# 🚀 SmarTrash - Intelligentes Müllklassifizierungssystem (Advanced)

## 📊 System-Übersicht

Eine **vollständig erweiterte AI-Müllklassifizierung** mit:
- **429 Objekte** in der Datenbank (vorher: 80)
- **8 Material-Typen** mit detaillierten Eigenschaften
- **Intelligente Fallback-Logik** für unbekannte Objekte
- **Compound-Material-Erkennung** (z.B. Tetrapak)
- **Detailliertes Reasoning-System** (WARUM geht etwas wohin?)
- **Recycling-Score-Berechnung** (0-100%)
- **Produktivitäts-Features** für kontinuierliches Lernen

---

## 🎯 Was wurde implementiert?

### 1️⃣ **MASSIVE OBJECT DATABASE (429 Objekte)**

#### Kunststoff/Plastik (80+ Objekte)
- Verpackungen: Flaschen, Becher, Container, Boxen, Taschen
- Essensbesteck: Einwegbesteck (Gabel, Messer, Löffel)
- Haushalt: Zahnbürsten, Kämme, Bürsten
- Spielzeug: Puppen, Actionfiguren, Lego (kontaminiert)

#### Papier/Karton (60+ Objekte)
- Medien: Bücher, Magazine, Zeitungen
- Verpackungen: Kartons, Boxen, Pizza-Boxen, Eierkartone
- Hygiene: Toilettenpapier, Küchenpapier, Taschentücher
- Papierprodukte: Umschläge, Notizblöcke, Flyer

#### Biomüll (100+ Objekte)
- **Obst**: Äpfel, Orangen, Bananen, Erdbeeren, Weintrauben, Pflaumen, Zitrone, Ananas, Melone, Pfirsich
- **Gemüse**: Brokkoli, Karotte, Kartoffel, Tomate, Gurke, Paprika, Zwiebel, Knoblauch, Spinat, Salat
- **Essensreste**: Brot, Pizza, Pasta, Reis, Fleisch, Fisch, Hähnchen, Ei, Käse, Joghurt, Butter
- **Pflanzen**: Blüten, Blätter, Gras, Laub, Unkraut, Kompost, Gartenschnitt
- **Spezial**: Serviette (dreckig), Pferdepenal, Kaffee-Satz, Teeblätter

#### Glas (15+ Objekte)
- Flaschen: Bierflaschen, Weinflaschen, Gläser
- Verpackungen: Gläser, Vasen, Rahmen
- **HINWEIS**: Geht in Altglascontainer, nicht in Haustonne!

#### Elektronik (80+ Objekte)
- **Smartphones/Computer**: iPhone, Android, Laptop, Tablet, PC
- **Eingabegeräte**: Maus, Tastatur, Monitor, Drucker
- **Audio**: Speaker, Kopfhörer, Mikrofon, Radio
- **Haushaltsgeräte**: Toaster, Wasserkocher, Haartrockner, Mikrowelle
- **Gaming**: PlayStation, Xbox, Nintendo, Controller
- **Zubehör**: Kabel, Netzteil, Batterie, Charger
- **⚠️ BATTERIE-WARNUNG**: Viele enthalten Akkus!

#### Textil/Kleidung (30+ Objekte)
- Kleidung: Hemden, Hosen, Kleider, Jacken, Sweater
- Schuhe: Stiefel, Turnschuhe, Hausschuhe
- Accessoires: Socken, Handschuhe, Mütze, Schal, Hut
- Andere: Handtuch, Bettwäsche, Gardinen, Decke

#### Möbel/Großmüll (20+ Objekte)
- Sitzmöbel: Stühle, Sofas, Betten
- Schränke: Regale, Schränke, Kommoden, Nachttische
- Tische: Esstische, Schreibtische, Bänke
- **→ Sperrmüll Anmeldung erforderlich**

#### Sonstiges (40+ Objekte)
- Sportgeräte: Bälle, Schläger, Skateboards, Skier
- Werkzeuge: Schere, Hammer, Schraubendreher, Nägel
- Dinge: Regenschirm, Koffer, Rahmen, Spiegel
- **Spezial**: Luftballon, Tetrapak, Laminated Paper

---

### 2️⃣ **MATERIAL-DATENBANK (8 Materialtypen)**

Jedes Material hat detaillierte Eigenschaften:

```python
MATERIAL_DATABASE = {
    "plastic": {
        "types": ["PET", "HDPE", "PVC", "LDPE", "PP", "PS", "Other"],
        "contamination_tolerance": "low",
        "moisture_sensitivity": "low",
        "max_acceptable_contamination": 0.6,
    },
    "paper": {
        "contamination_tolerance": "low",
        "moisture_sensitivity": "very_high",  # ← KRITISCH!
        "max_acceptable_contamination": 0.4,
        "moisture_threshold": 0.3,
        "special_rules": ["Nass → Restmüll", "Fette → Restmüll"],
    },
    "organic": {
        "contamination_tolerance": "medium",
        "max_acceptable_contamination": 0.8,
        "special_rules": ["Verpackung entfernen!", "Fleisch OK", "Essensöl OK"],
    },
    # ... weitere 5 Materialtypen
}
```

---

### 3️⃣ **COMPOUND-MATERIAL-ERKENNUNG**

Intelligente Erkennung von **Mehrschicht-Materialien**:

| Objekt | Materialien | Recyclebar | Korrekte Entsorgung |
|--------|------------|-----------|-------------------|
| **Tetrapak** | Papier (75%) + Kunststoff (20%) + Alu (5%) | ❌ Nein | Restmüll / Spezialsammlung |
| **Chipbag** | Kunststoff + Aluminium | ❌ Nein | Restmüll |
| **Laminated Paper** | Papier + Kunststoff-Beschichtung | ❌ Nein | Restmüll |
| **Yoghurt-Behälter** | Kunststoff-Deckel + Papp-Becher | ✅ Ja (Wertstoff) | Wertstoff |

---

### 4️⃣ **SPEZIALWISSEN (5 Knifflige Fälle)**

```python
SPECIAL_KNOWLEDGE = {
    "serviette": {
        "key_issue": "Meist ölig/verschmutzt",
        "classification": "BIOMÜLL (nicht PAPIER!)",
        "reasoning": "Nicht sauberes Papier",
    },
    "pferdepenal": {
        "key_issue": "Tierkot",
        "classification": "BIOMÜLL",
        "reasoning": "Organisches Material, kompostierbar",
    },
    "luftballon": {
        "key_issue": "Gummi nicht abbaubar",
        "classification": "RESTMÜLL (nicht PLASTIK!)",
        "reasoning": "Kunststoff/Gummi nicht recyclebar",
    },
    # ... weitere 2 Fälle
}
```

---

### 5️⃣ **INTELLIGENTE ANALYSE-METHODEN**

#### `analyze_material_detailed(material: str) → Dict`
Liefert alle Infos über ein Material:
```python
classifier.analyze_material_detailed("plastic")
# Returns: {
#   "contamination_tolerance": "low",
#   "moisture_sensitivity": "low",
#   "special_rules": ["Zu dreckig → Restmüll", ...],
#   "examples": ["Getränkeflasche", "Behälter", ...]
# }
```

#### `analyze_compound_materials(object_name: str) → Optional[Dict]`
Erkennt Mehrschicht-Materialien:
```python
classifier.analyze_compound_materials("tetrapak")
# Returns: {
#   "is_compound": True,
#   "materials": ["paper", "plastic", "aluminum"],
#   "composition": "75% Papier, 20% Kunststoff, 5% Aluminium",
#   "correct_disposal": "Restmüll oder spezielle Tetrapak-Sammelstellen",
# }
```

#### `generate_detailed_reasoning(class_name, confidence, material, bin) → Dict`
Erklärt WARUM etwas in die Tonne gehört:
```python
result = classifier.generate_detailed_reasoning(
    "serviette", 0.85, "paper", "BIOMÜLL"
)
# Returns: Schritt-für-Schritt Erklärung
```

#### `estimate_recyclability_score(class_name, material, contamination_level) → Dict`
Berechnet wie recyclebar etwas ist (0-100%):
```python
score = classifier.estimate_recyclability_score("bottle", "plastic", 0.1)
# Returns: {
#   "recyclability_score": 54,
#   "score_description": "🟡 Mäßig recyclebar",
#   "factors": ["Verschmutzung: -10%"]
# }
```

#### `get_disposal_instructions(class_name, material) → List[str]`
Material-spezifische Entsorgungshinweise:
```python
instructions = classifier.get_disposal_instructions("bottle", "plastic")
# Returns: [
#   "✓ Kunststoff-Tipps:",
#   "  • Gut sichtbar: kleine Öffnungen zum Ausspülen",
#   "  • Lebensmittelreste vollständig entfernen",
#   "  • Deckel kann oben bleiben",
#   "  • Falten ist OK (spart Platz)"
# ]
```

#### `get_learning_priorities() → List[Dict]`
Zeigt **häufigste Verwechslungen** für fokussiertes Lernen:
```
🎯 Serviette (HIGH PRIORITY)
   ❌ Häufiger Fehler: → PAPIER statt BIOMÜLL
   ⚠️  Grund: Optisch sieht es wie Papier aus
   ✅ Korrekt: BIOMÜLL (wegen Öl/Verschmutzung)
```

#### `predict_next_question(class_name) → List[str]`
Vorhersage möglicher Fragen des Nutzers:
```python
questions = classifier.predict_next_question("smartphone")
# Returns: [
#   "❓ Hat das Gerät Batterien/Akkus?",
#   "❓ Kann ich die Batterie selbst rausnehmen?",
#   "❓ Wo sammelt man Elektroschrott?"
# ]
```

#### `get_knowledge_summary() → Dict`
Zeigt wie umfangreich die Datenbank ist:
```python
summary = classifier.get_knowledge_summary()
# Returns: {
#   "total_objects_mapped": 429,
#   "materials_known": 8,
#   "compound_materials_known": 4,
#   "special_cases_known": 5,
#   "battery_warning_devices": 9,
#   "electronic_device_keywords": 30
# }
```

---

## 📈 Test-Ergebnisse

```
✅ TEST 1: Massive WASTE_MAPPING (429 Objekte)
✅ TEST 2: Material-Datenbank Analyse (8 Materialtypen)
✅ TEST 3: Compound Materials (4 Mehrschicht-Typen)
✅ TEST 4: Spezialwissen (Serviette, Pferdepenal, Luftballon)
✅ TEST 5: Detailliertes Reasoning (Schritt-für-Schritt Erklärung)
✅ TEST 6: Recycling-Score Berechnung (0-100%)
✅ TEST 7: Entsorgungshinweise (Material-spezifisch)
✅ TEST 8: Wissens-Statistiken (Datenbank-Umfang)
✅ TEST 9: Lern-Prioritäten (Häufige Verwechslungen)
✅ TEST 10: Produktivität-Features (Frage-Vorhersage)
```

---

## 🔬 Beispiel: Wie funktioniert das System?

### Szenario: Nutzer hat Serviette gefunden

```python
# 1. Klassifizierung
result = classifier.classify_by_name_only("serviette")
# → BIOMÜLL (nicht PAPIER!)

# 2. Detailliertes Reasoning
reasoning = classifier.generate_detailed_reasoning(
    "serviette", 0.95, "paper", "BIOMÜLL"
)
# Zeigt: Schritt 1→2→3→4 + Spezialfall-Info

# 3. Entsorgungshinweise
instructions = classifier.get_disposal_instructions("serviette", "paper")
# → "Papier-Tipps: NICHT nass, ölig, verschmutzt"
# → "⚠️  Spezialfall: Serviette → BIOMÜLL wegen Öl/Verschmutzung"

# 4. Recycling-Score
score = classifier.estimate_recyclability_score("serviette", "paper", 0.3)
# → 50% (wegen Verschmutzung)

# 5. Häufige Verwechslungen
priorities = classifier.get_learning_priorities()
# → Zeigt: "Serviette ist HIGH PRIORITY Verwechslungskanditat"

# 6. Nächste Frage?
questions = classifier.predict_next_question("serviette")
# → "Funktioniert das auch wenn es nass ist?"
# → "Muss ich die Verpackung waschen?"
```

---

## 💡 Produktivitäts-Features

### 1. **Learning Priorities** (Fokussiertes Lernen)
Zeigt die 5 **häufigsten Verwechslungen**:
- Serviette → PAPIER statt BIOMÜLL (HIGH)
- Luftballon → PLASTIK statt RESTMÜLL (HIGH)
- Tetrapak → PAPIER statt RESTMÜLL (HIGH)
- Elektronik → RESTMÜLL statt WERTSTOFFHOF (CRITICAL)

### 2. **Fallback-Logik** (Intelligente Fehlerbehandlung)
Wenn KI unsicher ist:
1. Statisches Mapping prüfen
2. Dynamischer Cache prüfen
3. Name + Hinweise analysieren
4. Heuristiken anwenden
5. Konservativ zu RESTMÜLL fallback

### 3. **Compound-Material-Erkennung** (Mehrschicht)
Automatische Erkennung von:
- Tetrapak (75% Papier + 20% Kunststoff + 5% Alu)
- Chipbags (Kunststoff + Aluminium)
- Laminated Paper (Papier + Kunststoff)

### 4. **Frage-Vorhersage** (Nutzer-Unterstützung)
Vorhersage möglicher Fragen:
- "Hat das Gerät Batterien/Akkus?" → für Elektronik
- "Kann der Deckel mit rein?" → für Plastik
- "Kann ich die Verpackung auch mitwerfen?" → für Bio

---

## 🎓 Verwendungsbeispiele

### Einfache Klassifizierung
```python
from waste_classifier import WasteClassifier

classifier = WasteClassifier()
result = classifier.classify_by_name_only("water bottle")
print(result["bin"])  # PLASTIK
```

### Detaillierte Analyse
```python
# Material-Info
details = classifier.analyze_material_detailed("plastic")
print(details["contamination_tolerance"])  # "low"

# Entsorgungshinweise
instructions = classifier.get_disposal_instructions("bottle", "plastic")
for instr in instructions:
    print(instr)

# Recycling-Score
score = classifier.estimate_recyclability_score("bottle", "plastic", 0.2)
print(f"Score: {score['recyclability_score']}%")
```

### Spezialwissen abrufen
```python
# Learning Priorities
priorities = classifier.get_learning_priorities()
for p in priorities:
    print(f"{p['class']}: {p['common_mistake']}")

# Nächste Fragen vorhersagen
questions = classifier.predict_next_question("smartphone")
for q in questions:
    print(q)
```

---

## 📊 Statistiken

| Metrik | Wert |
|--------|------|
| Objekte in Datenbank | **429** |
| Material-Typen | **8** |
| Compound-Materialien | **4** |
| Spezialfälle | **5** |
| Batterie-Geräte | **9** |
| Elektronik-Keywords | **30** |
| Material-Token-Regeln | **64+** |
| Heuristische Gruppen | **6** |

---

## 🚀 Nächste Schritte

1. **Auto-Retrain**: Wöchentliches Neutraining mit User-Feedback
2. **Web-Daten Integration**: Online-Material-Datenbanken (Wikipedia, etc.)
3. **Regionale Anpassung**: Lokale Recycling-Regeln
4. **Visuelle Verbesserung**: Bild-basierte Material-Analyse
5. **Export-Features**: YOLO-Training mit Annotations

---

## ✨ Zusammenfassung

SmarTrash ist jetzt ein **intelligentes, selbstlernendes Müllklassifizierungssystem** mit:

✅ Umfangreicher Objektdatenbank (429 Objekte)
✅ Detaillierten Material-Eigenschaften  
✅ Intelligenter Fallback-Logik  
✅ Compound-Material-Erkennung  
✅ Ausführlichem Reasoning-System  
✅ Recycling-Score-Berechnung  
✅ Produktivitäts-Features für kontinuierliches Lernen  

**Die KI ist jetzt so smart wie möglich, um die beste mögliche Müllklassifizierung zu bieten!** 🌍♻️
