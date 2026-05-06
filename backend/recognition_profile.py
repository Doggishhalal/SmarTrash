import json
from pathlib import Path
from typing import Any, Dict

PROFILE_PATH = Path(__file__).with_name("recognition_profile.json")
DEFAULT_PROFILE: Dict[str, Any] = {
    "profile_name": "best_quality_yolox_l",
    "model_family": "YOLOX",
    "model_variant": "yolox_l",
    "enabled_features": {
        "tta": True,
        "multiscale": True,
        "flip_augmentation": True,
        "rescue_pass": True,
        "output_framing": True,
        "knowledge_enrichment": True,
        "learning_focus": True,
        "auto_retrain": True,
        "battery_safety": True,
    },
    "multiscale_scales": [0.75, 1.0, 1.25, 1.5],
    "public_data_sources": [
        "COCO",
        "TACO",
        "Open Images",
        "Roboflow Waste",
        "Wikidata",
        "OpenFoodFacts",
        "OpenStreetMap Tags",
        "Wikimedia Commons",
    ],
    "quality_targets": {
        "min_detection_confidence": 0.60,
        "min_framing_quality": 0.62,
        "min_tta_support_ratio_handheld": 0.18,
        "min_tta_support_ratio_default": 0.34,
    },
}


def load_recognition_profile(path: Path | None = None) -> Dict[str, Any]:
    profile_path = path or PROFILE_PATH
    if not profile_path.exists():
        return dict(DEFAULT_PROFILE)

    try:
        with profile_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
            if isinstance(payload, dict):
                merged = dict(DEFAULT_PROFILE)
                merged.update(payload)
                if isinstance(payload.get("enabled_features"), dict):
                    merged["enabled_features"] = {
                        **DEFAULT_PROFILE.get("enabled_features", {}),
                        **payload["enabled_features"],
                    }
                if isinstance(payload.get("quality_targets"), dict):
                    merged["quality_targets"] = {
                        **DEFAULT_PROFILE.get("quality_targets", {}),
                        **payload["quality_targets"],
                    }
                return merged
    except Exception:
        pass

    return dict(DEFAULT_PROFILE)
