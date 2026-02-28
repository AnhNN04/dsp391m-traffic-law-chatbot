"""
Router Node - NODE 2: Intent Classification.

Phân loại ý định của câu hỏi để điều hướng luồng xử lý phù hợp.
"""

from typing import Dict, Any, Literal
from pydantic import BaseModel, Field

from app.domain.state import AgentState
from app.application.interfaces.i_llm_service import ILLMService
from app.application.nodes.base_node import BaseNode
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)

class IntentClassification(BaseModel):
    """Schema cho kết quả phân loại intent."""
    intent: Literal["legal", "procedure", "chitchat"] = Field(
        description="Loại intent: legal (tra cứu luật), procedure (thủ tục), chitchat (xã giao)"
    )
    confidence: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Độ tin cậy của phân loại (0-1)"
    )
    reasoning: str = Field(
        description="Giải thích ngắn gọn lý do phân loại"
    )


class RouterNode(BaseNode):
    """
    Node phân loại ý định câu hỏi.
    
    Mục đích: Tách luồng xử lý để tối ưu:
    - Legal: Cần tra cứu database về văn bản luật, mức phạt
    - Procedure: Thủ tục hành chính (đăng ký xe, xử lý phạt nguội...)
    - Chitchat: Chào hỏi, cảm ơn -> Không cần retrieval
    
    Ví dụ:
        "Vượt đèn đỏ phạt bao nhiêu?" -> legal
        "Làm thế nào để đăng ký xe mới?" -> procedure
        "Xin chào!" -> chitchat
    """
    
    ROUTER_PROMPT = """Bạn là chuyên gia phân loại ý định câu hỏi về luật giao thông.

Câu hỏi: "{query}"

Hãy phân loại câu hỏi này vào 1 trong 3 loại:

1. **legal**: Câu hỏi về nội dung luật, quy định, mức phạt, điều khoản pháp lý
   - VD: "Vượt đèn đỏ phạt bao nhiêu?", "Nồng độ cồn cho phép là bao nhiêu?", "Điều 5 quy định gì?"

2. **procedure**: Câu hỏi về thủ tục, quy trình hành chính
   - VD: "Làm thế nào để đăng ký xe?", "Đóng phạt nguội ở đâu?", "Giấy tờ cần thiết để thi bằng lái?"

3. **chitchat**: Chào hỏi, cảm ơn, tán gẫu, hoặc câu hỏi không liên quan luật
   - VD: "Xin chào", "Cảm ơn bạn", "Bạn tên gì?", "Thời tiết hôm nay thế nào?"

LƯU Ý:
- Nếu câu hỏi mơ hồ hoặc quá chung chung -> phân loại vào chitchat
- Nếu câu hỏi kết hợp nhiều ý -> ưu tiên legal hoặc procedure

Trả về JSON với format sau:
{{
    "intent": "legal" hoặc "procedure" hoặc "chitchat",
    "confidence": 0.95,
    "reasoning": "Câu hỏi về mức phạt vi phạm, thuộc nội dung luật"
}}
"""

    def __init__(self, smart_llm: ILLMService):
        """
        Initialize Router Node.
        
        Args:
            smart_llm: LLM thông minh (GPT-4o-mini) cho classification chính xác
        """
        super().__init__(node_name="Router")
        self.llm = smart_llm
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Phân loại intent của câu hỏi.
        
        Args:
            state: AgentState chứa rewritten_query
            
        Returns:
            Dict với intent field
        """
        self._log_entry(state)
        
        try:
            # Validate state
            self._validate_state(state, required_keys=["rewritten_query"])
            
            query = state["rewritten_query"]
            
            # Nếu query rỗng -> default chitchat
            if not query or len(query.strip()) < 2:
                logger.warning(f"[{self.node_name}] Empty query, defaulting to chitchat")
                return {"intent": "chitchat"}
            
            # Classify intent
            classification = self._classify_intent(query)
            
            logger.info(
                f"[{self.node_name}] Query: '{query[:50]}...' | "
                f"Intent: {classification.intent} | "
                f"Confidence: {classification.confidence:.2f} | "
                f"Reasoning: {classification.reasoning}"
            )
            
            result = {"intent": classification.intent}
            self._log_exit(result)
            return result
            
        except Exception as e:
            self._log_error(e)
            # Fallback: Default về chitchat để tránh crash
            logger.warning(f"[{self.node_name}] Classification failed, defaulting to chitchat")
            return {"intent": "chitchat"}
    
    def _classify_intent(self, query: str) -> IntentClassification:
        """
        Gọi LLM để phân loại intent.
        
        Args:
            query: Câu hỏi cần phân loại
            
        Returns:
            IntentClassification object
        """
        prompt = self.ROUTER_PROMPT.format(query=query)
        
        try:
            # Sử dụng structured output
            result = self.llm.generate_structured(
                prompt=prompt,
                schema=IntentClassification
            )
            
            # Validate confidence
            if result.confidence < 0.3:
                logger.warning(
                    f"[{self.node_name}] Low confidence ({result.confidence}), "
                    f"consider as chitchat"
                )
                # Nếu confidence quá thấp, chuyển sang chitchat an toàn
                if result.intent in ["legal", "procedure"]:
                    result.intent = "chitchat"
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.node_name}] Structured output failed: {e}")
            
            # Fallback: Parse từ text response
            try:
                response_text = self.llm.generate_text(prompt)
                return self._parse_intent_from_text(response_text, query)
                
            except Exception as inner_e:
                logger.error(f"[{self.node_name}] Text parsing failed: {inner_e}")
                # Ultra fallback
                return IntentClassification(
                    intent="chitchat",
                    confidence=0.5,
                    reasoning="Unable to classify, defaulting to chitchat"
                )
    
    def _parse_intent_from_text(
        self, 
        response: str, 
        query: str
    ) -> IntentClassification:
        """
        Parse intent từ text response của LLM (fallback method).
        
        Args:
            response: Response text từ LLM
            query: Original query
            
        Returns:
            IntentClassification object
        """
        # Simple heuristic parsing
        response_lower = response.lower()
        
        # Check từ khóa trong response
        if '"intent": "legal"' in response or '"intent":"legal"' in response:
            intent = "legal"
        elif '"intent": "procedure"' in response or '"intent":"procedure"' in response:
            intent = "procedure"
        else:
            intent = "chitchat"
        
        # Check từ khóa trong query để double-check
        query_lower = query.lower()
        legal_keywords = ["phạt", "luật", "điều", "quy định", "vi phạm", "lỗi", "nồng độ"]
        procedure_keywords = ["làm thế nào", "thủ tục", "đăng ký", "giấy tờ", "nộp", "đóng"]
        
        # Nếu query có từ khóa rõ ràng, override
        if any(kw in query_lower for kw in legal_keywords):
            intent = "legal"
        elif any(kw in query_lower for kw in procedure_keywords):
            intent = "procedure"
        
        return IntentClassification(
            intent=intent,
            confidence=0.7,
            reasoning=f"Parsed from text response: {response[:100]}"
        )
