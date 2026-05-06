# 🗑️ SmarTrash - AI-gestützte Abfallklassifizierung

**Intelligente Abfallsortiersystem mit kontinuierlichem self-learning**

---

## 🎯 Was ist SmarTrash?

SmarTrash ist ein **produktionsreifes AI-System** zur automatischen Klassifizierung von Abfall in 4 Kategorien:

- **RESTMÜLL** (Sperrmüll, Sonstiges)
- **BIOMÜLL** (Organisches Material)
- **PAPIER** (Karton, Papier, Zeitschriften)
- **PLASTIK** (Kunststoffverpackungen)

### Besonderheiten:
✅ **Self-Learning**: Verbessert sich durch Feedback  
✅ **Hard-Safety Mode**: Unsichere Fälle → Manuelle Review (nicht Auto-Sortierung)  
✅ **Echtzeit Web-Dashboard**: Live-Kamera, Feedback, Quality Monitoring  
✅ **Vollständig kostenlos**: Keine bezahlten APIs/Services  
✅ **Datenschutz by Design**: Lokale Verarbeitung, Automatische Cleanup  
✅ **Production-ready**: Compliance Guard, Error-Rate Tracking, Audit-Logging  

---

## 🚀 Schnell-Installation

```bash
cd backend
# Windows:
start.bat  # oder: .\setup.ps1

# Linux/Mac:
chmod +x start.sh  # falls vorhanden
python main.py
```

Dashboard öffnet sich automatisch unter: **http://localhost:8000/dashboard**

Siehe [INSTALLATION.md](backend/INSTALLATION.md) für detaillierte Anweisungen.

---

## 📁 Projektstruktur

```
SmarTrash/
├── README.md                           # Dieses Dokument
├── backend/
│   ├── start.bat                       # Quick-Start (Windows)
│   ├── setup.ps1                       # Setup Script (PowerShell)
│   ├── INSTALLATION.md                 # Detaillierte Anleitung
│   ├── requirements.txt                # Python Dependencies
│   │
│   ├── main.py                         # FastAPI Server + REST API
│   ├── safety_config.py                # Zentrale Konfiguration
│   │
│   ├── inference.py                    # YOLOX Detection Pipeline
│   ├── waste_classifier.py             # Abfall → Bin Klassifizierung
│   ├── detail_analysis.py              # Material/Zustand Erkennung
│   │
│   ├── learning_db.py                  # Feedback-Speicher & Analytics
│   ├── sample_memory.py                # Training-Datenverwaltung
│   ├── quality_controller.py           # Adaptive Quality Thresholds
│   ├── compliance_guard.py             # No-Cost & Privacy Verifikation
│   │
│   ├── frontend/                       # Web-Dashboard
│   │   ├── index.html                  # UI
│   │   ├── dashboard.js                # Interaktivität
│   │   └── style.css                   # Styling
│   │
│   ├── ncnn-master/                    # NCNN Library (optional)
│   ├── opencv-4.12.0/                  # OpenCV (optional)
│   ├── YOLOX-main/                     # YOLOX Source (optional)
│   └── sample_memory/                  # Trainings-Daten
│       ├── incoming/                   # Neue Bilder
│       ├── verified/                   # Verifizierte Samples
│       │   ├── RESTMÜLL/
│       │   ├── BIOMÜLL/
│       │   ├── PAPIER/
│       │   └── PLASTIK/
│       ├── feedback/
│       │   ├── stimmt/                 # Positive Feedback
│       │   └── stimmt_nicht/           # Negative Feedback
│       └── exports/                    # Dataset-Exports
└── .gitignore
```

---

## 🎮 Workflow

### 1️⃣ **Bild analysieren**
```bash
curl -X POST http://localhost:8000/detect \
  -F "file=@abfall.jpg"
```

**Response:**
```json
{
  "detections": [
    {
      "class_name": "plastic_bottle",
      "confidence": 0.95,
      "recommended_bin": "PLASTIK",
      "user_action": "AUTO_SORT"
    }
  ],
  "quality_control_mode": "stable_high_quality",
  "adaptive_policy_mode": "stable_high_quality"
}
```

### 2️⃣ **Feedback geben**
```bash
curl -X POST http://localhost:8000/feedback/verify \
  -H "Content-Type: application/json" \
  -d '{
    "detection_id": 123,
    "feedback_type": "stimmt",
    "image_base64": "data:image/jpeg;base64,..."
  }'
```

### 3️⃣ **Monitoring**
```bash
# Error-Rate Trend
curl http://localhost:8000/quality/error-trend

# Compliance Status
curl http://localhost:8000/compliance/report

# System Health
curl http://localhost:8000/system/audit
```

### 4️⃣ **Dataset exportieren** (für Retraining)
```bash
curl http://localhost:8000/learning/export-dataset
```

---

## 🧠 How It Works (KI-Komponenten)

### 1. **Detection** (YOLOX)
- Pre-trained YOLOX Small (80 COCO-Klassen)
- Erkennt Alltagsobjekte (Flaschen, Dosen, Papier, etc.)
- Output: Bounding Boxes + Confidence-Scores

### 2. **Classification** (Waste Bins)
- Maps YOLOX Detektionen → 4 Abfall-Kategorien
- **Hard-Safety**: Confidence < threshold → MANUAL_CHECK_REQUIRED
- **Fallback**: Batterie erkannt → sofort Manual Review

### 3. **Quality Control** (Adaptive Thresholds)
```
Error-Rate < 12% + improving → milde Thresholds
Error-Rate 12-28% → normales Threshold
Error-Rate > 28% → strict Thresholds
```

### 4. **Learning** (Feedback-Loop)
```
Benutzer sieht: [Bild + Detektion]
  ↓
User gibt Feedback: "stimmt" oder "stimmt_nicht"
  ↓
System speichert:
  - Detektion in Learning-DB
  - Bild in verified/{correct_class}/
  - Erhöht Confidence für korrekte Klasse
  - Senkt Confidence für falsche Klasse
  ↓
Nächste Detektion nutzt aktualisierte Gewichte
```

---

## 📊 Dashboard Features

### Live-Tab:
- **Kamera-Stream** von Webcam
- **Bild-Upload** mit File-Picker
- **Echtzeit Bounding Boxes** auf Video
- **Detektions-Tabelle** mit Confidence & Empfehlungen

### Feedback-Interface:
- **Stimmt!** Button → speichert korrekte Klassifizierung
- **Stimmt nicht** Button → speichert falsche Klassifizierung
- Automatische Bild-Speicherung in Training-Datenbank

### Monitoring:
- **Error-Rate Chart** (Trend über Zeit)
- **Compliance Score** (% NO-COST Policy erfüllt)
- **Quality Control Mode** (Cold-Start / Strict Recovery / Stable High-Quality)
- **Review-Queue** (Cases die noch manuelles Review brauchen)
- **Quick Stats** (Heute, diese Woche, gesamt)

---

## ⚙️ Konfiguration

### Zentrale Safety-Flags (safety_config.py):

```python
# Sicherheit
SMARTRASH_HARD_SAFETY_MODE = True          # ← Unsicher = Manual Review
SMARTRASH_ULTRA_STRICT_ELECTRONICS = True  # ← Batterien erkannt = Manual Review
SMARTRASH_MIN_QUALITY = 0.70
SMARTRASH_MIN_CONFIDENCE = 0.55

# Kosten
SMARTRASH_NO_COST_MODE = True              # ← Nur gratis APIs
SMARTRASH_ALLOW_PAID_INTEGRATIONS = False

# Datenschutz
SMARTRASH_STORE_PERSON_IMAGES = False      # ← Nicht speichern wenn Person erkannt
SMARTRASH_RETENTION_DAYS = 30              # ← Auto-Cleanup nach 30 Tagen

# Quality Control
SMARTRASH_ENABLE_ADAPTIVE_POLICY = True
SMARTRASH_ERROR_RATE_WINDOW = 80           # ← Letzten 80 Samples
SMARTRASH_ERROR_RATE_TARGET = 0.15         # ← Ziel: 15% Fehler
```

### Umgebungsvariablen:
```bash
export SMARTRASH_HARD_SAFETY_MODE=true
export SMARTRASH_NO_COST_MODE=true
export SMARTRASH_RETENTION_DAYS=30
export YOLOX_DEVICE=cpu  # oder: cuda (für GPU)
```

---

## 📈 Daten-Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER/CAMERA                              │
│                 (Bild hochladen)                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  YOLOX Detection      │
         │  (80 COCO Klassen)    │
         │  → Bboxes + Scores    │
         └────────────┬──────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Detail Analysis       │
         │ (Material, State)     │
         │ + Web Knowledge       │
         │ (Wikipedia, DBpedia)  │
         └────────────┬──────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Quality Control       │
         │ Adaptive Thresholds   │
         │ (Low/Normal/Strict)   │
         └────────────┬──────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Waste Classifier      │
         │ YOLOX → 4 Bins        │
         │ + Hard-Safety Mode    │
         │ → Manual Review?      │
         └────────────┬──────────┘
                     │
        ┌────────────┴──────────┬─────────────┐
        │                       │             │
        ▼                       ▼             ▼
   AUTO_SORT         MANUAL_CHECK_REQUIRED  ERROR/ALERT
   (High Conf)       (Low Conf/Battery)     (Compliance)
        │                       │             │
        └───────────┬───────────┴─────────────┘
                    │
                    ▼
         ┌───────────────────────┐
         │      USER FEEDBACK    │
         │  stimmt / stimmt nicht │
         └────────────┬──────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Learning Database    │
         │ • Decision logging    │
         │ • Feedback storage    │
         │ • Error analytics     │
         └────────────┬──────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Sample Memory        │
         │ • Verified samples    │
         │ • Class directories   │
         │ • YOLO export ready   │
         └────────────┬──────────┘
                     │
                   LOOP
              (Nächstes Bild)
```

---

## 🔐 Compliance & Sicherheit

### ✅ No Hidden Costs
- `compliance_guard.py` scannt `requirements.txt` auf bezahlte Pakete
- Keine Cloud-APIs (OpenAI, Google Cloud, AWS)
- Alle Quellen gratis: Wikipedia REST, DBpedia SPARQL, OpenFoodFacts

### ✅ Privacy by Design
- Person-Bilder **NICHT** gespeichert (check bei Accept)
- Automatische **30-Tage Cleanup** (konfigurierbar)
- Alle Daten lokal in SQLite
- Transparent logging: `/compliance/report` zeigt Status

### ✅ Audit Logging
- Jede Detektions-Entscheidung wird geloggt
- `decisions_audit` Tabelle mit: `decision_quality, requires_manual_review, review_reasons`
- Systemprüfung: `/system/audit` zeigt Production-Readiness

---

## 🧪 Testing & Validation

### Unit Tests (später):
```bash
pytest backend/
```

### API Tests:
```bash
# Health
curl http://localhost:8000/health

# Compliance
curl http://localhost:8000/compliance/report

# System Audit
curl http://localhost:8000/system/audit
```

### Dashboard Test:
1. Browser: http://localhost:8000/dashboard
2. Kamera starten
3. Foto aufnehmen
4. Feedback geben (Stimmt/Stimmt nicht)
5. Überprüfe: Review-Queue, Error-Rate, Compliance

---

## 📚 API Dokumentation

### Vollständige Docs (interaktiv):
```
http://localhost:8000/docs
```

### Wichtigste Endpoints:

| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| POST | `/detect` | Bild analysieren |
| POST | `/feedback/verify` | Feedback geben |
| GET | `/learning/review-queue` | Manual-Review Cases |
| GET | `/learning/export-dataset` | Dataset YOLO-Format |
| GET | `/quality/error-trend` | Fehlerrate-Trend |
| GET | `/compliance/report` | Compliance Status |
| POST | `/compliance/cleanup-data` | Effektiv 30-Tage Cleanup |
| GET | `/system/audit` | System-Audit & Production-Check |

---

## 🎓 Beispiel: Von 0 zu Production

### Tag 1: Setup
```bash
cd backend
./start.bat  # oder setup.ps1
```

### Day 1-7: Training Data sammeln
1. 50-100 Bilder hochladen
2. Für jedes `stimmt` oder `stimmt nicht` geben
3. Error-Rate sinkt auf < 20%

### Day 8-14: Model testen
1. Zusätzliche 50-100 Bilder
2. Error-Rate sollte auf < 15% stabil werden
3. Review-Queue sollte klein sein

### Day 15+: Production
1. Dataset mit 200+ verifizierte Samples exportieren
2. Mit YOLOX neu trainieren (optional, externe Tools)
3. Deploy neues Model
4. Täglich Feedback weiter sammeln
5. Monatlich Retraining mit neuesten Daten

---

## 🛠️ Troubleshooting

### Error: "ModuleNotFoundError: No module named 'fastapi'"
```bash
pip install --upgrade pip
pip install -r requirements.txt
# Falls noch immer Fehler: venv neu erstellen
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Error: "YOLOX model not found"
- Model muss unter `C:\models\yolox_s.pth` sein
- Download: https://github.com/Megvii-BaseDetection/YOLOX/releases

### Dashboard zeigt "Offline"
- Server läuft? Prüfe: http://localhost:8000/health
- Firewall blockiert? Port 8000 freigeben
- Browser-Cache clearen (Ctrl+Shift+Delete)

### Kamera funktioniert nicht
- Erlaubnis für Browser geben (Pop-up akzeptieren)
- Andere Browser testen (Chrome/Firefox empfohlen)
- USB-Kamera umstecken (auch bei USB)

---

## 📞 Support & Kontakt

- **Dashboard Help**: Siehe "?" Button oben rechts (später hinzufügen)
- **API Docs**: http://localhost:8000/docs
- **Issues**: Prüfe TROUBLESHOOTING oben
- **Log-Dateien**: Terminal-Output des Servers zeigt Fehler

---

## 📜 Lizenz & Credits

- **YOLOX**: [GitHub](https://github.com/Megvii-BaseDetection/YOLOX) (MIT License)
- **FastAPI**: [GitHub](https://github.com/tiangolo/fastapi) (MIT License)
- **PyTorch**: [GitHub](https://github.com/pytorch/pytorch) (BSD License)
- **Bootstrap 5 & Chart.js**: Kostenlos, Open-Source

---

## ✨ Roadmap (Zusätzliche Features)

- [ ] Mobile App (iOS/Android)
- [ ] Real-time Sensor Integration (IR, Weight)
- [ ] Automated Model Retraining Pipeline
- [ ] Multi-language Support (EN, FR, IT, ES)
- [ ] Advanced Analytics Dashboard
- [ ] Hardware Optimization (ARM/Edge Devices)
- [ ] Cloud Sync Option (optional)

---

## 🎯 Status: ✅ PRODUCTION READY

- ✅ Safety: Hard-Safety Mode aktiviert
- ✅ Compliance: No-Cost Guard, Privacy Controls
- ✅ UI: Web-Dashboard vollständig
- ✅ API: REST vollständig dokumentiert
- ✅ Learning: Feedback-Loop funktionstüchtig
- ✅ Monitoring: Error-Rate Tracking, Audit Logs

🚀 **Ready to Go!**

---

*Last Updated: March 4, 2026*
*SmarTrash v2.0 - AI-Powered Waste Classification*
