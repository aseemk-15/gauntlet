"""The fan-out: 10 lanes × 3 attackers, concurrent, chart as cached prefix, temp 1."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import ATTACKER_MAX_TOKENS, ATTACKER_MODEL
from .llm import cached_system, client, extract_json

ATTACKER_ROLE = """You are one adversarial reviewer in a 30-agent gauntlet run against a
discharge plan. Your one job: find the documented way this discharge plan fails this
patient, within your assigned attack lane — with verbatim chart receipts — or concede.

Rules:
- Use ONLY the chart provided. Every quote must be copied VERBATIM from it (exact
  characters; you may trim with "..." between separate verbatim fragments, but each
  fragment must appear exactly in the chart). Fabricated or paraphrased quotes get your
  objection killed instantly in review.
- Your objection must be about how the PLAN fails the PATIENT — a concrete harm pathway,
  not chart hygiene, style, or documentation completeness for its own sake.
- Propose exactly ONE concrete, placeable order or action that would close the gap.
- If your lane genuinely has no documented failure, return NO_OBJECTION — a dead
  objection is worse than none.

Respond with ONLY a JSON object, no prose around it:
{
  "objection": true,
  "claim": "<one sentence: what fails and how it harms this patient>",
  "quotes": [{"section": "<chart section header>", "quote": "<verbatim chart text>"}],
  "missing": "<what the plan lacks>",
  "proposed_order": "<one concrete placeable order>"
}
or: {"objection": false, "reason": "<why the lane is clean>"}"""


def attack_prompt(lane: str, focus: str, agent_n: int) -> str:
    return (
        f"Your attack lane: {lane} — {focus}\n"
        f"You are attacker #{agent_n} of 3 in this lane; find the strongest documented "
        f"failure you can, even if a teammate might find the same one.\n"
        f"Attack the plan in the section marked 'THE PLAN UNDER ATTACK'."
    )


def run_attacker(run, chart_text: str, lane: str, focus: str, agent_n: int) -> dict:
    agent_id = f"{lane}#{agent_n}"
    system = cached_system(ATTACKER_ROLE, chart_text)
    run.emit("attacker_start", quiet=True, agent=agent_id, lane=lane)
    result = None
    for attempt in (1, 2):  # retry-once on parse failure
        resp = client().messages.create(
            model=ATTACKER_MODEL,
            max_tokens=ATTACKER_MAX_TOKENS,
            temperature=1,
            system=system,
            messages=[{"role": "user", "content": attack_prompt(lane, focus, agent_n)}],
        )
        run.add_usage(ATTACKER_MODEL, resp.usage)
        try:
            result = extract_json(resp.content[0].text)
            break
        except (ValueError, json.JSONDecodeError) as e:
            run.emit("parse_retry", agent=agent_id, attempt=attempt, err=str(e)[:80])
    if result is None:
        result = {"objection": False, "reason": "unparseable after retry"}
    result["agent"] = agent_id
    result["lane"] = lane
    if result.get("objection"):
        run.emit("objection", agent=agent_id, lane=lane,
                 claim=str(result.get("claim", ""))[:110])
    else:
        run.emit("no_objection", agent=agent_id, lane=lane)
    return result


def fan_out(run, chart_text: str, lanes: dict, per_lane: int = 3,
            role: str = ATTACKER_ROLE) -> list[dict]:
    jobs = [(lane, focus, n) for lane, focus in lanes.items()
            for n in range(1, per_lane + 1)]
    run.emit("attack_begin", agents=len(jobs), lanes=len(lanes))
    # First call primes the prompt cache; the rest fan out against a warm prefix.
    first = run_attacker(run, chart_text, *jobs[0])
    results = [first]
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = [pool.submit(run_attacker, run, chart_text, lane, focus, n)
                for lane, focus, n in jobs[1:]]
        for fut in as_completed(futs):
            results.append(fut.result())
    objections = [r for r in results if r.get("objection")]
    run.emit("attack_done", raw_objections=len(objections),
             conceded=len(results) - len(objections), meter=run.meter())
    return results
