"""Người gác hải đăng, đèn biển Hòn Gió: the fixed content of the lighthouse career (game/careers/lighthouse.py).

Everything is fictional: Xí nghiệp Bảo đảm hàng hải Vịnh Ngọc, đảo Hòn Gió, bến cá Cửa Lở, Đài Duyên hải Vịnh Ngọc,
the light's characteristic and the station's rules ("Nội quy trạm đèn", a game rule). What they teach is the real habit
of the trade: check the light and its power every morning and log what you find honestly, light it on time and check
its characteristic against the list of lights, observe the weather the same way every time and report it plainly,
warn boats early, relay a distress call to the coastal station with the right priority and position (never go out
alone into a storm), keep strangers out of the lamp room, shelter anyone in danger. Safety is always the right
answer; giving in is never rewarded.

Shapes (all lists and dicts, so a stored task equals its regenerated original after a JSON round trip):
* PEOPLE    (name, role, note, persona) — NPC ids lighthouse_npc_01…
* EQUIP     the morning round; FAULTS what it can turn up (fix = the keeper can, forms = where it must be reported)
* SEA       what can happen on the water (look = what the binoculars show, need = the actions it takes,
            relay = the right priority on the radio)
* VISITORS  who lands on the island and what they want (permit, night, emergency, best/ok/bad answers)
* GOODS     the supply boat's list; BASKET the captain's private basket of fresh things
The surprises (DESK), the chuyện oái oăm (ODD) and the situations live in game/careers/lighthouse_odd.py.
"""
from __future__ import annotations

COMPANY = 'Xí nghiệp Bảo đảm hàng hải Vịnh Ngọc'
STATION = 'Đài Duyên hải Vịnh Ngọc'
ISLAND = 'đảo Hòn Gió'
LIGHT = 'Đèn biển Hòn Gió'
PORT = 'bến cá Cửa Lở'
BORDER = 'Đồn biên phòng Cửa Lở'
CHARACTER = 'Chớp nhóm 3 trắng, chu kỳ 15 giây'
CHAR_CODE = 'Fl(3)W 15s · tầm hiệu lực 22 hải lý'

PEOPLE = [
    ('Chú Bảy Đèn', 'Trạm trưởng đèn biển Hòn Gió', 'Ba mươi năm trên đảo, nhìn màu mây là biết chiều nay có giông. Nói ít, lau kính đèn kỹ như lau mặt con.', 'warm'),
    ('Chị Hải Yến', 'Trực ban Đài Duyên hải Vịnh Ngọc', 'Giọng bộ đàm sang sảng, ghét nhất ai báo cáo ậm ừ “chắc khoảng khoảng”.', 'bossy'),
    ('Anh Khôi', 'Phó phòng kỹ thuật xí nghiệp', 'Kiểm tra qua bộ đàm bất kể giờ nào, hay đòi những thứ trời ơi đất hỡi.', 'sour'),
    ('Ông Sáu Ghe', 'Chủ tàu cá ở bến Cửa Lở', 'Bốn chục năm đi biển, tin vào kinh nghiệm hơn tin bản tin. Hay xin “quay đèn về phía lưới”.', 'picky'),
    ('Chú Tư Lực', 'Thuyền trưởng tàu tiếp tế Hòn Gió 02', 'Nửa tháng ra đảo một lần, mang theo rau, nước, dầu và một giỏ “hàng riêng” giá trên trời.', 'sour'),
    ('Vy Vlog', 'TikToker du lịch, 300k follow', 'Đi đâu cũng livestream, câu cửa miệng: “Cho em xin một góc thôi mà anh ơi.”', 'genz'),
    ('Anh Đức', 'Nhà văn đi tìm cảm hứng', 'Viết tiểu thuyết về người gác đèn, muốn “sống thử” trên đảo một tuần.', 'quiet'),
    ('Cô Thắm', 'Hướng dẫn viên tàu du lịch Biển Ngọc', 'Dẫn khách ra đảo mỗi sáng, giấy tờ lúc nào cũng đủ, chỉ khách là không bao giờ đủ kiên nhẫn.', 'picky'),
]
BAY, YEN, KHOI, SAU, LUC, VY, DUC, THAM = range(8)

# ---------------------------------------------------------------- the day's sea (kit.daily)
MODS = [
    dict(id='calm', emoji='🌤️', label='Biển êm', hint='Trời trong, biển lặng. Ngày đẹp thì khách ra đảo đông: xem giấy tờ trước khi cho lên.', weight=3),
    dict(id='breeze', emoji='🌬️', label='Gió mùa về', hint='Gió cấp 5–6, sóng bạc đầu. Quan trắc kỹ, gió từ cấp 6 thì phát cảnh báo cho tàu thuyền.',
         min_day=2, weight=2),
    dict(id='fog', emoji='🌫️', label='Sương mù', hint='Tầm nhìn dưới một cây số: chạy còi sương mù, canh tàu đi gần bãi đá ngầm.', min_day=2, weight=2),
    dict(id='storm', emoji='⛈️', label='Áp thấp, biển động', hint='Áp kế tụt nhanh, gió giật. Cảnh báo sớm, tàu nào còn ngoài khơi là canh chừng. Không ai ra khơi bằng xuồng.',
         min_day=3, weight=1),
    dict(id='tourist', emoji='🏖️', label='Mùa du lịch', hint='Tàu du lịch, cano thuê, người livestream kéo ra đảo. Nội quy trạm là nội quy trạm.', min_day=2, weight=2),
]

# ---------------------------------------------------------------- the almanac and the rule (Nội quy trạm, a game rule)
LIGHT_RULE = 'Thắp đèn trước giờ mặt trời lặn 15 phút, tắt đèn sau giờ mặt trời mọc 15 phút.'
OFFSET = 15

# ---------------------------------------------------------------- the morning round: the equipment
EQUIP = [
    dict(id='lamp', emoji='💡', name='Bóng đèn & bộ đổi bóng', test='Xem bóng chính, bóng dự phòng', ok='Bóng chính sáng tốt, bóng dự phòng sẵn sàng trên bộ đổi bóng.'),
    dict(id='lens', emoji='🔆', name='Kính đèn', test='Soi kính đèn, lớp kính bảo vệ', ok='Kính lành. Muối biển với bụi bám một lớp mờ như mọi sáng.'),
    dict(id='rotate', emoji='⚙️', name='Mô-tơ quay đèn', test='Cho quay thử, bấm giờ một vòng', ok='Mô-tơ chạy êm, một vòng đúng 15 giây.'),
    dict(id='solar', emoji='🔋', name='Pin mặt trời & ắc quy', test='Đọc đồng hồ ắc quy, xem tấm pin', ok='Ắc quy 92%, tấm pin sạch, đèn sạc xanh.'),
    dict(id='gen', emoji='🛢️', name='Máy phát dự phòng & bồn dầu', test='Chạy thử năm phút, xem nhớt, đo bồn dầu', ok='Máy nổ đều, nhớt đủ vạch, không rỉ dầu.'),
    dict(id='horn', emoji='📯', name='Còi sương mù & bộ đàm VHF', test='Thử còi một hồi ngắn, gọi thử đài', ok='Còi kêu vang, chị Hải Yến: “Đài nghe rõ, chào trạm Hòn Gió.”'),
]
EQUIP_IDS = [x['id'] for x in EQUIP]
FORMS = {
    'so': dict(emoji='📒', name='Ghi sổ trực', hint='việc nhỏ đã tự xử lý, ca sau cần biết'),
    'phieu': dict(emoji='🧾', name='Phiếu báo hỏng gửi xí nghiệp', hint='cần thợ ra đảo hoặc gửi vật tư theo tàu'),
    'dai': dict(emoji='📻', name='Báo đài duyên hải ngay', hint='ảnh hưởng tín hiệu đèn, còi: đài phát thông báo hàng hải'),
}
FAULTS = {
    'bulb': dict(item='lamp', text='Bóng chính cháy đêm qua, bộ đổi bóng đã tự chuyển sang bóng dự phòng.', fix='Lắp bóng mới vào vị trí chính, thử lại bộ đổi bóng',
                 forms=['so'], danger=False, why='Bóng dự phòng đang gánh, mình thay bóng chính là xong; ghi sổ để xí nghiệp gửi thêm bóng.'),
    'changer': dict(item='lamp', text='Bộ đổi bóng kẹt: bóng chính mà cháy thì bóng dự phòng không tự lên!', fix='Gỡ kẹt, cố định bộ đổi bóng, thử chuyển bằng tay',
                    forms=['so', 'phieu', 'dai'], danger=True, why='Đêm nay đèn có thể tắt mà không ai hay: đài cần biết để báo tàu thuyền, xí nghiệp gửi linh kiện.'),
    'motor': dict(item='rotate', text='Mô-tơ quay chậm: một vòng mất 19 giây thay vì 15.', fix=None, forms=['phieu', 'dai'], danger=True,
                  why='Đèn sai đặc tính, tàu có thể nhận nhầm là đèn khác. Mô-tơ phải thợ thay: báo đài phát thông báo hàng hải.'),
    'crack': dict(item='lens', text='Một tấm kính bảo vệ nứt chân chim ở góc dưới.', fix=None, forms=['phieu'], danger=False,
                  why='Chưa ảnh hưởng ánh sáng, nhưng gió lớn có thể vỡ: xin kính mới theo tàu.'),
    'battery': dict(item='solar', text='Ắc quy chỉ còn 38%, tấm pin phủ đầy phân chim.', fix='Lau tấm pin, chạy máy phát sạc bù', forms=['so'], danger=False,
                    why='Pin bẩn thì sạc không vào; mình lau, sạc bù và ghi sổ.'),
    'oil': dict(item='gen', text='Máy phát rỉ dầu ở khớp ống, nhớt dưới vạch.', fix='Châm nhớt, siết khớp, lót khay hứng dầu', forms=['so', 'phieu'], danger=False,
                why='Siết tạm được, nhưng khớp ống phải thay: ghi sổ và xin vật tư.'),
    'horn': dict(item='horn', text='Còi sương mù kêu khàn một tiếng rồi tắt hẳn.', fix=None, forms=['phieu', 'dai'], danger=True,
                 why='Đêm sương mà còi câm thì tàu không biết đảo ở đâu: đài phải báo tàu thuyền, xí nghiệp gửi thợ.'),
    'vhf': dict(item='horn', text='Bộ đàm VHF chính rè rè, đài nghe chữ được chữ mất.', fix='Chuyển sang bộ đàm dự phòng, thử lại', forms=['so', 'phieu'], danger=False,
                why='Có máy dự phòng thì mình tự chuyển; máy chính phải gửi về sửa.'),
}
HANDOVER = [
    'Chú Bảy ghi: “Đêm qua gió đông bắc giật cấp 6, đèn chạy tốt. Mèo Mun bắt được con chuột kho.”',
    'Chú Bảy ghi: “Còn hai bóng dự phòng trong tủ. Tàu tiếp tế nhớ xin thêm bóng với nhớt máy.”',
    'Chú Bảy ghi: “Ông Sáu Ghe lại gọi xin quay đèn về phía lưới. Chú không cho. Con cũng đừng cho.”',
    'Chú Bảy ghi: “Chiều qua có cano thuê ghé, đòi lên đỉnh tháp chụp ảnh. Nói khéo mà cứng.”',
    'Chú Bảy ghi: “Luống rau muống sau nhà đã lên ngọn. Tưới buổi chiều thôi, nắng trưa cháy lá.”',
    'Chú Bảy ghi: “Áp kế hôm qua tụt hai vạch lúc chiều. Hôm nay để ý mây phía đông.”',
]

# ---------------------------------------------------------------- the weather watch (quan trắc)
# Beaufort (cấp gió): the real scale's metres per second.
BEAUFORT = [(0, 0.0, 0.2), (1, 0.3, 1.5), (2, 1.6, 3.3), (3, 3.4, 5.4), (4, 5.5, 7.9), (5, 8.0, 10.7), (6, 10.8, 13.8),
            (7, 13.9, 17.1), (8, 17.2, 20.7), (9, 20.8, 24.4)]
SEA_STATES = {
    'lang': dict(label='Lặng – gợn nhẹ', seen='Mặt biển phẳng lì, chỉ gợn lăn tăn như vảy cá.'),
    'nho': dict(label='Sóng nhỏ', seen='Sóng nhỏ dài, vài ngọn vỡ lấp lánh, chưa thấy bạc đầu.'),
    'vua': dict(label='Sóng vừa, bạc đầu', seen='Sóng dài hơn, bạc đầu trắng xóa nhiều nơi, có bụi nước.'),
    'lon': dict(label='Sóng lớn, biển động', seen='Sóng chồm cao, bọt trắng bị gió kéo thành vệt dài, bụi nước mù mịt.'),
}
VIS = {
    'xa': dict(label='Trên 10 km', seen='Thấy rõ mũi Cửa Lở (15 km) xanh thẫm cuối chân trời.'),
    'kha': dict(label='4 – 10 km', seen='Thấy hòn Đá Bia (8 km), không thấy mũi Cửa Lở đâu.'),
    'kem': dict(label='1 – 4 km', seen='Thấy hòn Mõ (3 km) mờ mờ, không thấy hòn Đá Bia.'),
    'mu': dict(label='Dưới 1 km', seen='Trắng xóa. Không thấy cả phao số 1 cách bến 800 mét.'),
}
BARO = {
    'up': dict(label='Tăng'),
    'steady': dict(label='Đứng'),
    'down': dict(label='Giảm chậm'),
    'fast': dict(label='Giảm nhanh (từ 3 hPa / 3 giờ)'),
}
INSTRUMENTS = {
    'wind': dict(emoji='🌬️', name='Máy đo gió', short='Gió'),
    'sea': dict(emoji='🌊', name='Nhìn mặt biển', short='Biển'),
    'vis': dict(emoji='🔭', name='Nhìn các mốc tầm xa', short='Tầm nhìn'),
    'baro': dict(emoji='🧭', name='Áp kế & sổ áp', short='Áp suất'),
}
WARN_WIND = 6        # from cấp 6 (or a fast-falling barometer) the station warns boats (game rule)

# ---------------------------------------------------------------- the evening log (dusk)
REMARKS = {
    'ontime': '✅ Thắp đèn đúng giờ',
    'char_ok': '🔆 Đèn đúng đặc tính',
    'char_bad': '⚠️ Đèn sai đặc tính, đã báo đài',
    'fog': '📯 Sương mù, đã chạy còi',
    'horn_out': '🔇 Còi hỏng, đã báo đài',
    'wind': '🌬️ Gió mạnh, theo dõi tàu thuyền',
}
CHAR_OPTIONS = ['3 chớp trắng, chu kỳ 15 giây', '3 chớp trắng, chu kỳ 19 giây', '2 chớp trắng, chu kỳ 10 giây']

# ---------------------------------------------------------------- the sea: what can happen on the water
# Actions: look · vhf (gọi tàu kênh 16, with words) · lamp (đèn tín hiệu) · horn · buoy (ném phao) · relay (báo đài, a priority)
#          · track (canh giữ mục tiêu, ghi phương vị) · boat / swim (always wrong: never go alone)
SEA_ACTS = {
    'vhf': dict(emoji='📻', name='Gọi tàu trên kênh 16'),
    'lamp': dict(emoji='🔦', name='Đèn tín hiệu: “Bạn đang đi vào nguy hiểm”'),
    'horn': dict(emoji='📯', name='Kéo còi gọi'),
    'buoy': dict(emoji='🛟', name='Ném phao cứu sinh có dây'),
    'track': dict(emoji='🧭', name='Canh giữ mục tiêu, ghi phương vị vào sổ'),
    'boat': dict(emoji='🚣', name='Tự lấy xuồng của trạm ra cứu'),
    'swim': dict(emoji='🏊', name='Nhảy xuống bơi ra kéo vào'),
}
RELAY = {
    'mayday': dict(emoji='🆘', name='MAYDAY RELAY · cấp cứu', hint='tính mạng người đang bị đe dọa'),
    'pan': dict(emoji='🟧', name='PAN-PAN · khẩn cấp', hint='cần giúp đỡ, chưa nguy tới tính mạng'),
    'securite': dict(emoji='🟨', name='SÉCURITÉ · an toàn hàng hải', hint='cảnh báo cho tàu thuyền, không ai gặp nạn'),
    'border': dict(emoji='🛡️', name='Báo đồn biên phòng (qua đài)', hint='vi phạm pháp luật trên biển, tàu cố ra khơi khi có lệnh cấm'),
}
WORDS = {
    'forecast': dict(emoji='📋', name='Đọc bản tin: gió, sóng, áp thấp'),
    'shelter': dict(emoji='⚓', name='Khuyên vào tránh trú ở âu Cửa Lở'),
    'family': dict(emoji='👨‍👩‍👧', name='Nhắc vợ con ở nhà đang chờ'),
    'law': dict(emoji='⚖️', name='Nói rõ đây là vi phạm, trạm phải báo'),
    'threat': dict(emoji='😠', name='Dọa “cho đi tù”'),
    'beg': dict(emoji='🙏', name='Năn nỉ cho xong'),
}
BOATS = ['CL-4721-TS', 'CL-3058-TS', 'CL-6610-TS', 'CL-2297-TS', 'CL-5143-TS', 'CL-7036-TS']


def _sea(cid, emoji, title, opening, look, need, relay=None, persons=None, npc=YEN, mods=None, min_day=1, weight=2, night=False,
         talk=None, extra=''):
    return dict(id=cid, emoji=emoji, title=title, opening=opening, look=look, need=list(need), relay=relay, persons=persons, npc=npc,
                mods=mods, min_day=min_day, weight=weight, night=night, talk=talk, extra=extra)


SEA = {
    'flare': _sea('flare', '🔴', 'Pháo hiệu đỏ giữa biển động', 'Một đốm đỏ vọt lên trời rồi rơi chậm xuống phía đông nam. Rồi thêm một đốm nữa.',
                  'Qua ống nhòm: một tàu cá vỏ gỗ {boat} nghiêng hẳn một bên, phương vị {bearing}°, cách khoảng {dist} hải lý. Đếm được {persons} người bám mạn.',
                  ['look', 'relay', 'track'], relay='mayday', persons=True, npc=YEN, mods=['storm', 'breeze'], min_day=3, weight=3, night=True),
    'drift': _sea('drift', '🛶', 'Tàu cá trôi dạt, chết máy', 'Một tàu cá nhỏ trôi ngang, không thấy khói máy, có người đứng vẫy áo.',
                  'Qua ống nhòm: tàu {boat}, phương vị {bearing}°, cách {dist} hải lý, {persons} người, tàu không nghiêng, không thấy nước vào. Họ giơ dây kéo ra hiệu.',
                  ['look', 'relay', 'track'], relay='pan', persons=True, npc=YEN, weight=3),
    'mob': _sea('mob', '🛟', 'Người rơi xuống nước gần bến', 'Tiếng hét từ phía bến: một chiếc kayak lật úp, có người chới với cách bờ chừng ba chục mét.',
                'Qua ống nhòm: một người không mặc áo phao, đang chìm dần, phương vị {bearing}°, cách {dist} hải lý tính từ trạm. Bạn đồng hành của họ bám thuyền lật.',
                ['look', 'buoy', 'relay', 'track'], relay='mayday', persons=True, npc=THAM, mods=['calm', 'tourist'], min_day=2, weight=2),
    'kids': _sea('kids', '🧒', 'Tụi nhỏ thách nhau bơi ra đảo', 'Mấy cái đầu đen nhấp nhô giữa con nước, từ phía làng chài bơi về hướng đảo.',
                 'Qua ống nhòm: {persons} đứa nhỏ, phương vị {bearing}°, còn cách đảo chừng {dist} hải lý. Một đứa bơi chậm hẳn lại, ngửa mặt thở.',
                 ['look', 'horn', 'buoy', 'relay', 'track'], relay='mayday', persons=True, npc=BAY, mods=['calm', 'tourist'], min_day=3, weight=2),
    'reef': _sea('reef', '🪨', 'Tàu cá lao về phía bãi đá ngầm', 'Đèn hành trình xanh đỏ của một tàu cá đang đi thẳng vào bãi đá ngầm hòn Mõ.',
                 'Qua ống nhòm: tàu {boat}, phương vị {bearing}°, cách {dist} hải lý, chạy đều máy, buồng lái tối om.',
                 ['look', 'vhf'], relay='pan', npc=SAU, mods=['calm', 'fog', 'breeze'], weight=2, night=True, talk='reef'),
    'storm_out': _sea('storm_out', '⛵', 'Tàu cá cố ra khơi khi có cảnh báo', 'Đài vừa phát tin áp thấp. Một tàu cá vẫn nổ máy rời bến Cửa Lở, mũi hướng ra khơi.',
                      'Qua ống nhòm: tàu {boat} của ông Sáu Ghe, phương vị {bearing}°, cách {dist} hải lý, chở đầy lưới, sáu người trên boong.',
                      ['look', 'vhf'], relay='border', npc=SAU, mods=['storm', 'breeze'], min_day=3, weight=3, talk='storm'),
    'blast': _sea('blast', '💥', 'Tiếng nổ trầm dưới nước', 'Một tiếng “ục” trầm đục vang lên từ phía bãi đá. Cá chết trắng nổi lên mặt nước.',
                  'Qua ống nhòm: tàu {boat} đang vớt cá chết, phương vị {bearing}°, cách {dist} hải lý. Một người cầm can nhựa buộc dây.',
                  ['look', 'relay'], relay='border', npc=YEN, mods=['calm', 'tourist'], min_day=4, weight=1, talk='blast'),
}
SEA_GENTLE = 'drift'
# How the people out there take what was said on the radio (by the case).
TALK = {
    'reef': dict(ok='📻 “Trạm Hòn Gió đây, tàu {boat} chú ý, phía trước là bãi đá ngầm!” Một giọng ngái ngủ: “Hả? Chết cha… cảm ơn trạm!” Tàu bẻ lái gấp.',
                 silent='📻 Gọi ba lần trên kênh 16: không ai trả lời. Đèn hành trình vẫn lừ lừ tiến về bãi đá.'),
    'storm': dict(back='📻 Ông Sáu Ghe im một lúc lâu: “Thôi được… quay về.” Tàu chậm lại rồi vòng mũi về âu Cửa Lở.',
                  again='📻 Ông Sáu Ghe: “Bản tin năm nào chả dọa! Cá đang lên, mất con nước này là mất cả tháng!”',
                  refuse='📻 Ông Sáu Ghe: “Tui đi biển bốn chục năm, cần gì cậu dạy!” Rồi tắt bộ đàm. Tàu vẫn hướng ra khơi.'),
    'blast': dict(back='📻 Bên kia tắt bộ đàm. Tàu nổ máy chạy về phía bờ.',
                  again='📻 Một giọng khàn: “Ê trạm, nhắm mắt cho qua đi. Mai anh mang ra chục ký mực, coi như bồi dưỡng.”',
                  refuse='📻 “Mày báo thử coi, ở đảo một mình đó nghe.” Rồi tắt máy.'),
}
WORD_SCORE = {   # how much each thing said moves the captain (fixed from the words, never random)
    'storm': dict(forecast=2, shelter=2, family=1, law=1, threat=-2, beg=-1),
    'blast': dict(forecast=0, shelter=0, family=0, law=2, threat=-1, beg=-2),
}

# ---------------------------------------------------------------- visitors (Nội quy trạm: khách chỉ lên ban ngày, có giấy
# của xí nghiệp, có người đi kèm, không quá 10 người một lượt, không vào phòng đèn, không ở lại qua đêm trừ khi gặp nạn)
ANSWERS = {
    'escort': dict(emoji='🧑‍✈️', name='Cho tham quan theo nội quy, mình đi kèm (không vào phòng đèn)'),
    'yard': dict(emoji='📸', name='Chỉ cho đứng ở sân trạm, bến đá chụp ảnh'),
    'refuse': dict(emoji='✋', name='Từ chối lịch sự, nói rõ nội quy trạm'),
    'shelter': dict(emoji='🏠', name='Cho trú tạm trong nhà trạm, báo đài'),
    'report': dict(emoji='🛡️', name='Báo đồn biên phòng qua đài'),
    'give': dict(emoji='⚠️', name='Chiều theo cho xong'),
}


def _v(vid, emoji, who, wants, line, again, papers, best, ok=(), bad=(), permit=False, night=False, group=1, emergency=False,
       soft=False, sneaky=False, npc=None, offer=0, mods=None, min_day=1, weight=2, give=''):
    return dict(id=vid, emoji=emoji, who=who, wants=wants, line=line, again=again, papers=papers, best=list(best), ok=list(ok), bad=list(bad),
                permit=permit, night=night, group=group, emergency=emergency, soft=soft, sneaky=sneaky, npc=npc, offer=offer, mods=mods,
                min_day=min_day, weight=weight, give=give)


VISITORS = [
    _v('tour', '🚤', 'Cô Thắm · đoàn khách tàu Biển Ngọc', 'Đưa tám vị khách lên tham quan sân trạm và chân tháp',
       '“Chào em, đoàn chị tám người, có giấy của xí nghiệp đây. Cho khách chụp ở chân tháp với nghe kể chuyện đèn nhé!”',
       '“Khách chị trả tiền tour rồi, em nhanh nhanh giùm chị nha.”',
       'Giấy giới thiệu của xí nghiệp: đoàn 8 người, tham quan ban ngày, có chữ ký và dấu đỏ.', ['escort'], ['yard'], ['give'],
       permit=True, group=8, npc=THAM, weight=3, give='Bạn để khách tự leo lên phòng đèn. Một ông khách sờ vào kính đèn để lại cả bàn tay mồ hôi muối.'),
    _v('students', '🎒', 'Thầy Lâm · đoàn học sinh THCS Cửa Lở', 'Mười bốn em học sinh đi trải nghiệm “một ngày làm người gác đèn”',
       '“Trường có công văn với xí nghiệp rồi. Các em mê đèn biển lắm, cho các em lên đỉnh tháp một lượt luôn nha!”',
       '“Đi một lượt cho nhanh em ơi, tàu đón lúc ba giờ.”',
       'Công văn của xí nghiệp: đồng ý cho đoàn học sinh tham quan ban ngày, chia nhóm không quá 10 em, có người của trạm đi kèm.',
       ['escort'], ['yard'], ['refuse', 'give'], permit=True, group=14, weight=2,
       give='Mười bốn đứa nhỏ ùa lên cầu thang xoắn cùng lúc. Một em trượt chân ở bậc thứ chín, may thầy Lâm đỡ kịp.'),
    _v('selfie', '🤳', 'Nhóm bạn trẻ đi cano thuê', 'Lên đỉnh tháp chụp “ảnh sống ảo” lúc hoàng hôn',
       '“Anh ơi cho tụi em lên đỉnh chụp năm phút thôi, ánh hoàng hôn trên này đỉnh nóc kịch trần luôn á!”',
       '“Anh khó vậy, tụi em đi cả tiếng cano mới ra tới đây đó!”',
       'Không ai có giấy tờ gì. Chủ cano bảo: “Tôi chỉ chở thôi, khách muốn đi đâu thì đi.”', ['refuse', 'yard'], [], ['escort', 'give'],
       group=6, sneaky=True, mods=['calm', 'tourist', 'breeze'], weight=3,
       give='Sáu người leo lên ban công phòng đèn, một bạn ngồi vắt vẻo lên lan can để chụp. Gió giật một cái, cả nhóm tái mặt.'),
    _v('propose', '💍', 'Cặp đôi muốn cầu hôn trên đỉnh tháp', 'Lên ban công phòng đèn lúc nửa đêm để cầu hôn dưới ánh đèn quét',
       '“Anh ơi em đã lên kế hoạch cả năm rồi! Nửa đêm, ánh đèn quét qua, em quỳ xuống… Cho em mượn đỉnh tháp mười phút thôi!”',
       '“Em trả anh năm chục xu tiền “bồi dưỡng”, coi như anh góp phần vào hạnh phúc của tụi em nha!”',
       'Không có giấy tờ, thuê ghe ra đảo lúc chiều tối. Ghe hẹn hai giờ sáng mới quay lại đón.', ['refuse', 'yard'], ['shelter'], ['escort', 'give'],
       group=2, night=True, offer=50, sneaky=True, mods=['calm', 'tourist'], min_day=2, weight=2,
       give='Bạn cho hai người lên phòng đèn lúc nửa đêm. Cô gái đứng chắn ngay trước kính đèn để chụp, đèn tối một góc suốt mười phút.'),
    _v('vy', '📱', 'Vy Vlog · 300k follow', 'Livestream “một đêm trong phòng đèn hải đăng”',
       '“Hi anh gác đèn! Em đang live nè, cả nhà ơi đây là anh gác đèn cute nhất miền Trung! Anh cho em vào phòng đèn live xíu nha 🥺”',
       '“Anh không cho thì em quay cảnh anh từ chối, cả nhà phán xét nha 🙃”',
       'Không có giấy của xí nghiệp. Vy đưa một “thư mời hợp tác” tự in, logo mờ tịt.', ['refuse', 'yard'], [], ['escort', 'give'],
       npc=VY, group=3, sneaky=True, mods=['calm', 'tourist'], min_day=2, weight=3,
       give='Vy live ngay trong phòng đèn, cầm điện thoại sát kính quét. Clip lên xu hướng, kèm cảnh bạn dắt người lạ vào khu vực cấm.'),
    _v('ghost', '👻', 'Kênh YouTube “Đêm Rợn Người”', 'Quay phim ma lúc nửa đêm, xin tắt đèn mười phút “cho có không khí”',
       '“Đảo này đồn có hồn người gác đèn cũ lắm anh. Anh tắt đèn mười phút thôi, tụi em quay cảnh “đèn tự tắt”, view triệu luôn!”',
       '“Mười phút thôi mà, giờ này làm gì có tàu nào!”',
       'Bốn người, máy quay hồng ngoại, không giấy tờ. Ghe chở họ đã về bờ, hẹn sáng mai đón.', ['refuse', 'shelter'], ['report'], ['escort', 'give'],
       group=4, night=True, sneaky=True, min_day=3, weight=2,
       give='Bạn tắt đèn mười phút. Đúng lúc đó một tàu hàng đi ngang tìm mốc hòn Gió mà không thấy, phải gọi đài hỏi.'),
    _v('writer', '✍️', 'Anh Đức · nhà văn', 'Ở lại trên đảo một tuần “để sống thử đời người gác đèn”',
       '“Tôi có giấy của xí nghiệp đây. Tôi chỉ xin một góc nhà kho, một tuần thôi, tự nấu ăn, không phiền ai.”',
       '“Tôi viết về các anh mà. Người đọc cần thấy sự thật cô đơn của nghề này…”',
       'Giấy của xí nghiệp ghi rõ: “tham quan, phỏng vấn trong ngày”. Không có dòng nào cho ở lại.', ['escort'], ['yard', 'refuse'], ['give'],
       npc=DUC, permit=True, soft=True, weight=2,
       give='Anh Đức ở lại. Đêm thứ hai anh lên phòng đèn “tìm cảm hứng” lúc ba giờ sáng, quên đóng cửa ban công trong gió.'),
    _v('kayak', '🛶', 'Hai bạn chèo kayak lạc đường', 'Xin trú nhờ: trời sắp tối, gió lên, thuyền thủng',
       '“Anh ơi cho tụi em vào nhờ với… thuyền thủng, điện thoại ướt hết, tụi em lạnh quá…”',
       '“Tụi em không có giấy tờ gì hết, anh đừng đuổi tụi em…”',
       'Hai người ướt sũng, môi tím tái, không áo phao. Gió đang lên cấp 5, trời sắp tối.', ['shelter'], [], ['refuse', 'yard'],
       emergency=True, group=2, mods=['calm', 'breeze', 'tourist'], min_day=2, weight=2,
       give='Bạn cho hai người vào nhà trạm, nhưng không báo đài. Đêm đó cả nhà hai bạn báo mất tích, tàu cứu nạn ra tìm cả đêm.'),
    _v('fisher', '🤕', 'Ngư dân bị thương ở tay', 'Ghé đảo xin sơ cứu: tay rách vì dây lưới, máu thấm đỏ khăn',
       '“Chú ơi cho cháu ghé băng tạm cái tay, chảy máu hoài không cầm…”',
       '“Tụi cháu đi tàu cá, không có giấy gì đâu chú…”',
       'Vết rách dài ở bàn tay, quấn khăn bẩn. Tàu cá CL-6610-TS neo sát bến.', ['shelter'], [], ['refuse', 'yard'],
       emergency=True, group=1, min_day=2, weight=2,
       give='Bạn băng tạm cho anh ta rồi để tàu đi luôn, không báo đài. Hai ngày sau vết thương nhiễm trùng, tàu phải quay vào bờ gấp.'),
    _v('drone', '🚁', 'Anh thợ flycam', 'Bay flycam vòng quanh đèn lúc đèn đang quét “cho ảnh có vệt sáng”',
       '“Anh cho em bay một vòng quanh đỉnh tháp lúc đèn quét thôi, em bay giỏi lắm, chưa rơi lần nào!”',
       '“Em quay xong gửi anh làm ảnh đại diện luôn!”',
       'Không giấy phép bay, không giấy của xí nghiệp. Máy bay là loại lớn, cánh quạt to bằng bàn tay.', ['refuse', 'yard'], [], ['escort', 'give'],
       group=1, night=True, mods=['calm', 'tourist'], min_day=2, weight=2,
       give='Chiếc flycam quệt vào lan can phòng đèn rồi rơi, mảnh cánh quạt cứa một vệt dài trên kính bảo vệ.'),
    _v('nephew', '😎', 'Cháu của anh Khôi', 'Dẫn bạn bè lên đỉnh tháp “nhậu ngắm trăng”',
       '“Chú Khôi bảo em cứ ra, nói tên chú là được. Tụi em mang bia với mực, lên đỉnh tháp ngồi tí thôi.”',
       '“Gọi chú Khôi đi, chú nói là anh phải nghe à!”',
       'Không có giấy tờ. Gọi đài nhờ hỏi thì xí nghiệp nói anh Khôi không ký giấy nào.', ['refuse'], ['report', 'yard'], ['escort', 'give'],
       group=5, night=True, sneaky=True, min_day=3, weight=2,
       give='Năm thanh niên ngồi nhậu trên ban công phòng đèn. Một lon bia lăn xuống, vỡ kính bảo vệ.'),
    _v('shrine', '🧓', 'Ông cụ làng chài', 'Thắp hương miếu Bà trên mỏm đá cạnh trạm, như mọi rằm',
       '“Rằm nào ông cũng ra thắp hương miếu Bà, cầu cho tụi nhỏ đi biển bình an. Cháu cho ông đi nhờ lối sân trạm nhé.”',
       '“Ông đi chậm thôi mà, không đụng gì của trạm đâu.”',
       'Miếu Bà nằm ngoài rào trạm, lối đi phải qua sân. Ông cụ chống gậy, đi một mình.', ['escort'], ['yard'], ['refuse', 'give'],
       soft=True, group=1, mods=['calm', 'tourist', 'fog'], weight=2,
       give='Bạn chỉ tay cho ông tự đi. Ông trượt chân ở bậc đá rêu, may chỉ trầy đầu gối.'),
    _v('press', '🎤', 'Phóng viên báo tỉnh', 'Phỏng vấn và quay phim phòng đèn cho phóng sự “Người giữ lửa”',
       '“Chị có thẻ nhà báo đây. Phóng sự về các bạn mà, cho chị vào phòng đèn quay vài cảnh nhé.”',
       '“Chị làm phóng sự tích cực mà, em ngại gì?”',
       'Có thẻ nhà báo, nhưng không có giấy của xí nghiệp cho vào khu vực đèn.', ['yard'], ['refuse'], ['escort', 'give'],
       group=2, mods=['calm', 'tourist'], min_day=2, weight=2,
       give='Chị phóng viên quay trong phòng đèn. Phóng sự lên sóng kèm cảnh cửa phòng đèn mở toang, xí nghiệp gọi hỏi ngay.'),
    _v('cargo', '📦', 'Người lạ xin gửi hàng ở nhà kho trạm', 'Gửi mấy thùng hàng kín trong kho trạm “vài hôm”, trả trước một trăm xu',
       '“Anh cho em gửi mấy thùng này trong kho trạm vài hôm, có người tới lấy. Một trăm xu, em đưa trước luôn.”',
       '“Hai trăm. Hàng hợp pháp mà, anh khỏi hỏi.”',
       'Thùng dán kín, không giấy tờ, không ghi gì. Ghe của họ tắt đèn hành trình.', ['report'], ['refuse'], ['give', 'escort'],
       group=2, night=True, offer=100, min_day=4, weight=1,
       give='Bạn nhận tiền, cho gửi hàng. Tuần sau biên phòng ra đảo kiểm tra, mấy thùng hàng lậu nằm ngay trong kho trạm.'),
    _v('fake', '🕴️', 'Người tự xưng “đoàn kiểm tra”', 'Xin chìa khóa phòng đèn và sổ trực để “kiểm tra đột xuất”',
       '“Đoàn kiểm tra của trên. Cậu đưa chìa khóa phòng đèn với sổ trực đây, không cần báo ai.”',
       '“Cậu không hợp tác là tôi ghi biên bản cậu cản trở công vụ!”',
       'Không có quyết định kiểm tra, không thẻ ngành. Gọi đài hỏi thì xí nghiệp không cử đoàn nào.', ['refuse'], ['report'], ['give', 'escort'],
       group=2, min_day=4, weight=1,
       give='Bạn đưa chìa khóa. Hai người lục tung tủ, mang đi cuốn sổ trực và hai bình ắc quy dự phòng.'),
    _v('wedding', '👰', 'Đoàn chụp ảnh cưới', 'Chụp ảnh cưới trên ban công phòng đèn',
       '“Anh ơi cô dâu chú rể muốn có ảnh trên ban công đèn, váy bay trong gió đẹp xỉu. Tụi em xin mười phút thôi!”',
       '“Ảnh cưới cả đời có một lần mà anh…”',
       'Thợ ảnh có giấy phép kinh doanh của studio, không có giấy của xí nghiệp.', ['yard'], ['refuse'], ['escort', 'give'],
       group=5, mods=['calm', 'tourist'], min_day=2, weight=2,
       give='Cô dâu đứng trên ban công, gió giật lật váy che cả kính đèn. Thợ ảnh suýt rơi máy xuống chân tháp.'),
    _v('thung', '🧺', 'Tụi nhỏ chèo thúng ra đảo “thám hiểm”', 'Ở lại chơi đến tối, “ngủ lại đảo cho ngầu”',
       '“Tụi con chèo thúng ra đây nè chú! Cho tụi con ở lại tới tối coi đèn bật nha!”',
       '“Thúng tụi con chèo về được mà, chú đừng gọi ba mẹ tụi con…”',
       'Ba đứa nhỏ chừng mười tuổi, một cái thúng chai, không áo phao. Trời sắp chiều, gió trở hướng.', ['shelter'], [], ['refuse', 'give', 'yard'],
       emergency=True, group=3, soft=True, mods=['calm', 'tourist'], min_day=2, weight=2,
       give='Bạn để tụi nhỏ tự chèo thúng về lúc chiều. Gió trở, cái thúng xoay vòng giữa luồng, phải nhờ tàu cá kéo vào.'),
]
VISITOR = {x['id']: x for x in VISITORS}
VISITOR_GENTLE = 'tour'
V_OK = {   # how a visitor takes the keeper's answer when it works
    'escort': '{who} gật đầu, xếp hàng theo bạn đi tham quan, nghe kể chuyện đèn rất chăm chú.',
    'yard': '{who} chụp ảnh ở sân trạm với cái tháp làm nền. Ảnh vẫn đẹp, không ai phải trèo lên đâu.',
    'refuse': '{who} lầm bầm nhưng quay ra bến, chờ ghe đón.',
    'shelter': 'Bạn đưa {who} vào nhà trạm, lấy chăn khô, nước ấm, rồi gọi đài báo có người trú tạm trên đảo.',
    'report': 'Bạn gọi đài nhờ chuyển tin cho đồn biên phòng. {who} vội vã xuống ghe bỏ đi.',
}
V_SULK = '{who} hậm hực, nói vọng lại vài câu khó nghe, nhưng không làm gì thêm.'
V_SNEAK = '{who} lẻn qua cửa tháp, đang leo cầu thang xoắn lên phòng đèn!'
V_BLOWUP = '{who} nổi khùng, quay clip mặt bạn: “Gác đèn gì mà như quan!”'
V_BAD = {   # a wrong answer that is not giving in
    'refuse_emergency': 'Bạn từ chối người đang gặp nạn. Trời tối dần, gió lên, họ ngồi co ro ở bến đá.',
    'escort_nopermit': 'Bạn dẫn người không có giấy của xí nghiệp vào tháp. Nội quy trạm là để giữ đèn.',
    'refuse_permit': 'Người ta có giấy của xí nghiệp đàng hoàng mà bạn đuổi về. Xí nghiệp nhận ngay một cuộc gọi phàn nàn.',
}

# ---------------------------------------------------------------- the supply boat (tàu tiếp tế)
SUPPLY_EVERY = 7
SUPPLY_FIRST = 3
FUEL_CLAIM = 200
GOODS = [
    dict(id='rice', emoji='🍚', name='Gạo 25 kg'),
    dict(id='water', emoji='💧', name='Nước ngọt 20 bình'),
    dict(id='gas', emoji='🔥', name='Bình gas nấu ăn'),
    dict(id='veg', emoji='🥬', name='Rau củ tươi'),
    dict(id='fish', emoji='🐟', name='Thịt cá đông lạnh'),
    dict(id='parts', emoji='🧰', name='Bóng đèn dự phòng, nhớt máy'),
]
GOODS_IDS = [x['id'] for x in GOODS]
GOODS_STATE = {
    'ok': 'Đủ, còn tốt.',
    'short': 'Thiếu so với phiếu giao hàng.',
    'spoiled': 'Hỏng: dập nát, bốc mùi, không dùng được.',
}
BASKET = dict(name='Giỏ “hàng riêng” của chú Tư Lực', items='Xoài chín, cà phê phin, cá khô, hạt cho mèo Mun, mấy tờ báo tuần', fair=40)
SUPPLY_LINES = dict(
    claim='Chú Tư Lực chìa phiếu: “Dầu hai trăm lít đủ nghen. Ký đi cho chú còn chạy kịp con nước.”',
    sign_more='Chú Tư Lực: “Ký đủ hai trăm đi, thiếu chút đỉnh chuyến sau chú bù. Ai mà kiểm.”',
)

# ---------------------------------------------------------------- life on the rock
LONELY_MAX = 10
LONELY_TIRED = 7
FRESH_DAYS = 7
GARDEN_RIPE = 5
CALLS = [
    'Má: “Con ăn uống gì chưa? Mà nè, bao giờ dẫn bạn gái/bạn trai về cho má coi mặt?”',
    'Dì Ba: “Con bé nhà ông Tư mới đi du học về đó, dì gửi số cho con nha. Ở đảo hoài sao lấy vợ lấy chồng?”',
    'Ba: “Đèn đóm gì, về quê mở tiệm tạp hóa với ba cho rồi.” Rồi ba im lặng một lúc: “Giữ sức khỏe nha con.”',
    'Em gái: “Anh/chị ơi Tết này có về không? Mẹ để phần bánh tét trong tủ lạnh từ giờ rồi đó 😭”',
    'Bà ngoại: “Ngoài đó có ma không con? Bà gửi theo tàu cái bùa bình an nghen.”',
    'Má: “Thằng con nhà hàng xóm cưới vợ rồi đó. Con thì cưới… cái đèn hả?”',
    'Cô Út: “Ở ngoài đó tiền lương có dư không? Cô mượn chút sửa nhà, Tết trả.”',
]
PET_LINES = [
    'Mèo Mun cọ đầu vào chân bạn, kêu rừ rừ như cái mô-tơ đèn.',
    'Mun tha về một con cá chuồn còn giãy, đặt trước cửa như khoe chiến lợi phẩm.',
    'Mun nằm phơi bụng trên bậc đá, nheo mắt nhìn đàn hải âu.',
    'Mun nhảy lên bàn trực, ngồi đè lên cuốn sổ đúng chỗ bạn đang ghi.',
]
GARDEN_LINES = [
    'Bạn tưới mấy thùng xốp rau muống, hành lá với hai gốc ớt chen giữa khe đá.',
    'Bạn chắn lại tấm lưới che gió cho luống rau, nhổ vài cọng cỏ biển.',
    'Mấy đọt rau muống mới nhú, xanh mướt giữa nền đá xám.',
]
GARDEN_HARVEST = 'Bạn cắt được một rổ rau muống, nấu canh với con cá chuồn Mun bắt. Bữa tối ngon nhất tuần.'

# ---------------------------------------------------------------- intro
INTRO = dict(
    title='Giới thiệu nghề: người gác hải đăng',
    lead=f'Một ngọn tháp trắng trên {ISLAND}, mười hai hải lý ngoài khơi. Đèn quét đêm đêm cho tàu thuyền về {PORT}. '
         f'Bạn vào {COMPANY}, theo chú Bảy Đèn học giữ lửa.',
    work=[('🌅', 'Sáng: tắt đèn đúng giờ, kiểm từng thiết bị, lau kính, ghi sổ dầu'), ('🌬️', 'Quan trắc gió, sóng, tầm nhìn, áp suất; báo đài duyên hải'),
          ('🌇', 'Chiều: thắp đèn đúng giờ, đếm chớp so với danh mục đèn'), ('🔭', 'Canh biển: tàu gặp nạn thì báo đài đúng mức, không tự ra khơi'),
          ('🚤', 'Khách ra đảo: xem giấy tờ, đi kèm, không ai vào phòng đèn'), ('⛴️', 'Ngày tàu tiếp tế: đo dầu, kiểm hàng, ký đúng số thật'),
          ('🐈‍⬛', 'Nuôi mèo Mun, chăm vườn rau trên đá, gọi điện về nhà cho đỡ nhớ')],
    meet=[('🤳', 'Khách đòi lên đỉnh tháp sống ảo'), ('💍', 'Cặp đôi đòi cầu hôn trên ban công lúc nửa đêm'), ('👻', 'Kênh ma đòi tắt đèn “cho có không khí”'),
          ('🎣', 'Ông Sáu Ghe: “quay đèn về phía lưới giùm”'), ('📻', 'Anh Khôi: kiểm tra qua bộ đàm, đòi đủ thứ trời ơi'),
          ('⛴️', 'Chú Tư Lực: dầu thiếu mà đòi ký đủ'), ('📞', 'Má gọi: “Bao giờ lấy vợ lấy chồng?”')],
    stars=[('💡', 'Đèn sáng đúng giờ, đúng đặc tính'), ('📒', 'Sổ trực, sổ dầu ghi đúng sự thật'), ('📻', 'Báo đài rõ ràng, đúng mức khẩn cấp'),
           ('🛟', 'Cứu người bằng phao, bằng bộ đàm, không liều mạng'), ('✋', 'Không ai vào phòng đèn trái nội quy'), ('🏠', 'Người gặp nạn luôn được trú tạm')],
)

# ---------------------------------------------------------------- regulars' small stories (by PEOPLE index)
REG_STORY = {
    BAY: ('Chú Bảy: “Đèn tắt một đêm là có người không về nhà được. Nhớ vậy là đủ.”',
          'Chú Bảy kể năm bão lớn, chú quay tay mô-tơ suốt đêm cho đèn khỏi đứng.',
          'Chú Bảy đưa bạn cái giẻ lau kính bằng da hươu cũ: “Giữ lấy. Kính sạch thì đèn mới xa.”'),
    YEN: ('Chị Hải Yến: “Báo rõ thế là chị chép một lần là xong.”', 'Chị Hải Yến bảo cả đài khen bản tin của trạm Hòn Gió gọn, đúng.',
          'Chị Hải Yến gửi theo tàu tiếp tế một hộp bánh in: “Cho người giữ đèn Hòn Gió.”'),
    SAU: ('Ông Sáu Ghe càu nhàu nhưng gật đầu: “Ờ, trạm nói cũng phải.”', 'Ông Sáu Ghe gọi lên trạm hỏi bản tin trước khi xuất bến.',
          'Ông Sáu Ghe gửi lên đảo một con cá thu to: “Cảm ơn mấy lần cậu gọi tui.”'),
    THAM: ('Cô Thắm: “Đi theo em, khách nghe kể chuyện đèn mê luôn.”', 'Cô Thắm in thêm dòng “tôn trọng nội quy trạm đèn” vào tờ rơi tour.',
           'Cô Thắm mang ra một xấp thiệp khách du lịch viết tặng trạm Hòn Gió.'),
}

# ---------------------------------------------------------------- the day's words
DAY_LINES = dict(odd='🙄 Gặp {n} chuyện oái oăm, xử lý đẹp {ok}.', record='📁 Hồ sơ: {label}.',
                 tired='😮‍💨 Mệt rồi: thưởng ca chỉ còn một nửa. Xin nghỉ bù ở nhà trạm.',
                 lonely='🏝️ Nhớ nhà quá: gọi điện về nhà, chơi với Mun, chăm vườn rau cho đỡ trống trải.')
