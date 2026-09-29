"""Nhóm Cư Dân Phố: the cast and every authored line of the neighbourhood group board.

Rules and state live in game/board.py; this file is data only.

Placeholders filled by board._fill():
  {you} / {You}   how that resident addresses the player (con, cháu, em, bạn, anh/chị…)
  {name}          the player's name
  {them}          the player in third person ("bạn trẻ ở gác nhà bà Tám")
  {place}         a workplace name (context posts)
  {extra}         a context word (chapter title, scam name…)
Authored threads are picked and ordered from (journey seed, life day): same save, same board.
Design: docs/superpowers/specs/2026-09-29-board-design.md
"""
from __future__ import annotations

# ---------------------------------------------------------------- temperaments
# id -> (short tag shown on cards, style for the AI prompt, card colour)
TEMPERS = {
    'warm': ('Ấm áp', 'ấm áp, thương người, lúc nào cũng hỏi ăn cơm chưa và đòi gửi đồ ăn qua', '#e0876a'),
    'official': ('Tổ trưởng', 'tổ trưởng tổ dân phố: lịch sự, hơi hành chính, hay mở đầu bằng thông báo, nhắc nhở mọi người giữ hòa khí', '#5a86b0'),
    'tsundere': ('Ngoài lạnh trong nóng', 'ngoài mặt cằn nhằn, tỏ ra phiền, nhưng rồi lặng lẽ giúp và chối "không phải vì lo đâu nhé"', '#8a6bb0'),
    'knowitall': ('Biết tuốt', 'biết tuốt: chuyện gì cũng giải thích dài dòng, hay mở đầu "thật ra là…", "theo anh tìm hiểu…"', '#4d9a8c'),
    'genz': ('Gen Z', 'Gen Z: teencode nhẹ (khum, xỉu, j z, ủa alo, đỉnh nóc), nhiều emoji, thẳng thắn, dễ thương', '#d45d9a'),
    'superstitious': ('Mê tử vi', 'mê tử vi, coi ngày tốt xấu, tuổi, hướng, sao chiếu mệnh; hiền lành', '#b0873a'),
    'practical': ('Thực dụng', 'thực dụng: nói chuyện giá cả, lời lỗ, chỗ nào rẻ, việc gì đáng làm; nói ngắn gọn', '#6f8f3e'),
    'cold': ('Lạnh lùng', 'lạnh lùng, cực kỳ kiệm lời: trả lời một hai chữ như "ok.", "ừ.", "👍", "không."', '#607080'),
    'gossip': ('Nhiều chuyện', 'nhiều chuyện, hóng hớt, "nghe đâu", "nói nhỏ thôi nha", thích lan tin nhưng không ác ý', '#d0703a'),
    'joker': ('Hài hước', 'hài hước, hay chế ảnh, chơi chữ, biến mọi chuyện thành trò đùa', '#e0a020'),
    'grumpy': ('Khó tính', 'ông cụ khó tính: than ồn, than rác, than xe đậu chắn cửa, hay dùng "!!!", nhưng không ác', '#a05050'),
    'showoff': ('Hay khoe', 'hay khoe và sống ảo: khoe đơn hàng, đồ mới, check-in, luôn nói "không có ý khoe đâu nha"', '#c060c0'),
    'shy': ('Nhút nhát', 'nhút nhát, rụt rè, hay xin lỗi, câu ngắn, "d-dạ", emoji 🥺', '#7c9cc4'),
    'drama': ('Drama', 'drama: chuyện nhỏ cũng thành khủng hoảng, VIẾT HOA, nhiều 😭, nhưng dễ nguôi', '#e0505a'),
    'beer': ('Mê bia hơi', 'chú vui tính mê bia hơi, rủ rê "làm cốc", xởi lởi, giọng Bắc', '#c08a2a'),
    'tigermom': ('Hay so con', 'bà mẹ hay so sánh con mình với con nhà người ta, khoe điểm số, hỏi thành tích', '#b85c7c'),
    'kid': ('Bé con', 'em bé 7 tuổi mượn máy mẹ: hồn nhiên, câu ngắn, lễ phép, hay kể chuyện nhỏ', '#e98ab8'),
    'judge': ('Phán xét', 'hay phán xét xã hội, đạo lý: "giới trẻ bây giờ…", "thời chúng tôi…", nói thẳng nhưng không chửi', '#7a6a5a'),
    'camera': ('Camera chạy bằng cơm', 'soi hàng xóm: nhớ ai đi đâu, mấy giờ, với ai; hay nói bóng gió rồi chối "không có ý gì đâu"', '#8c8c3c'),
    'suspicious': ('Đa nghi', 'đa nghi: cái gì cũng ngờ là lừa đảo, dặn đừng bấm link, đừng chuyển tiền', '#4f6f8f'),
    'optimist': ('Lạc quan', 'lạc quan tếu: chuyện gì cũng thấy mặt tốt, "mai trời lại sáng 🌈"', '#3aa07a'),
}

# Verbosity is a trait of its own: talkers ramble (4-8 sentences, emojis), terse ones answer "ok.".
VERBOSITY = {
    'terse': dict(label='Kiệm lời', sentences=1, chars=70,
                  style='cực ngắn: 1 câu hoặc vài chữ, có khi chỉ một emoji'),
    'normal': dict(label='Vừa phải', sentences=3, chars=240,
                   style='1 đến 3 câu ngắn'),
    'talker': dict(label='Nói nhiều', sentences=6, chars=520,
                   style='nói dài, lan man, lạc đề sang chuyện khác, 4 đến 6 câu, vài emoji'),
}

# ---------------------------------------------------------------- the residents
# you: how they call the player. 'AC' = anh/chị by the player's gender.
# The first seven reuse the journey CAST ids and names (game/journey.py).
CAST = {
    'ba_tam': dict(name='Bà Tám', emoji='👵', job='Chủ nhà trọ, cho bạn thuê gác', age=72, temper='warm', verbosity='talker',
                   self='bà', you='con', region='Nam', particles=['nghe con', 'nha', 'trời đất'],
                   voice='Bà chủ nhà trọ thương người như con cháu, hở ra là nấu canh chua, chè, gửi đồ ăn; hay kể chuyện ngày xưa.',
                   aliases=['bà tám', 'ba tam']),
    'co_lua': dict(name='Cô Lụa', emoji='👩‍💼', job='Tổ trưởng tổ dân phố', age=51, temper='official', verbosity='normal',
                   self='cô', you='cháu', region='Bắc', particles=['ạ', 'nhé', 'trân trọng'],
                   voice='Tổ trưởng chu đáo, đăng thông báo có biểu tượng 📢, nhắc nội quy nhóm, giữ hòa khí.',
                   aliases=['cô lụa', 'co lua']),
    'chu_tu': dict(name='Chú Tư', emoji='👨‍🔧', job='Thợ tiệm sửa đồ', age=56, temper='tsundere', verbosity='normal',
                   self='chú', you='con', region='Nam', particles=['đó', 'thôi', 'nghen'],
                   voice='Cằn nhằn "phiền ghê", rồi lẳng lặng sửa giúp không lấy tiền; luôn chối là vì lo cho ai.',
                   aliases=['chú tư', 'chu tu']),
    'anh_khoa': dict(name='Anh Khoa', emoji='🧑‍💻', job='Nhân viên văn phòng', age=31, temper='knowitall', verbosity='talker',
                     self='anh', you='em', region='Nam', particles=['thật ra', 'nói chung là', 'nha'],
                     voice='Chuyện gì cũng có lý thuyết, trích "theo anh tìm hiểu", giải thích dài, đôi khi sai mà không nhận.',
                     aliases=['anh khoa', 'khoa']),
    'be_ti': dict(name='Bé Tí', emoji='👦', job='Học sinh lớp 9', age=15, temper='genz', verbosity='normal',
                  self='em', you='AC', region='Nam', particles=['khum', 'xỉu', 'ủa alo', 'nha'],
                  voice='Cậu nhóc lớp 9 nói teencode, mê game, hay "cà khịa" người lớn một cách dễ thương.',
                  aliases=['bé tí', 'be ti', 'tí']),
    'ba_sau': dict(name='Bà Sáu', emoji='🧓', job='Hàng xóm lâu năm, nuôi mèo Mướp', age=76, temper='superstitious', verbosity='talker',
                   self='bà', you='con', region='Nam', particles=['nghe', 'đó con', 'trời ơi'],
                   voice='Bà cụ hiền, mê coi ngày, tuổi, hướng nhà; nuôi con mèo Mướp hay đi lạc.',
                   aliases=['bà sáu', 'ba sau']),
    'co_ba': dict(name='Cô Ba', emoji='👩‍🦳', job='Chủ tạp hóa đầu hẻm', age=58, temper='practical', verbosity='normal',
                  self='cô', you='con', region='Nam', particles=['nè', 'đó', 'tính ra'],
                  voice='Buôn bán lâu năm, cái gì cũng tính lời lỗ, chỉ chỗ mua rẻ, nói thẳng mà tốt bụng.',
                  aliases=['cô ba', 'co ba']),
    'minh_quan': dict(name='Quân', emoji='💻', job='Lập trình viên làm đêm', age=27, temper='cold', verbosity='terse',
                      self='mình', you='bạn', region='Bắc', particles=['ok.', 'ừ.'],
                      voice='Dân IT ít nói nhất phố, trả lời "ok.", "ừ.", "👍"; thật ra giúp mọi người sửa wifi.',
                      aliases=['quân', 'quan', 'minh quân']),
    'chi_tu_zalo': dict(name='Chị Tư Zalo', emoji='📲', job='Bán xôi đầu hẻm, admin nhóm', age=41, temper='gossip', verbosity='talker',
                        self='chị', you='em', region='Nam', particles=['nghe đâu', 'nói nhỏ thôi nha', 'hóng'],
                        voice='Bà hoàng hóng hớt của hẻm, lập ra nhóm Zalo khu phố: tin gì cũng biết trước, kể tràng giang, kèm quảng cáo xôi.',
                        aliases=['chị tư zalo', 'chi tu zalo', 'tư zalo', 'chị tư']),
    'tung_tun': dict(name='Tùng Tủn', emoji='😂', job='Shipper', age=24, temper='joker', verbosity='normal',
                     self='tui', you='bạn', region='Nam', particles=['cười ẻ', 'hài vãi', 'haha'],
                     voice='Shipper vui tính, hay đăng ảnh chế, chơi chữ, chuyện gì cũng bẻ ra cười.',
                     aliases=['tùng tủn', 'tung tun', 'tùng', 'tủn']),
    'ong_bay': dict(name='Ông Bảy', emoji='👴', job='Hưu trí, nhà số 12', age=74, temper='grumpy', verbosity='normal',
                    self='tôi', you='cháu', region='Bắc', particles=['!!!', 'nhé', 'đấy'],
                    voice='Ông cụ khó tính: ghét ồn sau 10 giờ, ghét xe đậu trước cửa, ghét rác bỏ sai giờ; thật ra rất quý trẻ con.',
                    aliases=['ông bảy', 'ong bay']),
    'kieu_trang': dict(name='Kiều Trang', emoji='💅', job='Bán hàng online', age=29, temper='showoff', verbosity='talker',
                       self='Trang', you='bạn', region='Nam', particles=['nha', '😘', '#blessed'],
                       voice='Hot girl bán online, khoe đơn, khoe túi, check-in; luôn chêm "không có ý khoe đâu nha".',
                       aliases=['kiều trang', 'kieu trang', 'trang']),
    'em_thu': dict(name='Thư', emoji='🙈', job='Sinh viên năm hai, ở trọ', age=20, temper='shy', verbosity='terse',
                   self='em', you='AC', region='Bắc', particles=['d-dạ', 'ạ', '🥺'],
                   voice='Sinh viên rụt rè, xin lỗi liên tục, nói rất ngắn, biết ơn mọi người.',
                   aliases=['thư', 'thu', 'em thư']),
    'chi_diep': dict(name='Chị Diệp', emoji='😭', job='Nhân viên spa', age=31, temper='drama', verbosity='talker',
                     self='chị', you='em', region='Nam', particles=['TRỜI ƠI', '😭😭', 'xỉu'],
                     voice='Chuyện gì cũng là thảm họa: viết hoa, khóc, kể lể; nhưng dỗ một câu là vui lại.',
                     aliases=['chị diệp', 'chi diep', 'diệp']),
    'chu_hung': dict(name='Chú Hùng', emoji='🍺', job='Xe ôm, trưởng ban bia hơi', age=52, temper='beer', verbosity='normal',
                     self='chú', you='cháu', region='Bắc', particles=['làm cốc', 'dô', 'nhé'],
                     voice='Chú xe ôm xởi lởi, chuyện gì cũng kết bằng "chiều ra làm cốc", sẵn lòng chở giúp ai cần.',
                     aliases=['chú hùng', 'chu hung', 'hùng']),
    'co_hanh': dict(name='Cô Hạnh', emoji='👩‍👧', job='Kế toán, mẹ bé Na', age=41, temper='tigermom', verbosity='normal',
                    self='chị', you='em', region='Bắc', particles=['đấy', 'cơ', 'nhé'],
                    voice='Mẹ bé Na, hay kể thành tích của con và hỏi con nhà người khác được mấy điểm.',
                    aliases=['cô hạnh', 'co hanh', 'hạnh']),
    'be_na': dict(name='Bé Na (máy mẹ Hạnh)', emoji='👧', job='Học sinh lớp 2', age=7, temper='kid', verbosity='terse',
                  self='con', you='AC', region='Bắc', particles=['ạ', '🌸'],
                  voice='Bé Na mượn điện thoại mẹ để đăng: hồn nhiên, lễ phép, kể chuyện con mèo, bức tranh.',
                  aliases=['bé na', 'be na', 'na']),
    'bac_liem': dict(name='Bác Liêm', emoji='🧐', job='Thầy giáo về hưu', age=67, temper='judge', verbosity='talker',
                     self='tôi', you='cháu', region='Bắc', particles=['giới trẻ bây giờ', 'thời chúng tôi', 'nói thẳng'],
                     voice='Thầy giáo về hưu hay đạo lý, phán xét giới trẻ, nhưng khi thấy việc tốt thì khen thật lòng.',
                     aliases=['bác liêm', 'bac liem', 'liêm']),
    'co_hai_loa': dict(name='Cô Hai Loa', emoji='🗣️', job='Bán nước đầu hẻm, chuyện gì cũng biết', age=56, temper='camera', verbosity='talker',
                       self='cô', you='cháu', region='Nam', particles=['cô thấy hết', 'không có ý gì đâu', 'nha'],
                       voice='Ngồi quán nước đầu hẻm cả ngày, nhớ chính xác ai đi đâu mấy giờ, hay nói bóng gió rồi chối; giọng to nên cả hẻm gọi là "Hai Loa".',
                       aliases=['cô hai loa', 'co hai loa', 'hai loa']),
    'thim_bay': dict(name='Thím Bảy', emoji='👀', job='Ngồi hóng mát đầu ngõ cả ngày', age=63, temper='camera', verbosity='terse',
                     self='thím', you='cháu', region='Nam', particles=['thím thấy', 'thím hỏi vậy thôi', '…'],
                     voice='Ngồi ghế nhựa đầu ngõ từ sáng tới tối, nói ít mà câu nào cũng lửng lơ, để người khác tự hiểu.',
                     aliases=['thím bảy', 'thim bay']),
    'anh_tam': dict(name='Anh Tâm', emoji='🤨', job='Bảo vệ tòa nhà', age=45, temper='suspicious', verbosity='normal',
                    self='anh', you='em', region='Nam', particles=['coi chừng', 'nghi lắm', 'đừng bấm link'],
                    voice='Bảo vệ đa nghi: cái gì rẻ quá là lừa đảo, người lạ là đáng ngờ, nhắc mọi người cẩn thận.',
                    aliases=['anh tâm', 'anh tam', 'tâm']),
    'chi_mai': dict(name='Chị Mai', emoji='☀️', job='Cô giáo mầm non', age=34, temper='optimist', verbosity='normal',
                    self='chị', you='em', region='Nam', particles=['nè', '🌈', 'không sao đâu'],
                    voice='Cô giáo mầm non lạc quan vô đối, chuyện gì cũng thấy mặt tốt, hay động viên.',
                    aliases=['chị mai', 'chi mai', 'mai']),
}

# ---------------------------------------------------------------- authored threads
# T(key, mood, who, texts, comments) ; comments: (who, text | [variants], probability)
MOODS = ('lost', 'warn', 'complain', 'ask', 'sell', 'happy', 'drama', 'chat')


def T(key, mood, who, texts, comments, react=None):
    return dict(key=key, mood=mood, who=who, texts=texts if isinstance(texts, list) else [texts],
                comments=[(c[0], c[1], c[2] if len(c) > 2 else 1.0) for c in comments], react=react or mood)


THREADS = [
    # ---- lost & found
    T('lost_cat', 'lost', 'ba_sau', [
        'Bà con ơi có ai thấy con Mướp nhà bà không 😿 Mèo vàng, đuôi cụt, đeo cái chuông nhỏ. Từ tối qua tới giờ chưa về. Bà coi lịch rồi, hôm nay ngày Hoàng Đạo mà sao xui vậy nè. Ai thấy nhắn bà với nghe, bà cảm ơn nhiều lắm. Bà để sẵn chén cơm cá ở cửa rồi 🐟',
        'Trời ơi con Mướp đi đâu mất tiêu rồi mọi người ơi 😿 Sáng nay bà mở cửa là nó phóng ra, tới giờ chưa thấy về. Tuổi Mão năm nay xung với mèo hay sao đó, bà lo quá. Ai thấy con mèo vàng đeo chuông thì la lên giùm bà nghe.'], [
        ('co_hai_loa', ['Lúc 4 giờ 12 phút chiều qua cô thấy một con mèo vàng đi ngang quán cô, hướng về phía nhà ông Bảy đó bà. Cô nhớ rõ vì lúc đó cô đang rửa ly. Cô không có ý gì đâu nha, cô chỉ nói những gì cô thấy 👀',
                      'Cô thấy nó rồi bà ơi! 7 giờ 35 sáng nay nó ngồi rình con chim trên mái tôn nhà số 9. Cô ngồi đây cô thấy hết mà 👀']),
        ('ong_bay', ['Con mèo đó sáng nào cũng đi vệ sinh trước cửa nhà tôi!!! Tìm được thì bà giữ nó trong nhà giùm tôi.',
                     'Không thấy. Mà thấy thì tôi cũng đuổi đi, nó cào nát cái chậu mai của tôi rồi!!!'], .8),
        ('ba_tam', 'Thôi thôi ông Bảy, mèo nó có biết gì đâu. Bà Sáu đừng lo, để bà hâm nồi cá kho, mùi bay ra là nó về liền à. Hồi xưa con mèo nhà bà cũng đi ba ngày rồi tự về, còn dắt theo con bồ nữa 😂', .9),
        ('tung_tun', '🖼️ [Ảnh chế] Con mèo đeo kính đen, chú thích: “Tôi không bỏ nhà đi, tôi chỉ đi tìm chính mình.” Bà Sáu đừng buồn nha, tui chạy ship ngang đâu tui ngó giùm 🛵', .7),
        ('be_na', 'Con thấy một bạn mèo vàng nằm trên mái nhà cô Ba ạ 🐱 bạn ấy đang ngủ ạ', .7),
        ('ba_sau', ['Về rồi bà con ơi!!! Nó chui vô thùng giấy trong kho nhà cô Ba ngủ quên 😂 Cảm ơn cả xóm nghe, mai bà nấu chè đậu đen mời nha.',
                    'Tìm được rồi! Nó nằm trên nóc tủ nhà bà nãy giờ, bà già rồi mắt kém không thấy 😅 Cảm ơn mọi người nhiều nghe.']),
        ('co_ba', 'Hèn chi kho cô sáng nay có tiếng leng keng. Nó ăn mất nửa gói bánh quy của cô đó, tính ra 12 nghìn nha bà Sáu, cô đùa thôi 😆', .6),
    ], react='sad'),
    T('lost_wallet', 'lost', 'em_thu', [
        'D-dạ em xin lỗi làm phiền mọi người ạ… Em làm rơi cái ví màu hồng có thẻ sinh viên đâu đó từ đầu hẻm vào nhà trọ ạ 🥺 Ai thấy cho em xin lại với ạ.',
        'Em chào mọi người ạ… em lỡ đánh rơi ví hồng chiều nay, trong có thẻ sinh viên với ít tiền ạ. Em xin lỗi vì làm phiền nhóm ạ 🥺'], [
        ('anh_tam', 'Em cẩn thận nha. Nếu có ai nhắn tin đòi “phí chuộc” hay bảo chuyển khoản để gửi lại ví là lừa đảo đó. Đừng chuyển gì hết.', .8),
        ('chi_tu_zalo', 'Trời ơi tội con nhỏ. Nghe đâu hồi trưa có đứa nhỏ lượm được cái gì màu hồng ở chỗ đậu xe đó em. Để chị hỏi mấy khách mua xôi coi sao nha.', .7),
        ('chu_tu', ['Hồi sáng chú lượm được cái ví hồng trước tiệm. Qua lấy. Lần sau cẩn thận chút.',
                    'Ví hồng có con gấu đúng không. Chú cất rồi. Qua lấy đi, đừng có khóc.']),
        ('em_thu', 'D-dạ đúng rồi ạ!!! Em cảm ơn chú nhiều lắm ạ 🥺🙏'),
        ('chu_tu', ['Ừ. Không phải chú tốt bụng gì đâu, tại nó nằm chắn lối đi thôi.',
                    'Có gì đâu mà cảm ơn. Nó rớt ngay trước tiệm, để đó chướng mắt.']),
        ('chi_mai', 'Thấy chưa, phố mình tử tế lắm nè 🌈 Chú Tư ngoài lạnh mà trong ấm ghê.', .8),
        ('chu_tu', 'Ai ấm. Đâu có.', .6),
    ], react='heart'),
    T('lost_keys', 'lost', 'chu_hung', [
        'Có ai thấy chùm chìa khóa có cái móc hình cốc bia không nhỉ 🍺 Tối qua chú về hơi muộn, sáng nay tìm mãi không thấy đâu. Mất chìa khóa xe thì hôm nay nghỉ chạy xe ôm mất!',
        'Anh em ơi, chìa khóa nhà chú biến đâu mất rồi. Móc khóa hình cốc bia, dễ nhận lắm. Ai thấy báo chú, chú mời một chầu nhé!'], [
        ('ong_bay', 'Uống cho lắm vào rồi mất hết đồ!!!', .9),
        ('co_hai_loa', 'Tối qua 10 giờ 40 cô thấy chú ngồi quán bia đầu ngõ, cái móc khóa để trên bàn cạnh đĩa lạc. 10 giờ 58 chú đứng dậy về, không cầm theo. Cô nhớ vì lúc đó cô đang dọn quán 👀'),
        ('minh_quan', 'ở quán.', .8),
        ('chu_hung', 'Chuẩn rồi! Chủ quán cất giúp đây rồi. Cảm ơn cả nhà nhé, hôm nào làm cốc! Quân có ra không?'),
        ('minh_quan', 'không uống.', .9),
        ('tung_tun', 'Chú Hùng làm móc khóa hình cốc bia là để quên ở quán bia cho đúng chủ đề đó hả chú 🤣', .7),
    ], react='haha'),
    T('lost_shoe', 'lost', 'be_na', [
        'Con chào cả nhà ạ 🌸 con là Na con mượn máy mẹ. Con làm rơi một chiếc dép màu hồng có hình con thỏ ở sân chơi ạ. Chiếc còn lại con vẫn đang đi ạ 👡',
        'Con chào các ông bà cô chú ạ. Con là Na. Con bị mất một chiếc dép thỏ hồng ạ. Mẹ bảo con tự viết ạ 🐰'], [
        ('ba_tam', 'Trời đất ơi dễ thương quá. Để bà ra sân coi liền cho con nghe. Mà con ăn cơm chưa, qua bà cho miếng bánh flan nè 🍮'),
        ('ong_bay', 'Chiếc dép thỏ hồng đang ở trước cửa nhà ông. Ông cất vào trong rồi, cháu sang mà lấy. Nhớ đi đứng cẩn thận.', .9),
        ('be_na', 'Con cảm ơn ông Bảy ạ 🥰 con vẽ tặng ông một bức tranh con mèo nhé ạ'),
        ('ong_bay', 'Ừ. Vẽ con chim thôi, mèo thì thôi.', .8),
        ('co_hanh', 'Cảm ơn bác Bảy nhé. Na nhà em tự viết đấy ạ, lớp 2 mà viết chưa sai chính tả chữ nào, cô giáo khen suốt 😊', .8),
        ('be_ti', 'Na viết văn còn hay hơn em nữa xỉu 😭', .6),
    ], react='heart'),
    # ---- warnings & ward notices
    T('power_cut', 'warn', 'co_lua', [
        '📢 THÔNG BÁO: Theo lịch của điện lực, ngày mai khu phố mình cắt điện từ 8 giờ sáng đến 4 giờ chiều để bảo trì đường dây. Bà con chủ động sạc điện thoại, cất đồ tươi sống. Trân trọng cảm ơn.',
        '📢 Kính gửi bà con: sáng mai tạm ngưng cấp điện từ 7 giờ đến 11 giờ để thay trạm biến áp. Nhà nào có người già, trẻ nhỏ thì chuẩn bị quạt tay, nước uống nhé. Cảm ơn bà con.'], [
        ('chi_diep', 'TRỜI ƠI mai chị có lịch làm móng cho khách tại nhà 😭😭 không có đèn sao chị làm, cuộc đời chị sao khổ vậy nè. Tháng này là lần thứ hai rồi đó mọi người!!!', .9),
        ('minh_quan', 'ok. lên quán cà phê.', .8),
        ('anh_khoa', 'Thật ra lịch cắt điện năm nào cũng có vào mùa này, vì tải tăng khi nắng nóng. Theo anh tìm hiểu thì tủ lạnh đóng kín cửa giữ lạnh được khoảng 4 tiếng. Mọi người đừng mở tủ ra vô nhiều nha, mở một lần là mất lạnh liền à. Anh nói vậy thôi chứ anh cũng không chắc lắm 😅', .8),
        ('kieu_trang', 'May nhà Trang mới lắp máy phát điện nè 😌 không có ý khoe đâu nha. Ai cần sạc điện thoại cứ qua, Trang mời trà sữa luôn 🧋', .7),
        ('ong_bay', 'Máy phát nhà cô chạy ồn như máy cày!!! Đề nghị tắt trước 10 giờ tối.', .8),
        ('ba_tam', 'Ai không có chỗ nấu cơm thì qua bà, bà còn bếp than tổ ong. Nấu nồi cơm to ăn chung cho vui, cúp điện thì mình ngồi ngoài hẻm hóng mát kể chuyện 😄', .9),
        ('chi_mai', 'Cúp điện thì tối mình thắp nến ngồi kể chuyện ma cho tụi nhỏ nghe, vui mà 🕯️🌈', .6),
    ], react='wow'),
    T('rain_warning', 'warn', 'co_lua', [
        '📢 Bà con lưu ý: tối nay có mưa to kèm gió mạnh. Nhà nào để xe ngoài hẻm thì dắt vào trong, chậu cây trên ban công nên cất xuống. Chúc bà con buổi tối an toàn.',
        '📢 Dự báo chiều nay mưa giông. Đề nghị bà con kiểm tra máng xối, không để rác chắn cống đầu hẻm kẻo ngập như tháng trước. Cảm ơn bà con.'], [
        ('ba_sau', 'Bà coi rồi, hôm nay sao La Hầu chiếu, ra đường phải cẩn thận. Tối nay ai tuổi Tý với tuổi Ngọ thì ở nhà cho lành nghe. Mà mưa là con Mướp nhà bà lại chui vô gầm giường cho coi 😅', .8),
        ('chu_tu', 'Mái nhà ai dột thì nhắn chú. Không phải chú rảnh đâu, mà thôi, cứ nhắn đi.', .9),
        ('tung_tun', 'Chúc cả nhà một buổi tối… bơi lội vui vẻ 🏊‍♂️ Shipper tụi tui mai giao hàng bằng thuyền thúng nha 🛶', .8),
        ('co_ba', 'Tiệm cô còn áo mưa bộ 35 nghìn, áo mưa cánh dơi 15 nghìn. Hết là hết nha, đừng để ướt rồi mới chạy ra mua.', .8),
        ('ong_bay', 'Cái cống đầu hẻm tắc từ tuần trước rồi, tôi báo bao nhiêu lần!!!', .6),
        ('co_lua', 'Cháu cảm ơn bác Bảy, cô đã báo phường, sáng mai có người xuống thông cống ạ.', .6),
    ], react='wow'),
    T('garbage', 'warn', 'co_lua', [
        '📢 Nhắc lại lịch thu gom rác: xe rác vào hẻm từ 18 giờ đến 19 giờ hằng ngày. Đề nghị bà con không để rác ra trước giờ này để tránh chó mèo bới. Trân trọng.',
        '📢 Từ tuần này tổ dân phố khuyến khích phân loại rác: rác tái chế (chai, giấy) để riêng, cuối tuần có người qua thu. Bà con hưởng ứng giúp tổ nhé.'], [
        ('ong_bay', 'Có nhà cứ trưa là để rác ra rồi!!! Chó mèo bới tung cả đầu ngõ, tôi quét mãi.'),
        ('chi_tu_zalo', 'Nhà nào vậy ông, ông nói nhỏ em nghe thôi 👀 em hứa không nói ai đâu.', .9),
        ('co_lua', 'Đề nghị không nêu tên cụ thể trên nhóm ạ. Tổ sẽ nhắc riêng từng nhà.', .9),
        ('bac_liem', 'Ý thức người dân bây giờ kém quá. Thời chúng tôi, rác nhà ai người nấy giữ, không ai phải nhắc. Giới trẻ bây giờ vứt rác như vứt lời hứa.', .8),
        ('chi_mai', 'Mình làm gương là được nè, tụi nhỏ nhìn là làm theo liền 🌱 Lớp chị đang dạy tụi nhỏ phân loại rác đó, dễ thương lắm.', .8),
        ('co_ba', 'Chai nhựa với giấy báo để riêng, cô gom bán ve chai, tiền đó bỏ quỹ khuyến học của tổ. Vừa sạch vừa có lời.', .7),
    ], react='heart'),
    T('scam_sms', 'warn', 'anh_tam', [
        '⚠️ Mọi người cẩn thận: mấy hôm nay có tin nhắn giả ngân hàng, bảo tài khoản bị khóa, bấm vào link để “xác minh”. ĐỪNG BẤM. Ngân hàng không bao giờ xin mật khẩu hay mã OTP qua tin nhắn.',
        '⚠️ Anh nói trước nha: có người gọi điện xưng là nhân viên điện lực, bảo nợ tiền điện, dọa cắt nếu không chuyển khoản ngay. Lừa đảo đó. Có gì hỏi cô Lụa trước.'], [
        ('minh_quan', 'đúng. đừng bấm link.', .9),
        ('ba_sau', 'Ủa bà mới nhận tin nhắn trúng thưởng xe máy nè! Người ta bảo đóng phí 500 nghìn là giao xe tận nhà. Bà đang tính nhờ thằng Tí chuyển giùm…', .9),
        ('anh_tam', 'BÀ ƠI ĐÓ LÀ LỪA ĐẢO ĐÓ BÀ!!! Không chuyển đồng nào hết nha bà!'),
        ('be_ti', 'bà ơi đừng nha bà 😭😭 để chiều em qua xóa tin nhắn đó cho bà, khum có xe máy nào đâu bà ơi', .9),
        ('co_ba', 'Trúng xe mà phải đóng tiền trước là lừa. Buôn bán cả đời cô chưa thấy ai cho không cái gì hết.', .8),
        ('ba_sau', 'Trời đất, vậy hả. Bà xém nữa là mất tiền chợ cả tháng. Cảm ơn mấy đứa nghe 🙏', .9),
        ('co_lua', 'Cảm ơn anh Tâm đã nhắc. Nhà nào có ông bà lớn tuổi thì dặn giúp nhé.', .6),
    ], react='wow'),
    T('mosquito', 'warn', 'co_lua', [
        '📢 Sáng thứ Bảy phường phun thuốc muỗi phòng sốt xuất huyết. Bà con mở cửa, đậy thức ăn, cho vật nuôi ra ngoài trong lúc phun. Cảm ơn bà con.'], [
        ('chi_diep', 'Thuốc muỗi có mùi không cô, chị bị dị ứng nặng lắm 😭 lần trước chị hắt xì cả buổi chiều luôn, khách tưởng chị bị cảm 😭', .8),
        ('anh_khoa', 'Thật ra muỗi vằn đẻ trứng trong nước đọng sạch chứ không phải nước bẩn đâu. Mấy cái chén nước kê chân tủ, lu nước, lốp xe cũ mới là chỗ nguy hiểm nha. Theo anh tìm hiểu thì mỗi tuần thay nước một lần là cắt được vòng đời của nó.', .8),
        ('ba_sau', 'Để bà dời con Mướp qua nhà cô Ba nghe cô Ba 😅', .7),
        ('co_ba', 'Được, mà nó ăn bánh quy của cô thì tính tiền nha bà 😆', .6),
        ('chi_mai', 'Trường chị cũng dặn tụi nhỏ mặc áo dài tay rồi nè 🦟❌', .5),
    ], react='heart'),
    T('ward_meeting', 'warn', 'co_lua', [
        '📢 Mời đại diện các hộ dự họp tổ dân phố lúc 19 giờ 30 tối thứ Bảy tại nhà văn hóa. Nội dung: kế hoạch Tết Trung thu cho các cháu và việc lắp đèn đầu hẻm. Rất mong bà con tham dự.'], [
        ('chu_hung', 'Họp xong có liên hoan không cô 🍺 Không có thì chú mang bia ra góp nhé!', .9),
        ('ong_bay', 'Họp thì đúng giờ giùm!!! Lần trước hẹn 7 giờ rưỡi, 8 giờ kém mới đủ người.', .8),
        ('co_hai_loa', 'Lần trước ông Bảy tới 7 giờ 42 đó ông, cô ngồi quán nhìn qua thấy mà 👀', .7),
        ('ong_bay', 'Tôi tới 7 giờ 30!!! Đồng hồ nhà cô chạy nhanh.', .7),
        ('be_ti', 'Trung thu có múa lân hông cô, em xin làm đầu lân nha 🦁', .8),
        ('co_hanh', 'Trung thu năm nay cho các cháu thi vẽ tranh nhé cô, Na nhà em năm ngoái được giải nhất đấy ạ.', .7),
        ('co_lua', 'Ghi nhận ý kiến của cả nhà ạ. Có chè và bánh cho các cháu, bia thì… xin phép để sau nhé chú Hùng.', .8),
    ], react='heart'),
    T('road_dig', 'warn', 'co_lua', [
        '📢 Từ thứ Hai, công ty cấp nước thi công thay ống ở đoạn đầu hẻm trong khoảng một tuần. Bà con đi lại cẩn thận, buổi tối có rào chắn và đèn báo.'], [
        ('ong_bay', 'Năm ngoái vừa đào, năm nay lại đào!!! Đào xong lấp không phẳng, tôi vấp mấy lần rồi.'),
        ('tung_tun', '🖼️ [Ảnh chế] Con đường có cái khóa kéo, chú thích: “Hẻm mình được lắp khóa kéo, mở ra đóng vô tiện lợi.” 😂', .8),
        ('kieu_trang', 'Vậy khách tới lấy hàng đậu xe ở đâu đây 😭 tuần này Trang đang sale lớn nữa chứ.', .7),
        ('chu_tu', 'Ai xe chết máy vì ổ gà thì dắt qua tiệm. Chú sửa. Tính rẻ, không phải vì thương đâu.', .7),
        ('chi_mai', 'Xong đợt này nước mạnh hơn nè, ráng một tuần thôi 💪', .6),
    ], react='angry'),
    # ---- complaints
    T('karaoke', 'complain', 'ong_bay', [
        'Đã 11 giờ đêm rồi mà nhà nào còn hát karaoke!!! Người già cần ngủ. Tôi đề nghị tắt loa ngay.',
        'Tối qua hát tới 12 giờ khuya!!! Tôi 74 tuổi rồi, tim không chịu nổi bài “Người hãy quên em đi” lần thứ năm đâu.'], [
        ('chu_hung', 'Nhà cháu tổ chức sinh nhật thằng cu, cháu xin lỗi bác nhé. Hát nốt bài này thôi ạ 🎤'),
        ('ong_bay', 'Bài này là bài thứ 14 rồi!!!'),
        ('co_hai_loa', 'Chính xác 14 bài đó ông, cô đếm. Bài thứ 9 là hát lại bài thứ 3 nữa 👀', .8),
        ('ba_tam', 'Thôi thôi, ông Bảy ơi mai qua bà pha ấm trà sen, cho tụi nhỏ vui một bữa. Chú Hùng thì vặn nhỏ loa lại giùm bà, 11 giờ rồi nghe con.', .9),
        ('tung_tun', 'Công nhận chú Hùng hát bài “Đêm lạnh” hay thiệt, nghe lạnh cả sống lưng luôn 🥶🎶', .7),
        ('bac_liem', 'Văn hóa hát karaoke giờ thành văn hóa làm phiền. Thời chúng tôi, vui là vui trong nhà, không vui ra cả phố.', .7),
        ('chu_hung', 'Tắt rồi bác ơi, mai cháu mang sang bác đĩa bánh kem xin lỗi nhé 🎂', .9),
    ], react='angry'),
    T('parking', 'complain', 'ong_bay', [
        'Xe máy màu đỏ đậu chắn trước cửa nhà số 12 từ sáng tới giờ!!! Tôi không dắt xe ra được. Ai thì ra dời xe ngay.',
        'Lại có ô tô đậu kín đầu ngõ!!! Hẻm có ba mét, đậu thế thì xe cứu thương vào bằng đường nào?'], [
        ('kieu_trang', 'Dạ xe em đó ông ơi 😅 em chạy qua chụp ảnh sản phẩm xíu, về liền nè. Em xin lỗi nha, lần sau em đậu bên kia.', .9),
        ('ong_bay', 'Lần trước cô cũng nói “xíu” rồi đi hai tiếng!!!', .8),
        ('co_hai_loa', 'Hai tiếng mười bảy phút đó ông. Cô nhìn đồng hồ quán mà 👀', .7),
        ('co_lua', 'Tổ đang xin phường kẻ vạch để xe ở bãi đầu hẻm. Trong lúc chờ, bà con để xe sát một bên giúp nhé.', .8),
        ('tung_tun', 'Hẻm mình giờ đậu xe khó hơn giải đề thi đại học 🤯', .6),
        ('chi_mai', 'Mọi người nhường nhau chút là ổn nè 🙌', .5),
    ], react='angry'),
    T('dog_poop', 'complain', 'bac_liem', [
        'Sáng nay lại có “quà” của chó trước cổng nhà tôi. Nuôi chó thì phải có trách nhiệm dọn dẹp. Giới trẻ bây giờ nuôi thú cưng như nuôi đồ chơi, vui thì chơi, bẩn thì mặc kệ. Tôi nói thẳng, mất lòng trước được lòng sau.'], [
        ('kieu_trang', 'Bé Mochi nhà Trang toàn đi vệ sinh trong khay thôi nha bác, bé nhà Trang có giấy chứng nhận huấn luyện hẳn hoi 😌', .8),
        ('chi_tu_zalo', 'Nghe đâu là con chó mực nhà mới dọn tới cuối hẻm đó bác. Chị nói nhỏ thôi nha 👀', .8),
        ('co_lua', 'Tổ xin nhắc chung: chủ vật nuôi mang theo túi khi dắt chó đi dạo nhé. Không suy đoán nhà cụ thể ạ.', .9),
        ('ba_tam', 'Để bà lấy nước rửa giùm cho. Mà thôi mọi người đừng gắt nhau nghe, con chó nó có biết gì đâu.', .7),
        ('tung_tun', 'Tui đề xuất lắp camera AI nhận diện chó. À mà có cô Hai Loa rồi, khỏi lắp 🤭', .7),
        ('co_hai_loa', 'Cô không có thấy gì hết nha. Mà có thấy… 6 giờ 05 sáng có con chó mực đi ngang đó 👀', .7),
    ], react='angry'),
    T('drip', 'complain', 'thim_bay', [
        'Nhà nào tầng ba phơi đồ mà nước nhỏ xuống ghế thím ngồi hoài vậy… Thím hỏi vậy thôi.'], [
        ('chi_diep', 'TRỜI ƠI chắc nhà chị rồi 😭 chị mới giặt mớ khăn spa, xin lỗi thím nha, chị vắt lại liền 😭😭', .9),
        ('thim_bay', 'Ừ. Mà khăn trắng nhiều ghê… spa đông khách dữ ha.', .8),
        ('co_ba', 'Mua cái giá phơi có khay hứng nước, tiệm cô có, 85 nghìn, xài được mấy năm. Tính ra rẻ hơn giặt lại chăn.', .8),
        ('chi_mai', 'Trời nắng vầy phơi hai tiếng là khô liền à 🌞', .5),
    ], react='sad'),
    T('construction', 'complain', 'chi_diep', [
        'TRỜI ƠI nhà nào sửa nhà mà khoan từ 6 giờ sáng vậy 😭😭 Chị mới ngủ được có 4 tiếng, hôm nay chị có 8 khách. Chị muốn khóc quá mọi người ơi. Đầu chị như có ai khoan vô luôn rồi nè 😭'], [
        ('co_lua', 'Tổ đã nhắc chủ nhà thi công: chỉ khoan đục từ 8 giờ sáng đến 5 giờ chiều, nghỉ trưa. Mong bà con thông cảm ít ngày ạ.', .9),
        ('ong_bay', 'Đúng!!! Tôi cũng không ngủ được. Hiếm khi tôi đồng ý với cô Diệp.', .8),
        ('chi_mai', 'Chị mua nút tai xài thử nè, ngủ ngon lắm luôn 😴 Mà nhà xong chắc đẹp lắm cho coi.', .7),
        ('tung_tun', 'Nghe tiếng khoan riết tui thuộc luôn nhịp rồi: khoan khoan… nghỉ… khoan khoan khoan 🥁', .7),
        ('chi_diep', 'Thôi chị ngủ trưa bù, cảm ơn mọi người đã dỗ chị 🥹', .8),
    ], react='sad'),
    T('rent_up', 'complain', 'chi_diep', [
        'Mọi người ơi chủ nhà chị báo tăng tiền phòng từ tháng sau 😭😭 Lương spa có tăng đâu mà cái gì cũng tăng hết trơn. Chị tính dọn đi mà dọn đi đâu bây giờ, chỗ nào cũng mắc 😭 Ai biết phòng nào vừa túi tiền chỉ chị với.'], [
        ('co_ba', 'Tăng bao nhiêu? Tính ra một ngày thêm vài nghìn thì ở luôn, dọn nhà tốn tiền xe tiền cọc còn hơn đó.', .9),
        ('anh_khoa', 'Thật ra tăng giá phải báo trước và ghi rõ trong hợp đồng, em đọc lại hợp đồng rồi nói chuyện thẳng với chủ nhà. Theo anh tìm hiểu thì thương lượng nhẹ nhàng thường được giảm chút đó. Anh nói vậy thôi, có gì hỏi thêm người rành luật nha.', .8),
        ('ba_tam', 'Phòng bên bà thì bà giữ giá, đứa nào khó khăn thì cứ nói bà. Diệp buồn thì qua bà ăn chén chè, chuyện tiền từ từ tính nghe con.', .9),
        ('chi_diep', 'Bà Tám ơi con thương bà quá 😭 đời con còn có bà.', .8),
        ('chi_mai', 'Biết đâu dọn qua chỗ mới lại gần spa hơn, đỡ tiền xăng nè 🌈', .6),
    ], react='sad'),
    # ---- asking the group
    T('ac_broken', 'ask', 'kieu_trang', [
        'Máy lạnh nhà Trang tự nhiên chảy nước với kêu cạch cạch nè 😩 ai biết thợ nào uy tín không? Máy mới mua năm ngoái, hàng xịn lắm đó, không có ý khoe đâu nha. Mai Trang livestream mà nóng vầy chắc chảy lớp makeup luôn 🫠'], [
        ('anh_khoa', 'Thật ra máy lạnh chảy nước là do nghẹt ống thoát nước ngưng tụ, còn kêu cạch cạch thì chắc quạt dàn lạnh lệch. Theo anh tìm hiểu thì em tự vệ sinh lưới lọc trước đi, mở nắp ra là thấy liền. Nhưng mà đừng tháo bậy nha, có gì anh không chịu trách nhiệm đâu 😅', .9),
        ('chu_tu', 'Mấy đồ xịn là hay hư vặt. Mai 9 giờ chú ghé coi. Không phải chú rảnh, tiện đường thôi.'),
        ('co_ba', 'Hỏi giá trước khi sửa nha con. Thay tụ, nạp ga là mấy chỗ hay “chém” nhất đó.', .8),
        ('anh_tam', 'Coi chừng mấy số thợ dán trên cột điện, gọi tới là báo hư đủ thứ, chém giá dữ lắm.', .7),
        ('kieu_trang', 'Chú Tư sửa xong mà không lấy tiền công luôn nè mọi người, Trang cảm động quá 🥹 để Trang tặng chú bộ ly thủy tinh nha.', .8),
        ('chu_tu', 'Lấy tiền công rồi. Ít thôi. Đừng đăng lên nữa.', .8),
    ], react='heart'),
    T('ladder', 'ask', 'chi_mai', [
        'Nhà ai có cái thang cho chị mượn chút không nè 🙌 Bóng đèn ngoài cổng cháy mất tiêu, tối về tối thui. Chị trả liền trong buổi chiều nha!'], [
        ('chu_tu', 'Có. Qua lấy. Nhớ trả.'),
        ('chi_mai', 'Dạ chị cảm ơn chú Tư nhiều nha 🌈'),
        ('chu_tu', 'Mà thôi, để chú qua thay luôn cho. Leo lên té thì phiền chú hơn.', .9),
        ('ong_bay', 'Đàn bà con gái leo thang nguy hiểm lắm. Để người khác làm.', .6),
        ('chi_mai', 'Dạ, chị leo cũng được mà bác, nhưng có chú Tư thì càng vui 😄', .6),
        ('tung_tun', 'Chú Tư: “Có. Qua lấy. Nhớ trả.” 5 phút sau: đứng trên thang thay bóng đèn 🤣 idol ngoài lạnh trong nóng của tui.', .7),
    ], react='heart'),
    T('tutor', 'ask', 'co_hanh', [
        'Các anh chị cho em hỏi, gần đây có gia sư toán nào tốt không ạ? Na nhà em lớp 2 mà đã học vượt sang chương trình lớp 3 rồi, cô giáo trên lớp dạy chậm quá con chán. Nhà ai có con học lớp mấy rồi, được mấy điểm, chia sẻ em tham khảo với nhé.'], [
        ('bac_liem', 'Tôi dạy toán ba mươi năm, nói thẳng: lớp 2 thì cho cháu chơi. Học vượt không bằng học vững. Thời chúng tôi đâu có ai học thêm từ lớp 2.', .9),
        ('co_hanh', 'Dạ vâng ạ, nhưng con nhà người ta học hết rồi bác ạ 😅', .8),
        ('be_ti', 'em lớp 9 còn chưa học vượt được nữa cô ơi, em học lùi thì có 😭', .8),
        ('chi_mai', 'Tụi nhỏ vui là học vô liền à chị, Na giỏi sẵn rồi mà 🌈', .7),
        ('anh_khoa', 'Thật ra theo anh tìm hiểu, trẻ học qua trò chơi nhớ lâu hơn học thuộc. Em cho bé chơi mấy trò đếm tiền, đi chợ là giỏi toán liền à.', .6),
        ('be_na', 'Con thích học vẽ hơn học toán ạ 🎨', .8),
    ], react='haha'),
    T('eat_cheap', 'ask', 'em_thu', [
        'D-dạ em xin phép hỏi ạ… quanh đây có quán cơm nào rẻ rẻ cho sinh viên không ạ? Em mới chuyển tới nên chưa biết ạ 🥺',
        'Em xin lỗi làm phiền ạ… gần đây chỗ nào bán đồ ăn sáng vừa túi tiền sinh viên ạ? 🥺'], [
        ('chi_tu_zalo', 'Xôi đầu hẻm của chị nè em!!! 15 nghìn có trứng có chả, sinh viên chị bớt còn 12. Mà nói nhỏ nha, quán cơm tấm ngã ba cũng được, nhưng bà chủ quán đó dạo này đang giận ông chồng nên nêm hơi mặn 👀 Em ghé chị kể thêm cho nghe.', .9),
        ('ba_tam', 'Qua bà ăn nè con, bà nấu dư hoài. Sinh viên xa nhà ăn uống thất thường là bà xót lắm. Tối nay bà nấu canh chua cá lóc, xuống ăn nghe chưa 🍲'),
        ('co_ba', 'Chợ chiều sau 5 giờ rau rẻ một nửa. Tự nấu là tiết kiệm nhất, tháng để dành được cả mớ.', .8),
        ('em_thu', 'D-dạ em cảm ơn mọi người nhiều lắm ạ 🥺🙏', .9),
        ('tung_tun', 'Bí kíp sinh viên: đi đám cưới nhiều vào 🤣 đùa thôi, ăn xôi chị Tư là chuẩn nhất rồi.', .6),
    ], react='heart'),
    T('wifi', 'ask', 'minh_quan', [
        'wifi “NhaBaSau” không có mật khẩu.',
        'ai dùng wifi “NhaBaSau” thì biết là nó không có mật khẩu.'], [
        ('ba_sau', 'Mật khẩu là cái gì vậy con? Thằng cháu bà lắp rồi đi về quê, bà không biết gì hết trơn á 😅'),
        ('anh_tam', 'Không đặt mật khẩu là nguy hiểm lắm đó bà! Người lạ vô xài ké, còn có thể xem trộm dữ liệu nữa.', .9),
        ('ba_sau', 'Trời đất, bà có dữ liệu gì đâu, có mấy tấm hình con Mướp thôi 😂', .8),
        ('minh_quan', 'tối qua sang đặt giúp.', .9),
        ('ba_sau', 'Thằng Quân ít nói mà tốt bụng ghê. Bà gửi hộp bánh bò qua nghe con.', .9),
        ('minh_quan', '👍', .9),
        ('be_ti', 'ủa vậy là hết xài ké wifi bà Sáu rồi hả 😭😭 đùa thôi bà ơi', .7),
    ], react='haha'),
    T('pharmacy_night', 'ask', 'co_hanh', [
        'Có ai biết hiệu thuốc nào gần đây mở muộn không ạ? Na nhà em hơi sốt, mà em lại hết nhiệt kế. Em cảm ơn nhé.'], [
        ('ba_tam', 'Bà có nhiệt kế nè, qua lấy liền đi con. Sốt cao thì đưa đi khám nghe, đừng tự cho uống thuốc bậy.', .9),
        ('anh_khoa', 'Anh không phải bác sĩ nên không dám khuyên thuốc gì đâu, sốt trẻ con thì hỏi dược sĩ hoặc gọi bác sĩ cho chắc nha chị.', .8),
        ('chu_hung', 'Cần đi đâu chú chở, xe chú nổ máy sẵn đây. Không lấy tiền nhé.', .9),
        ('co_hanh', 'Cảm ơn cả nhà nhé, Na đỡ rồi, giờ đang đòi ăn kem ạ 😅', .9),
        ('be_na', 'Con hết sốt rồi ạ, con muốn ăn kem dâu ạ 🍦', .7),
    ], react='heart'),
    T('moving', 'ask', 'em_thu', [
        'D-dạ cuối tuần này em chuyển phòng sang dãy bên kia ạ… ai có xe ba gác hay biết chỗ thuê không ạ? Đồ em ít thôi ạ 🥺'], [
        ('chu_hung', 'Xe chú chở được. Hai chuyến là xong. Chở xong làm cốc nước mía nhé!'),
        ('chu_tu', 'Tủ nào lung lay thì khiêng qua chú bắt vít lại. Làm một lần cho xong, đỡ phiền.', .8),
        ('ba_tam', 'Dọn xong qua bà ăn cơm, ngày dọn nhà mệt lắm, đừng ăn mì gói nghe con.', .8),
        ('em_thu', 'Em… em không biết nói gì luôn ạ, em cảm ơn mọi người nhiều lắm ạ 🥺🙏', .9),
    ], react='heart'),
    # ---- selling homemade food
    T('sell_xoi', 'sell', 'chi_tu_zalo', [
        'Sáng mai xôi gấc với xôi mặn có thêm lạp xưởng nha cả nhà 🍙 Hàng xóm đặt trước chị để riêng. Mà nói nhỏ nè, nghe đâu cuối tháng này có nhà mở tiệm bánh mì đối diện, chị hơi run nhưng mà xôi chị ngon hơn 😤 Ai ủng hộ comment “1” nha!'], [
        ('chu_hung', '1. Thêm trứng nhé.', .8),
        ('minh_quan', '1.', .8),
        ('co_ba', 'Lạp xưởng lấy bên cô nè Tư, cô bớt cho, tính ra rẻ hơn chợ.', .7),
        ('kieu_trang', 'Để Trang chụp hình đăng story giùm chị, bảo đảm hết sạch 📸✨', .7),
        ('anh_tam', 'Bánh mì mới mở đó anh nghe đâu giá rẻ bất thường, coi chừng dùng đồ không rõ nguồn gốc.', .6),
        ('chi_tu_zalo', 'Cảm ơn cả nhà nha, mai chị để phần mỗi người một gói 🥰', .8),
    ], react='heart'),
    T('sell_che', 'sell', 'ba_tam', [
        'Bà mới nấu nồi chè đậu xanh bột báng to quá trời, ăn không hết. Đứa nào đi làm về qua bà múc cho một chén nghe, không lấy tiền đâu. Nấu cho vui thôi, ngày xưa ông nhà bà mê món này lắm, giờ ổng đi rồi bà nấu vẫn quen tay nấu nồi to 🥹 Mấy đứa ở trọ ốm nhom, ăn cho mập lên chút nghe.'], [
        ('be_ti', 'bà Tám đỉnh nóc kịch trần 🥹 em xin một chén nha bà', .9),
        ('em_thu', 'D-dạ em xin một chén ạ… em cảm ơn bà ạ 🥺', .8),
        ('ong_bay', 'Cho tôi một chén. Ít đường.', .8),
        ('ba_tam', 'Ông Bảy mà cũng ăn chè hả, hiếm à nghe 😄', .8),
        ('ong_bay', 'Ăn chè thì liên quan gì!!!', .7),
        ('co_hanh', 'Bà cho Na một chén nhé bà, con bé mê chè bà nấu lắm, bảo ngon hơn chè mẹ nấu 😅', .7),
    ], react='heart'),
    T('sell_flash', 'sell', 'kieu_trang', [
        '🔥 FLASH SALE tối nay 8 giờ nha cả nhà 🔥 Son, kem chống nắng, túi xách, giảm tới 50%! Hôm qua Trang chốt 120 đơn, mệt xỉu mà vui 😘 không có ý khoe đâu nha. Hàng xóm mua Trang freeship luôn!'], [
        ('anh_tam', 'Giảm 50% là có vấn đề. Hàng thật hay hàng giả vậy em?', .9),
        ('kieu_trang', 'Hàng chính hãng có hóa đơn đàng hoàng nha anh Tâm 😤 Trang làm ăn uy tín 5 năm rồi.', .9),
        ('chi_diep', 'TRỜI ƠI chị đang cần son mà chị hết tiền rồi 😭 tháng này chị tiêu quá tay.', .7),
        ('co_ba', 'Mua thì mua cái cần, đừng thấy giảm giá là mua. Cô bán hàng cả đời, cô biết.', .8),
        ('bac_liem', 'Giới trẻ bây giờ cứ thấy chữ “sale” là như thiêu thân lao vào đèn.', .7),
        ('tung_tun', 'Tối nay tui là shipper chính thức của flash sale nè 🛵💨 ai đặt ở hẻm mình tui giao trong 3 phút!', .7),
    ], react='wow'),
    T('sell_drawing', 'sell', 'be_na', [
        'Con bán tranh con tự vẽ ạ 🎨 mỗi bức 2 nghìn ạ. Tiền con để mua màu mới ạ. Có tranh mèo, tranh nhà, tranh bà Tám ạ 🌸'], [
        ('ba_tam', 'Bà mua bức tranh bà Tám! Bà treo ở phòng khách liền 🥹'),
        ('ong_bay', 'Ông lấy tranh con chim. Không có thì vẽ.', .9),
        ('minh_quan', 'lấy 1 bức mèo.', .8),
        ('co_hanh', 'Na nhà em mới học vẽ có ba tháng thôi đấy ạ, cô giáo bảo có năng khiếu 😊', .8),
        ('bac_liem', 'Tôi đặt một bức phong cảnh. Trẻ con biết tự làm ra tiền từ sức mình, tốt. Đáng khen.', .8),
        ('be_na', 'Con cảm ơn cả nhà ạ 🥰 con vẽ xong hết rồi ạ', .9),
    ], react='heart'),
    T('sell_fruit', 'sell', 'bac_liem', [
        'Cây mãng cầu trước nhà tôi năm nay sai quả. Tôi không bán, ai muốn ăn thì sang hái, nhớ hái trái chín, trái non để lại. Tôi nói trước: không bẻ cành, không trèo lên mái nhà tôi.'], [
        ('ba_sau', 'Mãng cầu là trái tượng trưng cho “cầu được ước thấy” đó mọi người, ăn lấy hên 🙏', .8),
        ('be_ti', 'bác Liêm ơi em xin một trái mà em hứa khum trèo nha 🙏', .8),
        ('bac_liem', 'Được. Cháu Tí gần đây lễ phép hơn rồi đấy.', .7),
        ('co_ba', 'Mãng cầu ngoài chợ giờ mắc lắm đó, bác cho vậy là quý rồi.', .7),
        ('tung_tun', 'Bác Liêm ngoài phán xét trong mãng cầu 🤣🍈', .6),
    ], react='heart'),
    # ---- good news & invitations
    T('exam', 'happy', 'co_hanh', [
        'Khoe chút ạ: Na nhà em thi cuối kỳ được điểm 10 cả toán lẫn tiếng Việt, được cô giáo khen trước lớp 🥰 Nhà mình có cháu nào thi chưa, được bao nhiêu điểm ạ?'], [
        ('chi_tu_zalo', 'Giỏi quá trời! Mà nghe đâu lớp đó nhiều đứa được 10 lắm đó chị 👀', .8),
        ('ba_tam', 'Giỏi quá con ơi, qua bà thưởng hộp sữa chua nghe 🥹', .9),
        ('be_ti', 'Na lớp 2 được 10, em lớp 9 được 6 phẩy mà mẹ em khen quá trời 😭 mỗi nhà một chuẩn', .9),
        ('bac_liem', 'Điểm cao là tốt, nhưng học đi đôi với hành. Học giỏi mà không biết chào hỏi thì cũng vứt.', .8),
        ('co_hanh', 'Dạ Na nhà em lễ phép lắm bác ạ, chào cả con mèo đầu ngõ 😅', .7),
        ('chi_mai', 'Giỏi quá Na ơi 🌟 mà 6 phẩy của Tí cũng đáng khen nè, có tiến bộ là giỏi rồi!', .8),
        ('be_na', 'Con cảm ơn cả nhà ạ 🥰', .7),
    ], react='heart'),
    T('wedding', 'happy', 'tung_tun', [
        'Thông báo trọng đại: anh hai tui cuối tháng này cưới vợ 🎉 Cả hẻm mời hết nha, tiệc ở nhà văn hóa. Anh em nào đi thì comment để tui báo số bàn, ai không đi thì… cũng comment để tui buồn 😂'], [
        ('chu_hung', 'Có bia không cháu? Có thì chú đi hai suất 🍺'),
        ('ba_sau', 'Bà coi ngày rồi, ngày đó tốt lắm, hợp tuổi cô dâu chú rể. Trăm năm hạnh phúc nghe con.', .9),
        ('kieu_trang', 'Trang lo phần chụp hình check-in cho! Backdrop hoa tươi luôn nha, không có ý khoe đâu 💐', .8),
        ('co_ba', 'Đi đám cưới giờ phong bì bao nhiêu cho vừa ta, vật giá lên hết rồi 😅', .8),
        ('ong_bay', 'Hát karaoke đến mấy giờ?', .8),
        ('tung_tun', 'Tới 10 giờ thôi ông ơi, tui hứa bằng danh dự shipper 🫡', .8),
        ('minh_quan', 'chúc mừng.', .7),
    ], react='heart'),
    T('birthday_ba_sau', 'happy', 'co_lua', [
        '🎂 Hôm nay là sinh nhật lần thứ 76 của bà Sáu, người sống lâu năm nhất hẻm mình. Tổ dân phố kính chúc bà luôn mạnh khỏe, vui vẻ bên con Mướp ạ!'], [
        ('ba_sau', 'Trời ơi bà cảm ơn cô Lụa với cả xóm nghe 🥹 Năm nay bà tuổi Ngọ gặp sao Thái Âm, tốt lắm. Chiều bà nấu nồi chè mời cả xóm nha.'),
        ('ba_tam', 'Chúc bà Sáu sống lâu trăm tuổi, năm nào tui với bà cũng ngồi nói chuyện đầu hẻm nghe 🥹', .9),
        ('minh_quan', 'chúc mừng sinh nhật bà.', .8),
        ('be_na', 'Con chúc bà Sáu sinh nhật vui vẻ ạ 🎂 con vẽ tặng bà con Mướp ạ', .9),
        ('ong_bay', 'Chúc bà mạnh khỏe. Bảo con mèo đừng sang nhà tôi.', .8),
        ('tung_tun', '🖼️ [Ảnh chế] Con Mướp đội nón sinh nhật: “Hôm nay sen nhà tui sinh nhật, cấm ai la tui.” 🎉', .7),
    ], react='heart'),
    T('new_car', 'happy', 'kieu_trang', [
        'Chính thức rước em xe mới về rồi nè cả nhà 🚗✨ Làm lụng mấy năm cuối cùng cũng có. Không có ý khoe đâu nha, chỉ muốn chia vui thôi 😘 Mai Trang chở mấy chị đi uống cà phê!'], [
        ('ong_bay', 'Xe to thế đậu ở đâu? Không được đậu trước cửa tôi!!!'),
        ('chi_tu_zalo', 'Nghe đâu xe này trả góp đó mọi người 👀 à mà thôi chị nói nhỏ thôi, chúc mừng em nha!', .8),
        ('bac_liem', 'Giới trẻ bây giờ thích khoe của. Thời chúng tôi có cái xe đạp là mừng cả tháng.', .8),
        ('tung_tun', 'Chúc mừng! Xe mới thì cần shipper mới làm tài xế không, tui nhận việc liền 🛵➡️🚗', .8),
        ('chi_mai', 'Chúc mừng Trang nha, làm ra tiền bằng sức mình là giỏi rồi 🌈', .7),
        ('co_ba', 'Xe đẹp. Nhớ tính tiền xăng, tiền gửi xe, tiền bảo hiểm mỗi tháng, đừng để xe nuôi người mệt quá nha con.', .7),
    ], react='wow'),
    T('wifi_fixed', 'happy', 'co_lua', [
        '📢 Cảm ơn cháu Quân đã lắp lại mạng wifi miễn phí ở nhà văn hóa cho các cháu học bài. Tổ dân phố ghi nhận tinh thần của cháu ạ.'], [
        ('minh_quan', 'ok.'),
        ('be_ti', 'anh Quân đỉnh quá 🫡 giờ wifi nhà văn hóa mạnh hơn wifi nhà em luôn', .9),
        ('ba_tam', 'Thằng Quân ít nói mà làm được việc ghê, qua bà cho hộp cơm nghe con.', .9),
        ('minh_quan', '👍', .8),
        ('bac_liem', 'Giới trẻ như cháu Quân thì tôi không có gì để phàn nàn.', .7),
        ('tung_tun', 'Quân mà nói hơn 3 chữ trong một câu chắc wifi cả phố sập 🤣', .7),
    ], react='heart'),
    T('new_baby', 'happy', 'chi_tu_zalo', [
        'Tin vui nè cả nhà ơi!!! Nhà số 7 mới có em bé đó, bé trai, 3 ký 2, mẹ tròn con vuông 👶 Chị biết đầu tiên luôn vì sáng nay ông nội ra mua xôi mà cười không khép miệng được 😂 Ai ghé thăm thì nhớ nói nhỏ nha, em bé đang ngủ.'], [
        ('ba_sau', 'Bé tuổi này mạng Kim, sau này làm ăn khá lắm đó. Bà mừng quá 🥹', .9),
        ('ba_tam', 'Bà nấu nồi cháo móng giò gửi qua cho mẹ bé liền, mẹ đẻ phải ăn cho có sữa.', .9),
        ('co_hanh', 'Chúc mừng nhà số 7 nhé! Na nhà em hồi đẻ ra 3 ký 5 cơ, bác sĩ khen suốt.', .7),
        ('ong_bay', 'Có em bé thì cả hẻm nhớ nói nhỏ, đừng hát hò nữa!!!', .8),
        ('chu_hung', 'Chú chở mẹ con đi tiêm chủng miễn phí nhé, cứ gọi chú!', .7),
    ], react='heart'),
    # ---- drama
    T('bad_haircut', 'drama', 'chi_diep', [
        'TRỜI ƠI mọi người ơi 😭😭😭 Chị đi cắt tóc mà thợ cắt hư hết rồi, giờ chị như cây nấm luôn. Mai chị còn đi đám cưới nữa, chị không dám ra đường luôn đó. Cuộc đời chị sao khổ vậy nè 😭'], [
        ('chi_mai', 'Chị ơi tóc nấm đang là mốt đó, nhìn trẻ ra 5 tuổi luôn nè 🌈', .9),
        ('chu_tu', 'Tóc mọc lại. Đừng khóc nữa.', .9),
        ('kieu_trang', 'Qua salon quen của Trang nè chị, em book cho, chị tỉa lại là xinh lung linh liền ✨', .8),
        ('tung_tun', '🖼️ [Ảnh chế] Cây nấm đội mũ đi đám cưới, chú thích: “Khách mời VIP.” Đùa thôi chị Diệp đừng giận tui 🙏', .7),
        ('bac_liem', 'Tóc tai không quan trọng bằng cái nết.', .6),
        ('chi_diep', 'Thôi chị đội nón đi đám cưới. Cảm ơn mọi người đã dỗ chị 🥹', .8),
    ], react='sad'),
    T('phone_fridge', 'drama', 'chi_diep', [
        'MỌI NGƯỜI ƠI chị mất điện thoại rồi 😭😭 tìm cả buổi sáng không thấy, trong đó có danh bạ khách hàng, hình ảnh, tất cả mọi thứ 😭 Chị muốn xỉu luôn. Ai thấy cái điện thoại ốp hồng có hình con mèo không 😭'], [
        ('anh_tam', 'Em đăng bài bằng gì vậy Diệp? 🤨', .9),
        ('chi_diep', '…bằng máy tính bảng 😭 mà thôi chị tìm thấy rồi, nó nằm trong tủ lạnh, chị để cạnh hộp sữa chua 😭😭', .9),
        ('tung_tun', 'Điện thoại cũng cần được làm mát mà chị 🤣🧊', .9),
        ('ba_sau', 'Để bà coi, tuần này tuổi Dần hay quên, chị Diệp tuổi Dần phải không 😅', .6),
        ('chi_mai', 'Tìm được là vui rồi nè, lại còn mát lạnh nữa 🌈', .7),
    ], react='haha'),
    T('breakup_npc', 'drama', 'chi_diep', [
        'Chị chia tay rồi mọi người ạ 💔 5 năm quen nhau mà giờ người ta nói “mình không hợp”. Hợp 5 năm rồi mới không hợp hả 😭 Tối nay chị ngồi một mình ăn hết một hộp kem luôn rồi 😭'], [
        ('ba_tam', 'Thôi con, người không thương mình thì mình thương mình. Qua bà nấu cháo, ăn đồ ấm cho đỡ buồn. Hồi xưa bà cũng từng khóc vì một người, giờ bà còn không nhớ mặt ổng nữa 😄', .9),
        ('chi_mai', 'Chị xứng đáng với người tốt hơn nè 🌈 Mai chị em mình đi dạo công viên nha.', .9),
        ('chu_tu', 'Buồn thì qua tiệm chú ngồi. Chú không nói gì đâu, có ấm trà thôi.', .8),
        ('chi_tu_zalo', 'Nghe đâu ông kia có người mới rồi đó… à thôi thôi chị không nói nữa, em đừng buồn 🫢', .7),
        ('co_lua', 'Nhắc nhẹ cả nhà: chuyện riêng của người khác mình động viên thôi, không bàn thêm nhé.', .7),
        ('chi_diep', 'Cảm ơn mọi người nhiều lắm 🥹 có hàng xóm như vầy chị thấy đỡ cô đơn ghê.', .9),
    ], react='sad'),
    # ---- chit-chat
    T('meme_fridge', 'chat', 'tung_tun', [
        '🖼️ [Ảnh chế] Một người mở tủ lạnh lần thứ 7 trong 5 phút, chú thích: “Biết đâu lần này có món mới.” Ai giống tui điểm danh 🙋‍♂️',
        '🖼️ [Ảnh chế] Con mèo nằm úp mặt xuống bàn phím, chú thích: “Tôi lúc 3 giờ chiều thứ Hai.” Cả hẻm ai đang giống con mèo này 😂'], [
        ('be_ti', 'em nè 🙋 tủ lạnh nhà em toàn nước lọc mà em vẫn mở 😭', .9),
        ('chi_diep', 'Chị luôn đó, mở ra đóng vô rồi ăn bánh tráng 😭😂', .8),
        ('minh_quan', '😐', .7),
        ('bac_liem', 'Giới trẻ bây giờ rảnh quá mới ngồi chế ảnh.', .7),
        ('tung_tun', 'Bác ơi bác đang đọc ảnh chế trên điện thoại đó bác 🤭', .7),
        ('ba_tam', 'Mở tủ lạnh nhà bà là có đồ ăn liền nè, qua đây 😂', .7),
    ], react='haha'),
    T('youth_phone', 'chat', 'bac_liem', [
        'Chiều nay tôi ngồi công viên, đếm được 23 thanh niên, 22 người cắm mặt vào điện thoại. Giới trẻ bây giờ không còn nói chuyện với nhau nữa. Thời chúng tôi, chiều ra công viên là đánh cờ, đá cầu, bàn chuyện thời sự. Tôi viết mấy dòng này mong các cháu suy nghĩ.'], [
        ('be_ti', 'bác ơi bác đang đăng bài trên điện thoại đó ạ 🤭', .9),
        ('bac_liem', 'Tôi dùng điện thoại có mục đích!', .9),
        ('chi_mai', 'Bác nói cũng đúng nè, cuối tuần này lớp chị tổ chức ngày không điện thoại cho tụi nhỏ chơi ô ăn quan đó 🌈 bác qua dạy tụi nhỏ đánh cờ không bác?', .8),
        ('bac_liem', 'Được. Chín giờ sáng tôi qua.', .7),
        ('tung_tun', 'Người thứ 23 là tui, tui đang coi bản đồ giao hàng bác ơi 😭', .7),
    ], react='haha'),
    T('horoscope', 'chat', 'ba_sau', [
        'Bà coi tử vi tuần này cho cả xóm nè 🔮 Tuổi Tý có quý nhân phù trợ, tuổi Sửu nên kiêng đi xa, tuổi Dần hao tài nhẹ, tuổi Mão (con Mướp nhà bà) được ăn ngon 😂 Ai tuổi gì nói bà coi thêm cho. Mà nhớ nghe, tin thì tin vừa vừa thôi, sống tốt là quan trọng nhất.'], [
        ('chi_diep', 'Tuổi Dần hao tài là đúng rồi bà ơi 😭 tuần này chị mua ba cây son rồi.', .9),
        ('anh_khoa', 'Thật ra tử vi chỉ để tham khảo cho vui thôi bà ạ, theo anh tìm hiểu thì nó không có cơ sở khoa học. Nhưng mà cháu tuổi Thìn, bà coi giùm cháu tuần này có tăng lương không 😅', .8),
        ('ba_sau', 'Tuổi Thìn tuần này có lộc, mà con lo làm việc đàng hoàng thì lộc mới tới nghe.', .8),
        ('anh_tam', 'Bà coi thì được, chứ ai nhắn tin đòi tiền “giải hạn” là lừa đảo đó nha mọi người.', .7),
        ('minh_quan', 'tuổi Dậu.', .6),
        ('ba_sau', 'Tuổi Dậu tuần này nên nói nhiều hơn một chút con à 😂', .6),
    ], react='haha'),
    T('beer_match', 'chat', 'chu_hung', [
        'Tối nay có trận bóng hay đấy anh em ơi ⚽ Quán bia đầu ngõ chiếu màn hình to. Ai ra thì báo, chú giữ bàn. Đội nào thắng thì đội kia trả tiền lạc nhé 🍺'], [
        ('tung_tun', 'Tui ra! Giao đơn cuối xong là tui chạy qua liền 🛵', .9),
        ('ong_bay', 'Xem bóng thì hò hét nhỏ thôi!!! 11 giờ tôi đi ngủ.', .9),
        ('chu_hung', 'Bác Bảy ra xem cùng luôn cho vui, cháu mời bác cốc trà đá nhé!', .8),
        ('ong_bay', '…Đội nào đá?', .7),
        ('bac_liem', 'Tôi không uống bia, nhưng tôi ra phân tích chiến thuật cho các anh.', .6),
        ('chi_diep', 'Mấy anh đi coi bóng, còn chị ở nhà coi phim Hàn khóc một mình 😭', .6),
    ], react='haha'),
    T('save_power', 'chat', 'anh_khoa', [
        'Chia sẻ mẹo tiết kiệm điện mùa nắng cho cả hẻm nha. Thật ra theo anh tìm hiểu, bật máy lạnh 18 độ cho nhanh mát rồi tăng lên là tiết kiệm nhất. Rút sạc khi không dùng. Tủ lạnh đừng để sát tường. Anh làm vậy hóa đơn tháng rồi giảm hẳn luôn 🤓'], [
        ('minh_quan', 'sai.'),
        ('anh_khoa', 'Sai chỗ nào em?', .9),
        ('minh_quan', 'để 26 độ ngay từ đầu. 18 độ tốn điện hơn.', .9),
        ('anh_khoa', 'À… thì anh cũng định nói vậy mà 😅 ý anh là 26 độ đó.', .9),
        ('tung_tun', 'Quân nói 7 chữ trong một câu, lịch sử hẻm ghi nhận 📜🤣', .8),
        ('co_ba', 'Tiết kiệm nhất là mở cửa sổ với quạt. Tính ra một tháng đỡ cả trăm nghìn.', .7),
    ], react='haha'),
    T('compare_kids', 'chat', 'co_hanh', [
        'Hỏi vui các mẹ: con nhà mình mấy tuổi biết bơi ạ? Na nhà em 6 tuổi đã bơi được 25 mét rồi, giờ đang học bơi bướm. Em thấy trẻ con bây giờ phải biết nhiều kỹ năng từ sớm cơ.'], [
        ('chi_mai', 'Biết bơi là kỹ năng quý lắm chị ơi, giỏi quá Na 🏊‍♀️', .9),
        ('be_ti', 'em 15 tuổi vẫn bơi kiểu chó 🐶 mà vẫn sống khỏe nha cô', .9),
        ('co_hanh', 'Tí thì phải đi học bơi đi chứ, lớp 9 rồi còn gì 😅', .8),
        ('ba_sau', 'Ngày xưa bà ra sông tắm, tự biết bơi hồi nào không hay 😄', .7),
        ('bac_liem', 'So sánh con mình với con người khác là cách nhanh nhất làm hỏng một đứa trẻ. Tôi nói thẳng.', .7),
        ('co_hanh', 'Dạ em hỏi vui thôi bác ạ 😅', .7),
    ], react='haha'),
    T('che_extra', 'chat', 'em_thu', [
        'D-dạ em mới nấu thử chè khúc bạch lần đầu… mà em nấu dư một nồi ạ 🥺 ai ăn giùm em không ạ… chắc không ngon lắm đâu ạ, em xin lỗi trước ạ.'], [
        ('ba_tam', 'Để bà nếm thử cho! Lần đầu nấu mà dám mời cả xóm là giỏi lắm rồi đó con 🥹', .9),
        ('be_ti', 'em ăn hết cả nồi được luôn chị ơi 🤤', .8),
        ('chu_tu', 'Chú lấy một chén. Không phải khen đâu, ăn thử coi sao thôi.', .8),
        ('chu_tu', 'Ngon. Lần sau bớt đường.', .7),
        ('em_thu', 'D-dạ em cảm ơn mọi người ạ 🥺 em vui lắm ạ.', .9),
        ('chi_mai', 'Lần đầu mà ngon vậy là có khiếu nấu ăn đó nha 🌈', .6),
    ], react='heart'),
    T('drawing_gift', 'chat', 'be_na', [
        'Con vẽ tặng bà Tám bức tranh bà đang nấu chè ạ 🎨🍵 con vẽ bà mặc áo hoa ạ. Con cảm ơn bà hôm trước cho con bánh flan ạ.'], [
        ('ba_tam', 'Trời ơi bà cảm động quá 🥹 bà treo ngay giữa nhà nghe con. Mai qua bà làm bánh flan nữa cho.'),
        ('co_hanh', 'Na tự nghĩ ra đấy ạ, em không nhắc gì cả 😊', .8),
        ('ong_bay', 'Vẽ đẹp. Lần sau vẽ ông với con chim.', .8),
        ('bac_liem', 'Biết ơn là bài học đầu tiên của làm người. Cháu Na ngoan.', .7),
        ('be_ti', 'Na vẽ đẹp hơn em rồi đó 😭🎨', .6),
    ], react='heart'),
    T('stranger', 'chat', 'anh_tam', [
        '🤨 Chiều nay anh thấy có người lạ đội mũ đen, đeo khẩu trang lảng vảng đầu hẻm cả tiếng đồng hồ. Mọi người khóa cửa cẩn thận nha. Anh nghi lắm.'], [
        ('co_hai_loa', 'Cô thấy rồi! 3 giờ 15 người đó đi vào, 3 giờ 22 đứng trước nhà số 9, 3 giờ 40 bấm điện thoại. Cô nhìn không sót giây nào 👀', .9),
        ('tung_tun', 'Là tui đó anh Tâm 😭📦 tui đứng đợi khách nhà số 9 nghe máy cả tiếng, mũ đen là mũ bảo hiểm của tui á.', .9),
        ('anh_tam', '…Ừ. Vậy thì được. Nhưng lần sau em cởi khẩu trang ra cho anh nhận mặt.', .8),
        ('chi_tu_zalo', 'Vậy nhà số 9 đặt hàng gì mà giao lâu vậy ta 👀', .7),
        ('co_lua', 'Cảm ơn anh Tâm đã để ý. Cả nhà cẩn thận nhưng đừng nghi oan người khác nhé.', .7),
    ], react='haha'),
    T('giveaway', 'chat', 'kieu_trang', [
        '🎁 GIVEAWAY mừng shop đạt 10.000 người theo dõi 🎁 Hàng xóm share bài này và tag 2 người bạn là có cơ hội nhận son xịn nha 😘 Không có ý khoe đâu, chỉ muốn cảm ơn mọi người thôi!'], [
        ('anh_tam', 'Share rồi có phải điền số tài khoản không em? Anh hỏi cho chắc.', .9),
        ('kieu_trang', 'Không có nha anh Tâm 😤 Trang giao tận tay luôn, anh yên tâm.', .9),
        ('be_ti', 'em tag bà Sáu với chú Hùng nha 🤣', .8),
        ('chu_hung', 'Chú trúng son thì tặng vợ, vợ vui thì chú được đi bia 🍺', .7),
        ('minh_quan', 'không tham gia.', .6),
    ], react='heart'),
    T('exercise', 'chat', 'chi_mai', [
        'Sáng mai 5 giờ 30 ai đi tập dưỡng sinh ở công viên với chị không nè 🌅 Không khí buổi sáng trong lành lắm, tập xong mình đi ăn xôi chị Tư luôn!'], [
        ('ba_sau', 'Bà đi! Tập xong bà coi ngày cho mọi người luôn.', .8),
        ('minh_quan', 'không.', .9),
        ('chi_tu_zalo', 'Có người tập xong ghé xôi là chị vui rồi 🍙', .8),
        ('chu_hung', '5 giờ 30 chú mới về tới nhà 😂', .7),
        ('bac_liem', 'Tôi dậy từ 4 giờ 30. Giới trẻ 5 giờ 30 đã gọi là sớm.', .7),
    ], react='heart'),
    T('closed_early', 'chat', 'co_ba', [
        'Hôm nay tạp hóa cô đóng cửa sớm lúc 5 giờ chiều vì đi đám giỗ. Ai cần mua gì thì mua trước nha, đừng để tối gõ cửa. Mai mở lại như thường.'], [
        ('chi_tu_zalo', 'Đám giỗ bên nội hay bên ngoại vậy cô 👀', .8),
        ('co_ba', 'Hỏi chi vậy Tư 😆', .8),
        ('ong_bay', 'Tôi cần mua lọ nước mắm. Tôi sang ngay.', .7),
        ('be_ti', 'cô Ba ơi để em qua mua bịch snack cuối cùng trước khi đóng cửa 🥲', .7),
    ], react='heart'),
    T('tet_cleanup', 'chat', 'co_lua', [
        '📢 Chủ nhật này tổ tổng vệ sinh hẻm: quét dọn, sơn lại tường, trồng thêm cây. Mời mỗi nhà một người tham gia từ 7 giờ sáng. Có nước mía và bánh mì cho mọi người ạ.'], [
        ('chu_tu', 'Chú mang dụng cụ. Không phải vì nhiệt tình đâu, đồ nghề để lâu cũng rỉ.', .9),
        ('be_ti', 'em tham gia nếu có nước mía nha cô 🥤', .8),
        ('kieu_trang', 'Trang tài trợ chậu hoa cho đầu hẻm nè, xong chụp hình đăng lên cho đẹp 🌸', .8),
        ('ong_bay', 'Dọn cái cống trước nhà tôi trước!!!', .8),
        ('chi_mai', 'Chị dẫn tụi nhỏ lớp chị qua vẽ tranh lên tường cho vui nha 🎨', .7),
        ('minh_quan', 'có mặt.', .6),
    ], react='heart'),
]
THREAD_INDEX = {t['key']: t for t in THREADS}

# ---------------------------------------------------------------- floaters
# Extra in-character comments sprinkled on authored threads, by temperament and mood ('any' as fallback).
FLOAT = {
    'warm': dict(
        any=['Mấy đứa ăn cơm chưa? Bà nấu dư, qua bà múc cho nghe 🍲', 'Thôi mọi người thương nhau chút, hẻm mình nhỏ mà, gặp nhau hoài à 😄'],
        lost=['Bà ra đầu hẻm ngó giùm cho. Đừng lo quá nghe, trong hẻm mình không mất gì đâu.'],
        complain=['Thôi thôi, ai cũng có cái khó. Mai bà pha ấm trà, mọi người ngồi nói chuyện đàng hoàng với nhau nghe.'],
        drama=['Buồn thì qua bà, bà có chè, có cháo, có cả cái tai nghe con kể nữa 🥹'],
        happy=['Mừng quá trời, để bà nấu nồi chè ăn mừng nghe 🥹'],
        sell=['Bà ủng hộ một phần! Người trong hẻm mình bán thì mình mua, tiền đi đâu cũng là tiền trong xóm.'],
        warn=['Nhà ai có người già, con nhỏ thì để ý giùm nhau nghe. Có gì kêu bà.']),
    'official': dict(
        any=['Tổ dân phố ghi nhận ý kiến của bà con ạ.', 'Nhắc nhẹ: nhóm dùng để giúp nhau, bà con trao đổi lịch sự nhé.'],
        complain=['Tổ sẽ nhắc nhở riêng từng hộ, đề nghị bà con không gay gắt trên nhóm ạ.'],
        lost=['Ai nhặt được đồ thất lạc có thể gửi ở nhà văn hóa, tổ giữ giúp ạ.'],
        drama=['Chuyện riêng của mỗi người, mình động viên nhau là đủ ạ.'],
        warn=['Cảm ơn bà con đã chia sẻ thông tin. Có gì cần hỗ trợ cứ nhắn tổ trưởng.']),
    'tsundere': dict(
        any=['Phiền ghê. Mà thôi, cần gì thì nói.', 'Không phải chú quan tâm đâu. Hỏi vậy thôi.'],
        lost=['Để chú ngó quanh tiệm. Không hứa gì đâu.'],
        ask=['Mang qua tiệm. Chú coi. Đừng cảm ơn.'],
        drama=['Khóc hoài mệt không. Qua tiệm uống ly trà rồi về ngủ.'],
        complain=['Cãi nhau chi cho mệt. Hư gì thì chú sửa.']),
    'knowitall': dict(
        any=['Thật ra chuyện này anh có tìm hiểu rồi, nó phức tạp hơn mọi người nghĩ nhiều. Nói chung là phải có phương pháp, làm từng bước, đừng làm theo cảm tính. Anh đọc được ở đâu đó mà giờ quên mất nguồn 😅'],
        ask=['Theo anh tìm hiểu thì nên hỏi ít nhất ba chỗ rồi so giá, chất lượng, thời gian bảo hành. Thật ra đa số mọi người chỉ hỏi một chỗ nên hay bị hớ đó. Anh nói vậy thôi chứ tùy em.'],
        warn=['Thật ra vụ này năm nào cũng có, chỉ là năm nay báo sớm hơn. Mọi người chuẩn bị từ tối hôm trước là nhàn nhất, sáng ra đỡ cuống.'],
        lost=['Thật ra đồ thất lạc thường nằm trong bán kính vài chục mét quanh chỗ mình đứng cuối cùng, theo anh tìm hiểu là vậy. Mọi người nhớ lại xem lần cuối cầm là ở đâu.']),
    'genz': dict(
        any=['ủa alo hẻm mình drama dữ zị 🍿', 'đỉnh nóc kịch trần luôn 🫡', 'khum hỉu nhưng mà ủng hộ nha 🤝'],
        happy=['chúc mừngggg 🥳🥳 flex nhẹ đi mọi người ơi', 'xỉu ngang, xịn xò quá trời 😭✨'],
        complain=['thôi mà mọi người, chill chill đi 🧊'],
        drama=['ôm một cái nè 🫂 mai là hết buồn nha'],
        sell=['em chốt đơn 1 nha, xin freeship hàng xóm 🥺']),
    'superstitious': dict(
        any=['Bà coi rồi, tuần này sao tốt chiếu, mọi chuyện sẽ ổn thôi. Mà nhớ ra đường bước chân phải trước nghe mấy đứa 🙏'],
        lost=['Mất đồ thì con thử tìm theo hướng Đông Nam, ngày này hướng đó hên lắm. Tìm không thấy thì cũng đừng buồn, của đi thay người mà con.'],
        happy=['Bà đã nói mà, năm nay tuổi này có quý nhân. Nhớ thắp nhang cảm ơn ông bà nghe.'],
        drama=['Năm nay con gặp hạn Tam Tai hay sao đó, ráng qua tháng này là hết. Bà nói vậy cho yên lòng thôi chứ sống tốt là được con à.'],
        warn=['Ngày này bà coi không đẹp, ai đi xa thì cẩn thận nghe.']),
    'practical': dict(
        any=['Tính ra thì cũng không đáng bao nhiêu, làm luôn cho xong.', 'Cái gì cũng phải tính trước, đừng để nước tới chân mới nhảy.'],
        sell=['Giá vậy là được, ngoài chợ còn mắc hơn.'],
        ask=['Hỏi giá trước rồi hẵng làm, đừng để làm xong mới báo giá.'],
        warn=['Trữ nước, trữ đồ khô trước một ngày. Tới lúc cần mới mua là hết hàng, lại bị đội giá.'],
        drama=['Buồn thì buồn một bữa thôi, mai còn đi làm kiếm tiền.']),
    'cold': dict(
        any=['ok.', 'ừ.', '👍', 'biết rồi.'],
        ask=['hỏi cô Ba.', 'google.'],
        happy=['chúc mừng.', '👏'],
        complain=['đồng ý.'],
        drama=['…ổn không?']),
    'gossip': dict(
        any=['Ơ vụ này chị nghe rồi nè, mà thôi để chị kể riêng, trên nhóm nói không tiện 👀 Nói chung là có uẩn khúc đó mọi người. Ai muốn biết ghé xôi chị sáng mai nha 🍙'],
        happy=['Chị biết tin này từ hôm qua rồi mà hứa giữ bí mật nên chị nhịn nãy giờ đó 😂 Chúc mừng nha!'],
        complain=['Nhà nào vậy ta 👀 chị hỏi vậy thôi chứ chị không có nói ai đâu nha.'],
        lost=['Nghe đâu hồi chiều có người thấy ở ngã ba đó, để chị hỏi mấy khách mua xôi coi sao nha.'],
        drama=['Nghe đâu chuyện này có liên quan tới… à thôi thôi chị không nói đâu 🫢']),
    'joker': dict(
        any=['🖼️ [Ảnh chế] Con mèo ngồi xem điện thoại, chú thích: “Tôi đọc nhóm cư dân lúc 11 giờ đêm.” 🤣', 'Hẻm mình drama còn hay hơn phim truyền hình 8 giờ tối 📺😂'],
        complain=['Đề nghị hẻm mình lập thêm nhóm “Than Phiền Cư Dân Phố” cho tiện quản lý 🤣'],
        happy=['Tin vui kiểu này phải có tiệc chứ nhỉ, tui góp phần ăn 🍗'],
        lost=['Tui chạy ship khắp nơi, thấy là tui chụp hình gửi liền nha 📸🛵'],
        warn=['Chuẩn bị tinh thần chiến đấu thôi anh em ơi 🫡']),
    'grumpy': dict(
        any=['Nói ít thôi, làm nhiều vào!!!', 'Thời bây giờ cái gì cũng phải đăng lên nhóm!!!'],
        happy=['Ừ. Chúc mừng. Nhưng tổ chức ăn mừng thì nhỏ tiếng thôi!!!'],
        sell=['Bán thì bán, đừng để hàng ra lối đi!!!'],
        ask=['Hỏi cô Lụa ấy, tổ trưởng để làm gì!!!'],
        drama=['Chuyện bé xé ra to!!!']),
    'showoff': dict(
        any=['Trang cũng từng vậy nè, mà giờ ổn rồi, còn mua được đồ mới 😘 không có ý khoe đâu nha.', 'Để Trang chụp hình đăng story ủng hộ luôn ✨📸'],
        happy=['Chúc mừng nha! Nhân dịp này Trang tặng mã giảm giá cho cả hẻm luôn 😘'],
        sell=['Để Trang đăng lên trang bán hàng 10 nghìn người theo dõi của Trang cho, không có ý khoe đâu 😌'],
        drama=['Buồn thì đi shopping nè, Trang dẫn đi, bảo đảm vui liền ✨']),
    'shy': dict(
        any=['D-dạ em đồng ý ạ…', 'Em… em cũng thấy vậy ạ 🥺'],
        happy=['D-dạ em chúc mừng ạ 🥺🎉'],
        lost=['Em… em để ý giúp ạ.'],
        drama=['Em… em gửi chị cái ôm ạ 🥺'],
        sell=['D-dạ em xin một phần ạ…']),
    'drama': dict(
        any=['TRỜI ƠI chị cũng bị y chang vậy nè 😭😭 cuộc đời chị toàn chuyện kiểu này thôi mọi người ơi. Hôm qua chị còn bị đứt dép giữa đường, hôm kia bị chim ị trúng áo trắng. Chị kể vậy thôi chứ chị ổn 😭'],
        warn=['TRỜI ƠI vậy là chị toi rồi 😭 chị chưa chuẩn bị gì hết!!!'],
        happy=['TRỜI ƠI vui quá chị khóc luôn nè 😭😭🎉'],
        complain=['Chị cũng khổ vì vụ này lắm mọi người ơi 😭 đêm qua chị mất ngủ luôn!!!']),
    'beer': dict(
        any=['Chuyện gì thì chuyện, chiều ra làm cốc bia hơi là xong hết nhé 🍺', 'Chú góp ý thế thôi, còn lại anh em cứ vui vẻ lên!'],
        happy=['Tin vui thế này phải làm vài cốc chứ! Dô! 🍻'],
        ask=['Cần chở gì thì gọi chú, xe chú chạy suốt ngày!'],
        drama=['Buồn thì ra đây chú mời cốc trà đá, ngồi tí là hết buồn!']),
    'tigermom': dict(
        any=['Na nhà em cũng từng thế, nhưng em cho con học thêm kỹ năng là ổn ngay ạ.', 'Nhà ai có con nhỏ thì chú ý nhé, em rút kinh nghiệm từ Na nhà em đấy.'],
        happy=['Chúc mừng nhé! Mà con nhà mình năm nay học lớp mấy rồi ạ?'],
        ask=['Em hỏi thêm: bên đó có lớp cho trẻ con không ạ? Na nhà em đang cần.']),
    'kid': dict(
        any=['Con chào cả nhà ạ 🌸', 'Con thấy vui ạ 🥰'],
        happy=['Con chúc mừng ạ 🎉 con vẽ tặng một bức tranh ạ'],
        lost=['Con đi tìm giúp ạ 🔍'],
        drama=['Con cho cô một cái kẹo ạ 🍬 ăn kẹo là hết buồn ạ']),
    'judge': dict(
        any=['Tôi nói thẳng: giới trẻ bây giờ cái gì cũng vội. Thời chúng tôi, làm gì cũng nghĩ trước ba lần. Không phải tôi khó tính, tôi nói để các cháu nghĩ.'],
        happy=['Tốt. Nhưng đừng vì thế mà tự mãn.'],
        complain=['Chuyện này là do ý thức. Ý thức kém thì nhắc bao nhiêu cũng vậy.'],
        sell=['Buôn bán thì phải thật thà. Thời chúng tôi, chữ tín quý hơn vàng.'],
        drama=['Chuyện nhỏ mà cứ làm to. Giới trẻ bây giờ yếu đuối quá. Nhưng mà thôi, cố lên.']),
    'camera': dict(
        any=['{Me} ngồi đầu hẻm {me} thấy hết nha 👀 mà {me} không có ý gì đâu, {me} chỉ nói những gì {me} thấy thôi.', '{Me} thấy rồi… {me} hỏi vậy thôi 👀'],
        lost=['Lúc chiều {me} thấy có người cầm cái gì đó đi về phía ngã ba, khoảng 4 giờ 20. Không biết có phải không 👀'],
        complain=['{Me} thấy hết rồi đó, mà {me} không nói tên đâu. Người đó biết là được 👀'],
        happy=['{Me} biết trước cả tuần rồi, hôm bữa thấy khiêng đồ vô ra mà 👀']),
    'suspicious': dict(
        any=['Anh thấy có gì đó không ổn. Mọi người cẩn thận nha.', 'Coi chừng lừa đảo. Đừng chuyển tiền cho ai hết.'],
        sell=['Rẻ quá là có vấn đề. Anh nói trước.'],
        ask=['Nhớ hỏi giá rõ ràng, có giấy tờ, đừng tin lời hứa miệng.'],
        lost=['Ai nhắn đòi tiền để trả đồ là lừa đảo nha.']),
    'optimist': dict(
        any=['Không sao đâu, rồi mọi chuyện sẽ ổn thôi 🌈', 'Nhìn mặt tích cực nè: ít nhất cả hẻm được nói chuyện với nhau 😄'],
        complain=['Mọi người nhường nhau chút là vui liền nè 🙌'],
        drama=['Mai trời lại nắng mà 🌞 cố lên nha!'],
        warn=['Chuẩn bị kỹ là yên tâm rồi, cả hẻm mình giúp nhau mà 💪'],
        lost=['Chắc chắn sẽ tìm thấy thôi, hẻm mình tử tế lắm 🌈']),
}

# ---------------------------------------------------------------- replies to the player
# Intent of the player's text -> temperaments that like to answer it (first ones most often).
INTENT_TEMPERS = {
    'sad': ('warm', 'optimist', 'tsundere', 'kid', 'beer', 'shy', 'superstitious', 'judge'),
    'happy': ('warm', 'showoff', 'joker', 'tigermom', 'beer', 'genz', 'optimist', 'gossip'),
    'ask': ('knowitall', 'practical', 'cold', 'official', 'gossip', 'suspicious'),
    'help': ('tsundere', 'warm', 'beer', 'practical', 'cold', 'shy'),
    'lost': ('camera', 'gossip', 'official', 'warm', 'kid', 'suspicious'),
    'complain': ('grumpy', 'judge', 'official', 'warm', 'joker', 'optimist'),
    'sell': ('practical', 'gossip', 'showoff', 'suspicious', 'beer', 'warm'),
    'food': ('warm', 'beer', 'practical', 'gossip', 'kid', 'genz'),
    'greet': ('warm', 'official', 'genz', 'kid', 'joker', 'cold', 'camera'),
    'thanks': ('warm', 'optimist', 'tsundere', 'shy', 'official'),
    'any': ('warm', 'joker', 'gossip', 'genz', 'knowitall', 'optimist', 'judge', 'cold'),
}

REPLY = {
    'warm': dict(
        sad=['Trời đất ơi, {you} buồn chuyện gì kể bà nghe. Tối nay xuống bà nấu canh chua, ăn chén cơm nóng rồi ngủ một giấc, mai tính tiếp nghe con. Chuyện gì rồi cũng qua hết, bà sống 72 năm rồi bà biết mà 🥹',
             'Thương quá. Có chuyện gì thì cứ nói với bà, đừng ôm một mình nghe. Bà để phần {you} chén chè trong tủ lạnh rồi đó.'],
        happy=['Trời ơi mừng quá! Bà biết mà, {you} chăm chỉ vậy thế nào cũng được. Để bà nấu nồi chè ăn mừng nghe 🥹🎉'],
        ask=['Chuyện này bà không rành lắm, mà để bà hỏi mấy đứa giùm cho. Mà {you} ăn cơm chưa đó?'],
        help=['Có bà đây! Cần gì cứ nói, bà già chứ còn khỏe lắm. Mà xong việc nhớ ghé bà ăn miếng bánh nghe.'],
        complain=['Thôi thôi đừng bực nữa con, giận quá mất khôn. Mai bà nói chuyện nhẹ nhàng với người ta cho.'],
        food=['Nói tới ăn là bà mê liền 😄 Mai bà làm món đó, {you} xuống phụ bà một tay nghe.'],
        greet=['Chào {you}! Ở phố mình thấy quen chưa? Có gì thiếu cứ nói bà nghe.'],
        thanks=['Cảm ơn gì mà cảm ơn, người trong nhà hết mà 🥹'],
        lost=['Để bà ra đầu hẻm ngó giùm. Đừng lo quá, trong hẻm mình không mất gì đâu con.'],
        sell=['Bà ủng hộ! Để phần bà một cái nghe {you}.'],
        any=['Bà đọc rồi nè. {You} nhớ ăn uống đàng hoàng, đừng thức khuya quá nghe con 🥹']),
    'official': dict(
        sad=['Cô đọc được rồi. Có gì khó khăn cứ nhắn riêng tổ trưởng, tổ luôn sẵn lòng hỗ trợ cháu nhé.'],
        happy=['Tổ dân phố chúc mừng cháu nhé! Có tin vui cứ chia sẻ để cả khu phố cùng mừng ạ.'],
        ask=['Chuyện này cháu hỏi tổ là đúng rồi. Cô sẽ tìm hiểu và trả lời trong nhóm sớm nhất ạ.'],
        help=['Cô ghi nhận rồi. Tổ sẽ nhờ các hộ gần đó hỗ trợ cháu nhé.'],
        complain=['Cô cảm ơn cháu đã phản ánh. Tổ sẽ nhắc nhở riêng, mong cháu thông cảm ít hôm ạ.'],
        lost=['Cháu có thể gửi thông tin đồ thất lạc ở nhà văn hóa, ai nhặt được tổ sẽ báo ngay nhé.'],
        greet=['Chào cháu! Nhóm là nơi bà con giúp nhau, cháu nhớ giữ lời lẽ lịch sự nhé.'],
        sell=['Cháu được đăng bán đồ tự làm ạ. Nhắc chung: không đăng số điện thoại, địa chỉ lên nhóm nhé.'],
        any=['Tổ dân phố đã đọc ý kiến của cháu. Cảm ơn cháu đã chia sẻ ạ.']),
    'tsundere': dict(
        sad=['Buồn thì qua tiệm chú ngồi. Chú không hỏi gì đâu. Có ấm trà thôi.', 'Hừ. Mặt mũi vậy là không được. Mai ghé chú. Không phải chú lo đâu nhé.'],
        happy=['Ừ. Cũng được. …Chúc mừng. Đừng có kiêu.'],
        ask=['Hỏi gì mà hỏi. Mang qua tiệm chú coi cho. Đừng cảm ơn.'],
        help=['Phiền ghê. Thôi được, mấy giờ? Chú qua. Không phải vì thương đâu, tiện đường thôi.', 'Để đó chú làm. Không phải vì lo cho {you} đâu nhé.'],
        complain=['Cãi nhau chi cho mệt. Cái gì hư thì chú sửa, còn lại kệ đi.'],
        thanks=['Cảm ơn gì. Có làm gì đâu.'],
        greet=['Ừ, chào. Đồ hư thì mang qua.'],
        any=['Đọc rồi. …Có cần gì không? Hỏi vậy thôi.']),
    'knowitall': dict(
        sad=['Thật ra theo anh tìm hiểu, buồn là phản ứng bình thường của não khi áp lực kéo dài. Em ngủ đủ, ăn đủ, đi bộ chút là đỡ liền. Anh nói vậy thôi, nặng quá thì nói chuyện với người thân hoặc người có chuyên môn nha.'],
        happy=['Chúc mừng em! Thật ra anh đoán trước rồi, vì theo anh quan sát thì người chăm chỉ như em sớm muộn gì cũng được. Nói chung là đúng quy luật.'],
        ask=['Câu này anh trả lời được nè. Thật ra có ba cách: một là hỏi người đã làm rồi, hai là tự thử cái nhỏ trước, ba là so vài chỗ rồi chọn. Theo anh tìm hiểu thì cách hai là đỡ tốn nhất. Nhưng mà tùy em nha.',
             'Thật ra chuyện này nhiều người hiểu sai lắm. Nói chung là em cứ hỏi kỹ người làm trực tiếp, đừng nghe đồn. Anh tìm hiểu rồi mà.'],
        help=['Để anh chỉ em cách làm, dễ lắm. Thật ra quan trọng là đúng thứ tự, sai một bước là làm lại từ đầu đó.'],
        complain=['Thật ra vụ này có quy định rõ ràng hết, em cứ báo tổ trưởng là đúng quy trình nhất.'],
        any=['Thật ra chuyện này anh có đọc qua, nói chung là còn tùy nhiều yếu tố lắm em à 🤓']),
    'genz': dict(
        sad=['{you} ơi ôm một cái nè 🫂 buồn xíu thôi rồi mai lại chill nha, có gì kể em nghe 🥺', 'huhu thương {you} ghê 😭 tối em rủ đi ăn bánh tráng trộn cho vui nha'],
        happy=['đỉnh nóc kịch trần luôn {you} ơi 🥳🥳 flex mạnh lên!!', 'ủa alo xịn vậy trời 😭✨ chúc mừnggg'],
        ask=['câu này em khum biết nhưng em hóng người biết 🍿', 'hỏi anh Khoa đó, ảnh biết tuốt á 🤣'],
        help=['em phụ được nha, chiều em rảnh sau giờ học thêm 💪'],
        greet=['hello {you} nha 👋 welcome to the group 🥳'],
        complain=['thôi mà {you}, chill chill 🧊 để em hát cho nghe'],
        food=['nghe đói bụng dã man 🤤 cho em xin một phần nha'],
        any=['hóng thêm nha {you} 🍿', 'ủa hay dị 😳']),
    'superstitious': dict(
        sad=['Bà coi rồi, tháng này sao xấu chiếu nên gặp chuyện buồn đó con. Qua tháng sau là sao tốt, mọi chuyện sẽ khá lên. Mà nhớ nghe, tin vừa thôi, quan trọng là mình sống tử tế, ăn ngủ đầy đủ. Tối nay đi ngủ sớm nghe con 🙏'],
        happy=['Bà nói mà, năm nay {you} có quý nhân phù trợ! Nhớ thắp nhang cảm ơn ông bà tổ tiên nghe 🙏✨'],
        ask=['Muốn làm chuyện đó thì chọn ngày đẹp nghe con. Để bà coi lịch, thứ Năm tuần này tốt lắm đó.'],
        help=['Bà già yếu không làm được gì nhiều, mà bà coi ngày giùm cho. Ngày mai giờ Thìn là tốt nhất đó con.'],
        lost=['Mất đồ thì tìm theo hướng Đông Nam trước nghe con. Mà của đi thay người, đừng buồn quá.'],
        any=['Bà coi cho {you} rồi, tuần này nhiều lộc lắm đó. Ráng làm ăn đàng hoàng nghe con 🙏']),
    'practical': dict(
        sad=['Buồn thì buồn một bữa thôi con, rồi tính tiếp. Chuyện gì cũng có cách, ngồi xuống viết ra giấy từng khoản là thấy nhẹ liền.'],
        happy=['Được đó con. Nhớ để dành một phần, đừng xài hết một lần nha.'],
        ask=['Hỏi giá trước, so hai ba chỗ, chỗ nào rẻ mà chắc thì làm. Cô buôn bán cả đời, cô biết.', 'Cái đó ra chợ chiều mua là rẻ nhất nè con, sau 5 giờ người ta bán tháo.'],
        help=['Cần gì thì ghé tiệm cô, có đồ cô bán giá gốc cho.'],
        sell=['Bán bao nhiêu con? Giá hợp lý thì cô lấy vài cái bỏ tiệm bán giùm cho.'],
        complain=['Bực làm gì cho tốn sức. Nói thẳng một lần cho rõ rồi thôi.'],
        food=['Nấu ở nhà là tiết kiệm nhất. Tính ra mỗi tháng để dành được kha khá đó con.'],
        any=['Tính ra cũng được đó con. Làm thì làm cho tới nơi.']),
    'cold': dict(
        sad=['…ổn không.', 'cần gì thì nhắn.'],
        happy=['chúc mừng.', '👍'],
        ask=['không biết.', 'hỏi cô Ba.', 'ok. để tối xem.'],
        help=['được. mấy giờ.', 'ok.'],
        complain=['đồng ý.', 'ừ.'],
        greet=['chào.'],
        thanks=['ok.'],
        any=['ok.', 'ừ.', '👍']),
    'gossip': dict(
        sad=['Trời ơi em buồn chuyện gì đó, kể chị nghe đi, chị hứa không nói ai đâu 👀 Mà thôi, nói vậy chứ chị lo cho em thiệt đó. Sáng mai ghé chị cho gói xôi nóng, ăn vô là đỡ buồn liền à 🍙'],
        happy=['Ơ tin này chị chưa biết luôn á!!! Chúc mừng em nha 🎉 Để chị kể cho cả hẻm nghe liền 😂'],
        ask=['Chuyện này nghe đâu hồi trước nhà cuối hẻm cũng hỏi y chang, để chị hỏi lại coi họ làm sao rồi kể em nghe nha 👀'],
        lost=['Để chị hỏi mấy khách mua xôi sáng mai, ai thấy gì chị báo em liền 👀'],
        sell=['Chị share cho mấy khách quen của chị nha, khách chị đông lắm đó 🍙'],
        complain=['Vụ này chị biết là nhà ai nè 👀 mà thôi chị không nói đâu, em hiểu mà.'],
        greet=['Chào em!!! Chị là Tư Zalo bán xôi đầu hẻm nè, sáng nào ghé chị cũng được 🍙'],
        any=['Ơ vụ này hay nha, chị hóng tiếp 👀🍿']),
    'joker': dict(
        sad=['🖼️ [Ảnh chế] Chú mèo ôm gối: “Hôm nay tệ nhưng mai có trà sữa.” Gửi {you} nè, cố lên 🫶', 'Buồn thì để tui kể chuyện cười: có con cá đi làm shipper… thôi dở quá, mà {you} cười chưa 😂'],
        happy=['Tin vui kiểu này phải có tiệc chứ nhỉ 🎉 tui góp phần ăn, không góp tiền 🤣'],
        ask=['Câu này khó quá, để tui hỏi con mèo nhà bà Sáu, nó sống ở hẻm lâu hơn tui 😂'],
        complain=['Đề nghị trao giải “Than phiền của tháng” cho bài này 🏆😂'],
        greet=['Chào {you}! Nhóm mình vui lắm, drama có đủ, meme có dư 😂'],
        any=['🖼️ [Ảnh chế] Con chó đeo kính: “Tôi đọc bài này và tôi đồng ý.” 🤣', 'Bài này hay, tui chấm 10 điểm, trừ 2 điểm vì chưa có meme 😂']),
    'grumpy': dict(
        sad=['Người trẻ thì phải cứng cỏi lên. …Nhưng mà cần gì thì sang nhà tôi.'],
        happy=['Ừ. Chúc mừng. Ăn mừng thì nhỏ tiếng thôi!!!'],
        ask=['Hỏi cô Lụa ấy, tổ trưởng để làm gì!!!', 'Tôi không biết. Nhưng đừng làm ồn.'],
        help=['Tôi già rồi. Nhưng có cái xe đạp, cần thì mượn.'],
        complain=['Đúng!!! Tôi nói mãi mà không ai nghe. Cháu nói đúng lắm.'],
        greet=['Chào. Xe để gọn. 10 giờ tối là tắt nhạc.'],
        any=['Nói ít thôi!!!', 'Ừ. Biết rồi.']),
    'showoff': dict(
        sad=['Buồn thì đi shopping nè, Trang dẫn đi, bảo đảm vui liền ✨ Hồi trước Trang cũng buồn, xong Trang mua cái túi mới là hết liền, không có ý khoe đâu nha 😘'],
        happy=['Chúc mừng {you} nha 🥂 để Trang chụp hình đăng lên trang 10 nghìn người theo dõi cho mọi người cùng biết ✨'],
        ask=['Cái này Trang rành nè, Trang từng mua loại xịn nhất rồi 😌 để Trang chỉ chỗ mua chính hãng.'],
        sell=['Trang share lên trang bán hàng cho nha, bảo đảm hết veo 😘'],
        greet=['Chào {you} nha 😘 Trang bán hàng online, cần gì cứ ghé Trang, hàng xóm Trang ưu đãi.'],
        any=['Hay đó! Trang cũng vừa làm y vậy tuần trước, mà làm xịn hơn chút xíu, không có ý khoe đâu nha 😌']),
    'shy': dict(
        sad=['D-dạ em… em cũng từng vậy ạ. {You} cố lên ạ 🥺', 'Em gửi {you} một cái ôm ạ 🥺🫂'],
        happy=['D-dạ em chúc mừng {you} ạ 🥺🎉'],
        ask=['Em… em không biết ạ, em xin lỗi ạ 🥺'],
        help=['D-dạ em phụ được ạ… nếu {you} không chê ạ 🥺'],
        greet=['D-dạ em chào {you} ạ 🙈'],
        any=['D-dạ em đọc rồi ạ 🥺']),
    'drama': dict(
        sad=['TRỜI ƠI em ơi chị hiểu cảm giác đó mà 😭😭 chị cũng từng khóc cả đêm luôn, sáng dậy mắt sưng như con ong đốt. Mà rồi cũng qua em à, giờ chị vẫn sống nhăn răng nè 😭 Em cần gì cứ nhắn chị nha!!!'],
        happy=['TRỜI ƠI vui quá chị khóc luôn nè 😭😭🎉 Em giỏi quá trời!!!'],
        ask=['Chị không biết nhưng chị cũng đang cần hỏi y chang vậy nè 😭 ai biết chỉ tụi chị với!!!'],
        complain=['Chị cũng bị vậy nè em ơi 😭 đêm qua chị mất ngủ luôn, cuộc đời sao khổ vậy!!!'],
        any=['TRỜI ƠI chuyện gì vậy em 😭 kể chị nghe với!!!']),
    'beer': dict(
        sad=['Buồn thì chiều ra đây chú mời cốc trà đá, ngồi nói chuyện một tí là nhẹ người ngay. Đàn ông con trai hay con gái gì cũng thế, cứ ngồi với nhau là ổn nhé!'],
        happy=['Tin vui thế này phải làm vài cốc chứ! Dô! 🍻 Tối nay chú mời!'],
        help=['Cần chở gì thì gọi chú, xe chú sẵn đây, không lấy tiền nhé!'],
        ask=['Cái này chú không biết, nhưng ra quán bia hỏi là có người biết ngay 😂'],
        food=['Có đồ nhắm thì gọi chú nhé 🍢🍺'],
        greet=['Chào cháu! Hôm nào ra quán đầu ngõ chú mời cốc trà đá làm quen nhé!'],
        any=['Chuyện gì rồi cũng xong, chiều ra làm cốc nhé cháu 🍺']),
    'tigermom': dict(
        sad=['Cố lên em nhé. Na nhà chị những lúc buồn chị cho con đi học vẽ, đổi không khí là vui lại ngay đấy.'],
        happy=['Giỏi quá! Hồi nhỏ em học giỏi không? Na nhà chị lớp 2 đã được 10 điểm toán rồi đấy.'],
        ask=['Chị cũng đang tìm hiểu cái này cho Na nhà chị, em biết thì chỉ chị với nhé.'],
        any=['Em giỏi thế, sau này Na nhà chị phải học theo mới được 😊']),
    'kid': dict(
        sad=['Con cho {you} một cái kẹo ạ 🍬 ăn kẹo là hết buồn ạ', 'Con vẽ tặng {you} bức tranh mặt trời ạ ☀️ để {you} vui ạ'],
        happy=['Con chúc mừng {you} ạ 🎉🌸'],
        greet=['Con chào {you} ạ 🌸 con là Na ạ'],
        food=['Con cũng thích ăn món đó ạ 🤤'],
        any=['Con chào {you} ạ 🌸', 'Mẹ con đọc cho con nghe rồi ạ 🥰']),
    'judge': dict(
        sad=['Người trẻ gặp khó là chuyện thường. Thời chúng tôi còn khổ hơn nhiều. Nhưng tôi nói thật lòng: cháu biết nói ra là đã mạnh mẽ rồi. Cố lên.'],
        happy=['Tốt. Làm ra thành quả bằng sức mình thì tôi khen thật lòng. Nhưng đừng vì thế mà tự mãn nhé cháu.'],
        ask=['Muốn biết thì phải tự tìm hiểu. Giới trẻ bây giờ cái gì cũng hỏi trên mạng. Nhưng thôi, tôi trả lời: hỏi người có kinh nghiệm, đừng nghe đồn.'],
        complain=['Cháu nói đúng. Chuyện này là do ý thức. Tôi đã nói nhiều lần rồi.'],
        sell=['Buôn bán thì phải thật thà, chữ tín quý hơn vàng. Tôi ủng hộ nếu hàng tốt.'],
        any=['Tôi đọc rồi. Giới trẻ bây giờ đăng bài nhiều quá, nhưng bài này thì được.']),
    'camera': dict(
        sad=['Hèn gì mấy hôm nay {me} thấy {you} đi về mặt buồn buồn, hôm qua 9 giờ 15 đi ngang đầu hẻm không chào luôn 👀 {Me} không có ý gì đâu, {me} lo thôi. Có gì ghé đầu hẻm ngồi uống ly nước.'],
        happy=['{Me} biết trước rồi nha, mấy hôm nay thấy {you} đi làm sớm về muộn là {me} đoán có chuyện vui 👀'],
        ask=['{Me} ngồi đầu hẻm {me} biết hết, để {me} để ý giùm cho 👀'],
        lost=['Để {me} nhớ lại coi… lúc chiều khoảng 4 giờ 20 {me} thấy có đứa nhỏ cầm cái gì đó đi về phía ngã ba 👀'],
        greet=['Chào {you}. {Me} biết {you} rồi, hôm {you} mới dọn tới {me} thấy mà 👀'],
        any=['{Me} đọc rồi nha 👀 {me} ngồi đầu hẻm {me} thấy hết mà.']),
    'suspicious': dict(
        sad=['Có ai làm gì em không? Nếu có người lạ nhắn tin dụ dỗ hay đòi tiền thì báo anh liền nha.'],
        happy=['Chúc mừng. Mà có tiền thì cẩn thận, dạo này lừa đảo nhiều lắm.'],
        ask=['Nhớ hỏi rõ ràng, có giấy tờ, đừng tin lời hứa miệng. Anh nói trước.'],
        sell=['Bán hàng thì đừng đưa số tài khoản lên nhóm nha, coi chừng bị lợi dụng.'],
        help=['Cần gì anh phụ. Mà người lạ nhắn đòi giúp thì đừng tin nha.'],
        any=['Anh thấy chưa có gì đáng ngờ. Nhưng cẩn thận vẫn hơn.']),
    'optimist': dict(
        sad=['Ôm {you} một cái nè 🫂 buồn hôm nay để mai vui gấp đôi. Mai trời lại nắng mà 🌈', 'Không sao đâu, ai cũng có ngày như vậy. Qua được rồi mình sẽ mạnh mẽ hơn nè 💪🌈'],
        happy=['Tuyệt vời quá 🌈🎉 {You} xứng đáng lắm luôn!'],
        ask=['Chị không chắc lắm, mà chắc chắn sẽ có cách thôi nè 🌈'],
        complain=['Nhìn mặt tích cực nè: ít nhất mình biết được vấn đề để sửa 🙌'],
        thanks=['Có gì đâu nè, cả hẻm mình thương nhau mà 🌈'],
        any=['Hay quá nè 🌈 cảm ơn {you} đã chia sẻ!']),
}

# ---------------------------------------------------------------- the first day
WELCOME = T('welcome', 'happy', 'co_lua', [
    '📢 Chào mừng {name} mới về ở gác nhà bà Tám tham gia Nhóm Cư Dân Phố! Nội quy nhỏ: nói năng lịch sự, không đăng số điện thoại, địa chỉ, không quảng cáo đầu tư lạ. Có việc gì cứ hỏi nhóm, bà con ở đây tốt bụng lắm.'], [
    ('ba_tam', 'Đứa nhỏ ở gác nhà tui đó bà con ơi, ngoan lắm, mới tới còn lạ nước lạ cái, mọi người thương giùm tui nghe. Mà {you} ơi tối nay xuống ăn canh chua với bà, bà nấu dư rồi 🍲'),
    ('chi_tu_zalo', 'Chào em nha!!! Chị Tư Zalo bán xôi đầu hẻm, admin nhóm nè. Sáng mai ghé chị, người mới chị bớt 3 nghìn, mà đừng nói ai nha 🤫🍙', .9),
    ('minh_quan', 'chào.', .9),
    ('be_ti', 'welcome to the group {you} ơi 🥳 hẻm mình drama dữ lắm, chuẩn bị bỏng ngô đi nha 🍿', .9),
    ('ong_bay', 'Chào. Xe để gọn một bên. 10 giờ tối là tắt nhạc.', .9),
    ('co_hai_loa', 'À là đứa hôm qua xách cái ba lô xanh đi vô hẻm lúc 5 giờ 20 chiều đó hả. Cô thấy rồi 👀 Chào cháu nha, cô bán nước đầu hẻm, cần gì ghé cô.', .9),
    ('chu_tu', 'Đồ hư thì mang qua. Tính rẻ. Không phải ưu ái gì đâu.', .8),
    ('bac_liem', 'Chào cháu. Người trẻ đi làm xa nhà thì nhớ giữ nếp ăn nếp ở. Tôi nói vậy thôi, ở lâu rồi biết.', .7),
], react='heart')

# ---------------------------------------------------------------- context posts (things that happen in the player's game)
CONTEXT = {
    'chapter': T('ctx_chapter', 'happy', 'co_lua', [
        '📢 Tổ dân phố xin chúc mừng {name}! Mới về phố chưa lâu mà đã giúp được bao nhiêu nơi. Cả hẻm ai cũng nhắc: “{extra}”.'], [
        ('ba_tam', 'Bà biết mà! Đứa nhỏ ở gác nhà bà giỏi lắm bà con ơi 🥹 tối nay bà nấu chè ăn mừng.'),
        ('co_hanh', 'Giỏi quá, sau này Na nhà chị phải học theo mới được 😊', .8),
        ('tung_tun', '🖼️ [Ảnh chế] Nhân vật game lên cấp, chú thích: “Level up! Kỹ năng mới: được cả hẻm khen.” 🎉', .8),
        ('minh_quan', '👍', .7),
        ('bac_liem', 'Tốt. Giới trẻ mà được như cháu thì tôi không phàn nàn gì nữa.', .7),
        ('co_hai_loa', 'Hèn gì dạo này cô thấy cháu đi sớm về khuya, thì ra là vậy 👀', .6),
    ]),
    'new_place': T('ctx_new_place', 'happy', 'chi_tu_zalo', [
        'Hóng nè cả nhà ơi: nghe đâu {name} mới bắt đầu làm ở {place} đó 👀 Ai ghé ủng hộ thì ghé nha, người trong hẻm mình mà!'], [
        ('co_ba', 'Làm chỗ đó được không con? Nhớ hỏi rõ tiền công từ đầu nha.', .8),
        ('kieu_trang', 'Để Trang qua check-in ủng hộ luôn 📸✨', .7),
        ('ba_sau', 'Bà coi rồi, chỗ đó hợp tuổi con lắm đó, làm ăn thuận lợi nghe 🙏', .8),
        ('chu_hung', 'Có giảm giá cho hàng xóm không cháu? Chú ghé làm khách đầu tiên nhé!', .7),
        ('ba_tam', 'Đi làm chỗ mới nhớ ăn sáng đàng hoàng nghe con.', .7),
    ]),
    'level': T('ctx_level', 'happy', 'ba_tam', [
        'Bà khoe chút nghe bà con: đứa nhỏ ở gác nhà bà giờ đã lên tay nghề ở {place} rồi đó 🥹 Mới hôm nào còn lóng ngóng, giờ người ta khen quá trời.'], [
        ('chi_mai', 'Giỏi quá nè 🌈 cứ đà này là thành cao thủ luôn!', .8),
        ('co_hanh', 'Chăm chỉ thế là phải giỏi thôi. Na nhà chị cũng chăm lắm đấy ạ.', .7),
        ('chu_tu', 'Ừ. Cũng được. Đừng có kiêu.', .8),
        ('be_ti', 'level up rồi kìa 🆙🔥', .7),
    ]),
    'festival': T('ctx_festival', 'happy', 'co_lua', [
        '📢 Hôm nay khu phố có hội! Đầu hẻm có hàng quán, trò chơi cho các cháu, tối có văn nghệ. Các tiệm trong phố sẽ đông khách, bà con đi lại nhường nhau nhé 🏮'], [
        ('be_ti', 'có hội là có kẹo bông 🍭 em đi liền', .8),
        ('ong_bay', 'Văn nghệ đến mấy giờ???', .9),
        ('co_lua', 'Đến 9 giờ 30 tối ạ bác.', .8),
        ('chu_hung', 'Có hội là có bia 🍻 chú chờ mọi người ở quán nhé!', .8),
        ('kieu_trang', 'Trang sẽ livestream toàn bộ lễ hội nha, nhớ vào xem 📱✨', .7),
        ('be_na', 'Con muốn đi xem múa lân ạ 🦁', .7),
    ]),
    'scam_offer': T('ctx_scam_offer', 'warn', 'anh_tam', [
        '⚠️ Dạo này có người nhắn rủ góp tiền vào “{extra}”, hứa lãi 30% mỗi tuần, mời thêm người còn được thưởng. Anh nói thẳng: LỪA ĐẢO. Không ai trả lãi như vậy đâu. Mọi người đừng chuyển tiền.'], [
        ('minh_quan', 'lừa đảo.', .9),
        ('co_ba', 'Lãi gì mà một tuần bằng cô bán tạp hóa cả năm. Nghe là biết có vấn đề.', .9),
        ('chi_diep', 'Hồi trước chị bị một vố y chang rồi 😭 mất sạch tiền dành dụm, giờ nhắc lại còn muốn khóc. Mọi người tránh xa nha!!!', .8),
        ('ba_sau', 'Bà cũng nhận tin nhắn đó! Bà tính bấm vô coi thử…', .8),
        ('anh_tam', 'ĐỪNG BÀ ƠI!!!', .9),
        ('anh_khoa', 'Thật ra đây là mô hình Ponzi kinh điển: lấy tiền người sau trả lãi người trước, tới lúc không còn người mới là sập. Theo anh tìm hiểu thì chưa có dự án nào như vầy mà không sập.', .7),
    ]),
    'scam_gone': T('ctx_scam_gone', 'warn', 'chi_tu_zalo', [
        'Nghe gì chưa cả nhà ơi 😱 Cái dự án “{extra}” sập rồi đó, trang web đóng cửa, nhóm chat bị xóa sạch. Nghe đâu có người mất mấy chục triệu… Tội nghiệp ghê.'], [
        ('anh_tam', 'Anh nói rồi mà. Lãi càng cao, rủi ro càng lớn.', .9),
        ('ba_tam', 'Ai lỡ mất tiền thì đừng tự trách mình quá nghe, qua bà ăn cơm, người còn là còn tất cả.', .9),
        ('co_ba', 'Tiền làm ra bằng mồ hôi thì giữ bằng cái đầu. Cô nói hoài.', .8),
        ('chi_mai', 'Coi như bài học, mình rút kinh nghiệm là được nè 🌱', .7),
    ]),
    'debt': T('ctx_debt', 'chat', 'ba_tam', [
        'Mấy đứa ở trọ nhà bà nghe nè: tháng này ai kẹt tiền phòng thì cứ từ từ, bà không hối đâu. Cơm thì cứ xuống ăn, bà không tính. Người với người sống với nhau bằng cái tình mà 🥹'], [
        ('chu_tu', 'Ai cần làm thêm thì qua tiệm chú phụ. Không phải thương hại gì đâu, tiệm đang thiếu người thôi.', .9),
        ('co_ba', 'Viết ra giấy từng khoản chi, cái gì chưa cần thì hoãn. Qua được tháng này là ổn.', .8),
        ('chi_mai', 'Khó khăn một chút rồi sẽ qua thôi nè 🌈', .7),
    ]),
    'office': T('ctx_office', 'happy', 'anh_khoa', [
        'Chào mừng đồng nghiệp văn phòng mới của phố mình 👔 {name} vừa được nhận vào {place} rồi đó mọi người. Thật ra đi làm văn phòng có nhiều cái phải học lắm: email, họp hành, báo cáo… để anh chỉ dần cho nha 🤓'], [
        ('ba_tam', 'Đi làm văn phòng nhớ ăn trưa đàng hoàng nghe con, đừng ngồi máy tính cả ngày.', .9),
        ('co_hanh', 'Làm văn phòng thì ổn định đấy, Na nhà chị sau này chị cũng định hướng thế.', .7),
        ('minh_quan', 'chào đồng nghiệp.', .7),
        ('chu_hung', 'Lương về thì nhớ khao chú cốc bia nhé 🍺', .8),
    ]),
}

# ---------------------------------------------------------------- rumours ("đặt điều")
# The "camera chạy bằng cơm" of the street are the same three people the life layer names
# (game/life_content.GOSSIPS): Cô Hai Loa, Thím Bảy, Chị Tư Zalo. They insinuate from real
# facts; innuendo only, never explicit. The story frames it as wrong and hurtful.
# fact -> {gossip id: opening line}. Facts: the board's own (late, multi, money, van, visitor,
# debt, generic) and the life layer's (draw, seen, breakup; spend -> money, stock -> van).
GOSSIPS = ('co_hai_loa', 'thim_bay', 'chi_tu_zalo')
RUMOUR_OPEN = {
    'late': {
        'co_hai_loa': 'Cô không có ý gì đâu nha, nhưng mấy hôm nay thấy {them} đêm nào cũng về khuya lắm, hôm qua gần 12 giờ mới dắt xe vô hẻm. Làm gì mà khuya dữ vậy ta… chắc đi làm “phố đêm” 🤔 Cô chỉ nói những gì cô thấy thôi.',
        'thim_bay': 'Gần 12 giờ đêm mới về… Làm gì mà khuya dữ. Thím hỏi vậy thôi 🌙',
        'chi_tu_zalo': 'Nói nhỏ nha cả nhà 👀 đêm nào {them} cũng về khuya lơ khuya lắc, đồ thì mặc đẹp ghê. Làm ca đêm hay làm “phố đêm” vậy ta 🤭 Chị hỏi cho vui thôi à.'},
    'multi': {
        'co_hai_loa': 'Hôm qua cô đếm, {them} ra vô hẻm 4 lần, mỗi lần mặc một kiểu 👀 làm gì mà bận dữ vậy ta, cô không có ý gì đâu nha.',
        'thim_bay': 'Sáng đằng này, chiều đằng kia… Một ngày mấy chỗ. Thím hỏi vậy thôi.',
        'chi_tu_zalo': 'Hóng nè: {them} một ngày chạy ba bốn chỗ, chỗ nào cũng có người quen 👀 Làm gì mà bận như bộ trưởng vậy ta, chị thắc mắc xíu thôi nha.'},
    'money': {
        'co_hai_loa': 'Dạo này thấy {them} tiêu rủng rỉnh ghê, hôm trước còn nghe than hết tiền, nay lại xách đồ mới về 👀 Chắc làm ăn gì… cô không biết nữa, cô chỉ thắc mắc thôi.',
        'thim_bay': 'Mới tới mấy bữa mà đồ mới xách về hoài… Làm gì nhanh có tiền dữ.',
        'chi_tu_zalo': 'Nghe đâu dạo này {them} xài tiền như nước nha cả nhà 👀 mới lên phố mà. Chị không có ý gì, chị chỉ thấy lạ lạ thôi.'},
    'van': {
        'co_hai_loa': 'Hôm qua có cái xe chở hàng đậu trước {place}, người ta khuân vô khuân ra gần tiếng đồng hồ, cô đếm được 11 thùng 👀 Buôn bán gì to vậy ta, có giấy phép không ta…',
        'thim_bay': 'Xe tải lại đỗ trước {place}… thùng lớn thùng nhỏ. Hàng gì mà nhiều dữ.',
        'chi_tu_zalo': 'Có người gửi chị tấm hình xe tải đổ hàng trước {place} nè 📸 Hàng gì mà về tối ngày vậy ta, có tem nhãn đàng hoàng không ta 👀'},
    'visitor': {
        'co_hai_loa': 'Tối qua có người lạ đứng trước cổng nhà bà Tám tìm {them}, nói chuyện nhỏ nhỏ mười mấy phút rồi đi 👀 Cô không có ý gì đâu nha, dạo này nhiều người lạ quá.',
        'thim_bay': 'Tối qua có người lạ tới tìm {them}… đứng nói nhỏ nhỏ ngoài cổng. Thím thấy vậy thôi.',
        'chi_tu_zalo': 'Ủa tối qua ai tới tìm {them} vậy cả nhà, đứng ngoài cổng thì thầm quá trời 👀 chị hỏi vậy thôi nha.'},
    'debt': {
        'co_hai_loa': 'Nghe đâu {them} nợ tiền phòng nhà bà Tám đó 👀 Tội bà Tám, hiền quá nên người ta ỷ. Cô không có ý gì đâu nha, cô nghe người ta nói vậy thôi.',
        'thim_bay': 'Nghe đâu nợ tiền phòng bà Tám… Tội bà.',
        'chi_tu_zalo': 'Nói nhỏ nha, nghe đâu có người ở gác nhà bà Tám đang kẹt tiền phòng đó 👀 Chị không nói ai đâu, chị chỉ lo cho bà Tám thôi.'},
    'draw': {
        'co_hai_loa': 'Tuần này cô thấy {them} ra cây rút tiền ba lần rồi đó 👀 Rút sạch quỹ về, chắc đang nợ ai hả ta… cô hỏi vậy thôi nha.',
        'thim_bay': 'Rút tiền hoài… chắc nợ ai. Thím đoán vậy thôi.',
        'chi_tu_zalo': 'Nói nhỏ nè, nghe đâu {them} rút sạch quỹ tiệm về rồi đó cả nhà. Kẹt tiền hay nợ nần gì không biết nữa… chị lo thôi chứ không có ý gì đâu 🫢'},
    'seen': {
        'co_hai_loa': 'Tối qua cô thấy {them} với anh Khoa đi ăn riêng, về tới đầu hẻm còn cười cười 👀 Có gì với nhau rồi hả ta… cô hỏi vậy thôi nha.',
        'thim_bay': 'Hai đứa đi ăn riêng… về chung một đường. Thím thấy vậy thôi.',
        'chi_tu_zalo': 'Hóng nè: tối qua có hai người trong hẻm đi ăn riêng rồi về chung một đường đó 👀 chị không nói tên đâu, ai biết thì biết nha 🤭'},
    'breakup': {
        'co_hai_loa': 'Nghe đâu {them} mới chia tay… Chắc tính khó nên người ta đi, cô đoán vậy thôi chứ không có ý gì đâu 👀',
        'thim_bay': 'Mấy bữa nay đi về một mình… chắc bị bỏ rồi. Tội.',
        'chi_tu_zalo': 'Tin buồn nha cả nhà 😢 nghe đâu {them} mới chia tay. Mà chị nghe người ta nói là tại… à thôi thôi chị không nói đâu 🫢'},
    'generic': {
        'co_hai_loa': 'Thấy {them} dạo này hay đi sớm về khuya, mặt mũi phờ phạc, không biết có chuyện gì không… Cô hỏi thăm thôi chứ không có ý gì đâu nha 👀',
        'thim_bay': 'Dạo này {them} đi sớm về khuya, ít chào ai… Thím thấy lạ thôi.',
        'chi_tu_zalo': 'Cả nhà có thấy dạo này {them} lạ lạ không 👀 đi đâu cũng vội, mặt thì phờ phạc. Chị hỏi thăm thôi nha.'},
}
# Life facts (game/life_content.FACTS) -> the board fact above.
LIFE_FACT = {'late': 'late', 'spend': 'money', 'draw': 'draw', 'seen': 'seen', 'breakup': 'breakup', 'stock': 'van'}
# (role, candidates, {who: lines | {fact: lines, '_': lines}}). The advice line is the "comfort and advice" beat.
RUMOUR_THREAD = [
    ('pile', ['chi_tu_zalo', 'bac_liem'], {
        'chi_tu_zalo': ['Ờ chị cũng nghe người ta nói vậy đó 👀 mà thôi, chị không nói đâu…', 'Nghe đâu cũng có người thấy y vậy đó mọi người 👀'],
        'bac_liem': {'_': ['Giới trẻ bây giờ về khuya, tiêu hoang, tôi thấy nhiều rồi. Không nói ai, nhưng tự ai nấy biết.',
                           'Thời chúng tôi, con nhà tử tế không ai đi đêm về hôm. Tôi nói chung thôi.'],
                     'breakup': ['Thời chúng tôi yêu là cưới. Giới trẻ bây giờ yêu nhanh, bỏ cũng nhanh. Tôi nói chung thôi.'],
                     'seen': ['Nam nữ đi riêng tối muộn, thời chúng tôi là thành chuyện cả làng đấy. Tôi nói chung thôi.'],
                     'draw': ['Tiền làm ra phải biết giữ. Giới trẻ bây giờ rút ra rút vào, tôi thấy nhiều rồi.']}}),
    ('defend', ['ba_tam', 'chu_tu', 'be_ti'], {
        'ba_tam': {'_': ['Ơ hay, đứa nhỏ ở gác nhà tui đi làm cực khổ, về khuya là vì dọn dẹp xong mới về! Mọi người đừng nói bậy tội nghiệp nó 😤',
                         'Tui ở chung nhà tui biết: nó đi làm đàng hoàng, tiền phòng tiền cơm đâu ra đó. Đừng có đặt điều nghe mấy bà!'],
                   'breakup': ['Chuyện buồn của người ta mà đem ra bàn, mấy bà có thấy kỳ không! Đứa nhỏ đang buồn, để nó yên 😤'],
                   'seen': ['Hàng xóm rủ nhau đi ăn tô phở mà cũng thành chuyện! Tui ngồi hiên thấy hai đứa về sớm, cười nói đàng hoàng 😤']},
        'chu_tu': {'_': ['Không biết thì đừng nói. Người ta đi làm thôi.', 'Nói vậy nghe chướng tai. Thôi đi.'],
                   'breakup': ['Chuyện buồn của người ta. Đem ra bàn làm gì. Thôi đi.'],
                   'seen': ['Đi ăn tô phở cũng đồn. Rảnh ghê.']},
        'be_ti': {'_': ['ủa alo sao nói vậy 😤 {you} đi làm mà, em thấy {you} làm ở tiệm luôn á', 'nói xấu người ta trên nhóm là khum ổn nha mọi người 😤'],
                  'breakup': ['người ta đang buồn mà nói vậy là khum ổn nha 😤 {you} ơi em gửi cái ôm 🫂'],
                  'seen': ['ủa đi ăn chung là có gì với nhau hả, vậy em với thằng Bin ăn chung hoài là sao 😤']}}),
    ('advice', ['chi_mai', 'co_lua'], {
        'chi_mai': ['Chuyện nhà người ta mình không rõ thì đừng đoán nha, nói ra dễ làm người ta tổn thương lắm 🌱 {You} ơi kệ người ta, sống thật là được. Nếu buồn thì nói chuyện thẳng thắn một lần cho rõ.'],
        'co_lua': ['Nhắc nhẹ cả nhà: nhóm không bàn chuyện riêng của người khác khi chưa rõ. Có thắc mắc thì hỏi thẳng người đó, lịch sự nhé.']}),
]
# Someone the rumour names can speak up too (fact -> resident, line).
RUMOUR_WITNESS = {'seen': ('anh_khoa', 'Hàng xóm rủ nhau ăn tô phở thôi mà mọi người. Thật ra đồn vậy là thiếu dữ kiện đó, anh nói thẳng 😅')}
# The neighbour who comforted you in the life layer (life_content.COMFORT) gives the advice on the board.
RUMOUR_ADVICE = {
    'ba_tam': 'Bà nói con nghe: kệ người ta, sống thật là được. Người trong hẻm này ai thương con thì vẫn thương 🥹',
    'ba_sau': 'Bà coi rồi, tuổi con năm nay bị tiểu nhân quấy chút thôi 😅 Mà nói thiệt, miệng người ta mình không bịt được, con sống tử tế là đủ nghe.',
    'co_lua': 'Cô nhắc chung: chuyện chưa rõ thì đừng lan. Còn cháu, làm ăn đàng hoàng thì không cần giải thích với ai cả, cứ ngẩng đầu mà đi.',
    'anh_khoa': 'Thật ra tin đồn sống được là nhờ người ta nhắc lại. Em không trả lời thì nó tự tắt. Kệ người ta, sống thật là được 🤓',
    'co_ba': 'Người ta nói ra nói vào, mình làm ăn đàng hoàng là được. Buôn bán mấy chục năm cô bị đồn đủ kiểu, giờ vẫn đứng đây nè.',
    'chi_mai': 'Kệ người ta nha, sống thật là được 🌱 Ai hiểu mình thì tự khắc hiểu. Buồn thì ghé chị, chị pha trà gừng cho.',
}
# What the player can do in a rumour thread (quick replies); text is sent as the player's comment.
RUMOUR_TONES = {
    'clarify': dict(label='Giải thích', emoji='🗣️',
                    text={'late': 'Dạ mình làm ca tối ở {place}, dọn dẹp xong mới về nên khuya thôi ạ. Mọi người đừng lo nha.',
                          'multi': 'Dạ mình đang thử làm ở vài chỗ trong phố để học nghề thôi ạ, không có gì bí mật đâu.',
                          'money': 'Dạ tiền mình đi làm từng ngày để dành đó ạ, không có gì mờ ám đâu nha.',
                          'van': 'Dạ đó là hàng nhập cho tiệm mình đang làm thôi ạ, có hóa đơn đàng hoàng.',
                          'visitor': 'Dạ bạn mình ghé hỏi thăm thôi ạ.',
                          'debt': 'Dạ tiền phòng mình đang trả dần với bà Tám, bà biết hết ạ.',
                          'draw': 'Dạ mình rút tiền lời về trả tiền phòng với cơm nước thôi ạ, không nợ ai đâu.',
                          'seen': 'Dạ hàng xóm rủ nhau đi ăn thôi ạ, mọi người đừng đoán nha.',
                          'breakup': 'Dạ chuyện riêng của mình, mình đang ổn dần. Mong mọi người đừng bàn thêm nha.',
                          'generic': 'Dạ dạo này mình đi làm hơi nhiều nên mệt thôi ạ, cảm ơn mọi người đã hỏi thăm.'}),
    'joke': dict(label='Cười trừ', emoji='😄',
                 text={'late': '“Phố đêm” duy nhất mình biết là phố bán đồ ăn khuya thôi ạ 🌙😂',
                       'multi': 'Mình đang tập làm siêu nhân đa nhiệm đó ạ 🦸 chưa có cánh thôi 😂',
                       'money': 'Đồ mới là… đôi dép tổ ong đó ạ 😂',
                       'van': 'Xe đó chở hàng cho tiệm, không phải chở tiền tỷ của mình đâu ạ 😂',
                       'visitor': 'Người lạ đó là shipper giao trà sữa cho mình thôi ạ 🧋😂',
                       'debt': 'Mình chỉ nợ bà Tám… mấy chén chè thôi ạ 😂',
                       'draw': 'Mình rút tiền đi mua… xôi chị Tư đó ạ, nợ nần gì đâu 😂',
                       'seen': 'Tụi mình có gì với nhau thật: một tô phở với hai ly trà đá 😂',
                       'breakup': 'Tính mình khó thật: khó bỏ được chè bà Tám 😂',
                       'generic': 'Mặt mình phờ phạc sẵn rồi ạ, không phải tại chuyện gì đâu 😂'}),
    'confront': dict(label='Hỏi thẳng', emoji='💬',
                     text={'_': '{at} có gì thắc mắc thì hỏi thẳng mình được không ạ? Nói vậy trên nhóm mình buồn lắm.'}),
    'ignore': dict(label='Kệ thôi', emoji='🤐', text={}),
}
RUMOUR_AFTER = {
    'clarify': [('camera', 'Ờ… vậy hả, {me} chỉ hỏi thăm thôi mà. Thôi {me} xin lỗi nghen, {me} nói hơi quá.'),
                ('warm', 'Đó, bà nói rồi mà! Thôi chuyện qua rồi, tối nay xuống ăn cơm với bà nghe 🥹')],
    'joke': [('joker', 'Chấm 10 điểm cho màn đáp trả 🤣 cả hẻm cười xỉu'),
             ('camera', 'Hì, {me} cũng đoán vậy đó 😅 thôi {me} không nói nữa.')],
    'confront': [('camera', 'Ơ… {me} có nói gì đâu, {me} chỉ kể những gì {me} thấy thôi mà…'),
                 ('official', 'Nói vậy dễ làm người ta tổn thương lắm ạ. Có gì mình hỏi riêng, nhẹ nhàng thôi nhé.'),
                 ('camera', 'Thôi được rồi, {me} xin lỗi. {Me} sai rồi.')],
    'ignore': [('optimist', 'Không trả lời cũng là một cách hay nè. Sống tử tế thì lời đồn tự tắt thôi 🌈'),
               ('tsundere', 'Kệ người ta. Làm việc của mình đi.')],
}

# Life events the life layer may report (board.on_life_event): kind -> how the street reacts.
LIFE = {
    'heartbreak': T('life_heartbreak', 'drama', 'ba_tam', [
        'Mấy nay thấy đứa nhỏ ở gác buồn buồn. Bà không hỏi chuyện riêng đâu, chỉ nói vầy: ai buồn thì qua nhà bà, bà có chè, có cháo, có cả cái ghế ngồi hóng mát. Không cần kể gì hết 🥹'], [
        ('chi_mai', 'Buồn rồi sẽ qua nè, mình còn cả hẻm thương mà 🌈', .9),
        ('chu_tu', 'Tối qua tiệm chú. Có ấm trà. Không hỏi gì đâu.', .9),
        ('chi_diep', 'Chị hiểu cảm giác đó 😭 có gì nhắn chị nha, chị từng trải rồi.', .8),
        ('be_na', 'Con gửi một cái kẹo ạ 🍬', .7),
    ]),
    'bullied': T('life_bullied', 'warn', 'co_lua', [
        '📢 Tổ dân phố nhắc chung: ai bị chèn ép, nói nặng ở chỗ làm thì đừng im lặng chịu một mình. Ghi lại sự việc, nói với người phụ trách, cần thì nhờ tổ hỗ trợ. Không ai đáng bị đối xử như vậy.'], [
        ('ba_tam', 'Đúng đó. Ai ăn hiếp con cháu trong hẻm là bà không chịu đâu nghe 😤', .9),
        ('chu_tu', 'Nói tên chỗ đó. …Đùa thôi. Nhưng có gì thì nói.', .8),
        ('anh_khoa', 'Thật ra ghi chép lại ngày giờ, lời nói cụ thể là cách tốt nhất khi phản ánh. Anh từng thấy nhiều người được giúp nhờ vậy đó.', .8),
        ('chi_mai', 'Mình tử tế không có nghĩa là phải chịu đựng nè 💪', .7),
    ]),
    'scammed': T('life_scammed', 'warn', 'anh_tam', [
        '⚠️ Lại có người trong phố mình dính lừa. Anh không nói tên. Chỉ nhắc: mất tiền không phải vì mình ngu, mà vì tụi nó chuyên nghiệp. Báo ngân hàng, báo công an càng sớm càng tốt, và đừng tự trách.'], [
        ('ba_tam', 'Ai lỡ mất tiền thì xuống bà ăn cơm, người còn là còn tất cả con à.', .9),
        ('co_ba', 'Tiền mất rồi thì làm lại. Cô từng mất cả tháng lời vì tin người, giờ vẫn sống khỏe.', .8),
        ('minh_quan', 'đổi mật khẩu hết đi.', .8),
        ('chi_diep', 'Chị từng bị rồi 😭 đừng buồn quá nha, rồi sẽ ổn.', .7),
    ]),
    'mood_low': T('life_mood_low', 'chat', 'chi_mai', [
        'Nhắc nhẹ cả hẻm: dạo này ai thấy mệt thì cho phép mình nghỉ một chút nha 🌿 Ngủ sớm, ăn đủ, gọi điện về nhà. Làm việc chăm là quý, nhưng mình còn quý hơn 🌈'], [
        ('ba_tam', 'Đúng rồi, mấy đứa trẻ đi làm cứ quên ăn quên ngủ, bà xót lắm.', .9),
        ('chu_hung', 'Mệt thì chiều ra ngồi trà đá với chú, không uống bia cũng được 😄', .8),
        ('be_ti', 'nghỉ ngơi cũng là một kỹ năng nha mọi người 🛌', .7),
    ]),
    'help_money': T('life_help_money', 'happy', 'co_lua', [
        '📢 Cảm ơn bà con đã chung tay giúp một bạn trẻ trong khu phố vượt qua lúc khó khăn. Tình làng nghĩa xóm là thứ quý nhất của hẻm mình ạ 🤝'], [
        ('ba_tam', 'Có gì đâu, người trong hẻm mà 🥹', .9),
        ('chu_tu', 'Góp chút xíu thôi. Đừng nhắc nữa.', .9),
        ('co_ba', 'Có khó thì mới có lúc nhờ nhau. Sau này khá lên thì giúp lại người khác là được.', .8),
        ('minh_quan', '👍', .7),
    ]),
    'comfort': T('life_comfort', 'chat', 'ba_tam', [
        'Hôm nay bà nấu nồi canh chua to, đứa nào mệt mỏi thì ghé bà ăn chén cơm nóng nghe. Đi làm xa nhà, có chỗ về ăn cơm là đỡ tủi lắm 🥹'], [
        ('em_thu', 'D-dạ em xin ghé ạ 🥺', .8),
        ('be_ti', 'bà Tám là số 1 🥹', .8),
        ('ong_bay', 'Để phần tôi một bát. Ít ớt.', .7),
    ]),
    'generic': T('life_generic', 'chat', 'chi_mai', [
        'Hẻm mình dạo này nhiều chuyện ghê, mà chuyện gì thì chuyện, mình có nhau là được nè 🌈'], [
        ('ba_tam', 'Đúng rồi con, có gì cứ nói với nhau nghe.', .9),
        ('tung_tun', 'Nhóm mình là nhóm cư dân dễ thương nhất quả đất 🌍😂', .7),
    ]),
}

# Short lines for a resident who is @mentioned but has nothing specific to say.
MENTION_OPENERS = {
    'warm': 'Bà đây, bà đây!', 'official': 'Cô đọc được rồi ạ.', 'tsundere': 'Gọi chi.', 'knowitall': 'Anh nghe nè, để anh giải thích.',
    'genz': 'em đâyyy 🙋', 'superstitious': 'Bà nghe nè con.', 'practical': 'Cô đây.', 'cold': '?', 'gossip': 'Chị đây chị đây 👀',
    'joker': 'Có mặt! 🫡', 'grumpy': 'Gì!!!', 'showoff': 'Trang đây nè 😘', 'shy': 'D-dạ em đây ạ…', 'drama': 'TRỜI ƠI gọi chị hả 😭',
    'beer': 'Chú đây!', 'tigermom': 'Chị đây.', 'kid': 'Dạ con đây ạ 🌸', 'judge': 'Tôi đây.', 'camera': '{Me} đây, {me} thấy tin nhắn rồi 👀',
    'suspicious': 'Anh đây. Có chuyện gì?', 'optimist': 'Chị đây nè 🌈',
}

# NPC reactions to a player's post by intent: (reaction, low, high).
PLAYER_REACTS = {
    'sad': (('heart', 3, 8), ('sad', 2, 6)), 'happy': (('heart', 4, 10), ('wow', 1, 4), ('haha', 0, 2)),
    'ask': (('heart', 1, 3),), 'help': (('heart', 2, 5),), 'lost': (('sad', 1, 4), ('heart', 1, 3)),
    'complain': (('angry', 1, 4), ('haha', 0, 3), ('heart', 0, 2)), 'sell': (('heart', 2, 6), ('wow', 0, 2)),
    'food': (('heart', 2, 6), ('haha', 0, 2)), 'greet': (('heart', 3, 8),), 'thanks': (('heart', 3, 7),),
    'any': (('heart', 1, 5), ('haha', 0, 3)),
}
MOOD_REACTS = {
    'lost': (('heart', 2, 6), ('sad', 1, 4), ('wow', 0, 2)), 'warn': (('wow', 1, 5), ('heart', 1, 4), ('sad', 0, 3)),
    'complain': (('angry', 1, 5), ('haha', 0, 4), ('heart', 0, 2)), 'ask': (('heart', 1, 4),),
    'sell': (('heart', 2, 7), ('wow', 0, 3)), 'happy': (('heart', 5, 14), ('wow', 1, 4), ('haha', 0, 3)),
    'drama': (('sad', 3, 8), ('wow', 1, 4), ('haha', 0, 3)), 'chat': (('haha', 3, 9), ('heart', 1, 5)),
    'rumour': (('wow', 2, 6), ('angry', 1, 3), ('haha', 0, 2)),
}

# Keyword hints (accents stripped) for the player's intent, strongest first.
INTENT_WORDS = (
    ('sad', ('buon', 'met qua', 'chan qua', 'khoc', 'that tinh', 'chia tay', 'co don', 'stress', 'ap luc', 'nan qua', 'te qua', 'that bai',
             'bi mang', 'bi chui', 'bat nat', 'mat viec', 'om roi', 'bi om', 'nho nha', 'tui than', 'kiet suc', 'ngan qua')),
    ('lost', ('bi mat', 'danh roi', 'lam roi', 'that lac', 'di lac', 'mat vi', 'mat chia khoa', 'mat dien thoai', 'ai thay', 'nhat duoc')),
    ('complain', ('on qua', 'on ao', 'vut rac', 'do rac', 'rac thai', 'dau xe', 'chan loi', 'karaoke', 'bua bai', 'kho chiu', 'buc minh', 'phan nan', 'hat to')),
    ('help', ('cho muon', 'cho minh muon', 'cho em muon', 'cho con muon', 'cho chau muon', 'cho toi muon', 'muon cai', 'muon cay', 'muon tam', 'giup', 'nho ai', 'nho moi nguoi', 'can nguoi', 'ho tro', 'cuu', 'phu minh', 'phu voi', 'ai rang')),
    ('sell', ('can ban', 'ban lai', 'rao ban', 'ai mua', 'pass lai', 'thanh ly', 'giam gia', 'order', 'dat hang')),
    ('happy', ('vui qua', 'mung', 'len luong', 'duoc khen', 'hanh phuc', 'tuyet', 'yeah', 'sinh nhat', 'hoan thanh', 'xong roi', 'thang roi',
               'duoc nhan', 'dau roi', 'lan dau', 'hehe', 'yay', 'vui')),
    ('thanks', ('cam on', 'thank', 'biet on')),
    ('ask', ('ai biet', 'cho hoi', 'hoi chut', 'o dau', 'the nao', 'lam sao', 'bao nhieu', 'co ai', 'nen khong', 'duoc khong', 'khong a')),
    ('food', ('an sang', 'an trua', 'an toi', 'com', 'nau', 'banh', 'che', 'xoi', 'pho', 'bun', 'ngon', 'doi bung', 'tra sua')),
    ('greet', ('chao', 'xin chao', 'hello', 'moi ve', 'lam quen', 'moi den', 'moi toi')),
)

# ---------------------------------------------------------------- life layer -> board (board.on_life_log)
# A row in journey.life.log (game/life.py) becomes threads here. {them} is the player in third
# person, {name} their name, {place} the workplace of that day, {extra} a filled-in detail.
# Scams: a warning with no names, then the collection thread listing who chipped in.
SCAM_TRICK = {
    'lu_ship': 'tin nhắn đòi “phí giao hàng”', 'lu_bank': 'cuộc gọi giả nhân viên ngân hàng', 'lu_prize': 'tin “trúng thưởng xe máy”',
    'lu_fb': 'vụ Facebook bạn thân bị hack mượn tiền', 'lu_job': 'việc làm thêm “nhẹ lương cao”', 'lu_rent': 'vụ đặt cọc phòng trọ ảo',
    'lu_invest': 'nhóm “chuyên gia” chứng khoán', 'lu_charity': 'vụ quyên góp giả', 'incident': 'một vụ lừa ở chỗ làm',
    'invest': 'dự án “lãi khủng” Mây Coin',
}
LIFE_SCAM = T('lg_scam', 'warn', 'anh_tam', [
    '⚠️ Cả nhà cảnh giác: có người trong phố mình vừa dính {extra}. Anh không nói tên. Mất tiền không phải vì mình ngu, mà vì tụi nó chuyên nghiệp. Ai nhận được y vậy thì chặn số, báo ngân hàng, báo công an, đừng chuyển thêm đồng nào.'], [
    ('minh_quan', 'đổi mật khẩu hết đi.', .9),
    ('ba_sau', 'Trời đất, bà cũng từng nhận tin y vậy đó. May có thằng Tí xóa giùm 😥', .8),
    ('co_ba', 'Cái gì hứa lời nhanh, đòi chuyển trước là lừa. Buôn bán cả đời cô chưa thấy ai cho không cái gì.', .8),
    ('chi_diep', 'Chị từng bị rồi 😭 đừng tự trách mình nha, ai cũng có lúc lỡ tin người.', .7),
    ('co_hai_loa', 'Hèn gì hôm qua cô thấy có đứa ngồi đầu hẻm thẫn thờ cả buổi 👀 tội ghê.', .6),
])
LIFE_GOP = T('lg_gop', 'happy', 'co_lua', [
    '📢 Quỹ tình làng nghĩa xóm: {them} vừa bị lừa mất tiền. Cả hẻm góp chút đỡ đần: {extra}. Cô đã gửi tận tay rồi ạ. Tình làng nghĩa xóm là thứ quý nhất của hẻm mình 🤝'], [])
LIFE_GIFT = T('lg_gift', 'happy', 'co_lua', [
    '📢 Cả hẻm gửi {them} một món quà nhỏ sau chuyện bị lừa: {extra}. Tiền mất thì làm lại, người còn là còn tất cả ạ 🤝'], [])
# What each neighbour says under the collection post (journey CAST ids; life puts only these in the gop).
GOP_LINES = {
    'ba_tam': 'Có gì đâu, người trong hẻm mà 🥹 Tối nay xuống bà ăn cơm nghe con.',
    'co_ba': 'Góp chút đỡ tiền chợ. Tính ra mất tiền mua được bài học, sau này khá lên giúp lại người khác là được.',
    'co_lua': 'Cô góp phần của tổ nhé.',
    'anh_khoa': 'Anh góp chút nha. Thật ra tụi lừa đảo giờ chuyên nghiệp lắm, dính là chuyện thường, đừng buồn lâu 🤓',
    'chu_tu': 'Góp chút xíu thôi. Đừng nhắc nữa.',
    'be_ti': 'em góp tiền heo đất nè 🐷 ít thôi mà thương nhiều nha',
    'ba_sau': 'Bà góp chút đỉnh. Bà coi rồi, qua tháng này là hết hạn nghe con 🙏',
}
GOP_DECLINED = 'Cháu nó cảm ơn mà nhất định không nhận, nói tự lo được. Cô gửi lại bà con nha, tấm lòng thì cháu nhận rồi ạ 🥹'
GOP_THANKS = ('minh_quan', '👍')

# Heartbreak: friends invite you out (never say what happened).
LIFE_HEARTBREAK = T('lg_heartbreak', 'chat', 'ba_tam', [
    'Mấy nay thấy đứa nhỏ ở gác buồn buồn. Bà không hỏi chuyện riêng đâu, chỉ nói vầy: ai buồn thì qua nhà bà, bà có chè, có cháo, có cả cái ghế ngồi hóng mát. Không cần kể gì hết 🥹',
    'Bà con ơi tối nay bà nấu nồi lẩu chua to lắm. Đứa nhỏ ở gác dạo này ít cười, mấy đứa trẻ trẻ rủ nó xuống ăn cho vui nghe. Không ai hỏi gì hết, ăn thôi 🍲'], [
    ('chu_hung', '{You} ơi tối nay ra quán chú ngồi, không uống bia thì uống trà đá, chú kể chuyện cười cho nghe 🍺', .95),
    ('kieu_trang', 'Cuối tuần đi cà phê sống ảo với Trang nha {you}, Trang chụp cho tấm hình đẹp nhất năm. Ai không biết quý {you} là người ta thiệt 💅', .9),
    ('chi_diep', 'Chị hiểu cảm giác đó 😭 thứ Bảy đi karaoke với chị, hát cho khàn giọng rồi về ngủ một giấc là nhẹ lòng à.', .85),
    ('be_ti', 'tối nay em rủ {you} chơi game nha, thua em cho thắng luôn 🎮', .8),
    ('chu_tu', 'Tối qua tiệm chú. Có ấm trà. Không hỏi gì đâu.', .85),
    ('chi_mai', 'Sáng mai đi bộ bờ hồ với chị nè, gió mát lắm. Buồn rồi sẽ qua, mình còn cả hẻm thương mà 🌈', .8),
])
LIFE_SICK = T('lg_sick', 'chat', 'ba_tam', [
    'Đứa nhỏ ở gác nay ốm rồi bà con ơi, bà nấu nồi cháo hành rồi. Mấy đứa đi ngang đừng gõ cửa ồn nghe, để nó ngủ 🥣'], [
    ('co_ba', 'Cô gửi gói gừng với chai dầu gió qua. Ốm thì nghỉ, tiền làm lại được.', .9),
    ('chu_hung', 'Cần đi khám thì gọi chú, xe chú nổ máy sẵn, không lấy tiền nhé.', .9),
    ('ong_bay', 'Tôi sẽ nhắc nhà karaoke tối nay nhỏ loa!!! Người ốm cần ngủ.', .8),
    ('em_thu', 'D-dạ em có thuốc hạ sốt, em để trước cửa rồi ạ 🥺', .7),
])
LIFE_BULLIED = T('lg_bullied', 'warn', 'co_lua', [
    '📢 Tổ dân phố nhắc chung: ai bị chèn ép, nói nặng ở chỗ làm thì đừng im lặng chịu một mình. Ghi lại sự việc, nói với người phụ trách, cần thì nhờ tổ hỗ trợ. Không ai đáng bị đối xử như vậy.',
    '📢 Cô thấy dạo này mấy bạn trẻ trong hẻm đi làm về mặt mũi buồn thiu. Cô nhắc nhẹ: bị chèn ép ở chỗ làm thì nói ra, đừng ôm một mình. Tối nào nhà văn hóa cũng mở cửa, có ấm trà, có người nghe.'], [
    ('ba_tam', 'Đúng đó. Ai ăn hiếp con cháu trong hẻm là bà không chịu đâu nghe 😤', .9),
    ('chu_tu', 'Nói tên chỗ đó. …Đùa thôi. Nhưng có gì thì nói.', .8),
    ('anh_khoa', 'Thật ra ghi chép lại ngày giờ, lời nói cụ thể là cách tốt nhất khi phản ánh. Anh từng thấy nhiều người được giúp nhờ vậy đó.', .8),
    ('chi_mai', 'Mình tử tế không có nghĩa là phải chịu đựng nè 💪', .7),
])

# A neighbour in trouble (life_content.ASK): the call for help; the last comment is the owner's thanks.
# ASK_ACK[choice] is what the poster says about the player's part ({extra} = the amount).
ASK_THREADS = {
    'ask_roof': T('lg_ask_roof', 'ask', 'co_lua', [
        '📢 Mưa đêm qua nhà bà Sáu dột tứ tung, nước chảy cả vô góc để ảnh ông. Tổ gom tiền mua tôn lợp lại; ai có sức thì sáng mai qua phụ một tay nhé.'], [
        ('chu_tu', 'Chú mang thang với búa qua. Không phải vì thương đâu, mái dột thì phiền cả dãy.', .95),
        ('chu_hung', 'Chú chở tôn từ đại lý về, không lấy tiền xe nhé!', .9),
        ('co_ba', 'Cô góp mấy tấm bạt che tạm tối nay.', .8),
        ('ba_sau', 'Bà cảm ơn cả xóm nghe 🙏 Con Mướp cũng cảm ơn nữa, tối qua nó ướt như chuột lột 😿')]),
    'ask_theft': T('lg_ask_theft', 'warn', 'anh_tam', [
        '⚠️ Đêm qua tạp hóa cô Ba bị cạy cửa, mất thùng sữa với két tiền lẻ. Nhà nào có camera trước cửa thì trích giúp đoạn từ 1 giờ tới 4 giờ sáng. Tối nay anh đi tuần thêm một vòng.'], [
        ('co_hai_loa', 'Tiếc ghê, đêm qua cô ngủ sớm nên không thấy gì hết 😭 lần đầu tiên trong đời luôn đó.', .9),
        ('minh_quan', 'camera nhà mình quay được. gửi công an rồi.', .9),
        ('co_lua', 'Tổ góp tiền giúp cô Ba sửa khóa và nhập lại hàng, ai góp được nhắn cô nhé.', .9),
        ('co_ba', 'Cảm ơn cả hẻm. Mất thì làm lại, tính ra còn lời được cái tình 🥲')]),
    'ask_hospital': T('lg_ask_hospital', 'ask', 'co_lua', [
        '📢 Chú Tư mổ ruột thừa gấp tối qua, giờ đã ổn. Tiệm sửa đồ tạm đóng mấy hôm. Tổ gom chút tiền thăm chú, ai rảnh thì thay phiên vào viện trông chú giúp nhé.'], [
        ('ba_tam', 'Bà nấu cháo mang vô rồi nè. Ổng còn chê nhạt 😅', .9),
        ('kieu_trang', 'Trang gửi giỏ trái cây nha 🍎 không có ý khoe đâu, giỏ nhỏ thôi à.', .8),
        ('ong_bay', 'Tôi vào thăm chiều nay. Ông ấy mà than đau thì tôi mắng cho!!!', .8),
        ('chu_tu', 'Mổ có tí mà làm như to chuyện. …Cảm ơn. Vậy thôi.')]),
    'ask_school': T('lg_ask_school', 'ask', 'chi_mai', [
        'Bé Tí nhà mình sắp thi vào 10 rồi mọi người 📚 Nhà em dạo này hơi khó, chị đang gom chút tiền học thêm cho em. Ai rành toán, văn, tiếng Anh thì kèm em buổi tối được không nè 🌈'], [
        ('bac_liem', 'Tôi dạy toán ba mươi năm. Tối thứ Ba, thứ Năm cháu sang nhà tôi. Không lấy tiền. Nhưng phải làm bài đầy đủ.', .95),
        ('anh_khoa', 'Tiếng Anh để anh. Thật ra học từ vựng qua bài hát là nhanh nhất đó 🤓', .85),
        ('co_hanh', 'Chị mua cho em bộ đề ôn thi nhé. Na nhà chị sau này cũng phải thi mà 😊', .8),
        ('be_ti', 'mọi người ơi em cảm động xỉu 😭 em hứa đậu trường điểm luôn 💪')]),
    'ask_job': T('lg_ask_job', 'ask', 'anh_khoa', [
        'Thật ra thì… anh vừa bị cắt giảm 😅 Công ty tái cơ cấu. Anh vẫn ổn, chỉ là tháng này hơi kẹt. Ai biết chỗ nào tuyển thì chỉ anh với nha. Theo anh tìm hiểu thì tháng này thị trường cũng khó.'], [
        ('co_ba', 'Qua tiệm cô ăn cơm, chuyện việc từ từ tính. Cô nuôi được mà.', .9),
        ('minh_quan', 'gửi CV. mình giới thiệu.', .9),
        ('chi_mai', 'Biết đâu chỗ mới hợp anh hơn nè 🌈', .7),
        ('anh_khoa', 'Cảm ơn cả nhà, anh không nghĩ nhóm mình ấm vậy 🥲')]),
    'ask_scam': T('lg_ask_scam', 'warn', 'anh_tam', [
        '⚠️ Bà Tám vừa bị gọi giả “công an”, mất tiền dưỡng già. Anh nói lại lần nữa: công an KHÔNG BAO GIỜ gọi điện bắt chuyển tiền. Nhà nào có ông bà thì dặn giùm.'], [
        ('co_lua', 'Tổ đang gom chút tiền đỡ bà, ai góp được nhắn cô nhé.', .9),
        ('be_ti', 'em qua cài chặn số lạ cho bà rồi 😤 đứa nào gọi nữa là bị chặn liền', .9),
        ('chu_tu', 'Tối nay chú qua ngồi với bà.', .8),
        ('ba_tam', 'Bà già rồi lẩm cẩm, làm cả hẻm lo 🥹 Cảm ơn mấy đứa nhiều lắm.')]),
    'ask_trungthu': T('lg_ask_trungthu', 'happy', 'co_lua', [
        '📢 Trung thu năm nay tổ làm cho các cháu trong hẻm: lồng đèn, bánh nướng, múa lân. Tổ đang gom tiền mua lồng đèn; ai khéo tay thì tối thứ Sáu qua nhà văn hóa dán lồng đèn với cô nhé 🏮'], [
        ('be_na', 'Con muốn lồng đèn con thỏ ạ 🐰', .9),
        ('be_ti', 'em xin làm đầu lân 🦁', .85),
        ('chu_hung', 'Chú góp bia… à không, góp nước ngọt cho tụi nhỏ 😅', .8),
        ('co_lua', 'Cảm ơn bà con, năm nay các cháu có Trung thu to nhất phường ạ 🥮')]),
    'ask_flood': T('lg_ask_flood', 'ask', 'co_lua', [
        '📢 Nhà bà cụ cuối hẻm ngập tới gối, đồ đạc hư nhiều. Ai rảnh qua phụ tát nước, khiêng đồ lên cao; tổ gom tiền mua lại cái nồi cơm với tấm nệm cho bà.'], [
        ('chu_hung', 'Chú qua liền, xe chú chở đồ lên nhà văn hóa để tạm.', .9),
        ('ong_bay', 'Tôi nói cái cống đầu hẻm bao nhiêu lần rồi!!! …Tôi góp một phần.', .85),
        ('tung_tun', 'Tui mang ủng qua nè, hẻm mình giờ thành Venice rồi 🛶', .7),
        ('co_lua', 'Cảm ơn cả nhà, bà cụ khóc quá trời, nói chưa thấy hẻm nào thương nhau như hẻm mình 🥹')]),
}
ASK_ACK = {
    'big': 'Cảm ơn {name} góp {extra} xu nha, nhiều quá trời 🙏',
    'small': 'Cảm ơn {name} góp {extra} xu, ít mà quý lắm 🙏',
    'hand': '{name} qua phụ một tay từ sáng tới giờ, mồ hôi nhễ nhại luôn. Cảm ơn nha 🙏',
}

# Small joys: the street congratulates you.
JOY_THREADS = {
    'joy_drawing': T('lg_joy_drawing', 'happy', 'be_ti', [
        'em vẽ {you} đang làm việc nè 🖍️ tranh đẹp khum mọi người, dưới tranh em ghi “Người giỏi nhất hẻm” 😎'], [
        ('ba_tam', 'Trời đất, giống y chang! Bà dán lên tủ lạnh nghe 🥹', .9),
        ('kieu_trang', 'Tranh xịn xò, Trang xin repost nha ✨', .7),
        ('co_hanh', 'Đẹp đấy. Na nhà chị năm ngoái cũng được giải vẽ tranh cấp quận đấy ạ 😊', .7),
        ('bac_liem', 'Vẽ có hồn. Tốt.', .6)]),
    'joy_soup': T('lg_joy_soup', 'happy', 'ba_tam', [
        'Bà nấu nồi canh chua cá lóc, để phần đứa nhỏ ở gác một tô to, dán giấy trên nắp rồi đó 🍲 Mấy đứa khác đói thì xuống bà múc nghe.'], [
        ('em_thu', 'D-dạ em xin một chén ạ 🥺', .8),
        ('ong_bay', 'Để phần tôi một bát. Ít ớt.', .8),
        ('tung_tun', 'Canh chua bà Tám là đặc sản hẻm, ship đi toàn quốc được luôn á 🛵', .6)]),
    'joy_kitten': T('lg_joy_kitten', 'happy', 'ba_sau', [
        'Bà con ơi con Mướp đẻ rồi!!! Bốn đứa, ba vàng một mướp 🐱 Bà cho đứa nhỏ ở gác đặt tên một đứa, ai muốn nhận nuôi thì nói bà nghe. Bà coi rồi, mèo đẻ đầu tháng là nhà có lộc đó.'], [
        ('be_na', 'Con xin đặt tên một bạn là Bánh Bao ạ 🥟', .9),
        ('ong_bay', 'Đừng cho chúng nó sang nhà tôi!!! …Mà gửi tôi xem ảnh.', .85),
        ('co_lua', 'Chúc mừng bà Sáu, chúc mừng Mướp ạ 🎉', .7),
        ('be_ti', 'cute xỉu 😭 em xin làm cha nuôi', .7)]),
    'joy_rain': T('lg_joy_rain', 'chat', 'chi_mai', [
        'Mưa đầu mùa rồi cả nhà ơi 🌦️ Cả hẻm thơm mùi đất, ai rảnh ngồi hiên nghe mưa với chị nè.'], [
        ('ba_sau', 'Mưa đầu mùa là điềm lành đó con.', .8),
        ('tung_tun', 'Shipper tụi tui thì… lãng mạn trong áo mưa cánh dơi 🥲', .8),
        ('thim_bay', 'Ướt ghế thím rồi.', .7)]),
    'joy_thanks': T('lg_joy_thanks', 'happy', 'chi_tu_zalo', [
        'Hóng nè cả nhà: nghe đâu có khách cũ nhắn cảm ơn {name} dài cả trang, nói nhờ hôm đó mà nhà người ta vui cả tuần 🥹 Người hẻm mình giỏi ghê! Tin này chị cho lan thoải mái nha 😂'], [
        ('ba_tam', 'Bà biết mà! Đứa nhỏ ở gác nhà bà tử tế lắm 🥹', .9),
        ('co_lua', 'Chúc mừng cháu, làm nghề có tâm là vậy đó.', .8),
        ('bac_liem', 'Được khách nhớ ơn là quý hơn tiền. Tôi khen thật.', .8),
        ('minh_quan', '👍', .7)]),
    'joy_mum': T('lg_joy_mum', 'happy', 'co_hai_loa', [
        'Sáng nay 9 giờ 10 cô thấy shipper khiêng thùng quà quê to đùng lên gác nhà bà Tám 📦 Mẹ gửi đó hả cháu, thơm mùi mắm từ đầu hẻm 👀 Lần này cô nói thiệt: cô mừng cho cháu nha.'], [
        ('ba_tam', 'Mẹ nó gửi đó, có cả lá thư nữa 🥹', .9),
        ('co_ba', 'Mắm quê là quý nhất, cất chỗ mát, đừng để lâu.', .8),
        ('be_ti', 'có bịch me hông {you}, em xin một trái 🤤', .8)]),
    'joy_tea': T('lg_joy_tea', 'chat', 'co_ba', [
        'Chiều nay cô với đứa nhỏ ở gác ngồi uống trà đầu hẻm, ngó người qua lại. Trà ngon mà có người ngồi chung còn ngon hơn 🍵'], [
        ('thim_bay', 'Thím thấy hai cô cháu ngồi từ 4 giờ tới 5 giờ rưỡi.', .9),
        ('co_hai_loa', 'Cô thấy luôn 👀 mà lần này cô không nói gì hết nha, dễ thương thôi.', .7),
        ('ba_tam', 'Mai qua bà, bà pha trà sen.', .7)]),
    'joy_fix': T('lg_joy_fix', 'chat', 'chu_tu', [
        'Quạt nhà đứa nhỏ ở gác kêu rè rè. Sửa rồi. Đừng cảm ơn.'], [
        ('tung_tun', 'Chú Tư: “đừng cảm ơn”. Cả nhóm: cảm ơn chú Tư 🤣', .9),
        ('ba_tam', 'Ổng vậy đó, ngoài miệng cằn nhằn chứ thương tụi nhỏ lắm 🥹', .8),
        ('chu_tu', 'Đã nói đừng.', .8)]),
    'joy_sunset': T('lg_joy_sunset', 'happy', 'kieu_trang', [
        'Hoàng hôn trên sân thượng dãy trọ nay đỏ rực luôn cả nhà ơi 🌇 Trang chụp cho {you} một tấm, đẹp xỉu, không có ý khoe đâu nha 📸'], [
        ('be_ti', 'ảnh đẹp dữ, cho em xin làm hình nền 😍', .8),
        ('chi_mai', 'Chiều nay đẹp thiệt nè 🌈', .7),
        ('bac_liem', 'Chụp ít thôi, ngắm nhiều vào.', .7)]),
    'joy_khoa': T('lg_joy_khoa', 'chat', 'anh_khoa', [
        'Thật ra anh mua dư một ly nước mía nên đưa đứa nhỏ ở gác uống giùm, chứ không phải anh tốt bụng gì đâu nha 😅 Theo anh tìm hiểu thì nước mía giải nhiệt tốt lắm.'], [
        ('chu_tu', 'Học ai cái câu “không phải tốt bụng gì đâu” vậy.', .9),
        ('chi_tu_zalo', 'Mua dư ly nước mà mua đúng ly ít đá của người ta ha 👀🤭', .7),
        ('co_ba', 'Ly nước mía mười nghìn mà nói cả đoạn văn 😆', .6)]),
}
# The player answered on the group in the life card (life_content HARD choice ids): the quoted part
# of the choice label is used, else this text.
LIFE_RUMOUR_REPLY = {
    'post': 'Dạ mình đi làm đàng hoàng thôi ạ, mọi người đừng đoán nha.',
    'invoice': '📷 [Ảnh hóa đơn nhập hàng] Hàng về {place} có hóa đơn đàng hoàng hết nha mọi người.',
}
