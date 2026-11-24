"""Bounded historical inventory; default-branch commits and PRs, not all refs."""
from datetime import datetime, timezone
from .domain import record


def inventory(repo, read, max_pages=20):
    if not 1 <= max_pages <= 100:
        raise ValueError("max_pages must be in [1,100]")
    root = "/repos/" + repo
    records = {}

    def scan(key, endpoint, identity):
        pages, seen, reason = [], set(), None
        for n in range(1, max_pages + 1):
            url = endpoint + ("&" if "?" in endpoint else "?") + f"per_page=100&page={n}"
            try:
                raw = read(url, False)
                if len(raw) != 1 or not isinstance(raw[0], list):
                    raise ValueError("expected array page")
                page = raw[0]
                ids = [item[identity] for item in page]
                if len(page) > 100:
                    raise ValueError("unexpected page size")
                pages.append(page)
                if len(set(ids)) != len(ids) or seen.intersection(ids):
                    reason = "duplicate_identity_across_pages"
                    break
                seen.update(ids)
                if len(page) < 100:
                    break
            except (RuntimeError, ValueError, TypeError, KeyError, OSError) as exc:
                reason = type(exc).__name__
                break
        else:
            reason = "page_budget_exhausted"
        status = "complete" if reason is None else "partial" if pages else "failed"
        records[key] = record(endpoint, pages, status, reason)
        return len(seen)

    # Freeze default branch tip before commit enumeration; PR inventory remains live.
    try:
        meta = read(root, False)
        if len(meta) != 1:
            raise ValueError("repository metadata missing")
        branch = meta[0]["default_branch"]
        from urllib.parse import quote
        tip = read(root + "/commits/" + quote(branch, safe=""), False)
        if len(tip) != 1:
            raise ValueError("branch tip missing")
        sha = tip[0]["sha"]
        if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("invalid SHA")
        records["repo"] = record(root, meta)
        records["tip"] = record(root + "/commits/" + quote(branch, safe=""), tip)
        commits = scan("commits", root + "/commits?sha=" + sha, "sha")
    except (RuntimeError, ValueError, TypeError, KeyError, OSError) as exc:
        records["tip"] = record(root, [], "failed", type(exc).__name__)
        commits = None
    prs = scan("prs", root + "/pulls?state=all&sort=created&direction=asc", "number")
    return {"schema": "g1-inventory-v1", "subject": repo,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "records": records, "counts": {"prs": prs, "default_branch_commits": commits},
            "limits": ["PR list is not an atomic snapshot.",
                       "Default-branch ancestry excludes unmerged branch-only commits, deleted refs and inaccessible data.",
                       "A completed endpoint does not prove account-wide completeness."]}


def select_prs(inv, budget):
    """Temporal sample with merged/unmerged distinction. Not a utility ranking."""
    if not 1 <= budget <= 100:
        raise ValueError("budget must be in [1,100]")
    prs = {}
    for page in inv["records"]["prs"]["pages"]:
        for pr in page:
            prs.setdefault(pr["number"], pr)
    ordered = sorted(prs.values(), key=lambda p: (p.get("created_at") or "", p["number"]))
    if len(ordered) <= budget:
        chosen = ordered
    else:
        # Cover chronological range; reserve one slot for a nonmerged PR if feasible.
        chosen = []
        nonmerged = [p for p in ordered if not p.get("merged_at")]
        if budget >= 2 and nonmerged:
            chosen.append(nonmerged[-1])
        pool = [p for p in ordered if p not in chosen]
        k = budget - len(chosen)
        if k == 1:
            chosen.append(pool[-1])
        elif k > 1:
            chosen.extend(pool[i * (len(pool)-1) // (k-1)] for i in range(k))
    numbers = sorted(p["number"] for p in chosen)
    return {"method": "temporal_spread_plus_nonmerged_v1", "numbers": numbers,
            "observed_prs": len(ordered), "not_selected": len(ordered)-len(numbers),
            "limit": "Sampling by time/state, not significance, skill or utility; review and override selection."}
