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
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(judge_objection, run, chart, o, strict_note)
                for o in objections]
        for fut in as_completed(futs):
            verdicts.append(fut.result())
    survivors = [v for v in verdicts if v["verdict"] == "survive"]
    run.emit("judge_done", survivors=len(survivors),
             killed=len(verdicts) - len(survivors), meter=run.meter())
    return verdicts


CLUSTER_ROLE = """You cluster surviving objections from an adversarial discharge review
into DISTINCT findings. Two objections belong to the same finding if they describe the
same underlying gap in the plan (same harm pathway, same missing order), even if worded
differently or found via different lanes. Do not merge genuinely different gaps.

For each cluster, synthesize the single strongest statement of the finding, choose the
best verbatim quotes (copy them EXACTLY as given), and the single best proposed order.

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
    payload = [{k: v["objection"].get(k) for k in
                ("claim", "quotes", "missing", "proposed_order", "lane")}
               | {"agent": v["agent"]} for v in survivors]
    resp = client().messages.create(
        model=JUDGE_MODEL, max_tokens=JUDGE_MAX_TOKENS,
        system=[{"type": "text", "text": CLUSTER_ROLE}],
        messages=[{"role": "user", "content": json.dumps(payload, indent=2)}],
    )
    run.add_usage(JUDGE_MODEL, resp.usage)
    findings = extract_json(resp.content[0].text)["findings"]
    for f in findings:
        f["found_by"] = len(f.get("members", []))
        run.emit("finding", id=f["id"], title=f["title"], found_by=f["found_by"])
    run.emit("cluster_done", findings=len(findings), meter=run.meter())
    return findings
