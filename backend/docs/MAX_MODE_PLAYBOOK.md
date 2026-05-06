# Max-Mode Playbook (Ohne Modelltraining)

Dieses Dokument beschreibt den maximalen Betriebsmodus fuer bessere Ergebnisse, Performance und stabile Projektstruktur.

## Zielbild

- Hohe Praezision durch konservative Ausgabe bei riskanten Klassen
- Breiter Wissensstand durch Seed-Import und lokalen Wissensindex
- Gute Laufzeit durch Caching, DB-Indizes und Bulk-Schreibvorgaenge

## 1) Wissen aufbauen

1. Seed-Import ausfuehren:
   - `POST /learning/knowledge/import?max_terms=200&allow_live_fetch=false`
2. Lernstand pruefen:
   - `GET /learning/stats`
3. Risikoklassen pruefen:
   - `GET /learning/risky-classes`

## 2) Laufzeitregeln (strikter Modus)

- Riskante Klassen werden strenger gefiltert (hoehere effektive Schwellen)
- TTA-Konsens wird bei riskanten Klassen haerter bewertet
- Hinweise wie `contains_battery` und `hazardous_hint` erhoehen die Entscheidungsschwelle

## 3) Performance-Hinweise

- Risk-Policy nutzt TTL-Cache (kein voller DB-Read pro Bild)
- Seed-Import schreibt Objektwissen als Bulk-Upsert
- SQLite nutzt Indizes auf Feedback-, Detection- und Audit-Schluesseln

## 4) Empfohlener Betriebsablauf

1. Server starten
2. Seed-Import einmalig ausfuehren
3. Reale Bilder verarbeiten
4. Unsichere Faelle ueber `/feedback/verify` bestaetigen
5. Regelmaessig `GET /learning/stats` und `GET /learning/risky-classes` beobachten

## 5) Validierung nach Aenderungen

- `python -m py_compile inference.py learning_db.py web_knowledge.py main.py`
- `python tests/smoke_test.py`
- `python tests/test_waste_sorting.py`

## 6) Grenzen ohne Training

Ohne Retraining verbessert sich vor allem Entscheidungslogik und Wissensnutzung.
Die visuelle Erkennung bleibt durch die Modellgewichte begrenzt.
