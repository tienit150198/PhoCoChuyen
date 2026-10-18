# 📺 Quảng cáo có thưởng

Chủ game chốt (18–19/10/2026):
- Chỉ dùng quảng cáo có thưởng (reward), không dùng quảng cáo xen màn hình.
- Chỉ dùng Google. Meta đã đóng Audience Network cho web từ tháng 4/2020.
- Mỗi tài khoản xem tối đa **7 lượt mỗi ngày giờ Việt Nam**. Một máy dùng nhiều tài khoản vẫn được, không chặn theo IP hay thiết bị ("dù sao người ta cũng ủng hộ mà").
- Các chỗ có nút 📺: Ghép ba (hồi sinh kèm trợ giúp), Giờ vàng riêng (1 tiếng ×1,5), bị trộm / bị lừa (lấy lại một nửa), trượt phỏng vấn / thi (thi lại ngay), hàng đang về (về và vào kho luôn: "nếu xem quảng cáo thì cộng vào luôn"), trại giam (ra trại ngay), ghép thú cưng (+10 điểm % tỷ lệ thành công ở mọi hạng: "ví dụ SSS từ 3% lên thành 13% ấy, random nhé").
- Đưa lên nhưng **chưa hiển thị**: production không đặt `ADS_REWARDED`, chủ game nói lúc nào mới bật.
- Không làm thưởng khép ca và rương lượt 3 / lượt 7.

## Mã nguồn

| Phần | File |
|---|---|
| Luật, thưởng, kiểm tra bản lưu | `game/ads.py` (`journey['ads']`) |
| Định tuyến lệnh `ad_ticket` / `ad_claim` | `game/engine.py` |
| ⏰ Giờ vàng riêng ×1,5 | `game/workplace_business.py` `_finish` (đơn nhân viên), `game/quay_business.py` `sale` (quầy) |
| 🧩 Ghép ba: lượt hỗ trợ từ quảng cáo | `game/tile_match.py` (`_free_all`, `_end`: dùng sau lượt miễn phí trong ngày, trước khi trả xu) |
| 🚔 Trại giam: ra ngay | `game/ads.py` → `jail.release`; `game/jail.py` `OPEN_COMMANDS` |
| 💸 Khoản vừa bị trộm / bị lừa | `ads.note_loss()` gọi ở `game/rui.py` (móc túi, trộm vào nhà, hack), `game/mishap.py` (giả danh, link giả, ATM, "tin nội bộ", côn đồ; **không** tính tiền phạt), `game/happenings.py` (trộm ở tiệm, phần không được đền lại), `game/life.py` (bị lừa) |
| 📝 Thi lại | `employment` `cooldown_day`, `certificates` `study.start/ready`, `promotion` `wait` |
| 📦 Hàng về ngay | `game/inventory.py` đơn nhập hàng (các bước của `inv_receive`), `c['shipments']` của quầy kho (nhà thuốc, Mẹ & bé: `engine.stock_received`) |
| 🐾 Ghép thú cưng | `ads.pet_boost` / `ads.spend_pet_boost`, gọi trong `game/pet_tiers.py` `_fuse` (đã gắn từ 2.4.55) |
| Trang web: meta `mnl-bonus`, CSP, Referrer-Policy | `game/ads.py`, `game/webassets.py`, `server.py` (`/ads.txt` và meta `google-adsense-account`: `game/observability.py`) |
| Client | `public/js/v4/bonus-video.js` (luồng xem, bảng ☰ Thêm), `public/js/v4/bonus-button.js` (nút 📺 vẽ từ `state.ads`), `public/css/bonus-video.css` |
| Nút ở từng chỗ | `tile-match.js` (màn thua), `jail.js` (trại), `rui.js` (thẻ bị trộm / hack), `views.js` (trượt phỏng vấn, 🚚 Đang giao), `certificates.js` (chờ bài thi tự học), `promo.js` (hẹn xét lại), `app.js` (quầy kho, ☰ Thêm) |
| Test | `tests/test_ads.py` |

File phía client không được có chữ "ads" trong tên. Trình chặn quảng cáo sẽ chặn file đó, và `tests/test_asset_names.py` cũng chặn.

## Luồng một lượt xem

1. Người chơi bấm nút 📺. Client gửi `ad_ticket {place, what?, career?}`. Server từ chối nếu đã đủ 7 lượt trong ngày, hoặc chỗ đó không còn gì để cho (ví dụ không có hàng nào đang về).
2. Client hiện quảng cáo thưởng của Google (`adBreak({type:'reward'})`). Cú bấm nút 📺 chính là lời mời xem, nên `beforeReward` gọi `showAdFn()` luôn. Nếu không có quảng cáo (không có nguồn, bị trình chặn quảng cáo, tải script lỗi), client báo một dòng ngắn và không tính lượt.
3. Khi có `adViewed`, client gửi `ad_claim {ticket}`. Server chỉ nhận vé khi đã qua ít nhất 8 giây (`MIN_WATCH_S`) và chưa quá 15 phút kể từ lúc phát vé. Server kiểm tra lại chỗ đó còn gì để cho, rồi trả thưởng và tăng số lượt.

**Giới hạn đã biết:** quảng cáo trên web không có xác minh phía máy chủ (SSV). Ai tự viết script có thể bỏ qua bước xem quảng cáo, nhưng vẫn chỉ được tối đa 7 lượt thưởng mỗi ngày.

**Lớp hiển thị:** quảng cáo Google là một iframe cố định, nằm dưới các `<dialog>` modal. Vì vậy các dialog đang mở được đóng lại trong lúc quảng cáo chạy, xem xong thì `restore()` của từng chỗ mở lại đúng màn.

## Phần thưởng

| Chỗ | Thưởng |
|---|---|
| ⏰ `gold` | Lãi tiệm và quầy ×1,5 trong 1 giờ, nhân thêm trên Giờ vàng chung của phố. Mỗi lượt cộng thêm 1 giờ, tổng không quá 7 giờ phía trước |
| 🧩 `tile` | Hồi sinh: ô vừa làm đầy khay quay lại bàn, kèm +1 ↩, +1 🔀, +1 ⇪. Lượt hỗ trợ được giữ tới khi dùng, tối đa 30 lượt mỗi loại |
| 🚔 `jail` | Ra trại ngay. Trong trại chỉ xem được loại này |
| 💸 `theft` | Một nửa khoản vừa bị trộm / bị lừa gần nhất trở lại ví, trong vòng 24 giờ, mỗi khoản một lần |
| 📝 `retake` `what=job` | Nơi tuyển dụng cho ứng tuyển / thi tuyển lại ngay hôm nay |
| 📝 `retake` `what=cert` | Bài thi chứng chỉ tự học mở ngay (từ ngày đời thứ 2; lớp học cấp tốc vốn thi được ngay) |
| 📝 `retake` `what=promo` | Buổi xét thăng chức chưa qua được hẹn lại ngay sau ca làm tới |
| 📦 `rush` | Mọi đơn đang trên đường tới nơi làm đó về ngay và vào kho luôn, như kiểm đếm đủ ở cửa (đơn giao thiếu vẫn khiếu nại được). Kệ hết chỗ thì thùng đó chờ ở cửa |
| 🐾 `pet` | Lần ghép thú cưng tới +10 điểm % tỷ lệ thành công ở mọi hạng (tối đa 95%), vẫn tung may rủi. Giữ một lượt tới khi ghép |

Không đặt nút 📺 ở **Chợ đen** (cờ bạc giả lập, rủi ro chính sách AdSense) và ở **lì xì / chuyển khoản**.

## Bật quảng cáo

1. **Duyệt trang AdSense:** bản 2.4.54 (nhánh `feat/adsense-verify`) gắn meta `google-adsense-account` và `/ads.txt`, không tải script quảng cáo nào. Sau khi deploy, chủ game bấm "Yêu cầu xem xét" và tắt Auto ads.
2. **Duyệt H5 Games Ads:** nộp đơn tại https://adsense.google.com/start/h5-games-ads/
3. **Thêm biến môi trường** vào `/etc/mot-ngay-lam-nghe/game.env`:
   - `ADS_REWARDED=1` (dùng mã nhà xuất bản `ca-pub-9603813200470438` trong `game/observability.py`)
   - Tùy chọn: `ADS_TEST=1` để Google chỉ trả quảng cáo thử trong lúc kiểm tra.
4. **Rolling reload** trong khung 04:00–05:00. Thử trên máy thật: ☰ Thêm → 📺 Quà xem quảng cáo. Xong thì bỏ `ADS_TEST`.
5. **Tắt khẩn cấp:** đặt `MNL_ADS_OFF=1` rồi reload. Mọi nút 📺 biến mất, bản lưu giữ nguyên.

Chạy thử ở máy local, không cần Google: đặt `ADS_FAKE=1`. Quảng cáo khi đó là một màn đếm ngược. Không bao giờ bật `ADS_FAKE` trên production.

## "Có gì mới" cho bản bật quảng cáo (soạn sẵn)

Chỉ thêm vào `game/whats_new.py` ở đúng bản bật `ADS_REWARDED`:

```python
dict(version="…", date="…", items=(
    dict(emoji='📺', text="Quà xem quảng cáo (☰ Thêm): mỗi tài khoản 7 lượt một ngày, xem hết quảng cáo là có quà."),
    dict(emoji='⏰', text="Giờ vàng riêng: lãi tiệm và quầy ×1,5 trong 1 giờ."),
    dict(emoji='🧩', text="Ghép ba khay đầy? Xem quảng cáo để hồi sinh, kèm thêm trợ giúp."),
    dict(emoji='💸', text="Bị trộm, bị lừa: xem quảng cáo lấy lại một nửa số tiền."),
    dict(emoji='📝', text="Trượt phỏng vấn, chờ thi chứng chỉ, hẹn xét thăng chức: xem quảng cáo để thi lại ngay."),
    dict(emoji='📦', text="Hàng đang về: xem quảng cáo là hàng về và vào kho ngay. Trong trại: xem quảng cáo là ra trại ngay."),
    dict(emoji='🐾', text="Ghép thú cưng: xem quảng cáo để lần ghép tới thêm 10% tỷ lệ thành công, hạng nào cũng được."),
)),
```
