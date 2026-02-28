# LLM Services Implementation Guide

## Overview

This layer implements concrete LLM services that adhere to the `ILLMService` interface. We use two different providers optimized for different use cases:

- **OpenAI (GPT-4o-mini)**: Smart, accurate, great for complex reasoning
- **Groq (LLama-3.1-8b)**: Fast, free, perfect for simple classification

## Architecture

```
app/infrastructure/external_services/
├── __init__.py
├── openai_service.py     # GPT-4o-mini implementation
└── groq_service.py       # LLama-3.1-8b implementation
```

## OpenAI Service

### When to Use
✅ Query rewriting (needs context understanding)  
✅ Answer generation (needs coherent responses)  
✅ Document grading (needs quality assessment)  
✅ Complex reasoning tasks

### Features
- Uses LangChain's `ChatOpenAI`
- Supports structured output via `with_structured_output()`
- Error handling with retry logic
- Comprehensive logging

### Usage

```python
from app.infrastructure.external_services import OpenAIService

# Initialize from settings
service = OpenAIService.from_settings()

# Or manually
service = OpenAIService(
    api_key="sk-...",
    model="gpt-4o-mini",
    temperature=0.1
)

# Basic generation
response = service.generate("Rewrite this query: Nó phạt bao nhiêu?")

# Structured output
from pydantic import BaseModel

class Intent(BaseModel):
    intent: str
    confidence: float

result = service.generate_structured(
    "Classify: Vượt đèn đỏ phạt bao nhiêu?",
    schema=Intent
)
print(result.intent)  # "legal"
```

## Groq Service

### When to Use
✅ Guardrails (safety checks)  
✅ Intent routing (classification)  
✅ Quick yes/no decisions  
✅ Speed-critical operations

### Features
- Ultra-fast inference (< 500ms typical)
- Free tier available
- Uses LangChain's `ChatGroq`
- JSON mode for structured output
- Rate limit handling

### Usage

```python
from app.infrastructure.external_services import GroqService

# Initialize from settings
service = GroqService.from_settings()

# Or manually
service = GroqService(
    api_key="gsk_...",
    model="llama-3.1-8b-instant",
    temperature=0.1
)

# Basic generation
response = service.generate("Is this safe: Hello world")

# Structured output
from pydantic import BaseModel

class SafetyCheck(BaseModel):
    is_safe: bool
    reason: str

result = service.generate_structured(
    "Check safety: Vượt đèn đỏ phạt bao nhiêu?",
    schema=SafetyCheck
)
print(result.is_safe)  # True
```

## Error Handling

Both services implement robust error handling:

```python
from app.domain.exceptions import (
    LLMConnectionError,
    LLMOutputError,
    LLMRateLimitError
)

try:
    response = service.generate(prompt)
except LLMConnectionError as e:
    # API connection failed
    logger.error(f"Connection failed: {e.message}")
    # Fallback to alternative service
    
except LLMRateLimitError as e:
    # Rate limit exceeded (mainly Groq)
    logger.warning(f"Rate limited, retry after {e.details['retry_after']}s")
    # Wait and retry
    
except LLMOutputError as e:
    # Invalid output format
    logger.error(f"Invalid output: {e.message}")
    # Use default response
```

## Configuration

Both services read from `settings.py`:

```python
# .env file
OPENAI_API_KEY=sk-proj-...
GROQ_API_KEY=gsk_...
SMART_LLM_MODEL=gpt-4o-mini
FAST_LLM_MODEL=llama-3.1-8b-instant
DEFAULT_TEMPERATURE=0.1
```

```python
# In code
from app.infrastructure.external_services import OpenAIService, GroqService

# Uses settings automatically
smart_llm = OpenAIService.from_settings()
fast_llm = GroqService.from_settings()
```

## Performance Comparison

| Metric | OpenAI (GPT-4o-mini) | Groq (LLama-3.1-8b) |
|--------|---------------------|---------------------|
| Speed | ~2-3 seconds | ~0.3-0.5 seconds |
| Quality | Excellent | Good |
| Cost | ~$0.15/1M input tokens | Free (with limits) |
| Use Case | Complex reasoning | Quick classification |

## Integration with Nodes

Example: Using different LLMs for different tasks

```python
class Container:
    def __init__(self):
        # Smart LLM for complex tasks
        self.smart_llm = OpenAIService.from_settings()
        
        # Fast LLM for simple tasks
        self.fast_llm = GroqService.from_settings()
        
        # Inject into nodes
        self.rewrite_node = RewriteNode(llm=self.smart_llm)
        self.router_node = RouterNode(llm=self.fast_llm)
        self.guardrails_node = GuardrailsNode(llm=self.fast_llm)
        self.generate_node = GenerateNode(llm=self.smart_llm)
```

## Logging

All operations are logged with `loguru`:

```
2024-02-06 10:30:00.123 | INFO     | openai_service:__init__:45 | OpenAI service initialized | model=gpt-4o-mini | temperature=0.1
2024-02-06 10:30:01.456 | DEBUG    | openai_service:generate:78 | Generating text with OpenAI | model=gpt-4o-mini | prompt_length=45
2024-02-06 10:30:02.789 | DEBUG    | openai_service:generate:98 | OpenAI generation successful | output_length=123
```

## Testing

Run the example file to test your setup:

```bash
# Make sure you have valid API keys in .env
python -m examples.llm_services_usage
```

Expected output:
```
==================================================
EXAMPLE 1: OpenAI - Basic Text Generation
==================================================
Response: Lỗi vượt đèn đỏ với ô tô phạt bao nhiêu?

==================================================
EXAMPLE 2: OpenAI - Structured Output
==================================================
Intent: legal
Confidence: 0.95
Reason: Câu hỏi về mức phạt vi phạm giao thông

...
```

## Troubleshooting

### OpenAI API Key Invalid
```
Error: Failed to initialize OpenAI service
```
**Solution**: Check that `OPENAI_API_KEY` in `.env` starts with `sk-`

### Groq Rate Limit
```
Error: Groq rate limit exceeded
```
**Solution**: Groq free tier has limits. Wait 60s or upgrade plan.

### Import Errors
```
ModuleNotFoundError: No module named 'langchain_openai'
```
**Solution**: Install dependencies: `pipenv install langchain-openai langchain-groq`

## Next Steps

After implementing LLM services:
1. ✅ Implement vector store (ChromaDB)
2. ✅ Implement graph store (Neo4j)
3. ✅ Create application nodes using these services
4. ✅ Wire everything in Container

---

**Tech Stack:**
- LangChain Core
- LangChain OpenAI
- LangChain Groq
- Pydantic (for schemas)
- Loguru (for logging)
