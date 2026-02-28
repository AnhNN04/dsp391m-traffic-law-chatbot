"""
Ask Human Node - NODE 5: Human-in-the-Loop Clarification.

Sinh câu hỏi làm rõ khi thiếu thông tin và trigger interrupt để chờ user response.
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage

from app.domain.state import AgentState
from app.application.interfaces.i_llm_service import ILLMService
from app.application.nodes.base_node import BaseNode
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)

class AskHumanNode(BaseNode):
    """
    Node xử lý Human-in-the-loop interaction.
    
    Khi hệ thống thiếu thông tin quan trọng để trả lời, node này:
    1. Sinh câu hỏi làm rõ tự nhiên
    2. Gửi câu hỏi cho user
    3. Trigger interrupt để graph dừng lại chờ response
    
    Flow:
        Query: "Vượt đèn đỏ phạt bao nhiêu?"
        Grade: missing_info = "loại phương tiện"
        -> Ask Human: "Bạn đang hỏi về xe máy hay ô tô ạ?"
        -> [INTERRUPT - Chờ user trả lời]
        -> User: "Xe máy"
        -> [Resume] Quay lại retrieval với query đầy đủ
    """
    
    CLARIFICATION_PROMPT = """Bạn là trợ lý tư vấn luật giao thông chuyên nghiệp.

Tình huống: Người dùng đã hỏi một câu hỏi nhưng thiếu thông tin quan trọng để trả lời chính xác.

Câu hỏi của người dùng: "{query}"

Thông tin còn thiếu: {missing_info}

Nhiệm vụ: Sinh 1 câu hỏi ngắn gọn, lịch sự để làm rõ thông tin còn thiếu.

Yêu cầu:
1. Câu hỏi phải tự nhiên, thân thiện
2. Đưa ra gợi ý cụ thể nếu có (VD: liệt kê các lựa chọn)
3. Không quá dài dòng (tối đa 2 câu)
4. Dùng ngôn ngữ lịch sự (ạ, em, anh/chị...)

Ví dụ tốt:
- "Bạn đang hỏi về xe máy hay ô tô ạ?"
- "Em có thể cho biết vi phạm xảy ra trong khu vực nội thành hay ngoại thành không ạ?"
- "Anh/chị muốn biết mức phạt cho trường hợp vi phạm lần đầu hay tái phạm?"

Câu hỏi của bạn (chỉ trả về câu hỏi, không giải thích):"""

    def __init__(self, smart_llm: ILLMService):
        """
        Initialize Ask Human Node.
        
        Args:
            smart_llm: LLM thông minh để sinh câu hỏi tự nhiên
        """
        super().__init__(node_name="AskHuman")
        self.llm = smart_llm
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Sinh câu hỏi làm rõ và chuẩn bị interrupt.
        
        Args:
            state: AgentState chứa rewritten_query và grade_result
            
        Returns:
            Dict với clarification_question và messages
        """
        self._log_entry(state)
        
        try:
            # Validate state
            self._validate_state(state, required_keys=["rewritten_query"])
            
            query = state["rewritten_query"]
            grade_result = state.get("grade_result", {})
            missing_info = grade_result.get("missing_info", "thông tin bổ sung")
            
            # Sinh câu hỏi làm rõ
            clarification_question = self._generate_clarification(query, missing_info)
            
            logger.info(
                f"[{self.node_name}] Generated question: '{clarification_question}'"
            )
            
            # Chuẩn bị state update
            result = {
                "clarification_question": clarification_question,
                "messages": [AIMessage(content=clarification_question)]
            }
            
            # Note: Interrupt sẽ được config ở Graph level
            # Node này chỉ cần return câu hỏi
            
            self._log_exit(result)
            logger.info(f"[{self.node_name}] 🛑 Triggering interrupt - Waiting for user response")
            
            return result
            
        except Exception as e:
            self._log_error(e)
            # Fallback: Đặt câu hỏi generic
            fallback_question = (
                "Em cần thêm một số thông tin để tư vấn chính xác. "
                "Anh/chị có thể cung cấp thêm chi tiết về tình huống của mình được không ạ?"
            )
            logger.warning(f"[{self.node_name}] Using fallback question")
            return {
                "clarification_question": fallback_question,
                "messages": [AIMessage(content=fallback_question)]
            }
    
    def _generate_clarification(self, query: str, missing_info: str) -> str:
        """
        Gọi LLM để sinh câu hỏi làm rõ.
        
        Args:
            query: Câu hỏi gốc của user
            missing_info: Thông tin còn thiếu (từ Grade Node)
            
        Returns:
            Câu hỏi làm rõ
        """
        prompt = self.CLARIFICATION_PROMPT.format(
            query=query,
            missing_info=missing_info
        )
        
        try:
            question = self.llm.generate_text(prompt)
            
            # Post-processing
            question = question.strip()
            
            # Loại bỏ quotes nếu có
            if question.startswith('"') and question.endswith('"'):
                question = question[1:-1]
            if question.startswith("'") and question.endswith("'"):
                question = question[1:-1]
            
            # Validate độ dài
            if len(question) < 10:
                logger.warning(f"[{self.node_name}] Generated question too short")
                return self._get_template_question(missing_info)
            
            if len(question) > 300:
                logger.warning(f"[{self.node_name}] Generated question too long, truncating")
                question = question[:297] + "..."
            
            return question
            
        except Exception as e:
            logger.error(f"[{self.node_name}] LLM generation failed: {e}")
            return self._get_template_question(missing_info)
    
    def _get_template_question(self, missing_info: str) -> str:
        """
        Lấy câu hỏi template dựa trên missing_info (fallback).
        
        Args:
            missing_info: Loại thông tin thiếu
            
        Returns:
            Câu hỏi template
        """
        # Map missing_info keywords -> template questions
        missing_lower = missing_info.lower()
        
        if "phương tiện" in missing_lower or "xe" in missing_lower:
            return "Bạn đang hỏi về xe máy, ô tô, hay loại phương tiện khác ạ?"
        
        if "khu vực" in missing_lower or "địa điểm" in missing_lower:
            return "Vi phạm xảy ra ở khu vực nào ạ (nội thành, ngoại thành, đường cao tốc)?"
        
        if "lần" in missing_lower or "tái phạm" in missing_lower:
            return "Đây là vi phạm lần đầu hay đã từng vi phạm trước đó ạ?"
        
        if "thời gian" in missing_lower:
            return "Anh/chị có thể cho biết vi phạm xảy ra khi nào không ạ?"
        
        # Default generic question
        return (
            f"Em cần thêm thông tin về {missing_info} để tư vấn chính xác. "
            "Anh/chị có thể cung cấp thêm chi tiết được không ạ?"
        )
    
    def validate_user_response(self, response: str) -> bool:
        """
        Validate xem user response có hợp lệ không (optional helper).
        
        Args:
            response: Response từ user sau interrupt
            
        Returns:
            True nếu valid
        """
        # Basic validation
        if not response or len(response.strip()) < 2:
            return False
        
        # Check không phải spam
        if len(response) > 500:
            return False
        
        return True
