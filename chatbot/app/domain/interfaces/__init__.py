"""
Domain Interfaces

Abstract interfaces for data access layer.
These define contracts that infrastructure implementations must follow.
"""

from app.domain.interfaces.i_vector_store import IVectorStore
from app.domain.interfaces.i_graph_store import IGraphStore
from app.domain.interfaces.i_llm_service import ILLMService
from app.domain.interfaces.i_embedding_service import IEmbeddingService
from app.domain.interfaces.i_search_tool import ISearchTool

__all__ = [
    "IVectorStore",
    "IGraphStore",
    "ILLMService",
    "IEmbeddingService",
    "ISearchTool"
]
