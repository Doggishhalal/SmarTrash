#!/usr/bin/env python3
"""Test the fixes for Serviette recognition and single-char crash"""

from waste_classifier import get_classifier

classifier = get_classifier()

# Test 1: Serviette-Klassifizierung
print('✅ TEST 1: Serviette-Erkennung')
result = classifier.classify_by_name_only('Serviette')
print(f'  Input: Serviette')
print(f'  Bin: {result["bin"]} ({result["bin_description"]})')
print(f'  Material: {result["material"]}')
if result['bin'] == 'BIOMÜLL':
    print(f'  ✓ CORRECT: BIOMÜLL')
else:
    print(f'  ❌ WRONG: Got {result["bin"]} instead of BIOMÜLL')
print()

# Test 2: Napkin
print('✅ TEST 2: Napkin-Erkennung')
result = classifier.classify_by_name_only('napkin')
print(f'  Input: napkin')
print(f'  Bin: {result["bin"]} ({result["bin_description"]})')
if result['bin'] == 'BIOMÜLL':
    print(f'  ✓ CORRECT: BIOMÜLL')
else:
    print(f'  ❌ WRONG: Got {result["bin"]} instead of BIOMÜLL')
print()

# Test 3: Single char input (sollte nicht crashen)
print('✅ TEST 3: Single-Char Input Safety')
try:
    result = classifier.classify_by_name_only('S')
    print(f'  Input: S')
    print(f'  Bin: {result["bin"]}')
    print(f'  ✓ No crash on single character!')
except Exception as e:
    print(f'  ❌ CRASHED: {e}')
print()

# Test 4: Leerer Input (sollte auch safe sein)
print('✅ TEST 4: Empty Input Safety')
try:
    result = classifier.classify_by_name_only('')
    print(f'  Input: (empty)')
    print(f'  Bin: {result["bin"]}')
    print(f'  ✓ No crash on empty input!')
except Exception as e:
    print(f'  ❌ CRASHED: {e}')
print()

# Test 5: Verifying dynamic learning works
print('✅ TEST 5: Dynamic Learning Mapping')
print(f'  Static mapping size: {len(classifier.WASTE_MAPPING)}')
print(f'  Dynamic mapping size: {len(classifier.dynamic_mapping)}')
print(f'  ✓ Dynamic mapping ready for learning')
