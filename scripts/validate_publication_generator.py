#!/usr/bin/env python3
"""Deterministic validation for ARWO CHUNK-05 Publication Generator."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_JOB_NORMALIZED_v0.1.yaml"
PUBLICATION = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_PUBLICATION_v0.1.yaml"
SCHEMA = ROOT / "schemas/PUBLICATION_OUTPUT_SCHEMA_v0.1.json"
POLICY = ROOT / "policies/PUBLICATION_GENERATION_POLICY_v0.1.yaml"

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def check(condition, test_id, message, failures):
    status = "PASS" if condition else "FAIL"
    print(f"{test_id}: {status} — {message}")
    if not condition:
        failures.append(test_id)

def main() -> int:
    job = load_yaml(JOB)
    pub = load_yaml(PUBLICATION)
    schema = load_json(SCHEMA)
    policy = load_yaml(POLICY)
    failures = []

    errors = sorted(Draft202012Validator(schema).iter_errors(pub), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            print(f"SCHEMA ERROR at {list(error.path)}: {error.message}")
    check(not errors, "PG-T001", "publication schema validation", failures)

    channel = pub["channels"][0]
    content = channel["content"]
    canonical_title = job["job"]["title"]["canonical"]
    check(content["title"] == canonical_title, "PG-T002", "canonical title preserved", failures)

    source_mandatory = [r["text"] for r in job["job"]["requirements"]["mandatory"]]
    published_mandatory = content["mandatory_requirements"]
    check(
        set(source_mandatory).issubset(set(published_mandatory)),
        "PG-T003",
        "all mandatory requirements preserved",
        failures,
    )
    check(
        set(published_mandatory).issubset(set(source_mandatory)),
        "PG-T004",
        "no extra mandatory requirements",
        failures,
    )

    serialized = json.dumps(content).lower()
    location_tokens = [x for x in [job["job"]["location"].get("city"), job["job"]["location"].get("region"), job["job"]["location"].get("country")] if x]
    if not location_tokens and job["job"]["location"]["mode"] == "unspecified":
        check(
            not any(token in serialized for token in ["remote", "hybrid", "onsite", "on-site"]),
            "PG-T005",
            "no unsupported location claim",
            failures,
        )
    else:
        check(True, "PG-T005", "location claim grounded or absent", failures)

    compensation = job["job"]["compensation"]
    if all(compensation.get(k) is None for k in ("currency", "min", "max")):
        money_pattern = re.compile(r"\$|mxn|usd|salary range|compensation of")
        check(not money_pattern.search(serialized), "PG-T006", "no unsupported compensation claim", failures)
    else:
        check(True, "PG-T006", "compensation grounded or absent", failures)

    employment_type = job["job"].get("employment_type")
    if employment_type is None:
        check(
            not any(token in serialized for token in ["full-time", "part-time", "contractor", "contract role"]),
            "PG-T007",
            "no unsupported employment type claim",
            failures,
        )
    else:
        check(True, "PG-T007", "employment type grounded or absent", failures)

    years_pattern = re.compile(r"\b\d+\+?\s*(?:years?|yrs?)\b")
    check(not years_pattern.search(serialized), "PG-T008", "no invented experience years", failures)

    expected_url = None
    check(content["application_url"] == expected_url, "PG-T009", "application URL preserved", failures)
    check(pub["status"] == "draft", "PG-T010", "default publication status is draft", failures)
    check(pub["consistency"]["unsupported_claims"] == 0, "PG-T011", "unsupported claims reported as zero", failures)

    linkedin_profile = policy["channel_profiles"]["linkedin_social"]
    headline_ok = len(content["headline"] or "") <= linkedin_profile["headline_max_chars"]
    summary_ok = len(content["summary"]) <= linkedin_profile["summary_max_chars"]
    check(headline_ok and summary_ok, "PG-T012", "LinkedIn profile length limits respected", failures)

    print()
    if failures:
        print("PUBLICATION-GENERATOR-GATE: FAIL")
        print("Blocking tests:", ", ".join(failures))
        return 1

    print("PUBLICATION-GENERATOR-GATE: PASS")
    print("Blocking tests: 0")
    return 0

if __name__ == "__main__":
    sys.exit(main())
