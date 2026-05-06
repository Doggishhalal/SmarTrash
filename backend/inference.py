import hashlib
import json
import os
import sys
import time

import cv2
import numpy as np

# Make YOLOX package importable (YOLOX-main is sibling of this file)
ROOT = os.path.dirname(__file__)
YOLOX_ROOT = os.path.join(ROOT, "YOLOX-main")
if YOLOX_ROOT not in sys.path:
    sys.path.append(YOLOX_ROOT)

try:
    from tools.demo import Predictor
    from yolox.data.datasets import COCO_CLASSES
    from yolox.exp import get_exp
except Exception as e:
    raise RuntimeError(
        "Failed to import YOLOX modules. Ensure YOLOX-main is present and its requirements are installed. "
        f"Import error: {e}"
    )

import torch
from detail_analyzer import get_analyzer
from detection_optimizer import get_detection_optimizer
from learning_db import get_db
from quality_controller import get_quality_controller
from recognition_profile import load_recognition_profile
from safety_config import get_config
from waste_classifier import get_classifier
from web_knowledge import get_fetcher

# Konfigurations-Konstanten
MIN_CONFIDENCE = 0.20  # Breite Erkennung intern, finale Ausgabe wird separat gefiltert
NMS_THRESHOLD = 0.45   # Non-Maximum Suppression für bessere Überlappungs-Behandlung
PERSON_STRICT_THRESHOLD = 0.92  # Personen nur bei extrem hoher Sicherheit berücksichtigen
OUTPUT_MIN_CONFIDENCE = 0.60  # HARD THRESHOLD: Nur Ergebnisse >= 60% ausgeben (v2.2 Optimization)
MIN_TTA_SUPPORT_RATIO = 0.34  # Niedrige TTA-Unterstützung deutet auf instabile Erkennung hin
MIN_TTA_SUPPORT_RATIO_HANDHELD = 0.18  # Handheld objects are often tiny and unstable across TTA views
MIN_BBOX_AREA_RATIO = 0.00035  # Sehr kleine Boxen sind häufig Rauschen
MAX_BBOX_ASPECT_RATIO = 8.5  # Extrem lange Boxen sind oft Artefakte

MATERIAL_TO_HINT = {
    "paper": "paper_material",
    "plastic": "plastic_material",
    "organic": "organic_material",
    "glass": "glass_material",
    "electronic": "electronic_waste",
    "metal": "metal_material",
    "textile": "textile_material",
    "wood": "wood_material",
}

BASE_HIGH_RISK_CLASSES = {
    "cell phone", "laptop", "mouse", "remote", "keyboard", "clock", "tv", "hair drier",
    "battery", "charger", "power bank", "light bulb", "fluorescent lamp",
}

# Small handheld objects are frequently under-scored although visually correct.
HANDHELD_PRIORITY_CLASSES = {"cell phone", "clock", "watch", "smartwatch"}
FRAMING_PRIORITY_CLASSES = HANDHELD_PRIORITY_CLASSES | {"bottle", "cup", "can", "glass"}
MAX_FOCUS_REFINES_PER_IMAGE = 2  # Keep runtime stable
MAX_OUTPUT_FOCUS_REFINES_PER_IMAGE = 6  # Output-only refinement can safely run on more boxes
RESCUE_CONFIDENCE_FLOOR = 0.14
MIN_FRAMING_QUALITY_TARGET = 0.62
FRAMING_BORDER_BAND_RATIO = 0.10

CLASS_ALIASES = {
    "phone": "cell phone",
    "smartphone": "cell phone",
    "mobile phone": "cell phone",
    "cellphone": "cell phone",
    "watch": "clock",
    "smartwatch": "clock",
    "wristwatch": "clock",
}

RISKY_HINTS = {"contains_battery", "electronic_waste", "hazardous_hint"}


def _read_class_names_file(file_path: str):
    if not file_path or not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.lower().endswith(".json"):
                payload = json.load(f)
                if isinstance(payload, dict):
                    payload = payload.get("classes", [])
                if isinstance(payload, list):
                    return [str(item).strip() for item in payload if str(item).strip()]
                return []

            class_names = []
            for line in f:
                name = line.strip()
                if not name or name.startswith("#"):
                    continue
                class_names.append(name)
            return class_names
    except Exception:
        return []


def _load_class_names():
    env_file = os.environ.get("SMARTRASH_CLASS_NAMES_FILE") or os.environ.get("YOLOX_CLASS_NAMES_FILE")
    class_names = _read_class_names_file(env_file)
    if class_names:
        return class_names
    return list(COCO_CLASSES)


def _normalize_class_name(name: str) -> str:
    normalized = str(name).strip().lower()
    return CLASS_ALIASES.get(normalized, normalized)


class YOLOXRunner:
    def __init__(self, ckpt_path=None, exp_name="yolox_s", device="cpu", confidence_threshold=MIN_CONFIDENCE):
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.recognition_profile = load_recognition_profile()
        self.class_names = _load_class_names()
        self.exp = get_exp(exp_name=exp_name)

        # Optimale Test-Konfiguration für beste Ergebnisse
        self.exp.test_conf = confidence_threshold
        self.exp.nmsthre = NMS_THRESHOLD

        self.model = self.exp.get_model()
        self.model.eval()

        # Auto-detect model path if not provided
        if ckpt_path is None:
            ckpt_path = os.path.join(ROOT, "YOLOX_outputs/yolox_s/yolox_s.pth")

        if not os.path.exists(ckpt_path):
            raise RuntimeError(f"Checkpoint not found at: {ckpt_path}")

        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        if "model" in ckpt:
            self.model.load_state_dict(ckpt["model"])
        else:
            self.model.load_state_dict(ckpt)

        if device != "cpu" and torch.cuda.is_available():
            self.model.to(device)

        self.predictor = Predictor(
            self.model, self.exp, self.class_names,
            device=("gpu" if device != "cpu" and torch.cuda.is_available() else "cpu")
        )
        enabled_features = self.recognition_profile.get("enabled_features", {})
        self.use_tta = bool(enabled_features.get("tta", True))  # Test-Time Augmentation für bessere Genauigkeit
        self.use_multiscale = bool(enabled_features.get("multiscale", True))  # Multi-Scale Testing
        self.use_flip_augmentation = bool(enabled_features.get("flip_augmentation", True))
        self.use_rescue_pass = bool(enabled_features.get("rescue_pass", True))
        self.multiscale_scales = list(self.recognition_profile.get("multiscale_scales", [0.8, 1.0, 1.2, 1.4]))
        self.risky_class_cache_ttl_sec = 180.0
        self._cached_risky_classes = set()
        self._cached_risky_classes_at = 0.0

    @staticmethod
    def _clamp_bbox(bbox, img_w, img_h):
        x1, y1, x2, y2 = [float(v) for v in bbox]
        x1 = max(0.0, min(x1, float(img_w - 1)))
        y1 = max(0.0, min(y1, float(img_h - 1)))
        x2 = max(0.0, min(x2, float(img_w)))
        y2 = max(0.0, min(y2, float(img_h)))
        if x2 <= x1:
            x2 = min(float(img_w), x1 + 1.0)
        if y2 <= y1:
            y2 = min(float(img_h), y1 + 1.0)
        return [x1, y1, x2, y2]

    def _expand_bbox(self, bbox, img_w, img_h, expand_ratio: float):
        x1, y1, x2, y2 = [float(v) for v in bbox]
        w = max(1.0, x2 - x1)
        h = max(1.0, y2 - y1)
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        nw = w * (1.0 + float(expand_ratio))
        nh = h * (1.0 + float(expand_ratio))
        expanded = [
            cx - (nw / 2.0),
            cy - (nh / 2.0),
            cx + (nw / 2.0),
            cy + (nh / 2.0),
        ]
        return self._clamp_bbox(expanded, img_w, img_h)

    def _framing_fit_metrics(self, image: np.ndarray, bbox):
        """Estimate how well a bbox fits object edges for self-checking and auto-tuning."""
        img_h, img_w = image.shape[:2]
        x1, y1, x2, y2 = self._clamp_bbox(bbox, img_w, img_h)
        ix1, iy1, ix2, iy2 = [int(round(v)) for v in [x1, y1, x2, y2]]
        if ix2 - ix1 < 6 or iy2 - iy1 < 6:
            return {
                "quality": 0.25,
                "border_density": 1.0,
                "center_density": 0.0,
                "edge_density": 0.0,
                "need_expand": True,
            }

        roi = image[iy1:iy2, ix1:ix2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 45, 150)

        h, w = edges.shape[:2]
        band = max(1, int(round(min(h, w) * FRAMING_BORDER_BAND_RATIO)))

        border_mask = np.zeros_like(edges, dtype=np.uint8)
        border_mask[:band, :] = 1
        border_mask[-band:, :] = 1
        border_mask[:, :band] = 1
        border_mask[:, -band:] = 1
        center_mask = 1 - border_mask

        edge_binary = (edges > 0).astype(np.uint8)
        border_pixels = int(border_mask.sum())
        center_pixels = int(center_mask.sum())

        border_density = float((edge_binary * border_mask).sum()) / max(float(border_pixels), 1.0)
        center_density = float((edge_binary * center_mask).sum()) / max(float(center_pixels), 1.0)
        edge_density = float(edge_binary.mean())

        # High border density usually means cropped object; healthy box has more center than border support.
        crop_penalty = max(0.0, border_density - (center_density * 0.85))
        quality = 1.0 - min(0.95, crop_penalty * 2.6)
        quality = (quality * 0.75) + (min(1.0, edge_density / 0.22) * 0.25)
        quality = max(0.0, min(1.0, quality))

        need_expand = border_density > (center_density * 0.9 + 0.015)
        return {
            "quality": round(float(quality), 3),
            "border_density": round(float(border_density), 4),
            "center_density": round(float(center_density), 4),
            "edge_density": round(float(edge_density), 4),
            "need_expand": bool(need_expand),
        }

    def _refine_bbox_focus(self, image: np.ndarray, bbox, class_name: str, score: float, support_ratio: float):
        """Image-aware box refinement to improve framing position and size."""
        img_h, img_w = image.shape[:2]
        x1, y1, x2, y2 = self._clamp_bbox(bbox, img_w, img_h)

        w = x2 - x1
        h = y2 - y1
        if w < 2 or h < 2:
            return [x1, y1, x2, y2], {"applied": False, "reason": "degenerate_box"}

        class_name_lc = str(class_name or "").strip().lower()
        context_margin = 0.32 if class_name_lc in HANDHELD_PRIORITY_CLASSES else 0.18
        ex1 = int(max(0, np.floor(x1 - (w * context_margin))))
        ey1 = int(max(0, np.floor(y1 - (h * context_margin))))
        ex2 = int(min(img_w, np.ceil(x2 + (w * context_margin))))
        ey2 = int(min(img_h, np.ceil(y2 + (h * context_margin))))

        roi = image[ey1:ey2, ex1:ex2]
        if roi.size == 0:
            return [x1, y1, x2, y2], {"applied": False, "reason": "empty_roi"}

        # Guardrail: skip expensive contour scan on very large ROIs.
        if (roi.shape[0] * roi.shape[1]) > 180000:
            return [x1, y1, x2, y2], {"applied": False, "reason": "roi_too_large"}

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 40, 140)
        edges = cv2.dilate(edges, np.ones((3, 3), dtype=np.uint8), iterations=1)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return [x1, y1, x2, y2], {"applied": False, "reason": "no_contours"}

        base_center = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        roi_area = float(max(roi.shape[0] * roi.shape[1], 1))
        min_contour_area = max(18.0, roi_area * 0.002)
        selected_rects = []

        for contour in contours:
            rx, ry, rw, rh = cv2.boundingRect(contour)
            if rw < 4 or rh < 4:
                continue

            contour_area = float(rw * rh)
            if contour_area < min_contour_area:
                continue

            cx = ex1 + rx + (rw / 2.0)
            cy = ey1 + ry + (rh / 2.0)
            center_dist = np.hypot(cx - base_center[0], cy - base_center[1])
            center_gate = max(26.0, 0.52 * np.hypot(w, h))
            if center_dist > center_gate:
                continue

            selected_rects.append((rx, ry, rw, rh, contour_area))

        if not selected_rects:
            return [x1, y1, x2, y2], {"applied": False, "reason": "no_valid_rect"}

        selected_rects.sort(key=lambda item: item[4], reverse=True)
        selected_rects = selected_rects[:3]
        rx = min(item[0] for item in selected_rects)
        ry = min(item[1] for item in selected_rects)
        rmax_x = max(item[0] + item[2] for item in selected_rects)
        rmax_y = max(item[1] + item[3] for item in selected_rects)
        rw = max(1, rmax_x - rx)
        rh = max(1, rmax_y - ry)

        refined = [
            float(ex1 + rx),
            float(ey1 + ry),
            float(ex1 + rx + rw),
            float(ey1 + ry + rh),
        ]
        refined = self._clamp_bbox(refined, img_w, img_h)

        # Blend original and refined bbox to avoid unstable jumps.
        refine_strength = 0.45
        if class_name_lc in HANDHELD_PRIORITY_CLASSES:
            refine_strength = 0.60
        refine_strength += max(0.0, (0.6 - float(score))) * 0.30
        refine_strength += max(0.0, (0.5 - float(support_ratio))) * 0.25
        refine_strength = max(0.30, min(refine_strength, 0.88))

        blended = [
            (x1 * (1.0 - refine_strength)) + (refined[0] * refine_strength),
            (y1 * (1.0 - refine_strength)) + (refined[1] * refine_strength),
            (x2 * (1.0 - refine_strength)) + (refined[2] * refine_strength),
            (y2 * (1.0 - refine_strength)) + (refined[3] * refine_strength),
        ]
        blended = self._clamp_bbox(blended, img_w, img_h)

        fit_metrics = self._framing_fit_metrics(image, blended)
        if fit_metrics.get("need_expand"):
            expand_ratio = 0.12 if class_name_lc in HANDHELD_PRIORITY_CLASSES else 0.08
            blended = self._expand_bbox(blended, img_w, img_h, expand_ratio=expand_ratio)
            fit_metrics = self._framing_fit_metrics(image, blended)

        return blended, {
            "applied": True,
            "refine_strength": round(refine_strength, 3),
            "roi_shape": [int(roi.shape[1]), int(roi.shape[0])],
            "fit_metrics": fit_metrics,
        }

    def _apply_output_framing(self, image: np.ndarray, detections, max_refines: int = 6):
        """Refine final output boxes only; never feed refined boxes back into recognition gates."""
        if not detections:
            return [], {
                "output_mode": "output_only_refinement",
                "output_refined_count": 0,
                "output_skipped_count": 0,
                "focus_refined_count": 0,
                "focus_skipped_count": 0,
                "low_quality_boxes": 0,
                "avg_framing_quality": 0.0,
                "self_check_status": "no_detections",
            }

        refined_output = []
        refined_count = 0
        skipped_count = 0
        low_quality_count = 0
        quality_values = []
        auto_expanded_count = 0

        ordered = sorted(
            list(detections),
            key=lambda d: float(d.get("calibrated_confidence", d.get("score", 0.0))),
            reverse=True,
        )

        for det in ordered:
            out_det = dict(det)
            model_bbox = list(out_det.get("bbox", [0.0, 0.0, 1.0, 1.0]))
            out_det["bbox_model"] = list(model_bbox)
            model_fit = self._framing_fit_metrics(image, model_bbox)

            class_name_lc = str(out_det.get("class", "")).strip().lower()
            score = float(out_det.get("calibrated_confidence", out_det.get("score", 0.0)))
            support_ratio = float(out_det.get("tta_support_ratio", 1.0))

            should_refine = (
                refined_count < max_refines
                and ((class_name_lc in FRAMING_PRIORITY_CLASSES) or (score < 0.86) or (support_ratio < 0.80))
            )

            if should_refine:
                candidate_bbox, focus_meta = self._refine_bbox_focus(
                    image=image,
                    bbox=model_bbox,
                    class_name=out_det.get("class", ""),
                    score=score,
                    support_ratio=support_ratio,
                )
                if focus_meta.get("applied") and self._iou(model_bbox, candidate_bbox) >= 0.30:
                    cand_fit = self._framing_fit_metrics(image, candidate_bbox)
                    model_quality = float(model_fit.get("quality", 0.0))
                    cand_quality = float(cand_fit.get("quality", 0.0))

                    if cand_quality + 0.02 < model_quality:
                        out_det["bbox"] = model_bbox
                        out_det["framing_focus"] = {
                            "applied": False,
                            "reason": "candidate_worse_than_model",
                            "model_quality": model_quality,
                            "candidate_quality": cand_quality,
                        }
                        skipped_count += 1
                        selected_fit = model_fit
                    else:
                        selected_bbox = candidate_bbox
                        selected_fit = cand_fit
                        if selected_fit.get("need_expand"):
                            expand_ratio = 0.12 if class_name_lc in HANDHELD_PRIORITY_CLASSES else 0.07
                            expanded = self._expand_bbox(selected_bbox, image.shape[1], image.shape[0], expand_ratio)
                            expanded_fit = self._framing_fit_metrics(image, expanded)
                            if float(expanded_fit.get("quality", 0.0)) >= float(selected_fit.get("quality", 0.0)):
                                selected_bbox = expanded
                                selected_fit = expanded_fit
                                auto_expanded_count += 1

                        out_det["bbox"] = selected_bbox
                        out_det["framing_focus"] = {
                            **focus_meta,
                            "model_fit": model_fit,
                            "selected_fit": selected_fit,
                        }
                        refined_count += 1
                else:
                    out_det["bbox"] = model_bbox
                    out_det["framing_focus"] = {"applied": False, "reason": "low_overlap_safety"}
                    skipped_count += 1
                    selected_fit = model_fit
            else:
                out_det["bbox"] = model_bbox
                out_det["framing_focus"] = {"applied": False, "reason": "post_output_skip"}
                skipped_count += 1
                selected_fit = model_fit

            framing_quality = float(selected_fit.get("quality", 0.0))
            out_det["framing_quality"] = framing_quality
            out_det["framing_needs_improvement"] = framing_quality < MIN_FRAMING_QUALITY_TARGET
            if out_det["framing_needs_improvement"]:
                low_quality_count += 1
            quality_values.append(framing_quality)

            refined_output.append(out_det)

        avg_quality = float(sum(quality_values) / max(len(quality_values), 1))
        self_check_status = "ok"
        if avg_quality < MIN_FRAMING_QUALITY_TARGET or low_quality_count > max(1, len(refined_output) // 3):
            self_check_status = "needs_improvement"

        return refined_output, {
            "output_mode": "output_only_refinement",
            "output_refined_count": refined_count,
            "output_skipped_count": skipped_count,
            "focus_refined_count": refined_count,
            "focus_skipped_count": skipped_count,
            "output_auto_expanded_count": auto_expanded_count,
            "low_quality_boxes": low_quality_count,
            "avg_framing_quality": round(avg_quality, 3),
            "framing_quality_target": MIN_FRAMING_QUALITY_TARGET,
            "self_check_status": self_check_status,
        }

    def _get_learned_risky_classes(self, db):
        """Lädt riskante Klassen periodisch aus Feedback statt pro Bild."""
        now = time.time()
        if (now - float(self._cached_risky_classes_at)) <= self.risky_class_cache_ttl_sec:
            return self._cached_risky_classes

        try:
            risky_rows = db.get_risky_classes_from_feedback(min_wrong_rate=0.30, min_samples=6, limit=60)
            self._cached_risky_classes = {
                str(r.get("class_name", "")).strip().lower()
                for r in risky_rows
                if str(r.get("class_name", "")).strip()
            }
            self._cached_risky_classes_at = now
        except Exception:
            # Behalte letzten gültigen Cache bei
            pass

        return self._cached_risky_classes

    def _apply_tta(self, image: np.ndarray):
        """Test-Time Augmentation: mehrere Varianten testen, Ergebnisse kombinieren"""
        results_all = []
        source_count = 0

        # Multi-Scale Testing für verschiedene Objektgrößen
        if self.use_multiscale:
            scales = list(self.multiscale_scales or [0.8, 1.0, 1.2, 1.4])
            for scale in scales:
                if scale != 1.0:
                    h, w = image.shape[:2]
                    scaled = cv2.resize(image, (int(w * scale), int(h * scale)))
                    scaled_results = self._single_detect(scaled)
                    # Skaliere Bboxes zurück
                    for det in scaled_results:
                        det["bbox"] = [x / scale for x in det["bbox"]]
                        det["tta_source"] = f"scale_{scale}"
                    results_all.append(scaled_results)
                    source_count += 1
                else:
                    base_results = self._single_detect(image)
                    for det in base_results:
                        det["tta_source"] = "scale_1.0"
                    results_all.append(base_results)
                    source_count += 1
        else:
            # Original
            base_results = self._single_detect(image)
            for det in base_results:
                det["tta_source"] = "base"
            results_all.append(base_results)
            source_count += 1

        # Horizontal Flip für bessere Detection von gespiegelten Objekten
        if self.use_tta and self.use_flip_augmentation:
            flipped = cv2.flip(image, 1)
            flipped_results = self._single_detect(flipped)
            # Flip bboxes zurück
            for det in flipped_results:
                w = image.shape[1]
                x1, y1, x2, y2 = det["bbox"]
                det["bbox"] = [w - x2, y1, w - x1, y2]
                det["tta_source"] = "flip"
            results_all.append(flipped_results)
            source_count += 1

        # Kombiniere und entferne Duplikate (NMS über alle Augmentationen)
        combined = []
        for results in results_all:
            combined.extend(results)

        return self._merge_detections(combined, total_sources=max(source_count, 1))

    def _merge_detections(self, detections, total_sources=1):
        """Merge überlappende Detections derselben Klasse per Weighted Fusion."""
        if not detections:
            return []

        # Gruppiere nach Klasse
        by_class = {}
        for det in detections:
            cls = det["class"]
            if cls not in by_class:
                by_class[cls] = []
            by_class[cls].append(det)

        merged = []
        for cls, dets in by_class.items():
            # Sortiere nach Score
            dets = sorted(dets, key=lambda x: x["score"], reverse=True)

            used = set()
            for i, det in enumerate(dets):
                if i in used:
                    continue

                cluster = [det]
                used.add(i)
                for j in range(i + 1, len(dets)):
                    if j in used:
                        continue
                    if self._iou(det["bbox"], dets[j]["bbox"]) > NMS_THRESHOLD:
                        cluster.append(dets[j])
                        used.add(j)

                source_ids = {
                    str(c.get("tta_source", "base"))
                    for c in cluster
                }
                support_count = len(source_ids)
                support_ratio = support_count / max(float(total_sources), 1.0)

                if len(cluster) == 1:
                    single = dict(cluster[0])
                    single.pop("tta_source", None)
                    single["tta_support_count"] = support_count
                    single["tta_support_ratio"] = support_ratio
                    merged.append(single)
                    continue

                # Weighted box fusion by score
                weights = [max(float(c.get("score", 0.0)), 1e-6) for c in cluster]
                weight_sum = float(sum(weights))
                x1 = sum(c["bbox"][0] * w for c, w in zip(cluster, weights)) / weight_sum
                y1 = sum(c["bbox"][1] * w for c, w in zip(cluster, weights)) / weight_sum
                x2 = sum(c["bbox"][2] * w for c, w in zip(cluster, weights)) / weight_sum
                y2 = sum(c["bbox"][3] * w for c, w in zip(cluster, weights)) / weight_sum

                max_score = max(float(c.get("score", 0.0)) for c in cluster)
                fused_bonus = min(0.08, 0.02 * (len(cluster) - 1))
                fused_score = min(1.0, max_score + fused_bonus)

                merged.append({
                    "class": cls,
                    "score": fused_score,
                    "bbox": [x1, y1, x2, y2],
                    "tta_support_count": support_count,
                    "tta_support_ratio": support_ratio,
                })

        return merged

    def _iou(self, box1, box2):
        """Berechne Intersection over Union"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0

    def _single_detect(self, image: np.ndarray, confidence_threshold: float = None):
        """Einzelne Detection ohne Augmentation"""
        conf_threshold = self.confidence_threshold if confidence_threshold is None else float(confidence_threshold)
        outputs, _ = self.predictor.inference(image)
        if outputs is None or outputs[0] is None:
            return []

        out = outputs[0].cpu().numpy()
        results = []

        for det in out:
            score = float(det[4] * det[5])

            # Nur sichere Erkennungen
            if score < conf_threshold:
                continue

            x1, y1, x2, y2 = [float(v) for v in det[0:4]]
            cls_id = int(det[6])
            cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else str(cls_id)

            # People suppression for trash sorting UX: humans should almost never appear
            if str(cls_name).strip().lower() == "person" and score < PERSON_STRICT_THRESHOLD:
                continue

            results.append({"class": cls_name, "score": score, "bbox": [x1, y1, x2, y2]})

        return results

    def _apply_rescue_detection(self, image: np.ndarray):
        """Fallback pass for hard images where the base model returns no candidates."""
        h, w = image.shape[:2]
        if h <= 0 or w <= 0:
            return []

        # Build robust rescue views for low-contrast and blurry images.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        clahe_bgr = cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)

        sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        sharpened = cv2.filter2D(image, -1, sharpen_kernel)

        gamma = 1.25
        lut = np.array([(i / 255.0) ** (1.0 / gamma) * 255 for i in range(256)]).astype("uint8")
        gamma_corrected = cv2.LUT(image, lut)

        rescue_views = [
            ("clahe", clahe_bgr),
            ("sharpen", sharpened),
            ("gamma", gamma_corrected),
        ]

        rescue_threshold = max(RESCUE_CONFIDENCE_FLOOR, float(self.confidence_threshold) - 0.06)
        rescue_candidates = []
        for name, view in rescue_views:
            view_dets = self._single_detect(view, confidence_threshold=rescue_threshold)
            for det in view_dets:
                det["tta_source"] = f"rescue_{name}"
            rescue_candidates.extend(view_dets)

        if not rescue_candidates:
            return []

        return self._merge_detections(rescue_candidates, total_sources=max(len(rescue_views), 1))

    def detect(self, image: np.ndarray, image_hash: str = None, debug: bool = False):
        """Hauptmethode: Detection mit optionaler TTA für beste Ergebnisse"""
        rescue_used = False
        if self.use_tta:
            detections = self._apply_tta(image)
        else:
            detections = self._single_detect(image)

        if len(detections) == 0:
            rescue_detections = self._apply_rescue_detection(image)
            if rescue_detections:
                detections = rescue_detections
                rescue_used = True

        img_h, img_w = image.shape[:2]

        framing_debug = {
            "enabled": True,
            "optimizer_applied": False,
            "optimizer_rejected_count": 0,
            "optimizer_mode": "disabled_pre_pipeline",
            "focus_refined_count": 0,
            "focus_skipped_count": 0,
            "optimizer_error": None,
        }

        # Erweitere mit Detail-Analyse, Learning und Waste Classification
        db = get_db()
        analyzer = get_analyzer()
        fetcher = get_fetcher()
        waste_classifier = get_classifier()
        config = get_config()
        quality_controller = get_quality_controller()
        adaptive_policy = quality_controller.get_adaptive_policy()
        priority_feedback_classes = db.get_priority_feedback_classes(limit=8)
        learning_priority_map = {
            _normalize_class_name(str(item.get("class_name", ""))): {
                "rank": idx + 1,
                "class_name": str(item.get("class_name", "")),
                "urgency": float(item.get("urgency", 0.0)),
                "accuracy_rate": float(item.get("accuracy_rate", 0.0)),
                "total_samples": int(item.get("total_samples", 0)),
            }
            for idx, item in enumerate(priority_feedback_classes)
            if str(item.get("class_name", "")).strip()
        }
        class_quality_cache = {}
        class_risk_cache = {}
        class_knowledge_cache = {}
        web_fetch_count = 0
        debug_rejections = {
            "low_tta_support": 0,
            "high_risk_support_gate": 0,
            "medium_risk_support_gate": 0,
            "tiny_bbox_gate": 0,
            "extreme_aspect_gate": 0,
            "effective_threshold_gate": 0,
            "final_optimizer_gate": 0,
        }

        learned_risky_classes = self._get_learned_risky_classes(db)

        raw_class_counts = {}
        for raw_det in detections:
            cls = _normalize_class_name(raw_det.get("class", "unknown"))
            raw_class_counts[cls] = raw_class_counts.get(cls, 0) + 1

        enhanced_detections = []
        for det in detections:
            class_name_norm = _normalize_class_name(det.get("class", ""))
            if class_name_norm:
                det["class"] = class_name_norm

            # 1. Analysiere Objekt-Zustand (Dreck, Beschädigungen, etc.)
            conditions = analyzer.analyze_object_condition(image, det["bbox"])
            overall_condition = analyzer.get_overall_condition(conditions)

            # 2. Kalibriere Confidence basierend auf Lernhistorie
            calibrated_conf = db.get_calibrated_confidence(det["class"], det["score"])
            profile = db.get_class_knowledge_profile(det["class"])
            if profile and int(profile.get("seen_count", 0)) >= 5:
                profile_avg = float(profile.get("avg_confidence", calibrated_conf))
                calibrated_conf = (calibrated_conf * 0.75) + (profile_avg * 0.25)
                if int(profile.get("seen_count", 0)) >= 20:
                    best_conf = float(profile.get("best_confidence", calibrated_conf))
                    calibrated_conf = min(1.0, calibrated_conf + max(0.0, (best_conf - calibrated_conf) * 0.05))
            if det["class"] in class_quality_cache:
                quality_guard = class_quality_cache[det["class"]]
            else:
                quality_guard = db.get_data_quality_guard(det["class"], calibrated_conf)
                class_quality_cache[det["class"]] = quality_guard

            # 2b. TTA-Konsens beeinflusst die Zuverlässigkeit
            support_ratio = float(det.get("tta_support_ratio", 1.0))
            support_count = int(det.get("tta_support_count", 1))
            support_adjustment = (support_ratio - 0.5) * 0.08
            calibrated_conf = max(0.0, min(1.0, calibrated_conf + support_adjustment))
            support_ratio_gate = 0.22 if class_name_norm in HANDHELD_PRIORITY_CLASSES else 0.28
            support_conf_gate = 0.52 if class_name_norm in HANDHELD_PRIORITY_CLASSES else 0.58
            if support_ratio < support_ratio_gate and calibrated_conf < support_conf_gate:
                debug_rejections["low_tta_support"] += 1
                continue

            if class_name_norm in class_risk_cache:
                class_risk = class_risk_cache[class_name_norm]
            else:
                confusion = db.get_confusion_risk(det["class"])
                confusion_level = str(confusion.get("risk_level", "low"))
                is_base_risky = class_name_norm in BASE_HIGH_RISK_CLASSES
                is_learned_risky = class_name_norm in learned_risky_classes
                class_risk = {
                    "confusion_level": confusion_level,
                    "is_high_risk": is_base_risky or is_learned_risky or confusion_level == "high",
                    "is_medium_risk": confusion_level == "medium",
                }
                class_risk_cache[class_name_norm] = class_risk

            if class_risk["is_high_risk"]:
                handheld_class = class_name_norm in HANDHELD_PRIORITY_CLASSES
                min_support_ratio = 0.20 if handheld_class else 0.66
                min_support_count = 1 if handheld_class else 2
                min_confidence_gate = 0.56 if handheld_class else 0.80

                if support_ratio < min_support_ratio:
                    debug_rejections["high_risk_support_gate"] += 1
                    continue
                if support_count < min_support_count and calibrated_conf < min_confidence_gate:
                    debug_rejections["high_risk_support_gate"] += 1
                    continue
            elif class_risk["is_medium_risk"] and support_ratio < 0.55 and calibrated_conf < 0.72:
                debug_rejections["medium_risk_support_gate"] += 1
                continue

            # 3. Extrahiere Bildausschnitt für Material-Analyse
            x1, y1, x2, y2 = [int(c) for c in det["bbox"]]
            x1 = max(0, min(x1, img_w - 1))
            y1 = max(0, min(y1, img_h - 1))
            x2 = max(0, min(x2, img_w))
            y2 = max(0, min(y2, img_h))
            if x2 <= x1:
                x2 = min(img_w, x1 + 1)
            if y2 <= y1:
                y2 = min(img_h, y1 + 1)
            det["bbox"] = [float(x1), float(y1), float(x2), float(y2)]
            image_region = image[y1:y2, x1:x2] if y2 > y1 and x2 > x1 else None

            # 3b. Geometrischer Qualitätsfilter für Falsch-Positiv-Reduktion
            bbox_w = max(1, x2 - x1)
            bbox_h = max(1, y2 - y1)
            bbox_area_ratio = (bbox_w * bbox_h) / max(float(img_w * img_h), 1.0)
            bbox_aspect_ratio = max(bbox_w / bbox_h, bbox_h / bbox_w)

            min_area_ratio = 0.00008 if class_name_norm in HANDHELD_PRIORITY_CLASSES else MIN_BBOX_AREA_RATIO
            min_area_conf_gate = 0.65 if class_name_norm in HANDHELD_PRIORITY_CLASSES else 0.70
            if bbox_area_ratio < min_area_ratio and calibrated_conf < min_area_conf_gate:
                debug_rejections["tiny_bbox_gate"] += 1
                continue
            if bbox_aspect_ratio > MAX_BBOX_ASPECT_RATIO and calibrated_conf < 0.75:
                debug_rejections["extreme_aspect_gate"] += 1
                continue

            # 3c. Lokales Objektwissen aus DB als zusätzlicher Genauigkeitsanker
            memory_hints = []
            object_knowledge = db.get_object_knowledge(det["class"])
            if object_knowledge:
                mem_conf = float(object_knowledge.get("confidence", 0.0))
                mem_material = str(object_knowledge.get("inferred_material", "")).strip().lower()
                if mem_material in MATERIAL_TO_HINT:
                    memory_hints.append(MATERIAL_TO_HINT[mem_material])
                if mem_conf >= 0.85:
                    calibrated_conf = min(1.0, calibrated_conf + 0.03)

            # 4. Internetwissen als zusätzlicher Sicherheits-/Material-Hinweis
            if config.enable_web_knowledge and calibrated_conf >= config.web_fetch_min_confidence:
                if det["class"] in class_knowledge_cache:
                    knowledge_info = class_knowledge_cache[det["class"]]
                elif web_fetch_count < max(config.max_web_fetch_classes_per_image, 0):
                    knowledge_info = fetcher.get_disposal_hints(det["class"], db=db)
                    class_knowledge_cache[det["class"]] = knowledge_info
                    web_fetch_count += 1
                else:
                    knowledge_info = {"hints": [], "confidence": 0.0}
                knowledge_hints = knowledge_info.get("hints", [])
            else:
                knowledge_info = {"hints": [], "confidence": 0.0}
                knowledge_hints = []

            if memory_hints:
                merged_hints = []
                for hint in knowledge_hints + memory_hints:
                    if hint not in merged_hints:
                        merged_hints.append(hint)
                knowledge_hints = merged_hints

            risk_penalty = 0.0
            if class_risk["is_high_risk"]:
                risk_penalty += 0.02 if class_name_norm in HANDHELD_PRIORITY_CLASSES else 0.09
            elif class_risk["is_medium_risk"]:
                risk_penalty += 0.04
            if any(h in RISKY_HINTS for h in knowledge_hints):
                risk_penalty += 0.05

            class_output_threshold = 0.40
            try:
                class_output_threshold = db.get_class_output_threshold(det["class"], default_threshold=0.40)
            except Exception:
                class_output_threshold = 0.40

            effective_threshold = max(OUTPUT_MIN_CONFIDENCE, min(0.90, class_output_threshold + risk_penalty))

            # Avoid over-pruning phones/watches while preserving the hard 60% minimum.
            class_name_lc = str(det.get("class", "")).strip().lower()
            if class_name_lc in HANDHELD_PRIORITY_CLASSES and support_ratio >= MIN_TTA_SUPPORT_RATIO:
                effective_threshold = min(effective_threshold, OUTPUT_MIN_CONFIDENCE)

            # Hard output threshold: nur ausreichend sichere Erkennungen ausgeben
            if calibrated_conf < effective_threshold:
                debug_rejections["effective_threshold_gate"] += 1
                continue

            # 5. WASTE CLASSIFICATION - Entscheide in welche Mülltonne!
            waste_info = waste_classifier.classify_waste(
                class_name=det["class"],
                confidence=calibrated_conf,
                object_condition=overall_condition,
                image_region=image_region,
                learning_context=quality_guard,
                knowledge_hints=knowledge_hints,
                adaptive_policy=adaptive_policy,
                prior_knowledge=object_knowledge,
            )

            # 6. Speichere in Learning DB
            detection_id = db.add_detection(
                predicted_class=det["class"],
                confidence=calibrated_conf,
                bbox=det["bbox"],
                details=overall_condition,
                image_hash=image_hash,
            )

            try:
                db.upsert_object_knowledge(
                    object_name=det["class"],
                    inferred_material=waste_info.get("material", "unknown"),
                    inferred_bin=waste_info.get("bin", "RESTMÜLL"),
                    confidence=calibrated_conf,
                    source="detection_pipeline",
                    notes=waste_info.get("action", "AUTO_SORT")
                )
            except Exception:
                pass

            # Speichere Conditions
            for cond in conditions:
                db.add_condition(detection_id, cond["type"], cond["severity"], cond["description"])

            if config.enable_audit_logging:
                db.add_decision_audit(
                    detection_id=detection_id,
                    class_name=det["class"],
                    waste_info=waste_info
                )

            # 7. Erweitere Detection mit allen Infos
            det["calibrated_confidence"] = calibrated_conf
            det["original_confidence"] = det["score"]
            det["object_condition"] = overall_condition
            det["detection_id"] = detection_id
            det["image_hash"] = image_hash
            det["learned"] = True
            det["quality_guard"] = quality_guard
            det["tta_support_count"] = support_count
            det["tta_support_ratio"] = support_ratio
            det["bbox_area_ratio"] = bbox_area_ratio
            det["class_threshold"] = class_output_threshold
            det["class_risk_policy"] = {
                "is_high_risk": class_risk["is_high_risk"],
                "is_medium_risk": class_risk["is_medium_risk"],
                "risk_penalty": risk_penalty,
                "effective_threshold": effective_threshold,
            }
            det["web_knowledge"] = {
                "available": len(knowledge_hints) > 0,
                "hints": knowledge_hints,
                "confidence": knowledge_info.get("confidence", 0.0)
            }

            online_validation = knowledge_info.get("online_validation", {}) if isinstance(knowledge_info, dict) else {}
            web_source = "none"
            if knowledge_hints:
                web_source = "local_or_cached"
            if online_validation.get("accepted", False):
                web_source = "online_validated"
            elif online_validation:
                web_source = "online_unverified"

            det["data_provenance"] = {
                "model": "YOLOX",
                "pipeline": "local_model_plus_learning_plus_optional_web",
                "class_name": det.get("class"),
                "confidence_chain": {
                    "raw_confidence": float(det.get("score", 0.0)),
                    "calibrated_confidence": float(calibrated_conf),
                    "effective_threshold": float(effective_threshold),
                    "passed_threshold": bool(calibrated_conf >= effective_threshold),
                },
                "tta": {
                    "support_ratio": float(support_ratio),
                    "support_count": int(support_count),
                },
                "local_learning": {
                    "used": bool(object_knowledge),
                    "source": str((object_knowledge or {}).get("source", "none")),
                    "material_hint": str((object_knowledge or {}).get("inferred_material", "")),
                    "memory_hints": list(memory_hints),
                },
                "web_knowledge": {
                    "used": bool(knowledge_hints),
                    "source": web_source,
                    "hints": list(knowledge_hints),
                    "confidence": float(knowledge_info.get("confidence", 0.0)),
                    "validation": online_validation,
                },
            }

            det["decision_trace"] = {
                "risk_policy": det["class_risk_policy"],
                "quality_guard_reasons": list(quality_guard.get("reasons", [])),
                "waste_action": waste_info.get("action", "MANUAL_CHECK_REQUIRED"),
                "requires_manual_review": bool(waste_info.get("requires_manual_review", False)),
                "review_reasons": list(waste_info.get("review_reasons", [])),
            }

            reliability_signal = float((quality_guard.get("reliability") or {}).get("reliability", 0.5) or 0.5)
            confusion_level = str((quality_guard.get("confusion") or {}).get("risk_level", "low")).lower()
            knowledge_signal = float(knowledge_info.get("confidence", 0.0) or 0.0)
            confusion_penalty = 0.0
            if confusion_level == "high":
                confusion_penalty = 0.18
            elif confusion_level == "medium":
                confusion_penalty = 0.08

            uncertainty_score = 1.0 - (
                (float(calibrated_conf) * 0.48)
                + (float(support_ratio) * 0.18)
                + (reliability_signal * 0.16)
                + (knowledge_signal * 0.10)
            )
            uncertainty_score += min(0.10, max(0.0, risk_penalty * 0.5))
            uncertainty_score += confusion_penalty
            uncertainty_score = max(0.0, min(1.0, uncertainty_score))

            det["uncertainty_score"] = float(uncertainty_score)
            det["decision_reliability"] = float(max(0.0, min(1.0, 1.0 - uncertainty_score)))

            # WASTE SORTING INFO - Das wichtigste für Mülltrennung!
            det["waste_sorting"] = waste_info
            det["requires_manual_review"] = waste_info.get("requires_manual_review", False)
            det["user_action"] = waste_info.get("action", "MANUAL_CHECK_REQUIRED")
            det["adaptive_policy_mode"] = adaptive_policy.get("mode", "normal")

            learning_priority = learning_priority_map.get(class_name_norm)
            if learning_priority:
                det["learning_target"] = {
                    **learning_priority,
                    "is_focus_class": True,
                }

                # Confidence gate for focus classes: uncertain detections become review cases
                # so user feedback can improve exactly the classes with highest error impact.
                if float(calibrated_conf) < 0.72:
                    review_reasons = set(waste_info.get("review_reasons", []) or [])
                    review_reasons.add("learning_priority_class")
                    waste_info["review_reasons"] = sorted(review_reasons)
                    waste_info["requires_manual_review"] = True
                    waste_info["action"] = "MANUAL_CHECK_REQUIRED"
                    waste_info["recommended_bin"] = None
                    det["requires_manual_review"] = True
                    det["user_action"] = "MANUAL_CHECK_REQUIRED"
            else:
                det["learning_target"] = {
                    "is_focus_class": False,
                }

            enhanced_detections.append(det)

        # ===== FINAL VALIDATION: Multi-Layer Detection Optimization (v2.2) =====
        # Enforce 60% hard threshold + geometry checks + anomaly detection
        try:
            optimizer = get_detection_optimizer()
            valid_detections, rejected_detections = optimizer.validate_and_filter_detections(
                detections=enhanced_detections,
                image_width=img_w,
                image_height=img_h,
                strict_mode=True  # Strict mode: apply all validations
            )

            debug_rejections["final_optimizer_gate"] = len(rejected_detections)

            # Final framing only on accepted detections to avoid harming recognition quality.
            valid_detections, output_framing_meta = self._apply_output_framing(
                image=image,
                detections=valid_detections,
                max_refines=MAX_OUTPUT_FOCUS_REFINES_PER_IMAGE,
            )
            framing_debug.update(output_framing_meta)

            # Auto self-learning when recognition quality is weak:
            # always local trusted seeds first, then internet enrichment if available.
            auto_self_learning_report = None
            recognition_issue = (
                len(detections) == 0
                or len(enhanced_detections) == 0
                or len(valid_detections) == 0
            )
            if recognition_issue:
                try:
                    auto_self_learning_report = fetcher.auto_self_learn_on_recognition_issue(
                        db=db,
                        trigger_objects=list(raw_class_counts.keys()),
                        include_priority_terms=True,
                        max_terms=220,
                    )
                except Exception as learn_err:
                    auto_self_learning_report = {
                        "status": "error",
                        "error": str(learn_err),
                    }

                try:
                    db.add_self_improvement_run(
                        event_type="recognition_issue",
                        status=str(auto_self_learning_report.get("status", "unknown")),
                        report=auto_self_learning_report,
                    )
                except Exception:
                    pass

            # Log rejection statistics (for debugging)
            if rejected_detections:
                report = optimizer.generate_detection_report(valid_detections, rejected_detections)
                # Could log this for analytics

            if debug:
                model_has_handheld_signal = any(k in HANDHELD_PRIORITY_CLASSES for k in raw_class_counts.keys())
                return {
                    "detections": valid_detections,
                    "debug": {
                        "raw_class_counts": raw_class_counts,
                        "pipeline_rejections": debug_rejections,
                        "optimizer_rejected_count": len(rejected_detections),
                        "optimizer_report": optimizer.generate_detection_report(valid_detections, rejected_detections),
                        "framing": framing_debug,
                        "rescue_detection_used": rescue_used,
                        "input_detection_count": len(detections),
                        "enhanced_detection_count": len(enhanced_detections),
                        "auto_self_learning": auto_self_learning_report,
                        "online_data_policy": {
                            "local_first": True,
                            "online_only_when_issue": True,
                            "online_requires_validation": True,
                        },
                        "diagnosis": {
                            "model_detected_candidates": len(detections) > 0,
                            "model_has_handheld_signal": model_has_handheld_signal,
                            "likely_issue": (
                                "model_no_signal" if len(detections) == 0 else
                                "pipeline_filtering" if len(enhanced_detections) == 0 else
                                "final_optimizer_filtering" if len(valid_detections) == 0 else
                                "ok"
                            ),
                        },
                        "learning_focus": {
                            "priority_classes": priority_feedback_classes,
                            "focus_gate_min_confidence": 0.72,
                        },
                    },
                }

            return valid_detections
        except Exception as e:
            # Fallback: return enhanced_detections as-is if optimizer fails
            print(f"[Warning] Detection optimizer failed: {e}, returning unfiltered detections")
            try:
                enhanced_detections, output_framing_meta = self._apply_output_framing(
                    image=image,
                    detections=enhanced_detections,
                    max_refines=MAX_OUTPUT_FOCUS_REFINES_PER_IMAGE,
                )
                framing_debug.update(output_framing_meta)
            except Exception:
                pass
            if debug:
                return {
                    "detections": enhanced_detections,
                    "debug": {
                        "raw_class_counts": raw_class_counts,
                        "pipeline_rejections": debug_rejections,
                        "optimizer_error": str(e),
                        "framing": framing_debug,
                        "rescue_detection_used": rescue_used,
                        "input_detection_count": len(detections),
                        "enhanced_detection_count": len(enhanced_detections),
                        "auto_self_learning": {
                            "status": "skipped_due_to_optimizer_error"
                        },
                        "diagnosis": {
                            "model_detected_candidates": len(detections) > 0,
                            "model_has_handheld_signal": any(k in HANDHELD_PRIORITY_CLASSES for k in raw_class_counts.keys()),
                            "likely_issue": "optimizer_error_fallback",
                        },
                    },
                }
            return enhanced_detections


# Alias für Kompatibilität - viele Tests erwarten "ObjectDetector"
class ObjectDetector(YOLOXRunner):
    """Wrapper-Klasse für Kompatibilität mit Tests"""
    pass


_runner = None


def _get_runner():
    global _runner
    if _runner is None:
        ckpt = os.environ.get("YOLOX_CKPT") or os.path.join(ROOT, "YOLOX_outputs/yolox_s/yolox_s.pth")
        device = os.environ.get("YOLOX_DEVICE", "cpu")
        exp_name = os.environ.get("YOLOX_EXP_NAME", "yolox_s")
        _runner = YOLOXRunner(ckpt_path=ckpt, exp_name=exp_name, device=device)
        classifier = get_classifier()
        db = get_db()
        fetcher = get_fetcher()
        class_names = list(getattr(_runner, "class_names", []) or COCO_CLASSES)
        try:
            db.seed_class_knowledge_profiles(class_names)
        except Exception:
            pass
        try:
            classifier.bootstrap_known_classes(class_names)
        except Exception:
            pass
        try:
            profiles = []
            for class_name in class_names:
                profile = classifier.get_class_profile(class_name)
                profile["confidence"] = 0.45
                profiles.append(profile)
            db.seed_object_knowledge_index(profiles, source="class_bootstrap")
        except Exception:
            pass
        try:
            fetcher.warmup_object_knowledge(class_names, db=db, max_live_fetch=24)
        except Exception:
            pass
    return _runner


def detect_image(image_bytes: bytes, debug: bool = False):
    """Dekodiere Bildbytes und liefere Detektionen als JSON-kompatible Liste zurück."""
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError("Could not decode image bytes")
    runner = _get_runner()
    return runner.detect(img, image_hash=image_hash, debug=debug)
