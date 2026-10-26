# Bảng test gói 4 (Đạt / Không đạt) — thử trên Windows có Moho

Chuẩn bị: mở Moho 14, **mở một dự án** (File → New). Mở Manage Moho, thêm thư mục có vài ảnh PNG, một tệp WAV.

| # | Làm | Phải thấy |
|---|-----|-----------|
| 1 | Chuột phải một thẻ tệp | Menu hiện bình thường (gói trước bị lỗi), có **Gửi vào Moho** và mục "dự phòng" |
| 2 | Quản lý → **Ứng dụng đích** → **Cài script vào Moho...** → chọn Custom Content Folder (lấy ở Moho → Edit → Preferences) | Báo "Đã cài script: ...\Scripts\Menu\ManageMoho_Import.lua" |
| 3 | **Khởi động lại Moho**, mở dự án, xem menu **Scripts** | Có **Manage Moho - Import**. Bấm thử: Moho báo "nothing to import" (nghĩa là script chạy) |
| 4 | Chuột phải một ảnh PNG → **Gửi vào Moho** | Hoặc ảnh vào ngay, hoặc Manage Moho báo "Đã xếp tệp vào hàng đợi": bấm Scripts → Manage Moho - Import, ảnh thành lớp mới tên theo tệp |
| 5 | Chuột phải tệp WAV → Gửi vào Moho (rồi bấm menu nếu cần) | Có lớp âm thanh mới |
| 6 | Chọn 3 tệp → Gửi vào Moho | Cả 3 thành 3 lớp |
| 7 | (Tùy chọn) Gán phím tắt cho script trong Moho, ghi vào ô "Phím tắt gọi script", Lưu, gửi lại | Không cần bấm menu nữa; Manage Moho báo "Đã gửi vào Moho: ..." |
| 8 | Mở Adobe Animate + một tài liệu, chọn ứng dụng **Adobe Animate** trong tab Ứng dụng đích, Lưu; chuột phải ảnh → Gửi vào Adobe Animate | Ảnh xuất hiện trên sân khấu Animate |
| 9 | Kéo thả cũ vào Moho | Như trước (nếu Moho không hiện, dùng bước 4) |
| 10 | Nhấp đúp ảnh | Có nút vàng **Gửi vào Moho** |

Nếu bước 3 hoặc 4 không đạt, gửi mình: (1) thư mục bạn đã chọn ở bước 2, (2) ảnh chụp menu Scripts của Moho, (3) tệp `keo.log` trong `%APPDATA%\ManageMoho`, (4) nếu Moho hiện lỗi Lua thì chụp cửa sổ Lua Console (Window → Lua Console nếu có).
