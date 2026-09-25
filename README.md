# AI Recruitment Workflow Orchestrator — MVP v0.1

ARWO converts an unstructured job requisition into standardized, traceable and human-approved recruitment artifacts.

## MVP Flow

```text
Job Requisition
      ↓
Job Normalizer
      ↓
Canonical Job Contract
      ├── Questionnaire Generator
      ├── Publication Generator
      └── QA Validator
                ↓
          Human Approval
                ↓
       Controlled Publication
```

## Core Outputs

1. Canonical job requisition contract
2. Screening questionnaire contract
3. Google Form build specification
4. Publication package
5. QA report
6. Human approval contract
7. Workflow state and audit trail
8. Requirement-to-question traceability

## Golden Test Case

`GTC-001 — Gaming QA Engineer`

The first golden test is derived from the recruitment form reviewed during project design.

## Design Principles

- Human-in-the-loop before publication
- Canonical YAML contracts
- Deterministic validation where possible
- AI only for semantic extraction/generation tasks
- No candidate PII stored in GitHub
- Full traceability between requirements and generated artifacts
- Versioned prompts, skills, contracts, schemas and policies

## Repository Boundary

GitHub stores the technical control plane: architecture, contracts, schemas, code, prompts, skills, tests and non-PII audit artifacts.

Candidate CVs, phone numbers, personal emails, real application responses and secrets are explicitly excluded.

## Current Phase

`CHUNK-01B — Repository Bootstrap & Governance`

Next functional chunk after the repository baseline gate passes:

`CHUNK-02 — Job Normalizer`
