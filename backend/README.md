# Backend Struktur

Saubere Ordner:

- `docs/` → Dokumentation
- `scripts/` → Setup-Helfer (`setup.ps1`)
- `tests/` → Testskripte
- Root (`backend/`) → nur Runtime-Kern

## Python-Dateien im Root (alle werden genutzt)

### Core Runtime (v2.0)
- `app.py` → Desktop GUI Einstieg
- `main.py` → FastAPI Server Einstieg (API v2.1.0)
- `inference.py` → YOLOX Inferenzpipeline
- `waste_classifier.py` → Müllklassifikation/Regeln
- `web_knowledge.py` → Wissensanreicherung (lokal/web)
- `learning_db.py` → SQLite Learning/Feedback Speicher
- `quality_controller.py` → adaptive Qualitätsregeln
- `safety_config.py` → zentrale Sicherheits-/Feature-Config
- `sample_memory.py` → Bildspeicher/Export fürs Lernen
- `detail_analyzer.py` → Zustandsanalyse (Dreck/Nässe etc.)
- `compliance_guard.py` → Compliance-/No-Cost Prüfungen
- `performance_tracker.py` → Performance-Metriken (API)

### Enhancement Modules (v2.1 - NEW)
- `web_knowledge_enhanced.py` → **343 Objekt-Seeds von 5 Datensätzen** (COCO, TACO, Open Images, Roboflow, Wikidata)
- `framing_optimizer.py` → **Adaptive NMS, Multi-Scale Box Fusion, Quality Scoring**
- `recognition_profile.json` → zentrale YOLOX-L Qualitätskonfiguration mit TTA, Multi-Scale, Rescue-Pass und freien Datenquellen
- `recognition_profile.py` → lädt das aktive Erkennungsprofil und steuert die Inferenz-Features

## Start

- Desktop-App: `start.bat` oder `start.ps1`
- API-Server: `python main.py`

## Tests

- Smoke-Test: `python tests/smoke_test.py`
- API-Test (optional, Server muss laufen): `python tests/test_api.py`
- Sorting-Demo: `python tests/test_waste_sorting.py`

## Betriebsdoku

- Max-Mode (ohne Training): `docs/MAX_MODE_PLAYBOOK.md`
- Code-Index (Dateirollen + Zuständigkeiten): `docs/CODEBASE_INDEX.md`

## Wartung

- Audit-Skript (potenziell ungenutzte Symbole): `python scripts/audit_project.py`

## YOLOX Best-Mode

Das Projekt bleibt bewusst auf YOLOX für eine klare Lizenzlage.

Aktiviert sind standardmäßig:

- YOLOX-L als bevorzugter Modellpfad
- Test-Time-Augmentation
- Multi-Scale-Inferenz
- Flip-Augmentation
- Rescue-Pass für schwierige Bilder
- Output-Framing / Box-Optimierung
- Local-first Wissensanreicherung
- Kostenfreie öffentliche Datenquellen (COCO, TACO, Open Images, Roboflow Waste, Wikidata, OpenFoodFacts, OSM, Wikimedia)
- Auto-Optimierung und Feedback-Learning
