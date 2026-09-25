#!/usr/bin/env python3
"""Generate and validate deterministic ARWO approval manifests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
JOB_PATH = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_JOB_NORMALIZED_v0.1.yaml"
QUESTIONNAIRE_PATH = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_QUESTIONNAIRE_v0.1.yaml"
PUBLICATION_PATH = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_PUBLICATION_v0.1.yaml"
FORM_BUILDER_PATH = ROOT / "scripts/build_google_form_spec.py"
QA_ORCH_PATH = ROOT / "scripts/run_qa_orchestrator.py"

def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _file_bytes(path: Path) -> bytes:
    return path.read_bytes()

def _artifact(artifact_id: str, artifact_type: str, version: str, path: str, payload: bytes) -> dict:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "version": version,
        "path": path,
        "sha256": _sha256_bytes(payload),
    }

def build_manifest() -> dict:
    questionnaire = yaml.safe_load(QUESTIONNAIRE_PATH.read_text(encoding="utf-8"))
    form_builder = _load_module(FORM_BUILDER_PATH, "arwo_form_builder_for_approval")
    qa_orch = _load_module(QA_ORCH_PATH, "arwo_qa_orch_for_approval")

    form_spec = form_builder.build(questionnaire)
    qa_report = qa_orch.evaluate()

    artifacts = [
        _artifact(
            "APP-ART-001", "job_contract", "0.1",
            "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_JOB_NORMALIZED_v0.1.yaml",
            _file_bytes(JOB_PATH),
        ),
        _artifact(
            "APP-ART-002", "questionnaire_contract", "0.1",
            "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_QUESTIONNAIRE_v0.1.yaml",
            _file_bytes(QUESTIONNAIRE_PATH),
        ),
        _artifact(
            "APP-ART-003", "form_build_spec", "0.1",
            "generated://GTC001/FORM_BUILD_SPEC_v0.1.json",
            _canonical_json_bytes(form_spec),
        ),
        _artifact(
            "APP-ART-004", "publication_contract", "0.1",
            "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_PUBLICATION_v0.1.yaml",
            _file_bytes(PUBLICATION_PATH),
        ),
        _artifact(
            "APP-ART-005", "qa_report", "0.1",
            "generated://GTC001/QA_REPORT_v0.1.json",
            _canonical_json_bytes(qa_report),
        ),
    ]
    manifest_digest = _sha256_bytes(_canonical_json_bytes(artifacts))
    return {
        "hash_algorithm": "sha256",
        "artifacts": artifacts,
        "manifest_digest": manifest_digest,
    }

def build_synthetic_approval() -> dict:
    qa_orch = _load_module(QA_ORCH_PATH, "arwo_qa_orch_for_approval_decision")
    qa_report = qa_orch.evaluate()
    if qa_report["overall_result"] != "READY_FOR_HUMAN_APPROVAL" or qa_report["blocking_findings"]:
        raise RuntimeError("QA package is not ready for human approval")

    manifest = build_manifest()
    return {
        "approval_id": "APP-GQA-001-GOLDEN-TEST",
        "job_id": "JOB-GQA-001",
        "version": "0.1",
        "status": "approved",
        "requested_at": "2026-09-25T00:00:00Z",
        "manifest": manifest,
        "reviewer": {
            "role": "synthetic_test_reviewer",
            "identity": "GOLDEN_TEST_ONLY"
        },
        "decision": {
            "decided_at": "2026-09-25T00:00:01Z",
            "comments": "Synthetic approval used only to validate the CHUNK-07 mechanism."
        },
        "publication_authorization": {
            "allowed": True,
            "channels": ["linkedin_social"]
        },
        "gate_07": {
            "result": "PASS",
            "reason": "Synthetic golden-test approval satisfies exact-manifest binding rules."
        }
    }

def validate_manifest_current(approval: dict) -> bool:
    return approval["manifest"] == build_manifest()

def validate_mutation_detection(approval: dict) -> bool:
    tampered = json.loads(json.dumps(approval))
    tampered["manifest"]["artifacts"][0]["sha256"] = "0" * 64
    return not validate_manifest_current(tampered)

def approval_allowed(qa_report: dict, reviewer_identity: str | None, channels: list[str]) -> bool:
    return (
        qa_report["overall_result"] == "READY_FOR_HUMAN_APPROVAL"
        and not qa_report["blocking_findings"]
        and bool(reviewer_identity)
        and bool(channels)
    )

if __name__ == "__main__":
    print(yaml.safe_dump(build_synthetic_approval(), sort_keys=False, allow_unicode=True))
