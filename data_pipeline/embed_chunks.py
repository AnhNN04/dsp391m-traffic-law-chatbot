"""
embed_chunks.py
===============
Đọc từng file JSON chunk trong data/chunks/, tính vector embedding cho
trường `embed_content` bằng sentence-transformers (local, miễn phí),
sau đó ghi thêm key `embedding` vào mỗi chunk và lưu lại file JSON.

Model mặc định: paraphrase-multilingual-mpnet-base-v2
  - 768 dimensions, hỗ trợ tiếng Việt tốt
  - Tải 1 lần (~420 MB), tự cache tại ~/.cache/huggingface/

Chạy:
    python embed_chunks.py
    python embed_chunks.py --model intfloat/multilingual-e5-small   # nhỏ hơn, nhanh hơn
    python embed_chunks.py --model BAAI/bge-m3                      # tốt nhất, nặng hơn
"""

import argparse
import json
import time
from pathlib import Path
from typing import List, Dict

# ── Cấu hình ────────────────────────────────────────────────────────────────
CHUNK_DIR     = Path(__file__).parent / "convert_to_md" / "data" / "chunks"
DEFAULT_MODEL = "intfloat/multilingual-e5-small"
BATCH_SIZE    = 64      # embed bao nhiêu chunk cùng lúc (tùy RAM/GPU)


def load_model(model_name: str):
    """Tải SentenceTransformer model (cache local sau lần đầu)."""
    from sentence_transformers import SentenceTransformer
    print(f"📦 Đang tải model: {model_name}")
    print("   (Lần đầu chạy sẽ tải về từ HuggingFace, ~420 MB cho model mặc định)")
    t0 = time.time()
    model = SentenceTransformer(model_name)
    print(f"✅ Model sẵn sàng ({time.time() - t0:.1f}s)\n")
    return model


def embed_file(chunk_file: Path, model, batch_size: int) -> int:
    """
    Đọc một file JSON chunk, tính embedding cho từng chunk,
    ghi thêm key `embedding`, lưu lại file. Trả về số chunk đã embed.
    """
    chunks: List[Dict] = json.loads(chunk_file.read_text(encoding="utf-8"))

    if not chunks:
        print(f"  ⚠️  File rỗng, bỏ qua.")
        return 0

    # Thu thập tất cả embed_content
    texts = [c.get("embed_content") or c.get("content", "") for c in chunks]

    # Embed theo batch
    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        vecs = model.encode(
            batch,
            show_progress_bar=False,
            normalize_embeddings=True,   # cosine similarity
            convert_to_numpy=True,
        )
        all_vectors.extend(vecs.tolist())

    # Ghi embedding vào từng chunk
    for chunk, vec in zip(chunks, all_vectors):
        chunk["embedding"] = vec

    # Lưu lại file (ghi đè)
    chunk_file.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return len(chunks)


def main(model_name: str, batch_size: int):
    print("=" * 60)
    print("  EMBED CHUNKS - Vietnamese Traffic Law RAG Pipeline")
    print("=" * 60)
    print(f"  Model    : {model_name}")
    print(f"  Batch    : {batch_size}")
    print(f"  Chunk dir: {CHUNK_DIR}\n")

    model = load_model(model_name)

    chunk_files = sorted(CHUNK_DIR.glob("*_fix.json"))
    print(f"Tìm thấy {len(chunk_files)} file chunk.\n")

    total = 0
    errors = []
    t_start = time.time()

    for chunk_file in chunk_files:
        print(f"--- {chunk_file.name} ---")
        try:
            t0 = time.time()
            n = embed_file(chunk_file, model, batch_size)
            elapsed = time.time() - t0
            print(f"  ✅ {n} chunks embedded | {elapsed:.1f}s")
            total += n
        except Exception as e:
            print(f"  ❌ Lỗi: {e}")
            errors.append(chunk_file.name)

    elapsed_total = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"HOÀN TẤT: {len(chunk_files) - len(errors)}/{len(chunk_files)} file thành công")
    print(f"Tổng chunks đã embed: {total} | Thời gian: {elapsed_total:.1f}s")
    if errors:
        print(f"❌ Lỗi: {errors}")
    print()
    print("➡️  Tiếp theo chạy: python push_to_neo4j.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed chunk content using sentence-transformers")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Model name (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE,
        help=f"Embedding batch size (default: {BATCH_SIZE})"
    )
    args = parser.parse_args()
    main(args.model, args.batch_size)
