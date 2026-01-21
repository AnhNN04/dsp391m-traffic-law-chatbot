import json
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

from config import (
    CHUNK_DIR,
    EMBED_DIR,
    EMBED_OUTPUT,
    MODEL_NAME,
    BATCH_SIZE,
    NORMALIZE,
)


def load_chunks(chunk_dir: Path):
    """Load and merge all chunked JSON files"""
    print("Looking for chunk files in:", chunk_dir.resolve())

    json_files = [
        p for p in chunk_dir.iterdir()
        if p.is_file() and p.suffix.lower() == ".json"
    ]

    print("Found files:", [p.name for p in json_files])

    if not json_files:
        raise RuntimeError(f"No chunk files found in {chunk_dir.resolve()}")

    chunks = []
    for file in sorted(json_files):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            chunks.extend(data)

    return chunks


def embed_chunks(chunks, model):
    texts = []
    valid_indices = []

    for idx, item in enumerate(chunks):
        content = item.get("embed_content")
        if content:
            texts.append("passage: " + content)
            valid_indices.append(idx)

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=NORMALIZE,
        show_progress_bar=True,
    )

    for idx, emb in zip(valid_indices, embeddings):
        chunks[idx]["embedding"] = emb.tolist()

    return chunks


def main():
    print("Loading embedding model:", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    print("Loading chunks from:", CHUNK_DIR)
    chunks = load_chunks(CHUNK_DIR)
    print(f"Total chunks: {len(chunks)}")

    print("Embedding...")
    chunks = embed_chunks(chunks, model)

    EMBED_DIR.mkdir(parents=True, exist_ok=True)

    print("Saving embeddings to:", EMBED_OUTPUT)
    with open(EMBED_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print("Embedding completed successfully.")


if __name__ == "__main__":
    main()
