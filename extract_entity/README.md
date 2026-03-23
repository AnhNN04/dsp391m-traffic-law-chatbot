# README — Extract Entity (Knowledge Graph)

## Mục tiêu

Bổ sung lớp **semantic Knowledge Graph** lên trên graph hierarchy hiện tại (`Document→Clause`).
Sau khi chạy script này, Neo4j sẽ có thêm `KGEntity` nodes kết nối với nhau qua các semantic relationship như `CÓ_QUYỀN_PHẠT_ĐẾN`, `BỊ_PHẠT`, `THỰC_HIỆN_HÀNH_VI`...

## Các file

| File | Chức năng |
|------|-----------|
| `ontology.py` | Định nghĩa lược đồ (6 node types, 8 rel types, prompt, JSON schema) |
| `extract_entities.py` | Script chính — đọc Clauses, gọi Gemini, push entity  |
| `neo4j_kg_search.py` | Cypher queries và helper class để search trong KG |
| `README.md` | Tài liệu này |

## Cài đặt

```bash
# Đảm bảo đã có các package cần thiết
pip install google-generativeai neo4j python-dotenv
```

## Sử dụng

### Test nhanh (dry-run, không push Neo4j)

```bash
cd extract_entity
python extract_entities.py --limit 5 --dry-run
```

### Chỉ xử lý clause về thẩm quyền (test focused)

```bash
python extract_entities.py --filter-keyword "có quyền" --dry-run
python extract_entities.py --filter-keyword "có quyền"      # khi đã ổn thì bỏ dry-run
```

### Chạy toàn bộ

```bash
python extract_entities.py
```

Thêm `--delay 1.0` nếu bị rate-limit bởi Gemini API:
### Reset Graph (Xóa toàn bộ KG)

Nếu bạn muốn xóa toàn bộ các Entity/Relationship do tool sinh ra để trả Neo4j về nguyên thủy:
```bash
python cleanup_kg.py
```
*(Lệnh này chỉ xóa node `KGEntity`, các node luật gốc `Clause` vẫn an toàn tuyệt đối).*

## Kiểm tra kết quả trong Neo4j Browser

```cypher
// Thống kê entity theo loại
MATCH (e:KGEntity) RETURN e.type, count(e) ORDER BY count(e) DESC

// Visualize semantic relationships
MATCH (e:KGEntity)-[r]->(f:KGEntity)
RETURN e, r, f LIMIT 50

// Tìm thẩm quyền phạt tiền
MATCH (a:KGEntity {type:'AUTHORITY'})-[:CÓ_QUYỀN_PHẠT_ĐẾN]->(p:KGEntity {type:'PENALTY_AMOUNT'})
RETURN a.name, p.name, p.amount_vnd ORDER BY p.amount_vnd DESC

// Traverse từ entity về clause gốc
MATCH (cl:Clause)-[:HAS_ENTITY]->(e:KGEntity)
WHERE e.name CONTAINS 'Thanh tra'
RETURN cl.content, e.name, e.type LIMIT 10
```

## Ontology (Lược đồ)

### Node Types
| Type | Ý nghĩa | Ví dụ |
|------|---------|-------|
| `AUTHORITY` | Cơ quan có thẩm quyền xử phạt | "Cảnh sát giao thông" |
| `PENALTY_ACTION` | Hình thức xử phạt / Biện pháp | "Tịch thu tang vật" |
| `PENALTY_AMOUNT` | Mức tiền phạt | "10.000.000 đồng" |
| `VIOLATION` | Hành vi vi phạm | "chạy quá tốc độ" |
| `SUBJECT` | Đối tượng vi phạm | "người điều khiển xe máy" |
| `VEHICLE` | Phương tiện giao thông | "xe ô tô" |

### Relationship Types
| Relationship | Từ → Đến |
|-------------|---------|
| `CÓ_QUYỀN_ÁP_DỤNG` | AUTHORITY → PENALTY_ACTION |
| `CÓ_QUYỀN_PHẠT_ĐẾN` | AUTHORITY → PENALTY_AMOUNT |
| `QUY_ĐỊNH_THẨM_QUYỀN` | Clause → AUTHORITY |
| `THỰC_HIỆN_HÀNH_VI` | SUBJECT → VIOLATION |
| `ĐIỀU_KHIỂN` | SUBJECT → VEHICLE |
| `BỊ_PHẠT` | VIOLATION → PENALTY_AMOUNT |
| `BỊ_ÁP_DỤNG` | VIOLATION → PENALTY_ACTION |
| `QUY_ĐỊNH_HÀNH_VI` | Clause → VIOLATION |
