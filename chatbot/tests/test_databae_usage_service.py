"""
Database Services Usage Examples

Demonstrates how to use ChromaDB, Neo4j, and Tavily services.

Run with:
    python -m tests.test_database_services_usage
"""

from app.infrastructure.persistence import ChromaRepo, Neo4jRepo
from app.infrastructure.external_services import TavilyService
from app.domain.entities import LegalDocument, DocumentSource
from app.infrastructure.config import setup_logger, settings


def example_chroma_basic():
    """Example 1: Basic vector search with ChromaDB."""
    print("=" * 60)
    print("EXAMPLE 1: ChromaDB - Vector Similarity Search")
    print("=" * 60)
    
    try:
        # Initialize from settings
        repo = ChromaRepo.from_settings()
        
        # Get collection stats
        stats = repo.get_collection_stats()
        print(f"Collection: {stats['collection_name']}")
        print(f"Documents: {stats['document_count']}")
        print()
        
        # Search for documents
        query = "vượt đèn đỏ xe máy phạt bao nhiêu"
        docs = repo.search(query, k=3)
        
        print(f"Query: {query}")
        print(f"Results found: {len(docs)}")
        print()
        
        for i, doc in enumerate(docs, 1):
            print(f"{i}. Score: {doc.score:.3f}")
            print(f"   Content: {doc.content[:100]}...")
            print(f"   Article: {doc.article_id}")
            print()
    
    except Exception as e:
        print(f"❌ ChromaDB example failed: {e}")
        print("   Make sure ChromaDB is initialized with data")
    
    print()


def example_chroma_add_documents():
    """Example 2: Add documents to ChromaDB."""
    print("=" * 60)
    print("EXAMPLE 2: ChromaDB - Add Documents")
    print("=" * 60)
    
    try:
        repo = ChromaRepo.from_settings()
        
        # Create sample documents
        sample_docs = [
            LegalDocument(
                content="Điều 5. Phạt tiền từ 4.000.000 đồng đến 6.000.000 đồng đối với người điều khiển xe mô tô vi phạm đèn đỏ.",
                source=DocumentSource.DATABASE,
                article_id="Dieu_5",
                law_name="Nghị định 100/2019/NĐ-CP",
                metadata={"chapter": 2, "vehicle": "motorcycle"}
            ),
            LegalDocument(
                content="Điều 6. Phạt tiền từ 800.000 đồng đến 1.000.000 đồng đối với người điều khiển xe không đội mũ bảo hiểm.",
                source=DocumentSource.DATABASE,
                article_id="Dieu_6",
                law_name="Nghị định 100/2019/NĐ-CP",
                metadata={"chapter": 2, "vehicle": "motorcycle"}
            )
        ]
        
        # Add to vector store
        repo.add_documents(
            documents=sample_docs,
            ids=["sample_1", "sample_2"]
        )
        
        print(f"✅ Added {len(sample_docs)} documents to vector store")
        print()
        
        # Verify by searching
        docs = repo.search("không đội mũ bảo hiểm", k=1)
        if docs:
            print("Verification search:")
            print(f"Found: {docs[0].content[:80]}...")
        
    except Exception as e:
        print(f"❌ Add documents failed: {e}")
    
    print()


def example_neo4j_penalty_query():
    """Example 3: Query Neo4j for penalty information."""
    print("=" * 60)
    print("EXAMPLE 3: Neo4j - Penalty Information Query")
    print("=" * 60)
    
    try:
        # Initialize from settings
        repo = Neo4jRepo.from_settings()
        
        # Check connection
        if not repo.health_check():
            print("❌ Neo4j connection failed")
            return
        
        print("✅ Connected to Neo4j")
        print()
        
        # Query penalty info
        docs = repo.get_penalty_info(
            violation_desc="đèn đỏ",
            vehicle_type="motorcycle",
            limit=3
        )
        
        print(f"Query: vượt đèn đỏ (xe máy)")
        print(f"Results found: {len(docs)}")
        print()
        
        for i, doc in enumerate(docs, 1):
            print(f"{i}. {doc.article_id} - {doc.law_name}")
            print(f"   {doc.content[:150]}...")
            print()
    
    except Exception as e:
        print(f"❌ Neo4j example failed: {e}")
        print("   Make sure Neo4j is running and populated with data")
    
    print()


def example_neo4j_cypher():
    """Example 4: Execute raw Cypher query."""
    print("=" * 60)
    print("EXAMPLE 4: Neo4j - Raw Cypher Query")
    print("=" * 60)
    
    try:
        repo = Neo4jRepo.from_settings()
        
        # Simple Cypher query
        cypher = """
        MATCH (v:Violation)
        RETURN v.name as violation_name, 
               v.penalty_min as penalty_min,
               v.penalty_max as penalty_max
        LIMIT 5
        """
        
        results = repo.run_cypher_query(cypher)
        
        print(f"Results: {len(results)}")
        print()
        
        for result in results:
            print(f"- {result['violation_name']}")
            print(f"  Phạt: {result['penalty_min']:,} - {result['penalty_max']:,} VNĐ".replace(",", "."))
        
    except Exception as e:
        print(f"❌ Cypher query failed: {e}")
    
    print()


def example_tavily_search():
    """Example 5: Web search with Tavily."""
    print("=" * 60)
    print("EXAMPLE 5: Tavily - Web Search")
    print("=" * 60)
    
    try:
        service = TavilyService.from_settings()
        
        # Perform web search
        query = "nghị định 100 2019 vượt đèn đỏ"
        docs = service.search(
            query=query,
            max_results=3,
            include_domains=["thuvienphapluat.vn", "luatvietnam.vn"]
        )
        
        print(f"Query: {query}")
        print(f"Results found: {len(docs)}")
        print()
        
        for i, doc in enumerate(docs, 1):
            url = doc.metadata.get("url", "")
            title = doc.metadata.get("title", "")
            print(f"{i}. {title}")
            print(f"   URL: {url}")
            print(f"   Content: {doc.content[:100]}...")
            print()
    
    except Exception as e:
        print(f"❌ Tavily search failed: {e}")
        print("   Make sure TAVILY_API_KEY is configured in .env")
    
    print()


def example_hybrid_retrieval():
    """Example 6: Hybrid retrieval (Vector + Graph)."""
    print("=" * 60)
    print("EXAMPLE 6: Hybrid Retrieval (Vector + Graph)")
    print("=" * 60)
    
    try:
        # Initialize both stores
        vector_repo = ChromaRepo.from_settings()
        graph_repo = Neo4jRepo.from_settings()
        
        query = "vượt đèn đỏ xe máy"
        
        # Search both stores
        print(f"Query: {query}")
        print()
        
        vector_docs = vector_repo.search(query, k=3)
        print(f"Vector results: {len(vector_docs)}")
        
        graph_docs = graph_repo.get_penalty_info(query, limit=2)
        print(f"Graph results: {len(graph_docs)}")
        print()
        
        # Combine results (graph has priority)
        all_docs = graph_docs + vector_docs
        
        print("Combined results:")
        for i, doc in enumerate(all_docs[:5], 1):
            print(f"{i}. Source: {doc.source.value}")
            print(f"   Score: {doc.score:.3f if doc.score else 'N/A'}")
            print(f"   {doc.content[:80]}...")
            print()
    
    except Exception as e:
        print(f"❌ Hybrid retrieval failed: {e}")
    
    print()


def example_fallback_pattern():
    """Example 7: Fallback pattern (DB -> Web Search)."""
    print("=" * 60)
    print("EXAMPLE 7: Fallback Pattern (DB -> Web Search)")
    print("=" * 60)
    
    try:
        vector_repo = ChromaRepo.from_settings()
        tavily = TavilyService.from_settings()
        
        query = "luật giao thông mới nhất 2026"
        
        # Try local database first
        print(f"Query: {query}")
        print()
        
        local_docs = vector_repo.search(query, k=3)
        
        if local_docs and any(doc.score > 0.7 for doc in local_docs):
            print("✅ Found in local database")
            best_doc = max(local_docs, key=lambda d: d.score)
            print(f"Best match (score: {best_doc.score:.3f})")
            print(f"{best_doc.content[:100]}...")
        else:
            print("⚠️  No good match in local database")
            print("Falling back to web search...")
            print()
            
            web_docs = tavily.search(query, max_results=2)
            if web_docs:
                print("✅ Found on the web")
                print(f"{web_docs[0].content[:100]}...")
            else:
                print("❌ No results found")
    
    except Exception as e:
        print(f"❌ Fallback pattern failed: {e}")
    
    print()


def main():
    """Run all examples."""
    
    # Setup logging
    setup_logger(log_level="INFO")
    
    print("\n")
    print("=" * 60)
    print("DATABASE SERVICES EXAMPLES")
    print("=" * 60)
    print()
    
    # ChromaDB examples
    example_chroma_basic()
    example_chroma_add_documents()
    
    # Neo4j examples
    example_neo4j_penalty_query()
    example_neo4j_cypher()
    
    # Tavily examples
    example_tavily_search()
    
    # Advanced patterns
    example_hybrid_retrieval()
    example_fallback_pattern()
    
    print("=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
