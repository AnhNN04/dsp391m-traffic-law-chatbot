"""
ChromaDB Vector Store Implementation

Concrete implementation of IVectorStore using ChromaDB for vector similarity search.
Uses Google's embedding model for high-quality semantic search.

Author: AnhNN217-FHN
"""

from typing import List, Optional
import os

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

from app.domain.interfaces import IVectorStore
from app.domain.entities import LegalDocument, DocumentSource
from app.domain.exceptions import VectorStoreError, DatabaseConnectionError
from app.infrastructure.config import get_logger, settings

logger = get_logger(__name__)


class ChromaRepo(IVectorStore):
    """
    ChromaDB implementation of IVectorStore.
    
    Uses Google's text-embedding-004 model for semantic search.
    Stores embeddings locally in ./data/chroma_db directory.
    
    Attributes:
        client: Chroma vector store instance
        embeddings: Google embedding function
        collection_name: Name of the Chroma collection
        persist_directory: Local path for persistence
    
    Example:
        >>> repo = ChromaRepo.from_settings()
        >>> docs = repo.search("vượt đèn đỏ", k=5)
        >>> for doc in docs:
        ...     print(doc.content[:100])
    """
    
    def __init__(
        self,
        google_api_key: str,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "legal_documents",
        embedding_model: str = "models/embedding-004"
    ):
        """
        Initialize ChromaDB repository.
        
        Args:
            google_api_key: Google API key for embeddings
            persist_directory: Local directory for vector storage
            collection_name: Name of the Chroma collection
            embedding_model: Google embedding model name
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        try:
            # Create persist directory if it doesn't exist
            os.makedirs(persist_directory, exist_ok=True)
            
            # Initialize Google embeddings
            logger.info(
                "Initializing Google embeddings",
                model=embedding_model
            )
            self.embeddings = GoogleGenerativeAIEmbeddings(
                google_api_key=google_api_key,
                model=embedding_model
            )
            
            # Initialize Chroma client
            logger.info(
                "Initializing ChromaDB client",
                persist_directory=persist_directory,
                collection=collection_name
            )
            self.client = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=persist_directory
            )
            
            logger.info(
                "ChromaDB repository initialized successfully",
                collection=collection_name
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize ChromaDB repository",
                error=str(e),
                persist_directory=persist_directory
            )
            raise DatabaseConnectionError(
                "Failed to initialize ChromaDB",
                database_type="ChromaDB",
                connection_string=persist_directory
            ) from e
    
    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[dict] = None
    ) -> List[LegalDocument]:
        """
        Search for similar documents using semantic similarity.
        
        Args:
            query: The search query text
            k: Number of results to return
            filter_metadata: Optional metadata filters (not used in basic implementation)
        
        Returns:
            List of LegalDocument entities ordered by relevance
        
        Raises:
            VectorStoreError: If search operation fails
        
        Example:
            >>> docs = repo.search("vượt đèn đỏ xe máy", k=3)
            >>> for doc in docs:
            ...     print(f"Score: {doc.score}, Content: {doc.content[:50]}")
        """
        try:
            logger.debug(
                "Performing vector similarity search",
                query=query[:100],
                k=k
            )
            
            # Perform similarity search with scores
            results = self.client.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_metadata
            )
            
            # Convert to LegalDocument entities
            legal_docs = []
            for doc, score in results:
                legal_doc = self._langchain_doc_to_legal_document(
                    doc,
                    score=float(score)
                )
                legal_docs.append(legal_doc)
            
            logger.debug(
                "Vector search completed",
                results_found=len(legal_docs),
                top_score=legal_docs[0].score if legal_docs else None
            )
            
            return legal_docs
            
        except Exception as e:
            logger.error(
                "Vector search failed",
                error=str(e),
                query=query[:100],
                k=k
            )
            raise VectorStoreError(
                f"Vector search failed: {str(e)}"
            ) from e
    
    def add_documents(
        self,
        documents: List[LegalDocument],
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of LegalDocument entities to add
            ids: Optional list of unique IDs for each document
        
        Raises:
            VectorStoreError: If add operation fails
        
        Example:
            >>> doc = LegalDocument(
            ...     content="Điều 5. Phạt tiền...",
            ...     source=DocumentSource.DATABASE,
            ...     article_id="Dieu_5"
            ... )
            >>> repo.add_documents([doc], ids=["doc_1"])
        """
        try:
            logger.info(
                "Adding documents to vector store",
                count=len(documents)
            )
            
            # Convert LegalDocument to LangChain Document
            langchain_docs = [
                self._legal_document_to_langchain_doc(doc)
                for doc in documents
            ]
            
            # Generate IDs if not provided
            if ids is None:
                ids = [f"doc_{i}" for i in range(len(documents))]
            
            # Add to Chroma
            self.client.add_documents(
                documents=langchain_docs,
                ids=ids
            )
            
            logger.info(
                "Documents added successfully",
                count=len(documents)
            )
            
        except Exception as e:
            logger.error(
                "Failed to add documents",
                error=str(e),
                count=len(documents)
            )
            raise VectorStoreError(
                f"Failed to add documents: {str(e)}"
            ) from e
    
    def delete_documents(self, ids: List[str]) -> None:
        """
        Delete documents from the vector store.
        
        Args:
            ids: List of document IDs to delete
        
        Raises:
            VectorStoreError: If delete operation fails
        """
        try:
            logger.info("Deleting documents", count=len(ids))
            
            self.client.delete(ids=ids)
            
            logger.info("Documents deleted successfully", count=len(ids))
            
        except Exception as e:
            logger.error("Failed to delete documents", error=str(e))
            raise VectorStoreError(
                f"Failed to delete documents: {str(e)}"
            ) from e
    
    def get_collection_stats(self) -> dict:
        """
        Get statistics about the vector store collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.client._collection.count()
            
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error("Failed to get collection stats", error=str(e))
            return {
                "collection_name": self.collection_name,
                "error": str(e)
            }
    
    def _langchain_doc_to_legal_document(
        self,
        doc: Document,
        score: float
    ) -> LegalDocument:
        """
        Convert LangChain Document to LegalDocument entity.
        
        Args:
            doc: LangChain Document
            score: Similarity score
        
        Returns:
            LegalDocument entity
        """
        return LegalDocument(
            content=doc.page_content,
            source=DocumentSource.VECTOR_STORE,
            metadata=doc.metadata,
            score=score,
            article_id=doc.metadata.get("article_id"),
            law_name=doc.metadata.get("law_name")
        )
    
    def _legal_document_to_langchain_doc(
        self,
        legal_doc: LegalDocument
    ) -> Document:
        """
        Convert LegalDocument entity to LangChain Document.
        
        Args:
            legal_doc: LegalDocument entity
        
        Returns:
            LangChain Document
        """
        metadata = legal_doc.metadata.copy()
        
        # Add entity fields to metadata
        if legal_doc.article_id:
            metadata["article_id"] = legal_doc.article_id
        if legal_doc.law_name:
            metadata["law_name"] = legal_doc.law_name
        
        return Document(
            page_content=legal_doc.content,
            metadata=metadata
        )
    
    @classmethod
    def from_settings(cls) -> "ChromaRepo":
        """
        Create ChromaRepo from application settings.
        
        Returns:
            Configured ChromaRepo instance
        
        Example:
            >>> repo = ChromaRepo.from_settings()
        """
        return cls(
            google_api_key=settings.GOOGLE_API_KEY,
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_model=settings.EMBEDDING_MODEL
        )