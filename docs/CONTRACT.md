# Evidence contract v0 (candidate)

- Repository identity: GitHub numeric repository ID; names are mutable.
- Raw response: SHA-256 of bytes, source URL, observation timestamp and run ID. REST page content is preserved locally.
- Snapshot: repository ID, resource kind, provider ID, SHA-256 of canonical JSON. Immutable by content identity. An observation references one snapshot and the source page. A provider timestamp is not an observation timestamp.
- Git: bare mirrors preserve fetched Git objects and refs. Ref observations and commit metadata are separately recorded, using commit SHA. Author, committer and co-author trailers are evidence of claimed attribution, not proof of human authorship.
- Coverage: one receipt per attempted endpoint or Git operation, with status, pages/items and error class. A failed or partial receipt is never a complete result. Zero results and unavailable endpoints are different. Deep mode and scope are recorded in the run.
- Derived interpretations: separate consumers may correlate decisions, failures, tests, deployments, collaborators and changes. They must cite stable source identifiers, record attribution uncertainty and avoid treating commit volume as competence. No source snapshot is edited by a consumer.
- Privacy: raw payloads and mirrors are private. Export is not publication. Public projections require independent redaction and explicit publication. No credentials or private source copies in the public collector repository.

## Roadmap

V0: owned/explicit/accessible repo inventory, REST resources, deep expansion, Git mirror and commit/ref metadata, receipts and JSONL.
V1: complete GraphQL connection pagination (discussions, review threads, contribution discovery), external repo scope, job logs subject to retention and permissions, durable endpoint cursors and deletion/tombstone semantics, resumable rate-aware requests, deterministic graph projections and measured coverage.
V2: candidate consumer contracts for CV evidence, portfolio and cross-project learning. No automatic governance or adoption by consumers.
