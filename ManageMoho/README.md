# Manage Moho (bước 1)

Phần mềm Windows chạy song song với Moho Pro để lấy tài nguyên nhanh.
Phần mềm chỉ lưu LIÊN KẾT tới tệp, không bao giờ xóa/đổi tên/di chuyển tệp thật.

## Đưa lên GitHub và tải bộ cài về

1. Vào github.com, đăng nhập, bấm dấu **+** (góc trên phải) → **New repository**.
2. Đặt tên `ManageMoho`, chọn **Private**, bấm **Create repository**.
3. Ở trang kho mới, bấm **uploading an existing file**.
4. Giải nén file zip này, mở thư mục `ManageMoho`, chọn TẤT CẢ bên trong (kể cả thư mục `.github`) rồi kéo thả vào trang GitHub.
   - Nếu không thấy thư mục `.github` (Windows ẩn nó): trong File Explorer bấm **Xem (View) → Hiện (Show) → Mục ẩn (Hidden items)**.
5. Kéo xuống bấm **Commit changes**.
6. Bấm tab **Actions**. Một mục "Build Manage Moho" sẽ tự chạy (khoảng 5–10 phút, có vòng tròn vàng).
7. Khi hiện dấu tick xanh, bấm vào mục đó, kéo xuống phần **Artifacts**, tải `ManageMoho-Setup` về, giải nén ra `ManageMoho_Setup.exe` và cài.
   - Dấu X đỏ nghĩa là có lỗi: bấm vào, chụp màn hình phần chữ đỏ gửi cho Claude.
8. Windows có thể báo "Windows protected your PC": bấm **More info → Run anyway** (bộ cài chưa có chữ ký số).

## Dữ liệu lưu ở đâu
`%APPDATA%\ManageMoho\manage_moho.db`. Gỡ phần mềm không xóa file này.
