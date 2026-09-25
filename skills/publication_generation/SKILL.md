# Skill: Publication Generation

## Purpose
Generate channel-specific recruitment copy from the canonical ARWO job requisition.

## Inputs
- Canonical job requisition
- Publication policy
- Optional application URL
- Channel profile

## Procedure
1. Validate the canonical job contract.
2. Copy the canonical title.
3. Build a short summary from source-grounded content only.
4. Include every mandatory requirement.
5. Include desirable requirements only when present in the canonical job.
6. Include responsibilities only when present.
7. Include tools only when useful and grounded.
8. Never infer missing location, salary, employment type or years.
9. Preserve the application URL byte-for-byte when provided.
10. Generate a neutral call to action.
11. Produce consistency metrics and warnings.
12. Validate output before any external publication.

## Grounding Rules
- No new requirements.
- No new benefits.
- No new salary or location claims.
- No statements such as "fast-growing", "leading", "best", or similar unless explicitly present in the source.
- No candidate ranking or suitability claims.
- No external posting action in this skill.

## Required QA
- all mandatory requirements present
- unsupported claims = 0
- application link consistency = PASS
- publication status remains draft until approval
