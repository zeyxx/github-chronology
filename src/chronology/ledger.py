"""Conservative multi-PR claim candidates; no competence or utility inference."""
from .domain import canonical, digest


def build_ledger(projections):
    """One ledger entry per observed merge or exact-SHA successful check.

    Keep conflicting observations separate and retain provenance and limits.
    Never mark a CV claim validated; semantic interpretation remains external.
    """
    entries = {}
    coverage = {}
    for p in projections:
        key = p["evidence_bundle_sha256"]
        coverage[key] = {"subject": p["subject"], "records": p["coverage"],
                         "warnings": p["warnings"]}
        for f in p["facts"]:
            value = f["value"]
            if f["kind"] == "delivery" and value.get("merged") is True and value.get("merge_sha"):
                statement = f"PR {p['subject']} reported merged at commit {value['merge_sha']}."
            elif f["kind"] == "check" and value.get("status") == "completed" and value.get("conclusion") == "success":
                statement = f"PR {p['subject']}: check {value.get('name')!r} reported success at {value['sha']}."
            else:
                continue
            entry = {"subject": p["subject"], "claim_type": f["kind"],
                     "candidate_statement": statement, "source_fact": f,
                     "evidence_bundle_sha256": key, "status": "PENDING_HUMAN_REVIEW",
                     "attribution": "UNKNOWN_INDIVIDUAL_AUTONOMY",
                     "limitations": [f["limit"], "Not a demonstrated skill or personal outcome.",
                                     "Inspect coverage and conflicting observations before reuse."],
                     "cv_disposition": "UNDECIDED"}
            entries[digest(entry)] = entry
    return {"schema": "g1-ledger-v1", "coverage": coverage,
            "entries": [{"id": k, **entries[k]} for k in sorted(entries)],
            "human_review_required": True}
