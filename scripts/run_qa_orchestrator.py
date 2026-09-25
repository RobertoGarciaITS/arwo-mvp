#!/usr/bin/env python3
"""Deterministic ARWO pre-human-approval QA orchestrator."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_JOB_NORMALIZED_v0.1.yaml"
QUESTIONNAIRE = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_QUESTIONNAIRE_v0.1.yaml"
PUBLICATION = ROOT / "tests/golden/GTC001_GAMING_QA_ENGINEER/EXPECTED_PUBLICATION_v0.1.yaml"
DATA_POLICY = ROOT / "governance/DATA_BOUNDARY_POLICY_v0.1.yaml"
FORM_BUILDER = ROOT / "scripts/build_google_form_spec.py"

TECHNICAL_INTENTS = {"eligibility", "experience", "technical_coverage", "tool_proficiency", "evidence"}

def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)

def load_form_builder():
    spec = importlib.util.spec_from_file_location("arwo_form_builder", FORM_BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module

def _check(check_id: str, name: str, passed: bool, evidence: Any) -> dict:
    return {
        "check_id": check_id,
        "name": name,
        "result": "PASS" if passed else "FAIL",
        "evidence": evidence,
    }

def _gate(gate_id: str, name: str, checks: list[dict], allow_observation: bool = False) -> dict:
    failed = [c for c in checks if c["result"] == "FAIL"]
    if failed:
        result = "FAIL"
    else:
        result = "PASS_WITH_OBSERVATION" if allow_observation else "PASS"
    return {"gate_id": gate_id, "name": name, "result": result, "checks": checks}

def evaluate() -> dict:
    job = load_yaml(JOB)
    questionnaire = load_yaml(QUESTIONNAIRE)
    publication = load_yaml(PUBLICATION)
    data_policy = load_yaml(DATA_POLICY)
    form_builder = load_form_builder()
    form_spec = form_builder.build(questionnaire)

    questions = [q for s in questionnaire["sections"] for q in s["questions"]]
    mandatory = job["job"]["requirements"]["mandatory"]
    desirable = job["job"]["requirements"]["desirable"]
    unclassified = job["job"]["requirements"]["unclassified"]

    gates = []
    blocking_findings = []
    observations = []

    # GATE-01
    g1 = _gate("GATE-01", "job_completeness", [
        _check("G1-C01", "canonical_title_present", bool(job["job"]["title"]["canonical"].strip()), job["job"]["title"]["canonical"]),
        _check("G1-C02", "summary_present", bool(job["job"]["summary"].strip()), job["job"]["summary"]),
        _check("G1-C03", "mandatory_requirements_present", len(mandatory) > 0, [r["id"] for r in mandatory]),
    ])
    gates.append(g1)

    # GATE-02
    all_requirements = mandatory + desirable + unclassified
    all_categorized = all(bool(r.get("category")) for r in all_requirements)
    mandatory_ids = {r["id"] for r in mandatory}
    knockout_qs = [q for q in questions if q["knockout"]["enabled"]]
    knockout_valid = all(set(q["source_requirement_ids"]) & mandatory_ids for q in knockout_qs)
    known_ids = {"REQ-001", "REQ-002", "REQ-003", "REQ-004"}
    actual_ids = {r["id"] for r in all_requirements}
    g2 = _gate("GATE-02", "requirement_classification", [
        _check("G2-C01", "every_requirement_has_category", all_categorized, sorted(actual_ids)),
        _check("G2-C02", "knockout_only_when_mandatory", knockout_valid, [q["question_id"] for q in knockout_qs]),
        _check("G2-C03", "no_unsupported_requirements", actual_ids == known_ids, sorted(actual_ids)),
    ])
    gates.append(g2)

    # GATE-03
    screening_required = {r["id"] for r in mandatory if r.get("screening_required")}
    covered = {
        rid
        for q in questions
        for rid in q.get("source_requirement_ids", [])
        if rid in screening_required
    }
    coverage_pct = 100 if not screening_required else round(len(covered) / len(screening_required) * 100)
    g3 = _gate("GATE-03", "question_coverage", [
        _check("G3-C01", "mandatory_requirement_coverage_equals_100_percent", coverage_pct == 100, coverage_pct),
        _check("G3-C02", "screening_required_requirements_have_questions", covered == screening_required, sorted(covered)),
    ])
    gates.append(g3)

    # GATE-04
    ids = [q["question_id"] for q in questions]
    duplicate_ids = len(ids) != len(set(ids))
    orphan_technical = []
    for q in questions:
        if q["intent"] not in TECHNICAL_INTENTS:
            continue
        if q["source_origin"] == "job_requirement" and not q["source_requirement_ids"]:
            orphan_technical.append(q["question_id"])
        if q["source_origin"] == "job_tool" and not q["source_tool_names"]:
            orphan_technical.append(q["question_id"])
    supported_types = {
        "short_text","paragraph","integer","decimal","single_choice","multi_choice",
        "dropdown","date","url","email","phone","file_upload_manual_template"
    }
    type_valid = all(q["type"] in supported_types for q in questions)
    trace_ids = {t["question_id"] for t in form_spec["traceability"]}
    g4 = _gate("GATE-04", "question_consistency", [
        _check("G4-C01", "no_duplicate_question_ids", not duplicate_ids, ids),
        _check("G4-C02", "no_orphan_technical_questions", not orphan_technical, orphan_technical),
        _check("G4-C03", "question_type_matches_supported_intent_mapping", type_valid, sorted({q["type"] for q in questions})),
        _check("G4-C04", "form_build_traceability_complete", trace_ids == set(ids), sorted(trace_ids)),
    ])
    gates.append(g4)

    # GATE-05
    github_prohibited = set(data_policy["github"]["prohibited"])
    expected_prohibited = {"candidate_pii", "resumes", "real_application_payloads", "authentication_secrets"}
    current_salary_present = any(q["analytics_key"] == "current_salary" for q in questions)
    resume_deferred = any(d["analytics_key"] == "resume_file" for d in form_spec["deferred_items"])
    privacy_checks = [
        _check("G5-C01", "github_candidate_pii_prohibited", expected_prohibited.issubset(github_prohibited), sorted(github_prohibited)),
        _check("G5-C02", "sensitive_current_salary_not_in_default_profile", not current_salary_present, current_salary_present),
        _check("G5-C03", "resume_upload_explicitly_deferred", resume_deferred, [d["analytics_key"] for d in form_spec["deferred_items"]]),
    ]
    g5 = _gate("GATE-05", "privacy_review", privacy_checks, allow_observation=True)
    gates.append(g5)
    observations.append({
        "id": "QA-OBS-001",
        "gate_id": "GATE-05",
        "severity": "info",
        "text": "Resume upload remains an operational Google Forms template item and candidate files must not be stored in GitHub."
    })

    # GATE-06
    pub_content = publication["channels"][0]["content"]
    source_mandatory = {r["text"] for r in mandatory}
    published_mandatory = set(pub_content["mandatory_requirements"])
    application_url_match = pub_content["application_url"] is None
    unsupported_claims = publication["consistency"]["unsupported_claims"]
    g6_checks = [
        _check("G6-C01", "no_new_mandatory_requirements_in_publication", published_mandatory.issubset(source_mandatory), sorted(published_mandatory)),
        _check("G6-C02", "no_removed_mandatory_requirements", source_mandatory.issubset(published_mandatory), sorted(source_mandatory)),
        _check("G6-C03", "unsupported_publication_claims_zero", unsupported_claims == 0, unsupported_claims),
        _check("G6-C04", "application_link_consistent_with_current_preapproval_state", application_url_match, pub_content["application_url"]),
    ]
    g6 = _gate("GATE-06", "publication_consistency", g6_checks, allow_observation=True)
    gates.append(g6)
    observations.append({
        "id": "QA-OBS-002",
        "gate_id": "GATE-06",
        "severity": "info",
        "text": "Application URL is not yet assigned; publication therefore remains draft and cannot be externally published."
    })

    for gate in gates:
        for check in gate["checks"]:
            if check["result"] == "FAIL":
                blocking_findings.append({
                    "gate_id": gate["gate_id"],
                    "check_id": check["check_id"],
                    "severity": "blocking",
                    "evidence": check["evidence"],
                })

    ready = not blocking_findings and all(g["result"] in {"PASS", "PASS_WITH_OBSERVATION"} for g in gates)

    return {
        "report_id": "QA-JOB-GQA-001-v0.1",
        "job_id": job["job_id"],
        "version": "0.1",
        "stage": "pre_human_approval",
        "overall_result": "READY_FOR_HUMAN_APPROVAL" if ready else "BLOCKED",
        "gates": gates,
        "blocking_findings": blocking_findings,
        "observations": observations,
        "traceability_summary": {
            "job_id_consistent": questionnaire["job_id"] == job["job_id"] == publication["job_id"],
            "mandatory_requirements_total": len(screening_required),
            "mandatory_requirements_covered": len(covered),
            "mandatory_screening_coverage_percent": coverage_pct,
            "questionnaire_questions_total": len(questions),
            "form_traceability_entries": len(form_spec["traceability"]),
            "publication_mandatory_requirements_total": len(published_mandatory),
        },
        "next_action": "CHUNK-07 Human Approval" if ready else "Resolve blocking QA findings",
    }

if __name__ == "__main__":
    print(yaml.safe_dump(evaluate(), sort_keys=False, allow_unicode=True))
