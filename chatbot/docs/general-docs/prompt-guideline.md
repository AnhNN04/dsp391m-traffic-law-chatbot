
# BỘ PROMPT KỊCH BẢN (MASTER PROMPT FLOW)

**Dự án:** Traffic Law Agent (V3.6 Architecture)

## HƯỚNG DẪN SỬ DỤNG

1.  **Chuẩn bị Context:** Trước khi bắt đầu, hãy đảm bảo bạn đã mở các file tài liệu đặc tả (`Execution_Plan.md`, `Specs_v3.6.md`) trong trình editor để AI có thể đọc được (Add to Context).
    
2.  **Quy tắc 1 Prompt - 1 Nhiệm vụ:** Copy lần lượt từng prompt bên dưới. Đợi AI code xong, review sơ bộ rồi mới paste prompt tiếp theo.
    
3.  **Role Play:** Các prompt bên dưới đã được setup sẵn role "Senior Python Architect".
    

## PHẦN 1: KHỞI TẠO PROJECT (INFRASTRUCTURE & SHARED)

### Prompt 1.1: Setup cấu trúc thư mục & Config

> **Context:** Dựa vào tài liệu `Traffic_Law_Chatbot_Specs_v3.6_CleanArch.md` và `Traffic_Law_Chatbot_Execution_Plan.md`.
> 
> **Yêu cầu:**
> 
> 1.  Hãy đóng vai Senior Python Developer. Tạo cấu trúc thư mục project chuẩn Clean Architecture như trong tài liệu đặc tả.
>     
> 2.  Tạo file `Pipfile` với các thư viện: `langchain`, `langchain-openai`, `langchain-groq`, `langchain-community`, `langgraph`, `pymongo`, `chromadb`, `neo4j`, `pydantic-settings`, `loguru`, `python-dotenv`.
>     
> 3.  Implement module `app/shared/config.py` sử dụng `pydantic-settings` để load các biến môi trường từ `.env` (OPENAI_API_KEY, GROQ_API_KEY, MONGO_URI, NEO4J_URI...).
>     
> 4.  Implement module `app/shared/logger.py` sử dụng `loguru` config output ra stderr với format chuẩn đẹp.
>     
> 5.  Tạo file `.env.example`.
>     
> 
> **Lưu ý:** Chỉ tạo khung thư mục và các file cấu hình này. Chưa code logic nghiệp vụ.

### Prompt 1.2: Docker Setup

> **Yêu cầu:**
> 
> Viết file `docker-compose.yml` để chạy hạ tầng cơ sở gồm:
> 
> 1.  **MongoDB** (image `mongo:latest`, port 27017, volume persistence).
>     
> 2.  **ChromaDB** (image `chromadb/chroma`, port 8000, volume persistence).
>     
>     Hãy đảm bảo cấu hình user/password cho Mongo khớp với ví dụ trong `.env.example`.
>     

## PHẦN 2: DOMAIN LAYER (CORE)

_Lưu ý: Tầng này quan trọng nhất, tuyệt đối không import LangChain ở đây (trừ typing)._

### Prompt 2.1: Entities & State

> **Context:** Đang làm việc tại folder `app/domain`.
> 
> **Yêu cầu:**
> 
> 1.  Implement `app/domain/entities.py`: Định nghĩa các Dataclass/Pydantic model cho `LegalDocument` (content, source, metadata) và `Violation` (violation_name, penalty, law_article).
>     
> 2.  Implement `app/domain/state.py`: Định nghĩa `AgentState` (TypedDict) chứa: `messages` (list), `rewritten_query` (str), `intent` (Literal), `documents` (List[LegalDocument]), `clarification_question` (Optional[str]). Sử dụng `Annotated` và `add_messages` từ `langgraph` cho field messages.
>     
> 3.  Implement `app/domain/exceptions.py`: Định nghĩa các Custom Exception cơ bản (VD: `InfrastructureError`, `LLMOutputError`).
>     

### Prompt 2.2: Interfaces (Abstracts)

> **Yêu cầu:**
> 
> Định nghĩa các Interface (Abstract Base Classes) tại `app/domain/interfaces/` để chuẩn bị cho Dependency Injection:
> 
> 1.  `i_vector_store.py`: Abstract class `IVectorStore` với method `search(query: str, k: int) -> List[LegalDocument]`.
>     
> 2.  `i_graph_store.py`: Abstract class `IGraphStore` với method `get_penalty_info(violation_desc: str) -> List[LegalDocument]`.
>     
> 3.  `i_llm_service.py` (tại `app/application/interfaces/`): Abstract class `ILLMService` với method `generate(prompt: str) -> str` và `generate_structured(prompt: str, schema: Type[BaseModel]) -> BaseModel`.
>     
> 
> **Quy tắc:** Chỉ viết Abstract Class, không viết code xử lý (pass).

## PHẦN 3: INFRASTRUCTURE LAYER (PROVIDERS)

_Lưu ý: Đây là lúc cài cắm các thư viện cụ thể._

### Prompt 3.1: LLM Services Implementation

> **Context:** Implement các interface đã định nghĩa ở bước trước.
> 
> **Yêu cầu:**
> 
> 1.  Implement `app/infrastructure/external_services/openai_service.py`: Class `OpenAIService` kế thừa `ILLMService`. Sử dụng `ChatOpenAI` (`gpt-4o-mini`).
>     
> 2.  Implement `app/infrastructure/external_services/groq_service.py`: Class `GroqService` kế thừa `ILLMService`. Sử dụng `ChatGroq` (`llama3-8b-8192`).
>     
> 
> Hãy đảm bảo xử lý try/except và log lỗi bằng `app/shared/logger.py` khi gọi API.

### Prompt 3.2: Database Implementation (Vector & Graph)

> **Yêu cầu:**
> 
> 1.  Implement `app/infrastructure/persistence/chroma_repo.py`: Class `ChromaRepo` kế thừa `IVectorStore`.
>     
>     -   Sử dụng `GoogleGenerativeAIEmbeddings` (model `models/embedding-004`).
>         
>     -   Khởi tạo `Chroma` client trỏ vào path local `./data/chroma_db`.
>         
> 2.  Implement `app/infrastructure/persistence/neo4j_repo.py`: Class `Neo4jRepo` kế thừa `IGraphStore`.
>     
>     -   Sử dụng `GraphCypherQAChain` của LangChain hoặc driver native để query Neo4j Aura.
>         
> 3.  Implement `app/infrastructure/external_services/tavily_service.py`: Wrapper cho Tavily Search API.
>     

## PHẦN 4: APPLICATION LAYER (LOGIC & NODES)

_Lưu ý: Ghép nối Logic._

### Prompt 4.1: Prompts Management

> **Yêu cầu:**
> 
> Tạo module `app/application/prompts/` chứa các file định nghĩa Prompt Template (String hoặc ChatPromptTemplate):
> 
> 1.  `rewrite_prompt.py`: Prompt viết lại câu hỏi dựa trên lịch sử.
>     
> 2.  `router_prompt.py`: Prompt phân loại intent (Legal/Chitchat).
>     
> 3.  `generate_prompt.py`: Prompt sinh câu trả lời final với yêu cầu trích dẫn nguồn nghiêm ngặt.
>     
> 4.  `clarification_prompt.py`: Prompt sinh câu hỏi làm rõ khi thiếu thông tin.
>     

### Prompt 4.2: Logic Nodes Implementation (Phần 1)

> **Yêu cầu:**
> 
> Implement các Node logic tại `app/application/nodes/`. Áp dụng Dependency Injection (nhận Interfaces vào `__init__`).
> 
> 1.  `guardrails_node.py`: Dùng Groq Service check input an toàn.
>     
> 2.  `rewrite_node.py`: Dùng OpenAI Service viết lại query.
>     
> 3.  `router_node.py`: Dùng OpenAI Service phân loại intent.
>     
> 
> Các Node phải là Callable class (`__call__`), nhận vào `AgentState` và trả về `dict` để update state.

### Prompt 4.3: Logic Nodes Implementation (Phần 2 - Retrieval & Grade)

> **Yêu cầu:**
> 
> 1.  Implement `retrieval_node.py`: Nhận vào `vector_store` và `graph_store`. Thực hiện search song song và gộp kết quả vào `documents`.
>     
> 2.  Implement `grade_node.py`: Kiểm tra `documents` trong state.
>     
>     -   Logic điều hướng: Nếu docs rỗng -> set flag search web. Nếu docs mâu thuẫn -> set flag ask human.
>         
> 3.  Implement `ask_human_node.py`: Sinh câu hỏi làm rõ và return config để `interrupt`.
>     

## PHẦN 5: ORCHESTRATION (THE GRAPH)

### Prompt 5.1: Dependency Container

> **Yêu cầu:**
> 
> Implement `app/container.py`. Tạo class `Container` để khởi tạo toàn bộ hệ thống:
> 
> 1.  Load Settings, Init Logger.
>     
> 2.  Init các Provider (OpenAI, Groq, Chroma, Neo4j, Mongo).
>     
> 3.  Init các Node và inject Provider tương ứng vào chúng.
>     
> 
> Mục đích: File này là nơi duy nhất khởi tạo các object (`new`).

### Prompt 5.2: Main Graph

> **Yêu cầu:**
> 
> Implement `app/application/workflows/main_graph.py`.
> 
> 1.  Sử dụng `StateGraph` với `AgentState`.
>     
> 2.  Import `Container` để lấy các Node đã init.
>     
> 3.  Define các Nodes: `guardrails`, `rewrite`, `router`, `retrieval`, `grade`, `generate`, `web_search`.
>     
> 4.  Define Edges (Luồng đi) và Conditional Edges (Rẽ nhánh) theo đúng diagram trong tài liệu specs v3.5.
>     
> 5.  Setup `MongoDBSaver` làm checkpointer.
>     
> 6.  Compile graph và return `app`.
>     

## PHẦN 6: ENTRY POINT & TESTING

### Prompt 6.1: CLI Runner (Test loop)

> **Yêu cầu:**
> 
> Viết file `main.py` ở root để chạy thử chatbot trên Terminal.
> 
> 1.  Khởi tạo `thread_id` ngẫu nhiên.
>     
> 2.  Vòng lặp `while True` nhận input từ user.
>     
> 3.  Gọi `graph.stream` để chạy và in ra từng bước xử lý (Node nào đang chạy).
>     
> 4.  Xử lý logic `Interrupt`: Nếu graph dừng tại node `ask_human`, in câu hỏi của bot ra, nhận input user, và dùng `Command(resume=...)` để chạy tiếp.
>     

### Prompt 6.2: Seeding Script

> **Yêu cầu:**
> 
> Viết script `scripts/seed_data.py` để fake dữ liệu mẫu:
> 
> 1.  Insert 5 văn bản luật mẫu về "Vượt đèn đỏ", "Nồng độ cồn" vào ChromaDB local.
>     
> 2.  (Optional) Insert vài node graph mẫu vào Neo4j (nếu connection ok).
>     
>     Giúp tôi có dữ liệu để test luồng Retrieval.
>     

```

### Mẹo nhỏ khi dùng Copilot/Claude với bộ prompt này:

1.  **Dùng `@` trong VS Code:** Khi chat với Copilot, hãy gõ `@workspace` để nó đọc được toàn bộ file trong project hiện tại. Ví dụ: *"@workspace Implement prompt 2.1..."*
2.  **Kiểm tra từng bước:** Đừng copy toàn bộ 6 phần vào 1 lần chat. Hãy làm xong Phần 1 -> Chạy thử code (hoặc check syntax) -> Làm Phần 2.
3.  **Debug:** Nếu AI code sai import (lỗi thường gặp nhất), hãy copy lỗi paste lại vào chat kèm câu: *"Fix this circular import error adhering to Clean Architecture rules defined in specs."*

```
