"""Chùa Gió Lành answers in its own voice (game/pagoda_voice.py): visitors' impressions, the young monk's replies,
the visitor's answer, bystanders and the pile-on never read like a shop ("ủng hộ quán", "dịch vụ", "5 sao"…), the
pagoda is never "mới mở", the AI voice is told where it is; other careers are untouched; old saves still load."""
import json
import re
import unittest
from unittest import mock

from tests.helpers import Journey
from game import ai
from game import consequences as cq
from game import engine as E
from game import feedback as F
from game import feedback_voices as FV
from game import lb_titles as LBT
from game import pagoda_voice as PV
from game import tip_content as TC
from game.careers import PLUGINS
from game.engine import public_state, validate_state

PG = PLUGINS.get('pagoda')
# What the owner listed, plus the shop words the old path used.
SHOP = re.compile(r'(?<!\w)(ủng hộ|shop|quán|tiệm|dịch vụ|giá|khuyến mãi|5 sao|năm sao|quay lại mua|voucher|hoàn tiền|chủ quán|'
                  r'khách hàng|cửa hàng|mới mở|khai trương|phục vụ|rep)(?!\w)', re.I)


def clean(test, text, where=''):
    test.assertIsNone(SHOP.search(text or ''), f'{where}: {text}')


class Base(unittest.TestCase):
    def setUp(self):
        if PG is None:
            raise unittest.SkipTest('pagoda is filtered out by MNL_CAREERS')
        self.j = Journey('pagoda')

    def reviews(self, days=range(1, 16), slots=range(1, 25)):
        """(task, review) for many pagoda jobs: careful, slow, with a slip, on every kind of day."""
        s, c = self.j.state, self.j.c
        for day in days:
            c['day'] = day
            for slot in slots:
                t = PG.make_task(day, slot, 1)
                t.update(status='completed', day=day, mistakes=int(slot % 5 == 0), patience=100 - (slot * 7) % 70)
                if slot % 5 == 0:
                    cq.slip(t, 'mn:loud', 2, 'Nhắc khách hơi to giữa chánh điện.')
                yield t, F.make_review(s, c, t, 'completed')

    def post(self, review, t, n=[0]):
        n[0] += 1
        p = E.add_feed(self.j.state, self.j.c, t['npc'], review['text'], t['id'], review['stars'], 'review')
        F.attach(p, review)
        return p


class VisitorsWrite(Base):
    def test_no_shop_words_in_any_first_review(self):
        seen = 0
        kinds = set()
        for t, r in self.reviews():
            clean(self, r['text'], t['id'])
            for x in r['feedback'].get('clues') or []:
                clean(self, x, 'clue')
            kinds.add((r['feedback'].get('twist') or {}).get('kind'))
            F.validate_post(dict(r, feedback=r['feedback']))
            seen += 1
        self.assertGreater(seen, 300)
        # The pagoda only ever gets careless reviews that make sense there.
        self.assertTrue(kinds - {None})
        self.assertLessEqual(kinds - {None}, {'offtopic', 'flip_low', 'flip_high', 'no_visit'})

    def test_reviews_speak_of_the_pagoda(self):
        texts = [r['text'] for _, r in self.reviews(days=(2, 5, 9), slots=range(1, 13))]
        joined = ' '.join(texts)
        self.assertIn('chùa', joined)
        self.assertTrue(any(w in joined for w in ('Sân chùa', 'chánh điện', 'Bàn Phật', 'chuông', 'công đức')))
        self.assertFalse(any('mới mở' in x or 'khai trương' in x for x in texts))

    def test_the_pagoda_is_never_new(self):
        for rows in (PV.OPEN.values(), [x for v in PV.CLOSE.values() for x in v], PV.LIFESTORY, PV.SHORT):
            for x in rows:
                for line in (x if isinstance(x, list) else [x]):
                    self.assertNotIn('mới mở', line)
                    self.assertNotIn('khai trương', line)

    def test_same_inputs_same_review(self):
        a = [r['text'] for _, r in self.reviews(days=(4,), slots=range(1, 9))]
        b = [r['text'] for _, r in self.reviews(days=(4,), slots=range(1, 9))]
        self.assertEqual(a, b)


class PlayerAnswers(Base):
    def test_tone_choices_are_humble_and_never_commercial(self):
        labels = set()
        for t, r in self.reviews(days=(3, 8), slots=range(1, 15)):
            p = self.post(r, t)
            pub = F.public_post(p, 'pagoda')
            tones = pub['feedback'].get('tones') or []
            self.assertEqual([x['id'] for x in tones], list(FV.TONE_ORDER))
            for x in tones:
                labels.add(x['label'])
                clean(self, x['text'], x['id'])
                clean(self, x['label'], x['id'])
                if x['id'] not in ('harsh', 'genz', 'sassy', 'funny'):
                    self.assertTrue(any(w in x['text'] for w in ('chùa', 'Chùa', 'A Di Đà Phật', 'ghi nhận', 'Cảm ơn')), x['text'])
        self.assertIn('Mời ghé lễ', labels)
        self.assertNotIn('Mời quay lại', labels)

    def test_every_reply_line_in_the_tables_is_clean(self):
        for table in (PV.TONES, PV.TONES_POS):
            for tid, rows in table.items():
                self.assertIn(tid, FV.TONES)
                for x in rows:
                    clean(self, x, tid)
        for rows in list(PV.REACT.values()) + list(PV.GUEST_TEXT.values()) + list(PV.PILE_ON.values()):
            for x in rows:
                clean(self, x)
        for x in PV.FAN_TEXT + PV.REPORT_ANGRY + [PV.FANS_NOTE, PV.VIRAL, PV.SASS_LOST, PV.REMEMBER, PV.PILE_LABEL]:
            clean(self, x)
        # No luck or blessings in exchange for money anywhere in the pagoda's words.
        allx = json.dumps([PV.TONES, PV.TONES_POS, PV.REACT, PV.OPEN, PV.GOOD], ensure_ascii=False)
        for w in ('tài lộc', 'phát tài', 'cầu được ước thấy', 'giải hạn'):
            self.assertNotIn(w, allx)

    def test_the_whole_thread_through_the_game(self):
        j = self.j
        posts = []
        for t, r in self.reviews(days=(5, 7), slots=range(1, 12)):
            if r['stars'] and r['feedback']['status'] == 'open':
                posts.append(self.post(r, t)['id'])
        tones = list(FV.TONE_ORDER)
        lines = []
        for i, pid in enumerate(posts[:18]):
            pub = next(p for p in public_state(j.state)['careers']['pagoda']['feed'] if p['id'] == pid)
            tone = pub['feedback']['tones'][i % len(tones)]
            out = j.act('fb_reply', post=pid, text=tone['text'], offer='none', tone=tone['id'])
            lines.append(out['message'])
            for _ in range(3):
                out = j.act('advance')
                lines += [x for x in out.get('effects', []) if isinstance(x, str)]
        validate_state(j.state)
        for p in j.c['feed']:
            if p.get('kind') != 'review':
                continue
            clean(self, p['text'], p['id'])
            for row in p['feedback']['thread']:
                if row['role'] != 'owner':
                    clean(self, row['text'], row['role'])
        replied = [p for p in j.c['feed'] if p['id'] in posts and any(x['role'] == 'customer' for x in p['feedback']['thread'])]
        self.assertTrue(replied)
        for x in lines:
            clean(self, x, 'message')

    def test_free_text_reply_gets_a_pagoda_answer(self):
        t, r = next((t, r) for t, r in self.reviews(days=(6,)) if r['stars'] <= 4 and not r['feedback'].get('twist'))
        p = self.post(r, t)
        self.j.act('fb_reply', post=p['id'], text='A Di Đà Phật, chùa xin lỗi bác, lần sau chùa sẽ chú ý hơn ạ.', offer='none')
        self.j.act('advance'), self.j.act('advance'), self.j.act('advance')
        p = next(x for x in self.j.c['feed'] if x['id'] == p['id'])
        answer = [x for x in p['feedback']['thread'] if x['role'] == 'customer']
        self.assertTrue(answer)
        texts = [x for rows in PV.REACT.values() for x in rows]
        self.assertTrue(any(PV.fill(x, owner='thầy', note='')[:12] == answer[0]['text'][:12] for x in texts), answer[0]['text'])

    def test_rude_reply_pile_on_in_pagoda_words(self):
        t, r = next((t, r) for t, r in self.reviews(days=(6,)) if r['stars'])
        p = self.post(r, t)
        out = self.j.act('fb_reply', post=p['id'], text='Không vừa ý thì bác đi chùa khác, ở đây không cần.', offer='none', tone='harsh')
        self.assertIn('cảm nhận 1★', out['message'])
        piles = [x for x in self.j.c['feed'] if (x.get('feedback') or {}).get('twist', {}).get('kind') == 'pile_on']
        self.assertTrue(piles)
        for x in piles:
            self.assertIn(x['text'], PV.PILE_ON['customer'])
            self.assertEqual(x['feedback']['criteria'][0]['label'], PV.PILE_LABEL)


    def test_ignore_and_report_messages(self):
        rs = [(t, r) for t, r in self.reviews(days=(6, 7)) if r['stars']]
        msgs = []
        for t, r in rs[:4]:
            p = self.post(r, t)
            msgs.append(self.j.act('fb_ignore', post=p['id'])['message'])
        for t, r in rs[4:6]:
            p = self.post(r, t)
            msgs.append(self.j.act('fb_report', post=p['id'])['message'])
            p = next(x for x in self.j.c['feed'] if x['id'] == p['id'])
            for row in p['feedback']['thread']:
                clean(self, row['text'], 'report')
        self.assertIn(PV.IGNORED, msgs)
        for x in msgs:
            clean(self, x, 'message')
        validate_state(self.j.state)


class Elsewhere(Base):
    def test_other_careers_keep_their_voice(self):
        j = Journey('milk_tea')
        post = dict(id='post-x', npc=j.task['npc'], author='A', text='Ngon.', day=1, stars=3, kind='review',
                    feedback=dict(persona='warm', criteria=[dict(key='speed', label='Tốc độ', score=3, note='chờ hơi lâu')], cap=5, fair=3,
                                  stars_original=3, unfair=None, thread=[], status='open', rounds=0, pending=None, voice='scripted',
                                  task='t', title='Ly trà', value=0))
        tones = F.public_post(post, 'milk_tea')['feedback']['tones']
        self.assertEqual(tones[0]['label'], 'Ấm áp')
        self.assertEqual(tones[5]['label'], 'Mời quay lại')
        self.assertEqual(F.public_post(post)['feedback']['tones'], tones)
        self.assertEqual(LBT.title_of('milk_tea', 1)['text'], '🏆 Trùm trà sữa')

    def test_weekly_title_and_tips(self):
        self.assertEqual(LBT.title_of('pagoda', 1)['text'], '🪷 Siêng việc chùa nhất tuần')
        self.assertNotIn('Trùm', LBT.tiers_of('pagoda')[0]['name'])
        for x in TC.CAREER_GIFT_LINES['pagoda'] + TC.CAREER_WELCOME['pagoda']:
            clean(self, x)
        self.assertEqual(PG.SPEC['open_line'][:14], 'Cổng chùa đã m')

    def test_a_shop_voiced_review_in_an_old_save_still_loads(self):
        """Reviews written before this change (shop words, a 'drama' visitor, a teencode style) stay as they are."""
        j = self.j
        p = E.add_feed(j.state, j.c, 'pagoda_npc_02', 'Ủng hộ quán mới mở nha!', 'old', 3, 'review')
        p['feedback'] = dict(persona='drama', criteria=[dict(key='craft', label='Làm việc chu đáo', score=3, note='còn sơ suất')], cap=5,
                             fair=3, stars_original=3, unfair=None, thread=[dict(role='owner', text='Dạ tiệm cảm ơn ạ', day=1, offer='refund')],
                             status='open', rounds=1, pending=None, voice='scripted', task='old', title='Quét sân', value=0,
                             style='teencode', twist=dict(kind='bocphot', reportable=False), clues=['Dọa bóc phốt, đòi đền'])
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        pub = public_state(s)['careers']['pagoda']
        old = next(x for x in pub['feed'] if x['id'] == p['id'])
        self.assertEqual(old['text'], 'Ủng hộ quán mới mở nha!')
        self.assertEqual(len(old['feedback']['tones']), len(FV.TONE_ORDER))
        out = j.act('fb_reply', post=p['id'], text='A Di Đà Phật, chùa xin ghi nhận ạ.', offer='none', tone='warm')
        self.assertTrue(out['message'])
        validate_state(j.state)


class AIVoice(Base):
    def awaiting(self):
        t, r = next((t, r) for t, r in self.reviews(days=(6,)) if r['stars'] and not r['feedback'].get('twist'))
        p = self.post(r, t)
        p['feedback']['status'] = 'awaiting'
        p['feedback']['pending'] = dict(decision='keep', stars=p['stars'], text='Vâng.', turn=0)
        return p

    def test_prompt_knows_it_is_a_pagoda_and_shop_words_are_dropped(self):
        p = self.awaiting()
        seen = {}

        def fake(msgs, **kw):
            seen['msgs'] = msgs
            return json.dumps(dict(decision='revise_up', stars=p['stars'], text='Cảm ơn thầy, ủng hộ quán dài dài nha!'), ensure_ascii=False), None
        with mock.patch.object(ai, 'chat', fake):
            self.assertIsNone(ai.feedback_decision(self.j.c, p, 'vi', 'pagoda'))
        system = seen['msgs'][0]['content']
        self.assertIn('chùa Gió Lành là ngôi chùa lâu năm', system)
        self.assertEqual(json.loads(seen['msgs'][1]['content'])['context']['role'], PV.AI_ROLE)
        good = json.dumps(dict(decision='revise_up', stars=p['stars'], text='Cảm ơn thầy, rằm tới tôi lại lên chùa.'), ensure_ascii=False)
        with mock.patch.object(ai, 'chat', lambda msgs, **kw: (good, None)):
            self.assertTrue(ai.feedback_decision(self.j.c, p, 'vi', 'pagoda'))

    def test_rewrite_in_shop_words_is_dropped(self):
        t, r = next((t, r) for t, r in self.reviews(days=(6,)) if r['stars'] and not r['feedback'].get('twist') and not r['feedback'].get('style'))
        p = self.post(r, t)
        with mock.patch.object(ai, 'chat', lambda msgs, **kw: ('Dịch vụ ở đây tốt, sẽ ủng hộ dài dài.', None)):
            self.assertIsNone(ai.review_voice(self.j.c, p, 'vi', 'pagoda'))
        with mock.patch.object(ai, 'chat', lambda msgs, **kw: ('Sân chùa sạch, thầy chỉ đường nhẹ nhàng, lòng thấy yên.', None)):
            self.assertTrue(ai.review_voice(self.j.c, p, 'vi', 'pagoda'))


if __name__ == '__main__':
    unittest.main()
