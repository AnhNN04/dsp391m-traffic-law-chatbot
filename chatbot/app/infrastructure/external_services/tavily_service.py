"""
Tavily Search Service Implementation

Web search service using Tavily API for fallback when information
is not found in the local knowledge base.

Author: AnhNN217-FHN
"""

from typing import List, Optional
from tavily import TavilyClient

from app.domain.entities import LegalDocument, DocumentSource
from app.domain.exceptions import WebSearchError
from app.infrastructure.config import get_logger, settings

logger = get_logger(__name__)


class TavilyService:
    """
    Tavily API wrapper for web search.
    
    Tavily is optimized for LLM applications with clean, structured results.
    Used as a fallback when local knowledge base doesn't have the answer.
    
    Attributes:
        client: Tavily client instance
        api_key: Tavily API key
        default_domains: List of trusted legal websites
    
    Example:
        >>> service = TavilyService.from_settings()
        >>> docs = service.search(
        ...     "nghị định 100 vượt đèn đỏ",
        ...     max_results=3
        ... )
    """
    
    def __init__(
        self,
        api_key: str,
        default_domains: Optional[List[str]] = None
    ):
        """
        Initialize Tavily service.
        
        Args:
            api_key: Tavily API key
            default_domains: Default list of domains to search
        """
        self.api_key = api_key
        self.default_domains = default_domains or [
            "thuvienphapluat.vn",
            "luatvietnam.vn",
            "baochinhphu.vn",
            "chinhphu.vn"
        ]
        
        try:
            self.client = TavilyClient(api_key=api_key)
            
            logger.info(
                "Tavily service initialized",
                default_domains=self.default_domains
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize Tavily service",
                error=str(e)
            )
            raise WebSearchError(
                "Failed to initialize Tavily service",
                provider="Tavily"
            ) from e
    
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
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            include_domains: Domains to restrict search to (uses default if None)
            exclude_domains: Domains to exclude from search
            search_depth: "basic" for quick search, "advanced" for deep search
        
        Returns:
            List of LegalDocument entities from web search results
        
        Raises:
            WebSearchError: If search operation fails
        
        Example:
            >>> docs = service.search(
            ...     "nghị định 100 vượt đèn đỏ",
            ...     max_results=3,
            ...     include_domains=["thuvienphapluat.vn"]
            ... )
        """
        try:
            logger.debug(
                "Performing web search with Tavily",
                query=query,
                max_results=max_results,
                search_depth=search_depth
            )
            
            # Use default domains if none specified
            domains = include_domains or self.default_domains
            
            # Perform search
            response = self.client.search(
                query=query,
                max_results=max_results,
                include_domains=domains,
                exclude_domains=exclude_domains or [],
                search_depth=search_depth,
                include_raw_content=False  # We only need clean text
            )
            
            # Convert results to LegalDocument entities
            legal_docs = []
            for result in response.get("results", []):
                legal_doc = self._tavily_result_to_legal_document(result)
                legal_docs.append(legal_doc)
            
            logger.debug(
                "Web search completed",
                results_found=len(legal_docs),
                query=query
            )
            
            return legal_docs
            
        except Exception as e:
            logger.error(
                "Web search failed",
                error=str(e),
                query=query
            )
            raise WebSearchError(
                f"Web search failed: {str(e)}",
                provider="Tavily",
                query=query
            ) from e
    
    def search_with_metadata(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[dict]:
        """
        Search with full metadata (URLs, snippets, timestamps, etc.).
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            **kwargs: Additional Tavily search parameters
        
        Returns:
            List of dictionaries with complete search result metadata
        """
        try:
            logger.debug("Performing web search with full metadata", query=query)
            
            response = self.client.search(
                query=query,
                max_results=max_results,
                **kwargs
            )
            
            return response.get("results", [])
            
        except Exception as e:
            logger.error("Web search with metadata failed", error=str(e))
            raise WebSearchError(
                f"Web search failed: {str(e)}",
                provider="Tavily",
                query=query
            ) from e
    
    def get_page_content(self, url: str) -> str:
        """
        Fetch and extract main content from a specific URL.
        
        Note: Tavily's extract endpoint may have different pricing/limits.
        
        Args:
            url: URL of the page to fetch
        
        Returns:
            Extracted text content
        
        Raises:
            WebSearchError: If page cannot be fetched
        """
        try:
            logger.debug("Fetching page content", url=url)
            
            # Use Tavily's extract feature
            response = self.client.extract(urls=[url])
            
            if response and len(response) > 0:
                return response[0].get("content", "")
            
            return ""
            
        except Exception as e:
            logger.error("Failed to fetch page content", error=str(e), url=url)
            raise WebSearchError(
                f"Failed to fetch page content: {str(e)}",
                provider="Tavily"
            ) from e
    
    def _tavily_result_to_legal_document(self, result: dict) -> LegalDocument:
        """
        Convert Tavily search result to LegalDocument entity.
        
        Args:
            result: Tavily search result dictionary
        
        Returns:
            LegalDocument entity
        """
        # Extract content and metadata
        content = result.get("content", "")
        title = result.get("title", "")
        url = result.get("url", "")
        score = result.get("score", 0.0)
        
        # Combine title and content
        full_content = f"{title}\n\n{content}" if title else content
        
        return LegalDocument(
            content=full_content,
            source=DocumentSource.WEB_SEARCH,
            metadata={
                "url": url,
                "title": title,
                "published_date": result.get("published_date"),
                "search_score": score
            },
            score=float(score)
        )
    
    def health_check(self) -> bool:
        """
        Check if Tavily service is accessible.
        
        Returns:
            True if service is operational, False otherwise
        """
        try:
            # Perform a minimal test search
            response = self.client.search(
                query="test",
                max_results=1
            )
            return "results" in response
        except Exception as e:
            logger.error("Tavily health check failed", error=str(e))
            return False
    
    def get_usage_stats(self) -> dict:
        """
        Get API usage statistics.
        
        Note: Tavily may not provide detailed usage stats via API.
        This is a placeholder for future implementation.
        
        Returns:
            Dictionary with usage information
        """
        try:
            # Tavily doesn't have a usage endpoint, so we return basic info
            return {
                "provider": "Tavily",
                "api_key_configured": bool(self.api_key),
                "default_domains": self.default_domains
            }
        except Exception as e:
            logger.error("Failed to get usage stats", error=str(e))
            return {"error": str(e)}
    
    @classmethod
    def from_settings(cls) -> "TavilyService":
        """
        Create TavilyService from application settings.
        
        Returns:
            Configured TavilyService instance
        
        Example:
            >>> service = TavilyService.from_settings()
        """
        if not settings.TAVILY_API_KEY:
            logger.warning("TAVILY_API_KEY not configured")
        
        return cls(api_key=settings.TAVILY_API_KEY)
