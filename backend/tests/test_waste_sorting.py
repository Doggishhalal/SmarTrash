"""
Waste Sorting Demo - Zeigt Mülltrennung Fähigkeiten
===================================================
Demonstriert wie das System Objekte in die richtige Tonne sortiert
"""
from waste_classifier import get_classifier

# Initialisiere Classifier
classifier = get_classifier()

print("\n" + "="*80)
print("♻️  SMARTRASH - INTELLIGENTE MÜLLTRENNUNG DEMO")
print("="*80)

# Zeige verfügbare Tonnen
print("\n🗑️  VERFÜGBARE MÜLLTONNEN:\n")
summary = classifier.get_bin_summary()
for bin_name, description in summary["bins"].items():
    print(f"  • {bin_name}: {description}")

print(f"\n📊 Insgesamt {summary['total_classes_mapped']} Objektklassen gemappt")
print(f"🔋 {len(summary['battery_warning_classes'])} Klassen mit Batteriewarnung")

# Demonstration mit verschiedenen Objekten
print("\n" + "="*80)
print("📋 BEISPIEL-KLASSIFIKATIONEN:")
print("="*80)

test_objects = [
    # Plastik
    {"class": "bottle", "confidence": 0.95, "condition": None, "description": "Saubere Plastikflasche"},
    {"class": "bottle", "confidence": 0.87, "condition": {"details": [{"type": "dirt", "severity": 0.7}]}, "description": "Stark verschmutzte Flasche"},
    
    # Papier
    {"class": "book", "confidence": 0.92, "condition": None, "description": "Trockenes Buch"},
    {"class": "book", "confidence": 0.88, "condition": {"details": [{"type": "wetness", "severity": 0.6}]}, "description": "Nasses Buch"},
    
    # Bio
    {"class": "banana", "confidence": 0.98, "condition": None, "description": "Bananenschale"},
    {"class": "apple", "confidence": 0.94, "condition": None, "description": "Apfelrest"},
    
    # Elektronik mit Batterien
    {"class": "cell phone", "confidence": 0.91, "condition": None, "description": "Handy"},
    {"class": "remote", "confidence": 0.85, "condition": None, "description": "Fernbedienung"},
    {"class": "laptop", "confidence": 0.89, "condition": None, "description": "Laptop"},
    
    # Glas
    {"class": "wine glass", "confidence": 0.93, "condition": None, "description": "Weinglas"},
]

for i, obj in enumerate(test_objects, 1):
    print(f"\n{'─'*80}")
    print(f"Test {i}: {obj['description']}")
    print(f"{'─'*80}")
    
    result = classifier.classify_waste(
        class_name=obj["class"],
        confidence=obj["confidence"],
        object_condition=obj["condition"]
    )
    
    # Ausgabe
    print(f"📦 Objekt: {obj['class']}")
    print(f"🎯 Confidence: {result['confidence']:.1%}")
    print(f"🗑️  Tonne: {result['bin']} ({result['bin_description']})")
    print(f"🔬 Material: {result['material']}")
    print(f"♻️  Recyclebar: {'Ja' if result['recyclable'] else 'Nein'}")
    
    if result.get("special_disposal"):
        print(f"⚠️  Spezialentsorgung: {result['special_disposal']}")
    
    print(f"\n💭 Begründung:")
    for reason in result["reasoning"]:
        print(f"   • {reason}")
    
    if result["warnings"]:
        print(f"\n⚠️  WARNUNGEN:")
        for warning in result["warnings"]:
            # Highlight Batteriewarnungen
            if "BATTERIE" in warning:
                print(f"   🔋 {warning}")
            else:
                print(f"   ⚠️  {warning}")
    
    if result["condition_affected_decision"]:
        print(f"\n🔄 ZUSTAND HAT ENTSCHEIDUNG GEÄNDERT!")

print("\n" + "="*80)
print("🎯 ZUSAMMENFASSUNG DER REGELN:")
print("="*80)

print("""
1. PLASTIK (Gelbe Tonne):
   ✅ Saubere Verpackungen, Flaschen, Kunststoff-Behälter
   ❌ Stark verschmutzte Verpackungen → Restmüll

2. PAPIER (Blaue Tonne):
   ✅ Trockenes Papier, Karton, Pappe
   ❌ Nasses oder verschmutztes Papier → Restmüll

3. BIOMÜLL (Braune Tonne):
   ✅ Essensreste, Obst, Gemüse (OHNE Verpackung!)
   ⚠️  Verpackung vorher entfernen!

4. RESTMÜLL (Schwarze Tonne):
   • Alles was nicht recyclebar ist
   • Verschmutzte Materialien
   • Standard-Fallback

SONDERENTSORGUNG:
🔋 ELEKTRONIK MIT BATTERIEN:
   • Handy, Laptop, Fernbedienung, Maus, etc.
   • ⚠️⚠️ IMMER vorher auf Batterien/Akkus prüfen!
   • Batterien separat entsorgen (Sammelstellen)
   • Gerät dann zum Elektroschrott / Wertstoffhof

🥃 GLAS:
   • Altglascontainer (nicht Haustonne!)
   • Nach Farbe sortieren

🪑 SPERRMÜLL:
   • Möbel, große Gegenstände
   • Anmeldung bei Gemeinde erforderlich
""")

print("="*80)
print("✅ Waste Sorting System vollständig getestet!")
print("🧠 System berücksichtigt: Material + Zustand + Spezialregeln")
print("🔋 Batteriewarnungen aktiv für sichere Entsorgung!")
print("="*80 + "\n")
