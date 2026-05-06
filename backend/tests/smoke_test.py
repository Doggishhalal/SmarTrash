#!/usr/bin/env python3
"""Minimaler Smoke-Test für Backend-Kernmodule."""

import os
import sys
from pathlib import Path


def main():
    backend_dir = Path(__file__).resolve().parent.parent
    os.chdir(backend_dir)
    sys.path.insert(0, str(backend_dir))

    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ.setdefault("YOLOX_DEVICE", "cpu")

    print("[SMOKE] Prüfe Kern-Imports...")
    from inference import detect_image  # noqa: F401
    from learning_db import get_db
    from quality_controller import get_quality_controller
    from safety_config import get_config
    from waste_classifier import get_classifier
    from web_knowledge import get_fetcher

    print("[SMOKE] Initialisiere Singletons...")
    _ = get_config()
    _ = get_db()
    _ = get_quality_controller()
    _ = get_classifier()
    _ = get_fetcher()

    print("[SMOKE] OK")


if __name__ == "__main__":
    main()
