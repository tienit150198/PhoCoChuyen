"""Công an phường, generator 2 (owner spec 11/10): a child handed to the wrong adult (hạ 1 bậc hàm + giam hàm 15 ngày),
the chuyên án đường dây buôn lậu (+1 ngày xét thăng cấp; failed, escaped or bribed: giam hàm 3 ngày), the posts about
the ward's shops (a real complaint is never silenced), the business inspection (đủ/thiếu, then the right measure), and
old saves keeping generator 1 (kit legacy band)."""
import copy
import json
import unittest

from game import org_content as OC
from game import promotion as pm
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.helpers import Journey
from tests.test_career_police import P, at, codes, solve

if P is not None:
    from game.careers import kit
    from game.careers import police_content as PC

O = OC.ORGS['cand']


def gi(gid):
    return next(i for i, g in enumerate(O['grades']) if g['id'] == gid)


def ladder(j, grade='trung_si'):
    """The officer on the CAND ladder at `grade` (the record is made lazily, as the first action would)."""
    x = pm.org_live(j.state, j.c, 'police', True)[1]
    x['g'] = gi(grade)
    return x


def org(j):
    return pm.record(j.state, 'police')['org']


def hold(j):
    return (pm.record(j.state, 'police').get('cx') or {}).get('hold', 0)


def grade(j):
    return O['grades'][org(j)['g']]['id']


def needs(j, tid):
    return next(t for t in public_state(j.state)['careers']['police']['tasks'] if t['id'] == tid)['needs']


@unittest.skipIf(P is None, 'police filtered out')
class Kidnap(unittest.TestCase):
    """Spec 1: trao trả nhầm người thân → trẻ bị dẫn đi; giáng 1 cấp bậc hàm + giam hàm 15 ngày."""

    def test_the_clues_are_in_plain_sight(self):
        wrong = [k for k, x in PC.CHILDREN.items() if not x['genuine']]
        self.assertEqual(set(wrong), {'ch-tun', 'ch-ken'})
        for k in wrong:
            says = PC.CHILDREN[k]['says']
            self.assertIn('không nhờ', says['id'], k)            # the parents' phone says it
            self.assertTrue('không' in says['kid'] or 'không chạy' in says['kid'], k)   # the child does not go to them
            self.assertIn('Hỏi ai nhờ đón', says['detail'], k)   # the adult cannot say who sent them

    def test_handing_over_to_the_wrong_adult_demotes_and_holds_however_careful(self):
        for case in ('ch-tun', 'ch-ken'):
            j = at(case, 'child')
            ladder(j)
            tid = j.task['id']
            j.act('ask', task=tid)
            j.act('cap_calm', task=tid)
            j.act('cap_tag', task=tid)
            r = j.act('cap_announce', task=tid, how='call')
            self.assertTrue('giữ cháu' in r['message'] or 'Đừng giao' in r['message'], case)   # the parent on the phone says it too
            for q in PC.VERIFY:
                j.act('cap_verify', task=tid, q=q)
            self.assertEqual(set(needs(j, tid)['says']), set(PC.VERIFY))
            r = j.act('cap_handover', task=tid)
            self.assertIn('Công an Thành phố tìm thấy bé an toàn', r['message'], case)
            self.assertIn('Hạ 1 bậc hàm', r['rank_note'], case)
            self.assertIn('Giam hàm 15', r['rank_note'], case)
            self.assertEqual(grade(j), 'ha_si', case)
            self.assertEqual(hold(j), PC.KIDNAP_DAYS, case)
            self.assertEqual(pm.record(j.state, 'police')['cx']['sev'][-1]['c'], 'kidnap', case)
            self.assertEqual(org(j)['warns'], [], case)   # the grave case only, no extra ⚠️ for the same act
            self.assertIn('wrong_adult', codes(j.get(tid)), case)
            facts = j.c['ext']['data']['today']['facts']
            self.assertTrue(any('bị dẫn đi' in f['text'] and f['true'] for f in facts), case)
            validate_state(json.loads(json.dumps(j.state)))

    def test_a_hasty_handover_is_grave_too(self):
        j = at('ch-ken', 'child')
        ladder(j)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('cap_calm', task=tid)
        j.act('cap_announce', task=tid, how='loa')
        r = j.act('cap_handover', task=tid)
        self.assertIn('Hạ 1 bậc hàm', r['rank_note'])
        self.assertEqual((grade(j), hold(j)), ('ha_si', PC.KIDNAP_DAYS))

    def test_holding_the_child_is_right_and_costs_nothing(self):
        j = at('ch-ken', 'child')
        ladder(j)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('cap_calm', task=tid)
        j.act('cap_announce', task=tid, how='loa')
        j.act('cap_verify', task=tid, q='kid')
        j.act('cap_verify', task=tid, q='id')
        r = j.act('cap_hold', task=tid)
        self.assertIn('ba Ken', r['message'])
        self.assertEqual((grade(j), hold(j)), ('trung_si', 0))
        self.assertFalse(j.get(tid).get('slips'))

    def test_under_grace_it_is_a_reminder_with_the_story(self):
        j = at('ch-tun', 'child', learned=False)
        ladder(j)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('cap_calm', task=tid)
        j.act('cap_announce', task=tid, how='loa')
        j.act('cap_verify', task=tid, q='kid')
        j.act('cap_verify', task=tid, q='detail')
        r = j.act('cap_handover', task=tid)          # anh Định stops it once
        self.assertIn('Anh Định', r['message'])
        r = j.act('cap_handover', task=tid)
        self.assertIn('bị dẫn đi', r['message'])
        self.assertIn('Nhắc quy trình', r['rank_note'])
        self.assertEqual((grade(j), hold(j)), ('trung_si', 0))


def ring_at(case=None):
    j = at(case, 'ring')
    ladder(j)
    tid = j.task['id']
    j.act('ask', task=tid)
    return j, tid


def good(step):
    return next(o[0] for o in PC.RING_STEP[step]['options'] if o[2] == 'good')


@unittest.skipIf(P is None, 'police filtered out')
class Ring(unittest.TestCase):
    """Spec 2: chuyên án đường dây buôn lậu, hàng trên 100.000 xu."""

    def test_it_comes_now_and_then_and_is_a_big_case(self):
        days = [d for d in range(1, 1201) if P.ring_slot(d)]
        self.assertTrue(1 / 7 < len(days) / 1200 < 1 / 4, len(days))
        self.assertTrue(all(d >= PC.RING_FROM_DAY and P.ring_slot(d) in (2, 3) for d in days))
        for d in days[:30]:
            self.assertEqual(P.task_kind(d, P.ring_slot(d)), 'ring')
        self.assertEqual({P.make_task(d, P.ring_slot(d), 1)['_v']['case'] for d in days}, set(PC.RINGS))
        for x in PC.RINGS.values():
            self.assertGreater(x['value'], PC.RING_VALUE_MIN)
        for sid, st in PC.RING_STEPS:
            self.assertEqual([o[2] for o in st['options']].count('good'), 1, sid)
            self.assertTrue({o[2] for o in st['options']} <= {'good', 'fail', 'escape'}, sid)
        self.assertTrue(any(o[2] == 'escape' for _, st in PC.RING_STEPS for o in st['options']))

    def test_solved_step_by_step_gives_a_day_towards_the_next_grade(self):
        j, tid = ring_at('rg-phone')
        tig = org(j)['tig']
        self.assertIn('186.000', j.task['opening'])
        self.assertEqual(needs(j, tid)['value_text'], '186.000')
        j.act('cap_case', task=tid, step='tip', choice='verify')
        with self.assertRaises(GameError):
            j.act('cap_case', task=tid, step='papers', choice='customs')   # one step at a time
        r = j.act('cap_case', task=tid, step='watch', choice='watch')
        self.assertIn('phong bì', r['message'])
        self.assertEqual(needs(j, tid)['env']['answered'], None)
        with self.assertRaises(GameError):
            j.act('cap_case', task=tid, step='papers', choice='customs')   # the envelope first
        r = j.act('cap_caseenv', task=tid, choice='report')
        self.assertEqual(org(j)['liem'], 1)
        j.act('cap_case', task=tid, step='papers', choice='customs')
        r = j.act('cap_case', task=tid, step='raid', choice='truck')
        t = j.get(tid)
        self.assertEqual((t['status'], t['result']), ('completed', 'solved'))
        self.assertIn('186.000 xu', r['message'])
        self.assertIn('+1 ngày', r['rank_note'])
        self.assertEqual(org(j)['tig'], tig + 1)
        self.assertEqual(hold(j), 0)
        self.assertEqual({c['key']: c['score'] for c in P.feedback(j.c, t)['criteria']}, {'honest': 5, 'case': 5})
        with self.assertRaises(GameError):
            j.act('cap_case', task=tid, step='raid', choice='truck')
        validate_state(json.loads(json.dumps(j.state)))

    def test_a_wrong_call_lets_the_suspect_escape_and_holds_the_grade(self):
        j, tid = ring_at()
        tig = org(j)['tig']
        j.act('cap_case', task=tid, step='tip', choice='verify')
        r = j.act('cap_case', task=tid, step='watch', choice='ask')
        t = j.get(tid)
        self.assertEqual((t['status'], t['result'], t['choice']), ('completed', 'failed', 'escape'))
        self.assertIn('trốn', r['message'])
        self.assertIn(f'Giam hàm {PC.RING_HOLD}', r['rank_note'])
        self.assertEqual((hold(j), org(j)['tig'], grade(j)), (PC.RING_HOLD, tig, 'trung_si'))
        self.assertIn('ring_escape', codes(t))
        self.assertIsNone(needs(j, tid)['env'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_dropping_the_tip_fails_the_case(self):
        j, tid = ring_at()
        r = j.act('cap_case', task=tid, step='tip', choice='drop')
        self.assertEqual(j.get(tid)['result'], 'failed')
        self.assertIn(f'Giam hàm {PC.RING_HOLD}', r['rank_note'])

    def test_the_rings_envelope_taken_demotes_and_loses_the_case(self):
        j, tid = ring_at()
        j.act('cap_case', task=tid, step='tip', choice='verify')
        j.act('cap_case', task=tid, step='watch', choice='watch')
        r = j.act('cap_caseenv', task=tid, choice='take')
        t = j.get(tid)
        self.assertEqual((t['status'], t['result'], t['choice']), ('completed', 'failed', 'bribed'))
        self.assertIn('bribe', codes(t))
        self.assertIn('Nhận phong bì', r['rank_note'])
        self.assertIn(f'Giam hàm {PC.RING_HOLD}', r['rank_note'])
        self.assertIsNotNone(org(j)['mark']['b'])
        self.assertEqual((grade(j), hold(j)), ('ha_si', PC.RING_HOLD))
        validate_state(json.loads(json.dumps(j.state)))

    def test_forged_case_steps_are_refused(self):
        j, tid = ring_at()
        j.act('cap_case', task=tid, step='tip', choice='verify')
        for key, value in (('acts', {'watch': 'watch'}), ('acts', {'tip': 'rush', 'watch': 'watch'}), ('acts', {'tip': 'nope'}),
                           ('press', 'take'), ('seen', ['look:0'])):
            s = copy.deepcopy(j.state)
            t = next(x for x in s['careers']['police']['tasks'] if x['id'] == tid)
            t[key] = value
            with self.assertRaises(GameError, msg=(key, value)):
                validate_state(s)


def posts_at():
    j = at(None, 'posts')
    ladder(j)
    tid = j.task['id']
    j.act('ask', task=tid)
    return j, tid


@unittest.skipIf(P is None, 'police filtered out')
class Posts(unittest.TestCase):
    """Spec 3: đòi hỏi ngoài dịch vụ → gỡ; bóc phốt đòi đền bù → mời làm việc, phạt; góp ý thật → không gỡ, không phạt."""

    def test_every_task_has_a_real_complaint_and_another_kind(self):
        for d in range(3, 120):
            for sl in range(2, 8):
                if P.task_kind(d, sl) == 'posts':
                    ids = P.make_task(d, sl, 1)['_v']['posts']
                    self.assertEqual(len({PC.POSTS[k]['shop'] for k in ids}), PC.POST_N)   # three shops
                    kinds = [PC.POSTS[k]['kind'] for k in ids]
                    self.assertEqual(len(kinds), PC.POST_N)
                    self.assertIn('real', kinds)
                    self.assertTrue(set(kinds) - {'real'})

    def test_by_the_book(self):
        j, tid = posts_at()
        pub = needs(j, tid)
        self.assertTrue(all(p['look'] is None and 'kind' not in p for p in pub['posts']))
        r = solve(j, j.get(tid))
        t = j.get(tid)
        self.assertEqual((t['status'], t['result']), ('completed', 'reviewed'))
        self.assertFalse(t.get('slips'), t.get('slips'))
        self.assertTrue(r['celebrate'])
        self.assertEqual(org(j)['warns'], [])
        self.assertTrue(all(p['look'] and p['outcome'] for p in needs(j, tid)['posts']))

    def test_silencing_a_real_complaint_is_a_warning(self):
        for act in ('down', 'fine'):
            j, tid = posts_at()
            ids = j.task['_v']['posts']
            i = next(i for i, k in enumerate(ids) if PC.POSTS[k]['kind'] == 'real')
            j.act('cap_plook', task=tid, i=i)
            r = j.act('cap_post', task=tid, i=i, act=act)
            self.assertIn('Cảnh cáo 1/3', r['message'], act)
            self.assertEqual(org(j)['warns'][-1]['c'], 'wrong_penalty', act)
            self.assertIn(f'gag{i}', codes(j.get(tid)))

    def test_extortion_is_fined_and_only_taking_it_down_falls_short(self):
        j, tid = posts_at()
        ids = j.task['_v']['posts']
        for i, k in enumerate(ids):
            kind = PC.POSTS[k]['kind']
            j.act('cap_plook', task=tid, i=i)
            j.act('cap_post', task=tid, i=i, act='down' if kind == 'bocphot' else PC.POST_BEST[kind])
        t = j.get(tid)
        n_threat = sum(PC.POSTS[k]['kind'] == 'bocphot' for k in ids)
        self.assertEqual(len([c for c in codes(t) if c.startswith('soft')]), n_threat)
        self.assertEqual(org(j)['warns'], [])

    def test_one_post_once_and_forged_acts_are_refused(self):
        j, tid = posts_at()
        j.act('cap_post', task=tid, i=0, act=PC.POST_BEST[PC.POSTS[j.task['_v']['posts'][0]]['kind']])
        with self.assertRaises(GameError):
            j.act('cap_post', task=tid, i=0, act='keep')
        with self.assertRaises(GameError):
            j.act('cap_post', task=tid, i=1, act='ban')
        for key, value in (('acts', {'0': 'ban'}), ('acts', {'7': 'keep'}), ('seen', ['look:5'])):
            s = copy.deepcopy(j.state)
            t = next(x for x in s['careers']['police']['tasks'] if x['id'] == tid)
            t[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)


def biz_at(case):
    j = at(case, 'inspect')
    ladder(j)
    tid = j.task['id']
    j.act('ask', task=tid)
    return j, tid


def mark_all(j, tid, truth=True):
    x = PC.BIZ[j.get(tid)['_v']['case']]
    for p in PC.PAPER_IDS:
        j.act('cap_paper', task=tid, paper=p)
        j.act('cap_mark', task=tid, paper=p, v=x['papers'][p][0] if truth else 'ok')


@unittest.skipIf(P is None, 'police filtered out')
class Inspect(unittest.TestCase):
    """Spec 4: thuế, hóa đơn nguồn hàng, kê khai hải quan → nhắc nhở / phạt hành chính / chuyển Hải quan."""

    def test_the_rule_covers_each_measure(self):
        best = {k: PC.biz_best(x) for k, x in PC.BIZ.items()}
        self.assertEqual(set(best.values()), set(PC.VERDICT_IDS))
        self.assertEqual(best['bz-cosmetic'], 'customs')   # a customs gap goes to Hải quan even with other gaps

    def test_every_business_by_the_book(self):
        for case in PC.BIZ:
            j, tid = biz_at(case)
            solve(j, j.get(tid))
            t = j.get(tid)
            self.assertEqual((t['status'], t['choice']), ('completed', PC.biz_best(PC.BIZ[case])), case)
            self.assertFalse(t.get('slips'), (case, t.get('slips')))
            self.assertEqual(needs(j, tid)['best'], PC.biz_best(PC.BIZ[case]))

    def test_read_then_mark_then_decide(self):
        j, tid = biz_at('bz-grocery')
        with self.assertRaises(GameError):
            j.act('cap_mark', task=tid, paper='tax', v='miss')        # not read yet
        self.assertEqual(needs(j, tid)['checks'], {})
        j.act('cap_paper', task=tid, paper='tax')
        j.act('cap_mark', task=tid, paper='tax', v='ok')
        j.act('cap_mark', task=tid, paper='tax', v='miss')            # changeable until the decision
        with self.assertRaises(GameError):
            j.act('cap_verdict', task=tid, v='fine')                  # every paper marked first
        self.assertEqual(needs(j, tid)['marks'], {'tax': 'miss'})
        self.assertIsNone(needs(j, tid)['best'])

    def test_a_heavy_penalty_on_a_business_in_order_is_a_warning(self):
        for v in ('fine', 'customs'):
            j, tid = biz_at('bz-cafe')
            mark_all(j, tid)
            r = j.act('cap_verdict', task=tid, v=v)
            self.assertIn('Cảnh cáo 1/3', r['message'], v)
            self.assertEqual(org(j)['warns'][-1]['c'], 'wrong_penalty', v)
            self.assertIn('heavy', codes(j.get(tid)))

    def test_lighter_or_misplaced_measures_and_wrong_marks_are_slips_only(self):
        j, tid = biz_at('bz-phone')
        mark_all(j, tid, truth=False)
        j.act('cap_verdict', task=tid, v='fine')
        self.assertEqual(codes(j.get(tid)), {'mark_customs', 'wrongdesk'})
        self.assertEqual(org(j)['warns'], [])
        j, tid = biz_at('bz-hardware')
        mark_all(j, tid)
        j.act('cap_verdict', task=tid, v='remind')
        self.assertEqual(codes(j.get(tid)), {'soft'})
        validate_state(json.loads(json.dumps(j.state)))

    def test_forged_marks_are_refused(self):
        j, tid = biz_at('bz-cafe')
        for key, value in (('acts', {'tax': 'maybe'}), ('acts', {'vat': 'ok'}), ('seen', ['paper:vat'])):
            s = copy.deepcopy(j.state)
            t = next(x for x in s['careers']['police']['tasks'] if x['id'] == tid)
            t[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)


@unittest.skipIf(P is None, 'police filtered out')
class Client(unittest.TestCase):
    def test_the_new_work_renders_at_every_step(self):
        import shutil
        import subprocess
        from pathlib import Path
        from game.content import public_content
        if not shutil.which('node'):
            self.skipTest('node not installed')
        cases = []

        def snap(name, j, expect, absent=()):
            cases.append(dict(name=name, tid=j.c['tasks'][0]['id'], state=public_state(j.state), expect=list(expect), absent=list(absent)))

        j, tid = posts_at()
        snap('posts open', j, ['cap-post', 'data-command="cap_plook"', 'Xử lý bài đăng'])
        j.act('cap_plook', task=tid, i=0)
        j.act('cap_post', task=tid, i=0, act='keep')
        snap('posts one handled', j, ['cap-post done', 'cap-look'])
        j, tid = biz_at('bz-phone')
        snap('inspect open', j, ['data-command="cap_paper"', 'Mức xử lý'], ['data-command="cap_verdict"'])
        mark_all(j, tid)
        snap('inspect marked', j, ['data-command="cap_verdict"', 'cap-mark on', 'Chuyển hồ sơ sang Hải quan'])
        j.act('cap_verdict', task=tid, v='customs')
        snap('inspect done', j, ['✅ Đủ', '❌ Thiếu'], ['data-command="cap_verdict"'])
        j, tid = ring_at('rg-wine')
        snap('ring open', j, ['Chuyên án lớn', '152.000 xu', 'data-command="cap_case"'])
        j.act('cap_case', task=tid, step='tip', choice='verify')
        j.act('cap_case', task=tid, step='watch', choice='watch')
        snap('ring envelope', j, ['cap-renv', 'data-command="cap_caseenv"', 'Tư “Mập”'], ['data-command="cap_case"'])
        j.act('cap_caseenv', task=tid, choice='refuse')
        j.act('cap_case', task=tid, step='papers', choice='customs')
        j.act('cap_case', task=tid, step='raid', choice='truck')
        snap('ring solved', j, ['Phá án thành công'], ['data-command="cap_case"'])
        j, tid = ring_at()
        j.act('cap_case', task=tid, step='tip', choice='rush')
        snap('ring failed', j, ['Chuyên án chưa thành'])
        j = at('ch-ken', 'child')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('cap_calm', task=tid)
        j.act('cap_announce', task=tid, how='loa')
        snap('child pick-up', j, ['data-confirm', 'Chú Lực'])
        root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(['node', str(root / 'tests' / 'police_cases_ui.mjs')], cwd=root, input=json.dumps(dict(content=public_content(), cases=cases)),
                              text=True, encoding='utf-8', capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr[-3000:])
        self.assertIn('views passed', proc.stdout)


@unittest.skipIf(P is None, 'police filtered out')
class OldSaves(unittest.TestCase):
    def test_tasks_saved_before_generator_two_keep_their_generator(self):
        day, slot = next((d, s) for d in range(4, 200) for s in range(2, 8)
                         if P.make_task(d, s, 5)['kind'] != P.make_task(d, s, 5 + kit.LEGACY_TURN)['kind'])
        j = Journey('police', slot=slot, day=day)
        old = P.make_task(day, slot, 5 + kit.LEGACY_TURN)
        old['created_turn'] = 5   # as a save made before generator 2 stored it
        self.assertEqual(old['gen'], 1)
        j.c['tasks'] = [old]
        j.c['active_task'] = old['id']
        s = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            validate_state(s)
        s = migrate_state(s)
        validate_state(s)
        t = s['careers']['police']['tasks'][0]
        self.assertEqual((t['gen'], t['kind']), (1, old['kind']))
        self.assertGreaterEqual(t['created_turn'], kit.LEGACY_TURN)
        self.assertEqual(migrate_state(s)['careers']['police']['tasks'][0]['created_turn'], t['created_turn'])   # once only

    def test_a_new_task_cannot_pass_as_an_old_one(self):
        j = at(None, 'ring')
        s = copy.deepcopy(j.state)
        s['careers']['police']['tasks'][0]['gen'] = 1
        with self.assertRaises(GameError):
            validate_state(s)


if __name__ == '__main__':
    unittest.main()
