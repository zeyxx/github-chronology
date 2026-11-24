# G1 PR evidence probe (candidate)

Use an authenticated GitHub CLI with read permission. No installation or network writes required. From the checkout:

    PYTHONPATH=src python -m unittest discover -s tests -v
    PYTHONPATH=src python -m chronology.cli observe OWNER/REPO 123 --output "$HOME/.local/share/chronology-g1"
    PYTHONPATH=src python -m chronology.cli replay PATH_TO_BUNDLE --output "$HOME/.local/share/chronology-g1"

Each acquisition produces a private bundle, projection and metrics. The bundle retains parsed API pages and canonical JSON hashes, not byte-exact HTTP bodies or headers. Only a complete first PR response is required; subsequent partial/failed endpoints remain visible and exit 2. API commands are not HTTP request counts because pagination may issue several requests. Replay does not contact GitHub. Check runs are scoped to the head and merge SHA; a check is not a proof of full test coverage. Commit/file caps are conservatively marked partial. No automatic claim of skills or outcomes. CV candidates are deliberately empty until a human or subsequent reviewed assessment supplies them.

Limits: no account-wide acquisition, check-run logs, issue timelines, commit diffs beyond PR files, workflow jobs, event store, live webhooks or semantic evaluation; no full transactional snapshot across API calls. PR consistency is checked at end but not guaranteed. Pagination errors currently discard that endpoint's partial stdout; report failure. Independent review and primary evidence remain required for career claims. Corpus stays outside Git, owner-only. Synthetic CI only. This is a technical UC-001 probe, not KPI-001 completion.
