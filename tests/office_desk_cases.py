"""Shared checks for the hands-on desks of Công ty CP Cánh Diều (game/careers/office_work.py):
hr_admin, secretary, it_helpdesk. Each career's test module mixes DeskCases into a TestCase."""
import copy
import json

from game import employment
from game.careers import PLUGINS, kit, office
from game.careers import office_work as ow
from game.engine import GameError, apply_action, new_state, public_state, validate_state
from tests.helpers import Journey

HIDDEN = ('"_bin"', '"_ok"', '"_sol"', '"_q"', '"_why"', '"_role"', '"_twist"', '"_sev"')


def perfect(t: dict) -> dict:
    """The right answer for the dossier as it is true now (after a fired change of mind)."""
    w = ow.truth(t)
    k = w['type']
    if k == 'sort':
        return {it['id']: it['_bin'] for it in w['items']}
    if k == 'mark':
        return {sg['id']: sg['_ok'] for sg in ow.segs_of(w) if sg['_ok'] != sg['keep']}
    if k == 'slots':
        return dict(w['_sol'])
    if k == 'fields':
        return {f['id']: f['_ok'] for f in w['fields']}
    if k == 'seq':
        need = [s['id'] for s in w['pool'] if s['_role'] == 'need']
        after = [(a, b) for a, b, _ in w.get('_after', []) if a in need and b in need]
        order, left = [], list(need)
        while left:
            x = next(x for x in left if not any(b == x and a in left for a, b in after))
            order.append(x)
            left.remove(x)
        return dict(order=order)
    good = next(o for o in w['options'] if o['_q'] == 'good')
    return dict(read=[f['id'] for f in w['facts']], choice=good['id'])


def roundtrip(j):
    s = json.loads(json.dumps(j.state))
    validate_state(s)
    return s


class DeskCases:
    M = None            # the career module
    CRUNCH = AUDIT = None

    @classmethod
    def setUpClass(cls):
        if cls.M.ID not in PLUGINS:
            import unittest
            raise unittest.SkipTest(cls.M.ID + ' is filtered out by MNL_CAREERS')

    @property
    def P(self):
        return self.M.P

    @property
    def forms(self):
        return [f['id'] for f in self.M.FORMS]

    def find(self, form, twist=None, day_from=1):
        for day in range(day_from, 40):
            for slot in range(6):
                if self.M.JOB.form_of(day, slot)['id'] != form:
                    continue
                if twist is not None and (self.M.make_task(day, slot, 1)['tw'] is not None) != twist:
                    continue
                return day, slot
        raise AssertionError(f'no slot for {form} twist={twist}')

    def journey(self, form, twist=None, day_from=1):
        day, slot = self.find(form, twist, day_from)
        self.j = Journey(self.M.ID, slot=slot, day=day)
        return self.j

    def data(self, j=None):
        return (j or self.j).c['ext']['data']

    def view(self, tid):
        return next(t for t in public_state(self.j.state)['careers'][self.M.ID]['tasks'] if t['id'] == tid)

    def clear_desk(self, j):
        desk = self.data(j)['desk']
        if desk['ev']:
            ev = kit.desk_public(desk, self.M.DESK, self.M.ID)['ev']
            j.act(self.P + 'desk', option=ev['options'][0]['id'])

    def fill(self, j, tid):
        """Put the right answer in through the commands, following any change of mind as it fires."""
        P = self.P
        for _ in range(4):
            t = j.get(tid)
            want = perfect(t)
            kind = t['work']['type']
            if kind == 'sort':
                todo = [(k, v) for k, v in want.items() if t['ans'].get(k) != v]
                for k, v in todo:
                    j.act(P + 'put', task=tid, item=k, bin=v)
            elif kind == 'mark':
                w = ow.truth(t)
                todo = [sg for sg in ow.segs_of(w) if t['ans'].get(sg['id'], sg['keep']) != sg['_ok']]
                for sg in todo:
                    j.act(P + 'mark', task=tid, seg=sg['id'], opt=sg['_ok'])
            elif kind == 'slots':
                todo = [k for k, v in want.items() if t['ans'].get(k) != v]
                for k in todo:
                    clash = [x for x, v in j.get(tid)['ans'].items() if v == want[k] and x != k]
                    for x in clash:
                        j.act(P + 'place', task=tid, item=x, cell=None)
                    j.act(P + 'place', task=tid, item=k, cell=want[k])
            elif kind == 'case':
                todo = [f for f in want['read'] if f not in (t['ans'].get('read') or [])]
                for f in todo:
                    j.act(P + 'read', task=tid, fact=f)
            else:
                todo = []
            if perfect(j.get(tid)) == want:
                return want
        raise AssertionError('the answer kept changing')

    def play(self, j, tid):
        """Ask, do the work right and hand it in; returns the hand-in result."""
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        for _ in range(4):
            want = self.fill(j, tid)
            kind = j.get(tid)['work']['type']
            if kind == 'case':
                return j.act(self.P + 'reply', task=tid, option=want['choice'], confirm=True)
            extra = dict(fields=want) if kind == 'fields' else dict(order=want['order']) if kind == 'seq' else {}
            r = j.act(self.P + 'file', task=tid, confirm=True, **extra)
            if not r.get('twist'):
                return r
        raise AssertionError('dossier never filed')

    # ---------------------------------------------------------------- generation
    def test_generation_deterministic_valid_and_solvable(self):
        seen = {}
        for day in range(1, 26):
            for slot in range(6):
                t = self.M.make_task(day, slot, 3)
                self.assertEqual(t, self.M.make_task(day, slot, 3))
                self.assertEqual(json.loads(json.dumps(t)), t)
                form = next(f for f in self.M.FORMS if f['id'] == t['form'])
                self.assertLessEqual(form['min_day'], day)
                seen.setdefault(t['form'], set()).add(json.dumps(t['work'], sort_keys=True, ensure_ascii=False))
                for fire in (False, True):
                    if fire and not t['tw']:
                        continue
                    x = copy.deepcopy(t)
                    x['known'] = True
                    if fire:
                        x['tw'] = 'fired'
                    x['ans'] = perfect(x)
                    ow.validate_task(x)
                    r = ow.grade(x)
                    self.assertEqual(r['errors'], [], (day, slot, t['form'], fire))
                    self.assertEqual(r['ok'], r['total'])
                    self.assertTrue(r['total'] > 0)
        self.assertEqual(set(seen), set(self.forms))
        for form, works in seen.items():
            self.assertGreaterEqual(len(works), 4, form)       # many different situations per form

    def test_mods_follow_the_office_calendar(self):
        mods = [self.M.JOB.mod(d)['id'] for d in range(1, 6)]
        cfg = self.M.JOB.cfg
        self.assertEqual(mods[1:4], [cfg['intro'][2], cfg['intro'][3], cfg['intro'][4]])
        self.assertEqual(mods[4], cfg['crunch'])
        self.assertEqual(self.M.JOB.mod(10)['id'], cfg['crunch'])
        self.assertNotIn(self.M.JOB.mod(1)['id'], (cfg['crunch'], cfg['audit']))
        for d in range(6, 30):
            self.assertIn(self.M.JOB.mod(d)['id'], [m['id'] for m in self.M.MODS])

    # ---------------------------------------------------------------- play through the commands
    def test_every_form_solvable_and_paid(self):
        for form in self.forms:
            for twist in (False, True):
                try:
                    j = self.journey(form, twist)
                except AssertionError:
                    continue
                with self.subTest(form=form, twist=twist):
                    tid = j.task['id']
                    money = j.c['money']
                    r = self.play(j, tid)
                    t = j.get(tid)
                    self.assertEqual(t['status'], 'completed')
                    self.assertTrue(t['filed'])
                    self.assertFalse(t['late'])
                    self.assertEqual(t['result']['errors'], [])
                    self.assertTrue(r.get('celebrate'))
                    if twist:
                        self.assertEqual(t['tw'], 'fired')
                    self.assertEqual(j.c['money'], money + t['bonus'])
                    post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
                    self.assertEqual(post['feedback'].get('fair', post['stars']), 5)   # a picky boss may still grumble unfairly
                    self.assertEqual({x['key'] for x in post['feedback']['criteria']}, {'accuracy', 'quality', 'care', 'speed'})
                    self.assertEqual(self.data(j)['clean'], 1)
                    roundtrip(j)

    def test_public_view_hides_answers_and_the_coming_change(self):
        j = self.journey(self.forms[0], twist=True)
        tid = j.task['id']
        v = self.view(tid)
        self.assertIsNone(v['work'])
        self.assertIsNone(v['papers'])
        j.act('ask', task=tid)
        v = self.view(tid)
        dump = json.dumps(v, ensure_ascii=False)
        for k in HIDDEN:
            self.assertNotIn(k, dump)
        self.assertIsNone(v['tw'])
        self.assertNotIn('twist', v['work'])
        self.assertEqual(v['hints_left'], ow.HINT_MAX)
        self.play(j, tid)
        v = self.view(tid)
        self.assertEqual(v['tw'], 'fired')
        self.assertIn('note', v['work']['twist'])
        self.assertTrue(v['result']['lines'])

    def test_a_call_about_a_sorted_card_puts_it_back_with_the_call_on_it(self):
        sorts = [f['id'] for f in self.M.FORMS if self.M.make_task(*self.find(f['id']), 1)['work']['type'] == 'sort']
        for form in sorts:
            try:
                j = self.journey(form, twist=True)
            except AssertionError:
                continue
            with self.subTest(form=form):
                tid = j.task['id']
                j.act('ask', task=tid)
                tw = j.get(tid)['work']['_twist']
                items = [it['id'] for it in j.get(tid)['work']['items']]
                order = [tw['item']] + [k for k in items if k != tw['item']]
                for k in order:   # the changed card first, so it is already in a tray when the call comes
                    if j.get(tid)['tw'] == 'fired':
                        break
                    j.act(self.P + 'put', task=tid, item=k, bin=j.get(tid)['work']['bins'][0]['id'])
                self.assertEqual(j.get(tid)['tw'], 'fired')
                self.assertNotIn(tw['item'], j.get(tid)['ans'])
                self.assertTrue(ow.ready(j.get(tid)))
                card = next(it for it in self.view(tid)['work']['items'] if it['id'] == tw['item'])
                self.assertIn('📞', card['note'])
                return
        self.skipTest('no sort form with a call')

    def test_case_facts_stay_hidden_until_read_and_gate_the_answer(self):
        j = self.journey('case')
        tid = j.task['id']
        j.act('ask', task=tid)
        w = j.task['work']
        self.assertTrue(all(f['text'] is None for f in self.view(tid)['work']['facts']))
        gated = next((o for o in w['options'] if o['requires']), None)
        self.assertIsNotNone(gated)
        with self.assertRaises(GameError):
            j.act(self.P + 'reply', task=tid, option=gated['id'], confirm=True)
        f = gated['requires'][0]
        j.act(self.P + 'read', task=tid, fact=f)
        facts = {x['id']: x for x in self.view(tid)['work']['facts']}
        self.assertTrue(facts[f]['text'])
        with self.assertRaises(GameError):
            j.act(self.P + 'read', task=tid, fact=f)       # once is enough
        self.assertEqual(j.task['mistakes'], 0)
        roundtrip(j)

    def test_a_harmful_answer_hurts_care_trust_and_pay(self):
        j = self.journey('case')
        tid = j.task['id']
        j.act('ask', task=tid)
        bad = next(o for o in j.task['work']['options'] if o['_q'] == 'bad')
        for f in j.task['work']['facts']:
            j.act(self.P + 'read', task=tid, fact=f['id'])
        trust = self.data()['office']['trust']
        money = j.c['money']
        r = j.act(self.P + 'reply', task=tid, option=bad['id'], confirm=True)
        t = j.get(tid)
        self.assertFalse(r['correct'])
        self.assertTrue(any(e['sev'] >= 2 for e in t['result']['errors']))
        self.assertLess(self.data()['office']['trust'], trust)
        self.assertLess(j.c['money'] - money, t['bonus'])
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
        self.assertLess(post['feedback'].get('fair', post['stars']), 5)
        roundtrip(j)

    def test_wrong_sorting_costs_bonus_and_is_explained(self):
        form = next(f['id'] for f in self.M.FORMS if self.M.make_task(*self.find(f['id'], False), 1)['work']['type'] == 'sort')
        j = self.journey(form, twist=False)
        tid = j.task['id']
        j.act('ask', task=tid)
        w = j.task['work']
        bins = [b['id'] for b in w['bins']]
        for it in w['items']:
            j.act(self.P + 'put', task=tid, item=it['id'], bin=next(b for b in bins if b != it['_bin']))
        money = j.c['money']
        trust = self.data()['office']['trust']
        r = j.act(self.P + 'file', task=tid, confirm=True)
        t = j.get(tid)
        self.assertFalse(r['correct'])
        self.assertEqual(t['result']['ok'], 0)
        self.assertTrue(t['result']['errors'])
        self.assertTrue(all(e['text'] for e in t['result']['errors']))
        self.assertLess(j.c['money'] - money, t['bonus'])
        self.assertLess(self.data()['office']['trust'], trust)
        self.assertGreater(t['mistakes'], 0)
        roundtrip(j)

    def test_hints_cost_time_and_bonus_and_stop_at_three(self):
        j = self.journey(self.forms[0], twist=False)
        tid = j.task['id']
        with self.assertRaises(GameError):
            j.act(self.P + 'hint', task=tid)                # read the brief first
        j.act('ask', task=tid)
        clock = self.data()['office']['clock']
        r = j.act(self.P + 'hint', task=tid)
        self.assertIn('💡', r['message'])
        self.assertEqual(self.data()['office']['clock'], clock + ow.COST['hint'])
        j.act(self.P + 'hint', task=tid)
        j.act(self.P + 'hint', task=tid)
        with self.assertRaises(GameError):
            j.act(self.P + 'hint', task=tid)
        self.assertEqual(len(j.task['tips']), ow.HINT_MAX)
        money = j.c['money']
        self.play(j, tid)
        t = j.get(tid)
        self.assertEqual(j.c['money'], money + t['bonus'] - ow.HINT_CUT * ow.HINT_MAX)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
        crit = {x['key']: x['score'] for x in post['feedback']['criteria']}
        self.assertEqual(crit['quality'], 3)
        roundtrip(j)

    def test_hand_in_needs_confirm_and_finished_work(self):
        for form in self.forms:
            if form == 'case':
                continue
            with self.subTest(form=form):
                j = self.journey(form, twist=False)
                tid = j.task['id']
                j.act('ask', task=tid)
                kind = j.task['work']['type']
                with self.assertRaises(GameError):
                    j.act(self.P + 'file', task=tid)
                if kind in ('sort', 'slots'):
                    with self.assertRaises(GameError):
                        j.act(self.P + 'file', task=tid, confirm=True)
                if kind == 'fields':
                    with self.assertRaises(GameError):
                        j.act(self.P + 'file', task=tid, confirm=True, fields={})
                    with self.assertRaises(GameError):
                        j.act(self.P + 'file', task=tid, confirm=True, fields={'nope': 'x'})
                if kind == 'seq':
                    with self.assertRaises(GameError):
                        j.act(self.P + 'file', task=tid, confirm=True, order=[])
                    with self.assertRaises(GameError):
                        j.act(self.P + 'file', task=tid, confirm=True, order=['zz'])
                self.assertFalse(j.get(tid)['filed'])
                self.assertEqual(j.get(tid)['status'] != 'completed', True)

    def test_malformed_moves_rejected(self):
        for form in self.forms:
            with self.subTest(form=form):
                j = self.journey(form, twist=False)
                tid = j.task['id']
                kind = j.task['work']['type']
                with self.assertRaises(GameError):                 # not asked yet
                    j.act(self.P + 'put', task=tid, item='x', bin='y')
                j.act('ask', task=tid)
                bad = dict(sort=[('put', dict(item='zz', bin='x')), ('put', dict(item=j.task['work'].get('items', [{}])[0].get('id'), bin='nope'))],
                           mark=[('mark', dict(seg='zz', opt=0)), ('mark', dict(seg=(ow.segs_of(j.task['work']) or [{}])[0].get('id'), opt=99))],
                           slots=[('place', dict(item='zz', cell='a|b')), ('place', dict(item=j.task['work'].get('items', [{}])[0].get('id'), cell='no|no'))],
                           case=[('read', dict(fact='zz')), ('reply', dict(option='zz', confirm=True))],
                           fields=[('put', dict(item='x', bin='y')), ('read', dict(fact='x'))],
                           seq=[('mark', dict(seg='x', opt=0)), ('place', dict(item='x', cell='a|b'))])[kind]
                for cmd, p in bad + [('nonsense', {})]:
                    with self.assertRaises(GameError, msg=(cmd, p)):
                        j.act(self.P + cmd, task=tid, **p)
                self.assertEqual(j.task['ans'], {} if kind != 'case' else j.task['ans'])
                self.assertEqual(j.task['mistakes'], 0)

    def test_tampered_dossier_rejected(self):
        j = self.journey(self.forms[0], twist=True)
        tid = j.task['id']
        j.act('ask', task=tid)
        for change in (lambda t: t['work'].update(type='case'), lambda t: t.update(bonus=999), lambda t: t.update(tw='later'),
                       lambda t: t.update(tips=['a'] * 9), lambda t: t.update(filed=True), lambda t: t.update(gen=99),
                       lambda t: t['ans'].update(zz='x')):
            s = copy.deepcopy(j.state)
            change(next(t for t in s['careers'][self.M.ID]['tasks'] if t['id'] == tid))
            with self.assertRaises(GameError):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers'][self.M.ID]['ext']['data']['day_stats']['filed'] = -1
        with self.assertRaises(GameError):
            validate_state(s)

    def test_late_hand_in_loses_bonus_and_trust(self):
        j = self.journey(self.forms[1], twist=False)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.task['due'] = office.OPEN + 1
        money = j.c['money']
        trust = self.data()['office']['trust']
        r = self.play(j, tid)
        t = j.get(tid)
        self.assertTrue(t['late'])
        self.assertIn('Trễ hạn', r['message'])
        self.assertEqual(j.c['money'], money + t['bonus'] - office.LATE_CUT)
        self.assertLess(self.data()['office']['trust'], trust + 2)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
        self.assertEqual({x['key']: x['score'] for x in post['feedback']['criteria']}['speed'], 1)

    def test_closed_office_then_overtime(self):
        j = self.journey(self.forms[0], twist=False)
        tid = j.task['id']
        j.act('ask', task=tid)
        self.data()['office']['clock'] = office.CLOSE
        with self.assertRaises(GameError) as cm:
            self.play(j, tid)
        self.assertEqual(cm.exception.code, 'office_closed')
        money = j.c['money']
        with self.assertRaises(GameError):
            j.act(self.P + 'overtime')
        j.act(self.P + 'overtime', confirm=True)
        self.assertEqual(j.c['money'], money + (18 if self.M.JOB.mod(j.c['day'])['id'] == self.M.JOB.cfg['crunch'] else 12))
        self.play(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        roundtrip(j)

    def test_crunch_day_is_due_earlier(self):
        day = next(d for d in range(2, 20) if self.M.JOB.mod(d)['id'] == self.M.JOB.cfg['crunch'])
        normal = next(d for d in range(2, 20) if self.M.JOB.mod(d)['id'] != self.M.JOB.cfg['crunch'])
        a = Journey(self.M.ID, slot=0, day=day).task['due']
        b = Journey(self.M.ID, slot=0, day=normal).task['due']
        self.assertEqual(a, max(office.OPEN + 60, b - 30))

    # ---------------------------------------------------------------- whole days
    def test_full_days_through_the_api(self):
        j = Journey(self.M.ID)
        self.j = j
        cid = self.M.ID
        inspected = None
        for day in range(1, 7):
            if day > 1:
                j.act('start_day')
            self.assertEqual(j.c['day'], day)
            self.clear_desk(j)
            mine = [t for t in j.c['tasks'] if t['career'] == cid and t['status'] not in ('completed', 'cancelled')]
            self.assertTrue(mine)
            for t in mine:
                self.clear_desk(j)
                r = self.play(j, t['id'])
                self.assertTrue(r.get('correct'), (day, t['form']))
                self.clear_desk(j)
            roundtrip(j)
            r = j.act('end_day', carry_event=True)
            summ = r['summary']['career']
            self.assertEqual(summ['filed'], len(mine))
            self.assertEqual(summ['clean'], len(mine))
            if self.M.JOB.mod(day)['id'] == self.M.JOB.cfg['audit']:
                inspected = summ['inspect']
            roundtrip(j)
        self.assertTrue(inspected and inspected['ok'])
        self.assertTrue(any(e['category'] == 'audit_bonus' for e in j.c['ops']['finance']['ledger']))
        self.assertEqual(self.data()['late'], 0)
        self.assertGreaterEqual(self.data()['care']['reliable'], 3)
        pub = public_state(j.state)['careers'][cid]['data']
        self.assertEqual(set(pub['today']), {'mod', 'rules'})
        self.assertTrue(pub['today']['rules'])

    def test_more_work_and_day_forms_differ(self):
        j = Journey(self.M.ID)
        forms = [t['form'] for t in j.c['tasks'] if t['career'] == self.M.ID]
        self.assertGreaterEqual(len(forms), 2)
        self.assertEqual(len(forms), len(set(forms)))
        roundtrip(j)

    # ---------------------------------------------------------------- saves & hiring
    def test_old_save_without_desk_data_loads(self):
        j = Journey(self.M.ID)
        s = copy.deepcopy(j.state)
        s['careers'][self.M.ID]['ext']['data'] = {}
        public_state(s)
        validate_state(s)
        d = s['careers'][self.M.ID]['ext']['data']
        self.assertIn('office', d)
        self.assertIn('day_stats', d)
        j.state = s
        t = next(t for t in j.c['tasks'] if t['career'] == self.M.ID)
        self.play(j, t['id'])
        roundtrip(j)

    def test_hiring_gate_and_postings(self):
        state = new_state()
        state, _ = apply_action(state, self.M.ID, 'select_career', {})
        with self.assertRaises(GameError) as cm:
            apply_action(state, self.M.ID, 'start_day', {})
        self.assertEqual(cm.exception.code, 'not_hired')
        posts = employment.postings(self.M.ID)
        self.assertEqual([p['salary'] for p in posts], [(55, 80), (50, 70)])
        for p in posts:
            for q in p['questions']:
                self.assertIsNotNone(employment.question(self.M.ID, q), q)
        post = posts[0]

        def act(name, **p):
            nonlocal state
            state, r = apply_action(state, self.M.ID, name, p)
            return r
        act('job_apply', posting=post['id'])
        act('job_cv', strengths=post['wants'][:3], claims=['fresh'])
        act('job_letter', parts=dict(why='specific', example='story', close='available'))
        for qid in post['questions']:
            q = employment.question(self.M.ID, qid)
            act('job_answer', question=qid, option=max(q['options'], key=lambda o: o['score'])['id'])
        self.assertEqual(state['careers'][self.M.ID]['job']['status'], 'offer')
        act('job_accept', confirm=True)
        act('start_day')
        self.assertTrue(state['careers'][self.M.ID]['tasks'])
        validate_state(json.loads(json.dumps(state)))

    def test_content_and_rules(self):
        c = self.M.content()
        self.assertEqual([f['id'] for f in c['forms']], self.forms)
        self.assertEqual(c['hint_max'], ow.HINT_MAX)
        for d in range(1, 8):
            for r in self.M.rules(d):
                self.assertTrue(r['title'] and r['text'])
