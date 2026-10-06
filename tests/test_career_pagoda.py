"""Chùa Gió Lành (plugin career pagoda): the morning schedule and the abbot's word, the yard, the main hall
(incense away from the curtains), guiding visitors (dress code, no "lucky bell", no fortune-telling money),
the vegetarian kitchen (swaps, allergies), the donation book counted to the xu, listening (and a crisis that
is never kept secret), the full-moon ceremony, the old and the children, incidents; the allowance is never
cut, surprises, determinism, save validation and old saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game.careers import kit, PLUGINS
from game import consequences as cq
from game.content import initial_career, make_task
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state

PG = PLUGINS.get('pagoda')
if PG is not None:
    from game.careers import pagoda_content as pc


def find(pred, days=range(1, 160), slots=range(1, 12)):
    """(day, slot) of the first job the predicate likes."""
    for d in days:
        for s in slots:
            if pred(PG.make_task(d, s, 1)):
                return d, s
    raise AssertionError('no such job')


def of(vid):
    return lambda t: t['needs']['variant'] == vid


def earned(j, tid):
    return sum(r['amount'] for r in j.c['ops']['finance']['ledger'] if r.get('ref') == tid)


class Base(unittest.TestCase):
    def setUp(self):
        if PG is None:
            raise unittest.SkipTest('pagoda is filtered out by MNL_CAREERS')
        self.j = Journey('pagoda')

    def d(self, j=None):
        return (j or self.j).c['ext']['data']

    def at(self, pred):
        day, slot = find(pred)
        return Journey('pagoda', slot=slot, day=day)

    def act(self, j, name, **p):
        r = j.act(name, **p)
        self.settle(j)
        return r

    def settle(self, j):
        ev = self.d(j)['desk']['ev']
        if ev:
            j.act('chua_desk', option=kit.desk_script(PG.DESK, ev['script'])['default'])

    def good(self, key):
        return next(o for o, k in key['options'].items() if k['q'] == 'good')

    def play_step(self, j, tid):
        """One step the careful way, from its key (a tally from the bills on the table, as a player counts)."""
        t = j.get(tid)
        st = t['needs']['steps'][t['at']]
        key = t['_key'].get(st['id'], {})
        typ = st['type']
        if typ == 'pick':
            for iid, k in key['items'].items():
                if k['ok'] is True and iid not in t['work'].get(st['id'], []):
                    self.act(j, 'chua_pick', task=tid, item=iid)
            return self.act(j, 'chua_close', task=tid)
        if typ == 'sort':
            for iid, k in key['items'].items():
                self.act(j, 'chua_put', task=tid, item=iid, bin=k['right'][0])
            return self.act(j, 'chua_close', task=tid)
        if typ == 'order':
            for x in self.order_of(st, key):
                self.act(j, 'chua_seq', task=tid, item=x)
            return self.act(j, 'chua_close', task=tid)
        if typ == 'choose':
            return self.act(j, 'chua_choose', task=tid, option=self.good(key))
        return self.act(j, 'chua_tally', task=tid, amount=sum(st['bills']))

    def best(self, j, tid, overrides=None):
        overrides = overrides or {}
        if not j.get(tid)['known']:
            self.act(j, 'ask', task=tid)
        for _ in range(60):
            t = j.get(tid)
            if t['status'] in ('completed', 'cancelled') or t['stage'] != 'work':
                break
            st = t['needs']['steps'][t['at']]
            if st['id'] in overrides:
                overrides[st['id']](j, tid, st, t['_key'].get(st['id'], {}))
                continue
            self.play_step(j, tid)
        return j.get(tid)

    def until(self, j, tid, sid):
        """Play carefully up to step `sid`."""
        if not j.get(tid)['known']:
            self.act(j, 'ask', task=tid)
        while j.get(tid)['needs']['steps'][j.get(tid)['at']]['id'] != sid:
            self.play_step(j, tid)
        t = j.get(tid)
        st = t['needs']['steps'][t['at']]
        return st, t['_key'][sid]

    @staticmethod
    def order_of(st, key):
        left = [i['id'] for i in st['items'] if i['id'] not in key['bad']]
        rules = [(a, b) for a, b, *_ in key['rules']]
        out = []
        while left:
            x = next(x for x in left if not any(b == x and a in left for a, b in rules))
            out.append(x)
            left.remove(x)
        return out

    def codes(self, t):
        return [r['code'] for r in cq.slips(t)]


class Spec(Base):
    def test_spec_shape(self):
        s = PG.SPEC
        self.assertEqual((s['id'], s['prefix']), ('pagoda', 'chua_'))
        self.assertTrue(6 <= len(s['people']) <= 10)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertEqual(len(s['staff']), 4)
        self.assertEqual(len(s['stories']), 3)
        self.assertTrue(3 <= len(s['situations']) <= 8)
        self.assertEqual(s['tip'], 0)
        for k in s['no_tick'] + s['free_actions'] + tuple(PG.ACTIONS):
            self.assertTrue(k.startswith('chua_'), k)

    def test_no_meta_text_and_no_asking_for_money(self):
        banned = ('NPC', 'trong game', 'người chơi', 'mô phỏng', 'giả lập', 'nhiệm vụ', 'anh/chị')
        blob = json.dumps([pc.VARIANTS, PG.DESK, PG.SITUATIONS, PG.REG_STORY, PG.INTRO, PG.SPEC['meta'], pc.NOTEBOOK, pc.MODS,
                           pc.MOD_WORD, PG.REMIND], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)
        # Asking for money, telling fortunes or "giải hạn" is only ever the wrong answer.
        for v in pc.VARIANTS:
            for st in v['steps']:
                for o in st.get('options', []):
                    if any(w in o['label'] for w in ('Nhận phong bì', 'Bịa', 'giải hạn cho')):
                        self.assertEqual(o['q'], 'bad', o['id'])

    def test_every_job_is_well_formed(self):
        self.assertEqual({v['kind'] for v in pc.VARIANTS}, set(PG.KINDS) - {'setup'})
        for v in pc.VARIANTS:
            with self.subTest(job=v['id']):
                self.assertTrue(0 <= v['npc'] < len(pc.PEOPLE))
                ids = [s['id'] for s in v['steps']]
                self.assertEqual(len(ids), len(set(ids)))
                for i, s in enumerate(v['steps']):
                    self.assertIn(s['type'], PG.STEP_TYPES)
                    if s.get('when'):
                        self.assertIn(s['when'][0], ids[:i])
                    if s['type'] == 'pick':
                        self.assertTrue(any(x['ok'] is True for x in s['items']))
                    elif s['type'] == 'choose':
                        self.assertTrue(any(o['q'] == 'good' for o in s['options']))
                        for o in s['options']:
                            if o['q'] == 'good':
                                self.assertEqual(o['sev'], 0, o['id'])
                            elif o['q'] == 'bad':
                                self.assertGreater(o['sev'], 0, o['id'])
                    elif s['type'] == 'sort':
                        bins = {b['id'] for b in s['bins']}
                        for x in s['items']:
                            self.assertTrue(set(x['right']) <= bins and set(x['wrong']) <= bins, x['id'])
                    elif s['type'] == 'order':
                        bad = {x['id'] for x in s['items'] if x['bad']}
                        for a, b, *_ in s['rules']:
                            self.assertFalse({a, b} & bad, (a, b))
                    elif s['type'] == 'tally':
                        self.assertTrue(s['bills'] and all(isinstance(b, int) and b > 0 for b in s['bills']))
                if v['kind'] == 'book':
                    self.assertIn('tally', [s['type'] for s in v['steps']])

    def test_allowance_is_modest(self):
        self.assertEqual(PG.PAY['setup'], 0)
        for k, v in PG.PAY.items():
            if k != 'setup':
                self.assertTrue(5 <= v <= 10, k)
        self.assertEqual(set(PG.PAY), set(PG.KINDS))
        self.assertEqual(set(pc.MOD_WORD), {m['id'] for m in pc.MODS})


class Determinism(Base):
    def test_tasks_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 20):
            for slot in range(0, 12):
                a, b = PG.make_task(day, slot, 1), PG.make_task(day, slot, 99)
                a.pop('created_turn'), b.pop('created_turn')
                self.assertEqual(a, b)
                self.assertEqual(make_task('pagoda', day, slot, 1)['id'], f'pagoda-{day:04d}-{slot:02d}')

    def test_first_day_and_the_mix(self):
        self.assertEqual(PG.make_task(1, 0, 1)['kind'], 'setup')
        self.assertEqual([PG.make_task(1, s, 1)['needs']['variant'] for s in range(1, 11)], list(PG.DAY1))
        seen = {PG.make_task(d, s, 1)['needs']['variant'] for d in range(1, 120) for s in range(1, 12)}
        self.assertEqual(seen, {v['id'] for v in pc.VARIANTS}, 'every job turns up')
        for d in range(2, 30):
            plan = PG._day_plan(d)
            self.assertEqual(len(plan), 11)
            self.assertTrue(len({k for k, _ in plan}) >= 5, d)
            if PG.mod_of(d)['id'] != 'ram':
                self.assertNotIn('c_cau_an', {v for _, v in plan}, d)
                self.assertNotIn('k_ram', {v for _, v in plan}, d)

    def test_full_moon_brings_the_ceremony(self):
        d = next(d for d in range(2, 80) if PG.mod_of(d)['id'] == 'ram')
        self.assertEqual(PG._day_plan(d)[1][0], 'ceremony')


class Careful(Base):
    def test_the_first_day_done_carefully(self):
        j = self.j
        self.assertEqual(j.task['kind'], 'setup')
        for t in list(j.c['tasks']):
            if t['status'] in ('completed', 'cancelled'):
                continue
            t = self.best(j, t['id'])
            self.assertEqual(t['status'], 'completed', t['title'])
            self.assertFalse(cq.slips(t), (t['title'], cq.slips(t)))
            self.assertEqual(earned(j, t['id']), PG.PAY[t['kind']])
        validate_state(json.loads(json.dumps(j.state)))

    def test_every_job_can_be_done_cleanly(self):
        for v in pc.VARIANTS:
            with self.subTest(job=v['id']):
                j = self.at(of(v['id']))
                tid = j.task['id']
                t = self.best(j, tid)
                self.assertEqual(t['status'], 'completed')
                self.assertFalse(cq.slips(t), cq.slips(t))
                self.assertEqual(earned(j, tid), PG.PAY[v['kind']])
                validate_state(json.loads(json.dumps(j.state)))


class Mistakes(Base):
    def test_loudspeaker_at_four_is_a_manners_slip(self):
        j, tid = self.j, self.j.task['id']
        st, key = self.until(j, tid, 'kh')
        for x in self.order_of(st, key) + ['loa']:
            self.act(j, 'chua_seq', task=tid, item=x)
        self.act(j, 'chua_close', task=tid)
        self.assertIn('mn:kh.loa', self.codes(j.get(tid)))

    def test_order_close_needs_the_count_the_button_shows(self):
        # Live 06/10: "Xong" looked ready after one chore; the server refused 68 times "Còn việc chưa xếp".
        j, tid = self.j, self.j.task['id']
        st, key = self.until(j, tid, 'kh')
        pub = next(x for x in PG.public_task(j.get(tid))['needs']['steps'] if x['id'] == 'kh')
        need = len(st['items']) - len(key['bad'])
        self.assertEqual(pub['need'], need)
        self.assertTrue(all('bad' not in i for i in pub['items']))
        right = self.order_of(st, key)
        for x in right[:-1]:
            self.act(j, 'chua_seq', task=tid, item=x)
        with self.assertRaises(GameError) as e:
            j.act('chua_close', task=tid)
        self.assertIn(f'{need - 1}/{need}', str(e.exception))
        # k = n with the decoy in place of the last chore: taken, both named, nothing told before closing
        self.act(j, 'chua_seq', task=tid, item='loa')
        self.act(j, 'chua_close', task=tid)
        codes = self.codes(j.get(tid))
        self.assertIn('mn:kh.loa', codes)
        self.assertIn(f'cr:kh.miss.{right[-1]}'[:32], codes)
        validate_state(json.loads(json.dumps(j.state)))

    def test_a_slip_never_cuts_the_allowance(self):
        j = self.at(of('h_huong'))
        tid = j.task['id']

        def wrong(j, tid, st, key):
            for iid in key['items']:
                self.act(j, 'chua_put', task=tid, item=iid, bin='ban')
            self.act(j, 'chua_close', task=tid)
        t = self.best(j, tid, overrides={'cho': wrong})
        self.assertTrue(cq.safety(t))
        self.assertEqual(earned(j, tid), PG.PAY['hall'])

    def test_fish_sauce_in_the_vegetarian_kitchen_is_dishonest(self):
        j = self.at(of('k_trua'))
        tid = j.task['id']

        def wrong(j, tid, st, key):
            for iid, k in key['items'].items():
                self.act(j, 'chua_put', task=tid, item=iid, bin='dung' if iid == 'mam' else k['right'][0])
            self.act(j, 'chua_close', task=tid)
        t = self.best(j, tid, overrides={'thay': wrong})
        self.assertIn('hn:thay.mam', self.codes(t))

    def test_peanuts_for_the_allergic_guest_is_a_safety_slip(self):
        j = self.at(of('k_trua'))
        tid = j.task['id']

        def wrong(j, tid, st, key):
            for iid, k in key['items'].items():
                self.act(j, 'chua_put', task=tid, item=iid, bin='thuong' if iid == 'lan' else k['right'][0])
            self.act(j, 'chua_close', task=tid)
        t = self.best(j, tid, overrides={'phan': wrong})
        self.assertTrue(cq.safety(t))

    def test_keeping_a_crisis_secret_is_a_safety_slip(self):
        j = self.at(of('l_nang'))
        tid = j.task['id']
        t = self.best(j, tid, overrides={'giup': lambda j, tid, st, key: self.act(j, 'chua_choose', task=tid, option='giu')})
        self.assertIn('sf:giup.giu', self.codes(t))
        self.assertTrue(cq.safety(t))

    def test_the_envelope_goes_in_the_box_or_back(self):
        j = self.at(of('g_han'))
        tid = j.task['id']
        t = self.best(j, tid, overrides={'han': lambda j, tid, st, key: self.act(j, 'chua_choose', task=tid, option='nhan')})
        self.assertIn('phong_bi', t['skipped'])
        self.assertIn('hn:han.nhan', self.codes(t))


class Tally(Base):
    def test_exact_count_is_written_and_the_wallet_does_not_move(self):
        j = self.at(of('b_hom'))
        tid = j.task['id']
        st, key = self.until(j, tid, 'dem')
        self.assertNotIn('"total"', json.dumps(public_state(j.state)['careers']['pagoda'], ensure_ascii=False))
        money = j.c['money']
        r = self.act(j, 'chua_tally', task=tid, amount=sum(st['bills']))
        self.assertTrue(r['correct'])
        self.assertEqual(j.c['money'], money)
        self.assertEqual(self.d(j)['stats']['exact'], 1)

    def test_a_wrong_count_is_named_and_fixed_in_the_book(self):
        j = self.at(of('b_giay'))
        tid = j.task['id']
        st, key = self.until(j, tid, 'dem')
        money = j.c['money']
        r = self.act(j, 'chua_tally', task=tid, amount=sum(st['bills']) + 10)
        self.assertFalse(r['correct'])
        self.assertIn('hn:dem.lech', self.codes(j.get(tid)))
        self.assertEqual(j.c['money'], money)

    def test_tally_refuses_nonsense(self):
        j = self.at(of('b_hom'))
        tid = j.task['id']
        self.until(j, tid, 'dem')
        for bad in (-1, 'abc', 10 ** 6):
            with self.assertRaises(GameError):
                j.act('chua_tally', task=tid, amount=bad)


class Week(Base):
    def test_a_week_of_play_keeps_the_save_valid(self):
        j = self.j
        for day in range(1, 8):
            self.assertEqual(j.c['day'], day)
            self.assertEqual(j.task['kind'], 'setup')
            for t in [x for x in j.c['tasks'] if x['status'] not in ('completed', 'cancelled')]:
                if j.get(t['id'])['status'] in ('completed', 'cancelled'):
                    continue
                self.settle(j)
                t = self.best(j, t['id'])
                self.assertFalse(cq.slips(t), (day, t['title'], cq.slips(t)))
            validate_state(json.loads(json.dumps(j.state)))
            self.settle(j)
            j.act('end_day', carry_event=True)
            j.act('start_day')
        self.assertGreater(self.d()['stats']['jobs'], 10)
        self.assertEqual(self.d()['stats']['slips'], 0)


class Surprises(Base):
    def test_every_surprise_option_is_playable(self):
        for x in PG.DESK:
            for o in x['options']:
                j = Journey('pagoda')
                self.d(j)['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('chua_choose', task=j.task['id'], option='ghi')
                self.assertTrue(j.act('chua_desk', option=o['id'])['message'], (x['id'], o['id']))
                validate_state(json.loads(json.dumps(j.state)))

    def test_surprise_reviews_are_written_by_a_visitor_not_the_abbot_or_a_child(self):
        seen = 0
        for x in PG.DESK:
            for o in x['options']:
                rv = o['effects'].get('review')
                if not rv:
                    continue
                by = rv[2] if len(rv) > 2 else x['npc']
                self.assertNotIn(by, (0, 4), (x['id'], o['id']))     # thầy Huệ Minh, bé Na (a 4th-grader)
                j = Journey('pagoda')
                self.d(j)['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                j.act('chua_desk', option=o['id'])
                post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == 'desk-t')
                self.assertEqual(post['npc'], kit.npc_id('pagoda', by))
                seen += 1
        self.assertGreater(seen, 5)

    def test_situations_are_playable(self):
        j = self.j
        for x in PG.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)


class Saves(Base):
    def test_validate_rejects_broken_data(self):
        for path, value in ((('intro',), 'yes'), (('regulars',), {'7': {'visits': 1}}), (('stats', 'jobs'), -1), (('desk',), None)):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['pagoda']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_validate_rejects_a_forged_task(self):
        def key(t):
            t['_key'] = {}

        def at(t):
            t['at'] = 99

        def work(t):
            t['work'] = {'ghost': 1}

        def stage(t):
            t['stage'] = 'late'

        def needs(t):
            t['needs']['steps'][0]['type'] = 'haggle'
        base = self.at(of('b_hom')).state
        for forge in (key, at, work, stage, needs):
            s = copy.deepcopy(base)
            t = next(x for x in s['careers']['pagoda']['tasks'] if x['kind'] == 'book')
            forge(t)
            with self.assertRaises(GameError, msg=forge.__name__):
                validate_state(s)

    def test_old_save_without_the_pagoda_loads(self):
        s = new_state()
        s['careers'].pop('pagoda', None)
        s = migrate_state(s)
        validate_state(s)
        self.assertIn('pagoda', s['careers'])

    def test_data_from_an_older_build_fills_in(self):
        s = copy.deepcopy(self.j.state)
        d = s['careers']['pagoda']['ext']['data']
        d['stats'].pop('exact')
        d.pop('regulars')
        validate_state(s)

    def test_hidden_facts_stay_hidden(self):
        j = self.at(of('k_trua'))
        tid = j.task['id']
        self.assertIsNone(next(x for x in public_state(j.state)['careers']['pagoda']['tasks'] if x['id'] == tid)['needs'])
        j.act('ask', task=tid)
        view = next(x for x in public_state(j.state)['careers']['pagoda']['tasks'] if x['id'] == tid)
        raw = json.dumps(view, ensure_ascii=False)
        self.assertNotIn('_key', raw)
        for word in ('"ok"', '"right"', '"rules"', '"q"', '"total"', '"why"'):
            self.assertNotIn(word, raw)


@unittest.skipUnless(PLUGINS.get('pagoda'), 'pagoda is filtered out by MNL_CAREERS')
class OldStorySaves(unittest.TestCase):
    def old_save(self, chapter):
        s = new_state()
        jr.enable_story(s, 4242)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        s['careers'].pop('pagoda')
        j = s['journey']
        j['chapter'] = chapter
        j['unlocked'] = [cid for n in range(1, min(chapter, jr.LAST) + 1) for cid in jr.CH_UNLOCKS[n] if cid in s['careers']]
        j['done'] = list(range(1, chapter))
        return s

    def test_the_pagoda_joins_fresh_and_nothing_else_moves(self):
        s = self.old_save(3)
        before = {cid: json.dumps(c, sort_keys=True, ensure_ascii=False) for cid, c in s['careers'].items()}
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        self.assertEqual(json.dumps(m['careers']['pagoda'], sort_keys=True), json.dumps(initial_career('pagoda'), sort_keys=True))
        for cid, raw in before.items():
            self.assertEqual(json.dumps(m['careers'][cid], sort_keys=True, ensure_ascii=False), raw, cid)

    def test_chapter_two_opens_the_pagoda(self):
        m = migrate_state(json.loads(json.dumps(self.old_save(2))))
        self.assertTrue(jr.is_unlocked(m, 'pagoda'))
        m = migrate_state(json.loads(json.dumps(self.old_save(1))))
        self.assertFalse(jr.is_unlocked(m, 'pagoda'))


if __name__ == '__main__':
    unittest.main()
