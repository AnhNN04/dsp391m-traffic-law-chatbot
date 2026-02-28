# Dependency Injection Container - Hướng Dẫn

## 📋 Tổng Quan

`Container` là **trái tim** của hệ thống - nơi duy nhất khởi tạo các object và wire dependencies.

### Triết Lý Thiết Kế

```
Nguyên tắc vàng: "New is glue"
→ Chỉ Container được phép dùng `new` (khởi tạo object)
→ Code khác chỉ phụ thuộc vào Interfaces
```

### Lợi Ích

✅ **Testability**: Dễ mock dependencies khi test  
✅ **Flexibility**: Swap implementations không cần sửa code  
✅ **Maintainability**: Tất cả config tập trung 1 chỗ  
✅ **Clear Dependencies**: Biết rõ Node nào cần Service gì  

---

## 🏗️ Kiến Trúc Container

```
Container
├── Settings (từ .env)
├── Logger (loguru)
│
├── LLM Services
│   ├── OpenAI (Smart - GPT-4o-mini)
│   └── Groq (Fast - Llama-3)
│
├── Databases
│   ├── ChromaDB (Vector Store)
│   ├── Neo4j (Graph Store - Optional)
│   └── MongoDB (State Persistence)
│
├── Search Tools
│   └── Tavily (Web Search - Optional)
│
└── Nodes (8 nodes)
    ├── GuardrailsNode
    ├── RewriteNode
    ├── RouterNode
    ├── RetrievalNode
    ├── GradeNode
    ├── AskHumanNode
    ├── WebSearchNode
    └── GenerateNode
```

---

## 🚀 Cách Sử Dụng

### 1. Setup Environment

```bash
# Copy template
cp .env.example .env

# Edit và điền API keys
nano .env
```

**Yêu cầu tối thiểu:**
```env
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=...  # For embeddings
```

### 2. Khởi Tạo Container

```python
from app.container import Container

# Khởi tạo container
container = Container()

# Tất cả dependencies sẵn sàng!
```

### 3. Sử Dụng Services

```python
# Access LLM services
openai = container.openai_service
groq = container.groq_service

# Access databases
chroma = container.chroma_repo
neo4j = container.neo4j_repo  # None nếu không config

# Access nodes
guardrails = container.guardrails_node
rewrite = container.rewrite_node

# Access compiled graph
graph = container.graph
```

---

## 💡 Lazy Loading

Container sử dụng **lazy loading** - chỉ khởi tạo khi cần:

```python
container = Container()
# ✅ Nhanh! Chỉ load settings

openai = container.openai_service  
# 🔧 Bây giờ mới khởi tạo OpenAI

openai2 = container.openai_service
# ⚡ Trả về instance đã cache, không init lại
```

**Lợi ích:**
- Startup nhanh
- Tiết kiệm tài nguyên
- Chỉ init service thực sự cần

---

## 🔧 Dependency Injection Pattern

### Cách Hoạt Động

```python
# ❌ BAD: Hardcode dependency
class RewriteNode:
    def __init__(self):
        self.llm = ChatOpenAI(...)  # Hardcode!

# ✅ GOOD: Inject dependency
class RewriteNode:
    def __init__(self, smart_llm: ILLMService):
        self.llm = smart_llm  # Interface!

# Container wiring
container.rewrite_node = RewriteNode(
    smart_llm=container.openai_service
)
```

### Ví Dụ Thực Tế

```python
# 1. Define interface (Domain layer)
class ILLMService(ABC):
    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        pass

# 2. Implement (Infrastructure layer)
class OpenAIService(ILLMService):
    def generate_text(self, prompt: str) -> str:
        return self.client.invoke(prompt)

# 3. Inject (Container)
rewrite_node = RewriteNode(
    smart_llm=OpenAIService(...)  # Concrete
)

# 4. Use (Application layer)
# RewriteNode chỉ biết ILLMService, không biết OpenAI
```

---

## ⚙️ Configuration

### Settings Class (Pydantic)

Tất cả config được validate tự động:

```python
from app.shared.config import settings

# Access config
print(settings.OPENAI_API_KEY)
print(settings.OPENAI_MODEL)

# Helper methods
if settings.is_production():
    # Production logic
    
if settings.has_neo4j():
    # Use graph store
```

### Feature Flags

```python
# Trong .env
ENABLE_NEO4J=false
ENABLE_WEB_SEARCH=true

# Trong code
if settings.has_neo4j():
    graph_docs = neo4j_repo.search(...)
else:
    # Fallback to vector only
```

---

## 🧪 Testing

### Mock Dependencies

```python
from unittest.mock import Mock

def test_rewrite_node():
    # Mock LLM service
    mock_llm = Mock(spec=ILLMService)
    mock_llm.generate_text.return_value = "Rewritten query"
    
    # Inject mock
    node = RewriteNode(smart_llm=mock_llm)
    
    # Test
    result = node(state)
    assert result["rewritten_query"] == "Rewritten query"
```

### Test Container

```python
def test_container_initialization():
    """Test container loads successfully."""
    container = Container()
    
    assert container.settings is not None
    assert container.openai_service is not None
    
def test_lazy_loading():
    """Test services are lazy loaded."""
    container = Container()
    
    # Chưa init OpenAI
    assert container._openai_service is None
    
    # Trigger init
    _ = container.openai_service
    
    # Đã init
    assert container._openai_service is not None
```

---

## 🐛 Debugging

### Check Initialization

```python
container = Container()

# Check logs
# Output sẽ hiện:
# 🚀 Initializing Traffic Law Agent Container
# 📋 Environment: development
# 🔧 Initializing OpenAI service...
# ✅ OpenAI service ready
```

### Verify Config

```python
from app.shared.config import settings

print(f"OpenAI: {settings.OPENAI_API_KEY[:10]}...")
print(f"Model: {settings.OPENAI_MODEL}")
print(f"Neo4j enabled: {settings.has_neo4j()}")
```

### Common Issues

**1. Missing API Key**
```
❌ Failed to load settings: Field required [OPENAI_API_KEY]
```
→ Kiểm tra .env file

**2. Neo4j Connection Failed**
```
⚠️ Neo4j initialization failed (optional): Connection refused
```
→ Check NEO4J_URI, hoặc set ENABLE_NEO4J=false

**3. Import Error**
```
ModuleNotFoundError: No module named 'app.infrastructure'
```
→ Các providers chưa được implement (sẽ làm ở Prompt 3.x)

---

## 📊 Dependency Graph

```
Container
    ↓
┌───────────────────────────────────────┐
│          LLM Services                 │
├───────────────────────────────────────┤
│ OpenAI ← RewriteNode                 │
│        ← RouterNode                   │
│        ← GradeNode                    │
│        ← AskHumanNode                │
│        ← GenerateNode                │
│                                       │
│ Groq   ← GuardrailsNode              │
└───────────────────────────────────────┘
    ↓
┌───────────────────────────────────────┐
│          Databases                    │
├───────────────────────────────────────┤
│ Chroma ← RetrievalNode               │
│ Neo4j  ← RetrievalNode (optional)    │
└───────────────────────────────────────┘
    ↓
┌───────────────────────────────────────┐
│          Search Tools                 │
├───────────────────────────────────────┤
│ Tavily ← WebSearchNode (optional)    │
└───────────────────────────────────────┘
```

---

## 🔒 Best Practices

### 1. Never Hardcode Dependencies

```python
# ❌ BAD
class MyNode:
    def __init__(self):
        self.llm = ChatOpenAI(api_key="sk-...")

# ✅ GOOD
class MyNode:
    def __init__(self, llm: ILLMService):
        self.llm = llm
```

### 2. Use Interfaces

```python
# ❌ BAD: Depend on concrete class
def process(openai_service: OpenAIService):
    ...

# ✅ GOOD: Depend on interface
def process(llm_service: ILLMService):
    ...
```

### 3. Cleanup Resources

```python
container = Container()
try:
    # Use container
    graph = container.graph
    result = graph.invoke(...)
finally:
    # Cleanup
    container.cleanup()
```

---

## 🚀 Next Steps

Sau khi Container setup xong:

1. ✅ **Implement Providers** (Prompt 3.1, 3.2)
   - OpenAIService
   - GroqService  
   - ChromaRepo
   - Neo4jRepo
   - TavilyService

2. ✅ **Build Graph** (Prompt 5.2)
   - Define nodes
   - Add edges
   - Configure checkpointer

3. ✅ **Create CLI** (Prompt 6.1)
   - Runner script
   - Interactive loop

---

## 📚 Tham Khảo

- **Martin Fowler - Dependency Injection**: https://martinfowler.com/articles/injection.html
- **Clean Architecture**: Robert C. Martin
- **SOLID Principles**: Especially "D" - Dependency Inversion

---

## ✨ Summary

Container là **Single Source of Truth** cho dependencies:

- 🎯 **One place** to configure everything
- 🔌 **Easy to swap** implementations  
- 🧪 **Simple to test** with mocks
- 📦 **Lazy loading** for performance
- 🛡️ **Type safe** with interfaces

**Remember:** Good architecture makes testing easy. If it's hard to test, the design is wrong! 🎯
