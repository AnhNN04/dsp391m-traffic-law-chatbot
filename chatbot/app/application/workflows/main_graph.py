"""
Main Graph Definition

Nơi lắp ráp các Node thành một đồ thị hoàn chỉnh (StateGraph).
Định nghĩa luồng đi (Edges), điểm rẽ nhánh (Conditional Edges) và Checkpoint.

Author: AnhNN217-FHN
"""

from typing import Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.checkpoint.memory import MemorySaver

# Import Container và State
from app.container import container
from app.domain.state import AgentState
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)

# 2. Define Conditional Logic (Hàm điều hướng)
def route_guardrails(state: AgentState) -> Literal["rewrite", "end_unsafe"]:
    """Điều hướng sau khi check an toàn."""
    # GuardrailsNode trả về is_blocked=True khi từ chối
    if state.get("is_blocked", False):
        return "end_unsafe"
    return "rewrite"

def route_router(state: AgentState) -> Literal["retrieval", "generate"]:
    """Điều hướng sau khi phân loại ý định."""
    intent = state.get("intent", "chitchat")
    if intent in ["legal", "procedure"]:
        return "retrieval"
    return "generate"

def route_grade(state: AgentState) -> Literal["generate", "ask_human"]:
    """Điều hướng sau khi đánh giá tài liệu."""
    return state.get("next_action", "generate")

# 3. Build Graph
def build_traffic_law_graph():
    """
    Xây dựng StateGraph cho Traffic Law Agent.
    """
    workflow = StateGraph(AgentState)

    # --- ADD NODES ---
    # Lấy Node instances từ Container
    workflow.add_node("guardrails", container.guardrails_node)
    workflow.add_node("rewrite", container.rewrite_node)
    workflow.add_node("router", container.router_node)
    workflow.add_node("retrieval", container.retrieval_node)
    workflow.add_node("grade", container.grade_node)
    # Bỏ qua web_search node
    # workflow.add_node("web_search", container.web_search_node)
    workflow.add_node("generate", container.generate_node)
    workflow.add_node("ask_human", container.ask_human_node)

    # --- DEFINE EDGES ---
    
    # 1. Start -> Guardrails
    workflow.add_edge(START, "guardrails")

    # 2. Guardrails -> Rewrite (Safe) OR End (Unsafe)
    workflow.add_conditional_edges(
        "guardrails",
        route_guardrails,
        {
            "rewrite": "rewrite",
            "end_unsafe": END 
        }
    )

    # 3. Rewrite -> Router
    workflow.add_edge("rewrite", "router")

    # 4. Router -> Retrieval (Legal) OR Generate (Chitchat)
    workflow.add_conditional_edges(
        "router",
        route_router,
        {
            "retrieval": "retrieval",
            "generate": "generate",   # Chitchat đi thẳng vào Generate để sinh response
        }
    )

    # 5. Retrieval -> Grade
    workflow.add_edge("retrieval", "grade")

    # 6. Grade -> Generate / Ask Human
    workflow.add_conditional_edges(
        "grade",
        route_grade,
        {
            "generate": "generate",
            "ask_human": "ask_human"
        }
    )

    # 7. (Đã xóa Web Search -> Generate)
    
    # 8. Generate -> End
    workflow.add_edge("generate", END)

    # 9. Ask Human -> Router (Loop back after interruption)
    # Sau khi user trả lời câu hỏi làm rõ, luồng sẽ quay lại Router 
    # để phân tích lại ý định với thông tin mới.
    workflow.add_edge("ask_human", "router")

    # --- SETUP CHECKPOINTER ---
    # MongoHistory là class lưu chat logs, KHÔNG phải LangGraph checkpointer.
    # MemorySaver đủ dùng cho dev (state trong RAM, mất khi restart).
    # Để dùng MongoDB persistence: cần langgraph-checkpoint-mongodb riêng.
    checkpointer = MemorySaver()
    logger.info("✅ Graph Checkpointer: MemorySaver (in-memory)")

    # --- COMPILE ---
    # interrupt_after=["ask_human"]: Dừng graph sau khi node 'ask_human' chạy xong
    # để chờ user input.
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=["ask_human"]
    )

    return app

# Export Runnable App
traffic_app = build_traffic_law_graph()
