# G1 PR evidence probe (candidate)

Use an authenticated GitHub CLI with read permission. No installation or network writes required. From the checkout:

    PYTHONPATH=src python -m unittest discover -s tests -v
    PYTHONPATH=src python -m chronology.cli observe OWNER/REPO 123 --output "$HOME/.local/share/chronology-g1"
    PYTHONPATH=src python -m chronology.cli replay PATH_TO_BUNDLE --output "$HOME/.local/share/chronology-g1"

Each acquisition produces a private bundle, projection and metrics. The bundle retains parsed API pages and canonical JSON hashes, not byte-exact HTTP bodies or headers. Only a complete first PR response is required; subsequent partial/failed endpoints remain visible and exit 2. API commands are not HTTP request counts because pagination may issue several requests. Replay does not contact GitHub. Check runs are scoped to the head and merge SHA; a check is not a proof of full test coverage. Commit/file caps are conservatively marked partial. No automatic claim of skills or outcomes. CV candidates are deliberately empty until a human or subsequent reviewed assessment supplies them.

Limits: no account-wide acquisition, check-run logs, issue timelines, commit diffs beyond PR files, workflow jobs, event store, live webhooks or semantic evaluation; no full transactional snapshot across API calls. PR consistency is checked at end but not guaranteed. Pagination errors currently discard that endpoint's partial stdout; report failure. Independent review and primary evidence remain required for career claims. Corpus stays outside Git, owner-only. Synthetic CI only. This is a technical UC-001 probe, not KPI-001 completion.

## Multi-PR candidate ledger

    PYTHONPATH=src python -m chronology.cli ledger PATH_TO_BUNDLE_1 PATH_TO_BUNDLE_2 --output "$HOME/.local/share/chronology-g1"

The ledger verifies page digests and rebuilds projections directly from bundles. It generates neutral candidate statements only for observed merges and exact-SHA completed successful checks. Each entry retains a source fact, bundle ID, attribution unknown, limitations and pending review. The ledger carries endpoint coverage and warnings; partial data is not complete. Same bundle replay is idempotent; separate observations are not collapsed, even if they describe the same merge. This is not a skill evaluator, a claim approval mechanism or an automatic CV generator. Manual or reviewed semantic interpretation of source files and individual contributions is still required.

## Bounded historical inventory

    PYTHONPATH=src python -m chronology.cli inventory OWNER/REPO --max-pages 20 --budget 12 --output "$HOME/.local/share/chronology-g1"

Inventories visible PRs and commits reachable from a captured default-branch tip, not every Git ref. Page budget is per collection; partial pages retained on handled errors, duplicate identities flagged. Selection spreads a bounded sample across time and reserves a nonmerged example when feasible. It is not a significance ranking. Review the selected PR numbers, then use observe and ledger. No automatic deep collection in this increment; no claims based solely on commit counts. Corpus stays private. Default-branch history and PRs may overlap; never sum them as distinct work.

## Account relationship probe

    PYTHONPATH=src python -m chronology.cli account --max-pages 10 --output "$HOME/.local/share/chronology-g1"

Uses the authenticated account (not an arbitrary login), owned repository list, per-repo genealogy and bounded authored external issues/PR search. Distinguishes parent and network root, known nonfork and unknown. Search results must match expected type and account ID; unresolved repository names are references, not stable IDs. Records evidence and coverage; search is indexed and permission-dependent, not exhaustive. External reviews/comments/commits, branch divergence, identity linking and intellectual lineage remain out of scope. No private data in public CI or Git. Account mode requires authenticated gh access to user/repo/search endpoints; connector availability is different.

## Fork divergence probe

    PYTHONPATH=src python -m chronology.cli fork OWNER/REPO --max-branches 20 --output "$HOME/.local/share/chronology-g1"

Read parent identity and pin default-branch tips. Compare each selected branch SHA with the captured parent SHA, asking for only one commit payload per comparison. Keep distinct branches but reuse comparison for identical tips. A failed comparison is unknown; branch budget or a full first page marks partial. Counts are reachability differences, not author attribution, patch equivalence, utility or unique work across branches. Never sum branch ahead counts. No mutation, clone or upstream submission. CI synthetic only.

## External contribution assessment

    PYTHONPATH=src python -m chronology.cli contribution OWNER/REPO 123 --output "$HOME/.local/share/chronology-g1"

Issue lifecycle and closure reason are independent of technical disposition. Read issue and comments; no lexical classifier of acceptance or validity. Optional --annotation JSON must contain bundle_sha256, comment_id, disposition, reviewer, scope and rationale. The annotation represents a human-reviewed interpretation, not independent validation; OWNER/MEMBER/COLLABORATOR is a provider association, not proof of delegated authority. Do not interpret closed/completed as fixed. Missing response data is unknown. FIX_REPORTED means a maintainer reports a fix, not verified execution or causality. Verify linked commit and regression changes separately; deployment, bounty, impact and human autonomy remain unknown unless supported. Mixed reports require finding-level annotations; do not flatten multiple findings into one verdict. PR merge/acceptance remains separate. This probe does not support multi-finding annotations or automated fix verification yet; synthetic tests only.
