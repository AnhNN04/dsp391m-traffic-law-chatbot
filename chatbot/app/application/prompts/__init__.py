"""
Prompts Package

Centralized prompt templates for all agent nodes.
All prompts are maintained here for easy management and updates.
"""

from app.application.prompts.rewrite_prompt import (
    REWRITE_PROMPT_TEMPLATE,
    REWRITE_SYSTEM_MESSAGE,
    REWRITE_SIMPLE_TEMPLATE,
    format_chat_history_for_rewrite
)

from app.application.prompts.router_prompt import (
    ROUTER_PROMPT_TEMPLATE,
    ROUTER_SYSTEM_MESSAGE,
    ROUTER_SIMPLE_TEMPLATE,
    IntentClassification,
    ROUTER_EXAMPLES,
    get_router_examples_text
)

from app.application.prompts.generate_prompt import (
    GENERATE_PROMPT_TEMPLATE,
    GENERATE_WITH_HISTORY_TEMPLATE,
    GENERATE_SHORT_TEMPLATE,
    GENERATE_SYSTEM_MESSAGE,
    GENERATE_SIMPLE_TEMPLATE,
    format_documents_for_context,
    get_data_source_label
)

from app.application.prompts.clarification_prompt import (
    CLARIFICATION_PROMPT_TEMPLATE,
    CLARIFICATION_SYSTEM_MESSAGE,
    CLARIFICATION_SIMPLE_TEMPLATE,
    ClarificationQuestion,
    CLARIFICATION_PATTERNS,
    get_predefined_clarification,
    detect_missing_info,
    format_documents_summary,
    format_multiple_choice
)

__all__ = [
    # Rewrite
    "REWRITE_PROMPT_TEMPLATE",
    "REWRITE_SYSTEM_MESSAGE",
    "REWRITE_SIMPLE_TEMPLATE",
    "format_chat_history_for_rewrite",
    
    # Router
    "ROUTER_PROMPT_TEMPLATE",
    "ROUTER_SYSTEM_MESSAGE",
    "ROUTER_SIMPLE_TEMPLATE",
    "IntentClassification",
    "ROUTER_EXAMPLES",
    "get_router_examples_text",
    
    # Generate
    "GENERATE_PROMPT_TEMPLATE",
    "GENERATE_WITH_HISTORY_TEMPLATE",
    "GENERATE_SHORT_TEMPLATE",
    "GENERATE_SYSTEM_MESSAGE",
    "GENERATE_SIMPLE_TEMPLATE",
    "format_documents_for_context",
    "get_data_source_label",
    
    # Clarification
    "CLARIFICATION_PROMPT_TEMPLATE",
    "CLARIFICATION_SYSTEM_MESSAGE",
    "CLARIFICATION_SIMPLE_TEMPLATE",
    "ClarificationQuestion",
    "CLARIFICATION_PATTERNS",
    "get_predefined_clarification",
    "detect_missing_info",
    "format_documents_summary",
    "format_multiple_choice"
]
