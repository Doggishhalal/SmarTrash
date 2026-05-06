# Codebase Index

Ziel: schnell finden, wo welche Funktion lebt, ohne Duplikate und mit klarer Wartungsstruktur.

## Runtime Kern (backend/)

- main.py: FastAPI API und Orchestrierung der Endpunkte
- app.py: Desktop GUI Anwendung
- inference.py: YOLOX Inferenz, Konsens, Schwellen, Risiko-Policy
- waste_classifier.py: Material/Bin-Regeln und Sicherheitsentscheidungen
- learning_db.py: SQLite Persistenz, Feedback, Kalibrierung, Audit
- web_knowledge.py: lokale und externe Wissenshints, Seed-Import
- quality_controller.py: adaptive Policy fuer Entscheidungsschwellen
- safety_config.py: zentrale Sicherheits- und Betriebsparameter
- detail_analyzer.py: Objektzustand (z. B. nass, verschmutzt)
- compliance_guard.py: No-Cost und Privacy Compliance
- sample_memory.py: Sample-Speicherung und Dataset-Export
- performance_tracker.py: Lern- und Performancemetriken

## Tests (backend/tests)

- smoke_test.py: schneller Import- und Initialisierungscheck
- test_waste_sorting.py: Funktionscheck der Sortierlogik
- test_api.py: aktueller API-Vertragstest (gegen laufenden Server)

## Skripte (backend/scripts)

- setup.ps1: Setup-Hilfe
- audit_project.py: Projekt-Audit (potenziell ungenutzte Symbole, Runtime-Pruefung)

## Doku (backend/docs)

- INSTALLATION.md: Installation und Start
- MAX_MODE_PLAYBOOK.md: Maximalmodus ohne Retraining
- CODEBASE_INDEX.md: diese Uebersicht

## Daten und Build-Artefakte

- smartrash_learning.db: lokale Laufzeitdatenbank
- __pycache__: Python Build-Cache (kann geloescht werden)
- venv/.venv: virtuelle Umgebungen

## Orientierung fuer schnelle Wartung

1. API-Fehler: main.py + learning_db.py + inference.py
2. Falsche Klassifikation: inference.py + waste_classifier.py + web_knowledge.py
3. Lernverhalten: learning_db.py + quality_controller.py
4. Sicherheitsfragen: safety_config.py + compliance_guard.py + waste_classifier.py
5. Desktop-Verhalten: app.py
