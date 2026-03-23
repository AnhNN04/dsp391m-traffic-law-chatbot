import subprocess
import os
import glob

def convert_all_docx_to_pdf(source_folder):
    # 1. Cấu hình đường dẫn LibreOffice (Kiểm tra kỹ đường dẫn này trên máy bạn)
    libreoffice_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
    
    if not os.path.exists(libreoffice_path):
        print(f"Lỗi: Không tìm thấy LibreOffice tại {libreoffice_path}")
        return

    # 2. Lấy danh sách tất cả file .docx và .doc trong thư mục
    # Sử dụng glob để quét file
    docx_files = glob.glob(os.path.join(source_folder, "*.docx"))
    
    if not docx_files:
        print(f"Không tìm thấy file Word nào trong thư mục: {source_folder}")
        return

    print(f"Tìm thấy {len(docx_files)} file. Bắt đầu chuyển đổi...")

    # 3. Vòng lặp chuyển đổi
    for file_path in docx_files:
        file_name = os.path.basename(file_path)
        
        # Lệnh chuyển đổi
        command = [
            libreoffice_path,
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', source_folder,  # Lưu PDF cùng thư mục với file gốc
            file_path
        ]

        try:
            print(f"--- Đang xử lý: {file_name}")
            # Chạy lệnh và đợi nó kết thúc trước khi sang file tiếp theo
            subprocess.run(command, check=True, shell=False)
        except Exception as e:
            print(f"❌ Lỗi khi chuyển đổi file {file_name}: {e}")

    print("\n✅ Hoàn thành tất cả!")

if __name__=='__main__':
    folder_path = r"C:\DSP\convert_to_md\data\raw_doc"
    convert_all_docx_to_pdf(folder_path)