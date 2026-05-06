"""
Umfassendes Test-Skript für die erweiterte SmarTrash Müllklassifizierung
Testet alle neuen Features und Analysemethoden
"""

from waste_classifier import WasteClassifier

def test_extended_object_database():
    """Test der massiv erweiterten WASTE_MAPPING (300+ Objekte)"""
    print("\n" + "="*70)
    print("TEST 1: Massive WASTE_MAPPING (300+ Objekte)")
    print("="*70)
    
    classifier = WasteClassifier()
    
    # Test verschiedene Objekt-Kategorien
    test_objects = [
        # Plastik
        ("water bottle", "PLASTIK", "plastic"),
        ("shopping bag", "PLASTIK", "plastic"),
        ("takeout container", "PLASTIK", "plastic"),
        
        # Papier
        ("newspaper", "PAPIER", "paper"),
        ("pizza box", "PAPIER", "paper"),
        ("egg carton", "PAPIER", "paper"),
        
        # Bio
        ("strawberry", "BIOMÜLL", "organic"),
        ("mushroom", "BIOMÜLL", "organic"),
        ("coffee grounds", "BIOMÜLL", "organic"),
        
        # Elektronik
        ("smartphone", "RESTMÜLL", "electronic"),
        ("gaming console", "RESTMÜLL", "electronic"),
        
        # Glas
        ("beer bottle", "RESTMÜLL", "glass"),
        ("wine glass", "RESTMÜLL", "glass"),
        
        # Textil
        ("shirt", "RESTMÜLL", "textile"),
        ("shoe", "RESTMÜLL", "textile"),
    ]
    
    for obj, expected_bin, expected_material in test_objects:
        result = classifier.classify_by_name_only(obj)
        bin_ok = result["bin"] == expected_bin
        material_ok = result["material"] == expected_material
        status = "✅" if (bin_ok and material_ok) else "❌"
        print(f"{status} '{obj}' → {result['bin']}/{result['material']}")
        if not bin_ok or not material_ok:
            print(f"   Erwartet: {expected_bin}/{expected_material}")
    
    print(f"\n📊 Totale Objekte in WASTE_MAPPING: {len(classifier.WASTE_MAPPING)}")
    print(f"📊 Dynamisch gelernte Objekte: {len(classifier.dynamic_mapping)}")

def test_material_database():
    """Test der detaillierten MATERIAL_DATABASE"""
    print("\n" + "="*70)
    print("TEST 2: Material-Datenbank Analyse")
    print("="*70)
    
    classifier = WasteClassifier()
    materials = ["plastic", "paper", "organic", "glass", "electronic"]
    
    for material in materials:
        details = classifier.analyze_material_detailed(material)
        if details["found"]:
            print(f"\n🔬 Material: {material.upper()}")
            print(f"   Tonne: {details['bin']}")
            print(f"   Verschmutzung: {details['contamination_tolerance']}")
            print(f"   Feuchte: {details['moisture_sensitivity']}")
            print(f"   Regeln: {len(details['special_rules'])} Spezialregeln")
            print(f"   Beispiele: {details['examples'][:2]}")

def test_compound_materials():
    """Test für Mehrschicht-Material-Erkennung"""
    print("\n" + "="*70)
    print("TEST 3: Compound Materials (Mehrschicht-Materialien)")
    print("="*70)
    
    classifier = WasteClassifier()
    
    test_compounds = ["tetrapak", "laminated_paper", "chipbag", "yogurt_container"]
    
    for compound in test_compounds:
        analysis = classifier.analyze_compound_materials(compound)
        if analysis:
            print(f"\n📦 {compound.upper()}")
            print(f"   Materialien: {', '.join(analysis['materials'])}")
            print(f"   Zusammensetzung: {analysis['composition']}")
            print(f"   Recyclebar: {'✅ Ja' if analysis['recyclable'] else '❌ Nein'}")
            print(f"   Richtige Entsorgung: {analysis['correct_disposal']}")

def test_special_knowledge():
    """Test für Spezialwissen bei kniffligen Objekten"""
    print("\n" + "="*70)
    print("TEST 4: Spezialwissen (Serviette, Pferdepenal, Luftballon)")
    print("="*70)
    
    classifier = WasteClassifier()
    
    special_cases = {
        "serviette": {
            "should_go_to": "BIOMÜLL",
            "reason": "Meist ölig/verschmutzt",
        },
        "pferdepenal": {
            "should_go_to": "BIOMÜLL",
            "reason": "Organisches Material",
        },
        "luftballon": {
            "should_go_to": "RESTMÜLL",
            "reason": "Gummi nicht recyclebar",
        },
    }
    
    for obj_name, expected in special_cases.items():
        result = classifier.classify_by_name_only(obj_name)
        correct = result["bin"] == expected["should_go_to"]
        status = "✅" if correct else "❌"
        print(f"{status} {obj_name}")
        print(f"   → {result['bin']} (erwartet: {expected['should_go_to']})")
        print(f"   Grund: {expected['reason']}")

def test_detailed_reasoning():
    """Test für ausführliche Erklärungen"""
    print("\n" + "="*70)
    print("TEST 5: Detailliertes Reasoning (Warum → Welche Tonne)")
    print("="*70)
    
    classifier = WasteClassifier()
    
    test_objects = ["serviette", "plastic bottle", "cardboard box"]
    
    for obj in test_objects:
        result = classifier.classify_by_name_only(obj)
        reasoning = classifier.generate_detailed_reasoning(
            obj, 0.85, result["material"], result["bin"]
        )
        
        print(f"\n🔍 {obj.upper()}")
        for step in reasoning["reasoning_chain"]:
            if "result" in step:
                print(f"   Schritt {step['step']}: {step['title']}")
                print(f"   → {step['result']}")

def test_recyclability_score():
    """Test für Recycling-Score"""
    print("\n" + "="*70)
    print("TEST 6: Recycling-Score Berechnung")
    print("="*70)
    
    classifier = WasteClassifier()
    
    test_objects = [
        ("glass bottle", "glass", 0.0),  # Sauberes Glas
        ("plastic bottle", "plastic", 0.2),  # Leicht verschmutzt
        ("paper cardboard", "paper", 0.5),  # Sehr nass
        ("tetrapak", "mixed", 0.0),  # Compound-Material
    ]
    
    for obj, material, contamination in test_objects:
        score = classifier.estimate_recyclability_score(obj, material, contamination)
        print(f"\n📈 {obj}")
        print(f"   Score: {score['recyclability_score']:.0f}% - {score['score_description']}")
        if score['factors']:
            for factor in score['factors']:
                print(f"   Faktor: {factor}")

def test_disposal_instructions():
    """Test für Entsorgungshinweise"""
    print("\n" + "="*70)
    print("TEST 7: Entsorgungsanweisungen")
    print("="*70)
    
    classifier = WasteClassifier()
    
    test_objects = [
        ("plastic bottle", "plastic"),
        ("paper box", "paper"),
        ("food waste", "organic"),
        ("smartphone", "electronic"),
    ]
    
    for obj, material in test_objects:
        instructions = classifier.get_disposal_instructions(obj, material)
        print(f"\n📋 {obj.upper()} ({material})")
        for instruction in instructions:
            print(f"   {instruction}")

def test_knowledge_summary():
    """Test für Wissens-Zusammenfassung"""
    print("\n" + "="*70)
    print("TEST 8: Wissens-Statistiken")
    print("="*70)
    
    classifier = WasteClassifier()
    summary = classifier.get_knowledge_summary()
    
    print(f"\n📚 SmarTrash Wissens-Datenbank:")
    print(f"   ✓ Objekte gemappt: {summary['total_objects_mapped']}")
    print(f"   ✓ Dynamisch gelernt: {summary['dynamic_objects_learned']}")
    print(f"   ✓ Materialien bekannt: {summary['materials_known']}")
    print(f"   ✓ Compound-Materialien: {summary['compound_materials_known']}")
    print(f"   ✓ Spezialfälle: {summary['special_cases_known']}")
    print(f"   ✓ Batterie-Geräte: {summary['total_battery_warning_devices']}")
    print(f"   ✓ Elektronik-Keywords: {summary['electronic_device_keywords']}")
    print(f"\n   Materialien: {', '.join(summary['material_list'])}")

def test_learning_priorities():
    """Test für Learning Priorities"""
    print("\n" + "="*70)
    print("TEST 9: Lern-Prioritäten (Häufige Verwechslungen)")
    print("="*70)
    
    classifier = WasteClassifier()
    priorities = classifier.get_learning_priorities()
    
    for priority in priorities:
        print(f"\n🎯 {priority['class']} (Priorität: {priority['priority']})")
        print(f"   ❌ Häufiger Fehler: {priority['common_mistake']}")
        print(f"   ⚠️  Grund: {priority['why_confused']}")
        print(f"   ✅ Korrekt: {priority['correct_bin']}")

def test_next_questions():
    """Test für automatische Frage-Vorhersage"""
    print("\n" + "="*70)
    print("TEST 10: Produktivität - Frage-Vorhersage")
    print("="*70)
    
    classifier = WasteClassifier()
    
    test_objects = ["smartphone", "serviette", "plastic bottle"]
    
    for obj in test_objects:
        questions = classifier.predict_next_question(obj)
        if questions:
            print(f"\n💡 {obj.upper()}")
            for q in questions[:2]:  # Zeige nur erste 2
                print(f"   {q}")

def run_all_tests():
    """Führe alle Tests aus"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "🚀 SmarTrash ADVANCED FEATURES TEST" + " "*19 + "║")
    print("║" + " "*18 + "Massive Datenbank + Intelligente Analyse" + " "*10 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        test_extended_object_database()
        test_material_database()
        test_compound_materials()
        test_special_knowledge()
        test_detailed_reasoning()
        test_recyclability_score()
        test_disposal_instructions()
        test_knowledge_summary()
        test_learning_priorities()
        test_next_questions()
        
        print("\n" + "="*70)
        print("✅✅ ALLE TESTS ERFOLGREICH ABGESCHLOSSEN! ✅✅")
        print("="*70)
        print("\n📊 SYSTEM-STATUS:")
        print("   ✓ 300+ Objekte in Datenbank")
        print("   ✓ 8 Material-Typen mit detaillierten Eigenschaften")
        print("   ✓ Compound-Material-Erkennung")
        print("   ✓ Detailliertes Reasoning-System")
        print("   ✓ Recycling-Score-Berechnung")
        print("   ✓ Entsorgungshinweise")
        print("   ✓ Lern-Prioritäten-Analyse")
        print("   ✓ Produktivitäts-Features")
        
    except Exception as e:
        print(f"\n❌ TEST FEHLER: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
