"""
Framing Optimizer - Verbesserte Bounding Box Qualität
======================================================
Optimiert Box-Qualität durch:
- Adaptive NMS pro Klasse basierend auf Feedback
- Box-Regression Refinement
- Multi-Scale Alignment
- Confidence Fusion von mehreren Quellen
"""
from typing import Dict, List, Optional, Tuple

import numpy as np


class FramingOptimizer:
    """Optimiert Detection-Fraiming für bessere Bounding Boxes"""

    # Adaptive NMS Thresholds pro Kategorie
    ADAPTIVE_NMS_THRESHOLDS = {
        "Electronics": 0.50,     # Elektronik: höhere Schwelle (viele kleine Teile)
        "Battery": 0.45,         # Batteries: strict
        "Plastic_Bottle": 0.55,  # Flaschen: mittelhoch (oft geclustert)
        "Paper": 0.60,           # Papier: höher (deformierbar)
        "Organic": 0.65,         # Bio: höher (Form variabel)
        "Default": 0.45,         # Standard
    }

    # Box Padding pro Kategorie (um Edges zu erfassen)
    BOX_PADDING_PIXELS = {
        "Electronics": 8,        # Elektronik braucht etwas mehr
        "Small_Objects": 3,      # Kleine Objekte: minimal
        "Default": 5,
    }

    # Minimale Box-Area pro Kategorie (in Pixel²)
    MIN_BOX_AREA = {
        "Electronics": 1024,     # ~32x32 mindestens
        "Default": 512,          # ~23x23 mindestens
    }

    def __init__(self):
        pass

    def fuse_multiframe_detections(
        self,
        detection_clusters: List[List[Dict]],
        iou_threshold: float = 0.4,
        confidence_weight: float = 0.7
    ) -> List[Dict]:
        """
        Fusioniert Detections aus mehreren Frames/Augmentationen
        mit besserer Box-Qualität durch Alignment.

        detections: [{class, score, bbox=[x1,y1,x2,y2], ...}, ...]
        """
        if not detection_clusters or all(not c for c in detection_clusters):
            return []

        # Flatten + gruppiere nach Klasse
        all_dets = []
        frame_ids = []
        for frame_idx, dets in enumerate(detection_clusters):
            for det in dets:
                det_copy = dict(det)
                det_copy["_frame_id"] = frame_idx
                all_dets.append(det_copy)
                frame_ids.append(frame_idx)

        if not all_dets:
            return []

        # Gruppiere nach Klasse + räumlich nah
        by_class = {}
        for det in all_dets:
            cls = det.get("class", "unknown")
            if cls not in by_class:
                by_class[cls] = []
            by_class[cls].append(det)

        # Fusioniere pro Klasse
        fused = []
        for cls, dets in by_class.items():
            # Sortiere nach Score (absteigend)
            dets_sorted = sorted(dets, key=lambda x: x.get("score", 0), reverse=True)

            used = set()
            for i, det in enumerate(dets_sorted):
                if i in used:
                    continue

                # Finde alle Detections, die mit diesem überlappen
                cluster = [det]
                used.add(i)
                for j in range(i + 1, len(dets_sorted)):
                    if j in used:
                        continue
                    if self.iou(det["bbox"], dets_sorted[j]["bbox"]) > iou_threshold:
                        cluster.append(dets_sorted[j])
                        used.add(j)

                # Fusioniere Cluster
                fused_det = self._fuse_bbox_cluster(
                    cluster,
                    class_name=cls,
                    confidence_weight=confidence_weight
                )
                fused.append(fused_det)

        return fused

    def _fuse_bbox_cluster(
        self,
        cluster: List[Dict],
        class_name: str = "",
        confidence_weight: float = 0.7
    ) -> Dict:
        """Fusioniert einen Cluster von überlappenden Boxes mit Gewichtung"""

        # Gewichte nach Confidence
        scores = [max(float(d.get("score", 0.5)), 1e-6) for d in cluster]
        score_sum = sum(scores)
        weights = [s / score_sum for s in scores]

        # Weighted Box Fusion (WBF) - bessere Box-Qualität
        boxes = [d["bbox"] for d in cluster]
        x1 = sum(b[0] * w for b, w in zip(boxes, weights))
        y1 = sum(b[1] * w for b, w in zip(boxes, weights))
        x2 = sum(b[2] * w for b, w in zip(boxes, weights))
        y2 = sum(b[3] * w for b, w in zip(boxes, weights))

        # Box-Refinement (Small Object Enhancement)
        w = x2 - x1
        h = y2 - y1
        area = w * h

        # Adaptive padding
        padding = self.BOX_PADDING_PIXELS.get(self._categorize_object(class_name, area), 5)
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = x2 + padding  # Assume image bounds checked later
        y2 = y2 + padding

        # Confidence: Gewichtete Fusion + Support-Bonus
        max_conf = max(scores)
        support_bonus = 0.03 * min(len(cluster) - 1, 3)  # +3% pro zusätzlicher Detection, max
        fused_conf = min(1.0, max_conf + support_bonus)

        # Apply confidence weight factor
        fused_conf = fused_conf * confidence_weight + max(scores) * (1 - confidence_weight)

        return {
            "class": class_name,
            "score": float(fused_conf),
            "bbox": [float(x1), float(y1), float(x2), float(y2)],
            "cluster_size": len(cluster),
            "framing_quality": self._assess_framing_quality(cluster, len(cluster)),
        }

    def refine_small_objects(
        self,
        detections: List[Dict],
        image_width: int,
        image_height: int
    ) -> List[Dict]:
        """Verbessert Framing von kleinen Objekten"""

        refined = []
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            w = x2 - x1
            h = y2 - y1
            area = w * h
            total_area = image_width * image_height
            area_ratio = area / total_area

            # Bei kleinen Objekten: aggressivere Größe-Anpassung
            if area_ratio < 0.01:  # < 1% der Bildfläche
                # Vergrößere Box leicht für bessere Context
                expansion = 1.1
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                new_w = w * expansion
                new_h = h * expansion
                x1 = max(0, cx - new_w / 2)
                y1 = max(0, cy - new_h / 2)
                x2 = min(image_width, cx + new_w / 2)
                y2 = min(image_height, cy + new_h / 2)

                det["bbox"] = [x1, y1, x2, y2]
                det["framing_note"] = "small_object_expansion"

            refined.append(det)

        return refined

    def filter_by_box_quality(
        self,
        detections: List[Dict],
        min_area: int = 512,
        max_aspect_ratio: float = 8.5,
        quality_threshold: float = 0.65
    ) -> Tuple[List[Dict], List[str]]:
        """
        Filtert Detections basierend auf Box-Qualität.
        Gibt zurück: (quality_detections, filtered_reasons)
        """
        quality = []
        rejected_reasons = []

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            w = x2 - x1
            h = y2 - y1
            area = w * h
            aspect = max(w, h) / (min(w, h) + 1e-6)

            # Prüfe Mindestwerte
            if area < min_area:
                rejected_reasons.append(f"area_too_small: {area} < {min_area}")
                continue

            if aspect > max_aspect_ratio:
                rejected_reasons.append(f"aspect_ratio_extreme: {aspect} > {max_aspect_ratio}")
                continue

            # Prüfe Qualitäts-Score
            framing_q = det.get("framing_quality", 0.7)
            if framing_q < quality_threshold:
                rejected_reasons.append(f"framing_quality: {framing_q} < {quality_threshold}")
                continue

            quality.append(det)

        return quality, rejected_reasons

    def _categorize_object(self, class_name: str, area: float) -> str:
        """Kategorisiert ein Objekt für adaptive Parameter"""
        class_lower = str(class_name).lower()

        if any(kw in class_lower for kw in ["battery", "phone", "electronic", "chip", "wire"]):
            return "Electronics"

        if any(kw in class_lower for kw in ["battery", "akku", "lithium"]):
            return "Battery"

        if any(kw in class_lower for kw in ["bottle", "can", "cup"]):
            return "Plastic_Bottle"

        if any(kw in class_lower for kw in ["paper", "cardboard", "newspaper"]):
            return "Paper"

        if any(kw in class_lower for kw in ["food", "apple", "banana", "organic"]):
            return "Organic"

        if area < 3000:
            return "Small_Objects"

        return "Default"

    def _assess_framing_quality(self, cluster: List[Dict], cluster_size: int) -> float:
        """
        Bewertet Framing-Qualität eines Detections basierend auf:
        - Cluster-Konsistenz
        - Confidence-Spanne
        - Multi-Frame Support
        """
        if not cluster:
            return 0.5

        scores = [d.get("score", 0.5) for d in cluster]

        # Base quality: max confidence
        base = max(scores) * 0.5

        # Bonus für mehrere Quellen (Multi-Frame)
        multi_frame_bonus = 0.2 * min(cluster_size, 3) / 3

        # Penalty für zu unterschiedliche Scores
        score_std = np.std(scores) if len(scores) > 1 else 0
        consistency_bonus = 0.3 * max(0, 1 - score_std)

        total = base + multi_frame_bonus + consistency_bonus
        return min(1.0, total)

    @staticmethod
    def iou(box1: List[float], box2: List[float]) -> float:
        """Intersection over Union"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0

    def optimize_detection_output(
        self,
        detections: List[Dict],
        image_width: int,
        image_height: int
    ) -> Dict:
        """
        Gesamt-Optimierungs-Pipeline für beste Framing-Qualität:
        1. Kleine Objekte verbessern
        2. Nach Qualität filtern
        3. Adaptives NMS
        """

        # Step 1: Kleine Objekte verbessern
        refined = self.refine_small_objects(detections, image_width, image_height)

        # Step 2: Nach Qualität filtern
        quality, rejected = self.filter_by_box_quality(refined)

        # Step 3: Adaptive NMS
        by_class = {}
        for det in quality:
            cls = det.get("class", "unknown")
            if cls not in by_class:
                by_class[cls] = []
            by_class[cls].append(det)

        final = []
        for cls, dets in by_class.items():
            threshold = self.ADAPTIVE_NMS_THRESHOLDS.get(self._categorize_object(cls, 0), 0.45)
            nms_dets = self._apply_adaptive_nms(dets, threshold)
            final.extend(nms_dets)

        return {
            "optimized_detections": final,
            "rejected_count": len(rejected),
            "rejection_reasons": rejected[:5],  # Top 5 reasons
            "total_quality": len(final) / max(len(detections), 1),
        }

    def _apply_adaptive_nms(self, detections: List[Dict], threshold: float) -> List[Dict]:
        """Adaptive NMS pro Klasse"""
        if not detections:
            return []

        # Sortiere nach Score
        sorted_dets = sorted(detections, key=lambda x: x.get("score", 0), reverse=True)

        keep = []
        used = set()

        for i, det in enumerate(sorted_dets):
            if i in used:
                continue

            keep.append(det)
            used.add(i)

            # Unterdrücke überlappende Detections
            for j in range(i + 1, len(sorted_dets)):
                if j in used:
                    continue

                if self.iou(det["bbox"], sorted_dets[j]["bbox"]) > threshold:
                    used.add(j)

        return keep


# Singleton
_optimizer_instance = None

def get_framing_optimizer() -> FramingOptimizer:
    """Singleton für Framing-Optimierung"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = FramingOptimizer()
    return _optimizer_instance
    return _optimizer_instance
