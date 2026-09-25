# High-Level Design — ARWO v0.1

## Logical Architecture

```text
JOB SOURCE
  ↓
INTAKE
  ↓
JOB NORMALIZER AGENT
  ↓
JOB_REQUISITION_CONTRACT
  ├── QUESTION DESIGNER → QUESTIONNAIRE CONTRACT → FORM BUILDER
  ├── PUBLICATION GENERATOR → PUBLICATION CONTRACT
  └── QA VALIDATOR → QA REPORT
                         ↓
                  HUMAN APPROVAL
                    ↓       ↓
                 CHANGES  APPROVED
                            ↓
                        PUBLISHERS
```

## Component Responsibilities

- **Intake:** accepts the source requisition and registers provenance.
- **Job Normalizer Agent:** extracts canonical title, summary, responsibilities, requirements, tools, experience, location and screening-critical requirements.
- **Question Designer Agent:** maps requirements to controlled question intents and response types.
- **Form Builder:** deterministic transformation of questionnaire contract into form API payload.
- **Publication Generator:** creates channel-specific copy from the canonical job contract only.
- **QA Validator:** checks schema, coverage, duplicates, contradictions, unsupported claims and traceability.
- **Approval Orchestrator:** packages artifacts for human review.
- **Publisher:** publishes only after explicit approval.

## External Integrations

| Integration | Role |
|---|---|
| Google Drive | Operational job artifacts and source documents |
| Gmail | Review / approval communication |
| Google Forms | Candidate intake form |
| GitHub | Code, contracts, schemas, prompts, skills, tests |
| LinkedIn / social connector | Publication after approval |
| GCP | Execution, secrets, logs and optional analytics |

## Security Boundary

GitHub may contain code, schemas, synthetic tests, contracts and policies. It must not contain candidate CVs, phone numbers, personal emails, real application responses or secrets.

## State Machine

```text
DRAFT → INGESTED → NORMALIZED → QUESTIONNAIRE_GENERATED
      → PUBLICATION_GENERATED → QA_PASSED
      → PENDING_HUMAN_APPROVAL
          ├─ CHANGES_REQUESTED
          └─ APPROVED → PUBLISHED
```
