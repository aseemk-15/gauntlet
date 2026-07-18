# The Gauntlet

**Bring receipts or die.**

Before a patient is discharged, 30 adversarial agents each get one job: find the
documented way this discharge plan fails this patient — with verbatim chart receipts —
or die in review. A strict evidence judge kills ~90% of objections. The survivors render
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
./gauntlet-cli run assets/chart-eleanor-vance.md           # full 30-agent gauntlet
./gauntlet-cli run assets/chart-eleanor-vance.md --amended # attack the amended plan
./gauntlet-cli run --encounter covid-inpt                  # ambient mode (organizer dataset)
```

## How it works

See [DESIGN.md](DESIGN.md) for the architecture and the pre-event calibration findings
that shaped it.

- **Attack:** 10 lanes × 3 attackers, concurrent, temp 1, the chart as a cached prompt
  prefix. Attackers object to nearly everything by design — precision is not their job.
- **Judge:** frontier model, temp 0, four tests (verbatim evidence, already-addressed,
  tonight-materiality, single-order actionability), default kill. Then one clustering
  pass merges survivors into distinct findings; cluster size renders as a
  "found by N of 30" confidence badge.
- **Fix loop:** survivor cards state gaps; the clinician decides; an agent emits a
  structured order artifact. No mock CPOE.
- **Targeted re-verification:** only the fixed findings' lanes re-attack the amended
  plan; any new survivor must pass a second, maximum-strictness judge pass.

All elapsed-time and cost numbers displayed anywhere are real, measured from live API
usage. Nothing is simulated.

## License

MIT
