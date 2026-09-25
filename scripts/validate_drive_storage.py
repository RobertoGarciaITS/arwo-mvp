#!/usr/bin/env python3
"""Validate ARWO Phase-02 Google Drive storage baseline."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "integrations/google_drive/DRIVE_STORAGE_CONTRACT_v0.1.yaml"
CLASSIFICATION = ROOT / "governance/DRIVE_DATA_CLASSIFICATION_POLICY_v0.1.yaml"
ACCESS = ROOT / "governance/DRIVE_FOLDER_ACCESS_MATRIX_v0.1.yaml"
DATA_POLICY = ROOT / "governance/DATA_BOUNDARY_POLICY_v0.1.yaml"
SCHEMA = ROOT / "schemas/DRIVE_JOB_STORAGE_MANIFEST_SCHEMA_v0.1.json"
MANIFEST = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_DRIVE_STORAGE_MANIFEST_v0.1.yaml"

REQUIRED_CHILDREN = {
    "source","normalized","forms","publications",
    "approvals","candidates","responses","audit"
}

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def check(condition: bool, test_id: str, message: str, failures: list[str]):
    status = "PASS" if condition else "FAIL"
    print(f"{test_id}: {status} — {message}")
    if not condition:
        failures.append(test_id)

def main() -> int:
    failures = []
    contract = load_yaml(CONTRACT)
    classification = load_yaml(CLASSIFICATION)
    access = load_yaml(ACCESS)
    data_policy = load_yaml(DATA_POLICY)
    manifest = load_yaml(MANIFEST)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    children = set(contract["job_folder_pattern"]["required_children"])
    check(children == REQUIRED_CHILDREN, "P2DS-T001", "required job folder structure defined", failures)

    check(
        manifest["folders"]["candidates"]["restricted"] is True
        and manifest["folders"]["responses"]["restricted"] is True,
        "P2DS-T002",
        "candidate and response folders restricted",
        failures,
    )

    check(
        manifest["folders"]["approvals"]["restricted"] is True,
        "P2DS-T003",
        "approvals folder restricted",
        failures,
    )

    github_prohibited = set(data_policy["github"]["prohibited"])
    check(
        "candidate_pii" in github_prohibited and "real_application_payloads" in github_prohibited,
        "P2DS-T004",
        "candidate PII and real application payloads prohibited in GitHub",
        failures,
    )

    rules = classification["rules"]
    check(
        rules["candidate_pii_public_sharing"] == "prohibited",
        "P2DS-T005",
        "public link sharing prohibited for candidate PII",
        failures,
    )

    naming = contract["naming"]
    controlled_ok = (
        "{job_id}" in naming["artifact_pattern"]
        and "{version}" in naming["artifact_pattern"]
        and contract["controls"]["checksum_required_for_controlled_artifacts"] is True
    )
    check(
        controlled_ok,
        "P2DS-T006",
        "controlled artifacts require job_id, version and checksum",
        failures,
    )

    runtime = access["roles"]["runtime_service"]
    controlled_access = runtime["candidates"] == "controlled" and runtime["responses"] == "controlled"
    check(
        controlled_access,
        "P2DS-T007",
        "runtime service candidate/response access is controlled",
        failures,
    )

    errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            print(f"SCHEMA ERROR at {list(error.path)}: {error.message}")
    check(not errors, "P2DS-T008", "storage manifest schema valid", failures)

    check(
        contract["controls"]["source_immutable"] is True,
        "P2DS-T009",
        "source folder content is governed as immutable",
        failures,
    )

    check(
        classification["rules"]["real_candidate_data_never_in_test_fixtures"] is True,
        "P2DS-T010",
        "real candidate data forbidden in test fixtures",
        failures,
    )

    print()
    if failures:
        print("P2-GATE-02-DRIVE-STORAGE: FAIL")
        print("Blocking tests:", ", ".join(failures))
        return 1

    print("P2-GATE-02-DRIVE-STORAGE: PASS")
    print("Blocking tests: 0")
    return 0

if __name__ == "__main__":
    sys.exit(main())
