# GitHub Chronology

Read-only, local-first collection of Git and GitHub evidence. The corpus can feed a CV audit, a portfolio, project composition and cross-project improvement documents. GitHub/Git retain source authority; observations never authorize changes or prove individual competence.

## Run V0

Requirements: Python 3.11+, Git, GitHub CLI authenticated with a read-capable account. No Python dependencies.

    gh auth status
    python github_chronology.py collect --output "$HOME/.local/share/github-chronology" --workers 4
    python github_chronology.py export --output "$HOME/.local/share/github-chronology"
    python -m unittest discover -s tests -v

Default scope: repositories owned by the authenticated user, including private repositories visible to the token. Explicit scope: repeat `--repo OWNER/NAME`; `--accessible` opts into all repositories returned by the authenticated affiliation listing. Prefer a narrow trial first. `--no-git` skips mirrors; `--deep` additionally fetches per-issue timelines, per-PR reviews/files/commits, per-run jobs and per-deployment statuses. No remote writes.

Output: SQLite evidence.sqlite3 (raw API pages, deduplicated item snapshots, observations and coverage), bare Git mirrors by stable repository ID, evidence.jsonl and coverage.jsonl. Multiple scans retain snapshots and distinguish each observation run. V0 performs full REST scans rather than claiming incremental synchronization; Git mirrors fetch incrementally.

## Coverage and limits

REST pagination follows Link headers. Every attempted endpoint has a receipt (complete, partial or failed); a non-complete scan exits 2. Complete means successful traversal of the exposed endpoint, not complete history of the account. REST provider caps, deleted/unreachable data, expired Actions logs, private inaccessible repos, forks, external contributions, discussions, review-thread resolution and API retention require additional work. Deep mode may make many requests. Rate limits terminate an affected endpoint rather than silently inventing completeness.

Git mirrors retain fetched refs and reachable objects, not objects removed before collection. Local mirror snapshots may change on later fetches; retained evidence records do not reconstruct all historical blobs lost before collection. Never execute checked-out repository content.

The code is public; collected data is PRIVATE, may contain secrets and third-party information, and must never be committed or shared blindly. Export outside any Git working tree, restrict access, and redact separate consumer projections. No CV, scoring, TID generation or portfolio publication is part of this collector.

See docs/CONTRACT.md for the versioned evidence boundary. V0 is a review candidate, not a certified exhaustive export.
