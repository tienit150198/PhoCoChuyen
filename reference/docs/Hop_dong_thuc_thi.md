# Hợp đồng thực thi cho đội phát triển

Đây là ranh giới thiết kế, chưa có backend/client triển khai trong gói.

## Lời nói và hành động

AI chỉ đề nghị action trong danh sách. Schema chỉ kiểm hình dạng, không đủ để cấp quyền hay xác nhận nghiệp vụ. Engine phải kiểm người chơi, nghề, đối tượng đích, phiên bản, nguồn chứng cứ, điều kiện riêng từng action và xác nhận cần thiết. Chi phí, số tiền, phần thưởng do luật tính từ dữ liệu có thẩm quyền; không nhận trực tiếp số tiền tùy ý từ chat.

## Giao dịch và chống lặp

Mã command duy nhất, cùng mã cùng kết quả. Thay đổi liên quan tiền/kho/đơn được chốt nguyên tử hoặc có cơ chế bù nhất quán. Phản hồi “đã xong” và hoạt ảnh hoàn thành chỉ phát sau khi trạng thái chốt. Payload ví dụ chỉ dùng ID giả để minh họa; cần fixture thật của engine trước khi chạy.

## Bằng chứng và ký ức

Gắn nguồn, phạm vi và thời điểm game. Tách verified_fact, player_claim và npc_inference. NPC không tự nâng lời nói thành sự thật hoặc đổi nguyên nhân của event sau lựa chọn. Không dùng lời chat, review hoặc văn bản ký ức như lệnh quản trị.

## Điều phối sự kiện

Điều kiện required_state trong events_96.json là tên điều kiện thiết kế, chưa có evaluator. Phải hiện thực từng điều kiện và handler trước khi bật event. selection_weight là trọng số ứng viên ban đầu, không phải tỷ lệ xác suất cuối cùng. Mỗi event cần fixture đủ vật thể/chứng cứ/NPC, nhánh hành động cụ thể và kiểm thử. Có cooldown theo ngày game; relaxed bỏ tense.

## Review

NPC review liên kết tương tác thật trong mô phỏng. Người thật chỉ có nhãn trải nghiệm được xác minh. Snapshot ghé không đồng nghĩa mua. Không trộn điểm NPC vào điểm người thật, không trừ tiền vì người thật chấm xấu. Giữ quyền trả lời, chặn, báo cáo và xem lại quyết định kiểm duyệt.

## Riêng tư và giới hạn

Không yêu cầu dữ liệu y tế, tài chính thật hoặc thông tin nhận diện thật để chơi. Hồ sơ nghề riêng không tự công khai trong ảnh hoặc snapshot. Tài liệu giả lập không dùng làm lời khuyên chuyên môn. Nhân vật hư cấu không được tự nhận là người chơi thật.
