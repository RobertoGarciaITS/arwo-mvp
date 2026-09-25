#!/usr/bin/env python3
"""Validate ARWO Phase-02 runtime configuration and secrets baseline."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/RUNTIME_CONFIG_SCHEMA_v0.1.json"
ENV_EXAMPLE = ROOT / "config/runtime.env.example"
SECRETS = ROOT / "governance/SECRETS_REGISTRY_v0.1.yaml"
ENV_POLICY = ROOT / "governance/ENVIRONMENT_POLICY_v0.1.yaml"
IAM = ROOT / "governance/IAM_RUNTIME_ROLE_MATRIX_v0.1.yaml"
DATA_POLICY = ROOT / "governance/DATA_BOUNDARY_POLICY_v0.1.yaml"
RUNTIME_CONTRACT = ROOT / "architecture/RUNTIME_CONFIGURATION_CONTRACT_v0.1.yaml"

SECRET_NAMES = {
    "ARWO_GOOGLE_OAUTH_CLIENT_SECRET",
    "ARWO_GOOGLE_OAUTH_REFRESH_TOKEN",
    "ARWO_PUBLICATION_ACCESS_TOKEN",
}

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def parse_env(path: Path) -> dict[str, str]:
    result = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result

def as_bool(value: str) -> bool:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ValueError(f"Invalid boolean value: {value}")

def typed_config(raw: dict[str, str]) -> dict:
    bool_keys = {
        "ARWO_GOOGLE_FORMS_ENABLED",
        "ARWO_GOOGLE_DRIVE_ENABLED",
        "ARWO_GMAIL_ENABLED",
        "ARWO_PUBLICATION_ENABLED",
    }
    nullable_keys = {"ARWO_DRIVE_ROOT_FOLDER_ID", "ARWO_FORM_TEMPLATE_ID"}
    result = {}
    for key, value in raw.items():
        if key in bool_keys:
            result[key] = as_bool(value)
        elif key in nullable_keys:
            result[key] = value or None
        else:
            result[key] = value
    return result

def check(condition: bool, test_id: str, message: str, failures: list[str]):
    status = "PASS" if condition else "FAIL"
    print(f"{test_id}: {status} — {message}")
    if not condition:
        failures.append(test_id)

def main() -> int:
    failures: list[str] = []
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    raw_env = parse_env(ENV_EXAMPLE)
    config = typed_config(raw_env)
    secrets = load_yaml(SECRETS)
    env_policy = load_yaml(ENV_POLICY)
    iam = load_yaml(IAM)
    data_policy = load_yaml(DATA_POLICY)
    runtime_contract = load_yaml(RUNTIME_CONTRACT)

    errors = sorted(Draft202012Validator(schema).iter_errors(config), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            print(f"SCHEMA ERROR at {list(error.path)}: {error.message}")
    check(not errors, "P2RS-T001", "runtime config example validates against schema", failures)

    check(config["ARWO_ENVIRONMENT"] == "sandbox", "P2RS-T002", "example environment is sandbox", failures)
    check(config["ARWO_PUBLICATION_ENABLED"] is False, "P2RS-T003", "publication disabled by default", failures)

    env_text = ENV_EXAMPLE.read_text(encoding="utf-8")
    secret_values_absent = all(
        secret_name not in raw_env or raw_env.get(secret_name, "") == ""
        for secret_name in SECRET_NAMES
    )
    check(secret_values_absent, "P2RS-T004", "no secret values in committed example", failures)

    all_secret_rules = all(
        item.get("repository_value_allowed") is False
        for item in secrets["secrets"]
    )
    check(all_secret_rules, "P2RS-T005", "all registered secrets forbid repository values", failures)

    prod = env_policy["environments"]["production"]
    check(
        prod["publication"] == "allowed_only_with_real_human_approval",
        "P2RS-T006",
        "production publication requires real human approval",
        failures,
    )

    runtime_service = next(
        item for item in iam["runtime_identities"]
        if item["id"] == "ARWO-RUNTIME-SERVICE"
    )
    check(
        "unrestricted_project_owner" in runtime_service["prohibited"],
        "P2RS-T007",
        "runtime service identity cannot be unrestricted project owner",
        failures,
    )

    check(
        iam["controls"]["separate_deployer_and_runtime_identity"] is True,
        "P2RS-T008",
        "deployer and runtime identities are separated",
        failures,
    )

    github_prohibited = set(data_policy["github"]["prohibited"])
    check(
        "candidate_pii" in github_prohibited and "resumes" in github_prohibited,
        "P2RS-T009",
        "candidate PII and resumes remain outside GitHub",
        failures,
    )

    declared_refs = set(runtime_contract["secret_references"])
    registry_refs = {item["logical_name"] for item in secrets["secrets"]}
    check(
        declared_refs == registry_refs == SECRET_NAMES,
        "P2RS-T010",
        "runtime contract and secret registry reference the same secret names",
        failures,
    )

    print()
    if failures:
        print("P2-GATE-01-RUNTIME-SECURITY: FAIL")
        print("Blocking tests:", ", ".join(failures))
        return 1

    print("P2-GATE-01-RUNTIME-SECURITY: PASS")
    print("Blocking tests: 0")
    return 0

if __name__ == "__main__":
    sys.exit(main())
