# Bảng test (Đạt / Không đạt) — thử trên Windows

| # | Làm | Phải thấy |
|---|-----|-----------|
| 1 | Mở phần mềm | Biểu tượng phim đỏ FPM ở thanh tiêu đề và thanh tác vụ |
| 2 | Kéo một ảnh vào vùng làm việc của Moho (đang mở dự án) | Ảnh vào Moho (kiểu kéo B là mặc định) |
| 3 | Nhấn nút **?** trên thanh trên cùng | Mở Quản lý ở tab Hướng dẫn |
| 4 | Nhấp đúp một tệp .obj hoặc .stl | Mô hình 3D hiện ra; kéo chuột trái để xoay, lăn chuột để zoom, chuột phải để dịch, nhấp đúp về mặc định |
| 5 | Nhấp đúp tệp .fbx | Báo "Chưa xem được định dạng, xem được OBJ, STL" |
| 6 | Cắt một đoạn âm thanh, kéo vào Moho | Đoạn âm thanh vào Moho |
| 7 | Quản lý → Cài đặt: xem dòng "Đang có N tệp đã cắt, chiếm ..."; thử "Xóa hết tệp đã cắt" | Số liệu đúng; xóa xong về 0 |
| 8 | Cài đặt → "File âm thanh đã cắt" chọn một mức tự dọn rồi Lưu | Lần mở sau, tệp cũ hơn mức đã chọn bị xóa |
| 9 | Kịch bản → chọn Google AI → Mở | Khung chat AI hiện to thay cho danh sách tài khoản; nút ‹ Chọn AI để quay lại; không còn nút Gửi đoạn / Chép trả lời |
| 11 | Tải 1 tệp 3D lên, nhấp đúp xem, rồi tải thêm 1 tệp nữa | Cả hai thẻ nằm cùng một hàng và đều bấm, xem, kéo được |
| 10 | Nếu trang không cho đăng nhập trong khung → bấm **Cửa sổ riêng** | Mở bằng Chrome/Edge như trước |
| 12 | Cắt một đoạn âm thanh, kéo vào Moho; mở thư mục `%APPDATA%\ManageMoho\exports` | Chỉ có 1 tệp .mp3 nhỏ (cắt lại đúng đoạn cũ không đẻ thêm tệp) |
| 13 | Kéo đoạn cắt ra ngoài chỗ không nhận (ví dụ màn hình nền) | Tệp vừa tạo tự bị xóa |
| 14 | Cắt chọn cả bài rồi kéo vào Moho | Không tạo tệp mới trong exports (dùng luôn tệp gốc) |
| 15 | Trên GitHub Actions: tải 2 bản `ManageMoho-Setup_Nhe` và `ManageMoho-Setup_DayDu` | Bản Nhẹ nhỏ hơn rất nhiều; AI ở bản Nhẹ mở bằng cửa sổ Chrome/Edge riêng |
| 16 | Quản lý → Cài đặt → bấm "Dọn rác ngay" | Báo đã dọn và dung lượng giải phóng; kịch bản, mục, đăng nhập vẫn còn |
| 17 | Gỡ cài đặt phần mềm (Settings → Apps) | Hỏi có xóa dữ liệu cá nhân không; chọn Không thì thư mục `%APPDATA%\ManageMoho` còn kịch bản/cài đặt nhưng hết `testdrag`, `keo.log`; chọn Có thì xóa sạch; thư mục `C:\Users\Public\ManageMoho` mất; script trong Moho đã gỡ |
