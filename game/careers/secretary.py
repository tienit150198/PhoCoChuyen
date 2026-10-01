"""Công ty CP Cánh Diều — the director's secretary (plugin career).

Real desk work of a busy director's office, checked by hand: sort the morning's mail into what the
director must see, what to answer yourself, what goes to a department and what is a scam (a fake
"director" asking for an urgent transfer, a supplier "changing bank accounts"); take down a phone
message where the caller corrects himself; proof-read letters against the director's note and the
calendar; fit the director's meetings into rooms and hours; plan the steps of a board meeting or a
business trip without the harmful shortcuts; and handle the angry supplier at reception.

The director changes his mind. Often. The dossier mechanics are shared with the other Cánh Diều
desks (office_work.py). Every rule here is a simplified GAME rule, not legal advice.
"""
from __future__ import annotations

from . import office_work as ow

ID = 'secretary'
P = 'tk_'

PEOPLE = [
    ('Anh Quân', 'Giám đốc Công ty Cánh Diều', 'Quyết nhanh, đổi ý còn nhanh hơn; ghét bị làm phiền giờ trưa.', 'bossy'),
    ('Chị Khuê', 'Trợ lý cũ, nay ở phòng kinh doanh', 'Chỉ việc tận tình, câu cửa miệng “sếp ghét nhất là…”.', 'warm'),
    ('Ông Lực', 'Chủ xưởng vải Lực Thành (nhà cung cấp)', 'Nóng tính, đòi gặp giám đốc ngay.', 'sour'),
    ('Linh', 'Nhân viên kinh doanh', 'Hay nhờ chen vào lịch sếp.', 'genz'),
    ('Cô Hằng', 'Kế toán trưởng', 'Chỉ tin giấy có dấu đỏ.', 'picky'),
    ('Nhi', 'Lễ tân', 'Hiền, hay hoảng khi khách to tiếng.', 'quiet'),
]
BOSS = 'Anh Quân'

# ================================================================ dossier 1: the morning mail
MAIL_BINS = [dict(id='boss', label='Trình sếp', emoji='📌'), dict(id='self', label='Tự trả lời', emoji='✍️'),
             dict(id='dept', label='Chuyển phòng ban', emoji='📤'), dict(id='junk', label='Rác / lừa đảo', emoji='🗑️')]
SCHOOLS = ('Trường Tiểu học Hoa Sen', 'Trường THCS Lê Lợi', 'Trường Tiểu học Bình Minh', 'Trung tâm Anh ngữ Ngôi Sao')
SHOPS = ('Shop Cặp Xinh', 'Nhà sách Mặt Trời', 'Văn phòng phẩm Thiên Long Phát', 'Cửa hàng Bé Đến Trường')


def _mails(rng, used: set) -> list:
    """Every kind of mail the director's office gets: (key, bin, from, subject, text, why, sev, code, tier)."""
    a, _ = ow.person(rng, used)
    b, _ = ow.person(rng, used)
    big = rng.randrange(60, 160) * 1000
    small = rng.randrange(20, 45) * 100
    return [
        ('big', 'boss', rng.choice(SCHOOLS[:2] + SHOPS[1:2]), f'Đơn đặt balo năm học mới · {ow.xu(big)} xu',
         'Cần giám đốc ký hợp đồng trước thứ Sáu.', 'Đơn từ 50.000 xu cần giám đốc ký.', 2, 'in_big', 0),
        ('small', 'dept', rng.choice(SHOPS), f'Đặt 20 balo · tổng {ow.xu(small)} xu', 'Nhờ báo giá và ngày giao.',
         'Đơn dưới 50.000 xu: chuyển phòng kinh doanh lo.', 1, 'in_small', 0),
        ('gov', 'boss', 'Sở Công Thương', 'Giấy mời hội nghị doanh nghiệp', 'Kính mời đại diện lãnh đạo công ty tham dự.',
         'Cơ quan nhà nước mời lãnh đạo: trình sếp.', 2, 'in_gov', 0),
        ('tax', 'boss', 'Chi cục Thuế quận', 'Thông báo lịch kiểm tra thuế', 'Đề nghị công ty chuẩn bị hồ sơ năm 2024.',
         'Thư của cơ quan thuế: trình sếp ngay.', 2, 'in_tax', 1),
        ('press', 'boss', 'Phóng viên báo Thị Trường', 'Xin phỏng vấn về tin cắt giảm nhân sự', 'Mong giám đốc trả lời trước 17 giờ.',
         'Báo chí: chỉ giám đốc quyết định trả lời.', 2, 'in_press', 1),
        ('expo', 'boss', 'Ban tổ chức Hội chợ Đồ dùng học tập', 'Mời đặt gian hàng hội chợ', 'Phí gian hàng 30.000 xu, cần lãnh đạo xác nhận.',
         'Khoản chi lớn cần lãnh đạo xác nhận.', 1, 'in_expo', 0),
        ('appt', 'self', f'Anh {ow.short(a)} · In ấn Phúc Lộc', 'Xin hẹn gặp giám đốc tuần sau', 'Muốn giới thiệu mẫu in túi mới.',
         'Xin lịch hẹn: thư ký trả lời theo lịch trống của sếp.', 1, 'in_appt', 0),
        ('thanks', 'self', rng.choice(SCHOOLS), 'Thư cảm ơn đã tặng 100 cặp sách', 'Các em học sinh gửi lời cảm ơn công ty.',
         'Thư cảm ơn: thư ký trả lời thay, báo sếp trong bản tin cuối ngày.', 1, 'in_thanks', 0),
        ('ack', 'self', 'Xưởng vải Lực Thành', 'Đã nhận đơn đặt vải, giao ngày 20', 'Nhờ xác nhận lại địa chỉ kho nhận.',
         'Chỉ cần xác nhận địa chỉ kho — thư ký trả lời được.', 1, 'in_ack', 0),
        ('itmail', 'self', 'Anh Long (IT) <long@canhdieu.vn>', 'Lịch bảo trì máy chủ tối thứ Bảy', 'Nhờ chị báo giúp sếp tắt máy trước khi về.',
         'Thư thật từ IT nội bộ (đúng tên miền canhdieu.vn): xác nhận và nhắc sếp.', 1, 'in_it', 1),
        ('invoice', 'dept', 'Công ty Điện lực', 'Hóa đơn tiền điện tháng 9', 'Hạn thanh toán ngày 25.',
         'Hóa đơn: chuyển phòng kế toán.', 1, 'in_invoice', 0),
        ('cv', 'dept', b, 'Ứng tuyển thợ may mẫu', 'Em gửi CV và ảnh sản phẩm đã may.', 'CV: chuyển phòng nhân sự.', 1, 'in_cv', 0),
        ('pc', 'dept', 'Nhi (lễ tân)', 'Máy tính lễ tân không lên màn hình', 'Em bật mãi không được ạ.', 'Máy hỏng: chuyển IT.', 1, 'in_pc', 0),
        ('complain', 'dept', f'Phụ huynh {a}', 'Balo con tôi đứt quai sau 2 tuần', 'Yêu cầu công ty trả lời trong hôm nay.',
         'Khiếu nại sản phẩm: chuyển kinh doanh, họ trả lời trong ngày.', 1, 'in_complain', 0),
        ('ceo', 'junk', 'Anh Quân <quan.canhdieu.gd@gmail.com>', 'GẤP: chuyển 85.000 xu cho đối tác trước 11h',
         'Anh đang họp, không nghe máy được. Em chuyển ngay vào số tài khoản này rồi báo anh.',
         'Giả danh giám đốc: địa chỉ gmail lạ, đòi chuyển tiền gấp, không cho gọi lại — lừa đảo.', 3, 'in_ceo', 1),
        ('bankchg', 'junk', 'Lực Thành Kế toán <lucthanh.ketoan@outlook.com>', 'Thông báo đổi số tài khoản nhận tiền',
         'Từ tháng này vui lòng chuyển tiền vào tài khoản mới dưới đây.',
         'Đổi số tài khoản qua email: không làm theo, gọi lại số đã lưu để xác minh.', 3, 'in_bank', 1),
        ('prize', 'junk', 'Ban tổ chức Quay số Tri ân', 'Chúc mừng công ty trúng xe máy', 'Bấm vào link để nhận thưởng.',
         'Trúng thưởng không tham gia: rác.', 1, 'in_prize', 0),
        ('phish', 'junk', 'Bộ phận IT <it-support@canhdieu-secure.net>', 'Mật khẩu email sắp hết hạn', 'Đăng nhập lại tại đường link này.',
         'Tên miền lạ (không phải canhdieu.vn), đòi đăng nhập qua link: lừa đảo.', 2, 'in_phish', 0),
        ('ads', 'junk', 'Khóa học Làm giàu 4.0', 'Giảm 90% hôm nay', 'Chỉ còn 3 suất cuối cùng!', 'Quảng cáo: rác.', 1, 'in_ads', 0),
    ]


def g_inbox(rng, ctx: dict) -> dict:
    tier = ctx['tier']
    used: set = set()
    rows = [r for r in _mails(rng, used) if r[8] <= min(1, tier)]
    by_bin = {}
    for r in rows:
        by_bin.setdefault(r[1], []).append(r)
    pick = [rng.choice(by_bin[b['id']]) for b in MAIL_BINS]
    n = min(9, 6 + (tier >= 1) + (tier >= 2) + ctx['more'])
    rest = [r for r in rows if r not in pick]
    pick += rng.sample(rest, n - len(pick))
    rng.shuffle(pick)
    items = [dict(id=f'm{i}', title=r[3], sub=r[2], lines=[r[4]], note=None, _bin=r[1], _why=r[5], _sev=r[6], _code=r[7], _key=r[0])
             for i, r in enumerate(pick)]
    tw = None
    if ctx['twist']:
        keys = {it['_key']: it for it in items}
        if 'expo' in keys:
            tw = dict(item=keys['expo']['id'], bin='dept', why='Sếp đã giao hội chợ cho phòng kinh doanh.', sev=1,
                      note='Anh Quân nhắn: “Hội chợ năm nay anh giao hết cho phòng kinh doanh, đừng trình anh nữa.”')
        elif 'appt' in keys:
            tw = dict(item=keys['appt']['id'], bin='boss', why='Sếp muốn tự gọi cho người này.', sev=1,
                      note='Anh Quân nhắn: “Thư anh Phúc Lộc đưa anh, anh tự gọi — người quen cũ.”')
        elif 'big' in keys:
            tw = dict(item=keys['big']['id'], bin='dept', why='Sếp đã ủy quyền chị Khuê ký đơn này.', sev=1,
                      note='Anh Quân nhắn: “Đơn của trường anh ủy quyền chị Khuê ký, chuyển kinh doanh luôn.”')
        if tw:
            tw['at'] = n - 2
    for it in items:
        it.pop('_key')
    return dict(npc=0, title=f'Hộp thư sáng nay ({n} thư)',
                opening='Anh Quân vừa đi ngang: “Em lọc thư giúp anh. Cái gì anh phải xem thì để riêng, đừng để anh đọc thư rác.”',
                brief=f'Xếp {n} thư vào bốn khay: trình sếp, tự trả lời, chuyển phòng ban, rác/lừa đảo.',
                papers=[dict(id='rule', emoji='🗂️', title='Sếp dặn', lines=[
                    'Trình sếp: đơn từ 50.000 xu, cơ quan nhà nước, báo chí, khoản chi lớn cần lãnh đạo.',
                    'Tự trả lời: xin lịch hẹn, cảm ơn, xác nhận thông tin đơn giản.',
                    'Chuyển phòng: hóa đơn → kế toán · CV → nhân sự · máy hỏng → IT · khiếu nại, đơn nhỏ → kinh doanh.',
                    'Rác/lừa đảo: trúng thưởng, quảng cáo, đòi chuyển tiền gấp, đổi số tài khoản, link đăng nhập lạ.',
                    'Email thật của công ty luôn có đuôi @canhdieu.vn.'])],
                work=dict(type='sort', bins=MAIL_BINS, items=items, _twist=tw))


# ================================================================ dossier 2: a phone message
TOPICS = [dict(id='pay', label='Thanh toán / công nợ'), dict(id='quote', label='Hỏi giá / đặt hàng'), dict(id='complain', label='Khiếu nại'),
          dict(id='ship', label='Giao nhận hàng'), dict(id='meet', label='Xin hẹn gặp')]
SPOKEN = [('hai giờ rưỡi chiều', '14:30'), ('ba giờ chiều', '15:00'), ('bốn giờ kém mười lăm chiều', '15:45'),
          ('mười giờ sáng', '10:00'), ('chín rưỡi sáng', '09:30'), ('bốn giờ chiều', '16:00'), ('mười một giờ trưa', '11:00')]
LATER = [('năm giờ chiều', '17:00'), ('bốn rưỡi chiều', '16:30')]


def _phone(rng) -> str:
    return '09' + ''.join(rng.choice('0123456789') for _ in range(8))


def _say(num: str) -> str:
    return f'{num[:4]} {num[4:7]} {num[7:]}'


def _bad_phone(rng, num: str) -> str:
    i = rng.randrange(4, 9)
    a, b = num[i], num[i + 1]
    if a == b:
        return num[:i + 1] + str((int(b) + 2) % 10) + num[i + 2:]
    return num[:i] + b + a + num[i + 2:]


def g_calls(rng, ctx: dict) -> dict:
    tier = ctx['tier']
    used: set = set()
    name, female = ow.person(rng, used)
    hon = 'chị' if female else 'anh'
    me = 'tôi'
    phone, said_t = _phone(rng), rng.choice(SPOKEN)
    wrong_phone = _bad_phone(rng, phone)
    kind = rng.choice(('pay', 'quote', 'complain', 'ship', 'meet', 'bank'))
    amt = rng.randrange(20, 90) * 1000
    other = _phone(rng)
    if kind == 'pay':
        company, topic = 'Xưởng vải Lực Thành', 'pay'
        lines = [f'Alô, {me} là {name}, kế toán bên {company}. Cho {me} gặp anh Quân.',
                 f'Khoản tiền vải tháng trước, {ow.xu(amt)} xu, quá hạn năm hôm rồi. Nhờ anh Quân gọi lại cho {me}.']
    elif kind == 'quote':
        company, topic = rng.choice(SCHOOLS), 'quote'
        lines = [f'Chào em, {me} là {name}, phụ trách mua sắm của {company}.',
                 f'Trường muốn đặt khoảng {rng.choice((150, 200, 300))} balo cho học sinh lớp 1, cần báo giá. Số tổng đài trường là 028 3{rng.randrange(1000000, 9999999)}, nhưng em đừng gọi số đó, giờ hành chính không ai nghe đâu.']
    elif kind == 'complain':
        company, topic = 'Phụ huynh (khách lẻ)', 'complain'
        lines = [f'Alô! {me} là {name}, phụ huynh. Balo mua bên các anh chị mới hai tuần đã đứt quai!',
                 f'Mã đơn của {me} là CD-{rng.randrange(10000, 99999)}. {me.capitalize()} cần người có trách nhiệm gọi lại.']
    elif kind == 'ship':
        company, topic = 'Vận tải Nhanh Như Gió', 'ship'
        lines = [f'Chào em, anh {name} bên {company}. Xe chở vải cho Cánh Diều bị kẹt cầu.',
                 f'Xe đến trễ, cần người ở kho ký nhận. Hotline công ty anh là 1900 {rng.randrange(1000, 9999)}, nhưng em gọi thẳng di động anh cho nhanh.']
    elif kind == 'meet':
        company, topic = 'Công ty Khóa kéo Sao Mai', 'meet'
        lines = [f'Chào em, {me} là {name}, giám đốc kinh doanh {company}.',
                 f'{me.capitalize()} muốn hẹn gặp anh Quân tuần sau để giới thiệu mẫu khóa kéo mới.']
    else:
        company, topic = 'Ngân hàng Phương Nam', 'pay'
        lines = [f'Chào em, {me} là {name}, cán bộ tín dụng {company}.',
                 'Hồ sơ vay của công ty còn thiếu một chữ ký trên giấy nhận nợ, cần xử lý trước khi giải ngân.']
    script = [dict(who='📞 Khách', text=lines[0]), dict(who='🙋 Bạn', text='Dạ anh Quân đang họp ạ. Mình để lại lời nhắn giúp em nhé?'),
              dict(who='📞 Khách', text=lines[1])]
    if tier >= 1:
        script.append(dict(who='📞 Khách', text=f'Số {me}: {_say(wrong_phone)}… à không, nhầm, {_say(phone)}. Số kia là của vợ {me}.'
                           if not female else f'Số {me}: {_say(wrong_phone)}… à không, nhầm, {_say(phone)}. Số kia là của chồng {me}.'))
    else:
        script.append(dict(who='📞 Khách', text=f'Số {me} là {_say(phone)}.'))
    script.append(dict(who='📞 Khách', text=f'Gọi lại sau {said_t[0]} nhé, trước đó {me} không nghe máy được.'))
    if tier >= 2:
        script.append(dict(who='📞 Khách', text=f'À, có ai hỏi thì số bàn {me} là {_say(other)}, nhưng gọi di động thôi nhé.'))
    alts = [f'{x} {name}' for x in ('anh', 'chị', 'ông', 'bà')]
    fields = [dict(id='name', label='Người gọi (họ tên)', kind='text', _ok=name, _alt=alts, _why='Ghi đủ họ tên để sếp biết ai.', _sev=1),
              dict(id='company', label='Gọi từ đâu', kind='text', _ok=company,
                   _alt=[company.replace('Công ty ', ''), company.replace('Ngân hàng ', ''), company.split(' (')[0]], _why='Ghi đúng tên đơn vị.', _sev=1),
              dict(id='phone', label='Số gọi lại', kind='digits', _ok=phone, _why='Người gọi đã sửa lại số — lấy số sau cùng.', _sev=2, _code='call_phone'),
              dict(id='time', label='Gọi lại lúc (24 giờ, vd 14:30)', kind='time', _ok=said_t[1], _why=f'“{said_t[0]}” là {said_t[1]}.', _sev=1),
              dict(id='topic', label='Việc gì', kind='pick', opts=TOPICS, _ok=topic, _why='Chọn đúng việc để sếp biết gọi lại chuẩn bị gì.', _sev=1)]
    tw = None
    if ctx['twist']:
        later = rng.choice([x for x in LATER if x[1] != said_t[1]])
        tw = dict(at=0, field='time', ok=later[1], why=f'Người gọi đã đổi giờ: “{later[0]}” là {later[1]}.',
                  note=f'{name} vừa gọi lại lần nữa — nghe máy đi!',
                  line=dict(who='📞 Khách (gọi lại)', text=f'À em ơi, {me} đổi giờ nhé: {later[0]} mới gọi được.'))
    return dict(npc=0, title=f'Ghi lời nhắn: {name}',
                opening='Điện thoại bàn reo. Anh Quân đang họp, chị Khuê nhắc: “Ghi lời nhắn cho đủ, sai một số là sếp gọi nhầm người đấy.”',
                brief='Đọc cuộc gọi, ghi lời nhắn cho sếp: ai gọi, từ đâu, số gọi lại, giờ gọi lại, việc gì.',
                papers=[dict(id='rule', emoji='📝', title='Mẫu lời nhắn', lines=['Ghi đúng họ tên, số sau cùng người gọi đọc.',
                                                                              'Giờ ghi theo 24 giờ: 2 giờ rưỡi chiều = 14:30.'])],
                work=dict(type='fields', script=script, fields=fields, _twist=tw))


# ================================================================ dossier 3: proof-reading a letter
SUPPLIERS = [('Ông', 'Nguyễn Văn Lực', 'Giám đốc', 'Xưởng vải Lực Thành', 'mét vải canvas'),
             ('Bà', 'Trần Thị Thu', 'Giám đốc', 'Công ty Khóa kéo Sao Mai', 'bộ khóa kéo'),
             ('Ông', 'Phạm Quốc Hưng', 'Trưởng phòng kinh doanh', 'Công ty Bao bì Hưng Thịnh', 'thùng carton')]
TIMES = ('8 giờ 30', '9 giờ 00', '10 giờ 00', '14 giờ 00', '15 giờ 30')
HOLIDAYS = [('Quốc khánh', (1, 9), 2), ('Tết Dương lịch', (1, 1), 1), ('Giỗ Tổ Hùng Vương', (7, 4), 1)]
YEAR = 2025


def _d(d: int, m: int) -> str:
    return f'{d:02d}/{m:02d}/{YEAR}'


def _letter_invite(rng, ctx: dict) -> dict:
    hon, name, role, company, unit = rng.choice(SUPPLIERS)
    other_hon = 'Bà' if hon == 'Ông' else 'Ông'
    m = rng.choice((10, 11))
    d = rng.randrange(3, 27)
    while ow.weekday(d, m, YEAR) in ('thứ Bảy', 'Chủ nhật'):
        d += 1
    wd = ow.weekday(d, m, YEAR)
    t = rng.choice(TIMES)
    qty = rng.choice((5000, 8000, 12000, 15000))
    new_t = rng.choice([x for x in TIMES if x != t])
    paras = [
        ('p', ['Kính gửi: ', dict(id='to', right=f'{hon} {name}', wrong=[f'{hon} {ow.plain_text(name)}', f'{other_hon} {name}'],
                                  why='Đúng danh xưng và tên có dấu như danh thiếp.', code='lt_name'),
               ' — ', dict(id='role', right=role, wrong=['Phó giám đốc', 'Kế toán trưởng', 'Giám đốc' if role != 'Giám đốc' else 'Chủ tịch'],
                           why='Đúng chức danh người nhận.', code='lt_role'), f', {company}.']),
        ('p', ['Công ty CP Cánh Diều ', dict(id='respect', right='trân trọng kính mời', wrong=['chân trọng kính mời', 'yêu cầu'],
                                             why='“Trân trọng” viết với tr; thư mời không dùng “yêu cầu”.', code='lt_spell'),
               f' {hon.lower()} đến làm việc lúc ', dict(id='time', right=t, wrong=[x for x in TIMES if x not in (t, new_t)][:2],
                                                        why='Giờ theo ghi chú của sếp.', sev=2, code='lt_time'),
               ', ', dict(id='wd', right=wd, wrong=[x for x in ow.WEEKDAYS[:5] if x != wd][:2], why=f'Ngày {_d(d, m)} là {wd} (xem lịch).', code='lt_wd'),
               ', ngày ', dict(id='date', right=_d(d, m), wrong=[_d(d + 1, m), _d(d, m + 1 if m < 12 else 1)], why='Ngày theo ghi chú của sếp.', sev=2,
                               code='lt_date'), ', tại Phòng họp lớn.']),
        ('p', ['Nội dung: thống nhất đơn đặt ', dict(id='qty', right=ow.xu(qty), wrong=[ow.xu(qty // 10), ow.xu(qty * 10)],
                                                     why='Số lượng theo ghi chú của sếp.', sev=2, code='lt_qty'), f' {unit} cho mùa tựu trường.']),
        ('p', [dict(id='close', right=f'Rất mong {hon.lower()} sắp xếp thời gian tham dự.',
                    wrong=[f'Đề nghị {hon.lower()} có mặt đúng giờ, nếu không sẽ hủy đơn.', 'Hẹn gặp lại nha!'],
                    why='Thư mời đối tác: lời lẽ lịch sự, trang trọng.', code='lt_tone')]),
        ('sig', ['Trân trọng, Giám đốc ', dict(id='sig', right='Trần Minh Quân', wrong=['Trần Minh Quang', 'Trần Quân Minh'],
                                               why='Tên giám đốc phải đúng.', sev=2, code='lt_sig')]),
    ]
    twist = None
    if ctx['twist']:
        twist = dict(seg='time', to=new_t, note=f'Anh Quân đổi ý: “Dời giờ hẹn sang {new_t} nhé, sửa thư trước khi gửi.”', why='Sếp đã dời giờ hẹn.')
    return dict(title=f'Soát thư mời: {hon} {name}', who=2,
                paras=paras, twist=twist,
                papers=[dict(id='memo', emoji='🗒️', title='Ghi chú của anh Quân', lines=[
                            f'Mời {hon.lower()} {name} — {role}, {company}.', f'Hẹn {t}, ngày {_d(d, m)}, Phòng họp lớn.',
                            f'Bàn đơn {ow.xu(qty)} {unit}.', 'Ký: Giám đốc Trần Minh Quân.']),
                        dict(id='cal', emoji='📅', title=f'Lịch tháng {m}', lines=[f'{ow.weekday(x, m, YEAR).capitalize()}: {_d(x, m)}'
                                                                                    for x in range(max(1, d - 2), min(28, d + 3))])])


def _letter_holiday(rng, ctx: dict) -> dict:
    name, (d, m), n = rng.choice(HOLIDAYS)
    end_d = d + n - 1
    back_d = end_d + 1
    while ow.weekday(back_d, m, YEAR) in ('thứ Bảy', 'Chủ nhật'):
        back_d += 1
    back = f'{ow.weekday(back_d, m, YEAR)}, ngày {_d(back_d, m)}'
    paras = [
        ('h', [f'THÔNG BÁO NGHỈ LỄ {name.upper()}']),
        ('p', ['Kính gửi: ', dict(id='to', right='Toàn thể cán bộ, nhân viên', wrong=['Các bạn', 'Phòng kế toán'],
                                  why='Thông báo chung gửi toàn công ty.', code='lt_to')]),
        ('p', ['Công ty thông báo lịch ', dict(id='nghi', right='nghỉ', wrong=['nghĩ', 'ngỉ'], why='“Nghỉ” (nghỉ ngơi) dấu hỏi.', code='lt_spell'),
               f' lễ {name} từ ngày ', dict(id='start', right=_d(d, m), wrong=[_d(d + 1, m), _d(d, m % 12 + 1)], why='Theo quyết định của giám đốc.', sev=2,
                                            code='lt_start'),
               ' đến hết ngày ', dict(id='end', right=_d(end_d, m), wrong=[_d(end_d + 1, m), _d(end_d + 2, m)], why='Theo quyết định của giám đốc.', sev=2,
                                     code='lt_end'), ' (', dict(id='n', right=f'{n} ngày', wrong=[f'{n + 1} ngày', f'{n + 2} ngày'],
                                                              why='Đếm đúng số ngày nghỉ.', code='lt_days'), ').']),
        ('p', ['Nhân viên đi làm lại vào ', dict(id='back', right=back, wrong=[f'{ow.weekday(end_d, m, YEAR)}, ngày {_d(end_d, m)}',
                                                                                f'thứ Hai, ngày {_d(back_d + 1, m)}'],
                                               why='Ngày đi làm lại là ngày làm việc đầu tiên sau kỳ nghỉ (xem lịch).', sev=2, code='lt_back'), '.']),
        ('p', ['Xưởng bố trí trực bảo vệ theo ', dict(id='roster', right='lịch phân công đính kèm', wrong=['ý kiến cá nhân', 'lịch năm ngoái'],
                                                       why='Trực lễ theo lịch phân công đã duyệt.', code='lt_roster'), '.']),
        ('sig', ['Giám đốc ', dict(id='sig', right='Trần Minh Quân', wrong=['Trần Minh Quang', 'Trần Quân Minh'], why='Tên giám đốc phải đúng.', sev=2,
                                   code='lt_sig')]),
    ]
    twist = None
    if ctx['twist']:
        twist = dict(seg='to', to='Quý đối tác và toàn thể nhân viên', why='Sếp muốn gửi cả đối tác.',
                     note='Anh Quân: “Thông báo này gửi cả đối tác nữa, sửa dòng Kính gửi giúp anh.”')
    cal = [f'{ow.weekday(x, m, YEAR).capitalize()}: {_d(x, m)}' for x in range(max(1, d - 1), min(28, back_d + 2))]
    return dict(title=f'Soát thông báo nghỉ {name}', who=0, paras=paras, twist=twist,
                papers=[dict(id='memo', emoji='🗒️', title='Quyết định của giám đốc', lines=[
                            f'Nghỉ lễ {name}: {n} ngày, từ {_d(d, m)} đến hết {_d(end_d, m)}.', 'Trực bảo vệ theo lịch phân công đính kèm.',
                            'Ký: Giám đốc Trần Minh Quân.']), dict(id='cal', emoji='📅', title=f'Lịch tháng {m}', lines=cal)])


def _letter_reply(rng, ctx: dict) -> dict:
    used: set = set()
    name, female = ow.person(rng, used)
    hon = 'Bà' if female else 'Ông'
    code = f'CD-{rng.randrange(10000, 99999)}'
    wrong_code = code[:4] + code[5] + code[4] + code[6:] if code[4] != code[5] else code[:-1] + str((int(code[-1]) + 1) % 10)
    paras = [
        ('p', ['Kính gửi ', dict(id='to', right=f'{hon} {name}', wrong=[f'{hon} {ow.plain_text(name)}', f'{"Ông" if female else "Bà"} {name}'],
                                 why='Đúng danh xưng, tên có dấu như đơn khiếu nại.', code='lt_name')]),
        ('p', ['Cánh Diều đã nhận phản ánh về đơn hàng ', dict(id='code', right=code, wrong=[wrong_code, code.replace('CD-', 'CĐ-')],
                                                             why='Mã đơn phải khớp đơn khiếu nại.', code='lt_code'), '.']),
        ('p', [dict(id='sorry', right='Chúng tôi thành thật xin lỗi vì sự cố này.', wrong=['Lỗi này do quý khách sử dụng sai cách.', 'Chuyện nhỏ thôi ạ.'],
                    why='Trả lời khiếu nại: nhận lỗi, không đổ cho khách.', sev=2, code='lt_tone')]),
        ('p', ['Theo chính sách bảo hành, chiếc balo sẽ được ', dict(id='fix', right='đổi mới miễn phí', wrong=['sửa lại có tính phí', 'giảm giá 10% lần sau'],
                                                                     why='Lỗi đường may được đổi mới miễn phí.', sev=2, code='lt_policy'),
               ' trong vòng ', dict(id='days', right='30 ngày', wrong=['7 ngày', '3 tháng'], why='Chính sách: 30 ngày.', code='lt_days'), '.']),
        ('p', ['Mọi thắc mắc xin gọi đường dây nóng ', dict(id='hot', right='1900 6868', wrong=['1900 8686', '1800 6868'], why='Đúng số đường dây nóng.',
                                                            code='lt_hot'), '.']),
        ('sig', ['Phòng Kinh doanh — Công ty CP Cánh Diều']),
    ]
    twist = None
    if ctx['twist']:
        twist = dict(seg='fix', to='đổi mới miễn phí, tặng kèm hộp bút', why='Sếp quyết tặng thêm cho khách.',
                     note='Anh Quân: “Khách quen ba năm rồi đấy, tặng thêm hộp bút, ghi vào thư giúp anh.”')
    return dict(title=f'Soát thư trả lời khiếu nại {code}', who=1, paras=paras, twist=twist,
                papers=[dict(id='claim', emoji='📮', title='Đơn khiếu nại', lines=[f'{hon} {name} · đơn {code}', 'Balo chống gù đứt quai sau 2 tuần.']),
                        dict(id='policy', emoji='📜', title='Chính sách bảo hành', lines=['Lỗi đường may, quai, khóa: đổi mới miễn phí trong 30 ngày.',
                                                                                           'Đường dây nóng: 1900 6868.'])])


def g_letter(rng, ctx: dict) -> dict:
    x = rng.choice((_letter_invite, _letter_holiday, _letter_reply))(rng, ctx)
    n_bad = min(5, 2 + min(ctx['tier'], 2) + ctx['more'])
    blocks, tw = ow.doc(rng, x['paras'], n_bad, x['twist'])
    return dict(npc=x['who'], title=x['title'],
                opening='Anh Quân đưa bản nháp: “Em soát giúp anh rồi in ra ký. Sai một chữ là mất mặt với người ta đấy.”',
                brief='Soát bản nháp với giấy tờ bên cạnh: chạm chỗ sai, chọn cách viết đúng. Chỗ đúng thì để nguyên.',
                papers=x['papers'], work=dict(type='mark', blocks=blocks, _twist=tw))


# ================================================================ dossier 4: the director's day
ROOMS = [dict(id='gd', label='Phòng giám đốc', cap=4, tags=[]), dict(id='a', label='Phòng họp A', cap=10, tags=['proj']),
         dict(id='b', label='Phòng họp B', cap=6, tags=['tv'])]
HOURS = [dict(id='h0830', label='08:30', half='am'), dict(id='h0930', label='09:30', half='am'), dict(id='h1030', label='10:30', half='am'),
         dict(id='h1330', label='13:30', half='pm'), dict(id='h1430', label='14:30', half='pm'), dict(id='h1530', label='15:30', half='pm')]
TAGS = dict(proj='máy chiếu', tv='màn hình gọi video')
MEETINGS = [
    dict(id='gb', title='Họp giao ban trưởng phòng', who=['Anh Quân', 'Chị Huyền', 'Cô Hằng', 'Linh'], size=6, needs=[]),
    dict(id='jp', title='Tiếp đối tác Nhật Bản', who=['Anh Quân', 'Linh'], size=5, needs=['proj']),
    dict(id='luc', title='Làm việc với ông Lực (xưởng vải)', who=['Anh Quân', 'Cô Hằng'], size=3, needs=[]),
    dict(id='vid', title='Gọi video nhà máy Bình Dương', who=['Anh Quân'], size=2, needs=['tv']),
    dict(id='pv', title='Phỏng vấn trưởng phòng thiết kế', who=['Anh Quân', 'Chị Huyền'], size=3, needs=[]),
    dict(id='bank', title='Ký hồ sơ vay với ngân hàng', who=['Anh Quân', 'Cô Hằng'], size=4, needs=[]),
    dict(id='mau', title='Duyệt mẫu balo mới', who=['Linh', 'Chú Lâm'], size=4, needs=['proj']),
]
BUSY = {'Cô Hằng': 'đi nộp thuế', 'Linh': 'đi gặp khách', 'Chị Huyền': 'phỏng vấn ứng viên', 'Chú Lâm': 'kiểm hàng xuất'}


def g_meetings(rng, ctx: dict) -> dict:
    tier = ctx['tier']
    n = min(5, 3 + (tier >= 1) + (tier >= 2) + ctx['more'])
    items = [dict(x, who=list(x['who']), needs=list(x['needs'])) for x in rng.sample(MEETINGS, n)]
    ids = {it['id'] for it in items}
    people = sorted({w for it in items for w in it['who'] if w in BUSY})
    busy = [dict(who=w, text=BUSY[w]) for w in rng.sample(people, min(len(people), 1 + (tier >= 1)))]
    taken = [dict(text='{room} lúc {time} phòng kinh doanh đã đặt trước.'), dict(text='{room} lúc {time} có lớp đào tạo an toàn lao động.')][:1 + (tier >= 2)]
    windows = []
    if 'jp' in ids:
        windows.append(dict(item='jp', half='am', text='Đoàn khách Nhật chỉ ở công ty buổi sáng.'))
    elif 'luc' in ids:
        windows.append(dict(item='luc', half='pm', text='Ông Lực chỉ đến được buổi chiều.'))
    before = []
    if 'gb' in ids and 'jp' in ids:
        before.append(dict(a='gb', b='jp', text='Họp giao ban chốt giá trước rồi mới gặp khách Nhật.'))
    elif 'mau' in ids and 'jp' in ids:
        before.append(dict(a='mau', b='jp', text='Duyệt mẫu xong mới mang mẫu đi chào khách Nhật.'))
    tb = None
    if ctx['twist']:
        tb = dict(who='Anh Quân', text='đi ngân hàng đột xuất', note='Anh Quân đổi ý: “Mấy giờ đó anh phải ra ngân hàng, dời việc của anh đi nhé.”')
    work = ow.build_slots(rng, ROOMS, HOURS, TAGS, items, busy, taken, windows, before, tb)
    return dict(npc=0, title=f'Xếp lịch làm việc của sếp ({n} việc)',
                opening='Anh Quân: “Mai anh có mấy việc này. Em xếp giờ, xếp phòng giúp anh, đừng để ai phải chờ.”',
                brief=f'Xếp {n} cuộc họp vào phòng và giờ: không trùng người, đủ chỗ, đúng thiết bị, tránh giờ người ta bận.',
                papers=[dict(id='rooms', emoji='🚪', title='Phòng', lines=['Phòng giám đốc: 4 chỗ', 'Phòng họp A: 10 chỗ, có máy chiếu',
                                                                         'Phòng họp B: 6 chỗ, có màn hình gọi video'])],
                work=work)


# ================================================================ dossier 5: plan the steps
PLANS = [
    dict(id='board', title='Chuẩn bị họp hội đồng quản trị', npc=0,
         opening='Anh Quân: “Mai họp hội đồng quản trị. Em lo từ A đến Z nhé, đừng để anh phải nhắc.”',
         steps=[('book', 'Đặt phòng họp A trên lịch chung', 'need', 'Có phòng mới ghi được địa điểm.'),
                ('invite', 'Gửi giấy mời kèm tài liệu cho từng thành viên', 'need', 'Thành viên cần đọc tài liệu trước.'),
                ('test', 'Thử máy chiếu, cáp HDMI, micro', 'need', 'Hỏng thiết bị giữa buổi là mất mặt.'),
                ('print', 'In tài liệu đúng số người, đóng dấu MẬT', 'need', 'Tài liệu họp là tài liệu mật.'),
                ('minutes', 'Chuẩn bị mẫu biên bản và người ghi', 'need', 'Họp hội đồng phải có biên bản.'),
                ('zalo', 'Gửi tài liệu mật qua nhóm Zalo chung của công ty', 'bad', 'Lộ tài liệu mật cho cả công ty.', 3),
                ('grab', 'Lấy phòng họp A dù đang có lớp đào tạo, không báo ai', 'bad', 'Phải đặt lịch, không giành phòng.', 2),
                ('extra', 'In thừa 50 bản cho chắc', 'bad', 'Tài liệu mật in thừa dễ thất lạc.', 1),
                ('flower', 'Đặt hoa để bàn', 'opt', ''),
                ('online', 'Gửi link họp trực tuyến và thử kết nối', 'opt', '')],
         after=[('book', 'invite', 'Có phòng rồi mới ghi được địa điểm trong giấy mời.'), ('book', 'test', 'Phải có phòng mới thử thiết bị trong phòng.')],
         twist=dict(step='online', note='Anh Quân nhắn: “Có một thành viên họp trực tuyến từ Đà Nẵng nhé em.”', why='Có thành viên họp trực tuyến.',
                    after=[('book', 'online', 'Có phòng mới thử kết nối trong phòng.')])),
    dict(id='guests', title='Đón đoàn khách Nhật thăm xưởng', npc=0,
         opening='Anh Quân: “Thứ Năm đoàn khách Nhật sang thăm xưởng. Việc lớn đấy, em lên kế hoạch giúp anh.”',
         steps=[('confirm', 'Xác nhận số người, giờ đến với bên khách', 'need', 'Biết số người, giờ đến mới chuẩn bị đúng.'),
                ('car', 'Đặt xe đón ở sân bay', 'need', 'Khách không tự tìm đường được.'),
                ('safety', 'Báo xưởng dọn lối đi, chuẩn bị mũ bảo hộ cho khách', 'need', 'Vào xưởng phải an toàn.'),
                ('interp', 'Thuê phiên dịch tiếng Nhật', 'need', 'Không ai trong công ty nói tiếng Nhật.'),
                ('lunch', 'Đặt bàn ăn trưa', 'need', 'Khách ở tới trưa.'),
                ('nohat', 'Dẫn khách vào khu máy đang chạy, không cần mũ', 'bad', 'Nguy hiểm, sai quy định an toàn.', 3),
                ('discount', 'Hứa với khách chiết khấu 30% thay sếp', 'bad', 'Chỉ giám đốc được quyết giá.', 3),
                ('allstaff', 'Bắt cả công ty ở lại tối để dọn xưởng', 'bad', 'Dọn trong giờ làm theo phân công là đủ.', 1),
                ('gift', 'Chuẩn bị quà lưu niệm (balo mẫu)', 'opt', ''),
                ('veg', 'Đặt thêm suất chay', 'opt', '')],
         after=[('confirm', 'car', 'Biết giờ đến mới đặt xe đúng chuyến.'), ('confirm', 'lunch', 'Biết số người mới đặt đủ bàn.')],
         twist=dict(step='veg', note='Bên khách vừa báo: hai người trong đoàn ăn chay.', why='Có khách ăn chay.',
                    after=[('confirm', 'veg', 'Biết số người mới đặt đủ suất.')])),
    dict(id='trip', title='Đặt chuyến công tác Đà Nẵng cho sếp', npc=0,
         opening='Anh Quân: “Tuần sau anh bay Đà Nẵng gặp nhà phân phối. Em lo vé, chỗ ở cho anh.”',
         steps=[('ask', 'Hỏi sếp giờ họp ở Đà Nẵng', 'need', 'Biết giờ họp mới chọn chuyến bay.'),
                ('flight', 'Đặt vé đến trước giờ họp ít nhất 3 tiếng', 'need', 'Chậm chuyến là lỡ họp.'),
                ('hotel', 'Đặt khách sạn gần chỗ họp', 'need', 'Đỡ mất thời gian đi lại.'),
                ('advance', 'Làm giấy tạm ứng công tác phí', 'need', 'Chi công tác phải có tạm ứng.'),
                ('plan', 'Gửi sếp lịch trình gộp một trang', 'need', 'Sếp xem một trang là biết hết.'),
                ('card', 'Dùng thẻ tín dụng cá nhân của sếp mà không hỏi', 'bad', 'Không tự dùng tiền riêng của người khác.', 2),
                ('late', 'Đặt chuyến cuối ngày hôm trước họp cho rẻ', 'bad', 'Chuyến cuối hay trễ, sếp đến nơi nửa đêm.', 1),
                ('idcard', 'Gửi ảnh CCCD của sếp vào nhóm chat nhờ đặt hộ', 'bad', 'Lộ giấy tờ tùy thân.', 3),
                ('car', 'Đặt xe đón tại sân bay Đà Nẵng', 'opt', ''),
                ('umbrella', 'Nhắc sếp mang ô', 'opt', '')],
         after=[('ask', 'flight', 'Biết giờ họp mới chọn chuyến bay.'), ('flight', 'plan', 'Có vé rồi mới gộp được lịch trình.'),
                ('hotel', 'plan', 'Có khách sạn rồi mới gộp được lịch trình.')],
         twist=dict(step='car', note='Anh Quân: “Lần này anh mang theo hai thùng balo mẫu đấy.”', why='Sếp mang hai thùng hàng mẫu.',
                    after=[('flight', 'car', 'Biết giờ hạ cánh mới đặt xe.')])),
    dict(id='party', title='Tổ chức tiệc 15 năm thành lập', npc=0,
         opening='Anh Quân: “Thứ Sáu kỷ niệm 15 năm công ty. Làm cho đàng hoàng nhưng đừng phung phí nhé em.”',
         steps=[('budget', 'Chốt danh sách khách và ngân sách với sếp', 'need', 'Biết ngân sách, số khách mới làm được.'),
                ('venue', 'Đặt tiệc trong ngân sách', 'need', 'Có chỗ, có món.'),
                ('invite', 'Gửi thư mời ghi tên từng người', 'need', 'Mời đúng người, đúng tên.'),
                ('speech', 'Soạn bài phát biểu cho sếp', 'need', 'Sếp cần nói vài lời.'),
                ('host', 'Phân công người đón khách', 'need', 'Khách đến không ai đón là thất lễ.'),
                ('over', 'Đặt tiệc vượt ngân sách cho hoành tráng', 'bad', 'Phung phí, sếp đã dặn.', 2),
                ('collect', 'Bắt nhân viên góp tiền mua quà tặng sếp', 'bad', 'Không ép ai góp tiền.', 2),
                ('group', 'Mời đối tác bằng một tin nhắn chung', 'bad', 'Thiếu trang trọng với đối tác.', 1),
                ('tent', 'Thuê bạt che sân', 'opt', ''),
                ('photo', 'Thuê người chụp ảnh', 'opt', '')],
         after=[('budget', 'venue', 'Biết ngân sách mới đặt tiệc.'), ('budget', 'invite', 'Chốt danh sách rồi mới gửi thư mời.')],
         twist=dict(step='tent', note='Dự báo chiều thứ Sáu mưa to — tiệc lại tổ chức ngoài sân.', why='Trời sẽ mưa, tiệc ngoài sân.',
                    after=[('budget', 'tent', 'Thuê bạt cũng phải nằm trong ngân sách.')])),
]


def seq_work(rng, x: dict, ctx: dict) -> dict:
    """A plan of steps (need / bad / opt) shuffled into a pool; the twist turns one 'opt' into 'need'."""
    pool = [dict(id=s[0], label=s[1], _role=s[2], _why=s[3], _sev=s[4] if len(s) > 4 else 1) for s in x['steps']]
    rng.shuffle(pool)
    tw = None
    if ctx['twist'] and x.get('twist'):
        tw = dict(x['twist'], at=0, after=[list(a) for a in x['twist'].get('after', [])])
    return dict(type='seq', pool=pool, _after=[list(a) for a in x['after']], _twist=tw)


def g_prep(rng, ctx: dict) -> dict:
    x = rng.choice(PLANS)
    return dict(npc=x['npc'], title=x['title'], opening=x['opening'],
                brief='Chọn những việc cần làm, xếp đúng thứ tự; bỏ ra những việc gây hại. Việc không cần thì làm hay không cũng được.',
                papers=[dict(id='rule', emoji='🧭', title='Nguyên tắc', lines=['Việc nào cần thông tin của việc khác thì làm sau.',
                                                                              'Tài liệu mật, giấy tờ cá nhân: không gửi nhóm chung.',
                                                                              'Chỉ sếp quyết giá, quyết chi lớn.'])],
                work=seq_work(rng, x, ctx))


# ================================================================ dossier 6: at reception
CASES = [
    dict(id='lucangry', npc=2, title='Ông Lực đòi gặp giám đốc ngay',
         opening='Ông Lực đứng giữa sảnh, giọng vang cả tầng: “Tiền vải nợ quá hạn rồi! Cho tôi gặp ông Quân ngay, không chờ!”',
         facts=[dict(id='cal', title='Lịch của sếp', text='Anh Quân đang họp với ngân hàng tới 11:00, sau đó trống 30 phút.'),
                dict(id='debt', title='Hỏi cô Hằng', text='Hóa đơn quá hạn 5 ngày vì xưởng chưa gửi biên bản giao hàng có chữ ký kho.'),
                dict(id='calls', title='Nhật ký cuộc gọi', text='Ông Lực đã gọi ba lần từ hôm qua, chưa ai gọi lại.')],
         options=[dict(id='wait', label='Mời ông vào phòng chờ, xin lỗi vì chưa gọi lại, mời cô Hằng xuống nói về biên bản còn thiếu, hẹn sếp gặp 11:00',
                       requires=['cal', 'debt'], _q='good', _out='Ông Lực nguôi giận, gửi ngay biên bản còn thiếu; 11 giờ sếp gặp ông năm phút là xong.'),
                  dict(id='back', label='Bảo ông về, hôm khác hẹn trước', requires=[], _q='ok',
                       _out='Ông Lực về, gọi điện thẳng cho sếp mắng một trận; chuyện vẫn chưa xong.'),
                  dict(id='burst', label='Gõ cửa phòng họp gọi sếp ra', requires=[], _q='bad', _sev=2,
                       _out='Sếp bị gọi ra giữa buổi họp ngân hàng, mất mặt; ông Lực vẫn chưa nhận được tiền.')]),
    dict(id='faketax', npc=5, title='“Cán bộ thuế” không hẹn trước',
         opening='Nhi gọi lên run run: “Có anh tự xưng cán bộ thuế, đòi xem sổ sách ngay, còn bảo ‘có bồi dưỡng thì nhẹ nhàng’…”',
         facts=[dict(id='paper', title='Hỏi giấy tờ', text='Anh ta không có quyết định kiểm tra, chỉ đưa danh thiếp in mờ.'),
                dict(id='call', title='Gọi Chi cục Thuế', text='Chi cục xác nhận: không có cán bộ nào tên đó, không có lịch kiểm tra hôm nay.'),
                dict(id='rule', title='Quy định kiểm tra thuế', text='Kiểm tra tại doanh nghiệp phải có quyết định gửi trước.')],
         options=[dict(id='verify', label='Lịch sự xin quyết định kiểm tra, báo đã xác minh với Chi cục, mời anh ta về; ghi lại sự việc',
                       requires=['paper', 'call'], _q='good', _out='Kẻ giả danh bỏ đi. Chi cục cảm ơn vì báo tin, cả khu được cảnh báo.'),
                  dict(id='kick', label='Đuổi ra ngay, không hỏi gì', requires=[], _q='ok', _out='Hắn đi, nhưng không ai ghi lại, hôm sau hắn sang công ty bên cạnh.'),
                  dict(id='pay', label='Đưa sổ sách và phong bì cho xong chuyện', requires=[], _q='bad', _sev=3,
                       _out='Mất tiền, lộ sổ sách cho kẻ lừa đảo; công ty phải trình báo công an.')]),
    dict(id='wifecard', npc=0, title='Vợ sếp xin mã OTP thẻ công ty',
         opening='Chị Mai (vợ anh Quân) gọi: “Em đọc giúp chị mã OTP thẻ công ty nhé, chị mua vé máy bay cho cả nhà đi biển.”',
         facts=[dict(id='rule', title='Quy định thẻ công ty', text='Thẻ công ty chỉ chi việc công; mã OTP không đọc cho bất kỳ ai.'),
                dict(id='boss', title='Lịch của sếp', text='Anh Quân đang trên máy bay, 2 tiếng nữa hạ cánh.'),
                dict(id='voice', title='Nghe kỹ cuộc gọi', text='Đúng giọng chị Mai, gọi từ số đã lưu trong danh bạ.')],
         options=[dict(id='kind', label='Từ chối khéo vì quy định thẻ, nhắn sếp khi hạ cánh, gợi ý chị thanh toán bằng thẻ cá nhân',
                       requires=['rule', 'boss'], _q='good', _out='Chị Mai hơi phật ý nhưng hiểu. Anh Quân về còn khen: “Em làm đúng.”'),
                  dict(id='later', label='“Để em hỏi anh Quân” rồi quên luôn', requires=[], _q='ok', _out='Chị Mai chờ mãi, giá vé tăng, hai vợ chồng cãi nhau.'),
                  dict(id='otp', label='Đọc mã OTP vì là vợ sếp', requires=['voice'], _q='bad', _sev=3,
                       _out='Chi việc riêng bằng thẻ công ty; cô Hằng phát hiện, sếp phải hoàn tiền và giải trình.')]),
    dict(id='press', npc=0, title='Phóng viên ở sảnh',
         opening='Một phóng viên chặn bạn ở sảnh: “Nghe nói Cánh Diều sắp cắt giảm một nửa xưởng? Chị xác nhận giúp một câu thôi.”',
         facts=[dict(id='rule', title='Quy định phát ngôn', text='Chỉ giám đốc hoặc người được ủy quyền mới phát ngôn với báo chí.'),
                dict(id='fact', title='Thông tin nội bộ', text='Công ty đang tính mua máy mới, chưa có quyết định nào về nhân sự.'),
                dict(id='card', title='Thẻ nhà báo', text='Thẻ thật, báo Thị Trường.')],
         options=[dict(id='card', label='Không bình luận, xin danh thiếp, hẹn giám đốc trả lời bằng văn bản trong ngày',
                       requires=['rule'], _q='good', _out='Anh Quân gửi thông cáo rõ ràng; bài báo đăng đúng sự thật, thợ yên tâm.'),
                  dict(id='deny', label='Phủ nhận luôn: “Không có chuyện đó”', requires=[], _q='ok', _out='Nói thay sếp; tuần sau báo hỏi lại khi công ty mua máy mới.'),
                  dict(id='leak', label='Nói nhỏ chuyện công ty đang tính mua máy mới', requires=['fact'], _q='bad', _sev=3,
                       _out='Báo giật tít “Cánh Diều thay người bằng máy”; xưởng hoang mang, ba thợ giỏi nghỉ việc.')]),
    dict(id='notin', npc=0, title='“Ai gọi cũng bảo anh đi vắng”',
         opening='Anh Quân dặn: “Chiều nay ai gọi cũng bảo anh đi vắng.” Mười phút sau, cô giáo trường con anh gọi: bé bị sốt cao.',
         facts=[dict(id='order', title='Lời dặn của sếp', text='Sếp đang tiếp khách quan trọng, không muốn bị làm phiền.'),
                dict(id='urgent', title='Cuộc gọi của trường', text='Bé sốt 39 độ, trường cần phụ huynh đến đón trong 30 phút.'),
                dict(id='wife', title='Số chị Mai', text='Chị Mai đang đi công tác Hà Nội.')],
         options=[dict(id='tell', label='Nhắn ngay vào phòng cho sếp: việc gia đình khẩn, trường gọi', requires=['urgent'], _q='good',
                       _out='Anh Quân xin lỗi khách năm phút, gọi người nhà đón bé kịp. Anh cảm ơn bạn mãi.'),
                  dict(id='note', label='Ghi lời nhắn, đưa sếp khi khách về', requires=[], _q='ok', _out='Một tiếng sau sếp mới biết, phải chạy vội tới trường.'),
                  dict(id='lie', label='Bảo trường “anh Quân đi vắng” đúng như lời dặn', requires=['order'], _q='bad', _sev=2,
                       _out='Bé chờ ở phòng y tế hai tiếng; sếp biết chuyện thì giận vì không ai báo.')]),
    dict(id='forge', npc=3, title='Linh nhờ ký thay sếp',
         opening='Linh chạy tới: “Chị ơi, báo giá phải gửi khách trước 5 giờ mà sếp ở sân bay. Chị ký thay sếp giùm em, chữ sếp dễ bắt chước lắm!”',
         facts=[dict(id='rule', title='Quy định chữ ký', text='Không ai được ký thay giám đốc nếu không có giấy ủy quyền.'),
                dict(id='reach', title='Liên lạc với sếp', text='Sếp ở phòng chờ sân bay, đọc được email và ký số trên điện thoại.'),
                dict(id='client', title='Khách hàng', text='Khách cần báo giá trước 17:00 để kịp họp ban giám hiệu.')],
         options=[dict(id='esign', label='Gửi báo giá cho sếp duyệt và ký số qua email, báo khách sẽ nhận trước 17:00',
                       requires=['rule', 'reach'], _q='good', _out='Sếp ký số trong 10 phút ở phòng chờ. Khách nhận đúng giờ, không ai phạm quy định.'),
                  dict(id='self', label='Bảo Linh tự lo, không phải việc của mình', requires=[], _q='ok', _out='Linh xoay mãi, gửi muộn 20 phút, khách phàn nàn.'),
                  dict(id='sign', label='Ký thay cho kịp', requires=[], _q='bad', _sev=3,
                       _out='Giả chữ ký giám đốc: báo giá bị khách nghi ngờ, bạn bị kỷ luật.')]),
]


def g_case(rng, ctx: dict) -> dict:
    return ow.case_work(rng, CASES)


# ================================================================ the office around the dossiers
MODS = [
    dict(id='normal', min_day=1, weight=3, emoji='☀️', name='Ngày bình thường', text='Sếp ở công ty cả ngày, việc đều tay.'),
    dict(id='away', min_day=2, weight=2, emoji='✈️', name='Sếp sắp đi công tác', text='Anh Quân chuẩn bị bay, kế hoạch nào cũng có thể đổi phút chót.'),
    dict(id='vip', min_day=2, weight=2, emoji='🎩', name='Ngày đón khách lớn', text='Đối tác lớn ghé thăm: thư từ, điện thoại dày hơn.'),
    dict(id='check', min_day=2, weight=2, emoji='🔍', name='Chị Khuê soát việc', text='Cuối ngày chị Khuê soát thư từ, lịch hẹn bạn làm.'),
    dict(id='board', emoji='🏛️', name='Họp hội đồng quản trị', forced_only=True,
         text='Ngày họp hội đồng quản trị: việc gấp, hạn sớm. Tăng ca hôm nay được trả 18 xu.'),
]


def rules(day: int) -> list:
    return [dict(id='mail', emoji='📌', title='Trình sếp', text='Đơn từ 50.000 xu, cơ quan nhà nước, báo chí, khoản chi lớn.'),
            dict(id='scam', emoji='🛡️', title='Lừa đảo', text='Email thật có đuôi @canhdieu.vn. Không chuyển tiền, không đổi số tài khoản qua email.'),
            dict(id='msg', emoji='📞', title='Lời nhắn', text='Lấy số sau cùng người gọi đọc. Giờ ghi theo 24 giờ.'),
            dict(id='sign', emoji='✍️', title='Chữ ký', text='Không ký thay sếp. Sếp ở xa thì ký số qua email.'),
            dict(id='cal', emoji='📅', title='Lịch', text='Không ai ở hai nơi cùng lúc; phòng đủ chỗ, đủ thiết bị.')]


DESK = [
    dict(id='lunch_call', title='Đối tác gọi giữa giờ trưa', emoji='🍱', npc=0, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='12:15, sếp đang ngủ trưa (“không ai được gọi anh”). Đối tác Nhật gọi: muốn chốt đơn lớn trước khi bay lúc 13:00.',
         options=[dict(id='wake', label='Gõ cửa báo sếp: đơn lớn, khách sắp bay', hint='', effects=dict(trust=2, xp=6), good=True,
                       outcome='Sếp ngái ngủ nhưng chốt được đơn, chiều còn mua trà sữa cho bạn.'),
                  dict(id='note', label='Ghi lời nhắn, chờ 13:00', hint='', effects=dict(trust=-2), good=False,
                       outcome='13:00 khách đã lên máy bay. Đơn hoãn sang tháng sau.'),
                  dict(id='self', label='Tự hứa với khách “đồng ý hết”', hint='', effects=dict(trust=-3, review=[2, 'Thư ký tự quyết thay giám đốc.']), good=False,
                       outcome='Sếp phải gọi lại đính chính từng điều khoản.')],
         default='note'),
    dict(id='roomgrab', title='Phòng họp bị chiếm', emoji='🚪', npc=3, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Năm phút nữa khách của sếp tới mà phòng họp A đang có phòng kinh doanh ngồi, Linh bảo: “Bọn em họp gấp, chị lấy phòng khác đi!”',
         options=[dict(id='calendar', label='Mở lịch chung cho Linh xem, xin trả phòng và gợi ý phòng B đang trống', hint='', effects=dict(xp=5), good=True,
                       outcome='Linh xin lỗi, dọn sang phòng B. Khách tới phòng đã sẵn sàng.'),
                  dict(id='give', label='Nhường, đưa khách vào phòng giám đốc chật chội', hint='', effects=dict(trust=-1), good=None,
                       outcome='Khách ngồi chen chúc, không có máy chiếu.'),
                  dict(id='shout', label='Lớn tiếng đuổi cả phòng ra', hint='', effects=dict(review=[2, 'Thư ký lớn tiếng ngay trước mặt khách.']), good=False,
                       outcome='Khách đến đúng lúc nghe hai bên to tiếng.')],
         default='give'),
    dict(id='flowers', title='Sếp quên sinh nhật vợ', emoji='💐', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Anh Quân hốt hoảng: “Hôm nay sinh nhật vợ anh! Em đặt hoa giúp anh, lấy quỹ tiếp khách cũng được.”',
         options=[dict(id='own', label='Đặt hoa, nhờ sếp chuyển khoản tiền riêng', hint='', effects=dict(trust=2, xp=4), good=True,
                       outcome='Hoa tới đúng giờ, tiền riêng ra tiền riêng. Sếp gật gù: “Em chu đáo thật.”'),
                  dict(id='fund', label='Lấy quỹ tiếp khách cho nhanh', hint='', effects=dict(trust=1, review=[2, 'Quỹ tiếp khách mua hoa cho vợ giám đốc à?']), good=False,
                       outcome='Cuối tháng cô Hằng hỏi: “Khoản hoa này tiếp khách nào?”'),
                  dict(id='no', label='“Anh tự đặt nhé”', hint='', effects=dict(trust=-2), good=None, outcome='Sếp quên tiếp. Tối về bị giận.')],
         default='no'),
    dict(id='gossip', title='Dò lịch sếp', emoji='👀', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Linh hỏi nhỏ: “Sếp hẹn ai bên nhân sự chiều nay thế? Có phải sắp cho ai nghỉ không chị?”',
         options=[dict(id='private', label='“Lịch sếp chị không nói được em ạ.” Đổi chủ đề nhẹ nhàng', hint='', effects=dict(xp=5), good=True,
                       outcome='Linh cười trừ. Tin đồn không bắt đầu từ bàn bạn.'),
                  dict(id='hint', label='Nháy mắt: “Em đoán xem”', hint='', effects=dict(trust=-2), good=False,
                       outcome='Đến chiều cả phòng kinh doanh đồn ầm có người bị đuổi.'),
                  dict(id='tell', label='Kể hết cho Linh', hint='', effects=dict(trust=-4, review=[1, 'Lịch giám đốc lộ ra ngoài từ bàn thư ký.']), good=False,
                       outcome='Sếp biết chuyện, gọi bạn vào nói chuyện riêng.')],
         default='private'),
    dict(id='shred', title='Hủy tài liệu cũ', emoji='🗃️', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Sếp đưa ba tập hồ sơ: “Hủy hết đi em.” Lướt qua, bạn thấy một bản hợp đồng gốc còn hiệu lực đến năm sau.',
         options=[dict(id='ask', label='Rút bản hợp đồng ra, hỏi lại sếp trước khi hủy', hint='', effects=dict(trust=2, xp=6), good=True,
                       outcome='“Ơ, may quá, bản gốc duy nhất đấy!” Sếp cất ngay vào tủ.'),
                  dict(id='all', label='Hủy hết như sếp bảo', hint='', effects=dict(trust=-3), good=False,
                       outcome='Tháng sau tranh chấp với nhà cung cấp, không còn bản gốc.'),
                  dict(id='keep', label='Không hủy gì, cất hết vào kho', hint='', effects=dict(time=15), good=None, outcome='Kho chật thêm ba tập hồ sơ.')],
         default='all'),
    dict(id='giftcard', title='Tin nhắn “sếp” xin mua thẻ cào', emoji='📲', npc=0, min_day=2, tone='tense', at='open', weight=2, mods=None,
         text='Số lạ nhắn Zalo, ảnh đại diện là anh Quân: “Anh đang họp, em mua giúp anh 10 thẻ cào 500 xu, gửi mã qua đây, về anh trả.”',
         options=[dict(id='call', label='Gọi số cũ của sếp để hỏi, báo IT số lạ này', hint='', effects=dict(xp=6), good=True,
                       outcome='Sếp đang ngồi ăn sáng, không nhắn gì. IT cảnh báo cả công ty.'),
                  dict(id='buy', label='Mua ngay kẻo sếp chờ', hint='−50 xu', effects=dict(money=-50), good=False, outcome='Mất 50 xu. Sếp không hề nhắn.'),
                  dict(id='ignore', label='Lờ đi', hint='', effects={}, good=None, outcome='Hôm sau Nhi nhận được tin y hệt và suýt mua.')],
         default='ignore'),
    dict(id='earlyguest', title='Khách đến sớm một tiếng', emoji='⏰', npc=5, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Nhi gọi: “Khách hẹn 10 giờ mà 9 giờ đã tới rồi chị ơi, phòng họp còn đang dọn.”',
         options=[dict(id='tea', label='Mời khách ngồi phòng chờ, pha trà, đưa catalogue xem trước', hint='Mất 10 phút', effects=dict(time=10, xp=4), good=True,
                       outcome='Khách xem catalogue, tới giờ họp đã chọn sẵn ba mẫu.'),
                  dict(id='rush', label='Gọi sếp họp sớm luôn', hint='', effects=dict(trust=-2), good=False,
                       outcome='Sếp đang dở việc khác, bước vào họp mặt nặng mày nhẹ.'),
                  dict(id='wait', label='Để khách tự ngồi chờ ở sảnh', hint='', effects=dict(review=[3, 'Đến sớm thì ngồi sảnh một tiếng không ai hỏi.']), good=None,
                       outcome='Khách ngồi bấm điện thoại một tiếng.')],
         default='wait'),
    dict(id='printer', title='Máy in kẹt 5 phút trước họp', emoji='🖨️', npc=0, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Tài liệu họp mới in được nửa thì máy kẹt giấy. Năm phút nữa vào họp.',
         options=[dict(id='pdf', label='Gửi bản PDF lên màn hình phòng họp, gọi IT xử lý máy', hint='', effects=dict(xp=5), good=True,
                       outcome='Mọi người đọc trên màn hình; in xong bản giấy mang vào giữa buổi.'),
                  dict(id='yank', label='Giật mạnh tờ giấy ra', hint='', effects=dict(money=-10), good=False, outcome='Rách trục cuốn giấy, sửa mất 10 xu.'),
                  dict(id='late', label='Xin hoãn họp 20 phút', hint='', effects=dict(trust=-2), good=None, outcome='Khách phải chờ, sếp không vui.')],
         default='late'),
    dict(id='scolded', title='Sếp quát oan', emoji='😤', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Vừa bị khách phàn nàn, anh Quân quay sang quát bạn vì “lịch hẹn lộn xộn” — mà lịch đó do chính anh đổi sáng nay.',
         options=[dict(id='calm', label='Bình tĩnh đưa lịch sử thay đổi, đề xuất chốt lịch mỗi sáng', hint='', effects=dict(trust=2, xp=6), good=True,
                       outcome='Sếp đọc, im một lúc: “Ừ, anh đổi. Mai mình chốt lịch lúc 8 giờ.”'),
                  dict(id='cry', label='Nhận lỗi cho xong', hint='', effects=dict(trust=-1), good=None, outcome='Êm chuyện, nhưng tuần sau sếp lại đổi lịch y hệt.'),
                  dict(id='argue', label='Cãi lại trước mặt mọi người', hint='', effects=dict(trust=-4), good=False, outcome='Cả phòng im phăng phắc. Sếp đóng sầm cửa.')],
         default='cry'),
    dict(id='giftbox', title='Quà Tết của nhà cung cấp', emoji='🎁', npc=2, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Ông Lực gửi riêng cho bạn một hộp quà to: “Cảm ơn cháu sắp lịch cho chú gặp sếp nhanh.”',
         options=[dict(id='report', label='Báo sếp, đưa quà vào quỹ chung của văn phòng', hint='', effects=dict(trust=2, xp=5), good=True,
                       outcome='Cả phòng chia nhau hộp bánh; ông Lực hiểu thư ký không nhận quà riêng.'),
                  dict(id='keep', label='Giữ riêng, không ai biết', hint='', effects=dict(trust=-3, review=[2, 'Muốn gặp giám đốc nhanh thì gửi quà cho thư ký.']), good=False,
                       outcome='Tuần sau ông Lực xin chen lịch sếp, “như lần trước”.'),
                  dict(id='return', label='Gửi trả lại ngay', hint='', effects=dict(xp=3), good=None, outcome='Ông Lực hơi quê nhưng không nói gì.')],
         default='keep'),
]

SITUATIONS = [
    dict(id='TK-S01', title='Sếp bảo nói dối khách', npc=0, tone='tense', min_day=2,
         opening='Anh Quân: “Ông Lực mà gọi thì bảo hàng đã chuyển khoản rồi, ngân hàng lỗi.” Bạn biết tiền chưa hề chuyển.',
         swap='Bạn là giám đốc đang kẹt dòng tiền, cần thêm ba ngày.',
         facts=[dict(id='fact', title='Sổ chi', source='Cô Hằng', text='Lệnh chuyển tiền chưa được tạo; quỹ đang chờ khách trả nợ thứ Năm.'),
                dict(id='trust', title='Quan hệ với Lực Thành', source='Chị Khuê', text='Mười năm làm ăn, chưa lần nào trễ quá một tuần.'),
                dict(id='way', title='Cách khác', source='Chị Khuê', text='Có thể gọi xin gia hạn ba ngày, cam kết bằng văn bản.')],
         options=[dict(id='honest', label='Đề xuất sếp tự gọi xin gia hạn ba ngày kèm cam kết; bạn soạn sẵn thư', requires=['fact', 'way'],
                       quality='good', stars=5, review='Nói thật, xin hẹn rõ ràng — tôi chịu chờ. Làm ăn là phải vậy.',
                       outcome='Ông Lực đồng ý gia hạn, vẫn giao vải đúng hẹn.',
                       perspectives=[dict(who='Ông Lực', emoji='🧵', text='Biết trước thì tôi xoay được.'),
                                     dict(who='Anh Quân', emoji='🧑‍💼', text='Hóa ra nói thật nhẹ hơn.')]),
                  dict(id='lie', label='Nói dối theo lời sếp', quality='bad', stars=1, review='Ngân hàng lỗi ba ngày liền à? Tôi không tin nữa.',
                       outcome='Ông Lực gọi ngân hàng kiểm tra, biết bị lừa, ngừng giao vải.',
                       perspectives=[dict(who='Ông Lực', emoji='😠', text='Mất tiền thì ít, mất lòng tin thì nhiều.')]),
                  dict(id='dodge', label='Tránh nghe máy cả ngày', quality='ok', stars=3, review='Gọi mãi không ai nghe, bực mình.',
                       outcome='Ông Lực lên tận công ty, chuyện to hơn.',
                       perspectives=[dict(who='Nhi', emoji='🛎️', text='Em phải đứng đỡ lời ở sảnh.')])],
         lesson='Thư ký giữ uy tín cho sếp bằng cách giúp sếp nói thật cho khéo.'),
    dict(id='TK-S02', title='Bản tin cuối ngày cho sếp', npc=1, tone='gentle', min_day=2,
         opening='Chị Khuê: “Hồi chị làm thư ký, cuối ngày chị gửi sếp một bản tin năm dòng. Em có muốn thử không?”',
         swap='Bạn là trợ lý cũ, biết sếp quên trước quên sau, muốn người mới bớt vất vả.',
         facts=[dict(id='habit', title='Thói quen của sếp', source='Chị Khuê', text='Sếp đọc tin nhắn ngắn buổi tối, không đọc email dài.'),
                dict(id='miss', title='Việc bị quên tuần trước', source='Nhật ký', text='Hai lời nhắn của đối tác bị sếp quên gọi lại.'),
                dict(id='time', title='Thời gian', source='Lịch của bạn', text='Mỗi tối mất 10 phút.')],
         options=[dict(id='yes', label='Làm bản tin năm dòng: việc đã xong, việc mai, ai cần gọi lại', requires=['habit', 'miss'],
                       quality='good', stars=5, review='Có bản tin tối, sáng anh vào là biết làm gì. Hay!',
                       outcome='Không còn lời nhắn nào bị quên; sếp đổi lịch ít hẳn.',
                       perspectives=[dict(who='Anh Quân', emoji='🧑‍💼', text='Anh đỡ phải nhớ.'),
                                     dict(who='Chị Khuê', emoji='🌸', text='Truyền nghề thành công.')]),
                  dict(id='long', label='Gửi email dài liệt kê hết mọi thứ', quality='ok', stars=3, review='Email dài quá anh chưa đọc.',
                       outcome='Sếp vẫn quên một cuộc gọi.', perspectives=[dict(who='Anh Quân', emoji='😵', text='Nhiều chữ quá.')]),
                  dict(id='no', label='Thôi, việc ai nấy nhớ', quality='bad', stars=2, review='Lại quên gọi lại khách rồi…',
                       outcome='Một đối tác phàn nàn vì chờ cuộc gọi cả tuần.', perspectives=[dict(who='Đối tác', emoji='📞', text='Hứa gọi lại mà không thấy.')])],
         lesson='Giúp sếp nhớ đúng cách sếp đọc.'),
    dict(id='TK-S03', title='Đồng nghiệp muốn chen lịch sếp', npc=3, tone='gentle', min_day=3,
         opening='Linh nài nỉ: “Chị cho em 15 phút với sếp chiều nay nha, em phải xin duyệt giá gấp. Lịch kín thì chị gạch ai đó đi!”',
         swap='Bạn là nhân viên kinh doanh, khách đang chờ giá, chậm là mất đơn.',
         facts=[dict(id='cal', title='Lịch chiều nay', source='Lịch chung', text='Kín từ 13:30 đến 16:30; 16:30–16:45 sếp ký giấy tờ.'),
                dict(id='size', title='Đơn của Linh', source='Phòng kinh doanh', text='Đơn 40.000 xu — dưới mức phải trình giám đốc, trưởng phòng duyệt được.'),
                dict(id='rule', title='Phân quyền duyệt giá', source='Quy chế', text='Đơn dưới 50.000 xu trưởng phòng kinh doanh duyệt.')],
         options=[dict(id='route', label='Chỉ Linh: đơn dưới 50.000 xu trưởng phòng duyệt được; nếu vẫn cần sếp thì xin 5 phút lúc 16:30',
                       requires=['size', 'rule'], quality='good', stars=5, review='Hóa ra không cần sếp! Em xin duyệt trong 10 phút, khách ký luôn 🙌',
                       outcome='Linh chốt đơn kịp; lịch sếp không bị xáo trộn.',
                       perspectives=[dict(who='Linh', emoji='📦', text='Biết quy trình đỡ mất thời gian.')]),
                  dict(id='bump', label='Gạch một cuộc hẹn khác cho Linh', quality='bad', stars=2, review='Tôi bị hủy hẹn phút chót mà không ai giải thích.',
                       outcome='Đối tác bị hủy hẹn phàn nàn với sếp.', perspectives=[dict(who='Anh Quân', emoji='🧑‍💼', text='Ai cho gạch lịch của anh?')]),
                  dict(id='no', label='“Kín rồi, mai nhé”', quality='ok', stars=3, review='Mai thì khách đi mất rồi chị ơi.',
                       outcome='Linh mất đơn vì không biết cách khác.', perspectives=[dict(who='Linh', emoji='😞', text='Giá mà ai chỉ.')])],
         lesson='Giữ lịch sếp, nhưng chỉ cho người ta con đường khác.'),
]

CARE = dict(
    id=ID, prefix=P, boss=BOSS,
    ranks=('Thử việc', 'Thư ký chính thức', 'Thư ký riêng của giám đốc', 'Được đề cử trợ lý giám đốc'),
    lines=('Ba ngày không sót một lời nhắn. Anh ký chính thức cho em.',
           'Từ nay em giữ lịch riêng của anh. Ai muốn gặp anh phải qua em.',
           'Anh đề cử em làm trợ lý giám đốc. Không có em chắc anh lạc mất lịch.'),
    mates=[
        dict(id='khue', name='Chị Khuê', role='Trợ lý cũ, nay ở phòng kinh doanh', npc=1, emoji='🌸',
             asks=[('Em xem giúp chị bản báo giá này có lỗi chính tả nào không?', 15),
                   ('Chị cần đặt phòng họp gấp chiều nay, em xếp giúp chị nhé?', 20)],
             thanks='Chị Khuê cười: “Có gì khó cứ hỏi chị nhé.”', no='Chị Khuê: “Ừ, em bận thì thôi.”',
             cover='Chị Khuê đỡ giúp một tay —'),
        dict(id='nhi', name='Nhi', role='Lễ tân', npc=5, emoji='🛎️',
             asks=[('Khách nước ngoài hỏi đường, chị ra nói giúp em vài câu tiếng Anh nhé?', 15),
                   ('Sổ khách ra vào em ghi lộn, chị chỉ em sắp lại với?', 20)],
             thanks='Nhi để lên bàn hộp sữa chua: “Em cảm ơn chị!”', no='Nhi: “Dạ không sao, em tự lo được.”',
             cover='Nhi chạy giấy tờ giữa các phòng giúp —'),
        dict(id='tam', name='Chú Tâm', role='Tài xế của giám đốc', npc=None, emoji='🚗',
             asks=[('Mai sếp đi Bình Dương mấy giờ, cháu xem lịch giúp chú?', 10),
                   ('Phiếu xăng tháng này chú ghi chưa đúng, cháu xem giúp chú?', 20)],
             thanks='Chú Tâm cười hiền: “Mai chú mua xôi cho.”', no='Chú Tâm: “Ừ, để chú hỏi phòng kế toán.”',
             cover='Chú Tâm chạy đưa giấy tờ giúp —'),
    ])

FORMS = [dict(id='inbox', label='Thư gửi sếp', min_day=1, bonus=25, build=g_inbox),
         dict(id='calls', label='Ghi lời nhắn', min_day=1, bonus=20, build=g_calls),
         dict(id='letter', label='Soát văn bản', min_day=1, bonus=25, build=g_letter),
         dict(id='meetings', label='Lịch của sếp', min_day=2, bonus=30, build=g_meetings),
         dict(id='prep', label='Lên kế hoạch', min_day=2, bonus=20, build=g_prep),
         dict(id='case', label='Tiếp khách', min_day=3, bonus=20, build=g_case)]

JOB = ow.OfficeJob(dict(
    id=ID, prefix=P, boss=BOSS, boss_npc=0, forms=FORMS, mods=MODS, forced={4: 'board'}, intro={2: 'away', 3: 'vip', 4: 'check'},
    more_mods=('vip',), busy_mod='away', crunch='board', audit='check', auditor='Chị Khuê', helpers=('Chị Khuê',), care=CARE, desk=DESK,
    rules=rules,
    hints=dict(inbox='Đọc “Sếp dặn” → chạm từng thư, chọn khay. Soi kỹ địa chỉ gửi: email thật luôn có đuôi @canhdieu.vn.',
               calls='Đọc hết cuộc gọi, kể cả câu cuối — người gọi hay sửa số, sửa giờ. Ghi giờ theo 24 giờ.',
               letter='So từng chỗ với ghi chú của sếp và tờ lịch: chạm chỗ sai, chọn cách viết đúng.',
               meetings='Chọn một cuộc họp → chạm ô phòng/giờ. Xem bảng: ai bận, phòng nào đã có người đặt, cần máy chiếu hay màn hình.',
               prep='Chạm từng việc để thêm vào danh sách theo thứ tự. Việc gây hại thì bỏ ra.',
               case='Tìm hiểu từng chuyện trước, rồi chọn cách trả lời giữ được uy tín cho sếp và công ty.'),
    staff_area={'desk': ('inbox', 'calls', 'letter'), 'plan': ('meetings', 'prep')},
))
JOB.bind(globals())

EMPLOYMENT = dict(
    postings=[
        dict(id='tk-canhdieu', org='Công ty CP Cánh Diều', kind='corp', title='Thư ký giám đốc',
             salary=(55, 80), probation_days=3, wants=['careful', 'communication', 'patience'],
             perks=['Làm việc cạnh giám đốc', 'Gặp nhiều đối tác', 'Lịch thay đổi liên tục'],
             culture='Giám đốc quyết nhanh, đổi ý còn nhanh hơn; thư ký là người giữ cho mọi thứ không rối.',
             questions=['tk_scam', 'tk_secret', 'conflict'], reference=True),
        dict(id='tk-office', org='Văn phòng Dịch vụ Ngọc Bích', kind='firm', title='Lễ tân kiêm thư ký',
             salary=(50, 70), probation_days=2, wants=['communication', 'learning'],
             perks=['Nhận việc nhanh', 'Nghe điện thoại nhiều', 'Giờ giấc ổn định'],
             culture='Văn phòng cho thuê chỗ ngồi, phục vụ nhiều công ty nhỏ cùng lúc.',
             questions=['tk_scam', 'mistake'], reference=False),
    ],
    questions={
        'tk_scam': dict(text='Email “giám đốc” từ địa chỉ gmail lạ, đòi chuyển tiền gấp vì đang họp. Bạn làm gì?', options=[
            dict(id='verify', label='Không chuyển; gọi lại số đã lưu của sếp để xác minh, báo kế toán và IT', score=3, note='Bình tĩnh, đúng quy trình.'),
            dict(id='pay', label='Chuyển ngay kẻo sếp giận', score=0, note='Lừa đảo giả danh giám đốc là kiểu mất tiền phổ biến nhất.'),
            dict(id='reply', label='Trả lời email hỏi lại', score=1, note='Hỏi lại kẻ gian thì kẻ gian vẫn trả lời “đúng rồi”.')]),
        'tk_secret': dict(text='Đồng nghiệp dò hỏi lịch hẹn riêng của giám đốc. Bạn trả lời sao?', options=[
            dict(id='polite', label='Từ chối nhẹ nhàng, không tiết lộ', score=3, note='Kín đáo mà không mất lòng.'),
            dict(id='tell', label='Kể vì là đồng nghiệp thân', score=0, note='Lịch giám đốc lộ ra là tin đồn bắt đầu.'),
            dict(id='hint', label='Ám chỉ cho vui', score=1, note='Ám chỉ cũng là để lộ.')]),
    },
)

SPEC = dict(
    id=ID, prefix=P, category='office',
    meta=dict(short='Thư ký giám đốc', place='Công ty CP Cánh Diều', tagline='Giữ cho lịch sếp không rối, dù sếp đổi ý.', icon='calendar',
              color='#b0546a', light='#f8e7ec', weather='Trời mát, điều hòa chạy êm', work='Việc', station='Bàn thư ký',
              greeting='Hộp thư, sổ lời nhắn và lịch của sếp đã mở sẵn. Soát kỹ từng chữ — và chuẩn bị tinh thần, sếp hay đổi ý.',
              caption='Một lời nhắn đúng bằng mười cuộc gọi', map_label='22 · CÁNH DIỀU · THƯ KÝ'),
    people=PEOPLE,
    staff=[('Chị Khuê', 'desk', 'Thuộc thói quen của sếp như lòng bàn tay.', 88, 90),
           ('Nhi', 'desk', 'Nhớ mặt từng khách, pha trà rất khéo.', 72, 92),
           ('Chú Tâm', 'plan', 'Biết đường tắt khắp thành phố.', 75, 95)],
    roles={'desk': 'Hành chính – lễ tân', 'plan': 'Hậu cần'},
    tip=0,
    physical=(),
    free_actions=(),
    no_tick=(P + 'put', P + 'mark', P + 'place', P + 'read', P + 'hint', P + 'desk', P + 'overtime', P + 'help', P + 'cover', P + 'break'),
    employment=EMPLOYMENT,
    activity=('📅', 'Bàn thư ký gọn gàng', [('Thư đến', 'Hộp thư'), ('Lời nhắn', 'Sổ điện thoại'), ('Thư mời', 'Văn bản'), ('Lịch họp', 'Lịch sếp')],
              ['Lọc thư', 'Ghi lời nhắn', 'Soát văn bản', 'Xếp lịch sếp']),
    stories=[('Email giả danh giám đốc', ('Một sáng thứ Hai, email “anh Quân” đòi chuyển 85.000 xu gấp.',
                                          'Bạn gọi lại số đã lưu: sếp đang ăn phở, không gửi gì cả.',
                                          'Cả công ty được cảnh báo; tháng sau công ty bên cạnh mất tiền vì đúng kiểu email đó.')),
             ('Tờ lịch dán tủ lạnh', ('Sếp đổi lịch bốn lần trong một buổi sáng.',
                                      'Bạn đề xuất chốt lịch lúc 8 giờ, mọi thay đổi sau đó báo qua bạn.',
                                      'Một tháng sau, không cuộc hẹn nào bị chồng giờ.')),
             ('Ông Lực nóng tính', ('Ông Lực quát ầm sảnh vì tiền vải chậm.',
                                    'Bạn mời ông vào phòng chờ, gọi kế toán xuống nói rõ giấy tờ còn thiếu.',
                                    'Từ đó ông Lực gọi bạn là “cô thư ký biết điều”, Tết còn gửi thiệp.'))],
    review_asides=['Lời nhắn đầy đủ, gọi lại đúng giờ.', 'Lịch hẹn rõ ràng.', 'Thư từ lịch sự, không sai chữ nào.', 'Giữ kín chuyện của sếp.'],
    situations=SITUATIONS,
    guide='Mỗi việc là một việc thật: lọc thư vào khay, ghi lời nhắn điện thoại, soát thư mời và thông báo, xếp lịch họp của sếp, lên kế hoạch từng bước, tiếp khách khó. Đọc giấy tờ bên cạnh, rồi nộp trước giờ hạn. Sếp hay đổi ý — đọc kỹ tin báo rồi sửa lại. Lương ngày trả khi khép ca.',
)
