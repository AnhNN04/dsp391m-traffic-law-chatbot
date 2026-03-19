"""
Domain Exceptions

Custom exceptions for the Traffic Law Agent system.
These exceptions are organized by layer and concern.

Author: AnhNN217-FHN
"""

from typing import Optional


# ==================== Base Exceptions ====================

class TrafficLawAgentError(Exception):
    """
    Base exception for all Traffic Law Agent errors.
    
    All custom exceptions inherit from this base class,
    making it easy to catch all agent-specific errors.
    """
    
    def __init__(self, message: str, details: Optional[dict] = None):
        """
        Initialize exception with message and optional details.
        
        Args:
            message: Human-readable error message
            details: Additional context about the error
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """String representation of the exception."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ==================== Domain Layer Exceptions ====================

class DomainError(TrafficLawAgentError):
    """Base exception for domain layer errors."""
    pass


class InvalidStateError(DomainError):
    """Raised when AgentState is in an invalid state."""
    pass


class EntityValidationError(DomainError):
    """Raised when entity validation fails."""
    pass


# ==================== Infrastructure Layer Exceptions ====================

class InfrastructureError(TrafficLawAgentError):
    """
    Base exception for infrastructure layer errors.
    
    This includes database connections, API calls, and external services.
    """
    pass


class DatabaseConnectionError(InfrastructureError):
    """Raised when database connection fails."""
    
    def __init__(
        self,
        message: str,
        database_type: str,
        connection_string: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize database connection error.
        
        Args:
            message: Error message
            database_type: Type of database (MongoDB, Neo4j, ChromaDB)
            connection_string: Connection string (credentials will be masked)
        """
        details = {
            "database_type": database_type,
            "connection_string": self._mask_credentials(connection_string)
        }
        details.update(kwargs)
        super().__init__(message, details)
    
    @staticmethod
    def _mask_credentials(conn_str: Optional[str]) -> Optional[str]:
        """Mask password in connection string."""
        if not conn_str:
            return None
        # Simple masking: replace everything between :// and @
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', conn_str)


class DatabaseQueryError(InfrastructureError):
    """Raised when database query execution fails."""
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        database_type: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize query error.
        
        Args:
            message: Error message
            query: The query that failed (optional)
            database_type: Type of database
        """
        details = {
            "query": query,
            "database_type": database_type
        }
        details.update(kwargs)
        super().__init__(message, details)


class VectorStoreError(InfrastructureError):
    """Raised when vector store operations fail."""
    pass


class GraphStoreError(InfrastructureError):
    """Raised when graph database operations fail."""
    pass


class CypherQueryError(GraphStoreError):
    """Raised when Cypher query syntax is invalid or execution fails."""
    
    def __init__(self, message: str, cypher: Optional[str] = None, **kwargs):
        """
        Initialize Cypher query error.
        
        Args:
            message: Error message
            cypher: The Cypher query that failed
        """
        details = {"cypher": cypher}
        details.update(kwargs)
        super().__init__(message, details)


# ==================== Application Layer Exceptions ====================

class ApplicationError(TrafficLawAgentError):
    """Base exception for application layer errors."""
    pass


class NodeExecutionError(ApplicationError):
    """Raised when a graph node fails to execute."""
    
    def __init__(
        self,
        message: str,
        node_name: str,
        state_snapshot: Optional[dict] = None,
        **kwargs
    ):
        """
        Initialize node execution error.
        
        Args:
            message: Error message
            node_name: Name of the node that failed
            state_snapshot: Snapshot of state at failure time
        """
        details = {
            "node_name": node_name,
            "state_snapshot": state_snapshot
        }
        details.update(kwargs)
        super().__init__(message, details)


class WorkflowError(ApplicationError):
    """Raised when graph workflow encounters an error."""
    pass


# ==================== LLM-Related Exceptions ====================

class LLMError(TrafficLawAgentError):
    """Base exception for LLM-related errors."""
    pass


class LLMOutputError(LLMError):
    """
    Raised when LLM output is invalid or cannot be parsed.
    
    This typically happens when expecting JSON but getting text,
    or when output doesn't match expected schema.
    """
    
    def __init__(
        self,
        message: str,
        output: Optional[str] = None,
        expected_format: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize LLM output error.
        
        Args:
            message: Error message
            output: The invalid output from LLM
            expected_format: What format was expected
        """
        details = {
            "output": output[:500] if output else None,  # Truncate long outputs
            "expected_format": expected_format
        }
        details.update(kwargs)
        super().__init__(message, details)


class LLMConnectionError(LLMError):
    """Raised when LLM API connection fails."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        model: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize LLM connection error.
        
        Args:
            message: Error message
            provider: LLM provider (OpenAI, Groq, etc.)
            model: Model name that failed
        """
        details = {
            "provider": provider,
            "model": model
        }
        details.update(kwargs)
        super().__init__(message, details)


class LLMRateLimitError(LLMError):
    """Raised when LLM API rate limit is exceeded."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize rate limit error.
        
        Args:
            message: Error message
            provider: LLM provider
            retry_after: Seconds to wait before retrying
        """
        details = {
            "provider": provider,
            "retry_after": retry_after
        }
        details.update(kwargs)
        super().__init__(message, details)


# ==================== Retrieval Exceptions ====================

class RetrievalError(ApplicationError):
    """Base exception for retrieval-related errors."""
    pass


class NoRelevantDocumentsError(RetrievalError):
    """
    Raised when no relevant documents are found.
    
    This is not always an error - it might trigger web search
    or asking user for clarification.
    """
    
    def __init__(
        self,
        message: str = "No relevant documents found",
        query: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize no documents error.
        
        Args:
            message: Error message
            query: The query that returned no results
        """
        details = {"query": query}
        details.update(kwargs)
        super().__init__(message, details)


class AmbiguousQueryError(RetrievalError):
    """
    Raised when query is too ambiguous to process.
    
    This should trigger the Ask Human node to get clarification.
    """
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        ambiguity_reason: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize ambiguous query error.
        
        Args:
            message: Error message
            query: The ambiguous query
            ambiguity_reason: Why the query is ambiguous
        """
        details = {
            "query": query,
            "ambiguity_reason": ambiguity_reason
        }
        details.update(kwargs)
        super().__init__(message, details)


# ==================== External Service Exceptions ====================

class ExternalServiceError(InfrastructureError):
    """Base exception for external service errors."""
    pass


class WebSearchError(ExternalServiceError):
    """Raised when web search fails."""
    
    def __init__(
        self,
        message: str,
        provider: str = "Tavily",
        query: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize web search error.
        
        Args:
            message: Error message
            provider: Search provider name
            query: The search query
        """
        details = {
            "provider": provider,
            "query": query
        }
        details.update(kwargs)
        super().__init__(message, details)


# ==================== Configuration Exceptions ====================

class ConfigurationError(TrafficLawAgentError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            config_key: The configuration key that's invalid
        """
        details = {"config_key": config_key}
        details.update(kwargs)
        super().__init__(message, details)


# ==================== Safety Exceptions ====================

class SafetyError(ApplicationError):
    """Base exception for safety-related issues."""
    pass


class UnsafeInputError(SafetyError):
    """
    Raised when user input fails safety checks.
    
    This triggers in the Guardrails node when input contains:
    - Prompt injection attempts
    - Toxic/offensive content
    - Malicious queries
    """
    
    def __init__(
        self,
        message: str = "Input failed safety checks",
        reason: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize unsafe input error.
        
        Args:
            message: Error message
            reason: Why the input is unsafe
        """
        details = {"reason": reason}
        details.update(kwargs)
        super().__init__(message, details)


# ==================== Utility Functions ====================

def get_error_category(error: Exception) -> str:
    """
    Get the category of an error for logging/monitoring.
    
    Args:
        error: The exception instance
    
    Returns:
        Category string (infrastructure, application, llm, etc.)
    
    Example:
        >>> try:
        ...     raise DatabaseConnectionError("Connection failed", "MongoDB")
        ... except Exception as e:
        ...     category = get_error_category(e)
        ...     # category = "infrastructure"
    """
    if isinstance(error, InfrastructureError):
        return "infrastructure"
    elif isinstance(error, LLMError):
        return "llm"
    elif isinstance(error, ApplicationError):
        return "application"
    elif isinstance(error, DomainError):
        return "domain"
    elif isinstance(error, ConfigurationError):
        return "configuration"
    else:
        return "unknown"


def should_retry(error: Exception) -> bool:
    """
    Determine if an operation should be retried based on error type.
    
    Args:
        error: The exception that occurred
    
    Returns:
        True if the operation should be retried
    
    Example:
        >>> try:
        ...     call_api()
        ... except Exception as e:
        ...     if should_retry(e):
        ...         time.sleep(1)
        ...         call_api()  # Retry
    """
    # Retry on connection errors but not on validation errors
    retry_types = (
        DatabaseConnectionError,
        LLMConnectionError,
        WebSearchError
    )
    
    # Don't retry rate limits (need longer wait) or safety issues
    no_retry_types = (
        LLMRateLimitError,
        UnsafeInputError,
        EntityValidationError,
        ConfigurationError
    )
    
    if isinstance(error, no_retry_types):
        return False
    
    if isinstance(error, retry_types):
        return True
    
    return False
