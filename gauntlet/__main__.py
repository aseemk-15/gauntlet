"""CLI: the gauntlet runs headless here first. The web view renders the same events."""
import argparse
import sys

from .chart import load_chart


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
        print("\nattack phase: not built yet", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
