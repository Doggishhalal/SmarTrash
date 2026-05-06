"""
Detail Analyzer - Erkennt Zustand und Kleinigkeiten auf Objekten
================================================================
Analysiert: Sauberkeit, Beschädigungen, Besonderheiten
"""
import cv2
import numpy as np


class DetailAnalyzer:
    """Analysiert Details wie Dreck, Beschädigungen, Verfärbungen"""
    
    def __init__(self):
        self.conditions = []
    
    def analyze_object_condition(self, image: np.ndarray, bbox: list):
        """Analysiere Objekt-Zustand innerhalb der BBox"""
        conditions = []
        
        x1, y1, x2, y2 = [int(v) for v in bbox]
        # Crop to object
        obj_roi = image[y1:y2, x1:x2]
        
        if obj_roi.size == 0:
            return conditions
        
        # 1. Sauberkeits-Analyse (Dreck, Flecken)
        dirt_score = self._detect_dirt(obj_roi)
        if dirt_score > 0.3:
            conditions.append({
                "type": "dirt",
                "severity": dirt_score,
                "description": f"Verschmutzung erkannt ({dirt_score:.1%})"
            })
        
        # 2. Beschädigungs-Analyse (Risse, Kratzer)
        damage_score = self._detect_damage(obj_roi)
        if damage_score > 0.2:
            conditions.append({
                "type": "damage",
                "severity": damage_score,
                "description": f"Beschädigung erkannt ({damage_score:.1%})"
            })
        
        # 3. Verfärbungs-Analyse
        discoloration_score = self._detect_discoloration(obj_roi)
        if discoloration_score > 0.25:
            conditions.append({
                "type": "discoloration",
                "severity": discoloration_score,
                "description": f"Verfärbung erkannt ({discoloration_score:.1%})"
            })
        
        # 4. Feuchtigkeit/Nässe
        wetness_score = self._detect_wetness(obj_roi)
        if wetness_score > 0.3:
            conditions.append({
                "type": "wetness",
                "severity": wetness_score,
                "description": f"Feuchtigkeit erkannt ({wetness_score:.1%})"
            })
        
        # 5. Textur-Anomalien
        texture_score = self._detect_texture_anomalies(obj_roi)
        if texture_score > 0.35:
            conditions.append({
                "type": "texture_anomaly",
                "severity": texture_score,
                "description": f"Ungewöhnliche Textur ({texture_score:.1%})"
            })
        
        return conditions
    
    def _detect_dirt(self, roi):
        """Erkenne Dreck durch dunkle Flecken und Unregelmäßigkeiten"""
        if roi.size == 0:
            return 0.0
        
        # Konvertiere zu Graustufen
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        
        # Detect dark spots (Dreck ist oft dunkel)
        dark_threshold = np.mean(gray) * 0.6
        dark_pixels = np.sum(gray < dark_threshold)
        dark_ratio = dark_pixels / gray.size
        
        # Variance (Dreck macht Bild ungleichmäßiger)
        variance = np.var(gray)
        variance_score = min(variance / 1000.0, 1.0)
        
        return (dark_ratio * 0.6 + variance_score * 0.4)
    
    def _detect_damage(self, roi):
        """Erkenne Beschädigungen durch Kanten-Analyse"""
        if roi.size == 0:
            return 0.0
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        
        # Canny Edge Detection (Risse sind Kanten)
        edges = cv2.Canny(gray, 50, 150)
        edge_ratio = np.sum(edges > 0) / edges.size
        
        # Scharfe, unnatürliche Kanten deuten auf Beschädigungen hin
        return min(edge_ratio * 2.0, 1.0)
    
    def _detect_discoloration(self, roi):
        """Erkenne Verfärbungen durch Farb-Analyse"""
        if roi.size == 0 or len(roi.shape) != 3:
            return 0.0
        
        # Konvertiere zu HSV
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Analyse Hue-Varianz (Verfärbungen = ungleiche Farben)
        h, s, v = cv2.split(hsv)
        hue_std = np.std(h)
        sat_std = np.std(s)
        
        # Hohe Varianz = Verfärbung
        color_variance = (hue_std + sat_std) / 200.0
        return min(color_variance, 1.0)
    
    def _detect_wetness(self, roi):
        """Erkenne Feuchtigkeit durch Glanz/Reflexionen"""
        if roi.size == 0:
            return 0.0
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        
        # Nasse Oberflächen haben oft helle Reflexionen
        bright_threshold = np.mean(gray) * 1.4
        bright_pixels = np.sum(gray > bright_threshold)
        bright_ratio = bright_pixels / gray.size
        
        # Analyse Gradient (nasse Flächen haben glatte Gradienten)
        gradient_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gradient_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(gradient_x**2 + gradient_y**2)
        smooth_score = 1.0 - min(np.mean(gradient_mag) / 50.0, 1.0)
        
        return (bright_ratio * 0.5 + smooth_score * 0.5)
    
    def _detect_texture_anomalies(self, roi):
        """Erkenne ungewöhnliche Texturen"""
        if roi.size == 0:
            return 0.0
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        
        # LBP (Local Binary Pattern) für Textur-Analyse
        # Vereinfachte Version: Analyse lokaler Varianz
        patches = []
        h, w = gray.shape
        patch_size = 16
        
        for i in range(0, h - patch_size, patch_size):
            for j in range(0, w - patch_size, patch_size):
                patch = gray[i:i+patch_size, j:j+patch_size]
                patches.append(np.var(patch))
        
        if not patches:
            return 0.0
        
        # Ungewöhnliche Textur = hohe Varianz zwischen Patches
        patch_variance = np.var(patches)
        return min(patch_variance / 500.0, 1.0)
    
    def get_overall_condition(self, conditions):
        """Berechne Gesamt-Zustand"""
        if not conditions:
            return {"state": "clean", "score": 1.0, "description": "Objekt in gutem Zustand"}
        
        avg_severity = np.mean([c["severity"] for c in conditions])
        
        if avg_severity < 0.2:
            state = "good"
            description = "Leichte Gebrauchsspuren"
        elif avg_severity < 0.4:
            state = "acceptable"
            description = "Sichtbare Abnutzung"
        elif avg_severity < 0.6:
            state = "worn"
            description = "Deutliche Abnutzung"
        elif avg_severity < 0.8:
            state = "poor"
            description = "Starke Abnutzung"
        else:
            state = "damaged"
            description = "Stark beschädigt/verschmutzt"
        
        return {
            "state": state,
            "score": 1.0 - avg_severity,
            "description": description,
            "details": conditions
        }


# Singleton
_analyzer = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = DetailAnalyzer()
    return _analyzer
