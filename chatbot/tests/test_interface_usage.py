"""
Interface Usage Example

This shows how the abstract interfaces will be used in nodes.
The actual implementations will be created in the Infrastructure layer.
"""

from typing import List
from pydantic import BaseModel

from app.application.interfaces import ILLMService

from app.domain.interfaces import IVectorStore, IGraphStore
from app.domain.entities import LegalDocument
from app.domain.state import AgentState


# ==================== Example Node Using Interfaces ====================

class RetrievalNode:
    """
    Example node that uses dependency injection with interfaces.
    
    This node depends on abstractions (IVectorStore, IGraphStore),
    not concrete implementations. This makes it:
    - Testable (can inject mocks)
    - Flexible (can swap implementations)
    - Decoupled (no infrastructure dependencies)
    """
    
    def __init__(
        self,
        vector_store: IVectorStore,
        graph_store: IGraphStore
    ):
        """
        Initialize with injected dependencies.
        
        Args:
            vector_store: Any implementation of IVectorStore (ChromaDB, Pinecone, etc.)
            graph_store: Any implementation of IGraphStore (Neo4j, Neptune, etc.)
        """
        self.vector_store = vector_store
        self.graph_store = graph_store
    
    def __call__(self, state: AgentState) -> dict:
        """
        Execute retrieval using both vector and graph stores.
        
        Args:
            state: Current agent state
        
        Returns:
            Updated state with retrieved documents
        """
        query = state["rewritten_query"]
        
        # Use the abstract interfaces - we don't care about the implementation
        vector_docs = self.vector_store.search(query, k=5)
        graph_docs = self.graph_store.get_penalty_info(query)
        
        # Combine results (graph has higher priority)
        all_docs = graph_docs + vector_docs
        
        return {"documents": all_docs}


class RewriteNode:
    """Example node using LLM service interface."""
    
    def __init__(self, llm_service: ILLMService):
        """
        Initialize with injected LLM service.
        
        Args:
            llm_service: Any implementation of ILLMService (OpenAI, Groq, etc.)
        """
        self.llm = llm_service
    
    def __call__(self, state: AgentState) -> dict:
        """
        Rewrite the user query with full context.
        
        Args:
            state: Current agent state
        
        Returns:
            Updated state with rewritten query
        """
        # Build prompt from conversation history
        history = state["messages"][-3:]  # Last 3 messages
        prompt = f"Rewrite this query with context: {history}"
        
        # Use the abstract interface
        rewritten = self.llm.generate(prompt)
        
        return {"rewritten_query": rewritten}


class RouterNode:
    """Example node using structured output."""
    
    def __init__(self, llm_service: ILLMService):
        """
        Initialize with injected LLM service.
        
        Args:
            llm_service: Any implementation of ILLMService
        """
        self.llm = llm_service
    
    def __call__(self, state: AgentState) -> dict:
        """
        Classify user intent using structured output.
        
        Args:
            state: Current agent state
        
        Returns:
            Updated state with classified intent
        """
        
        # Define the structure we want from the LLM
        class IntentClassification(BaseModel):
            intent: str  # "legal", "procedure", or "chitchat"
            confidence: float
        
        query = state["rewritten_query"]
        prompt = f"Classify the intent of this query: {query}"
        
        # Use structured output
        result = self.llm.generate_structured(prompt, schema=IntentClassification)
        
        return {"intent": result.intent}


# ==================== How It All Wires Together ====================

def example_dependency_injection():
    """
    Example showing how dependencies are injected.
    
    This will be done in the Container class.
    """
    
    # In real code, these would be actual implementations:
    # from app.infrastructure.persistence.chroma_repo import ChromaVectorStore
    # from app.infrastructure.persistence.neo4j_repo import Neo4jGraphStore
    # from app.infrastructure.external_services.openai_service import OpenAIService
    
    # For now, we just show the pattern:
    
    # Step 1: Create concrete implementations (Infrastructure layer)
    # vector_store = ChromaVectorStore(persist_dir="./data/chroma")
    # graph_store = Neo4jGraphStore(uri="bolt://localhost:7687", auth=("neo4j", "password"))
    # smart_llm = OpenAIService(api_key="sk-...", model="gpt-4o-mini")
    
    # Step 2: Inject them into nodes (Application layer)
    # retrieval_node = RetrievalNode(
    #     vector_store=vector_store,
    #     graph_store=graph_store
    # )
    # 
    # rewrite_node = RewriteNode(llm_service=smart_llm)
    # router_node = RouterNode(llm_service=smart_llm)
    
    # Step 3: Build graph with nodes
    # graph = StateGraph(AgentState)
    # graph.add_node("rewrite", rewrite_node)
    # graph.add_node("retrieval", retrieval_node)
    # graph.add_node("router", router_node)
    
    pass


# ==================== Testing Example ====================

class MockVectorStore(IVectorStore):
    """Mock implementation for testing."""
    
    def search(self, query: str, k: int = 5) -> List[LegalDocument]:
        """Return fake documents for testing."""
        from app.domain.entities import DocumentSource
        
        return [
            LegalDocument(
                content=f"Mock document for query: {query}",
                source=DocumentSource.DATABASE,
                score=0.95
            )
        ]


def test_retrieval_node():
    """Example test using mock implementations."""
    
    # Create mock dependencies
    mock_vector = MockVectorStore()
    mock_graph = MockVectorStore()  # Reuse for simplicity
    
    # Inject mocks into node
    node = RetrievalNode(vector_store=mock_vector, graph_store=mock_graph)
    
    # Create test state
    from app.domain.state import create_initial_state
    state = create_initial_state(session_id="test_123")
    state["rewritten_query"] = "test query"
    
    # Execute node
    result = node(state)
    
    # Assert results
    assert len(result["documents"]) > 0
    assert "Mock document" in result["documents"][0].content
    
    print("✅ Test passed! Interface pattern working correctly.")


if __name__ == "__main__":
    print("=" * 60)
    print("Interface Usage Examples")
    print("=" * 60)
    print("\n1. Nodes use abstract interfaces, not concrete implementations")
    print("2. Dependencies are injected via constructor")
    print("3. Easy to test with mock implementations")
    print("4. Easy to swap implementations (ChromaDB -> Pinecone)")
    print("\n" + "=" * 60)
    
    test_retrieval_node()
