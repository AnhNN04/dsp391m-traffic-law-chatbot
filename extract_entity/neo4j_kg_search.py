"""
neo4j_kg_search.py
==================
Các Cypher query để tìm kiếm trong Knowledge Graph (KGEntity nodes).
Sử dụng trong neo4j_repo.py như Strategy 4: Entity Graph Traversal.

Import và dùng trong neo4j_repo.py:
    from extract_entity.neo4j_kg_search import KGEntitySearch
"""

from typing import List, Optional, Dict, Any


# ── Cypher Queries ────────────────────────────────────────────────────────────

# Tìm entity theo keyword, rồi traverse ra các clause gốc + related entities
Q_ENTITY_GRAPH_SEARCH = """
// Bước 1: Tìm KGEntity khớp keyword bằng fulltext
CALL db.index.fulltext.queryNodes('kg_entity_fulltext', $query, {limit: 10})
YIELD node AS entity, score

// Bước 2: Traverse các semantic relationship
OPTIONAL MATCH (entity)-[r1]-(related:KGEntity)

// Bước 3: Leo ngược lên Clause gốc (qua HAS_ENTITY)
OPTIONAL MATCH (source_clause:Clause)-[:HAS_ENTITY]->(entity)

// Bước 4: Lấy context đầy đủ từ Clause (kèm Article parent)
OPTIONAL MATCH (source_clause)<-[:HAS_CLAUSE]-(article:Article)

RETURN
  entity.name       AS entity_name,
  entity.type       AS entity_type,
  collect(DISTINCT {name: related.name, type: related.type, rel: type(r1)}) AS related_entities,
  source_clause.content  AS clause_content,
  source_clause.id       AS clause_id,
  article.article        AS article_name,
  article.article_id     AS article_id,
  score
ORDER BY score DESC
LIMIT $limit
"""

# Tìm authority và quyền phạt của họ (Cypert trực tiếp cho câu hỏi về thẩm quyền)
Q_AUTHORITY_PENALTY_SEARCH = """
MATCH (a:KGEntity {type: 'AUTHORITY'})-[r:CÓ_QUYỀN_PHẠT_ĐẾN|CÓ_QUYỀN_ÁP_DỤNG]->(p:KGEntity)
WHERE a.name CONTAINS $keyword OR a.normalized_name CONTAINS $keyword
OPTIONAL MATCH (cl:Clause)-[:HAS_ENTITY]->(a)
RETURN
  a.name      AS authority,
  type(r)     AS relationship,
  p.name      AS penalty,
  p.type      AS penalty_type,
  p.amount_vnd AS amount_vnd,
  cl.content  AS source_content
ORDER BY p.amount_vnd DESC NULLS LAST
LIMIT $limit
"""

# Tìm vi phạm và mức phạt tương ứng
Q_VIOLATION_PENALTY_SEARCH = """
MATCH (v:KGEntity {type: 'VIOLATION'})-[:BỊ_PHẠT|BỊ_ÁP_DỤNG]->(p:KGEntity)
WHERE v.name CONTAINS $keyword OR v.normalized_name CONTAINS $keyword
OPTIONAL MATCH (cl:Clause)-[:HAS_ENTITY]->(v)
RETURN
  v.name      AS violation,
  p.name      AS penalty,
  p.type      AS penalty_type,
  p.amount_vnd AS amount_vnd,
  cl.content  AS source_content
ORDER BY p.amount_vnd DESC NULLS LAST
LIMIT $limit
"""

# Stats - dùng cho debug/monitoring
Q_KG_STATS = """
MATCH (e:KGEntity)
RETURN e.type AS entity_type, count(e) AS count
ORDER BY count DESC
"""


# ── Helper Class (Optional, tích hợp vào neo4j_repo.py nếu muốn) ─────────────

class KGEntitySearch:
    """
    Wrapper để gọi các KG search queries.
    Sử dụng trong neo4j_repo.py bằng cách kế thừa hoặc composition.
    """

    def __init__(self, driver):
        self.driver = driver

    def entity_graph_search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Tìm entity theo keyword rồi trả về context đầy đủ từ clause gốc.
        Dùng như Strategy 4 bổ sung vào get_penalty_info().
        """
        try:
            with self.driver.session() as session:
                records = list(session.run(Q_ENTITY_GRAPH_SEARCH, {
                    "query": query,
                    "limit": limit,
                }))
            return [dict(r) for r in records]
        except Exception as e:
            return []

    def authority_penalty_search(self, keyword: str, limit: int = 5) -> List[Dict]:
        """Tìm quyền phạt của một cơ quan/chức danh cụ thể."""
        try:
            with self.driver.session() as session:
                records = list(session.run(Q_AUTHORITY_PENALTY_SEARCH, {
                    "keyword": keyword,
                    "limit": limit,
                }))
            return [dict(r) for r in records]
        except Exception:
            return []

    def violation_penalty_search(self, keyword: str, limit: int = 5) -> List[Dict]:
        """Tìm mức phạt cho một hành vi vi phạm cụ thể."""
        try:
            with self.driver.session() as session:
                records = list(session.run(Q_VIOLATION_PENALTY_SEARCH, {
                    "keyword": keyword,
                    "limit": limit,
                }))
            return [dict(r) for r in records]
        except Exception:
            return []

    def get_kg_stats(self) -> List[Dict]:
        """Thống kê số lượng entity theo từng loại."""
        try:
            with self.driver.session() as session:
                records = list(session.run(Q_KG_STATS))
            return [dict(r) for r in records]
        except Exception:
            return []
