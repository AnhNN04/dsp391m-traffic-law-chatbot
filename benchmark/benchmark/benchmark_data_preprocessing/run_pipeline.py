import os
import json
from processor_spacing import fix_vietnamese_glued_words_in_data
from processor_noise import clean_noisy_answers_from_data
from processor_docs_filter import filter_answers_from_data, get_doc_patterns
from processor_duplicates import remove_duplicates_from_data

# Set paths
current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(os.path.dirname(current_dir))
data_dir = os.path.join(base_dir, "benchmark", "benchmark_data")
raw_data_json = os.path.join(data_dir, "raw", "raw_benchmark_data.json")
processed_dir = os.path.join(data_dir, "preprocess")

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"Lỗi: File {filepath} không tồn tại!")
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    print(f"1. Đang load dữ liệu RAW từ {raw_data_json}...")
    data = load_json(raw_data_json)
    if not data:
        print("Pipeline ngừng chạy do không có dữ liệu đầu vào.")
        return
        
    print("2. Đang sửa lỗi dính chữ (missing spaces)...")
    data, fixed_count = fix_vietnamese_glued_words_in_data(data)
    print(f"   -> Đã xử lý cách chữ.")
    
    print("3. Đang lọc câu trả lời nhiễu (noisy)...")
    data, bad_data = clean_noisy_answers_from_data(data)
    if bad_data:
        print(f"   -> Đã loại bỏ {len(bad_data)} mẫu nhiễu.")
        
    print("4. Đang filter dựa theo tập Document gốc (laws)...")
    raw_docs_dir = os.path.join(base_dir, "data", "raw")
    doc_patterns = get_doc_patterns(raw_docs_dir)
    data = filter_answers_from_data(data, doc_patterns)
    print(f"   -> Đã giữ lại {len(data)} mẫu khớp keyword / document formats.")
    
    print("5. Đang check và loại bỏ duplicate (trùng lặp câu hỏi)...")
    data, duplicate_data = remove_duplicates_from_data(data)
    if duplicate_data:
        print(f"   -> Đã loại bỏ {len(duplicate_data)} mẫu trùng lặp.")
        
    print("6. Đang lưu dữ liệu hoàn chỉnh (Processed)...")
    processed_path = os.path.join(processed_dir, "filtered_data_agent.json")
    save_json(data, processed_path)
    print(f"HOÀN THÀNH PIPELINE! Dữ liệu sạch đã sẵn sàng tại:\n{processed_path}")

if __name__ == "__main__":
    main()
