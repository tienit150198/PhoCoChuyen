"""One character's journey: chapters and unlocks, wallet and funds, titles, day luck."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from game import journey as jr
from game.content import CAREERS, public_content
from game.engine import GameError, apply_action, migrate_state, needs_migration, new_state, public_state, validate_state
from game.storage import Store
from tests.helpers import Journey

CH1 = [c for c in jr.CH_UNLOCKS[1] if c in CAREERS]


def story_state(gender='female'):
    s = new_state()
    jr.enable_story(s, 12345)
    if gender:
        s['journey']['gender'] = gender
    validate_state(s)
    return s


def act(s, where, action, **p):
    return apply_action(s, where, action, p)


def ledger_ok(c):
    f = c['ops']['finance']
    return f['opening_balance'] + sum(x['amount'] for x in f['ledger']) == c['money']


def set_money(c, amount):
    """Test fixture: move a fund while keeping its ledger identity."""
    c['ops']['finance']['opening_balance'] += amount - c['money']
    c['money'] = amount


def poke(s):
    """A no-op journey action that runs the evaluation hook."""
    return act(s, None, 'jr_equip', title=s['journey']['equipped'])


class Play:
    """Two Ch1 workplaces started under the story."""

    def __init__(self):
        s = story_state()
        for cid in ('milk_tea', 'grocery'):
            s, _ = act(s, cid, 'select_career')
            s, _ = act(s, cid, 'start_day')
            s, _ = act(s, cid, 'end_day', carry_event=True)
        self.s = s

    def day(self, career='milk_tea', **p):
        s, _ = act(self.s, career, 'start_day')
        s, r = act(s, career, 'end_day', carry_event=True, **p)
        self.s = s
        return r


class Gating(unittest.TestCase):
    def test_new_state_is_open_sandbox(self):
        s = new_state()
        self.assertFalse(s['journey']['story'])
        for cid in CAREERS:
            self.assertTrue(jr.is_unlocked(s, cid))
        s, _ = act(s, 'restaurant' if 'restaurant' in CAREERS else CAREERS[-1], 'select_career')

    def test_locked_refused_on_select_and_start_without_change(self):
        s = story_state()
        locked = next(c for c in CAREERS if c not in CH1)
        before = copy.deepcopy(s)
        for action in ('select_career', 'start_day', 'buy_upgrade'):
            with self.assertRaises(GameError) as err:
                act(s, locked, action)
            self.assertEqual(err.exception.code, 'locked')
        self.assertEqual(s, before)
        for cid in CH1:
            act(s, cid, 'select_career')

    def test_intro_needs_a_character_first(self):
        s = story_state(gender=None)
        with self.assertRaises(GameError):
            act(s, CH1[0], 'select_career')
        with self.assertRaises(GameError):
            act(s, None, 'jr_profile', gender='other')
        with self.assertRaises(GameError):
            act(s, None, 'jr_profile', name='   ')
        s, _ = act(s, None, 'jr_profile', gender='male', name='Tùng')
        self.assertEqual((s['name'], s['journey']['gender']), ('Tùng', 'male'))
        s, _ = act(s, CH1[0], 'select_career')
        self.assertTrue(s['journey']['intro'])
        self.assertEqual(public_state(s)['journey']['gender'], 'male')

    def test_locked_office_cannot_apply(self):
        s = story_state()
        office = next(c for c in jr.OFFICE if c in CAREERS)
        from game import employment as emp
        self.assertFalse(emp._unlocked(s, office))
        with self.assertRaises(GameError):
            act(s, office, 'job_apply', posting=emp.postings(office)[0]['id'])

    def test_day_mode_cannot_be_picked(self):
        s = story_state()
        with self.assertRaises(GameError):
            act(s, CH1[0], 'life_mode', mode='festival')


class Chapters(unittest.TestCase):
    def test_first_chapter_by_real_play_unlocks_the_next(self):
        j = Journey('milk_tea')
        jr.enable_story(j.state, 7)
        j.state['journey']['gender'] = 'female'
        self.assertEqual(j.state['journey']['chapter'], 1)
        for _ in range(3):
            j.solve()
        self.assertEqual(j.state['journey']['chapter'], 1)   # the first day is not over yet
        r = j.act('end_day', carry_event=True)
        journey = j.state['journey']
        self.assertEqual(journey['chapter'], 2)
        self.assertEqual(journey['done'], [1])
        self.assertTrue(set(jr.CH_UNLOCKS[2]) & set(CAREERS) <= set(journey['unlocked']))
        self.assertIn('st_newcomer', journey['titles'])
        self.assertTrue(r.get('celebrate'))
        self.assertTrue(any(n['kind'] == 'chapter' and n['ref'] == '1' for n in journey['news']))
        validate_state(j.state)

    def test_chapters_follow_real_progress_and_stop_at_the_end(self):
        s = story_state()
        cs = s['careers']
        for cid in CAREERS:
            cs[cid]['metrics']['served'] = 12
            cs[cid]['xp'] = 400
            cs[cid]['day'] = 4
        s['journey']['stats']['withdrawn'] = 10
        s['journey']['clean_days'] = 9
        office = next(c for c in jr.OFFICE if c in CAREERS)
        from game import employment as emp
        cs[office]['job'] = emp.hired_record(office)
        cs[office]['job']['days_worked'] = 3
        for _ in range(8):
            s, _ = poke(s)
        self.assertEqual(s['journey']['chapter'], jr.LAST + 1)
        self.assertEqual(s['journey']['done'], list(range(1, jr.LAST + 1)))
        self.assertEqual(set(s['journey']['unlocked']), set(CAREERS))
        self.assertTrue(public_state(s)['journey']['finale'])
        validate_state(s)

    def test_goals_view_reads_real_state(self):
        s = story_state()
        goals = public_state(s)['journey']['goals']
        self.assertEqual([g['id'] for g in goals], ['days', 'tasks'])
        self.assertFalse(any(g['done'] for g in goals))


class Migration(unittest.TestCase):
    def old_save(self):
        s = new_state()
        del s['journey']
        s['schema'] = 4
        cs = s['careers']
        for cid, served, xp, day in (('milk_tea', 8, 240, 5), ('restaurant', 6, 120, 3), ('florist', 2, 60, 2)):
            if cid in cs:
                cs[cid].update(started=True, xp=xp, day=day)
                cs[cid]['metrics']['served'] = served
        return s

    def test_old_save_keeps_started_and_fast_forwards(self):
        old = self.old_save()
        self.assertTrue(needs_migration(old))
        m = migrate_state(old)
        validate_state(m)
        j = m['journey']
        self.assertTrue(j['story'])
        self.assertTrue(j['intro'])
        self.assertIsNone(j['gender'])
        for cid in ('milk_tea', 'restaurant', 'florist'):
            if cid in CAREERS:
                self.assertIn(cid, j['unlocked'])
        # 16 tasks at 3 places, level 3: chapters 1–3 are behind them (tracked goals skipped).
        self.assertEqual(j['done'], [1, 2, 3])
        self.assertTrue(set(jr.CH_UNLOCKS[4]) & set(CAREERS) <= set(j['unlocked']))
        self.assertEqual(j['life_day'], 1 + 4 + 2 + 1)
        self.assertEqual(j['wallet'], jr.START_WALLET)
        self.assertEqual(migrate_state(m), m)            # idempotent
        self.assertFalse(needs_migration(m))
        s, _ = act(m, 'restaurant' if 'restaurant' in CAREERS else 'milk_tea', 'select_career')

    def test_store_persists_migration_once(self):
        with tempfile.TemporaryDirectory() as td:
            store = Store(Path(td) / 'j.db')
            token, _, _ = store.session()
            with store.connect() as db:
                db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(self.old_save()), store.key(token)))
            s, rev, _ = store.read(token)
            self.assertEqual(rev, 1)
            self.assertTrue(s['journey']['story'])
            self.assertEqual(store.read(token)[1], 1)


class Wallet(unittest.TestCase):
    def test_living_costs_every_life_day(self):
        p = Play()
        j = p.s['journey']
        self.assertEqual(j['life_day'], 3)
        # milk_tea sat idle while grocery worked: its fund paid that upkeep, not the wallet.
        # The first life day ended with Bà Tám's welcome gift.
        self.assertEqual(j['wallet'], jr.START_WALLET - 2 * jr.LIVING[1] + jr.WELCOME_GIFT)
        rows = [h for h in j['history'] if h['kind'] == 'living']
        self.assertEqual([h['amount'] for h in rows], [-jr.LIVING[1]] * 2)
        before = j['wallet']
        r = p.day('grocery')
        self.assertEqual(p.s['journey']['wallet'], before - jr.LIVING[1])
        self.assertEqual(r['summary']['journey']['living'], jr.LIVING[1])
        self.assertTrue(any('Ngày sống' in e for e in r['effects']))

    def test_idle_upkeep_goes_to_the_idle_fund_only(self):
        p = Play()
        s = p.s
        idle, played = s['careers']['grocery'], s['careers']['milk_tea']
        money = idle['money']
        upkept = lambda c: len([x for x in c['ops']['finance']['ledger'] if x['category'] == 'upkeep'])
        before = upkept(played)
        p.day('milk_tea')
        idle, played = p.s['careers']['grocery'], p.s['careers']['milk_tea']
        fee = jr.upkeep(p.s, 'grocery')
        self.assertEqual(idle['money'], money - fee)
        last = idle['ops']['finance']['ledger'][-1]
        self.assertEqual((last['category'], last['amount']), ('upkeep', -fee))
        self.assertEqual(upkept(played), before)   # the workplace you work at pays its own bills instead
        self.assertTrue(ledger_ok(idle) and ledger_ok(played))

    def test_upkeep_shortfall_comes_from_the_wallet(self):
        p = Play()
        set_money(p.s['careers']['grocery'], 1)
        validate_state(p.s)
        wallet = p.s['journey']['wallet']
        p.day('milk_tea')
        fee = jr.upkeep(p.s, 'grocery')
        self.assertEqual(p.s['careers']['grocery']['money'], 0)
        self.assertEqual(p.s['journey']['wallet'], wallet - jr.LIVING[1] - (fee - 1))
        self.assertTrue(any(h['kind'] == 'upkeep' and h['amount'] == -(fee - 1) for h in p.s['journey']['history']))

    def test_pause_and_reopen(self):
        p = Play()
        with self.assertRaises(GameError):
            act(p.s, None, 'jr_pause', career='grocery')          # needs confirm
        s, _ = act(p.s, None, 'jr_pause', career='grocery', confirm=True)
        with self.assertRaises(GameError):
            act(s, None, 'jr_pause', career='grocery', confirm=True)
        with self.assertRaises(GameError) as err:
            act(s, 'grocery', 'start_day')
        self.assertEqual(err.exception.code, 'paused')
        money = s['careers']['grocery']['money']
        p.s = s
        p.day('milk_tea')
        self.assertEqual(p.s['careers']['grocery']['money'], money)   # no upkeep while paused
        s, r = act(p.s, None, 'jr_reopen', career='grocery', confirm=True)
        self.assertNotIn('grocery', s['journey']['paused'])
        self.assertEqual(s['careers']['grocery']['money'], money - jr.REOPEN_FEE)
        self.assertEqual(s['careers']['grocery']['ops']['finance']['ledger'][-1]['category'], 'reopen_fee')
        self.assertIn('x_reopen', s['journey']['titles'])
        act(s, 'grocery', 'start_day')

    def test_pause_rules(self):
        p = Play()
        s, _ = act(p.s, 'milk_tea', 'start_day')
        with self.assertRaises(GameError):
            act(s, None, 'jr_pause', career='milk_tea', confirm=True)          # shift is open
        with self.assertRaises(GameError):
            act(p.s, None, 'jr_pause', career='delivery', confirm=True)        # never worked there
        with self.assertRaises(GameError):
            act(p.s, None, 'jr_withdraw', career='restaurant', amount=5)       # locked

    def test_reopen_paid_by_wallet_or_free_when_stuck(self):
        p = Play()
        s, _ = act(p.s, None, 'jr_pause', career='grocery', confirm=True)
        set_money(s['careers']['grocery'], 3)
        wallet = s['journey']['wallet']
        s2, _ = act(s, None, 'jr_reopen', career='grocery', confirm=True)
        self.assertEqual(s2['journey']['wallet'], wallet - jr.REOPEN_FEE)
        # Broke everywhere and nowhere else to work: the neighbours help, no soft-lock.
        s, _ = act(s, None, 'jr_pause', career='milk_tea', confirm=True)
        for cid in CH1:  # every other storefront of chapter 1 is closed too
            if cid not in ('milk_tea', 'grocery', 'delivery'):
                s['journey']['paused'][cid] = s['journey']['life_day']
        # Delivery hires through a trial now: while not hired it is not somewhere else to work either.
        s['journey']['wallet'] = 0
        set_money(s['careers']['grocery'], 0)
        validate_state(s)
        s, r = act(s, None, 'jr_reopen', career='grocery', confirm=True)
        self.assertNotIn('grocery', s['journey']['paused'])
        self.assertEqual(s['journey']['wallet'], 0)

    def test_withdraw_and_invest_limits(self):
        p = Play()
        c = p.s['careers']['milk_tea']
        most = jr.withdraw_max(c)
        self.assertEqual(most, c['money'] - jr._unpaid(c) - jr.RESERVE)
        self.assertGreater(most, 0)
        for bad in (0, -5, most + 1, 1.5, '10'):
            with self.assertRaises(GameError):
                act(p.s, None, 'jr_withdraw', career='milk_tea', amount=bad)
        revenue = c['ops']['finance']['period_revenue']
        net = c['money'] - c['day_start_money']
        wallet = p.s['journey']['wallet']
        s, _ = act(p.s, None, 'jr_withdraw', career='milk_tea', amount=most)
        c2 = s['careers']['milk_tea']
        self.assertEqual(c2['money'], c['money'] - most)
        self.assertEqual(c2['money'], jr._unpaid(c2) + jr.RESERVE)
        self.assertEqual(s['journey']['wallet'], wallet + most)
        self.assertEqual(c2['ops']['finance']['ledger'][-1]['category'], 'owner_draw')
        self.assertEqual(c2['ops']['finance']['period_revenue'], revenue)      # not taxable
        self.assertEqual(c2['money'] - c2['day_start_money'], net)             # not the shop's cost
        self.assertEqual(c2['costs'], c['costs'])
        self.assertIn('m_first_draw', s['journey']['titles'])
        with self.assertRaises(GameError):
            act(s, None, 'jr_withdraw', career='milk_tea', amount=1)
        with self.assertRaises(GameError):
            act(s, None, 'jr_invest', career='milk_tea', amount=s['journey']['wallet'] + 1)
        s, _ = act(s, None, 'jr_invest', career='milk_tea', amount=20)
        c3 = s['careers']['milk_tea']
        self.assertEqual(c3['money'], c2['money'] + 20)
        self.assertEqual(c3['ops']['finance']['ledger'][-1]['category'], 'owner_capital')
        self.assertEqual(c3['ops']['finance']['period_revenue'], revenue)
        self.assertEqual(c3['earnings'], c2['earnings'])
        self.assertTrue(ledger_ok(c3))

    def test_sandbox_has_no_wallet_actions(self):
        j = Journey('milk_tea')
        with self.assertRaises(GameError):
            j.act('jr_withdraw', career='milk_tea', amount=5)

    def test_salary_lands_in_the_wallet(self):
        from game import employment as emp
        career = next(c for c in ('corp_accounting', 'tax_payroll', 'teacher') if c in CAREERS)
        j = Journey(career)
        jr.enable_story(j.state, 3)
        j.state['journey']['gender'] = 'male'
        c = j.c
        c['day_completed'] = 1
        money, wallet = c['money'], j.state['journey']['wallet']
        r = j.act('end_day', carry_event=True)
        pay = r['summary']['job']['salary']
        self.assertGreater(pay, 0)
        self.assertEqual(j.c['money'], money)
        gift = jr.WELCOME_GIFT   # it was the first life day: Bà Tám's welcome gift comes too
        self.assertEqual(j.state['journey']['wallet'], wallet + pay - jr.LIVING[j.state['journey']['chapter']] + gift)
        cats = [x['category'] for x in j.c['ops']['finance']['ledger'][-2:]]
        self.assertEqual(cats, ['salary', 'salary_to_wallet'])
        self.assertIn('m_salary', j.state['journey']['titles'])
        self.assertEqual(jr.upkeep(j.state, career), 0)
        self.assertTrue(emp.required(career))
        self.assertTrue(ledger_ok(j.c))


class Debt(unittest.TestCase):
    def test_debt_pauses_the_story_until_repaid(self):
        s = story_state()
        s, _ = act(s, 'milk_tea', 'select_career')
        s, _ = act(s, 'milk_tea', 'start_day')
        s['careers']['milk_tea']['metrics']['served'] = 3
        s['journey']['wallet'] = 4
        s['journey']['life_day'] = 2   # past the first day (whose end brings a welcome gift)
        s, r = act(s, 'milk_tea', 'end_day', carry_event=True)
        j = s['journey']
        self.assertEqual(j['wallet'], 4 - jr.LIVING[1])
        self.assertEqual(j['chapter'], 1)                       # goals met, but in debt
        self.assertTrue(public_state(s)['journey']['progress_paused'])
        self.assertEqual(public_state(s)['journey']['debt'], jr.LIVING[1] - 4)
        self.assertTrue(any('nợ' in e for e in r['effects']))
        self.assertEqual(j['clean_days'], 0)
        s, _ = act(s, None, 'jr_withdraw', career='milk_tea', amount=20)
        self.assertEqual(s['journey']['chapter'], 2)
        self.assertEqual(s['journey']['stats']['debt_repaid'], 1)
        self.assertIn('m_debt_free', s['journey']['titles'])


class Titles(unittest.TestCase):
    def test_catalogue(self):
        self.assertGreaterEqual(len(jr.TITLES), 40)
        cats = {t['cat'] for t in jr.TITLES}
        self.assertEqual(cats, {'story', 'general', 'career', 'skill', 'money', 'secret'})
        self.assertEqual(len({t['id'] for t in jr.TITLES}), len(jr.TITLES))
        for cid in jr.SKILL_WEIGHTS:
            self.assertIn('c_' + cid, jr.TITLE_INDEX)

    def test_awarded_once_with_day_and_equip(self):
        s = story_state()
        s['careers']['milk_tea']['metrics']['served'] = 1
        s, r = poke(s)
        j = s['journey']
        self.assertEqual(j['titles']['g_first'], j['life_day'])
        self.assertEqual(r['journey']['titles'], ['g_first'])
        news = [n for n in j['news'] if n['kind'] == 'titles']
        self.assertEqual(news[0]['items'], ['g_first'])
        s['journey']['life_day'] = 9
        s, r = poke(s)
        self.assertEqual(s['journey']['titles']['g_first'], 1)
        self.assertNotIn('journey', r)
        self.assertEqual(len([n for n in s['journey']['news'] if n['kind'] == 'titles']), 1)
        with self.assertRaises(GameError):
            act(s, None, 'jr_equip', title='g_tasks200')
        s, _ = act(s, None, 'jr_equip', title='g_first')
        pub = public_state(s)['journey']
        self.assertEqual(pub['equipped_title']['name'], 'Việc đầu tiên')
        s, _ = act(s, None, 'jr_seen', ids=[n['id'] for n in s['journey']['news']])
        self.assertEqual(s['journey']['news'], [])
        from game.social import snapshot
        self.assertEqual(snapshot(s)[0]['title'], dict(emoji='🌱', name='Việc đầu tiên'))   # shown on Phố nghề
        s, _ = act(s, None, 'jr_equip', title=None)
        self.assertIsNone(snapshot(s)[0]['title'])

    def test_secret_titles_stay_hidden_until_earned(self):
        content = public_content()['journey']
        secret = [t for t in content['titles'] if t.get('secret')]
        self.assertTrue(secret)
        self.assertTrue(all(set(t) == {'id', 'cat', 'secret'} for t in secret))
        s = story_state()
        self.assertEqual(public_state(s)['journey']['secret'], {})
        s['journey']['stats']['reopened'] = 1
        s, _ = poke(s)
        self.assertEqual(public_state(s)['journey']['secret']['x_reopen']['name'], 'Nghỉ để đi xa hơn')

    def test_maturity_and_skills_are_derived(self):
        s = story_state()
        base = public_state(s)['journey']['maturity']
        self.assertEqual(base['level'], 1)
        s['careers']['accounting']['metrics']['served'] = 30
        s['careers']['accounting']['xp'] = 900
        pub = public_state(s)['journey']
        self.assertEqual(pub['maturity']['xp'], 900 + jr.BREADTH_XP)
        self.assertGreater(pub['maturity']['level'], 1)
        skills = {x['id']: x for x in pub['skills']}
        self.assertEqual(skills['numbers']['points'], 60)
        self.assertEqual(skills['numbers']['level'], 3)
        self.assertEqual(skills['creative']['level'], 0)


class DayLuck(unittest.TestCase):
    def test_mode_is_deterministic_and_stored(self):
        s = story_state()
        self.assertEqual(jr.roll_mode(s, 'milk_tea', 1), 'normal')
        rolls = [jr.roll_mode(s, 'milk_tea', d) for d in range(2, 402)]
        self.assertEqual(rolls, [jr.roll_mode(s, 'milk_tea', d) for d in range(2, 402)])
        counts = {m: rolls.count(m) for m in ('calm', 'normal', 'festival')}
        self.assertTrue(60 <= counts['calm'] <= 140 and 170 <= counts['normal'] <= 270 and 45 <= counts['festival'] <= 120, counts)
        s, _ = act(s, 'milk_tea', 'select_career')
        s, _ = act(s, 'milk_tea', 'start_day')
        a, _ = act(s, 'milk_tea', 'end_day', carry_event=True)
        b, _ = act(s, 'milk_tea', 'end_day', carry_event=True)
        self.assertEqual(a['careers']['milk_tea']['life']['mode'], jr.roll_mode(s, 'milk_tea', 2))
        self.assertEqual(a['careers']['milk_tea']['life']['mode'], b['careers']['milk_tea']['life']['mode'])
        a, _ = act(a, 'milk_tea', 'start_day')
        want = {'calm': 2, 'normal': 3, 'festival': 4}[a['careers']['milk_tea']['life']['mode']]
        unfinished = 3   # day 1's tasks were carried over, new ones only top up to the day's target
        self.assertEqual(len([t for t in a['careers']['milk_tea']['tasks'] if t['day'] == 2]), max(0, want - unfinished))

    def test_settings_mode_is_ignored(self):
        s = new_state()
        s, _ = act(s, None, 'settings', mode='challenge')
        self.assertEqual(s['settings']['mode'], 'everyday')


class Integrity(unittest.TestCase):
    def test_ledger_invariant_through_everything(self):
        p = Play()
        s, _ = act(p.s, None, 'jr_withdraw', career='milk_tea', amount=30)
        s, _ = act(s, None, 'jr_invest', career='grocery', amount=15)
        s, _ = act(s, None, 'jr_pause', career='grocery', confirm=True)
        s, _ = act(s, None, 'jr_reopen', career='grocery', confirm=True)
        p.s = s
        for _ in range(3):
            p.day('milk_tea')
        for cid, c in p.s['careers'].items():
            self.assertTrue(ledger_ok(c), cid)
        validate_state(p.s)

    def test_tampered_journey_is_rejected(self):
        s = story_state()
        for edit in (lambda j: j['unlocked'].append('group_accounting'), lambda j: j.update(wallet='9'),
                     lambda j: j['titles'].update(fake=1), lambda j: j.update(chapter=3),
                     lambda j: j.update(gender='x'), lambda j: j.update(equipped='g_first'),
                     lambda j: j['paused'].update(teacher=1), lambda j: j['stats'].update(hack=1)):
            bad = copy.deepcopy(s)
            edit(bad['journey'])
            with self.assertRaises(GameError):
                validate_state(bad)

    def test_reset_all_keeps_the_story(self):
        s = story_state()
        s, _ = act(s, None, 'reset_all', confirm='BAT DAU LAI')
        self.assertTrue(s['journey']['story'])
        self.assertFalse(s['journey']['intro'])
        self.assertIsNone(s['journey']['gender'])

    def test_public_state_is_small(self):
        p = Play()
        self.assertLess(len(json.dumps(public_state(p.s)['journey'], ensure_ascii=False)), 8500)   # 1.4.8: owning several homes (housing props) added ~180 bytes


class Storage(unittest.TestCase):
    def test_story_store_sessions_and_imports(self):
        with tempfile.TemporaryDirectory() as td:
            plain = Store(Path(td) / 'a.db')
            token, _, _ = plain.session()
            self.assertFalse(plain.read(token)[0]['journey']['story'])
            store = Store(Path(td) / 'b.db', story=True)
            token, _, _ = store.session()
            s = store.read(token)[0]
            self.assertTrue(s['journey']['story'])
            self.assertEqual(s['journey']['unlocked'], CH1)
            locked = next(c for c in CAREERS if c not in CH1)
            with self.assertRaises(GameError):
                store.command(token, 'req-lock-01', 0, locked, 'select_career', {})
            # A sandbox backup cannot switch the story off: it joins at its own progress.
            j = Journey('restaurant' if 'restaurant' in CAREERS else 'milk_tea')
            r = store.command(token, 'req-import-1', 0, None, 'import_save',
                              {'save': {'format': 'mot-ngay-lam-nghe/save-v4', 'state': j.state}})
            s = store.read(token)[0]
            self.assertTrue(s['journey']['story'])
            self.assertIn(j.career, s['journey']['unlocked'])
            self.assertTrue(r['state']['journey']['story'])


if __name__ == '__main__':
    unittest.main()


class Onboarding(unittest.TestCase):
    def test_old_first_chapter_save_gets_every_storefront(self):
        from game.engine import migrate_state, public_state
        s = story_state()
        s['journey']['unlocked'] = ['milk_tea', 'grocery', 'delivery']  # a save from before the wider chapter 1
        s = migrate_state(s)
        self.assertTrue(set(CH1) <= set(s['journey']['unlocked']))
        validate_state(s)

    def test_first_view_shows_an_open_workplace(self):
        from game.engine import public_state
        s = story_state()
        v = public_state(s)
        self.assertIn(v['focus'], s['journey']['unlocked'])
        self.assertIn('feed', v['careers'][v['focus']])
