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

## 4. Đưa tệp vào Moho – có 3 cách

### Cách A. Kéo thả (nhanh nhất)
Giữ chuột vào thẻ tệp, kéo sang **vùng làm việc của Moho** rồi thả. Tệp gốc không bị di chuyển hay xóa.

Moho chỉ nhận khi đủ các điều kiện sau:

| Điều kiện | Cách kiểm tra |
|---|---|
| Moho **đã mở một dự án** (File → New / Open) | Không có dự án thì Moho không có chỗ để đặt tệp. |
| Thả vào **vùng làm việc** (khung vẽ ở giữa) | Thả vào thanh công cụ, Timeline, Library có thể bị bỏ qua. |
| Loại tệp Moho hỗ trợ | Ảnh (PNG, JPG, BMP, TGA, GIF), âm thanh (WAV, MP3, M4A, AIFF), video, .obj, PSD... `.blend`, `.fbx` thường không nhận. |
| Moho **không đang hiện hộp thoại** nào | Đóng hộp thoại đang mở rồi thả lại. |
| Moho và Manage Moho **cùng quyền** | Nếu Moho chạy "Run as administrator" mà Manage Moho thì không, Windows chặn kéo thả và phím gửi. Mở cả hai cùng quyền. |
| Khi thả ảnh, Moho có thể **hỏi cách dùng** (Tracing Image / New Image Layer) | Chọn trong Moho. |

### Cách B. Gửi vào Moho (không cần kéo thả) — dùng khi Cách A không hiện gì
1. **Chuột phải** vào tệp → **Gửi vào Moho (hộp thoại Nhập)**. Hoặc nhấp đúp tệp rồi bấm nút vàng **Gửi vào Moho** ở bảng thông tin.
2. Phần mềm tự đưa Moho lên trước, bấm phím Nhập của Moho (mặc định `Ctrl+Shift+Y`), điền đường dẫn tệp vào hộp thoại rồi bấm Mở.
3. **Đừng chạm chuột/bàn phím** trong 1–3 giây đó. Chọn nhiều tệp thì gửi lần lượt; nếu Moho hỏi cách dùng ảnh, trả lời xong rồi gửi tiếp các tệp còn lại.
4. Tệp `.moho` dùng phím Mở (`Ctrl+O`) thay vì Nhập.

Điều kiện: Moho đã mở dự án và không đang hiện hộp thoại khác.

### Cách C. Dán ảnh (chỉ ảnh)
Chuột phải một ảnh → **Dán ảnh vào Moho (Ctrl+V)**. Ảnh được đưa vào bộ nhớ tạm rồi tự bấm Ctrl+V trong Moho (Moho từ bản 12.3 tạo lớp ảnh mới từ ảnh dán). Ảnh dán không giữ liên kết tới tệp gốc.

> Mọi lần kéo thả được ghi vào tệp `keo.log` trong `%APPDATA%\ManageMoho`. Nếu có gì lạ, gửi tệp này cho người hỗ trợ.

## 5. Dùng cho phần mềm khác (không chỉ Moho)

Mở **Quản lý → tab Ứng dụng đích**:

1. Chọn phần mềm có sẵn (Moho, Premiere Pro, After Effects, Photoshop) hoặc bấm **Thêm ứng dụng** và gõ tên.
2. Điền:
   - **Từ khóa tên .exe**: một phần tên tệp chạy của phần mềm (xem trong Task Manager → Details). Ví dụ `krita`, `blender`, `clip studio`.
   - **Phím tắt Nhập**: phím mở hộp thoại nhập tệp của phần mềm đó, ví dụ `ctrl+i`, `ctrl+shift+y`, `ctrl+o`.
   - **Phím tắt Mở dự án** và **đuôi tệp dùng phím Mở** (nếu phần mềm có tệp dự án riêng).
   - **Cách gửi**: Hộp thoại Nhập (mặc định) hoặc Dán ảnh.
3. Bấm **Lưu**, sau đó bấm **Kiểm tra kết nối**: phần mềm sẽ mở phần mềm đích, bấm phím Nhập, và báo hộp thoại có hiện không rồi tự đóng lại.
4. Từ đó nút **Gửi vào …**, nút "Về …" (đưa phần mềm lên trước) và nút trong bảng thông tin dùng phần mềm bạn chọn.

Phím tắt của Premiere/After Effects/Photoshop trong bảng là giá trị gợi ý theo mặc định của chúng; nếu bạn đã đổi phím tắt trong phần mềm đó thì sửa lại cho khớp. Những phần mềm tự vẽ hộp thoại riêng (không dùng hộp thoại Mở của Windows) có thể không điền được: khi đó dùng Cách A hoặc Cách C.

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
| Kéo thả được nhưng Moho không hiện tệp | Kiểm tra bảng điều kiện ở Cách A (nhất là: đã mở dự án, thả vào vùng làm việc, cùng quyền). Vẫn không được thì dùng **Gửi vào Moho** (Cách B). |
| "Không thấy hộp thoại Nhập" | Moho chưa mở dự án, đang có hộp thoại khác, hoặc phím tắt Nhập khác `Ctrl+Shift+Y`. Trong Moho vào menu File → Import xem phím tắt ghi bên cạnh, rồi sửa ở Quản lý → Ứng dụng đích. |
| "đang chạy bằng quyền Administrator" | Mở Moho và Manage Moho cùng quyền. |
| "Chưa thấy Moho đang chạy" | Từ khóa tên .exe chưa khớp: xem tên trong Task Manager rồi sửa ở Ứng dụng đích. |
| Ảnh bị Moho hỏi "Tracing Image / New Image Layer" | Bình thường; chọn trong Moho. |
