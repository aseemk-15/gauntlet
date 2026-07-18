"""The judge: four tests, default kill, temperature 0. All precision lives here.

Then one dedup/cluster call merges survivors into distinct findings; cluster size
renders as the "found by N of 30" badge.
"""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import JUDGE_MAX_TOKENS, JUDGE_MODEL
from .llm import cached_system, client, extract_json

JUDGE_ROLE = """You are the evidence judge in an adversarial discharge-review gauntlet.
Attacker agents raise objections against the discharge plan in the chart below. Your
default verdict is KILL. An objection survives ONLY if it passes ALL FOUR tests:

TEST 1 — EVIDENCE. Every quoted fragment must appear VERBATIM in the chart AND actually
support the claim being made. A quote that is real but does not support the claim fails.
(A mechanical verbatim pre-check result is provided; if it says a quote is absent, the
objection is dead regardless of anything else.)

TEST 2 — ADDRESSED. If the chart — anywhere, including any amendment or addendum with a
named owner and a date — already covers the objection, KILL it. "Covered" means a
concrete order, plan, or assignment exists; a vague mention is not coverage. If it is
genuinely not covered anywhere, the objection survives this test.

TEST 3 — MATERIALITY (the tonight test). Would a reasonable hospitalist, shown this
objection at the bedside tonight, change or add an order before this patient leaves?
KILL: therapy preference opinions (e.g. drug A vs drug B when the chart documents the
choice), clinical judgment calls within accepted practice, chart-hygiene and
documentation-completeness complaints, and hypotheticals the chart already guards
against. Survive: concrete, patient-specific harm pathways left open by the plan.

TEST 4 — ACTIONABILITY. The objection must yield ONE concrete, placeable order or
assignment (a lab with a date, a med change, a named result owner, a scheduled contact).
"Consider closer monitoring" is not an order. If no single placeable order exists, KILL.

Be strict. Duplicated findings are fine (clustering happens later) — judge each
objection on its own merits. Respond with ONLY a JSON object:
{
  "verdict": "survive" | "kill",
  "failed_test": null | "evidence" | "addressed" | "materiality" | "actionability",
  "reasoning": "<2-3 sentences, concrete, citing chart facts>"
}"""


def judge_objection(run, chart, obj: dict, strict_note: str = "") -> dict:
    agent_id = obj["agent"]
    # Mechanical verbatim pre-check — fabricated receipts die before the model runs.
    quote_checks = []
    for q in obj.get("quotes", []):
        text = q.get("quote", "") if isinstance(q, dict) else str(q)
        for frag in text.split("..."):
            frag = frag.strip()
            if frag:
                quote_checks.append((frag, chart.contains_verbatim(frag)))
    absent = [f for f, ok in quote_checks if not ok]

    user = (
        (strict_note + "\n" if strict_note else "")
        + "Objection under review:\n" + json.dumps(
            {k: obj.get(k) for k in ("lane", "claim", "quotes", "missing", "proposed_order")},
            indent=2)
        + "\n\nMechanical verbatim pre-check: "
        + (f"{len(absent)} of {len(quote_checks)} quoted fragments ABSENT from chart: "
           + json.dumps(absent[:3]) if absent else
           f"all {len(quote_checks)} quoted fragments verbatim-present.")
        + "\nApply the four tests. Default kill."
    )
    resp = client().messages.create(
        # Opus 4.8 rejects the temperature param; determinism rides on the strict rubric
        model=JUDGE_MODEL, max_tokens=1000,
        system=cached_system(JUDGE_ROLE, chart.text),
        messages=[{"role": "user", "content": user}],
    )
    run.add_usage(JUDGE_MODEL, resp.usage)
    try:
        verdict = extract_json(resp.content[0].text)
    except (ValueError, json.JSONDecodeError):
        verdict = {"verdict": "kill", "failed_test": "evidence",
                   "reasoning": "unparseable judge output — default kill"}
    if absent and verdict.get("verdict") == "survive":
        verdict = {"verdict": "kill", "failed_test": "evidence",
                   "reasoning": f"quote(s) not verbatim in chart: {absent[:2]}"}
    verdict["agent"] = agent_id
    verdict["objection"] = obj
    evt = "survivor" if verdict["verdict"] == "survive" else "killed"
    run.emit(evt, agent=agent_id, lane=obj.get("lane", "?"),
             test=verdict.get("failed_test") or "-",
             why=str(verdict.get("reasoning", ""))[:100])
    return verdict


def judge_all(run, chart, objections: list[dict], strict_note: str = "") -> list[dict]:
    run.emit("judge_begin", objections=len(objections))
    verdicts = []
    if not objections:
        run.emit("judge_done", survivors=0, killed=0, meter=run.meter())
        return verdicts
    # First verdict runs alone to prime the judge's chart-prefix cache.
    verdicts.append(judge_objection(run, chart, objections[0], strict_note))
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(judge_objection, run, chart, o, strict_note)
                for o in objections[1:]]
        for fut in as_completed(futs):
            verdicts.append(fut.result())
    survivors = [v for v in verdicts if v["verdict"] == "survive"]
    run.emit("judge_done", survivors=len(survivors),
             killed=len(verdicts) - len(survivors), meter=run.meter())
    return verdicts


SINGLETON_GATE_NOTE = """CONFIRMATION GATE — MAXIMUM STRICTNESS. This finding was raised
by only ONE attacker in the whole swarm (single-source; multi-agent findings skip this
gate). Presume it should be killed. Confirm survival ONLY if the gap is unambiguous,
material tonight, and clearly not covered anywhere in the chart. Judgment calls within
accepted practice, access/logistics speculation, and monitoring preferences die here."""


def singleton_gate(run, chart, findings: list[dict]) -> list[dict]:
    """Calibration: multi-agent support is a confidence tier. Singleton findings face a
    second maximum-strictness pass; survivors render with a single-source badge."""
    kept = []
    for f in findings:
        if f.get("found_by", 0) != 1:
            kept.append(f)
            continue
        obj = {"agent": f"gate:{f['id']}", "lane": f.get("id"),
               "claim": f.get("claim"), "quotes": f.get("quotes"),
               "missing": f.get("missing"), "proposed_order": f.get("proposed_order")}
        v = judge_objection(run, chart, obj, strict_note=SINGLETON_GATE_NOTE)
        if v["verdict"] == "survive":
            kept.append(f | {"gate": "confirmed"})
        else:
            run.emit("gate_killed", finding=f["id"],
                     why=str(v.get("reasoning", ""))[:110])
    return kept


CLUSTER_ROLE = """You cluster surviving objections from an adversarial discharge review
into DISTINCT findings. Two objections belong to the same finding if they describe the
same underlying gap in the plan (same harm pathway, same missing order), even if worded
differently or found via different lanes. Two objections that would be closed by the
same set of orders in the same care domain (e.g. "no weight monitoring" and "diuretic
unchanged above dry weight" are both the volume-management gap) are ONE finding — state
both facets in its claim. Do not merge genuinely different gaps.

For each cluster, synthesize the single strongest statement of the finding, choose the
best verbatim quotes (copy them EXACTLY as given, at most 3 per finding), and the single
best proposed order. Output AT MOST 6 findings — merge aggressively; a large survivor
set means heavy duplication, not many distinct gaps. Keep every "members" list complete.

Respond with ONLY JSON:
{"findings": [{
  "id": "<kebab-case-slug>",
  "title": "<short title>",
  "claim": "<one-sentence strongest statement>",
  "members": ["<agent ids>"],
  "quotes": [{"section": "...", "quote": "<verbatim>"}],
  "missing": "<what the plan lacks>",
  "proposed_order": "<one placeable order>"
}]}"""


def cluster(run, survivors: list[dict]) -> list[dict]:
    if not survivors:
        return []
    # Slim payload at swarm scale: one quote per objection (enforce_receipts recovers
    # full receipts from the members' originals afterwards).
    payload = []
    for v in survivors:
        o = v["objection"]
        payload.append({"agent": v["agent"], "lane": o.get("lane"),
                        "claim": o.get("claim"),
                        "quotes": (o.get("quotes") or [])[:1],
                        "missing": str(o.get("missing", ""))[:220],
                        "proposed_order": str(o.get("proposed_order", ""))[:220]})
    findings = None
    note = ""
    for attempt in (1, 2):  # retry once if the model breaks the JSON contract
        resp = client().messages.create(
            model=JUDGE_MODEL, max_tokens=8000,
            system=[{"type": "text", "text": CLUSTER_ROLE + note}],
            messages=[{"role": "user", "content": json.dumps(payload, indent=2)}],
        )
        run.add_usage(JUDGE_MODEL, resp.usage)
        try:
            findings = extract_json(resp.content[0].text)["findings"]
            break
        except (ValueError, json.JSONDecodeError, KeyError) as err:
            run.emit("cluster_retry", attempt=attempt, err=str(err)[:80])
            note = ("\nPREVIOUS ATTEMPT PRODUCED INVALID/TRUNCATED JSON. Output ONLY "
                    "compact valid JSON, max 5 findings, max 2 quotes each, no prose.")
    if findings is None:
        # code fallback: one finding per lane from the strongest survivor
        by_lane = {}
        for v in survivors:
            by_lane.setdefault(v["objection"].get("lane", "?"), []).append(v)
        findings = []
        for lane, vs in list(by_lane.items())[:6]:
            o = vs[0]["objection"]
            findings.append({"id": f"{lane}-finding", "title": str(o.get("claim", ""))[:80],
                             "claim": o.get("claim"), "members": [v["agent"] for v in vs],
                             "quotes": o.get("quotes", []), "missing": o.get("missing"),
                             "proposed_order": o.get("proposed_order")})
        run.emit("cluster_fallback", findings=len(findings))
    for f in findings:
        f["found_by"] = len(f.get("members", []))
        run.emit("finding", id=f["id"], title=f["title"], found_by=f["found_by"])
    run.emit("cluster_done", findings=len(findings), meter=run.meter())
    return findings
