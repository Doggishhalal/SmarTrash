#!/usr/bin/env python3
"""Test neue Features: Serviette, Pferdepenal, Luftballon"""

from waste_classifier import get_classifier
from learning_db import get_db

print("[TEST] Neue Klassifizierungen...")

classifier = get_classifier()

# Test 1: Serviette
result = classifier.classify_by_name_only('Serviette')
assert result['bin'] == 'BIOMÜLL', f"Serviette sollte Biotonne sein, ist aber {result['bin']}"
print('✅ Test 1 passed: Serviette → Biotonne')

# Test 2: Pferdepenal
result = classifier.classify_by_name_only('Pferdepenal')
assert result['bin'] == 'BIOMÜLL', f"Pferdepenal sollte Biotonne sein, ist aber {result['bin']}"
print('✅ Test 2 passed: Pferdepenal → Biotonne')

# Test 3: Luftballon
result = classifier.classify_by_name_only('Luftballon')
assert result['bin'] == 'RESTMÜLL', f"Luftballon sollte Restmüll sein, ist aber {result['bin']}"
print('✅ Test 3 passed: Luftballon → Restmüll')

print("\n[TEST] Manuelle Annotations...")

db = get_db()

# Test 4: Speichere manuelle Annotation
ann_id = db.save_manual_annotation(
    bbox={"x1": 10, "y1": 20, "x2": 100, "y2": 150},
    object_class="Serviette",
    frame_path="/tmp/test.jpg",
    suggested_bin="Biotonne",
    comment="Test-Annotation"
)
assert ann_id is not None, "Annotation sollte ID haben"
print(f'✅ Test 4 passed: Manuelle Annotation gespeichert (ID: {ann_id})')

# Test 5: Bestätigung
db.confirm_manual_annotation(ann_id)
annotations = db.get_manual_annotations(only_confirmed=True)
assert len(annotations) > 0, "Sollte mindestens eine bestätigte Annotation geben"
assert annotations[0]['object_class'] == 'Serviette', "Falsche Klasse"
print(f'✅ Test 5 passed: Annotation bestätigt und abgerufen')

# Test 6: Statistiken
stats = db.get_manual_annotations_statistics()
assert stats['total_annotations'] > 0, "Sollte Annotations haben"
assert 'Serviette' in stats['top_classes'], "Serviette sollte in Top Classes sein"
print(f'✅ Test 6 passed: Annotation Statistics: {stats}')

print("\n" + "="*60)
print("✅✅ ALLE TESTS BESTANDEN! ✅✅")
print("="*60)
print("\nNEUE FEATURES FUNKTIONIEREN:")
print("  ✓ Serviette → Biotonne")
print("  ✓ Pferdepenal → Biotonne")
print("  ✓ Luftballon → Restmüll")
print("  ✓ Manuelle Annotations speichern & laden")
print("  ✓ Annotations-Bestätigung")
print("  ✓ Statistiken")
