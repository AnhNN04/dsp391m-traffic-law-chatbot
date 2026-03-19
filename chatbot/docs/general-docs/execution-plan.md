
# KẾ HOẠCH THỰC THI CHI TIẾT: TRAFFIC LAW AGENT SYSTEM

**Dự án:** Trợ lý ảo Tư vấn Luật Giao thông

**Kiến trúc:** Clean Architecture + Domain-Driven Design (Lite)

**Trạng thái:** Ready for Coding

## GIAI ĐOẠN 1: KHỞI TẠO & HẠ TẦNG CƠ SỞ (FOUNDATION)

_Mục tiêu: Thiết lập môi trường, cấu trúc thư mục chuẩn và các module dùng chung._

### Bước 1.1: Project Skeleton & Environment

-   **Mô tả:** Tạo cấu trúc thư mục và cài đặt dependencies.
    
-   **Yêu cầu:**
    - Sử dụng `virtualenv` hoặc `pipenv`.
    
    -   Tạo đúng cây thư mục như mô tả trong tài liệu `proj_structure.md`.
        
    -   Setup `Pipfile` (hoặc `requirements.txt`) với các thư viện: `langchain`, `langgraph`, `pydantic`, `loguru`, `pymongo`, `chromadb`, `neo4j`, `python-dotenv`.
        
    -   Tạo file `.env.example`.
        
-   **Output:** Folder structure rỗng nhưng đầy đủ `__init__.py`.
    

### Bước 1.2: Shared Modules (Config & Logging)

-   **Mô tả:** Thiết lập module cấu hình và ghi log tập trung.
    
-   **Files:**
    
    -   `app/shared/config.py`: Sử dụng `pydantic-settings` để load biến môi trường. Class `Settings` phải validate được API Key.
        
    -   `app/shared/logger.py`: Cấu hình `loguru` để format log chuẩn JSON hoặc text màu, output ra stderr.
        
-   **Lưu ý:** Tuyệt đối không dùng `print` trong code sau bước này.
    

### Bước 1.3: Docker Infrastructure

**Chú ý:** Phần này có thể thay thế bằng `mongo cloud` và cạy `chromadb` dạng local persistent cho mục đích test.

-   **Mô tả:** Dựng file `docker-compose.yml` để chạy các service phụ trợ.
    
-   **Services:**
    
    -   `mongodb`: Image `mongo:latest`, map port 27017.
        
    -   `chromadb`: (Tùy chọn) Image `chromadb/chroma`, map port 8000.
        
-   **Output:** Chạy `docker-compose up -d` thành công.
    

## GIAI ĐOẠN 2: DOMAIN LAYER (CORE BUSINESS)

_Mục tiêu: Định nghĩa "Luật chơi" và Interface, không phụ thuộc framework bên ngoài._

### Bước 2.1: Entities & State

-   **Files:**
    
    -   `app/domain/state.py`: Định nghĩa `AgentState` (TypedDict) chứa `messages`, `rewritten_query`, `intent`, `documents`.
        
    -   `app/domain/entities.py`: Định nghĩa `LegalDocument` (dataclass) và `Violation` (dataclass).
        
    -   `app/domain/exceptions.py`: Các lỗi như `LLMGenerationError`, `DatabaseConnectionError`.
        
-   **Lưu ý:** File này không được import `langchain` (trừ `Annotated` cho State).
    

### Bước 2.2: Repository Interfaces (Abstracts)

-   **Mô tả:** Định nghĩa hợp đồng (Contract) cho Database.
    
-   **Files:**
    
    -   `app/domain/interfaces/i_vector_store.py`: Class `IVectorStore(ABC)` với method `search(query)`.
        
    -   `app/domain/interfaces/i_graph_store.py`: Class `IGraphStore(ABC)` với method `get_penalty(violation)`.
        
-   **Quy tắc:** Chỉ định nghĩa hàm `abstractmethod`, không viết code xử lý.
    

## GIAI ĐOẠN 3: INFRASTRUCTURE LAYER (PROVIDERS)

_Mục tiêu: Implement các Interfaces đã định nghĩa bằng công nghệ cụ thể._

### Bước 3.1: LLM Services (OpenAI & Groq)

-   **Input:** `app/application/interfaces/i_llm_service.py` (cần tạo interface này trước).
    
-   **Implementation:**
    
    -   `app/infrastructure/external_services/openai_service.py`: Implement `ILLMService` dùng `ChatOpenAI` (GPT-4o-mini).
        
    -   `app/infrastructure/external_services/groq_service.py`: Implement `ILLMService` dùng `ChatGroq` (Llama-3).
        
-   **Yêu cầu:** Xử lý `try-catch` khi gọi API, log error nếu timeout.
    

### Bước 3.2: Persistence Adapters (Databases)

-   **Vector Store:**
    
    -   File: `app/infrastructure/persistence/chroma_repo.py`.
        
    -   Logic: Implement `IVectorStore`. Khởi tạo `Chroma` client trỏ vào local folder. Dùng `GoogleGenerativeAIEmbeddings`.
        
-   **Graph Store:**
    
    -   File: `app/infrastructure/persistence/neo4j_repo.py`.
        
    -   Logic: Implement `IGraphStore`. Sử dụng `Neo4jGraph` của LangChain hoặc driver `neo4j` native để chạy Cypher.
        
-   **Web Search:**
    
    -   File: `app/infrastructure/external_services/tavily_service.py`.
        
    -   Logic: Wrapper cho `TavilyClient`.
        

## GIAI ĐOẠN 4: APPLICATION LAYER (LOGIC NODES)

_Mục tiêu: Xử lý logic nghiệp vụ, ghép nối Domain và Infra._

### Bước 4.1: Prompt Management

-   **Mô tả:** Tập trung toàn bộ Prompt Template.
    
-   **File:** `app/application/prompts/*.py`.
    
-   **Nội dung:**
    
    -   `REWRITE_PROMPT`: Prompt viết lại câu hỏi.
        
    -   `ROUTER_PROMPT`: Prompt phân loại intent (JSON output).
        
    -   `GUARDRAILS_PROMPT`: Prompt check an toàn.
        
    -   `GENERATE_PROMPT`: Prompt sinh câu trả lời final.
        

### Bước 4.2: Node Implementation (Base Nodes)

-   **Yêu cầu chung:** Các class Node nhận Interfaces vào constructor (Dependency Injection).
    
-   **Guardrails Node:** Sử dụng `fast_llm` (Groq). Check input user.
    
-   **Rewrite Node:** Sử dụng `smart_llm` (OpenAI). Input `messages` -> Output `rewritten_query`.
    
-   **Router Node:** Sử dụng `smart_llm` với mode `json_object` hoặc `structured_output`.
    

### Bước 4.3: Retrieval Logic (Hybrid Search)

-   **File:** `app/application/nodes/retrieval_node.py`.
    
-   **Logic:**
    
    -   Nhận `vector_store` và `graph_store`.
        
    -   Chạy song song (hoặc tuần tự) 2 hàm search.
        
    -   Gộp kết quả vào danh sách `documents` trong state.
        

### Bước 4.4: Decision Logic (Grade & Ask Human)

-   **Grade Node:** Đánh giá xem `documents` có rỗng không.
    
-   **Ask Human Node:**
    
    -   Nếu thiếu thông tin -> Sinh câu hỏi làm rõ.
        
    -   **Quan trọng:** Cần return cấu hình để LangGraph biết là cần `interrupt`.
        

## GIAI ĐOẠN 5: ORCHESTRATION (THE GRAPH)

_Mục tiêu: Nối các Node thành một đồ thị hoàn chỉnh._

### Bước 5.1: Dependency Container

-   **File:** `app/container.py`.
    
-   **Mô tả:** Class `Container` khởi tạo tất cả các instance:
    
    -   Init `Settings`, `Logger`.
        
    -   Init `OpenAIService`, `GroqService`, `ChromaRepo`, `Neo4jRepo`.
        
    -   Init các Node: `rewrite_node`, `retrieval_node`... và tiêm dependencies tương ứng vào.
        

### Bước 5.2: Main Graph Definition

-   **File:** `app/application/workflows/main_graph.py`.
    
-   **Logic:**
    
    -   Khai báo `StateGraph(AgentState)`.
        
    -   `add_node`: Thêm các node đã init từ Container.
        
    -   `add_edge`: Định nghĩa luồng đi (`Start` -> `Guardrails` -> `Rewrite`...).
        
    -   `add_conditional_edges`: Định nghĩa logic rẽ nhánh tại Router và Grade.
        
    -   **Persistence:** Kết nối `MongoDBSaver` vào `graph.compile(checkpointer=...)`.
        

## GIAI ĐOẠN 6: INTERFACE & DEPLOYMENT

_Mục tiêu: Chạy thử và đóng gói._

### Bước 6.1: CLI Entry Point (Test Mode)

-   **File:** `main.py` (hoặc `app/presentation/cli/main.py`).
    
-   **Logic:**
    
    -   Vòng lặp `while True` nhận input từ bàn phím.
        
    -   Gọi `graph.invoke` hoặc `graph.stream`.
        
    -   Xử lý logic `Interrupt`: Nếu graph dừng, in ra câu hỏi làm rõ -> Nhận input user -> Gọi `graph.invoke(..., Command(resume=input))`.
        

### Bước 6.2: Final Review & Data Seeding

-   **Seeding:** Viết script `scripts/seed_data.py` để nạp dữ liệu mẫu vào ChromaDB và Neo4j Aura (để có cái mà test).
    
-   **Testing:** Chạy thử các kịch bản:
    
    1.  Hỏi luật bình thường.
        
    2.  Hỏi câu không có trong DB (để test Web Search).
        
    3.  Hỏi thiếu thông tin (để test Interrupt).
        

## TỔNG KẾT: CHECKLIST CHO AGENT CODE

Prompt khi triển khai theo AI Agent code:

> _"Hãy đóng vai Senior Python Backend Developer. Implement module [TÊN MODULE] theo kiến trúc Clean Architecture. Tuân thủ Interface đã định nghĩa tại [FILE INTERFACE]. Sử dụng Pydantic và Loguru. Code cần có Docstring chuẩn Google."_
