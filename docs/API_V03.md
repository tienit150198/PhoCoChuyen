# API bổ sung v0.3

Xem `API.md` cho HTTP, cookie, CSRF, `request_id`, `expected_revision` và các action cũ. Cấu trúc request không đổi. `GET /api/bootstrap` thêm `content.experiences`. `GET /api/state` trả trạng thái công khai: mặt thẻ trí nhớ chưa lật và các thông tin riêng chưa được mở được lọc.

`GET /api/save/export` trả `save-v3`, schema 3, đầy đủ cho chủ phiên. Đây là bản sao lưu do người chơi sở hữu, không phải bằng chứng thành tích cạnh tranh.

## Router

`game.engine.apply_action` gọi `game.experiences.handle` cho các tiền tố `life_`, `lesson_`, `tour_`, `tea_`. Luật chạy ở server; UI chỉ gửi ý định. Giao dịch của lớp lưu trữ bảo đảm quay lại trạng thái trước nếu lệnh lỗi. Mọi thay đổi đều được kiểm tra mã yêu cầu và phiên bản.

| Action | Payload chính |
|---|---|
| `life_rename` | `name`: tên tối đa 36 ký tự |
| `life_mode` | `mode`: `calm` / `normal` / `festival`, chọn trước khi mở ca |
| `life_price` | `item`, `price`: chỉnh trước ca trong khoảng 75–125% giá mẫu; không sửa giá đã chốt của đơn cũ |
| `life_goal` / `life_badge` | `goal` / `badge`: nhận thưởng nếu đủ điều kiện và chưa nhận |
| `life_town` | `place`: `square` / `library` / `garden` / `studio` / `market` |
| `life_festival` | Không cần trường bổ sung; kiểm đủ mục tiêu ngày hội |
| `life_chapter` | `story`, `choice`: mã do nội dung định nghĩa |
| `life_reply_edit` | `post`, `index`, `text`: chỉ sửa bình luận của người chơi |
| `life_activity_start` | `spec`, `practice` (boolean), `replace` (boolean xác nhận đổi trò đang chơi) |
| `life_activity_assign` | `card`, `target` |
| `life_activity_step` / `life_activity_flip` | `card` |
| `life_activity_undo` / `life_activity_check` | Không cần trường bổ sung |
| `lesson_plan` | `task`, `steps`: `[demo, practice, reflect]` |
| `lesson_attendance` | `task`, `student`, `present` (boolean) |
| `lesson_teach` | `task`, `student`, `method`: `visual` / `hands` / `story` |
| `lesson_grade` | `task`, `student`, `correct` (boolean), `feedback` (mã trong nội dung) |
| `lesson_complete` | `task`, `confirm: true` |
| `tour_plan` | `task`, `route`: danh sách mã điểm |
| `tour_count` | `task`, `visitor` |
| `tour_depart` | `task`, `confirm: true` |
| `tour_locate` | `task`, `location: info` |
| `tour_tell` | `task`, `answer` |
| `tour_photo` | `task`, `object` |
| `tour_next` | `task` |
| `tour_complete` | `task`, `confirm: true` |
| `tea_prepare` | `item`, `qty`: 1–20, `confirm: true` |
| `tea_add` | `task`, `item` |
| `tea_config` | `task`, `size`, `sugar`, `ice` |
| `tea_check` / `tea_seal` | `task` |
| `tea_discard` / `tea_serve` | `task`, `confirm: true` |

Các ví dụ thực thi nằm trong `tests/test_experiences.py` và `public/js/experience-ui.js`. Không gộp nhiều lệnh thay đổi trong một request. Không cập nhật ví từ nội dung chat. Mở menu hoặc đọc thông tin không cần tăng lượt thao tác nghề.

## Lưu và chuyển phiên bản

Schema 3 bổ sung các nghề mới và mục `life` trong từng nghề. `life` chứa lô nguyên liệu, bảng giá, mục tiêu, trò nhỏ và kỷ lục, câu chuyện và mốc lựa chọn, sticker, huy hiệu, nơi đã ghé, tiền tip, chi phí và tổng kết.

Công việc mới chứa kế hoạch/điểm danh/phiếu phản hồi, hoặc tuyến/kiểm đoàn/bưu thiếp, hoặc ly/giá đã chốt. `experiences.validate` kiểm tra cấu trúc, mã định danh và các ràng buộc; nội dung bài học và điểm đến được lấy từ dữ liệu nguồn.

Chuyển từ schema 2 không truy thu chi phí; giữ nguyên mục vận hành đã có. Hỗ trợ đọc schema 1/2 từ cơ sở dữ liệu, nhập bản lưu v1/v2/v3 và chỉ xuất định dạng v3. Nhập bản lưu thay toàn bộ phiên hiện tại, không trộn hai bản chơi.

## Ranh giới bảo mật local

Không có API gian lận dành cho môi trường dev. Dữ liệu tình huống kiểm thử được tạo trong mã kiểm thử rồi nhập như bản lưu của chủ phiên. Người chơi có thể sửa bản sao lưu của mình; không dùng dữ liệu đó làm bằng chứng thành tích online.

Văn bản được escape trước khi hiển thị. HTTP trả 400 cho dữ liệu đầu vào sai và 409 khi phiên bản bị cũ; không ghi phần thay đổi đang dang dở. Xem thêm `SECURITY_AND_PRIVACY.md` trước khi cân nhắc công khai một server.
