"""
Neo4j Graph Store Implementation

Concrete implementation of IGraphStore using Neo4j for graph-based queries.
Stores structured relationships between violations, vehicles, and legal articles.

Author: AnhNN217-FHN
"""

from typing import List, Optional
from neo4j import GraphDatabase

from app.domain.interfaces import IGraphStore
from app.domain.entities import LegalDocument, DocumentSource
from app.domain.exceptions import GraphStoreError, DatabaseConnectionError, CypherQueryError
from app.infrastructure.config import get_logger, settings

logger = get_logger(__name__)


class Neo4jRepo(IGraphStore):
    """
    Neo4j implementation of IGraphStore.
    
    Uses Neo4j graph database to store and query structured legal knowledge.
    Supports complex relationship queries via Cypher.
    
    Attributes:
        driver: Neo4j driver instance
        uri: Neo4j connection URI
        database: Database name (default: "neo4j")
    
    Example:
        >>> repo = Neo4jRepo.from_settings()
        >>> docs = repo.get_penalty_info("vượt đèn đỏ")
        >>> for doc in docs:
        ...     print(doc.content)
    """
    
    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        database: str = "neo4j"
    ):
        """
        Initialize Neo4j repository.
        
        Args:
            uri: Neo4j connection URI (e.g., bolt://localhost:7687)
            username: Neo4j username
            password: Neo4j password
            database: Database name (default: neo4j)
        """
        self.uri = uri
        self.database = database
        
        try:
            logger.info(
                "Connecting to Neo4j",
                uri=uri,
                database=database
            )
            
            self.driver = GraphDatabase.driver(
                uri,
                auth=(username, password)
            )
            
            # Test connection
            with self.driver.session(database=database) as session:
                result = session.run("RETURN 1 as test")
                result.single()
            
            logger.info(
                "Neo4j connection established successfully",
                uri=uri
            )
            
        except Exception as e:
            logger.error(
                "Failed to connect to Neo4j",
                error=str(e),
                uri=uri
            )
            raise DatabaseConnectionError(
                "Failed to connect to Neo4j",
                database_type="Neo4j",
                connection_string=uri
            ) from e
    
    def get_penalty_info(
        self,
        violation_desc: str,
        vehicle_type: Optional[str] = None,
        limit: int = 5
    ) -> List[LegalDocument]:
        """
        Get penalty information for a specific violation.
        
        Searches the graph for violations matching the description
        and returns penalty details as LegalDocument entities.
        
        Args:
            violation_desc: Description or keyword of the violation
            vehicle_type: Optional vehicle type filter
            limit: Maximum number of results
        
        Returns:
            List of LegalDocument entities with penalty information
        
        Example:
            >>> docs = repo.get_penalty_info("vượt đèn đỏ", vehicle_type="motorcycle")
            >>> print(docs[0].content)
        """
        try:
            logger.debug(
                "Querying penalty info from graph",
                violation_desc=violation_desc,
                vehicle_type=vehicle_type,
                limit=limit
            )
            
            # Build Cypher query
            if vehicle_type:
                cypher = """
                MATCH (v:Violation)-[:APPLIES_TO]->(veh:Vehicle {type: $vehicle_type})
                WHERE v.name CONTAINS $violation_desc 
                   OR v.description CONTAINS $violation_desc
                   OR v.keywords CONTAINS $violation_desc
                MATCH (v)-[:DEFINED_IN]->(a:Article)
                RETURN v.name as violation_name,
                       v.penalty_min as penalty_min,
                       v.penalty_max as penalty_max,
                       v.description as description,
                       v.additional_penalties as additional_penalties,
                       a.content as article_content,
                       a.article_id as article_id,
                       a.law_name as law_name
                LIMIT $limit
                """
                parameters = {
                    "violation_desc": violation_desc,
                    "vehicle_type": vehicle_type,
                    "limit": limit
                }
            else:
                cypher = """
                MATCH (v:Violation)
                WHERE v.name CONTAINS $violation_desc 
                   OR v.description CONTAINS $violation_desc
                   OR v.keywords CONTAINS $violation_desc
                MATCH (v)-[:DEFINED_IN]->(a:Article)
                RETURN v.name as violation_name,
                       v.penalty_min as penalty_min,
                       v.penalty_max as penalty_max,
                       v.description as description,
                       v.additional_penalties as additional_penalties,
                       a.content as article_content,
                       a.article_id as article_id,
                       a.law_name as law_name
                LIMIT $limit
                """
                parameters = {
                    "violation_desc": violation_desc,
                    "limit": limit
                }
            
            # Execute query
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher, parameters)
                records = list(result)
            
            # Convert to LegalDocument entities
            legal_docs = []
            for record in records:
                # Build content from violation and article info
                content = self._format_penalty_content(record)
                
                legal_doc = LegalDocument(
                    content=content,
                    source=DocumentSource.GRAPH_STORE,
                    metadata={
                        "violation_name": record.get("violation_name"),
                        "penalty_min": record.get("penalty_min"),
                        "penalty_max": record.get("penalty_max"),
                        "additional_penalties": record.get("additional_penalties"),
                        "description": record.get("description")
                    },
                    article_id=record.get("article_id"),
                    law_name=record.get("law_name"),
                    score=1.0  # Graph results are exact matches
                )
                legal_docs.append(legal_doc)
            
            logger.debug(
                "Graph query completed",
                results_found=len(legal_docs)
            )
            
            return legal_docs
            
        except Exception as e:
            logger.error(
                "Graph query failed",
                error=str(e),
                violation_desc=violation_desc
            )
            raise GraphStoreError(
                f"Failed to query penalty info: {str(e)}"
            ) from e
    
    def run_cypher_query(
        self,
        query: str,
        parameters: Optional[dict] = None
    ) -> List[dict]:
        """
        Execute a raw Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
        
        Returns:
            List of result records as dictionaries
        
        Raises:
            CypherQueryError: If query execution fails
        
        Example:
            >>> results = repo.run_cypher_query(
            ...     "MATCH (v:Violation) RETURN v.name LIMIT 5"
            ... )
        """
        try:
            logger.debug(
                "Executing Cypher query",
                query=query[:100],
                parameters=parameters
            )
            
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                records = [record.data() for record in result]
            
            logger.debug(
                "Cypher query completed",
                results_count=len(records)
            )
            
            return records
            
        except Exception as e:
            logger.error(
                "Cypher query failed",
                error=str(e),
                query=query[:100]
            )
            raise CypherQueryError(
                f"Cypher query execution failed: {str(e)}",
                cypher=query
            ) from e
    
    def _format_penalty_content(self, record: dict) -> str:
        """
        Format graph query result into readable content.
        
        Args:
            record: Neo4j query result record
        
        Returns:
            Formatted content string
        """
        parts = []
        
        # Violation name
        violation_name = record.get("violation_name", "")
        if violation_name:
            parts.append(f"Lỗi: {violation_name}")
        
        # Description
        description = record.get("description", "")
        if description:
            parts.append(f"Mô tả: {description}")
        
        # Penalty range
        penalty_min = record.get("penalty_min")
        penalty_max = record.get("penalty_max")
        if penalty_min is not None and penalty_max is not None:
            penalty_str = self._format_penalty_range(penalty_min, penalty_max)
            parts.append(f"Mức phạt: {penalty_str}")
        
        # Additional penalties
        additional = record.get("additional_penalties", "")
        if additional:
            parts.append(f"Hình phạt bổ sung: {additional}")
        
        # Article content
        article_content = record.get("article_content", "")
        if article_content:
            parts.append(f"\nCăn cứ pháp lý:\n{article_content}")
        
        return "\n".join(parts)
    
    def _format_penalty_range(self, min_amount: int, max_amount: int) -> str:
        """Format penalty range with thousands separator."""
        if min_amount == max_amount:
            return f"{min_amount:,} VNĐ".replace(",", ".")
        return f"{min_amount:,} - {max_amount:,} VNĐ".replace(",", ".")
    
    def health_check(self) -> bool:
        """
        Check if Neo4j connection is healthy.
        
        Returns:
            True if connection is working, False otherwise
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                result.single()
            return True
        except Exception as e:
            logger.error("Neo4j health check failed", error=str(e))
            return False
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self): #, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    @classmethod
    def from_settings(cls) -> "Neo4jRepo":
        """
        Create Neo4jRepo from application settings.
        
        Returns:
            Configured Neo4jRepo instance
        
        Example:
            >>> repo = Neo4jRepo.from_settings()
        """
        return cls(
            uri=settings.NEO4J_URI,
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD
        )
