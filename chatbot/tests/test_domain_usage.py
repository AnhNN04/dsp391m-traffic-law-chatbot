"""
Domain Layer Usage Examples

This file demonstrates how to use the domain entities, state, and exceptions.
"""

from app.domain import (
    LegalDocument,
    Violation,
    ViolationType,
    VehicleType,
    DocumentSource,
    create_legal_document,
    create_violation,
    AgentState,
    create_initial_state,
    get_last_user_message, # impelemt when ingest to graph and interact with user's chat history
    has_sufficient_context,
    DatabaseConnectionError,
    LLMOutputError,
    get_error_category,
    should_retry
)


def example_legal_document():
    """Example: Creating and using LegalDocument entities."""
    print("=" * 60)
    print("EXAMPLE 1: Legal Document")
    print("=" * 60)
    
    # Create a legal document
    doc = LegalDocument(
        content="Điều 5. Phạt tiền từ 4.000.000 đồng đến 6.000.000 đồng đối với người điều khiển xe mô tô, xe gắn máy vi phạm quy định về chấp hành hiệu lệnh của đèn tín hiệu giao thông.",
        source=DocumentSource.VECTOR_STORE,
        metadata={
            "law": "Nghị định 100/2019/NĐ-CP",
            "chapter": 2,
            "effective_date": "2020-01-01"
        },
        score=0.89,
        article_id="Điều 5",
        law_name="Nghị định 100/2019/NĐ-CP"
    )
    
    print(f"Content: {doc.content[:100]}...")
    print(f"Source: {doc.source.value}")
    print(f"Score: {doc.score}")
    print(f"Citation: {doc.get_citation()}")
    print(f"Is Relevant (>0.7): {doc.is_relevant()}")
    print()
    
    # Factory function
    doc2 = create_legal_document(
        content="Sample legal text",
        source=DocumentSource.WEB_SEARCH,
        article_id="Điều 10"
    )
    print(f"Doc 2 Citation: {doc2.get_citation()}")
    print()


def example_violation():
    """Example: Creating and using Violation entities."""
    print("=" * 60)
    print("EXAMPLE 2: Violation")
    print("=" * 60)
    
    # Create a violation manually
    violation = Violation(
        violation_name="Vượt đèn đỏ",
        violation_type=ViolationType.RED_LIGHT,
        penalty_min=4_000_000,
        penalty_max=6_000_000,
        law_article="Điều 5 Nghị định 100/2019/NĐ-CP",
        vehicle_type=VehicleType.MOTORCYCLE,
        additional_penalties="Tước GPLX 1-3 tháng",
        description="Không chấp hành hiệu lệnh đèn đỏ"
    )
    
    print(f"Name: {violation.violation_name}")
    print(f"Type: {violation.violation_type.value}")
    print(f"Penalty Range: {violation.get_penalty_range()}")
    print(f"Is Severe (>5M): {violation.is_severe()}")
    print(f"\nFull Description:\n{violation.get_full_description()}")
    print()
    
    # Factory function with type inference
    violation2 = create_violation(
        violation_name="Không đội mũ bảo hiểm",
        penalty_min=100_000,
        penalty_max=200_000,
        law_article="Điều 6 ND 100"
    )
    print(f"\nViolation 2 (inferred type): {violation2.violation_type.value}")
    print()


def example_agent_state():
    """Example: Working with AgentState."""
    print("=" * 60)
    print("EXAMPLE 3: Agent State")
    print("=" * 60)
    
    # Create initial state
    state = create_initial_state(
        session_id="session_123",
        user_id="user_456"
    )
    
    print(f"Session ID: {state['session_id']}")
    print(f"User ID: {state['user_id']}")
    print(f"Initial Intent: {state['intent']}")
    print(f"Initial Data Source: {state['data_source']}")
    print()
    
    # Simulate adding documents
    state["documents"] = [
        create_legal_document("Document 1", score=0.85),
        create_legal_document("Document 2", score=0.45)
    ]
    
    print(f"Has Sufficient Context: {has_sufficient_context(state)}")
    print(f"Number of Documents: {len(state['documents'])}")
    print()


def example_exceptions():
    """Example: Using custom exceptions."""
    print("=" * 60)
    print("EXAMPLE 4: Exceptions")
    print("=" * 60)
    
    # Database connection error
    try:
        raise DatabaseConnectionError(
            "Failed to connect to MongoDB",
            database_type="MongoDB",
            connection_string="mongodb://user:password@localhost:27017",
            error_code=111
        )
    except DatabaseConnectionError as e:
        print(f"Error: {e.message}")
        print(f"Details: {e.details}")
        print(f"Category: {get_error_category(e)}")
        print(f"Should Retry: {should_retry(e)}")
    print()
    
    # LLM output error
    try:
        raise LLMOutputError(
            "Expected JSON but got text",
            output="This is plain text instead of JSON",
            expected_format="JSON"
        )
    except LLMOutputError as e:
        print(f"\nError: {e.message}")
        print(f"Output: {e.details.get('output')}")
        print(f"Expected: {e.details.get('expected_format')}")
        print(f"Should Retry: {should_retry(e)}")
    print()


def example_serialization():
    """Example: Converting entities to/from dictionaries."""
    print("=" * 60)
    print("EXAMPLE 5: Serialization")
    print("=" * 60)
    
    # Create and serialize a document
    doc = create_legal_document(
        content="Sample content",
        source=DocumentSource.DATABASE,
        score=0.92
    )
    
    doc_dict = doc.to_dict()
    print("Document as dict:")
    print(doc_dict)
    print()
    
    # Deserialize back
    doc_restored = LegalDocument.from_dict(doc_dict)
    print(f"Restored document content: {doc_restored.content}")
    print(f"Restored source: {doc_restored.source.value}")
    print()
    
    # Same for violation
    violation = create_violation(
        violation_name="Quá tốc độ",
        penalty_min=2_000_000,
        penalty_max=4_000_000,
        law_article="Điều 7 ND 100",
        vehicle_type=VehicleType.CAR
    )
    
    violation_dict = violation.to_dict()
    violation_restored = Violation.from_dict(violation_dict)
    print(f"Violation: {violation_restored.violation_name}")
    print(f"Vehicle: {violation_restored.vehicle_type.value}")
    print()


if __name__ == "__main__":
    example_legal_document()
    example_violation()
    example_agent_state()
    example_exceptions()
    example_serialization()
    
    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
