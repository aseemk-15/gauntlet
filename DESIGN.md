# DESIGN — The Gauntlet

## Architecture

```
                 chart (markdown / FHIR bundle)
                          │  authoring comments stripped at load —
                          │  agents never see fixture metadata
                          ▼
      ┌───────────────────────────────────────────┐
      │ ATTACK   10 lanes × 3 attackers, concurrent│
      │ fast model, temp 1, chart = CACHED prefix  │
      │ output: JSON objections w/ verbatim quotes │
      └───────────────────┬───────────────────────┘
                          │ ~28-30 raw objections
                          ▼
      ┌───────────────────────────────────────────┐
      │ JUDGE    frontier model, temp 0, DEFAULT   │
      │ KILL. Four tests:                          │
      │  1 EVIDENCE     quotes verbatim in chart?  │
      │  2 ADDRESSED    covered incl. amendments?  │
      │  3 MATERIALITY  change an order TONIGHT?   │
      │  4 ACTIONABILITY one placeable order?      │
      └───────────────────┬───────────────────────┘
                          │ ~3-5 survivors
                          ▼
      ┌───────────────────────────────────────────┐
      │ DEDUP    one cluster call → distinct        │
      │ findings; cluster size = "found by N of 30"│
      └───────────────────┬───────────────────────┘
                          ▼
      ┌───────────────────────────────────────────┐
      │ SEVERITY  lookup tables (ISMP high-alert,  │
      │ ONC high-priority DDI) → tier + citation   │
      └───────────────────┬───────────────────────┘
                          ▼
      ┌───────────────────────────────────────────┐
      │ FIX LOOP  cards state GAPS → clinician     │
      │ decides → agent emits structured order     │
      │ artifact (no mock CPOE)                    │
      └───────────────────┬───────────────────────┘
                          ▼
      ┌───────────────────────────────────────────┐
      │ TARGETED RE-VERIFICATION  re-attack ONLY   │
      │ the fixed findings' lanes vs amended chart │
      │ (amendment SUPERSEDES med list); new        │
      │ survivors face a 2nd max-strictness judge  │
      └───────────────────────────────────────────┘
                          ▼
        "0 SURVIVING OBJECTIONS — 30 attacks · <real time>
         · attacked and not broken"  (not a safety certification)
```

Every stage emits real events to a JSONL stream; the CLI trace and the mission-log web
view are two renderers of the same stream. Elapsed time and cost are computed from actual
API usage objects — nothing displayed is simulated.

## Why it is built this way (pre-event calibration findings)

Pre-event calibration experiments (2026-07-16/17, code discarded per event rules; results
carried as knowledge) shaped five design decisions:

1. **All precision lives in the judge.** Attackers object ~28/30 regardless of
   instructions. A naive "be strict" judge passed 20/30 objections; the four-test rubric
   with default-kill at temperature 0 gets to 3-4 genuine survivors. So: replicate
   attackers, single-run the judge.
2. **Dedup is mandatory.** 13 raw survivors → 4 distinct findings in calibration; the
   cluster size is a free consensus badge ("found independently by N of 30"). Treated as
   a confidence tier, not a filter — real findings have arrived as singletons.
3. **Naive full-swarm re-run-to-clean is only ~60-70% reliable — and every escapee
   observed across 11 calibration re-runs was a REAL residual gap, not a hallucination.**
   Hence targeted re-verification (re-attack only the fixed lanes) as the primary
   mechanic, plus a second-pass confirmation gate, plus amendments that SUPERSEDE the
   med list of record — append-only addenda create internal contradictions the swarm
   correctly catches.
4. **Zero fabricated-evidence survivors were ever observed** — requiring verbatim,
   source-attributed quotes and verifying them mechanically against the chart text holds.
5. **Judge is ~5x more stable than attackers** (consistent with published NHS multi-agent
   findings): attacker variety is where the recall comes from; judge determinism is where
   the precision comes from.

## Lanes

Discharge mode (10 lanes × 3 attackers): drug-interactions, anticoagulation-monitoring,
volume-status, renal-electrolytes, pending-results, follow-up-continuity,
med-rec-contradictions, outside-records, care-coordination, infection-course.

Ambient mode (6 lanes × 2 attackers, organizer dataset): said-not-documented,
med-mismatch, follow-up-gaps, grounding (note vs FHIR numerics), internal-contradiction,
safety-unaddressed. Receipts are source-attributed across transcript / note / AVS / FHIR.

## Models

Attackers: Haiku-class, temperature 1, max_tokens ≥ 900, retry-once on parse failure.
Judge / dedup / confirmation gate: frontier model, temperature 0. The shared chart prefix
is cached (`cache_control` on the system block) — that is what makes 30 concurrent agents
cheap (~$0.40-0.65 and ~45-65s per full run, measured).

## Integrity rules

- Agents never see fixture authoring comments (stripped at load).
- No clinical advice: the system surfaces documented conflicts with receipts; the
  clinician decides everything.
- Banner language is exactly "0 SURVIVING OBJECTIONS — attacked and not broken. Not a
  safety certification." Never "safe" or "cleared."
