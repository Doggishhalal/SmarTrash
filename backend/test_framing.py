#!/usr/bin/env python
"""Quick test of framing optimizer"""
from framing_optimizer import get_framing_optimizer

opt = get_framing_optimizer()
print("✓ Framing Optimizer loaded")

test_det = [
    {'class': 'bottle', 'score': 0.8, 'bbox': [10, 20, 100, 150]},
    {'class': 'battery', 'score': 0.92, 'bbox': [8, 18, 102, 152]},
]

result = opt.optimize_detection_output(test_det, 640, 480)
print(f"📦 Optimization result: {result['total_quality']:.1%} quality")
print(f"   Rejected: {result['rejected_count']}")
print(f"   Optimized: {len(result['optimized_detections'])} detections")
