#!/usr/bin/env python3
"""SmarTrash REST API Contract Test (aktuelle Endpunkte)."""

import sys
from typing import List, Tuple

import requests

BASE_URL = "http://localhost:8000"


def _check_get(endpoint: str, expected_status: int = 200) -> Tuple[bool, str]:
    url = f"{BASE_URL}{endpoint}"
    try:
        resp = requests.get(url, timeout=4)
        ok = resp.status_code == expected_status
        msg = f"GET {endpoint:<34} -> {resp.status_code}"
        return ok, msg
    except Exception as exc:
        return False, f"GET {endpoint:<34} -> ERROR {exc}"


def _check_post(endpoint: str, expected_status: int = 200) -> Tuple[bool, str]:
    url = f"{BASE_URL}{endpoint}"
    try:
        resp = requests.post(url, json={}, timeout=4)
        ok = resp.status_code == expected_status
        msg = f"POST {endpoint:<33} -> {resp.status_code}"
        return ok, msg
    except Exception as exc:
        return False, f"POST {endpoint:<33} -> ERROR {exc}"


def run() -> int:
    checks: List[Tuple[bool, str]] = []

    # Core
    checks.append(_check_get("/"))
    checks.append(_check_get("/health"))
    checks.append(_check_get("/docs"))

    # Learning
    checks.append(_check_get("/learning/stats"))
    checks.append(_check_get("/learning/priorities"))
    checks.append(_check_get("/learning/review-queue"))
    checks.append(_check_get("/learning/recommendations"))
    checks.append(_check_get("/learning/threshold/book"))
    checks.append(_check_get("/learning/risky-classes"))

    # Quality/Safety/Compliance
    checks.append(_check_get("/quality/control"))
    checks.append(_check_get("/quality/error-trend"))
    checks.append(_check_get("/config/safety"))
    checks.append(_check_get("/compliance/no-cost"))
    checks.append(_check_get("/compliance/report"))
    checks.append(_check_post("/compliance/cleanup-data"))

    # Audit and info endpoints
    checks.append(_check_get("/audit/recent"))
    checks.append(_check_get("/system/audit"))
    checks.append(_check_get("/waste/bins"))
    checks.append(_check_get("/learning/dashboard"))

    print("\n" + "=" * 72)
    print("SmarTrash API Contract Test")
    print("=" * 72)
    for ok, message in checks:
        print(f"{'OK ' if ok else 'ERR'} {message}")

    failed = [c for c in checks if not c[0]]
    print("-" * 72)
    print(f"Checks: {len(checks)} | Failed: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
