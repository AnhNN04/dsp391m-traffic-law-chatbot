"""
Streamlit Web User Interface for Traffic Law Chatbot

This script provides a web-based chat interface using Streamlit,
integrating with the existing LangGraph workflow defined in app.container.

Run with:
    streamlit run app_ui.py
"""

import streamlit as st
import time
from typing import List, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.container import container
from app.domain.state import create_initial_state

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Việt Nam Traffic Law Chatbot",
    page_icon="🚦",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stChatFloatingInputContainer {
        padding-bottom: 20px;
    }
    .main-header {
        text-align: center;
        margin-bottom: 30px;
    }
    .badge {
        display: inline-block;
        padding: 4px 8px;
        margin: 0 4px;
        border-radius: 4px;
        background-color: #f0f2f6;
        font-size: 0.8rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Flag_of_Vietnam.svg/2000px-Flag_of_Vietnam.svg.png", width=100)
    st.title("Traffic Law Assistant")
    st.markdown("""
    Trợ lý ảo hỗ trợ giải đáp pháp luật giao thông đường bộ Việt Nam.
    
    *Hỗ trợ:*
    - Tra cứu quy định, thủ tục
    - Hỏi đáp mức xử phạt
    - Thông tin chung về giao thông
    
    *Powered by Phí Đình Huy*
    """)
    
    st.divider()
    
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = f"st_session_{int(time.time())}"
        st.session_state.pending_human_response = False
        st.session_state.current_state = None
        st.rerun()

# --- INITIALIZATION ---
def init_session_state():
    """Khởi tạo state cho Streamlit."""
    if "messages" not in st.session_state:
        # Initial greeting message
        st.session_state.messages = [
            AIMessage(content="Xin chào! Tôi là trợ lý pháp luật giao thông. Tôi có thể giúp gì cho bạn hôm nay?")
        ]
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"st_session_{int(time.time())}"
    if "pending_human_response" not in st.session_state:
        st.session_state.pending_human_response = False
    if "clarification_question" not in st.session_state:
        st.session_state.clarification_question = None

init_session_state()

# --- MAIN UI ---
st.markdown("<h1 class='main-header'>🚦 TƯ VẤN LUẬT GIAO THÔNG</h1>", unsafe_allow_html=True)

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(msg.content)

# --- CHAT INPUT & PROCESSING ---

# Nếu hệ thống ĐANG CHỜ câu trả lời làm rõ từ user (interrupt state)
if st.session_state.pending_human_response:
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(f"**Vui lòng làm rõ:** {st.session_state.clarification_question}")
        
    answer = st.text_input("Câu trả lời của bạn...", key="clarification_input")
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Gửi trả lời", type="primary", use_container_width=True):
            if answer:
                # 1. Thêm câu trả lời vào UI
                human_msg = HumanMessage(content=answer)
                st.session_state.messages.append(human_msg)
                
                # 2. Xóa trạng thái chờ
                st.session_state.pending_human_response = False
                st.session_state.clarification_question = None
                
                # 3. Tiếp tục Graph từ điểm dừng
                with st.spinner("Đang xử lý tiếp..."):
                    # Update thread state with the new message
                    config = {"configurable": {"thread_id": st.session_state.session_id}}
                    
                    try:
                        # Continue graph execution
                        # Cập nhật state bằng update_state và resume
                        container.graph.update_state(config, {"messages": [human_msg]})
                        
                        final_state = None
                        for s in container.graph.stream(None, config=config, stream_mode="values"):
                            final_state = s
                        
                        # 4. Kiểm tra có tiếp tục bị interrupt không
                        if final_state and final_state.get("clarification_question"):
                            st.session_state.pending_human_response = True
                            st.session_state.clarification_question = final_state["clarification_question"]
                        else:
                            # 5. Thông thường đã xong dứt điểm
                            if final_state and "messages" in final_state:
                                latest_ai_msg = final_state["messages"][-1]
                                if isinstance(latest_ai_msg, AIMessage):
                                    st.session_state.messages.append(latest_ai_msg)
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Có lỗi xảy ra khi xử lý: {str(e)}")
                        st.session_state.pending_human_response = False

# Xử lý nhập liệu binh thường
else:
    if query := st.chat_input("Nhập câu hỏi pháp lý giao thông của bạn (Ví dụ: Vượt đèn đỏ phạt bao nhiêu?)..."):
        # Add user message to UI
        human_msg = HumanMessage(content=query)
        st.session_state.messages.append(human_msg)
        
        # Display instantly
        with st.chat_message("user", avatar="👤"):
            st.markdown(query)
            
        # Call LangGraph
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Đang tra cứu dữ liệu..."):
                config = {"configurable": {"thread_id": st.session_state.session_id}}
                initial_state = create_initial_state(
                    session_id=st.session_state.session_id,
                    initial_messages=st.session_state.messages
                )
                
                try:
                    # Stream state updates
                    final_state = None
                    last_ui_update_time = time.time()
                    
                    for event in container.graph.stream(initial_state, config=config, stream_mode="values"):
                        final_state = event
                        
                    # Handle Human-in-the-loop interruption
                    if final_state and final_state.get("clarification_question"):
                        st.session_state.pending_human_response = True
                        st.session_state.clarification_question = final_state["clarification_question"]
                        st.rerun() # Refresh immediately to show the input box
                        
                    # Handle Normal Completion
                    elif final_state and "messages" in final_state:
                        # So sánh list messages: LangGraph trả về list có message mới ở cuối
                        latest_msg = final_state["messages"][-1]
                        
                        if isinstance(latest_msg, AIMessage):
                            st.markdown(latest_msg.content)
                            
                            # Hiển thị metadata badge
                            if final_state.get("data_source"):
                                st.markdown(f"""
                                <div style="margin-top: 10px; color: gray;">
                                    <span class="badge">Nguồn: database</span>
                                    <span class="badge">Intent: {final_state.get('intent', 'unknown')}</span>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            st.session_state.messages.append(latest_msg)
                        elif getattr(final_state, "is_blocked", False) or final_state.get("is_blocked"):
                             # Xử lý trường hợp bị Guardrails chặn nhưng graph không sinh message mới
                             msg = AIMessage(content="Xin lỗi, tôi không thể trả lời câu hỏi này. Nội dung không an toàn hoặc nằm ngoài phạm vi hỗ trợ.")
                             st.markdown(msg.content)
                             st.session_state.messages.append(msg)
                             
                except Exception as e:
                    st.error(f"Có lỗi hệ thống xảy ra: {str(e)}")
