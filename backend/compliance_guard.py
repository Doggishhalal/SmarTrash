"""
Compliance & No-Cost Guard
==========================
Prüft Datenschutz-/Kosten-Risiken mit kostenlosen, lokalen Checks.
"""
import os
from pathlib import Path
from typing import Dict, List

from safety_config import get_config


REQUIREMENTS_PATH = Path(__file__).parent / "requirements.txt"

PAID_KEYWORDS = [
    "openai", "anthropic", "azure-ai", "google-cloud-vision", "boto3", "aws", "clarifai"
]

SUSPICIOUS_ENV_VARS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "CLARIFAI_PAT",
]

FREE_SOURCES = [
    "Wikipedia REST API",
    "DBpedia SPARQL",
    "OpenFoodFacts",
]


def _read_requirements() -> List[str]:
    if not REQUIREMENTS_PATH.exists():
        return []
    lines = []
    for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line.lower())
    return lines


def check_no_cost_policy() -> Dict:
    cfg = get_config()
    reqs = _read_requirements()

    paid_packages = []
    for req in reqs:
        if any(keyword in req for keyword in PAID_KEYWORDS):
            paid_packages.append(req)

    env_hits = []
    for env_name in SUSPICIOUS_ENV_VARS:
        if os.environ.get(env_name):
            env_hits.append(env_name)

    ok_no_cost = cfg.no_cost_mode and (not cfg.allow_paid_integrations) and len(paid_packages) == 0

    warnings = []
    if not cfg.no_cost_mode:
        warnings.append("no_cost_mode_disabled")
    if cfg.allow_paid_integrations:
        warnings.append("paid_integrations_allowed")
    if paid_packages:
        warnings.append("potential_paid_packages_detected")
    if env_hits:
        warnings.append("external_paid_api_keys_present")

    return {
        "ok": ok_no_cost,
        "free_sources": FREE_SOURCES,
        "paid_packages_detected": paid_packages,
        "paid_api_key_env_detected": env_hits,
        "warnings": warnings,
        "config": {
            "no_cost_mode": cfg.no_cost_mode,
            "allow_paid_integrations": cfg.allow_paid_integrations,
        },
    }


def check_privacy_policy() -> Dict:
    cfg = get_config()

    warnings = []
    if cfg.store_images_with_person:
        warnings.append("person_image_storage_enabled")
    if cfg.data_retention_days > 90:
        warnings.append("retention_period_long")

    return {
        "ok": len(warnings) == 0,
        "warnings": warnings,
        "config": {
            "store_images_with_person": cfg.store_images_with_person,
            "data_retention_days": cfg.data_retention_days,
        },
        "recommendation": "Personenbilder nicht speichern und Retention kurz halten (z.B. 30 Tage).",
    }


def build_compliance_report() -> Dict:
    no_cost = check_no_cost_policy()
    privacy = check_privacy_policy()

    checks = [
        {"name": "no_cost_policy", "ok": no_cost["ok"]},
        {"name": "privacy_policy", "ok": privacy["ok"]},
    ]

    issues = []
    if not no_cost["ok"]:
        issues.extend(no_cost["warnings"])
    if not privacy["ok"]:
        issues.extend(privacy["warnings"])

    score = sum(1 for c in checks if c["ok"]) / len(checks)

    return {
        "score": score,
        "compliant": score == 1.0,
        "checks": checks,
        "issues": sorted(list(set(issues))),
        "details": {
            "no_cost": no_cost,
            "privacy": privacy,
        },
    }
