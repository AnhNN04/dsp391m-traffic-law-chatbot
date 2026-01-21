# Embedding Pipeline – Traffic Law Data

## Scope
Module này phụ trách **tạo embedding cho các văn bản luật đã được chunk sẵn**  
và cung cấp script kiểm tra search.

Pipeline này **không xử lý chunking** (PDF → JSON).


## Input

Input là các file JSON đã được chunk sẵn, nằm tại:

data/process/chunking/*.json

## Embedding Model

- Model: `intfloat/multilingual-e5-small`
- Framework: sentence-transformers
- Vector dimension: 384
- Similarity metric: cosine similarity

### Model-specific notes

Model E5 yêu cầu:
- Văn bản cần prefix:
  - `passage:` cho dữ liệu
  - `query:` cho câu hỏi tìm kiếm

Ví dụ:
- Passage: `passage: Nội dung điều luật...`
- Query: `query: quy định về người tham gia giao thông`

## Output

Sau khi embedding, dữ liệu được lưu tại:

data/process/embedding/laws_embedded.json

Mỗi chunk sau embedding sẽ có thêm field:

- `embedding`: list[float] – vector embedding đã normalize

## Embedding Process

1. Load toàn bộ file JSON từ `data/process/chunking`
2. Lấy nội dung từ trường `embed_content`
3. Thêm prefix `passage:` theo chuẩn E5
4. Tạo embedding theo batch
5. Lưu kết quả ra `laws_embedded.json`
