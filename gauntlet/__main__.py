"""CLI: the gauntlet runs headless here first. The web view renders the same events."""
import argparse
import json
import sys

from .attack import fan_out
from .chart import load_chart
from .events import Run
from .judge import cluster, judge_all
from .lanes import AGENTS_PER_LANE, DISCHARGE_LANES


def main(argv=None):
    p = argparse.ArgumentParser(prog="gauntlet", description="Bring receipts or die.")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run the gauntlet against a chart or encounter")
    run.add_argument("chart", nargs="?", help="path to a markdown chart")
    run.add_argument("--encounter", help="encounter id from assets/abridge-dataset")
    run.add_argument("--amended", action="store_true", help="attack the amended plan")
    run.add_argument("--summary-only", action="store_true", help="print chart summary and exit")
    args = p.parse_args(argv)

    if args.cmd == "run":
        if args.encounter:
            print("ambient mode: not built yet", file=sys.stderr)
            return 2
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
        findings = cluster(run, survivors)
        (run.dir / "verdicts.json").write_text(json.dumps(verdicts, indent=2))
        (run.dir / "findings.json").write_text(json.dumps(findings, indent=2))
        print(f"\n{len(objections)} attacks → {len(survivors)} survived review → "
              f"{len(findings)} distinct findings  ({run.meter()})")
        for f in findings:
            print(f"  [{f['id']}] {f['title']}  — found by {f['found_by']} of "
                  f"{len(results)}")
        print(f"artifacts: {run.dir}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
