"""
Benchmark Runner - Chạy toàn bộ pipeline benchmark

Thứ tự:
1. eval_retrieval.py   → Level 1: Hit Rate@3
2. eval_matching.py    → Level 2: ROUGE-L & BERTScore  
3. visualize.py        → Vẽ biểu đồ

Usage: python run_all.py
"""

import sys
import time
from pathlib import Path

def main():
    start = time.time()
    
    print("=" * 60)
    print("🚀 BENCHMARK PIPELINE START")
    print("=" * 60)
    
    # Level 1
    print("\n\n" + "=" * 60)
    print("📋 LEVEL 1: Document Retrieval (Hit Rate@3)")
    print("=" * 60)
    
    try:
        from eval_retrieval import run_evaluation as eval_retrieval
        retrieval_results = eval_retrieval()
    except Exception as e:
        print(f"❌ Level 1 failed: {e}")
        import traceback
        traceback.print_exc()
        retrieval_results = None
    
    # Level 2
    print("\n\n" + "=" * 60)
    print("📋 LEVEL 2: Information Matching (ROUGE-L & BERTScore)")
    print("=" * 60)
    
    try:
        from eval_matching import run_evaluation as eval_matching
        matching_results = eval_matching()
    except Exception as e:
        print(f"❌ Level 2 failed: {e}")
        import traceback
        traceback.print_exc()
        matching_results = None
    
    # Visualize
    print("\n\n" + "=" * 60)
    print("📊 VISUALIZATION")
    print("=" * 60)
    
    try:
        from visualize import plot_hit_rate, plot_matching_scores, plot_combined_summary
        
        print("\n1️⃣  Level 1 chart:")
        plot_hit_rate()
        
        print("\n2️⃣  Level 2 chart:")
        plot_matching_scores()
        
        print("\n3️⃣  Combined chart:")
        plot_combined_summary()
        
    except Exception as e:
        print(f"❌ Visualization failed: {e}")
        import traceback
        traceback.print_exc()
    
    elapsed = time.time() - start
    print(f"\n\n{'=' * 60}")
    print(f"✅ BENCHMARK PIPELINE COMPLETE ({elapsed:.1f}s)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
