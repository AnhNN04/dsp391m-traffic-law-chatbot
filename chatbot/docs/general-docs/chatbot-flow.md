
# BLUEPRINT KỸ THUẬT: HỆ THỐNG CHATBOT AI LUẬT GIAO THÔNG VIỆT NAM

**(Technical Architecture & Implementation Guide)**

## 1. TỔNG QUAN KIẾN TRÚC (SYSTEM ARCHITECTURE)

Hệ thống được thiết kế theo mô hình **Stateful Adaptive RAG**, trong đó:

-   **Brain (Bộ não):** LangGraph điều phối luồng hội thoại.
    
-   **Memory (Bộ nhớ phiên):** State lưu trữ trạng thái trong RAM (không lưu DB lịch sử).
    
-   **Knowledge Base (Tri thức):** Mô hình lai giữa **Neo4j** (Cấu trúc/Logic) và **ChromaDB** (Ngữ nghĩa/HyDE).
    

### 1.1. Luồng dữ liệu (Data Flow)

`Raw Markdown` -> `ETL Pipeline` -> `Structured DB (Graph + Vector)` -> `Runtime Engine` -> `User Response`.

### 1.2. Phạm vi dữ liệu (Data Scope)

1.  **Nhóm Quy chuẩn (Laws):** Luật Giao thông đường bộ, Luật Trật tự ATGT (Dùng để giải thích "Tại sao phạt").
    
2.  **Nhóm Chế tài (Decrees):** Nghị định 168, Nghị định 336 (Dùng để trả lời "Phạt bao nhiêu").
    

## 2. THIẾT KẾ CƠ SỞ DỮ LIỆU (DATABASE DESIGN)

Chúng ta không lưu trữ text nguyên bản. Chúng ta lưu trữ **"Đơn vị Vi phạm" (Atomic Violation Units)**.

### 2.1. Graph Database Schema (Neo4j)

Lưu trữ "Khung xương" pháp lý để đảm bảo truy vết chính xác.

-   **Nodes (Thực thể):**
    
    -   `Document`: (VD: "Nghị định 168").
        
    -   `Article` (Điều): Chứa thông tin về **Phương tiện** (Vehicle Context).
        
    -   `Clause` (Khoản): Chứa thông tin về **Mức phạt** (Penalty Context).
        
    -   `Point` (Điểm): Chứa nội dung **Hành vi** (Behavior). Đây là Node lá quan trọng nhất.
        
-   **Edges (Quan hệ):**
    
    -   `(:Document)-[:HAS_PART]->(:Article)-[:HAS_PART]->(:Clause)-[:HAS_PART]->(:Point)`
        
    -   `(:Point)-[:REFERS_TO]->(:Point)` (Dùng cho tham chiếu nội bộ: "phạt như điểm a").
        

### 2.2. Vector Database Schema (ChromaDB)

Lưu trữ "Ngữ nghĩa" để tìm kiếm ý định người dùng.

-   **Document Structure (Virtual Document):**
    
    Không embed text luật gốc! Embed đoạn văn bản tổng hợp:
    
    ```
    [SUMMARY]: Tóm tắt hành vi (Văn nói).
    [KEYWORDS]: Từ khóa, tiếng lóng (kẹp 3, tạt đầu...).
    [HYDE]: Các câu hỏi giả định (Vượt đèn đỏ phạt nhiêu?).
    [FULL_TEXT]: Nội dung gốc của Điểm + Mức phạt (từ Khoản) + Loại xe (từ Điều).
    
    ```
    
-   **Metadata (Bắt buộc để lọc):**
    
    ```
    {
        "node_id": "ND168_D6_K3_Pa",   // Key liên kết sang Neo4j
        "vehicle": "MOTORBIKE",        // Filter quan trọng nhất
        "fine_range": "800000-1000000" // Dùng để lọc theo mức phạt (nếu cần)
    }
    
    ```
    

## 3. QUY TRÌNH XỬ LÝ DỮ LIỆU (ETL PIPELINE DETAILED)

Quy trình này chạy **Offline** (chạy 1 lần khi nạp dữ liệu).

### BƯỚC 1: PARSING & FLATTENING (Phân rã & Làm phẳng)

**Mục tiêu:** Giải quyết việc mức phạt nằm ở Khoản nhưng hành vi nằm ở Điểm.

**Logic chi tiết:**

1.  **Khởi tạo Parser:**
    
    -   Input: File Markdown.
        
    -   Variables: `current_vehicle = None`, `current_fine = None`.
        
2.  **Duyệt tuần tự (Line-by-line):**
    
    -   **Gặp Header `Điều`:**
        
        -   Dùng Regex/Keywords xác định loại xe (`mô tô`, `ô tô`, `máy kéo`...).
            
        -   Gán vào `current_vehicle`.
            
        -   Reset `current_fine`.
            
    -   **Gặp Header `Khoản`:**
        
        -   Regex tìm số tiền: `phạt tiền từ (...) đến (...)`.
            
        -   Gán vào `current_fine`.
            
        -   _Lưu ý:_ Nếu khoản không có tiền (chỉ dẫn chiếu), gán `current_fine = "REFER_TO_CHILD"`.
            
    -   **Gặp Header `Điểm`:**
        
        -   Tạo object `ViolationUnit`.
            
        -   **Thừa kế:** Copy `current_vehicle` và `current_fine` vào object này.
            
        -   **Tạo ID:** `DOC_DIEU_KHOAN_DIEM` (VD: `ND168_D5_K3_Pa`).
            

### BƯỚC 2: REFERENCE RESOLUTION (Xử lý tham chiếu)

**Mục tiêu:** Xử lý các câu "quy định tại điểm a khoản này".

**Logic:**

1.  Tạo Dictionary `LookupMap`: `{ID: Content}`.
    
2.  Duyệt lại các `ViolationUnit`. Nếu thấy pattern `điểm [a-z] khoản [0-9]`:
    
    -   Tìm ID tương ứng trong `LookupMap`.
        
    -   Lấy content của ID đó nối vào content hiện tại.
        
    -   _Ví dụ:_ "Phạt như điểm a" -> "Phạt như điểm a (tức là: Vượt đèn đỏ)".
        

### BƯỚC 3: LLM ENRICHMENT (Sinh dữ liệu HyDE)

**Mục tiêu:** Tạo dữ liệu cho Vector DB.

**Logic:** Gọi API Gemini cho từng `ViolationUnit`.

-   **Prompt:** Input là (Hành vi + Xe + Tiền). Output là JSON: `{summary, keywords, hyde_questions, scenario}`.
    
-   **Chú ý:** Prompt cần dặn LLM dịch các từ chuyên ngành (VD: "chuyển hướng" -> "rẽ", "tín hiệu" -> "đèn/còi").
    

### BƯỚC 4: INGESTION (Nạp DB)

1.  Nạp cấu trúc cây vào **Neo4j**.
    
2.  Nạp Virtual Document vào **ChromaDB**.
    

## 4. KIẾN TRÚC RUNTIME (CHATBOT ENGINE)

Hệ thống sử dụng **LangGraph** để điều phối.

### 4.1. Định nghĩa State (AgentState)

Đây là bộ nhớ RAM duy nhất của phiên chat.

```
class AgentState(TypedDict):
    # --- Input ---
    session_id: str
    input_message: str          # Câu hỏi user (raw)
    
    # --- Context ---
    chat_history: List[str]     # List message trước đó (cho Contextualize)
    
    # --- Extracted Data ---
    rewritten_query: str        # Câu hỏi đã làm rõ nghĩa
    intent: str                 # LEGAL_QUERY, GREETING, UNKNOWN
    vehicle: str                # MOTORBIKE, CAR, UNKNOWN
    violation_keywords: str     # Tóm tắt hành vi
    
    # --- Retrieval ---
    candidate_ids: List[str]    # Kết quả từ Vector
    final_context: str          # Text tổng hợp từ Graph
    
    # --- Output ---
    response: str

```
