"""
Data Seeding Script

Nạp dữ liệu mẫu vào ChromaDB và Neo4j để phục vụ testing.
Dữ liệu: Các mức phạt phổ biến (Vượt đèn đỏ, Nồng độ cồn).

Usage: python scripts/seed_data.py
"""

import sys
import os

# Thêm root path để import được module app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.container import Container
from app.domain.entities import LegalDocument

def seed():
    print("🌱 Starting Data Seeding...")
    
    # Init Container để lấy các Repo
    container = Container()
    vector_store = container.vector_store
    graph_store = container.graph_store
    
    # --- DỮ LIỆU MẪU ---
    sample_docs = [
        LegalDocument(
            content="""
            Nghị định 100/2019/NĐ-CP - Điều 6. Xử phạt người điều khiển xe mô tô, xe gắn máy.
            Khoản 4, Điểm e: Phạt tiền từ 800.000 đồng đến 1.000.000 đồng đối với người điều khiển xe thực hiện hành vi:
            Không chấp hành hiệu lệnh của đèn tín hiệu giao thông (Vượt đèn đỏ).
            """,
            metadata={"law": "ND100", "article": "6", "topic": "Vượt đèn đỏ", "vehicle": "motorcycle"},
            source="database"
        ),
        LegalDocument(
            content="""
            Nghị định 100/2019/NĐ-CP - Điều 5. Xử phạt người điều khiển xe ô tô.
            Khoản 5, Điểm a: Phạt tiền từ 4.000.000 đồng đến 6.000.000 đồng đối với người điều khiển xe thực hiện hành vi:
            Không chấp hành hiệu lệnh của đèn tín hiệu giao thông (Vượt đèn đỏ).
            Tước quyền sử dụng Giấy phép lái xe từ 01 tháng đến 03 tháng.
            """,
            metadata={"law": "ND100", "article": "5", "topic": "Vượt đèn đỏ", "vehicle": "car"},
            source="database"
        ),
        LegalDocument(
            content="""
            Nghị định 100/2019/NĐ-CP. Quy định về nồng độ cồn.
            Mức 1: Chưa vượt quá 50 miligam/100 mililít máu hoặc 0.25 miligam/1 lít khí thở.
            - Xe máy: Phạt 2-3 triệu, tước bằng 10-12 tháng.
            - Ô tô: Phạt 6-8 triệu, tước bằng 10-12 tháng.
            """,
            metadata={"law": "ND100", "topic": "Nồng độ cồn"},
            source="database"
        ),
        LegalDocument(
            content="""
            Điều 30. Xử phạt chủ phương tiện vi phạm quy định liên quan đến giao thông đường bộ.
            Phạt tiền từ 800.000 đồng đến 2.000.000 đồng đối với cá nhân là chủ xe mô tô, xe gắn máy tự ý thay đổi khung, máy, hình dáng, kích thước, đặc tính của xe (Độ xe).
            """,
            metadata={"law": "ND100", "topic": "Độ xe"},
            source="database"
        )
    ]
    
    # 1. Seed ChromaDB
    print(f"\n💾 Adding {len(sample_docs)} docs to ChromaDB...")
    try:
        vector_store.add_documents(sample_docs)
        print("✅ ChromaDB seeded successfully.")
    except Exception as e:
        print(f"❌ Failed to seed ChromaDB: {e}")

    # 2. Seed Neo4j (Optional)
    # Đây là Cypher query mẫu để tạo node
    print("\n🕸️ Seeding Neo4j (Optional)...")
    if graph_store and graph_store.graph:
        cypher_query = """
        MERGE (l:Law {name: "Nghị định 100/2019/NĐ-CP"})
        MERGE (v1:Violation {name: "Vượt đèn đỏ xe máy", fine_range: "800k - 1tr", legal_reference: "Điều 6, Khoản 4"})
        MERGE (v2:Violation {name: "Vượt đèn đỏ ô tô", fine_range: "4tr - 6tr", legal_reference: "Điều 5, Khoản 5"})
        MERGE (v1)-[:BELONGS_TO]->(l)
        MERGE (v2)-[:BELONGS_TO]->(l)
        """
        try:
            graph_store.run_cypher(cypher_query)
            print("✅ Neo4j seeded successfully.")
        except Exception as e:
            print(f"⚠️ Failed to seed Neo4j: {e}")
    else:
        print("⚠️ Neo4j connection not available. Skipping.")

    print("\n🎉 Seeding Complete!")

if __name__ == "__main__":
    seed()
