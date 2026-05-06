# FIX: OpenMP duplicate library error (NumPy + OpenCV + MKL)
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import socket
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(
    title="SmarTrash AI - Self-Learning Object Detection",
    description="Advanced object detection with self-learning, detail analysis, and feedback system (v2.2 - Perfected Detection)",
    version="2.2.0",
)

# CORS aktivieren
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Frontend Dashboard
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_path):
    app.mount("/dashboard", StaticFiles(directory=frontend_path, html=True), name="dashboard")

# Setze YOLOX Checkpoint Path
model_path = os.environ.get("YOLOX_CKPT", "C:\\models\\yolox_l.pth")
os.environ["YOLOX_CKPT"] = model_path
os.environ.setdefault("YOLOX_DEVICE", "cpu")
if "YOLOX_EXP_NAME" not in os.environ:
    name = os.path.basename(str(model_path or "")).lower()
    exp_guess = "yolox_s"
    for key in ["yolox_x", "yolox_l", "yolox_m", "yolox_s", "yolox_tiny", "yolox_nano"]:
        if key in name:
            exp_guess = key
            break
    os.environ["YOLOX_EXP_NAME"] = exp_guess


@app.on_event("startup")
def startup_auto_self_improvement():
    """Automatische Selbstoptimierung beim Backend-Start (lokal zuerst, dann online-validiert)."""
    try:
        from learning_db import get_db
        from web_knowledge import get_fetcher

        db = get_db()
        fetcher = get_fetcher()
        report = fetcher.auto_self_learn_on_recognition_issue(
            db=db,
            trigger_objects=fetcher.ONLINE_SELF_LEARN_PRIORITY_TERMS,
            include_priority_terms=True,
            max_terms=180,
            force=False,
        )
        db.add_self_improvement_run(
            event_type="api_startup_auto",
            status=str(report.get("status", "unknown")),
            report=report,
        )
    except Exception as e:
        print(f"[Startup] Auto self-improvement skipped: {e}")

# Pydantic Models für Requests
class FeedbackRequest(BaseModel):
    detection_id: int
    predicted_class: str
    correct_class: str
    comment: Optional[str] = None


class VerifyFeedbackRequest(BaseModel):
    detection_id: int
    feedback_type: Optional[str] = None  # 'stimmt' or 'stimmt_nicht' (from Dashboard)
    stimmt: Optional[bool] = None  # Legacy: true/false
    correct_class: Optional[str] = None
    image_base64: Optional[str] = None
    comment: Optional[str] = None

@app.get("/")
def read_root():
    """API Info"""
    from safety_config import get_config
    cfg = get_config()

    return {
        "message": "SmarTrash AI - Self-Learning Detection System v2.2 🚀 (Perfected)",
        "version": "2.2.0",
        "status": "running",
        "mode": "hard_safety" if cfg.hard_safety_mode else "standard",
        "features": {
            "self_learning": True,
            "feedback_system": True,
            "detail_analysis": True,
            "condition_detection": True,
            "web_knowledge": True,
            "public_knowledge_seeds": True,
            "persistent_memory": True,
            "confidence_calibration": True,
            "500plus_dataset_import": True,
            "framing_optimization": True,
            "multi_scale_tta": True,
            "detection_optimization_v22": True,
            "local_first_knowledge": True,
            "auto_online_self_learning": True,
            "hard_safety_mode": cfg.hard_safety_mode
        },
        "new_features_v2_2": {
            "detection_threshold": "60% Hard Minimum (no exceptions)",
            "multi_layer_validation": "Geometry + Confidence + Class-Specific + Anomaly Detection",
            "object_quality_guarantee": "Only high-confidence, spatially-valid detections",
            "false_positive_reduction": "Class-specific thresholds + edge detection + anomaly filtering"
        },
        "recognition_profile": __import__("recognition_profile").load_recognition_profile(),
        "endpoints": {
            "GET /": "API info",
            "GET /dashboard": "Web Dashboard (Live-Feed, Feedback, Compliance)",
            "GET /health": "Health check with learning stats",
            "POST /detect": "Upload image for detection with 60% hard threshold (OPTIMIZED v2.2)",
            "POST /detect?debug=true": "Detection + pipeline rejection diagnostics",
            "POST /feedback": "Submit user feedback to improve AI",
            "POST /feedback/verify": "Binary feedback: stimmt oder stimmt nicht",
            "GET /learning/stats": "View learning progress",
            "GET /learning/class/{class_name}": "View accuracy for specific class",
            "GET /learning/priorities": "Top classes where feedback improves most",
            "GET /learning/review-queue": "Open manual-review cases without feedback",
            "POST /learning/knowledge/import": "Import seed knowledge (80 terms max)",
            "POST /learning/dataset/import-all": "🚀 MASSIVE: Import up to 5000 objects from free datasets",
            "GET /learning/dataset/info": "Info about available public datasets & licensing",
            "NOTE auto-learning": "Detection uses trusted local knowledge first, then live web enrichment if internet is available and recognition is weak",
            "GET /learning/threshold/{class_name}": "Show adaptive class output threshold",
            "GET /learning/risky-classes": "Show classes with high confusion risk",
            "POST /learning/export-dataset": "Export verified dataset for retraining",
            "POST /learning/self-improvement/run": "Trigger local-first self-improvement cycle (+ online validation if internet is available)",
            "GET /learning/self-improvement/status": "Show persistent self-improvement metrics and latest runs",
            "GET /learning/recommendations": "Data-driven next improvements",
            "GET /quality/control": "Adaptive quality controller state",
            "GET /quality/error-trend": "Rolling error-rate trend",
            "GET /compliance/no-cost": "No hidden costs policy status",
            "GET /compliance/report": "Compliance report (privacy + no-cost)",
            "POST /compliance/cleanup-data": "Apply retention cleanup",
            "GET /config/safety": "Active hard safety configuration"
        }
    }

@app.get("/health")
def health_check():
    """Health Check with Learning Stats"""
    from compliance_guard import build_compliance_report
    from learning_db import get_db
    from safety_config import get_config

    model_exists = os.path.exists(model_path)
    db = get_db()
    cfg = get_config()
    stats = db.get_learning_stats()
    compliance = build_compliance_report()

    warnings = []
    if not model_exists:
        warnings.append("model_missing")
    if stats.get("learning_rate", 0.0) < 0.05:
        warnings.append("low_feedback_coverage")
    if stats.get("average_accuracy", 0.0) < 0.6 and stats.get("total_feedback", 0) >= 10:
        warnings.append("low_accuracy_after_feedback")
    if not compliance.get("compliant", False):
        warnings.append("compliance_issues")

    return {
        "status": "healthy",
        "purpose": "Intelligente Mülltrennung System",
        "version": "2.2.0",
        "optimization_level": "PERFECTED",
        "detection_threshold": "60% Hard Minimum",
        "model_path": model_path,
        "model_exists": model_exists,
        "device": os.environ.get("YOLOX_DEVICE", "cpu"),
        "waste_bins": ["Restmüll", "Biomüll", "Papier", "Plastik"],
        "features": {
            "waste_sorting": True,
            "material_detection": True,
            "battery_warning": True,
            "hard_safety_mode": cfg.hard_safety_mode,
            "test_time_augmentation": True,
            "multi_scale_testing": True,
            "advanced_nms": True,
            "detail_analysis": True,
            "self_learning": True,
            "web_knowledge": True,
            "detection_optimization": "Multi-Layer Validation (v2.2)",
            "coco_classes": 80,
            "optimization": "Production AI with Perfect Waste Sorting"
        },
        "recognition_profile": __import__("recognition_profile").load_recognition_profile(),
        "learning": stats,
        "compliance": {
            "compliant": compliance.get("compliant", False),
            "score": compliance.get("score", 0.0),
            "issues": compliance.get("issues", [])
        },
        "warnings": warnings,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/detect")
async def detect_image(file: UploadFile = File(...), debug: bool = Query(default=False)):
    """Upload image for advanced object detection with detail analysis"""
    content_type = str(file.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")

    if not os.path.exists(model_path):
        raise HTTPException(
            status_code=503,
            detail=f"Model not found at {model_path}. Set YOLOX_CKPT environment variable."
        )

    try:
        # Lazy import YOLOX inference
        import inference

        # Read image data
        data = await file.read()

        # Run detection with detail analysis and learning
        inference_result = inference.detect_image(data, debug=debug)
        detections = inference_result.get("detections", []) if isinstance(inference_result, dict) else inference_result

        # Persistiere Müll-Bilddatei + Metadaten für kontinuierliches Lernen
        sample_memory_saved = False
        sample_memory_skipped_reason = None
        try:
            from safety_config import get_config
            from sample_memory import (contains_person_detection,
                                       save_incoming_sample)

            cfg = get_config()
            image_hash = detections[0].get("image_hash") if detections else None
            has_person = contains_person_detection(detections)

            allow_store = bool(image_hash)
            if has_person and not cfg.store_images_with_person:
                allow_store = False
                sample_memory_skipped_reason = "person_detected_privacy_policy"

            if allow_store:
                save_incoming_sample(data, image_hash=image_hash, detections=detections)
                sample_memory_saved = True
            elif sample_memory_skipped_reason is None:
                sample_memory_skipped_reason = "no_image_hash_or_no_detections"
        except Exception:
            # Lernen soll weiterlaufen, auch wenn Dateispeicherung fehlschlägt
            sample_memory_skipped_reason = "memory_save_error"

        # Sortiere nach kalibierter Confidence (beste zuerst)
        detections = sorted(detections, key=lambda x: x.get("calibrated_confidence", x["score"]), reverse=True)

        # Analysiere für bessere Übersicht
        has_battery_warning = any(
            any(("BATTERIE" in w) or ("Akku" in w) or ("akku" in w)
                for w in d.get("waste_sorting", {}).get("warnings", []))
            for d in detections
        )
        web_enriched_count = sum(
            1 for d in detections
            if (d.get("data_provenance", {}).get("web_knowledge", {}).get("used", False))
        )
        local_learning_count = sum(
            1 for d in detections
            if (d.get("data_provenance", {}).get("local_learning", {}).get("used", False))
        )
        explainable_count = sum(
            1 for d in detections
            if bool(d.get("waste_sorting", {}).get("explainability"))
        )
        manual_review_count = sum(1 for d in detections if d.get("requires_manual_review", False))
        high_quality_count = sum(
            1 for d in detections
            if d.get("waste_sorting", {}).get("decision_quality", 0.0) >= 0.75
        )
        policy_mode = detections[0].get("adaptive_policy_mode", "normal") if detections else "normal"

        response = {
            "status": "success",
            "detections": detections,
            "count": len(detections),
            "battery_warning": has_battery_warning,
            "manual_review_count": manual_review_count,
            "high_quality_count": high_quality_count,
            "sorting_quality": "needs_review" if manual_review_count > 0 else "high_confidence",
            "quality_control_mode": policy_mode,
            "provenance_summary": {
                "total_detections": len(detections),
                "using_local_learning": local_learning_count,
                "using_web_knowledge": web_enriched_count,
                "with_explainability": explainable_count,
                "decision_transparency": "enabled",
            },
            "actions": {
                "manual_check_required": manual_review_count > 0,
                "auto_sort_allowed": manual_review_count == 0,
                "safety_note": "Bei MANUAL_CHECK_REQUIRED bitte Nutzerentscheidung einholen"
            },
            "best_detection": detections[0] if detections else None,
            "ai_features": {
                "tta_enabled": True,
                "multiscale_enabled": True,
                "detail_analysis": True,
                "condition_detection": True,
                "confidence_calibration": True,
                "self_learning": True,
                "web_knowledge_hints": True,
                "quality_guard": True
            },
            "feedback_info": "You can submit feedback via POST /feedback to improve AI accuracy",
            "data_memory": {
                "saved": sample_memory_saved,
                "skipped_reason": sample_memory_skipped_reason
            },
            "timestamp": datetime.now().isoformat()
        }

        if debug and isinstance(inference_result, dict):
            response["debug"] = inference_result.get("debug", {})

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection error: {str(e)}")

@app.post("/feedback")
def submit_feedback(feedback: FeedbackRequest):
    """Submit user feedback to improve AI (Human teaches AI!)"""
    from learning_db import get_db

    try:
        db = get_db()
        db.add_feedback(
            detection_id=feedback.detection_id,
            predicted_class=feedback.predicted_class,
            correct_class=feedback.correct_class,
            user_comment=feedback.comment
        )

        return {
            "status": "success",
            "message": "Thank you! AI is now smarter 🧠",
            "feedback_stored": True,
            "detection_id": feedback.detection_id,
            "ai_learned": f"Class '{feedback.correct_class}' accuracy will improve"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback error: {str(e)}")


@app.post("/feedback/verify")
def verify_feedback(feedback: VerifyFeedbackRequest):
    """Binary Feedback: stimmt / stimmt nicht mit automatischer Lernspeicherung."""
    import base64
    from datetime import datetime

    from learning_db import get_db
    from sample_memory import save_feedback_sample

    try:
        # Support both formats: feedback_type (from Dashboard) and stimmt (legacy)
        is_correct = None
        if feedback.feedback_type:
            is_correct = feedback.feedback_type == 'stimmt'
        elif feedback.stimmt is not None:
            is_correct = feedback.stimmt
        else:
            raise ValueError("Either feedback_type or stimmt required")

        db = get_db()
        result = db.add_binary_feedback(
            detection_id=feedback.detection_id,
            is_correct=is_correct,
            correct_class=feedback.correct_class,
            user_comment=feedback.comment,
        )

        detection = result["detection"]
        predicted_class = result["predicted_class"]
        correct_class = result["correct_class"]
        is_correct = result["is_correct"]

        image_hash = detection.get("image_hash")
        memory_paths = None

        # If image_base64 provided, save it (from Dashboard)
        if feedback.image_base64:
            import hashlib
            from pathlib import Path

            image_data = base64.b64decode(feedback.image_base64.split(',')[-1])
            image_hash = hashlib.sha256(image_data).hexdigest()

            # Save to verified storage
            class_folder = correct_class or predicted_class
            sample_dir = Path(__file__).parent / "sample_memory" / "verified" / class_folder
            sample_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = sample_dir / f"{timestamp}_{detection.get('detection_id', 'unknown')}.jpg"
            image_path.write_bytes(image_data)
            memory_paths = {"image": str(image_path)}

        elif image_hash:
            memory_paths = save_feedback_sample(
                image_hash=image_hash,
                detection_id=feedback.detection_id,
                predicted_class=predicted_class,
                correct_class=correct_class,
                is_correct=is_correct,
                comment=feedback.comment,
            )

        return {
            "status": "success",
            "feedback_type": "stimmt" if is_correct else "stimmt_nicht",
            "detection_id": feedback.detection_id,
            "predicted_class": predicted_class,
            "correct_class": correct_class,
            "ai_learning": {
                "updated": True,
                "from_existing_files": bool(image_hash),
                "memory_saved": memory_paths is not None,
            },
            "memory_paths": memory_paths,
            "message": "Feedback gespeichert. KI lernt jetzt aus bisherigen + neuen Müllbeispielen."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verify feedback error: {str(e)}")

@app.get("/learning/stats")
def get_learning_statistics():
    """View AI learning progress and statistics"""
    from learning_db import get_db

    db = get_db()
    stats = db.get_learning_stats()

    return {
        "status": "success",
        "statistics": stats,
        "interpretation": {
            "learning_rate": f"{stats['learning_rate']:.1%} of detections have feedback",
            "accuracy": f"{stats['average_accuracy']:.1%} average accuracy",
            "experience": f"{stats['total_detections']} total detections analyzed"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/learning/class/{class_name}")
def get_class_accuracy(class_name: str):
    """View accuracy and learning for specific object class"""
    from learning_db import get_db

    db = get_db()
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT accuracy_rate, total_samples, last_updated
        FROM confidence_calibration
        WHERE class_name = ?
    """, (class_name,))
    row = cursor.fetchone()

    if not row:
        return {
            "status": "no_data",
            "class_name": class_name,
            "message": "No learning data yet for this class"
        }

    return {
        "status": "success",
        "class_name": class_name,
        "accuracy_rate": row[0],
        "total_samples": row[1],
        "last_updated": row[2],
        "interpretation": f"AI is {row[0]:.1%} accurate for '{class_name}' based on {row[1]} samples"
    }

@app.get("/learning/priorities")
def get_learning_priorities(limit: int = 5):
    """Top Klassen, bei denen Nutzer-Feedback den größten Qualitätsgewinn bringt."""
    from learning_db import get_db

    db = get_db()
    priorities = db.get_priority_feedback_classes(limit=max(1, min(limit, 20)))
    return {
        "status": "success",
        "priorities": priorities,
        "message": "Diese Klassen zuerst korrigieren, um die KI am schnellsten zu verbessern"
    }


@app.get("/learning/review-queue")
def get_learning_review_queue(limit: int = 25):
    """Offene MANUAL_CHECK_REQUIRED Fälle ohne Feedback (active learning queue)."""
    from learning_db import get_db

    db = get_db()
    queue = db.get_pending_review_cases(limit=max(1, min(limit, 200)))
    return {
        "status": "success",
        "count": len(queue),
        "queue": queue,
        "message": "Diese Fälle zuerst verifizieren für maximale Qualitätssteigerung"
    }


@app.get("/learning/memory")
def get_learning_memory_stats():
    """Statistiken über gespeicherte Mülldateien und verifizierte Lernbeispiele."""
    from sample_memory import get_memory_stats

    stats = get_memory_stats()
    return {
        "status": "success",
        "memory": stats,
        "message": "Bisherige + neue Mülldateien werden für kontinuierliches Lernen gespeichert"
    }


@app.post("/learning/export-dataset")
def export_learning_dataset(train_ratio: float = 0.8):
    """Exportiert verifizierte Daten als YOLO-kompatibles Trainingsdataset."""
    from sample_memory import export_training_dataset

    result = export_training_dataset(train_ratio=train_ratio)
    return {
        "status": "success",
        "dataset": result,
        "message": "Dataset exportiert. Kann direkt für Retraining genutzt werden."
    }


@app.post("/learning/self-improvement/run")
def run_self_improvement_cycle(max_terms: int = 220):
    """Startet einen expliziten Selbstverbesserungs-Lauf (lokal zuerst, dann online-validiert)."""
    from learning_db import get_db
    from web_knowledge import get_fetcher

    db = get_db()
    fetcher = get_fetcher()

    report = fetcher.auto_self_learn_on_recognition_issue(
        db=db,
        trigger_objects=fetcher.ONLINE_SELF_LEARN_PRIORITY_TERMS,
        include_priority_terms=True,
        max_terms=max(40, min(int(max_terms), 1200)),
        force=True,
    )

    db.add_self_improvement_run(
        event_type="manual_trigger",
        status=str(report.get("status", "unknown")),
        report=report,
    )

    return {
        "status": "success",
        "mode": "local_first_then_online_validated",
        "report": report,
        "message": "Selbstverbesserung ausgeführt: Lokales Wissen priorisiert, Online-Wissen nur nach Qualitätsprüfung übernommen"
    }


@app.get("/learning/self-improvement/status")
def get_self_improvement_status(limit: int = 25):
    """Zeigt persistente Selbstverbesserungs-Kennzahlen und letzte Läufe."""
    from learning_db import get_db

    db = get_db()
    summary = db.get_self_improvement_summary()
    recent_runs = db.get_recent_self_improvement_runs(limit=max(1, min(limit, 200)))

    return {
        "status": "success",
        "summary": summary,
        "recent_runs": recent_runs,
        "policy": {
            "local_first": True,
            "online_fetch_when_needed": True,
            "online_requires_validation": True,
            "persistent_learning": True,
        },
    }


@app.get("/learning/online-selfcheck")
def get_online_learning_selfcheck(force_refresh: bool = False):
    """Prüft, ob Online-Wissenspfad und Selbstlernen funktionsfähig sind."""
    from learning_db import get_db
    from safety_config import get_config
    from web_knowledge import get_fetcher

    cfg = get_config()
    db = get_db()
    fetcher = get_fetcher()

    internet_ok = bool(fetcher.has_internet_connection(force_refresh=bool(force_refresh)))
    summary = db.get_self_improvement_summary()
    last_runs = db.get_recent_self_improvement_runs(limit=5)

    online_activity = int(summary.get("total_live_enriched_terms", 0))
    accepted_online = int(summary.get("total_accepted_online_terms", 0))

    overall_ok = bool(
        cfg.enable_web_knowledge
        and (
            internet_ok
            or online_activity > 0
            or accepted_online > 0
        )
    )

    return {
        "status": "success",
        "overall_ok": overall_ok,
        "checks": {
            "web_knowledge_enabled": bool(cfg.enable_web_knowledge),
            "internet_available": internet_ok,
            "self_improvement_runs": int(summary.get("total_runs", 0)),
            "live_enriched_terms": online_activity,
            "accepted_online_terms": accepted_online,
        },
        "policy": {
            "local_first": True,
            "online_requires_validation": True,
            "strict_safety": bool(cfg.hard_safety_mode),
        },
        "recent_runs": last_runs,
        "message": (
            "Online-Selbstlernen ist aktiv und überprüfbar"
            if overall_ok else
            "Online-Selbstlernen aktuell eingeschränkt (Internet/Web-Feature prüfen)"
        )
    }


@app.get("/learning/recommendations")
def get_learning_recommendations():
    """Gibt datengetriebene Empfehlungen für die nächste Qualitätsverbesserung."""
    from learning_db import get_db
    from sample_memory import build_improvement_recommendations

    db = get_db()
    report = build_improvement_recommendations(db)
    return {
        "status": "success",
        "report": report,
        "message": "Optimierungsvorschläge basieren auf echten Produktionsdaten"
    }


@app.get("/learning/focus")
def get_learning_focus(limit: int = 5):
    """Liefert aktuelle Lernziel-Klassen inkl. Confidence-Gate-Kontext."""
    from learning_db import get_db

    db = get_db()
    priorities = db.get_priority_feedback_classes(limit=max(1, min(int(limit), 20)))
    review_queue = db.get_pending_review_cases(limit=200)
    trend = db.get_recent_feedback_error_rates(window=80)

    top_priority = priorities[0] if priorities else None

    return {
        "status": "success",
        "focus_gate": {
            "enabled": True,
            "min_confidence_for_focus_auto": 0.72,
            "rule": "focus_class_and_low_confidence_requires_manual_review",
        },
        "top_priority": top_priority,
        "priorities": priorities,
        "review_queue_count": len(review_queue),
        "error_trend": trend,
        "message": "Diese Klassen zuerst korrigieren für maximale Genauigkeitssteigerung"
    }


@app.post("/learning/knowledge/import")
def import_public_knowledge(max_terms: int = 80, allow_live_fetch: bool = False):
    """Importiert öffentliches Seed-Wissen zur Verbesserung der Hint-Abdeckung ohne Retraining."""
    from learning_db import get_db
    from web_knowledge import get_fetcher

    db = get_db()
    fetcher = get_fetcher()
    result = fetcher.import_public_knowledge_seeds(
        db=db,
        max_terms=max(1, min(max_terms, 400)),
        allow_live_fetch=bool(allow_live_fetch),
    )
    return {
        "status": "success",
        "result": result,
        "message": "Seed-Wissen importiert und für spätere Entscheidungen verfügbar"
    }


@app.post("/learning/dataset/import-all")
def import_all_public_datasets(max_objects: int = 1500, allow_live_fetch: bool = False):
    """
    🚀 MASSIVE DATABASE EXPANSION: Importiert möglichst viele gratis Objekte ohne Training!

    Datensätze (alle CC-BY 4.0 oder kompatibel, kommerziell nutzbar):
    - COCO 2014: 80 base classes
    - TACO: 60 Trash Annotation Categories
    - Open Images V7: 55+ material classes
    - Roboflow Waste Detection: 31 spezialisierte Klassen
    - Wikidata: 35+ Abfall-Kategorien

    Gesamt: 1000+ eindeutige Objekte (je nach Quelle/Version + Varianten) für optimierte Inferenz

    Query Parameter:
    - max_objects: Limit (default 1500, max 5000)
    - allow_live_fetch: Wikipedia-API für Material-Eigenschaften aktivieren (rate-limited)
    """
    from learning_db import get_db

    try:
        from web_knowledge_enhanced import get_fetcher as get_enhanced_fetcher
        db = get_db()
        fetcher = get_enhanced_fetcher()

        result = fetcher.import_all_datasets_to_db(
            db=db,
            max_objects=max(1, min(int(max_objects), 5000))
        )

        return {
            "status": "success",
            "import_result": result,
            "message": f"✓ {result.get('indexed_objects', 0)} neue Objekte importiert aus {len(result.get('datasets_included', []))} Gratis-Datensätzen",
            "datasets": result.get("datasets_included", []),
            "total_coverage": f"{result.get('total_unique_objects', 0)} eindeutige Objekte für Klassifikation",
            "next_steps": [
                "POST /learning/knowledge/import für erweiterte Ontologie-Synonyme",
                "POST /detect um neue Datensätze live zu testen",
                "GET /learning/recommendations für optimale nächste Schritte"
            ]
        }
    except ImportError:
        return {
            "status": "error",
            "message": "web_knowledge_enhanced.py nicht gefunden. Stelle sicher dass alle Module installiert sind.",
            "fallback": "Nutze POST /learning/knowledge/import als Alternative"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dataset import error: {str(e)}")


@app.get("/learning/dataset/info")
def get_dataset_info():
    """Info über verfügbare öffentliche Datensätze und ihre Lizenzierung"""
    try:
        from web_knowledge_enhanced import get_fetcher as get_enhanced_fetcher
        fetcher = get_enhanced_fetcher()
        all_seeds = fetcher.get_all_public_knowledge_seeds()

        return {
            "status": "success",
            "available_datasets": {
                "COCO": {
                    "classes": 80,
                    "license": "CC-BY 4.0",
                    "source": "Common Objects in Context",
                    "commercial_use": True
                },
                "TACO": {
                    "classes": 60,
                    "license": "Harvard Dataverse",
                    "source": "Trash Annotation Dataset",
                    "commercial_use": True
                },
                "Open Images": {
                    "classes": 55,
                    "license": "CC-BY 4.0",
                    "source": "Google Open Images Extended",
                    "commercial_use": True
                },
                "Roboflow Waste": {
                    "classes": 31,
                    "license": "Various (CC-BY-SA compatible)",
                    "source": "Roboflow Waste Detection",
                    "commercial_use": True
                },
                "Wikidata": {
                    "classes": 35,
                    "license": "CC0 (Public Domain)",
                    "source": "Structured Waste Categories",
                    "commercial_use": True
                },
                "Open Food Facts": {
                    "classes": 40,
                    "license": "ODbL",
                    "source": "Open product packaging taxonomy",
                    "commercial_use": True
                },
                "OpenStreetMap Tags": {
                    "classes": 25,
                    "license": "ODbL",
                    "source": "Recycling and waste object tags",
                    "commercial_use": True
                },
                "Wikimedia Commons": {
                    "classes": 40,
                    "license": "CC-BY-SA",
                    "source": "Object categories for consumer/electronic items",
                    "commercial_use": True
                },
                "Open Electronics Taxonomy": {
                    "classes": len(getattr(fetcher, "TECH_DEVICE_OBJECTS", [])),
                    "license": "Public/Free taxonomy terms",
                    "source": "Expanded technical device object vocabulary",
                    "commercial_use": True
                },
                "Bottle-Container Taxonomy": {
                    "classes": len(getattr(fetcher, "BOTTLE_CONTAINER_OBJECTS", [])),
                    "license": "Public/Free taxonomy terms",
                    "source": "Expanded bottle, jar, can and container vocabulary",
                    "commercial_use": True
                }
            },
            "total_unique_objects": len(all_seeds),
            "all_objects_sample": all_seeds[:50],
            "import_endpoint": "POST /learning/dataset/import-all"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Could not retrieve dataset info: {str(e)}"
        }


@app.get("/learning/threshold/{class_name}")
def get_class_output_threshold(class_name: str):
    """Zeigt die aktuell adaptive Ausgabeschwelle für eine Klasse."""
    from learning_db import get_db

    db = get_db()
    threshold = db.get_class_output_threshold(class_name, default_threshold=0.40)
    return {
        "status": "success",
        "class_name": class_name,
        "output_threshold": threshold,
        "message": "Schwelle steigt bei schlechter Historie und sinkt bei stabiler hoher Qualität"
    }


@app.get("/learning/risky-classes")
def get_learning_risky_classes(min_wrong_rate: float = 0.30, min_samples: int = 6, limit: int = 40):
    """Zeigt Klassen mit hoher Fehlerrate für strengere Laufzeitbehandlung."""
    from learning_db import get_db

    db = get_db()
    risky = db.get_risky_classes_from_feedback(
        min_wrong_rate=max(0.05, min(min_wrong_rate, 0.95)),
        min_samples=max(1, min(min_samples, 200)),
        limit=max(1, min(limit, 200)),
    )
    return {
        "status": "success",
        "count": len(risky),
        "risky_classes": risky,
        "message": "Diese Klassen werden in der Inferenz konservativer gefiltert"
    }

@app.get("/config/safety")
def get_safety_config():
    """Aktive Sicherheitskonfiguration (Hard Safety Mode)."""
    from safety_config import get_config
    cfg = get_config()
    return {
        "status": "success",
        "safety_config": cfg.as_dict(),
        "note": "Steuerbar über Umgebungsvariablen SMARTRASH_*"
    }


@app.get("/quality/control")
def get_quality_control_state():
    """Aktuelle adaptive Qualitäts-Policy (Fehlerquote-basiert)."""
    from quality_controller import get_quality_controller

    qc = get_quality_controller()
    policy = qc.get_adaptive_policy()
    return {
        "status": "success",
        "policy": policy,
        "message": "Policy wird automatisch angepasst, um Fehlerquote zu senken"
    }


@app.get("/quality/error-trend")
def get_quality_error_trend(window: int = 80):
    """Fehlertrend aus den letzten Feedbacks."""
    from learning_db import get_db

    db = get_db()
    trend = db.get_recent_feedback_error_rates(window=max(10, min(window, 500)))
    return {
        "status": "success",
        "trend": trend,
        "target": {
            "recent_error_rate_goal": "< 0.10",
            "trend_goal": "improving"
        }
    }


@app.get("/compliance/no-cost")
def get_no_cost_status():
    """Prüft, ob versteckte Kostenquellen deaktiviert sind."""
    from compliance_guard import check_no_cost_policy

    report = check_no_cost_policy()
    return {
        "status": "success",
        "no_cost": report,
        "message": "No-Cost-Guard prüft Pakete, Konfiguration und API-Key-Umgebung"
    }


@app.get("/compliance/report")
def get_compliance_report():
    """Gesamtreport für Kosten- und Datenschutz-Compliance."""
    from compliance_guard import build_compliance_report

    report = build_compliance_report()
    return {
        "status": "success",
        "report": report,
        "message": "Compliance-Report basiert auf lokalen, kostenlosen Checks"
    }


@app.post("/compliance/cleanup-data")
def cleanup_compliance_data():
    """Führt Retention-Cleanup für gespeicherte Lerndateien durch."""
    from safety_config import get_config
    from sample_memory import cleanup_old_memory_files

    cfg = get_config()
    result = cleanup_old_memory_files(retention_days=cfg.data_retention_days)
    return {
        "status": "success",
        "cleanup": result,
        "message": "Retention-Policy angewendet"
    }

@app.get("/audit/recent")
def get_recent_audit_logs(limit: int = 50):
    """Zeigt die letzten Sicherheitsentscheidungen für Nachvollziehbarkeit."""
    from learning_db import get_db

    db = get_db()
    entries = db.get_recent_audits(limit=limit)
    return {
        "status": "success",
        "count": len(entries),
        "entries": entries
    }

@app.get("/system/audit")
def run_system_audit():
    """Selbstprüfung: passt Konfiguration, Datenqualität und Sicherheitsmodus?"""
    from compliance_guard import build_compliance_report
    from learning_db import get_db
    from safety_config import get_config
    from waste_classifier import get_classifier

    db = get_db()
    cfg = get_config()
    classifier = get_classifier()
    compliance = build_compliance_report()

    checks = []
    issues = []

    checks.append({"name": "model_file", "ok": os.path.exists(model_path), "value": model_path})

    thresholds_ok = (
        0.0 <= cfg.min_decision_quality_for_autosort <= 1.0
        and 0.0 <= cfg.min_confidence_for_autosort <= 1.0
    )
    checks.append({
        "name": "threshold_ranges",
        "ok": thresholds_ok,
        "value": {
            "min_quality": cfg.min_decision_quality_for_autosort,
            "min_confidence": cfg.min_confidence_for_autosort
        }
    })
    if not thresholds_ok:
        issues.append("invalid_threshold_range")

    try:
        cursor = db.conn.cursor()
        cursor.execute("SELECT 1")
        db_ok = True
    except sqlite3.Error:
        db_ok = False
    checks.append({"name": "database_connection", "ok": db_ok})
    if not db_ok:
        issues.append("database_unavailable")

    stats = db.get_learning_stats()
    checks.append({"name": "feedback_rate", "ok": stats.get("learning_rate", 0.0) >= 0.05, "value": stats.get("learning_rate", 0.0)})
    checks.append({"name": "hard_safety", "ok": cfg.hard_safety_mode, "value": cfg.hard_safety_mode})
    checks.append({"name": "ultra_strict", "ok": cfg.ultra_strict_mode, "value": cfg.ultra_strict_mode})
    checks.append({"name": "audit_logging", "ok": cfg.enable_audit_logging, "value": cfg.enable_audit_logging})
    checks.append({"name": "no_cost_mode", "ok": compliance.get("details", {}).get("no_cost", {}).get("ok", False), "value": cfg.no_cost_mode})
    checks.append({"name": "privacy_policy", "ok": compliance.get("details", {}).get("privacy", {}).get("ok", False), "value": cfg.store_images_with_person})

    mapping_summary = classifier.get_bin_summary()
    mapped_classes = mapping_summary.get("total_classes_mapped", 0)
    mapping_ok = mapped_classes >= 45
    checks.append({"name": "mapping_coverage", "ok": mapping_ok, "value": mapped_classes})
    if not mapping_ok:
        issues.append("low_mapping_coverage")

    if not os.path.exists(model_path):
        issues.append("model_missing")
    if stats.get("learning_rate", 0.0) < 0.05:
        issues.append("collect_more_feedback")
    if not compliance.get("compliant", False):
        issues.extend(compliance.get("issues", []))

    ok_checks = sum(1 for c in checks if c.get("ok"))
    score = ok_checks / max(len(checks), 1)

    return {
        "status": "success",
        "audit_score": score,
        "ready_for_production": score >= 0.85 and "model_missing" not in issues and compliance.get("compliant", False),
        "checks": checks,
        "issues": sorted(list(set(issues))),
        "compliance": compliance,
        "recommendations": [
            "Model-Datei bereitstellen (YOLOX_CKPT)",
            "Mehr Feedback über /feedback sammeln",
            "Unsichere Fälle mit MANUAL_CHECK_REQUIRED bestätigen",
            "/learning/priorities nutzen für schnellere Qualitätsverbesserung",
            "No-Cost-Mode aktiv halten und keine bezahlten APIs freischalten",
            "Retention-Cleanup regelmäßig ausführen (/compliance/cleanup-data)"
        ]
    }

@app.get("/waste/bins")
def get_waste_bins_info():
    """Get information about all 4 waste bins and classification rules"""
    from waste_classifier import get_classifier

    classifier = get_classifier()
    summary = classifier.get_bin_summary()

    return {
        "status": "success",
        "bins": summary["bins"],
        "total_classes_mapped": summary["total_classes_mapped"],
        "materials": summary["materials"],
        "battery_warning_devices": summary["battery_warning_classes"],
        "rules": {
            "PLASTIK": {
                "description": "Gelbe Tonne / Wertstofftonne",
                "accepts": ["Plastikflaschen", "Verpackungen", "Kunststoff-Behälter"],
                "rejects": ["Stark verschmutzte Verpackungen", "Nicht-Verpackungen"]
            },
            "PAPIER": {
                "description": "Blaue Tonne / Papiertonne",
                "accepts": ["Karton", "Papier", "Pappe"],
                "rejects": ["Nasses Papier", "Verschmutztes Papier", "Beschichtetes Papier"]
            },
            "BIOMÜLL": {
                "description": "Braune Tonne / Biotonne",
                "accepts": ["Essensreste", "Obst", "Gemüse", "Organisches Material"],
                "rejects": ["Verpackungen", "Plastik", "Gekochtes Fleisch (je nach Region)"]
            },
            "RESTMÜLL": {
                "description": "Schwarze Tonne / Restmülltonne",
                "accepts": ["Alles was nicht recyclebar ist", "Verschmutzte Materialien"],
                "note": "Elektronik, Batterien, Glas haben Sonderentsorgung!"
            }
        },
        "special_disposal": {
            "elektronik": "Wertstoffhof / Elektroschrott-Sammlung",
            "batterien": "Sammelstellen in Supermärkten / Wertstoffhof",
            "glas": "Altglascontainer (nach Farbe sortiert)",
            "sperrmüll": "Anmeldung bei Gemeinde erforderlich"
        },
        "tips": [
            "🔋 Batterien IMMER separat entsorgen!",
            "💧 Nasses Papier gehört in Restmüll",
            "🧼 Verpackungen ausspülen für Recycling",
            "🍌 Bioabfall ohne Verpackung in Biotonne",
            "♻️ Im Zweifelsfall → Restmüll"
        ]
    }


@app.get("/waste/quality-check")
def run_waste_quality_check():
    """Deterministische Selbstprüfung der Tonnentrennung inkl. Batterie-Hinweise."""
    from waste_classifier import get_classifier

    classifier = get_classifier()

    cases = [
        {"class": "bottle", "conf": 0.92, "expected_bin": "PLASTIK", "expect_battery_warning": False},
        {"class": "book", "conf": 0.90, "expected_bin": "PAPIER", "expect_battery_warning": False},
        {"class": "banana", "conf": 0.96, "expected_bin": "BIOMÜLL", "expect_battery_warning": False},
        {"class": "cell phone", "conf": 0.94, "expected_bin": "RESTMÜLL", "expect_battery_warning": True},
        {"class": "laptop", "conf": 0.93, "expected_bin": "RESTMÜLL", "expect_battery_warning": True},
        {"class": "remote", "conf": 0.91, "expected_bin": "RESTMÜLL", "expect_battery_warning": True},
        {"class": "tv", "conf": 0.89, "expected_bin": "RESTMÜLL", "expect_battery_warning": True},
    ]

    details = []
    passed = 0

    for case in cases:
        result = classifier.classify_waste(
            class_name=case["class"],
            confidence=case["conf"],
            object_condition=None,
        )
        warnings = result.get("warnings", []) or []
        has_battery_warning = any(
            ("BATTERIE" in str(w))
            or ("Akku" in str(w))
            or ("akku" in str(w))
            or ("könnte Akku/Batterien enthalten" in str(w))
            for w in warnings
        )

        bin_ok = str(result.get("bin", "")).upper() == case["expected_bin"]
        battery_ok = (has_battery_warning == bool(case["expect_battery_warning"]))
        ok = bool(bin_ok and battery_ok)
        if ok:
            passed += 1

        details.append({
            "class": case["class"],
            "expected_bin": case["expected_bin"],
            "actual_bin": result.get("bin"),
            "expect_battery_warning": case["expect_battery_warning"],
            "actual_battery_warning": has_battery_warning,
            "ok": ok,
            "warnings": warnings,
        })

    total = len(cases)
    score = passed / max(total, 1)

    return {
        "status": "success",
        "score": score,
        "passed": passed,
        "total": total,
        "perfect": passed == total,
        "details": details,
        "message": "Tonnentrennung und Batterie-Hinweise geprüft"
    }

@app.get("/learning/dashboard")
def get_learning_dashboard():
    """Complete Performance Dashboard - See how AI improves over time"""
    from performance_tracker import get_tracker

    try:
        tracker = get_tracker()
        dashboard = tracker.get_learning_dashboard()

        return {
            "status": "success",
            "dashboard": dashboard,
            "summary": {
                "is_learning": dashboard["overall_stats"]["learning_rate"] > 0,
                "total_detections": dashboard["overall_stats"]["total_detections"],
                "total_feedback": dashboard["overall_stats"]["total_feedback"],
                "avg_accuracy": dashboard["overall_stats"]["average_accuracy"],
                "best_class": dashboard["best_performing_classes"][0] if dashboard["best_performing_classes"] else None,
                "needs_focus": dashboard["needs_improvement"][0] if dashboard["needs_improvement"] else None
            },
            "message": "🧠 AI is continuously learning and improving",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "insufficient_data",
            "message": "Not enough data yet. Start using the system and provide feedback!",
            "error": str(e)
        }


@app.get("/benchmark/quality")
def get_benchmark_quality():
    """Messbarer Überblick, wie nah das System an einem reifen Produkt ist."""
    from performance_tracker import get_tracker
    from recognition_profile import load_recognition_profile

    try:
        tracker = get_tracker()
        profile = load_recognition_profile()
        summary = tracker.get_benchmark_summary(recognition_profile=profile)
        return {
            "status": "success",
            "benchmark": summary,
            "message": "Messbarer Qualitätsüberblick für das aktuelle YOLOX-Profil"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "Benchmark konnte nicht berechnet werden",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn

    def _find_available_port(start_port=8000, max_tries=30):
        for p in range(start_port, start_port + max_tries):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if s.connect_ex(("127.0.0.1", p)) != 0:
                    return p
        return start_port

    requested_port = int(os.environ.get("APP_PORT", "8000"))
    run_port = _find_available_port(requested_port)

    print("\n" + "="*70)
    print("♻️  SmarTrash AI - Intelligente Mülltrennung System")
    print("="*70)
    print(f"📁 Model path: {model_path}")
    print(f"✓ Model exists: {os.path.exists(model_path)}")
    print(f"🖥️  Device: {os.environ.get('YOLOX_DEVICE', 'cpu')}")
    print("\n🗑️  Mülltonnen (4 Kategorien):")
    print("  • RESTMÜLL - Schwarze Tonne")
    print("  • BIOMÜLL - Braune Tonne")
    print("  • PAPIER - Blaue Tonne")
    print("  • PLASTIK - Gelbe Tonne / Wertstofftonne")
    print("\n🎯 KI Features:")
    print("  • Waste Sorting (Automatische Mülltrennung)")
    print("  • Material Detection (Plastik, Papier, Bio, etc.)")
    print("  • 🔋 Battery Warning (für Elektronik mit Batterien)")
    print("  • Condition Analysis (Nässe, Verschmutzung)")
    print("  • Test-Time Augmentation (TTA)")
    print("  • Multi-Scale Testing")
    print("  • Advanced NMS")
    print("  • Self-Learning from Feedback")
    print("  • Confidence Calibration")
    print("  • Persistent Memory (SQLite)")
    print("  • Web Knowledge (Wikipedia)")
    print("\n🌐 Endpoints:")
    print(f"  • 📊 DASHBOARD: http://localhost:{run_port}/dashboard  ⭐ START HERE!")
    print(f"  • API: http://localhost:{run_port}")
    print(f"  • Docs: http://localhost:{run_port}/docs")
    print(f"  • Health: http://localhost:{run_port}/health")
    print(f"  • Waste Bins Info: http://localhost:{run_port}/waste/bins")
    print(f"  • Learning Stats: http://localhost:{run_port}/learning/stats")
    print(f"  • Verify Feedback: http://localhost:{run_port}/feedback/verify")
    print(f"  • Learning Memory: http://localhost:{run_port}/learning/memory")
    print(f"  • Review Queue: http://localhost:{run_port}/learning/review-queue")
    print(f"  • Export Dataset: http://localhost:{run_port}/learning/export-dataset")
    print(f"  • Recommendations: http://localhost:{run_port}/learning/recommendations")
    print(f"  • Performance Dashboard: http://localhost:{run_port}/learning/dashboard")
    print(f"  • Learning Priorities: http://localhost:{run_port}/learning/priorities")
    print(f"  • Safety Config: http://localhost:{run_port}/config/safety")
    print(f"  • No-Cost Status: http://localhost:{run_port}/compliance/no-cost")
    print(f"  • Compliance Report: http://localhost:{run_port}/compliance/report")
    print(f"  • Data Cleanup: http://localhost:{run_port}/compliance/cleanup-data")
    print(f"  • Recent Audit Logs: http://localhost:{run_port}/audit/recent")
    print(f"  • System Audit: http://localhost:{run_port}/system/audit")
    print("\n⚠️  WICHTIG:")
    print("  • System erkennt 80 COCO Objekt-Klassen")
    print("  • Berücksichtigt Material + Zustand für Trennung")
    print("  • 🔋 Warnt automatisch bei Batterien/Akkus")
    print("  • Lernt mit jedem Feedback besser!")
    if run_port != requested_port:
        print(f"  • ⚠️ Port {requested_port} war belegt → nutze automatisch {run_port}")
    print("="*70 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=run_port, log_level="info")
