"""Fix loop: survivor cards state GAPS; the clinician decides; an agent emits each
accepted decision as a structured order artifact. No mock CPOE — the artifact IS the
output. Accepting the anticoag/volume/results fixes authors an amendment that
SUPERSEDES the discharge med list (append-only addenda create contradictions the swarm
correctly catches — see DESIGN.md).
"""
import json
import time
from pathlib import Path

# Fix content for the Eleanor demo chart, authored from the chart asset's disclosed
# amendment authoring spec (see README Disclosures). Keyed by finding keywords.
FIXES = {
    "anticoag": {
        "match": ("inr", "warfarin", "anticoag"),
        "orders": [
            "LAB: INR + BMP (Cr, K+) draw 07/18, results to Dr. Patel + coumadin clinic same-day",
            "LAB: post-course INR 07/23; coumadin clinic manages dosing through 07/26",
            "EDUCATION: bleeding precautions reviewed with daughter (documented)",
        ],
    },
    "volume": {
        "match": ("weight", "volume", "diuretic", "dry"),
        "orders": [
            "MED: furosemide 40 mg PO BID x5 days, reassess at 07/21 telehealth vs home dose",
            "MONITOR: daily home weights, call for gain >1.5 kg; STOP-LOSS: hold diuretic + call if weight <75 kg or SBP <100",
            "REFERRAL: home health RN visit 07/18; cardiology appointment moved up to 07/24",
        ],
    },
    "cultures": {
        "match": ("culture", "pending", "result"),
        "orders": [
            "ROUTING: blood cultures x2 (07/14) — named result owner Dr. Patel; micro pages hospitalist on any growth",
            "DOC: discharge summary updated to note pending cultures + de-escalation plan",
        ],
    },
}

AMENDMENT = """
## AMENDMENT 1 — Discharge Orders (07/16 16:45, Dr. Patel) — SUPERSEDES 14:32 plan

This amendment is the discharge plan of record. The 07/16 14:32 medication list and
follow-up plan are VOID and replaced in full below.

### Medication List of Record (07/16 16:45, Dr. Patel)
- warfarin 5 mg PO daily — CONTINUE; coumadin clinic manages dosing through 07/26
- TMP-SMX DS 800-160 mg PO BID — CONTINUE through 07/20 (7-day course from 07/13)
- furosemide 40 mg PO BID x5 days (through 07/21), then reassess at 07/21 telehealth
  visit vs home dose 40 mg daily
- metoprolol succinate 50 mg PO daily — CONTINUE
- acetaminophen 500 mg PRN

### Anticoagulation monitoring (owner: Dr. Patel, with coumadin clinic)
- INR drawn 07/18 (2 days post-discharge) WITH BMP (Cr, K+); results routed to Dr. Patel
  and coumadin clinic same day. Post-course INR 07/23. Coumadin clinic manages warfarin
  dosing through 07/26. Daughter instructed on bleeding precautions (documented 07/16).
- Repeat BMP at the 07/21 telehealth visit if K+ >5.0 or Cr rises >0.3 from baseline.

### Volume management (owner: Dr. Patel; cardiology 07/24)
- Daily home weights; patient/daughter call for gain >1.5 kg. STOP-LOSS: hold diuretic
  and call if weight <75 kg or SBP <100. Home health RN visit 07/18. Patient is not
  expected to reach dry weight (74.3 kg) before discharge — deliberate outpatient
  diuresis strategy per cardiology recommendation; cardiology appointment moved up to
  07/24.

### Follow-up appointments — ALL SCHEDULED BEFORE DISCHARGE (booking documented)
- 07/18 home health RN visit (agency confirmed).
- 07/21 telehealth visit with Dr. Patel's clinic for diuretic reassessment and BMP
  review — BOOKED by discharge coordinator 07/16; date/time confirmed at bedside with
  patient and daughter; instructions given. Owner: Dr. Patel.
- 07/24 cardiology (Dr. Kim; moved up from 09/2026); daughter confirmed transport.
- PCP visit scheduled 07/28 by discharge coordinator (replaces "patient to schedule").

### Pending results (owner: Dr. Patel)
- Blood cultures x2 drawn 07/14 (no growth to date, day 2) remain pending at discharge.
  Named result owner: Dr. Patel. Routing order placed: micro pages hospitalist on any
  growth; de-escalation per course completion if no growth. Discharge summary updated to
  note pending cultures and the contingency plan; daughter has callback contact.
"""


def match_fix(finding: dict) -> str | None:
    # id + title only — claims mention the warfarin context incidentally and mis-match
    blob = (str(finding.get("id", "")) + " " + str(finding.get("title", ""))).lower()
    for name, fix in FIXES.items():
        if any(m in blob for m in fix["match"]):
            return name
    return None


def render_card(f: dict, total: int = 30, width: int = 78) -> str:
    bar = "─" * width
    lines = [bar,
             f"█ {f.get('tier_label', '?')}  ·  {f['title']}",
             f"  found independently by {f.get('found_by', '?')} of {total}"
             + ("  ·  SINGLE-SOURCE" if f.get("found_by") == 1 else ""),
             f"  cite: {f.get('citation', '')}",
             f"  CLAIM   {f.get('claim', '')}",
             f"  GAP     {f.get('missing', '')}"]
    if f.get("receipts_verified"):
        lines.append("  RECEIPTS machine-verified verbatim against source ✓")
    for q in f.get("quotes", [])[:3]:
        if isinstance(q, dict):
            lines.append(f"  RECEIPT [{q.get('section', '?')}] \"{q.get('quote', '')[:90]}\"")
    lines.append(f"  ORDER?  {f.get('proposed_order', '')}")
    lines.append(bar)
    return "\n".join(lines)


def apply_fixes(run, chart, findings: list[dict], decisions: dict[str, str]) -> dict:
    """decisions: finding id -> 'accept' | 'dismiss:<rationale>'. Emits order artifacts,
    authors the superseding amendment, writes the amended chart. Returns manifest."""
    orders, fixed_ids, dismissed, applied = [], [], [], set()
    for f in findings:
        d = decisions.get(f["id"], "accept")
        if d.startswith("dismiss"):
            rationale = d.partition(":")[2] or "clinician judgment"
            dismissed.append({"finding": f["id"], "rationale": rationale})
            run.emit("dismissed", finding=f["id"], rationale=rationale)
            continue
        fix = match_fix(f)
        if fix is None:
            dismissed.append({"finding": f["id"],
                              "rationale": "no canned fix — clinician to address manually"})
            run.emit("dismissed", finding=f["id"], rationale="no matching fix template")
            continue
        fixed_ids.append(f["id"])
        if fix in applied:  # same fix domain already ordered — don't double-emit
            run.emit("covered", finding=f["id"], by=fix)
            continue
        applied.add(fix)
        for text in FIXES[fix]["orders"]:
            order = {"order_id": f"ORD-{len(orders)+1:03d}", "finding": f["id"],
                     "order": text, "status": "transmitted",
                     "at": time.strftime("%Y-%m-%d %H:%M:%S")}
            orders.append(order)
            run.emit("order_emitted", order_id=order["order_id"], finding=f["id"],
                     order=text[:90])

    amended_text = chart.text.rstrip() + "\n" + AMENDMENT
    amended_path = run.dir / "amended-chart.md"
    amended_path.write_text(amended_text)
    manifest = {"fixed": fixed_ids, "dismissed": dismissed, "orders": orders,
                "amended_chart": str(amended_path)}
    (run.dir / "orders.json").write_text(json.dumps(manifest, indent=2))
    run.emit("amendment_written", supersedes="14:32 med list + follow-up plan",
             fixed=len(fixed_ids), orders=len(orders))
    return manifest
