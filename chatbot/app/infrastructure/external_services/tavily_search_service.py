"""
Tavily Search Service — implement ISearchTool dùng Tavily API.
"""
from typing import List, Optional, Dict, Any

from app.domain.entities import LegalDocument, DocumentSource
from app.domain.interfaces.i_search_tool import ISearchTool
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)


class TavilySearchService(ISearchTool):
    """
    Web search sử dụng Tavily API.
    Tìm kiếm các trang luật pháp uy tín về giao thông Việt Nam.
    """

    def __init__(self, api_key: str):
        try:
            from tavily import TavilyClient
            self.client = TavilyClient(api_key=api_key)
            logger.info("TavilySearchService initialized")
        except ImportError:
            raise ImportError("Cần cài tavily-python: pip install tavily-python")

    def search(
        self,
        query: str,
        max_results: int = 3,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        search_depth: str = "basic"
    ) -> List[LegalDocument]:
        """Tìm kiếm và trả về LegalDocument list."""
        raw = self.search_with_metadata(
            query=query,
            max_results=max_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            search_depth=search_depth
        )
        return [self._to_document(r) for r in raw]

    def search_with_metadata(
        self,
        query: str,
        max_results: int = 3,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Gọi Tavily API và trả về raw results."""
        try:
            params = {
                "query": query,
                "max_results": max_results,
                "search_depth": kwargs.get("search_depth", "basic"),
            }
            if kwargs.get("include_domains"):
                params["include_domains"] = kwargs["include_domains"]

            response = self.client.search(**params)
            results = response.get("results", [])
            logger.debug(f"Tavily returned {len(results)} results for: {query[:60]}")
            return results
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []

    def get_page_content(self, url: str) -> str:
        """Lấy nội dung từ URL cụ thể."""
        try:
            response = self.client.extract(urls=[url])
            results = response.get("results", [])
            if results:
                return results[0].get("raw_content", "")
            return ""
        except Exception as e:
            logger.warning(f"get_page_content failed for {url}: {e}")
            return ""

    def health_check(self) -> bool:
        """Kiểm tra Tavily có hoạt động không."""
        try:
            result = self.client.search("test", max_results=1)
            return bool(result)
        except Exception:
            return False

    def get_usage_stats(self) -> Dict[str, Any]:
        """Trả về thống kê (Tavily không expose API này nên trả empty)."""
        return {}

    def _to_document(self, result: Dict[str, Any]) -> LegalDocument:
        """Convert Tavily result → LegalDocument."""
        title = result.get("title", "")
        content = result.get("content", result.get("snippet", ""))
        url = result.get("url", "")

        return LegalDocument(
            content=f"{title}\n\n{content}".strip(),
            source=DocumentSource.WEB_SEARCH,
            law_name=title,
            metadata={
                "source_type": "web",
                "url": url,
                "title": title,
                "search_engine": "tavily",
            },
            score=result.get("score", 0.7)
        )
