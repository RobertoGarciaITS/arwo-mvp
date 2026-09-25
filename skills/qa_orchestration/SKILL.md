# Skill: ARWO QA Orchestration

## Purpose
Evaluate the full pre-approval ARWO artifact package and produce a single auditable QA report.

## Required Inputs
- canonical job requisition
- questionnaire
- form-build specification
- publication contract
- QA gate contract
- data-boundary policy

## Gate Sequence
1. GATE-01 — Job completeness
2. GATE-02 — Requirement classification
3. GATE-03 — Questionnaire coverage
4. GATE-04 — Questionnaire consistency
5. GATE-05 — Privacy/data-boundary review
6. GATE-06 — Publication consistency

GATE-07 is intentionally not executed in CHUNK-06 because it is the Human Approval gate.

## Rules
- Evaluate gates in order.
- Do not mutate artifacts during QA.
- Every blocking finding must include gate ID, check ID and evidence.
- A missing required artifact is a blocking failure.
- PASS_WITH_OBSERVATION is allowed only for explicitly non-blocking findings.
- The overall result is READY_FOR_HUMAN_APPROVAL only when all pre-approval blocking gates pass.

## Core Checks
- canonical title, summary and mandatory requirements exist
- every requirement is categorized
- knockout rules only reference mandatory requirements
- mandatory screening coverage is 100%
- no orphan technical questions
- no duplicate question IDs
- form build spec preserves questionnaire order and traceability
- GitHub data boundary excludes candidate PII and secrets
- publication contains all and only canonical mandatory requirements
- unsupported publication claims are zero

## Output
Produce a QA report conforming to `QA_REPORT_SCHEMA_v0.1.json`.
