"""
Grade Node - NODE 4: Document Quality Assessment & Routing Decision.

Đánh giá xem documents tìm được có đủ để trả lời câu hỏi hay cần hành động gì tiếp theo.
"""

from typing import Dict, Any, Literal
from pydantic import BaseModel, Field

from app.domain.state import AgentState
# from app.domain.entities import LegalDocument
from app.domain.interfaces.i_llm_service import ILLMService
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
    
    GRADE_PROMPT = """Bạn là chuyên gia đánh giá chất lượng thông tin pháp luật giao thông.

Câu hỏi: "{query}"

Văn bản tìm được:
{documents}

Nhiệm vụ: Đánh giá xem các văn bản có đủ để trả lời câu hỏi không.

**QUY TẮC PHÂN TÍCH QUAN TRỌNG VỀ TỪ VỰNG:**
Người dùng thường dùng từ ngữ đời sống (colloquial) thay vì thuật ngữ luật pháp, bạn MANG TRÁCH NHIỆM suy luận sự tương đương. Ví dụ:
- "vượt đèn đỏ", "vượt đèn vàng" -> tương đương với "không chấp hành hiệu lệnh của đèn tín hiệu giao thông"
- "kẹp 3", "chở 3" -> tương đương với "chở theo từ 02 người trở lên"
- "không xi nhan" -> tương đương với "chuyển hướng không có tín hiệu báo hướng rẽ"
- "đi ngược chiều" -> tương đương với "đi ngược chiều của đường đi một chiều"

**QUY TẮC ĐÁNH GIÁ CHUNG:**
- Nếu văn bản CÓ đề cập đến hành vi vi phạm tương đương với câu hỏi (sau khi đã suy luận từ ngữ học như trên) → `can_answer = true`
- Nếu câu hỏi hỏi tổng quát về một luật, văn bản trong luật đó là ĐỦ ĐỂ TRẢ LỜI
- Chỉ đặt `can_answer = false` khi văn bản HOÀN TOÀN không chứa bất kỳ hành vi tương đương nào. Ưu tiên giữ lại tài liệu để Generate Node xử lý thay vì reject.

Trả về JSON:
{{
    "can_answer": true hoặc false,
    "reason": "Lý do ngắn gọn (nếu true, hãy chỉ ra cụm từ luật pháp tương đương. Nếu false, giải thích tại sao không khớp)",
    "missing_info": "" (nếu can_answer=false: thiếu gì),
    "confidence": 0.9
}}
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
            next_action = self._determine_next_action(grade_result, has_documents=bool(documents))
            
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
        """Format documents với metadata đầy đủ để LLM biết nguồn luật."""
        formatted_lines = []
        total_chars = 0

        for idx, doc in enumerate(documents, 1):
            if isinstance(doc, dict):
                content    = doc.get("content", "")
                law_name   = doc.get("law_name", "")
                law_id     = doc.get("law_id", "")
                article_id = doc.get("article_id", "")
                clause     = doc.get("clause", "")
            else:
                content    = getattr(doc, "content", "")
                law_name   = getattr(doc, "law_name", "") or ""
                law_id     = ""
                article_id = getattr(doc, "article_id", "") or ""
                meta       = getattr(doc, "metadata", {}) or {}
                law_id     = meta.get("law_id", "")
                clause     = meta.get("clause", "")

            if len(content) > 500:
                content = content[:500] + "..."

            # Header rõ ràng giúp LLM nhận ra luật nào
            header_parts = []
            if law_id:
                header_parts.append(law_id)
            if law_name:
                header_parts.append(law_name[:60])
            if article_id:
                header_parts.append(f"Điều {article_id}" + (f" Khoản {clause}" if clause else ""))
            header = " | ".join(header_parts) if header_parts else f"Văn bản {idx}"

            formatted_lines.append(f"[{idx}] {header}\n{content}\n")

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
        grade_result: GradeResult,
        has_documents: bool = True
    ) -> Literal["generate", "web_search", "ask_human"]:
        """
        Quyết định next action dựa trên đánh giá của LLM.
        
        Logic:
        - Nếu LLM đánh giá văn bản CÓ THỂ trả lời (can_answer=True) -> generate
        - Nếu LLM đánh giá văn bản KHÔNG THỂ trả lời (can_answer=False) -> web_search
        - Nếu không có văn bản nào -> web_search
        """
        # Không có docs → web search
        if not has_documents:
            return "web_search"
            
        # Nếu LLM đánh giá không thể trả lời bằng đống văn bản này -> fallback web_search
        if not grade_result.can_answer:
            logger.info(f"[{self.node_name}] Documents irrelevant/insufficient, routing to web_search. Reason: {grade_result.reason}")
            return "web_search"
            
        return "generate"
