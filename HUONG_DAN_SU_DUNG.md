# Manage Moho – Hướng dẫn sử dụng

Manage Moho là cửa sổ nhỏ chạy cạnh Moho (hoặc phần mềm khác) để lấy tài nguyên nhanh: ảnh, âm thanh, GIF, video, model 3D, dự án, vector, tài liệu... mà không phải mở This PC nhiều lần.

---

## 1. Cài đặt và mở lần đầu

1. Chạy `ManageMoho_Setup.exe` (lấy từ GitHub: tab **Actions** → lần chạy mới nhất → mục **Artifacts** → `ManageMoho-Setup`).
2. Mở Manage Moho. Lần đầu sẽ thấy màn hình trống "Chưa có thư mục nào".
3. Bấm nút lớn **Tải thư mục lên** và chọn thư mục chứa tài nguyên (hoặc kéo thả thư mục từ máy vào cửa sổ). Muốn tải tệp lẻ thì đổi chế độ ở hàng nút trên cùng.

## 2. Các mục

- Hàng biểu tượng có sẵn: Tất cả, Ảnh, Âm thanh, GIF, Video, Model 3D, Dự án, Vector, Tài liệu, Yêu thích.
- Một tệp có thể nằm trong nhiều mục.
- Chuột phải vào mục để sửa tên/biểu tượng, đổi bộ lọc, dời trái/phải hoặc xóa.
- Nút **+** (hàng riêng bên dưới) để thêm mục mới, chọn biểu tượng hoặc ảnh cho nút.
- Bộ lọc định dạng mặc định là **TẤT CẢ**.

## 3. Duyệt, xem trước, thao tác với tệp

- Thư mục và tệp là thẻ chữ nhật; nhấp vào thư mục để mở, nút mũi tên để quay ra.
- Mỗi trang tối đa 25 mục, chuyển trang bằng thanh số ở cạnh dưới.
- **Nhấp đúp** một tệp: bảng thông tin trượt lên, có xem ảnh, chạy GIF/video, nghe âm thanh.
- Rê chuột vào thẻ âm thanh thì tự phát; GIF/video chạy ngay trên thẻ (tắt được ở Quản lý → Cài đặt).
- **Chuột phải** một tệp: xem trước, mở, yêu thích, ghim, đổi tên hiển thị (không đổi tên tệp thật), thêm vào mục khác, sao chép đường dẫn, **Gửi vào Moho**.
- Nút **Đọc lại** (hàng nút trên cùng) chỉ cập nhật mục đang mở; tên hiển thị về như tên tệp gốc.

## 4. Đưa tệp vào Moho

### 4.0 Kéo thả trực tiếp – tìm kiểu kéo mà Moho nhận (làm 1 phút)
Moho nhận kéo thả bình thường (tool AA09 cũng kéo được), nên cần chọn đúng **kiểu kéo** của Manage Moho:
1. Mở Moho và **mở một dự án**.
2. Manage Moho → **Quản lý → Cài đặt**, kéo xuống phần "Kiểm tra kéo thả" có 4 ô: A, B, C, D.
3. Giữ chuột vào ô A, kéo vào **vùng làm việc của Moho**, thả. Xem có ảnh vàng hiện trong Moho không. Làm lần lượt B, C, D.
4. Ô nào làm ảnh hiện ra thì chọn kiểu đó ở mục **Kiểu kéo thả**, bấm Lưu. Từ đó kéo thẻ tệp nào cũng dùng kiểu đó.
5. Báo kết quả (ô nào được / không ô nào được) cho người hỗ trợ.

Nếu không ô nào được, dùng cách Script bên dưới.

### 4.1 Cách chắc nhất: Script (làm 1 lần, dùng mãi)

Kéo thả giữa hai phần mềm phụ thuộc vào việc Moho có chịu nhận hay không. Các công cụ khác (ví dụ MohoMCP) không dựa vào kéo thả mà **chạy một script Lua ngay trong Moho**, nên Manage Moho cũng làm như vậy: nó xếp danh sách tệp vào hàng đợi, script trong Moho đọc hàng đợi và tạo lớp ảnh/lớp âm thanh bằng lệnh chính thức của Moho, rồi báo kết quả ngược lại.

### Cài script (chỉ một lần)
1. Trong Moho: **Edit → Preferences → General**, bấm nút **Custom Content Folder** (nếu chưa đặt thì đặt một thư mục bất kỳ; Moho sẽ tự tạo các thư mục con).
2. Trong Manage Moho: **Quản lý → Ứng dụng đích → Cài script vào Moho...** rồi chọn đúng thư mục Custom Content đó.
3. **Khởi động lại Moho.** Trong menu **Scripts** sẽ có **Manage Moho - Import**.

### Dùng hằng ngày
1. Mở Moho và **mở một dự án**.
2. Trong Manage Moho: **chuột phải tệp → Gửi vào Moho** (hoặc nhấp đúp tệp rồi bấm nút vàng **Gửi vào Moho**). Chọn nhiều tệp cũng được.
3. Phần mềm tự thử bấm menu script. Nếu không tự bấm được, nó báo "Đã xếp tệp vào hàng đợi": bạn vào Moho bấm **Scripts → Manage Moho - Import** một lần là tệp vào dự án.
4. Muốn khỏi bấm menu: trong Moho gán phím tắt cho script (**Edit → Keyboard Shortcuts**, tìm Manage Moho - Import), rồi ghi phím đó vào ô **Phím tắt gọi script** ở tab Ứng dụng đích. Từ đó mọi thứ tự động.

Script nhập được: ảnh (PNG, JPG, BMP, TGA, GIF), video (AVI, MOV, MP4), âm thanh (WAV, MP3, M4A, AIFF), vector (AI, EPS). Mỗi tệp thành một lớp mới đặt tên theo tên tệp. PSD, .obj, .moho dùng File → Import hoặc kéo thả của Moho.

### Hai cách dự phòng
- **Kéo thả**: kéo thẻ tệp vào vùng làm việc của Moho (cần dự án đang mở, Moho và Manage Moho cùng quyền, không có hộp thoại nào đang mở).
- **Gửi bằng hộp thoại Nhập (dự phòng)**: chuột phải tệp → mục có chữ "dự phòng". Phần mềm bấm phím Nhập của Moho (mặc định `Ctrl+Shift+Y`) và điền tệp vào hộp thoại. Phím này sửa được ở tab Ứng dụng đích.
- **Dán ảnh Ctrl+V**: chỉ cho ảnh, dùng khi hai cách trên không được.

## 5. Adobe Animate và phần mềm khác

**Adobe Animate** (có sẵn trong tab Ứng dụng đích): chuột phải tệp → **Gửi vào Adobe Animate**. Phần mềm tạo một tệp lệnh JSFL (`importFile`) rồi chạy bằng `Animate.exe tệp.jsfl -AlwaysRunJSFL` – cách Adobe ghi trong tài liệu để chạy lệnh vào Animate đang mở. Điều kiện: Animate đang chạy và **đã mở một tài liệu**. Tệp được nhập lên sân khấu.

**Phần mềm khác**: **Quản lý → Ứng dụng đích → Thêm ứng dụng**, đặt tên, ghi **từ khóa tên .exe** (xem trong Task Manager), **Phím tắt Nhập** của phần mềm đó, chọn cách gửi **Hộp thoại Nhập**, bấm Lưu rồi **Kiểm tra kết nối**. Có sẵn gợi ý cho Premiere Pro, After Effects, Photoshop (phím mặc định của chúng; sửa nếu bạn đã đổi phím).

## 6. Cắt âm thanh

Chuột phải một tệp âm thanh → **Cắt âm thanh...** → xuất hiện dạng sóng; kéo dài/ngắn, **bôi đen** đoạn cần lấy rồi **giữ chuột kéo thẳng vùng bôi đen** sang Moho. Tệp gốc không bị đổi.

## 7. Kịch bản

Nút **Kịch bản** ở thanh dưới mở cửa sổ riêng, chia 3 vùng (kéo thanh chia để chỉnh kích thước): hỏi AI ở trên-trái, danh sách kịch bản ở dưới-trái, trình soạn kịch bản ở bên phải (phân cảnh, lời thoại, hành động, đậm/nghiêng/gạch chân, màu chữ, căn dòng). Kịch bản lưu dạng `.txt` kèm bản `.html` giữ màu và căn dòng. Đóng cửa sổ chính thì cửa sổ Kịch bản không bị đóng theo.

## 8. Nút ở thanh trên cùng

Luôn nổi trên đầu · Làm mờ (thanh trượt, tự mờ khi chuột rời cửa sổ) · Về ứng dụng đích (đưa Moho/phần mềm đang chọn lên trước) · Đọc lại · Thu gọn/mở rộng.

## 9. Sao lưu

**Quản lý → Sao lưu**: lưu các mục, thư mục nguồn, tên hiển thị, yêu thích, ghim, cài đặt, danh sách ứng dụng đích, kịch bản. Không lưu các tệp tài nguyên thật và không lưu mật khẩu.

## 10. Khi gặp sự cố

| Triệu chứng | Làm gì |
|---|---|
| Gửi vào Moho báo "Đã xếp tệp vào hàng đợi" | Bình thường nếu chưa gán phím tắt: vào Moho bấm Scripts → Manage Moho - Import. |
| Báo "không phản hồi / script có thể chưa được cài" | Cài script (mục 4), khởi động lại Moho, mở dự án. |
| Không thấy "Manage Moho - Import" trong menu Scripts | Thư mục Custom Content chọn chưa đúng với thư mục Moho đang dùng (xem Moho → Edit → Preferences → Custom Content Folder), hoặc chưa khởi động lại Moho. |
| Một số tệp báo lỗi | Loại tệp script chưa hỗ trợ (PSD, .obj...) hoặc tên tệp có chữ có dấu mà Moho không đọc được: thử đổi tên tệp thành không dấu. |
| Kéo thả được nhưng Moho không hiện tệp | Dùng Gửi vào Moho (script) thay cho kéo thả. |
| "đang chạy bằng quyền Administrator" | Mở Moho và Manage Moho cùng quyền. |
| "Chưa thấy Moho đang chạy" | Từ khóa tên .exe chưa khớp: xem tên trong Task Manager rồi sửa ở Ứng dụng đích. |
| Animate không nhập | Animate chưa mở tài liệu, hoặc chưa chạy. Mở/tạo tài liệu rồi gửi lại. |
