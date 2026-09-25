#!/usr/bin/env python3
"""Deterministic validation for ARWO CHUNK-04 Google Forms Form Builder."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
QUESTIONNAIRE = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_QUESTIONNAIRE_v0.1.yaml"
SCHEMA = ROOT / "schemas/FORM_BUILD_SPEC_SCHEMA_v0.1.json"
BUILDER = ROOT / "scripts/build_google_form_spec.py"

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def load_builder():
    spec = importlib.util.spec_from_file_location("arwo_form_builder", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module

def check(condition, test_id, message, failures):
    status = "PASS" if condition else "FAIL"
    print(f"{test_id}: {status} — {message}")
    if not condition:
        failures.append(test_id)

def main() -> int:
    questionnaire = load_yaml(QUESTIONNAIRE)
    schema = load_json(SCHEMA)
    builder = load_builder()
    build_spec = builder.build(questionnaire)
    failures = []

    errors = sorted(Draft202012Validator(schema).iter_errors(build_spec), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            print(f"SCHEMA ERROR at {list(error.path)}: {error.message}")
    check(not errors, "FB-T001", "build spec schema validation", failures)

    check(build_spec["mode"] == "template_clone", "FB-T002", "template mode selected for file-upload questionnaire", failures)

    deferred = build_spec["deferred_items"]
    check(
        len(deferred) == 1 and deferred[0]["analytics_key"] == "resume_file",
        "FB-T003",
        "exactly one resume file-upload question deferred",
        failures,
    )

    payload_text = json.dumps(build_spec["batch_update"])
    check("fileUploadQuestion" not in payload_text, "FB-T004", "no fileUploadQuestion create request emitted", failures)

    requests = build_spec["batch_update"]["requests"]
    indices = [r["createItem"]["location"]["index"] for r in requests]
    check(indices == list(range(len(requests))), "FB-T005", "createItem indices are sequential", failures)

    expected_sections = [s["title"] for s in questionnaire["sections"]]
    emitted_sections = []
    for req in requests:
        item = req["createItem"]["item"]
        if "textItem" in item or "pageBreakItem" in item:
            emitted_sections.append(item["title"])
    check(emitted_sections == expected_sections, "FB-T006", "section order preserved", failures)

    source_questions = [
        q
        for section in questionnaire["sections"]
        for q in section["questions"]
        if q["type"] != "file_upload_manual_template"
    ]
    emitted_questions = [
        req["createItem"]["item"]
        for req in requests
        if "questionItem" in req["createItem"]["item"]
    ]
    check(
        [q["label"] for q in source_questions] == [item["title"] for item in emitted_questions],
        "FB-T007",
        "emitted question order preserved",
        failures,
    )

    required_ok = all(
        source["required"] == emitted["questionItem"]["question"]["required"]
        for source, emitted in zip(source_questions, emitted_questions)
    )
    check(required_ok, "FB-T008", "required flags preserved", failures)

    options_ok = True
    choice_type_ok = True
    choice_map = {"single_choice": "RADIO", "multi_choice": "CHECKBOX", "dropdown": "DROP_DOWN"}
    for source, emitted in zip(source_questions, emitted_questions):
        if source["type"] in choice_map:
            choice = emitted["questionItem"]["question"].get("choiceQuestion", {})
            actual_options = [o["value"] for o in choice.get("options", [])]
            if actual_options != source.get("options", []):
                options_ok = False
            if choice.get("type") != choice_map[source["type"]]:
                choice_type_ok = False
    check(options_ok, "FB-T009", "choice option values and order preserved", failures)
    check(choice_type_ok, "FB-T010", "choice types mapped correctly", failures)

    source_ids = {
        q["question_id"]
        for section in questionnaire["sections"]
        for q in section["questions"]
    }
    traced_ids = {t["question_id"] for t in build_spec["traceability"]}
    check(source_ids == traced_ids, "FB-T011", "all questionnaire questions represented in traceability", failures)

    numeric_questions = [
        q for q in source_questions
        if q["type"] in {"integer", "decimal"} and q.get("validation")
    ]
    numeric_warning_ids = {
        w["question_id"] for w in build_spec["warnings"] if w.get("code") == "FB-W001"
    }
    check(
        {q["question_id"] for q in numeric_questions}.issubset(numeric_warning_ids),
        "FB-T012",
        "v0.1 numeric validation limitation is explicit",
        failures,
    )

    check(
        build_spec["template_form_id"] is None
        and build_spec["create_request"].get("template_form_id") is None,
        "FB-T013",
        "runtime Google template ID is not committed to repository",
        failures,
    )

    # 4 visible section headers + 13 API-emitted questions; resume upload remains in the template.
    check(len(requests) == 17, "FB-T014", "expected deterministic request count is 17", failures)

    print()
    if failures:
        print("FORM-BUILDER-GATE: FAIL")
        print("Blocking tests:", ", ".join(failures))
        return 1

    print("FORM-BUILDER-GATE: PASS")
    print("Blocking tests: 0")
    print(f"Requests emitted: {len(requests)}")
    print(f"Deferred template items: {len(deferred)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
