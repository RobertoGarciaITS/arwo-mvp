# Skill: Job Normalization

## Purpose
Convert raw vacancy text into the ARWO canonical job requisition contract.

## Inputs
- Raw job text
- Optional source metadata

## Method
1. Read the complete source before extracting fields.
2. Identify explicit statements only.
3. Separate responsibilities from requirements.
4. Separate mandatory from desirable only when the source supports that distinction.
5. Normalize wording without changing meaning.
6. Assign stable IDs:
   - responsibilities: `RESP-001...`
   - mandatory requirements: `REQ-001...`
   - desirable requirements: continue the requirement sequence.
7. Extract tools separately from requirements when possible.
8. Use `null` for absent optional facts.
9. Add warnings for ambiguous or missing information.
10. Validate output against the output schema.

## Grounding Rules
- Never invent minimum years.
- Never convert a desirable skill into a mandatory skill.
- Never infer remote/onsite status.
- Never infer salary or currency.
- Never add tools that are not present in the source.
- Never infer candidate suitability.

## Output Quality
Expected:
- canonical title present
- summary grounded in the source
- all requirements traceable to source wording
- zero unsupported requirements
- deterministic IDs
- valid JSON/YAML structure

## Human-in-the-Loop Conditions
Escalate when:
- must-have vs nice-to-have is unclear
- contradictory location or employment terms exist
- title is ambiguous
- required experience is described inconsistently
