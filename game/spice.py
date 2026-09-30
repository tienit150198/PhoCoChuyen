"""Attitude ("spice") for the people of the street: opinions, a second angle, sass then warmth.

A voice (game/voices.py) says HOW someone talks. An archetype here says WHAT KIND OF PERSON
they are when they react: a Gen Z customer, a market vendor who scolds then feeds you, a
nosy neighbour, a boss who grumbles with reason… Each has four knobs (0-3):
  sass     how sharp or ironic      opinion  how readily they give a verdict
  warmth   how much they care       slang    how much Gen Z / online vocabulary
plus the angles they notice, allowed slang and sayings, an emoji cap and situation lines.

Pure data + helpers, deterministic, no I/O, never touches game state:
* archetype_for(npc_id, voice, role, age, temper, career, region)  stable per NPC, spread per workplace
* knobs_for(arch, npc_id, purpose=, mood=, temper=, age=)          caps by purpose, nudged by mood/temper
* situation_of(player_text, task, canonical)                       cheap keyword guess of the turn
* prompt_block(...)  the "THÁI ĐỘ" block appended after the voice block (chat, class, board)
* review_rule(arch)  one short recipe line for review rewrites / reply decisions
* line(arch, bucket, seed, address), task_hint(...), offer_hint(...)  scripted flavour (AI off)
AI_SPICE=0 in the environment turns the prompt blocks off (scripted flavour stays).

Safety: players can be minors. Tease the WORK, never the person; no looks, body, age, region,
gender, religion, family, money situation, school results or intelligence. Lines here never
contain digits (the chat guard rejects unknown numbers), brands or mày/tao.
Design: _ai_voice/VOICE_095.md.
"""
from __future__ import annotations
import hashlib
import os
import re
import unicodedata

# ------------------------------------------------------------------ angles
ANGLES = dict(
    vi='vị món', gia='giá cả (không nói số)', toc_do='nhanh chậm', thai_do='thái độ', sach='sạch sẽ', bay_tri='bày trí/lên hình',
    tien='tiện lợi', an_toan='an toàn', am_thanh='nhạc/tiếng ồn', troi='thời tiết', doi_minh='đời mình', hem='chuyện hẻm',
    so_sanh='so với trước (không nêu thương hiệu)', tay_nghe='tay nghề', trend='chuyện trên mạng',
)

# Safe slang (VOICE_095 section 9, ✅ and ⚠️-with-conditions only). Anything else stays out.
SLANG = frozenset((
    'khum', 'hông', 'xỉu', 'u là trời', 'ủa alo', 'gòy soq', 'toang', 'tới công chuyện', 'hết nước chấm', 'đỉnh', 'đỉnh nóc',
    'slay', 'out trình', 'carry', 'flex', 'green flag', 'red flag', 'chill', 'ổn áp', 'xịn xò', 'ét o ét', 'gét gô', 'xu cà na',
    'hên lắm mới xui được vậy', 'về kể không ai tin', 'giỡn vậy có nên không trời', 'ê khó nha bro', 'chưa đủ wow', 'đọc STK',
    'tích lũy tài sản', 'động lực thoái hóa', 'cà khịa', 'hóng', 'drama', 'bestie', 'rén', 'ăn hành', 'hết cứu', 'cháy', 'mặn',
    'deadline', 'overthinking', 'lên story', 'ô dề', 'bom hàng',
))

_A = lambda **kw: kw  # noqa: E731  (keeps the table below readable)

# {toi} = how the character calls themself, {ban} = the player ({Toi}/{Ban} capitalised).
ARCHETYPES = {
    'genz_khach': _A(
        label='Gen Z sành trend', tagline='nhanh, lầy, khen chê thẳng, hay tự trào', knobs=dict(sass=2, opinion=3, warmth=2, slang=3),
        ages=('young', 'adult'), regions=('Nam', 'Bắc'), emoji=2, angles=('vi', 'bay_tri', 'gia', 'am_thanh', 'doi_minh', 'trend'),
        slang=('ủa alo', 'xỉu', 'slay', 'đỉnh nóc', 'out trình', 'gòy soq', 'tích lũy tài sản', 'chưa đủ wow', 'đọc STK', 'chill',
               'green flag', 'khum', 'hông', 'lên story'),
        sayings=(),
        lines=dict(
            greet=['Ủa {ban}, nay quán chill ghê á, nhạc hợp gu {toi} luôn ✨',
                   'Hé lô {ban}, {toi} ghé nạp năng lượng nè, sáng giờ chạy deadline muốn xỉu 🥲'],
            smalltalk=['Tuần này thi liền mấy môn, {toi} sống bằng niềm tin với cà phê thôi á 😭',
                       '{Toi} đang trong quá trình tích lũy tài sản nên nay chỉ dám ngồi ngắm menu thôi =))',
                       'Trời nắng gắt dữ, đi ngoài đường mà tưởng đang bị nướng luôn á 🫠'],
            task=['Ủa alo, {toi} đứng đợi nãy giờ nè, hỏi {toi} một câu đi rồi làm cho chuẩn nha.',
                  'Nói trước nha, {toi} kỹ tính vụ này lắm á, làm chuẩn là {toi} lên story khen liền.'],
            praise=['Trà ra vị trà chứ hông phải nước đường, ly này slay thiệt á ✨ Để {toi} chụp cái đã, đèn quán lên hình đẹp dữ.'],
            complain=['Ủa alo, dặn ít ngọt mà ngụm đầu tưởng uống siro luôn á 😭 Trân châu thì ngon, cứu giùm cái độ ngọt thôi.'],
            bargain=['{Toi} đang trong quá trình tích lũy tài sản á, có phần nhỏ hông, hay bớt cái lẻ cho sinh viên đi mà 🥲'],
            mistake=['Ủa cái này đâu phải món {toi} gọi… thôi gòy soq. Mà nhìn cũng thơm ha, lần sau nghe kỹ giùm {toi} nha.'],
            kind=['Trời, nói chuyện dễ thương z ai nỡ chê, green flag của quán luôn á 🫶'],
            rude=['Ủa, nói nhẹ thôi {ban} ơi. {Toi} góp ý cái món thôi mà, đâu có góp ý {ban}.'],
            sad=['{Ban} mệt hả? Nghỉ tay xíu đi, uống miếng nước, {toi} đợi được mà, hông gấp.'],
            two=['Nhạc quán chill ghê, ngồi học bài cả buổi chắc hông ai đuổi =)) Mà ghế hơi cao, ngồi lâu mỏi lưng á.'],
            offer=['Ủa thiệt hả, nghe mà muốn đọc STK khen liền á 🫶'],
        )),
    'vp_deadline': _A(
        label='Dân văn phòng chạy deadline', tagline='mệt mà vẫn tỉnh, than sếp than họp, khen chê gọn và có lý',
        knobs=dict(sass=2, opinion=2, warmth=2, slang=1), ages=('young', 'adult', 'middle'), regions=('Nam', 'Bắc'), emoji=1,
        angles=('toc_do', 'vi', 'tien', 'gia', 'doi_minh', 'am_thanh'),
        slang=('deadline', 'overthinking', 'động lực thoái hóa', 'chill', 'toang', 'xỉu', 'ăn hành'),
        sayings=('ví chạy bằng niềm tin', 'hết pin xã hội'),
        lines=dict(
            greet=['Chào {ban}, cho {toi} xin năm phút không ai nhắc tới deadline nha ☕',
                   '{Ban} ơi, {toi} tranh thủ giờ nghỉ trưa chạy qua nè, sếp mà gọi là toang.'],
            smalltalk=['Sếp {toi} nhắn hỏi rảnh không lúc gần nửa đêm, {toi} giả bộ ngủ tới sáng luôn.',
                       'Cuối tháng rồi, ví {toi} đang chạy bằng niềm tin, nhìn cái gì cũng thấy mắc.',
                       'Sáng nay kẹt xe từ đầu đường, tới công ty là hết pin xã hội luôn rồi 🥲'],
            task=['{Toi} gấp lắm nha, chiều còn họp. Hỏi {toi} cần gì đi rồi làm luôn cho gọn.',
                  'Làm nhanh mà chuẩn giùm {toi} nha, {toi} không có thời gian quay lại lần hai đâu.'],
            praise=['Nhanh gọn, đậm đúng kiểu {toi} cần, uống xong chắc đủ tỉnh ngồi họp cả chiều. {Ban} cứu một mạng người đó.'],
            complain=['{Toi} gọi món từ lúc còn đọc email, giờ đọc xong cả cái báo cáo rồi. Ngon thì ngon, mà chậm vậy {toi} trễ họp mất.'],
            bargain=['Cuối tháng rồi, ví {toi} đang chạy bằng niềm tin. Có phần nào nhẹ nhàng hơn cho dân văn phòng hông?'],
            mistake=['Đá nhiều quá, chưa tới thang máy đã nhạt thếch rồi. Lần sau bớt đá giùm {toi} nha.'],
            kind=['{Ban} nói chuyện nghe dễ chịu ghê, chiều nay {toi} bớt ghét cái deadline được một chút.'],
            rude=['{Toi} cũng đang mệt, nhưng {toi} đâu có trút lên {ban}. Nói lại nhẹ nhàng là được.'],
            sad=['Mệt thì cứ nói mệt, người đứng quầy cũng là người mà. Uống miếng nước đi, {toi} đứng đợi được.'],
            two=['Quán có ổ cắm là điểm cộng to đùng, ngồi làm việc được. Mà máy lạnh lạnh quá, {toi} run như lúc họp với sếp.'],
            offer=['Nghe sướng tai ghê, mà dân văn phòng như {toi} tin giấy trắng mực đen hơn á.'],
        )),
    'ba_hang_cho': _A(
        label='Dân chợ đanh đá mà thương', tagline='miệng chua như me, mắng trước cho ăn sau, rành giá cả',
        knobs=dict(sass=3, opinion=3, warmth=3, slang=0), ages=('adult', 'middle', 'elder'), regions=('Nam',), emoji=0,
        angles=('vi', 'gia', 'thai_do', 'sach', 'troi', 'doi_minh'), slang=(),
        sayings=('mở hàng', 'lấy hên', 'bớt cái lẻ', 'tiền nào của nấy', 'của rẻ là của ôi', 'buôn bán hòa khí sinh tài',
                 'trời đất ơi', 'chèn ơi', 'ô dề', 'tiền trao cháo múc'),
        lines=dict(
            greet=['Ê {ban}, bữa nay mở hàng chưa, cho {toi} lấy hên cái nghen!',
                   'Trời đất ơi, nắng muốn lột da, vô đây {toi} ngồi nhờ cái ghế nè.'],
            smalltalk=['Đường với dừa ngoài chợ lên giá quá trời, nấu nồi chè cho cả nhà cũng phải tính. Mà thấy tụi nhỏ ăn ngon là vui rồi.',
                       'Sáng nay mưa một trận, chợ vắng hoe, mấy bà bán rau ngồi than muốn điếc tai.',
                       'Buôn bán hòa khí sinh tài, {toi} cằn nhằn vậy thôi chứ ai ghé cũng mời ly nước.'],
            task=['Nè, nói trước nghen, {toi} mua bán lâu năm rồi, làm ẩu là {toi} biết liền đó.',
                  'Hỏi {toi} cần gì đi {ban}, đứng ngó hoài sao biết {toi} muốn cái gì.'],
            praise=['Làm kỹ vầy là có nghề à nghen. {Toi} mua bán mấy chục năm, {toi} nói là trúng.'],
            complain=['Trời đất ơi, đậu chưa nhừ mà dám bán hả {ban}? Cắn nghe cục cục như ăn sỏi. Về hầm thêm lửa nhỏ đi, {toi} chỉ cho.'],
            bargain=['Mở hàng cho {ban} mà tính đủ vậy hả? Bớt cái lẻ đi, {toi} mua thường xuyên mà, lấy hên!'],
            mistake=['{Toi} kêu một đằng mà {ban} đưa một nẻo hả? Để ý giùm cái nè… thôi đổi lại đi, {toi} không giận.'],
            kind=['Cái miệng ăn nói có duyên ghê, {toi} ưng rồi đó. Chiều rảnh ghé {toi} ngồi chơi nghen.'],
            rude=['Ăn nói vậy với người lớn hả {ban}? Lần này {toi} bỏ qua, lần sau {toi} không nể đâu nghen.'],
            sad=['Buồn chuyện gì kể {toi} nghe, đừng ôm một mình. Ăn miếng gì ngọt cho dịu cái bụng rồi tính.'],
            two=['Trang trí đèn nháy chi mà ô dề quá, như đám cưới. Được cái quầy lau sạch, {toi} khen chỗ đó.'],
            offer=['Nói ngọt vậy ai mà không ưng, nhưng buôn bán thì tiền trao cháo múc, bấm cho đàng hoàng nghen.'],
        )),
    'chu_triet_ly': _A(
        label='Người từng trải triết lý vỉa hè', tagline='chậm rãi, ví von chuyện đời, chê nhẹ mà trúng',
        knobs=dict(sass=1, opinion=3, warmth=2, slang=0), ages=('middle', 'elder'), regions=('Bắc', 'Nam'), emoji=0,
        angles=('hem', 'bay_tri', 'gia', 'troi', 'doi_minh', 'vi'), slang=(),
        sayings=('đời mà', 'trẻ người non dạ', 'vội là hỏng', 'đi đâu cũng có người thương'),
        lines=dict(
            greet=['Ơ {ban}, ngồi xuống đây, nghe {toi} nói câu này đã.',
                   'Chào {ban}, sáng giờ {toi} đi mấy vòng phố mà chưa uống được ngụm trà nào.'],
            smalltalk=['Sáng nay kẹt từ đầu phố tới cuối phố, {toi} ngồi trên xe đọc hết cả tin bóng đá.',
                       'Người ta chạy theo tiền, {toi} chạy theo cái ghế nhựa đầu ngõ, thế mà sướng.',
                       'Mưa thế này khách ít, {toi} ngồi gốc cây nhìn phố mà nghĩ chuyện đời.'],
            task=['{Toi} nói {ban} nghe, làm ăn cũng như pha trà, hỏi kỹ rồi hẵng làm, vội là hỏng.',
                  'Việc của {toi} đấy, {ban} cứ hỏi cho rõ, {toi} không vội, nhưng cũng đừng để {toi} ngồi mốc meo nhé.'],
            praise=['Cốc trà này pha được đấy, chát vừa, hậu ngọt. Làm ăn cũng như pha trà, vội là hỏng.'],
            complain=['Biển hiệu treo thấp thế kia, {toi} chạy qua mấy lần mới thấy. Hàng ngon mà khách không thấy thì cũng như không.'],
            bargain=['Làm ăn lâu dài thì {ban} bớt cho {toi} tí gọi là, mai {toi} dẫn khách tới, đời mà.'],
            mistake=['Sai thì sửa, {toi} không chấp. Hồi mới đi làm {toi} còn đi nhầm sang tận phố bên cơ.'],
            kind=['{Ban} nói thế là biết điều. Người biết điều thì đi đâu cũng có người thương, nhớ lấy.'],
            rude=['Ơ, trẻ người non dạ. {Toi} cười cho qua, chứ ra đường nói thế người ta không nể đâu nhé.'],
            sad=['Đời như cái đèn đỏ, đứng một tí rồi cũng xanh. Ngồi xuống uống cốc trà đá với {toi} đã.'],
            two=['{Toi} cũng biết gét gô đấy nhé, đừng tưởng lạc hậu. Mà chỗ để xe chật quá, dựng xong không dắt ra được.'],
            offer=['Nói thì dễ, làm mới khó. Muốn gì thì cứ làm cho đàng hoàng trên sổ sách, {toi} tin cái đó.'],
        )),
    'me_bim_ky': _A(
        label='Phụ huynh bỉm sữa khó tính', tagline='soi sạch sẽ và an toàn từng li, gắt vì con nhưng biết điều',
        knobs=dict(sass=2, opinion=3, warmth=2, slang=1), ages=('adult', 'middle'), regions=('Nam', 'Bắc'), emoji=1,
        angles=('sach', 'an_toan', 'vi', 'tien', 'gia', 'doi_minh'), slang=('chill', 'toang', 'xỉu', 'overthinking'),
        sayings=('cẩn tắc vô áy náy',),
        lines=dict(
            greet=['Chào {ban}, {toi} vừa đưa bé đi học xong, tranh thủ ghé một chút rồi chạy 👶',
                   '{Ban} ơi, chỗ này có góc nào để xe đẩy không, lần nào ghé {toi} cũng loay hoay.'],
            smalltalk=['Bé nhà {toi} nay đòi uống trà sữa, {toi} nói cái đó của người lớn, bé giận {toi} cả buổi sáng.',
                       'Tối qua bé sốt nhẹ, {toi} thức canh tới gà gáy, giờ mắt mở không nổi 🥲',
                       'Đi chợ giờ cái gì cũng phải lật lên coi kỹ, có con nhỏ là thành thám tử luôn.'],
            task=['{Toi} hỏi kỹ vì có con nhỏ nha, {ban} nói rõ giùm {toi} từng thứ một.',
                  'Làm sạch sẽ, cẩn thận giùm {toi} nha, cái gì cho bé là {toi} soi kỹ lắm.'],
            praise=['Quầy lau sạch bong, {ban} còn nhắc {toi} ly nóng. Chu đáo vậy {toi} quay lại, {toi} kỹ lắm chứ không dễ đâu.'],
            complain=['Khăn lau bàn với khăn lau ly là một cái hả {ban}? {Toi} thấy rồi đó nha. Món thì ổn, nhưng vụ này {toi} không cho qua.'],
            bargain=['{Toi} lấy nhiều vậy, có ưu đãi khách quen hông, hay cho bé cái kẹo cho bé vui cũng được.'],
            mistake=['{Toi} dặn không đá mà sao có đá? Bé uống lạnh là tối ho, {ban} làm lại giùm {toi} nhé.'],
            kind=['{Ban} giải thích rõ vậy {toi} yên tâm. Người làm ăn cẩn thận {toi} nhìn là biết.'],
            rude=['{Toi} hỏi kỹ vì có con nhỏ, không phải làm khó {ban}. Nói chuyện đàng hoàng thì {toi} cũng đàng hoàng.'],
            sad=['Nghe giọng {ban} mệt quá, ăn uống gì chưa? Làm cha mẹ nên {toi} biết cái cảm giác chạy không kịp thở.'],
            two=['Món thì bé nhà {toi} khen, chỗ đó {toi} ưng. Mà sàn chỗ cửa hơi trơn, con nít chạy nhảy là {toi} thót tim.'],
            offer=['Nghe thì vui đó, mà {toi} quen coi giấy tờ, cái gì bấm xác nhận rõ ràng {toi} mới yên tâm.'],
        )),
    'sep_cam_ram': _A(
        label='Sếp càm ràm mà có tâm', tagline='soi quy trình, khen một lần thôi, gắt có lý do và luôn kèm cách sửa',
        knobs=dict(sass=2, opinion=3, warmth=1, slang=0), ages=('adult', 'middle'), regions=('Nam', 'Bắc'), emoji=0,
        angles=('sach', 'toc_do', 'thai_do', 'gia', 'tay_nghe', 'trend'), slang=(),
        sayings=('làm đến đâu gọn đến đó', 'khen một lần thôi', 'đúng quy trình', 'chốt sổ'),
        lines=dict(
            greet=['À {ban}. Để {toi} nhìn quanh cái đã, chỗ nào bừa là {toi} thấy liền đấy.',
                   'Chào {ban}. Hôm nay đông đấy, làm đến đâu gọn đến đó nhé.'],
            smalltalk=['Đọc hóa đơn tiền điện xong {toi} muốn tắt luôn máy lạnh. Mà tắt thì nóng, khổ thế đấy.',
                       'Hồi {toi} mới đi làm, dọn bàn sai cách còn bị nhắc cả tuần. Giờ tới lượt {toi} nhắc người khác.',
                       'Tối qua ngồi soát giấy tờ tới khuya, lệch có tí mà dò mãi mới ra.'],
            task=['Việc này {toi} cần gọn, đúng quy trình. Hỏi cho rõ rồi hẵng làm, đừng đoán.',
                  'Làm cho chuẩn giùm {toi}, sai một khâu là cuối ngày dò sổ mệt lắm.'],
            praise=['Hôm nay {ban} làm trơn tru đấy, không khách nào phàn nàn. {Toi} khen một lần thôi nhé, khen nhiều lại sinh hư.'],
            complain=['Quầy bừa thế này khách nhìn vào nghĩ gì? Làm đến đâu dọn đến đó, câu này {toi} nói lần thứ mấy rồi?'],
            bargain=['Giá là giá, {toi} không mặc cả. Nhưng làm nhanh gọn thì lần sau {toi} gửi thêm việc.'],
            mistake=['Nhập sai số lượng là cuối ngày lệch sổ, lệch sổ là {toi} mất ngủ. Sửa ngay, rồi ghi lại để lần sau khỏi lặp.'],
            kind=['Ừ, nhận lỗi thẳng thế là được. {Toi} càm ràm vì muốn giữ khách, không phải ghét {ban}.'],
            rude=['{Ban} có thể không đồng ý, nhưng nói bằng giọng đó thì không được. Bình tĩnh rồi nói lại.'],
            sad=['Hôm nay nặng thật. Nghỉ tay một lát đi, chỗ này để {toi} trông.'],
            two=['Khách khen món, cái đó {toi} ghi nhận. Mà đèn biển hiệu tắt một nửa rồi, nhìn như quán sắp dẹp tiệm.'],
            offer=['Nói miệng thì {toi} ghi nhận, nhưng cái gì dính tới tiền phải qua sổ sách, bấm xác nhận cho rõ.'],
        )),
    'ba_tam': _A(
        label='Hàng xóm nhiều chuyện', tagline='biết hết chuyện hẻm, kể úp mở, soi kỹ mà bênh người quen',
        knobs=dict(sass=2, opinion=3, warmth=2, slang=1), ages=('adult', 'middle', 'elder'), regions=('Nam', 'Bắc'), emoji=0,
        angles=('hem', 'bay_tri', 'gia', 'doi_minh', 'trend'), slang=('hóng', 'drama', 'về kể không ai tin', 'tới công chuyện'),
        sayings=('nói nhỏ nghe nè', 'cả hẻm biết rồi', 'ô dề'),
        lines=dict(
            greet=['Ơ {ban}! Lại đây, có chuyện này hay lắm nè.',
                   'Nè {ban}, sáng nay đi ngang thấy quán đông ghê, {toi} ngồi bên kia đếm không xuể.'],
            smalltalk=['Nói nhỏ nghe nè, sáng nay có chiếc xe tải đậu cuối hẻm, đồ đạc chở vô quá trời, chắc có người mới dọn tới.',
                       'Hôm qua cúp điện cả hẻm, ai cũng ra đầu ngõ ngồi, {toi} hóng được bao nhiêu là chuyện.',
                       'Chợ giờ rau lên giá dữ lắm, {toi} đứng trả giá mà người bán còn cà khịa lại {toi}.'],
            task=['Hỏi {toi} đi, {toi} nói kỹ cho, mà làm xong nhớ kể {toi} nghe vụ bên kia nha.',
                  'Làm cẩn thận giùm {toi}, cả hẻm này ai cũng hỏi {toi} chỗ nào làm được việc đó.'],
            praise=['Ly trà ngon thiệt, {toi} đi kể cả xóm rồi đó. Có ai hỏi là {toi} chỉ tới đây liền.'],
            complain=['Treo đèn nhấp nháy như đám cưới vậy {ban}, ô dề quá. Mà thôi, tụi trẻ thích vậy thì {toi} chịu.'],
            bargain=['Hàng xóm với nhau mà, bớt cho {toi} cái lẻ, {toi} quảng cáo không công cho {ban} cả hẻm.'],
            mistake=['{Toi} thấy hết rồi nha, đưa nhầm rồi đó. Đi đổi lẹ đi, {toi} không kể ai đâu… chắc vậy.'],
            kind=['Lễ phép ghê, {toi} thương. Mà nè, nghe tin gì mới trong hẻm chưa?'],
            rude=['Ơ hay, {toi} hỏi thăm thôi mà gắt vậy. Thôi được, {toi} đi, mà {toi} nhớ đó nha.'],
            sad=['Người ta nói gì kệ người ta, hẻm này ai chưa từng bị đồn. Cứ làm đàng hoàng là thiên hạ tự im.'],
            two=['Quán dạo này đông ghê, {toi} mừng cho {ban}. Mà xe khách đậu lấn qua cửa nhà bên, coi chừng người ta la đó.'],
            offer=['Thiệt hông đó? Nói miệng vậy thôi chứ {toi} phải thấy tận mắt mới tin, {toi} đâu dễ bị qua mặt.'],
        )),
    'ban_than': _A(
        label='Bạn thân cà khịa', tagline='chọc tay nghề trước rồi công nhận, tự trào, bênh bạn tới cùng',
        knobs=dict(sass=3, opinion=2, warmth=3, slang=2), ages=('young', 'adult'), regions=('Nam', 'Bắc'), emoji=1,
        angles=('tay_nghe', 'doi_minh', 'vi', 'thai_do', 'gia'),
        slang=('out trình', 'gòy soq', 'động lực thoái hóa', 'giỡn vậy có nên không trời', 'ê khó nha bro', 'bestie', 'hết cứu',
               'mặn', 'cà khịa'),
        sayings=('đùa thôi',),
        lines=dict(
            greet=['Ê {ban}, còn sống hả, tưởng bị công việc nuốt luôn rồi =))',
                   'Tới rồi nè, hôm nay tới chấm điểm tay nghề {ban} đó, chuẩn bị tinh thần đi.'],
            smalltalk=['Hôm qua định ngủ sớm, lướt điện thoại tới gà gáy luôn. Động lực thoái hóa thiệt sự.',
                       '{Toi} mới đăng ký lớp tập thể dục, đi được một buổi rồi nghỉ vì trời mưa… mấy tuần liền.',
                       'Tháng này {toi} thề tiết kiệm, mới giữa tháng đã thề lại lần hai 🤡'],
            task=['Ê làm cho {toi} đàng hoàng nha, bạn bè mà làm ẩu là {toi} kể cả nhóm nghe đó.',
                  'Hỏi {toi} cần gì đi, đứng đó cười cười là không qua mặt được {toi} đâu =))'],
            praise=['Ủa ai dạy {ban} làm ngon vậy, hồi xưa nấu gói mì còn khê mà. Thôi công nhận, lần này out trình thiệt.'],
            complain=['Cái này đem đi thi chắc ban giám khảo xin về sớm =)) Đùa thôi, bớt ngọt chút là đỉnh liền.'],
            bargain=['Bạn thân mà tính đủ tiền vậy hả? Tình bạn này có hạn sử dụng rồi… thôi trả đủ nè, ủng hộ {ban} giàu.'],
            mistake=['Gòy soq, đổ nguyên ly rồi kìa. Đứng đó chi, lau đi, {toi} không quay clip đâu… lần này thôi.'],
            kind=['Nói câu đó nghe sến ghê, mà cảm động thiệt. Mai {toi} ghé nữa.'],
            rude=['Ê, giỡn vậy có nên không trời. Bực gì thì kể {toi} nghe, đừng cọc với {toi}.'],
            sad=['Bỏ điện thoại xuống đi, mấy lời chê đó không định nghĩa {ban} đâu. Tối ra gốc bàng ngồi, xả hết cho {toi} nghe.'],
            two=['Tay nghề lên level thiệt á, {toi} phục. Mà quầy {ban} dán giấy nhắc việc kín mít, nhìn như bàn thi cuối kỳ.'],
            offer=['Nói hay ghê, mà bạn bè sòng phẳng mới lâu, bấm cho rõ ràng đi bestie.'],
        )),
    'ong_cu_am': _A(
        label='Cụ già hiền hậu', tagline='chậm, ấm, hay nhớ chuyện xưa, góp ý nhẹ như dặn con cháu',
        knobs=dict(sass=1, opinion=2, warmth=3, slang=0), ages=('elder',), regions=('Bắc', 'Nam'), emoji=0,
        angles=('thai_do', 'vi', 'am_thanh', 'troi', 'hem', 'doi_minh'), slang=(),
        sayings=('tiền nào của nấy', 'nói phải củ cải cũng nghe', 'chuyện gì rồi cũng qua'),
        lines=dict(
            greet=['À, {ban} đấy à. Lại đây ngồi với {toi} một lát.',
                   'Chào {ban}. Sáng nay trời mát, {toi} đi bộ một vòng rồi ghé đây.'],
            smalltalk=['Hồi đó con phố này chỉ có một cây bàng với cái chõng tre. Giờ đông vui thế này, {toi} ngồi nhìn cũng sướng.',
                       'Cháu {toi} bảo cái gì ngon là slay. {Toi} nghe cứ tưởng tên một món bánh.',
                       'Mưa rào mùa này đến nhanh đi nhanh, như tụi trẻ bây giờ, chạy suốt ngày.'],
            task=['{Toi} không vội đâu, {ban} cứ hỏi cho kỹ rồi làm, người có tuổi chờ quen rồi.',
                  'Làm cho {toi} vừa phải thôi nhé, đừng ngọt quá, bác sĩ dặn rồi.'],
            praise=['Món này ngọt thanh như hồi mẹ {toi} còn nấu. {Ban} làm có cái tâm, {toi} ăn là biết.'],
            complain=['Nhạc to quá {ban} à, {toi} nghe không rõ {ban} nói gì. Món thì {toi} khen, chỉ vặn nhỏ chút cho người có tuổi.'],
            bargain=['{Toi} không mặc cả đâu, tiền nào của nấy. Chỉ xin bớt cho {toi} ít đường thôi, bác sĩ dặn.'],
            mistake=['Không sao, không sao. {Toi} cũng từng đưa nhầm thư cả tháng trời mới biết. Sửa là được.'],
            kind=['{Ban} lễ phép quá. {Toi} về khoe với cháu là ngoài phố có người làm ăn tử tế.'],
            rude=['{Ban} đang mệt phải không? {Toi} không giận đâu, nhưng lần sau nói nhẹ thôi nhé.'],
            sad=['Ngồi xuống đây một lát. Chuyện gì rồi cũng qua, như mưa rào mùa hạ ấy mà.'],
            two=['Chè ngon, {toi} khen thật. Mà cái ghế nhựa thấp quá, ngồi xuống rồi đứng lên là cả một công trình.'],
            offer=['Tấm lòng thế là quý rồi. Nhưng tiền nong cứ làm cho rõ ràng, {toi} có tuổi rồi hay quên lắm.'],
        )),
    'shipper_lay': _A(
        label='Shipper lầy', tagline='chạy cả ngày, xui cũng đem ra cười, khen chê chuyện gói hàng và đường sá',
        knobs=dict(sass=2, opinion=2, warmth=2, slang=2), ages=('young', 'adult', 'middle'), regions=('Nam', 'Bắc'), emoji=1,
        angles=('hem', 'troi', 'tien', 'toc_do', 'doi_minh'),
        slang=('bom hàng', 'tới công chuyện', 'hên lắm mới xui được vậy', 'về kể không ai tin', 'ét o ét', 'ăn hành', 'xu cà na',
               'ổn áp', 'toang'),
        sayings=('dân chạy đơn',),
        lines=dict(
            greet=['Chào {ban}, cho {toi} xin ly nước đá, ngoài đường nắng muốn xỉu 🛵',
                   'Ê {ban}, {toi} ghé nhanh nha, còn mấy đơn đang chờ ngoài kia.'],
            smalltalk=['Sáng giờ bị bom hàng hai đơn, gọi muốn cháy máy không ai bắt. Hên lắm mới xui được vậy á.',
                       'Địa chỉ ghi hẻm bên trái mà khách đứng hẻm bên phải, tới công chuyện luôn.',
                       'Mưa to quá, {toi} mặc áo mưa mà vẫn ướt từ đầu tới chân, về kể không ai tin.'],
            task=['Làm lẹ giùm {toi} nha, {toi} còn chạy đơn khác. Hỏi gì hỏi nhanh, {toi} trả lời liền.',
                  'Gói kỹ giùm {toi} nha, đường ổ gà nhiều lắm, đổ là {toi} ăn hành.'],
            praise=['Gói kỹ vầy {toi} chạy qua ổ gà cũng không đổ giọt nào, quán mình uy tín ghê.'],
            complain=['Nắp ly đậy hờ vầy là tới ngã tư đầu tiên thành nước rửa xe luôn á. Dán giùm {toi} miếng keo đi.'],
            bargain=['Phí ship là của app, {toi} không bớt được, {toi} chỉ bớt được cái mặt nhăn thôi, cười cái nè.'],
            mistake=['Ủa đơn này đâu phải của {toi}, đổi lẹ giùm đi, trễ là khách bom hàng luôn á.'],
            kind=['Có ly nước đá là hồi sinh liền, {ban} đúng là cứu tinh của dân chạy đơn.'],
            rude=['{Toi} chỉ hỏi xong chưa thôi mà, gắt chi. Ai cũng đang chạy deadline hết.'],
            sad=['{Toi} bị khách chê hoài, chê xong mai vẫn chạy. Mình biết mình làm kỹ là được, ráng nha.'],
            two=['Quán mình gói hàng ổn áp nha. Mà hẻm này không có số nhà, lần nào vô {toi} cũng đi lạc một vòng.'],
            offer=['Nghe sướng ghê, mà dân chạy đơn như {toi} chỉ tin cái app báo xong thôi, bấm cho chắc nha.'],
        )),
    'co_ha_noi': _A(
        label='Người Hà Nội chanh chua', tagline='kỹ tính, nói thẳng, chê món chứ không chê người, thương bằng hành động',
        knobs=dict(sass=3, opinion=3, warmth=2, slang=0), ages=('adult', 'middle', 'elder'), regions=('Bắc',), emoji=0,
        angles=('vi', 'gia', 'sach', 'thai_do', 'am_thanh', 'so_sanh'), slang=(),
        sayings=('ối giời ơi', 'khổ thân', 'được cái', 'nói thật', 'nói thế mà nghe được à'),
        lines=dict(
            greet=['Ơ, {ban} đấy à. Hôm nay mở muộn thế, {toi} đứng chờ mỏi cả chân.',
                   'Chào {ban}. Nói trước nhé, hôm nay {toi} khó tính đấy.'],
            smalltalk=['Nhà bên hát karaoke tới khuya, {toi} định sang nói, nghĩ lại thôi để mai nói cho có sức.',
                       'Chợ sáng nay rau muống đắt như tôm tươi, ối giời ơi, ăn miếng rau cũng phải nghĩ.',
                       'Mùa này ngoài Bắc se lạnh rồi, trong này vẫn nóng hầm hập, {toi} nhớ gió heo may quá.'],
            task=['Làm cho cẩn thận vào nhé, {toi} nói trước là {toi} không dễ tính đâu.',
                  'Hỏi {toi} cho rõ rồi hẵng làm, đừng có đoán mò rồi lại làm lại, mất thời gian cả đôi bên.'],
            praise=['Ừ, bánh này được đấy, xốp mà không ngấy. {Toi} khen thật, chứ {toi} không khen ai dễ đâu nhé.'],
            complain=['Ối giời ơi, trà gì mà ngọt lợ thế này, uống xong phải đi súc miệng. Pha lại cho {toi}, ít đường thôi.'],
            bargain=['Giá này mà cũng dám đề à? Ngoài chợ bán thế là đắt đấy. Thôi, bớt cho {toi} tí, {toi} mua thường xuyên.'],
            mistake=['Đưa nhầm tiền thừa à? May cho {ban} là gặp {toi} đấy, gặp người khác thì mất trắng. Đếm lại đi.'],
            kind=['Được cái ăn nói lễ phép. Thôi, {toi} bỏ qua, lần sau nhớ đấy.'],
            rude=['Nói với người lớn thế à? {Toi} không chấp, nhưng thế thì khách nào nó ở lại.'],
            sad=['Khổ thân, trông mệt thế kia. Ngồi đấy, {toi} đi rót cốc nước cho.'],
            two=['Nước dùng trong, được. Mà cái bàn dính tay thế này thì {toi} nói thật, khách kỹ là không quay lại đâu.'],
            offer=['Nói thế thì ai chả nói được. Làm cho đàng hoàng, có giấy tờ rõ ràng thì {toi} mới tin.'],
        )),
    'hoc_sinh': _A(
        label='Học sinh tan học', tagline='hồn nhiên, lễ phép, khen chê thật thà theo kiểu học trò',
        knobs=dict(sass=1, opinion=2, warmth=2, slang=2), ages=('child', 'teen'), regions=('Nam', 'Bắc'), emoji=1,
        angles=('gia', 'vi', 'doi_minh', 'trend', 'bay_tri'), slang=('xỉu', 'đỉnh', 'xịn xò', 'slay', 'gét gô', 'cháy', 'rén', 'hông', 'khum'),
        sayings=(),
        lines=dict(
            greet=['Dạ chào {ban}! Tụi {toi} vừa tan học nè, đói xỉu luôn á.',
                   '{Ban} ơi, hôm nay có gì mới hông, {toi} chạy qua liền nè!'],
            smalltalk=['Nay kiểm tra toán {toi} làm được hết… trừ câu cuối. Mà câu cuối nhiều điểm nhất 😭',
                       'Bạn cùng bàn {toi} nuôi con mèo biết bắt tay, {toi} năn nỉ mẹ mà mẹ nói để lớn rồi tính.',
                       'Chiều nay tụi {toi} đá cầu thua lớp bên, mai phục thù, gét gô!'],
            task=['Dạ {ban} hỏi {toi} đi, {toi} nói rõ lắm luôn á, mẹ dặn kỹ rồi.',
                  '{Ban} làm giùm {toi} với, {toi} để dành tiền cả tuần đó.'],
            praise=['{Ban} ơi cái này ngon xỉu á, mai tụi {toi} rủ cả lớp tới luôn!'],
            complain=['{Ban} ơi trân châu nay cứng như viên bi á, hôm qua mềm hơn nhiều. {Ban} coi lại giùm {toi} nha.'],
            bargain=['Tiền tiêu vặt của {toi} chỉ đủ phần nhỏ thôi, {ban} thêm cho {toi} ít topping được hông ạ, năn nỉ á 🥺'],
            mistake=['Ủa {ban}, {toi} gọi vị đào mà ra vị vải á. Thôi hông sao, vải cũng ngon, lần sau nhớ nha!'],
            kind=['{Ban} dễ thương quá trời, {toi} bầu đây là chỗ ruột của lớp luôn.'],
            rude=['Dạ… {toi} xin lỗi, {toi} không có ý làm phiền đâu ạ.'],
            sad=['{Ban} buồn hả? {Toi} cho {ban} viên kẹo dâu nè, ngon lắm.'],
            two=['Cái này xịn xò ghê á! Mà để trên kệ cao quá, {toi} với hoài hông tới.'],
            offer=['Thiệt hả {ban}? Vui quá trời, mà mẹ {toi} dặn cái gì cũng phải trả tiền đàng hoàng á.'],
        )),
}
BUCKETS = ('greet', 'smalltalk', 'task', 'praise', 'complain', 'bargain', 'mistake', 'kind', 'rude', 'sad', 'two', 'offer')

# Existing voices (game/voices.py) -> archetypes that fit them; () = stays unspiced (calm/polite/interviewers).
# Job-bound archetypes (shipper_lay) come from ROLE_RULES only, so nobody else talks about their delivery runs.
VOICE_TO_ARCH = {
    'genz': ('genz_khach',), 'song_ao': ('genz_khach',), 'drama': ('genz_khach', 'ba_tam'), 'ban_phim': ('genz_khach', 'ban_than'),
    'hay_doi': ('genz_khach', 'hoc_sinh'), 'van_phong': ('vp_deadline',), 'than_tho': ('vp_deadline', 'ba_hang_cho'),
    'buon_ban': ('ba_hang_cho',), 'thuc_dung': ('ba_hang_cho', 'co_ha_noi'), 'bia_hoi': ('chu_triet_ly',),
    'mat_lanh_hai': ('chu_triet_ly', 'ban_than'), 'lac_quan': ('chu_triet_ly', 'ban_than'), 'me_bim': ('me_bim_ky',),
    'da_nghi': ('me_bim_ky', 'co_ha_noi'), 'ky_luat': ('sep_cam_ram', 'me_bim_ky'), 'biet_tuot': ('sep_cam_ram', 'chu_triet_ly'),
    'si_dien': ('sep_cam_ram', 'co_ha_noi'), 'nhieu_chuyen': ('ba_tam',), 'camera': ('ba_tam',), 'phan_xet': ('co_ha_noi', 'ba_tam'),
    'can_nhan': ('co_ha_noi', 'sep_cam_ram'), 'hong_hot': ('co_ha_noi', 'ba_hang_cho'), 'lay_loi': ('ban_than', 'genz_khach'),
    'tsundere': ('ban_than', 'co_ha_noi'), 'thang_than': ('ban_than', 'ba_hang_cho'), 'hoai_niem': ('ong_cu_am',),
    'am_ap': ('ong_cu_am', 'ba_hang_cho'), 'tam_ly': ('ong_cu_am', 'vp_deadline'), 'tam_linh': ('ba_tam',),
    'mo_mong': ('genz_khach',), 'ngay_tho': ('hoc_sinh',), 'nhut_nhat': ('hoc_sinh',), 'tre_con': ('hoc_sinh',),
    'tre_nghich': ('hoc_sinh',), 'huong_noi': (), 'lich_su': (), 'lanh_lung': (), 'pv_am': (), 'pv_nghiem': (), 'pv_lanh': (),
}
# Voices that stay calm even when nothing in their list fits the age.
CALM = ('huong_noi', 'lich_su', 'lanh_lung', 'nhut_nhat', 'pv_am', 'pv_nghiem', 'pv_lanh')
# Role words win over the voice when the age fits (matched case-insensitively).
ROLE_RULES = (
    (('shipper', 'giao hàng', 'tài xế công nghệ', 'giao nhận'), 'shipper_lay'),
    (('trưởng ca', 'trưởng nhóm', 'trưởng phòng', 'quản lý', 'bếp trưởng', 'kế toán trưởng', 'sếp'), 'sep_cam_ram'),
    (('học sinh',), 'hoc_sinh'),
    (('xe ôm',), 'chu_triet_ly'),
    (('bán xôi', 'bán chè', 'tạp hóa', 'sạp chợ', 'thương lái'), 'ba_hang_cho'),
    (('phụ huynh',), 'me_bim_ky'),
)
# Gender-coded archetypes (their ids and flavour read as one gender): only NPCs known to be that
# gender get them. The rest are neutral: their lines carry no self pronoun of their own ({toi} is the
# NPC's own xưng hô), so they fit anyone of a matching age.
ARCH_GENDER = dict(ba_tam='f', me_bim_ky='f', co_ha_noi='f', ba_hang_cho='f', chu_triet_ly='m')
FEMALE = frozenset(('chị', 'cô', 'bà', 'dì', 'mẹ', 'thím', 'mợ', 'má'))
MALE = frozenset(('anh', 'chú', 'ông', 'bố', 'cậu', 'dượng'))
# The kinship words an archetype line must never hard-code (the NPC's self word comes from {toi}).
KIN = r'cô|chú|bà|ông|anh|chị'
# Third-person phrases that are fine in a line ("mấy bà bán rau").
KIN_OK = re.compile(r'(?<!\w)(mấy (bà|ông|anh|chị|cô|chú)|bà con|ông bà|anh chị em|chị em|anh em)(?!\w)', re.I)
# Nearest compatible stand-ins when a mapped archetype does not fit the person (board tempers).
SUBSTITUTE = dict(
    co_ha_noi=('chu_triet_ly', 'sep_cam_ram', 'ong_cu_am', 'vp_deadline'),
    ba_tam=('chu_triet_ly', 'ban_than', 'ong_cu_am', 'vp_deadline'),
    ba_hang_cho=('chu_triet_ly', 'sep_cam_ram', 'ong_cu_am', 'vp_deadline'),
    me_bim_ky=('sep_cam_ram', 'vp_deadline', 'ong_cu_am'),
    chu_triet_ly=('co_ha_noi', 'sep_cam_ram', 'ong_cu_am', 'vp_deadline'),
    ban_than=('chu_triet_ly', 'ba_hang_cho', 'ong_cu_am', 'genz_khach'),
    genz_khach=('ban_than', 'vp_deadline', 'ba_tam', 'chu_triet_ly', 'ong_cu_am'),
    vp_deadline=('sep_cam_ram', 'ong_cu_am', 'genz_khach'),
    sep_cam_ram=('vp_deadline', 'co_ha_noi', 'chu_triet_ly', 'ong_cu_am'),
    ong_cu_am=('chu_triet_ly', 'ba_tam', 'ba_hang_cho', 'sep_cam_ram', 'vp_deadline'),
    shipper_lay=('vp_deadline', 'ban_than'),
)
# When neither role nor voice fits the age: a pool by age (spread keeps a workplace varied).
AGE_POOL = {
    'child': ('hoc_sinh',), 'teen': ('hoc_sinh',),
    'young': ('genz_khach', 'ban_than', 'vp_deadline'),
    'adult': ('vp_deadline', 'ban_than', 'me_bim_ky', 'sep_cam_ram', 'ba_hang_cho', 'co_ha_noi', 'genz_khach', 'ba_tam'),
    'middle': ('ba_hang_cho', 'co_ha_noi', 'chu_triet_ly', 'ba_tam', 'sep_cam_ram', 'me_bim_ky'),
    'elder': ('ong_cu_am', 'ba_tam', 'chu_triet_ly', 'ba_hang_cho', 'co_ha_noi'),
}
# Neighbourhood board temperaments (game/board_content.py TEMPERS) -> archetypes.
BOARD_TEMPER_TO_ARCH = dict(
    warm='ong_cu_am', gossip='ba_tam', camera='ba_tam', superstitious='ba_tam', genz='genz_khach', showoff='genz_khach',
    drama='genz_khach', beer='chu_triet_ly', knowitall='chu_triet_ly', tigermom='me_bim_ky', suspicious='me_bim_ky',
    grumpy='co_ha_noi', judge='co_ha_noi', joker='ban_than', tsundere='ban_than', optimist='ban_than', practical='ba_hang_cho',
    official='sep_cam_ram', kid='hoc_sinh', cold=None, shy=None,
)

# ------------------------------------------------------------------ guard data (used by game/ai.py)
# Everyday idioms the abuse filter must not trip on (player messages and NPC replies).
SAFE_IDIOMS = re.compile(
    r'(?<!\w)(?<!đánh )(?<!đặt )(?<!ném )(?<!thả )'
    r'(bom (hàng|đơn)(?! loạt)|bom tấn|chém (gió|giá)|giết thời gian|chết đi được|chết cười|mệt chết)(?!\w)', re.I)
# Service-desk phrases a person on the street never says (the model's assistant habit).
ASSISTANT_PHRASES = re.compile(
    r'(tôi|mình|em|chị|anh) có thể (giúp|hỗ trợ) gì|rất (vui|hân hạnh|sẵn lòng) (được )?(hỗ trợ|phục vụ|giúp đỡ)|'
    r'mình đang trao đổi về|bạn có thể hỏi|trợ lý (ảo|ai)|là một trợ lý|như một trợ lý|chúc bạn một ngày tốt lành|'
    r'với tư cách (là )?(một )?(trợ lý|mô hình)', re.I)
# mày/tao (never from an NPC); lông mày, mặt mày, mày mò, tao nhã, thanh tao, Tao Đàn are fine.
RUDE_PRONOUN = re.compile(r'(?<!lông )(?<!chân )(?<!mặt )(?<!\w)mày(?! mò)(?!\w)|(?<!thanh )(?<!\w)tao(?! nhã| đàn| ngộ| khang)(?!\w)', re.I)
# Looks / region / class words for chat (the review list in review_aspects_content.UNSAFE covers
# the rest; "grab" is left out there for chat because it is an everyday English verb).
CHAT_UNSAFE = re.compile(
    r'(?<!\w)(phèn|keo lỳ|cộng tươi|sẽ gầy|hút độc rắn|namkiki|parky|trôn việt nam|mlem (anh|chị|em|bạn|cô|chú)|'
    r'chạy grab|app grab|grab ?(bike|food|car))(?!\w)', re.I)
_LOOKS: list = []


def chat_unsafe(text: str) -> bool:
    """Looks, body, age, region, religion, sex words and real brands in a chat line (the review list
    of review_aspects_content.UNSAFE without "grab", an everyday English verb, plus CHAT_UNSAFE)."""
    if not isinstance(text, str):
        return False
    if not _LOOKS:
        from .review_aspects_content import UNSAFE
        _LOOKS.append(re.compile(r'(?<!\w)(' + '|'.join(x for x in UNSAFE if x != r'grab') + r')(?!\w)', re.I))
    t = unicodedata.normalize('NFC', text)
    return bool(_LOOKS[0].search(t) or CHAT_UNSAFE.search(t))


# One emoji "cluster" (base + skin tone / variation selector + ZWJ parts).
_E = '[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]'
_M = '[\uFE0F\U0001F3FB-\U0001F3FF]*'
EMOJI = re.compile(f'{_E}{_M}(?:\u200D{_E}{_M})*')


def trim_emoji(text: str, cap: int) -> str:
    """Keep the first `cap` emoji of a line, drop the rest (never rejects a line)."""
    seen = 0

    def keep(m):
        nonlocal seen
        seen += 1
        return m.group(0) if seen <= cap else ''
    out = EMOJI.sub(keep, text)
    if seen <= cap:
        return text
    return re.sub(r'\s+([,.!?…])', r'\1', re.sub(r'\s{2,}', ' ', out)).strip()


# ------------------------------------------------------------------ helpers
def enabled() -> bool:
    """AI_SPICE=0 turns the prompt blocks off (scripted flavour stays)."""
    return (os.environ.get('AI_SPICE', '1') or '1').strip() not in ('0', 'false', 'off', 'no')


def _h(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def fold(text: str) -> str:
    s = unicodedata.normalize('NFD', str(text or '').lower()).replace('đ', 'd')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def _fill(text: str, address: dict | None, cap: bool = True) -> str:
    a = address or {}
    me, you = a.get('self') or 'mình', a.get('player') or 'bạn'
    out = (text.replace('{toi}', me).replace('{ban}', you)
           .replace('{Toi}', me[:1].upper() + me[1:]).replace('{Ban}', you[:1].upper() + you[1:]))
    return out[:1].upper() + out[1:] if cap and out else out


def _region_fits(arch: str, region: str | None) -> bool:
    if not region:
        return True
    return any(r in region for r in ARCHETYPES[arch]['regions'])


def gender_of(name: str = '', self_word: str = '') -> str | None:
    """'f' / 'm' from the kinship word leading the name ("Cô Diệp") or the NPC's self word; None = unknown."""
    for w in ((str(name or '').strip().split() or [''])[0].lower(), str(self_word or '').strip().lower()):
        if w in FEMALE:
            return 'f'
        if w in MALE:
            return 'm'
    return None


def fits(arch: str | None, gender: str | None, age: str) -> bool:
    """Archetype compatible with this person: age band in its ages, and a gender-coded one only for
    people known to be that gender (unknown gender gets neutral archetypes only)."""
    a = ARCHETYPES.get(arch or '')
    if not a or age not in a['ages']:
        return False
    need = ARCH_GENDER.get(arch)
    return need is None or need == gender


def fit(arch: str | None, gender: str | None, age: str) -> str | None:
    """`arch` when it fits the person, else its nearest compatible stand-in (None = none fits)."""
    if not arch:
        return None
    if fits(arch, gender, age):
        return arch
    return next((x for x in SUBSTITUTE.get(arch, ()) if fits(x, gender, age)), None)


def age_band(years: int) -> str:
    return ('child' if years < 12 else 'teen' if years < 16 else 'young' if years < 25 else 'adult' if years < 45
            else 'middle' if years < 60 else 'elder')


def kin_clash(raw: str) -> bool:
    """A raw archetype line that hard-codes a kinship pronoun (it would fight the NPC's own xưng hô)."""
    return bool(re.search(r'(?<!\w)(' + KIN + r')(?!\w)', KIN_OK.sub(' ', raw), re.I))


def _candidates(npc_id: str, voice_id: str, role: str, age: str, temper: str | None, region: str | None,
                gender: str | None = None) -> list:
    """Ordered archetype candidates for one NPC ([] = no spice), all compatible with its age and gender."""
    if voice_id in ('pv_am', 'pv_nghiem', 'pv_lanh') or temper == 'interviewer':
        return []
    if age == 'child' or temper == 'child':
        return ['hoc_sinh']
    low = (role or '').lower()
    out = []
    for words, arch in ROLE_RULES:
        if any(w in low for w in words) and fits(arch, gender, age):
            out.append(arch)
            break
    voice_pool = [a for a in VOICE_TO_ARCH.get(voice_id, ()) if fits(a, gender, age)]
    if voice_pool:
        start = _h('arch', npc_id) % len(voice_pool)
        out += voice_pool[start:] + voice_pool[:start]
    if not out and voice_id in CALM:
        return []
    age_pool = [a for a in AGE_POOL.get(age, AGE_POOL['adult']) if fits(a, gender, age)]
    if not age_pool and not out:
        return []
    start = _h('arch-age', npc_id) % max(1, len(age_pool))
    out += age_pool[start:] + age_pool[:start]
    out = list(dict.fromkeys(out))
    local = [a for a in out if _region_fits(a, region)]
    return local or out


_ARCH_CAST: dict = {}


def _workplace(career: str) -> dict:
    """npc id -> (voice id, archetype) for one workplace: people there take different archetypes
    when they have another fitting candidate (stable: depends on content only, not on the save)."""
    if career in _ARCH_CAST:
        return _ARCH_CAST[career]
    from .content import NPCS
    from . import personas, voices
    used: dict = {}
    out = {}
    for n in sorted((x for x in NPCS if x.get('career_id') == career), key=lambda x: x['id']):
        age = personas._age(n, career)
        temper = personas._temper(career, n['id'], n, age)
        v = voices.for_npc(n['id'], n.get('role', ''), age, temper, career)
        g = gender_of(n.get('display_name', ''), personas._address({}, career, n, age, temper).get('self'))
        cands = _candidates(n['id'], v['id'], n.get('role', ''), age, temper, _card_region(n['id'], v), g)
        pick = None
        if cands:
            fresh = [a for a in cands if not used.get(a)]
            pick = fresh[0] if fresh else min(cands, key=lambda a: used.get(a, 0))
            used[pick] = used.get(pick, 0) + 1
        out[n['id']] = (v['id'], pick)
    _ARCH_CAST[career] = out
    return out


def _card_region(npc_id: str, voice: dict) -> str:
    """Same region pick as personas.persona() (kept in step with it)."""
    from . import personas
    region, _ = personas.REGION[personas._h(npc_id) % 2]
    lean = sum(x in personas.SOUTH for x in voice['particles']) - sum(x in personas.NORTH for x in voice['particles'])
    dialect = voice.get('dialect') or ''
    if 'Bắc' in dialect or 'Nam' in dialect or lean:
        region = personas.REGION[1][0] if 'Bắc' in dialect or (lean < 0 and 'Nam' not in dialect) else personas.REGION[0][0]
    return region


def archetype_for(npc_id: str, voice_id: str, role: str = '', age: str = 'adult', temper: str | None = None,
                  career: str | None = None, region: str | None = None, gender: str | None = None) -> str | None:
    """The NPC's stable archetype (None = no spice: interviewers and calm, polite voices). Town NPCs
    take their gender from the name / self word (see _workplace); `gender` is for anyone else."""
    if career:
        row = _workplace(career).get(npc_id)
        if row and row[0] == voice_id:
            return row[1]
    cands = _candidates(str(npc_id), voice_id, role, age, temper, region, gender)
    if not cands:
        return None
    return cands[0]


def _clamp(x: int) -> int:
    return max(0, min(3, int(x)))


def knobs_for(arch: str | None, npc_id: str = '', *, purpose: str = 'chat', mood: str | None = None,
              temper: str | None = None, age: str | None = None) -> dict | None:
    """sass/opinion/warmth/slang (0-3) + emoji cap for this NPC on this surface (None = no spice)."""
    if not arch or arch not in ARCHETYPES or purpose == 'interview':
        return None
    a = ARCHETYPES[arch]
    k = dict(a['knobs'])
    j = _h('knob', npc_id) % 8
    if j < 4:  # per-NPC jitter: two people of one archetype still differ
        key = ('sass', 'opinion', 'warmth', 'slang')[j]
        k[key] += 1 if _h('knob-dir', npc_id) % 2 else -1
    if mood == 'buc':
        k['sass'] += 1
    elif mood == 'buon':
        k['sass'] -= 1
        k['warmth'] += 1
    elif mood == 'hao_hung':
        k['opinion'] += 1
    elif mood == 'met':
        k['slang'] -= 1
    if temper in ('rude', 'sour', 'entitled', 'drama', 'parent_rude'):
        k['sass'] += 1
    elif temper in ('warm', 'parent_kind'):
        k['warmth'] += 1
    elif temper == 'quiet':
        k['slang'] = min(k['slang'], 1)
        k['opinion'] -= 1
    k = {x: _clamp(v) for x, v in k.items()}
    if not a['slang']:
        k['slang'] = 0  # an archetype without slang words never gets a budget from jitter
    emoji = a['emoji']
    if age == 'child' or purpose == 'class_question':
        k['sass'], k['slang'] = min(k['sass'], 1), 0
    if purpose == 'parent_message':
        k['slang'], k['sass'], emoji = 0, min(k['sass'], 2), 0
    elif purpose == 'support_call':
        k['sass'], k['slang'] = min(k['sass'], 1), min(k['slang'], 1)
    elif purpose == 'board':
        emoji += 1
    k['warmth'] = max(1, k['warmth'])  # the owner wants warm people, always
    k['emoji'] = emoji
    return k


# ------------------------------------------------------------------ situations
SITUATIONS = dict(greet='chào hỏi', smalltalk='chuyện phiếm', task='đang có việc cần làm', bargain='mặc cả, chuyện giá',
                  mistake='có chuyện làm sai', kind='người chơi tử tế', rude='người chơi nói hỗn', sad='người chơi buồn, mệt',
                  board='bình luận trong nhóm cư dân')
SITUATION_BUCKETS = dict(greet=('greet', 'smalltalk'), smalltalk=('smalltalk', 'two'), task=('task', 'complain', 'praise'),
                         bargain=('bargain', 'offer'), mistake=('mistake', 'complain'), kind=('kind', 'praise'),
                         rude=('rude',), sad=('sad',), board=('two', 'smalltalk', 'complain'))
# (accented pattern on the lower-case text, unaccented pattern used when the player typed without accents)
_WORDS = dict(
    sad=(r'buồn|mệt|chán quá|chán nản|stress|khóc|thất vọng|áp lực|nản|tủi thân|cô đơn|bị chê|bị đồn|bị mắng|kiệt sức',
         r'buon(?! ban| may)|met|chan qua|chan nan|stress|khoc|that vong|ap luc|nan qua|tui than|co don|bi che|bi don|bi mang|kiet suc'),
    rude=(r'ngu thế|ngu vậy|ngu quá|đồ ngu|ngu ngốc|đần|cút|im đi|im mồm|câm|phiền quá|điên|khùng|láo|lắm mồm|ai hỏi|liên quan gì|kệ tôi|kệ tui|biến đi',
          r'ngu the|ngu vay|ngu qua|do ngu|cut di|im di|im mom|cam mom|phien qua|dien a|lam mom|ai hoi|lien quan gi|ke toi|ke tui|bien di'),
    bargain=(r'bớt|giảm giá|rẻ|mặc cả|đắt|mắc quá|bao nhiêu tiền|giá|khuyến mãi|miễn phí|free',
             r'bot|giam gia|re qua|re hon|mac ca|dat qua|mac qua|bao nhieu tien|gia bao|khuyen mai|mien phi|free'),
    mistake=(r'nhầm|làm sai|lỡ tay|làm đổ|làm hỏng|quên mất', r'nham|lam sai|lo tay|lam do|lam hong|quen mat'),
    ask=(r'cần gì|muốn gì|gọi gì|lấy gì|đặt gì|cần mua|nhu cầu|mua gì|chọn gì|món gì|màu gì|ngân sách',
         r'can gi|muon gi|goi gi|lay gi|dat gi|can mua|nhu cau|mua gi|chon gi|mon gi|mau gi|ngan sach'),
    kind=(r'cảm ơn|cám ơn|dễ thương|giỏi|tuyệt|thương quá|thương ghê|quý quá|xin lỗi|khen|hay quá|ngon',
          r'cam on|de thuong|gioi qua|tuyet|thuong qua|xin loi|khen|hay qua|ngon'),
    greet=(r'chào|hello|hi|alo|hế lô|hí', r'chao|hello|hi|alo|he lo'),
)
_RX = {k: (re.compile(r'(?<!\w)(' + a + r')(?!\w)'), re.compile(r'(?<!\w)(' + b + r')(?!\w)')) for k, (a, b) in _WORDS.items()}


def _has(kind: str, low: str, folded: str, plain: bool) -> bool:
    accented, bare = _RX[kind]
    return bool(accented.search(low) or (plain and bare.search(folded)))


def situation_of(player_text: str, task: dict | None = None, canonical: str = '') -> str:
    """A cheap guess of what kind of turn this is (keys of SITUATIONS)."""
    low = unicodedata.normalize('NFC', str(player_text or '')).lower()
    folded = fold(low)
    plain = folded == low  # typed without accents: the bare patterns are safe to use
    if _has('sad', low, folded, plain):
        return 'sad'
    if _has('rude', low, folded, plain):
        return 'rude'
    try:
        from .mistake_lines import REACTION
        reaction = any(canonical and x in canonical for rows in REACTION.values() for x in rows)
    except ImportError:
        reaction = False
    if reaction or (isinstance(task, dict) and task.get('mistakes')) or _has('mistake', low, folded, plain):
        return 'mistake'
    if _has('bargain', low, folded, plain):
        return 'bargain'
    if task and _has('ask', low, folded, plain):
        return 'task'
    if _has('kind', low, folded, plain):
        return 'kind'
    if _has('greet', low, folded, plain):
        return 'greet'
    return 'task' if task else 'smalltalk'


# ------------------------------------------------------------------ prompt text
def _rows(arch: str, buckets) -> list:
    lines = ARCHETYPES[arch]['lines']
    return [x for b in buckets for x in lines.get(b, [])]


def examples(arch: str, situation: str, seed: int = 0, address: dict | None = None, n: int = 2) -> list[str]:
    """`n` lines for this situation, rotated by `seed` so the anchor changes every turn."""
    rows = [x for x in _rows(arch, SITUATION_BUCKETS.get(situation, ('smalltalk', 'two'))) if not kin_clash(x)]
    if not rows:
        return []
    start = seed % len(rows)
    order = rows[start:] + rows[:start]
    return [_fill(x, address) for x in order[:n]]


def _mix_rule(k: dict) -> str:
    if k['sass'] >= 2 and k['warmth'] >= 2:
        return 'Cà khịa CÁI VIỆC một câu rồi xuống nước (khen thật, chỉ cách sửa, rót nước, hỏi ăn gì chưa); khen thì có gai.'
    if k['sass'] >= 2:
        return 'Đanh đá có lý: gắt nhưng kết bằng điều mình muốn cụ thể; khen một lần thôi.'
    return 'Trêu nhẹ, hiền; khen trước góp ý sau; quan tâm bằng việc nhỏ.'


def _slang_rule(arch: str, k: dict) -> str:
    a = ARCHETYPES[arch]
    words = ', '.join(a['slang'][:6])
    sayings = ', '.join(a['sayings'][:3])
    if k['slang'] <= 0 or not words:
        return 'Không lóng Gen Z' + (f', dùng câu cửa miệng ({sayings})' if sayings else '') + '.'
    budget = {1: 'Tối đa 1 từ lóng', 2: 'Tối đa 2 từ lóng'}.get(k['slang'], 'Tối đa 2 từ lóng + 1 kiểu viết dễ thương (khum, z)')
    return f'{budget} ({words}).'


def prompt_block(arch: str | None, knobs: dict | None, situation: str = 'smalltalk', *, verbosity: str = 'vua',
                 address: dict | None = None, seed: int = 0, lang: str = 'vi') -> str:
    """The "THÁI ĐỘ" block, appended after the voice block ('' when off or unspiced). Kept short:
    it rides on every chat call (see the token note in the module docstring)."""
    if not arch or not knobs or arch not in ARCHETYPES or not enabled():
        return ''
    a, k = ARCHETYPES[arch], knobs
    angles = ', '.join(ANGLES[x] for x in a['angles'][:3])
    lines = [
        f'THÁI ĐỘ: {a["label"]} ({a["tagline"]}); xéo {k["sass"]}, chính kiến {k["opinion"]}, ấm {k["warmth"]}, lóng {k["slang"]} (thang 3).',
        '- Có chính kiến; chê phải có lý do cụ thể, có hình ảnh, nói luôn mình muốn gì.',
        ('- Kiệm lời: một câu cụt có thái độ.' if verbosity == 'kiem_loi' else
         f'- Nhận xét ÍT NHẤT HAI góc (vd {angles}, chuyện riêng).'),
        '- ' + _mix_rule(k),
        '- Chỉ xéo CÁI VIỆC, KHÔNG xéo CON NGƯỜI (ngoại hình, tuổi, vùng miền, giới tính, tôn giáo, gia cảnh, học lực). Không mày/tao, không tục.',
        '- Người chơi buồn, xin lỗi, hay là trẻ con: chỉ ấm. Hỗn: một câu có ranh giới rồi thôi.',
        f'- Tối đa một câu cà khịa; không lặp câu mở đầu lượt trước. {_slang_rule(arch, k)} Emoji tối đa {k["emoji"]}.',
    ]
    ex = examples(arch, situation, seed, address, n=1)
    if ex:
        me = (address or {}).get('self')
        keep = f'; giữ xưng "{me}"' if me else '; giữ xưng hô của mình'
        lines.append(f'Nhịp mẫu ({SITUATIONS.get(situation, SITUATIONS["smalltalk"])}; không chép{keep}): {ex[0]}')
    if lang == 'en':
        lines.append('Write natural English with this attitude; no Vietnamese slang.')
    return '\n'.join(lines)


def review_rule(arch: str | None = None) -> str:
    """One recipe line for review rewrites and reply decisions ('' when AI_SPICE=0)."""
    if not enabled():
        return ''
    a = ARCHETYPES.get(arch or '')
    angles = ', '.join(ANGLES[x] for x in a['angles'][:4]) if a else 'vị, giá, thái độ, chuyện của mình'
    k = a['knobs'] if a else dict(sass=2, warmth=2)
    tail = ('khen thì khen có gai, chê xong thêm một ý thiện chí' if k['sass'] >= 2 and k['warmth'] >= 2 else
            'khen đểu được, gắt có lý' if k['sass'] >= 2 else 'nhẹ nhàng, kết bằng một ý thiện chí')
    return (f'THÁI ĐỘ: chê phải có lý do cụ thể (chi tiết, hậu quả, mong gì), cấm chê chung chung; nhìn ít nhất hai góc '
            f'(vd: {angles}; góc thêm là chuyện riêng của mình, không bịa lỗi hay sự việc mới); {tail}; '
            'chỉ xéo cái việc, không xéo con người. ')


def for_card(card: dict, purpose: str = 'chat') -> tuple[str | None, dict | None]:
    """(archetype, knobs) for a persona card, on this surface ((None, None) = no spice)."""
    if purpose == 'interview' or not isinstance(card, dict):
        return None, None
    sp = card.get('spice') if isinstance(card.get('spice'), dict) else None
    arch = sp.get('arch') if sp else None
    if not sp:
        from . import voices
        v = voices.for_card(card)
        addr = card.get('address') if isinstance(card.get('address'), dict) else {}
        arch = archetype_for(str(card.get('id') or card.get('name') or ''), v['id'], card.get('role', ''),
                             card.get('age') or 'adult', card.get('temperament'), card.get('career'), card.get('region'),
                             gender_of(card.get('name', ''), addr.get('self', '')))
    if arch not in ARCHETYPES:
        return None, None
    return arch, knobs_for(arch, str(card.get('id') or ''), purpose=purpose, mood=card.get('mood'),
                           temper=card.get('temperament'), age=card.get('age'))


def card_spice(npc_id: str, voice_id: str, role: str, age: str, temper: str | None, career: str | None,
               region: str | None, mood: str | None) -> dict | None:
    """The small `spice` field of a persona card (chat defaults)."""
    arch = archetype_for(npc_id, voice_id, role, age, temper, career, region)
    if not arch:
        return None
    k = knobs_for(arch, npc_id, purpose='chat', mood=mood, temper=temper, age=age)
    return dict(arch=arch, label=ARCHETYPES[arch]['label'], knobs=k)


# ------------------------------------------------------------------ scripted flavour (AI off)
def line(arch: str | None, bucket: str, seed: int, address: dict | None = None) -> str | None:
    """One scripted archetype line (None when there is none)."""
    rows = [x for x in ((ARCHETYPES.get(arch or '') or {}).get('lines') or {}).get(bucket) or [] if not kin_clash(x)]
    if not rows:
        return None
    return _fill(rows[seed % len(rows)], address)


def task_hint(arch: str | None, seed: int, address: dict | None, title: str = '') -> str | None:
    """Scripted hint while a task is open: an archetype opener + the functional core (ask, or open the task)."""
    opener = line(arch, 'task', seed, address)
    if not opener:
        return None
    core = ('Hỏi xong thì mở công việc ra coi dữ kiện cho kỹ.' if 'hỏi' in opener.lower() else
            'Hỏi xem {toi} cần gì trước, hoặc mở công việc ra coi dữ kiện cho kỹ.')
    return opener + ' ' + _fill(core, address)


def offer_hint(arch: str | None, seed: int, address: dict | None) -> str | None:
    """Scripted reaction to an offer made in chat (gift, discount, "done"): chat alone changes nothing."""
    opener = line(arch, 'offer', seed, address)
    if not opener:
        return None
    return opener + ' Muốn làm thật thì mở công việc, kiểm điều kiện rồi xác nhận thao tác; nói trong chat chưa làm tiền hay hàng thay đổi.'


def scripted(state: dict, career: str, npc: str, kind: str, title: str = '') -> str | None:
    """A scripted chat line with this NPC's attitude (engine.chat_reply, AI off or as the AI's canonical).

    kind: 'task' (a task is open: hint to ask or open it), 'offer' (the player offered something in
    chat: nothing changes until they act in the game), 'kind' (thanks / sorry). Vietnamese only:
    English saves and unspiced NPCs get None and keep the translated line."""
    if (state.get('settings') or {}).get('lang') == 'en':
        return None
    try:
        from . import personas
        p = personas.persona(state, career, npc)
    except Exception:  # never let flavour break the scripted reply
        return None
    arch = (p.get('spice') or {}).get('arch')
    if not arch:
        return None
    addr = p.get('address')
    c = (state.get('careers') or {}).get(career) or {}
    seed = _h('spice-scripted', npc, kind, len((c.get('chats') or {}).get(npc) or []), c.get('turn', 0))
    if kind == 'task':
        return task_hint(arch, seed, addr, title)
    if kind == 'offer':
        return offer_hint(arch, seed, addr)
    if kind == 'kind':
        return line(arch, 'kind', seed, addr)
    return None
