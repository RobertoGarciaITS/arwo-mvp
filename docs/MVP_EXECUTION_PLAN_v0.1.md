# MVP Execution Plan v0.1

## Chunk 01 — Foundation
Create schemas, contracts, policies, state machine and golden test case.

**Exit gate:** all baseline artifacts are syntactically valid and cross-referenced.

## Chunk 01B — Repository Bootstrap & Governance
Create the governed GitHub baseline, data boundaries, branch policy, artifact registry and project state.

**Exit gate:** remote tree matches the governed baseline and the bootstrap PR is auditable.

## Chunk 02 — Job Normalizer
Input: raw job text  
Output: `job_contract.yaml`

Tests:
- title extracted
- responsibilities extracted
- must-have vs nice-to-have separated
- no unsupported requirements introduced

## Chunk 03 — Questionnaire Generator
Input: `job_contract.yaml`  
Output: `questionnaire_contract.yaml`

Tests:
- 100% mandatory screening coverage
- no orphan technical questions
- valid question type per policy
- knockout only from mandatory requirements

## Chunk 04 — Form Builder
Input: `questionnaire_contract.yaml`  
Output: `form_build_spec.json` + created form preview

## Chunk 05 — Publication Generator
Input: approved `job_contract.yaml`  
Output: channel-specific publication contract

## Chunk 06 — QA Orchestrator
Runs GATE-01 through GATE-06.

## Chunk 07 — Human Approval
Creates review package and approval request.

## Chunk 08 — Controlled Publication
Requires GATE-07 PASS and explicit approved status.

## Definition of MVP Done
- Golden Test Case GTC-001 runs end-to-end
- all seven gates implemented
- no publication can bypass approval
- artifacts are versioned
- traceability matrix is generated
