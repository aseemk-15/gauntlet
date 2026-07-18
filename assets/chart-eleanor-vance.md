# SYNTHETIC PATIENT CHART — Eleanor Vance (FICTIONAL — demo asset, authored pre-event)

## Demographics / Problem List
- Eleanor Vance, 78F. MRN 000-DEMO-4471.
- HFrEF, EF 30% (see cardiology records). Atrial fibrillation, on warfarin (CHA2DS2-VASc 6).
- CKD stage 3b (baseline Cr ~1.5, est CrCl ~40 mL/min). HTN. OA.
- Allergies: NKDA (confirmed on admission and per outside records).

## Admission H&P (07/11, Dr. Patel, hospitalist)
78F with HFrEF (EF 30%) and AF on warfarin admitted 07/11 with acute decompensated heart
failure: 1 wk progressive dyspnea, orthopnea, 3+ pitting edema. Admission weight 79.6 kg.
BNP 1840. CXR: pulmonary vascular congestion, small bilateral effusions. Started IV
furosemide. Home meds continued: warfarin 5 mg PO daily (on warfarin 11 years, INR stable
on current dose; patient declines DOAC switch — cost/coverage discussed 2024, documented
by PCP), metoprolol succinate 50 mg daily, furosemide 40 mg PO daily (home dose),
lisinopril previously discontinued 2025 for hyperkalemia episode.

## Hospital Course (summary through 07/16)
- 07/11–07/13: IV diuresis, net -3.2 L. Transitioned to PO furosemide 07/14.
- 07/12: dysuria + urinary frequency; UA: +LE, +nitrites, >50 WBC. Dx: UTI. Urine culture
  sent 07/12. Empiric TMP-SMX DS (800-160) PO BID started 07/13 per sensitivities pending,
  renally reviewed (CrCl ~40: acceptable; monitor K+).
- 07/14: Tmax 38.6 overnight. Blood cultures x2 drawn 07/14 06:10. Afebrile since 07/14 PM.
- 07/14: urine culture RESULT: >100,000 CFU/mL E. coli, PAN-SENSITIVE (incl. TMP-SMX).
- 07/15–07/16: clinically improved, on room air, ambulating with PT.

## Medication List at Discharge (med rec 07/16)
- warfarin 5 mg PO daily — home med, CONTINUE
- TMP-SMX DS 800-160 mg PO BID — CONTINUE through 07/20 (7-day course from 07/13)
- furosemide 40 mg PO daily — home dose, UNCHANGED
- metoprolol succinate 50 mg PO daily — CONTINUE
- acetaminophen 500 mg PRN

## Labs (most recent)
- 07/16 06:00: Na 138, K 4.2, Cr 1.5 (baseline), BUN 34. CBC unremarkable, WBC 8.2 (from 13.1).
- 07/12: INR 2.4 (in range). NO INR drawn after 07/12.
- Micro: urine cx 07/12 → E. coli pan-sensitive (final 07/14). Blood cx x2 07/14 →
  NO GROWTH TO DATE (preliminary, day 2).

## Vitals / Weights
- 07/16 06:00: BP 128/74, HR 68 (rate-controlled AF), afebrile 48h, SpO2 95% RA.
- Weights: 79.6 kg (07/11 admit) → 78.9 (07/13) → 78.6 (07/14) → 78.4 kg (07/15).

## PT Note (07/15, R. Alvarez PT)
"Pt ambulated 150 ft with rolling walker, room air, RPE 11/20. Weight today 78.4 kg.
Recommend home PT 2x/wk. Cleared for home discharge from mobility standpoint."

## Scanned Outside Record — Cardiology clinic letter (03/2026, faxed, Dr. Kim, OCR'd)
"...echocardiogram 02/2026: LVEF 30%, moderate MR. Target DRY WEIGHT 74.3 kg. Optimal
volume management essential; recommend daily weights at home, call for gain >1.5 kg..."

## Advance Care Planning
POLST reviewed 07/14: FULL TREATMENT. Documented by Dr. Patel with patient and daughter.

## Social
Lives with daughter (primary support, owns car, documented driver to appointments).
Medicare A/B + Part D. Copay sensitivity documented by PCP (2024).

## DISCHARGE ORDER + SUMMARY DRAFT (07/16 14:32, Dr. Patel) — THE PLAN UNDER ATTACK
- Disposition: HOME today with daughter. Home PT referral placed.
- Meds per med rec above (no changes at discharge).
- Follow-up: PCP in 1–2 weeks (patient to schedule). Cardiology "as scheduled" (next appt
  09/2026).
- Discharge summary draft: HF exacerbation, diuresed to improvement; UTI on TMP-SMX,
  afebrile 48h. [No mention of pending blood cultures. No INR follow-up ordered. No
  post-discharge weight monitoring plan beyond "resume home routine."]

<!-- SEEDED HAZARDS (authoring note, not part of chart shown to agents):
  1. warfarin + TMP-SMX potentiation with NO INR recheck ordered (last INR 07/12)
  2. discharge weight 78.4 vs documented dry weight 74.3 (fax), furosemide unchanged
  3. blood cultures pending at discharge, no result owner / routing, absent from summary
  Everything else deliberately clean: POLST documented, transport documented, NKDA
  consistent, K+ normal w/ monitoring note, renal dose reviewed, urine cx sensitive. -->

<!-- AMENDMENT SPEC for the demo fix-loop (calibration-tested 07-16; the version below
  achieved re-run-to-clean; deviations from it produced legitimate escapees every time):
  - INR draw 07/18 (2 days post-discharge — 07/19 drew a "peak interaction window" escapee)
    AND post-course INR 07/23; coumadin clinic manages dosing through 07/26; daughter told
    bleeding precautions.
  - BMP (Cr, K+) with the 07/18 draw (closes the "monitor K+ but no lab ordered" gap that
    escaped twice); results to Dr. Patel + coumadin clinic same-day; repeat at 07/21
    telehealth if K+ >5.0 or Cr rise >0.3.
  - Diuresis: furosemide 40 BID x5d then reassess at 07/21 telehealth vs home dose; daily
    home weights, call >1.5 kg gain; STOP-LOSS: hold diuretic and call if weight <75 kg or
    SBP <100 (kills the "no lower safety limit" escapee); home health RN 07/18; document
    "not expected to reach dry weight before discharge — deliberate outpatient strategy
    per cardiology"; cardiology appt moved to 07/24.
  - Cultures: ownership assigned (Dr. Patel), micro-pages-hospitalist routing order,
    discharge summary updated to note pending cultures + de-escalation plan.
  - CRITICAL AUTHORING RULE: the amendment must SUPERSEDE the med list ("this list is the
    discharge med list of record; the 14:32 list is VOID") — append-only addenda leave
    contradictions the swarm reliably catches (furosemide daily-vs-BID escaped this way).
  - Walker: confirm rolling walker already at home (in use since 2025), no new DME. -->
