"""
Rewrite Node - NODE 1: Query Transformation.

Biến đổi câu hỏi phụ thuộc ngữ cảnh thành câu hỏi độc lập dựa trên lịch sử chat.
"""

from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.domain.state import AgentState
from app.application.interfaces.i_llm_service import ILLMService
from app.application.nodes.base_node import BaseNode
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)

class RewriteNode(BaseNode):
    """
    Node viết lại câu hỏi dựa trên lịch sử hội thoại.
    
    Mục đích: Khắc phục vấn đề của RAG khi user sử dụng đại từ
    nhân xưng hoặc tham chiếu ngữ cảnh trước đó.
    
    Ví dụ:
        User: "Vượt đèn đỏ phạt bao nhiêu?"
        Bot: "Từ 4-6 triệu đồng..."
        User: "Còn xe máy thì sao?" 
        -> Rewrite: "Mức phạt vượt đèn đỏ đối với xe máy là bao nhiêu?"
    """
    
    # Prompt template
    REWRITE_PROMPT = """Bạn là chuyên gia xử lý ngôn ngữ tự nhiên.

Nhiệm vụ: Viết lại câu hỏi cuối cùng của người dùng sao cho nó độc lập, đầy đủ ý nghĩa mà không cần đọc lịch sử chat.

Lịch sử hội thoại gần đây:
{chat_history}

Câu hỏi hiện tại: "{current_query}"

Quy tắc:
1. KHÔNG trả lời câu hỏi, CHỈ viết lại
2. Thay thế các đại từ (nó, cái đó, lỗi trên, còn...) bằng từ cụ thể
3. Bổ sung chủ ngữ/vị ngữ nếu thiếu
4. Giữ nguyên ý định của câu hỏi gốc
5. Nếu câu hỏi đã rõ ràng, giữ nguyên

Câu hỏi đã viết lại (chỉ trả về câu hỏi, không giải thích):"""

    def __init__(self, smart_llm: ILLMService):
        """
        Initialize Rewrite Node.
        
        Args:
            smart_llm: LLM thông minh (GPT-4o-mini) để hiểu ngữ cảnh tốt
        """
        super().__init__(node_name="Rewrite")
        self.llm = smart_llm
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Viết lại câu hỏi của user.
        
        Args:
            state: AgentState chứa messages
            
        Returns:
            Dict với rewritten_query
        """
        self._log_entry(state)
        
        try:
            # Validate state
            self._validate_state(state, required_keys=["messages"])
            
            messages = state["messages"]
            if not messages:
                logger.warning(f"[{self.node_name}] No messages to rewrite")
                return {"rewritten_query": ""}
            
            # Lấy câu hỏi hiện tại
            current_query = self._extract_current_query(messages)
            
            # Nếu đây là câu hỏi đầu tiên (không có lịch sử)
            if len(messages) <= 1:
                logger.info(f"[{self.node_name}] First message, no rewrite needed")
                result = {"rewritten_query": current_query}
                self._log_exit(result)
                return result
            
            # Lấy lịch sử chat (tối đa 3 cặp hội thoại gần nhất)
            chat_history = self._format_chat_history(messages)
            
            # Gọi LLM để rewrite
            rewritten = self._rewrite_query(current_query, chat_history)
            
            logger.info(
                f"[{self.node_name}] Original: '{current_query}' | "
                f"Rewritten: '{rewritten}'"
            )
            
            result = {"rewritten_query": rewritten}
            self._log_exit(result)
            return result
            
        except Exception as e:
            self._log_error(e)
            # Fallback: Trả về câu hỏi gốc nếu rewrite fail
            fallback_query = self._extract_current_query(state.get("messages", []))
            logger.warning(f"[{self.node_name}] Using original query as fallback")
            return {"rewritten_query": fallback_query}
    
    def _extract_current_query(self, messages: List[BaseMessage]) -> str:
        """
        Trích xuất câu hỏi hiện tại từ messages.
        
        Args:
            messages: Danh sách messages
            
        Returns:
            Nội dung câu hỏi cuối cùng của user
        """
        if not messages:
            return ""
        
        # Lấy message cuối cùng
        last_message = messages[-1]
        return last_message.content.strip()
    
    def _format_chat_history(
        self, 
        messages: List[BaseMessage], 
        max_pairs: int = 3
    ) -> str:
        """
        Format lịch sử chat thành string để đưa vào prompt.
        
        Args:
            messages: Danh sách messages (bao gồm cả current)
            max_pairs: Số cặp hội thoại tối đa (default 3)
            
        Returns:
            String formatted history
        """
        # Loại bỏ message cuối cùng (vì đó là current query)
        history_messages = messages[:-1]
        
        # Lấy N cặp gần nhất (1 cặp = 1 user + 1 assistant)
        # Lùi từ cuối lên để lấy các message gần nhất
        recent_messages = history_messages[-(max_pairs * 2):]
        
        # Format thành string
        formatted_lines = []
        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                formatted_lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                # Cắt ngắn response của bot để tiết kiệm token
                content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                formatted_lines.append(f"Assistant: {content}")
        
        return "\n".join(formatted_lines) if formatted_lines else "Không có lịch sử"
    
    def _rewrite_query(self, current_query: str, chat_history: str) -> str:
        """
        Gọi LLM để rewrite query.
        
        Args:
            current_query: Câu hỏi hiện tại
            chat_history: Lịch sử đã format
            
        Returns:
            Câu hỏi đã được viết lại
        """
        prompt = self.REWRITE_PROMPT.format(
            current_query=current_query,
            chat_history=chat_history
        )
        
        try:
            rewritten = self.llm.generate_text(prompt)
            
            # Post-processing: Loại bỏ các ký tự thừa
            rewritten = rewritten.strip()
            
            # Loại bỏ quotes nếu LLM wrap output trong quotes
            if rewritten.startswith('"') and rewritten.endswith('"'):
                rewritten = rewritten[1:-1]
            if rewritten.startswith("'") and rewritten.endswith("'"):
                rewritten = rewritten[1:-1]
            
            # Nếu LLM trả về quá ngắn hoặc lỗi, dùng original
            if len(rewritten) < 5:
                logger.warning(f"[{self.node_name}] Rewritten too short, using original")
                return current_query
            
            return rewritten
            
        except Exception as e:
            logger.error(f"[{self.node_name}] LLM call failed: {e}")
            return current_query
