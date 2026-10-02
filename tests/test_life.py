"""Chuyện đời thường & tình làng nghĩa xóm (game/life.py)."""
import copy
import random
import unittest

from game import invest as iv
from game import journey as jr
from game import life as lf
from game.engine import GameError, apply_action, new_state, public_state, validate_state
from game.life_content import ASK, COMFORT, COPE, HARD, JOYS, NOT_FOR_CALLING, WORK
from game.content import CAREERS


def state(wallet=150, seed=12345, gender='female', story=True):
    s = new_state()
    if story:
        jr.enable_story(s, seed)
    s['journey']['gender'] = gender
    s['journey']['wallet'] = wallet
    iv.migrate(s)
    lf.migrate(s)
    validate_state(s)
    return s


def L(s):
    return s['journey']['life']


def at(s, d):
    """Jump to life day `d` without rolling anything (for hand-fired cards)."""
    s['journey']['life_day'] = d
    L(s)['day'] = d
    return s


def day(s, career='teacher', completed=3, mode='normal', income=10, check=True):
    """One life day closing the way end_day does: journey bumps life_day, then life catches up."""
    j = s['journey']
    j['days'] = (j['days'] + [dict(d=j['life_day'], c=career, m=mode)])[-60:]
    j['life_day'] += 1
    j['wallet'] += income
    result = dict(summary=dict(completed=completed))
    lf.on_life_day(s, result, career)
    if check:
        validate_state(s)
    else:
        lf.validate(s)
    return result


def act(s, name, **p):
    t = copy.deepcopy(s)
    return lf.action(t, name, p)


def quick(s, name, **p):
    """Like act, for long simulated runs: the life layer's own checks only."""
    r = lf.apply(s, name, p)
    lf.validate(s)
    return s, r


def play(s, rng=None):
    """Answer the pending card to the end (random affordable choices, or the first)."""
    for _ in range(8):
        card = L(s)['pending']
        if not card or card['stage'] == 'done':
            return s
        ch = [c for c in lf.public(s)['pending']['choices'] if c['ok']]
        c = rng.choice(ch) if rng else ch[0]
        s, _ = quick(s, 'lf_choose', id=card['id'], choice=c['id'])
    return s


def run(seed, n=60, career='teacher', rng=None, income=10, check=False):
    s = state(seed=seed)
    seen = []
    for _ in range(n):
        day(s, career, income=income, check=check)
        card = L(s)['pending']
        seen.append(dict(card) if card else None)
        s = play(s, rng)
    return s, seen


class Content(unittest.TestCase):
    def test_counts_and_shapes(self):
        cats = {}
        for x in HARD:
            cats[x['cat']] = cats.get(x['cat'], 0) + 1
            self.assertTrue(2 <= len(x['choices']) <= 3, x['id'])
            self.assertTrue(any(c['money'] >= 0 for c in x['choices']), x['id'])
            self.assertLess(x['hit'], 0)
            for c in x['careers'] or ():
                self.assertIn(c, CAREERS)
        for cat in ('an_hiep', 'phu_huynh', 'khach', 'lua', 'that_tinh', 'xui', 'dat_dieu'):
            self.assertGreaterEqual(cats.get(cat, 0), 7, cat)
        self.assertGreaterEqual(len(COMFORT), 12)
        self.assertGreaterEqual(len(ASK), 6)
        self.assertGreaterEqual(len(JOYS), 6)
        self.assertEqual({c['id'] for c in COPE} >= {'karaoke', 'tra_sua', 'dalat', 'vungtau', 'online', 'nhau', 'ho', 'ngu', 'me'}, True)
        self.assertEqual(set(WORK), set(CAREERS))
        ids = [x['id'] for x in HARD] + [x['id'] for x in COMFORT] + [x['id'] for x in ASK] + [x['id'] for x in JOYS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_career_has_hard_days_of_its_own(self):
        for cid in CAREERS:
            own = [x for x in HARD if x['careers'] and cid in x['careers']]
            self.assertGreaterEqual(len(own), 3, cid)

    def test_texts_fill_for_every_gender(self):
        for g in ('male', 'female', None):
            s = state(gender=g)
            for x in HARD:
                card = lf._new_card(L(s), 5, 'hard', x['id'], x['cat'], 'react', 'teacher', gossip='thim_bay')
                for t in x['lines'] + [c['label'] for c in x['choices']] + [c['text'] for c in x['choices']] + [x['title']]:
                    out = lf._fill(t, s, card)
                    self.assertNotIn('{', out, (x['id'], out))


class Rhythm(unittest.TestCase):
    def test_deterministic_for_a_seed(self):
        a, sa = run(7, 30)
        b, sb = run(7, 30)
        c, sc = run(8, 30)
        self.assertEqual(sa, sb)
        self.assertEqual(L(a), L(b))
        self.assertNotEqual([x and x['ref'] for x in sa], [x and x['ref'] for x in sc])

    def test_frequency_over_60_days(self):
        days = events = hard = 0
        for seed in range(12):
            _, seen = run(seed, 60, career=('teacher', 'delivery', 'milk_tea', 'corp_accounting')[seed % 4],
                          rng=random.Random(seed))
            later = seen[3:]
            days += len(later)
            events += sum(1 for x in later if x)
            hard += sum(1 for x in later if x and x['kind'] == 'hard')
        self.assertTrue(.4 <= events / days <= .7, events / days)
        self.assertTrue(.25 <= hard / days <= .45, hard / days)

    def test_calm_first_days(self):
        for seed in range(30):
            _, seen = run(seed, 5)
            self.assertIsNone(seen[0], seed)          # life day 2: nothing yet
            for x in seen[:4]:
                if x and x['kind'] == 'hard':
                    self.assertTrue(lf.HARD_INDEX[x['ref']]['mild'])

    def test_no_identical_variant_within_ten_days(self):
        for seed in range(8):
            _, seen = run(seed, 60, rng=random.Random(seed))
            last = {}
            for i, x in enumerate(seen):
                if x and x['kind'] in ('hard', 'ask', 'joy'):
                    if x['ref'] in last:
                        self.assertGreaterEqual(i - last[x['ref']], lf.RECENT, (seed, x['ref']))
                    last[x['ref']] = i

    def test_neighbours_follow_most_hard_days(self):
        total = warm = 0
        for seed in range(10):
            s = state(seed=seed)
            for _ in range(40):
                day(s, check=False)
                card = L(s)['pending']
                if card and card['kind'] == 'hard':
                    total += 1
                    choice = [c for c in lf.public(s)['pending']['choices'] if c['ok']][0]
                    s, _ = quick(s, 'lf_choose', id=card['id'], choice=choice['id'])
                    warm += L(s)['pending']['stage'] in ('comfort', 'gop')
                s = play(s)
        self.assertGreater(warm / total, .7)

    def test_story_off_nothing_happens(self):
        s = state(story=False)
        for _ in range(30):
            day(s)
        self.assertIsNone(L(s)['pending'])
        self.assertEqual(L(s)['log'], [])
        self.assertFalse(lf.public(s)['enabled'])
        with self.assertRaises(GameError):
            act(s, 'lf_cope', choice='ho')


class Money(unittest.TestCase):
    def test_wallet_never_negative_and_spirit_in_range(self):
        for seed in range(12):
            s = state(wallet=20, seed=seed)
            rng = random.Random(seed)
            for _ in range(60):
                day(s, 'delivery', income=rng.choice((0, 5, 30)), check=False)
                s = play(s, rng)
                self.assertGreaterEqual(s['journey']['wallet'], 0)
                self.assertTrue(0 <= L(s)['spirit'] <= 100)
                if rng.random() < .3 and L(s)['coped'] != s['journey']['life_day'] and not L(s)['pending']:
                    ok = [c for c in lf.public(s)['cope'] if c['ok']]
                    if ok:
                        s, _ = quick(s, 'lf_cope', choice=rng.choice(ok)['id'])

    def test_life_rows_in_wallet_history(self):
        s, _ = run(3, 40, rng=random.Random(3))
        rows = [h for h in s['journey']['history'] if h['kind'] == 'life']
        self.assertTrue(rows)
        self.assertIn('life', jr.HISTORY_KINDS)

    def test_paid_choices_disabled_when_poor(self):
        s = at(state(wallet=5), 6)
        x = lf.HARD_INDEX['xu_home']
        L(s)['pending'] = lf._fire_hard(s, L(s), x, 6, 'teacher')
        view = lf.public(s)['pending']
        send = next(c for c in view['choices'] if c['id'] == 'send')
        self.assertFalse(send['ok'])
        self.assertIn('Ví còn', send['why'])
        with self.assertRaises(GameError) as cm:
            act(s, 'lf_choose', id=view['id'], choice='send')
        self.assertEqual(cm.exception.code, 'not_enough')
        cope = {c['id']: c for c in lf.public(s)['cope']}
        self.assertFalse(cope['dalat']['ok'])
        self.assertTrue(cope['ho']['ok'])

    def test_forced_loss_capped_by_wallet(self):
        s = at(state(wallet=10), 6)
        card = lf._fire_hard(s, L(s), lf.HARD_INDEX['lu_bank'], 6, 'teacher')
        self.assertEqual(card['loss'], 10)
        self.assertEqual(s['journey']['wallet'], 0)

    def test_cope_once_a_day_and_hangover(self):
        s = state(wallet=100)
        for _ in range(3):
            day(s)
        L(s)['pending'] = None
        s, r = act(s, 'lf_cope', choice='nhau')
        self.assertEqual(s['journey']['wallet'], 100 + 30 - 12)
        with self.assertRaises(GameError):
            act(s, 'lf_cope', choice='ho')
        before = L(s)['spirit']
        L(s)['pending'] = None
        day(s, mode='normal', completed=0)
        self.assertLess(L(s)['spirit'], before + 1)


class Neighbours(unittest.TestCase):
    def test_scam_card_leads_to_a_collection(self):
        s = at(state(wallet=200, seed=1), 9)
        card = lf._fire_hard(s, L(s), lf.HARD_INDEX['lu_invest'], 9, 'teacher')
        L(s)['pending'] = card
        found = False
        for seed in range(20):
            t = copy.deepcopy(s)
            t['journey']['seed'] = seed
            t, _ = act(t, 'lf_choose', id=card['id'], choice='report')
            c = L(t)['pending']
            if c['stage'] == 'gop' and c['gop']['rows']:
                found = True
                before = t['journey']['wallet']
                total = c['gop']['total']
                self.assertTrue(10 <= total <= card['loss'])
                t, _ = act(t, 'lf_choose', id=c['id'], choice='take')
                self.assertEqual(t['journey']['wallet'], before + total)
                self.assertEqual(L(t)['pending']['stage'], 'done')
                self.assertIn('Cả xóm góp tiền giúp bạn', t['journey']['history'][-1]['label'])
                t, _ = act(t, 'lf_close', id=c['id'])
                self.assertIsNone(L(t)['pending'])
                break
        self.assertTrue(found)

    def test_incident_scam_loss_queues_neighbour_help(self):
        s = state(wallet=200)
        for _ in range(3):
            day(s)
        L(s)['pending'] = None
        c = s['careers']['teacher']
        c['incidents']['last'] = dict(id='inc-9', script='scam_police', choice='pay', day=4, good=False, won=None, auto=False,
                                      practice=False, lines=[dict(where='wallet', amount=-50, cat='scam_loss')], trust=-2)
        lf.after(s, 'teacher', 'inc_choose', {})
        self.assertEqual(len(L(s)['queue']), 1)
        lf.after(s, 'teacher', 'inc_choose', {})
        self.assertEqual(len(L(s)['queue']), 1)       # seen once
        day(s)
        card = L(s)['pending']
        self.assertEqual(card['kind'], 'scam')
        self.assertEqual(card['stage'], 'gop')
        self.assertEqual(card['loss'], 50)

    def test_invest_rug_pull_queues_neighbour_help(self):
        s = state(wallet=200)
        s['journey']['invest']['stats']['lost'] = 80
        day(s)
        card = L(s)['pending']
        self.assertEqual((card['kind'], card['src'], card['loss']), ('scam', 'invest', 80))

    def test_migrate_does_not_replay_old_scams(self):
        s = new_state()
        jr.enable_story(s, 5)
        iv.migrate(s)
        s['journey']['invest']['stats']['lost'] = 40
        s['careers']['grocery']['incidents']['last'] = dict(id='inc-1', script='scam_police', choice='pay', day=4, good=False,
                                                           won=None, auto=False, practice=False,
                                                           lines=[dict(where='wallet', amount=-50, cat='scam_loss')], trust=0)
        lf.migrate(s)
        lf.after(s, 'grocery', 'inc_choose', {})
        s['journey']['life_day'] += 1
        lf.on_life_day(s)
        self.assertEqual(L(s)['queue'], [])
        self.assertNotEqual((L(s)['pending'] or {}).get('kind'), 'scam')

    def test_ask_raises_bond(self):
        s = at(state(wallet=100), 8)
        card = lf._new_card(L(s), 8, 'ask', 'ask_roof', 'xom', 'ask', 'teacher')
        card['who'].append('ba_sau')
        L(s)['pending'] = card
        s, _ = act(s, 'lf_choose', id=card['id'], choice='big')
        self.assertEqual(L(s)['bonds']['ba_sau'], lf.BOND_START + 8)
        self.assertEqual(s['journey']['wallet'], 75)
        self.assertEqual(L(s)['log'][-1]['kind'], 'ask')

    def test_rumour_needs_a_real_fact_and_always_gets_comfort(self):
        s = state(wallet=100)
        self.assertEqual(lf.facts(s, 'teacher', dict(completed=1), 5), set())
        self.assertIn('late', lf.facts(s, 'teacher', dict(completed=6), 5))
        for seed in range(15):
            t = at(state(wallet=100, seed=seed), 8)
            x = next(h for h in HARD if h['cat'] == 'dat_dieu' and h['fact'] == 'late')
            card = lf._fire_hard(t, L(t), x, 8, 'teacher', gossip='co_hai_loa')
            L(t)['pending'] = card
            t, _ = act(t, 'lf_choose', id=card['id'], choice='ignore')
            c = L(t)['pending']
            self.assertEqual(c['stage'], 'comfort', seed)
            self.assertTrue(lf.COMFORT_INDEX[c['comfort']]['advice'])
            row = t['journey']['life']
            self.assertEqual(row['stats']['rumours'], 1)

    def test_low_spirit_brings_impulse_and_neighbours(self):
        kinds = set()
        for seed in range(25):
            s = state(wallet=300, seed=seed)
            for _ in range(8):
                day(s)
            for _ in range(12):
                L(s)['spirit'] = 6
                L(s)['pending'] = None
                day(s, completed=0)
                if L(s)['pending']:
                    kinds.add(L(s)['pending']['kind'])
        self.assertIn('sick', kinds)
        self.assertIn('invite', kinds)
        self.assertIn('impulse', kinds)


class Engine(unittest.TestCase):
    def test_public_state_and_end_day_summary(self):
        s = state(wallet=100)
        s['careers']['milk_tea']['started'] = True
        s['current'] = 'milk_tea'
        for _ in range(4):
            s, _ = apply_action(s, 'milk_tea', 'start_day')
            s, r = apply_action(s, 'milk_tea', 'end_day')
        self.assertIn('life', r['summary'])
        self.assertIn('spirit', r['summary']['life'])
        v = public_state(s)
        self.assertIn('life', v)
        self.assertTrue(v['life']['enabled'])
        self.assertEqual(L(s)['day'], s['journey']['life_day'])
        validate_state(s)

    def test_lf_commands_route_through_engine(self):
        s = state(wallet=100)
        for _ in range(3):
            day(s)
        L(s)['pending'] = None
        s, r = apply_action(s, None, 'lf_cope', dict(choice='me'))
        self.assertTrue(r['message'])
        self.assertEqual(L(s)['log'][-1]['kind'], 'cope')

    def test_validate_rejects_bad_life(self):
        s = state()
        L(s)['spirit'] = 101
        with self.assertRaises(GameError):
            validate_state(s)
        s = state()
        L(s)['log'].append(dict(id='x'))
        with self.assertRaises(GameError):
            validate_state(s)

    def test_log_row_shape_for_other_modules(self):
        s, _ = run(2, 30, rng=random.Random(2))
        for r in L(s)['log']:
            self.assertEqual(set(r), lf.LOG_KEYS)




class Taken(unittest.TestCase):
    def test_no_heartbreak_cards_once_engaged_or_married(self):
        L = dict(recent={})
        free = {x['cat'] for x in lf._hard_pool(L, 40, None)}
        taken = {x['cat'] for x in lf._hard_pool(L, 40, None, taken=True)}
        self.assertIn('that_tinh', free)
        self.assertNotIn('that_tinh', taken)
        self.assertEqual(free - {'that_tinh'}, taken)
        s = dict(marriage=dict(spouse=dict(status='engaged')))
        self.assertTrue(lf._taken(s))
        self.assertFalse(lf._taken(dict(marriage=dict(spouse=None))))
        self.assertFalse(lf._taken({}))


class Calling(unittest.TestCase):
    def test_a_monk_gets_no_heartbreak_beer_or_meat(self):
        L = dict(recent={}, bonds={})
        self.assertNotIn('that_tinh', {x['cat'] for x in lf._hard_pool(L, 40, 'pagoda')})
        self.assertIn('that_tinh', {x['cat'] for x in lf._hard_pool(L, 40, 'teacher')})
        cats = tuple({c for k in COMFORT for c in k['cats']})
        seen = set()
        for seed in range(300):
            for cat in cats:
                k = lf._pick_comfort({}, L, (cat,), 40, 'pagoda', random.Random(seed))
                if k:
                    seen.add(k)
        self.assertTrue(seen)
        self.assertFalse(seen & ({'work_karaoke'} | set(NOT_FOR_CALLING)), seen)
        self.assertIn('khoa_bia', {lf._pick_comfort({}, L, ('ru',), 40, 'teacher', random.Random(i)) for i in range(200)})


if __name__ == '__main__':
    unittest.main()
