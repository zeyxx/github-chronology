# ADR-0001 — Candidate architecture
Status: PROPOSED; not ratified or implemented.

Use a Python modular monolith with pure typed domain, application use cases and replaceable adapters. Logical pipeline: acquisition (backfill/live/reconciliation) -> durable evidence/event journal -> chronology projections -> measurements/assessments -> goal-relative gaps -> authorized views. Graph is a logical model, not a mandate for graph DB. Fact views are independent of goals. Historical imports and live deliveries share the evidence boundary but retain distinct provenance.

Initial persistence candidate SQLite for single-node transactional ingestion and replay, evaluated on the first vertical; DuckDB/Parquet and Git partial/full acquisition are experiments, not decisions. Prefer pyproject packaging, pytest, Ruff/type checks and GitHub Actions with synthetic data; select exact dependencies during G1. No Kafka, graph service, distributed execution, mandatory LLM or public webhook deployment now.

Alternatives: bulk export only (insufficient for continuous observation), event-only (cannot reconstruct history and gaps), full distributed stack (unjustified complexity). PR #1 and issue #2 are acquisition experiments; do not merge them as architectural ratification. Benchmark existing tools before custom collectors. First prove UC-001 and a gap view, then measure expansion. Preserve private storage outside the repo. No automatic consumer adoption or authority transfer.
