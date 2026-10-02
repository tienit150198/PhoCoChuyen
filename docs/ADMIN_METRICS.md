# Số liệu vận hành của Phố Có Chuyện: định nghĩa, cách tính, giới hạn

Tài liệu này dành cho người đọc không chuyên kỹ thuật, ví dụ nhà đầu tư, người mua hoặc bên nhận nhượng quyền, cùng với người vận hành game.
Mỗi chỉ số gồm ba phần:

- **Ý nghĩa**: viết bằng lời thường.
- **Cách tính**: dòng kỹ thuật, nói rõ số lấy từ bảng nào.
- **Giới hạn**: điều cần biết trước khi dùng con số.

Các số này hiển thị ở trang vận hành `/admin`, mục **📊 Tổng quan đầu tư**. Mỗi số trên trang có nút ⓘ giải thích ngay tại chỗ.
Trang còn cho tải về:

- **CSV** của từng phần hoặc của tất cả;
- **báo cáo in** (`/admin#bao-cao`), mỗi phần một trang, có ghi giờ của số liệu và phụ lục định nghĩa.

Định nghĩa trong tài liệu này, trong nút ⓘ, trong CSV và trong báo cáo in lấy từ cùng một nguồn là `DEFS` trong `game/admin_kpi.py`. Khi định nghĩa trong code thay đổi, cần sửa tài liệu này theo.

---

## 1. Nguyên tắc chung

| Nguyên tắc | Nghĩa là |
|---|---|
| **Ngày giờ Việt Nam** | Một "ngày" tính từ 00:00 đến 24:00 giờ Việt Nam (UTC+7), dù máy của người xem đặt múi giờ nào. Cơ sở dữ liệu lưu giờ UTC. Mọi phép đổi ngày đều cộng thêm 7 giờ. |
| **Chỉ ngày đã kết thúc** | Các khoảng "7 / 30 / 90 ngày / Tất cả" chỉ cộng những ngày đã hết. Hôm nay đang dở nên chỉ hiện riêng trên biểu đồ, bằng cột nhạt. |
| **Số đông cứng** | Khi một ngày kết thúc được 20 phút, các số của ngày đó được ghi một lần vào bảng `stat_kpi_daily` và không bao giờ sửa lại. Nhờ vậy số cũ không âm thầm thay đổi khi người chơi xoá bản lưu hay khi dữ liệu chi tiết hết hạn lưu. |
| **Không đoán số** | Phần nào chưa tính được, vì hết thời gian cho phép hoặc lỗi, sẽ để trống và ghi tên phần đó trên trang. Số chưa có dữ liệu hiện "—". **Doanh thu = 0, ghi "chưa bật"**: game chưa có thanh toán, quảng cáo hay gói trả phí, và trang không ước tính doanh thu. |
| **Không có dữ liệu cá nhân** | Trang, CSV và báo cáo đều chỉ có số tổng hợp, không có tên, email, mã phiên, IP hay chữ người chơi gõ. Trong tệp xuất: một ô đếm dưới 5 người ghi là "<5"; một tỉ lệ tính trên dưới 5 người để trống. Trên trang, tỉ lệ tính trên dưới 30 người có nhãn "ít dữ liệu". |
| **Độ tin cậy** | Các tỉ lệ giữ chân và tỉ lệ chuyển đổi có kèm khoảng tin cậy 95% (phương pháp Wilson). Nhóm càng nhỏ thì khoảng càng rộng. |
| **"Đang thu thập từ"** | Bộ đếm mới (xu, thiết bị, độ trễ, lỗi máy chủ, thời gian hoạt động, đỉnh online, AI) chỉ bắt đầu đếm từ ngày bản này lên máy chủ. Trang ghi "từ dd/mm" cạnh mỗi số như vậy, và không có số liệu cho trước ngày đó. |

### Không làm chậm người chơi

- Các số được tính **nền**. Phần tính chỉ chạy khi có người vận hành đang mở trang và dừng khi trang đóng.
- Mỗi lần tính chạy tối đa 10 phút một lần, mỗi phần có giới hạn thời gian (20 giây cho cả phần, 5 giây cho mỗi câu lệnh).
- Phần tính chỉ đọc các bảng thống kê nhỏ và chỉ mục, không quét toàn bộ bảng lớn.
- Phần tính tạm dừng khi máy chủ bận. Các cơ chế bảo vệ từ ngày 30/09 vẫn giữ nguyên:
  - mẫu 400 bản lưu;
  - mỗi 30 phút đọc mẫu một lần;
  - nghỉ gấp 3 lần thời gian vừa chạy;
  - kiểm tra tải máy (load average) trước khi chạy;
  - dừng khi trang đóng.
- Bản lưu nặng khoảng 100 KB nên **không bao giờ đọc hết**. Kinh tế và ví lấy từ mẫu 400 bản lưu thay đổi gần nhất.
- Bộ đếm mới chỉ cộng vào bộ nhớ của tiến trình khi người chơi thao tác. Mỗi tiến trình ghi xuống cơ sở dữ liệu 30 giây một lần.

---

## 2. Tăng trưởng

| Chỉ số | Ý nghĩa | Cách tính | Giới hạn |
|---|---|---|---|
| Tổng bản lưu | Mọi bản lưu đang có, kể cả người mở game rồi đi ngay và bot. | `COUNT(*) FROM sessions` | Không phải số người. |
| **Người đã chơi** | Bản lưu có ít nhất một thao tác chơi thật. | `sessions.revision > 0` **và** (có ngày trong `stat_active`/`stat_players`, **hoặc** thay đổi lần cuối trước khi có nhật ký ngày) | Bản lưu chỉ được nâng cấp phiên bản khi mở lại (`revision` tăng nhưng không có thao tác) **không** được tính (xem lỗi 1 ở mục 10). Một người chơi trên hai thiết bị mà không đăng nhập bị tính là hai người. |
| Tài khoản | Người đã đăng ký tên đăng nhập và mật khẩu. | `COUNT(*) FROM accounts` | Gồm cả tài khoản vận hành và tài khoản thử. |
| Khách đã chơi | Người đã chơi nhưng chưa đăng ký. | người đã chơi − bản lưu có tài khoản | |
| Tỉ lệ có tài khoản | Trong người đã chơi, bao nhiêu phần trăm đã đăng ký. | bản lưu có tài khoản ÷ người đã chơi | |
| Lượt mở game mới | Bản lưu mới tạo trong ngày. Mỗi trình duyệt hoặc thiết bị mới tạo một bản. | `stat_births` theo ngày VN (trigger khi tạo bản lưu) | Gồm cả bot và người chỉ mở rồi đi. |
| **Người chơi mới** | Bản lưu tạo trong ngày **và** có thao tác ngay trong ngày đó. Đây là "nhóm" (cohort) dùng để tính giữ chân. | `stat_births ∩ stat_active` cùng ngày; với ngày đã qua, lấy số đông cứng | Trước đây con số này tăng dần về sau (lỗi 2). Bản này đã sửa. |
| Tỉ lệ kích hoạt | Phần trăm lượt mở mới thực sự chơi ngay ngày đầu. | người chơi mới ÷ lượt mở mới | Bot làm tỉ lệ thấp đi. |
| Tài khoản mới | Tài khoản đăng ký trong ngày VN. | `accounts.created_at` (UTC) đổi sang ngày UTC+7 | |
| Người từng hoạt động (cộng dồn) | Tổng số người có ít nhất một ngày hoạt động, tính đến hết ngày. | cộng dồn `stat_players.first_day` | Chỉ tính từ khi có nhật ký ngày. |
| So với kỳ trước | 7 hoặc 30 ngày gần nhất so với 7 hoặc 30 ngày ngay trước đó. | tổng hai cửa sổ, (mới − cũ) ÷ cũ | Ghi "—" khi kỳ trước chưa nằm trọn trong lịch sử. |

## 3. Hoạt động

| Chỉ số | Ý nghĩa | Cách tính | Giới hạn |
|---|---|---|---|
| **DAU** | Số người có thao tác trong ngày VN. | `COUNT(*) FROM stat_active WHERE day = ?` (trigger khi bản lưu đổi `updated_at`) | |
| WAU / MAU | Số người khác nhau có thao tác trong 7 hoặc 30 ngày, tính đến hết ngày đó. | `COUNT(DISTINCT sid)` trên `stat_active` | `stat_active` giữ mãi (từ 1.4.3); số đông cứng vẫn là nguồn chính cho ngày cũ. |
| Độ dính (DAU/MAU) | Một người chơi trong tháng quay lại trung bình bao nhiêu phần trăm số ngày. 20% tương đương khoảng 6 ngày mỗi tháng. | DAU ÷ MAU của cùng ngày, sau đó lấy trung bình | |
| Người quay lại | DAU trừ người chơi mới. | `dau − new_players` | |
| Người trở lại sau ≥ 7 ngày | Người hoạt động hôm nay mà lần hoạt động trước cách đó từ 8 ngày trở lên. | `stat_players.last_day ≤ ngày − 8` trước khi cập nhật | Bảng mới, nhưng dựng lại được từ nhật ký ngày (`stat_active`) nên có số cho cả các ngày trước. |
| Đỉnh người online | Số người có thao tác trong 5 phút gần nhất. Đo mỗi phút, lấy mức cao nhất trong ngày. | `COUNT(sessions.updated_at ≥ now − 5')` qua chỉ mục `stat_sessions_seen` | **Thu thập từ bản này.** |
| Đỉnh thao tác/phút | Số thao tác mỗi phút của mọi tiến trình máy chủ, lấy mức cao nhất trong ngày. | `command_stats().per_min` | **Thu thập từ bản này.** |
| Phút chơi / người / ngày | Thời gian chơi trung bình. Một phiên kết thúc khi 5 phút không có thao tác. | tổng giây ÷ số người (`stat_play`, `stat_play_daily`); khi gộp nhiều ngày thì lấy trung bình có trọng số theo số người | Từ 01/10 00:31 là số chính xác. Trước đó là ước tính từ biên nhận lệnh, và trang ghi rõ những ngày ước tính. |
| Trung vị phút chơi | Một nửa người chơi chơi ít hơn mức này mỗi ngày. | trung vị phân bố giây/người | |
| Phiên / người / ngày | Số lần vào chơi trung bình mỗi người mỗi ngày. | số phiên ÷ số người | Một phiên chơi qua nửa đêm bị tách thành hai ngày. |
| Tổng giờ chơi | Tổng số giờ mọi người chơi trong ngày. | tổng giây ÷ 3600 | |
| Giờ chơi trong tuần | Số người hoạt động trung bình theo từng giờ VN và từng thứ trong tuần. | 28 ngày đã qua gần nhất, `stat_play_daily.data.hours` | |

## 4. Giữ chân

| Chỉ số | Ý nghĩa | Cách tính | Giới hạn |
|---|---|---|---|
| **Giữ chân D1/D3/D7/D14/D30** | Trong người chơi mới của một ngày, bao nhiêu phần trăm quay lại đúng 1/3/7/14/30 ngày sau. | Σ người quay lại ở ngày+k ÷ Σ người chơi mới, chỉ tính các ngày bắt đầu đã đủ k ngày, trong 60 ngày bắt đầu gần nhất | Trước đây D30 không bao giờ tính được (lỗi 3). Có khoảng tin cậy 95%. **Game ra mắt 28/09: D7 cần đến 05/10, D30 cần đến 28/10 mới có nhóm đầu tiên.** |
| Từ đầu (số đông cứng) | Cùng cách tính, áp dụng cho mọi ngày bắt đầu kể từ khi có nhật ký. | `stat_kpi_daily.ret_d{k}`, ghi một lần khi ngày k đã qua | Số đông cứng không đổi khi bản lưu bị xoá. |
| Giữ chân cuốn (D1+, D7+…) | Phần trăm người còn quay lại vào ngày k **hoặc bất kỳ ngày nào sau đó**. | có `stat_active` ở ngày ≥ ngày đầu + k | Luôn lớn hơn hoặc bằng giữ chân đúng ngày. |
| Nhóm theo tuần bắt đầu | Phần trăm người chơi mới của một tuần (thứ Hai đến Chủ nhật) còn hoạt động ở tuần thứ k. | `stat_births` + `stat_active`, 10 tuần | Ô của tuần chưa hết được tô nhạt. |
| Tăng trưởng theo tuần | Người hoạt động trong tuần = mới + ở lại (cũng chơi tuần trước) + trở lại (nghỉ ≥ 1 tuần). "Rời đi" là người chơi tuần trước nhưng tuần này không chơi. | `_week` trong `game/kpi.py`, đông cứng theo tuần | Tuần đầu chưa có tuần trước để so, nên đánh dấu "*". Tính lại được cho mọi tuần đã có nhật ký ngày. |
| Tỉ lệ rời bỏ tuần | Trong người chơi tuần trước, bao nhiêu phần trăm không chơi tuần này. | rời đi ÷ người chơi tuần trước | |
| Khách → tài khoản | Trong người chơi mới của 30 ngày đã qua, bao nhiêu phần trăm hiện đã đăng ký. | người chơi mới có dòng trong `accounts` ÷ người chơi mới | |
| Số ngày hoạt động / người | Mỗi người đã chơi bao nhiêu ngày khác nhau. | `stat_players.days` | Bảng mới. Dữ liệu được dựng lại từ `stat_active` khi tính lần đầu. |

## 5. Gắn bó

| Chỉ số | Ý nghĩa | Cách tính | Giới hạn |
|---|---|---|---|
| Dùng tính năng | Trong người hoạt động, bao nhiêu phần trăm dùng một nhóm tính năng (ngân hàng, học, nhà, tủ đồ…), lấy trung bình mỗi ngày. | người có thao tác thuộc nhóm (theo tiền tố tên lệnh, `kpi.FEATURES`) ÷ DAU, 7 ngày | `stat_actions` giữ mãi (từ 1.4.3); ngày cũ dùng số đông cứng. |
| Người trên bảng xếp hạng | Người có tên trên bảng tổng. | `leaderboard board='all'` | |
| Đã thành thạo ≥ 1 nghề | Phần trăm người đã lên cấp 3 ở ít nhất một nơi làm. | `mastered ≥ 1 ÷ người trên bảng` | |
| Ngày làm việc (trung vị) | Số ngày làm việc trong game (không phải ngày thật), cộng mọi nơi làm. | trung vị `leaderboard.days` | |
| Nghề | Số người, phần trăm thành thạo và số ngày trung bình của từng nghề. | `leaderboard` theo bảng nghề | |
| Cột mốc | Phần trăm người mở game đã đạt từng bước: đặt tên, khách đầu, lên cấp 2, hết ngày 7… | `stat_milestones` ÷ số "Mở game" | Đo từ 01/10. Một số người cũ được ước tính. |
| Tin nhắn chat / người nhắn tin / tỉ lệ người nhắn tin | Hoạt động chat chung theo ngày. | `chat_messages` (không tính tin quản trị), tìm khoảng `id` của ngày bằng tìm kiếm nhị phân trên khoá chính | Không đọc nội dung tin nhắn. |
| Cặp bạn bè, người có bạn, cặp đôi, đã cưới, đám cưới, hẹn hò 30 ngày | Mức độ xã hội trong game. | `friends`, `couples`, `wedding_parties`, `live_dates` | Số tại thời điểm tính, không có lịch sử theo ngày. |

## 6. Kinh tế (xu trong game)

| Chỉ số | Ý nghĩa | Cách tính | Giới hạn |
|---|---|---|---|
| Xu tạo ra / Xu tiêu đi / Xu ròng | Lượng xu người chơi nhận và chi qua thao tác. Xu ròng dương kéo dài nghĩa là lạm phát. | Sau mỗi thao tác: thay đổi của (ví + quỹ nơi làm + tiền gửi ngân hàng; nợ không trừ). Phần tăng cộng vào `xu_in:<lệnh>`, phần giảm cộng vào `xu_out:<lệnh>` | **Thu thập từ bản này.** Tiền chuyển giữa ví, quỹ và ngân hàng không tính. Vay tính là xu vào, trả nợ là xu ra. Quà và quỹ chung giữa hai người chơi chưa được tính. Lệnh lặp lại (cùng mã yêu cầu) và lệnh lỗi không được tính. |
| Xu tạo ra / DAU | Xu một người nhận được trong một ngày. | `xu_in ÷ dau` | |
| Ví trung vị (mẫu) | Số xu của người chơi ở giữa. | trung vị ví trong mẫu 400 bản lưu thay đổi gần nhất; ghi mỗi ngày một điểm | **Mẫu không ngẫu nhiên.** Đây là toàn bộ người chơi gần đây (trang ghi rõ "mọi người chơi có thao tác từ …"), nên lệch về người đang chơi nhiều. ± là sai số 95% nếu coi đây là mẫu. |
| **Doanh thu** | Game chưa có thanh toán, quảng cáo hay gói trả phí. | **0, chưa bật** | Không ước tính. |

## 7. Chất lượng và ổn định

| Chỉ số | Ý nghĩa | Cách tính | Giới hạn |
|---|---|---|---|
| Độ trễ thao tác p50/p95/p99 | Thời gian máy chủ xử lý một thao tác (không tính mạng). | biểu đồ `cmd_ms:<ô>` theo ngày; lấy mốc trên của ô chứa phân vị, nên là số dè dặt | **Thu thập từ bản này.** |
| Thời gian hoạt động | Phần trăm số phút trong ngày máy chủ đang chạy. | `up_min` (+1 mỗi phút) ÷ số phút của ngày | **Thu thập từ bản này.** Ngày đầu bắt đầu giữa chừng nên không tính. Chỉ đo được khi máy chủ còn chạy, tức là không phải đo từ bên ngoài. |
| Lỗi máy chủ (5xx) | Phần trăm câu trả lời API là lỗi máy chủ, gồm cả 503 "đang bận". | `http:5xx ÷ http:*` | **Thu thập từ bản này.** |
| Lỗi trình duyệt / 1000 thao tác | Lỗi JavaScript báo về, chia theo số thao tác. | `stat_client_errors` (bỏ lỗi do Zalo hoặc tiện ích) ÷ thao tác × 1000 | |
| Góp ý, Góp ý / 100 DAU | Mức độ người chơi lên tiếng. | `player_feedback.created_at` theo ngày VN | |
| Phản hồi góp ý | Thời gian từ lúc người chơi gửi đến lúc người vận hành đọc (trung vị, trung bình), phần trăm đã đọc, **số còn chờ và chờ lâu nhất**. | `stat_fb_ack`, cửa sổ tính từ nửa đêm VN | Trước đây trung vị che mất các góp ý còn chờ (lỗi 5). |
| Thời gian tải trang p50 | Từ lúc mở trang đến khung hình đầu tiên của game, 7 ngày. | `stat_loads` metric `frame` | |
| Lượt gọi AI | Số lần game gọi mô hình ngôn ngữ, cộng mọi tiến trình. | `stat_counters ai:*` | Trước đây chỉ đếm một tiến trình và mất khi khởi động lại (lỗi 4). |

## 8. Nguồn người chơi

| Chỉ số | Ý nghĩa | Cách tính | Giới hạn |
|---|---|---|---|
| Nguồn | Người chơi đến từ đâu, kèm D1 và D7 của từng nguồn. | `stat_acquisition` (utm_source, nếu không có thì trang giới thiệu, nếu không có nữa thì "direct") | |
| Hệ điều hành / loại máy / trình duyệt / ngôn ngữ | Thiết bị của các lượt mở mới. | `dev_os:`, `dev_form:`, `dev_br:`, `lang:` theo User-Agent và Accept-Language, chỉ lưu nhóm, không lưu chuỗi gốc | **Thu thập từ bản này.** |
| Bot | Lượt mở do máy tìm kiếm hoặc trình xem trước liên kết. | `dev_bot` | Bot cũng tạo bản lưu (và được tính trong "lượt mở game mới") nhưng không bao giờ thành "người chơi mới". |

## 9. Hạ tầng

| Chỉ số | Cách tính |
|---|---|
| Dung lượng cơ sở dữ liệu | `pg_database_size` hoặc kích thước tệp SQLite |
| Kích thước bản lưu | `pg_column_size(state)` (sau nén) hoặc `octet_length`, trên mẫu 400 bản lưu, đọc 100 bản mỗi câu lệnh |
| Bảng lớn nhất | số dòng đếm nền mỗi 2 phút; bảng lớn dùng số ước tính (≈) |
| Phiên bản, số tiến trình, CPU, thao tác/phút lúc này | thông tin của máy chủ |

---

## 10. Lỗi số liệu đã sửa trong bản này

| # | Sai ở đâu | Ảnh hưởng | Cách sửa |
|---|---|---|---|
| 1 | Bản lưu cũ chỉ được nâng cấp phiên bản khi mở lại (không có thao tác) vẫn có `revision > 0`. Khi di chuyển dữ liệu, chúng bị tính là "người đã chơi" và "khách", và lần mở lại tiếp theo còn tạo một dòng DAU. | "Người đã chơi", "khách" và DAU bị **thổi phồng** sau đợt di chuyển. | Loại các bản lưu "ma": không có ngày hoạt động và có thay đổi sau khi nhật ký bắt đầu. Con số bị loại hiện riêng ở "chưa từng thao tác". Mốc so sánh dùng ngày bắt đầu nhật ký, không dùng thời điểm thay đổi cuối. |
| 2 | "Người chơi mới" của một ngày đếm cả người tạo bản lưu hôm đó nhưng **chơi vào hôm sau**. | Số người chơi mới của các ngày cũ tăng dần về sau. | Chỉ tính người có thao tác ngay trong ngày tạo bản lưu (cùng định nghĩa với nhóm giữ chân). Ngày đã qua dùng số đông cứng. |
| 3 | Nhóm giữ chân chỉ giữ 30 ngày bắt đầu. | **D30 không bao giờ tính được**, D14 thiếu một nửa. | Giữ 60 ngày bắt đầu, và thêm đường "từ đầu" lấy từ số đông cứng. |
| 4 | Bộ đếm AI nằm trong bộ nhớ của từng tiến trình. | Chỉ thấy khoảng 1/8 số lượt (8 tiến trình), và mất hết khi khởi động lại. | Ghi vào `stat_counters` (`ai:*`), cộng mọi tiến trình, giữ lại qua các lần khởi động. |
| 5 | Góp ý "N ngày" dùng cửa sổ trượt 24h×N thay vì ngày VN. Trung vị thời gian đọc chỉ tính các góp ý đã đọc. | Số theo ngày lệch; góp ý chờ lâu bị che. | Cửa sổ tính từ nửa đêm VN. Thêm số còn chờ, chờ lâu nhất và phần trăm đã đọc. |
| 6 | Trang vận hành hiển thị giờ theo máy của người xem. | Xem từ nước ngoài thì "hôm nay" và giờ bị lệch. | Mọi giờ hiển thị theo `Asia/Ho_Chi_Minh`. |
| 7 | Dòng phụ D1 ghi số người của cả khoảng thời gian. | Đọc nhầm mẫu số của D1. | Ghi "trên N người đủ 1 ngày" (chỉ các nhóm đã đủ ngày). |
| 8 | Nhãn "mẫu" của các thẻ tính từ bản lưu không nói rõ mẫu là gì. | Dễ hiểu nhầm là mẫu ngẫu nhiên. | Ghi "toàn bộ người chơi có thao tác từ <thời điểm>", và nói rõ đây không phải mẫu ngẫu nhiên. |
| 9 | Dữ liệu chi tiết (`stat_active` 120 ngày, `stat_actions` 60 ngày) bị xoá theo hạn, và lịch sử chỉ đọc từ dữ liệu sống. | Số cũ đổi hoặc mất khi dữ liệu hết hạn hay bản lưu bị xoá (thiên lệch sống sót). | Số theo ngày được đông cứng vào `stat_kpi_daily` và bảng `stat_players`. Việc dọn dẹp không bao giờ xoá ngày chưa đông cứng. |
| 10 | Tỉ lệ rời bỏ đếm cả bản lưu "ma" (lỗi 1). | Tỉ lệ rời bỏ bị thổi phồng. | Chỉ tính bản lưu có ngày hoạt động. |

Mỗi lỗi có một bài kiểm thử tái hiện trong `tests/test_admin_kpi.py`.

## 10b. Giữ số liệu mãi mãi (từ 1.4.3)

Theo yêu cầu chủ game (02/10): số liệu thống kê người chơi không bao giờ bị xoá hay sửa.

- Không còn xoá theo hạn: `stat_active`, `stat_play`, `stat_play_est`, `stat_actions`, `stat_leaves`, `stat_leave_last`, `stat_client_errors`, `stat_loads` đều giữ mãi. Các biến `ADMIN_STATS_ACTIVE_DAYS`, `ADMIN_STATS_PLAY_DAYS`, `RETENTION_*_DAYS` mặc định 0 = giữ mãi; chỉ khi người vận hành tự đặt số mới xoá.
- Bản lưu bị xoá (người chơi tự xoá, bản lưu khách bỏ trống, bản lưu không hoạt động lâu) **không còn kéo theo số liệu**: các trigger `*_gone` không xoá gì nữa, `retention.forget` không xoá. Dòng số liệu chỉ mang mã ngẫu nhiên của bản lưu, không tên, không tài khoản, nên sau khi bản lưu mất thì không còn nối được tới người nào.
- Số theo ngày vẫn được đông cứng vào `stat_kpi_daily` / `stat_players` như trước.
- Dung lượng tăng dần theo số người chơi; trang Giữ chân hiện dung lượng log để theo dõi.

## 11. Các giới hạn đã biết (chưa sửa, cần nói rõ khi trình bày)

- **Thời gian lịch sử ngắn.** Game ra mắt 28/09/2026 và nhật ký theo ngày bắt đầu cùng đợt đó. D7 chỉ có nhóm đầu tiên từ 05/10, D30 từ 28/10. Các bộ đếm mới (xu, thiết bị, độ trễ, 5xx, thời gian hoạt động, đỉnh online, AI) bắt đầu từ ngày bản này lên máy chủ.
- **Một người, nhiều thiết bị.** Khách chưa đăng nhập dùng hai trình duyệt bị tính là hai người. Tài khoản gộp được việc này, nhưng chỉ cho người đã đăng ký.
- **Tài khoản vận hành và tài khoản thử chưa bị loại** khỏi các số. Ảnh hưởng nhỏ, nhưng là một vài người khi game còn ít người chơi.
- **Bot** tạo bản lưu. Bot nằm trong "lượt mở game mới" và "tổng bản lưu", không nằm trong "người chơi mới" hay DAU (bot không thao tác).
- **Phiên qua nửa đêm** bị tách thành hai ngày.
- **"Khách đầu" theo nguồn** có mẫu số là mọi lượt mở của nguồn đó, không chỉ người đã chơi.
- **Kinh tế** chưa tính quà và quỹ chung giữa hai người chơi, cũng không tính các thay đổi ngoài lệnh chơi (ví dụ quản trị sửa dữ liệu).
- **Ví và kích thước bản lưu** lấy từ mẫu người chơi gần đây, không phải mẫu ngẫu nhiên.
- **Thời gian hoạt động** do chính máy chủ đo. Nếu cả máy chủ tắt thì phút đó không được ghi, nên tỉ lệ vẫn đúng, nhưng con số này không thay được việc đo từ bên ngoài.

## 12. Bảng mới (thêm, không sửa bảng cũ)

Các bảng này được tạo idempotent bởi `admin_stats.ensure()`: chạy lại không sao, chỉ thêm bảng.

SQLite (`game/kpi.py SCHEMA`):

```sql
CREATE TABLE IF NOT EXISTS stat_counters (day TEXT NOT NULL, key TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(day, key)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS stat_kpi_daily (day TEXT NOT NULL, key TEXT NOT NULL, value REAL, at REAL NOT NULL,
  PRIMARY KEY(day, key)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS stat_players (sid TEXT PRIMARY KEY, first_day TEXT NOT NULL, last_day TEXT NOT NULL,
  days INTEGER NOT NULL) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS stat_players_first ON stat_players(first_day);
CREATE INDEX IF NOT EXISTS stat_players_last ON stat_players(last_day);
```

PostgreSQL (`game/kpi.py PG_DDL`):

```sql
CREATE TABLE IF NOT EXISTS stat_counters (day text COLLATE "C" NOT NULL, key text COLLATE "C" NOT NULL, n bigint NOT NULL DEFAULT 0,
  PRIMARY KEY (day, key)) WITH (fillfactor = 85);
CREATE TABLE IF NOT EXISTS stat_kpi_daily (day text COLLATE "C" NOT NULL, key text COLLATE "C" NOT NULL, value double precision,
  at double precision NOT NULL, PRIMARY KEY (day, key));
CREATE TABLE IF NOT EXISTS stat_players (sid text COLLATE "C" PRIMARY KEY, first_day text COLLATE "C" NOT NULL,
  last_day text COLLATE "C" NOT NULL, days bigint NOT NULL);
CREATE INDEX IF NOT EXISTS stat_players_first ON stat_players (first_day);
CREATE INDEX IF NOT EXISTS stat_players_last ON stat_players (last_day);
```

**Kích thước ước tính:**

- `stat_counters`: khoảng 150 khoá mỗi ngày, tức khoảng 55 nghìn dòng mỗi năm.
- `stat_kpi_daily`: khoảng 40 khoá mỗi ngày.
- `stat_players`: mỗi người chơi một dòng, khoảng 60 byte.

**Chi phí khi chạy:**

- Mỗi thao tác và mỗi câu trả lời API: một lần cộng vào từ điển trong bộ nhớ.
- Mỗi 30 giây, mỗi tiến trình: một giao dịch ghi các khoá đã đổi.
- Mỗi phút, một tiến trình: một câu `COUNT` qua chỉ mục `stat_sessions_seen`.
- Mỗi lần tính nền (khi có người xem trang): tối đa 45 ngày được đông cứng, mỗi ngày trong một giao dịch ngắn. Các ngày đã đông cứng không phải tính lại.

Để kiểm tra lại số trực tiếp trên cơ sở dữ liệu, dùng `scripts/verify_admin_metrics.sql`. Tệp chỉ đọc, có giới hạn thời gian và chỉ đi qua chỉ mục.
