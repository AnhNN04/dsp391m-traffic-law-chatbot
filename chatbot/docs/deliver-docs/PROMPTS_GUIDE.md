# Prompts Management Guide

## Overview

This module centralizes all prompt templates used throughout the Traffic Law Agent system. By keeping prompts in one place, we ensure:

✅ **Consistency** - All nodes use the same formatting  
✅ **Maintainability** - Easy to update prompts  
✅ **Testability** - Prompts can be tested independently  
✅ **Version Control** - Track prompt changes over time

## Architecture

```
app/application/prompts/
├── __init__.py
├── rewrite_prompt.py        # Query rewriting
├── router_prompt.py          # Intent classification
├── generate_prompt.py        # Answer generation
└── clarification_prompt.py   # Clarification questions
```

## Prompt Files

### 1. Rewrite Prompt

**File:** `rewrite_prompt.py`  
**Purpose:** Resolve pronouns and add context from chat history  
**Node:** Rewrite Node  
**LLM:** OpenAI GPT-4o-mini (needs good context understanding)

**What it does:**
- Converts "Nó phạt bao nhiêu?" → "Lỗi vượt đèn đỏ với xe máy phạt bao nhiêu?"
- Resolves pronouns: nó, cái đó, lỗi trên
- Adds missing context from previous messages

**Usage:**
```python
from app.application.prompts import REWRITE_PROMPT_TEMPLATE
from langchain_core.messages import HumanMessage, AIMessage

chat_history = [
    HumanMessage(content="Vượt đèn đỏ phạt bao nhiêu?"),
    AIMessage(content="Phạt 4-6 triệu với xe máy."),
]

prompt = REWRITE_PROMPT_TEMPLATE.format_messages(
    chat_history=chat_history,
    question="Còn ô tô thì sao?"
)

rewritten = llm.generate(prompt[-1].content)
# Result: "Lỗi vượt đèn đỏ với ô tô phạt bao nhiêu?"
```

**Key Features:**
- Uses `MessagesPlaceholder` for dynamic history
- Maximum 3 message pairs (6 messages) for context
- Helper: `format_chat_history_for_rewrite()`

### 2. Router Prompt

**File:** `router_prompt.py`  
**Purpose:** Classify user intent (legal/procedure/chitchat)  
**Node:** Router Node  
**LLM:** Groq Llama-3 (fast classification)

**Intent Categories:**
- **legal**: Questions about laws, penalties, regulations
- **procedure**: Questions about administrative procedures
- **chitchat**: Greetings, thanks, off-topic

**Usage:**
```python
from app.application.prompts import (
    ROUTER_PROMPT_TEMPLATE,
    IntentClassification
)

prompt = ROUTER_PROMPT_TEMPLATE.format_messages(
    query="Vượt đèn đỏ phạt bao nhiêu?"
)

result = llm.generate_structured(
    prompt[-1].content,
    schema=IntentClassification
)

print(result.intent)      # "legal"
print(result.confidence)  # 0.95
print(result.reasoning)   # "Hỏi về mức phạt vi phạm"
```

**Structured Output:**
```python
class IntentClassification(BaseModel):
    intent: str  # "legal", "procedure", or "chitchat"
    confidence: float  # 0.0 to 1.0
    reasoning: str  # Explanation
```

**Examples Provided:**
- 6 pre-defined examples for few-shot learning
- Access via `ROUTER_EXAMPLES`

### 3. Generate Prompt

**File:** `generate_prompt.py`  
**Purpose:** Generate final answer with strict citation  
**Node:** Generate Node  
**LLM:** OpenAI GPT-4o-mini (needs good reasoning)

**Critical Rules:**
1. ✅ **MUST cite sources** - Every fact must reference an article
2. ✅ **Use ONLY provided context** - No external knowledge
3. ✅ **No fabrication** - Don't make up information
4. ✅ **Clear citations** - "Theo Điều X Nghị định Y..."

**Usage:**
```python
from app.application.prompts import (
    GENERATE_PROMPT_TEMPLATE,
    format_documents_for_context,
    get_data_source_label
)

# Format documents
context = format_documents_for_context(documents)
source = get_data_source_label("vector_store")

# Generate prompt
prompt = GENERATE_PROMPT_TEMPLATE.format_messages(
    question="Vượt đèn đỏ xe máy phạt bao nhiêu?",
    context=context,
    data_source=source
)

answer = llm.generate(prompt[-1].content)
# Result: "Theo Điều 5 Nghị định 100/2019/NĐ-CP, lỗi vượt đèn đỏ..."
```

**Citation Format Examples:**
```
✅ GOOD:
"Theo Điều 5 Nghị định 100/2019/NĐ-CP, mức phạt là 4-6 triệu đồng."

❌ BAD:
"Mức phạt là 4-6 triệu đồng." (No citation)
```

**Variants:**
- `GENERATE_PROMPT_TEMPLATE` - Standard answer
- `GENERATE_WITH_HISTORY_TEMPLATE` - Includes chat history
- `GENERATE_SHORT_TEMPLATE` - Concise answers

**Helper Functions:**
- `format_documents_for_context()` - Format docs with numbering
- `get_data_source_label()` - Human-readable source label

### 4. Clarification Prompt

**File:** `clarification_prompt.py`  
**Purpose:** Generate questions when info is missing  
**Node:** Ask Human Node  
**LLM:** OpenAI GPT-4o-mini (needs good question generation)

**When to Use:**
- Query missing vehicle type
- Query missing violation type
- Ambiguous references ("đèn" without color)
- Need to confirm understanding

**Usage:**
```python
from app.application.prompts import (
    CLARIFICATION_PROMPT_TEMPLATE,
    detect_missing_info,
    get_predefined_clarification,
    format_multiple_choice
)

# Auto-detect pattern
pattern = detect_missing_info("Phạt bao nhiêu?")
# Returns: "missing_vehicle_type"

# Get predefined clarification
clarification = get_predefined_clarification(pattern)
print(clarification["question"])
# "Bạn đang hỏi về loại xe nào?"

print(clarification["suggestions"])
# ["Xe máy", "Ô tô", "Xe tải", "Xe khách"]

# Format as multiple choice
formatted = format_multiple_choice(
    clarification["question"],
    clarification["suggestions"]
)
```

**Predefined Patterns:**
- `missing_vehicle_type` - No vehicle specified
- `missing_violation_type` - No violation specified
- `ambiguous_light` - "đèn" without color
- `missing_location` - No location context
- `missing_time_context` - Unclear timeframe

**Custom Clarification:**
```python
prompt = CLARIFICATION_PROMPT_TEMPLATE.format_messages(
    original_query="Cái này phạt bao nhiêu?",
    issue="Không rõ 'cái này' là gì",
    documents_summary="Không có tài liệu phù hợp"
)

clarification = llm.generate(prompt[-1].content)
```

## Best Practices

### 1. Always Use Templates

❌ **DON'T** - Hardcode prompts in nodes:
```python
# Bad
response = llm.generate("Viết lại câu hỏi này: " + query)
```

✅ **DO** - Use centralized templates:
```python
# Good
from app.application.prompts import REWRITE_PROMPT_TEMPLATE

prompt = REWRITE_PROMPT_TEMPLATE.format_messages(
    chat_history=history,
    question=query
)
response = llm.generate(prompt[-1].content)
```

### 2. Format Documents Properly

✅ Always use helper functions:
```python
from app.application.prompts import format_documents_for_context

context = format_documents_for_context(docs)
# Properly formatted with numbering and scores
```

### 3. Structured Output When Possible

For classification/routing, use Pydantic schemas:
```python
from app.application.prompts import IntentClassification

result = llm.generate_structured(prompt, schema=IntentClassification)
# Returns typed object, not raw text
```

### 4. Validate Citations

When testing generate prompt:
```python
answer = llm.generate(prompt)

# Check for citations
assert "Theo Điều" in answer or "Nghị định" in answer
assert not answer.startswith("Mức phạt là")  # No citation at start
```

## Testing Prompts

Run the examples:
```bash
python -m examples.prompts_usage
```

Expected output:
```
EXAMPLE 1: Rewrite Prompt
Original: "Còn ô tô thì sao?"
Rewritten: "Lỗi vượt đèn đỏ với ô tô phạt bao nhiêu?"

EXAMPLE 2: Router Prompt
Query: "Vượt đèn đỏ phạt bao nhiêu?"
Intent: legal
Confidence: 0.95
```

## Updating Prompts

When updating prompts, follow this workflow:

1. **Update the prompt file** (e.g., `generate_prompt.py`)
2. **Test with examples**: `python -m examples.prompts_usage`
3. **Test in nodes**: Run node tests
4. **Version control**: Commit with clear message

```bash
# Example commit message
git commit -m "prompts: improve generate prompt citation requirements

- Added explicit examples of good vs bad citations
- Strengthened warning against fabrication
- Added disclaimer for web search results"
```

## Prompt Engineering Tips

### For Rewrite Prompt:
- Keep context window small (3 pairs max)
- Emphasize "don't answer, just rewrite"
- Provide diverse examples

### For Router Prompt:
- Use few-shot learning with examples
- Make categories mutually exclusive
- Prefer legal over procedure when ambiguous

### For Generate Prompt:
- Strict citation requirements
- Show good vs bad examples
- Handle different data sources differently

### For Clarification Prompt:
- Keep questions short and friendly
- Provide answer suggestions when possible
- Avoid asking multiple things at once

## Common Issues

### Issue: Rewrite doesn't preserve meaning
**Solution:** Add more examples to `REWRITE_SYSTEM_MESSAGE`

### Issue: Router misclassifies intent
**Solution:** Update `ROUTER_EXAMPLES` with edge cases

### Issue: Generate doesn't cite sources
**Solution:** Add stricter warnings and more examples

### Issue: Clarification is too formal
**Solution:** Update examples with more casual phrasing

## Integration with Nodes

Each prompt is designed for a specific node:

```python
# In RewriteNode
from app.application.prompts import REWRITE_PROMPT_TEMPLATE

class RewriteNode:
    def __call__(self, state):
        prompt = REWRITE_PROMPT_TEMPLATE.format_messages(...)
        return llm.generate(prompt[-1].content)

# In RouterNode
from app.application.prompts import ROUTER_PROMPT_TEMPLATE, IntentClassification

class RouterNode:
    def __call__(self, state):
        prompt = ROUTER_PROMPT_TEMPLATE.format_messages(...)
        return llm.generate_structured(prompt, IntentClassification)

# In GenerateNode
from app.application.prompts import GENERATE_PROMPT_TEMPLATE

class GenerateNode:
    def __call__(self, state):
        prompt = GENERATE_PROMPT_TEMPLATE.format_messages(...)
        return llm.generate(prompt[-1].content)
```

## Performance Metrics

Track prompt effectiveness:
- **Rewrite accuracy**: Are pronouns resolved correctly?
- **Router accuracy**: Is intent classified correctly?
- **Generate quality**: Are citations present? Is info accurate?
- **Clarification rate**: How often do we need clarification?

---

**Remember:** Good prompts are the foundation of a good LLM application. Invest time in crafting and testing them!
