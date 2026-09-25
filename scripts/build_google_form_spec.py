#!/usr/bin/env python3
"""Build a deterministic Google Forms request plan from an ARWO questionnaire."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_QUESTIONNAIRE_v0.1.yaml"
DEFAULT_OUTPUT = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/GENERATED_FORM_BUILD_SPEC_v0.1.json"

TEXT_TYPES = {"short_text", "integer", "decimal", "phone", "email", "url"}
CHOICE_MAP = {
    "single_choice": "RADIO",
    "multi_choice": "CHECKBOX",
    "dropdown": "DROP_DOWN",
}

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def question_item(question: dict) -> dict:
    qtype = question["type"]
    question_resource = {"required": question["required"]}

    if qtype in TEXT_TYPES:
        question_resource["textQuestion"] = {"paragraph": False}
    elif qtype == "paragraph":
        question_resource["textQuestion"] = {"paragraph": True}
    elif qtype in CHOICE_MAP:
        question_resource["choiceQuestion"] = {
            "type": CHOICE_MAP[qtype],
            "options": [{"value": value} for value in question.get("options", [])],
            "shuffle": False,
        }
    elif qtype == "date":
        question_resource["dateQuestion"] = {"includeTime": False, "includeYear": True}
    else:
        raise ValueError(f"Unsupported API-emitted question type: {qtype}")

    item = {
        "title": question["label"],
        "questionItem": {"question": question_resource},
    }
    if question.get("help_text"):
        item["description"] = question["help_text"]
    return item

def build(questionnaire: dict) -> dict:
    deferred = []
    warnings = []
    traceability = []
    requests = []
    emitted_index = 0

    all_questions = [q for s in questionnaire["sections"] for q in s["questions"]]
    has_file_upload = any(q["type"] == "file_upload_manual_template" for q in all_questions)

    mode = "template_clone" if has_file_upload else "create_new"

    for section_number, section in enumerate(questionnaire["sections"]):
        if section_number == 0:
            section_item = {"title": section["title"], "textItem": {}}
        else:
            section_item = {"title": section["title"], "pageBreakItem": {}}

        requests.append({
            "createItem": {
                "item": section_item,
                "location": {"index": emitted_index},
            }
        })
        emitted_index += 1

        for q in section["questions"]:
            traceability.append({
                "question_id": q["question_id"],
                "analytics_key": q["analytics_key"],
                "source_origin": q["source_origin"],
                "source_requirement_ids": q["source_requirement_ids"],
                "source_tool_names": q["source_tool_names"],
                "emission": "deferred_template" if q["type"] == "file_upload_manual_template" else "api_create_item",
            })

            if q["type"] == "file_upload_manual_template":
                deferred.append({
                    "question_id": q["question_id"],
                    "analytics_key": q["analytics_key"],
                    "type": q["type"],
                    "strategy": "preconfigured_template_item",
                    "reason": "Google Forms API does not support creating file upload questions",
                })
                continue

            if q["type"] in {"integer", "decimal"} and q.get("validation"):
                warnings.append({
                    "code": "FB-W001",
                    "question_id": q["question_id"],
                    "text": "ARWO numeric validation is retained as metadata but is not emitted by the v0.1 Forms adapter.",
                })

            requests.append({
                "createItem": {
                    "item": question_item(q),
                    "location": {"index": emitted_index},
                }
            })
            emitted_index += 1

    create_request = (
        {
            "strategy": "drive_copy_template",
            "template_contract": "integrations/google_forms/FORM_TEMPLATE_CONTRACT_v0.1.yaml",
            "template_form_id": None,
            "runtime_executable": False,
        }
        if mode == "template_clone"
        else {
            "strategy": "forms.create",
            "body": {"info": {"title": questionnaire["questionnaire_id"]}},
            "runtime_executable": True,
        }
    )

    return {
        "build_id": f"BUILD-{questionnaire['questionnaire_id']}-v0.1",
        "questionnaire_id": questionnaire["questionnaire_id"],
        "provider": "google_forms",
        "mode": mode,
        "template_form_id": None,
        "create_request": create_request,
        "batch_update": {"requests": requests},
        "deferred_items": deferred,
        "traceability": traceability,
        "warnings": warnings,
    }

def main() -> int:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    spec = build(load_yaml(input_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
