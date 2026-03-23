import json
import re
import os

def fix_vietnamese_glued_words(text):
    if not text:
        return text
        
    # 1. Chữ HOA liên tiếp (từ viết tắt) dính liền chữ thường (vd: BGTVTquy định -> BGTVT quy định)
    text = re.sub(r'([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]{2,})([a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])', r'\1 \2', text)
    
    # 2. Số dính liền chữ cái (vd: Điều 18Thông tư -> Điều 18 Thông tư, 2014quy -> 2014 quy)
    text = re.sub(r'(\d)([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐa-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])', r'\1 \2', text)
    
    # 3. Chữ thường dính liền chữ HOA (vd: địnhNghị -> định Nghị)
    text = re.sub(r'([a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])([A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ])', r'\1 \2', text)
    
    return text

def process_file(filepath="data_agent.json"):
    print(f"Đang tiến hành hậu xử lý (fix các lỗi dính chữ) trong {filepath}...")
    
    if not os.path.exists(filepath):
        print(f"File {filepath} không tồn tại!")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    data, fixed_count = fix_vietnamese_glued_words_in_data(data)

    print(f"[+] Đã kiểm tra và fix lỗi cách chữ thành công cho {fixed_count} mẫu Q&A.")
    
    # Ghi đè lại nội dung đã fix
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"[+] Toàn bộ dữ liệu sạch sẽ đã được sao lưu vào file gốc.")

def fix_vietnamese_glued_words_in_data(data):
    fixed_count = 0
    for item in data:
        orig_q = item.get("question", "")
        orig_a = item.get("answer", "")
        orig_c = item.get("context", "")
        
        new_q = fix_vietnamese_glued_words(orig_q)
        new_a = fix_vietnamese_glued_words(orig_a)
        new_c = fix_vietnamese_glued_words(orig_c)
        
        if new_q != orig_q or new_a != orig_a or new_c != orig_c:
            item["question"] = new_q
            item["answer"] = new_a
            item["context"] = new_c
            fixed_count += 1
            
    return data, fixed_count

if __name__ == "__main__":
    process_file()
