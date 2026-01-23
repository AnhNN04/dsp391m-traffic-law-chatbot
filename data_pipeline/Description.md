# Traffic Law Data Pipeline  
**PDF → Markdown → Chunk → Embedding → Search**

## 1. Mục tiêu

Pipeline này phục vụ cho các hệ thống **Legal RAG / Legal Chatbot**, với mục tiêu:

- Chuyển đổi văn bản **Luật giao thông đường bộ** từ PDF sang dữ liệu có cấu trúc
- Chunk hoá theo **đơn vị pháp lý chuẩn** (Điều / Khoản)
- Tạo **vector embedding** phục vụ semantic search và retrieval
- Đảm bảo **truy vấn chính xác + có khả năng trích dẫn pháp lý**

Pipeline được thiết kế theo **multi-stage**, mỗi stage độc lập, dễ debug và dễ mở rộng.



## 2. Tổng quan luồng xử lý (End-to-end)
```text
data/raw/
└── *.pdf
↓ convert_pdf_to_markdown.py
data/markdown_raw/
└── *.md
↓ fix_markdown.py
data/markdown_fixed/
└── *-fixV1.md
↓ chunk_law.py
data/process/chunking/
└── *-chunkV1.json
↓ embedding_chunks.py
data/process/embedding/
└── laws_embedded.json
```


## 3. Stage 1 – Convert PDF → Markdown (Raw)

### Mục tiêu
- Trích xuất nội dung từ PDF sang Markdown
- Giữ tối đa **structure gốc của văn bản pháp luật**:
  - Heading
  - Xuống dòng
  - Bullet / numbering

### Công cụ
- `pymupdf4llm`

### Output
data/markdown_raw/*.md

Markdown ở stage này:
- Chưa làm sạch
- Còn header / footer / công báo / số trang
- Được dùng làm **input thô** cho bước fix-markdown



## 4. Stage 2 – Fix & Clean Markdown

### Mục tiêu
Loại bỏ nhiễu do PDF gây ra nhưng **không phá vỡ cấu trúc pháp lý**.


### 4.1 Các loại nhiễu được xử lý

- Header chính trị:
  - “CỘNG HÒA XHCN VIỆT NAM”
  - “Độc lập – Tự do – Hạnh phúc”
- Header Quốc hội / số hiệu luật
- Dòng Công báo:
  - “Công báo / Số … / Ngày …”
  - Thường lặp lại ở đầu mỗi trang
- Số trang:
  - `Trang 5`
  - `5 / 120`
  - Số đứng riêng lẻ
- Dòng phân cách vô nghĩa:
  - `-----`
  - `_____`


### 4.2 Chuẩn hoá hình thức

- Giữ xuống dòng theo layout PDF (không flatten text)
- Chuẩn hoá bullet:
  - `x)` → `x.`
- Hạn chế nhiều dòng trống liên tiếp
- Không can thiệp nội dung pháp lý


### Output
data/markdown_fixed/*-fixV1.md

> Đây là **nguồn đầu vào chuẩn duy nhất** cho bước chunking.


## 5. Stage 3 – Legal Chunking & Normalization

### Mục tiêu
Chunk hoá văn bản theo **đơn vị pháp lý có thể trích dẫn**  
→ phục vụ truy vấn chính xác cho Legal RAG.


### 5.1 Phân tích cấu trúc luật

Văn bản được parse theo phân cấp chuẩn:

Luật → Chương → Mục → Điều → Khoản → Điểm

markdown
Sao chép mã

#### Quy ước Markdown

- `#`   : Tên Luật  
- `##`  : Chương / Mục  
- `###` : Điều  
- `1.`  : Khoản  
- `a.`  : Điểm  


### 5.2 Nguyên tắc chunk hoá

- Chunk theo **Khoản** (`1.`, `2.`, `3.`)
- Nếu Điều **không có Khoản** → chunk theo **Điều**
- Các Điểm (`a.`, `b.`, `c.`):
  - Được nối lại
  - Gắn vào Khoản tương ứng
- Mỗi chunk tương ứng với **một đơn vị pháp lý độc lập**


### 5.3 Chuẩn hoá nội dung

- Unicode normalization (NFC)
- Chuẩn hoá khoảng trắng
- Giữ nguyên tiếng Việt có dấu
- Text dùng cho embedding / token count:
  - chuyển về chữ thường
  - loại bỏ khoảng trắng dư
- **Không** stemming / lemmatization  
  (bảo toàn ý nghĩa pháp lý)


### 5.4 Định danh & metadata

Mỗi chunk được gán metadata để:
- truy vấn
- trích dẫn
- debug
- kiểm soát context window

#### Các trường chính

- `law_id`      : Parse từ tên file (`LDB`, `LTTATGTDB`)
- `article_id`  : Số Điều
- `clause_id`   : Số Khoản (hoặc `null`)
- `token_count` : Số token

#### Ví dụ chunk output

```json
{
  "law_id": "LDB",
  "article_id": "2",
  "clause_id": "3",
  "token_count": 188,
  "Tên-Luật": "LUẬT ĐƯỜNG BỘ",
  "Chương": "Chương I: NHỮNG QUY ĐỊNH CHUNG",
  "Mục": null,
  "Điều": "Điều 2. Giải thích từ ngữ",
  "Khoản": "3",
  "Nội-Dung": "...",
  "embed_content": "LUẬT ĐƯỜNG BỘ. Chương I... Khoản 3..."
}
```
### Output

data/process/chunking/\*-chunkV1.json



## 6. Stage 4 – Embedding Pipeline

### 6.1 Scope

Module này **chỉ xử lý embedding & search test**.

 Không xử lý:
- PDF
- Markdown
- Chunking


### 6.2 Input

data/process/chunking/\*.json


Yêu cầu mỗi chunk phải có:
- `embed_content`


### 6.3 Embedding Model

- **Model**: `intfloat/multilingual-e5-small`
- **Framework**: `sentence-transformers`
- **Vector dimension**: `384`
- **Similarity metric**: Cosine similarity


### 6.4 Lưu ý đặc thù E5

Model E5 yêu cầu **prefix bắt buộc**.

**Passage (dữ liệu):**
passage: Nội dung điều luật...

**Query (truy vấn):**
query: quy định về người tham gia giao thông



### 6.5 Quy trình embedding

1. Load toàn bộ file JSON chunk
2. Lấy nội dung từ `embed_content`
3. Thêm prefix `passage:`
4. Encode theo batch
5. Normalize vector
6. Lưu kết quả ra `laws_embedded.json`


### 6.6 Output

data/process/embedding/laws_embedded.json


Mỗi chunk sau embedding có thêm:
- `embedding: list[float]` (vector đã normalize)


## 7. Search & Validation

- Encode query với prefix `query:`
- Similarity metric: **cosine similarity**
- Trả về **Top-K chunk** có score cao nhất

Mục đích:
- Kiểm tra chất lượng embedding
- Sanity check pipeline
- Đánh giá khả năng retrieval


## 8. Ưu điểm của Pipeline

- Logic ổn định, không đổi giữa các version
- Flow xử lý rõ ràng như state machine
- Debug được từng stage độc lập
- Dễ mở rộng:
  - Split Khoản dài
  - Detect Điều lỗi format
  - Thêm metadata pháp lý
  - Thay embedding model