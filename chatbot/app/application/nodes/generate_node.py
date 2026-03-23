"""
Generate Node - NODE 7: Final Answer Generation.

Tổng hợp thông tin từ documents và sinh câu trả lời cuối cùng cho user.
"""

from typing import Dict, Any, List
from langchain_core.messages import AIMessage

from app.domain.state import AgentState
from app.domain.entities import LegalDocument
from app.domain.interfaces.i_llm_service import ILLMService
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
    
    GENERATE_SYSTEM_PROMPT = """Bạn là chuyên gia tư vấn luật giao thông Việt Nam.

NHIỆM VỤ: Trả lời câu hỏi DỰA TRÊN CÁC VĂN BẢN ĐƯỢC CUNG CẤP BÊN DƯỚI. Không được dùng kiến thức ngoài.

QUY TẮC BẮT BUỘC:
1. **CHỈ dùng thông tin có trong văn bản được cung cấp** — TUYỆT ĐỐI không tự thêm thông tin từ kiến thức bên ngoài.
2. **Trích dẫn nguồn rõ ràng**: "Theo Điều X Khoản Y Nghị định Z..." (chỉ cite những điều CÓ trong văn bản).
3. **Nêu đầy đủ các hình thức xử phạt** nếu văn bản đề cập:
   - Phạt tiền (mức tối thiểu – tối đa)
   - Hình thức phạt bổ sung: tước quyền sử dụng GPLX, tạm giữ phương tiện, trục xuất...
   - Trừ điểm GPLX (nếu có)
4. **Phân loại theo loại phương tiện** khi văn bản quy định khác nhau cho xe máy, ô tô, xe tải...
5. **TỰ ĐỘNG SUY LUẬN TỪ NGỮ**: Khi người dùng hỏi bằng ngôn ngữ đời thường (VD: "vượt đèn đỏ", "kẹp 3", "không xi nhan", "ngược chiều"), hãy TRỰC TIẾP sử dụng các Điểm, Khoản có nội dung tương đương về mặt pháp lý (VD: "không chấp hành hiệu lệnh của đèn tín hiệu", "chở theo từ 2 người", "không có tín hiệu báo hướng rẽ", "đi ngược chiều") để trả lời chứ đừng báo là không tìm thấy quy định.
6. **Nếu thực sự không tìm thấy** thông tin liên quan dù đã thử suy luận tương đương → thừa nhận thẳng: "Trong các văn bản cung cấp không có quy định cụ thể về vấn đề này."
7. KHÔNG được đề cập bất kỳ luật nào KHÔNG có trong văn bản được cung cấp.

CẤU TRÚC CÂU TRẢ LỜI GỢI Ý:
- Mở đầu: Nêu hành vi vi phạm (sử dụng từ ngữ pháp lý kết hợp với từ của người dùng cho dễ hiểu) và căn cứ pháp lý.
- Thân: Liệt kê mức phạt theo loại phương tiện (nếu có).
- Phạt bổ sung: Tước GPLX / tạm giữ xe / trừ điểm (nếu văn bản đề cập).
- Kết: Bảng tóm tắt nếu có nhiều mức phạt khác nhau.

TONE: Chuyên nghiệp, rõ ràng hut gọn. Xưng "em", gọi "anh/chị".
"""

    GENERATE_USER_PROMPT = """Câu hỏi của người dùng: "{query}"

Các văn bản tham khảo:
{documents}

Hãy trả lời đầy đủ và chính xác câu hỏi dựa trên các văn bản trên. Trích dẫn nguồn cụ thể (Điều, Khoản, Nghị định). Nếu câu hỏi liên quan đến xử phạt, hãy nêu rõ mức phạt tiền, hình thức phạt bổ sung và điểm trừ GPLX nếu có."""

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
            intent = state.get("intent", "legal")
            
            # Case 1: Chitchat (không có documents vì chưa qua Retrieval)
            if not documents and intent not in ["legal", "procedure"]:
                logger.info(f"[{self.node_name}] Chitchat detected, generating conversational response")
                answer = self._generate_chitchat_response(query)
            # Case 2: Không có documents nhưng là câu hỏi pháp lý -> Không tìm được gì
            elif not documents:
                logger.warning(f"[{self.node_name}] No documents, generating fallback answer")
                answer = self._generate_fallback_answer(query)
            else:
                # Case 3: Có documents -> Sinh câu trả lời từ context
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
            
            # Loại bỏ disclaimer (theo yêu cầu user để ẩn việc search web)
            # if data_source == "internet":
            #     answer = self._add_web_disclaimer(answer)
            
            return answer
            
        except Exception as e:
            logger.error(f"[{self.node_name}] LLM generation failed: {e}")
            return self._generate_fallback_answer(query)
    
    def _format_documents_for_prompt(
        self, 
        documents: List[LegalDocument],
        max_docs: int = 6
    ) -> str:
        """Format documents thành text để đưa vào prompt."""
        # Ưu tiên db docs hơn vì chính xác hơn so với web docs
        web_docs = []
        db_docs = []
        for doc in documents:
            source_type = "db"
            if isinstance(doc, dict):
                if doc.get("metadata", {}).get("source_type") == "web":
                    source_type = "web"
            elif hasattr(doc, "metadata") and doc.metadata.get("source_type") == "web":
                source_type = "web"
                
            if source_type == "web":
                web_docs.append(doc)
            else:
                db_docs.append(doc)
                
        # Lấy db docs trước, bổ sung web docs nếu còn slot
        docs_to_use = db_docs + web_docs
        docs_to_use = docs_to_use[:max_docs]
        
        formatted_lines = []

        for idx, doc in enumerate(docs_to_use, 1):
            if isinstance(doc, dict):
                content    = doc.get("content", "")
                law_name   = doc.get("law_name", "")
                article_id = doc.get("article_id", "")
                clause     = doc.get("clause", "")
            else:
                content    = getattr(doc, "content", "")
                
                # Cố gắng lấy law_name từ attr hoặc metadata
                doc_meta = getattr(doc, "metadata", {}) or {}
                law_name   = getattr(doc, "law_name", None) or doc_meta.get("law_name", "")
                article_id = getattr(doc, "article_id", None) or doc_meta.get("article_id", "")
                clause     = doc_meta.get("clause", "")

            # Truncate nếu quá dài (Giảm xuống 2000 thay vì 3000 để tránh lỗi API TPM)
            max_len = 2000
            if len(content) > max_len:
                content = content[:max_len] + "..."

            # Lấy law_id từ metadata/doc
            if isinstance(doc, dict):
                law_id = doc.get("law_id", "") or doc.get("metadata", {}).get("law_id", "")
            else:
                doc_meta = getattr(doc, "metadata", {}) or {}
                law_id = getattr(doc, "law_id", None) or doc_meta.get("law_id", "")

            # Xác định loại nguồn để ghi chú trong prompt
            source_type = "DATABASE"
            if isinstance(doc, dict):
                if doc.get("metadata", {}).get("source_type") == "web":
                    source_type = "WEB_REFERENCE"
            elif hasattr(doc, "metadata") and doc.metadata.get("source_type") == "web":
                source_type = "WEB_REFERENCE"

            # Header rõ ràng để LLM trích dẫn đúng
            header_parts = [f"Source: {source_type}"]
            if law_id:
                header_parts.append(law_id)
            if law_name:
                header_parts.append(law_name[:100])
            if article_id:
                header_parts.append(f"Điều {article_id}" + (f" Khoản {clause}" if clause else ""))
            header = " | ".join(header_parts) if header_parts else f"Văn bản {idx}"


            formatted_lines.append(
                f"--- [{idx}] {header} ---\n"
                f"{content}\n"
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
            "📌 *Lưu ý*: Những thông tin trên vẫn chỉ mang tính chất tham khảo, "
            "hãy kiểm tra lại từ các văn bản chính thống."
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
                "Tạm biệt anh/chị! Hy vọng là em đã giúp ích được cho anh/chị. "
                "Hẹn gặp lại! 👋"
            )
        else:
            return (
                "Câu hỏi của anh/chị không thuộc lĩnh vực luật giao thông mà em có thể hỗ trợ. "
                "Anh/chị có muốn hỏi về các quy định, mức phạt hoặc thủ tục giao thông không ạ? 🚦"
            )
        
        # Default chitchat
        # return (
        #     "Em là trợ lý tư vấn về luật giao thông Việt Nam. "
        #     "Anh/chị có câu hỏi gì về các quy định, mức phạt, "
        #     "hoặc thủ tục liên quan đến giao thông không ạ?"
        # )
