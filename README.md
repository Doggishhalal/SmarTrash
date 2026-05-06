# 🗑️ SmarTrash - AI-Gestützte Intelligente Abfallkassifizierung

> **⚡ Schnellstart:** Doppelklick auf `backend/start.bat` → Dashboard unter `http://localhost:8000/dashboard`
>
> **🎯 Mit VS Code?** Drücke **F5** → fertig! ([Details](VSCODE_QUICKSTART.md))

---

## 📋 Was ist SmarTrash?

**SmarTrash** ist eine **Production-Ready AI-Lösung** zur automatischen Klassifizierung von Abfall mit kontinuierlichem Selbstlernen.

### Das System kann:
- ✅ Abfall in 4 Kategorien klassifizieren (RESTMÜLL, BIOMÜLL, PAPIER, PLASTIK)
- ✅ Sich selbst durch Feedback verbessern (Error-Rate sinkt mit mehr Daten)
- ✅ Unsichere Fälle erkennen (Hard-Safety: nie blindes Auto-Sorting)
- ✅ Adaptive Qualität beibehalten (adjustiert Thresholds automatisch)
- ✅ Transparent berichten (Compliance, Privacy, Audit Logs)
- ✅ Vollständig kostenlos (keine bezahlten APIs)

---

## 🚀 Quick Start

### Option 1: VS Code (empfohlen für Entwicklung)
```
1. Öffne Ordner in VS Code
2. Drücke F5
3. Browser: http://localhost:8000/dashboard
```
**→ Siehe [VSCODE_QUICKSTART.md](VSCODE_QUICKSTART.md)**

### Option 2: Batch Script (einfach)
```
1. Doppelklick: backend/start.bat
2. Browser: http://localhost:8000/dashboard
```

### Option 3: PowerShell
```powershell
cd backend
.\setup.ps1
```

### Option 4: Manuell
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**Fertig!** 🎉 Dashboard ist bereit.

---

## 📚 Dokumentation

| Datei | Für Wen | Lesen Wenn |
|-------|---------|-----------|
| [backend/QUICK_START.md](backend/QUICK_START.md) | Anfänger | Du möchtest in 5 Min starten |
| [backend/INSTALLATION.md](backend/INSTALLATION.md) | Developer | Du installierst manuell / hast Probleme |
| [SMARTRASH_README.md](SMARTRASH_README.md) | Techie | Du möchtest alles verstehen |
| [DELIVERABLES.md](DELIVERABLES.md) | Manager | Du möchtest wissen was fertig ist |
| [backend/COMPLETION.md](backend/COMPLETION.md) | QA | Du möchtest die Checklist sehen |

---

## 🎯 Features

### Dashboard (Web UI)
- 📷 **Live Kamera-Stream** oder Bild-Upload
- 🎯 **Detektions-Visualisierung** mit Bounding Boxes
- 📝 **Feedback Interface**: "Stimmt!" / "Stimmt nicht" Buttons
- 📊 **Charts**: Error-Rate Trend, Quality Mode, Stats
- ✅ **Compliance Status**: Score %, Issues, Fixes
- 📋 **Review Queue**: Cases die Feedback brauchen

### AI System
- 🤖 **YOLOX Detection**: 80 COCO-Klassen
- 🗂️ **Classification**: Zu 4 Abfall-Kategorien
- 📚 **Self-Learning**: Verbessert sich durch Feedback
- 🛡️ **Hard-Safety**: Unsicher = Manual Review (nie Auto-Sort)
- 📈 **Adaptive Quality**: Passt Thresholds an Error-Rate an

### REST API
- `POST /detect` - Bild analysieren
- `POST /feedback/verify` - Feedback geben
- `GET /learning/review-queue` - Manual Cases
- `GET /learning/export-dataset` - YOLO Dataset
- `GET /quality/error-trend` - Analytics
- `GET /compliance/report` - Compliance Status
- `GET /system/audit` - Production Check

### Safety & Compliance
- ✅ **No Hidden Costs**: Scannt auf Paid APIs
- ✅ **Privacy**: Person-Bilder nicht gespeichert, 30d Auto-Cleanup
- ✅ **Audit Logs**: Jede Entscheidung trackt
- ✅ **Hard-Safety Mode**: Lieber Manual als Fehler
- ✅ **Transparent Reporting**: Alle Metriken verfügbar

---

## 📁 Projekt-Struktur

```
SmarTrash/
├── QUICK_START.md           ← 🚀 HIER ANFANGEN!
├── INSTALLATION.md          ← Detaillierte Installation
├── SMARTRASH_README.md      ← Komplett Dokumentation
├── DELIVERABLES.md          ← Was ist fertig?
│
└── backend/
    ├── start.bat            ← 🚀 SCHNELLSTART (Windows)
    ├── start.sh             ← 🚀 SCHNELLSTART (Linux/Mac)
    ├── setup.ps1            ← PowerShell Setup
    │
    ├── main.py              ← FastAPI Server
    ├── inference.py         ← Detection Pipeline
    ├── waste_classifier.py  ← Klassifizierung
    ├── learning_db.py       ← Feedback Storage
    ├── quality_controller.py ← Adaptive Thresholds
    ├── compliance_guard.py  ← No-Cost Guard
    │
    └── frontend/
        ├── index.html       ← Dashboard UI
        ├── dashboard.js     ← Interaktivität
        └── style.css        ← Styling
```

---

## 💡 Typischer Ablauf

```
1. Bild hochladen
   ↓
2. Detektionen sehen (mit Boxen + Confidence)
   ↓
3. Feedback geben: "Stimmt!" oder "Stimmt nicht"
   ↓
4. System speichert Bild zu korrekter Klasse
   ↓
5. Error-Rate sinkt (sichtbar in Chart)
   ↓
6. Nächste Bilder werden besser klassifiziert
   ↓
7. Nach 200+ Samples → Dataset exportieren → Retraining (optional)
```

---

## ⚙️ Anforderungen

- **Python 3.8+** → [Download](https://python.org)
- **YOLOX Model** (540 MB) → [Download](https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1_weights/yolox_s.pth)
  - Speichern unter: `C:\models\yolox_s.pth`

---

## 🔐 Compliance (wichtig!)

### Punkt 1: Keine versteckten Kosten ✅
- `compliance_guard.py` scannt alle Dependencies
- Nur gratis: Wikipedia, DBpedia, OpenFoodFacts
- Keine Cloud-APIs (OpenAI, Google, AWS)

### Punkt 2: Rechtliche Sicherheit ✅
- Person-Bilder **werden NICHT** gespeichert
- 30-Tage Auto-Cleanup (DSGVO-konform)
- Transparent Audit Logging
- Kein Dark Data

### Punkt 3: Sichere Sortierung ✅
- Hard-Safety Mode: Unsicher = MANUAL_CHECK_REQUIRED
- Batterien: Sofort Manual Review
- Quality Control: Adaptive Thresholds

---

## 🎓 Erste Schritte

### Installation (einmalig):
```bash
cd backend
./start.bat  # Windows
# oder
./start.sh   # macOS/Linux
```

### Verwendung (täglich):
1. Browser: `http://localhost:8000/dashboard`
2. Kamera starten oder Bild hochladen
3. Detektionen sehen
4. Feedback geben
5. Stats überwachen
6. Wiederholen!

### Nach 2 Wochen (Production):
```bash
# Dashboard Stats zeigen Error-Rate < 15%
curl http://localhost:8000/quality/error-trend

# Exportiere Dataset
curl http://localhost:8000/learning/export-dataset

# Optional: Neues Model trainieren (externe Tools)
```

---

## 🆘 Häufige Fragen

### Q: Wo fange ich an?
A: Lese [backend/QUICK_START.md](backend/QUICK_START.md) (2 Min) oder klick einfach `start.bat`

### Q: Warum "Hard-Safety"?
A: Lieber ein Fall zu viel Manuell checken als ein Fehler zu sortieren.

### Q: Welche Bin-Kategorien?
A: RESTMÜLL, BIOMÜLL, PAPIER, PLASTIK (4 Bins)

### Q: Kostet das etwas?
A: Nein! 100% kostenlos, gratis APIs, Open-Source Dependencies

### Q: Ist es legally safe?
A: Ja! Keine Person-Daten, lokal processed, transparent audit logs

### Q: Kann es lernen?
A: Ja! Error-Rate sinkt mit jedem Feedback (selbstlernend)

---

## 📊 Monitoring

```bash
# Alle wichtigen URLs:
http://localhost:8000                      # API Root
http://localhost:8000/dashboard            # Dashboard UI
http://localhost:8000/docs                 # API Dokumentation
http://localhost:8000/health               # Health Status
http://localhost:8000/quality/error-trend  # Error Analytics
http://localhost:8000/compliance/report    # Compliance Score
http://localhost:8000/system/audit         # Production-Ready?
```

---

## ✅ Status

```
✅ PRODUCTION READY

✅ AI Detection System
✅ Web Dashboard
✅ REST API (30+ Endpoints)
✅ Self-Learning Loop
✅ Quality Control
✅ Safety & Compliance
✅ Documentation
✅ Installation Scripts

Ready to deploy! 🚀
```

---

## 📞 Support

- **Schnell Start**: [backend/QUICK_START.md](backend/QUICK_START.md)
- **Installation**: [backend/INSTALLATION.md](backend/INSTALLATION.md)
- **Full Docs**: [SMARTRASH_README.md](SMARTRASH_README.md)
- **API Docs**: http://localhost:8000/docs
- **Was fertig?**: [DELIVERABLES.md](DELIVERABLES.md)

---

## 🚀 Start Now!

```bash
# Windows
Double-Click: backend/start.bat

# PowerShell
cd backend
.\setup.ps1

# Terminal
cd backend
python main.py
```

**Dann öffnen:** `http://localhost:8000/dashboard`

---

*✨ SmarTrash v2.0 - AI-Powered Waste Classification*
*Status: ✅ PRODUCTION READY*
*Last Updated: March 4, 2026*
