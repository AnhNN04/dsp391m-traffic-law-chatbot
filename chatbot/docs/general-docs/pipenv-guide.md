# Hướng dẫn sử dụng Pipenv

## Giới thiệu
Pipenv là một công cụ quản lý môi trường và gói Python, giúp đơn giản hóa việc cài đặt và quản lý các thư viện cần thiết cho dự án. Pipenv kết hợp cả **Pip** và **Virtualenv**, giúp đảm bảo môi trường phát triển đồng nhất.

---

## Cài đặt Pipenv
### 1. Kiểm tra Python và Pip
Trước tiên, đảm bảo bạn đã cài đặt Python và Pip:
```bash
python --version
pip --version
```

### 2. Cài đặt Pipenv
Cài đặt Pipenv bằng lệnh:
```bash
pip install pipenv
```
Kiểm tra cài đặt thành công:
```bash
pipenv --version
```

---

## Sử dụng Pipenv trong dự án

### 1. Tạo môi trường mới
Di chuyển vào thư mục dự án và chạy lệnh:
```bash
pipenv install
```
Lệnh này sẽ:
- Tạo môi trường ảo (virtual environment).
- Cài đặt các thư viện từ `Pipfile`.

### 2. Cài đặt thư viện mới
Để cài đặt thư viện mới, sử dụng lệnh:
```bash
pipenv install <tên_thư_viện>
```
Ví dụ:
```bash
pipenv install requests
```

### 3. Chạy ứng dụng trong môi trường ảo
Để chạy ứng dụng trong môi trường ảo, sử dụng lệnh:
```bash
pipenv run python <tên_file>
```
Ví dụ:
```bash
pipenv run python main.py
```

### 4. Kích hoạt môi trường ảo
Nếu muốn vào môi trường ảo để chạy lệnh thủ công:
```bash
pipenv shell
```
Thoát khỏi môi trường ảo:
```bash
exit
```

### 5. Kiểm tra các thư viện đã cài đặt
Để xem danh sách các thư viện đã cài đặt:
```bash
pipenv graph
```

### 6. Khóa phiên bản thư viện
Sau khi cài đặt hoặc cập nhật thư viện, chạy lệnh:
```bash
pipenv lock
```
Lệnh này sẽ cập nhật file `Pipfile.lock` để lưu trạng thái các thư viện.

---

## Các lệnh hữu ích khác
- **Gỡ bỏ thư viện**:
  ```bash
  pipenv uninstall <tên_thư_viện>
  ```
- **Xóa môi trường ảo**:
  ```bash
  pipenv --rm
  ```
- **Kiểm tra lỗi môi trường**:
  ```bash
  pipenv check
  ```

---

## Lưu ý
- **Pipfile**: Chứa danh sách các thư viện cần thiết.
- **Pipfile.lock**: Khóa phiên bản thư viện để đảm bảo môi trường đồng nhất.
- Luôn sử dụng `pipenv install` thay vì `pip install` để đảm bảo môi trường được quản lý đúng cách.

---

## Tài liệu tham khảo
- [Pipenv Documentation](https://pipenv.pypa.io/en/latest/)