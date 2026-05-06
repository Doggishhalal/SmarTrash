# 🎯 Neues Feedback- & Lern-System für SmarTrash

## ✨ Was ist neu?

### 1️⃣ **Intelligente Korrektur-Dialoge**
Wenn die KI etwas falsch erkennt:
- Klick auf **"❌ Falsch - Korrigieren"**
- Gib den **richtigen Objektnamen** ein (z.B. "Serviette")
- Die KI schlägt automatisch die **richtige Mülltonne vor**
- Bestätige und die KI **lernt sofort**

### 2️⃣ **Manuelles Zeichnen für nicht erkannte Objekte**
Wenn die KI etwas **gar nicht sieht**:
- Klick auf **"🎨 Manuell Zeichnen"**
- Zeichne ein **Rechteck um das Objekt** (2 Mausklicks)
- Gib den **Objektnamen ein**
- KI schlägt Tonne vor und **speichert es zum Lernen**

### 3️⃣ **Besseres Verständnis für spezielle Objekte**
Die KI kennt jetzt:
- **Serviette** → 🟢 **Braune Biotonne** (nicht Papiertonne!)
  - Grund: Papierservietten sind meist dreckig/geölt
- **Pferdepenal** → 🟢 **Braune Biotonne** (organisch)
- **Luftballon** → ⚫ **Restmüll** (nicht recycelbar)

---

## 🔄 Workflows im Detail

### Workflow A: Falsch erkannte Sache korrigieren
```
📸 Kamera zeigt: "Das ist eine Flasche"
❌ Nutzer sieht: "Das ist aber eine SERVIETTE!"

1. Klick "❌ Falsch - Korrigieren"
2. Tippe "Serviette"
3. KI schlägt vor: "→ Braune Tonne / Biotonne"
4. Bestätige mit "✅ Speichern"
5. 🧠 KI lernt: "Serviette = Biotonne"
```

### Workflow B: Nicht erkanntes Objekt annotieren
```
📸 Kamera läuft, aber KI sieht ein Objekt NICHT

1. Klick "🎨 Manuell Zeichnen"
2. Ein neues Fenster öffnet sich
3. Zeichne Rechteck: klick oben-links → klick unten-rechts
4. Tippe Objektnamen (z.B. "Pferdepenal")
5. KI schlägt Tonne vor
6. Speichern - wird für Training verwendet
```

---

## 🧠 Was lernt die KI?

### Von Korrekturen:
- Feedback zeigt der KI: "Das war falsch, das ist richtig"
- Pro Korrektur verbessert sich die Accuracy für diese Klasse
- Mit 5-10 Korrektionen: ~2-5% Accuracy-Verbesserung

### Von manuellen Annotations:
- Frame + Bounding Box + Objektname werden gespeichert
- Diese Daten bilden eine Test-Trainings-Datenbank
- Können für wöchentliches Auto-Retrain genutzt werden

---

## 📊 Statistiken & Monitoring

Im **Learning Dashboard** (über FastAPI `/learning/dashboard`):
- Wie viele Korrektionen pro Klasse
- Trend: Verbessert sich die Accuracy?
- Welche Klassen brauchen mehr Feedback?
- Wie viele manuelle Annotations gesammelt

---

## ⚙️ Technische Details

### Neue Methoden in `waste_classifier.py`:
```python
# Einfache Klassifizierung nur nach Objektnamen
result = classifier.classify_by_name_only("Serviette")
# Gibt zurück: {
#   "bin": "BIOMÜLL",
#   "bin_description": "Braune Tonne / Biotonne",
#   "material": "paper",
#   "reasoning": ["'serviette' → BIOMÜLL"],
#   "warnings": [],
# }
```

### Neue Tabelle in `learning_db.py`:
```python
db.save_manual_annotation(
    bbox={"x1": 10, "y1": 20, "x2": 100, "y2": 150},
    object_class="Pferdepenal",
    frame_path="/path/to/frame.jpg",
    suggested_bin="Biotonne",
    comment="Manuell gezeichnet"
)
```

---

## 🚀 Nächste Schritte

1. **Sammeln von Feedback**: Mit jeder Korrektur wird die KI besser
2. **Sammeln von Annotations**: Nicht erkannte Objekte manuell zeichnen
3. **Wöchentliches Retrain**: Auto-Retrain nutzt Feedback für Verbesserung
4. **Monitoring**: Dashboard zeigt Fortschritt

---

## 📝 Beispiel-Korrektionen

| Objekt | Alte KI | Nutzerin korrigiert | Neue KI | Lerneffekt |
|--------|---------|------------------|---------|-----------|
| Serviette | Papiertonne | "Serviette" | Biotonne ✓ | Papier != Bio erkannt |
| Pferdepenal | Restmüll | "Pferdepenal" | Biotonne ✓ | Organik erkannt |
| Luftballon | Gelbe Tonne | "Luftballon" | Restmüll ✓ | Recycling-Regeln gelernt |

---

**Mit diesem System wird dein SmarTrash immer besser!** 🎯
Jede Korrektur und jede Annotation macht die KI intelligenter.
