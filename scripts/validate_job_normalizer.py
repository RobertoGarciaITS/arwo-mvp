#!/usr/bin/env python3
"""Deterministic validation for ARWO CHUNK-02 Job Normalizer."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_JOB_NORMALIZED_v0.1.yaml"
SCHEMA = ROOT / "schemas/JOB_NORMALIZER_OUTPUT_SCHEMA_v0.1.json"

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def check(condition: bool, test_id: str, message: str, failures: list[str]):
    status = "PASS" if condition else "FAIL"
    print(f"{test_id}: {status} — {message}")
    if not condition:
        failures.append(test_id)

def main() -> int:
    data = load_yaml(EXPECTED)
    schema = load_json(SCHEMA)
    failures: list[str] = []

    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            print(f"SCHEMA ERROR at {list(error.path)}: {error.message}")
    check(not errors, "JN-T009", "output schema validation", failures)

    job = data["job"]
    check(job["title"]["canonical"] == "Gaming QA Engineer", "JN-T001", "canonical title", failures)

    mandatory = job["requirements"]["mandatory"]
    mandatory_by_id = {item["id"]: item for item in mandatory}
    check("REQ-003" in mandatory_by_id, "JN-T002", "multiplayer requirement preserved", failures)
    check(
        mandatory_by_id.get("REQ-003", {}).get("knockout") is True,
        "JN-T003",
        "mandatory multiplayer requirement not downgraded",
        failures,
    )

    exp = job["experience"]
    check(
        exp.get("professional_years_min") is None and exp.get("domain_years_min") is None,
        "JN-T004",
        "no numeric experience invented",
        failures,
    )

    check(job["location"]["mode"] == "unspecified", "JN-T005", "no location invented", failures)

    tools = {item["name"] for item in job["tools"]}
    check(
        tools == {"Postman", "Swagger", "Jira", "ClickUp"},
        "JN-T006",
        "expected tool set extracted",
        failures,
    )

    allowed_requirement_ids = {"REQ-001", "REQ-002", "REQ-003", "REQ-004"}
    found_ids = {
        item["id"]
        for group in ("mandatory", "desirable", "unclassified")
        for item in job["requirements"][group]
    }
    check(found_ids == allowed_requirement_ids, "JN-T007", "no unsupported requirements", failures)

    ordered_ids = [
        item["id"]
        for group in ("mandatory", "desirable", "unclassified")
        for item in job["requirements"][group]
    ]
    check(ordered_ids == ["REQ-001", "REQ-002", "REQ-003", "REQ-004"], "JN-T008", "stable requirement IDs", failures)

    warnings = {item.get("code") for item in data.get("warnings", [])}
    check("JN-W001" in warnings, "JN-T010", "reconstructed-source warning present", failures)

    print()
    if failures:
        print("JOB-NORMALIZER-GATE: FAIL")
        print("Blocking tests:", ", ".join(failures))
        return 1

    print("JOB-NORMALIZER-GATE: PASS")
    print("Blocking tests: 0")
    return 0

if __name__ == "__main__":
    sys.exit(main())
