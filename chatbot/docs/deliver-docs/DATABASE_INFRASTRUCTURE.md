# Database Infrastructure Guide

## Overview

This layer implements concrete database services that provide the knowledge base for the Traffic Law Agent:

- **ChromaDB**: Vector similarity search for semantic retrieval
- **Neo4j**: Graph database for structured legal relationships
- **Tavily**: Web search fallback for current information

## Architecture

```
app/infrastructure/
├── persistence/
│   ├── chroma_repo.py        # Vector store implementation
│   └── neo4j_repo.py          # Graph store implementation
└── external_services/
    └── tavily_service.py      # Web search implementation
```

## ChromaDB Vector Store

### Purpose
Semantic search over legal documents using embeddings. Finds documents that are conceptually similar to the query, even if they don't share exact keywords.

### Tech Stack
- **Database**: ChromaDB (local persistence)
- **Embeddings**: Google text-embedding-004 (768 dimensions)
- **Interface**: LangChain Chroma integration

### Features
- ✅ Local file-based persistence (`./data/chroma_db`)
- ✅ High-quality Google embeddings (free tier)
- ✅ Similarity scores for ranking
- ✅ Metadata filtering support

### Usage

```python
from app.infrastructure.persistence import ChromaRepo

# Initialize from settings
repo = ChromaRepo.from_settings()

# Or manually
repo = ChromaRepo(
    google_api_key="your-api-key",
    persist_directory="./data/chroma_db",
    collection_name="legal_documents"
)

# Search
docs = repo.search("vượt đèn đỏ xe máy", k=5)
for doc in docs:
    print(f"Score: {doc.score:.3f}")
    print(f"Content: {doc.content[:100]}")

# Add documents
from app.domain.entities import LegalDocument, DocumentSource

new_doc = LegalDocument(
    content="Điều 5. Phạt tiền...",
    source=DocumentSource.DATABASE,
    article_id="Dieu_5"
)
repo.add_documents([new_doc], ids=["doc_1"])

# Get stats
stats = repo.get_collection_stats()
print(f"Total documents: {stats['document_count']}")
```

### When to Use
✅ Broad queries ("luật về xe máy")  
✅ Semantic search ("quy định đèn giao thông")  
✅ When exact keywords aren't known  
❌ When you need exact penalty amounts (use Neo4j instead)

## Neo4j Graph Store

### Purpose
Structured queries for exact information. Stores relationships between violations, vehicles, and legal articles in a graph structure.

### Tech Stack
- **Database**: Neo4j Aura (cloud) or local Neo4j
- **Query Language**: Cypher
- **Driver**: Neo4j Python driver

### Graph Schema

```cypher
# Nodes
(Violation) - Properties: name, penalty_min, penalty_max, description
(Vehicle) - Properties: type (motorcycle, car, truck)
(Article) - Properties: article_id, law_name, content

# Relationships
(Violation)-[:APPLIES_TO]->(Vehicle)
(Violation)-[:DEFINED_IN]->(Article)
```

### Features
- ✅ Exact penalty lookups
- ✅ Vehicle-specific queries
- ✅ Legal reference tracking
- ✅ Raw Cypher support for advanced queries

### Usage

```python
from app.infrastructure.persistence import Neo4jRepo

# Initialize from settings
repo = Neo4jRepo.from_settings()

# Or manually
repo = Neo4jRepo(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="your-password"
)

# Get penalty info
docs = repo.get_penalty_info(
    violation_desc="vượt đèn đỏ",
    vehicle_type="motorcycle",
    limit=3
)

for doc in docs:
    print(doc.content)
    # Output:
    # Lỗi: Vượt đèn đỏ
    # Mức phạt: 4.000.000 - 6.000.000 VNĐ
    # Căn cứ pháp lý: Điều 5...

# Raw Cypher query
results = repo.run_cypher_query("""
    MATCH (v:Violation)-[:APPLIES_TO]->(veh:Vehicle {type: 'motorcycle'})
    RETURN v.name, v.penalty_min, v.penalty_max
    LIMIT 5
""")

# Health check
if repo.health_check():
    print("Neo4j is connected")

# Always close when done
repo.close()

# Or use context manager
with Neo4jRepo.from_settings() as repo:
    docs = repo.get_penalty_info("vượt đèn đỏ")
```

### When to Use
✅ Exact penalty queries  
✅ Vehicle-specific information  
✅ Legal reference lookups  
✅ Structured data extraction  
❌ Vague/broad queries (use ChromaDB instead)

## Tavily Web Search

### Purpose
Fallback search when information isn't in the local database. Optimized for LLM applications with clean, structured results.

### Tech Stack
- **Provider**: Tavily API
- **Filtering**: Domain-based restriction
- **Output**: Clean text (no HTML/ads)

### Features
- ✅ Free tier: ~1000 searches/month
- ✅ LLM-optimized results (clean text)
- ✅ Domain filtering (only trusted legal sites)
- ✅ Fast search (< 2s typical)

### Usage

```python
from app.infrastructure.external_services import TavilyService

# Initialize from settings
service = TavilyService.from_settings()

# Or manually
service = TavilyService(api_key="tvly-...")

# Search with domain filtering
docs = service.search(
    query="nghị định 100 vượt đèn đỏ",
    max_results=3,
    include_domains=["thuvienphapluat.vn", "luatvietnam.vn"],
    search_depth="basic"  # or "advanced"
)

for doc in docs:
    url = doc.metadata.get("url")
    print(f"Source: {url}")
    print(f"Content: {doc.content[:100]}")

# Get full metadata
results = service.search_with_metadata(
    query="luật giao thông 2026",
    max_results=5
)

for result in results:
    print(result["title"])
    print(result["url"])
    print(result["published_date"])
```

### When to Use
✅ Query about recent changes/news  
✅ Information not in local database  
✅ Administrative procedures (website links)  
❌ Historical legal documents (use local DB)

## Hybrid Retrieval Pattern

Combine vector, graph, and web search for best results:

```python
from app.infrastructure.persistence import ChromaRepo, Neo4jRepo
from app.infrastructure.external_services import TavilyService

class HybridRetriever:
    def __init__(self):
        self.vector = ChromaRepo.from_settings()
        self.graph = Neo4jRepo.from_settings()
        self.web = TavilyService.from_settings()
    
    def retrieve(self, query: str, vehicle_type: str = None):
        # Step 1: Try graph for exact matches
        graph_docs = self.graph.get_penalty_info(query, vehicle_type)
        
        if graph_docs:
            return graph_docs, "graph"
        
        # Step 2: Try vector for semantic search
        vector_docs = self.vector.search(query, k=5)
        
        # Check if results are good enough
        if vector_docs and max(d.score for d in vector_docs) > 0.7:
            return vector_docs, "vector"
        
        # Step 3: Fallback to web search
        web_docs = self.web.search(query, max_results=3)
        
        return web_docs, "web"

# Usage
retriever = HybridRetriever()
docs, source = retriever.retrieve("vượt đèn đỏ xe máy")
print(f"Found {len(docs)} docs from {source}")
```

## Configuration

All services read from `.env`:

```bash
# Google (for ChromaDB embeddings)
GOOGLE_API_KEY=your-google-api-key

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma_db
CHROMA_COLLECTION_NAME=legal_documents
EMBEDDING_MODEL=models/embedding-004

# Neo4j
NEO4J_URI=bolt://localhost:7687  # or neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Tavily
TAVILY_API_KEY=tvly-your-api-key
```

## Data Seeding

Before using, you need to populate the databases:

### ChromaDB Seeding

```python
from app.infrastructure.persistence import ChromaRepo
from app.domain.entities import LegalDocument, DocumentSource

repo = ChromaRepo.from_settings()

# Example: Load from JSON file
import json

with open("data/legal_docs.json") as f:
    raw_docs = json.load(f)

legal_docs = [
    LegalDocument(
        content=doc["content"],
        source=DocumentSource.DATABASE,
        article_id=doc["article_id"],
        law_name=doc["law_name"],
        metadata=doc.get("metadata", {})
    )
    for doc in raw_docs
]

repo.add_documents(legal_docs)
print(f"Added {len(legal_docs)} documents")
```

### Neo4j Seeding

```python
from app.infrastructure.persistence import Neo4jRepo

repo = Neo4jRepo.from_settings()

# Create violations
create_violation = """
CREATE (v:Violation {
    name: 'Vượt đèn đỏ',
    penalty_min: 4000000,
    penalty_max: 6000000,
    description: 'Không chấp hành hiệu lệnh đèn đỏ',
    keywords: 'đèn đỏ,đèn giao thông,tín hiệu'
})

CREATE (veh:Vehicle {type: 'motorcycle'})
CREATE (a:Article {
    article_id: 'Điều 5',
    law_name: 'Nghị định 100/2019/NĐ-CP',
    content: 'Phạt tiền từ 4-6 triệu đồng...'
})

CREATE (v)-[:APPLIES_TO]->(veh)
CREATE (v)-[:DEFINED_IN]->(a)
"""

repo.run_cypher_query(create_violation)
```

## Error Handling

All services implement comprehensive error handling:

```python
from app.domain.exceptions import (
    VectorStoreError,
    GraphStoreError,
    WebSearchError
)

try:
    docs = vector_repo.search(query)
except VectorStoreError as e:
    logger.error(f"Vector search failed: {e.message}")
    # Fallback to graph or web

try:
    docs = graph_repo.get_penalty_info(query)
except GraphStoreError as e:
    logger.error(f"Graph query failed: {e.message}")
    # Fallback to vector or web

try:
    docs = web_service.search(query)
except WebSearchError as e:
    logger.error(f"Web search failed: {e.message}")
    # Return error message to user
```

## Performance Comparison

| Service | Latency | Accuracy | Cost | Best For |
|---------|---------|----------|------|----------|
| ChromaDB | ~200ms | Good | Free | Semantic search |
| Neo4j | ~50ms | Excellent | Free tier | Exact queries |
| Tavily | ~2s | Variable | ~$0.001/search | Current info |

## Testing

Run examples to test your setup:

```bash
# Make sure all services are configured in .env
python -m examples.database_services_usage
```

## Troubleshooting

### ChromaDB: "Collection not found"
**Solution**: Initialize with `add_documents()` first, or the collection is empty

### Neo4j: "Connection refused"
**Solution**: Make sure Neo4j is running (`docker ps` or check Aura cloud)

### Tavily: "Invalid API key"
**Solution**: Check `TAVILY_API_KEY` in `.env` starts with `tvly-`

### Google Embeddings: "Quota exceeded"
**Solution**: Google has generous free tier but there are limits. Wait or use different API key.

## Next Steps

After database infrastructure:
1. ✅ Create application nodes (Rewrite, Retrieval, Generate)
2. ✅ Wire everything in Container
3. ✅ Build the LangGraph workflow
4. ✅ Add checkpointing with MongoDB

---

**Dependencies Required:**
```bash
pipenv install \
  langchain-chroma \
  langchain-google-genai \
  chromadb \
  neo4j \
  tavily-python
```
