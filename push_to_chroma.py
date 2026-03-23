import os
import json
import glob
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / "chatbot" / ".env"
load_dotenv(ENV_FILE)

# Lấy cấu hình từ .env
# Vì CHROMA_PERSIST_DIR trong .env có dạng './data/chroma_db' và chạy từ thư mục chatbot/
# nên script này nằm ở root, ta cần nối thêm 'chatbot/' vào trước.
chroma_dir_env = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
if chroma_dir_env.startswith("./"):
    chroma_dir_env = chroma_dir_env[2:]
CHROMA_PATH = BASE_DIR / "chatbot" / chroma_dir_env
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "traffic_law")

CHUNK_DIR = BASE_DIR / "chunk"

# ── ID Generators (Bản sao từ push_to_neo4j) ──────────────────────────────────
# Cực kỳ quan trọng: Định danh ID trong Chroma phải trùng khớp 100% với Graph Neo4j
# thì Hybrid Search trên chatbot mới bắt tay nhau được.

def make_article_node_id(law_id: str, article_id: str) -> str:
    return f"{law_id}::Art{article_id}"

def make_clause_node_id(law_id: str, article_id: str, clause: str) -> str:
    return f"{law_id}::Art{article_id}::Cl{clause}"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"📁 ChromaDB Path:   {CHROMA_PATH}")
    print(f"📦 Collection Name: {COLLECTION_NAME}")
    
    # 1. Khởi tạo Chroma Client và Collection
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    # Lấy danh sách file json
    json_files = glob.glob(str(CHUNK_DIR / "*.json"))
    if not json_files:
        print("❌ Không tìm thấy file JSON nào trong thư mục chunk/")
        return
        
    print(f"🔍 Tìm thấy {len(json_files)} file JSON. Bắt đầu đẩy dữ liệu...")
    
    total_docs = 0
    
    for file_path in json_files:
        filename = os.path.basename(file_path)
        print(f"\n📄 Đang xử lý file: {filename}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        seen_ids = set()
        
        for item in tqdm(data, desc="Đọc chunks"):
            # Bỏ sót dữ liệu nếu lỗi
            if "embedding" not in item or not item["embedding"]:
                continue
                
            # Tạo ID chuẩn như Neo4j
            law_id = item.get("law_id")
            article_id = item.get("article_id")
            clause = item.get("clause")
            
            if not law_id or not article_id:
                continue
                
            if clause:
                doc_id = make_clause_node_id(str(law_id), str(article_id), str(clause))
            else:
                doc_id = make_article_node_id(str(law_id), str(article_id))
                
            # Tạo Metadata (loại bỏ các trường dài dòng để nhẹ DB)
            metadata = {
                "law_id": str(law_id),
                "type": str(item.get("type", "")),
                "article_id": str(article_id)
            }
            if clause:
                metadata["clause"] = str(clause)
                
            # Deduplicate ID (Xử lý trường hợp 1 Clause dài bị cắt làm nhiều chunk nhỏ)
            base_id = doc_id
            counter = 1
            while doc_id in seen_ids:
                doc_id = f"{base_id}_{counter}"
                counter += 1
            seen_ids.add(doc_id)
                
            # Lấy trường nội dung
            content = item.get("content", "")
            if not content:
                continue
                
            ids.append(doc_id)
            documents.append(content)
            embeddings.append(item["embedding"])
            metadatas.append(metadata)
            
        if ids:
            # Upsert theo batch để tránh tràn RAM (Chroma khuyến nghị batch ~5000 -> 40000, 
            # chúng ta có vài nghìn cứ push 1 cục 500 cho an toàn hoặc push hết cũng OK vì size < 10000)
            batch_size = 1000
            for i in range(0, len(ids), batch_size):
                end_idx = i + batch_size
                try:
                    collection.upsert(
                        ids=ids[i:end_idx],
                        documents=documents[i:end_idx],
                        embeddings=embeddings[i:end_idx],
                        metadatas=metadatas[i:end_idx]
                    )
                except Exception as e:
                    print(f"❌ Lỗi khi Upsert batch {i}-{end_idx}: {e}")
                    
            print(f"  ✅ Đã Upsert {len(ids)} chunks vào ChromaDB.")
            total_docs += len(ids)
            
    # Hiển thị thống kê
    print(f"\n============================================================")
    print(f"HOÀN TẤT")
    print(f"  Tổng số files : {len(json_files)}")
    print(f"  Tổng số chunks: {total_docs}")
    print(f"  ChromaDB Path : {CHROMA_PATH}")
    print(f"  Total DB size : {collection.count()} tài liệu hiện có")
    print(f"============================================================")
    print("Mọi thứ đã sẵn sàng cho Vector Search độc lập!")

if __name__ == "__main__":
    main()
