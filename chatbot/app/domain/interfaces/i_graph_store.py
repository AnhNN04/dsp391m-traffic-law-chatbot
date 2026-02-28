"""
Graph Store Interface

Abstract interface for graph database operations.
Concrete implementations: Neo4j, NetworkX, Amazon Neptune, etc.

Author: AnhNN217-FHN
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from app.domain.entities import LegalDocument, Violation


class IGraphStore(ABC):
    """
    Abstract interface for graph database operations.
    
    This interface defines the contract for graph database implementations.
    Graph stores are used to query structured relationships between
    violations, vehicles, and legal articles.
    
    """
    
    @abstractmethod
    def get_penalty_info(
        self,
        violation_desc: str,
        vehicle_type: Optional[str] = None,
        limit: int = 5
    ) -> List[LegalDocument]:
        """
        Get penalty information for a specific violation.
        
        This method queries the graph to find penalty information
        based on violation description and optionally vehicle type.
        
        Args:
            violation_desc: Description or keyword of the violation
                Example: "vượt đèn đỏ", "quá tốc độ", "không đội mũ"
            vehicle_type: Optional vehicle type filter ("motorcycle", "car", etc.)
            limit: Maximum number of results to return
        
        Returns:
            List of LegalDocument entities with penalty information
        
        Raises:
            GraphStoreError: If query execution fails

        """
        pass
    
    @abstractmethod
    def get_violation_details(
        self,
        violation_code: str
    ) -> Optional[Violation]:
        """
        Get detailed violation information by code.
        
        Args:
            violation_code: Unique violation code (e.g., "V001", "RED_LIGHT_001")
        
        Returns:
            Violation entity or None if not found
        

        """
        pass
    
    @abstractmethod
    def query_related_violations(
        self,
        violation_code: str,
        relationship_type: str = "SIMILAR_TO",
        max_depth: int = 2
    ) -> List[Violation]:
        """
        Find violations related to a given violation.
        
        Uses graph traversal to find connected violations based on
        relationships like SIMILAR_TO, OFTEN_WITH, etc.
        
        Args:
            violation_code: Starting violation code
            relationship_type: Type of relationship to follow
            max_depth: Maximum depth of graph traversal
        
        Returns:
            List of related Violation entities
        
        """
        pass
    
    @abstractmethod
    def run_cypher_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a raw Cypher query (for advanced use cases).
        
        This method provides low-level access to the graph database
        for complex queries not covered by other methods.
        
        Args:
            query: Cypher query string
            parameters: Query parameters for parameterized queries
        
        Returns:
            List of result records as dictionaries
        
        Raises:
            CypherQueryError: If query syntax is invalid or execution fails
        
        """
        pass
    
    @abstractmethod
    def get_law_structure(
        self,
        law_name: str
    ) -> Dict[str, Any]:
        """
        Get the hierarchical structure of a law.
        
        Returns the structure showing chapters, articles, and their
        relationships within a specific law document.
        
        Args:
            law_name: Name of the law (e.g., "Nghị định 100/2019/NĐ-CP")
        
        Returns:
            Dictionary representing the law structure
        
        """
        pass
    
    @abstractmethod
    def find_shortest_path(
        self,
        start_entity: str,
        end_entity: str,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find the shortest path between two entities in the graph.
        
        Useful for understanding legal relationships and dependencies.
        
        Args:
            start_entity: Starting node identifier
            end_entity: Target node identifier
            max_depth: Maximum path length to search
        
        Returns:
            List of nodes and relationships in the shortest path

        """
        pass
    
    @abstractmethod
    def add_violation(
        self,
        violation: Violation,
        vehicle_types: List[str],
        article_id: str
    ) -> None:
        """
        Add a new violation to the graph.
        
        Creates the violation node and its relationships to
        vehicle types and legal articles.
        
        Args:
            violation: Violation entity to add
            vehicle_types: List of applicable vehicle types
            article_id: ID of the legal article defining this violation
        
        """
        pass
    
    @abstractmethod
    def update_penalty(
        self,
        violation_code: str,
        penalty_min: int,
        penalty_max: int
    ) -> None:
        """
        Update penalty amounts for a violation.
        
        Args:
            violation_code: Code of the violation to update
            penalty_min: New minimum penalty
            penalty_max: New maximum penalty

        """
        pass
    
    @abstractmethod
    def search_by_keywords(
        self,
        keywords: List[str],
        match_all: bool = False
    ) -> List[LegalDocument]:
        """
        Search for documents using keyword matching in the graph.
        
        Args:
            keywords: List of keywords to search for
            match_all: If True, require all keywords; if False, any keyword
        
        Returns:
            List of matching LegalDocument entities
        
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the graph database.
        
        Returns:
            Dictionary with stats like node counts, relationship counts, etc.
        
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the graph store is accessible and healthy.
        
        Returns:
            True if the store is operational, False otherwise
        
        """
        pass
