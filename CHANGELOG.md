# Unreleased

perf/client (từ 74cfb003): ⚡ đỡ lag phía trình duyệt (chủ game 23/10 "check sửa lại đỡ lag luôn nhé, hiện tại lag lắm"). Không đổi version, không đổi schema, không đổi hình trên máy khỏe. Đo bằng Playwright, màn điện thoại 390×844, CPU chậm 4×, base 74cfb003 → nhánh này (GPU, trung vị 2 lượt): phố 2.5D đi bộ 33 → 60 khung/giây (khung p95 75 → 18 ms), phố đứng yên CPU bận 19 → 12%, cảnh làm việc 2.5D đứng yên 16 → 9%, giao diện cũ cảnh làm việc đứng yên 42 → 60 khung/giây, đi 52 → 57; heap JS ở phố 45 → 21 MB. Không GPU (máy yếu vẽ bằng CPU, trung vị 2 lượt): cảnh làm việc cũ đi bộ 40 → 51 khung/giây, tác vụ dài 19 (1,1 s) → 2 (0,1 s), đứng yên CPU bận 50 → 43%; phố 2.5D gần như không đổi (51–60 khung/giây, trong sai số máy đo). Khởi động (TTI 2,3–3,0 s) không đổi rõ, máy đo đang tải ~40% từ việc khác.
- public/js/perf-mode.js (mới): một công tắc ⚡ máy yếu dùng chung. Bật khi cảnh đo thấy máy vẽ chậm (World.watchCost > 22 ms/khung trên màn nhỏ, phố 2.5D trung bình > 30 ms/khung suốt 120 khung đang chạy) hoặc trình duyệt báo ≤ 2 GB RAM; nhớ 7 ngày (localStorage mnl.perf); `?perf=low|full` để thử. Khi bật: html[data-perf=low] bỏ backdrop-filter (css/app.css), canvas cũ tối đa 1,25× điểm ảnh và vẽ cảnh nền chậm gấp đôi, phố 2.5D giới hạn 30 khung/giây. Máy khỏe không bao giờ thấy.
- Giao diện cũ (world.js, boba-world.js): nhịp vẽ cảnh nền (ambient) giãn theo thời gian vẽ thật (≥ 4× chi phí một khung) thay vì cố định; phòng có đồ động vẽ lại theo chi phí đo được (0,1–0,5 s) thay vì mỗi khung nền; watchCost hạ mật độ điểm ảnh 2 → 1,5 → 1,25 trên màn nhỏ khi khung vẽ quá chậm. scenes/kit.js: fit() nhớ cỡ chữ đã đo (trước đo lại mỗi khung).
- Phố 2.5D (client/isometric/phaser-world.ts, sign-placement.ts): ảnh vẽ từ canvas dùng textures.create thay addCanvas (bỏ getImageData đọc ngược, ~0,2 s mỗi lần dựng phố ở 4×); khoảng cách biển chỉ đường tới đường nhớ theo danh sách đường (đường nóng nhất khi dựng phố, ~0,44 s ở 4×); tìm hộp thoại đang mở dùng danh sách sống getElementsByTagName thay querySelector mỗi khung. Đã build lại public/js/isometric/phaser-world.js.
- Quay lại tab / app: social.js, ticker.js, home-guests.js, workplace-visit.js chỉ đọc lại khi lần đọc trước đã ≥ 30 s (trước đọc lại mọi lần chuyển app): mỗi lần chuyển app 4,8 → 3,2 yêu cầu với khách; tài khoản thật bớt thêm khách ghé nhà và đơn ghé chỗ làm. Giữ nguyên beacon rời trang (thống kê) và kiểm tra bản mới /api/health.
- Không xóa file cũ: đã rà, phần nặng nhất còn lại (whatsnew-data) đã tải lười, không tìm thấy code chết chắc chắn để bỏ; chưa đụng: tải ảnh 2.5D lần đầu (đến 8,3 MB webp, ~150 MB sau giải mã) và 3 lần dựng phố lúc khởi động — để đợt sau.
- Test: tests/perf-mode.mjs, tests/test_perf_mode.py.

# 2.5.4.3 — 23/10/2026

🪽 Cánh vẽ lại to và đẹp hơn (chủ game 23/10 "cánh mua xong ra ngoài xấu quá", "to hơn nhé"), cả bản đồ mới lẫn giao diện cũ: thiên thần lông nhiều lớp, phượng hoàng lông lửa, dơi / rồng màng có xương (rồng gai vảy vàng), tiên hai đôi trong có gân, bướm cánh trước sau có mắt cánh; sải cánh ~1,4–2× đầu chibi, mọc từ bả vai lên ngang đầu; hạng: viền màu B/A, quầng + tia từ S, lấp lánh SS/SSS, viền vàng Huyền thoại; đập nhẹ khi đứng, mạnh khi đi; vẽ một lần mỗi kiểu, dùng chung (feat/wings-v2 3b186310).

# 2.5.4.2 — 23/10/2026

Hotfix: giao diện cũ, cảnh làm việc đen thui chỉ còn đồ đạc và mèo (người chơi Đại lý xe, Android): Chrome xóa bộ nhớ khung vẽ phòng khi chuyển app; boba-world.js vẽ lại phòng khi quay lại trang (visibilitychange), khi khung vẽ báo contextrestored, và vẽ thẳng lên sân khấu khi khung vẽ đang mất (isContextLost).

# 2.5.4.1 — 23/10/2026

Hotfix: 🪽 tab Cánh báo "Thao tác chưa hoàn tất" khi mở Tiệm phụ kiện từ menu (jrAccShop trong v4/journey.js tạo ui.as thiếu wfz → st.wfz.filter lỗi). journey.js khởi tạo đủ wfz / reveal / wtry; acc-shop.js wingShelf chịu được ui.as cũ.

# 2.5.4 — 23/10/2026

feat/pairs-wings (từ origin/main afb38304 = 2.5.3): 🤝 thêm 7 phụ kiện đôi + giá mới, 💞 quan hệ bạn bè, 🪽 cánh có hạng D → Huyền thoại (chủ game 22/10: "tính xem thêm cánh cho người dùng nhé, cánh sẽ buff cho người chơi khi đánh pet", "cánh này là làm đẹp cho người dùng nhé, với tăng tiền kiếm được nữa", "cho nâng nữa, nâng lên như thú đi", "mua thì mặc định D hoặc C ngẫu nhiên", "cho cánh đẹp tí, có cả mode cũ và mode mới đều hiển thị được nhé"). Schema 89 → 90 (chỉ thêm bảng friend_bonds, wing_worn). Save: khóa mới journey['wings'] (2.5.3 giữ nguyên, không đọc). Có gì mới 2.5.4.

## 🤝 Phụ kiện đôi
- Giá tăng 50% (chủ game 22/10 "giá như này rẻ quá, tăng nhẹ tí nữa"): Chí cốt 220 → 330, Bạn thân 175 → 265, Tri kỉ 130 → 200 xu. Lý do ghi trong docstring game/friend_charms_content.py: giá cũ chỉ bằng nửa ngày công người chơi trung vị (≈ 170 xu/ngày đo 21/10, ≈ 250 với 📈 thu nhập tăng thêm), rẻ hơn cái mũ len; nay xếp ba bậc theo quan hệ mở được: 165–220 xu (khoảng một ngày), 265–330 (ngày rưỡi), 440–570 (hai ngày công, ngang nhẫn vàng 24K). Một cặp mua một lần cho hai người.
- 7 cặp mới, mỗi cặp một chỗ riêng trên nhân vật (vẽ ở v4/look.js paintPlayer / paintPairs, chibi 2.5D ở isometric/character-art.js): 🧶 Chỉ đỏ (vòng tay, 165 xu), ⭐ Đồng đội (huy hiệu ngực, 175), 🧸 Gấu bông (ngồi trên vai, 220), 🎈 Bay cao (bóng bay trái tim buộc cổ tay, 285), 🪭 Tri âm (quạt giấy cầm tay, 310), 💞 Nửa trái tim (dây chuyền, 440), 🟢 Kết nghĩa (ngọc bội đeo hông, 570). Giá sau chỉ số giá.
- Mỗi cặp có `step` 1–3 (mức thân), dùng để mở quan hệ.

## 💞 Quan hệ
- 6 nhãn, không phân biệt giới: 💛 Bạn thân, 🤜 Cạ cứng (mọi cặp), 🔥 Chí cốt (cặp mức 2 trở lên hoặc Chí cốt), 💐 Tri kỉ (Tri kỉ, Nửa trái tim, Kết nghĩa), 🐉 Anh em kết nghĩa, 🌸 Chị em kết nghĩa (Nửa trái tim, Kết nghĩa). Mặc định 🤝 Bạn bè.
- Mở khi hai bạn cùng có một cặp `paired` hợp nhãn. Một người hỏi (charm_bond), người kia đồng ý (charm_bond_answer); cả hai cùng hỏi một nhãn là thành luôn. Mỗi hai người một nhãn, đổi được (nhãn cũ giữ tới khi bạn kia đồng ý nhãn mới), một bên bỏ về Bạn bè được (charm_bond_off). Hủy kết bạn hoặc chặn thì xóa luôn.
- Hiện ở: danh sách bạn bè (marriage.js), "Đang có" ở Tiệm phụ kiện và thẻ Phụ kiện đôi (charms.js, nút đặt / đổi / bỏ, lời mời đang chờ), thẻ người chơi trên phố cũ (walk.js) và bản đồ 2.5D (isometric-social.js, live/town_social.py, live/street.py `rel`).
- Bảng friend_bonds(lo, hi, label, charm, at, ask, ask_by, ask_charm, ask_at), schema 90.

## 🪽 Cánh
- game/wings.py, game/wings_content.py: 6 kiểu (chỉ là dáng): 🦋 bướm 8.800, 🧚 tiên 13.200, 🦇 dơi 16.500, 🪽 thiên thần 24.000, 🐉 rồng 36.000, 🔥 phượng hoàng 54.000 xu. 8 hạng D, C, B, A, S, SS, SSS, Huyền thoại; hạng quyết định mọi thứ.
- Mua: server quay hạng D (70%) hoặc C (30%); `rid` của yêu cầu: gửi lại trả đúng cánh đã ra, không trừ tiền lần hai. Đôi đầu tiên tự đeo. Có màn mở hộp nhỏ.
- Ghép: y hệt thú (game/pet_tiers.py): ba đôi bất kỳ, đôi chính giữ kiểu; phí theo hạng thấp nhất 500 / 2.000 / 10.000 / 50.000 / 300.000 / 20 triệu / 200 triệu; tỉ lệ 60 / 45 / 30 / 15 / 10 / 15% (+3% mỗi bậc chênh), ba SSS ra Huyền thoại 15% (từ S dễ hơn thú, phí cao hơn: chủ game 22/10 "Huyền thoại 5-10 tỷ là hợp lý"; trung bình từ kiểu rẻ nhất: S ≈ 1 triệu, SS ≈ 25 triệu, SSS ≈ 450 triệu, Huyền thoại ≈ 7 tỷ); trượt dưới S giữ cả ba, từ S mất hai đôi phụ. Không hiện tỉ lệ.
- Tiền kiếm được: +2 / 4 / 6 / 8 / 11 / 15 / 20 / 25% tiền làm việc của chính mình (cùng gốc với phần của thú: việc xong, lương ngày, TT99, hoa hồng; không tính đơn nhân viên, quầy, quà), tối đa 40k / 100k / 300k / 800k / 2 triệu / 6 triệu / 16 triệu / 30 triệu xu một ngày (chủ game 22/10: "trần/ngày tăng lên nữa", "SSS được 20%", "tối đa đó gấp đôi đi"), chỉ chế độ câu chuyện. Dòng riêng "🪽 Cánh …" (other_income), không tính vào gốc 🔥 x3, 📈 income_boost nhân dòng đó đúng một lần như mọi dòng thưởng: các khoản thưởng cộng nhau, không nhân chồng.
- Đấu thú: +1 / 1 / 2 / 2 / 3 / 4 / 5 / 6% máu và sức đánh cho thú của người đeo (snapshot `wg`, game/pet_battle.py derive). Mô phỏng 3.000 trận mỗi mức: +6% thắng ~62% cùng hạng, thú hơn một hạng thắng 74–78%, và vẫn thắng ~58–66% trước thú kém một hạng đeo cánh Huyền thoại: cánh không bao giờ hơn một hạng thú. ENGINE 1 không đổi; trận có cánh lưu engine 2 (2.5.3 chỉ hiện kết quả đã lưu, không phát lại).
- Hình: public/js/v4/wings-art.js, lông vũ / màng cánh nhiều lớp, gradient, viền tối, vỗ nhẹ ở cảnh nơi làm việc; từ C viền màu hạng, từ S hào quang, từ SS lấp lánh, SSS cầu vồng, Huyền thoại vàng rực. Vẽ ở cả giao diện cũ (gương tủ đồ, phố cũ, cảnh làm việc, chân dung) và 2.5D (chibi: sau lưng khi quay mặt, trên lưng khi quay đi; người khác thấy qua live/wings.py `wg`, bảng wing_worn schema 90). Đã build lại public/js/isometric/phaser-world.js.
- Cánh động (chủ game 22/10: "cánh có hoạt họa, có tia sáng này kia nhé"): cánh vỗ liên tục quanh gốc vai, hai bên đối xứng, mỗi kiểu một nhịp (bướm 1,3 s, tiên 1,5 s, phượng 1,8 s, thiên thần 2 s, dơi 2,4 s, rồng 2,6 s, rồng / dơi vỗ chậm và nặng hơn); hạt sáng lấp lánh bay ra khỏi cánh ở mọi hạng (2–3 hạt D–A, 5–6 từ S, 8–9 ở SSS / Huyền thoại); từ S có hào quang thở và tia sáng xoay chậm sau lưng; SSS / Huyền thoại thêm vòng sáng tỏa ra mỗi 2,6 s kèm chùm hạt vàng (SSS cầu vồng). Cùng một bộ số (v4/wings-art.js flapAt, wingMotes, raysAt, burstAt) cho mọi nơi:
  - giao diện cũ: phố đi dạo (v4/walk.js vẽ cánh tách khỏi hình người, cánh lấy từ vài khung vỗ đã vẽ sẵn dùng chung, hạt trước người; khi có cánh trong khung hình, phố vẽ lại ~15 khung/giây thay vì 8, không thêm vòng lặp mới), cảnh nơi làm việc (boba-world.js), Tiệm phụ kiện, tủ đồ, gương (SVG tự chạy bằng SMIL, không có script mỗi khung; chân dung tròn giữ yên);
  - 2.5D: client/isometric/wing-rigs.ts, chibi vẽ không cánh, cánh là ảnh riêng (khung vỗ, hào quang, tia, vòng, hạt dùng lại ảnh có sẵn, không vẽ canvas mỗi khung); cảnh vẫn ngủ khi đứng yên, chỉ đánh thức một khung ~15 lần/giây khi có cánh động trong tầm nhìn; tối đa 8 người có cánh động (mình trước, rồi người gần nhất), còn lại cánh đứng yên, tối đa 48 hạt; trên xe cánh đứng yên. Các đảo khác (đảo riêng, đảo bang) giữ cánh tĩnh trong hình chibi.
  - Giảm chuyển động (cài đặt, html / body .reduce-motion, prefers-reduced-motion): cánh đứng yên, hào quang / tia đứng yên, không hạt bay, không vòng sáng.
- Tiệm phụ kiện có tab 🪽 Cánh: thử trước gương, mua, tủ cánh có huy hiệu hạng, chọn ba đôi để ghép, bảng hạng được gì. Tủ đồ có thẻ cánh đang đeo.

## 🛠️ Sửa lỗi
- 👗 Thời trang, Thay đồ ma-nơ-canh: nút áo / áo khoác / giày không còn bị co méo (class nhóm của nút đổi g-* → cg-*, trùng với hình ma-nơ-canh).
- 🛠️ Thiết bị tăng tốc (feedback #498): save có nhiều nơi làm việc có nhân viên luôn còn đơn cũ, mua thiết bị báo "Còn đơn cũ đang chốt tiền" mãi; giờ chốt riêng đơn của nơi đó rồi lắp (workplace_business.settle(only=)).
- 🏦 Giao dịch viên (feedback #495): bước "Tiền quầy phải có" hiện lại sổ giao dịch trong ngày.
- ♿ Văn phòng phẩm / Căn tin (feedback #497, người chơi khiếm thị): dòng đọc cho trình đọc màn hình (khách cần gì, kết quả giao, khách tiếp theo), focus tự tới bước kế tiếp; thẻ giới thiệu street_kit là region thay vì dialog.

- 🗺️ Bản đồ mới: kéo / zoom bản đồ xong, nhân vật đi lại (chạm đất, chạm nhà, phím, cần điều khiển) thì camera đi theo lại như bản đồ cũ, giữ mức zoom đã chọn (trước phải bấm 🧭 Về giữa; người chơi: "move nhân vật mà cam không đi theo"). Toàn cảnh đảo giữ nguyên.

## Kiểm thử
- tests/test_wings.py (mới), tests/test_wings_live.py (mới), tests/wings-art.mjs (mới); tests/test_friend_charms.py thêm Bonds (quan hệ), giá và danh sách mới; tests/friend-charms.mjs. tests/wings-art.mjs thêm: nhịp từng kiểu, hạt / tia / vòng theo hạng, SVG tự động (SMIL) và giảm chuyển động, phố cũ và 2.5D vẽ cánh tách rời; tests/isometric-vehicles.mjs có withWings.
- RollbackTo253: save có cánh qua 2.5.3 (git archive afb38304) validate / migrate / qua ngày rồi về lại nguyên vẹn; trận không cánh phát lại giống hệt 2.5.3.

# 2.5.3.1 — 23/10/2026

Hotfix: 🚗 Đại lý xe không nhập được Xe mui trần cổ (người chơi trên Cả phố: "xe mui trần 1 chiếc không nhập được", "10 chiếc cũng hong nhập dc"). game/inventory.py validate giữ trần 10.000 xu một đơn vị cho đơn nhập và lô hàng, thấp hơn giá hãng của mui trần (~12.936 xu, qua Bãi xe gần phố ~17.464 xu): đơn bị từ chối "Số lượng không hợp lệ.". Trần giờ là giá đơn vị cao nhất mà nhà cung cấp nào cũng có thể tính (không dưới 10.000). tests/test_career_car_dealer.py DearCars.

# 2.5.3 — 22/10/2026

Gộp feat/careers-253 (💍 jewelry, 🚗 car_dealer, 🍱 canteen, ✏️ stationery: 72 nghề), feat/friend-accessories (🤝 phụ kiện đôi + 🛍️ Tiệm phụ kiện Hạt Cườm, schema 86 friend_charms), feat/bank-loan-tiers (💳 vay / thẻ khi nhập hàng thiếu tiền, 🐷 hạng tiết kiệm tới 100 tỷ, lãi +0 / 1,5 / 3 / 4 / 5 %), feat/gov-redeem-cop-179 (👮 xóa kỷ luật sau 15 ngày tốt, 🚔 báo công an sửa, biển 179), feat/econ-1022 (📈 thu nhập tăng thêm theo tài sản game/income_boost.py: dưới 50 triệu +50%, 50–200 triệu +40%, 200 triệu–1 tỷ +30%, từ 1 tỷ +20%, Chợ đen +3 điểm thắng), fix/ios-keyboard (public/js/typing-tap.js, popup chờ khi đang gõ), feat/archive-pack (🗄️ schema 89 archive_packed + scripts/archive_pack.py). Schema 84 → 89 (85, 87, 88 không dùng). Có gì mới 2.5.3.

## feat/careers-253

🍱 Căn tin trường Tiểu học Phố Mây (`canteen`) và ✏️ Tiệm văn phòng phẩm Bút Mây (`stationery`): người chơi #482 "bán căn tin trường học", #483 "tiệm văn phòng phẩm"; chủ game 22/10 "UI như kiểu của trà sữa, show hết ra người ta chọn như game bán hàng ấy, cho mở toàn bộ game nhé". Nhánh gồm cả merge feat/careers-luxury-biz (💍 jewelry, 🚗 car_dealer) lên 2.5.2.4: 72 nghề. Không đổi schema (không bảng mới), không thêm khóa save ngoài careers.<id>; cả hai DORMANT, LATE_UNLOCKS 1 (mở cho mọi người từ chương 1, vào `unlocked` khi đã làm). Chưa thêm mục Có gì mới (chờ chủ game).
- game/careers/counterkit.py (mới): quầy bán chung kiểu trà sữa. Một khách = một việc: `needs` thuần theo (ngày, lượt) gồm các dòng (`any` × `qty`), `budget` (tiền tiêu vặt), `avoid` (dị ứng / ăn chay), `sample` (lưu mẫu). Người chơi chạm hàng bỏ vào khay (tối đa 60 món, mỗi chạm ≤ 20), bấm Giao; server chấm: thiếu / dư / khách không hỏi / vượt tiền / dính món kiêng thì giữ khay để sửa, ghi lỗi một lần mỗi loại, trừ chất lượng; đúng thì hàng rời kệ (FIFO, giá vốn ghi `cogs`), dịch vụ trừ vật tư, khách trả giá niêm yết (cố định). Khách giờ cao điểm (`bell`) về lớp khi trống đánh (task 'referred', không tiền), trừ ca êm và mấy khách đầu. Có 🎓 chứng chỉ: +2 xu mỗi lượt. Client không thấy hàng nào trả lời dòng nào.
- canteen: sáng (lượt 0–3) bán đồ ăn sáng trước trống 7 giờ; ra chơi (lượt 4–7) nước, ăn vặt, mua giùm bạn; trưa (lượt 8–11, từ ngày 2) cô / thầy chủ nhiệm đặt N phần cơm (cơm, rau, canh, món mặn; bạn ăn chay lấy đậu hũ), phải 🧪 Lưu mẫu (một lần mỗi ngày) trước phần đầu tiên. Hỏi dị ứng (sữa, đậu phộng; trưa có bạn dị ứng cá), ngày ăn chay, tiền tiêu vặt.
- stationery: khách lẻ, học sinh có tiền tiêu vặt, phụ huynh đọc danh sách lớp (từ ngày 2: "vở" là vở ô li cho lớp 1–5, vở kẻ ngang từ lớp 6; từ ngày 4 thường kèm bọc vở + dán nhãn, mỗi quyển một tờ giấy bọc, một nhãn), vở nhà mang tới bọc (từ ngày 4), photo đề cương / hồ sơ tính theo lượt 10 trang (mỗi lượt một xấp A4). Dịch vụ chờ vật tư: hết giấy A4 thì không photo.
- Sự cố trên quầy (DESK) chặn quầy tới khi chọn, chứng chỉ canteen_basics / stationery_basics, câu chuyện, gói chuyên môn, ngày êm / đông (MODS), danh hiệu c_canteen / c_stationery.
- Đăng ký: careers ORDER (+2 cuối), engine.DORMANT, journey LATE_UNLOCKS + danh hiệu, career_stories, career_competition_content, certificate_content, coach, guide_content, career_scale_content (72 nghề, nhóm Bán lẻ, catalog §67–68), career_specialism_content, build_id, incident / tip / life / promotion / review_aspects / lb_titles, work_gear, workplace_business, inventory SUPPLIERS, live/street_data, town_layout (2 lô), x3 (tự động).
- Client: public/js/careers/counter_kit.js (mới, quầy chung: lưới hàng theo nhóm với số tồn, +1 / −1 / +5, khay, bong bóng khách, trống trường) + canteen.js, stationery.js, css; isometric (mặt tiền, nội thất căn tin / tiệm), danh sách nghề, từ vựng, tutorial, vinh danh, hội chợ, icon. Bundle isometric build lại, docs/qa/isometric-feature-parity.json cập nhật.
- Rollback: về 2.5.2.4 (d4eb098b) an toàn với save chưa làm hai nghề; save đã làm: `scripts/strip_new_careers.py strip --careers canteen,stationery` (gỡ cả chứng chỉ canteen_basics / stationery_basics), `restore` khi lên lại (tests/test_counter_careers_compat.py).
- i18n/overrides.json: ~1.430 chuỗi + ~180 mẫu (câu khách sinh ra, lời chấm, nhãn quầy); tests/counter-careers-ui.mjs dịch mọi dòng hiện trên quầy 30 ngày qua v4/i18n.js.
- Tests: tests/test_career_canteen.py, test_career_stationery.py, test_counter_careers_i18n.py, test_counter_careers_compat.py, counter-careers-ui.mjs; số nghề trong các test đếm lên 72 (test_capacity_catalog hết lỗi 40 != 36 có sẵn trên main).
# Chưa phát hành — feat/remote-close

📲 F#456 "khi làm ở nước ngoài thì có nút để đóng các cửa tiệm luôn": chủ đồng ý, nhưng phải mua mới có. Không đổi schema, không thêm khóa save mới (món đồ nằm trong journey.gadgets.own như mọi món ở Mây Mobile).
- game/gadgets.py: tab mới 📲 Tiện ích, món 📲 Máy quản lý từ xa (quan_ly_xa) 5.500 xu (giá gốc 5.000 + chỉ số 10 %), mua một lần, bán lại 65 % như đồ công nghệ khác; không hiện trên thẻ khoe (show_view chỉ lấy tab đồ công nghệ).
- game/remote_close.py + game/engine.py: end_day {remote: true} trên nghề cần khép = đúng nhánh end_day ở tiệm (lương, điện nước, kho, sự cố, ngày sống, x3, thăng tiến, điểm bang ở storage). Khác duy nhất: giữ s['current'] (không nhảy cảnh) và không kiểm "bỏ dở việc" nơi đang đứng. Chuyện đang dở mang sang mai như nút Khép ca (carry_event). Chưa có máy: từ chối 'need_device', không đổi gì; ca đã khép: trả lời êm (duplicate), không đổi gì.
- game/journey.py: public journey.remote {own, item, shops[{career, day, done, left, event, here}]}, chỉ có khi đang mở ca hoặc đã có máy.
- public/js/v4/remote-close.js (mới): bảng 📲 Đóng ca từ xa; app.js: mục menu (chỉ khi có ca mở ở nơi khác), journey.js: dòng trên trang Hành trình, abroad.js: nút đóng ca từ xa trong "Còn N ca đang mở" và thẻ du học; chưa có máy thì ghi rõ mua gì, ở đâu. gadgets.js: tab Tiện ích.
- Có gì mới 2.5.2, Hướng dẫn → Mở ca và khép ca +1 dòng, i18n/overrides.json: 23 câu + 12 mẫu.
- Rollback 2.5.1 an toàn: validator cũ giữ id lạ trong gadgets.own (ẩn đi), bỏ qua cờ remote.
# Chưa phát hành — feat/deco-tap-place

♿ Góp ý #443 (người chơi dùng trình đọc màn hình, chủ game duyệt): bày trí phòng bằng chạm chọn rồi chạm chỗ đặt, không cần kéo thả. Cùng lệnh jr_deco_put / jr_deco_buy / jr_deco_pick như kéo thả: không đổi schema, không thêm khóa save.
- public/js/v4/reno.js: chạm một món (thẻ trong túi / cửa hàng, hoặc món đã bày) là chọn: viền chọn, aria-pressed, vùng đọc `.dc-live` (một vùng aria-live ngoài phần vẽ lại) đọc "Đã chọn …, hàng 2 cột 3. Chạm chỗ muốn đặt."; chạm chỗ trống trong phòng là đặt / dời tới đó (đồ nhỏ chạm lên bàn, kệ thì lên đó); chạm lại món đó hoặc ✕ Bỏ chọn / Esc là thôi. Món đã ghim không dời.
- Mỗi ô trong vùng đặt của món đang chọn là một `<button>` thật có tên ("hàng 1 cột 4, trống", "…, có ghế đẩu", "…, vướng cửa ra vào", "…, đang ở đây"): trong suốt đè lên hình phòng 2D (ngón tay vẫn chạm hình bên dưới), dạng bản đồ ô nhỏ dưới cảnh 3D. Ô không đặt được bấm vào thì đọc lý do.
- Món đang chọn có ⬅️⬆️⬇️➡️ dời từng ô (vướng cửa / cửa sổ thì nhảy tới ô trống kế tiếp; sát mép thì báo), ✕ Bỏ chọn, 📍 Đặt lên bàn / kệ cho đồ nhỏ. Tên món trong phòng kèm vị trí. Món bị TalkBack / Switch Access bấm (click không có ngón tay trước) cũng chọn được.
- Tiêu điểm: nút đang giữ tiêu điểm bị vẽ lại / tạm khóa khi đang gửi lệnh thì trả tiêu điểm về đúng nút đó; nút biến mất (✕ Bỏ chọn, thẻ cuối cùng, Cất túi) thì về món đồ / căn phòng. Ô nhập chữ không bao giờ bị lấy lại tiêu điểm.
- Dòng thông báo (bk-flash) không còn là vùng aria-live riêng: render() đọc nó qua `.dc-live` (cùng một câu lần sau vẫn được đọc). Thanh món đang cầm là nhóm có tên thay vì role=status.
- public/css/reno.css: ô đè, bản đồ ô 3D, nút bước 44 px. Đảo riêng / đảo bang / gian hàng hội chợ dùng trình sửa khác (ô dựng cố định), không đổi.
- Có gì mới 2.5.2 (một dòng ♿), game.__version__ 2.5.2. i18n/overrides.json: 19 chuỗi, 25 mẫu.
- Tests: tests/deco_tap_place.mjs, tests/test_deco_tap_place.py; scripts/browser_deco_tap.py (390x844, cảm ứng).
# Chưa phát hành — feat/hotel-homestay-distinct

🏡🛎️ F#466 "homestay và khách sạn không khác gì cả". Homestay = nhà năm phòng của bạn; khách sạn Sông Mây = bạn làm thuê theo ca, quy trình, đồng đội. Không đổi schema; hotel: khóa task mới tùy chọn (t0, fast), homestay: khóa task mới tùy chọn (tea).
- game/careers/hotel.py + hotel_content.py: bộ sinh việc 2 (GEN 2) cho lễ tân và buồng phòng. Lễ tân = "Quầy giờ cao điểm": 4 khách cùng lúc (VIP → Anh Khôi quản lý trực, trưởng đoàn đại lý → Tú quầy đoàn), xếp thứ tự theo giờ cần xong, chỉ giao phòng "Sạch · đã kiểm" trên bảng 16 phòng 6 trạng thái, cài thẻ, phàn nàn theo quy trình. Buồng phòng = "Bảng phòng": dọn trước phòng của khách sắp đến, khóa phòng hỏng (OOO), chia phòng bẩn cho tổ theo tầng (Chị Hoa / Chị Lụa), kiểm phòng, báo số phòng bán được. Giao ban đầu ca (công suất, lượt đến, VIP, đoàn). Chấm cả tốc độ: đúng hết trong thời gian chuẩn (TARGET 120–180 giây) = "Nhanh", +1 xu (FAST_BONUS). Lương ngày 52–66 xu và thưởng 5–7 xu/việc giữ nguyên.
- Việc hotel tạo trước (gen 1) dời created_turn sang dải legacy (heal_save) nên vẫn dựng lại đúng như cũ; 4 việc còn lại (giặt là, bữa sáng, bảo trì, trang trí) giữ nguyên nội dung.
- game/careers/homestay.py: 🫖 Trà ở hiên sau khi trao chìa (hs_tea): chọn chuyện hợp người khách → tâm trạng +8 (sai +2), một lần mỗi lượt nhận phòng. Không đổi giá, không đổi tiền.
- Mô tả chọn nghề: "Homestay nhà mình" / "Nhân viên khách sạn"; hướng dẫn, coach, Có gì mới 2.5.2.
- public/js/careers/hotel.js + hotel.css: hàng chờ ở quầy, bảng tình trạng phòng theo tầng (đổi ngay khi khóa phòng / ký kiểm), khách đến hôm nay + tổ buồng, ⏱️ chuẩn N giây. homestay.js + homestay.css: thẻ trà ở hiên.
- i18n/overrides.json: ~130 câu + ~25 mẫu.
# Chưa phát hành — feat/wedding-life

💍 Đời sống vợ chồng phase 1 (góp ý #442, #444; chủ game 21/10 "có đi thật luôn nhé, có chụp ảnh này kia luôn, thuê máy bay du thuyền gì đó"). Kế hoạch: docs/WEDDING_LIFE_PLAN.md. Schema 83 (bảng mới wl_rites, wl_trips, wl_photos, wl_chores; 81–82 để trống), không thêm khóa save.
- game/wedding_life.py + wedding_life_content.py: 🧺 lễ rước dâu + lễ gia tiên 6 bước hai người lần lượt chọn (đính hôn đã chốt kế hoạch hoặc đã cưới; miễn phí nếu kế hoạch có gia tiên, chưa có thì phí gia tiên + mâm quả 5/7/9 theo giá ăn hỏi, hoãn / hết hạn 3 ngày / ly hôn hoàn đúng một lần). ✈️ chuyến đi 11 nơi (6 trong nước, 4 nước ngoài, đảo riêng), vé / thuê máy bay / thuê du thuyền / máy bay, du thuyền nhà mình (xăng = giá thuê ÷ 10), trả bằng quỹ chung / chia đôi / mình bao; tiền giữ tới khi người kia bấm đi, từ chối / hủy / 48 giờ / ly hôn hoàn đúng nơi đã trả. Mỗi ngày một người chọn, chuyện bất ngờ, ảnh đôi (dữ liệu vẽ của photo_studio). 🏠 việc nhà, đi chợ, nấu cơm, chăm con mỗi ngày (+hạnh phúc, +1 tinh thần, không ra tiền).
- game/marriage.py (hành động wl_*, view.life), game/couple.py (ly hôn: hoàn tiền chuyến đi trước khi chia quỹ), live/wedding.py + wedfeast.js (MC kể lễ rước dâu cho khách), portrait-art.js (chú thích ảnh), public/js/v4/wedlife.js + marriage.js (tab 🏠 Sống chung / 🧺 Lễ gia tiên), marriage.css.
- Có gì mới 2.5.2 (4 dòng, chưa nâng game.__version__), Hướng dẫn "Lễ rước dâu, đi chơi, sống chung", i18n/overrides.json.
# Chưa phát hành — feat/careers-kol (2.5.2)

📱🎤🎬 Ba nghề mới (chủ game "nghề mới thì làm đi, làm KOL này kia luôn"; người chơi #471 "diễn viên, đi hát", #472 "làm diễn viên ca sĩ"). Cả ba chấm theo từng bước (game/careers/stepkit.py, giao diện slip_kit), ngủ yên tới khi làm (engine.DORMANT), có trong scripts/strip_new_careers.py; không đổi schema, không thêm khóa save. 64 → 67 nghề.
- 📱 kol, Studio Hẻm Xanh (chủ studio, chương 2, prefix ko_): 8 loại hợp đồng (review món ăn, đập hộp, hướng dẫn nấu món, livestream bán hàng, review chỗ nghỉ, giới thiệu ứng dụng, quay khai trương, video tuyên truyền của phường), 9–11 bước: đọc brief chốt dạng nội dung → yêu cầu oái oăm của nhãn hàng (ghi rõ quảng cáo, không đánh giá khống, không giục mua giả) → câu mở đầu, trình tự, xử lý lúc quay, số món theo phút live / số cảnh, nhạc miễn phí bản quyền, thứ tự dựng, giờ đăng, bình luận, tỉ lệ tương tác / chốt đơn, nội dung báo cáo → gửi đúng mã hợp đồng. Cát-xê 15–24 xu mỗi hợp đồng, nhân theo chất lượng (tối thiểu 5), không lương; chứng chỉ kol_basics (hire=False) +1 xu; tăng tiền công nhóm LOW. 15 yêu cầu oái oăm, 15 chuyện giữa việc (app vay tiền, mua người theo dõi ảo, giữ tiền quyên góp… có dấu quay lại).
- 🎤 singer, Phòng trà Mây Chiều (lương 54–70, chương 2, prefix cs_): 8 kiểu lượt hát (bolero, nhạc xưa, tình ca, acoustic, dân ca, mừng sinh nhật, cha-cha-cha, jazz), 7–11 bước: nhìn khán phòng → khách dặn điều oái oăm → khởi động đúng thứ tự → chọn bài trong sổ hợp âm (không hát bài chưa xin phép) → thử âm → phút còn lại, giấy xin bài → sự cố trên sân khấu → hết lượt → đọc lời chúc đúng bàn, đúng tên. Thưởng 6–9 xu mỗi lượt, nhân theo chất lượng (tối thiểu 3); tăng tiền công LOW. 12 yêu cầu, 12 chuyện (hát nhép có dấu quay lại).
- 🎬 actor, Hãng phim Bến Mây, phim "Ngõ Nhỏ Có Nắng" (lương 58–76, chương 3, prefix dn_): 8 loại cảnh (cãi nhau, chia tay, đoàn tụ, hồi hộp, hành động, diễn với diễn viên nhí, dưới mưa, buổi ra mắt phim), 6–10 bước: đọc trang kịch bản → đoàn phim dặn điều oái oăm (an toàn trước, không tin đồn) → thoại đúng thứ tự, đứng đúng dấu, nối cảnh, nghe đạo diễn, đếm lượt quay còn lại, tập cảnh hành động an toàn (hoặc phát biểu, trả lời báo chí, chọn ảnh được đăng) → trả trang phục đúng móc. Thưởng 7–10 xu mỗi cảnh, nhân theo chất lượng (tối thiểu 3); tăng tiền công MID. 12 yêu cầu, 12 chuyện (lộ kịch bản có dấu quay lại).
- Đủ bộ như moto/vet: chứng chỉ, chuyện nghề 5 hồi + kỷ vật, danh hiệu, thăng chức, gói chuyên môn (10 bậc), thi đua, quy mô (kol nhóm nghệ thuật, singer/actor phụ cấp cơ quan), mẹo, đánh giá, đồ nghề, hướng dẫn ngày đầu, coach, lô đất ở khu hội chợ, nhà và phòng làm việc 2.5D (biển điện thoại, micro, bảng clapper), hình phiếu (điện thoại, sân khấu, bảng clapper), x3 thu nhập tự xoay. Có gì mới 2.5.2: 3 dòng.
- i18n/overrides.json: ~2.300 chuỗi + 34 mẫu. Lùi bản: bản cũ từ chối save đã làm các nghề này; chạy `scripts/strip_new_careers.py strip --careers kol,singer,actor --archive …` rồi `restore` với cùng archive khi lên lại.
- tests: test_career_kol/singer/actor, test_kol_singer_actor_compat (2.5.1, b0159d84), test_kol_singer_actor_i18n, tests/kol-ui.mjs (390×844); đếm nghề 64 → 67. tests/isometric-feature-parity.mjs: thêm stub seedHween/hwNow (trên main đang lỗi), danh mục tiện ích bỏ ev2010 đã đóng (68 → 67).

# Chưa phát hành — feat/career-tuning (2.5.2)

🔧 Người chơi #470 "Thêm độ xe để đua xe đi ad ơi", chủ game 22/10 "độ xe này kia làm kĩ vào nhé". SCHEMA_VERSION 84 (bảng mới race_runs, race_duels; 83 là 💍 đời sống vợ chồng), khóa save tùy chọn journey.tune. Có gì mới 2.5.2: 3 dòng.
- Nghề mới 🔧 Xưởng độ xe Tư Pít-tông (tuning, mở ở chương 2): phiếu độ có mục tiêu (drag / đèo / đi phố / chạy dịch vụ) và ngân sách, bảng độ chọn món vừa tiền theo thứ tự ưu tiên của xưởng, lắp đúng quy trình, chạy dyno, đo ồn / khí thải, thẻ thông số thật, giao đúng xe đúng biển. Luật: món trái luật (pô thẳng, tháo bầu xúc tác, đèn chớp, biển gập) luôn có trong phiếu để thử; chọn là phải làm lại, phạt 5 xu, mỗi 3 lần cảnh cáo thì đoàn kiểm tra ghé. Tiền công ròng 20–32 xu mỗi xe (trung bình ~27), phụ tùng 9–56 xu xưởng ứng trước, khách trả khi nhận xe; chứng chỉ "Độ xe đúng luật cơ bản" bớt 2 xu phụ tùng.
- 🏁 Đường đua Bến Mây (game/racing.py, public/js/v4/race-track.js, mở từ 🚗 Nhà xe): độ chính xe của mình ở Xưởng Tư Pít-tông, 4 dòng × 3 cấp (⚙️ động cơ, 🔩 khung gầm, 🛑 phanh, 🛞 lốp), giá mỗi cấp 4 / 9 / 16 % giá xe, sàn xe máy 40 / 90 / 160 xu, ô tô 120 / 270 / 480 xu, làm tròn 10 xu (tiền vào xưởng, không vào ai). Mỗi lượt đua làm mòn đồ (lốp 10, phanh 6, động cơ 3, khung 2; trượt bánh / bốc khói thêm 3 mòn lốp), đồ mòn còn 40 % + 60 % × độ mới; 🧰 bảo dưỡng 25 % giá trị phần đã mòn (tối thiểu 10 xu). Chỉ xe máy và ô tô (cả bản giới hạn theo xe gốc); xe đạp, thuyền, máy bay không đua; xe đang hỏng không độ, không đua.
- Đua tất định: drag 400 m (đề-pa êm / vừa / mạnh theo chỉ số bám đề-pa, ba lần sang số) và đèo Mây Bay (5 khúc cua, điểm phanh sớm / vừa / muộn theo độ chắc), may mắn ±0,4 % gieo theo mã lượt chạy; mỗi lượt lưu đủ đầu vào để xem lại y hệt. Sổ tay đường đua nói rõ luật chọn.
- ⏱️ Chạy tính giờ: phí sân 5 xu (drag) / 8 xu (đèo), đốt hết; tối đa 20 lượt một ngày; bảng tuần theo đường đua × hạng xe (4 bảng), mỗi người tính lượt nhanh nhất; top 1 / top 2–3 giữ danh hiệu tuần (lb_titles race_drag_bike, race_drag_car, race_deo_bike, race_deo_car), chốt sáng thứ Hai như Đấu trường.
- ⚔️ Đua tay đôi (không đồng bộ): phí cố định 10 / 20 / 50 xu, người thách chạy trước và phí được giữ; người nhận cùng hạng xe, chỉ số đua chênh ≤ 20 %; người nhanh hơn nhận 2 × phí − 20 % (đốt), hòa hoàn đủ; không ai nhận trong 24 giờ hoặc hủy thì hoàn đủ. Không cược ngoài phí. Chặn: tài khoản ≥ 3 ngày, không cùng mạng (svc_net / lì xì / đấu trường), không bị chặn, không tự đua, cùng hai người ≤ 2 trận một ngày, mỗi người nhận ≤ 10 trận một ngày, mở ≤ 3 lời thách; phí tính vào hạn mức chuyển tiền của tài khoản mới (bank_xfer.count_out). Kill switch MNL_RACE_OFF=1 (lời thách đang mở vẫn hủy / hết hạn được).
- 🛎️ Phố dịch vụ, Thợ độ xe là người chơi (game/tuning_service.py): ⚙️ độ map động cơ (+3 % mã lực 10 lượt đua, giá gốc 120 xu), 🔩 chỉnh khung gầm (+4 bám 10 lượt, 120 xu), 🧰 bảo dưỡng xe độ (mọi món mới lại, 80 xu); thợ làm 3 bước ở xưởng (dx_svc) rồi mới giao được. Kill switch MNL_TUNING_SVC_OFF=1.
- Máy chủ: POST /api/race/home|trial|challenge|accept|cancel|replay (light route, 60 thao tác / phút, 10 lượt chạy / phút), housekeeping trả lời thách đấu quá hạn. Lệnh jr_tune_buy / jr_tune_fix qua journey.action.
- Quay lui an toàn: 2.5.1 không đọc race_runs / race_duels và giữ nguyên journey.tune (validate cho phép khóa lạ); tiền phí đã trừ / đã trả nằm trong ví như dòng 'life'; lời thách đang mở khi quay lui nằm chờ tới khi bản này chạy lại (hết hạn thì hoàn).
- i18n/overrides.json: tiếng Anh cho nghề, đường đua, dịch vụ, thông báo.
- Gộp vào 2.5.2 (integ/2.5.2-tuning): lô 🔧 trên đảo dời sang (-20,5; 26,5) vì trùng đúng lô 📱 KOL (-6; 8); dòng Động cơ dùng ⚙️ thay 💻 (đường đua, dịch vụ độ map, hướng dẫn), 🔩 cho Khung gầm. Đếm nghề 68.

# Chưa phát hành — feat/careers-luxury-biz (2.5.2)

💍 Tiệm vàng Ngọc Mây (`jewelry`, chương 2) và 🚗 Đại lý xe Phố Mây (`car_dealer`, chương 2): người chơi #472 "làm chủ bán vàng, kim cương, xe hơi, xe máy"; chủ game 21/10 "nghề mới thì làm đi". Không đổi schema (không bảng mới), không thêm khóa save ngoài journey.xe_care đã có; cả hai DORMANT, LATE_UNLOCKS 2. Nhóm tăng tiền công: mặc định MID. Có gì mới 2.5.2: 2 dòng.
- jewelry: sáng mở két (đếm két, đối sổ giao ca, kiểm cân bằng quả cân chuẩn, treo giá mua vào / bán ra 9999); chưa mở thì không phục vụ khách (shop_closed). Khách: bán nữ trang (lấy món, cân phân, tiền vàng theo bảng hôm nay, hóa đơn, giao món; món rời tủ ngay, giá vốn ghi trên phiếu), mua lại vàng cũ (CCCD, quét tuổi, cân trừ đá, trừ 3% hàng tiệm khác, sổ mua hàng; đồ mạ và người bán không rõ nguồn gốc bị từ chối), kiểm định kim cương 4C (từ ngày 3; đá giả moissanite từ ngày 25). Bảng giá `board(day)` thuần: giá giữa REF 520 xu/chỉ dao động ±3,4%, bán +1,2%, mua −1,2%. Vàng mua lại chuyển công ty ngay trong ngày theo giá giữa: tiệm không giữ vàng, không đầu cơ được, không mua bán vàng giữa người chơi. Lời mỗi lượt ≈ 13–60 xu (tiền công + chênh lệch), mua lại ≈ 7–30 xu, kiểm định 30 xu (+2 xu nếu có 🎓 chứng chỉ jewelry_basics). Hết hàng: "Hết hàng, hẹn khách" (vg_out, không tiền).
- car_dealer: sáng nhận lô xe (đối số khung, PDI năm bước, niêm yết bảng giá). Khách: bán xe (chọn xe hợp nhu cầu, nói thật thông số, lái thử, tổng tiền gồm trước bạ 2% / 10% và biển số 5 / 20 xu nộp hộ, không tính vào thu nhập; trả góp qua Ngân hàng Phố: trả trước ≥ 30%, vay ≤ 5.000 xu, góp ≤ 40% thu nhập, đại lý không cho nợ; hồ sơ đăng ký, biển số, giao xe), thu xe cũ (giấy tờ, trừ 10%/năm tối thiểu 30%, trừ tiền sửa; bãi xe cũ mua lại 106% cùng ngày), bảo hành / bảo dưỡng (20 xu, +2 xu có 🎓 car_dealer_basics), phụ kiện. Lời bán xe máy 17–55 xu + phí đăng ký 15, ô tô 99–264 + 40. Cả hai tiệm: nhà cung cấp chính hãng (partner, giá niêm yết) + giao gấp (express, ×1,35), không giá sỉ, không mặc cả (inventory `firm`); kệ chứa 80 như mọi tiệm. Người chơi mua xe cho mình ở 🚗 Xe & phương tiện (garage), không mua qua đại lý.
- game/dealer_service.py: 🛎️ Phố dịch vụ 🚗 Bảo dưỡng ô tô (bao_duong_oto, giá NPC 120, 1 xe/đơn, ba bước dx_svc, giao khi đã xong trong svc_ok; gỡ cảnh báo "xe sắp hỏng" của ô tô, ô tô bớt hỏng 10 ngày). Tắt: MNL_DEALER_SVC_OFF=1. moto_service.bikes/apply nhận nhóm xe ('bike' mặc định).
- Đăng ký: careers ORDER (+2 cuối), engine.DORMANT, journey LATE_UNLOCKS + danh hiệu c_jewelry / c_car_dealer, career_stories ARCS, career_competition_content, certificate_content, coach, guide_content, career_scale_content (66 nghề, nhóm Bán lẻ), career_specialism_content (+2 gói), build_id, incident / tip / life / promotion / review_aspects / lb_titles, work_gear, workplace_business, inventory SUPPLIERS, service_market, town_layout (2 lô khu biệt thự), x3 (tự động).
- Client: public/js/careers/jewelry.js, car_dealer.js + css; bảng giá ▲/▼ so hôm qua, nút Kho, "🔑 Mua xe cho mình" mở garage; isometric (mặt tiền nhẫn / ô tô, nội thất), danh sách nghề, từ vựng, tutorial, vinh danh, hội chợ, Phố dịch vụ. Bundle isometric build lại.
- Rollback: về 2.5.1 (b0159d84) an toàn với save chưa làm hai nghề; save đã làm: `scripts/strip_new_careers.py strip --careers jewelry,car_dealer` (gỡ cả chứng chỉ jewelry_basics / car_dealer_basics), `restore` khi lên lại. Trước rollback: MNL_DEALER_SVC_OFF=1 cho khỏi nhận đơn mới, rồi hoàn tiền các đơn bao_duong_oto còn mở (2.5.1 không biết dịch vụ này).
- i18n/overrides.json: 1.449 chuỗi + 35 mẫu.

# Chưa phát hành — fix/fb-money-2110

🏦 F#462 "giao dịch lớn hơn 10tr đều không được" + 🥛 F#463/#454 sữa tươi hỏng giữa ca. Không đổi schema, không thêm khóa save.
- game/bank.py: nộp / rút ATM / gửi và rút sổ không kỳ hạn / trả thẻ "số khác": mỗi lần tối đa 1.000.000.000 xu (TX_MAX, trước 10.000.000 = AMOUNT_MAX). Sổ có kỳ hạn giữ 10.000.000 xu mỗi sổ (TERM_MAX, rules.term_max; báo "Sổ có kỳ hạn tối đa 10.000.000 xu mỗi sổ.": không đổi kinh tế tiền gửi khi chủ game chưa duyệt). Quá mức báo "Mỗi lần tối đa … xu." thay vì "ít nhất 1 xu". Dòng Sổ ví tách ≤ 10 triệu/dòng (journey.validate mọi bản). Chặn trước khi vượt BAL_MAX / WALLET_MAX (tài khoản, sổ không kỳ hạn, ví, tất toán sớm). AMOUNT_MAX (pay(), vay, thuê nhà, validator) và RENEW_MAX (tái tục 10 triệu) giữ nguyên. rules.tx_max cho client.
- game/invest.py: sổ tiết kiệm 📈 gửi / rút mỗi lần tới 1 tỷ (lệnh coin, dự án giữ 10 triệu); _wallet tách dòng ≤ 10 triệu (cũng sửa "Tất cả" / bán coin trên 10 triệu từng bị validator từ chối).
- game/journey.py: Góp vốn (jr_invest) mỗi lần tới FUND_MAX 1 tỷ (trước CAPITAL_MAX 100 triệu).
- public/js/v4/bank.js: số quá rules.tx_max báo ngay "Mỗi lần tối đa … xu." (server cũ: 10 triệu).
- cafe_bakery: "Ca sữa tươi vừa mở có mùi chua" giảm nửa lần nữa: SOUR_KEEP 0,6 → 0,3 (~14 % → ~7 % số ngày), có 🧊 Tủ trữ sữa riêng 0,15 → 0,08 (~3,6 % → ~1,9 %). Lô sữa hỏng lộ ra ngay lúc mở ca (at = 0, on_start mở chuyện), không còn bật giữa ca sau khi nướng bánh.
- i18n/overrides.json: 8 mẫu.

# Chưa phát hành — career previews

🧾 Món đang làm hiện ra dần, như ly trà sữa (chủ game 21/10: "chỗ Ly trà sữa đó cập nhật cho các nghề khác tương tự được luôn đi"). Chỉ đổi giao diện: không đổi chấm điểm, tiền công, save hay schema.
- ui-kit `buildUp` + `withArt` (app.css 27f, lớp `ck-k-<loại>`): khay, rổ, túi, đĩa, tô, nồi, hộp, ly, ốc quế, bàn thợ, giấy, quầy tiền; món đã bỏ vào rơi xuống, món khách còn chờ là bóng xám, món khách không gọi viền đỏ. street_kit `person(x,t,inner,tag,art)` vẽ hình bên cạnh phiếu khách; slip_kit `stepsArt` cho nghề chấm theo bước.
- Trà đá: khay mang ra (cốc có đá / không đá, đồ ăn vặt). Kem: ly / ốc quế / trái dừa / hộp với từng viên kem, topping. Cơm tấm: dĩa hoặc hộp (cơm, món tủ kính, ốp la, mỡ hành, nước mắm, canh). Nấu cơm: mâm thực đơn → giỏ đi chợ → mâm cơm, món chín đặt lên mâm.
- Hoa: bó hoa đúng dáng khách đặt, từng cành, giấy gói và nơ đổi màu theo lựa chọn. Quần áo: ma-nơ-canh mặc dần từng món đúng màu / họa tiết, đơn online là thùng hàng. Trái cây: rổ trái cây, quả dập / sai độ chín viền đỏ. Cửa hàng thú cưng: túi đồ, thùng gửi, bể cá đầy nước dần. Chăm thú cưng: bàn tắm với từng dịch vụ, bát ăn theo gam.
- Nông trại: thùng carton / túi giấy đầy dần, nhãn hữu cơ. Giặt ủi: rổ → giá phơi → túi, từng món theo chất liệu, màu, vết bẩn. Sửa chữa: món đồ trên bàn thợ, từng bộ phận thay xong, ✅ khi chạy thử đạt. Nội trợ: giỏ / khay / hộp theo việc.
- Lễ tân (hồ sơ khách), giao dịch viên (giao dịch), phục chế (đồ trên bàn thợ), nghiên cứu (khay mẫu), đài phát thanh (kịch bản lên sóng), sửa xe (xe trên bàn sửa), thú y (khay khám): một mảnh cho mỗi bước, bước đang làm viền màu nghề.
- Quán ăn và tiệm cà phê / bánh kem đã có hình từ đợt trước (tô, ly, bánh kem). Không có nghề nhà thuốc trong game nên không làm.
- i18n/overrides.json: 18 chuỗi + 6 mẫu (nhãn đọc màn hình).

# v2.5.1 — 2026-10-22

feat/careers-batch-3: 🏍️ Tiệm sửa xe Út Lanh (moto, chương 2) và 🩺 Phòng khám Thú y Cỏ May (vet, chương 3), dịch vụ Phố dịch vụ 🔧 bảo dưỡng xe, 🩺 khám, 💉 tiêm; không đổi schema (79 để trống), khóa save tùy chọn journey.xe_care; moto vào nhóm tăng tiền công LOW (+20%), vet MID. Có gì mới 2.5.1: 2 dòng.
# v2.5.0.1 — 2026-10-21

💐 Hotfix (chủ game 21/10 "viết thiệp giờ login vào vẫn bị thông báo đó, xóa đi"): public/js/isometric/town-utilities.js EV2010_UNTIL còn 21/10 23:59:59 nên thẻ Thiệp 20/10 giữa màn hình, thẻ ở Hành trình và lối vào trong Tiện ích vẫn hiện dù máy chủ đã đóng viết từ 20/10 23:59:59 (MNL_2010_UNTIL). Nay EV2010_UNTIL = 20/10 23:59:59; trang /2010 vẫn mở đọc thiệp bằng link tới hết 25/10. Không có dòng Có gì mới.

# v2.5.0 — 2026-10-21

Bản gộp lớn (khung 4–5h): careers-integ (5 nghề mới, Phố dịch vụ, phòng sinh, phòng khách sạn, hội chợ việc làm, dịch vụ cưới, chụp ảnh), hướng dẫn coach cho nghề mới, quầy chuỗi (trần thuê/điện, phí chuỗi không trừ thưởng lãi), đấu giá +50 món, Halloween 26–31/10 (schema 80), trang trí +55 món, nhà đảo + bang, thân thiết NPC, màn làm việc dễ nhìn, tiền công +8–20% và Tuần lễ tay nghề 22–28/10 (MNL_PAYWEEK_FROM/UNTIL). Có gì mới 2.5.0: 14 dòng.

## quầy chuỗi

🌸 Quầy chuỗi bớt nặng (chủ game 21/10, người chơi báo "quầy hoa bán còn nửa giá"; không có mục Có gì mới, chưa tăng phiên bản). Giá bán từng món không đổi; từ 20/10 phí chuỗi của 2.4.52/2.4.53 (`dea74703`, `d846233f`) làm một chuỗi ki-ốt hoa 64 quầy mất ~40% phần chủ nhận, chuỗi tốc độ thường thì lỗ, vì mỗi xu thuê/điện/thuế tăng thêm còn kéo thưởng lãi nhân viên 236% xuống theo (mất ~3,36 xu).
- Phần chuỗi (tiền thuê và điện trên mức gốc, các điểm thuế chuỗi trên 7%) vẫn trừ đủ vào két nhưng không còn trừ vào lãi tính thưởng: thưởng lãi tính đúng như trước 20/10 (giá vốn, thuê/điện gốc, thuế 7%). game/quay_business.py: `_charge` ghi phần gốc vào `profit_boost.costs` và `income_tax.loss`, `income_tax_parts` tách thuế gốc / thuế chuỗi, mỗi phần có số lẻ riêng (khóa tùy chọn `business.chain_carry` {rent, power, tax}; bản cũ bỏ qua khóa lạ); đơn của khách là người chơi (player_service_tasks.credit_visit) cũng vậy.
- Bậc thang mềm hơn: tiền thuê × n/10 dừng ở ×1,5 (RENT_MAX = 15 quầy), điện × n/5 dừng ở ×2 (POWER_MAX = 10 quầy). Thuế chuỗi giữ nguyên (+2…+20 điểm trên 5…50 quầy). Màn quầy hiện "tiền thuê ×…, điện ×…" theo mức đã chặn.
- Một ki-ốt hoa bán lan 25 xu, 3 nhân viên, một ngày thật (phần chủ nhận sau giá vốn, xu; % so với trước 20/10):

| Số quầy | Tốc độ thường (6.939 lượt/ngày): 2.4.71 | Bản này | Tốc độ nhanh (34.697 lượt/ngày): 2.4.71 | Bản này |
|---|---|---|---|---|
| trước 20/10 | 168.780 | 168.780 | 1.122.897 | 1.122.897 |
| 6 | 163.830 (97%) | 167.268 (99%) | 1.097.429 (98%) | 1.115.278 (99%) |
| 11 | 149.063 (88%) | 162.912 (97%) | 1.051.880 (94%) | 1.101.762 (98%) |
| 21 | 100.438 (60%) | 156.179 (93%) | 951.957 (85%) | 1.079.762 (96%) |
| 31 | 56.652 (34%) | 153.478 (91%) | 856.869 (76%) | 1.061.795 (95%) |
| 51 | −7.191 | 150.777 (89%) | 731.303 (65%) | 1.043.827 (93%) |
| 64 | −25.911 | 150.777 (89%) | 685.385 (61%) | 1.043.827 (93%) |

- Mọi nghề quầy, mọi chỗ (xe, sạp, ki-ốt), bảng món mặc định, tốc độ thường, 6…64 quầy: thấp nhất 75% (quần áo ki-ốt/sạp), trái cây 78%, còn lại ≥ 82% (2.4.71: quần áo ki-ốt 25%, trà đá xe lỗ). Chuỗi 64 ki-ốt hoa tốc độ nhanh: phí chuỗi ≈ 5,1 triệu/ngày (2.4.71: ≈ 28 triệu).
- tests/test_quay_chain_bonus.py (thưởng bằng đúng trước 20/10, chuỗi ≤ 5 quầy không đổi từng xu, thuế tách không làm tròn mất, ≥ 70% mọi nghề ở 64 quầy, kiểm tra khóa chain_carry); tests/test_wealth_fee.py theo mức chặn mới.
## npc-goodwill

💛 Thân thiết với NPC: lấy lòng hàng xóm và khách quen giờ có lợi thật (chủ game 21/10: "để mọi người biết sự quan trọng của việc lấy lòng NPC", "lấy lòng NPC thì kinh doanh được nhiều tiền hơn… hoặc là sẽ được mở thêm gì đó mà mọi người k biết"). Xây trên Điểm thân quen có sẵn (game/closeness.py: điểm 0–100, 5 bậc, trò chuyện, quà, lời mời, đánh giá, nhạt dần sau 14 ngày); luật mới ở game/goodwill.py + game/goodwill_content.py. Không đổi phiên bản, chưa có dòng Có gì mới.
- 💼 Khách ruột trả thêm (engine.task_done → goodwill.pay_bonus): xong việc cho khách Người quen +2%, Thân thiết +4%, Như người nhà +6%; hỏi thăm/tặng quà trong 7 ngày gần đây +2%; 📜 bí kíp bà Sáu +2% ở quán ăn/quán nước; 🤝 khách sộp được giới thiệu +10%. Tối đa 10% tiền công một việc (tính trên phần lời với tiệm bán hàng, như đồ nghề), 200 xu một việc, 1.000 xu một ngày Việt Nam cho cả bản lưu, chỉ trong ngày có thưởng theo giờ thật (interest_clock.day_paid), không áp cho đơn người chơi; vào quỹ nơi làm, danh mục 'revenue'.
- 🏘️ Hàng xóm: bà Tám bớt 10%/20% tiền phòng khi còn ở gác (journey.living_cost → goodwill.living), cô Ba bán quà ngoài phố rẻ 10%/20%; mỗi người một việc giúp mỗi tuần (qn_favour, 7 ngày Việt Nam): bữa cơm bà Tám (tinh thần +5), gói quà quê cô Ba và rổ rau bà Sáu (một món vào túi quà), tiệc tổ cô Lụa (cả hẻm +1, tinh thần +3), bài giới thiệu anh Khoa (3 khách sộp), ấm trà chú Tư (tỉnh táo +20), sân thượng Bé Tí (tinh thần +6).
- 🔒 Mở khóa ẩn (hiện "🔒 ???" tới khi đạt, chữ không gửi xuống máy khách trước đó): hũ me ngào dưới quầy cô Ba (Như người nhà: món quà riêng, +2 thân quen), sân thượng bí mật của Bé Tí, bí kíp gia truyền bà Sáu, bài đăng của anh Khoa, danh xưng "Người tốt của tổ" (cô Lụa) và "Cả hẻm thương" (cả 7 hàng xóm Thân thiết), khách Như người nhà giới thiệu khách sộp mỗi tuần khi hỏi thăm, 📖 Chuyện riêng của từng hàng xóm (Như người nhà + giúp 3 việc nhờ). Khi mở, người đó nhắn một câu vào 💌 Lời nhắn (dòng 'care' có sẵn), menu 👥 có chấm ✨ tới khi mở bảng (qn_gw_seen).
- 📝 Việc nhờ mỗi ngày Việt Nam: một người quen nhờ mua giúp một loại quà (theo sở thích, hợp trẻ nhỏ); tặng món đúng loại là xong, +3. 🎂 Sinh nhật (hàng xóm cố định, khách theo id; thấy ngày từ Người quen): quà đúng ngày tính gấp đôi, một lần mỗi ngày.
- ⏱️ Giới hạn: trò chuyện + tặng quà cộng tối đa 12 điểm cho một người mỗi ngày Việt Nam (ngày sống vẫn kết thúc nhanh được, ngày thật thì không); đã đủ thì món quà bị từ chối trước khi trả tiền, trò chuyện chỉ nhận một câu "đã vui lắm rồi"; điểm trừ không bị chặn.
- 👥 Người quen: thẻ hướng dẫn lần đầu (game/coach/people.py → coach-content.js "features", ghi nhớ bằng notesSeen "gw1"), mục 💛 Thân thiết hôm nay (việc nhờ, sinh nhật, khách sộp, danh xưng), 💼 +x% trên từng dòng, trang mỗi người có 💛 Thân thiết được gì (bậc, đang có, bậc sau, 🔒 ???), nút việc giúp hằng tuần, 📖 Chuyện riêng, giá quà cô Ba và món "📝 đúng việc nhờ". Hướng dẫn 📖 mục Thân thiết với hàng xóm thêm 3 dòng.
- Bản lưu: chỉ khóa tùy chọn journey.npcgw (bản 2.4.72 giữ nguyên, không đọc: journey cho phép khóa thêm; tests/test_goodwill.py chạy thật bản 2.4.72 83fe229c). Không thêm khóa vào journey.closeness, không danh hiệu mới trong journey.titles, không loại hộp thư/món túi quà/danh mục sổ thu chi mới. Không bảng mới, không đổi SCHEMA_VERSION.
- Công tắc MNL_NPCGW_OFF=1: tắt mọi ưu đãi, ngừng điểm mới (việc nhờ, sinh nhật, mở khóa, việc giúp, khách sộp), bỏ giới hạn 12 điểm (luật cũ); khối dữ liệu giữ nguyên, bật lại là chạy tiếp.
- Kiểm thử: tests/test_goodwill.py; scripts/browser_goodwill.py (390×844, 1280×800).
## career-ui

🧭 Màn làm việc từng nghề dễ hiểu hơn (chủ game 21/10: "coi UI sắp xếp cho dễ hiểu ở từng nghề… button sắp xếp cũng khó nhìn… show hết thông tin ra xong người ta chọn, kiểu show trà sữa, các loại hoa xong ruy băng"). Chỉ đổi giao diện: máy chủ chấm điểm, trả tiền như cũ; không khóa save mới, không đổi schema, không đổi phiên bản, chưa có dòng Có gì mới.
- Thanh nút dưới cùng (mọi nghề dùng .ui-bar, cả 2 giao diện): trên điện thoại bước tiếp theo nằm một dòng riêng, nút chính một mình cả hàng (cao 50 px), không còn bị ép 40–62% bề ngang rồi xuống 2–3 dòng chữ; dòng báo kết quả (barNote) thành dòng nhạt có vạch màu nghề, không còn là ô tối trông như nút bấm.
- Bộ ghép chung mới trong ui-kit.js (app.css 27f): slip ("🧾 Phiếu khách": từng phần khách gọi thành một dòng chữ thường, ✓ đúng / ✗ sai / ! cần chỉnh / ○ chưa làm), steps (các bước đánh số, bước đang làm tô màu nghề, chạm để nhảy tới khu đó), secHead (tiêu đề đánh số cho từng khu trên bảng chọn).
- 🧋 Trà sữa (giao diện gọn): phiếu khách theo thứ tự pha (Ly · Trà · Siro · Topping · Đá · Đường) thay cho hàng chip phải vuốt ngang; ly đang pha nằm cạnh phiếu ("Ly của bạn": trà rót dâng lên, đá và trân châu rơi vào); thanh bước 1 Ly → 2 Trà → (Siro) → (Topping) → Đá·đường → Nắp → Giao; mọi quầy mở hết thành một bảng chọn, mỗi khu đánh số như bước của nó, khu khách không gọi ghi "khách không gọi"; món đã chọn viền màu nghề có dấu ✓. Sửa lỗi cũ: thanh nút của trà sữa mang lớp .mt-bar trùng tên thanh kiên nhẫn (display:block, cao 8px) nên nút bị lệch nửa hàng; nay là .mt-cta. Bỏ nút "Nghe gọi món" trùng trong bong bóng khi thanh nút đã có; bỏ câu "Pha xong trà, đá, đường…" lặp hai lần ở giao diện đầy đủ.
- 💐 Tiệm hoa (giao diện gọn): thẻ khách + hàng chip "Khách cần" + 3 tab gộp thành một phiếu (ai, lời khách, từng yêu cầu một dòng có dấu, câu còn nên hỏi, kiên nhẫn) và thanh bước 1 Chọn hoa → 2 Cắm & gói → 3 Thiệp → 4 Giao (chạm để đổi khu). Bó hoa xem trước (hoa, giấy gói, màu nơ) vẫn ngay dưới.
- Sửa đồ, nhà hàng, quần áo (asm_kit reqPin, giao diện gọn): chip yêu cầu thành lưới 2 cột dòng to có dấu tròn ✓/✗; tab khu làm việc thành một thanh chọn đánh số "1. … 2. …", tab đang mở tô màu nghề. Chip trên đầu màn ghi "🧾 Phiếu 2/5" thay vì chỉ "2/5".
- ☕ Cà phê & bánh (gọn): thẻ order thành phiếu khách (từng dòng có dấu, số đo ở cuối dòng), ly đang pha nằm cạnh tên món (cà phê, sữa, bọt rót dâng lên từng lớp, đá rơi vào; khay bánh, bánh kem cũng vậy); thanh bước 1 Ly → Xay → Chiết → (Sữa) → (Vẽ) → (Nắp) → (Bánh) → Giao chỉ gồm phần món này cần; mọi quầy món cần mở hết thành khu đánh số (không còn gập từng quầy), quầy món không cần còn một dòng ghi "khách không gọi"; ô đã chọn có dấu ✓, ô khách gọi viền đứt màu nghề. Tab khu làm việc ghi chữ (Quầy · Lò · Tủ · Bánh kem) thay vì chỉ biểu tượng.
- 🍜 Mì cay (gọn): phiếu khách có tô đang làm bên cạnh (nước dùng dâng lên, mì và topping rơi vào tô); thanh bước Tô·nước → Mì → Topping → Cay → (Nắp) → Giao; bếp chia 4 khu đánh số (Tô & nước dùng · Luộc mì · Topping · Sốt ớt), ô đã lấy có ✓. Thẻ ghim "Order" trùng nội dung không hiện nữa ở giao diện gọn.
- 💇 Salon (gọn): thẻ khách thành phiếu: ảnh mẫu khách đưa bên cạnh "gương" (tóc bây giờ: màu, độ dài, đổi theo từng bước), mỗi dịch vụ một dòng có ✓ (dịch vụ bỏ sau khi chốt ghi "không làm", thêm thì "thêm"); hàng bước 7 biểu tượng không chữ thành thanh bước đánh số có chữ (Tư vấn · Chốt · Pha màu · Gội · Cắt · Sấy · Tính tiền), chạm để mở khu đó.
- 🍲 Phở (gọn): món khách gọi thành các dòng phiếu ngay trong thẻ khách (nhúng bánh, từng loại thịt, hành, chan nước bao nhiêu %, quẩy, rau); bàn làm việc xếp theo thứ tự làm một tô (tô & thịt → muôi nước dùng → trên quầy → ăn kèm), mỗi khu đánh số.
- 💅 Nail (gọn): phiếu làm móng (dịch vụ, màu, dáng & độ dài có ✓/✗, ảnh mẫu) bên cạnh bàn tay khách: 5 móng đổi dáng, độ dài theo lúc dũa, đổi màu theo lớp sơn mới nhất, bóng lên khi có lớp top, chấm hoa khi đã vẽ; các khu Chuẩn bị · Tháo sơn · Sửa · Dáng · Da viền · Sơn · Hơ đèn · Vẽ · Hoàn thiện đánh số 1–9; màu đã chọn có ✓.
- 🐶 Chăm thú (gọn): hàng bước tắm tỉa chỉ có biểu tượng thành thanh bước đánh số có chữ, chỉ các bước bé này cần; sữa tắm đã chọn có ✓.
- 🏪 Tạp hóa: tab Quầy · Kho · Sổ nợ · Giỏ (Giỏ quen) luôn ghi chữ (trước chỉ tab đang mở có chữ).
- Quần áo, trà đá: đã bày hết lựa chọn (món, màu, size; trà, đồ ăn vặt, khay) nên giữ nguyên.
- Tiếng Anh: i18n/overrides.json + build (45 chuỗi, 10 mẫu).
- Kiểm tra: ảnh 390×844 trước/sau ở cả 2 giao diện và giao diện tối "Phố đêm" (trà sữa, tiệm hoa, nhà hàng, cà phê, sửa đồ, quần áo, phở, salon, tạp hóa, nail, trà đá, chăm thú); tests milk tea / florist / guides / webassets và các bài node của giao diện.
## pay-boost

💰 Thêm tiền công khi làm nghề (chủ game 21/10: "thêm tiền thưởng cho mọi người khi làm nghề nhé, hiện tại đang ít, tăng nhẹ nữa thì tốt, coi làm event hay gì đó thì làm ngắn hạn cũng được"; "cái nào thêm để mọi người mua và tự động hay scale gì đó hợp lý thì làm luôn nha"). game/pay_boost.py, public/js/v4/paykit.js. Không đổi phiên bản, chưa có dòng Có gì mới.
- Đo trước (21/10, việc hoàn thành trong các test nghề, trung vị tiền công một việc mà các khoản thưởng tính trên đó): trà đá 3 xu/ly, rác 6, chùa 7, nấu cơm 10, thư viện 10, cơm 12, trái cây 14, photobooth 14, kem 15,5, nội trợ 18, giặt ủi 18, thông cống 20, nail 20, nông trại 21, xưởng vẽ 25, phục chế 26, homestay 27, giúp việc 28, ZPOP 30, phở 38, trà sữa 40, quán mì 48, bánh & cà phê 50,5, thú cưng 53,5, kế toán 65, mẹ & bé 85, trông trẻ 86, tạp hóa 90, quần áo 133, tiệm hoa 195. Nghề làm thuê: lương hợp đồng 14–24 (giao hàng) / 15–24 (chăm thú cưng) / 18–28 (sửa đồ, salon) … 50–85 (văn phòng, khách sạn, đài, viện…) / 65–110 (phi công) / 80–140 (dầu khí), cộng thưởng việc 5–10 xu (khách sạn, tiệc, luật, hải quan, bưu điện, ngân hàng, công an, điều dưỡng…) tới 25–97 xu (văn phòng, kế toán, salon). Thăng chức: +8/20/35/55/66/77/88 % lương (làm thuê), chủ tiệm 3–21 % tiền bo khách quen; 🔥 x3: ngày của nghề trả thêm 2 × lãi ròng gốc (trần 3.000 xu/ca).
- 💰 Tăng tiền công vĩnh viễn, một bảng RAISE: ước lượng một ngày = 4 việc × trung vị + lương hợp đồng giữa khung; dưới 90 xu/ngày +20 % (22 nghề: trà đá, rác, chùa, cơm, kem, giặt ủi, thông cống, nông trại, khách sạn, tiệc, luật, bưu điện, ngân hàng, đài, viện…), 90–249 +12 % (27 nghề), từ 250 (và 3 nghề kế toán có lương ×3) +8 % (13 nghề: hoa, quần áo, tạp hóa, mẹ & bé, salon, giáo viên…). Trung bình 14 %/nghề; một ngày trung bình 156 → 173 xu (+11,3 %): nhóm +20 % 65 → 78, nhóm +12 % 134 → 150, nhóm +8 % 356 → 384. Ví dụ: trà đá 12 → 14, giặt ủi 72 → 86, khách sạn 83 → 100, giao hàng 103 → 115, quán mì 192 → 215, phi công 148 → 165, tiệm hoa 780 → 842 xu/ngày.
- Tính ở đâu: một chỗ, tile_match.fund_bonus (không direct) gọi pay_boost.on_earning: việc tự tay làm xong (income_gear.completion_bonus), lương ngày làm thuê (sau thăng chức: chức cao vẫn lương cao), lương TT99, hoa hồng chi nhánh nước ngoài. Không áp cho đơn nhân viên, quầy, quyết toán 2.x, hội chợ, lãi, quà, chuyển khoản. Mỗi khoản một dòng riêng "💰 Tiền công +N% · …" (tối đa 500 xu/dòng), làm tròn theo băm (lặp lệnh ra cùng số).
- 🎉 Tuần lễ tay nghề (ngắn hạn): MNL_PAYWEEK_FROM / MNL_PAYWEEK_UNTIL (giây Unix; thiếu một trong hai là tắt). Dự kiến 22/10 00:00 – 28/10 23:59:59 giờ VN: MNL_PAYWEEK_FROM=1792602000 MNL_PAYWEEK_UNTIL=1793206799. +20 % tiền công mọi nghề; 🎉 Chuyên cần: 5 việc tự làm xong trong một ngày VN được thưởng một lần 30/40/50/60/70/80/100 xu theo số ngày liên tiếp (ngắt một ngày thì tính lại). Dòng bảng tin mỗi ngày (/api/news `payweek`, bản cũ bỏ qua), băng rôn trên bàn làm việc (+20 %, Chuyên cần x/5).
- Thứ tự và trần: tăng lương + Tuần lễ + đồ nghề cộng (không nhân), trần 50 %; ngày 🔥 x3 của nghề trần 40 % (cắt đồ nghề trước, rồi sự kiện), x3 vẫn chỉ nhân lãi ròng gốc (journey._base_net trừ summary['payboost']) nên một ngày x3 tối đa ×3,4.
- 🧰 Bộ đồ nghề (⋯ → 🧰 Bộ đồ nghề, mở bảng Thiết bị; trả bằng quỹ nghề, mỗi nghề riêng): 5 bậc +2/3/5/6/8 % tiền công nghề đó (bậc cao thay bậc thấp), giá 275 / 770 / 1.760 / 3.850 / 8.250 xu. 🤝 Mối khách quen 1.650 xu: ~20 % việc xong được boa thêm 10 % tiền công (1–40 xu) ≈ +2 %. Tổng phần mua ≤ +10 %. ⏩ Làm nhanh 2.750 xu (giặt ủi, phục chế): bước nào tự tay làm đúng 50 lần (chỉ đếm câu đúng, bước làm nhanh không đếm) thì một chạm; máy chủ lấy đáp án từ khóa của phiếu và chạy đúng lệnh của nghề (chấm, trả tiền, tính giờ như làm tay). Không có nhân viên tự nhập hàng.
- Giao diện: màn "Cảm ơn bạn đã giúp!" có khung 💵 Tiền công việc này (Lương cơ bản + 💰 Tăng tiền công + 🎉 Tuần lễ tay nghề + 🧰 Đồ nghề + 🤝 Khách quen boa + 🎉 Chuyên cần = Tổng) và nút 🧰 Bộ đồ nghề; lời nhắn "💰 +N xu tiền công thêm."; nút ⏩ Làm nhanh: <bước> trên bàn làm việc khi bước đã đủ 50 lần.
- Hướng dẫn: chủ đề 💵 "Tiền công thêm & Bộ đồ nghề" (🧭 Tiền bạc); coach hai bước chung tùy chọn (băng rôn 🎉 khi có sự kiện, khung tiền công + 🧰), tiếng Anh trong i18n/overrides.json.
- 🛑 MNL_PAYBOOST_OFF=1: tắt tăng lương, sự kiện, Chuyên cần, đồ nghề, boa, Làm nhanh (đồ đã mua vẫn giữ). tests/__init__.py đặt mặc định 1 cho các test cũ (giữ đúng số tiền), tests/test_pay_boost.py bật lên.
- Dữ liệu: không bảng mới, không SCHEMA_VERSION. Khóa save tùy chọn journey.paykit {v, tool, book, fast, st, wk}; 2.4.72 (83fe229c) giữ nguyên khi đọc/lưu (tests/test_pay_boost.py Compat).
- Kiểm tra: tests/test_pay_boost.py (19); tests/test_tile_match.py thêm pay_boost.py vào danh sách nơi gọi fund_bonus.

# v2.4.72 — 2026-10-21

💐 Chốt sự kiện Thiệp 20/10 (chủ game 20/10 "tối nay 0h thì chốt", "nội dung k ổn thì lấy lại tiền, acc clone chuyển đi tài khoản khác cũng lấy lại", "công bố ngẫu nhiên… có xxx thiệp đã gửi tới", "thiệp giữ tới ngày 25/10 sẽ mất"):
- Viết thiệp đóng 20/10 23:59:59 (MNL_2010_UNTIL trên máy chủ); READ_UNTIL 25/10/2026 23:59:59.
- event2010.RECAP (922 thiệp, 723 người gửi, 8 tên ngẫu nhiên trong số thiệp đạt) → dòng bảng tin mỗi ngày (key ev2010:recap:<ngày>) và trang /2010 sau khi đóng.
- ↩️ system_gift TAKE: dòng 'take-…' trạng thái 'take' (bản cũ chỉ trả 'pending', không bao giờ hiểu nhầm thành quà) → trừ ví, rồi số dư ngân hàng, phần thiếu thành nợ ví; thẻ "−N xu · Đã thu hồi", nút "Đã hiểu".
Có gì mới 2.4.72: 1 dòng.
## coach (nghề mới)

🧭 Hướng dẫn ngày đầu kiểu mới (coach: vòng sáng + làm mờ + bong bóng ngắn trên nút thật) cho các nghề mới của careers-integ, kiểm lại trên trình duyệt 390×844, cả giao diện gọn và đầy đủ, phố 2.5D và phố cổ điển (chủ game: "có đầy đủ hướng dẫn theo kiểu mới"). Không đổi phiên bản, chưa có dòng Có gì mới.
- Đối chiếu: cả 62 nghề trong game/guide_content.py ORDER (55 nghề plugin + 7 nghề gốc) đều có bước coach riêng trong game/coach/*.py; Lễ tân, Ngân hàng, Thợ phục chế, Viện nghiên cứu, Đài phát thanh, Khách sạn, Nhà hàng tiệc, Hải quan, Luật sư đã có sẵn. Lỗi tìm thấy khi chơi thử và đã sửa ở dưới.
- Mở ca từ phố 2.5D (bảng việc đang đóng): các bước tùy chọn đầu nghề (thẻ giới thiệu "Vào việc thôi!", học việc, chọn vị trí / hướng ca, kiểm phòng thu, an toàn đầu ca) bị bỏ qua lặng lẽ trước khi người chơi kịp vào bảng việc. Nay khi chưa có bước nào của nghề hiện ra, coach chỉ "Làm tiếp" để vào việc trước, rồi mới bỏ những bước thật sự không có (coach.js). Ảnh hưởng mọi nghề có bước mở đầu tùy chọn (Ngân hàng, Đài phát thanh, Viện nghiên cứu, Lễ tân, Hải quan, Bưu điện, Phi công…).
- Trả lời sai mà game vẫn nhận (sai thì sửa ngay tại bước đó): bước tùy chọn kế tiếp không thấy nút nên bị bỏ, kéo theo cả phần còn lại (Lễ tân chọn sai yêu cầu → mất các bước xếp phòng, giao chìa, xếp xe, sổ giao ca). Nay bước được đánh dấu S(…, fix=True) (Lễ tân: Chốt yêu cầu, Xếp phòng, Giao chìa, Xếp xe, Sổ giao ca; Đài phát thanh: Xác nhận thứ tự kiểm phòng thu) mà còn mở lại thì coach quay về bước đó ("Chọn đủ rồi bấm Chốt yêu cầu") thay vì bỏ (coach-core.js CoachRun.back, chỉ lùi một bước; chỉ bước có dấu, để những nút luôn nằm trên màn hình như ô chọn sữa không làm coach đi vòng; tests/coach_engine.mjs).
- Thợ phục chế và Tiệm giặt: lối "Chọn đủ rồi bấm Xác nhận" trỏ vào nút Xác nhận (nút .primary, coach coi như tab đang mở nên không bao giờ vòng sáng) → hiện "Chưa thấy nút này". Nay vòng sáng các lựa chọn của chặng đang mở.
- Ngân hàng (ngày đầu: học việc 3 bài → thi thực hành 3 phần → nhận quỹ): sau bài học đầu, bước "Bắt đầu thi" bị bỏ vì nút chưa hiện, rồi "Nhận yêu cầu" báo "Nút hiện khi có khách mới" trong lúc còn học. Nay: bước thi vòng sáng bài học còn lại tới khi nút thi hiện; thêm bước "Mỗi phần thi làm một lần. Bí thì Gợi ý, mất 🎯."; "Nhận yêu cầu" chờ khuất (không che bài thi) khi học / thi / nhận quỹ còn mở. Cờ mới của lối mở V(…, hold=True) (game/coach/__init__.py, coach.js).
- 🛎️ Dịch vụ của người chơi: coach chỉ dành cho chỗ làm (mở ca, khép ca), nên các bảng dịch vụ có gợi ý dùng lần đầu kiểu gợi ý ngắn có sẵn (tips.js, một bong bóng có vòng trên đúng nút, tắt khi chạm, đóng bảng hoặc sau 9 giây, mỗi gợi ý một lần, cho mọi bản lưu): 🛎️ Phố dịch vụ (Tìm, Của tôi), 🏥 phòng sinh (đón con chung, phòng sinh của chủ homestay), 📸 tiệm ảnh (khách đặt chụp, thợ nhận đơn), 💒 dịch vụ cưới (cưới của bạn, đơn cưới), 🎪 Hội chợ việc làm (dạo hội chợ, dựng gian). Đã xem lưu trong settings.notesSeen thành MỘT id gói "fh-" (store.js FEATURE_BITS, chỉ thêm ở cuối), như "gd-"/"co-": không khóa save mới, rollback an toàn.
- Tiếng Anh: i18n/overrides.json + scripts/i18n_extract.py build. `python -m game.coach --i18n` giữ nguyên kiểu xuống dòng của overrides.json (trước đây trên Windows đổi cả file sang CRLF).
- Kiểm tra: tests/test_coach.py, tests/coach_engine.mjs (lùi một bước, id "fh-"), test các nghề mới; chạy thử scripts/browser_coach.py (Ngân hàng, Lễ tân, Đài phát thanh, Viện nghiên cứu, Thợ phục chế; gọn và đầy đủ; 2.5D và cổ điển): mọi vòng sáng nằm trong màn hình, bong bóng không che nút.
## auction items

🔨 Nhà đấu giá thêm 50 món, món nào cũng dùng được (chủ game 20/10: "thêm nhiều đồ mới cho đấu giá nhé, thêm nhiều vào và ứng dụng được"). Danh mục 81 → 131 món. game/auction_content.py (dữ liệu), game/auction.py (trao món, câu "dùng để làm gì"), game/journey.py (thưởng đồ nghề cuối ca), game/deco_content.py + public/js/v4/deco-art.js (nội thất độc bản), public/js/v4/auction-display.js + public/css/auction.css (thẻ lô). Không đổi phiên bản, chưa có dòng Có gì mới.
- Loại cũ thêm món: 🏎️ 8 xe bản giới hạn (Cub Đồng Cổ số 50, Tay ga Hồng Ngọc số 88, Mini Ngọc Trai số 02, SUV Đêm Nhung số 09, Buồm Hoàng Hôn số 03, Cánh quạt Ngọc Trai số 01, Trực thăng Đồng Cổ số 01, Tia Chớp Hồng Ngọc số 02; 5 màu sơn riêng mới), 🚗 7 biển số, ✈️ 3 số đăng ký tàu bay, ⚓ 3 biển tên du thuyền, 👑 6 danh hiệu. Dùng như món cùng loại đã có: xe vào Nhà xe, biển gắn lên xe để lời mỗi ca +3–10%, danh hiệu đeo ở Phong cách.
- 🪑 Đồ trang trí độc bản (9 món: sập gụ khảm xà cừ, bonsai sanh, piano gỗ hồng, đồng hồ quả lắc Pháp, đèn chùm pha lê, bình Chu Đậu, ấm tử sa, mai vàng cổ thụ, đèn kéo quân): vào túi đồ trang trí (uq_<id>), bày ở nhà như món gốc kèm ánh lấp lánh; Ấm cúng = món gốc +1/+2/+3 theo hạng, tính như món gốc trong các bộ góc. Không bán, không bán lại, không hiện trong cửa hàng.
- 🐾 Đồ thú cưng độc bản (6 món, hạng A → SSS mà tiệm không bán): vào Tủ đồ thú cưng như một món thường (đeo, bỏ, ghép được); thưởng làm việc vẫn trong trần của tủ đồ (tối đa 25%) và trần ngày của bé. Tủ đầy 150 món thì món chờ, bỏ bớt một món là tự vào tủ ở lượt sau.
- 🧰 Đồ nghề độc bản (8 món cho Sớm Mai, Photobooth, Tạp hóa, Phở, Tiệm may, Hoa, Sửa đồ, Trà sữa): mỗi ca ở đúng nơi đó lợi nhuận +2/+3/+4% theo hạng, trên cùng nền với 🔥 x3 và Biển đẹp. Cộng với Biển đẹp tối đa 10% và 2.000 xu một ca; chỉ trả khi ngày được tính lương. Không phải x5.
- Giá mở: theo hạng 5k / 50k / 500k như cũ; 3 món đỉnh (siêu xe Tia Chớp Hồng Ngọc 1.000.000, vòng kim cương SSS 800.000, máy espresso 800.000) mở cao hơn, chỉ khi đúng hạng của món. Tài sản: xe bản giới hạn tính theo giá mua lại của xe gốc như trước; nội thất, đồ thú cưng, đồ nghề không tính (xu đã đốt, không bán lại).
- Dữ liệu: không có bước schema. Khóa save mới tùy chọn journey.uniq_y {v, own} cho 3 loại mới (journey.uniq / uniq_x của bản cũ kiểm chặt loại nên không đụng). Bản cũ (2.4.71) giữ nguyên khóa lạ, đồ trang trí là món hợp lệ theo hình dạng trong reno.items, đồ thú cưng dùng mã món tủ đồ đã có; trao thưởng loại mới trên bản cũ bị từ chối nên dòng live_effects vẫn chờ, bản mới trao sau. tests/test_auction_items.py: bản lưu có đủ loại mới đi qua 2.4.71 cả hai chiều.
- Kiểm tra: tests/test_auction_items.py (19), tests/auction_items.mjs; test_deco / test_deco_more chấp nhận món độc bản uq_dc_. Ảnh 390×844: thẻ lô 4 loại, Của tôi, túi đồ, kéo sập vào phòng khách (Ấm cúng 15 → 21). Tiếng Anh: i18n/overrides.json + build.
## halloween

🎃 Lễ hội Ma Phố, Halloween 26–31/10/2026 (chủ game 20/10; kế hoạch: docs/HALLOWEEN_2026.md). Tự mở 0:00 26/10 giờ VN, khép 23:59:59 31/10, đổi kẹo tới hết 01/11; trước đó không có gì hiện ra. game/halloween.py + halloween_content.py, public/js/v4/halloween.js, halloween-data.js, halloween-town.js, public/css/halloween.css, quản trị public/js/admin/halloween.js. Không đổi phiên bản, chưa có dòng Có gì mới.
- Kiếm 🍬 kẹo: điểm danh 10/ngày; 5 quả bí ngô nấp quanh phố mỗi ngày (câu đố 4 lựa chọn, đoán một lần, 5 kẹo; phố 2.5D đi tới đúng biển là nhặt luôn); "Cho kẹo hay bị ghẹo?" gõ cửa người chơi khác (10 nhà/ngày, mỗi nhà một lần, 4 kẹo hoặc bị ghẹo 1; chủ nhà 2 kẹo/khách, tối đa 15 khách/ngày); mỗi ngày một chủ đề có thưởng nhỏ; 31/10 từ 19:00 mọi kẹo ×2 + Bí ngô khổng lồ 30.
- Quầy đổi kẹo: 3 danh hiệu, 2 khung, 1 màu tên Halloween trọn đời (🎨 Phong cách, không mua được bằng xu), vòng kẹo thú cưng, túi 20.000 xu tối đa 3 lần/tài khoản. Bảng kẹo: top 3 "Vua Kẹo Halloween 2026" + khung bí ngô vàng, top 4–10 "Top 10 săn kẹo 2026", trao một lần lúc 0:00 01/11.
- Thẻ khai hội giữa màn hình mỗi ngày (break-gate 'hween' sau Thiệp 20/10), dòng tin chạy chữ mỗi ngày + lúc 19:00 31/10, lối vào ở menu và Tiện ích, phố 2.5D trang trí (lớp phủ DOM, không đụng bản Phaser).
- Chống nick phụ: chỉ tài khoản; gõ cửa cần tài khoản ≥ 1 ngày, ≤ 3 tài khoản/mạng/ngày; túi xu cần tài khoản ≥ 3 ngày, ngày sống ≥ 3, ≤ 3 tài khoản/mạng cả mùa (mạng lưu mã băm); mọi thưởng một lần theo khóa + khóa advisory. Quản trị → Halloween (GET /api/admin/halloween). 🛑 MNL_HALLOWEEN_OFF=1.
- Dữ liệu: SCHEMA_VERSION 80 (76–79 của nhánh khác): bảng mới hw_players, hw_log + index; không FK, không backfill, không khóa save. Quà qua live_effects kind 'hween' (2.4.71 để chờ). tests/test_halloween.py, tests/test_halloween_compat.py, tests/halloween.mjs, scripts/browser_halloween.py (ảnh 390×844). Tiếng Anh: i18n/overrides.json + build.
## home decor

🛋️ Thêm đồ trang trí cho nhà (chủ game 21/10: "thêm đồ trang trí cho nhà"). game/deco_content.py (MORE_2026, 8 bộ góc, STYLES), game/deco.py (catalogue: `new`, `styles`), public/js/v4/deco-art.js (55 hình), client/home3d/meshes.js + public/js/v4/home-3d-scene.js (cảnh 3D), public/js/v4/reno.js + public/css/reno.css (cửa hàng, 📍 Đặt nhanh). Không đổi phiên bản, không bước schema, chưa có dòng Có gì mới.
- 55 món mới, giá 22–1.200 xu (giá ghi sao bán vậy, không qua chỉ số giá), Ấm cúng +1…+3 mỗi món: 🏮 Nét Việt xưa (sập gụ chân quỳ, tủ chè khảm trai, đèn lồng và chùm đèn lồng Hội An, tranh Đông Hồ đàn gà và đám cưới chuột, bình phong gỗ chạm, chiếu hoa, ấm tích giỏ ủ, nón lá, đèn dầu, tranh thêu sen), tối giản (sofa góc chữ L, đèn sàn cần câu, tranh trừu tượng, bàn trà mặt đá, kệ bậc thang, đèn giấy, bình cành khô), pastel (giường đám mây, ghế lười tai thỏ, đèn mây, kệ cầu vồng, thảm mây, gấu dâu tây, đèn kẹo bông), gaming (màn hình cong, bàn phím LED, giá tai nghe, đèn thanh RGB, poster game, kệ tay cầm), góc đọc sách (tủ sách kịch trần, ghế bành, đèn cổ ngỗng, chăn len, kệ sách treo, bản đồ), bếp (bàn ăn tròn, nồi đất kho cá, tủ bếp treo, máy rửa bát, giỏ bánh mì), nhà tắm (thang treo khăn, chậu ngâm chân, đèn đá muối, kệ tre), ban công và cây (bộ bàn ghế ban công, chậu lan, giàn mướp, hòn non bộ, đèn năng lượng mặt trời, sen đá, bàng Singapore, thảm thổ cẩm). Món nào cũng có hình 2D, khối 3D, tên tiếng Anh; biệt thự có thêm phòng thì món cũng vào được phòng cùng loại.
- 8 bộ góc mới, thưởng Ấm cúng +2/+3, trần SET_BONUS_MAX = 3 (mỗi bộ tính một lần mỗi nhà): Gian nhà xưa +3, Phố Hội lên đèn +2, Phòng khách tối giản +3, Phòng ngủ pastel +3, Góc stream +2, Góc đọc sách +2, Ban công xanh mát +2, Bữa cơm nhà +2. Ấm cúng chỉ đổi tinh thần mỗi sáng theo bậc có trần như cũ (+1 từ 10, +2 từ 24), không ra tiền.
- Cửa hàng trên điện thoại: 🔎 ô tìm theo tên (gõ không dấu cũng được, tiếng Anh cũng được, giữ con trỏ khi danh sách đổi), chip 🆕 Mới về, hàng chip phong cách (Nét Việt xưa, Tối giản, Pastel dễ thương, Góc gaming, Góc đọc sách, Cây xanh & ban công), đếm "x/y món", hết món thì có nút Bỏ lọc; thẻ món mới có nhãn "Mới".
- 📍 Đặt nhanh (góp ý #443, người chơi khiếm thị): cầm món lên (chạm thẻ) thì hiện các nút chỗ trống có tên đọc được ("Đặt chùm đèn lồng Hội An: Giữa tường, phòng khách"): trái/giữa/phải của tường, sàn hoặc thảm; đồ nhỏ thì "Lên tủ chè…" trên mặt kệ, bàn có sẵn. Chỗ do client tính theo đúng luật server (không vướng cửa, không chồng món), bấm là mua/đặt như kéo thả, không cần kéo.
- Lưu và quay về bản cũ: không bước schema, không khóa lưu mới; món mới chỉ là đồ có mã mới. Bản cũ đọc save vẫn hợp lệ (chỉ kiểm hình dạng), giữ món mới trong nhà nhưng không vẽ; nếu bản cũ ghi lại bố trí thì món mới về túi đồ, vẫn còn của người chơi, lên bản mới đặt lại được.
- Kiểm thử: tests/test_deco_2026.py (đủ món, hình 2D/3D, tên tiếng Anh, bộ góc làm được trong biệt thự và không cộng trùng, mua/đặt/lưu/đọc lại từng món, chủ nhà và khách đều thấy, bán lại nửa giá, quay về bản cũ); scripts/browser_decor_2026.py (390×844: cửa hàng, lọc, tìm, Đặt nhanh bằng bàn phím, hoàn thành Gian nhà xưa, xem 2D và 3D).
## island houses + bang

🏡⚔️ Đảo riêng có nhiều kiểu nhà đẹp hơn, bang hội có thêm việc để làm cùng nhau (chủ game 20/10 "coi hướng đảo có thể xây nhà các kiểu đẹp và nhiều hơn, bang hội nữa nhiều hơn"). game/island_build*.py, public/js/house-art.js (mới: vẽ nhà 2.5D dùng chung), public/js/v4/island.js, game/bang_extra.py + bang_extra_content.py (mới), public/js/v4/bang.js. Không đổi phiên bản, chưa có dòng Có gì mới.
- 🏠 15 kiểu nhà mới trong 4 bậc, mỗi kiểu 3 cấp và 3 màu: 🌾 Mộc mạc (Nhà tranh vách đất 1,5tr, Nhà tre sinh thái 2,5tr, Nhà trên cây 3tr, Cabin gỗ chữ A 4tr), 🏮 Phong vị (Bungalow mái lá 5tr, Nhà phố Hội An 6tr, Nhà rường Huế 7tr, Nhà hải đăng 7tr – 1 cái/đảo, Nhà kiểu Nhật 8tr, Hanok 8tr), 💎 Sang trọng (Biệt thự Pháp 12tr, Địa Trung Hải 14tr, Biệt thự kính 18tr), 👑 Đỉnh cao (Dinh thự châu Âu 30tr, Hoàng cung Á Đông 35tr – chỉ đảo lớn, 1 cái/đảo). Giá cấp 1 / 2 / 3 nằm giữa nhà sàn, biệt thự biển và lâu đài cũ; cả 3 cấp tối đa 170tr (rẻ hơn đảo đắt nhất); điểm bảng đảo theo giá như nhà cũ, một kiểu chỉ tính đa dạng một lần dù khác màu.
- 🎨 Màu chọn miễn phí khi xây; sơn lại (jr_isle_paint) 10 % giá cấp 1 (tối thiểu 200k), xong ngay, giữ cấp; tiền sơn cộng vào giá trị công trình (phá nhà vẫn hoàn theo luật cũ). Màu nằm trong tên loại công trình ('<kiểu>__<n>'): KHÔNG thêm khóa save, không đổi bảng.
- Nhà vẽ 2.5D thật (cùng mô hình cho giao diện mới Phaser và giao diện cũ canvas), khách ghé đảo thấy đúng kiểu và màu; nhà bậc 3–4 có cần cẩu lúc xây; phòng bên trong theo kiểu (nhà tranh, nhà cây, hải đăng, Nhật, Hanok, hoàng cung) hoặc theo bậc.
- Bảng xây: tab 🏠 Nhà ở / 🎡 Vui chơi, lọc theo bậc, lưới thẻ có ảnh vẽ, chọn một kiểu thì hiện ảnh lớn + xem trước 3 cấp + chọn màu trước khi trả tiền; nhà đã xây có nút 🎨 Sơn lại. Vừa tay ở 390×844.
- 🏯 Kiểu đại sảnh (bang): 8 kiểu ngoài Đình bang mặc định, mở một lần bằng quỹ bang: Phủ rường cố đô / Sảnh Hanok / Sảnh Phù Tang 10tr (Đại sảnh cấp 2), Dinh thự Pháp / Sảnh Địa Trung Hải 25tr (cấp 3), Sảnh kính hiện đại 50tr / Lâu đài châu Âu 60tr (cấp 4), Hoàng cung Á Đông 100tr (cấp 5). Kiểu đã mở và 3 màu đổi miễn phí; đổi tối đa 1 lần/giờ. Chỉ Bang chủ/Phó bang. Chỉ là diện mạo: không cộng điểm, không cộng chức năng.
- 🎏 Trang trí đảo bang (cần 🏝️ Đảo bang): Dãy đèn lồng 3tr, Vườn đào 5tr, Cờ hội 6tr (Đại sảnh 2), Tượng rồng đá 12tr (2), Lầu chuông 15tr (3), Thuyền rồng 20tr (3); mua một lần bằng quỹ, Bang chủ/Phó bang. Mỗi món +5 % điểm nhiệm vụ tuần, trần +30 %; không tính vào xếp hạng tuần, không có trong danh sách công trình.
- 📋 Nhiệm vụ tuần của bang: 3 nhiệm vụ mỗi tuần (mỗi loại đo một việc khác nhau: điểm danh, ngày làm việc, thành viên hoạt động, góp quỹ, xây bằng quỹ), mục tiêu theo số thành viên. Xong thì ai đã góp sức cho bang tuần đó (điểm danh, làm việc hoặc góp quỹ) nhận 40–80 điểm cống hiến (+ thưởng trang trí); mỗi người tối đa 3 lần/tuần dù đổi bang. Không ra xu, không rút quỹ, không vào điểm xếp hạng bang.
- Đảo bang vẽ đại sảnh theo kiểu và màu, trang trí đặt sẵn chỗ (thuyền rồng nhấp nhô ở bến), ở cả hai giao diện.
- Dữ liệu: KHÔNG có bước schema (không dùng 77). Kiểu đại sảnh nằm trong cột bang_facilities.place có sẵn (bản cũ không đọc); trang trí là dòng bang_facilities 'd_<id>' cấp 1 (bản cũ bỏ qua khi tính cấp và xếp hạng); tiền mua là dòng bang_fund 'build'; điểm nhiệm vụ là dòng bang_points 'quest'. Rollback: bản cũ đọc save bình thường; công trình đảo có màu khác 0 bị bản cũ coi là loại lạ (ẩn, có thể bị đánh dấu 'gone' trong island_builds tới lần đồng bộ sau của chủ đảo); kiểu nhà mới màu 0 thì bản cũ cũng không biết kiểu (ẩn như trên).
- Kiểm tra: tests/test_island_houses.py, tests/test_bang_extra.py (mới), tests/test_island_build*.py, tests/island-build.mjs (cập nhật). Tiếng Anh: i18n/overrides.json + build.

## restoration
## moto

🏍️ Nghề mới Tiệm sửa xe Út Lanh (thợ sửa xe máy đầu hẻm), có dịch vụ người chơi ↔ người chơi (chủ game 21/10 "tính toán làm thêm nghề khác luôn nhé"; đợt nghề 3, docs/CAREERS_BATCH_3.md). game/careers/moto.py, moto_content.py, game/careers/stepkit.py (bộ bước dùng chung), game/moto_service.py, public/js/careers/moto.js + slip_kit.js.
- Nghề tiệm (mở từ chương 2, LATE_UNLOCKS; nằm ngủ trong save tới khi chơi, engine.DORMANT). Mỗi phiếu một chiếc xe: nghe khách tả bệnh → chốt lỗi (8 bệnh: thủng săm, quá hạn nhớt, bugi, sên chùng, má phanh mòn, đèn pha, ắc quy yếu, xe lội nước) → chốt 1–2 yêu cầu oái oăm → các bước theo sổ tay (tính km từ tem nhớt, ml nhớt, độ chùng sên, má phanh còn bao nhiêu mm, đúng ampe cầu chì, giờ sạc theo Ah, súc nhớt hai lần…) → giao đúng xe theo biển số giữa ba chiếc giống hệt. Tên bệnh chỉ hiện sau bước đầu.
- Máy chủ chấm từng bước; sai một bước −8% chất lượng (phanh, xe ngập: sai thì trừ sao). Lãi 9–16 xu / xe + 2 xu mỗi yêu cầu + cấp, nhân chất lượng; phụ tùng tiệm ứng trước, trừ khi giao.
- "Oái oăm": 15 yêu cầu khách (nhớt xe số đổ xe tay ga "cũng được", cầu chì to hơn "cho khỏi đứt", đề thử xe vừa lội nước, tháo bộ hạn chế xe 50 phân khối, lùi đồng hồ km để bán xe, ắc quy bảo hành mà đòi ghi "hỏng do tiệm", đòi xem lại đồ thay ra…) và 14 chuyện bất ngờ ở tiệm (thùng phụ tùng rẻ không hóa đơn rồi công an phường ghé hỏi, mưa ngập năm xe chết máy xếp hàng, xăng pha nước, mèo ngủ trên lốc máy, đòi độ pô kêu to, Bà Chín xẹp bánh mà không đủ tiền…).
- 🛎️ Phố dịch vụ: 🔧 Bảo dưỡng xe máy (NPC 50 xu, người chơi mặc định ×3 = 150 xu, một xe mỗi đơn; người mua cần có xe máy). Thợ làm 3 bước chấm điểm ở bàn thợ (áp suất bánh sau, thay nhớt đúng thứ tự, kiểm an toàn) rồi mới Giao được (moto_bench). Xe của người mua: gỡ cảnh báo 🎲 "xe sắp hỏng" và 10 ngày ít hỏng vặt (rủi ro hỏng chia đôi). 🛑 MNL_MOTO_SVC_OFF=1.
- Đủ bộ: hướng dẫn ngày đầu (coach) hai giao diện, lô mới khu hành chính (phố 2.5D) + biển ở phố cổ điển, chứng chỉ Kỹ thuật sửa xe máy cơ bản (chứng chỉ nghề, không phỏng vấn: có nó thì đại lý bớt 1 xu phụ tùng mỗi xe), mạch truyện "Chiếc cờ lê số 10" (5 đoạn), danh hiệu, thăng chức, 10 gói chuyên môn, thi đua NPC, quy mô, tip, quà, đánh giá, đồ nghề, tiếng Anh.
- Dữ liệu: không đổi schema (79 vẫn để dành). Khóa save tùy chọn journey.xe_care {v, cars} mà 2.4.71 giữ nguyên không đọc. Lùi bản: `scripts/strip_new_careers.py strip --careers …,moto,vet` (mặc định đã có), `restore` trả lại từng byte (tests/test_moto_vet_compat.py).
- Số nghề: 62 → 63.

## vet

🩺 Nghề mới Bác sĩ thú y ở Phòng khám Thú y Cỏ May (phòng khám mà 🐾 thú cưng vẫn đưa tới), có dịch vụ người chơi ↔ người chơi. game/careers/vet.py, vet_content.py, game/vet_service.py, public/js/careers/vet.js.
- Nghề lương (56–72 xu/ca, mở từ chương 3, nằm ngủ trong save tới khi chơi) + thưởng chất lượng mỗi ca khám (5–9 xu theo bệnh + 1 mỗi yêu cầu, nhân chất lượng, tối thiểu 3). Mỗi ca một bé: nghe chủ kể → chốt bệnh (8 ca: tiêm phòng, cắt móng, ve và bọ chét, ăn nhầm sô-cô-la, nôn ra máu nghi parvo, mèo đực tắc tiểu, nuốt dị vật, triệt sản) → yêu cầu oái oăm của chủ → cân bằng hiệu số (chó: chị Duyên bế lên cân người; mèo: trừ lồng), đo thân nhiệt, liều theo cân, dịch truyền, giờ nhịn ăn trước mổ → trả đúng bé theo phiếu chuồng.
- "Oái oăm": 14 yêu cầu của chủ (cho mèo uống paracetamol, thuốc giảm đau của người cho chó, bôi tỏi trị ve, cắt tai cắt đuôi cho đẹp, viết giấy tiêm khống, bán vắc xin về tự tiêm, cho ăn no rồi đòi mổ…; chỉ hiện yêu cầu hợp loài) và 14 chuyện bất ngờ (khách ôm rắn cảnh tới, chó cắn nhau ở phòng chờ, mèo hoang bị xe tông → được nhận nuôi, nhờ chích thuốc cho chó hàng xóm "im", gà đá đòi "thuốc tăng lực", ông Sáu hỏi chuyện cho bé Mun đi, sổ tiêm khống bị cán bộ phường kiểm, vắc xin mua online, cúp điện tủ vắc xin…).
- 🛎️ Phố dịch vụ: 🩺 Khám thú cưng (NPC 150 → 450 xu) và 💉 Tiêm phòng (NPC 250 → 750 xu), một bé mỗi đơn, chỉ bác sĩ còn làm ở phòng khám mới nhận; bác sĩ làm 3 bước ở bàn khám rồi mới Giao được (vet_bench). Hiệu ứng như phòng khám NPC (hồi sức khỏe, gia hạn tiêm, thân thiết). 🛑 MNL_VET_SVC_OFF=1.
- Đủ bộ như nghề trên: coach, lô cạnh tiệm thú cưng, Chứng chỉ Chăm sóc thú y cơ bản, mạch truyện "Chiếc ống nghe một phút", danh hiệu, 10 gói chuyên môn, tiếng Anh.
- Dữ liệu: không bảng mới, không khóa save mới. Lùi bản như nghề sửa xe.
- Số nghề: 63 → 64.

## restoration

🧰 Thợ phục chế (nghề thứ 60 trong careers-integ): Xưởng phục chế Hồn Xưa của chú Khải, phục chế đồ xưa đồ hỏng; và phục chế đồ của người chơi khác qua 🛎️ Phố dịch vụ (chủ game 21/10: "làm hết đi"). game/careers/restore.py + restore_content.py (nghề), game/restore_service.py (người chơi với người chơi), public/js/careers/restore.js + public/css/careers/restore.css (bàn làm việc), public/js/v4/restore.js + public/css/restore.css (🧰 Phục chế đồ). Không đổi phiên bản, chưa có dòng Có gì mới.
- Việc của nghề: mỗi phiếu là một món (đồng hồ quả lắc ông nội, ghế mây bà, đài radio, máy khâu con bướm, bình gốm men lam, rương hồi môn, va li da, đèn dầu, quạt con cóc, gia phả chép tay, áo dài cưới của mẹ, xe đạp của ông, tủ thờ gỗ gụ, máy ảnh phim; mở dần theo ngày 1/4/10/20/40), 8 bước server chấm: đọc dấu hiệu → gọi đúng tên hư hỏng (nứt, gỉ, mọt, bong sơn, lỏng mộng, rách, kẹt máy, mẻ, tuột sợi, hỏng dây điện) → chốt yêu cầu khách → linh kiện (thiếu thì chế lại cùng vật liệu, không tháo đồ khách khác) → làm sạch theo chất liệu → phục hồi từng chỗ hư → hoàn thiện → kiểm 4 mục → trả đúng phiếu. Sai thì sửa ngay tại bước đó, chất lượng −12 mỗi lần (sàn 40). Vật tư ứng theo phiếu, trừ một lần khi trả đồ; công 14 + 3 mỗi chỗ hư + 2 mỗi yêu cầu khách + mốc ngày. Thợ vững tay 100 phiếu đạt + 30 ngày; Nghệ nhân Hồn Xưa 180 + 45.
- "Oái oăm" (luật chủ game): 14 yêu cầu khách, 1–2 cái mỗi phiếu, hợp chất liệu món đồ, đổi đáp án: giữ vết xước kỷ niệm mà đòi đẹp như mới (hoàn thiện = chừa vết xước), đồ "gia truyền trăm năm" còn tem nhà máy (ghi đúng tuổi), mặc cả nửa giá (giữ giá công, bớt hạng mục), đồ của bà ngoại mà đòi mới tinh (nói rõ mất lớp gốc, khách ký thì làm mới), thiếu linh kiện chợ hết bán (chế lại, ghi phiếu), đám cưới chiều nay đòi xong trong 1 tiếng, khách tự dán keo 502 rồi đòi đền, hai anh em tranh nhau, thư cũ trong ngăn bí mật, thương lái nhờ làm giả đồ cổ, giữ mùi long não mà tủ mốc, đòi chụp gửi Zalo 10 phút một lần, thầy phong thủy đòi sơn đỏ gỗ gụ, bảo tàng đòi giấy "nguyên bản 100%".
- Phục chế cho người chơi (Phố dịch vụ, đúng API service_market.register): 🛵 xe máy / xe đạp, 🚗 ô tô, ⛵ thuyền / máy bay đang hỏng sau rủi ro (journey.rui.broken.xe: xe chạy lại được, như jr_rui_fix mà không qua bảo hiểm), 🏚️ một phần nhà đang ở và sở hữu bị xuống cấp (reno.parts: về 100%, gỡ luôn "nhà hỏng" của rủi ro cho phần đó), 🪑 làm đồ gỗ thành cổ điển (chỉ đổi vẻ ngoài: nước sáp trầm vẽ trên phòng). Không thêm cơ chế làm hỏng đồ mới. Giá thường 40 / 500 / 2.500 / 120 / 60 xu; người chơi trả mặc định ×3, thợ chỉnh ×1–×10 hoặc thương lượng; 95 % cho thợ, 5 % bị đốt; hủy / từ chối / quá hạn hoàn đủ (luật Phố dịch vụ).
- Luồng: khách mở 🧰 Phục chế đồ (từ 🔧 Đang hỏng của Bảo hiểm & rủi ro, nút 🧰 Làm cổ điển của món đồ trong nhà, hoặc 🧰 Bàn thợ), chọn món + dặn "giữ dấu thời gian" hay "làm mới" (phiếu restore_tickets) rồi chọn thợ ở Phố dịch vụ; thợ Nhận đơn, làm 3 bước ở 🧰 Bàn thợ (bước đầu gắn phiếu vào đơn; bước cuối phải đúng lời khách dặn; chọn sai thì làm lại, mỗi lần sai bớt một ⭐), rồi 🎁 Giao đồ. Hook deliver của chợ (trong giao dịch đánh dấu đã giao) kiểm đủ 3 bước và đóng phiếu; on_buyer của chợ (trong giao dịch trả tiền thợ, ngay sau đó) phục hồi món trong bản lưu của khách ĐÚNG MỘT LẦN (chợ chỉ lật ready → done một lần; dấu mang mã đơn) và gắn dấu "✨ Đã phục chế bởi <thợ> ⭐⭐⭐" (tab ✨ Đã phục chế; đồ gỗ hiện nước sáp và nhãn ✨ Cổ điển). Đơn bị hoàn tiền thì phiếu tự mở lại.
- 🛑 MNL_RESTORE_OFF=1: không ghi phiếu mới, không đặt mới, thợ không mở bán / không giao (đơn đã trả tiền hết hạn thì chợ hoàn đủ); món đang thanh toán vẫn vào bản lưu. Không có cache trong bộ nhớ.
- Bản đồ: lô mới ở khu dân cư cạnh tiệm giặt (phố 2.5D: mặt tiền đồng hồ quả lắc + hộp sáp trên nền xưởng, bố trí trong xưởng riêng: tủ linh kiện, bàn khám & phục hồi, kệ đồ chờ, quầy nhận và trả đồ); phố cũ: biển 🧰 Phục chế ở Phố dịch vụ cạnh Sửa đồ. Hướng dẫn từng bước ngày đầu (game/coach/services.py, cả hai giao diện), sổ tay nghề, danh hiệu, thăng tiến, các bậc quy mô, gói chuyên môn (game/data/career_specialisms_restore.json), thi đua, đánh giá khách.
- Dữ liệu: SCHEMA_VERSION 72 (69–71 của nhánh khác): bảng mới restore_tickets + index; chỉ thêm, không FK, không backfill. Khóa save mới tùy chọn journey.restored {v, items} (tối đa 80 dấu) mà 2.4.66 giữ nguyên không đọc. Nghề restore nằm trong engine.DORMANT: chưa làm thì không lưu, 2.4.66 vẫn đọc bản lưu; đã làm thì trước khi rollback chạy scripts/strip_new_careers.py strip --careers restore (restore để trả lại). tests/test_restore_compat.py: 2.4.66 chơi tiếp bản lưu có dấu phục chế, khởi động trên DB 72 không DDL, giữ mọi dòng.
- Kiểm tra: tests/test_career_restore.py, tests/test_restore_service.py, tests/test_restore_compat.py; số nghề 58 → 59 trong các test đếm nghề (Lễ tân là 58). Ảnh 390×844 và 844×390: bàn làm việc gọn / đầy đủ, 🧰 Bàn thợ, 🧰 Phục chế đồ, ✨ Đã phục chế, phố 2.5D, phố cũ. Tiếng Anh: i18n/overrides.json + build.

## research

🔬 Nghề mới Viện nghiên cứu (nhà nghiên cứu) ở Viện nghiên cứu Sông Mây (chủ game 21/10 "làm hết đi"). game/careers/research.py, research_content.py, game/research_lab.py, public/js/careers/research.js.
- Nghề có lương hợp đồng (54–70), mở từ chương 3 (LATE_UNLOCKS), nằm ngủ trong save tới khi chơi (engine.DORMANT). Đầu ca chọn một trong ba hướng: 🌱 Giống cây (lai tạo, khảo nghiệm ngoài đồng, ngân hàng hạt giống), 🍳 Công thức món (chuẩn hóa công thức, hội đồng nếm mù, giá vốn và nhãn), 🛠️ Sáng chế (mẫu thử, thử độ bền, hồ sơ sáng chế). Mỗi bước chấm ở máy chủ, sai thì sửa tại chỗ, chất lượng giảm 6/lần (sàn 60), thưởng 6–8 xu theo chất lượng.
- An toàn đầu ca (blouse, kính, găng, tủ hút, sổ) và cuối ca (cất mẫu, khóa tủ hóa chất, tắt thiết bị); viện trưởng đi kiểm tra bất chợt ~30% ngày; quên tắt thiết bị thì 15% đêm hỏng mẫu, đền 8% lương ca (2–6 xu), không quá số tiền trong ví.
- "Oái oăm": 14 chuyện bất ngờ (thí nghiệm nổ, mẫu bị chuột ăn, hội đồng duyệt khó tính, nhà tài trợ đòi kết quả sớm, đồng nghiệp nhận vơ công, cúp điện tủ ấm, sếp gợi ý làm đẹp số liệu, phản biện đòi trích bài của mình, thực tập sinh dán nhầm nhãn, mèo ngủ trên khay mẫu, quỹ đòi báo cáo gấp, phóng viên giật tít, viện trưởng đòi cay hơn, hạn nộp dời sớm); trong phiếu có ô ruộng bị trâu giẫm/ngập, túi mẫu bị chuột gặm, người nếm vừa ăn mì cay, anh Quý đòi đứng tên; từ ngày nghề 4 việc nào cũng kết thúc trước hội đồng (giữ số liệu thật).
- 📬 Đơn nghiên cứu của người chơi (Phố dịch vụ, service_market.register 'research'): 🌱 Giống cây cải tiến (giá NPC 40), 🍳 Công thức món mới (40), 🛠️ Đồ sáng chế (60); giá người chơi ×3 mặc định, 95% cho người làm, 5% đốt. Người làm nhận đơn, làm 3 bước nghiên cứu chấm ở máy chủ (bảng research_jobs), bước cuối tự giao; "Xong việc" chung bị từ chối nếu chưa làm đủ 3 bước.
- Hiệu ứng thật nhưng có trần (tests chứng minh): giống +1 sản lượng cho 3 vụ thu Vườn mới (2 vụ nếu chất lượng < 90%), chỉ ớt/lúa/thanh long/dâu tây/xoài, tối đa 14 ngày; công thức: quán ăn của người mua nhận thêm 10% (≥1, tối đa 3 xu) cho 12 đơn (8 nếu < 90%), tổng tối đa 30 xu, 7 ngày; đồ sáng chế chỉ để khoe trong 📱 Mây Mobile → Của bạn (không bán, không ra tiền), kệ tối đa 12 món. Mỗi loại một hiệu ứng đang chạy, 3 ngày mới đặt lại; giá trị tối đa của mỗi dịch vụ ≤ giá NPC (người mua trả ×3). Hiệu ứng vào save đúng một lần (on_buyer + danh sách đơn đã nhận).
- Bản đồ: lô mới ở Vườn Gió Tây cạnh Trang trại (2.5D: biển bình thí nghiệm, phòng làm việc riêng; phố cổ điển: Khu văn phòng); hướng dẫn ngày đầu (coach) cho cả hai giao diện; chứng chỉ, mạch truyện 5 đoạn, danh hiệu, gói chuyên môn 10 bậc.
- Dữ liệu: SCHEMA_VERSION 71 (67, 70 của nhánh khác): bảng mới research_jobs + 1 index; không FK, không backfill. Save: khóa tùy chọn journey.lab (2.4.66 giữ nguyên, không đọc); careers.research vắng mặt khi chưa chơi (đã chơi thì không lùi về dưới bản thêm nghề, như mọi nghề mới). 🛑 MNL_RESEARCH_OFF=1: không đặt/làm/giao đơn mới, hiệu ứng tạm dừng (không mất).
- Số nghề: +1 (cộng thêm trên các nghề nhánh khác).

## radio

📻 Nghề mới Đài phát thanh Sóng Mây (phát thanh viên / DJ), có tương tác người chơi với người chơi (chủ game 21/10 "làm hết đi"). game/careers/radio.py, game/careers/radio_content.py, game/radio_station.py, public/js/careers/radio.js, public/js/v4/radio.js.
- Nghề lương theo hợp đồng (50–64 xu/ca, thử việc 3 ngày), mở từ chương 3 (LATE_UNLOCKS, ngủ đông trong save như hotel/banquet/reception). Đầu ca BẮT BUỘC kiểm phòng thu theo đúng thứ tự (bàn trộn, mic, tai nghe, đường truyền, đèn ĐANG PHÁT SÓNG) rồi mới lên sóng.
- 🎙️ Phát thanh viên (mọi người bắt đầu ở đây): 📰 bản tin phường (chọn tin được đọc, bỏ tin đồn và quảng cáo trá hình, xếp tin khẩn → dịch vụ công → sự kiện, tính thời lượng, đính chính phút chót), 📢 quảng cáo nhà tài trợ (chỉ đọc bản MỚI NHẤT ĐÃ DUYỆT — bản gửi qua tin nhắn lúc 9:59 thì không, gạch câu phóng đại, tính độ dài spot, yêu cầu phút chót của nhà tài trợ), 💌 lời chúc thính giả (bỏ lời có số điện thoại / link / địa chỉ / bêu riếu, đọc theo giờ gửi, tên không dấu thì hỏi lại, đọc nhầm tên thì xin lỗi đọc lại).
- 🎧 DJ ca nhạc (sau 3 ca phát thanh viên đạt, +10 kinh nghiệm): 🎵 khách gọi xin bài lạ (tìm theo lời bài tả, bài chưa có bản quyền / lời thô thì từ chối khéo, canh lời dẫn cho kịp bản tin đầu giờ, yêu cầu oái oăm), ☎️ thính giả gọi vào sóng (chửi thề → XÓA TRỄ 7 giây, gọi phá, bé gọi nhầm tìm mẹ, chê nhạc, rao đa cấp, xin kêu gọi chuyển tiền, ghi sổ cuộc gọi), 🎚️ xếp chương trình (bỏ bài không được phát, đúng khung chương trình, tính lời dẫn, khách mời trễ / say / đòi quảng cáo / đòi tiền trên sóng).
- ⚡ Mất điện giữa sóng: khoảng 35% số ngày (từ ngày 2), sau việc đầu tiên xong; chặn mọi bước cho tới khi làm đủ sổ sự cố (UPS → băng dự phòng → máy phát → kiểm bàn trộn, mic → xin lỗi thính giả → ghi sổ). Gọn: +6 kinh nghiệm; sai từ 3 bước hoặc bỏ mặc tới cuối ca: sóng câm, đánh giá 2 sao, ca đó không tính thử việc.
- Hơn 40 tình huống "oái oăm" trong phiếu việc + 10 chuyện bất ngờ ở đài (mèo nhảy lên bàn trộn, giả giọng ca sĩ, mưa dột tủ máy, trò chơi có thưởng hai người cùng đúng, kịch bản ghi nhầm ngày lễ…). Mỗi bước chấm ở máy chủ, sai thì sửa tại chỗ (−6% chất lượng mỗi lần, sàn 60%), lần sai thứ hai chị Hoa chỉ đáp án. Mã lựa chọn trung tính (a, b, c…): không lộ đáp án.
- 🛎️ Hai dịch vụ cho người chơi qua Phố dịch vụ (service_market.register): 📢 Quảng cáo tiệm trên sóng (giá NPC 500 xu, mặc định ×3 = 1.500 xu, chạy trên bảng tin cả phố 60 phút; người mua cần có tiệm / quầy / chỗ làm) và 🎵 Gửi bài hát tặng người thương (giá NPC 200 xu, ×3 = 600 xu, 30 phút; cần DJ đã hết thử việc). Giữ tiền, 95% cho DJ, 5% đốt, hoàn đủ khi từ chối / quá hạn — theo đúng Phố dịch vụ.
- Lên sóng: DJ mở 📻 Đơn lên sóng (cả giao diện gọn lẫn đầy đủ), đọc dòng sẽ chạy, chọn nhạc nền / bài hát, đánh dấu đã đọc kỹ rồi bấm 🔴 Lên sóng (nhận + giao đơn một lần, được trả ngay). Nút "Xong việc" chung bị từ chối (phải duyệt ở đài).
- Kiểm duyệt: lời của người mua kiểm ngay khi đặt (trước khi giữ tiền, khóa mới `note_check` của service_market) và lại khi lên sóng: 6–120 ký tự, một dòng, không link / e-mail / @handle / tài khoản liên hệ / số điện thoại, không từ tục (dùng lại live/filters và social.BANNED); bị từ chối thì không bao giờ lên sóng (không che chữ).
- Giới hạn bảng tin: tối đa 4 dòng cùng lúc cả phố, mỗi người mua 2 lượt / ngày VN (kể cả đơn đang chờ), mỗi DJ 12 lượt / ngày; khóa tư vấn (advisory lock) để hai DJ không cùng lấy chỗ cuối. Trên máy: mỗi dòng chạy 1 lượt, lặp lại tối đa 8 phút một lần, bộ nhớ ≤ 32 dòng. Bộ đệm máy chủ 10 giây, tối đa 4 kho.
- Gỡ dòng: người mua, DJ hoặc quản trị (GET/POST /api/admin/radio) ẩn được, không hoàn tiền (đã phát), không bao giờ xóa; tài khoản bị xóa thì dòng tự ẩn.
- 🛑 MNL_RADIO_OFF=1: không nhận đơn, không lên sóng, bảng tin không hiện dòng nào của đài; đơn đang chờ vẫn hủy / hoàn tiền bình thường. Nghề đài vẫn chơi được.
- Bản đồ: lô mới ở Hẻm Hoa Giấy (2.5D, mặt tiền ăng-ten + đèn ON AIR, phòng làm việc riêng: kệ băng đĩa, bàn biên tập, bàn trộn âm, tủ máy); phố cổ điển: biển 📻 Đài phát thanh ở Khu văn phòng. Hướng dẫn từng bước ngày đầu (🧭) cho cả hai giao diện, hai kiểu phố.
- Đủ bộ như các nghề khác: hành trình nghề (5 đoạn truyện, kỷ vật micro bọc mút xanh), chứng chỉ Phát thanh viên cơ bản, danh hiệu, thăng chức, tip, quà, đánh giá, đồ nghề, thi đua NPC, quy mô + 10 gói chuyên môn, từ ngữ riêng của nghề, tiếng Anh cho mọi chữ mới.
- Dữ liệu: bước SCHEMA_VERSION 70 của đài (63–69, 71–73 của nhánh khác; sau khi gộp careers-integ SCHEMA_VERSION là 73): bảng mới radio_lines + 5 index; chỉ thêm, không FK, không backfill. Save: chỉ bản ghi nghề `radio` (ngủ đông khi chưa làm). Quay về 2.4.66: save chưa làm đài đọc bình thường; save đã làm đài phải `scripts/strip_new_careers.py strip --careers radio` rồi `restore` khi lên lại. 2.4.66 chạy trên CSDL 70 không DDL, giữ nguyên dòng (tests/test_radio_compat.py).
- Tests: tests/test_career_radio.py (24), tests/test_radio_station.py (13), tests/test_radio_compat.py (3), tests/radio-ui.mjs (15); số nghề +1 (60 với lễ tân và giao dịch viên ngân hàng).

## town-fair

🎪 Hội chợ việc làm (Hội chợ phố): hội chợ hằng tuần, mọi nghề dựng gian hàng phục vụ người chơi khác (chủ game 21/10: "làm hết đi"). Khác hẳn 🏮 Hội chợ dân gian / Chợ đen (game/fair*.py): module, tên và bảng riêng. game/town_fair.py (luật), game/town_fair_content.py (trình diễn, tình huống, quà), public/js/v4/town-fair.js + town-fair-data.js + css/town-fair.css.
- Lịch: thứ Bảy 14:00–17:00 giờ Việt Nam (ngoài giờ cao điểm 17:30–20:00, xa Bang chiến Chủ nhật 20:00). Admin (Phố dịch vụ trong /admin): tắt/bật lịch hằng tuần, mở một kỳ đặc biệt 1–6 giờ, đóng sớm. 🛑 MNL_FAIR_OFF=1: không mở, không giảm giá, không lên bảng tin; kỳ đã diễn ra vẫn chốt và giữ quà.
- 🧑‍🔧 Gian hàng: mỗi người một gian mỗi kỳ, cho một nghề đã làm; chọn giảm 10/15/20/25/30% trên giá 🛎️ Phố dịch vụ CỦA CHÍNH MÌNH cho nghề đó (service_market.quote / legacy_quote hỏi town_fair.discount), không bao giờ dưới sàn / giá gốc NPC; dịch vụ 🤝 thương lượng không giảm. Dọn gian hoặc hết hội chợ: giá về như cũ ngay. Tiền vẫn đi đúng đường Phố dịch vụ (giữ tiền, 95 % / đốt 5 %, hoàn đủ): không có đường thanh toán mới.
- 🎭 Trình diễn: mỗi nghề một tiết mục riêng (33 nghề) + 3 tiết mục theo nhóm (ẩm thực, cửa hàng, dịch vụ, văn phòng, ngoài trời); diễn 5 phút, tối đa 8 lần, cách nhau 10 phút; người xem trong lúc diễn được 🎟️ tem nghề đó.
- 😵 Oái oăm (luật chủ game): 16 tình huống (khách thử không mua, trẻ con làm đổ đồ, mưa bất chợt, gian bên mở nhạc to, cúp điện, bảo vệ nhắc lấn lối, khách quên ví…), mỗi cái 3 cách xử lý, đổi điểm gian (0–100, bắt đầu 70); không trả lời trong 10 phút: −5. Tối đa 6 lần mỗi kỳ, chỉ khi gian đang mở.
- 🎟️ Tem: mỗi nghề một tem mỗi kỳ, từ đơn đã xong ở gian của nghề đó (đặt trong giờ hội chợ, xong trong 48 giờ sau vẫn tính) hoặc xem trình diễn. 3 / 6 / 10 tem đổi 🎟️ Khách dạo hội chợ / 🏮 Khung đèn lồng hội chợ / 🎡 Thổ địa hội chợ (Phong cách, giữ mãi); đổi đúng một lần (fair_rewards + dòng live_effects 'tfair' trong một giao dịch).
- 🏆 Bảng kỳ hội chợ: 🛎️ Phục vụ nhiều nhất và 🌟 Điểm gian hàng (không khí ± sao khách chấm); chốt 48 giờ sau khi đóng (housekeeping, đúng một lần), lưu vào fair_events.board, không xóa; top 3 mỗi bảng nhận 🛎️ Gian hàng đắt khách / 🌟 Gian hàng được yêu, gian phục vụ ≥ 3 khách nhận 🎪 Chủ gian hội chợ. Bảng tin phố: lúc mở và lúc chốt.
- Lối vào: Khu phố › 🎪 Hội chợ việc làm (lên thanh chính khi đang mở), biển 🎪 trên đảo 2.5D và trong 🧭 Chỉ đường / Tiện ích, dòng bảng tin một lần mỗi kỳ (/api/news `tfair`, bản cũ bỏ qua), giá hội chợ "🎪 −N%" trong Phố dịch vụ. API: GET /api/townfair/view|board; POST /api/townfair/open|pct|close|show|moment|watch|claim; admin GET/POST /api/admin/townfair.
- Dữ liệu: SCHEMA_VERSION 74 (70–73 của nhánh khác): bảng mới fair_events, fair_booths, fair_stamps, fair_rewards, fair_config + index; chỉ thêm, không FK, không backfill, KHÔNG thêm khóa save (quà là món Phong cách trong journey.spend.own; 2.4.66 chỉ kiểm định dạng id và không hiển thị id lạ; dòng live_effects 'tfair' để chờ). Cache có giới hạn (cấu hình 30 giây, bảng / danh sách gian LRU 32).
- Kiểm thử: tests/test_town_fair.py (13), tests/test_town_fair_compat.py (2.4.66 trên DB 74: không DDL, giữ dòng, quà chờ rồi trả đúng một lần, save hợp lệ); tests/__init__.py đặt MNL_FAIR_OFF=1 cho các bài khác.

## hotel

🏨 Phòng cho người chơi: người chơi làm Homestay / Khách sạn cho người chơi khác thuê phòng qua đêm hoặc vài giờ (chủ game 21/10: "nghề phải tương tác người chơi với người chơi", "làm hết đi"). game/hotel_stay.py (luật), game/hotel_stay_content.py (tình huống oái oăm), public/js/v4/hotel-stay.js + public/css/hotel-stay.css (🏨 Sổ phòng). Không đổi phiên bản, chưa có dòng Có gì mới.
- Đăng ký vào 🛎️ Phố dịch vụ (service_market.register, đúng API thật) 3 dịch vụ cho cả 'homestay' và 'hotel': 🛏️ Phòng nghỉ qua đêm (1 đêm = 3 giờ thật, tối đa 3 đêm), ⏰ Nghỉ vài giờ (1 giờ thật), 💞 Phòng đôi cho cặp đôi (vợ chồng hoặc đã đính hôn, tối đa 3 đêm). Giá thường (NPC) homestay 30 / 12 / 44 xu, khách sạn 40 / 15 / 56 xu (theo giá phòng 28–48 xu của nghề Homestay); người chơi trả mặc định ×3 (90 / 36 / 132 và 120 / 45 / 168 xu), chủ chỉnh ×1–×10 hoặc 🤝 thương lượng ở 🧰 Dịch vụ của tôi. Giữ tiền (escrow), 95 % cho chủ khi trả phòng, 5 % bị đốt, mọi hủy / từ chối / khách không tới đều hoàn đủ: luật của Phố dịch vụ, không đường tiền riêng.
- Luồng: khách đặt → đơn hiện ở 📥 Đơn và 🏨 Sổ phòng của chủ (huy hiệu svc) → chủ ✅ Xác nhận (take) → khách bấm 🧳 Tôi tới rồi → chủ 🔑 Nhận phòng: chọn phòng (homestay: Đồi Thông, Sương Sớm, Gác Mái, Ban Công Hồ; khách sạn: 101, 205, 308, Suite 501 tốn 3 xu dọn), đúng lời dặn của khách (+6) hay sai (−6), phòng đôi mà xếp 2 giường đơn (−12), và xử lý tình huống lúc nhận phòng → đang ở: tình huống trong đêm tự tới theo thời gian, khách nhờ tối đa 2 việc (trả phòng muộn 1 tiếng, nâng hạng miễn phí, mang thú cưng, gối + gấu bông, mì nửa đêm, phòng bên ồn) → hết giờ hoặc khách 🧳 Trả phòng sớm (sau 15 phút) → chủ 🧾 Trả phòng với một tình huống cuối (minibar, khăn trong vali, gửi mèo, đổi 5 sao lấy giảm giá, hóa đơn công ty) → chủ nhận tiền ngay, khách thấy phần nghỉ ngơi và ⭐ chấm điểm (đánh giá của Phố dịch vụ).
- "Oái oăm" (luật chủ game 01/10): 6 tình huống nhận phòng, 11 trong đêm (2 riêng cho cặp đôi), 6 yêu cầu của khách, 5 lúc trả phòng; mỗi cái 3 cách xử lý: đổi độ hài lòng (0–100, bắt đầu 70), có cách tốn 1–5 xu của chủ (bị đốt, không trả cho ai), có cách cho trả muộn / nâng hạng. Tính khách (dễ tính / khó tính ×1,5 điểm trừ / lắm chuyện thêm 1 tình huống) và lời dặn rút theo mã đơn. Bỏ lỡ một tình huống: −8; không ai làm thủ tục trả phòng: −5. Chủ có thẻ 😊 Hài lòng TB, số lượt, xử lý / bỏ lỡ.
- Lợi ích cho khách (thật nhưng vừa phải, dùng thanh có sẵn, MỖI NGÀY VN MỘT LẦN mỗi người: bảng hotel_rest): qua đêm +45 tỉnh táo, +25 no bụng (bữa sáng), +3 tinh thần (phòng đôi +4); vài giờ +20 tỉnh táo, +1 tinh thần; hài lòng ≥ 80 thêm +1 tinh thần, < 40 thì không cộng tinh thần và tỉnh táo còn một nửa. Cặp đôi: cả hai cùng được nghỉ (người kia qua bước riêng, đúng một lần). Không in xu: tiền của chủ là tiền khách đã giữ.
- Hạn giờ: khách không tới trong 12 giờ sau khi chủ xác nhận, hoặc chủ không nhận phòng 12 giờ sau khi khách tới: tự hủy, hoàn đủ; khách chờ ở quầy ≥ 60 phút thì giao diện gợi ý hủy; quá giờ trả phòng + 30 phút không ai làm thủ tục: hệ thống tự trả phòng và trả tiền cho chủ (housekeeping, cả khi hai người đều vắng). Mỗi khách giữ tối đa 1 lượt đặt cùng lúc; mỗi phòng một khách đang ở. Nút "Xong việc" chung của Phố dịch vụ bị từ chối cho đơn phòng (phải trả phòng ở Sổ phòng).
- Đúng một lần: mọi bước khóa dòng hotel_stays (FOR UPDATE) và kiểm bước trước; chi phí của chủ và phần nghỉ của người kia ghi save trong cùng giao dịch (marriage._mutate); trả phòng đánh dấu đơn đã giao trong cùng giao dịch (service_market.deliver_in_commit) nên chợ trả tiền đúng một lần (test nhiều luồng cùng bấm).
- 🛑 MNL_HOTEL_OFF=1: không nhận đặt / không mở bán mới, Sổ phòng báo đang đóng; lượt đã trả tiền vẫn hủy / trả phòng / tự trả bình thường (không kẹt tiền). Không có cache trong bộ nhớ.
- Lối vào: Khu phố › 🏨 Sổ phòng (người làm Homestay / Khách sạn), nút 🏨 Sổ phòng trên mỗi đơn phòng trong 📥 Phố dịch vụ (cả khách lẫn chủ); huy hiệu svc cộng việc đang chờ chủ (khách ở quầy, tình huống, trả phòng). API: GET /api/hotel/view; POST /api/hotel/confirm|decline|cancel|arrive|checkin|handle|ask|leave|checkout (CSRF, rate limit).
- Dữ liệu: SCHEMA_VERSION 68 (67 của nhánh khác): bảng mới hotel_stays, hotel_hosts, hotel_rest + index; chỉ thêm, không FK, không backfill, KHÔNG thêm khóa save (chỉ đổi giá trị journey.needs.wake/full và journey.life.spirit mà 2.4.66 đã kiểm). Rollback: 2.4.66 (a808cb79) khởi động trên DB 68 không DDL, giữ dòng, save chủ / khách / người kia validate + migrate + nhận lệnh (tests/test_hotel_stay_compat.py).
- Kiểm tra: tests/test_hotel_stay.py (giá ×3/×N, cả luồng 95 %/5 % + bảo toàn tiền + chi phí đốt, "Xong việc" bị từ chối, một phòng một khách, một lượt mỗi khách, yêu cầu của khách + trả muộn, hủy / từ chối / không tới hoàn đủ, tự trả phòng khi vắng, trả phòng đúng một lần khi nhiều luồng, nghỉ một lần mỗi ngày, cặp đôi cùng nghỉ đúng một lần, công tắc tắt, danh mục tình huống), tests/test_hotel_stay_http.py, tests/test_hotel_stay_compat.py; tests/test_birth_compat.py bỏ ghim số 65 (≥ 65). scripts/browser_hotel_stay.py (chủ + khách 390×844, chủ nhận phòng 844×390, khách 844×390). Tiếng Anh: i18n/overrides.json + build.
- Ghi chú cho nhánh khác: game/birth.py và game/photo_studio.py gọi service_market.register với khóa không có trong API (emoji, max, hours, cap, session…) nên đăng ký bị bỏ qua im lặng (try/except): phòng sinh và gói chụp ảnh chưa hiện trong Phố dịch vụ.

## wedding-services

💒 Dịch vụ cưới từ người chơi: cặp đôi thuê NGƯỜI CHƠI KHÁC làm nghề phù hợp cho đám cưới của mình (chủ game 21/10 "làm hết đi": nghề phải tương tác người chơi với người chơi). game/wed_services.py, game/wed_services_content.py, public/js/v4/wed-services.js (+ public/css/wed-services.css). Không đổi phiên bản, chưa có dòng Có gì mới.
- Bốn dịch vụ đăng ký qua 🛎️ Phố dịch vụ (service_market.register): 🍽️ Tiệc cưới: nấu & phục vụ (Nhà hàng tiệc, theo bàn, tối đa 30), 💐 Hoa cưới: cổng hoa, bàn tiệc, hoa cầm tay (Tiệm hoa), 👰 Váy cưới & vest chú rể (Shop quần áo), 💄 Trang điểm & làm tóc cô dâu (Salon tóc). 📸 Ảnh cưới dùng lại gói "Ảnh đôi · cưới" của Tiệm ảnh người chơi (game/photo_studio.py), không làm trùng. Không có nghề nào hợp với MC / ban nhạc: hai mục NPC đó giữ nguyên.
- Giá: giá NPC trong kế hoạch cưới (một bàn thực đơn tiêu chuẩn 44 xu, hoa 66, váy & vest 66, trang điểm 28) × 3 mặc định; người bán chọn ×1–×10 hoặc 🤝 thương lượng. Tiền giữ (escrow) từ ví rồi tài khoản, người làm nhận 95 %, 5 % bị đốt khi giao; từ chối / hủy / quá hạn (24 giờ chưa nhận, 72 giờ chưa giao) hoàn đủ. Mọi luật chống rửa tiền, trần cặp, đúng một lần: của Phố dịch vụ.
- Cặp đôi (đã đính hôn, hoặc đã cưới mà tiệc chưa tổ chức xong): Hôn nhân › thẻ 💒 Dịch vụ cưới từ người chơi → Dịch vụ cưới › 💍 Cưới của bạn: đội ngũ đang phục vụ, đơn của cả hai vợ chồng, từng dịch vụ với người chơi đang mở (⭐, online, giá), chọn yêu cầu (thực đơn + món chính, tông màu + hoa chính, mẫu váy + đồ chú rể, kiểu trang điểm + kiểu tóc), số bàn, lời dặn → Thuê · giữ tiền (hoặc gửi giá).
- Người làm (nghề Nhà hàng tiệc / Tiệm hoa / Shop quần áo / Salon tóc): mục 💒 Đơn cưới ngay trên thanh nghề (huy hiệu qua ticker me.wedsvc) → bật dịch vụ, Nhận đơn, rồi làm việc thật 7 bước: 2 bước làm theo yêu cầu của cô dâu chú rể, 1 bước tay nghề, 3 chuyện OÁI ĂM (cô dâu nhắn 5 giờ sáng đổi màu hoa, mẹ chồng chê canh nhạt / chê váy hở vai / đòi đổi kiểu trang điểm, nhà trai báo thêm bàn phút chót, cúp điện, gió quật cổng hoa, phù dâu đổ cà phê lên váy…), bước kiểm lần cuối phải khớp yêu cầu HIỆN TẠI (đồng ý đổi thì phải theo cái mới). Mỗi bước chấm một lần trên server (khéo léo 2 / tạm ổn 1 / hỏng việc 0, tối đa 14 điểm → 1–5 ⭐). Nút Xong việc của Phố dịch vụ cũng bị từ chối cho tới khi làm đủ bước.
- Hiện ra ở đám cưới: thẻ Hôn nhân và thiệp kỷ niệm ("Tiệc do X phục vụ ⭐⭐⭐⭐", "Hoa do Y cắm"…); 💌 thiệp mời cưới cả phố có dòng "Đội ngũ người chơi"; tiệc cưới trực tiếp: MC cảm ơn từng người, bảng "💒 Đội ngũ" cạnh cổng hoa, cổng hoa và bó hoa tung theo màu người cắm hoa chọn. Ngày cưới: dịch vụ đã giao từ 3 ⭐ tính như mục NPC tương ứng cho không khí tiệc (hoa / váy / trang điểm / album), tiệc 4 ⭐ nâng thực đơn một bậc cho tiền mừng; chi phí kế hoạch không đổi. Không thuê ai thì đám cưới NPC y như cũ.
- 🛑 MNL_WEDSVC_OFF=1: không đặt mới, không làm bước, không giao (đơn đã trả chờ hoặc tự hoàn theo hạn của Phố dịch vụ); đám cưới NPC không ảnh hưởng. Bộ nhớ đệm đội ngũ mỗi cặp: 20 giây, tối đa 512 cặp.
- Dữ liệu: SCHEMA_VERSION 69 (67–68 của nhánh khác): bảng mới wedsvc_jobs + 2 index; không FK, không backfill, không khóa save mới. Kết quả đám cưới có thêm khóa tùy chọn `services`. 2.4.66 chạy trên 69 không DDL, giữ dòng, hiện đám cưới có đội ngũ, tự quyết ngày cưới của nó, đọc được save đã trả / đã nhận tiền (tests/test_wed_services_compat.py).
- Tests: tests/test_wed_services.py (giá ×3 giữ đúng một lần, yêu cầu theo đơn, ai được thuê, công tắc tắt, hoàn tiền, chấm từng bước một lần, giao chờ đủ bước rồi trả 95 %, đổi phút chót đổi bước kiểm cuối, làm ẩu ít sao, thêm bàn, đơn đặt từ danh mục chung, thương lượng, thẻ Hôn nhân / thiệp mời / ngày cưới, không thuê ai thì y như cũ, bộ nhớ đệm có giới hạn, truy vấn của dịch vụ trực tiếp), tests/test_wed_services_compat.py. Tiếng Anh: i18n/overrides.json + build.

## service-market

🛎️ Phố dịch vụ: người chơi phục vụ người chơi qua mọi nghề (chủ game 21/10). Không đổi phiên bản, chưa có Có gì mới. Chi tiết: docs/SERVICE_MARKET.md.
- Giá cho khách là người chơi: mặc định ×3 giá thường (NPC). Người bán chọn ×1–×10 cho từng dịch vụ, hoặc 🤝 Thương lượng: khách trả giá, người bán Đồng ý / Trả giá / Từ chối, tối đa 6 lượt, 12 giờ không trả lời thì hết hạn; giá luôn trong [max(giá sàn, giá thường), min(giá thường ×10, giá tối đa)]; chốt giá là giữ tiền ngay.
- Giữ tiền (escrow): từ ví rồi tài khoản, không cho nợ, dòng Sổ ví ≤ 10 triệu. Người bán Nhận đơn → Xong việc (hoặc nghề tự giao qua hook) → khách xác nhận (24 giờ không xác nhận thì tự xác nhận) → người bán nhận 95 %, 5 % phí bị ĐỐT (không vào ai). Hủy / từ chối / quá hạn (24 giờ chưa nhận, 72 giờ chưa giao): hoàn đủ. Mỗi lần tiền đi là một giao dịch (bản lưu dưới khóa revision + trạng thái đơn đổi có điều kiện): trả đúng một lần dù nhiều tab / nhiều worker; dọn hạn và trả tiền cả khi hai người đều vắng (housekeeping).
- ⭐ Đánh giá sau mỗi đơn xong (mỗi cặp 1 đánh giá được tính / 7 ngày, tài khoản ≥ 3 ngày), uy tín người bán (⭐, số đơn, 🤝 khách quen = khách ≥ 2 đơn), hiện trên thẻ chỗ làm và trong 🛎️ Phố dịch vụ (Khu phố): 🔎 Tìm (lọc theo nghề, xếp ⭐ uy tín / 💰 giá / 🟢 online / 🤝 nhiều đơn), 📥 Đơn (Cần bạn / Đang diễn ra / Đã xong, nút theo từng bước, huy hiệu qua ticker me.svc), 🧰 Của tôi (bật/tắt, ×N hoặc thương lượng, giá sàn, lời giới thiệu, uy tín). 🚩 Báo cáo trong 24 giờ sau khi giao → admin › Phố dịch vụ (đóng kèm ghi chú; không tự phạt ai), kèm tổng xu đã đốt.
- Chống rửa tiền: không tự mua của mình; cùng mạng (tag băm của lì xì / đấu trường pet / svc_net, 3 ngày) không giao dịch, trừ vợ chồng (vẫn tính trần); mỗi cặp tối đa 5 đơn/ngày và 60 triệu xu/tuần; tài khoản dưới 7 ngày chung trần 500.000 xu/ngày với chuyển khoản (bank_xfer.count_out); một đơn tối đa 50 triệu (dịch vụ khai giá tối đa cao hơn thì theo đó), đơn chỗ làm cũ tối đa 1 triệu; chặn nhau thì không giao dịch.
- Đơn chỗ làm hiện có (việc kế tiếp của nghề, đơn nhân viên, món ở quầy) vào danh mục (career 'job', quay 'dish'): giá ×3 (hoặc theo người bán, thương lượng được), trả 95 % + đốt 5 % (cột work_service_orders.fee), giữ tiền ví rồi tài khoản, cùng luật chống rửa tiền; bật ở 🧰 thì ai cũng đặt được dù chỗ làm để Bạn bè. Giữ nguyên chặn khai thác: thưởng lãi khách ghé quầy vẫn tối đa 2× giá gốc món; thưởng 40 % lãi đơn nhân viên chỉ tính lãi thật ở giá thường. Đơn tạo trước bản này giữ điều kiện cũ (100 %).
- Cho các nghề mới (Lễ tân, sinh con, chụp ảnh, giao dịch viên…): service_market.register(career, service_id, spec) với name, base (số hoặc hàm), unit, duration, floor (vd phòng sinh ≥ 500.000), max_price, qty_max, deliver(db, provider_sid, buyer_sid, order) -> dict, on_buyer/on_provider(state, order), confirm, requires, check, can_provide, pay_to; giao bằng deliver(store, …) hoặc result['svc_done'] trong lệnh của nghề.
- Dữ liệu: SCHEMA_VERSION 63 (chỉ thêm bảng svc_settings, svc_orders, svc_reviews, svc_rep, svc_flags, svc_net, cột work_service_orders.fee mặc định 0, index work_reviews_provider; không FK, không backfill, không khóa save mới). 2.4.66 chạy trên 63 không DDL, đọc được bản lưu có giá ×3, trả đơn chỗ làm sẵn sàng theo điều kiện cũ; đơn bản mới tạo mà bản cũ chưa nhận thì bản cũ từ chối (stale_offer), khách hủy được, hoàn đủ (tests/test_service_market_compat.py).
- Tests: tests/test_service_market.py (giá ×3/×N/sàn/số lượng, thương lượng 6 lượt + hết hạn, escrow đúng một lần khi nhiều yêu cầu cùng lúc, phí đốt + bảo toàn tiền, hoàn tiền, cùng mạng/vợ chồng/trần cặp/tài khoản mới/chặn, hook giao + on_buyer, svc_done, uy tín/khách quen/báo cáo, đơn chỗ làm ×3 + thương lượng + 95 %, trần thưởng quầy, lãi thật nhân viên, xóa tài khoản), tests/test_service_market_http.py, tests/test_service_market_compat.py; scripts/browser_service_market.py (2 người chơi, 390×844 + 844×390). tests/test_work_visits.py cập nhật theo ×3 và 95 %. Dev: MNL_SVC_DEMO=1 thêm 🧋 Pha trà tại nhà để thử.
- 🏥 Phòng sinh của người chơi và 📸 thợ ảnh người chơi hiện trong 🛎️ Phố dịch vụ (trước đây register() bị từ chối vì khóa spec sai, lỗi bị nuốt nên không hiện): thẻ có giá, ⭐ và nút mở đúng luồng riêng (Nhà & Gia đình › 👶 Đón con chung chọn sẵn phòng; tờ đặt chụp của tiệm, chọn sẵn gói). Đặt, giữ tiền, trả tiền vẫn ở birth_stays / photo_orders: Phố dịch vụ từ chối đặt / trả giá / cài ×N cho các dịch vụ này (own_flow / own_settings), không có đường trả tiền thứ hai. Spec mới `open` + `providers` + `offer` + `setup`; server gọi service_market.install_own() lúc khởi động; tests/test_service_market.py OwnFlow, tests/test_birth.py, tests/test_photo_studio.py. Không đổi schema, không khóa save mới.

## birth

🏥 Phòng sinh & nhận nuôi: đón con chung (và con riêng) giờ phải mất tiền, có giá sàn (chủ game 21/10: "sinh con ok rồi, và phải mất tiền ra, đặt tiền tối thiểu và không được ít hơn mức đó. Thay luồng nhận con như hiện tại luôn"). game/birth.py, public/js/v4/birth.js. Không đổi phiên bản, chưa có dòng Có gì mới.
- 🏥 Sinh con: vợ hoặc chồng chọn phòng sinh ở Nhà & Gia đình › 👶 Đón con chung: **Nhà hộ sinh Phố Mây** (NPC, giá cố định 800.000 xu, luôn còn chỗ: không ai bị chặn) hoặc **phòng sinh của người chơi** (chủ homestay, giá do chủ đặt, **không dưới 500.000 xu**, tối đa 5.000.000 xu). Đặt tên bé, chọn **ai trả** ("Tôi trả" / "Nhờ người ấy trả"), tùy chọn mời điều dưỡng. Lời mời gửi người kia; **chưa trừ đồng nào cho tới khi người kia bấm Đồng ý**. Lúc đó người trả trả trọn giá: ví trước rồi tài khoản, không quẹt thẻ tín dụng, không mắc nợ, không dùng quỹ chung; dòng Sổ ví ≤ 10 triệu.
- Đã đặt → bấm 🏨 **Nhận phòng** (vợ hoặc chồng) → ở phòng **3 giờ thật** (đếm ngược, thanh tiến độ) → bé chào đời: khoảnh khắc chào đời (🏥 → 👶, tim bay, một lần mỗi thiết bị, tắt chuyển động khi giảm chuyển động) → 🤱 Bế bé → thẻ bé như cũ, thêm dòng "🏥 Chào đời ở … · 🩺 Điều dưỡng … hỗ trợ". Hết giờ thì bé tự chào đời ở lần đọc tiếp theo (mở Nhà & Gia đình, vào nhà) hoặc khi bấm 👶 Đón bé (đồng hồ chạm 0 tự bấm). **Hủy trước khi nhận phòng: hoàn đủ** về đúng nơi đã trả (tiền mặt về ví, phần tài khoản về tài khoản); đã nhận phòng thì không hủy.
- 📄 Nhận nuôi: phí giấy tờ ở **Trung tâm bảo trợ Phố Mây 300.000 xu** (mức tối thiểu chủ game đặt), cùng quy tắc đồng ý/ai trả; bé về ngay khi người kia đồng ý. **Con riêng** (Góc chăm riêng › jr_hh_adopt bé) cũng trả phí này (ví trước rồi tài khoản, không thẻ); client cũ không gửi `fee` thì bị từ chối kèm giá, không trừ gì.
- 🩺 Điều dưỡng (tùy chọn): người chơi đã bắt đầu nghề Điều dưỡng thấy thẻ "🩺 Ca sinh cần điều dưỡng" (ca đã đặt/đang ở, cặp có mời), bấm Nhận hỗ trợ (người đầu tiên được nhận; tối đa 3 ca cùng lúc; không tự đỡ ca nhà mình). Bé chào đời **khỏe hơn**: no bụng / sạch sẽ / vui vẻ 85 (thay vì 65), gắn bó 10. **Không in xu**: điều dưỡng không nhận tiền (nhận lời cảm ơn qua thông báo).
- 🏡 Chủ homestay (quy mô nghề Homestay cấp ≥ 1) thấy thẻ "Phòng sinh của bạn": đặt tên, giá (≥ 500.000, ≤ 5.000.000), mở/tạm đóng; xem số bé đã chào đời, ⭐ đánh giá, ca đang ở / đã đặt. Một phòng nhận tối đa 2 ca đang ở cùng lúc (ca đã đặt chờ nhận phòng). Tiền của cặp được **giữ ở lượt đặt** (escrow) tới khi bé chào đời: **đốt 5%**, 95% về ví chủ phòng qua marriage_effects (cộng ở lần tải sau). Đổi giá / đóng phòng trước khi người kia đồng ý: lời mời tự hủy, không ai mất tiền. Phòng biến mất (chủ xóa tài khoản) trước khi nhận phòng: hoàn đủ. Sau khi sinh, cặp chấm 1–5 sao một lần.
- Tiền: NPC (800.000) và phí nhận nuôi (300.000) là **xu bị hút hẳn**; phòng người chơi: 5% bị đốt, phần còn lại chỉ là tiền chuyển từ cặp sang chủ phòng (không sinh xu). Không dùng price_index (giá chủ game đặt).
- Ly hôn / xóa tài khoản khi đang có lượt đặt: lời mời hủy, tiền đã trả hoàn đủ cho người trả (marriage_effects; người trả là người xóa tài khoản thì thôi).
- 🔌 Chỗ nối cho chợ dịch vụ (game/service_market.py, nhánh khác, SCHEMA 63): nếu import được, game/birth.py đăng ký spec `('homestay'|'hotel', 'phong_sinh')` với `floor=500000` (getattr, lỗi thì bỏ qua). Hiện phòng người chơi dùng bảng riêng birth_rooms. Khi chợ chạy đặt chỗ, chỉ cần thay 2 hàm: `rooms(db, viewer)` (danh sách phòng đang mở) và `_release(db, stay)` (tiền giữ đi đâu khi bé chào đời); đồng ý, trả tiền, ở phòng, chào đời, hoàn tiền vẫn ở game/birth.py.
- Luồng cũ (không xóa, không sửa gì): bé đã có và bản giữ riêng sau chia tay giữ nguyên; **lời mời đón con miễn phí đang chờ lúc triển khai vẫn được đồng ý như trước** (miễn phí, sinh thì chờ 1 ngày lịch VN). family_child_request mới (client cũ) bị từ chối "Tải lại trang để xem cách mới". Có lời mời cũ đang chờ thì không đặt phòng mới được (trả lời/hủy nó trước). Nếu bằng cách nào đó bé đã có trong lúc đang ở phòng (rollback 2.4.66 nhận lời mời cũ) thì phòng sinh được hoàn đủ.
- Lệnh mới (POST /api/marriage/…, qua family.act: rid + biên nhận, khóa save của cả hai): family_birth_book {kind, name, where: 'npc'|'agency'|id phòng, price (giá đã thấy, sai là price_changed), payer: 'me'|'partner', nurse}, family_birth_answer {id, answer}, family_birth_cancel, family_birth_checkin, family_birth_done, family_birth_rate {id, stars}, family_birth_nurse {id} (chỉ save của điều dưỡng), family_room_set {name, price, open} (chỉ save chủ phòng). Đúng một lần: mọi thao tác khóa dòng birth_stays (FOR UPDATE), bé là dòng family_children (PRIMARY KEY couple, ON CONFLICT DO NOTHING); hai vợ chồng + lần đọc của trang cùng bấm: một bé, một khoản cho chủ phòng.
- Dữ liệu: **SCHEMA_VERSION 65** (63, 64 của nhánh khác): bảng mới birth_rooms, birth_stays + index (một lượt mở mỗi cặp: unique một phần). Chỉ thêm bảng/index, không FK, không backfill, **không thêm khóa save**. Bé sinh qua phòng có khối tùy chọn `birth {where, nurse, at}` trong JSON của family_children: 2.4.66 bỏ qua và giữ nguyên khi chăm/ly hôn.
- Rollback: 2.4.66 (a808cb79) khởi động trên DB 65 không DDL, giữ dòng; bé sinh qua phòng hiện, chăm, chia bản giữ riêng bình thường trên 2.4.66; save đã trả / được hoàn / nhận con riêng có phí validate + migrate + nhận lệnh trên 2.4.66 (tests/test_birth_compat.py). Trên 2.4.66 lượt đặt đang mở chỉ đứng yên (không ai mất tiền); quay lại bản này thì tiếp tục.
- Kiểm tra: tests/test_birth.py (22: sàn giá, giá đã thấy, đồng ý hai bên, không trừ khi chưa đồng ý, ví rồi tài khoản không thẻ/không nợ, hủy hoàn đủ, đúng một lần khi 2 vợ chồng + lần đọc cùng bấm, 3 lần đồng ý cùng lúc trừ một lần, phí nhận nuôi chung/riêng, escrow 95%/5%, đánh giá, sức chứa, phòng của nhà mình, điều dưỡng, bé cũ không đổi, lời mời cũ vẫn miễn phí, ly hôn hoàn tiền, chấm đỏ), tests/test_birth_compat.py (3), tests/test_family.py / test_household.py / test_cradle.py cập nhật (lời mời cũ chèn như 2.4.66 để lại; con riêng trả phí); scripts/browser_birth.py (4 trình duyệt 390×844: chủ homestay, vợ, chồng, điều dưỡng; ảnh từng bước). Tiếng Anh: i18n/overrides.json + build.

## photo

📸 Nhiếp ảnh cho người chơi (chủ game 21/10: thợ ảnh người chơi chụp cho người chơi khác, giá ×3 NPC hoặc giá thương lượng; game/photo_studio.py, public/js/v4/portrait.js, portrait-art.js). Chưa có Có gì mới, chưa đổi phiên bản.
- 🛒 Đặt chụp (người mua): từ thẻ chỗ làm của tiệm ảnh (Ghé chỗ làm › 📸 Đặt chụp ảnh) hoặc hồ sơ Phố nghề của thợ. 5 gói, giá NPC → mặc định ×3: Chân dung 300 → 900, Ảnh đôi · cưới 500 → 1.500 (cần người thương đính hôn/cưới), Gia đình 700 → 2.100 (thêm người thương, bé hoặc pet), Đầy tháng 600 → 1.800 (cần bé ở nhà; nhánh sinh con nối vào gói `day_thang`), Sản phẩm 400 → 1.200 (món của một chỗ làm đã mở). Thợ tự đặt giá, người mua trả giá được, luôn trong khoảng ×1 → ×5 giá NPC. Chọn phông mong muốn và không khí (tươi tắn / sang trọng / tinh nghịch / tình cảm), lời nhắn 80 ký tự. Xu được giữ (ví trước, rồi tài khoản; không vay) cùng một giao dịch với đơn. Ảnh chụp từ "bản chụp vẻ ngoài" lấy lúc đặt (tủ đồ + màu, vẻ ngoài người thương lấy từ bản lưu của người đó, bé, pet), nên hai người không cần online cùng lúc.
- 📷 Buổi chụp (thợ, bất kỳ cấp nào của nghề 📸 Photobooth): sổ "📸 Khách đặt chụp chân dung" ở chỗ làm (cả giao diện gọn và đầy đủ), Nhận đơn / ✕. Màn máy ảnh vẽ đúng nhân vật của khách: chọn phông (5 phông studio, phố đèn lồng, hồ sen, chợ hoa, cầu gỗ hoàng hôn, Chùa Gió Lành, đảo riêng nếu khách có đảo, cổng hoa cưới, bàn sản phẩm), ánh sáng (5), khung hình (toàn thân / nửa người / cận mặt), dáng (20 dáng đơn + 7 dáng đôi), biểu cảm, đạo cụ; rồi bấm máy: đếm 3-2-1, khách còn nhúc nhích (nhòe), đứng yên mở mắt (bấm lúc này), chớp mắt, rồi hết dáng. 3 kiểu, máy chủ chấm từng lần bấm; chọn tấm đẹp nhất, chỉnh nhẹ (độ sáng, độ ấm, mịn da, viền tối; quá tay mất 1 sao), giao ảnh. Sao 1–5 theo tấm ảnh, đúng phông/không khí khách muốn, đèn hợp phông, khung hợp gói.
- 💰 Giao ảnh: thợ nhận 95% vào ví, 5% đốt (photo_orders.pay + burn = giá, đúng từng xu). Thợ từ chối, khách hủy trước khi thợ nhận, quá hạn (48 giờ chưa nhận, 72 giờ chưa giao): hoàn đủ (khách tự hủy: vào ví ngay; còn lại: hàng live_effects 'photo', trả một lần ở lần tải sau hoặc khi mở Album).
- 🖼️ Album ảnh (Kỷ niệm › 🖼️ Album ảnh chụp, hộp thư Phố nghề › Xem): ảnh mới nhất trước, quá 60 ảnh thì ảnh cũ vào mục "Xem cũ hơn" (không xóa). Mỗi ảnh: 🙂 Đặt làm ảnh hồ sơ (hiện trên hồ sơ Phố nghề), 🖼️ Treo trong nhà (khung `anh_chup` vào túi đồ trang trí, treo tường như tranh, tối đa 12), 💾 Lưu ảnh (PNG trên máy), 👁 Ẩn/Hiện ở tiệm thợ. Thợ giữ một bản trong bộ sưu tập công khai ở thẻ tiệm.
- 🖌️ Ảnh là bản vẽ của chính game (look.js / booth-poses.js / baby-art.js / pet-art.js) từ ~1–2 KB dữ liệu đã kiểm từng mã, không có ảnh tải lên: không ai đưa được hình tùy ý lên màn hình người khác.
- 🛡️ Chống lách: cần tài khoản, tài khoản thợ đủ 3 ngày, không tự đặt tiệm mình, không qua người chặn, giá trong ×1–×5, cùng mạng không đặt/nhận/giao cho nhau (mã băm địa chỉ như lì xì/đấu trường), mỗi cặp 2 đơn/ngày (hai chiều), 5 đơn chờ/người mua, 20 đơn/thợ. Xóa dữ liệu: ảnh rời bộ sưu tập, đơn đang chờ ở tiệm được hoàn cho khách.
- 🔌 Chỗ nối Chợ dịch vụ (service_market, nhánh khác, schema 63): khởi động gọi `service_market.register('photobooth', gói, spec)` nếu module có (getattr; không có thì bỏ qua), spec có base/floor/cap/default ×3, `snapshot` và `deliver`. Cho tới lúc đó dùng đường đặt trực tiếp ở trên; MNL_PHOTO_DIRECT_OFF=1 tắt đặt trực tiếp mới, MNL_PHOTO_OFF=1 tắt cả tính năng.
- Kỹ thuật: GET/POST /api/photo/<op> (nhẹ, tự đọc/ghi bản lưu qua marriage._mutate), housekeeping hết hạn mỗi phút. SCHEMA_VERSION 66 (chỉ thêm bảng/index: photo_studios, photo_orders, photos, photo_pfp; không FK, không backfill; 63–65 của nhánh khác). Bản lưu: chỉ khóa tùy chọn journey.photo_wall; 2.4.66 tải, chơi và giữ nguyên bản lưu có khung ảnh (kể cả đang treo), khởi động trên schema 66 không chạy DDL, để hàng 'photo' chờ (tests/test_photo_studio_compat.py). Tiếng Anh: i18n/overrides.json.

## le-tan

🔑 Nghề mới Lễ tân Khách sạn Hoa Sứ (chủ game 21/10: "thêm nghề lễ tân và nhiều cái oái oăm của lễ tân nữa nhé"; game/careers/reception.py, reception_content.py, public/js/careers/reception.js). Chưa có dòng Có gì mới, không đổi phiên bản, không đổi schema (không bảng mới).
- Khách sạn nhỏ sáu phòng trên hai tầng, quầy ngay dưới: cả bảng phòng vừa một màn điện thoại dọc. Nghề làm công (operations.SALARIED, lương hợp đồng 50–64 xu khi khép ca + thưởng nhỏ mỗi việc theo chất lượng), mở từ chương 3 (journey.LATE_UNLOCKS), chưa làm thì không lưu (engine.DORMANT).
- Sáu loại việc xoay vòng (ROTA, nhận khách 3/8): 🛎️ Nhận khách — đọc lời khách để chọn yêu cầu (ngủ nông → yên tĩnh, vali to → chỗ để hành lý, đau gối → tầng trệt, đi chung → sát vách, hai giường, giường đôi, nhìn phố, giá rẻ), kéo thẻ khách vào phòng trên bảng phòng (hoặc chạm thẻ rồi chạm phòng), lấy đúng chìa trên bảng móc (móc đỏ 108 kho khăn, móc xám ổ cũ…), xếp xe hành lý (nặng dưới, dễ vỡ trên, đồ dài ở khung, mỗi tầng có sức chứa), ghi sổ giao ca chỉ việc còn dở; 🧾 Trả phòng (đối số chìa, tính tiền đêm × giá + minibar + phụ thu trả trễ − cọc, gửi hành lý thẻ hai nửa); 🧹 Điều phối dọn phòng (khách đang chờ ở sảnh trước rồi theo giờ khách tới, kiểm phòng cô Lài báo xong, nhờ người phụ khi cô quá tải); ⏰ Lịch dịch vụ sáng mai (báo thức, khay ăn sáng, xe sân bay, xe bến xe trên lịch 15 phút, hai chuyến trùng xe đối tác thì gọi hãng khác, cộng phí); 😤 Phàn nàn (nghe ra điều thật sự sai, kiểm bằng sổ hoặc tận mắt, bù theo chính sách hoặc 0 nếu không phải lỗi, ghi sổ phản ánh); 🧸 Đồ thất lạc (tìm từ chỗ cuối còn thấy đồ, đối chiếu sổ, hỏi chi tiết ẩn). Bước xếp phòng và xe hành lý chấm theo luật (mọi cách xếp đúng sức chứa, đúng yêu cầu, phòng sạch, sát vách đều đạt; chìa đi theo phòng bạn đã xếp), các bước khác chấm theo đáp án; sai thì sửa tại chỗ, lần đầu nói cách làm, lần hai chị Quyên chỉ đáp án.
- 🧪 Ca thử việc trong nghề: ba phần — khách bình thường, khách tới sớm khi phòng chưa dọn, một nhóm hai yêu cầu cùng lúc; đạt khi đúng sức chứa, đủ yêu cầu và sổ giao ca đủ việc còn dở ngay lần đầu. Phần chưa đạt nói rõ cần luyện gì và quay lại hôm sau; phần đã đạt được giữ (data.trial). Tuyển dụng: CV → phỏng vấn → buổi làm thử với chị Quyên (3 tình huống, một lựa chọn không an toàn là dừng).
- 🎭 30 chuyện oái oăm ở quầy có hậu quả kéo dài: ca trước bán trùng phòng (nâng hạng / phòng tương đương / khách sạn đối tác — tốn khác nhau, đối tác sau gửi hóa đơn và nhờ trả ơn), phòng bên tập văn nghệ, đặt 2 người tới cả nhóm (anh Tài quay lại với cả xe khách), cây khổng lồ ở sảnh, "rẻ, rộng, đẹp, yên tĩnh, nhìn ra phố" (chị Diễm quay lại với bản in 1 sao hoặc dắt hội bạn tới), báo đã dọn mà còn khăn cũ, dọa đánh giá để ở miễn phí (khách quay lại dắt bạn), bé Su mất gấu bông trước giờ xe chạy (tranh cảm ơn cất trong Sổ nghề), tổ chức cầu hôn bất ngờ, mèo Bơ "không phải quản lý", quên hộ chiếu ở két, mất điện ca tối, khách say về khuya, đoàn tới sớm 4 tiếng, đổi phòng lần thứ ba, VIP tự nhận quen giám đốc, vali nhầm giữa hai khách, đồng nghiệp tranh công (lần hai), nhân viên mới mắc lỗi mình từng mắc, cô Lài dỗi xin nghỉ, Khoa mời cà phê xin lỗi, và vòng khách quen ông Tư Bến (giữ phòng 102 nhìn cây sứ → ảnh bến sông 1975; làm ông buồn → ông sang khách sạn bên kia sông). Quan hệ với chị Quyên, Khoa, Na, cô Lài, ông Tư (0–100) đổi theo lựa chọn và mở/đóng chuyện sau; chi phí khách sạn cộng trong tổng kết ngày (quá 50 xu chị Quyên nhắc); kỷ niệm cất trong 📒 Sổ nghề. Truyện nghề 5 phần "Phòng 102 của ông Tư Bến".
- 🎖️ Thăng tiến qua ba kỳ thi theo bậc (promotion_content.STEP_BANK/EXAM_NAME, promotion._draw_qs): đón đoàn, trực ca tối, điều phối sự kiện; chức danh Lễ tân đón đoàn → Lễ tân trực ca tối → Điều phối sự kiện Hoa Sứ → Trưởng ca lễ tân → Phó quản lý → Quản lý Khách sạn Hoa Sứ → Cố vấn. Từ bậc 2 chọn hướng đi (rc_branch, đổi sau 7 ngày): 💗 chăm sóc khách (→ trưởng bộ phận trải nghiệm), 🗂️ điều hành (→ trưởng ca → quản lý khách sạn), 🎪 sự kiện (điều phối đoàn và sự kiện của phố), 🏡 tự kinh doanh (→ homestay); việc của hướng đó thưởng ×1.25 (tự kinh doanh ×1.1 mọi việc).
- Đi kèm: chứng chỉ Nghiệp vụ lễ tân cơ bản, danh hiệu 🔑 Người giữ bảng móc chìa, hướng dẫn nghề + 🧭 hướng dẫn ngày đầu (game/coach/food.py, coach-content.js sinh lại), giọng phản hồi đánh giá, tiền boa/quà, khía cạnh đánh giá, đồ nghề, việc riêng, thi đua, gói mở rộng nghề + chuyên môn (career_specialisms_58.json, mục 58 trong catalog), lô 2.5D ở bãi cỏ nam công viên (x 9,9 · y 46,6; bỏ 5 cây trồng) với mặt tiền bảng móc chìa + hoa sứ và nội thất quầy/bảng chìa/xe hành lý/ghế sảnh/ổ mèo Bơ (bundle dựng lại), giao diện cũ ở Phố dịch vụ, tiếng Anh (i18n/overrides.json + public/i18n/en.json).
- Hai giao diện (gọn/đầy đủ), điện thoại dọc và ngang, máy tính: scripts/browser_reception.py chơi ba ca thử việc và mọi loại việc ở 2 × 4 cỡ màn (360×740, 390×844, 844×390, 1366×900), không lỗi trang, không tràn ngang.
- Rollback: bản 2.4.66 đòi đúng danh sách nghề của nó. Save chưa đụng tới lễ tân không lưu khối nghề (DORMANT) nên 2.4.66 đọc và chơi tiếp được; save đã làm lễ tân phải chạy `scripts/strip_new_careers.py strip --careers reception` trước khi lùi (khối nghề, danh hiệu, thăng tiến, truyện, người thân quen cất vào file lưu trữ), `restore` trả lại y nguyên khi lên lại (tests/test_career_reception.py Rollback chạy trên `git archive a808cb79`). Không có bảng mới.
- Kiểm thử: tests/test_career_reception.py (đăng ký, mọi việc sinh ra tự giải được, sáu loại việc đầu–cuối có sửa sai, luật xếp phòng/xe, chống sửa phiếu, ca thử việc giữ phần đạt, tình huống và hậu quả, kỳ thi theo bậc, hướng đi, tuyển dụng đủ bước, rollback 2.4.66), tests/reception-ui.mjs (mọi bước của sáu loại việc và ba phần thử việc vẽ đúng, không lộ đáp án); các test đếm nghề 57 → 58; tests/test_bang.py và tests/test_auto_order_desk.py gửi bản lưu cho bản cũ ở dạng lưu thật (tests/helpers.unknown_out: lễ tân chưa đụng tới không có trong text lưu). check_task_compat với origin/main: OK. Toàn bộ test Python và node: không có lỗi mới so với origin/main (các lỗi còn lại có sẵn ở origin/main, phần lớn là test lùi bản cần git hoặc node_modules).


## ngan-hang

🏦 Nghề mới **Ngân hàng — giao dịch viên** ("Quầy số 3 xin chào!", đề xuất đã duyệt mục 2; game/careers/teller.py, teller_content.py, public/js/careers/teller.js, public/css/careers/teller.css). Không có Có gì mới, không đổi __version__.
- Quầy số 3 ở Phòng giao dịch Bến Chợ của Ngân hàng Phố, mở từ chương 3 (journey.LATE_UNLOCKS, không ghi vào unlocked khi chưa làm). Nghề làm công (operations.SALARIED): lương hợp đồng 56–70 xu/ngày khi khép ca, thưởng nhỏ mỗi khách theo chất lượng (6–8 xu × chất lượng × hệ số học việc 50% / tập sự 75% / chính thức 100%, +15% mỗi bậc của nhánh). Tiền ở quầy là tiền của ngân hàng tính bằng nghìn đồng: không bao giờ đụng ví, tài khoản hay game/bank.py của người chơi.
- Mỗi khách năm bước: nhận yêu cầu (ask) → kiểm tra thông tin → xử lý tiền → xác nhận → giao biên nhận; mọi bước chấm ở máy chủ, sai thì bước đó giữ lại để sửa, chất lượng −8/lần (sàn 60), lần sai thứ hai chị Hạnh chỉ đáp án (học việc/tập sự: ngay lần đầu). Khách là người trong phố: Bà Lựu trà đá, Dì Bảy cơm tấm, Bác Lâm phở, Ông Khang, Chị Thơ tiệm album, Anh Hùng shipper, Cụ Mến vé số…
- Việc: 💵 Rút tiền (khay tiền tự cộng: kéo hoặc chạm tờ tiền vào khay, − để bỏ, +10 một cọc; luật của khay ở máy chủ: đúng tổng, lời dặn của khách "không tờ 500"/"5 tờ 50 lì xì"/"toàn tờ nhỏ"/"ít tờ nhất", ngăn két đang hết; phiếu lệch số và chữ phải hỏi lại, phiếu thiếu chữ ký, người nhà rút hộ không có ủy quyền thì chưa chi) · 🪙 Đổi tiền lẻ (đếm tiền chủ quán đưa, đúng số cọc 10 tờ, có khi khách đổi ý giữa chừng) · 🔁 Chuyển tiền (chọn người nhận khớp cả tên, ảnh và nghề giữa nhiều người trùng tên, phí khác ngân hàng 11 nghìn, khách dặn trừ phí vào tiền chuyển) · 🐷 Gửi tiết kiệm theo mục tiêu (sửa nhà, mua xe, mở quán: góp mỗi tháng làm tròn lên 10 nghìn, sản phẩm hợp nhu cầu) · 🏧 Tiếp quỹ ATM (hộp dưới 100 tờ, đúng khe đúng mệnh giá, nạp đầy 400 tờ, hai người ký). Đầu ca đếm quỹ phong bì và so sổ bàn giao (ngày lệch thì lập biên bản, không ký); 🧾 Bàn giao cuối ca: khớp biên nhận trong khay với sổ giao dịch, tìm giao dịch treo, tính tiền quầy phải có. Về mà chưa bàn giao: chị Hạnh 2★, ngày không tính tập sự/lên chức. Ngày: thường, lương hưu, cuối tháng, hệ thống chậm, mưa (kit.daily).
- 🍵 Chuyện dài của Bà Lựu (ngày chẵn từ ngày 2, khách tiết kiệm đầu tiên của ngày): lập kế hoạch mua xe trà 12 triệu → góp tháng đầu (túi thiếu 30 nghìn, phải nói thật) → cháu xin rút (tư vấn trung thực, tính lãi mất) → đợt góp cuối → tất toán, chuyển cho đúng xưởng inox trong hai xưởng trùng tên. Xong: 5★, +12 xp, xe trà mới đứng cạnh quán trà đá trên bản đồ 2.5D (public journey.tea_cart, PhaserWorld.setTeaCart, chỉ hiện khi đã xong), bà mời ly trà đầu tiên (tl_seen).
- Tuyển dụng: ứng tuyển (CV + phỏng vấn 3 câu, có 2 câu riêng của ngân hàng) → 🎓 học việc ngắn 3 bài (tl_learn) → 📝 thi thực hành 3 phần, mỗi phần làm một lần (đếm và đổi tiền đúng cọc; chọn đúng người nhận khi có người trùng tên; phiếu ghi một số, khách nói số khác: phải làm rõ trước) — trượt thì mai thi lại đề khác, trong lúc chờ bấm 👀 Xem chị Hạnh làm (khách được phục vụ, không thưởng). Qua: 🪪 bảng tên, ⚡ thi trong 150 giây, 🎯 không xin gợi ý (thêm xp). Rồi 2 ca tập sự có chị Hạnh kèm (ca có ≥2 khách đạt và đã bàn giao) → giao dịch viên.
- Nhánh nghề (trong ngân hàng, chạy song song 🎖️ Thăng tiến): Giao dịch (cao cấp → trưởng quầy, bài xét: điều phối ca đông + tìm chỗ hụt khi bàn giao) · Tư vấn (phụ trách khách quen → chuyên viên mục tiêu tài chính; sổ tư vấn trung thực ≥2 lần thì phần câu hỏi chỉ tiêu tự đạt) · Vận hành (ATM → kiểm soát giao dịch → vận hành chi nhánh, bài xét: soát nhật ký, đối chiếu quỹ, kiểm soát kép) · Quản lý (mở từ Trưởng quầy → quản lý chi nhánh, bài xét: xếp lịch nhân sự, số quầy ngày lương hưu, chuyện trong phòng; cuối ca có thêm bước xếp ca ngày mai). Bậc của nhánh thêm bước riêng: tư vấn hẹn lịch góp, vận hành soát nhật ký máy.
- 24 chuyện oái oăm (kit.desk, dấu để lại hậu quả về sau): ca trước bàn giao thiếu (tự kiểm / báo trưởng quầy / ký đại → kiểm quỹ đột xuất), hộp bánh đầy tiền lẻ (kỷ vật → cháu cụ Mến quay lại), khách tự nhận quen giám đốc (bỏ qua kiểm giấy tờ → chủ tài khoản thật gọi tới), khách quay lại bảo thiếu tiền (bù quỹ không biên bản → quỹ hụt), máy gọi số in ba vé cùng số, sếp ép bán gói không hợp (bán → cụ quay lại đòi hủy; tư vấn đúng → sổ ghi nhận giúp khi xét chức), đồng nghiệp nhờ làm hộ rồi nhận công (→ nhờ ký thay ô kiểm soát), tiền nghi giả, ông Khang quên PIN (viết PIN lên thẻ → thẻ bị nhặt mất), mất mạng giữa giao dịch (làm lại → ghi hai lần), khách đọc sai số tài khoản (→ khoản chuyển nhầm cần gọi lại), có người chuyển nhầm vào tài khoản bác Lâm, livestream ở quầy, tiền ướt ngày mưa, các cụ xếp hàng ngày lương hưu. Sổ ghi nhận (tư vấn đúng nhu cầu, làm đúng quy trình, đi tắt, bị nhận vơ công). 3 tình huống nhiều góc nhìn (cuộc gọi lừa đảo bà cụ, chia nhỏ tiền mặt lớn, đồng chủ sổ).
- Đăng ký đủ chỗ như các nghề trước: hướng dẫn nghề + 🧭 hướng dẫn ngày đầu (coach office), truyện 5 phần "Chiếc ghế xoay ở Quầy số 3", chứng chỉ Nghiệp vụ giao dịch viên cơ bản, gói chuyên môn 10 bậc (game/data/career_specialisms_teller.json), mở rộng (scale), thi đua, giọng, tip/quà, khía cạnh đánh giá, danh hiệu c_teller, bậc thăng tiến, đồ nghề, việc riêng, lô nhà ở Khu Tri Thức (51.5–55.7, 43.5–47.7), tên/biển ở map cũ, mặt tiền 2.5D (két tròn + cọc xu), nội thất làm việc, gói 2.5D build lại, tiếng Anh (i18n/overrides.json, build en.json).
- Bản lưu / rollback: không DDL, không bảng mới, SCHEMA_VERSION giữ 62. Khối nghề `careers.teller` ngủ (engine.DORMANT) khi chưa đụng tới nên 2.4.66 đọc nguyên save. Save đã làm ngân hàng: chạy `scripts/strip_new_careers.py strip --careers teller` trước khi lùi (nay cất cả chứng chỉ teller_service: journey.certificates, study, cert_paper, khung đeo), `restore` trả lại khi lên lại. tests/test_career_teller_compat.py: 2.4.66 (a808cb79, git archive) đọc save chưa đụng; save story đã ứng tuyển, học, thi, làm 2 ngày, chuyện oái oăm, chặng Bà Lựu, chứng chỉ đeo, ca đang mở dở khách — strip xong 2.4.66 validate/migrate/public và chơi trọn một ngày nghề khác, ví không đổi; restore trên bản này trả khối nghề y từng byte. tests/helpers.as_stored: các test rollback cũ gửi save đúng như máy chủ lưu (ngân hàng chưa đụng thì không có trong bản lưu).
- Tests: tests/test_career_teller.py (28), tests/test_career_teller_compat.py (2), tests/teller-ui.mjs (14); đếm nghề 57→58 ở các test đếm (59 khi gộp cùng Lễ tân trong careers-integ).

# v2.4.71 — 2026-10-20

Không có mục Có gì mới.

## war-lineup

- 👑 Bang chủ chọn đội hình Bang chiến pet tuần (chủ game: "bang chủ được quyền chọn danh sách thú để xuất chiến nhé, hiện tại bang chủ không chọn thú xuất chiến được"). Bang chủ và Phó bang (không phải Trưởng lão) lên (như người xếp đội hình ⚔️ Thách đấu) mở 🛡️ Bang chiến › 🗓️ Bang chiến tuần › 👑 Chọn đội hình bang: danh sách thành viên với các bé của từng người (hạng, 💪), gợi ý sẵn bé mạnh nhất của mỗi người; chọn tối đa 5 người, mỗi người 1 bé, lưu trước giờ chốt (19:50). Đội hình của bang chủ thay mọi lượt tự chọn của bang tuần đó; thành viên thấy "👑 Bang chủ đã chọn đội hình" và không tự đổi hay rút được; người chọn đổi được tới lúc chốt, hoặc ↩️ Để mọi người tự chọn (giữ đội hình đang có). Chuyện trong bang và nhóm chat bang có dòng nêu tên người được chọn.
- Máy chủ kiểm: chức vụ, giờ chốt, tối đa 5, mỗi người 1 bé, bé phải là của chính người đó (ở nhà hoặc trại nuôi), đủ điều kiện như tự chọn (đang trong bang, bang có 🏝️ Đảo bang). Ảnh chụp chỉ số bé như khi tự chọn (đọc save chỉ để xem, không ghi), vẫn theo bé tới giờ chốt.
- game/pet_war.py: lệnh mới `war_team` (danh sách cho người chọn), `war_lineup {picks: [{pid, pet}]}`, `war_lineup_off`; `war` trả thêm `lead`, `can_lead`; `war_pick` / `war_unpick` trả lỗi `lead_set` khi bang chủ đã chọn. Đánh dấu bằng một dòng trong pet_war_picks (sid `~lead|bang|<id>`, không phải người chơi: mọi chỗ đọc đều bỏ qua, bản 2.4.70 cũng vậy vì không bang nào có sid đó). Không thêm bảng hay cột, SCHEMA_VERSION giữ 73, không khóa save mới. game/bang_pets.py: can_lead, role_of, roster, lock_team (khóa hàng bang trước), announce.
- Kiểm thử: tests/test_pet_war_lineup.py (đặt đội hình, thành viên không ghi đè được, Trưởng lão trở xuống bị từ chối, sau giờ chốt bị từ chối, bé của người khác bị từ chối, tự chọn vẫn chạy khi chưa có đội hình bang chủ, trận đánh bằng đội hình bang chủ; bản 2.4.70 (aeb68cc0) đọc cùng bảng vẫn đánh đúng đội hình đó).

## war-card

- 🛡️ Thẻ Bang chiến tuần cho mọi thành viên ở 🏯 trang chủ bang (chủ game: "có nơi nào đó cho mọi người ở bang thấy sự kiện bang chiến cuối tuần đi"): ngày giờ trận (CN 20:00), giờ chốt đội (19:50) và đếm ngược từng giây; trạng thái ⏳ Đang chờ / 🔒 Đội hình đã chốt / 🔴 Đang đánh / 🏁 Kết quả tuần (vô địch, á quân, dừng ở vòng nào, điểm) hoặc tuần không đủ bang; đội hình 5 ô (tên thành viên, bé, hạng, 💪, hoặc "Còn trống"), ai chọn (👑 Bang chủ/Phó bang hay mọi người tự chọn); các trận của bang (vòng, đối thủ khi đã biết, tỉ số). Nút: 👑 Chọn đội hình (Bang chủ, Phó bang: mở thẳng màn chọn đội hình), 🐾 Ghi danh / Đổi bé của tôi (khi chưa có đội hình bang chủ), 📺 Xem trận (đang đánh hoặc đã xong). Mục ⚔️ Bang có thêm dòng nhỏ trong ngày bang chiến ("🛡️ Bang chiến 20:00 hôm nay", "Đã chốt đội, sắp đánh", "đang đánh").
- ⏰ Nhắc trước 1 tiếng (18:50–19:50): mỗi bang đang hoạt động, có Đảo bang nhận một dòng ở Chuyện trong bang và nhóm chat bang "🛡️ Bang chiến 20:00 tối nay, đội hình chốt lúc 19:50…", đúng một lần mỗi tuần (bước housekeeping của đấu trường; dòng nhật ký 'war_remind' của chính bang là dấu đã nhắc, 200 bang mỗi lượt 30 giây, khóa advisory theo tuần).
- game/pet_war.py team_card (dữ liệu thẻ: một truy vấn lượt chọn của bang, thành viên, hàng pet_war; các trận và bảng xếp hạng chỉ khi đã đánh), remind_due; game/bang.py page['war'] (GET /api/bang có sẵn) và me_view mine.war (giờ trận, không truy vấn); game/bang_pets.py remind. Không đổi bảng, cột hay save. Màn đấu trường: sau giờ chốt dòng "Bang chủ đã chọn đội hình" không còn ghi "bạn không tự đổi được".
- Kiểm thử: tests/test_pet_war_card.py (thành viên, bang chủ/phó, trước và sau giờ chốt, đang đánh, sau trận: vô địch, á quân, bang không ra trận, tuần không đủ bang; giờ trận cho mục ⚔️ Bang; nhắc đúng một lần mỗi bang, bỏ bang chưa có đảo hoặc bị ẩn, theo lượt, không nhắc ngoài giờ).

# v2.4.70 — 2026-10-20

Không có mục Có gì mới.

## bang-rename

- ✏️ Bang chủ đổi được tên bang (tối đa 2 lần mỗi bang, chủ game "giới hạn 1 bang được đổi 2 lần"; theo luật tên như khi lập, không trùng bang đang hoạt động; ghi vào Chuyện trong bang, nhóm chat đổi tên theo) và huy hiệu (biểu tượng, cũng tối đa 2 lần) ở ⚙️ Cài đặt bang (chủ game: "tên bang và huy hiệu cho phép đổi nhé").

## bang-found-7d

- ⚔️ Lập bang: tài khoản đủ 7 ngày (đời thực) là lập được, thay vì 14 (chủ game: "7 ngày là tạo được bang, k phải 14 ngày"). bang_content.FOUND_ACCOUNT_DAYS = 7; vẫn cần 5 triệu xu.

# v2.4.69 — 2026-10-20

Không có mục Có gì mới (chủ game: cho người dùng mua, không thông báo).

## bang-rejoin-24h

- 🚪 Rời bang chờ 24 giờ (thay vì 48) mới vào hoặc lập bang khác (chủ game: "chỉnh lại rời bang chờ 24h nhé"). bang_content.REJOIN_HOURS = 24.

## accessories

🧰 Phụ kiện nghề (chủ game: "thêm phụ kiện vào cho người ta nhé", "phụ kiện kiểm tra tuổi hay gì đó... để check"). game/career_gadgets.py: mỗi món mua một lần bằng quỹ nghề, hiện trong Trang trí & nâng cấp (mục 🧰 Phụ kiện nghề, trên Thiết bị nghề), lệnh mới `gadget_buy {item}` (không tốn giờ tiệm).
- 🧊 Tủ trữ sữa riêng · 220 xu (Tiệm bánh & cà phê, góp ý #454 "Xác suất sữa bị hỏng trong ngày khá cao… thêm phụ kiện tủ trữ đồ riêng"): sữa tươi nhập về để được 3 ngày thay vì 2 (game/inventory.py `_receive_lot` hỏi `life_bonus` của nghề), sữa tươi đang trên kệ lúc lắp tủ cũng thêm 1 ngày; chuyện "Ca sữa tươi vừa mở có mùi chua" còn ~3,6% số ngày.
- 🥛 Tỷ lệ sữa chua giảm cho mọi người: trước đây ~22,3% số ngày từ ngày 2 (mô phỏng 20.000 ngày), giờ ~13,7% (SOUR_KEEP 0,6); có tủ ~3,6% (SOUR_KEEP_FRIDGE 0,15). Lượt bị bỏ thay bằng một chuyện bất ngờ khác chưa có trong ngày (số chuyện mỗi ngày giữ nguyên), cố định theo ngày nên tải lại không đổi.
- 📏 Máy kiểm tra độ tuổi · 120 xu (Tiệm quà mẹ & bé, góp ý #452 "khách mua mà độ tuổi nó bé hơn cái món quy định thì làm sao để bán đc"): đơn đã biết tuổi bé thì mỗi món trên kệ hiện ✓ hợp / ✗ chưa hợp; hộp khách hỏi chưa hợp tuổi thì khung 📏 nêu nhãn, lời cảnh báo và tối đa 3 món hợp tuổi, còn hàng, trong ngân sách (nút 💬 Gợi ý thay ngay trên món), bước hướng dẫn trỏ thẳng món đó. Người chơi vẫn tự tư vấn, lấy hàng, gói, kiểm. Bố mẹ lần đầu: chỉ ✓/✗ sau khi đã hỏi tuổi bé. game/giftshop.py `age_check`, chỉ là dữ liệu xem (`careers.mother_baby.age_check`), không lưu.
- Không có phụ kiện: hướng dẫn rõ hơn ở đơn "chọn quà cho bé" (cả giao diện gọn): "Hộp này chưa hợp tuổi bé: đừng bán, chọn một món có nhãn hợp tuổi, trong ngân sách, rồi bấm “💬 Gợi ý thay” ở món đó", bước hướng dẫn ghi "Hộp … chưa hợp bé N tháng: 💬 Gợi ý thay một món hợp tuổi". Không có kẹt: với giá mặc định luôn có vài món hợp tuổi trong ngân sách (ngân sách = giá hộp khách hỏi + 20 xu); hết hàng thì nhập ở Kho.
- Bản lưu: khóa tùy chọn `careers.<nghề>.gadgets = {id: {paid, day}}` (không phải mã nâng cấp: 2.4.68 từ chối mã lạ trong `upgrades`). 2.4.68 đọc được, giữ nguyên, bỏ qua (tests/test_career_gadgets.py chạy trên `git archive 289df99d`). check_task_compat OK. Tiếng Anh: i18n/overrides.json, đã build public/i18n/en.json.
- tests/test_career_gadgets.py: mua (quỹ, một lần, sai nghề, thiếu quỹ), sữa +1 ngày (kệ lúc lắp và hàng nhập), tỷ lệ sữa chua trước/sau, máy kiểm tra (gợi ý hợp tuổi, trong ngân sách, còn hàng; hết hàng; bố mẹ lần đầu), không có phụ kiện = như cũ, bản lưu chạy trên 2.4.68.

# v2.4.68 — 2026-10-20

Không có mục Có gì mới (chủ game: không thông báo).

## bang-disband

- 👑 Giải tán bang chỉ cần bấm hai lần (chủ game 21/10 "chưa giải tán được bang nhé"): 2.4.67 còn bắt gõ đúng tên bang từng ký tự, mọi lần thử trên production đều bị từ chối (400). Giờ không cần gõ; app cũ còn gửi tên thì tên được so như khóa trùng tên (bỏ hoa thường, dấu cách, dấu).

## pet-buy

- 🐾 Mua thú không còn giới hạn 10 bé một lần (chủ game 21/10 "mua thú thì k cần giới hạn tối đa đâu"): chỉ còn giới hạn chỗ ở (3 ở nhà + 30 ở trại nuôi). pets_content.BUY_QTY_MAX = 33.

## pet-autofuse

🤖 Ghép tự động đồ thú cưng (chủ game: "ghép thú thì thêm chế độ ghép tự động cho áo quần nhé"). game/pet_wardrobe.py, public/js/v4/pets.js.
- Lệnh mới jr_pet_wfuse_auto {scope: 'all' hoặc một món, max_rank (mặc định SSS), keep_worn (mặc định true), budget (bắt buộc), confirm}: ghép liên tiếp từng bộ 3 món giống hệt chưa mặc, hạng thấp trước (cùng hạng: theo thứ tự trong tiệm); trượt thì thử lại bộ đó; món mới ra ghép tiếp được. Dừng khi hết bộ ba, lượt tiếp theo vượt ngân sách hoặc số tiền đang có, hoặc đủ 50 lượt. Một lệnh = một lần lưu, trừ tiền một lần (ví trước, thiếu lấy tài khoản, như _pay); trả về tóm tắt {n, ok, lux, spent, stop, used, made, left}.
- Mỗi lượt là đúng phép ghép của jr_pet_wfuse (tách thành _fuse_three dùng chung: cùng tỷ lệ, cùng phí, cùng thứ tự roll, tháo đồ, 💎 dòng sang từ hạng A, dòng "hot"). jr_pet_wfuse giữ nguyên câu trả lời và kết quả như 2.4.67 (test so với cây 2.4.67). Tỷ lệ vẫn không hiện.
- Tủ đồ: nút 🤖 Ghép tự động (số bộ ba ghép được ngay) mở màn riêng: chọn món (tất cả / một món), ghép tới hạng, xem trước số bộ ba và phí vòng đầu, ô "Tiêu tối đa" kiểu − số + (mặc định = phí vòng đầu, chip Vòng đầu ×2 ×5), xác nhận, rồi thẻ kết quả (lượt, thành công, trượt, 💎, xu đã tốn, món mới). Máy chủ cũ (không có auto_max trong nội dung) thì không hiện nút. Điện thoại 390×844 và ngang đã kiểm.
- Không có khóa mới trong bản lưu: món sinh ra giống hệt món ghép tay, 2.4.66 / 2.4.67 đọc được bản lưu sau khi ghép tự động (test chạy trên cây hai bản đó).
- Tiếng Anh: chuỗi mới trong i18n/overrides.json, đã build public/i18n/en.json.
- tests/test_pet_wardrobe_auto.py: bằng N lần ghép tay (cùng seed), ngân sách, tiền (ví rồi tài khoản, hết tiền thì dừng), đồ đang mặc, giới hạn 50, không có bộ ba, request id gửi lại chỉ trừ một lần, bản lưu chạy trên 2.4.66 / 2.4.67.

# v2.4.67 — 2026-10-20

Gồm nội quy bang và sửa chip 💬 Nói gần đây. Không có mục Có gì mới (chủ game 21/10: "mấy cái kia update trước đi, k cần thông báo, còn update nghề làm sau"); các nghề mới và Phố dịch vụ ra ở bản sau (SCHEMA 63–72 của chúng: bảng được tạo khi bản đó lên).

## bang-rules

📜 Nội quy bang (chủ game 21/10 "bang thì thêm cái nội quy bang nữa nhé, thiếu nội quy bang rồi", "công bố bên ngoài thì có nội quy bang riêng nữa, có text và giới hạn chữ"). game/bang_code.py, SCHEMA_VERSION 73.
- Hai nội quy cho mỗi bang: 📢 Nội quy công khai (tối đa 300 ký tự, 8 dòng): hiện ngoài bang, xem trước 1 dòng trên thẻ bang ở Tìm bang, đầy đủ trên trang bang cho khách và người xin vào; 📜 Nội quy nội bộ (tối đa 1200 ký tự, 20 dòng): chỉ thành viên thấy. Tab mới 📜 trong bảng Bang.
- Bang chủ và Phó bang viết / sửa (như cách nhận người). Ô soạn có bộ đếm trực tiếp "123/300 ký tự · 3/8 dòng", 6 dòng gợi ý chạm là thêm ("Online góp quỹ mỗi tuần", "Không chửi bậy trong bang", "Bang chiến Chủ nhật 20:00 phải có mặt", "Vắng 7 ngày không báo sẽ bị mời ra"…). Lọc như khẩu hiệu: không link, e-mail, số điện thoại, từ cấm bị che. Mỗi nội quy sửa cách nhau ≥ 15 giây, cả bang tối đa 20 lần một ngày. Sửa theo phiên bản (compare-and-set): hai người sửa cùng lúc thì một người được, người kia được báo "vừa được người khác sửa"; bấm lại cùng nội dung không ghi gì thêm. Mỗi lần sửa ghi Chuyện trong bang ("📜 X cập nhật nội quy công khai của bang.") và giữ bản cũ (bang_code_hist, chỉ thêm, không xóa).
- Vào bang: bang có nội quy công khai thì phải đánh dấu "Tôi đã đọc và đồng ý nội quy bang" trước khi Vào / Xin vào / Nhận lời mời; máy chủ kiểm tra {agree, code_ver}: nội quy vừa đổi thì đọc lại; bản 2.4.66 (không gửi gì) được báo rõ "Tải lại game để đọc và đồng ý nội quy rồi vào bang nhé"; bang không có nội quy công khai vào như cũ. Lưu phiên bản đã đồng ý.
- 📜 Nội quy mới: thành viên thấy chấm đỏ trên tab 📜, thẻ "Nội quy mới" ở 🏯 và số trên nút ⚔️ Bang (kèm thông báo khi đang online) tới khi mở tab. Thành viên mới coi như đã đọc bản công khai đã đồng ý, chưa đọc bản nội bộ.
- Quản trị (trang Bang): xem cả hai nội quy, ẩn / hiện lại từng cái; chữ vẫn giữ trong dữ liệu, ghi Chuyện trong bang và ghi chú quản trị. Nội quy đã ẩn thì người xin vào không cần đồng ý; Bang chủ không đăng lại đúng chữ đã bị ẩn.
- MNL_BANG_OFF tắt cả nội quy cùng Bang. Không có khóa mới trong bản lưu.
- Cơ sở dữ liệu (SCHEMA_VERSION 73, chỉ thêm bảng và index, không FK, không backfill): bang_code (mỗi bang × loại: chữ, phiên bản, ai sửa, ẩn), bang_code_hist, bang_code_seen (đã đọc tới bản nào, bản đã đồng ý). 2.4.66 chạy trên DB này không DDL, giữ nguyên dữ liệu, vẫn vào bang được (tests/test_bang_code_compat.py).

## bang-leave

- 🚪 Rời bang thì 48 giờ sau mới vào bang khác (chủ game 21/10 "set là thoát bang thì cần 48h sau mới vào được bang khác"): áp cho vào thẳng, xin vào, nhận lời mời, được duyệt và lập bang mới (bị từ chối thì không trừ tiền). Quay lại đúng bang vừa rời thì được ngay; bị mời ra hoặc bang giải tán thì không phải chờ. Đang ở một bang thì phải rời trước rồi mới vào bang khác (hết đổi bang thẳng). game/bang.py rejoin_left/_rejoin_need, C.REJOIN_HOURS = 48, MNL_BANG_REJOIN_HOURS ghi đè (0: tắt). tests/test_bang_rejoin.py.
- 👑 Bang chủ giải tán bang không cần trao chức (chủ game 21/10 "giải tán bang k cần nhường chức nha, cho phép giải tán luôn"): mục Rời bang của Bang chủ giờ là thẻ Giải tán (gõ tên bang, bấm hai lần); thành viên ra khỏi bang và vào bang khác được ngay.

## social-chip

- 💬 Nói gần đây (bản đồ 2.5D) tự ẩn khi menu Khu phố hoặc một bảng đang mở, không còn che menu (ảnh chủ game 21/10 "cái này nó che nè").

# v2.4.66 — 2026-10-21

Một lần phát hành gom (chủ game 21/10 "cứ gom lại phát hành 1 lần … update gì đó chung chung"): sửa gõ chữ ở lì xì + 8 màn, chọn số lượng khi mua bé/linh kiện/quần áo bé, ⚔️ Thách đấu bang, xếp hạng bang = pet + công trình + cấp bang (không tính cống hiến), mua/nâng Đảo bang 1M→30M→60M→120M→200M (cần đảo để chơi Bang chiến/Luyện pet/Thách đấu; bang cũ được cấp 1), quỹ bang không giới hạn (điểm góp tối đa 50.000/ngày, Kho bang +5%/cấp), màn Bang mượt, nút Xây Đền vàng. Schema 61–62 (chỉ thêm bảng/cột). Có gì mới: 1 dòng chung.

## bang-challenge

⚔️ Thách đấu bang (chủ game 21/10: "đấu trường pets chỉ mở cho các bang hội đánh nhau thôi, thêm hoạt động đó vào cho các bang hội nhé", "các bạn trong bang xếp nhau mà chơi"; game/bang_challenge.py). Chưa có Có gì mới.
- 🐾 Đội hình bang (đứng yên, không reset theo tuần): mỗi thành viên ghi danh 1 bé (đổi/rút lúc nào cũng được), Trưởng lão trở lên xếp thứ tự (▲▼): 5 bé sẵn sàng đầu tiên ra sân, còn lại dự bị và tự vào thay khi người ra sân rời bang hoặc bé không còn ở nhà/trại nuôi. Ảnh chụp chỉ số của bé theo mọi lệnh jr_pet_* (như Bang chiến). Tách riêng với đội hình Bang chiến tuần (pet_war_picks giữ nguyên luật cũ).
- ⚔️ Thách đấu: Trưởng lão trở lên của bang A chọn bang B trong danh sách (🏆 Elo, thắng–thua, 💪 sức 5 bé, bang sức gần nhau ở trên, lý do nếu chưa thách được) và gửi lời; Trưởng lão trở lên của B Nhận/Từ chối trong 30 phút (A hủy được khi còn chờ; quá giờ thì hết hạn). Bang chọn cách nhận: Hỏi trước / Tự nhận (đánh ngay) / Không nhận (Phó bang trở lên). Nhận lời là máy chủ đánh ngay một lần (team_match, ghép cặp ngẫu nhiên theo mã trận, Trận 1→5, thắng nhiều hơn thắng, thiếu bé thua trận đó, Sân luyện pet +1%/cấp tối đa 5% như Bang chiến). Cả hai bang nhận tin trong chat bang + nhật ký bang; ai cũng xem lại được (hoạt cảnh 5 trận, bang mình bên trái).
- 🏆 Thưởng, không có xu: Elo thách đấu riêng của bang (bang_chal_team, K 24; không đụng Elo Bang chiến tuần), mỗi bé ra sân của bang thắng +10 điểm cống hiến (hòa +5 cả hai; tối đa 3 lần/người/ngày, mã theo người theo ngày nên đổi bang không cày thêm; không có gì khi thắng bang ra sân dưới 3 bé), và điểm 🐾 xếp hạng tuần (thắng 200, hòa 70, tối đa 2.000/tuần).
- Giới hạn mỗi ngày (giờ VN): 1 bang gửi 5 lời, đấu 5 trận (gửi + nhận), cùng 2 bang tối đa 2 trận (đang chờ + đã đấu), 1 bang chờ tối đa 5 lời cùng lúc, giữa 2 bang chỉ 1 lời chờ; cần ít nhất 3 bé sẵn sàng để gửi và để nhận. Bang ẩn/giải tán không hiện, không bị thách; lời đang chờ của bang đó bị hủy.
- 🏝️ Chủ game 21/10 "phải có mua đảo bang thì mới chơi được": gửi, nhận và hiện trong danh sách cần bang có Đảo bang, qua bang.has_island (bangs.isle ≥ 1). Câu từ chối: "Bang cần mua Đảo bang để thách đấu."
- Giao diện: ⚔️ Bang › 🏯 có thẻ "⚔️ Thách đấu bang" (thành tích, lời thách đấu để Nhận/✕, 3 trận gần nhất ▶, nút ⚔️ Thách đấu / 🐾 Đội hình); Đấu trường › 🛡️ Bang chiến có 2 mục ⚔️ Thách đấu | 🗓️ Bang chiến tuần (đội hình + xếp, ghi danh bé, lời thách đấu, trận của bang, 👀 Khắp phố, luật); Đảo bang › Sân luyện pet có nút ⚔️ Thách đấu bang. Huy hiệu ⚔️ Bang và một thông báo khi có lời thách mới (Trưởng lão trở lên).
- 👑 Bang mạnh nhất tuần đổi cách tính (chủ game 21/10, chốt: "đừng để cống hiến bang tính điểm nhé, hãy tính điểm của pets, công trình và cấp bang làm điểm nhé"): điểm = 🐾 Pets (Bang chiến pet tuần × 500 điểm/điểm bảng, chỉ tính sau khi các trận đã chiếu; thách đấu; 💪 chiến lực = bé mạnh nhất của mỗi thành viên hiện tại, tối đa 30 người, ÷ 2) + 🏗️ Công trình (mỗi cấp công trình trừ Đại sảnh × 150) + ⭐ Cấp bang ((cấp Đại sảnh + cấp 🏝️ Đảo bang 0–5, cột bangs.isle; nâng cấp đã xong giờ tính ngay) × 500), tất cả × Tượng bang (+2%/cấp, giữ như cũ). Điểm cống hiến không còn tính vào xếp hạng (vẫn dùng ở Cửa hàng bang). Bảng xếp hạng, thẻ bang và trang bang hiện 3 phần + tổng. Ví dụ: bang vô địch (14 điểm bảng) 7.500 > bang Đại sảnh 5 + 25 cấp công trình 6.250 > bang chỉ góp 500 triệu xu 500 (cả ba chưa có đảo; mỗi cấp đảo thêm 500).
- Kỹ thuật: lệnh mới POST /api/arena/tc, tc_find, tc_match, tc_reg, tc_unreg, tc_order, tc_send {bang, rid}, tc_answer {id, ok}, tc_cancel, tc_set {mode} (tất cả trừ tc_reg không đọc bản lưu). Thứ tự khóa như game/bang.py: các dòng bangs theo id → bang_members → bang_chal/bang_chal_team; đánh đúng một lần (open → done dưới khóa dòng, hai Trưởng lão cùng bấm Nhận: một trận, người sau nhận lại cùng trận); rid trùng trả lại lời cũ. Công tắc tắt: MNL_BANG_CHAL_OFF=1 (hoặc MNL_BANG_OFF / MNL_PET_ARENA_OFF). Hết hạn dọn trong housekeeping (pet_arena.run_housekeeping).
- SCHEMA_VERSION 61 (chỉ thêm bảng/index, không FK, không backfill, không khóa save mới): bang_chal_roster, bang_chal_team, bang_chal, pet_power (bé mạnh nhất của mỗi người, ghi trong giao dịch lệnh jr_pet_* chỉ khi đổi, và khi vào đấu trường; xếp hạng không bao giờ đọc bản lưu). 2.4.64 chạy trên DB 61 không DDL, trang bang/đấu trường cũ đọc được dữ liệu mới (dòng điểm 'chal', nhật ký 'chal'), lệnh tc_* bị từ chối 'unknown' (tests/test_bang_challenge_compat.py). Trong lúc lăn bản, tiến trình cũ vẫn tính xếp hạng theo công thức cũ: ai chốt người thắng tuần trước thì theo công thức của bản đó.
- Tests: tests/test_bang_challenge.py (21: đội hình/quyền xếp, gửi/nhận/từ chối/hủy/hết hạn, giới hạn, đánh một lần khi 3 người cùng nhận và khi nhận đua với hủy, thưởng không xu và không ghi bản lưu, đảo bang, xếp hạng 3 phần, rẻ: không đọc bản lưu), tests/test_bang_challenge_compat.py; scripts/browser_bang_challenge.py (2 bang, 390×844 và 844×390).

## bang-island-buy

🏝️ Mua Đảo bang, nâng cấp đảo, quỹ bang không giới hạn (chủ game 21/10: "đảo bang bắt phải mua nhé … sau mở rộng lên được", "mua giá như giá đảo", "có mức rẻ hơn cho đảo bang là 1m", "muốn lên thì nâng cấp tiếp, 30m thì được cấp 2", "phải có mua đảo bang thì mới chơi được", "quỹ bang cho k giới hạn", "góp 1 lần không giới hạn tiền"). Không đổi phiên bản, không Có gì mới.
- 🏝️ Đảo bang phải mua: bang lập từ bản này chưa có đảo cho tới khi Bang chủ hoặc Phó bang mua cấp 1 bằng quỹ bang (1.000.000 xu, có ngay). Nâng lần lượt cấp 2 / 3 / 4 / 5 bằng quỹ: 30 / 60 / 120 / 200 triệu xu (đúng giá Đảo Dừa, San Hô, Mây Đá, Hoàng Hôn đọc từ game/island_content.py; giá đảo riêng không qua price_index nên không nhân hệ số), xây 6 / 12 / 24 / 48 giờ thật (giàn giáo, bãi cát đang bồi + cần cẩu ở chỗ khu mới, 🚧 trên đảo và thẻ đếm giờ). Chỉ trả từ quỹ (sổ quỹ kind 'build', mã 'i:<bang>:<cấp>'), dưới khóa dòng bang: hai sĩ quan bấm cùng lúc chỉ trừ một lần, bấm lại cùng cấp trả lời "đã có" không trừ (POST /api/bang/isle {to, confirm}).
- Mỗi cấp đảo to thêm một khu (cả 2.5D và giao diện cũ, cùng tọa độ nên công trình không dời chỗ): 1 Đảo nhỏ (như đảo trước 21/10) · 2 🥋 Võ đường bờ đông · 3 🍵 Trà đình bên hồ cá bờ tây · 4 🛕 Bảo tháp trên đồi thông · 5 🗼 Hải đăng + đèn lồng vàng khắp đảo, đường đá vàng. Người trên đảo cùng lúc: 30 / 40 / 50 / 60 / 80. Đi tới khu xa: tìm đường vòng (findPath) thay vì đi thẳng rồi kẹt.
- Công trình bang cấp cao cần đảo: cấp 5–6 cần đảo cấp 2, 7–8 cấp 3, 9 cấp 4, 10 cấp 5 (công trình 5 cấp tính gấp đôi: Đại sảnh 3 → đảo 2, 4 → 3, 5 → 5). Cấp 1–4 không cần đảo. Cấp đã xây giữ nguyên, chỉ lần nâng tiếp theo phải chờ.
- Chơi trên đảo cần đảo (has_island): ra Đảo bang (chưa có đảo: nút 🏯 mở thẻ mua đảo; khách được mời không vào được), Đấu trường pet (khóa 'island': "🏝️ Mua Đảo bang" cho sĩ quan, "Nhờ Bang chủ hoặc Phó bang" cho thành viên; xếp đội / luyện pet / chọn bé Bang chiến bị từ chối 'no_island'), Bang chiến pet (bang không có đảo không cử ai: can_pick = False). Vào bang, góp quỹ, điểm danh, xây công trình, cửa hàng, chat, giờ vàng vẫn chạy khi chưa có đảo (để bang dành quỹ mua đảo).
- Bang có từ trước bản này: được đảo cấp 1 miễn phí (cột isle mặc định 1 = 'grant'; cả bang do bản 2.4.64 lập trong lúc cuốn bản). Không xóa, không đặt lại gì.
- 💰 Quỹ bang không giới hạn: bỏ trần quỹ theo Kho bang và trần 10 triệu mỗi lần góp; góp bao nhiêu tùy số tiền có (ví trước rồi tài khoản, dòng Sổ ví ≤ 10 triệu mỗi dòng), bội số 1.000; chỉ còn trần kỹ thuật (10^12 mỗi lần, 10^15 quỹ). Điểm cống hiến từ góp quỹ tối đa 50.000 điểm/ngày/người (mọi bang cộng lại) để một lần góp khổng lồ không lấn hết. Kho bang không còn nâng trần quỹ: thưởng điểm khi góp tăng từ +2% lên +5%/cấp. Ô góp: 1tr · 10tr · 100tr · Tất cả.
- Xếp hạng tuần: cấp đảo cộng vào ⭐ Cấp bang (cấp Đại sảnh + cấp đảo) × 500 của 👑 Bang mạnh nhất tuần (mục Thách đấu bang); không có phần điểm nào khác cho đảo.
- Phòng live của đảo: sức chứa theo cấp đảo (Access.cap), bước đi của cả phòng gửi gộp mỗi 0,2 giây (mỗi người bước mới nhất) nên đảo 80 người vẫn nhẹ.
- Dữ liệu: SCHEMA_VERSION 62 (61 để cho nhánh Thách đấu bang): bangs thêm cột isle (mặc định 1), isle_to, isle_started, isle_ready, isle_paid (mặc định 0), isle_how (mặc định 'grant'), ADD COLUMN IF NOT EXISTS, mặc định hằng: không viết lại bảng, không backfill. 2.4.64 chạy được trên schema 62 (tests/test_integration_compat.py Previous: khởi động không DDL, đọc trang bang, đảo, góp quỹ, điểm danh, lập bang). Lùi về 2.4.64: mọi bang lại vào đảo miễn phí, trần quỹ cũ quay lại (quỹ vượt trần vẫn giữ nguyên, chỉ không góp thêm được); cột mới nằm yên.
- Khác: scripts/check_old_safari.mjs miễn thêm hai mẫu reset() của Phaser (TweenManager.existing, TweenChain.add: tên biến rút gọn đổi theo bundle mới), có test. Dev: scripts/browser_bang_island_buy.py (BROWSER_CHANNEL=chrome dùng Chrome có sẵn).

## bang-smooth

⚔️ Bảng Bang bấm mượt, đứng yên chỗ đang bấm (chủ game 21/10 "bang bấm còn giật giật lắm nên sửa lại đi", "chọn cái nào có thể tiếp tục đóng cái đó chứ k cần phải đổi qua cái khác nhé"). Không đổi luật, không đổi schema, không Có gì mới.
- Nguyên nhân giật (đo bằng scripts/browser_bang_perf.py, 390×844, CPU chậm 4× và 12×, mạng +80 ms): mỗi lần bấm vẽ lại cả bảng bằng innerHTML hai lần (lúc chờ và lúc có kết quả) và lúc chờ làm mờ (disabled, opacity .5) mọi nút hành động trong bảng; dòng kết quả chèn lên đầu bảng đẩy mọi thẻ xuống (thẻ Cổng bang tụt 70 px ngay dưới ngón tay); phong chức làm danh sách sắp lại theo chức (người vừa phong nhảy lên chỗ khác); góp quỹ xong ô số tiền về 100.000; công trình xây xong không hiện lại nút nâng cấp cho tới khi đóng mở bảng; mỗi lần bấm ở bảng còn vẽ lại cả phố phía sau (renderMain); chạm tab không về đầu tab (cuộn nhầm phần tử).
- public/js/v4/bang.js: bảng được vá tại chỗ (morph: chỉ nút/chữ đổi mới bị đụng, danh sách có khóa data-k: thành viên, công trình, đồ, bang, đơn; cây con không đổi được trình duyệt so sánh và bỏ qua); chỉ nút vừa bấm hiện vòng xoay chờ, không làm mờ cả bảng; một lần ghi một lúc (bấm đúp không gửi hai lần; bấm xác nhận sớm hơn 200 ms sau bấm đầu không tính là xác nhận); thẻ vừa bấm giữ nguyên chỗ trên màn hình (neo cuộn); dòng kết quả nằm ở thanh dưới cùng cạnh nút chính (tự ẩn sau 6 giây nếu là tin tốt); giữ tab, số tiền góp đã chọn, thành viên đang mở, chỗ cuộn của từng tab, khung 📜 đang mở; thứ tự danh sách thành viên giữ nguyên khi bảng còn mở (người mới xuống cuối); góp quỹ xong thanh quỹ nhích ngay, trang làm mới phía sau, bấm góp tiếp được ngay; quay lại game (ẩn/hiện trang) thì làm mới bảng nên công trình vừa xong hiện nút nâng cấp cấp sau; phố vẽ lại một lần khi đóng bảng; đồng hồ đếm ngược chỉ ghi khi phút đổi; "3 giờ 60 phút" thành "4 giờ"; gõ tên bang ở Lập bang thì nút Lập bang và hình xem trước theo ngay; nút 🎆 Bắn nằm dưới nút mua (mua pháo không bị đẩy).
- ⏰ Chưa có Đền vàng (bang THE CIRCLE, chủ game 21/10 "bang chủ chưa chọn được giờ vàng của bang"): thẻ Giờ vàng có nút chính "🏗️ Xây Đền vàng · 10 triệu · 4 giờ" (giá, giờ lấy từ công trình của trang, bấm hai lần như ở 🏗️) cho Bang chủ/Phó bang; quỹ thiếu thì hiện "Quỹ còn thiếu X xu" + "🙌 Góp quỹ" (cuộn tới thẻ Quỹ bang); đang xây thì đếm ngược "xong là chọn được giờ vàng"; thành viên thấy "Nhờ Bang chủ/Phó bang xây ⏰ Đền vàng để mở giờ vàng".
- game/bang.py: 👑 Bang mạnh nhất tuần trước: tuần ra mắt (mọi bang lập tuần này, không ai thắng được tuần trước) trước đây MỖI lần vẽ trang sau một lần ghi bất kỳ đều mở giao dịch ghi + pg_advisory_xact_lock của tuần (freeze) rồi tính điểm tuần trước; nay chỉ đọc (không bang nào có trước khi tuần trước hết thì trả None). Một lần ghi của thành viên (_bump, post) bỏ cache danh sách/bảng xếp hạng như cũ nhưng giữ 👑 (hết hạn sau 15 giây như cũ). Không thêm index (bang_points giữ 35 ngày: truy vấn theo người chơi nhỏ; EXPLAIN ANALYZE các truy vấn trang đều dùng index).
- Số đo server (scripts/bench_bang.py: bang 30 người + 15 bang, 250.000 dòng điểm, 60.000 dòng nhật ký; trung vị): GET trang sau một lần ghi 13,2 → 6,5 ms (38 → 32 câu SQL, không còn giao dịch ghi); ?board=1 9,5 → 2,2 ms (15 → 9); ?q= 12,2 → 4,5 ms (22 → 16); POST (điểm danh, xây, phong chức, mời ra, vào bang, đặt khẩu hiệu, mặc đồ) 14–19 → 7–8 ms (mỗi lần ít hơn 8 câu SQL).
- Số đo máy khách (CPU chậm 12×, trung vị mỗi lần bấm, trước → sau): phản hồi đầu tiên sau khi chạm 46–80 → 12–31 ms ở các thao tác ghi; tác vụ dài (> 50 ms) ở phong chức, mời ra, mở thành viên, xây, điểm danh 1 → 0; thời gian bố cục mỗi thao tác ghi 16–38 → 5–12 ms; vẽ lại cả bảng 2 → 0 lần; số nút bị làm mờ lúc chờ 3–6 → 0 (chỉ còn nút bị khóa thật, ví dụ hết chỗ xây); thẻ Cổng bang khi xây: tụt 70 px → đứng yên. CPU 4×: không còn tác vụ dài ở cả hai bản, phản hồi ~14 ms.
- Kiểm tra: tests/test_bang_smooth.py (mới: 👑 không ghi ở tuần ra mắt, vẫn chốt khi tuần trước có bang, một lần ghi giữ 👑 bỏ bảng; hợp đồng của bang.js); scripts/browser_bang_perf.py (mới: số đo + góp 3 lần liền giữ 500.000, nâng cùng một công trình 2 lần liền thẻ đứng yên, phong chức thẻ vẫn mở, mua 3 lần vẫn ở 🛍️, ⏰ Đền vàng khi thiếu quỹ / đủ quỹ / đang xây); scripts/browser_bang.py thêm ⏰ Đền vàng cho Bang chủ và thành viên.

## buy-qty

🛍️ Chọn số lượng khi mua (chủ game 21/10: "mua bé hoặc mua linh kiện cho chọn số lượng mua nữa nhé, trang phục cũng thế"). Ba tiệm trong 🐾 Thú cưng: Tiệm (chó/mèo), 👗 Quần áo + 🪽 Cánh, 🧰 Linh kiện › Tiệm.
- Mỗi tiệm có ô Số lượng: − / ô gõ số (qtyBox) / +, nút nhanh ×1 ×3 ×5 ×10 và "Tối đa ×N" (N = mức nhỏ nhất của giới hạn lệnh, chỗ còn trống, số tiền đủ trả), dòng "N × giá = tổng"; nút chính và hộp xác nhận ghi ×N và tổng tiền. Chỉ hiện khi mua được từ 2 trở lên. Mua bé: các bé tên "Tofu", "Tofu 2", "Tofu 3"… (vừa 16 ký tự), cùng giống, cùng màu lông, mỗi bé tự gieo hạng D/C như mua lẻ.
- Máy chủ: jr_pet_adopt (chỉ from shop), jr_pet_gear_buy, jr_pet_wbuy nhận khóa tùy chọn `qty` (số nguyên thật, không bool/chuỗi/số lẻ; thiếu = 1). Giới hạn mỗi lần: bé 10 (pets_content.BUY_QTY_MAX) và không quá chỗ trống ở nhà + trại nuôi (pets.room_left; không gửi về quê), linh kiện 20 (pet_tiers.GEAR_QTY_MAX) và không quá chỗ trống trong túi 60, đồ 20 (pet_wardrobe.BUY_QTY_MAX) và không quá chỗ trống trong tủ 150. Nhận nuôi ở Chân Nhỏ vẫn từng bé một (qty ≠ 1 bị từ chối). Thiếu chỗ, thiếu tiền, ngoài mùa bán, dòng sang… thì từ chối cả lần mua, không trừ xu.
- Trả một lần qty × giá (một dòng Sổ ví "… ×N", ví trước rồi tài khoản như cũ), rồi tạo N món/bé y hệt N lần mua lẻ (cùng dạng lưu: bản cũ đọc như thường). pets._pay nay chia phần tiền mặt trên 10 triệu thành nhiều dòng ≤ journey.ROW_MAX (như bang/đảo); dưới 10 triệu giữ nguyên một dòng như trước. Mua nhiều nhất hiện nay: 10 × 30.000, 20 × 120.000, 20 × 240.000 xu, đều dưới 10 triệu.
- Kết quả lệnh giữ khóa cũ (pet, rank, gear, item = món đầu) và thêm pets / gears / items khi qty > 1. Catalogue thêm pets.buy_qty, tiers.limits.gear_qty, wardrobe.qty_max; client chỉ gửi qty khi > 1 và chỉ vẽ ô số lượng khi máy chủ có các khóa này, nên client mới trên máy chủ cũ vẫn mua lẻ được, client cũ trên máy chủ mới không đổi gì.
- Rollback: không đổi schema, không thêm khóa lưu. tests/test_pet_buy_qty.py: không qty cho ra journey + thông điệp y hệt 2.4.63 (fb4b2e82, cùng roll/giờ); bản lưu sau khi mua nhiều (6 bé, 15 linh kiện có hàng xịn, 13 món đồ, một khoản 25 triệu chia dòng) validate/migrate/nhận lệnh trên 2.4.63 và 2.4.60; mỗi giới hạn từ chối mà không trừ tiền; qty sai kiểu/âm/quá lớn bị từ chối; gửi lại cùng request_id chỉ trừ một lần, revision cũ bị từ chối.
- Tủ đồ của nhân vật (wardrobe.py, jr_wd_buy) không đổi: mỗi món chỉ sở hữu một lần nên không có số lượng.
## coach

🧭 Hướng dẫn từng bước ngày đầu cho cả 57 nghề (chủ game 21/10 từ góp ý người chơi: "ngày đầu mình cho hướng dẫn các nghề cả nhập hàng, mua bán, rồi đóng cửa… hướng dẫn từng cái từng nghề ở mode cũ và mới luôn"). Chưa có dòng Có gì mới (đề xuất cho chủ game: "🧭 Ngày đầu ở mỗi nghề có hướng dẫn từng bước: nhập hàng, bán, đóng ca. Xem lại: ⋯ → 🧭 Hướng dẫn").
- Vòng sáng trên nút thật (làm mờ phần còn lại, vòng nhấp nháy; tắt khi giảm chuyển động) + bong bóng vài chữ; bước tự qua khi người chơi bấm đúng nút và máy chủ nhận lệnh (bị từ chối thì giữ bước). "Bỏ qua" từng bước, "Tắt hướng dẫn", xem lại ở ⋯ → 🧭 Hướng dẫn trong màn làm việc. Nút không có trên màn hình (giao diện khác, tab đang đóng, sheet đóng, chưa tới lượt): vòng sáng chỉ vào tab / "Làm tiếp" / nút đóng bảng, hoặc bong bóng nói nút ở đâu; nút bị cuộn khuất thì cuộn tới. Game đã đi trước (nút sáng của game là bước sau) thì hướng dẫn đi theo.
- Mỗi nghề: Mở ca → vòng việc của nghề (từ các bước [[Nút]] của 📖 Hướng dẫn nghề, có "Chi tiết" là dòng hướng dẫn gốc) → vòng nhập hàng ở các tiệm (mở kho → đặt → đếm thùng lên kệ) → Khép ca → đọc Tổng kết (tiền vào quỹ, sao). Bước tình huống (bia → kiểm tuổi, tiền giả…) chỉ hiện khi có.
- Chạy ở cả hai giao diện làm việc (gọn / đầy đủ) và cả phố 2.5D lẫn giao diện cũ: tìm nút theo data-coach / data-command / data-action rồi theo chữ trên nút (cả tiếng Anh).
- Ai được: bản lưu mới (đặt tên với onboarding, ngày 1, chưa làm nghề nào) tự chạy ở ngày đầu mỗi nghề; người chơi cũ thấy một lần mỗi nghề chip "🧭 Có hướng dẫn mới cho nghề này · Xem ✕", không ép. Khi chạy thì gợi ý ngày đầu (tips) và thẻ "Lần đầu làm ở đây?" nhường chỗ.
- Lưu: không thêm khóa mới vào bản lưu. Đánh dấu nằm trong settings.notesSeen mà mọi bản từ 0.x đều nhận (≤ 12 id [a-z0-9-]): "co-…" đã mời/đã chạy, "cd-…" đã xong (mỗi nghề 1 bit như "gd-…"), "cn1" bản lưu bắt đầu cùng hướng dẫn; bước đang dở ở localStorage mnl.coach.run. Rollback an toàn: bản cũ chỉ không hiện hướng dẫn (tests/test_coach.py SaveCompat đối chiếu luật notes_seen của origin/main).
- Mã: public/js/tutorial/coach.js (lớp hiển thị, chip), coach-core.js (máy bước, không DOM), coach-content.js (sinh bởi `python -m game.coach` từ game/coach/*.py), public/css/coach.css; móc nhỏ: app.js (⋯ → 🧭 Hướng dẫn, TUT_OPEN), tutorial/index.js, store.js (gói bit chung), tips.js + announce.js (nhường chỗ), data-coach ở vài nút nghề. Tiếng Anh: game/coach EN → i18n/overrides.json (`python -m game.coach --i18n`, rồi `scripts/i18n_extract.py build`).
- Kiểm thử: tests/test_coach.py (mỗi nghề có bước riêng, mọi [[nút]] của bước hướng dẫn là đích hoặc chữ, nhãn/selector có thật, chữ ngắn + có tiếng Anh, file sinh mới nhất, tương thích lưu), tests/coach_engine.mjs (qua bước khi bấm, giữ bước khi bị từ chối, bỏ qua, bong bóng "ở đâu" khi thiếu nút, vòng sáng vào tab, bước tùy chọn, nhảy theo game, bit trong notesSeen), scripts/browser_coach.py (chơi theo hướng dẫn ở 2 giao diện, chụp màn hình từng bước).
## classic-type

🔤 Giao diện đầy đủ (cũ) trên điện thoại: một thang chữ gọn hơn, dễ đọc hơn (chủ game 21/10, góp ý "giao diện cũ có vẻ font to hơn khó nhìn hơn"; chỉ CSS, css/compact.css mục E, chỉ khi html không có data-clean và data-layout="phone"; giao diện gọn, bản đồ 2.5D, máy tính bảng và máy tính giữ nguyên). Không có Có gì mới, không đổi phiên bản.
- Đo trước (playwright, 54 nghề, màn làm việc + màn kế tiếp, 360×740 / 390×844 / 844×390, tính theo số ký tự): cỡ chữ hai giao diện như nhau, nhưng bản đầy đủ hiện thêm mọi dòng bản gọn ẩn đi, phần lớn ở mặc định 16 px / 1,6 của trang. Màn làm việc đầu ở 390 px: 39 % chữ nội dung và 37 % chữ trên nút từ 16 px trở lên, 53 % chữ trong bảng/danh sách 16 px; đoạn văn line-height 1,6. Ghi chú nhanh (toast) nằm đè lên tiêu đề màn làm việc ở 46/54 nghề (85 chỗ đè ở 390 px, 84 ở 360 px, 43 ở 844×390; ghi chú 2 dòng tràn xuống tiêu đề). 360 px: tiếp viên hàng không tràn ngang 18 px (dải "Thành phố · Hướng dẫn an toàn" kéo cột lưới).
- Thang mới trong các trang (sheet) của bản đầy đủ: chữ nội dung 15 px / 1,5 (--fs-3 = .9375rem trong sheet, chữ không có cỡ riêng thừa hưởng), tiêu đề thẻ 18 px (--fs-4; phần giới thiệu nghề đường phố từng 20 px), nút 15 px (nút lớn ở thanh dưới theo --fs-3), nhãn 12–14 px (--fs-1/--fs-2 giữ nguyên), tiêu đề trang 17 px (như cũ). Bộ văn phòng (kế toán DN, lương thuế, tập đoàn, nhân sự, thư ký, IT), lời khách của tiệm quần áo, tâm trạng bé (trông trẻ), tiêu đề mục gập (giáo viên, hướng dẫn viên), lời khách bàn đối chiếu (kế toán, nhà thuốc) hết ghim 16 px; nút chọn giá tạp hóa 18 → 16 px; ghi chú nhỏ giao hàng không dưới 12 px.
- Sau: màn đầu 390 px chữ nội dung ≥ 16 px 39 % → 5 %, nút 37 % → 0 %, bảng 53 % → 0 %; màn kế tiếp 22 % → 2 % (nút 26 % → 1 %); line-height chữ nội dung 1,51 → 1,45. Ghi chú nhanh nằm dưới thanh tiêu đề như giao diện gọn (không còn đè tiêu đề; còn 6 chỗ chồng chữ ở 390 px khi ghi chú hiện trên dòng đầu nội dung vài giây). Màn làm việc là một cột rộng đúng bằng sheet (cột lưới ẩn từng giãn theo dòng không xuống hàng), dải tiếp viên xuống dòng: hết tràn ngang ở 360 px. Độ tương phản chữ nội dung không đổi (≥ 4,5:1 cho 99,5 % ký tự; phần dưới 4,5 là nút/ô đang tắt và màu nhấn riêng của vài nghề, cả hai giao diện như nhau). Không đổi chiều cao nút/vùng chạm (số nút dưới 32 px trước/sau như nhau).
- Giao diện gọn: đo lại 54 nghề trước/sau, từng phần tử chữ giống hệt. Trang ở thị trấn cổ điển (ngân hàng, sổ tiệm, chuẩn bị, người quen, tủ đồ, cài đặt, xếp hạng, nhà) khi chọn bản đầy đủ trên điện thoại cũng theo thang này (chữ nội dung ≥ 16 px 13 % → 3 %).

# v2.4.65 — 2026-10-21

🛡️ Bang chiến pet chuyển sang 20:00 Chủ nhật hằng tuần (chốt đội hình 19:50; chủ game 21/10 "bang chiến diễn ra chủ nhật hằng tuần, 8h tối"); PET_WAR_DOW/HOUR vẫn chỉnh được. Dòng Có gì mới 2.4.63 sửa "tối thứ Bảy" → "20:00 Chủ nhật". Không có Có gì mới mới.

# v2.4.64 — 2026-10-21

Sửa và đổi luật sau 2.4.63 (chủ game 21/10). Không có Có gì mới.
- 🐾 Đấu trường: bé thứ 2, 3 ra sân không còn mờ/nghiêng (hiệu ứng gục `fill:'forwards'` của bé trước được hủy khi bé mới vào); một bước hiệu ứng lỗi không còn làm đứng cả trận (bắt lỗi từng bước).
- 🐾 Đấu trường chỉ dành cho bang ("ẩn đi, chỉ dành cho bang", "chỉ mở cho các bang hội đánh nhau"): bỏ lối vào ở Thêm/Tiện ích/Khu phố và nút ⚔️ ở Thú cưng (mở từ ⚔️ Bang / Đảo bang); tab chỉ còn 🛡️ Bang chiến và 🎯 Luyện pet; đấu xếp hạng 1v1, giao hữu và giải tuần đóng (server từ chối: bang_only / cup_closed); luyện và xếp đội cần đang ở bang (no_bang). `pet_arena.BANG_ONLY` (True). Dữ liệu cũ giữ nguyên.
- ⚔️ Lập bang: bỏ điều kiện chức danh — chỉ cần tài khoản đủ 14 ngày và 5.000.000 xu ("ai cũng lập được").
# v2.4.63 — 2026-10-21

Ra mắt Bang, Đảo bang, Xây trên đảo, Đấu trường pet (chủ game 19–20/10). Gồm các nhánh island-build, bang, pet-arena, bang-island, tích hợp + review fixes + chế độ duyệt thành viên (schema 56–60, chỉ thêm bảng/cột). Phí giữ tài sản lớn nay tính đảo 60% + công trình 20% (chủ game chốt 20/10). Công tắc tắt khẩn: MNL_BANG_OFF, MNL_ISLAND_BUILD_OFF, MNL_PET_ARENA_OFF, MNL_BANG_ISLAND=0. Có gì mới: 4 dòng.

## island-build

🏗️ Xây trên đảo (chủ game 19/10 "công trình trên đảo k kiếm tiền, xây dựng nơi riêng, nhà này kia thôi", "thời gian lên đảo thoải mái"):
- Ô đất theo đảo (game/island_build_content.py PLOTS = public/js/island-layout.js plots, cùng số, cùng thứ tự; tests/test_island_build.py so hai danh sách): Đảo Dừa 6, San Hô 10, Mây Đá 16, Hoàng Hôn 24, mỗi đảo có ô ⚓ sát biển. Biệt thự San Hô dời sang tây (0,27; 0,47), Hoàng Hôn dời lên bắc (0,40; 0,31) để không ô nào khuất sau biệt thự trên bản đồ 2.5D; vài cây dừa, suối nước nóng/lửa trại Mây Đá dời chỗ; cầu tàu San Hô dài thêm 0,01 chạm bờ (trước đây cuối cầu và bờ hở 0,009, người chơi kẹt trên cầu).
- 8 công trình × 3 cấp, trả đủ một lần mỗi cấp (ví trước rồi tài khoản, không vay, ví nợ thì không xây; dòng sổ ví ≤ 10 triệu, kind 'life', như mua đảo), xây theo giờ thật (giàn giáo + ⏳ cho tới giờ): 🛖 Nhà sàn 2/4/7 triệu · 6/12/24 g; 🏡 Biệt thự biển 8/14/22 triệu · 18/30/48 g; 🏰 Lâu đài 25/40/60 triệu · 36/48/48 g (chỉ Mây Đá, Hoàng Hôn, 1/đảo); 🌳 Công viên 1,5/3/5 triệu · 6/12/18 g; 🏊 Hồ bơi 3/6/10 triệu · 8/16/24 g; ⛳ Sân golf mini 6/10/16 triệu · 12/24/36 g (1/đảo); 🏕️ Khu cắm trại 1/2/4 triệu · 6/10/16 g; ⚓ Bến du thuyền 5/9/15 triệu · 12/24/36 g (ô sát biển, 1/đảo). Tối đa 2 đội thợ (2 công trình đang xây) mỗi đảo.
- Không công trình nào kiếm tiền: không thuê, không vé, không thu nhập. Phá bỏ (hoặc hủy khi đang xây) nhận lại 20% tiền đã bỏ vào ô (thu hồi vật liệu); bán đảo thì công trình trên đảo được phá dỡ cùng, nhận 20% đó cùng 60% giá đảo.
- Lệnh mới jr_isle_build {island, plot, kind, confirm}, jr_isle_up {island, plot, confirm}, jr_isle_raze {island, plot, confirm}, jr_isle_use {trip, plot}. Khối lưu mới journey.islb (khóa tùy chọn, bản cũ bỏ qua; không thêm khóa vào journey.island). Bảng island_builds (bản sao của islb, ghi trong cùng giao dịch lưu: storage command_commit) cho khách, danh sách đảo mở và bảng xếp hạng đọc.
- Trên đảo (cả 2.5D và giao diện cũ): ô trống có cọc, giàn giáo + lưới xanh (+ cần cẩu cho biệt thự/lâu đài) với ⏳ giờ còn lại, xây xong thì hiện công trình theo cấp; người chơi đi vòng qua nhà và công trường (tìm đường mới, island-layout.js findPath). Hồ bơi/công viên/golf/cắm trại/bến là chỗ chơi (tư thế, mọi người thấy), mỗi lần dùng +1 tinh thần, tối đa 3 lần/ngày (server kiểm người đó đang ở trên đảo có công trình đó). Nhà: chạm cửa → xem bên trong (phòng có đồ theo cấp); chủ đảo chạm ô trống hoặc nút 🏗️ để xây.
- Hộp thoại 🏝️: thẻ mới 🏗️ Xây (bản đồ nhỏ các ô, chọn ô → danh sách công trình / nâng cấp / phá bỏ, một nút chính), thẻ 🌍 Ghé đảo (lời mời + đảo đang mở cửa).
🌍 Đảo mở cửa: chủ đảo bật "Mở cửa cho mọi người" trên chuyến đang mở; ai trong hành trình, không ở trại tạm giữ, không chặn nhau (hai chiều) đều ghé được từ 🌍 Ghé đảo (Khu phố › Đảo mở cửa); tối đa 40 người trên đảo (chủ + bạn bè + khách, đếm dưới khóa dòng chuyến; phòng live cũng giới hạn 40); một lần ghé một đảo; về phố là rời đảo; chủ "Mời về" từng người hoặc đóng cửa (khách về phố, bạn bè ở lại). Bảng island_public, island_visitors.
♾️ Ra đảo không giới hạn thời gian: chuyến mở tới khi chủ kết thúc, bán đảo, reset, nhập bản lưu (như cũ). Cột island_trips.ends vẫn ghi (10 năm sau) để bản cũ đọc vẫn thấy chuyến còn mở; chuyến do bản cũ tạo vẫn hết sau 60 phút.
🏝️ Bảng "Đảo đẹp" (Bảng xếp hạng, danh hiệu tuần top 1 / 2–3 / 4–10: 🏝️ Đảo đẹp nhất phố, 🌴 Chủ đảo mộng mơ, ⛱️ Hội chủ đảo xinh, khung như các bảng khác): điểm hòn đảo đẹp nhất của mỗi người = Σ điểm × cấp đã xây xong (nhà sàn 10, công viên 8, cắm trại 6, hồ bơi 14, bến 18, golf 20, biệt thự 24, lâu đài 50) + 10 cho mỗi loại khác nhau; chỉ danh hiệu, không tiền.
🏛️ Phí giữ tài sản lớn và bảng 💰 Tài phú tính đảo theo giá bán lại 60% và công trình theo giá thu hồi 20% (wealth_fee.islands, wealth._extras). Trước đây phí giữ tài sản lớn chưa tính đảo.
Rollback: SCHEMA_VERSION 56 chỉ thêm bảng/index (island_builds, island_public, island_visitors), không FK, không backfill; 2.4.60 và cũ hơn không đọc. Bản lưu có journey.islb chạy được trên 2.4.60 và 2.4.34 (tests/test_island_build_compat.py), bản cũ không thu/trả gì từ công trình. Nếu lùi bản: khách 🌍 không vào được đảo (ACCESS_SQL cũ chỉ cho bạn bè), chuyến mới hiện "còn ~5 triệu phút" ở client cũ; nếu bán đảo trên bản cũ, công trình nằm yên trong bản lưu (không mất), hiện lại khi mua lại đảo. Web và live nên lên/xuống cùng nhau (live/island.py: sức chứa 40 khi mở cửa).

## bang

⚔️ Bang (chủ game 19/10; game/bang.py, game/bang_content.py, live/bangs.py, public/js/v4/bang.js, bang-tag.js, css/bang.css):
- Lập bang (lệnh jr_bang_found): tài khoản ≥ 14 ngày, có chức danh (thăng tiến ≥ 1 bậc ở một nghề), 5.000.000 xu đốt hẳn (ví rồi ngân hàng, không vay, dòng ví ≤ 10 triệu, kind 'life'). Tên theo luật tên người chơi, khóa không trùng bỏ dấu/hoa/khoảng trắng (advisory lock theo khóa tên); 16 biểu tượng, 10 màu, khẩu hiệu ≤ 60 ký tự (lọc như chat).
- Vào bang thoải mái (POST /api/bang/<op>, chỉ DB): bang mở vào ngay, bang duyệt thì xin/duyệt, lời mời theo mã PCC; đổi bang không chờ, mỗi lúc một bang (unique index); Bang chủ phải trao chức/giải tán trước. Sức chứa theo Đại sảnh 10/15/20/25/30, đếm dưới khóa dòng bang.
- Quỹ bang chỉ góp (jr_bang_give 1.000–10.000.000 xu, bội số 1.000, ghi trong giao dịch của bản lưu, id 'g:<pid>:<n>'), tối đa theo Kho bang (20 triệu → 1 tỷ); chỉ dùng xây công trình; giải tán thì đốt quỹ (dòng 'burn'), không rút, không chuyển. Thứ tự khóa: sessions → bangs (theo id) → bang_members.
- Điểm cống hiến theo người theo bang: 1 điểm/1.000 xu góp (+2%/cấp Kho bang), điểm danh +20/ngày, ngày làm việc (end_day) +10 ×3/ngày; id theo người theo ngày nên đổi bang không cày thêm được.
- Danh hiệu: Bang chủ 1, Phó bang 2, Trưởng lão 3, Tinh anh 5, Thành viên; trao chức, mời ra (Phó trở lên, không mời người cùng/cao chức); rời bang mất danh hiệu ngay. Thẻ bang + chức hiện cạnh tên trên bản đồ 2.5D (dòng thứ hai của bảng tên, màu bang), phố đi dạo cũ, chat, hồ sơ Phố nghề.
- Công trình bang (owner 19/10 "nhiều thứ cần xây và nâng cấp"): Đại sảnh 5 cấp, Kho bang 10, Xưởng may 5, Đền vàng 5, Cổng bang 5, Tượng bang 10, Sân luyện pet 10 (bang.member_perks cho đấu thú cưng sau này). Giá 1 triệu–200 triệu xu/cấp, xây 1–48 giờ thật, cấp n cần Đại sảnh cấp ⌈n/2⌉, xây 1 (Đại sảnh ≥ 3: 2) cùng lúc. Cấp công trình ×100 điểm vào xếp hạng tuần.
- Cửa hàng bang chỉ đổi bằng điểm: huy hiệu 150 (biểu tượng bang trước tên), áo đồng phục 300 (polo / hoodie ở Xưởng may 3 / áo dài ở 5, màu bang trên nhân vật), cờ bang 200 (treo trong nhà, cần Cổng 1), sơn thuyền màu bang 400 (du thuyền trên bản đồ, cần Xưởng may 2), pháo hoa bang 100 (cả phố thấy, cần Cổng 3, 10 phút/lần/bang). Xưởng may −5%/cấp cho đồ may. Đồ vẫn trong túi khi rời bang, chỉ dùng khi ở đúng bang đó.
- ⏰ Giờ vàng của bang (owner 19/10 "chủ bang có thể chọn được giờ riêng"): Đền vàng cấp 1: 1 lần/tuần 30 phút … cấp 5: mỗi ngày 60 phút; Bang chủ/Phó đặt trước ≥ 1 giờ, ≤ 7 ngày, mốc 5 phút, mỗi ngày tối đa 1, không đổi sau khi bắt đầu. Trong giờ: lãi đơn nhân viên và quầy ×2 cho thành viên, lấy mức lớn hơn với giờ vàng của phố (không cộng dồn; giờ vàng riêng từ quảng cáo vẫn nhân thêm như cũ). Tính theo thời điểm của đơn: thành viên lúc giờ bắt đầu (bang_stints) mới được; máy chủ đọc cửa sổ 1 lần/phút/tiến trình, gắn vào lệnh (không truy vấn theo đơn). Ticker báo "⏰ Giờ vàng của bang …".
- 👑 Bang mạnh nhất tuần: điểm cống hiến tuần + cấp công trình (+2%/cấp Tượng bang); đầu tuần sau chốt người thắng (bang_week_win), thành viên mang 👑 trong thẻ suốt tuần; không thưởng xu.
- Chat bang: nhóm chat (chat_channels kind 'group', owner 'bang') tự thêm/bớt theo thành viên, không tự rời/thêm/đuổi bằng tay.
- Quản trị › ⚔️ Bang: ẩn / hiện / đổi tên bang, không bao giờ xóa. Xóa dữ liệu người chơi: rời bang (Bang chủ trao cho người kế), sổ quỹ giữ dạng ẩn danh.
- Lối vào: Tiện ích › Bạn bè & khu phố › ⚔️ Bang, Thêm › Khu phố › Bang (cả giao diện cũ).
SCHEMA_VERSION 57 (56 của nhánh đảo): 11 bảng mới (bangs, bang_members, bang_stints, bang_asks, bang_fund, bang_points, bang_facilities, bang_items, bang_gh, bang_log, bang_week_win), chỉ thêm, không FK, không backfill. Bản lưu: chỉ khóa tùy chọn journey['bang'] {v, n, sum, last} (2.4.60 nhận nguyên, tests/test_bang.py Compat). Lệnh jr_bang_* chỉ client mới gửi. Không có "Có gì mới".

## pet-arena

🐾 Đấu trường pet (chủ game 19/10: "thêm thi đua nữa nhé, kết hợp với pet ra tranh đấu với bang nữa"; bang chiến: "mỗi bang đến giờ sẽ chọn các pet ra đánh với nhau, đánh 5v5 và ngẫu nhiên ấy, mỗi người chọn 1 pet … ai thắng nhiều thì vào vòng trong", "phải thêm pet đánh nhau hiệu ứng này kia nữa"). Mở ở Tiện ích → Đời sống & đi chơi (🐾 Đấu trường pet, 🛡️ Bang chiến pet), ☰ Thêm → Khu phố, và nút ⚔️ trong 🐾 Thú cưng.
- ⚔️ Trận đấu do máy chủ quyết (game/pet_battle.py, ENGINE 1): đội 1–3 bé (ở nhà hoặc trại nuôi), đánh lần lượt, bé thắng giữ máu đánh tiếp. Chỉ số thật của bé (5 chỉ số đã gồm hạng, tiềm năng, giống, huấn luyện, linh kiện) → máu/công/thủ/tốc; ngũ hành theo chỉ số giống thiên về (Hỏa/Thổ/Thủy/Mộc/Kim, khắc ×1,07 / ×0,95) và một chiêu mỗi hệ (☄️ Cầu lửa, 🪨 Khiên đá, 🌊 Sóng nước, 🍃 Dây leo, ✨ Móng vàng); 🐶 chó trụ 1 máu một lần, 🐱 mèo né giỏi hơn, 🌟 huyền thoại/thần thú +6%. RNG riêng (splitmix64) gieo từ mã trận: xem lại là y hệt trận cũ; trang chỉ diễn hoạt cảnh. Mô phỏng 1v1: hơn một hạng thắng ~74%, hơn hai hạng ~89%, đủ bộ linh kiện cùng hạng ~78%, linh kiện +10 so với +0 ~77%, khắc hệ ~62%, chó–mèo 50%, ~10 lượt một trận.
- 🏆 Đấu xếp hạng: đối thủ ngẫu nhiên cùng tầm điểm (Elo 1000, người đánh K32, người bị đánh K16), không cần online (đội của họ là ảnh chụp, cập nhật mỗi lệnh jr_pet_*). Mùa theo tuần: đầu tuần điểm kéo về nửa đường tới 1000; danh hiệu tuần (🏆 Vua đấu trường tuần / ⚔️ Cao thủ đấu trường / 🛡️ Chiến binh đấu trường) cho ai đủ 5 trận với 3 người khác nhau. Chống cày: tài khoản ≥ 1 ngày, không ghép hai máy cùng mạng (băm có muối), cùng hai người tối đa 2 trận/ngày, không gặp lại 3 đối thủ gần nhất, 20 trận/ngày; không ai hợp thì đấu tập với 🐾 Bé nhà Mây (không tính điểm). Không có xu: chỉ điểm, ⭐ và danh hiệu.
- 🤝 Giao hữu với bạn bè (không tính điểm, 20/ngày). 🎯 Thử thách: 3 đội Bé nhà Mây mỗi ngày (Dễ/Vừa/Khó = 85/100/118% sức đội mình), thắng lần đầu mỗi cái +1 ⭐ (12 lượt/ngày).
- 🏟️ Giải đấu pet tuần (game/pet_cup.py): đăng ký trong tuần, Chủ nhật 21:00 (ngoài giờ cao điểm) đấu kiểu Thụy Sĩ 3–7 vòng một lần trên máy chủ (khóa tư vấn, đúng một lần), ít hơn 4 người thì hủy; danh hiệu 👑 Vô địch / 🥈 Top 3 / 🎗️ Top 10 giải pet tuần.
- 🛡️ Bang chiến pet (game/pet_war.py): mỗi thành viên chọn 1 bé, mỗi bang 5 bé, chốt đội 20:50, Thứ Bảy 21:00 đấu loại trực tiếp (bang mạnh được miễn vòng 1 khi lẻ); mỗi trận xếp cặp ngẫu nhiên theo mã trận 5 trận 1–1 (Trận 1…5), thiếu bé thì thua trận đó, thắng nhiều hơn vào vòng trong, các vòng cách nhau 5 phút, mỗi trận 1–1 hiện sau 30 giây (cả phố xem cùng một kết quả, xem trực tiếp hoặc xem lại). Bang vô địch: 5 người ra trận nhận 🏆 Bang vô địch đấu pet, á quân 🥈 Á quân bang chiến pet; bảng xếp hạng bang theo tuần và điểm bang qua các tuần. Bang là một "loại đội" (team_kind/team_id): bản này chưa có bang nên chưa ai có đội (MNL_PET_WAR_DEMO=1 ở máy thử: 6 đội mẫu). Giờ đổi được bằng PET_WAR_DOW/PET_WAR_HOUR/PET_WAR_MIN, PET_CUP_DOW/PET_CUP_HOUR.
- 🎬 Hoạt cảnh (public/js/v4/pet-arena.js, css/pet-arena.css): bé lao tới, chớp trắng + rung khi trúng, số máu bay, CHÍ MẠNG rung sân, hiệu ứng từng hệ (cầu lửa bay, sóng nước, lá, tia vàng, khiên đá), thanh máu, gục ngã, bé thắng nhảy + pháo giấy, âm thanh nhỏ theo cài đặt; ⏩ ×2, ⏭ bỏ qua; dòng diễn biến dưới sân; điện thoại dọc/ngang và máy tính.
- 🐾 Bé không bao giờ bị thương, mất đồ hay đổi gì: không lệnh nào của đấu trường ghi vào bản lưu.
Kỹ thuật: POST /api/arena/<op> (view, lineup, fight, friend, friends, npc, replay, ladder, cup_join, cup_leave, cup_board, war, war_pick, war_unpick, war_match), giới hạn 90/phút, đánh 12/phút (ARENA_FIGHTS_PER_MINUTE). SCHEMA_VERSION 58 (56, 57 là của nhánh khác): bảng mới pet_arena, pet_arena_season, pet_arena_matches, pet_cup, pet_cup_entries, pet_war, pet_war_picks, pet_war_matches, pet_team_ladder, pet_team_rating (chỉ thêm, không FK). Không khóa save mới. lb_titles: bảng danh hiệu 'arena', 'pet_cup', 'pet_war' (pet_war 2 bậc: hạng 1–5, 6–10; khung honour-frames). Rollback về 2.4.60: không DDL (phiên bản DB cao hơn), bảng mới để nguyên, danh hiệu 'arena' hạng 1 có thể hiện "🏆 Trùm arena" tới lần làm mới hằng ngày kế tiếp (tests/test_pet_arena_compat.py). API cho bang: pet_war.register('bang', provider) với team_of / name / can_pick / facility('san_luyen_pet' → +1%/cấp, tối đa 5%), team_match(a, b, key), standings, ladder, team_rating, training_bonus. Tests: tests/test_pet_arena.py, tests/test_pet_arena_compat.py; scripts/browser_pet_arena.py. Không có Có gì mới.
## bang-island

⚔️ Đảo bang (chủ game duyệt 19/10; tắt mặc định MNL_BANG_ISLAND=0, chưa có Có gì mới):
- Lãnh địa của bang: bản đồ đảo 2.5D riêng (24 ô, lớn hơn đảo riêng) với 7 ô cố định: Đại sảnh giữa đảo, Kho bang, Xưởng may, Sân luyện pet, Đền vàng, Tượng bang giữa quảng trường, Cổng bang bên bến tàu; vườn hoa, ao sen, rừng trúc, dãy đèn lồng, đồi thông, hình nhân tập võ. Mỗi công trình đổi diện mạo theo bậc cấp 1–3 gỗ / 4–6 đá / 7–10 vàng, giàn giáo tre khi đang xây, đất trống cắm cọc khi chưa xây. Cờ và màu bang trên cổng, đại sảnh, sân đấu, cánh buồm thuyền bang; tên bang trên biển cổng. Giao diện cũ: đi dạo 2D cùng bản đồ.
- Phòng trực tiếp mỗi bang (live/bang_island.py, tối đa 40 người): thành viên và khách cùng đi, vẫy tay/vái chào/hô khẩu hiệu, nói (qua kho chat: lọc, báo cáo), đứng ở công trình; quyền vào hỏi lại mỗi 10 giây và ngay khi game server báo; di chuyển không đụng DB.
- Chạm công trình mở bảng: cấp, cấp tiếp theo, giờ xây còn lại, các nút (Nâng cấp, Góp quỹ, Đấu trường pet…) hiện là chỗ chờ cho nhánh Bang / đấu trường pet nối vào.
- Hợp đồng dữ liệu với nhánh Bang: game/bang_island.py (BangIslandView, provider), docs/BANG_ISLAND.md (JSON schema, cách nối). Không bảng mới, không khóa save mới.

## tích hợp (feat/island-bang-pets)

Gộp 4 nhánh (Xây trên đảo, Bang, Đấu trường pet, Đảo bang) và nối chúng với nhau; SCHEMA_VERSION 58 (56 đảo, 57 bang, 58 pet; Đảo bang không thêm bảng):
- 🛡️ Bang chiến pet dùng bang thật (game/bang_pets.py, đăng ký loại đội 'bang' ở game/pet_war.py): đội = bang đang ở (bang đang hoạt động, không bị quản trị ẩn), mỗi thành viên chọn 1 bé, 5 người chọn trước ra trận; Sân luyện pet +1%/cấp chỉ số bé trong bang chiến, tối đa 5% (cấp 6–10 chỉ còn tính điểm xếp hạng). Chưa vào bang: nút ⚔️ Tìm bang trong tab Bang chiến.
- 👑 Bang mạnh nhất tuần cộng điểm bang chiến pet của tuần (điểm bảng bang chiến × 100: thắng 1 trận 300, vô địch thêm 500), chỉ sau khi bang chiến xong (game/bang.py war_scores).
- ⚔️ Đảo bang bật mặc định (MNL_BANG_ISLAND=0 để tắt), nối bang thật (game/bang_island_source.py): công trình bang → ô trên đảo (kho → Kho bang, tuong → Tượng bang, cong → Cổng bang), mỗi công trình có cấp tối đa riêng (5 hoặc 10, diện mạo co giãn theo 10 bậc), xây xong theo giờ hiện ngay; thành viên (chức theo bang), khách = người đang có lời mời của bang; bang giải tán thì đảo đóng; bang bị ẩn chỉ thành viên vào được. Bang báo đảo khi vào/rời/mời ra/phong chức/mời/xây/giải tán (pg_notify op 'bang_island').
- Nút trên đảo: ⬆️ Nâng cấp chạy lệnh xây của bang (Phó bang trở lên, quỹ bang, hỏi xác nhận giá trước); 👥/💌 → Bang › Thành viên, 🪙/✨ → Bang của tôi, 👘 → Cửa hàng bang, 🏆 → Xếp hạng tuần, 🏟️ → Đấu trường pet › Bang chiến, 🎯 → Thử thách. Nút 🏯 Đảo bang trong hộp Bang. MNL_BANG_ISLAND_STUB chỉ dùng khi thiếu provider thật và không bao giờ khi có DATABASE_URL.
- i18n: giữ bản dịch cũ của “Quỹ $1 xu”, “$1 người”; từ trùng của Đảo bang dùng cách gọi của nhánh Bang (“Guild”).

## review fixes

Sửa theo hai lượt review (19/10); SCHEMA_VERSION 59 (chỉ thêm bảng/index lưu trữ, không FK, không backfill, không khóa save bắt buộc; 2.4.60 không đọc):
- 💰 Góp quỹ không bao giờ mất tiền: id sổ quỹ 'g:<pid>:<nonce>' (nonce ngẫu nhiên trong journey.bang.last.r, tùy chọn: khối cũ vẫn hợp lệ) thay cho 'g:<pid>:<n>' (n đếm lại sau reset_all / nhập bản lưu cũ → trùng id, ví bị trừ mà quỹ không tăng); nếu trùng id thì báo lỗi và hoàn cả lệnh.
- 🔒 Thứ tự khóa một chiều (dòng bang theo id rồi dòng thành viên): điểm danh khóa bang trước (không deadlock với mời ra/giải tán); duyệt đơn đọc cả hai bang rồi khóa cùng lúc theo thứ tự id (không deadlock khi người xin đang đổi bang).
- ⏰ Giờ vàng của bang chỉ tính cho thành viên vào bang ≥ 24 giờ trước giờ bắt đầu và chỉ tới lúc rời bang (bang_stints), nên nhảy bang không ăn ×2; offline bù đơn vẫn y như online. Vào bang vẫn miễn phí, giới hạn mềm 10 bang/ngày (giờ VN, cả lập bang) có thông báo rõ. Hủy giờ vàng khóa 5 phút trước giờ bắt đầu.
- ⏰ Bộ nhớ đệm giờ vàng nhỏ: chỉ cửa sổ đang quanh "bây giờ" (bắt đầu trong 1 giờ tới, kết thúc trong 3 giờ qua, mới nhất trước, ≤ 2.000) và quãng thành viên cần; mỗi tiến trình một luồng đọc (luồng khác dùng bản đang có); cửa sổ cũ hơn của từng người (bù đơn offline ≤ 14 ngày) đọc riêng mỗi 30 phút, giữ ≤ 4.096 người; không xóa đệm khi vào/rời bang (chỉ sửa đúng bang khi hủy); không bao giờ đọc trong giao dịch đang khóa bản lưu.
- 🛡️ Bang chiến: chỉ đếm lượt chọn của thành viên hiện tại; rời bang / bị mời ra / bang bị ẩn hoặc giải tán thì bỏ bé đã chọn (trước giờ chốt đội).
- 🗄️ Không để bảng phình mãi, không xóa dữ liệu: trận đấu trường > 30 ngày → pet_arena_matches_old (xem lại vẫn được), bang_log > 30 ngày (giữ 20 dòng mới nhất mỗi bang), bang_points > 35 ngày, bang_stints đã đóng > 30 ngày → bảng *_old; housekeeping 10 phút/lần, lô 500, ngoài giờ cao điểm 17:30–20:00.
- Đảo bang: giới hạn 200 lần kiểm tra quyền mỗi tick tính chung mọi phòng. Thẻ bang: đổi cài đặt bang / quản trị chỉ làm mới thẻ của thành viên bang đó.
- Thứ tự triển khai: live chạy trước khi game server tạo island_public / island_visitors thì vẫn cho chủ đảo và bạn bè vào (kiểm tra kiểu 2.4.60), tự thử lại mỗi phút. Live đọc bảng bang đã chịu được bảng chưa có (kiểm lại).
- Đường nóng: lệnh jr_pet_* không ghi lại ảnh chụp đội khi không đổi; trang bang chỉ mở giao dịch ghi khi có công trình tới giờ xong (👑 đọc trước khi chốt); ghé đảo đọc bản lưu của khách trước khi khóa chuyến.
- 🛑 Công tắc tắt khẩn (mặc định bật): MNL_BANG_OFF, MNL_ISLAND_BUILD_OFF, MNL_PET_ARENA_OFF (và MNL_BANG_ISLAND như cũ) ẩn lối vào (content.off / island build_off) và từ chối thao tác mới nhẹ nhàng; bản lưu, công trình đang xây, giờ vàng đã đặt, giải tuần và bang chiến vẫn chạy.
- 🏅 Danh hiệu tuần khi chạy lẫn 2.4.60: nếu 2.4.60 làm lượt làm mới trong ngày, tiến trình bản mới kế tiếp dựng lại dòng tuần này của Đảo đẹp, đấu trường, giải pet, bang chiến; ngày đầu tuần còn dựng lại dòng chốt tuần trước của đấu trường, giải pet, bang chiến. Không sửa được: dòng chốt tuần trước của 🏝️ Đảo đẹp (bảng là độ đẹp hiện tại) và quãng vài giờ giữa lượt của 2.4.60 và lượt dựng lại.

## cách nhận người vào bang (chủ game 20/10)

"chủ bang được quyền tắt, mở hoặc tự động duyệt member vào bang tùy chọn, hoặc là yêu cầu nghề gì trên xxx thì được … rồi được xem danh sách member, rồi đá khỏi bang"; SCHEMA_VERSION 60 (cột bangs.rules thêm bằng ADD COLUMN IF NOT EXISTS, mặc định hằng '{}', 2.4.60 không đọc bảng bang):
- ⚙️ Cài đặt bang › 🚪 Cách nhận người (Bang chủ và Phó bang): 🚫 Đóng (không ai vào/xin vào; người được mời vẫn vào, đơn đang chờ vẫn duyệt được), 🔒 Cần duyệt (đơn chờ Trưởng lão trở lên), 🚪 Tự động duyệt (đủ yêu cầu là vào ngay, chưa đủ thì báo rõ thiếu gì). Cột `open` vẫn giữ khớp (1 = tự động duyệt) cho mã cũ.
- 📋 Yêu cầu tùy chọn, áp dụng cùng lúc: một nghề từ một chức danh thật của thang thăng tiến (vd. Tiệm trà sữa từ Chủ tiệm có tiếng, bậc 2), chức danh bậc X ở nghề bất kỳ, tuổi tài khoản tối thiểu (ngày). Máy chủ kiểm từ bản lưu thật (đọc trước giao dịch, chỉ khi bang có yêu cầu) khi vào, khi xin, khi nhận lời mời và khi duyệt; đổi yêu cầu không mời ra người đã ở trong bang. Thẻ bang ở 🔎 Tìm bang và trang bang hiện cách nhận người và yêu cầu.
- 👥 Danh sách thành viên: chức, ngày vào, điểm cống hiến tuần này / tổng, lần chơi gần nhất (theo ngày); Bang chủ phong/giáng chức và mời ra bất kỳ ai, Phó bang mời ra Trưởng lão/Tinh anh/Thành viên, không ai mời ra người cùng hoặc cao chức hơn; ghế: Bang chủ 1, Phó bang 2, Trưởng lão 3, Tinh anh 5.
# v2.4.62 — 2026-10-20

🖥️ #440 (chủ game 19/10 "các nghề đều phải có cả 2 bên"): mỗi nghề chọn riêng Giao diện đầy đủ (cũ) / gọn (mới) ở nút ⋯ màn làm việc (mnl.clean.c, v4/shell.js setCleanCareer), "↩️ Theo cài đặt chung" để bỏ; thêm bản gọn cho khách sạn, tiệc, bưu điện, xưởng vẽ, luật sư, giặt ủi, hải quan; trả bản đầy đủ cho cứu hộ, y tá, công an, cà phê, quần áo, tạp hóa, kho.
📋 Đối chiếu nội bộ: bản đầy đủ mở sẵn chứng từ, chip xuống dòng; ui-kit tapSlip chặn chạm nhầm khi lướt ([data-tap-guard]).
🧹 #447 (chủ game 19/10 "làm việc tốt và phạt nặng gì đó để được xóa tội"): org.clear_one / pm_org_clear: đang công tác (không đình chỉ), CLEAR_RUN 10 ngày liên tục không vi phạm (x.clean), ★ ≥ 4.0, nộp phạt CLEAR_FINE 500k × lần thứ n từ ví → hồ sơ công tác −1 vi phạm, chuỗi ngày tốt về 0; journey.svc.pd đếm số lần (bản cũ không đọc được khóa pd: rollback dưới 2.4.62 từ chối save đã xóa vi phạm). Hải quan từ chối vì vi phạm thì chỉ cách xóa; 🎖️ Cấp bậc → Xem thêm có ô 🧹.
💌 Vòng quay 20/10: lời chúc riêng mỗi người (wish_of: 10 × 16 × 8 câu ghép theo mã quà), hiện thay đoạn chữ chung.
Có gì mới 2.4.62: 4 dòng.

# v2.4.61 — 2026-10-19

🎡 Quà 20/10 (chủ game 19/10 "vòng quay từ 100k -> 1m", "mốc 666k 888k, 1314, 520 cho có ý nghĩa", "tài khoản mới/cũ, miễn sao trong 20/10 vào là được tặng"): system_gift BROADCASTS wheel2010 (since/until 20/10 00:00 → 21/10 00:00 VN), ô quay WHEEL 100k·168k·200k·520k·666k·888k·1tr·1.314k theo trọng số (trung bình ≈ 360k), chọn theo hash sid; thẻ quà (gift.js) quay bánh xe rồi mới hiện số.
🛃 #441 Hải quan: lời từ chối vì cấp bậc Công an chỉ đường Binh nhì → Binh nhất → Hạ sĩ.
🐾 #446: nút ✓ Đổi tên bé bật ngay khi gõ (trước đó vẫn mờ tới lần vẽ lại).
Có gì mới 2.4.61: 3 dòng.

# v2.4.60 — 2026-10-19

⚡ Lag (chủ game 19/10 "check ipad phản hồi người dùng rất lag", "máy tính với đth nữa check k để lag"):
- Ảnh thú cưng nhỏ (dưới 90 px: dải bé, tủ đồ, bảng 🐾) là <img> tĩnh (pet-art.js petIMG/petPicture, blob: URL, cache 160), chỉ ảnh lớn chuyển động (.pet-live); bảng 🐾 mở 3,5 s → 0,24 s trên điện thoại chậm 4×, chờ chạm iPad 99 → 17 ms.
- pets.js không dựng lại khi HTML không đổi và bỏ qua state khi đóng; bảng tin chạy chữ tạm dừng dưới sheet (blur trên tablet); isometric-town/movement chỉ ghi DOM khi giá trị đổi.
- Server: nhớ đệm lịch x3 tuần, bộ trang trí (deco.sets_of), feedback.normalize.
🧰 Linh kiện thú cưng (chủ game 19/10 "bắt buộc cộng 10 rồi mới cho lên bậc, cũng 3 món, bậc S trở đi thì mất đồ nguyên liệu"; "làm sao nâng tới SSS, chỗ nào dễ nhìn hơn"): jr_pet_gear_fuse cần món chính +10 (có thể đang gắn), lên hạng tại chỗ về +0; trượt từ S mất 2 món nguyên liệu. Tab Linh kiện: 3 bước lên hạng, bảng loại × hạng (⬆), nút chính "Lên hạng" khi +10, nút Mua nguyên liệu D/C.
🧧 #426 lì xì: không giới hạn số người cùng mạng (IP_MAX mặc định 0, LIXI_IP_MAX=n bật lại).
🔁 #438/#439: bảng Tự đặt hàng nói hàng tới vẫn cần đếm, 🤖 Tự nhận hàng (Bộ đếm kho bậc 5) thì tự lên kệ.
Có gì mới 2.4.60: 4 dòng.

# v2.4.59 — 2026-10-19

🐾 Thú cưng (chủ game 19/10 "thêm mấy pets kì lân, rồi khủng long … ở mức S trở lên sẽ có, nhưng khi ra thì random tỷ lệ, người dùng có thể chọn pets hiện tại hoặc chuyển đổi (mình sẽ đưa cho người ta pets đó chứ k phải để người dùng chọn)"):
- ✨ 6 thần thú (pets_content fuse='myth', không bán): Kỳ Lân, Kỳ Lân Một Sừng, Khủng Long Bạo Chúa, Khủng Long Cổ Dài, Khủng Long Ba Sừng, Rồng Con. Ghép thành công lên S/SS/SSS+ có tỷ lệ ẩn (pet_wardrobe.MYTH_BP 25/30/40%) game chọn ngẫu nhiên một thần thú (petw.mo, khóa tùy chọn); người chơi giữ bé hoặc cho bé hóa thần thú (jr_pet_morph), giữ hạng/tên/đồ/linh kiện; Linh Khuyển/Mèo Thần Tài hóa thần thú vẫn là huyền thoại. pet-art: sừng, gạc, bờm cầu vồng/lửa, diềm cổ, gai lưng, mõm dài, đuôi bò sát, cánh rồng; thần thú giữ màu khi có hiệu ứng lông SSS.
Góp ý người chơi (chủ game "check feedback … xử lý luôn rồi rep luôn"):
- #426 lì xì: mỗi bao tối đa 5 lượt giật trên một mạng (LIXI_IP_MAX), bạn bè chung wifi giật được.
- #427/#431 nhập hàng: đếm món nào nhập món đó (thùng gộp, thùng tự đặt), 👥 nhân viên trong ca đếm giúp (inv_receive staff), đóng kho mà đếm đúng thì tự nhập kệ.
- #432 giao diện mới: nút giữa ở khu phố là "Về quán/Về tiệm/Về lớp…" (không start_day); ngày đầu tiên vẫn mở ca một chạm.
- #433 🔁 Tự đặt hàng cho Mẹ & bé và Nhà thuốc (khóa c.auto_order_desk, gộp theo nhà cung cấp).
- #434 bảng Online: thẻ của mình báo đã ghi nhận phút chơi và còn bao lâu lên bảng (giờ đầu tuần không tính lên bảng).
- #430 phòng hát: Hát cùng kiểm tra micro ngay khi bấm, lỗi mic không còn quay về nút ban đầu, báo đúng lý do (không có mic / bị chặn / đang bận).
Có gì mới 2.4.59: 5 dòng.

# v2.4.58 — 2026-10-19

🐾 Thú cưng (chủ game 19/10 "thêm nhiều trang phục thú cưng và linh kiện … mua được cánh nữa, cánh thì nhiều loại", "con pets nào cũng có thể lên cấp sss và huyền thoại hết nhé, khi lên thì được chọn giữ bé hiện tại hoặc đổi giống", "chưa thấy chỗ mua cánh … đổi pets đi như nào cũng k biết", "làm dễ hiểu hơn nhé", "bậc S trở lên mới mất", "khung xếp hạng thú cưng cute hơn nhé"):
- 👗 Tủ đồ của bé (game/pet_wardrobe.py, pet_wardrobe_content.py, khối journey['petw']): 108 món (24 cánh, áo, mũ, kính, vòng cổ, ổ nằm), mua hạng D/C ở Tiệm (quầy 👗 Quần áo, 🪽 Cánh), 3 món giống hệt ghép lên hạng, từ A có thể ra 💎 dòng sang (không bán), bộ Halloween / 20-10 / thủy thủ / cưới / hoàng gia, đồ hạng C+ cộng % tiền làm việc khi bé đi dạo. Đồ cũ vẫn dùng được.
- 🌟 Giống nào cũng lên SSS và huyền thoại: lên hạng chọn giữ giống bé chính hoặc đổi sang giống bé phụ; 3 SSS giữ giống thì thành huyền thoại giữ giống (petw.lg), hoặc đổi sang Linh Khuyển / Mèo Thần Tài.
- Ghép trượt chỉ mất 2 bé phụ từ hạng S (LOSE_FROM 4), hạng A trượt giữ cả ba.
- 8 giống mới trong tiệm: Maltese, Spitz, Doberman, Cavalier, Chinchilla, Angora, Savannah, Korat.
- 🧰 Linh kiện 💎 mẫu xịn (5 mẫu mỗi ô, giá ×5–×80, cộng thêm 3–16%); mẫu lưu ở petw.gm để bản cũ vẫn đọc được.
- Giao diện dễ hiểu hơn: tab có chữ, nút 🦮 Dắt bé đi dạo to rõ, hướng dẫn tủ đồ, thử đồ trên bé trước khi mua, chọn giống khi ghép.
- 🏆 Bục top 3 bảng xếp hạng thú cưng kiểu pastel tai mèo, ruy băng 🐾, hạng 4+ hình bàn chân; ảnh bé có đồ, cánh, huyền thoại giữ giống. Bé trên phố 2.5D mặc đồ tủ đồ.
Có gì mới 2.4.58: 4 dòng, chỉ về thú cưng. Bản dịch tiếng Anh cho các chữ mới.

# v2.4.57 — 2026-10-19

🐾 Thú cưng (chủ game 19/10):
- Ghép có 👑 bé chính (chủ game "chọn 1 giống chính để nó giữ lại giống đó, còn lại 2 giống kia là nguyên liệu … thất bại thì sẽ biến mất giống thêm vào … cấp A trở lên mới mất pets phụ"): jr_pet_fuse `main` (mặc định bé đầu), thành công thì bé chính lên hạng tại chỗ (giữ giống, lông, tên, huấn luyện, linh kiện; tiềm năng lấy cao hơn), hai bé kia về quê với bà; trượt dưới A giữ cả ba, từ A (LOSE_FROM) mất hai bé phụ (không vào `ret`). 3 SSS: bé chính thành huyền thoại cùng loài. Giống lai chỉ khi chọn `mix` (bé mới, ba bé về quê). Tin 🌈/🌟 trên phố: ref theo bé và hạng.
- Bỏ giới hạn 10 lần ghép/ngày (chủ game "ghép mỗi ngày k giới hạn nhé"): `day.f` chỉ đếm.
- 🏆 Bảng xếp hạng chính có mục 🐾 Thú cưng (game/pet_lb.py, đọc pet_board 'LC', theo quyền riêng tư của bảng xếp hạng): bục top 3 có vương miện, khung vàng/bạc/đồng, ảnh bé kèm hào quang; danh hiệu tuần 🐉 Vua thú cưng của phố / 🦄 Sen cưng siêu cấp / 🐾 Hội sen yêu bé với khung riêng (57, 02, 19). Không đổi leaderboard.VERSION (không dựng lại bảng).
- 🪽 Cánh SSS mới: ba lớp lông vũ đầu tròn, pastel cầu vồng, có phát sáng.
- Sửa: hình bé hạng B, SSS, huyền thoại có thuộc tính stroke lặp, hỏng khi vẽ thành ảnh (bé dắt đi dạo trên phố 2.5D).
- 📋 Bé nhà mình: danh sách dạng lưới, dải ảnh kéo ngang.
Có gì mới 2.4.57: 3 dòng, chỉ về thú cưng.

# v2.4.56 — 2026-10-19

🐾 Thú cưng (chủ game 19/10, sau khi 2.4.55 lên):
- "Bé nhà mình sao k hiển thị full các bé": dải ảnh trên cùng có mọi bé (nhà, rồi trại 🏠, quê 🌾); 📋 danh sách lọc theo chó/mèo, hạng, nơi ở; bấm bé ở trại: đón về, hoặc nhà đủ 3 thì đổi chỗ với một bé ở nhà (jr_pet_kennel `swap`, `walk`).
- Hào quang mới (pet-art.js aura): B vòng đôi + kim cương, A ngọc tím + pha lê bay, S tia nắng vàng xoay, SS tia lửa + lửa chân + đốm lửa, SSS cánh thiên thần + vầng hào quang + tia cầu vồng + mưa sao, lông 🌈 Cầu Vồng pastel; huyền thoại tia vàng, mây lành, Mèo Thần Tài vẫy lộc + mưa đồng + thỏi vàng, Linh Khuyển rồng vàng. SSS/huyền thoại vẽ to hơn một chút (khung rộng hơn).
- Luật: ghép ngay khi mua về (bỏ 3 ngày), chó mèo ghép chung (huyền thoại theo một bé bố mẹ); bé nhận nuôi/mua chỉ hạng D/C (trại D80 C20, tiệm D60 C40), linh kiện ở tiệm D/C, dạo tìm D/C; hạng cao chỉ từ ghép.
- Ẩn mọi tỷ lệ (chủ game "đừng show tỷ lệ ra"): catalogue không còn shelter/shop/fuse/mix/hybrid/legend/mutant/up, kết quả ghép không còn `chance`, linh kiện không còn `up_bp`.
Có gì mới 2.4.56: 3 dòng, chỉ về thú cưng.

# v2.4.55 — 2026-10-19

🐾 Thú cưng hạng D–SSS (chủ game 19/10; trò chơi/giải đấu thú cưng để sau). game/pet_tiers.py, mọi dữ liệu mới ở `journey.petx` (bản cũ giữ khóa lạ nên rollback về 2.4.53/2.4.54 không mất gì; bé ở trại nuôi bản cũ không thấy):
- Hạng khi nhận (Chân Nhỏ D70 C22 B6 A1,8 S0,18 SS0,02; tiệm D55 C28 B11 A4,5 S1,3 SS0,19 SSS0,0001 %); bé cũ: nhận nuôi D, mua C. Bé đang dắt và không buồn cộng 2/3/5/8/12/20/30 % tiền làm việc của chính mình (tile_match.fund_bonus, không tính lệnh quầy), trần 20k…1M/ngày, SSS thân ≥100/200: 40 %/1,25M, 50 %/1,5M; dòng "🐾 Thú cưng hạng…" không tính vào x3.
- Ghép 3 bé cùng loài (≥3 ngày, không buồn): 60/45/30/15/6/3 %, 3 SSS → huyền thoại 5 % (phí 500…5M, 10M), lệch hạng +3 %/bậc, 14 công thức lai 10 %, cùng giống 5 % đột biến; thành công: ba bé về quê với bà; trượt: giữ cả ba, mất phí; 10 lần/ngày; SS+ và huyền thoại báo cả phố (bảng tin). Trại nuôi 30 chỗ. 14 giống mới ở tiệm, 14 giống lai, 2 huyền thoại (Linh Khuyển Hoàng Kim, Mèo Thần Tài).
- 5 chỉ số + luyện (10 buổi/ngày), linh kiện 5 ô D–SSS (+1…+10, trượt không mất; ghép 3 món; dạo tìm 3 lần/ngày), bảng 💪 Lực chiến (pet_board week 'LC', GET /api/pets/board?kind=power).
- Dắt bé ở phố/đám cưới/thị trấn 2.5D (client/isometric/pet-walkers.ts, live `pt` có r/x; live/pet_rank.py chỉ giữ hạng người chơi thật có). Chó ×1,3.
- 📺 Quảng cáo (vẫn tắt): lần ghép tới +10 điểm % (ads.pet_boost trong pet_tiers._fuse, ≤95 %).
Có gì mới 2.4.55: 4 dòng, chỉ về thú cưng (chủ game).

# v2.4.54 — 2026-10-19

📺 Xác minh trang với Google AdSense (chủ game 19/10: "cứ gắn đi, tí nữa deploy sau"): trang có `<meta name="google-adsense-account" content="ca-pub-9603813200470438">` (game/observability.py head_tags) và `/ads.txt` trả `google.com, pub-9603813200470438, DIRECT, f08c47fec0942fa0` (server.py). Không có script quảng cáo, CSP không đổi, người chơi không thấy gì. Quảng cáo có thưởng làm sau (nhánh feat/rewarded-ads). Không có Có gì mới. Test: tests/test_adsense_verify.py.

📺 Quảng cáo có thưởng, đưa lên nhưng **tắt** (chủ game 19/10: "đưa lên nhưng chưa hiển thị nhé, nào tôi nói thì mới hiển thị"): game/ads.py, chỉ chạy khi có `ADS_REWARDED=1` (sau khi Google duyệt AdSense + H5 Games Ads) hoặc `ADS_FAKE=1` ở máy local; không đặt thì không có nút 📺, không có script quảng cáo, CSP như cũ, bản lưu không đổi. 7 lượt mỗi tài khoản mỗi ngày giờ Việt Nam, không chặn theo máy. Các chỗ: ⏰ Giờ vàng riêng 1 tiếng ×1,5 · 🧩 Ghép ba hồi sinh kèm trợ giúp · 🚔 ra trại ngay · 💸 lấy lại một nửa khoản vừa bị trộm / bị lừa (không tính tiền phạt, phần đã được đền hay bảo hiểm trả) · 📝 phỏng vấn lại / thi chứng chỉ / xét thăng chức lại ngay · 📦 hàng đang về vào kho luôn · 🐾 lần ghép thú cưng tới +10 điểm % (gắn vào ghép thú khi bản thú cưng hạng lên). Vé xem (`ad_ticket` → `ad_claim` sau ít nhất 8 giây) do server giữ. docs/REWARDED_ADS.md: cách bật, "Có gì mới" soạn sẵn.

# v2.4.53 — 2026-10-19

🏛️ Phí giữ tài sản lớn và thuế/thuê chuỗi quầy áp dụng từ 20/10, có thông báo (chủ game 19/10: "mai rồi trừ nhé, với thông báo cho người ta biết luôn"). game/wealth_fee.py START = 20/10 (giờ Việt Nam): trước ngày đó không trừ; khoản 2.4.52 đã trừ hôm 18–19/10 được hoàn hết vào ví ở lệnh kế tiếp ("🏛️ Hoàn phí giữ tài sản lớn (áp dụng từ 20/10)"); quay_business.chain_scope tính chuỗi = 1 trước START_TS.

⚡ Điện quầy theo chuỗi (chủ game 19/10 "điện nước theo chuỗi thì tăng", chọn mức vừa): trên POWER_FREE = 5 quầy, điện mỗi quầy × n/5 (64 ki-ốt: 15 → 192 xu/10 phút, cả chuỗi ≈1,77 triệu/ngày thay vì 138k). Sổ quầy ghi "điện ×…" cạnh thuế/thuê chuỗi. Có gì mới 2.4.53: 3 dòng (phí tài sản, thuế/thuê chuỗi, hoàn phí).

🔧 Phí giữ tài sản tính cả quỹ mọi nơi làm việc đã bắt đầu, kể cả nơi làm thuê (wealth_fee.assets(): wealth_pricing.total bỏ qua chúng; 19/10 một người top đã chuyển ~80 triệu sang đó), và lấy phí từ quỹ nơi làm việc sau cùng (giữ 80 xu dự phòng và tiền hóa đơn chưa trả, journey._transfer 'owner_draw').

# v2.4.52 — 2026-10-18

🏬 Người giàu tốn tiền hơn (chủ game 18/10: "làm sao cho người giàu tốn tiền nhiều hơn, tăng tiền duy trì, tiền chuỗi, phí… tăng càng nhiều thì phí nhiều đi"; chọn mức nhẹ; không thông báo trong Có gì mới). Kiểm tra top 10 trước đó: top 1 (64 ki-ốt hoa) lãi ≈55 triệu/ngày, chủ yếu từ thưởng lãi nhân viên.
- Thuế chuỗi: game/quay_business.py CHAIN_TAX — chủ có trên 5 / 10 / 20 / 30 / 50 quầy trả thêm 2 / 5 / 10 / 15 / 20 điểm thuế thu nhập (7%) trên lãi mỗi quầy; thưởng lãi tính sau thuế nên giảm theo. Số quầy lấy từ save đang tính sổ (chain_scope: settle, quay.public, credit_visit); quầy đọc lẻ tính như 1.
- Phí duy trì chuỗi: trên RENT_FREE = 10 quầy, tiền thuê mỗi quầy × số quầy / 10 (64 quầy: ×6,4).
- Màn quầy (v4/quay.js) ghi "🏬 Chuỗi N quầy: thuế thu nhập X% (thêm Y%), tiền thuê ×Z".
- 🏛️ Phí giữ tài sản lớn: game/wealth_fee.py — mỗi ngày (giờ Việt Nam, thời gian thật) 0,5% phần tài sản (wealth_pricing.total) trên 30 triệu tới 100 triệu và 1% phần trên 100 triệu; ngày vắng tính tối đa 3 ngày; lấy từ ví → tài khoản → tiết kiệm không kỳ hạn → két quầy (đầy nhất trước), không bao giờ thành nợ; ghi sổ "🏛️ Phí giữ tài sản lớn". journey['wfee'] {d, paid, last} (tùy chọn; bản cũ giữ nguyên khóa lạ). Chạy ở engine._apply_action sau fair_cash; MNL_WEALTH_FEE_OFF=1 tắt (mặc định trong tests/__init__.py). tests/test_wealth_fee.py.

# v2.4.51 — 2026-10-18

🍼 Kho Mẹ & bé / Nhà thuốc cùng thang với các tiệm khác (#424, shii: "tại sao lại giới hạn chỉ có 48 kho trong khi ở các cửa hàng khác thì ít nhất là 80"; chủ game 18/10 duyệt). game/convenience.py: LINE = order_progression.LIMITS (80, 120, 200 … 4000), CAPACITY = capacity_progression.units(80, bậc) (80, 120, 180 … 4000); trước đây 6…200 món mỗi dòng đặt, 12…600 món mỗi mã. Bậc "Kho & đơn nhập" đã mua giữ nguyên vị trí trên thang, chỉ tăng số; mặt bằng (stock_cap 12/18/24) và kệ 'shelf' không còn thấp hơn mức 80. SAVE_STOCK/SAVE_LINE theo bảng mới (4000): save có hơn 600 món một mã hoặc kiện hơn 200 món sẽ bị bản 2.4.50 trở về trước từ chối → không rollback dưới 2.4.51 sau khi người chơi nhập kiện lớn.

📦 Kiện lớn đếm theo khay: app.js crateGoods() — kiện trên 20 món ở quầy Mẹ & bé / Nhà thuốc hiện khay 10 ô, "Đếm khay", trang 10 khay (cratePage của v4/inventory-limits.js, cùng hành động v4TallyTray / v4CratePage với các tiệm khác); kiện nhỏ vẫn chạm từng món như cũ.

Tests: test_warehouse_convenience, test_engine, test_operations (mặt bằng không còn giới hạn dưới 80), test_workplace_business cập nhật theo thang mới.

# v2.4.50 — 2026-10-18

👛 Rút hết (#423, thanhtruc09: "mong ad thêm phần nút rút tất cả"). public/js/v4/wealth.js: Tiền của bạn → Quỹ nơi làm việc có nút "👛 Rút hết · N xu" khi có từ 2 quỹ rút được (drawAll: withdraw_max của từng nơi). Một hộp xác nhận, rồi từng quỹ chạy đúng lệnh jr_withdraw như nút Rút về ví (đọc lại withdraw_max sau mỗi lần, dừng ở lần lỗi đầu tiên); mỗi quỹ vẫn giữ 80 xu dự phòng và tiền hóa đơn chưa trả. app.js chuyển wlDrawAll sang wealthAction; money.css .wl-all.

📦 Kho Mẹ & bé / Nhà thuốc (#424, shii: "hay bị lỗi reset làm mất đi các số vừa nhập"). app.js stockDesk: số đã gõ hoặc bấm −/+ lưu ở ui.whQty[nghề][mã] (whBill) và được vẽ lại sau mỗi lần làm mới (30 s nhân viên, mỗi lệnh, đổi nhà cung cấp…) — trước đây morphNode trả ô về mặc định 1 khi ô không đang được chọn; xóa sau khi đặt (whOrder, whMerge). Thêm nút "Tối đa" (data-wh-step="max") đặt số bằng giới hạn của dòng (min(line_max, chỗ trống trên kệ)). desks.css: .wh-qty thêm cột cho nút. Sức chứa/giới hạn mỗi lần đặt của hai tiệm cũ (convenience.CAPACITY/LINE) chưa đổi: chờ chủ game duyệt.

💬 Trò chuyện mở nhanh hơn (chủ game 18/10: "bấm trò chuyện cũng load lâu"). v4/live.js: sau lời chào của dịch vụ live, khi trình duyệt rảnh thì tải sẵn v4/chat.js (≈60 KB cùng honours/khung/lì xì), lần bấm đầu không phải chờ tải. Đo 2.4.48 với 2.4.49 trên điện thoại giả lập (CPU ×4): fps phố/ca làm, long task, style/layout như nhau; máy chủ: /api/command ~0,2 s như hôm trước.

# v2.4.49 — 2026-10-18

🎯 HUD 2.5D gọn hơn (chủ game 18/10: "có vẻ giao diện mới khiến người ta khó chơi game quá", "chữ nút gọn lại, đừng để ngoài quá, gọn gọn tí thì hay hơn, giờ che nhiều cái quá khó chơi"). public/js/isometric-shell.js: bỏ thẻ việc (details.iso-mission), thanh "Đang ở" (.iso-scene) và thẻ Trò chuyện (.iso-chat); thay bằng một nút chính ở giữa phía trên thanh dưới (.iso-go, goButton()): Chọn nghề / Tới quán (ngày đầu) / Xin việc / Mở ca / Làm tiếp / Khép ca / Vào làm, dòng nhỏ là tên tiệm. "Mở ca" (isoOpen) vào tiệm và mở ca ngay bằng lệnh start (start_day); không mở được (đêm, cần kiểm tra trước…) thì mở trang Chuẩn bị như cũ. Thanh dưới: Công việc · Trò chuyện (badge tin chưa đọc) · Thêm; trong tiệm thêm Ra đảo (4 nút). Trong tiệm ẩn cần điều khiển và nút Chỉ đường, hàng nút làm việc nằm ngay trên thanh dưới (không còn 3 hàng chồng nhau). Điện thoại: thẻ tên/ví nhỏ lại, Chỉ đường/Tiện ích thành ô 60 px, cần điều khiển 84 px mờ nhẹ, Góc nhìn chỉ còn biểu tượng, trạng thái người trong phố lên trên. Chữ nút tối thiểu 11–12 px và to theo Cài đặt → Chữ lớn (--iso-t 1.15). public/css/isometric.css: khối "Compact HUD" cuối file.

🏪 Đang dở ca thì mở game vào thẳng tiệm (app.js: world.setMode('work') trước bootShell khi ca đang mở; iso-boot.js đàn chim đọc mode ban đầu).

🕹️ Giao diện cũ dễ tìm: ☰ Thêm → "Giao diện cũ" (rail-foot, isoClassic → interface-mode.js askInterface, cùng hộp hỏi với lần đầu). Người chơi ngày 2–10 đi trong phố 5 phút (tab đang xem, không có hộp thoại) mà chưa mở ca được hỏi một lần mỗi máy "Thấy khó chơi?" (stuckWatch, localStorage mnl.iso.stuckAsked).

🧭 Hướng dẫn trỏ đúng nút 2.5D: tour.js (journey → Công việc, open → Mở ca, task → Làm tiếp, ví/quỹ → .iso-wallet/.iso-fund), tips.js (Công việc thay vì "Thêm → Hành trình"). Tests: tests/isometric-shell.mjs, isometric-camera.mjs, isometric-hud-layout.cjs; scripts/browser_mobile_sweep.py, browser_creative_civic.py dùng .iso-go.

# v2.4.48 — 2026-10-18

🦉 Bảng Online (chủ game 18/10: "thống kê thêm thời gian online nhiều và cho top các bạn online nhiều nữa nhé, top 1 khung này, còn các top khác bạn tự thêm, top 10 tối đa nhé"; "giảm thời gian thực tế xuống 1h nhé, kiểu onl 5 tiếng thì hiển thị 4 tiếng thôi"): game/online_board.py, GET /api/leaderboard?board=online. Thời gian = stat_play (trigger trên receipts: lệnh cách lệnh trước ≤10 phút thì tính cả quãng đó, treo máy không cày được), cộng các ngày thứ Hai–Chủ nhật giờ VN, hiện bớt 1 tiếng (SHOWN_OFF), lên bảng khi hiện ≥1 phút; cùng quyền riêng tư tên như các bảng khác; cache 60 s mỗi tiến trình. Danh hiệu tuần (lb_titles BOARD_TITLES online, MAIN): 🦉 Cú đêm của phố / 🌙 Thức cùng ánh trăng / 🏮 Hội cú đêm, cập nhật mỗi ngày; thứ Hai chốt tuần cũ bằng tổng của chính tuần đó (standings_online). Khung: 73 Cú đêm của phố (bảng chủ game gửi, scripts/cut_honour_frames.py CLIP), 71 (đèn lồng đêm), 69 (hoàng hôn). Client: tab 🦉 Online (leaderboard.js OWN, 7 tab có Khách mời → .lb-kinds.seven), giờ dạng 12h05. Tests: tests/test_online_board.py.

# v2.4.47 — 2026-10-18

🖼️ Khung chat méo / bị cắt (chủ game 18/10: "mèo với thỏ bị lỗi khi nhắn rồi, bị cắt", "nhiều cái scale bị biến dạng méo méo"): border-image 9 phần trước đây cắt ở viền khung chữ nên kéo giãn cả họa tiết nằm dọc cạnh (đầu mèo, thỏ, ống hút, lá, mái nhà). scripts/build_honour_frames.py slices() giờ chọn cho mỗi khung một dải 6 px theo chiều ngang và một dải theo chiều dọc để kéo giãn: chỗ ảnh ít đổi nhất giữa hai dòng/cột liền nhau, phạt dòng/cột có thêm điểm ảnh ngoài viền (hoa, nơ). honour-frames-data.js chat có thêm 4 số cắt [trên, phải, dưới, trái] (chat[6:10]); bubble() dùng chúng (dữ liệu cũ thì cắt như trước). ::before border-width 0 (khung hẹp thì ảnh thu nhỏ đều, không tràn màn hình ở tin của mình), bong bóng có min-width bằng khung chữ của ảnh (--hf-minw) để tin ngắn vẫn đủ cỡ.

🔤 Khung có chữ (27 TOP 10, 37–55 TRÙM): tin của mình không lật ảnh (hf-nf), chữ không bị ngược.

🛠️ Khung chung của Trùm nghề không có khung riêng: 72 "Top tổng hợp nghề" (có hộp giao hàng + mũ shipper, giống 54 Trùm giao hàng) → 56 "Cao thủ đa nghề" (CAREER_ANY).

# v2.4.46 — 2026-10-18

🖼️ Chọn khung (chủ game 18/10 "người ta nhiều khung thì chủ động đổi khung được k"): lệnh jr_frame {id: 'auto' | 'off' | lb_<bảng>_<hạng> | dh_… | t_…} lưu ở khóa mới journey.hf_pick (game/journey.py HF_PICK; bản cũ giữ nguyên khóa lạ nên rollback chỉ quên lựa chọn), public state có hf_pick khi đã chọn. Không kiểm danh hiệu có giữ hay không: live/honours.py đọc hf_pick cùng journey.titles, đưa id đã chọn lên đầu `tt` nếu đang giữ (t_… luôn đứng đầu, client chỉ dùng khi st.t đúng là nó), 'off' → thêm 'hf_off' (client cũ không hiện chip). game/live_chat.honours_commit báo NOTIFY honours cho jr_frame. /api/bootstrap lb_titles có thêm rank. public/js/v4/honour-frames.js: pick() theo lựa chọn, choices()/chooser(): mục "🖼️ Khung danh hiệu" ở Hành trình → Danh hiệu (Tự động, từng khung đang giữ, khung công trình đang đeo, Không dùng khung). 🆓 Khung thường (chủ game 18/10 "cho người ta chọn khung mặc định nữa nhé, nếu k muốn thì bỏ đi"): 7 khung ai cũng đeo được, id k_01, k_02, k_05, k_19, k_22, k_23, k_24 (bộ Gốc + Đời sống, không trùng khung danh hiệu; journey.FREE_FRAMES, honour-frames.js FREE), luôn đứng đầu `tt` khi chọn; mục chọn khung hiện cho mọi người (không có top thì "Không dùng khung" = tự động). Tests: tests/test_honour_frame_pick.py, test_live_honours, scripts/browser_honour_frames.py.

📱 Tắt nhấn giữ / copy / zoom (chủ game 18/10): viewport maximum-scale=1, user-scalable=no; app.css html touch-action pan-x pan-y, body user-select none + touch-callout none (input, textarea, contenteditable vẫn chọn/copy/dán được); bỏ pinch-zoom ở đầu sheet; boot.js chặn gesturestart/gesturechange (iOS bỏ qua user-scalable) và menu nhấn giữ (contextmenu) trên màn hình cảm ứng, trừ ô nhập. Không thêm listener touchmove (cuộn vẫn passive).

# v2.4.45 — 2026-10-18

🖼️ Khung danh hiệu (chủ game 18/10: "thêm logo, danh hiệu vào cho các top nhé, với khung chat"; "chỉ các danh hiệu top này kia có giá trị thôi", "sưu tầm cũng có"): bộ 72 khung (Downloads/Pho_Co_Chuyen_72_Bo_Khung…) cắt bằng scripts/cut_honour_frames.py, đóng gói bằng scripts/build_honour_frames.py → public/icons/frames/NN_av.webp, NN_chat.webp (51 khung, ~1,3 MB, tải khi cần) + public/js/v4/honour-frames-data.js. public/js/v4/honour-frames.js chọn khung từ `tt`/`st` (live/honours.py): bảng chính top 1 / 2–3 / 4–10 (all, titles, certs, wealth, collection), Trùm nghề (khung riêng 25 nghề, còn lại khung chung 72 + icon nghề), danh hiệu đấu giá dh_*, danh hiệu công trình đang đeo; Chợ đen, đám cưới, việc chùa không có khung. Avatar: khung chồng ngoài (::after); chat: border-image 9 phần (::before, lật cho tin của mình), giờ gửi ở giữa để không bị họa tiết che. Bảng xếp hạng: khung quanh số hạng của người giữ danh hiệu và ở Danh hiệu tuần. scripts/browser_honour_frames.py: kiểm trên Chromium (điện thoại sáng/tối, isometric, desktop, 4 bảng).

🌈 Chip danh hiệu top: hn-top (vàng), hn-t1 (bạc), hn-t2 (đồng), hn-t3 (Trùm nghề), hn-t4 (đấu giá), có bản tối.

🏺 game/lb_titles.py: BOARD_TITLES thêm 'collection' (🏺 Bộ sưu tập huyền thoại, 🔨 Nhà sưu tầm đấu giá, 💠 Hội sưu tầm), MAIN thêm COLLECTION. CAREER_NOUN thêm lawyer, art_studio, post_office, laundry; honours.js thêm customs/hotel/banquet/… và f_loss_king, f_loss_club cho khớp.

💰 Góp ý #416: jr_withdraw giới hạn 10**6 nên quỹ > 1.000.080 xu báo "Số lượng không hợp lệ". Giờ tới FUND_MAX, không quá WALLET_MAX (10**9) cho ví, ghi Sổ ví theo từng dòng ≤ ROW_MAX (10**7) để bản cũ (rollback) vẫn validate; places có withdraw_max.

🐱 Góp ý #413: thú cưng ngồi trên xe (public/js/v4/ride.js drawRide `pet`, walk.js, town-walk.js; tests/ride.mjs).

✏️ Góp ý #420: đổi tên ở Hành trình (jr_profile) chưa ghi accounts.display nên chat/bạn bè/bảng xếp hạng giữ tên cũ: Store gọi accounts.sync_character_name cho jr_profile (lưu lại cùng tên cũng đồng bộ), live/chat.py đổi tên cả người đi dạo ở phố/chợ.

# v2.4.44 — 2026-10-18

🧩 Ghép ba màn 101–200 thêm loại đồ (chủ game 18/10 "cần gì 20 loại, thêm 30 40 loại được mà thoải mái", "tăng thoải mái, làm cho khó lên là được"): game/tile_match.py ICONS 28 → 48 (thêm 20 ở CUỐI: 🍩 🎈 📷 🎸 🍓 🍕 🧁 🎒 👒 🌻 🍔 🐰 🐸 🥭 🎧 📚 🐼 🦋 👟 🎮, đều Emoji ≤ 11 cho iOS 15; màn ≤ 20 loại lấy từ đúng 28 cái đầu nên màn 1–100 không đổi, kiểm bằng hash build); scripts/build_tile_levels.py curve_hi kinds 22 → 40 (màn 100: 20), vẫn chồng 8–14 lớp. Bảng màn mới là TABLE 3; bảng của 2.4.43 giữ ở game/tile_match_levels_v2.py để ván chơi trên trang 2.4.43 (gửi v=2) vẫn được tính; jr_tile_end nhận v ∈ TABLES (1, 2, 3), v=1 chỉ tới màn 100.

# v2.4.43 — 2026-10-17

🧩 Ghép ba Phố Mây tới màn 200 (chủ game 17/10 "mở thêm tới màn 200, khó hơn nhé", rồi "xếp nhiều layer là được", "cần gì tăng [loại đồ], xếp nhiều lớp hơn là được"): màn 1–100 giữ nguyên (bảng 2.4.7, kiểm bằng hash build); màn 101–200 giữ 20 loại đồ của màn 100, khó hơn bằng chồng cao hơn: 8–11 lớp ở 101–150, 10–14 lớp ở 151–200 (màn 91–100: 4–7 lớp), 127 → 190 ô. game/tile_match.py: kiểu xếp mới — một số lớp đặt thẳng lên lớp dưới thay vì lệch nửa ô (STRAIGHT: offset 'h3' một lớp thẳng mỗi 3 lớp, 'H' từng cặp), nên bàn 7 × 8 cao hơn trước khi lệch làm co lại; màn 1–100 không có ô nào nằm thẳng trên ô lớp ngay dưới. scripts/build_tile_levels.py --extend: giữ LEVELS[:100], sinh 101–200 (hình vừa: pagoda, lantern, lighthouse, hourglass…; 'big' bị cắt còn ~5 lớp nên bỏ), loại màn bị cắt thấp, solve() kiểm từng màn, ưu tiên màn bot thắng được ít nhất 1/48. Đo: ô bị che kín làm "người chơi nhanh" (greedy_rate) gần như không thắng ở 76/100 màn mới (màn 100: 4%), kể cả khi thêm 3 ô khay — mọi màn vẫn giải được; theo dõi người chơi qua 101–110 sau khi lên, nới nếu kẹt. public/js/v4/tile-match.js: ô nằm thẳng trên ô khác được nâng vài px mỗi lớp (depth) để thấy chồng; mọi chỗ "100" đọc tile.max từ server.

Lưu tiến độ: journey.tile.lv và cur.lv vẫn ≤ 100 (bản cũ kiểm như vậy); số màn qua sau 100 nằm ở khóa mới journey.tile_hi = {lv: 0..100} (chỉ khi tile.lv = 100). Rollback: bản cũ giữ nguyên khóa lạ trong journey, tính người chơi ở màn 100. Phúc lợi: +0,2%/màn đến 100 (20%), rồi +0,1%/màn — tối đa +30% ở màn 200 (PERMILLE_PER_HI, chỉnh được). Trang cũ (2.4.5–2.4.6) vẫn dừng ở màn 100; bảng v1 chỉ có 100 màn nên jr_tile_end {v:1} cho màn > 100 bị từ chối.

🛵 Bỏ nút Còi (chủ game 17/10 "còi với góc nhìn bị che rồi, xóa còi đi"): gỡ nút .iso-horn của public/js/isometric-shell.js (thao tác isoHorn), CSS của nó, public/js/isometric/horn.js, public/audio/sfx/horn.mp3 (và dòng ghi công trong CREDITS.md), honk() của client/isometric/phaser-world.ts (build lại public/js/isometric/phaser-world.js). Các phần khác của 2.4.41 (tăng tốc dần, bóng, khói, đỗ xe) giữ nguyên.

🗄️ Chat Cả phố gọn hơn (chủ game 17/10 "giữ khoảng mấy trăm tin gần nhất, cái cũ thì đưa vào đâu đấy"): live/chat.py TOWN_KEEP 2000 → 500; prune_town chép tin cũ sang bảng mới chat_archive (SCHEMA_VERSION 55, game/pg_schema.py; nguyên cột + archived_at, game không đọc, không gửi người chơi) rồi mới xóa khỏi chat_messages. Chưa có bảng (game server cũ) thì không dọn. Tin đang chờ admin xét báo cáo và tin ghim vẫn giữ. Tin nhắn riêng và nhóm không đổi.

# v2.4.42 — 2026-10-17

✨ Có gì mới (chủ game 17/10 "deploy thì show có gì mới ra chứ, cả ngày chưa thấy"; save admin trên prod đã ghi whatsNewSeen 2.4.41 dù chủ game không thấy bảng): public/js/v4/whatsnew.js không đánh dấu đã đọc khi bảng tự mở nữa, chỉ khi người chơi đóng (Đã hiểu, ✕, Esc, Thử ngay). Bảng bị thứ khác đóng (sự kiện close mà chưa đọc) thì canh lúc rảnh để mở lại (rearm); tải lại trang khi bảng đang mở thì bảng hiện lại.

# v2.4.41 — 2026-10-17

🛵 Xe trên đảo 2.5D (chủ game 17/10 "chỗ xe chạy map 2.5d cho khác tí", chọn: cảm giác lái, xe đẹp hơn, xe đỗ / sân bay): client/isometric/phaser-world.ts — xe tăng tốc dần (RIDE_RAMP 0,7 s, ease-out; tốc độ tối đa không đổi, vẫn ≤ live/town.py SPEED), nghiêng đầu khi bốc tốc, nảy nhẹ theo quãng đường, khói xả sau đuôi xe máy/ô tô (MOTOR, tối đa 8 cụm); bóng mềm dưới xe (vehicle-art.js rideStamp). Nút 📯 Còi (🔔 với xe đạp) bên phải khi đang đi xe trong khu phố: tiếng còi xe thật CC0 (public/audio/sfx/horn.mp3, freesound keweldog #182474, ghi trong CREDITS.md), chuông xe đạp dùng ting.mp3; chữ "📯 Bíp bíp!" trên đầu (0,8 s một lần). Tới cửa một nơi thì xe đỗ bên cạnh, người đi bộ vào; bước tiếp là lên xe lại. Du thuyền dập dềnh, sóng vỗ mạn; sân bay có đèn viền đường băng và cờ gió; máy bay bay qua có bóng lướt trên phố và vệt khói trắng.

🏝️ Đảo riêng đắt hơn (chủ game 17/10 "đảo cho giá đắt lên"): game/island_content.py giá gấp đôi — Đảo Dừa 15M → 30M, San Hô 30M → 60M, Mây Đá 60M → 120M, Hoàng Hôn 100M → 200M (vẫn ≤ PRICE_MAX 10⁹, mua bằng tiền mặt vẫn ghi thành các dòng ≤ 10M). Phí giữ đảo và giá bán lại tính theo giá đã trả, nên đảo đã mua giữ nguyên phí và giá bán lại cũ.

Sửa theo góp ý:
- #411 🔁 Tự đặt hàng (game/auto_order.py): khi tiền còn lại (mức trong ngày = 50% quỹ lúc mở cửa, hoặc quỹ trên mức giữ lại) chỉ đủ một phần, đặt phần vừa đủ (ít nhất 1/4 số "đặt", PART_MIN) thay vì bỏ qua đến khi kệ về 0. `reorder.why` ('cap' / 'fund') — dòng Tự đặt hàng ghi "hết mức hôm nay" hoặc "quỹ thiếu" kèm một dòng giải thích (bản server cũ không gửi why: như trước).
- #412 Góp ý: nút 🗑️ Xóa (bấm hai lần) cho góp ý chưa có lời đáp; POST /api/feedback/delete (player_feedback.delete: một DELETE theo id + chủ + reply IS NULL, ảnh xóa theo ON DELETE CASCADE; giới hạn như sửa).
- Nhà hàng tiệc / Khách sạn: câu "… chỉ: đáp án" bỏ dấu chấm cuối của từng lựa chọn và ngăn bằng "; " khi lựa chọn có dấu phẩy (kit.answer_text), hết cảnh "cột., …..".

# v2.4.40 — 2026-10-17

🧧 Lì xì (chủ game 17/10: "giật lì xì mỗi người không giới hạn, giật thoải mái … mỗi người phát không giới hạn … ưu tiên cái nào chưa giật hoặc còn lên trên"): game/lixi.py bỏ GRAB_DAY / GRAB_DAY_XU / PAIR_DAY (None; đặt số là bật lại), bỏ DAY_MAX / OPEN_MAX khi phát, GAP 60 → 5 giây (chống bấm đúp). Vẫn giữ: một bao mỗi người mỗi lượt phát, không tự giật bao của mình, tài khoản ≥3 ngày, ngày sống ≥10, một bao mỗi mạng mỗi lượt phát, chặn nhau thì không giật. GET /api/lixi liệt kê mọi bao còn mở (tối đa 300) và 30 bao đã xong gần nhất; danh sách 🧧 xếp bao mình còn giật được lên đầu (lixi-cards.js ranked/grabbable) và ghi "N bao đang chờ bạn giật". live/lixi.py giữ 120 bao mở cho trang mới vào.

🍽️🏨 Nhà hàng tiệc và Khách sạn dễ chơi hơn (chủ game 17/10): sai một bước lần đầu thì bước tính số ghi cách tính (HOW), sai lần hai cùng bước thì đồng nghiệp chỉ đáp án (kit.step_help, đếm từ nhật ký phiếu, không thêm khóa mới vào save). Mỗi lần sai trừ 6 điểm chất lượng thay vì 12 (ngày lễ nhà hàng 9 thay vì 18), sàn 60 thay vì 40; phiếu sai trước bản này vẫn hợp lệ với điểm cũ. Nhà hàng: khả năng cháy bếp khi quên tắt điện 40% → 15%. Đề bài và đáp án không đổi (tương thích phiếu cũ).

# v2.4.39 — 2026-10-17

🍽️ Nhà hàng tiệc (chủ game 17/10: "ghi 4200 rồi mà không đúng"): ô nhập số của mọi bước (số bàn, gam, phần, kg, số dụng cụ) gửi thiếu `step` nên server luôn từ chối ("Làm theo bước đang mở"), dù số đúng; banquet.js numberStep gửi {task, step}. tests/banquet-ui.mjs kiểm tra nút Ghi vào phiếu mang đúng bước.

# v2.4.38 — 2026-10-17

📅 Đơn hẹn giờ cho shipper (chủ game 17/10 "shipper thêm cái hẹn giờ"; game/careers/delivery.py, khóa tùy chọn `appt` trên đơn): từ ngày 2 ~45% đơn đủ điều kiện (~1/5 tổng đơn, không có đơn đồ ăn) có khung 30 phút (20 phút từ ngày 10); đúng giờ +4 xu, sớm thì chờ (≤45 phút) hoặc gọi hỏi (dl_appt), trễ −4 / −8 xu (phí không âm, không trừ ví); hợp đồng "Chuyến giao đúng hẹn" tính 2 đơn; nhắc giờ phía client.

Sửa theo góp ý:
- #404 Khách sạn · Trang trí: báo sai cụ thể (món không hợp dịp + dịp của nó, món khách tránh, thiếu N món, vượt ngân sách) và dòng luật trên bước; đề bài, đáp án không đổi (tương thích task cũ).
- #405 Khách sạn / Nhà hàng tiệc: mở 3 lựa chọn bù cho khách khi trả lời đánh giá (6/10/20 xu, trả từ quỹ nghề; career_voice).
- #406 Danh sách nghề: 💵 ~xu/ngày (ca gần nhất) hoặc lương hợp đồng, chip "💰 Nhiều xu trước".
- #407 Giọng đọc số tiền (sounds.js): gỡ hàng đợi speechSynthesis bị kẹt/tạm dừng trên Android, resume khi trang hiện lại, chờ danh sách giọng tới 2 s.
- Nhà hàng tiệc (chủ game 17/10, ảnh): 📋 Tờ dán cửa bếp (dòng sổ bếp) ngay dưới bước vệ sinh đầu ca / dọn bếp cuối ca; đơn vị ô nhập số (sk-amt-in small) không co, không ngắt chữ ("bàn" bị bẻ thành cột dọc).
- #408 Quầy cần người: "Cần làm 10 việc ở nghề 🛒 Tạp hóa (bạn đã làm 3/10)…" + nút vào nghề.

# v2.4.37 — 2026-10-17

Bản cho người chơi nhiều tiền (chủ game 16/10) + nghề mới từ góp ý #401:
- 🏗️ Công trình của phố (game/town_projects.py, schema 52): 6 công trình, cả phố góp tiền tới mục tiêu, bảng tài trợ, xây 48 giờ; lô riêng ở map mới (tp_*) và map cũ. Admin chỉ có API /api/admin/town. Lô Sân vận động dời sang (26–30, 46,5–50) để không đè lô nhà hàng tiệc.
- 🔢 Đấu giá biển số / xe / máy bay (feat/vehicles-plates): xe chạy trên cả hai map với biển số; xe đang đi có biển đấu giá cộng 3–10% thu nhập làm việc (không cộng dồn, tối đa 2.000 xu/ca).
- 🏝️ Đảo riêng (game/island_trips.py, live/island.py, schema 54): mua đảo, chuyến đi bằng du thuyền/phi cơ theo số ghế, mời bạn bè, map riêng ở cả hai giao diện.
- 🧧 Lì xì (game/lixi.py, live/lixi.py, schema 51): phát 10.000–10.000.000 xu trong 1–100 bao; giật ngẫu nhiên; mỗi người giật tối đa 20 bao / 300.000 xu một ngày, 3 bao của cùng một người phát; bao không ai giật sau 24 giờ trả lại người phát.
- 🍽️ Nghề Nhà hàng tiệc Hồng Mây (banquet, góp ý #401): bếp (phụ bếp thử việc 3 ca → đầu bếp, vệ sinh đầu ca, tắt thiết bị cuối ca, đoàn kiểm tra VSATTP ~30% ngày, cháy bếp 2–6 xu) và sảnh sự kiện (số bàn → phòng Sen/Cúc/Lan/Hồng Mây, chủ đề, thực đơn, trang trí, âm thanh ánh sáng, sự cố); ngày lễ thưởng ×1,5. Mở từ chương 3, ngủ khi chưa làm (rollback an toàn cho save chưa đụng tới).

# v2.4.36 — 2026-10-17

📦 Tự đặt hàng (góp ý #400: 18 mặt hàng sắp hết mà chỉ 10 được đặt): có 📦 Gộp thùng tự đặt thì mọi đơn tự đặt đang đi đường tính chung là một xe (inventory._shipments nhận c, auto_order.box_ids), nên auto_order.pick đặt hết mặt hàng thiếu thay vì dừng ở TRANSIT_CAP − SLOTS_FREE = 10 xe; chưa có thùng thì như cũ. public: o.van='auto' cho đơn trong thùng, restock.js đếm xe theo đó.

🛵 Đi xe (góp ý #402: phố 2D chỉ thấy hai bánh xe): ride.js lưu thân xe + người ngồi vào canvas đệm; Android Chrome có thể xoá trắng canvas đệm khi app xuống nền / thiếu bộ nhớ và game dùng lại bản trắng mãi. Giờ: canvas đệm mất (isContextLost / width 0 / contextlost) thì vẽ lại, xoá cache khi trang hiện lại (visibilitychange), canvas cũ được giải phóng (width 0), không tạo được canvas thì vẽ thẳng lên phố (paintBody).

# v2.4.35 — 2026-10-16

🎁 Kho báu trong phố (chủ game 16/10 tối: "10p thì sẽ từ 10 - 15 rương random"): mỗi đợt 10 phút ngẫu nhiên 10–15 rương (town_treasure.WAVE_MIN/WAVE_CHESTS, 92 điểm đặt); mã rương nhận số thứ tự 2 chữ số (CHEST). Lùi về 2.4.34 thì rương số 10–14 của đợt đang có không nhặt được tới khi hết hạn (≤ 30 phút).

🐕 Đua chó (chủ game 16/10 tối: "tỷ lệ ăn cao quá, cho ăn tỷ lệ thấp lại, lãi nhiều quá … giảm nhẹ xíu thôi, giảm 5% so với hiện tại"): giá trả thưởng giảm 5% so với 2.4.34, làm tròn tới 0,1: fair_dog.CLASSES (29, 39, 52, 78, 105, 190) = bảng 08/10, mỗi chó trả 92,8–95% tiền cược; giá khi cược dồn dập (≥ 11 ván/phút) hoặc lãi chợ đen trong ngày ≥ 100.000 (OLD) cũng giảm 5%: (28, 37, 49, 74, 100, 180) = 88,2–90%. Bảng vẫn hiện đúng giá ván kế tiếp của người chơi.

# v2.4.34 — 2026-10-16

🛎️ Nghề mới Khách sạn Sông Mây (chủ game 16/10 "thêm nghề khách sạn đi"): nghề làm công (operations.SALARIED, lương hợp đồng khi khép ca + thưởng mỗi việc theo chất lượng), xoay 6 vị trí: lễ tân, dọn phòng, giặt là, bữa sáng, sửa chữa, trang trí sảnh; mỗi việc vài bước kiểm ở server, sai bước làm lại và trừ chất lượng. Mùa Valentine / Tết / Noel (ngày Việt Nam): thêm một khách, thưởng ×1,5, sảnh trang trí theo mùa. 12 chuyện quầy lễ tân, truyện 5 phần, chứng chỉ, nấc thăng tiến, nhà isometric, lô ở khu công viên, tiếng Anh. Mở từ chương 3 qua journey.LATE_UNLOCKS (không ghi vào unlocked của mọi save), chưa làm thì không lưu (engine.DORMANT như hải quan): rollback xuống 2.4.33 vẫn đọc được save chưa đụng tới khách sạn.

🎲 Cân lại chợ đen (chủ game 16/10: "tỷ lệ 55 - 60% … đừng cho lỗ nhưng đừng cho lãi nhiều", tính cả cheat / thua nhỏ rồi cược lớn / spam; "đừng giới hạn 600 ván, … spam 1 game nhanh quá thì thua cao hơn"):
- Chiếu trong, lô tô, vé cào rút 57%; theo lãi/lỗ chợ đen hôm nay: lãi ≥ 100.000 → 45%, lãi > 30.000 → 52%, đang lỗ mà cược ≤ min(số lỗ, 5.000) → 60%. Cược từ 50.000: tối đa 40% + công an như cũ. Bốn ván thắng liền vẫn nguội 45%.
- Nhịp chơi (journey.fair_pace, không giới hạn số ván): một quầy quá 10 ván trong 60 giây −5 điểm, từ 16 ván −12 điểm, sàn 40%; bầu cua bão 10 và đua chó giá cũ khi chơi dồn hoặc lãi ≥ 100.000. Gợi ý "🥶 Chơi dồn dập quá" thay cho "Vận đang nguội vì chơi liền một trò".
- Bỏ ván đầu ngày 65% và các khung 70% bí mật (fair_boost.rate luôn None), giữ khoảng cách 3 giây của xóc đĩa; giảm dần theo chuỗi ván (RUN_STEP) không còn áp cho chiếu trong / lô tô / vé cào.
- Trả thưởng: chiếu trong thắng ăn 0,75 lần tiền cược (xâu 25%), lô tô kinh 1,8×, vé cào trúng trung bình 1,775× (không còn giải hoàn vé), bầu cua bão 20:1, đua chó +~5%.
- Mô phỏng (scripts/sim_bm_strategies.py, docs/FAIR_HOUSE_EDGE.md): chơi thường 57% thắng, RTP ~100%; gấp thếp 99%, thua nhỏ rồi cược 45k 98%, bot 3 giây 84%, dò 3 ván rồi 49k 94%.

# v2.4.33 — 2026-10-16

🧰 Kho báu trong phố (chủ game 16/10: "giới hạn 1 ngày 1 người 300 rương (0h thì reset), k cần thông báo"): town_treasure.DAY_MAX = 300, đếm từ 0h giờ Việt Nam (UTC+7) thay vì 24 giờ trượt; quá số thì báo "Hôm nay bạn đã nhặt đủ 300 rương rồi. Sau 0 giờ đêm nay nhặt tiếp nhé!" (treasure_day). Không có dòng Có gì mới cho phần này (chủ game dặn).

Sửa theo góp ý người chơi:
- ✈️ #394 nữ phi công gặp toàn tình huống cho nam: chuyện oái oăm (air_odd) nhận bản lời riêng theo giới tính nhân vật (x['female']), giới tính ghi vào chuyện lúc mở (ev.g) để cả lượt đẩy, kết quả và nhật ký dùng đúng bản. 10 chuyện của phi công có bản nữ (rượu ở Phú Quốc, TikToker, du thuyền đối tác, gõ cửa khách sạn, mảnh giấy, cầu hôn qua loa, đổi ca, phóng viên, mai mối, em họ).
- 🗂️ #395/#396 Hành chính nhân sự không khép ca được khi văn phòng đóng cửa còn hồ sơ dở: bàn làm việc chung (office_work.js: hr_admin, it_helpdesk) dùng thanh "Khép ca · xem tổng kết" như các bàn kế toán; màn ca làm thêm nút Khép ca cạnh "Làm tiếp" khi văn phòng đã đóng.
- 📮 #393 Bưu điện trả lời đánh giá "xin lỗi + sửa sai" thiếu bù tiền: thêm bù đắp "Hoàn cước 20 xu".
- 📦 #391 tự đặt hàng về 9–18 thùng phải mở từng thùng (chủ game: "thêm cái đó, nhưng mất 10k xu để mua"): mở khóa 📦 Gộp thùng tự đặt (auto_order.BOX_KEY, 10.000 xu, quỹ trước rồi ví, sau khi có 🔁 Tự đặt hàng). Hàng tự đặt tới cửa hiện là một thùng (inventory.public box=auto), nhận một lần inv_receive {box, counts}: mỗi món vẫn đếm, cả thùng một lượt 20 phút; thiếu thì khiếu nại từng món như cũ. Mua ở Kho (dòng Tự đặt hàng) hoặc Thiết bị nghề.
- 🧭 #397 giao diện cũ bấm Đổi nghề nhảy sang Đầu tư: nút Đổi nghề mở lại trang chính của Hành trình (jrView='home').

# v2.4.32 — 2026-10-16

🎨 Thể lệ thi bộ sticker (chủ game 16/10: "mấy bên đạt giải giữ ảnh gốc, đạt giải thì đưa vào làm sticker chính thức của game, note chỗ event thôi"): trang /sticker thêm hai dòng thể lệ (bộ đạt giải thành sticker chính thức của game; người đạt giải giữ file ảnh gốc để ban tổ chức liên hệ lấy). Chỉ ghi ở trang sự kiện: không có dòng Có gì mới (chủ game dặn).

# v2.4.31 — 2026-10-16

🏆 Tăng giải thi bộ sticker (chủ game 16/10: "tăng giải thưởng lên giải nhất 5M, tăng các giải còn lại luôn"): Top 1 5.000.000 xu (từ 3.000.000), top 2–3 2.500.000 xu (từ 1.500.000), top 4–10 1.000.000 xu (từ 500.000). Quà tham gia giữ 200.000 xu. sticker_event.PRIZES, trang /sticker, thẻ trong game. Có gì mới: 1 dòng.

# v2.4.30 — 2026-10-16

🎨 Thi sticker đổi sang BỘ sticker (chủ game 16/10 chiều, kèm ảnh mẫu 16 chú mèo: "phải làm như này"; "hoặc là từng cái, hoặc là 1 nhóm"; ít nhất 12; AI "cho, nhưng phải ghi rõ"; 1 bộ mỗi tài khoản, được thay; hashtag #PhoCoChuyen; link nhóm Facebook).
- Trang /sticker làm lại: người chơi tự làm bằng app bất kỳ rồi tải lên; bỏ trình vẽ trên trang (public/js/sticker/editor.js). Hai cách nộp: một ảnh ghép cả bộ (tự ghi số sticker, 12–100, tối đa 3 MB, cạnh 300–4096) hoặc từng sticker (12–24 ảnh, máy người chơi thu mỗi ảnh vào khung 512×512, tối đa 250 KB). Bắt buộc chọn "Tự vẽ" / "Có dùng AI"; chú thích đăng nhóm tự ghi "(có dùng AI)". Nộp lại là thay bộ cũ (bộ đã xếp hạng thì khóa). Nút tải ảnh để đăng: ảnh cả bộ có nhãn @tên, hoặc ảnh ghép từng sticker.
- game/sticker_event.py: POST /api/sticker/pack, GET /api/sticker/pack/<id>/<idx>; /api/sticker/submit (sticker lẻ) trả 410. Xếp hạng, trao giải, kết quả theo bộ. Quà tham gia 200.000 xu một lần mỗi tài khoản: 17 tài khoản đã nhận theo thể lệ cũ giữ quà, nộp bộ không nhận thêm; trang báo họ nộp bộ để được xét giải.
- Admin "🎨 Thi sticker": danh sách bộ (ảnh, số sticker, AI, lần nộp), lọc "Có dùng AI", cảnh báo ảnh trùng tài khoản khác; sticker lẻ thể lệ cũ chỉ để xem.
- Schema 50: sticker_packs, sticker_pack_images (bảng mới).
- Link nhóm: https://www.facebook.com/groups/1985137015484964. Hashtag #PhoCoChuyen.
- Có gì mới: 3 dòng.

# v2.4.29 — 2026-10-16

🎨 Cuộc thi làm sticker (chủ game 16/10: "tạo sticker chủ đề bất kì, đăng nhóm facebook, ai được vote nhiều hơn thì thắng, tham gia tặng 200k, top 1 3m, top 2–3 1.5m, top 10 500k, có cả username, top 10 có sticker dùng trong chat").
- Trang riêng /sticker (public/sticker.html, public/js/sticker/, game/sticker_event.py): vẽ/ghép sticker 512×512 với tên tài khoản đóng dấu sẵn, tải ảnh về, gửi tối đa 3 bài; hướng dẫn đăng nhóm Facebook với hashtag #StickerMotNgayLamNghe. Hạn gửi 27/10 23:59.
- Quà tham gia 200.000 xu một lần mỗi tài khoản (đã đăng ký, ngày sống ≥ 3) qua system_gifts; giải top 1–10 do admin trao sau khi chốt bình chọn trên Facebook (trang admin "🎨 Thi sticker": duyệt, từ chối, xếp hạng, trao/thu hồi giải).
- Schema 49: sticker_entries, sticker_rewards (bảng mới). 47 bỏ trống.
- Link nhóm Facebook (sticker_event.FB_GROUP_URL) chưa có: trang ghi "sẽ có ở đây sớm".
- Có gì mới: 3 dòng.

# v2.4.28 — 2026-10-16

🛠️ Hotfix Hải quan: ứng tuyển rồi "làm lại nghề" (reset_career, started = False) để customs trong journey.unlocked mà không thuộc chương nào (CH_UNLOCKS) → mọi thao tác bị từ chối "Nơi làm việc mở sớm hơn chương hiện tại" (1 người chơi, 16/10). journey.validate cho phép nơi mà gov_rules.opens đã mở. Test: tests/test_career_customs.py test_applied_then_reset_still_validates.

# v2.4.27 — 2026-10-16

🛃 Nội dung cập nhật 14/10 của chủ game ("triển khai thêm cái này rồi thông báo nữa nhé").
- 👮 Điều lệnh Công an (game/gov_rules.py): bổ nhiệm Giám đốc CATP khi hồ sơ không quá 6 vi phạm; chuộc người thân/bạn bè/vợ chồng/hôn phu đang chấp hành án → giáng 2 bậc hàm + kỷ luật 15 ngày; cá độ ở chợ đen → giáng 1 bậc hàm + kỷ luật 10 ngày. Ghi trong Điều lệnh và hồ sơ công tác.
- 🛃 Nghề mới Hải quan (game/careers/customs.py, customs_content.py): điều kiện 3 chương + đã làm Công an tới Hạ sĩ + không quá 3 vi phạm; thi tuyển 8 câu (qua 6/8); thang hàm hq; bốn mảng việc (kiểm tra/giám sát, chống buôn lậu, thuế xuất nhập khẩu, phòng chống tội phạm); NPC phản ánh cuối ca, gỡ hoặc chuyển CATP truy tố (game/npc_complaints.py); vi phạm trong nghề (bao che → giáng 1 bậc + 10 ngày, làm sai lệch hồ sơ → 15 ngày, tham ô/nhận hối lộ → khai trừ).
- 🛃 Kiểm tra kho tiệm người chơi (game/hq_ops.py): chỉ dựa trên nợ thuế quá hạn thật trong save; nhắc nộp / cưỡng chế trích tiền (≥2 ngày trễ) / kê biên hàng tồn (≥5 ngày, quỹ không đủ), phải được cấp trên (người chơi hoặc Cục tự duyệt sau 6 giờ) duyệt; chủ tiệm khiếu nại trong 3 ngày, sai thì hoàn trả; xử lý sai → giáng 1 bậc + 15 ngày, 3 lần trong 14 ngày → khai trừ + cấm ngành nhà nước. Không kiểm tra bạn bè/vợ chồng/chính mình; giới hạn lượt mỗi ngày, mỗi tiệm.
- Schema 48: hq_roster, hq_cases (bảng mới). 47 để dành cho cuộc thi sticker.
- ⚠️ Save đã dùng Hải quan không mở được trên bản cũ hơn: không rollback dưới 2.4.27 khi đã có người vào nghề.
- Có gì mới: 2 dòng.

# v2.4.26 — 2026-10-16

💐 Sự kiện Thiệp 20/10 (chủ game 16/10: "1 event riêng… ghi chú gì đó gửi tặng người khác, có share link… không cần chơi game vẫn đọc được… vài theme… tham gia tặng 100k"; "làm nhiều theme cute vào").
- Trang riêng /2010 (public/2010.html, public/js/event2010.js, game/event2010.py): Nam gửi nữ / Nữ gửi nam / Gửi ai cũng được, 13 mẫu tự vẽ (SVG/CSS), lời nhắn ≤ 400 ký tự, hình dán, xem trước; link /2010/c/<id> ai cũng đọc được (phong bì mở, hoa rơi, thả tim, "Viết thiệp tặng lại"), ảnh xem trước Zalo/Facebook theo mẫu (không lộ lời nhắn).
- Quà 100.000 xu một lần mỗi tài khoản (đã đăng ký, nhân vật từ ngày sống 3; tối đa 5 quà mỗi địa chỉ mạng), qua system_gifts. Viết đến 21/10 23:59, đọc đến 20/12. MNL_2010_OFF=1 tắt viết/quà.
- Kiểm duyệt: người gửi xóa, người đọc báo cáo (3 báo cáo ẩn chờ admin), admin "💐 Thiệp 20/10"; che số điện thoại, đường link, từ thô.
- Công bố trong game: Tiện ích → Thiệp 20/10, dòng trên Hành trình, popup một lần, dòng bảng tin mỗi ngày; Có gì mới có nút mở trang.
- Schema 46: ev2010_cards, ev2010_reports, ev2010_rewards (bảng mới).

# v2.4.25 — 2026-10-16

🫖 Đầu game nhẹ hơn, đợt 2 (chủ game 16/10 "ok sửa đi"). Chỉ nhân vật mới ở chế độ câu chuyện, ngày sống 1–3 (`journey.EASY_DAYS`); không thêm khóa lưu.
- Trà sữa: sáng ngày sống 2–3 quầy có sẵn 8 phần mỗi loại trà/trân châu/foam đang bán, miễn phí như hàng mở đầu (`boba._ready_pots`); từ ngày 4 tự ủ.
- Cảnh kết chương 1 / mở chương 2 rút còn 2 câu mỗi cảnh (cho mọi người: chỉ hiện ở lần khép ca đầu).
- Bảng "Chuẩn bị ngày 2/3": một câu của Cô Ba, mục nồi/đặt hàng gập lại; sổ khách quen gập trong ngày 1–3 (trừ khách "như mọi khi"); nút Trò chuyện ẩn ngày 1; truyện nghề tự bật từ ngày 4; tổng kết ngày 1–3 gập sổ sách/đánh giá/thăng tiến.
- Số chữ: kết chương 1 175→59, mở chương 2 113→70, Chuẩn bị ngày 2 280→88, quầy ngày 2 127→72.
- Có gì mới: 1 dòng.

# v2.4.24 — 2026-10-16

🌱 Người mới dễ vào hơn (chủ game 16/10: "giai đoạn đầu quá khó chơi, nhiều chữ thừa, giao diện không tối ưu"). Chỉ áp dụng cho nhân vật mới ở chế độ câu chuyện; số kinh tế và schema không đổi. Ghi chú nghiên cứu: onboarding-notes-1016.md (ngoài repo).
- Máy chủ: cả ngày sống 1 khách không mất kiên nhẫn (`engine.LEARNING_LIFE_DAYS`); ngày sống 2–3 luôn "thong thả" (`journey.EASY_DAYS=3`, chốt lúc khép ngày); người mới không bị hỏi "quay về giao diện cũ?" (`journey.interface.interfacePromptSeen`, khóa sẵn có).
- Đảo: đặt tên xong nhân vật tự đi tới quán đầu tiên và mở ngày 1; HUD "Đầu hẻm đang cần người phụ quán · Tới quán"; hết khách thì "Hết khách rồi · Khép ca".
- Ngày 1 ẩn băng tin, nút camera, chấm tiện ích, nút "?" thứ hai; trang Hành trình ẩn hội chợ/đời sống/bảng tin/du học/truyện/chứng chỉ/nhà tới ngày 2.
- Tổng kết lần khép ca đầu: sổ sách, đánh giá, thăng tiến, ghi chú nghề gom vào "Chi tiết cả ngày" (216 → ~103 chữ). Thẻ x3 chờ tới ngày sống 4. Chỉ đường: lời dẫn ngắn hơn.
- Có gì mới: 1 dòng.

# v2.4.23 — 2026-10-16

⚡ Bớt lag trên bản lưu lớn (chủ game 15/10: "có mấy cái lỗi gì đó bấm thấy lag lắm, coi tối ưu đi"). Đo trên bản lưu thật 10,6 MB (54 nghề): mỗi lệnh nhanh hơn ~9–12%, mỗi lần tải trạng thái có đồng bộ tiệm (nhân viên làm, 30 giây/lần) ~1,1 s → ~0,8 s. Kết quả game và định dạng bản lưu không đổi.
- Giờ vàng: lịch của một ngày rút một lần mỗi tiến trình (game/golden_hour.py), không rút lại cho từng đơn nhân viên.
- Chuyên môn nghề: chỉ chép khối `scale` thay vì chép sâu cả nghề mỗi lần xem (~25 ms/lần trên bản lưu lớn).
- GET /api/state: lượt đồng bộ tiệm ngay sau đó dùng lại bản lưu vừa đọc nếu phiên bản chưa đổi (Store.command `own`, truy vấn `_SNAPSHOT_KEPT` không tải lại văn bản bản lưu).
- game/validate_memo.py: khi lưu nghề vừa đổi, việc/bài đăng/sổ tay/ký ức/chat có JSON giống hệt bản đã kiểm qua trong worker thì không kiểm lại; lỗi thì kiểm đầy đủ lại để báo đúng thông báo cũ. `VALIDATE_MEMO=0` tắt.
- Shop quần áo: nhân viên đếm hàng đang giữ một lần cho mỗi đơn thay vì mỗi món × cỡ.
- SCOPED_CAREER_VALIDATION vẫn tắt (mặc định).

# v2.4.22 — 2026-10-15

🎲 Chợ đen thắng dễ hơn (chủ game 15/10: "tăng tỷ lệ thắng chợ đen lần đầu lên 65% đi, với lâu lâu mỗi ngày cho khoảng 3p (chia ra 1 ngày khoảng 3 - 4 lần) ngẫu nhiên là tỷ lệ thắng tăng cao nhé. Với chỗ xóc đĩa thì cho delay 3s mỗi lần mở nhé để tránh spam"; thông báo chỉ ghi "Tăng tỷ lệ thắng chợ đen").
- game/fair_boost.py (chỉ máy chủ, không gửi tỷ lệ hay khung giờ ra client): ván đầu tiên mỗi ngày (giờ VN) ở các sạp có rút tỷ lệ (chiếu trong/xóc đĩa, lô tô, vé cào) thắng 65%; mỗi ngày 3–4 khung 3 phút (08:00–24:00, mỗi khung trong một phần bằng nhau của ngày, không chồng nhau, giống nhau cho mọi người, rút từ ngày + muối máy chủ của lịch tin nhà `property_market._salt`) thắng 70% khi lời chợ đen hôm nay chưa quá 300.000 xu. Cả hai chỉ cho ván dưới 50.000 xu (ván 50k+ vẫn tối đa 40%); công an, dẹp chiếu, phạt giữ nguyên. Vé cào thắng trong lúc được tăng là vé có lời (không tính vé hoàn tiền), như Ngày vàng. Bầu cua (xúc xắc thật) và đua chó (tỷ lệ cố định) không đổi. MNL_BM_BOOST_OFF=1 tắt (tests).
- Xóc đĩa: mỗi ván cách ván trước của người đó ít nhất 3 giây (máy chủ từ chối, mã `fair_slow`); nút "Xóc!" khóa 3 giây có đếm ngược.
- Khóa lưu mới (tùy chọn): `journey.fair_bm_day` {d: ngày đã dùng ván đầu, xd: ms ván xóc đĩa trước}. Bản lưu cũ không có vẫn hợp lệ.
- Có gì mới: 1 dòng.

Rương kho báu: mỗi đợt 10 phút rải 10 rương (trước 3–5).

# v2.4.21 — 2026-10-15

Thông báo "Giờ vàng - lợi nhuận cao" (chủ game 15/10: "triển khai đi xong thông báo 'giờ vàng - lợi nhuận cao'"): một mục Có gì mới, để cả người đã xem 2.4.20 cũng thấy. Không đổi gì khác.

# v2.4.20 — 2026-10-15

⏰ Giờ vàng + quầy lãi hơn (chủ game 15/10: "chấp nhận, và tăng thêm lãi cho người dùng đi, … 10p hoặc 1h ngẫu nhiên mỗi ngày là khung giờ vàng, hoặc theo ngày").
- game/golden_hour.py: mỗi ngày (giờ VN) bốc từ ngày: ~1/7 là Ngày vàng (×1,5 cả ngày), còn lại một Giờ vàng 10/30/60 phút bắt đầu 07:00–23:00 (×2). Không lưu gì. Nhân lãi lúc đơn/lượt bán xảy ra: đơn nhân viên (staff_market.x), lượt bán quầy (phần chủ nhận, scale_take). Lỗ không nhân. Bảng tin (/api/news `golden`) chạy 1 lần mỗi khung; chip/dòng ở thẻ nghề, Sổ tiệm và quầy. MNL_GOLDEN_OFF=1 tắt (tests).
- Quầy tạp hóa: giá vốn 68% → 55%.
- Quầy vắng khách: quá 10 phút kể từ lượt bán cuối thì chi phí theo thời gian (thuê, điện, môi trường, bảo kê, lương) ngừng tính tới lượt bán sau (`_busy`, đo từ thời điểm bán nên poll hay offline như nhau). Quầy chưa bán lần nào trả như cũ. Ca người chơi thuê không đổi.
- Không thêm khóa lưu. Có gì mới: 2 dòng.

# v2.4.19 — 2026-10-15

📒 Quầy: dòng "Lãi" không còn trừ hàng còn trên kệ (chủ game 15/10 nhờ xem nhóm chat: "kinh doanh mà k có lãi"). Nhập hàng ghi chi phí hàng ngay lúc nhập, nên quầy vừa nhập lô lớn hiện lỗ nặng (7 quầy bánh & cà phê trung bình −57.000 xu, tiền hàng 27× doanh thu) dù hàng vẫn còn. `public()` cộng lại giá vốn hàng còn (`stock_value`, unit_cost × số phần): hàng tính khi bán, hỏng hoặc mất. Tiền, thưởng và sổ không đổi; nhãn "Lãi đã ghi sổ" → "Lãi", thêm "vốn ≈ … xu" dưới Nguyên liệu còn. Tiệm có nhân viên vốn đã tính hàng lúc bán (1.010 tiệm, 2 tiệm ≤ 0). Không có Có gì mới.

# v2.4.18 — 2026-10-15

wishmerge (chủ game 15/10: "đưa vào 1 cái đi, sử dụng chung mà"; nhãn cây "sửa nhé"). Không có Có gì mới.

## wishmerge

📜 Một bảng chung duy nhất: Vườn ước nguyện (chủ game 15/10 về “Bảng chung” cũ: “đưa vào 1 cái đi, sử dụng chung mà”); 🏷️ nhãn tên cây trong sân chùa 2.5D luôn hiện đủ trên điện thoại hẹp (“ở mép trái màn hình hẹp, vài nhãn tên cây bị khuất một phần”). Giới hạn giữ nguyên (5 điều ước/ngày, 150 ký tự, 3 báo cáo thì ẩn, khách viết được). Chưa đổi số phiên bản, chưa thêm Có gì mới.

- Lời chúc cũ trong vườn: thẻ lời chúc mà chủ thẻ đã chọn Công khai (bảng `chua_public_cards`, đọc tại chỗ, không chép, không backfill) treo trên cây hợp chủ đề cho MỌI người thấy: khỏe → Sức khỏe, bình an / thanh thản / “bà con khu phố luôn thương nhau” → Bình an, “cả nhà luôn thương nhau” → Gia đạo, siêng năng → Sự nghiệp, kiên nhẫn → Ước mơ, yên nghỉ → Tưởng nhớ, may mắn → Tài lộc (`game/chua_wish.py` card_tree; mọi cặp người/điều mong đều có cây). Trên cây: vài mảnh giấy kem viền đỏ giữa các dải lụa (luôn có tới 4 mảnh dù cây nhiều điều ước) và mục “📜 Lời chúc cũ trên cây” dưới danh sách điều ước, có “Xem thêm” (GET `/api/chua/wishes?tree=&old=1&before=`, con trỏ theo position). Đọc như điều ước (‹ › đi qua cả hai), không hiện người viết (bảng cũ cũng không), ghi “📜 Lời chúc cũ · Ngày N”. 🙏 Cùng cầu (mỗi người một lần), ⚑ Báo cáo (bảng `reports` kind `card`, 3 người thì tự ẩn, người báo cáo không thấy nữa), thẻ của mình có “Thôi chia sẻ” (POST `/api/chua/wishes {op, card}`). Vườn và bảng tên cây đếm “N điều ước · M lời chúc cũ”.
- Quyền riêng tư giữ đúng: chỉ thẻ có dòng trong `chua_public_cards` mới hiện; chủ thôi chia sẻ (ở vườn hoặc đường cũ `/api/chua/cards/visibility`), đặt lại, nhập bản lưu hay xóa bản lưu thì thẻ biến khỏi cây ngay lần đọc sau (trang không cache; chỉ số đếm theo cây cache 10 s). “Của tôi” có mục “📜 Lời chúc cũ của bạn”: từng thẻ (cả phần archive) ghi “🌳 Đang treo ở cây …” / “🔒 Chỉ mình tôi” với nút “Treo vào vườn” / “Thôi chia sẻ” (đúng các route cũ). Bỏ lối vào riêng “📜 Bảng lời chúc cũ” ở Quanh đây (vẫn giữ cho máy chủ cũ không có vườn). Bảng chung cũ (`/api/chua/cards?scope=public`, client cũ còn đọc) cũng không còn hiện thẻ bị ẩn vì báo cáo hoặc admin gỡ.
- Admin “Ước nguyện”: thêm mục “📜 Lời chúc cũ người chơi chia sẻ” (bị báo cáo lên trước, lý do, @tài khoản chủ, 🙏), Gỡ / Treo lại (`/api/admin/wishes {act, card}`); quyết định gắn theo chủ + thẻ nên chủ chia sẻ lại vẫn bị gỡ. Không xóa, không sửa thẻ nào; “Xóa dữ liệu” (XOA) xóa 🙏/đánh dấu của người đó.
- DB: SCHEMA_VERSION 45 — chỉ thêm bảng `chua_card_marks` (sid, card_id → prayers, reports, status, reviewed_at, by_admin) và `chua_card_prayers` (+ chỉ mục), không FK, không backfill, không đổi bảng cũ. Bản lưu không đổi gì (không khóa mới): 2.4.16 và 2.4.15 đọc được (test chạy `chua.validate` của e535140b và f17d9d70); rollback thì hai bảng mới bị bỏ qua và bảng chung cũ hiện lại như trước.
- Nhãn tên cây (public/js/scenes/chua-iso.js layoutBoards, public/js/v4/chua-visit.js): mỗi bảng tên của cây đang trong khung nằm trọn trong khung hình, không đè bảng khác, biển “VƯỜN ƯỚC NGUYỆN”, biển Nhà trai, huy hiệu việc/💬 hay dòng gợi ý (tìm chỗ gần nhất, ưu tiên dời ngang để vẫn nằm dưới cây); chạm bảng tên ở chỗ nó được vẽ. Lần nhìn đầu trên màn hẹp canh giữa cả vườn (đủ 9 cây và 9 nhãn ở 360×740, 375×667, 390×844, 412×915; 844×390 thấy trọn chiều cao vườn). Cây ra ngoài khung thì không vẽ nhãn (không chất nhãn ở mép). Biển “🌳 VƯỜN ƯỚC NGUYỆN” trượt dọc cột cho khỏi bị cắt ở mép (cột ra ngoài khung thì không vẽ biển).
- Kiểm: tests/test_chua_wish.py (+ OldCardTrees, OldCardsInTheGarden: thẻ chia sẻ hiện cho người khác, riêng tư/thôi chia sẻ/đặt lại/xóa thì không, 🙏 một lần, 3 báo cáo ẩn, admin gỡ/treo lại kể cả khi chia sẻ lại, phân trang, XOA, schema 45 idempotent, 2.4.16/2.4.15 validate), scripts/check_chua.mjs (72 bố cục nhãn ở các cỡ màn), scripts/browser_wish_trees.py (thêm 375×667, 412×915; `WISH_SIZES=`; kiểm nhãn cây, lời chúc cũ trên Cây Sức khỏe, 🙏, “Thôi chia sẻ”, Quanh đây không còn bảng riêng, admin gỡ thẻ; kiểm đè nút chỉ tính phần thấy được trong khung cuộn). Tiếng Anh: i18n/overrides.json + `scripts/i18n_extract.py build`.

# v2.4.17 — 2026-10-15

📈 Tăng lợi nhuận kinh doanh (chủ game 15/10: "mở tiệm cho lãi cao hơn, cho mọi người tăng 60% lãi"; thông báo "Tăng lợi nhuận kinh doanh").
- Đơn riêng của nhân viên ở nơi làm: lãi mỗi đơn ×1,6 (staff_market.SHOP_BOOST = 160, sau thị trường/🔥 nghề hot); thưởng 40% tính trên lãi đó nên phần chủ nhận cũng ×1,6. Giữ PROFIT_PERCENT = 40 vì bản lưu kiểm `total×100+carry == positive×40` (bản cũ phải đọc được).
- Quầy: thưởng lãi 40% → 124%, nhân viên bán 110% → 236% (phần chủ nhận (100+p)×1,6). profit_boost chỉ lưu carry/total/costs nên bản cũ đọc được. Hướng dẫn cập nhật số.
- Chặn khai thác (đã có từ trước, nặng hơn khi thưởng 124%): đơn của khách là người chơi ở quầy chỉ tính thưởng trên tối đa 2× giá gốc món (VISIT_BONUS_RATIO); giá chủ đặt tới 1.000.000 xu vẫn vào két đủ nhưng hệ thống không trả thưởng trên phần đó.
- Lỗ không bao giờ được nhân. Có gì mới: 1 dòng.
# v2.4.16 — 2026-10-15

Gồm nodog, mobileui và wishtree (chủ game 15/10: "xong hết thì deploy rồi bảo 'tối ưu UI'"). Có gì mới: 3 dòng (tối ưu UI, chùa 2.5D + Vườn ước nguyện, nhẹ và mượt hơn).

## nodog

🐕 Bỏ trò Kéo co chó sủa (chủ game 15/10: "xóa trò 'kéo co chó sủa' đi cho nhẹ").
- Người chơi không còn thấy trò ở đâu: bỏ mục Khu phố/menu, mốc 🐕 trên phố cổ điển, tòa "Sân chơi thú cưng" trên bản đồ 2.5D (game/town_layout.json, dựng lại public/js/isometric/phaser-world.js) và phòng `bark` trong venue-place. Xóa public/js/v4/dog-bark.js, dog-bark-board.js, public/css/dog-bark.css, public/audio/bark/ (7 tiếng sủa + CREDITS; bỏ dòng ghi công trong THIRD_PARTY_NOTICES.md), MANIFEST bỏ các file đã xóa. Có gì mới cũ giữ nguyên chữ; nút "Thử ngay" tự ẩn vì không còn nút `liveBark`.
- Máy chủ: bỏ GET /api/dogbark, POST /api/dogbark/cancel, giới hạn tốc độ `jr_bark_`, header microphone của trò (chỉ còn theo LIVE_KARAOKE_MIC; /api/karaoke/birth cũng chỉ còn theo công tắc đó). Live service: bỏ live/dog_bark.py, cờ `bark` trong welcome và biến LIVE_DOG_BARK (bản này bỏ qua biến đó; drop-in systemd có thể gỡ khi deploy). Lệnh `jr_bark_join` từ chối ("Kéo co chó sủa đã ngừng rồi nha.", mã `bark_off`), không trừ xu.
- Giữ lại để không mất tiền/dữ liệu và rollback được: bảng `bark_tickets` và mọi dòng (không DROP, SCHEMA_VERSION không đổi); game/dog_bark.py tối giản (apply_fx + fx_commit trả khoản 'bark' còn treo; housekeeping 30 s trả lại vé còn mở do bản cũ để lại, đúng một lần; forget khi xóa dữ liệu); game/dog_bark_board.py tối giản (5 danh hiệu tuần vẫn hợp lệ trong bản lưu, apply_fx trả giải 'bark_weekly' còn treo, forget). Không chốt tuần mới, không tạo giải mới. Bản lưu không có khóa nào của trò. 2.4.15 đọc được mọi thứ bản này ghi (chỉ là dòng vé 'back' + live_effects 'bark' như cũ).
- Tests: bỏ test_dog_bark*, test_live_dog_bark, dog_bark_*.mjs, scripts browser_dog_bark/dog_bark_rollback_check; thêm tests/test_dog_bark_removed.py; sửa các test đếm tiện ích/tòa nhà/venue. Không có Có gì mới.

## mobileui

📱 Màn điện thoại không còn chỗ đè nhau (chủ game 15/10: “nhiều cái UI bị đè nhau ở màn mobile… check cẩn thận từng màn”). Quét tự động mọi màn tới được (HUD 2.5D, Tiện ích + từng nhóm, Thêm + từng nhóm, giao diện cổ điển, màn làm việc của 54 nghề và bước kế tiếp) ở 360×740, 375×667, 390×844, 412×915, 844×390 và 1366×768, có ảnh chụp từng trang cuộn; sửa riêng từng màn, chỉ CSS (một chỗ vẽ canvas của giao hàng), không đổi luật chơi hay bản lưu. Bỏ qua Kéo co chó sủa và Đi chùa (nhánh khác đang làm lại).

- Phố 2.5D, điện thoại dọc: cần điều khiển không còn lấn 8 px vào thẻ “Đang ở”; trong tiệm, hàng nút làm việc (Khách ghé/Pha chế/Kho/Sổ tiệm) không còn đè thẻ “Đang ở”/“Trò chuyện”, cần điều khiển và nút Góc nhìn dời lên theo. Danh sách Tiện ích (và thẻ việc) khi mở nằm trên nút Góc nhìn (trước nút này che dòng “Thư giãn”, 360–375 px). (isometric.css)
- Đầu mỗi bảng trên điện thoại hẹp (≤ 400 px): tên được hai dòng thay vì “Hai ly c…”, “Định…”, “T…” (Tủ đồ); ví + quỹ xếp hai dòng thay vì chữ đè lên nhau và “320 xu” bị cắt (Người quen, Túi đồ, Chuẩn bị, Sổ tiệm); nút ngắn trong đầu bảng (“Quay lại”, “🛵 Sổ shipper”) không xuống dòng. Gợi ý “Bước tiếp theo” trong đầu bảng có hàng riêng, hết cảnh bị bóp thành cột một chữ cao 320 px (Chăm sóc khách hàng). (compact.css D1–D2)
- Bản đồ phố cổ điển: thông báo nằm trên mặt đường, không đè hàng nút “📋 Danh sách”, “🏝️ Ra đảo nhặt rương”, “Chỉ đường”. (compact.css D3)
- Bàn văn phòng (HR, thư ký, IT, kế toán…) điện thoại ngang: hồ sơ đang mở không còn bị cắt còn 24 px dưới “Nhận thêm việc”; thẻ kế hoạch không bóp tên thành “Gói / báo / cáo”. (office_kit.css)
- Hướng dẫn viên điện thoại ngang: nút “Chọn …” và ↶ không đè “Chọn thêm 2 điểm”. (teach.css)
- Quán ăn (≤ 360 px): chai sốt ớt không còn co còn ~60 px để số lượt đè lên 🌶️. (restaurant.css)
- Bán hoa: nhãn “Đúng tông”/“Khách cần” nằm trên mép thẻ, không đè bông hoa. (florist.css)
- Giao hàng tự lái (sân < 420 px): dòng “km/h · Xăng” vẽ phía trên cần lái, không nằm dưới cần lái và bàn đạp Phanh/Ga. (delivery_isometric.js)
- Nhà, xe, điện thoại (≤ 480 px): giá xuống dưới tên khi không đủ chỗ (trước “Du / thuyền / Hoàng / Hôn”), chip “Giữ xe & bảo dưỡng … xu/tháng” không tràn khỏi thẻ. (house.css)
- Sưu tập, Đi chơi và các danh sách mua sắm (≤ 400 px): sao và giá xuống dòng dưới tên thay vì bóp tên thành ba dòng (“Tourbillon / Kim / Cương”). (spend.css)
- Công cụ: `scripts/browser_mobile_sweep.py` + `scripts/mobile_layout_detect.js` (chạy lại toàn bộ lượt quét).
## wishtree (🌳 Cây ước nguyện + chùa 2.5D, chủ game 15/10)

🌳 Cây ước nguyện (chủ game 15/10: “mọi người vào 1 cái cây, rồi ghi cái ước nguyện mình muốn chứ k phải chọn chọn… có rất nhiều cái cây ước nguyện”): 9 cây theo chủ đề (Bình an, Gia đạo, Sức khỏe, Học hành, Sự nghiệp, Tài lộc, Tình duyên, Ước mơ, Tưởng nhớ). Người chơi tự viết điều ước (3–150 ký tự, emoji được, tối đa 3 dòng), chọn màu dải lụa (5 màu), tùy chọn ẩn tên, “Treo lên cây” → dải lụa bay lên cây. Mỗi cây: tranh cây đa của bản đồ với 24 dải lụa mới nhất (chạm để đọc, ‹ › đọc tiếp) và danh sách thẻ giấy bên dưới (mới nhất trước, “Xem thêm” theo con trỏ id). 🙏 Cùng cầu (mỗi người một lần mỗi điều ước), ⚑ Báo cáo (bảng `reports` kind `wish`; 3 người báo cáo → tự ẩn chờ admin; người báo cáo không thấy điều ước đó nữa), người viết tự “Gỡ xuống”; “Của tôi” xem mọi điều ước của mình kèm trạng thái. Lọc chữ như chat (live/filters.py: số điện thoại, link, liên hệ, từ nặng bị che; bản gốc chỉ admin thấy). Giới hạn: 5 điều ước / người / ngày VN (đếm trong giao dịch của bản lưu: lần thứ 6 bị từ chối, bản lưu không đổi), 6 lần treo/phút/phiên + 30/phút/IP ở /api/command (`WISHES_PER_MINUTE`), đọc 120/phút, báo cáo 10/10 phút. Admin: mục “Ước nguyện” (bị báo cáo trước; Gỡ / Treo lại; không xóa). Tắt treo mới: `MNL_WISH_OFF=1`. Xóa tài khoản (“XOA”) xóa điều ước + lượt cùng cầu của người đó; ngoài ra không xóa gì (chỉ đổi trạng thái).
Treo một điều ước = việc `nguyen` của chùa (`jr_chua_do {act:'nguyen', tree, text, color, anon}`): cùng tinh thần +3, cùng `journey.chua.did/n` như trước; chữ KHÔNG vào bản lưu (bảng mới) nên bản lưu đọc được bằng 2.4.14 (test chạy `chua.validate` của origin/main). Thẻ lời chúc cũ (chọn người/điều mong) vẫn nhận từ client cũ, vẫn quản lý chia sẻ ở “Quanh đây → 📜 Bảng lời chúc cũ” (chỉ hiện khi có thẻ).
🛕 Chùa 2.5D (chủ game 15/10: “tối ưu hết chỗ chùa… theo dạng 2.5d trình bày rõ ràng và đẹp”): một sân chùa isometric (public/js/scenes/chua-iso.js) dùng lại tranh của bản đồ 2.5D (chùa careers-v1, cây đa, sheet cây cỏ — không thêm ảnh mới) và nhân vật bản đồ (4 hướng, 3 bước): chánh điện + chiếu khấn + mõ + thầy Huệ Minh, gác chuông, lư hương, hồ sen + ghế, giá chổi, bàn cơm chay + bếp bà Nhạn, cổng tam quan, Vườn ước nguyện 9 cây (dải lụa theo màu các điều ước mới nhất, bảng tên + số điều ước). Chạm sân để đi, kéo để nhìn quanh; thanh bước Thắp hương → Khấn → Ước nguyện → Tụng kinh + Quanh đây. Bỏ 3 khu (sân / chánh điện / nhà ăn) và nút chọn khu; mọi việc cũ (thắp hương, chuông, khấn, tụng kinh theo nhịp mõ, cơm chay, nói chuyện, công đức) giữ nguyên. Đời thường: thêm nút “🌳 Vườn ước nguyện”; bỏ 4 lời nguyện chọn sẵn ở “Làm nhanh”.
DB: SCHEMA_VERSION 44 — chỉ thêm bảng `chua_wishes`, `chua_wish_prayers` (+ chỉ mục), không FK, không backfill; bản 2.4.14 bỏ qua chúng (rollback an toàn, điều ước vẫn giữ). Không khóa mới trong bản lưu. Có gì mới: chưa thêm (chờ chủ game; đề xuất: “🌳 Chùa mới 2.5D với Vườn ước nguyện: tự viết điều ước, treo lên cây, đọc và cùng cầu cho nhau.”).
Kiểm: tests/test_chua_wish.py, tests/temple-walk-ui.mjs, scripts/check_chua.mjs (sân 2.5D: chỗ đứng, đường đi, vẽ), scripts/browser_wish_trees.py (360×740, 390×844, 844×390, 1280×800, + `--lang en`), scripts/browser_chua.py, scripts/browser_chua_visibility.py.

# v2.4.15 — 2026-10-15

⚡ Giảm lag (chủ game 15/10). Bản lưu lớn (54 nghề, tới 14 MB) làm mỗi lệnh mất 1–1,6 s: sổ thu chi mỗi nghề giữ tới 1.200 dòng, phần lớn là 4–5 dòng cho từng đơn riêng của nhân viên.
- Sổ thu chi: đơn riêng của nhân viên (lương, vật tư, doanh thu, thưởng 40%, 🧩 Phúc lợi) cộng vào một dòng mỗi ngày cho từng nhân viên ("Lương đơn riêng · Nhi · 37 đơn", ref `sum:<nhóm>`); tổng tiền, kiểm ví và mọi tổng theo ngày không đổi, chi tiết từng đơn vẫn ở biên nhận. LEDGER_MAX 1200 → 400: phần dư chuyển vào archive như trước (không mất). Bản lưu lớn nhỏ đi 25–40%.
- Tính bù đơn nhân viên: hàng đợi heap thay cho quét lại mọi nhân viên mỗi đơn (cùng thứ tự, đã so từng byte trên 5 bản lưu thật); mỗi lệnh tính tối đa 0,3 s (SETTLE_SECONDS), phần còn lại lệnh sau tính tiếp.
- 6 GET không đọc bản lưu nữa (home-guests, garage/spouse, family/baby, wedinvite, wedding, feedback/mine).
Bản cũ đọc được bản lưu mới (dòng gộp là dòng sổ bình thường). Không có Có gì mới.
# v2.4.14 — 2026-10-15

🔁 Tự đặt hàng giá 100.000 xu (trước 350.000, chủ game 15/10); người đã mua giá cũ được hoàn phần chênh bằng quà hệ thống. Không có Có gì mới.

# v2.4.13 — 2026-10-14

Gồm autoreorder (#387): 🔁 Tự đặt hàng mua 350.000 xu mỗi nơi làm (khóa nghề `auto_order` tùy chọn), tự đặt khi dưới ngưỡng từ quỹ tiệm, giữ sàn quỹ + trần 50%/ngày. Có gì mới: 1 dòng.

## autoreorder (🔁 Tự đặt hàng, góp ý #387)

🔁 Tự đặt hàng: mở khóa trả phí cho từng nơi có kho (350.000 xu = bậc 5 của thang giá chung, cùng giá Bộ đếm kho · Bậc 5 mở 🤖 Tự nhận hàng; trả bằng quỹ trước, thiếu lấy ví), mua ở Kho (dòng 🔒 có giá, chỉ hiện khi đã đặt hàng ≥3 lần, #384) hoặc Thiết bị. Mỗi món một công tắc và “còn dưới X thì đặt Y” (mặc định X = 20% kệ, Y lấp tới ~90% trong hạn mức mỗi dòng). Hàng trên kệ + đang về dưới X thì đặt Y với nhà cung cấp dùng lần cuối (không thì Hạt Nắng) qua đúng đường inv_order (giá, giá sỉ, ship, thời gian giao, giao thiếu, lô FIFO); chỉ trả bằng quỹ, giữ sàn (80 xu + hóa đơn chưa trả + một ngày lương), tối đa 50% quỹ đầu ngày mỗi ngày, mỗi món một đơn tự đặt đang về, chừa 2 chuyến cho đơn tay; món vơi nhất đặt trước. Chạy sau mỗi thao tác và khi tải game (cả lúc vắng mặt), sau 🤖 Tự nhận hàng. Sổ tay: “🔁 Tự đặt 40 vắt Mì tươi (Nhà phân phối Hạt Nắng, ~13:15 hôm nay)”; quỹ thiếu: “🔁 Quỹ không đủ để tự đặt.” (một lần/ngày). Bản lưu: khóa tùy chọn `careers.<nghề>.auto_order` (không phải mã nâng cấp: 2.4.11 từ chối mã lạ trong `upgrades`); 2.4.11 đọc được, bỏ qua (tests/test_auto_order.py chạy trên `git archive rel-2.4.11`). Lệnh mới `stock_reorder` (không tốn giờ tiệm). check_task_compat OK. Có gì mới: một dòng 🔁 (đang gắn vào mục 2.4.11; đánh số lại khi phát hành).

# v2.4.12 — 2026-10-14

🧩 Ghép ba Phố Mây: bỏ giới hạn 15 màn mới mỗi ngày (chủ game 14/10); vẫn giữ thời gian tối thiểu mỗi màn. `n` vẫn lưu tối đa 15 để bản cũ đọc được. Không có Có gì mới.

# v2.4.11 — 2026-10-14

Gồm chua (đi chùa từng bước, gọn đẹp) và profnghe (hồ sơ gọn, tìm nghề có tìm kiếm + lọc). Có gì mới: tổng hợp các bản 2.4.3–2.4.11 (không nhắc chợ đen/hội chợ).

# v2.4.10 — 2026-10-14

🧩 Ghép ba Phố Mây: chồng úp vẽ ô trên cùng (đã lật) ĐÈ LÊN các ô úp bên dưới — 2.4.7–2.4.9 vẽ ngược, ô úp che mất ô mở nên chạm vào chỉ trúng ô úp, chồng không lấy được và cuối màn dư 3 ô không khớp (màn 5 trở đi, 96/100 màn; chủ game báo ở màn 8). Đổi 🪷 thành 🥥 (🪷 hiện ô trống trên iOS 15.0–15.3, từ màn 77). Thêm scripts/browser_tile_levels.py: chơi trọn màn 1–20 bằng chạm thật trên màn hình điện thoại. Màn chơi, nước đi và bản lưu giữ nguyên. Không có Có gì mới.
# v2.4.9 — 2026-10-14

Gồm mapart (bản đồ 2.5D và cổ điển đẹp hơn, chim bay; không đổi vị trí cửa/đường) và treasure-free (rương kho báu không giới hạn mỗi đợt/ngày). Không có Có gì mới.

## mapart (không có Có gì mới)

- Bản đồ đẹp hơn (chủ game “map đẹp hơn đi”), không đổi chỗ nào, cửa, đường đi hay vùng chạm. Phố 2.5D: cỏ có khóm cỏ, hoa nhỏ, sỏi và mảng nắng/bóng; đường có viền cỏ, lòng đường sáng hơn ở giữa và đá viền; bóng dưới nhà mềm hơn (bỏ vệt xám to). Tất cả nằm trong ảnh nền đã lưu sẵn, không tốn thêm gì mỗi khung hình; chi tiết nhỏ tắt khi thu nhỏ hết cỡ. Bản đồ phố cổ điển: bãi cỏ, hàng cây và mái nhà phía sau, vỉa hè lát gạch, lề đường, lối đi giữa hai mép cỏ, đèn lồng đỏ ở các cột đèn, tên phố trên đường mờ hơn, dấu x3 trên biển chỉ còn một chấm 🔥 (số x3 vẫn ở thanh trên); trên điện thoại, đủ ba nút ở thanh trên thì ẩn chữ “Khu phố” (trước bị che còn một chữ cái). Thỉnh thoảng có một đàn chim bay ngang (cả hai bản đồ): không có vòng lặp khung hình, tắt khi giảm chuyển động, tab ẩn hoặc đang ở trong nơi làm việc. Đo trên Chrome giả lập CPU chậm 4×: thời gian mỗi khung hình không đổi; dựng lại ảnh nền (thỉnh thoảng khi kéo bản đồ) chậm hơn khoảng 2–5 ms (2.5D) và 5–15 ms (cổ điển, một lần mỗi cỡ màn).

## treasure-free

Rương kho báu bản đồ 2.5D: bỏ giới hạn 1 rương/đợt và 5 rương/ngày (chủ game 14/10 "mỗi người nhặt thoải mái"); rương nhặt xong biến mất với mọi người, ai tới trước nhặt trước. Vẫn cần tài khoản đủ 1 ngày tuổi và đứng gần rương.

## daygate

Ngày thực đạt chuẩn (Mở rộng nghề, Chuyên môn nghề) được tính NGAY khi đạt (≥3 việc sạch, ≥80%; mốc có hợp đồng: thêm ca quản lý nghiệm thu), mỗi ngày lịch một lần, lỗi sau đó trong ngày không trừ; không còn chờ 0h. Mốc đầu cần 2 ngày thực thay vì 3. Dòng sống “Hôm nay: x/y việc sạch · đã tính ✓ / còn N việc sạch nữa” ở Mở rộng nghề, Chuyên môn, Tay nghề lâu năm và hàng “ngày tốt” Thăng tiến. Bản lưu: khóa tùy chọn `careers.<nghề>.scale_credit` (2.4.8 đọc được, bỏ qua). Không có Có gì mới.
## chua (không có Có gì mới)

- 🛕 Đi chùa gọn và đẹp hơn (chủ game “nhìn lộn xộn quá”): đầu cảnh một dòng (Rằm · cơm chay · thanh tinh thần), khu chùa thành nút nổi trên cảnh, thanh bước đi lễ dưới cảnh 🪔 Thắp hương → 🙏 Khấn → 📜 Lời chúc → 💌 Chia sẻ (chạm là tự đi tới, kể cả qua cửa khu khác; ✓ khi đã làm hôm nay) và 🧭 Quanh đây cho các chỗ còn lại; khấn và lời chúc hỏi từng câu một (cho ai → mong gì, chỉ hiện điều hợp → đọc lại), lời chúc xem trước như mảnh giấy đỏ, sau khi treo có nút “Chia sẻ lên bảng chung”; mỗi khung một nút chính (“Tiếp: …” dẫn sang bước sau), lời giới thiệu vào “?”; trên máy tính khung nằm bên phải và cảnh trượt sang để còn thấy nhân vật; tiếng chuông nhỏ khi thắp hương/treo lời chúc, “✨ +n” bay lên trên nhân vật. Luật, phần thưởng, dữ liệu lưu không đổi; chỉ giao diện (check_task_compat OK).
# (chưa phát hành) — profnghe

Hồ sơ & tìm nghề (chủ game 14/10: "chỗ profiles quá lỗi, lộn xộn quá, tìm nghề cũng khó"). Nơi làm việc ở Hành trình: ô tìm nghề không cần dấu ("pho", "tra sua"; khớp nguyên chữ trước), lọc Đang làm / Mở được / Khóa và theo nhóm, thứ tự đang làm → mở được → khóa, mỗi nghề một hàng gọn (tên, ngày · cấp · quỹ, bước mở khóa “Xong chương N là mở” / “Mở ở chương N” — nghề khóa nay hiện tên), nhóm dài gập sau 6 dòng “Xem thêm”; gõ và chạm lọc chỉ ẩn/hiện hàng có sẵn (không vẽ lại); 🏆 Xếp hạng nghề ngay đầu mục, thẻ lời x3/nghề hot giữ nguyên. Thẻ nhân vật: ví lớn không tràn ô (809k xu, số đủ ở nhãn), danh hiệu đang đeo một dòng (cái đầu có tên, còn lại biểu tượng), xe/điện thoại/Thay đồ thành một hàng chip. Phố nghề: nút “Quay lại phố” mũi tên đúng chiều (trước là ›), tab Hồ sơ hiện thẻ của bạn như hàng xóm thấy + “✏️ Sửa hồ sơ” gập, hồ sơ người khác gọn (đầu thẻ, một hàng đồ có, nút chính, Nơi làm việc và đánh giá 3 cái + “Xem thêm”, “Cấp” thay “Lv”), thẻ ở phố 2 nghề +N. Chỉ giao diện, không đổi lưu. Không có Có gì mới.

# v2.4.8 — 2026-10-14

Gồm declutter (#384): bớt chữ nhỏ ở Hành trình/Công việc, Kho, màn làm ca, HUD; chế độ gọn tự bật ở mọi cỡ màn hình với giao diện 2.5D (tắt được trong Cài đặt). Không có Có gì mới.

# v2.4.7 — 2026-10-14

🧩 Ghép ba Phố Mây sửa lỗi “mãi không ghi nhận” và lag: chơi hoàn toàn trên máy, qua màn là hiện thẻ thắng ngay, máy chủ ghi nhận ngầm bằng MỘT lệnh `jr_tile_end {n, moves, ms, v}` (trợ giúp tính tiền lúc kết thúc), hàng chờ giữ qua tải lại trang (“Đang ghi nhận…” → “✓ Đã ghi nhận”); màn tự mô tả, không còn phụ thuộc `cur` (bỏ lỗi tile_none, uid 877); chồng úp lật từng ô (bản cũ để ô dưới úp mãi từ màn 8: “3 ô cuối không khớp”); bảng màn mới khó hơn từ màn 5 (bảng cũ v1 vẫn chấm được); bớt chữ trên màn chơi. journey.tile giữ nguyên dạng 2.4.5. Không có Có gì mới.

# v2.4.6 — 2026-10-14

Gồm wk244: 🏆 Top lời chợ đen theo tuần như Top lỗ (schema 43: chỉ mục; scripts/fair_board_recompute.py --week), 🤖 Tự nhận hàng mở bằng Bộ đếm kho · Bậc 5 (tự đếm, xếp kệ, khiếu nại thiếu; journey/nghề auto_stock tùy chọn). Không có Có gì mới.

# v2.4.5 — 2026-10-14

Gồm fb382: ngày thực đạt chuẩn tính cả việc khách giữ lại từ hôm trước, dòng điều kiện hiện “Hôm nay: …” + “Cách tính” (#382 #383); đảo nhặt rương có “📋 Danh sách rương” cho trình đọc màn hình (#381). Không có Có gì mới.

# v2.4.4 — 2026-10-14

Quầy: nhập hàng mỗi lần mặc định 200 phần (trước 5, chủ game 14/10: quầy hết hàng không mở lại được); các bậc trả phí 300 → 20.000. Vượt mức thì thẻ nhập hàng báo ngay dưới ô nhập. Không có Có gì mới.

# v2.4.3 — 2026-10-14

Gồm fb374 (nút nâng sức chứa kho riêng, giá nail ×2,5 — góp ý #374 #375 #378), bmrank (Bảng vàng chợ đen cộng lại tiền phạt đã hoàn, phạt công an người chơi cập nhật ngay; scripts/fair_board_recompute.py), tile-match (🧩 Ghép ba Phố Mây, journey.tile tùy chọn, phúc lợi +0,2 %/màn tối đa +20 %).

## declutter (không có Có gì mới)

- Bớt chữ nhỏ cho người mới (chủ game “xóa bớt các chữ nhỏ kia đi”, góp ý #384): giao diện 2.5D bật “Giao diện gọn” ở mọi cỡ màn (trước chỉ điện thoại; Cài đặt → Giao diện vẫn Tắt được); Hành trình bỏ dòng lý do chung chung trên nút, nhãn nhóm nghề trên thẻ, “Mới mở” ở chương 1, “vắng chủ không tốn phí”, chip “📉 Lãi thấp”, dòng gợi ý danh hiệu, dòng “Học rồi thi…”; Kho bỏ dòng khóa 🤖 Tự nhận hàng khi chưa có Bộ đếm kho · Bậc 5, giờ mở cửa và đơn vị dưới từng ô (vào tooltip), dòng “nâng sức chứa trước”; tạp hóa: cách nhập & sức chứa vào “?”; tủ kính tiệm bánh, thẻ Giới thiệu nghề tiệm áo, mục nhiệm vụ HUD và cần điều khiển gọn chữ hơn; hộp hỏi giao diện ngắn lại. Lý do nút bị khóa, giá, tiền, hạn giữ nguyên. Chỉ giao diện; việc sinh nhiệm vụ không đổi. check_word_caps: Kho ≤ 66 chữ (trước 67–79), màn làm việc bảo mẫu/tiệm bánh/tạp hóa ≤ 22.

## fb382 (không có Có gì mới)

- Ngày thực đạt chuẩn (góp ý #382, #383; Mở rộng nghề và Chuyên môn nghề): việc khách giữ lại từ ngày nghề trước, làm xong hôm nay nay được tính vào việc sạch và ngày thực (trước đây bị bỏ qua: một tiệm quần áo mất 5 việc, 4 việc sạch trong ngày 14/10). Dòng điều kiện hiện tiến độ hôm nay (“Hôm nay: 16/18 việc sạch · đạt, cộng lúc 0h”) và “Cách tính ?” (ngày lịch 0h–24h giờ Việt Nam, ≥3 việc tự làm không lỗi, ≥80% sạch, từ mốc 2 thêm ca quản lý nghiệm thu; khác ngày đạt chuẩn của Tay nghề). Nút bị khóa ghi “Cần thêm N ngày thực đạt chuẩn.” thay cho câu sai “Ngày thực đạt chuẩn đã kết thúc”. Tay nghề lâu năm giữ luật cũ, dòng ngày đạt chuẩn ghi rõ “Ngày nghề có ≥3 việc sạch, ≥80%; cộng khi khép ca”. Save không đổi dạng; bản cũ vẫn đọc được.
- Đảo chung, nhặt rương cho người dùng trình đọc màn hình (góp ý #381): nút “📋 Danh sách rương” ở đầu màn liệt kê mọi rương, gần nhất trước (“Rương 1 · cách khoảng 12 bước”), mỗi dòng có nút “Đi tới và nhặt” tự đưa nhân vật tới rương và nhặt theo đúng đường chạm rương (máy chủ vẫn xác minh vị trí). Kết quả và lỗi được đọc qua vùng thông báo; danh sách tự cập nhật mỗi giây mà không làm mất tiêu điểm, nhớ trạng thái mở cho lần sau và khi mở sẵn thì tiêu điểm vào danh sách thay vì bản đồ. Chưa dịch tiếng Anh (cả màn đảo chưa có bản dịch).

## wk244 🤖 Tự nhận hàng (góp ý #326 #333 #361; Có gì mới: chủ game quyết định)

- 🤖 Tự nhận hàng: có 📦 Bộ đếm kho · Bậc 5 của nghề (đã bán, giá giữ nguyên) thì thùng hàng tới cửa được máy chủ tự đếm và nhập kệ, đúng như một lần đếm đúng: đủ số thực có, mỗi đơn thành một lô theo giá vốn của đơn, đơn gộp nhận cả thùng một lần; giao thiếu thì tự khiếu nại theo cùng đường hoàn tiền của nút “Khiếu nại phần thiếu” (một lần). Thùng không vừa kệ vẫn chờ ở cửa như trước. Chạy sau mỗi thao tác của nghề và khi tải game (hàng về lúc vắng mặt lên kệ trước khi người chơi xem). Áp dụng cả quầy mẹ & bé / nhà thuốc (kiện cũ), vật tư hợp đồng và vật tư chuyên môn (giữ giá vốn từng lô, FIFO). Sổ nghề ghi “📦 Tự nhận N món: …”.
- Bảng Kho có công tắc “🤖 Tự nhận hàng: Bật/Tắt” (mặc định Bật khi đã mở; tắt thì quay về đếm tay); chưa mở thì hiện một dòng khóa nêu Bộ đếm kho · Bậc 5. Khóa save tùy chọn `careers.<nghề>.auto_stock = false` chỉ có khi người chơi tắt; 2.4.3 vẫn nhận save có khóa này (đã kiểm bằng git archive rel-2.4.3). Việc sinh nhiệm vụ không đổi.

## wk244 Top lời theo tuần (không có Có gì mới: thay đổi chợ đen)

- Bảng vàng chợ đen: Top lời tính theo tuần như Top lỗ (chủ game 14/10), cùng sổ `fair_loss_week`, cùng tuần thứ Hai 00:00. Lời ròng tuần cộng tiền phạt được hoàn (`refund-cd-…`) trả vào save trong tuần, một lần. 👑 Vua trò chơi / 🎪 Cao thủ chợ đen trao thứ Hai từ 19/10 theo tuần vừa qua, cùng lúc với Top lỗ, không trao hai lần. Dải người chơi vẫn hiện “lời tích lũy cả chợ”. Schema 43 chỉ thêm chỉ mục. `scripts/fair_board_recompute.py --week` cộng các khoản hoàn đã trả trong tuần trước bản này (chạy thử mặc định).

## fb374 (không có Có gì mới)

- Kho (góp ý #375, #378): bảng Kho có riêng nút “Nâng sức chứa lên …” (Thiết bị → Sức chứa kho nghề) bên cạnh “Nâng nhập mỗi dòng”; trước đây chỉ có nút hạn mức nhập 80 → 120 nên người chơi mua nhầm tưởng là sức chứa. Khi một dòng đã nhập đầy kệ, bảng Kho không mời mua thêm hạn mức nhập; Thiết bị ghi rõ kho đang chứa bao nhiêu. Báo “Kho chứa tối đa …”/“Kệ … không đủ chỗ” chỉ chỗ nâng sức chứa. Không đổi giá, quyền đã mua hay dữ liệu bản lưu.
- Tiệm nail (góp ý #374): giá dịch vụ ×2,5 (cắt dũa 10, sơn thường 20, sơn gel 38, tháo gel 12, nối móng 50, French 10, vẽ hoa 12, đính đá 10, chăm da tay 15). Ngày 4–7 trước đây trung vị 20 xu/ngày, lỗ nhẹ, so với chăm thú cưng 60, chụp ảnh 73, salon 215. Bảng giá đã lưu theo giá cũ (kể cả giá tự chỉnh 75–125%) chuyển sang cùng vị trí trong khung giá mới một lần khi tải; đơn riêng mặc định của nhân viên nail 12 → 30 xu (= cắt dũa + sơn thường). Không đổi dữ kiện nhiệm vụ; không thêm khóa bản lưu, bản cũ đọc giá mới như giá thường.

# Chưa phát hành

- Bảng vàng chợ đen (Top lời) tính đúng lời ròng: tiền phạt chợ đen đã được hoàn bằng quà hệ thống (mã `refund-cd-…`, 8 người chiều 11/10, 18.538.100 xu) được cộng lại vào điểm (game/fair_refund.py; save không đổi); phạt của công an người chơi (và mọi thay đổi qua marriage._mutate) cập nhật ngay dòng bảng và sổ Top lỗ tuần trong cùng giao dịch, không còn chờ lệnh kế của người bị phạt. Tính lại dòng bảng hiện có: `scripts/fair_board_recompute.py` (mặc định chạy thử, `--apply` để ghi). Không công bố, không đổi schema hay save.

## tile-match (Có gì mới: 1 dòng, bản phát hành quyết định số bản)

- 🧩 Ghép ba Phố Mây (thiết kế của chủ game): trò ghép ba kiểu Tile Master ở Khu phố và trên Bản đồ phố. 100 màn có độ khó tăng dần (thêm loại đồ, tầng, chồng úp, khay sát hơn, hình trái tim/ngôi nhà/chùa/hải đăng…; từ màn 40 có 🔒 khóa cần 🔑, từ màn 55 có 🧊 băng chạm hai lần). Mỗi màn là seed + tham số (game/tile_match_levels.py, dựng bằng scripts/build_tile_levels.py), đã kiểm bằng bộ giải; 4 trợ giúp (hoàn tác, xáo, đẩy ra, thêm ô) miễn phí vài lượt mỗi ngày, sau đó trả xu, giá gấp đôi mỗi lần trong màn. Mỗi màn MỚI qua lần đầu: +0,2% tiền kiếm từ làm việc và kinh doanh (tối đa +20%), ghi thành dòng riêng "🧩 Phúc lợi" ở tiền làm việc, lương, đơn nhân viên, quầy, hợp đồng/chuyên môn và hoa hồng nước ngoài; không áp dụng cho lãi ngân hàng, Mây Coin, vàng, chợ đen, kéo co, đấu giá, chuyển khoản, quà và thu hồi; không nhân lại trong ngày x3. Máy chủ chơi lại các nước đi theo seed để xác nhận thắng, tối thiểu 20 giây/màn và 0,25 giây/lần chạm, tối đa 15 màn mới mỗi ngày. Bản lưu: journey.tile (tùy chọn, 2.4.2 giữ nguyên); không DDL; dữ kiện nhiệm vụ không đổi.
- Có gì mới (đề xuất): 🧩 Ghép ba Phố Mây: 100 màn ở Khu phố. Mỗi màn mới qua lần đầu, tiền làm việc và kinh doanh +0,2%, tối đa +20%!

# v2.4.2 — 2026-10-14

- Theo yêu cầu chủ game, gom thay đổi 2.0.6–2.4.1 thành một thẻ Có gì mới: nghề, chứng chỉ, thăng tiến/thi đua, chùa và quyền riêng tư, đi lại/chat/reaction, quy mô/chuỗi, 540 gói chuyên môn, nâng kho/nhập/quầy và các lỗi đã sửa.
- Thẻ dùng mốc thông báo mới 2.4.2, tự hiện một lần khi người chơi quay lại ở lúc rảnh; xem lại tại Cài đặt → Cách chơi → Xem các cập nhật mới. Giữ cơ chế chờ hết thao tác và không hiện cho người vừa tạo nhân vật.

# v2.4.1 — 2026-10-14

- Sửa khung “Nói gần đây” của map 2.5D che nút zoom: chừa khoảng riêng cho bộ điều khiển máy ảnh ở màn hình nhỏ, ngang và máy tính; chat/reaction vẫn dùng được.
- Thêm đủ 540 gói chuyên môn (54 nghề × 10 bậc) trong Thăng tiến: định lượng vật tư, trình tự thao tác, tiêu chí bàn giao riêng theo gói. Mở gói bằng học phí, học và thực hành đạt yêu cầu trước khi nhận đơn.
- Học phí tuần tự 3.000 → 100.000.000 xu; tổng 152.692.000 xu mỗi nghề có thu phí. Có điều kiện kinh nghiệm, việc tự làm không lỗi và ngày thực đạt chuẩn; thực hành lại không thu thêm tiền. Chùa học công quả miễn phí, chỉ tăng tinh thần trong trần 100.
- Đơn chuyên môn dùng chung suất quản lý; một người trực tiếp làm một đơn chuyên môn mỗi lần. Kho riêng dùng quyền nâng sức chứa/hạn mức nhập đã mua, tính hàng đang về và đang giữ cho đơn. Mua, nhận, giữ và tiêu hao vật tư theo giá vốn từng lô; thuế, công và tiền nghiệm thu có biên nhận, không nhân thưởng cũ.
- Nghề công vụ nhận vật tư hiện vật của đơn vị và phụ cấp nghiệm thu; ngân sách đơn vị không chuyển thành thu nhập cá nhân. Nội dung tình huống là mô phỏng trong game.
- Giữ nguyên dữ kiện nhiệm vụ và kho cũ; gói mới phục vụ đơn chuyên môn riêng. Nhãn chính có tiếng Anh, nội dung 540 tình huống hiện dùng tiếng Việt dự phòng. Không đổi schema DB; cần giữ bản chạy hiểu dữ liệu chuyên môn sau khi người chơi sử dụng.

# v2.4.0 — 2026-10-14

- Mở lộ trình quy mô 8 bậc cho 54 nghề: kinh doanh phát triển cơ sở/chuỗi; nghề công vụ nhận phạm vi điều phối; chùa phát triển công quả. Không bán chức vụ hoặc cấp hàm.
- Tạp hóa có tổng phí quy mô 402.300.000 xu, tối đa 12 điểm và 50 vị trí toàn mạng. Các nhóm nghề dùng giá và tài nguyên riêng. Lên bậc cần việc sạch, ngày thực đạt chuẩn, chứng chỉ và quỹ nghề.
- Hợp đồng nhiều bước: dự toán, nhập/giữ vật tư, xếp người vào vị trí, xử lý phát sinh, nghiệm thu và đối soát. Tiền vật tư, lương, mặt bằng, hao hụt và thuế có biên nhận; lãi không nhân lại thưởng cũ. Suất quản lý dùng chung: khởi đầu 1, thêm 4/ngày thực, giữ tối đa 12.
- Sức chứa và nhập mỗi lần vẫn là quyền trả phí độc lập; kho điều phối tính cả hàng đang về và hàng giữ chỗ, dùng chung giữa các cơ sở. Cơ sở phụ kinh doanh dùng chung hạn mức số quầy toàn tài khoản.
- Cơ sở có nội thất đi lại, vật cản, vị trí và nhân sự; cho phép ghé thăm công khai hoặc giữ riêng tư, chat và reaction theo phòng. Không đổi dữ kiện nhiệm vụ cũ hay schema DB.
- Hợp đồng hiện có một dòng vật tư lõi riêng theo nghề; chưa triển khai 540 công thức/mẫu hàng từng được đề xuất. Tình huống mới ưu tiên tiếng Việt; nhãn thao tác và tài chính có bản tiếng Anh.

# v2.3.1 — 2026-10-14

- Chat/reaction và tương tác 2.5D; hạn mức nhập trả phí theo nghề; lịch sử hôn nhân và chặn hoạt động đám cưới đã hủy.
- Chợ đen: đúng một lượt đầu 55%, sau đó theo tỷ lệ đã thống nhất.

# v2.3.0 — 2026-10-13

- Thêm thi đua cùng 3 đồng nghiệp NPC cho đủ54 nghề, với162 tình huống phân công, kiểm tra và ghi nhận. Mỗi kỳ10 ca thực sự làm việc; đạt80/100 được tính kỳ tốt bất kể thứ hạng NPC. Năm hạng thi đua cần tối thiểu150 ca cùng bậc nghề tương ứng.
- Thưởng kỳ tối đa300/900/2.000/5.000/10.000xu theo hạng và không quá10% thu nhập cơ bản tự làm hợp lệ; không nhân lại x3/trang bị/nhân viên. Chùa nhận tinh thần theo phần còn thiếu đến trần100. Tình huống nhóm lưu một lựa chọn/ngày nghề; tiến trình cũ được giữ.
- Mở tiện ích kiểm đếm, hạn mức nhập hàng, sở hữu/nâng quầy và sức chứa theo bậc trả xu. Giá bậc3.000 →100.000.000xu; tổng152.692.000xu mỗi nhánh. Mua tuần tự, server kiểm tra số dư và quyền sở hữu; không xóa tài sản vượt hạn mức cũ.
-27 nghề có nhánh sức chứa kho, mở rộng cả nguyên liệu, lô hàng, hàng giữ cho khách và các kho thành phẩm liên quan. Số lượng hàng hủy/đặt trước được hạch toán đúng khi sức chứa tăng; không tăng cỡ mẻ nấu theo sức chứa.
- Cho phép góp vốn nghề lớn trong trần quỹ; bản dịch và giao diện điện thoại đi kèm. Chưa phát hành540 gói công thức/mẫu hàng trong tài liệu thiết kế.
- Không đổi schema DB hoặc dữ kiện sinh nhiệm vụ. Sau khi có người mua kho/quầy vượt giới hạn cũ, khắc phục bằng bản tương thích2.3.x; không hạ trực tiếp về2.2.1 vì giới hạn kiểm tra bản lưu cũ thấp hơn.

# v2.2.1 — 2026-10-13

- Thẻ chúc ở chùa có hai quyền xem: Công khai hoặc Chỉ mình tôi, chọn khi treo và đổi lại được sau đó. Thẻ đã viết trước đây giữ riêng tư.
- Thêm bảng lời chúc công khai của mọi người, đọc theo trang. Chuyển về riêng tư gỡ thẻ khỏi bảng chung; chỉ chủ thẻ có quyền đổi, kể cả thẻ cũ trong lịch sử.
- Giữ hoạt động chùa lặp không giới hạn và tinh thần tối đa 100; nội dung riêng tư không xuất hiện trong API bảng chung.

# v2.2.0 — 2026-10-13

- Cửa chùa mở thẳng sân đi bộ, có chánh điện và nhà ăn. Thắp hương, cầu may, khấn, tụng kinh và treo thẻ được làm lại không giới hạn; tinh thần vẫn tối đa 100. Cơm chay giữ điều kiện ngày có cơm và bụng chưa no.
- Thẻ chúc người thân lưu riêng tư, giữ qua ngày sống; 40 thẻ gần nhất ở hàng rào, thẻ cũ đọc qua lịch sử. Chống lệnh gửi trùng, giữ bản lưu cũ và không đổi bảng DB.
- Thêm 14 không gian đi lại cho quán cà phê, spa, rạp phim, karaoke, sân chơi thú cưng, salon, làm móng, thủ công, sách, vẽ, nhạc, đọc sách, vườn và gia đình. Chạm để đi, phím mũi tên/WASD hoặc cần di chuyển; có vật cản, điểm tương tác và lối ra.
- Vào phòng miễn phí; tới quầy mới mở dịch vụ hiện có. Đóng dịch vụ trở lại đúng phòng. Giao diện cũ cũng vào được khu câu cá, chèo thuyền và bơi; danh mục đi chơi có lối vào trực tiếp.

# v2.1.0 — 2026-10-13

- Thêm bốn nghề: Xưởng vẽ Màu Nắng, Văn phòng luật Bình An, Tiệm giặt ủi Nếp Thơm và Bưu điện Cánh Thư. Mỗi nghề có quy trình riêng, nhiều loại đơn và nội dung nâng cao theo ngày nghề.
- Thành tích yêu cầu việc đạt chất lượng và ngày thực sự làm việc; nội dung cuối mở từ ngày 40–45. Tiền giặt/vẽ trừ vật tư từng đơn; luật sư và bưu điện nhận lương theo hợp đồng cộng thưởng việc, bưu phí không trở thành thu nhập người chơi.
- Mở giặt ủi ở chương 2, xưởng vẽ và bưu điện ở chương 3, luật sư ở chương 4. Tổng cộng 54 nghề, có địa điểm, hướng dẫn và giao diện điện thoại.
- Mở thang thăng tiến thông thường lên bậc 7; giáo viên có bậc 6–7, phi công giữ 7 bậc, công an giữ hệ thống bổ nhiệm riêng. Thưởng chủ tiệm bậc 5–7 tối đa 42/50/60 xu/ngày; tăng lương nhân viên 66/77/88% trước thương lượng.
- Thêm ba bậc tay nghề cho mọi nghề: 40/120/260 việc tự làm không lỗi, 15/40/75 ngày đạt chuẩn và cấp nghề 20/45/90. Sát hạch 4 câu cần 7/8 điểm; trượt phải làm thêm 3 ngày đạt chuẩn. Thưởng ngày đạt chuẩn 6/12/20 xu có giới hạn lượt trả công, không nhân tiếp theo ngày x3.
- Bản lưu cũ tự bổ sung nghề mới, giữ tiến trình 50 nghề trước. Không đổi dữ kiện nhiệm vụ cũ hoặc bảng DB. Sau khi bản lưu có nghề mới, khắc phục bằng bản tương thích 2.1.x; không hạ mã trực tiếp về 2.0.7.

# v2.0.7 — 2026-10-13

- Thu két: chủ quầy đặt vốn giữ lại tùy ý; tiền còn dư mới về ví, áp dụng cả thu nhiều quầy. Két vào vốn giữ lại phần vượt trần trong két.
- Rương trên phố: ưu tiên nhặt rương khi trùng điểm tương tác với địa điểm, bằng chuột và phím E.
- Du học: nói rõ cách sang ngày sống mới để học tiếp. Đi làm nước ngoài liệt kê đầy đủ ca còn mở và có nút về từng nơi.
- Bổ sung bản dịch tiếng Anh, kiểm thử bảo toàn tiền và tương tác. Không thay dữ kiện nhiệm vụ hoặc bảng DB.

# v2.0.6 — 2026-10-13

🎓 Ba chứng chỉ kinh doanh học trả phí, lần lượt cơ bản / nâng cao / quản lý chuỗi. Học phí cơ sở 500 / 2.000 / 5.000 xu, theo chỉ số giá hiện tại là 550 / 2.200 / 5.500 xu; mỗi khóa gồm một lần thi, thi lại nửa phí hiện hành. Xe đẩy đầu tiên không cần giấy; nhiều xe/sạp cần cơ bản, tối đa hai ki-ốt cần nâng cao, từ ba ki-ốt cần quản lý chuỗi.

🚔 Chủ từ ba quầy chưa đủ giấy nhận một biên bản trong phiên chơi và có 72 giờ thực để học. Sau hạn, phần vượt quyền dừng nhận đơn mới và dừng chi phí tự động; giữ tài sản, đơn đã nhận và một quầy sinh kế cho chủ cũ. Học đủ hoặc chọn quầy ưu tiên cập nhật quyền hoạt động, không mở lại quầy chủ tự đóng. Không thu phạt hay tự ghi danh.

Giao diện chỉ rõ học phí và vốn mở tiệm, khóa còn thiếu, thời hạn và lý do hạn chế; đi học rồi quay lại vị trí đang xem. Có bản dịch tiếng Anh. Không bật popup thông báo toàn hệ thống.

Kỹ thuật: hồ sơ tùy chọn trong journey.quay.business_license, không thêm bảng DB. MNL_BUSINESS_LICENSES_OFF=1 tắt điều kiện mở rộng; MNL_BUSINESS_INSPECTIONS_OFF=1 tắt cưỡng chế. Rollback sử dụng mã 2.0.6 với hai cờ này, không quay về 2.0.5 vốn chưa biết các chứng chỉ mới.

# v2.0.5 — 2026-10-12

Công an (spec chủ phố 11/10): thêm chức Giám đốc CATP (tối đa 1 người chơi) và hàm Thiếu tướng; Phó Giám đốc CATP tối đa 5 người chơi (bảng cand_roster, kiểm ghế trong giao dịch lệnh). Lên Giám đốc cần 20 ngày ở Phó Giám đốc, lên Thiếu tướng cần 10 ngày ở Đại tá, tổng 30 ngày liền không vi phạm. Học viên (bảng đỏ trơn) hiện sau khóa chuyển loại, trước Thiếu úy. Quân hàm theo bảng màu mới (đỏ #EE0000, vạch #FFFF00 hướng lên; Úy/Tá sao to hơn 2%, vạch #FFFF66, sao #FFFF33; Thiếu tướng nền #DD0000).

Bút tích đỏ: cảnh cáo thứ 2 là một kỳ Không hoàn thành nhiệm vụ, thứ 3 hạ 1 bậc hàm và giam hàm 20 ngày làm, thứ 4 (chưa đủ 10 ngày sạch) khai trừ cuối ca, tạm giữ 3 ngày, cấm vào lại ngành Công an. Chỉ huy (từ Ban chỉ huy CA phường) xét thi đua toàn lực lượng và khai trừ lỗi nặng.

Ca trực mới: kiểm tra doanh nghiệp (thuế, nguồn hàng, tờ khai hải quan), gỡ bài đòi hỏi ngoài dịch vụ và xử phạt bóc phốt đòi đền bù, trẻ lạc giao nhầm người (hạ 1 bậc, giam hàm đến 15 ngày), án buôn lậu trên 100.000 xu (phá được +1 ngày xét thăng hàm; thất bại, nhận hối lộ, để thoát giam hàm 3 ngày).

Tuần tra Chợ đen giữa người chơi: lục soát, phạt hành chính 30% tiền cược, tạm giữ 1 ngày, bắt giữ 3 ngày; chứng cứ là ván có trả tiền trong 15 phút gần nhất, người chơi nhỏ chỉ bị lục soát. Phong bì tối đa 5.000 xu, tỷ lệ bị phát hiện 5% + 0,5% mỗi lần (tối đa 85%). Schema 41: cand_roster, cand_stops, cand_acts.

Gồm cả các sửa giao diện mới của 2.0.4.2.

# v2.0.4.2 — 2026-10-11

Giao diện mới: bài tập huấn Thư viện tô sáng đáp án đã chọn (#341); nhạc nền mạng chậm phát tiếp từ chỗ đoạn mở đầu dừng, không lặp lại đoạn đầu (#346); thanh công việc và các tab kho luôn vừa màn hình 360 px, không trượt qua lại khi nhập hàng (#348); khay thùng hàng giữ ô 30 px như giao diện cũ (#345); nút Thử lại khi tải phố lỗi bấm được, hộp chọn giao diện đóng ngay khi lưu lỗi, nhãn Xem hướng dẫn không che cần điều khiển/menu, chạm đóng menu không làm nhân vật đi, Esc ngoài phố không làm mờ đảo (#344).

# v2.0.4 — 2026-10-11

Chợ đen: mọi khoản phạt công an là 30% tiền cược của chính ván bị bắt (kèm tịch thu tiền cược); ví thiếu thì trừ ngân hàng, sổ tiết kiệm, sổ Mây, vàng, Mây Coin. Tắt kiểm tra ví/tài sản cũ. Chơi nhỏ (dưới 50k, lời hôm nay chưa quá 300k) không bị bắt hay dẹp chiếu. Ván từ 50k thắng tối đa 40% (cả trong Hai ngày vàng). Hoàn phần phạt dư 16:49–17:26 bằng quà hệ thống.

Chống gian lận: nhập bản lưu chỉ vào đúng bản đã xuất, so tổng tài sản (vàng, Mây, nhà, xe). Mây Coin từ 21:00 11/10 tính tin tức ngay đầu giờ. Tiệm áo chỉ tính đồ khách đặt, thưởng đồ nghề/giá/nước ngoài trên tiền lời, giá sỉ ×1,5. x3 không tính tiền hoàn đơn; mục tiêu ngày, thưởng quản lý, x3, giá nhà chỉ tính cho ngày có giờ thật (bản mới bắt đầu 48 ngày). Chơi lại từ đầu không sinh tiền; sổ nợ trà đá kiểm mọi dòng ghi khống. Kho báu hết hạn sau 3 đợt, 1 rương/đợt, 5 rương/ngày, tài khoản từ 1 ngày. Kéo co chó sủa giới hạn sức kéo khi hét liên tục, bảng tuần chỉ tính trận người–người đủ điều kiện, cược tối đa 200.000. Tiệc cưới: khách và lì xì từ tài khoản 1 ngày, khóa giới hạn 2 tiệc/ngày, tiệc đã hủy không trả. Nhà mua lúc tin xấu tính giá gốc trung tính; lịch tin nhà có muối máy chủ từ 03/11. Phạt thiết bị hỗ trợ tính cả sổ Mây, vàng, Mây Coin; phóng dao trả lúc nửa đêm cũng bị kiểm. Lãi ngân hàng không vượt trần số dư.

# v2.0.1 — 2026-10-11

Sửa kính theo vị trí mắt ở từng hướng/bước đi, mũ khi quay lưng, màu áo và mảnh ảnh thừa của nhân vật ngoài phố. Dùng đường cắt cổ thực tế cho bơi/chèo thuyền, chỉnh tư thế ngồi và chân trên thuyền.

Lên thuyền từ phần cầu gỗ đi được; bơi tự do có nút Lên bờ và phím Space tương ứng, quay lại thang trước khi lên. Không yêu cầu đi hết vòng mới được thoát hồ.

Giảm xử lý/vẽ avatar đứng yên và ngoài màn hình; đổi màu sprite trực tiếp trên bộ đệm, giữ nguyên kết quả từng pixel. Chẩn đoán tùy chọn đo thêm khoảng thời gian giữa khung hình.

Rương chưa nhặt được giữ lại qua các đợt và khởi động lại. Mỗi 10 phút vẫn thêm 3–5 rương; mỗi rương trả 10.000 xu một lần cho người nhặt hợp lệ. Rương trùng chỗ hiển thị thành cụm có số lượng, mở từng rương. Chỉ dọn biên nhận đã nhặt quá thời gian lưu vết; không xóa rương chưa nhặt. Schema 39 thêm chỉ mục cho truy vấn rương còn lại. Giữ nguyên thời hạn Hai ngày vàng và thông báo 2.0 đã phát.

Giao diện cũ có lối Ra đảo nhặt rương trên bản đồ và menu Khu phố, dùng chung đảo/người chơi/rương với 2.5D. Đóng đảo trả lại nơi làm việc và giữ lựa chọn giao diện cũ.

Giảm nhẹ khả năng bị công an bắt khi chơi Chợ Đen; giữ điều kiện áp dụng, tiền phạt và thời gian tạm giữ. Không đưa tỷ lệ vào giao diện công khai.

# v2.0.0 — 2026-10-11

Giao diện Phaser 2.5D cho khu phố và nơi làm nghề; 50 ngoại thất riêng, 50 bố cục nội thất, cây cối/tiện ích và biển hiệu theo công trình. Cải thiện camera, di chuyển, hoạt động ngoài trời và vòng đời tải tài nguyên; nhà ở/không gian trang trí 3D, avatar và phụ kiện dùng chung dữ liệu nhân vật.

Cài đặt có công tắc Giao diện mới, lưu theo tài khoản; mặc định bật và mời người chơi chọn giao diện cũ một lần. Giữ tiến độ và phiên đăng nhập khi chuyển chế độ. Góp ý cho phép tối đa 3 ảnh, kiểm tra và chuẩn hóa phía máy chủ, chỉ chủ góp ý/quản trị đọc được; không tự xóa ảnh theo tuổi góp ý.

Hai ngày vàng Chợ Đen: cửa sổ 48 giờ do quản trị kích hoạt sau kiểm tra deploy, tăng xác suất các lượt Chiếu trong, lô tô và vé cào. Không tự kích hoạt khi khởi động lại. Thông báo 2.0 qua công cụ quản trị riêng sau smoke check, không phát trong quá trình build hoặc trước deploy.

# v1.9.48 — 2026-10-10

Theo yêu cầu bổ sung: lấy số lời/lỗ Hội chợ hiện có làm mốc cho tuần đầu của Top lỗ. Chạy seed một lần theo từng lô, có con trỏ tiếp tục và khóa giao dịch để không cộng trùng; không đổi save/ví. Từ tuần kế tiếp vẫn chỉ tính phát sinh trong tuần. Giao diện giải thích tuần đầu có số liệu cũ; Có gì mới giữ nguyên.

# v1.9.47 — 2026-10-10

Hội chợ có Top lỗ riêng theo tuần, tiền thắng/kiếm trong tuần bù trừ tiền thua. Top 1 nhận 🥀 Vua đen đủi, Top 2–10 nhận ☔ Hội đen đủi mỗi thứ Hai, giữ danh hiệu vĩnh viễn, không thưởng xu. Bắt đầu ghi nhận từ bản cập nhật, không hồi tố tổng lỗ cũ. Schema 36 thêm bảng sổ tuần, ghi cùng giao dịch lưu game; giữ nguyên Top lời và Có gì mới.

# v1.9.46 — 2026-10-10

Theo chủ game: khôi phục tối thiểu 30 trận hợp lệ mỗi tuần trước khi xếp top tỷ lệ thắng và xét thưởng kéo co. Giữ giải thưởng và tie-break. Deploy âm thầm; giữ nguyên Có gì mới theo yêu cầu.

# v1.9.45 — 2026-10-10

Theo yêu cầu chủ game: top kéo co tuần xét tỷ lệ thắng của mọi người có trận hợp lệ, bỏ ngưỡng 30 trận. Giữ top 5, mức thưởng, danh hiệu, tie-break và quyền ẩn tên. Có gì mới gồm đúng bốn ý: sàn đấu giá đẹp hơn, vật dụng tăng khách/thu nhập, vào Chợ đen miễn phí, top kéo co giải nhất 2 triệu xu.

# v1.9.44 — 2026-10-10

Nâng cấp thu nhập theo nghề; tổng 30 tranh và top nhà sưu tầm; Chợ đen miễn phí và tăng nhẹ tỷ lệ thắng; giải kéo co micro theo tuần. Đã triển khai 10/10, xem docs/DEPLOY_1.9.44_2026-10-10.md.

# v1.9.43 — 2026-10-10

Lời đáp góp ý của admin tối đa 10.000 ký tự (trước 300), chủ game 10/10. 👴 Thắng Ông Hai: giữ tiền thắng, rồi công an bắt vì dùng thiết bị thứ ba: phạt 30–50 % ví + tài khoản (không nợ), tạm giữ 3 ngày (fair.py _hai_device, fair_hai.device_fine). Không có Có gì mới.

# v1.9.42 — 2026-10-10

Gồm dog-bark-fix: dây chỉ nhích khi có tiếng sủa thật (cả hai bên), cả hai im thì hòa; đo nền ồn, tắt khử vọng; chó nhà Mây sủa thành tiếng mỗi lần kéo. Không có Có gì mới.

## dog-bark-fix (không có Có gì mới)

🐕 Kéo co chó sủa: **phải sủa mới tính**, cả hai bên (chủ game 10/10 "chó sủa sao nhiều trận không thắng", "có trận tự thắng mà không cần sủa"). Lỗi cũ: chó nhà Mây kéo liên tục cả lúc không phát tiếng (tiếng chỉ phát khi lực ≥ 35, lực "sủa một mình" 22–34 nên dây trôi mà không nghe sủa); dây chạy hết nửa sân trong ~2 giây; mic bật khử tiếng vọng nên giọng người chơi bị dìm đúng lúc chó sủa; không trừ tiếng ồn nền nên phòng ồn tự kéo dây.
- Chó nhà Mây chỉ kéo **trong lúc sủa**: mỗi tiếng sủa server gửi `bark_dog` trước, trang phát tiếng chó thật đúng lúc đó (tắt tiếng 🔇 thì hiện bong bóng "GÂU!" to). Sức chó rút ngẫu nhiên mỗi trận, có nhịp (dồn dập, nghỉ, lấy hơi, mệt), không bám theo người chơi, không trôi.
- Người chơi chỉ kéo khi **sủa thật**: trang tự đo tiếng ồn nền trong giây đầu, gửi độ to vượt nền (nói chuyện ~30–50, hét ~70–90); server chỉ tính mẫu ≥ 30, tiếng đều đều (ù, số cố định) tính 0. Thanh đo có vạch "sủa qua vạch là kéo".
- Hai bên im: dây đứng yên, hết giờ là **hòa, trả cược**. Dây di chuyển chậm hơn: trận nhanh nhất 15 giây; im lặng thì thua chậm (≥ ~30 giây); hét bình thường ~50/50; hét to và liên tục thắng rõ.
- Mic: tắt khử tiếng vọng / lọc ồn / tự chỉnh âm lượng; trận chỉ bắt đầu khi mic thật sự có tiếng (`bark_ready`), không có thì sau 20 giây trả cược; iPhone chưa chạy âm thanh thì hiện "👆 Chạm để bật mic"; mic im bặt (toàn số 0) thì báo lý do, không đặt cược. Đang đấu với chó mà mic ngừng thì trận tạm dừng (quá 15 giây: chốt theo dây).
- Nhật ký: một dòng mỗi trận trong log live (`bark match …`): độ to trung bình/đỉnh, nền ồn, số tiếng sủa và lực chó, người thắng. Chỉ số, không có âm thanh.
Không đổi DDL, không khóa save mới, không đổi tiền/kèo. Kiểm tra: tests/test_dog_bark.py, tests/test_live_dog_bark.py, scripts/browser_dog_bark.py (mic giả: hét thắng, im lặng thua sau 45 giây).

# v1.9.41 — 2026-10-10

Gồm dog-bark (🐕 Kéo co chó sủa, bật bằng LIVE_DOG_BARK=1 cho cả mot-ngay-lam-nghe và mnl-live; schema 34: bark_tickets; kind thanh toán 'bark'), và sweeper không theo dấu tiền tài khoản admin.

## dog-bark (Có gì mới: 1 dòng, bản 1.9.41)

🐕 **Kéo co chó sủa** (chủ game 10/10): trò riêng ở Khu phố và trên Bản đồ phố (cạnh Phòng hát), không thuộc chợ đen (không công an chợ đen, không Lộc trời cho, không Bảng vàng). Đặt cược từ 100 xu tới mức ví trả được (giữ cược trước trận), bấm "Tìm đối thủ": ghép ngẫu nhiên người cùng mức cược, không bao giờ ghép hai máy cùng IP (băm có muối, chỉ trong bộ nhớ live), cùng hai người tối đa 3 trận liên tiếp (reset khi cả hai đấu người khác hoặc sau 2 giờ). Sau 20 giây không có ai thì tự đấu với **🐕 Chó nhà Mây · <tên>** (giống và tên ngẫu nhiên mỗi trận, ghi rõ là chó của game, không có hồ sơ người chơi). Sợi dây có cờ ở giữa, ai sủa to hơn (độ to từ mic, chỉ gửi con số, không gửi âm thanh) kéo cờ về phía mình; tới vạch là thắng, hết 45 giây dây lệch bên nào bên đó thắng, giữa là hòa. Thoát hoặc mất kết nối quá 10 giây là thua.
💰 Thắng ăn cả hai phần cược (hệ thống trả, phí 0 %); hòa trả cược; thắng chó nhà Mây nhận ×2, thua thì mất cược. Tiền về ví qua live_effects loại 'bark', mỗi vé trả đúng một lần (UPDATE có điều kiện + một dòng trả tiền, lật 'applied' trong giao dịch của save). Vé chờ quá 5 phút / kẹt trận quá 10 phút (live khởi động lại) tự hoàn cược.
🛡️ Luật riêng: cần tài khoản + năm sinh ≥ 16 tuổi (account_birth, hỏi một lần như Phòng hát), mỗi ngày tối đa 60 trận, 20 trận với chó nhà Mây và lời tối đa 5.000 xu từ chó (cược với chó vừa phần còn lại), thắng liền 4 kèo thì nghỉ 15 phút. Chó nhà Mây có lực ngẫu nhiên quanh độ to của chính người chơi (bùng, nghỉ, hồi sức), mô phỏng ~49–50 % thắng với người sủa thật, im lặng hay sủa lí nhí thì thua. Độ nhạy mic tự chỉnh ở máy. Tiếng chó thật (7 bản ghi CC0, public/audio/bark/), mỗi lần sủa một cao độ/độ dài/độ to khác.
👀 Người khác xem trận đang kéo và ném 👏🔥. 👑 "Vua sủa" tuần: người lời nhiều nhất tuần hiện ở sảnh (không cấp danh hiệu vào save để rollback an toàn).
Kỹ thuật: game/dog_bark.py, live/dog_bark.py, public/js/v4/dog-bark.js; công tắc LIVE_DOG_BARK (cả game server: header microphone=(self) và lệnh jr_bark_join; cả live). SCHEMA_VERSION 34: bảng bark_tickets (chỉ thêm). Không có khóa save mới. Bản 1.9.40 rollback: bỏ qua dòng 'bark' (đợi bản mới trả), scripts/dog_bark_rollback_check.py OK.

## chat-head (không có Có gì mới)

💬 Đầu khung nhắn riêng hết vỡ (chủ game 10/10 "UI lỗi nè"): tên không còn bị cắt nửa trên, danh hiệu không còn thành cột chip 1 chữ và "+N" không còn đè lên tin nhắn (đầu khung bị co lại khi cuộc trò chuyện dài; giờ giữ nguyên chiều cao). Tên một dòng, dưới là "Đang online" + 1 danh hiệu (2 khi khung ≥ 520 px) + "+N" ngay trong đầu khung, bấm mở hết; "Ghé chỗ làm", 🔔, "Chặn" xuống hàng riêng khi không đủ chỗ, ✕ luôn ở góc phải. Nhóm và Cả phố cũng không bị co.

# v1.9.40 — 2026-10-10

Gồm couple-race (khóa quỹ chung khi ly hôn/rút, hold thẻ chung chốt cùng save, quà tặng không cộng hai lần), mishap kiểu thug/police lấy quỹ tiệm + sweeper theo dấu tiền + bảng tài phú cập nhật, hoa hồng tiệm quần áo nước ngoài 40–50 %, thẻ nhập hàng gọn (kho-compact). Không có Có gì mới.

## couple-race (không có Có gì mới)

🏦 Quỹ chung không còn bị chi hai lần khi rút tiền đúng lúc ly hôn / xóa tài khoản: mọi thay đổi quỹ (gửi, rút, thẻ chung, hoàn tiền, chia khi chia tay) khóa theo cùng một thứ tự (dòng couples rồi dòng joint_funds), số dư lúc chia đọc dưới khóa; rút sau khi đã chia tay bị từ chối gọn "Hai bạn đã chia tay, quỹ chung đã được chia rồi." (trước đó có thể deadlock hoặc trả thêm tối đa 10 triệu xu).
💳 Thẻ chung: khoản giữ (held) được chốt 'done' ngay trong giao dịch ghi bản lưu của lệnh mua (couple.commit_holds trong storage._store/_command_locked, marriage._mutate, home_decor.command), nên 60 lần gửi 1 xu đẩy mã khỏi marriage.applied không còn làm hoàn tiền một căn nhà đã mua. Khoản giữ đã bị hoàn (void) thì lệnh mua bị từ chối 'expired', không bao giờ vừa có nhà vừa được hoàn. Điểm hạnh phúc (couple_stats) đọc-ghi dưới khóa dòng.
🎁 Phố nghề: tặng quà khóa theo người tặng (pg_advisory_xact_lock), hai lần bấm cùng lúc chỉ ra một món quà (trước đó người nhận được cộng xu hai lần). Không DDL, không khóa save mới.
## kho-compact (không có Có gì mới)

📦 Thẻ "Nhập …" trong Kho & nhập hàng gọn lại (chủ game 10/10 "dài quá, dài dòng quá"; mọi nghề có kho dùng chung thẻ này): 113–131 chữ còn 26–31, cao ~1.150 px còn ~560 px trên điện thoại 360 px. Số liệu thành biểu tượng (📦 16/80 · 55 xu/cái · ⏳ 20 ngày); hóa đơn một dòng "275 xu · sỉ −4% · nhận ~10:15" (tag ship chỉ khi mất phí); lý do không đặt được (thiếu quỹ, kệ đầy, đủ xe đang về) vẫn hiện chữ đỏ ngay dưới, nút Đặt ngay mờ kèm lý do + nút sửa ("Lấy 5"); nhà cung cấp thành hàng một dòng (Chợ đầu mối / Hạt Nắng / Hỏa tốc · giờ · ×giá); giờ giao & điều kiện từng nơi và đoạn "Trả tiền khi đặt…" vào nút "?" của thẻ; nút Thêm vào đơn / Đặt ngay nằm trong thanh dùng chung (.ui-bar). Điện thoại: đầu sheet kho chỉ hiện Quỹ tiệm (ví không trả tiền nhập hàng) để tiêu đề không bị cắt. Size quần áo thành chip một dòng; nhóm hàng quần áo có tên tiếng Việt (Áo, Quần & chân váy…). Chip số lượng bấm sau khi gõ số giờ đổi đúng số. `check_word_caps.py --kho` giữ thẻ ≤ 35 chữ ở 360 và 390 px.

# v1.9.39 — 2026-10-10

Gồm góp ý #303 (quay-fix: mở rộng quầy khi có tình huống chờ, tên quầy che từ không còn invalid_save), #307 (share-deco: journey.decor_stay tùy chọn), #304 (teacher-grades: lớp 2–5, ext.data.homeroom, task.grade_room tùy chọn), #306 (clothing-abroad: tasks abroad tùy chọn).

## hoa hồng tiệm quần áo ở nước ngoài

- Seoul 20→40 %, Osaka/Lyon 25→45 %, Melbourne 30→50 % doanh thu mỗi ngày (chủ game 10/10). Hợp đồng đang chạy giữ mức cũ (pct lưu lúc nhận).

## quay-fix (không có Có gì mới)

🏗️ Mở rộng quầy (#303): tình huống chủ tiệm và việc của nhân viên đang chờ không còn chặn mở rộng (chúng vẫn chờ nguyên); chỉ còn ca tự đứng quầy đang mở và tình huống chỉ xe đẩy mới có (kiểm tra chỗ đặt xe) chặn. Nút Mở rộng mờ kèm lý do ngay khi chưa làm được (quay.grow_busy, `grow[].why` chỉ là trường hiển thị).
🏪 Tên quầy có từ bị che (••• dài hơn từ 2 chữ) hoặc ký tự điều khiển ở cuối không còn bị từ chối với lỗi "Dữ liệu quầy trong bản lưu không hợp lệ": tên được cắt lại 24 ký tự và bỏ khoảng trắng hai đầu. Khi kiểm tra quầy từ chối một bản lưu, log server ghi một dòng `[quay-invalid] <tệp>:<dòng>` (không có dữ liệu người chơi).
## teacher-grades (F#304, Có gì mới 1.9.38)

🏫 Giáo viên lớp 2–5 (game/teach_grades.py): mở theo cấp nghề (lớp 2 cấp 2, lớp 3 cấp 4, lớp 4 cấp 6, lớp 5 cấp 8). Cô Hiệu trưởng mời nhận lớp ở đầu tiết (Nhận / Ở lại), đổi lớp trong Kế hoạch lớp (1 lần/ngày). Mỗi lớp 8 bài theo GDPT 2018 (Toán, Tiếng Việt, TN&XH / Khoa học / LS&ĐL) có câu hỏi giơ tay; khoảng 2/3 tiết có một tin nhắn khó chịu (Zalo 22 giờ, quỹ lớp, dạy thêm, xin đề, sửa học bạ, nộp giáo án mẫu mới…), trả lời sai thành phản ánh của phụ huynh. Mỗi lớp trên lớp 1 +5 xu/tiết. Lớp 1 và mọi công việc sinh ra không đổi (task-compat OK). Khóa mới tùy chọn: ext.data.homeroom {g, seen, day} của nghề giáo viên, task.grade_room (tiết lớp 2–5; bản 1.9.37 bỏ qua, coi tiết là chưa bắt đầu).
## clothing-abroad (góp ý #306)

👗 Shop quần áo đi nước ngoài (game/clothing_abroad.py): ở 🌏 Đi làm nước ngoài có thêm Tiệm Áo Chỉ Mây ở Seoul, Osaka, Lyon, Melbourne (phục vụ đủ 12 khách ở nhà, Chị Vy bao vé, 4–6 ngày, hoa hồng 20–30% doanh thu quầy mỗi ngày có khách vào quỹ tiệm; các nơi làm khác tạm nghỉ như hợp đồng làm thuê). Vẫn là game tiệm áo cũ, khách là người địa phương: tên, lời chào, size kiểu Hàn (55/66, 90/95, tuổi Hàn), Nhật (7号/9号, M/L/LL/3L, cm), Pháp (EU 36/46), Úc (AU 8, vòng ngực inch) với 📏 bảng quy đổi ở quầy; 22 thói quen khó chiều (xin “service”, khăn che mặt phòng thử, miễn thuế, “Bonjour” trước, túi giấy, UPF, “change of mind”…) phải trả lời trước khi chốt bill, câu “tùy tính khách” do tính ẩn quyết định, trả lời sai là lỗi như mọi lỗi khác. Sinh việc không đổi (check_task_compat OK với 1.9.37). Khóa save mới tùy chọn: task tiệm áo `abroad` {to, ask, ans, ok}; hợp đồng journey.abroad.work với career 'clothing', emp None, fee 0 (bản 1.9.37 thấy không có việc làm thuê nên kết thúc hợp đồng, không mất xu).

# v1.9.38 — 2026-10-09

Gồm exploit-fixes (nhập bản lưu, reset nơi làm, phóng dao, kế toán × x3, bỏ ngày ăn lương/tiền thuê, ném vòng, giới hạn chuyển tiền tài khoản mới), ong-hai-hard (journey.fair_hai), hot-career (lãi nhân viên theo thị trường + nghề hot), mishap: kiểu police, bán coin. Khóa mới tùy chọn: journey.fair_day, journey.fair_hai.

## share-deco (góp ý #307: ở chung, ở trọ cũng tự trang trí)

🏡 Người ở chung (lời mời "Ở chung") bấm 🪴 Dọn đồ sang ở là bày nhà bạn như nhà mình: tự mua, đặt, dời, xoay, bán, sơn tường/sàn bằng túi và ví của mình (khóa tùy chọn journey.decor_stay, chỗ ở deco 'stay'; tường/sàn chỉ hiện ở góc nhìn của người ở chung). Chủ nhà, vợ/chồng và người ở chung thấy đồ của nhau (chỉ xem, không ai bán/dời đồ người khác). Rời nhà, bị thu hồi, hết là bạn hay chủ nhà dọn đi: đồ về túi, cách bày giữ trong decor_away. Ở trọ/thuê nhà người chơi: vẫn tự bày như cũ, ghi chú rõ hơn. Sửa: về lại chỗ cũ thì món đã xoay vẫn xoay. 1.9.37 đọc được (bỏ qua khóa mới, đồ về túi; quay lại bản này thì bày lại như trước).
Có gì mới (gợi ý cho bản phát hành): 🏡 Ở chung nhà bạn hay ở trọ đều tự mua, bày, bán đồ của mình như nhà mình. Ở chung: Mời bạn → 🪴 Dọn đồ sang ở.

## exploit-fixes (không có Có gì mới, deploy lặng lẽ)

💾 Nhập bản lưu (game/save_guard.py): save của tài khoản không nhập được nữa (chỉ admin khôi phục); khách chỉ nhập bản xuất nguyên vẹn của máy chủ (chữ ký HMAC `sign` trong tệp, khóa SAVE_SIGN_SECRET, thiếu thì lấy từ DATABASE_URL), không cũ hơn và không nhiều xu hơn save hiện tại. Mỗi lần nhập một dòng `[import]` trong log. Nút Nhập bản lưu tắt cho tài khoản.
🔁 Bắt đầu lại nghề (hành trình): quỹ nơi làm việc giữ nguyên, tối đa 320 xu (không còn nạp lại 320 để rút tiếp). reset_career được tính vào KPI kinh tế.
🗡️ Phóng dao (không thông báo): lượt ném tới máy chủ trễ hơn 2 s so với cú ném cuối thì không nhận (màn chơi tiếp); lãi ròng tối đa 20.000 xu mỗi ngày VN (journey.fair_day, tùy chọn).
💼 Ngày 🔥 x3 không còn nhân thêm phần ×3/×5 của lương kế toán (job note `boost`, trừ khỏi lãi ngày như tăng ca).
⏱️ Ngày sống vượt hạn mức giờ thật (interest_clock: 1 giờ = 1 ngày, tối đa 168): không lương, không thưởng phòng điều hành, không tiền thuê nhà (chia theo ngày trong tháng), không khách xem tin cho thuê. Thưởng phòng điều hành cần ít nhất 1 việc xong. Tin cho thuê NPC mới tối đa 1,5× giá tham khảo (người đang thuê giữ giá).
💍 Ném vòng (không thông báo): trả tối đa 400 xu mỗi ngày VN (journey.fair_day.ring).
💸 Tài khoản dưới 7 ngày thật: thuê nhà người chơi, phong bì cưới, gửi tiền cho vợ/chồng và gửi vào quỹ chung cùng tính vào hạn mức 500.000 xu/ngày như chuyển khoản (bank_xfer.count_out, chung bảng bank_xfer_days).

# v1.9.37 — 2026-10-09

- 🔐 Sự cố tài chính theo lịch (game/mishap.py, live_effects kind `mishap`, scripts/mishap_plan.py): bản cũ bỏ qua loại này (để pending). on_load chỉ trả hàng có `at` đã tới.
- journey.iclock thêm `s` (ngày bắt đầu tính theo giờ thật).

Gồm bank-exploit phần 1: lãi theo giờ thật (1 giờ = 1 ngày lãi, tối đa 168; journey.iclock tùy chọn), tái tục tối đa 10M gốc, tài khoản dưới 7 ngày thật chuyển tối đa 500k/ngày, log [day-skip]. Không có Có gì mới.

## bank-exploit (phần 1: lãi theo giờ thật)

⏱️ Lãi chạy theo giờ thật (chủ game 09/10, lỗ hổng bỏ trống ngày để ăn lãi): 1 giờ đời thực = 1 ngày tính lãi, tích tối đa 168 ngày (game/interest_clock.py). Ngày kết thúc vượt hạn mức vẫn trôi (hóa đơn, nợ, thẻ chạy như cũ) nhưng không có lãi: sổ không kỳ hạn, sổ có kỳ hạn (trừ ngày đó khỏi kỳ, cả khi tất toán sớm) và sổ tiết kiệm Đầu tư. Mây Coin không đổi. Khóa save mới tùy chọn journey.iclock; con trỏ ngày của ngân hàng/đầu tư vẫn chạy như cũ nên rollback về 1.9.36 không trả bù.
🔁 Tái tục: gốc gửi tiếp tối đa 10.000.000 xu (bank.RENEW_MAX), lãi và phần gốc vượt về tài khoản thanh toán (hết lãi kép vô hạn).
💸 Tài khoản dưới 7 ngày đời thực chuyển khoản tối đa 500.000 xu mỗi ngày (bank_xfer.NEW_DAY_MAX).
🚨 Save kết thúc hơn 150 ngày trong một ngày đời thực: một dòng "[day-skip]" trong log server.
## 👴 Ông Hai khó hơn, công an ở bàn Ông Hai (chủ game 09/10; ghi chú nội bộ, không đưa vào "Có gì mới")

👴 Nguyên nhân: Ông Hai 1.9.36 tìm theo số nước cố định nên cùng bàn luôn đi cùng nước; uid 5952/5226 chỉ lặp 2 đường đi 39 nước (mỗi cách Ông mở một đường), thắng 502/532. Giờ: mở ô giữa (9, hai chiều), mỗi nước bốc thăm trong các nước gần bằng nước tốt nhất (KHO_SPREAD), tìm nhanh gấp đôi mỗi nước (vị trí phẳng, _sow), tối đa KHO_NODES 4000 nước mô phỏng và KHO_MS 35 ms: ~30 ms/nước trên server (trước ~350 ms).
🚨 Bàn Ông Hai (game/fair_hai.py): thắng 2 ván liền, hoặc 3 ván trong 24 giờ → công an ập vào: thu lại tiền thắng của các ván đó (ví trước, rồi tài khoản ngân hàng, không bao giờ âm), rồi bắt như chợ đen (phạt 30% ví còn lại, trại tạm giữ). Tối đa 30 ván với Ông Hai một ngày. Save mới tùy chọn journey.fair_hai {d, n, s, w}; 1.9.36 giữ nguyên và không đọc. Đột kích 30% ví, kiểm tra tài sản 10%, Lộc trời cho không đổi.
## 📈 Lãi nhân viên theo thị trường + 🔥 Nghề hot hôm nay (chủ game 09/10)

- Chỉ đơn riêng của nhân viên (game/workplace_business.py `_finish`) đổi; người chơi tự bán, đơn khách người chơi
  (player_service_tasks) và Bảng giá giữ nguyên. Mới: game/staff_market.py, public/js/market-ui.js.
- Lãi mỗi đơn tính trên giá vốn nhập lại (`_replacement`, hoặc giá lô nếu cao hơn): giữ nguyên tới 16 xu, phần trên giữ 1/4,
  tối đa 24 xu (theo sao). Đồ si nhân viên trước ~142 xu/đơn (≈ 53.600 xu/giờ với 4 người, 17× việc văn phòng) nay ~32
  (≈ 12.300/giờ); mẹ & bé, kem, cơm, cà phê… giảm nhẹ; nghề lãi thấp không đổi.
- Hệ số thị trường mỗi nghề ×0,6–×1,6, đổi mỗi 30 phút (tổng 3 sóng sin, pha theo tên nghề), mỗi bước ≤ 10%, trung bình ≈ ×1.
  🔥 Mỗi ngày (giờ VN) một nghề hot: ×2 hệ số, giữ trong ×2–×2,5; xoay hết 50 nghề mới lặp, không trùng hai ngày liền.
  Tính theo giờ hoàn thành đơn, nên đơn bù lúc vắng và đơn từng lượt ra cùng số. MNL_MARKET_OFF=1 tắt (tests mặc định tắt).
- Hiện ở: thẻ nơi làm (🔥 Nghề hot ×2 / 📈 Lãi cao ×1,3 / 📉 Lãi thấp ×0,8), 🏆 Xếp hạng nghề (chip nghề hot có 🔥, dòng lãi
  nhân viên), Sổ tiệm → Nhân viên (dòng "🔥 Hôm nay lãi cao ×2" / "📈 Lãi đang cao ×1,3 ↑" + đường 48 giờ), Lúc bạn vắng
  ("lãi … xu (×1,3)"). public_state['market'] và business.market chỉ là dữ liệu xem.
- Không có khóa lưu mới, không đổi CSDL; biên nhận giữ đúng dạng cũ nên 1.9.36 đọc được save.
- Có gì mới (cho bản phát hành): 📈 Lãi đơn nhân viên giờ lên xuống theo giờ, mỗi nghề một kiểu; mỗi ngày có 1 🔥 nghề hot lãi ×2. Xem ở Công việc, Sổ tiệm.

# v1.9.36 — 2026-10-09

🎆 Pháo hoa (#299–#301): show gắn vào hộp thoại trên cùng nên ✕ không còn lọt xuống nền làm đóng việc đang làm; đang mở hộp thoại/game thì chỉ chip nhỏ; Cài đặt → Cách chơi: Bật / Chỉ báo nhỏ / Tắt (lưu trên máy); ngắn và nhẹ hơn.
🏪 Quầy (#295/#296): Nhập lại như lần trước (quay.again), thiếu thì lấy từ ví (dòng Sổ ví ≤ 10^7), mở rộng xe → sạp → ki-ốt tại chỗ (jr_quay_upgrade), Quản lý chung theo loại với nút cho cả nhóm. Save mở được trên 1.9.34/1.9.35.
✏️ Sửa góp ý chưa trả lời (POST /api/feedback/edit); 🏆 Xếp hạng nghề trong trang Công việc (#294).

# v1.9.35 — 2026-10-09

🗺️ Trại tạm giữ có bản đồ đi lại (public/js/scenes/jail-place.js, jail-map.js): mỗi việc công ích một góc, giường hết ngày, phòng thăm gặp nhờ bảo lãnh, cổng đếm ngược; NPC chỉ ở client.
🔒 Bị giữ chỉ được ở trại, nhắn tin, làm công ích (chủ game 09/10): allowlist lệnh (jail.OPEN_COMMANDS), route HTTP (OPEN_ROUTES), frame live (chỉ chat); việc người khác làm cho mình vẫn vào. Live biết ai đang bị giữ qua bảng nhỏ jail_marks (SCHEMA_VERSION 33), không đọc save.
⏳ Một ngày trong trại ≥ 20 phút, 8 việc từ 14 loại (9 việc mới), mỗi việc ≥ 45 giây; đủ 8 việc ngày tính 2. Trạng thái mới ở journey.jail2; journey.jail giữ dạng cũ nên save mở được trên 1.9.32–1.9.34; ngày bắt đầu trên server cũ giữ luật cũ.

# v1.9.34 — 2026-10-09

🚨 Chợ đen: tỷ lệ bị bắt một ván tối đa 30% (fair_bm.ARREST_CAP, trước 70%; chủ game 09/10). Từ 290.000 xu (lời trên 300k) hoặc 340.000 xu cược là chạm trần. Không đổi save.

# v1.9.33 — 2026-10-09

🎁 Quà admin trên 10.000.000 xu: trước đây kẹt ở trạng thái chờ (mỗi dòng Sổ ví tối đa 10^7, journey.validate); giờ chia thành nhiều dòng ≤ 10.000.000 (system_gift.ROW_MAX). Quà làm ví vượt 10^9 thì chờ, không trừ gì. Quà 50.000.000 xu đang chờ sẽ vào ví ở lần tải tiếp theo.

# v1.9.32 — 2026-10-09

🐕 Đua chó (chủ game 09/10): sạp cược mới ở Chợ đen (game/fair_dog.py, fair-dog.js), mỗi 2 phút một lượt 6 chó, trả thưởng cố định theo hạng (tối đa 95%), chỉ xem và cổ vũ; luật bảo kê/công an/tạm giữ như các sạp khác. Không lưu gì mới.
🚨 Cược lớn: ván từ 50.000 xu có thể bị bắt (1% + 1% mỗi 10.000, cộng 5% khi lời trên 300.000 trong ngày, trần 70%) — fair_bm.arrest_p.
🗡️ Phóng dao, ô ăn quan là trò kỹ năng: không bắt ngẫu nhiên, chỉ bắt khi nghi gian lận/spam (game/fair_watch.py); bỏ trần ngầm 300 xu/ngày của phóng dao; cược tối đa 1.000 xu; dao quay nhanh dần (+10%/màn, tối thiểu +5%) và quay tới lui có báo trước (fair_knife.twist_schedule); Ông Hai vẫn thưởng 10.000 xu. Save đọc được trên 1.9.30/1.9.31.

# v1.9.31 — 2026-10-09

🚔 Trại tạm giữ (chủ game 09/10): game/jail.py, journey.jail; bắt ở chợ đen chỉ khi lời chợ đen hôm nay > 300.000 xu, 5%/ván (fair_bm.ARREST_FROM, BM_ARREST_P): mất cược + phạt 30% ví + 3 ngày; tố cáo sai 25% → 1 ngày; công ích 3 việc/ngày (đủ 3: ngày tính 2); bảo lãnh bởi bạn bè, bạn trả 30.000 xu; tự thả sau ngày án × 24h; MNL_JAIL_OFF=1 tắt.
🌙 Chợ đen mở mãi (FAIR_DAYS 0, cùng đợt fair20261009), trao danh hiệu 0h thứ Hai hằng tuần, vay nóng không thu khi đóng.
🏰 Biệt thự (estates) mời ghé thăm / ở chung / trang trí giúp được (home_guests, home_coop, live/home.py). Không đổi CSDL; save đọc được trên 1.9.29.

# v1.9.30 — 2026-10-09

📦 Bước 2 nâng kho (#277, chủ game 09/10 "ok nâng đi"): sức chứa mỗi món tối thiểu 80 (com giữ 120), dòng đơn tới 80 (server gửi line_cap), thùng >20 xếp khay 10 với nút Đếm khay; save của bản này không đọc được trên 1.9.28 nên chỉ quay về 1.9.29.
✅ Nút Tất cả (#290): lắp hết thiết bị quầy (rẻ trước, trong số tiền có), thuê đủ chỗ quầy, cả đội vào/nghỉ ca (public/js/v4/select-all.js; dùng lệnh sẵn có, không đổi server).
🚔 Công an sửa sao thì thẻ "lần ghé gần đây" ở chăm sóc khách cũng cập nhật. Không đổi CSDL.

# v1.9.29 — 2026-10-09

🚨 Chợ đen bỏ cấm (chủ game 09/10: "bỏ cấm hội chợ luôn nhe"): bị bắt vẫn mất tiền cược và nộp phạt nhưng chơi tiếp được; 'ban' đã lưu hôm nay (1.9.28) đọc như đã nộp bảo kê.
📦 Hủy đơn hàng đang giao hoàn 80% (làm tròn xuống) tiền hàng + ship (chủ game 09/10).
🧰 Bước 1 nâng kho (#277): save chấp nhận tồn tới 80/món (hoặc sức chứa cao hơn của nghề), dòng đơn/nháp tới 80, hàng hủy lớn hơn; giới hạn thật vẫn như cũ (bước 2 ở bản sau). Không đổi CSDL; save đọc được trên 1.9.28.

# v1.9.28 — 2026-10-09

🚔 Báo công an đánh giá NPC vô lý (chủ game 09/10): game/review_police.py, lệnh fb_cop; sao hiện thấp hơn điểm thật (fb.fair) thì công an xác minh (ẩn tỷ lệ), sửa sao và đôi khi bồi thường ≤100 xu; 3 lần/ngày, 1 lần/đánh giá, 3 ngày gần nhất.
🕶️ Bảo kê chợ đen hên xui 40% mỗi 2 ngày (fair_bm.asked, cố định theo seed + đợt 2 ngày; không lưu, không hiện).
👛 Rút quỹ: nút một chạm rút tối đa + ✏️ Rút số khác gõ số (góp ý #285/#287), Góp vốn bên cạnh.
📦 Hủy đơn hàng đang giao, hoàn đủ (inv_cancel, góp ý #276); tiệm album có nút đếm lại tiền khách đưa (#288); gợi ý xin bớt đơn gộp (#284).
🔧 Ở chung nhà lên được tầng 2 (#280, reno.js VISIT_OPS); dỗ bé không còn kẹt dưới 100% (#282/#283); nhà thuốc nhãn K / ❄️ Lạnh (#278). Không đổi CSDL; save đọc được trên 1.9.27.

# v1.9.27 — 2026-10-09

🕶️ Chợ đen (chủ game 08/10 23:15: "k phải là hội chợ, nó là Chợ đen. Vào chợ đen phải nộp bảo kê, phí bảo kê là 10k xu, nếu k nộp thì bị trấn lột 30% tiền hiện có. vào chợ đen có thể bị công an bắt, tỷ lệ bị bắt cực cao"): đổi tên hiển thị Hội chợ → Chợ đen; cổng bảo kê 10.000 xu mỗi ngày (giờ VN), không nộp bị trấn lột 30% ví (không đụng ngân hàng) rồi được vào; mỗi ván có đặt tiền có thể bị công an ập vào (game/fair_bm.py BM_ARREST_P, không hiện ra): mất tiền cược, phạt 30% ví, bị đuổi tới hết ngày. Trạng thái lưu ở journey.fair_bm (bản 1.9.26 vẫn đọc được). Không đổi CSDL.

# v1.9.26 — 2026-10-08

🏮 Hội chợ mở lại 09/10–13/10 (chủ game 08/10: "mở hội chợ nhé, tỷ lệ chỉnh lại làm sao cho phù hợp, đảm bảo nhà cái luôn thắng"; "chợ đen để luôn ở ngoài"; "số liệu k hiển thị ra, mn đặt cược bao nhiêu thoải mái"): FAIR_START 2026-10-09, 5 ngày; mọi trò trả tiền đều có lợi thế nhà cái (docs/FAIR_HOUSE_EDGE.md, scripts/sim_fair_odds.py); lô tô cược phụ đóng; phóng dao giới hạn lời mỗi ngày không báo ra; bầu cua / chiếu trong gõ số cược tùy ý (trần ẩn 1.000.000 xu/ván); không gửi tỷ lệ thắng cho trang; lối vào 🏮 Hội chợ ngay trên khu phố (town-walk.js). Không đổi CSDL.

# v1.9.25 — 2026-10-08

👛 Người chơi góp ý 08/10 ("rút về ví cồng kềnh quá … trở lại như cũ, cho góp vốn bên cạnh chỗ rút thôi"): quỹ nơi làm việc lại có nút một chạm "👛 Rút về ví · tối đa X xu" (rút mức tối đa rồi xác nhận, như trước 1.9.20); "📈 Góp vốn" ngay bên cạnh, bấm mới mở ô gõ số xu (public/js/v4/wealth.js, journey.js, money.css; cẩm nang sửa theo). Không đổi save, không đổi CSDL.

# v1.9.24 — 2026-10-08

🎵 Nhạc "lúc nghe được lúc không" (chủ game 08/10): iPhone iOS 15–16.3 không có navigator.audioSession nên công tắc im lặng tắt Web Audio → thêm thẻ <audio> im lặng (WAV blob:) khi nhạc bật; tự chạy lại AudioContext khi statechange/pageshow/focus/devicechange và kiểm tra 2,5 s; nhạc tải hỏng thử lại 2/5/15/30/60 s, tải treo 20 s thì huỷ; bộ giải mã 32 kHz hỏng thì dùng context của trang; sửa A→B→A phát nhầm bài; chạm đầu khi module chưa tải vẫn được nghe lại (public/js/audio.js, v4/music.js, shell.js). Không đổi save, không đổi CSDL.

# v1.9.23 — 2026-10-08

💌 Thiệp mời cưới cả phố (chủ game 08/10): cặp đã đính hôn/kết hôn viết lời mời (10–200 ký tự, qua bộ lọc chat), 10.000 xu mỗi thiệp (ví trước, rồi ngân hàng/thẻ); mọi người thấy một lần (popup như Có gì mới), tối đa 3 thiệp/người/ngày; 1 thiệp/tiệc, 1 thiệp/24 giờ mỗi người gửi; tôn trọng chặn; admin xem/gỡ thiệp; MNL_WED_INVITE_OFF=1 tắt. CSDL: SCHEMA_VERSION 32 (wed_invites, wed_invite_seen — chỉ thêm bảng). Không thêm khóa save.

# v1.9.22 — 2026-10-08

🎆 Pháo hoa không phải đợi (chủ game 08/10 "pháo hoa bắn k cần đợi"): gap 600 → 0 giây (game/lux_content.py), trang xếp hàng tối đa 6 màn pháo hoa (public/js/v4/fireworks.js). Không đổi save, không đổi CSDL.

# v1.9.21 — 2026-10-08

Góp ý #273–#275 và chủ game 08/10: 🎆 pháo hoa bắn thật cho cả server + băng thông báo dài (live/fireworks.py, public/js/v4/fireworks.js; lối vào Khu phố → Bắn pháo hoa); 💊 nhà thuốc hiện "Hôm nay: ngày N ở quầy", hạn dùng còn mấy ngày, Rút hết hộp quá hạn, phạt kệ quá hạn tối đa 2 điểm/ngày; 🛡️ bảo hiểm Gói trọn 100% giá ×2 và Bảo hiểm điện nước (game/rui.py: rui.full, rui.pol2, rui.dn tùy chọn, server 1.9.20 vẫn nhận); /admin 🎁 Tặng xu không giới hạn ngoài trần ví 10^9. Không đổi CSDL.

# v1.9.20 — 2026-10-08

Gom một bản các việc từ góp ý người chơi #248–#271 (chủ game 08/10): cấp bậc công an và cảnh cáo (#251 #253 #258), hạn kế toán doanh nghiệp (#265 #269), thi chứng chỉ ra ngoài (#267) và báo chợ ế cả phố (#263 #264), món đào và góp/rút vốn gõ số (#248 #259), học lịch sử Việt Nam (#255), ô nhập số (#250 #260 #262), phòng hát khớp giọng + 🎤 Hát cùng, thang lương theo chức + du học + làm ở nước ngoài (#249 #254; không có lương x5), biệt thự vào được (#270 #271), cho bạn trang trí + chuyện nhà thuê (#257 #261), bé ở nhà + bế bé đi chơi (#252). CSDL: SCHEMA_VERSION 31 (home_deco_grants, home_deco_log). Nhân viên tự nhập kho: không làm (chủ game).

# v1.9.19 — 2026-10-07

Gồm kara-sync (người nghe theo video của người hát trừ độ trễ giọng; `kara_vt` qua live, không khóa lưu) và typed-qty (gõ số trong mọi ô − N +, `public/js/qty-input.js`).

## 🎙️ Giọng và nhạc khớp nhau (mic trực tiếp "bị delay xíu")

- Người hát hát theo video của chính họ, giọng tới người nghe trễ hơn (thu, mã hoá, SFU qua TCP, bộ đệm). Nay khi mic bật, máy người hát gửi thời điểm video của mình khoảng mỗi giây (`kara_vt`: thời điểm, tốc độ phát đang chỉnh, vòng mạng; qua máy chủ live, không qua SFU); máy chủ chỉ nhận từ người đang hát có mic, số hợp lệ, tối đa 1 lần/0,6 giây, đóng dấu giờ rồi chuyển cho người đang nghe giọng trong phòng (tôn trọng chặn). Người nghe đang nghe giọng thì video chạy theo video người hát trừ độ trễ của giọng (bộ đệm jitter đo bằng getStats + nửa vòng mạng hai bên + 40 ms; 0–1,5 giây), chỉnh nhẹ tốc độ khi lệch quá 0,12 giây, tua tối đa 2 lần một bài khi lệch quá 0,6 giây. Không có `kara_vt` mới (dưới 3 giây) hoặc không nghe giọng: theo đồng hồ chung như cũ. Người hát đồng bộ như cũ. Đồng hồ chung của phòng đo thêm một lần mỗi 15 giây (giữ lần có vòng ngắn nhất): 5 lần đo lúc vào phòng có thể rơi đúng lúc máy đang bận tải, mà người nghe giờ so đồng hồ của hai máy.
- Mỗi bài, mỗi người nghe gửi một dòng vào beacon lỗi: "kara_mic sync jb=… rtt=… up=… lag=… off=…" (máy chủ che chữ số nên mỗi số là một chữ cái: a 0–99 ms, b 100–199 ms … p ≥ 1,5 giây; `novt` khi không nhận được thời điểm của người hát).
- Quay lại bản cũ an toàn: trang cũ bỏ qua `kara_vt`; máy chủ live cũ trả 'unknown' thì trang mới thôi gửi và không báo lỗi. Không thêm khoá lưu, không đổi CSDL.
## Gõ số thay vì bấm + (chủ game 07/10: "cho nhập số nhé")

- Con số giữa − và + giờ là ô gõ được (`public/js/qty-input.js` `qtyBox`, docs/UI_KIT.md "Typed quantity"): bàn phím số,
  chạm vào là chọn cả số, chỉ nhận chữ số (dán "1.000" = 1000), Enter hoặc rời ô thì kẹp vào khoảng cho phép (trống/0 = mức
  thấp nhất), tổng tiền đổi theo như khi bấm. Nút − / + và các chip (5, 10, "Đầy kệ"…) vẫn còn. Chữ ≥ 16px (iPhone không zoom).
- Có ở: Kho nhập hàng (số lượng, đơn gộp, đếm nhận thùng, 🔒 Giữ cho ca bạn), Kho & sổ quầy (nhà thuốc, mẹ & bé), vàng (Đầu tư
  và Tiệm vàng), sổ tiết kiệm/Mây Coin (số xu khác ngoài chip), quầy (lương, bàn ghế, nhập thêm, góp vốn, giữ hàng), tiệc
  (số khách, theo bước 5), số bàn cưới, đấu giá (trả giá tùy ý, không dưới mức tối thiểu), ô tiền của street kit (mọi nghề
  dùng `amountBox`, đòi nợ), dầu, pet shop (cá theo bể, đóng hàng), trà sữa (đặt hàng), tạp hóa (tem giá, số lượng nhập),
  pet care (gram/bữa), thương lượng "Nhận n/…" (đường sắt, hải đăng, tổ bay).
- Máy chủ không đổi: mọi lệnh các ô này gửi đã từ chối số ngoài khoảng, số lẻ, chữ và true/false (tests/test_typed_qty.py).
  Lương quầy phía máy khách nay tối đa 10.000 xu như máy chủ (trước 1.000.000, máy chủ từ chối).
- Không có khóa lưu mới.
- Có gì mới (cho bản phát hành): 🔢 Khỏi bấm + mỏi tay: số lượng nhập hàng, vàng, lương, số khách… giờ chạm vào là gõ số được luôn

# v1.9.18 — 2026-10-07

Gồm "🔒 Giữ lại cho ca của tôi" (ops.business_keep, business.keep tùy chọn) và sửa sự cố đồ trang trí 07/10:

- Biệt thự Sông Hồng: từ 1.9.11 bếp và phòng ngủ 2 mất một hàng, cửa sổ / quầy bếp mới đè lên ô cũ, nên khi đổi khóa `:v2` 139 món của 16 người chơi vào túi đồ và lưới cũ làm vài món bị nắn lệch. Nay mỗi phòng cũ là tập cha của phòng cũ (estates.superset), `_v2_alias` giữ nguyên từng vị trí; món chỉ phòng mới chứa nằm ở `journey.decor_wide` (tùy chọn, 1.9.17 bỏ qua: hiện trong túi).
- Món mà 1.9.11..1.9.17 đặt trên ô thứ 7 của quầy bếp Sông Hồng (quầy nay 6 ô như nhà cũ) vào túi đồ khi tải (`deco._v2_fit`); trước đó validate từ chối cả bản lưu (5 bản lưu thật, bắt được ở bước kiểm tra trước deploy).
- Chuyển chỗ ở: bố cục chỗ cũ được nhớ trong `journey.decor_away` (3 chỗ gần nhất, tùy chọn), quay về là bày lại; món đã bán thì thôi.

## 🔒 Giữ lại cho ca của tôi (B4 phần 2, góp ý #243, #247)

- Kho: chạm một món, dòng "🔒 Giữ cho ca bạn − N +" đặt số tối thiểu (0–999) nhân viên không bán; ô hàng hiện "🔒 N". Nhân viên (và khách người chơi họ phục vụ) dừng món đó khi kho còn đúng N, lý do ghi "🔒 Giữ 5 ly giấy cho ca của bạn."; việc của chủ vẫn dùng hết. Thực đơn nhân viên, trọng số món và cỡ áo đều tính phần giữ (quần áo: bán từ cỡ còn nhiều nhất để phần giữ còn đủ cỡ). Quầy: cùng ô ở tab 📦 Hàng. Thẻ "Lúc bạn vắng" thêm dòng "🔒 Giữ lại 5 ly giấy cho bạn". Khóa tùy chọn `ops.business_keep` / `business.keep` của quầy ({món: 1..999}); không đặt thì như cũ, 1.9.17 nhận và giữ nguyên khóa. Không đổi cách sinh việc.

# v1.9.17 — 2026-10-07

Gồm r6-misc: thẻ "Lúc bạn vắng" (ops.business_used tùy chọn), ném vòng cách nhau 2 giây, dòng chữ đấu giá và danh hiệu.

## Mic trực tiếp: người nghe nối được và thấy trạng thái (B3)

- SDK LiveKit tải từ chính máy chủ game (`public/js/vendor/livekit-client-2.22.3.umd.js`, cùng SRI), jsDelivr chỉ còn là dự phòng; mỗi nguồn chờ tối đa 15 giây. Người nghe tải SDK trước rồi mới xin vé, nên mạng chậm không làm hết hạn vé 60 giây. Bản phát hành không nén lại thư mục `vendor/`.
- Người nghe thấy "🎧 Đang nối giọng…", rồi thanh âm lượng (hoặc "🔈 Chạm để nghe giọng" trên iPhone; chạm bất kỳ đâu trong phòng hát cũng được), hoặc "Chưa nghe được giọng · Thử lại" sau 2 lần tự thử lại. Người hát thấy "🎙️ Đang nối mic…", hoặc "Chưa phát được giọng · Thử lại".
- Ghi bước dừng vào beacon lỗi (`stat_client_errors`, kind toast, "kara_mic listen|sing <bước>: <mã>"): mod → sdk → token → signal → ice → track → audio (người hát có thêm perm), cả khi người nghe bỏ đi lúc còn chờ hơn 8 giây. Mic tắt vì phòng SFU bị xoá không còn báo nhầm "Mic đã ngắt kết nối".
## r6-misc (B4 báo cáo lúc vắng, B5 ném vòng, WP-5 chữ)

- 🧾 Lúc bạn vắng (B4, góp ý #243, #247): quay lại nơi làm hay quầy sau ít nhất 5 phút, nếu nhân viên đã bán thì hiện
  một thẻ: "Lúc bạn vắng: nhân viên bán 37 đơn, dùng 37 ly giấy, 37 hạt… · lãi 1.240 xu", bấm "Xem chi tiết" để xem
  từng món, thu, lương, giá vốn, thưởng 40% và lời giải thích "hàng không hết hạn: nhân viên đã bán". Nơi làm: thẻ ở
  Sổ tiệm → Nhân viên, kèm thông báo nhỏ và dòng "Cần để ý"; quầy: thẻ trên đầu quầy. Số món của nơi làm lấy từ bộ đếm
  mới `ops.business_used` (tùy chọn, mỗi nghề một bảng {món: số đã dùng}, chỉ đơn riêng của nhân viên cộng vào; hết hạn,
  mất trộm, việc của chủ không tính). Bản lưu thiếu khóa vẫn hợp lệ; 1.9.15 và 1.9.16 nhận và giữ nguyên khóa. Mốc "lần
  xem trước" lưu trong máy (localStorage), không thêm gì vào bản lưu.
- 💍 Ném vòng (B5): lượt mới chỉ phát sau 2 giây kể từ lượt trước (trước: 1,5 giây và chỉ khi lượt đang dở). Bấm nhanh
  hơn thì máy chủ trả "Từ từ thôi nha, cô Tư đang nhặt vòng!", không trừ gì. Nút "Ném lượt nữa" tự chờ đủ 2 giây nên
  chơi bình thường không bao giờ gặp. Không giới hạn số lượt, cách tính xu giữ nguyên.
- 🔨 Nhà đấu giá: thêm dòng "Ai trả giá cũng là người chơi thật. Người thắng mất hẳn số xu đã trả, không hoàn lại."
- 🏅 Hành trình: dưới danh hiệu đang đeo thêm "Danh hiệu tự hiện cạnh tên trong chat. Chạm để đổi cái đang đeo."

# v1.9.16 — 2026-10-07

- Điều dưỡng: ô Huyết áp tách thành hai ô số (tâm thu / tâm trương) có dấu "/" in sẵn, vì bàn phím số điện thoại không có phím "/" (chủ game 07/10). Gửi lên vẫn là "120/80".
- iOS 15: vẽ khung bo góc (roundRect) và hộp thoại (<dialog>) có bản thay thế.

Gồm sửa lỗi vòng góp ý 5: trả lời đánh giá không mất, nút Khép ca to, hội chợ 10 phút/20 ván đầu không kiểm tra, tiệm hoa, situationView, ảnh JPEG ≤ 200 KB, log 413. Không có Có gì mới.

# v1.9.15 — 2026-10-07

Gồm sửa karaoke (hết giật, nhận thêm kiểu link), lux (nút mờ khi thiếu tiền), và mic trực tiếp (schema 30 account_birth; bật bằng LIVE_KARAOKE_MIC=1 sau khi cài LiveKit: deploy/livekit).
# Chưa phát hành

## Sửa lỗi iPhone iOS 15: cảnh tiệm không vẽ, sheet không mở (B1, B2)

- iOS 15.4–15.8 (mở được game từ 1.9.14) không vẽ được cảnh nào: khoảng 3.680 lỗi `roundRect is not a function`
  từ 14:17, vì `roundRect` của canvas chỉ có từ Safari 16. `public/js/boot.js` thêm `roundRect` cho
  CanvasRenderingContext2D, Path2D và OffscreenCanvasRenderingContext2D, chỉ khi trình duyệt chưa có. Bản này theo
  spec HTML: bán kính là số, `{x,y}` hoặc danh sách 1–4 giá trị; báo RangeError khi sai; bỏ qua NaN/∞; thu nhỏ góc
  chồng nhau; lật khi w/h âm. Đã so từng điểm ảnh với bản gốc của WebKit và Chromium (fill, stroke, Path2D): trùng
  khớp. iOS 15.0–15.3 không có `<dialog>` (39 chỗ `showModal()`), nên boot.js thêm một bản thay tối giản: chỉ chạy khi
  không có `HTMLDialogElement`; có open/showModal/close, sự kiện close, Esc gửi cancel và một lớp nền `.mnl-backdrop`.
  `scripts/check_old_safari.mjs` giờ chặn `.roundRect(` và `.showModal(` nếu boot.js không có bản thay. Nó cũng chặn
  `requestIdleCallback`, `OffscreenCanvas`, `ctx.reset()`, `checkVisibility()` và `navigator.userActivation` khi dùng
  không có kiểm tra (các chỗ đang dùng đều đã có). Không đổi save, không đổi server.

## Sửa lỗi chiều 07/10 (trả lời đánh giá, Khép ca, công an hội chợ, tiệm hoa)

- Trả lời đánh giá không còn mất im lặng (fb_reply 409: 29 → 148 lần): khi lời AI của khách lưu chậm, câu trả lời được
  gửi lại tối đa 3 lần theo trạng thái mới (chờ lời AI đang trên đường về xong, nghỉ 0,2 / 0,5 / 1 giây). Vẫn không được
  thì chữ vẫn nằm trong ô và hiện thông báo "Trả lời chưa gửi được, khách vừa nhắn." kèm nút **Gửi lại** (điền lại chữ
  và gửi). Lệnh khác cũng thử lại 3 lần thay vì 1.
- F#236: nút Khép ca ở màn chính (khi còn mời thêm khách được) là nút có chữ, nằm riêng một hàng, không còn là icon cửa
  nhỏ. Khép ca / Mở ca trong thanh dưới cùng và trong bảng việc chiếm cả hàng, cao ít nhất 44 px (360×640, 320×568).
- Hội chợ: vừa vào không bị công an hỏi ngay. Mỗi lượt chơi (bắt đầu sau 30 phút không chơi ván có cược) có 10 phút
  đầu hoặc 20 ván có cược đầu, tính mốc nào tới SAU, không kiểm tra thu 30% ví và không hỏi nguồn tài sản. Xác suất và
  khoảng cách giữa hai lần kiểm tra giữ như 1.9.12; dẹp chiếu trong vẫn tính từng ván. Khóa mới, tùy chọn:
  `journey.fair_sess` {at, n, ls} (1.9.13 giữ nguyên khi đọc; thiếu khóa = ván có cược tới bắt đầu lượt mới).
- Tiệm hoa: bấm Cắm/Bó từ màn vẽ trước khi hẹn giờ cắm xong thì bỏ qua cho tới lần vẽ lại; máy chủ coi lệnh cắm lần hai
  trên bó đã cắm là OK và không đổi gì (không tính nhịp, không trừ kiên nhẫn) thay vì báo "Đã hoàn thành dáng.".
- Bảng tình huống không còn lỗi khi trạng thái chưa có nghề hiện tại (12 lỗi lúc khởi động lại 10:22).
- Lệnh quá lớn (>256 KB) ghi một dòng `[cmd-413]`: tên lệnh, cỡ, ba trường lớn nhất (chỉ tên và cỡ, không ghi nội dung).
- Ảnh chụp cảnh (📸 album) và ảnh phòng (Sửa nhà) trên iPhone không còn bị từ chối "Thao tác quá lớn": Safari không
  làm được WebP nên trước đây gửi PNG (thường > 256 KB). Giờ thử WebP, không được thì JPEG (không bao giờ PNG), hạ dần
  chất lượng rồi cỡ ảnh tới khi ≤ 200.000 ký tự (v4/photo-encode.js).
- Không thêm mục "Có gì mới". Không đổi CSDL.

# v1.9.14 — 2026-10-07 (hotfix)

Gồm "Sửa lỗi iPhone iOS 15–16.3 không vào được game".

# Chưa phát hành

## Sửa lỗi iPhone iOS 15–16.3 không vào được game

- Từ ít nhất 01/10, iPhone chạy iOS 15 và iOS 16.0–16.3 (khoảng 90 máy mỗi ngày) không mở được game: hai biểu thức
  regex dùng "nhìn lùi" `(?<=…)` mà Safari chỉ hiểu từ 16.4 (`public/js/toast-lines.js`, `public/js/v4/i18n.js`). Một
  file không đọc được là cả game không tải, rồi màn hình cứ tải lại ↔ "Tải lại" mãi.
- Viết lại hai chỗ đó không dùng nhìn lùi (`splitNotes`, `sentences`), kết quả cắt câu y hệt bản cũ
  (tests/old_safari_regex.mjs so trên ~20.000 chuỗi mẫu và ngẫu nhiên).
- `boot.js`: thêm bản vá cho `.at()`, `Object.hasOwn`, `findLast`/`findLastIndex`, `crypto.randomUUID` (iOS 15.0–15.3
  chưa có; chỉ thêm khi máy thiếu). `admin/users.js` bỏ `.at()` (trang admin không có boot.js).
- `boot.js`: khi file của game không đọc được (lỗi cú pháp), lần đầu tự tải lại một lần như cũ; lần thứ hai không tải
  lại nữa mà báo rõ "Trình duyệt này quá cũ… cập nhật iOS hoặc mở bằng Chrome" (máy mới thì vẫn là "Tải lại"), và gửi
  một beacon kèm UA: cột screen `old:v<bản>:ios15.8` / `parse:v<bản>:chrome90` trong stat_client_errors.
- Kiểm tra mới `scripts/check_old_safari.mjs` (chạy kèm `node scripts/check_js.mjs`, và tests/test_old_safari.py): đọc
  mọi file public/**/*.js bằng acorn (để sẵn ở scripts/vendor, không cần npm) và báo lỗi khi gặp thứ Safari 15.0 không
  có: regex nhìn lùi, cờ v/d, modifier, tên nhóm trùng; class static block; cú pháp mới hơn ES2022; await ngoài module;
  `.at()`/`Object.hasOwn`/`structuredClone`/`toSorted`/`Object.groupBy`/… khi chưa có bản vá hay chưa kiểm tra.
# Chưa phát hành

## Phòng hát bớt giật, dễ thêm bài; Mua sắm: nút ảnh thẻ mờ khi thiếu tiền

- 🎤 Nhạc hết giật (B2, chat 07/10 "nhạc cứ giật giật"): trước đây cứ lệch 0,35 giây là máy tua lại video mỗi giây; mỗi
  lần tua phải tải lại, máy yếu càng lệch thêm, thành vòng lặp. Giờ lệch dưới 2 giây chỉ chỉnh nhẹ tốc độ (0,95 / 1,05,
  nếu YouTube cho; không thì để yên), lệch quá 2 giây mới tua, tối đa 10 giây một lần, không bao giờ tua khi đang tải.
  Thử hai máy (giả lập): lệch nhau 52–311 ms; với YouTube thật: 1–2 ms.
- 🎤 Nói rõ chưa có mic (B3): trong phòng có một dòng "Mic trực tiếp sắp có; giờ hát theo video, cả phòng xem chung"
  (tự ẩn khi bản có mic bật cờ `kara_mic`). Dưới ô dán link: "Mở YouTube → Chia sẻ → Sao chép đường liên kết → dán vào
  đây". Nhận thêm kiểu link điện thoại hay chép: thiếu https:// (youtu.be/…, m.youtube.com/…, music.youtube.com/…,
  youtube.com/shorts/…), link nằm trong câu chia sẻ, trong ngoặc/nháy, có ký tự ẩn, `&` bị mã hóa sau v=. Link sai thì
  báo ngắn "Chưa thấy link YouTube trong đó." (hướng dẫn nằm ngay trên).
- 🛍️ Ảnh thẻ visa (B7, 33 lần bấm khi thiếu tiền từ một người): nút 📷 Chụp ảnh mờ đi khi ví dưới giá ("Ví chưa đủ"), bấm
  vào chỉ hiện lý do, không gửi lệnh (kiểu "mờ có lý do" của docs/UI_KIT.md). Nút 🛡️ Bảo hiểm cũng vậy ("Còn thiếu … xu",
  trả bằng ví rồi tới tài khoản ngân hàng như máy chủ). Các nút mua khác (thanh dưới) đã có sẵn lý do.
- Không đổi bản lưu, không thêm khóa, không đổi CSDL. Không thêm mục "Có gì mới".

# Chưa phát hành

## Phòng hát: mic trực tiếp

- 🎙️ Phòng hát Mây: người đang đứng sân khấu bấm **🎙️ Mic** để cả phòng nghe giọng mình hát trực tiếp (trễ ~0,2–0,5 s),
  người nghe không nói được, không ghi âm ở đâu cả. Cả phòng thấy "🎤 Đang phát trực tiếp giọng hát"; người nghe có
  nút âm lượng giọng riêng (🎤, 🔇) đè lên video YouTube của chính mình, "🔈 Chạm để nghe giọng" khi điện thoại cần chạm.
  Lần đầu: một dòng khuyên đeo tai nghe, rồi hỏi năm sinh (lưu một lần), rồi trình duyệt xin quyền micro. Đồng bộ video
  giữ nguyên như cũ.
- An toàn: dưới 16 tuổi (tính theo tuổi nhỏ nhất có thể từ năm sinh) chỉ nghe; tài khoản phải đủ 1 ngày; mic tự tắt khi
  hết bài / bỏ bài / bị bỏ phiếu / QL bỏ bài, khi rời phòng, sau 6 phút, khi QL bấm 🔇 Cắt mic (trong phòng hoặc trang
  quản trị) hay 3 người báo cáo giọng hát (🚩: nói bậy / 🛟 có vẻ là trẻ em / khác; QL thấy là "🎙️ lúc hát mic trực
  tiếp"). Mời ra, khóa chat như cũ. Chặn nhau (👥 › 🚫 mới trong phòng) thì không nghe giọng nhau, chặn giữa bài cũng bị
  ngắt trong 1 giây. QL có thêm "🎂 Hỏi lại năm sinh".
- Kỹ thuật: SFU LiveKit tự cài (deploy/livekit: cấu hình, systemd, nginx `/sfu/`, ufw 7881/tcp, script `install.sh`
  để lead chạy; TURN/TLS qua 443 là bước 2 tùy chọn). Nhà mạng chặn UDP vào/ra máy chủ (đã đo, chỉ đọc), nên tiếng đi
  qua ICE/TCP. Mỗi lượt mic một phòng SFU riêng, xóa là cắt ngay; token của ca sĩ chỉ phát micro, của người nghe chỉ
  nghe (live/sfu.py). SDK livekit-client 2.22.3 tải từ jsDelivr, khóa SRI, chỉ khi có mic.
- Công tắc `LIVE_KARAOKE_MIC=1` (mặc định tắt, cả live và game server). Tắt: header, route, khung live y như 1.9.13
  (`Permissions-Policy: microphone=()`). Bật: `microphone=(self)`, CSP thêm đúng một file SDK và nguồn SFU.
- CSDL: bảng mới `account_birth` (SCHEMA_VERSION 30, sau 29 của đấu giá; chỉ thêm bảng; quay về 1.9.13 không thấy nó). Không thêm khóa nào
  trong bản lưu. Xóa dữ liệu cá nhân xóa luôn năm sinh.
- Kiểm thử: tests/test_karaoke_mic.py, tests/test_live_karaoke_mic.py; scripts/browser_live_karaoke_mic.py (4 điện
  thoại, LiveKit thật, mic giả; `--tcp-only`: không UDP).
# v1.9.13 — 2026-10-07

Gồm "Nhà đấu giá đồ độc bản" (schema 29: auction_lots, auction_bids; journey.uniq).

# v1.9.12 — 2026-10-07

Chỉ gồm "Hội chợ: công an bắt ít hơn một nửa" (không thông báo Có gì mới).

# Chưa phát hành

## Hội chợ: công an bắt ít hơn một nửa

- Công an tới ít hơn một nửa, mỗi lần thu bao nhiêu vẫn như cũ:
  - Chiếu trong bị dẹp: 0,88% mỗi ván (trước 1,76%). Tiền phạt (¼ tiền cược, ít nhất 3 xu) và 2 phút bày lại giữ nguyên.
  - Thu 30% ví (lời hôm nay trên 50.000 xu, sau một ván có cược): 35% khi tới lượt kiểm tra (trước 70%), vẫn tối đa 30
    phút một lần.
  - Hỏi nguồn tài sản (tiền lời hội chợ trên 50.000 xu): 22,5% khi tới lượt (trước 45%), vẫn tối đa 2 tiếng một lần, thu
    10% phần lời mới.
- Chiếu trong vẫn khoảng 50 ván thắng trên 100 (chơi liền một trò thì thấp nhất 40%): ít bị dẹp hơn nên xác suất rút
  thăm chỉnh lại cho khớp (XD_BASE .513 → .508, XD_FLOOR .407 → .404).
- Không đổi bản lưu, không thêm khóa, không đổi CSDL; 1.9.10 và 1.9.11 vẫn đọc được bản lưu. Không thêm mục "Có gì mới".
# Chưa phát hành

## Nhà đấu giá đồ độc bản

- Chủ phố 07/10: một chỗ tiêu tiền thật lớn cho người giàu (top 1% giữ 57% tiền, người giàu nhất 4,1 triệu xu, người
  giữa bảng kiếm ~262 xu/ngày). 🔨 **Nhà đấu giá** (game/auction.py + auction_content.py, v4/auction.js): chỉ phố mở phiên,
  người chơi không tự đăng bán (không rửa tiền được). Mỗi lô là một món độc nhất, chỉ đúng một người sở hữu mãi mãi.
- 48 món, 3 hạng giá khởi điểm 5.000 / 50.000 / 500.000 xu (bước giá tối thiểu 500 / 2.500 / 25.000 hoặc 5%, lấy số lớn):
  🚗 biển số đẹp (29A-888.88, 51G-999.99, Mây-6666, 68-LỘC-68…: biển vàng trên xe đang đi, ở Gara, trên phố của mình và hồ
  sơ; biển tên tự viết không được chép), 📱 số điện thoại đẹp (0999.999.999…: trên hồ sơ và điện thoại đang dùng),
  🖼️ tranh độc bản của họa sĩ trong phố (treo ở nhà như đồ trang trí, có bảng đồng, không bán lại), 🏞️ quyền đặt tên
  danh thắng (Hồ, Đồi, Bến, Vườn, Cầu, Thác mang tên người thắng, bảng 🏞️ Danh thắng trên bản đồ), 👑 danh hiệu độc bản
  ("Người đầu tiên lên Mặt Trăng Phố Mây"…: bên tên trong chat `tt`, đeo ở Phong cách).
- Lịch: mỗi ngày 1–3 phiên, tính sẵn theo ngày (phiên 1 hạng thường, phiên 2 quý hiếm, phiên 3 huyền thoại), mở 20:30 /
  21:00 / 21:30 (sau giờ cao điểm), chạy 24 giờ. 5 phút cuối có người trả giá: thêm 5 phút (tối đa 6 giờ). Không ai trả:
  món về lại kho. Người vận hành thêm phiên: POST /api/admin/auction (món trong danh mục, hoặc biển số/số điện thoại tự đặt).
- Trả giá (`jr_auc_bid`): tiền được giữ từ ví rồi tới tài khoản, không bao giờ nợ; tự nâng giá của mình chỉ giữ thêm phần
  chênh. Bị trả cao hơn: tiền về ngay (trang nhận tin từ dịch vụ live và lấy lại liền; về đúng chỗ đã lấy: phần từ tài
  khoản về tài khoản). Thắng: tiền của người thắng bị đốt (không ai nhận). Tài khoản phải đủ 3 ngày; tối đa 12 lần trả giá
  một phút; tên hiển thị qua bộ lọc, có ô "Ẩn danh". "🔒 Đang giữ cho đấu giá" hiện trên chip ví; bảng 💰 Tài phú vẫn tính
  tiền đang giữ. Không pay-to-win: chỉ để khoe.
- An toàn tiền: mỗi lần trả giá khóa dòng phiên (FOR UPDATE) trong chính giao dịch lưu bản lưu, so khớp tiền giữ trong bản
  lưu với cơ sở dữ liệu, compare-and-set theo `seq`; sai thì cả lệnh hủy, không mất xu. Tiền trả lại và món thắng đi qua
  `live_effects` (loại 'auction'), dòng chuyển trạng thái ngay trong giao dịch của bản lưu nên chỉ trả một lần. Chốt phiên
  (dọn dẹp mỗi 30 giây và khi có người mở trang) khóa dòng, chỉ từ 'open', id cố định: chạy bao nhiêu lần, bao nhiêu
  worker cũng chỉ một lần.
- Live: `auction_watch` khi đang mở Nhà đấu giá; giá mới tới ngay từ NOTIFY của lệnh trả giá (không hỏi CSDL theo khung
  hình); `auction_outbid` / `auction_won` tới người chơi ở bất cứ đâu trong game. Thông báo đẩy khi bị trả cao hơn (mỗi
  phiên tối đa 10 phút một lần) và khi thắng. Bán từ 50.000 xu: một dòng trên bảng tin phố.
- Giao diện: cửa 🔨 Nhà đấu giá (Khu văn phòng) và 🏞️ Danh thắng (Ngoại ô) trên bản đồ, mục trong "Ngân hàng & nhà";
  4 tab (Đang đấu, Đã chốt, Danh thắng, Của tôi), 20 chữ một màn (check_word_caps --life).
- Bản lưu: khóa tùy chọn `journey.uniq` {v, hold, own, stats} (migrate + validate); các bức tranh thắng là món `uq_tr_*`
  trong `journey.reno.items`; danh hiệu thắng nằm trong `journey.spend.own`. Đã thử (scripts/auction_rollback_check.py):
  bản lưu mới mở, kiểm tra, chơi qua một ngày và lưu lại trên 1.9.11, quay về bản mới vẫn nguyên tiền giữ và đồ.
  Quay về 1.9.11: phiên không chốt, tiền đang giữ nằm nguyên trong bản lưu, dòng 'auction' chờ bản mới.
- CSDL: SCHEMA_VERSION 29 (`auction_lots`, `auction_bids`; chỉ thêm bảng). Cổng task-compat với 1.9.11: OK.

# v1.9.11 — 2026-10-07

Gồm "Nuôi chó mèo" (pets-plus), "Tăng ca ×2 và thưởng năng suất" (ot-bonus), "Giá cả tăng ~10%" (price-up), "Thêm
nhiều thứ để mua" (luxury-sinks) và nghề mới "Bán album ZPOP" (career-zpop). Có gì mới: một mục 5 dòng. Các mục từ
"Chat hiện đủ danh hiệu" tới trước "# v1.9.10" đã có trong bản 1.9.10.

- Khi ghép: đồ nội thất và giấy dán tường của dinh thự giữ giá viết sẵn (không qua chỉ số giá: hàm `_i`/`_sk` của
  nội thất nay nhân chỉ số). Phi cơ có tổ bay đổi tên "Trực thăng VIP có tổ bay", "Siêu du thuyền Hoàng Gia có thủy
  thủ đoàn", "Chuyên cơ thân rộng có tổ bay" để không lẫn với Trực thăng riêng 78.000, Phản lực riêng 117.000, Siêu du
  thuyền Ngọc Trai 195.000 của Gara; mã vẫn riêng (`journey.lux` khác `journey.garage`). Thú cưng giữ giá hằng số.
- Bản lưu: thêm khóa tùy chọn `journey.pets`, `journey.lux` (1.9.10 đọc được) và khối nghề `careers.zpop` (1.9.10 không
  đọc được: "Bản lưu cần đủ các nghề."). Quay về 1.9.10 thì chạy trước `scripts/strip_new_careers.py strip --careers
  zpop` (cất phần của nghề ra file lưu trữ, `restore` trả lại khi lên bản mới; tiền không đổi). Đã thử: bản lưu 1.9.11
  đã gỡ zpop qua migrate_state + validate_state của 1.9.10 và chơi tiếp một ngày.
- CSDL: SCHEMA_VERSION 28 (27 `pet_board`, 28 `lux_gifts`; chỉ thêm bảng). Cổng task-compat với 1.9.10: OK.
- Trang mở từ bản cũ hơn 1.9.11 nhận 426 `client_outdated` và tự tải lại (MIN_CLIENT mặc định 1.9.11, từ 1.9.10).

# Chưa phát hành

## Nuôi chó mèo

- 🐾 Nuôi thú cưng (game/pets.py + pets_content.py, v4/pets.js, v4/pet-art.js): 14 giống chó (chó ta, Poodle, Corgi, Shiba, Phốc sóc, Chihuahua, Husky, Golden, Alaska, Phú Quốc, Bắc Hà, Pug, Samoyed, Lạp xưởng) và 13 giống mèo (mướp ta, tam thể, mun, Anh lông ngắn, Anh lông dài, Ba Tư, Scottish Fold, Munchkin, Ragdoll, Bengal, Sphynx, Maine Coon, Xiêm), mỗi giống 2–4 màu lông, tự vẽ 4 dáng (ngồi, đi dạo, ngủ, vui) theo nét "ấm cúng" của game, tính cách riêng. Giá 300 xu (giống ta) → 30.000 xu (Phú Quốc thuần chủng).
- 🏠 Góc nhận nuôi Chân Nhỏ ở Tiệm Thú Nhỏ Chú Út: mỗi ngày 3 bé chờ nhà mới (có hôm có bé thuần chủng bị bỏ lại), nhận nuôi miễn phí, tùy tâm ủng hộ 20–500 xu. 🛍️ Tiệm bán mọi giống và màu. Cửa 🐾 cạnh shop thú cưng trên bản đồ phố, và trong menu Khu phố.
- Tối đa 3 bé ở nhà; 🏡 "Về quê với bà" giữ bé lại (đón về lúc nào cũng được), không bé nào mất đi.
- Chăm nhẹ nhàng: no, vui, sạch, khỏe giảm theo ngày; bỏ bê thì bé buồn, hơi yếu, không bao giờ chết hay bỏ đi. Thức ăn 4 mức (cơm nhà miễn phí → tiệc 80 xu), đồ chơi (dùng hết hoặc giữ mãi), tắm ở nhà 15 xu, spa Mèo Mập 120/90 xu hoặc gọi thợ là người chơi nghề Pet care (đơn khách thật có sẵn), khám 150 xu, tiêm phòng 250 xu/30 ngày.
- Phụ kiện giữ mãi (mỗi món một bé đeo): vòng cổ, nơ, nón lá mini, mũ ếch, vương miện, áo len, áo mưa, áo đội tuyển, hoodie khủng long, áo dài mini, váy công chúa, ổ bông → lâu đài 5.000 xu.
- Bé học trò theo ngày được chăm (bắt tay, lăn tròn, "pằng!"…), 📸 chụp ảnh chung với nhân vật (4 dáng, 4 khung, lưu về máy), 🏆 Bé cưng của tuần (chỉ để khoe). Bé đi theo nhân vật trên bản đồ phố, ở trong phòng, và người khác thấy bé ở phố đi dạo.
- Không pay-to-win: không thêm xu, không thưởng công việc; bé vui chào bạn +1 tinh thần mỗi ngày. Tiền qua ví/tài khoản như cũ (dòng 'life').
- Bản lưu: thêm khóa tùy chọn `journey.pets` (migrate + validate); 1.9.10 đọc, giữ và lưu lại nguyên vẹn (đã thử). Bảng mới `pet_board` (SCHEMA_VERSION 27). Live: trường tùy chọn `pt` cạnh `look` (dịch vụ cũ bỏ qua).
- Giá là hằng số, không qua chỉ số giá 07/10 (price_index): đồ của bé là đồ mới, giá đã tính sẵn.

## Tăng ca ×2 và thưởng năng suất

- Chủ tiệm 07/10: ai làm nhiều việc trong một ngày thì có thêm tiền. Mỗi nghề có một "ngày bình thường" đo từ máy chủ
  (khoảng 65% số ca làm ít việc hơn mức này, 28/09–07/10): trà sữa 7 việc, tạp hóa 4, giao hàng 6, mẹ và bé 3, phi công 8,
  thư ký 9… Làm quá mức đó, mỗi việc xong tốt (hoàn tất, có trả tiền, đánh giá công bằng từ 3★) được trả thêm đúng tiền
  công việc đó: "⏱️ Tăng ca ×2", tối đa 3 việc một ca, mỗi việc thêm tối đa 50 xu.
- Làm tới mức chăm nhất (khoảng 12% số ca, ít nhất 3 việc quá ngày bình thường) thì lúc khép ca được thêm 30% tiền công
  các việc trong ngày: "⚡ Thưởng năng suất 30%", tối đa 60 xu.
- Chỉ tính việc tự tay làm: đơn nhân viên tự bán, đội làm trong ca quản lý, đơn của người chơi khác không tính. Tiền boa,
  lương ngày, lương ×3/×5 kế toán, phần tăng lương chức vụ không nhân đôi. Ngày 🔥 x3 tính thưởng trên tiền lời không gồm
  hai khoản này (không cộng dồn).
- Tiền về quỹ nơi làm việc như tiền công, nhóm "Tăng ca, thưởng năng suất" trong sổ thu chi; không tính vào doanh thu chịu
  thuế 4% (nghề hưởng lương vốn không đóng). Ai mới thêm nghề sau này tự có mức: max(4, số việc nghề giao trong ngày), +3.
- Màn làm việc có chip nhỏ không chữ cạnh nút ngày và trên đầu màn việc: "⏱️ 2/3" → "🔥 ×2 1/3" → "⚡ +30%"; chạm vào
  để xem luật. Tổng kết ngày thêm thẻ "Thưởng chăm chỉ". Không thêm khóa bản lưu, không thêm bảng; bản 1.9.9 đọc được
  bản lưu mới; không trả bù cho ngày cũ.

## Giá cả tăng ~10%

- Chủ phố 07/10: "mọi người nhiều tiền quá rồi". Bảng 💰 Top tài phú 07/10: 38.725 người, top 1% giữ 57% tổng tài sản
  (06/10: 50%), top 10 giữ 22%; người giữa bảng ~470 xu. Thứ người giàu mua là xe, nhà, đồ đắt tiền.
- Một chỗ duy nhất: `game/price_index.py` (`INDEX_PCT = 110`, bậc xa xỉ `LUXURY`: từ 20.000 xu +20%, từ 60.000 xu +30%).
  Mọi bảng giá người chơi trả ghi giá gốc và đi qua `pi.price()` khi nạp; lần chỉnh sau chỉ sửa một dòng.
- Tăng ~10% (làm tròn đẹp, giá dưới 5 xu giữ nguyên): tiền phòng + cơm nước mỗi ngày 10–20 → 11–22 xu, phòng trọ 14 → 15
  (giường ký túc xá giữ 7 xu cho người mới), điện nước nhà mình, xe dọn nhà; xe (và tiền xăng), điện thoại, quần áo, mở khóa màu, nội thất, giấy
  dán tường, sửa và nâng cấp nhà; đi quán, spa, rạp phim, phong cách tuần, gợi ý công đức (5/20/50/200/1.000 → 6/22/55/220/1.100);
  ăn trưa/tối/ăn thêm, tủ lạnh, nuôi mèo/cún và đồ cho bé; học phí lớp cấp tốc 15–30 → 17–33; làm tóc, đi chơi khu phố,
  chụp ảnh hội chợ 5 → 6; đồ chống rủi ro, thuốc, khám bệnh, xả stress, mua sắm bốc đồng, góp giúp hàng xóm (gợi ý);
  nhẫn, tiệc cưới (rạp, cỗ, nghi lễ, dịch vụ); phạt trễ thẻ 8 → 9; cơm trưa mang cho vợ/chồng 5 → 6.
- Xa xỉ tăng mạnh hơn (chỉ người giàu chạm tới): Siêu xe 30.000 → 36.000, Siêu du thuyền 150.000 → 195.000, Phản lực
  90.000 → 117.000, Kim Long Vàng 24.000 → 28.800, mua penthouse/biệt thự thêm 20–30% thuế.
- 🏠 Nhà: giá niêm yết giữ nguyên (1.9.9 khóa giá nhà trong bản lưu), thay bằng dòng 💹 Thuế trước bạ 10/20/30% trả cùng
  khoản trả trước (ví hoặc tài khoản; không vay, không lấy quỹ chung). Thuế không cộng vào giá thị trường, giá bán, tiền
  cho thuê hay phí bảo trì. `prices()` đã nhận sẵn giá mới để bản sau gộp thuế vào giá niêm yết.
- Không đổi: lương, tiền bo, giá khách NPC trả, giá sỉ/hàng nhập của nghề, quầy riêng (giá mặt bằng, thuê, nâng cấp),
  giá người chơi tự đặt, tiền cược hội chợ và vé số, khoản vay/lãi suất, các khoản trả từ quỹ nơi làm (quà đồng nghiệp,
  đồ nghề), phí theo % (ngân hàng, Mây Coin, vàng). Làm nail 18 và làm đồ thủ công 22 giữ nguyên (1.9.9 khóa giá trong bản
  lưu; validate đã nhận giá mới cho bản sau). Vé tham quan của nghề hướng dẫn viên giữ nguyên (nằm trong việc sinh ra).
- Đồ đã mua giữ giá đã trả: xe, điện thoại bán lại 70%/65% giá đã trả, nhẫn 80% giá đã trả, nhà theo giá mua. Bảng tài
  phú không tăng ảo. Nội thất bán lại 50% giá hiện hành (món mua trước 07/10 bán được ~55% giá đã trả, vẫn lỗ).
- Bản lưu: không thêm khóa. Bản lưu làm ở bản này vẫn mở được trên 1.9.9 (đã thử: nhà 3 bậc thuế, du thuyền, phản lực,
  điện thoại vàng, quần áo, nội thất, phong cách, công đức, học phí, làm tóc, đi chơi). Cổng task-compat với 1.9.9: OK.

## Thêm nhiều thứ để mua

- 🛍️ **Mua sắm** (menu "Ngân hàng & nhà", 4 cửa mới trên bản đồ: ✈️ Đại lý vé, 💎 Hàng hiệu, 🎆 Mạnh Thường Quân,
  🏰 Dinh thự). Giá 300 → 3.000.000 xu, dồn vào chỗ người giàu đang để tiền. Không đồ nào tăng thu nhập hay giúp làm việc:
  chỉ danh hiệu, khoe hồ sơ, album, tinh thần trong giới hạn cũ.
- ✈️ **Du lịch nước ngoài**: Trung Quốc, Hàn, Nhật, Mỹ, Châu Âu; hạng phổ thông / thương gia (×3) / hoàng gia (×10).
  Xin visa đủ giấy: ảnh 3.5×4.5 chưa quá 30 ngày (chụp 20 xu), sao kê tài khoản 1–3 lần giá vé, xác nhận đi làm, lịch
  trình, bảo hiểm (Châu Âu); Mỹ phỏng vấn 3 câu (học xong tiếng Anh: 1 câu). Thiếu một giấy là bị trả hồ sơ, phí không
  hoàn. Mỗi ngày một chuyến, đóng dấu hộ chiếu, ảnh vào album, quà lưu niệm mua ngay hôm đó.
- 💎 **Bộ sưu tập**: đồng hồ, túi hiệu, trang sức, tranh, tượng hiếm, rượu vang; ★ → ★★★★ (2.000 → 2.000.000 xu). Bán lại
  60 %. Rượu vang khui uống được (mất chai, không hoàn tiền).
- 🏰 **Dinh thự** (6 căn, 150.000 → 2.500.000 xu): vườn Đà Lạt, Đông Dương, kính Mây, biển Mũi Né, Penthouse Sky Mây, Dinh
  thự đảo Hòn Mây. Ở được, 2–3 tầng (nút chuyển tầng), phòng to hơn nhiều và phòng riêng của biệt thự: thư phòng, phòng
  khách quý, phòng chiếu phim, hầm rượu, gym, phòng thay đồ, gara trưng bày, sân thượng, hồ bơi vô cực, chòi vườn. Mỗi
  loại phòng có màu tường, sàn, đồ gắn sẵn và 18 món nội thất riêng, 7 bộ góc mới. Bán lại 60 %.
- 🌅 **Biệt thự Sông Hồng** được nâng cấp miễn phí: ba tầng, phòng to hơn, thêm thư phòng, phòng khách quý, sân thượng
  ngắm sông. Đồ đang bày giữ nguyên chỗ (món nào vướng cửa sổ, cửa mới thì vào túi).
- 🛫 **Phi cơ & du thuyền có phi hành đoàn**: Trực thăng VIP có tổ bay 200.000, Siêu du thuyền Hoàng Gia có thủy
  thủ đoàn 1.000.000, Chuyên cơ thân rộng có tổ bay 2.000.000 (trên Siêu du thuyền Ngọc Trai của Gara, nay 195.000; tên
  khác hẳn Trực thăng riêng / Phản lực riêng của Gara, mã riêng trong `journey.lux`). Mỗi ngày một chuyến đi chơi.
- 🧾 **Phí hạng sang** mỗi tháng (5 ngày sống): dinh thự 0,4–0,6 %, phi cơ 0,6–0,8 %, đồ sưu tập từ 50.000 xu 0,2 % giá
  mua (quản gia, bảo vệ, phi hành đoàn, bảo hiểm). Trừ ví rồi tài khoản; thiếu thì miễn, không bao giờ thành nợ.
- 🎉 **Mở tiệc** sinh nhật / tân gia: 4 hạng (Tiệc nhà → Hoàng gia), 5–100 khách. Tiệc sang lên bảng tin cả phố.
- 🎓 **Khóa học**: 5 ngoại ngữ, nếm rượu vang, golf, MBA, bằng lái máy bay riêng; mỗi ngày một buổi, học xong có danh
  hiệu.
- 🎆 **Mạnh Thường Quân**: pháo hoa cả phố (lên bảng tin và Cả phố, mỗi 10 phút một màn), khắc tên ghế đá (24 chỗ) và
  cột đèn (12 chỗ) với lời khắc chọn sẵn, tài trợ hội chợ / đêm nhạc ZPOP của tuần, góp quỹ thư viện trường. Bảng Mạnh
  Thường Quân tuần, có ẩn danh.
- 🏷️ 16 danh hiệu trọn đời (Dân xê dịch, Chúa đảo, Thạc sĩ MBA, Mạnh Thường Quân…), đeo ở Phong cách như danh hiệu tuần,
  hiện bên tên trong chat. Thẻ người chơi ở Phố nghề khoe dinh thự, món quý nhất, số nước đã đi.
- Bảng 💰 tính dinh thự, phi cơ, đồ sưu tập theo giá bán lại 60 %.
- Bản lưu: khối mới `journey.lux` (bản 1.9.9 vẫn mở được, đồ trang trí ở dinh thự tạm vào túi). Bảng mới `lux_gifts`
  (SCHEMA_VERSION 28, sau 27 của thú cưng).

## Nghề mới: bán album ZPOP

- Tiệm album Mây Pop của chị Thơ ở Phố chợ (mở ở chương 3, cửa tiệm 💿 cạnh quán cơm tấm). Bán album và đồ fan của ba
  nhóm nhạc hư cấu: BLANKPINK (nhóm nữ 4 người: Bơ-Ri, Mận-Ji, Sữa-Ah, Hồng-Bi; fandom BLINKY, lightstick "Búa hồng"),
  7GIÓ (nhóm nam 7 người) và tân binh KIWIZ. Không có tên, ảnh, bài hát hay công ty thật; hình chỉ là emoji và hình vẽ.
- Album nhiều phiên bản: Pink, Blank, Jewel case (bản giới hạn), Digipack từng thành viên (card chắc chắn của người đó),
  bản trưng bày đã khui, Kit ver không có CD. Khách nói theo thứ bên trong ("chắc chắn card Mận-Ji", "bản có đĩa CD",
  "búa có Bluetooth, lắp pin sẵn"), mình phải chọn đúng bản, đúng pin (ver.1 pin AAA, ver.2 pin AA).
- Ở quầy: quét Bảng Zchart, cuộn poster vào ống, ghi phiếu fansign (tỉ lệ thật hiện ngay: 30 suất / số phiếu), tặng
  POB của tiệm. Bản giới hạn có số tối đa mỗi người (ngày comeback 2, ngày thường 3).
- Buổi sáng: đếm bản giới hạn, dựng biển giới hạn đúng luật nhà phân phối, thử búa trưng bày (hết pin thì thay); ngày hạn
  chót cộng sổ đặt trước rồi chốt đơn (trả tiền nhập thật, hàng vào kho).
- Khách khó, tự quyết theo tính riêng: dân trao đổi card đòi khui trước khi trả tiền, phụ huynh không rành nhóm (phải xem
  giấy nhắn của bé), người đẩy chart mua 30 bản chỉ cần hóa đơn, dân buôn gom bản giới hạn, người lấy hàng đặt trước giùm
  (hỏi mã, đối số điện thoại), fan đòi hứa chắc trúng fansign, đòi POB tiệm khác, người chen hàng ngày comeback. Khách
  quay lại: đòi trả vì card "sai" thành viên (album đã khui không đổi, trừ album lỗi), búa mua ngoài đòi bảo hành (soi tem,
  seri, app), búa không ghép ghế (pin ngược, app cũ, Bluetooth tắt, chưa nhập ghế), gửi hàng nhái bán ăn chia.
- 9 chuyện bất ngờ (xin bật MV thật to, thùng album móp, card rơi dưới quầy, fan xin ngủ trước cửa, cúp điện máy quét
  Zchart…), 3 tình huống, ngày comeback / hạn chốt / cosplay / cuối tuần / mưa, khách quen Na (BLINKY bảy năm) có câu
  chuyện riêng tới ngày trúng fansign, truyện nghề 5 hồi, học nghề 3 khách đầu với chị Thơ, danh hiệu, hướng dẫn.
- Màn làm việc trên điện thoại theo bộ giao diện gọn (thanh dưới một nút chính, nút mờ kèm lý do, "?"). Tiền chỉ từ hàng
  bán ra (nhập ở Kho theo giá vốn); lãi một ngày ngang tiệm ảnh, tiệm nail.
- Bản lưu: thêm khối nghề `zpop` (bản cũ tự có khi tải lại). Không thêm bảng, không đổi cách sinh việc của nghề cũ.

## Chat hiện đủ danh hiệu

- Chủ game 07/10: ai đang giữ danh hiệu nào thì chat hiện hết bên tên. Gồm danh hiệu tuần của bảng xếp hạng (Trải
  nghiệm, Danh hiệu, Chứng chỉ, Tài phú top 10; Trùm từng nghề top 1), danh hiệu hội chợ dân gian (🌪️ Trúng bão bầu
  cua, 🎯 Mắt thần phi tiêu, 👑 Vua trò chơi, 🎪 Cao thủ hội chợ… cả 11 cái) và 🥇/🎊 Khách mời của tuần (đám cưới).
- Chip nhỏ bên tên: emoji + tên ngắn kèm hạng ("💰 Top 3 Tài phú", "🏆 Trùm trà sữa", "🌪️ Bão bầu cua"). Điện
  thoại hiện 2 chip + "+N", máy tính 3; chạm tên hoặc "+N" mở hộp nhỏ liệt kê đủ tên và nguồn ("Top 3 Tài phú · tuần
  này", "Hội chợ dân gian"). Có ở Cả phố, nhóm, lời trích khi trả lời (chip tốt nhất), đầu cuộc nhắn riêng (DM), thẻ
  người chơi ở phố đi dạo; bảng tên trên phố thêm emoji các danh hiệu còn lại. Danh hiệu mua tuần (🎨) giữ như cũ.
- Live service: khung `msg`, trang lịch sử, `reply` và walker/`card` có thêm `tt` (danh sách id, tốt nhất trước:
  `lb_<bảng>_<hạng>`, `f_*`, `w_vip`/`w_pro`). Máy chủ tự tra từ lb_weekly và bản lưu (journey.titles), không bao giờ
  tin client; cache LRU 20.000 người (TTL 15 phút), bảng tuần đọc lại mỗi 5 phút. Game báo NOTIFY `honours` (trúng danh
  hiệu hội chợ, nhận danh hiệu qua live_fx) và `honours_lb` (làm mới bảng tuần, chốt tuần thứ Hai) để cập nhật ngay;
  tuần đã hết thì chip tự mất. Không thêm truy vấn mỗi tin nhắn. Client cũ bỏ qua `tt`, `ti` giữ nguyên chữ.
- Không thêm khóa bản lưu, không đổi DDL.
## Phòng điều hành bay, lộ trình kế toán, tạp hóa, ghim nội thất (fix-office-misc)

## Phòng điều hành bay (F#223)

- Cơ trưởng nghỉ việc thì hãng điều một cơ trưởng khác về thay, cùng bậc (trước đây người thay luôn là cơ phó mới).
- Đội bay không bao giờ mở ngày với ít hơn 2 cơ trưởng: thiếu thì hãng nâng cơ phó giỏi nhất lên (phòng cũ được sửa
  ngay ngày làm kế tiếp, quỹ lương cộng thêm phần chênh).
- Số chặng cần cơ trưởng = số cơ trưởng còn bay được hôm nay (tối đa 2): hết cảnh ngày nào cũng có chặng bị hủy.
- Phó Giám đốc Khối (bậc 5) có thêm ⬆️ Thăng chức. Phòng chỉ huy công an giữ nguyên luật.

## Lộ trình kế toán (F#227)

- Dòng khóa thăng tiến ghi tiến độ: "🧭 Lộ trình bậc 2: 4/6 ngày chắc tay · tin tưởng 48/55", kèm thanh tiến độ.
- Thêm ô "🪜 Cách lên bậc" 3 bước ngắn, chi tiết sau nút "?". Áp dụng cho kế toán doanh nghiệp, thuế & tiền lương,
  kế toán hợp nhất.

## Chuyện đời và chuyện ở tiệm (F#221)

- Tuần đầu ở một chỗ làm (ngày 1–7): chỉ chuyện nhẹ, tần suất còn một nửa.
- Chuyện để tới cuối ngày chưa quyết: chọn cách ít tốn nhất mà không sai (trước đây là cách tệ nhất), không được thưởng.
- Lựa chọn hên xui ghi rõ tỷ lệ: "🎲 Hên xui · 40% được việc" (chuyện đời và chuyện bất ngờ ở quầy).
- Mất trộm ở tiệm/quầy: "📹 Xem camera, báo công an phường" có 50% (85% nếu có camera) lấy lại đủ, không mất xu.

## Ghim nội thất (F#224)

- Nút 📌 Ghim trên từng món khi sắp xếp: món đã ghim không bị kéo nhầm (lưu trên máy này). Phải kéo 12 px (trước 6 px)
  món mới bắt đầu dời.

Bản lưu: không thêm khóa mới; bản 1.9.10 đọc được.
## Sửa lỗi nhỏ (backlog 4: misc4)

- 📡 iPhone gửi được số liệu ẩn danh (beacon): Safari và WebView iOS (Zalo…) gửi `Origin: null` khi trang đặt
  `Referrer-Policy: no-referrer`, nên mọi beacon từ iPhone bị 403 (07/10: 2.818 lần, 0 lần nhận). Giờ `null` tính là
  "không rõ nguồn", nhận `Sec-Fetch-Site` same-origin / same-site / none và Origin là host của mình (www ↔ không www);
  website khác vẫn bị chặn. Beacon chỉ ghi bảng stat_*, cookie phiên SameSite=Strict; API đổi dữ liệu giữ nguyên
  kiểm tra CSRF và Origin.
- 💬 Chuyện phố: nút "Trao đổi tình huống" chỉ hiện ở nghề máy chủ nhận (mẹ & bé, nhà thuốc, kế toán, CSKH; giáo viên,
  hướng dẫn viên, trà sữa mở sổ riêng). 45 nghề khác không còn nút bấm ra lời từ chối; "Trả lời đánh giá" vẫn như cũ.
  Danh mục nghề có cờ `review_followup` (game/content.py REVIEW_FOLLOWUP).
- 🐣 Tên nhân vật được có tối đa 2 emoji ("Vịt🐣", "Bơ 🐨", cờ 🇻🇳, emoji ghép 👩‍💻 tính là 1). Cần ít nhất một chữ hoặc
  số; lọc từ tục vẫn chạy (emoji chen giữa chữ không lách được). Ô tên ở màn chào có dòng nhắc luật. Chữ cái đầu ở ảnh
  đại diện (Chuyện phố, hôn nhân) và tên khi đi chung xe không còn cắt đôi emoji.
- 🐢 Đỡ lag trên điện thoại: vòng sáng chỉ đường (gd-pulse / gd-ring) nhấp nháy 3 lần rồi sáng đứng yên, không chạy mãi
  (trước đó trang tính lại kiểu chữ 60 lần mỗi giây khi đứng yên). Bật "Giảm chuyển động" thì vòng đứng yên ngay.
- Không thêm khóa bản lưu, không đổi DDL.
## Sửa lỗi bấm hai lần khi khách đang trả lời

- Lỗi từ 1.9.3: khi khách đang "viết" (AI trả lời đánh giá, viết lại đánh giá, giọng cô giáo), lệnh bấm sau phải chờ tới 4 giây mà nút không báo gì, người chơi bấm lại, lệnh trùng xếp hàng rồi bị từ chối ("Khách đang đọc phản hồi trước của bạn.", "Còn một chuyện trong lớp cần xử lý trước."). Giờ lệnh y hệt đang chờ hoặc đang gửi không gửi lần hai; vừa xếp hàng là màn đã coi như đang bận (giữ lần bấm sau, nút hiện vòng chờ). Ô trả lời đánh giá và nút "Gửi trả lời" tắt trong lúc gửi. Mốc chờ AI tối đa 4 giây giữ nguyên.
- Đánh giá: chỉ gửi kiểu bù đắp mà nghề đang chơi có (tab mở từ trước 1.9.5 gửi "Hoàn 20 xu" cho nghề không hoàn → "Nghề này không bù đắp kiểu đó."); chưa có danh mục của nghề thì chỉ "Không bù". Trang cũ hơn bản máy chủ: nút "🔄 Tải lại để cập nhật" không tắt được và trang tự tải lại ở lần chuyển màn tiếp theo (khi không gõ dở, không có lệnh đang gửi; mỗi phiên bản một lần).
- Tab cũ tự làm mới: mỗi lệnh gửi kèm phiên bản trang (`cv`); máy chủ trả 426 `client_outdated` cho trang cũ hơn `MIN_CLIENT` (mặc định 1.9.11, biến môi trường `MIN_CLIENT`, để trống là tắt; không bao giờ cao hơn bản máy chủ đang chạy nên trang mới không bao giờ bị từ chối). Trang trò chơi chưa gửi `cv` (có X-Game-Delta) tính là cũ; công cụ/script không có header đó thì không. Trang tự tải lại khi rảnh, tối đa một lần mỗi phiên bản và một lần mỗi 2 phút (không lặp khi triển khai cuốn chiếu); worker cũ bỏ qua `cv`.
- Trà sữa sau khi khép ca: ly còn dở vẫn mở được quầy nhưng ly, trà, siro, topping, đá, đường, dán nắp mờ đi, bấm vào hiện "⚠ Mở ca trước" kèm nút mở ca; nút chính dưới cùng thành "☀️ Mở ca". Không còn chọn món hiện trước rồi bị trả về. Kho, ủ trà, đặt hàng vẫn dùng được.
- Chăm sóc khách: chứng cứ "Chính sách đổi trả" của vụ thiếu món hiện là "Chính sách thiếu hàng" (chỉ đổi chữ trên màn, bản lưu giữ nguyên để 1.9.10 vẫn đọc được). Gợi ý "Đổi đúng món" thêm "(không phải thiếu món)"; chọn sai phương án thì dòng 📌 căn cứ hiện trước.
- Tiệm hoa: hẹn giờ nhấc hoa / cắm mút không gửi lại khi người chơi đã tự bấm và lệnh còn đang gửi; đọc lại bó hoa trước bước cắm.
- Không thêm khóa bản lưu, không đổi CSDL.

# v1.9.10 — 2026-10-07

Gồm "Cấp bậc công an" (ranks-police: org ladder, cấp hiệu bảng màu riêng của game). Có gì mới cũng thông báo Phòng hát Mây (bật từ 07:28 07/10 bằng LIVE_KARAOKE).

# Chưa phát hành

## Sửa lỗi: quầy chỉ bán 3 món, nhà cho thuê không lấy lại được, quỹ chung tối đa 5.000 xu

- 🏪 Quầy (F#232, F#220): nhân viên chỉ bán món đã bật ở Menu, mà menu mặc định chỉ có 3 món đầu (Áo, Quần, Váy), trong khi tab 📦 Hàng cho nhập cả 12. Quầy mới bật sẵn mọi món của nghề (tối đa 18). Nhập hàng một món chưa bật thì tự bật món đó (giữ giá đã đặt). Tab 📦 Hàng ghi "Chưa bật ở Menu" cạnh món có hàng mà chưa bán, kèm nút "Bật" và "Bật tất cả món có hàng"; bật thêm món được cả khi đang đứng quầy (đổi giá, bỏ món vẫn phải đóng ca). Quầy cũ giữ nguyên menu, không tự đổi.
- 🏪 Khi menu nhiều món, khách của nhân viên tới lần lượt từng món thay vì dồn một đợt (cùng số khách mỗi giờ như trước).
- 💼 Góp vốn quầy: lấy ví trước, thiếu thì lấy tài khoản ngân hàng, đúng như hướng dẫn; ví đang nợ thì không góp, không bao giờ làm âm ví hay tài khoản.
- 🏠 Thuê nhà người chơi (F#225): người thuê nghỉ chơi thì ngày sống không trôi, hợp đồng treo mãi. Chủ nhà nay thấy "hết hạn ngày X" và nút "Lấy lại nhà" khi kỳ đã trả hết theo giờ thật: quá 5 ngày kể từ lần trả gần nhất (10 ngày nếu người thuê đã trả trước kỳ sau), hoặc người thuê vắng 3 ngày mà chưa trả trước kỳ sau. Không bao giờ giữa kỳ. Người thuê nhận thông báo (hộp thư + nhật ký nhà), không mất thêm xu, tìm chỗ ở mới. Điều khoản thuê ghi rõ điều này.
- 🏦 Quỹ chung (F#231): mỗi lần gửi tối đa 200.000 xu (trước đây dùng nhầm hạn mức tặng tiền 5.000). Tặng / cho mượn vẫn tối đa 5.000.
- Bản lưu: không thêm khóa mới (quầy mới ghi sẵn `menu`, khóa đã có). Bảng `rentals` có thêm trạng thái `ended`. Bản 1.9.10 đọc được mọi bản lưu mới (đã thử).

## Cấp bậc công an

- Hệ chức vụ & cấp bậc dùng chung (game/org.py + org_content.py), công an trước: cấp bậc hàm (Binh nhì → Đại tá; Thiếu tướng Giám đốc chỉ là NPC) và chức vụ (Tổ viên → Tổ phó → Tổ trưởng → Đội phó/Đội trưởng 113 → Phó/Trưởng CA phường Mây → Phó/Trưởng phòng PC06 → Trợ lý BGĐ → Phó Giám đốc CATP) là hai đường riêng. Hàm lên theo ngày làm, ★ và hồ sơ sạch, tới trần của chức vụ; vài bậc cần khóa học (2 câu kiểm tra). Chức vụ lên bằng bổ nhiệm: đủ hàm, đủ ngày, chờ ghế trống, phỏng vấn 2 câu. Trưởng phòng PC06 trần Thượng tá.
- ⚠️ Hệ thống tự nhận diện làm sai quy trình (xem thiếu giấy, chen hàng, trả đồ/giao trẻ khi chưa xác minh, đăng ảnh trẻ, bỏ qua nguy hiểm, xử lý sai mức, dọa khi hòa giải, bỏ tin báo chưa gọi lại, ghi khống sổ trực ban): mỗi lần một cảnh cáo, lần 4 hạ 1 bậc hàm. 10 ngày sạch hết 1 cảnh cáo; kỳ "Hoàn thành xuất sắc" xóa 1. Ở Binh nhì: tạm đình chỉ 3 ngày, không lương. Hạ hàm dưới chức vụ thì về chức cao nhất hàm cho phép. Lúc thử việc và khi anh Định còn kèm: chỉ nhắc.
- 💵 Nhận phong bì: hạ 1 bậc ngay, ghi dấu liêm chính mãi mãi (không làm Trợ lý BGĐ, Phó Giám đốc, không lên Đại tá); tự giác nộp lại trong ca thì thành 1 cảnh cáo, dấu vẫn ghi "đã tự giác". Phong bì mới ở đồ thất lạc, hòa giải, tuần tra; lập biên bản hành vi đưa hối lộ được +1 Liêm chính.
- 🏢 Phòng chỉ huy từ Tổ trưởng (dùng chung phòng điều hành của phi công): phân công, khen, nhắc, khiển trách, cảnh cáo, kiểm điểm, kỷ luật, thăng/giáng, điều động, tăng/hạ bậc lương, chỉ với cán bộ NPC (có người nhận phong bì ngầm). Kỷ luật thiếu căn cứ bị tính cảnh cáo cho mình. Trợ lý BGĐ: kiểm tra điều lệnh 2 đơn vị một ngày rồi trình PGĐ.
- 🎖️ Thẻ cấp bậc (cấp hiệu, ⚠️ n/3, ★, Liêm chính), nhân vật mặc quân phục có cấp hiệu, huy hiệu, mũ khi vào ca công an; người khác thấy cấp hiệu ở phố đi dạo và đám cưới. Cấp hiệu theo bảng màu riêng của game (chủ game 07/10): nền xanh két, vạch bạc, sao vàng nhạt; chiến sĩ, hạ sĩ quan nền xanh nhạt hơn; cấp tướng (NPC) nền đồng.
- Cán bộ khu vực cũ vào thang theo bậc đang có (bậc 0 → Tổ viên Hạ sĩ … bậc 4 → Phó Trưởng CA Thiếu tá), không đổi tiền, lương không thấp hơn hôm nay. Lương theo hệ số hàm × phụ cấp chức vụ. Hỗ trợ tiếp dân bán thời gian giữ thang cũ. Các nghề khác: mới có khung nội dung.
- Bản lưu: thêm khóa tùy chọn `journey.promo.police.org` và `careers.police.ext.data.beat`; bản 1.9.4 và 1.9.9 đọc được (đã thử quay về và chơi tiếp một ngày).

# v1.9.9 — 2026-10-07

Gồm "Giao diện gọn: đợt 4" (quầy ăn uống + phố còn lại) và "đợt 5" (13 nghề cuối + màn đời sống: nhà, bản đồ, ngân hàng, hội chợ).

# Chưa phát hành

## Hội chợ: tỷ lệ thắng thấp hơn, chơi liền một trò thì vận nguội, công an kiểm tra tài sản

- Chiếu trong, lô tô, vé cào, phần may rủi của ném vòng: khoảng 50 ván trên 100 là thắng (trước 65), tức gần hòa
  vốn, hết cày xu ở hội chợ. Bỏ luật "thua liền 4 ván thì ván sau chắc thắng" (cược nhỏ 4 ván rồi cược lớn là ăn chắc).
  Thắng liền 4 ván thì vận hơi nguội, còn 45%.
- Lô tô: Kinh ăn 2,1 lần tiền tờ, làm tròn xuống (trước 2,2; Hũ đêm hội 2,3). Hô Kinh đúng lúc mọi ván thì lời nhiều
  nhất 5% (tờ 2 và 5 xu: hòa vốn).
- Chơi một trò quá 10 ván: mỗi ván sau giảm 1,5 điểm, thấp nhất 40% (khoảng ván 17 trở đi). Chỉ hai cách về lại 50%:
  chơi 3 ván ở trò may rủi có cược khác (bầu cua, chiếu trong, lô tô, vé cào, trộn trò nào cũng được), mỗi ván cược ít
  nhất 20 xu và ít nhất ¼ tiền cược gần nhất ở trò đang nguội; hoặc nghỉ trò đó 10 phút. Ván cược nhỏ hơn, ném vòng,
  ô ăn quan, phóng dao không tính. Trong gian hiện dòng "🥶 Vận đang nguội…" kèm "cần thêm N ván ≥ X xu ở trò khác".
  Bầu cua vẫn là xúc xắc thật (mỗi mặt 1/6), không bị vận nguội.
- Lần công an thu 30% ví giữ nguyên như 1.9.9 (sau một ván có cược, lời hôm nay trên 50.000 xu, 70%, tối đa 30 phút
  một lần).
- Thêm một luật riêng: công an hỏi nguồn tài sản khi tiền lời ở hội chợ kỳ này (số trên Bảng vàng) trên 50.000 xu, sau
  một ván có cược, tối đa 2 tiếng một lần, 45%. Thu 10% phần lời mới từ lần hỏi trước (không thu hai lần trên cùng một
  đồng), lấy ví trước rồi tới tài khoản ngân hàng, không bao giờ âm, không thành nợ. Ghi trong Sổ ví. Cùng một ván
  thì lần thu 30% ví đến trước, lần hỏi tài sản sau, tính trên tiền lời còn lại; hai thẻ hiện lần lượt.
- 🍀 Lộc trời cho: một ván may rủi có cược vừa thắng (cả bầu cua, xúc xắc vẫn thật) đôi khi ăn ×10 tiền cược thay cho
  tiền thắng thường. Cả máy chủ mỗi giờ nhiều nhất một lần (khóa chung trong bảng mnl_meta, giữ trong cùng giao dịch
  của lệnh: thử lại lệnh không nhận hai lần). Tính vào tiền lời hội chợ.
- Bản lưu: thêm khóa tùy chọn journey.fair_audit {ed, base, at} và journey.fair_cool {trò: {n, at, sw, st}}; bản 1.9.9 vẫn
  nhận bản lưu mới. Không thêm bảng, không
  đổi SCHEMA_VERSION. Chiếu dẹp vẫn bày lại sau 2 phút như cũ.

## Giao diện gọn: đợt 4

- 12 nghề: quầy trà sữa, cà phê – bánh, quán mì cay, tiệm hoa, tiệm kem, nội trợ, thu gom rác, sạp trái cây, tiệm nail,
  nấu cơm gia đình, photobooth, thư viện. Màn đầu trên điện thoại (390 px) còn 13–30 chữ (trước 35–109).
- Trà sữa: hết cảnh 3 khung dính trên màn. Phiếu gọi món không còn dính trên đầu, chỉ còn chip "🧾 0/5" trên đầu màn để
  mở lại phiếu khi đã cuộn xuống. Thanh dưới chung (ly nhỏ, "Còn n bước" và một nút chính); cà phê cũng vậy, máy tính
  không còn hai nút giống nhau.
- Lời giải thích (nhịp pha 2×/4×, so phiếu miễn phí, mẹo dán nắp, lời dẫn buổi sáng…) vào nút "?" (mục "Trên màn này").
  Danh sách bước thành chip "📋 0/4"; nút trên bàn lặp lại bước ở thanh dưới chỉ còn hai chữ ("🌡️ Ẩm kế").
- Giữ nguyên trên màn mọi thứ quyết định đúng sai: phiếu gọi món đủ từng dòng ("Không sữa bò", dị ứng hải sản, mang
  về), lời khách, khoảng cân chuẩn của viên kem, nút tủ cần vặn, túi rác "trông lạ", tác dụng dù/bạt, kim cân lệch, móng
  khách, luật của nhà nấu cơm ("Bé không ăn cay, sợ xương cá…"), độ ẩm kho kèm khoảng chuẩn. Ngày mưa, cúp điện, nắng
  gắt thì lời dặn buổi sáng ("mang ủng", "căng bạt", "sạc sẵn đèn pin") vẫn hiện ngay.
- Nội trợ: buổi nhận tiền chợ còn "💵 “80 xu” · 4 tờ gấp đôi" và ba cách làm gọn chữ, đủ ý. Nấu cơm: thực đơn chỉ mở
  nhóm món đang tới lượt, nhóm khác một dòng kèm món đã chọn.
- Máy chủ báo trước, nút mờ kèm lý do (đã bị từ chối nhiều nhất 04–06/10): trà sữa không còn mời khách đổi trân châu khi
  quầy không nấu được (mời đổi chỉ với siro/topping mua sẵn), mì cay không mời đổi lần hai món đã đổi và chỉ múc thêm chén
  nước dùng khi tô đã có nước, nội trợ "Còn việc chưa xếp vào thứ tự", thu gom phải quét rác vương vãi trước (nút sửa:
  "🧹 Quét dọn"), sạp trái cây đủ số trái anh Lâm gom, tiệm nail / photobooth / kem chưa mở tiệm (nút sửa: về việc buổi
  sáng).
- Giao diện cổ điển và máy tính giữ chữ như cũ; công tắc "Giao diện gọn" / `MNL_CLEAN_UI=off` vẫn tắt được. Không đổi
  bản lưu, không thêm bảng, không đổi cách sinh việc.
## Giao diện gọn: đợt 5

- Đợt cuối: 13 màn làm việc và các trang đời sống còn nhiều chữ. Màn đầu trên điện thoại (390 px) còn 16–30 chữ: giao
  hàng 128 → 30 (các đơn khác vẫn hiện, mỗi đơn một dòng: đi → đến, ⏰ hạn, 💵 ⚠️ ❄️), nhà thuốc 90 → 24, giáo viên 87 → 24, kế toán 83 → 22, hướng dẫn viên 82 → 23, shop quần áo 60 → 25,
  tạp hóa 43 → 18, homestay 41 → 18, sửa đồ 40 → 24, salon 37 → 26, chăm thú cưng 34 → 18, mẹ & bé 32 → 21, nông trại
  26 → 16. Trang đời sống tối đa 30 chữ: nhà 115 → 29, bản đồ khu phố 51 → 29, hội chợ 66 → 25, ngân hàng (đã mở tài
  khoản) 144 → 27; quầy, tủ đồ, đi chơi, phòng hát, màn chính vốn đã gọn, giữ nguyên.
- Mọi nghề còn lại dùng thanh dưới chung một nút chính (nhà thuốc, kế toán, mẹ & bé, giao hàng, nông trại, homestay, tạp
  hóa, salon, chăm thú cưng, shop quần áo). Lời giải thích, luật, cách tính vào nút "?".
- Giữ nguyên trên màn mọi thứ quyết định đúng sai: lời khách nói (giao hàng giữ trọn câu dặn), phiếu thuốc và nhãn lô,
  chứng từ và số tiền khi đối chiếu, câu hỏi và câu trả lời của học trò, yêu cầu của đoàn khách, phòng và đơn của khách
  homestay, size/màu/ngân sách khi bán quần áo, bệnh máy khách kể, yêu cầu màu tóc (tên việc của salon và sửa đồ không bao
  giờ bị cắt ngắn vì chính là lời khách).
- Nút chưa bấm được thì mờ nhưng vẫn chạm được, nói rõ lý do và có nút sửa (máy chủ báo trước): nhà thuốc (khay chưa khớp
  phiếu, chưa đọc nhãn lô), kế toán (ghép chứng từ, bàn giao), giao hàng (ngã tư ngoài chặng, chưa chọn điểm đến), homestay
  (phòng có đơn app chờ đồng bộ, gợi ý quá nhiều nơi), shop quần áo (giá treo hết size), salon, sửa đồ, chăm thú cưng.
- Hội chợ: trò ném vòng không còn tự chơi lại lượt đã xong (trước đây bị báo "Lượt ném này đã xong rồi." liên tục).
- Nhà: thẻ nơi ở chỉ còn tên và tiền mỗi ngày bằng biểu tượng; đồ đạc và nhà đang rao gọn thành một dòng mở ra được. Ngân
  hàng: các mục là biểu tượng, cách trả mặc định gọn một dòng, dòng báo thành công tự mờ sau 6 giây.
- Giao diện cổ điển và máy tính giữ như cũ; công tắc "Giao diện gọn" / `MNL_CLEAN_UI=off` vẫn tắt được.
- Không đổi bản lưu, không thêm bảng, không đổi cách sinh việc.

# v1.9.8 — 2026-10-07

Gồm "Giao diện gọn: đợt 2" (công an, điều dưỡng, cứu hộ bể bơi, dầu khí, phi công, tiếp viên) và "đợt 3" (6 bàn văn phòng, chăm sóc khách hàng, tiệm thú cưng).

# Chưa phát hành

## Giao diện gọn: đợt 2

- Đợt 2 bớt chữ, 6 nghề đồng phục: công an phường, điều dưỡng, cứu hộ hồ bơi, thợ dầu khí, phi công, tiếp viên. Màn làm việc đầu ca trên điện thoại còn 19–30 chữ (trước 42–172).
- Phi công và tiếp viên: phần giới thiệu nghề không còn chiếm cả màn làm việc (135–172 chữ), giờ là thẻ ngắn như các nghề phố (tên nghề, 3 dòng biểu tượng, nút "?"); thanh dưới chuyển sang thanh chung một nút chính.
- Giữ nguyên mọi manh mối quyết định đúng sai, nhiều chỗ còn dễ thấy hơn: ngưỡng thẻ báo động của điều dưỡng hiện ngay trên từng ô chỉ số (`🚨 ≥38,0 · ≤35,5`), khoảng Clo/pH của bảng mẫu nằm cạnh số que thử, giờ sấm cuối kèm `+30′`, phi công thấy dầu chờ giông thành một dòng riêng trong bảng dầu. Sổ trực ban (công an) và sổ giao ca (điều dưỡng) giữ ghi chú đã đọc; công an có bản ngắn giữ giờ và người cần mình ("Bà Năm bị “cán bộ điều tra” giục chuyển tiền 8:30…"). Lời người giao việc giữ nguyên câu nói; chỉ phần dẫn cảnh ("Chị Thu mở cửa tàu") vào "?".
- Tiếp viên: thẻ lên tàu ghi "Hàng thoát hiểm: người lớn", ghế trẻ nhỏ ghi "♨️ không đồ nóng" ngay trên phiếu gọi món.
- Danh sách bước thành chip "📋 0/4" trên dòng ngày; lựa chọn chờ (làm trước, giường xem trước, mở cổng) mở ra khi tới lượt.
- Máy chủ báo trước, nút mờ kèm lý do: công an chọn chủ đề thứ tư, điều dưỡng chuyển đi thủ thuật khi người bệnh đã từ chối, cứu hộ mở lại hồ khi dông chưa tới, thợ dầu khí xả áp/kiểm về không khi chưa khóa đủ, phi công cất cánh khi chưa xong checklist/thông báo, bay lại khi chỉ còn dầu cho lần này, tiếp viên mời món ghế đã có.
- Giao diện cổ điển và máy tính giữ chữ như cũ; tắt nhanh như đợt 1. Không đổi bản lưu, không thêm bảng, không đổi cách sinh việc.
## Giao diện gọn: đợt 3

- 8 màn bàn giấy và tiệm thú: kế toán tập đoàn, kế toán doanh nghiệp, thuế & lương, hành chính – nhân sự, thư ký, IT
  helpdesk, chăm sóc khách hàng, tiệm thú cưng. Màn đầu (điện thoại 390 px) còn 18–30 chữ (trước 68–141).
- Bàn văn phòng (6 nghề): hàng trạng thái chỉ còn biểu tượng và số (🕗 · thanh tin tưởng · 🔋 · ⏰ · 📅); thẻ trên cùng chỉ
  ghi chữ ở thẻ đang mở; hồ sơ chưa nhận mở thẳng tab 📂 với người giao việc và lời họ nói (lời dặn dài và "🎯 yêu cầu"
  vào nút "?"); thanh dưới dùng chung `.ui-bar`, một nút chính (dấu DUYỆT/TRÌNH SẾP/TRẢ LẠI và lý do lệch sổ thành một
  hàng nút đủ to phía trên).
- Cách tính 📐, mẹo, chi phí hỏi gợi ý, chú thích bảng… vào nút "?" (mục "Trên màn này"). Ô nào vừa kiểm sai thì cách
  tính của ô đó vẫn hiện ngay.
- Giữ nguyên trên màn mọi thứ quyết định đúng sai: lời người giao việc, dữ liệu giấy tờ, "Sếp dặn", quy định giờ làm,
  đề bài từng bước; dòng sổ đối chiếu chỉ bỏ chữ lặp lại, giữ "Nhập theo HĐ-45", "xuất kho 29/03", "lập 16:00",
  "Bán cho …", số NM × tỷ giá.
- Sau 17:30 nút làm việc mờ đi nhưng vẫn chạm được: hiện lý do và nút "🌙 Tăng ca" (máy chủ báo trước `can.work`, trước
  đây hành chính – nhân sự và thư ký bị từ chối "office_closed" nhiều). Bảng lương: dòng đã đánh dấu đủ 3 ô thì các ô
  còn lại mờ và nói rõ lý do (`can.tp_flag`).
- Chăm sóc khách hàng: thanh dưới giữ nút việc bây giờ; bước, lời giải thích, cuộc gọi chưa bắt đầu gọn lại một dòng
  (vẫn thấy tâm trạng khách); các phương án vẫn ghi "Khi …".
- Tiệm thú cưng: giới thiệu nghề còn tên, 3 dòng biểu tượng và "?"; một nút "Vào tiệm" duy nhất; lời khách giữ nguyên,
  cảnh dẫn vào "?"; danh sách việc thành chip "📋 0/2".
- Giao diện cổ điển và máy tính giữ như cũ; công tắc "Giao diện gọn" / `MNL_CLEAN_UI=off` vẫn tắt được.
- Không đổi bản lưu, không thêm bảng, không đổi cách sinh việc.

# v1.9.7 — 2026-10-07

Gồm "Giao diện gọn hơn" (ui-foundation + đợt 1: 10 màn, giữ đủ manh mối quyết định). Tắt nhanh: Cài đặt → Giao diện → "Giao diện gọn", hoặc MNL_CLEAN_UI=off trên máy chủ.

# v1.9.6 — 2026-10-07

Gồm "Thêm chỗ tiêu xu" (spend-1, bảng donations + chat_style, schema 25) và "Phòng hát Mây" (karaoke-p1, schema 26, TẮT mặc định: LIVE_KARAOKE). CSP mở cho YouTube embed. Có gì mới chỉ nói phần tiêu xu; karaoke thông báo khi bật.
## Giao diện gọn (ui-foundation)

## Giao diện gọn hơn

- Chủ game 06/10: "gọn hơn, clean hơn, ít chữ hơn, dễ chơi hơn". Đợt nền tảng, dùng chung cho mọi nghề (docs/UI_KIT.md).
- Một thanh dưới chung (`.ui-bar`): bên trái là bước tiếp, bên phải là một nút chính. Đã chuyển 21 nghề phố (street kit), tiệm hoa, quán ăn, tiệm sửa, tiệm quần áo, giáo viên, hướng dẫn viên. Bỏ luật "42%" bóp chữ trên điện thoại và các bản vá `!important` của giáo viên/hướng dẫn viên.
- Giới thiệu nghề (21 nghề phố): từ ~180 chữ còn ~22 chữ, gồm tên nghề, 3 dòng biểu tượng và nút "?" chứa phần giới thiệu đầy đủ.
- Nút chưa bấm được thì mờ đi nhưng vẫn chạm được: chạm vào sẽ hiện một dòng lý do và nút sửa ngay trên thanh dưới, không gửi lệnh vào chỗ chắc bị từ chối. Máy chủ báo trước bằng đúng luật nó dùng để từ chối: giúp việc (lau khi chưa cầm dụng cụ/chai, chai cạn) và tiệm hoa (trao hoa khi chưa cắm/gói xong).
- Phiếu khách (tiệm hoa, sửa đồ, quán ăn, quần áo) không còn ghim trên điện thoại; số "3/6 ✓" thành chip trên đầu, chạm để mở phiếu.
- Thông báo hiện ngay trong thanh dưới, chỗ "bước tiếp", vài giây (≤ 8 chữ, chạm để xem hết), không che tên màn hình hay nội dung đang làm.
- Nút "?" trên đầu và dòng gợi ý đủ 44 px.
- Bảng cỡ chữ 4 bậc và bảng khoảng cách (`--fs-*`, `--sp-*`).
- Có công tắc tắt: Cài đặt → Giao diện → "Giao diện gọn" (Tự động / Bật / Tắt), hoặc tắt cho mọi người bằng `MNL_CLEAN_UI=off` trên máy chủ.
- Máy chủ báo trước thêm cho chùa (xếp việc, xếp chỗ), cơm tấm (dĩa chưa xới cơm) và photobooth (hết khung, hết bao kiếng, chọn quá số tấm).
- Đợt 1 bớt chữ, 10 màn nhiều chữ nhất: thông cống, cơm tấm, hải đăng, gác chắn tàu, trà đá, bảo mẫu, phở, chùa, tổng đài cứu hộ, giúp việc. Mỗi màn còn 17–30 chữ (trước 47–131). Lời giải thích, mô tả đồ nghề và chuyện dẫn được chuyển vào nút "?". Mọi manh mối quyết định đúng sai vẫn hiện ngay trên màn: lời khách, sổ hẹn (mỗi nhà một dòng), hướng tàu, ghi chú giao ca ("đừng cho", "nhắc khéo"), mẹo của việc bẫy ở chùa ("Mở loa ra đường 4h"), chỗ lấn đường ở quán trà đá, quy tắc nước cơm tấm, giờ tắt đèn +15′.
- Không đổi bản lưu, không thêm bảng, không đổi cách sinh việc.

# v1.9.5 — 2026-10-06/07

Gồm các mục "Chưa phát hành" bên dưới: nông trại mới (farm-plus), mỗi nghề một cách nói (voice-w1), nghề làm công không đóng thuế tiệm (salary-notax).

## Nghề làm công không đóng thuế tiệm (salary-notax)

## Nghề làm công không đóng thuế tiệm

- Chủ game 06/10: nghề làm công, ăn lương (không phải tiệm) không còn đóng thuế 4% và tiền mặt bằng trên tiền công của mình. Áp dụng cho 18 nghề: thầy chùa, giáo viên, điều dưỡng, công an phường, tổng đài cứu hộ, cứu hộ hồ bơi, thư viện, gác chắn đường sắt, gác hải đăng, phi công, tiếp viên, thợ dầu khí, kế toán công ty, kế toán tập đoàn, hành chính – nhân sự, thư ký, IT helpdesk, CSKH. Tiệm, sạp, quán và dịch vụ thu phí của khách (kế toán dịch vụ, thuế & tiền lương, thợ, giúp việc…) giữ nguyên luật cũ.
- Từ ca khép tiếp theo: không cộng tiền thuê mỗi ngày, cuối kỳ 7 ca không ra phong bì thuế và mặt bằng, không có thông báo "Kết kỳ thuế". Phần đã tích trong kỳ đang mở cũng không bị thu. Khoản thuế và mặt bằng đã ra (đã trả hay chưa trả), các kỳ đã kết và sổ giao dịch cũ giữ nguyên: không hoàn, không truy thu. Điện nước, lương nhân viên vẫn như cũ.
- Sổ thu chi của các nghề này ẩn "Phong bì cuối kỳ" (doanh thu kỳ, thuế dự kiến, tiền thuê tích lũy); thẻ Mặt bằng không ghi tiền thuê; tổng kết ngày không còn dòng "thuê … xu".
- Đo bằng cách chơi cẩn thận 14 ngày ở mặt bằng mặc định: điều dưỡng, công an, cứu hộ, cứu hộ hồ bơi, gác chắn, hải đăng được thêm khoảng 7,6 xu mỗi ngày (6 xu thuê + ~1,6 xu thuế), thợ dầu khí 7,9 xu; mặt bằng lớn hơn thì được thêm 11 hoặc 18 xu thuê mỗi ngày. Không thêm trường mới trong bản lưu; bản 1.9.4 vẫn đọc được bản lưu mới.
## Phòng hát Mây (karaoke-p1)

## Phòng hát Mây

- 🎤 Chủ game 06/10: ba phòng hát công khai (Nhạc trẻ, Bolero · trữ tình, Nhạc quốc tế), tối đa 30 người mỗi phòng, đầy thì mở phòng phụ cùng chủ đề. Chị Ngân giữ mic. Vào từ Bản đồ phố (Phố hàng rong) hoặc Thêm › Khu phố › Phòng hát. Chỉ hiện khi dịch vụ live bật `LIVE_KARAOKE=1` (mặc định tắt).
- Mọi người xem cùng một video YouTube ở cùng một giây (trình phát YouTube chính thức, youtube-nocookie, giữ nguyên quảng cáo và logo). Dán link → Kiểm tra (oEmbed, có bộ nhớ đệm) → Xếp hàng: 2 xu, bài đầu mỗi ngày miễn phí. Người xếp bài lên "sân khấu"; cả phòng thả emoji, giữ 🙌 cổ vũ, nhắn, tặng xu (5/10/20/50; ca sĩ nhận 80 %, 20 % đốt; gửi tối đa 200, nhận tối đa 500 xu/ngày). Hết bài: 10 giây vỗ tay. Bỏ phiếu bỏ bài. Chưa có giọng hát trực tiếp, không ghi âm.
- 🧩 Đoán bài: chủ câu đố cho một câu hát ngắn (≤ 12 chữ, che vài chữ bằng ___) hoặc vài emoji, cả phòng gõ đoán (không dấu, sai chính tả nhẹ vẫn được). Người đầu tiên đúng nhận 5 xu (tối đa 25 xu/ngày mỗi người, 10 câu có thưởng/ngày mỗi chủ đố). Hết 60 giây hoặc có người đúng thì hiện đáp án, link thưởng của chủ đố được phát tiếp.
- Kiểm duyệt: tên bài, lời nhắn, câu đoán qua bộ lọc chat (từ nặng thành *); báo cáo (🛟 trẻ vị thành niên lên đầu); khóa chat và chặn được tôn trọng; Ban quản lý bỏ bài, mời ra 1 giờ, đóng phòng, cấm bài, khóa chat (trong phòng và tab 🎤 Phòng hát của trang quản trị).
- Kỹ thuật: CSP chỉ mở thêm khung YouTube, script iframe_api và ảnh i.ytimg.com; Permissions-Policy giữ micro tắt. Khung YouTube tự gửi Referer gốc trang (cả trang vẫn no-referrer; thiếu Referer YouTube báo lỗi 153). CSDL thêm `kara_songs`, `kara_tickets`, `kara_reviews` (SCHEMA_VERSION 26, sau 25 của spend-1). Sổ ví ghi loại `life` (bản 1.9.4 đọc được); loại `karaoke` đã được chấp nhận để bản sau dùng. Không thêm khóa bản lưu.

## Chỗ tiêu xu (spend-1)

## Thêm chỗ tiêu xu

- Chủ game 06/10 ("cho nhiều cái để mọi người tiêu tiền hơn"): người chơi trung bình kiếm ~262 xu/ngày sống, tiêu ~12. Thêm chỗ tiêu hằng ngày và chỗ khoe, không cái nào ra tiền hay giúp làm việc.
- ☕ Đi quán (4 quán của phố, 8–35 xu): no bụng/tỉnh táo tăng, quán đầu ngày +1 tinh thần (món ≥28 xu +2), thẻ tích điểm 10 dấu đổi nhãn dán. Có lối sang quán người chơi (Phố nghề).
- 💆 Spa Sen (25–40 xu): +2 tinh thần lần đầu mỗi ngày. 🎬 Rạp Mây: mỗi tuần một phim, 20 xu, +2 tinh thần, giữ cuống vé.
- 🙏 Công đức Chùa Gió Lành: từ 5 xu, chọn lời cầu, ẩn danh hoặc ghi tên tài khoản. Bảng công đức tuần (khách luôn ẩn danh). Sư thầy cảm ơn mọi người như nhau.
- 🎨 Phong cách 7 ngày (gia hạn tối đa 4 tuần): màu tên 120–400, khung hồ sơ 100–400, danh hiệu 60–400 (vài cái phải chơi mới mở). Hiện trong chat, khi đi dạo, trên hồ sơ Phố nghề.
- Cửa trên Bản đồ phố (☕ Phố chợ, 💆🎨 Phố dịch vụ, 🎬 Phố hàng rong, 🙏 cạnh Chùa) và mục "Đi chơi", "Phong cách" trong menu.
- Bản lưu: thêm `journey.spend` (tùy chọn); sổ ví dùng loại `life` có sẵn, bản 1.9.4 vẫn đọc được. CSDL: bảng mới `donations`, `chat_style` (SCHEMA_VERSION 25). Dịch vụ live đọc màu/khung/danh hiệu từ `chat_style`, gửi kèm trường `st` (ngoài `look`); bản live cũ bỏ qua.

# v1.9.4 — 2026-10-06

- 🏪 Nhân viên tiệm (nơi làm việc) bán nhanh gấp 1,6 lần ngày đầu (góp ý người chơi; lịch sử bản 1.7.8–1.9.3 cho thấy tốc độ chưa từng bị giảm, tiệm thấy chậm chủ yếu do hết hàng).
- 💬 Góp ý dài tới 10.000 ký tự (trước 1.000).
## Mỗi nghề một cách nói (voice-w1)

## Mỗi nghề một cách nói

- Chủ game 06/10 ("nghề mỗi nghề mỗi khác, ví dụ như nhà sư mà nó bảo shop", "sửa mấy cách trò chuyện"): mỗi nghề có một bộ từ riêng (`game/career_voice.py`: chỗ làm, người được phục vụ, ca, tiền, đánh giá, bù đắp), gửi kèm danh mục nghề cho máy khách (`terms`). Tiệm, quán giữ nguyên chữ như cũ.
- Các màn hình dùng chung đọc bộ từ này thay vì chữ "tiệm": hộp xác nhận ("Xác nhận việc chùa", "Xác nhận việc trực ban"), khép ca và sổ ("Sổ chùa", "Sổ khoa", "Đóng cổng chùa hôm nay?"), sổ đội ("Ban công quả", "Mời Phật tử làm công quả", "Thu nhập nghề", "Sân chùa đang yên.", "Về chùa"), chip quỹ ("Quỹ chùa", "Quỹ nghề"), thăng tiến ("Phật tử biếu thêm 5% công đức"), nhắc mỗi ngày ("Chuông sáng đã điểm, chùa đang chờ thầy ☀️", "Ca trực sáng sắp bắt đầu 🩺"), ghé chỗ làm và hồ sơ bạn bè ("Thầy tiếp", "Chấm chỗ làm của…", "lượt tiếp dân").
- Nghề hưởng lương (chùa, giáo viên, điều dưỡng, công an, cứu hộ, thư viện, gác chắn, hải đăng, tổ bay, giàn khoan, văn phòng, CSKH): lời khép ca không còn nhắc tiền thuê, thuế hay "sổ tiệm".
- Trả lời đánh giá: 26 nghề không phải tiệm có câu trả lời mẫu riêng (khoa, bên phường, tổ, thư viện, em thư ký…), nhãn riêng ("Mời làm việc", "Mời gặp", "Hẹn thu bổ sung") và bù đắp hợp nghề (chai nước ấm, gia hạn sách, bớt tiền công). Công an không bao giờ bù đắp thứ gì có giá trị: không hiện mục bù đắp, máy chủ cũng từ chối. Người bình luận dưới đánh giá không còn "bênh quán". Chùa và giáo viên giữ bộ câu riêng như cũ.
- Chỉ đổi chữ: cùng mã giọng, mã bù đắp, mã khách, cách sinh việc như cũ (cổng task-compat OK). Câu trả lời cũ trong bản lưu giữ nguyên. Thuế 4% và tiền thuê không đổi ở bản này. Không thêm khóa lưu, không đổi bảng. Không có "Có gì mới".

## Nhân viên tiệm (staff-speed)

## Nhân viên tiệm bán nhanh như ngày đầu

- Góp ý người chơi 06/10 ("tăng tốc độ bán hàng của nhân viên tiệm", không phải quầy): soát lại mọi bản từ 1.7.8 (04/10, ngày đầu có đơn riêng) tới 1.9.3. Nhịp mỗi đơn chưa từng bị giảm (vẫn 80 phút-công ÷ tốc độ nhân viên); chỉ có uy tín tiệm (từ 1.7.12, 05/10 07:26) làm chậm tối đa 10% khi uy tín âm. Tiệm thường dừng vì hết hàng trên kệ chứ không phải vì đơn chậm.
- Tiệm bán hàng (nghề có hàng/kho: Mẹ & Bé, tạp hóa, hoa, cà phê, quần áo, trà sữa, thuốc, salon…) giờ 50 phút-công một đơn thay vì 80: nhanh gấp 1,6 lần ngày đầu; uy tín −10 vẫn nhanh gấp ~1,45 lần. Tiệm 2 nhân viên tốc độ ~75: khoảng 190 đơn/giờ thay vì ~120. Nghề dịch vụ không dùng hàng (kế toán, giáo viên…) giữ 80. Vẫn chỉ bán món còn hàng và có lãi sau lương, vật tư; ô "mỗi giờ · đơn" trong Sổ tiệm tự cập nhật từ đơn kế tiếp. Không đổi bản lưu.

# Chưa phát hành

## Nông trại mới

- Chủ game 06/10 ("nông trại nữa, chán lắm, nâng lên đi"). Số liệu 01–06/10: 57% lượt bấm ở nông trại là việc vặt (tưới 10.370, nhổ cỏ 4.920, thăm sâu 4.214, khơi rãnh 2.529), mỗi ngày chơi chỉ giao trung vị 4 đơn; 27% người chơi rời đi trong ngày chưa giao được đơn nào, chỉ 16% quay lại ngày thứ hai.
- 🌟 Tab mới **Trại** (`game/careers/farm_plus.py`, `public/js/careers/farm_plus.js`), gồm 4 mục:
  - 🌱 Vườn: ô đất lớn theo giờ thật của máy chủ, kể cả khi đi vắng. Có ớt, lúa, dưa hấu, bí ngô, thanh long, dâu tây (cần nhà kính), xoài, cà phê, chín sau 6 phút tới 2 giờ. Mỗi vụ có việc chăm riêng: cắm cọc, dẫn nước, lót rơm, bấm ngọn, thắp đèn, che lưới, bao trái, tỉa cành. Thêm việc theo thời tiết hôm đó (khát nước, giông) và sâu. Mỗi việc một chạm khi tới lúc. Bỏ lỡ thì hụt sản lượng, xuống loại B; để quá lứa cũng xuống loại B.
  - 🐄 Chuồng: vịt (trứng vịt), bò sữa (sữa), heo (nuôi 4 cữ rồi bán).
  - 🧾 Bán: bán ở chợ (bán dồn thì giá tụt, chợ tự hồi theo giờ) hoặc giao đơn đặc sản cho tiệm trà sữa, lò bánh, quán chè, quán cơm tấm, quán cà phê, sạp trái cây, quán chay (đòi VietGAP), anh Tuấn. Khách nào cũng có yêu cầu riêng: chỉ lấy loại A, có hạn giờ… Có khách đòi bớt giá; giữ giá thì có người vẫn mua, có người bỏ đi, tùy tính khách (ẩn).
  - 🛠️ Nâng cấp (tiêu xu): khai hoang ô 3–6 (80/150/250/400), tưới nhỏ giọt 180 (6 luống rau cũ cũng tự giữ ẩm), máy cày mini 260 (gieo, chăm, thu cả vườn một chạm), chuồng trại 220, nhà kính 350, VietGAP 450 (cần 15 lần thu loại A; giá bán +20%).
- Cấp trang trại 1–10, danh hiệu 🏅 Nông dân giỏi ở cấp 5. Thêm kỷ lục, trái vàng hiếm (25 xu), bí khổng lồ 20–60 kg (có giải), Hội mùa vào ngày cuối mỗi mùa (giá +25%).
- Dễ thấy: ở chế độ 🚶 Tự đi có nút "🌟 Trại" trên cảnh, ngay dưới nút đổi góc nhìn; nút sáng lên và có số khi có ô chín, ô cần chăm hoặc chuồng đã xong (cả trước lần mở đầu). Tab 🌟 Trại cũng hiện số đó, tự cập nhật khi tới giờ. Thanh dưới vẫn một hàng. Có bản tiếng Anh cho chữ mới (`i18n/overrides.json`, `public/i18n/en.json`).
- Bớt việc vặt ở 6 luống: thêm nút 🌾 Nhổ cỏ cả vườn và 🔍 Thăm cả vườn (một nhịp). Gợi ý giữa các đơn chỉ thẳng nút nhổ cỏ cả vườn khi có từ 2 luống nhiều cỏ.
- Thu nhập (bot chăm mỗi phút, đo bằng chính máy chủ): vườn mới (2 ô) +50 xu/giờ, trại giữa (4 ô, chuồng) +90/giờ, đủ nâng cấp +240/giờ. Nông trại hiện thu khoảng 170 xu mỗi ngày chơi (trà sữa ~420, tiệm hoa ~770). Riêng nâng cấp tốn tổng cộng 2.340 xu. Test chặn trần: dưới 80 xu/giờ khi mới mở, dưới 300 xu/giờ khi đủ nâng cấp.
- Bản lưu: khóa mới, tùy chọn: `careers.farm.ext.farm_plus`. Bản lưu cũ không có khóa này vẫn chạy như trước. Không đổi đơn hàng, luống rau, kho mát. Đã thử: 1.9.3 nhận, chơi tiếp và giữ nguyên bản lưu do bản này ghi. Không có DDL. Không thêm "Có gì mới".
# v1.9.3 — 2026-10-06: sửa lỗi + cập nhật thêm

## Chat: lọc từ nặng bằng dấu *

- Chủ game 06/10 (một người chơi chửi bới ở Cả phố, đã ẩn tin và khóa chat 24 giờ): từ nặng giờ hiện thành dấu * theo đúng số chữ ("đéo" → "***"); bắt cả kiểu viết chen dấu chấm/gạch ("đ.ị.t", "l.ồ.n", "v-ú"); thêm "đéo", "vú", "làm gái" (trừ "vú sữa", "vú nuôi", "vú em"). Tiếng lóng GenZ ("vl", "đm", "cút") vẫn giữ như luật 30/09. Số điện thoại, link vẫn che •••.

Có gì mới (chủ game: "sửa lỗi, cập nhật thêm"): sửa lỗi tiệm hoa/giúp việc/chùa/giáo viên/giao hàng/tiệm quần áo; 45 món avatar; cửa hàng điện thoại; bầu cua xúc xắc thật; thăng tiến rõ ràng hơn. Các mục "Chưa phát hành" bên dưới là nội dung của bản này.

## Bầu cua xúc xắc thật

- 🎲 Chủ game 06/10 ("ra cua nhiều quá, bị cheat"): bầu cua lăn ba xúc xắc ngẫu nhiên thật, mỗi mặt 1/6, không quyết thắng thua trước và không còn "thua 4 ván thì ván sau chắc thắng" (trước đây xúc xắc chọn theo mặt đặt nên ai đặt cua thì cua ra nhiều). Lâu dài đặt một mặt lỗ khoảng 4,6% (bão vẫn 10:1). Chiếu trong, lô tô, vé cào, ném vòng giữ như cũ. Không đổi bản lưu.
## Xe giao hàng, tiệm hoa hết hàng, kệ tiệm quần áo, xoay ca phi công (fix-misc)

- 🛵 Giao hàng (#5): xe không còn đứng khựng trước ngã tư có đèn nằm ngoài chặng đang giao. Máy khách kiểm tra hành lang chặng giống máy chủ (đi vòng tối đa 1 ô) trước khi hỏi đèn: ngoài chặng thì đèn chỉ là cảnh, không hỏi, không giữ xe. Máy chủ từ chối hoặc mạng chậm quá 4 giây thì ngã tư đó được thả, xe không bao giờ bị giữ mãi.
- 💐 Tiệm hoa (#9): hết thiệp hoặc hết băng rôn thì nút viết thiệp, in băng rôn và "Dùng lời này" tắt, kèm dòng "Hết thiệp: nhập thêm mới viết được." và nút 📦 nhập hàng ngay cạnh. Bước "Viết thiệp" trong gợi ý cũng dẫn sang nhập hàng khi hết.
- 👗 Tiệm quần áo (F#218): cảnh tiệm vẽ giá treo theo hàng thật trên giá (mỗi mẫu còn hàng một móc, nhiều cái thì móc dày hơn; nón, thắt lưng, tất, giày, túi xếp ở kệ dưới, chồng cao theo số lượng; bảng nhỏ ghi tổng số cái). Hết sạch thì giá trống. Thẻ 👚 Giá treo báo khi có thùng hàng đã tới cửa mà chưa đếm nhận, kèm nút mở thùng.
- ✈️ Phòng điều hành (F#212): nói rõ luật xoay ca. "Xem thêm" có dòng 🔁 Xoay ca; mỗi người có thẻ "🔁 N ngày liền" hoặc "🥱 2 ngày liền · nên nghỉ" (cả trong danh sách chọn người); mục 🎯 hôm nay có dòng xoay ca; tổng kết ngày ghi "🥱 Xoay ca: … đã bay liền từ hôm trước nên dễ trễ hơn hẳn". Luật không đổi.
- Không thêm khóa lưu, không đổi tiền, không đổi cách sinh việc. Máy chủ gửi thêm `tired_at` ở phòng điều hành (chỉ hiển thị). Không có "Có gì mới".

## Tiệm hoa trên điện thoại + Bảng giá (WP-B)

- Góp ý #204 và chat: trên điện thoại dọc (từ 1.8.0), ở tiệm hoa thẻ "Khách cần" dính trên đầu che kệ hoa, chữ bên cột xem trước đè lên ô hoa, chạm không chọn được loại hoa. Giờ thẻ mở thì cuộn theo trang (thu gọn còn một dòng thì vẫn ghim), cột xem trước nằm đúng chỗ, nơ/băng rôn/giấy bóng không vẽ đè lên thẻ nữa. Sửa chung cho mọi nghề dùng thẻ này: sửa đồ, tiệm quần áo, quán mì. Điện thoại ngang và máy tính giữ như cũ.
- Tiệm hoa: nút 🏷️ Bảng giá ở bàn làm việc, ở thanh nghề và một dòng giữa hai đơn: giá từng loại hoa đổi trước khi mở ca, tính vào giá trị bó; khách vẫn trả đúng giá đơn đã báo.
- Chỉ đổi giao diện (CSS/JS): không đổi bản lưu, tiền hay máy chủ. Không có "Có gì mới".

## Thu nhập mỗi giờ, mỗi ngày (WP-D)

- 💰 Sổ tiệm → Đội (#19): khung "Lãi ước tính của đội" ghi lãi mỗi giờ (và số đơn/giờ) và mỗi ngày 24 giờ nếu đủ hàng, đủ quỹ, đã gồm thưởng 40%; kèm số đơn quỹ nghề còn trả được. Tính từ nhịp đơn (`rate_per_hour`) và lãi đơn tiếp theo máy chủ đã có.
- 🏪 Quầy của bạn: thẻ quầy có nhân viên ghi "Lãi 1 giờ" theo chợ lúc này và "Lãi 1 ngày (24 giờ)", đã trừ hàng, lương, điện, thuế và cộng thưởng nhân viên bán, cùng hàng còn đủ bán bao lâu. Máy chủ tính từ đúng nhịp khách, lịch chợ, giá và chi phí mà sổ quầy dùng (một ngày mô phỏng lệch dưới 1%).
- 🎪 Hội chợ (#18, chỉ con số): dải trên cùng thêm "📊 Trò lời +X · trò lỗ −Y" hôm nay, cộng theo từng trò. Không đổi tỷ lệ, không đổi Ông Hai.
- Chỉ hiển thị: không đổi kinh tế, không thêm khóa lưu.

## Thăng tiến rõ ràng, cấp hàm Phó Tổng Giám đốc (WP-C)

- 🏢 "Ngày điều hành tốt" (F#206): Thăng tiến ghi tiến độ "Ngày điều hành tốt: 2/5" kèm thanh và điều kiện (tự xếp ít nhất 1 việc ở 🗓️ Điều phối, cuối ngày điểm điều hành từ 60/100). Phòng điều hành có mục 🎯 "Hôm nay tính ngày tốt?" (đã tự xếp chưa, còn việc cần quyết, ô trống, quỹ lương). Tổng kết ngày ghi điểm và cách tính ("📊 Điểm điều hành 72/100 (đúng giờ 40 + tinh thần 22 + 20 − phàn nàn 12) → ✓ tính 1 ngày điều hành tốt", hoặc lý do chưa tính) và tiến độ n/5. Nhật ký phòng ghi điểm từng ngày. "Xem thêm" giải thích công thức. Thẻ cấp hàm phi công ghi thêm n/5.
- 🎖️ Phỏng vấn lên chức hụt không còn im lặng (#11): báo câu nào bị chấm 0 điểm và bạn đã chọn gì, hoặc "Xin cao" khi chưa có hai câu tốt nhất; ghi rõ hẹn xét lại sau 3 ngày làm. Thăng tiến hiện thẻ "📋 Lần xét vừa rồi" (từng câu: ✅ tốt nhất / 🟡 tạm được / ❌ chưa ưng) và cách đếm ngày tới lần xét sau. Nút "?" ở câu hỏi và phần xin lương nói rõ luật.
- ✈️ Cấp hàm Phó Tổng Giám đốc (F#207, chủ game duyệt): một ngôi sao lớn trên cánh chim vàng, kiểu hàng không, thay cho 4 gạch + 3 sao + cành tùng. Nhãn: "1 sao lớn · cánh chim vàng".
- Không thêm khóa lưu, không đổi tiền. Máy chủ gửi thêm vài trường chỉ để hiển thị (`review` khi hoãn xét, `office.score/good`, `me`, `good_score`, `got/need` ở yêu cầu phòng điều hành, cờ `big/wing` của cấp hàm); bản 1.9.1 bỏ qua chúng.
## wardrobe-classic

## Tủ đồ: 45 món mới (góp ý #200)

- 🛍️ Tiệm Áo Chỉ Mây nhập thêm 45 món, mở bán từ chương 3 (nhân viên tiệm vẫn giảm 20%), có nhãn "Mới" trong Tủ đồ:
  - 8 kiểu tóc: dài uốn sóng, bob mái ngố, đuôi ngựa buộc cao, hai búi tròn, wolf cut, undercut, mái bay, tết bím.
  - 11 đầm và chân váy: váy hai dây, áo dài cách tân, đầm suông, váy maxi hoa, đầm sơ mi, váy yếm jean, đầm babydoll hoa nhí, đầm dạ hội kim sa, chân váy tennis, chân váy jean, chân váy xếp ly dài.
  - 11 áo và quần: croptop, baby tee, áo khoác bomber, hoodie oversize, sơ mi oversize, áo khoác jean, áo ba lỗ, quần ống rộng, cargo, jogger, short jean.
  - 4 đôi giày: sneaker chunky, Mary Jane, bốt cổ ngắn, dép quai ngang.
  - 11 phụ kiện: kính mát mắt mèo, kính cận gọng vuông, mũ bucket, mũ lưỡi trai, nơ lụa to, kẹp tóc càng cua, vòng cổ, khuyên tai tròn, đồng hồ, khăn bandana, balo mini.
- Món nào cũng vẽ đủ ở gương Tủ đồ, ảnh tròn, ảnh chat, đám cưới, đi dạo, hội chợ, hẹn hò, cho cả nam và nữ, và đổi màu được bằng Bảng màu (màu đã mở dùng chung).
- Tủ đồ: nút 🙂 Gương mặt ngay trên đầu (biểu cảm, kiểu mặt khi chat) và lối tới Tên · giới tính ở cuối trang; trên điện thoại 7 mục chia 2 hàng.
- Bản lưu: thêm khóa gốc tùy chọn `wardrobe_plus` (chỉ có khi đã mua món mới). Khối `wardrobe` cũ chỉ giữ món bản 1.9.2 biết, nên bản 1.9.2 đọc bản lưu mới vẫn hợp lệ, hiện món mặc định ở chỗ món mới và không mất món đã mua. Dịch vụ live cũ cũng hiện món mặc định. Không đổi tiền, không thêm bảng.
## gadgets-classic (F#205: điện thoại & đồ công nghệ, giao diện quen thuộc)

- 📱 Cửa hàng điện thoại Mây Mobile ở Phố dịch vụ trên bản đồ phố (cạnh Gara; Chỉ đường → 📱 Điện thoại), hoặc Thêm → Ngân hàng & nhà. Năm hạng máy: Mây Lite 5 150 xu, Sao Mai S12 600, Mây Pro 16 2.400, Sen Gập Fold 3 6.000, Kim Long Vàng 24K 24.000. Đồ công nghệ: tai nghe Sóc Pods 120, đồng hồ Mây Watch 450, máy tính bảng Mây Tab 1.200, máy chơi game Rồng Con 1.600, máy ảnh Cò Trắng X 3.200. Thương hiệu đều là tên tự đặt.
- Trả đủ một lần như mua xe (ví trước, thiếu thì lấy tài khoản; ví nợ thì không mua được), không vay, không phí ngày hay phí tháng. Bán lại 65% giá đã trả, vào ví. Tiền đi qua sổ ví và sổ tài khoản như cũ, không sinh xu.
- 🔁 Máy cũ anh Khoa cho: mua điện thoại đầu tiên thì “Thu cũ đổi mới”, bớt 20 xu, một lần (bỏ chọn nếu muốn giữ máy cũ).
- Khoe: nhân vật cầm máy đang dùng (bản đồ phố, ảnh selfie), huy hiệu máy cạnh “Thay đồ” ở Hành trình, thẻ Phố nghề có máy và 3 món đồ đắt nhất. Mỗi hạng máy thêm một món vui, cộng dồn, không món nào làm ra tiền: Chỉ đường nhớ 3 nơi vừa đi, khung selfie (lưu ảnh về máy), viền màu vỏ máy quanh huy hiệu trên hồ sơ, khung ảnh đôi, viền vàng.
- Hướng dẫn: mục “Lên đời điện thoại”. Tài phú tính điện thoại và đồ công nghệ theo giá bán lại.
- Bản lưu: thêm khóa tùy chọn `journey.gadgets` (chỉ có từ lần mua đầu). Bản 1.9.2 đọc, giữ nguyên và lưu lại bản lưu có khóa này; bản lưu cũ vẫn đọc bình thường. Thẻ người chơi (Phố nghề) có thêm `phone`, bản cũ bỏ qua. Không đổi bảng, không đổi dịch vụ live.
## WP-5 Boot / live

- 💬 Nút Chat hiện ngay sau khung hình đầu: nút xám "đang kết nối…" (chạm thì báo đang kết nối và thử lại liền), sáng lên khi máy chủ chat chào. Kết nối chat khởi động ngay lúc rảnh đầu tiên sau khung hình đầu thay vì cuối hàng chờ (~6 giây). Chưa kết nối được lần nào thì thử lại sau 3, 8, 20 giây rồi mới giãn ra 1–10 phút (trước đây chờ 60 giây, nên ai mở game đúng lúc dịch vụ chat khởi động lại thì không thấy chat cả phút).
- 🔄 Màn hình tải không còn kẹt: app.js (hoặc một file của nó) tải hỏng, hay một file có phiên bản bị 404 lúc đang cập nhật, thì tự tải lại một lần (chống cache). Hỏng lần nữa trong 2 phút hoặc mất mạng thì hiện nút "Tải lại" kèm phiên bản và mã lỗi. Sau 25 giây vẫn chưa xong thì gợi ý "Tải lại". Stylesheet hỏng được thử lại một lần.
- 📊 Lỗi tải trang ghi kèm phiên bản và mã HTTP (screen `loading:v1.9.2-<build>:404`, beacon rời trang `p: v<phiên bản>`).
## phản hồi đánh giá + thanh dưới hướng dẫn viên

- Phản hồi đánh giá: chạm bị dội (409 revision_conflict ở fb_reply và các chạm ngay sau, ~29 phiên ở trà sữa, quần áo, cà phê, thư ký, homestay). Lời AI của khách đáp lại chủ quán (`/api/ai/feedback`) và lời đánh giá được viết lại (`/api/ai/review`) ghi vào save ngoài hàng lệnh; giờ chúng xếp hàng như lời AI của giáo viên: các chạm sau chờ chúng xong, tối đa 4 giây (`AI_WAIT`, dùng chung với `VOICE_WAIT`), AI chậm không làm đứng màn hình, câu trả lời AI cũ hơn trạng thái đang hiện thì bỏ qua. Test mới: tests/fb_queue.mjs (tests/test_fb_queue.py).
- Hướng dẫn viên, bước chọn lộ trình trên điện thoại: thanh dưới bị ép 42% như thanh giáo viên trước đây, chỉ còn thấy ⏱ (🎟 xu và 😊 khách bị cắt), dòng gợi ý và nút dồn vào phần còn lại. Giờ ba con số nằm một dòng riêng đủ rộng trên cùng thanh, dòng gợi ý và nút dùng cả bề ngang (teach.css). Máy tính không đổi.
- Chỉ sửa phía trình duyệt: không có khóa lưu mới, không đổi máy chủ.

## WP-3 lệnh nghề + giáo viên

- Người chơi mới: chạm đầu tiên ở tiệm trà sữa (Ủ trà…) bị từ chối "Chọn một nghề trước nhé." (14 phiên ngày 06/10). Màn hình vẽ theo nơi đang mở (`focus`) nhưng lệnh gửi theo `current`, còn trống ở tài khoản mới. Trà sữa và Mẹ & bé giờ ghi rõ nghề; `api.command` (và lời AI phản hồi, đánh giá) mặc định theo `current`, không có thì `focus`, như app.js. Bộ kế hoạch nhập hàng / ngày mai đọc kho cũng vậy. Test mới: tests/command_career.mjs (kiểm cả mọi nghề không gọi `api.command` thiếu nghề).
- Giáo viên (góp ý #211, iPhone 390×797 "các lựa chọn cứ xếp chồng lên nhau"): trên điện thoại, 3 ô giáo án nằm ngay trên thẻ hoạt động thay vì trong thanh dưới (thanh bị ép 42%, các ô xếp thành cột, chữ và nút chồng lên nhau, cao 145 px → 57 px). Huy hiệu thứ tự nằm trong thẻ, không đè thẻ bên cạnh; cuộn tới nút chừa chỗ cho thanh dưới.
- Giáo viên: chạm bị dội (409 revision_conflict ở lesson_next / lesson_call / lesson_answer / cl_parent, 15 phiên). Lời AI viết lại câu học sinh / phụ huynh ghi vào save ngoài hàng lệnh; giờ nó xếp hàng: các chạm sau chờ nó xong, tối đa 4 giây (VOICE_WAIT), rồi đi tiếp. Không có khóa lưu mới, không đổi máy chủ.
## WP-2 Giúp việc + Chùa

- 🧹 Giúp việc: chưa cầm dụng cụ, chưa chọn chai, hay chai đang cầm đã cạn thì các chỗ lau bị khoá, có dòng nhắc cần làm gì (trước đây bấm vào là bị từ chối, hơn 400 lần một ngày). Chai cạn không chọn được nữa; cạnh nó có nút “🧴 Châm” để châm ngay từ kho. Hướng dẫn học nghề cũng nhắc châm chai trước khi dùng.
- 🧺 Giúp việc: nếu xe đồ nghề chưa soạn thì các tab phòng bị ẩn, thay bằng nút “🧺 Về soạn xe”. Nếu việc soạn xe buổi sáng đã bị huỷ (ví dụ do rời tiệm giữa ca), lệnh mới `gv_cart` mở lại việc đó (vẫn mã slot 0, không thêm khoá lưu), nên không còn bị kẹt cả ngày.
- 🛕 Chùa: ở bước xếp thứ tự hiện “Đã xếp k/n”, nút “Xong” chỉ hiện khi đã xếp đủ n việc. Máy chủ nhận đúng khi đủ n việc: thiếu một việc cần làm vì đã xếp nhầm việc không nên làm thì bị tính là lỗi “Quên mất việc …” chứ không còn bị từ chối.
- Không đổi tiền và không thêm bảng. Bản 1.9.2 đọc và chơi tiếp được bản lưu mới (đã kiểm validate_state).

# v1.9.2 — 2026-10-06: giao diện cũ trở lại

- 🎨 Theo chủ game: giao diện cổ điển (bản đồ phố 2D, cảnh từng tiệm, như 1.8.1) là giao diện mặc định. Máy chủ giữ nguyên 1.9.1 (quầy có nhân viên +50%, sửa tip kế toán ngày 1, dữ liệu Thư giãn trên đảo vẫn được giữ). Đảo 2.5D sẽ quay lại dưới dạng tuỳ chọn ở bản sau.
- Có gì mới: thay mục 1.9.0 (đảo 2.5D) bằng 1.9.2: giao diện quen thuộc, quầy +50%.
# v1.9.1 — 2026-10-06 (hotfix)

- Người chơi mới thi đạt kế toán ngày 1 rồi làm Kế toán doanh nghiệp / tập đoàn: nộp việc đầu tiên bị từ chối "Kết quả tip của công việc sai." (lời chào việc đầu thành tip 0 xu ở nghề không có tip tiền). Giờ là một món quà. Không có "Có gì mới".

# v1.9.0 — 2026-10-06

Có gì mới (chủ game duyệt): đảo 2.5D, Chỉ đường, quầy có nhân viên lãi hơn 50%.

## Phố 2.5D

- 🏝️ Cả game là đảo 2.5D (Phaser): mọi lần mở game đều đứng giữa phố; người chơi mới chọn ngoại hình, đặt tên rồi ra thẳng đảo. Đi tự do mọi hướng bằng cần điều khiển, phím W A S D / mũi tên hoặc chạm đường; chạm cửa tiệm là vào làm, "Ra đảo" để quay lại (đứng ngay trước cửa tiệm vừa làm). Đảo nhớ chỗ bạn đứng trên máy này.
- 🧭 Chỉ đường: chọn nơi muốn tới (mọi nghề, Nhà, Ngân hàng, Bảng xếp hạng, Phố nghề, Hội chợ, Lịch cưới, Quầy, Nhóm phố, Đi dạo, Hẹn hò, Hôn nhân, câu cá, chèo thuyền, bơi) hoặc gõ tìm; nhân vật tự đi theo đường vẽ sẵn, chạm đất hay di chuyển là dừng, tới nơi là mở luôn. Các nơi không phải tiệm có biển chỉ đường trên đảo.
- Cửa tiệm cho mọi nghề, kể cả thư viện, điều dưỡng, dầu khí, đường sắt, hải đăng, tổng đài cứu hộ, cứu hộ bể bơi, công an.
- Thanh trên (tên, ví, quỹ, cài đặt), thẻ việc tiếp theo, Sổ việc, Người quen, Thư giãn (câu cá, chèo thuyền, bơi: miễn phí, không tiền thưởng), Trò chuyện, góc nhìn và thanh dưới Phố · Công việc · Nhân vật · Túi đồ · Thêm. Điện thoại dọc và ngang: không nút nào đè nút nào, tránh tai thỏ; thông báo hiện ở khoảng trống phía trên cần điều khiển.
- Bỏ giao diện cũ (cảnh vẽ 2D của từng tiệm, bản đồ phố 2D): tải nhẹ hơn. Phần Phaser (~360 KB gzip) tải song song với khung hình đầu và chạy ngay sau; mạng chập chờn thì tự thử lại, rồi có nút "Thử lại".
- Hiện người chơi khác trên đảo: `LIVE_TOWN=1` cho dịch vụ live (mặc định tắt).
- Bản lưu: thêm khóa tùy chọn `journey.leisure` (chỉ có khi đã chơi câu cá / chèo thuyền / bơi); bản lưu cũ vẫn đọc bình thường, bản 1.8 đọc bản lưu mới cũng không lỗi. Không đổi tiền, không thêm bảng.
## Quầy: nhân viên bán lãi hơn 50%

- 🧑‍🍳 Ở Quầy của bạn, mỗi đơn nhân viên bán giờ được thưởng 110% phần lãi sau chi phí và thuế (trước đây 40%). Cùng giá, cùng hàng, tiền bạn thực nhận mỗi ngày từ quầy có nhân viên tăng khoảng 50% ở cả Xe đẩy, Sạp chợ và Ki-ốt.
- Đơn bạn tự đứng quầy, đơn online tự đóng gói và đơn khách là người chơi vẫn thưởng 40% như cũ. Quầy đang lỗ (ví dụ Ki-ốt chỉ một nhân viên) không có lãi nên không có thưởng: thuê đủ người hoặc chỉnh giá trước.
- Chỉ áp dụng cho đơn bán từ lúc cập nhật; tiền đã ghi sổ giữ nguyên. Ghi chú trong thẻ quầy và mục Hướng dẫn “Quầy của bạn” ghi rõ hai mức thưởng.

# v1.8.1 — 2026-10-06

## Nghề mới: Người gác hải đăng

- 🗼 Nghề mới ở chương 4 (Được tin cậy): giữ đèn biển Hòn Gió trên một hòn đảo đá cho Xí nghiệp Bảo đảm hàng hải Vịnh Ngọc, cùng chú Bảy Đèn và mèo Mun. Việc làm thuê: ứng tuyển, có lương ngày và thưởng mỗi việc làm đúng quy trình. Chứng chỉ Gác đèn biển giúp dễ được nhận.
- Ca sáng: tắt đèn đúng giờ theo giờ mặt trời mọc, thử sáu thiết bị, tắt mô-tơ rồi mới lau kính, ghi sổ dầu đúng số đo; hỏng thì tự xử lý hoặc báo đúng nơi (sổ trực, phiếu báo hỏng, báo đài khi ảnh hưởng tín hiệu đèn, còi).
- Quan trắc 7 giờ: đọc máy đo gió, mặt biển, các mốc tầm xa, áp kế; báo đài bốn số liệu; gió từ cấp 6 hoặc áp giảm nhanh thì phát cảnh báo cho tàu thuyền. Chạng vạng: thắp đèn đúng giờ, đếm chớp so với danh mục đèn, sương mù chạy còi, đèn sai thì báo đài, ghi sổ đúng sự thật.
- Canh biển: pháo hiệu đỏ giữa bão, tàu chết máy trôi dạt, người rơi xuống nước, tụi nhỏ thách nhau bơi ra đảo, tàu lao về bãi đá ngầm, tàu cố ra khơi khi có lệnh cấm, đánh cá bằng chất nổ. Nhìn kỹ, gọi tàu, ném phao, báo đài đúng mức (MAYDAY RELAY, PAN-PAN, biên phòng) và đúng phương vị, canh giữ mục tiêu. Không bao giờ tự lấy xuồng ra khơi; thuyền trưởng nghe hay không là tùy tính họ.
- Khách ra đảo (17 kiểu): đoàn có giấy, khách sống ảo đòi lên đỉnh tháp, cặp đôi đòi cầu hôn lúc nửa đêm, Vy Vlog livestream, kênh ma đòi tắt đèn, nhà văn xin ở một tuần, kayak lạc lúc chiều tối… Xem giấy tờ rồi tự chọn cách trả lời; khách nài thêm, có người lẻn lên cầu thang tháp. Người gặp nạn luôn được trú tạm.
- Tàu tiếp tế mỗi bảy ngày: đo bồn trước và sau, kiểm từng món, ghi món thiếu hỏng, ký đúng số lít dù chú Tư Lực nài ký đủ 200; trả giá giỏ đồ tươi của chú bằng tiền túi.
- Đời sống trên đảo: nhớ nhà tăng dần, đồ tươi hết giữa hai chuyến tàu; chơi với Mun, tưới vườn rau trên đá, gọi điện về nhà (má hỏi bao giờ lấy vợ lấy chồng). 35 chuyện oái oăm (ông Sáu Ghe xin quay đèn về phía lưới, anh Khôi đòi sơn tháp màu hồng, đếm hải âu, ký khống dầu, ở đảo thêm ba tuần, quấy rối trên kênh 16…), 17 chuyện bất ngờ, 6 tình huống, truyện nghề “Cái giẻ da của chú Bảy”, thang thăng tiến 4 bậc, cảnh đảo và tòa nhà ở Ngoại ô.

## Nghề mới: Nhân viên trực tổng đài cứu hộ

- 📞 Tổng đài Cứu hộ phường Mây (mở ở chương 4 “Được tin cậy”, việc làm thuê): trực đường dây cháy, ngập, tai nạn, kẹt thang máy, thú cưng mắc kẹt, cấp cứu cùng chị Thảo. Chứng chỉ Tiếp nhận cuộc gọi khẩn cấp giúp dễ được nhận; thang thăng tiến 4 bậc.
- Nhận ca: gọi bộ đàm sáu đội, đánh dấu đội tạm ngưng trên bảng đội; quên đánh dấu thì lát gọi đội đó không ai trả lời.
- Mỗi cuộc gọi: hỏi địa chỉ trước, rồi chuyện gì, mấy người, nguy hiểm gì, số gọi lại; người gọi không biết chỗ thì hỏi mốc, gửi định vị, nhờ người đi đường; người đang hoảng thì trấn an (mỗi người hợp một cách, quát là hỏng). Cuộc nghi ngờ (giọng cười, im lặng, bé con, ông Ba gọi lần thứ mười) phải nghe, hỏi kỹ, gọi lại rồi mới quyết: có cuộc thật, có cuộc đùa, do tính ẩn của người gọi.
- Tự chọn mức ưu tiên và đội để gửi, hoặc chuyển đúng nơi với giọng mình chọn (nhẹ, dứt khoát, gắt): khách say đòi taxi, mèo kẹt trên cây từ ba giờ sáng, karaoke, DJ xin “một câu”, “người quan trọng” đòi ưu tiên, gọi nhầm đặt phở… Gửi xe cho chuyện không khẩn thì đội bị giữ chân, ca thật sau phải chờ phường bên.
- Trong lúc chờ: đọc thẻ hướng dẫn an toàn (có thẻ nghe hợp lý mà nguy hiểm: dội nước vào chảo dầu, đi thang máy khi cháy, tháo mũ bảo hiểm), giữ máy với người gọi một mình. Mùa mưa nhiều đường dây réo cùng lúc: nghe nhanh, xếp ưu tiên. Không bao giờ có hướng dẫn cho uống thuốc.
- 42 chuyện oái oăm quanh tổng đài (sếp ép KPI, đồng nghiệp rủ cúp máy khỏi hỏi, tắt ghi âm, sửa giờ nhật ký, fan cuồng giọng tổng đài, họ hàng xin ưu tiên…), 14 chuyện bất ngờ ở phòng trực, 6 tình huống, truyện nghề “Chiếc tai nghe của chị Thảo”, sổ nhật ký cuối ca, cảnh phòng trực và tòa nhà ở Phố dịch vụ.

## Nghề mới: Nhân viên cứu hộ hồ bơi

- 🛟 Nghề mới **Nhân viên cứu hộ hồ bơi** ở Hồ bơi Sóng Xanh (chương 4 “Được tin cậy”): ứng tuyển, phỏng vấn, thử việc; lương ngày cộng thưởng nhỏ cho mỗi việc làm đúng. Anh Hải kèm ba việc đầu, nhắc trước mỗi lỗi một lần.
- Mở hồ: kiểm từng món (độ trong của nước, que thử Clo & pH so “Bảng mẫu Sóng Xanh”, nắp hút đáy, phao ống, phao tròn & sào, hộp sơ cứu, biển độ sâu, điện thoại khẩn), tự gõ số vào sổ nước, tự sửa hoặc báo đúng người; chưa an toàn thì hoãn mở. Cứu hộ không tự đổ hóa chất.
- Canh hồ có hẹn giờ: quét đủ năm khu trong một phút, thổi còi đúng luật (chạy trên bờ, nhảy cắm đầu chỗ cạn, chai thủy tinh, trẻ không người lớn, nhào lộn, quay lén, giả vờ kêu cứu, dìm đầu…). Người đuối nước thật thì im lặng: báo động, gọi hỗ trợ, với hoặc ném trước, xuống nước luôn mang phao ống, xem thở rồi sơ cứu; không bao giờ dốc ngược.
- Soát người ở cổng (say bia, vết thương hở, đau mắt đỏ, không mũ bơi…), lớp bơi trẻ em (bơi thử rồi mới phát vòng tay, bé Bon nói dối biết bơi), sơ cứu không dùng thuốc, dông chiều (lên bờ, trú sảnh có mái, đếm người, ba mươi phút sau tiếng sấm cuối mới mở lại dù sếp giục).
- Hơn năm mươi người oái oăm quanh hồ: ông Tư không chịu đội mũ bơi, cô Hằng nhảy aerobic ở làn nhanh, Kha nhào lộn quay TikTok, phụ huynh dán mắt điện thoại, đại gia đòi làn riêng, khách tán tỉnh xin dạy riêng, quản lý không cho đóng hồ vì doanh thu… Bạn tự chọn giọng, lời nói và báo ai; chiều theo không bao giờ có thưởng. Cuối ca tự ghi sổ trực từ những gì thật sự xảy ra.
- Chứng chỉ Cứu hộ hồ bơi giúp dễ được nhận; thang thăng tiến Cứu hộ chính → Quản lý an toàn hồ bơi.

## Nghề mới: Công an phường

- 👮 Nghề mới **Công an phường** ở Công an phường Mây (chương 4 “Được tin cậy”, mở cùng điều dưỡng, gác chắn): ứng tuyển, phỏng vấn, thử việc; lương ngày cộng thưởng nhỏ cho mỗi việc làm đúng. Nghề người chơi xin, giữ nhẹ nhàng: giúp dân, không có vũ khí hay chiến thuật, không trích luật thật.
- Một ca gồm: giao ban (đọc sổ trực ban, chọn việc gấp làm trước), bàn cư trú (xem từng giấy, nhận hoặc chỉ đúng giấy cần bổ sung), đồ thất lạc (kiểm đếm cùng người nhặt, hỏi kỹ người tới nhận; có người nhận vơ), hòa giải hàng xóm (karaoke, xe đậu chắn cửa, tường nứt, con chó Lu, cây xoài: nghe từng bên rồi tự đề xuất, hai bên tự quyết theo tính), trẻ lạc (dỗ bé, không đăng ảnh, xác minh người đón), tuần tra chợ, cổng trường, hội chợ, đám cưới (nhắc trước, biên bản sau, nguy hiểm thì xử lý ngay), nói chuyện chống lừa đảo cho các cụ, điện thoại trực ban (ai gặp nguy đi trước, gọi lại trước khi coi là tin báo sai).
- Hơn bốn mươi người “oái oăm”: phong bì “cà phê”, cháu “sếp quận”, karaoke nửa đêm, cô Thoa ngày nào cũng có “người khả nghi”, Kha livestream cả bàn tiếp dân, chú say quậy, bà Năm mang chè ngồi kể chuyện cả tiếng, tố bừa nhà bên, sếp đòi đủ chỉ tiêu biên bản… Bạn tự chọn giọng, lời nói và báo ai; nhận phong bì hay chiều theo không bao giờ có thưởng.
- Cuối ca tự ghi sổ trực ban từ những gì thật sự đã xảy ra (dòng “lập thêm biên bản” cho đủ chỉ tiêu là ghi khống). Anh Định kèm ba việc đầu; Chứng chỉ Tiếp dân & hòa giải giúp dễ được nhận; thang thăng tiến Cán bộ khu vực chính thức → Phó trưởng Công an phường; truyện nghề “Cuốn sổ hẻm của anh Định”.

# v1.8.0 — 2026-10-06

Có gì mới (chủ game duyệt): "Cập nhật toàn bộ UI UX", "Thêm Top tài phú trên Bảng xếp hạng".

## Ông Hai 10.000 xu (đã lên trước ở 1.7.16)

- 🪨 Ô ăn quan: thắng Ông Hai được 10.000 xu (trước 500). Bé Bi giữ nguyên (50 xu, cách chơi cũ).
- Ông Hai đi trước và mạnh hơn hẳn: tìm kiếm alpha-beta có bảng chuyển vị, ưu tiên nước ăn, nước "sát thủ", đào sâu dần đến khoảng 8 lượt, giải chính xác khi gần hết quân. Ngân sách tính bằng số nước mô phỏng (20.000), không theo đồng hồ; không cố ý đi nước kém.
- Bản lưu không đổi khóa; bản 1.7.15 cũ vẫn đọc được ván thắng 10.000 xu và ván Ông Hai đã đi trước.

## Sửa: kiểm tra theo phần (tắt mặc định)

- Kiểm tra rút gọn (SCOPED_CAREER_VALIDATION): tiệm có hồ sơ an ninh đang mở, khi sổ an ninh không đổi mà tiệm vẫn bị tính lương/sổ thu chi, không còn bị từ chối nhầm "Tham chiếu hồ sơ an ninh sai." (mã hồ sơ bỏ qua vẫn được đếm). Mặc định vẫn tắt; bật lên thì kết quả giống hệt kiểm tra đầy đủ.

## Nghề mới: Cán bộ thư viện – lưu trữ

- 📚 Thư viện – Lưu trữ phường Mây (mở ở chương 4 “Được tin cậy”): phụ cô Nguyệt giữ sách và hồ sơ của phường. Sáng xem ẩm kế kho (trên 60% bật máy hút ẩm), soi bẫy mọt, chuột, gián, mở phòng đọc.
- Quầy mượn trả: tra ký hiệu, kiểm thẻ (hết hạn, đủ 3 cuốn, còn nợ phí), sách tra cứu chỉ đọc tại chỗ, đặt trước sách đang có người mượn; gợi ý sách theo gu ẩn của bạn đọc.
- Trả sách: tự đề xuất tiền phạt (1 xu/ngày, tối đa 15, cộng phí hỏng), bạn đọc tự quyết theo tính (trả, mặc cả, khất, cãi); miễn khi có lý do chính đáng, ghi sổ nợ, đòi nợ; sửa sách đúng cách.
- Biên mục: xếp 10 lớp, ký hiệu tác giả, lọc sách tặng mốc, lậu, lỗi thời mà giữ sách cũ quý. Phòng đọc: nhắc ồn ào, ăn uống, ngủ ngáy, đôi bạn tình tứ, hút thuốc cạnh kho… mỗi người phản ứng một kiểu.
- Kho lưu trữ: tập huấn trước lượt đầu, kiểm giấy tờ, mức tiếp cận, đúng hộp, tìm hồ sơ kẹp nhầm, cấp bản sao (bản gốc không rời kho), ghi sổ. Hơn 60 kiểu nhờ vả oái oăm, 16 chuyện bất ngờ, 6 tình huống, truyện nghề, Chứng chỉ nghiệp vụ lưu trữ.

## Nghề mới: Thợ dầu khí

- Nghề mới 🛢️ Thợ dầu khí (chương 4, cạnh phi công): kỹ thuật viên vận hành trên giàn Hải Âu của Dầu khí Sóng Bạc, việc làm thuê lương đi biển cao. Đợt 14 ngày: ngày bay trực thăng ra giàn, bốn ngày ca 12 tiếng, ngày bàn giao về bờ; bão tới thì ở lại thêm trên giàn hoặc chờ ở bờ.
- Ngày bay: soạn túi (không bật lửa, bình xịt, dao, rượu, thuốc lá điện tử, tối đa 15 kg), mặc đồ bơi giữ nhiệt, áo phao, bình thở, chụp tai, trả lời câu thoát hiểm trực thăng, sương mù thì ngồi chờ. Lên giàn: gắn thẻ bảng đếm người, nhận xuồng cứu sinh theo biển cửa phòng, nhớ ba tiếng còi.
- Mỗi ca: họp an toàn (đồ bảo hộ, thử khí mẫu máy đo, mối nguy), bảo dưỡng có giấy phép (đúng loại giấy phép, đối chiếu việc cẩu, khóa và treo thẻ từng điểm, xả áp, kiểm về không, đo khí, người canh lửa/canh bồn), đi tuần đọc đồng hồ, báo động đi ngược gió về đúng xuồng. Có lúc van lọt, khí rò, thiếu ôxy, cẩu trên đầu, cầu dao ghi nhầm: ✋ Dừng việc luôn đúng, dừng mà không có gì sai cũng không bị trừ; báo suýt sự cố được cảm ơn.
- Ngày về bờ: bàn giao thật cho ca sau, rồi cả nhà nhờ tiền: hỏi rõ, gửi số mình chọn hoặc không gửi, mặc cả với người nhà; có khoản cần thật, có khoản là trò lừa.
- 42 chuyện oái oăm (sếp ép bỏ bước đo khí, nhà thầu ký khống checklist, bạn cùng phòng ngáy, chê cơm nhà ăn, Má gọi lúc mất sóng, em đòi điện thoại mới, anh họ rủ góp tiền ảo, ở lại thêm ca, quấy rối và bắt nạt…), 15 chuyện bất ngờ theo ngày đi biển, 6 tình huống; chứng chỉ An toàn cơ bản ngoài khơi, thang thăng tiến 4 bậc, truyện nghề, hướng dẫn, cảnh giàn khoan và tòa nhà ở khu Sân bay.

## Nghề mới: Gác chắn đường sắt

- Nghề mới ở chương 4 (Được tin cậy): nhân viên gác chắn đường ngang Bến Mây kiêm tuần đường cho Xí nghiệp Đường sắt Sông Mây. Việc làm thuê: ứng tuyển, có lương ngày và thưởng mỗi chuyến gác đúng quy trình. Chứng chỉ An toàn đường ngang giúp dễ được nhận.
- Nhận ca: đọc sổ giao ca, thử từng thiết bị (chuông đèn, cần chắn, bộ đàm, cờ đèn…), hỏng thì tự xử lý (thay pin, lắp tay quay) và báo đúng nơi: sổ giao ca, phiếu báo hỏng hay gọi ga.
- Mỗi chuyến tàu: nghe ga gọi và nhắc lại lệnh, dẹp người trên ray (khách chụp ảnh, tụi nhỏ, chú Hớn ngủ quên, con bò, xe ba gác kẹt…), chuông trước chắn sau, hạ chắn đúng lúc, giữ chắn trước gần 30 kiểu người đòi qua (xe ôm, đám tang, xe hoa, xe cứu thương, người dúi tiền, TikToker…); bạn tự chọn cách trả lời, người ta tự quyết theo tính. Không dẹp kịp thì báo dừng tàu: luôn đúng.
- Tàu chậm giữa chừng, tàu thứ hai chạy ngược chiều, toa thiếu đèn đuôi, bầu trục bốc khói: nhìn hết đoàn tàu, hỏi ga trước khi nâng chắn, ghi sổ nhật ký đúng sự thật.
- Tuần đường Km 7 – Km 8: bu lông lỏng, tà vẹt nứt, đá ba-lát trôi, ray nứt, ray cong vì nắng, đèn tín hiệu tắt, nong ớt trên ray… tự xử lý, cắm cờ phòng vệ, điện khẩn hay ghi đúng phiếu.
- Chuyện oái oăm quanh chòi gác: lời mời “có ý”, quấy rối, sếp bảo sửa giờ cho đẹp, đồng nghiệp nhờ ký sổ khống, gác thêm ca đêm; ca đêm làm mệt, mệt thì phải tỉnh táo trước khi nghe lệnh. Có truyện nghề “Cái còi đồng của chú Sáu”.

## Nghề mới: Điều dưỡng

- 🏥 Nghề mới **Điều dưỡng khoa Nội** ở Bệnh viện phường Lá Sen (chương 4, mở cùng nhà thuốc, phi công): ứng tuyển, phỏng vấn, thử việc; lương ngày cộng thưởng nhỏ cho mỗi việc làm đúng. Cũng là nghề “bệnh viện” người chơi xin.
- Một ca gồm: nhận giao ca (đọc sổ, chọn giường xem trước), đo dấu hiệu sinh tồn rồi tự gõ số vào phiếu, so thẻ báo động và báo bác sĩ, cho thuốc theo y lệnh (hỏi tên + ngày sinh, vòng dị ứng, nhãn khay, đường huyết, biển nhịn ăn), chuông gọi, phân loại ở quầy tiếp đón theo thẻ màu, chuẩn bị thủ thuật (giấy cam đoan, nhịn ăn, trang sức), ra viện (giấy ra viện, BHYT, rút kim luồn, dặn dò, nhờ nhắc lại).
- Chị Hoa kèm ba việc đầu, nhắc trước mỗi lỗi một lần. Người bệnh có quyền từ chối: hỏi, giải thích, báo bác sĩ; ép là lỗi. Không có liều thuốc nào trong game: bác sĩ quyết điều trị.
- Hơn bốn mươi người “oái oăm” quanh khoa: phong bì, 500 xu đổi giường đẹp, đòi bác sĩ giỏi nhất, cả họ vào thăm, “thần y” mang thuốc nam, quay clip, khách say ca tối, đồng nghiệp rủ làm tắt, ép trực thêm ca, người nhà xin giấy nghỉ ốm giả… Bạn tự chọn giọng, lời nói và báo ai; chiều theo không bao giờ có thưởng.
- Cuối ca tự viết sổ giao ca từ những gì thật sự đã xảy ra (ghi khống bị trừ điểm hồ sơ). Chứng chỉ An toàn người bệnh giúp dễ được nhận; thang thăng tiến Điều dưỡng chính → Trưởng phòng Điều dưỡng.

## Kiểm tra giao diện trước phát hành (tiệc cưới, hội chợ, màn live)

- Tiệc cưới khi xoay ngang: lễ đường lại hiện trọn cả sân (cô dâu chú rể, sân khấu, múa lân, pháo hoa), không bám theo khách đứng ở cổng hoa nữa; thanh trên cùng gọn một hàng, mâm cỗ một hàng 8 món, bảng chọn nhạc 4 bài một hàng.
- Hội chợ xoay ngang: bản đồ hội chợ không lấn xuống thanh vuốt ở đáy màn hình.
- Điện thoại hẹp (360 px): tiêu đề dài nhường chỗ cho số xu ở thanh trên (Bày trí phòng không còn cắt "860 xu").

## WP1 Nhân viên tiệm & nhập hàng

- Nhân viên bán theo cả danh mục hàng của tiệm (Mẹ & Bé, tạp hóa, thú cưng, trái cây, hoa, trà đá, kem, cơm, phở, mì cay, cà phê, salon, nail, sửa chữa…), chỉ món còn hàng, ưu tiên món còn nhiều; hết thỏ bông vẫn bán món khác.
- Đơn riêng của nhân viên tính theo giá kệ của chính nghề và luôn có lãi sau lương, vật tư; món lãi mỏng thì bán theo lố (vài ký gạo, chục trứng), kem bán nguyên hộp 1,2 kg thay vì giá một viên.
- Sổ tiệm hiện đơn tiếp theo: giá thu, lương, vật tư, giá vốn, lãi ước tính; tiền vào quỹ nghề; khi đội dừng thì nói rõ đang hết món gì hoặc giá không đủ bù lương.
- Tiệm Mẹ & Bé đặt đơn gộp nhiều mã một lần (tối đa 12 mã, một chuyến xe, trả một lần).
- Đơn gộp ở kho: tối đa 20 dòng, nhiều size của cùng một món trong một đơn, 12 đơn đang giao cùng lúc; báo rõ tiền nhập hàng trừ vào quỹ nghề.

## WP2 Đánh giá, kiểm duyệt & an toàn

- Đánh giá NPC: mọi đánh giá đều báo cáo được. Đánh giá lạc đề, nhầm quán, chưa ghé, cài cắm, chê chuyện ngoài lề và "hùa theo" bị gỡ khỏi điểm trung bình (vẫn giữ, có đánh dấu). Báo cáo không được duyệt giữ nguyên sao, không kéo thêm 1★; hùa theo không bao giờ kéo hùa theo.
- Khách lạ viết đánh giá là khách cùng nghề; đánh giá "nhầm quán" ít hơn. Bù xu cho đánh giá không thể đổi (nhầm quán, chưa ghé…) được cảnh báo trước, không trừ xu; khung trả lời ghi "khách trả lời sau ~2 lượt làm".
- Đánh giá giữa người chơi (Phố nghề, dịch vụ chỗ làm): chỉ tính đánh giá mới nhất của mỗi người, tài khoản từ 3 ngày tuổi, không tính đánh giá trong 24 giờ quanh lúc chủ quán chuyển xu/tặng quà xu. Không xóa đánh giá nào.
- Tên hiển thị: đổi tên ở Cài đặt và Hành trình dùng chung bộ lọc tên tài khoản, chặn thêm cách viết không dấu/viết liền (concac, dcm…). Quản trị có danh sách tên vi phạm và nút "Đổi tên an toàn"; không tự đổi tên ai.
- Chat: nhắc nhở an toàn thân thiện (một lần) khi tin nhắn có hẹn gặp, địa chỉ, số điện thoại, zalo/fb/ig/tiktok; lý do báo cáo "An toàn / trẻ vị thành niên" lên đầu hàng chờ quản trị; khóa chat theo phút và chế độ chậm cho từng người hoặc cả Cả phố; @tên người chơi đang có trong Cả phố không bị che. Không tự cấm ai.
## WP3 Nghề & hàng tiệm

- Tiệm áo, salon: bill/phương án lố ngân sách mở 💬 Trao đổi: gợi ý món rẻ hơn hoặc dời dịch vụ, xin thêm ngân sách (khách tự quyết theo tính, chỉ hỏi một lần), bớt giá trong mức chủ cho, hoặc nói thật. Lờ khách hay thất hứa vẫn bị trừ.
- Tiệm áo thêm 14 món: đầm maxi, váy babydoll, set áo + chân váy, blazer, cardigan, polo, chân váy chữ A, quần tây, quần short, sneaker, sandal, túi xách, bông tai, khăn lụa; khách quen hay dặn thêm (lấy thêm món, muốn mặc đầm, không jean, giày đi biển). Món mới nhập qua Kho; tủ đồ có thêm đồ tương ứng.
- Lớp học: lời học trò hiện ngay sau tối đa 2 giây (AI viết lại thì thay sau); phiếu cuối tiết có dòng hướng dẫn chấm.
- Giữ trẻ: tính bé hiện rõ dưới “🙂 Chào bé”, chào sai thì nhắc đúng tính bé.
- Buồng ảnh: mã phòng gõ được R, S, F, X, J, W, DD dù đang bật Telex.
- Giao hàng: đơn mới hiện giờ hẹn trước khi nhận (ngày 1: giao trong bao nhiêu phút).
- Thú cưng: thẻ việc có nút Khép ca khi đang để lát nữa, hết giờ hoặc thiếu hàng (kèm dòng “Hết …”).
- Homestay: 📥 Hộp đơn OTA có huy hiệu số đơn trùng và hướng dẫn xử lý.
## WP4 Thăng tiến dài hơn

- Phi công: cấp hàm có gạch/sao (Cơ phó cấp thấp 1 gạch → Trưởng đội bay 4 gạch 1 sao), thêm Phó Giám đốc, Giám đốc Khối khai thác bay và Phó Tổng Giám đốc (trần).
- Giáo viên lên tới Hiệu trưởng. Các nghề khác giữ thang 4 bậc; không ai bị hạ bậc, bậc cũ giữ nguyên.
- 🏢 Phòng điều hành cho bậc lãnh đạo: điều phối chuyến bay/phân công, nhân sự NPC (nói chuyện, khen, nhắc nhở, cảnh cáo, kiểm điểm, đình chỉ, thăng/giáng chức, tăng/hạ bậc lương) theo tính cách ẩn, việc khó cần quyết; ảnh hưởng đúng giờ, phàn nàn, tinh thần, quỹ lương và thưởng điều hành.
- Bản lưu: bậc trên 4 và phòng điều hành nằm ở khóa phụ, bản cũ vẫn đọc được khi lùi phiên bản.
## WP5 Nhà, nội thất & cuộn ổn định

- Thêm 55 món nội thất cho mọi phòng (phòng khách, ngủ, bếp, tắm, ban công, sân vườn) và đồ nhỏ: đèn, cây, thảm, khung ảnh, kệ, đồ chơi, đồ bếp; kệ mới "Bếp & ăn uống", ba bộ góc mới, máy chiếu dải ngân hà phủ sao lên tường.
- Xoay mặt trước/mặt sau cho 29 món (giường, bàn, ghế, tủ, tủ lạnh, piano…), không chỉ ti vi và sofa.
- Mỗi phòng bày được gấp rưỡi số món; khi đầy, báo đúng số món tối đa và cách bày thêm.
- Nhà của bạn có mục "Đồ đạc của bạn": mọi món đang có (nội thất từng phòng và trong túi, quần áo, xe, đồ ăn trong tủ lạnh, giấy dán tường) kèm tên và thông tin.
- Thanh trượt đồ trong Bày trí kéo được tới món cuối, nút ‹ › không bị khóa khi đang chờ máy chủ, không nhảy về đầu khi cập nhật.
- Danh sách trong các bảng không còn giật về đầu khi đang cuộn hoặc sau khi bấm; chi tiết đánh giá trên màn rộng cuộn được.
- Không đổi tiền hay dữ liệu cũ; bản lưu mới vẫn đọc được trên bản 1.7.15 (đồ vượt sức chứa cũ và hướng xoay mới nằm ở khóa riêng).
## WP10 💰 Top tài phú

Chủ game (05/10): "thêm top tài phú nhé … thêm top tài phú cho toàn server". Không có "Có gì mới", không thông báo. Chuyển từ nhánh lb-wealth-17 sang đúng cây đang chạy (7b3b72c, 1.7.15) và tính thêm tiền/tài sản có từ 1.5–1.7.

- Bảng xếp hạng có tab mới 💰 **Tài phú** (`board=wealth`): ai giàu nhất phố. Điểm = tài sản ròng tính trên server từ bản lưu (`game/wealth.py` `worth()`):
  - đúng như "Tiền của bạn" (`public/js/v4/wealth.js` pockets(): Tổng tài sản − Tổng nợ): ví (âm thì là nợ), quỹ mọi nơi làm đã mở, ngân hàng (tài khoản + tiết kiệm không kỳ hạn + các sổ có kỳ hạn − nợ vay còn lại − dư nợ thẻ), mọi căn nhà đang sở hữu theo giá thị trường hôm nay (`housing.value_of` với hệ số thị trường nhà lúc mua) − nợ vay mua nhà còn lại;
  - cộng thêm những gì bảng tiền chưa liệt kê nhưng bản lưu giữ sẵn bằng số: sổ tiết kiệm Mây (`invest.saving.balance`), Mây Coin và vàng theo **giá vốn** đã lưu (`invest.coin.basis` khi còn `units`, `vang.cost` khi còn `phan`: số xu đã trả, gồm phí/chênh lệch; không tra giá thị trường), mọi xe theo giá cửa hàng mua lại (`garage.sell_price`), mọi quầy riêng theo giá sang nhượng (`quay.sell_back`: giá chỗ × 50 % + đồ lắp × 30 % + két + vốn), trừ tiền quầy còn nợ (`due`, phạt chưa nộp) và vay nóng hội chợ (`fair_cash`: khoản đang vay + nợ còn lại).
  - Mua coin/vàng không đổi tài sản ròng (xu chỉ chuyển túi); bán ra thì tài sản ròng đổi đúng bằng phần lãi/lỗ đã chốt.
  - Không tính: Quỹ chung vợ chồng (ở ngoài bản lưu, của hai người), tiền đang chuyển khoản / lương giữ trước / tiền thuê nhà trả trước (nằm trong bảng dữ liệu, không trong bản lưu). Dòng luật trên bảng nói rõ điều này.
- Chỉ người chơi theo câu chuyện; tài sản ròng ≤ 0 thì không có dòng. Bằng nhau: ai nhiều tổng tài sản hơn, rồi ai đạt mức đó trước. Ẩn tên / khách tự bật giống các bảng khác. Số trên bảng cập nhật mỗi khi bản lưu được ghi (giá nhà theo lịch đổi thì bảng theo ở lệnh kế tiếp).
- Danh hiệu tuần (top 1 / 2–3 / 4–10): 💎 Đại gia của phố, 💰 Đại gia mới nổi, 🤑 Hội nhà giàu; cập nhật hằng ngày, chốt tuần 0:00 thứ Hai như các bảng khác.
- `leaderboard.VERSION` 2 → 3: lần khởi động đầu tiên dựng lại mọi dòng ở nền (danh hiệu tuần chờ dựng xong). Không có DDL, không đổi bản lưu (bảng chỉ đọc bản lưu).
- Ghi bảng: khi các bảng của một bản lưu không đổi và bản tóm tắt trước đó được biết là khớp với bảng (`lb.synced()`: tiến trình này vừa ghi các dòng đó, hoặc lệnh trước không đổi số nào trên các dòng đã khớp; cùng revision), chỉ ghi những dòng có số thay đổi (tài phú đổi theo hầu hết lệnh có tiền: 1 câu lệnh thay vì 1 câu/bảng). Thêm hoặc mất một bảng, lệnh đầu tiên của tiến trình với bản lưu đó, hay bảng hội chợ cần tự chữa (`lb.heal`): đồng bộ đủ như cũ.
- Tab trên điện thoại (390 px): 4 tab xếp 2 × 2, có 💍 Khách mời thì 5 tab xếp 3 + 2, đủ chữ.
- Thẻ bạn bè (`game/friends.py`) chỉ lấy nghề chính từ bảng nơi làm (bảng danh hiệu, tài phú, hội chợ `fair…xu` không lọt vào).
- Hướng dẫn › Bảng xếp hạng thêm dòng Top tài phú (`public/js/tutorial/guide-content.js` tạo lại). Chưa có bản tiếng Anh cho các dòng mới.
## WP6 Quầy, hội chợ, tiền & luồng

- Quầy: camera, chuông, két sắt, bảo vệ giảm đúng khả năng bị trộm như nhãn ghi; két sắt giữ lại ít nhất nửa két. Thẻ quầy hiện "Rủi ro trộm" và chi phí mở quầy chạy trực tiếp.
- Thuê bạn: lời mời có huy hiệu trong game, lời mời chưa nhận được hiện lý do; nói rõ hàng nhập dùng quỹ nghề của người làm thêm; ghi "chỗ đứng" thay cho số người.
- "3 ngày tuổi": nói rõ tài khoản của ai, còn bao nhiêu giờ (đời thực), phiên khách có câu riêng; kết bạn từ chat báo lý do cụ thể.
- Bỏ dở việc: máy chủ kiểm tra trước rồi mới hỏi "Vẫn đi", không lặp hộp thoại; "Xin nghỉ việc" chờ một nhịp mới bấm được "Đồng ý".
- Bảng giá tiệm vẽ đủ món cho mọi nghề có bảng giá (quán cơm, phở, tạp hóa…). Kết kỳ thuế có thông báo kèm phép tính.
- Hội chợ: khoảng 65% ván may rủi là thắng (thắng liền 4 ván thì nguội còn 55%); phóng dao màn mới nhẹ hơn, tính giờ theo lúc chạm; ném vòng rơi đúng gần chỗ ném; lô tô chưa đủ hàng chỉ nhắc, không phạt.
## WP8 Điện thoại gọn + xoay ngang

- Điện thoại dọc: đầu màn hình làm việc còn một hàng (~56 px: tên, quỹ, ❔ ⋯ ✕); 16 thanh nút của các nghề dùng chung một thanh gọn (~60 px) sát đáy, có khoảng cuộn khớp.
- Thông báo trên màn làm việc nằm trong hàng tiêu đề, không còn đè nút hay thanh nút; chỉ một dòng, chạm ▾ để xem hết.
- Màn chính: bỏ "Đổi nghề" trùng (vẫn ở Thêm), thẻ việc 64 px với "Khách ghé" bên cạnh, thanh dưới 64 px: cảnh được ~70% chiều cao.
- Tab Chuẩn bị, khung bên, ô xem trước tủ đồ không còn ghim trên điện thoại; menu Thêm 3 cột, cao tối đa 60%, thanh dưới vẫn thấy; nút chạm tối thiểu 44 px.
- Xoay ngang: thanh nghề chuyển sang cột trái (kèm chat), thanh trên 44 px, thẻ việc nổi góc phải, Thêm thành ngăn kéo bên phải; màn hình làm việc tràn toàn màn, hai cột như máy tính, chừa tai thỏ và thanh home.
- Đi dạo xoay ngang: phố được vẽ to hơn và camera đi theo nhân vật; khi bàn phím mở (kb-open) đầu màn hình gọn lại, ô chat tối đa 2 dòng, chat/đi dạo chỉ còn tin nhắn và ô nhập.
- Bản đồ phố gọn hơn trên điện thoại (mục tiêu thu nhỏ, ô tìm đường một hàng, nút phóng to tránh thanh home); hội chợ xoay ngang bỏ dây cờ, bản đồ to hơn. Máy tính bảng và máy tính giữ nguyên.
## WP7 Phase-0 performance

- Lệnh nhanh hơn với bản lưu lớn: nghề chỉ đổi phần tiền/sổ thu chi do nhân viên chạy đơn thì chỉ kiểm tra lại phần đã đổi (sổ thu chi: chỉ các dòng mới); bản lưu ghi ra giữ nguyên từng byte.
- Ảnh chụp chỗ làm cho bạn bè ghé (work visits) được tính trước khi khóa bản lưu; khóa giữ ngắn hơn.
- Bản lưu đi thẳng dạng UTF-8 từ lúc đọc tới lúc ghi PostgreSQL, không giải mã/mã hóa lại 1–7 MB mỗi lệnh.
- Cưới hỏi, chuyển khoản, quỹ đôi, thuê quầy, ghé chỗ làm: chỉ kiểm tra lại các nghề bị thay đổi thay vì cả 41 nghề.
- Kiểm tra toàn bộ định kỳ mỗi 200 lệnh (VALIDATE_FULL_EVERY, trước 50); mã BUILD chỉ đổi khi mã di trú/kiểm tra bản lưu có thể đổi (lên số phiên bản, hướng dẫn, quan sát hệ thống không còn ép kiểm tra lại mọi bản lưu).
- Thêm scripts/bench_command.py đo từng pha của một lệnh trên bản lưu tổng hợp 225 KB / 1.4 MB / 3 MB.

# 1.7.15 — 2026-10-05

- Coin/vàng chung thị trường theo giờ thực: 10 phút một phiên, 1 giờ một ngày thị trường; giữ tài sản và giá vốn khi chuyển đổi.
- Tối ưu sổ giao dịch khi xử lý nhiều đơn NPC, kiểm tra lịch sử và vẽ hội chợ/buồng ảnh/cào vé.
- Quầy hiển thị khách thật và lượt mua vừa xác nhận; giữ bảng doanh thu, thông tin, vị trí cuộn khi cập nhật.
- Cược trò có phí tối đa 500 xu/lượt; phóng dao mới tăng số dao/tốc độ bia, giữ xác suất thắng và ván đang dở.
- Bổ sung đề nghị lương gấp đôi của NPC và các lựa chọn chi phí kinh doanh; giữ kiểm tra số dư và chống trừ lặp.
- Có gì mới gồm đúng bốn dòng chủ game cung cấp; không phát lại quà.

# 1.7.14 — 2026-10-05

- Quầy có trạng thái mở/đóng thật, giữ đơn đã nhận và không cộng bù khách trong thời gian đóng.
- Thị trường thay đổi lượng khách; bổ sung thuế thu nhập, phí môi trường, gói bảo vệ và vật dụng giảm rủi ro có tác dụng cụ thể.
- Rủi ro trộm/hack tăng theo bậc tài sản, thêm thiết bị phòng vệ; giữ giới hạn thiệt hại và không truy thu sự cố cá nhân offline.
- Nhân viên NPC có chuyện tăng lương, cưới, xin nghỉ; chất lượng phục vụ tạo đánh giá và lịch sử chi phí rõ ràng.
- Phát hành yên lặng: không thêm Có gì mới, không phát lại quà.

# 1.7.13 — 2026-10-05

- Giảm tải khi ghé chỗ làm và xử lý đơn nhân viên tích lũy; giữ nguyên tiền, lịch sử và bảo vệ giao dịch.
- Chat giữ danh sách tin khi nội dung không đổi; Nhà không khóa điều hướng trong lúc tải chợ thuê.
- Không thêm Có gì mới hoặc phát lại quà.

# 1.7.12 — 2026-10-05

- Thêm tình huống có lựa chọn cho chủ tiệm và Quầy riêng; camera giảm nguy cơ trộm, lịch sử lưu kết quả xử lý.
- Chủ nhà tự đặt giá cho NPC hoặc người chơi thuê; hợp đồng trả trước, gia hạn và nội thất nhà thuê riêng.
- Tin bất động sản trong game ảnh hưởng giá bán lại và giá thuê, có giai đoạn hồi phục.
- Phát hành yên lặng: giữ thông báo ba dòng đã chỉnh, không tạo Có gì mới và không phát lại quà.

# 1.7.11 — 2026-10-05

- Thêm mục Đầu tư trực tiếp trong menu, gom Mây Coin và Vàng với giá, tài sản, lãi/lỗ và giao dịch trên cùng màn hình.
- Tin thị trường trong game tạo xu hướng 2–5 ngày; khoảng 70% đợt tin có chiều tăng. Giữ nguyên tài sản và giá vốn đã lưu.
- Giữ lịch sử vàng đến 05/10; cơ chế mới áp dụng từ 06/10. Coin tiếp tục đổi giá theo ngày sống.
- Phát hành yên lặng: không thêm Có gì mới, không tặng lại quà hội chợ.

# 1.7.10 — 2026-10-05

- Tặng toàn server 300 xu hội chợ, xác nhận một lần cho mỗi bản lưu; giữ quà chờ cho người offline.
- Tăng xác suất hội chợ, giảm khi lặp một trò; giữ Ô ăn quan. Giảm 20% xác suất bị bắt tại hội chợ.
- Thêm 40% lợi nhuận đủ điều kiện, khách xếp hàng liên tục, nhân viên bán đa dạng hàng thay vì chỉ áo thun.
- Bản đồ, chỉ đường và điều khiển giao hàng rõ hơn; sửa đồng hồ đèn giao thông bị tạo lặp.
- Sửa kết nối live tự phục hồi, thưởng/lịch phi công biến thiên, bán nhẫn dư và hướng dẫn đón bé.

# v1.7.9 — giảm xử lý API và thu gọn khách ghé

- Dựng dịch vụ chỉ sao chép nghề cần dùng; bỏ tải lại bản lưu khi hỏi hộp đơn rỗng và khi xác thực API ghé tiệm.
- Dùng chung dữ liệu trước thay đổi trong transaction; dùng kết quả tính tiền nhân viên đã commit cho API trạng thái.
- Giảm hỏi đơn nền khi không có đơn đang xử lý, tạm dừng khi tab ẩn; vẫn theo dõi nhanh các đơn đang phục vụ.
- Khách ghé nằm trong bố cục, không đè nút Làm tiếp/Hoàn thành; giữ nguyên chiều rộng phiếu công việc trên điện thoại.
- Nút chat và ghé tiệm trong danh sách bạn bè cùng kích thước, nằm cùng hàng.
- Có gì mới thông báo ba mục tốc độ, khách ghé và danh sách bạn bè; chưa thiết kế lại toàn bộ màn ghé tiệm.

# v1.7.8 — tiệm tự vận hành, ghé thăm bạn và trò chuyện

- Nhân viên tự động của Quầy riêng và Sổ tiệm phục vụ liên tục, tính cả thời gian offline tới khi thiếu hàng hoặc quỹ; mở không giới hạn quầy, chọn menu và định giá từng món.
- Trang bị tăng tốc cho các nghề; ghé chỗ làm, đặt dịch vụ người chơi và đánh giá sau khi hoàn thành.
- Bạn bè mời ghé nhà hoặc ở chung lâu dài, kể cả khi chủ offline; quyền vào nhà theo lời mời đã chấp nhận.
- Trả lời từng tin nhắn; tên nhân vật cập nhật trong bạn bè, chat và phòng chung, giữ nguyên username.
- Shop thú cưng tách cá theo bể; sửa đọc bản lưu café cũ thiếu bar_pace.
- Có gì mới giới thiệu các phần trên cùng xưởng gấu bông và trải nghiệm gia đình đã phát hành ở 1.7.5–1.7.7.
- Chưa bao gồm lỗi vốn góp của chủ Quầy riêng không liên kết quỹ nghề của người chơi làm thuê; các nghề mới vẫn để đợt riêng.

# v1.7.7 — nhà dễ tìm, cử chỉ có lời đáp

- Đưa Nhà & Gia đình, Vào nhà, Mời về ở và Con chung ngay dưới nhân vật trong Hành trình; lời mời cần trả lời nằm đầu trang gia đình.
- Làm rõ điều kiện đón con của cả hai, trạng thái đang chờ, cùng chăm bé và các lối vào nhà; gom tùy chọn phụ để thao tác chính dễ thấy trên điện thoại.
- Người gửi bước tới và thực sự ôm, hôn hoặc thả tim. Người nhận chọn Đáp lại để cả hai cùng tương tác, hoặc Ngại ngùng, Giận dỗi, Để sau.
- Cử chỉ đồng bộ hai màn hình, tự khép lại khi hết hạn, di chuyển hay rời phòng; có hỗ trợ giảm chuyển động và bàn phím.

# v1.7.6 — tự tay may bạn gấu

- Xưởng handmade có gấu bông: đo vải, cắt hai mặt, may viền, nhồi bông và gắn mặt, nơ, dấu trang trí.
- Bàn thủ công có hướng dẫn trực tiếp, thao tác kéo hoặc bàn phím, làm lại từng bước và giữ bản nháp trên máy theo tài khoản.
- Gốm, vòng tay và thiệp có công đoạn tương ứng; thành phẩm giữ dấu trang trí trên kệ. Chỉ trả vật liệu khi hoàn thiện và xác nhận thanh toán.

# v1.7.5 — cùng ở trong nhà

- Người sống chung thấy nhân vật của nhau trong cùng phòng, cùng di chuyển và gửi ôm, hôn, thả tim.
- Nội thất, màu tường/sàn và phần sửa sang hiển thị thống nhất; thay đổi trang trí cập nhật sang người kia.
- Giữ đồ mua riêng của từng người; đổi tường/sàn lưu cùng thanh toán, không trừ lặp. Rời nhà, đổi phòng, nối lại mạng và nhiều tab được đồng bộ.

# v1.7.4 — thông báo cập nhật trong game

- Bổ sung bảng “Có gì mới” cho đợt sửa vừa phát hành: con chung, ở chung, nội thất, chuyển khoản/quỹ chung, chat và thao tác nghề.
- Người chơi quay lại thấy thông báo một lần vào lúc nghỉ phù hợp; có thể mở lại trong Cài đặt → Cách chơi → Có gì mới. Có bản tiếng Anh.
- Các nghề mới vẫn ở đợt sau.

# v1.7.3 — sửa phản hồi, gia đình và PostgreSQL

- Admin có danh sách người chơi, tìm theo tên hoặc username; chat riêng giữ đủ tin mới khi mở phòng, tải lịch sử và nối lại mạng.
- PostgreSQL là cơ sở dữ liệu duy nhất cho game, live và công cụ vận hành; bỏ nhánh SQLite và công cụ chuyển đổi cũ.
- Vợ chồng có con chung, cùng chăm bé và gửi lời mời về ở chung; bảo toàn nhà riêng, tiền cọc và dữ liệu con khi thay đổi quan hệ.
- Bỏ giới hạn tổng 60 món nội thất; thêm hướng trước/sau cho TV và sofa, dùng đồ trong nhà chung và cập nhật bạn cùng nhà.
- Bỏ hạn mức ngày của chuyển khoản và rút quỹ chung; vẫn kiểm tra số dư, người nhận và chống xử lý lặp.
- Cà phê có tốc độ máy 1×/2×/4×; nhập áo chọn đúng size; làm rõ lương, nhân viên quầy, đánh giá cần trả lời và chỉ số tình làng nghĩa xóm.
- Bổ sung hoạt động gặp NPC trong phố; cải thiện đổi nghề, hướng dẫn, thao tác bảng trên điện thoại và điều khiển tự lái giao hàng.
- Các nghề mới theo đề xuất được tách sang đợt sau.

# v1.7.2 — công an thu hồi tiền bị hack

- Sau khi xử lý sự cố, công an có 30% cơ hội bắt được kẻ hack; kết quả sau 2 ngày sống. Bắt được thì hoàn đủ khoản mất vào tài khoản ngân hàng và ghi lịch sử.
- Hồ sơ riêng không đè việc thu hồi tiền mặt; giữ kết quả qua tải lại, không hoàn lặp. Bổ sung trạng thái đang chờ, hướng dẫn và EN.

# v1.7.1 — rủi ro hack ngân hàng

- Thêm cảnh báo đăng nhập lạ trước 1–2 ngày sống; đổi mã và khóa phiên lạ miễn phí để chặn sự cố.
- Nếu bỏ qua, mất 8% tài khoản thanh toán, tối đa 3.000 xu và chịu giới hạn rủi ro chung. Ghi lịch sử ngân hàng/rủi ro, không trừ lặp khi tải lại; không trừ ví, tiết kiệm, thẻ hay quỹ chung.
- Hướng dẫn VI/EN nêu rõ nguồn tiền bị mất, cách phòng và bảo hiểm không bồi thường hack. Không phát sinh khi offline.

# v1.7.0 — phản hồi người chơi và đời sống trong phố

- Homestay kiểm tra cả lịch đặt, giữ phòng điện thoại và OTA trước khi nhận cọc; giao ngày trả/nhận phòng đúng theo đêm lưu trú.
- Đánh giá có lời đe dọa tống tiền có thể lưu bằng chứng và báo công an trong game; không tự đổi sao hoặc trừ xu.
- Quỹ chung tăng giới hạn chi/rút lên 1.000 xu mỗi người trong 24 giờ; bổ sung hướng dẫn trả bằng quỹ chung và cách tính lời quầy.
- Thanh toán mua sắm cá nhân trực tiếp từ tài khoản ngân hàng; thiếu số dư sẽ dừng nếu chọn cách này. Giữ nguyên các lựa chọn ví, thẻ và quỹ chung.
- Cà phê có nhịp máy 1×/2×; Hộ chiếu chỉ rõ tiến độ và cách nhận huy hiệu Hẹn ở ngày hội.
- Ba kiểu tóc búi, ba mẫu đầm mới, hiển thị đồng nhất trên nhân vật và ảnh đại diện.
- Thuê người chơi ở quầy hiển thị cả bạn mới, mời riêng ngay sau khi kết bạn; bỏ giới hạn giao diện chỉ hiện 8 bạn.
- Không giới hạn số quầy, phân trang 12 quầy. Sổ quầy ghi chi phí ngày bán, thuế xu chung toàn chuỗi, trộm/cướp, kiểm tra vệ sinh/chứng từ và đòi bảo kê; kiểm tra đạt không phạt, có cách phòng ngừa và báo công an. Không truy thu ngày cũ khi nâng cấp.
- Chọn nguồn trả cho từng giao dịch cá nhân và lương thuê người chơi; lương được giữ trước, hoàn về đúng nguồn khi hủy/hết hạn. Quỹ chung cũ đã đóng thì hoàn về ví người chi.
- Sổ shipper có hợp đồng, bậc nghề, trang bị và thưởng theo đơn thực sự giao; không nhận thưởng lặp. Tự lái giao hàng có đèn giao thông và phạt vượt đèn đỏ.
- Hướng dẫn tự lái máy bay theo từng giai đoạn, có thể mở lại; thẻ nghề chỉ rõ tiến độ thăng chức và phần quản lý.
- Góc gia đình: tự chọn nhận nuôi em bé, mèo hoặc cún, đặt tên, chăm sóc theo ngày sống, tiến trình trưởng thành và đồ mặc cho bé. Lưu riêng theo nhân vật, không tự phát sinh phí khi offline.
- Đi làm tóc, làm nail với vai trò khách và tự làm đồ DIY, xem mẫu/giá trước khi xác nhận.
- Kết bạn từ tin nhắn chat, mời bạn vào buồng chụp qua tin nhắn riêng; nhập mã hỗ trợ bộ gõ đang ghép chữ. Kiểm tra quyền xem tin và chặn hai chiều.
- Trang trí giữ vị trí thanh phòng khi chọn phòng cuối, thêm nút cuộn phòng/cửa hàng; ghi lời báo thú cưng có chỉ dẫn chọn đúng việc đã quan sát.
- Xe và máy bay chưa sử dụng không tự gặp sự cố hỏng theo ngày; đổi màu/trưng xe không tính là chuyến đi.
- Chạm tủ quần áo hoặc giá treo trong nhà để xem và thử đồ đã sở hữu, mở Tủ đồ để mặc.
- Cập nhật hướng dẫn Việt/Anh. Bản này giữ các sửa lỗi đã phát hành ở 1.6.8.

Rollback: giữ hỗ trợ mã tóc/đầm, bank.pref=account, số quầy và sổ thu chi mới; giữ bộ xử lý hoàn lương theo nguồn cho các ca đã giữ tiền. Không chạy nguyên bản 1.6.8 trên save đã dùng tính năng mới. Xem docs/FEEDBACK_2026-10-04.md để biết kiểm tra và triển khai.

# v1.6.8 — ✈️ hộp Bỏ dở việc ở Hãng bay

- `abandon.js`/`abandon.css`: hàng nút đổi class `.ab-row` → `.ab-btns`; `careers/air_kit.css` có `.ab-row` (bảng giờ bay, lưới nền tối) nên rời Hãng bay khi làm dở thì hai nút bị bóp thành cột hẹp trên nền đen.

# v1.6.7 — 🎁 quà cả phố 100 xu, 💰 hoàn phí "Nơi làm khác"

- `system_gift.BROADCASTS`: mọi người chơi (khách, tài khoản cũ và mới) nhận 100 xu một lần khi tải game, tới 11/10 21:00; test tắt bằng MNL_BROADCAST_OFF. Không chèn hàng loạt: lúc tải, save tự có dòng `system_gifts` riêng (`all1004-<hash sid>`), rồi đi đường quà sẵn có (pending → applied → seen, có thiệp).
- `journey._refund_upkeep()` trong `upgrade()`: lần tải đầu, `stats.upkeep_paid` (tổng phí duy trì nơi vắng chủ đã trả) cộng vào ví với dòng "Hoàn phí duy trì nơi vắng chủ 💰", rồi về 0. Không thêm trường save; tải lại không hoàn lần hai.

# v1.6.6 — 🧭 giao đơn quầy: nút theo hướng bản đồ

- `quay-ride.js` `turnChoices()`: nút ở ngã tư hiện hướng trên bản đồ (⬆️ ⬇️ ⬅️ ➡️) tính từ hướng xe, vẫn gửi L/S/R như cũ (feedback #144: xe chạy ngang thì không có nút đi xuống).

# v1.6.5 — 💼 nơi làm cũ không trừ tiền nữa

- `journey.upkeep()` = 0: bỏ phí "duy trì khi vắng chủ" (4/7/11 xu mỗi ngày cho mọi nơi đã mở, chip "Nơi làm khác −X"); mở lại nơi tạm đóng miễn phí (REOPEN_FEE 0), bỏ nút Tạm đóng. Kho, nhân viên, hóa đơn nơi cũ đứng yên chờ quay lại. Không hoàn tiền quá khứ.
- Phạt bỏ dở ca ghi rõ "Phạt bỏ dở ca ở <nơi>", nguồn trả (quỹ/ví/lương) trong hộp xác nhận. Save không thêm trường mới.

# v1.6.4 — 📸 buồng chụp: 49 dáng, 14 biểu cảm, 50 sticker kéo thả

- Buồng chụp hội chợ: tab Biểu cảm riêng (14 mặt), 49 dáng; sau khi chụp mở trình trang trí dải ảnh: chạm để dán, kéo để dời, ↻ xoay/đổi cỡ, hoàn tác, lên trên, xoá; sticker lưu vào ảnh tải về. Trang trí mặc định giữ nguyên.

# v1.6.3 — 💑 vợ chồng chung xe, 🛡️ admin chuyển khoản không giới hạn

- Xe của vợ/chồng (`GET /api/garage/spouse`); live quyết ai lái trước; `back`/`fair_back` để ngồi sau; trường mới đều tùy chọn, cờ `coride` trong welcome (feedback #136).
- Chuyển khoản: tài khoản trong ADMIN_USERS chuyển ngay, không hạn mức ngày, không chờ kết bạn, không điều kiện tuổi tài khoản/ngày sống; tối đa 1.000.000 xu mỗi lần.

# v1.6.2 — 🛒 quán quá giờ đóng cửa không giữ chân, 🏡 mua nhà không tự dọn, 📖 hướng dẫn 1.6

- `game/abandon.py`: chỗ làm đã quá giờ đóng cửa thì đổi chỗ không hỏi, không phạt, việc dở giữ nguyên (feedback #140: Tạp hóa 21:30 dở ca làm "Ở lại làm nốt" kéo về mãi). Bản xem trước/kết quả thêm khóa tùy chọn `closing`.
- Nhà: mua nhà khi đang ở (nhà mình hoặc nhà chung) không tự dọn; thẻ "Nhà chung với …" và nút "💞 Về ở chung" (`jr_home_move` `to=shared`, feedback #137). Bản đồ phố: tiệm tạm đóng kéo cửa, nhãn ⏸, nút Mở lại vào làm luôn.
- Hướng dẫn: chuyển khoản (số lấy từ `bank_xfer.py`), bản đồ phố, đi xe, chụp ảnh hội chợ, tự lái/tự bay/nông trại.

# v1.6.1 — ✈️ phi công tự bay, 📸 buồng chụp một màn, 💸 chuyển khoản cần 1 ngày, 🎁 admin tặng xu

- Phi công tự bay góc nhìn thứ nhất (`public/js/careers/pilot_fly.js`), trường `flown` tùy chọn; ⏩ Bay nhanh làm đường lui.
- Buồng chụp hội chợ: xem trước dính trên cùng, tab Dáng / Khung ảnh / Phông nền / Đạo cụ cuộn bên dưới; máy tính hai cột.
- Chuyển khoản: `ACCOUNT_DAYS` 3 → 1, chữ "ngày chơi game (đời thực)".
- Admin: trang 🎁 Tặng xu (danh sách user, tặng qua `system_gifts`, cột `granted_by`, PG schema 16).
- Test: `test_live_wedding` chờ xu phút tiệc ghi xong (không đổi game).

# v1.6.0 — 🗺️ phố đi dạo, 🛵 tự lái & đi xe, 🚜 nông trại góc nhìn, 🏪 quầy v2 + bán online, 📸 photobooth đẹp, 💸 chuyển khoản bạn bè

- Màn hình chính là bản đồ phố (`public/js/v4/town-walk.js`); danh sách Hành trình vẫn còn (📋 Danh sách, Cài đặt → Màn hình chính).
- Giao hàng Tự lái góc nhìn thứ nhất (`public/js/careers/delivery_drive.js`), lệnh server giữ nguyên (`dl_plan`/`dl_ride`); ⏩ Đi nhanh làm đường lui.
- Nông trại góc nhìn thứ nhất/thứ ba, chạy xe máy giao hàng.
- Đi xe của mình trong phố, hội chợ, đi dạo (`public/js/v4/ride.js`); live: trường tùy chọn `r`/`v`, frame `ride`. Không tốn xăng.
- Quầy v2 (`game/quay.py`): tự đứng quầy, menu & giá, trang trí, hình quầy canvas, bán online, 26 tình huống; sửa lỗi bấm tự cuộn lên.
- Photobooth hội chợ: 30 dáng (9 dáng nhóm, `booth_set` thêm `all` tùy chọn), khung, nền, sticker, lọc màu, chữ & ngày trên dải ảnh.
- Chuyển khoản bạn bè (`game/bank_xfer.py`, bảng `bank_xfers`, `bank_xfer_days`, PG schema 15): hạn mức gửi 2.000/ngày, nhận 3.000/ngày, tài khoản ≥3 ngày & ≥10 ngày sống, bạn ≥60 phút; 30 ngày chưa nhận thì hoàn.
- Sửa: gợi ý câu chọn nhiều đáp án nói đúng chỗ sai (`game/procedures.py`, feedback #124); hoàn tiền/xin lỗi có thể làm khách sửa sao (`feedback.amends`); trông trẻ/giúp việc/nấu cơm hiện tiền công.

# v1.5.4 — 📸 buồng chụp hội chợ luôn mở, tự nối lại; 🧋 trà sữa không khựng; 🧑‍🏫 lớp học không đứng

- Buồng chụp hội chợ: sảnh vẽ lại theo trạng thái socket live, nối lại ngay khi mở buồng (`live.reconnect(true)`), bỏ chữ "đang nghỉ"; rớt mạng trong phòng bạn bè thì tự `booth_join` lại. `live/booth.py`: người cuối mất socket được giữ chỗ 120 giây (`GRACE_SECS`, `away`), mã phòng vẫn dùng được.
- Lớp học: câu trả lời học sinh không chờ AI (`later`, chờ tối đa 2 giây). Trà sữa: chọn nguyên liệu hiện ngay (optimistic).

# v1.5.3 — 🧮 ô số kế toán nhận số âm, phép tính, đơn vị; 💍 chờ 3 tiếng sau ly hôn

- `public/js/v4/amount-parse.js`: ô số của Học TT99, kế toán doanh nghiệp/tập đoàn, thuế-lương là ô chữ (bàn phím đầy đủ), hiểu `-`/`−`/(…), dấu nghìn, đ/k/tr/tỷ, + − × / ( ), đơn vị cuối áp cho cả phép tính; xem trước "= …". Server không đổi.
- Hôn nhân: sau ly hôn chờ `REMARRY_HOURS` = 3 tiếng (trước 3 ngày); 26 người đang chờ đã được đưa về mốc mới trên prod (sao lưu /root/remarry_backup_20261003.csv).

# v1.5.2 — 🎁 Quà hệ thống tới 100.000 xu

- `game/system_gift.py`: MAX_COINS 1000 → 100000 (chủ game tặng một người chơi 100k xu, 03/10); `scripts/grant_gift.py` đòi `--large` khi trên 1000 xu để vẫn chặn gõ nhầm.

# v1.5.1 — 🎖️ Thăng tiến & ca quản lý, 🏪 quầy riêng, 🧹🍲👶 ba nghề nội trợ, 🛡️ rủi ro & tiệm vàng, ✨ UI gọn

- Thăng tiến mọi nghề (`game/promotion.py`): 4 bậc, không giáng chức; làm thuê tăng lương 8–35%, chủ quán thêm tip khách quen; từ bậc 3 mở Ca quản lý (chia việc, kiểm việc, gỡ rối, chốt ca).
- Quầy riêng (`game/quay.py`): xe đẩy / sạp / ki-ốt, nhân viên NPC tự đặt lương, thu két; thuê người chơi khác một ca (bảng `quay_jobs`), lương là chuyển khoản giữ trước, trả một lần.
- Nghề mới: Giúp việc theo giờ (`giupviec`), Nấu cơm gia đình (`naucom`), Bảo mẫu trông trẻ (`babysitter`). Lịch x3 của các nghề cũ không đổi.
- Rủi ro đời sống (`game/rui.py`): luôn báo trước, có cách phòng, trần theo tài sản, không bao giờ nợ, người mới được miễn; bảo hiểm sức khỏe / xe / nhà, đồ an toàn. Tiệm vàng Kim Phát (`game/vang.py`).
- UI gọn: toast ≤8 chữ bấm để mở đủ, thẻ ví cuối ngày dạng chip (có chip 🔥 x3), x3 / ngân hàng / chip "Hôm nay" gấp chi tiết.

# v1.5.0 — 🍜 Bán phở, 🍚 Bán cơm, 📸 Photobooth, 🏠 vào nhà & tủ lạnh, 🧧 phong bì

- Nghề mới: Bán phở (quán phở Cây Si), Bán cơm (Cơm tấm Dì Bảy), Photobooth (Tiệm ảnh Tách Tách). Tuần x3 đang chạy giữ nguyên lịch các nghề cũ.
- Hội chợ: photobooth chụp một mình / với người lạ / với bạn bằng mã, dải ảnh có khung tải về PNG.
- Vào nhà, phòng trọ, KTX; tủ lạnh (`game/fridge.py`) cất đồ ăn.
- Đám cưới: phong bì không giới hạn, mức 500 xu từ ngày sống 3. Nút gửi tự quản trạng thái bận (không bị tap guard chung nuốt), mất phản hồi thì gửi lại cùng request id, server trả "đã gửi" thay vì "không đủ xu" cho lần gửi lại (e63e643).
- Nông trại: phân bón lá thúc. 🌅 Ngày mai trong tổng kết ngày cho các nghề; năm đợt chỉnh UI theo nghề.
- Tổng kết ngày: dòng 🔥 Thưởng ngày x3 (`summary.journey.x3`); thưởng đã trả nhưng thẻ không hiện (chủ game thử gom rác 03/10).
- Đánh giá: nhãn "Đã trả lời" chỉ khi người chơi đã trả lời; nhận xét của tổ bay (đóng ngay, `fb.own`) ghi "không cần trả lời" (Yuika, chat 03/10).

# v1.4.33 — 🌐 Cốc Cốc / trình chặn quảng cáo không còn kẹt màn hình tải

Chủ game: "game vào bằng Cốc Cốc không được… tới bước tải cuối thấy dừng luôn".

- `public/js/scenes/reads.js` chứa chuỗi `ads.js` ("re-ads.js"): luật chặn quảng cáo chung (bộ chặn có sẵn của Cốc Cốc, uBlock, AdGuard) chặn file này, cả đồ thị module của `app.js` hỏng, trang đứng ở màn hình tải (thống kê lỗi client: ~135 lần/ngày `app.js` + `reads.js`). Đổi tên `scenes/room-watch.js`; `v4/popup-gate.js` → `v4/break-gate.js` (chữ "popup").
- `tests/test_asset_names.py`: không file nào trang tải có tên mà bộ chặn quảng cáo bắt (trừ `telemetry.js`, `analytics-preferences.js`: tải sau, lỗi được bắt).
- Kiểm bằng trình duyệt với luật chặn `ads.js|popup`: 1.4.32 kẹt màn hình tải, 1.4.33 vào game.

# v1.4.32 — 🧑‍🍳 Nhân viên kiếm thêm cho tiệm

Chủ game: "cho nhân viên làm có thêm tiền thưởng khi thuê nhân viên", đổi tên nhóm menu.

- `operations.on_close`: mỗi việc nhân viên làm xong trong ca (đếm ở `attendance[day][id].jobs`) +3 xu (+4 khi tinh thần ≥80 hoặc cẩn thận ≥90), tối đa 12 việc/người/ngày, một dòng "Thu khác" mỗi ngày (ref `staff-jobs-<day>`), tính vào thu nhập/lời ngày (cả x3). Người tạm dừng/nghỉ/không ca không có.
- Sự cố nhân viên thật: cách sự cố trước ≥4 ngày tiệm và xác suất mỗi việc giảm một nửa (≈1 lần/4–5 ngày thay vì gần như mỗi ngày). Diễn tập giữ nguyên.
- Menu: nhóm "Tiền & nhà" → "Ngân hàng & nhà" (#110).

# v1.4.31 — ⏱️ Kim dừng đúng chỗ, nhân viên rõ ràng, nút Ngân hàng

Từ góp ý và tin nhắn nhóm 03/10 (Rizz, kattie #100, Cô Cả, Suzy, Cá Voi Xanh #110) và thống kê lỗi client.

- Canh mức (máy may, tắm thú, ép nắp…): `dayclock.daylight` chạy theo giờ thật (cảnh không còn vẽ lại mỗi khung hình khi bảng mở); màu/chữ thanh cập nhật mỗi khung hình; `TAP_LAG` 3 → 30 s (dung sai giữ nguyên); đồng hồ server ước lượng kiểu NTP (`server_recv`, `api.clockSample`); máy may chấm theo `sew_zone(t)` như trang vẽ, bấm trước vạch báo ngay không gửi.
- Nhân viên: người bị tạm dừng vì sự cố của mình không còn chấm công, tính lương, tăng mệt; thẻ nhân viên ghi việc hôm nay và lý do nghỉ; tổng kết ngày có dòng "Đội hôm nay" (`attendance[day][id].jobs` tùy chọn).
- Tiền của bạn: nút "🏦 Vào Ngân hàng" / "Mở tài khoản" (#110: ngân hàng nằm trong Thêm › Tiền & nhà từ 01/10).
- `/api/ai/review`, `/api/ai/feedback`: `_internal` lấy 4 giá trị từ `store.read()` (chỉ có 3) khi review đã được xử lý trước → 400 `invalid_data` (~70/giờ). Bạn quen qua hẹn hò được cấp mã PCC (`friends.ensure_codes`) nên Hủy kết bạn/Chặn/Cầu hôn chạy. Tên hồ sơ trùng đánh dấu ô tên, không gửi lặp; các từ chối hợp lệ không còn báo là lỗi client.
- Sổ tiệm: hướng dẫn khép sự cố ghi đúng tên tab "Nhân viên".

# v1.4.30 — 💞 Nhà chung thấy đồ của nhau

Phản ánh của người chơi (TrangChit, góp ý #109): "Mình trang trí nhà nhưng Minh Hưng không thấy đồ đạc trong nhà".

- Đồ đạc thuộc bản lưu của từng người, nên ở nhà chung mỗi người chỉ thấy đồ mình bày. `GET /api/deco/mate` (`game/deco_mate.py`): khi hai vợ chồng (còn kết hôn) cùng ở một nhà (một người đứng tên `own`, người kia `shared` qua cặp này, cùng id và loại nhà), trả các món người kia đã đặt, đọc bản lưu của họ một lần, không ghi gì, không thêm khóa nào vào bản lưu (1.4.28 vẫn nhận mọi bản lưu). `reno.js` vẽ chúng cùng đồ của mình (cả ảnh chụp), chỉ để xem: không chọn, không kéo, không vào túi, không tính Ấm cúng.
- Sổ tiệm (Suzy, homestay): cho nhân viên nghỉ khi họ còn sự cố đang mở giờ báo rõ các bước khép sự cố thay vì "Cần trao đổi sự cố đang mở…".

# v1.4.29 — 📒 Học kế toán: bản lưu cũ không còn bị khóa

Phản ánh của người chơi (num_cute, góp ý #108): "cứ hiện đáp án đã lưu chưa được chấm đúng… ấn vào học bằng cũng không cho vào".

- Mã phương án đúng của câu trắc nghiệm suy từ chữ của đề (`accounting_content.choice`). 1.4.27 thêm lại dấu cách nên 3 câu đổi mã (`vn_business_vouchers_practice_2` o1→o2, `vn_business_b01_practice_3` o2→o0, `vn_business_demanddeposit_exam` o1→o0). Người đã làm đúng các câu này trước 1.4.27 bị `validate` từ chối cả bản lưu → mọi thao tác báo lỗi.
- `accounting_school.LEGACY_KEYS`: đáp án đã lưu đúng theo mã cũ vẫn hợp lệ; điểm thi/chứng nhận chấm theo mã cũ vẫn khớp; thẻ bài đã giải hiện phương án đúng hiện tại; trả lời mới vẫn chấm theo mã hiện tại.
- `tests/accounting_released_keys.json`: ảnh chụp mọi mã đáp án đã phát hành; sửa chữ làm đổi mã sẽ làm test đỏ.

# v1.4.28 — 🔥 Thưởng x3 tính đủ cả ngày

Chủ game: "nghe bảo lương x3 nhưng mà chưa tăng đúng kìa".

- `engine.end_day`: tổng kết (thu, chi, lời) đọc sau khi đã trả lương (`emp.on_close`) và khép ca riêng của nghề; lời = thu − chi (rút/góp vốn đã bị loại khỏi thu/chi). Trước đây lời lấy trước khi trả lương và bằng quỹ − `day_start_money`; rút quá vốn đầu ngày làm mốc kẹt ở 0 và mất phần lời. Ví dụ: vốn 320, bán 300, rút 540 → thưởng 160 thay vì 600; nghề có lương gần như không được thưởng x3. Save không đổi.

# v1.4.27 — 📚 Đề kế toán TT99 hết dính số

Người chơi (Viên Nhu trên Cả phố, góp ý #104): "phần 11 câu 2 bài ôn kế toán doanh nghiệp… số nó kì kì".

- `accounting_vn_content.py`: mất dấu cách trước chữ số trên toàn khóa TT99: số tài khoản dính số tiền ("Nguồn cũ 4416.000.000đ" = 441 6.000.000đ, "Có 33125.000.000đ" = 331 25.000.000đ, 21 chỗ, tách theo từng bài) và chữ dính số ("36tháng", "VAT10%", "xem128", "100bộ"). Đáp án, id, số câu không đổi.

# v1.4.26 — 🛒 Thu gom rác: túi dán phiếu không làm kẹt ngõ

Phản ánh của người chơi (tieuthuki): "thu gom rác bấm không được nữa".

- `garbage.js roundSteps()`: "Tới nhà sau" chờ mọi túi `loaded`; túi đã dán phiếu (sự cố chủ nhà chặn xe → "Dán phiếu", hoặc tự từ chối) không bao giờ lên xe, nên ở nhà chưa phải cuối ngõ không còn nút nào để bấm. Giờ túi `refused` tính là đã xử lý (cả ô đếm x/y trên dải nhà). Server không đổi.

# v1.4.25 — ⚡ Gửi state theo phần (delta), vẽ nền quán trà sữa một lần

Chủ game: "có gì tối ưu lại k chậm thì vẫn tiếp tục tối ưu"; góp ý #100 (chậm, lag).

- feat/state-delta (f9846f5, 46a05fe, a862c4c, 08ba757): `game/state_delta.py`; trang gửi `X-Game-Delta: 1` và `known` (hash các phần đang giữ); server chia dict/list > 2 KB thành phần (tới 6 tầng), phần trang đã có ghi `0` + `delta.refs`; không nhớ gì về trang. 409 và export luôn trả đủ. Trang cũ / server cũ: như trước. Trả lời gzip p50 ~28 KB → ~5,8 KB; parse JSON p50 84 → 11 ms (4x CPU). `api.js inflate()`, thiếu phần thì đọc `GET /api/state`. Dev `?deltacheck=1`: đóng băng state, so với `/api/state`; 0 lệch trên first_day 7 nghề, hội chợ, nhà, garage.
- Nền phòng (`boba-world.js backdrop()`): khóa cache theo những gì phòng đọc (`scenes/reads.js`), không theo `rev`; mây/đèn trà sữa vẽ chồng bằng `ambient()`. Phiên 30 lệnh: vẽ nền 189 → 10 lần, script main-thread 10,2 → 4,0 s.

# v1.4.24 — 🗡️ Phóng dao thay phi tiêu

Chủ game (03/10): "game phi tiêu đổi thành game này đi: càng ngày càng khó, chơi 1 màn xong chọn chơi tiếp hoặc dừng, chơi tiếp mà thua thì thua hết, dừng thì nhận thưởng hiện tại. Lâu lâu thì hiển thị "màn sau x2"".

- feat/fair-knife (b347631, 8171336): `game/fair_knife.py`, lệnh `fair_kn_*`, `v4/fair-knife.js`; gỡ `fair_darts.py`/`fair-darts.js`. Cược 2/5/10/20 xu, 10 màn (bia xoay nhanh dần, đảo chiều, khựng; 6–7 dao, có dao cắm sẵn), qua màn chọn Dừng/Chơi tiếp, thua mất hết; từ màn 2, 25 % màn là 🔥 x2 (không liền nhau). Thang × cược: 1.1, 1.2, 1.6, 2.1, 2.8, 3.9, 5.4, 8, 12, 19. Server giữ seed, client chỉ gửi thời điểm phóng, server chấm lại; quá 60 s là thua; lượt bỏ dở được trả như Dừng cuối ngày VN. Lời hội chợ > 2000 xu: bia khó hơn tới 3 bậc. Lưu ở `journey.fair_kn` (bộ kiểm 1.4.20 bỏ qua). Client cũ: gian phi tiêu ẩn, lệnh cũ trả "tải lại trang".

# v1.4.23 — 📚 Việc làm kế toán TT99 (x3, lễ x5), 📦 Kho & đếm nhanh, 🪟 một thẻ một lúc, 👆 nút chính chỉ chỗ

Chủ game (03/10): "coi code kế toán thông tư 99, làm xong giới thiệu việc làm ở đâu nữa nhé, với check kiến thức này kia, bắt học thi qua mới làm được nhé, và ở đó kế toán lương x3 bình thường, đôi khi lễ tăng lên x5"; gói UI/UX WP-2/3/4 (tham khảo bộ nghiên cứu, giữ thiết kế hiện tại).

- 📚 feat/acct-jobs (4f6141e, ce27e21, ce1eaca): `game/accounting_jobs.py`. Hành trình: Mây Tre Xanh cần chứng nhận Kế toán cơ bản, Sông Hồng Group cần Kế toán DN Việt Nam (TT99); máy chủ chặn `need_cert`, thẻ 🔒 + "Đi học". Người đã làm/đã nộp hồ sơ giữ quyền cũ (x1, không kiểm tra). Kiểm tra đầu ca 3 câu từ ngân hàng đề (đúng 2/3), đề theo seed, không lưu gì. Lương x3, ngày lễ VN x5 (1/1, Tết, Giỗ Tổ, 30/4, 1/5, 2/9 + ngày liền kề; bảng 2026–2028), trần 600 xu/ngày, chỉ nhân dòng lương; x3_week cộng riêng. Giới thiệu việc làm trong tab Thi & chứng nhận. Không thêm khóa save.
- 📦 feat/ui-wp3 (ef9b569…e55eede): hóa đơn ngay dưới số lượng, nhà cung cấp dạng chip, giữ để đếm (~7 món/giây, D4, góp ý #97), Chuẩn bị trà sữa mở Kho trước, tổng kết ngày mở đầu "🌅 Ngày mai". `public/css/stock.css` mới.
- 🪟 feat/ui-wp2 (3ae8a17, 2dac23b, 7316f0c): `v4/popup-gate.js` một quy tắc chung (quà → Có gì mới → x3 → truyện), không mở trên tổng kết/khách đang chờ; mẹo lần đầu cạnh thanh dưới; dòng ví/quỹ nằm trong header sheet.
- 👆 feat/ui-wp4 (ee0b12f): từ khách thứ 2 nút chính dạng viền "👆 Chạm: …", cuộn tới + mũi tên ▼, không làm thay; toast một dòng ngay trên thanh dưới. D1: khách đầu giữ như cũ.

# v1.4.22 — 📱 Thanh dưới 5 nút, 🧭 Hành trình gọn, 👫 đứng tại gian ở bãi hội

Chủ game (03/10): "các bạn chơi trò gì thì bên ngoài thấy người ta đứng trò đó nhé, chứ đừng biến mất".

- 📱 feat/ui-wp1 (9b716d1, a754368, c0cafa0): thanh dưới điện thoại cố định 5 ô (Khách · bàn nghề · Kho · Sổ tiệm · Thêm), Kho mở đúng trang theo nghề, huy hiệu hàng sắp hết; HUD chip 44 px, < 360 px chỉ icon + số; Thêm không lặp lại thanh dưới; phụ đề một dòng cho Khu phố (D5: giữ tên).
- 🧭 feat/ui-wp5 (466aa94): Hành trình mở đầu bằng "Tiếp tục ở …", nơi làm việc dạng ô 2 cột trên điện thoại, nơi chưa mở cuộn ngang; Chuẩn bị chung: Kho trước, "Hôm nay · thời tiết / Nhiệm vụ" gộp một dòng gập, cấp & XP lên đầu, tab 44 px cuộn ngang.
- feat/fair-stand (be8274a, 47c71b0): client không còn gửi `fair_out` khi mở trang gian (chỉ khi đóng hội chợ/hết hội); `fair_mv`/`fair_in` thêm trường tùy chọn `s` (gian đang chơi, chữ thường ngắn; sai thì bỏ qua), gửi cho người khác trong `in`/`mv` và snapshot. Người chơi đứng ở điểm đứng của gian, bong bóng emoji trò (xe ăn vặt 🍡/🥤; vay nóng không có bong bóng). Live cũ: vẫn đứng, không bong bóng; client cũ bỏ qua `s`.

# v1.4.21 — ⏱️ Bấm dừng chấm đúng lúc chạm (#100)

Góp ý #100: bấm dừng bị trễ, thanh chạy quá chỗ đã bấm.

- feat/tap-lag (cefe0c0…e27f67a): client gửi `tap_at` (thời điểm chạm) kèm lệnh dừng; server `kit.tap_now(p)` chấm theo đó, kẹp trong [lúc tới − 3 s, lúc tới + 0,25 s], sai kiểu thì dùng giờ tới. Áp dụng: tea_seal, pc_rinse/pc_dry, cb_stop/cb_milk_stop/cb_unload, ao_sew_stop, hs_plate/hs_clean, rs_drain, sl_rinse. Thanh chạy bằng Web Animations (translateX), đóng băng ngay lúc pointerdown. Client cũ/server cũ: chấm lúc tới như trước.

# v1.4.20 — 🔥 Nghề x3 trong tuần, 🎟️ vé số cào, 🏮 35 món nhà, 💬 xóa tin nhắn & bỏ chặn, góp ý người chơi

Chủ game (03/10): "mỗi ngày x3 cho … trò bất kì", "làm liên tiếp, đầu tuần thông báo và tự áp dụng, mấy trò mà chia ra 1 tuần là đủ tất cả trò", "thêm trò cào xổ số… cào bằng tay thật", "thêm phụ kiện ở nhà", "bạn bè cho chọn xóa tin nhắn", "thông báo lâu quá, người ta có thể bấm tắt được"; góp ý #93–#99.

- 🔥 Nghề x3 trong tuần (`game/x3_week.py`): mỗi tuần (thứ Hai → Chủ nhật, giờ VN) chia 35 nghề cho 7 ngày (5 nghề/ngày, seed theo ngày thứ Hai); khép ca đúng ngày của nghề → thưởng thêm 2 × tiền lời ròng của ngày (net của ca, gồm lương; ≥ 0, tối đa 3000) vào ví, dòng Sổ ví "🔥 Thưởng ngày x3" (kind salary). Không lưu gì trong save; `public_state.x3 {x, week, days, day, today}`; `v4/x3week.js` bật lịch tuần một lần mỗi tuần, nút "Hôm nay lời x3" + chip trên thẻ nơi làm việc. `MNL_X3_OFF=1` tắt thưởng (test đặt sẵn). (Bản nháp x3 cho gian hội chợ đã gỡ: chủ game nói x3 là cho nghề.)
- 🎟️ Vé số cào (feat/fair-scratch 1263dd8): `fair_xs {price}`, vé 2/5/10/20 xu, thắng ~42 % (sàn 39 %), ~1,03 xu trả lại mỗi xu; cào bằng tay trên canvas, 70 % là lộ. Chuỗi vé giữ ở `journey.fair_run2`.
- 🏮 Trang trí nhà (feat/home-decor2 c98de6f): 35 món mới, kệ "Trung thu & Tết", 5 bộ; `deco_content.KNOWN_1419`; máy 1.4.19 vẫn nhận save có món mới.
- 💬 Chat (feat/chat-delete 4b8809d): giữ tin → "Xóa ở phía tôi" / "Thu hồi" (24 giờ); "Chọn" xóa nhiều cuộc trò chuyện; "🚫 Đã chặn" + Bỏ chặn (#93). Bảng mới `chat_hides`, `chat_clears` (SCHEMA_VERSION 13, chỉ thêm).
- 🔔 Thông báo (#95, #96): chạm để tắt, thời gian hiện theo độ dài chữ.
- 🗂️ Bàn văn phòng (#94): cuộc gọi đổi ý về một thẻ đã xếp trả thẻ về "chưa xếp", ghi chú 📞 in trên thẻ, thẻ đó mở trước.
- 🍡 Hàng ăn vặt (chủ game 03/10: "kẹo bông, nước mía… hội chợ không mua được, sửa cho mua nhé"): bỏ chặn "no rồi" (người vừa ăn sáng đã ở FULL_CAP 90 nên xe nào cũng khóa); chỉ còn chặn khi ví thiếu, no bụng/tỉnh táo vẫn tối đa 100.
- TikTok login (fix/tiktok-login 2ae19dc, phiên khác) gộp vào 1.4.20.
- 🪨 Ô ăn quan (#99): câu "quan non" nói rõ cần đủ 5 dân, không tính theo vòng.

# v1.4.19 — 🏆 Bảng vàng theo tiền lời, 👫 thấy nhau ở bãi hội

Chủ game (03/10): "thay vì tính điểm, tính tổng tiền mọi người thắng… tiền thắng nhiều xếp top", "mọi người vào hội chợ thì cho thấy nhau… (k thông báo)".

- Bảng vàng (feat/fair-money c14b8f8): điểm = `money_of(j)` = stats won − lost + earned (không tính quà 500 xu, vay nóng, ăn vặt). Bảng mới `fair20261003xu`, chỉ người đang lời; hàng cũ theo điểm không đọc nữa, xóa dần khi người chơi ghi lại. `lb.heal()` ghi lại hàng khi tiến trình gặp save lần đầu. Bỏ điểm khỏi UI.
- Bãi hội nhiều người (feat/fair-crowd 5df2ec2): `live/fair.py` phòng tối đa 30, vị trí theo tỉ lệ sàn, giới hạn như phố, chặn được tôn trọng, không thông báo. `LIVE_FAIR` mặc định theo `LIVE_STREET`. Client `fair-crowd.js`.

# v1.4.18 — 🍡 Hàng ăn vặt hội chợ

Chủ game (03/10): "người ta mua đồ ăn, uống nước mía được nữa nhé".

- `game/fair_food.py`, lệnh `fair_snack {item}` (chỉ khi hội mở): cô Út (kẹo bông 2, bắp nướng 3, bánh tráng nướng 4 xu), chú Năm (nước mía 2, chè 3, tàu hũ 2 xu). Tác dụng theo luật Ăn thêm (`needs` full/wake), từ chối khi đã no/tỉnh hoặc ví thiếu. Một dòng Sổ ví mỗi ngày "🍡 Ăn vặt hội chợ · N món". Không lưu gì trong `journey.fair` (feat/fair-food 0a111bb).

# v1.4.17 — 🦀 Bầu cua 5 giây, chơi dồn nguội tới 25%, 🎱 lô tô 53%

Chủ game (03/10): "bầu cua dễ thắng quá, spam mãi cái đó thì giảm tỷ lệ thắng… có thể thấp hơn 30%, mỗi lần bấm đợi 5s để mở", "gánh lô tô -> 53%", "bên ngoài luôn hiện hôm nay kiếm 0 xu => lỗi".

- Bầu cua: `RUN_RULES['bc'] = (.02, .25)` (sau 10 ván liên tiếp giảm 2 điểm %/ván, sàn 25%); bát mở sau `BC_OPEN_MS` 5 s, máy chủ đòi các ván cách ≥ `BC_GAP_MS` 4,8 s (`fair_slow`).
- Lô tô (feat/fair-food ea869e7): thắng/thua bốc trước bằng `luck_p(j, f, 'lt', t)`, rồi chọn `rs` cho ván khớp kết quả; Kinh = 2,2× tiền tờ (hũ đêm 2,3×), LOTO_PRIZE 23 → 11 cho tờ cũ.
- `fair.js` strip: "Hôm nay kiếm" = tổng `today_xu` mọi gian (trước đó đọc meter ô ăn quan/ném vòng, ra 0 từ khi bỏ trần).

# v1.4.16 — 🎲 Hội chợ: 53%, phi tiêu 51%, chơi dồn thì nguội vận

Chủ game (03/10): "giảm tỷ lệ thắng… hiện tại cao quá làm mất giá xu", "bầu cua, chiếu trong, gánh lô tô -> 53%", "ném vòng -> không tính điểm", "phóng phi tiêu -> 51%", "chơi liên tục 1 game thì tỷ lệ thắng sẽ giảm dần xuống, tối thiểu 40%".

- `game/fair.py`: WIN_P .60 → .53 (taper tới .45 giữ nguyên). `luck_p()`: sau RUN_FREE=10 ván liên tiếp cùng một gian (mỗi ván cách ≤ RUN_GAP=180 s) giảm RUN_STEP=1 điểm % mỗi ván, sàn P_FLOOR=.40. Chuỗi ván ở `journey.fair_run` {g, n, at} (tùy chọn, ngoài `journey.fair`).
- `game/fair_darts.py`: P_HI/P_LO .40/.30 → .51/.45.
- Ném vòng: PT_RING3/PT_RING5 = 0 (không điểm Bảng vàng); tỉ lệ giữ nguyên. Lô tô 53% ở bản sau (feat/fair-food).

# v1.4.15 — 📚 Học kế toán TT99, 🧾 hồ sơ lương, 🛕 giọng chùa, 🛁 nhà tắm & hồ bơi

Chủ game (02–03/10): "kế toán có cái thông tư 99 đưa lên luôn", "thông tư 99 gợi ý nhiều lên", "giao diện xấu quá, làm sao dễ coi hơn" (hồ sơ lương), "cách trả lời của chùa khác các bên còn lại mới đúng", "nhà chưa có nhà tắm, biệt thự 60k cũng k có hồ bơi".

- Học kế toán (TT99): trường + công ty thực hành Mây Tre Xanh, 84 bài, thi chứng nhận, gợi ý, tra cứu tài khoản; migration lười, payload công khai nhỏ, không lộ đáp án (374d610, 6f18bc5, a958ac0, 730bc5d).
- Bàn lương: mỗi ô một thẻ, một thẻ kết quả, gợi ý sâu theo số người chơi nhập (dc39d25, 6dc6d4c, a0ffed1).
- Chùa: cảm nhận/hồi đáp/quà biếu/danh hiệu tuần bằng giọng nhà chùa, không từ buôn bán (feat/pagoda-voice).
- Nhà: phòng tắm cho mọi chỗ ở, hồ bơi cho biệt thự, 15 món đồ, thư giãn mỗi ngày (feat/home-rooms).

# v1.4.14 — 🎲 Hội chợ hên xui, phi tiêu khó hơn, xu hôm nay

Chủ game (03/10): "tỷ lệ thắng đang cao quá, chỉnh tỷ lệ thắng là 60% và hên xui", "phi tiêu thì làm sao cho người ta khó trúng hơn", "sao xu kiếm hôm nay không hiển thị ở loto, rồi điểm nữa sao không thấy tính khi win".

- Bãi hội đi dạo được (feat/fair-walk 77eee50): `public/js/scenes/fair-place.js`, `public/js/v4/fair-walk.js`; bấm gian nào thì đi tới rồi mở gian đó, "📋 Danh sách trò" là lối phụ. `fair.odds(net, hi, lo)` dùng chung cho phi tiêu.
- `game/fair.py`: WIN_P .70 → .60 (taper tới .45 ở +5000 giữ nguyên).
- `game/fair_darts.py`: P_HI/P_LO .70/.45 → .40/.30; `fair-darts.js`: tâm ngắm chạy nhanh hơn (chu kỳ ~1,7×).
- Lô tô thắng: kết quả mang `points` (thẻ Kinh hiện "+N điểm hội chợ"; trước đó máy chủ vẫn cộng điểm nhưng không báo).
- `public.fair.today_xu`: xu từng gian trong ngày đời (đọc từ dòng Sổ ví, không lưu gì mới); `fair.js` hiện "💰 Hôm nay kiếm ở …".

# v1.4.13 — 🎪 Hội chợ: dễ ăn, không giới hạn, nhanh hơn

Chủ game (03/10): "lâu dài người chơi ăn", "thắng 70% số ván", "thắng khoảng 2000 xu thì cho thua dần bớt đi", "riêng ô ăn quan vẫn giữ như hiện tại", "mỗi ngày chơi không giới hạn tiền", "không giới hạn lượt chơi", "kiếm k giới hạn, điểm và lượt chơi không giới hạn", "kinh hụt thoải mái", "đọc số nào thì bảng của người ta màu phải sáng lên", "ném vòng là 1 chai có thể có nhiều vòng", "đẩy tốc độ hội chợ lên", "bấm 1 ô rồi bỏ chọn ô đó để qua ô khác được chứ".

- Bầu cua / xóc đĩa (feat/fair-walk 4cca065): máy chủ bốc thắng/thua theo `win_p` (70% khi lãi thử vận hôm nay ≤ +2000, giảm tuyến tính còn 45% ở +5000 rồi giữ), rồi chọn xúc xắc/đồng xu khớp kết quả. Xóc đĩa 1:1, công an 2% (từ 4%), phạt stake//4 (tối thiểu 3).
- Bỏ: trần thua 150 xu/ngày, 400 lượt/ngày, 80 lượt ném vòng/ngày, trần xu kiếm ô ăn quan/ném vòng, trần điểm/ngày. Chỉ ví giới hạn (không bao giờ âm). Các bộ đếm trong save dừng ở mốc cũ để máy chủ 1.4.12 (rolling release) vẫn nhận save.
- Ném vòng: một chai ăn nhiều vòng, 3 xu mỗi vòng trúng, +8 khi đủ 5.
- Lô tô (feat/fair-loto2 eef4a92, d2fe874): kinh hụt không giới hạn (phạt 1 xu, không quá ví), số vừa gọi sáng lên trên tờ dò (không tự đánh dấu).
- Quà vào hội 500 xu (một lần mỗi save mỗi kỳ hội) và Vay nóng của Bà Sáu: 50–500 xu, lãi 20%, một khoản một lúc, trả bất cứ lúc nào; hội tàn thì `fh.settle` thu từ ví, rồi ngân hàng, phần còn lại ghi nợ (ví không bao giờ âm). Save: `journey.fair_cash` (5e6738d).
- Phóng phi tiêu (game/fair_darts.py, 26ab755): đặt 2–50 xu, 1:1, 70%→45% như trên, +1 điểm mỗi phát trúng, danh hiệu hồng tâm.
- Nhanh hơn: GAP_MS 1200 → 400, lắc bát 850 → 450 ms.
- Ô ăn quan: luật như cũ; chọn ô rồi vẫn đổi / bỏ chọn được tới khi bấm hướng rải (máy chủ vẫn chặn đi hai lần bằng ply).

# v1.4.12 — 🏮 Hội chợ: mượt, rõ, không chọn lại

- Bấm không nhảy trang: vá DOM tại chỗ thay vì dựng lại cả trang (`fair.js`). Lắc bát / rải quân nhanh hơn, nút chờ máy chủ hiện đang làm.
- Chiếu trong: không còn bấm Xóc rồi bị từ chối (hạn mức ngày < cược + phạt): khóa nút và nói rõ lý do; dải "mấy ván gần đây"; kết quả ghi bên đã chọn.
- Ô ăn quan: đã bốc quân thì không chọn lại; máy chủ không cho đi hai lần trên cùng một bàn.

# v1.4.11 — 🏮 Hội chợ: sửa nhanh

- Chủ game (03/10 00:0x): "bấm vào đặt thì tự nhiên nó scroll lên", "chơi xong 1 trận làm sao chơi lại, bầu cua". `fair.js keep()` giữ cả `scrollTop` của dialog; dưới kết quả bầu cua có "🔁 Lắc tiếp" / "Đặt lại"; hết hạn mức ngày thì ghi lý do cạnh nút.
- Đếm ngược về 0 thì client tự `api.refresh()` để mở hội chợ, không cần tải lại trang.

# v1.4.10 — 🛕 Vào chùa Gió Lành

Chủ game (02/10): "chùa là phải mở cái chùa luôn chứ", "vào đó tự bấm khấn… có trụ trì, có tụng kinh", "đi tới đâu có đấy", "chùa có nhạc chùa nữa".

- Màn "Vào chùa" (Đời thường → Đi chùa): sân chùa, chánh điện, nhà ăn; mỗi việc ở đúng chỗ. Khấn tự chọn (sức khỏe, bình an), tụng kinh tự gõ mõ 12 nhịp (+1…+4 tinh thần), Thầy Huệ Minh nói chuyện theo ngày âm lịch. Miễn phí, 4 việc/ngày (trước 3).
- Âm thanh CC0/public domain thật (Freesound, Wikimedia Commons; nguồn trong `public/music/CREDITS.md`): chuông, mõ, chuông gia trì, tiếng tụng, tiếng sáng ở sân; theo công tắc "Âm thanh", tải khi vào chùa.
- Lùi bản trong ngày: save đã khấn/tụng hoặc làm 4 việc bị 1.4.9 từ chối tới hết ngày sống đó.

# v1.4.9 — 💍 Cầu hôn lại sau 3 tiếng, 📦 sửa đơn gộp

- Chủ game (02/10): "cầu hôn bị từ chối thì 3 tiếng sau mới được cầu hôn lại" — `wedding_content.DECLINE_HOURS = 3` (thay `DECLINE_DAYS = 3`).
- Tiệm nail báo lỗi "Danh sách hàng không hợp lệ." khi bấm "Gộp N món thiếu": gợi ý gửi 20 dòng, đơn tối đa 8. Server nhận tới 40 dòng khi `fit` (phần dư báo lại như cũ); client `fitDraft` (`public/js/v4/restock.js`) soạn đơn vừa chỗ và vừa quỹ.

# v1.4.8 — 🏘️ Nhiều nhà, 🛫 bên trong nơi làm việc

Chủ game (02/10): "cho phép sở hữu nhiều bất động sản/nhà nhé"; góp ý người chơi về sân bay: "nên làm thêm phần bên trong nữa ạ" → "mấy map cụ thể thì có bên trong bên ngoài, bổ sung này kia vào đa dạng lên".

- `game/housing.py` VERSION 2: `own` là nhà đang ở, các căn khác trong `props` (để trống hoặc cho thuê, tiền thuê mỗi tháng = 5%/năm giá niêm yết). Tối đa 4 căn. Hạn mức vay 40% tính mọi khoản vay nhà. Dọn nhà 20 xu. Save v1 nâng cấp tại chỗ, không mất gì.
- Khu bên trong (`public/js/scenes/areas.js`, `interior.js`, `airport.js`, `backroom.js`): sân bay 5 khu; milk tea, cafe, quán ăn, tạp hoá, hoa, mẹ & bé, quần áo, salon, thú cưng, sửa chữa, homestay, shipper có thêm khu. Chỉ phía client, không đổi nhiệm vụ/kinh tế/save.
- Lùi bản: save có nhà v2 bị bản cũ từ chối — lùi bản phải khôi phục dữ liệu.

# v1.4.7 — 💅 Tiệm nail, 🛕 chùa, 🎱 lô tô, 🧑‍🎤 avatar chat

Chủ game (02/10): "có 1 cái làm móng hay nail đi", "thêm thầy chùa nữa, mn đi chùa được nhé", "loto thì có nhạc, có mc, có người biểu diễn…", "avatar cho mọi người chat ấy, set nhiều hơn và đa dạng hơn".

- Nghề `nail` (`game/careers/nail.py`): tiệm chị Diệp, mở ở chương 2. Gel, móng úp, đính đá, dưỡng da tay; vệ sinh dụng cụ; hoàn tiền bong gel theo số tiền khách thật sự trả.
- Nghề `pagoda` (`game/careers/pagoda.py`, `pagoda_content.py`): phụ việc chùa, phụ cấp cố định 6–10 xu, không nhận tiền khách, không bán "đồ được ban phước". Ngày ở chùa không hiện thẻ bia, thịt, thất tình.
- Đi chùa (`game/chua.py`, `public/js/v4/chua.js`): trong mục Đời sống, miễn phí, tối đa 3 việc/ngày.
- Gánh lô tô (`game/fair.py`, `public/js/v4/fair-loto.js`): MC cô Bảy Lô Tô, 118 câu thơ tự viết, nhạc CC0 `wedding-funk.mp3`. Tổng cược ≤ 50 xu/ván, trần theo ngày, Kinh sai phạt 1 xu (không quá ví).
- Ảnh đại diện chat (`game/avatar.py`, `live/faces.py`, `public/js/v4/face.js`, `avatar.js`): SCHEMA 11→12 thêm bảng `chat_faces` (chỉ CREATE TABLE IF NOT EXISTS). Mã mặt được server dựng lại từ danh sách cho phép. Deploy game server trước live.
- Lùi bản: save có `nail`/`pagoda` trong `careers` bị 1.4.6 từ chối — lùi bản phải khôi phục, không chỉ đổi code.

# v1.4.6 — 🚗 Xe, máy bay, du thuyền

Chủ game (02/10): "thêm cả cái xe, máy bay, du thuyền cho mọi người mua nhé".

- `game/garage.py` + `public/js/v4/garage.js`: 11 phương tiện, 120 xu (xe đạp) tới 90.000 xu (phản lực riêng). Trả đủ một lần (ví trước, rồi tài khoản ngân hàng), không vay, không quẹt thẻ, ví không âm; mỗi mẫu một chiếc; 11 màu sơn; biển tên chỉ chủ thấy.
- Chip xe "đang đi" trên hồ sơ, xe đậu trước nhà, trên thẻ Phố nghề. Một chuyến đi chơi mỗi ngày sống (+tinh thần, tiền xăng ghi trên nút). Bán lại 70%.
- Save cũ không đổi (`journey.garage` chỉ tạo khi mua chiếc đầu tiên). Không phí ngầm.

# v1.4.5 — 💼 Lương nghề văn phòng ổn hơn cho người mới

Chủ game duyệt (02/10): "để tiền ổn xíu cho mn chơi game này, tăng xíu nhé". Áp dụng cho Thuế & lương, Kế toán doanh nghiệp, Kế toán hợp nhất (`game/careers/office.py`: `pay`, `rookie`, `wrong_min`).

- **Tăng chung:** mỗi hồ sơ +2 xu (`RAISE`), sàn thưởng 14 xu thay vì 10 (khay chứng từ, bàn đối chiếu trước là 8). Hồ sơ sạch 32 xu; bảng lương 32 xu trước phản ứng của chị Hồng.
- **Đang thử việc** (hạng 0 của lộ trình, tới lần thăng chức đầu): mỗi lỗi trừ một nửa (2 xu, khay 2 xu), không bao giờ dưới nửa thưởng; nộp trễ −4 xu thay vì −8; trả lời sai tốn 8 phút văn phòng thay vì 15. Thăng chức rồi thì luật như cũ.
- Không đổi cách sinh hồ sơ (check_task_compat OK), không đổi dạng save. Thẻ tờ khai hiện đúng số thưởng mới (`pay`, tùy chọn).
- Hướng dẫn trong game cập nhật số mới. Sửa lỗi JS `e.target.closest is not a function` khi bấm vào nút không phải phần tử HTML.

# v1.4.4 — 💡 Bớt khó hiểu: nút ghi lý do, Hỏi nhanh, thanh toán tất cả

Theo chat người chơi và số thao tác bị từ chối trên máy chủ (stat_actions). Nguyên tắc chủ game: chỉ gợi ý, người chơi tự làm (không tự điền, không chọn sẵn, không lộ đáp án).

- **Nút ghi lý do** (server vẫn là nguồn luật; trường public mới đều tùy chọn):
  - **Trà sữa:** Ủ/đặt hàng ghi "Thiếu N xu", "Kho đầy", "Đang chờ N/N đơn"; dòng quỹ tiệm/ví; chặn bấm đúp. `boba.py` thêm `held`, `shelf_cap`, `max_orders`, `cup_cap`.
  - **Chứng chỉ:** lớp không trả được thì khóa, tự học miễn phí lên đầu; sửa lỗi chặn người trả bằng thẻ.
  - **Sớm Mai:** rót hình chỉ khi đã chiết shot và đánh sữa.
  - **Tạp hóa:** "Soạn giỏ" chỉ khi soạn được (`_pack_gate`), nếu không thì "Kệ hết …: nhập ở Kho" và nút Sang Kho.
  - **Kho (mọi nghề):** một dòng cách nhập hàng; đếm sai thùng gộp báo trước. **Giỏ đặt hàng** đủ 8 món thì nút chuyển sang xem đơn; gộp nhiều món thêm phần vừa giỏ (`cart_lines`).
  - **Mẹ & bé:** đổi món đã hợp thì chị Ly giải thích tại chỗ (`fits`); tiệm chưa mở thì khóa tư vấn quà; giá hiện khoảng cho phép.
  - **Salon:** hết hàng thì khóa gội/keratin; thẻ 🎨 Bảng màu (tra cứu chung).
  - **Trạm lắng nghe:** mỗi phương án ghi "khi nào dùng".
- **Thuế và kế toán (chỉnh nhẹ):** dòng 📐 dưới mỗi ô; ô sai được đánh dấu (`bad` trong kết quả `ca_step`/`ga_step`); văn phòng đóng cửa thì chỉ còn Khép ca; bàn kế toán khóa nút khi chưa đủ điều kiện. Lương và cách chấm không đổi.
- **❓ Hỏi nhanh:** 15 câu trong Hướng dẫn, nút ở cuối menu và Cài đặt → Cách chơi; "Đi tới" chỉ mở màn hình. Màn mở đầu: "Vào làm thôi" không còn bấm mà không có phản ứng gì khi chưa chọn Nam/Nữ.
- **🧾 Thanh toán tất cả** (`ops_pay_all`): khoản quá hạn trước, khoản quỹ không đủ thì để lại, không âm quỹ.

# v1.4.3 — 🍢 Ăn thêm, số liệu giữ mãi mãi

**🍢 Ăn thêm (góp ý của chủ game sau #72).** Trong ngày làm, người chơi chủ động mua thêm đồ ăn bất cứ lúc nào, trả bằng ví: bánh bao 3 xu (+20 no bụng), xôi mặn 5 xu (+35), tô phở 8 xu (+50), cà phê sữa đá 3 xu (+15 tỉnh táo). Không giới hạn số lần; chỉ từ chối khi đã no (≥ 90) / đã tỉnh (≥ 90) hoặc ví không đủ (không bao giờ nợ). Không cộng tinh thần, không thêm trường nào vào bản lưu (`jr_needs_snack`). Hiện trong ô việc đang làm khi no bụng < 50 hoặc tỉnh táo < 40, và luôn có trong trang Đời thường.

**📊 Số liệu người chơi giữ mãi mãi.** Không còn xoá theo hạn (`stat_active`, `stat_play`, `stat_actions`, `stat_leaves`, `stat_client_errors`, `stat_loads`…): `ADMIN_STATS_*_DAYS`, `RETENTION_*_DAYS` mặc định 0 = giữ mãi. Bản lưu bị xoá không còn kéo theo số liệu: trigger `*_gone` của SQLite bỏ, hàm `*_gone` của PostgreSQL thay bằng hàm rỗng một lần khi khởi động (chỉ khi còn DELETE), `retention.forget` không xoá. `stat_play` vẫn được cộng dồn theo ngày sau 60 ngày cho trang nhanh. Trang Quyền riêng tư ghi rõ số liệu ẩn danh được giữ lâu dài.

# v1.4.2 — 📊 Tổng quan đầu tư cho admin, sửa lỗi quán trà sữa

**📊 Admin: Tổng quan đầu tư.** Mục mới 9 tab (tổng quan, tăng trưởng, hoạt động, giữ chân, gắn bó, kinh tế, chất lượng, nguồn, hạ tầng), chọn kỳ 7/30/90 ngày/tất cả, ⓘ định nghĩa + cách tính, khoảng tin cậy 95% cho tỉ lệ, nhãn "ít dữ liệu" khi dưới 30 người; doanh thu ghi "Chưa bật". Xuất CSV và báo cáo in (không dữ liệu cá nhân, ô dưới 5 người ghi "<5"). Định nghĩa đầy đủ: `docs/ADMIN_METRICS.md`; đối chiếu trên DB: `scripts/verify_admin_metrics.sql` (chỉ đọc, 5 s). Bộ đếm mới (bắt đầu từ bản này): xu vào/ra, thiết bị/HĐH/trình duyệt/ngôn ngữ, độ trễ p50/p95/p99, 5xx, thời gian hoạt động, đỉnh online, lượt AI. DDL thêm (idempotent): `stat_counters`, `stat_kpi_daily`, `stat_players` + chỉ mục `stat_players_first`, `stat_players_last`. Sửa cách tính: save chỉ được nâng phiên bản (chưa thao tác) không còn tính là người chơi; "người chơi mới" chỉ tính ai chơi ngay trong ngày tạo; giữ 60 ngày bắt đầu (D30 tính được); lượt AI cộng mọi tiến trình qua DB; góp ý theo ngày VN; trang admin luôn hiện giờ VN; nhãn D1 và nhãn mẫu đúng; số mỗi ngày đông cứng một lần. Bảo vệ hiệu năng 30/09 giữ nguyên.

**Đo lường tùy chọn (Firebase/Google Analytics).** Chỉ bật khi đặt `SITE_URL` và cấu hình `FIREBASE_*` công khai, và chỉ sau khi người chơi đồng ý; tôn trọng Do Not Track/GPC; không gửi định danh, chữ hay save. Thêm canonical, robots.txt, sitemap.xml. Hiện chưa cấu hình trên production nên chưa thu gì.

**🧋 Quán trà sữa.** Màn Kho & đặt hàng / Bảng giá và thẻ chờ khách không còn lỗi "reading 'data'" khi phòng chưa tải xong (~40 lần/ngày từ 01/10).

# v1.4.1 — 🍚 No bụng và 😴 Tỉnh táo

**Ăn uống và giấc ngủ (hành trình, feedback #72).** Cạnh thanh Tinh thần có thêm 🍚 No bụng và 😴 Tỉnh táo (`game/needs.py`, `journey.needs`), giảm theo giờ quán (−7/giờ và −4/giờ). Bữa sáng tự động, miễn phí. Từ 11:30 có dải chọn bữa trưa một chạm trong thẻ ca (cơm hộp miễn phí, cơm bình dân 4 xu, bánh mì + cà phê 3 xu, hoặc nhịn); không chọn thì 13:30 tự ăn cơm hộp; ăn không làm chạy đồng hồ quán. Khép ca xong, màn Buổi tối (nút 🌙) cho chọn bữa tối (món miễn phí theo chỗ ở: cơm Bà Tám, mì gói KTX, tự nấu; bún riêu 4 xu, cơm tấm 9 xu, ăn cùng vợ/chồng) và giờ đi ngủ 22:00–01:00 (tỉnh táo sáng mai 100/91/82/73); nút "Như mọi khi"; quên chọn thì sáng hôm sau tự lấy lựa chọn quen, không tốn xu. Tinh thần: −1 mỗi thanh mỗi ngày khi dưới 25, +1 ăn đủ bữa, +1 ngủ trước 23:00 (hoặc +1 thư giãn khi thức khuya). Cơm nhà đã nằm trong tiền cơm nước nên không thu hai lần; món trả tiền ghi Sổ ví loại `living`, thiếu tiền thì không mua được. Lệnh `jr_needs_lunch`, `jr_needs_eve` chống bấm lặp. Chế độ không cốt truyện không có. Không DDL; 1.4.0 bỏ qua `journey.needs`.

# v1.4.0 — 🪴 Bày trí tự do kiểu Nhà Có Mèo

**Bày trí phòng tự do** (owner 02/10: "linh động hơn… thoải mái kéo thả như Nhà Có Mèo"). Giữ món đồ rồi kéo thả đi đâu cũng được trong nhà riêng, phòng trọ, gác lửng và góc giường KTX; tọa độ số nguyên nhỏ (20 đơn vị một ô), một lệnh `jr_deco_put` khi thả. Đồ chồng lên nhau, vẽ theo chiều sâu với thứ tự `z` riêng; đồ nhỏ đứng trên bàn, kệ treo, kệ bếp, gối, kệ đầu giường và đi theo (lật theo) khi dời món bên dưới. Lật, Lên, Xuống, Đổi phòng, Cất túi, Bán 50%, Hoàn tác, 🎨 Màu (bảng màu chung 1.3.3; màu vẫn ở `colors.deco[uid]`, bán đồ thì xóa màu). Tab "Tường & sàn": 22 kiểu sơn, giấy dán tường, sàn và ga giường (miễn phí hoặc 20–60 xu, mua một lần dùng mọi phòng, không cộng Ấm cúng). Nắng theo giờ, đèn sáng ban đêm, bóng đổ mềm; Mochi đi dạo, ngủ trưa, bé mèo Bơ tới khi phòng đạt 24 điểm. Thêm "Kệ gỗ treo trơn" (66 món). Server kiểm tra vùng đặt, chặn cửa ra vào/cửa sổ/cầu thang, giới hạn đồ mỗi chỗ và 60 món mỗi phòng, chống bấm lặp, `DECO_PER_MINUTE` (150). Save: khối mới `journey.decor = {v, at, sig, items, skins, owned, ops}`; `journey.deco` giữ định dạng 1.3.2 (bản lưới) nên 1.3.2 vẫn đọc được (bố cục làm tròn theo ô). Save 1.3.2 tự chuyển sang, không mất món. Sửa lỗi 1.3.2: class `dc-bar`/`dc-chip`/`dc-card`/`dc-note` trùng `dayclock.css` làm ẩn thanh Hoàn tác / Cất hết / Xong. Không DDL.

# v1.3.4 — 🎓 Giấy chứng nhận và ảnh lưu niệm

**Giấy chứng nhận & ảnh lưu niệm.** Mỗi chứng chỉ thi đạt có một Giấy chứng nhận đầy đủ do trung tâm hư cấu "Trung tâm Đào tạo Nghề Phố Có Chuyện" cấp (không quốc huy, không tên cơ quan thật): viền hoa văn, tên người chơi, ngành, điểm và xếp loại (Xuất sắc ≥90, Giỏi ≥80, Khá ≥70, Đạt), ngày sống và ngày cấp thật, số hiệu `PCC-…` tính từ dữ liệu sẵn có, chữ ký và mộc đỏ, ghi chú "không có giá trị pháp lý ngoài đời thực". Thi đạt hiện màn chúc mừng có confetti. Giấy xem được từ Trung tâm chứng chỉ và huy hiệu hồ sơ, kể cả chứng chỉ thi đạt trước bản này. Tab "📸 Ảnh lưu niệm" vẽ nhân vật theo trang phục hiện tại, đội mũ cử nhân cầm giấy trong lễ trao chứng chỉ. Tải về máy: PNG trên desktop, bảng chia sẻ trên điện thoại, nhấn giữ để lưu trên iPhone; ảnh lưu niệm lưu được vào Kỷ niệm (album nhận thêm JPEG). Save thêm trường tùy chọn `earned_on`. Không DDL.

# v1.3.3 — 🎨 Bảng màu chung

**Bảng màu chung.** Màu không còn mua riêng cho từng món: mở khóa một màu (40 xu, Vàng gold và Bạc ánh kim 60 xu, nhân viên Tiệm Áo Chỉ Mây giảm 20%) là dùng miễn phí cho mọi áo, quần, giày dép, phụ kiện và đồ nội thất, ở nhà riêng, phòng trọ, gác lửng lẫn ký túc xá. Màu gốc luôn miễn phí. Món đổi màu hiện tên "tên trơn · màu". Đồ đạc giữ màu khi cất vào túi hay dọn nhà, màu hiện cả trong ảnh polaroid. Người đi dạo cùng phố thấy đúng màu bạn mặc (`look.tint` tối đa 8 mục). Màu đã mua theo từng phụ kiện ở 1.3.1 tự chuyển vào bảng màu. Save: khóa gốc `colors = {v, have, wear, deco}` (màu đồ nội thất theo uid, không đụng khối deco/reno); `wardrobe_colors` giữ dạng 1.3.1. Quay lui về 1.3.2: áo quần và đồ nội thất hiện màu gốc, phụ kiện giữ màu. Không DDL.

# v1.3.2 — 🪴 Bày trí phòng

**🪴 Bày trí phòng.** Trang trí nhà giờ là một căn phòng thật (`game/deco.py`, SVG góc 3/4): lưới ô, tường và sàn riêng, cửa sổ đổi theo ngày/đêm. Chọn món trong Túi đồ hoặc Cửa hàng (65 món, 6 nhóm: 27 món cũ giữ giá và điểm, 38 món mới), chạm hoặc kéo để đặt; dời, lật, thu hồi về túi, bán lại 50%, hoàn tác, thu hồi tất cả; phím mũi tên/F/Delete/Esc trên máy tính. Bày trí được ở nhà riêng (mọi phòng), nhà vợ/chồng, gác Bà Tám, phòng trọ (cả gác lửng) và góc giường ký túc xá; chỗ thuê chỉ trang trí, không sửa nhà; chuyển chỗ ở thì đồ tự vào túi. Điểm Ấm cúng = số loại đồ + 9 bộ góc (+2/+3) + nâng cấp nhà (+2 mỗi cấp); nhà riêng +1 tinh thần mỗi sáng từ 10 điểm, +2 từ 24 (độ bền ≥ 50, không trễ góp), chỗ thuê tối đa +1. Mèo Mochi chấm điểm, hàng xóm thỉnh thoảng ghé khen (không thưởng). Chụp polaroid (webp) vào album nghề hoặc tải về. Save thêm `journey.deco` (bản cũ bỏ qua); khối `reno` giữ dạng 1.2.0, đồ đặt theo slot tự chuyển sang lưới; lệnh `jr_reno_*` của trang cũ vẫn chạy. Không DDL.

# v1.3.1 — 🎨 Phụ kiện đổi màu

**Màu phụ kiện (feedback #70).** Kính gọng tròn, kính râm, nón lá, mũ len, nơ cài tóc và túi đeo chéo đổi được 11 màu (Đen tuyền, Nâu gỗ, Vàng gold, Bạc ánh kim, Hồng pastel, Đỏ son, Cam đào, Xanh bạc hà, Xanh navy, Tím lavender, Trắng kem). Màu gốc miễn phí; mỗi màu khác mở khóa một lần cho từng món (20 xu, ánh kim 30 xu, nhân viên Chỉ Mây giảm 20%, trả qua `bank.pay`, một dòng sổ ví `life`), sau đó đổi qua lại miễn phí. Xem trước trên gương, gợi ý màu hợp tóc. Màu hiện ở mọi nơi có nhân vật (avatar, đi dạo, phòng cưới, ảnh Kỷ niệm, thẻ người chơi, bảng xếp hạng). Save thêm khóa gốc `wardrobe_colors` (bản cũ bỏ qua); lệnh mới `jr_wd_color`, `jr_wd_wear` nhận `tint`; khung trực tiếp mang `look.tint` đã kiểm tra (`live/street.py clean_look`): web và live phải lên/quay lui cùng nhau. Không DDL.

# v1.3.0 — 🏮 Hội chợ dân gian, 🍨 nghề bán kem, 🛏️ ký túc xá, 🔔 ting ting, 🦁 tiệc cưới sôi động

**🏮 Hội chợ dân gian (03/10–07/10, feedback #63).** Khu phố mở hội 5 ngày, chơi bằng xu trong game (`game/fair*.py`, `public/js/v4/fair.js`). Cổng hội vào từ banner Hành trình và mục Khu phố. Chơi kiếm xu, không cần cược: Ô ăn quan với Bé Bi (+15 xu) hoặc Ông Hai (+30 xu, nhìn trước 3 nước), tối đa 90 xu/ngày; Ném vòng cổ chai 2 xu mỗi chai, đủ 5 chai thêm 5 xu, tối đa 45 xu/ngày (server tạo ván và chấm). Thử vận may: Bầu cua 1–20 xu (bão ăn 10), Lô tô tờ 5 xu ăn 23, Chiếu trong 10–50 xu với 4% công an phường ghé (mất cược, phạt max(5, nửa cược), dẹp chiếu 2 phút). Thua tối đa 150 xu/ngày, 400 ván/ngày, không cho vay, chống gửi trùng. Bảng vàng (board `fair20261003`, tối đa 30 điểm/ngày); hội tàn 60 giây thì Top 1 nhận 👑 Vua trò chơi, Top 2–10 nhận 🎪 Cao thủ hội chợ (một lần, `leaderboard_meta` `fair:<edition>`). Năm danh hiệu riêng của hội. Env: `MNL_FAIR_START` (mặc định 2026-10-03), `MNL_FAIR_DAYS` (5), `FAIR_PER_MINUTE` (40). Save thêm `journey.fair` và loại Sổ ví `fair`: mọi worker phải chạy bản này trước giờ mở hội.

**🍨 Nghề bán kem: Tiệm kem Góc Phượng (chương 3).** Cô Hiền kèm ba khách đầu (cân viên kem, đậy nắp tủ, lời dặn, tiền thối; lỗi được nhắc trước khi đưa kem, không ghi điểm). Mỗi ngày nấu một mẻ theo sổ cô Hiền: kem dừa, kem bơ, kem khoai môn (cần Chứng chỉ làm kem; sandbox từ ngày 5): đong theo lon, ly, muỗng; nấu 76–88 °C (89 °C tách dầu, 96 °C khét đổ bỏ); ngâm đá dưới 10 °C; đánh kem đúng phút. Hộp đông qua đêm, hôm sau bán, viên nhà làm +1 xu, tủ tối đa 3 hộp. Chứng chỉ làm kem mới (8 ghi chú, đề 6 câu, đúng 4 đạt, 15 xu), không cộng tỷ lệ nhận việc mà mở công thức khoai môn. Đánh giá của khách thêm "Kem mịn, lạnh".

**🛏️ Ký túc xá Hẻm 7.** Chỗ ở thuê rẻ nhất: giường tầng 7 xu/ngày, cọc 20 xu, ở chung với Quân, anh Tuấn và My (10 khoảnh khắc cùng phòng). Không thêm trường save mới; `rent.kind = 'ky_tuc_xa'` (bản cũ không nhận id này, quay lui cần script).

**🔔 Chat và Góc hẹn hò (feedback #64, #66).** Nhóm chat nhận web push như tin riêng; nút 🔔/🔕 trên đầu mỗi cuộc trò chuyện: Bật / Tắt 8 giờ / Tắt (`chat_members.muted_until`, không DDL). Góc hẹn hò cho biết ai đang chờ, ai vừa ngồi và giờ đông nhất; nút "📣 Rủ mọi người" (10 phút một lần). Sửa số đếm trong danh sách chat bị vẽ lệch ra góc.

**💸 Ting ting.** Tiền về là nghe tiếng chuông CC0 (`public/audio/sfx/ting.mp3`, ghi công trong CREDITS) kèm giọng đọc số tiền của trình duyệt ("Đã nhận 50 xu", dưới 10 xu chỉ ting). Hai công tắc mới trong Cài đặt → Âm thanh. Thư mục `audio` vào VERSIONED_DIRS.

**🧾 Bàn tính lương minh bạch hơn (feedback #71).** Sau khi chuyển bảng lương, mỗi ô được tô theo kết quả (bỏ sót / đánh dấu nhầm / bắt đúng); chạm vào ô để xem giá trị đúng, cách tính từng bước và hồ sơ, quy định làm căn cứ. Thông báo trả lương và phiếu lương ghi tên ô sai. Các phiếu khác nêu ô chưa khớp mà không lộ đáp án; bước tính thuế hiện cách tính theo bậc. Thêm "Xem lại hồ sơ đã làm". Sửa lý do của lỗi "thiếu người phụ thuộc" khi có hồ sơ mới nộp đúng hạn. Cách chấm điểm không đổi.

**📅 Ô ngày giờ ở văn phòng.** Gõ bằng bàn phím số thì tự thêm "/" và ":"; nút 📅 mở lịch chọn ngày (`office_work.js`). Máy chủ vốn đã nhận các định dạng này.

**💇 Tiệm tóc (feedback #67).** Khách chê "còn dài" thì luôn cắt thêm được, kể cả sau khi tỉa tầng; lời chê được lưu qua tải lại trang; nhật ký dài không còn chặn mọi bước.

**🦁 Tiệc cưới sôi động.**
- 👰 Bảng tên cô dâu chú rể: viên thuốc vàng – hồng, chữ đậm 14px, 👰/🤵 (💍 khi chưa rõ), "Cô dâu"/"Chú rể" bên dưới; chữ màu mận đậm trên nền sáng nên đọc rõ cả giao diện sáng lẫn tối. Hai người đứng sát nhau thì hai bảng tự dạt sang hai bên, không đè lên nhau.
- 🦁 Múa lân mới (public/js/scenes/stroll.js `paintLion`, vẽ canvas 2D, không ảnh): đầu lân to nhiều màu (bờm, sừng có quả bông, tai xanh, gương trán, lông mày trắng, mắt chớp, má hồng, hàm mở/đóng có răng và lưỡi, râu), thân vải đỏ vảy vàng có tua viền, hai cặp chân bước (người múa đầu và đuôi), đuôi phe phẩy. Lắc đầu, gật theo trống, chồm lên và đớp phong bao lì xì treo trên cột rồi ngậm đi. Ba lượt lân dài hơn: 40–110 s, 280–350 s, 450–505 s của tiệc (cũ là hai lượt ngắn), xe trống đi theo. Lân dạo phố (sự kiện đường phố) dùng chung hình mới.
- 🔊 Bốn loa ở bốn góc sân rung theo nhịp (đèn LED, sóng âm). 🪩 Sân khấu: quả cầu disco lấp lánh, 6 luồng đèn màu quét từ sân khấu, đổi màu theo phách, sàn nhảy ô màu sáng theo nhịp; nháy tối đa ~2 lần/giây và chỉ trong vùng sân khấu; bật "giảm chuyển động" (hệ thống hoặc cài đặt) thì đèn đứng yên, chỉ đổi màu chậm, không pháo giấy.
- 🎶 Nhạc cưới thu sẵn thay nhạc tổng hợp (public/music/wedding-*.mp3, mono 64 kbps, tổng ~2,3 MB, tất cả CC0/phạm vi công cộng, ghi công ở public/music/CREDITS.md): "Funky House" (Of Far Different Nature), "Funky Disco Beats to Boogie/Woogie to" (Fupi), Wagner "Treulich geführt" (bản thu Musopen, CC0) lúc rước dâu, trống chiêng lân (Jor92, Freesound, CC0) khi lân múa. Vị trí bài = giây của tiệc chia lấy dư độ dài bài nên mọi khách nghe cùng chỗ, cùng nhịp với đèn (BPM cố định của từng bài); lệch quá 0,35 s thì tự chỉnh. Giữ nguyên mở khóa âm thanh, nút tắt nhạc; nhạc nền game tự nhỏ đi khi đang ở tiệc (`audio.duck`).
- 🍲 Mâm cỗ: chạm vào một bàn tiệc là mở mâm (8 món, 🍺 bia, 🥤 nước ngọt) và ngồi vào chỗ trống. Gắp món +1 tinh thần (tối đa 3 lần mỗi tiệc), bia −1 tinh thần (tối đa 2 lần) và cả phòng thấy hai ly cụng "Dzô! 🍻", nước ngọt không tính gì. Máy chủ live quyết định: khung `wed_eat {k, d}` (8 lần/10 giây), phải đang ở trong tiệc, tiệc đang mở và chưa tàn; mỗi lần trả là một dòng `live_effects` khóa cố định `weat:{tiệc}:{sid24}:{n}` / `wbeer:…` nên khởi động lại không trả hai lần (đọc lại theo khóa chính, không quét bảng). `live_effects` nay nhận tinh thần âm tới −10 (chỉ kind spirit). Bàn tiệc vẽ đầy đủ hơn: mâm xoay, gà, xôi gấc, nem, tôm, bò xào, nồi lẩu, bát cơm, đũa, ly bia từng chỗ.
- 🎧 Chú rể chọn nhạc (owner 02/10: "nhạc remix gì đó, nhiều nhạc không bản quyền rồi cho chú rể chọn nhạc"): nút 🎧 trên thanh tiêu đề mở danh sách "Chọn nhạc cho tiệc": Theo chương trình, Funky house, Disco sôi động, Quẩy EDM, Remix bay phòng 140, Electro house, House Latin, Funk nhún nhảy, Nhạc chậm cho cặp đôi. Chú rể giữ quyền chọn (nhân vật nam trong cặp); chú rể không có trong phòng thì cô dâu chọn; cặp cùng giới thì ai cũng chọn được. Máy chủ live quyết định: khung `wed_music {k}` (6 lần/20 giây mỗi kết nối, mỗi tiệc 20 giây mới đổi một lần `MUSIC_GAP`, chỉ bài trong `WL.MUSIC`, tiệc đang mở và chưa tàn), cả phòng nhận `wed_music {k, at, by, name, who}`, người vào sau nhận lựa chọn trong thông tin phòng. Mọi khách phát bài đó từ `at` (vị trí = giây hiện tại − `at`, chia lấy dư độ dài bài); nhạc rước dâu và trống lân vẫn ưu tiên rồi quay lại bài đã chọn; đèn, sàn nhảy và loa theo BPM của bài; MC nói "Chú rể đổi nhạc rồi: …! Quẩy lên nào! 🎧". Lựa chọn chỉ giữ trong bộ nhớ (khởi động lại dịch vụ live thì về "Theo chương trình").
- 🎶 Sáu bài mới cho danh sách (public/music/wedding-{edm,remix,electro,latin,funk,love}.mp3, tổng ~3,6 MB, mono 64 kbps, cắt tròn ô nhịp và nối vòng mượt; tất cả CC0 trên OpenGameArt, ghi công ở public/music/CREDITS.md và THIRD_PARTY_NOTICES.md): "Joyfully" (MintoDog, 170 BPM), "Melodic EDM Loops" (Fupi, 140 BPM), "Vengeance Electro" (Of Far Different Nature, 128 BPM), "OMW to beat the big bad" (Fupi, 120 BPM), "Funked Up" (Joth, 87 BPM), "Love Song [instrumental]" (nene, 95 BPM). Không dùng nhạc có bản quyền, không dùng bài "NCS" trên YouTube.
- 💐 Tung hoa: phút 8:45 của tiệc MC mời tung hoa; cô dâu chú rể có nút "💐 Tung hoa" (60 giây, không bấm thì tự tung). Máy chủ chọn ngẫu nhiên một khách đang có mặt có tài khoản (đứng gần sân khấu dễ trúng hơn), +20 xu một lần mỗi tiệc (`wtoss:{tiệc}`), cả phòng thấy bó hoa bay và tên người bắt được.
- 💃 Đứng trên sân khấu là nhảy theo nhịp; nút "💃 Nhảy" (cảm xúc `dance`, chỉ trong tiệc cưới) xoay một vòng cho cả phòng thấy. 🎊 Pháo giấy khi cô dâu chú rể bước vào, 🎆 pháo hoa 25 giây cuối tiệc. MC có thêm lời dẫn cho lân, mâm cỗ, sàn nhảy, tung hoa, pháo hoa.
- Không có DDL, không sửa dữ liệu người chơi. Tệp tĩnh mới public/music/wedding-*.mp3 (10 tệp, ~5,9 MB) đi theo đường /music/ sẵn có (có `?v=`, nginx `location ~ ^/(js|css|i18n|icons|music)/`, CSP `media-src 'self' blob:`), không cần đổi nginx/CSP.
- "Có gì mới": lân mới, loa và đèn sân khấu, nhạc mới và chú rể chọn nhạc, mâm cỗ, nhảy, tung hoa, pháo hoa, bảng tên cô dâu chú rể.

# v1.2.3 — Sửa lỗi tab Kế hoạch cưới

- 💍 Lỗi (stat_client_errors, 22 lần 01–02/10: `Cannot read properties of null (reading 'venue')`): cặp đã đính hôn có kế hoạch cưới đã gửi/đã chốt, mở lại tab Kế hoạch thì `planner()` đọc `S.plan` khi chưa có bản nháp nên màn Hôn nhân không vẽ được. Giờ xét trạng thái đám cưới trước, không có bản nháp thì hiện lời nhắc sang mục "Hai bạn".
- "Có gì mới": sửa lỗi tab Kế hoạch cưới.

# v1.2.2 — 😍 Thả cảm xúc trong chat; màn quản lý chat cho quản trị (tìm kiếm, xem chữ gốc)

- 😍 Cảm xúc (owner 01/10: "nhấn giữ là reaction"): nhấn giữ ~0,45 giây một tin ở Cả phố, nhắn riêng, nhóm (chạm hoặc chuột; kéo/cuộn là hủy; không bôi chữ, không hiện menu iOS) để mở thanh ❤️ 😂 😮 😢 👍 🔥. Mỗi người một cảm xúc mỗi tin: chọn lại cái đang có là bỏ, chọn cái khác là đổi. Dưới bong bóng hiện số đếm, cái của mình được tô; bấm vào một ô để thả/bỏ. Chạm (không giữ) vẫn mở hàng thao tác cũ (báo cáo, thu hồi, 📌 ghim cho quản trị).
- Máy chủ live: khung `react {id, e}` (30 lần/10 giây), chỉ thành viên của nhắn riêng/nhóm, không với tin đã ẩn/thu hồi, người đang bị khóa chat và khách không thả được; báo cho cả kênh `reacts {ch, id, r, by, e}`. Bảng `chat_reacts` (khóa (msg, pid), chỉ mục theo pid). Tin gửi theo trang (`joined`, `history`, `missed`) kèm `r` (đếm) và `my`; đếm được nhớ trong bộ nhớ (LRU 20.000 tin), đọc bằng một truy vấn gom nhóm theo id của trang. Dọn Cả phố xóa luôn cảm xúc của các tin bị dọn; xóa dữ liệu người chơi xóa cảm xúc của họ.
- 🔎 Quản trị › Chat › "Tin nhắn" (thay tab "Cả phố"): mọi kênh, 200 tin một trang, "Tải cũ hơn" theo id; lọc Cả phố / Nhắn riêng / Nhóm, theo người (bấm tên) và theo cuộc trò chuyện; ô tìm chữ, tên hoặc mã người chơi (`GET /api/admin/chat/messages`, chỉ ADMIN_USERS, mỗi lần chỉ xét tối đa 20.000 id theo khóa chính).
- Chữ gốc: từ bản này tin bị bộ lọc che (•••) lưu thêm chữ người chơi gõ ở cột chỉ quản trị đọc `chat_messages.raw` (NULL khi không bị che); màn quản trị hiện "Gốc: …". Không bao giờ gửi cho người chơi. Tin cũ chỉ còn bản đã che. Thu hồi tin hoặc xóa dữ liệu thì xóa luôn chữ gốc.
- SCHEMA_VERSION 11: `chat_reacts`, `chat_reacts_pid`, `ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS raw` (không mặc định, không ghi lại bảng). Dịch vụ live chờ bảng `chat_reacts`: khởi động game server trước.
- 🌞 Thẻ "Nhiệm vụ hôm nay" (góp ý #69): mỗi nhiệm vụ chưa xong có dòng nói cách tính (mở cửa rồi làm xong việc; tab Trò nhỏ; bấm 💬 ở công việc hoặc Người quen → Trò chuyện với 2 người khác nhau, chat Cả phố không tính) và lời nhắc đóng ca là tính lại, nhận quà trước khi đóng ca.
- "Có gì mới": thả cảm xúc trong chat; cách tính nhiệm vụ hôm nay.

# v1.2.1 — 📌 Ghim tin nhắn và tin quản trị ở Cả phố (cập nhật âm thầm)

- 📢 Tài khoản quản trị (`ADMIN_USERS`, cùng giá trị với game.env, nay cũng đặt trong live.env) nhắn ở Cả phố không qua bộ lọc, không giới hạn tần suất; tin mang huy hiệu "📢 Quản trị", liên kết bấm được (`chat_messages.adm`, hàng pid `admin` cũng tính là quản trị).
- 📌 Quản trị bấm vào một tin ở Cả phố để "Ghim tin này" / "Bỏ ghim"; thanh ghim ở đầu Cả phố cho mọi người (bảng `chat_pins`, SCHEMA_VERSION 10). `scripts/chat_pin.py --msg/--unpin/--show` ghim từ máy chủ; dịch vụ live nhận qua PG NOTIFY và đọc lại mỗi 30 giây.
- Không có mục "Có gì mới" (owner 01/10: không cần thông báo).

# v1.2.0 — Vào nhà, sửa nhà, trang trí; nghề Nội trợ; ba vị trí văn phòng

- 🏠 Trong nhà (game/reno.py, public/js/v4/reno.js): nhà đã mua có nút "Vào nhà": xem từng phòng (SVG, xuống cấp và nâng cấp hiện trong hình), sửa 5 hạng mục (tường, trần mái, sàn, điện nước, bếp; giá theo mức hư và độ rộng nhà), nâng cấp 2 bậc, trang trí 27 món (mua, dời, cất kho, bán lại 50%). Xuống cấp 1 điểm mỗi 4/6/8 ngày sống (không dưới 30%). Ấm cúng ≥10: +1 tinh thần mỗi sáng, ≥24: +2. Khối `journey.reno` chỉ tạo khi người chơi thao tác lần đầu.
- 🧹 Nghề Nội trợ (`homemaker`, nhà chị Thảo, mở chương 2): đi chợ (5 kiểu, nhớ danh sách, chọn đồ tươi, mặc cả, sổ chợ khớp từng xu), nấu ăn theo khẩu vị và dị ứng, rửa bát, giặt phơi, lau dọn, chăm bà, đưa đón trẻ, tủ lạnh, cây, sự cố, dọn Tết; truyện "Cuốn sổ chợ bìa xanh"; tiếng Anh.
- 💼 Ba vị trí văn phòng ở Công ty CP Cánh Diều (mở chương 5, phải ứng tuyển): Hành chính – Nhân sự, Thư ký giám đốc, IT văn phòng; máy chủ chấm điểm và trả lương; mỗi nghề truyện 5 đoạn, chứng chỉ "Hành chính văn phòng". Ba nghề kế toán thêm 6 tình huống.
- "Có gì mới": nhà, Nội trợ, văn phòng, tình huống kế toán.

# v1.1.4 — Đi ăn cưới tính từ 2 phút, sửa đơn sỉ bà Sáu bị treo

- Khách được tính là "đi ăn cưới" khi có mặt ít nhất 2 phút trong tiệc (`GUEST_MIN_MINUTES`, owner 01/10): 15 xu mỗi khách của cô dâu chú rể, số khách trên thẻ cuối tiệc, bảng Khách mời của tuần. Vẫn ghi `wedding_guests` ngay khi vào (lộc 20 xu/phút, phong bì không đổi). Khách thấy "✅ Đã ghi nhận bạn đi ăn cưới" sau phút thứ 2.
- Lỗi (góp ý #57): đơn sỉ tạp hóa báo giá ở mức bớt sâu nhất (hoặc lần thứ 2) luôn được trả lời dứt khoát; bản lưu đang kẹt được trả lời khi tải (`grocery.heal_save` trong `migrate_state`), tiền cọc ghi như một lần chốt thường. Sửa đồ điện: hết 6 lần báo giá thì phần khách chưa duyệt coi như từ chối, không còn kẹt ở "Trả máy".
- "Có gì mới": luật 2 phút, sửa đơn sỉ bà Sáu; dòng 1.1.3 về ghi nhận sửa cho khớp.

# v1.1.3 — Tiệc cưới 10 phút, ai vào cũng được ghi nhận, phong bì mừng cưới

- Lỗi: tiệc #14 (01/10 14:15) có 14 khách nói chuyện nhưng chỉ 4 người được ghi nhận: khách phải ở đủ 5 phút (đếm trong bộ nhớ) và bản 1.1.2 khởi động lại dịch vụ live lúc 14:20 giữa tiệc, mất hết thời gian đã ngồi; người chơi dưới 1 ngày tuổi không được tính. Nay khách được ghi vào `wedding_guests` ngay khi bước vào (cả người đứng ngoài cổng; chưa có tài khoản thì ok=0), bỏ luật 1 ngày tuổi.
- Tiệc 10 phút (mở trước 5 phút để khách tụ lại). Mỗi phút ai có mặt trong phút đó +20 xu (cả cô dâu chú rể), khách nhận tiền ở tối đa 2 đám/ngày; khóa mỗi phút cố định nên khởi động lại dịch vụ live không mất gì. Cô dâu chú rể mỗi người +15 xu mỗi khách (tối đa 360), danh hiệu "Đám cưới đông vui" ở 20 khách; thưởng trên 2.000 xu chia nhiều dòng. Bảng Khách mời của tuần: đám có mặt ít nhất 1 phút.
- "Tổ chức tiệc cưới" trong Hôn nhân: cặp đã cưới (kể cả cưới trước 1.1.0, chưa có ngày giờ) hoặc đính hôn đã chốt kế hoạch tự chọn ngày giờ tiệc (10 phút đến 14 ngày tới), miễn phí, một lần; giờ đó thành ngày cưới trên thẻ (`wedding_dates` source party). "Mời khách" miễn phí, một lần: bạn bè hai người nhận hộp thư + thông báo đẩy, cả phố nhận dòng tin. Thiệp cưới trong kế hoạch: miễn phí (các kế hoạch đã chốt giữ nguyên giá).
- Tiệc sinh động (public/js/v4/wedfeast.js, theo đồng hồ tiệc, mọi khách thấy như nhau): MC dẫn chương trình, 6 hàng xóm nói chuyện, 4 bạn nhỏ chạy quanh hát đồng dao và nói câu GenZ, 2 lượt múa lân, đèn nháy, cỗ trên bàn, bánh cưới và tháp ly, nhạc cưới tổng hợp (Wagner, Bridal Chorus, phạm vi công cộng; nhạc vui viết riêng; trống lân), nút tắt nhạc.
- 🧧 Phong bì mừng cưới (góp ý #56): khách đang dự (có tài khoản, đã ghi nhận, không phải cô dâu chú rể) chọn 10/20/50/100/200 xu và một lời chúc soạn sẵn; trừ ví khách (`marriage_effects` `wenv:<đám>:<rid>`), mỗi người trong đôi nhận một nửa (`live_effects` `wedenv:`), tối đa 500 xu mỗi khách mỗi đám, bấm hai lần không trừ hai lần. Dịch vụ live đọc lại dòng trừ tiền rồi báo cả phòng (`wed_env`); thẻ riêng cuối tiệc của cô dâu chú rể ghi tổng phong bì.
- 📜 Bảng "Lời chúc" trong tiệc cưới: lời mọi người nói và phong bì được giữ lại (3 dòng mới nhất, bấm "Xem hết" để xem 40 dòng), vì bong bóng chat biến mất nhanh và bàn phím che màn hình. Thanh trên cùng của tiệc thành 2 hàng để tên cô dâu chú rể không bị che.
- "Có gì mới": tiệc cưới mới, 20 xu/phút, ghi nhận ngay, phong bì mừng cưới, bảng lời chúc, tổ chức tiệc cho mọi cặp.

# v1.1.2 — Danh hiệu tuần của Bảng xếp hạng, đeo nhiều danh hiệu

- Bảng xếp hạng có thêm bảng 🎖️ Danh hiệu (số danh hiệu trò chơi đã có; bằng nhau thì nhiều danh hiệu bí mật hơn, rồi có sớm hơn). Bảng xếp hạng VERSION 2: lần khởi động đầu dựng lại mọi dòng (backfill nền).
- 🏅 Danh hiệu tuần (game/lb_titles.py, bảng `lb_weekly`, schema 9): top 1 / top 2–3 / top 4–10 của Trải nghiệm (Tất cả), Danh hiệu, Chứng chỉ và top 1 mỗi nơi làm ("🏆 Trùm …"). Tính lại mỗi ngày (giờ Việt Nam), chốt tuần lúc 0:00 thứ Hai (giữ mãi, không xóa). Hiện trên bảng (ai đang giữ, lần cập nhật cuối, tuần trước), cạnh tên ở Hành trình, Phố nghề và bảng tên khi Đi dạo / dự cưới. Không có xu thưởng.
- Đeo cùng lúc tối đa 3 danh hiệu và chứng chỉ (`journey.worn`); bản lưu cũ: danh hiệu đang đeo thành cái đầu tiên. Bảng tên Đi dạo: cái đầu hiện tên, các cái sau hiện biểu tượng.
- Không có "Có gì mới".

# v1.1.1 — Hotfix kế hoạch cưới

- Gửi kế hoạch cưới: lỗi từ máy chủ hiện ngay cạnh nút gửi (trước đây chỉ hiện ở đầu hộp thoại, người chơi tưởng không gửi được); chọn giờ cách chưa tới 1 tiếng thì báo trước và khóa nút gửi.
- Hai bạn cùng chọn báo tin cưới thì cả phố nhận tin "💌 A & B sẽ cưới lúc DD/MM/YYYY · HH:MM tại …" (news kind booked). Không có "Có gì mới".

# v1.1.0 — Đám cưới trực tiếp

- Đặt bàn cưới có ngày giờ thật (lưu mãi, hiện trên thẻ), Lịch cưới trong Khu phố, tiệc cưới trực tiếp 30 phút (live/wedding.py): khách có tài khoản +15 xu mỗi 5 phút (tối đa 60 xu/đám, 2 đám/ngày), cô dâu chú rể +30 xu/khách ở lại ≥5 phút, mốc 10 và 20 khách, ảnh chụp chung vào Kỷ niệm; người chưa có tài khoản xem từ ngoài cổng. Kỷ niệm 100 ngày/1 năm/500/1000 ngày cưới có quà, danh hiệu, lì xì NPC. Thi đua "Khách mời của tuần" (scripts/wedding_week.py). Schema 8. Bật bằng LIVE_WEDDING=1.
- "Có gì mới": đám cưới trực tiếp, kỷ niệm, khách mời của tuần.

# v1.0.6 — Hotfix đơn sỉ tạp hóa

- Báo giá sỉ tính theo bảng giá gốc, không theo giá kệ: tiệm tăng giá kệ (vd gạo 20 thay vì 18, trứng 4 thay vì 3) thì trước đây kể cả bớt 15% vẫn cao hơn mức khách chịu, đơn sỉ không bao giờ chốt được (góp ý #49/#52 của ShinMi). Màn báo giá ghi "giá gốc". Không có "Có gì mới".

# v1.0.5 — Lỗi lúc tải game, bấm hai lần

- Người chơi quay lại mà mã hoặc phần dữ liệu bàn làm việc của nghề tải hỏng trên mạng yếu (game vẫn mở): mở việc của khách ném "Cannot read properties of undefined (reading 'filter')" (163 lần ngày 01/10, app.js jobView rơi xuống màn chăm sóc khách hàng, supportJob). Nay hiện khung chờ và tự tải lại sau 2, 4, 8… 30 giây; mã nghề tải lại bằng URL khác (trình duyệt nhớ lần import hỏng).
- Bấm hai lần, tab khác (revision_conflict): bản đọc trạng thái cũ không ghi đè trạng thái mới hơn; bước giống hệt vừa xong ở tab này không gửi lại; xung đột lần hai không hiện lỗi, chỉ đồng bộ màn hình.
- Lỗi phía người chơi: kèm chỗ ném lỗi (file:dòng:cột của 3 khung đầu, không query), giữ tên thuộc tính trong "reading '…'"; bỏ lỗi không phải của game (zaloJSV2 của Zalo, tiện ích trình duyệt, file site khác) ở trình duyệt, máy chủ và bảng admin; "Đang tải" chỉ khi màn chờ còn hiện, sau khung hình đầu là "Vừa vào game".
- Không có "Có gì mới".
# v1.0.4 — Bớt chỗ bấm là lỗi

- Từ log 01/10: hết giờ/đủ khách thì nút thành "Làm nốt việc dở" hoặc "Khép ca" (sửa lệch 20 phút ở giờ đóng cửa); tạp hóa chưa mở ca thì nút mờ + "Mở ca"; quầy hết hàng ghi "hết hàng · nhập thêm"; thiếu nguyên liệu ghi ngay trên nút (thú cưng, tiệm bánh, homestay); "🚚 n/8 đơn đang về" và nút nhận thùng; đếm thùng chỉ ra dòng lệch; thiếu xu thì nút mờ "thiếu N xu"; trà sữa đổi món đúng ly, giá thử có khoảng cho phép; Trạm Lắng Nghe ghi tên từng bước và căn cứ; sự cố nhân viên đang mở thì dẫn tới đó.
- Sửa lỗi báo giá sỉ ở tạp hóa (góp ý #49): mức giảm cao nhất bị từ chối thì khách rời đi thay vì kẹt đơn mãi. Không có "Có gì mới".

# v1.0.3 — Góc hẹn hò

- Hẹn hò trong game (live/ DatingFeature, v4 dating): ghế đá ở mọi nơi đi dạo và mục "Góc hẹn hò" đầu nhóm Quan hệ; chọn gặp bạn nam/nữ/ai cũng được, ghép người online chưa chặn nhau và chưa hẹn trong 24 giờ; buổi hẹn 5 phút: 3 thẻ làm quen (94 câu), "chọn món cho nhau", 1 phút chat, thả ❤️ hoặc 👋 riêng tư; cùng ❤️ thành "Đang tìm hiểu 💕" và kết bạn, +5 tinh thần (tối đa 15/ngày); không ai biết ai từ chối. Chỉ tài khoản mới hẹn hò được. Bảng mới (schema 7): live_dates, date_bonds. Bật bằng LIVE_DATING=1.
- "Có gì mới": góc hẹn hò.

# v1.0.2 — Gộp đơn nhập hàng

- Kho: giỏ theo từng nhà cung cấp ("🛒 Thêm vào đơn", một lần "Đặt đơn" = một phí ship, một lần giao, một thùng), phí ship 2–5 xu và miễn ship theo ngưỡng (chủ game duyệt), giá sỉ theo số lượng, xin bớt 5/10/15% (nhà cung cấp tự quyết, mỗi ngày một lần), hết hàng một món, xe giao muộn, đơn tối thiểu; giao thiếu/khiếu nại theo cả đơn hoặc từng dòng. Tạp hóa có "🛒 +N vào đơn" ở Kho & giá. Đơn cũ đang giao giữ nguyên. Không có "Có gì mới".

# v1.0.1 — Chat ra ngoài menu

- Chat đứng đầu menu, bấm một lần là vào (không còn nằm trong nhóm Quan hệ). Không có "Có gì mới".
- Chỉ tài khoản mới được nhắn (Cả phố, bạn bè, nhóm, bong bóng khi đi dạo); khách vẫn đọc, đi dạo, vẫy tay, và có nút "Tạo tài khoản" ngay chỗ ô nhắn. Tạo xong là nhắn được ngay, không cần tải lại.
- Cả phố giữ 2.000 tin mới nhất (dịch vụ live xóa tin cũ hơn theo lô nhỏ mỗi 5 phút; tin bị báo cáo chưa xử lý được giữ tới khi duyệt). Tin bạn bè và nhóm giữ mãi.
- Mỗi lần tải 30 tin (lần đầu và mỗi "Xem cũ hơn"), mọi kênh.

# v1.0.0 — Chat

- Dịch vụ live riêng (live/, asyncio + websockets, mnl-live.service, nginx /live): chat bạn bè, nhóm (≤20), kênh Cả phố (online, 10 giây/tin, người mới 10 phút chỉ đọc), chấm online (tắt được), lọc số điện thoại/link/tục nặng (tiếng lóng GenZ được), báo cáo (3 báo cáo tự ẩn), chặn, tab Chat trong admin (ẩn tin, cấm chat 1 giờ/24 giờ/7 ngày). Bảng mới (schema 6): chat_channels, chat_members, chat_messages, chat_mutes, chat_prefs, live_effects. Bật bằng LIVE_URL=/live ở game và LIVE_CHAT=1 ở live.env. Không có hướng dẫn cho chat.
- Đi dạo khu phố (live/street.py, v4/walk.js): 4 nơi, ≤20 người mỗi khu, bong bóng, biểu cảm, bàn tám chuyện (72 chủ đề), múa lân, hàng rong, lì xì (≤30 xu/ngày, game/live_effects.py, POST /api/live/effects). Bật bằng LIVE_STREET=1.
- "Có gì mới": chat, Cả phố, chấm online, đi dạo.

# v0.9.19 — Menu gọn, pha màu dễ

- Menu "Thêm" từ 25 xuống 11–12 mục: Công việc (Hành trình, Chuẩn bị, Sổ tiệm, Đánh giá) và Đời sống (Khu phố, Quan hệ, Tiền & nhà, Chuyện của bạn, Của mình), chấm đỏ cộng dồn lên nhóm. Bỏ "Hướng dẫn" khỏi menu: lần đầu vào một nghề hiện một lần "Bỏ qua / Xem hướng dẫn", màn làm việc nghề nào cũng có nút "?", Cài đặt giữ một đường dẫn hướng dẫn.
- Tiệm tóc: bảng pha màu dự tính (xem trước màu bát, so với màu khách cần, oxy có nâng nổi không) và bảng 6×6 các kiểu phối; cùng công thức với máy chủ (test so 527.000 trường hợp).
- Không có "Có gì mới".

# v0.9.18 — Admin: giữ chân người chơi

- Ghi mốc hành trình (stat_milestones), thao tác theo ngày (stat_actions, 60 ngày rồi gộp), tín hiệu rời game và tốc độ tải thật (POST /api/beacon: stat_leaves, stat_loads), lỗi phía người chơi (stat_client_errors), nguồn người chơi (stat_acquisition). Admin có mục "Giữ chân": quay lại D1–D30 theo ngày bắt đầu, phễu người mới, rớt ở đâu, theo nghề, theo nguồn, tốc độ tải, lỗi, dung lượng log. ~3 µs mỗi lệnh; RETENTION_LOG=0 để tắt. Người chơi không thấy thay đổi; không có "Có gì mới".

# v0.9.17 — Đời không như mơ: 5 nghề mới thêm oái oăm

- Thông ống cống, bán trái cây, thu gom rác (game/careers/street_folk.py): người chơi tự báo giá và tự ra giá, NPC có tính cách ẩn tự quyết và tự đánh giá; chặt chém khách và hậu quả, chủ nhà lèm bèm (nhịn/cãi/mời ra/bỏ việc), quỵt, ghi nợ và sổ nợ, chôm chỉa, chê bán đắt, rác nguy hiểm, phá hoại ca đêm, sổ thu phí vệ sinh; 31 tình huống bất ngờ mới. Sửa 5 lỗi của nghề thông cống (lộ giá trước khi nghe khách, kẹt hướng dẫn…).
- Phi công và tiếp viên (game/careers/air_odd.py): 57 tình huống người xung quanh ép, dụ, quấy rối, ép KPI, ép tập gym…; người chơi chọn giọng, câu đáp và người hỗ trợ; kỷ luật tới cách chức nếu chiều theo; báo cáo quấy rối luôn được bảo vệ; phi công hạ cánh trong mưa bão.
- Không có "Có gì mới".

# v0.9.16 — Bắt đầu nhanh và vui hơn

- Người mới: một màn chào + tên + chọn chỗ làm (gợi ý Trà sữa); ngày 1 mở cửa là có khách; hướng dẫn thành gợi ý ngay trên nút. Giao ly đầu tiên sau 10 lần bấm (trước 23).
- Không popup nào trước khách thứ 3; người mới không nhận "Có gì mới"; danh hiệu ngày đầu là thông báo nhỏ; truyện nghề chờ hết ngày 1.
- Khách đầu tiên cho tip, "còn N khách nữa là lên cấp", lên cấp 2 ở khách thứ 3 (trà sữa: 3 ly thay vì 4), quà chào mừng +20 xu cuối ngày 1.
- Gợi ý đúng lúc: đổi nghề, tiền ở đâu, đồng hồ, nút khép ca; tiệm bánh ghi rõ nguyên liệu còn thiếu. Không có "Có gì mới".

# v0.9.15 — Năm nghề mới: trái cây, thu gom rác, thông cống, phi công, tiếp viên

- Ba nghề đường phố, mở ở chương 3 (nhánh careers-street): 🍉 Bán trái cây (Sạp trái cây Dì Tư: dọn sạp, thử cân với quả cân 1 ký, lựa trái dập, chọn đúng độ chín, trừ bì, trả giá, xả hàng chiều tối), 🗑️ Thu gom rác (Tổ thu gom phường Mây, ca tối: đồ bảo hộ, kiểm xe, mở túi lạ, tách đồ nguy hại, ba ngăn, điểm tập kết và tiền ve chai của cô Tám, phản ánh của cư dân), 🪠 Thông ống cống (Thông cống chú Hai: xếp đồ nghề theo sổ hẹn, tìm nguyên nhân, báo giá trước khi làm, xuống hố ga đủ quy trình an toàn, bảo hành). Mỗi nghề có màn hình làm việc riêng (street_kit), cảnh `lane`, cốt truyện, chuyện bất ngờ, ngày khó và hướng dẫn.
- Hai nghề của Hãng bay Cánh Cò, mở ở chương 4, phải ứng tuyển (CV, thư, phỏng vấn) (nhánh careers-air): ✈️ Phi công (cơ phó: bản tin và nhiên liệu, kiểm tra quanh tàu, checklist trước khởi động, quyết định giữa chặng, bay chờ, sân bay dự bị, bay lại không bao giờ là lỗi) và 💺 Tiếp viên hàng không (đón khách ở cửa, hướng dẫn an toàn, xe phục vụ với suất ăn đặc biệt, đèn thắt dây, khách khó, sơ cứu). Giao diện riêng: thẻ lên tàu, bảng giờ bay, phòng tổ bay, Sổ bay (air_kit), cảnh `airfield`, nhóm chứng chỉ An toàn bay.
- Bản lưu cũ chỉ được thêm năm nơi làm mới (chưa nhận việc); các nghề khác không đổi gì: scripts/check_task_compat.py khớp toàn bộ nhiệm vụ mà bản đang chạy (0.9.14) sinh ra cho 23 nghề hiện có.
- 🎁 Quà từ Phố Có Chuyện (nhánh system-gift): quà riêng từ hệ thống (xu vào ví + một thẻ lời nhắn), trả một lần khi mở game, không bao giờ trả hai lần; bảng system_gifts (PostgreSQL SCHEMA_VERSION 4, tạo lúc khởi động), POST /api/gift/seen, scripts/grant_gift.py để tặng. Dùng cho quà xin lỗi sự cố 01/10 00:33–00:36. Không có trong "Có gì mới".
- "Có gì mới" 0.9.15: một dòng cho mỗi nghề mới (chủ game yêu cầu; chỉ tính năng mới), kèm bản tiếng Anh trong i18n/overrides.json. Nguồn dịch i18n/source.json được trích lại.


# v0.9.14 — Admin: thời gian chơi

- Trang admin có mục "Thời gian chơi": phút mỗi người mỗi ngày, độ dài một lượt, người mới ngày đầu, phân bố thời gian và người chơi theo giờ. Đo chính xác bằng trigger trên receipts (bảng stat_play, ~12 µs mỗi lệnh); 2 ngày trước đó ước tính từ biên nhận (scripts/playtime_backfill.py). Người chơi không thấy thay đổi; không có "Có gì mới".

# v0.9.13 — Biệt thự, căn hộ, giá nhà mới; tiền của bạn; sửa lỗi 0.9.5

- Nhà của bạn: thêm 4 loại căn hộ (Studio Nắng Mai 2.400 xu, Căn hộ Mây Xanh 1 phòng ngủ 5.400, Căn hộ Cánh Diều 2 phòng ngủ 10.200, Penthouse Mây Xanh 21.600) và 2 biệt thự (Biệt thự Vườn Cau 36.000, Biệt thự Sông Hồng 60.000), mỗi căn có tinh thần, điện nước và một dòng giới thiệu riêng; biệt thự có vườn, hồ bơi.
- Giá nhà rao bán tăng 20%: căn tập thể 1.800, căn hộ mini 3.600, nhà phố nhỏ 7.800, nhà có sân 14.400 xu. Tiền thuê phòng trọ giữ nguyên (14 xu/ngày, cọc 60) vì là chi phí sinh hoạt hằng ngày, không phải giá nhà.
- Nhà đã mua trước 0.9.13 giữ nguyên giá đã trả, khoản vay và lịch trả góp; giá thị trường khi bán vẫn tính từ giá đã trả (+3%/năm, tối đa +30%), không tự nhảy theo giá rao mới.
- Vay mua penthouse cần điểm tín dụng từ 670, Biệt thự Vườn Cau từ 700, Biệt thự Sông Hồng từ 740; mỗi kỳ trả góp vẫn không quá 40% thu nhập một tháng. Vợ chồng góp quỹ chung mua được mọi loại nhà.
- Nhà đang rao chia theo Phòng thuê / Căn hộ / Nhà phố / Biệt thự, mỗi loại một biểu tượng và màu; mỗi căn ghi giá, số tiền trả trước, góp mỗi tháng (3 năm) và "thiếu N xu". "Bước tiếp theo" gợi ý căn đắt nhất vừa sức (tính cả điểm tín dụng căn đó cần).
- 💰 Thanh trên cùng có hai ô có chữ: "🏪 Quỹ" (quỹ nơi đang làm) và "👛 Ví" (ví riêng, đỏ khi nợ). Bấm vào mở "Tiền của bạn": ví, ngân hàng (tài khoản, tiết kiệm, sổ kỳ hạn và ngày đáo hạn, khoản vay, thẻ), quỹ từng nơi làm kèm nút "Rút về ví · tối đa N", quỹ chung vợ chồng, nhà (giá hôm nay, còn nợ vay), Tổng tài sản và Tổng nợ. Ô 👛 trong bảng trạng thái và ô Ví ở Hành trình cũng mở bảng này.
- Sửa lỗi sau 0.9.5: vợ chồng tặng quà / chuyển quỹ không còn làm lượt bấm tiếp theo của người kia báo "tab khác" (tự thử lại một lần khi lệch phiên bản); quỹ chung hiện đúng dấu tiền rút; nhãn thang điểm tín dụng; dòng "Đến giờ đóng cửa" trên điện thoại; tab Hôn nhân; biểu tượng cho 3 nghề mới; dấu phân cách hàng nghìn; "Free size" thay cho "size F" trên màn hình.
- Tiếng Anh: thêm ~450 câu và ~350 mẫu cho các màn 0.9.5, cùng nhà mới, danh sách nhà theo nhóm, bảng Tiền của bạn và "Có gì mới" 0.9.6–0.9.10; tra cứu lồng nhau không còn làm hỏng bộ nhớ đệm dịch.
- Trước mỗi bản phát hành: scripts/check_task_compat.py so từng nhiệm vụ mà bản đang chạy sinh ra (mọi nghề, ngày 1–40, lượt 0–11) với bản mới; khác một trường là dừng (lỗi "Dữ kiện gốc của nhiệm vụ không hợp lệ" của 0.9.6). Bản này khớp 23.520/23.520 với bản đang chạy.
- Phát hành lặng lẽ: không có mục "Có gì mới" cho 0.9.13 (chủ game quyết định có thông báo hay không).

# v0.9.12 — Làm thử chứng chỉ không nhảy lên đầu

- Thi chứng chỉ: bấm đáp án làm thử hoặc 💡 gợi ý giữ nguyên vị trí cuộn và mục đang mở (public/js/v4/certificates.js: renderSheet() thay vì renderSheet(false)).

# v0.9.11 — Thất tình không bịa người yêu

- Chuyện đời "thất tình": bỏ các thẻ ngầm cho rằng bạn đang có người yêu (bị chia tay, yêu xa, bị cắm sừng, quên sinh nhật; vẫn định nghĩa để bản lưu cũ đang giữ thẻ đó chơi tiếp). Người đã đính hôn/kết hôn với người chơi khác không gặp thẻ thất tình; lời đồn "bị bỏ" chỉ sau khi bị ghost (game/life.py PARTNER_STORIES, DUMPED, _taken; tests/test_life_heartbreak.py).

# v0.9.10 — Đã chuyển sang máy chủ mới

- "Có gì mới" báo nâng cấp hạ tầng đã xong (30/09 21:00: máy chủ mới 9 vCPU, 15 GB RAM; gián đoạn 11 giây, dữ liệu giữ nguyên). Không đổi logic game.

# v0.9.9 — Thông báo bảo trì ngắn

- "Có gì mới" báo bảo trì 21:00–21:10 ngày 30/09 để chuyển sang máy chủ mới; dữ liệu giữ nguyên. Không đổi logic game.

# v0.9.8 — Thông báo nâng cấp máy chủ

- "Có gì mới" báo trước: từ 20:00 đến 0:00 ngày 30/09 hệ thống nâng cấp hạ tầng; vẫn chơi bình thường, trải nghiệm có thể bị ảnh hưởng một chút. Không đổi logic game.

# v0.9.5 — Mua nhà, tủ đồ, tiền luôn trong tầm mắt

- Cập nhật máy chủ không làm mất thao tác: trình duyệt tự gửi lại khi gặp 502/503/504 và hiện "Đang cập nhật máy chủ…"; máy chủ trả 503 `db_unavailable` thay vì lỗi, khóa bảo trì cho lúc chuyển bản; triển khai cuốn chiếu không gián đoạn (deploy/rolling_release.sh, docs/DEPLOY_ROLLING.md); sửa thêm vài điểm SQLite.
- Nhà của bạn: thuê phòng tốt hơn, mua nhà trả trước 30% và vay Ngân hàng Phố trả góp mỗi tháng (tới 3 năm), bán nhà; ở nhà mình thì hết tiền phòng. Vợ chồng góp quỹ chung mua nhà rồi về ở chung.
- Ngân hàng: tiết kiệm có kỳ hạn tới 3 năm, lãi tính theo năm (1 năm = 60 ngày sống, 1 tháng = 5 ngày), tới hạn tự tái tục nếu chọn; sổ cũ giữ nguyên lãi đã hứa.
- Tủ đồ: kiểu tóc, áo quần, giày, phụ kiện cho nhân vật; làm ở Tiệm Áo Chỉ Mây được giảm 20%. Bản lưu cũ giữ đúng dáng nhân vật đang có.
- Khách kiên nhẫn hơn một chút (PATIENCE_FACTOR 1,2 ở game/patience.py: chờ lâu hơn khoảng 20% mới bực hay bỏ về; hai việc đầu ở mỗi nơi vẫn không mất kiên nhẫn).
- Tiền đền nhẹ hơn (COMPENSATION_FACTOR 0,8 ở game/compensation.py): đền hư hỏng, bỏ dở việc, đền cho khách trong chuyện đời và từng nghề giảm khoảng 20%; tiền người chơi nhận về giữ nguyên.
- Người trong phố có chính kiến hơn (khen có gai, chê có lý); cha mẹ nói đúng giới của mình.
- Chip 💰 Ví · Quỹ tiệm trên đầu mọi màn tiêu tiền (ở ngân hàng và Nhà của bạn: Ví · Tài khoản · Quỹ chung); hộp xác nhận ghi "còn thiếu N xu".
- Hàng giao thiếu: nút "Khiếu nại phần thiếu" ngay trong Kho. Tiệm sửa đồ ghi sẵn phụ kiện khách đưa kèm; pet care và shop quần áo hiện lời dặn cạnh chỗ chọn.
- Giao diện yên hơn: thông báo nhiều dòng có biểu tượng, trang Đánh giá theo từng ô, Tổng kết ngày, Chuyện phố, Sổ tiệm và quầy trà sữa bớt ô màu, mỗi màn một nút chính.
- Trang admin: việc thống kê bản lưu không tranh tài nguyên với người chơi.
- Popup "Có gì mới" chỉ còn các điểm của 0.9.5.

# v0.9.4 — Kết hôn, ngân hàng, 3 nghề mới

- Hết giật lag: chạy trên PostgreSQL (từ 0.9.3); 0.9.4 thêm các bảng mới lúc khởi động, không khóa bảng lớn.
- Chương 3 thêm Shop quần áo, Shop thú cưng và quán trà đá vỉa hè.
- Kết hôn (cần tài khoản): nhẫn, cầu hôn bằng mã người chơi, tiệc cưới, tiền mừng, tin trên phố; quỹ chung và thẻ chung vợ chồng; ly hôn.
- Ngân hàng Phố: tiết kiệm, thẻ, khoản vay, điểm tín dụng.
- Bạn bè (tìm theo tên tài khoản) và điểm thân quen với người quen trong phố.
- Chứng chỉ nghề (thi 6 câu, đúng 4 là đạt, có gợi ý 💡) và "Đi cửa sau" khi trượt phỏng vấn.
- Bảng xếp hạng: Top trải nghiệm (cả phố, từng nghề) và Top chứng chỉ; ẩn/hiện tên trong Cài đặt.
- Đồng hồ trong ngày, sáng/tối, giờ mở cửa và đóng cửa; bỏ dở việc giữa chừng có phạt.
- Khách bo tip, khách đưa thiếu tiền (đếm lại, nhắc, cho nợ, báo công an), đánh giá nhiều góc hơn.
- Sách hướng dẫn đầy đủ (87 mục), màn hình gọn hơn trên điện thoại, thông báo hiện lâu hơn, tải nhanh hơn (lazy-load, file nén sẵn).
- Popup "Có gì mới" liệt kê các điểm trên.

# v0.9.3 — Thông báo "Có gì mới" cho toàn máy chủ

- Máy chủ chạy PostgreSQL: mỗi thao tác dưới 0,1 giây, người chơi không phải chờ nhau.
- Bảng "Có gì mới" hiện giữa màn hình cho mọi người chơi (cả người mới), không chờ lúc rảnh.

# v0.9.2 — Máy chủ PostgreSQL, khắc phục giật lag

- Lưu trữ chuyển sang PostgreSQL (bật bằng DATABASE_URL; không có thì chạy SQLite như cũ). Mỗi người chơi chỉ khóa save của mình, không còn hàng đợi ghi chung.
- Công cụ chuyển dữ liệu (scripts/pg_migrate.py, deploy/pg/*): chép trước khi game chạy, đồng bộ, đối chiếu sha256 từng save, chuyển trong vài giây, quay về được.
- Trang admin: tóm tắt nhanh, các mục tải riêng, có cache; không làm chậm người chơi.
- Chịu tải: giới hạn theo IP chỉnh được (NEW_SESSIONS_PER_MINUTE, REGISTER_*, LOGIN_*, BOOTSTRAP_PER_MINUTE), MAX_THREADS mỗi worker; AI rớt kết nối thì dùng câu soạn sẵn.
- Popup "Có gì mới" giữa màn hình: thông báo đã khắc phục sự cố sáng 30/9.

# v0.9.1 — Sửa đặt phòng homestay trên điện thoại

- Chọn phòng đã có khách hoặc không đủ chỗ không còn làm khung "Bước tiếp theo" phình to che hết lịch; ghi chú xuống dòng gọn.
- Bấm cả hàng phòng để chọn (không chỉ ô tên), có dấu ✓ và thông báo "Đã chọn … · 1/2 chỗ"; màn 360px thấy đủ 7 đêm, cột tên phòng đứng yên.
- Thông báo nhỏ không còn đè lên lịch; màn ngang có chỗ để thao tác.

## Dễ nhìn hơn

## Giao diện
- Quán mì cay: phiếu order giờ là danh sách từng dòng (nước dùng, topping, cấp cay, mang về, dị ứng) có dấu ✓/✗/○ theo tô đang làm, thay cho câu dài và mục "Kiểm tô" bị ẩn.
- Lời khách và câu chuyện được gập gọn thành một dòng, bấm để mở.
- Nút mới "📖 Thực đơn": giá, còn bao nhiêu, mở ở cấp mấy, món có hải sản/thịt/chay được và vài luật bếp cần nhớ.
- Trên máy tính, phiếu order đứng cạnh bếp; dải "Hôm nay" gọn một dòng khi đang làm.

## Nhạc nền
- Thay nhạc tự sinh bằng 6 bản nhạc CC0 (miễn bản quyền) từ OpenGameArt, mỗi nhóm nghề một bài, chuyển bài mượt khi đổi nghề. Nguồn và tác giả ở `public/music/CREDITS.md`.

## Âm thanh
- Loa báo tiền: khách chuyển khoản vào tiệm là nghe “ting ting · Đã nhận … xu”, đọc bằng giọng tiếng Việt của máy (tiếng Anh: “Received … coins”). Nhiều khoản về liền nhau gộp thành một lần đọc. Máy không có giọng tiếng Việt thì chỉ ting ting kèm chip “🔔 +… xu”.
- Giọng nhân vật: nhân vật “líu lo” vài âm tiết khi nói, mỗi người một giọng (trẻ con cao, ông bà trầm), dấu thanh tiếng Việt uốn giọng; bạn cũng có giọng riêng khi nhắn tin.
- Âm thanh chi tiết: tiền về, két tính tiền, xong một bước, chuông cửa khi khách tới, chuông nhẹ khi khép ca và lên cấp, tiếng lật giấy khi mở bảng.
- Cài đặt → Âm thanh có ba công tắc mới; tắt “Âm thanh thao tác” là tắt hết.

# v0.5.0 — Một người, một khu phố

## Hành trình của một nhân vật
- Vào game là bắt đầu một câu chuyện: bạn mới chuyển về khu phố, tự đặt tên và chọn giới tính (nam hoặc nữ, không có mặc định). Lời thoại, lời phụ huynh và học sinh gọi bạn theo giới tính đã chọn.
- Nghề mở dần theo 6 chương. Chương đầu có quán trà sữa, tạp hóa và giao hàng; về sau mở tiệm bánh, tiệm hoa, tiệm mẹ & bé, quán ăn, thú cưng, tiệm tóc, sửa đồ, nông trại, homestay, CSKH, nhà thuốc, hướng dẫn viên, giáo viên, kế toán và các văn phòng lớn.
- Tiền có hai tầng: ví riêng của bạn (trả tiền nhà và ăn uống mỗi ngày sống) và quỹ riêng của từng nơi làm (điện nước, mặt bằng, lương, hàng hóa). Có thể rút lãi về ví, góp vốn, tạm nghỉ hay mở lại một nơi làm.
- Nhân vật trưởng thành theo cấp, có kỹ năng và bộ sưu tập danh hiệu; có thể đeo một danh hiệu.
- Bỏ phần chọn "nhịp ngày" và độ khó. Mỗi ngày trời tự định: ngày thường, ngày thong thả hay ngày hội.

## Xin việc
- Nghề cần tuyển dụng phải nộp hồ sơ, phỏng vấn xong và ký thư mời mới được đi làm.
- Thỉnh thoảng gặp may: giám đốc (hay hiệu trưởng) đọc hồ sơ và mời thẳng, hoặc tình cờ gặp sếp cuối ngày và được mời vào làm.

## Nghề đa dạng hơn
- Quầy trà sữa làm tay: chồng ly M/L, bình trà, 12 ô topping có số lượng và ổ khóa, đá, đường, máy dán nắp; khách có thanh kiên nhẫn, khách quen có sổ riêng; mỗi ngày một chuyện riêng (ví dụ học sinh tan học) và bất ngờ ở quầy phải tự quyết.
- Tiệm mẹ & bé: gói quà đúng dịp, đọc nhãn tuổi trên hộp đồ chơi, soạn bộ đồ cho cha mẹ mới, đổi trả không hóa đơn, đơn tiệc nhiều món.
- Quán ăn, tiệm bánh và tiệm hoa: "hên xui của ngày" (mưa, giờ cao điểm, lễ hội…), bất ngờ có hậu quả thật (đoàn kiểm tra, mất hàng, đơn tiệc lớn, người viết review ngồi góc quán), khách có tính cách, chuỗi phục vụ liên tiếp và điểm cuối ngày.
- Nhà thuốc, kế toán và CSKH: bàn giấy tờ kiểu soi hồ sơ, đánh dấu dòng sai, đóng dấu và chịu kết quả.
- Văn phòng (kế toán doanh nghiệp, thuế – lương, tập đoàn): đồng hồ giờ làm, hạn nộp từng hồ sơ, độ tin của sếp, tăng ca và phạt nhỏ.
- Giáo viên có tiết học thật với từng học sinh, kế hoạch vừa khung giờ, phiếu cuối giờ; hướng dẫn viên có đoàn khách với mong muốn riêng, thời tiết, lộ trình và quỹ đoàn.
- Tạp hóa, giao hàng, nông trại và tiệm hoa có thêm tình huống và sửa lỗi nhập hàng, hạn dùng.
- Sửa đồ, tiệm tóc, thú cưng và homestay có thêm tình huống và cách làm mới.

## Giao diện và cảnh
- Nhân vật không còn đi xuyên quầy, kệ hay tường; mọi điểm tương tác đều đi tới được.
- Sắp lại menu: thao tác trong tiệm ở thanh dưới, sổ sách và khu phố ở menu bên (trên điện thoại là "Thêm").
- Bỏ các dòng giải thích hậu trường. Thông báo chồng nhau không còn che đầu thẻ trên điện thoại.
- Sổ thu chi hiện tên đúng cho các khoản mới (lương, hoàn tiền, tiền tip, tiền phạt, sinh hoạt, chuyển quỹ…).

## Ngôn ngữ
- Bản tiếng Anh phủ toàn bộ nội dung mới.

# v0.4.0 — Phố nghề mở cửa

Bản này chuẩn bị để mở game công khai cho mọi người chơi.

## Nghề và công việc thật
- Thêm các nghề mới dạng plugin (`game/careers/`). Mỗi nghề có quầy làm việc riêng, kho nguyên liệu với lô và hạn dùng, nhập hàng, giá bán, nhân viên, và nhiều tình huống ngoài đời kèm nhiều góc nhìn.
- Có bàn chế biến/lắp ráp (như quầy mì); các nghề kế toán, thuế và tập đoàn làm thủ tục nhiều bước (bút toán, đối chiếu, tờ khai); một số nghề như giáo viên và kế toán phải nộp hồ sơ và phỏng vấn mới được nhận vào làm.
- Giáo viên có thêm **Kế hoạch lớp**: bài học nhiều môn, chấm bài, gặp phụ huynh, và lịch năm học 9 tháng với Trung thu, sinh nhật chung trong tháng, 20/11, Hội khỏe Phù Đổng, góc Tết gói bánh chưng mini, dã ngoại nông trại và lễ tổng kết. Mỗi hoạt động kết thúc bằng tóm tắt từ góc nhìn học sinh, phụ huynh và đồng nghiệp.

## Phản hồi và AI nhân vật
- Khách để lại phản hồi sau khi mua hàng hay dùng món, chấm theo từng tiêu chí đúng với những gì đã xảy ra.
- Mỗi người phản hồi có tính cách riêng: chanh chua, bố đời, ấm áp vui tính, kỹ tính, Gen Z, kiệm lời. Với giáo viên, người phản hồi là phụ huynh (hay lo, khó tính, đồng hành).
- Chủ quán trả lời, có thể kèm bù đắp; khách tự quyết định sửa sao, giữ nguyên hay cãi lại (tối đa 3 lượt).
- AI tùy chọn (máy chủ cấu hình LLM, người chơi phải đồng ý), có kịch bản dự phòng. Số sao luôn được kẹp trong khoảng dữ kiện cho phép, và câu trả lời có chèn link hay chèn lệnh sẽ bị loại.

## Phố nghề — chơi cùng nhau
- Hồ sơ công khai, danh bạ quán, ghé thăm quán người khác, đánh giá (chỉ sau khi đã ghé) và trả lời đánh giá.
- Tặng quà (sticker + xu, có giới hạn), chợ nguyên liệu giữa người chơi (giữ hàng hộ, hàng giữ nguyên hạn dùng, giới hạn giá), bảng tin nghề có bình luận và biểu cảm, theo dõi, hộp thư, mục tiêu tuần cả phố.
- Có chặn, báo cáo (nội dung bị 3 người báo cáo sẽ tự ẩn), lọc link/số điện thoại/từ thô tục, giới hạn tần suất.

## Giao diện, âm thanh, ngôn ngữ
- Thiết kế lại giao diện: 5 phong cách (Kem, Trà xanh, Biển, Kẹo, Đêm), bố cục riêng cho điện thoại, máy tính bảng và máy tính (tự nhận hoặc tự chọn), font Be Vietnam Pro tự host.
- Nhạc nền tự sinh theo từng nghề (không dùng tệp nhạc ngoài), chỉnh âm lượng nhạc và hiệu ứng riêng.
- Chọn ngôn ngữ Tiếng Việt / English. Bản tiếng Anh phủ toàn bộ giao diện, nội dung 20 nghề, NPC, sự kiện và câu chuyện; câu ghép từ số, tên hay nhiều đoạn "·" vẫn được dịch từng phần. Thông báo đẩy cũng theo ngôn ngữ đã chọn.
- Cài đặt gom theo thẻ: Chơi, Giao diện, Âm thanh, Ngôn ngữ, Thông báo, Dữ liệu.

## Thông báo và PWA
- Web push (VAPID ES256 viết bằng Python thuần, push không mang nội dung). Thông báo khi có khách ghé, đánh giá, quà, hàng bán được, bình luận; tùy chọn nhắc mở quán mỗi ngày.
- Có manifest, icon, service worker, trang offline; cài được lên màn hình chính (iPhone cần "Thêm vào MH chính" để nhận thông báo).

## Mở công khai an toàn
- Có trang Chính sách quyền riêng tư (`/privacy`) và Điều khoản (`/terms`), liên hệ trachanhtv.works@gmail.com. Người chơi tự xóa được toàn bộ dữ liệu của mình.
- Chạy được sau reverse proxy HTTPS (`TRUST_PROXY`), cookie Secure, HSTS, CSP chặt hơn, gzip + ETag, giới hạn phiên mới, tự dọn phiên cũ. Có Docker healthcheck, compose kèm Caddy (HTTPS tự động) và hướng dẫn `docs/DEPLOY.md`.
- Bản lưu schema 4 (`save-v4`), tự chuyển từ v1–v3. Nghề mới được thêm vào bản lưu cũ ở trạng thái ban đầu.

---

# v0.3.0 — Những ngày nhiều chuyện

- Giữ bốn vòng chơi gốc; thêm giáo viên, hướng dẫn viên và trà sữa. Danh mục có 19 nghề, trong đó 7 nghề chơi được.
- Giao diện kem–hồng, menu bảng phấn, giấy dán, hội thoại khách và ly vector nguyên bản; sửa bố cục màn hình dọc để thanh chức năng không che mục tiêu.
- Ba vòng nghề mới có luật kiểm chứng: bài học/điểm danh/phản hồi; tuyến/thời tiết/kiểm đoàn; nguyên liệu/lô/giá chốt/hạn dùng.
- Thêm 28 bộ trò nhỏ thuộc bốn họ luật, 21 mẩu chuyện ba chặng, 12 loại huy hiệu, ba mục tiêu mỗi ngày, khu phố năm điểm và ngày hội tự chọn.
- Mở rộng thành 42 NPC, 28 ứng viên; vai trò và đạo cụ riêng cho nghề mới. Giữ nhân viên, thu chi, mặt bằng và an ninh v0.2.
- Sửa được lời phản hồi review mà không đổi sao của NPC; bổ sung câu nhận xét vui theo nghề, thưởng ngày chống trùng, combo, tip đội tách két và hao hụt không trừ tiền hai lần.
- Bản lưu v3, chuyển schema 1/2 lên 3. Thêm kiểm thử nghiệp vụ, kiểm thử lại các chức năng cũ và luồng UI bảy nghề; tài liệu đối chiếu phần đã có với phạm vi thiết kế.

## Lịch sử

# Changelog

## 0.2.0 — Boba & đời sống tiệm

### Added
- Operations notebook shared by four playable careers, with separate economy/staff/state.
- 16 hireable employees, career-specific roles and bounded automatic assistance, shift schedules, attendance, rest, training, bonuses, dismissal and scripted factual chat.
- Employee mistakes/misconduct scenarios, evidence, deferred repair invoices, recovery and training outcomes. No automatic wage deductions.
- Cash ledger, daily wages/utilities/coverage, per-shift rent, 7-close fictional tax periods, one extension/bill, receipts and a one-time emergency grant.
- Three premises, capacity guards, visible scene changes and migration-safe existing shelf upgrades.
- Fixed-truth security cases, proof-gated reports, NPC police, separate asset restitution and bounded rewards; pre-event insurance and no duplicate compensation.
- Camera/bell/lock/light props, mode-aware event director and isolated rehearsals.
- Original front-facing boba/pastel artwork for all four careers, dedicated portrait composition, larger touch hit areas, employee/officer sprites and financial hotspots.
- 53 new Python test cases and a dedicated browser operations workflow suite.

### Changed / fixed
- Save schema 2, import both old/new backup envelopes; lazy transactional migration preserves prior gameplay without retroactive bills.
- Every economic mutation goes through the same ledger and SQLite idempotency guard.
- Preserve expanded detail panels on state refresh; reset sheet scroll when switching views.
- Explicitly close SQLite connections after context-managed operations.
- Rehiring does not reset same-day training/bonus limits.

### Scope
Local/LAN playable prototype. No real-user community, public production release, full-autonomous LLM workforce or gameplay for 12 locked careers. Tax, police rewards and insurance are authored fictional game rules. See implementation matrix and test reports.

---

# v0.1.0 — playable prototype

- Bốn vòng nghề độc lập có state và lưu SQLite; 12 nghề tương lai có preview.
- Cảnh vector isometric có di chuyển, hitbox, NPC, trang trí, chụp ảnh.
- Bàn chọn hàng/gói quà; bàn kiểm lô hư cấu; bảng đối chiếu nguồn; màn xử lý CSKH.
- 24 NPC, chat kịch bản theo ngữ cảnh, memory liên kết sự kiện, feed/review/bình luận local.
- 96 vignette dựa trên baseline với evidence/choice/execute; practice không tạo thưởng.
- 12 tuyến mục tiêu/milestone, nâng cấp, nhịp ngày tự chọn, giữ việc qua ca.
- Export/import JSON, xác nhận hành động kinh tế, revision và command idempotency.
- Adapter AI rephrase tùy chọn có consent/fallback; chưa kết nối model thật.
- Script chạy Windows/macOS/Linux, test stdlib, browser test adapter, manifest và kiểm gói giải nén.
