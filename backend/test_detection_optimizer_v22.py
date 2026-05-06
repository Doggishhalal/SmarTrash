#!/usr/bin/env python
"""
SmarTrash v2.2.0 - Detection Optimizer Validation
===================================================
Validiert dass all Detections:
- 60% Hard-Threshold erfüllen
- Multi-Layer Validation bestehen
- Geometrisch valid sind
- Keine Anomalien haben
"""

import json

from detection_optimizer import get_detection_optimizer


def test_basic_validation():
    """Test basic detection validation"""
    print("\n[Test 1] Basic Detection Validation")
    print("-" * 50)

    optimizer = get_detection_optimizer()

    # Test detections: mix of good and bad
    test_dets = [
        {
            "class": "bottle",
            "score": 0.85,
            "calibrated_confidence": 0.87,
            "bbox": [50, 50, 150, 250],
            "tta_support_count": 2
        },
        {
            "class": "battery",
            "score": 0.45,  # TOO LOW!
            "calibrated_confidence": 0.48,
            "bbox": [200, 100, 250, 150],
            "tta_support_count": 1
        },
        {
            "class": "plastic",
            "score": 0.72,
            "calibrated_confidence": 0.75,
            "bbox": [10, 10, 100, 100],  # Small box
            "tta_support_count": 1
        },
    ]

    valid, rejected = optimizer.validate_and_filter_detections(
        detections=test_dets,
        image_width=640,
        image_height=480,
        strict_mode=True
    )

    print(f"✓ Valid detections: {len(valid)}")
    for det in valid:
        print(f"  - {det['class']}: {det.get('confidence_final', 0.0):.1%} ✓")

    print(f"✗ Rejected: {len(rejected)}")
    for rej in rejected:
        print(f"  - {rej['detection']['class']}: {rej['reason']}")

    report = optimizer.generate_detection_report(valid, rejected)
    print(f"\n📊 Report: Pass rate {report['pass_rate']:.1%}, Avg confidence {report['avg_confidence_valid']:.1%}")
    return len(valid) >= 1 and len(rejected) >= 1


def test_class_specific_thresholds():
    """Test class-specific confidence requirements"""
    print("\n[Test 2] Class-Specific Thresholds")
    print("-" * 50)

    optimizer = get_detection_optimizer()

    test_dets = [
        {"class": "person", "score": 0.65, "bbox": [0, 0, 100, 200], "tta_support_count": 1},
        {"class": "cell phone", "score": 0.65, "bbox": [100, 100, 150, 180], "tta_support_count": 1},
        {"class": "smartwatch", "score": 0.64, "bbox": [320, 160, 370, 220], "tta_support_count": 1},
        {"class": "bottle", "score": 0.65, "bbox": [200, 200, 250, 350], "tta_support_count": 1},
    ]

    valid, rejected = optimizer.validate_and_filter_detections(
        detections=test_dets,
        image_width=640,
        image_height=480,
        strict_mode=True
    )

    print(f"✓ Valid: {len(valid)}")
    for det in valid:
        threshold = optimizer.class_adjustments.get(det['class'], 0.60)
        print(f"  - {det['class']}: {det.get('confidence_final', 0.0):.1%} (threshold: {threshold:.0%}) ✓")

    print(f"✗ Rejected: {len(rejected)}")
    for rej in rejected:
        class_name = rej['detection']['class']
        threshold = optimizer.class_adjustments.get(class_name, 0.60)
        print(f"  - {class_name}: Below class threshold {threshold:.0%}")

    # Handheld classes should pass >= 60% with valid geometry.
    cell_phone_valid = any(str(d.get("class", "")).lower() == "cell phone" for d in valid)
    smartwatch_valid = any(str(d.get("class", "")).lower() == "smartwatch" for d in valid)
    return cell_phone_valid and smartwatch_valid


def test_geometry_validation():
    """Test geometric anomaly detection"""
    print("\n[Test 3] Geometry & Anomaly Detection")
    print("-" * 50)

    optimizer = get_detection_optimizer()

    test_dets = [
        {"class": "bottle", "score": 0.88, "bbox": [50, 50, 150, 200], "tta_support_count": 1},
        {"class": "glass", "score": 0.85, "bbox": [5, 5, 8, 10], "tta_support_count": 1},  # TOO SMALL!
        {"class": "phone", "score": 0.90, "bbox": [100, 100, 150, 600], "tta_support_count": 1},  # EXTREME ASPECT RATIO!
        {"class": "cup", "score": 0.82, "bbox": [0, 0, 640, 480], "tta_support_count": 1},  # TOO LARGE!
    ]

    valid, rejected = optimizer.validate_and_filter_detections(
        detections=test_dets,
        image_width=640,
        image_height=480,
        strict_mode=True
    )

    print(f"✓ Geometrically valid: {len(valid)}")
    for det in valid:
        print(f"  - {det['class']} @ {det['bbox']}")

    print(f"✗ Geometric anomalies: {len(rejected)}")
    for rej in rejected:
        print(f"  - {rej['detection']['class']}: {rej['reason']}")

    # Should reject some anomalies
    return len(rejected) >= 2


def test_60_percent_hard_threshold():
    """Validate that 60% is absolute minimum"""
    print("\n[Test 4] 60% Hard Threshold Enforcement")
    print("-" * 50)

    optimizer = get_detection_optimizer()

    # Use "person" which has threshold 55% (< 60%), so 60-61% will pass
    test_dets = [
        {
            "class": "person",
            "score": 0.59,
            "calibrated_confidence": 0.59,
            "bbox": [50, 50, 150, 200],
            "tta_support_count": 1
        },  # Just below hard threshold!
        {
            "class": "person",
            "score": 0.60,
            "calibrated_confidence": 0.60,
            "bbox": [200, 200, 300, 350],
            "tta_support_count": 1
        },  # Just at hard threshold!
        {
            "class": "person",
            "score": 0.61,
            "calibrated_confidence": 0.61,
            "bbox": [400, 100, 500, 250],
            "tta_support_count": 1
        },  # Above hard threshold!
    ]

    valid, rejected = optimizer.validate_and_filter_detections(
        detections=test_dets,
        image_width=640,
        image_height=480,
        strict_mode=True
    )

    print(f"✓ Passed 60% hard threshold: {len(valid)}")
    for det in valid:
        print(f"  - Person @ {det.get('score', 0.0):.0%} → {det.get('confidence_final', 0.0):.0%} ✓")

    print(f"✗ Below hard 60%: {len(rejected)}")
    for rej in rejected:
        score = rej['detection'].get('score', 0.0)
        reason = rej.get('reason', 'unknown')
        print(f"  - Person @ {score:.0%}: {reason}")

    # 59% MUST be rejected, 60%+ MUST pass
    has_59_rejected = any(d['detection'].get('score') == 0.59 for d in rejected)
    has_60_valid = any(d.get('score', 0.0) == 0.60 for d in valid)
    has_61_valid = any(d.get('score', 0.0) == 0.61 for d in valid)

    success = has_59_rejected and has_60_valid and has_61_valid

    print(f"\n  ✓ 59% rejected (below 60% hard)? {has_59_rejected}")
    print(f"  ✓ 60%+ passed (meets hard threshold)? {has_60_valid and has_61_valid}")

    return success


def test_alias_normalization_for_watch_phone():
    """Aliases like smartwatch/mobile phone should map to canonical classes."""
    print("\n[Test 5] Alias Normalization (watch/phone)")
    print("-" * 50)

    optimizer = get_detection_optimizer()

    test_dets = [
        {"class": "smartwatch", "score": 0.63, "bbox": [100, 120, 180, 220], "tta_support_count": 1},
        {"class": "mobile phone", "score": 0.64, "bbox": [220, 140, 300, 280], "tta_support_count": 1},
    ]

    valid, rejected = optimizer.validate_and_filter_detections(
        detections=test_dets,
        image_width=640,
        image_height=480,
        strict_mode=True
    )

    print(f"✓ Valid after alias mapping: {len(valid)}")
    for det in valid:
        print(f"  - {det.get('class')}: {det.get('confidence_final', 0.0):.1%}")
    print(f"✗ Rejected after alias mapping: {len(rejected)}")

    smartwatch_passed = any(str(d.get("class", "")).lower() == "smartwatch" for d in valid)
    mobile_phone_passed = any(str(d.get("class", "")).lower() == "mobile phone" for d in valid)
    return smartwatch_passed and mobile_phone_passed


def main():
    print("\n" + "=" * 70)
    print("SmarTrash v2.2.0 - Detection Optimizer Validation Suite")
    print("=" * 70)

    tests = [
        ("Basic Validation", test_basic_validation),
        ("Class-Specific Thresholds", test_class_specific_thresholds),
        ("Geometry & Anomalies", test_geometry_validation),
        ("60% Hard Threshold", test_60_percent_hard_threshold),
        ("Alias Normalization", test_alias_normalization_for_watch_phone),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
            print(f"\n{'✓ PASS' if result else '✗ FAIL'}: {name}")
        except Exception as e:
            print(f"\n✗ ERROR: {name} - {e}")
            results.append((name, False))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All tests PASSED! Detection Optimizer v2.2 is OPTIMIZED!")
        print("\nKey Features Validated:")
        print("  ✓ 60% Hard Threshold enforced")
        print("  ✓ Multi-Layer Validation working")
        print("  ✓ Class-Specific Confidence Adjustments")
        print("  ✓ Geometry & Anomaly Detection")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed!")

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
    success = main()
    exit(0 if success else 1)
