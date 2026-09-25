#!/usr/bin/env python3
"""Validate ARWO CHUNK-06 QA Orchestrator output."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "scripts/run_qa_orchestrator.py"
SCHEMA = ROOT / "schemas/QA_REPORT_SCHEMA_v0.1.json"

def load_module():
    spec = importlib.util.spec_from_file_location("arwo_qa_orchestrator", ORCH)
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
    report = load_module().evaluate()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    failures = []

    errors = sorted(Draft202012Validator(schema).iter_errors(report), key=lambda e: list(e.path))
    if errors:
        for e in errors:
            print(f"SCHEMA ERROR at {list(e.path)}: {e.message}")
    check(not errors, "QAO-T001", "QA report schema valid", failures)

    gates = {g["gate_id"]: g for g in report["gates"]}
    check(set(gates) == {"GATE-01","GATE-02","GATE-03","GATE-04","GATE-05","GATE-06"}, "QAO-T002", "six pre-approval gates present", failures)
    check(gates["GATE-01"]["result"] == "PASS", "QAO-T003", "job completeness passes", failures)
    check(gates["GATE-02"]["result"] == "PASS", "QAO-T004", "requirement classification passes", failures)
    check(report["traceability_summary"]["mandatory_screening_coverage_percent"] == 100, "QAO-T005", "mandatory screening coverage is 100%", failures)
    check(gates["GATE-04"]["result"] == "PASS", "QAO-T006", "question consistency passes", failures)
    check(gates["GATE-05"]["result"] in {"PASS","PASS_WITH_OBSERVATION"}, "QAO-T007", "privacy gate non-blocking", failures)
    check(gates["GATE-06"]["result"] in {"PASS","PASS_WITH_OBSERVATION"}, "QAO-T008", "publication consistency non-blocking", failures)
    check(len(report["blocking_findings"]) == 0, "QAO-T009", "no blocking findings", failures)
    check(report["overall_result"] == "READY_FOR_HUMAN_APPROVAL", "QAO-T010", "package ready for human approval", failures)
    check("GATE-07" not in gates, "QAO-T011", "GATE-07 intentionally not executed", failures)
    check(report["traceability_summary"]["job_id_consistent"] is True, "QAO-T012", "cross-artifact job_id consistent", failures)

    print()
    if failures:
        print("QA-ORCHESTRATOR-GATE: FAIL")
        print("Blocking tests:", ", ".join(failures))
        return 1

    print("QA-ORCHESTRATOR-GATE: PASS")
    print("Blocking tests: 0")
    print("Overall result:", report["overall_result"])
    return 0

if __name__ == "__main__":
    sys.exit(main())
