"""
Benchmark Level 1: Document Retrieval - Hit Rate@3

Đánh giá khả năng truy xuất tài liệu của từng phương pháp tìm kiếm:
  1-1: Dense Search (Vector semantic search)
  1-2: Graph Search (Law-specific + Graph traversal)  
  1-3: Tri-Hybrid Search (Sparse + Dense + Graph)

Metric: Hit Rate@3 - Tỷ lệ câu hỏi mà ít nhất 1 document đúng nằm trong top 3.

Usage: python eval_retrieval.py
Output: results/retrieval_results.json + charts/level1_hit_rate.png
"""

import json
import sys
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# ── Setup paths ──────────────────────────────────────────────────────────
CHATBOT_DIR = Path(__file__).resolve().parent.parent.parent / "chatbot"
sys.path.insert(0, str(CHATBOT_DIR))
os.chdir(str(CHATBOT_DIR))

from dotenv import load_dotenv
load_dotenv(CHATBOT_DIR / ".env")

# Import trực tiếp neo4j_repo.py bằng importlib, bypass __init__.py
import importlib.util

from app.domain.interfaces import IGraphStore
from app.domain.entities import LegalDocument, Violation, DocumentSource
from app.domain.exceptions import GraphStoreError, DatabaseConnectionError, CypherQueryError
from app.infrastructure.config import settings
from app.infrastructure.config.logger import get_logger

_neo4j_spec = importlib.util.spec_from_file_location(
    "neo4j_repo",
    str(CHATBOT_DIR / "app" / "infrastructure" / "persistence" / "neo4j_repo.py")
)
_neo4j_module = importlib.util.module_from_spec(_neo4j_spec)
_neo4j_spec.loader.exec_module(_neo4j_module)

Neo4jRepo = _neo4j_module.Neo4jRepo

logger = get_logger("benchmark_retrieval")

# ── Paths ────────────────────────────────────────────────────────────────
BENCHMARK_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BENCHMARK_DIR / "benchmark_data" / "preprocess" / "clean_benchmark_data.json"
RESULTS_DIR = BENCHMARK_DIR / "benchmark_process" / "results"
CHARTS_DIR = BENCHMARK_DIR / "benchmark_process" / "charts"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Helper: Extract law references from answer ──────────────────────────
def extract_law_refs(answer: str) -> List[str]:
    refs = []
    dieu_matches = re.findall(r'Điều\s+(\d+)', answer)
    for d in dieu_matches:
        refs.append(f"Điều {d}")
    khoan_matches = re.findall(r'[Kk]hoản\s+(\d+)', answer)
    for k in khoan_matches:
        refs.append(f"khoản {k}")
    law_id_matches = re.findall(r'(\d+/\d{4}/[A-ZĐ\-]+)', answer)
    refs.extend(law_id_matches)
    return refs


def check_hit(retrieved_docs: List[Any], answer: str, top_k: int = 3) -> bool:
    if not retrieved_docs:
        return False
    
    top_docs = retrieved_docs[:top_k]
    gt_refs = extract_law_refs(answer)
    gt_dieu = [ref for ref in gt_refs if ref.startswith("Điều")]
    gt_law_ids = [ref for ref in gt_refs if '/' in ref]
    
    for doc in top_docs:
        doc_content = doc.content if hasattr(doc, 'content') else ""
        doc_article_id = str(doc.article_id or "") if hasattr(doc, 'article_id') else ""
        doc_law_id = ""
        if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
            doc_law_id = doc.metadata.get("law_id", "")
        
        # Check 1: Article ID match
        for dieu_ref in gt_dieu:
            dieu_num = re.search(r'\d+', dieu_ref)
            if dieu_num and doc_article_id == dieu_num.group():
                return True
        
        # Check 2: Law ID + content overlap
        for law_id in gt_law_ids:
            law_num = law_id.split('/')[0]
            if law_num in doc_law_id and len(doc_content) > 50:
                answer_words = answer.split()
                doc_text = doc_content
                for i in range(len(answer_words) - 4):
                    gram = " ".join(answer_words[i:i+5])
                    if gram in doc_text:
                        return True
        
        # Check 3: Direct content overlap
        if len(doc_content) > 50 and len(answer) > 100:
            answer_sentences = answer.split("\n")
            for sent in answer_sentences:
                sent = sent.strip()
                if len(sent) > 30 and sent[:50] in doc_content:
                    return True
    
    return False


# ── Search strategies ────────────────────────────────────────────────────

def search_dense(repo: Neo4jRepo, query: str, limit: int = 3) -> List:
    """1-1: Dense only (Vector semantic search)."""
    search_terms = repo._extract_keywords(query)
    docs = repo._vector_search(search_terms, limit=limit)
    return docs[:limit]


def search_graph(repo: Neo4jRepo, query: str, limit: int = 3) -> List:
    """1-2: Graph Search (Law-specific + graph traversal)."""
    results = []
    seen = set()

    def add_docs(docs):
        for doc in docs:
            key = doc.content[:100]
            if key not in seen:
                results.append(doc)
                seen.add(key)

    law_num = repo._detect_law_number(query)
    if law_num:
        add_docs(repo._search_by_law_id(law_num, limit=limit))

    search_terms = repo._extract_keywords(query)
    add_docs(repo._vector_search(search_terms, limit=limit))

    results.sort(key=lambda x: getattr(x, "score", 0.0) or 0.0, reverse=True)
    return results[:limit]


def search_tri_hybrid(repo: Neo4jRepo, query: str, limit: int = 3) -> List:
    """1-3: Tri-Hybrid (Sparse + Dense + Graph) = get_penalty_info()."""
    return repo.get_penalty_info(query, limit=limit)


# ── Visualization ───────────────────────────────────────────────────────

def plot_results(results_summary: Dict):
    """Vẽ bar chart Hit Rate@3 và lưu file."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import numpy as np

    # Font setup
    for font in ['Segoe UI', 'Arial Unicode MS', 'Tahoma', 'DejaVu Sans']:
        if font in [f.name for f in fm.fontManager.ttflist]:
            plt.rcParams['font.family'] = font
            break
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.unicode_minus'] = False

    # Data
    COLORS = ["#4ECDC4", "#FF6B6B", "#45B7D1"]
    methods = []
    hit_rates = []
    for key in ["dense", "graph", "tri_hybrid"]:
        if key in results_summary:
            methods.append(results_summary[key]["name"])
            hit_rates.append(results_summary[key]["hit_rate"])

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(methods, hit_rates, color=COLORS[:len(methods)], width=0.5,
                  edgecolor='white', linewidth=1.5, zorder=3)

    for bar, rate in zip(bars, hit_rates):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
                f'{rate:.2%}', ha='center', va='bottom',
                fontweight='bold', fontsize=14, color='#333333')

    ax.set_ylabel('Hit Rate@3', fontsize=14, fontweight='bold')
    ax.set_title('Level 1: Document Retrieval - Hit Rate@3',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_ylim(0, 1.15)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0%}'))
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    output_path = CHARTS_DIR / "level1_hit_rate.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"\n📊 Chart saved: {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────

def run_evaluation():
    print(f"📂 Loading benchmark data: {DATA_FILE}")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        benchmark_data = json.load(f)

    total = len(benchmark_data)
    print(f"📊 Total questions: {total}")

    print(f"🔌 Connecting to Neo4j: {settings.NEO4J_URI}")
    repo = Neo4jRepo(
        uri=settings.NEO4J_URI,
        username=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD
    )
    print("✅ Neo4j connected!\n")

    strategies = {
        "dense":      {"name": "Dense Search",      "fn": search_dense,      "hits": 0, "total": 0, "details": []},
        "graph":      {"name": "Graph Search",       "fn": search_graph,      "hits": 0, "total": 0, "details": []},
        "tri_hybrid": {"name": "Tri-Hybrid Search",  "fn": search_tri_hybrid, "hits": 0, "total": 0, "details": []},
    }

    for idx, item in enumerate(benchmark_data):
        question = item["question"]
        answer = item["answer"]
        print(f"\n[{idx+1}/{total}] {question[:80]}...")

        for key, s in strategies.items():
            try:
                t0 = time.time()
                docs = s["fn"](repo, question, limit=3)
                elapsed = time.time() - t0

                hit = check_hit(docs, answer, top_k=3)
                s["total"] += 1
                if hit:
                    s["hits"] += 1

                status = "✅ HIT" if hit else "❌ MISS"
                print(f"  {s['name']:22s}: {status} ({len(docs)} docs, {elapsed:.2f}s)")

                s["details"].append({
                    "question": question, "hit": hit,
                    "num_docs": len(docs), "time_s": round(elapsed, 3)
                })
            except Exception as e:
                print(f"  {s['name']:22s}: ❌ ERROR - {e}")
                s["total"] += 1
                s["details"].append({"question": question, "hit": False, "error": str(e)})

    # Results
    print(f"\n\n{'='*60}")
    print("📊 RESULTS: Hit Rate@3")
    print(f"{'='*60}")

    results_summary = {}
    for key, s in strategies.items():
        rate = s["hits"] / s["total"] if s["total"] > 0 else 0
        results_summary[key] = {
            "name": s["name"], "hits": s["hits"],
            "total": s["total"], "hit_rate": round(rate, 4),
            "details": s["details"]
        }
        print(f"  {s['name']:22s}: {rate:.2%} ({s['hits']}/{s['total']})")

    # Save JSON
    output_file = RESULTS_DIR / "retrieval_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Results saved: {output_file}")

    # Plot chart
    plot_results(results_summary)

    repo.close()
    print("✅ Level 1 Done!")
    return results_summary


if __name__ == "__main__":
    run_evaluation()
