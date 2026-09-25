#!/usr/bin/env python3
"""Validate ARWO CHUNK-08 Controlled Publication release gate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/build_publication_execution_plan.py"
SCHEMA = ROOT / "schemas/PUBLICATION_EXECUTION_PLAN_SCHEMA_v0.1.json"
APPROVAL_MODULE = ROOT / "scripts/build_approval_manifest.py"

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
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
    module = load_module(MODULE_PATH, "release_gate")
    approval_module = load_module(APPROVAL_MODULE, "approval_fixture")
    plan = module.build_execution_plan()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    failures = []

    errors = sorted(Draft202012Validator(schema).iter_errors(plan), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            print(f"SCHEMA ERROR at {list(error.path)}: {error.message}")
    check(not errors, "CP-T001", "execution plan schema valid", failures)

    approval = approval_module.build_synthetic_approval()
    check(approval["status"] == "approved", "CP-T002", "approved status required", failures)
    check(approval["gate_07"]["result"] == "PASS", "CP-T003", "GATE-07 PASS required", failures)

    digest_check = next(c for c in plan["checks"] if c["check_id"] == "CP-C03")
    hash_check = next(c for c in plan["checks"] if c["check_id"] == "CP-C04")
    channel_check = next(c for c in plan["checks"] if c["check_id"] == "CP-C05")
    check(digest_check["result"] == "PASS", "CP-T004", "exact manifest digest matches", failures)
    check(hash_check["result"] == "PASS", "CP-T005", "all artifact hashes match", failures)
    check(channel_check["result"] == "PASS", "CP-T006", "requested channel authorized", failures)

    plan2 = module.build_execution_plan()
    check(plan["idempotency_key"] == plan2["idempotency_key"], "CP-T007", "idempotency key deterministic", failures)

    mutated = module.build_execution_plan(current_manifest=module.mutated_manifest())
    check(
        mutated["status"] == "BLOCKED" and len(mutated["blocking_findings"]) > 0,
        "CP-T008",
        "artifact mutation blocks execution",
        failures,
    )

    unauthorized = module.build_execution_plan(requested_channel="company_site")
    check(
        unauthorized["status"] == "BLOCKED",
        "CP-T009",
        "unauthorized channel blocks execution",
        failures,
    )

    # Static test code only creates a plan and contains no external publishing call.
    check(
        plan["status"] != "EXECUTED",
        "CP-T010",
        "static CI does not execute an external action",
        failures,
    )

    synthetic_marker = (
        "GOLDEN-TEST" in plan["approval_id"]
        and "real human approval" in plan["next_action"].lower()
    )
    check(
        synthetic_marker,
        "CP-T011",
        "synthetic fixture explicitly nonproduction",
        failures,
    )

    check(
        plan["status"] == "READY_FOR_CONTROLLED_EXECUTION" and len(plan["blocking_findings"]) == 0,
        "CP-T012",
        "ready state returned when all release checks pass",
        failures,
    )

    print()
    if failures:
        print("CONTROLLED-PUBLICATION-GATE: FAIL")
        print("Blocking tests:", ", ".join(failures))
        return 1

    print("CONTROLLED-PUBLICATION-GATE: PASS")
    print("Blocking tests: 0")
    print("Release state:", plan["status"])
    print("External action executed: false")
    return 0

if __name__ == "__main__":
    sys.exit(main())
