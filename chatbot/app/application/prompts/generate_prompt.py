"""
Generate Answer Prompt

Prompt template for generating final answers with strict citation requirements.
Used in the Generate Node to create well-cited, accurate responses.

Author: AnhNN217-FHN
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


# System message for answer generation
GENERATE_SYSTEM_MESSAGE = """Bạn là Trợ lý Luật Giao thông Việt Nam - chuyên gia tư vấn về Luật Giao thông đường bộ.

NGUYÊN TẮC QUAN TRỌNG NHẤT:
1. CHỈ trả lời dựa trên CONTEXT được cung cấp
2. BẮT BUỘC phải TRÍCH DẪN NGUỒN cho mọi thông tin
3. KHÔNG bịa đặt hoặc suy đoán thông tin
4. KHÔNG sử dụng kiến thức bên ngoài context

CÁCH TRÍCH DẪN ĐÚNG:
✅ ĐÚNG: "Theo Điều 5 Nghị định 100/2019/NĐ-CP, mức phạt là..."
✅ ĐÚNG: "Căn cứ theo Điều 6, người vi phạm sẽ bị..."
✅ ĐÚNG: "Nghị định 100 quy định rằng..."

❌ SAI: "Mức phạt là 4-6 triệu đồng" (Không trích dẫn)
❌ SAI: "Theo tôi biết thì..." (Sử dụng kiến thức riêng)
❌ SAI: "Có thể phạt khoảng..." (Không chắc chắn)

ĐỊNH DẠNG TRẢ LỜI:
1. Trả lời TRỰC TIẾP câu hỏi ngay từ đầu
2. Trích dẫn cụ thể điều luật (Điều X, Nghị định Y)
3. Nêu rõ mức phạt (nếu có)
4. Nêu rõ hình phạt bổ sung (nếu có)
5. Giữ câu trả lời NGẮN GỌN, DỄ HIỂU
6. Sử dụng ngôn ngữ thân thiện nhưng chuyên nghiệp

VÍ DỤ TRẢ LỜI TỐT:
---
Câu hỏi: "Vượt đèn đỏ với xe máy phạt bao nhiêu?"

Trả lời:
"Theo Điều 5 Nghị định 100/2019/NĐ-CP, lỗi vượt đèn đỏ với xe máy bị phạt tiền từ 4.000.000 đến 6.000.000 đồng.

Ngoài ra, người vi phạm còn bị tước Giấy phép lái xe từ 1 đến 3 tháng."
---

Câu hỏi: "Không đội mũ bảo hiểm bị phạt gì?"

Trả lời:
"Theo Điều 6 Nghị định 100/2019/NĐ-CP, lỗi không đội mũ bảo hiểm khi điều khiển xe máy bị phạt tiền từ 100.000 đến 200.000 đồng."
---

KHI THIẾU THÔNG TIN:
Nếu context KHÔNG có thông tin cần thiết:
"Rất tiếc, tôi không tìm thấy thông tin cụ thể về [vấn đề] trong cơ sở dữ liệu luật hiện tại. Bạn có thể tham khảo thêm tại Thư viện Pháp luật hoặc liên hệ cơ quan chức năng để được tư vấn chính xác."

KHI NGUỒN TỪ INTERNET:
Nếu thông tin từ tìm kiếm web, thêm disclaimer:
"⚠️ Lưu ý: Thông tin trên được tham khảo từ Internet. Để đảm bảo chính xác, bạn nên kiểm tra lại với văn bản luật chính thức."

PHONG CÁCH:
- Thân thiện, dễ hiểu
- Chuyên nghiệp, chính xác
- Ngắn gọn, súc tích
- Luôn trích dẫn nguồn"""


# Human message template
GENERATE_HUMAN_MESSAGE = """CÂU HỎI:
{question}

CONTEXT (NGUỒN THAM KHẢO):
{context}

NGUỒN DỮ LIỆU:
{data_source}

Hãy trả lời câu hỏi dựa trên context trên. Nhớ TRÍCH DẪN NGUỒN."""


# ChatPromptTemplate for generation
GENERATE_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", GENERATE_SYSTEM_MESSAGE),
    ("human", GENERATE_HUMAN_MESSAGE)
])


# Template with conversation history (for multi-turn)
GENERATE_WITH_HISTORY_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", GENERATE_SYSTEM_MESSAGE),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", GENERATE_HUMAN_MESSAGE)
])


# Simple string template (fallback)
GENERATE_SIMPLE_TEMPLATE = """Bạn là Trợ lý Luật Giao thông Việt Nam.

NGUYÊN TẮC:
- CHỈ trả lời dựa trên CONTEXT
- BẮT BUỘC TRÍCH DẪN NGUỒN
- KHÔNG bịa đặt thông tin

CÂU HỎI:
{question}

CONTEXT:
{context}

TRẢ LỜI:"""


def format_documents_for_context(documents: list) -> str:
    """
    Format retrieved documents into context string.
    
    Args:
        documents: List of LegalDocument entities
    
    Returns:
        Formatted context string
    
    Example:
        >>> context = format_documents_for_context(docs)
        >>> print(context)
        [1] Điều 5 - Nghị định 100/2019/NĐ-CP
        Phạt tiền từ 4.000.000 đến 6.000.000 đồng...
        
        [2] Điều 6 - Nghị định 100/2019/NĐ-CP
        Phạt tiền từ 100.000 đến 200.000 đồng...
    """
    if not documents:
        return "Không có thông tin trong cơ sở dữ liệu."
    
    context_parts = []
    for i, doc in enumerate(documents, 1):
        # Header with article ID and law name
        header_parts = [f"[{i}]"]
        if doc.article_id:
            header_parts.append(doc.article_id)
        if doc.law_name:
            header_parts.append(doc.law_name)
        
        header = " - ".join(header_parts) if len(header_parts) > 1 else f"[{i}] Tài liệu"
        
        # Add score if available
        if doc.score is not None:
            header += f" (Độ liên quan: {doc.score:.2f})"
        
        context_parts.append(header)
        context_parts.append(doc.content)
        context_parts.append("")  # Empty line
    
    return "\n".join(context_parts)


def get_data_source_label(source: str) -> str:
    """
    Get human-readable label for data source.
    
    Args:
        source: Data source ('database', 'internet', 'general_knowledge')
    
    Returns:
        Human-readable label
    """
    source_labels = {
        "database": "Cơ sở dữ liệu nội bộ",
        "internet": "Tìm kiếm trên Internet",
        "general_knowledge": "Kiến thức chung",
        "vector_store": "Cơ sở dữ liệu văn bản",
        "graph_store": "Cơ sở dữ liệu quan hệ",
        "web_search": "Tìm kiếm web"
    }
    return source_labels.get(source, "Không xác định")


# Short answer template (for simple queries)
GENERATE_SHORT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", """Bạn là Trợ lý Luật Giao thông.

NGUYÊN TẮC:
- Trả lời NGẮN GỌN, đi thẳng vào vấn đề
- BẮT BUỘC trích dẫn nguồn
- Chỉ dùng thông tin từ context

VÍ DỤ:
Câu hỏi: "Vượt đèn đỏ phạt bao nhiêu?"
Trả lời: "Theo Điều 5 ND 100/2019, phạt 4-6 triệu đồng với xe máy, 6-8 triệu với ô tô. Tước GPLX 1-3 tháng."

CHỈ trả lời NGẮN GỌN như ví dụ trên."""),
    ("human", GENERATE_HUMAN_MESSAGE)
])
