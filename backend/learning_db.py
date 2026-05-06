"""
Learning Database - Persistentes Gedächtnis für die KI
======================================================
Speichert alle Erkennungen, Feedback und lernt kontinuierlich.
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "smartrash_learning.db"


class LearningDatabase:
    """Persistente Datenbank für Self-Learning"""

    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._init_db()

    def _init_db(self):
        """Erstelle Tabellen"""
        cursor = self.conn.cursor()

        # Erkennungs-Historie
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                original_class TEXT NOT NULL,
                predicted_class TEXT NOT NULL,
                confidence REAL NOT NULL,
                bbox TEXT NOT NULL,
                image_hash TEXT,
                details TEXT
            )
        """)

        # User Feedback (Menschen korrigieren KI)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detection_id INTEGER,
                timestamp TEXT NOT NULL,
                predicted_class TEXT NOT NULL,
                correct_class TEXT NOT NULL,
                user_comment TEXT,
                FOREIGN KEY (detection_id) REFERENCES detections(id)
            )
        """)

        # Confidence-Kalibrierung pro Klasse
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS confidence_calibration (
                class_name TEXT PRIMARY KEY,
                avg_confidence REAL,
                accuracy_rate REAL,
                total_samples INTEGER,
                last_updated TEXT
            )
        """)

        # Aggregiertes Klassenwissen für kontinuierliches Lernen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS class_knowledge_profile (
                class_name TEXT PRIMARY KEY,
                seen_count INTEGER NOT NULL DEFAULT 0,
                avg_confidence REAL NOT NULL DEFAULT 0.0,
                best_confidence REAL NOT NULL DEFAULT 0.0,
                last_seen TEXT
            )
        """)

        # Objekt-Zustandsdetails (Dreck, Beschädigungen, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS object_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detection_id INTEGER,
                condition_type TEXT NOT NULL,
                severity REAL,
                description TEXT,
                FOREIGN KEY (detection_id) REFERENCES detections(id)
            )
        """)

        # Web-Wissen Cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS web_knowledge (
                object_name TEXT PRIMARY KEY,
                description TEXT,
                properties TEXT,
                source TEXT,
                fetched_at TEXT
            )
        """)

        # Objektwissen-Index (material/bin/Quelle) für maximale Wiederverwendung
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS object_knowledge_index (
                object_name TEXT PRIMARY KEY,
                inferred_material TEXT,
                inferred_bin TEXT,
                confidence REAL,
                source TEXT,
                last_updated TEXT,
                notes TEXT
            )
        """)

        # Audit-Log für Sicherheitsentscheidungen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                detection_id INTEGER,
                class_name TEXT NOT NULL,
                action TEXT NOT NULL,
                recommended_bin TEXT,
                safe_fallback_bin TEXT,
                decision_quality REAL,
                requires_manual_review INTEGER,
                review_reasons TEXT,
                battery_warning INTEGER,
                FOREIGN KEY (detection_id) REFERENCES detections(id)
            )
        """)

        # Persistentes Protokoll für automatische Selbstverbesserung
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS self_improvement_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                local_seed_terms INTEGER DEFAULT 0,
                local_indexed_objects INTEGER DEFAULT 0,
                live_enriched_terms INTEGER DEFAULT 0,
                internet_available INTEGER DEFAULT 0,
                trigger_terms_used INTEGER DEFAULT 0,
                accepted_online_terms INTEGER DEFAULT 0,
                details TEXT
            )
        """)

        # Manuelle Annotations für nicht erkannte Objekte (Training-Daten)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manual_annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                image_hash TEXT,
                bbox TEXT NOT NULL,
                object_class TEXT NOT NULL,
                frame_saved INTEGER DEFAULT 0,
                frame_path TEXT,
                suggested_bin TEXT,
                user_confirmed INTEGER DEFAULT 0,
                comment TEXT
            )
        """)

        # Performance-Indizes für häufige Queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_predicted_class ON feedback(predicted_class)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_correct_class ON feedback(correct_class)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_detection_id ON feedback(detection_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_predicted_class ON detections(predicted_class)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_detection_id ON decisions_audit(detection_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_class_name ON decisions_audit(class_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_object_knowledge_source ON object_knowledge_index(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_self_improvement_timestamp ON self_improvement_runs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manual_annotations_timestamp ON manual_annotations(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manual_annotations_class ON manual_annotations(object_class)")

        self.conn.commit()

    def add_detection(self, predicted_class, confidence, bbox, details=None, image_hash=None):
        """Speichere neue Erkennung"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO detections (timestamp, original_class, predicted_class, confidence, bbox, image_hash, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), predicted_class, predicted_class, confidence,
              json.dumps(bbox), image_hash, json.dumps(details) if details else None))
        self._update_class_knowledge_profile(predicted_class, confidence)
        self.conn.commit()
        return cursor.lastrowid

    def _update_class_knowledge_profile(self, class_name, confidence):
        """Aggregiere Wissen pro Klasse: Häufigkeit, mittlere/beste Confidence."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT seen_count, avg_confidence, best_confidence
            FROM class_knowledge_profile
            WHERE class_name = ?
            """,
            (class_name,)
        )
        row = cursor.fetchone()
        now = datetime.now().isoformat()
        conf = float(confidence or 0.0)

        if row:
            seen_count = int(row[0] or 0)
            avg_conf = float(row[1] or 0.0)
            best_conf = float(row[2] or 0.0)
            new_count = seen_count + 1
            new_avg = ((avg_conf * seen_count) + conf) / max(new_count, 1)
            new_best = max(best_conf, conf)
            cursor.execute(
                """
                UPDATE class_knowledge_profile
                SET seen_count = ?, avg_confidence = ?, best_confidence = ?, last_seen = ?
                WHERE class_name = ?
                """,
                (new_count, new_avg, new_best, now, class_name)
            )
        else:
            cursor.execute(
                """
                INSERT INTO class_knowledge_profile (class_name, seen_count, avg_confidence, best_confidence, last_seen)
                VALUES (?, ?, ?, ?, ?)
                """,
                (class_name, 1, conf, conf, now)
            )

    def add_feedback(self, detection_id, predicted_class, correct_class, user_comment=None):
        """User korrigiert KI - wichtigster Lernmechanismus!"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO feedback (detection_id, timestamp, predicted_class, correct_class, user_comment)
            VALUES (?, ?, ?, ?, ?)
        """, (detection_id, datetime.now().isoformat(), predicted_class, correct_class, user_comment))
        self.conn.commit()

        # Update Confidence-Kalibrierung
        self._update_calibration(predicted_class, correct_class == predicted_class)
        if correct_class != predicted_class:
            # Positives Signal für die richtige Klasse
            self._update_calibration(correct_class, True)

    def get_detection(self, detection_id):
        """Hole Detection-Datensatz nach ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, original_class, predicted_class, confidence, bbox, image_hash, details
            FROM detections
            WHERE id = ?
            """,
            (detection_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "timestamp": row[1],
            "original_class": row[2],
            "predicted_class": row[3],
            "confidence": row[4],
            "bbox": json.loads(row[5]) if row[5] else None,
            "image_hash": row[6],
            "details": json.loads(row[7]) if row[7] else None,
        }

    def add_binary_feedback(self, detection_id, is_correct, correct_class=None, user_comment=None):
        """Feedback mit 'stimmt' / 'stimmt nicht'."""
        detection = self.get_detection(detection_id)
        if not detection:
            raise ValueError(f"Detection {detection_id} not found")

        predicted_class = detection["predicted_class"]
        final_correct_class = predicted_class if is_correct else (correct_class or predicted_class)

        self.add_feedback(
            detection_id=detection_id,
            predicted_class=predicted_class,
            correct_class=final_correct_class,
            user_comment=user_comment,
        )

        return {
            "detection": detection,
            "predicted_class": predicted_class,
            "correct_class": final_correct_class,
            "is_correct": bool(is_correct),
        }

    def get_pending_review_cases(self, limit=50):
        """Fälle mit MANUAL_CHECK_REQUIRED ohne abgeschlossenes Feedback."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                da.id,
                da.timestamp,
                da.detection_id,
                da.class_name,
                da.decision_quality,
                da.review_reasons,
                d.image_hash,
                d.bbox,
                d.confidence
            FROM decisions_audit da
            JOIN detections d ON d.id = da.detection_id
            LEFT JOIN feedback f ON f.detection_id = da.detection_id
            WHERE da.requires_manual_review = 1
              AND f.id IS NULL
            ORDER BY da.decision_quality ASC, da.id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 1000)),)
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "audit_id": row[0],
                "timestamp": row[1],
                "detection_id": row[2],
                "class_name": row[3],
                "decision_quality": float(row[4] or 0.0),
                "review_reasons": json.loads(row[5]) if row[5] else [],
                "image_hash": row[6],
                "bbox": json.loads(row[7]) if row[7] else None,
                "confidence": float(row[8] or 0.0)
            })
        return result

    def _update_calibration(self, class_name, was_correct):
        """Update Confidence-Kalibrierung basierend auf Feedback"""
        cursor = self.conn.cursor()

        # Hole aktuelle Stats
        cursor.execute("SELECT * FROM confidence_calibration WHERE class_name = ?", (class_name,))
        row = cursor.fetchone()

        if row:
            total = row[3] + 1
            correct = row[2] * row[3] + (1 if was_correct else 0)
            accuracy = correct / total

            cursor.execute("""
                UPDATE confidence_calibration
                SET accuracy_rate = ?, total_samples = ?, last_updated = ?
                WHERE class_name = ?
            """, (accuracy, total, datetime.now().isoformat(), class_name))
        else:
            cursor.execute("""
                INSERT INTO confidence_calibration (class_name, avg_confidence, accuracy_rate, total_samples, last_updated)
                VALUES (?, 0.5, ?, 1, ?)
            """, (class_name, 1.0 if was_correct else 0.0, datetime.now().isoformat()))

        self.conn.commit()

    def get_calibrated_confidence(self, class_name, raw_confidence):
        """Hole kalibrierte Confidence basierend auf historischer Accuracy"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT accuracy_rate FROM confidence_calibration WHERE class_name = ?", (class_name,))
        row = cursor.fetchone()

        if row and row[0] is not None:
            # Kombiniere Model-Confidence mit historischer Accuracy
            return (raw_confidence + row[0]) / 2.0
        return raw_confidence

    def get_class_reliability(self, class_name):
        """Gibt Verlässlichkeit für eine Klasse zurück (Accuracy + Datenmenge)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT accuracy_rate, total_samples FROM confidence_calibration WHERE class_name = ?",
            (class_name,)
        )
        row = cursor.fetchone()
        if not row:
            return {
                "accuracy_rate": 0.5,
                "total_samples": 0,
                "reliability": 0.2,
                "data_sufficient": False
            }

        accuracy_rate = float(row[0] or 0.0)
        total_samples = int(row[1] or 0)
        sample_factor = min(total_samples / 40.0, 1.0)
        reliability = accuracy_rate * sample_factor + 0.2 * (1.0 - sample_factor)

        return {
            "accuracy_rate": accuracy_rate,
            "total_samples": total_samples,
            "reliability": reliability,
            "data_sufficient": total_samples >= 8
        }

    def get_confusion_risk(self, class_name):
        """Misst wie oft eine Klasse falsch vorhergesagt wurde und wohin sie verwechselt wird."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM feedback
            WHERE predicted_class = ?
            """,
            (class_name,)
        )
        total = int(cursor.fetchone()[0] or 0)

        if total == 0:
            return {
                "total_feedback": 0,
                "wrong_rate": 0.0,
                "top_confusions": [],
                "risk_level": "unknown"
            }

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM feedback
            WHERE predicted_class = ? AND correct_class != predicted_class
            """,
            (class_name,)
        )
        wrong = int(cursor.fetchone()[0] or 0)
        wrong_rate = wrong / max(total, 1)

        cursor.execute(
            """
            SELECT correct_class, COUNT(*) AS cnt
            FROM feedback
            WHERE predicted_class = ? AND correct_class != predicted_class
            GROUP BY correct_class
            ORDER BY cnt DESC
            LIMIT 3
            """,
            (class_name,)
        )
        top_confusions = [{"correct_class": r[0], "count": int(r[1])} for r in cursor.fetchall()]

        if wrong_rate >= 0.5:
            risk_level = "high"
        elif wrong_rate >= 0.25:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "total_feedback": total,
            "wrong_rate": wrong_rate,
            "top_confusions": top_confusions,
            "risk_level": risk_level
        }

    def get_data_quality_guard(self, class_name, calibrated_confidence):
        """Entscheidungshilfe: soll der User manuell prüfen?"""
        reliability = self.get_class_reliability(class_name)
        confusion = self.get_confusion_risk(class_name)

        reasons = []
        if calibrated_confidence < 0.45:
            reasons.append("low_confidence")
        if reliability["reliability"] < 0.5:
            reasons.append("low_reliability")
        if confusion["risk_level"] == "high":
            reasons.append("high_confusion")

        return {
            "requires_manual_review": len(reasons) > 0,
            "reasons": reasons,
            "reliability": reliability,
            "confusion": confusion
        }

    def add_condition(self, detection_id, condition_type, severity, description):
        """Speichere Zustandsdetails (Dreck, Beschädigung, etc.)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO object_conditions (detection_id, condition_type, severity, description)
            VALUES (?, ?, ?, ?)
        """, (detection_id, condition_type, severity, description))
        self.conn.commit()

    def add_decision_audit(self, detection_id, class_name, waste_info):
        """Speichere Sicherheits- und Trennungsentscheidung für Nachvollziehbarkeit."""
        cursor = self.conn.cursor()
        review_reasons = waste_info.get("review_reasons", [])
        warnings = waste_info.get("warnings", [])
        has_battery_warning = int(any(("BATTERIE" in w) or ("Akku" in w) or ("akku" in w) for w in warnings))
        cursor.execute(
            """
            INSERT INTO decisions_audit (
                timestamp, detection_id, class_name, action, recommended_bin, safe_fallback_bin,
                decision_quality, requires_manual_review, review_reasons, battery_warning
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                detection_id,
                class_name,
                waste_info.get("action", "MANUAL_CHECK_REQUIRED"),
                waste_info.get("recommended_bin"),
                waste_info.get("safe_fallback_bin", "RESTMÜLL"),
                float(waste_info.get("decision_quality", 0.0)),
                int(bool(waste_info.get("requires_manual_review", True))),
                json.dumps(review_reasons),
                has_battery_warning,
            )
        )
        self.conn.commit()

    def add_self_improvement_run(self, event_type: str, status: str, report: dict):
        """Persistiert automatische Selbstverbesserungs-Läufe inkl. Qualitätsdaten."""
        payload = report or {}
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO self_improvement_runs (
                timestamp, event_type, status,
                local_seed_terms, local_indexed_objects, live_enriched_terms,
                internet_available, trigger_terms_used, accepted_online_terms,
                details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                str(event_type or "unknown"),
                str(status or "unknown"),
                int(payload.get("local_seed_terms", 0) or 0),
                int(payload.get("local_indexed_objects", 0) or 0),
                int(payload.get("live_enriched_terms", 0) or 0),
                int(bool(payload.get("internet_available", False))),
                int(payload.get("trigger_terms_used", 0) or 0),
                int(payload.get("accepted_online_terms", 0) or 0),
                json.dumps(payload),
            ),
        )
        self.conn.commit()

    def get_recent_self_improvement_runs(self, limit=50):
        """Liefert die letzten automatischen Selbstverbesserungs-Läufe."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, event_type, status, local_seed_terms,
                   local_indexed_objects, live_enriched_terms, internet_available,
                   trigger_terms_used, accepted_online_terms, details
            FROM self_improvement_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 500)),),
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "timestamp": row[1],
                "event_type": row[2],
                "status": row[3],
                "local_seed_terms": int(row[4] or 0),
                "local_indexed_objects": int(row[5] or 0),
                "live_enriched_terms": int(row[6] or 0),
                "internet_available": bool(row[7]),
                "trigger_terms_used": int(row[8] or 0),
                "accepted_online_terms": int(row[9] or 0),
                "details": json.loads(row[10]) if row[10] else {},
            })
        return result

    def get_self_improvement_summary(self):
        """Aggregierte Kennzahlen zur kontinuierlichen Selbstverbesserung."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM self_improvement_runs")
        total_runs = int(cursor.fetchone()[0] or 0)

        cursor.execute(
            """
            SELECT
                SUM(local_seed_terms),
                SUM(local_indexed_objects),
                SUM(live_enriched_terms),
                SUM(accepted_online_terms),
                SUM(internet_available)
            FROM self_improvement_runs
            """
        )
        agg = cursor.fetchone() or (0, 0, 0, 0, 0)

        cursor.execute(
            """
            SELECT status, COUNT(*)
            FROM self_improvement_runs
            GROUP BY status
            """
        )
        by_status = {str(r[0]): int(r[1] or 0) for r in cursor.fetchall()}

        return {
            "total_runs": total_runs,
            "total_local_seed_terms": int(agg[0] or 0),
            "total_local_indexed_objects": int(agg[1] or 0),
            "total_live_enriched_terms": int(agg[2] or 0),
            "total_accepted_online_terms": int(agg[3] or 0),
            "runs_with_internet": int(agg[4] or 0),
            "by_status": by_status,
        }

    def get_recent_audits(self, limit=50):
        """Liefert letzte Audit-Einträge, neueste zuerst."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, detection_id, class_name, action, recommended_bin, safe_fallback_bin,
                   decision_quality, requires_manual_review, review_reasons, battery_warning
            FROM decisions_audit
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 500)),)
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "timestamp": row[1],
                "detection_id": row[2],
                "class_name": row[3],
                "action": row[4],
                "recommended_bin": row[5],
                "safe_fallback_bin": row[6],
                "decision_quality": row[7],
                "requires_manual_review": bool(row[8]),
                "review_reasons": json.loads(row[9]) if row[9] else [],
                "battery_warning": bool(row[10]),
            })
        return result

    def cache_web_knowledge(self, object_name, description, properties, source):
        """Cache Web-Wissen über Objekte"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO web_knowledge (object_name, description, properties, source, fetched_at)
            VALUES (?, ?, ?, ?, ?)
        """, (object_name, description, json.dumps(properties), source, datetime.now().isoformat()))
        self.conn.commit()

    def upsert_object_knowledge(self, object_name, inferred_material, inferred_bin, confidence, source, notes=None):
        """Speichert/aktualisiert ein verdichtetes Wissensprofil pro Objektklasse."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO object_knowledge_index
            (object_name, inferred_material, inferred_bin, confidence, source, last_updated, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(object_name),
                inferred_material,
                inferred_bin,
                float(confidence or 0.0),
                source,
                datetime.now().isoformat(),
                notes,
            ),
        )
        self.conn.commit()

    def bulk_upsert_object_knowledge(self, records):
        """Bulk-Upsert für Objektwissen zur Beschleunigung großer Imports."""
        if not records:
            return 0

        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        rows = []
        for rec in records:
            object_name = str(rec.get("object_name", "")).strip()
            if not object_name:
                continue
            rows.append(
                (
                    object_name,
                    str(rec.get("inferred_material", "unknown")),
                    str(rec.get("inferred_bin", "RESTMÜLL")),
                    float(rec.get("confidence", 0.0) or 0.0),
                    str(rec.get("source", "bulk_upsert")),
                    now,
                    rec.get("notes"),
                )
            )

        if not rows:
            return 0

        cursor.executemany(
            """
            INSERT OR REPLACE INTO object_knowledge_index
            (object_name, inferred_material, inferred_bin, confidence, source, last_updated, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()
        return len(rows)

    def seed_object_knowledge_index(self, profiles, source="bootstrap"):
        """Bulk-Seed für Objektwissen-Index aus Klassenprofilen."""
        if not profiles:
            return
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        rows = []
        for profile in profiles:
            obj = str(profile.get("class_name", "")).strip()
            if not obj:
                continue
            rows.append(
                (
                    obj,
                    profile.get("material", "unknown"),
                    profile.get("bin", "RESTMÜLL"),
                    float(profile.get("confidence", 0.45)),
                    source,
                    now,
                    profile.get("source", "seed"),
                )
            )

        if not rows:
            return

        cursor.executemany(
            """
            INSERT OR IGNORE INTO object_knowledge_index
            (object_name, inferred_material, inferred_bin, confidence, source, last_updated, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def get_object_knowledge(self, object_name):
        """Liefert verdichtetes Wissensprofil einer Objektklasse."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT object_name, inferred_material, inferred_bin, confidence, source, last_updated, notes
            FROM object_knowledge_index
            WHERE object_name = ?
            """,
            (object_name,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "object_name": row[0],
            "inferred_material": row[1],
            "inferred_bin": row[2],
            "confidence": float(row[3] or 0.0),
            "source": row[4],
            "last_updated": row[5],
            "notes": row[6],
        }

    def get_web_knowledge(self, object_name):
        """Hole gecachtes Web-Wissen"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT description, properties, source FROM web_knowledge WHERE object_name = ?", (object_name,))
        row = cursor.fetchone()
        if row:
            return {
                "description": row[0],
                "properties": json.loads(row[1]) if row[1] else {},
                "source": row[2]
            }
        return None

    def get_class_knowledge_profile(self, class_name):
        """Liefert aggregiertes Klassenwissen (Seen/Avg/Best)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT class_name, seen_count, avg_confidence, best_confidence, last_seen
            FROM class_knowledge_profile
            WHERE class_name = ?
            """,
            (class_name,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "class_name": row[0],
            "seen_count": int(row[1] or 0),
            "avg_confidence": float(row[2] or 0.0),
            "best_confidence": float(row[3] or 0.0),
            "last_seen": row[4],
        }

    def seed_class_knowledge_profiles(self, class_names):
        """Initialisiert Klassenprofile für bekannte Klassen (ohne bestehende Werte zu überschreiben)."""
        if not class_names:
            return
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        rows = [
            (str(name), 0, 0.0, 0.0, now)
            for name in class_names
            if str(name).strip()
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO class_knowledge_profile (class_name, seen_count, avg_confidence, best_confidence, last_seen)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def get_learning_stats(self):
        """Statistiken über Lernfortschritt"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM detections")
        total_detections = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM feedback")
        total_feedback = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(accuracy_rate) FROM confidence_calibration")
        avg_accuracy = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT COUNT(*) FROM web_knowledge")
        knowledge_items = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM class_knowledge_profile")
        class_knowledge_items = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM object_knowledge_index")
        object_knowledge_items = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM self_improvement_runs")
        self_improvement_runs = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT source, COUNT(*)
            FROM object_knowledge_index
            GROUP BY source
            """
        )
        knowledge_sources = {str(row[0] or "unknown"): int(row[1] or 0) for row in cursor.fetchall()}

        knowledge_coverage = (object_knowledge_items / max(class_knowledge_items, 1)) if class_knowledge_items > 0 else 0.0

        priority = self.get_priority_feedback_classes(limit=5)

        return {
            "total_detections": total_detections,
            "total_feedback": total_feedback,
            "average_accuracy": avg_accuracy,
            "web_knowledge_cached": knowledge_items,
            "class_knowledge_profiles": class_knowledge_items,
            "object_knowledge_indexed": object_knowledge_items,
            "self_improvement_runs": self_improvement_runs,
            "knowledge_sources": knowledge_sources,
            "knowledge_coverage": knowledge_coverage,
            "learning_rate": total_feedback / max(total_detections, 1),
            "priority_feedback_classes": priority
        }

    def get_class_output_threshold(self, class_name, default_threshold=0.40):
        """Dynamische Ausgabeschwelle je Klasse basierend auf Feedbackqualität."""
        base = float(default_threshold)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT accuracy_rate, total_samples
            FROM confidence_calibration
            WHERE class_name = ?
            """,
            (class_name,),
        )
        row = cursor.fetchone()
        if not row:
            return base

        accuracy = float(row[0] or 0.0)
        samples = int(row[1] or 0)

        if samples < 5:
            return min(0.55, base + 0.03)

        if accuracy < 0.45:
            return min(0.72, base + 0.16)
        if accuracy < 0.60:
            return min(0.66, base + 0.11)
        if accuracy < 0.75:
            return min(0.58, base + 0.06)
        if accuracy > 0.92 and samples >= 25:
            return max(0.30, base - 0.05)

        return base

    def get_risky_classes_from_feedback(self, min_wrong_rate=0.30, min_samples=6, limit=40):
        """Liefert Klassen mit hoher Fehlerrate für strengere Laufzeitregeln."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                predicted_class,
                COUNT(*) AS total_samples,
                SUM(CASE WHEN correct_class != predicted_class THEN 1 ELSE 0 END) AS wrong_samples
            FROM feedback
            GROUP BY predicted_class
            HAVING total_samples >= ?
            """,
            (max(1, int(min_samples)),),
        )

        risky = []
        for class_name, total_samples, wrong_samples in cursor.fetchall():
            total = int(total_samples or 0)
            wrong = int(wrong_samples or 0)
            if total <= 0:
                continue
            wrong_rate = wrong / float(total)
            if wrong_rate >= float(min_wrong_rate):
                risky.append(
                    {
                        "class_name": str(class_name),
                        "wrong_rate": wrong_rate,
                        "total_samples": total,
                        "wrong_samples": wrong,
                    }
                )

        risky.sort(key=lambda x: (x["wrong_rate"], x["total_samples"]), reverse=True)
        return risky[: max(1, int(limit))]

    def get_priority_feedback_classes(self, limit=5):
        """Klassen priorisieren, bei denen Feedback den größten Nutzen bringt."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                class_name,
                COALESCE(accuracy_rate, 0.0) AS accuracy_rate,
                COALESCE(total_samples, 0) AS total_samples
            FROM confidence_calibration
            ORDER BY (1.0 - COALESCE(accuracy_rate, 0.0)) DESC,
                     COALESCE(total_samples, 0) DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        result = []
        for class_name, accuracy_rate, total_samples in rows:
            urgency = (1.0 - float(accuracy_rate)) * min(float(total_samples) / 20.0, 1.0)
            result.append({
                "class_name": class_name,
                "accuracy_rate": float(accuracy_rate),
                "total_samples": int(total_samples),
                "urgency": urgency
            })
        return result

    def get_hard_cases(self, limit=100):
        """Liefert schwierige Fälle (manuelle Prüfung / niedrige Qualität) für gezieltes Nachtraining."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                da.id,
                da.timestamp,
                da.detection_id,
                da.class_name,
                da.action,
                da.decision_quality,
                da.review_reasons,
                d.image_hash,
                d.bbox
            FROM decisions_audit da
            LEFT JOIN detections d ON d.id = da.detection_id
            WHERE da.requires_manual_review = 1
               OR da.decision_quality < 0.60
            ORDER BY da.id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 2000)),)
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "audit_id": row[0],
                "timestamp": row[1],
                "detection_id": row[2],
                "class_name": row[3],
                "action": row[4],
                "decision_quality": float(row[5] or 0.0),
                "review_reasons": json.loads(row[6]) if row[6] else [],
                "image_hash": row[7],
                "bbox": json.loads(row[8]) if row[8] else None,
            })
        return result

    def get_recent_feedback_error_rates(self, window=50):
        """Rolling Fehlerquote aus den letzten Feedbacks (gesamt + letzte Hälfte)."""
        n = max(10, min(int(window), 1000))
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT predicted_class, correct_class
            FROM feedback
            ORDER BY id DESC
            LIMIT ?
            """,
            (n,)
        )
        rows = cursor.fetchall()
        if not rows:
            return {
                "window": n,
                "samples": 0,
                "overall_error_rate": 0.0,
                "recent_error_rate": 0.0,
                "trend": "unknown"
            }

        # rows sind absteigend (neueste zuerst)
        errors = [1 if r[0] != r[1] else 0 for r in rows]
        overall_error_rate = sum(errors) / len(errors)

        half = max(1, len(errors) // 2)
        recent = errors[:half]
        older = errors[half:]
        recent_error_rate = sum(recent) / len(recent)
        older_error_rate = (sum(older) / len(older)) if older else recent_error_rate

        if recent_error_rate < older_error_rate - 0.03:
            trend = "improving"
        elif recent_error_rate > older_error_rate + 0.03:
            trend = "worsening"
        else:
            trend = "stable"

        return {
            "window": n,
            "samples": len(errors),
            "overall_error_rate": overall_error_rate,
            "recent_error_rate": recent_error_rate,
            "older_error_rate": older_error_rate,
            "trend": trend
        }

    def save_manual_annotation(self, bbox, object_class, image_hash=None, frame_path=None, suggested_bin=None, comment=None):
        """
        Speichere manuelle Annotation für nicht erkannte Objekte
        
        Args:
            bbox: Bounding Box als Dict oder JSON-String {"x1": ..., "y1": ..., "x2": ..., "y2": ...}
            object_class: Objektname, den der Nutzer eingegeben hat
            image_hash: Hash des Frames (zur Duplikat-Erkennung)
            frame_path: Pfad wo Frame gespeichert wurde
            suggested_bin: Vorschlag für Mülltonne von der KI
            comment: Nutzer-Kommentar
            
        Returns:
            annotation_id
        """
        cursor = self.conn.cursor()
        bbox_json = json.dumps(bbox) if not isinstance(bbox, str) else bbox
        
        cursor.execute("""
            INSERT INTO manual_annotations (
                timestamp, image_hash, bbox, object_class, 
                frame_saved, frame_path, suggested_bin, comment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            image_hash,
            bbox_json,
            object_class,
            1 if frame_path else 0,
            frame_path,
            suggested_bin,
            comment
        ))
        self.conn.commit()
        return cursor.lastrowid

    def confirm_manual_annotation(self, annotation_id):
        """Nutzer bestätigt manuelle Annotation - wird als Training-Beispiel verwendet"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE manual_annotations
            SET user_confirmed = 1
            WHERE id = ?
        """, (annotation_id,))
        self.conn.commit()

    def get_manual_annotations(self, limit=500, only_confirmed=False):
        """
        Hole manuelle Annotations (z.B. für Training-Export)
        
        Args:
            limit: Max Anzahl
            only_confirmed: Nur vom Nutzer bestätigte Annotations
            
        Returns:
            Liste von Annotations mit Metadaten
        """
        cursor = self.conn.cursor()
        query = "SELECT * FROM manual_annotations"
        params = []
        
        if only_confirmed:
            query += " WHERE user_confirmed = 1"
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(max(1, min(limit, 5000)))
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "timestamp": row[1],
                "image_hash": row[2],
                "bbox": json.loads(row[3]) if row[3] else {},
                "object_class": row[4],
                "frame_saved": bool(row[5]),
                "frame_path": row[6],
                "suggested_bin": row[7],
                "user_confirmed": bool(row[8]),
                "comment": row[9]
            })
        return result

    def get_manual_annotations_statistics(self):
        """Statistiken über manuelle Annotations"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM manual_annotations")
        total = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM manual_annotations WHERE user_confirmed = 1")
        confirmed = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT object_class, COUNT(*) FROM manual_annotations
            GROUP BY object_class
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        by_class = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "total_annotations": total,
            "confirmed_annotations": confirmed,
            "pending_confirmation": total - confirmed,
            "top_classes": by_class
        }


# Singleton
_db = None

def get_db():
    global _db
    if _db is None:
        _db = LearningDatabase()
    return _db
