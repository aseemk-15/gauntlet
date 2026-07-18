"""Attack-lane taxonomy. Each lane is one way discharge plans fail patients."""

DISCHARGE_LANES = {
    "drug-interactions": "Interactions between medications on the discharge list (including newly started drugs against chronic ones), and any monitoring those interactions demand that the plan does not order.",
    "anticoagulation": "Anticoagulation management: dosing, monitoring labs, follow-up ownership, bleeding-risk changes introduced during this admission.",
    "volume-status": "Volume status and diuresis: discharge weight vs any documented target or dry weight, diuretic dosing vs trajectory, weight-monitoring plans.",
    "renal-electrolytes": "Renal function and electrolytes: renal dosing of each med, potassium/creatinine risks, labs promised or implied but not ordered post-discharge.",
    "pending-results": "Results still pending at discharge: cultures, labs, imaging — who owns each result, how it routes, whether the discharge summary mentions it.",
    "follow-up-continuity": "Follow-up appointments and continuity: are the intervals safe for what happened this admission, is anything left to 'patient to schedule' that is load-bearing?",
    "med-rec-contradictions": "Internal contradictions in the medication record: does any list, note, or amendment disagree with another about drug, dose, or duration?",
    "outside-records": "Buried outside records: faxed/scanned/OCR'd documents (specialist letters, prior records) containing targets or warnings the discharge plan ignores.",
    "care-coordination": "Care coordination and access: transport, home support, equipment, cost/coverage constraints documented in the chart that the plan's follow-up depends on.",
    "infection-course": "The infection course: antibiotic choice vs sensitivities, course duration, de-escalation, response monitoring, and what happens after the course ends.",
}

AGENTS_PER_LANE = 3
