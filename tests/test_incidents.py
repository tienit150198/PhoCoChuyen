"""Chuyện đời: fines, police, tax, theft, scams and people across every workplace."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from game import incidents as inc
from game import journey as jr
from game.content import CAREERS
from game.engine import GameError, apply_action, public_state, validate_state, new_state
from game.incident_content import CATS, INCIDENTS, INDEX
from game.storage import Store


def ledger_ok(c):
    f = c['ops']['finance']
    return f['opening_balance'] + sum(x['amount'] for x in f['ledger']) == c['money']


def set_money(c, amount):
    c['ops']['finance']['opening_balance'] += amount - c['money']
    c['money'] = amount


def quiet(c):
    """Test fixture: nothing else on screen today (no situation, no desk surprise)."""
    ext = c.get('ext') or {}
    if 'situation' in ext:
        ext['situation'] = None
        ext['sit_day'] = c['day']
    d = ext.get('data') or {}
    if isinstance(d.get('desk'), dict):
        d['desk']['ev'] = None


def open_day(career, story=True, gender='female', seed=12345):
    s = new_state()
    if story:
        jr.enable_story(s, seed)
        s['journey']['gender'] = gender
        s['journey']['intro'] = True
        if career not in s['journey']['unlocked']:
            s['journey']['unlocked'].append(career)
    from game.employment import hired_record, required
    if required(career):
        s['careers'][career]['job'] = hired_record(career)
    s, _ = apply_action(s, career, 'select_career', {})
    s, _ = apply_action(s, career, 'start_day', {})
    c = s['careers'][career]
    quiet(c)
    c['incidents']['plan'] = None
    return s


def fire(s, career, sid):
    c = s['careers'][career]
    quiet(c)
    c['incidents']['active'] = None
    row = inc._fire(s, c, career, sid)
    validate_state(s)
    return row


def choose(s, career, option, rid=None):
    rid = rid or s['careers'][career]['incidents']['active']['id']
    return apply_action(s, career, 'inc_choose', {'id': rid, 'option': option})


def home_of(x):
    return next(c for c in x['careers'] if c in CAREERS)


def fake_c(day, mode='normal'):
    return dict(day=day, life=dict(mode=mode), incidents=inc.initial())


class Content(unittest.TestCase):
    def test_catalogue_size_and_coverage(self):
        roots = [x for x in INCIDENTS if not x['chain']]
        self.assertGreaterEqual(len(roots), 60)
        for cid in CAREERS:
            own = [x for x in roots if cid in x['careers']]
            self.assertGreaterEqual(len(own), 5, cid)
            cats = {x['cat'] for x in own}
            self.assertGreaterEqual(len(cats), 3, cid)
        self.assertEqual({x['cat'] for x in INCIDENTS}, set(CATS))

    def test_integrity(self):
        chains = {x['id'] for x in INCIDENTS if x['chain']}
        reached = set()
        for x in INCIDENTS:
            self.assertIn(x['cat'], CATS)
            self.assertTrue(2 <= len(x['options']) <= 4, x['id'])
            ids = [o['id'] for o in x['options']]
            self.assertEqual(len(ids), len(set(ids)), x['id'])
            self.assertIn(x['default'], ids, x['id'])
            if not x['chain']:   # follow-ups may be pure consequences; a fresh story always has a right way
                self.assertTrue(any(o['good'] is True or o.get('luck') and o['luck']['win']['good'] is True
                                    and o['luck']['lose']['good'] is True for o in x['options']), x['id'])
            self.assertFalse(INDEX[x['id']]['options'][ids.index(x['default'])].get('voluntary'), x['id'])
            for o in x['options']:
                for src in [o] + ([o['luck']['win'], o['luck']['lose']] if o.get('luck') else []):
                    for where, amount, cat in src.get('pay', []):
                        self.assertIn(where, ('fund', 'wallet'))
                        self.assertIsInstance(amount, int)
                        self.assertTrue(cat)
                    if src.get('follow'):
                        self.assertIn(src['follow'][0], INDEX, x['id'])
                        reached.add(src['follow'][0])
        self.assertEqual(chains - reached, set())

    def test_no_meta_words(self):
        def texts(node):
            if isinstance(node, str):
                yield node
            elif isinstance(node, dict):
                for k, v in node.items():
                    if k not in ('id', 'npc', 'careers', 'cat', 'default', 'flag', 'unflag', 'follow', 'weights'):
                        yield from texts(v)
            elif isinstance(node, (list, tuple)):
                for v in node:
                    yield from texts(v)
        dump = ' | '.join(texts(INCIDENTS)).lower()
        for w in ('npc', 'trong game', 'của game', 'ngày game', 'luật game', 'hư cấu', 'mô phỏng', 'giả lập', 'người chơi'):
            self.assertNotIn(w, dump)


class Rates(unittest.TestCase):
    def freq(self, day, mode='normal', n=400):
        hits = 0
        for seed in range(n):
            s = dict(journey=dict(seed=seed))
            hits += inc.roll_plan(s, fake_c(day, mode), 'grocery') is not None
        return hits / n

    def test_deterministic(self):
        s = dict(journey=dict(seed=7))
        a = [inc.roll_plan(s, fake_c(d), 'restaurant') for d in range(1, 30)]
        b = [inc.roll_plan(s, fake_c(d), 'restaurant') for d in range(1, 30)]
        self.assertEqual(a, b)
        other = [inc.roll_plan(dict(journey=dict(seed=8)), fake_c(d), 'restaurant') for d in range(1, 30)]
        self.assertNotEqual(a, other)

    def test_rarer_early_more_later(self):
        self.assertEqual(self.freq(1), 0)
        self.assertEqual(self.freq(2), 0)
        early, late = self.freq(4), self.freq(14)
        self.assertTrue(0.2 < early < 0.4, early)
        self.assertTrue(0.45 < late < 0.65, late)
        self.assertLess(self.freq(14, 'calm'), late - 0.15)
        self.assertGreater(self.freq(14, 'festival'), late)

    def test_plan_respects_career_day_and_calm(self):
        for seed in range(200):
            s = dict(journey=dict(seed=seed))
            for mode in ('normal', 'calm'):
                p = inc.roll_plan(s, fake_c(4, mode), 'teacher')
                if p:
                    x = INDEX[p['script']]
                    self.assertIn('teacher', x['careers'])
                    self.assertFalse(x['chain'])
                    self.assertLessEqual(x['min_day'], 4)
                    self.assertIn(p['at'], (1, 2))
                    if mode == 'calm':
                        self.assertEqual(x['tone'], 'mild')

    def test_recent_not_repeated(self):
        c = fake_c(20)
        c['incidents']['history'] = [dict(script=x['id'], day=1) for x in INCIDENTS if 'grocery' in x['careers']][:12]
        recent = {h['script'] for h in c['incidents']['history']}
        for seed in range(100):
            p = inc.roll_plan(dict(journey=dict(seed=seed)), c, 'grocery')
            if p:
                self.assertNotIn(p['script'], recent)


class Firing(unittest.TestCase):
    def test_story_off_never_plans_or_fires(self):
        s = open_day('grocery', story=False)
        c = s['careers']['grocery']
        c['day'] = 12
        c['day_completed'] = 2
        c['incidents']['plan'] = dict(day=12, at=1, script='night_breakin', fired=False)
        r = {}
        inc.after(s, c, 'grocery', 'task_select', r)
        self.assertIsNone(c['incidents']['active'])
        inc.after(s, c, 'grocery', 'start_day', r)
        self.assertIsNone(c['incidents']['plan'])

    def test_fires_through_engine_once_and_caps(self):
        s = open_day('grocery')
        c = s['careers']['grocery']
        c['day_completed'] = 1
        c['incidents']['plan'] = dict(day=c['day'], at=1, script='found_wallet', fired=False)
        t = next(t for t in c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled'))
        s, r = apply_action(s, 'grocery', 'task_select', {'task': t['id']})
        box = s['careers']['grocery']['incidents']
        self.assertEqual(box['active']['script'], 'found_wallet')
        self.assertEqual(r['incident'], box['active']['id'])
        self.assertTrue(box['plan']['fired'])
        # One open decision at a time; the plan never fires twice.
        s2, _ = apply_action(s, 'grocery', 'task_select', {'task': t['id']})
        self.assertEqual(s2['careers']['grocery']['incidents']['active']['id'], box['active']['id'])
        self.assertEqual(s2['careers']['grocery']['incidents']['seq'], 1)
        # The daily cap holds even with follow-ups waiting.
        c = s['careers']['grocery']
        c['incidents']['active'] = None
        c['incidents']['count'] = dict(day=c['day'], n=inc.DAILY_CAP)
        c['incidents']['follow'] = [dict(script='scam_caught', day=c['day'], src='x')]
        inc.after(s, c, 'grocery', 'task_select', {})
        self.assertIsNone(c['incidents']['active'])

    def test_waits_for_other_surprises_and_first_task(self):
        s = open_day('grocery')
        c = s['careers']['grocery']
        c['incidents']['plan'] = dict(day=c['day'], at=1, script='found_wallet', fired=False)
        c['day_completed'] = 0
        inc.after(s, c, 'grocery', 'task_select', {})
        self.assertIsNone(c['incidents']['active'])
        c['day_completed'] = 1
        c['ext']['situation'] = dict(stage='open', practice=False)
        inc.after(s, c, 'grocery', 'task_select', {})
        self.assertIsNone(c['incidents']['active'])
        c['ext']['situation'] = None
        c['ext']['data']['zz'] = dict(event=dict(id='e1', stage='open'))
        self.assertTrue(inc._busy(c))
        del c['ext']['data']['zz']
        inc.after(s, c, 'grocery', 'end_day', {})
        self.assertIsNone(c['incidents']['active'])
        inc.after(s, c, 'grocery', 'task_select', {})
        self.assertEqual(c['incidents']['active']['script'], 'found_wallet')

    def test_follow_up_comes_days_later(self):
        s = open_day('pharmacy')
        fire(s, 'pharmacy', 'scam_police')
        s, _ = choose(s, 'pharmacy', 'pay')
        box = s['careers']['pharmacy']['incidents']
        self.assertEqual([f['script'] for f in box['follow']], ['scam_caught'])
        self.assertGreater(box['follow'][0]['day'], s['careers']['pharmacy']['day'])


class Choices(unittest.TestCase):
    def test_every_choice_money_category_and_ledger(self):
        bases = {}
        for x in INCIDENTS:
            cid = home_of(x)
            if cid not in bases:
                bases[cid] = open_day(cid)
                set_money(bases[cid]['careers'][cid], 5000)
            for o in x['options']:
                s = copy.deepcopy(bases[cid])
                row = fire(s, cid, x['id'])
                c0 = s['careers'][cid]
                fund0, wallet0, n0, trust0 = c0['money'], s['journey']['wallet'], len(c0['ops']['finance']['ledger']), c0['incidents']['trust']
                s, r = choose(s, cid, o['id'], row['id'])
                c = s['careers'][cid]
                box = c['incidents']
                won = box['last']['won']
                res = (o['luck']['win'] if won else o['luck']['lose']) if o.get('luck') else None
                lines = inc._lines(o, res)
                want_fund = sum(a for w, a, _ in lines if w == 'fund')
                want_wallet = sum(a for w, a, _ in lines if w == 'wallet')
                self.assertEqual(c['money'] - fund0, want_fund, (x['id'], o['id']))
                wallet_rows = [h for h in s['journey']['history'] if h['kind'] == 'incident']
                self.assertEqual(s['journey']['wallet'] - wallet0, want_wallet, (x['id'], o['id']))
                new = c['ops']['finance']['ledger'][n0:]
                money_rows = [e for e in new if e['ref'] == row['id']]
                self.assertEqual(sorted((e['amount'], e['category']) for e in money_rows),
                                 sorted((a, cat) for w, a, cat in lines if w == 'fund' and a), (x['id'], o['id']))
                self.assertTrue(ledger_ok(c), (x['id'], o['id']))
                self.assertIsNone(box['active'])
                self.assertEqual(box['history'][-1]['choice'], o['id'])
                self.assertEqual(box['history'][-1]['fund'], want_fund)
                self.assertEqual(box['history'][-1]['wallet'], want_wallet)
                self.assertTrue(0 <= box['trust'] <= 100)
                self.assertTrue(r['message'])
                if want_wallet:
                    self.assertTrue(wallet_rows)

    def test_wallet_lines_really_hit_the_wallet(self):
        s = open_day('pharmacy')
        fire(s, 'pharmacy', 'scam_police')
        w0 = s['journey']['wallet']
        f0 = s['careers']['pharmacy']['money']
        s, _ = choose(s, 'pharmacy', 'pay')
        self.assertEqual(s['journey']['wallet'], w0 - 50)
        self.assertEqual(s['careers']['pharmacy']['money'], f0)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'incident')

    def test_no_double_charge(self):
        s = open_day('grocery')
        set_money(s['careers']['grocery'], 500)
        row = fire(s, 'grocery', 'fire_safety')
        s, _ = choose(s, 'grocery', 'fix', row['id'])
        snap = json.dumps(s, sort_keys=True)
        with self.assertRaises(GameError) as e:
            choose(s, 'grocery', 'fix', row['id'])
        self.assertEqual(e.exception.code, 'already_decided')
        self.assertEqual(json.dumps(s, sort_keys=True), snap)
        # A stale id never decides a newer incident either.
        row2 = fire(s, 'grocery', 'counterfeit')
        with self.assertRaises(GameError):
            choose(s, 'grocery', 'refuse', row['id'])
        self.assertEqual(s['careers']['grocery']['incidents']['active']['id'], row2['id'])

    def test_invalid_option_changes_nothing(self):
        s = open_day('grocery')
        fire(s, 'grocery', 'fire_safety')
        snap = json.dumps(s, sort_keys=True)
        for bad in ('nope', None, 5):
            with self.assertRaises(GameError):
                apply_action(s, 'grocery', 'inc_choose', {'id': s['careers']['grocery']['incidents']['active']['id'], 'option': bad})
        self.assertEqual(json.dumps(s, sort_keys=True), snap)

    def test_voluntary_cost_needs_money(self):
        s = open_day('pharmacy')
        set_money(s['careers']['pharmacy'], 10)
        fire(s, 'pharmacy', 'tax_envelope')
        pub = public_state(s)['careers']['pharmacy']['incidents']['active']
        self.assertFalse(next(o for o in pub['options'] if o['id'] == 'envelope')['affordable'])
        self.assertTrue(next(o for o in pub['options'] if o['id'] == 'refuse')['affordable'])
        with self.assertRaises(GameError) as e:
            choose(s, 'pharmacy', 'envelope')
        self.assertEqual(e.exception.code, 'not_enough')

    def test_forced_cost_overflows_to_wallet_never_overdraws(self):
        s = open_day('grocery')
        set_money(s['careers']['grocery'], 20)
        w0 = s['journey']['wallet']
        fire(s, 'grocery', 'fire_safety')
        s, _ = choose(s, 'grocery', 'fine_only')
        c = s['careers']['grocery']
        self.assertEqual(c['money'], 0)
        self.assertEqual(s['journey']['wallet'], w0 - 30)
        self.assertTrue(ledger_ok(c))
        self.assertEqual({(l['where'], l['amount']) for l in c['incidents']['last']['lines']}, {('fund', -20), ('wallet', -30)})

    def test_story_off_pays_from_fund_only(self):
        s = open_day('pharmacy', story=False)
        c = s['careers']['pharmacy']
        set_money(c, 300)
        fire(s, 'pharmacy', 'scam_police')
        pub = public_state(s)['careers']['pharmacy']['incidents']['active']
        self.assertTrue(all(st['where'] == 'fund' for o in pub['options'] for st in o['stakes']))
        s, _ = choose(s, 'pharmacy', 'pay')
        self.assertEqual(s['careers']['pharmacy']['money'], 250)

    def test_trust_flags_and_good_choice(self):
        s = open_day('teacher')
        fire(s, 'teacher', 'parent_coffee')
        t0 = s['careers']['teacher']['incidents']['trust']
        s, r = choose(s, 'teacher', 'boundary')
        box = s['careers']['teacher']['incidents']
        self.assertIs(box['last']['good'], True)
        self.assertTrue(r.get('celebrate'))
        self.assertGreaterEqual(box['trust'], t0)
        self.assertEqual(s['careers']['teacher']['metrics'].get('incidents_good'), 1)

    def test_luck_is_seeded(self):
        s = open_day('grocery')
        row = fire(s, 'grocery', 'fire_safety')
        a, _ = choose(copy.deepcopy(s), 'grocery', 'borrow', row['id'])
        b, _ = choose(copy.deepcopy(s), 'grocery', 'borrow', row['id'])
        self.assertEqual(a['careers']['grocery']['incidents']['last'], b['careers']['grocery']['incidents']['last'])
        self.assertIn(a['careers']['grocery']['incidents']['last']['won'], (True, False))


class Practice(unittest.TestCase):
    def test_replay_changes_no_money_or_trust(self):
        s = open_day('grocery')
        set_money(s['careers']['grocery'], 500)
        fire(s, 'grocery', 'fire_safety')
        s, _ = choose(s, 'grocery', 'fix')
        c = s['careers']['grocery']
        before = (c['money'], s['journey']['wallet'], c['incidents']['trust'], len(c['incidents']['history']),
                  len(c['ops']['finance']['ledger']), c['xp'])
        with self.assertRaises(GameError):
            apply_action(s, 'grocery', 'inc_practice', {'script': 'counterfeit'})   # never met here
        s, _ = apply_action(s, 'grocery', 'inc_practice', {'script': 'fire_safety'})
        self.assertTrue(s['careers']['grocery']['incidents']['active']['practice'])
        s, _ = choose(s, 'grocery', 'fine_only')
        c = s['careers']['grocery']
        self.assertEqual((c['money'], s['journey']['wallet'], c['incidents']['trust'], len(c['incidents']['history']),
                          len(c['ops']['finance']['ledger']), c['xp']), before)
        self.assertTrue(c['incidents']['last']['practice'])
        self.assertEqual(c['incidents']['follow'], [])
        s, _ = apply_action(s, 'grocery', 'inc_practice', {'script': 'fire_safety'})
        s, _ = apply_action(s, 'grocery', 'inc_close', {})
        self.assertIsNone(s['careers']['grocery']['incidents']['active'])

    def test_real_incident_cannot_be_closed_or_replaced(self):
        s = open_day('grocery')
        fire(s, 'grocery', 'fire_safety')
        s, _ = choose(s, 'grocery', 'fix')
        fire(s, 'grocery', 'counterfeit')
        with self.assertRaises(GameError):
            apply_action(s, 'grocery', 'inc_close', {})
        with self.assertRaises(GameError):
            apply_action(s, 'grocery', 'inc_practice', {'script': 'fire_safety'})


class DayEnd(unittest.TestCase):
    def test_undecided_takes_default_and_shows_in_summary(self):
        s = open_day('grocery')
        set_money(s['careers']['grocery'], 500)
        fire(s, 'grocery', 'fire_safety')
        s, r = apply_action(s, 'grocery', 'end_day', {'carry_event': True})
        box = s['careers']['grocery']['incidents']
        self.assertIsNone(box['active'])
        self.assertIsNone(box['plan'])
        self.assertEqual(box['history'][-1]['choice'], INDEX['fire_safety']['default'])
        self.assertTrue(box['history'][-1]['auto'])
        items = r['summary']['incidents']['items']
        self.assertEqual(items[0]['script'], 'fire_safety')
        self.assertTrue(items[0]['auto'])
        self.assertEqual(items[0]['fund'], -50)

    def test_quiet_day_has_no_summary_block(self):
        s = open_day('grocery')
        s, r = apply_action(s, 'grocery', 'end_day', {'carry_event': True})
        self.assertIsNone(r['summary'].get('incidents'))


class Public(unittest.TestCase):
    def test_hidden_fields_never_leak(self):
        for sid, cid in (('fire_safety', 'grocery'), ('parent_coffee', 'teacher'), ('scam_police', 'pharmacy'), ('night_breakin', 'grocery')):
            s = open_day(cid)
            fire(s, cid, sid)
            a = public_state(s)['careers'][cid]['incidents']['active']
            dump = json.dumps(a, ensure_ascii=False)
            for k in ('"good"', '"outcome"', '"luck"', '"follow"', '"trust"', '"flag"', '"default"', '"weights"'):
                self.assertNotIn(k, dump, (sid, k))
            for o in INDEX[sid]['options']:
                if o['outcome']:
                    self.assertNotIn(o['outcome'][:30], dump)

    def test_gender_variants(self):
        texts = set()
        for g in ('male', 'female', None):
            s = open_day('teacher', gender=g)
            fire(s, 'teacher', 'parent_coffee')
            texts.add(public_state(s)['careers']['teacher']['incidents']['active']['text'])
        self.assertEqual(len(texts), 3)

    def test_last_and_log(self):
        s = open_day('grocery')
        fire(s, 'grocery', 'counterfeit')
        s, _ = choose(s, 'grocery', 'refuse')
        v = public_state(s)['careers']['grocery']['incidents']
        self.assertIsNone(v['active'])
        self.assertEqual(v['last']['script'], 'counterfeit')
        self.assertTrue(v['last']['outcome'])
        self.assertEqual(v['log'][0]['script'], 'counterfeit')
        self.assertEqual(v['replay'], ['counterfeit'])


class Saves(unittest.TestCase):
    def test_old_save_migrates(self):
        s = open_day('grocery')
        for c in s['careers'].values():
            c.pop('incidents', None)
        s2, _ = apply_action(s, 'grocery', 'task_select', {'task': s['careers']['grocery']['tasks'][0]['id']})
        for cid, c in s2['careers'].items():
            self.assertEqual(c['incidents']['trust'], inc.TRUST_START, cid)
        # Partial books are filled in too.
        s3 = copy.deepcopy(s2)
        del s3['careers']['grocery']['incidents']['flags']
        inc.migrate(s3)
        validate_state(s3)

    def test_invalid_book_rejected(self):
        s = open_day('grocery')
        for mutate in (lambda b: b.update(trust=150), lambda b: b.update(active=dict(script='nope')),
                       lambda b: b['history'].append(dict(script='fire_safety', choice='zzz', day=1, good=True, won=None)),
                       lambda b: b.update(v=99)):
            bad = copy.deepcopy(s)
            mutate(bad['careers']['grocery']['incidents'])
            with self.assertRaises(GameError):
                validate_state(bad)

    def test_round_trip_store(self):
        with tempfile.TemporaryDirectory() as td:
            store = Store(Path(td) / 'i.db', story=True)
            token, _, _ = store.session()
            s, rev, _ = store.read(token)
            s['journey']['gender'] = 'male'
            with store.connect() as db:
                db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(s), store.key(token)))
            cid = s['journey']['unlocked'][0]
            store.command(token, 'req-inc-01', rev, cid, 'select_career', {})
            s, rev, _ = store.read(token)
            if not s['careers'][cid]['open']:
                store.command(token, 'req-inc-02', rev, cid, 'start_day', {})
                s, rev, _ = store.read(token)
            x = next(x for x in INCIDENTS if not x['chain'] and cid in x['careers'])
            fire(s, cid, x['id'])
            with store.connect() as db:
                db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(s), store.key(token)))
            s2, rev2, _ = store.read(token)
            self.assertEqual(s2['careers'][cid]['incidents'], s['careers'][cid]['incidents'])
            store.command(token, 'req-inc-03', rev2, cid, 'inc_choose',
                          {'id': s['careers'][cid]['incidents']['active']['id'], 'option': x['default']})
            s3, _, _ = store.read(token)
            self.assertIsNone(s3['careers'][cid]['incidents']['active'])
            self.assertEqual(s3['careers'][cid]['incidents']['history'][-1]['choice'], x['default'])


if __name__ == '__main__':
    unittest.main()
