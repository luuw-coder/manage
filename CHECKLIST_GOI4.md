# Bảng test gói 4 (Đạt / Không đạt) — thử trên Windows có Moho

Chuẩn bị: mở Moho 14, **mở một dự án** (File → New). Mở Manage Moho, thêm thư mục có vài ảnh PNG, một tệp WAV và một tệp .moho.

| # | Làm | Phải thấy |
|---|-----|-----------|
| 1 | **Chuột phải** vào một thẻ tệp bất kỳ | Menu hiện ra bình thường (gói trước bị lỗi ở bước này), có dòng **Gửi vào Moho (hộp thoại Nhập)** |
| 2 | Quản lý → tab **Ứng dụng đích** → **Kiểm tra kết nối** | Báo "Đạt: thấy Moho ... và hộp thoại ... hiện ra". Nếu báo "Không thấy hộp thoại Nhập": vào Moho xem phím tắt ở File → Import, sửa ô Phím tắt Nhập, Lưu, thử lại |
| 3 | Chuột phải một ảnh PNG → **Gửi vào Moho** | Moho lên trước, hộp thoại Nhập hiện rồi tự điền và đóng; ảnh vào dự án (Moho có thể hỏi Tracing Image / New Image Layer) |
| 4 | Chuột phải tệp WAV → **Gửi vào Moho** | Âm thanh vào dự án |
| 5 | Chọn 3 tệp (Ctrl+nhấp) → chuột phải → **Gửi vào Moho** | Gửi lần lượt; nếu Moho hỏi giữa chừng thì phần mềm dừng và báo, trả lời xong gửi tiếp |
| 6 | Chuột phải tệp .moho → **Gửi vào Moho** | Moho mở dự án đó (dùng Ctrl+O) |
| 7 | Chuột phải ảnh → **Dán ảnh vào Moho (Ctrl+V)** | Ảnh vào Moho thành lớp ảnh mới |
| 8 | Nhấp đúp một ảnh | Bảng thông tin có nút vàng **Gửi vào Moho** |
| 9 | Kéo một thẻ ảnh vào vùng làm việc của Moho (cách cũ) | Hoạt động như trước; nếu Moho không hiện tệp, thông báo gợi ý dùng "Gửi vào Moho" |
| 10 | Ứng dụng đích → **Thêm ứng dụng** (ví dụ Krita), điền từ khóa .exe và phím tắt, Lưu | Menu chuột phải đổi thành "Gửi vào Krita"; nút "Về …" đưa Krita lên trước |
| 11 | Ứng dụng đích → chọn Krita → **Xóa** | Trở về Moho; hồ sơ có sẵn (Moho, Premiere...) không xóa được |
| 12 | Chạy Moho bằng "Run as administrator" rồi thử Gửi | Báo rõ cần mở cả hai cùng quyền |

Nếu bước 3 không đạt, gửi mình: (1) kết quả bước 2, (2) tệp `keo.log` trong `%APPDATA%\ManageMoho`, (3) phím tắt ghi cạnh File → Import trong Moho của bạn.
