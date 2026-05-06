#!/usr/bin/env python3
"""Lightweight project audit for maintainability and dead-code hints.

This script is intentionally conservative: it reports *potential* issues
without deleting anything.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_FILES = {
    "main.py",
    "app.py",
    "inference.py",
    "waste_classifier.py",
    "learning_db.py",
    "web_knowledge.py",
    "quality_controller.py",
    "safety_config.py",
    "sample_memory.py",
    "detail_analyzer.py",
    "compliance_guard.py",
    "performance_tracker.py",
}

SKIP_DIRS = {"venv", ".venv", "YOLOX-main", "__pycache__"}


def _iter_py_files() -> List[Path]:
    files: List[Path] = []
    for p in ROOT.rglob("*.py"):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        files.append(p)
    return sorted(files)


def _collect_defs_and_names(py_file: Path) -> Dict[str, Set[str]]:
    src = py_file.read_text(encoding="utf-8")
    tree = ast.parse(src)

    defs: Set[str] = set()
    names: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defs.add(node.name)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return {"defs": defs, "names": names}


def main() -> int:
    files = _iter_py_files()

    all_defs: Dict[str, Set[str]] = {}
    all_names: Set[str] = set()

    for f in files:
        collected = _collect_defs_and_names(f)
        all_defs[str(f.relative_to(ROOT))] = collected["defs"]
        all_names.update(collected["names"])

    potentially_unused = []
    for rel, defs in all_defs.items():
        for d in sorted(defs):
            if d.startswith("_"):
                continue
            if d not in all_names:
                potentially_unused.append((rel, d))

    runtime_missing = sorted([f for f in RUNTIME_FILES if not (ROOT / f).exists()])

    print("=" * 72)
    print("SmarTrash Project Audit")
    print("=" * 72)
    print(f"Python files scanned: {len(files)}")
    print()

    print("Runtime files present:")
    for name in sorted(RUNTIME_FILES):
        status = "OK" if (ROOT / name).exists() else "MISSING"
        print(f"  - {name:24} {status}")
    if runtime_missing:
        print("\nMissing runtime files:")
        for m in runtime_missing:
            print(f"  - {m}")

    print("\nPotentially unused public symbols (manual review required):")
    if not potentially_unused:
        print("  - none")
    else:
        for rel, symbol in potentially_unused[:120]:
            print(f"  - {rel}: {symbol}")

    print("\nNote: This report is heuristic and should be validated manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
