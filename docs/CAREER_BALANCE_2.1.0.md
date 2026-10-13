# Cân bằng nghề và lộ trình 2.1.0

## Bốn nghề mới

| Nghề | Quy trình | Thu nhập trực tiếp | Mốc dài hạn |
|---|---|---|---|
| Xưởng vẽ | Lập phương án, vẽ 4–6 lớp theo thứ tự, duyệt ba tiêu chí, giao đúng người | Lãi gốc khoảng 22–26 xu/tranh sau vật tư | 140 tranh tốt, 35 ngày hoạt động và tranh tốt được tạo từ ngày 45 |
| Luật sư | Đối chiếu hồ sơ, chứng cứ và xử lý tình huống hư cấu | Lương hợp đồng 50–75 xu, thưởng việc gốc 4–7 xu | 120 việc tốt, 30 ngày hoạt động và việc tốt được tạo từ ngày 40 |
| Giặt ủi | Kiểm đồ, phân loại, xử lý vết bẩn, giặt, sấy, hoàn thiện, kiểm và trả | Lãi gốc khoảng 16–24 xu/đơn; vật tư trừ một lần | 100 việc tốt/30 ngày, rồi 180 việc tốt/45 ngày |
| Bưu điện | Kiểm, cân, định tuyến, ghi cước, nhãn và bàn giao | Lương 50–65 xu, thưởng việc sạch 5/6/9 xu; cước không vào ví | 180 việc tốt, 45 ngày hoạt động, 12 đợt bưu gửi nâng cao |

Nội dung có nhiều biến thể từ ngày 1/4/10/20/40 trở đi. Bưu điện ngày muộn có lô 2–3 kiện. Mức tiền trên là trước các hệ thống thưởng chung, không phải cam kết tổng tiền thực nhận.

Mô phỏng toàn ca không nhân viên ở ngày 1/10/40 cho lãi sau dự phòng chi phí lần lượt: vẽ 61/99/94, giặt 48/55/54, luật 92/97/98, bưu điện 85/86/86 xu. Người làm hoàn hảo mọi việc được hệ thống xếp, không mua nâng cấp hoặc nhận trợ cấp; nghề nhân viên dùng mức lương cao nhất hợp đồng và đã qua thử việc. Số liệu bao gồm thu/chi chung, chi phí thuê và thuế dồn tích; mỗi mốc ngày là mẫu độc lập.

Mô phỏng đúng bốn đơn nhân viên tự làm mỗi ngày tăng các giá trị tương ứng lên vẽ 125/163/158, giặt 101/109/108, luật 155/160/162, bưu điện 136/137/138. Lương nhân viên trừ theo từng đơn đúng đồng hồ máy chủ. Chuỗi bảy ngày có tuyển người, trả các hóa đơn thật: vẽ +862, giặt +662 xu. Đơn tự động không cộng tay nghề tự làm của chủ.

## Thăng bậc và tay nghề

Thang thông thường lên bậc 7. Các danh hiệu cũ giữ nguyên; công an giữ quy trình cấp hàm, bổ nhiệm và ghế. Chủ tiệm bậc 5/6/7 thưởng 15/18/21% với trần 42/50/60 xu mỗi ngày. Nhân viên tăng lương cơ bản 66/77/88%, thương lượng tối đa thêm 12 điểm phần trăm. Quy mô và trần thưởng đội không tăng theo các bậc này.

Tay nghề là nhánh riêng, tính từ các việc sau cập nhật; không suy diễn số ngày hoạt động quá khứ từ việc mở cửa. Ba mốc đòi hỏi đồng thời 40/120/260 việc không lỗi, 15/40/75 ngày chuẩn, cấp XP 20/45/90. Một ngày chuẩn có ít nhất ba việc không lỗi và ít nhất 80% số việc hoàn thành trong ngày không lỗi; chỉ việc tự làm được tạo cùng ngày mới tính. Thi bốn câu cần 7/8; trượt phải tích thêm ba ngày chuẩn sau khi nộp bài.

Mô phỏng 54 nghề, hai nhịp mỗi nghề: ba việc sạch/ngày đạt bậc vào ngày 19/44/89; bốn việc sạch/ngày đạt ngày 15/40/75. Trong 90 ngày, thưởng tay nghề lần lượt 710/870 xu khi mọi ngày đều còn lượt nhận thu nhập và thi đạt ngay sau khép ca đủ điều kiện. Thưởng không truy lĩnh cho ngày khép trước lúc có danh hiệu.

Thưởng cố định 6/12/20 xu/ngày chuẩn theo bậc, một lần mỗi ngày nghề, cần còn lượt trả thu nhập. Không nhân tiếp bằng x3 hoặc lương. Nghỉ việc/đổi hợp đồng giữ danh hiệu; đặt lại nghề chủ động sẽ đặt lại tiến trình. Bài sát hạch lưu sau từng câu, không gửi đáp án hoặc điểm lựa chọn trong phản hồi công khai.

Bằng chứng tái lập: `tests/creative_civic_economy.py`, `tests/career_mastery_simulation.py`, `tests/test_mastery_engine.py`, `scripts/browser_creative_civic.py`, `scripts/browser_career_mastery.py`. Báo cáo JSON và ảnh kiểm tra nằm trong output cục bộ.
