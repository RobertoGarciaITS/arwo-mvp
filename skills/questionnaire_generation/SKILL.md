# Skill: Questionnaire Generation

## Purpose
Convert the canonical ARWO job requisition into a structured screening questionnaire with explicit provenance.

## Inputs
- Canonical job requisition
- Question generation policy
- Question mapping rules
- Optional questionnaire profile

## Procedure
1. Validate the canonical job input.
2. Enumerate mandatory, desirable and unclassified requirements.
3. Identify which requirements require screening.
4. For each screening requirement, select an intent and response type.
5. Generate deterministic question IDs in presentation order.
6. Attach every job-derived question to its source requirement ID.
7. Ground tool-proficiency questions using `source_tool_names`.
8. Mark standard identity/contact/logistics fields as `source_origin: system_policy`.
9. Apply knockout logic only to explicit mandatory requirements.
10. Generate coverage metrics and warnings.
11. Validate the final questionnaire against the output schema.

## Mapping Guidance
- Binary eligibility requirement → single choice Yes/No
- Years of experience → integer or controlled dropdown
- Multiple technical features → multi choice
- Evidence/examples → paragraph
- Tool set exposure → multi choice when multiple simultaneous tools are possible
- URL → url
- Notice period → dropdown
- Resume upload → file-upload placeholder for the downstream form builder

## Anti-Invention Rules
- Do not create technical screening questions without a requirement or tool source.
- Do not add a knockout because a skill merely appears desirable.
- Do not convert an unclassified requirement into mandatory.
- Do not infer years, salary thresholds, location or citizenship requirements.
- Administrative fields may come only from an explicit system policy/profile.

## Quality Gate
- Mandatory screening coverage = 100%
- Unsupported technical questions = 0
- Orphan technical questions = 0
- Invalid knockout rules = 0
- Duplicate semantic questions = 0
- Schema validation = PASS
