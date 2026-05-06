"""
Sample Memory for Continual Learning
===================================
Speichert erkannte Müllbilder + Feedback-Labels (stimmt/stimmt nicht)
für kontinuierliches Lernen aus bestehenden und neuen Daten.
"""
import json
import shutil
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).parent / "waste_memory"
INCOMING_DIR = BASE_DIR / "incoming"
VERIFIED_DIR = BASE_DIR / "verified"
FEEDBACK_DIR = BASE_DIR / "feedback"


def _ensure_dirs():
    for path in [INCOMING_DIR, VERIFIED_DIR, FEEDBACK_DIR, FEEDBACK_DIR / "stimmt", FEEDBACK_DIR / "stimmt_nicht"]:
        path.mkdir(parents=True, exist_ok=True)


def save_incoming_sample(image_bytes: bytes, image_hash: str, detections: List[Dict]) -> Dict:
    """Speichert das Originalbild + Detection-Metadaten als Rohdatenpool."""
    _ensure_dirs()

    image_path = INCOMING_DIR / f"{image_hash}.jpg"
    meta_path = INCOMING_DIR / f"{image_hash}.json"

    if not image_path.exists():
        image_path.write_bytes(image_bytes)

    payload = {
        "image_hash": image_hash,
        "timestamp": datetime.now().isoformat(),
        "detections": detections,
    }
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "image_path": str(image_path),
        "meta_path": str(meta_path),
    }


def save_feedback_sample(
    image_hash: str,
    detection_id: int,
    predicted_class: str,
    correct_class: str,
    is_correct: bool,
    comment: Optional[str] = None,
):
    """Speichert Feedback-Beispiel und legt Bild in verifiziertem Klassenordner ab."""
    _ensure_dirs()

    status_folder = "stimmt" if is_correct else "stimmt_nicht"
    feedback_path = FEEDBACK_DIR / status_folder / f"det_{detection_id}_{image_hash}.json"

    record = {
        "detection_id": detection_id,
        "image_hash": image_hash,
        "predicted_class": predicted_class,
        "correct_class": correct_class,
        "is_correct": is_correct,
        "comment": comment,
        "timestamp": datetime.now().isoformat(),
    }
    feedback_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    src_image = INCOMING_DIR / f"{image_hash}.jpg"
    class_dir = VERIFIED_DIR / correct_class.replace(" ", "_")
    class_dir.mkdir(parents=True, exist_ok=True)
    dst_image = class_dir / f"{image_hash}.jpg"

    if src_image.exists() and not dst_image.exists():
        shutil.copy2(src_image, dst_image)

    return {
        "feedback_path": str(feedback_path),
        "verified_image_path": str(dst_image),
    }


def get_memory_stats() -> Dict:
    """Statistiken des gespeicherten Lernspeichers."""
    _ensure_dirs()

    incoming_images = len(list(INCOMING_DIR.glob("*.jpg")))
    verified_images = len(list(VERIFIED_DIR.glob("**/*.jpg")))
    correct_feedback = len(list((FEEDBACK_DIR / "stimmt").glob("*.json")))
    incorrect_feedback = len(list((FEEDBACK_DIR / "stimmt_nicht").glob("*.json")))

    class_counts = {}
    for class_dir in VERIFIED_DIR.iterdir():
        if class_dir.is_dir():
            class_counts[class_dir.name] = len(list(class_dir.glob("*.jpg")))

    return {
        "incoming_images": incoming_images,
        "verified_images": verified_images,
        "feedback_correct": correct_feedback,
        "feedback_incorrect": incorrect_feedback,
        "verified_classes": class_counts,
    }


def contains_person_detection(detections: List[Dict]) -> bool:
    """Prüft ob Personen erkannt wurden (Datenschutz-relevant)."""
    for det in detections:
        if det.get("class") == "person":
            return True
    return False


def cleanup_old_memory_files(retention_days: int = 30) -> Dict:
    """Löscht alte Dateien entsprechend Retention-Policy."""
    _ensure_dirs()
    threshold = datetime.now().timestamp() - (max(1, retention_days) * 24 * 3600)

    removed = {
        "incoming_images": 0,
        "incoming_meta": 0,
        "feedback": 0,
    }

    for p in INCOMING_DIR.glob("*.jpg"):
        if p.stat().st_mtime < threshold:
            p.unlink(missing_ok=True)
            removed["incoming_images"] += 1
    for p in INCOMING_DIR.glob("*.json"):
        if p.stat().st_mtime < threshold:
            p.unlink(missing_ok=True)
            removed["incoming_meta"] += 1

    for folder in [FEEDBACK_DIR / "stimmt", FEEDBACK_DIR / "stimmt_nicht"]:
        for p in folder.glob("*.json"):
            if p.stat().st_mtime < threshold:
                p.unlink(missing_ok=True)
                removed["feedback"] += 1

    return {
        "retention_days": retention_days,
        "removed": removed,
    }


def export_training_dataset(train_ratio: float = 0.8) -> Dict:
    """
    Exportiert verifizierte Beispiele als YOLO-kompatibles Detection-Dataset.
    Nutzt Bounding-Boxen aus incoming-Metadaten + correct_class aus Feedback.
    """
    _ensure_dirs()

    export_root = BASE_DIR / "exports" / datetime.now().strftime("dataset_%Y%m%d_%H%M%S")
    images_train = export_root / "images" / "train"
    images_val = export_root / "images" / "val"
    labels_train = export_root / "labels" / "train"
    labels_val = export_root / "labels" / "val"
    for p in [images_train, images_val, labels_train, labels_val]:
        p.mkdir(parents=True, exist_ok=True)

    feedback_files = list((FEEDBACK_DIR / "stimmt").glob("*.json")) + list((FEEDBACK_DIR / "stimmt_nicht").glob("*.json"))
    samples = []
    classes = set()

    for feedback_file in feedback_files:
        try:
            record = json.loads(feedback_file.read_text(encoding="utf-8"))
            image_hash = record.get("image_hash")
            detection_id = record.get("detection_id")
            correct_class = record.get("correct_class")
            if not image_hash or not detection_id or not correct_class:
                continue

            image_path = INCOMING_DIR / f"{image_hash}.jpg"
            meta_path = INCOMING_DIR / f"{image_hash}.json"
            if not image_path.exists() or not meta_path.exists():
                continue

            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            detections = meta.get("detections", [])
            det_match = None
            for det in detections:
                if det.get("detection_id") == detection_id:
                    det_match = det
                    break
            if det_match is None:
                continue

            bbox = det_match.get("bbox")
            if not bbox or len(bbox) != 4:
                continue

            samples.append({
                "image_hash": image_hash,
                "image_path": image_path,
                "class_name": correct_class,
                "bbox": bbox,
            })
            classes.add(correct_class)
        except Exception:
            continue

    classes = sorted(classes)
    class_to_idx = {name: idx for idx, name in enumerate(classes)}

    random.shuffle(samples)
    split = int(len(samples) * max(0.5, min(train_ratio, 0.95)))
    train_samples = samples[:split]
    val_samples = samples[split:]

    def _write_label(sample, img_dst, lbl_dst):
        import cv2
        img = cv2.imread(str(sample["image_path"]))
        if img is None:
            return False
        h, w = img.shape[:2]
        x1, y1, x2, y2 = [float(v) for v in sample["bbox"]]
        cx = ((x1 + x2) / 2.0) / max(w, 1)
        cy = ((y1 + y2) / 2.0) / max(h, 1)
        bw = max(0.0, (x2 - x1) / max(w, 1))
        bh = max(0.0, (y2 - y1) / max(h, 1))
        cls_idx = class_to_idx[sample["class_name"]]

        shutil.copy2(sample["image_path"], img_dst)
        lbl_dst.write_text(f"{cls_idx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding="utf-8")
        return True

    written_train = 0
    written_val = 0

    for sample in train_samples:
        img_dst = images_train / f"{sample['image_hash']}.jpg"
        lbl_dst = labels_train / f"{sample['image_hash']}.txt"
        if _write_label(sample, img_dst, lbl_dst):
            written_train += 1

    for sample in val_samples:
        img_dst = images_val / f"{sample['image_hash']}.jpg"
        lbl_dst = labels_val / f"{sample['image_hash']}.txt"
        if _write_label(sample, img_dst, lbl_dst):
            written_val += 1

    dataset_yaml = {
        "path": str(export_root),
        "train": "images/train",
        "val": "images/val",
        "names": {idx: name for name, idx in class_to_idx.items()},
        "nc": len(classes),
    }
    (export_root / "dataset.yaml").write_text(json.dumps(dataset_yaml, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "export_path": str(export_root),
        "classes": classes,
        "class_count": len(classes),
        "samples_total": len(samples),
        "samples_train": written_train,
        "samples_val": written_val,
        "dataset_yaml": str(export_root / "dataset.yaml"),
    }


def build_improvement_recommendations(db) -> Dict:
    """Erstellt konkrete Optimierungsmaßnahmen basierend auf realen Daten."""
    memory = get_memory_stats()
    stats = db.get_learning_stats()
    hard_cases = db.get_hard_cases(limit=200)
    priorities = db.get_priority_feedback_classes(limit=8)

    recommendations = []

    if stats.get("learning_rate", 0.0) < 0.15:
        recommendations.append("Mehr 'stimmt/stimmt nicht' Feedback sammeln (Ziel: >15% Feedback-Rate).")
    if memory.get("verified_images", 0) < 200:
        recommendations.append("Mehr verifizierte Müllbilder sammeln (Ziel: mindestens 200 Beispiele).")
    if len(hard_cases) > 40:
        recommendations.append("Hard-Cases priorisieren und gezielt nachlabeln/retrainen.")
    if priorities:
        top = ", ".join([p["class_name"] for p in priorities[:3]])
        recommendations.append(f"Top-Verwechslungsklassen zuerst verbessern: {top}.")

    return {
        "learning_stats": stats,
        "memory_stats": memory,
        "hard_cases": len(hard_cases),
        "priority_classes": priorities,
        "recommendations": recommendations,
    }
