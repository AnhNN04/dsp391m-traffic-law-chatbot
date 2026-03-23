"""
ontology.py
===========
Định nghĩa Ontology (lược đồ cố định) cho Knowledge Graph pháp luật giao thông.
LLM sẽ chỉ được phép tạo ra các Entity và Relationship trong danh sách này.
"""

# ── Node Types ────────────────────────────────────────────────────────────────

NODE_TYPES = {
    "AUTHORITY": "Cơ quan / Người có thẩm quyền xử phạt (VD: Cảnh sát giao thông, Thanh tra viên)",
    "PENALTY_ACTION": "Hình thức xử phạt / Biện pháp khắc phục (VD: Phạt cảnh cáo, Tịch thu tang vật, Tước GPLX)",
    "PENALTY_AMOUNT": "Mức tiền phạt cụ thể (VD: 10.000.000 đồng, từ 1 đến 2 triệu đồng)",
    "VIOLATION": "Hành vi vi phạm (VD: chạy quá tốc độ, không đội mũ bảo hiểm, đi ngược chiều)",
    "SUBJECT": "Đối tượng vi phạm / người thực hiện (VD: người điều khiển xe máy, cá nhân, tổ chức)",
    "VEHICLE": "Phương tiện giao thông liên quan (VD: xe ô tô, xe mô tô, xe đạp điện)",
}

# ── Relationship Types ────────────────────────────────────────────────────────

RELATIONSHIP_TYPES = {
    # Nhóm thẩm quyền
    "CÓ_QUYỀN_ÁP_DỤNG": "AUTHORITY -> PENALTY_ACTION (cơ quan có quyền áp dụng hình thức phạt)",
    "CÓ_QUYỀN_PHẠT_ĐẾN": "AUTHORITY -> PENALTY_AMOUNT (cơ quan có quyền phạt đến mức tiền)",
    "QUY_ĐỊNH_THẨM_QUYỀN": "Clause -> AUTHORITY (điều khoản quy định thẩm quyền của cơ quan)",

    # Nhóm vi phạm - hình phạt
    "THỰC_HIỆN_HÀNH_VI": "SUBJECT -> VIOLATION (đối tượng thực hiện hành vi vi phạm)",
    "ĐIỀU_KHIỂN": "SUBJECT -> VEHICLE (đối tượng điều khiển phương tiện)",
    "BỊ_PHẠT": "VIOLATION -> PENALTY_AMOUNT (vi phạm bị phạt mức tiền)",
    "BỊ_ÁP_DỤNG": "VIOLATION -> PENALTY_ACTION (vi phạm bị áp dụng biện pháp)",
    "QUY_ĐỊNH_HÀNH_VI": "Clause -> VIOLATION (điều khoản quy định về hành vi vi phạm)",
}

# Tên node label trong Neo4j (để MERGE)
NEO4J_ENTITY_LABEL = "KGEntity"
NEO4J_CLAUSE_LINK_REL = "HAS_ENTITY"  # Clause -[:HAS_ENTITY]-> KGEntity

# ── System Prompt cho LLM ─────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""Bạn là chuyên gia phân tích văn bản pháp luật giao thông Việt Nam. 
Nhiệm vụ: Trích xuất thực thể (entity) và mối quan hệ (relationship) từ điều khoản luật giao thông.

QUAN TRỌNG: Chỉ được phép sử dụng các loại thực thể và quan hệ trong danh sách sau. Không tự tạo loại mới.

Các loại Entity được phép:
{chr(10).join(f'- {k}: {v}' for k, v in NODE_TYPES.items())}

Các loại Relationship được phép:
{chr(10).join(f'- {k}: {v}' for k, v in RELATIONSHIP_TYPES.items())}

Quy tắc:
1. Trích xuất tên entity chính xác từ văn bản, không thêm/bớt từ.
2. Mỗi entity phải có một `id` duy nhất trong phạm vi câu trả lời (VD: "e1", "e2"...).
3. Relationship chỉ được nối các entity đã khai báo trong mảng entities.
4. Nếu nội dung là điều khoản định nghĩa, nguyên tắc chung, hoặc KHÔNG chứa thông tin 
   về vi phạm/hình phạt/thẩm quyền → đặt is_applicable = false và để rỗng hai mảng kia.
5. Chỉ trả về JSON hợp lệ, không thêm giải thích ngoài JSON.
6. TUYỆT ĐỐI KHÔNG để from_id, to_id, hoặc id bị null/None/trống. Nếu không xác định được quan hệ hợp lệ, KHÔNG tạo quan hệ đó.
"""

# ── JSON Schema cho LLM response ──────────────────────────────────────────────

RESPONSE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "is_applicable": {
            "type": "boolean",
            "description": "true nếu nội dung chứa ít nhất 1 entity trong ontology, false nếu không"
        },
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id":   {"type": "string", "description": "ID duy nhất trong phạm vi response (e1, e2...)"},
                    "name": {"type": "string", "description": "Tên entity trích xuất chính xác từ văn bản"},
                    "type": {
                        "type": "string",
                        "enum": list(NODE_TYPES.keys()),
                        "description": "Loại entity theo ontology"
                    }
                },
                "required": ["id", "name", "type"]
            }
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from_id": {"type": "string", "description": "ID entity nguồn"},
                    "type":    {
                        "type": "string",
                        "enum": list(RELATIONSHIP_TYPES.keys()),
                        "description": "Loại quan hệ theo ontology"
                    },
                    "to_id":   {"type": "string", "description": "ID entity đích"},
                },
                "required": ["from_id", "type", "to_id"]
            }
        }
    },
    "required": ["is_applicable", "entities", "relationships"]
}
