# Kiểm thử v0.5

Từ v0.5 máy chủ thật chạy **hành trình**: một nhân vật, nghề mở dần theo chương, ví riêng có tiền sinh hoạt, nghề văn phòng phải phỏng vấn xong mới được làm. Để kiểm được mọi nghề trong trình duyệt, chạy server với `MNL_DEV=1`: hành trình tắt, mọi nghề mở và có lệnh `job_quick` (nhận việc nhanh). `browser_v04.py` tự đặt biến này cho server tạm của nó. Các script cũ (`browser_smoke.py`, `browser_operations.py`, `browser_v03.py`) nhận `--base`, nên cần tự chạy `MNL_DEV=1 python server.py` trước. Máy chủ thật không được đặt `MNL_DEV`.

| Lệnh | Kiểm gì |
|---|---|
| `node scripts/check_js.mjs` | Cú pháp và import của mọi module JS. |
| `node scripts/check_nav.mjs` | Bản đồ va chạm của các cảnh: nhân vật không đi xuyên quầy, kệ hay tường, và mọi điểm tương tác đều tới được. |
| `python scripts/verify_package.py <zip>` | Giải nén gói, chạy test trong gói, bật server với hành trình: chưa chọn giới tính thì chưa vào nghề, nghề khóa bị từ chối, chọn giới tính rồi mở quán trà sữa, chống gửi lặp, xuất bản lưu. |


| Lệnh | Kiểm gì |
|---|---|
| `python scripts/run_checks.py` | Toàn bộ test Python (luật lõi, 20 nghề, Kế hoạch lớp, phản hồi/AI, Phố nghề, web push, HTTP, SQLite, migration). Báo cáo ở `artifacts/python-test-report.json`. |
| `MNL_CAREERS=restaurant python -m unittest discover -s tests -t .` | Chạy nhanh khi chỉ sửa một nghề. Test của các nghề bị lọc sẽ tự bỏ qua. |
| `python scripts/browser_v04.py [--shots DIR] [--lang en]` | Trình duyệt thật (Playwright + Chromium) trên điện thoại 390×844, máy tính bảng 820×1180 và máy tính 1440×900: màn chọn nghề, mọi thẻ công việc của 20 nghề, các thẻ Cài đặt, 5 phong cách, Phố nghề và tiếng Anh. Báo lỗi console, lỗi 5xx và tràn ngang. `--lang en` chạy cả vòng bằng tiếng Anh; số chuỗi chưa dịch nằm ở `i18n_misses`/`sample_misses`. Báo cáo ở `artifacts/browser-v04-report.json`. |
| `python scripts/i18n_extract.py extract` rồi `status` | Tìm chuỗi tiếng Việt mới chưa có bản dịch tiếng Anh. Dịch phần thiếu trong `i18n/todo/`, rồi chạy `merge` và `build`. Chuỗi ghép theo ngữ cảnh (ví dụ "lượt $1" → "turn $1") thêm vào `i18n/overrides.json`. |
| `node --check public/js/**/*.js` | Kiểm cú pháp JS (cần Node). |

Chưa kiểm được và cần người thật làm trước khi mở rộng:
- iPhone/Safari vật lý (thông báo chỉ chạy sau khi đã "Thêm vào MH chính").
- AI với khóa và model thật trên máy chủ công khai.
- Tải lớn và nhiều người chơi cùng lúc.

---

> Tài liệu nền v0.2 được giữ để tra cứu. Phần bổ sung hiện hành ở V03_GUIDE.md, API_V03.md và README.md; số lượng nghề/schema trong lịch sử không mô tả v0.3.

# Kiểm thử và những điều chưa được xác minh

## Kết quả tự động tại thời điểm đóng gói

Kết quả máy đọc được trong `artifacts/python-test-report.json`, `artifacts/browser-test-report.json` và `artifacts/browser-operations-report.json`; log ca Python ở `artifacts/python-tests.log`. Không thay báo cáo dự kiến trong reference bằng “đã pass”.

### Python / luật game / HTTP / persistence

347 ca dùng `unittest`, không cần pip. Trong đó có 192 ca tham số hóa 96 vignette × hai lựa chọn; 26 biến thể nhiệm vụ nghề; và các ca luật, validation, DB, HTTP, AI fallback còn lại. Các ca đều chạy với dữ liệu giả lập/temp DB, không dùng session của người chơi.

Các điều kiện đã kiểm gồm giữ tồn giữa hai giỏ, bán/giao đúng một lần, gói sai được sửa, không soft-lock khi số dư bằng 0, không xuất lô giữ/hết hiệu lực, không đoán phiếu thiếu, nhiều-một và một-nhiều, thiếu nguồn, không kết thúc CSKH bằng lời hứa, practice không tạo kinh tế, cost không âm ví, version/save lỗi, xung đột ghi, gửi trùng ID, Host/Origin/CSRF, path traversal, nội dung chat XSS và lỗi endpoint giả lập.

Chạy lại:

```sh
python3 scripts/run_checks.py
npm run check
```

Node chỉ kiểm cú pháp JS, không phải kiểm gameplay. `package.json` không có runtime dependencies; không cần `npm install` để chơi.

### UI với Chromium

Suite thao tác qua DOM thật và API server thật: bắt đầu cả bốn nghề, hoàn tất một đơn/phiếu/hồ sơ/vụ cho từng nghề; xử lý một sự kiện thật và diễn tập người quay clip; đăng bài/trả lời; chat; mua và đặt cây; chụp ảnh; xuất/nhập save; tải lại trang; kiểm bố cục portrait 390×844 và menu Thêm. Kiểm không có pageerror chưa bắt trong các luồng đó.

Môi trường tạo gói chặn `page.goto` tới localhost bằng chính sách quản trị Chromium. Không thay đổi chính sách đó. `scripts/browser_harness.py --bridge` nạp chính CSS và mã module vào một `about:blank` có global mới, rồi chuyển request `/api/` tới server qua httpx. Không mở các URL ngoài API local trong adapter.

**Giới hạn bằng chứng:** bridge xác minh render, sự kiện DOM, luồng UI và backend, nhưng không chứng minh browser fetch/cookie/CSP trực tiếp hoặc Safari iOS. HTTP test riêng xác minh cookie/header/status bằng client chuẩn; đây không phải thay thế kiểm thiết bị thật. Không ghi “đã test iPhone” chỉ vì viewport có touch.

Ở máy phát triển không bị chặn navigation, chạy `scripts/browser_smoke.py` **không có `--bridge`** để dùng HTTP trong Chromium bình thường. Script phát triển cần Playwright/httpx và browser được cài riêng, không có trong ZIP.

## Cần kiểm trước khi phát hành

Chưa kiểm Windows/macOS installer, iPhone/Safari thật, Android thật, accessibility với screen reader, tải nhiều người, session abuse, vận hành Internet, Docker image hoặc model AI thật. Chưa playtest cân bằng nhiều ngày với người dùng thật. Báo cáo 347 pass không khẳng định mọi tương tác hoặc yêu cầu trong thiết kế gốc đều hoàn thành.

Những hình trong `artifacts/` là ảnh chụp renderer/UI của bản mã này. Chúng không phải ảnh concept, nhưng cũng không chứng minh một luồng chưa được test.

## Làm ZIP lại

```sh
python3 scripts/run_checks.py
npm run check
python3 scripts/package.py
python3 scripts/verify_package.py ../Mot_ngay_lam_nghe_Source_Code_v0_2.zip
```

ZIP loại `.env`, DB, cookie/session runtime, cache, node_modules và font binaries. `MANIFEST.json` ở root chứa hash của source và asset; manifest gốc trong reference không phải manifest của source mới. Script verify giải nén ra thư mục sạch, kiểm hash, bật server từ đường dẫn mới và chạy một lệnh có cookie/CSRF.

## Bổ sung v0.2

53 ca Python mới kiểm nhân viên có làm việc thật; giữ hàng đúng tồn; nghỉ/xếp ca/đào tạo; lương chỉ tính ca thực làm; không né hạn đào tạo bằng tuyển lại; tiền thuê theo số ngày ở từng mặt bằng; thuế trên thu nhập nghề, không gồm thưởng/hỗ trợ; thanh toán/gia hạn một lần; sửa đồ; dấu vết chứng cứ; thu hồi và thưởng một lần; trần thưởng; bảo hiểm mua trước; số dư khớp sổ; migrate save-v1/DB cũ và retry an toàn.

Suite `browser_operations.py` có 12 nhóm kiểm: tuyển/giao việc/ca/đào tạo/thưởng/chat; diễn tập không đổi tiền/kỹ năng; lương/điện nước/gia hạn/nộp tiền; mặt bằng/nhân viên thứ hai/camera/bảo hiểm; sửa đồ có hóa đơn; vụ trộm có NPC công an và thu hồi/thưởng; 7 ngày game tạo thuê/thuế; trường hợp không thu hồi và bảo hiểm; tải lại; năm tab ở 390×844; nhân sự/tiền riêng bốn nghề; không lỗi JS chưa bắt.

**Dữ liệu kiểm thử có kiểm soát:** các vụ hỏng đồ thật, trộm bị bắt, không thu hồi và kỳ thu nhập được tạo qua luật game rồi nạp bằng API import save chính thức. Giá trị ngẫu nhiên riêng được cố định trong test để phủ cả hai kết quả. Đây không phải tất cả sự kiện phát sinh ngẫu nhiên trong một lượt chơi và không có endpoint gian lận riêng trong bản game. Ảnh 24–26 thể hiện kết quả từ các fixture này.

Ví dụ chạy suite mới với HTTP bình thường:

```sh
python3 scripts/browser_operations.py --base http://127.0.0.1:8765
```

Có thể thêm `--bridge --chromium /usr/bin/chromium` chỉ trong môi trường kiểm thử nêu ở trên. Bộ nguồn dùng cú pháp tương thích Python 3.11 và được kiểm bằng parser `feature_version=(3,11)`; lần chạy thực tế ở đây là Python 3.13.5.
