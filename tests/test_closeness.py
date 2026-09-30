"""Điểm thân quen (game/closeness.py): score, tiers, gains and losses, caps, decay, gifts both ways,
helpers for other systems, and saves."""
import copy
import unittest

from game import closeness as qn
from game.engine import GameError, add_feed, apply_action, migrate_state, new_state, public_state, validate_state
from tests.helpers import Journey


def fresh(career='mother_baby'):
    j = Journey(career)
    return j


def bump_day(j, n=1):
    """Outside the story every closed workday is a closeness day: move the workplace calendar."""
    j.c['day'] += n
    res = dict(effects=[])
    qn.after(j.state, j.career, 'advance', {}, res)
    validate_state(j.state)
    return res


def set_score(s, pid, v):
    qn._set(s, pid, v)


def gift_rows(c, cat):
    return [r for r in c['ops']['finance']['ledger'] if r['category'] == cat]


class TierTests(unittest.TestCase):
    def test_thresholds(self):
        for score, t in ((0, 1), (19, 1), (20, 2), (39, 2), (40, 3), (59, 3), (60, 4), (79, 4), (80, 5), (100, 5)):
            self.assertEqual(qn.tier_of(score), t, score)
        self.assertEqual([qn.tier_name(t) for t in range(1, 6)],
                         ['Người lạ', 'Quen mặt', 'Người quen', 'Thân thiết', 'Như người nhà'])

    def test_helper_ranges(self):
        j = fresh()
        s = j.state
        ids = ['ba_tam', 'be_ti', 'mother_baby_npc_01', 'grocery_npc_01', 'nobody', None, 42]
        for v in (0, 25, 50, 70, 100):
            set_score(s, 'ba_tam', v)
            set_score(s, 'mother_baby_npc_01', v)
            for pid in ids:
                c = qn.closeness(s, pid)
                self.assertTrue(0 <= c <= 100)
                self.assertIn(qn.tier(s, pid), range(1, 6))
                self.assertTrue(1.0 <= qn.closeness_bonus(s, pid) <= 1.6)
                self.assertIn(qn.forgiveness(s, pid), (0, 1))
                w = qn.wedding(s, pid)
                self.assertTrue(0 <= w['attend'] <= 100 and w['gift_mult'] > 0)
        self.assertEqual(qn.closeness(s, 'nobody'), 0)
        c = s['careers']['mother_baby']
        c['relationships']['mother_baby_npc_05'] = 59
        self.assertEqual(qn.forgives(c, 'mother_baby_npc_05'), 0)
        c['relationships']['mother_baby_npc_05'] = 60
        self.assertEqual(qn.forgives(c, 'mother_baby_npc_05'), 1)
        self.assertEqual(qn.forgives(c, 'nobody'), 0)
        bonus = [qn.TIP_BONUS[t] for t in range(1, 6)]
        self.assertEqual(bonus, sorted(bonus))
        attend = [qn.WEDDING[t][0] for t in range(1, 6)]
        self.assertEqual(attend, sorted(attend))

    def test_scores_reuse_existing_bonds(self):
        j = fresh()
        s = j.state
        self.assertEqual(qn.closeness(s, 'ba_tam'), s['journey']['life']['bonds']['ba_tam'])
        s['careers']['mother_baby']['relationships']['mother_baby_npc_02'] = 33
        self.assertEqual(qn.closeness(s, 'mother_baby_npc_02'), 33)
        # Cô Ba at the tạp hóa is the neighbour Cô Ba: one score.
        set_score(s, 'co_ba', 71)
        self.assertEqual(qn.closeness(s, 'grocery_npc_01'), 71)
        self.assertEqual(qn.tier(s, 'grocery_npc_01'), 4)


class ChatTests(unittest.TestCase):
    def test_first_chat_of_the_day_only(self):
        j = fresh()
        before = qn.closeness(j.state, 'ba_tam')
        r = j.act('qn_chat', who='ba_tam')
        gain = qn.closeness(j.state, 'ba_tam') - before
        self.assertIn(gain, (1, 2, 3))
        self.assertTrue(r['message'].startswith('Bà Tám: “'))
        mid = qn.closeness(j.state, 'ba_tam')
        j.act('qn_chat', who='ba_tam')
        self.assertEqual(qn.closeness(j.state, 'ba_tam'), mid)       # daily cap
        bump_day(j)
        j.act('qn_chat', who='ba_tam')
        self.assertGreater(qn.closeness(j.state, 'ba_tam'), mid)

    def test_talk_in_the_chat_sheet_counts_once_and_rude_words_cost(self):
        j = fresh()
        npc = 'mother_baby_npc_03'
        j.act('talk', npc=npc, text='Chào bạn')
        a = qn.closeness(j.state, npc)
        self.assertIn(a, (1, 2, 3))
        j.act('talk', npc=npc, text='Hôm nay thế nào?')
        self.assertEqual(qn.closeness(j.state, npc), a)
        bump_day(j)
        set_score(j.state, npc, 30)
        j.act('talk', npc=npc, text='đồ ngu như bò, cút đi')
        self.assertEqual(qn.closeness(j.state, npc), 27)
        j.act('talk', npc=npc, text='đồ ngu như bò')
        self.assertEqual(qn.closeness(j.state, npc), 27)             # one rude hit a day

    def test_strangers_cannot_be_messaged(self):
        j = fresh()
        with self.assertRaises(GameError):
            j.act('qn_chat', who='salon_npc_05')
        with self.assertRaises(GameError):
            j.act('qn_chat', who='nobody')


class GiftTests(unittest.TestCase):
    def test_liked_neutral_disliked(self):
        j = fresh()
        s = j.state
        like = qn.taste('ba_tam')
        self.assertEqual(like['likes'], ['betel', 'sweet'])
        set_score(s, 'ba_tam', 50)
        money = j.c['money']
        r = j.act('qn_gift', who='ba_tam', gift='trau', src='buy')
        self.assertEqual(r['how'], 'liked')
        self.assertEqual(qn.closeness(j.state, 'ba_tam'), 56)
        self.assertEqual(j.c['money'], money - 5)
        self.assertEqual(gift_rows(j.c, 'gift_out')[-1]['amount'], -5)
        self.assertIn('betel', j.state['journey']['closeness']['people']['ba_tam']['rv'])
        with self.assertRaises(GameError):                               # one gift a day each
            j.act('qn_gift', who='ba_tam', gift='che', src='buy')
        bump_day(j)
        r = j.act('qn_gift', who='ba_tam', gift='bia', src='buy')
        self.assertEqual(r['how'], 'disliked')
        self.assertEqual(qn.closeness(j.state, 'ba_tam'), 54)
        bump_day(j)
        r = j.act('qn_gift', who='ba_tam', gift='tra', src='buy')       # neutral, 10 xu: +3 +1
        self.assertEqual(r['how'], 'neutral')
        self.assertEqual(qn.closeness(j.state, 'ba_tam'), 58)

    def test_effect_table(self):
        self.assertEqual(qn.gift_effect('be_ti', qn.GIFTS['snack']), ('liked', 6))
        self.assertEqual(qn.gift_effect('co_lua', qn.GIFTS['bia']), ('disliked', -2))
        self.assertEqual(qn.gift_effect('co_lua', qn.GIFTS['trai_cay']), ('neutral', 3))
        self.assertEqual(qn.gift_effect('ba_tam', qn.GIFTS['phong_bi']), ('cash', 3))
        # Customers get seeded tastes, always the same.
        a, b = qn.taste('salon_npc_03'), qn.taste('salon_npc_03')
        self.assertEqual(a, b)
        self.assertEqual(len(a['likes']), 2)
        self.assertNotIn(a['dislikes'][0], a['likes'])

    def test_kids_and_bag(self):
        j = fresh()
        with self.assertRaises(GameError):
            j.act('qn_gift', who='be_ti', gift='bia', src='buy')
        st = j.state['journey']['closeness']
        st['bag']['banh_bo'] = 1
        money = j.c['money']
        r = j.act('qn_gift', who='be_ti', gift='banh_bo', src='bag')
        self.assertEqual(r['how'], 'neutral')
        self.assertEqual(j.c['money'], money)
        self.assertNotIn('banh_bo', j.state['journey']['closeness']['bag'])
        with self.assertRaises(GameError):
            j.act('qn_gift', who='co_ba', gift='banh_bo', src='bag')

    def test_not_enough_money(self):
        j = fresh()
        from game.engine import money
        money(j.state, j.c, 2 - j.c['money'], 'Chi tiêu khác')
        validate_state(j.state)
        with self.assertRaises(GameError):
            j.act('qn_gift', who='ba_tam', gift='trau', src='buy')


class WorkTests(unittest.TestCase):
    def _review(self, j, npc, stars, slips=()):
        t = j.task
        t['slips'] = [dict(code=c, sev=1, text='x', note='', safety=False) for c in slips]
        post = add_feed(j.state, j.c, npc, 'Đánh giá', t['id'], stars, 'review')
        res = dict(effects=[])
        qn.after(j.state, j.career, 'advance', {}, res)
        return post, res

    def test_stars_move_the_score_once(self):
        j = fresh()
        npc = 'mother_baby_npc_02'
        set_score(j.state, npc, 40)
        self._review(j, npc, 5)
        self.assertEqual(qn.closeness(j.state, npc), 42)
        qn.after(j.state, j.career, 'advance', {}, dict(effects=[]))
        self.assertEqual(qn.closeness(j.state, npc), 42)                 # never twice
        self._review(j, npc, 1)
        self.assertEqual(qn.closeness(j.state, npc), 37)
        self._review(j, npc, 3, slips=('change_short',))
        self.assertEqual(qn.closeness(j.state, npc), 33)                 # −1 and −3 short-changed

    def test_a_real_job_counts(self):
        j = fresh()
        npc = j.task['npc']
        j.solve()
        post = next(p for p in j.c['feed'] if p.get('kind') == 'review')
        # remember() +4, then the stars.
        self.assertEqual(qn.closeness(j.state, npc), max(0, 4 + qn.STARS[post['stars']]))


class ReceiveTests(unittest.TestCase):
    def _run(self, score, days=400, festival=False):
        j = fresh()
        s = j.state
        for pid in qn._cast():
            set_score(s, pid, score)
        if festival:
            j.c['life']['mode'] = 'festival'
        st = s['journey']['closeness']
        got = 0
        for d in range(days):
            st['inbox'] = [r for r in st['inbox'] if r['kind'] == 'invite' and r['state'] == 'new']
            before = st['seq']
            j.c['day'] += 1
            for pid in qn._cast():
                set_score(s, pid, score)     # hold the tier still (no decay, no thank losses)
            qn.after(s, j.career, 'advance', {}, dict(effects=[]))
            got += sum(1 for r in st['inbox'] if r['kind'] in ('gift', 'envelope') and int(r['id'][3:]) > before)
        return j, got

    def test_frequency_grows_with_tier(self):
        _, low = self._run(30)
        _, mid = self._run(50)
        _, high = self._run(85)
        self.assertEqual(low, 0)
        self.assertGreater(mid, 0)
        self.assertGreater(high, mid)

    def test_envelopes_paid_once_through_the_ledger(self):
        j, _ = self._run(90, days=250, festival=True)
        rows = gift_rows(j.c, 'gift')
        self.assertTrue(rows, 'close people give an envelope now and then')
        self.assertEqual(len({r['ref'] for r in rows}), len(rows))
        # Running the hook again on the same day pays nothing more.
        money = j.c['money']
        n = len(rows)
        qn.after(j.state, j.career, 'advance', {}, dict(effects=[]))
        qn.after(j.state, j.career, 'advance', {}, dict(effects=[]))
        self.assertEqual(j.c['money'], money)
        self.assertEqual(len(gift_rows(j.c, 'gift')), n)
        validate_state(j.state)

    def test_thank_and_unthanked(self):
        j = fresh()
        s = j.state
        st = s['journey']['closeness']
        row = qn._push(st, 'gift', 'co_ba', 'Cô Ba cho xoài', qn.today(s), item='xoai')
        a = qn.closeness(s, 'co_ba')
        j.act('qn_thank', id=row['id'])
        self.assertEqual(qn.closeness(j.state, 'co_ba'), a + 2)
        with self.assertRaises(GameError):
            j.act('qn_thank', id=row['id'])
        st = j.state['journey']['closeness']
        row = qn._push(st, 'gift', 'co_lua', 'Cô Lụa cho bánh', qn.today(j.state), item='banh_it')
        b = qn.closeness(j.state, 'co_lua')
        bump_day(j)
        self.assertEqual(qn.closeness(j.state, 'co_lua'), b)
        bump_day(j)
        self.assertEqual(qn.closeness(j.state, 'co_lua'), b - 1)

    def test_invites(self):
        j = fresh()
        st = j.state['journey']['closeness']
        d = qn.today(j.state)
        go = qn._push(st, 'invite', 'ba_tam', 'Đám giỗ', d, until=d + 1)
        a = qn.closeness(j.state, 'ba_tam')
        money = j.c['money']
        j.act('qn_invite', id=go['id'], choice='go')
        self.assertEqual(qn.closeness(j.state, 'ba_tam'), a + 5)
        self.assertEqual(j.c['money'], money - qn.INVITE_COST)
        with self.assertRaises(GameError):
            j.act('qn_invite', id=go['id'], choice='wish')
        st = j.state['journey']['closeness']
        wish = qn._push(st, 'invite', 'chu_tu', 'Sinh nhật', d, until=d + 1)
        b = qn.closeness(j.state, 'chu_tu')
        j.act('qn_invite', id=wish['id'], choice='wish')
        self.assertEqual(qn.closeness(j.state, 'chu_tu'), b + 1)
        st = j.state['journey']['closeness']
        qn._push(st, 'invite', 'co_ba', 'Đầy tháng', d, until=d + 1)
        c0 = qn.closeness(j.state, 'co_ba')
        bump_day(j)
        self.assertEqual(qn.closeness(j.state, 'co_ba'), c0)
        bump_day(j)
        self.assertEqual(qn.closeness(j.state, 'co_ba'), c0 - 3)


class DecayTests(unittest.TestCase):
    def test_gentle_decay_with_floors(self):
        j = fresh()
        s = j.state
        npc = 'mother_baby_npc_04'
        set_score(s, npc, 60)
        set_score(s, 'ba_sau', 42)
        j.act('qn_chat', who='ba_sau')
        s = j.state
        qn.change(s, npc, 0, 'x', 'talk')
        a = qn.closeness(s, npc)
        cast = qn.closeness(s, 'ba_sau')
        bump_day(j, 13)
        self.assertEqual(qn.closeness(j.state, npc), a)
        bump_day(j, 1)                                                  # day 14 apart
        self.assertEqual(qn.closeness(j.state, npc), a - 1)
        qn.after(j.state, j.career, 'advance', {}, dict(effects=[]))
        self.assertEqual(qn.closeness(j.state, npc), a - 1)             # once per step
        bump_day(j, 7)
        self.assertEqual(qn.closeness(j.state, npc), a - 2)
        self.assertGreaterEqual(qn.closeness(j.state, 'ba_sau'), qn.FLOOR_CAST if cast >= qn.FLOOR_CAST else cast)
        bump_day(j, 700)
        self.assertEqual(qn.closeness(j.state, npc), qn.FLOOR_NPC)      # never below the floor
        self.assertEqual(qn.closeness(j.state, 'ba_sau'), qn.FLOOR_CAST)


class SaveTests(unittest.TestCase):
    def test_new_and_old_saves(self):
        s = new_state()
        validate_state(s)
        old = copy.deepcopy(s)
        old['journey'].pop('closeness', None)
        up = migrate_state(old)
        self.assertIn('closeness', up['journey'])
        validate_state(up)
        view = public_state(up)
        self.assertIn('closeness', view)
        names = {p['name'] for p in view['closeness']['people']}
        self.assertTrue({'Bà Tám', 'Cô Ba', 'Bé Tí'} <= names)

    def test_bad_data_is_refused(self):
        j = fresh()
        for bad in (lambda st: st['people'].update(nobody=dict(seen=1, talk=0, gift=0, dec=0, rv=[], given=0, got=0)),
                    lambda st: st['bag'].update(vang=1),
                    lambda st: st['inbox'].append(dict(id='qn-9', day=1, kind='boom', who='ba_tam', text='x', item=None,
                                                       amount=0, state='new', until=1)),
                    lambda st: st.update(version=9)):
            s = copy.deepcopy(j.state)
            bad(s['journey']['closeness'])
            with self.assertRaises(GameError):
                validate_state(s)

    def test_life_changes_show_in_history(self):
        j = fresh()
        s = j.state
        s['journey']['life']['bonds']['anh_khoa'] += 4
        qn.after(s, j.career, 'advance', {}, dict(effects=[]))
        row = s['journey']['closeness']['log'][-1]
        self.assertEqual((row['who'], row['d'], row['k']), ('anh_khoa', 4, 'life'))

    def test_public_view(self):
        j = fresh()
        j.act('qn_chat', who='co_lua')
        v = public_state(j.state)['closeness']
        p = next(x for x in v['people'] if x['id'] == 'co_lua')
        self.assertTrue(p['talked'])
        self.assertEqual(p['tier'], qn.tier_of(p['score']))
        self.assertEqual(len(p['likes']), 1)                            # tier 3 reveals the first like
        self.assertTrue(p['history'])
        self.assertTrue(any(g['src'] == 'buy' for g in v['gifts']))


if __name__ == '__main__':
    unittest.main()
