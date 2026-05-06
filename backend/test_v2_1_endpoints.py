#!/usr/bin/env python
"""End-to-End API Test for dataset/framing features (v2.2 compatible)."""
import json
import time

import requests

BASE_URL = "http://localhost:8000"

def test_root():
    """Test root endpoint"""
    print("\n[1/4] Testing root endpoint...")
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert str(data.get("version", "")).startswith("2.2"), f"Version should be 2.2.x, got {data.get('version')}"
    assert "dataset/import-all" in str(data), "New endpoint not documented"
    print(f"✓ Root endpoint OK (v{data.get('version')})")
    return data

def test_dataset_info():
    """Test dataset info endpoint"""
    print("\n[2/4] Testing dataset info endpoint...")
    r = requests.get(f"{BASE_URL}/learning/dataset/info")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    datasets = data.get("available_datasets", {})
    assert len(datasets) >= 5, f"Should have 5+ datasets, got {len(datasets)}"
    print(f"✓ Dataset info OK ({data.get('total_unique_objects')} objects)")
    for name, info in datasets.items():
        print(f"  - {name}: {info['license']}")
    return data

def test_dataset_import():
    """Test dataset import endpoint"""
    print("\n[3/4] Testing dataset import endpoint...")
    r = requests.post(f"{BASE_URL}/learning/dataset/import-all?max_objects=50")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data.get("status") == "success", f"Status should be success, got {data.get('status')}"

    result = data.get("import_result", {})
    print(f"✓ Dataset import OK")
    print(f"  Processed: {result.get('processed')} objects")
    print(f"  Indexed: {result.get('indexed_objects')} objects")
    print(f"  Coverage: {result.get('total_unique_objects')} unique objects")
    return data

def test_framing_module():
    """Test framing optimizer module loads"""
    print("\n[4/4] Testing framing optimizer module...")
    from framing_optimizer import get_framing_optimizer
    opt = get_framing_optimizer()

    test_det = [
        {'class': 'plastic_bottle', 'score': 0.85, 'bbox': [10, 20, 100, 150]},
        {'class': 'battery', 'score': 0.92, 'bbox': [8, 18, 102, 152]},
    ]

    result = opt.optimize_detection_output(test_det, 640, 480)
    assert "optimized_detections" in result
    print(f"✓ Framing optimizer OK")
    print(f"  Optimized: {len(result.get('optimized_detections', []))} detections")
    print(f"  Quality: {result.get('total_quality', 0.0):.1%}")
    return result

def main():
    print("=" * 70)
    print("SmarTrash v2.2 - End-to-End API Test")
    print("=" * 70)

    try:
        # Give server time to start
        print("\n⏳ Waiting for API server to be ready...")
        for i in range(10):
            try:
                r = requests.get(f"{BASE_URL}/", timeout=1)
                if r.status_code == 200:
                    print("✓ API server is ready")
                    break
            except Exception:
                if i < 9:
                    time.sleep(1)
                else:
                    raise RuntimeError("API server did not start")

        # Run tests
        test_root()
        test_dataset_info()
        test_dataset_import()
        test_framing_module()

        print("\n" + "=" * 70)
        print("✅ All tests PASSED!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. POST /learning/dataset/import-all to load all 200+ objects")
        print("2. POST /detect with your images")
        print("3. POST /feedback/verify to provide feedback")
        print("4. GET /learning/dashboard to monitor improvement")

    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
