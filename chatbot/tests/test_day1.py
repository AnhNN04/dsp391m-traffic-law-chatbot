import requests
import sys

# Cấu hình URL
BASE_URL = "http://localhost:8000/api/v1"
# Tài khoản test (Thay đổi email nếu chạy lại nhiều lần để tránh lỗi duplicate)
EMAIL = "day1_test@example.com"
PASSWORD = "test_passwd"

def test_flow():
    print("🚀 BẮT ĐẦU KIỂM THỬ NGÀY 1...")

    # 1. Đăng ký (Register)
    print("\n1️⃣ Đang test Đăng ký...")
    register_payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "full_name": "Automated Tester"
    }
    try:
        reg_res = requests.post(f"{BASE_URL}/auth/register", json=register_payload)
        
        if reg_res.status_code == 200:
            print("✅ Đăng ký thành công!")
            print(f"   Response: {reg_res.json()}")
        elif reg_res.status_code == 400 and "đã được đăng ký" in reg_res.text:
            print("⚠️ Email đã tồn tại (Pass qua bước này để test login).")
        else:
            print(f"❌ Đăng ký thất bại: {reg_res.text}")
            # Không dừng lại, thử login xem tài khoản cũ có vào được không
    except Exception as e:
        print(f"❌ Lỗi kết nối server: {e}")
        print("💡 Gợi ý: Kiểm tra xem bạn đã chạy 'python main.py' chưa?")
        sys.exit(1)

    # 2. Đăng nhập (Login)
    print("\n2️⃣ Đang test Đăng nhập...")
    # Lưu ý: OAuth2PasswordRequestForm yêu cầu gửi data dạng Form (ko phải JSON)
    # và field tên là 'username' chứ ko phải 'email'
    login_data = {
        "username": EMAIL,  
        "password": PASSWORD
    }
    login_res = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    
    if login_res.status_code == 200:
        token_data = login_res.json()
        access_token = token_data["access_token"]
        print("✅ Đăng nhập thành công!")
        print(f"   Token nhận được: {access_token[:20]}...")
    else:
        print(f"❌ Đăng nhập thất bại: {login_res.text}")
        sys.exit(1)

    # 3. Truy cập route bảo vệ (/me)
    print("\n3️⃣ Đang test truy cập API bảo mật (/me)...")
    headers = {"Authorization": f"Bearer {access_token}"}
    me_res = requests.get(f"{BASE_URL}/auth/me", headers=headers)

    if me_res.status_code == 200:
        user_info = me_res.json()
        print("✅ Truy cập thành công!")
        print(f"   Xin chào: {user_info['full_name']} (ID: {user_info['id']})")
    else:
        print(f"❌ Truy cập thất bại: {me_res.text}")
        sys.exit(1)

    print("\n🎉 CHÚC MỪNG! BẠN ĐÃ HOÀN THÀNH XUẤT SẮC NGÀY 1.")

if __name__ == "__main__":
    test_flow()