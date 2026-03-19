"""
Domain Layer

The core business logic layer containing entities, state, and exceptions.
This layer is completely framework-agnostic and contains no infrastructure code.

Exports:
    - Entities: LegalDocument, Violation, ViolationType, VehicleType
    - State: AgentState, PartialAgentState, state utilities
    - Exceptions: All custom exceptions
"""

from app.domain.entities import (
    LegalDocument,
    Violation,
    ViolationType,
    VehicleType,
    DocumentSource,
    create_violation
)

from app.domain.state import (
    AgentState,
    PartialAgentState,
    StateUpdate,
    MessageList,
    create_initial_state,
    get_last_user_message,
    get_conversation_history,
    update_metadata,
    has_sufficient_context,
    should_interrupt
)

from app.domain.exceptions import (
    # Base
    TrafficLawAgentError,
    
    # Domain
    DomainError,
    InvalidStateError,
    EntityValidationError,
    
    # Infrastructure
    InfrastructureError,
    DatabaseConnectionError,
    DatabaseQueryError,
    VectorStoreError,
    GraphStoreError,
    CypherQueryError,
    
    # Application
    ApplicationError,
    NodeExecutionError,
    WorkflowError,
    
    # LLM
    LLMError,
    LLMOutputError,
    LLMConnectionError,
    LLMRateLimitError,
    
    # Retrieval
    RetrievalError,
    NoRelevantDocumentsError,
    AmbiguousQueryError,
    
    # External
    ExternalServiceError,
    WebSearchError,
    
    # Configuration
    ConfigurationError,
    
    # Safety
    SafetyError,
    UnsafeInputError,
    
    # Utilities
    get_error_category,
    should_retry
)

__all__ = [
    # Entities
    "LegalDocument",
    "Violation",
    "ViolationType",
    "VehicleType",
    "DocumentSource",
    "create_violation",
    
    # State
    "AgentState",
    "PartialAgentState",
    "StateUpdate",
    "MessageList",
    "create_initial_state",
    "get_last_user_message",
    "get_conversation_history",
    "update_metadata",
    "has_sufficient_context",
    "should_interrupt",
    
    # Exceptions
    "TrafficLawAgentError",
    "DomainError",
    "InvalidStateError",
    "EntityValidationError",
    "InfrastructureError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "VectorStoreError",
    "GraphStoreError",
    "CypherQueryError",
    "ApplicationError",
    "NodeExecutionError",
    "WorkflowError",
    "LLMError",
    "LLMOutputError",
    "LLMConnectionError",
    "LLMRateLimitError",
    "RetrievalError",
    "NoRelevantDocumentsError",
    "AmbiguousQueryError",
    "ExternalServiceError",
    "WebSearchError",
    "ConfigurationError",
    "SafetyError",
    "UnsafeInputError",
    "get_error_category",
    "should_retry"
]
