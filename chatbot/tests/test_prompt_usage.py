"""
Prompts Usage Examples

Demonstrates how to use the centralized prompt templates.

Run with:
    python -m tests.test_prompt_usage
"""

from langchain_core.messages import HumanMessage, AIMessage

from app.application.prompts import (
    REWRITE_PROMPT_TEMPLATE,
    format_chat_history_for_rewrite,
    ROUTER_PROMPT_TEMPLATE,
    IntentClassification,
    GENERATE_PROMPT_TEMPLATE,
    format_documents_for_context,
    get_data_source_label,
    CLARIFICATION_PROMPT_TEMPLATE,
    get_predefined_clarification,
    detect_missing_info,
    format_multiple_choice
)
from app.domain.entities import LegalDocument, DocumentSource
from app.infrastructure.external_services import OpenAIService, GroqService
from app.infrastructure.config import setup_logger


def example_rewrite_prompt():
    """Example 1: Query rewriting with conversation history."""
    print("=" * 60)
    print("EXAMPLE 1: Rewrite Prompt")
    print("=" * 60)
    
    # Simulate conversation history
    chat_history = [
        HumanMessage(content="Vượt đèn đỏ phạt bao nhiêu?"),
        AIMessage(content="Phạt từ 4-6 triệu đồng với xe máy."),
        HumanMessage(content="Còn ô tô thì sao?")
    ]
    
    # Format with template
    prompt = REWRITE_PROMPT_TEMPLATE.format_messages(
        chat_history=chat_history[:-1],  # Exclude last message
        question=chat_history[-1].content
    )
    
    print("Chat History:")
    history_text = format_chat_history_for_rewrite(chat_history[:-1])
    print(history_text)
    print()
    
    print("Original Question:")
    print(f'"{chat_history[-1].content}"')
    print()
    
    print("Prompt to LLM:")
    print(f"{prompt[-1].content[:200]}...")
    print()
    
    # Use with LLM
    try:
        llm = OpenAIService.from_settings()
        response = llm.generate(prompt[-1].content)
        print("Rewritten Query:")
        print(f'"{response}"')
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
    
    print()


def example_router_prompt():
    """Example 2: Intent classification."""
    print("=" * 60)
    print("EXAMPLE 2: Router Prompt")
    print("=" * 60)
    
    test_queries = [
        "Vượt đèn đỏ phạt bao nhiêu?",
        "Làm sao để đóng phạt nguội?",
        "Xin chào",
        "Điều 5 quy định gì?"
    ]
    
    try:
        llm = GroqService.from_settings()
        
        for query in test_queries:
            print(f'Query: "{query}"')
            
            # Format prompt
            prompt = ROUTER_PROMPT_TEMPLATE.format_messages(query=query)
            
            # Use structured output
            result = llm.generate_structured(
                prompt[-1].content,
                schema=IntentClassification
            )
            
            print(f"Intent: {result.intent}")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Reasoning: {result.reasoning}")
            print()
    
    except Exception as e:
        print(f"❌ Router example failed: {e}")
        print("Using predefined examples:")
        from app.application.prompts import ROUTER_EXAMPLES
        for ex in ROUTER_EXAMPLES[:3]:
            print(f'Query: "{ex["query"]}"')
            print(f'Intent: {ex["intent"]}')
            print()
    
    print()


def example_generate_prompt():
    """Example 3: Answer generation with citation."""
    print("=" * 60)
    print("EXAMPLE 3: Generate Prompt")
    print("=" * 60)
    
    # Simulate retrieved documents
    docs = [
        LegalDocument(
            content="Điều 5. Phạt tiền từ 4.000.000 đồng đến 6.000.000 đồng đối với người điều khiển xe mô tô vi phạm quy định về chấp hành hiệu lệnh của đèn tín hiệu giao thông. Ngoài ra, người vi phạm còn bị tước Giấy phép lái xe từ 1 đến 3 tháng.",
            source=DocumentSource.VECTOR_STORE,
            article_id="Điều 5",
            law_name="Nghị định 100/2019/NĐ-CP",
            score=0.95
        ),
        LegalDocument(
            content="Điều 6. Phạt tiền từ 6.000.000 đồng đến 8.000.000 đồng đối với người điều khiển xe ô tô vi phạm quy định về chấp hành hiệu lệnh của đèn đỏ.",
            source=DocumentSource.VECTOR_STORE,
            article_id="Điều 6",
            law_name="Nghị định 100/2019/NĐ-CP",
            score=0.92
        )
    ]
    
    question = "Vượt đèn đỏ với xe máy phạt bao nhiêu?"
    
    # Format context
    context = format_documents_for_context(docs)
    data_source = get_data_source_label("vector_store")
    
    print("Question:")
    print(question)
    print()
    
    print("Context:")
    print(context)
    print()
    
    print("Data Source:")
    print(data_source)
    print()
    
    # Format prompt
    prompt = GENERATE_PROMPT_TEMPLATE.format_messages(
        question=question,
        context=context,
        data_source=data_source
    )
    
    try:
        llm = OpenAIService.from_settings()
        response = llm.generate(prompt[-1].content)
        
        print("Generated Answer:")
        print(response)
    
    except Exception as e:
        print(f"❌ Generate failed: {e}")
        print("\nExpected answer format:")
        print('Theo Điều 5 Nghị định 100/2019/NĐ-CP, lỗi vượt đèn đỏ với xe máy bị phạt tiền từ 4.000.000 đến 6.000.000 đồng. Ngoài ra, người vi phạm còn bị tước Giấy phép lái xe từ 1 đến 3 tháng.')
    
    print()


def example_clarification_prompt():
    """Example 4: Clarification question generation."""
    print("=" * 60)
    print("EXAMPLE 4: Clarification Prompt")
    print("=" * 60)
    
    # Test ambiguous queries
    ambiguous_queries = [
        "Phạt bao nhiêu?",
        "Vượt đèn thì sao?",
        "Lỗi đó có bị phạt không?"
    ]
    
    for query in ambiguous_queries:
        print(f'Ambiguous Query: "{query}"')
        
        # Detect missing info
        pattern = detect_missing_info(query)
        print(f"Detected Pattern: {pattern}")
        
        # Get predefined clarification
        if pattern != "general":
            clarification = get_predefined_clarification(pattern)
            print(f'Clarification: "{clarification["question"]}"')
            
            if clarification.get("suggestions"):
                formatted = format_multiple_choice(
                    clarification["question"],
                    clarification["suggestions"]
                )
                print("\nFormatted for user:")
                print(formatted)
        
        print()
    
    # Use LLM for custom clarification
    print("Using LLM for custom clarification:")
    query = "Cái này phạt bao nhiêu?"
    
    prompt = CLARIFICATION_PROMPT_TEMPLATE.format_messages(
        original_query=query,
        issue="Không rõ 'cái này' là lỗi vi phạm gì",
        documents_summary="Không có tài liệu phù hợp"
    )
    
    try:
        llm = OpenAIService.from_settings()
        response = llm.generate(prompt[-1].content)
        
        print(f'Original: "{query}"')
        print(f'Clarification: "{response}"')
    
    except Exception as e:
        print(f"❌ Clarification failed: {e}")
    
    print()


def example_integration():
    """Example 5: Full integration (Rewrite -> Route -> Generate)."""
    print("=" * 60)
    print("EXAMPLE 5: Full Integration")
    print("=" * 60)
    
    # Simulate a conversation
    chat_history = [
        HumanMessage(content="Cho tôi biết về lỗi vượt đèn đỏ"),
        AIMessage(content="Lỗi vượt đèn đỏ là vi phạm nghiêm trọng..."),
        HumanMessage(content="Nó phạt bao nhiêu với xe máy?")
    ]
    
    print("Step 1: Rewrite Query")
    print("-" * 40)
    
    # Rewrite
    rewrite_prompt = REWRITE_PROMPT_TEMPLATE.format_messages(
        chat_history=chat_history[:-1],
        question=chat_history[-1].content
    )
    
    print(f'Original: "{chat_history[-1].content}"')
    
    try:
        llm = OpenAIService.from_settings()
        rewritten = llm.generate(rewrite_prompt[-1].content)
        print(f'Rewritten: "{rewritten}"')
        print()
        
        # Route
        print("Step 2: Route Intent")
        print("-" * 40)
        
        router_prompt = ROUTER_PROMPT_TEMPLATE.format_messages(query=rewritten)
        
        result = llm.generate_structured(
            router_prompt[-1].content,
            schema=IntentClassification
        )
        
        print(f"Intent: {result.intent}")
        print(f"Confidence: {result.confidence:.2f}")
        print()
        
        # Generate (with mock documents)
        print("Step 3: Generate Answer")
        print("-" * 40)
        
        mock_doc = LegalDocument(
            content="Điều 5. Phạt tiền từ 4.000.000 đến 6.000.000 đồng...",
            source=DocumentSource.DATABASE,
            article_id="Điều 5",
            law_name="Nghị định 100/2019/NĐ-CP",
            score=0.95
        )
        
        context = format_documents_for_context([mock_doc])
        
        generate_prompt = GENERATE_PROMPT_TEMPLATE.format_messages(
            question=rewritten,
            context=context,
            data_source="database"
        )
        
        answer = llm.generate(generate_prompt[-1].content)
        print("Answer:")
        print(answer)
    
    except Exception as e:
        print(f"❌ Integration example failed: {e}")
    
    print()


def main():
    """Run all examples."""
    
    setup_logger(log_level="INFO")
    
    print("\n")
    print("=" * 60)
    print("PROMPTS USAGE EXAMPLES")
    print("=" * 60)
    print()
    
    example_rewrite_prompt()
    example_router_prompt()
    example_generate_prompt()
    example_clarification_prompt()
    example_integration()
    
    print("=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
