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
