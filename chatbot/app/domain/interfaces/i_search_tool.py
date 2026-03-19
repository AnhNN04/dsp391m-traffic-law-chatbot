"""
Search Tool Interface

Abstract interface for web search operations.
Concrete implementations: Tavily, Serper, Google Search, Bing, etc.

Author: AnhNN217-FHN
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from app.domain.entities import LegalDocument


class ISearchTool(ABC):
    """
    Abstract interface for web search operations.
    
    This interface defines the contract for web search service implementations.
    Used as a fallback when information is not found in the local knowledge base.
    
    Example Implementation:
        >>> class TavilySearchService(ISearchTool):
        ...     def __init__(self, api_key: str):
        ...         self.client = TavilyClient(api_key=api_key)
        ...     
        ...     def search(self, query: str, max_results: int = 5) -> List[LegalDocument]:
        ...         results = self.client.search(query, max_results=max_results)
        ...         return [self._to_legal_document(r) for r in results["results"]]
    """
    
    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        search_depth: str = "basic"
    ) -> List[LegalDocument]:
        """
        Search the web for relevant information.
        
        This method performs web search and converts results into
        LegalDocument entities for consistent handling.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            include_domains: Optional list of domains to restrict search to
                Example: ["thuvienphapluat.vn", "luatvietnam.vn"]
            exclude_domains: Optional list of domains to exclude
            search_depth: "basic" for quick search, "advanced" for deep search
        
        Returns:
            List of LegalDocument entities from web search results
        
        Raises:
            WebSearchError: If search operation fails
        
        Example:
            >>> search = TavilySearchService(api_key="tvly-...")
            >>> docs = search.search(
            ...     "nghị định 100 vượt đèn đỏ",
            ...     max_results=3,
            ...     include_domains=["thuvienphapluat.vn"]
            ... )
            >>> for doc in docs:
            ...     print(f"{doc.source}: {doc.content[:100]}")
        """
        pass
    
    @abstractmethod
    def search_with_metadata(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search with full metadata (URLs, snippets, timestamps, etc.).
        
        Returns raw search results with all available metadata,
        not converted to LegalDocument entities.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            **kwargs: Additional search parameters
        
        Returns:
            List of dictionaries with search result metadata
        
        Example:
            >>> results = search.search_with_metadata("nghị định 100")
            >>> for result in results:
            ...     print(f"URL: {result['url']}")
            ...     print(f"Title: {result['title']}")
            ...     print(f"Snippet: {result['snippet']}")
        """
        pass
    
    @abstractmethod
    def get_page_content(
        self,
        url: str
    ) -> str:
        """
        Fetch and extract main content from a specific URL.
        
        Useful when you want to get the full text of a search result.
        
        Args:
            url: URL of the page to fetch
        
        Returns:
            Extracted text content
        
        Raises:
            WebSearchError: If page cannot be fetched or parsed
        
        Example:
            >>> url = "https://thuvienphapluat.vn/van-ban/Giao-thong/..."
            >>> content = search.get_page_content(url)
            >>> print(content[:500])
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the search service is accessible.
        
        Returns:
            True if service is operational, False otherwise
        
        Example:
            >>> if not search.health_check():
            ...     logger.warning("Search service is down, using only local data")
        """
        pass
    
    @abstractmethod
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get API usage statistics (if available).
        
        Returns:
            Dictionary with usage info like requests used, quota remaining
        
        Example:
            >>> stats = search.get_usage_stats()
            >>> print(f"Searches this month: {stats['requests_used']}")
            >>> print(f"Quota remaining: {stats['quota_remaining']}")
        """
        pass
