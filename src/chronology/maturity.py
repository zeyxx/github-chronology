"""Independent evidence dimensions; never infer value or motive from activity."""
from .domain import digest

DIMENSIONS = ("implementation", "verification", "runtime", "deployment",
              "usage", "outcome", "learning")
STATUSES = ("OBSERVED", "REPORTED", "FAILED", "UNKNOWN")


def assess(subject, evidence):
    """Project explicitly scoped evidence statements, not automatic validation.

    Caller supplies reviewed observations; hashes identify statements, not truth.
    Preserve counterevidence, including evidence for different revisions.
    """
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("subject required")
    grouped = {k: {} for k in DIMENSIONS}
    for item in evidence:
        dimension = item.get("dimension")
        status = item.get("status")
        if dimension not in grouped or status not in STATUSES[:-1]:
            raise ValueError("invalid evidence dimension or status")
        if item.get("subject") != subject:
            raise ValueError("subject mismatch")
        for key in ("revision", "environment", "source", "claim", "method"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError("explicit scope and source required")
        grouped[dimension][digest(item)] = item
    result = {}
    for dimension, observations in grouped.items():
        rows = [observations[k] for k in sorted(observations)]
        result[dimension] = {"evidence": rows,
                             "status": "EVIDENCE_PRESENT" if rows else "UNKNOWN"}
    return {"schema": "g1-maturity-v1", "subject": subject,
            "dimensions": result, "utility": "UNASSESSED",
            "churn": "UNASSESSED", "motivation": "NOT_INFERRED",
            "limitations": ["Evidence is scoped to a revision and environment.",
                            "No promotion across dimensions or automatic utility inference.",
                            "Missing observation is not evidence of absence."]}


def review_churn(before, after, objective, evidence_refs):
    """Record a comparison opportunity, not a waste classification."""
    if not all(isinstance(x, str) and x.strip() for x in (before, after, objective)):
        raise ValueError("explicit comparison and objective required")
    if not isinstance(evidence_refs, list) or not evidence_refs or not all(
            isinstance(x, str) and x.strip() for x in evidence_refs):
        raise ValueError("evidence references required")
    return {"before": before, "after": after, "objective": objective,
            "evidence_refs": sorted(set(evidence_refs)),
            "status": "PENDING_REVIEW",
            "limitations": ["Rework can be useful learning, maintenance or risk reduction.",
                            "Measure outcome and cost; do not infer ego or motive."]}
