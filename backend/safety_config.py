"""
Safety & Quality Configuration for SmarTrash
===========================================
Zentrale Konfiguration für sichere Mülltrennung.
"""
import os


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class SafetyConfig:
    def __init__(self):
        self.hard_safety_mode = _env_bool("SMARTRASH_HARD_SAFETY", True)
        self.ultra_strict_mode = _env_bool("SMARTRASH_ULTRA_STRICT", True)
        self.min_decision_quality_for_autosort = _env_float("SMARTRASH_MIN_QUALITY", 0.72)
        self.min_confidence_for_autosort = _env_float("SMARTRASH_MIN_CONFIDENCE", 0.55)
        self.enable_web_knowledge = _env_bool("SMARTRASH_ENABLE_WEB", True)
        self.strict_battery_policy = _env_bool("SMARTRASH_STRICT_BATTERY", True)
        self.enable_audit_logging = _env_bool("SMARTRASH_AUDIT_LOG", True)
        self.web_fetch_min_confidence = _env_float("SMARTRASH_WEB_MIN_CONF", 0.35)
        self.max_web_fetch_classes_per_image = int(_env_float("SMARTRASH_WEB_MAX_CLASSES", 8))
        self.no_cost_mode = _env_bool("SMARTRASH_NO_COST_MODE", True)
        self.allow_paid_integrations = _env_bool("SMARTRASH_ALLOW_PAID", False)
        self.store_images_with_person = _env_bool("SMARTRASH_STORE_PERSON_IMAGES", False)
        self.data_retention_days = int(_env_float("SMARTRASH_RETENTION_DAYS", 30))

    def as_dict(self):
        return {
            "hard_safety_mode": self.hard_safety_mode,
            "ultra_strict_mode": self.ultra_strict_mode,
            "min_decision_quality_for_autosort": self.min_decision_quality_for_autosort,
            "min_confidence_for_autosort": self.min_confidence_for_autosort,
            "enable_web_knowledge": self.enable_web_knowledge,
            "strict_battery_policy": self.strict_battery_policy,
            "enable_audit_logging": self.enable_audit_logging,
            "web_fetch_min_confidence": self.web_fetch_min_confidence,
            "max_web_fetch_classes_per_image": self.max_web_fetch_classes_per_image,
            "no_cost_mode": self.no_cost_mode,
            "allow_paid_integrations": self.allow_paid_integrations,
            "store_images_with_person": self.store_images_with_person,
            "data_retention_days": self.data_retention_days,
        }


_config = None


def get_config() -> SafetyConfig:
    global _config
    if _config is None:
        _config = SafetyConfig()
    return _config
