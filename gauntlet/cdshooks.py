"""CDS Hooks export: survivor findings → spec-shaped cards, the payload an EHR
order-sign hook (e.g. Epic CDS Hooks) would render at discharge signing. Written to
runs/<dir>/cds-cards.json on every run — the integration story, inspectable.
"""
import json
import uuid

INDICATOR = {1: "critical", 2: "warning", 3: "info"}


def _uid(kind: str, fid: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"gauntlet:{kind}:{fid}"))


def export_cards(run, findings: list[dict]) -> dict:
    cards = []
    for f in findings:
        detail = [f.get("claim", ""), ""]
        detail += [f"> **[{q.get('section', '?')}]** \"{q.get('quote', '')}\""
                   for q in f.get("quotes", []) if isinstance(q, dict)]
        detail += ["", f"*{f.get('citation', '')}*",
                   f"*Found independently by {f.get('found_by', '?')} reviewers; "
                   f"receipts machine-verified verbatim. Not a safety certification.*"]
        cards.append({
            "uuid": _uid("card", str(f.get("id"))),
            "summary": str(f.get("title", ""))[:140],
            "indicator": INDICATOR.get(f.get("tier"), "warning"),
            "detail": "\n".join(detail),
            "source": {"label": "The Gauntlet — adversarial discharge review",
                       "topic": {"display": str(f.get("id", "finding"))}},
            "suggestions": [{
                "uuid": _uid("suggestion", str(f.get("id"))),
                "label": str(f.get("proposed_order", "Review finding"))[:200],
                "actions": [{"type": "create",
                             "description": str(f.get("proposed_order", ""))}],
            }],
            "overrideReasons": [{"code": "clinician-judgment",
                                 "display": "Clinician judgment — rationale documented"}],
        })
    payload = {"cards": cards}
    (run.dir / "cds-cards.json").write_text(json.dumps(payload, indent=2))
    run.emit("cds_export", cards=len(cards), file="cds-cards.json")
    return payload
