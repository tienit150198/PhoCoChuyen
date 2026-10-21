# Đợt nghề thứ 3 (21/10, chủ game: "tính toán làm thêm nghề khác luôn nhé")

Nguyên tắc chung (giữ như các nghề trước): nghề **làm bằng tay**, mỗi bước có quy trình thật và máy chủ chấm; có tình huống
"oái oăm" kiểu đời thường Việt Nam; không chữ "meta"; nghề mới nằm ngủ trong save tới khi chơi (engine.DORMANT), có trong
scripts/strip_new_careers.py, có test lùi bản. Mỗi nghề phải có ít nhất một **dịch vụ người chơi ↔ người chơi** qua 🛎️ Phố dịch vụ
(service_market.register, giá người chơi mặc định ×3 giá NPC, 95% cho người làm, 5% đốt) và hiệu ứng thật trên save người mua,
có trần, có công tắc tắt.

Mức kinh tế tham chiếu (mỗi ca, nghề cũ): nghề lương 50–72 xu/ca; tiệm tự chủ 8–16 xu lãi / việc, 5–7 việc / ca.

## Danh sách ứng viên

### 1. 🏍️ Tiệm sửa xe máy (moto): **đã làm**
- **Vòng chơi:** mỗi phiếu là một chiếc xe. Nghe khách tả bệnh → chốt lỗi (8 bệnh: thủng săm, quá hạn nhớt, bugi, sên chùng, má phanh, đèn, ắc quy, xe ngập) → chốt 1–2 yêu cầu oái oăm của khách → các bước theo sổ tay (đo, tính, chọn đúng thứ tự) → giao đúng xe theo biển số.
- **Oái oăm:** khách đòi "đề thử" xe vừa lội nước, lắp cầu chì to hơn "cho khỏi đứt", lùi đồng hồ km để bán xe, tháo bộ hạn chế xe 50 phân khối, phụ tùng rẻ không hóa đơn (rồi công an phường ghé hỏi), ba chiếc xe giống hệt chỉ khác biển, chú Hai Lúa nghi tiệm tráo đồ zin…
- **Người chơi ↔ người chơi:** 🔧 Bảo dưỡng xe máy: bơm lốp, thay nhớt, kiểm an toàn cho xe của người chơi khác. Gỡ cảnh báo 🎲 "xe sắp hỏng" và xe ít hỏng vặt (rủi ro chia đôi) trong 10 ngày.
- **Kinh tế:** tiệm (doanh thu – phụ tùng), lãi 9–16 xu / xe + yêu cầu, × chất lượng; dịch vụ người chơi 50 xu NPC → 150 xu.
- **Mở:** chương 2.

### 2. 🩺 Bác sĩ thú y (vet): **đã làm**
- **Vòng chơi:** ở Phòng khám Thú y Cỏ May (phòng khám mà pets.py đã nhắc tới). Mỗi ca một bé: nghe chủ kể → chốt bệnh (8 ca: tiêm phòng, cắt móng, ve, ăn sô-cô-la, parvo, tắc tiểu, nuốt dị vật, triệt sản) → yêu cầu oái oăm của chủ → cân bằng cách trừ (chó: chị Duyên bế lên cân người; mèo: trừ lồng), đo nhiệt, tính liều theo cân, tính dịch truyền, giờ nhịn ăn → trả đúng bé theo phiếu chuồng.
- **Oái oăm:** chủ đòi cho mèo uống paracetamol, bôi tỏi trị ve, cắt tai cắt đuôi cho "đẹp", viết giấy tiêm khống, khách ôm rắn cảnh tới, gà đá đòi "thuốc tăng lực", tủ vắc xin mất điện, ông Sáu hỏi chuyện cho bé Mun đi…
- **Người chơi ↔ người chơi:** 🩺 Khám thú cưng và 💉 Tiêm phòng cho thú cưng của người chơi khác (tương đương khám / tiêm của pets.py: hồi sức khỏe, gia hạn tiêm).
- **Kinh tế:** nghề lương 56–72 xu/ca + thưởng chất lượng 5–9 xu + yêu cầu, mỗi ca khám; dịch vụ 150 / 250 xu NPC → 450 / 750 xu.
- **Mở:** chương 3.

### 3. 🔌 Thợ điện nước
- **Vòng chơi:** đến nhà khách. Dò đường điện bằng bút thử, tính tiết diện dây theo công suất, chọn CB, thay vòi, dò rò nước bằng đồng hồ nước.
- **Oái oăm:** chủ nhà đòi nối dây "tạm" không cần CB, chung cư cúp nước giờ cao điểm, ống âm tường không có bản vẽ, khách đòi "lắp nhanh khỏi xin phép".
- **Người chơi ↔ người chơi:** 🔧 Sửa điện nước nhà người chơi (gỡ rủi ro nhà, +độ bền nội thất trong N ngày).
- **Kinh tế:** tiệm / tự do, 10–14 xu / việc.
- **Mở:** chương 2.

### 4. 🧵 Thợ may đo
- **Vòng chơi:** lấy số đo (vòng ngực, eo, mông, dài tay), cộng chừa đường may, cắt theo rập, may theo thứ tự, thử đồ.
- **Oái oăm:** khách đòi may áo dài trong 1 ngày, khách "sẽ giảm 5 ký trước đám cưới" và đòi may theo số đo đó, vải khách mang tới không đủ khổ.
- **Người chơi ↔ người chơi:** 👗 May đồ cho nhân vật người chơi khác (gắn với tính năng thay trang phục 0.9.5): món đồ "may đo" có tên người may.
- **Kinh tế:** tiệm, 10–15 xu / món; đồ may đo cho người chơi 100 xu NPC.
- **Mở:** chương 2.

### 5. 🚒 Lính cứu hỏa (PCCC)
- **Vòng chơi:** ca trực. Kiểm bình chữa cháy theo kim áp, chọn loại bình đúng đám cháy (A/B/C/điện), lộ trình xe theo hẻm, kiểm tra PCCC tiệm.
- **Oái oăm:** báo cháy giả, chủ tiệm giấu bình gas sau quầy, hẻm quá hẹp xe không vào, khán giả quay video chắn đường.
- **Người chơi ↔ người chơi:** 🧯 Kiểm tra PCCC tiệm của người chơi (giảm rủi ro cháy tiệm N ngày, giấy chứng nhận treo tiệm).
- **Kinh tế:** nghề lương 58–74 xu/ca.
- **Mở:** chương 3.

### 6. 🔑 Thợ khóa
- **Vòng chơi:** xác minh chủ nhà (giấy tờ, hàng xóm) rồi mới mở khóa; đếm chốt khóa, làm chìa theo răng, thay ruột khóa.
- **Oái oăm:** người "quên chìa" mà không có giấy tờ nhà, vợ chồng giận nhau đòi đổi khóa, khách đòi sao chìa nhà người khác.
- **Người chơi ↔ người chơi:** 🔐 Thay ổ khóa nhà / tiệm người chơi (chống trộm trong rủi ro N ngày).
- **Kinh tế:** tiệm nhỏ, 8–12 xu / việc.
- **Mở:** chương 1 (nghề nhập môn).

### 7. 🦷 Phụ tá nha khoa
- **Vòng chơi:** tiệt trùng dụng cụ theo thứ tự, ghi sơ đồ răng (ký hiệu 11–48), pha vật liệu đúng tỉ lệ, dặn sau nhổ răng.
- **Oái oăm:** bệnh nhân sợ khoan bỏ chạy, phụ huynh đòi nhổ hết răng sữa một lần, khách đòi tẩy trắng trong ngày cưới.
- **Người chơi ↔ người chơi:** 😁 Khám răng cho nhân vật (danh hiệu "nụ cười" tạm thời, +hạnh phúc).
- **Kinh tế:** nghề lương 54–70 xu/ca.
- **Mở:** chương 3.

### 8. 👓 Thợ cắt kính
- **Vòng chơi:** đọc đơn kính (cầu, trụ, trục), đo khoảng cách đồng tử, chọn tròng, mài và lắp vào gọng.
- **Oái oăm:** khách mua đơn kính trên mạng, ông cụ đòi đeo lại kính 20 năm trước, học sinh muốn đeo kính "cho ngầu" dù mắt bình thường.
- **Người chơi ↔ người chơi:** 👓 Cắt kính cho nhân vật (phụ kiện hiển thị, ghi tên thợ).
- **Kinh tế:** tiệm, 10–14 xu / cặp.
- **Mở:** chương 2.

### 9. 🔧 Xưởng độ xe Tư Pít-tông (tuning): **đã làm** (2.5.2, người chơi #470 "Thêm độ xe để đua xe")
- **Vòng chơi:** mỗi phiếu là một chiếc xe với mục tiêu (drag / đèo / đi phố / chạy dịch vụ) và ngân sách. Chọn món vừa tiền theo thứ tự ưu tiên của xưởng → lắp đúng quy trình → chạy dyno → đo ồn, khí thải → thẻ thông số → giao đúng xe đúng biển.
- **Đúng luật:** pô thẳng, tháo bầu xúc tác, đèn chớp, biển gập luôn nằm trong phiếu; chọn là phải làm lại, phạt 5 xu, mỗi 3 lần cảnh cáo thì đoàn kiểm tra ghé.
- **Người chơi ↔ người chơi:** ⚙️ độ map động cơ (+3 % mã lực 10 lượt đua), 🔩 chỉnh khung gầm (+4 bám 10 lượt), 🧰 bảo dưỡng xe độ (game/tuning_service.py, docs/SERVICE_MARKET.md).
- **Đường đua Bến Mây** (game/racing.py): độ chính xe của mình 4 dòng × 3 cấp, chạy tính giờ (drag 400 m, đèo Mây Bay) có bảng tuần và danh hiệu, đua tay đôi phí cố định 10 / 20 / 50 xu (người nhanh hơn lấy hũ trừ 20 % đốt). Số liệu đầy đủ trong CHANGELOG v2.5.2.
- **Kinh tế:** tiền công ròng 20–32 xu / xe (trung bình ~27); dịch vụ người chơi 120 / 120 / 80 xu NPC → 360 / 360 / 240 xu.
- **Mở:** chương 2.

## Thứ tự đề xuất
1. **🏍️ Sửa xe máy** và 2. **🩺 Thú y**: làm trước (xong trong đợt này). Cả hai nối vào hệ thống đã có người chơi dùng hằng ngày (🛵 xe trong gara + 🎲 rủi ro "xe sắp hỏng"; 🐾 thú cưng + khám / tiêm), nên dịch vụ người chơi có giá trị ngay mà không cần bảng mới.
3. **🧵 May đo**: đi cùng tính năng thay trang phục đã hứa (0.9.5), người chơi có cái để khoe.
4. **🔌 Điện nước**: gắn với nhà / nội thất (khu trang trí nhà do nhánh khác làm, chờ nhánh đó ổn định).
5. **🚒 Cứu hỏa**: gắn với tiệm của người chơi giàu (rủi ro tiệm).
6. **🔑 Thợ khóa**, 7. **👓 Cắt kính**, 8. **🦷 Nha khoa**: vòng chơi ngắn, làm sau.

## Ghi chú kỹ thuật
- Bộ bước dùng chung: game/careers/stepkit.py (bước chọn, chọn theo thứ tự, chọn nhiều, nhập số, chấm chất lượng, đơn người chơi). Phía máy: public/js/careers/slip_kit.js. Nghề sau dùng lại được.
- Không đổi schema (SCHEMA_VERSION 79 vẫn để dành). Đơn người chơi nằm trong bảng chung service_orders; hiệu ứng ghi vào save người mua.
