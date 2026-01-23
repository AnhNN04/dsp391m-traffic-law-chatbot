import os
import re
import pathlib
import logging
import pymupdf4llm
from typing import List, Dict
from config import DATA_DIR, MD_RAW_DIR

RAW_DATA_DIR = DATA_DIR / "raw"
OUTPUT_DIR = MD_RAW_DIR

# =============================================================================
# 1. CẤU HÌNH LOGGING & HẰNG SỐ (LOGGING & CONSTANTS)
# =============================================================================

# Setup Logging để in ra console rõ ràng
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# DANH SÁCH CÁC MẪU REGEX NHẬN DIỆN NHIỄU (NOISE PATTERNS)
# Phân tích dựa trên mô tả:
# 1. Header chính trị: Cộng hòa XHCN VN, Độc lập - Tự do...
# 2. Header Quốc hội: Luật số..., Quốc hội khóa...
# 3. Footer/Header Công báo: Công báo / Số ... / Ngày ...
# 4. CÔNG BÁO/Số.../Ngày... lặp lại ở đầu mỗi trang
# 5. Số trang (đứng một mình hoặc dạng Trang x/y) ở góc trên bên trái
# Lưu ý: Regex có thêm `[\*\#]*` để bắt cả trường hợp text bị bold (**Text**) hoặc heading (## Text)
NOISE_PATTERNS = [
    # --- Nhóm Chính trị & Quốc hiệu ---
    r"^[\*\#\s]*CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM.*$",
    r"^[\*\#\s]*Độc lập\s*-\s*Tự do\s*-\s*Hạnh phúc.*$",
    r"^[\*\#\s]*QUỐC HỘI.*$",
    
    # --- Nhóm Số hiệu & Ngày tháng (Header trang đầu) ---
    r"^[\*\#\s]*Luật số[:\s].*$",
    r"^[\*\#\s]*Số[:\s].*\/QH\d+.*$",
    r"^[\*\#\s]*Hà Nội, ngày\s+\d+\s+tháng\s+\d+\s+năm.*$",
    
    # --- Nhóm Công báo (Header các trang sau) ---
    r"^[\*\#\s]*Công báo.*$",
    r"^[\*\#\s]*\/.*Năm.*\/.*Số.*$",   # VD: / Năm 2024 / Số 100
    
    # --- Nhóm Tên luật lặp lại (Page Header) Optional ---
    r"^[\*\#\s]*LUẬT TRẬT TỰ, AN TOÀN GIAO THÔNG ĐƯỜNG BỘ.*$",
    r"^[\*\#\s]*LUẬT ĐƯỜNG BỘ.*$",
    
    # --- Nhóm Số trang ---
    r"^[\*\#\s]*Trang\s*\d+.*$",          # VD: Trang 1
    r"^[\*\#\s]*\d+\s*\/\s*\d+$",         # VD: 1/50
    r"^[\*\#\s]*\d+$",                    # VD: 5 (Số đứng một mình)
    
    # --- Nhóm Ký tự phân cách vô nghĩa ---
    r"^[\*\#\s]*[-–_]{2,}.*$",            # Dòng chỉ toàn dấu gạch ngang/gạch dưới
]


# =============================================================================
# 2. LOGIC FLOW & PSEUDO-CODE (MÃ GIẢ)
# =============================================================================

"""
MÃ GIẢ THUẬT TOÁN (ALGORITHM PSEUDO-CODE):

INPUT: Thư mục chứa các file PDF (bao gồm cả file lẻ và file chia nhỏ _1, _2).
OUTPUT: Các file Markdown đã làm sạch và gộp nội dung.

BEGIN PROCEDURE main:
    1.  Kiểm tra và tạo thư mục output (data/processed).
    2.  Lấy danh sách tất cả file .pdf từ input.
    
    3.  CALL function group_pdf_files(file_list) -> file_groups:
        # Gom nhóm các file bị chia tách (VD: LuatA_1, LuatA_2 -> Nhóm LuatA)
        INIT dictionary groups = {}
        FOR each file IN file_list:
            PARSE tên file để tìm pattern "TenFile_SoThuTu"
            IF match pattern:
                KEY = TenFile
                ADD file vào list của KEY
            ELSE:
                KEY = TenFileGoc
                ADD file vào list của KEY
        SORT các file trong từng nhóm theo thứ tự tên (đảm bảo _1 trước _2).
        RETURN groups.

    4.  FOR each (group_name, pdf_files) IN file_groups:
        INIT merged_content = ""
        
        FOR each pdf_file IN pdf_files:
            PRINT "Đang xử lý file..."
            
            # Bước A: Trích xuất thô
            raw_markdown = pymupdf4llm.to_markdown(pdf_file)
            
            # Bước B: Làm sạch nhiễu (Quan trọng)
            cleaned_text = CALL function clean_markdown_content(raw_markdown)
            
            # Bước C: Gộp
            APPEND cleaned_text TO merged_content
            ADD "\n\n" TO merged_content (để tránh dính chữ giữa các file)
        
        # Bước D: Lưu file
        WRITE merged_content TO "data/processed/{group_name}.md"
        PRINT "Hoàn tất nhóm {group_name}"

END PROCEDURE
"""


# =============================================================================
# 3. IMPLEMENTATION (MÃ NGUỒN)
# =============================================================================

def clean_markdown_content(text: str) -> str:
    """
    Loại bỏ các dòng nhiễu (Header, Footer, Số trang, Slogan) khỏi văn bản Markdown.
    
    Args:
        text (str): Nội dung markdown thô từ pymupdf4llm.
        
    Returns:
        str: Nội dung sạch.
    """
    lines = text.split('\n')
    cleaned_lines = []
    
    # Pre-compile regex để tăng tốc độ xử lý trong vòng lặp
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]
    
    total_lines = len(lines)
    removed_count = 0
    
    for line in lines:
        stripped_line = line.strip()
        
        # 1. Giữ lại dòng trống (nhưng hạn chế quá nhiều dòng trống liên tiếp)
        if not stripped_line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
            
        # 2. Kiểm tra xem dòng có khớp bất kỳ mẫu nhiễu nào không
        is_noise = False
        for pattern in compiled_patterns:
            if pattern.match(stripped_line):
                is_noise = True
                removed_count += 1
                # Debug log cho các dòng bị xóa (nếu cần kiểm tra kỹ)
                # logger.debug(f"Removed noise: {stripped_line}")
                break
        
        if not is_noise:
            cleaned_lines.append(line) # Giữ nguyên line gốc (bao gồm indent nếu có)
            
    logger.info(f"---> Đã lọc bỏ {removed_count}/{total_lines} dòng nhiễu.")
    return "\n".join(cleaned_lines)


def group_pdf_files(pdf_paths: List[pathlib.Path]) -> Dict[str, List[pathlib.Path]]:
    """
    Gom nhóm các file PDF. 
    Logic: Nếu tên file kết thúc bằng _số (VD: _1, _2), gộp chung vào 1 nhóm.
    """
    groups = {}
    
    # Regex bắt pattern đuôi _số (VD: abc_1.pdf, abc_02.pdf)
    split_pattern = re.compile(r'(.+)_(\d+)$')

    for path in pdf_paths:
        stem = path.stem # Tên file không đuôi
        match = split_pattern.match(stem)
        
        if match:
            # File thuộc nhóm chia nhỏ (VD: LuatGT_1 -> Group: LuatGT)
            base_name = match.group(1)
        else:
            # File độc lập -> Group là tên chính nó
            base_name = stem
            
        if base_name not in groups:
            groups[base_name] = []
        groups[base_name].append(path)
    
    # Sắp xếp danh sách file trong mỗi nhóm (quan trọng để _1 luôn đứng trước _2)
    for base_name in groups:
        groups[base_name].sort(key=lambda p: p.name)
        
    return groups


def main():
    """
    Hàm thực thi chính.
    """
    # 1. Setup thư mục
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created output directory: {OUTPUT_DIR}")

    # 2. Quét file PDF
    pdf_files = list(RAW_DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.warning("Không tìm thấy file PDF nào trong data/raw/")
        return

    logger.info(f"Tìm thấy {len(pdf_files)} file PDF đầu vào.")

    # 3. Gom nhóm file
    file_groups = group_pdf_files(pdf_files)
    logger.info(f"Đã phân loại thành {len(file_groups)} bộ dữ liệu: {list(file_groups.keys())}")

    # 4. Xử lý từng nhóm
    for group_name, files in file_groups.items():
        logger.info(f"--- BẮT ĐẦU XỬ LÝ BỘ: {group_name} ---")
        logger.info(f"Gồm các file thành phần: {[f.name for f in files]}")
        
        merged_md_content = ""
        
        for idx, pdf_path in enumerate(files):
            try:
                logger.info(f"---> Processing file: {pdf_path.name}...")
                
                # --- A. Conversion ---
                # to_markdown trả về text kèm format (bold, heading...)
                raw_md = pymupdf4llm.to_markdown(str(pdf_path))
                
                # --- B. Cleaning ---
                clean_md = clean_markdown_content(raw_md)
                
                # --- C. Merging ---
                # Nếu là file thứ 2 trở đi (_2), thêm khoảng trắng để tách biệt
                if idx > 0:
                    merged_md_content += "\n\n" 
                
                merged_md_content += clean_md
                
            except Exception as e:
                logger.error(f"Lỗi khi xử lý file {pdf_path.name}: {e}")
                # Không break, cố gắng xử lý tiếp các file khác
        
        # 5. Lưu kết quả
        output_path = OUTPUT_DIR / f"{group_name}.md"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(merged_md_content)
            logger.info(f"HOÀN TẤT! File lưu tại: {output_path}")
            logger.info(f"Tổng kích thước: {len(merged_md_content)} ký tự.\n")
            
        except IOError as e:
             logger.error(f"Lỗi khi ghi file output {output_path}: {e}")

if __name__ == "__main__":
    main()