# Phát hành Manage Moho không còn màn hình xanh (Microsoft Store)

## Vì sao có màn hình xanh?
Windows SmartScreen cảnh báo mọi tệp `.exe` **chưa được ký** bởi một nhà phát hành mà Microsoft tin cậy. Phần mềm của bạn không có gì xấu, chỉ là chưa có chữ ký. Muốn hết cảnh báo thì phải qua một trong các đường sau (thông tin theo trang Microsoft và các nguồn kiểm tra tháng 10/2026, giá có thể đổi):

| Cách | Chi phí | Điều kiện | Kết quả |
|---|---|---|---|
| **Microsoft Store (khuyên dùng)** | Miễn phí đăng ký cá nhân (từ 9/2025) | Tài khoản Microsoft, xác minh danh tính nhẹ | Microsoft tự ký gói MSIX, người dùng cài từ Store, **không có màn hình xanh** |
| Azure Artifact Signing | khoảng 9,99 USD/tháng | Cá nhân chỉ ở **Mỹ và Canada** | Có chữ ký, SmartScreen vẫn có thể cảnh báo lúc đầu |
| Chứng chỉ OV mua của CA (DigiCert, Sectigo...) | khoảng 150–300 USD/năm | Mọi nước | Có chữ ký, SmartScreen vẫn cảnh báo cho đến khi đủ lượt tải |
| SignPath Foundation | Miễn phí | Dự án **mã nguồn mở công khai** (giấy phép OSI), được họ duyệt | Có chữ ký, tên hiển thị là "SignPath Foundation" |
| Không ký (hiện tại) | 0 | | Màn hình xanh, phải bấm "Thông tin thêm → Vẫn chạy" |

Chứng chỉ EV trước đây tránh được SmartScreen ngay, nhưng Microsoft nói điều đó không còn đúng nữa nên không đáng tiền.

**Đường hợp lý nhất cho bạn là Microsoft Store**: miễn phí, hợp lệ, hết cảnh báo, và người dùng cài/gỡ như mọi ứng dụng khác.

## Các bước (làm một lần)
1. Vào https://storedeveloper.microsoft.com và đăng ký **tài khoản cá nhân** bằng tài khoản Microsoft. Nếu đăng ký không hỗ trợ nước bạn, báo lại để chọn cách khác (mình không kiểm chứng được danh sách nước).
2. Vào Partner Center → **Apps and games → New product → MSIX or PWA app** → đặt tên giữ chỗ (ví dụ "Manage Moho").
3. Trong sản phẩm vừa tạo vào **Product management → Product identity**, ghi lại 3 giá trị:
   - **Package/Identity/Name** (dạng `12345Ten.ManageMoho`)
   - **Package/Identity/Publisher** (dạng `CN=xxxxxxxx-xxxx-...`)
   - **Package/Properties/PublisherDisplayName** (tên hiển thị của bạn)
4. Trên GitHub: repo → **Settings → Secrets and variables → Actions → tab Variables → New repository variable**, tạo 3 biến đúng tên:
   `MSIX_IDENTITY_NAME`, `MSIX_PUBLISHER`, `MSIX_PUBLISHER_DISPLAY` và dán 3 giá trị ở trên (chép **đúng từng ký tự**).
5. Tab **Actions → "Build MSIX cho Microsoft Store" → Run workflow**. Xong tải artifact `ManageMoho-MSIX` (tệp `ManageMoho.msix`).
6. Trong Partner Center, tạo **Submission**, tải lên `ManageMoho.msix`, điền mô tả, ảnh chụp màn hình, xếp hạng độ tuổi. Phần "chính sách quyền riêng tư" dùng nội dung tệp `PRIVACY.md` (đăng lên một trang web công khai rồi dán đường dẫn, ví dụ GitHub Pages hoặc một trang Gist).
7. Gói dùng quyền **runFullTrust** (bắt buộc cho phần mềm máy tính để chạy tự do như kéo thả, gửi phím vào Moho). Partner Center sẽ hỏi lý do, ghi: "Ứng dụng máy tính quản lý tệp và đưa tệp vào Moho/Adobe Animate".
8. Gửi duyệt. Microsoft kiểm duyệt rồi tự ký, thường mất vài ngày.

## Cần biết
- Bản cài `.exe` qua GitHub (không phải Store) vẫn hiện màn hình xanh cho đến khi bạn làm một trong các cách ký ở bảng trên.
- Bản Store không có "cửa sổ AI nhúng" nặng: workflow này dựng **bản Nhẹ**. AI mở bằng cửa sổ Chrome/Edge riêng.
- Dữ liệu ứng dụng của bản Store nằm trong vùng riêng của gói và **được xóa sạch khi gỡ cài đặt** (cả dữ liệu cá nhân, khác với bản `.exe` có hỏi bạn). Các thư mục bạn tự chọn (thư mục lưu tệp cắt, thư mục Moho) không bị đụng tới.
- Mình chưa thử đóng gói này trên máy Windows thật. Nếu workflow báo lỗi, gửi mình dòng lỗi đỏ.
