
# TÀI LIỆU TỔ CHỨC CODE - CLEAN ARCHITECT

**Dự án:** Trợ lý ảo Tư vấn Luật Giao thông

**Triết lý:** Dependency Inversion Principle (DIP) - Code phụ thuộc vào Abstract, không phụ thuộc vào Concrete.

## 1. TỔNG QUAN KIẾN TRÚC PHÂN LỚP (LAYERED ARCHITECTURE)

Hệ thống được chia thành 4 vòng tròn đồng tâm (từ trong ra ngoài):

1.  **Domain Layer (Entities & Interfaces):**
    
    -   Chứa `AgentState`, các Entities (Văn bản luật, Lỗi vi phạm).
        
    -   Chứa **Repository Interfaces** (Định nghĩa các hàm giao tiếp DB nhưng không có code thực thi).
        
    -   _Nguyên tắc:_ Không phụ thuộc vào bất kỳ framework nào (kể cả LangChain).
        
2.  **Application Layer (Use Cases / Workflows):**
    
    -   Chứa logic của các **Node** (Rewrite, Retrieval, Grade...).
        
    -   Chứa **Service Interfaces** (Định nghĩa LLM, Search Tools).
        
    -   Chứa logic điều phối Graph (`StateGraph`).
        
    -   _Nguyên tắc:_ Chỉ phụ thuộc vào Domain Layer.
        
3.  **Infrastructure Layer (Adapters / Providers):**
    
    -   **Implement** các Interfaces đã định nghĩa ở Domain/Application.
        
    -   Chứa code cụ thể: gọi OpenAI API, kết nối Neo4j, ChromaDB, MongoDB.
        
    -   Chứa cấu hình `Logging`, `Settings`.
        
4.  **Presentation Layer (Entry Points):**
    
    -   API (FastAPI) hoặc CLI.
        
    -   Nơi thực hiện **Dependency Injection** (Gắn kết các lớp lại với nhau).
        

## 2. CHI TIẾT TỔ CHỨC CODE (PROJECT STRUCTURE)

Cấu trúc thư mục phản ánh chính xác kiến trúc Clean:

```
traffic-law-bot/
├── app/
│   ├── domain/                         # [INNER LAYER] Nghiệp vụ cốt lõi
│   │   ├── __init__.py
│   │   ├── entities.py                 # Class: Document, Violation
│   │   ├── state.py                    # TypedDict: AgentState
│   │   ├── exceptions.py               # Domain Errors
│   │   └── interfaces/                 # [ABSTRACTS] Định nghĩa hợp đồng (Contract)
│   │       ├── i_vector_store.py       # ABC cho ChromaDB
│   │       ├── i_graph_store.py        # ABC cho Neo4j
│   │       └── i_chat_history.py       # ABC cho Mongo
│   │
│   ├── application/                    # [USE CASES] Logic xử lý
│   │   ├── __init__.py
│   │   ├── interfaces/                 # [ABSTRACTS] Service contracts
│   │   │   ├── i_llm_service.py        # ABC cho OpenAI/Groq
│   │   │   └── i_search_tool.py        # ABC cho Tavily
│   │   ├── nodes/                      # [CORE LOGIC] Implement các Node của Graph
│   │   │   ├── base_node.py
│   │   │   ├── guardrails_node.py
│   │   │   ├── rewrite_node.py
│   │   │   ├── retrieval_node.py
│   │   │   └── ...
│   │   └── workflows/                  # Dựng Graph
│   │       └── main_graph.py           # Nơi nối các Node lại
│   │
│   ├── infrastructure/                 # [OUTER LAYER] Thực thi chi tiết
│   │   ├── __init__.py
│   │   ├── config/                     # Settings, Logging
│   │   ├── persistence/                # Implement Domain Interfaces (DB)
│   │   │   ├── chroma_repo.py          # Implements IVectorStore
│   │   │   ├── neo4j_repo.py           # Implements IGraphStore
│   │   │   └── mongo_history.py        # Implements IChatHistory
│   │   └── external_services/          # Implement App Interfaces (API)
│   │       ├── openai_service.py       # Implements ILLMService
│   │       ├── groq_service.py         # Implements ILLMService (Fast)
│   │       └── tavily_service.py       # Implements ISearchTool
│   │
│   └── container.py                    # [DI] Dependency Injection Container
│
├── main.py                             # Entry Point
├── .env
└── docker-compose.yml

```

## 3. THIẾT KẾ ABSTRACTS (INTERFACES)

Đây là phần quan trọng nhất để đảm bảo tính linh hoạt. Code trong Application/Node sẽ chỉ gọi các hàm này.

### 3.1. Domain Interfaces (Trong `app/domain/interfaces`)

**`i_vector_store.py`**

```
from abc import ABC, abstractmethod
from typing import List
from app.domain.entities import LegalDocument

class IVectorStore(ABC):
    @abstractmethod
    def search_similarity(self, query: str, k: int = 5) -> List[LegalDocument]:
        """Tìm kiếm văn bản theo ngữ nghĩa"""
        pass

```

**`i_graph_store.py`**

```
from abc import ABC, abstractmethod
from typing import Dict, Any

class IGraphStore(ABC):
    @abstractmethod
    def query_exact_penalty(self, violation_keyword: str, vehicle_type: str) -> Dict[str, Any]:
        """Truy vấn chính xác mức phạt từ Graph"""
        pass
        
    @abstractmethod
    def run_cypher(self, query: str) -> List[Dict]:
        """Chạy câu lệnh Cypher thô (Dành cho Agent nâng cao)"""
        pass

```

### 3.2. Application Interfaces (Trong `app/application/interfaces`)

**`i_llm_service.py`**

```
from abc import ABC, abstractmethod

class ILLMService(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, system_message: str = "") -> str:
        """Sinh văn bản đơn giản"""
        pass
        
    @abstractmethod
    def generate_structured(self, prompt: str, schema: Any) -> Any:
        """Sinh JSON theo schema (Dùng cho Router)"""
        pass

```

## 4. PHÂN TÍCH XỬ LÝ LÕI CỦA CHATBOT (NODE LOGIC)

Tại tầng Application, các Node là các **Classes** được tiêm (inject) các Interfaces vào Constructor.

### NODE 1: REWRITE NODE (Xử lý Context)

-   **Logic:** Sử dụng LLM thông minh (GPT-4o) để viết lại câu hỏi.
    
-   **Dependency:** `ILLMService`.
    

```
# app/application/nodes/rewrite_node.py

from app.domain.state import AgentState
from app.application.interfaces.i_llm_service import ILLMService

class RewriteNode:
    def __init__(self, llm_service: ILLMService):
        self.llm = llm_service # Dependency Injection
        
    def __call__(self, state: AgentState) -> dict:
        history = state["messages"]
        # Logic prompt ở đây, không phụ thuộc vào OpenAI hay Groq cụ thể
        prompt = f"Rewrite this query based on history: {history[-1].content}"
        
        rewritten = self.llm.generate_text(prompt)
        return {"rewritten_query": rewritten}

```

### NODE 3: RETRIEVAL NODE (Xử lý Tìm kiếm)

-   **Logic:** Gọi song song Vector và Graph, sau đó gộp kết quả.
    
-   **Dependency:** `IVectorStore`, `IGraphStore`.
    

```
# app/application/nodes/retrieval_node.py

from app.domain.interfaces.i_vector_store import IVectorStore
from app.domain.interfaces.i_graph_store import IGraphStore

class RetrievalNode:
    def __init__(self, vector_store: IVectorStore, graph_store: IGraphStore):
        self.vector_store = vector_store
        self.graph_store = graph_store
        
    def __call__(self, state: AgentState) -> dict:
        query = state["rewritten_query"]
        
        # 1. Gọi Abstract Vector Store
        # (Ở đây không quan tâm là Chroma hay Pinecone)
        docs_vector = self.vector_store.search_similarity(query)
        
        # 2. Gọi Abstract Graph Store
        # (Ở đây không quan tâm là Neo4j hay NetworkX)
        # Giả sử đã trích xuất entity "Xe máy" từ query
        docs_graph = self.graph_store.query_exact_penalty(query, "motorcycle")
        
        # 3. Merge Logic (Core Business)
        combined_docs = self._merge_results(docs_vector, docs_graph)
        
        return {"documents": combined_docs}

    def _merge_results(self, vec, graph):
        # Logic nghiệp vụ: Graph luôn được ưu tiên
        return [graph] + vec

```

### NODE 0: GUARDRAILS NODE (Bảo vệ)

-   **Logic:** Dùng LLM tốc độ cao (Groq) để check nhanh.
    
-   **Dependency:** `ILLMService` (Nhưng khi inject sẽ inject bản Groq).
    

```
class GuardrailsNode:
    def __init__(self, fast_llm: ILLMService):
        self.llm = fast_llm
        
    def __call__(self, state: AgentState) -> dict:
        # Check input...
        is_safe = self.llm.generate_text("Is safe? " + state["messages"][-1].content)
        # ... logic chặn

```

## 5. INFRASTRUCTURE IMPLEMENTATION (PROVIDERS)

Đây là nơi "hiện thực hóa" các Abstracts.

### 5.1. Implementing Vector Store (Chroma)

```
# app/infrastructure/persistence/chroma_repo.py
from app.domain.interfaces.i_vector_store import IVectorStore
from langchain_chroma import Chroma

class ChromaRepo(IVectorStore):
    def __init__(self, path: str, embedding_fn):
        self.db = Chroma(persist_directory=path, embedding_function=embedding_fn)
        
    def search_similarity(self, query: str, k: int = 5):
        # Code cụ thể của LangChain Chroma nằm ở đây
        results = self.db.similarity_search(query, k=k)
        # Convert LangChain Document -> Domain Entity
        return [doc.page_content for doc in results]

```

### 5.2. Implementing LLM (OpenAI)

```
# app/infrastructure/external_services/openai_service.py
from app.application.interfaces.i_llm_service import ILLMService
from langchain_openai import ChatOpenAI

class OpenAIService(ILLMService):
    def __init__(self, api_key: str, model: str):
        self.client = ChatOpenAI(api_key=api_key, model=model)
        
    def generate_text(self, prompt: str, system_message: str = ""):
        # Gọi API thực sự
        return self.client.invoke([system_message, prompt]).content

```

## 6. WIRING EVERYTHING (DEPENDENCY INJECTION)

Tại `app/container.py` hoặc `main.py`, chúng ta sẽ lắp ráp các mảnh ghép.

```
# app/container.py (Giả mã)

from app.infrastructure.external_services.openai_service import OpenAIService
from app.infrastructure.external_services.groq_service import GroqService
from app.infrastructure.persistence.chroma_repo import ChromaRepo
from app.infrastructure.persistence.neo4j_repo import Neo4jRepo

from app.application.nodes.rewrite_node import RewriteNode
from app.application.nodes.retrieval_node import RetrievalNode
from app.application.workflows.main_graph import build_graph

class Container:
    def __init__(self):
        # 1. Init Infrastructure (Providers)
        self.smart_llm = OpenAIService(model="gpt-4o-mini")
        self.fast_llm = GroqService(model="llama-3-8b")
        self.vector_store = ChromaRepo(path="./data")
        self.graph_store = Neo4jRepo(uri="bolt://...")
        
        # 2. Init Application Nodes (Inject Providers)
        self.rewrite_node = RewriteNode(llm_service=self.smart_llm)
        self.guardrails_node = GuardrailsNode(fast_llm=self.fast_llm) # Dùng Groq cho rẻ
        self.retrieval_node = RetrievalNode(
            vector_store=self.vector_store,
            graph_store=self.graph_store
        )
        
        # 3. Build Graph
        self.graph = build_graph(
            rewrite=self.rewrite_node,
            guardrails=self.guardrails_node,
            retrieval=self.retrieval_node
        )

# Khi chạy app chỉ cần:
# app_container = Container()
# app_container.graph.invoke(...)

```

## 7. ƯU ĐIỂM CỦA KIẾN TRÚC NÀY

1.  **Dễ thay thế công nghệ (Swappable):**
    
    -   Muốn đổi từ OpenAI sang Gemini? Chỉ cần viết class `GeminiService` implement `ILLMService` và sửa 1 dòng trong `Container`. Code logic trong Node `Rewrite` **không cần sửa một chữ nào**.
        
    -   Muốn đổi từ Chroma sang Pinecone? Tương tự.
        
2.  **Dễ test (Testability):**
    
    -   Khi viết Unit Test cho `RetrievalNode`, bạn không cần kết nối DB thật. Chỉ cần tạo một `MockVectorStore` trả về dữ liệu giả.
        
3.  **Domain Focus:**
    
    -   Thư mục `app/application/nodes` chỉ chứa logic nghiệp vụ luật (Flow đi như thế nào, xử lý kết quả ra sao), không bị lẫn lộn với code gọi API.
      
