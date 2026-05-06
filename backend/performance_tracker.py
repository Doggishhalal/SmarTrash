"""
Performance Tracker - Zeigt wie die KI sich verbessert
======================================================
Misst und visualisiert Lernfortschritt über Zeit
"""
from learning_db import get_db
from datetime import datetime, timedelta
import json


class PerformanceTracker:
    """Trackt KI-Performance und Verbesserungen"""
    
    def __init__(self):
        self.db = get_db()
    
    def get_accuracy_trend(self, days=7):
        """Zeige Accuracy-Entwicklung über Zeit"""
        cursor = self.db.conn.cursor()
        
        # Hole Feedback der letzten N Tage
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT 
                DATE(timestamp) as day,
                COUNT(*) as total,
                SUM(CASE WHEN predicted_class = correct_class THEN 1 ELSE 0 END) as correct
            FROM feedback
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY day
        """, (cutoff,))
        
        trend = []
        for row in cursor.fetchall():
            day, total, correct = row
            accuracy = correct / total if total > 0 else 0
            trend.append({
                "date": day,
                "total_feedbacks": total,
                "correct": correct,
                "accuracy": accuracy
            })
        
        return trend
    
    def get_class_improvements(self):
        """Zeige welche Klassen sich am meisten verbessert haben"""
        cursor = self.db.conn.cursor()
        
        # Vergleiche frühe vs. späte Accuracy
        cursor.execute("""
            WITH early_feedback AS (
                SELECT 
                    predicted_class,
                    COUNT(*) as total,
                    SUM(CASE WHEN predicted_class = correct_class THEN 1 ELSE 0 END) as correct
                FROM feedback
                WHERE id <= (SELECT COUNT(*)/2 FROM feedback)
                GROUP BY predicted_class
            ),
            late_feedback AS (
                SELECT 
                    predicted_class,
                    COUNT(*) as total,
                    SUM(CASE WHEN predicted_class = correct_class THEN 1 ELSE 0 END) as correct
                FROM feedback
                WHERE id > (SELECT COUNT(*)/2 FROM feedback)
                GROUP BY predicted_class
            )
            SELECT 
                COALESCE(e.predicted_class, l.predicted_class) as class_name,
                COALESCE(e.correct * 1.0 / NULLIF(e.total, 0), 0) as early_accuracy,
                COALESCE(l.correct * 1.0 / NULLIF(l.total, 0), 0) as late_accuracy,
                COALESCE(l.correct * 1.0 / NULLIF(l.total, 0), 0) - COALESCE(e.correct * 1.0 / NULLIF(e.total, 0), 0) as improvement
            FROM early_feedback e
            FULL OUTER JOIN late_feedback l ON e.predicted_class = l.predicted_class
            WHERE COALESCE(e.total, 0) + COALESCE(l.total, 0) >= 3
            ORDER BY improvement DESC
        """)
        
        improvements = []
        for row in cursor.fetchall():
            class_name, early, late, improvement = row
            improvements.append({
                "class": class_name,
                "early_accuracy": early or 0.0,
                "late_accuracy": late or 0.0,
                "improvement": improvement or 0.0,
                "learned": improvement > 0.1  # >10% Verbesserung
            })
        
        return improvements
    
    def get_detection_quality_trend(self):
        """Zeige wie sich Erkennungs-Qualität entwickelt"""
        cursor = self.db.conn.cursor()
        
        # Analyse: Frühe vs. späte Detections
        cursor.execute("""
            SELECT 
                id,
                timestamp,
                confidence,
                details
            FROM detections
            ORDER BY timestamp
        """)
        
        all_detections = cursor.fetchall()
        if len(all_detections) < 10:
            return {"status": "insufficient_data", "message": "Need at least 10 detections"}
        
        # Split in early/late
        split_point = len(all_detections) // 2
        early = all_detections[:split_point]
        late = all_detections[split_point:]
        
        # Berechne durchschnittliche Confidence
        early_conf = sum(d[2] for d in early) / len(early)
        late_conf = sum(d[2] for d in late) / len(late)
        
        # Berechne Anzahl erkannter Conditions
        early_conditions = sum(1 for d in early if d[3] and json.loads(d[3]).get("details"))
        late_conditions = sum(1 for d in late if d[3] and json.loads(d[3]).get("details"))
        
        return {
            "early_period": {
                "avg_confidence": early_conf,
                "detections_with_conditions": early_conditions,
                "total_detections": len(early)
            },
            "late_period": {
                "avg_confidence": late_conf,
                "detections_with_conditions": late_conditions,
                "total_detections": len(late)
            },
            "improvement": {
                "confidence_change": late_conf - early_conf,
                "condition_detection_improved": late_conditions > early_conditions
            }
        }
    
    def get_learning_dashboard(self):
        """Komplettes Dashboard mit allen Metriken"""
        stats = self.db.get_learning_stats()
        
        cursor = self.db.conn.cursor()
        
        # Top 5 beste Klassen
        cursor.execute("""
            SELECT class_name, accuracy_rate, total_samples
            FROM confidence_calibration
            WHERE total_samples >= 3
            ORDER BY accuracy_rate DESC
            LIMIT 5
        """)
        best_classes = [{"class": r[0], "accuracy": r[1], "samples": r[2]} for r in cursor.fetchall()]
        
        # Top 5 schlechteste Klassen
        cursor.execute("""
            SELECT class_name, accuracy_rate, total_samples
            FROM confidence_calibration
            WHERE total_samples >= 3
            ORDER BY accuracy_rate ASC
            LIMIT 5
        """)
        worst_classes = [{"class": r[0], "accuracy": r[1], "samples": r[2]} for r in cursor.fetchall()]
        
        # Häufigste Fehler
        cursor.execute("""
            SELECT predicted_class, correct_class, COUNT(*) as count
            FROM feedback
            WHERE predicted_class != correct_class
            GROUP BY predicted_class, correct_class
            ORDER BY count DESC
            LIMIT 5
        """)
        common_errors = [{"predicted": r[0], "should_be": r[1], "count": r[2]} for r in cursor.fetchall()]
        
        return {
            "overall_stats": stats,
            "best_performing_classes": best_classes,
            "needs_improvement": worst_classes,
            "common_mistakes": common_errors,
            "accuracy_trend": self.get_accuracy_trend(days=30),
            "class_improvements": self.get_class_improvements(),
            "quality_trend": self.get_detection_quality_trend()
        }

    def get_benchmark_summary(self, recognition_profile=None):
        """Leichtgewichtiger Qualitäts- und Reifegradbericht für das aktuelle System."""
        dashboard = self.get_learning_dashboard()
        stats = dashboard.get("overall_stats", {}) or {}
        profile = recognition_profile or {}
        enabled_features = profile.get("enabled_features", {}) or {}

        total_feedback = int(stats.get("total_feedback", 0) or 0)
        avg_accuracy = float(stats.get("average_accuracy", 0.0) or 0.0)
        detection_count = int(stats.get("total_detections", 0) or 0)

        feature_score = sum(1 for enabled in enabled_features.values() if enabled)
        feature_total = max(len(enabled_features), 1)
        feature_coverage = feature_score / feature_total

        readiness = 0.0
        readiness += min(0.35, avg_accuracy * 0.35)
        readiness += min(0.20, min(total_feedback / 100.0, 1.0) * 0.20)
        readiness += min(0.20, min(detection_count / 200.0, 1.0) * 0.20)
        readiness += feature_coverage * 0.25

        gaps = []
        if total_feedback < 25:
            gaps.append("too_little_feedback")
        if avg_accuracy < 0.75 and total_feedback >= 10:
            gaps.append("accuracy_below_target")
        if not enabled_features.get("auto_retrain", False):
            gaps.append("auto_retrain_disabled")
        if not enabled_features.get("knowledge_enrichment", False):
            gaps.append("knowledge_enrichment_disabled")

        return {
            "readiness_score": round(min(1.0, readiness), 3),
            "readiness_label": "production_ready" if readiness >= 0.82 else "needs_more_data" if readiness < 0.60 else "strong_but_improvable",
            "feature_coverage": round(feature_coverage, 3),
            "total_feedback": total_feedback,
            "total_detections": detection_count,
            "average_accuracy": avg_accuracy,
            "gaps": gaps,
            "active_profile": profile.get("profile_name", "unknown"),
            "model_variant": profile.get("model_variant", "unknown"),
            "public_data_sources": list(profile.get("public_data_sources", [])),
        }


# Singleton
_tracker = None

def get_tracker():
    global _tracker
    if _tracker is None:
        _tracker = PerformanceTracker()
    return _tracker
