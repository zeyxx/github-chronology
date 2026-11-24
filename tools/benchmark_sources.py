"""Measure Git acquisition strategies and inventory native GitHub archives.

No network mutations. No archive extraction. Results stay on stdout.
Run on a trusted workstation with Git authentication already configured.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import time
from collections import Counter

REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def git(*args, cwd=None):
    result = subprocess.run(
        ["git", "-c", "gc.auto=0", *args], cwd=cwd,
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1800,
    )
    if result.returncode:
        raise RuntimeError("Git failed; verify authentication and repository access")
    return result.stdout


def graph(path):
    return set(git("rev-list", "--all", "--parents", cwd=path).splitlines())


def refs(path):
    return set(git("for-each-ref", "--format=%(refname)%09%(objectname)", cwd=path).splitlines())


def measure(repo, rounds, root):
    if not REPO.fullmatch(repo):
        raise ValueError("Expected OWNER/NAME")
    url = "https://github.com/" + repo + ".git"
    root = Path(root).expanduser().resolve()
    if any((p / ".git").exists() for p in (root, *root.parents)):
        raise ValueError("Use a directory outside a Git worktree")
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    if root.stat().st_mode & 0o077:
        raise ValueError("Benchmark directory must have mode 700")
    for i in range(rounds):
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            result = {}
            # Alternate order to reduce systematic cache bias.
            modes = ["full", "blobless"] if i % 2 == 0 else ["blobless", "full"]
            for mode in modes:
                dest = Path(tmp) / (mode + ".git")
                flags = ["--filter=blob:none"] if mode == "blobless" else []
                start = time.perf_counter()
                git("clone", "--mirror", *flags, "--", url, str(dest))
                elapsed = time.perf_counter() - start
                objects = sum(p.stat().st_size for p in (dest / "objects").rglob("*") if p.is_file())
                g, r = graph(dest), refs(dest)
                result[mode] = (g, r, {"seconds": elapsed, "object_bytes": objects,
                                      "commits": len(g), "refs": len(r),
                                      "promisor_packs": len(list((dest / "objects" / "pack").glob("*.promisor")))})
            print(json.dumps({"round": i + 1, "repo": repo,
                              "full": result["full"][2], "blobless": result["blobless"][2],
                              "graph_equal": result["full"][0] == result["blobless"][0],
                              "refs_equal": result["full"][1] == result["blobless"][1]}))
            # A live repository may change between acquisitions; report, never silently dismiss.
            # Temporary private clones are removed automatically.


def archive_inventory(path):
    path = Path(path).expanduser().resolve()
    start = time.perf_counter()
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    counts, sizes = Counter(), Counter()
    with tarfile.open(path, "r|*") as archive:
        for member in archive:
            # No extraction, no member payload printed. Category by basename prefix
            # or extension is only an inventory heuristic, not proof of semantics.
            if not member.isfile():
                counts["non_regular"] += 1
                continue
            name = Path(member.name).name
            category = re.sub(r"[-_]?\d+(?=\.[^.]+$)", "", name) if name.endswith(".json") else Path(name).suffix or "(no extension)"
            counts[category] += 1
            sizes[category] += member.size
    print(json.dumps({"archive_sha256": sha.hexdigest(), "compressed_bytes": path.stat().st_size,
                      "seconds": time.perf_counter() - start,
                      "category_counts": dict(counts), "category_uncompressed_bytes": dict(sizes)}))


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    g = sub.add_parser("git")
    g.add_argument("repo")
    g.add_argument("--rounds", type=int, choices=range(1, 6), default=3)
    g.add_argument("--output", required=True)
    a = sub.add_parser("archive")
    a.add_argument("path")
    args = parser.parse_args()
    if args.command == "git":
        measure(args.repo, args.rounds, args.output)
    else:
        archive_inventory(args.path)


if __name__ == "__main__":
    main()
