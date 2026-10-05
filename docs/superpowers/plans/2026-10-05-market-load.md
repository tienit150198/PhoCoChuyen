# Giảm tải nền và biểu đồ đầu tư

Goal: loại bỏ đọc/ghi bản lưu chỉ để xem giá, cung cấp biểu đồ 1H/1D/3D/1W/1M theo thời gian thực.

Design: dùng WebSocket hiện có, đăng ký khi mở Đầu tư và hủy khi ẩn/đóng; gửi snapshot giá chung khi đăng ký/đổi khung và khi sang phiên 600 giây. API giá công khai chỉ dùng dự phòng, không đọc player/save, không chạy settlement. Cache chung theo phiên và khung, tối đa 181 điểm/tài sản, không có giá tương lai hoặc lịch sử trước thời điểm thị trường mở. Không đổi engine hoặc salt/epoch. Lệnh mua/bán vẫn được server xác nhận như cũ.

1. Regression tests: no full-state polling; recent state suppresses staff background read; chart ranges, timestamp/price axes, out-of-order frames, reconnect/hidden/manual fallback, matching trade quotes.
2. `market_data.py`, `live/market.py`, `live/app.py`, `server.py`: bounded market snapshot, subscription and public fallback endpoint. Reuse feature lifecycle; compute off the socket loop; no DB work.
3. `public/js/v4/invest-market.js`, `invest-chart.js`, `invest.js`, `public/css/invest.css`: quote-only controller, visible subscription, ranges and chart exploration; project quotes onto holdings without mutating API state.
4. `work-equipment.js`, `app.js`: 30-second staff fallback, skip hidden/busy/recent sync/investment/Quay-owned refresh.
5. Run focused Node/Python tests, real socket/HTTP integration and mobile browser rendering. Package only explicit changes atop deployed hotfix1, verify all game files unchanged. Deploy silently, measure public market endpoint and API distribution. Report measured scope and remaining full-save debt.

No notification or new gameplay/economy changes. Authorized as part of active lag fix and user's explicit socket/chart instructions; no additional approval gate.
