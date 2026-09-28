> LƯU TRỮ LỊCH SỬ v0.2. Phạm vi hiện tại xem README.md và V03_GUIDE.md.

# Một ngày làm nghề — web game v0.2.0

**Bản chơi local: bốn nghề, phong cách boba, nhân viên, sổ thu chi, mặt bằng, trộm và công an NPC. Mã nguồn đầy đủ, không cần API key hoặc npm install.**

Mở cảnh tiệm nhỏ, đi tới đồ vật để tương tác, tự tay làm công việc, nói chuyện với NPC và đọc những phản hồi của họ. Tiến trình được lưu bằng SQLite trên máy chạy server. Đồ họa vector mặt tiền tiệm phong cách boba/pastel, bố cục riêng cho màn hình dọc và âm thanh nhẹ được dựng trực tiếp bằng mã nguồn; không tải asset hay font bên ngoài.

> Đây là **bản playable prototype**, không phải bản phát hành thương mại đã hoàn thành toàn bộ tài liệu 48 trang. Bốn nghề có vòng chơi riêng đã chạy được. Sự kiện dùng một bộ máy kể chuyện tương tác chung; chat mặc định là kịch bản theo ngữ cảnh. Các giới hạn được liệt kê rõ trong `docs/IMPLEMENTED_VS_DESIGN.md`.

## Mới trong v0.2

Đây là bản sửa từ v0.1, không phải dự án giao diện rời: giữ bốn vòng nghề, 24 NPC, 96 vignette, review/bình luận, trang trí và dữ liệu nền. Các hệ thống mới tác động vào cùng ví, kho, ca làm và bản lưu.

- **Nhân viên:** 16 ứng viên (4/nghề); tuyển, phân công, lịch ca, nghỉ, hướng dẫn, thưởng, nhắc nhở, kết thúc hợp tác. Có nhân vật trong cảnh và hỗ trợ đúng nghề; không tự duyệt bước cuối.
- **Sự cố:** làm rơi đồ, kẹt thiết bị, nhầm khay; có tình huống làm hỏng đồ khi bực. Kiểm nguồn và nghe người liên quan → chọn khắc phục → chờ nhịp làm việc → kiểm kết quả. Sự cố thật tạo hóa đơn sửa, không tự khấu trừ lương.
- **Sổ thu chi:** lương ca đã làm, điện nước, phí bảo vệ, sửa chữa; tiền thuê và thuế game kết mỗi 7 ca. Trả từng phong bì, gia hạn một lần, xem biên nhận và dòng tiền.
- **Mặt bằng:** góc nhỏ / cửa sổ nắng / sân vườn, đổi phí thuê, số nhân viên, sức chứa kho và vật thể trong cảnh.
- **An ninh:** kiểm hàng để nhầm / quên thanh toán / trộm / giật túi NPC. Có camera, chuông, khóa, đèn; báo NPC công an, kết quả sau nhịp game, nhận tài sản và tiền thưởng ở hai bước riêng. Có hỗ trợ khi đã bật gói bảo vệ trước sự việc.
- **Diễn tập:** mở ngay 8 tình huống mới để học luồng. Không trừ tài sản, không cộng thưởng hoặc kỹ năng. Ca thật vẫn có chi phí khi khép.
- **Tương thích:** tự nâng save schema 1 lên 2, không thu lương/thuế/tiền thuê hồi tố. Giữ nâng cấp phụ việc cũ riêng biệt với người tuyển mới.

Mọi tỷ lệ thuế, giá thuê, bảo hiểm, công an và thưởng đều là **quy tắc hư cấu**. Không dùng các con số này để làm việc ngoài đời. Xem [hướng dẫn phần mới](docs/V02_GUIDE.md) và [phạm vi thực tế](docs/IMPLEMENTED_VS_DESIGN.md).

## 1. Mở game

Cần **Python 3.11 trở lên**. Bản đóng gói được kiểm thử bằng Python 3.13; không cần cài thư viện Python để chơi.

**Windows:** giải nén vào một thư mục bình thường, mở `start.bat`.

**macOS / Linux:** mở Terminal trong thư mục, chạy:

```sh
python3 server.py --open
```

Hoặc `./start.sh`; nếu file chưa có quyền chạy, dùng `sh start.sh`. macOS có thêm `start.command`. Đường dẫn lưu dựa vào vị trí mã nguồn, không phụ thuộc thư mục Terminal hiện tại.

**Lệnh tương đương trên Windows:**

```powershell
py -3 server.py --open
```

Trình duyệt mở tại:

```text
http://127.0.0.1:8765
```

Giữ cửa sổ Terminal đang chạy trong lúc chơi. Nhấn `Ctrl+C` để dừng; các thao tác đã xác nhận vẫn được lưu. Không mở trực tiếp `public/index.html` bằng `file://`, vì game cần API và SQLite.

Cổng bị chiếm:

```sh
python3 server.py --port 8766 --open
```

## 2. Bốn nghề đã chơi được

| Nghề | Vòng chơi có trong mã nguồn |
|---|---|
| Tiệm mẹ & bé | Hỏi nhu cầu → lấy đúng hàng → phối giấy, nơ và thiệp → kiểm giỏ → thanh toán, giao → review. Có giữ tồn, nhập hàng và kiểm nhận kiện. |
| Nhà thuốc nhỏ | Đọc phiếu hư cấu → kiểm mã và lô → lấy đúng lượng → kiểm ba điều kiện → bàn giao; chuyển người phụ trách khi ngoài phạm vi. |
| Một ngày làm kế toán | Mở nguồn → sửa sai theo gốc / loại trùng có căn cứ → nối chứng từ và giao dịch theo nhóm → kiểm và bàn giao. Có trường hợp thiếu nguồn, nhiều-một, một-nhiều và khoản hoàn. |
| Chăm sóc khách hàng | Xác minh → đọc chứng cứ → đề xuất → gửi việc phối hợp → đợi theo nhịp game → kiểm kết quả → đóng vụ. Có bàn giao và các phương án gửi bù, đổi, đối soát, hoàn, hướng dẫn giả lập. |

Nhà thuốc và kế toán chỉ dùng dữ liệu mô phỏng. Không có tên/liều thuốc thật hoặc chỉ dẫn kê khai thuế. Tiền trong chứng từ và tiền hoàn của công ty không cộng/trừ trực tiếp vào ví cá nhân.

## 3. Cách tương tác

Chạm/click sàn để nhân vật đi. Chạm nhân vật để nói chuyện; chạm kệ, bàn, bảng tin, kho hoặc cửa để thao tác. Khi canvas có focus, dùng WASD/mũi tên để di chuyển, `E` để dùng điểm tương tác gần nhất. Các nút dưới cảnh là đường vào tương đương, đặc biệt hữu ích trên điện thoại.

Mỗi nghề có tiến trình, ví, kho, công việc, quan hệ và album riêng. Logo phía trên hoặc mục **Nghề** mở màn chuyển nghề. Mở ngày tạo 2/3/4 việc theo chế độ Thư giãn/Đời thường/Thử thách; **không có đồng hồ đếm ngược bắt đọc nhanh**. Khép ca giữ các việc còn dang dở. Ngày mới tiếp tục theo lựa chọn của người chơi, không chạy theo ngày ngoài đời.

**Chuyện phố:** xem review NPC, trả lời, đăng lời nhắn. NPC phản hồi sau một vài nhịp hành động; có nút xem tin mới để tiến nhịp. Bình luận không tự hoàn thành đơn hay thay đổi sao đánh giá.

**Bạn quen:** 24 hồ sơ NPC. Chat bằng nút gợi ý hoặc tự gõ. Lời thoại mặc định nhận diện một số ý định theo ngữ cảnh; không giả là một mô hình AI tự do. Những việc đã làm được lưu thành ký ức tham chiếu sự kiện gốc.

**Sổ tay:** ba tuyến mục tiêu/milestone cho mỗi nghề, ký ức, nhật ký và 24 tình huống của nghề. Tổng cộng 96 tình huống thực thi qua cùng cấu trúc: mở chứng cứ → chọn phương án → xác nhận → làm hai bước → nhận kết quả. Các chủ đề gồm review, clip xin quà, dùng thử nhiều lần, quên ví, nghi mất hàng, thất lạc đồ, áp lực xử lý và tình huống nghề.

Sự kiện tự xuất hiện sau công việc đầu tiên trong ca theo điều kiện. **Diễn tập** từ Sổ tay không tốn xu, không tăng XP/quan hệ và không thể dùng để cày thưởng. Đang có sự kiện thật chưa xong thì hoàn thành trước khi mở diễn tập khác. Sự kiện căng được lọc trong chế độ Thư giãn.

**Trang trí:** mua đồ bằng xu, đổi một trong các vị trí hỗ trợ, thay tông phòng. Kệ mở rộng tăng sức chứa thật; một số công cụ cho gợi ý. Nâng cấp phụ việc cũ vẫn hỗ trợ một lần/ngày. Nhân viên tuyển trong **Sổ tiệm** là cơ chế mới có ca, lương, hỗ trợ theo lượt và sai sót; hai hệ không bị trộn khi nâng bản lưu.

**Kỷ niệm:** chụp ảnh thật từ canvas đã trang trí, lưu tối đa 6 ảnh/nghề và tải ảnh. Không dùng ảnh dựng giả để thay ảnh game.

Trên màn nhỏ, thanh hành động có thể cuộn ngang. Nút **Thêm** mở Cách chơi, Sổ tay, Bạn quen, Kỷ niệm và đổi nghề. Cài đặt có giảm chuyển động, chữ lớn, âm thao tác, nhạc tổng hợp và nhịp ngày.

## 4. Lưu và chuyển tiến trình

Mặc định dữ liệu nằm ở `storage/game.sqlite3`. Cookie `mnl_session` xác định phiên; nhiều trình duyệt tạo nhiều phiên **chơi đơn riêng**, không phải multiplayer.

Trong **Cài đặt → Bản lưu**, chọn **Xuất bản lưu** để nhận JSON. Trình duyệt/máy khác có thể **Nhập bản lưu**; thao tác này thay cả bốn nghề của phiên đang mở sau xác nhận. Xóa cookie hoặc dùng cửa sổ riêng tư sẽ tạo phiên mới, không tự tìm lại người chơi trước đó. Không có tài khoản/email/đăng nhập trong prototype.

Để sao lưu toàn bộ máy chủ, dừng server trước rồi sao chép thư mục `storage/`. Khi SQLite đang chạy có thể có thêm file WAL/SHM; không tự copy riêng một file DB đang ghi và coi đó là bản sao nhất quán.

Có thể đổi vị trí DB:

```sh
python3 server.py --db /duong/dan/game.sqlite3
```

Thao tác thay đổi state được lưu trong giao dịch; cùng mã request gửi lại không cộng tiền hai lần. Hai tab cũ cùng sửa sẽ được phát hiện bằng revision và yêu cầu làm mới, không âm thầm ghi đè tiến trình.

### Nâng từ v0.1

Cách an toàn: chạy bản cũ, **Xuất bản lưu JSON**; dừng bản cũ; chạy bản mới; nhập JSON trong Cài đặt. Bản mới nhận cả `save-v1` và `save-v2`, xuất `save-v2`. Hoặc dừng server rồi sao lưu/chuyển thư mục `storage/` sang mã mới; giữ hostname/cổng và cookie cũ để tiếp tục cùng phiên. Không chạy hai phiên bản đồng thời trên cùng file DB.

Sau chuyển đổi, tiền, nghề, việc đang làm, kho, hội thoại, album và trang trí cũ được giữ. Sổ thu chi bắt đầu với số dư tại thời điểm nâng cấp; không tạo nợ cho những ngày đã chơi trong v0.1. **Bản lưu v0.2 không dùng ngược với v0.1**; giữ một bản sao JSON/DB cũ trước khi nâng.

## 5. AI tùy chọn, mặc định không gọi Internet

Sao chép `.env.example` thành `.env`. Cấu hình một server hỗ trợ đường dẫn chat-completions:

```dotenv
LLM_BASE_URL=http://127.0.0.1:8000/v1
LLM_MODEL=ten-model-dang-serve
LLM_API_KEY=
```

Khởi động lại server, vào **Cài đặt → Hội thoại → cho phép gửi lời chat**, rồi lưu quyền AI. Không nhập API key trong trình duyệt hoặc commit `.env`.

Adapter hiện tại **chỉ diễn đạt lại câu chuẩn của NPC**, nhận câu người chơi gần nhất và câu chuẩn; không đọc toàn bộ kho/tiền, không có tool sửa state. Có timeout, giới hạn lượt, kiểm số mới xuất hiện và fallback. Bộ lọc này không bảo đảm mọi lời diễn đạt đều đúng ngữ nghĩa; UI cho xem câu chuẩn làm nguồn sự thật. Không cấu hình hoặc không đồng ý thì không gọi endpoint. Mất endpoint vẫn chơi bằng kịch bản được.

**Chưa kiểm thử với API/model thật.** Test adapter hiện dùng phản hồi giả lập để kiểm tra fallback, lỗi, nội dung bất hợp lệ và quyền đồng ý. Chi phí/quyền riêng tư của endpoint do chủ server lựa chọn quản lý.

## 6. Chơi thử từ điện thoại trong cùng LAN

Tạo `.env` với IP thật của máy chủ, ví dụ:

```dotenv
HOST=0.0.0.0
ALLOWED_HOSTS=192.168.1.10
```

Chạy `python3 server.py`, cho phép cổng 8765 trên **mạng riêng đáng tin**, mở từ điện thoại cùng Wi-Fi:

```text
http://192.168.1.10:8765
```

Đổi IP ví dụ thành IP máy bạn. Điện thoại tạo phiên riêng; xuất/nhập JSON để chuyển tiến trình. Không port-forward, public tunnel hoặc công khai server này. Đây là máy chủ thử local/LAN, chưa có xác thực tài khoản, HTTPS gateway, kiểm duyệt người dùng thật hay quản trị production. Không đặt `ALLOWED_HOSTS=*` để “sửa nhanh”.

## 7. Kiểm thử

Kiểm thử luật game, dữ liệu, SQLite và HTTP bằng thư viện chuẩn:

```sh
python3 scripts/run_checks.py
```

Bộ hiện tại có **347 ca tự động**; kết quả thực tế của lần chạy đóng gói nằm trong `artifacts/python-test-report.json` và `artifacts/python-tests.log`. Nhiều ca là tham số hóa 96 tình huống × 2 phương án; đây không phải 347 luồng chơi thủ công khác nhau.

Kiểm cú pháp frontend bằng Node, chỉ dùng khi phát triển:

```sh
npm run check
```

Kiểm UI optional (không cần để chơi):

```sh
python3 -m pip install playwright httpx
python3 -m playwright install chromium
# Bật game server ở Terminal khác, rồi:
python3 scripts/browser_smoke.py --base http://127.0.0.1:8765
python3 scripts/browser_operations.py --base http://127.0.0.1:8765
```

Môi trường tạo gói chặn browser navigation tới localhost. Kiểm thử UI tại đây dùng `--bridge` để nạp chính module và CSS vào trang trắng, nối fetch qua local HTTP adapter; **không thay đổi chính sách bảo mật trình duyệt**. Kết quả này kiểm thao tác UI + backend thật, nhưng không thay thế kiểm CSP/network của browser thật hay Safari trên iPhone. Xem `artifacts/browser-test-report.json`, `artifacts/browser-operations-report.json` và `docs/TESTING.md`.

## 8. Mã nguồn ở đâu?

```text
server.py                 HTTP + cookie phiên + CSRF + static files
 game/content.py          Vật phẩm, nghề, nhiệm vụ và cân bằng
 game/engine.py           Luật hành động, state, tiền, tồn, nhiệm vụ, lưu/khôi phục
 game/events.py           96 vignette có chứng cứ, phương án và bước thực hiện
 game/storage.py          SQLite, transaction, revision, idempotency
 game/dialogue.py         Adapter AI diễn đạt lời thoại, tùy chọn
 game/operations.py       Nhân viên, sổ chi phí, mặt bằng, sự cố, an ninh
 public/js/world.js       Lõi canvas, hit-test, đường đi và chụp ảnh
 public/js/boba-world.js  Cảnh boba chính diện; bố cục portrait riêng
 public/js/operations-ui.js  Sổ tiệm: nhân viên, thu chi, mặt bằng, an ninh
 public/css/boba.css      Chủ đề pastel, thẻ nhân viên và sổ vận hành
 public/js/app.js         UI, bốn bàn nghề, hội thoại, review, trang trí
 public/js/api.js          Gọi API theo thứ tự, retry có cùng request ID
 public/js/icons.js       Hình vector/nhân vật/vật phẩm bằng mã
 public/js/audio.js       Âm thanh Web Audio, không asset âm nhạc bên ngoài
 public/css/game.css      Giao diện desktop và portrait mobile
 reference/               Bản thiết kế gốc và dữ liệu nội dung nền
 tests/                   Kiểm thử tự động
 scripts/                 Trình chạy test và browser harness
 artifacts/               Báo cáo thật và ảnh chụp gameplay
 docs/                    Kiến trúc, API, phạm vi, kiểm thử, bảo mật
 storage/                 DB sinh ra khi chạy; ZIP không chứa phiên người chơi
```

`reference/` là baseline đầy đủ để phát triển tiếp; **không dùng nó như danh sách tất cả tính năng đã hoàn thành**. Xem phạm vi được hiện thực hóa trong `docs/IMPLEMENTED_VS_DESIGN.md`.

## 9. Những gì chưa có

Chưa có multiplayer, review từ người thật, đăng nhập tài khoản, giao dịch tiền thật, mobile native, livestream/TikTok/Zalo thật, PvP hoặc 12 nghề mở rộng. Hội thoại mở hoàn toàn, các hoạt cảnh truyện nhiều nhánh và mô phỏng NPC tự vận hành dài hạn chưa nằm trong bản này. Đồ họa hiện là vector 2D chính diện phong cách tiệm trà sữa, có bố cục portrait riêng, không sao chép tranh minh họa hoặc nhãn hàng trong ảnh tham khảo.

Không có bản cài Windows/macOS đi kèm Python; người chạy cần cài Python. Dockerfile là phương án đóng gói bổ sung, chưa được build/chạy trong môi trường tạo gói.
