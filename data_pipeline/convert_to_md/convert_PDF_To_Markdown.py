import os
import re
import pathlib
import logging
import pymupdf4llm
from typing import List, Dict


# Setup Logging để in ra console rõ ràng
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

BASE_DIR = pathlib.Path(__file__).resolve().parent

RAW_DATA_DIR = BASE_DIR / "data" / "raw"

PROCESSED_DATA_DIR = BASE_DIR / "data" / "proceed"


NOISE_PATTERNS = [
    # --- Nhóm Chính trị & Quốc hiệu ---
    r"^[\*\#\s]*CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM.*$",
    r"^[\*\#\s]*Độc lập\s*-\s*Tự do\s*-\s*Hạnh phúc.*$",
    
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






def clean_markdown_content(text: str) -> str:

    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    lines = text.split('\n')
    cleaned_lines = []
    
    # Pre-compile regex
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]
    
    for line in lines:
        stripped_line = line.strip()
        
        if not stripped_line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
            
        is_noise = False
        for pattern in compiled_patterns:
            if pattern.match(stripped_line):
                is_noise = True
                break
        
        if not is_noise:
            cleaned_lines.append(line) 
            
    return "\n".join(cleaned_lines).strip()






def group_pdf_files(pdf_paths: List[pathlib.Path]) -> Dict[str, List[pathlib.Path]]:
    groups = {}
    
    split_pattern = re.compile(r'(.+)_(\d+)$')

    for path in pdf_paths:
        stem = path.stem # Tên file không đuôi
        match = split_pattern.match(stem)
        
        if match:
            base_name = match.group(1)
        else:
            base_name = stem
            
        if base_name not in groups:
            groups[base_name] = []
        groups[base_name].append(path)
    
    for base_name in groups:
        groups[base_name].sort(key=lambda p: p.name)
        
    return groups





def main():
    if not os.path.exists(PROCESSED_DATA_DIR):
        os.makedirs(PROCESSED_DATA_DIR)
        logger.info(f"Created output directory: {PROCESSED_DATA_DIR}")

    pdf_files = list(RAW_DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.warning("Không tìm thấy file PDF nào trong data/raw/")
        return

    logger.info(f"Tìm thấy {len(pdf_files)} file PDF đầu vào.")

    file_groups = group_pdf_files(pdf_files)
    logger.info(f"Đã phân loại thành {len(file_groups)} bộ dữ liệu: {list(file_groups.keys())}")

    for group_name, files in file_groups.items():
        logger.info(f"--- BẮT ĐẦU XỬ LÝ BỘ: {group_name} ---")
        logger.info(f"Gồm các file thành phần: {[f.name for f in files]}")
        
        merged_md_content = ""
        
        for idx, pdf_path in enumerate(files):
            try:
                logger.info(f"---> Processing file: {pdf_path.name}...")
                
                raw_md = pymupdf4llm.to_markdown(str(pdf_path))
                
                clean_md = clean_markdown_content(raw_md)
                
                if idx > 0:
                    merged_md_content += "\n\n" 
                
                merged_md_content += clean_md
                
            except Exception as e:
                logger.error(f"Lỗi khi xử lý file {pdf_path.name}: {e}")
        
        output_path = PROCESSED_DATA_DIR / f"{group_name}.md"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(merged_md_content)
            logger.info(f"HOÀN TẤT! File lưu tại: {output_path}")
            logger.info(f"Tổng kích thước: {len(merged_md_content)} ký tự.\n")
            
        except IOError as e:
             logger.error(f"Lỗi khi ghi file output {output_path}: {e}")

if __name__ == "__main__":
    main()