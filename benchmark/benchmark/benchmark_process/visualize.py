"""
Benchmark Visualization

Tạo biểu đồ cho kết quả benchmark:
  - Level 1: Bar chart đơn (Hit Rate@3) cho 3 phương pháp
  - Level 2: Grouped bar chart (ROUGE-L & BERTScore) cho Dense vs Tri-Hybrid

Có thể chạy sau khi đã có kết quả evaluation, hoặc dùng dữ liệu mẫu/nhập tay.

Usage: python visualize.py [--from-results | --manual]
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────
BENCHMARK_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BENCHMARK_DIR / "benchmark_process" / "results"
OUTPUT_DIR = BENCHMARK_DIR / "benchmark_process" / "charts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Style config ─────────────────────────────────────────────────────────
# Màu sắc đẹp cho biểu đồ  
COLORS = {
    "sparse_dense": "#4ECDC4",   # Teal
    "graph":        "#FF6B6B",   # Coral
    "tri_hybrid":   "#45B7D1",   # Sky blue
    "dense":        "#96CEB4",   # Sage green
    "tri_hybrid_2": "#FFEAA7",   # Pastel yellow
}

# Cố gắng dùng font hỗ trợ tiếng Việt
def setup_font():
    """Setup font hỗ trợ tiếng Việt."""
    # Thử các font phổ biến trên Windows
    vietnamese_fonts = [
        'Segoe UI', 'Arial Unicode MS', 'Tahoma', 'Times New Roman', 
        'Calibri', 'Cambria', 'DejaVu Sans'
    ]
    
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    for font_name in vietnamese_fonts:
        if font_name in available_fonts:
            plt.rcParams['font.family'] = font_name
            print(f"  Using font: {font_name}")
            return
    
    print("  Using default font (Vietnamese may not render correctly)")

setup_font()
plt.rcParams['font.size'] = 12
plt.rcParams['axes.unicode_minus'] = False


# ── Chart 1: Level 1 - Hit Rate@3 ───────────────────────────────────────

def plot_hit_rate(data: Optional[Dict] = None, output_path: Optional[Path] = None):
    """
    Bar chart đơn cho Level 1: Document Retrieval - Hit Rate@3.
    
    Args:
        data: Dict với keys 'sparse_dense', 'graph', 'tri_hybrid', 
              mỗi key có value là dict chứa 'hit_rate'
        output_path: Đường dẫn file output
    """
    if data is None:
        # Thử load từ file results
        results_file = RESULTS_DIR / "retrieval_results.json"
        if results_file.exists():
            with open(results_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"  Loaded results from: {results_file}")
        else:
            print("  ⚠️  No retrieval results found. Using placeholder data.")
            print("  💡 Run eval_retrieval.py first, then run this script again.")
            data = {
                "sparse_dense": {"name": "Sparse + Dense", "hit_rate": 0.0},
                "graph":        {"name": "Graph Search",   "hit_rate": 0.0},
                "tri_hybrid":   {"name": "Tri-Hybrid",     "hit_rate": 0.0},
            }
    
    # Extract values
    methods = []
    hit_rates = []
    colors = []
    
    for key in ["sparse_dense", "graph", "tri_hybrid"]:
        if key in data:
            methods.append(data[key].get("name", key))
            hit_rates.append(data[key].get("hit_rate", 0.0))
            colors.append(COLORS.get(key, "#999999"))
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars = ax.bar(methods, hit_rates, color=colors, width=0.5, 
                  edgecolor='white', linewidth=1.5, zorder=3)
    
    # Add value labels on bars
    for bar, rate in zip(bars, hit_rates):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{rate:.2%}', ha='center', va='bottom', 
                fontweight='bold', fontsize=14, color='#333333')
    
    # Styling
    ax.set_ylabel('Hit Rate@3', fontsize=14, fontweight='bold')
    ax.set_title('Level 1: Document Retrieval - Hit Rate@3', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_ylim(0, 1.15)
    ax.set_yticks(np.arange(0, 1.1, 0.1))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    if output_path is None:
        output_path = OUTPUT_DIR / "level1_hit_rate.png"
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"  💾 Chart saved: {output_path}")


# ── Chart 2: Level 2 - ROUGE-L & BERTScore ──────────────────────────────

def plot_matching_scores(data: Optional[Dict] = None, output_path: Optional[Path] = None):
    """
    Grouped bar chart cho Level 2: Information Matching.
    2 nhóm (ROUGE-L, BERTScore) x 2 cột (Dense, Tri-Hybrid).
    
    Args:
        data: Dict với keys 'dense_search', 'tri_hybrid_search',
              mỗi key chứa 'rouge_l' và 'bertscore' với 'average'
        output_path: Đường dẫn file output
    """
    if data is None:
        results_file = RESULTS_DIR / "matching_results.json"
        if results_file.exists():
            with open(results_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"  Loaded results from: {results_file}")
        else:
            print("  ⚠️  No matching results found. Using placeholder data.")
            print("  💡 Run eval_matching.py first, then run this script again.")
            data = {
                "dense_search": {
                    "rouge_l":   {"average": 0.0},
                    "bertscore": {"average": 0.0}
                },
                "tri_hybrid_search": {
                    "rouge_l":   {"average": 0.0},
                    "bertscore": {"average": 0.0}
                }
            }
    
    # Extract values
    metrics = ['ROUGE-L', 'BERTScore']
    dense_scores = [
        data["dense_search"]["rouge_l"]["average"],
        data["dense_search"]["bertscore"]["average"]
    ]
    tri_scores = [
        data["tri_hybrid_search"]["rouge_l"]["average"],
        data["tri_hybrid_search"]["bertscore"]["average"]
    ]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(metrics))
    width = 0.3
    
    bars1 = ax.bar(x - width/2, dense_scores, width, 
                   label='Dense Search', color=COLORS["dense"],
                   edgecolor='white', linewidth=1.5, zorder=3)
    bars2 = ax.bar(x + width/2, tri_scores, width,
                   label='Tri-Hybrid Search', color=COLORS["sparse_dense"],
                   edgecolor='white', linewidth=1.5, zorder=3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.005,
                    f'{height:.4f}', ha='center', va='bottom',
                    fontweight='bold', fontsize=12, color='#333333')
    
    # Styling
    ax.set_ylabel('Score', fontsize=14, fontweight='bold')
    ax.set_title('Level 2: Information Matching - Dense vs Tri-Hybrid',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=14, fontweight='bold')
    
    # Dynamic y-axis
    max_score = max(max(dense_scores), max(tri_scores))
    ax.set_ylim(0, min(1.15, max_score * 1.25) if max_score > 0 else 1.15)
    
    ax.legend(fontsize=12, loc='upper right')
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    if output_path is None:
        output_path = OUTPUT_DIR / "level2_matching.png"
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"  💾 Chart saved: {output_path}")


# ── Chart 3: Combined Summary ───────────────────────────────────────────

def plot_combined_summary(retrieval_data: Optional[Dict] = None, 
                         matching_data: Optional[Dict] = None,
                         output_path: Optional[Path] = None):
    """
    Tạo figure tổng hợp gồm 2 subplot: Level 1 và Level 2.
    """
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    
    # ── Subplot 1: Level 1 ──
    ax1 = axes[0]
    
    if retrieval_data is None:
        results_file = RESULTS_DIR / "retrieval_results.json"
        if results_file.exists():
            with open(results_file, "r", encoding="utf-8") as f:
                retrieval_data = json.load(f)
    
    if retrieval_data:
        methods = []
        hit_rates = []
        colors = []
        for key in ["sparse_dense", "graph", "tri_hybrid"]:
            if key in retrieval_data:
                methods.append(retrieval_data[key].get("name", key))
                hit_rates.append(retrieval_data[key].get("hit_rate", 0.0))
                colors.append(COLORS.get(key, "#999999"))
        
        bars = ax1.bar(methods, hit_rates, color=colors, width=0.5,
                       edgecolor='white', linewidth=1.5, zorder=3)
        for bar, rate in zip(bars, hit_rates):
            ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
                     f'{rate:.2%}', ha='center', va='bottom',
                     fontweight='bold', fontsize=12, color='#333333')
    
    ax1.set_ylabel('Hit Rate@3', fontsize=13, fontweight='bold')
    ax1.set_title('Level 1: Document Retrieval', fontsize=14, fontweight='bold', pad=15)
    ax1.set_ylim(0, 1.15)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))
    ax1.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # ── Subplot 2: Level 2 ──
    ax2 = axes[1]
    
    if matching_data is None:
        results_file = RESULTS_DIR / "matching_results.json"
        if results_file.exists():
            with open(results_file, "r", encoding="utf-8") as f:
                matching_data = json.load(f)
    
    if matching_data:
        metrics = ['ROUGE-L', 'BERTScore']
        dense_scores = [
            matching_data["dense_search"]["rouge_l"]["average"],
            matching_data["dense_search"]["bertscore"]["average"]
        ]
        tri_scores = [
            matching_data["tri_hybrid_search"]["rouge_l"]["average"],
            matching_data["tri_hybrid_search"]["bertscore"]["average"]
        ]
        
        x = np.arange(len(metrics))
        width = 0.3
        
        bars1 = ax2.bar(x - width/2, dense_scores, width,
                        label='Dense Search', color=COLORS["dense"],
                        edgecolor='white', linewidth=1.5, zorder=3)
        bars2 = ax2.bar(x + width/2, tri_scores, width,
                        label='Tri-Hybrid Search', color=COLORS["sparse_dense"],
                        edgecolor='white', linewidth=1.5, zorder=3)
        
        for bars in [bars1, bars2]:
            for bar in bars:
                ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.005,
                         f'{bar.get_height():.4f}', ha='center', va='bottom',
                         fontweight='bold', fontsize=11, color='#333333')
        
        ax2.set_xticks(x)
        ax2.set_xticklabels(metrics, fontsize=13, fontweight='bold')
        ax2.legend(fontsize=11, loc='upper right')
        
        max_score = max(max(dense_scores), max(tri_scores))
        ax2.set_ylim(0, min(1.15, max_score * 1.25) if max_score > 0 else 1.15)
    
    ax2.set_ylabel('Score', fontsize=13, fontweight='bold')
    ax2.set_title('Level 2: Information Matching', fontsize=14, fontweight='bold', pad=15)
    ax2.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    fig.suptitle('Benchmark Results: Tri-Hybrid Search Evaluation', 
                 fontsize=18, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    
    if output_path is None:
        output_path = OUTPUT_DIR / "combined_summary.png"
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"  💾 Combined chart saved: {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print("📊 Generating benchmark charts...\n")
    
    print("1️⃣  Level 1: Hit Rate@3")
    plot_hit_rate()
    
    print("\n2️⃣  Level 2: ROUGE-L & BERTScore")
    plot_matching_scores()
    
    print("\n3️⃣  Combined Summary")
    plot_combined_summary()
    
    print(f"\n✅ All charts saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
