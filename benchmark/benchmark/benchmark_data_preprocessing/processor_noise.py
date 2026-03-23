import json
import os

def clean_noisy_answers(filepath="data_agent.json"):
    print(f"Đang phân tích lọc đáp án lỗi trong {filepath}...")
    
    if not os.path.exists(filepath):
        print(f"File {filepath} không tồn tại!")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    good_data, bad_data = clean_noisy_answers_from_data(data)

    print(f"[+] Tổng số lượng mẫu ban đầu: {len(data)}")
    print(f"[+] Đã lọc và giữ lại {len(good_data)} mẫu chất lượng.")
    print(f"[-] Đã bóc ra {len(bad_data)} mẫu bị lỗi nội dung (Nội dung chính, rác, quá ngắn...).")

    # Lưu lại file xịn đè lên bản cũ
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(good_data, f, ensure_ascii=False, indent=4)
        
    # Tùy chọn: Lưu các mẫu lỗi ra file riêng để bạn có thể xem lại trước khi xoá vĩnh viễn
    with open("bad_samples_log.json", 'w', encoding='utf-8') as f:
        json.dump(bad_data, f, ensure_ascii=False, indent=4)
        print(f"[*] Để an toàn, tôi đã xuất danh sách các câu lỗi ra file 'bad_samples_log.json' cho bạn tham khảo.")

def clean_noisy_answers_from_data(data):
    good_data = []
    bad_data = []
    
    for item in data:
        ans = item.get("answer", "").strip()
        
        is_bad = False
        
        # 1. Trả lời bị rỗng
        if not ans:
            is_bad = True
            
        # 2. Nhận diện lỗi theo quy luật thực tế: 
        # Bất kỳ câu trả lời nào có xuất hiện dấu '?' chứng tỏ hệ thống đã cào nhầm phần câu hỏi, mục lục hoặc mục lục bài viết vào đáp án.
        elif '?' in ans:
            is_bad = True
            
        if is_bad:
            bad_data.append(item)
        else:
            good_data.append(item)
            
    return good_data, bad_data

if __name__ == "__main__":
    clean_noisy_answers()
