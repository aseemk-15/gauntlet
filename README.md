# The Gauntlet

**Bring receipts, or be refuted.**

Before a patient is discharged, an adversarial swarm (10 lanes × up to 10 agents) each
gets one job: find the documented way this discharge plan fails this patient — with
verbatim chart receipts — or be refuted in review. A strict evidence judge rejects
~90-95% of objections with reasons. The survivors render
as evidence cards with chart-line receipts. The clinician fills the gaps. A targeted
re-verification confirms the amended plan holds.

This is an **agent pipeline with a mission-log view** — the CLI runs the whole gauntlet
headless; the web view replays the same real event stream.

> **"0 SURVIVING OBJECTIONS" means attacked and not broken. It is not a safety
> certification.** The Gauntlet surfaces documented conflicts for clinician review; it
> never gives clinical advice and never resolves a conflict itself.

Built at the Abridge x Anthropic hackathon, 2026-07-18, in one day.

## Disclosures

Prebuilt assets used, per event rules: (1) a synthetic patient chart (Eleanor Vance —
fictional, authored before the event as test data; includes an authoring spec for the
amendment used in the demo's fix loop); (2) the organizer-provided
synthetic-ambient-fhir-25 dataset. A visual design sketch of the UI existed pre-event as
a mock; all code, prompts, and UI in this repo were written during the event. Pre-event
calibration experiments informed design choices (documented in DESIGN.md); their code was
discarded.

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install anthropic
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env   # never committed

# the full demo arc, headless:
./gauntlet-cli run assets/chart-eleanor-vance.md   # 30 attackers -> judge -> evidence cards
./gauntlet-cli fix runs/<run-dir> \                # clinician decisions -> orders + amendment
    --dismiss <finding-id>:"rationale"             #   (amendment SUPERSEDES the med list)
./gauntlet-cli reverify runs/<run-dir>             # targeted re-attack of the fixed lanes

# ambient-documentation mode (organizer dataset):
./gauntlet-cli run --encounter covid-inpt          # aliases: covid-inpt, annual-htn, hospice-1/2

# attack any discharge summary against an encounter's grounding record
# (two test variants, authored during the event, live in assets/variants/):
./gauntlet-cli run --encounter covid-inpt --summary assets/variants/covid-discharge-poor.md
# poor variant -> 4 verified findings; corrected variant -> 0 survivors.
# The mission log also has an "attack your own summary" panel that launches real runs.

# views of the same real event stream (CLI prints it too):
.venv/bin/python ui/serve.py
#   http://localhost:3010            the note under review: EMR-neutral discharge
#                                    summary; run ceremony overlay; red-pen highlights
#                                    with popover accept/dismiss; accepted orders
#                                    insert as tracked changes; re-verify chip
#   http://localhost:3010/md         physician sheet (single-column card view)
#   http://localhost:3010/corridor   corridor mission log (field -> judge gate -> document)
#   http://localhost:3010/classic    original mission log
# every run also writes runs/<dir>/cds-cards.json — CDS Hooks cards, the payload an
# EHR order-sign hook (e.g. Epic CDS Hooks) would render at discharge signing
```

## How it works

See [DESIGN.md](DESIGN.md) for the architecture and the pre-event calibration findings
that shaped it.

- **Attack:** 10 lanes × 3 attackers, concurrent, temp 1, the chart as a cached prompt
  prefix. Attackers object to nearly everything by design — precision is not their job.
- **Judge:** frontier model, temp 0, four tests (verbatim evidence, already-addressed,
  tonight-materiality, single-order actionability), refute by default. Then one clustering
  pass merges survivors into distinct findings; cluster size renders as a
  "found by N of 30" confidence badge.
- **Fix loop:** survivor cards state gaps; the clinician decides; an agent emits a
  structured order artifact. No mock CPOE.
- **Targeted re-verification:** only the fixed findings' lanes re-attack the amended
  plan; any new survivor must pass a second, maximum-strictness judge pass.

All elapsed-time and cost numbers displayed anywhere are real, measured from live API
usage. Nothing is simulated.

## Evidence integrity

Two different promises, stated exactly:

- **Receipts are guaranteed.** Every quote rendered on a card is mechanically verified
  verbatim against the source text, in code, after every model stage (including the
  clustering step, which is the one place quotes could drift). A drifted quote is
  replaced with the original attacker's verified quote or dropped; a finding with no
  verifiable receipt cannot render. No model output is trusted for evidence.
- **Claims are argued, not guaranteed.** The one-sentence claim above the receipts is a
  model-authored argument about verified evidence. It survives four adversarial tests
  and (if single-source) a maximum-strictness confirmation gate — but it is reviewed,
  not proven. That is why every card is attributable (finder agents, lane, full run
  audit trail in `runs/<dir>/`), why the clinician makes every decision, and why the
  banner never says "safe."

## License

MIT
