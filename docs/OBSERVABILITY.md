# Thống kê và log Phố Có Chuyện

Ngày thiết lập: **02/10/2026**. Firebase riêng được tạo trực tiếp trên tài khoản Google đang đăng nhập.

## Tài nguyên đã tạo

| Tài nguyên | Thông tin |
|---|---|
| Firebase | `pho-co-chuyen`, số dự án `948402225430`, gói Spark miễn phí |
| Web app | Phố Có Chuyện Web — `1:948402225430:web:e91da51c891c97de8d5037` |
| GA4 property | **Phố Có Chuyện**, ID `557111946` |
| GA4 web stream | ID `15939995458`, measurement ID `G-VQ41KGJ2GW` |
| Stream URL | `https://phocochuyen.io.vn`; đã lưu và xác nhận trong UI |
| Custom dimensions | Event scope: Nghề chơi (`career`), Phiên bản game (`game_version`), Loại lỗi client (`error_kind`); đã lưu cả 3 |
| Enhanced measurement | Tắt, đã xác nhận trong UI |
| Giờ báo cáo | Việt Nam, GMT+07:00 |
| Báo cáo mặc định | Truy cập web/app và engagement/retention; lĩnh vực Games |
| Search Console | Đã thêm URL `https://phocochuyen.io.vn/`; **chưa xác minh** |

[Firebase Console](https://console.firebase.google.com/project/pho-co-chuyen/overview) · [Google Analytics](https://analytics.google.com/analytics/web/#/p557111946/reports/dashboard?r=firebase-overview) · [Search Console](https://search.google.com/search-console?resource_id=https%3A%2F%2Fphocochuyen.io.vn%2F) · [Admin game](https://phocochuyen.io.vn/admin).

**Hiện trạng production lúc kiểm tra:** phiên bản 1.3.4; `/robots.txt` và `/sitemap.xml` còn 404, trang chủ chưa có Firebase config hoặc meta xác minh. GA4 chưa nhận dữ liệu. Các thay đổi 1.3.5 và cấu hình mới đã chuẩn bị tại máy phát triển, chưa được triển khai vì máy này chưa có quyền SSH vào `103.195.238.178`. Không lấy số 0 trên property vừa tạo làm số lượng người chơi thật.

Gói `mnl-1.3.5-analytics.zip` được tạo riêng từ nền production `d7e55a6` (1.3.4), cộng các thay đổi thống kê. Trong lúc thực hiện, nhánh làm việc có thêm cập nhật bày trí phòng 1.4.0 từ công việc khác; gói thống kê không chứa cập nhật đó. Trước khi deploy phải kiểm tra phiên bản live để tránh ghi đè một release mới hơn. Nếu live đã lên 1.4.0, tích hợp các file thống kê từ mã nguồn hiện tại và đóng gói theo phiên bản mới.

## Chỉ số xem ở đâu

| Nhu cầu | Báo cáo |
|---|---|
| Người đang truy cập, sự kiện gần đây | GA4 Reports → Realtime |
| Người mới, quay lại, lượt ghé | GA4 Reports → Understand web/app traffic |
| Nguồn Google, mạng xã hội, trực tiếp | GA4 Acquisition (referrer đã loại query/hash) |
| Giữ chân, thời gian tương tác, thiết bị | GA4 Engagement/Retention và Tech |
| Lượt chọn nghề/mở ca/kết thúc ca | GA4 Events với `career_start`, `shift_complete`, dimension `career` |
| Màn hình đang dùng | `screen_view`, `screen_name` |
| Lỗi client theo loại | `client_error`, `error_kind`; stack chi tiết ở admin Giữ chân |
| Tốc độ tải trang/kết nối | Firebase Performance, sau khi SDK nhận dữ liệu |
| Từ khóa, impression, click từ Google | Search Console Performance, sau khi xác minh và Google xử lý |
| Phễu ngày đầu và thống kê game đầy đủ | Admin game → Giữ chân/Thời gian chơi; không phụ thuộc Google hoặc consent |

GA4 chỉ tính các trình duyệt cho phép thống kê; không bằng số tài khoản hay bản lưu. GA4/Firebase không hồi phục số liệu trước lúc cài đặt. Giữ các báo cáo admin làm nguồn cho lịch sử.

## Dữ liệu được gửi

`page_view`, `game_ready`, `career_start`, `shift_complete`, `screen_view`, `client_error`. Chỉ thêm mã nghề, màn hình, loại lỗi và phiên bản game. Không gửi tên tài khoản, cookie game, ID bản lưu, nội dung chat/góp ý, message/stack lỗi chi tiết, payload của command, số xu hay dữ liệu bản lưu. Google SDK tự đo thiết bị, phiên truy cập, thời gian tương tác và hiệu năng. Advertising consent bị từ chối và Google Signals/personalization bị tắt trong config.

Game hỏi bằng một lựa chọn nhỏ sau màn hình đầu tiên. Chưa chọn hoặc từ chối thì không tải Google SDK. DNT/GPC cũng tắt Google. Người chơi đổi lựa chọn tại `/privacy`; những tab game đang mở nhận thay đổi ngay qua storage event. Chạy ở localhost không gửi số liệu vào property production.

## Cấu hình máy chủ

Các giá trị thật đã lưu vào `.env` bị git bỏ qua trên máy phát triển. Trên production, thêm các trường công khai tương ứng vào `/etc/mot-ngay-lam-nghe/game.env` (không ghi đè các dòng PostgreSQL/AI/admin hiện có):

```dotenv
SITE_URL=https://phocochuyen.io.vn
FIREBASE_PROJECT_ID=pho-co-chuyen
FIREBASE_APP_ID=1:948402225430:web:e91da51c891c97de8d5037
FIREBASE_MESSAGING_SENDER_ID=948402225430
FIREBASE_MEASUREMENT_ID=G-VQ41KGJ2GW
FIREBASE_PERFORMANCE=1
GOOGLE_SITE_VERIFICATION=pLTiDMtyJagFfIqyAPzwijUCMASqFzOfqdRY3oiIXSs
```

`FIREBASE_API_KEY` lấy từ `.env` local hoặc Firebase → Project settings → web app → SDK setup. Đây là khóa cấu hình SDK web công khai, không phải khóa service account. Không copy toàn bộ `.env` local lên server. Không cần Firebase Admin SDK hay khóa riêng; PostgreSQL vẫn giữ bản lưu.

## Kích hoạt và kiểm tra

1. **Đã hoàn thành:** GA4 Admin → Data streams → Phố Có Chuyện Web: Stream URL đúng tên miền; Enhanced measurement tắt để tránh tự theo dõi link/file/form ngoài event whitelist. Đã xác nhận qua UI.
2. **Đã hoàn thành:** GA4 Admin → Custom definitions: 3 event-scoped dimensions `career`, `game_version`, `error_kind`. `screen_name` dùng dimension màn hình có sẵn. Cấu hình dimension không thay thế việc cài SDK.
3. Triển khai release 1.3.5 bằng quy trình rolling hiện có tại `docs/DEPLOY_ROLLING.md`, giữ các env và shared storage hiện có. Đây là bản cập nhật kỹ thuật yên lặng, không tạo popup “Có gì mới”.
4. Xác nhận `/api/health`, `/robots.txt`, `/sitemap.xml` đều 200. View-source trang chủ phải có meta `mnl-observability`, `google-site-verification` và canonical đúng tên miền. CSP chỉ cho đúng host Google, vẫn giữ hash inline và không mở unsafe-inline/eval.
5. Mở game trên tên miền thật, chọn Cho phép; GA4 Realtime phải thấy page_view/game_ready và sự kiện sau khi mở/kết thúc ca. Nếu không có dữ liệu, kiểm tra blocker, console, CSP và cấu hình stream trước khi kết luận số người chơi bằng 0.
6. Trong Search Console, chọn HTML tag → Xác minh. Chỉ khi Google báo thành công mới submit `sitemap.xml` và liên kết Search Console với GA4. Mã xác minh phải luôn còn trên trang.
7. Kiểm tra Firebase Performance sau khi SDK gửi dữ liệu; không coi việc import SDK là đã có báo cáo.

## Log hiện có

- Lỗi JS, promise, asset, API, toast và stack: `public/js/telemetry.js` → `/api/beacon` → bảng thống kê riêng trong PostgreSQL → Admin Giữ chân. Lỗi extension/in-app browser được lọc, có giới hạn/batch, không đọc bản lưu để ghi log.
- Lỗi Python/API và slow command: journal của service game. Sau khi SSH vào đúng server:

```sh
journalctl -u mot-ngay-lam-nghe --since '1 hour ago' --no-pager
journalctl -u mnl-live --since '1 hour ago' --no-pager
tail -n 100 /var/log/mnl-rolling-release.log
```

- Nginx access/error logs: dùng đường dẫn đang cấu hình trong site Phố Có Chuyện trên server. Không thay cấu hình các website/service khác.
- Không bật Cloud Logging trả phí, không xuất log chứa dữ liệu người chơi sang Google, không tạo Firestore/Auth/Storage không liên quan. Stack chi tiết của web game tiếp tục ở bộ log hiện có.

## Kiểm thử

Đã chạy thành công 39 Python tests, 7 Node tests và kiểm tra cú pháp JS toàn bộ thư mục public. Bản zip được kiểm tra hash, khởi động server từ thư mục giải nén và chơi ngày đầu qua HTTP; request trùng không được áp dụng hai lần. CSP cho phép endpoint `firebase.googleapis.com` để SDK Analytics lấy cấu hình web, ngoài các endpoint Analytics/Performance.

```sh
python -m unittest tests.test_observability tests.test_telemetry_js tests.test_http tests.test_webassets -v
node --test tests/observability.mjs
node scripts/check_js.mjs
```

Tài liệu SDK: [Firebase Web](https://firebase.google.com/docs/web/setup), [Analytics](https://firebase.google.com/docs/analytics/get-started?platform=web), [Performance](https://firebase.google.com/docs/perf-mon/get-started-web), [Search Console verification](https://support.google.com/webmasters/answer/9008080?hl=en).
