"""Pure evidence projection. No network, clock or file operations."""
import hashlib
import json

VERSION = "g1-pr-v1"


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def record(source, pages, status="complete", error=None):
    return {"source": source, "pages": pages, "status": status,
            "error": error, "sha256": digest(pages)}


def project(bundle):
    """Derive candidates, never skills or utility, from a frozen evidence bundle."""
    records = bundle["records"]
    pr = records["pr"]["pages"][0]
    head = pr["head"]["sha"]
    merge = pr.get("merge_commit_sha") if pr.get("merged") is True else None
    facts, timeline, warnings = [], [], []

    def ref(key):
        r = records[key]
        return {"source": r["source"], "sha256": r["sha256"], "record": key}

    def add(key, kind, value, limit):
        facts.append({"kind": kind, "value": value, "evidence": [ref(key)], "limit": limit})

    def items(key, field=None):
        r = records.get(key)
        if not r:
            return []
        result = {}
        for page in r["pages"]:
            for item in (page[field] if field else page):
                identity = item.get("id", item.get("sha", item.get("filename")))
                if identity is None:
                    identity = digest(item)
                # Distinct conflicting versions are not collapsed.
                result[(str(identity), digest(item))] = item
        return [result[k] for k in sorted(result)]

    def event(key, kind, date, value):
        if date:
            timeline.append({"kind": kind, "source_time": date,
                             "value": value, "evidence": [ref(key)]})

    add("pr", "delivery", {"merged": pr.get("merged"), "head_sha": head,
                           "merge_sha": merge, "title": pr.get("title")},
        "Merge is not deployment, adoption or utility.")
    add("pr", "provider_author", (pr.get("user") or {}).get("login"),
        "Account authorship does not prove individual contribution or autonomy.")
    event("pr", "pr.created", pr.get("created_at"), pr["number"])
    event("pr", "pr.merged", pr.get("merged_at") if merge else None, pr["number"])
    commits = items("commits")
    for c in commits:
        meta = c.get("commit") or {}
        add("commits", "commit", {"sha": c["sha"],
            "author_login": (c.get("author") or {}).get("login"),
            "message": meta.get("message"),
            "parents": [p["sha"] for p in c.get("parents", [])]},
            "Commit text and author metadata are source assertions, not verified human authorship.")
        event("commits", "commit.authored_timestamp", (meta.get("author") or {}).get("date"), c["sha"])
    for f in items("files"):
        add("files", "changed_file", {"path": f["filename"], "status": f.get("status")},
            "Changed path does not establish quality, security or skill.")
    for r in items("reviews"):
        add("reviews", "review", {"id": r["id"], "state": r.get("state"),
            "reviewer": (r.get("user") or {}).get("login"), "commit_sha": r.get("commit_id")},
            "Reviewer identity or approval alone does not establish independent review.")
        event("reviews", "review.submitted", r.get("submitted_at"), r["id"])
    for key, sha in (("checks_head", head), ("checks_merge", merge)):
        if not sha or key not in records:
            continue
        for c in items(key, "check_runs"):
            if c.get("head_sha") != sha:
                warnings.append({"record": key, "reason": "check_sha_mismatch", "id": c.get("id")})
                continue
            add(key, "check", {"id": c["id"], "name": c.get("name"), "sha": sha,
                "status": c.get("status"), "conclusion": c.get("conclusion")},
                "Check result scoped to exact commit; test contents and deployment not established.")
            event(key, "check.completed", c.get("completed_at"), c["id"])

    # Deterministic even for repeated identical input.
    facts.sort(key=canonical)
    timeline.sort(key=lambda e: (e["source_time"], canonical(e)))
    return {"schema": VERSION, "subject": bundle["subject"],
            "evidence_bundle_sha256": digest(bundle), "facts": facts, "timeline": timeline,
            "coverage": {k: {"status": r["status"], "error": r["error"], "evidence": ref(k)}
                         for k, r in sorted(records.items())},
            "warnings": sorted(warnings, key=canonical),
            "attribution": "UNKNOWN_INDIVIDUAL_AUTONOMY",
            "outcome": "UNKNOWN", "utility": "UNKNOWN",
            "cv_candidates": [], "human_review_required": True}
