
# TÀI LIỆU ĐẶC TẢ KỸ THUẬT: TRAFFIC LAW AGENT (V3.5 - DEMO OPTIMIZED)

**Dự án:** Trợ lý ảo Tư vấn Luật Giao thông

**Phiên bản:**: 0.1.0 (Updated Node 0 & Diagram)

**Mục tiêu:** Tối ưu cho Demo đồ án môn học, chú trọng vào logic nghiệp vụ và Human-in-the-loop.

**Framework:** LangGraph, LangChain, MongoDB, ChromaDB, Neo4j.

## 1. TỔNG QUAN HỆ THỐNG & KIẾN TRÚC (SYSTEM ARCHITECTURE DEEP DIVE)

### 1.1. Triết lý thiết kế (Design Philosophy)

Hệ thống được thiết kế như một **Cognitive Loop (Vòng lặp nhận thức)** thay vì đường thẳng. Nó mô phỏng quy trình tư duy của một luật sư tư vấn:

1.  **Hiểu:** Làm rõ câu hỏi mơ hồ.
    
2.  **Tra cứu:** Tìm kiếm từ nhiều nguồn (Luật, Web).
    
3.  **Đánh giá:** Tự kiểm tra xem thông tin đã đủ chưa.
    
4.  **Hỏi lại:** Nếu chưa rõ, quay lại hỏi thân chủ (User).
    
5.  **Trả lời:** Tổng hợp và trích dẫn.
    

### 1.2. Sơ đồ High-Level (Graph Diagram)

Dưới đây là luồng di chuyển dữ liệu giữa các Node trong LangGraph:

```plaintext
graph TD
    Start([Start / User Input]) --> Node0[NODE 0: State Init & Guardrails]
    
    Node0 -- Safe --> Node1[NODE 1: Rewrite]
    Node0 -- Unsafe --> End([End: Blocked Response])
    
    Node1 --> Node2[NODE 2: Router]
    
    Node2 -- Chitchat --> End
    Node2 -- Legal/Procedure --> Node3[NODE 3: Retrieval]
    
    Node3 --> Node4[NODE 4: Grade & Decide]
    
    Node4 -- Sufficient --> Node7[NODE 7: Generate Answer]
    Node4 -- Insufficient --> Node6[NODE 6: Web Search]
    Node4 -- Ambiguous --> Node5[NODE 5: Ask Human]
    
    Node6 --> Node7
    
    Node5 -.->|Interrupt| User((User))
    User -.->|Reply| Node0
    
    Node7 --> End

```

Hệ thống chia làm 3 tầng dữ liệu rõ rệt:

-   **Knowledge Layer (Immutable):** Neo4j (Graph) & ChromaDB (Vector) chứa văn bản luật gốc. Không bị thay đổi bởi chat.
    
-   **Memory Layer (Mutable):** MongoDB lưu trữ `checkpoint`. Đây là "Short-term memory" chứa trạng thái hội thoại hiện tại.
    
-   **Orchestration Layer:** LangGraph điều phối logic, quyết định luồng đi.
    

## 2. QUẢN LÝ TRẠNG THÁI (DOMAIN STATE)

State không chỉ là nơi chứa biến, mà là "Mạch máu" của hệ thống.

```python
from typing import TypedDict, Annotated, List, Optional, Literal
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # --- Conversation History ---
    # Danh sách tin nhắn, tự động nối thêm (append) tin nhắn mới
    messages: Annotated[List[dict], add_messages]
    
    # --- Internal Reasoning Context ---
    # Câu hỏi đã được làm rõ chủ ngữ/vị ngữ (VD: "Nó phạt bao nhiêu" -> "Xe máy vượt đèn đỏ phạt bao nhiêu")
    rewritten_query: str
    
    # Phân loại ý định: 'legal' (luật), 'procedure' (thủ tục), 'chitchat' (odds and ends)
    intent: Literal['legal', 'procedure', 'chitchat']
    
    # --- Retrieval Data ---
    # Danh sách các đoạn văn bản/điều luật tìm được
    documents: List[dict] 
    # Nguồn dữ liệu cuối cùng dùng để trả lời: 'database', 'internet', 'general_knowledge'
    data_source: str
    
    # --- Control Flags ---
    # Câu hỏi hệ thống muốn hỏi ngược lại user (Nếu có -> Trigger Interrupt)
    clarification_question: Optional[str]

```

## 3. ĐẶC TẢ CHI TIẾT TỪNG NODE (NODE SPECIFICATION)

### NODE 0: STATE INIT & GUARDRAILS (State Management)

-   **Mô tả:** Cổng kiểm soát và khởi tạo phiên làm việc.
    
-   **Mục đích:**
    
    1.  Xác nhận trạng thái hội thoại (được load tự động từ MongoDB Checkpointer) là valid.
        
    2.  Kiểm tra an toàn nội dung (Guardrails) trước khi xử lý logic.
        
-   **Input:** `messages` (tin nhắn người dùng vừa gửi + lịch sử cũ).
    
-   **Output:** `messages` (nếu an toàn) hoặc Tín hiệu dừng.
    
-   **Logic xử lý:**
    
    1.  **State Check:** Kiểm tra xem đây là phiên chat mới hay tiếp tục (resume sau khi interrupt).
        
    2.  **Input Validation:** Kiểm tra độ dài tin nhắn, các ký tự lạ.
        
    3.  **Security Check:** (Optional) Sử dụng RegEx hoặc LLM nhẹ để lọc Prompt Injection/Toxic content.
        
    4.  **Action:**
        
        -   Nếu Hợp lệ -> Chuyển sang **NODE 1**.
            
        -   Nếu Vi phạm -> Trả về thông báo từ chối phục vụ và kết thúc luồng.
            

### NODE 1: REWRITE (Query Transformation)

-   **Mô tả:** Chuyên gia ngôn ngữ học. Biến đổi câu hỏi phụ thuộc ngữ cảnh thành câu hỏi độc lập.
    
-   **Mục đích:** Khắc phục điểm yếu của RAG khi user hỏi đại từ nhân xưng (nó, cái đó, lỗi trên).
    
-   **Input:** `messages` (Toàn bộ lịch sử).
    
-   **Output:** `rewritten_query`.
    
-   **Logic xử lý:**
    
    1.  Lấy 3-5 cặp hội thoại gần nhất.
        
    2.  Prompt LLM: "Hãy viết lại câu hỏi cuối cùng của người dùng sao cho nó đầy đủ ý nghĩa mà không cần đọc lịch sử chat. KHÔNG trả lời câu hỏi, chỉ viết lại."
        
-   **Ví dụ:**
    
    -   _Input:_ User: "Vượt đèn đỏ phạt bao nhiêu?"; Bot: "..."; User: "**Còn xe máy?**"
        
    -   _Output:_ "Mức phạt lỗi vượt đèn đỏ đối với xe máy là bao nhiêu?"
        

### NODE 2: ROUTER (Intent Classification)

-   **Mô tả:** Bộ điều hướng giao thông.
    
-   **Mục đích:** Tách luồng để tiết kiệm chi phí. Câu chào hỏi không cần tra DB.
    
-   **Input:** `rewritten_query`.
    
-   **Output:** `intent` (Enum).
    
-   **Logic xử lý:**
    
    1.  Dùng LLM với `structured_output` (trả về JSON).
        
    2.  Classify vào: `legal` (cần tra cứu), `chitchat` (chào hỏi).
        
-   **Lưu ý:** Nếu câu hỏi mơ hồ (VD: "Luật giao thông có gì vui?"), đẩy về `chitchat`.
    

### NODE 3: RETRIEVAL (Hybrid Search Engine)

-   **Mô tả:** Thủ thư thông thái. Tìm kiếm dữ liệu từ kho nội bộ.
    
-   **Mục đích:** Lấy thông tin chính xác từ Vector Store và Graph.
    
-   **Input:** `rewritten_query`.
    
-   **Output:** `documents`.
    
-   **Logic xử lý:**
    
    1.  **Parallel Execution:** Chạy đồng thời 2 luồng:
        
        -   _Vector Search:_ Tìm 5 chunks văn bản tương đồng nhất từ ChromaDB.
            
        -   _Graph Search:_ (Nếu có Neo4j) Trích xuất thực thể (Xe, Lỗi) -> Query Cypher để lấy mức phạt chính xác.
            
    2.  **Fusion:** Gộp kết quả lại. Nếu trùng lặp, ưu tiên Graph (độ chính xác cao hơn).
        
-   **Quy trình triển khai:** Cần viết Class `HybridRetriever` trong tầng Infrastructure để ẩn đi logic gọi DB.
    

### NODE 4: GRADE & DECIDE (The Judge)

-   **Mô tả:** Thẩm phán đánh giá bằng chứng.
    
-   **Mục đích:** Quyết định xem dữ liệu tìm được có đủ để trả lời không, hay cần tìm web, hay cần hỏi lại user.
    
-   **Input:** `rewritten_query`, `documents`.
    
-   **Output:** Điều hướng sang node tiếp theo (`GENERATE`, `WEB_SEARCH`, `ASK_HUMAN`).
    
-   **Logic xử lý:**
    
    1.  LLM Check: "Dựa vào `documents`, có trả lời được `rewritten_query` không?"
        
    2.  **Rule 1:** Nếu `documents` rỗng -> Sang `WEB_SEARCH`.
        
    3.  **Rule 2:** Nếu `documents` có thông tin nhưng mâu thuẫn hoặc câu hỏi user thiếu thông tin (VD: chưa rõ loại xe) -> Sang `ASK_HUMAN`.
        
    4.  **Rule 3:** Nếu OK -> Sang `GENERATE`.
        

### NODE 5: ASK HUMAN (Human-in-the-loop / Interrupt)

-   **Mô tả:** Nhân viên chăm sóc khách hàng.
    
-   **Mục đích:** Tương tác với user để lấy thêm thông tin.
    
-   **Input:** `rewritten_query`, lý do thiếu tin.
    
-   **Output:** `clarification_question`.
    
-   **Logic xử lý:**
    
    1.  LLM sinh câu hỏi: "Bạn đang hỏi mức phạt cho ô tô hay xe máy?".
        
    2.  Lưu câu hỏi vào state `clarification_question`.
        
    3.  **CRITICAL:** Raise `NodeInterrupt` hoặc trả về cấu hình dừng Graph.
        
    4.  Hệ thống chờ User Input mới.
        
    5.  Sau khi nhận input -> Update State -> Quay lại Node `RETRIEVAL` hoặc `ROUTER`.
        

### NODE 6: WEB SEARCH (Fallback)

-   **Mô tả:** Nghiên cứu sinh tìm kiếm Google.
    
-   **Mục đích:** Xử lý các câu hỏi về thủ tục mới, tin tức, hoặc tình huống lạ chưa có trong luật.
    
-   **Input:** `rewritten_query`.
    
-   **Output:** `documents` (được cập nhật thêm nguồn web).
    
-   **Logic xử lý:**
    
    1.  Gọi Tavily API với query.
        
    2.  Lọc domain: Chỉ lấy `thuvienphapluat.vn`, `luatvietnam.vn`, `chinhphu.vn`.
        
    3.  Format kết quả thành dạng Document chuẩn.
        

### NODE 7: GENERATE (Final Answer)

-   **Mô tả:** Thư ký soạn thảo văn bản.
    
-   **Mục đích:** Tạo câu trả lời cuối cùng cho người dùng.
    
-   **Input:** `rewritten_query`, `documents`.
    
-   **Output:** Tin nhắn phản hồi (AI Message).
    
-   **Logic xử lý:**
    
    1.  System Prompt: "Bạn là trợ lý luật. Chỉ trả lời dựa trên context cung cấp. BẮT BUỘC trích dẫn điều khoản (VD: Theo Điều 5...)."
        
    2.  Nếu nguồn từ Web, thêm disclaimer: "Thông tin tham khảo từ Internet."
        

## 4. HƯỚNG DẪN SETUP MÔI TRƯỜNG (ENVIRONMENT SETUP)

### 4.1. Cài đặt Python & Quản lý gói (Pipenv)

```
# 1. Cài đặt Pipenv (nếu chưa có)
pip install --user pipenv

# 2. Tạo project & cài đặt thư viện
mkdir chatbot-pipeline
cd chatbot-pipeline

# Cài đặt Core Stack
pipenv install langchain langchain-openai langchain-community langgraph pymongo chromadb tavily-python neo4j pydantic python-dotenv

# Cài đặt Dev Tools
pipenv install --dev jupyter ipykernel

# 3. Vào môi trường ảo
pipenv shell

```

### 4.2. Hạ tầng Database (Docker Compose)

Tạo file `docker-compose.yml` tại root:

```
version: '3.9'
services:
  # MongoDB cho Chat History (Persistence)
  mongodb:
    image: mongo:latest
    container_name: traffic_mongo
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=password123
    volumes:
      - ./data/mongo:/data/db

  # ChromaDB cho Vector Search (Optional - dùng local mode)
  chromadb:
    image: chromadb/chroma:latest
    container_name: traffic_chroma
    ports:
      - "8000:8000"
    volumes:
      - ./data/chroma:/chroma/chroma

```

Chạy lệnh: `docker-compose up -d`

### 4.3. Cấu hình (.env)

```
# App Config
APP_ENV=development
LOG_LEVEL=INFO

# API Keys
OPENAI_API_KEY=sk-proj-...
TAVILY_API_KEY=tvly-...

# Database
MONGO_URI=mongodb://admin:password123@localhost:27017
NEO4J_URI=bolt://localhost:7687
NEO4J_AUTH=neo4j/password

```
