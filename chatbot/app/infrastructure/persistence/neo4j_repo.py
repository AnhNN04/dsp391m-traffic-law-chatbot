"""
Neo4j Graph Store Implementation

Concrete implementation of IGraphStore using Neo4j.
Schema: (:Law)-[:HAS_CHAPTER]->(:Chapter)-[:HAS_ARTICLE]->(:Article)-[:HAS_CLAUSE]->(:Clause)

Supports:
  - Vector similarity search (via clause_embedding index, 384 dims)
  - Fulltext keyword search (via clause_fulltext index)
  - Graph traversal queries

Author: AnhNN217-FHN
"""

from typing import List, Optional, Dict, Any
from neo4j import GraphDatabase

from app.domain.interfaces import IGraphStore
from app.domain.entities import LegalDocument, Violation, DocumentSource
from app.domain.exceptions import GraphStoreError, DatabaseConnectionError, CypherQueryError
from app.infrastructure.config import get_logger, settings

logger = get_logger(__name__)

# Lazy-load embedding model để tránh import nặng khi khởi động
# Model này tạo ra vector 768 chiều khớp với vector.dimensions trong push_to_neo4j.py
_EMBED_MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
_embed_model = None


def _get_embed_model():
    """Lazy-load embedding model (singleton)."""
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {_EMBED_MODEL_NAME}")
        _embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
        logger.info("Embedding model loaded")
    return _embed_model


def _embed_text(text: str) -> List[float]:
    """Embed a single text string."""
    model = _get_embed_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


class Neo4jRepo(IGraphStore):
    """
    Neo4j implementation of IGraphStore.

    Data schema in Neo4j:
        (:Law {law_id, type, law_name})
            -[:HAS_CHAPTER]->
        (:Chapter {law_id, chapter_id, chapter_name})
            -[:HAS_ARTICLE]->
        (:Article {law_id, article_id, article, section})
            -[:HAS_CLAUSE]->
        (:Clause {law_id, article_id, clause, content, embed_content,
                  vector_embedding, law_name, type})

    Indexes:
        - clause_embedding  : VECTOR INDEX on Clause.vector_embedding (384, cosine)
        - clause_fulltext   : FULLTEXT INDEX on Clause.content + embed_content
    """

    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        database: Optional[str] = None  # None = use server default (works with AuraDB)
    ):
        self.uri = uri
        self.database = database

        try:
            logger.info(f"Connecting to Neo4j: {uri} (db={database})")
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1").single()
            logger.info(f"Neo4j connection established: {uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {type(e).__name__}: {e}")
            raise DatabaseConnectionError(
                f"Failed to connect to Neo4j: {e}",
                database_type="Neo4j",
                connection_string=uri
            ) from e

    # ==================== PRIMARY SEARCH METHODS ====================

    def get_penalty_info(self, violation_desc: str, limit: int = 10) -> List[LegalDocument]:
        """
        Tìm kiếm thông tin quy định, mức phạt kết hợp Phrase + Vector + Fulltext + Graph Search.
        Luồng: 
          1) Extract keyword -> 2) Detect Law ID -> 3) Phrase Search -> 4) Vector Search -> 5) Fulltext Search.
          Kết quả được gộp (chống trùng) và rải về LLM.
        """
        logger.debug(f"Searching Neo4j: {violation_desc[:80]}")

        results = []
        search_terms = self._extract_keywords(violation_desc)
        logger.debug(f"Search terms: {search_terms}")

        seen: set = set()

        def add_docs(docs):
            for doc in docs:
                key = doc.content[:100]
                if key not in seen:
                    results.append(doc)
                    seen.add(key)

        try:
            # Strategy 0: Law-specific (nếu hỏi về một nghị định cụ thể)
            law_num = self._detect_law_number(violation_desc)
            if law_num:
                law_docs = self._search_by_law_id(law_num, limit=10)
                add_docs(law_docs)
                logger.debug(f"Law-specific '{law_num}': {len(law_docs)} docs")

            # Strategy 1: Phrase search — độ chính xác cao nhất (chạy TRƯỚC vector)
            phrase_docs = self._phrase_search(search_terms, limit=10)
            add_docs(phrase_docs)

            # Strategy 2: Vector semantic search
            vector_docs = self._vector_search(search_terms, limit=10)
            add_docs(vector_docs)

            # Strategy 3: Fulltext keyword search (bổ sung)
            keyword_docs = self._fulltext_search(search_terms, limit=10)
            add_docs(keyword_docs)

            # Sắp xếp lại tổng hợp các tài liệu theo điểm score giảm dần để giữ lại những kết quả tốt nhất
            results.sort(key=lambda x: getattr(x, "score", 0.0) or 0.0, reverse=True)

            logger.debug(f"Neo4j search complete: {len(results)} docs, returning top {limit}")
            return results[:limit]

        except Exception as e:
            logger.error(f"Neo4j search failed: {e}")
            raise GraphStoreError(f"Failed to search: {str(e)}") from e

    def _extract_keywords(self, query: str) -> str:
        """Trích xuất từ khóa từ câu hỏi, bỏ các cụm không cần thiết và map từ đồng nghĩa."""
        import re
        # Bỏ các cụm hỏi thông thường
        patterns = [
            r'\bcó sao không\??',
            r'\bcó bị phạt không\??',
            r'\bphạt bao nhiêu\??',
            r'\bquy định (gì|điều gì|như thế nào)\??',
            r'\bnhư thế nào\??',
            r'\bcó được không\??',
            r'\blà gì\??',
            r'\bcho tôi biết\b',
            r'\bhãy cho biết\b',
            r'\bcho hỏi\b',
        ]
        cleaned = query
        for p in patterns:
            cleaned = re.sub(p, ' ', cleaned, flags=re.IGNORECASE)
            
        # Map từ đồng nghĩa dân dã sang từ khóa luật pháp nghiêm ngặt
        synonyms = {
            r'\b(uống|nhậu|xỉn|say) (rượu|bia)\b': 'nồng độ cồn',
            r'\b(lấn|chèn|đè) vạch\b': 'vạch kẻ đường',
            r'\b(vượt đèn|đèn đỏ|đèn vàng)\b': 'tín hiệu đèn giao thông',
            r'\b(quay đầu|quẹo)\b': 'chuyển hướng',
            r'\b(bắn tốc độ|chạy quá tốc độ|chạy nhanh)\b': 'tốc độ',
            r'\b(ngược chiều)\b': 'đi ngược chiều',
            r'\b(kẹp 3|chở 3)\b': 'chở quá số người',
            r'\b(kẹp nách|vỉa hè)\b': 'trên hè phố',
            r'\b(bỏ chạy|tẩu thoát)\b': 'gây tai nạn giao thông không dừng lại',
            r'\b(bốc đầu|bốc đít|đánh võng|lạng lách)\b': 'lạng lách đánh võng',
            r'\b(không nhường đường)\b': 'không nhường đường', 
            r'\b(xe ưu tiên|cứu thương|cứu hỏa|cảnh sát)\b': 'xe ưu tiên',
        }
        for pattern, replacement in synonyms.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
            
        cleaned = ' '.join(cleaned.split())  # normalize whitespace
        return cleaned.strip() or query

    def _detect_law_number(self, query: str) -> Optional[str]:
        """Phát hiện số nghị định/luật trong câu hỏi. VD: 'nghị định 168' → '168'."""
        import re
        match = re.search(r'(?:nghị định|nd|nđ|decree)\s*(\d{2,4})', query, re.IGNORECASE)
        if match:
            return match.group(1)  # "168", "336", v.v.
        return None

    def _search_by_law_id(self, law_num: str, limit: int = 5) -> List[LegalDocument]:
        """Lấy các điều khoản scope (Điều 1, 2 đầu) của nghị định theo số hiệu."""
        try:
            cypher = """
            MATCH (l:Document)-[:HAS_CHAPTER]->(c)-[:HAS_ARTICLE]->(a)-[:HAS_CLAUSE]->(cl)
            WHERE l.law_id CONTAINS $law_num
            RETURN cl.content AS content,
                   cl.article_id AS article_id,
                   cl.clause AS clause,
                   l.law_name AS law_name,
                   l.law_id AS law_id,
                   toInteger(cl.article_id) AS art_order
            ORDER BY art_order ASC, toInteger(cl.clause) ASC
            LIMIT $limit
            """
            with self.driver.session() as session:
                records = list(session.run(cypher, {"law_num": law_num, "limit": limit}))

            docs = []
            for r in records:
                doc = LegalDocument(
                    content=r["content"] or "",
                    source=DocumentSource.GRAPH_STORE,
                    metadata={
                        "search_type": "law_specific",
                        "article_id": r["article_id"],
                        "clause": r["clause"],
                        "law_id": r["law_id"],
                    },
                    article_id=r["article_id"],
                    law_name=r["law_name"],
                    score=0.95  # high score vì exact law match
                )
                docs.append(doc)
            return docs
        except Exception as e:
            logger.warning(f"Law-specific search for '{law_num}' failed: {e}")
            return []


    def _vector_search(self, query: str, limit: int = 5) -> List[LegalDocument]:
        """Semantic search dùng vector index."""
        try:
            embedding = _embed_text(query)

            cypher = """
            CALL db.index.vector.queryNodes('clause_embedding', $limit, $embedding)
            YIELD node AS matched_node, score
            
            // Dò ngược lên `Article` chứa node này
            OPTIONAL MATCH (matched_node)<-[:HAS_CLAUSE]-(parent:Article)
            WITH matched_node, score, coalesce(parent, matched_node) AS article
            
            // Leo lên đỉnh đồ thị để lấy thông tin Luật (Document) qua Chapter
            OPTIONAL MATCH (article)<-[:HAS_ARTICLE]-(:Chapter)<-[:HAS_CHAPTER]-(doc:Document)
            
            // Tìm tất cả các Clause con của Article này để lấy ngữ cảnh trọn vẹn
            OPTIONAL MATCH (article)-[:HAS_CLAUSE]->(cl:Clause)
            WITH article, matched_node, score, doc,
                 article.article + coalesce(" (" + article.section + ")", "") AS title,
                 cl
            ORDER BY toInteger(cl.clause) ASC
            WITH article, matched_node, score, title, doc, collect(cl) AS all_clauses
            
            // Đưa Khoản khớp nhất lên đầu tiên để tránh bị truncate mất thông tin quan trọng
            WITH article, matched_node, score, title, doc,
                 [c IN all_clauses WHERE c = matched_node] + [c IN all_clauses WHERE c <> matched_node] AS clauses
                 
            WITH article.article_id AS article_id, 
                 title, clauses, article, doc,
                 max(score) AS max_score,
                 head([c IN clauses WHERE c = matched_node]) AS matched_node
                 
            WITH article_id, title, clauses, article, max_score AS score, matched_node, doc,
                 CASE WHEN size(clauses) > 0 
                      THEN reduce(s = title + ":\n", c IN clauses | 
                           s + "- Khoản " + coalesce(c.clause, "") + (CASE WHEN c = matched_node THEN " [KẾT QUẢ KHỚP NHẤT]" ELSE "" END) + ": " + coalesce(c.content, "") + "\n")
                      ELSE title + ":\n" + coalesce(article.content, "") 
                 END AS full_context
                 
            RETURN full_context AS content,
                   coalesce(matched_node.embed_content, article.embed_content) AS embed_content,
                   article.article_id AS article_id,
                   matched_node.clause AS clause,
                   coalesce(matched_node.law_name, article.law_name, doc.law_name) AS law_name,
                   coalesce(matched_node.law_id, article.law_id, doc.law_id) AS law_id,
                   score
            ORDER BY score DESC
            """

            with self.driver.session() as session:
                records = list(session.run(cypher, {
                    "embedding": embedding,
                    "limit": limit
                }))

            docs = []
            for r in records:
                doc = LegalDocument(
                    content=r["content"] or "",
                    source=DocumentSource.GRAPH_STORE,
                    metadata={
                        "search_type": "vector",
                        "article_id": r["article_id"],
                        "clause": r["clause"],
                        "law_id": r["law_id"],
                        "score": r["score"],
                        "embed_content": r["embed_content"]
                    },
                    article_id=r["article_id"],
                    law_name=r["law_name"],
                    score=float(r["score"])
                )
                docs.append(doc)

            return docs
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []

    def _phrase_search(self, keywords: str, limit: int = 5) -> List[LegalDocument]:
        """Tìm kiếm bằng phrase matching."""
        try:
            words = keywords.split()
            phrases = []
            for i in range(len(words) - 2):
                phrases.append(f'"{words[i]} {words[i+1]} {words[i+2]}"')
            for i in range(len(words) - 1):
                phrase = f'"{words[i]} {words[i+1]}"'
                if phrase not in phrases:
                    phrases.append(phrase)

            if not phrases: return []
            lucene_query = " OR ".join(phrases)
            
            cypher = """
            CALL db.index.fulltext.queryNodes('clause_fulltext', $query, {limit: 20})
            YIELD node AS matched_node, score
            
            OPTIONAL MATCH (matched_node)<-[:HAS_CLAUSE]-(parent:Article)
            WITH matched_node, score, coalesce(parent, matched_node) AS article
            
            OPTIONAL MATCH (article)<-[:HAS_ARTICLE]-(:Chapter)<-[:HAS_CHAPTER]-(doc:Document)
            
            OPTIONAL MATCH (article)-[:HAS_CLAUSE]->(cl:Clause)
            WITH article, matched_node, score, doc,
                 article.article + coalesce(" (" + article.section + ")", "") AS title,
                 cl
            ORDER BY toInteger(cl.clause) ASC
            WITH article, matched_node, score, title, doc, collect(cl) AS all_clauses
            
            // Đưa Khoản khớp nhất lên đầu tiên để tránh bị truncate mất thông tin quan trọng
            WITH article, matched_node, score, title, doc,
                 [c IN all_clauses WHERE c = matched_node] + [c IN all_clauses WHERE c <> matched_node] AS clauses
                 
            WITH article.article_id AS article_id, 
                 title, clauses, article, doc,
                 max(score) AS max_score,
                 head([c IN clauses WHERE c = matched_node]) AS matched_node
                 
            WITH article_id, title, clauses, article, max_score AS score, matched_node, doc,
                 CASE WHEN size(clauses) > 0 
                      THEN reduce(s = title + ":\n", c IN clauses | 
                           s + "- Khoản " + coalesce(c.clause, "") + (CASE WHEN c = matched_node THEN " [KẾT QUẢ KHỚP NHẤT]" ELSE "" END) + ": " + coalesce(c.content, "") + "\n")
                      ELSE title + ":\n" + coalesce(article.content, "") 
                 END AS full_context
                 
            RETURN full_context AS content,
                   coalesce(matched_node.embed_content, article.embed_content) AS embed_content,
                   article_id,
                   matched_node.clause AS clause,
                   coalesce(matched_node.law_name, article.law_name, doc.law_name) AS law_name,
                   coalesce(matched_node.law_id, article.law_id, doc.law_id) AS law_id,
                   score
            ORDER BY score DESC
            LIMIT $limit
            """
            
            with self.driver.session() as session:
                records = list(session.run(cypher, {"query": lucene_query, "limit": limit}))

            docs = []
            for r in records:
                doc = LegalDocument(
                    content=r["content"] or "",
                    source=DocumentSource.GRAPH_STORE,
                    metadata={
                        "search_type": "phrase",
                        "article_id": r["article_id"],
                        "clause": r["clause"],
                        "law_id": r["law_id"],
                        "score": r["score"],
                        "embed_content": r["embed_content"]
                    },
                    article_id=r["article_id"],
                    law_name=r["law_name"],
                    score=min(1.0, float(r["score"]) / 3.0) if r["score"] else 0.5
                )
                docs.append(doc)
            return docs
        except Exception as e:
            logger.warning(f"Phrase search failed: {e}")
            return []

    def _fulltext_search(self, query: str, limit: int = 5) -> List[LegalDocument]:
        """Keyword search dùng fulltext index."""
        try:
            safe_query = query.replace('"', '\\"').replace("'", "\\'")
            cypher = """
            CALL db.index.fulltext.queryNodes('clause_fulltext', $query, {limit: 20})
            YIELD node AS matched_node, score
            
            OPTIONAL MATCH (matched_node)<-[:HAS_CLAUSE]-(parent:Article)
            WITH matched_node, score, coalesce(parent, matched_node) AS article
            
            OPTIONAL MATCH (article)<-[:HAS_ARTICLE]-(:Chapter)<-[:HAS_CHAPTER]-(doc:Document)
            
            OPTIONAL MATCH (article)-[:HAS_CLAUSE]->(cl:Clause)
            WITH article, matched_node, score, doc,
                 article.article + coalesce(" (" + article.section + ")", "") AS title,
                 cl
            ORDER BY toInteger(cl.clause) ASC
            WITH article, matched_node, score, title, doc, collect(cl) AS all_clauses
            
            // Đưa Khoản khớp nhất lên đầu tiên để tránh bị truncate mất thông tin quan trọng
            WITH article, matched_node, score, title, doc,
                 [c IN all_clauses WHERE c = matched_node] + [c IN all_clauses WHERE c <> matched_node] AS clauses
                 
            WITH article.article_id AS article_id, 
                 title, clauses, article, doc,
                 max(score) AS max_score,
                 head([c IN clauses WHERE c = matched_node]) AS matched_node
                 
            WITH article_id, title, clauses, article, max_score AS score, matched_node, doc,
                 CASE WHEN size(clauses) > 0 
                      THEN reduce(s = title + ":\n", c IN clauses | 
                           s + "- Khoản " + coalesce(c.clause, "") + (CASE WHEN c = matched_node THEN " [KẾT QUẢ KHỚP NHẤT]" ELSE "" END) + ": " + coalesce(c.content, "") + "\n")
                      ELSE title + ":\n" + coalesce(article.content, "") 
                 END AS full_context
                 
            RETURN full_context AS content,
                   coalesce(matched_node.embed_content, article.embed_content) AS embed_content,
                   article_id,
                   matched_node.clause AS clause,
                   coalesce(matched_node.law_name, article.law_name, doc.law_name) AS law_name,
                   coalesce(matched_node.law_id, article.law_id, doc.law_id) AS law_id,
                   score
            ORDER BY score DESC
            LIMIT $limit
            """

            with self.driver.session() as session:
                records = list(session.run(cypher, {"query": safe_query, "limit": limit}))

            docs = []
            for r in records:
                doc = LegalDocument(
                    content=r["content"] or "",
                    source=DocumentSource.GRAPH_STORE,
                    metadata={
                        "search_type": "fulltext",
                        "article_id": r["article_id"],
                        "clause": r["clause"],
                        "law_id": r["law_id"],
                        "score": r["score"],
                        "embed_content": r["embed_content"]
                    },
                    article_id=r["article_id"],
                    law_name=r["law_name"],
                    score=min(1.0, float(r["score"]) / 3.0) if r["score"] else 0.5
                )
                docs.append(doc)
            return docs
        except Exception as e:
            logger.warning(f"Fulltext search failed: {e}")
            return []

    # ==================== INTERFACE IMPLEMENTATIONS ====================

    def get_violation_details(self, violation_code: str) -> Optional[Violation]:
        """Lấy Clause theo article_id (violation_code)."""
        try:
            cypher = """
            MATCH (cl:Clause {article_id: $code})
            RETURN cl.content AS content, cl.law_name AS law_name
            LIMIT 1
            """
            with self.driver.session() as session:
                record = session.run(cypher, {"code": violation_code}).single()
            if record:
                return Violation(
                    code=violation_code,
                    name=record["content"][:100],
                    description=record["content"],
                    law_name=record["law_name"]
                )
            return None
        except Exception as e:
            logger.error(f"get_violation_details failed: {e}")
            return None

    def query_related_violations(
        self,
        violation_code: str,
        relationship_type: str = "SIMILAR_TO",
        max_depth: int = 2
    ) -> List[Violation]:
        """Tìm các điều khoản cùng Article."""
        try:
            cypher = """
            MATCH (cl1:Clause {article_id: $code})<-[:HAS_CLAUSE]-(a:Article)-[:HAS_CLAUSE]->(cl2:Clause)
            WHERE cl2.article_id <> $code
            RETURN cl2.content AS content, cl2.article_id AS article_id,
                   cl2.law_name AS law_name, cl2.clause AS clause
            LIMIT 5
            """
            with self.driver.session() as session:
                records = list(session.run(cypher, {"code": violation_code}))

            return [
                Violation(
                    code=f"{r['article_id']}.{r['clause']}",
                    name=r["content"][:100],
                    description=r["content"],
                    law_name=r["law_name"]
                )
                for r in records
            ]
        except Exception as e:
            logger.warning(f"query_related_violations failed: {e}")
            return []

    def run_cypher_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute raw Cypher query."""
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            raise CypherQueryError(f"Cypher failed: {str(e)}", cypher=query) from e

    def get_law_structure(self, law_name: str) -> Dict[str, Any]:
        """Lấy cấu trúc phân cấp của 1 nghị định."""
        try:
            cypher = """
            MATCH (l:Law)-[:HAS_CHAPTER]->(c)-[:HAS_ARTICLE]->(a)-[:HAS_CLAUSE]->(cl)
            WHERE l.law_name CONTAINS $name
            RETURN l.law_id AS law_id, l.law_name AS law_name,
                   count(DISTINCT c) AS chapters,
                   count(DISTINCT a) AS articles,
                   count(DISTINCT cl) AS clauses
            """
            with self.driver.session(database=self.database) as session:
                record = session.run(cypher, {"name": law_name}).single()
            return record.data() if record else {}
        except Exception as e:
            logger.error(f"get_law_structure failed: {e}")
            return {}

    def find_shortest_path(
        self,
        start_entity: str,
        end_entity: str,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """Tìm đường ngắn nhất giữa 2 điều khoản."""
        try:
            cypher = """
            MATCH p = shortestPath(
                (a:Clause {article_id: $start})-[*..{max_depth}]-(b:Clause {article_id: $end})
            )
            RETURN [n IN nodes(p) | n.article_id] AS path
            """
            return self.run_cypher_query(cypher, {
                "start": start_entity,
                "end": end_entity,
                "max_depth": max_depth
            })
        except Exception as e:
            logger.warning(f"find_shortest_path failed: {e}")
            return []

    def add_violation(self, violation: Violation, vehicle_types: List[str], article_id: str) -> None:
        """Không dùng — data được ingest qua script riêng."""
        logger.warning("add_violation not implemented — use ingest_to_neo4j.py instead")

    def update_penalty(self, violation_code: str, penalty_min: int, penalty_max: int) -> None:
        """Không dùng."""
        logger.warning("update_penalty not implemented")

    def search_by_keywords(self, keywords: List[str], match_all: bool = False) -> List[LegalDocument]:
        """Tìm kiếm theo từ khóa."""
        query = " AND ".join(keywords) if match_all else " OR ".join(keywords)
        return self._fulltext_search(query, limit=10)

    def get_statistics(self) -> Dict[str, Any]:
        """Thống kê số nodes trong graph."""
        try:
            cypher = """
            MATCH (l:Law) WITH count(l) AS laws
            MATCH (c:Chapter) WITH laws, count(c) AS chapters
            MATCH (a:Article) WITH laws, chapters, count(a) AS articles
            MATCH (cl:Clause) WITH laws, chapters, articles, count(cl) AS clauses
            RETURN laws, chapters, articles, clauses
            """
            with self.driver.session(database=self.database) as session:
                record = session.run(cypher).single()
            return record.data() if record else {}
        except Exception as e:
            logger.error(f"get_statistics failed: {e}")
            return {}

    def health_check(self) -> bool:
        """Kiểm tra kết nối Neo4j."""
        try:
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1").single()
            return True
        except Exception:
            return False

    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @classmethod
    def from_settings(cls) -> "Neo4jRepo":
        return cls(
            uri=settings.NEO4J_URI,
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD
        )
