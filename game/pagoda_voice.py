"""Chùa Gió Lành's own voice in the review thread (the owner, 02/10: "cách trả lời của chùa khác các bên còn lại
mới đúng, giờ giống quá").

At merge time the pagoda borrowed the shops' review machinery, so visitors wrote "Ủng hộ quán mới mở nha!" and the
young monk answered "Dạ tiệm cảm ơn bạn…". Here the pagoda gets its own words everywhere the review thread reaches:

* visitors (khách thập phương, Phật tử, bà con) write about calm, a clean yard, being guided kindly, quiet during
  chanting, finding their way, the vegetarian meal, the donation book counted in front of them; never "service";
* the player's ready-made replies are humble and gentle ("A Di Đà Phật", "Cảm ơn bác đã ghé chùa", "chùa xin ghi
  nhận", "mời bác rằm tới ghé lễ"); never commercial, never luck or blessings in exchange for money;
* the visitor's answer to a reply, bystanders, friends who come along, the pile-on after a rude reply.

The pagoda is the neighbourhood's long-standing pagoda: nothing here calls it new. Same data as every career (the
same persona ids, twist kinds, styles, tones and offers, so saves and the rolling release are untouched); only the
words differ. feedback.py and feedback_voices.py call in through `on(career)` and the helpers below; every roll is
seeded from ids like the shared path, so a reload never rerolls.
"""
from __future__ import annotations

import re

CAREERS = ('pagoda',)

# Words a pagoda line never uses (tests/test_pagoda_voice.py runs every generated line through it).
COMMERCIAL = re.compile(r'(?<!\w)(ủng hộ|shop|quán|tiệm|dịch vụ|giá|khuyến mãi|5 sao|năm sao|quay lại mua|voucher|hoàn tiền|'
                        r'chủ quán|khách hàng|cửa hàng|mới mở|khai trương|đáng tiền|phục vụ)(?!\w)', re.I)


def on(career) -> bool:
    return career in CAREERS


def commercial(text: str) -> bool:
    return bool(COMMERCIAL.search(text or ''))


def _pick(rows, seed: int, k: int = 0):
    return rows[(seed + k * 7919) % len(rows)]


class _Blank(dict):
    def __missing__(self, key):
        return ''


def fill(text: str, **kw) -> str:
    return re.sub(r'\s{2,}', ' ', text.format_map(_Blank(kw))).strip()


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:] if text and text[0] != '“' else text


# ------------------------------------------------------------------ who is who
# How a visitor calls the player: a young monk (thầy) or a young nun (sư cô).
def owner_call(s: dict) -> str:
    j = (s or {}).get('journey')
    g = j.get('gender') if isinstance(j, dict) else None
    return 'sư cô' if g == 'female' else 'thầy'


# How the player addresses the pagoda's own people in a reply (people index in pagoda_content.PEOPLE).
ADDRESS = {0: 'thầy', 1: 'bà', 2: 'cô', 3: 'anh', 4: 'con', 5: 'chị', 6: 'ông', 7: 'chị', 8: 'anh'}


def address(post: dict, persona: str) -> str:
    npc = str(post.get('npc') or '')
    if npc.startswith('pagoda_npc_') and not (post.get('feedback') or {}).get('stranger'):
        try:
            return ADDRESS.get(int(npc.rsplit('_', 1)[1]) - 1, 'bác')
        except ValueError:
            pass
    return 'bạn' if persona == 'genz' else 'bác'


# What a criterion is about, in the pagoda's words (pagoda.CRIT, the morning keys, the pile-on's "attitude").
TOPIC = {'craft': 'việc quét dọn, hương đèn', 'safe': 'chuyện nhang đèn, an toàn', 'honest': 'chuyện sổ công đức',
         'manner': 'cách nhắc nhở, chỉ dẫn', 'speed': 'chuyện phải chờ', 'plan': 'thời khóa sáng', 'word': 'lời thầy dặn',
         'attitude': 'cách trả lời', 'overall': 'buổi ghé chùa'}


def topic(crit: dict) -> str:
    label = str(crit.get('label') or '')
    return TOPIC.get(crit.get('key'), label[:1].lower() + label[1:] if label else 'buổi ghé chùa')


# ------------------------------------------------------------ the visitor writes
OPEN = {
    5: ['A Di Đà Phật, ghé chùa một buổi mà lòng nhẹ hẳn.', 'Sáng nay lên chùa thấy bình an lắm.',
        'Chùa Gió Lành vẫn hiền như mọi khi.', 'Ngồi hiên chùa nghe gió sông, quên hết chuyện ngoài kia.'],
    4: ['Chùa yên và sạch, chỉ có chút xíu cần để ý.', 'Ghé chùa thấy dễ chịu, còn một chuyện nhỏ thôi.',
        'Buổi lễ nhẹ nhàng, chỉ một điểm nhỏ chưa trọn.'],
    3: ['Hôm nay lên chùa có chỗ chưa được yên lòng.', 'Chùa vẫn đẹp, nhưng hôm nay có vài chuyện chưa ổn.'],
    2: ['Hôm nay lên chùa mà về hơi buồn.', 'Mong chùa để ý hơn, hôm nay nhiều chỗ chưa ổn.'],
    1: ['Lên chùa mà về không yên lòng chút nào.', 'Hôm nay ở chùa có chuyện làm tôi buồn thật sự.'],
}
# A few visitors have their own way of saying it (persona ids are the shared ones).
OPEN_BY = {
    'genz': {5: ['Chùa chill ghê, ngồi nghe chuông mà muốn ở lại cả buổi 🪷', 'Lên chùa sống chậm một bữa, thương ghê 🙏'],
             4: ['Chùa xinh, yên, chỉ có một xíu thôi nè.'], 3: ['Hơi buồn xíu nha.']},
    'quiet': {5: ['Yên. Sạch. Mát.', 'Bình an.'], 4: ['Yên. Có chút chưa ổn.'], 3: ['Chưa yên lắm.'], 2: ['Buồn.']},
    'bossy': {5: ['Tôi đi chùa khắp nơi rồi, chùa này giữ nếp tốt.', 'Hồi xưa tôi lên chùa này với ông bà, nếp chùa vẫn y như cũ.'],
              4: ['Nếp chùa giữ tốt, tôi chỉ nhắc một chút thôi.'], 3: ['Tôi nói thật để chùa sửa.']},
    'sour': {5: ['Tính tôi khó, mà hôm nay hết chỗ chê.'], 4: ['Được, nhưng tôi vẫn phải nói một câu.'],
             3: ['Nói thật thì hôm nay chưa ổn.']},
    'picky': {5: ['Tôi để ý từng góc: bàn Phật, lư hương, sổ công đức. Đều gọn.'], 4: ['Gần trọn, còn một chỗ tôi để ý.'],
              3: ['Tôi để ý thấy mấy chỗ chưa ổn.']},
    'knowitall': {4: ['Tôi đi lễ mấy chục năm, nói để thầy trẻ biết.'], 3: ['Tôi rành nếp chùa, hôm nay chưa đúng.'],
                  2: ['Tôi rành nếp chùa, hôm nay sai nhiều.']},
    'rude': {4: ['Được. Mà chưa trọn.'], 3: ['Chưa ổn.'], 2: ['Không vui.'], 1: ['Buồn thật.']},
}
GOOD = {
    'craft': ['Sân chùa sạch lá, hương đèn gọn gàng.', 'Bàn Phật hoa tươi, trái cây bày ngay ngắn.', 'Việc gì cũng làm cẩn thận, nhìn là thấy yên.'],
    'safe': ['Nhang đèn để xa rèm, người già trẻ nhỏ đều được để ý.', 'Lối đi khô ráo, bậc thềm có người đỡ.'],
    'honest': ['Hòm công đức có hai người cùng đếm, ghi sổ rõ ràng.', 'Chuyện công đức ở chùa minh bạch, ai cũng yên tâm.'],
    'manner': ['Được chỉ dẫn nhẹ nhàng, không ai bị ngượng.', 'Thầy trẻ nói chậm, nghe xong thấy lòng nhẹ hẳn.'],
    'speed': ['Hỏi đường vào chánh điện là có người chỉ ngay.', 'Lên chùa không phải đứng chờ lâu.'],
    'plan': ['Chuông sáng ngân đều, công phu đúng giờ.', 'Sáng sớm nghe chuông, đúng giờ như mọi khi.'],
    'word': ['Thầy trẻ nghe thầy trụ trì dặn rất chăm.'],
    '': ['Ghé chùa một buổi mà lòng thấy an.'],
}
BAD = {
    'craft': ['Sân với bàn Phật còn vài chỗ chưa gọn: {note}.', 'Có chỗ còn sơ suất ({note}).'],
    'safe': ['Chỗ nhang đèn làm tôi hơi lo: {note}.', 'Người già lên bậc thềm mà chưa ai để ý, sợ trượt.'],
    'honest': ['Chuyện công đức nên rõ ràng hơn: {note}.'],
    'manner': ['Lời nhắc hơi gắt, tôi thấy ngại.', 'Mong lần sau được chỉ dẫn nhẹ nhàng hơn.'],
    'speed': ['Đứng chờ ở cổng hơi lâu.', 'Hỏi đường vào chánh điện mà phải chờ một lúc mới có người chỉ.'],
    'plan': ['Chuông sáng hôm nay hơi lệch giờ.'],
    'word': ['Thầy trẻ còn lơ đãng lúc nghe dặn.'],
    '': ['Có chỗ chưa được chu đáo: {note}.'],
}
# A visitor who remembers it differently (the records say otherwise: the player can answer with them).
UNFAIR = {'craft': 'sân còn đầy lá', 'safe': 'khói nhang bay khắp sân', 'honest': 'không thấy ai ghi sổ công đức',
          'manner': 'bị nhắc to trước mặt mọi người', 'speed': 'đứng chờ ở cổng mãi', 'plan': 'chuông sáng đánh muộn',
          'word': 'thầy trẻ chẳng nghe ai dặn'}
UNFAIR_LINE = ['Có điều tôi nhớ hôm đó {claim}.', 'Chỉ tiếc là {claim}.']
ITEM = dict(pos=['Việc {item} làm chu đáo.', '{item} làm khéo, nhìn là thấy có lòng.'],
            neg=['Việc {item} còn vội.'])
CLOSE = dict(
    festival_pos=['Ngày đông Phật tử mà chùa vẫn yên, quý lắm.', 'Rằm đông người mà ai cũng được chỉ chỗ thắp hương.'],
    festival_neg=['Biết là ngày đông, nhưng mong chùa để ý hơn.'],
    calm_pos=['Chiều vắng, ngồi hiên chùa nghe gió sông mà nhẹ người.'], calm_neg=['Chùa vắng mà vẫn còn sơ suất.'],
    early_pos=['Thầy trẻ còn lạ mặt mà làm việc đã chín chắn.'], early_neg=['Thầy trẻ chắc còn lạ việc, từ từ sẽ quen.'],
    late_pos=['Đi chùa này mấy chục năm, nếp chùa vẫn giữ như xưa.'], late_neg=['Lên chùa bao năm, hôm nay thấy hơi lạ.'],
)
SHORT = ['A Di Đà Phật. 🙏', 'Yên. Sạch. Mát.', 'Nghe chuông xong thấy nhẹ lòng.', 'Chùa hiền quá.', '🪷🙏', 'Bình an.']
LIFESTORY = [
    'Mẹ tôi mất năm ngoái, rằm nào tôi cũng lên chùa thắp nén nhang. Hôm nay {owner} đứng chờ tôi khấn xong mới dọn chiếu, không hối. Cảm ơn nhiều.',
    'Hồi nhỏ bà dắt tôi lên chùa này, giờ tôi dắt con. Hàng cau vẫn vậy, tiếng chuông vẫn trầm. Ghé một buổi mà nhớ bà quá.',
    'Tôi làm ca đêm, sáng tan ca hay ghé chùa ngồi nghe công phu. Hôm nay {owner} rót cho chén trà nóng, ấm cả bụng.',
]
# Careless reviews (shared twist kinds; the pagoda only ever gets these four).
TWIST_WEIGHTS = (('offtopic', 3), ('flip_low', 2), ('flip_high', 2), ('no_visit', 1))
TWIST_TEXT = {
    'offtopic': ['Đường xuống bến sông đang đào, bụi mù mịt. Một sao.', 'Trời nắng gắt, đi bộ lên chùa mệt muốn xỉu.',
                 'Điện thoại hết pin giữa đường, bực cả buổi.', 'Hôm nay tôi bị sếp mắng nên chấm một sao.',
                 'Gửi xe ở đầu bến mà chú giữ xe nói chuyện cộc lốc.', 'Mưa to, đường ra bến ngập, ướt hết giày.'],
    'no_visit': ['Chưa lên chùa bao giờ, nghe nói ngày rằm đông lắm nên chấm vậy.', 'Đi ngang thấy cổng đông người nên thôi, chấm tạm.',
                 'Chưa ghé, nghe hàng xóm kể chùa nghiêm quá nên ngại.'],
}
CLUES = {'offtopic': ['Không nói gì về buổi ghé chùa'], 'no_visit': ['Tự nhận chưa lên chùa']}
MOODS = ('knowitall', 'rude')      # a bad-day visitor; nobody at the pagoda bargains for gifts or threatens a "bóc phốt"


def _line(rows: dict, crit: dict) -> list:
    return rows.get(crit.get('key')) or rows['']


def compose(persona: str, stars: int, criteria: list, seed: int, unfair: dict | None = None) -> str:
    opens = (OPEN_BY.get(persona) or {}).get(stars) or OPEN[max(1, min(5, stars))]
    parts = [_pick(opens, seed)]
    best = max(criteria, key=lambda x: x['score'])
    worst = min(criteria, key=lambda x: x['score'])
    if unfair:
        parts.append(fill(_pick(UNFAIR_LINE, seed, 1), claim=unfair['claim']))
    elif worst['score'] <= 3:
        parts.append(fill(_pick(_line(BAD, worst), seed, 1), note=worst.get('note', '')))
    if best['score'] >= 4 and (not unfair or best['key'] != unfair['key']):
        parts.append(_pick(_line(GOOD, best), seed, 2))
    return ' '.join(parts)[:600]


def decorate(s: dict, c: dict, t: dict, stars: int, text: str, seed: int, item: str) -> str:
    """An item line and a closer that fits the day, like the shared path, in the pagoda's words."""
    from .feedback import _roll
    parts = [text]
    pos = stars >= 4
    if _roll('item', t['id'], c['day']) < .45:
        parts.append(_cap(fill(_pick(ITEM['pos' if pos else 'neg'], seed, 3), item=item)))
    if _roll('close', t['id'], c['day']) < .4:
        mode = ((c.get('life') or {}).get('mode')) if isinstance(c.get('life'), dict) else None
        day = c.get('day', 1)
        stage = mode if mode in ('festival', 'calm') and seed % 2 else 'early' if day <= 3 else 'late' if day >= 8 else None
        if stage:
            parts.append(_pick(CLOSE[stage + ('_pos' if pos else '_neg')], seed, 5))
    return ' '.join(parts)[:600]


def _twist(seed: int, fair: int) -> str:
    rows = [(k, w) for k, w in TWIST_WEIGHTS if not (k == 'flip_low' and fair < 4) and not (k == 'flip_high' and fair > 3)]
    x = seed % sum(w for _, w in rows)
    for k, w in rows:
        if x < w:
            return k
        x -= w
    return rows[-1][0]


def make_review(s: dict, c: dict, t: dict, status: str, ev: dict, persona: str, stars: int, seed: int) -> dict:
    """feedback.make_review for the pagoda: the same rolls and the same review record, the pagoda's words.
    No shop gripes ("con mèo trên quầy"), no shop aspects, no bargaining moods."""
    from . import feedback as fb_
    from . import feedback_voices as fv
    fair = stars
    item = fv.topic(t)
    owner = owner_call(s)
    twist = unfair = style = None
    clues, out, text = [], {}, None
    if status == 'completed' and not t.get('slips') and fb_._roll('twist', t['id'], c['day']) < fb_.twist_rate(c['day']):
        kind = _twist(fb_._hash('kind', t['id'], c['day']), fair)
        spec = fb_.TWISTS[kind]
        persona = spec['persona'] or persona
        if kind == 'flip_low' and fb_.PERSONAS[persona]['bias'] < 0:
            persona = ('warm', 'genz', 'quiet')[seed % 3]
        if kind == 'flip_low':
            stars, text = 1, compose(persona, fair, ev['criteria'], seed)
        elif kind == 'flip_high':
            stars, text = 5, compose(persona, fair, ev['criteria'], seed)
        else:
            stars, text = (1 + seed % 2 if kind == 'no_visit' else 1), _pick(TWIST_TEXT[kind], seed // 7)
        twist = dict(kind=kind, reportable=spec['reportable'])
        clues = list(CLUES.get(kind) or spec['clues'])
        if spec['stranger']:
            npc = fb_._stranger(t['career'], t['npc'], seed)
            from .content import NPC_INDEX
            out = dict(npc=npc, author=NPC_INDEX[npc]['display_name'])
    elif stars >= 5 and status == 'completed' and c['day'] >= 2 and seed % 6 == 0:
        crit = ev['criteria'][seed % len(ev['criteria'])]
        unfair = dict(key=crit['key'], label=crit['label'], claim=UNFAIR.get(crit['key'], 'có chỗ chưa như tôi nghĩ'), truth=crit['note'])
        stars = 3 if fb_.PERSONAS[persona]['bias'] < 0 else 4
    elif status == 'completed' and fb_._roll('mood', t['id'], c['day']) < fb_.mood_rate(c['day']):
        persona = MOODS[fb_._hash('mood', t['id']) % len(MOODS)]
        if stars >= 5:
            stars = 4
    if text is None and status == 'completed' and not (unfair or t.get('slips') or persona in fb_.HARSH) \
            and fb_._roll('style', t['id'], c['day']) < fv.style_rate(c.get('day', 1)):
        worst = min(ev['criteria'], key=lambda x: x['score'])
        if worst['score'] >= 4 and fair >= 4:
            if fb_._hash('style-kind', t['id'], c['day']) % 3 == 0:
                style, stars, text = 'lifestory', 5, fill(_pick(LIFESTORY, seed), owner=owner)
            else:
                style, text = 'short', _pick(SHORT, seed)
    if text is None:
        shown = [x for x in ev['criteria'] if not (t.get('slips') and x['key'] in ('accuracy', 'order'))] or ev['criteria']
        text = compose(persona, stars, shown, seed, unfair)
        if t.get('slips'):
            from . import mistake_lines
            text = mistake_lines.weave(text, t, seed)
        if not unfair:
            text = decorate(s, c, t, stars, text, seed, item)
    fb = dict(persona=persona, criteria=ev['criteria'], cap=ev['cap'], fair=fair, stars_original=stars, unfair=unfair,
              thread=[], status='open', rounds=0, pending=None, voice='scripted', task=t['id'], title=t.get('title', ''),
              value=int(t.get('_value', 0) or 0), item=item[:80])
    if style:
        fb['style'] = style
    if twist:
        fb['twist'] = twist
    if clues:
        fb['clues'] = clues
    if out:
        fb['stranger'] = True
    return dict(text=text[:600], stars=stars, feedback=fb,
                aside=not (twist or unfair or style or persona in fb_.HARSH or t.get('slips')), **out)


# ------------------------------------------------------------ the player answers
# Same ten tones (ids, risk, the outcome table) as every career; labels and words of the pagoda.
LABEL = {'warm': 'Từ tốn', 'funny': 'Tự trào', 'sassy': 'Đùa nhẹ', 'facts': 'Nêu sự thật', 'sorry': 'Xin lỗi, sửa ngay',
         'invite': 'Mời ghé lễ', 'process': 'Kể nếp chùa', 'genz': 'Trẻ trung', 'silent': 'Ngắn gọn', 'harsh': 'Đáp trả gắt'}
TONES = {
    'warm': ['A Di Đà Phật. Cảm ơn {who} đã ghé chùa và viết mấy dòng này. Góp ý về {label}, chùa xin ghi nhận ạ.',
             'Cảm ơn {who} đã lên chùa. Chuyện {label} chùa đã nghe, sẽ để ý hơn ạ.',
             'Đọc lời {who} viết, cả chùa thấy quý. Chùa xin ghi nhận và sửa dần ạ.'],
    'funny': ['Đọc xong mà chổi tre trong tay cũng đứng hình 😅 Chùa xin nhận phần {label} về sửa ạ.',
              'Dạ chùa xin ghi chuyện {label} lên bảng nội quy, sáng nào quét sân cũng đọc lại 😄',
              'Thầy trụ trì đọc xong cười hiền, giao ngay bài tập về {label} cho chùa rồi ạ 😅'],
    'sassy': ['Dạ theo sổ chùa thì {fact} ạ. Chắc hôm đó trời nóng nên {who} thấy lâu hơn thôi 🙂',
              'Chùa ghi nhận hết ạ. Riêng chuyện {label} thì {fact}, mời {who} ghé lại một sáng ngồi nghe chuông là thấy liền 😌',
              'Dạ chùa nhận góp ý, còn buồn thì để sau giờ công phu ạ 😌'],
    'facts': ['Dạ, sổ chùa hôm đó ghi: {fact}. Chùa gửi lại để {who} cùng xem cho rõ ạ.',
              'Chùa đã xem lại sổ ghi chép hôm đó: {fact}. Nếu {who} còn thấy chỗ nào chưa ổn, chùa xin xem thêm ạ.',
              'Dạ có ghi nhận cụ thể: {fact}. Chùa gửi {who} để mình cùng nhìn lại cho công bằng ạ.'],
    'sorry': ['A Di Đà Phật, chùa xin lỗi {who} vì {label} chưa chu đáo. Thầy trụ trì đã nhắc lại cả chùa, lần sau sẽ cẩn thận hơn ạ.',
              'Chùa xin lỗi {who} ạ. Chuyện {fact} là thiếu sót của chùa, đã sửa lại rồi ạ.',
              'Dạ chùa nhận thiếu sót. Mong {who} hoan hỷ, lần sau lên chùa sẽ thấy khác ạ.'],
    'invite': ['Cảm ơn {who} đã góp ý. Rằm tới mời {who} ghé lễ, chùa sẽ đón tiếp chu đáo hơn ạ.',
               'Lần sau {who} lên chùa cứ gọi một tiếng, chùa chỉ đường, dọn chỗ ngồi cho {who} ạ.',
               'Mời {who} sáng nào rảnh ghé nghe chuông, uống chén trà với chùa ạ 🍵'],
    'process': ['Dạ ở chùa việc gì cũng theo thời khóa: sáng quét sân, trưa lo bếp chay, công đức thì hai người cùng đếm. Hôm đó {fact}, chùa đang xem lại chỗ cần kỹ hơn ạ.',
                'Chùa làm theo nếp: nghe thầy dặn, làm từng việc, xong thì xem lại. Góp ý về {label} chùa đưa vào lời dặn mỗi sáng ạ.',
                'Dạ ngày rằm khách thập phương đông, chùa chỉ dẫn lần lượt nên có lúc phải chờ. Chùa đang sắp xếp lại để {label} tốt hơn ạ.'],
    'genz': ['Dạ chùa “note” lại liền ạ 📝 Lần sau {label} sẽ chỉn chu hơn, {who} ghé lại nghe chuông nha 🪷',
             'Real ạ, chùa nhận hết 🙏 Lần sau {who} lên là thấy khác liền nha ✨'],
    'silent': ['A Di Đà Phật. Chùa đã đọc, cảm ơn {who} ạ.', 'Dạ, chùa xin ghi nhận ạ.', 'Cảm ơn {who} 🙏'],
    'harsh': ['Không vừa ý thì {who} đi chùa khác, ở đây không cần.', 'Khó tính vậy thì khỏi lên chùa.',
              'Biết gì mà chê, lo chuyện của mình đi.'],
}
# A happy review: nothing to apologise for.
TONES_POS = {
    'warm': ['A Di Đà Phật. Cảm ơn {who} đã ghé chùa, đọc mấy dòng này cả chùa vui lây ạ.', 'Cảm ơn {who} đã thương chùa. Rằm tới mời {who} lên lễ ạ.'],
    'funny': ['Đọc xong cả chùa cười hiền, chổi tre quét sân cũng nhẹ tay hơn 😄 Cảm ơn {who} ạ!'],
    'sassy': ['Dạ chùa vẫn quét sân mỗi sáng mà, nhưng được {who} để ý thì vẫn vui ạ 😌'],
    'facts': ['Dạ sổ chùa hôm đó ghi: {fact}. Cảm ơn {who} đã để ý kỹ vậy ạ.'],
    'sorry': ['Nếu có gì chưa chu đáo, chùa xin {who} hoan hỷ bỏ qua ạ. Cảm ơn {who} nhiều.'],
    'invite': ['Cảm ơn {who} nhiều ạ! Lần sau lên chùa, mời {who} ở lại dùng cơm chay trưa ạ.'],
    'process': ['Dạ nếp chùa là làm từng việc nhỏ, việc nào cũng xem lại. Cảm ơn {who} đã nhận ra ạ.'],
    'genz': ['Được khen là chùa vui lắm luôn ạ 🙏 {who} ghé lại nghe chuông nha ✨'],
    'silent': ['A Di Đà Phật, cảm ơn {who} ạ.', 'Cảm ơn {who} 🙏'],
    'harsh': ['Khen thì khen, biết gì mà chấm với chả điểm.', 'Không cần khen, lo chuyện của mình đi.'],
}


def tone_texts(post_id, rounds, happy, who, label, fact, _hash) -> tuple:
    """One reply text per tone (feedback_voices.TONE_ORDER), like feedback_voices._tone_texts."""
    from .feedback_voices import TONE_ORDER
    out = []
    for tid in TONE_ORDER:
        rows = (TONES_POS if happy else TONES)[tid]
        out.append(_cap(fill(_pick(rows, _hash('tpl', post_id, rounds, tid)), who=who, label=label, fact=fact)))
    return tuple(out)


# -------------------------------------------------------- the visitor answers back
REACT = {
    'up': ['Đọc lời {owner} viết mà thấy nhẹ lòng, tôi sửa lại sao nhé.', 'Cảm ơn {owner} đã trả lời tử tế. Tôi thêm sao.',
           'Thấy chùa nhận và sửa, tôi yên tâm rồi.'],
    'moved': ['Đọc xong mà rưng rưng. Tôi sửa lại cho đúng lòng mình.', 'A Di Đà Phật, cảm ơn {owner}. Rằm tới tôi lại lên chùa.'],
    'keep': ['Cảm ơn {owner} đã trả lời. Tôi để nguyên cảm nhận nhé.', 'Tôi đọc rồi. Để lần sau lên chùa xem sao.',
             'Biết là chùa có lòng, nhưng tôi vẫn giữ ý mình.'],
    'seen': ['Đã đọc.', 'Vâng.'],
    'argue': ['Tôi vẫn thấy {note}, mong {owner} xem lại giúp.', 'Không phải tôi khó, nhưng hôm đó đúng là {note}.'],
    'down': ['Lên chùa mà nhận câu trả lời vậy, tôi buồn thật. Hạ sao.', 'Tôi không nghĩ ở chùa lại được trả lời như thế.'],
    'jab': ['Đùa kiểu đó không hợp ở chùa đâu {owner}.'],
    'thanks': ['Dạ, tôi cảm ơn {owner}. Hẹn ngày rằm.', 'A Di Đà Phật, cảm ơn {owner} nhiều.'],
    'flip_fix': ['Ơ, tôi bấm nhầm sao thật. Sửa lại liền, xin lỗi {owner} 🙏', 'Trời, tay nhanh hơn mắt, tôi chấm nhầm. Sửa rồi.'],
    'flip_keep': ['Góp ý vậy thôi, sao thì cứ để nguyên.'],
    'offtopic': ['Biết là không phải lỗi của chùa, nhưng hôm đó tôi bực thật.', 'Ừ thì chuyện ngoài đường, nhưng tôi chấm theo cảm xúc.'],
    'offtopic_soft': ['Thôi thấy {owner} trả lời hiền quá, tôi thêm một sao.', 'Ừ, đâu phải lỗi của chùa. Tôi sửa lại.'],
    'no_visit': ['Để hôm nào rảnh tôi lên chùa thử.', 'Chưa ghé thật, nhưng cứ để vậy đã.'],
    'pile_on': ['Tôi đọc rồi, vẫn giữ ý mình.', 'Mong lần sau chùa bình tĩnh hơn.'],
    'pile_on_soft': ['Thấy chùa nhận sai thì tôi bớt buồn. Nâng lên chút.'],
}


def react(s: dict, post: dict, decision: dict, seed: int) -> dict:
    """The visitor's answer to the player's reply, in the pagoda's words. Same decision and stars."""
    from .feedback import _kind
    fb = post['feedback']
    kind = _kind(fb)
    d = decision.get('decision')
    stars = post.get('stars') or 0
    if kind == 'flip_low':
        key = 'flip_fix' if d == 'revise_up' else 'keep'
    elif kind == 'flip_high':
        key = 'flip_keep'
    elif kind == 'offtopic':
        key = 'offtopic_soft' if d == 'revise_up' else 'offtopic'
    elif kind == 'pile_on':
        key = 'pile_on_soft' if d == 'revise_up' else 'pile_on'
    elif kind == 'no_visit':
        key = 'no_visit'
    elif kind == 'fan' or (d == 'keep' and stars >= 5):
        key = 'thanks'
    elif d == 'revise_up':
        key = 'moved' if (decision.get('stars') or 0) - stars >= 2 else 'up'
    elif d == 'revise_down':
        key = 'jab' if decision.get('sass') == 'lost' else 'down'
    elif d == 'argue':
        key = 'argue'
    else:
        key = 'seen' if decision.get('tone') == 'silent' else 'keep'
    worst = min(fb['criteria'], key=lambda x: x['score'])
    note = fb['unfair']['claim'] if fb.get('unfair') else worst.get('note', '')
    return dict(decision, text=fill(_pick(REACT[key], seed), owner=owner_call(s), note=note))


# ------------------------------------------------------------ the people around
GUEST_NAMES = [('Bà Sáu xóm bến', '👵'), ('Chú Hai giữ xe', '🛵'), ('Cô Út', '🙏'), ('Anh Khoa', '🧢'),
               ('Bác Tám chèo đò', '🚣'), ('Chị Mai ban hộ niệm', '📿'), ('Bé Bin', '🎈')]
GUEST_TEXT = dict(
    defend=['Tôi lên chùa này mấy chục năm, thầy trả lời vậy là hiền lắm rồi.', 'Bình tĩnh nha, ở chùa ai cũng có lòng mà.',
            'Hôm đó tôi cũng có mặt, chùa làm đúng mà.'],
    cheer=['Đọc lời chùa trả lời mà thấy nhẹ lòng 🙏', 'A Di Đà Phật, chùa mình hiền quá.', 'Rằm tới tôi rủ cả nhà lên chùa.'],
    troll=['Ủa rồi sao nữa, kể tiếp đi 👀', 'Hóng 🍿'],
    agree=['Ở chùa mà trả lời vậy là không nên.', 'Khách thập phương góp ý thì nghe thôi, sao gắt vậy.'],
    fake=['Ủa, chùa mình đâu có chuyện đó.', 'Hình như bạn nhầm chỗ rồi á.', 'Tài khoản này mới lập mà ta 🤔'],
)
FAN_TEXT = ['Nghe {author} kể nên sáng nay lên chùa, đúng là yên thật 🙏', '{author} rủ đi lễ rằm, lần đầu lên mà thấy thương chùa liền.',
            'Đọc lời {author} viết, tôi dắt mẹ lên chùa. Mẹ vui cả buổi.']
FANS_NOTE = '{author} rủ bà con lên chùa: thêm {n} cảm nhận tốt.'
PILE_ON = dict(
    customer=['Đọc câu trả lời của chùa mà buồn. Một sao.', 'Ở chùa mà nói với khách thập phương như vậy à?',
              'Từng lên chùa này, đọc câu trả lời thì thấy tiếc.'],
    report=['Khách góp ý thật mà chùa đi báo cáo, tôi thấy không hay.', 'Góp ý thật lòng mà bị báo cáo, buồn ghê.'],
    phot=['Nghe kể trong xóm rồi, buồn ghê.'],
)
PILE_LABEL = 'Cách trả lời khách thập phương'
REPORT_ANGRY = ['Tôi kể thật lòng mà bị báo cáo. Hạ thêm sao.', 'Góp ý cho chùa mà bị báo cáo, buồn ghê.']
REMEMBER = 'Đã sửa cảm nhận sau khi đọc lời chùa hồi đáp.'
VIRAL = 'Câu trả lời gắt bị chụp lại, lan khắp xóm: thêm {n} cảm nhận 1★.'
SASS_LOST = 'Câu đùa bị chụp lại, bà con không vui: thêm {n} cảm nhận 1★.'
OFFER_LEDGER = 'Biếu khách thập phương: '
# What happens after an answer, in the game's status line.
RESOLVED = {'revise_up': 'đã sửa cảm nhận tốt hơn', 'revise_down': 'đã sửa cảm nhận thấp hơn', 'argue': 'muốn nói thêm',
            'keep': 'giữ nguyên cảm nhận'}
IGNORED = 'Đã để đó. Cảm nhận vẫn giữ nguyên.'
PHOT_LINE = 'Chùa im lặng thì tôi kể với bà con trong xóm vậy.'
PHOT_MSG = '{author} kể chuyện khắp xóm: thêm {n} cảm nhận 1★.'
REPORT_OK = 'Cảm nhận này đã được gỡ. Điểm trung bình không còn tính nó.'
REPORT_NO = 'Không gỡ được: khách có ghé chùa thật. {author} biết chuyện và buồn hơn.'
REPORT_EXTRA = ' Thêm {n} cảm nhận 1★ vì chuyện này.'

# The optional AI voice (game/ai.py): where the visitor is and what never to say.
AI_ROLE = 'khách thập phương ghé chùa Gió Lành viết cảm nhận, rồi đọc lời hồi đáp của thầy trẻ ở chùa'
AI_RULE = ('Bối cảnh: chùa Gió Lành là ngôi chùa lâu năm của phố (không phải chùa mới mở), không phải cửa hàng. '
           'Người trả lời là thầy trẻ ở chùa. Bạn là khách thập phương / Phật tử: nói về sự yên tĩnh, sân chùa sạch, '
           'được chỉ dẫn nhẹ nhàng, giữ yên lặng giờ tụng kinh, tìm đường, bữa cơm chay, sổ công đức. Giữ lời lẽ tôn trọng Phật giáo, '
           'không chế giễu. Tuyệt đối không dùng từ buôn bán: quán, tiệm, shop, dịch vụ, giá, khuyến mãi, ủng hộ, khách hàng; '
           'không nhắc chuyện đổi tiền lấy may mắn hay phước lộc. ')
