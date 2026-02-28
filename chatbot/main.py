
"""
CLI Entry Point

Giao diện dòng lệnh để chạy Traffic Law Agent.
Hỗ trợ:
- Streaming Output (Hiển thị từng bước xử lý của Graph).
- Persistence (Lưu lịch sử chat qua thread_id).
- Human-in-the-loop (Xử lý Interrupt khi Bot hỏi lại).

Usage: python main.py
"""

import uuid
import sys
from typing import Dict, Any

from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage

from app.application.workflows.main_graph import traffic_app
from app.infrastructure.config.logger import get_logger

app_logger = get_logger("main")

def print_step(step_output: Dict[str, Any]):
    """In ra thông tin node đang chạy."""
    for node_name, state_update in step_output.items():
        print(f"\n🔄 [NODE: {node_name.upper()}] processed.")
        
        # Nếu là node tạo ra tin nhắn trả lời (Generate), in ra
        if "messages" in state_update and state_update["messages"]:
            last_msg = state_update["messages"][-1]
            if isinstance(last_msg, AIMessage):
                print(f"🤖 BOT: {last_msg.content}")

def run_cli():
    # 1. Tạo Session ID (Thread ID)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"🚀 Traffic Law Bot started! (Session: {thread_id})")
    print("Gõ 'quit' hoặc 'exit' để thoát.\n")

    while True:
        # 2. Kiểm tra trạng thái hiện tại của Graph
        # Để xem có đang bị Interrupt (dừng chờ user) không
        snapshot = traffic_app.get_state(config)
        
        user_input = ""
        
        # --- TRƯỜNG HỢP 1: GRAPH ĐANG BỊ NGẮT (INTERRUPTED) ---
        if snapshot.next:
            # Nếu next step tồn tại dù stream đã kết thúc -> Đang chờ resume
            # Kiểm tra xem có phải dừng sau node 'ask_human' không
            last_state = snapshot.values
            clarification_q = last_state.get("clarification_question")
            
            if clarification_q:
                print(f"❓ BOT (Cần làm rõ): {clarification_q}")
                
            # Nhận input trả lời câu hỏi làm rõ
            user_input = input("👤 USER (Trả lời): ")
            if user_input.lower() in ["quit", "exit"]:
                break
                
            # Resume Graph bằng Command
            # Truyền user_input vào messages để cập nhật lịch sử và resume luồng đi tiếp
            command = Command(
                resume=HumanMessage(content=user_input)
            )
            
            print("... Đang tiếp tục xử lý ...")
            try:
                # Gọi stream với Command để resume
                for event in traffic_app.stream(command, config=config):
                    print_step(event)
            except Exception as e:
                app_logger.error(f"Error executing graph: {e}")
                
        # --- TRƯỜNG HỢP 2: HỘI THOẠI MỚI ---
        else:
            user_input = input("👤 USER: ")
            if user_input.lower() in ["quit", "exit"]:
                break
            
            # Input Message
            inputs = {"messages": [HumanMessage(content=user_input)]}
            
            try:
                # Chạy Graph từ đầu
                for event in traffic_app.stream(inputs, config=config):
                    print_step(event)
            except Exception as e:
                app_logger.error(f"Error executing graph: {e}")

if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
