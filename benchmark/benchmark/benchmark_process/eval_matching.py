"""
Benchmark Level 2: Information Matching - ROUGE-L & BERTScore

So sánh nội dung retrieved với ground truth answer:
  - Dense Search vs Tri-Hybrid Search
  - Metrics: ROUGE-L (lexical) & BERTScore (semantic)

Usage: python eval_matching.py
Output: results/matching_results.json + charts/level2_matching.png
"""

import json
import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any

# ── Setup paths ──────────────────────────────────────────────────────────
CHATBOT_DIR = Path(__file__).resolve().parent.parent.parent / "chatbot"
sys.path.insert(0, str(CHATBOT_DIR))
os.chdir(str(CHATBOT_DIR))

from dotenv import load_dotenv
load_dotenv(CHATBOT_DIR / ".env")

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

logger = get_logger("benchmark_matching")

# ── Paths ────────────────────────────────────────────────────────────────
BENCHMARK_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BENCHMARK_DIR / "benchmark_data" / "preprocess" / "clean_benchmark_data.json"
RESULTS_DIR = BENCHMARK_DIR / "benchmark_process" / "results"
CHARTS_DIR = BENCHMARK_DIR / "benchmark_process" / "charts"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Metrics ──────────────────────────────────────────────────────────────

def compute_rouge_l(reference: str, hypothesis: str) -> float:
    """ROUGE-L (F1) dựa trên Longest Common Subsequence."""
    if not reference or not hypothesis:
        return 0.0

    ref_tokens = reference.split()
    hyp_tokens = hypothesis.split()
    if not ref_tokens or not hyp_tokens:
        return 0.0

    m, n = len(ref_tokens), len(hyp_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref_tokens[i-1] == hyp_tokens[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])

    lcs_length = dp[m][n]
    if lcs_length == 0:
        return 0.0

    precision = lcs_length / n
    recall = lcs_length / m
    f1 = (2 * precision * recall) / (precision + recall)
    return round(f1, 6)


def compute_bertscore(references: List[str], hypotheses: List[str]) -> List[float]:
    """BERTScore F1 dùng sentence-transformers cosine similarity."""
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np

        model_name = settings.EMBEDDING_MODEL
        print(f"  📦 Loading BERTScore model: {model_name}")
        model = SentenceTransformer(model_name)

        scores = []
        batch_size = 16

        for i in range(0, len(references), batch_size):
            batch_refs = [r[:2000] for r in references[i:i+batch_size]]
            batch_hyps = [h[:2000] for h in hypotheses[i:i+batch_size]]

            ref_embs = model.encode(batch_refs, normalize_embeddings=True)
            hyp_embs = model.encode(batch_hyps, normalize_embeddings=True)

            for ref_e, hyp_e in zip(ref_embs, hyp_embs):
                cos_sim = float(np.dot(ref_e, hyp_e))
                scores.append(round(max(0.0, cos_sim), 6))

        return scores
    except ImportError:
        print("  ⚠️  sentence-transformers not installed.")
        return [0.0] * len(references)


# ── Search strategies ────────────────────────────────────────────────────

def search_dense(repo: Neo4jRepo, query: str, limit: int = 5) -> str:
    """Dense Search only: Vector semantic search."""
    search_terms = repo._extract_keywords(query)
    docs = repo._vector_search(search_terms, limit=limit)
    return "\n\n".join([doc.content for doc in docs if doc.content]) if docs else ""


def search_tri_hybrid(repo: Neo4jRepo, query: str, limit: int = 5) -> str:
    """Tri-Hybrid Search: Sparse + Dense + Graph."""
    docs = repo.get_penalty_info(query, limit=limit)
    return "\n\n".join([doc.content for doc in docs if doc.content]) if docs else ""


# ── Visualization ───────────────────────────────────────────────────────

def plot_results(results: Dict):
    """Vẽ grouped bar chart ROUGE-L & BERTScore và lưu file."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import numpy as np

    for font in ['Segoe UI', 'Arial Unicode MS', 'Tahoma', 'DejaVu Sans']:
        if font in [f.name for f in fm.fontManager.ttflist]:
            plt.rcParams['font.family'] = font
            break
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.unicode_minus'] = False

    metrics = ['ROUGE-L', 'BERTScore']
    dense_scores = [
        results["dense_search"]["rouge_l"]["average"],
        results["dense_search"]["bertscore"]["average"]
    ]
    tri_scores = [
        results["tri_hybrid_search"]["rouge_l"]["average"],
        results["tri_hybrid_search"]["bertscore"]["average"]
    ]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(metrics))
    width = 0.3

    bars1 = ax.bar(x - width/2, dense_scores, width,
                   label='Dense Search', color='#96CEB4',
                   edgecolor='white', linewidth=1.5, zorder=3)
    bars2 = ax.bar(x + width/2, tri_scores, width,
                   label='Tri-Hybrid Search', color='#4ECDC4',
                   edgecolor='white', linewidth=1.5, zorder=3)

    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., h + 0.005,
                    f'{h:.4f}', ha='center', va='bottom',
                    fontweight='bold', fontsize=12, color='#333333')

    ax.set_ylabel('Score', fontsize=14, fontweight='bold')
    ax.set_title('Level 2: Information Matching - Dense vs Tri-Hybrid',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=14, fontweight='bold')

    max_score = max(max(dense_scores), max(tri_scores))
    ax.set_ylim(0, min(1.15, max_score * 1.25) if max_score > 0 else 1.15)

    ax.legend(fontsize=12, loc='upper right')
    ax.grid(axis='y', alpha=0.3, linestyle='--', zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    output_path = CHARTS_DIR / "level2_matching.png"
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

    # Phase 1: Retrieve content
    print("=" * 60)
    print("🔍 Phase 1: Retrieving content...")
    print("=" * 60)

    dense_contents = []
    trihybrid_contents = []
    references = []
    questions = []

    for idx, item in enumerate(benchmark_data):
        question = item["question"]
        answer = item["answer"]
        print(f"\n[{idx+1}/{total}] {question[:70]}...")

        t0 = time.time()
        dense_content = search_dense(repo, question, limit=5)
        t_dense = time.time() - t0

        t0 = time.time()
        trihybrid_content = search_tri_hybrid(repo, question, limit=5)
        t_tri = time.time() - t0

        dense_contents.append(dense_content)
        trihybrid_contents.append(trihybrid_content)
        references.append(answer)
        questions.append(question)

        print(f"  Dense:      {len(dense_content):>6} chars ({t_dense:.2f}s)")
        print(f"  Tri-Hybrid: {len(trihybrid_content):>6} chars ({t_tri:.2f}s)")

    repo.close()

    # Phase 2: ROUGE-L
    print(f"\n{'='*60}")
    print("📊 Phase 2: Computing ROUGE-L...")
    print("=" * 60)

    dense_rouge = [compute_rouge_l(references[i], dense_contents[i]) for i in range(total)]
    tri_rouge = [compute_rouge_l(references[i], trihybrid_contents[i]) for i in range(total)]

    avg_rouge_d = sum(dense_rouge) / len(dense_rouge)
    avg_rouge_t = sum(tri_rouge) / len(tri_rouge)
    print(f"  Dense:      {avg_rouge_d:.4f}")
    print(f"  Tri-Hybrid: {avg_rouge_t:.4f}")

    # Phase 3: BERTScore
    print(f"\n{'='*60}")
    print("📊 Phase 3: Computing BERTScore...")
    print("=" * 60)

    dense_hyps = [c if c else "Không tìm thấy thông tin" for c in dense_contents]
    tri_hyps = [c if c else "Không tìm thấy thông tin" for c in trihybrid_contents]

    dense_bert = compute_bertscore(references, dense_hyps)
    tri_bert = compute_bertscore(references, tri_hyps)

    avg_bert_d = sum(dense_bert) / len(dense_bert)
    avg_bert_t = sum(tri_bert) / len(tri_bert)
    print(f"  Dense:      {avg_bert_d:.4f}")
    print(f"  Tri-Hybrid: {avg_bert_t:.4f}")

    # Summary
    print(f"\n{'='*60}")
    print("📊 FINAL RESULTS")
    print(f"{'='*60}")
    print(f"{'Method':<22s} {'ROUGE-L':>10s} {'BERTScore':>12s}")
    print(f"{'-'*44}")
    print(f"{'Dense Search':<22s} {avg_rouge_d:>10.4f} {avg_bert_d:>12.4f}")
    print(f"{'Tri-Hybrid Search':<22s} {avg_rouge_t:>10.4f} {avg_bert_t:>12.4f}")

    results = {
        "dense_search": {
            "rouge_l": {"average": round(avg_rouge_d, 4), "scores": dense_rouge},
            "bertscore": {"average": round(avg_bert_d, 4), "scores": dense_bert}
        },
        "tri_hybrid_search": {
            "rouge_l": {"average": round(avg_rouge_t, 4), "scores": tri_rouge},
            "bertscore": {"average": round(avg_bert_t, 4), "scores": tri_bert}
        },
        "details": [
            {
                "question": questions[i],
                "dense_rouge_l": dense_rouge[i],
                "tri_hybrid_rouge_l": tri_rouge[i],
                "dense_bertscore": dense_bert[i],
                "tri_hybrid_bertscore": tri_bert[i]
            }
            for i in range(total)
        ]
    }

    # Save JSON
    output_file = RESULTS_DIR / "matching_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Results saved: {output_file}")

    # Plot chart
    plot_results(results)

    print("✅ Level 2 Done!")
    return results


if __name__ == "__main__":
    run_evaluation()
