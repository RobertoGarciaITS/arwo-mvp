# Skill: Human Approval

## Purpose
Create and validate a human approval package for ARWO.

## Preconditions
The QA Orchestrator must report:
- `READY_FOR_HUMAN_APPROVAL`
- zero blocking findings

## Approval Package
The package binds:
- canonical job contract
- questionnaire contract
- form-build specification
- publication contract
- QA report

Each artifact must include:
- artifact ID
- artifact type
- version
- repository path
- SHA-256 digest

## Process
1. Verify pre-approval QA status.
2. Generate the approval manifest.
3. Compute SHA-256 for each approved artifact.
4. Freeze the manifest logically for reviewer inspection.
5. Collect the human decision.
6. Require reviewer identity and role for an approved decision.
7. Require explicitly authorized publication channels.
8. Recompute hashes before publication.
9. Invalidate approval if any approved artifact changed.
10. Emit GATE-07 result.

## Human Decisions
- `approved`
- `changes_requested`
- `rejected`

## Important Rule
The test fixture may simulate an approval decision to validate the mechanism. It must never be interpreted as an actual production human approval.

## Exit Criteria
- approval schema valid
- hashes complete
- exact-manifest binding valid
- synthetic golden approval validates
- mutation detection test passes
- GATE-07 logic passes
