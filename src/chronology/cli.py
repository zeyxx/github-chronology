"""G1: collect an authorized PR and replay its evidence locally."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from .domain import canonical, digest, project, record
from .ledger import build_ledger

NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
SHA = re.compile(r"[a-f0-9]{40}")


def parse_pages(raw):
    decoder = json.JSONDecoder()
    pages = []
    while raw.strip():
        raw = raw.lstrip()
        obj, end = decoder.raw_decode(raw)
        pages.append(obj)
        raw = raw[end:]
    if not pages:
        raise ValueError("empty response")
    return pages


def gh_read(endpoint, paginated):
    cmd = ["gh", "api", "--method", "GET", "--hostname", "github.com",
           "-H", "X-GitHub-Api-Version: 2022-11-28"]
    if paginated:
        cmd.append("--paginate")
    result = subprocess.run(cmd + [endpoint], capture_output=True, text=True,
                            timeout=180, check=False)
    if result.returncode:
        raise RuntimeError("gh API request failed")
    return parse_pages(result.stdout)


def collect(repo, number, read=gh_read):
    if not NAME.fullmatch(repo) or number < 1:
        raise ValueError("Expected OWNER/REPO and positive PR number")
    start = time.monotonic()
    root = "/repos/" + repo
    prpath = root + "/pulls/" + str(number)
    records = {}

    def take(key, path, paginated=True, field=None, cap=None):
        try:
            pages = read(path, paginated)
            if not isinstance(pages, list) or not pages:
                raise ValueError("missing pages")
            if paginated:
                arrays = [p[field] if field else p for p in pages]
                if not all(isinstance(a, list) for a in arrays):
                    raise ValueError("invalid response shape")
                count = sum(map(len, arrays))
                capped = cap is not None and count >= cap
                if field:
                    totals = [p.get("total_count") for p in pages]
                    if any(type(t) is int and t != count for t in totals):
                        capped = True
                records[key] = record(path, pages, "partial" if capped else "complete",
                                      "provider_cap_or_count_mismatch" if capped else None)
            else:
                if len(pages) != 1 or not isinstance(pages[0], dict):
                    raise ValueError("invalid singleton")
                records[key] = record(path, pages)
        except (RuntimeError, ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
            # Exception text may contain private provider data.
            records[key] = record(path, [], "failed", type(exc).__name__)

    take("pr", prpath, False)
    if records["pr"]["status"] != "complete":
        raise RuntimeError("PR unavailable; no projection created")
    pr = records["pr"]["pages"][0]
    if pr.get("number") != number:
        raise ValueError("PR number mismatch")
    head = pr["head"]["sha"]
    merge = pr.get("merge_commit_sha") if pr.get("merged") is True else None
    if not SHA.fullmatch(head) or (merge and not SHA.fullmatch(merge)):
        raise ValueError("unexpected commit ID")
    take("commits", prpath + "/commits?per_page=100", cap=250)
    take("files", prpath + "/files?per_page=100", cap=3000)
    take("reviews", prpath + "/reviews?per_page=100")
    take("checks_head", root + "/commits/" + head + "/check-runs?filter=all&per_page=100", field="check_runs")
    if merge and merge != head:
        take("checks_merge", root + "/commits/" + merge + "/check-runs?filter=all&per_page=100", field="check_runs")
    # Detect moving source; not a transactional provider snapshot.
    take("pr_end", prpath, False)
    if records["pr_end"]["status"] == "complete":
        end = records["pr_end"]["pages"][0]
        if any(pr.get(k) != end.get(k) for k in ("updated_at", "merged", "merge_commit_sha")) or end["head"]["sha"] != head:
            records["pr_end"]["status"] = "partial"
            records["pr_end"]["error"] = "pr_changed_during_collection"
    for key, expected in (("commits", pr.get("commits")), ("files", pr.get("changed_files"))):
        r = records[key]
        if r["status"] == "complete" and type(expected) is int and sum(map(len, r["pages"])) != expected:
            r["status"], r["error"] = "partial", "pr_count_mismatch"
    bundle = {"schema": "g1-bundle-v1", "subject": repo + "#" + str(number),
              "observed_at": datetime.now(timezone.utc).isoformat(), "records": records}
    return bundle, {"elapsed_seconds": round(time.monotonic() - start, 6),
                    "api_commands": len(records),
                    "serialized_bundle_bytes": len(canonical(bundle).encode())}


def private_root(path):
    root = Path(path).expanduser().resolve()
    if any((p / ".git").exists() for p in (root, *root.parents)):
        raise ValueError("Output must be outside Git worktrees")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.stat().st_mode & 0o077:
        raise ValueError("Output directory must have mode 700")
    return root


def put(root, name, data):
    target = root / name
    with target.open("x", encoding="utf-8") as f:
        f.write(canonical(data) + "\n")
    return target


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("observe")
    p.add_argument("repo")
    p.add_argument("number", type=int)
    p.add_argument("--output", required=True)
    p = sub.add_parser("replay")
    p.add_argument("bundle")
    p.add_argument("--output", required=True)
    p = sub.add_parser("ledger")
    p.add_argument("bundles", nargs="+")
    p.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        root = private_root(args.output)
        if args.mode == "ledger":
            bundles = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.bundles]
            for bundle in bundles:
                for r in bundle["records"].values():
                    if digest(r["pages"]) != r["sha256"]:
                        raise ValueError("Evidence checksum mismatch")
            ledger = build_ledger([project(b) for b in bundles])
            key = digest(ledger)
            dest = root / (key + ".ledger.json")
            if dest.exists():
                if json.loads(dest.read_text(encoding="utf-8")) != ledger:
                    raise ValueError("Ledger replay divergence")
            else:
                put(root, dest.name, ledger)
            print(json.dumps({"ledger_id": key, "entries": len(ledger["entries"])}))
            return 0
        if args.mode == "observe":
            bundle, metrics = collect(args.repo, args.number)
            key = digest(bundle)
            put(root, key + ".bundle.json", bundle)
        else:
            bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
            key = digest(bundle)
            metrics = None
        for r in bundle["records"].values():
            if digest(r["pages"]) != r["sha256"]:
                raise ValueError("Evidence checksum mismatch")
        result = project(bundle)
        dest = root / (key + ".projection.json")
        if dest.exists():
            if json.loads(dest.read_text(encoding="utf-8")) != result:
                raise ValueError("Replay divergence")
        else:
            put(root, dest.name, result)
        if metrics is not None:
            put(root, key + ".metrics.json", metrics)
        partial = any(r["status"] != "complete" for r in bundle["records"].values())
        print(json.dumps({"bundle_id": key, "facts": len(result["facts"]),
                          "partial": partial, "metrics": metrics}))
        return 2 if partial else 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        print("Observation failed: " + type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
