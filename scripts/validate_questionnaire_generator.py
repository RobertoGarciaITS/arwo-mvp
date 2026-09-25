#!/usr/bin/env python3
"""Deterministic validation for ARWO CHUNK-03 Questionnaire Generator."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_JOB_NORMALIZED_v0.1.yaml"
QUESTIONNAIRE = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_QUESTIONNAIRE_v0.1.yaml"
SCHEMA = ROOT / "schemas/QUESTIONNAIRE_OUTPUT_SCHEMA_v0.1.json"

TECHNICAL_INTENTS = {"eligibility", "experience", "technical_coverage", "tool_proficiency", "evidence"}

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def flatten_questions(data):
    return [q for section in data["sections"] for q in section["questions"]]

def check(condition, test_id, message, failures):
    status = "PASS" if condition else "FAIL"
    print(f"{test_id}: {status} — {message}")
    if not condition:
        failures.append(test_id)

def main() -> int:
    job_data = load_yaml(JOB)
    q_data = load_yaml(QUESTIONNAIRE)
    schema = load_json(SCHEMA)
    failures = []

    errors = sorted(Draft202012Validator(schema).iter_errors(q_data), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            print(f"SCHEMA ERROR at {list(error.path)}: {error.message}")
    check(not errors, "QG-T001", "questionnaire schema validation", failures)

    questions = flatten_questions(q_data)
    mandatory = {
        r["id"]: r
        for r in job_data["job"]["requirements"]["mandatory"]
        if r.get("screening_required", False)
    }
    covered = {
        rid
        for q in questions
        for rid in q.get("source_requirement_ids", [])
        if rid in mandatory
    }
    coverage_pct = round((len(covered) / len(mandatory)) * 100) if mandatory else 100
    check(coverage_pct == 100, "QG-T002", "mandatory screening coverage is 100%", failures)
    check(covered == set(mandatory), "QG-T003", "every mandatory screening requirement has a question", failures)

    mandatory_ids = set(mandatory)
    invalid_knockout = [
        q["question_id"] for q in questions
        if q["knockout"]["enabled"]
        and not set(q["source_requirement_ids"]).intersection(mandatory_ids)
    ]
    check(not invalid_knockout, "QG-T004", "knockout rules only use mandatory requirements", failures)

    orphan_technical = []
    for q in questions:
        if q["intent"] not in TECHNICAL_INTENTS:
            continue
        if q["source_origin"] == "job_requirement" and not q["source_requirement_ids"]:
            orphan_technical.append(q["question_id"])
        if q["source_origin"] == "job_tool" and not q["source_tool_names"]:
            orphan_technical.append(q["question_id"])
    check(not orphan_technical, "QG-T005", "no orphan technical questions", failures)

    canonical_tools = {t["name"] for t in job_data["job"]["tools"]}
    bad_tool_refs = [
        q["question_id"] for q in questions
        if q["source_origin"] == "job_tool"
        and not set(q["source_tool_names"]).issubset(canonical_tools)
    ]
    check(not bad_tool_refs, "QG-T006", "tool questions grounded in canonical job tools", failures)

    bad_system = [
        q["question_id"] for q in questions
        if q["source_origin"] == "system_policy"
        and (q["source_requirement_ids"] or q["source_tool_names"])
    ]
    check(not bad_system, "QG-T007", "system-policy questions stay separate from job-derived traceability", failures)

    ids = [q["question_id"] for q in questions]
    check(len(ids) == len(set(ids)), "QG-T008", "question IDs are unique", failures)
    expected_ids = [f"Q-{i:03d}" for i in range(1, len(ids) + 1)]
    check(ids == expected_ids, "QG-T009", "question order and IDs are deterministic", failures)

    labels = {q["label"] for q in questions}
    check("Current Salary" not in labels, "QG-T010", "current salary excluded from default MVP profile", failures)

    resume = next((q for q in questions if q["analytics_key"] == "resume_file"), None)
    check(
        resume is not None and resume["type"] == "file_upload_manual_template",
        "QG-T011",
        "resume upload delegated to downstream form template strategy",
        failures,
    )

    coverage = q_data["coverage"]
    check(
        coverage["unsupported_technical_questions"] == 0,
        "QG-T012",
        "unsupported technical questions reported as zero",
        failures,
    )

    print()
    if failures:
        print("QUESTIONNAIRE-GENERATOR-GATE: FAIL")
        print("Blocking tests:", ", ".join(failures))
        return 1

    print("QUESTIONNAIRE-GENERATOR-GATE: PASS")
    print("Blocking tests: 0")
    return 0

if __name__ == "__main__":
    sys.exit(main())
