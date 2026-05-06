# 🗑️ SmarTrash - Produktive Installationsleitfaden

## ⚡ Schnellstart (5 Minuten)

### Windows (einfach):
1. **Doppelklick auf `start.bat`** im `backend/` Ordner
2. Folgen Sie den Anweisungen (Dependencies werden automatisch installiert)
3. Öffnen Sie im Browser: **http://localhost:8000/dashboard**
4. Bild hochladen → detektieren → Feedback geben → KI lernt!

### Windows (PowerShell):
```powershell
cd backend
.\scripts\setup.ps1
```

### Linux/Mac:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python main.py
```

---

## 📋 Voraussetzungen

- **Python 3.8+** → [Download](https://python.org)
- **YOLOX Model** (540 MB) → [Download](https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1_weights/yolox_s.pth)

---

## 🔧 Manuelle Installation (falls nötig)

### 1. Python Environment setup:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Dependencies installieren:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. YOLOX Model herunterladen:
```bash
# Erstelle Ordner (falls nicht vorhanden)
mkdir C:\models  # Windows
mkdir ~/models   # macOS/Linux

# Download Model (540 MB)
# Von: https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1_weights/yolox_s.pth
# Nach: C:\models\yolox_s.pth
```

### 4. Server starten:
```bash
python main.py
```

---

## 🌐 Zugriff auf Dashboard

Nach dem Start erreichen Sie:

| URL | Zweck |
|-----|-------|
| http://localhost:8000/dashboard | **Web-Dashboard** (Kamera, Feedback, Stats) |
| http://localhost:8000/docs | API-Dokumentation (interaktiv) |
| http://localhost:8000 | JSON API Root (alle Endpoints) |

---

## 📸 Dashboard Features

### Live Tab:
- **Kamera starten** → Bild aufnehmen → analysieren
- **Bild hochladen** → direkt mit File-Picker
- **Echtzeit Bounding Boxes** auf Video

### Feedback:
- **Stimmt!** / **Stimmt nicht** Buttons
- Speichert Training-Daten automatisch
- KI lernt sofort aus Feedback

### Monitoring:
- **Fehlerrate-Trend** (Chart)
- **Compliance Status** (✅ Keine versteckten Kosten)
- **Quality Control Mode** (adaptive Thresholds)
- **Review-Queue** (Cases zum manuellen Review)

---

## 🎓 Tyischer Workflow

1. **Bild aufnehmen** mit Kamera oder Upload
2. **Detektionen sehen** mit Confidence-Scores
3. **Feedback geben**: stimmt es oder nicht?
4. **System lernt** - Error-Rate sinkt mit mehr Feedback
5. **Bei ~80 Samples**: Exportiere zur Retraining
6. **Neues Model trainieren** und deployen

---

## ⚙️ Konfiguration

### Safety & Compliance (automatisch):
```python
# Aus: backend/safety_config.py
SMARTRASH_HARD_SAFETY_MODE=true        # Unsicher → Manual Review
SMARTRASH_NO_COST_MODE=true            # Keine bezahlten APIs
SMARTRASH_RETENTION_DAYS=30            # Auto-Datenlöschung
```

Umgebungsvariablen setzen:
```bash
# Windows (PowerShell)
$env:SMARTRASH_HARD_SAFETY_MODE = "true"

# Windows (Batch)
set SMARTRASH_HARD_SAFETY_MODE=true

# Linux/Mac
export SMARTRASH_HARD_SAFETY_MODE=true
```

---

## 🚀 API Endpoints (Für Integrations)

### Detection:
```bash
curl -X POST http://localhost:8000/detect \
  -F "file=@image.jpg"
```

### Feedback:
```bash
curl -X POST http://localhost:8000/feedback/verify \
  -H "Content-Type: application/json" \
  -d '{
    "detection_id": 123,
    "feedback_type": "stimmt",
    "image_base64": "data:image/jpeg;base64,..."
  }'
```

### Learning Stats:
```bash
curl http://localhost:8000/learning/stats
curl http://localhost:8000/quality/error-trend
curl http://localhost:8000/compliance/report
```

---

## 📊 Produktive Monitorierung

### Tägliche Compliance-Checks:
```bash
# Compliance Status
curl http://localhost:8000/compliance/report

# System Audit
curl http://localhost:8000/system/audit

# Fehlerrate & Trend
curl http://localhost:8000/quality/error-trend
```

### Datencleaup (30-Tage Retention):
```bash
curl -X POST http://localhost:8000/compliance/cleanup-data
```

---

## 🔍 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'fastapi'"
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Error: "No such file: yolox_s.pth"
Laden Sie das Model herunter:
- Quelle: https://github.com/Megvii-BaseDetection/YOLOX/releases
- Ziel: `C:\models\yolox_s.pth`
- Größe: ~540 MB

### Server lädt nicht?
```bash
# Auf Port-Konflikt prüfen
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # macOS/Linux

# Alternativen Ports:
python main.py --host 0.0.0.0 --port 8080
```

---

## 📱 Skalierung & Production

### Mit Uvicorn (für Production):
```bash
# Multi-Worker (nutzt alle CPU-Kerne)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 📚 Weitere Doku

- Strukturüberblick: `backend/README.md`
- Start-Hinweise: `backend/start.bat` oder `backend/start.ps1`

### Mit Gunicorn (Linux/Mac):
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

### Mit Docker (optional):
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

---

## 📚 Weitere Ressourcen

- **API Docs**: http://localhost:8000/docs (interaktiv)
- **Feedback Format**: Siehe `/feedback/verify` Endpoint
- **Dataset Export**: Unter `/learning/export-dataset`
- **Compliance Report**: Unter `/compliance/report`

---

## ✅ System-Checklist für Production

- [ ] Python 3.8+ installiert
- [ ] YOLOX Model heruntergeladen (`C:\models\yolox_s.pth`)
- [ ] Dependencies installiert (`pip install -r requirements.txt`)
- [ ] Dashboard öffnet sich unter `http://localhost:8000/dashboard`
- [ ] Erste Detektionen funktionieren (Test-Bild hochladen)
- [ ] Feedback speichert sich (Stimmt/Stimmt-nicht)
- [ ] Compliance-Report zeigt Score=100% (✅ Alles OK)

---

## 🎯 Was ist gebaut?

✅ **Self-Learning AI** - Verbessert sich mit Feedback
✅ **Hard-Safety Mode** - Unsichere Fälle nicht auto-sortieren
✅ **Web-Dashboard** - Moderne Live-Bedienoberfläche
✅ **Compliance Guard** - Keine versteckten Kosten/Daten
✅ **Quality Control** - Adaptive Threshold Adjustments
✅ **Dataset Export** - YOLO-Format für Retraining

🚀 **Ready for Production!**

---

*Fragen? Siehe API Docs oder Dashboard Help-Button*
