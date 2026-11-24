"""Authenticated-account repository and authored-item relationships.

No inferred identity, collaboration, originality or skill. Source records are
observations; a provider account is not a human identity.
"""
from datetime import datetime, timezone
import re
import subprocess
from urllib.parse import urlencode
from .domain import digest, record

LOGIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
ERRORS = (RuntimeError, ValueError, TypeError, KeyError, OSError, subprocess.TimeoutExpired)


def collect_account(read, max_pages=10):
    if not 1 <= max_pages <= 10:
        raise ValueError("max_pages must be in [1,10]")
    records = {}

    def one(key, path):
        try:
            pages = read(path, False)
            if len(pages) != 1 or not isinstance(pages[0], dict):
                raise ValueError("expected object")
            records[key] = record(path, pages)
            return pages[0]
        except ERRORS as exc:
            records[key] = record(path, [], "failed", type(exc).__name__)
            return None

    def scan(key, path, search=False):
        pages, seen, reason = [], set(), None
        for i in range(1, max_pages + 1):
            url = path + "&" + urlencode({"per_page": 100, "page": i})
            try:
                response = read(url, False)
                if len(response) != 1:
                    raise ValueError("expected one page")
                data = response[0]
                items = data["items"] if search else data
                if not isinstance(items, list) or len(items) > 100:
                    raise ValueError("invalid page")
                ids = [x["id"] for x in items]
                pages.append(data)
                if len(set(ids)) != len(ids) or seen.intersection(ids):
                    reason = "duplicate_ids"
                    break
                seen.update(ids)
                if search and data.get("incomplete_results") is not False:
                    reason = "search_incomplete"
                    break
                if len(items) < 100:
                    if search and data.get("total_count") != len(seen):
                        reason = "search_count_mismatch"
                    break
            except ERRORS as exc:
                reason = type(exc).__name__
                break
        else:
            reason = "page_budget_exhausted"
        records[key] = record(path, pages, "complete" if reason is None else
                              "partial" if pages else "failed", reason)

    account = one("account", "/user")
    if not account or type(account.get("id")) is not int or not LOGIN.fullmatch(account.get("login", "")):
        raise ValueError("authenticated account unavailable")
    login = account["login"]
    scan("owned", "/user/repos?affiliation=owner&visibility=all&sort=full_name&direction=asc")
    for page in records["owned"]["pages"]:
        for item in page:
            if (item.get("owner") or {}).get("id") != account["id"]:
                continue
            name = item.get("full_name", "")
            if not REPO.fullmatch(name) or type(item.get("id")) is not int:
                continue
            one("repo:" + str(item["id"]), "/repos/" + name)
    for kind in ("issue", "pr"):
        path = "/search/issues?" + urlencode({"q": f"is:{kind} author:{login} -user:{login}",
                                               "sort": "created", "order": "asc"})
        scan("external_" + kind, path, search=True)
    return {"schema": "g1-account-v1", "observed_at": datetime.now(timezone.utc).isoformat(),
            "records": records, "limits": ["Authenticated owned repositories only.",
                "External authored issue/PR search is indexed, bounded and permission-dependent.",
                "Reviews, comments, commits outside owned repos and non-GitHub sources not yet covered.",
                "No claim of complete account history."]}


def project_relations(bundle):
    records = bundle["records"]
    for r in records.values():
        if digest(r["pages"]) != r["sha256"]:
            raise ValueError("Evidence checksum mismatch")
    account = records["account"]["pages"][0]
    aid = "github:account:" + str(account["id"])
    nodes, edges, warnings = {}, {}, []
    counts = {"owned": 0, "forks": 0, "nonforks": 0, "fork_unknown": 0,
              "external_issues": 0, "external_prs": 0}

    def node(key, kind, label):
        nodes.setdefault(key, {"id": key, "kind": kind, "label": label})
        return key

    def edge(src, relation, dst, key, **details):
        r = records[key]
        value = {"source": src, "type": relation, "target": dst, "observed_at": bundle["observed_at"],
                 "evidence": {"record": key, "source": r["source"], "sha256": r["sha256"]},
                 "details": details}
        edges[digest(value)] = value

    node(aid, "account", account["login"])
    seen = set()
    for page in records["owned"]["pages"]:
        for item in page:
            rid = item.get("id")
            if type(rid) is not int or (item.get("owner") or {}).get("id") != account["id"] or rid in seen:
                continue
            seen.add(rid)
            counts["owned"] += 1
            key = "repo:" + str(rid)
            rr = records.get(key)
            meta = rr["pages"][0] if rr and rr["status"] == "complete" else {}
            if meta.get("id") != rid:
                meta = {}
            repo = node("github:repo:" + str(rid), "repository", item.get("full_name"))
            edge(aid, "OWNS", repo, "owned", limit="Observed ownership is not authorship.")
            if meta.get("fork") is True:
                counts["forks"] += 1
                for field, relation in (("parent", "FORKED_FROM"), ("source", "FORK_NETWORK_ROOT")):
                    upstream = meta.get(field) or {}
                    if type(upstream.get("id")) is int:
                        target = node("github:repo:" + str(upstream["id"]), "repository", upstream.get("full_name"))
                        edge(repo, relation, target, key, limit="Provider genealogy, not evidence of collaboration or original work.")
                    else:
                        warnings.append({"repo": repo, "reason": "missing_" + field})
            elif meta.get("fork") is False:
                counts["nonforks"] += 1
            else:
                counts["fork_unknown"] += 1
    external_seen = set()
    for kind in ("issue", "pr"):
        key = "external_" + kind
        for page in records[key]["pages"]:
            for item in page["items"]:
                url = item.get("repository_url", "")
                prefix = "https://api.github.com/repos/"
                name = url[len(prefix):] if url.startswith(prefix) else ""
                author = item.get("user") or {}
                actual = "pr" if "pull_request" in item else "issue"
                if actual != kind or author.get("id") != account["id"] or not REPO.fullmatch(name) or name.split("/")[0].lower() == account["login"].lower():
                    warnings.append({"record": key, "reason": "search_item_scope_or_type_mismatch"})
                    continue
                if type(item.get("id")) is not int or item["id"] in external_seen:
                    continue
                external_seen.add(item["id"])
                counts["external_prs" if kind == "pr" else "external_issues"] += 1
                obj = node("github:item:" + str(item["id"]), kind, item.get("html_url"))
                # Name-only external repository pointer; never equate it to stable ID without resolution.
                target = node("github:repo-name:" + name.lower(), "repository_reference", name)
                edge(aid, "OPENED_PR" if kind == "pr" else "OPENED_ISSUE", obj, key,
                     state=item.get("state"), created_at=item.get("created_at"),
                     limit="Provider-reported author; validity, autonomy and acceptance unknown.")
                edge(obj, "TARGETS_REPO", target, key)
    return {"schema": "g1-relations-v1", "counts": counts,
            "bundle_sha256": digest(bundle), "nodes": [nodes[k] for k in sorted(nodes)],
            "edges": [edges[k] for k in sorted(edges)], "warnings": warnings,
            "coverage": {k: {"status": v["status"], "error": v["error"]} for k,v in sorted(records.items())},
            "limits": bundle["limits"]}
