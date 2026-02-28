"""
Router Prompt

Prompt template for intent classification.
Used in the Router Node to determine query intent (legal/procedure/chitchat).

Author: AnhNN217-FHN
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


# Pydantic schema for structured output
class IntentClassification(BaseModel):
    """Structured output for intent classification."""
    
    intent: str = Field(
        description="Classified intent: 'legal', 'procedure', or 'chitchat'"
    )
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0"
    )
    reasoning: str = Field(
        description="Brief explanation for the classification"
    )


# System message for intent classification
ROUTER_SYSTEM_MESSAGE = """Bạn là hệ thống phân loại ý định câu hỏi về luật giao thông.

NHIỆM VỤ:
Phân loại câu hỏi người dùng vào MỘT trong các loại sau:

1. **legal** - Hỏi về LUẬT, QUY ĐỊNH, MỨC PHẠT
   Ví dụ:
   - "Vượt đèn đỏ phạt bao nhiêu?"
   - "Điều 5 Nghị định 100 quy định gì?"
   - "Không đội mũ bảo hiểm có bị phạt không?"
   - "Luật giao thông mới nhất ra sao?"

2. **procedure** - Hỏi về THỦ TỤC HÀNH CHÍNH
   Ví dụ:
   - "Làm sao để đóng phạt nguội?"
   - "Nộp phạt vi phạm giao thông ở đâu?"
   - "Thủ tục cấp lại bằng lái như thế nào?"
   - "Tôi bị tước bằng lái, làm gì để lấy lại?"

3. **chitchat** - CHÀO HỎI, TÁN GẪU, KHÔNG LIÊN QUAN
   Ví dụ:
   - "Xin chào"
   - "Bạn là ai?"
   - "Cảm ơn bạn"
   - "Thời tiết hôm nay thế nào?"

QUY TẮC PHÂN LOẠI:
- Nếu hỏi về MỨC PHẠT, LUẬT LỆ, QUY ĐỊNH → "legal"
- Nếu hỏi về THỦ TỤC, CÁCH LÀM, Ở ĐÂU → "procedure"
- Nếu CHÀO HỎI, CẢM ƠN, TÁN GẪU → "chitchat"
- Khi KHÔNG CHẮC CHẮN, ưu tiên "legal" hơn "procedure"

ĐỊNH DẠNG ĐẦU RA:
Trả về JSON với 3 trường:
- intent: "legal" / "procedure" / "chitchat"
- confidence: 0.0 đến 1.0
- reasoning: Giải thích ngắn gọn (1 câu)"""


# Human message template
ROUTER_HUMAN_MESSAGE = """Phân loại câu hỏi sau:

"{query}"

Trả về JSON với intent, confidence, và reasoning."""


# ChatPromptTemplate for router
ROUTER_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", ROUTER_SYSTEM_MESSAGE),
    ("human", ROUTER_HUMAN_MESSAGE)
])


# Simple string template (fallback)
ROUTER_SIMPLE_TEMPLATE = """Phân loại câu hỏi về luật giao thông vào một trong các loại:

1. legal - Hỏi về luật, quy định, mức phạt
2. procedure - Hỏi về thủ tục hành chính
3. chitchat - Chào hỏi, tán gẫu

CÂU HỎI:
{query}

Trả về JSON:
{{
  "intent": "legal/procedure/chitchat",
  "confidence": 0.95,
  "reasoning": "Giải thích ngắn gọn"
}}

JSON:"""


# Examples for few-shot learning (if needed)
ROUTER_EXAMPLES = [
    {
        "query": "Vượt đèn đỏ phạt bao nhiêu?",
        "intent": "legal",
        "confidence": 0.98,
        "reasoning": "Hỏi về mức phạt vi phạm giao thông"
    },
    {
        "query": "Đóng phạt nguội ở đâu?",
        "intent": "procedure",
        "confidence": 0.95,
        "reasoning": "Hỏi về địa điểm thực hiện thủ tục"
    },
    {
        "query": "Xin chào",
        "intent": "chitchat",
        "confidence": 0.99,
        "reasoning": "Lời chào hỏi đơn giản"
    },
    {
        "query": "Điều 5 quy định gì?",
        "intent": "legal",
        "confidence": 0.97,
        "reasoning": "Hỏi về nội dung quy định pháp luật"
    },
    {
        "query": "Làm sao để lấy lại bằng lái?",
        "intent": "procedure",
        "confidence": 0.96,
        "reasoning": "Hỏi về quy trình thủ tục hành chính"
    },
    {
        "query": "Cảm ơn bạn đã giúp đỡ",
        "intent": "chitchat",
        "confidence": 0.99,
        "reasoning": "Lời cảm ơn, không liên quan đến luật"
    }
]


def get_router_examples_text() -> str:
    """
    Get formatted examples for few-shot prompting.
    
    Returns:
        Formatted examples string
    """
    examples_text = "VÍ DỤ:\n\n"
    for ex in ROUTER_EXAMPLES:
        examples_text += f"Câu hỏi: \"{ex['query']}\"\n"
        examples_text += f"Intent: {ex['intent']}\n"
        examples_text += f"Confidence: {ex['confidence']}\n"
        examples_text += f"Reasoning: {ex['reasoning']}\n\n"
    
    return examples_text
