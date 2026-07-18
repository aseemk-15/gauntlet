"""Ambient mode: the same gauntlet pointed at an ambient-documentation encounter.

The SOAP note and after-visit summary are the documentation under attack; the ambient
transcript and FHIR record are the grounding sources. This is SYNTHETIC organizer data —
even carefully generated notes drift from their grounding; that is why the verification
layer exists.
"""
import json

from .chart import Chart, COMMENT_RE
from .config import ROOT

DATASET = ROOT / "assets" / "abridge-dataset" / "synthetic-ambient-fhir-25.json"

# Judge-pick go-list (calibration-verified fertile; SNF admissions are barren — excluded).
ALIASES = {
    "covid-inpt": "COVID-19 isolation",
    "annual-htn": "new hypertension",
    "hospice-1": "Hospice admission — end-stage colon cancer",
    "hospice-2": "advanced colon cancer with cardiac",
}

AMBIENT_LANES = {
    "said-not-documented": "Things the patient or clinician SAID in the transcript (symptoms, meds, concerns, commitments) that the note and after-visit summary fail to document or act on.",
    "med-mismatch": "Medication discrepancies between what the transcript says, what the note documents, what the after-visit summary tells the patient, and what the FHIR record shows.",
    "follow-up-gaps": "Follow-up, referral, or result-routing commitments made or implied in the encounter that the documentation leaves unowned, undated, or missing entirely.",
    "grounding": "Numeric and factual drift: values in the note or after-visit summary (labs, vitals, doses, dates) that contradict the FHIR structured record or the transcript — including a note lab snapshot that no longer reflects the latest or trending FHIR values for the same analyte.",
    "internal-contradiction": "Statements inside the documentation set (note vs after-visit summary vs FHIR) that contradict each other about this encounter.",
    "safety-unaddressed": "Documented abnormals or safety signals the assessment/plan never addresses: scan the FHIR lab series for markedly abnormal or persistently abnormal values (against standard reference ranges) and disclosures in the transcript, then check whether the note's assessment/plan ever mentions them.",
}

AMBIENT_ATTACKER_ROLE = """You are one adversarial reviewer in a gauntlet run against
ambient clinical documentation. The record below has four sources: TRANSCRIPT (ambient,
speaker-labeled), SOAP NOTE, AFTER-VISIT SUMMARY, and FHIR CONTEXT (structured record).
The NOTE and AFTER-VISIT SUMMARY are the documentation under attack; the TRANSCRIPT and
FHIR CONTEXT are grounding sources.

Your one job: find the documented way this documentation fails this patient, within your
assigned attack lane — with verbatim receipts — or concede.

Rules:
- Every quote must be copied VERBATIM from the record, and each quote's "section" must
  name its source: TRANSCRIPT, NOTE, AVS, or FHIR. Cross-source receipts (e.g. a NOTE
  value vs the FHIR value it contradicts) are the strongest possible evidence.
- The objection must matter for this patient — a concrete way the documentation misleads
  care, not style or completeness for its own sake.
- Propose exactly ONE concrete correction or order.
- If your lane is genuinely clean, return NO_OBJECTION.

Respond with ONLY a JSON object, no prose around it:
{
  "objection": true,
  "claim": "<one sentence: what fails and why it matters>",
  "quotes": [{"section": "TRANSCRIPT|NOTE|AVS|FHIR", "quote": "<verbatim>"}],
  "missing": "<what the documentation lacks or gets wrong>",
  "proposed_order": "<one concrete correction or order>"
}
or: {"objection": false, "reason": "<why the lane is clean>"}"""

SUMMARY_LANES = {
    "med-accuracy": "Medications in the discharge summary: wrong drug/dose/duration vs the grounding record, or instructions that are dangerous given the documented labs and conditions (renal function, interactions, contraindications).",
    "grounding": "Numeric and factual drift: values, dates, or events stated in the summary that contradict the FHIR record, the note, or the transcript.",
    "pending-followup": "Pending results, abnormal labs, or required follow-ups that the summary leaves without a named owner, a date, or any mention at all.",
    "said-not-documented": "Commitments, symptoms, or concerns raised in the transcript or note that the summary drops (promised referrals, monitoring, patient concerns).",
    "internal-contradiction": "Statements inside the summary that contradict each other or give the patient conflicting instructions.",
    "safety-unaddressed": "Markedly abnormal or trending values in the FHIR record (against standard reference ranges) that the summary's plan never addresses.",
}

SUMMARY_ATTACKER_ROLE = """You are one adversarial reviewer in a gauntlet run against a
DISCHARGE SUMMARY submitted for this encounter. The record below has grounding sources —
TRANSCRIPT (ambient, speaker-labeled), NOTE (the clinician's SOAP note), and FHIR
(structured record) — and one section marked DISCHARGE SUMMARY (SUBMITTED), which is THE
PLAN UNDER ATTACK.

Your one job: find the documented way this discharge summary fails this patient, within
your assigned attack lane — with verbatim receipts — or concede.

Rules:
- Every quote must be copied VERBATIM from the record, and each quote's "section" must
  name its source: TRANSCRIPT, NOTE, FHIR, or SUMMARY. The strongest receipts pair a
  SUMMARY statement with the grounding it contradicts or ignores.
- The objection must be about how the SUMMARY fails the PATIENT — a concrete harm
  pathway (wrong value, dangerous med instruction, abnormal left unowned, commitment
  dropped), not style or completeness for its own sake.
- Propose exactly ONE concrete, placeable order or correction.
- If your lane genuinely has no documented failure, return NO_OBJECTION.

Respond with ONLY a JSON object, no prose around it:
{
  "objection": true,
  "claim": "<one sentence: what fails and how it harms this patient>",
  "quotes": [{"section": "TRANSCRIPT|NOTE|FHIR|SUMMARY", "quote": "<verbatim>"}],
  "missing": "<what the summary lacks or gets wrong>",
  "proposed_order": "<one concrete placeable order or correction>"
}
or: {"objection": false, "reason": "<why the lane is clean>"}"""

SUMMARY_JUDGE_NOTE = """Context for this review: the objection targets a DISCHARGE
SUMMARY submitted for an encounter; the transcript, SOAP note, and FHIR record are the
grounding truth. Adapt the tests: ADDRESSED = the summary itself covers it with an owner
and a date; MATERIALITY = would a reasonable clinician change the summary or add an
order BEFORE the patient leaves (values contradicting the grounding record, unsafe med
instructions given the documented labs, documented abnormals with no follow-up owner,
and dropped commitments ARE material; stylistic or completeness quibbles are NOT);
ACTIONABILITY = one concrete placeable order or correction."""

AMBIENT_JUDGE_NOTE = """Context for this review: this is AMBIENT DOCUMENTATION, not a
discharge plan. The documentation under attack is the SOAP note and after-visit summary;
the transcript and FHIR record are grounding truth. Adapt the tests: ADDRESSED = the
documentation itself covers or corrects it; MATERIALITY = would the clinician correct
the note/AVS or add an order BEFORE SIGNING if shown this (numeric values contradicting
FHIR, content attributed to the patient that is absent from the transcript, and
documented abnormals with no assessment ARE material; stylistic or completeness quibbles
are NOT); ACTIONABILITY = one concrete correction or order."""


def _name(concept: dict) -> str:
    if not isinstance(concept, dict):
        return "?"
    return concept.get("text") or (concept.get("coding") or [{}])[0].get("display", "?")


def _fhir_lines(resources) -> list[str]:
    # related_resources is {resourceType: [resource, ...]}
    flat = []
    if isinstance(resources, dict):
        for lst in resources.values():
            flat.extend(lst)
    else:
        flat = [r.get("resource", r) for r in resources or []]
    out = []
    for res in flat:
        t = res.get("resourceType", "?")
        if t == "Observation":
            name = _name(res.get("code", {}))
            when = str(res.get("effectiveDateTime", ""))[:10]
            if "valueQuantity" in res:
                v = res["valueQuantity"]
                out.append(f"Observation: {name} = {v.get('value')} {v.get('unit', '')} ({when})")
            elif res.get("component"):
                parts = "; ".join(
                    f"{_name(c.get('code', {}))} "
                    f"{(c.get('valueQuantity', {}) or {}).get('value', '?')} "
                    f"{(c.get('valueQuantity', {}) or {}).get('unit', '')}"
                    for c in res["component"])
                out.append(f"Observation: {name} = {parts} ({when})")
            elif "valueCodeableConcept" in res:
                out.append(f"Observation: {name} = "
                           f"{_name(res['valueCodeableConcept'])} ({when})")
        elif t in ("Condition", "Procedure", "DiagnosticReport", "AllergyIntolerance",
                   "Immunization", "CarePlan"):
            name = _name(res.get("code", res.get("vaccineCode", {})))
            status = (res.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")
                      if t == "Condition" else res.get("status", ""))
            out.append(f"{t}: {name} {status}".strip())
        elif t in ("MedicationRequest", "MedicationStatement"):
            name = _name(res.get("medicationCodeableConcept", {}))
            out.append(f"{t}: {name} [{res.get('status', '?')}]")
    return out


def compose_with_summary(key: str, summary_text: str):
    """Grounding sources + a submitted discharge summary as the section under attack."""
    chart, meta = load_encounter(key)
    # demote the note/AVS to grounding; the submitted summary is the sole target
    text = (chart.text
            .replace("## NOTE (SOAP note — THE DOCUMENTATION UNDER ATTACK)",
                     "## NOTE (SOAP note — grounding source)")
            .replace("## AVS (after-visit summary, patient-facing — ALSO UNDER ATTACK)",
                     "## AVS (after-visit summary — grounding source)"))
    text += ("\n\n## DISCHARGE SUMMARY (SUBMITTED) — THE PLAN UNDER ATTACK\n"
             + COMMENT_RE.sub("", summary_text).strip() + "\n")
    return Chart(path=f"encounter:{key}+summary", text=text, sections={}), meta


def load_encounter(key: str):
    data = json.loads(DATASET.read_text())
    needle = ALIASES.get(key, key).lower()
    rec = next((r for r in data
                if needle in (r.get("metadata", {}).get("visit_title", "")
                              + " " + r["id"]).lower()), None)
    if rec is None and key.isdigit():
        rec = data[int(key)]
    if rec is None:
        raise SystemExit(f"no encounter matches {key!r}; aliases: {list(ALIASES)}")
    meta = rec["metadata"]
    fhir = rec.get("encounter_fhir", {})
    lines = _fhir_lines(fhir.get("related_resources", []))
    text = "\n".join([
        f"# AMBIENT ENCOUNTER — {meta.get('visit_title', '?')} "
        f"({str(meta.get('date', ''))[:10]}; SYNTHETIC organizer dataset)",
        "",
        "## TRANSCRIPT (ambient, speaker-labeled — grounding source)",
        rec.get("transcript", ""),
        "",
        "## NOTE (SOAP note — THE DOCUMENTATION UNDER ATTACK)",
        rec.get("note", ""),
        "",
        "## AVS (after-visit summary, patient-facing — ALSO UNDER ATTACK)",
        rec.get("after_visit_summary", ""),
        "",
        f"## FHIR (structured record of this encounter — grounding source; "
        f"{len(lines)} entries)",
        *lines,
    ])
    text = COMMENT_RE.sub("", text)
    chart = Chart(path=f"encounter:{key}", text=text, sections={})
    return chart, meta
