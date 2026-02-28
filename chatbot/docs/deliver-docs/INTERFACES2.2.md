# Interface Architecture Guide

## Overview

This document explains the **Dependency Inversion Principle** implementation in the Traffic Law Agent system. All concrete implementations depend on abstractions (interfaces), not the other way around.

## Why Interfaces?

### Without Interfaces (Bad) ❌
```python
# Node directly depends on concrete ChromaDB implementation
from chromadb import Chroma

class RetrievalNode:
    def __init__(self):
        self.db = Chroma(...)  # Tightly coupled!
    
    def run(self, query):
        return self.db.similarity_search(query)
```

**Problems:**
- Can't swap ChromaDB for Pinecone without rewriting `RetrievalNode`
- Can't test without a real database
- Changes to ChromaDB API break all nodes

### With Interfaces (Good) ✅
```python
# Node depends on abstract interface
from app.domain.interfaces import IVectorStore

class RetrievalNode:
    def __init__(self, vector_store: IVectorStore):
        self.vector_store = vector_store  # Loosely coupled!
    
    def run(self, query):
        return self.vector_store.search(query)
```

**Benefits:**
- Swap implementations in one place (Container)
- Test with mock implementations
- Isolate changes to implementations

## Interface Hierarchy

```
app/
├── domain/
│   └── interfaces/          # Data layer contracts
│       ├── i_vector_store.py
│       └── i_graph_store.py
│
└── application/
    └── interfaces/          # Service layer contracts
        ├── i_llm_service.py
        ├── i_search_tool.py
        └── i_embedding_service.py
```

## Domain Interfaces

### IVectorStore
**Purpose:** Vector similarity search  
**Implementations:** ChromaDB, Pinecone, Qdrant, Weaviate

**Core Methods:**
```python
search(query, k=5) -> List[LegalDocument]
add_documents(documents) -> None
similarity_search_with_score(query, k=5) -> List[tuple[LegalDocument, float]]
max_marginal_relevance_search(query, k=5) -> List[LegalDocument]
```

**Usage in Nodes:**
```python
class RetrievalNode:
    def __init__(self, vector_store: IVectorStore):
        self.vector_store = vector_store
    
    def __call__(self, state: AgentState) -> dict:
        query = state["rewritten_query"]
        docs = self.vector_store.search(query, k=5)
        return {"documents": docs}
```

### IGraphStore
**Purpose:** Structured relationship queries  
**Implementations:** Neo4j, Amazon Neptune, NetworkX

**Core Methods:**
```python
get_penalty_info(violation_desc, vehicle_type) -> List[LegalDocument]
get_violation_details(violation_code) -> Optional[Violation]
run_cypher_query(query, parameters) -> List[Dict]
query_related_violations(violation_code) -> List[Violation]
```

**Usage in Nodes:**
```python
class RetrievalNode:
    def __init__(self, vector_store: IVectorStore, graph_store: IGraphStore):
        self.vector_store = vector_store
        self.graph_store = graph_store
    
    def __call__(self, state: AgentState) -> dict:
        query = state["rewritten_query"]
        
        # Hybrid search: vector + graph
        vector_docs = self.vector_store.search(query, k=5)
        graph_docs = self.graph_store.get_penalty_info(query)
        
        # Merge results (graph has higher priority)
        all_docs = graph_docs + vector_docs
        return {"documents": all_docs}
```

## Application Interfaces

### ILLMService
**Purpose:** Language model operations  
**Implementations:** OpenAI (GPT-4o-mini), Groq (Llama-3), Anthropic (Claude)

**Core Methods:**
```python
generate(prompt, system_message) -> str
generate_structured(prompt, schema) -> BaseModel
generate_with_tools(prompt, tools) -> Dict
generate_streaming(prompt) -> Iterator[str]
```

**Usage Pattern:**
```python
# Smart LLM for complex reasoning
class RewriteNode:
    def __init__(self, smart_llm: ILLMService):
        self.llm = smart_llm
    
    def __call__(self, state: AgentState) -> dict:
        prompt = f"Rewrite this query: {state['messages'][-1].content}"
        rewritten = self.llm.generate(prompt, temperature=0.1)
        return {"rewritten_query": rewritten}

# Fast LLM for quick classification
class RouterNode:
    def __init__(self, fast_llm: ILLMService):
        self.llm = fast_llm
    
    def __call__(self, state: AgentState) -> dict:
        from pydantic import BaseModel
        
        class Intent(BaseModel):
            intent: str
        
        result = self.llm.generate_structured(
            state["rewritten_query"],
            schema=Intent
        )
        return {"intent": result.intent}
```

### ISearchTool
**Purpose:** Web search fallback  
**Implementations:** Tavily, Serper, Google Custom Search

**Core Methods:**
```python
search(query, max_results, include_domains) -> List[LegalDocument]
search_with_metadata(query) -> List[Dict]
get_page_content(url) -> str
```

**Usage in Nodes:**
```python
class WebSearchNode:
    def __init__(self, search_tool: ISearchTool):
        self.search = search_tool
    
    def __call__(self, state: AgentState) -> dict:
        query = state["rewritten_query"]
        
        # Search only trusted legal websites
        docs = self.search.search(
            query,
            max_results=3,
            include_domains=[
                "thuvienphapluat.vn",
                "luatvietnam.vn",
                "baochinhphu.vn"
            ]
        )
        
        return {
            "documents": state["documents"] + docs,
            "data_source": "internet"
        }
```

## Dependency Injection Pattern

All interfaces are wired together in the **Container**:

```python
# app/container.py

from app.domain.interfaces import IVectorStore, IGraphStore
from app.application.interfaces import ILLMService, ISearchTool

from app.infrastructure.persistence.chroma_repo import ChromaVectorStore
from app.infrastructure.persistence.neo4j_repo import Neo4jGraphStore
from app.infrastructure.external_services.openai_service import OpenAIService
from app.infrastructure.external_services.groq_service import GroqService
from app.infrastructure.external_services.tavily_service import TavilySearchService

from app.application.nodes.rewrite_node import RewriteNode
from app.application.nodes.retrieval_node import RetrievalNode

class Container:
    def __init__(self):
        # Step 1: Initialize Infrastructure (Concrete Implementations)
        self.vector_store: IVectorStore = ChromaVectorStore(...)
        self.graph_store: IGraphStore = Neo4jGraphStore(...)
        self.smart_llm: ILLMService = OpenAIService(model="gpt-4o-mini")
        self.fast_llm: ILLMService = GroqService(model="llama-3-8b")
        self.search_tool: ISearchTool = TavilySearchService(...)
        
        # Step 2: Initialize Nodes (Inject Dependencies)
        self.rewrite_node = RewriteNode(
            smart_llm=self.smart_llm
        )
        
        self.retrieval_node = RetrievalNode(
            vector_store=self.vector_store,
            graph_store=self.graph_store
        )
        
        self.web_search_node = WebSearchNode(
            search_tool=self.search_tool
        )
        
        # Step 3: Build Graph
        self.graph = self._build_graph()
    
    def _build_graph(self):
        from langgraph.graph import StateGraph
        
        graph = StateGraph(AgentState)
        graph.add_node("rewrite", self.rewrite_node)
        graph.add_node("retrieval", self.retrieval_node)
        graph.add_node("web_search", self.web_search_node)
        # ... add edges
        
        return graph.compile()
```

## Testing with Mock Implementations

Interfaces make testing trivial:

```python
# tests/mocks/mock_vector_store.py

from app.domain.interfaces import IVectorStore
from app.domain.entities import LegalDocument, DocumentSource

class MockVectorStore(IVectorStore):
    """Mock implementation for testing."""
    
    def __init__(self):
        self.documents = []
    
    def search(self, query, k=5, filter_metadata=None):
        # Return fake documents for testing
        return [
            LegalDocument(
                content=f"Mock result for: {query}",
                source=DocumentSource.DATABASE,
                score=0.95
            )
        ]
    
    def add_documents(self, documents, ids=None):
        self.documents.extend(documents)
    
    # ... implement other methods

# tests/test_retrieval_node.py

def test_retrieval_node():
    # Use mock instead of real ChromaDB
    mock_store = MockVectorStore()
    node = RetrievalNode(vector_store=mock_store, graph_store=None)
    
    state = create_initial_state("session_123")
    state["rewritten_query"] = "test query"
    
    result = node(state)
    
    assert len(result["documents"]) > 0
    assert "Mock result" in result["documents"][0].content
```

## Swapping Implementations

Want to switch from ChromaDB to Pinecone? Only change the Container:

```python
# Before
self.vector_store = ChromaVectorStore(persist_dir="./data")

# After
self.vector_store = PineconeVectorStore(
    api_key=settings.PINECONE_API_KEY,
    index_name="traffic-law"
)

# Nodes don't need any changes!
```

## Summary

**Key Principles:**
1. **Depend on Abstractions:** Nodes use `IVectorStore`, not `ChromaVectorStore`
2. **Inject Dependencies:** Don't create dependencies inside classes
3. **Single Responsibility:** Each interface has one clear purpose
4. **Test Isolation:** Use mocks to test business logic without infrastructure

**Files to Remember:**
- `app/domain/interfaces/` - Data layer contracts
- `app/application/interfaces/` - Service layer contracts
- `app/container.py` - Where everything gets wired together
- `app/infrastructure/` - Concrete implementations

This architecture makes the codebase:
- ✅ **Testable** - Mock any dependency
- ✅ **Flexible** - Swap implementations easily
- ✅ **Maintainable** - Changes are isolated
- ✅ **Professional** - Industry-standard design pattern
