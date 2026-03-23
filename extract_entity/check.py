import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR.parent / "chatbot" / ".env"
load_dotenv(ENV_FILE)

d = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

print("Nodes:")
print(d.execute_query("MATCH (e:KGEntity) RETURN count(e) AS c").records[0]["c"])

print("Relationships:")
print(d.execute_query("MATCH ()-[r]->() WHERE type(r) IN ['CÓ_QUYỀN_PHẠT_ĐẾN', 'THỰC_HIỆN_HÀNH_VI', 'CÓ_QUYỀN_ÁP_DỤNG', 'BỊ_PHẠT', 'BỊ_ÁP_DỤNG', 'ĐIỀU_KHIỂN'] RETURN count(r) AS c").records[0]["c"])
