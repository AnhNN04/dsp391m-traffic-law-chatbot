import json
import numpy as np
from sentence_transformers import SentenceTransformer

from config import (
    EMBED_OUTPUT,
    MODEL_NAME,
    TOP_K,
)


def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def encode_query(model, query: str):
    return model.encode(
        "query: " + query,
        normalize_embeddings=True
    )


def search(query, data, model, top_k=5):
    query_emb = encode_query(model, query)

    scores = []
    for item in data:
        emb = item.get("embedding")
        if not emb:
            continue

        score = float(np.dot(query_emb, np.array(emb)))
        scores.append((score, item))

    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[:top_k]


def print_results(query, results):
    print("=" * 80)
    print(f"Query: {query}")
    print("=" * 80)

    for score, item in results:
        print(f"Score: {score:.4f}")
        print(item.get("article", ""))
        print(item.get("content", "")[:300])
        print("-" * 80)


def main():
    print("Loading embedded data:", EMBED_OUTPUT)
    data = load_data(EMBED_OUTPUT)
    print(f"Total items: {len(data)}")

    print("Loading model:", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)

    test_queries = [
        "quy định về người tham gia giao thông đường bộ",
        "điều kiện của người điều khiển phương tiện",
        "người đi bộ tham gia giao thông đường bộ",
        "giấy phép lái xe có hiệu lực bao lâu",
    ]

    for query in test_queries:
        results = search(query, data, model, top_k=TOP_K)
        print_results(query, results)


if __name__ == "__main__":
    main()
