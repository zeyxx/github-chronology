# UC-001 — Observe a pull request end to end
Status: PROPOSED | G1 acceptance target

Input: explicitly selected, authorized GitHub PR; synthetic fixture first, then one real pilot in private local storage. CLI/import and read-only API are sufficient; no webhook infrastructure or account-wide export required.

Output: a locally consultable, versioned projection containing PR identity and timeline, linked commits, reviews and available CI runs; source references, collection receipts and uncertainty. Distinguish merged, tested, deployed, used, and useful. Do not infer the latter from the former. If no outcome evidence is supplied, utility remains UNKNOWN.

Acceptance:
- Stable identifiers, timestamps and source scope; trace every factual claim.
- Reconstruct chronology from source timestamps without inventing events.
- Attribute provider authorship without asserting human autonomy; distinguish known and unknown.
- Show review and CI evidence scoped to exact relevant commit(s); distinguish unavailable, failed and passed checks.
- Separate output/delivery from demonstrated outcome/utility.
- Duplicate import does not duplicate events/metrics; late input and corrections converge on the same projection for the same evidence and versions.
- Incomplete acquisition remains visible; no fabricated success or utility.
- Synthetic fixtures public, real results private. No source writes or automatic publication.
- Record wall time, API calls, coverage, bytes, reproducibility, and human review effort. Establish baseline; do not invent thresholds.

G1 extension: compare an explicit target (e.g. required verification) against observed evidence and distinguish a missing check from missing observation. No LLM required for first vertical. Dashboard, broad ingestion and market calibration follow evidence from the pilot.
