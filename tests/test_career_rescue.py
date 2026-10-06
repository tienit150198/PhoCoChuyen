"""Nhân viên trực tổng đài cứu hộ (game/careers/rescue.py): the board at the start of the shift, calls (the script,
finding the place, calming, checking a doubtful call, sending or redirecting, safe instructions, staying on the line),
the rain-season queue, chị Thảo's first catches, the board (a unit down, units tied up by a needless trip), the awkward
people of the line (air_odd engine), the end-of-shift log, hiring, and saves (old data, forged tasks, hidden facts).
Content is procedural only: no medicine and no amount ever appears."""
import copy
import json
import re
import unittest

from tests.helpers import Journey
from game.careers import PLUGINS, air_odd as ao
from game.engine import GameError, new_state, apply_action, public_state, validate_state

R = PLUGINS.get('rescue')
if R is not None:
    from game.careers import rescue_content as RC

ROUGH = re.compile(r'\b(địt|đụ|đéo|lồn|cặc|buồi|đĩ)\b', re.I)
DOSE = re.compile(r'\d+([.,]\d+)?\s*(mg|mcg|ml|µg|ui|iu|đơn vị|viên|lần/ngày|giọt)\b', re.I)


def quiet(j):
    """No encounter and no desk surprise for the rest of today."""
    d = j.c['ext']['data']
    ao.ensure(d).update(day=j.c['day'], plan=[], fired=0, ev=None)
    d['desk'].update(day=j.c['day'], plan=[], fired=0, ev=None)


_WHERE = {}


def where(case, truth=None, **want):
    """The first (day, slot) whose generated call is `case` (with the hidden traits asked for)."""
    key = (case, truth, tuple(sorted(want.items())))
    if key not in _WHERE:
        def ok(d, s):
            if R.task_kind(d, s) != 'call':
                return False
            v = R.make_task(d, s, 1)['_v']
            return v['case'] == case and (truth is None or v['truth'] == truth) and all(v[k] == x for k, x in want.items())
        _WHERE[key] = next((d, s) for d in range(1, 600) for s in range(1, 9) if ok(d, s))
    return _WHERE[key]


def at(case, truth=None, learned=True, **want):
    """A journey whose active task is the generated call `case`, shift open, the board marked as the careful player
    marks it at the start of the shift; chị Thảo gone when `learned`."""
    day, slot = where(case, truth, **want)
    j = Journey('rescue', slot=slot, day=day)
    j.act('cu_intro')
    quiet(j)
    j.c['ext']['data']['board'] = dict(day=day, down=R.flag_unit(day), busy={}, tied=[])
    if learned:
        j.c['ext']['data']['learn']['n'] = R.LEARN
    return j


def queue_at():
    day, slot = next((d, s) for d in range(2, 400) for s in range(2, 9) if R.task_kind(d, s) == 'queue')
    j = Journey('rescue', slot=slot, day=day)
    j.act('cu_intro')
    quiet(j)
    j.c['ext']['data']['learn']['n'] = R.LEARN
    return j


def codes(t):
    return {x['code'] for x in t.get('slips') or []}


def calm(j, t):
    v = j.get(t['id'])['_v']
    for how in [v['soothe']] + [h for h in ('breathe', 'name', 'task') if h != v['soothe']]:
        if j.get(t['id'])['calm'] >= v['panic']:
            break
        j.act('cu_calm', task=t['id'], how=how)


def locate(j, t):
    x = RC.CALLS[t['_v']['case']]
    if x['addr'] == 'vague':
        j.act('cu_find', task=t['id'], how='landmark')
    elif x['addr'] == 'lost':
        if t['_v']['smart']:
            j.act('cu_find', task=t['id'], how='locate')
        else:
            j.act('cu_find', task=t['id'], how='landmark')
            j.act('cu_find', task=t['id'], how='passer')


def solve(j, t, stay=None):
    """The careful way through one task."""
    tid = t['id']
    if t['kind'] == 'shift':
        for u in RC.UNIT_IDS:
            j.act('cu_radio', task=tid, unit=u)
        return j.act('cu_sign', task=tid, down=t['_v']['down'])
    if not t['known']:
        j.act('ask', task=tid)
    if t['kind'] == 'queue':
        for i, k in enumerate(t['_v']['lines']):
            j.act('cu_listen', task=tid, i=i)
            j.act('cu_color', task=tid, i=i, prio=RC.LINES[k]['best'])
        return j.act('cu_sort', task=tid)
    x = RC.CALLS[t['_v']['case']]
    v = t['_v']
    calm(j, t)
    j.act('cu_ask', task=tid, q='where')
    if x['hang'] or x['cat'] == 'doubt':
        j.act('cu_verify', task=tid, how='recall')
    locate(j, j.get(tid))
    for q in ('what', 'who', 'danger', 'phone'):
        j.act('cu_ask', task=tid, q=q)
    if v['truth'] == 'real':
        j.act('cu_send', task=tid, prio=x['prio'], teams=list(x['teams']))
    else:
        j.act('cu_redirect', task=tid, to=x['to'], tone='firm')
    for k in x['key']:
        j.act('cu_tell', task=tid, card=k)
    return j.act('cu_close', task=tid, stay=bool(x['stay'] and v['truth'] == 'real') if stay is None else stay)


def settle(j):
    """Answer a desk surprise or an encounter the careful way."""
    for _ in range(10):
        d = j.c['ext']['data']
        if d['desk']['ev']:
            x = next(s for s in RC.DESK if s['id'] == d['desk']['ev']['script'])
            good = next((o['id'] for o in x['options'] if o.get('good') is True), x['options'][0]['id'])
            j.act('cu_desk', option=good)
            continue
        if d['odd']['ev']:
            x = next(s for s in RC.ODD if s['id'] == d['odd']['ev']['script'])
            if x['kind'] == 'bargain':
                j.act('cu_odd', tone='firm', say=['rule'] if 'rule' in x.get('words', {}) else ['paper'], to='company', n=0)
            else:
                w = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'demand': ['rule', 'alt'], 'corner': ['speak', 'rule']}[x['kind']]
                to = 'self' if x['rank'] == 'kin' else 'company' if x['kind'] in ('harass', 'corner') else 'self'
                j.act('cu_odd', tone='firm', say=w, to=to)
            continue
        break


def play_days(days):
    j = Journey('rescue')
    j.act('cu_intro')
    for _ in range(days):
        for _ in range(8):
            settle(j)
            open_ = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred')]
            if not open_:
                if j.c['day_completed'] >= 5:
                    break
                j.act('more_work')
                continue
            solve(j, open_[0])
        settle(j)
        facts = j.c['ext']['data']['today']['facts']
        if facts:
            j.act('cu_report', lines=[f['id'] for f in facts if f['true']])
        j.act('end_day', carry_event=True)
        j.act('start_day')
        validate_state(json.loads(json.dumps(j.state)))
    return j


@unittest.skipIf(R is None, 'rescue filtered out')
class Content(unittest.TestCase):
    def test_spec_and_registration(self):
        self.assertEqual(R.SPEC['prefix'], 'cu_')
        prefixes = [m.SPEC['prefix'] for cid, m in PLUGINS.items() if cid != 'rescue']
        self.assertNotIn('cu_', prefixes)
        self.assertTrue(5 <= len(R.PEOPLE) <= 8)
        self.assertEqual(len(R.SPEC['staff']), 4)
        self.assertEqual(len(R.SPEC['stories']), 3)
        self.assertTrue(5 <= len(R.SPEC['situations']) <= 8)
        from game.journey import CH_UNLOCKS
        self.assertIn('rescue', CH_UNLOCKS[4])
        from game import certificates as ct
        self.assertEqual(ct.group_of('rescue'), 'emergency_call')
        from game.careers import ORDER
        # Added after nurse; in 1.8.1 the new careers follow in merge order (lighthouse, rescue, lifeguard, …).
        self.assertIn('rescue', ORDER[ORDER.index('nurse') + 1:])

    def test_many_awkward_people(self):
        ids = [x['id'] for x in RC.ODD]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(RC.ODD), 40)
        self.assertGreaterEqual(len(RC.DESK), 12)
        self.assertLessEqual({'charm', 'harass', 'demand', 'corner', 'bargain'}, {x['kind'] for x in RC.ODD})
        self.assertLessEqual({'pax', 'crew', 'boss', 'kin'}, {x['rank'] for x in RC.ODD})
        marks = {x['follow'] for x in RC.ODD if x.get('follow')}
        for x in RC.ODD:
            self.assertIn(x['kind'], ao.KINDS, x['id'])
            self.assertIn(x['rank'], ao.RANKS, x['id'])
            self.assertGreaterEqual(len(x['push']), 2, x['id'])
            self.assertLessEqual(set(x.get('words', {})), set(ao.WORDS[x['kind']]), x['id'])
            if x.get('need_mark'):
                self.assertIn(x['need_mark'], marks, x['id'])
            if x['kind'] == 'bargain':
                self.assertTrue(0 <= x['limit'] < x['ask'] and x['unit'], x['id'])
            if x.get('npc') is not None:
                self.assertLess(x['npc'], len(R.PEOPLE))
        # The annoying callers on the line itself, beside the encounters.
        junk = [k for k, x in RC.CALLS.items() if x['cat'] in ('junk', 'doubt')]
        self.assertGreaterEqual(len(junk), 15)

    def test_calls_are_consistent(self):
        for k, x in RC.CALLS.items():
            with self.subTest(case=k):
                self.assertEqual(x['id'], k)
                self.assertEqual(set(x['ans']) - {'landmark'}, set(RC.Q_IDS))
                self.assertLessEqual(set(x['cards']), set(RC.INSTR))
                self.assertLessEqual(set(x['key']), set(x['cards']) - RC.BAD)
                self.assertTrue(set(x['cards']) & RC.BAD or not x['cards'] or x['cat'] == 'junk' or k in ('r-puppy',))
                self.assertLessEqual(set(x['teams']) | set(x['ok_teams']), set(RC.UNIT_IDS))
                self.assertIn(x['soothe'], ('breathe', 'name', 'task'))
                if x['cat'] in ('real', 'doubt'):
                    self.assertIn(x['prio'], R.SEND_PRIO)
                    self.assertTrue(x['teams'])
                if x['cat'] in ('junk', 'doubt'):
                    self.assertIn(x['to'], RC.REDIRECT)
                    self.assertLessEqual(set(x['ok_to']), set(RC.REDIRECT))
                if x['cat'] == 'doubt':
                    self.assertTrue(0 < x['real'] < 1)
                    for how in RC.VERIFY:
                        self.assertEqual(set(x['clues'][how]), {'real', 'fake'})
                if x['addr'] == 'vague':
                    self.assertTrue(x['ans'].get('landmark'))
                if x['addr'] == 'lost':
                    self.assertEqual(set(x['lost']), {'locate', 'no_locate', 'passer'})
        for b in RC.BAD:
            self.assertIn(b, RC.HARM)
        self.assertEqual(set(RC.REAL_ROTATION) | set(RC.DOUBT_ROTATION) | set(RC.JUNK_ROTATION), set(RC.CALLS))

    def test_words_stay_pg13_and_never_give_a_dose(self):
        def walk(o):
            if isinstance(o, str):
                yield o
            elif isinstance(o, dict):
                for v in o.values():
                    yield from walk(v)
            elif isinstance(o, (list, tuple)):
                for v in o:
                    yield from walk(v)
        texts = list(walk([RC.ODD, RC.DESK, RC.SITUATIONS, RC.CALLS, RC.INSTR, RC.HARM, RC.LINES, RC.UNIT_NOTES, RC.INTRO, RC.REG_STORY, R.SPEC]))
        self.assertGreater(len(texts), 800)
        for s in texts:
            self.assertFalse(ROUGH.search(s), s)
            self.assertFalse(DOSE.search(s), s)

    def test_tasks_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 15):
            for slot in range(0, 8):
                a, b = R.make_task(day, slot, 1), R.make_task(day, slot, 99)
                self.assertEqual({k: a[k] for k in R.FIXED}, {k: b[k] for k in R.FIXED})
                self.assertEqual(a['kind'], b['kind'])
        self.assertEqual(R.task_kind(5, 0), 'shift')
        self.assertEqual(R.make_task(5, 0, 1)['_v']['down'], R.flag_unit(5))
        self.assertEqual({R.task_kind(d, s) for d in range(1, 40) for s in range(0, 8)}, set(R.KINDS))

    def test_every_call_comes_up_and_doubt_goes_both_ways(self):
        seen, truths = set(), set()
        for day in range(1, 250):
            for slot in range(1, 8):
                if R.task_kind(day, slot) == 'call':
                    v = R.make_task(day, slot, 1)['_v']
                    seen.add(v['case'])
                    if RC.CALLS[v['case']]['cat'] == 'doubt':
                        truths.add((v['case'], v['truth']))
        self.assertEqual(seen, set(RC.CALLS))
        for k in RC.DOUBT_ROTATION:
            self.assertIn((k, 'real'), truths)
            self.assertIn((k, 'fake'), truths)

    def test_day_one_is_gentle(self):
        cats = [RC.CALLS[R.make_task(1, s, 1)['_v']['case']]['cat'] for s in range(1, 8)]
        self.assertEqual(cats, list(R.DAY1))
        self.assertTrue(all(R.task_kind(1, s) == 'call' for s in range(1, 8)))


@unittest.skipIf(R is None, 'rescue filtered out')
class Hiring(unittest.TestCase):
    def test_start_day_needs_a_contract(self):
        s = new_state()
        s, _ = apply_action(s, 'rescue', 'select_career', {})
        with self.assertRaises(GameError) as e:
            apply_action(s, 'rescue', 'start_day', {})
        self.assertEqual(e.exception.code, 'not_hired')

    def test_every_posting_hires(self):
        from tests.test_employment_pipelines import applied, play_through
        for post in R.SPEC['employment']['postings']:
            s, _ = applied('rescue', post['id'])
            s, _ = play_through(s, 'rescue')
            self.assertEqual(s['careers']['rescue']['job']['status'], 'offer')
            validate_state(s)


@unittest.skipIf(R is None, 'rescue filtered out')
class Board(unittest.TestCase):
    def test_day_one_opens_on_the_board(self):
        j = Journey('rescue')
        self.assertEqual(j.task['kind'], 'shift')
        self.assertTrue(j.task['known'])
        pub = public_state(j.state)['careers']['rescue']
        t = next(x for x in pub['tasks'] if x['kind'] == 'shift')
        self.assertTrue(all(u['note'] is None for u in t['needs']['units']))
        self.assertNotIn('_v', t)
        self.assertNotIn('down', t)

    def test_radio_all_and_mark_the_down_unit(self):
        j = Journey('rescue')
        j.act('cu_intro')
        quiet(j)
        t = j.task
        r = solve(j, t)
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertTrue(r['celebrate'])
        self.assertEqual(j.c['ext']['data']['board']['down'], t['_v']['down'])
        board = public_state(j.state)['careers']['rescue']['data']['board']
        self.assertEqual([u['id'] for u in board if u['state'] == 'down'], [t['_v']['down']])

    def test_a_wrong_mark_is_caught_then_counted(self):
        j = Journey('rescue')
        j.act('cu_intro')
        quiet(j)
        t = j.task
        r = j.act('cu_sign', task=t['id'], down='none')
        self.assertIn('Chị Thảo', r['message'])
        self.assertEqual(j.get(t['id'])['status'], 'understood')
        j.act('cu_sign', task=t['id'], down='none')
        self.assertEqual(codes(j.get(t['id'])), {'unmarked', 'skim'})

    def test_an_unmarked_down_unit_costs_minutes_a_marked_one_does_not(self):
        for marked in (True, False):
            j = at('r-oilpan')
            down = R.flag_unit(j.c['day'])
            j.c['ext']['data']['board'] = dict(day=j.c['day'], down=down if marked else None, busy={}, tied=[])
            t = j.task
            j.act('ask', task=t['id'])
            calm(j, t)
            j.act('cu_ask', task=t['id'], q='where')
            j.act('cu_ask', task=t['id'], q='what')
            r = j.act('cu_send', task=t['id'], prio='p1', teams=['fire', down] if down != 'fire' else ['fire'])
            self.assertEqual('board' in codes(j.get(t['id'])), not marked, r['message'])

    def test_a_needless_trip_ties_the_unit_up_for_the_next_real_call(self):
        j = at('n-cat')
        t = j.task
        j.act('ask', task=t['id'])
        j.act('cu_ask', task=t['id'], q='where')
        j.act('cu_ask', task=t['id'], q='what')
        j.act('cu_send', task=t['id'], prio='p1', teams=['fire'])
        b = j.c['ext']['data']['board']
        self.assertEqual(b['busy'].get('fire'), R.AWAY)
        self.assertIn('fire', b['tied'])
        j.act('cu_close', task=t['id'], stay=False)
        self.assertIn('waste', codes(j.get(t['id'])))
        self.assertEqual(j.c['ext']['data']['board']['busy'].get('fire'), R.AWAY - 1)
        # The next real call needs the fire team: away on a needless trip it waits for the next ward (a slip);
        # away on a real call the next ward helps (no slip).
        for tied in (True, False):
            j = at('r-oilpan')
            day = j.c['day']
            j.c['ext']['data']['board'] = dict(day=day, down=R.flag_unit(day), busy={'fire': 1}, tied=['fire'] if tied else [])
            t = j.task
            j.act('ask', task=t['id'])
            calm(j, t)
            j.act('cu_ask', task=t['id'], q='where')
            j.act('cu_ask', task=t['id'], q='what')
            r = j.act('cu_send', task=t['id'], prio='p1', teams=['fire'])
            self.assertEqual('tied' in codes(j.get(t['id'])), tied, r['message'])
            self.assertNotIn('fire', j.c['ext']['data']['board']['tied'])


@unittest.skipIf(R is None, 'rescue filtered out')
class Calls(unittest.TestCase):
    def test_hidden_until_picked_up(self):
        j = at('r-oilpan')
        pub = next(x for x in public_state(j.state)['careers']['rescue']['tasks'] if x['id'] == j.task['id'])
        self.assertEqual(set(pub['needs']), {'line', 'time'})
        self.assertNotIn('_v', pub)
        j.act('ask', task=j.task['id'])
        pub = next(x for x in public_state(j.state)['careers']['rescue']['tasks'] if x['id'] == j.task['id'])
        self.assertNotIn('_v', pub)
        for secret in ('truth', 'panic', 'mood', 'soothe', 'smart', 'teams', 'prio', 'key', 'stay'):
            self.assertNotIn(secret, pub['needs'])
        self.assertEqual(pub['needs']['cards'], [])

    def test_every_call_the_careful_way_is_clean(self):
        for k, x in RC.CALLS.items():
            truths = ('real', 'fake') if x['cat'] == 'doubt' else (None,)
            for truth in truths:
                with self.subTest(case=k, truth=truth):
                    j = at(k, truth)
                    tid = j.task['id']
                    r = solve(j, j.task)
                    t = j.get(tid)
                    self.assertEqual(t['status'], 'completed')
                    self.assertFalse(t.get('slips'), (k, truth, t.get('slips'), r['message']))
                    validate_state(json.loads(json.dumps(j.state)))

    def test_where_comes_first_and_a_panicking_caller_answers_nothing(self):
        j = at('r-collapse', learned=False)
        t = j.task
        j.act('ask', task=t['id'])
        r = j.act('cu_ask', task=t['id'], q='what')
        self.assertIn('Địa chỉ trước', r['message'])
        r = j.act('cu_ask', task=t['id'], q='where')
        self.assertIn('Trấn an', r['message'])
        r = j.act('cu_ask', task=t['id'], q='where')
        self.assertEqual(j.get(t['id'])['asked'], [])
        calm(j, t)
        j.act('cu_ask', task=t['id'], q='where')
        self.assertEqual(j.get(t['id'])['asked'], ['where'])

    def test_shouting_makes_it_worse(self):
        j = at('r-collapse')
        t = j.task
        j.act('ask', task=t['id'])
        r = j.act('cu_calm', task=t['id'], how='shout')
        self.assertFalse(r.get('correct', True))
        self.assertIn('harsh', codes(j.get(t['id'])))

    def test_the_soothing_that_works_is_a_hidden_trait(self):
        seen = set()
        for day in range(1, 400):
            for slot in range(1, 8):
                if R.task_kind(day, slot) == 'call':
                    v = R.make_task(day, slot, 1)['_v']
                    if v['case'] == 'r-collapse':
                        seen.add(v['soothe'])
        self.assertGreater(len(seen), 1)

    def test_no_send_without_a_place(self):
        j = at('r-tourist')
        t = j.task
        j.act('ask', task=t['id'])
        calm(j, t)
        j.act('cu_ask', task=t['id'], q='where')
        j.act('cu_ask', task=t['id'], q='what')
        with self.assertRaises(GameError):
            j.act('cu_send', task=t['id'], prio='p1', teams=['amb'])
        locate(j, j.get(t['id']))
        j.act('cu_send', task=t['id'], prio='p1', teams=['amb'])
        self.assertEqual(j.get(t['id'])['stage'], 'decided')

    def test_a_location_link_needs_a_smartphone(self):
        for smart in (True, False):
            j = at('r-tourist', smart=smart)
            t = j.task
            j.act('ask', task=t['id'])
            calm(j, t)
            j.act('cu_ask', task=t['id'], q='where')
            j.act('cu_find', task=t['id'], how='locate')
            self.assertEqual(R.located(j.get(t['id'])), smart)

    def test_the_line_drops_and_is_called_back(self):
        j = at('d-ba', 'fake')
        t = j.task
        j.act('ask', task=t['id'])
        calm(j, t)
        r = j.act('cu_ask', task=t['id'], q='where')
        self.assertIn('cúp', r['message'])
        with self.assertRaises(GameError):
            j.act('cu_ask', task=t['id'], q='what')
        r = j.act('cu_verify', task=t['id'], how='recall')
        self.assertIn('ăn cơm', r['message'])
        j.act('cu_ask', task=t['id'], q='what')

    def test_a_real_call_waved_off_is_a_safety_slip(self):
        j = at('d-kid', 'real')
        t = j.task
        j.act('ask', task=t['id'])
        calm(j, t)
        j.act('cu_ask', task=t['id'], q='where')
        j.act('cu_ask', task=t['id'], q='what')
        j.act('cu_verify', task=t['id'], how='listen')
        j.act('cu_redirect', task=t['id'], to='adult', tone='firm')
        r = j.act('cu_close', task=t['id'], stay=False)
        t = j.get(t['id'])
        self.assertIn('missed', codes(t))
        self.assertFalse(r['correct'])

    def test_a_prank_unchecked_is_a_guess_checked_is_clean(self):
        for check in (True, False):
            j = at('d-prank', 'fake')
            t = j.task
            j.act('ask', task=t['id'])
            j.act('cu_ask', task=t['id'], q='where')
            j.act('cu_ask', task=t['id'], q='what')
            if check:
                r = j.act('cu_verify', task=t['id'], how='listen')
                self.assertIn('cười', r['message'])
            j.act('cu_redirect', task=t['id'], to='warn', tone='firm')
            j.act('cu_close', task=t['id'], stay=False)
            self.assertEqual('guess' in codes(j.get(t['id'])), not check)

    def test_priority_and_teams(self):
        j = at('r-bike')
        t = j.task
        j.act('ask', task=t['id'])
        calm(j, t)
        j.act('cu_ask', task=t['id'], q='where')
        locate(j, j.get(t['id']))
        for q in ('what', 'who', 'danger', 'phone'):
            j.act('cu_ask', task=t['id'], q=q)
        j.act('cu_send', task=t['id'], prio='p3', teams=['police', 'boat'])
        for k in ('neck', 'helmet'):
            j.act('cu_tell', task=t['id'], card=k)
        r = j.act('cu_close', task=t['id'], stay=True)
        c = codes(j.get(t['id']))
        self.assertLessEqual({'under_red', 'short_red', 'waste'}, c)
        self.assertFalse(r['correct'])

    def test_a_dangerous_instruction(self):
        j = at('r-oilpan')
        t = j.task
        j.act('ask', task=t['id'])
        calm(j, t)
        for q in RC.Q_IDS:
            j.act('cu_ask', task=t['id'], q=q)
        j.act('cu_send', task=t['id'], prio='p1', teams=['fire'])
        r = j.act('cu_tell', task=t['id'], card='water')
        self.assertFalse(r['correct'])
        self.assertIn('unsafe', codes(j.get(t['id'])))
        with self.assertRaises(GameError):
            j.act('cu_tell', task=t['id'], card='pry')          # not a card of this call

    def test_leaving_a_frightened_caller_alone(self):
        j = at('r-collapse')
        t = j.task
        j.act('ask', task=t['id'])
        calm(j, t)
        for q in RC.Q_IDS:
            j.act('cu_ask', task=t['id'], q=q)
        j.act('cu_send', task=t['id'], prio='p1', teams=['amb'])
        for k in ('cpr', 'door_open'):
            j.act('cu_tell', task=t['id'], card=k)
        j.act('cu_close', task=t['id'], stay=False)
        self.assertIn('left', codes(j.get(t['id'])))

    def test_tones_decided_by_the_callers_mood(self):
        out = {}
        for mood in (0, 2):
            for tone in ('soft', 'firm', 'sharp'):
                try:
                    j = at('n-taxi', mood=mood)
                except StopIteration:
                    continue
                t = j.task
                j.act('ask', task=t['id'])
                j.act('cu_ask', task=t['id'], q='where')
                j.act('cu_ask', task=t['id'], q='what')
                j.act('cu_redirect', task=t['id'], to='taxi', tone=tone)
                j.act('cu_tell', task=t['id'], card='nodrive')
                j.act('cu_close', task=t['id'], stay=False)
                out[(mood, tone)] = codes(j.get(t['id']))
        self.assertEqual(out[(2, 'firm')], set())
        self.assertIn('rude', out[(2, 'sharp')])
        self.assertIn('loop', out[(2, 'soft')])

    def test_chi_thao_catches_each_mistake_once(self):
        j = at('n-cat', learned=False)
        t = j.task
        j.act('ask', task=t['id'])
        j.act('cu_ask', task=t['id'], q='where')
        j.act('cu_ask', task=t['id'], q='what')
        r = j.act('cu_send', task=t['id'], prio='p1', teams=['fire'])
        self.assertIn('Chị Thảo', r['message'])
        self.assertEqual(j.get(t['id'])['stage'], 'open')
        j.act('cu_send', task=t['id'], prio='p1', teams=['fire'])
        self.assertEqual(j.get(t['id'])['stage'], 'decided')


@unittest.skipIf(R is None, 'rescue filtered out')
class Queue(unittest.TestCase):
    def test_the_queue_sorted_right(self):
        j = queue_at()
        t = j.task
        self.assertEqual(t['kind'], 'queue')
        self.assertTrue(any(RC.LINES[k]['best'] == 'p1' for k in t['_v']['lines']))
        pub = next(x for x in public_state(j.state)['careers']['rescue']['tasks'] if x['id'] == t['id'])
        self.assertTrue(all(q['best'] is None and 'ask' in q for q in pub['needs']['lines']))
        r = solve(j, t)
        self.assertFalse(j.get(t['id']).get('slips'), r['message'])

    def test_the_urgent_line_left_waiting(self):
        j = queue_at()
        t = j.task
        j.act('ask', task=t['id'])
        for i, k in enumerate(t['_v']['lines']):
            j.act('cu_color', task=t['id'], i=i, prio='p4' if RC.LINES[k]['best'] == 'p1' else RC.LINES[k]['best'])
        r = j.act('cu_sort', task=t['id'])
        self.assertFalse(r['correct'])
        self.assertIn('under_red', codes(j.get(t['id'])))


@unittest.skipIf(R is None, 'rescue filtered out')
class Around(unittest.TestCase):
    def test_every_surprise_option_is_playable(self):
        for x in RC.DESK:
            for o in x['options']:
                j = Journey('rescue')
                j.act('cu_intro')
                quiet(j)
                j.c['money'] += 50
                j.c['ops']['finance']['opening_balance'] += 50
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('cu_radio', task=j.task['id'], unit='fire')
                self.assertTrue(j.act('cu_desk', option=o['id'])['message'], (x['id'], o['id']))
                validate_state(json.loads(json.dumps(j.state)))

    def test_every_encounter_answers(self):
        for x in RC.ODD:
            j = Journey('rescue', slot=0, day=4)
            j.act('cu_intro')
            quiet(j)
            odd = ao.ensure(j.c['ext']['data'])
            odd['seq'] += 1
            odd['ev'] = dict(id=f'odd-{odd["seq"]}', script=x['id'], day=j.c['day'], at='between', said=[])
            pub = public_state(j.state)['careers']['rescue']['data']['odd']['ev']
            self.assertEqual(pub['script'], x['id'])
            if x['kind'] == 'charm':
                self.assertNotIn('ca bay', ' '.join(w['label'] for w in pub['words']))
            if x['kind'] == 'bargain':
                p = dict(tone='firm', say=['rule'] if 'rule' in x['words'] else ['paper'], to='company', n=x['limit'])
            else:
                say = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'corner': ['speak', 'rule'], 'demand': ['rule', 'alt']}[x['kind']]
                p = dict(tone='firm', say=say, to='self' if x['rank'] == 'kin' else 'company' if x['kind'] in ('harass', 'corner', 'charm') else 'crew')
            for _ in range(3):
                if odd['ev'] is None:
                    break
                j.act('cu_odd', **p)
                odd = j.c['ext']['data']['odd']
            self.assertIsNone(odd['ev'], x['id'])
            self.assertNotEqual(odd['last']['how'], 'give', x['id'])
            validate_state(json.loads(json.dumps(j.state)))

    def test_giving_in_is_never_rewarded(self):
        x = next(s for s in RC.ODD if s['id'] == 'ch-vip')
        j = Journey('rescue', slot=0, day=4)
        quiet(j)
        odd = ao.ensure(j.c['ext']['data'])
        odd['ev'] = dict(id='odd-1', script=x['id'], day=j.c['day'], at='between', said=[])
        j.act('cu_odd', tone='soft', say=['yes'], to='self')
        odd = j.c['ext']['data']['odd']
        self.assertEqual(odd['last']['how'], 'give')
        self.assertFalse(odd['last']['good'])
        self.assertGreaterEqual(odd['conduct']['points'], x['breach'])

    def test_situations_are_playable(self):
        j = Journey('rescue')
        for x in R.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_the_log_honest_and_with_a_lie(self):
        for honest in (True, False):
            j = at('r-gas')
            t = j.task
            j.act('ask', task=t['id'])
            calm(j, t)
            j.act('cu_ask', task=t['id'], q='where')
            j.act('cu_ask', task=t['id'], q='what')
            j.act('cu_send', task=t['id'], prio='p2', teams=['fire'])
            j.act('cu_close', task=t['id'], stay=False)            # no instruction, no phone: slips, so a tempting false line too
            facts = j.c['ext']['data']['today']['facts']
            self.assertTrue(any(not f['true'] for f in facts))
            pub = public_state(j.state)['careers']['rescue']['data']['today']['facts']
            self.assertTrue(all(set(f) == {'id', 'text'} for f in pub))
            pick = [f['id'] for f in facts if f['true'] or not honest]
            before = j.c['ext']['data']['odd']['conduct']['points']
            r = j.act('cu_report', lines=pick)
            self.assertEqual(j.c['ext']['data']['today']['report'], 'ok' if honest else 'false', r['message'])
            self.assertEqual(j.c['ext']['data']['odd']['conduct']['points'] > before, not honest)
            with self.assertRaises(GameError):
                j.act('cu_report', lines=pick)


@unittest.skipIf(R is None, 'rescue filtered out')
class Saves(unittest.TestCase):
    def test_round_trip_and_a_few_days(self):
        j = play_days(5)
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        self.assertGreater(j.c['ext']['data']['stats']['calls'], 12)
        summary = public_state(j.state)['careers']['rescue']
        self.assertTrue(summary['data']['board'])

    def test_validate_rejects_broken_data(self):
        j = Journey('rescue')
        for path, value in ((('learn', 'n'), -1), (('today', 'report'), 'maybe'), (('today', 'facts'), [dict(id='x', text='y', key=1, true=True)]),
                            (('intro',), 'yes'), (('stats', 'calls'), 'many'), (('board', 'down'), 'tank'), (('board', 'busy'), {'fire': 9}),
                            (('board', 'tied'), ['ufo'])):
            s = copy.deepcopy(j.state)
            node = s['careers']['rescue']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_validate_rejects_a_forged_task(self):
        j = at('r-oilpan')
        for key, value in (('_v', dict(R.make_task(*where('r-oilpan'), 1)['_v'], truth='fake')), ('asked', ['where', 'ghost']), ('tried', ['calm:hug']),
                           ('prio', 'p0'), ('teams', ['tank']), ('to', 'moon'), ('told', ['dance']), ('colors', {'5': 'p1'}), ('calm', 9),
                           ('stage', 'maybe')):
            s = copy.deepcopy(j.state)
            t = next(x for x in s['careers']['rescue']['tasks'] if x['id'] == j.task['id'])
            t[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_old_data_without_the_centre_book_loads(self):
        j = Journey('rescue')
        s = copy.deepcopy(j.state)
        d = s['careers']['rescue']['ext']['data']
        for k in ('odd', 'learn', 'regulars', 'desk', 'board'):
            d.pop(k, None)
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
