"""
Retrieval Node - NODE 3: Hybrid Search Engine.

Tìm kiếm dữ liệu từ nhiều nguồn (Vector Store + Graph Store) và gộp kết quả.
"""

from typing import Dict, Any, List
import hashlib

from app.domain.state import AgentState
from app.domain.entities import LegalDocument
from app.domain.interfaces.i_graph_store import IGraphStore
from app.domain.interfaces.i_llm_service import ILLMService
from app.application.nodes.base_node import BaseNode
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)

class RetrievalNode(BaseNode):
    """
    Node tìm kiếm Hybrid từ Vector Store và Graph Store.
    
    Chiến lược:
    1. Query Expansion: Dùng LLM dịch từ ngữ đời sống -> thuật ngữ pháp luật.
    2. Vector Search: Tìm kiếm ngữ nghĩa từ ChromaDB (văn bản luật)
    3. Graph Search: Truy vấn chính xác từ Neo4j (quan hệ vi phạm-mức phạt)
    4. Fusion: Gộp và khử trùng kết quả, ưu tiên Graph
    """
    
    EXPAND_PROMPT = """Bạn là chuyên gia về luật giao thông đường bộ Việt Nam. 
Nhiệm vụ của bạn là chuyển đổi câu hỏi bằng ngôn ngữ thường ngày của người dùng thành các thuật ngữ pháp lý chính xác nhất để tối ưu cho việc tìm kiếm trong cơ sở dữ liệu luật.

Quy tắc chuyển đổi:
1. Từ lóng/đời sống -> Thuật ngữ trong văn bản luật.
   Ví dụ:
   - "kẹp 3", "chở 3" -> "chở theo từ 02 người trở lên"
   - "vượt đèn đỏ", "vượt đèn vàng" -> "không chấp hành hiệu lệnh của đèn tín hiệu giao thông"
   - "không xi nhan" -> "chuyển hướng không có tín hiệu báo hướng rẽ"
   - "ngược chiều" -> "đi ngược chiều của đường đi một chiều"
   - "bỏ chạy", "tẩu thoát" -> "gây tai nạn giao thông không dừng lại"
   - "không nhường đường" -> "không nhường đường cho xe xin vượt", "gây cản trở xe ưu tiên"
2. Giữ lại loại phương tiện nếu có (xe máy, ô tô, xe đạp).
3. KHÔNG trả lời câu hỏi. CHỈ trả về câu truy vấn đã được viết lại bằng thuật ngữ pháp lý.

Câu hỏi của người dùng: "{query}"

Câu truy vấn thuật ngữ pháp lý:"""

    def __init__(
        self, 
        graph_store: IGraphStore,
        vector_store: Any,
        smart_llm: ILLMService
    ):
        """
        Initialize Retrieval Node.
        
        Args:
            graph_store: Graph database interface (Neo4j)
            vector_store: Vector database interface (ChromaDB)
            smart_llm: LLM for query expansion
        """
        super().__init__(node_name="Retrieval")
        self.graph_store = graph_store
        self.vector_store = vector_store
        self.llm = smart_llm
    
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
            
            # Bước 1: Dùng LLM dịch query từ ngôn ngữ đời sống sang thuật ngữ pháp lý
            expanded_query = self.llm.generate(
                system_message=self.EXPAND_PROMPT,
                prompt=query
            )
            
            logger.info(f"[{self.node_name}] Original query: '{query}' | Expanded query: '{expanded_query}'")
            
            # Bước 2: Sử dụng Graph Store (Neo4j) để tìm kiếm dựa trên expanded_query
            # Ghép cả 2 câu hỏi lại để tăng tối đa keyword coverage
            combined_search_term = f"{query} {expanded_query}"
            graph_docs = self._search_graph(combined_search_term)
            
            logger.info(
                f"[{self.node_name}] Retrieved: "
                f"{len(graph_docs)} from Neo4j graph"
            )
            
            result = {
                "documents": graph_docs,
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
    
    def _search_graph(self, query: str) -> List[LegalDocument]:
        try:
            combined_docs = []
            
            # --- 1. Vector Search (ChromaDB) ---
            vector_docs = []
            doc_ids = []
            if getattr(self, "vector_store", None):
                logger.debug(f"[{self.node_name}] Vector search: '{query}'")
                vector_docs = self.vector_store.search(query, k=5)
                logger.debug(f"[{self.node_name}] Vector store found {len(vector_docs)} docs")
                
                # Extract IDs for Graph Search
                for doc in vector_docs:
                    doc_id = doc.metadata.get("id") or doc.metadata.get("clause_id")
                    if doc_id and doc_id not in doc_ids:
                        doc_ids.append(doc_id)
                
                combined_docs.extend(vector_docs)
            
            # --- 2. Entity Graph Traversal (Neo4j) ---
            if self.graph_store and doc_ids:
                logger.debug(f"[{self.node_name}] Entity Graph traversal for {len(doc_ids)} IDs")
                entity_docs = self.graph_store.get_entity_subgraph_by_ids(doc_ids)
                logger.debug(f"[{self.node_name}] Entity Graph found {len(entity_docs)} subgraphs")
                combined_docs.extend(entity_docs)
                
            # --- 3. Fallback/Sparse Search (Neo4j) ---
            if self.graph_store:
                logger.debug(f"[{self.node_name}] Fulltext/Phrase search fallback")
                sparse_docs = self.graph_store.get_penalty_info(query)
                combined_docs.extend(sparse_docs)
                
            # --- 4. Khử trùng lặp và Sắp xếp ---
            unique_docs = []
            seen_content = set()
            for doc in combined_docs:
                h = hashlib.md5(doc.content.encode('utf-8')).hexdigest()
                if h not in seen_content:
                    seen_content.add(h)
                    unique_docs.append(doc)
            
            unique_docs.sort(key=lambda x: x.score, reverse=True)
            return unique_docs
            
        except Exception as e:
            logger.warning(
                f"[{self.node_name}] Hybrid search failed: {e}"
            )
            return []
    
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
