"""Severity tiers as pure LOOKUP against published lists — no model call, no judgment.

Sources encoded:
- ISMP List of High-Alert Medications in Acute Care Settings (class-level entries).
- ONC high-priority drug-drug interaction list (Phansalkar et al., JAMIA 2012) —
  interaction classes for which alerts should always fire.
"""

ISMP_HIGH_ALERT = {
    "anticoagulant": ["warfarin", "heparin", "apixaban", "rivaroxaban", "dabigatran",
                      "enoxaparin", "inr"],
    "insulin": ["insulin"],
    "opioid": ["morphine", "oxycodone", "hydromorphone", "fentanyl", "methadone"],
    "chemotherapy": ["methotrexate"],
    "digoxin (class: inotropic)": ["digoxin"],
}

ONC_HIGH_PRIORITY_DDI = [
    ("warfarin", "trimethoprim", "warfarin + TMP-SMX (potentiation, bleeding)"),
    ("warfarin", "tmp-smx", "warfarin + TMP-SMX (potentiation, bleeding)"),
    ("warfarin", "sulfamethoxazole", "warfarin + TMP-SMX (potentiation, bleeding)"),
    ("warfarin", "amiodarone", "warfarin + amiodarone"),
    ("warfarin", "fluconazole", "warfarin + azole antifungal"),
    ("digoxin", "amiodarone", "digoxin + amiodarone"),
    ("opioid", "benzodiazepine", "opioid + benzodiazepine (CNS/respiratory depression)"),
]

TIERS = {1: "TIER 1 · CRITICAL", 2: "TIER 2 · HIGH", 3: "TIER 3 · MODERATE"}


def classify(finding: dict) -> dict:
    """Attach tier + citation to a finding by lookup against its text content."""
    # Title + gap + order only: claims and receipts mention high-alert meds
    # incidentally (everyone cites the warfarin context) and would over-tier.
    blob = " ".join(str(finding.get(k, "")) for k in
                    ("id", "title", "missing", "proposed_order")).lower()

    for a, b, label in ONC_HIGH_PRIORITY_DDI:
        if a in blob and b in blob:
            return finding | {"tier": 1, "tier_label": TIERS[1],
                              "citation": f"ONC high-priority DDI list: {label}"}
    for cls, names in ISMP_HIGH_ALERT.items():
        if any(n in blob for n in names):
            return finding | {"tier": 1, "tier_label": TIERS[1],
                              "citation": f"ISMP high-alert medications (acute care): {cls}"}
    if any(w in blob for w in ("mismatch", "discrepan", "contradict", "hallucinat",
                               "not in transcript", "grounding", "drift",
                               "unaddressed", "not addressed", "never addressed")):
        return finding | {"tier": 2, "tier_label": TIERS[2],
                          "citation": "Documentation contradicts its grounding source "
                                      "(ambient note-error class)"}
    if any(w in blob for w in ("pending", "culture", "no owner", "ownership",
                               "routing", "result")):
        return finding | {"tier": 2, "tier_label": TIERS[2],
                          "citation": "Unowned pending result at transition of care "
                                      "(Roy et al., Ann Intern Med 2005 class)"}
    if any(w in blob for w in ("weight", "diuretic", "dry weight", "volume")):
        return finding | {"tier": 2, "tier_label": TIERS[2],
                          "citation": "Documented specialist target not operationalized "
                                      "at discharge (HF readmission driver)"}
    return finding | {"tier": 3, "tier_label": TIERS[3],
                      "citation": "Surviving objection outside encoded high-risk classes"}
