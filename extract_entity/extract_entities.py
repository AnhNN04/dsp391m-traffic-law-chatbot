"""
extract_entities.py
===================
Script trích xuất Entity và Relationship từ các Clause nodes trong Neo4j,
sau đó push ngược lên Neo4j thành Knowledge Graph thực sự.

Chạy sau khi đã push data lên Neo4j (push_to_neo4j.py):
    python extract_entities.py [--limit N] [--dry-run] [--filter-keyword KEYWORD]

Ví dụ:
    python extract_entities.py --limit 20 --dry-run
    python extract_entities.py --filter-keyword "thẩm quyền"
    python extract_entities.py
"""

import argparse
import json
import os
import time
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from groq import Groq
from neo4j import GraphDatabase

from ontology import (
    SYSTEM_PROMPT,
    NEO4J_ENTITY_LABEL,
    NEO4J_CLAUSE_LINK_REL,
    NODE_TYPES,
    RELATIONSHIP_TYPES,
)

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR.parent / "chatbot" / ".env"
load_dotenv(ENV_FILE)

NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")

LLM_MODEL   = "llama-3.3-70b-versatile"  # Groq, hỗ trợ JSON mode
MAX_RETRIES = 3
RETRY_DELAY = 2  # giây

# Singleton Groq client
_groq_client = None

def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client



# ── LLM Helper ────────────────────────────────────────────────────────────────

def call_groq(content: str) -> Optional[Dict]:
    """
    Gọi Groq (llama-3.3-70b-versatile) để extract entities/relationships.
    Dùng JSON mode để ép LLM trả về đúng cấu trúc.
    Trả về dict nếu thành công, None nếu lỗi.
    """
    client = _get_groq_client()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Phân tích điều khoản luật giao thông sau và trích xuất "
                "entity/relationship theo ontology đã định nghĩa. "
                "Trả về JSON hợp lệ duy nhất, không thêm giải thích.\n\n"
                f"<dieu_khoan>\n{content}\n</dieu_khoan>"
            ),
        },
    ]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=1024,
            )
            raw = response.choices[0].message.content.strip()
            # Groq JSON mode thường không cần strip markdown,
            # nhưng vẫn đề phòng:
            raw = re.sub(r"^```(?:json)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON parse error (lần {attempt}): {e}")
            if attempt == MAX_RETRIES:
                return None
            time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"  ⚠️  LLM error (lần {attempt}): {e}")
            if attempt == MAX_RETRIES:
                return None
            time.sleep(RETRY_DELAY)
    return None



# ── Validation ────────────────────────────────────────────────────────────────

def validate_output(data: Dict) -> Tuple[bool, str]:
    """
    Kiểm tra output của LLM để đảm bảo entity IDs tồn tại và
    relationship types/node types nằm trong Ontology.
    Trả về (is_valid, error_message).
    """
    if not isinstance(data, dict):
        return False, "Output không phải dict"
    if "is_applicable" not in data:
        return False, "Thiếu trường is_applicable"
    if not data.get("is_applicable", False):
        return True, ""  # Không áp dụng — valid nhưng skip

    entities = data.get("entities", [])
    relationships = data.get("relationships", [])
    entity_ids = {e["id"] for e in entities if "id" in e}

    # Validate entity types
    for e in entities:
        if e.get("type") not in NODE_TYPES:
            return False, f"Entity type không hợp lệ: {e.get('type')}"
        if not e.get("name", "").strip():
            return False, f"Entity name rỗng: {e}"

    # Validate relationships
    for r in relationships:
        if r.get("type") not in RELATIONSHIP_TYPES:
            return False, f"Relationship type không hợp lệ: {r.get('type')}"
        if r.get("from_id") not in entity_ids:
            return False, f"from_id '{r.get('from_id')}' không tồn tại trong entities"
        if r.get("to_id") not in entity_ids:
            return False, f"to_id '{r.get('to_id')}' không tồn tại trong entities"

    return True, ""


# ── Normalization ─────────────────────────────────────────────────────────────

def normalize_entity_name(name: str) -> str:
    """
    Chuẩn hóa tên entity để dùng làm unique key trong Neo4j MERGE.
    Lowercase, bỏ dấu câu thừa, normalize unicode.
    """
    name = unicodedata.normalize("NFC", name)
    name = name.strip()
    # Bỏ trailing dấu chấm phẩy/chấm
    name = re.sub(r"[;.]+$", "", name).strip()
    # Normalize whitespace
    name = re.sub(r"\s+", " ", name)
    return name


def extract_amount_vnd(name: str) -> Optional[int]:
    """Thử parse mức tiền phạt từ tên entity PENALTY_AMOUNT."""
    # Ví dụ: "10.000.000 đồng", "từ 1.000.000 đồng đến 2.000.000 đồng"
    numbers = re.findall(r"[\d.]+(?=\s*(?:đồng|triệu))", name.replace(",", "."))
    parsed = []
    for n in numbers:
        try:
            # Xử lý dấu chấm ngăn cách hàng nghìn (1.000.000)
            val = float(re.sub(r'\.(?=\d{3}(?:\.|$))', '', n).replace(".", "."))
            parsed.append(int(val))
        except ValueError:
            pass
    return max(parsed) if parsed else None


# ── Neo4j Push ────────────────────────────────────────────────────────────────

Q_CREATE_CONSTRAINTS = [
    f"""CREATE CONSTRAINT kg_entity_unique IF NOT EXISTS
        FOR (e:{NEO4J_ENTITY_LABEL}) REQUIRE (e.normalized_name, e.type) IS NODE KEY""",
]

Q_CREATE_FULLTEXT_INDEX = f"""
CREATE FULLTEXT INDEX kg_entity_fulltext IF NOT EXISTS
FOR (e:{NEO4J_ENTITY_LABEL}) ON EACH [e.name, e.normalized_name]
"""

Q_MERGE_ENTITY = f"""
MERGE (e:{NEO4J_ENTITY_LABEL} {{normalized_name: $normalized_name, type: $type}})
ON CREATE SET e.name         = $name,
              e.type         = $type,
              e.amount_vnd   = $amount_vnd,
              e.created_at   = datetime()
ON MATCH  SET e.name         = CASE WHEN size($name) > size(e.name) THEN $name ELSE e.name END,
              e.updated_at   = datetime()
RETURN e
"""

Q_MERGE_CLAUSE_ENTITY_REL = f"""
MATCH (cl:Clause {{id: $clause_id}})
MATCH (e:{NEO4J_ENTITY_LABEL} {{normalized_name: $normalized_name, type: $type}})
MERGE (cl)-[:{NEO4J_CLAUSE_LINK_REL}]->(e)
"""

Q_MERGE_ENTITY_REL = f"""
MATCH (from_e:{NEO4J_ENTITY_LABEL} {{normalized_name: $from_norm, type: $from_type}})
MATCH (to_e:{NEO4J_ENTITY_LABEL} {{normalized_name: $to_norm, type: $to_type}})
MERGE (from_e)-[r:`$rel_type`]->(to_e)
ON CREATE SET r.source_clause = $clause_id, r.created_at = datetime()
"""

Q_MARK_CLAUSE_EXTRACTED = """
MATCH (cl:Clause {id: $clause_id})
SET cl.kg_extracted = true
"""

def init_kg_schema(driver):
    """Tạo constraints và index cho KGEntity nodes."""
    with driver.session() as session:
        for cql in Q_CREATE_CONSTRAINTS:
            try:
                session.run(cql)
            except Exception as e:
                # Node key constraint phức tạp hơn, thử fallback
                try:
                    fallback = f"""CREATE CONSTRAINT kg_entity_unique_name IF NOT EXISTS
                        FOR (e:{NEO4J_ENTITY_LABEL}) REQUIRE e.normalized_name IS UNIQUE"""
                    session.run(fallback)
                except Exception:
                    pass
        try:
            session.run(Q_CREATE_FULLTEXT_INDEX)
            print("  ✅ Fulltext index kg_entity_fulltext created")
        except Exception as e:
            print(f"  ℹ️  Fulltext index: {e}")
    print("✅ KG schema initialized\n")


def push_entities_to_neo4j(
    driver,
    clause_id: str,
    entities: List[Dict],
    relationships: List[Dict],
    dry_run: bool = False,
) -> int:
    """
    Đẩy entities và relationships vào Neo4j.
    Trả về số entities đã push.
    """
    if not entities:
        return 0

    # Build lookup: id -> entity dict (với normalized_name và amount_vnd)
    id_to_entity = {}
    for e in entities:
        norm = normalize_entity_name(e["name"])
        amount = extract_amount_vnd(e["name"]) if e["type"] == "PENALTY_AMOUNT" else None
        id_to_entity[e["id"]] = {
            "name": e["name"],
            "type": e["type"],
            "normalized_name": norm,
            "amount_vnd": amount,
        }

    if dry_run:
        print(f"    [DRY-RUN] Sẽ tạo {len(entities)} entities, {len(relationships)} relationships")
        for e in id_to_entity.values():
            print(f"      [{e['type']}] {e['name']}")
        for r in relationships:
            f = id_to_entity.get(r["from_id"], {})
            t = id_to_entity.get(r["to_id"], {})
            print(f"      ({f.get('name', '?')}) -[:{r['type']}]-> ({t.get('name', '?')})")
        return len(entities)

    with driver.session() as session:
        # 1. Tạo / upsert entity nodes
        for e_info in id_to_entity.values():
            try:
                session.run(Q_MERGE_ENTITY, {
                    "name":            e_info["name"],
                    "type":            e_info["type"],
                    "normalized_name": e_info["normalized_name"],
                    "amount_vnd":      e_info["amount_vnd"],
                }).consume()
            except Exception as e:
                print(f"      ⚠️ Entity push error: {e}")

        # 2. Link Clause -> KGEntity
        for e_info in id_to_entity.values():
            try:
                session.run(Q_MERGE_CLAUSE_ENTITY_REL, {
                    "clause_id":      clause_id,
                    "normalized_name": e_info["normalized_name"],
                    "type":           e_info["type"],
                }).consume()
            except Exception:
                pass  # Clause không tồn tại thì bỏ qua

        # 3. Tạo semantic relationships giữa entities
        for r in relationships:
            from_e = id_to_entity.get(r["from_id"])
            to_e   = id_to_entity.get(r["to_id"])
            if not from_e or not to_e:
                continue
            rel_type = r["type"]
            # Dùng dynamic Cypher vì relationship type không thể parameterize
            cypher = f"""
            MATCH (from_e:{NEO4J_ENTITY_LABEL} {{normalized_name: $from_norm, type: $from_type}})
            MATCH (to_e:{NEO4J_ENTITY_LABEL} {{normalized_name: $to_norm, type: $to_type}})
            MERGE (from_e)-[r:`{rel_type}`]->(to_e)
            ON CREATE SET r.source_clause = $clause_id, r.created_at = datetime()
            """
            try:
                session.run(cypher, {
                    "from_norm":  from_e["normalized_name"],
                    "from_type":  from_e["type"],
                    "to_norm":    to_e["normalized_name"],
                    "to_type":    to_e["type"],
                    "clause_id":  clause_id,
                }).consume()
            except Exception as e:
                print(f"      ⚠️ Rel push error: {e}")

    return len(entities)


def mark_clause_extracted(driver, clause_id: str, dry_run: bool = False):
    """Đánh dấu Clause đã được LLM xử lý xong (kể cả không có thực thể nào) để bỏ qua lần chạy sau."""
    if dry_run:
        return
    try:
        with driver.session() as session:
            session.run(Q_MARK_CLAUSE_EXTRACTED, {"clause_id": clause_id}).consume()
    except Exception as e:
        print(f"      ⚠️ Lỗi khi đánh dấu extracted cho {clause_id}: {e}")

# ── Fetch Clauses ─────────────────────────────────────────────────────────────

def fetch_clauses(driver, limit: Optional[int] = None, filter_keyword: Optional[str] = None, force_reindex: bool = False) -> List[Dict]:
    """
    Lấy tất cả Clause nodes (và Article nếu không có clause) từ Neo4j.
    Hỗ trợ lọc theo keyword trong content để test nhanh.
    Hỗ trợ bỏ qua các Clause đã được extract (resumable) nếu force_reindex=False.
    """
    where_conditions = []
    params: Dict[str, Any] = {}

    if filter_keyword:
        where_conditions.append("cl.content CONTAINS $kw")
        params["kw"] = filter_keyword
        
    if not force_reindex:
        # Bỏ qua các Clause đã được xử lý (đánh dấu bằng property kg_extracted)
        where_conditions.append("cl.kg_extracted IS NULL")

    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

    limit_clause = f"LIMIT {limit}" if limit else ""

    cypher = f"""
    MATCH (cl:Clause)
    {where_clause}
    RETURN cl.id AS id, cl.content AS content, cl.law_id AS law_id,
           cl.article_id AS article_id, cl.clause AS clause
    {limit_clause}
    """

    with driver.session() as session:
        records = list(session.run(cypher, params))

    return [dict(r) for r in records]


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Trích xuất Entity/Relationship từ Clauses Neo4j bằng Gemini Flash."
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Giới hạn số clause xử lý (để test nhanh)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Chỉ print kết quả, không push vào Neo4j")
    parser.add_argument("--filter-keyword", type=str, default=None,
                        help="Chỉ xử lý clause có chứa keyword này (VD: 'thẩm quyền')")
    parser.add_argument("--force-reindex", action="store_true",
                        help="Bắt buộc extract lại toàn bộ cả những Clause đã làm rồi")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Thời gian chờ giữa mỗi lần gọi LLM (giây, mặc định 2.0 cho Groq)")
    return parser.parse_args()


def main():
    args = parse_args()

    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        print("❌ Thiếu biến môi trường NEO4J_*.")
        return
    if not GROQ_API_KEY:
        print("❌ Thiếu GROQ_API_KEY trong .env")
        return

    print(f"🔌 Kết nối Neo4j: {NEO4J_URI}")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
        print("✅ Kết nối thành công!\n")
    except Exception as e:
        print(f"❌ Không thể kết nối Neo4j: {e}")
        return

    if not args.dry_run:
        print("⚙️  Khởi tạo KG schema (constraints + index)...")
        init_kg_schema(driver)

    # Lấy danh sách clauses
    print(f"🔍 Lấy Clauses từ Neo4j"
          + (f" (filter: '{args.filter_keyword}')" if args.filter_keyword else "")
          + (f" (limit: {args.limit})" if args.limit else "")
          + "...")
    clauses = fetch_clauses(driver, limit=args.limit, filter_keyword=args.filter_keyword, force_reindex=args.force_reindex)
    print(f"  Tìm thấy {len(clauses)} clause(s) CHƯA được extract.\n")

    if not clauses:
        print("⚠️  Không có clause nào để xử lý.")
        driver.close()
        return

    # Stats
    total_entities   = 0
    total_skipped    = 0
    total_errors     = 0
    total_applicable = 0

    print("=" * 60)
    print(f"{'DRY-RUN MODE' if args.dry_run else 'LIVE MODE'} — Bắt đầu extraction")
    print("=" * 60 + "\n")

    for i, clause in enumerate(clauses, 1):
        clause_id = clause.get("id", "unknown")
        content   = clause.get("content", "")
        law_id    = clause.get("law_id", "")
        article_id = clause.get("article_id", "")
        clause_no  = clause.get("clause", "")

        label = f"[{i}/{len(clauses)}] law={law_id} Art{article_id} Cl{clause_no}"
        print(f"--- {label} ---")
        if not content.strip():
            print("  ⚠️  Nội dung rỗng, bỏ qua.\n")
            total_skipped += 1
            continue

        # Gọi LLM (Groq)
        result = call_groq(content)
        if result is None:
            print("  ❌ LLM trả về None sau tất cả retries.\n")
            total_errors += 1
            continue

        # Validate output
        is_valid, err_msg = validate_output(result)
        if not is_valid:
            print(f"  ❌ Invalid output: {err_msg}")
            print(f"     Raw: {json.dumps(result, ensure_ascii=False)[:200]}\n")
            total_errors += 1
            continue

        # Kiểm tra is_applicable
        if not result.get("is_applicable", False):
            print("  ℹ️  Không áp dụng (định nghĩa/nguyên tắc), bỏ qua.\n")
            mark_clause_extracted(driver, clause_id, args.dry_run)
            total_skipped += 1
            continue

        total_applicable += 1
        entities = result.get("entities", [])
        relationships = result.get("relationships", [])

        n_pushed = push_entities_to_neo4j(
            driver, clause_id, entities, relationships, dry_run=args.dry_run
        )
        mark_clause_extracted(driver, clause_id, args.dry_run)
        
        total_entities += n_pushed
        print(f"  ✅ {n_pushed} entities, {len(relationships)} relationships\n")

        time.sleep(args.delay)

    driver.close()

    print("=" * 60)
    print(f"HOÀN TẤT")
    print(f"  Clauses xử lý : {len(clauses)}")
    print(f"  Áp dụng       : {total_applicable}")
    print(f"  Bỏ qua (skip) : {total_skipped}")
    print(f"  Lỗi           : {total_errors}")
    print(f"  Entities đã push: {total_entities}")
    print("=" * 60)
    if not args.dry_run:
        print("\n💡 Kiểm tra kết quả trong Neo4j Browser:")
        print("   MATCH (e:KGEntity) RETURN e.type, count(e) ORDER BY count(e) DESC")
        print("   MATCH (e:KGEntity)-[r]->(f:KGEntity) RETURN e, r, f LIMIT 30")


if __name__ == "__main__":
    main()
