# Skill: Controlled Publication

## Purpose
Validate whether an ARWO recruitment package is safe and authorized to hand off to an external publishing adapter.

## Preconditions
- CHUNK-06 QA result is `READY_FOR_HUMAN_APPROVAL`.
- CHUNK-07 approval status is `approved`.
- GATE-07 result is `PASS`.
- The approval manifest contains SHA-256 hashes for all five controlled artifacts.

## Procedure
1. Recompute the current approval manifest.
2. Compare every artifact SHA-256 to the approved manifest.
3. Compare the manifest digest.
4. Verify the requested channel is in `publication_authorization.channels`.
5. Verify publication authorization is allowed.
6. Verify the publication artifact remains exactly the approved version.
7. Generate a deterministic idempotency key.
8. Produce a publication execution plan.
9. Return `READY_FOR_CONTROLLED_EXECUTION` only if all checks pass.
10. Do not perform the external action in static CI.

## Runtime Hand-off
A future channel adapter may execute the plan only after:
- credentials are obtained from an approved secret store,
- the pre-execution gate is rerun,
- the same idempotency key has not already succeeded.

## Failure Behavior
Fail closed. Any artifact mutation, unauthorized channel, missing approval, or digest mismatch blocks execution.

## Test Fixture Rule
Synthetic approval used in GTC-001 validates the mechanism only. It is never evidence that a real vacancy was authorized for public posting.
