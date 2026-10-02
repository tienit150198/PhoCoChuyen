# Học và thực hành kế toán

Hai khóa dùng chung một khu học trong menu **Học kế toán**. [Chương trình chi tiết](ACCOUNTING_CURRICULUM.md) mô tả 24 bài cơ bản và 60 bài doanh nghiệp, 252 bài tập và 84 câu trong ngân hàng thi.

## Tiến trình

Mỗi bài có mục tiêu, phần giảng, ví dụ, nguồn và 3 bài tập. Mở bài chỉ đánh dấu đã đọc; làm đúng đủ bài tập mới hoàn thành. Có 7 dạng câu hỏi. Đáp án chưa giải và đáp án đang thi không xuất hiện trong API công khai.

Thi cơ bản gồm 24 câu; thi doanh nghiệp rút 40 câu từ 60 câu, phủ đủ 15 chương. Đạt từ 80/100. Khóa doanh nghiệp yêu cầu chứng nhận cơ bản và hoàn thành 60 bài. Có thể thi lại miễn phí; bài chữa hiện sau khi nộp toàn bộ đề. Đề gắn với người chơi/lần thi, giữ qua tải lại.

Chứng nhận là **chứng nhận hoàn thành trong Phố Có Chuyện**. Có tên người chơi, điểm, ngày và số chứng nhận, có thể lưu bản HTML để in. Chứng nhận doanh nghiệp tăng lương nghề `corp_accounting` lên 3 lần; giữ lương hợp đồng làm căn cứ, áp dụng cả mức thử việc và không cộng dồn khi thi lại. Những nghề khác giữ hệ số riêng.

## Doanh nghiệp thực hành

Công ty CP Mây Tre Xanh là doanh nghiệp giả lập sản xuất, thương mại và dịch vụ, ghi sổ bằng VND trong 12 kỳ tháng năm 2026. Có 630 bước chứng từ/bút toán/khóa sổ/báo cáo. Nghĩa vụ thuế, lương, giá xuất kho và tỷ giá được hồ sơ cung cấp; TT99 hướng dẫn kế toán, không tự xác định nghĩa vụ thuế.

Người học mở chứng từ gốc trước khi ghi; đáp án đúng mới cập nhật sổ một lần. Bộ sổ gồm góp vốn, mua bán, VAT, tiền và công nợ theo đối tượng, vay/lãi, sản xuất/giá thành, TSCĐ/khấu hao, chi phí chờ phân bổ, dịch vụ nhiều kỳ, tiền gửi kỳ hạn/dự thu/đáo hạn, ngoại tệ, dự phòng, thuế hiện hành/hoãn lại, cổ tức và kết chuyển.

Số dư cuối tháng chuyển sang tháng sau. Tất cả máy mới, bảo hiểm, dịch vụ, tiền gửi và hóa đơn ngoại tệ tiếp tục được theo dõi các tháng sau. Có nhật ký kỳ hiện tại/kỳ trước, bảng cân đối gồm số đầu kỳ/phát sinh/cuối kỳ, sổ công nợ và bảng từng tài sản/hợp đồng.

Mẫu báo cáo lấy mã và nhãn từ [TT99 chính thức trên Công báo](https://congbao.chinhphu.vn/van-ban/thong-tu-so-99-2025-tt-btc-46529.htm): B01 có 126 dòng, B02 có 21, B03 trực tiếp có 27, B09 có 107 đề mục. Chỉ tiêu không phát sinh bằng 0; EPS không áp dụng với hồ sơ doanh nghiệp chưa đại chúng. Báo cáo tháng so sánh tháng trước, tháng 1 dùng số dư đầu năm cho B01; không có số kết quả năm 2025 để so sánh.

Hoàn thành sổ và 4 báo cáo mới nhận lương ca thực hành, một lần mỗi kỳ. Trong chế độ Hành trình, lương về ví cá nhân theo cơ chế lương hiện có, không khép ca nghề đang làm hay đẩy ngày sống. Ngoài Hành trình, lương theo quỹ nghề hiện có.

## Dữ liệu và kiểm tra

Bản lưu cũ tự thêm trạng thái học rỗng. Tiến độ bài, bài thi và chứng nhận được kiểm tra bằng bộ đề gốc. Kỳ sau cần hồ sơ bài làm đã hoàn thành của tất cả kỳ trước. Định khoản chỉ nhận 3 trường tài khoản Nợ/Có/số tiền, tránh dữ liệu phụ không giới hạn. Không thể nhận lại lương đã trả bằng gửi lại lệnh.

Kiểm thử bao phủ toàn bộ đáp án biên soạn, học/thi lại/chứng nhận, lương thường và thử việc, ví cá nhân, bản lưu cũ và dữ liệu sửa sai, đầy đủ 12 tháng, tiền không âm ở từng bước, cân đối sổ/B01/B03 và giao diện 7 dạng bài.

```text
python -m unittest tests.test_accounting_content tests.test_accounting_school tests.test_accounting_company tests.test_accounting_ui
node scripts/check_js.mjs
python scripts/run_checks.py
```

Kiểm tra ngày 02/10/2026 trên checkout chính: 24 kiểm thử riêng cho kế toán đều đạt. Trình duyệt Chrome đã thử trả lời sai rồi sửa đúng, hoàn thành bài, nộp câu thi và tiếp tục sau tải lại, hủy thi lại mà giữ chứng nhận, tải chứng nhận HTML, mở chứng từ và ghi bút toán, hoàn thành B09, nhận lương 300 xu từ hợp đồng 100 xu, khóa nút lĩnh lại và mở tháng 2. Ví tăng từ 60 lên 360 xu; nghề và ngày đang chơi được giữ. Dữ liệu khóa học và các bước giữa kỳ được chuẩn bị bằng reducer thật trong SQLite riêng để kiểm tra các điểm cuối của luồng; không sửa bản lưu người chơi thật. Đã xem bố cục ở 390×844 và 1280×900, không có lỗi console trong lượt kiểm tra cuối.

Kiểm tra cú pháp JavaScript: **701/701 tệp đạt**. `git diff --check` không báo lỗi.

Kiểm thử toàn dự án bằng Python 3.12.14 và WebSocket 17.1: **4.560 bài, 4.507 đạt, 49 bỏ qua, 2 thất bại và 2 lỗi**. Báo cáo thực tế nằm ở `artifacts/python-test-report.json` và `artifacts/python-tests.log`. Bốn lỗi ngoài phần kế toán đã được đối chiếu với mã gốc commit `4ae0d8d`:

| Bài kiểm thử | Kết quả đối chiếu mã gốc |
|---|---|
| `AccountStoreTests.test_old_database_gains_tables_and_sessions_keep_working` | Tái hiện lỗi Windows không xóa được SQLite đang mở ở bước dọn test. |
| `LoadsTests.test_what_orjson_refuses_is_parsed_by_json` | Tái hiện `RecursionError` khi bộ giải mã JSON đọc mảng lồng sâu trong runtime này. |
| `SharedLimitTests.test_limits_db_follows_game_db` | Tái hiện khác biệt đường dẫn Windows với chuỗi POSIX mà test mong đợi. |
| `HTTPv4Tests.test_ai_feedback_scripted_without_consent` | Mã gốc đã đặt `aiConsent=True`. Test đạt khi AI không được cấu hình, nhưng thất bại giống checkout có kế toán khi giả lập AI khả dụng và câu trả lời hợp lệ; việc đối chiếu dùng mock, không gọi dịch vụ AI thật. |

Log đối chiếu và ảnh trình duyệt được giữ ở `artifacts/accounting/`. Các lỗi trên không được sửa trong phạm vi thêm chương trình kế toán.

Đây là chương trình và hồ sơ học tập có phạm vi rõ. Bài học phủ rộng các nhóm TT99, nhưng một doanh nghiệp giả lập không phát sinh mọi nghiệp vụ, ngành nghề hoặc ngoại lệ pháp lý. Báo cáo và chứng nhận trong game không thay hồ sơ thực tế, kiểm toán hay chứng chỉ hành nghề.
