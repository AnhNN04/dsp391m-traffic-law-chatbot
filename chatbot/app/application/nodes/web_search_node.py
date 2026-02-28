"""
Web Search Node - NODE 6: Internet Fallback Search.

Tìm kiếm thông tin từ Internet khi database nội bộ không có kết quả.
"""

from typing import Dict, Any, List

from app.domain.state import AgentState
from app.domain.entities import LegalDocument
from app.application.interfaces.i_search_tool import ISearchTool
from app.application.nodes.base_node import BaseNode
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)

class WebSearchNode(BaseNode):
    """
    Node tìm kiếm từ Internet sử dụng Tavily API.
    
    Use cases:
    1. Database không có thông tin (mới ban hành, chưa index)
    2. Câu hỏi về thủ tục thay đổi (cần thông tin mới nhất)
    3. Tin tức, cập nhật chính sách
    
    Chiến lược:
    - Chỉ search các domain đáng tin cậy (thuvienphapluat.vn, luatvietnam.vn...)
    - Giới hạn số kết quả để tránh quá tải context
    - Tag rõ nguồn từ web để user biết
    
    Ví dụ:
        Query: "Quy định mới về phạt nguội năm 2024"
        -> Web search vì có thể có thay đổi mới
        -> Lấy top 3 kết quả từ các site luật uy tín
    """
    
    # Các domain đáng tin cậy
    TRUSTED_DOMAINS = [
        "thuvienphapluat.vn",
        "luatvietnam.vn",
        "baochinhphu.vn",
        "csgt.vn",
        "cand.com.vn",
        "nhandan.vn"
    ]
    
    def __init__(self, search_tool: ISearchTool):
        """
        Initialize Web Search Node.
        
        Args:
            search_tool: Search tool interface (Tavily wrapper)
        """
        super().__init__(node_name="WebSearch")
        self.search_tool = search_tool
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Thực hiện web search.
        
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
                logger.warning(f"[{self.node_name}] Empty query, skipping web search")
                return {
                    "documents": [],
                    "data_source": "none"
                }
            
            # Enhance query for legal search
            enhanced_query = self._enhance_query_for_legal_search(query)
            
            logger.info(f"[{self.node_name}] Searching web for: '{enhanced_query}'")
            
            # Thực hiện search
            web_results = self._search_web(enhanced_query)
            
            # Convert sang LegalDocument format
            documents = self._convert_to_documents(web_results)
            
            logger.info(
                f"[{self.node_name}] Found {len(web_results)} web results, "
                f"converted to {len(documents)} documents"
            )
            
            result = {
                "documents": documents,
                "data_source": "internet"
            }
            
            self._log_exit(result)
            return result
            
        except Exception as e:
            self._log_error(e)
            # Fallback: Trả về empty nếu web search fail
            logger.warning(f"[{self.node_name}] Web search failed, returning empty")
            return {
                "documents": [],
                "data_source": "web_error"
            }
    
    def _enhance_query_for_legal_search(self, query: str) -> str:
        """
        Tối ưu query cho search luật pháp.
        
        Thêm từ khóa context để tăng độ chính xác.
        
        Args:
            query: Query gốc
            
        Returns:
            Enhanced query
        """
        # Thêm context "luật giao thông việt nam" nếu chưa có
        query_lower = query.lower()
        
        # Nếu query đã có từ khóa luật -> giữ nguyên
        if any(kw in query_lower for kw in ["luật", "quy định", "nghị định", "thông tư"]):
            return query
        
        # Ngược lại, thêm context
        return f"{query} luật giao thông việt nam"
    
    def _search_web(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Gọi search tool để tìm kiếm web.
        
        Args:
            query: Search query
            max_results: Số kết quả tối đa
            
        Returns:
            List các search result dicts
        """
        try:
            results = self.search_tool.search(
                query=query,
                max_results=max_results,
                include_domains=self.TRUSTED_DOMAINS
            )
            
            logger.debug(f"[{self.node_name}] Raw search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"[{self.node_name}] Search API call failed: {e}")
            return []
    
    def _convert_to_documents(
        self, 
        web_results: List[Dict[str, Any]]
    ) -> List[LegalDocument]:
        """
        Convert web search results thành LegalDocument entities.
        
        Args:
            web_results: List kết quả từ search tool
            
        Returns:
            List LegalDocument
        """
        documents = []
        
        for result in web_results:
            try:
                # Extract fields (format có thể khác nhau tùy search tool)
                title = result.get("title", "Untitled")
                content = result.get("content", result.get("snippet", ""))
                url = result.get("url", "")
                
                # Tạo document
                doc = LegalDocument(
                    content=f"{title}\n\n{content}",
                    source=url,
                    metadata={
                        "source_type": "web",
                        "title": title,
                        "url": url,
                        "search_engine": "tavily"
                    }
                )
                
                documents.append(doc)
                
            except Exception as e:
                logger.warning(f"[{self.node_name}] Failed to convert result: {e}")
                continue
        
        return documents
    
    def _filter_by_domain(
        self, 
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Lọc kết quả chỉ giữ các domain đáng tin cậy (backup filter).
        
        Args:
            results: List search results
            
        Returns:
            Filtered list
        """
        filtered = []
        
        for result in results:
            url = result.get("url", "").lower()
            
            # Check xem URL có thuộc trusted domain không
            if any(domain in url for domain in self.TRUSTED_DOMAINS):
                filtered.append(result)
            else:
                logger.debug(
                    f"[{self.node_name}] Filtered out untrusted domain: {url}"
                )
        
        return filtered
    
    def _prioritize_official_sources(
        self, 
        documents: List[LegalDocument]
    ) -> List[LegalDocument]:
        """
        Sắp xếp documents ưu tiên các nguồn chính thống lên đầu.
        
        Args:
            documents: List documents
            
        Returns:
            Sorted list
        """
        # Define priority levels
        priority_map = {
            "baochinhphu.vn": 1,  # Cao nhất
            "thuvienphapluat.vn": 2,
            "luatvietnam.vn": 2,
            "csgt.vn": 3,
        }
        
        def get_priority(doc: LegalDocument) -> int:
            """Helper to get priority score."""
            source = doc.source.lower()
            for domain, priority in priority_map.items():
                if domain in source:
                    return priority
            return 99  # Lowest priority
        
        # Sort by priority
        return sorted(documents, key=get_priority)
