# Lộ trình nghề: nghề mới, nâng cấp nghề cũ, khung chung

Ngày lập: 23/10/2026, dựa trên mã nguồn `origin/main` bản 2.5.9.1 (72 nghề đang có trong game).

Chủ game yêu cầu:

> "các nghề mới thì lên hướng triển khai, làm giao diện dễ chơi, như mấy game 'quán net cỏ', ... các nghề khác để mà học hỏi UI
> cho đẹp, với các cơ chế phát triển của nghề, mở rộng sau này, rồi mấy cơ chế ảnh hưởng hay gặp của nghề nữa có hết nhé"
>
> "riêng roadmap các nghề thì mở rộng ra thêm cho nhiều nghề khác nữa nhé, các nghề hiện tại nữa"

Tài liệu gồm 5 phần:

| Phần | Nội dung | Ai cần đọc |
|---|---|---|
| [0. Tóm tắt](#0-tóm-tắt-một-trang) | Một trang: làm gì trước, làm gì sau | Chủ game |
| [1. Hiện trạng](#1-hiện-trạng-game-đang-có-gì) | 72 nghề hiện có và các hệ thống dùng chung | Chủ game, dev |
| [2. Học từ game khác](#2-học-từ-các-game-tham-khảo) | Mượn gì về giao diện, cơ chế phát triển, sự cố | Chủ game, thiết kế |
| [A. Khung chung](#a-khung-chung-cho-mọi-nghề) | Bộ giao diện, cây phát triển, sự cố "vui là chính", nối với hệ thống có sẵn | Dev, thiết kế |
| [B. Nghề mới](#b-nghề-mới) | 10 nghề người chơi xin và 16 nghề đề xuất thêm, mỗi nghề một thẻ | Chủ game, dev |
| [C. Nghề hiện có](#c-nâng-cấp-các-nghề-hiện-có) | Góp ý đang chờ và kế hoạch nâng cấp cho từng nghề | Chủ game, dev |
| [D. Các đợt triển khai](#d-các-đợt-triển-khai) | Đợt 0 → Đợt 4, rồi các việc để sau (Ma sói) | Chủ game |
| [Phụ lục](#phụ-lục) | Sự cố theo ngành, lỗi phát hiện khi khảo sát, ghi chú kỹ thuật | Dev |

Quy ước trong tài liệu:

- **Công sức:** S = dùng lại bộ bước sẵn có, khoảng 1 phiên làm. M = có màn riêng và 1 cơ chế mới, 2–4 phiên. L = cần hệ
  thống mới (sơ đồ phòng chạy theo thời gian, nhiều người chơi cùng lúc…), 1–2 tuần.
- **Ưu tiên:** P1 (làm ngay) → P4 (để sau). Xếp theo số lượt người chơi xin nhân với độ dễ làm.
- **xu:** tiền trong game. Mức thu nhập ghi trong tài liệu là **mức gốc**, chưa cộng các khoản thưởng chung (📈 +20–50 % theo
  tài sản, 💰 tăng tiền công, 🔥 x3 trong tuần, ⏱️ tăng ca, thưởng tay nghề).
- **#số:** mã góp ý của người chơi.

---

## 0. Tóm tắt một trang

**Điều người chơi xin nhiều nhất:** trang điểm (4 lượt), bác sĩ/phòng khám (4), ăn vặt vỉa hè (3), quán net (2), tiệm điện
thoại – laptop (2). Mỗi nghề sau được xin một lần: chủ nhà trọ, chủ tịch tập đoàn, ủy ban phường, MC, hiệu sách cũ.

**Nguyên tắc chung (giữ như các nghề đã làm):**

1. Mỗi nghề là **việc làm bằng tay**: người chơi tự làm từng bước, máy chủ chấm. Không có chữ "meta", không giảng giải dài.
2. **Dễ chơi trên điện thoại**: tối đa 25 chữ trên màn làm việc, một nút chính ở thanh dưới, chạm ≥ 44 px. Mọi nghề mới dùng
   chung một bộ giao diện (Phần A1).
3. **Vui là chính**: sự kiện tốt nhiều hơn sự kiện xấu. Chuyện xấu luôn được báo trước, luôn có cách phòng, có mức trần
   thiệt hại, và luôn có một kết cục nhẹ nhàng. Phần thưởng phải **nhìn thấy được** (pháo hoa, tiền bay vào két, sao tăng).
4. **Phát triển rõ ràng theo 5 tầng**: lên cấp → mở đồ nghề/món mới → mở rộng mặt bằng → thuê người → mở chi nhánh, chuỗi.
5. Mỗi nghề có ít nhất **một dịch vụ cho người chơi khác** qua 🛎️ Phố dịch vụ (như sửa xe, thú y, chụp ảnh đang có).

**Thứ tự đề xuất (chi tiết ở [Phần D](#d-các-đợt-triển-khai)):**

| Đợt | Nội dung chính | Vì sao |
|---|---|---|
| **0** | Khung chung (sơ đồ tiệm, màn tổng kết ngày mới, bảng sự kiện vui) + 5 góp ý cũ còn treo (#157/#158, #311, #355, #373, #320) | Nghề mới làm nhanh hơn và đều tay hơn; trả nợ góp ý cũ |
| **1** | 🍢 Ăn vặt vỉa hè, 💄 Trang điểm & phụ kiện, 🩺 Phòng khám bác sĩ, 📱 Tiệm điện thoại – laptop | Được xin nhiều nhất, dùng lại được nhiều thứ đã có |
| **2** | 🖥️ Quán net, 🏘️ Chủ nhà trọ, 🎙️ MC, 📚 Hiệu sách cũ & CLB | Còn lại trong danh sách người chơi xin |
| **3** | 🏛️ Ủy ban phường, 🏢 Chủ tịch tập đoàn, 🥖 Bánh mì, 🚿 Rửa xe, 🅿️ Giữ xe, 🛺 Xe ôm/taxi, 🔌 Điện nước, 🧵 May đo | Nghề phố phường gần gũi; chủ tịch là đích đến cho người chơi giàu |
| **4** | 💆 Spa, 🏋️ Gym, 🎤 Karaoke, 🚒 PCCC, 📐 Nội thất, 📰 Nhà báo, 🎮 Studio game, 🐟 Ao cá, 🔑 Thợ khóa, 👓 Cắt kính | Mở rộng phố, nối với nhà, tiệm và tin tức |
| Sau | 🐺 Ma sói (đã hoãn theo ý chủ game), nha khoa, các chuỗi liên nghề | |

Mỗi đợt nâng cấp thêm 6–10 nghề cũ (Phần C). Mỗi bản phát hành có popup "Có gì mới" và được deploy trong khung 04:00–05:00.

---

## 1. Hiện trạng: game đang có gì

### 1.1. 72 nghề hiện có

Kiểu nghề: **Chủ** = người chơi làm chủ tiệm (có quỹ nghề, kho, nhân viên). **Lương** = người chơi đi làm thuê (nộp hồ sơ,
phỏng vấn, thử việc, nhận lương). **Tổ** = làm theo tổ/gia đình trả công.

| Nhóm | Nghề (id) | Kiểu | Vòng chơi hiện tại (tóm tắt) |
|---|---|---|---|
| **Ăn uống** | 🧋 Trà sữa (milk_tea) | Chủ | Chọn ly → trà → siro → topping → đá, đường → dán nắp → giao; khách quen, bất ngờ ở quầy |
| | 🥐 Bánh & cà phê (cafe_bakery) | Chủ | Xay, định lượng → chiết 25–30 giây → sữa/đá → vẽ hình → giao; lò nướng mẻ; máy pha và lò chọn tốc độ 1×/2×/4× |
| | 🍜 Quán mì cay (restaurant) | Chủ | Tô → thả mì → nước dùng → topping → sốt → giao; sổ món quen, bàn nhiều tô |
| | 🍲 Phở (pho) | Chủ | Giữ lửa, hớt bọt, nêm → trụng bánh 3–4 lượt → xếp thịt → chan nước |
| | 🍛 Cơm tấm (com) | Chủ | Nấu nồi tấm, nồi trắng → dĩa/hộp → xới → gắp món → mỡ hành, nước mắm |
| | 🧊 Trà đá vỉa hè (tra_da) | Chủ | Pha chè, đập đá, rót, thu tiền; sổ ghi nợ chú xe ôm; xe trật tự tới thì dẹp ghế |
| | 🍦 Kem (ice_cream) | Chủ | Chỉnh nhiệt tủ → múc từng viên theo cân → topping |
| | 🍳 Nấu cơm gia đình (naucom) | Tổ | Chọn thực đơn hợp cả nhà trong tiền chợ → đi chợ → nấu |
| | 🏫 Căn tin trường (canteen) | Chủ | Chạm món vào khay trước tiếng trống; dị ứng, ngày chay |
| | 🎉 Nhà hàng tiệc (banquet) | Lương | Ca bếp (phụ bếp → đầu bếp) hoặc ca sảnh sự kiện theo phiếu |
| **Bán lẻ** | 🧸 Mẹ & bé (mother_baby) | Chủ | Chọn quà, gói giấy, nơ, thiệp; đọc nhãn tuổi; đổi trả |
| | 💊 Nhà thuốc (pharmacy) | Chủ | Đọc phiếu, kiểm lô, lấy đúng mã hộp; bàn giấy tờ |
| | 🛒 Tạp hóa (grocery) | Chủ | Quét, cân → khuyến mãi → kiểm tuổi → thối tiền; sổ nợ; đơn sỉ có cọc |
| | 💐 Tiệm hoa (florist) | Chủ | Hỏi dịp → chọn hoa theo ý nghĩa → sơ chế → bó/cắm → gói, thiệp → giao |
| | 👕 Shop quần áo (clothing) | Chủ | Nghe khách → chọn size, màu → mời thử → thối tiền; sửa đồ (lai quần, bóp eo) |
| | 🐠 Shop thú cưng (pet_shop) | Chủ | Hỏi kỹ → chọn đồ cho bé → quét → thối tiền |
| | 🍉 Trái cây (fruit) | Chủ | Thử cân, trừ bì → chọn độ chín → cân → trả giá |
| | 💿 Album ZPOP (zpop) | Chủ | Lấy đúng phiên bản, quà kèm, giữ giới hạn bản |
| | 💍 Tiệm vàng (jewelry) | Chủ | Bảng giá mỗi sáng; bán (cân, tính tiền); mua lại (quét tuổi, trừ hao); thẩm định đá |
| | 🚗 Đại lý xe (car_dealer) | Chủ | Chọn xe hợp nhu cầu, lái thử, tính trước bạ, trả góp, thu xe cũ |
| | ✏️ Văn phòng phẩm (stationery) | Chủ | Chạm món vào giỏ; danh sách lớp; bọc vở, dán nhãn, photo |
| **Làm đẹp, chăm sóc** | 💇 Salon tóc (salon) | Chủ | Tư vấn → pha màu, canh giờ → gội → cắt theo trình tự → sấy |
| | 💅 Làm móng (nail) | Chủ | Dũa, đẩy da → base, màu, top → hơ đèn đủ giờ |
| | 🐶 Chăm thú cưng (pet_care) | Chủ | Chải → tắm đúng nhiệt độ → sấy → tỉa móng → báo chủ |
| | 📸 Photobooth (photobooth) | Chủ | Gói, khung, phông, đạo cụ, đèn → bấm lúc vạch xanh → chọn tấm |
| | 🧺 Giặt ủi (laundry) | Chủ | Kiểm nhãn → tách màu → xử lý vết → giặt, sấy → ủi, gấp → trả đúng phiếu |
| | 🧹 Giúp việc theo giờ (giupviec) | Tổ | Chọn phòng → đúng dụng cụ, đúng chai → lau trên xuống |
| | 🏠 Nội trợ (homemaker) | Tổ | Đếm tiền chợ → làm từng việc nhà → ghi sổ chợ |
| | 👶 Bảo mẫu (babysitter) | Tổ | Đọc giấy dặn → bữa ăn hợp tuổi, tránh dị ứng → trò chơi → ru ngủ |
| **Kỹ thuật, sửa chữa** | 🔧 Sửa đồ (repair) | Chủ | Phiếu nhận → đo → chốt lỗi → báo giá → sửa → chạy thử; **đã sửa cả điện thoại, laptop, tai nghe, quạt, nồi cơm, xe đạp** |
| | 🏍️ Sửa xe máy (moto) | Chủ | Nghe bệnh → chốt lỗi → làm theo sổ tay → giao đúng biển số |
| | 🏎️ Độ xe (tuning) | Chủ | Bảng độ trong ngân sách, bỏ đồ trái luật → lắp → dyno → đo ồn |
| | 🏺 Phục chế (restore) | Chủ | Đọc dấu hiệu → chốt yêu cầu oái oăm → làm sạch → phục hồi |
| | 🚰 Thông cống (drain) | Chủ | Hỏi, nhìn, soi camera → báo giá → thông → xả thử → dọn |
| | 🎨 Xưởng vẽ (art_studio) | Chủ | Bố cục, màu, chất liệu → dựng từng lớp → giao đúng phiếu |
| **Ngoài trời** | 🌾 Nông trại (farm) | Chủ | Tưới theo thời tiết → nhổ cỏ, bắt sâu → thu hoạch đúng độ chín → bán sỉ; có màn đi trong vườn |
| | 🛵 Giao hàng (delivery) | Chủ | Nhận đơn → lộ trình → gói → giao, thu COD; có màn lái xe |
| | 🗑️ Thu gom rác (garbage) | Tổ | Đồ bảo hộ → vào ngõ → tách đồ nguy hại → bỏ đúng ngăn |
| **Lưu trú** | 🏡 Homestay (homestay) | Chủ | Lịch phòng → đón khách → dọn phòng → bữa sáng → hóa đơn |
| | 🏨 Khách sạn (hotel) | Lương | Ca luân phiên: quầy, bảng phòng, giặt là, bữa sáng, sửa chữa |
| | 🛎️ Lễ tân (reception) | Lương | Nhận khách → xếp phòng → giao chìa → ghi sổ giao ca |
| **Văn phòng** | 📒 Kế toán (accounting) | Chủ | Đối chiếu chứng từ, hỏi bản gốc |
| | 🎧 Chăm sóc khách hàng (customer_care) | Chủ | Xác minh → phối hợp → đóng yêu cầu |
| | 🧾 Kế toán DN (corp_accounting) · Thuế & lương (tax_payroll) · Kế toán tập đoàn (group_accounting) | Lương | Khay chứng từ, đóng dấu; bảng lương; ghép sổ hai bên |
| | 🗂️ Nhân sự (hr_admin) · 📞 Thư ký (secretary) · 💻 IT (it_helpdesk) | Lương | Hồ sơ thật: lọc CV, ghi lời nhắn, xếp lịch, sửa sự cố |
| | ⚖️ Luật sư (lawyer) | Lương | Chọn chứng cứ, xếp diễn biến, chỉ mâu thuẫn |
| | 🏦 Ngân hàng (teller) | Lương | Nhận quỹ → 5 bước mỗi khách → bàn giao quỹ |
| | 🔬 Viện nghiên cứu (research) | Lương | Giống cây, công thức món, sáng chế theo phiếu |
| **Công vụ, an toàn** | 🚓 Công an phường (police) | Lương | Cư trú, đồ thất lạc, hòa giải, tuần tra; cấp hàm, chức vụ |
| | 🛃 Hải quan (customs) | Lương | Luồng xanh/vàng/đỏ, tính thuế, hàng cấm; kiểm kho tiệm người chơi |
| | 📮 Bưu điện (post_office) | Lương | Cân, chọn dịch vụ, gõ cước, chia tuyến |
| | 📚 Thư viện – Lưu trữ (library) | Tổ | Ẩm kế kho, cho mượn, tính phí, biên mục |
| | 🚨 Tổng đài cứu hộ (rescue) | Lương | Địa chỉ trước → chuyện gì → trấn an → điều đội |
| | 🏊 Cứu hộ hồ bơi (lifeguard) | Lương | Thử thiết bị, sổ nước → quét 5 khu → cứu đuối nước |
| | 🚦 Gác chắn đường sắt (railway) | Lương | Thử thiết bị → dẹp người → hạ chắn đúng lúc |
| | 🗼 Gác hải đăng (lighthouse) | Lương | Tắt/bật đèn, lau kính, quan trắc, báo đài |
| | 🩺 Điều dưỡng (nurse) | Lương | Giao ca → đối chiếu vòng tay → đo, ghi → đối chiếu y lệnh |
| | 🐾 Bác sĩ thú y (vet) | Lương | Chốt bệnh → cân, tính liều → dặn chủ |
| **Giáo dục, du lịch** | 👩‍🏫 Giáo viên (teacher) | Lương | Tiết học với từng học sinh, chấm bài, họp phụ huynh, lịch năm học |
| | 🧳 Hướng dẫn viên (tour_guide) | Chủ | Đoàn có mong muốn riêng, lộ trình, quỹ đoàn, sự cố trên đường |
| **Hàng không, xa bờ** | ✈️ Phi công (pilot) · Tiếp viên (flight_attendant) | Lương | Bản tin, dầu, checklist; đón khách, an toàn; có màn bay |
| | 🛢️ Dầu khí (oil) | Lương | Đợt 14 ngày trên giàn; giấy phép công việc, cô lập thiết bị |
| **Nghệ thuật** | 📱 KOL (kol) · 🎤 Ca sĩ phòng trà (singer) · 🎬 Diễn viên (actor) · 📻 Đài phát thanh (radio) | Chủ/Lương | Theo phiếu từng bước; KOL: brief, quay, dựng, báo cáo số thật |
| **Tâm linh** | 🛕 Thầy chùa (pagoda) | Tổ | Thỉnh chuông, công phu, việc chùa, đếm tiền công đức |

Ghi chú kỹ thuật:
- Danh sách lấy từ `game/content.py` (`CAREERS`: 4 nghề gốc + 3 nghề v0.3 + 65 nghề plugin trong `game/careers/__init__.py`).
- Đã thử mở ca cho cả 72 nghề trên máy local (tạo save mới → chọn nghề → mở ca → hỏi khách → kiểm tra save): **không nghề nào lỗi**.
  Nghề nào cũng có file giao diện `public/js/careers/<id>.js` và file test `tests/test_career_<id>.py`.

### 1.2. Các hệ thống dùng chung (nghề mới chỉ cần cắm vào)

| Hệ thống | Có gì | File chính |
|---|---|---|
| **Cấp nghề** | Cấp = 1 + XP/90; vật phẩm, món mới mở theo cấp | `careers/kit.py`, `engine.py` |
| **Thăng tiến 7 bước** | Nhân viên tăng lương +8…+88 %; chủ tiệm nhận tiền boa khách quen +3…+21 %; từ bước 3 có "ca quản lý" giao việc cho 2–3 đồng đội | `promotion.py`, `promotion_office.py` |
| **Cấp hàm, chức vụ** | Công an, hải quan có thang riêng, có kỷ luật | `org.py`, `gov_rules.py` |
| **Tay nghề** | 3 mốc (40/120/260 việc không lỗi), thi 4 câu, thưởng 6/12/20 xu mỗi ngày chuẩn | `career_mastery.py` |
| **Chuyên môn** | Học có phí, rồi nhận đơn chuyên sâu | `career_specialism.py` |
| **Quy mô 8 bậc** | Mỗi nghề có 8 bậc từ "tiệm lớn" tới "chuỗi khu vực, mạng lưới" (ví dụ phở: Quán phở lớn → … → Thương hiệu phở) | `career_scale*.py` |
| **Quỹ nghề** | Mỗi nơi làm có quỹ riêng, rút về ví, góp vốn | `journey.py` |
| **Nhân viên** | Mỗi nghề có 2–3 vai trò; nhân viên tự bán đơn theo đồng hồ máy chủ kể cả khi offline; lãi nhân viên xoay theo "nghề hot hôm nay" | `workplace_business.py`, `staff_orders.py`, `staff_market.py`, `staff_life.py` |
| **Thiết bị nghề** | 3 bậc tốc độ; đón khách +15/30/50 %; chất lượng +10/20/30 %; bán online +25/50/100 % | `work_gear.py`, `income_gear.py` |
| **Phụ kiện nghề, bộ đồ nghề** | Phụ kiện mua một lần (ví dụ tủ trữ sữa); bộ đồ nghề 5 bậc +2…+8 %; mối khách quen; ⏩ Làm nhanh | `career_gadgets.py`, `pay_boost.py` |
| **Quầy của bạn** | 8 nghề có quầy tự mở bán theo thời gian thật (trà đá, trái cây, kem, bánh, trà sữa, hoa, tạp hóa, quần áo); tự nhập hàng; thuê người chơi khác đứng quầy | `quay*.py` |
| **Kho hàng** | Nhà cung cấp (chợ/đối tác/hỏa tốc), giao thiếu, hạn dùng, tự đặt hàng | `inventory.py`, `auto_order.py`, `auto_stock.py` |
| **Khách, đánh giá** | Thanh kiên nhẫn (+20 % đã nới); đánh giá nhiều góc nhìn; tiền boa hên xui; làm sai thì khách phàn nàn/đòi hoàn tiền; báo công an review vô lý | `patience.py`, `review_aspects.py`, `tips.py`, `consequences.py`, `review_police.py` |
| **Sự kiện, sự cố** | Ngày nhàn/thường/lễ hội; kiểu ngày riêng mỗi nghề (mưa, gió mùa, cuối tuần…); 130 "chuyện đời" (phạt, thuế, lừa đảo, bảo kê, nợ); 184 "chuyện bất ngờ" (trộm, phá đồ, phải đền, đột nhập đêm); tình huống nhiều góc nhìn; quyết định của chủ tiệm | `incidents.py`, `happenings.py`, `situations.py`, `shop_events.py`, `quay_events.py` |
| **Rủi ro cá nhân, bảo hiểm** | Hỏng xe, hỏng nhà, ốm, móc túi, trộm; có cảnh báo, cách phòng, mức trần; bảo hiểm trả 80 % | `rui.py` |
| **Thưởng chung** | 🔥 x3: mỗi nghề một ngày trong tuần; ⏰ Giờ vàng; ⏱️ Tăng ca ×2; 📈 thu nhập +50 % (giảm dần theo tài sản, còn +20 % trên 1 tỷ) | `x3_week.py`, `golden_hour.py`, `overtime.py`, `income_boost.py` |
| **Phố dịch vụ** | Người chơi phục vụ người chơi: giá mặc định ×3 giá NPC, 95 % cho người làm, 5 % bị đốt; hiện có: tiệc cưới, hoa cưới, váy cưới, trang điểm cô dâu, phòng nghỉ, chụp ảnh, quảng cáo trên đài, nghiên cứu, phục chế, sửa xe, thú y, độ xe, bảo dưỡng ô tô | `service_market.py` |
| **Bộ bước dùng chung** | Bước chọn, chọn theo thứ tự, chọn nhiều, nhập số, chấm chất lượng (dùng cho moto, vet, kol, singer, actor, tuning…) | `careers/stepkit.py`, `public/js/careers/slip_kit.js` |
| **Bộ giao diện** | Thanh dưới một nút chính, phiếu khách, bước đánh số, bảng chọn, vật đang làm dần đầy lên (ly, tô, khay…), nút "?" chứa luật | `docs/UI_KIT.md`, `public/js/ui-kit.js` |

### 1.3. Mức thu nhập tham chiếu (mức gốc, đã đọc trong code và tài liệu cân bằng)

| Kiểu nghề | Mức gốc | Ví dụ |
|---|---|---|
| Chủ tiệm tự làm | Lãi 8–16 xu mỗi việc, 5–7 việc mỗi ca (khoảng 50–110 xu/ca) | Sửa xe 9–16 xu/xe; giặt ủi 16–24 xu/đơn; phở 30 xu/tô (doanh thu) |
| Chủ tiệm tay nghề cao | 20–32 xu mỗi việc | Độ xe ~27 xu/xe; tranh 22–26 xu/tranh |
| Đi làm hưởng lương | 50–72 xu/ca + 4–10 xu thưởng mỗi việc làm đúng | Điều dưỡng 55–72; thú y 56–72; luật sư 50–75 |
| Lương cao nhất | 85–110 xu/ca | Phi công cơ trưởng |
| Dịch vụ cho người chơi | Giá NPC 50–250 xu × 3 | Bảo dưỡng xe máy 50 → 150; khám thú cưng 150 → 450 |

**Quy tắc cho nghề mới:** nằm trong các khung trên. Nghề mới không được trả hơn nghề cũ cùng kiểu, để người chơi chọn nghề vì
thích chứ không vì lãi. Chênh lệch thu nhập do 🔥 x3, ⏰ Giờ vàng và "nghề hot hôm nay" tạo ra, không phải do nghề mới đắt hơn.

### 1.4. Điểm mạnh và chỗ còn thiếu

**Điểm mạnh:** quy trình thật, nhiều tình huống đời thường Việt Nam, sự cố phong phú, nhiều tầng phát triển, có dịch vụ giữa
người chơi với nhau.

**Chỗ còn thiếu (nhìn chung):**

1. **Mở rộng chưa nhìn thấy được.** Đồ trang trí đã hiện trong cảnh, nhưng lên bậc quy mô (8 bậc) hay thêm nhân viên chủ yếu
   là con số và chữ. Game tham khảo cho người chơi *thấy* tiệm to lên (thêm ghế, thêm máy, thêm phòng). Nghề mới như quán net,
   nhà trọ, phòng khám, gym rất cần một "sơ đồ tiệm".
2. **Màn tổng kết cuối ngày** chưa thống nhất giữa các nghề và ít khoảnh khắc "ăn mừng": tiền về két, sao từng phần việc, món
   mới vừa mở khóa.
3. **Sự kiện nghiêng về rủi ro.** 130 chuyện đời + 184 chuyện bất ngờ phần lớn là trộm, phạt, lừa. Thiếu chuyện **tốt**: khách
   review lan truyền, đoàn khách lớn, báo chí ghé, nhà cung cấp tặng hàng, giải thưởng của phố.
4. **Nhiều nghề lương giống nhau ở nhịp chơi**: đọc phiếu → chọn → xác nhận. Cần thêm thao tác tay (kéo, giữ, canh giờ) như cà
   phê, phở, kem, photobooth đã có.
5. **Nghề "điều hành"** (chủ tịch, quản lý chuỗi) chưa có, trong khi người chơi giàu đã có 13–48 triệu xu và cần chỗ chơi tiếp.

---

## 2. Học từ các game tham khảo

Ghi chú: phần này mô tả cơ chế chung mà các game này tự giới thiệu, để học **cách làm**; không sao chép hình, tên, nội dung
của game nào. "Quán net cỏ" là cách gọi quán net bình dân Việt Nam đầu những năm 2000; game gần nhất là dòng *Internet Cafe
Simulator* (PC) và các game "cyber cafe simulator" trên điện thoại.

### 2.1. Bảng tham khảo

| Game | Giao diện đáng học | Cơ chế phát triển | Sự cố hay gặp | Mình mượn gì |
|---|---|---|---|---|
| **Internet Cafe Simulator 1–2** | Nhìn từ trên xuống thấy dãy máy; mỗi máy có biểu tượng trạng thái (trống, đang chơi, hỏng, bẩn) | Mua máy tốt hơn, cài game hot, nâng mạng, thêm đồ ăn uống, thuê kỹ thuật, dọn dẹp, bảo vệ | Máy hỏng, virus, mất mạng, trộm, côn đồ, hóa đơn điện, khách phàn nàn bẩn | **Sơ đồ máy** với icon trạng thái; một chạm vào máy để xử lý; nâng cấp từng máy |
| **PC Building Simulator** | Lắp linh kiện bằng kéo thả vào đúng khe; bảng thông số trước/sau | Mở linh kiện mới, xưởng to hơn | Hỏng linh kiện, khách đòi giá | Mini-game **lắp/sửa máy** cho quán net và tiệm điện thoại – laptop |
| **Good Pizza, Great Pizza** | Khách nói một câu mơ hồ, người chơi tự hiểu; bàn làm việc chiếm cả màn | Mở topping, máy móc, trang trí; câu chuyện khách quen | Khách khó tính, đối thủ bên kia đường | **Lời khách mơ hồ**, câu chuyện khách quen theo ngày |
| **Papa's (Pizzeria, Burgeria…)** | Chia thành các trạm (nhận đơn → nướng → trang trí → giao), mỗi trạm một màn; chấm điểm từng trạm | Mở nguyên liệu theo cấp; đồng phục, đồ trang trí; ngày lễ có món riêng | Giờ cao điểm, khách giám khảo bí mật | **Trạm làm việc đánh số**, chấm điểm từng trạm ở màn tổng kết; **khách giám khảo bí mật** |
| **Cooking Fever** | Tất cả nguyên liệu nằm trong tầm tay, chạm để cho vào; hàng khách ở trên có thanh kiên nhẫn | Nâng từng máy (nướng nhanh hơn, giữ nóng lâu hơn), trang trí tăng kiên nhẫn; nhiều nhà hàng | Khách hết kiên nhẫn, món cháy | **Nâng cấp từng máy** thấy rõ; **combo** phục vụ liên tục |
| **Diner Dash** | Kéo khách vào bàn; khách có màu, xếp đúng màu được thưởng | Thêm bàn, ghế đẹp hơn | Khách nóng tính, trẻ con quấy | **Kéo khách vào chỗ ngồi** (quán net, spa, nhà trọ); **combo màu** |
| **Two Point Hospital / Project Hospital** | Xây phòng theo chức năng; bệnh nhân đi qua chuỗi phòng; bảng chẩn đoán có % chắc chắn | Phòng mới, máy chẩn đoán, đào tạo bác sĩ | Dịch bệnh, máy hỏng, thanh tra, bệnh nhân bỏ về | Phòng khám: **% chắc chắn chẩn đoán** tăng theo khám/xét nghiệm, chi phí xét nghiệm |
| **Supermarket Simulator** | Quét mã, thối tiền bằng chạm tờ tiền; kệ hàng nhìn thấy | Mở thêm kệ, thêm mặt hàng, mua giấy phép bán hàng mới | Trộm, giá nhập tăng, hết hàng | Bán phụ kiện, bán máy: **giấy phép mở ngành hàng mới**; **giá nhập dao động** |
| **Gas Station Simulator** | Sửa sang dần từ trạm đổ nát; từng khu mở dần | Mở rộng mặt bằng theo mảnh | Khách quỵt, trộm, mất điện | **Mở rộng mặt bằng theo mảnh** nhìn thấy được |
| **Kairosoft (Game Dev Story, Cafeteria Nipponica, Pocket Clothier…)** | Màn nhỏ, chữ ít; nhân viên có chỉ số; bảng xếp hạng cuối năm | Đào tạo nhân viên, ra sản phẩm, thắng giải, mở chi nhánh | Sản phẩm thất bại, đối thủ, nhân viên nghỉ | **Chỉ số nhân viên**, **giải thưởng cuối năm**, studio game, chuỗi tiệm |
| **Stardew Valley** | Lịch mùa; mỗi ngày ngắn; quà cho dân làng | Nâng dụng cụ, chuồng trại, nhà | Thời tiết, quạ ăn vụ | Ao cá, nông trại: **lịch mùa**, nâng dụng cụ |
| **House Flipper** | Công cụ dọn, sơn, lắp; trước/sau | Mua nhà, sửa, bán lời | Hỏng hóc ẩn | Nội thất, điện nước, nhà trọ: **ảnh trước/sau**, sửa từng hạng mục |
| **Coffee Talk** | Pha đồ uống trong khi nghe chuyện; ít nút | Câu chuyện khách quen nối nhiều ngày | Cảm xúc khách | Hiệu sách, MC, karaoke: **câu chuyện khách quen** |
| **Overcooked** | Trạm rõ ràng, đồng hồ đơn ở trên | Nhiều bếp, phối hợp nhiều người | Bếp cháy, bếp bị chia đôi | Ăn vặt: **đồng hồ đơn**; chơi chung 2 người (để sau) |
| **Cozy Grove** | Mỗi ngày làm vài việc rồi nghỉ; quà mỗi ngày | Mở khu mới mỗi ngày | Gần như không có sự cố | **Nhịp chơi thư thả**, quà nhỏ mỗi ngày |
| **Game bác sĩ trên điện thoại** | Chạm vùng cơ thể, dụng cụ kéo vào vết thương | Mở dụng cụ | Bệnh nhân sợ, khóc | Phòng khám: **khay dụng cụ** kéo vào đúng chỗ |
| **Game trang điểm, làm đẹp** | Mặt khách ở giữa, khay mỹ phẩm ở dưới, quẹt ngón tay để tô | Mở bảng màu, cọ, phong cách | Khách dị ứng, khách đổi ý | Trang điểm: **quẹt để tô**, so ảnh mẫu, chấm % giống mẫu |
| **Food Truck Chef / game xe đồ ăn** | Xe nhỏ, 3–4 trạm, khách xếp hàng bên vỉa hè | Nâng xe, đổi địa điểm theo giờ | Mưa, hết gas, trật tự đô thị | Ăn vặt, bánh mì: **chọn điểm bán theo giờ** |
| **Hotel Dash / game khách sạn** | Sơ đồ phòng, khách kéo vào phòng, dọn phòng hiện bụi | Thêm phòng, nâng hạng phòng | Phòng bẩn, khách ồn | Nhà trọ: **sơ đồ dãy phòng** |

### 2.2. Những mẫu giao diện sẽ dùng lại nhiều lần

| Mẫu | Mô tả | Dùng cho |
|---|---|---|
| **Hàng khách + thanh kiên nhẫn** | Dải khuôn mặt trên cùng, mỗi người một thanh màu xanh → vàng → đỏ | Mọi nghề có khách |
| **Bàn làm việc chiếm 60 % màn** | Vật đang làm ở giữa (tô, mặt khách, máy, xe), khay dụng cụ dưới cùng | Mọi nghề làm tay |
| **Khay dụng cụ một chạm** | Hàng nút to có icon; chạm là dùng; giữ để xem tên | Ăn vặt, trang điểm, sửa máy, bác sĩ |
| **Kéo thả (tùy chọn)** | Kéo món vào vật đang làm; luôn có cách chạm thay thế (người chơi điện thoại nhỏ) | Trang điểm, lắp máy, xếp phòng |
| **Đồng hồ vòng** | Vòng tròn đầy dần trên món đang chiên/nướng/hơ; vùng xanh là chuẩn | Ăn vặt, bánh mì, nail, cà phê |
| **Combo** | Phục vụ liền 3 khách không lỗi: chữ "Combo ×3" và tiền boa nhỏ | Nghề đông khách |
| **Sơ đồ tiệm (mới)** | Lưới ô (máy, giường, phòng, ghế), mỗi ô một icon trạng thái; chạm ô để xử lý | Quán net, nhà trọ, phòng khám, spa, gym, giữ xe, karaoke |
| **Ảnh trước/sau** | Thanh trượt giữa hai ảnh | Rửa xe, điện nước, nội thất, phục chế |
| **Màn tổng kết ngày v2** | Tiền về két có hiệu ứng, sao từng trạm, món mới mở, câu khen của khách | Mọi nghề |
| **Cây nâng cấp** | Thẻ nâng cấp xếp theo tầng, cái nào mua được thì sáng | Mọi nghề có quỹ |

---

## A. Khung chung cho mọi nghề

### A1. Bộ giao diện chung "Bàn nghề"

Mọi nghề mới dùng chung một bố cục. Nghề cũ chuyển dần sang khi nâng cấp. Khung dưới đây vẽ cho màn điện thoại rộng khoảng
390 px.

**Mẫu 1: nghề làm từng món (ăn vặt, trang điểm, sửa máy, bác sĩ)**

```
┌──────────────────────────────────┐
│ 🍢 Ăn vặt Cô Út   💰128  ⭐4.6  ⏰16:40 │  ← đầu màn: tên ≤4 chữ, két, sao, giờ
├──────────────────────────────────┤
│ 😀▓▓▓ 🙂▓▓░ 😐▓░░  +2             │  ← hàng khách, thanh kiên nhẫn
├──────────────────────────────────┤
│ 🧾 Phiếu: Chân gà · cay vừa · mang về │  ← phiếu khách (1–3 dòng)
│                                  │
│          [ VẬT ĐANG LÀM ]        │  ← bàn làm việc, món dần đầy lên
│        (hộp chân gà, sốt…)       │
│                                  │
│ ① Chân gà ✓ ② Sốt ● ③ Rau ○ ④ Gói ○ │  ← các bước đánh số
├──────────────────────────────────┤
│ [🍗][🥫][🌶️][🍋][🥒][🥡]          │  ← khay dụng cụ, chạm 1 lần
├──────────────────────────────────┤
│ Tiếp: rưới sốt Thái              │
│ [        ✅ Giao cho khách       ] │  ← một nút chính
└──────────────────────────────────┘
```

**Mẫu 2: nghề có sơ đồ chỗ (quán net, nhà trọ, phòng khám, spa, gym, giữ xe, karaoke)**

```
┌──────────────────────────────────┐
│ 🖥️ Net Mây   💰340  ⭐4.4  ⏰21:15   │
├──────────────────────────────────┤
│ Chờ: 🧑‍🎓 🧑 👦(?)                  │  ← khách chờ; (?) = cần kiểm tra
├──────────────────────────────────┤
│ [01🟢][02🟢][03🔴][04⏳]           │  ← sơ đồ: 🟢 đang chơi, ⏳ sắp hết giờ
│ [05⬜][06🟢][07🧹][08🛠️]           │     ⬜ trống, 🧹 bẩn, 🛠️ hỏng, 🔴 gọi
│ [VIP1🟢][VIP2⬜]                  │
├──────────────────────────────────┤
│ Máy 03: khách gọi mì tôm         │  ← việc của ô vừa chạm
│ [🍜 Mì] [🥤 Nước] [⏱️ Nạp giờ]     │
├──────────────────────────────────┤
│ [       👉 Xếp khách vào máy 05   ] │
└──────────────────────────────────┘
```

**Mẫu 3: nghề hồ sơ/văn phòng** dùng `office_kit` đang có (phong bì → giấy tờ → đóng dấu), thêm tối thiểu một thao tác tay mỗi
hồ sơ (kéo giấy vào khay, đóng dấu bằng cú chạm giữ).

**Mẫu 4: màn tổng kết ngày v2 (mọi nghề)**

```
┌──────────────────────────────────┐
│        🌙 Hết ca ngày 12          │
│   💰 +146 xu  (bay vào két ✨)    │
│   ⭐⭐⭐⭐☆  12 khách · Combo ×5    │
├──────────────────────────────────┤
│ Trạm   Chân gà ⭐5  Sốt ⭐4  Gói ⭐5 │  ← điểm từng trạm (kiểu Papa's)
│ 🎁 Mở khóa: Bánh tráng nướng      │
│ 💬 "Sốt Thái đỉnh, mai quay lại!" │
│ 🔥 Ngày mai: x3 nghề này!         │
├──────────────────────────────────┤
│ [ 🛠️ Nâng cấp ]  [ ✅ Về nhà ]     │
└──────────────────────────────────┘
```

Quy tắc bắt buộc (giữ theo `docs/UI_KIT.md`): ≤ 25 chữ trên màn làm việc; đúng một nút chính; luật và công thức để sau nút
"?"; không gập mất dấu hiệu quyết định (dị ứng, độ cay, tuổi khách…); có cả "Giao diện gọn" và "Giao diện đầy đủ".

Ghi chú kỹ thuật:
- Thêm vào `ui-kit.js` hai phần mới: `seatMap({cells, onTap})` (sơ đồ chỗ) và `dayWrap({money, stars, stations, unlocks, quote})`
  (tổng kết ngày v2). Dùng lại `slip`, `steps`, `buildUp`, `actBar` đã có.
- Đồng hồ vòng dùng lại cách cà phê/nail đang tính giờ: thời điểm bắt đầu lưu ở máy chủ (`kit.now()`), kết quả tính khi người
  chơi bấm dừng. Không tin số giây của trình duyệt.
- Kéo thả luôn có cách chạm thay thế; kiểm tra `scripts/check_word_caps.py` cho mỗi nghề mới.

### A2. Cây phát triển chuẩn 5 tầng

| Tầng | Người chơi thấy gì | Nối vào hệ thống có sẵn |
|---|---|---|
| **1. Lên cấp nghề** | Cấp 1 → 10+: mỗi cấp mở một món/dịch vụ/khách mới, có màn "Mở khóa" | XP nghề (`kit.level`), vật phẩm có `unlock` |
| **2. Đồ nghề, máy móc** | Máy tốt hơn: nhanh hơn, ít hỏng, chất lượng cao hơn; nhìn thấy trên bàn | `work_gear`, `income_gear`, `career_gadgets`, bộ đồ nghề 5 bậc |
| **3. Mở rộng mặt bằng** | Thêm ghế/máy/phòng/giường trên sơ đồ tiệm; trang trí tăng kiên nhẫn khách | Quy mô 8 bậc (`career_scale`), trang trí (`deco`) |
| **4. Thuê người** | 2–3 vai trò; nhân viên có tốc độ, độ khéo; tự bán khi chủ vắng (không tự nhập hàng) | `workplace_business`, `staff_life`, `quay_hire` (thuê người chơi) |
| **5. Chi nhánh, chuỗi** | Mở điểm thứ 2, 3, 5…; ca quản lý chia việc; danh hiệu thương hiệu | `career_scale` (Hai cửa hàng → Chuỗi khu vực), thăng tiến bước 3+ |

Nghề làm thuê thay tầng 3–5 bằng: **thử việc → chính thức → tổ trưởng → trưởng phòng → giám đốc** (thăng tiến 7 bước, có ca
quản lý) và thêm lựa chọn **"mở cơ sở riêng"** ở bước cao (ví dụ bác sĩ mở phòng khám tư).

### A3. Sự cố và sự kiện: "vui là chính"

Chủ game muốn chơi thoải mái, ít bị phạt, phần thưởng thấy rõ. Mọi nghề mới theo 6 luật:

1. **Tỉ lệ tốt : xấu ≥ 2 : 1** trong một tuần chơi. Mỗi nghề có ít nhất 6 sự kiện tốt, 4 sự kiện trung tính, 4 sự kiện rắc rối.
2. **Báo trước, có cách phòng.** Mất điện có cảnh báo trước một ca; mua UPS/máy phát thì không sao. Thanh tra báo trước một
   ngày; tiệm sạch thì được khen.
3. **Mức trần.** Một sự cố không mất quá 8 % lãi tuần của nghề đó; người mới (7 ngày đầu ở nghề) chỉ gặp chuyện nhẹ. Giữ đúng
   luật của `incidents.py` (người mới) và `rui.py` (trần, không nợ).
4. **Luôn có lối ra tử tế.** Lựa chọn tốt có thể tốn một chút nhưng được phố quý (uy tín, khách quen, review đẹp).
5. **Thưởng nhìn thấy được.** Sự kiện tốt hiện pháo hoa, tiền bay vào két, khách quen mới có tên.
6. **Không trùng lặp với lớp sự cố đã có.** Trộm, lừa đảo, thuế, phạt vỉa hè đã có ở `incidents`/`happenings`; nghề mới chỉ
   thêm chuyện **riêng của nghề** và gắn nghề vào đúng nhóm (`FRONT`, `CASH`, `FOOD`…).

**Mẫu bảng sự kiện cho mỗi nghề:**

| Loại | Ví dụ chung | Kết quả |
|---|---|---|
| 🌟 Tốt | Review lan truyền, đoàn khách lớn, nhà cung cấp tặng hàng, báo chí ghé, giải thưởng của phố, khách quen giới thiệu bạn | +khách, +tiền boa, +danh tiếng, đồ trang trí kỷ niệm |
| 😐 Trung tính | Giờ cao điểm, mưa, lễ hội, khách lạ yêu cầu món ngoài thực đơn | Đổi nhịp chơi, có cơ hội kiếm thêm |
| ⚠️ Rắc rối | Máy hỏng, mất điện, giá nhập tăng, nhân viên xin nghỉ, khách khó, thanh tra | Có báo trước, cách phòng, trần thiệt hại |

Ghi chú kỹ thuật:
- Sự kiện riêng nghề đặt trong `SPEC['situations']` (tình huống nhiều góc nhìn), kiểu ngày `MODS` (như phở: gió mùa, mưa, cuối
  tuần, chợ sớm) và "bất ngờ trong ca" của chính nghề. Sự kiện tốt thêm thành một nhóm mới trong `happenings` (ví dụ kind
  `'vui'`), lăn bằng hạt giống như các nhóm khác, để không đổi lịch sự kiện cũ.
- Mọi khoản tiền đi qua `engine.money()` với nhóm sổ (`gift`, `recovery`, `bonus`…), không cộng thẳng.

### A4. Nối với hệ thống có sẵn (bảng kiểm cho mỗi nghề mới)

| Hệ thống | Nghề mới phải có |
|---|---|
| Hành trình | Chương mở nghề; không mở quá sớm nghề có tiền lớn |
| Quỹ nghề, kho | Kho riêng nếu bán hàng (`SPEC['inventory']`), giá chỉnh ±25 % |
| Nhân viên | 4 ứng viên NPC, 2–3 vai trò, `assist()` |
| Quầy của bạn | Chỉ với nghề bán món mang đi được (ví dụ ăn vặt, bánh mì) |
| Rủi ro và bảo hiểm | Gắn đúng nhóm sự cố; nghề nào giảm được rủi ro của người chơi khác thì bán dịch vụ đó (sửa điện chống chập, PCCC chống cháy) |
| Đánh giá | `feedback()` 3–5 tiêu chí; `review_asides` vui |
| 🔥 x3 | Thêm nghề vào **cuối** danh sách để không xáo tuần đang chạy |
| Thú cưng, xe | Thú cưng/xe có thể cộng % nghề như các nghề khác (`income_boost`, biển số, xe +3–10 %) |
| Phố dịch vụ | Ít nhất 1 dịch vụ cho người chơi, có hiệu ứng thật trong save người mua, có trần và công tắc tắt |
| Đấu giá, sưu tập | Đồ kỷ niệm của nghề (ví dụ băng VHS cũ, sách hiếm) có thể đem đấu giá |
| Có gì mới | Popup giữa màn cho người chơi |

### A5. Bảng kiểm kỹ thuật khi thêm một nghề

- [ ] `game/careers/<id>.py` theo hợp đồng `docs/PLUGIN_CAREERS.md`; `make_task` chỉ phụ thuộc (ngày, lượt).
- [ ] **Tiền tố lệnh không trùng** nghề khác và không trùng tiền tố lõi (`shop_ ac_ cs_ ph_ cl_ desk_ …`). Xem lỗi ở Phụ lục.
- [ ] Thêm id vào `ORDER` (cuối), `engine.DORMANT` (save cũ không bị đổi tới khi chơi), `scripts/strip_new_careers.py`, test
      lùi bản.
- [ ] `public/js/careers/<id>.js` + CSS dùng bộ "Bàn nghề"; qua `check_word_caps.py`.
- [ ] Chữ chỉ có tiếng Việt và tiếng Anh (i18n).
- [ ] Âm thanh: chỉ bản ghi CC0/public domain, không nhạc tổng hợp, không nhạc của ca sĩ.
- [ ] Popup "Có gì mới" và CHANGELOG.

---

## B. Nghề mới

### B0. Danh sách

| # | Nghề | Góp ý | Kiểu | Công sức | Ưu tiên | Đợt |
|---|---|---|---|---|---|---|
| B1 | 🍢 Quán ăn vặt vỉa hè | #81 #319 #507 | Chủ | M | P1 | 1 |
| B2 | 💄 Trang điểm & phụ kiện làm đẹp | #90 #120 #121 #501 | Chủ | M | P1 | 1 |
| B3 | 🩺 Bác sĩ phòng khám | #126 #139 #182 #249 | Lương → Chủ | L | P1 | 1 |
| B4 | 📱 Tiệm điện thoại – laptop | #489 #112 | Chủ | M | P1 | 1 |
| B5 | 🖥️ Quán net | #415 #490 | Chủ | L | P2 | 2 |
| B6 | 🏘️ Chủ nhà trọ | #506 | Chủ | M | P2 | 2 |
| B7 | 🎙️ MC dẫn chương trình | #139 | Chủ (tự do) | M | P2 | 2 |
| B8 | 📚 Hiệu sách cũ & câu lạc bộ | #141 | Chủ | M | P2 | 2 |
| B9 | 🏛️ Cán bộ ủy ban phường | #453 | Lương | M | P3 | 3 |
| B10 | 🏢 Chủ tịch tập đoàn | #293 | Ghế điều hành | L | P3 | 3 |
| B11 | 🥖 Xe bánh mì | đề xuất | Chủ | S | P3 | 3 |
| B12 | 🚿 Tiệm rửa xe | đề xuất | Chủ | S | P3 | 3 |
| B13 | 🅿️ Bãi giữ xe | đề xuất | Chủ | S | P3 | 3 |
| B14 | 🛺 Xe ôm công nghệ / taxi | đề xuất | Chủ (tự do) | M | P3 | 3 |
| B15 | 🔌 Thợ điện nước | đề xuất (đã có trong đợt nghề 3) | Chủ | M | P3 | 3 |
| B16 | 🧵 Tiệm may đo | đề xuất (đợt nghề 3) + #311 | Chủ | M | P3 | 3 |
| B17 | 💆 Spa – gội đầu dưỡng sinh | đề xuất | Chủ | M | P4 | 4 |
| B18 | 🏋️ Phòng gym & huấn luyện viên | đề xuất | Chủ | M | P4 | 4 |
| B19 | 🎤 Chủ quán karaoke | đề xuất (#141 có nhắc) | Chủ | M | P4 | 4 |
| B20 | 🚒 Lính cứu hỏa (PCCC) | đề xuất (đợt nghề 3) | Lương | M | P4 | 4 |
| B21 | 📐 Thiết kế nội thất | đề xuất | Chủ | L | P4 | 4 |
| B22 | 📰 Phóng viên báo phường | đề xuất | Lương | M | P4 | 4 |
| B23 | 🎮 Studio làm game nhỏ | đề xuất | Chủ | L | P4 | 4 |
| B24 | 🐟 Ao cá – bè nuôi | đề xuất | Chủ | M | P4 | 4 |
| B25 | 🔑 Thợ khóa | đề xuất (đợt nghề 3) | Chủ | S | P4 | 4 |
| B26 | 👓 Tiệm cắt kính | đề xuất (đợt nghề 3) | Chủ | S | P4 | 4 |

Đã kiểm tra để **không trùng nghề đang có**: phở, giặt ủi, sửa xe máy, giao hàng, hướng dẫn viên, tiệm vàng, nhà thuốc, KOL,
nông trại, photobooth (đã chụp ảnh cưới cho người chơi), IT hỗ trợ đều đã có nên không đưa vào. Nha khoa gộp vào phòng khám
(B3, chuyên khoa mở sau).

---

### B1. 🍢 Quán ăn vặt vỉa hè "Ăn vặt Cô Út" (#81 #319 #507)

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P1 · **Tham khảo:** Cooking Fever (mọi nguyên liệu trong tầm tay, nâng
từng máy), Food Truck Chef (xe đẩy, chọn điểm bán), Papa's (chấm điểm từng trạm).

**Vòng chơi** (một xe đẩy, 5 món mở dần):

1. Sáng: chọn **điểm bán** hôm nay (cổng trường, chợ đêm, công viên). Mỗi điểm đông khách vào giờ khác nhau.
2. Khách tới, nói món: "Chân gà sốt Thái, cay vừa, mang về".
3. Làm món theo trạm, chạm từng nguyên liệu vào hộp:
   - 🍗 **Chân gà sốt Thái:** lấy chân gà đã ngâm → rưới sốt (giữ nút, vạch xanh là vừa) → chanh, ớt theo độ cay → xoài, cà
     rốt → đậy hộp.
   - 🥟 **Bánh tráng trộn:** bánh tráng → chạm topping theo phiếu (khô bò, trứng cút, rau răm, đậu phộng) → sốt → lắc túi.
   - 🍢 **Lẩu xiên que:** thả xiên vào nồi (đồng hồ vòng) → vớt khi chín → đếm que tính tiền (mỗi màu que một giá).
   - 🐌 **Ốc:** chọn loại ốc → luộc / xào me / xào bơ tỏi (đồng hồ) → nước chấm đúng loại → tăm, kim.
   - 🐟 **Cá viên chiên:** thả vào chảo (đồng hồ; chiên quá thì cháy) → lăn sốt → xiên que.
4. Giao, thu tiền (dùng lại phần thối tiền của `till.py`, kể cả "khách đưa thiếu tiền").
5. Hết ca: màn tổng kết ngày v2, điểm từng trạm.

**Màn chính:**

```
┌──────────────────────────────────┐
│ 🍢 Cô Út · Cổng trường  💰62 ⏰16:20 │
│ 👧▓▓▓ 👦▓▓░ 🧑‍🎓▓░░ +3              │
├──────────────────────────────────┤
│ 🧾 Bánh tráng trộn · không hành   │
│ ①Bánh ✓ ②Topping 3/4 ③Sốt ○ ④Lắc ○ │
│     [ túi bánh tráng đầy dần ]    │
├──────────────────────────────────┤
│ [🥩Bò][🥚Cút][🌿Răm][🥜Đậu][🧅Hành] │
│ Bếp: [🍢 Nồi xiên ◔] [🐟 Chảo ◑]    │  ← đồng hồ vòng món đang nấu
├──────────────────────────────────┤
│ [          ➕ Thêm sốt           ] │
└──────────────────────────────────┘
```

**Phát triển:**

| Cấp | Mở |
|---|---|
| 1 | Chân gà sốt Thái, bánh tráng trộn; 1 điểm bán (cổng trường) |
| 3 | Cá viên chiên; điểm chợ đêm; nâng chảo (chiên nhanh, khó cháy) |
| 5 | Lẩu xiên que; 4 ghế nhựa (khách ngồi ăn, bán thêm nước) |
| 7 | Ốc 3 kiểu; điểm công viên cuối tuần |
| 10 | Ki-ốt cố định (không còn lo trật tự đô thị); thuê người phụ |
| Quy mô | Xe thứ 2 ở điểm khác → chuỗi xe đẩy → sốt thương hiệu riêng đóng chai |

**Kinh tế:** giá 8–20 xu/món, lãi 3–7 xu/món, 2–3 món mỗi khách; khoảng 60–100 xu/ca (ngang trà đá, kem). Có **quầy tự mở**
(thêm vào danh sách 8 quầy) cho món mang đi.

**Sự cố:**
- 🌟 Học sinh quay video "ăn vặt ngon nhất cổng trường" → 2 ngày đông khách; khách quen xin công thức sốt → tặng, nhận quà;
  hội chợ phố mời đặt quầy.
- 😐 Giờ tan học 8 khách cùng lúc (dễ ăn combo); mưa: khách mua mang về nhiều; ngày rằm: ốc ế, bánh tráng chay đắt hàng.
- ⚠️ Trật tự đô thị đi qua (dùng lại cách "dẹp ghế, gấp ô" của trà đá; có ki-ốt thì miễn); hết gas giữa ca (có bình dự phòng
  thì không sao); đoàn kiểm tra an toàn thực phẩm (đeo găng, hộp có nắp thì được khen); giá chân gà tăng 3 ngày.

**Nối hệ thống:** quầy của bạn, kho có hạn dùng (chân gà 2 ngày), sự cố nhóm `FRONT` + `FOOD`, giờ vàng, nhân viên. Dịch vụ
cho người chơi: 🍢 **Đặt mâm ăn vặt** cho tiệc ở nhà (khách tới chơi nhà vui hơn, nối `home_guests`) hoặc cho đám cưới.

**Mở rộng sau:** món theo mùa (bánh tráng nướng mùa lạnh, chè mùa nóng); thi "Vua sốt" của phố; xe đẩy theo lễ hội.

Ghi chú kỹ thuật:
- Đồng hồ nồi/chảo dùng mẫu cà phê/nail (thời điểm bắt đầu lưu ở máy chủ, chấm khi vớt). Đếm que là bước `number` của stepkit.
- Tiền tố gợi ý `av_`. Món có `allergen` (đậu phộng, hải sản).

---

### B2. 💄 Tiệm trang điểm & phụ kiện "Tiệm Xinh Mây" (#90 #120 #121 #501)

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P1 · **Tham khảo:** game trang điểm điện thoại (mặt khách ở giữa, quẹt để
tô, so ảnh mẫu), Good Pizza Great Pizza (lời khách mơ hồ), Supermarket Simulator (kệ phụ kiện).

**Vòng chơi** (hai nửa: bàn trang điểm và quầy phụ kiện):

1. Khách tới với **dịp** và **ảnh mẫu**: đi phỏng vấn, dự đám cưới, chụp kỷ yếu, hẹn hò, lên sân khấu.
2. **Hỏi da:** chạm hỏi "da dầu hay khô", "có dị ứng gì không". Có khách dị ứng thành phần (ví dụ hương liệu).
3. **Trang điểm theo lớp** (thứ tự cũng được chấm): làm sạch → kem lót → kem nền **đúng tông da** (chọn 1 trong 5 ô màu so với
   cổ khách) → che khuyết điểm → mày → mắt → má → môi → xịt khóa.
4. Mỗi lớp: chọn màu/kiểu trên khay, **quẹt ngón tay** lên vùng mặt (hoặc chạm vùng). Thanh "Giống mẫu %" tăng dần.
5. Khách soi gương, phản ứng theo % giống mẫu và độ hợp dịp.
6. **Quầy phụ kiện:** kẹp tóc, mi giả, son, bông tai… Tư vấn đúng (da nhạy cảm thì không bán keo mi rẻ), quét, thối tiền.

**Màn chính:**

```
┌──────────────────────────────────┐
│ 💄 Tiệm Xinh  💰95 ⭐4.7 ⏰10:05    │
│ 🧾 Đám cưới bạn · da dầu · ⚠️hương liệu │
├──────────────────────────────────┤
│ [ảnh mẫu]        [ MẶT KHÁCH ]    │
│  góc nhỏ          quẹt để tô      │
│ Giống mẫu ▓▓▓▓▓▓░░ 72 %           │
│ ①Sạch✓ ②Lót✓ ③Nền● ④Mắt○ ⑤Môi○   │
├──────────────────────────────────┤
│ Nền: [1][2][3][4][5]  (ô màu da)  │
│ Cọ:  [🖌️ Cọ to] [🧽 Mút] [✋ Tay]  │
├──────────────────────────────────┤
│ [        ✅ Xong lớp nền          ] │
└──────────────────────────────────┘
```

**Phát triển:**

| Cấp | Mở |
|---|---|
| 1 | Trang điểm nhẹ (đi làm, đi học); quầy 6 món phụ kiện |
| 3 | Mắt khói, kẻ mắt mèo; bảng màu thứ 2 |
| 5 | Trang điểm cô dâu (dịch vụ cưới cho người chơi, hiện salon đang làm: thêm nghề này làm người cung cấp thứ 2) |
| 7 | Trang điểm sân khấu, hóa trang Halloween (nối sự kiện Halloween) |
| 10 | Lớp dạy trang điểm (khách học trả phí); thuê thợ phụ |
| Quy mô | Ghế thứ 2 → studio có góc chụp trước/sau → chuỗi tiệm làm đẹp |

**Kinh tế:** trang điểm 25–60 xu/khách (lãi 10–20 sau mỹ phẩm), phụ kiện lãi 2–6 xu/món; khoảng 70–110 xu/ca (ngang salon, nail).

**Sự cố:**
- 🌟 Cô dâu đăng ảnh, cả xóm hỏi tên tiệm; KOL ghé (nối nghề KOL) → +danh tiếng; hãng mỹ phẩm gửi mẫu thử miễn phí.
- 😐 Mùa cưới, mùa kỷ yếu: đông khách đặt lịch; khách đổi ý giữa chừng ("thôi làm môi đỏ đi") → làm lại một lớp, không mất điểm.
- ⚠️ Khách nổi mẩn vì không hỏi dị ứng (đã hỏi thì không bao giờ xảy ra); lô son giả từ mối hàng rẻ (nối chuyện "hàng hiệu giá
  rẻ" đã có); đèn bàn trang điểm hỏng (mua đèn dự phòng).

**Nối hệ thống:** dịch vụ cưới (`wed_services`), Halloween, tủ đồ và ngoại hình nhân vật (`wardrobe`, `look`). Dịch vụ cho người
chơi: 💄 **Trang điểm nhân vật** (nhân vật người mua có lớp trang điểm hiển thị N ngày sống, tên thợ hiện ở hồ sơ).

**Mở rộng sau:** bộ phong cách (Hàn, Thái, cổ điển); cuộc thi trang điểm của phố; bộ mỹ phẩm thương hiệu riêng.

Ghi chú kỹ thuật: mặt khách là SVG chia vùng (trán, má, mắt, môi); thao tác quẹt chỉ gửi vùng và màu, máy chủ chấm theo phiếu
(không chấm nét vẽ). "Giống mẫu %" tính ở máy chủ. Tiền tố gợi ý `mk_`.

---

### B3. 🩺 Bác sĩ "Phòng khám Lá Sen" (#126 #139 #182 #249)

**Kiểu:** Lương ở Bệnh viện phường Lá Sen (cùng nơi với điều dưỡng); từ bước thăng tiến 5 được **mở phòng khám tư** (chủ) ·
**Công sức:** L · **Ưu tiên:** P1 · **Tham khảo:** Project Hospital (% chắc chắn chẩn đoán tăng theo khám, xét nghiệm), Two
Point Hospital (phòng chức năng, bệnh vui), game bác sĩ điện thoại (khay dụng cụ).

**Lưu ý nội dung:** bệnh, thuốc là **luật trong game**, đơn giản, không phải lời khuyên y tế; chọn bệnh nhẹ, đời thường (cảm
cúm, đau bụng, trầy xước, dị ứng, đau lưng…). Ca nặng thì đáp án luôn là **chuyển tuyến**.

**Vòng chơi:**

1. Bệnh nhân ngồi ghế; điều dưỡng NPC đưa phiếu (tên, tuổi, nhiệt độ, mạch).
2. **Hỏi bệnh:** chọn 3–4 câu trong 8 câu ("Đau từ bao giờ?", "Có sốt không?", "Đang dùng thuốc gì?", "Dị ứng thuốc gì?").
   Câu đúng làm thanh **"Chắc chắn %"** tăng.
3. **Khám:** chạm vùng cơ thể với dụng cụ (ống nghe, đèn soi họng, nhiệt kế, búa phản xạ).
4. **Xét nghiệm (tùy chọn):** tốn tiền bệnh nhân và thời gian; chỉ định thừa thì bệnh nhân không vui, thiếu thì dễ sai.
5. **Chẩn đoán:** chọn 1 trong 4 bệnh gợi ý, hoặc "Chuyển tuyến".
6. **Kê đơn, dặn dò:** thuốc đúng nhóm, tránh thuốc bệnh nhân dị ứng, dặn 2 điều. Đơn gửi sang **nhà thuốc**.

**Màn chính:**

```
┌──────────────────────────────────┐
│ 🩺 Phòng khám 2  ⏰09:40 · còn 3 người │
├──────────────────────────────────┤
│ 👵 Bà Năm, 68t · 🌡️38.2 · ❤️96     │
│ "Ho mấy hôm nay, đêm khó ngủ"     │
│ Chắc chắn ▓▓▓▓▓░░░ 55 %           │
├──────────────────────────────────┤
│ [Hỏi❓][Khám🔍][Xét nghiệm🧪][Đơn💊] │  ← 4 bước
│     [ hình người: đầu/ngực/bụng ] │
│ Dụng cụ: [🩺][🔦][🌡️][🔨]          │
├──────────────────────────────────┤
│ [       🧾 Chốt chẩn đoán ▸       ] │
└──────────────────────────────────┘
```

**Phát triển:**

| Bước | Mở |
|---|---|
| Thử việc (bác sĩ nội trú) | Bệnh thường gặp, bác sĩ trưởng góp ý sau mỗi ca |
| Chính thức | Xét nghiệm máu, X-quang |
| Bước 3–4 | Ca quản lý: chia bệnh nhân cho 2–3 bác sĩ NPC; khám sức khỏe đoàn (công ty, trường học) |
| Bước 5+ | **Mở phòng khám tư** (thành chủ: thuê điều dưỡng, mua máy siêu âm, mở chuyên khoa răng / mắt / nhi) |
| Quy mô | Phòng khám → đa khoa → chuỗi (8 bậc `career_scale`) |

**Kinh tế:** lương 60–80 xu/ca (trên điều dưỡng 55–72, dưới phi công 85–110) + 6–10 xu mỗi ca khám đúng. Phòng khám tư lãi
12–20 xu/bệnh nhân.

**Sự cố:**
- 🌟 Bệnh nhân khỏi bệnh mang giỏ trái cây cảm ơn; báo phường viết "bác sĩ tận tâm"; trường học mời khám sức khỏe (đơn lớn).
- 😐 Mùa cúm: hàng chờ dài nhưng bệnh dễ đoán; bệnh nhân lo lắng hỏi nhiều (chọn câu trấn an).
- ⚠️ Bệnh nhân đòi kháng sinh "cho nhanh khỏi" (từ chối khéo = điểm cao); máy X-quang hỏng (gửi bệnh viện khác, không mất tiền);
  thanh tra hồ sơ bệnh án (ghi đủ thì được khen).

**Nối hệ thống:** rủi ro "ốm" của người chơi (`rui.py`, hiện người chơi tới phòng khám NPC) → dịch vụ cho người chơi 🩺 **Khám
bệnh**: gỡ cảnh báo ốm, giảm tiền viện phí N ngày; BHYT công ty; điều dưỡng (cùng bệnh viện); nhà thuốc (nhận đơn); tổng đài cứu
hộ (ca chuyển tới); em bé (khám cho bé, nối `birth`).

**Mở rộng sau:** nha khoa (tiệt trùng dụng cụ, sơ đồ răng), mắt (nối tiệm cắt kính B26), nhi; khám tại nhà; hội chẩn với người
chơi khác.

Ghi chú kỹ thuật: Hỏi / Chẩn đoán / Đơn dùng `stepkit`; Khám là bước mới "chạm vùng" (vùng + dụng cụ là lựa chọn). "Chắc chắn %"
do máy chủ tính từ thông tin đã thu, không lộ đáp án. Có `employment` như điều dưỡng. Tiền tố gợi ý `bs_`.

---

### B4. 📱 Tiệm điện thoại – laptop "Chú Tư Mobile" (#489 #112)

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P1 · **Tham khảo:** PC Building Simulator (kéo linh kiện vào khe, bảng thông
số), Supermarket Simulator (kệ hàng, giá nhập dao động).

**Lưu ý:** tiệm **Sửa đồ Chú Tư (repair) đã sửa điện thoại, laptop, tai nghe** (màn, pin, cổng sạc, chập nước, RAM, SSD, quạt).
Người chơi xin thêm phần **bán**. Đề xuất làm **nghề riêng** (cây phát triển riêng) nhưng **dùng lại bước sửa** của repair khi
máy bảo hành hỏng.

**Vòng chơi:**

1. Sáng: xem **bảng giá nhập** hôm nay (máy mới, máy cũ, phụ kiện; dao động nhẹ).
2. Khách nói nhu cầu: "điện thoại chụp đẹp dưới 300 xu", "laptop cho sinh viên thiết kế", "đổi máy cũ lấy máy mới".
3. **Tư vấn:** chọn máy hợp nhu cầu và ngân sách (so 3 máy).
4. **Thu cũ đổi mới:** kiểm máy cũ (màn, pin, khóa tài khoản, IMEI) → định giá. Máy còn khóa tài khoản lạ có thể là đồ trộm
   (đã có chuyện "Điện thoại nghi là đồ trộm" trong lớp chuyện đời).
5. **Dịch vụ thêm:** dán cường lực (căn thẳng bằng kéo thả), chuyển dữ liệu, cài đặt ban đầu.
6. Thanh toán thẳng hoặc **trả góp** (dùng lại cách đại lý xe).
7. Máy bảo hành hỏng → bước sửa của repair.

**Màn chính:**

```
┌──────────────────────────────────┐
│ 📱 Chú Tư Mobile  💰410 ⏰14:00    │
│ 🧾 SV thiết kế · ≤900 xu · có máy cũ │
├──────────────────────────────────┤
│ [💻A 860]   [💻B 920⚠️]  [💻C 700]  │
│  RAM16 ✓     RAM16 ✓    RAM8 ✗    │
│  màn đẹp ✓   vượt giá   nhẹ ✓     │
├──────────────────────────────────┤
│ Máy cũ: [Màn✓][Pin 71%][Khóa?][IMEI?]│
│ Định giá: 120 xu                  │
├──────────────────────────────────┤
│ [  🤝 Chốt máy A + đổi máy cũ    ] │
└──────────────────────────────────┘
```

**Phát triển:**

| Cấp | Mở |
|---|---|
| 1 | Phụ kiện (ốp, cáp, sạc, cường lực), điện thoại phổ thông |
| 3 | Thu cũ đổi mới; dán cường lực |
| 5 | Laptop; trả góp |
| 7 | Máy cũ tân trang để bán lại (mua rẻ, sửa, bán lời) |
| 10 | Tủ trưng bày máy cao cấp; nhân viên bán hàng |
| Quy mô | Tiệm thứ 2 → chuỗi điện thoại của phố |

**Kinh tế:** lãi 3–8 % giá máy (máy 150–1 200 xu → 8–40 xu), phụ kiện 2–5 xu; khoảng 70–120 xu/ca. Giá thu cũ luôn thấp hơn giá
bán lại để không thành chỗ lách tiền.

**Sự cố:**
- 🌟 Máy mới ra mắt, khách xếp hàng; hãng thưởng đại lý bán chạy; khách khen dán cường lực "không một bọt khí".
- 😐 Mùa tựu trường laptop bán chạy; giá nhập tăng vì khan hàng 2 ngày (hàng tồn bán có lời hơn).
- ⚠️ Máy thu cũ bị khóa tài khoản (kiểm đủ thì không mua phải); khách đòi đổi trả quá hạn; hàng xách tay không hóa đơn (quản lý
  thị trường ghé, đã có trong lớp chuyện đời).

**Nối hệ thống:** tiệm sửa đồ (bảo hành), đấu giá (máy đời cũ hiếm thành đồ sưu tập), rủi ro "móc túi mất điện thoại" (`rui.py`)
→ dịch vụ cho người chơi 📱 **Máy thay thế giá thợ** khi bị mất điện thoại.

**Mở rộng sau:** máy chơi game, đồng hồ thông minh; sửa tận nơi; bán online qua quầy.

Ghi chú kỹ thuật: danh mục lỗi và bước sửa import từ `game/careers/repair.py`, không chép. Bảng giá nhập theo mẫu
`market_trends.py` (tin giả lập). Tiền tố gợi ý `dt_`.

---

### B5. 🖥️ Quán net "Net Mây" (#415 #490)

**Kiểu:** Chủ · **Công sức:** L · **Ưu tiên:** P2 · **Tham khảo:** Internet Cafe Simulator 1–2 (dãy máy, máy hỏng, virus,
trộm, nâng máy), PC Building Simulator (lắp máy), Diner Dash (kéo khách vào chỗ).

**Không khí "net cỏ":** dãy máy, quạt trần, mì tôm trứng, nước ngọt, sổ ghi giờ, giải đấu cuối tuần.

**Vòng chơi** (chạy theo **giờ trong ca**, không theo đồng hồ thật, để người chơi không phải canh màn):

1. Mở cửa: bật máy chủ, kiểm từng máy (máy 🛠️ thì sửa hoặc khóa).
2. Khách tới: **kiểm tuổi** (luật trong game: dưới 18 tuổi không ngồi sau 22:00; có khách nói dối tuổi, xem thẻ học sinh).
3. **Xếp khách vào máy** (chạm khách rồi chạm máy, hoặc kéo). Game thủ thích máy mạnh; khách học online thích góc yên.
4. **Nạp giờ**, thu tiền.
5. Ô máy báo việc: 🍜 gọi mì, 🥤 gọi nước, 🧹 bàn bẩn, 🦠 virus, 🔌 rớt mạng, ⏳ sắp hết giờ (mời nạp thêm). Mỗi việc là một thao
   tác ngắn (nấu mì: đồng hồ vòng; diệt virus: chọn đúng bước).
6. Cuối ca: tổng kết giờ máy, đồ ăn, máy hỏng.

**Màn chính:** xem "Mẫu 2" ở [Phần A1](#a1-bộ-giao-diện-chung-bàn-nghề) (sơ đồ máy).

**Phát triển:**

| Cấp | Mở |
|---|---|
| 1 | 8 máy cũ, mì tôm, nước ngọt |
| 3 | **Lắp máy** (kéo linh kiện CPU, RAM, card, nguồn vào khe) → máy gaming |
| 5 | Phòng VIP lạnh; ghế gaming; combo giờ + đồ ăn |
| 7 | Giải đấu cuối tuần (đông khách, phí tham gia, giải thưởng) |
| 10 | Góc stream (nối KOL); thuê kỹ thuật viên, thu ngân, bảo vệ |
| Quy mô | Tầng 2 → cyber game 40 máy → chuỗi |

**Kinh tế:** giờ máy 3–6 xu/giờ, đồ ăn lãi 2–4 xu; tiền điện theo số máy đang bật (nhắc tắt máy trống). Khoảng 70–120 xu/ca.
Máy tốt đắt: chỗ tiêu xu hợp lý cho người chơi giàu.

**Sự cố:**
- 🌟 Game hot ra mắt, kín máy; đội trong quán vô địch giải phố (cúp trưng ở quầy); khách quen tặng bánh sinh nhật quán.
- 😐 Cúp điện theo lịch (báo trước; có UPS/máy phát thì khách chơi tiếp); mưa to khách ở lâu; nghỉ hè học sinh đông.
- ⚠️ Phụ huynh tìm con trốn học (gọi phụ huynh = phố khen); công an kiểm tra giờ và khách nhỏ tuổi (kiểm tuổi đủ thì không
  sao); trộm chuột, tai nghe (khóa cáp); virus lây nhiều máy (phần mềm diệt virus); khách quá giờ quỵt tiền (nối "chuyện tiền nợ").

**Nối hệ thống:** KOL (stream), bảng xếp hạng (giải game của phố), IT hỗ trợ; dịch vụ cho người chơi 🛠️ **Lắp máy tính ở nhà**
(đồ trang trí "bàn gaming" trong nhà, +tinh thần); cúp điện của phố.

**Mở rộng sau:** người chơi khác đặt chỗ giải đấu ở quán mình; thẻ game giả lập; quán cà phê game.

Ghi chú kỹ thuật: cần `seatMap` (Phần A1). Giờ chơi của khách tính theo **lượt** trong ca như trà sữa (không chạy khi người
chơi rời màn). Kiểm tuổi dùng lại cách của tạp hóa. Tiền tố gợi ý `qn_`.

---

### B6. 🏘️ Chủ nhà trọ "Dãy trọ Cô Hai" (#506)

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P2 · **Tham khảo:** Hotel Dash (sơ đồ phòng), House Flipper (sửa từng hạng mục,
trước/sau).

**Đã có trong game:** thẻ chuyện nhà thuê (`tenancy.py`), người chơi cho người chơi thuê nhà (`rentals.py`), cho thuê nhà mình
sở hữu (`housing.py`). Nghề này biến chúng thành **việc hằng ngày** với người thuê NPC.

**Vòng chơi:**

1. Sáng: xem **sơ đồ dãy trọ** (6 phòng lúc đầu): trống, đang thuê, cần sửa, sắp hết hạn.
2. Việc trong ngày (3–5 việc):
   - 🚪 **Dẫn xem phòng:** nghe nhu cầu (sinh viên, công nhân, vợ chồng trẻ) → chọn phòng hợp → báo giá → hợp đồng, nhận cọc,
     **khai báo tạm trú** (nối công an phường).
   - ⚡ **Chốt điện nước:** đọc công tơ (số cũ, số mới) → nhân đơn giá → ghi phiếu.
   - 🔧 **Sửa chữa:** vòi rỉ, bóng đèn, khóa (tự làm hoặc gọi thợ điện nước B15, thợ khóa B25).
   - 🤝 **Chuyện người thuê:** ồn ào, nuôi thú, chậm tiền (dùng lại thẻ của `tenancy.py`).
   - 🧹 **Trả phòng:** kiểm phòng, trả cọc đúng.
3. Cuối ngày: thu tiền phòng, tổng kết.

**Màn chính:**

```
┌──────────────────────────────────┐
│ 🏘️ Dãy trọ Cô Hai  💰520 · ngày 5/tháng │
├──────────────────────────────────┤
│ [P1 🙂 SV ][P2 🙂 CN ][P3 ⬜ trống ] │
│ [P4 ⚠️ chậm][P5 🛠️ vòi][P6 ⏳ hết hạn]│
├──────────────────────────────────┤
│ P3: chị Thu xem phòng (vợ chồng trẻ)│
│ Cần: yên tĩnh · chỗ nấu · ≤60 xu  │
├──────────────────────────────────┤
│ [ 🚪 Dẫn xem ]  [ 📝 Hợp đồng ]    │
│ [        👉 Báo giá 55 xu        ] │
└──────────────────────────────────┘
```

**Phát triển:**

| Cấp | Mở |
|---|---|
| 1 | 6 phòng thường |
| 3 | Gác lửng (giá cao hơn); camera hành lang (bớt trộm) |
| 5 | Xây thêm tầng (6 → 12 phòng); máy giặt chung (thu phí) |
| 7 | Phòng khép kín có máy lạnh; thuê quản lý |
| 10 | Chung cư mini; khóa vân tay |
| Quy mô | Dãy trọ thứ 2 → ký túc xá tư → chuỗi căn hộ dịch vụ |

**Kinh tế:** tiền phòng thu theo tháng trong game (5 ngày sống), quy ra 50–100 xu/ca; trừ sửa chữa, điện nước chung. Xây tầng
tốn nhiều (chỗ tiêu xu, trả dần).

**Sự cố:**
- 🌟 Người thuê cũ thành đạt quay lại tặng quà; sinh viên đậu học bổng mời cả dãy ăn mừng; phường khen "khu trọ văn minh".
- 😐 Mùa nhập học nhiều người xem phòng; mất nước cả khu (chở nước, người thuê cảm ơn).
- ⚠️ Người thuê chậm tiền (gia hạn có hẹn, thường trả đủ); chập điện (CB tốt thì không sao); kiểm tra tạm trú (khai đủ thì được
  khen); người thuê bỏ đi để lại đồ (giữ đúng hạn).

**Nối hệ thống:** `tenancy.py`, `rentals.py` (dịch vụ 🏘️ **Phòng trọ cho người chơi**: rẻ hơn khách sạn, theo tháng), công an
phường, thợ điện nước, thợ khóa, rủi ro nhà (`rui.py`), giá bất động sản (`property_market.py`).

**Mở rộng sau:** mua nhà xuống cấp, sửa thành trọ; hội người thuê; thị trường cho thuê của phố.

Ghi chú kỹ thuật: dùng `seatMap`. Tiền dãy trọ vào quỹ nghề, tách hẳn tiền cho thuê nhà riêng của `housing.py` (không tính hai
lần). Tiền tố gợi ý `tro_`.

---

### B7. 🎙️ MC dẫn chương trình "MC Mây" (#139)

**Kiểu:** Chủ (tự do nhận show) · **Công sức:** M · **Ưu tiên:** P2 · **Tham khảo:** Coffee Talk (nghe chuyện, ít nút), game
nhịp điệu đơn giản (chạm đúng nhịp).

**Chỗ trống có sẵn:** `game/wed_services.py` ghi rõ chưa có nghề nào làm MC hay ban nhạc cho đám cưới. Nghề này lấp chỗ đó.

**Vòng chơi** (mỗi việc là một show):

1. Nhận show: đám cưới, khai trương tiệm, sinh nhật bé, hội chợ phố, đêm nhạc phòng trà.
2. **Kịch bản:** xếp các mục đúng thứ tự (đón khách → giới thiệu → nghi lễ → mời phát biểu → trò chơi → cảm ơn).
3. **Ghi đúng tên:** đọc thiệp/danh sách, chọn đúng xưng hô (ông bà, cô chú, anh chị) và đúng tên.
4. **Lên sân khấu:** mỗi mục là một thanh nhịp; chạm khi kim vào vùng xanh để nói câu dẫn. Thanh "Không khí" tăng/giảm.
5. **Ứng biến:** micro rè, cô dâu tới trễ, khách say lên sân khấu, mất điện → chọn câu ứng biến.
6. Kết thúc: vỗ tay, chủ tiệc trả tiền và tiền boa.

**Màn chính:**

```
┌──────────────────────────────────┐
│ 🎙️ Cưới Hùng–Lan  🎉 Không khí 78% │
├──────────────────────────────────┤
│ ✓Đón ✓Giới thiệu ●Nghi lễ ○Trò chơi │
│ "Xin mời hai họ…"                 │
│  ░░░░░▓▓█▓▓░░░░  ◀ kim            │  ← chạm khi kim vào vùng xanh
├──────────────────────────────────┤
│ ⚠️ Micro rè!                       │
│ [🎤 Micro dự phòng] [😄 Đùa nhẹ]   │
├──────────────────────────────────┤
│ [          🎤 Nói câu dẫn         ] │
└──────────────────────────────────┘
```

**Phát triển:** cấp 1 sinh nhật, khai trương → cấp 3 đám cưới → cấp 5 hội chợ, sự kiện công ty → cấp 7 song ngữ Việt – Anh → cấp
10 dẫn chương trình trên đài, phim trường (nối đài phát thanh, hãng phim). Đồ nghề: micro không dây, vest/áo dài, sổ kịch bản.
Quy mô: nhóm MC → công ty tổ chức sự kiện (thuê MC NPC, ban nhạc, âm thanh).

**Kinh tế:** 40–90 xu/show, 1–2 show/ca (ít việc, giá cao), khoảng 60–100 xu/ca.

**Sự cố:** 🌟 khách mời dẫn tiếp đám cưới của em; clip ứng biến lan truyền. 😐 mùa cưới kín lịch, phải chọn show. ⚠️ đọc sai tên
(kiểm thiệp thì không sai); micro hỏng (mang dự phòng); mất điện (ứng biến, hát mộc).

**Nối hệ thống:** dịch vụ cưới cho người chơi 🎙️ **MC đám cưới** (tiệc cưới người chơi có MC thật, tên hiện trong phần cảm ơn
của đám cưới trực tiếp); khai trương quầy/tiệm của người chơi; hội chợ phố; đài phát thanh; ca sĩ (ghép show).

Ghi chú kỹ thuật: thanh nhịp chấm ở máy chủ theo thời điểm bắt đầu và lúc chạm (như photobooth "bấm lúc vạch xanh"). Thêm
dịch vụ MC vào `wed_services`. Tiền tố gợi ý `mc_`.

---

### B8. 📚 Hiệu sách cũ & câu lạc bộ "Sách Cũ Gác Mây" (#141)

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P2 · **Tham khảo:** Coffee Talk (chuyện khách quen), Supermarket Simulator (kệ
theo thể loại), Kairosoft (sự kiện theo mùa).

**Đã có:** hoạt động "tiệm sách bí ẩn" và các câu lạc bộ trong Đi chơi (`community_outings.py`); thư viện phường. Nghề này là
**kinh doanh** sách cũ.

**Vòng chơi:**

1. **Thu mua:** người bán mang thùng sách → xem tình trạng (rách bìa, ố, thiếu trang, chữ ký tác giả) → định giá. Thỉnh thoảng
   có **sách hiếm**.
2. **Làm sạch, sửa:** dán gáy, lau bìa, bọc nilon (thao tác nhanh).
3. **Xếp kệ** theo thể loại (văn học, thiếu nhi, giáo khoa, truyện tranh, ngoại văn).
4. **Bán:** khách tả mơ hồ ("cuốn bìa xanh có con mèo, đọc hồi nhỏ") → tìm đúng trên kệ.
5. **Câu lạc bộ tối thứ Bảy:** chọn chủ đề, mời khách, pha trà; buổi vui → thành viên mới, khách quen.

**Màn chính:**

```
┌──────────────────────────────────┐
│ 📚 Gác Mây  💰88  ⏰15:10           │
│ 🧾 "Bìa xanh, có con mèo, hồi nhỏ" │
├──────────────────────────────────┤
│ [Văn học][Thiếu nhi●][Truyện][Ngoại văn]│
│ 📕📗📘📙📗📕  ← chạm cuốn để xem bìa │
│ Gợi ý: thiếu nhi · thập niên 90   │
├──────────────────────────────────┤
│ [      📗 Đưa cuốn này cho khách  ] │
└──────────────────────────────────┘
```

**Phát triển:** cấp 1 kệ sách → cấp 3 góc truyện tranh, thu mua tận nhà → cấp 5 góc cà phê sách → cấp 7 phòng câu lạc bộ, giấy
thẩm định sách hiếm → cấp 10 hội sách cũ của phố. Quy mô: tiệm thứ 2 → nhà sách cũ có kho → chuỗi.

**Kinh tế:** mua 1–5 xu, bán 4–15 xu; sách hiếm 50–300 xu (đưa lên **đấu giá** được); câu lạc bộ thu phí nhỏ. Khoảng 50–90 xu/ca
(nghề thư thả).

**Sự cố:** 🌟 tìm thấy bức thư cũ kẹp trong sách → trả lại chủ, nhận quà; nhà văn ghé ký tặng. 😐 mùa tựu trường bán sách giáo
khoa cũ; trời ẩm (bật máy hút ẩm). ⚠️ mối mọt (bẫy côn trùng như thư viện); sách in lậu (từ chối); khách đọc chùa cả ngày (mời
ngồi góc cà phê).

**Nối hệ thống:** thư viện (sách thanh lý), văn phòng phẩm, đấu giá, Đi chơi (tiệm sách bí ẩn); dịch vụ cho người chơi 📖 **Tủ
sách tại nhà** (đồ trang trí kệ sách có tên tiệm, +tinh thần).

Ghi chú kỹ thuật: thẩm định sách hiếm theo mẫu nhiều tiêu chí của tiệm vàng. Tiền tố gợi ý `sc_`.

---

### B9. 🏛️ Cán bộ "Ủy ban phường Mây" (#453)

**Kiểu:** Lương · **Công sức:** M · **Ưu tiên:** P3 · **Tham khảo:** Papers, Please (đối chiếu giấy tờ, nhưng **nhẹ nhàng**),
bàn hồ sơ đã có trong game (`office_kit`).

**Tách với công an phường** (cư trú, hòa giải đã có). Ủy ban làm **bộ phận một cửa**: chứng thực, hộ tịch, cấp phép, lễ hội của
phố. Thủ tục là **luật trong game**, đơn giản.

**Vòng chơi:**

1. Gọi số thứ tự, mời người dân lên.
2. Hồ sơ: khai sinh, chứng thực bản sao, đăng ký kết hôn, giấy phép sửa nhà, đăng ký hộ kinh doanh, xin tổ chức sự kiện trên vỉa hè.
3. Đối chiếu (thiếu gì, sai gì) → đóng dấu NHẬN / HẸN BỔ SUNG / TRẢ LẠI; hướng dẫn người dân (chọn lời nói).
4. Việc ngoài quầy: kiểm tra công trình sửa nhà, khánh thành công trình của phố.

**Màn chính:**

```
┌──────────────────────────────────┐
│ 🏛️ Một cửa · Số 27  ⏰08:35  hàng chờ 5 │
├──────────────────────────────────┤
│ 👨 Anh Tuấn: "Đăng ký khai sinh cho con" │
│ 📄 Tờ khai  📄 Giấy chứng sinh  📄 CCCD  │
│ ⚠️ Tên trên tờ khai ≠ giấy chứng sinh?  │
├──────────────────────────────────┤
│ [✅ NHẬN] [📝 HẸN BỔ SUNG] [↩️ TRẢ LẠI] │
├──────────────────────────────────┤
│ [       🔎 Soi từng dòng ▸        ] │
└──────────────────────────────────┘
```

**Phát triển:** thử việc → chuyên viên một cửa → tổ trưởng → phó chủ tịch phường (thang chức vụ `org.py` như công an, hải quan);
ca quản lý chia hồ sơ cho đồng nghiệp giờ cao điểm.

**Kinh tế:** lương 50–68 xu/ca + 4–8 xu mỗi hồ sơ đúng.

**Sự cố:** 🌟 cụ già gửi thư khen; phường đạt "một cửa thân thiện". 😐 cuối năm đông hồ sơ; mạng chậm (dùng sổ tay). ⚠️ người đưa
phong bì "cho nhanh" (`gov_rules`: từ chối = hồ sơ công tác sạch); giấy tờ giả (soi dấu).

**Nối hệ thống (điểm hay của nghề):** người chơi **kết hôn** (`marriage.py`), **sinh con** (`birth.py`), **sửa nhà** (`reno.py`),
**mở hộ kinh doanh** (giấy phép kinh doanh) → dịch vụ cho người chơi 🏛️ **Làm thủ tục** (giấy chứng nhận đẹp có chữ ký cán bộ
người chơi, lưu trong album). **Công trình của phố** (`town_projects.py`): cán bộ ủy ban cắt băng khánh thành.

Ghi chú kỹ thuật: dùng `office_kit` + `org.py`. Tiền tố gợi ý `ub_`.

---

### B10. 🏢 Chủ tịch tập đoàn "Tập đoàn Mây" (#293)

**Kiểu:** ghế điều hành cho người chơi đã có nhiều tiệm · **Công sức:** L · **Ưu tiên:** P3 · **Tham khảo:** Kairosoft (bảng
quyết định ngắn, tổng kết cuối năm), game tycoon (hội đồng quản trị, cổ đông).

**Ý tưởng:** không phải nghề làm tay, mà là **ghế điều hành** đặt trên các tiệm người chơi đang có. Mở khi có ít nhất 3 nơi làm
ở quy mô bậc 3 trở lên (đọc từ `career_scale`).

**Vòng chơi** (mỗi ngày một cuộc họp 5–10 phút):

1. **Họp giao ban:** 3 tờ trình từ 3 "công ty con" (chính là tiệm của người chơi), ví dụ "Mở thêm xe ăn vặt ở chợ đêm", "Lắp máy
   lạnh cho quán net", "Tuần lễ giảm giá tiệm hoa". Mỗi tờ trình ghi chi phí, lợi ích, rủi ro.
2. **Duyệt 1–2 tờ trình** (ngân sách có hạn). Tờ trình có hiệu lực N ngày cho tiệm đó (ví dụ +10 % khách 3 ngày, có trần).
3. **Việc chủ tịch:** gặp đối tác (chọn điều khoản), trả lời cổ đông, phát biểu trên đài, tài trợ công trình của phố.
4. **Cuối quý** (15 ngày sống): báo cáo, bảng xếp hạng tập đoàn của phố, danh hiệu.

**Màn chính:**

```
┌──────────────────────────────────┐
│ 🏢 Tập đoàn Mây · Họp sáng  💼 3 000 │
├──────────────────────────────────┤
│ 📄 Ăn vặt: xe chợ đêm   −1200 · +12%/5 ngày│
│ 📄 Quán net: máy lạnh   −1800 · +8%, ít hỏng│
│ 📄 Tiệm hoa: giảm giá   −400 · +khách −lãi │
├──────────────────────────────────┤
│ Đã chọn 1/2                        │
├──────────────────────────────────┤
│ [           ✍️ Ký duyệt           ] │
└──────────────────────────────────┘
```

**Phát triển:** Giám đốc điều hành → Tổng giám đốc → Chủ tịch HĐQT; mở các "ban" (tài chính, nhân sự, truyền thông), mỗi ban
thêm 1 tờ trình mỗi ngày; trụ sở là tòa nhà trên bản đồ phố.

**Kinh tế (để không phá cân bằng):**
- **Không in thêm tiền:** lương cố định 70–90 xu/ca; tờ trình chỉ cộng % có trần trên lãi tiệm của chính người chơi, không cộng
  dồn với 🔥 x3.
- Là **chỗ tiêu xu** cho người giàu: chi phí tờ trình, trụ sở, tài trợ. Hợp với hướng chủ game: thưởng thu nhập đã giảm dần theo
  tài sản (`income_boost`).

**Sự cố:** 🌟 tập đoàn được phố vinh danh; tờ trình thành công vượt dự kiến. 😐 thị trường đi xuống 3 ngày (tờ trình an toàn tốt
hơn). ⚠️ kiểm toán (sổ sạch thì được khen; nối kế toán tập đoàn); cổ đông chất vấn (trả lời thật thì qua).

**Nối hệ thống:** `career_scale`, thăng tiến (ca quản lý, `promotion_office` đã có cho phi công, hiệu trưởng), kế toán tập đoàn
(người chơi làm kế toán nhận việc của tập đoàn người chơi khác), `town_projects`, `lux`, bảng xếp hạng.

Ghi chú kỹ thuật: không là plugin nghề thường; là một màn mới cạnh `promotion_office`. Hiệu lực tờ trình lưu trong `journey` có
ngày hết hạn, áp tại `income_gear.completion_bonus` và lãi nhân viên, chung trần với các khoản thưởng khác.

---

### B11. 🥖 Xe bánh mì "Bánh mì Bà Bảy"

**Kiểu:** Chủ · **Công sức:** S · **Ưu tiên:** P3 · **Tham khảo:** Papa's (trạm: nướng → nhân → sốt → gói), Food Truck Chef.

**Vòng chơi:** sáng nướng mẻ bánh (đồng hồ lò, giòn vừa) → khách gọi (thịt nguội, xíu mại, trứng ốp, chả cá; "không hành, nhiều
ớt") → rạch bánh → phết pa-tê, bơ → xếp nhân theo phiếu → đồ chua, ngò, ớt → nước tương/sốt → gói giấy, bỏ túi. Giờ cao điểm
6:30–7:30 (học sinh, công nhân) thì khách đông, combo dễ.

```
┌──────────────────────────────────┐
│ 🥖 Bà Bảy  💰40  ⏰06:45  🔥 giờ cao điểm│
│ 🧑‍🔧▓▓▓ 👧▓▓░ 👨‍💼▓░░ +4             │
│ 🧾 Xíu mại · không hành · nhiều ớt │
│     [ ổ bánh mở ra, nhân đầy dần ] │
│ [🥖Bánh][🧈Pa-tê][🥩Xíu][🥒Chua][🌶️][🌿] │
│ [          🛍️ Gói & giao         ] │
└──────────────────────────────────┘
```

**Phát triển:** cấp 1 hai loại nhân → cấp 3 lò nướng to (mẻ 20 ổ) → cấp 5 bánh mì que, bánh mì chảo (ngồi ăn) → cấp 7 giao văn
phòng theo đơn (nối giao hàng) → cấp 10 tiệm có mặt bằng; quy mô: chuỗi xe bánh mì. Có quầy tự mở.

**Kinh tế:** 6–15 xu/ổ, lãi 2–5 xu, nhiều khách (8–12/ca) → 50–90 xu/ca.

**Sự cố:** 🌟 du khách nước ngoài khen trên mạng (đoàn khách tới); trường học đặt 50 ổ cho hội thao. 😐 mưa sáng (khách mua mang
đi); ngày rằm (bánh mì chay). ⚠️ lò hết gas (bình dự phòng); bánh mì nhập về bị ỉu (chọn mối khác, giao thiếu thì khiếu nại như
kho hiện có).

**Nối hệ thống:** quầy, kho (bánh 1 ngày, pa-tê 3 ngày), giao hàng, căn tin trường (giao bánh sỉ). Dịch vụ cho người chơi:
🥖 **Đặt bánh mì sáng** cho cả nhà (+no, tiết kiệm tiền ăn trong `needs`).

Ghi chú kỹ thuật: gần như dùng lại cấu trúc phở/cơm tấm (bày khay, gắp, chan). Tiền tố gợi ý `bmi_` (`bm_` đã là của bảo mẫu).

---

### B12. 🚿 Tiệm rửa xe "Rửa xe Bọt Mây"

**Kiểu:** Chủ · **Công sức:** S · **Ưu tiên:** P3 · **Tham khảo:** Car Detailing Simulator (xịt, bọt, lau theo vùng, thấy vết
bẩn mất dần), House Flipper (trước/sau).

**Vòng chơi:** xe vào cầu → chọn gói (rửa nhanh / rửa kỹ / vệ sinh nội thất / đánh bóng) → **xịt nước** vùng bẩn (chạm/quẹt,
vết bẩn mờ dần) → bọt tuyết → chà theo thứ tự trên xuống → xả → lau khô → hút bụi trong xe (tìm đồ khách để quên → trả lại) →
thanh trượt trước/sau cho khách xem.

```
┌──────────────────────────────────┐
│ 🚿 Bọt Mây  💰55  ⏰10:20  🚗 chờ 2  │
│ 🧾 Xe 59-X1 · rửa kỹ + hút bụi    │
│   [ xe ô tô, vết bùn mờ dần ]     │
│  Sạch ▓▓▓▓▓▓░░ 75 %               │
│ [💦 Xịt][🫧 Bọt][🧽 Chà][🌬️ Sấy][🧹 Hút] │
│ [         ✅ Giao xe cho khách     ] │
└──────────────────────────────────┘
```

**Phát triển:** xe máy → ô tô → phủ ceramic, vệ sinh khoang máy → cầu nâng thứ 2, máy rửa áp lực cao → nhân viên → chuỗi.

**Kinh tế:** xe máy 4–8 xu, ô tô 15–40 xu; lãi 50–90 xu/ca.

**Sự cố:** 🌟 khách để quên ví, trả lại → khách quen trọn đời; đội xe công ty ký hợp đồng rửa định kỳ. 😐 sau mưa lớn đông xe; nắng
gắt (rửa nhanh kẻo đọng vệt nước). ⚠️ cúp nước (bồn dự trữ); khách nói xe bị xước (có ảnh trước khi rửa thì rõ ràng).

**Nối hệ thống:** gara xe của người chơi (`garage.py`), độ xe, đại lý xe, đua xe. Dịch vụ cho người chơi: 🚿 **Rửa xe sáng bóng**
(xe hiện bóng loáng khi đi quanh phố N ngày, +chút độ bền xe giảm rủi ro hỏng vặt).

Ghi chú kỹ thuật: "Sạch %" là số vùng đã xử lý đúng dụng cụ (máy chủ chấm). Ảnh trước/sau dùng hai lớp SVG. Tiền tố `rx_`.

---

### B13. 🅿️ Bãi giữ xe "Giữ xe Chú Sáu"

**Kiểu:** Chủ · **Công sức:** S · **Ưu tiên:** P3 · **Tham khảo:** game xếp xe (parking jam), Diner Dash (xếp chỗ).

**Vòng chơi:** xe tới → **xé vé** (số vé = số chỗ) → **xếp xe vào ô** trên sơ đồ bãi (xe to chỗ to, xe về sớm để ngoài) → khách
về: **đối vé với biển số** (khách mất vé: xác minh giấy tờ xe) → thu tiền theo giờ, ngày, tháng. Cuối ngày đếm xe còn lại đúng
sổ.

```
┌──────────────────────────────────┐
│ 🅿️ Chú Sáu  💰36  🏍️ 42/60  ⏰18:05 │
│ [🏍️][🏍️][⬜][🏍️][🛵][⬜]            │
│ [🚗━━][⬜⬜][🏍️][🏍️][⬜]            │  ← sơ đồ bãi
│ Khách: vé 017 · 59-H2 123.45 ?    │
│ [🔎 Đối vé] [💵 Thu 3 xu] [🆘 Mất vé] │
│ [         🏍️ Trả xe              ] │
└──────────────────────────────────┘
```

**Phát triển:** bãi 30 chỗ → mái che → camera, vé thẻ từ → bãi ô tô → giữ xe sự kiện (đám cưới, lễ hội) → chuỗi bãi.

**Kinh tế:** 2–5 xu/xe, nhiều lượt; khoảng 40–80 xu/ca. Hợp đồng giữ xe tháng của tòa nhà.

**Sự cố:** 🌟 khách quên xe 3 ngày, giữ cẩn thận → cảm ơn, giới thiệu; đám cưới thuê giữ xe cả buổi. 😐 trận bóng lớn (đông, cần
xếp nhanh); mưa (mái che có giá). ⚠️ người lạ nhận xe không vé (xác minh đủ thì không mất xe); nhầm vé (đối biển số).

**Nối hệ thống:** xe người chơi, đám cưới, hội chợ, ủy ban phường (giấy phép bãi). Dịch vụ cho người chơi: 🅿️ **Gửi xe tháng**
(xe ít bị trộm trong `rui.py` N ngày).

Ghi chú kỹ thuật: dùng `seatMap`. Đối vé là bước đối chiếu hai chuỗi. Tiền tố `gx_`.

---

### B14. 🛺 Xe ôm công nghệ / taxi "Mây Đi"

**Kiểu:** Chủ (tài xế tự do) · **Công sức:** M · **Ưu tiên:** P3 · **Tham khảo:** Crazy Taxi bản hiền (đón đúng điểm, đi đúng
đường), màn lái của nghề giao hàng hiện có.

**Vòng chơi:** bật ứng dụng → **nhận cuốc** (xem điểm đón, điểm đến, giá; chọn nhận/bỏ) → tới điểm đón, **gọi khách** đúng tên →
đưa mũ bảo hiểm (xe máy) / mở cửa (ô tô) → **chọn đường** (ngắn mà kẹt hay xa mà thoáng) hoặc lái trên bản đồ (dùng màn lái của
giao hàng) → trả khách, thu tiền mặt hoặc qua ví → khách chấm sao.

```
┌──────────────────────────────────┐
│ 🛺 Mây Đi  ⭐4.9  💰48  ⏰17:30 (giờ tan tầm)│
│ 📍 Chợ Mây → 🏁 Bến xe  · 22 xu   │
│ 🧑 Chị Hạnh · 1 vali               │
│ Đường: [A ngắn 🚦kẹt] [B xa ✓thoáng] │
│      [ bản đồ nhỏ, xe đang chạy ] │
│ [         ✅ Nhận cuốc            ] │
└──────────────────────────────────┘
```

**Phát triển:** xe máy → ô tô 4 chỗ → 7 chỗ, xe điện (ít tốn xăng) → tài xế đối tác hạng vàng (cuốc sân bay) → thuê tài xế, đội
xe → hãng taxi nhỏ.

**Kinh tế:** 8–30 xu/cuốc, xăng, khấu hao; 60–100 xu/ca. Xe của người chơi trong gara dùng được (xe tốt chạy nhanh hơn: ý nghĩa
cho việc mua xe).

**Sự cố:** 🌟 khách để quên điện thoại, trả lại → thưởng; khách quen đặt riêng đi sân bay. 😐 giờ tan tầm giá cao hơn; mưa nhiều
cuốc. ⚠️ cảnh sát giao thông dừng xe (có giấy tờ đủ thì đi tiếp; đã có trong lớp chuyện đời); khách say (chọn cách xử lý an
toàn); xe hỏng giữa đường (bảo dưỡng ở tiệm sửa xe thì hiếm).

**Nối hệ thống:** gara, sửa xe máy, đèn giao thông (`traffic.py` đang dùng cho giao hàng, quầy), rủi ro xe, sân bay (phi công,
tiếp viên). Dịch vụ cho người chơi: 🛺 **Xe đưa đón** (người chơi đi chơi/đi du lịch tốn ít thời gian hơn hoặc rẻ hơn).

Ghi chú kỹ thuật: tách khỏi giao hàng (giao hàng chở hàng, COD). Dùng lại `delivery_drive.js`/`delivery_map.js` cho màn lái.
Tiền tố `xo_`.

---

### B15. 🔌 Thợ điện nước "Điện nước Anh Lực"

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P3 · **Tham khảo:** House Flipper (sửa từng hạng mục), game nối ống nước (pipe
puzzle). Đã có trong danh sách đợt nghề 3 (`docs/CAREERS_BATCH_3.md`).

**Vòng chơi:** khách gọi (cúp điện một phòng, vòi rỉ, ống tắc, ổ cắm cháy) → tới nhà → **dò lỗi** (bút thử điện, đồng hồ nước) →
báo giá → **ngắt CB trước** (an toàn: quên là lỗi nặng) → sửa: chọn dây đúng tiết diện theo công suất (bước nhập số), nối ống
(mini-game xoay khớp nối) → thử lại → dặn khách.

```
┌──────────────────────────────────┐
│ 🔌 Anh Lực · nhà cô Lan  ⏰14:10   │
│ 🧾 Bếp mất điện, ngửi mùi khét    │
│ [ sơ đồ: CB ─ ổ cắm bếp 🔥 ─ đèn ] │
│ ① Ngắt CB ✓ ② Dò ● ③ Thay ○ ④ Thử ○ │
│ [🖊️ Bút thử][📏 Đồng hồ][🔧 Kìm][🧯]│
│ [        🔎 Dò ổ cắm bếp          ] │
└──────────────────────────────────┘
```

**Phát triển:** sửa vặt → đi dây phòng mới → lắp bình nóng lạnh, máy bơm → thầu điện nước công trình (nối nhà trọ, nội thất) →
đội thợ.

**Kinh tế:** 10–14 xu/việc (theo đợt nghề 3), 5–7 việc/ca.

**Sự cố:** 🌟 phát hiện sớm dây sắp chập, cứu căn nhà → được báo phường khen; khách giới thiệu cả chung cư. 😐 mùa mưa nhiều nhà
dột, chập. ⚠️ chủ nhà đòi nối "tạm" không CB (từ chối = điểm cao); ống âm tường không có bản vẽ (dò kỹ).

**Nối hệ thống:** nhà và sửa nhà của người chơi (`reno.py`, phần "điện nước"), rủi ro nhà chập điện, vỡ ống (`rui.py`), nhà trọ.
Dịch vụ cho người chơi: 🔌 **Kiểm tra điện nước nhà** (gỡ cảnh báo rủi ro nhà, giảm nửa khả năng chập/vỡ ống N ngày, +độ bền
phần điện nước).

Ghi chú kỹ thuật: mini-game nối ống là bước "chọn theo thứ tự" của stepkit với hình khớp nối. Tiền tố `dnc_` (`dn_` đã là của diễn viên).

---

### B16. 🧵 Tiệm may đo "May Bà Tư" (+ góp ý #311)

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P3 · **Tham khảo:** Pocket Clothier (Kairosoft: may, mẫu mới, xu hướng), game may
đồ (đo, cắt, may theo đường).

**Liên quan:** shop quần áo (clothing) hiện có **sửa đồ** (lai quần, bóp eo) và câu chuyện "Tiệm May Bà Tư". Người chơi #311 xin
**may đo theo số đo**. Đề xuất hai bước: (1) thêm loại đơn "📏 Đặt may" vào shop quần áo (Phần C), (2) nghề may đo riêng cho người
muốn làm sâu.

**Vòng chơi:** khách chọn kiểu (áo dài, sơ mi, vest, váy) và vải → **lấy số đo** (vòng ngực, eo, mông, dài tay: đọc thước, ghi
số) → cộng chừa đường may (bước tính) → **cắt theo rập** (kéo theo đường nét đứt) → may theo thứ tự → hẹn **thử đồ** → chỉnh lại
nếu cần → giao.

```
┌──────────────────────────────────┐
│ 🧵 May Bà Tư  💰70  ⏰09:30         │
│ 🧾 Áo dài cưới · lụa đỏ · thử ngày 3 │
│  [ hình người + thước dây ]       │
│ Ngực [86] Eo [64] Mông [__] Tay [__]│
│ ①Đo● ②Cắt○ ③May○ ④Thử○            │
│ [        📏 Ghi số đo mông        ] │
└──────────────────────────────────┘
```

**Phát triển:** sửa đồ → may sơ mi, váy → áo dài, vest → bộ sưu tập theo mùa → thợ phụ, máy may công nghiệp → nhà may thương hiệu.

**Kinh tế:** 10–15 xu/món (đợt nghề 3), áo dài cưới 40–80 xu; đồ may đo cho người chơi giá NPC 100 xu × 3.

**Sự cố:** 🌟 áo dài cô dâu lên ảnh cưới đẹp → khách đặt theo; hoa hậu phố đặt may. 😐 mùa cưới, Tết đông đơn. ⚠️ khách "sẽ giảm
5 ký" đòi may theo số đo tương lai (khuyên may theo số hiện tại + hẹn chỉnh); vải khách mang thiếu khổ (báo trước khi cắt).

**Nối hệ thống:** tủ đồ nhân vật (`wardrobe`) → dịch vụ cho người chơi 👗 **May đồ cho nhân vật** (món đồ có tên thợ may, mặc được
trong phố), dịch vụ cưới (váy cưới hiện của shop quần áo), shop quần áo (đơn "Đặt may" chuyển sang).

Ghi chú kỹ thuật: số đo khách sinh từ (ngày, lượt); bước "chừa đường may" là bước `number`. Tiền tố `may_`.

---

### B17. 💆 Spa – gội đầu dưỡng sinh "Spa Lá Bạc Hà"

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P4 · **Tham khảo:** Diner Dash (xếp khách vào giường), game spa điện thoại (thao tác
massage theo vùng, thanh thư giãn).

**Vòng chơi:** khách tới, chọn liệu trình (gội đầu dưỡng sinh, massage chân, xông hơi, đắp mặt nạ) → **xếp vào giường** trên sơ đồ
→ pha nước đúng nhiệt độ → làm từng bước (gội: làm ướt → dầu gội → **day ấn huyệt theo thứ tự** → xả → ủ → sấy) → thanh "Thư giãn"
của khách tăng → mời trà gừng → thanh toán, đặt lịch lần sau.

```
┌──────────────────────────────────┐
│ 💆 Lá Bạc Hà  💰84  ⏰19:00         │
│ [🛏️1 😌][🛏️2 ⬜][🛏️3 🧖][🪑 chờ 2]  │
│ Giường 3: gội đầu dưỡng sinh       │
│ Thư giãn ▓▓▓▓▓░░ 68 %  · nước 39°C ✓│
│ Day: [Trán●][Thái dương○][Gáy○][Vai○]│
│ [         ✋ Day ấn vùng trán      ] │
└──────────────────────────────────┘
```

**Phát triển:** 2 giường gội → phòng massage chân → xông hơi thảo dược → gói liệu trình 10 buổi (khách quen) → kỹ thuật viên →
chuỗi spa.

**Kinh tế:** 15–45 xu/khách, lãi 8–18; 60–100 xu/ca.

**Sự cố:** 🌟 khách văn phòng mua gói 10 buổi; người nổi tiếng ghé. 😐 cuối tuần đông; trời lạnh (xông hơi đắt hàng). ⚠️ nước nóng
quá (chỉnh nhiệt độ trước khi gội: không bao giờ bỏng nếu đo); bình nước nóng hỏng (gọi thợ điện nước).

**Nối hệ thống:** tinh thần (`life.py`, nhu cầu `needs`) → dịch vụ cho người chơi 💆 **Thư giãn** (+tinh thần trong trần hiện có,
xả mệt), thú cưng không liên quan, salon/nail (combo làm đẹp).

Ghi chú kỹ thuật: dùng `seatMap`. Bước day huyệt = "chọn theo thứ tự". Không có nội dung nhạy cảm (spa gia đình). Tiền tố `sp_`.

---

### B18. 🏋️ Phòng gym & huấn luyện viên "Gym Gió Mạnh"

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P4 · **Tham khảo:** Gym Tycoon (máy tập, hội viên), game huấn luyện (kế hoạch tập,
chỉ số tiến bộ).

**Vòng chơi:** hội viên tới quẹt thẻ → hội viên mới: **đo chỉ số** (cân, vòng eo) → **lên giáo án** (chọn 4 bài hợp mục tiêu: giảm
cân, tăng cơ, dẻo dai; người đau lưng tránh bài nặng) → **chỉnh tư thế** (chọn chỗ sai trên hình) → theo dõi tiến bộ theo tuần →
bán nước, thẻ tháng. Giữa ca: lau máy, kiểm máy hỏng.

```
┌──────────────────────────────────┐
│ 🏋️ Gió Mạnh  💰66  👥 18/30  ⏰18:30 │
│ [🏃 máy chạy ×3][🏋️ tạ][🚴 xe][🧘 thảm]│
│ 👩 Chị Mai · giảm 3kg · ⚠️ đau gối  │
│ Giáo án: [🚴✓][🧘✓][🏃?][🦵 squat ✗] │
│ [         📝 Chốt giáo án         ] │
└──────────────────────────────────┘
```

**Phát triển:** phòng tập nhỏ → khu tạ, lớp yoga/aerobic theo giờ → PT 1 kèm 1 → bể bơi (nối cứu hộ hồ bơi) → chuỗi.

**Kinh tế:** thẻ tháng chia theo ngày + PT 15–30 xu/buổi; 60–100 xu/ca.

**Sự cố:** 🌟 hội viên đạt mục tiêu, khoe ảnh trước/sau → hội viên mới; giải chạy của phố. 😐 đầu năm ai cũng đăng ký (đông rồi
vắng dần); nắng nóng (bật quạt, máy lạnh). ⚠️ máy chạy hỏng (khóa máy, gọi sửa); hội viên tập sai tư thế (chỉnh kịp thì không sao).

**Nối hệ thống:** nhu cầu sức khỏe/tinh thần, rủi ro ốm (`rui.py`: tập đều thì giảm khả năng ốm) → dịch vụ cho người chơi 🏋️
**Huấn luyện cá nhân** (giảm nửa khả năng ốm N ngày, danh hiệu "khỏe" tạm thời).

Ghi chú kỹ thuật: dùng `seatMap` + stepkit. Tiền tố `gym_`.

---

### B19. 🎤 Chủ quán karaoke "Karaoke Nốt Mây"

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P4 · **Tham khảo:** Hotel Dash (phòng, dọn phòng), game quản lý quán bar (đồ uống
theo phòng).

**Đã có:** phòng hát trực tiếp nhiều người (`karaoke.py`, YouTube chính chủ) và hoạt động đi hát. Góp ý #141 ghi "nghề vận hành
karaoke vẫn hoãn". Nghề này là **người vận hành quán**.

**Vòng chơi:** khách tới (nhóm bạn, gia đình, công ty) → **xếp phòng** theo số người → bật máy, chỉnh âm thanh (bass, vang) → phòng
gọi đồ (trái cây, nước, khăn) → phòng báo micro hết pin, đầu máy treo → hết giờ tính tiền theo phút + đồ → dọn phòng.

```
┌──────────────────────────────────┐
│ 🎤 Nốt Mây  💰120  ⏰21:40          │
│ [P1 🎶 6ng][P2 🔔 gọi][P3 🧹][VIP 🎶]│
│ P2: thêm 2 dĩa trái cây, micro yếu │
│ [🍉 Trái cây][🥤 Nước][🔋 Pin micro] │
│ [          🚶 Mang lên P2         ] │
└──────────────────────────────────┘
```

**Phát triển:** 4 phòng → phòng VIP → hệ thống âm thanh xịn → phòng tiệc công ty → chuỗi.

**Kinh tế:** 10–25 xu/giờ phòng + đồ; 70–110 xu/ca; tiền điện, bản quyền (giả lập).

**Sự cố:** 🌟 công ty bao trọn quán tiệc tất niên; nhóm khách hát hay, quay clip giới thiệu. 😐 cuối tuần kín phòng; ngày lễ. ⚠️
khách say ồn ào (đã có chuyện "hàng xóm báo loa quá to"); kiểm tra PCCC (bình chữa cháy đủ thì qua; nối B20).

**Nối hệ thống:** phòng hát trực tiếp (`karaoke.py`, `live`) → người chơi đặt "phòng riêng" ở quán của người chơi (dịch vụ 🎤 **Thuê
phòng hát riêng cho nhóm bạn**), ca sĩ phòng trà, MC.

Ghi chú kỹ thuật: dùng `seatMap`; không phát nhạc trong nghề (chỉ âm thanh CC0), phần hát thật vẫn ở phòng trực tiếp. Tiền tố `kr_`.

---

### B20. 🚒 Lính cứu hỏa "Đội PCCC phường Mây"

**Kiểu:** Lương · **Công sức:** M · **Ưu tiên:** P4 · **Tham khảo:** Firefighting Simulator (chọn bình đúng loại cháy, lộ trình
xe), Overcooked (phối hợp đội). Đã có trong đợt nghề 3.

**Vòng chơi:** ca trực: kiểm xe, vòi, bình theo kim áp → báo cháy: hỏi địa chỉ, loại cháy → chọn **lộ trình xe** (hẻm hẹp xe lớn
không vào) → chọn **bình đúng loại cháy** (A gỗ giấy / B xăng dầu / C khí / điện: ngắt điện trước) → đưa người ra (đếm đủ người) →
**kiểm tra PCCC** tiệm trong phố (bình hết hạn, lối thoát bị chắn).

```
┌──────────────────────────────────┐
│ 🚒 Trực ca · 🔔 Báo cháy!  ⏰20:12 │
│ 📍 Hẻm 12 · quán ăn · khói bếp dầu │
│ Lộ trình: [Đường lớn ✓] [Hẻm 12 ✗hẹp]│
│ Bình: [💧A][🛢️B ✓][⚡CO2][🧯bột]    │
│ Người trong nhà: 3 · đã ra 2      │
│ [        🧯 Phun bình B           ] │
└──────────────────────────────────┘
```

**Phát triển:** chiến sĩ → tổ trưởng → đội trưởng (thang chức vụ như công an); diễn tập ở trường học, chung cư.

**Kinh tế:** 58–74 xu/ca (đợt nghề 3).

**Sự cố:** 🌟 cứu được con mèo trên mái, cả xóm vỗ tay; trường học tặng tranh cảm ơn sau buổi diễn tập. 😐 báo cháy giả (xác minh
rồi về, không mất gì); mùa khô nhiều cuộc gọi. ⚠️ hẻm bị xe đỗ chắn (nối bãi giữ xe); người xem quay phim chắn đường.

**Nối hệ thống:** rủi ro "cháy bếp" nhà người chơi (`rui.py`), bình chữa cháy (đồ chống rủi ro đã bán), tiệm của người chơi giàu →
dịch vụ cho người chơi 🧯 **Kiểm tra PCCC tiệm** (giảm rủi ro cháy tiệm N ngày, giấy chứng nhận treo tiệm). Tổng đài cứu hộ (cuộc
gọi chuyển sang).

Ghi chú kỹ thuật: có `employment`; dùng air_kit/street_kit như cứu hộ. Tiền tố `pccc_` (`pc_` đã là của chăm thú cưng).

---

### B21. 📐 Thiết kế nội thất "Studio Nhà Mây"

**Kiểu:** Chủ · **Công sức:** L · **Ưu tiên:** P4 · **Tham khảo:** House Flipper, Design Home (bố trí theo gu khách, khách chấm).

**Vòng chơi:** khách đưa **phòng trống** (phòng khách, phòng ngủ bé, quán cà phê) + gu (tối giản, cổ điển, Hàn Quốc) + ngân sách →
**bố trí đồ** trên lưới phòng (kéo thả, xoay 90°) → chọn màu sơn, đèn → kiểm luật (lối đi ≥ 1 ô, ổ cắm gần bàn làm việc) → xem thử
3D/2.5D → khách chấm điểm theo gu.

```
┌──────────────────────────────────┐
│ 📐 Nhà Mây · Phòng bé Na  💼 450 xu │
│ Gu: Bắc Âu · màu sáng · có góc đọc │
│ [ lưới phòng 6×5: 🛏️ 📚 🪑 🪟 ]     │
│ Hợp gu ▓▓▓▓▓░ 70 % · Ngân sách ✓  │
│ [🛏️][🪑][📚][💡][🪴][🎨 Sơn]       │
│ [        👀 Cho khách xem thử     ] │
└──────────────────────────────────┘
```

**Phát triển:** phòng đơn → căn hộ → quán, tiệm → biệt thự (nối dinh thự `estates.py`) → đội thi công (nối điện nước, thợ khóa) →
công ty kiến trúc.

**Kinh tế:** phí thiết kế 20–60 xu/phòng; 60–110 xu/ca.

**Sự cố:** 🌟 thiết kế được lên báo phường; khách giàu đặt cả dinh thự. 😐 đồ nội thất về trễ (đổi món tương đương). ⚠️ khách đổi gu
giữa chừng (sửa một phần, không mất điểm); đo sai kích thước (đo lại trước khi đặt hàng thì không bao giờ sai).

**Nối hệ thống:** trang trí nhà (`deco.py`, `home_decor.py`), sửa nhà (`reno.py`), dinh thự, đảo riêng. Dịch vụ cho người chơi:
📐 **Thiết kế lại phòng** (người thiết kế đề xuất bố trí; người mua bấm "áp dụng" là đồ tự xếp theo bản vẽ; +Ấm cúng nếu hợp gu).

Ghi chú kỹ thuật: dùng lưới và xoay 90° của `deco.py` (góp ý #358 xoay nội thất đã được ghi nhận). Tiền tố `nth_`.

---

### B22. 📰 Phóng viên "Báo Phố Mây"

**Kiểu:** Lương · **Công sức:** M · **Ưu tiên:** P4 · **Tham khảo:** Headliner (chọn tin, hậu quả xã hội), Papers, Please (kiểm
nguồn).

**Vòng chơi:** họp biên tập nhận đề tài → đi lấy tin (phỏng vấn 3 người: chọn câu hỏi) → **kiểm chứng** (đối chiếu nguồn, phát hiện
tin đồn) → viết tít (chọn tít đúng, không giật gân) → chọn ảnh → nộp bài trước giờ chốt → bài đăng, phản hồi bạn đọc.

```
┌──────────────────────────────────┐
│ 📰 Báo Phố Mây · Chốt 16:00  ⏰14:20 │
│ Đề tài: "Chợ đêm mở thêm dãy ăn vặt"│
│ Nguồn: 👵✓ 👮✓ 🧑‍🍳? (chưa kiểm)     │
│ Tít: [A Chợ đêm thêm 12 xe ✓]     │
│      [B "Chợ đêm loạn" ✗ giật gân] │
│ [         📤 Nộp bài              ] │
└──────────────────────────────────┘
```

**Phát triển:** cộng tác viên → phóng viên → biên tập viên → tổng biên tập; mảng: đời sống, kinh tế, thể thao (đua xe, giải pet).

**Kinh tế:** lương 50–70 xu/ca + nhuận bút 4–10 xu/bài.

**Sự cố:** 🌟 bài viết giúp tìm lại chủ cho chú chó lạc; giải báo chí của phố. 😐 tin nóng bất ngờ (đổi đề tài). ⚠️ tin đồn chưa
kiểm chứng (kiểm thì không đăng sai); người trong bài xin gỡ (đã có chuyện "Người trong ảnh tới đòi gỡ bài").

**Nối hệ thống (điểm mạnh):** tin trong game đã nhiều: ticker, đài phát thanh, công trình của phố, đua xe, giải thú cưng, đám cưới
người chơi. Bài viết lấy **sự kiện thật của người chơi** (người chơi đồng ý) → dịch vụ cho người chơi 📰 **Bài viết về tiệm của
bạn** (lên ticker phố + tăng khách tiệm nhẹ N ngày, có trần, như quảng cáo trên đài).

Ghi chú kỹ thuật: không tự đăng tên người chơi khi chưa đồng ý (privacy). Tiền tố `bao_`.

---

### B23. 🎮 Studio làm game nhỏ "Mây Games"

**Kiểu:** Chủ · **Công sức:** L · **Ưu tiên:** P4 · **Tham khảo:** Game Dev Story (Kairosoft: thể loại × chủ đề, chỉ số nhân viên,
giải thưởng cuối năm).

**Vòng chơi** (một dự án kéo dài vài ngày, mỗi ca làm một phần): chọn **thể loại × chủ đề** (đua xe × nấu ăn…) → chia việc cho nhân
viên theo chỉ số (lập trình, đồ họa, âm thanh) → **làm việc tay**: sửa lỗi (tìm 3 chỗ sai trong đoạn logic đơn giản), vẽ (chọn
bảng màu), lồng tiếng → thử nghiệm (bảng lỗi) → phát hành → điểm đánh giá, doanh thu theo tuần.

```
┌──────────────────────────────────┐
│ 🎮 Mây Games · Dự án "Phở Racing" │
│ Vui ▓▓▓▓░ Đẹp ▓▓▓░░ Mới ▓▓▓▓▓      │
│ 👩‍💻 Lan: code 7 · 🎨 Huy: vẽ 8      │
│ 🐞 Lỗi: 3 (chạm để sửa)            │
│ [🐞 Sửa lỗi][🎨 Vẽ][🎵 Âm thanh]   │
│ [        🚀 Thử nghiệm bản beta   ] │
└──────────────────────────────────┘
```

**Phát triển:** game điện thoại nhỏ → máy chơi game → giải "Game của năm" của phố → studio lớn, phát hành game của người chơi khác.

**Kinh tế:** doanh thu dự án chia theo ngày, trung bình 60–110 xu/ca; dự án thất bại vẫn hòa vốn (không phạt nặng).

**Sự cố:** 🌟 game lọt top, phố xếp hàng chơi thử; nhân viên ra ý tưởng hay. 😐 hạn chót dồn (tăng ca). ⚠️ lỗi lớn sau phát hành (vá
nhanh là xong); nhân viên xin nghỉ (tuyển người khác).

**Nối hệ thống:** quán net (game của studio cài ở quán), KOL (review game), ghép ba (`tile_match`: "game của studio" là các màn mới
do người chơi thiết kế, để sau).

Ghi chú kỹ thuật: dự án nhiều ngày lưu trong `ext.data` (như đoàn khách nhiều ngày của hướng dẫn viên). Tiền tố `gd_`.

---

### B24. 🐟 Ao cá – bè nuôi "Bè cá Cửa Lở"

**Kiểu:** Chủ · **Công sức:** M · **Ưu tiên:** P4 · **Tham khảo:** Stardew Valley (ao cá, lịch mùa, nâng dụng cụ), Fishing Clash
(kéo câu theo thanh lực).

**Vòng chơi:** sáng đo nước (độ mặn, nhiệt độ, oxy) → bật máy sục khí nếu thiếu → cho ăn đúng lượng (nhiều thì bẩn nước, ít thì cá
chậm lớn) → vớt cá bệnh → thu hoạch đúng kích cỡ (kéo lưới theo thanh lực) → cân, phân loại → bán cho chợ, nhà hàng.

```
┌──────────────────────────────────┐
│ 🐟 Bè Cửa Lở  💰58  ⏰06:10  🌊 gió cấp 3│
│ [Lồng1 🐟🐟 ✓][Lồng2 🐟 ⚠️O2][Lồng3 🦐]│
│ Lồng 2: oxy 3.1 (thấp) · 28°C     │
│ [💨 Sục khí][🍚 Cho ăn][🥅 Thu hoạch] │
│ [        💨 Bật sục khí lồng 2    ] │
└──────────────────────────────────┘
```

**Phát triển:** ao nhỏ → bè 3 lồng → tôm, cua → kho lạnh → hợp tác xã thủy sản (nối hải đăng: cảnh báo gió) → chuỗi.

**Kinh tế:** chu kỳ nuôi nhiều ngày, thu theo đợt; trung bình 50–90 xu/ca.

**Sự cố:** 🌟 mùa cá đẹp, giá cao; nhà hàng tiệc ký hợp đồng. 😐 trời trở gió (gia cố bè). ⚠️ mất điện máy sục khí (máy phát dự phòng
thì không sao); bão (hải đăng báo trước 1 ngày: thu hoạch sớm).

**Nối hệ thống:** nông trại (bán sỉ chợ đầu mối), hải đăng (thời tiết biển), nhà hàng tiệc, phở/cơm (nguyên liệu), câu cá trong Đi
chơi nếu có. Dịch vụ cho người chơi: 🐟 **Giỏ hải sản tươi** (nguyên liệu nấu ăn ở nhà, +tinh thần bữa cơm).

Ghi chú kỹ thuật: dùng lại vòng đời cây trồng của nông trại (`farm.py`) cho cá. Tiền tố `ca_` đã bị kế toán DN dùng (`ca_`) →
dùng `aoc_`.

---

### B25. 🔑 Thợ khóa "Khóa Chú Bảy"

**Kiểu:** Chủ · **Công sức:** S · **Ưu tiên:** P4 · **Tham khảo:** mini-game mở khóa (xoay chốt theo nhịp). Đã có trong đợt nghề 3.

**Vòng chơi:** khách gọi mở khóa → **xác minh chủ nhà** trước (giấy tờ, hàng xóm xác nhận) → mở bằng mini-game (đẩy từng chốt lên đúng
độ cao) → làm chìa theo răng (so răng chìa mẫu) → thay ruột khóa.

```
┌──────────────────────────────────┐
│ 🔑 Chú Bảy · nhà anh Phúc  ⏰22:15 │
│ Xác minh: [🪪 Giấy tờ ✓][🏠 Hàng xóm ?]│
│  Chốt: ▮▯▮▮▯  (đẩy đúng độ cao)   │
│ [⬆️ Đẩy chốt 2]                    │
│ [          🔓 Mở khóa             ] │
└──────────────────────────────────┘
```

**Phát triển:** mở khóa, làm chìa → khóa điện tử, vân tay → két sắt → dịch vụ 24 giờ.

**Kinh tế:** 8–12 xu/việc (đợt nghề 3), ca đêm giá cao hơn.

**Sự cố:** 🌟 giúp cụ già bị nhốt ngoài trời mưa → cả xóm quý. 😐 nửa đêm gọi gấp. ⚠️ người "quên chìa" không có giấy tờ (từ chối/gọi
công an phường = điểm cao); khách đòi sao chìa nhà người khác (từ chối).

**Nối hệ thống:** rủi ro trộm (`rui.py`; đồ "khóa chống trộm" đã bán) → dịch vụ cho người chơi 🔐 **Thay ổ khóa nhà/tiệm** (giảm nửa
khả năng trộm N ngày); nhà trọ.

Tiền tố `kh_`.

---

### B26. 👓 Tiệm cắt kính "Kính Sáng"

**Kiểu:** Chủ · **Công sức:** S · **Ưu tiên:** P4 · **Tham khảo:** game đo mắt (bảng chữ, thử tròng). Đã có trong đợt nghề 3.

**Vòng chơi:** đo mắt (khách đọc bảng chữ, đổi tròng đến khi rõ) hoặc đọc đơn kính của bác sĩ (cầu, trụ, trục) → đo khoảng cách đồng
tử → chọn gọng hợp mặt và ngân sách → mài tròng, lắp → chỉnh gọng vừa tai.

```
┌──────────────────────────────────┐
│ 👓 Kính Sáng  💰44  ⏰10:00        │
│ 🧾 Bé Bin · lớp 3 · "nhìn bảng mờ" │
│  E  F P  T O Z  (bé đọc đến dòng 4) │
│ Tròng: [-0.5][-0.75 ✓][-1.0]      │
│ [         👓 Chọn gọng            ] │
└──────────────────────────────────┘
```

**Phát triển:** kính cận → kính râm, kính áp tròng → máy đo tự động → phòng khám mắt (nối B3) → chuỗi.

**Kinh tế:** 10–14 xu/cặp (đợt nghề 3).

**Sự cố:** 🌟 bé đeo kính lần đầu nhìn rõ, mẹ cảm động. 😐 mùa tựu trường. ⚠️ học sinh muốn đeo kính "cho ngầu" dù mắt bình thường
(khuyên kính không độ); khách mang đơn trên mạng (đo lại).

**Nối hệ thống:** ngoại hình nhân vật → dịch vụ cho người chơi 👓 **Cắt kính cho nhân vật** (phụ kiện hiển thị, ghi tên thợ);
phòng khám (đơn kính).

Tiền tố `kk_`.

---

## C. Nâng cấp các nghề hiện có

### C1. Góp ý đang chờ (làm trong Đợt 0)

| Góp ý | Nghề | Người chơi xin | Hiện trạng trong code | Đề xuất | Công sức |
|---|---|---|---|---|---|
| **#157** | ☕ Cà phê & bánh | Chiết nhanh hơn, chuẩn hơn | Đã có hàng nút "⚡ 1× 2× 4×" trên màn (nhịp pha và nướng), vạch chuẩn 25–30 giây; nút bị làm mờ khi máy đang chạy | (1) Phụ kiện mới **"Máy pha hẹn giờ"** (mua một lần bằng quỹ nghề): tự dừng ở 28 giây, người chơi vẫn tự bấm bắt đầu; (2) vùng xanh to hơn trên điện thoại; (3) lời nhắc ngắn khi nút nhịp đang mờ ("đổi nhịp sau ly này") | S |
| **#158** | ☕ Cà phê & bánh | Tua nhanh khi làm bánh | Lò dùng chung nhịp 1×/2×/4×, nhưng **không đổi được khi đang có mẻ trong lò** (mẻ giữ nhịp lúc vào lò) | (1) Cho đổi nhịp **giữa mẻ** (phần đã nướng giữ nguyên, phần còn lại chạy nhịp mới); (2) nút **"⏩ Tua tới lúc chín"** khi không có khách nào đang chờ: đồng hồ lò nhảy tới ngay trước vùng chín, người chơi vẫn tự bấm lấy bánh ra | S |
| **#311** | 👕 Shop quần áo | May đo theo số đo | Đã có sửa đồ (lai quần, bóp eo) có bước đo | Loại đơn mới **"📏 Đặt may"**: lấy 4 số đo → chọn kiểu, vải → hẹn ngày thử (đơn nhiều ngày) → thử đồ, chỉnh → giao. Sau này chuyển sâu sang nghề may đo (B16) | M |
| **#355** | 📞 Thư ký | Ghi lời nhắn bằng lựa chọn thay vì gõ | Lời nhắn điện thoại: tên, đơn vị gõ chữ; số gọi lại gõ số; giờ gõ "14:30"; việc gì chọn | Mỗi ô thành **3–4 lựa chọn** nghe na ná nhau: tên (đúng / gần đúng / tên vợ người gọi), số (số sau cùng / số đọc nhầm lúc đầu / số bàn), giờ ("2 giờ rưỡi chiều" → 14:30 / 02:30 / 12:30). Giữ độ khó bằng lựa chọn dễ nhầm; vẫn giữ kiểu gõ cho ai thích (công tắc ở "?") | S |
| **#373** | 🛒 Tạp hóa | Thêm hàng, thêm khách sỉ | 14 mặt hàng; đơn sỉ có báo giá, cọc (đám cưới, quán cơm tấm, công ty dã ngoại) | (1) Thêm **12 mặt hàng** mở theo cấp: gia vị, đồ đông lạnh, đồ cúng rằm, văn phòng phẩm nhỏ, đồ dùng học sinh, đồ cho thú cưng; (2) thêm **khách sỉ** mới: quán ăn vặt (B1), căn tin trường, dãy trọ (B6), xe bánh mì (B11); (3) **bảng giá sỉ** theo số lượng; (4) giao sỉ qua nghề giao hàng | M |
| **#320** | 👩‍🏫 Giáo viên | (nội dung chi tiết không lưu trong repo) | Đã có lớp 1–5 theo cấp nghề, bài theo GDPT 2018, họp phụ huynh, lịch năm học | **Cần đọc lại góp ý gốc** trong hộp góp ý trước khi làm. Đề xuất sẵn nếu góp ý là "thêm nội dung": thêm lớp 6–9 (môn riêng), tiết thao giảng có giám khảo (kiểu khách giám khảo bí mật của Papa's), hội khỏe Phù Đổng | ? |

Ghi chú kỹ thuật:
- #157/#158: `game/careers/cafe_bakery.py` có `PACES = (1, 2, 4)`, lệnh `cb_pace` (bị chặn khi máy bận) và trường `shift` của mỗi khay
  lò (đã dùng để cộng giây khi tính độ chín). "Tua tới lúc chín" và đổi nhịp giữa mẻ có thể làm bằng cách cộng vào `shift` ở máy
  chủ (giới hạn hiện là 0–10 trong `validate`, cần nới), kiểm tra bằng `kit.clock` trong test. Phụ kiện mới thêm vào
  `career_gadgets.py` (như tủ trữ sữa).
- #355: `game/careers/secretary.py` `_phone()`: đổi `kind='text'|'digits'|'time'` thành `kind='pick'` với danh sách sinh từ cùng
  hạt giống (đã có sẵn `_bad_phone`, `alts`, `LATER` làm lựa chọn sai). Giữ save cũ: việc đang dở vẫn chấm theo kiểu cũ.
- #373: thêm item vào `SPEC['inventory']` của `grocery.py` với `unlock` theo cấp; khách sỉ mới vào danh sách đơn sỉ đang có.

### C2. Kế hoạch nâng cấp từng nghề

Đọc bảng: **Giao diện** = làm dễ chơi, đẹp hơn (mượn từ game tham khảo). **Phát triển** = cơ chế còn thiếu. **Sự kiện** = chuyện
mới, ưu tiên chuyện vui. **Mở rộng** = để sau. Mọi nghề cùng được: màn tổng kết ngày v2 (Phần A1) và nhóm sự kiện vui (Phần A3).

#### Ăn uống

| Nghề | Giao diện | Phát triển | Sự kiện mới | Mở rộng sau |
|---|---|---|---|---|
| 🧋 Trà sữa | Combo khi phục vụ liên tiếp; ly lắc có hiệu ứng | Máy dán nắp tự động (nâng cấp nhìn thấy); topping theo mùa | 🌟 Ngày hội trà sữa của phố (đơn đông, tiền boa) | Trà sữa đóng chai bán quầy |
| 🥐 Cà phê & bánh | #157 #158 (C1); bảng điểm từng trạm (pha, sữa, bánh) | Lò thứ 2 nhìn thấy trên bàn; công thức bánh theo mùa | 🌟 Văn phòng đặt hộp bánh họp; 😐 cúp điện sáng (lò ga dự phòng) | Lớp dạy làm bánh |
| 🍜 Mì cay | Hiệu ứng hơi nóng, cấp độ cay bằng thanh 1–7 trực quan | Bếp thứ 2; món mới theo cấp | 🌟 Thử thách "ăn cay cấp 7" (khách quay video) | Mì cay giao đêm |
| 🍲 Phở | Nồi nước dùng có mức nhìn thấy, bọt nổi để hớt | Nồi thứ 2 (phở gà); bàn ngoài vỉa hè | 🌟 Đoàn du khách ăn sáng; 😐 gió mùa (đã có) | Phở cuốn, phở trộn |
| 🍛 Cơm tấm | Khay món dạng lưới (Cooking Fever) | Cơm phần giao văn phòng | 🌟 Công ty đặt 30 phần | Bếp suất ăn công nghiệp (quy mô) |
| 🧊 Trà đá | Ghế nhựa trên sơ đồ vỉa hè (kéo khách vào ghế) | Thêm món: hướng dương, kẹo lạc, nước sấu | 🌟 Bàn cờ tướng thu hút khách quen | Quán nước góc phố có mái |
| 🍦 Kem | Viên kem rơi vào ly có hiệu ứng | Vị theo mùa; xe kem đi lễ hội | 🌟 Bé sinh nhật cả lớp tới ăn | Kem tự làm (máy) |
| 🍳 Nấu cơm gia đình | Bếp nhìn từ trên, nồi chảo có đồng hồ | Thêm nhà khách quen thứ 2 | 🌟 Gia đình mời ăn cùng ngày giỗ | Dạy nấu ăn online |
| 🏫 Căn tin | Tiếng trống đếm ngược to rõ | Bữa trưa bán trú (thực đơn tuần) | 🌟 Hội khỏe Phù Đổng (bán nước) | Hợp đồng nhiều trường |
| 🎉 Nhà hàng tiệc | Sơ đồ bàn tiệc (Diner Dash) cho ca sảnh | Đầu bếp chính: tự lên thực đơn tiệc | 🌟 Tiệc cưới người chơi (đã có dịch vụ) có lời cảm ơn công khai | Tổ chức tiệc ngoài trời |

#### Bán lẻ

| Nghề | Giao diện | Phát triển | Sự kiện mới | Mở rộng sau |
|---|---|---|---|---|
| 🧸 Mẹ & bé | Gói quà kéo giấy, buộc nơ (kéo thả tùy chọn) | Góc đồ sơ sinh theo tuổi; giỏ quà đầy tháng | 🌟 Bà ngoại mua quà cả năm cho cháu | Nối em bé của người chơi (`birth`) |
| 💊 Nhà thuốc | Màn giấy tờ ~70 chữ (đã ghi là ngoại lệ): gập phần đã kiểm | Nhận đơn từ bác sĩ (B3) | 🌟 Phường khen nhà thuốc đạt chuẩn | Giao thuốc tận nhà người già |
| 🛒 Tạp hóa | #373 (C1); kệ hàng nhìn thấy, hàng sắp hết có dấu | Kệ mở theo giấy phép ngành hàng (Supermarket Simulator) | 🌟 Trúng thưởng khuyến mãi của hãng | Minimart 24 giờ |
| 💐 Tiệm hoa | Bó hoa xoay xem 3 góc | Vườn hoa riêng (nối nông trại) | 🌟 Ngày 8/3, 20/10, Valentine kín đơn | Trang trí sự kiện lớn |
| 👕 Quần áo | #311 (C1); phòng thử có màn soi gương | Bộ sưu tập theo mùa | 🌟 Ngày hội giảm giá của phố | Thương hiệu riêng |
| 🐠 Shop thú cưng | Bể cá nhìn thấy, cá bơi | Góc thủy sinh; đồ cho pet hạng S+ của người chơi | 🌟 Hội chợ thú cưng | Nối hệ thú cưng nhiều bậc |
| 🍉 Trái cây | Cân đĩa có kim chạy | Giỏ quà biếu (Tết, Trung thu) | 🌟 Mùa sầu riêng (đông, giá tốt) | Trái cây nhập khẩu |
| 💿 ZPOP | Mở hộp album có hiệu ứng thẻ hiếm | Đặt trước có cọc | 🌟 Fan meeting ở phố | Quầy goods |
| 💍 Tiệm vàng | Bảng giá điện tử chạy chữ | Xưởng kim hoàn: làm nhẫn theo yêu cầu | 🌟 Mùa cưới đặt nhẫn đôi (nối đám cưới) | Kiểm định đá quý cho người chơi |
| 🚗 Đại lý xe | Xe xoay 360° | Showroom thứ 2, xe điện | 🌟 Ra mắt mẫu xe mới | Đua thử xe (nối đường đua) |
| ✏️ Văn phòng phẩm | Danh sách lớp dạng checklist chạm | Máy photo màu, in ảnh | 🌟 Mùa tựu trường | Nối hiệu sách cũ (B8) |

#### Làm đẹp, chăm sóc

| Nghề | Giao diện | Phát triển | Sự kiện mới | Mở rộng sau |
|---|---|---|---|---|
| 💇 Salon tóc | Ảnh trước/sau bằng thanh trượt | Ghế thứ 2 nhìn thấy; học viên | 🌟 Thi tạo mẫu tóc của phố | Chia việc trang điểm với B2 |
| 💅 Nail | Đèn hơ có đồng hồ vòng | Mẫu vẽ móng sưu tập | 🌟 Cô dâu và 4 phù dâu làm móng | Đắp gel chân |
| 🐶 Chăm thú cưng | Bọt xà phòng, nước xả có hiệu ứng | Khách sạn thú cưng (lưu trú qua đêm) | 🌟 Thi "thú cưng đẹp nhất" | Nối pet của người chơi (tắm cho pet người chơi) |
| 📸 Photobooth | Đã tốt; thêm khung theo mùa | Studio ngoài trời | 🌟 Mùa kỷ yếu | Quay phim cưới |
| 🧺 Giặt ủi | Máy giặt có đồng hồ vòng, áo bay khi sấy | Máy công nghiệp; giao nhận | 🌟 Khách sạn ký hợp đồng | Giặt hấp áo dài, rèm |
| 🧹 Giúp việc | Sơ đồ căn hộ, vết bẩn mờ dần (Car Detailing) | Tổ 3 người | 🌟 Chủ nhà để lời cảm ơn và bánh | Tổng vệ sinh Tết |
| 🏠 Nội trợ | Đã có tóm tắt gọn; thêm hình phòng | Ngày giỗ, Tết: nhiều việc | 🌟 Cả nhà tặng quà sinh nhật | Nối nhà của người chơi |
| 👶 Bảo mẫu | Thanh tâm trạng của bé bằng mặt cười | Nhận 2 bé | 🌟 Bé nói "con thương cô" | Nối con của người chơi |

#### Kỹ thuật, sửa chữa

| Nghề | Giao diện | Phát triển | Sự kiện mới | Mở rộng sau |
|---|---|---|---|---|
| 🔧 Sửa đồ | Mở máy kiểu PC Building (linh kiện nhìn thấy, kéo ra lắp vào) | Bàn sửa thứ 2; nối bán máy (B4) | 🌟 Sửa được radio cổ của ông cụ (đồ kỷ niệm) | Sửa tận nhà |
| 🏍️ Sửa xe máy | Xe trên cầu nâng, chạm bộ phận | Cầu nâng thứ 2 (đã có trong 8 bậc) | 🌟 Mùa mưa: cứu xe ngập (đông, khách cảm ơn) | Cứu hộ xe dọc đường |
| 🏎️ Độ xe | Bảng thông số trước/sau nhìn thấy | Đội đua của xưởng | 🌟 Xe khách độ thắng giải đua phố | Giải đua xưởng |
| 🏺 Phục chế | Thanh trượt trước/sau | Kho đồ cổ, đấu giá | 🌟 Bảo tàng phường đặt phục chế | Triển lãm |
| 🚰 Thông cống | Ống nhìn xuyên thấu khi soi camera | Xe hút bể phốt | 🌟 Cứu cả hẻm khỏi ngập sau mưa | Nối thợ điện nước (B15) |
| 🎨 Xưởng vẽ | Vẽ từng lớp có hiệu ứng | Phòng trưng bày | 🌟 Tranh được đấu giá giá cao | Lớp vẽ cho bé |

#### Ngoài trời, lưu trú

| Nghề | Giao diện | Phát triển | Sự kiện mới | Mở rộng sau |
|---|---|---|---|---|
| 🌾 Nông trại | Bảng "⏩ Bấm nhanh" ~97 chữ (đã ghi là cần làm lại): đổi thành sơ đồ ô vườn có icon chín | Nhà kính, chuồng to; lịch mùa (Stardew) | 🌟 Hội chợ nông sản, giải rau to nhất | Nối ao cá (B24) |
| 🛵 Giao hàng | Đã có màn lái; thêm combo giao đúng giờ | Xe điện, thùng giữ lạnh | 🌟 Khách tặng nước giữa trưa nắng | Nối xe ôm (B14) |
| 🗑️ Thu gom rác | Phân loại kéo thả vào ngăn | Xe ép rác, tổ trưởng | 🌟 Ngày hội tái chế: đổi ve chai lấy quà | Điểm tái chế của phố |
| 🏡 Homestay | Sơ đồ phòng (`seatMap`) | Thêm phòng nhìn thấy | 🌟 Khách nước ngoài viết thư cảm ơn | Tour nhỏ kèm phòng |
| 🏨 Khách sạn | Bảng phòng màu (dọn, có khách, hỏng) | Thăng tiến tới quản lý tầng | 🌟 Đoàn khách VIP | Nhà hàng khách sạn |
| 🛎️ Lễ tân | Hành lý kéo vào phòng | Trưởng ca | 🌟 Khách trả phòng tặng quà quê | Nối khách sạn |

#### Văn phòng

| Nghề | Giao diện | Phát triển | Sự kiện mới | Mở rộng sau |
|---|---|---|---|---|
| 📒 Kế toán | Màn ~75 chữ (ngoại lệ đã ghi): thêm thao tác kéo chứng từ vào nhóm | Khách hàng doanh nghiệp | 🌟 Khóa sổ đúng hạn, sếp mời ăn | Kiểm toán |
| 🎧 Chăm sóc KH | Thanh cảm xúc khách gọi tới | Trưởng nhóm | 🌟 Khách khen trên tổng đài | Nối tổng đài cứu hộ |
| 🧾 Kế toán DN / Thuế & lương / Kế toán tập đoàn | Đóng dấu bằng cú chạm giữ (cảm giác "cộp") | Nối chủ tịch tập đoàn (B10) | 🌟 Thưởng cuối năm, tiệc tất niên | Dịch vụ kế toán cho tiệm người chơi |
| 🗂️ Nhân sự | Hồ sơ ứng viên dạng thẻ quẹt | Tuyển cho tiệm của người chơi | 🌟 Ứng viên giỏi bạn giới thiệu | Ngày hội việc làm |
| 📞 Thư ký | #355 (C1) | Thư ký giám đốc cấp cao | 🌟 Sếp tặng hoa ngày 8/3 | Nối chủ tịch tập đoàn |
| 💻 IT | Sơ đồ tủ mạng kéo dây | Quản trị hệ thống | 🌟 Cứu dữ liệu của sếp | Nối quán net (B5) |
| ⚖️ Luật sư | Dòng thời gian kéo thả sự kiện | Văn phòng riêng | 🌟 Thắng vụ hòa giải cho xóm | Tư vấn hợp đồng cho người chơi |
| 🏦 Ngân hàng | Đếm tiền có hiệu ứng | Chuyên viên tín dụng | 🌟 Cụ già gửi tiết kiệm cảm ơn | Nối ngân hàng của người chơi |
| 🔬 Viện nghiên cứu | Ống nghiệm đổi màu | Đề tài nhiều ngày | 🌟 Giống mới được phố trồng | Đã có dịch vụ cho người chơi |

#### Công vụ, an toàn

| Nghề | Giao diện | Phát triển | Sự kiện mới | Mở rộng sau |
|---|---|---|---|---|
| 🚓 Công an phường | Đã gọn (23 chữ) | Đã có cấp hàm; thêm tổ tuần tra đêm | 🌟 Trả lại xe mất cho người dân | Nối ủy ban phường (B9) |
| 🛃 Hải quan | Luồng xanh/vàng/đỏ như đèn giao thông | Đội kiểm soát | 🌟 Phát hiện hàng cấm, được khen | Đã có kiểm kho người chơi |
| 📮 Bưu điện | Cân có kim, kiện hàng bay vào bao | Bưu cục trưởng | 🌟 Thư tay ngày Tết | Nối giao hàng |
| 📚 Thư viện | Kệ sách nhìn thấy | Góc thiếu nhi | 🌟 Ngày hội đọc sách | Nối hiệu sách cũ (B8) |
| 🚨 Cứu hộ tổng đài | Bản đồ phường hiện điểm gọi | Điều phối viên | 🌟 Người được cứu tới cảm ơn | Nối PCCC (B20), bác sĩ (B3) |
| 🏊 Cứu hộ hồ bơi | Sơ đồ 5 khu, người bơi có icon | Dạy bơi cho bé | 🌟 Lớp học bơi hè | Nối gym (B18) |
| 🚦 Gác chắn | Tàu chạy tới có âm thanh CC0 | Trưởng ga | 🌟 Ngày tàu lửa của phố | Nối du lịch |
| 🗼 Hải đăng | Ngọn đèn quay, biển đổi màu theo gió | Trạm thời tiết | 🌟 Thuyền về an toàn bắn pháo sáng cảm ơn | Nối ao cá (B24) |
| 🩺 Điều dưỡng | Đã gọn (19 chữ) | Nối bác sĩ (B3), cùng ca | 🌟 Bệnh nhân xuất viện cảm ơn | Điều dưỡng trưởng khoa |
| 🐾 Thú y | Cân thú, nhiệt kế nhìn thấy | Phòng mổ | 🌟 Cứu chó lạc, tìm được chủ | Đã có dịch vụ cho người chơi |

#### Giáo dục, du lịch, hàng không, nghệ thuật, tâm linh

| Nghề | Giao diện | Phát triển | Sự kiện mới | Mở rộng sau |
|---|---|---|---|---|
| 👩‍🏫 Giáo viên | #320 (C1); sơ đồ lớp, học sinh giơ tay | Lớp 6–9 | 🌟 20/11 học sinh tặng hoa | Dạy thêm |
| 🧳 Hướng dẫn viên | Bản đồ lộ trình kéo điểm dừng | Tour nhiều ngày (đã có) | 🌟 Đoàn khách tặng quà quê | Nối xe ôm/taxi (B14), du lịch nước ngoài (`abroad`) |
| ✈️ Phi công | Đã có màn bay | Đã có văn phòng điều hành | 🌟 Chuyến bay chở đoàn từ thiện | Bay quốc tế |
| 💺 Tiếp viên | Xe đẩy suất ăn đi dọc lối | Tiếp viên trưởng | 🌟 Hành khách nhí tặng tranh | Hạng thương gia |
| 🛢️ Dầu khí | Sơ đồ giàn | Trưởng ca | 🌟 Đợt 14 ngày an toàn tuyệt đối có thưởng | Nối hải đăng |
| 📱 KOL | Khung video dọc, bình luận chạy | Nối các tiệm của người chơi (quay quảng cáo) | 🌟 Video đạt triệu lượt xem | Live bán hàng |
| 🎤 Ca sĩ phòng trà | Sửa lỗi `cs_intro` (Phụ lục 2); thanh nhịp | Đêm nhạc riêng | 🌟 Khán giả xin chữ ký | Nối karaoke (B19), MC (B7) |
| 🎬 Diễn viên | Bảng phân cảnh kiểu truyện tranh | Vai chính | 🌟 Phim chiếu ở hội chợ phố | Lễ trao giải |
| 📻 Đài phát thanh | Bàn trộn âm có thanh trượt | DJ giờ vàng | 🌟 Thính giả gọi tới kể chuyện vui | Nối MC (B7), báo (B22) |
| 🛕 Thầy chùa | Đã gọn | Lễ hội chùa | 🌟 Rằm tháng Giêng đông Phật tử | Đã có Đi chùa |

---

## D. Các đợt triển khai

Thứ tự theo **số lượt người chơi xin × độ dễ làm**. Mỗi đợt là một hoặc vài bản phát hành, deploy khung 04:00–05:00, có popup
"Có gì mới". Mỗi nghề mới đi kèm test, test lùi bản, và nằm ngủ trong save cũ (`DORMANT`) tới khi người chơi chọn.

### Đợt 0: khung chung và nợ góp ý (làm trước)

| Việc | Công sức | Ghi chú |
|---|---|---|
| `seatMap` (sơ đồ chỗ) + `dayWrap` (tổng kết ngày v2) trong `ui-kit.js` | M | Dùng cho Đợt 1–4 |
| Nhóm sự kiện vui (🌟) trong `happenings`: 10 sự kiện chung (review lan truyền, đoàn khách, quà nhà cung cấp…) | M | Cân lại tỉ lệ tốt : xấu ≥ 2 : 1 |
| #157 #158 cà phê, #355 thư ký | S | |
| #373 tạp hóa | M | |
| #311 quần áo "Đặt may" | M | |
| #320 giáo viên: đọc lại góp ý gốc | S | |
| Sửa lỗi `cs_intro` của ca sĩ (Phụ lục 2) | S | |

### Đợt 1: bốn nghề được xin nhiều nhất

| Nghề | Công sức | Lý do xếp ở đây |
|---|---|---|
| 🍢 Ăn vặt vỉa hè (B1) | M | 3 lượt xin; dùng lại phở, trà đá, quầy |
| 💄 Trang điểm & phụ kiện (B2) | M | 4 lượt xin; nối đám cưới, Halloween, ngoại hình |
| 📱 Tiệm điện thoại – laptop (B4) | M | 2 lượt xin; dùng lại tiệm sửa đồ, trả góp |
| 🩺 Bác sĩ (B3) | L | 4 lượt xin; nối rủi ro ốm, điều dưỡng, nhà thuốc |

Nâng cấp nghề cũ đi kèm: nhà thuốc (nhận đơn bác sĩ), salon (trang điểm), sửa đồ (màn mở máy), cà phê, tạp hóa, mì cay.

### Đợt 2: còn lại trong danh sách người chơi xin

| Nghề | Công sức |
|---|---|
| 🖥️ Quán net (B5) | L |
| 🏘️ Chủ nhà trọ (B6) | M |
| 🎙️ MC (B7) | M |
| 📚 Hiệu sách cũ & CLB (B8) | M |

Nâng cấp đi kèm: homestay và khách sạn (sơ đồ phòng), IT (nối quán net), thư viện, văn phòng phẩm, ca sĩ, đài phát thanh, nhà
hàng tiệc (MC cho tiệc cưới).

### Đợt 3: phố phường và đích đến cho người giàu

| Nghề | Công sức |
|---|---|
| 🏛️ Ủy ban phường (B9) | M |
| 🏢 Chủ tịch tập đoàn (B10) | L |
| 🥖 Bánh mì (B11) · 🚿 Rửa xe (B12) · 🅿️ Giữ xe (B13) | S mỗi nghề |
| 🛺 Xe ôm/taxi (B14) | M |
| 🔌 Điện nước (B15) · 🧵 May đo (B16) | M mỗi nghề |

Nâng cấp đi kèm: nông trại (sơ đồ vườn thay bảng Bấm nhanh), giao hàng, kế toán các loại (nối tập đoàn), công an (nối ủy ban),
shop quần áo, thông cống.

### Đợt 4: mở rộng phố

💆 Spa (B17), 🏋️ Gym (B18), 🎤 Karaoke (B19), 🚒 PCCC (B20), 📐 Nội thất (B21), 📰 Báo phường (B22), 🎮 Studio game (B23),
🐟 Ao cá (B24), 🔑 Thợ khóa (B25), 👓 Cắt kính (B26). Có thể chia 2–3 bản. Nâng cấp đi kèm: các nghề còn lại trong bảng C2.

### Để sau

- 🐺 **Ma sói**: chủ game đã hoãn; để sau Đợt 4.
- Nha khoa, khám mắt, nhi (chuyên khoa của phòng khám B3).
- Chơi chung hai người trong một tiệm (kiểu Overcooked).
- Chuỗi liên nghề: ví dụ "phố ẩm thực" gồm ăn vặt + bánh mì + trà đá cùng một khu, có lễ hội riêng.

---

## Phụ lục

### Phụ lục 1. Sự cố hay gặp theo ngành (thư viện để chọn khi làm nghề)

| Ngành | 🌟 Tốt | 😐 Trung tính | ⚠️ Rắc rối (luôn báo trước, có cách phòng) |
|---|---|---|---|
| Ăn uống | Review lan truyền, đoàn khách, đặt tiệc, nhà cung cấp tặng hàng | Giờ cao điểm, mưa, ngày rằm, lễ hội | Hết gas, mất điện, an toàn thực phẩm, giá nguyên liệu tăng, trật tự đô thị |
| Bán lẻ | Hãng thưởng, khách sỉ lớn, mùa lễ | Tựu trường, Tết, khuyến mãi | Hàng giả từ mối rẻ, giao thiếu hàng, quản lý thị trường, trộm vặt |
| Làm đẹp | Cô dâu, KOL ghé, mẫu thử miễn phí | Mùa cưới, kỷ yếu, khách đổi ý | Dị ứng (luôn có bước hỏi), máy/đèn hỏng, phản ánh mạng |
| Sửa chữa, kỹ thuật | Cứu đồ kỷ niệm, hợp đồng định kỳ | Mùa mưa ngập | Linh kiện giả, khách nghi tráo đồ (có ảnh trước), đồ không rõ nguồn gốc |
| Y tế, chăm sóc | Bệnh nhân cảm ơn, báo khen | Mùa cúm, đông bệnh nhân | Đòi thuốc không đơn, máy hỏng, thanh tra hồ sơ |
| Lưu trú, nhà trọ | Khách cũ quay lại, phường khen | Mùa nhập học, mùa du lịch | Chậm tiền, chập điện, kiểm tra tạm trú, khách bỏ đi |
| Quán net, karaoke | Giải đấu, tiệc công ty | Cúp điện theo lịch, nghỉ hè | Khách nhỏ tuổi quá giờ, ồn ào, virus, kiểm tra PCCC |
| Xe, vận chuyển | Trả đồ khách quên, khách quen | Giờ tan tầm, mưa | Cảnh sát giao thông, xe hỏng, khách say |
| Văn phòng, công vụ | Thưởng, thư khen | Cuối năm dồn việc | Phong bì (luôn từ chối được), giấy tờ giả, lộ dữ liệu |
| Ngoài trời, nuôi trồng | Mùa được giá, hội chợ | Thời tiết đổi | Bão (báo trước), mất điện máy sục, sâu bệnh |

Đa số chuyện ⚠️ chung đã có trong `incident_content.py` (130 chuyện) và `happening_content.py` (184 chuyện). Nghề mới chỉ cần
gắn vào đúng nhóm và viết thêm chuyện riêng của nghề.

### Phụ lục 2. Lỗi và điểm lạ phát hiện khi khảo sát

| # | Mức | Mô tả | Cách kiểm | Đề xuất sửa |
|---|---|---|---|---|
| 1 | Nhỏ, có thật | **Ca sĩ phòng trà: nút "Vào việc thôi!" (`cs_intro`) bị đòi mở ca.** Nghề ca sĩ dùng tiền tố `cs_`, trùng tiền tố của nghề Chăm sóc khách hàng. Máy chủ (`engine.py`, dòng kiểm `action.startswith(("shop_","ac_","cs_"))`) và giao diện (`app.js` `SHUT_WORK`) đều bắt mọi lệnh `cs_` phải mở ca, nên lệnh miễn mở ca `cs_intro` của ca sĩ bị từ chối khi ca chưa mở. | Thử local: tạo save mới → chọn nghề `singer` → gửi `cs_intro` khi chưa mở ca → lỗi "Mở ca trước khi xử lý công việc nhé." Cùng thao tác với KOL (`ko_intro`) thì chạy bình thường. | Chỉ áp kiểm `cs_` cho `customer_care` (thêm điều kiện nghề), hoặc đổi tiền tố ca sĩ (cần giữ lệnh cũ cho save đang dở). Sửa cả `SHUT_WORK` ở `app.js`. |
| 2 | Không lỗi hiện tại, dễ gây lỗi sau | **Ba cặp nghề dùng chung tiền tố lệnh:** `rs_` (mì cay và viện nghiên cứu), `fa_` (nông trại và tiếp viên), `dx_` (độ xe và đại lý xe). Tài liệu `PLUGIN_CAREERS.md` yêu cầu tiền tố không trùng. Hiện engine chọn nghề theo `career` của lệnh nên chưa hỏng. | Đọc `SPEC['prefix']` của 65 nghề plugin. | Thêm test "tiền tố không trùng" để nghề mới không trùng nữa; giữ nguyên 3 cặp cũ (đổi sẽ hỏng save đang dở). |
| 3 | Không lỗi | Cả 72 nghề mở ca, nhận việc đầu tiên, kiểm save đều chạy được trên máy local; nghề nào cũng có file giao diện và file test. | Script khảo sát tạm, không đưa vào repo. | — |
| 4 | Ghi chú | Góp ý #320 (giáo viên) không có nội dung trong repo; cần đọc trong hộp góp ý. | Tìm `#320` trong `docs/`, `game/`, `CHANGELOG.md`. | — |

### Phụ lục 3. Ghi chú kỹ thuật chung

- Hợp đồng plugin nghề: `docs/PLUGIN_CAREERS.md`. Bộ bước dùng chung: `game/careers/stepkit.py` + `public/js/careers/slip_kit.js`.
- Bộ giao diện và giới hạn chữ: `docs/UI_KIT.md`, `scripts/check_word_caps.py`.
- Thêm nghề: cuối `ORDER` trong `game/careers/__init__.py`; thêm vào `engine.DORMANT`; `scripts/strip_new_careers.py`; 🔥 x3
  tự thêm nghề mới vào ngày ít nghề nhất mà không xáo tuần đang chạy (`x3_week.py`).
- Dịch vụ cho người chơi: `service_market.register(career, service_id, spec)` (giá NPC × 3, 95 % cho người làm, 5 % đốt), hiệu ứng
  ghi vào save người mua, có trần và công tắc tắt (xem `moto_service.py`, `vet_service.py` làm mẫu).
- Tiền tố gợi ý trong tài liệu này đã kiểm không trùng 65 tiền tố hiện có: `av_ mk_ bs_ dt_ qn_ tro_ mc_ sc_ ub_ bmi_ rx_ gx_ xo_
  dnc_ may_ sp_ gym_ kr_ pccc_ nth_ bao_ gd_ aoc_ kh_ kk_`.
- Mọi số tiền trong tài liệu là mức gốc đề xuất; trước khi phát hành chạy mô phỏng như `docs/CAREER_BALANCE_2.1.0.md` (ngày 1/10/40,
  có và không có nhân viên) để giữ trong khung ở mục 1.3.
