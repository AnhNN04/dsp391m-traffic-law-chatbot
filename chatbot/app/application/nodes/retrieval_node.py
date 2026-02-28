"""
Retrieval Node - NODE 3: Hybrid Search Engine.

Tìm kiếm dữ liệu từ nhiều nguồn (Vector Store + Graph Store) và gộp kết quả.
"""

from typing import Dict, Any, List
import hashlib

from app.domain.state import AgentState
from app.domain.entities import LegalDocument
from app.domain.interfaces.i_vector_store import IVectorStore
from app.domain.interfaces.i_graph_store import IGraphStore
from app.application.nodes.base_node import BaseNode
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)
    
class RetrievalNode(BaseNode):
    """
    Node tìm kiếm Hybrid từ Vector Store và Graph Store.
    
    Chiến lược:
    1. Vector Search: Tìm kiếm ngữ nghĩa từ ChromaDB (văn bản luật)
    2. Graph Search: Truy vấn chính xác từ Neo4j (quan hệ vi phạm-mức phạt)
    3. Fusion: Gộp và khử trùng kết quả, ưu tiên Graph
    
    Ví dụ flow:
        Query: "Xe máy vượt đèn đỏ phạt bao nhiêu?"
        -> Vector: 5 docs về "vượt đèn đỏ", "phạt nguội"...
        -> Graph: 1 doc chính xác "Xe máy - Vượt đèn đỏ - Phạt 800k-1tr"
        -> Combined: Graph doc + 4 vector docs (loại trùng)
    """
    
    def __init__(
        self, 
        vector_store: IVectorStore,
        graph_store: IGraphStore
    ):
        """
        Initialize Retrieval Node.
        
        Args:
            vector_store: Vector database interface (ChromaDB)
            graph_store: Graph database interface (Neo4j)
        """
        super().__init__(node_name="Retrieval")
        self.vector_store = vector_store
        self.graph_store = graph_store
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Thực hiện hybrid search.
        
        Args:
            state: AgentState chứa rewritten_query
            
        Returns:
            Dict với documents và data_source
        """
        self._log_entry(state)
        
        try:
            # Validate state
            self._validate_state(state, required_keys=["rewritten_query"])
            
            query = state["rewritten_query"]
            
            if not query or len(query.strip()) < 2:
                logger.warning(f"[{self.node_name}] Empty query, returning empty results")
                return {
                    "documents": [],
                    "data_source": "none"
                }
            
            # Bước 1: Vector Search
            vector_docs = self._search_vector(query)
            
            # Bước 2: Graph Search
            graph_docs = self._search_graph(query)
            
            # Bước 3: Merge và deduplicate
            combined_docs = self._merge_and_deduplicate(vector_docs, graph_docs)
            
            logger.info(
                f"[{self.node_name}] Retrieved: "
                f"{len(vector_docs)} from vector, "
                f"{len(graph_docs)} from graph, "
                f"{len(combined_docs)} total after merge"
            )
            
            result = {
                "documents": combined_docs,
                "data_source": "database"
            }
            
            self._log_exit(result)
            return result
            
        except Exception as e:
            self._log_error(e)
            # Fallback: Trả về empty nếu retrieval fail
            logger.warning(f"[{self.node_name}] Retrieval failed, returning empty")
            return {
                "documents": [],
                "data_source": "error"
            }
    
    def _search_vector(self, query: str, k: int = 5) -> List[LegalDocument]:
        """
        Tìm kiếm từ Vector Store.
        
        Args:
            query: Query string
            k: Số lượng kết quả tối đa
            
        Returns:
            List các LegalDocument
        """
        try:
            logger.debug(f"[{self.node_name}] Vector search: '{query}' (k={k})")
            docs = self.vector_store.search_similarity(query, k=k)
            logger.debug(f"[{self.node_name}] Vector found {len(docs)} docs")
            return docs
            
        except Exception as e:
            logger.error(f"[{self.node_name}] Vector search failed: {e}")
            return []
    
    def _search_graph(self, query: str) -> List[LegalDocument]:
        """
        Tìm kiếm từ Graph Store.
        
        Args:
            query: Query string
            
        Returns:
            List các LegalDocument
        """
        try:
            logger.debug(f"[{self.node_name}] Graph search: '{query}'")
            
            # Graph search có thể fail (Neo4j down, query error...)
            # Nên bọc trong try-except riêng
            docs = self.graph_store.get_penalty_info(query)
            logger.debug(f"[{self.node_name}] Graph found {len(docs)} docs")
            return docs
            
        except Exception as e:
            # Log warning nhưng không crash - fallback về Vector only
            logger.warning(
                f"[{self.node_name}] Graph search failed (fallback to vector only): {e}"
            )
            return []
    
    def _merge_and_deduplicate(
        self, 
        vector_docs: List[LegalDocument],
        graph_docs: List[LegalDocument],
        max_total: int = 10
    ) -> List[LegalDocument]:
        """
        Gộp và khử trùng kết quả từ 2 nguồn.
        
        Chiến lược:
        1. Graph docs lên đầu (độ chính xác cao)
        2. Loại bỏ vector docs trùng với graph docs
        3. Giới hạn tổng số <= max_total
        
        Args:
            vector_docs: Docs từ vector search
            graph_docs: Docs từ graph search
            max_total: Số doc tối đa sau merge
            
        Returns:
            List đã merge và deduplicate
        """
        # Nếu cả 2 đều rỗng
        if not vector_docs and not graph_docs:
            return []
        
        # Track các doc đã thấy bằng hash
        seen_hashes = set()
        result = []
        
        # Bước 1: Add graph docs trước (priority)
        for doc in graph_docs:
            doc_hash = self._hash_document(doc)
            if doc_hash not in seen_hashes:
                result.append(doc)
                seen_hashes.add(doc_hash)
        
        # Bước 2: Add vector docs (loại trùng)
        for doc in vector_docs:
            doc_hash = self._hash_document(doc)
            if doc_hash not in seen_hashes:
                result.append(doc)
                seen_hashes.add(doc_hash)
            
            # Giới hạn số lượng
            if len(result) >= max_total:
                break
        
        logger.debug(
            f"[{self.node_name}] Merged: {len(graph_docs)} graph + "
            f"{len(vector_docs)} vector -> {len(result)} unique docs"
        )
        
        return result
    
    def _hash_document(self, doc: LegalDocument) -> str:
        """
        Tạo hash của document để detect trùng lặp.
        
        Args:
            doc: LegalDocument
            
        Returns:
            Hash string
        """
        # Hash dựa trên content (loại bỏ whitespace để tránh false negative)
        content_normalized = doc.content.strip().lower()
        return hashlib.md5(content_normalized.encode()).hexdigest()
    
    def _extract_entity_hints(self, query: str) -> Dict[str, Any]:
        """
        Trích xuất gợi ý entity từ query để optimize graph search.
        
        Ví dụ: "Xe máy vượt đèn đỏ" -> {vehicle: "motorcycle", violation: "red_light"}
        
        Args:
            query: Query string
            
        Returns:
            Dict chứa entity hints
        """
        # Simple keyword matching (có thể nâng cấp thành NER sau)
        hints = {}
        
        query_lower = query.lower()
        
        # Vehicle type
        if any(kw in query_lower for kw in ["xe máy", "mô tô", "môtô"]):
            hints["vehicle_type"] = "motorcycle"
        elif any(kw in query_lower for kw in ["ô tô", "xe hơi", "xe con"]):
            hints["vehicle_type"] = "car"
        elif any(kw in query_lower for kw in ["xe tải", "xe tải nặng"]):
            hints["vehicle_type"] = "truck"
        
        # Violation type
        if "đèn đỏ" in query_lower:
            hints["violation"] = "red_light"
        elif any(kw in query_lower for kw in ["nồng độ cồn", "rượu bia", "say xỉn"]):
            hints["violation"] = "alcohol"
        elif "tốc độ" in query_lower:
            hints["violation"] = "speeding"
        
        return hints
