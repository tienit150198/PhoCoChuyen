# Thị trường đầu tư theo giờ thực

User yêu cầu và giao quyền chọn tỷ lệ/nhịp biến động: 1 giờ thực = 1 ngày thị trường, cập nhật khoảng 10 phút; cả coin và vàng có tăng/giảm, tin tức và lời/lỗ. Thực hiện trong worktree hiện có, không deploy theo chỉ dẫn mới nhất. Không đổi tiết kiệm, hội chợ hoặc nghề.

## Thiết kế

Giá chung phía server, chia thời gian Unix thành phiên 600 giây; 6 phiên là một ngày thị trường. Dùng seed bí mật từ môi trường (MNL_MARKET_SALT, dự phòng MNL_GOLD_SALT), không gửi seed hay lịch giá tương lai. Giá là hàm của thời điểm, không lệ thuộc lượt truy cập, ngày sống, seed người chơi, giờ máy khách hoặc việc server có chạy liên tục không. Tính có giới hạn/caching để không thêm lag.

Mỗi ngày có chế độ tăng, giảm hoặc đi ngang; tin tức kéo dài nhiều phiên và ảnh hưởng hướng đi nhưng không bảo đảm mỗi phiên cùng chiều. Coin biến động mạnh hơn vàng; đà tăng dài hạn nhẹ, có điều chỉnh về vùng giá hợp lý và phiên sốc có giới hạn. Không gán kết quả lời/lỗ riêng theo người. Giữ phí và quy tắc chi tiêu hiện tại.

Mốc mặc định local là 2026-10-05 00:00 UTC+7. Khi được phép deploy phải đặt `MNL_MARKET_EPOCH` đúng thời điểm chuyển đổi thật (Unix giây), không ở tương lai; sau đó giữ nguyên trên mọi worker. Public server phải có seed riêng ít nhất 24 ký tự từ `MNL_MARKET_SALT` hoặc `MNL_GOLD_SALT`; không dùng seed mặc định local. Giữ nguyên `MNL_GOLD_SALT` cũ để nối giá vàng. Giá vàng tại mốc nối tiếp giá cũ ngày đó. Coin được quy đổi một lần theo giá trị coin cũ tại mốc sang giá chung; giữ nguyên vốn/tiền/phí/lãi đã chốt, sai số lượng nhỏ được kiểm tra. Đọc public chỉ chiếu giá, không ghi dữ liệu; lệnh giao dịch đồng bộ giá hiện tại trong transaction. Cùng thời điểm cho cùng quote. Không dùng số liệu giá tài chính ngoài đời.

Hợp đồng module mới `game/realtime_market.py`: `EPOCH` Unix seconds, `TICK_SECONDS=600`, `DAY_SECONDS=3600`, `now()`, `quote(asset, at=None)` trả dict `price`, `previous`, `history`, `timestamps`, `tick`, `market_day`, `as_of`, `next_at`, `news`; `base_price(asset)` trả giá nối tiếp tại EPOCH. Coin đơn vị 1/100 xu, gold xu/chỉ. History 30 phiên gần nhất, toàn bộ đến thời điểm hiện tại; news public chỉ title/direction/active. Không có metadata tương lai ngoài thời điểm phiên kế tiếp.

UI giữ bảng giao dịch, sửa nhãn ngày và biểu đồ sang phiên 10 phút/giờ thực, nêu ngày thị trường dài 1 giờ. Giá đang giữ/lãi lỗ tính bằng quote hiện tại. Refresh có giới hạn khi bảng mở và tab visible; không poll liên tục toàn bộ save.

## Thực hiện và kiểm tra

- [x] Bộ giá: thêm test mốc 599/600/3599/3600, tính xác định, offline, lịch sử không đổi, chỉ có quá khứ, có cả tăng và giảm, coin biến động mạnh hơn vàng, chi phí chạy sau thời gian dài có giới hạn; chạy RED trước implement.
- [x] Backend: nối `invest.py`, `vang.py` vào bộ giá; test chuyển đổi coin một lần, public không mutate, không đẩy giá theo ngày sống, lệnh lấy giá mới tại biên phiên, bảo toàn giá vốn và phí, validate và reload. Rà consumers: rủi ro dùng vang.value hiện tại; coin vốn không được cộng trong rui.wealth, giữ chính sách hiện có.
- [x] UI: cập nhật `public/js/v4/invest.js` và hook `journeyBoot`; test nhãn thời gian, điểm biểu đồ, public metadata, không nhân đôi timer/lệnh giao dịch. Timer theo mốc server có jitter, retry tối thiểu 30s khi lỗi; dừng khi ẩn/đóng.
- [x] Chạy tests đầu tư/vàng/tiền/rủi ro và Node đầu tư, sửa test cũ chỉ khi giả định ngày sống bị yêu cầu thay đổi.
- [x] Browser mobile 320/390/430: giá/tin/biểu đồ và buy/sell không console error/overflow; lifecycle ẩn/đóng/mở lại sau offline và retry được kiểm tra bằng test timer.
- [x] Review nguồn thay đổi, ghi thông số và kết quả đo. Giữ các sửa lag chưa deploy; không tạo thông báo và không deploy.

## Kết quả 05/10/2026

- 157 tests Python qua (thị trường mới, đầu tư, tin thị trường, rủi ro, ngân hàng, trừ tiền PostgreSQL/idempotency).
- 9 tests Node qua (đầu tư và các kiểm tra hội chợ từ bản sửa lag đang giữ).
- Browser local PostgreSQL: mua/bán cả coin và vàng qua giao diện, 320/390/430 px không tràn ngang, không lỗi JavaScript. Báo cáo `output/playwright/realtime-invest/report.json`, ảnh cùng thư mục. Fixture đã dọn schema riêng.
- Public startup thực tế từ chối seed mặc định trước khi mở database. Review độc lập không còn lỗi chặn.
- `tests.test_rui.OldServer` với nguồn 1.4.31 có lỗi whitelist giá nghề có sẵn; đã tái hiện trên baseline 1.7.14, không sửa/ẩn test đó để nhận là pass toàn bộ.

### Thông số mô hình

Chế độ tin tăng/giảm/đi ngang 40/40/20 theo ngày thị trường; cường độ tin 0,7–1,3 cộng lực mua/bán độc lập [-1,8;1,8]. Ảnh hưởng có nhớ và giảm dần (8 giờ thực), giữ tối đa 48 giờ để việc tính không tăng theo tuổi server. Biên độ log coin/vàng 0,070/0,018; nhiễu phiên 0,008/0,002; xác suất sốc 3% mỗi phiên với cường độ 0,025/0,008, giảm dần trong 6 phiên. Mốc tham chiếu tăng tuyến tính nhẹ 0,060%/0,035% mỗi ngày thị trường, tối đa 4 lần mốc gốc. Đây là tham số nội bộ mô phỏng game, không đưa thành thông báo tỷ lệ thắng.

Qua 3 seed × 720 giờ: phiên giờ kết thúc cùng hướng tin khoảng 72–80%, có cả trường hợp ngược tin. Sai biệt trung bình mỗi phiên coin khoảng 1,446%, vàng 0,366% trong mẫu seed mặc định. 30 ngày thực mô phỏng seed local: coin 66,19–229,40 xu, vàng 482–714 xu/chỉ; đều có nhiều phiên tăng và giảm. Đây là mẫu mô phỏng, không bảo đảm lợi nhuận từng người.

Cold quote sau 10 năm khoảng 2 ms/asset, cache dưới 0,004 ms trong bài đo local. Không phát sinh cron hay replay một vòng cho từng phút offline.

### Lưu ý phát hành sau khi được phép

Đặt mốc chuyển đổi thật và seed riêng cố định trên toàn bộ worker; không thay seed vàng cũ. Không để code cũ tiếp tục giao dịch đồng thời sau chuyển đổi. Migration lượng coin hỗ trợ tối đa 10^15 đơn vị để bảo toàn mọi lượng cũ hợp lệ; bản cũ giới hạn 10^12 nên không rollback nguồn cũ với dữ liệu đã chuyển đổi vượt giới hạn này. Cần snapshot theo quy trình phát hành trước chuyển đổi. Chưa tạo package/version mới, chưa deploy và chưa thông báo trong đợt này.
