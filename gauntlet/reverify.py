"""Targeted re-verification: re-attack ONLY the fixed findings' lanes against the
amended chart. Any new survivor must pass a second, maximum-strictness judge pass
(the confirmation gate) before it counts. Calibration showed full-swarm re-runs land
clean only ~60-70% of the time — and every escapee was a REAL residual gap — so the
primary mechanic is targeted, gated, and honest about what it finds.
"""
import json
from pathlib import Path

from .attack import fan_out
from .chart import load_chart
from .events import Run
from .judge import judge_all
from .lanes import DISCHARGE_LANES

GATE_NOTE = """CONFIRMATION GATE — MAXIMUM STRICTNESS. This objection already survived
one judge pass against an AMENDED plan. Presume it should be killed. Confirm survival
ONLY if the gap is unambiguous, material tonight, and clearly not addressed anywhere in
the chart INCLUDING the amendment sections (which SUPERSEDE the original 14:32 plan —
read them as the plan of record). If the amendment covers it with an owner and a date,
KILL."""


def reverify(run_dir: str) -> int:
    rd = Path(run_dir)
    manifest = json.loads((rd / "orders.json").read_text())
    findings = json.loads((rd / "findings.json").read_text())
    chart = load_chart(manifest["amended_chart"])

    # The fixed findings' lanes = union of lanes their member attackers came from.
    fixed = {f["id"]: f for f in findings if f["id"] in manifest["fixed"]}
    lanes = sorted({m.split("#")[0] for f in fixed.values() for m in f.get("members", [])})
    lane_map = {ln: DISCHARGE_LANES[ln] for ln in lanes if ln in DISCHARGE_LANES}

    run = Run("reverify", dir_=rd)
    run.emit("reverify_begin", lanes=len(lane_map), targets=",".join(fixed))
    results = fan_out(run, chart.text, lane_map, per_lane=3)
    objections = [r for r in results if r.get("objection")]
    verdicts = judge_all(run, chart, objections)
    survivors = [v for v in verdicts if v["verdict"] == "survive"]

    confirmed = []
    if survivors:
        run.emit("gate_begin", candidates=len(survivors))
        gated = judge_all(run, chart, [v["objection"] for v in survivors],
                          strict_note=GATE_NOTE)
        confirmed = [v for v in gated if v["verdict"] == "survive"]

    (rd / "reverify.json").write_text(json.dumps(
        {"lanes": lanes, "attacks": len(results), "raw_survivors": len(survivors),
         "confirmed_survivors": [v["objection"] for v in confirmed]}, indent=2))

    n = len(results)
    if not confirmed:
        banner = (f"0 SURVIVING OBJECTIONS — {n} attacks · {run.elapsed:.0f}s · "
                  f"attacked and not broken")
        run.emit("banner", text=banner, note="Not a safety certification.")
        print(f"\n{'=' * 70}\n  {banner}\n  (Not a safety certification.)\n{'=' * 70}")
        print(f"  meter: {run.meter()}")
        return 0
    run.emit("residual_gaps", count=len(confirmed))
    print(f"\n{len(confirmed)} objection(s) survived the confirmation gate — "
          f"the fix was incomplete. That is the product working:")
    for v in confirmed:
        print(f"  · [{v['objection'].get('lane')}] {v['objection'].get('claim')}")
    return 1
