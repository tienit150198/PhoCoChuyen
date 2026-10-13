# Tính lợi ích và hoàn vốn của mở rộng kinh doanh

Ngày 12/10/2026. Mục đích: kiểm tra học phí và quyền mở rộng trước khi quyết định thiết kế. Các con số dưới đây là mô hình có điều kiện dựa trên mã nguồn, không phải số liệu người chơi hoặc cam kết thu nhập.

## Căn cứ và cách tính

- Snapshot local `origin/main`: `3f3030531dd13235a3c48c48799a1e3433612b18`. Không truy cập hoặc thay đổi DB/server production.
- Hàm dự báo: `game/quay_business.py:income`; dùng cùng khoảng cách khách tới, thuế, lương và thưởng như sổ tiền thật.
- Mỗi kỳ vận hành là 10 phút thật. Bảng dùng bình quân một giờ thật trên toàn chu kỳ thị trường 24 giờ, gồm cả lúc suy thoái và hưng thịnh; không dùng doanh thu một giờ đông khách để suy ra cả ngày.
- Menu mặc định đầy đủ, giá bán mặc định, uy tín 100, nhân viên từ danh sách tuyển dụng seed 7 ở lương họ yêu cầu. Đủ số nhân viên theo mặt bằng. Không online, không thiết bị tăng khách/tăng lãi, không đồ trang trí, không bảo vệ trả phí.
- Luôn đủ hàng và vốn; không có tăng lương, nghỉ việc, sự cố/phạt, đơn chủ tự phục vụ hoặc khách là người chơi. Những yếu tố này làm kết quả thực tế khác mô hình.
- Lợi nhuận đã trừ giá vốn hàng bán, lương, thuê chỗ, điện, môi trường và thuế trên lãi; cộng thưởng lợi nhuận nhân viên hiện có. Không coi tiền góp quỹ là doanh thu, không tính hàng tồn chưa bán thành chi phí hàng đã bán.
- Vốn chuẩn bị minh họa = giá mặt bằng + tiền hàng đủ khoảng một giờ bình quân (làm tròn nguyên từng món) + dự phòng một giờ chi phí cố định. Phần quỹ khởi đầu có sẵn trong giá mở quầy được thay bằng mức dự phòng này, không cộng hai lần.
- Thời gian thu hồi tiền bỏ ra = đầu tư bổ sung / lợi nhuận tăng thêm. Khi nâng cấp, trừ lợi nhuận của quầy cũ, không lấy toàn bộ lợi nhuận tiệm mới làm phần tăng thêm. Cách tính không khấu trừ giá trị sang nhượng, không mô phỏng thay đổi công suất trong thời gian tuyển người/nhập hàng.

Đã chạy riêng sổ tiền thật 24 giờ, tắt các sự kiện để khớp giả định. Lãi trà sữa thu được: xe đẩy 5.778 xu; sạp 12.437 xu; ki-ốt 37.266 xu. Dự báo tương ứng 5.784 / 12.441 / 37.266 xu; sai khác dưới 0,11%, do thời điểm đơn hàng và làm tròn. Đây là kiểm tra mô hình kinh tế, không phải kiểm thử tính năng chứng chỉ chưa triển khai.

## Kinh tế một cơ sở trà sữa

| Khoản | Xe đẩy | Sạp | Ki-ốt |
|---|---:|---:|---:|
| Nhân viên | 1 | 2 | 3 |
| Giá mặt bằng | 800 | 4.000 | 15.000 |
| Giá mở theo game, gồm quỹ khởi đầu | 851 | 4.072 | 15.111 |
| Tiền hàng dự trữ khoảng 1 giờ | 244 | 549 | 1.403 |
| Chi phí cố định mỗi giờ | 144 | 384 | 924 |
| Tổng vốn chuẩn bị trong mô hình, chưa học phí | 1.188 | 4.933 | 17.327 |
| Doanh thu bình quân/giờ | 479 | 1.164 | 3.081 |
| Toàn bộ chi phí hàng bán/vận hành/thuế mỗi giờ | 365 | 917 | 2.342 |
| Thưởng lợi nhuận nhân viên bình quân/giờ | 126 | 272 | 813 |
| Lãi sau chi phí, gồm thưởng, bình quân/giờ | **241** | **518** | **1.553** |

Các cột làm tròn độc lập nên phép cộng từ số hiển thị có thể lệch 1 xu. Mô hình dùng số chưa làm tròn khi tính hoàn vốn.

Lợi ích của mở thêm quầy là có thêm luồng bán hàng NPC chạy song song. Công thức hiện tại tính khách riêng cho từng quầy; chưa trừ khách giữa các quầy cùng chủ. Hai xe đẩy tương đương trong điều kiện trên lời khoảng 482 xu/giờ, ba xe khoảng 723 xu/giờ. Mỗi quầy vẫn cần người, hàng và vốn riêng, nên không phải mở xong là tự sinh tiền vô điều kiện.

Một ki-ốt cho lợi nhuận khoảng 6,44 xe đẩy trong một địa điểm quản lý. Đổi lại vốn mặt bằng cao hơn nhiều. Thị trường chung ảnh hưởng tất cả quầy cùng lúc; mở nhiều cơ sở không tự phân tán rủi ro suy thoái.

## Học phí thực trả và hoàn vốn

Giá cơ sở đề xuất 500 / 2.000 / 5.000 đi qua chỉ số giá hiện tại thành **550 / 2.200 / 5.500 xu**. Tổng từ chưa có giấy đến cấp 3 là 8.250 xu nếu đậu ngay cả ba cấp.

| Phương án theo bản kế hoạch trước | Tiền phải chuẩn bị thêm | Lãi tăng thêm/giờ | Thời gian thu hồi tiền |
|---|---:|---:|---:|
| Mở xe đẩy đầu, không học phí | 1.188 | 241 | 4,9 giờ |
| Học cấp 1, mở xe đẩy thứ hai | 1.738 | 241 | 7,2 giờ |
| Học cấp 1, nâng xe đẩy lên sạp | 4.295 | 277 | 15,5 giờ |
| Đã có cấp 1, học cấp 2, nâng sạp lên ki-ốt | 14.594 | 1.034 | 14,1 giờ |
| Đã có cấp 2, học cấp 3, mở xe đẩy thứ ba | 6.688 | 241 | 27,7 giờ |
| Mới có cấp 1, học tiếp cấp 2 và 3, mở xe đẩy thứ ba | 8.888 | 241 | 36,9 giờ |
| Đã có cấp 2, học cấp 3, mở thêm ki-ốt thứ ba | 22.827 | 1.553 | 14,7 giờ |
| Đã có cấp 2, học cấp 3 rồi mở thêm ba xe đẩy | 9.064 | 723 | 12,5 giờ |

“Giờ” là thời gian thực mà cơ sở vận hành đủ điều kiện trong thị trường theo mô hình, không phải số giờ người chơi phải ngồi bấm. Hết hàng, hết vốn hoặc thiếu nhân viên làm kéo dài thời gian. Dự phòng hàng một giờ bình quân có thể hết sớm hơn trong giai đoạn hưng thịnh.

Học phí riêng cũng cần nhìn theo lợi ích mở rộng: 550 xu cấp 1 tương đương khoảng 2,3 giờ lãi của một xe đẩy bổ sung; 2.200 xu cấp 2 tương đương 2,1 giờ phần lãi tăng thêm khi nâng sạp đủ người lên ki-ốt đủ người; 5.500 xu cấp 3 tương đương 22,8 giờ lãi chỉ một xe đẩy mới, nhưng khoảng 3,5 giờ lãi một ki-ốt mới. Đây là chi phí tiếp cận quyền mới, không phải tiền giấy chứng nhận tự tạo ra.

## Các điểm chưa cân đối

1. **Chứng chỉ trong đề xuất cũ chưa tự làm tiệm lời hơn.** Chúng chỉ mở quyền kinh doanh vốn đã tồn tại trong code. Học tăng hiểu biết và cấp giấy, nhưng không có khoản thưởng, giảm chi phí hoặc tự động hóa mới được triển khai. Không thể quảng cáo tăng thu nhập trực tiếp nhờ tấm giấy.
2. **Sạp chưa hấp dẫn về hiệu quả vốn.** Hai xe đẩy cần 2.376 xu vốn chuẩn bị và lời 482 xu/giờ; một sạp cần 4.933 xu và lời 518 xu/giờ. Sạp chỉ hơn 7,5% lãi nhưng hơn gấp đôi vốn. Điểm lợi hiện tại là quản một nơi thay vì hai. Cả hai phương án đều cần cấp 1 theo đề xuất nên học phí không xóa được chênh lệch.
3. **Nâng cấp mà không tuyển đủ người có thể tệ đi.** Trà sữa ở sạp chỉ một người còn khoảng 95 xu/giờ; ki-ốt một người lỗ khoảng 93 xu/giờ; ki-ốt hai người lời khoảng 680 xu/giờ. Không nên hiển thị dự báo với ba nhân viên nếu người chơi mới có một người.
4. **Giáo trình cấp 3 bị áp dụng quá sớm cho người bán nhỏ.** Mở thêm một xe đẩy phải thu hồi gần 28–37 giờ, trong khi mở thêm ki-ốt khoảng 15 giờ. Một mức phí cao gắn với mọi “cơ sở thứ ba” không hợp lý như nhau.
5. **Ngành hàng khác nhau đáng kể.** Với đủ người, lãi bình quân của tám ngành trong mô hình dao động xe đẩy khoảng 129–383, sạp 246–846, ki-ốt 819–2.389 xu/giờ. Trà sữa chỉ là ví dụ nhất quán để so sánh, không đại diện cho lợi nhuận tất cả ngành.
6. **Không cộng thưởng tiền tùy tiện.** Game đã có thưởng 110% phần lãi dương của đơn nhân viên và thiết bị nâng thu nhập. Cần tính tổng các hệ số trước khi thêm ưu đãi chứng chỉ. Các mức giảm giá vốn 5/10/15% đã được thử như phép tính đối chứng trong JSON, không phải quyền lợi được đề xuất hay chốt: ngành giá vốn cao sẽ hưởng lợi khác rất nhiều.

## Khuyến nghị sau phép tính

- Giữ 500 xu cơ sở cho cấp 1 làm mức thử nghiệm: mở quầy nhỏ thứ hai có khoảng thu hồi tiền 7,2 giờ trong ví dụ. Bài học và màn dự toán phải chỉ ra cả tiền hàng và lương, không chỉ giá mặt bằng.
- Cấp 2 giá cơ sở 2.000 có thể gắn với ki-ốt: tăng công suất đủ lớn nếu đủ nhân viên. Quyền lợi phải đi kèm dự toán theo số nhân viên thực, so sánh lợi nhuận trước/sau và cảnh báo thiếu vốn, tận dụng hàm thu nhập có sẵn. Chưa cần cộng thêm tiền thưởng chỉ vì có giấy.
- **Rút đề xuất bắt cấp 3 cho mọi cơ sở thứ ba.** Mức cơ sở 5.000 chỉ nên gắn với mở rộng chuỗi lớn, ví dụ ki-ốt thứ ba, hoặc gói công cụ quản lý tạo ích lợi rõ ràng. Ngưỡng chính xác và quyền của chuỗi quầy nhỏ cần chốt trong thiết kế tiếp; chưa dùng quy tắc cũ để triển khai.
- Nếu cấp 3 bán lợi ích quản lý, các ứng viên là nhập hàng theo mức tồn và hạn mức quỹ do chủ đặt, tổng quan lãi từng cơ sở, cảnh báo sắp hết hàng. Đây là tính năng mới cần làm và kiểm chứng; không tính thành lợi nhuận chắc chắn trong các bảng trên. Nhập lại theo lần trước và thao tác quản lý chung đã có, không tính chúng thành quyền mới.
- Trước khi chốt điều kiện sạp, cần so sánh tăng giá trị thật của sạp (công suất hoặc giảm chi phí có kiểm soát) với vai trò chỉ là mặt bằng ít phải quản lý hơn. Không tăng học phí hoặc khóa nhiều xe đẩy chỉ để che chênh lệch hiệu quả vốn.
- Hiển thị lợi ích mỗi lần mở rộng bằng tiền tăng thêm/giờ, vốn hàng/lương, thời gian thu hồi dự kiến và điều kiện đạt dự báo; hiển thị học phí theo giá đã điều chỉnh. Không chỉ ghi “được mở thêm quầy”.

## Tái lập

Cập nhật theo ý kiến người dùng ngày 12/10/2026: dùng công an kiểm tra chủ nhiều quầy để yêu cầu học có trả phí, kể cả chủ cũ. Học phí lúc này còn là chi phí duy trì quyền vận hành quy mô hiện có; không gọi đó là khoản đầu tư tự tạo thêm lợi nhuận. Đề xuất từ ba quầy nhận thông báo và thời hạn bổ sung; cấp học theo loại/quy mô, từ ba ki-ốt cần cấp 3. Ngưỡng chuỗi xe đẩy/sạp lớn và chi phí khi hạn chế cần tính tiếp. Chi tiết tại [kế hoạch](2026-10-12-business-progression.md#5-người-chơi-và-bản-lưu-cũ). Các phép tính và giới hạn mô hình phía trên vẫn giữ nguyên.

Các file nằm tại `D:/projects/Mot_ngay_lam_nghe/_business_balance_20261012/`:

- `source-revision.txt` và `source/game/`: snapshot mã nguồn dùng tính.
- `calculate.py`, `results.json`: 48 cấu hình ngành/mặt bằng/số nhân viên; dự báo thị trường bình quân và giờ suy thoái mẫu; các phép tính giảm giá vốn chỉ để khảo sát độ nhạy.
- `verify_ledger.py`, `ledger-verification.json`: chạy sổ tiền thật trong giả định được kiểm soát.
- `payback.json`: vốn chuẩn bị và các phương án hoàn vốn đã nêu.

Lệnh: `python _business_balance_20261012/calculate.py` và `python _business_balance_20261012/verify_ledger.py` từ workspace gốc. Cả hai đã chạy thành công. Chưa triển khai bất kỳ học phí hoặc quyền lợi chứng chỉ mới nào.
