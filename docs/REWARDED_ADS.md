# 📺 Quảng cáo có thưởng

Chủ game chốt ngày 18/10/2026:
- Chỉ dùng quảng cáo có thưởng (reward), không dùng quảng cáo xen màn hình.
- Chỉ dùng Google. Meta đã đóng Audience Network cho web từ tháng 4/2020.
- Mỗi tài khoản xem tối đa **7 lượt mỗi ngày giờ Việt Nam**. Không giới hạn theo IP hay thiết bị, clone vẫn được.
- Ghép ba có hồi sinh.
- Giờ vàng: **1 tiếng ×1,5 cho mỗi lượt xem**.

## Mã nguồn

| Phần | File |
|---|---|
| Luật, thưởng, kiểm tra bản lưu | `game/ads.py` (`journey['ads']`) |
| Định tuyến lệnh `ad_ticket` / `ad_claim` | `game/engine.py` |
| Giờ vàng riêng ×1,5 | `game/workplace_business.py` `_finish` (đơn nhân viên), `game/quay_business.py` `sale` (quầy) |
| Ghép ba: lượt hỗ trợ từ quảng cáo | `game/tile_match.py` (`_free_all`, `_end`: dùng sau lượt miễn phí trong ngày, trước khi trả xu) |
| Trại giam: bớt 5 phút | `game/ads.py` lùi `journey.jail.since`; `game/jail.py` `OPEN_COMMANDS` |
| Thưởng khép ca | `game/journey.py` `_end_of_day` → `ads.offer_shift` |
| Trang web: meta `mnl-bonus`, CSP, `/ads.txt`, Referrer-Policy | `game/ads.py`, `game/webassets.py`, `server.py` |
| Client | `public/js/v4/bonus-video.js`, `public/css/bonus-video.css` |
| Nút ở từng chỗ | `public/js/v4/tile-match.js` (màn thua), `public/js/v4/jail.js` (nút hết ngày), `public/js/app.js` (☰ Thêm, tổng kết ca) |
| Test | `tests/test_ads.py`, `scripts/browser_bonus_video.py` |

File phía client không được có chữ "ads" trong tên. Trình chặn quảng cáo sẽ chặn file đó, và `tests/test_asset_names.py` cũng chặn.

## Luồng một lượt xem

1. Người chơi bấm nút 📺. Client gửi `ad_ticket {place}`. Server từ chối nếu đã đủ 7 lượt trong ngày, hoặc chỗ đó không còn gì để cho.
2. Client hiện quảng cáo thưởng của Google (`adBreak({type:'reward'})`). Cú bấm nút 📺 chính là lời mời xem, nên `beforeReward` gọi `showAdFn()` luôn. Nếu không có quảng cáo (không có nguồn, bị trình chặn quảng cáo, tải script lỗi), client báo một dòng ngắn và không tính lượt.
3. Khi có `adViewed`, client gửi `ad_claim {ticket}`. Server chỉ nhận vé khi đã qua ít nhất 8 giây (`MIN_WATCH_S`) và chưa quá 15 phút kể từ lúc phát vé. Server trả thưởng, tăng số lượt, và mở rương ở lượt 3 và lượt 7.

**Giới hạn đã biết:** quảng cáo trên web không có xác minh phía máy chủ (SSV). Ai tự viết script có thể bỏ qua bước xem quảng cáo, nhưng vẫn chỉ được tối đa 7 lượt thưởng mỗi ngày. Chủ game đã chấp nhận điều này.

**Lớp hiển thị:** quảng cáo Google là một iframe cố định, nằm dưới các `<dialog>` modal. Vì vậy các dialog đang mở được đóng lại trong lúc quảng cáo chạy, xem xong thì `restore()` của từng chỗ mở lại đúng màn.

## Phần thưởng

| Chỗ | Thưởng |
|---|---|
| ⏰ `gold` | Lãi tiệm và quầy ×1,5 trong 1 giờ, cộng dồn với Giờ vàng chung của phố. Mỗi lượt cộng thêm 1 giờ, tổng không quá 7 giờ phía trước |
| 🧩 `tile` | Hồi sinh: ô vừa làm đầy khay quay lại bàn, kèm +1 ↩, +1 🔀, +1 ⇪. Lượt hỗ trợ được giữ tới khi dùng, tối đa 30 lượt mỗi loại |
| 🚔 `jail` | Ngày trong trại ngắn lại 5 phút. Trong trại chỉ xem được loại này |
| 💼 `shift` | Ca vừa khép được thêm 50% tiền ca cơ bản, tối đa 3.000 xu như trần x3. Mỗi ca nhận một lần |
| 🎁 Lượt 3 / lượt 7 | 3.000–8.000 xu / 10.000–30.000 xu |

Không đặt nút 📺 ở **Chợ đen** (cờ bạc giả lập, rủi ro chính sách AdSense) và ở **lì xì / chuyển khoản**.

## Bật quảng cáo

1. **Đăng ký AdSense** cho `phocochuyen.io.vn` và chờ duyệt. Sau đó nộp đơn vào chương trình H5 Games Ads: https://adsense.google.com/start/h5-games-ads/
2. **Thêm biến môi trường** vào `/etc/mot-ngay-lam-nghe/game.env`:
   - `ADS_CLIENT=ca-pub-XXXXXXXXXXXXXXXX`
   - Tùy chọn: `ADS_TEST=1` để Google chỉ trả quảng cáo thử trong lúc kiểm tra.
3. **Rolling reload.** Kiểm tra `/ads.txt` trả đúng dòng `google.com, pub-…, DIRECT, f08c47fec0942fa0`.
4. **Thử trên máy thật:** ☰ Thêm → 📺 Quà xem quảng cáo. Xong thì bỏ `ADS_TEST`.
5. **Tắt khẩn cấp:** đặt `MNL_ADS_OFF=1` rồi reload. Mọi nút 📺 biến mất, bản lưu giữ nguyên.

Chạy thử ở máy local, không cần Google: đặt `ADS_FAKE=1`. Quảng cáo khi đó là một màn đếm ngược. Không bao giờ bật `ADS_FAKE` trên production.

## "Có gì mới" cho bản bật quảng cáo (soạn sẵn)

Chỉ thêm vào `game/whats_new.py` ở đúng bản đã có `ADS_CLIENT`:

```python
dict(version="…", date="…", items=(
    dict(emoji='📺', text="Quà xem quảng cáo (☰ Thêm): mỗi ngày 7 lượt, lượt 3 và lượt 7 mở rương xu."),
    dict(emoji='⏰', text="Xem một quảng cáo: Giờ vàng riêng, lãi tiệm và quầy ×1,5 trong 1 giờ."),
    dict(emoji='🧩', text="Ghép ba khay đầy? Xem quảng cáo để hồi sinh, kèm thêm trợ giúp."),
    dict(emoji='💼', text="Khép ca xong xem quảng cáo nhận thêm tiền thưởng ca. Trong trại, mỗi lượt bớt 5 phút."),
)),
```
