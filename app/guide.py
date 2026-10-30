"""Nội dung Hướng dẫn sử dụng hiển thị trong phần mềm (Quản lý → Hướng dẫn, hoặc nút ? ở thanh trên)."""

GUIDE_MD = """# Hướng dẫn sử dụng

## 1. Thêm tài nguyên
- Bấm **Tải thư mục lên** (hoặc kéo thư mục từ máy vào cửa sổ) để chọn thư mục chứa ảnh, âm thanh, GIF, video, model 3D...
- Muốn thêm tệp lẻ: đổi chế độ ở hàng nút trên cùng sang **Tải tệp lên**.
- Thư mục nguồn nằm ở **Quản lý → Thư mục nguồn** (thêm, bớt, đọc lại).

## 2. Các mục và tìm tệp
- Hàng biểu tượng: Tất cả, Ảnh, Âm thanh, GIF, Video, Model 3D, Dự án, Vector, Tài liệu, Yêu thích.
- **Chuột phải một mục** để đổi tên/biểu tượng, đổi bộ lọc định dạng, dời trái phải hoặc xóa. Nút **+** thêm mục mới.
- Ô tìm kiếm lọc theo tên. Mỗi trang tối đa số mục bạn đặt ở Cài đặt; chuyển trang bằng thanh số dưới cùng.

## 3. Xem trước
- **Nhấp đúp** một tệp: bảng thông tin trượt lên. Ảnh phóng vừa khung, GIF/video chạy được, âm thanh nghe được.
- **Model 3D (.obj, .stl)**: kéo chuột trái để **xoay**, lăn chuột để **zoom**, kéo chuột phải để **dịch**, nhấp đúp để về góc mặc định. Định dạng khác (FBX, GLB, BLEND...) chưa xem được.
- Rê chuột vào thẻ âm thanh thì nghe thử; GIF/video chạy ngay trên thẻ (tắt được ở Cài đặt).

## 4. Đưa tệp vào Moho
**Cách chính: kéo thả.** Mở Moho và mở một dự án, rồi giữ chuột vào thẻ tệp, kéo sang **vùng làm việc của Moho** và thả. Tệp gốc không bị di chuyển hay xóa. Kiểu kéo mặc định đã chọn là kiểu Moho nhập được (B). Nếu một ngày Moho không nhận, thử đổi ở **Quản lý → Cài đặt → Kiểu kéo thả**.

Moho nhận khi: đã mở dự án · thả vào vùng làm việc (khung vẽ ở giữa) · loại tệp Moho hỗ trợ (ảnh, âm thanh, video, vector) · không có hộp thoại nào đang mở · Moho và Manage Moho cùng quyền (cùng bình thường hoặc cùng Administrator). Khi thả ảnh, Moho có thể hỏi cách dùng ảnh: chọn trong Moho.

**Cách dự phòng: chuột phải tệp → Gửi vào Moho.** Dùng khi kéo thả không được. Chọn nhiều tệp cũng gửi được.

## 5. Cắt âm thanh
Chuột phải một tệp âm thanh → **Cắt âm thanh...** → hình sóng hiện ra. Bôi đen đoạn cần lấy (kéo trên hình sóng), rồi **giữ chuột kéo thẳng vùng bôi đen** sang Moho. Phím tắt phát/dừng, phóng to/thu nhỏ bằng nút hoặc lăn chuột. Tệp gốc không bao giờ bị đổi.

**Về các tệp đã cắt:** Moho chỉ nhớ đường dẫn tệp âm thanh, không chép vào dự án nên tệp cắt phải còn trên máy. Để tiết kiệm dung lượng: tệp cắt xuất ra MP3 (nhỏ hơn WAV khoảng 10 lần, đổi được ở Cài đặt); cắt lại đúng đoạn cũ thì dùng lại tệp cũ, không tạo thêm; kéo hụt (Moho không nhận) thì tệp vừa tạo bị xóa ngay; chọn cả bài thì kéo luôn tệp gốc, không tạo tệp mới. Xóa tệp cắt thì lớp âm thanh trong Moho sẽ báo thiếu tệp. Ở **Quản lý → Cài đặt** có mục để xem dung lượng các tệp đã cắt, tự dọn tệp cũ, hoặc xóa hết. Muốn gọn nhất: đặt thư mục lưu tệp cắt ngay cạnh dự án Moho.

## 6. Kịch bản
Nút **Kịch bản** ở thanh dưới mở cửa sổ riêng gồm 3 vùng (kéo thanh chia để chỉnh): **Hỏi AI** ở trên-trái, danh sách kịch bản ở dưới-trái, trình soạn kịch bản ở bên phải.
- Soạn phân cảnh, lời thoại, hành động; đậm/nghiêng/gạch chân, màu chữ, căn dòng. Tự lưu và có lịch sử phiên bản.
- **Hỏi AI**: bấm đúp một AI trong danh sách (hoặc chọn rồi bấm **Mở**): khung chat AI hiện to ngay trong phần mềm và danh sách tài khoản ẩn đi. Bấm **‹ Chọn AI** để quay lại danh sách. Mỗi tài khoản có đăng nhập riêng, đăng nhập một lần là lần sau tự nhớ. Rời khung chat thì trình duyệt nhúng được đóng để trả lại RAM. Máy yếu có thể tắt khung nhúng ở **Quản lý → Cài đặt** (AI sẽ mở bằng cửa sổ Chrome/Edge riêng); bản cài \"Nhẹ\" vốn không kèm khung nhúng.
- Nếu một trang AI không cho đăng nhập trong khung, bấm **Cửa sổ riêng** để mở bằng Chrome/Edge.

## 7. Các nút trên cùng
**Luôn nổi** trên đầu · **Làm mờ** khi chuột rời (thanh trượt) · **Về Moho** (đưa Moho lên trước) · **Đọc lại** · **Thu gọn / mở rộng** · **?** mở hướng dẫn này.

## 8. Dùng cho phần mềm khác (Adobe Animate...)
**Quản lý → Ứng dụng đích**: chọn phần mềm bạn muốn đưa tệp vào. Kéo thả vẫn hoạt động như cũ; riêng Adobe Animate có thể dùng chuột phải tệp → **Gửi vào Adobe Animate** (Animate cần đang chạy và đã mở một tài liệu).

## 9. Sao lưu
**Quản lý → Sao lưu** lưu các mục, thư mục nguồn, tên hiển thị, yêu thích, ghim, cài đặt, kịch bản. Không lưu các tệp tài nguyên thật.

## 10. Gỡ cài đặt và dọn rác
- Phần mềm tự dọn rác của nó: tệp thử kéo, tệp tạm gửi sang Moho/Animate, bộ nhớ đệm trình duyệt AI, tệp âm thanh cắt cũ hơn 30 ngày (đổi được ở Cài đặt). **Quản lý → Cài đặt → Dọn rác ngay** để dọn tay.
- Khi gỡ cài đặt: rác luôn bị xóa; script đã cài vào Moho cũng được gỡ. Bộ gỡ hỏi bạn có muốn xóa luôn dữ liệu cá nhân (kịch bản, mục, cài đặt, đăng nhập AI, tệp âm thanh đã cắt) hay giữ lại. Chọn "Không" thì lần sau cài lại là dùng tiếp ngay.
- Muốn gỡ script khỏi Moho mà vẫn giữ phần mềm: **Quản lý → Ứng dụng đích → Gỡ script khỏi Moho**.

## 11. Gặp sự cố?
- Kéo thả vào Moho không hiện tệp: kiểm tra các điều kiện ở mục 4 (nhất là đã mở dự án, thả vào vùng làm việc, cùng quyền). Dùng **Gửi vào Moho** thay thế.
- Mọi lần kéo thả được ghi vào `keo.log` trong thư mục dữ liệu phần mềm (`%APPDATA%\\\\ManageMoho`); gửi tệp này khi cần hỗ trợ.
"""
