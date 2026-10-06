"""WP2 (06/10): reviews, moderation and safety without a database.

* Góp ý #196/#168: every review can be reported; off-topic, wrong-shop and pile-on reviews leave the average when
  reported (kept and marked), a report that is not accepted costs no star and brings no pile-on, and a pile-on never
  starts another one. Strangers who sign reviews come from the same trade; "nhầm quán" is rarer (#17).
* Chat C#15809 (#16): bù xu on a review that can never change is refused with a warning, before any xu leaves.
* Moderation #13: names go through the display-name rules on every rename, with an unaccented blocklist.
* Moderation #14 / #31: the chat's safety cue and @mentions of known players (live/filters.py).
"""
import json
import unittest

from game import accounts, engine, feedback as F
from game.engine import GameError, public_state, validate_state
from live import filters
from tests.helpers import Journey
from tests.test_feedback_reviews import fake_task, find, kind_of


def add(j, made, t):
    post = engine.add_feed(j.state, j.c, made.get('npc', t['npc']), made['text'], t['id'], made['stars'], 'review')
    F.attach(post, made)
    return post


def pub(j, pid):
    return next(x for x in public_state(j.state)['careers'][j.career]['feed'] if x['id'] == pid)


class Reviews(unittest.TestCase):
    def setUp(self):
        self.j = Journey('milk_tea')
        self.j.c['day'] = 15

    def post(self, kind):
        t = find(kind)
        return add(self.j, F.make_review(self.j.state, self.j.c, t, 'completed'), t)

    def test_every_twist_review_shows_a_report_button(self):
        for kind in ('offtopic', 'no_visit', 'wrong_shop', 'competitor', 'flip_low', 'bocphot', 'demand', 'mood', 'plain'):
            p = self.post(kind)
            self.assertTrue(pub(self.j, p['id'])['feedback']['can_report'], kind)

    def test_removable_kinds_leave_the_average_and_stay_listed(self):
        for kind in ('offtopic', 'wrong_shop', 'no_visit'):
            j = Journey('milk_tea')
            j.c['day'] = 15
            t = find(kind)
            p = add(j, F.make_review(j.state, j.c, t, 'completed'), t)
            stars = p['stars']
            r = j.act('fb_report', post=p['id'])
            self.assertEqual(r['report'], 'accepted', kind)
            p = next(x for x in j.c['feed'] if x['id'] == p['id'])
            self.assertIsNone(p['stars'])
            self.assertEqual(p['feedback']['removed_stars'], stars)
            self.assertTrue(pub(j, p['id'])['feedback']['removed'])
            validate_state(j.state)

    def test_old_saves_with_reportable_false_are_removable_now(self):
        p = self.post('offtopic')
        p['feedback']['twist']['reportable'] = False          # as stored before WP2
        validate_state(self.j.state)
        self.assertEqual(self.j.act('fb_report', post=p['id'])['report'], 'accepted')

    def test_pile_on_never_cascades_and_can_be_removed(self):
        p = self.post('plain')
        n = len(self.j.c['feed'])
        self.j.act('fb_reply', post=p['id'], text='Không thích thì đi chỗ khác, tiệm không tiếp loại khách như bạn.', offer='none')
        piles = self.j.c['feed'][:len(self.j.c['feed']) - n]
        self.assertTrue(piles and all(F._kind(x['feedback']) == 'pile_on' for x in piles))
        pile = piles[0]
        m = len(self.j.c['feed'])
        r = self.j.act('fb_reply', post=pile['id'], text='Đồ ngu.', offer='none')   # rude to a pile-on: no new pile-on
        self.assertNotIn('viral', r)
        self.assertEqual(len(self.j.c['feed']), m)
        self.j.act('advance')
        self.j.act('advance')
        self.assertEqual(self.j.act('fb_report', post=piles[-1]['id'])['report'], 'accepted')
        self.assertEqual(len(self.j.c['feed']), m)
        validate_state(self.j.state)

    def test_rejected_report_at_one_star_adds_nothing(self):
        t = find('flip_low')                   # praise tapped as 1★: a real visit, not removable
        p = add(self.j, F.make_review(self.j.state, self.j.c, t, 'completed'), t)
        self.assertEqual(p['stars'], 1)
        self.assertFalse(F.removable(p))
        n = len(self.j.c['feed'])
        r = self.j.act('fb_report', post=p['id'])
        self.assertEqual(r['report'], 'rejected')
        self.assertEqual(len(self.j.c['feed']), n)
        self.assertEqual(next(x for x in self.j.c['feed'] if x['id'] == p['id'])['stars'], 1)
        self.assertNotIn('1★', r['message'])

    def test_off_topic_gripe_that_took_a_star_is_removable(self):
        for i in range(4000):
            t = fake_task(f'g-{i}')
            made = F.make_review(self.j.state, self.j.c, t, 'completed')
            g = made['feedback'].get('gripe')
            if g and g['dropped'] and not g['positive'] and made['feedback'].get('unfair'):
                break
        else:
            self.fail('no gripe rolled')
        p = add(self.j, made, t)
        self.assertTrue(F.removable(p))
        self.assertEqual(self.j.act('fb_report', post=p['id'])['report'], 'accepted')

    def test_plain_event_review_is_reportable_and_kept(self):
        p = engine.add_feed(self.j.state, self.j.c, 'milk_tea_npc_02', 'Mới trưa đã hết trân châu, buồn ghê 💔', 'ev-1', 3, 'review')
        view = pub(self.j, p['id'])
        self.assertTrue(view['can_report'])
        self.assertNotIn('feedback', view)
        r = self.j.act('fb_report', post=p['id'])
        self.assertEqual(r['report'], 'rejected')
        p = next(x for x in self.j.c['feed'] if x['id'] == p['id'])
        self.assertEqual((p['stars'], p['reported']), (3, 15))
        self.assertNotIn('report', p)                # consequences.py's own flag stays untouched
        self.assertFalse(pub(self.j, p['id'])['can_report'])
        with self.assertRaises(GameError):
            self.j.act('fb_report', post=p['id'])
        validate_state(self.j.state)
        p['reported'] = 'x'
        with self.assertRaises(GameError):
            validate_state(self.j.state)

    def test_report_limit_counts_plain_reviews_too(self):
        for i in range(F.REPORTS_PER_DAY):
            p = engine.add_feed(self.j.state, self.j.c, 'milk_tea_npc_02', f'Ổn {i}', f'ev-{i}', 3, 'review')
            self.j.act('fb_report', post=p['id'])
        q = self.post('wrong_shop')
        with self.assertRaises(GameError):
            self.j.act('fb_report', post=q['id'])

    def test_refund_on_a_never_changing_review_warns_and_keeps_the_xu(self):
        for kind in ('no_visit', 'wrong_shop'):
            p = self.post(kind)
            before = json.dumps(self.j.state, sort_keys=True, ensure_ascii=False)
            with self.assertRaises(GameError) as e:
                self.j.act('fb_reply', post=p['id'], text='Xin lỗi bạn ạ, tiệm hoàn tiền nhé.', offer='refund')
            self.assertEqual(e.exception.code, 'offer_useless')
            self.assertIn('Chưa trừ xu nào', e.exception.message)
            self.assertEqual(json.dumps(self.j.state, sort_keys=True, ensure_ascii=False), before)
            self.assertIn('Báo cáo', pub(self.j, p['id'])['feedback']['offer_note'])
        real = self.post('plain')
        self.assertNotIn('offer_note', pub(self.j, real['id'])['feedback'])

    def test_strangers_come_from_the_same_trade_and_wrong_shop_is_rarer(self):
        self.assertEqual(dict(F.TWIST_WEIGHTS['customer'])['wrong_shop'], 1)
        for kind in ('offtopic', 'no_visit', 'competitor', 'wrong_shop'):
            made = F.make_review({}, dict(day=15), find(kind), 'completed')
            self.assertTrue(made['npc'].startswith('milk_tea_npc_'), (kind, made['npc']))
        late = [kind_of(F.make_review({}, dict(day=15), fake_task(f'w-{i}'), 'completed')) for i in range(3000)]
        self.assertLess(late.count('wrong_shop'), late.count('no_visit'))


class Names(unittest.TestCase):
    BAD = ('concac', 'con cặc lớn', 'Sục cháy chim', 'dcm', 'DCM vl', 'c.ặ.c', 'c4c', 'Con Kac', 'ConCacc', 'lồn', 'ditme ban', 'Concak123')
    GOOD = ('Các Bạn', 'Bác Cả', 'Buổi Sáng', 'Súc Sắc', 'Ngọc Lan', 'Mây', 'Đức Anh', 'Lớn', 'Dai', 'Cúc', 'Ca Cao', 'Lucas',
            'Tiểu Trà Trà', 'Bí Ve', 'em gạo', 'Cô Cả', 'Yuika', 'MinhQuan', 'Kir', 'Hải Đăng')

    def test_blocklist(self):
        for n in self.BAD:
            self.assertTrue(accounts.offensive_name(n), n)
        for n in self.GOOD:
            self.assertFalse(accounts.offensive_name(n), n)

    def test_display_cleaner_refuses(self):
        for n in self.BAD:
            with self.assertRaises(accounts.AccountError):
                accounts.clean_display(n)
        self.assertEqual(accounts.clean_display('Bí Ve'), 'Bí Ve')

    def test_both_rename_paths_use_the_rules(self):
        j = Journey('milk_tea')
        for n in ('concac', 'Sục cháy chim', 'abc.com'):
            with self.assertRaises(GameError):
                j.act('settings', name=n)
            with self.assertRaises(GameError):
                j.act('jr_profile', name=n)
        j.act('settings', name='Ngọc Lan')
        self.assertEqual(j.state['name'], 'Ngọc Lan')
        j.act('jr_profile', name='Bí Ve')
        self.assertEqual(j.state['name'], 'Bí Ve')

    def test_an_older_name_never_blocks_other_settings(self):
        j = Journey('milk_tea')
        j.state['name'] = 'Mây 🌸'                    # allowed before; not renamed automatically
        j.act('settings', name='Mây 🌸')
        j.act('jr_profile', name='Mây 🌸', gender='female')
        self.assertEqual(j.state['name'], 'Mây 🌸')


class ChatFilters(unittest.TestCase):
    def test_safety_cues(self):
        for text in ('hẹn gặp ở Hồ Tây nha', 'cuối tuần đi chơi ngoài đời không', 'anh chở em đi ăn nhé', 'nhà bạn ở đâu',
                     'nhà mình ở quận 7', 'cho xin địa chỉ', 'số điện thoại của em là gì', 'add zalo t nha', 'ib fb đi',
                     'follow ig mình', 'tiktok của t nè', 'em mấy tuổi', 'học trường nào vậy', 'gọi 0912345678 nhé', '@mylinh.2010'):
            self.assertTrue(filters.safety_cue(text), text)
        for text in ('chào cả phố', 'hôm nay bán được 20 ly', 'đi chợ mua trân châu', 'quầy ở cuối phố', 'giá 100.000 xu', 'vl thật'):
            self.assertFalse(filters.safety_cue(text), text)

    def test_known_names_can_be_mentioned(self):
        known = filters.mention_keys(['LeeSerin', 'Mây Hồng', 'Kir'])
        self.assertEqual(filters.mask('@LeeSerin ơi', known), '@LeeSerin ơi')
        self.assertEqual(filters.mask('@MâyHồng', known), '@MâyHồng')
        self.assertEqual(filters.mask('@stranger_99 add nha', known), '••• add nha')
        self.assertEqual(filters.mask('@LeeSerin ơi'), '••• ơi')   # no list: as before


if __name__ == '__main__':
    unittest.main()
