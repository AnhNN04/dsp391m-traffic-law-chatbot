"""
cleanup_kg.py
=============
Script dọn dẹp (xóa toàn bộ) các Entity và Relationship được tạo bởi extract_entities.py.
Giúp Neo4j trở về trạng thái ban đầu (chỉ còn Document, Chapter, Article, Clause).

Cách chạy:
    python cleanup_kg.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

from ontology import NEO4J_ENTITY_LABEL

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR.parent / "chatbot" / ".env"
load_dotenv(ENV_FILE)

NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


# ── Cypher Queries ────────────────────────────────────────────────────────────

# Xóa toàn bộ KGEntity và các dây liên kết nối VỚI NÓ (kể cả HAS_ENTITY từ Clause)
# Dùng node label được định nghĩa trong ontology.py
Q_DELETE_KG_ENTITIES = f"""
MATCH (e:{NEO4J_ENTITY_LABEL})
DETACH DELETE e
RETURN count(e) AS deleted_count
"""


def main():
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        print("❌ Thiếu biến môi trường NEO4J_*.")
        return

    print("⚠️  CẢNH BÁO: Script này sẽ XÓA TOÀN BỘ Knowledge Graph Entities.")
    print("Các node gốc (Document, Chapter, Article, Clause) sẽ ĐƯỢC GIỮ NGUYÊN.")
    confirm = input("Bạn có chắc chắn muốn tiếp tục? (y/n): ")
    if confirm.lower() != 'y':
        print("Đã hủy.")
        return

    print(f"\n🔌 Kết nối Neo4j: {NEO4J_URI}")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        print(f"❌ Không thể kết nối Neo4j: {e}")
        return

    print("🗑️  Đang xóa dữ liệu...")
    try:
        with driver.session() as session:
            record = session.run(Q_DELETE_KG_ENTITIES).single()
            deleted_count = record["deleted_count"] if record else 0
            
            print(f"✅ Đã xóa thành công {deleted_count} {NEO4J_ENTITY_LABEL} nodes (và các relationships liên quan).")
            print("Graph đã trở về trạng thái ban đầu của push_to_neo4j.py.")
    except Exception as e:
        print(f"❌ Lỗi khi xóa: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    main()
