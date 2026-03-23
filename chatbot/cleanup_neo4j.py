import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def cleanup():
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        print("❌ Thiếu biến môi trường Neo4j.")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    with driver.session() as session:
        print("--- Đang dọn dẹp Neo4j ---")
        
        # 1. Drop vector indexes
        indexes_to_drop = ["clause_embedding", "article_embedding", "clause_fulltext"]
        for idx in indexes_to_drop:
            try:
                session.run(f"DROP INDEX {idx}")
                print(f"  ✅ Đã xóa index: {idx}")
            except Exception as e:
                print(f"  ⚠️  Không thể xóa index {idx} (có thể không tồn tại): {e}")

        # 2. Delete all nodes (Document, Chapter, Article, Clause)
        try:
            print("  ⏳ Đang xóa tất cả các node...")
            session.run("MATCH (n:Document) DETACH DELETE n")
            session.run("MATCH (n:Chapter) DETACH DELETE n")
            session.run("MATCH (n:Article) DETACH DELETE n")
            session.run("MATCH (n:Clause) DETACH DELETE n")
            # Optionally delete everything if you want to be extremely thorough
            # session.run("MATCH (n) DETACH DELETE n")
            print("  ✅ Đã xóa tất cả các node liên quan.")
        except Exception as e:
            print(f"  ❌ Lỗi khi xóa node: {e}")

        # 3. Drop constraints (optional but good for a fresh start)
        constraints = [
            "doc_law_id", "chapter_uid", "article_uid", "clause_uid"
        ]
        for cstr in constraints:
            try:
                session.run(f"DROP CONSTRAINT {cstr}")
                print(f"  ✅ Đã xóa constraint: {cstr}")
            except Exception as e:
                print(f"  ⚠️  Không thể xóa constraint {cstr}: {e}")

    driver.close()
    print("\n✨ Dọn dẹp hoàn tất! Sẵn sàng cho push_to_neo4j.py")

if __name__ == "__main__":
    cleanup()
