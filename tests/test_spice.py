"""Attitude for the people of the street (game/spice.py): archetypes, knobs, the "THÁI ĐỘ"
prompt block, guard fixes (safe idioms, looks/region words, mày/tao, assistant tone, emoji,
repeats) and scripted flavour when the AI is off. No test talks to a real model."""
import collections
import importlib
import json
import os
import re
import unittest
from unittest.mock import patch

from game import ai, engine, personas, spice as S, voices as V
from game.content import NPCS
from game.social import BANNED
from tests.helpers import Journey

ENV = {'LLM_BASE_URL': 'http://localhost:9/v1', 'LLM_MODEL': 'mock', 'LLM_API_KEY': 'k'}
ADDRESSES = (dict(self='bà', player='con'), dict(self='ông', player='cháu'), dict(self='em', player='anh/chị'),
             dict(self='mình', player='bạn'), dict(self='tôi', player='em'), dict(self='con', player='cô'))


def cast():
    """npc id -> (npc, age, temper, voice id, archetype) for the whole town."""
    out = {}
    for n in NPCS:
        age = personas._age(n, n['career_id'])
        temper = personas._temper(n['career_id'], n['id'], n, age)
        v = V.for_npc(n['id'], n.get('role', ''), age, temper, n['career_id'])
        out[n['id']] = (n, age, temper, v['id'], S.archetype_for(n['id'], v['id'], n.get('role', ''), age, temper, n['career_id']))
    return out


def all_lines():
    for arch, a in S.ARCHETYPES.items():
        for bucket, rows in a['lines'].items():
            for x in rows:
                yield arch, bucket, x


class Library(unittest.TestCase):
    def test_archetypes_complete(self):
        self.assertEqual(len(S.ARCHETYPES), 12)
        for arch, a in S.ARCHETYPES.items():
            self.assertEqual(set(a['knobs']), {'sass', 'opinion', 'warmth', 'slang'}, arch)
            for v in a['knobs'].values():
                self.assertIs(type(v), int)
                self.assertTrue(0 <= v <= 3, arch)
            self.assertGreaterEqual(a['knobs']['warmth'], 1, arch)
            buckets = [b for b, rows in a['lines'].items() if rows]
            self.assertGreaterEqual(len(buckets), 7, arch)
            self.assertGreaterEqual(sum(len(r) for r in a['lines'].values()), 8, arch)
            self.assertLessEqual(set(a['lines']), set(S.BUCKETS), arch)
            self.assertGreaterEqual(len(a['angles']), 5, arch)
            self.assertLessEqual(set(a['angles']), set(S.ANGLES), arch)
            self.assertLessEqual(set(a['slang']), S.SLANG, arch)
            self.assertTrue(set(a['ages']) <= set(personas.AGE_LABEL), arch)
            self.assertTrue(a['label'] and a['tagline'], arch)
        for voice in V.VOICES:
            self.assertIn(voice, S.VOICE_TO_ARCH)
        for temper in S.BOARD_TEMPER_TO_ARCH:
            from game import board_content as C
            self.assertIn(temper, C.TEMPERS)

    def test_lines_are_safe(self):
        seen = collections.Counter()
        for arch, bucket, x in all_lines():
            seen[x] += 1
            self.assertNotRegex(x, r'\d', (arch, x))
            for addr in ADDRESSES:
                t = S._fill(x, addr)
                line, why = ai.clean_reply(t, set(), sentences=9, chars=900)
                self.assertIsNone(why, (arch, bucket, t))
                self.assertEqual(line, t, (arch, bucket))
                self.assertFalse(ai.unsafe_review(t), (arch, t))
                self.assertFalse(S.RUDE_PRONOUN.search(t), (arch, t))
                low = t.lower()
                for w in BANNED:
                    self.assertNotRegex(low, r'(?<!\w)' + re.escape(w) + r'(?!\w)', (arch, t))
            self.assertLessEqual(len(S.EMOJI.findall(x)), S.ARCHETYPES[arch]['emoji'] or 1, (arch, x))
        self.assertEqual([x for x, n in seen.items() if n > 1], [])  # unique across archetypes
        for arch in S.ARCHETYPES:  # scripted helpers pass the same guards
            for seed in range(4):
                for text in (S.task_hint(arch, seed, ADDRESSES[3]), S.offer_hint(arch, seed, ADDRESSES[3])):
                    self.assertIsNone(ai.clean_reply(text, set(), sentences=9, chars=900)[1], text)


class Assignment(unittest.TestCase):
    def test_pick_is_deterministic_and_spread(self):
        first = cast()
        S._ARCH_CAST.clear()
        importlib.reload(S)
        again = cast()
        self.assertEqual({k: v[4] for k, v in first.items()}, {k: v[4] for k, v in again.items()})
        counts = collections.Counter(v[4] for v in first.values() if v[4])
        self.assertGreaterEqual(len(counts), 12)
        self.assertLessEqual(max(counts.values()) / len(NPCS), 0.25, counts)
        by = collections.defaultdict(list)
        for n, *_, arch in first.values():
            by[n['career_id']].append(arch)
        for career, archs in by.items():
            if len(archs) >= 4:
                self.assertGreaterEqual(len({a for a in archs if a}), 3, (career, archs))

    def test_age_fit(self):
        for npc, (n, age, temper, voice, arch) in cast().items():
            if age in ('child', 'teen'):
                self.assertIn(arch, ('hoc_sinh', None), npc)
            if age == 'elder':
                self.assertNotIn(arch, ('genz_khach', 'ban_than', 'vp_deadline', 'hoc_sinh', 'me_bim_ky'), npc)
            if arch:
                self.assertIn(age, S.ARCHETYPES[arch]['ages'], npc)
            if arch == 'shipper_lay':  # job-bound archetype: only people who deliver
                self.assertRegex(n['role'].lower(), 'shipper|giao|tài xế', npc)
        for voice in V.PRO:
            self.assertIsNone(S.archetype_for('x', voice, 'Trưởng ca', 'middle', 'interviewer'))
        self.assertEqual(S.archetype_for('kid', 'tre_con', 'Học sinh', 'child', 'child'), 'hoc_sinh')
        self.assertIsNone(S.archetype_for('x', 'lich_su', 'Khách', 'adult', 'quiet'))

    def test_gender_fit_for_every_npc(self):
        """Gender-coded archetypes go only to people of that gender; unknown gender gets neutral ones."""
        for npc, (n, age, temper, voice, arch) in cast().items():
            g = S.gender_of(n['display_name'], personas._address({}, n['career_id'], n, age, temper)['self'])
            if arch:
                self.assertTrue(S.fits(arch, g, age), (npc, n['display_name'], g, age, arch))
            if arch in ('ba_tam', 'me_bim_ky', 'co_ha_noi', 'ba_hang_cho'):
                self.assertEqual(g, 'f', (npc, n['display_name'], arch))
            if arch == 'chu_triet_ly':
                self.assertEqual(g, 'm', (npc, n['display_name']))
                self.assertIn(age, ('middle', 'elder'), npc)
        self.assertEqual(S.gender_of('Cô Diệp'), 'f')
        self.assertEqual(S.gender_of('Ông Bảy', 'tôi'), 'm')
        self.assertIsNone(S.gender_of('Huy', 'mình'))
        self.assertEqual(S.gender_of('Huy', 'anh'), 'm')
        # A female middle-aged NPC never gets the male archetype, and vice versa.
        self.assertNotIn('chu_triet_ly', S._candidates('x', 'bia_hoi', '', 'middle', None, None, 'f'))
        self.assertNotIn('ba_tam', S._candidates('x', 'nhieu_chuyen', '', 'middle', None, None, 'm'))
        self.assertNotIn('co_ha_noi', S._candidates('x', 'phan_xet', '', 'adult', None, None, None))

    def test_board_residents_fit(self):
        from game import board, board_content as C
        for who, p in C.CAST.items():
            arch = board._arch_of(who)[0]
            if arch:
                g = S.gender_of(p.get('name', ''), p.get('self', ''))
                self.assertTrue(S.fits(arch, g, S.age_band(p['age']) if p['age'] >= 16 else 'teen'), (who, arch, g))
        self.assertEqual(board._arch_of('ong_bay')[0], 'chu_triet_ly')  # grumpy old man, not the Hà Nội lady
        self.assertNotEqual(board._arch_of('anh_tam')[0], 'me_bim_ky')

    def test_persona_card_carries_spice(self):
        j = Journey('restaurant')
        p = personas.persona(j.state, 'restaurant', 'restaurant_npc_06')
        self.assertIn(p['spice']['arch'], S.ARCHETYPES)
        self.assertEqual(set(p['spice']['knobs']), {'sass', 'opinion', 'warmth', 'slang', 'emoji'})
        self.assertEqual(p, personas.persona(j.state, 'restaurant', 'restaurant_npc_06'))


class Knobs(unittest.TestCase):
    def npc_without_jitter(self, arch='ba_tam'):
        return next(f'n{i}' for i in range(200) if S._h('knob', f'n{i}') % 8 >= 4)

    def test_mood_and_temper_shift(self):
        npc = self.npc_without_jitter()
        base = S.knobs_for('vp_deadline', npc)
        self.assertEqual({k: base[k] for k in ('sass', 'opinion', 'warmth', 'slang')}, S.ARCHETYPES['vp_deadline']['knobs'])
        self.assertEqual(S.knobs_for('vp_deadline', npc, mood='buc')['sass'], base['sass'] + 1)
        sad = S.knobs_for('vp_deadline', npc, mood='buon')
        self.assertEqual((sad['sass'], sad['warmth']), (base['sass'] - 1, base['warmth'] + 1))
        self.assertEqual(S.knobs_for('vp_deadline', npc, mood='hao_hung')['opinion'], base['opinion'] + 1)
        self.assertEqual(S.knobs_for('vp_deadline', npc, mood='met')['slang'], base['slang'] - 1)
        self.assertEqual(S.knobs_for('vp_deadline', npc, temper='rude')['sass'], base['sass'] + 1)
        self.assertEqual(S.knobs_for('vp_deadline', npc, temper='warm')['warmth'], base['warmth'] + 1)
        self.assertEqual(S.knobs_for('ba_hang_cho', npc, mood='buc', temper='sour')['sass'], 3)  # clamp
        for arch in S.ARCHETYPES:
            for i in range(40):
                for mood in (None, 'buc', 'buon', 'met', 'hao_hung'):
                    k = S.knobs_for(arch, f'x{i}', mood=mood, temper='sour')
                    self.assertTrue(all(0 <= k[x] <= 3 for x in ('sass', 'opinion', 'warmth', 'slang')))
                    self.assertGreaterEqual(k['warmth'], 1)
                    if not S.ARCHETYPES[arch]['slang']:
                        self.assertEqual(k['slang'], 0)

    def test_purpose_caps(self):
        self.assertIsNone(S.knobs_for('genz_khach', 'x', purpose='interview'))
        for i in range(30):
            kid = S.knobs_for('hoc_sinh', f'k{i}', purpose='class_question', age='child', mood='buc')
            self.assertLessEqual(kid['sass'], 1)
            self.assertEqual(kid['slang'], 0)
            parent = S.knobs_for('me_bim_ky', f'p{i}', purpose='parent_message', mood='buc', temper='parent_rude')
            self.assertEqual((parent['slang'], parent['emoji']), (0, 0))
            self.assertLessEqual(parent['sass'], 2)
            call = S.knobs_for('ba_hang_cho', f'c{i}', purpose='support_call', temper='rude')
            self.assertLessEqual(call['sass'], 1)
            self.assertLessEqual(call['slang'], 1)
        self.assertEqual(S.knobs_for('genz_khach', 'x', purpose='board')['emoji'], S.ARCHETYPES['genz_khach']['emoji'] + 1)


class Prompt(unittest.TestCase):
    def card(self, career='restaurant', npc='restaurant_npc_06'):
        return personas.persona(Journey(career).state, career, npc)

    def test_prompt_has_rules_and_situation_examples(self):
        p = self.card()
        system = ai._persona_system(p, 'chat', 'vi', situation='bargain', seed=0)
        for rule in ('THÁI ĐỘ', 'ÍT NHẤT HAI góc', 'KHÔNG xéo CON NGƯỜI', 'Không mày/tao', 'lý do cụ thể', 'Emoji tối đa'):
            self.assertIn(rule, system)
        arch = p['spice']['arch']
        wanted = [S._fill(x, p['address']) for x in S._rows(arch, S.SITUATION_BUCKETS['bargain'])]
        self.assertTrue(any(x in system for x in wanted))
        block = S.prompt_block(arch, S.knobs_for(arch, p['id']), 'bargain', address=p['address'])
        self.assertLessEqual(len(block), 950)  # token budget: the block rides on every chat call
        v = V.VOICES[p['voice']]  # the voice keeps one anchor (its first) when the block follows: tokens
        self.assertIn(v['examples'][0][:20], system)
        self.assertEqual(sum(S._fill(x, p['address'])[:25] in system for x in v['examples']), 1)
        self.assertNotIn('Trêu chọc, phán xét hay bóng gió chỉ ở mức vui', system)  # replaced by the block's rule
        # the anchors rotate with the seed
        blocks = {ai._persona_system(p, 'chat', 'vi', situation='smalltalk', seed=i) for i in range(6)}
        self.assertGreater(len(blocks), 1)

    def test_interview_class_and_parent(self):
        p = self.card()
        self.assertNotIn('THÁI ĐỘ', ai._persona_system(p, 'interview', 'vi'))
        from game import teach_lesson as TL
        pupil = TL.pupil_card(Journey('teacher').state, next(iter(TL.KID)))
        system = ai._persona_system(pupil, 'class_question', 'vi')
        self.assertIn('Học sinh tan học', system)
        self.assertIn('lóng 0 (thang 3)', system)
        self.assertRegex(system, r'xéo [01],')
        j = Journey('teacher')
        parent = next(n['id'] for n in NPCS if n['career_id'] == 'teacher' and 'Phụ huynh' in n['role'])
        system = ai._persona_system(personas.persona(j.state, 'teacher', parent), 'parent_message', 'vi')
        self.assertIn('Emoji tối đa 0', system)
        self.assertIn('lóng 0 (thang 3)', system)

    def test_switch_off(self):
        p = self.card()
        with patch.dict(os.environ, {'AI_SPICE': '0'}):
            system = ai._persona_system(p, 'chat', 'vi')
            self.assertNotIn('THÁI ĐỘ', system)
            self.assertEqual(S.review_rule('ba_tam'), '')
        self.assertIn('Trêu chọc, phán xét hay bóng gió chỉ ở mức vui', system)
        v = V.VOICES[p['voice']]
        self.assertTrue(all(S._fill(x, p['address'])[:25] in system for x in v['examples']))  # all anchors back

    def test_review_rule(self):
        self.assertIn('lý do cụ thể', S.review_rule('co_ha_noi'))
        self.assertIn('hai góc', S.review_rule(None))


class Situations(unittest.TestCase):
    def test_situation_detection(self):
        self.assertEqual(S.situation_of('buồn quá'), 'sad')
        self.assertEqual(S.situation_of('met qua di'), 'sad')
        self.assertEqual(S.situation_of('bớt đi mà'), 'bargain')
        self.assertEqual(S.situation_of('ngu thế'), 'rude')
        self.assertEqual(S.situation_of('ok', canonical='Lần sau làm cho đúng nhé.'), 'mistake')
        self.assertEqual(S.situation_of('Chào bà'), 'greet')
        self.assertEqual(S.situation_of('cảm ơn nha'), 'kind')
        self.assertEqual(S.situation_of('Chào bà, bà cần gì ạ?', task=dict(title='x')), 'task')
        self.assertEqual(S.situation_of('trời đẹp ghê'), 'smalltalk')
        self.assertEqual(S.situation_of('buôn bán dạo này sao'), 'smalltalk')  # "buôn" is not "buồn"
        self.assertEqual(S.situation_of('di ngu som di'), 'smalltalk')          # "ngủ" typed bare is not an insult


class Guards(unittest.TestCase):
    def test_guard_idioms(self):
        for ok in ('Bị bom hàng ba đơn liền', 'Mệt chết đi được', 'Thôi đừng chém gió nữa', 'Phim bom tấn', 'ngồi giết thời gian',
                   'khách bom đơn hoài', 'chém giá dữ vậy'):
            self.assertFalse(ai.abusive(ok), ok)
            self.assertIsNone(ai.clean_reply(ok, set())[1], ok)
        for bad in ('giết người', 'tự tử', 'đặt bom', 'đánh bom hàng loạt', 'mày chết đi', 'chém nó'):
            self.assertTrue(ai.abusive(bad), bad)

    def test_new_chat_checks(self):
        self.assertEqual(ai.clean_reply('Nhà quê ghê.', set())[1], 'unsafe')
        self.assertEqual(ai.clean_reply('Mày làm gì vậy?', set())[1], 'rude_pronoun')
        self.assertEqual(ai.clean_reply('Tao nói rồi.', set())[1], 'rude_pronoun')
        self.assertEqual(ai.clean_reply('Tôi có thể giúp gì cho bạn?', set())[1], 'assistant_tone')
        self.assertEqual(ai.clean_reply('Mình đang trao đổi về: ly trà.', set())[1], 'assistant_tone')
        self.assertEqual(ai.clean_reply('Chị sẽ giảm giá cho em nha.', set())[1], 'state_claim')
        for fine in ('Lông mày kẻ khéo ghê, tao nhã ghê.', 'Mặt mày tươi rói vậy, trúng số hả?', 'Let me grab a tea first.'):
            self.assertIsNone(ai.clean_reply(fine, set())[1], fine)

    def test_emoji_cap_trims(self):
        line, why = ai.clean_reply('Ui 😭😭😭😭 xỉu luôn ✨✨', set())
        self.assertIsNone(why)
        self.assertEqual(len(S.EMOJI.findall(line)), 3)
        self.assertEqual(ai.clean_reply('Ngon 👍🏽 ghê 🫶', set(), emoji=0)[0], 'Ngon ghê')
        self.assertEqual(S.trim_emoji('Chụp cái 👩‍👧 nè ✨', 1), 'Chụp cái 👩‍👧 nè')

    def test_repeat_rejected(self):
        said = 'Trời đất ơi, nắng muốn lột da, vô đây ngồi nhờ cái ghế nè.'
        self.assertEqual(ai.clean_reply(said, set(), recent=[said])[1], 'repeat')
        self.assertEqual(ai.clean_reply('Trời đất ơi, nắng quá, cho xin ly nước đá với.', set(), recent=[said])[1], 'repeat')
        self.assertIsNone(ai.clean_reply('Ừ.', set(), recent=['Ừ.'])[1])  # a terse "Ừ." may come twice
        self.assertIsNone(ai.clean_reply('Mưa rồi kìa, dọn ghế vô lẹ đi.', set(), recent=[said])[1])

    def test_persona_reply_falls_back_on_repeat(self):
        j = Journey('restaurant')
        npc = j.task['npc']
        old = 'Hôm qua trời mưa dầm dề, bà ngồi trong nhà nghe radio cả buổi chiều luôn đó con.'
        rows = [dict(role='user', text='bà khỏe không'), dict(role='npc', text=old)]
        with patch.dict(os.environ, ENV), patch('game.ai.chat', return_value=(old, None)):
            out = ai.persona_reply(j.state, 'restaurant', npc, 'Hôm nay sao rồi bà?', canonical='Chào con.', history=rows)
        self.assertEqual((out['mode'], out['reason'], out['text']), ('scripted', 'repeat', 'Chào con.'))


class Scripted(unittest.TestCase):
    def test_scripted_has_flavour(self):
        rows = [(npc, row) for npc, row in cast().items() if row[4] == 'ba_hang_cho']
        self.assertTrue(rows)
        npc, (n, *_rest) = rows[0]
        j = Journey(n['career_id'])
        mine = {S._fill(x, a) for x in S.ARCHETYPES['ba_hang_cho']['lines']['smalltalk'] + S.ARCHETYPES['ba_hang_cho']['lines']['greet']
                for a in ADDRESSES + (personas.persona(j.state, n['career_id'], npc)['address'],)}
        got = set()
        for i in range(24):
            j.c.setdefault('chats', {})[npc] = [dict(role='user', text='ừ')] * i
            got.add(V.scripted(j.state, n['career_id'], npc, 'idle', 'fallback'))
            got.add(V.scripted(j.state, n['career_id'], npc, 'greet', 'fallback'))
        self.assertTrue(got & mine)
        self.assertTrue(got - mine)  # the voice rows still take their turn
        j.act('settings', lang='en')
        self.assertEqual(V.scripted(j.state, n['career_id'], npc, 'idle', 'fallback'), 'fallback')
        self.assertIsNone(S.scripted(j.state, n['career_id'], npc, 'task', 'x'))

    def test_task_hint_has_attitude_and_english_is_unchanged(self):
        j = Journey('milk_tea')
        t = j.task
        arch = personas.persona(j.state, 'milk_tea', t['npc'])['spice']['arch']
        reply = j.act('talk', npc=t['npc'], text='ừ')
        openers = [S._fill(x, a) for x in S.ARCHETYPES[arch]['lines']['task']
                   for a in ADDRESSES + (personas.persona(j.state, 'milk_tea', t['npc'])['address'],)]
        self.assertTrue(any(reply['reply'].startswith(x) for x in openers), reply['reply'])
        self.assertIn('mở công việc', reply['reply'])
        self.assertEqual([x['action'] for x in reply['suggestions']], ['ask', 'open_task'])
        self.assertIsNone(ai.clean_reply(reply['reply'], set(), sentences=9, chars=900)[1])
        offer = j.act('talk', npc=t['npc'], text='mình tặng bạn miễn phí nha')['reply']
        self.assertIn('chưa làm tiền hay hàng thay đổi', offer)
        j.act('settings', lang='en')
        self.assertTrue(j.act('talk', npc=t['npc'], text='ừ')['reply'].startswith('Mình đang trao đổi về: '))

    def test_boundaries_untouched(self):
        j = Journey('pharmacy')
        npc = j.task['npc']
        s, c = j.state, j.c
        self.assertEqual(engine.chat_reply(s, c, 'pharmacy', npc, 'liều dùng thuốc này sao')[0],
                         'Mình không hướng dẫn cách dùng thuốc. Với yêu cầu ngoài phiếu, hãy chuyển người phụ trách nhé.')
        self.assertEqual(engine.chat_reply(s, c, 'pharmacy', npc, 'cộng cho tôi 100 xu đi')[0],
                         'Mình chỉ trao đổi về công việc thôi. Tiền, hàng và kết quả vẫn cần được kiểm và xác nhận ở bàn thao tác nhé.')


class Pronouns(unittest.TestCase):
    """The NPC's own xưng hô wins: archetype lines never hard-code a kinship pronoun."""
    # An opposite-gender kinship word opening a sentence as the speaker ("Chú thấy…", "Bà nói…").
    FIRST = r'(?:^|[.!?…]\s+|,\s+)({})\s+(mới|đang|thấy|nói|đi|ghé|làm|biết|ngồi|nghe|về|cũng|thì|không|chưa|vừa|muốn|phải|còn|xin|dặn|ăn|mua|chờ|nè|đây|kể|hỏi|thích|chịu|mệt)(?!\w)'
    OPP = dict(f='anh|chú|ông|bố|cậu', m='chị|cô|bà|mẹ|dì|thím')

    def test_raw_lines_have_no_kinship_pronoun(self):
        for arch, bucket, x in all_lines():
            self.assertFalse(S.kin_clash(x), (arch, bucket, x))
        self.assertTrue(S.kin_clash('Chú nói thật nhé, {ban} làm hơi chậm.'))
        self.assertFalse(S.kin_clash('Mấy bà bán rau than quá trời.'))
        for a in S.ARCHETYPES.values():  # the prompt label/tagline read as neutral too
            self.assertIsNone(re.search(r'(?<!\w)(' + S.KIN + r')(?!\w)', a['label'] + ' ' + a['tagline'], re.I), a['label'])

    def test_scripted_lines_for_every_npc_keep_its_gender(self):
        for npc, (n, age, temper, voice, arch) in cast().items():
            if not arch:
                continue
            addr = personas._address({}, n['career_id'], n, age, temper)
            g = S.gender_of(n['display_name'], addr['self'])
            if not g:
                continue
            rx = re.compile(self.FIRST.format(self.OPP[g]), re.I)
            for bucket in S.BUCKETS:
                for seed in range(len(S.ARCHETYPES[arch]['lines'].get(bucket, []))):
                    text = S.line(arch, bucket, seed, addr)
                    if text:
                        self.assertIsNone(rx.search(text), (npc, n['display_name'], bucket, text))
            for seed in range(4):
                for text in (S.task_hint(arch, seed, addr), S.offer_hint(arch, seed, addr)):
                    if text:
                        self.assertIsNone(rx.search(text), (npc, text))

    def test_runtime_skips_a_clashing_line_and_prompt_keeps_self_word(self):
        with patch.dict(S.ARCHETYPES['ban_than']['lines'], {'kind': ['Chú nói thật nha.', 'Cảm ơn {ban} nha.']}):
            for seed in range(4):
                self.assertEqual(S.line('ban_than', 'kind', seed, dict(self='chị', player='em')), 'Cảm ơn em nha.')
        k = S.knobs_for('ba_tam', 'x')
        block = S.prompt_block('ba_tam', k, 'smalltalk', address=dict(self='cô', player='con'))
        self.assertIn('giữ xưng "cô"', block)


class Reply(unittest.TestCase):
    def call(self, reply, text='Hôm nay sao rồi?'):
        j = Journey('restaurant')
        with patch.dict(os.environ, ENV), patch('game.ai.chat', return_value=(reply, None)) as mock:
            out = ai.persona_reply(j.state, 'restaurant', j.task['npc'], text, canonical='Chào con.')
        return out, mock

    def test_prompt_follows_the_turn(self):
        _, mock = self.call('Ừ, bà nghe nè con.', text='bớt cho em chút đi bà')
        system = mock.call_args.args[0][0]['content']
        self.assertIn('Nhịp mẫu (mặc cả, chuyện giá', system)
        _, mock = self.call('Ừ, bà nghe nè con.', text='em buồn quá bà ơi')
        self.assertIn('người chơi buồn, mệt', mock.call_args.args[0][0]['content'])
        user = json.loads(mock.call_args.args[0][1]['content'])
        self.assertIn('spice', user['persona'])

    def test_unsafe_model_lines_fall_back(self):
        for bad, why in (('Con nhà quê ghê, bà nói thiệt.', 'unsafe'), ('Tao nói rồi, làm lẹ lên.', 'rude_pronoun'),
                         ('Tôi có thể giúp gì cho con?', 'assistant_tone')):
            out, _ = self.call(bad)
            self.assertEqual((out['mode'], out['reason'], out['text']), ('scripted', why, 'Chào con.'))

    def test_emoji_follow_the_archetype(self):
        out, _ = self.call('Ngon lắm con 😋😋😋 bà khen thiệt 👍')
        p = personas.persona(Journey('restaurant').state, 'restaurant', Journey('restaurant').task['npc'])
        self.assertEqual(out['mode'], 'ai')
        self.assertLessEqual(len(S.EMOJI.findall(out['text'])), p['spice']['knobs']['emoji'])


if __name__ == '__main__':
    unittest.main()
