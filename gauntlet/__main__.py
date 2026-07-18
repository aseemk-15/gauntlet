"""CLI: the gauntlet runs headless here first. The web view renders the same events."""
import argparse
import json
import sys

from .attack import fan_out
from .chart import load_chart
from .events import Run
from .fixloop import apply_fixes, render_card
from .judge import cluster, judge_all, singleton_gate
from .lanes import AGENTS_PER_LANE, DISCHARGE_LANES
from .severity import classify


def main(argv=None):
    p = argparse.ArgumentParser(prog="gauntlet", description="Bring receipts or die.")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run the gauntlet against a chart or encounter")
    run.add_argument("chart", nargs="?", help="path to a markdown chart")
    run.add_argument("--encounter", help="encounter id from assets/abridge-dataset")
    run.add_argument("--amended", action="store_true", help="attack the amended plan")
    run.add_argument("--summary-only", action="store_true", help="print chart summary and exit")
    fix = sub.add_parser("fix", help="clinician decisions -> order artifacts + amendment")
    fix.add_argument("run_dir", help="runs/<dir> containing findings.json")
    fix.add_argument("--dismiss", action="append", default=[],
                     metavar="ID[:RATIONALE]", help="dismiss a finding instead of fixing")
    rv = sub.add_parser("reverify", help="re-attack only the fixed lanes vs amended chart")
    rv.add_argument("run_dir", help="runs/<dir> that has been through `fix`")
    args = p.parse_args(argv)

    if args.cmd == "fix":
        return do_fix(args)
    if args.cmd == "reverify":
        from .reverify import reverify
        return reverify(args.run_dir)

    if args.cmd == "run":
        if args.encounter:
            return do_ambient(args.encounter)
        if not args.chart:
            p.error("need a chart path or --encounter")
        chart = load_chart(args.chart)
        assert "<!--" not in chart.text, "authoring comments must never reach agents"
        print(chart.summary())
        if args.summary_only:
            return 0
        run = Run("eleanor" + ("-amended" if args.amended else ""))
        results = fan_out(run, chart.text, DISCHARGE_LANES, AGENTS_PER_LANE)
        (run.dir / "attack.json").write_text(json.dumps(results, indent=2))
        objections = [r for r in results if r.get("objection")]
        verdicts = judge_all(run, chart, objections)
        survivors = [v for v in verdicts if v["verdict"] == "survive"]
        findings = singleton_gate(run, chart,
                                  [classify(f) for f in cluster(run, survivors)])
        (run.dir / "verdicts.json").write_text(json.dumps(verdicts, indent=2))
        (run.dir / "findings.json").write_text(json.dumps(findings, indent=2))
        (run.dir / "meta.json").write_text(json.dumps({"chart": str(args.chart)}))
        print(f"\n{len(results)} attacks ({len(objections)} objections) → "
              f"{len(survivors)} survived review → "
              f"{len(findings)} distinct findings  ({run.meter()})\n")
        for f in findings:
            print(render_card(f))
        print(f"artifacts: {run.dir}")
        return 0
    return 0


def do_ambient(key: str):
    from .ambient import (AMBIENT_ATTACKER_ROLE, AMBIENT_JUDGE_NOTE, AMBIENT_LANES,
                          load_encounter)
    chart, meta = load_encounter(key)
    run = Run(f"ambient-{key}")
    (run.dir / "ambient-chart.md").write_text(chart.text)
    (run.dir / "meta.json").write_text(json.dumps(
        {"chart": f"runs/{run.dir.name}/ambient-chart.md",
         "encounter": meta.get("visit_title")}))
    print(f"encounter: {meta.get('visit_title')}")
    results = fan_out(run, chart.text, AMBIENT_LANES, per_lane=2,
                      role=AMBIENT_ATTACKER_ROLE)
    (run.dir / "attack.json").write_text(json.dumps(results, indent=2))
    objections = [r for r in results if r.get("objection")]
    verdicts = judge_all(run, chart, objections, strict_note=AMBIENT_JUDGE_NOTE)
    survivors = [v for v in verdicts if v["verdict"] == "survive"]
    findings = singleton_gate(run, chart,
                              [classify(f) for f in cluster(run, survivors)])
    (run.dir / "verdicts.json").write_text(json.dumps(verdicts, indent=2))
    (run.dir / "findings.json").write_text(json.dumps(findings, indent=2))
    print(f"\n{len(results)} attacks ({len(objections)} objections) → "
          f"{len(survivors)} survived review → "
          f"{len(findings)} distinct findings  ({run.meter()})\n")
    from .fixloop import render_card
    for f in findings:
        print(render_card(f, total=len(results)))
    print(f"artifacts: {run.dir}")
    return 0


def do_fix(args):
    from pathlib import Path
    rd = Path(args.run_dir)
    findings = json.loads((rd / "findings.json").read_text())
    meta = json.loads((rd / "meta.json").read_text())
    chart = load_chart(meta["chart"])
    decisions = {}
    for d in args.dismiss:
        fid, _, why = d.partition(":")
        decisions[fid] = f"dismiss:{why or 'clinician judgment'}"
    run = Run("fix", dir_=rd)
    run.emit("fix_begin", findings=len(findings))
    manifest = apply_fixes(run, chart, findings, decisions)
    for o in manifest["orders"]:
        print(f"  ✓ {o['order']}  — order transmitted")
    for d in manifest["dismissed"]:
        print(f"  ✗ {d['finding']} dismissed: {d['rationale']}")
    print(f"\namended chart (supersedes med list): {manifest['amended_chart']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
