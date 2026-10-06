"""Công an phường (game/careers/police.py): the briefing, the residence desk (and its envelopes), lost and found,
mediation with hidden traits, lost children, patrols (a reminder first, a report when repeated or dangerous), scam
talks, the duty phone, anh Định's first catches, the awkward people of the ward (air_odd engine), the end-of-shift
duty book, hiring, and saves (old data, forged tasks, hidden facts). No weapon, tactic or real law anywhere."""
import copy
import json
import re
import unittest

from tests.helpers import Journey
from game.careers import PLUGINS, air_odd as ao
from game.engine import GameError, new_state, apply_action, public_state, validate_state

P = PLUGINS.get('police')
if P is not None:
    from game.careers import police_content as PC

ROUGH = re.compile(r'\b(địt|đụ|đéo|lồn|cặc|buồi|đĩ)\b', re.I)
FORCE = re.compile(r'\b(súng|dùi cui|còng tay|khống chế|bắn|đánh đập|tra tấn|roi điện|điều \d+|nghị định|bộ luật|thông tư)\b', re.I)


def quiet(j):
    """No encounter and no desk surprise for the rest of today."""
    d = j.c['ext']['data']
    ao.ensure(d).update(day=j.c['day'], plan=[], fired=0, ev=None)
    d['desk'].update(day=j.c['day'], plan=[], fired=0, ev=None)


_WHERE = {}


def where(case, kind):
    """The first (day, slot) whose generated task is `case` of `kind` (tasks are pure: a test plays the real one)."""
    if (case, kind) not in _WHERE:
        _WHERE[(case, kind)] = next((d, s) for d in range(2, 400) for s in range(1, 9)
                                    if P.task_kind(d, s) == kind and (case is None or P.make_task(d, s, 1)['_v'].get('case') == case))
    return _WHERE[(case, kind)]


def at(case, kind, learned=True):
    """A journey whose active task is the generated task `case` of `kind`, shift open; anh Định gone when `learned`."""
    day, slot = where(case, kind)
    j = Journey('police', slot=slot, day=day)
    j.act('cap_intro')
    quiet(j)
    if learned:
        j.c['ext']['data']['learn']['n'] = P.LEARN
    return j


def codes(t):
    return {x['code'] for x in t.get('slips') or []}


def good_terms(j, t):
    """A deal both sides accept once both are heard (exists by construction)."""
    x = P._case_of(t)
    import itertools
    for combo in itertools.product(*[range(len(tm['options'])) for tm in x['terms']]):
        terms = {tm['id']: i for tm, i in zip(x['terms'], combo)}
        if P.accepts(t, 'a', terms) and P.accepts(t, 'b', terms):
            return terms
    return None


def solve(j, t):
    """The careful way through one task."""
    tid = t['id']
    k = t['kind']
    if k != 'brief' and not t['known']:
        j.act('ask', task=tid)
    t = j.get(tid)
    if k == 'brief':
        for e in PC.BRIEF_IDS:
            j.act('cap_read', task=tid, entry=e)
        return j.act('cap_first', task=tid, first=t['_v']['first'])
    if k == 'calls':
        for i, cid in enumerate(t['_v']['calls']):
            j.act('cap_cb', task=tid, i=i)
            j.act('cap_prio', task=tid, i=i, prio=PC.CALLS[cid]['best'])
        return j.act('cap_dispatch', task=tid)
    x = P._case_of(t)
    if k == 'desk':
        if t['needs']['press']:
            good = next(o[0] for o in PC.PRESS[t['needs']['press']]['options'] if o[2] == 'good')
            j.act('cap_press', task=tid, choice=good)
        for doc in t['needs']['docs']:
            j.act('cap_doc', task=tid, doc=doc)
        issue = P._issue(j.get(tid))
        return j.act('cap_back', task=tid, doc=issue) if issue else j.act('cap_accept', task=tid)
    if k == 'lost':
        j.act('cap_count', task=tid)
        for q in ('inside', 'id', 'color'):
            j.act('cap_lq', task=tid, q=q)
        return j.act('cap_give' if x['genuine'] else 'cap_keep', task=tid)
    if k == 'dispute':
        j.act('cap_hear', task=tid, side='a')
        j.act('cap_hear', task=tid, side='b')
        j.act('cap_offer', task=tid, terms=good_terms(j, j.get(tid)))
        return j.act('cap_sign', task=tid)
    if k == 'child':
        j.act('cap_calm', task=tid)
        j.act('cap_kq', task=tid, q='name')
        j.act('cap_tag', task=tid)
        j.act('cap_announce', task=tid, how='call')
        for q in ('kid', 'detail', 'id'):
            j.act('cap_verify', task=tid, q=q)
        return j.act('cap_handover' if x['genuine'] else 'cap_hold', task=tid)
    if k == 'patrol':
        for i, sid in enumerate(t['_v']['scenes']):
            j.act('cap_look', task=tid, i=i)
            good = next(o[0] for o in PC.SCENES[sid]['options'] if o[2] == 'good')
            j.act('cap_act', task=tid, i=i, choice=good)
        return j.act('cap_endpatrol', task=tid)
    if k == 'talk':
        j.act('cap_invite', task=tid)
        for tp in x['want']:
            j.act('cap_topic', task=tid, topic=tp)
        j.act('cap_present', task=tid)
        r = None
        for q in x['qs']:
            good = next(o[0] for o in PC.TALK_Q[q]['options'] if o[2] == 'good')
            r = j.act('cap_answer', task=tid, q=q, option=good)
        return r


def settle(j):
    """Answer a desk surprise or an encounter the careful way."""
    for _ in range(10):
        d = j.c['ext']['data']
        if d['desk']['ev']:
            x = next(s for s in PC.DESK if s['id'] == d['desk']['ev']['script'])
            good = next((o['id'] for o in x['options'] if o.get('good') is True), x['options'][0]['id'])
            j.act('cap_desk', option=good)
            continue
        if d['odd']['ev']:
            x = next(s for s in PC.ODD if s['id'] == d['odd']['ev']['script'])
            if x['kind'] == 'bargain':
                j.act('cap_odd', tone='firm', say=['rule'], to='company', n=0)
            else:
                w = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'demand': ['rule', 'alt'], 'corner': ['speak', 'rule']}[x['kind']]
                to = 'self' if x['rank'] == 'kin' else 'company' if x['kind'] in ('harass', 'corner') else 'self'
                j.act('cap_odd', tone='firm', say=w, to=to)
            continue
        break


def play_days(days):
    j = Journey('police')
    j.act('cap_intro')
    for _ in range(days):
        for _ in range(7):
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
            j.act('cap_log', lines=[f['id'] for f in facts if f['true']])
        j.act('end_day', carry_event=True)
        j.act('start_day')
        validate_state(json.loads(json.dumps(j.state)))
    return j


def walk(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from walk(v)


@unittest.skipIf(P is None, 'police filtered out')
class Content(unittest.TestCase):
    def test_spec_and_registration(self):
        self.assertEqual(P.SPEC['prefix'], 'cap_')
        prefixes = [m.SPEC['prefix'] for cid, m in PLUGINS.items() if cid != 'police']
        self.assertFalse(any(p.startswith('cap') or 'cap_'.startswith(p) for p in prefixes))
        self.assertTrue(5 <= len(P.PEOPLE) <= 8)
        self.assertEqual(len(P.SPEC['staff']), 4)
        self.assertEqual(len(P.SPEC['stories']), 3)
        self.assertTrue(5 <= len(P.SPEC['situations']) <= 8)
        from game.journey import CH_UNLOCKS
        self.assertIn('police', CH_UNLOCKS[4])
        from game import certificates as ct
        self.assertEqual(ct.group_of('police'), 'ward_service')
        from game.promotion_content import EMP_TITLES
        self.assertEqual(len(EMP_TITLES['police']), 4)

    def test_many_awkward_people(self):
        ids = [x['id'] for x in PC.ODD]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(PC.ODD), 40)
        self.assertGreaterEqual(len(PC.DESK), 12)
        kinds = {x['kind'] for x in PC.ODD}
        self.assertLessEqual({'charm', 'harass', 'demand', 'corner', 'bargain'}, kinds)
        self.assertLessEqual({'pax', 'crew', 'boss', 'kin'}, {x['rank'] for x in PC.ODD})
        marks = {x['follow'] for x in PC.ODD if x.get('follow')}
        for x in PC.ODD:
            self.assertIn(x['kind'], ao.KINDS, x['id'])
            self.assertIn(x['rank'], ao.RANKS, x['id'])
            self.assertGreaterEqual(len(x['push']), 2, x['id'])
            self.assertLessEqual(set(x.get('words', {})), set(ao.WORDS[x['kind']]), x['id'])
            if x.get('need_mark'):
                self.assertIn(x['need_mark'], marks, x['id'])
            if x['kind'] == 'bargain':
                self.assertTrue(0 <= x['limit'] < x['ask'] and x['unit'], x['id'])
            if x.get('npc') is not None:
                self.assertLess(x['npc'], len(P.PEOPLE))
        # The owner's list: envelope, an official's relative, karaoke, the daily suspect, a TikToker, a drunk uncle,
        # the chatty grandmother, a fake report, a boss chasing quotas.
        for sid in ('cap-envelope', 'cap-vip', 'cap-karaoke-night', 'cap-suspect', 'cap-live-desk', 'cap-drunk', 'cap-nam-chat',
                    'cap-fake-report', 'cap-kpi'):
            self.assertIn(sid, ids)

    def test_words_stay_pg13_without_force_or_real_law(self):
        texts = list(walk([PC.ODD, PC.DESK, PC.SITUATIONS, PC.BRIEF, PC.DESKS, PC.PRESS, PC.LOSTS, PC.DISPUTES, PC.CHILDREN, PC.SCENES,
                           PC.TOPICS, PC.TALK_Q, PC.TALKS, PC.CALLS, PC.INTRO, PC.REG_STORY, P.SPEC]))
        self.assertGreater(len(texts), 800)
        for s in texts:
            self.assertFalse(ROUGH.search(s), s)
            self.assertFalse(FORCE.search(s), s)

    def test_tasks_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 15):
            for slot in range(0, 7):
                a, b = P.make_task(day, slot, 1), P.make_task(day, slot, 99)
                self.assertEqual({k: a[k] for k in P.FIXED}, {k: b[k] for k in P.FIXED})
                self.assertEqual(a['kind'], b['kind'])
        self.assertEqual(P.task_kind(5, 0), 'brief')
        flag = P.flag_of(5)
        self.assertEqual(P.task_kind(5, 1), PC.FLAG_TASK[flag][0])
        self.assertEqual(P.make_task(5, 1, 1)['_v']['case'], PC.FLAG_TASK[flag][1])
        seen = {P.task_kind(d, s) for d in range(1, 40) for s in range(0, 7)}
        self.assertEqual(seen, set(P.KINDS))

    def test_every_case_comes_up(self):
        cases, scenes, calls = set(), set(), set()
        for day in range(1, 301):
            for slot in range(0, 8):
                t = P.make_task(day, slot, 1)
                cases.add(t['_v'].get('case'))
                scenes.update(t['_v'].get('scenes') or [])
                calls.update(t['_v'].get('calls') or [])
        for rows in (PC.DESKS, PC.LOSTS, PC.DISPUTES, PC.CHILDREN, PC.PATROLS, PC.TALKS):
            self.assertLessEqual(set(rows), cases)
        self.assertEqual(scenes, set(PC.SCENES))
        self.assertEqual(calls, set(PC.CALLS))

    def test_a_deal_always_exists_once_both_sides_are_heard(self):
        for case in PC.DISPUTES:
            j = at(case, 'dispute')
            t = j.task
            j.act('ask', task=t['id'])
            j.act('cap_hear', task=t['id'], side='a')
            j.act('cap_hear', task=t['id'], side='b')
            self.assertIsNotNone(good_terms(j, j.get(t['id'])), case)

    def test_every_option_text_is_whole(self):
        for sid, x in PC.SCENES.items():
            self.assertEqual(len(x['options']), 3, sid)
            self.assertIn('good', [o[2] for o in x['options']], sid)
        for q, x in PC.TALK_Q.items():
            self.assertEqual([o[2] for o in x['options']].count('good'), 1, q)
        for k, x in PC.CALLS.items():
            self.assertIn(x['best'], PC.PRIO, k)


@unittest.skipIf(P is None, 'police filtered out')
class Hiring(unittest.TestCase):
    def test_start_day_needs_a_contract(self):
        s = new_state()
        s, _ = apply_action(s, 'police', 'select_career', {})
        with self.assertRaises(GameError) as e:
            apply_action(s, 'police', 'start_day', {})
        self.assertEqual(e.exception.code, 'not_hired')

    def test_every_posting_hires(self):
        from tests.test_employment_pipelines import applied, play_through
        for post in P.SPEC['employment']['postings']:
            s, _ = applied('police', post['id'])
            s, _ = play_through(s, 'police')
            self.assertEqual(s['careers']['police']['job']['status'], 'offer')
            validate_state(s)


@unittest.skipIf(P is None, 'police filtered out')
class Brief(unittest.TestCase):
    def test_day_one_opens_on_the_briefing(self):
        j = Journey('police')
        self.assertEqual(j.task['kind'], 'brief')
        self.assertTrue(j.task['known'])
        pub = public_state(j.state)['careers']['police']
        t = next(x for x in pub['tasks'] if x['kind'] == 'brief')
        self.assertTrue(all(e['text'] is None for e in t['needs']['entries']))
        self.assertNotIn('_v', t)
        self.assertNotIn('first', t)

    def test_read_and_start_from_the_urgent_topic(self):
        j = Journey('police')
        j.act('cap_intro')
        quiet(j)
        t = j.task
        r = solve(j, t)
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed', r)
        self.assertFalse(t.get('slips'))
        nxt = P.make_task(1, 1, 1)
        self.assertEqual(nxt['_v']['case'], 'lf-wallet')

    def test_the_wrong_first_is_caught_then_counted(self):
        j = Journey('police')
        j.act('cap_intro')
        quiet(j)
        t = j.task
        wrong = next(k for k in PC.BRIEF_IDS if k != t['_v']['first'])
        r = j.act('cap_first', task=t['id'], first=wrong)
        self.assertFalse(r.get('correct', True))
        self.assertEqual(j.get(t['id'])['status'], 'understood')
        j.act('cap_first', task=t['id'], first=wrong)
        self.assertLessEqual({'priority', 'skim'}, codes(j.get(t['id'])))


@unittest.skipIf(P is None, 'police filtered out')
class Desk(unittest.TestCase):
    def test_every_desk_case_by_the_book(self):
        for case in PC.DESKS:
            j = at(case, 'desk')
            t = j.task
            solve(j, t)
            t = j.get(t['id'])
            self.assertEqual(t['status'], 'completed', case)
            self.assertFalse(t.get('slips'), (case, t.get('slips')))

    def test_envelope_must_be_answered_first_and_taking_it_costs(self):
        j = at('ds-ok-family', 'desk')
        t = j.task
        j.act('ask', task=t['id'])
        with self.assertRaises(GameError):
            j.act('cap_accept', task=t['id'])
        pub = public_state(j.state)['careers']['police']['tasks'][0]['needs']
        self.assertEqual(pub['pressure']['title'], PC.PRESS['envelope']['title'])
        before = j.c['ext']['data']['odd']['conduct']['points']
        j.act('cap_press', task=t['id'], choice='take')
        self.assertGreater(j.c['ext']['data']['odd']['conduct']['points'], before)
        for doc in t['needs']['docs']:
            j.act('cap_doc', task=t['id'], doc=doc)
        money = j.c['money']
        j.act('cap_accept', task=t['id'])
        t = j.get(t['id'])
        self.assertIn('bribe', codes(t))
        self.assertEqual(j.c['money'], money)   # no bonus after an envelope

    def test_accepting_an_incomplete_file_and_a_needless_return(self):
        j = at('ds-host', 'desk')
        t = j.task
        j.act('ask', task=t['id'])
        j.act('cap_press', task=t['id'], choice='decline')
        j.act('cap_accept', task=t['id'])
        self.assertLessEqual({'accept_bad', 'skim'}, codes(j.get(t['id'])))
        j = at('ds-ok-sv', 'desk')
        t = j.task
        j.act('ask', task=t['id'])
        for doc in t['needs']['docs']:
            j.act('cap_doc', task=t['id'], doc=doc)
        j.act('cap_back', task=t['id'], doc='host')
        self.assertIn('needless', codes(j.get(t['id'])))

    def test_someone_elses_paper_is_a_serious_slip(self):
        j = at('ds-other', 'desk')
        t = j.task
        j.act('ask', task=t['id'])
        for doc in t['needs']['docs']:
            j.act('cap_doc', task=t['id'], doc=doc)
        j.act('cap_accept', task=t['id'])
        self.assertIn('wrong_person', codes(j.get(t['id'])))

    def test_the_vip_is_kept_in_line(self):
        j = at('ds-mismatch', 'desk')
        t = j.task
        j.act('ask', task=t['id'])
        before = j.c['ext']['data']['odd']['conduct']['points']
        j.act('cap_press', task=t['id'], choice='skip')
        self.assertIn('queue', codes(j.get(t['id'])))
        self.assertGreater(j.c['ext']['data']['odd']['conduct']['points'], before)

    def test_hidden_until_checked(self):
        j = at('ds-expired', 'desk')
        t = j.task
        pub = public_state(j.state)['careers']['police']['tasks'][0]
        self.assertIsNone(pub['needs'])
        j.act('ask', task=t['id'])
        pub = public_state(j.state)['careers']['police']['tasks'][0]
        self.assertEqual(pub['needs']['checks'], {})
        self.assertNotIn('expired', json.dumps(pub, ensure_ascii=False))


@unittest.skipIf(P is None, 'police filtered out')
class Lost(unittest.TestCase):
    def test_every_lost_case_by_the_book(self):
        for case in PC.LOSTS:
            j = at(case, 'lost')
            t = j.task
            solve(j, t)
            t = j.get(t['id'])
            self.assertEqual(t['status'], 'completed', case)
            self.assertFalse(t.get('slips'), (case, t.get('slips')))

    def test_giving_to_an_impostor_is_a_safety_slip(self):
        j = at('lf-phone', 'lost')
        t = j.task
        j.act('ask', task=t['id'])
        with self.assertRaises(GameError):
            j.act('cap_lq', task=t['id'], q='color')
        j.act('cap_count', task=t['id'])
        pub = public_state(j.state)['careers']['police']['tasks'][0]['needs']
        self.assertEqual(pub['says'], {})
        self.assertNotIn('genuine', json.dumps(pub))
        j.act('cap_give', task=t['id'])
        t = j.get(t['id'])
        self.assertIn('wrong_owner', codes(t))
        self.assertTrue(any(r['safety'] for r in t['slips']))

    def test_keeping_from_the_real_owner(self):
        j = at('lf-wallet', 'lost')
        t = j.task
        j.act('ask', task=t['id'])
        j.act('cap_count', task=t['id'])
        for q in ('inside', 'id'):
            j.act('cap_lq', task=t['id'], q=q)
        j.act('cap_keep', task=t['id'])
        self.assertIn('needless', codes(j.get(t['id'])))


@unittest.skipIf(P is None, 'police filtered out')
class Dispute(unittest.TestCase):
    def test_every_dispute_by_the_book(self):
        for case in PC.DISPUTES:
            j = at(case, 'dispute')
            t = j.task
            r = solve(j, t)
            t = j.get(t['id'])
            self.assertEqual(t['status'], 'completed', (case, r))
            self.assertFalse(t.get('slips'), (case, t.get('slips')))

    def test_sides_decide_and_three_offers_at_most(self):
        j = at('dp-karaoke', 'dispute')
        t = j.task
        j.act('ask', task=t['id'])
        extreme = {'end': 0, 'vol': 0}            # all of chú Quý's way: chị Mận refuses
        r = j.act('cap_offer', task=t['id'], terms=extreme)
        o = j.get(t['id'])['offers'][-1]
        self.assertTrue(o['a'])
        self.assertFalse(o['b'], r)
        with self.assertRaises(GameError):
            j.act('cap_sign', task=t['id'])
        j.act('cap_offer', task=t['id'], terms=extreme)
        j.act('cap_offer', task=t['id'], terms=extreme)
        with self.assertRaises(GameError):
            j.act('cap_offer', task=t['id'], terms=extreme)
        j.act('cap_refer', task=t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertIn('nodeal', codes(t))

    def test_a_threat_hardens_both_sides(self):
        j = at('dp-wall', 'dispute')
        t = j.task
        j.act('ask', task=t['id'])
        j.act('cap_hear', task=t['id'], side='a')
        j.act('cap_hear', task=t['id'], side='b')
        soft = {s: P._tol(j.get(t['id']), s, PC.DISPUTES['dp-wall'][s]['care']) for s in 'ab'}
        j.act('cap_threat', task=t['id'])
        hard = {s: P._tol(j.get(t['id']), s, PC.DISPUTES['dp-wall'][s]['care']) for s in 'ab'}
        self.assertTrue(all(hard[s] <= soft[s] for s in 'ab') and hard != soft or all(v == 0 for v in soft.values()))
        self.assertIn('threat', codes(j.get(t['id'])))

    def test_the_hidden_heard_lines(self):
        j = at('dp-dog', 'dispute')
        t = j.task
        j.act('ask', task=t['id'])
        pub = public_state(j.state)['careers']['police']['tasks'][0]['needs']
        self.assertEqual(pub['heard'], {})
        self.assertNotIn('care', json.dumps(pub))


@unittest.skipIf(P is None, 'police filtered out')
class Child(unittest.TestCase):
    def test_every_child_by_the_book(self):
        for case in PC.CHILDREN:
            j = at(case, 'child')
            t = j.task
            solve(j, t)
            t = j.get(t['id'])
            self.assertEqual(t['status'], 'completed', case)
            self.assertFalse(t.get('slips'), (case, t.get('slips')))

    def test_the_neighbour_the_parents_did_not_send(self):
        j = at('ch-tun', 'child')
        t = j.task
        j.act('ask', task=t['id'])
        j.act('cap_calm', task=t['id'])
        j.act('cap_announce', task=t['id'], how='loa')
        pub = public_state(j.state)['careers']['police']['tasks'][0]['needs']
        self.assertNotIn('genuine', json.dumps(pub))
        j.act('cap_verify', task=t['id'], q='kid')
        j.act('cap_handover', task=t['id'])
        t = j.get(t['id'])
        self.assertIn('wrong_adult', codes(t))

    def test_posting_a_childs_photo(self):
        j = at('ch-bin', 'child')
        t = j.task
        j.act('ask', task=t['id'])
        j.act('cap_calm', task=t['id'])
        r = j.act('cap_announce', task=t['id'], how='post')
        self.assertFalse(r.get('correct', True))
        self.assertIn('post', codes(j.get(t['id'])))


@unittest.skipIf(P is None, 'police filtered out')
class Patrol(unittest.TestCase):
    def test_every_patrol_by_the_book(self):
        for case in PC.PATROLS:
            j = at(case, 'patrol')
            t = j.task
            solve(j, t)
            t = j.get(t['id'])
            self.assertEqual(t['status'], 'completed', case)
            self.assertFalse(t.get('slips'), (case, t.get('slips')))
        self.assertIn('gt-cross', P.make_task(*where('pt-gate', 'patrol'), 1)['_v']['scenes'])

    def test_every_scene_option_plays(self):
        for sid, x in PC.SCENES.items():
            case = next(k for k, v in PC.PATROLS.items() if v['place'] == x['place'])
            day, slot = next((d, s) for d in range(2, 400) for s in range(1, 9)
                             if P.task_kind(d, s) == 'patrol' and sid in P.make_task(d, s, 1)['_v'].get('scenes', []))
            for o in x['options']:
                j = Journey('police', slot=slot, day=day)
                j.act('cap_intro')
                quiet(j)
                j.c['ext']['data']['learn']['n'] = P.LEARN
                t = j.task
                j.act('ask', task=t['id'])
                i = t['_v']['scenes'].index(sid)
                j.act('cap_look', task=t['id'], i=i)
                r = j.act('cap_act', task=t['id'], i=i, choice=o[0])
                self.assertTrue(r['message'], (sid, o[0]))
                cs = codes(j.get(t['id']))
                if o[2] == 'good':
                    self.assertFalse(cs, (sid, o[0]))
                elif o[2] == 'bribe':
                    self.assertIn('bribe', cs)
                else:
                    self.assertTrue(cs, (sid, o[0]))
                validate_state(json.loads(json.dumps(j.state)))
            del case

    def test_reporting_a_first_small_thing_is_overzealous(self):
        j = at('pt-market', 'patrol')
        t = j.task
        j.act('ask', task=t['id'])
        sid = next(s for s in t['_v']['scenes'] if any(o[0] == 'report' and o[2] == 'bad' for o in PC.SCENES[s]['options'])) \
            if any(any(o[0] == 'report' and o[2] == 'bad' for o in PC.SCENES[s]['options']) for s in t['_v']['scenes']) else None
        if sid is None:
            self.skipTest('no first-time scene in this patrol')
        i = t['_v']['scenes'].index(sid)
        j.act('cap_act', task=t['id'], i=i, choice='report')
        self.assertTrue({f'bad{i}', 'blind'} <= codes(j.get(t['id'])))


@unittest.skipIf(P is None, 'police filtered out')
class TalkAndCalls(unittest.TestCase):
    def test_every_talk_by_the_book(self):
        for case in PC.TALKS:
            j = at(case, 'talk')
            t = j.task
            solve(j, t)
            t = j.get(t['id'])
            self.assertEqual(t['status'], 'completed', case)
            self.assertFalse(t.get('slips'), (case, t.get('slips')))

    def test_wrong_topics_and_a_bad_answer(self):
        j = at('tk-to3', 'talk')
        t = j.task
        j.act('ask', task=t['id'])
        j.act('cap_topic', task=t['id'], topic='prize')
        j.act('cap_present', task=t['id'])
        j.act('cap_answer', task=t['id'], q='q_official', option='obey')
        self.assertLessEqual({'noinvite', 'miss', 'qbad1'}, codes(j.get(t['id'])))
        for k in ('relative', 'otp', 'link'):
            pass
        j2 = at('tk-to3', 'talk')
        t2 = j2.task
        j2.act('ask', task=t2['id'])
        for k in ('relative', 'otp', 'link'):
            j2.act('cap_topic', task=t2['id'], topic=k)
        with self.assertRaises(GameError):
            j2.act('cap_topic', task=t2['id'], topic='prize')

    def test_calls_by_the_book_and_the_one_in_danger_first(self):
        j = at('cl-scam', 'calls')
        t = j.task
        self.assertIn('nam_bank', t['_v']['calls'])
        solve(j, t)
        self.assertFalse(j.get(t['id']).get('slips'))
        j = at('cl-scam', 'calls')
        t = j.task
        j.act('ask', task=t['id'])
        for i, cid in enumerate(t['_v']['calls']):
            j.act('cap_prio', task=t['id'], i=i, prio='later')
        j.act('cap_dispatch', task=t['id'])
        cs = codes(j.get(t['id']))
        self.assertTrue(any(c.startswith('under') for c in cs))

    def test_calling_a_real_report_fake(self):
        j = at(None, 'calls')
        t = j.task
        j.act('ask', task=t['id'])
        ids = t['_v']['calls']
        for i, cid in enumerate(ids):
            best = PC.CALLS[cid]['best']
            j.act('cap_prio', task=t['id'], i=i, prio='fake' if best in ('later', 'soon') else best)
        j.act('cap_dispatch', task=t['id'])
        cs = codes(j.get(t['id']))
        if any(PC.CALLS[c]['best'] in ('later', 'soon') for c in ids):
            self.assertTrue(any(c.startswith('dismiss') for c in cs), cs)
            self.assertIn('blind', cs)


@unittest.skipIf(P is None, 'police filtered out')
class Around(unittest.TestCase):
    def test_every_surprise_option_is_playable(self):
        for x in PC.DESK:
            for o in x['options']:
                j = Journey('police')
                j.act('cap_intro')
                quiet(j)
                j.c['money'] += 50
                j.c['ops']['finance']['opening_balance'] += 50
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('cap_read', task=j.task['id'], entry='scam')
                self.assertTrue(j.act('cap_desk', option=o['id'])['message'], (x['id'], o['id']))
                validate_state(json.loads(json.dumps(j.state)))

    def test_every_encounter_answers(self):
        for x in PC.ODD:
            j = Journey('police', slot=0, day=4)
            j.act('cap_intro')
            quiet(j)
            odd = ao.ensure(j.c['ext']['data'])
            odd['seq'] += 1
            odd['ev'] = dict(id=f'odd-{odd["seq"]}', script=x['id'], day=j.c['day'], at='between', said=[])
            pub = public_state(j.state)['careers']['police']['data']['odd']['ev']
            self.assertEqual(pub['script'], x['id'])
            words = ' '.join(w['label'] for w in pub['words'])
            self.assertNotIn('ca bay', words)
            self.assertNotIn('Hãng', words)
            if x['kind'] == 'bargain':
                p = dict(tone='firm', say=['rule'], to='company', n=x['limit'])
            else:
                say = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'corner': ['speak', 'rule'], 'demand': ['rule', 'alt']}[x['kind']]
                p = dict(tone='firm', say=say, to='self' if x['rank'] == 'kin' else 'company' if x['kind'] in ('harass', 'corner', 'charm') else 'crew')
            for _ in range(3):
                if odd['ev'] is None:
                    break
                j.act('cap_odd', **p)
                odd = j.c['ext']['data']['odd']
            self.assertIsNone(odd['ev'], x['id'])
            self.assertNotEqual(odd['last']['how'], 'give', x['id'])
            validate_state(json.loads(json.dumps(j.state)))

    def test_giving_in_to_an_envelope_costs_conduct(self):
        j = Journey('police', slot=0, day=4)
        quiet(j)
        odd = ao.ensure(j.c['ext']['data'])
        odd['ev'] = dict(id='odd-1', script='cap-envelope', day=j.c['day'], at='between', said=[])
        j.act('cap_odd', tone='soft', say=['yes'], to='self')
        odd = j.c['ext']['data']['odd']
        self.assertEqual(odd['last']['how'], 'give')
        self.assertFalse(odd['last']['good'])
        self.assertGreaterEqual(odd['conduct']['points'], 3)

    def test_the_quota_is_refused_lawfully(self):
        j = Journey('police', slot=0, day=4)
        quiet(j)
        odd = ao.ensure(j.c['ext']['data'])
        odd['ev'] = dict(id='odd-1', script='cap-kpi', day=j.c['day'], at='between', said=[])
        j.act('cap_odd', tone='firm', say=['rule', 'paper'], to='company', n=0)
        odd = j.c['ext']['data']['odd']
        self.assertIsNone(odd['ev'])
        self.assertTrue(odd['last']['good'])

    def test_situations_are_playable(self):
        j = Journey('police')
        for x in P.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_duty_book_honest_and_with_a_quota_lie(self):
        for honest in (True, False):
            j = at('pt-market', 'patrol')
            t = j.task
            j.act('ask', task=t['id'])
            for i, sid in enumerate(t['_v']['scenes']):
                j.act('cap_look', task=t['id'], i=i)
                good = next(o[0] for o in PC.SCENES[sid]['options'] if o[2] == 'good')
                j.act('cap_act', task=t['id'], i=i, choice=good)
            j.act('cap_endpatrol', task=t['id'])
            facts = j.c['ext']['data']['today']['facts']
            self.assertTrue(any(not f['true'] for f in facts))     # the tempting "more reports" line
            pub = public_state(j.state)['careers']['police']['data']['today']['facts']
            self.assertTrue(all(set(f) == {'id', 'text'} for f in pub))
            pick = [f['id'] for f in facts if f['true'] or not honest]
            before = j.c['ext']['data']['odd']['conduct']['points']
            r = j.act('cap_log', lines=pick)
            today = j.c['ext']['data']['today']
            self.assertEqual(today['log'], 'ok' if honest else 'false', r['message'])
            self.assertEqual(j.c['ext']['data']['odd']['conduct']['points'] > before, not honest)
            with self.assertRaises(GameError):
                j.act('cap_log', lines=pick)

    def test_anh_dinh_catches_each_mistake_once(self):
        j = at('lf-phone', 'lost', learned=False)
        t = j.task
        j.act('ask', task=t['id'])
        j.act('cap_count', task=t['id'])
        r = j.act('cap_give', task=t['id'])
        self.assertIn('Anh Định', r['message'])
        self.assertFalse(r.get('correct', True))
        self.assertEqual(j.get(t['id'])['status'], 'in_progress')


@unittest.skipIf(P is None, 'police filtered out')
class Saves(unittest.TestCase):
    def test_round_trip_and_a_few_days(self):
        j = play_days(5)
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        self.assertGreater(j.c['ext']['data']['stats']['tasks'], 8)

    def test_validate_rejects_broken_data(self):
        j = Journey('police')
        for path, value in ((('learn', 'n'), -1), (('today', 'log'), 'maybe'), (('today', 'facts'), [dict(id='x', text='y', key=1, true=True)]),
                            (('intro',), 'yes'), (('stats', 'tasks'), 'many')):
            s = copy.deepcopy(j.state)
            node = s['careers']['police']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_validate_rejects_a_forged_task(self):
        j = at('dp-karaoke', 'dispute')
        for key, value in (('_v', dict(case='dp-wall')), ('seen', ['hear:a', 'ghost']), ('offers', [dict(terms={'end': 9, 'vol': 0}, a=True, b=True)]),
                           ('prio', {'0': 'now'}), ('acts', {'0': 'remind'}), ('topics', ['otp', 'otp']), ('press', 'take'), ('answers', {'q_x': 'a'})):
            s = copy.deepcopy(j.state)
            t = next(x for x in s['careers']['police']['tasks'] if x['id'] == j.task['id'])
            t[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_old_data_without_the_ward_book_loads(self):
        j = Journey('police')
        s = copy.deepcopy(j.state)
        d = s['careers']['police']['ext']['data']
        for k in ('odd', 'learn', 'regulars', 'desk'):
            d.pop(k, None)
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
