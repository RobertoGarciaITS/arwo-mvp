#!/usr/bin/env python3
"""Validate ARWO CHUNK-07 Human Approval mechanism."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/build_approval_manifest.py"
SCHEMA = ROOT / "schemas/APPROVAL_OUTPUT_SCHEMA_v0.1.json"

def load_module():
    spec = importlib.util.spec_from_file_location("approval_manifest", MODULE_PATH)
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
    module = load_module()
    approval = module.build_synthetic_approval()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    failures = []

    errors = sorted(Draft202012Validator(schema).iter_errors(approval), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            print(f"SCHEMA ERROR at {list(error.path)}: {error.message}")
    check(not errors, "HA-T001", "approval schema valid", failures)

    artifacts = approval["manifest"]["artifacts"]
    check(len(artifacts) == 5, "HA-T002", "five required artifacts bound", failures)

    hash_re = re.compile(r"^[a-f0-9]{64}$")
    check(all(hash_re.match(a["sha256"]) for a in artifacts), "HA-T003", "all SHA-256 hashes valid", failures)
    check(bool(hash_re.match(approval["manifest"]["manifest_digest"])), "HA-T004", "manifest digest valid", failures)
    check(approval["reviewer"]["identity"] == "GOLDEN_TEST_ONLY", "HA-T005", "synthetic reviewer identity present", failures)
    check(approval["publication_authorization"]["channels"] == ["linkedin_social"], "HA-T006", "authorized channel present", failures)
    check(approval["status"] == "approved" and approval["gate_07"]["result"] == "PASS", "HA-T007", "approved state sets GATE-07 PASS", failures)
    check(module.validate_mutation_detection(approval), "HA-T008", "artifact mutation invalidates approval", failures)

    qa_not_ready = {"overall_result": "BLOCKED", "blocking_findings": [{"id": "synthetic"}]}
    blocked = not module.approval_allowed(qa_not_ready, "reviewer", ["linkedin_social"])
    check(blocked, "HA-T009", "approval blocked when QA not ready", failures)

    fixture_marked = (
        "GOLDEN-TEST" in approval["approval_id"]
        and approval["reviewer"]["role"] == "synthetic_test_reviewer"
        and "Synthetic" in (approval["decision"]["comments"] or "")
    )
    check(fixture_marked, "HA-T010", "approval explicitly marked as test fixture", failures)

    print()
    if failures:
        print("HUMAN-APPROVAL-GATE: FAIL")
        print("Blocking tests:", ", ".join(failures))
        return 1

    print("HUMAN-APPROVAL-GATE: PASS")
    print("Blocking tests: 0")
    print("Synthetic GATE-07 result:", approval["gate_07"]["result"])
    return 0

if __name__ == "__main__":
    sys.exit(main())
