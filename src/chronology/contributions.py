"""Separate provider lifecycle from human-reviewed technical dispositions."""
from datetime import datetime, timezone
import re
import subprocess
from .domain import digest, record

REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
DISPOSITIONS = {"ACKNOWLEDGED", "NEEDS_INFO", "ACCEPTED", "DUPLICATE",
                "OUT_OF_SCOPE", "REJECTED", "NOT_REPRODUCIBLE", "FIX_REPORTED"}
ERRORS = (RuntimeError, ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired)


def collect_issue(repo, number, read):
    if not REPO.fullmatch(repo) or type(number) is not int or number < 1:
        raise ValueError("invalid issue")
    path = f"/repos/{repo}/issues/{number}"
    issue = read(path, False)
    if len(issue) != 1 or issue[0].get("number") != number or "pull_request" in issue[0]:
        raise ValueError("not the requested issue")
    records = {"issue": record(path, issue)}
    try:
        pages = read(path + "/comments?per_page=100", True)
        if not pages or not all(isinstance(p, list) for p in pages):
            raise ValueError("invalid comments")
        ids = [c["id"] for page in pages for c in page]
        partial = len(set(ids)) != len(ids) or len(ids) != issue[0].get("comments")
        records["comments"] = record(path + "/comments?per_page=100", pages,
                                     "partial" if partial else "complete",
                                     "comment_count_or_duplicate" if partial else None)
    except ERRORS as exc:
        records["comments"] = record(path + "/comments", [], "failed", type(exc).__name__)
    return {"schema": "g1-issue-v1", "subject": f"{repo}#{number}",
            "observed_at": datetime.now(timezone.utc).isoformat(), "records": records}


def classify_issue(bundle, annotation=None):
    """Never infer technical acceptance from state, labels or keyword matches.

    Annotation is an explicitly human-reviewed interpretation of one owner/member
    comment. It must bind to this exact bundle; split mixed findings externally.
    """
    records = bundle["records"]
    for r in records.values():
        if digest(r["pages"]) != r["sha256"]:
            raise ValueError("evidence checksum mismatch")
    issue = records["issue"]["pages"][0]
    author = (issue.get("user") or {}).get("id")
    comments = {c["id"]: c for p in records["comments"]["pages"] for c in p}
    responses = [c["id"] for c in comments.values()
                 if author is not None and (c.get("user") or {}).get("id") not in (None, author)]
    partial = any(r["status"] != "complete" for r in records.values())
    result = {"schema": "g1-contribution-v1", "subject": bundle["subject"],
              "bundle_sha256": digest(bundle), "lifecycle": issue.get("state"),
              "closure_reason": issue.get("state_reason"), "partial": partial,
              "response_observation": "OTHER_ACCOUNT_RESPONDED" if responses else
                  "UNKNOWN" if partial else "NO_OTHER_COMMENT_OBSERVED",
              "other_comment_ids": sorted(responses), "disposition": "UNASSESSED",
              "fix_evidence": "UNVERIFIED", "impact": "UNKNOWN",
              "attribution": "PROVIDER_AUTHORSHIP_ONLY",
              "review_required": True}
    if annotation is None:
        return result
    if annotation.get("bundle_sha256") != digest(bundle):
        raise ValueError("annotation is not bound to this bundle")
    state = annotation.get("disposition")
    comment = comments.get(annotation.get("comment_id"))
    if state not in DISPOSITIONS or not comment or comment["id"] not in responses:
        raise ValueError("missing independent response or invalid disposition")
    if comment.get("author_association") not in ("OWNER", "MEMBER", "COLLABORATOR"):
        raise ValueError("authority requires manual resolution outside this probe")
    if not all(isinstance(annotation.get(k), str) and annotation[k].strip()
               for k in ("reviewer", "scope", "rationale")):
        raise ValueError("reviewer, scope and rationale required")
    result.update(disposition=state, reviewed_interpretation=annotation,
                  response_association=comment["author_association"],
                  fix_evidence="MAINTAINER_REPORTED" if state == "FIX_REPORTED" else "UNVERIFIED")
    # No automatic FIX_VERIFIED: commit and regression evidence need a separate review.
    return result
