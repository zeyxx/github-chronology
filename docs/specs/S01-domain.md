# S01 — Domain specification
Status: PROPOSED | v0.1

## Seven scales
E1 Artifact (file, function, document, contract); E2 Transaction (commit, review, CI run, deployment); E3 Mission (bounded intended result); E4 Subsystem (component, bounded context); E5 Project (product or project lifecycle); E6 Ecosystem (related projects and resource allocation); E7 Identity (actor trajectory across accounts, organizations and ecosystems).
These are observation scales, not rigid containment or bounded contexts. Subjects have stable typed IDs; edges are typed, time-scoped and evidenced. Many-to-many relations are normal; a PR can realize multiple missions and a mission span PRs. Account is not identity; identity/account links require explicit evidence and may be uncertain. Preserve human/agent/team/unknown attribution separately from provider authorship. A domain or skill is a cross-cutting taxonomy, not an eighth scale.

## Vocabulary
Subject, Activity (action), Work (transformation), Output (artifact/delivery), Outcome (observed effect), Utility (goal-relative value of effect), Cost (resources with units and scope), Attribution (evidenced contribution), Event (occurrence, source or reconstruction), Evidence (traceable source), Observation (factual statement bounded by evidence), Metric (versioned calculation), Assessment (revisable judgment), Objective (desired state with subject, horizon, criteria), ReferenceFrame (dated versioned external/internal requirements), Gap (comparison with explicit evidence and uncertainty), ImprovementOpportunity (candidate intervention with rationale and measurement plan).
Do not collapse work/output/outcome/utility; unknown costs are not zero. Metrics and goals are versioned; historical judgments retain their original reference frame. Gap types: demonstrated capability shortfall; evidence insufficient; observation coverage missing; strategic objective ambiguous or stale. Types may coexist.

## Candidate contexts
Acquisition; Evidence; Chronology; Measurement; Assessment; Objectives/Reference Frames; Gap Analysis; Projection. Initially modules in one Python application, not network services. Pure domain depends on no provider/DB/LLM. Scope/authority and publication policy are explicit. No automatic project/identity inference merely from repository ownership.

## Invariants
I1 Trace claims to evidence. I2 Unknown is not false/zero. I3 Activity != utility. I4 Authorship != autonomy. I5 Preserve originals; corrections append. I6 Replay deterministic projections for same evidence/schema/version. I7 Handle duplicate and out-of-order events. I8 Explicit aggregation/denominators and no double counting. I9 Show counterevidence and coverage. I10 Evaluate productions/capabilities, not human worth. I11 Private by default; authorized disclosure only. I12 Observation grants no authority to act. I13 Goals and reference frames must be explicit and dated; missing evidence cannot establish a capability deficit. I14 No causal inference from chronological proximity alone.

## Later specs
S03 events; S04 measurement; S05 assessment; S06 acquisition; S07 projection; S08 operations; S09 objectives; S10 reference frames; S11 gaps/improvement. Elaborate only as verticals require. No universal weighting yet.
