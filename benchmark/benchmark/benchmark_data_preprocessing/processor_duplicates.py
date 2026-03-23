import json
import os

def remove_duplicates(filepath):
    print(f"Đang kiểm tra trùng lặp trong file: {filepath}...")
    
    if not os.path.exists(filepath):
        print(f"[-] Lỗi: File {filepath} không tồn tại.")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"[-] Lỗi: Không thể phân tích cấu trúc file JSON {filepath}. File trống hoặc bị hỏng.")
            return

    original_count = len(data)
    unique_data, duplicate_data = remove_duplicates_from_data(data)
    removed_count = len(duplicate_data)
    
    if removed_count > 0:
        # Cập nhật và ghi đè lại tệp JSON (tập không bị trùng)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(unique_data, f, ensure_ascii=False, indent=4)
            
        # Lưu các bản copy bị xoá ra file tách biệt
        dup_file = "duplicate_samples_log.json"
        with open(dup_file, 'w', encoding='utf-8') as f:
            json.dump(duplicate_data, f, ensure_ascii=False, indent=4)
            
        print(f"[+] Đã phát hiện và xoá thành công {removed_count} mẫu có câu hỏi trùng lặp.")
        print(f"[*] Các mẫu bị loại này đã được sao lưu toàn vẹn vào file '{dup_file}' để bạn tra cứu.")
        print(f"[+] Dữ liệu hiện tại còn {len(unique_data)} câu hỏi/đáp án (duy nhất).")
    else:
        print("[+] Tuyệt vời! Không phát hiện câu hỏi nào trùng lặp. Giữ nguyên file gốc.")

def remove_duplicates_from_data(data):
    unique_data = []
    duplicate_data = []
    seen_questions = set()
    
    for item in data:
        # Chuyển về quét trùng lặp chỉ trên cột "question" theo yêu cầu
        question_text = item.get("question", "").strip().lower()
        
        if question_text not in seen_questions:
            seen_questions.add(question_text)
            unique_data.append(item)
        else:
            duplicate_data.append(item)
            
    return unique_data, duplicate_data

if __name__ == "__main__":
    # Trỏ đích xác vào file JSON chứa đống câu hỏi
    json_file_path = "data_agent.json"
    remove_duplicates(json_file_path)
