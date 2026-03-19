"""
IEmbeddingService Interface

This module defines the IEmbeddingService interface, which specifies the contract for
generating text embeddings. It includes methods for embedding single queries, multiple
documents, and retrieving the embedding dimensions.

Typical implementations include services like Google Embeddings, OpenAI Embeddings, etc.

Author: AnhNN217-FHN
"""

from abc import ABC, abstractmethod
from typing import List, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class IEmbeddingService(ABC):
    """
    Abstract interface for text embedding operations.
    
    Separate from ILLMService because embeddings are often provided
    by different models/providers optimized for semantic similarity.
    
    Example Implementation:
        >>> class GoogleEmbeddingService(IEmbeddingService):
        ...     def __init__(self, api_key: str):
        ...         self.embeddings = GoogleGenerativeAIEmbeddings(
        ...             google_api_key=api_key,
        ...             model="models/embedding-001"
        ...         )
    """
    
    @abstractmethod
    def embed_query(
        self,
        text: str
    ) -> List[float]:
        """
        Generate embedding vector for a single query text.
        
        Args:
            text: Query text to embed
        
        Returns:
            Embedding vector (typically 768 or 1536 dimensions)
        
        Example:
            >>> embedding = service.embed_query("vượt đèn đỏ")
            >>> len(embedding)  # 768
        """
        pass
    
    @abstractmethod
    def embed_documents(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embedding vectors for multiple documents.
        
        More efficient than calling embed_query multiple times
        due to batching.
        
        Args:
            texts: List of document texts to embed
        
        Returns:
            List of embedding vectors
        
        Example:
            >>> texts = ["Điều 5...", "Điều 6...", "Điều 7..."]
            >>> embeddings = service.embed_documents(texts)
            >>> len(embeddings)  # 3
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embedding vectors produced by this service.
        
        Returns:
            Embedding vector dimension
        
        Example:
            >>> dim = service.get_embedding_dimension()
            >>> print(f"Embeddings are {dim}-dimensional")
        """
        pass
