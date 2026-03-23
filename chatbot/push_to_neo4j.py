"""
push_to_neo4j.py
================
Đẩy dữ liệu từ các file JSON chunk (đã có key `embedding`) lên Neo4j.

Mô hình đồ thị:
    (Document) -[:HAS_CHAPTER]-> (Chapter)
    (Chapter)  -[:HAS_ARTICLE]-> (Article)
    (Document) -[:HAS_ARTICLE]-> (Article)   [khi không có chương]
    (Article)  -[:HAS_CLAUSE]->  (Clause)

Mỗi node Clause/Article lưu `embedding` (float list) để dùng với
Neo4j Vector Index (vector similarity search / RAG).

Chạy sau khi đã chạy embed_chunks.py:
    python push_to_neo4j.py
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

# ── Cấu hình ────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
CHUNK_DIR = Path(r"C:\law_chatbot\dsp391m-traffic-law-chatbot-chatbot-anhnnhe182323\chunk")
ENV_FILE  = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
ENABLE_NEO4J   = os.getenv("ENABLE_NEO4J", "False").lower() == "true"

# Thay đổi nếu dùng model khác (số chiều phải khớp với model đã embed)
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))

MAX_RETRIES = 3
RETRY_DELAY = 5     # giây


# ── Cypher queries ───────────────────────────────────────────────────────────

Q_MERGE_DOCUMENT = """
MERGE (d:Document {law_id: $law_id})
ON CREATE SET d.type = $type, d.law_name = $law_name, d.created_at = datetime()
ON MATCH  SET d.type = $type, d.law_name = $law_name, d.updated_at = datetime()
"""

Q_MERGE_CHAPTER = """
MATCH (d:Document {law_id: $law_id})
MERGE (c:Chapter {id: $chapter_node_id})
ON CREATE SET c.chapter_id = $chapter_id, c.chapter_name = $chapter_name, c.law_id = $law_id
MERGE (d)-[:HAS_CHAPTER]->(c)
"""

Q_MERGE_ARTICLE_WITH_CHAPTER = """
MATCH (c:Chapter {id: $chapter_node_id})
MERGE (a:Article {id: $article_node_id})
ON CREATE SET a.article_id = $article_id, a.article = $article,
              a.section = $section, a.law_id = $law_id
MERGE (c)-[:HAS_ARTICLE]->(a)
"""

Q_MERGE_ARTICLE_WITHOUT_CHAPTER = """
MATCH (d:Document {law_id: $law_id})
MERGE (a:Article {id: $article_node_id})
ON CREATE SET a.article_id = $article_id, a.article = $article,
              a.section = $section, a.law_id = $law_id
MERGE (d)-[:HAS_ARTICLE]->(a)
"""

# Đẩy Clause kèm embedding
Q_MERGE_CLAUSE = """
MATCH (a:Article {id: $article_node_id})
MERGE (cl:Clause {id: $clause_node_id})
ON CREATE SET cl.clause        = $clause,
              cl.content       = $content,
              cl.embed_content = $embed_content,
              cl.law_id        = $law_id,
              cl.article_id    = $article_id
SET cl.embedding = $embedding
MERGE (a)-[:HAS_CLAUSE]->(cl)
"""

# Đẩy nội dung vào Article không có khoản (kèm embedding)
Q_SET_ARTICLE_CONTENT = """
MATCH (a:Article {id: $article_node_id})
SET a.content       = $content,
    a.embed_content = $embed_content,
    a.embedding     = $embedding
"""

# Constraints (chạy 1 lần)
CONSTRAINTS = [
    "CREATE CONSTRAINT doc_law_id  IF NOT EXISTS FOR (d:Document) REQUIRE d.law_id IS UNIQUE",
    "CREATE CONSTRAINT chapter_uid IF NOT EXISTS FOR (c:Chapter)  REQUIRE c.id     IS UNIQUE",
    "CREATE CONSTRAINT article_uid IF NOT EXISTS FOR (a:Article)  REQUIRE a.id     IS UNIQUE",
    "CREATE CONSTRAINT clause_uid  IF NOT EXISTS FOR (cl:Clause)  REQUIRE cl.id    IS UNIQUE",
]

# Vector Indexes
VECTOR_INDEXES = [
    # Index cho Clause (có khoản)
    f"""CREATE VECTOR INDEX clause_embedding IF NOT EXISTS
        FOR (cl:Clause) ON (cl.embedding)
        OPTIONS {{indexConfig: {{`vector.dimensions`: {EMBEDDING_DIMENSIONS},
                                `vector.similarity_function`: 'cosine'}}}}""",
    # Index cho Article (không có khoản)
    f"""CREATE VECTOR INDEX article_embedding IF NOT EXISTS
        FOR (a:Article) ON (a.embedding)
        OPTIONS {{indexConfig: {{`vector.dimensions`: {EMBEDDING_DIMENSIONS},
                                `vector.similarity_function`: 'cosine'}}}}""",
]


# ── Helper ───────────────────────────────────────────────────────────────────

def make_chapter_node_id(law_id: str, chapter_id: str) -> str:
    return f"{law_id}::{chapter_id}"

def make_article_node_id(law_id: str, article_id: str) -> str:
    return f"{law_id}::Art{article_id}"

def make_clause_node_id(law_id: str, article_id: str, clause: str) -> str:
    return f"{law_id}::Art{article_id}::Cl{clause}"


def run_with_retry(session, query: str, params: Dict[str, Any]) -> None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            session.run(query, **params)
            return
        except ServiceUnavailable as e:
            if attempt == MAX_RETRIES:
                raise
            print(f"  ⚠️  Kết nối thất bại (lần {attempt}), thử lại sau {RETRY_DELAY}s... [{e}]")
            time.sleep(RETRY_DELAY)


# ── Init ─────────────────────────────────────────────────────────────────────

def init_schema(driver) -> None:
    """Tạo constraints và vector indexes (idempotent)."""
    with driver.session() as session:
        for cql in CONSTRAINTS:
            try:
                session.run(cql)
            except Exception:
                pass
        for cql in VECTOR_INDEXES:
            try:
                session.run(cql)
                print(f"  ✅ Vector index: {cql.split('INDEX')[1].split('IF')[0].strip()}")
            except Exception as e:
                print(f"  ⚠️  Vector index: {e}")
    print(f"✅ Schema khởi tạo xong (constraints + vector indexes, dims={EMBEDDING_DIMENSIONS})\n")


# ── Core push ────────────────────────────────────────────────────────────────

def push_chunks(driver, chunks: List[Dict], law_id: str) -> None:
    """Push toàn bộ chunks của một văn bản lên Neo4j."""
    if not chunks:
        return

    first = chunks[0]
    has_embedding = "embedding" in first

    if not has_embedding:
        print("  ⚠️  Chunks chưa có key 'embedding'. Hãy chạy embed_chunks.py trước!")

    # 1. Document
    with driver.session() as session:
        run_with_retry(session, Q_MERGE_DOCUMENT, {
            "law_id":   law_id,
            "type":     first.get("type", ""),
            "law_name": first.get("law_name", ""),
        })

    # 2. Chapters & Articles (dedup)
    seen_chapters: set = set()
    seen_articles: set = set()

    for chunk in chunks:
        chapter_id = chunk.get("chapter_id")
        article_id = str(chunk.get("article_id", ""))

        if chapter_id and chapter_id not in seen_chapters:
            seen_chapters.add(chapter_id)
            with driver.session() as session:
                run_with_retry(session, Q_MERGE_CHAPTER, {
                    "law_id":          law_id,
                    "chapter_node_id": make_chapter_node_id(law_id, chapter_id),
                    "chapter_id":      chapter_id,
                    "chapter_name":    chunk.get("chapter_name") or "",
                })

        if article_id and article_id not in seen_articles:
            seen_articles.add(article_id)
            chapter_node_id = make_chapter_node_id(law_id, chapter_id) if chapter_id else None
            article_node_id = make_article_node_id(law_id, article_id)

            with driver.session() as session:
                if chapter_node_id:
                    run_with_retry(session, Q_MERGE_ARTICLE_WITH_CHAPTER, {
                        "law_id": law_id, "chapter_node_id": chapter_node_id,
                        "article_node_id": article_node_id,
                        "article_id": article_id, "article": chunk.get("article", ""),
                        "section": chunk.get("section") or "",
                    })
                else:
                    run_with_retry(session, Q_MERGE_ARTICLE_WITHOUT_CHAPTER, {
                        "law_id": law_id, "article_node_id": article_node_id,
                        "article_id": article_id, "article": chunk.get("article", ""),
                        "section": chunk.get("section") or "",
                    })

    # 3. Clauses / Article content (kèm embedding)
    with driver.session() as session:
        for chunk in chunks:
            article_id = str(chunk.get("article_id", ""))
            clause     = chunk.get("clause")
            content    = chunk.get("content", "")
            embed      = chunk.get("embed_content", "")
            embedding  = chunk.get("embedding")   # list of floats, có thể None

            if not article_id:
                continue

            article_node_id = make_article_node_id(law_id, article_id)

            if clause:
                run_with_retry(session, Q_MERGE_CLAUSE, {
                    "law_id":          law_id,
                    "article_id":      article_id,
                    "article_node_id": article_node_id,
                    "clause_node_id":  make_clause_node_id(law_id, article_id, str(clause)),
                    "clause":          str(clause),
                    "content":         content,
                    "embed_content":   embed,
                    "embedding":       embedding,
                })
            else:
                run_with_retry(session, Q_SET_ARTICLE_CONTENT, {
                    "article_node_id": article_node_id,
                    "content":         content,
                    "embed_content":   embed,
                    "embedding":       embedding,
                })


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not ENABLE_NEO4J:
        print("⚠️  ENABLE_NEO4J=False trong .env. Không thực hiện push.")
        return

    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        print("❌ Thiếu biến môi trường NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD.")
        return

    print(f"🔌 Kết nối tới Neo4j: {NEO4J_URI}")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print("✅ Kết nối thành công!\n")
    except Exception as e:
        print(f"❌ Không thể kết nối Neo4j: {e}")
        driver.close()
        return

    init_schema(driver)

    chunk_files = sorted(CHUNK_DIR.glob("*_fix.json"))
    print(f"Tìm thấy {len(chunk_files)} file chunk.\n")

    total_chunks = 0
    errors: List[str] = []

    for chunk_file in chunk_files:
        print(f"--- Đang push: {chunk_file.name} ---")
        try:
            chunks: List[Dict] = json.loads(chunk_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ❌ Đọc file lỗi: {e}")
            errors.append(chunk_file.name)
            continue

        if not chunks:
            print("  ⚠️  File rỗng, bỏ qua.")
            continue

        law_id = chunks[0].get("law_id", chunk_file.stem.replace("_fix", ""))

        try:
            t0 = time.time()
            push_chunks(driver, chunks, law_id)
            elapsed = time.time() - t0
            has_emb = "✓ embedding" if "embedding" in chunks[0] else "✗ no embedding"
            print(f"  ✅ {len(chunks)} chunks | law_id={law_id} | {elapsed:.1f}s | {has_emb}")
            total_chunks += len(chunks)
        except Exception as e:
            print(f"  ❌ Lỗi push: {e}")
            errors.append(chunk_file.name)

    driver.close()

    print(f"\n{'=' * 60}")
    print(f"HOÀN TẤT: {len(chunk_files) - len(errors)}/{len(chunk_files)} file thành công")
    print(f"Tổng chunks đã push: {total_chunks}")
    if errors:
        print(f"❌ Lỗi: {errors}")
    print()
    print("💡 Dùng Neo4j Vector Search:")
    print("   CALL db.index.vector.queryNodes('clause_embedding', 5, $queryVector)")
    print("   YIELD node, score RETURN node.content, score")


if __name__ == "__main__":
    main()
