"""
Vector Store Interface

Abstract interface for vector database operations.
Concrete implementations: ChromaDB, Pinecone, Weaviate, etc.

Author: AnhNN217-FHN
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from app.domain.entities import LegalDocument


class IVectorStore(ABC):
    """
    Abstract interface for vector similarity search operations.
    
    This interface defines the contract for vector database implementations.
    Any vector store (ChromaDB, Pinecone, Qdrant, etc.) must implement
    these methods to be compatible with the application layer.
    
    """
    
    @abstractmethod
    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[LegalDocument]:
        """
        Search for similar documents using semantic similarity.
        
        This method performs vector similarity search to find documents
        that are semantically similar to the query text.
        
        Args:
            query: The search query text
            k: Number of results to return (default: 5)
            filter_metadata: Optional metadata filters to apply
                Example: {"law": "ND 100/2019", "vehicle": "motorcycle"}
        
        Returns:
            List of LegalDocument entities ordered by relevance (highest first)
        
        Raises:
            VectorStoreError: If search operation fails
        
        """
        pass
    
    @abstractmethod
    def add_documents(
        self,
        documents: List[LegalDocument],
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Add new documents to the vector store.
        
        This method embeds and stores documents for future retrieval.
        Used during data seeding or when adding new legal documents.
        
        Args:
            documents: List of LegalDocument entities to add
            ids: Optional list of unique IDs for each document
        
        Raises:
            VectorStoreError: If add operation fails
        
        """
        pass
    
    @abstractmethod
    def delete_documents(
        self,
        ids: List[str]
    ) -> None:
        """
        Delete documents from the vector store.
        
        Args:
            ids: List of document IDs to delete
        
        Raises:
            VectorStoreError: If delete operation fails

        """
        pass
    
    @abstractmethod
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store collection.
        
        Returns:
            Dictionary with stats like document count, embedding dimensions
        
        """
        pass
    
    @abstractmethod
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        score_threshold: float = 0.0
    ) -> List[tuple[LegalDocument, float]]:
        """
        Search with explicit similarity scores.
        
        Similar to search() but returns tuples of (document, score)
        for more granular control over relevance filtering.
        
        Args:
            query: The search query text
            k: Number of results to return
            score_threshold: Minimum similarity score (0.0 to 1.0)
        
        Returns:
            List of (LegalDocument, score) tuples
        
        """
        pass
    
    @abstractmethod
    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 5,
        fetch_k: int = 20,
        lambda_mult: float = 0.5
    ) -> List[LegalDocument]:
        """
        Search using Maximum Marginal Relevance (MMR) for diversity.
        
        MMR balances relevance with diversity to avoid redundant results.
        Useful when you want varied documents rather than similar ones.
        
        Args:
            query: The search query text
            k: Number of results to return
            fetch_k: Number of candidates to fetch before MMR re-ranking
            lambda_mult: Balance between relevance (1.0) and diversity (0.0)
        
        Returns:
            List of diverse LegalDocument entities
        
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the vector store is accessible and healthy.
        
        Returns:
            True if the store is operational, False otherwise

        """
        pass
