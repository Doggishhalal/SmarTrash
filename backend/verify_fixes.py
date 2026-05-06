#!/usr/bin/env python3
"""Quick verification that fixes work"""

import sys

print('✅ Testing app.py imports...')

try:
    from waste_classifier import get_classifier
    print('✓ waste_classifier imported')
    
    classifier = get_classifier()
    print('✓ Classifier initialized')
    
    # Quick test
    result = classifier.classify_by_name_only('Serviette')
    assert result['bin'] == 'BIOMÜLL', f'Expected BIOMÜLL but got {result["bin"]}'
    print(f'✓ Serviette → {result["bin_description"]}')
    
    # Test napkin too
    result = classifier.classify_by_name_only('napkin')
    assert result['bin'] == 'BIOMÜLL', f'Expected BIOMÜLL but got {result["bin"]}'
    print(f'✓ napkin → {result["bin_description"]}')
    
    print()
    print('✅ ALL CHECKS PASSED - App ready to use!')
    sys.exit(0)
except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
