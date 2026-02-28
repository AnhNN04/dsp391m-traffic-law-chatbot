"""
Clarification Prompt

Prompt template for generating clarification questions.
Used in the Ask Human Node when information is ambiguous or insufficient.

Author: AnhNN217-FHN
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


# Pydantic schema for clarification output
class ClarificationQuestion(BaseModel):
    """Structured output for clarification question."""
    
    question: str = Field(
        description="The clarification question to ask the user"
    )
    reason: str = Field(
        description="Why this clarification is needed"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested answers (if applicable)"
    )


# System message for clarification
CLARIFICATION_SYSTEM_MESSAGE = """Bạn là trợ lý thông minh, chuyên đặt câu hỏi làm rõ khi thông tin chưa đầy đủ.

NHIỆM VỤ:
Sinh ra câu hỏi ngắn gọn, rõ ràng để hỏi người dùng khi:
1. Câu hỏi thiếu thông tin quan trọng
2. Có nhiều cách hiểu khác nhau
3. Cần xác định loại xe, tình huống cụ thể

NGUYÊN TẮC:
✅ Câu hỏi NGẮN GỌN (1 câu)
✅ DỄ HIỂU, thân thiện
✅ ĐI THẲNG VÀO VẤN ĐỀ
✅ Đưa ra GỢI Ý trả lời nếu có thể

❌ TRÁNH câu hỏi dài dòng
❌ TRÁNH hỏi nhiều thứ cùng lúc
❌ TRÁNH ngôn ngữ quá chính thức

VÍ DỤ TỐT:
---
Tình huống: User hỏi "phạt bao nhiêu" mà không rõ loại xe
Câu hỏi: "Bạn đang hỏi về xe máy hay ô tô?"
Gợi ý: ["Xe máy", "Ô tô", "Xe tải"]
---

Tình huống: Hỏi về "vượt đèn" nhưng không rõ đèn đỏ hay đèn vàng
Câu hỏi: "Bạn muốn hỏi về vượt đèn đỏ hay đèn vàng?"
Gợi ý: ["Đèn đỏ", "Đèn vàng"]
---

Tình huống: Hỏi "lỗi đó" mà không rõ lỗi gì
Câu hỏi: "Bạn đang hỏi về lỗi vi phạm nào?"
Gợi ý: []
---

PHONG CÁCH:
- Thân thiện, lịch sự
- Ngắn gọn, dễ hiểu
- Giúp người dùng trả lời dễ dàng"""


# Human message template
CLARIFICATION_HUMAN_MESSAGE = """CÂU HỎI GỐC:
{original_query}

VẤN ĐỀ:
{issue}

TÀI LIỆU TÌM ĐƯỢC (nếu có):
{documents_summary}

Hãy sinh câu hỏi làm rõ ngắn gọn, thân thiện để hỏi người dùng."""


# ChatPromptTemplate for clarification
CLARIFICATION_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", CLARIFICATION_SYSTEM_MESSAGE),
    ("human", CLARIFICATION_HUMAN_MESSAGE)
])


# Simple string template (fallback)
CLARIFICATION_SIMPLE_TEMPLATE = """Sinh câu hỏi làm rõ cho tình huống sau:

CÂU HỎI GỐC: {original_query}
VẤN ĐỀ: {issue}

Câu hỏi làm rõ (ngắn gọn, thân thiện):"""


# Pre-defined clarification patterns
CLARIFICATION_PATTERNS = {
    "missing_vehicle_type": {
        "question": "Bạn đang hỏi về loại xe nào?",
        "suggestions": ["Xe máy", "Ô tô", "Xe tải", "Xe khách"]
    },
    "missing_violation_type": {
        "question": "Bạn muốn hỏi về lỗi vi phạm nào?",
        "suggestions": ["Vượt đèn đỏ", "Quá tốc độ", "Không đội mũ bảo hiểm", "Nồng độ cồn"]
    },
    "ambiguous_light": {
        "question": "Bạn muốn hỏi về đèn giao thông màu gì?",
        "suggestions": ["Đèn đỏ", "Đèn vàng", "Đèn xanh"]
    },
    "missing_location": {
        "question": "Vi phạm xảy ra ở khu vực nào?",
        "suggestions": ["Nội thành", "Ngoại thành", "Cao tốc", "Đường tỉnh"]
    },
    "missing_time_context": {
        "question": "Bạn hỏi về quy định hiện hành hay trước đây?",
        "suggestions": ["Hiện tại", "Năm 2019", "Năm 2020"]
    }
}


def get_predefined_clarification(pattern_key: str) -> dict:
    """
    Get a predefined clarification question by pattern key.
    
    Args:
        pattern_key: Key from CLARIFICATION_PATTERNS
    
    Returns:
        Dictionary with question and suggestions
    
    Example:
        >>> clarification = get_predefined_clarification("missing_vehicle_type")
        >>> print(clarification["question"])
        "Bạn đang hỏi về loại xe nào?"
    """
    return CLARIFICATION_PATTERNS.get(pattern_key, {
        "question": "Bạn có thể cung cấp thêm thông tin được không?",
        "suggestions": []
    })


def detect_missing_info(query: str) -> str:
    """
    Detect what information is missing from the query.
    
    Args:
        query: User query
    
    Returns:
        Pattern key for the missing information
    
    Example:
        >>> pattern = detect_missing_info("phạt bao nhiêu?")
        >>> print(pattern)
        "missing_vehicle_type"
    """
    query_lower = query.lower()
    
    # Check for missing vehicle type
    vehicle_keywords = ["xe máy", "ô tô", "xe tải", "xe khách", "xe buýt", "mô tô"]
    if not any(keyword in query_lower for keyword in vehicle_keywords):
        if "phạt" in query_lower or "mức phạt" in query_lower:
            return "missing_vehicle_type"
    
    # Check for missing violation type
    violation_keywords = ["đèn đỏ", "tốc độ", "mũ bảo hiểm", "cồn", "rượu"]
    if not any(keyword in query_lower for keyword in violation_keywords):
        if "lỗi" in query_lower or "vi phạm" in query_lower:
            return "missing_violation_type"
    
    # Check for ambiguous light reference
    if "đèn" in query_lower and not any(
        color in query_lower for color in ["đỏ", "vàng", "xanh"]
    ):
        return "ambiguous_light"
    
    return "general"


def format_documents_summary(documents: list) -> str:
    """
    Create a summary of retrieved documents for context.
    
    Args:
        documents: List of LegalDocument entities
    
    Returns:
        Summary string
    """
    if not documents:
        return "Không tìm thấy tài liệu phù hợp."
    
    summary_parts = []
    for i, doc in enumerate(documents[:3], 1):  # Only show top 3
        summary = f"{i}. "
        if doc.article_id:
            summary += f"{doc.article_id} "
        if doc.score:
            summary += f"(độ liên quan: {doc.score:.2f}) "
        summary += f"- {doc.content[:80]}..."
        summary_parts.append(summary)
    
    return "\n".join(summary_parts)


# Template for multiple choice clarification
CLARIFICATION_MULTIPLE_CHOICE_TEMPLATE = """CÂU HỎI: {question}

Vui lòng chọn:
{choices}

Hoặc nhập câu trả lời của bạn:"""


def format_multiple_choice(question: str, choices: list[str]) -> str:
    """
    Format a multiple choice clarification question.
    
    Args:
        question: The clarification question
        choices: List of choice options
    
    Returns:
        Formatted question with choices
    
    Example:
        >>> formatted = format_multiple_choice(
        ...     "Bạn hỏi về loại xe nào?",
        ...     ["Xe máy", "Ô tô", "Xe tải"]
        ... )
    """
    choices_text = "\n".join([f"{i}. {choice}" for i, choice in enumerate(choices, 1)])
    return CLARIFICATION_MULTIPLE_CHOICE_TEMPLATE.format(
        question=question,
        choices=choices_text
    )
