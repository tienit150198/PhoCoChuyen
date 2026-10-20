"""💛 Thân thiết với NPC (game/goodwill.py on top of game/closeness.py): the pay a close regular adds and its caps,
the neighbours' perks (rent, gift prices, the hidden jar, weekly favours), việc nhờ, birthdays, referrals, the reveal
of hidden rows, the per-Vietnam-day gain cap, the kill switch, the view, the coach card and saves an older release
(2.4.72) keeps loading."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import closeness as qn
from game import goodwill as gw
from game import goodwill_content as GC
from game.careers import kit
from game.engine import GameError, public_state, validate_state
from game.journey import living_cost
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parents[1]
T0 = 1_792_000_000.0          # a fixed real time (Vietnam day vn_day(T0))
LIVE = '83fe229c'             # release 2.4.72 (live): no goodwill code


class Base(unittest.TestCase):
    def setUp(self):
        self.now = T0
        p = mock.patch.object(kit, 'clock', lambda: self.now)
        p.start()
        self.addCleanup(p.stop)
        os.environ.pop('MNL_NPCGW_OFF', None)
        self.addCleanup(os.environ.pop, 'MNL_NPCGW_OFF', None)
        self.j = Journey('mother_baby')

    @property
    def s(self):
        return self.j.state

    def next_vn_day(self, n=1):
        self.now += 86400 * n

    def bump_life_day(self):
        self.j.c['day'] += 1
        qn.after(self.j.state, self.j.career, 'advance', {}, dict(effects=[]))
        validate_state(self.j.state)

    def fund(self, n):
        c = self.j.c
        c['money'] += n
        c['ops']['finance']['opening_balance'] += n

    def set(self, pid, v):
        qn._set(self.j.state, pid, v)

    def block(self):
        return self.s['journey'].get(gw.KEY)

    def ledger(self, text):
        return [r for r in self.j.c['ops']['finance']['ledger'] if text in r['reason']]

    def view(self):
        return public_state(self.j.state)['closeness']


class PayTests(Base):
    def solve_for(self, score, touched=False):
        t = self.j.task
        npc = t['npc']
        self.j.c['relationships'][npc] = score
        if touched:
            gw.touch(self.j.state, qn.home(npc))
        with mock.patch('game.interest_clock.day_paid', return_value=True):
            done = self.j.solve()
        return done, npc

    def paid(self):
        return sum(r['amount'] for r in self.ledger('Khách quen trả thêm'))

    def test_a_stranger_adds_nothing(self):
        self.solve_for(10)
        self.assertEqual(self.paid(), 0)

    def test_tiers_pay_more_and_contact_adds_two(self):
        for score, touched, pct in ((45, False, 2), (65, False, 4), (85, False, 6), (85, True, 8)):
            with self.subTest(score=score, touched=touched):
                self.setUp()
                done, npc = self.solve_for(score, touched)
                pay = next(r['amount'] for r in self.j.c['ops']['finance']['ledger'] if r['ref'] == done['id'] and r['reason'].startswith('Hoàn thành'))
                self.assertEqual(self.paid(), min(gw.JOB_CAP, (pay * pct + 50) // 100))
                self.assertGreater(self.paid(), 0)
                row = next(r for r in self.ledger('Khách quen trả thêm'))
                self.assertEqual(row['category'], 'revenue')
                self.assertEqual(row['ref'], done['id'])

    def test_pct_never_passes_the_cap(self):
        s = self.s
        npc = self.j.task['npc']
        self.j.c['relationships'][npc] = 95
        gw.touch(s, npc)
        b = gw._block(s)
        gw._set_ref(b, 'mother_baby', npc, gw.vn_day())
        with mock.patch.object(gw, '_has', return_value=True):
            self.assertLessEqual(gw.pay_pct(s, 'pho', npc), gw.MAX_PCT)
        t = dict(career='mother_baby', npc=npc, id='x-1')
        c = self.j.c
        with mock.patch('game.interest_clock.day_paid', return_value=True):
            got = gw.pay_bonus(s, c, t, 1000)
        self.assertEqual(got, 1000 * gw.MAX_PCT // 100)
        self.assertEqual(b['ref']['n'], gw.REF_JOBS - 1)
        self.assertEqual(len(self.ledger('Khách sộp')), 1)

    def test_job_and_day_caps(self):
        s = self.s
        npc = self.j.task['npc']
        self.j.c['relationships'][npc] = 90
        c = self.j.c
        with mock.patch('game.interest_clock.day_paid', return_value=True):
            got = [gw.pay_bonus(s, c, dict(career='mother_baby', npc=npc, id=f'x-{i}'), 10 ** 6) for i in range(8)]
        self.assertEqual(got[0], gw.JOB_CAP)
        self.assertEqual(sum(got), gw.DAY_CAP)
        self.next_vn_day()
        with mock.patch('game.interest_clock.day_paid', return_value=True):
            self.assertEqual(gw.pay_bonus(s, c, dict(career='mother_baby', npc=npc, id='x-9'), 10 ** 6), gw.JOB_CAP)
        validate_state(s)

    def test_no_bonus_beyond_the_real_time_allowance_or_for_player_orders(self):
        s = self.s
        npc = self.j.task['npc']
        self.j.c['relationships'][npc] = 90
        with mock.patch('game.interest_clock.day_paid', return_value=False):
            self.assertEqual(gw.pay_bonus(s, self.j.c, dict(career='mother_baby', npc=npc, id='x-1'), 500), 0)
        with mock.patch('game.interest_clock.day_paid', return_value=True):
            self.assertEqual(gw.pay_bonus(s, self.j.c, dict(career='mother_baby', npc=npc, id='x-1', player_order=True), 500), 0)
            self.assertEqual(gw.pay_bonus(s, self.j.c, dict(career='mother_baby', npc=npc, id='x-1'), 0), 0)
            self.assertEqual(gw.pay_bonus(s, self.j.c, dict(career='mother_baby', npc=npc, id='x-1'), 6), 0, 'rounded: no 1-xu bonus on a tiny job')

    def test_food_recipe_from_ba_sau(self):
        s = self.s
        npc = self.j.task['npc']
        self.j.c['relationships'][npc] = 45
        self.assertEqual(gw.pay_pct(s, 'pho', npc), 2)
        self.set('ba_sau', 85)
        self.assertEqual(gw.pay_pct(s, 'pho', npc), 4)
        self.assertEqual(gw.pay_pct(s, 'mother_baby', npc), 2)


class NeighbourPerks(Base):
    def test_ba_tam_rent(self):
        j = self.s['journey']
        j['story'] = True
        base = living_cost(j)
        self.assertNotIn('perk', base)
        self.assertEqual(base['where'], 'attic')
        for score, pct in ((65, 10), (85, 20)):
            j['life']['bonds']['ba_tam'] = score
            got = living_cost(j)
            cut = max(1, base['rent'] * pct // 100)
            self.assertEqual(got['rent'], base['rent'] - cut)
            self.assertEqual(got['total'], base['total'] - cut)
            self.assertEqual(got['perk'], cut)
        os.environ['MNL_NPCGW_OFF'] = '1'
        self.assertEqual(living_cost(j), base)

    def test_co_ba_prices_and_the_hidden_jar(self):
        self.fund(500)
        before = self.j.c['money']
        self.j.act('qn_gift', who='ba_sau', gift='tra', src='buy')
        self.assertEqual(before - self.j.c['money'], GC_price('tra'))
        with self.assertRaises(GameError):
            self.j.act('qn_gift', who='ba_tam', gift=GC.HIDDEN_GIFT['id'], src='buy')
        self.set('co_ba', 65)
        before = self.j.c['money']
        self.j.act('qn_gift', who='ba_tam', gift='tra', src='buy')
        self.assertEqual(before - self.j.c['money'], 9, '10 xu less 10 %')
        self.assertNotIn(GC.HIDDEN_GIFT['id'], [g['id'] for g in self.view()['gifts']])
        self.set('co_ba', 85)
        gifts = {g['id']: g for g in self.view()['gifts']}
        self.assertTrue(gifts[GC.HIDDEN_GIFT['id']]['secret'])
        self.assertEqual(gifts['tra']['price'], 8)
        self.assertEqual(gifts['tra']['was'], 10)
        before = self.j.c['money']
        r = self.j.act('qn_gift', who='co_ba', gift=GC.HIDDEN_GIFT['id'], src='buy')   # Cô Ba likes fruit
        self.assertEqual(before - self.j.c['money'], 5)
        self.assertGreaterEqual(r['gain'], 3 + GC.HIDDEN_GIFT['extra'])

    def test_favours_once_a_week(self):
        with self.assertRaises(GameError) as e:
            self.j.act('qn_favour', who='ba_sau')
        self.assertEqual(e.exception.code, 'locked')
        self.set('ba_sau', 65)
        r = self.j.act('qn_favour', who='ba_sau')
        self.assertTrue(r['message'])
        self.assertTrue(set(self.s['journey']['closeness']['bag']) & set(GC.FAVOUR_ITEMS['ba_sau']))
        with self.assertRaises(GameError) as e:
            self.j.act('qn_favour', who='ba_sau')
        self.assertEqual(e.exception.code, 'already_done')
        self.next_vn_day(gw.FAVOUR_DAYS)
        self.j.act('qn_favour', who='ba_sau')
        for bad in ('nobody', 'grocery_npc_01', ['ba_sau'], None):
            with self.subTest(who=bad), self.assertRaises(GameError):
                self.j.act('qn_favour', who=bad)

    def test_spirit_favours_and_the_party(self):
        s = self.s
        s['journey']['story'] = True
        s['journey']['life']['spirit'] = 50
        self.set('ba_tam', 65)
        self.j.act('qn_favour', who='ba_tam')
        self.assertEqual(self.s['journey']['life']['spirit'], 55)
        self.set('co_lua', 65)
        before = {p: qn.closeness(self.s, p) for p in GC.CAST}
        self.j.act('qn_favour', who='co_lua')
        after = {p: qn.closeness(self.s, p) for p in GC.CAST}
        self.assertEqual(after['co_lua'], before['co_lua'])
        self.assertTrue(all(after[p] == min(100, before[p] + 1) for p in GC.CAST if p != 'co_lua'))
        self.assertEqual(self.s['journey']['life']['spirit'], 58)

    def test_anh_khoa_referral(self):
        self.set('anh_khoa', 65)
        r = self.j.act('qn_favour', who='anh_khoa')
        ref = self.block()['ref']
        self.assertEqual((ref['c'], ref['n'], ref['by']), ('mother_baby', gw.REF_JOBS, 'anh_khoa'))
        self.assertTrue(r['effects'])
        g = self.view()['gw']
        self.assertEqual(g['ref']['n'], gw.REF_JOBS)
        self.next_vn_day(gw.FAVOUR_DAYS)
        with self.assertRaises(GameError):   # the last referral has not come in yet
            self.j.act('qn_favour', who='anh_khoa')


class ErrandBirthday(Base):
    def test_errand_done_by_a_matching_gift(self):
        self.j.act('qn_chat', who='ba_tam')       # any command stores today's request
        e = self.block()['err']
        self.assertEqual(e['d'], gw.vn_day())
        self.assertNotIn(e['tag'], qn.taste(e['who'])['dislikes'])
        gift = next(k for k, x in qn.GIFTS.items() if e['tag'] in x['tags'] and not (qn.is_kid(e['who']) and set(x['tags']) & set(qn.KID_NOT)))
        self.fund(500)
        before = qn.closeness(self.s, e['who'])
        r = self.j.act('qn_gift', who=e['who'], gift=gift, src='buy')
        self.assertEqual(self.block()['err']['st'], 'done')
        self.assertEqual(self.block()['errn'][e['who']], 1)
        self.assertEqual(qn.closeness(self.s, e['who']), min(100, before + r['gain'] + gw.ERRAND_GAIN))
        self.assertTrue(self.view()['gw']['errand']['done'])
        self.next_vn_day()
        self.j.act('qn_chat', who='ba_tam')
        self.assertEqual(self.block()['err']['st'], 'open')

    def test_birthday_gift_counts_twice_once_a_day(self):
        dd, mm = gw.birthday('ba_sau')
        import datetime
        day = (datetime.date(2026, mm, dd) - datetime.date(1970, 1, 1)).days
        self.now = day * 86400 - 7 * 3600 + 3600   # 01:00 in Vietnam that day
        self.assertTrue(gw.is_birthday('ba_sau'))
        self.set('ba_sau', 50)
        self.fund(500)
        r = self.j.act('qn_gift', who='ba_sau', gift='trai_cay', src='buy')   # fruit: Bà Sáu likes it
        self.assertEqual(qn.closeness(self.s, 'ba_sau'), 50 + 2 * r['gain'] + (gw.ERRAND_GAIN if self.block()['err']['st'] == 'done' and self.block()['err']['who'] == 'ba_sau' else 0))
        self.assertIn('ba_sau', [p['id'] for p in self.view()['people'] if p['gw'].get('bday_today')])
        self.bump_life_day()
        self.block()['err'] = None   # no việc nhờ in the way
        before = qn.closeness(self.s, 'ba_sau')
        r = self.j.act('qn_gift', who='ba_sau', gift='trai_cay', src='buy')
        self.assertEqual(qn.closeness(self.s, 'ba_sau'), before + r['gain'], 'the birthday counts once a Vietnam day')

    def test_birthdays_are_stable_dates(self):
        for pid in list(GC.CAST) + ['mother_baby_npc_01', 'grocery_npc_03']:
            d, m = gw.birthday(pid)
            self.assertTrue(1 <= d <= 31 and 1 <= m <= 12)
            self.assertEqual(gw.birthday(pid), (d, m))


class RateLimit(Base):
    def test_gains_from_chats_and_gifts_capped_per_vietnam_day(self):
        self.set('ba_sau', 40)
        self.fund(1000)
        total, refused = 0, 0
        for _ in range(6):
            total += self.j.act('qn_chat', who='ba_sau')['gain']
            try:
                total += self.j.act('qn_gift', who='ba_sau', gift='trai_cay', src='buy')['gain']
            except GameError as e:
                self.assertEqual(e.code, 'already_done')
                refused += 1
            self.bump_life_day()
        self.assertEqual(total, gw.VN_GAIN_CAP)
        self.assertGreater(refused, 0, 'a gift that cannot count today is refused before it is paid for')
        self.assertEqual(gw.room(self.s, 'ba_sau'), 0)
        r = self.j.act('qn_chat', who='ba_sau')
        self.assertEqual(r['gain'], 0)
        self.assertTrue(any('vui lắm rồi' in x for x in r['effects']))
        self.bump_life_day()
        self.next_vn_day()
        self.assertGreater(self.j.act('qn_chat', who='ba_sau')['gain'], 0)

    def test_losses_pass(self):
        self.set('ba_sau', 60)
        self.fund(1000)
        r = self.j.act('qn_gift', who='ba_sau', gift='ca_phe', src='buy')   # Bà Sáu dislikes coffee
        self.assertLess(r['gain'], 0)


class Reveal(Base):
    def test_hidden_rows_stay_secret_until_reached_then_are_told_once(self):
        v = self.view()
        ba = next(p for p in v['people'] if p['id'] == 'be_ti')
        roof = next(r for r in ba['gw']['ladder'] if r['id'] == 'roof')
        self.assertEqual((roof['name'], roof['words'], roof['emoji']), ('???', '', '🔒'))
        refer = next(r for r in v['gw']['common'] if r['id'] == 'refer')
        self.assertEqual(refer['name'], '???')
        self.assertNotIn('Sân thượng', json.dumps(v, ensure_ascii=False))
        self.set('be_ti', 65)
        r = self.j.act('qn_chat', who='ba_tam')
        self.assertTrue(any('sân thượng' in x for x in r['effects']))
        self.assertIn('be_ti:roof', self.block()['told'])
        rows = [x for x in self.s['journey']['closeness']['inbox'] if x['who'] == 'be_ti' and x['kind'] == 'care']
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.view()['gw']['fresh'], 1)
        r = self.j.act('qn_chat', who='ba_tam')
        self.assertFalse(any('sân thượng' in x for x in r['effects']), 'told once')
        self.j.act('qn_gw_seen')
        self.assertEqual(self.view()['gw']['fresh'], 0)
        ba = next(p for p in self.view()['people'] if p['id'] == 'be_ti')
        self.assertEqual(next(r for r in ba['gw']['ladder'] if r['id'] == 'roof')['name'], 'Sân thượng bí mật')

    def test_story_needs_the_errands(self):
        self.set('ba_tam', 90)
        self.j.act('qn_chat', who='ba_sau')
        self.assertNotIn('ba_tam:story', self.block()['told'])
        self.block()['errn']['ba_tam'] = GC.ERRANDS_FOR_STORY
        self.j.act('qn_chat', who='ba_sau')
        self.assertIn('ba_tam:story', self.block()['told'])
        ba = next(p for p in self.view()['people'] if p['id'] == 'ba_tam')
        self.assertEqual(ba['gw'].get('story'), GC.STORIES['ba_tam'])

    def test_customer_referral_after_a_chat(self):
        npc = 'mother_baby_npc_02'
        self.j.c['relationships'][npc] = 85
        r = self.j.act('qn_chat', who=npc)
        self.assertIn('refer', self.block()['told'])
        ref = self.block()['ref']
        self.assertEqual((ref['c'], ref['by']), ('mother_baby', npc))
        self.assertTrue(any(x.startswith('🤝') for x in r['effects']))
        refer = next(r for r in self.view()['gw']['common'] if r['id'] == 'refer')
        self.assertNotEqual(refer['name'], '???')

    def test_titles(self):
        self.assertEqual(self.view()['gw']['titles'], [])
        for pid in GC.CAST:
            self.set(pid, 85)
        self.j.act('qn_chat', who='ba_tam')
        names = [t['name'] for t in self.view()['gw']['titles']]
        self.assertEqual(names, ['Người tốt của tổ', 'Cả hẻm thương'])


class KillSwitch(Base):
    def test_off_keeps_everything_and_turns_perks_off(self):
        self.set('co_ba', 85)
        self.set('be_ti', 65)
        self.j.act('qn_chat', who='ba_tam')
        kept = json.dumps(self.block(), sort_keys=True)
        os.environ['MNL_NPCGW_OFF'] = '1'
        self.assertEqual(gw.shop_pct(self.s), 0)
        self.assertIsNone(gw.hidden_gift(self.s))
        self.assertEqual(gw.pay_pct(self.s, 'mother_baby', 'ba_tam'), 0)
        self.assertEqual(gw.reached(self.s), [])
        self.assertEqual(self.view()['gw'], dict(on=False))
        with self.assertRaises(GameError) as e:
            self.j.act('qn_favour', who='be_ti')
        self.assertEqual(e.exception.code, 'paused')
        self.set('ba_sau', 40)
        self.fund(1000)
        total = 0
        for _ in range(4):
            total += self.j.act('qn_chat', who='ba_sau')['gain']
            total += self.j.act('qn_gift', who='ba_sau', gift='trai_cay', src='buy')['gain']
            self.bump_life_day()
        self.assertGreater(total, gw.VN_GAIN_CAP, 'the old rules: no daily cap while off')
        b = json.loads(kept)
        self.assertEqual(json.dumps(self.block(), sort_keys=True), json.dumps(b, sort_keys=True), 'nothing lost, nothing moved')
        del os.environ['MNL_NPCGW_OFF']
        self.assertEqual(gw.shop_pct(self.s), 20)


class Validation(Base):
    def test_bad_blocks_are_refused(self):
        self.j.act('qn_chat', who='ba_tam')
        good = json.loads(json.dumps(self.s))
        validate_state(good)
        bads = [
            lambda b: b.update(x=1),
            lambda b: b.update(v=2),
            lambda b: b['p'].update(nobody=[0, 0, 0, 0]),
            lambda b: b['p'].update(ba_tam=[0, 99, 0, 0]),
            lambda b: b.update(ref=dict(c='nowhere', n=1, u=1, by='ba_tam')),
            lambda b: b.update(ref=dict(c='mother_baby', n=9, u=1, by='ba_tam')),
            lambda b: b.update(pay=[0, gw.DAY_CAP + 1]),
            lambda b: b.update(err=dict(d=1, who='ba_tam', tag='nope', st='open')),
            lambda b: b.update(told=['x' * 41]),
            lambda b: b['errn'].update(ba_tam=1000),
        ]
        for i, bad in enumerate(bads):
            with self.subTest(i=i):
                s = json.loads(json.dumps(good))
                bad(s['journey'][gw.KEY])
                with self.assertRaises(GameError):
                    validate_state(s)
        s = json.loads(json.dumps(good))
        s['journey'][gw.KEY] = []
        with self.assertRaises(GameError):
            validate_state(s)


class Coach(unittest.TestCase):
    def test_feature_coach_is_rendered_and_translated(self):
        from game import coach as C
        from game.coach import people
        data = C.public()
        self.assertIn('goodwill', data['features'])
        js = (ROOT / 'public' / 'js' / 'tutorial' / 'coach-content.js').read_text(encoding='utf-8')
        self.assertEqual(js, C.render_js())
        over = json.loads((ROOT / 'i18n' / 'overrides.json').read_text(encoding='utf-8'))['strings']
        for st in people.FEATURES['goodwill']:
            with self.subTest(line=st['t'][:30]):
                self.assertLessEqual(len(st['t']), 90)
                self.assertEqual(over.get(st['t']), people.EN[st['t']])
        src = (ROOT / 'public' / 'js' / 'v4' / 'closeness.js').read_text(encoding='utf-8')
        self.assertIn(f"GW_NOTE='{people.NOTE}'", src)
        from game.engine import notes_seen
        self.assertEqual(notes_seen('onb1,' + people.NOTE), 'onb1,' + people.NOTE)


def GC_price(gift):
    return qn.GIFTS[gift]['price']


class OlderRelease(Base):
    """2.4.72 (live) knows nothing of journey.npcgw: it loads, validates, plays and saves a save holding it untouched."""

    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-npcgw-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', LIVE, 'game', 'reference', 'live'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {LIVE}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def test_a_save_with_the_block_plays_on_2_4_72(self):
        from tests.helpers import as_stored
        self.set('be_ti', 65)
        self.set('co_ba', 85)
        self.j.act('qn_chat', who='ba_tam')
        self.set('anh_khoa', 65)
        self.j.act('qn_favour', who='anh_khoa')
        self.assertIsNotNone(self.block()['ref'])
        mine = json.dumps(self.block(), sort_keys=True)
        prog = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action
s=json.load(sys.stdin)
s=migrate_state(s);validate_state(s)
before=json.dumps(s['journey'].get('npcgw'),sort_keys=True)
s,_=apply_action(s,'mother_baby','qn_chat',{'who':'ba_sau'})
validate_state(s)
print(json.dumps([before,json.dumps(s['journey'].get('npcgw'),sort_keys=True),s]))
'''
        old = self.old_tree()
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(as_stored(self.s), ensure_ascii=False),
                             capture_output=True, text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        before, after, back = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertEqual(before, mine)
        self.assertEqual(after, mine, '2.4.72 keeps journey.npcgw untouched')
        from game.engine import migrate_state
        back = migrate_state(back, owned=True)
        validate_state(back)
        self.assertEqual(json.dumps(back['journey'][gw.KEY], sort_keys=True), mine)


if __name__ == '__main__':
    unittest.main()
