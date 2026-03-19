"""
Domain State

Defines the state structure for the LangGraph agent.
This is the "memory" that flows through all nodes in the graph.

Author: AnhNN217-FHN
"""

from typing import TypedDict, Annotated, List, Optional, Literal, Any
from langgraph.graph.message import add_messages

from app.domain.entities import LegalDocument


class AgentState(TypedDict):
    """
    The state structure for the Traffic Law Agent graph.
    
    This state flows through all nodes in the LangGraph workflow.
    Each node can read from and write to specific fields.
    
    Attributes:
        messages: Conversation history (automatically appends new messages)
        rewritten_query: Query rewritten with full context for retrieval
        intent: Classified intent of the user query
        documents: Retrieved legal documents from knowledge base
        data_source: Source of the final answer (database/internet/knowledge)
        clarification_question: Question to ask user for clarification (triggers interrupt)
        session_id: Unique session identifier for this conversation
        user_id: User identifier (optional)
        metadata: Additional context and debugging information
    
    Note:
        The `messages` field uses `add_messages` reducer which automatically
        appends new messages instead of replacing the list. This is crucial
        for maintaining conversation history.
    
    """
    
    # ==================== Conversation Context ====================
    
    # List of messages in the conversation
    # Uses add_messages reducer to automatically append new messages
    # rather than replacing the entire list
    messages: Annotated[List[Any], add_messages]
    
    # ==================== Query Processing ====================
    
    # Rewritten query with full context (resolved pronouns, added details)
    # Example: "Nó phạt bao nhiêu?" -> "Lỗi vượt đèn đỏ với xe máy phạt bao nhiêu?"
    rewritten_query: str
    
    # Classified intent: what the user is trying to do
    # - "legal": Asking about traffic laws, penalties, violations
    # - "procedure": Asking about administrative procedures
    # - "chitchat": General conversation, greetings
    intent: Literal["legal", "procedure", "chitchat"]
    
    # ==================== Retrieval Context ====================
    
    # List of legal documents retrieved from knowledge base
    # Can come from vector store, graph store, or web search
    documents: List[LegalDocument]
    
    # Source of information used for "Final Answer"
    # - "database": From vector/graph store
    # - "internet": From web search
    # - "general_knowledge": From LLM's training data
    # - "unknown": Not yet determined
    data_source: Literal["database", "internet", "general_knowledge", "unknown"]
    
    # ==================== Human-in-the-Loop ====================
    
    # Question to ask user for clarification
    # When this is set, the graph will interrupt and wait for user input
    # Example: "Bạn đang hỏi về xe máy hay ô tô?"
    clarification_question: Optional[str]
    
    # ==================== Session Management ====================
    
    # Unique identifier for this conversation session
    # Used by MongoDB checkpointer to save/load state
    session_id: str
    
    # Optional user identifier for personalization
    user_id: Optional[str]
    
    # ==================== Metadata & Debugging ====================
    
    # Additional context for debugging and logging
    # Can store: retrieval scores, processing times, error messages, etc.
    metadata: dict

    # Routing action determined by Grade Node
    next_action: Optional[Literal["generate", "web_search", "ask_human"]]
    
    # Grade Evaluation result
    grade_result: Optional[dict]

class PartialAgentState(TypedDict, total=False):
    """
    Partial state for node updates.
    
    Nodes don't need to update all fields in the state.
    This type allows nodes to return only the fields they want to update.
    
    The `total=False` parameter makes all fields optional, allowing
    nodes to update any subset of the state.
    
    """
    
    messages: Annotated[List[Any], add_messages]
    rewritten_query: str
    intent: Literal["legal", "procedure", "chitchat"]
    documents: List[LegalDocument]
    data_source: Literal["database", "internet", "general_knowledge", "unknown"]
    clarification_question: Optional[str]
    session_id: str
    user_id: Optional[str]
    metadata: dict
    next_action: Optional[Literal["generate", "web_search", "ask_human"]]
    grade_result: Optional[dict]


# Khởi tạo một trạng thái ban đầu AgentState cho một phiên hội thoại mới.
def create_initial_state(
    session_id: str,
    user_id: Optional[str] = None,
    initial_messages: Optional[List[Any]] = None
) -> AgentState:
    """
    Create a fresh AgentState for a new conversation.
    
    Args:
        session_id: Unique session identifier
        user_id: Optional user identifier
        initial_messages: Optional list of initial messages
    
    Returns:
        Initialized AgentState
    
    """
    return AgentState(
        messages=initial_messages or [],
        rewritten_query="",
        intent="legal",
        documents=[],
        data_source="unknown",
        clarification_question=None,
        session_id=session_id,
        user_id=user_id,
        metadata={},
        next_action=None,
        grade_result=None
    )

# Lấy nội dung tin nhắn cuối cùng của người dùng từ lịch sử hội thoại.
def get_last_user_message(state: AgentState) -> Optional[str]:
    """
    Extract the content of the last user message.
    
    Args:
        state: Current agent state
    
    Returns:
        Content of the last user message, or None if no messages
    
    """
    if not state["messages"]:
        return None
    
    # Iterate backwards to find the last human message
    for message in reversed(state["messages"]):
        if hasattr(message, "type") and message.type == "human":
            return message.content
        elif isinstance(message, dict) and message.get("type") == "human":
            return message.get("content")
    
    return None

# Lấy lịch sử hội thoại gần nhất (giới hạn số lượng tin nhắn bởi tham số max_messages).
def get_conversation_history(
    state: AgentState,
    max_messages: int = 10
) -> List[Any]:
    """
    Get recent conversation history.
    
    Args:
        state: Current agent state
        max_messages: Maximum number of messages to return (default: 10)
    
    Returns:
        List of recent messages

    """
    return state["messages"][-max_messages:] if state["messages"] else []

# Cập nhật một trường metadata cụ thể trong trạng thái, giữ nguyên các trường khác.
def update_metadata(
    state: AgentState,
    key: str,
    value: Any
) -> PartialAgentState:
    """
    Helper to update a single metadata field.
    
    Args:
        state: Current agent state
        key: Metadata key to update
        value: New value
    
    Returns:
        Partial state with updated metadata
    
    """
    updated_metadata = state.get("metadata", {}).copy()
    updated_metadata[key] = value
    return PartialAgentState(metadata=updated_metadata)

# Kiểm tra xem trạng thái hiện tại có đủ ngữ cảnh để trả lời câu hỏi hay không.
def has_sufficient_context(state: AgentState) -> bool:
    """
    Check if the state has enough context to answer the query.
    
    Args:
        state: Current agent state
    
    Returns:
        True if there are retrieved documents with good scores
    
    """
    if not state.get("documents"):
        return False
    
    # Check if at least one document is relevant (score > 0.7)
    relevant_docs = [
        doc for doc in state["documents"]
        if doc.is_relevant(threshold=0.7)
    ]
    
    return len(relevant_docs) > 0

# Kiểm tra xem có cần ngắt workflow để yêu cuầ người dùng làm rõ không.
def should_interrupt(state: AgentState) -> bool:
    """
    Check if the graph should interrupt to ask user for clarification.
    
    Args:
        state: Current agent state
    
    Returns:
        True if clarification_question is set

    """
    return state.get("clarification_question") is not None


# Type aliases for common types
StateUpdate = PartialAgentState
MessageList = Annotated[List[Any], add_messages]
