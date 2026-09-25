#!/usr/bin/env python3
"""Build deterministic controlled-publication execution plans for ARWO."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APPROVAL_MODULE = ROOT / "scripts/build_approval_manifest.py"
PUBLICATION_PATH = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_PUBLICATION_v0.1.yaml"

def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module

def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def _idempotency_key(approval_id: str, manifest_digest: str, requested_channel: str, publication_id: str) -> str:
    payload = {
        "approval_id": approval_id,
        "manifest_digest": manifest_digest,
        "requested_channel": requested_channel,
        "publication_id": publication_id,
    }
    return _sha256(_canonical_json_bytes(payload))

def build_execution_plan(
    requested_channel: str = "linkedin_social",
    approval: dict | None = None,
    current_manifest: dict | None = None,
) -> dict:
    approval_module = _load_module(APPROVAL_MODULE, "arwo_approval_for_release")
    approval = approval or approval_module.build_synthetic_approval()
    current_manifest = current_manifest or approval_module.build_manifest()

    publication = __import__("yaml").safe_load(PUBLICATION_PATH.read_text(encoding="utf-8"))

    checks = []
    blocking = []

    def add_check(check_id: str, name: str, passed: bool, evidence: Any):
        result = "PASS" if passed else "FAIL"
        checks.append({
            "check_id": check_id,
            "name": name,
            "result": result,
            "evidence": evidence,
        })
        if not passed:
            blocking.append({
                "check_id": check_id,
                "severity": "blocking",
                "evidence": evidence,
            })

    add_check(
        "CP-C01",
        "approval_status_approved",
        approval.get("status") == "approved",
        approval.get("status"),
    )
    add_check(
        "CP-C02",
        "gate_07_pass",
        approval.get("gate_07", {}).get("result") == "PASS",
        approval.get("gate_07", {}).get("result"),
    )
    add_check(
        "CP-C03",
        "manifest_digest_match",
        approval.get("manifest", {}).get("manifest_digest") == current_manifest.get("manifest_digest"),
        {
            "approved": approval.get("manifest", {}).get("manifest_digest"),
            "current": current_manifest.get("manifest_digest"),
        },
    )

    approved_hashes = {
        a["artifact_id"]: a["sha256"]
        for a in approval.get("manifest", {}).get("artifacts", [])
    }
    current_hashes = {
        a["artifact_id"]: a["sha256"]
        for a in current_manifest.get("artifacts", [])
    }
    add_check(
        "CP-C04",
        "all_artifact_hashes_match",
        approved_hashes == current_hashes,
        {
            "approved_artifact_count": len(approved_hashes),
            "current_artifact_count": len(current_hashes),
        },
    )

    authorization = approval.get("publication_authorization", {})
    channel_authorized = (
        authorization.get("allowed") is True
        and requested_channel in authorization.get("channels", [])
    )
    add_check(
        "CP-C05",
        "requested_channel_authorized",
        channel_authorized,
        {
            "requested_channel": requested_channel,
            "authorized_channels": authorization.get("channels", []),
        },
    )

    synthetic_fixture = (
        approval.get("reviewer", {}).get("role") == "synthetic_test_reviewer"
        and "GOLDEN-TEST" in approval.get("approval_id", "")
    )
    add_check(
        "CP-C06",
        "fixture_is_explicitly_synthetic",
        synthetic_fixture,
        approval.get("approval_id"),
    )

    ready = not blocking
    idem = _idempotency_key(
        approval["approval_id"],
        approval["manifest"]["manifest_digest"],
        requested_channel,
        publication["publication_id"],
    )

    return {
        "execution_plan_id": f"EXEC-{publication['publication_id']}-{requested_channel}-v0.1",
        "job_id": publication["job_id"],
        "publication_id": publication["publication_id"],
        "approval_id": approval["approval_id"],
        "requested_channel": requested_channel,
        "status": "READY_FOR_CONTROLLED_EXECUTION" if ready else "BLOCKED",
        "manifest_digest": approval["manifest"]["manifest_digest"],
        "idempotency_key": idem,
        "checks": checks,
        "blocking_findings": blocking,
        "next_action": (
            "Production runtime must obtain a real human approval and authorized external adapter before execution."
            if ready
            else "Resolve blocking release-gate findings and obtain a new approval if artifacts changed."
        ),
    }

def mutated_manifest() -> dict:
    approval_module = _load_module(APPROVAL_MODULE, "arwo_approval_for_mutation")
    manifest = copy.deepcopy(approval_module.build_manifest())
    manifest["artifacts"][0]["sha256"] = "0" * 64
    manifest["manifest_digest"] = _sha256(_canonical_json_bytes(manifest["artifacts"]))
    return manifest

if __name__ == "__main__":
    import yaml
    print(yaml.safe_dump(build_execution_plan(), sort_keys=False, allow_unicode=True))
