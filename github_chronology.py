"""Read-only GitHub evidence collector. No third-party Python dependencies."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
import uuid

API = "https://api.github.com"
VERSION = "0.1"
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')
SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, started TEXT, config TEXT);
CREATE TABLE IF NOT EXISTS blobs(sha TEXT PRIMARY KEY, raw BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS pages(run TEXT, repo INTEGER, source TEXT, observed TEXT, sha TEXT,
  PRIMARY KEY(run,repo,source,sha));
CREATE TABLE IF NOT EXISTS snapshots(repo INTEGER, kind TEXT, entity TEXT, sha TEXT, payload TEXT,
  PRIMARY KEY(repo,kind,entity,sha));
CREATE TABLE IF NOT EXISTS observations(run TEXT, repo INTEGER, kind TEXT, entity TEXT, sha TEXT,
  source TEXT, observed TEXT, page_sha TEXT,
  PRIMARY KEY(run,repo,kind,entity,sha,source));
CREATE TABLE IF NOT EXISTS coverage(run TEXT, repo INTEGER, source TEXT, status TEXT,
  pages INTEGER, items INTEGER, error TEXT, observed TEXT,
  PRIMARY KEY(run,repo,source));
"""


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def entity_key(item):
    if isinstance(item, dict):
        for k in ("id", "node_id", "sha", "number", "name", "ref"):
            if item.get(k) is not None:
                return str(item[k])
    return digest(canonical(item).encode())


def safe_root(path):
    root = Path(path).expanduser().resolve()
    for ancestor in (root, *root.parents):
        if (ancestor / ".git").exists():
            raise ValueError("Corpus must be outside a Git worktree")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.stat().st_mode & 0o077:
        raise ValueError("Corpus directory must not grant group/other access; chmod 700")
    return root


class Store:
    def __init__(self, root):
        self.db = sqlite3.connect(root / "evidence.sqlite3", timeout=60)
        self.db.execute("PRAGMA busy_timeout=60000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def run(self, config):
        run = uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO runs VALUES (?,?,?)", (run, now(), canonical(config)))
        return run

    def page(self, run, repo, source, raw, items, kind):
        page_sha, observed = digest(raw), now()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO blobs VALUES (?,?)", (page_sha, raw))
            self.db.execute("INSERT OR IGNORE INTO pages VALUES (?,?,?,?,?)",
                            (run, repo, source, observed, page_sha))
            for item in items:
                payload = canonical(item)
                sha = digest(payload.encode())
                entity = entity_key(item)
                self.db.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?)",
                                (repo, kind, entity, sha, payload))
                self.db.execute("INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?,?,?)",
                                (run, repo, kind, entity, sha, source, observed, page_sha))

    def receipt(self, run, repo, source, status, pages, items, error=""):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO coverage VALUES (?,?,?,?,?,?,?,?)",
                            (run, repo, source, status, pages, items, error, now()))

    def export(self, root):
        self.db.row_factory = sqlite3.Row
        queries = {
            "evidence.jsonl": """SELECT o.*,s.payload FROM observations o JOIN snapshots s
                 USING(repo,kind,entity,sha) ORDER BY o.observed,o.repo,o.kind,o.entity,o.sha,o.source""",
            "coverage.jsonl": "SELECT * FROM coverage ORDER BY observed,repo,source",
            "runs.jsonl": "SELECT * FROM runs ORDER BY started,id",
        }
        for name, sql in queries.items():
            target = root / name
            tmp = root / (name + ".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                for row in self.db.execute(sql):
                    record = dict(row)
                    if "payload" in record:
                        record["payload"] = json.loads(record["payload"])
                    record["schema_version"] = VERSION
                    f.write(canonical(record) + "\n")
            tmp.replace(target)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class APIClient:
    def __init__(self, token):
        self.token = token
        self.opener = build_opener(NoRedirect())

    def pages(self, endpoint):
        url = API + endpoint
        seen = set()
        while url:
            parsed = urlsplit(url)
            if parsed.scheme != "https" or parsed.netloc != "api.github.com" or url in seen:
                raise ValueError("Invalid or repeated pagination link")
            seen.add(url)
            request = Request(url, headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "github-chronology/" + VERSION,
            })
            with self.opener.open(request, timeout=60) as response:
                raw = response.read()
                link = response.headers.get("Link", "")
            yield url, raw, json.loads(raw)
            match = NEXT.search(link)
            url = match.group(1) if match else None


def error_label(exc):
    # Never persist exception text: URLs, subprocess output and credentials may be sensitive.
    if isinstance(exc, HTTPError):
        return "HTTP_" + str(exc.code)
    return type(exc).__name__


def scan(store, client, run, repo, endpoint, kind, array_key=None, singleton=False):
    pages = count = 0
    collected = []
    try:
        for source, raw, payload in client.pages(endpoint):
            if singleton:
                items = [payload]
            elif array_key:
                items = payload[array_key]
            else:
                items = payload
            if not isinstance(items, list):
                raise ValueError("Unexpected API response shape")
            store.page(run, repo, source, raw, items, kind)
            collected.extend(items)
            pages += 1
            count += len(items)
        store.receipt(run, repo, endpoint, "complete", pages, count)
    except Exception as exc:
        store.receipt(run, repo, endpoint, "partial" if pages else "failed",
                      pages, count, error_label(exc))
    return collected


def git_cmd(*args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(
        ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
         "-c", "gc.auto=0", *args], env=env, check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=1800).stdout


def git_scan(store, run, repo_id, name, root):
    source = "git:" + name
    count = pages = 0
    try:
        path = root / "mirrors" / (str(repo_id) + ".git")
        path.parent.mkdir(mode=0o700, exist_ok=True)
        remote = "https://github.com/" + name + ".git"
        if not path.exists():
            git_cmd("clone", "--mirror", "--", remote, str(path))
        else:
            if git_cmd("-C", str(path), "config", "--get", "remote.origin.url").decode().strip() != remote:
                raise ValueError("Mirror origin mismatch")
            git_cmd("-C", str(path), "fetch", "--prune", "origin")
        raw = git_cmd("-C", str(path), "for-each-ref", "--format=%(refname)%09%(objectname)")
        refs = [{"ref": line.split("\t")[0], "sha": line.split("\t")[1]}
                for line in raw.decode("utf-8", "replace").splitlines()]
        # Ref identity must be ref name, not the target SHA.
        for ref in refs:
            ref["id"] = ref["ref"]
        store.page(run, repo_id, source + "/refs", raw, refs, "git.ref")
        pages += 1
        count += len(refs)
        fmt = "%H%x00%P%x00%aI%x00%cI%x00%an%x00%ae%x00%cn%x00%ce%x00%B"
        raw = git_cmd("-C", str(path), "log", "--all", "-z", "--format=tformat:" + fmt)
        fields = raw.split(b"\0")
        if fields and fields[-1] == b"":
            fields.pop()
        if len(fields) % 9:
            raise ValueError("Invalid Git log record framing")
        keys = ("sha", "parents", "authored_at", "committed_at", "author_name",
                "author_email", "committer_name", "committer_email", "message")
        commits = []
        for i in range(0, len(fields), 9):
            item = dict(zip(keys, (x.decode("utf-8", "replace") for x in fields[i:i+9])))
            item["parents"] = item["parents"].split()
            commits.append(item)
        store.page(run, repo_id, source + "/commits", raw, commits, "git.commit")
        pages += 1
        count += len(commits)
        store.receipt(run, repo_id, source, "complete", pages, count)
    except Exception as exc:
        store.receipt(run, repo_id, source, "partial" if pages else "failed",
                      pages, count, error_label(exc))


def collect_repo(root, token, run, repo, deep, mirror):
    store = Store(root)
    try:
        repo_id, name = int(repo["id"]), repo["full_name"]
        if not REPO_NAME.fullmatch(name):
            raise ValueError("Invalid repository name")
        base = "/repos/" + name
        client = APIClient(token)
        def pull(suffix, kind, array=None, singleton=False):
            separator = "&" if "?" in suffix else "?"
            return scan(store, client, run, repo_id, base + suffix + separator + "per_page=100",
                        kind, array, singleton)

        pull("", "repository", singleton=True)
        for suffix, kind, array, singleton in [
            ("/languages", "languages", None, True),
            ("/branches", "branch", None, False),
            ("/tags", "tag", None, False),
            ("/releases", "release", None, False),
            ("/contributors", "contributor", None, False),
            ("/issues/comments", "issue.comment", None, False),
            ("/issues/events", "issue.event", None, False),
            ("/pulls/comments", "pr.comment", None, False),
            ("/actions/workflows", "workflow", "workflows", False),
            ("/actions/artifacts", "artifact", "artifacts", False),
        ]:
            pull(suffix, kind, array, singleton)
        issues = pull("/issues?state=all", "issue_or_pr")
        prs = pull("/pulls?state=all", "pr")
        runs = pull("/actions/runs", "workflow.run", "workflow_runs")
        deployments = pull("/deployments", "deployment")
        if deep:
            for issue in issues:
                pull("/issues/" + str(issue["number"]) + "/timeline", "issue.timeline")
            for pr in prs:
                prefix = "/pulls/" + str(pr["number"])
                for suffix, kind in [("", "pr.detail"), ("/reviews", "pr.review"),
                                     ("/files", "pr.file"), ("/commits", "pr.commit")]:
                    pull(prefix + suffix, kind, singleton=(suffix == ""))
            for item in runs:
                pull("/actions/runs/" + str(item["id"]) + "/jobs?filter=all", "workflow.job", "jobs")
            for item in deployments:
                pull("/deployments/" + str(item["id"]) + "/statuses", "deployment.status")
        if mirror:
            git_scan(store, run, repo_id, name, root)
        else:
            store.receipt(run, repo_id, "git:" + name, "skipped", 0, 0)
    finally:
        store.close()


def collect(args, root):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        token = subprocess.run(["gh", "auth", "token"], check=True,
                               capture_output=True, text=True).stdout.strip()
    if not token:
        raise ValueError("No GitHub token")
    store = Store(root)
    try:
        run = store.run({"version": VERSION, "explicit_repos": args.repo,
                         "accessible": args.accessible, "deep": args.deep,
                         "mirror": not args.no_git, "workers": args.workers})
        client = APIClient(token)
        if args.repo:
            repos = []
            for name in args.repo:
                if not REPO_NAME.fullmatch(name):
                    raise ValueError("Expected OWNER/NAME")
                repos.extend(scan(store, client, run, 0, "/repos/" + name,
                                  "discovery.repository", singleton=True))
        else:
            affiliation = "owner,collaborator,organization_member" if args.accessible else "owner"
            repos = scan(store, client, run, 0,
                         "/user/repos?visibility=all&affiliation=" + affiliation + "&per_page=100",
                         "discovery.repository")
        unique = {int(repo["id"]): repo for repo in repos}
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(collect_repo, root, token, run, repo, args.deep,
                                   not args.no_git): repo for repo in unique.values()}
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    store.receipt(run, int(futures[future]["id"]), "collector", "failed",
                                  0, 0, error_label(exc))
        stats = dict(store.db.execute("SELECT status,count(*) FROM coverage WHERE run=? GROUP BY status",
                                      (run,)))
        print(canonical({"run": run, "repositories": len(unique), "coverage": stats}))
        return 2 if stats.get("failed") or stats.get("partial") else 0
    finally:
        store.close()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("collect")
    cmd.add_argument("--output", required=True)
    scope = cmd.add_mutually_exclusive_group()
    scope.add_argument("--repo", action="append")
    scope.add_argument("--accessible", action="store_true")
    cmd.add_argument("--workers", type=int, choices=range(1, 9), default=4)
    cmd.add_argument("--deep", action="store_true")
    cmd.add_argument("--no-git", action="store_true")
    exp = sub.add_parser("export")
    exp.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        root = safe_root(args.output)
        if args.command == "collect":
            return collect(args, root)
        store = Store(root)
        try:
            store.export(root)
        finally:
            store.close()
        return 0
    except Exception as exc:
        print("Collector failed: " + error_label(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
