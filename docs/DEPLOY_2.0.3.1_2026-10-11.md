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
  - Bị bắt: **tịch thu tiền cược**, phạt **30% tiền lời hôm nay** (trừ ví trước, thiếu thì trừ tài khoản ngân hàng, sổ
    không kỳ hạn, sổ có kỳ hạn; không áp trần 2.000 xu của `loss_limits`), tạm giữ 3 ngày.
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
