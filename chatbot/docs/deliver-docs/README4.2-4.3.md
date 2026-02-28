# Application Nodes - Hướng Dẫn Sử Dụng

## 📋 Tổng Quan

Thư mục này chứa tất cả các **Node** (nút xử lý) trong LangGraph Agent Pipeline. Mỗi Node là một bước xử lý độc lập, nhận vào `AgentState` và trả về dict để update state.

## 🏗️ Kiến Trúc Node

### Base Node
Tất cả các Node kế thừa từ `BaseNode` để có:
- Logging tự động (entry/exit/error)
- State validation
- Error handling pattern

### Dependency Injection
Các Node nhận dependencies qua constructor (không hardcode):
```python
# ✅ Đúng
node = RewriteNode(smart_llm=openai_service)

# ❌ Sai
node = RewriteNode()  # Hardcode OpenAI trong node
```

## 📦 Danh Sách Nodes

### NODE 0: GuardrailsNode
**Mục đích:** Kiểm tra input an toàn trước khi xử lý

**Dependencies:**
- `fast_llm: ILLMService` (Groq)

**Input State:**
- `messages`

**Output State:**
- `is_blocked: bool` (nếu unsafe)
- `messages` (nếu block)

**Sử dụng:**
```python
from app.infrastructure.external_services.groq_service import GroqService
from app.application.nodes import GuardrailsNode

groq = GroqService(api_key="...", model="llama3-8b-8192")
node = GuardrailsNode(fast_llm=groq)

state = {"messages": [...]}
result = node(state)
```

---

### NODE 1: RewriteNode
**Mục đích:** Viết lại câu hỏi dựa trên lịch sử để làm rõ ngữ cảnh

**Dependencies:**
- `smart_llm: ILLMService` (GPT-4o-mini)

**Input State:**
- `messages`

**Output State:**
- `rewritten_query: str`

**Logic:**
- Nếu là câu hỏi đầu tiên → Giữ nguyên
- Nếu có lịch sử → Viết lại với context từ 3 cặp hội thoại gần nhất

---

### NODE 2: RouterNode
**Mục đích:** Phân loại intent để routing

**Dependencies:**
- `smart_llm: ILLMService`

**Input State:**
- `rewritten_query`

**Output State:**
- `intent: Literal["legal", "procedure", "chitchat"]`

**Routing Decision:**
- `legal` → Retrieval (tra cứu luật, mức phạt)
- `procedure` → Retrieval (thủ tục hành chính)
- `chitchat` → Generate (trả lời trực tiếp, không cần DB)

---

### NODE 3: RetrievalNode
**Mục đích:** Tìm kiếm Hybrid (Vector + Graph)

**Dependencies:**
- `vector_store: IVectorStore` (ChromaDB)
- `graph_store: IGraphStore` (Neo4j)

**Input State:**
- `rewritten_query`

**Output State:**
- `documents: List[LegalDocument]`
- `data_source: str` ("database")

**Logic:**
1. Vector search (top 5 docs)
2. Graph search (chính xác từ Neo4j)
3. Merge & deduplicate (ưu tiên Graph)

**Error Handling:**
- Nếu Graph fail → Fallback về Vector only
- Nếu cả 2 fail → Return empty list

---

### NODE 4: GradeNode
**Mục đích:** Đánh giá documents và quyết định next action

**Dependencies:**
- `smart_llm: ILLMService`

**Input State:**
- `rewritten_query`
- `documents`

**Output State:**
- `next_action: Literal["generate", "web_search", "ask_human"]`
- `grade_result: dict`

**Routing Logic:**
```
documents rỗng → web_search
documents có + thiếu info cụ thể → ask_human
documents có + mâu thuẫn → web_search
documents đầy đủ → generate
```

---

### NODE 5: AskHumanNode
**Mục đích:** Sinh câu hỏi làm rõ và trigger interrupt

**Dependencies:**
- `smart_llm: ILLMService`

**Input State:**
- `rewritten_query`
- `grade_result` (missing_info)

**Output State:**
- `clarification_question: str`
- `messages: [AIMessage]`

**QUAN TRỌNG:**
- Node này cần được config với `interrupt_before` hoặc `interrupt_after` trong Graph
- Sau khi return, Graph sẽ dừng và chờ user input
- User response sẽ được add vào messages và graph resume

---

### NODE 6: WebSearchNode
**Mục đích:** Tìm kiếm fallback từ Internet

**Dependencies:**
- `search_tool: ISearchTool` (Tavily)

**Input State:**
- `rewritten_query`

**Output State:**
- `documents: List[LegalDocument]`
- `data_source: str` ("internet")

**Trusted Domains:**
- thuvienphapluat.vn
- luatvietnam.vn
- baochinhphu.vn
- csgt.vn

---

### NODE 7: GenerateNode
**Mục đích:** Sinh câu trả lời cuối cùng

**Dependencies:**
- `smart_llm: ILLMService`

**Input State:**
- `rewritten_query`
- `documents`
- `data_source`

**Output State:**
- `messages: [AIMessage]`

**Nguyên tắc:**
- BẮT BUỘC trích dẫn nguồn
- Không bịa đặt thông tin
- Thêm disclaimer nếu từ web
- Ngôn ngữ chuyên nghiệp, dễ hiểu

---

## 🔧 Cách Sử Dụng Trong Graph

### Bước 1: Khởi tạo Dependencies (Container)
```python
from app.infrastructure.external_services import OpenAIService, GroqService
from app.infrastructure.persistence import ChromaRepo, Neo4jRepo
from app.application.nodes import *

# Init services
openai = OpenAIService(api_key="...", model="gpt-4o-mini")
groq = GroqService(api_key="...", model="llama3-8b-8192")
chroma = ChromaRepo(path="./data/chroma_db")
neo4j = Neo4jRepo(uri="bolt://...")

# Init nodes
guardrails = GuardrailsNode(fast_llm=groq)
rewrite = RewriteNode(smart_llm=openai)
router = RouterNode(smart_llm=openai)
retrieval = RetrievalNode(vector_store=chroma, graph_store=neo4j)
grade = GradeNode(smart_llm=openai)
ask_human = AskHumanNode(smart_llm=openai)
generate = GenerateNode(smart_llm=openai)
```

### Bước 2: Thêm vào Graph
```python
from langgraph.graph import StateGraph

graph = StateGraph(AgentState)

# Add nodes
graph.add_node("guardrails", guardrails)
graph.add_node("rewrite", rewrite)
graph.add_node("router", router)
graph.add_node("retrieval", retrieval)
graph.add_node("grade", grade)
graph.add_node("ask_human", ask_human)
graph.add_node("generate", generate)

# Add edges
graph.set_entry_point("guardrails")
graph.add_edge("guardrails", "rewrite")
graph.add_edge("rewrite", "router")

# Conditional edges
graph.add_conditional_edges(
    "router",
    lambda state: state["intent"],
    {
        "legal": "retrieval",
        "procedure": "retrieval",
        "chitchat": "generate"
    }
)

# ... more edges
```

## 🐛 Debug & Testing

### Test Từng Node Riêng Lẻ
```python
from app.domain.state import AgentState
from langchain_core.messages import HumanMessage

# Mock state
state: AgentState = {
    "messages": [HumanMessage(content="Vượt đèn đỏ phạt bao nhiêu?")],
    "rewritten_query": "",
    "intent": "legal",
    "documents": [],
    "data_source": "none",
    "clarification_question": None
}

# Test node
result = rewrite(state)
print(result)  # {"rewritten_query": "..."}
```

### Logging
Tất cả nodes đã tích hợp logging:
```
[Rewrite] 🎯 Starting | Last message: Vượt đèn đỏ phạt bao nhiêu?
[Rewrite] Original: 'Vượt đèn đỏ phạt bao nhiêu?' | Rewritten: 'Mức phạt lỗi vượt đèn đỏ là bao nhiêu?'
[Rewrite] ✅ Completed | Updates: ['rewritten_query']
```

## ⚠️ Lưu Ý Quan Trọng

1. **State Immutability:** Không mutate state trực tiếp, chỉ return dict update
2. **Error Handling:** Tất cả external calls phải bọc try-except
3. **Fallback:** Luôn có fallback logic khi service fail
4. **Type Hints:** Bắt buộc type hints đầy đủ
5. **Logging:** Dùng logger, không dùng print

## 📚 Tham Khảo

- **Specs Document:** `chatbot-pipeline.md` - Section 3 (Node Specification)
- **Architecture:** `proj_structure.md`
- **Tech Stack:** `tech-spec.md`

## 🚀 Next Steps

Sau khi implement xong tất cả Nodes:
1. Tạo Container (app/container.py) để wire dependencies
2. Build Graph (app/application/workflows/main_graph.py)
3. Setup CLI runner (main.py)
4. Test toàn bộ flow end-to-end
