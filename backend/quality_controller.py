"""
Quality Controller
==================
Automatisch strenger/lockerer je nach aktueller Fehlerquote,
um die Fehlerrate kontinuierlich zu senken.
"""
from learning_db import get_db
from safety_config import get_config


class QualityController:
    def __init__(self):
        self.db = get_db()
        self.cfg = get_config()

    def get_adaptive_policy(self):
        rates = self.db.get_recent_feedback_error_rates(window=80)

        base_quality = self.cfg.min_decision_quality_for_autosort
        base_conf = self.cfg.min_confidence_for_autosort

        # Standard policy
        policy = {
            "mode": "normal",
            "min_quality": base_quality,
            "min_confidence": base_conf,
            "force_manual_for_risky_classes": [],
            "reason": "baseline",
            "error_rates": rates,
        }

        samples = rates.get("samples", 0)
        recent_error = rates.get("recent_error_rate", 0.0)
        trend = rates.get("trend", "unknown")

        if samples < 20:
            policy["mode"] = "cold_start_safe"
            policy["min_quality"] = max(base_quality, 0.76)
            policy["min_confidence"] = max(base_conf, 0.62)
            policy["reason"] = "too_few_feedback_samples"
            return policy

        # Fehler steigt -> strenger
        if recent_error >= 0.28 or trend == "worsening":
            policy["mode"] = "strict_recovery"
            policy["min_quality"] = max(base_quality, 0.82)
            policy["min_confidence"] = max(base_conf, 0.68)
            policy["reason"] = "error_rate_high_or_worsening"
        elif recent_error <= 0.12 and trend == "improving":
            # Nur leicht lockern, nie unsicher
            policy["mode"] = "stable_high_quality"
            policy["min_quality"] = max(0.70, base_quality - 0.02)
            policy["min_confidence"] = max(0.52, base_conf - 0.02)
            policy["reason"] = "error_rate_low_and_improving"

        # Klassen mit hoher Verwechslungsrate immer manuell prüfen
        risky = []
        for item in self.db.get_priority_feedback_classes(limit=8):
            if item.get("accuracy_rate", 1.0) < 0.60 and item.get("total_samples", 0) >= 8:
                risky.append(item["class_name"])
        policy["force_manual_for_risky_classes"] = risky

        return policy


_controller = None


def get_quality_controller():
    global _controller
    if _controller is None:
        _controller = QualityController()
    return _controller
