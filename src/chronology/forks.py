"""Pinned fork comparisons, bounded branch discovery, no attribution inference."""
from datetime import datetime, timezone
from urllib.parse import quote
import re
import subprocess
from .domain import record

NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
SHA = re.compile(r"[a-f0-9]{40}")
ERRORS = (RuntimeError, ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired)


def collect_fork(repo, read, max_branches=20):
    if not NAME.fullmatch(repo) or not 1 <= max_branches <= 100:
        raise ValueError("invalid repository or branch budget")
    records = {}
    root = "/repos/" + repo

    def take(key, url, array=False):
        try:
            pages = read(url, False)
            if len(pages) != 1 or not isinstance(pages[0], list if array else dict):
                raise ValueError("invalid response")
            records[key] = record(url, pages)
            return pages[0]
        except ERRORS as exc:
            records[key] = record(url, [], "failed", type(exc).__name__)
            return None

    meta = take("repo", root)
    if not meta or meta.get("fork") is not True:
        raise ValueError("fork relation unavailable")
    parent = meta.get("parent") or {}
    name = parent.get("full_name", "")
    if not NAME.fullmatch(name):
        raise ValueError("parent unavailable")
    # Read parent tip separately; never use moving branch names in comparisons.
    pm = take("parent", "/repos/" + name)
    if not pm or pm.get("id") != parent.get("id"):
        raise ValueError("parent identity unavailable")
    default = meta["default_branch"]
    parent_branch = pm["default_branch"]
    pt = take("parent_tip", "/repos/" + name + "/commits/" + quote(parent_branch, safe=""))
    ft = take("fork_tip", root + "/commits/" + quote(default, safe=""))
    if not pt or not ft:
        raise ValueError("default branch tip unavailable")
    parent_sha, fork_sha = pt["sha"], ft["sha"]
    if not SHA.fullmatch(parent_sha) or not SHA.fullmatch(fork_sha):
        raise ValueError("invalid tip SHA")
    page = take("branches", root + "/branches?per_page=100&page=1", True)
    selected = [(default, fork_sha)]
    seen = {default}
    partial = page is None
    if page is not None:
        for item in sorted(page, key=lambda x: x.get("name", "")):
            branch = item.get("name")
            sha = (item.get("commit") or {}).get("sha", "")
            if not isinstance(branch, str) or not SHA.fullmatch(sha):
                partial = True
                continue
            if branch == default:
                if sha != fork_sha:
                    partial = True
                continue
            if branch in seen:
                partial = True
                continue
            seen.add(branch)
            if len(selected) < max_branches:
                selected.append((branch, sha))
            else:
                partial = True
        if len(page) >= 100:
            partial = True
    result = []
    cache = {}
    for branch, sha in selected:
        key = "compare:" + sha
        if sha not in cache:
            left = quote(pm["owner"]["login"] + ":" + parent_sha, safe=":")
            right = quote(meta["owner"]["login"] + ":" + sha, safe=":")
            c = take(key, root + "/compare/" + left + "..." + right + "?per_page=1")
            valid = c is not None and (c.get("base_commit") or {}).get("sha") == parent_sha
            valid = valid and all(type(c.get(k)) is int and c[k] >= 0 for k in ("ahead_by", "behind_by"))
            if not valid:
                if c is not None:
                    records[key]["status"] = "partial"
                    records[key]["error"] = "comparison_scope_or_count_invalid"
                cache[sha] = None
                partial = True
            else:
                cache[sha] = {"ahead": c["ahead_by"], "behind": c["behind_by"],
                              "merge_base": (c.get("merge_base_commit") or {}).get("sha"),
                              "status": c.get("status")}
        result.append({"branch": branch, "sha": sha, "comparison": cache[sha], "evidence": key})
    return {"schema": "g1-fork-v1", "observed_at": datetime.now(timezone.utc).isoformat(),
            "repo": repo, "parent": name, "parent_sha": parent_sha, "branches": result,
            "partial": partial, "records": records,
            "limits": ["Branch listing is a bounded first page; default tip captured separately.",
                       "Compare counters are reachability differences, not unique changes or personal contributions.",
                       "Never sum ahead counts across branches; ancestry may overlap.",
                       "Only one commit payload per comparison requested; no exhaustive commit enumeration.",
                       "No upstream PR acceptance or patch-equivalence inference."]}
