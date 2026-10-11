# Hotfix Chợ đen 2.0.3.1 — 11/10/2026

Triển khai theo yêu cầu chủ game, **không công bố** (không đổi Có gì mới). Rolling hoàn tất 16:49:38 UTC+7.

- Release: `/opt/mot-ngay-lam-nghe/releases/2.0.3.1-20261011164815`. Health `2.0.3.1`, build `2.0.3.1+1ed6748096a7`.
- Dựng bằng cách sao chép release 2.0.3 đang chạy (`2.0.3-20261011132357`), rồi thay đúng 7 file: `game/fair.py`,
  `game/fair_bm.py`, `game/fair_hai.py`, `game/fair_golden_days.py`, `game/__init__.py`, `package.json`,
  `package-lock.json`. Trước khi thay đã đối chiếu: 4 file game trên server trùng byte với `origin/main` a84d1d32.
  `MANIFEST.json` cập nhật sha256/bytes của 7 file; 0 file lệch manifest. Không đổi client, schema hay asset.
- Source: commit `fcf36984` (nhánh `fix/cho-den-owner-rules-1011`).
- Quay lui: `mnl-rolling-release --to /opt/mot-ngay-lam-nghe/releases/2.0.3-20261011132357`. Save mới vẫn hợp lệ
  với 2.0.3: dòng Sổ ví ≤ 10^7 (đã tách bằng `_pay_big`), net trong ±10^9, khóa mới `journey.fair_hai_w` là block tùy
  chọn mà bản cũ bỏ qua. Không cần phục hồi database.

## Luật mới (chủ game 11/10, xem `CHO_DEN_OWNER_RULES_2026-10-11.md`)

- **Hai ngày vàng:** 70% chỉ khi cược dưới 50.000 xu **và** lời chợ đen hôm nay chưa quá 300.000 xu. Từ 300.000 xu
  vẫn 40%. Các trường hợp còn lại dùng tỷ lệ thường. Vé cào chỉ trả kiểu sự kiện khi ván được 70%.
- **Công an, mọi ván có tiền cược** (bầu cua, chiếu trong, lô tô, vé cào, đua chó). Tỷ lệ bị bắt là tổng hai phần:
  - Theo tiền lời hôm nay: trên 300k là 2%, trên 1 triệu là 5%, trên 3 triệu là 10%, trên 10 triệu là 20%.
  - Theo tiền cược của ván: 50k–300k là 2→10%, 300k–1 triệu là 30→50%, 1–10 triệu là 50→80%, từ 10 triệu là 90%.
  - Tối đa 90%.
  - Bị bắt: **tịch thu tiền cược**, phạt **30% tiền cược của chính ván đó** (từ 2.0.3.3; 2.0.3.1–2.0.3.2 phạt 30% tiền
    lời cả ngày). Trừ ví trước, thiếu thì trừ tài khoản ngân hàng, sổ không kỳ hạn, sổ có kỳ hạn; không áp trần 2.000 xu
    của `loss_limits`. Tạm giữ 3 ngày.
- **Ô ăn quan (Ông Hai):** bỏ giới hạn 30 ván/ngày. Ván thắng không còn bị phạt từng ván. Ván thắng thứ 51 (đếm
  cộng dồn, `journey.fair_hai_w`) thì bị bắt vì "thiết bị hỗ trợ": phạt 50% tổng ví + ngân hàng, tạm giữ 3 ngày, rồi
  đếm lại từ 0.
- **Phóng dao:** bỏ trần lời 20.000 xu/ngày. Lời phóng dao trong ngày vượt 100.000 xu thì cũng bị bắt vì "thiết bị hỗ
  trợ" như trên.
- **Cược tối đa 10.000.000 xu/ván** (bầu cua, chiếu trong, đua chó). Đây là giới hạn kỹ thuật của save (ví ≤ 10^9);
  ví gần mức đó thì ván bị từ chối bằng câu "Hôm nay chơi vậy đủ rồi".
- Giữ nguyên: ném vòng (miễn phí) vẫn trả tối đa 400 xu/ngày; các bộ phát hiện bấm nhanh/spam của `fair_watch` vẫn phạt
  nhẹ như 2.0.3.

## Xác minh

- Kiểm thử chức năng cục bộ và trên server bằng chính code release (Python 3.12): bị bắt khi lời 2 triệu, cược 400k →
  thu 400k + phạt 600k; phần thiếu trừ sang ngân hàng; cược 5 triệu / 10 triệu qua `validate_state`; ván thắng thứ 51
  của Ông Hai phạt đúng 50% ví + ngân hàng; tỷ lệ bắt theo bảng trên.
- Sau rolling: health 2.0.3.1, `current` đúng release, `mot-ngay-lam-nghe` và `mnl-live` active, 0 Traceback trong log từ
  16:49, 0 phản hồi 5xx trong 2.000 dòng nginx gần nhất. Người chơi tiếp tục chơi chợ đen bình thường sau chuyển bản.
- Các bài kiểm thử cũ đang kiểm luật cũ (phạt từng ván Ông Hai, 30 ván/ngày, trần 2.000 xu ở chợ đen, giữ tiền cược
  khi bị bắt, hằng số tỷ lệ bắt) sẽ báo lỗi cho tới khi được cập nhật theo luật mới.

## 2.0.3.3 — phạt theo ván (17:17 11/10)

Chủ game: "phải tính tiền phạt của 1 trận" — người cược 8–10k/ván bị phạt 30% tiền lời cả ngày. Từ 2.0.3.3 bị bắt thì mất
tiền cược ván đó và phạt thêm 30% chính tiền cược ấy (`fair_bm.round_fine`); ván 10k → mất 10k + phạt 3k. Tỷ lệ bị bắt
không đổi. Commit `6b139d47`, release `2.0.3.3-20261011171609` (thay `game/fair.py`, `game/fair_bm.py` + 3 file phiên bản),
0 file lệch manifest, health 2.0.3.3. Quay lui: `mnl-rolling-release --to …/2.0.3.2-20261011165748`.

## 2.0.3.4 — mọi khoản phạt công an đều theo ván (17:26 11/10)

Sau 2.0.3.3 vẫn còn hai kiểu phạt không theo ván: "Công an kiểm tra đánh bạc" (`_wealth_raid`, 30% ví khi lời hôm nay
trên 50k, 35% mỗi 30 phút) và "Công an kiểm tra tài sản" (`_asset_audit`, 10% tiền lời). Cả hai đã tắt
(`fair.WALLET_CHECKS = False`). "Công an phường kiểm tra" ở chiếu trong (hủy ván, giữ tiền cược) phạt 30% tiền cược ván đó
(trước: 25%, trần 2.000). Bị bắt vì bấm nhanh/spam cũng phạt 30% tiền cược ván đó thay vì theo ví. Lời nhiều chỉ làm tăng
tỷ lệ bị bắt. Commit `38766959`, release `2.0.3.4-20261011172521`, health 2.0.3.4, 0 Traceback.

## 2.0.3.5 (17:33) và 2.0.4 (19:13 11/10)

- 2.0.3.5 `d72cc2da`: nhập bản lưu chỉ vào đúng bản đã xuất, so tổng tài sản; dẹp chiếu chỉ với ván công an đang để ý
  (arrest_p > 0); Mây Coin từ 21:00 tính tin tức ngay đầu giờ.
- Hoàn tiền phạt dư (quà `refund-cd-20261011-*`, 8 người, 18.538.100 xu). Xử phạt nhóm nhân bản tài khoản 09/10
  (Bunnyne gốc + Thịt Viên nhận tiền: còn 10% tài sản; 5 bản sao ntaphuong*: về 0; phần thiếu thành nợ ví). Sao lưu trạng
  thái trước khi phạt: `/root/backup_clone_ring_20261011.tsv` (chmod 600), công cụ `/root/penalty_clone_20261011.py`.
- 2.0.4 `8e9d2356`: gộp 4 nhánh sửa gian lận (x3/bỏ ngày, tiệm áo, kho báu/chó sủa/cưới, nhà/né phạt) + ván từ 50k thắng
  tối đa 40% + phạt bị bắt trừ tiếp sổ Mây/vàng/Mây Coin + tài khoản mới 48 ngày trả lương; Có gì mới 2.0.4. 36 file
  (4 JS nén bằng esbuild 0.28.2, kiểm tra trùng byte với bản đang chạy), check_task_compat OK, không có tiệc cưới trong
  40 phút. Release `2.0.4-20261011191227`, health 2.0.4, game + mnl-live active, 0 Traceback. Quay lui:
  `mnl-rolling-release --to …/2.0.3.5-20261011173211`.
