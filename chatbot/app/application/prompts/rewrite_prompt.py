"""
Query Rewrite Prompt

Prompt template for rewriting user queries with full context.
Used in the Rewrite Node to resolve pronouns and add context from chat history.

Author: AnhNN217-FHN
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


# System message for the rewrite task
REWRITE_SYSTEM_MESSAGE = """Bạn là trợ lý chuyên viết lại câu hỏi để làm rõ ngữ cảnh.

NHIỆM VỤ:
Viết lại câu hỏi cuối cùng của người dùng sao cho nó có đầy đủ ý nghĩa mà KHÔNG CẦN đọc lịch sử chat.

QUY TẮC:
1. Thay thế đại từ nhân xưng (nó, cái đó, lỗi trên...) bằng thực thể cụ thể
2. Bổ sung thông tin từ các câu trước nếu cần thiết
3. Giữ nguyên ý định của câu hỏi gốc
4. KHÔNG trả lời câu hỏi, chỉ viết lại
5. CHỈ trả về câu hỏi đã viết lại, KHÔNG giải thích

VÍ DỤ:
---
Lịch sử:
User: "Vượt đèn đỏ phạt bao nhiêu?"
Bot: "Phạt từ 4-6 triệu đồng với xe máy."
User: "Còn ô tô thì sao?"

Câu hỏi viết lại: "Lỗi vượt đèn đỏ với ô tô phạt bao nhiêu?"
---

Lịch sử:
User: "Cho tôi biết về Điều 5 Nghị định 100."
Bot: "Điều 5 quy định về lỗi vượt đèn đỏ..."
User: "Nó áp dụng cho xe nào?"

Câu hỏi viết lại: "Điều 5 Nghị định 100 áp dụng cho loại xe nào?"
---

Lịch sử:
User: "Không đội mũ bảo hiểm bị phạt bao nhiêu?"
Bot: "Phạt 100,000 - 200,000 đồng."
User: "Còn phạt gì khác không?"

Câu hỏi viết lại: "Lỗi không đội mũ bảo hiểm còn có hình phạt bổ sung gì khác không?"
---"""


# Human message template
REWRITE_HUMAN_MESSAGE = """Dựa vào lịch sử hội thoại, hãy viết lại câu hỏi cuối cùng:

{question}

CHỈ trả về câu hỏi đã viết lại, KHÔNG giải thích."""


# ChatPromptTemplate with message history
REWRITE_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", REWRITE_SYSTEM_MESSAGE),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", REWRITE_HUMAN_MESSAGE)
])


# Simple string template (fallback if not using LangChain)
REWRITE_SIMPLE_TEMPLATE = """Bạn là trợ lý chuyên viết lại câu hỏi để làm rõ ngữ cảnh.

NHIỆM VỤ: Viết lại câu hỏi cuối cùng sao cho có đầy đủ ý nghĩa mà không cần đọc lịch sử.

QUY TẮC:
- Thay thế đại từ nhân xưng bằng thực thể cụ thể
- Bổ sung thông tin từ các câu trước
- KHÔNG trả lời câu hỏi, chỉ viết lại
- CHỈ trả về câu hỏi đã viết lại

LỊCH SỬ HỘI THOẠI:
{chat_history}

CÂU HỎI CẦN VIẾT LẠI:
{question}

CÂU HỎI ĐÃ VIẾT LẠI:"""


def format_chat_history_for_rewrite(messages: list, max_pairs: int = 3) -> str:
    """
    Format chat history for the rewrite prompt.
    
    Takes the last N message pairs and formats them for context.
    
    Args:
        messages: List of message objects
        max_pairs: Maximum number of user-bot pairs to include
    
    Returns:
        Formatted chat history string
    
    Example:
        >>> history = format_chat_history_for_rewrite(messages, max_pairs=2)
        >>> print(history)
        User: "Vượt đèn đỏ phạt bao nhiêu?"
        Bot: "Phạt 4-6 triệu với xe máy"
        User: "Còn ô tô thì sao?"
    """
    if not messages:
        return ""
    
    # Take last N*2 messages (N pairs)
    recent_messages = messages[-(max_pairs * 2):]
    
    formatted_lines = []
    for msg in recent_messages:
        if hasattr(msg, 'type'):
            role = "User" if msg.type == "human" else "Bot"
            content = msg.content
        elif isinstance(msg, dict):
            role = "User" if msg.get("type") == "human" else "Bot"
            content = msg.get("content", "")
        else:
            continue
        
        formatted_lines.append(f'{role}: "{content}"')
    
    return "\n".join(formatted_lines)
