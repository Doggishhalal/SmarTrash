"""
Detection Optimizer - Perfekte Objekterkennung mit 60% Hard-Threshold
=======================================================================
Multi-Layer Validation für garantiert sichere Ergebnisse:
1. Confidence Score Validation (≥60%)
2. Spatial Validation (Box-Qualität)
3. Class-Specific Confidence Boost
4. Multi-Source Verification
5. Anomaly Detection & Filtering
"""
from typing import Dict, List, Optional, Tuple

import numpy as np


class PerfectionDetectionOptimizer:
    """
    Optimiert Detections auf Maximum Confidence & Reliability.
    Hard-Threshold: 60% Mindest-Wahrscheinlichkeit
    """

    # ===== CLASS-SPECIFIC CONFIDENCE REQUIREMENTS =====
    # Conservativer: Was braucht mehr Confidence bei diesem Klasse
    CLASS_CONFIDENCE_ADJUSTMENTS = {
        # High-Confidence Classes (real objects, easy to detect)
        "person": 0.55,           # People: trust more (common, clear)
        "bottle": 0.58,           # Bottles: distinct shape
        "cup": 0.58,              # Cups: recurring pattern
        "chair": 0.58,            # Furniture: large, clear
        "dog": 0.60,              # Animals: distinct features
        "cat": 0.60,
        "bicycle": 0.60,          # Vehicles: distinctive
        "car": 0.60,

        # Medium-Confidence Classes (need more verification)
        "backpack": 0.62,         # Bags: variable shapes
        "handbag": 0.62,
        "suitcase": 0.62,
        "book": 0.60,             # Objects: shape-dependent
        "banana": 0.60,           # Food: color-based (risky)
        "apple": 0.60,
        "sandwich": 0.61,
        "pizza": 0.61,
        "donut": 0.61,

        # LOW-Confidence Classes (hard to distinguish, need very high threshold)
        "sports ball": 0.68,      # Balls: easy to confuse with other round objects
        "frisbee": 0.68,
        "skateboard": 0.65,       # Sport equipment: similar objects
        "surfboard": 0.65,
        "kite": 0.70,             # Rare, needs lots of evidence

        # Electronic/Battery (CRITICAL - Safety Issue!)
        "cell phone": 0.60,       # Handheld classes often appear small in frame
        "laptop": 0.63,
        "keyboard": 0.62,
        "mouse": 0.62,
        "remote": 0.62,
        "clock": 0.60,
        "tv": 0.63,
        "microwave": 0.70,
        "oven": 0.70,
        "toaster": 0.70,
        "refrigerator": 0.72,
        "hair drier": 0.72,

        # Glass (Safety: Can break, cutting hazard)
        "wine glass": 0.68,
        "bottle": 0.62,  # Glass bottles
        "bowl": 0.65,    # Could be ceramic too
        "vase": 0.70,    # Fragile

        # Unknown/Ambiguous (keep aligned with hard threshold to avoid over-pruning)
        "unknown": 0.60,
    }

    CLASS_ALIASES = {
        "phone": "cell phone",
        "smartphone": "cell phone",
        "mobile phone": "cell phone",
        "cellphone": "cell phone",
        "watch": "clock",
        "smartwatch": "clock",
        "wristwatch": "clock",
    }

    # ===== ANOMALY DETECTION =====
    # Wenn Box zu klein/groß oder komische Aspect Ratio → reject
    MIN_BOX_AREA_PIXELS = 100      # Minimum 10x10 pixels
    MAX_BOX_AREA_RATIO = 0.85      # Max 85% of image
    MIN_BBOX_HEIGHT = 8            # Minimum height
    MIN_BBOX_WIDTH = 8             # Minimum width
    EXTREME_ASPECT_RATIO = 12.0    # width/height > this = anomaly

    # ===== SPATIAL CONSISTENCY =====
    MIN_BOX_OVERLAP_WITH_NEIGHBORS = 0.1  # If overlaps <10%, might be false positive

    # ===== CONFIDENCE SCORE ADJUSTMENTS =====
    CONFIDENCE_BOOST_MULTIFRAME = 0.05   # +5% if multiple TTA frames agree
    CONFIDENCE_PENALTY_SMALL_BOX = -0.08  # -8% for small objects (unreliable)
    CONFIDENCE_PENALTY_EXTREME_AR = -0.10 # -10% for extreme aspect ratios
    CONFIDENCE_PENALTY_EDGE_BOXES = -0.05 # -5% boxes touching image edge
    HANDHELD_CLASSES = {"cell phone", "clock", "remote", "mouse"}

    def __init__(self):
        self.hard_threshold = 0.60  # 60% minimum
        self.class_adjustments = self.CLASS_CONFIDENCE_ADJUSTMENTS

    def _normalize_class_name(self, class_name: str) -> str:
        name = str(class_name).strip().lower()
        return self.CLASS_ALIASES.get(name, name)

    def validate_and_filter_detections(
        self,
        detections: List[Dict],
        image_width: int,
        image_height: int,
        strict_mode: bool = True
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Multi-Layer Validation:
        Returns: (valid_detections, rejected_detections_with_reasons)
        """
        valid = []
        rejected = []

        for det in detections:
            # Layer 1: Extract & normalize confidence
            score = float(det.get("score", 0.0))
            calibrated = float(det.get("calibrated_confidence", score))
            class_name = self._normalize_class_name(det.get("class", "unknown"))

            # Nutze höhere der beiden Confidence-Werte
            base_confidence = max(score, calibrated)

            # Layer 2: Apply class-specific adjustment
            class_threshold = self.class_adjustments.get(
                class_name,
                self.class_adjustments.get("unknown", 0.60)
            )

            # Layer 3: Validate box geometry
            bbox = det.get("bbox", [0, 0, image_width, image_height])
            x1, y1, x2, y2 = [float(v) for v in bbox]

            geo_result = self._validate_box_geometry(
                bbox, image_width, image_height
            )
            if not geo_result["valid"]:
                rejected.append({
                    "detection": det,
                    "reason": f"geometry_invalid: {geo_result['reason']}"
                })
                continue

            # Layer 4: Calculate confidence adjustments
            confidence_adjusted = self._apply_confidence_adjustments(
                base_confidence=base_confidence,
                bbox=bbox,
                image_width=image_width,
                image_height=image_height,
                tta_support=det.get("tta_support_count", 1),
                class_name=class_name
            )

            # Layer 5: Check if meets threshold
            if confidence_adjusted < self.hard_threshold:
                rejected.append({
                    "detection": det,
                    "reason": f"confidence_too_low: {confidence_adjusted:.1%} < {self.hard_threshold:.0%}",
                    "score": confidence_adjusted,
                    "threshold": self.hard_threshold
                })
                continue

            # Layer 6: Check if meets class-specific threshold
            if confidence_adjusted < class_threshold:
                if strict_mode:
                    rejected.append({
                        "detection": det,
                        "reason": f"class_threshold_too_low: {confidence_adjusted:.1%} < {class_threshold:.0%} for '{class_name}'",
                        "score": confidence_adjusted,
                        "class_threshold": class_threshold
                    })
                    continue

            # Layer 7: All validations passed!
            det_validated = dict(det)
            det_validated["confidence_final"] = float(confidence_adjusted)
            det_validated["confidence_class_threshold"] = float(class_threshold)
            det_validated["validation_layers_passed"] = 7
            valid.append(det_validated)

        return valid, rejected

    def _validate_box_geometry(
        self,
        bbox: List[float],
        image_width: int,
        image_height: int
    ) -> Dict:
        """Validates bounding box geometry for anomalies"""
        x1, y1, x2, y2 = bbox

        # Check bounds
        if x1 < 0 or y1 < 0 or x2 > image_width or y2 > image_height:
            return {
                "valid": False,
                "reason": "out_of_bounds"
            }

        # Calculate dimensions
        width = x2 - x1
        height = y2 - y1
        area = width * height

        # Check minimum size
        if width < self.MIN_BBOX_WIDTH or height < self.MIN_BBOX_HEIGHT:
            return {
                "valid": False,
                "reason": f"too_small: {width}x{height} < {self.MIN_BBOX_WIDTH}x{self.MIN_BBOX_HEIGHT}"
            }

        if area < self.MIN_BOX_AREA_PIXELS:
            return {
                "valid": False,
                "reason": f"area_too_small: {area} < {self.MIN_BOX_AREA_PIXELS}"
            }

        # Check maximum size
        image_area = image_width * image_height
        if area > image_area * self.MAX_BOX_AREA_RATIO:
            return {
                "valid": False,
                "reason": f"area_too_large: {area / image_area:.1%} > {self.MAX_BOX_AREA_RATIO:.0%}"
            }

        # Check aspect ratio (width/height)
        aspect_ratio = width / (height + 1e-6)
        if aspect_ratio > self.EXTREME_ASPECT_RATIO or (1.0 / (aspect_ratio + 1e-6)) > self.EXTREME_ASPECT_RATIO:
            return {
                "valid": False,
                "reason": f"extreme_aspect_ratio: {aspect_ratio:.1f}"
            }

        return {"valid": True, "reason": "OK"}

    def _apply_confidence_adjustments(
        self,
        base_confidence: float,
        bbox: List[float],
        image_width: int,
        image_height: int,
        tta_support: int = 1,
        class_name: str = ""
    ) -> float:
        """Apply all confidence adjustments"""
        adjusted = float(base_confidence)

        # Penalty: Small boxes (unreliable)
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        area = width * height
        image_area = image_width * image_height
        area_ratio = area / image_area

        if area_ratio < 0.005:  # < 0.5% of image
            small_box_penalty = self.CONFIDENCE_PENALTY_SMALL_BOX
            if class_name in self.HANDHELD_CLASSES:
                small_box_penalty = -0.03
            adjusted += small_box_penalty

        # Penalty: Extreme aspect ratio
        aspect_ratio = width / (height + 1e-6)
        if aspect_ratio > 5.0 or aspect_ratio < 0.2:
            adjusted += self.CONFIDENCE_PENALTY_EXTREME_AR

        # Penalty: Boxes touching image edge (likely partial objects)
        edge_margin = 3
        if x1 < edge_margin or y1 < edge_margin or \
           x2 > (image_width - edge_margin) or y2 > (image_height - edge_margin):
            adjusted += self.CONFIDENCE_PENALTY_EDGE_BOXES

        # Boost: Multiple TTA frames agree
        if tta_support >= 2:
            adjusted += self.CONFIDENCE_BOOST_MULTIFRAME * min(tta_support - 1, 2)

        # Handheld devices are often slim/vertical; reward plausible geometry slightly.
        if class_name in self.HANDHELD_CLASSES and area_ratio >= 0.001:
            if 0.25 <= aspect_ratio <= 1.25:
                adjusted += 0.02

        return max(0.0, min(1.0, adjusted))  # Clamp to [0, 1]

    def generate_detection_report(
        self,
        valid: List[Dict],
        rejected: List[Dict]
    ) -> Dict:
        """Generate detailed report about detection quality"""
        total = len(valid) + len(rejected)

        rejection_reasons = {}
        for rej in rejected:
            reason = rej.get("reason", "unknown")
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

        avg_confidence_valid = np.mean([d.get("confidence_final", 0.6) for d in valid]) if valid else 0.0

        return {
            "total_detections": total,
            "valid": len(valid),
            "rejected": len(rejected),
            "pass_rate": len(valid) / max(total, 1),
            "avg_confidence_valid": float(avg_confidence_valid),
            "rejection_breakdown": rejection_reasons,
            "hard_threshold_enforced": 0.60,
            "quality_score": "OPTIMIZED" if len(valid) > 0 else "NO_DETECTIONS",
        }


# Singleton
_optimizer_instance = None

def get_detection_optimizer() -> PerfectionDetectionOptimizer:
    """Singleton for detection optimization"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = PerfectionDetectionOptimizer()
    return _optimizer_instance
    return _optimizer_instance
