# S02 — Evidence and epistemic specification
Status: PROPOSED | v0.1

## Contract candidate
Evidence reference: source/provider, stable resource ID or URL, revision/content digest, collection time, source occurrence time if available, acquisition method, scope, visibility and limitations. Raw payloads are untrusted and private; preserve integrity and distinguish source statements from independently verified facts. Hashing alone proves neither origin nor truth. Observations reference evidence and method/version; assessments additionally record subject, claim, evidence, counterevidence, uncertainty, scope and reference frame where relevant.

## Distinctions
Live delivery, reconstructed historical event and API state snapshot are different categories. Store occurrence and observed time separately. Do not fabricate historical events from current state. Distinguish source-reported, inferred, independently verified and unknown. Record source authority and coverage (expected denominator where knowable, inaccessible/capped/expired resources, partial/failed/skipped collections). Successful response is not completeness. Correction supersedes a claim without deleting history; privacy deletion policies must be explicitly supported, not overridden by append-only design.

## Integrity and permissions
Stable provider IDs plus occurrence/delivery identities; deduplicate retries without collapsing distinct events or source observations. Record conflicts, provenance and schema version. Replay deterministic versioned projections; assess semantic models separately, store outputs and model/prompt versions instead of claiming deterministic LLM replay. Validate ingress, authenticate live webhooks, prevent replay abuse, bound resource usage; never execute source content. Keep private corpus outside Git; redact separate authorized consumer projections. No credential material in logs. No cross-account identity linkage without authority/evidence.

## Verification
Synthetic tests for duplicate delivery, late arrival, unknown fields, missing evidence, correction, conflicting evidence, source scope and failed acquisition. Measure observed precision on independently annotated samples; report abstention/coverage alongside accuracy. No real private sample in public fixtures.
