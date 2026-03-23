import os
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --------------------------------------------------------- #
# 1. Các hàm xử lý Web Driver & Giao tiếp mạng
# --------------------------------------------------------- #

def init_driver():
    """Khởi tạo trình duyệt Selenium ẩn."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.page_load_strategy = 'eager'
    driver = webdriver.Chrome(options=options)
    return driver

def fetch_html(driver, url, wait_for_classname=None, timeout=15):
    """Tải một trang web và trả về page_source."""
    try:
        driver.set_page_load_timeout(timeout)
        driver.get(url)
    except TimeoutException:
        print(f"  [-] Timeout khi tải: {url} (Vẫn tiếp tục đọc HTML hiện tại)")
    
    if wait_for_classname:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, wait_for_classname))
            )
        except TimeoutException:
            print(f"  [-] Không đợi được element '{wait_for_classname}' trên {url}")
            return None
    time.sleep(1) # Chờ Dom ổn định
    
    return driver.page_source

# --------------------------------------------------------- #
# 2. Các hàm phân tích danh sách bài viết
# --------------------------------------------------------- #

def extract_article_metadata(article_soup):
    """Trích xuất url, danh sách tag và ngày đăng từ một thẻ article_soup (news-card)"""
    link_tag = article_soup.find("a", class_="title-link")
    if not link_tag or not link_tag.get("href"):
        return None, [], None
        
    article_url = link_tag["href"]
    if article_url.startswith("/"):
        article_url = "https://thuvienphapluat.vn" + article_url
        
    keyword_container = article_soup.find("div", class_="keyword")
    article_tags = []
    if keyword_container:
        span_tags = keyword_container.find_all("span")
        article_tags = [span.get_text(strip=True).lower() for span in span_tags]
        
    # Lấy thông tin ngày đăng từ thẻ <span class="sub-time">
    time_tag = article_soup.find("span", class_="sub-time")
    article_date = ""
    if time_tag:
        time_text = time_tag.get_text(strip=True)  # ví dụ: "16:30 | 13/08/2025"
        parts = time_text.split('|')
        if len(parts) > 1:
            article_date = parts[1].strip()  # "13/08/2025"
        else:
            article_date = time_text.strip()
            
    return article_url, article_tags, article_date

def is_article_matching_tags(article_tags, target_tags):
    """Kiểm tra xem danh sách tag của bài viết có khớp với target_tags không."""
    for tag in article_tags:
        for target in target_tags:
            if target in tag:
                return True
    return False

def get_valid_links_from_page(html_source, target_tags, min_date_str="01/01/2025"):
    """Quét trang danh sách, lọc những bài viết khớp keyword và đăng từ ngày min_date trở về sau."""
    if not html_source:
        return []
        
    soup = BeautifulSoup(html_source, "html.parser")
    articles = soup.find_all("article", class_="news-card")
    
    # Ép kiểu chuẩn cấu trúc định dạng mốc ngày (dd/mm/yyyy)
    try:
        min_date_obj = datetime.strptime(min_date_str, "%d/%m/%Y")
    except ValueError:
        min_date_obj = None
        
    valid_links = []
    reached_end_date = False
    
    for article in articles:
        url, tags, date_str = extract_article_metadata(article)
        
        # Kiểm tra niên hạn thời gian trước hết
        if min_date_obj and date_str:
            try:
                # Parse ngày của bài (VD: "13/08/2025")
                article_date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                # Lọc: Nếu ngày đăng bài nhỏ (cũ) hơn mốc thời gian thì bỏ qua bài này
                if article_date_obj < min_date_obj:
                    # Bật cờ thông báo đã cào tới những bài viết cũ hơn mốc thời gian cho phép
                    reached_end_date = True
                    continue 
            except ValueError:
                pass # Lỗi parse ngày bị hỏng thì vẫn châm chước duyệt cho an toàn
                
        # Chỉ lấy bài viết nếu bài viết thoả tag (vừa đúng thời gian vừa đúng nội dung)
        if url and is_article_matching_tags(tags, target_tags):
            valid_links.append((url, date_str))
            
    return valid_links, reached_end_date

# --------------------------------------------------------- #
# 3. Các hàm bóc tách dữ liệu bài viết (Detail Parsing)
# --------------------------------------------------------- #

def clean_html_content(content_soup):
    """Loại bỏ thẻ script, style và dọn dẹp nội dung."""
    for tag in content_soup(["script", "style"]):
        tag.decompose()
    return content_soup

def extract_context_sapo(content_soup):
    """Lấy đoạn sapo (phần bôi đậm đầu tiên, thường chứa context chunng)."""
    strong_tags = content_soup.find_all("strong")
    if strong_tags:
        return strong_tags[0].get_text(strip=True)
    return ""

def extract_qna_pairs(title_text, content_soup, sapo_text):
    """
    Bóc tách các cặp Câu hỏi - Trả lời.
    Heuristic: Tìm các thẻ thay đổi bối cảnh (heading h2, h3... hoặc p chứa chữ in đậm) để cắt nhỏ theo từng câu hỏi.
    Dữ liệu pháp luật thường có thẻ blockquote nên phải xử lý thêm thẻ này.
    """
    pairs = []
    current_question = title_text
    current_answer = []
    
    # Lặp qua tất cả thẻ con trực tiếp của #news-content
    for element in content_soup.children:
        # Đã bổ sung 'blockquote' để lấy luật được trích dẫn
        if element.name not in ['p', 'div', 'h2', 'h3', 'h4', 'ul', 'ol', 'table', 'blockquote']:
            continue
            
        text = element.get_text(strip=True)
        if not text:
            continue
            
        # Tránh đưa cả đoạn sapo vào lại đáp án nếu nó là đoạn đầu tiên rời rạc
        if sapo_text and text == sapo_text:
            continue
            
        is_new_question = False
        
        # Heuristic phát hiện câu hỏi mới:
        # 1. Là thẻ tiêu đề (h2, h3, h4) như bạn ví dụ
        if element.name in ['h2', 'h3', 'h4']:
            is_new_question = True
        # 2. Dự phòng: Hoặc là một thẻ p/div chủ yếu chứa thẻ in đậm (strong/b) và giống câu hỏi
        elif element.name in ['p', 'div']:
            strong_tag = element.find(['strong', 'b'])
            if strong_tag:
                strong_text = strong_tag.get_text(strip=True)
                if len(strong_text) > 5 and len(strong_text) >= len(text) * 0.8:
                    if strong_text.endswith('?') or strong_text.lower().startswith('câu '):
                        is_new_question = True

        if is_new_question:
            # Lưu câu hỏi và câu trả lời trước đó (nếu có nội dung trải lời thực tế)
            if current_answer and ''.join(current_answer).strip():
                pairs.append({
                    "question": current_question,
                    "answer": "\n\n".join(current_answer)
                })
            # Reset biến cho câu hỏi mới
            current_question = text
            current_answer = []
        else:
            # Thêm dòng văn bản vào câu trả lời hiện tại
            current_answer.append(text)
                
    # Lưu QnA pair cuối cùng của tập dữ liệu
    if current_question and current_answer:
        pairs.append({
            "question": current_question,
            "answer": "\n\n".join(current_answer)
        })
        
    return pairs

def parse_article_detail(html_source, url, article_date):
    """Điều phối bóc tách HTML chi tiết thành danh sách các data dict (một trang có thể ra >= 1 bộ pair QnA)."""
    if not html_source:
        return []
        
    soup = BeautifulSoup(html_source, "html.parser")
    title_element = soup.select_one("h1.title")
    if not title_element:
        return []
        
    title_text = title_element.get_text(strip=True)
    content_soup = soup.select_one("#news-content")
    if not content_soup:
        return []
        
    content_soup = clean_html_content(content_soup)
    sapo_text = extract_context_sapo(content_soup)
    
    qna_pairs = extract_qna_pairs(title_text, content_soup, sapo_text)
    
    results = []
    for pair in qna_pairs:
        results.append({
            "question": pair["question"],
            "context": sapo_text,
            "answer": pair["answer"],
            "date": article_date,
            "url": url
        })
        
    return results

# --------------------------------------------------------- #
# 4. Các hàm lưu trữ dữ liệu (I/O)
# --------------------------------------------------------- #

def save_results_to_json(data, output_file):
    """Ghi tiếp vào file JSON cũ bằng cách đọc ra, nối thêm và ghi trở lại."""
    if not data:
        return

    existing_data = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            print(f"  [-] Lỗi đọc file cũ (file bị lỗi cấu trúc), hệ thống sẽ ghi đè file mới.")

    existing_data.extend(data)
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
        print(f"  [+] Nối thêm thành công! Tổng số Q&A trong file hiện là: {len(existing_data)}")
    except Exception as e:
        print(f"  [-] Lỗi khi lưu file {output_file}: {e}")

# --------------------------------------------------------- #
# 5. Hàm chạy chính (Controller)
# --------------------------------------------------------- #

def main():
    target_tags = [
        "xe ô tô", "biển số xe", "xe máy", "vi phạm giao thông", 
        "biển số xe ô tô", "đăng kiểm xe", "chạy quá tốc độ", 
        "giao thông đường bộ", "nồng độ cồn", "giấy phép lái xe"
    ]
    base_url = "https://thuvienphapluat.vn/hoi-dap-phap-luat/giao-thong-van-tai"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(current_dir))
    data_dir = os.path.join(base_dir, "benchmark", "benchmark_data")
    output_file = os.path.join(data_dir, "raw", "raw_benchmark_data.json")
    
    # Cấu hình lọc bài viết từ mốc ngày/tháng/năm cụ thể
    filter_min_date = "01/01/2025"
    
    driver = init_driver()
    all_results = []
    
    # Cấu hình số trang để chạy
    start_page = 1
    end_page = 50
    
    try:
        for page in range(start_page, end_page + 1):
            url = f"{base_url}?page={page}" if page > 1 else base_url
            print(f"==> Đang quét trang {page}: {url} (Lấy từ ngày {filter_min_date})")
            
            html_list = fetch_html(driver, url, wait_for_classname="news-card")
            
            if not html_list:
                print("  --> Không có dữ liệu HTML hoặc lỗi mạng. Bỏ qua trang này!")
                continue
                
            valid_links, reached_end_date = get_valid_links_from_page(html_list, target_tags, min_date_str=filter_min_date)
            print(f"  --> Tìm thấy {len(valid_links)} bài viết khớp tags.")
            
            # Duyệt qua từng link bài chi tiết
            for link, article_date in valid_links:
                print(f"  [+] Đang lấy chi tiết: {link} (Ngày: {article_date})")
                
                # Quãng nghỉ 5 giây 1 trang để tránh chặn block request
                time.sleep(5)
                
                html_detail = fetch_html(driver, link)
                
                # Bóc tách
                article_qnas = parse_article_detail(html_detail, link, article_date)
                if article_qnas:
                    print(f"    --> Trích xuất được {len(article_qnas)} câu hỏi/trả lời từ bài viết này.")
                    all_results.extend(article_qnas)
                else:
                    print(f"    --> Không trích xuất được dữ liệu cho link này.")
            
            # (Đã bỏ cơ chế break tự động ở đây để bạn có thể quét thoải mái số trang đã cài)
                
            # Chuẩn bị sang trang tiếp theo 
            # Quãng nghỉ 5s khi chuyển sang trang danh sách tiếp theo đề phòng bị chặn
            time.sleep(5)

    finally:
        driver.quit()
        
    print(f"\n==============================================")
    print(f"Hoàn thành! Tổng cộng đã cào được {len(all_results)} câu hỏi/đáp.")
    print(f"==============================================")
    
    # Cuối cùng lưu toàn bộ ra JSON
    save_results_to_json(all_results, output_file)

if __name__ == "__main__":
    main()
