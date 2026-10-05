# Hội chợ, quầy và kiểm tra lag lần hai

Trạng thái: đã sửa và kiểm chứng trên máy phát triển, **chưa deploy** theo yêu cầu gần nhất.

## Phạm vi và lựa chọn

- Đo lại hội chợ đông người, thao tác ngắm/phóng dao, cào vé; chỉ giữ tối ưu có số đo tốt và không mất thao tác.
- Sửa quầy gập doanh thu/thông tin khi refresh và đóng nhầm khi kéo từ trong bảng ra ngoài.
- Quầy hiển thị tối đa tám người từ hàng đợi/đơn và giao dịch vừa xác nhận. Khách vừa mua được ghi rõ; không tạo doanh thu giả để làm cảnh đông.
- Trò có thu phí: tổng chi tối đa 500 xu/lượt, giữ lựa chọn nhỏ. Trò đang miễn phí không đổi. Công an ở chiếu trong tăng tương đối 10%: 1,6% thành 1,76%.
- Người dùng xác nhận tăng số dao cần phóng và tốc độ bia. Lượt mới dùng số dao làm tròn lên từ 1,5 lần và tốc độ 1,5 lần; giữ xác suất kết quả server. Lượt đang chơi giữ cấu hình cũ.
- NPC thỉnh thoảng đề nghị lương gấp đôi mức hiện tại, trần 10.000; chủ lựa chọn đồng ý hoặc từ chối. Giữ sự kiện đang chờ và nhân viên người thật.
- Thêm lựa chọn sửa thiết bị, xử lý hàng hỏng, đào tạo và quảng bá; hiện chi phí/lợi ích, ghi sổ đúng, không âm tiền hoặc trừ hai lần khi thử lại.
- Giữ các bản sửa lag và thị trường theo giờ thực chưa phát hành từ lượt trước.

## Bằng chứng trước sửa

Production 05/10/2026 khoảng 10:52–10:55 giờ Việt Nam, đọc log và thống kê, không chạy giao dịch người chơi:

- Load 1,84 trên 9 CPU; RAM khả dụng khoảng 8 GB. PostgreSQL chủ yếu idle; mẫu có một idle-in-transaction, không thấy chờ khóa trong mẫu.
- 15 phút: 8.657 lệnh API, median 168 ms, p95 511 ms; 2.854 lượt state, median 203 ms, p95 722 ms. Không có 5xx trong mẫu. Bootstrap p95 1.264 ms.
- Một số lệnh trên bản lưu 3–4,3 MB mất 1,6–2,2 giây, phần compute 1,3–1,9 giây. Không thể kết luận tất cả lag do socket hoặc thiếu CPU.
- Chromium tái hiện được revenue details đóng khi state cập nhật và dialog đóng khi bắt đầu kéo bên trong rồi thả ngoài.
- Cào vé đọc vị trí canvas và cập nhật progress cho từng điểm pointer gộp; bảy điểm tạo bảy lượt đọc/ghi.

## Kiểm chứng dự kiến

1. So sánh before/after từ `output/baseline-fair-quay-pass2`, cùng viewport/DPR/throttle/crowd.
2. Test lịch vẽ, ẩn/đóng/mở, font và resize; giữ đủ điểm pointer và thời gian tap.
3. Browser regression quầy: details, caret/scroll, backdrop, 320/390/430 px; dữ liệu khách cũ/đóng/hết hàng.
4. PostgreSQL test phí, tổng cược, receipt/retry, vòng đang chơi, lương/chi phí/validation và số dư.
5. Kiểm tra độc lập thay đổi; không đổi thông báo hoặc rollout production.

## Root: kiểm tra bản lưu lớn

Phát hiện validator dựng lại danh sách toàn bộ 314 NPC cho từng bài đăng và bình luận. Đổi thành tra cứu dictionary có kiểm tra kiểu, giữ GameError cho dữ liệu lỗi. Không bỏ bất kỳ validation tiền, nghề, hay lịch sử nào.

Mẫu tổng hợp 1.200 bài, mỗi bài một bình luận, 15 lần: validate career median 14,51 → 6,905 ms. Đây chỉ là chi phí validator của mẫu, không phải tốc độ toàn API. Test duyệt tất cả NPC/player, dữ liệu sai và kiểm tra không mutate lịch sử đều qua.

## Kết quả chức năng và kiểm tra chéo

- Quầy: giữ disclosure, focus/caret và scroll; nhận đúng cử chỉ click ngoài bảng; dừng poll khi ẩn/đóng, không tạo nhiều poller khi mở lại. Một trăm refresh không đổi cảnh không gây vẽ lại canvas.
- Chân dung lấy từ khách đang chờ và hóa đơn quầy trong 90 giây gần nhất; tối đa tám. Tên nhân viên trên hóa đơn không dùng làm tên khách. Quầy đóng/hết hàng không diễn cảnh mua; khách đang chờ thật vẫn hiện.
- Chi phí mới: bảo dưỡng 240, bổ sung nguyên liệu 160 (nghề thực phẩm), đào tạo 200, quảng bá 180 xu; đều có lựa chọn miễn phí. Giữ ghi sổ, chống trừ lặp và kiểm tra số dư.
- Quote lương chờ được tính lại từ lương hiện tại trước hiển thị và duyệt, kể cả khi chủ sửa lương bằng tay. Trần 10.000 xu và lương ca đã chốt giữ nguyên.
- Max cược 500 được kiểm tra tổng cả vé/cược phụ. Net validator mở tới ±1e9 để thưởng hợp lệ không lỗi khi vượt ranh cũ; giới hạn mua lượt mới khi abs(net)+stake đạt 1e6 giữ nguyên. Không cắt thưởng đang chờ.
- Root chạy 287 test engine/storage/fastjson/authors: qua. Mẫu lớn kiểm tra dữ liệu không đổi. Các nhóm tiền/hội chợ có kiểm tra PostgreSQL ở nhánh và được chạy lại sau tích hợp.
- Root dùng browser + server thật và DB test tạm: 12 tổ hợp BC/XD/dao/cào × 320/390/430 px đều chọn được 500, không tràn ngang; mua dao 500 xác nhận server trả 11 dao. Không lỗi JS; DB schema thử đã dọn.
- Kiểm tra chéo tìm và sửa hai P2: quote lương cũ sau chỉnh lương thủ công; tên nhân viên bị dùng làm khách. Review độc lập phần hiệu năng không còn P1/P2.

## Kiểm chứng tích hợp cuối

- Root chạy lại 383 test Python thuộc hội chợ, cược, lương, chi phí, vận hành, PostgreSQL business, quầy, ledger và thị trường giờ thực: tất cả qua trong 69,127 giây. Nhóm engine/storage/fastjson/authors 287 test đã qua riêng trước đó; hai nhóm có phần giao nhau.
- 18 test Node qua; 653/653 tệp JavaScript kiểm tra cú pháp qua. Root chạy lại 13 kiểm tra browser quầy: tất cả qua, không lỗi JavaScript.
- So sánh hội chợ cuối bằng ABAB, Chromium 390×844 DPR thiết bị 2, CPU chậm 4 lần, 30 người giả lập di chuyển: trước 113/132 khung, sau 172/162 khung trong các cửa sổ khoảng sáu giây; trung bình +36% số khung, giảm 25% script CPU. Tổng thời gian main thread chỉ giảm khoảng 7%; vẫn còn chi phí paint và biến động máy thử. Báo cáo chính xác: `output/playwright/fair-ab-final/report.json`.
- Giữ cache vật tĩnh và giới hạn DPR canvas hội chợ dọc ở 1,5 (hơi mềm hơn); không giảm nhịp input/ngắm/phóng. Buồng ảnh giữ chất lượng ảnh chụp/xuất, chỉ cache preview. Cào vé xử lý đủ điểm gộp, đọc layout/ghi tiến độ một lần mỗi pointer event; ngón thứ hai không thay thế thao tác đang cào.
- Workflow browser buồng ảnh tạo đủ bốn ảnh và in; cào một phần rồi hiện kết quả; mở các trò khác và đóng hội chợ không để lại callback hội chợ. Không coi đây là đã chơi hết mọi ván hoặc kiểm chứng multiplayer ảnh thực tế. Bằng chứng và giới hạn: `output/fair-pass2-final.md`.
- Đo lại backend tổng hợp 1.024 đơn NPC bằng JSON Python chuẩn: median 268,95 → 66,73 ms; state, chuỗi lưu và 4.096 dòng archive bằng nhau. Đây là tối ưu ledger từ lượt trước được giữ và kiểm tra lại, không phải số đo production sau deploy.
- Hash hai nguồn Có gì mới trùng bản phát hành 1.7.14. Không thay code/config production, không phát thông báo. PostgreSQL thử được dừng sau kiểm tra; các schema browser tạm đã dọn.

Không khẳng định đã loại bỏ mọi lag trên production: server chưa nhận bản này; bản lưu lớn và paint trên máy yếu vẫn là giới hạn cần đo sau khi người dùng cho phép deploy.
