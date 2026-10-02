"""Voices: every NPC talks in its own way (game/voices.py), the AI prompt uses the voice,
length follows verbosity, scripted chat has voice small talk, and reviews carry
off-topic gripes (game/review_gripes.py). No test talks to a real model."""
import collections
import json
import os
import re
import unittest
from unittest.mock import patch

from game import ai, engine, feedback as F, personas, review_gripes as RG, voices as V
from game.content import NPCS
from game.engine import validate_state
from tests.helpers import Journey

ENV = {'LLM_BASE_URL': 'http://localhost:9/v1', 'LLM_MODEL': 'mock', 'LLM_API_KEY': 'k'}
LONG = ('Ừ thì hôm nay trời nóng quá. Đầu hẻm có xe bánh mì mới mở. Mà thôi, chuyện đó để sau. '
        'Con làm cẩn thận giùm nha. Bà nói vậy thôi chứ bà thương lắm. Nhớ uống nước nữa. Vậy nha.')


def cast():
    out = {}
    for n in NPCS:
        age = personas._age(n, n['career_id'])
        temper = personas._temper(n['career_id'], n['id'], n, age)
        v = V.for_npc(n['id'], n.get('role', ''), age, temper, n['career_id'])
        out[n['id']] = (n, age, temper, v, V.verbosity_for(n['id'], v))
    return out


def npc_with(career, verbosity):
    for npc, (n, _, _, _, verb) in cast().items():
        if n['career_id'] == career and verb == verbosity:
            return npc
    raise unittest.SkipTest(f'no {verbosity} NPC in {career}')


class Library(unittest.TestCase):
    def test_many_complete_voices(self):
        self.assertGreaterEqual(len(V.VOICES), 30)
        for key in ('am_ap', 'lanh_lung', 'tsundere', 'nhieu_chuyen', 'camera', 'phan_xet', 'ban_phim', 'lay_loi', 'can_nhan',
                    'biet_tuot', 'nhut_nhat', 'drama', 'thuc_dung', 'song_ao', 'tam_linh', 'me_bim', 'bia_hoi', 'lac_quan',
                    'than_tho', 'da_nghi', 'ngay_tho', 'hoai_niem', 'genz', 'van_phong', 'tam_ly', 'thang_than', 'lich_su', 'huong_noi'):
            self.assertIn(key, V.VOICES)
        for vid, v in V.VOICES.items():
            for field in ('label', 'emoji', 'attitude', 'habits', 'topics', 'on_kind', 'on_rude', 'on_sad', 'idle', 'greet'):
                self.assertTrue(v[field], (vid, field))
            self.assertTrue(3 <= len(v['examples']) <= 5, vid)
            for line in v['examples'] + v['idle'] + v['greet'] + v['phrases']:
                self.assertNotRegex(line, r'\d', (vid, line))  # a copied digit would be rejected by the chat guard

    def test_limits(self):
        self.assertEqual((V.limits('kiem_loi')['sentences'], V.limits('kiem_loi')['chars']), (1, 60))
        self.assertEqual((V.limits('vua')['sentences'], V.limits('vua')['chars']), (3, 240))
        self.assertEqual((V.limits('noi_nhieu')['sentences'], V.limits('noi_nhieu')['chars']), (7, 600))
        self.assertLess(V.limits('kiem_loi')['max_tokens'], V.limits('vua')['max_tokens'])
        self.assertLess(V.limits('vua')['max_tokens'], V.limits('noi_nhieu')['max_tokens'])
        self.assertEqual(V.limits('nonsense'), V.limits('vua'))

    def test_mood_per_npc_per_day(self):
        self.assertEqual(V.mood_for('milk_tea_npc_01', 3), V.mood_for('milk_tea_npc_01', 3))
        self.assertGreater(len({V.mood_for('milk_tea_npc_01', d) for d in range(1, 30)}), 2)
        self.assertEqual(set(V.MOODS), {'vui', 'met', 'buc', 'buon', 'hao_hung'})


class Assignment(unittest.TestCase):
    def test_every_npc_gets_a_voice_that_fits(self):
        for npc, (n, age, temper, v, verb) in cast().items():
            self.assertIn(v['id'], V.VOICES, npc)
            self.assertIn(verb, V.VERBOSITY, npc)
            self.assertNotIn(v['id'], V.PRO, npc)             # interviewers only at the interview table
            if age == 'child':
                self.assertIn(v['id'], V.CHILD, npc)
            else:
                self.assertNotIn(v['id'], ('tre_con', 'tre_nghich'), npc)
            if n['career_id'] == 'teacher' and 'Phụ huynh' in n['role']:
                self.assertIn(v['id'], V.TEMPER[temper], npc)

    def test_distribution_is_spread(self):
        rows = cast().values()
        voices = collections.Counter(v['id'] for _, _, _, v, _ in rows)
        self.assertGreaterEqual(len(voices), 28)
        self.assertLessEqual(max(voices.values()) / len(NPCS), 0.1)
        verb = collections.Counter(x for *_, x in rows)
        share = {k: verb[k] / len(NPCS) for k in V.VERBOSITY}
        self.assertTrue(0.18 <= share['kiem_loi'] <= 0.32, share)
        self.assertTrue(0.38 <= share['vua'] <= 0.52, share)
        self.assertTrue(0.23 <= share['noi_nhieu'] <= 0.37, share)

    def test_people_of_one_workplace_sound_different(self):
        by = collections.defaultdict(list)
        for n, _, _, v, _ in cast().values():
            by[n['career_id']].append(v['id'])
        for career, ids in by.items():
            self.assertEqual(len(ids), len(set(ids)), career)

    def test_persona_card_carries_voice(self):
        j = Journey('restaurant')
        a = personas.persona(j.state, 'restaurant', 'restaurant_npc_06')
        self.assertEqual(a, personas.persona(j.state, 'restaurant', 'restaurant_npc_06'))
        for key in ('voice', 'voice_label', 'verbosity', 'mood', 'mood_why'):
            self.assertIn(key, a)
        self.assertEqual(a['address'], dict(self='bà', player='con'))  # unchanged by the voice

    def test_interviewers_stay_professional(self):
        for vid in V.VOICES:
            self.assertIn(V.professional(vid), V.PRO)
        card = dict(id='interviewer', name='Chị Mai', role='Trưởng ca', temperament='interviewer', style='thẳng, soi chi tiết', age='middle')
        self.assertEqual(V.for_card(card)['id'], 'pv_nghiem')
        self.assertEqual(V.for_card(dict(card, style='ít nói, cẩn thận'))['id'], 'pv_lanh')
        self.assertEqual(V.for_card(dict(card, style='hiền, xởi lởi'))['id'], 'pv_am')
        self.assertIn(V.for_card(dict(temperament='child', age='child', style='rất nhút nhát, nói nhỏ'))['id'], V.CHILD)


class Prompt(unittest.TestCase):
    def test_prompt_has_voice_examples_and_guardrails(self):
        j = Journey('restaurant')
        p = personas.persona(j.state, 'restaurant', 'restaurant_npc_06')
        system = ai._persona_system(p, 'chat', 'vi')
        v = V.VOICES[p['voice']]
        self.assertIn(v['label'], system)
        self.assertIn(v['examples'][0][:20], system)
        self.assertIn('Ví dụ giọng', system)
        self.assertIn('ĐỘ DÀI', system)
        for rule in ('không đáng tin', 'Không nhận mình là AI', 'con số', 'hoàn tiền', 'y tế', 'KHÔNG phải trợ lý'):
            self.assertIn(rule, system)
        self.assertIn(f'tối đa {V.limits(p["verbosity"])["sentences"]} câu', system)

    def test_camera_voice_is_innuendo_only(self):
        block = V.prompt_block('camera', 'noi_nhieu', 'buc', address=dict(self='cô', player='con'))
        self.assertIn('không con số', block)
        self.assertIn('không nói chuyện tình dục', block)
        self.assertIn('cô ngồi hóng mát', block)

    def test_old_cards_without_voice_still_work(self):
        card = dict(id='pupil:minh', name='Minh', role='Học sinh', age='child', age_label='trẻ nhỏ', temperament='child',
                    style='rất nhút nhát', personality='', address=dict(self='con', player='cô'), region='miền Nam', particles=['ạ'])
        system = ai._persona_system(card, 'class_question', 'vi')
        self.assertIn('Nhút nhát', system)
        self.assertIn('tối đa 3 câu', system)


class Reply(unittest.TestCase):
    def call(self, career, npc, reply, purpose='chat', canonical='Chào con.'):
        j = Journey(career)
        with patch.dict(os.environ, ENV), patch('game.ai.chat', return_value=(reply, None)) as mock:
            out = ai.persona_reply(j.state, career, npc, 'Hôm nay sao rồi?', canonical=canonical, purpose=purpose)
        return out, mock

    def test_terse_npc_is_trimmed(self):
        npc = npc_with('restaurant', 'kiem_loi')
        out, mock = self.call('restaurant', npc, LONG)
        self.assertEqual(out['mode'], 'ai')
        self.assertLessEqual(len(out['text']), 60)
        self.assertEqual(len(re.findall(r'[.!?…]+', out['text'])), 1)
        self.assertEqual(mock.call_args.kwargs['max_tokens'], V.limits('kiem_loi')['max_tokens'])

    def test_talkative_npc_keeps_more(self):
        npc = npc_with('restaurant', 'noi_nhieu')
        out, mock = self.call('restaurant', npc, LONG)
        self.assertEqual(out['mode'], 'ai')
        self.assertGreater(len(re.findall(r'[.!?…]+', out['text'])), 3)
        self.assertEqual(mock.call_args.kwargs['max_tokens'], V.limits('noi_nhieu')['max_tokens'])
        system = mock.call_args.args[0][0]['content']
        self.assertIn('NÓI NHIỀU', system)

    def test_interview_caps_length_and_goes_professional(self):
        npc = npc_with('restaurant', 'noi_nhieu')
        out, mock = self.call('restaurant', npc, LONG, purpose='interview')
        self.assertLessEqual(len(re.findall(r'[.!?…]+', out['text'])), 3)
        system = mock.call_args.args[0][0]['content']
        self.assertIn('Người phỏng vấn', system)
        self.assertNotIn('CHUYỆN PHỐ', system)

    def test_terse_npc_still_passes_facts(self):
        npc = npc_with('restaurant', 'kiem_loi')
        canonical = 'Cho mình 2 tô mì cay cấp độ nhẹ, một tô không hành, thêm trứng nhé.'
        out, _ = self.call('restaurant', npc, 'Hai tô mì cay nhẹ. Một tô không hành, thêm trứng. Vậy nha.', canonical=canonical)
        self.assertEqual(out['mode'], 'ai')
        self.assertIn('thêm trứng', out['text'])

    def test_guardrails_unchanged(self):
        npc = npc_with('restaurant', 'noi_nhieu')
        self.assertEqual(self.call('restaurant', npc, 'Bà cho con 999 nghìn nha.')[0]['reason'], 'new_numeric_claim')
        self.assertEqual(self.call('restaurant', npc, 'Là một mô hình ngôn ngữ, tôi không thể.')[0]['reason'], 'breaks_character')
        self.assertEqual(self.call('restaurant', npc, 'Bà đã hoàn tiền cho con rồi.')[0]['reason'], 'state_claim')

    def test_temperature_follows_voice(self):
        npc = npc_with('restaurant', 'noi_nhieu')
        _, mock = self.call('restaurant', npc, 'Ừ.')
        p = personas.persona(Journey('restaurant').state, 'restaurant', npc)
        self.assertEqual(mock.call_args.kwargs['temperature'], V.temperature(p['voice'], p['mood']))


class StreetTalk(unittest.TestCase):
    def test_gossips_spread_rumours_and_kind_people_comfort(self):
        j = Journey('milk_tea')
        post = engine.add_feed(j.state, j.c, 'milk_tea_npc_01', 'Tệ.', 'task-x', 1, 'review')
        post['day'] = j.c['day']
        gossip = V.street_talk(j.state, 'milk_tea', 'milk_tea_npc_02', 'camera', 1, dict(self='cô', player='con'))
        self.assertIn('rumour', gossip)
        self.assertNotRegex(gossip['rumour'], r'\d')
        kind = V.street_talk(j.state, 'milk_tea', 'milk_tea_npc_02', 'tam_ly', 1)
        self.assertIn('comfort', kind)
        child = V.street_talk(j.state, 'milk_tea', 'milk_tea_npc_02', 'tre_con', 1)
        self.assertFalse((child or {}).get('rumour'))


class ScriptedVariety(unittest.TestCase):
    def test_small_talk_differs_between_people(self):
        j = Journey('restaurant')
        lines = set()
        for n in [x for x in NPCS if x['career_id'] == 'restaurant']:
            lines.add(j.act('talk', npc=n['id'], text='ừ')['reply'])
            lines.add(j.act('talk', npc=n['id'], text='Chào bạn')['reply'])
        self.assertGreaterEqual(len(lines), 12)
        validate_state(j.state)

    def test_english_keeps_translated_line(self):
        j = Journey('restaurant')
        j.act('settings', lang='en')
        npc = next(x['id'] for x in NPCS if x['career_id'] == 'restaurant' and x['id'] != j.task['npc'])
        self.assertTrue(j.act('talk', npc=npc, text='ừ')['reply'].startswith('Hôm nay phố khá yên'))


# ---------------------------------------------------------------- review gripes
def fake_task(i, career='milk_tea', npc='milk_tea_npc_01'):
    return dict(id=f'task-{career}-{i}', career=career, npc=npc, mistakes=0, patience=100, known=True, title='Ly trà sữa')


class Gripes(unittest.TestCase):
    def roll(self, c, n=2500, npc='milk_tea_npc_01'):
        return [F.make_review({}, dict(c), fake_task(f'{c.get("day")}-{i}', npc=npc), 'completed') for i in range(n)]

    def test_frequency(self):
        for npc in ('milk_tea_npc_01', 'milk_tea_npc_02', 'milk_tea_npc_05'):
            made = self.roll(dict(day=15), npc=npc)
            share = sum(bool(m['feedback'].get('gripe')) for m in made) / len(made)
            self.assertTrue(0.15 <= share <= 0.25, (npc, share))
            dropped = [m for m in made if (m['feedback'].get('unfair') or {}).get('gripe')]
            self.assertTrue(dropped)
            for m in dropped:                       # a perfect job, one star lost to something off-topic
                self.assertEqual(m['stars'], m['feedback']['fair'] - 1)
                self.assertIn(RG.CLUE, m['feedback']['clues'])
                self.assertFalse(m['aside'])
            happy = [m for m in made if (m['feedback'].get('gripe') or {}).get('positive')]
            self.assertTrue(happy and all(m['stars'] == 5 for m in happy))

    def test_gripes_follow_real_state(self):
        busy = self.roll(dict(day=15, life=dict(mode='festival')), 1500)
        tied = collections.Counter(m['feedback']['gripe'].get('tied') for m in busy if m['feedback'].get('gripe'))
        self.assertGreater(tied['festival'] + tied['crowded'], 0)
        calm = self.roll(dict(day=15, life=dict(mode='normal')), 1500)
        self.assertFalse([m for m in calm if (m['feedback'].get('gripe') or {}).get('tied') in ('festival', 'crowded')])
        messy = self.roll(dict(day=15, ext=dict(data=dict(boba=dict(mess=4)))), 1500)
        self.assertTrue([m for m in messy if (m['feedback'].get('gripe') or {}).get('id') == 'dusty'])
        garden = self.roll(dict(day=15, ops=dict(property=dict(tier='garden'))), 1500)
        self.assertTrue([m for m in garden if (m['feedback'].get('gripe') or {}).get('id') == 'mosquito'])
        clean = self.roll(dict(day=15), 1500)
        self.assertFalse([m for m in clean if (m['feedback'].get('gripe') or {}).get('id') in ('dusty', 'mosquito')])

    def test_every_group_has_its_own_gripes(self):
        # The pagoda writes no side gripes at all (game/pagoda_voice.py), so it has none on purpose.
        for group in set(RG.GROUP.values()) - {'pagoda'}:
            neg = [g for g in RG.GRIPES.values() if group in g['groups'] and not g['pos']]
            pos = [g for g in RG.GRIPES.values() if group in g['groups'] and g['pos']]
            self.assertGreaterEqual(len(neg), 4, group)
            self.assertTrue(pos, group)
        self.assertFalse([g for g in RG.GRIPES.values() if 'teacher' in g['groups'] and 'shop' in g['groups']])

    def test_unfair_gripe_can_be_answered(self):
        j = Journey('milk_tea')
        j.c['day'] = 15
        t = next(t for t in (fake_task(f'ans-{i}') for i in range(5000))
                 if (F.make_review(j.state, j.c, t, 'completed')['feedback'].get('unfair') or {}).get('gripe'))
        made = F.make_review(j.state, j.c, t, 'completed')
        post = engine.add_feed(j.state, j.c, t['npc'], made['text'], t['id'], made['stars'], 'review')
        F.attach(post, made)
        validate_state(j.state)
        j.act('fb_reply', post=post['id'], text='Dạ theo phiếu ghi hôm đó món làm đúng yêu cầu ạ, tiệm cảm ơn góp ý.', offer='none')
        j.act('advance')
        j.act('advance')
        p = next(x for x in j.c['feed'] if x['id'] == post['id'])
        self.assertEqual(p['stars'], p['feedback']['fair'])
        self.assertNotIn('nhớ nhầm', p['feedback']['thread'][-1]['text'])

    def test_tone_reply_to_a_gripe(self):
        from game import feedback_voices as FV
        j = Journey('milk_tea')
        j.c['day'] = 8
        post = engine.add_feed(j.state, j.c, 'milk_tea_npc_01', 'Ngon, tiếc là con mèo nằm trên quầy.', 'task-g', 4, 'review')
        post['feedback'] = dict(persona='sour', criteria=[dict(key='accuracy', label='Đúng vị đã gọi', score=5, note='đúng trà, topping')],
                                cap=5, fair=5, stars_original=4, thread=[], status='open', rounds=0, pending=None, voice='scripted',
                                task='task-g', title='Ly trà sữa', value=0,
                                unfair=dict(key='gripe', label=RG.LABEL, claim='con mèo nằm trên quầy', truth='đúng trà', gripe='cat'),
                                gripe=dict(id='cat', form='backhanded', positive=False, dropped=True, tied=None))
        validate_state(j.state)
        d = FV.tone_decision(j.state, j.c, post, 'facts', 'none')
        self.assertEqual((d['decision'], d['stars']), ('revise_up', 5))
        self.assertIn(d['text'], RG.REPLY['gripe_soft'])

    def test_ai_review_voice_keeps_the_gripe(self):
        j = Journey('milk_tea')
        j.c['day'] = 15
        t = next(t for t in (fake_task(f'ai-{i}') for i in range(5000))
                 if (F.make_review(j.state, j.c, t, 'completed')['feedback'].get('gripe') or {}).get('form') not in (None, 'one_word'))
        made = F.make_review(j.state, j.c, t, 'completed')
        post = engine.add_feed(j.state, j.c, t['npc'], made['text'], t['id'], made['stars'], 'review')
        F.attach(post, made)
        with patch.dict(os.environ, ENV), patch('game.ai.chat', return_value=('Ngon thì ngon, mà thôi, chuyện kia tôi vẫn nhớ nha.', None)) as mock:
            out = ai.review_voice(j.c, post)
        self.assertTrue(out)
        system, user = mock.call_args.args[0][0]['content'], json.loads(mock.call_args.args[0][1]['content'])
        self.assertIn('gripe', user)
        self.assertIn('GIỌNG NHÂN VẬT', system)
        self.assertIn('BẮT BUỘC giữ đúng lý do', system)


if __name__ == '__main__':
    unittest.main()
