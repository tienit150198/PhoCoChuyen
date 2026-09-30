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

# Chưa phát hành — Dễ nhìn hơn

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
