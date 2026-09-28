# Phố Có Chuyện — v0.5 · Một ngày làm nghề

**Web game mô phỏng nghề nghiệp bằng tiếng Việt (có tiếng Anh).** Chọn một nghề, mở ca, làm đúng công việc thật của nghề đó, gặp các tình huống ngoài đời và nhìn chúng từ nhiều phía: khách, đồng nghiệp, chủ, phụ huynh. Chơi một mình hoặc ghé quán của người chơi khác ở **Phố nghề**.

Máy chủ chạy bằng Python thuần (thư viện chuẩn + SQLite), không cần `pip install` hay `npm install`. Chơi được trên điện thoại, máy tính bảng và máy tính, và cài được lên màn hình chính (PWA).

## Chạy trên máy

Cần Python 3.10 trở lên.

```bash
# Windows: mở start.bat, hoặc
python server.py --open
# macOS / Linux
python3 server.py --open
```

Mở `http://127.0.0.1:8765`. Nếu cổng bận, thêm `--port 8766`; `--db đường/dẫn.sqlite3` để chọn tệp dữ liệu khác; `--help` xem thêm tham số.

**Mở cho mọi người chơi qua Internet:** xem [`docs/DEPLOY.md`](docs/DEPLOY.md) (Docker + Caddy HTTPS tự động, hoặc systemd + Nginx).

## Các nghề

<!-- careers:start -->
**20 nghề chơi được:**

| Nghề | Việc thật trong game |
|---|---|
| Quán mì cay | Nấu nồi nước dùng theo mẻ, trụng và chắt mì, chọn topping, canh cấp độ cay, đổi món khi khách dị ứng, đóng hộp mang đi, vệ sinh bếp |
| Tiệm bánh & cà phê | Chiết espresso theo từng giây, đánh sữa, vẽ latte art; ủ và nướng bánh; viết chữ lên bánh kem; xử lý bánh qua đêm |
| Tiệm hoa | Cắt gốc, tuốt lá, ngâm mút, cắm theo dịp (sinh nhật, viếng, khai trương…); viết thiệp và băng rôn đúng phép |
| Tạp hóa đầu hẻm | Cân rau đúng mã, trừ bì, áp khuyến mãi, kiểm tuổi mua bia; thối tiền, soi tiền giả, kiểm chuyển khoản, ghi sổ nợ hàng xóm; xếp kệ theo hạn dùng |
| Tiệm sửa đồ | Nhận máy, ghi tình trạng, đo kiểm để khoanh lỗi, báo giá trước khi sửa, an toàn điện, bảo hành trung thực |
| Nông trại rau & gà | Gieo, tưới, làm cỏ, soi sâu, bón phân; thời gian cách ly thuốc; thu hoạch theo loại; cho gà ăn, nhặt trứng; đóng hàng và nhãn hữu cơ thật |
| Giao hàng | Lên lộ trình trên bản đồ, canh giờ món ăn, cân và đóng gói hàng, gọi khách, thu COD, nộp tiền, đổ xăng, ngày mưa |
| Homestay nhỏ | Lịch phòng, tiền cọc, check-in (không chụp giấy tờ), dọn phòng, bữa sáng, hóa đơn check-out từng khoản, gợi ý đi chơi |
| Chăm sóc thú cưng | Tắm đúng nhiệt độ, dầu gội đúng loại, cắt móng, giữ bé bớt sợ, báo cáo trung thực; nhận lưu trú (sổ tiêm), cho ăn theo khẩu phần |
| Salon tóc | Tư vấn, xem tóc, thử dị ứng, pha màu và canh giờ, cắt theo trình tự, không bán thêm dịch vụ khách không cần |
| Kế toán doanh nghiệp | Hóa đơn mua bán, định khoản Nợ/Có, đối chiếu ngân hàng, tuổi nợ, kiểm quỹ, kiểm kho, khấu hao, cân đối thử, khóa sổ (cần xin việc) |
| Thuế & tiền lương | Phiếu lương, bảo hiểm, thuế TNCN, tệp chuyển khoản lương, tờ khai VAT, lịch hạn nộp, quyết toán năm (cần xin việc) |
| Kế toán tập đoàn | Đối chiếu nội bộ, loại trừ giao dịch nội bộ, lãi chưa thực hiện, quy đổi ngoại tệ, lợi ích cổ đông thiểu số, bảng hợp nhất, làm việc với kiểm toán (cần xin việc) |
| Giáo viên | Tiết học nhiều môn, điểm danh, chấm bài, gặp phụ huynh, Trung thu, 20/11, sinh nhật lớp, Tết, dã ngoại theo lịch năm học (cần xin việc) |
| Tiệm trà sữa | Hỏi vị, pha từng lớp ly, lô nguyên liệu có hạn, giá chốt |
| Tiệm mẹ & bé | Hỏi nhu cầu, chọn đồ, gói quà, kiểm và giao |
| Nhà thuốc nhỏ | Đọc phiếu mô phỏng, kiểm mã/lô/số lượng, chuyển người phụ trách khi cần (không có thuốc hay liều thật) |
| Kế toán (góc sổ) | Đọc nguồn, loại trùng, ghép chứng từ, xử lý thiếu nguồn |
| Chăm sóc khách hàng | Xác minh, xem chứng cứ, đề xuất phương án, theo dõi tới khi xong |
| Hướng dẫn viên du lịch | Chọn tuyến, kiểm đoàn, kể chuyện điểm đến, chụp ảnh, gửi bưu thiếp |
<!-- careers:end -->

Mỗi nghề có:

- **Quầy làm việc riêng:** bàn chế biến, bàn lắp ráp, sổ sách, bảng thủ tục, bản đồ tuyến… tùy nghề.
- **Kho nguyên liệu:** lô, hạn dùng, nhập hàng, kiểm nhận, hao hụt; giá bán chỉnh được.
- **Tình huống ngoài đời:** mỗi tình huống có nhiều lựa chọn và phần tóm tắt "mỗi người nhìn thấy gì".
- **Phản hồi của khách:** chấm theo từng tiêu chí đúng những gì đã xảy ra, bằng giọng riêng của từng tính cách.
- **Vận hành chung:** nhân viên, lương, chi phí, mặt bằng, an ninh, mục tiêu, huy hiệu, trò nhỏ.
- **Xin việc:** một số nghề (giáo viên, kế toán…) phải nộp hồ sơ và phỏng vấn trước khi được nhận làm.

## Phản hồi và AI nhân vật

Sau mỗi đơn, khách có thể để lại review. Mỗi người mang một tính cách: 🍋 chanh chua, 🧐 bố đời, 🌻 ấm áp vui tính, kỹ tính, Gen Z, kiệm lời. Giáo viên thì nhận phản hồi từ phụ huynh. Bạn trả lời (có thể kèm bù đắp); khách tự quyết định sửa sao, giữ nguyên hay cãi lại.

AI là tùy chọn. Chủ server phải đặt `LLM_BASE_URL`, `LLM_MODEL` và `LLM_API_KEY` trong `.env` (xem `.env.example`), và người chơi phải bật "Cho phép AI" trong Cài đặt. Khi không có AI, game dùng kịch bản có sẵn. Dù có hay không có AI, số sao luôn nằm trong khoảng mà dữ kiện cho phép.

## Phố nghề

Tạo hồ sơ → ghé quán người khác → chấm sao và viết nhận xét → tặng sticker hoặc xu → mua bán nguyên liệu ở chợ → đăng mẹo nghề lên bảng tin → cùng cả phố hoàn thành mục tiêu tuần. Có chặn, báo cáo, lọc nội dung và giới hạn tần suất. Thông báo đẩy (web push) báo khi có người ghé, đánh giá hay tặng quà.

## Cài đặt trong game

Chơi · Giao diện (5 phong cách, bố cục điện thoại/máy tính bảng/máy tính) · Âm thanh (nhạc nền theo nghề, hiệu ứng) · Ngôn ngữ (Tiếng Việt/English) · Thông báo · Dữ liệu (xuất/nhập bản lưu, xóa dữ liệu).

## Bản lưu

Tiến trình được lưu trên máy chủ theo cookie phiên. Để mang sang trình duyệt khác: Cài đặt → Dữ liệu → Xuất, rồi Nhập ở trình duyệt mới. Bản lưu v1–v3 tự được nâng lên schema 4; nghề mới được thêm vào ở trạng thái ban đầu.

## Cấu trúc

```text
server.py                  HTTP (stdlib), cookie/CSRF/CSP, gzip, rate limit, API
game/engine.py             luật lõi, router action, migration, validate
game/careers/*.py          nghề dạng plugin (nội dung + luật + public view)
game/inventory.py          kho, lô, hạn dùng, nhập hàng
game/situations.py         tình huống ngoài đời, nhiều góc nhìn
game/feedback.py           review theo tiêu chí, tính cách, vòng phản hồi
game/procedures.py         thủ tục nhiều bước (kế toán, thuế, lớp học)
game/employment.py         tuyển dụng, phỏng vấn, thử việc
game/classroom.py          Kế hoạch lớp của giáo viên
game/social.py             Phố nghề (multiplayer)
game/push.py               web push (VAPID ES256, Python thuần)
game/ai.py                 AI nhân vật, có rào chắn
public/js/app.js           shell, router giao diện
public/js/v4/*.js          cài đặt, xã hội, push, nhạc, i18n, thủ tục, lớp học
public/js/careers/*.js     giao diện từng nghề
public/i18n/en.json        gói tiếng Anh (tạo bằng scripts/i18n_extract.py)
tests/                     test luật, HTTP, SQLite, xã hội, push
docs/                      API, triển khai, bảo mật, plugin nghề
```

Muốn thêm nghề: đọc [`docs/PLUGIN_CAREERS.md`](docs/PLUGIN_CAREERS.md).

## Kiểm thử

```bash
python scripts/run_checks.py          # toàn bộ test Python
python scripts/browser_v04.py         # kiểm trình duyệt (cần playwright)
python scripts/i18n_extract.py status # độ phủ bản dịch tiếng Anh
```

## Pháp lý và liên hệ

- [Chính sách quyền riêng tư](public/privacy.html) (`/privacy`) và [Điều khoản](public/terms.html) (`/terms`).
- Liên hệ: trachanhtv.works@gmail.com.
- Mọi nhân vật, doanh nghiệp, số liệu thuế, kế toán hay y tế trong game đều hư cấu và không phải lời khuyên chuyên môn. Xu trong game không có giá trị tiền thật.
- Mã nguồn: xem `LICENSE`. Font Be Vietnam Pro dùng giấy phép SIL OFL (`public/fonts/OFL.txt`).
