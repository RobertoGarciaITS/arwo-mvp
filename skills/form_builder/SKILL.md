# Skill: Google Forms Form Builder

## Purpose
Convert an approved ARWO questionnaire into a deterministic Google Forms build specification.

## Input
- Questionnaire output conforming to the ARWO Questionnaire Output Schema
- Google Forms compatibility policy
- Optional preconfigured template form ID

## Procedure
1. Validate the questionnaire before mapping.
2. Emit the initial `forms.create` request using the form title only.
3. Traverse sections in order.
4. Emit one `pageBreakItem` per questionnaire section.
5. Traverse questions in order and map each supported ARWO type to a Google Forms question resource.
6. Assign sequential `location.index` values in the exact emitted item order.
7. Preserve question labels, help text, required flags and option order.
8. Keep ARWO traceability in the build specification; do not attempt to hide it in user-facing form text.
9. For file-upload questions, do not emit a createItem request. Mark them as deferred and require a preconfigured template strategy.
10. Produce compatibility warnings for ARWO validations that v0.1 does not enforce through the Forms API.
11. Validate the build spec and request plan before any external write.

## Type Mapping
- short_text, integer, decimal, phone, email, url → textQuestion
- paragraph → textQuestion with paragraph=true
- single_choice → choiceQuestion/RADIO
- multi_choice → choiceQuestion/CHECKBOX
- dropdown → choiceQuestion/DROP_DOWN
- date → dateQuestion
- file_upload_manual_template → deferred template item

## Guardrails
- Never invent options.
- Never reorder questions.
- Never silently drop a required question.
- Never emit a fileUploadQuestion create request.
- Never store OAuth tokens or credentials in Git.
- Do not execute Google API writes during static CI tests.

## Exit Criteria
- questionnaire-to-build-spec mapping is deterministic
- emitted API item indices are sequential
- supported questions map without semantic changes
- every deferred question has an explicit reason and strategy
- FORM-BUILDER-GATE = PASS
