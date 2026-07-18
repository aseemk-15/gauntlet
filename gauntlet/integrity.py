"""Evidence integrity: code-level guarantee that no fabricated or altered quote can
render. Model output is never trusted for receipts — every quote on every final finding
is mechanically re-verified verbatim against the source text (the cluster step re-emits
quotes and could drift them). A drifted quote is replaced by the original attacker's
already-verified quote when possible, else dropped; a finding with zero verified
receipts cannot render.

What this guarantees: every receipt shown is verbatim-present in the chart, enforced in
code. What it does not guarantee: the truth of the model-authored CLAIM above the
receipts — that is adversarially judged, then decided by the clinician.
"""


def _verified_quotes(chart, quotes: list) -> list:
    good = []
    for q in quotes or []:
        if not isinstance(q, dict):
            continue
        frags = [f.strip() for f in str(q.get("quote", "")).split("...") if f.strip()]
        if frags and all(chart.contains_verbatim(f) for f in frags):
            good.append(q)
    return good


def enforce_receipts(run, chart, findings: list[dict],
                     survivors: list[dict] | None = None) -> list[dict]:
    """Verify every finding's quotes; recover from member attackers' original quotes
    on failure; drop findings that end up with no verified receipt."""
    originals = {}
    for v in survivors or []:
        originals[v.get("agent")] = (v.get("objection") or {}).get("quotes", [])

    kept = []
    for f in findings:
        good = _verified_quotes(chart, f.get("quotes"))
        dropped = len(f.get("quotes") or []) - len(good)
        if not good:  # recover from the finders' own judge-verified quotes
            pool = []
            for m in f.get("members", []):
                pool.extend(_verified_quotes(chart, originals.get(m, [])))
            good = pool[:3]
        if not good:
            run.emit("receipts_rejected", finding=f.get("id"),
                     reason="no verifiable verbatim receipt — finding dropped")
            continue
        f["quotes"] = good
        f["receipts_verified"] = True
        if dropped:
            run.emit("receipt_repaired", finding=f.get("id"), dropped=dropped,
                     kept=len(good))
        kept.append(f)
    run.emit("receipts_enforced", findings=len(kept),
             note="every rendered quote mechanically verified verbatim")
    return kept
