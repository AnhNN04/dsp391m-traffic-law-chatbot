"""
Grade Node - NODE 4: Document Quality Assessment & Routing Decision.

Đánh giá xem documents tìm được có đủ để trả lời câu hỏi hay cần hành động gì tiếp theo.
"""

from typing import Dict, Any, Literal
from pydantic import BaseModel, Field

from app.domain.state import AgentState
# from app.domain.entities import LegalDocument
from app.application.interfaces.i_llm_service import ILLMService
from app.application.nodes.base_node import BaseNode
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)


class GradeResult(BaseModel):
    """Schema cho kết quả đánh giá documents."""
    can_answer: bool = Field(
        description="Có thể trả lời câu hỏi dựa trên documents hiện có không"
    )
    reason: str = Field(
        description="Lý do đánh giá"
    )
    missing_info: str = Field(
        default="",
        description="Thông tin còn thiếu (nếu can_answer = False)"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Độ tin cậy của đánh giá"
    )


class GradeNode(BaseNode):
    """
    Node đánh giá chất lượng và độ đầy đủ của documents.
    
    Routing logic:
    1. Documents rỗng -> next_action = "web_search"
    2. Documents có nhưng thiếu thông tin quan trọng -> "ask_human"
    3. Documents mâu thuẫn hoặc không liên quan -> "web_search"
    4. Documents đầy đủ -> "generate"
    
    Ví dụ:
        Query: "Xe máy vượt đèn đỏ phạt bao nhiêu?"
        Docs: [Doc về vượt đèn đỏ cho ô tô]
        -> can_answer=False, missing_info="loại phương tiện"
        -> next_action="ask_human"
    """
    
    GRADE_PROMPT = """Bạn là chuyên gia đánh giá chất lượng thông tin.

Câu hỏi của người dùng: "{query}"

Các văn bản tìm được:
{documents}

Nhiệm vụ: Đánh giá xem các văn bản trên có đủ thông tin để trả lời câu hỏi không.

Tiêu chí đánh giá:
1. **Liên quan**: Văn bản có liên quan trực tiếp đến câu hỏi?
2. **Đầy đủ**: Thông tin có đủ chi tiết để trả lời đầy đủ?
3. **Nhất quán**: Các văn bản có mâu thuẫn nhau không?
4. **Cụ thể**: Nếu câu hỏi hỏi về 1 đối tượng cụ thể (VD: xe máy), văn bản có đề cập đúng đối tượng đó?

Trả về JSON:
{{
    "can_answer": true hoặc false,
    "reason": "Giải thích ngắn gọn",
    "missing_info": "Thông tin còn thiếu (VD: 'loại phương tiện', 'khu vực', 'thời gian')" hoặc "",
    "confidence": 0.9
}}

LƯU Ý:
- Nếu văn bản chỉ đề cập chung chung mà câu hỏi hỏi cụ thể -> can_answer = false
- Nếu văn bản mâu thuẫn nhau -> can_answer = false
- Nếu văn bản hoàn toàn không liên quan -> can_answer = false
"""

    def __init__(self, smart_llm: ILLMService):
        """
        Initialize Grade Node.
        
        Args:
            smart_llm: LLM thông minh để đánh giá chất lượng
        """
        super().__init__(node_name="Grade")
        self.llm = smart_llm
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Đánh giá documents và quyết định next action.
        
        Args:
            state: AgentState chứa rewritten_query và documents
            
        Returns:
            Dict với next_action field
        """
        self._log_entry(state)
        
        try:
            # Validate state
            self._validate_state(state, required_keys=["rewritten_query", "documents"])
            
            query = state["rewritten_query"]
            documents = state["documents"]
            
            # Case 1: Documents rỗng -> Web search
            if not documents:
                logger.info(f"[{self.node_name}] No documents found, routing to web_search")
                result = {
                    "next_action": "web_search",
                    "grade_result": {
                        "can_answer": False,
                        "reason": "No documents retrieved"
                    }
                }
                self._log_exit(result)
                return result
            
            # Case 2: Có documents -> Đánh giá chất lượng
            grade_result = self._grade_documents(query, documents)
            
            # Determine next action
            next_action = self._determine_next_action(grade_result)
            
            logger.info(
                f"[{self.node_name}] Grade: can_answer={grade_result.can_answer} | "
                f"confidence={grade_result.confidence:.2f} | "
                f"next_action={next_action} | "
                f"reason={grade_result.reason}"
            )
            
            result = {
                "next_action": next_action,
                "grade_result": grade_result.dict()
            }
            
            self._log_exit(result)
            return result
            
        except Exception as e:
            self._log_error(e)
            # Fallback: Cho phép generate (tránh stuck)
            logger.warning(f"[{self.node_name}] Grade failed, defaulting to generate")
            return {
                "next_action": "generate",
                "grade_result": {
                    "can_answer": True,
                    "reason": "Grade failed, attempting to generate"
                }
            }
    
    def _grade_documents(
        self, 
        query: str, 
        documents: list
    ) -> GradeResult:
        """
        Đánh giá chất lượng documents bằng LLM.
        
        Args:
            query: Câu hỏi gốc
            documents: List documents (có thể là dict hoặc LegalDocument)
            
        Returns:
            GradeResult object
        """
        # Format documents thành text
        docs_text = self._format_documents(documents)
        
        prompt = self.GRADE_PROMPT.format(
            query=query,
            documents=docs_text
        )
        
        try:
            # Sử dụng structured output
            result = self.llm.generate_structured(
                prompt=prompt,
                schema=GradeResult
            )
            return result
            
        except Exception as e:
            logger.warning(f"[{self.node_name}] Structured grading failed: {e}")
            
            # Fallback: Simple heuristic
            return self._heuristic_grade(query, documents)
    
    def _format_documents(self, documents: list, max_chars: int = 2000) -> str:
        """
        Format documents thành text để đưa vào prompt.
        
        Args:
            documents: List documents
            max_chars: Giới hạn tổng số ký tự
            
        Returns:
            Formatted string
        """
        formatted_lines = []
        total_chars = 0
        
        for idx, doc in enumerate(documents, 1):
            # Handle both dict and LegalDocument object
            if isinstance(doc, dict):
                content = doc.get("content", "")
                source = doc.get("source", "Unknown")
            else:
                content = getattr(doc, "content", "")
                source = getattr(doc, "source", "Unknown")
            
            # Truncate nếu quá dài
            if len(content) > 500:
                content = content[:500] + "..."
            
            formatted_lines.append(
                f"[Document {idx}] (Source: {source})\n{content}\n"
            )
            
            total_chars += len(content)
            if total_chars > max_chars:
                formatted_lines.append(f"... (và {len(documents) - idx} documents khác)")
                break
        
        return "\n".join(formatted_lines) if formatted_lines else "Không có văn bản nào."
    
    def _heuristic_grade(self, query: str, documents: list) -> GradeResult:
        """
        Đánh giá đơn giản bằng heuristic (fallback khi LLM fail).
        
        Args:
            query: Query string
            documents: List documents
            
        Returns:
            GradeResult
        """
        # Nếu không có docs
        if not documents:
            return GradeResult(
                can_answer=False,
                reason="No documents available",
                confidence=1.0
            )
        
        # Nếu có ít nhất 1 doc -> Assume có thể trả lời
        # (Conservative approach)
        return GradeResult(
            can_answer=True,
            reason=f"Found {len(documents)} documents (heuristic fallback)",
            confidence=0.6
        )
    
    def _determine_next_action(
        self, 
        grade_result: GradeResult
    ) -> Literal["generate", "web_search", "ask_human"]:
        """
        Quyết định next action dựa trên grade result.
        
        Logic:
        1. can_answer=True và confidence cao -> generate
        2. can_answer=False và có missing_info cụ thể -> ask_human
        3. can_answer=False và không rõ thiếu gì -> web_search
        4. can_answer=True nhưng confidence thấp -> web_search (verify)
        
        Args:
            grade_result: Kết quả đánh giá
            
        Returns:
            Next action string
        """
        # Rule 1: Có thể trả lời và tin tưởng
        if grade_result.can_answer and grade_result.confidence >= 0.7:
            return "generate"
        
        # Rule 2: Thiếu thông tin CỤ THỂ -> Hỏi user
        if (not grade_result.can_answer 
            and grade_result.missing_info 
            and len(grade_result.missing_info.strip()) > 0):
            return "ask_human"
        
        # Rule 3: Confidence thấp hoặc không đủ thông tin -> Search web
        if grade_result.confidence < 0.5 or not grade_result.can_answer:
            return "web_search"
        
        # Default: Thử generate
        return "generate"
