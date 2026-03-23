import os
import json
import re

# Lấy thư mục gốc (lùi 2 cấp từ thư mục hiện tại)
current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(os.path.dirname(current_dir))

# Đường dẫn
raw_data_dir = os.path.join(base_dir, "data", "raw")
input_json = os.path.join(current_dir, "data_agent.json")
output_json = os.path.join(current_dir, "filtered_data_agent.json")

def get_doc_patterns(directory):
    patterns = set()
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return patterns
        
    for filename in os.listdir(directory):
        # Chỉ lấy file .doc, bỏ qua .docx
        if filename.lower().endswith(".doc"):
            # Trích xuất dạng số_năm_Kýhiệu (ví dụ: 34_2024_TT-BGTVT) từ tên file
            matches = re.finditer(r'(\d+)_(\d+)_([A-Z0-9\-]+)', filename)
            for match in matches:
                so, nam, ky_hieu = match.group(1), match.group(2), match.group(3)
                # Chuyển thành số/năm/ký_hiệu (ví dụ: 34/2024/TT-BGTVT)
                pattern = f"{so}/{nam}/{ky_hieu}"
                patterns.add(pattern)
                # Nếu là ND-CP thì thêm cả NĐ-CP (do lỗi gõ phím tiếng Việt)
                if ky_hieu == 'ND-CP':
                    patterns.add(f"{so}/{nam}/NĐ-CP")
                # Thêm dạng không có ký hiệu để bao quát hơn (ví dụ: 34/2024)
                patterns.add(f"{so}/{nam}")
    return patterns

def main():
    doc_patterns = get_doc_patterns(raw_data_dir)
    print("Các mẫu trích xuất được từ file .doc:", doc_patterns)
    
    keywords = ["Luật Đường Bộ", "Luật Trật tự, an toàn giao thông đường bộ"]
    
    if not os.path.exists(input_json):
        print(f"File {input_json} does not exist.")
        return

    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    filtered_data = filter_answers_from_data(data, doc_patterns)
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=4)
        
    print(f"Đã lọc được {len(filtered_data)} mẫu từ tổng số {len(data)} mẫu ban đầu.")
    print(f"Kết quả được lưu vào file: {output_json}")

def filter_answers_from_data(data, doc_patterns):
    filtered_data = []
    keywords = ["Luật Đường Bộ", "Luật Trật tự, an toàn giao thông đường bộ"]
    
    for item in data:
        answer = item.get("answer", "")
        if not answer:
            continue
            
        # Loại bỏ ngay lập tức nếu chứa các luật, nghị định, thông tư của năm 2025 hoặc 2026 theo yêu cầu (vd: 336/2025/NĐ-CP, 01/2026/QĐ-UBND)
        if "/2025/" in answer or "/2026/" in answer:
            continue
            
        answer_lower = answer.lower()
        found = False
        
        # 1. Kiểm tra xem answer có chứa bất kỳ văn bản nào trong raw không
        for pattern in doc_patterns:
            if pattern in answer:
                found = True
                break
                
        # 2. Nếu không chứa văn bản nào trong raw, kiểm tra xem nó có chứa văn bản lạ (không có sẵn) không?
        if not found:
            # Tìm tất cả các chuỗi giống ký hiệu văn bản (ví dụ: 12/2025/TT-BCA, 100/2019/NĐ-CP)
            other_docs = re.findall(r'\d+/\d+/[A-ZĐ0-9\-]+', answer)
            
            # Nếu chứa văn bản lạ (không nằm trong danh sách của chúng ta), ta bỏ qua luôn mẫu này
            # Còn nếu không chứa văn bản lạ, ta mới check keywords
            if len(other_docs) == 0:
                for kw in keywords:
                    if kw.lower() in answer_lower:
                        found = True
                        break
                        
        if found:
            filtered_data.append(item)
            
    return filtered_data

if __name__ == "__main__":
    main()
