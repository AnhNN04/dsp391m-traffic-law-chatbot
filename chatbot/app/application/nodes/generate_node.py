"""
Generate Node - NODE 7: Final Answer Generation.

Tổng hợp thông tin từ documents và sinh câu trả lời cuối cùng cho user.
"""

from typing import Dict, Any, List
from langchain_core.messages import AIMessage

from app.domain.state import AgentState
from app.domain.entities import LegalDocument
from app.application.interfaces.i_llm_service import ILLMService
from app.application.nodes.base_node import BaseNode
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)


class GenerateNode(BaseNode):
    """
    Node sinh câu trả lời cuối cùng cho người dùng.
    
    Trách nhiệm:
    1. Tổng hợp thông tin từ documents
    2. Sinh câu trả lời tự nhiên, chính xác
    3. Trích dẫn nguồn rõ ràng
    4. Thêm disclaimer nếu dùng dữ liệu web
    
    Nguyên tắc:
    - BẮT BUỘC trích dẫn nguồn (Theo Điều X, Nghị định Y...)
    - Không bịa đặt thông tin không có trong documents
    - Nếu không chắc chắn, nói rõ
    - Ngôn ngữ chuyên nghiệp nhưng dễ hiểu
    
    Ví dụ output tốt:
        "Theo Nghị định 100/2019/NĐ-CP, mức phạt đối với lỗi vượt đèn đỏ 
        của xe máy là từ 800.000đ đến 1.000.000đ. Ngoài ra, vi phạm có thể 
        bị trừ 2 điểm giấy phép lái xe."
    """
    
    GENERATE_SYSTEM_PROMPT = """Bạn là chuyên gia tư vấn luật giao thông Việt Nam chuyên nghiệp.

NHIỆM VỤ:
Trả lời câu hỏi của người dùng dựa HOÀN TOÀN trên các văn bản được cung cấp.

NGUYÊN TẮC BẮT BUỘC:
1. **Trích dẫn nguồn**: Luôn cite rõ ràng (VD: "Theo Điều 5 Nghị định 100/2019/NĐ-CP...")
2. **Chính xác**: Chỉ dùng thông tin có trong văn bản, KHÔNG tự suy diễn
3. **Đầy đủ**: Trả lời trọn vẹn câu hỏi, không bỏ sót chi tiết quan trọng
4. **Rõ ràng**: Dùng ngôn ngữ dễ hiểu, tránh thuật ngữ khó
5. **Thừa nhận giới hạn**: Nếu văn bản không đủ info, nói thẳng

CÁCH TRÍCH DẪN:
✅ Tốt: "Theo Điều 6 Nghị định 100/2019/NĐ-CP, mức phạt là..."
✅ Tốt: "Nghị định 100 quy định rằng..."
❌ Tránh: "Tôi nghĩ rằng...", "Có thể là...", "Thường thì..."

FORMAT TRẢ LỜI:
- Trả lời trực tiếp câu hỏi ở đoạn đầu
- Bổ sung chi tiết, lưu ý nếu cần
- Kết thúc với nguồn tham khảo (nếu nhiều nguồn)

TONE:
Chuyên nghiệp, lịch sự, hữu ích. Xưng hô "em" (cho bot), "anh/chị" (cho user).
"""

    GENERATE_USER_PROMPT = """Câu hỏi của người dùng: "{query}"

Các văn bản tham khảo:
{documents}

Hãy trả lời câu hỏi dựa trên các văn bản trên. Nhớ trích dẫn nguồn rõ ràng."""

    def __init__(self, smart_llm: ILLMService):
        """
        Initialize Generate Node.
        
        Args:
            smart_llm: LLM thông minh (GPT-4o-mini) để sinh câu trả lời chất lượng
        """
        super().__init__(node_name="Generate")
        self.llm = smart_llm
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Sinh câu trả lời cuối cùng.
        
        Args:
            state: AgentState chứa rewritten_query, documents, data_source
            
        Returns:
            Dict với messages (AIMessage)
        """
        self._log_entry(state)
        
        try:
            # Validate state
            self._validate_state(state, required_keys=["rewritten_query"])
            
            query = state["rewritten_query"]
            documents = state.get("documents", [])
            data_source = state.get("data_source", "unknown")
            
            # Case 1: Không có documents -> Trả lời chung chung
            if not documents:
                logger.warning(f"[{self.node_name}] No documents, generating fallback answer")
                answer = self._generate_fallback_answer(query)
            else:
                # Case 2: Có documents -> Sinh câu trả lời từ context
                answer = self._generate_from_documents(query, documents, data_source)
            
            logger.info(
                f"[{self.node_name}] Generated answer: {len(answer)} chars | "
                f"Source: {data_source}"
            )
            
            result = {
                "messages": [AIMessage(content=answer)]
            }
            
            self._log_exit(result)
            return result
            
        except Exception as e:
            self._log_error(e)
            # Fallback: Trả lời xin lỗi
            error_message = (
                "Xin lỗi anh/chị, em gặp lỗi khi xử lý câu hỏi. "
                "Anh/chị vui lòng thử lại hoặc diễn đạt câu hỏi theo cách khác ạ."
            )
            return {
                "messages": [AIMessage(content=error_message)]
            }
    
    def _generate_from_documents(
        self, 
        query: str, 
        documents: List[LegalDocument], 
        data_source: str
    ) -> str:
        """
        Sinh câu trả lời dựa trên documents.
        
        Args:
            query: Câu hỏi của user
            documents: List documents tìm được
            data_source: Nguồn dữ liệu (database/internet)
            
        Returns:
            Câu trả lời final
        """
        # Format documents
        docs_text = self._format_documents_for_prompt(documents)
        
        # Build prompt
        user_prompt = self.GENERATE_USER_PROMPT.format(
            query=query,
            documents=docs_text
        )
        
        try:
            # Gọi LLM
            answer = self.llm.generate_text(
                prompt=user_prompt,
                system_message=self.GENERATE_SYSTEM_PROMPT
            )
            
            # Post-processing
            answer = answer.strip()
            
            # Thêm disclaimer nếu từ web
            if data_source == "internet":
                answer = self._add_web_disclaimer(answer)
            
            return answer
            
        except Exception as e:
            logger.error(f"[{self.node_name}] LLM generation failed: {e}")
            return self._generate_fallback_answer(query)
    
    def _format_documents_for_prompt(
        self, 
        documents: List[LegalDocument],
        max_docs: int = 5
    ) -> str:
        """
        Format documents thành text để đưa vào prompt.
        
        Args:
            documents: List documents
            max_docs: Số document tối đa (tránh quá dài)
            
        Returns:
            Formatted string
        """
        # Giới hạn số docs
        docs_to_use = documents[:max_docs]
        
        formatted_lines = []
        
        for idx, doc in enumerate(docs_to_use, 1):
            # Handle both dict and LegalDocument object
            if isinstance(doc, dict):
                content = doc.get("content", "")
                source = doc.get("source", "Unknown")
            else:
                content = getattr(doc, "content", "")
                source = getattr(doc, "source", "Unknown")
            
            # Truncate content nếu quá dài
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            formatted_lines.append(
                f"--- Văn bản {idx} ---\n"
                f"Nguồn: {source}\n"
                f"Nội dung:\n{content}\n"
            )
        
        return "\n".join(formatted_lines)
    
    def _generate_fallback_answer(self, query: str) -> str:
        """
        Sinh câu trả lời khi không có documents.
        
        Args:
            query: Câu hỏi của user
            
        Returns:
            Fallback answer
        """
        return (
            f"Xin lỗi anh/chị, em không tìm thấy thông tin cụ thể về '{query}' "
            "trong cơ sở dữ liệu hiện tại.\n\n"
            "Anh/chị có thể:\n"
            "- Diễn đạt lại câu hỏi với nhiều chi tiết hơn\n"
            "- Hỏi về các quy định luật giao thông cụ thể\n"
            "- Liên hệ trực tiếp cơ quan chức năng để được tư vấn chính xác nhất ạ."
        )
    
    def _add_web_disclaimer(self, answer: str) -> str:
        """
        Thêm disclaimer cho câu trả lời từ web.
        
        Args:
            answer: Câu trả lời gốc
            
        Returns:
            Answer có disclaimer
        """
        disclaimer = (
            "\n\n---\n"
            "📌 *Lưu ý*: Thông tin trên được tham khảo từ Internet. "
            "Em khuyến nghị anh/chị kiểm tra thêm từ nguồn chính thống "
            "hoặc liên hệ cơ quan pháp luật để chắc chắn ạ."
        )
        
        return answer + disclaimer
    
    def _is_query_chitchat(self, query: str) -> bool:
        """
        Check xem query có phải chitchat không (helper).
        
        Args:
            query: Query string
            
        Returns:
            True nếu là chitchat
        """
        chitchat_keywords = [
            "xin chào", "hello", "hi", "chào bạn",
            "cảm ơn", "thank", "tạm biệt", "bye",
            "bạn là ai", "tên gì", "how are you"
        ]
        
        query_lower = query.lower()
        return any(kw in query_lower for kw in chitchat_keywords)
    
    def _generate_chitchat_response(self, query: str) -> str:
        """
        Sinh response cho chitchat (optional - có thể handle ở router).
        
        Args:
            query: Query string
            
        Returns:
            Chitchat response
        """
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["xin chào", "hello", "hi", "chào"]):
            return (
                "Xin chào anh/chị! Em là trợ lý tư vấn luật giao thông. "
                "Anh/chị có câu hỏi gì về luật giao thông Việt Nam ạ?"
            )
        
        if any(kw in query_lower for kw in ["cảm ơn", "thank"]):
            return (
                "Rất vui được hỗ trợ anh/chị! Nếu có thắc mắc gì thêm, "
                "đừng ngại hỏi em nhé ạ."
            )
        
        if any(kw in query_lower for kw in ["tạm biệt", "bye"]):
            return (
                "Tạm biệt anh/chị! Chúc anh/chị lái xe an toàn ạ. "
                "Hẹn gặp lại! 👋"
            )
        
        # Default chitchat
        return (
            "Em là trợ lý tư vấn về luật giao thông Việt Nam. "
            "Anh/chị có câu hỏi gì về các quy định, mức phạt, "
            "hoặc thủ tục liên quan đến giao thông không ạ?"
        )
