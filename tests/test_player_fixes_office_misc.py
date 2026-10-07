"""Player reports fixed in the office-misc package (07/10):

* F#227 tax_payroll (and every accounting career on ACCT_CARE): the 🧭 Lộ trình gate shows its progress, and the
  promo sheet says in three short steps how the two counters fit.
* F#221 grocery "always pushed into the worst outcome": a workplace's first week draws only mild incidents at half the
  rate; an undecided incident takes a neutral option at closing, not a wrong answer; gamble options show their odds;
  every shop event has a choice that need not cost anything (a theft: the police and the camera may get it back).
* F#224 furniture moved by accident: 📌 Ghim per piece (client-side), and a longer press-and-move before a drag."""
import copy
import json
import random
import unittest
from pathlib import Path

from game import incidents as inc
from game import promotion as pm
from game import shop_events as ev
from game.careers import grocery as G
from game.careers import kit
from game.engine import money, new_state, public_state, validate_state
from game.incident_content import INCIDENTS, INDEX
from tests.helpers import Journey
from tests.test_incidents import fake_c
from tests.test_promotion import story

ROOT = Path(__file__).resolve().parents[1]


class AccountingGate(unittest.TestCase):
    def care_row(self, j):
        return next(r for r in public_state(j.state)['careers'][j.career]['promo']['next']['requirements'] if r['id'] == 'care')

    def test_gate_shows_days_and_trust(self):
        for career in pm.ACCT:
            j = Journey(career)
            story(j)
            d = j.c['ext']['data']
            d['care']['reliable'], d['office']['trust'] = 4, 48
            row = self.care_row(j)
            self.assertFalse(row['met'])
            self.assertEqual(row['label'], '🧭 Lộ trình bậc 2: 4/6 ngày chắc tay · tin tưởng 48/55', career)
            self.assertEqual((row['got'], row['need']), (4, 6))
            d['care']['reliable'], d['office']['trust'] = 9, 80   # capped at the mark, never "9/6"
            self.assertEqual(self.care_row(j)['label'], '🧭 Lộ trình bậc 2: 6/6 ngày chắc tay · tin tưởng 55/55')
            d['care']['rank'] = 2
            row = self.care_row(j)
            self.assertTrue(row['met'])
            self.assertEqual(row['label'], '🧭 Lộ trình bậc 2: đã đạt')
            validate_state(j.state)

    def test_second_step_asks_for_rank_three(self):
        j = Journey('tax_payroll')
        story(j)
        d = j.c['ext']['data']
        d['care'].update(reliable=7, rank=2)
        d['office']['trust'] = 60
        rec = pm.record(j.state, j.career, True)
        pm._sync(rec, j.c)
        rec['rank'] = 1
        row = self.care_row(j)
        self.assertEqual(row['label'], '🧭 Lộ trình bậc 3: 7/10 ngày chắc tay · tin tưởng 60/70')

    def test_client_says_how_in_three_steps(self):
        js = (ROOT / 'public/js/v4/promo.js').read_text(encoding='utf-8')
        start = js.index('const CARE_HOW=')
        block = js[start:js.index('`;', start)]
        visible = block.split('<details')[0]
        import re
        words = re.sub(r'<[^>]+>', ' ', visible.split('`', 1)[1]).split()
        self.assertLessEqual(len([w for w in words if any(ch.isalnum() for ch in w)]), 25, words)
        self.assertIn('Cách lên bậc', visible)
        self.assertIn('<summary>?</summary>', block)
        self.assertIn("r.id==='care'", js)


class Incidents(unittest.TestCase):
    def test_first_week_is_mild_and_half_as_often(self):
        hits = tense = 0
        for seed in range(600):
            for day in range(3, 8):
                p = inc.roll_plan(dict(journey=dict(seed=seed)), fake_c(day), 'grocery')
                if p:
                    hits += 1
                    tense += INDEX[p['script']]['tone'] != 'mild'
        self.assertEqual(tense, 0)
        rate = hits / (600 * 5)
        expected = sum(inc.rate(d) * inc.NEW_RATE for d in range(3, 8)) / 5
        self.assertLess(abs(rate - expected), .05, (rate, expected))
        later = [inc.roll_plan(dict(journey=dict(seed=s)), fake_c(12), 'grocery') for s in range(300)]
        self.assertTrue(any(p and INDEX[p['script']]['tone'] == 'tense' for p in later))   # the full pool from day 8

    def test_neutral_default_is_never_a_wrong_answer_when_one_exists(self):
        changed = 0
        for x in INCIDENTS:
            n = inc.neutral(x)
            o = next(o for o in x['options'] if o['id'] == n)
            if n != x['default']:
                changed += 1
                self.assertIsNot(o['good'], False, x['id'])
                self.assertFalse(o.get('luck') or o.get('voluntary'), x['id'])
            elif o['good'] is False:   # kept only when every other option is a gamble, voluntary or wrong
                self.assertFalse([y for y in x['options'] if y['good'] is not False and not y.get('luck') and not y.get('voluntary')], x['id'])
        self.assertGreater(changed, 20)
        self.assertEqual(inc.neutral(INDEX['fake_transfer']), 'wait')
        self.assertEqual(inc.neutral(INDEX['counterfeit']), 'refuse')

    def test_closing_time_takes_the_neutral_option_without_reward(self):
        from tests.test_incidents import fire, open_day
        s = open_day('grocery')
        fire(s, 'grocery', 'fake_transfer')
        c = s['careers']['grocery']
        money, xp = c['money'], c['xp']
        inc.on_close(s, c, 'grocery')
        h = c['incidents']['history'][-1]
        self.assertEqual((h['choice'], h['auto'], h['good']), ('wait', True, None))
        self.assertLessEqual(h['trust'], 0)
        self.assertEqual((c['money'], c['xp']), (money, xp))   # 'trust' (−60 xu) would have cost the fund
        validate_state(s)

    def test_gamble_options_show_their_odds(self):
        from tests.test_incidents import fire, open_day
        s = open_day('grocery')
        fire(s, 'grocery', 'counterfeit')
        c = s['careers']['grocery']
        view = inc.public(c, 'grocery', s)['active']
        hold = next(o for o in view['options'] if o['id'] == 'hold')
        luck = next(o for o in INDEX['counterfeit']['options'] if o['id'] == 'hold')['luck']
        self.assertEqual(hold['odds'], round(100 * (luck['p_camera'] if luck['p_camera'] is not None and inc._camera(c) else luck['p'])))
        self.assertIsNone(next(o for o in view['options'] if o['id'] == 'refuse')['odds'])
        dump = json.dumps(view, ensure_ascii=False)
        for k in ('"good"', '"outcome"', '"luck"', '"win"', '"lose"'):
            self.assertNotIn(k, dump)   # the odds, never the result
        js = (ROOT / 'public/js/v4/incidents.js').read_text(encoding='utf-8')
        self.assertIn('🎲 Hên xui', js)

    def test_grocery_desk_gambles_show_odds(self):
        bribe = next(o for o in G.EVENTS[0]['options'] if o['id'] == 'bribe')
        self.assertTrue(kit.desk_hint(bribe).endswith('🎲 Hên xui · 30% được việc'))
        hide = next(o for o in kit.desk_script(G.EVENTS, 'GE-REINSPECT')['options'] if o['id'] == 'hide')
        self.assertIn('40%', kit.desk_hint(hide))
        plain = next(o for o in G.EVENTS[0]['options'] if o['id'] == 'open')
        self.assertEqual(kit.desk_hint(plain), plain['hint'])
        desk = kit.desk_initial()
        desk['ev'] = dict(id='desk-1', script='GE-INSPECT', day=3, at='open')
        opts = kit.desk_public(desk, G.EVENTS, 'grocery')['ev']['options']
        self.assertIn('🎲', next(o for o in opts if o['id'] == 'bribe')['hint'])


class ShopEvents(unittest.TestCase):
    def spawn(self, kind, camera=False):
        s = new_state()
        c = s['careers']['milk_tea']
        c['started'] = True
        ev.tick_career(s, c, 'milk_tea')
        c['ops']['shop_events']['seq'] = 1
        c['ops']['shop_events']['pending'] = ev.make_event(kind, 1, 'milk_tea', camera)
        return s, c

    def test_every_event_has_a_choice_that_need_not_cost(self):
        for kind, spec in ev.CATALOGUE.items():
            self.assertTrue(any(x['cost'] == 0 and not x['loss'] or ev.recover_odds(kind, x['id'], False) for x in spec['choices']), kind)

    def test_theft_report_can_get_it_back(self):
        got = lost = 0
        for n in range(1, 120):
            s, c = self.spawn('theft')
            c['ops']['shop_events']['pending']['id'] = f'shop-milk_tea-{n}'
            c['ops']['shop_events']['seq'] = n
            money(s, c, 1000, 'Vốn thử', category='other_income')
            view = ev.public(c)['pending']
            report = next(x for x in view['choices'] if x['id'] == 'report')
            self.assertEqual(report['odds'], 50)
            self.assertIn('🎲 Hên xui · 50%', report['effect'])
            before = c['money']
            r = ev.choose_career(s, c, 'milk_tea', dict(event=view['id'], choice='report', confirm=True))
            paid = before - c['money']
            row = c['ops']['shop_events']['recent'][-1]
            self.assertEqual(row['text'], ev.CATALOGUE['theft']['choices'][0]['text'])   # what older builds validate
            if paid == 0:
                got += 1
                self.assertIn('không mất xu', r['message'])
                self.assertEqual(ev.public(c)['recent'][-1]['text'], ev.RECOVERED)
            else:
                lost += 1
            ev.validate(c['ops'], 'milk_tea', 'milk_tea')
            validate_state(s)
        self.assertTrue(40 < got < 80 and lost, (got, lost))
        s, c = self.spawn('theft', camera=True)
        self.assertEqual(next(x for x in ev.public(c)['pending']['choices'] if x['id'] == 'report')['odds'], 85)

    def test_stall_theft_too(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb
        from unittest.mock import patch
        s, st = fixture(staff=False)
        qb.settle(s, now=1000)
        st['business']['sold'] = ev.GAP
        with patch.object(ev, 'select_kind', return_value='theft'):
            ev.tick_quay(s, st)
        st.update(fund=100000, till=0)
        q = ev.public(st, True)['pending']
        self.assertIsNotNone(next(x for x in q['choices'] if x['id'] == 'report')['odds'])
        ev.choose_quay(s, st, dict(event=q['id'], choice='report', confirm=True))
        ev.validate(json.loads(json.dumps(st)), st['id'], st['trade'], st['place'])


class DecoPin(unittest.TestCase):
    def test_pin_and_a_longer_press(self):
        js = (ROOT / 'public/js/v4/reno.js').read_text(encoding='utf-8')
        self.assertIn('const DRAG_PX=12;', js)
        self.assertIn('Math.hypot(dx,dy)<DRAG_PX', js)
        self.assertNotIn('Math.hypot(dx,dy)<6', js)
        start = js.index('function startPieceDrag(')
        self.assertIn('if(isPinned(uid))return false;', js[start:start + 120])
        self.assertIn("case'pin':", js)
        self.assertIn("'📌 Ghim'", js)
        self.assertIn("localStorage.setItem(PIN_KEY", js)   # this device only: no save key


class Rollback(unittest.TestCase):
    """The live build (MNL_LIVE_TREE, an archive of rel-1.9.10) reads every save this package writes and plays a day."""
    PROG = ('import json,sys\nfrom game.engine import validate_state,apply_action,public_state\n'
            'for s in json.load(sys.stdin):\n'
            ' validate_state(s)\n cur=s["current"]\n public_state(s)\n c=s["careers"][cur]\n'
            ' if c["open"]:\n  s,_=apply_action(s,cur,"end_day",{"carry_event":True})\n'
            ' s,_=apply_action(s,cur,"start_day",{})\n validate_state(s)\n public_state(s)\n'
            'print("ok")')

    def saves(self):
        from game import promotion_office as OF
        from tests.test_incidents import fire, open_day
        from tests.test_promotion_ladders import at, office_state
        out = []
        j = at('pilot', 5)   # a captain quit (replaced by a captain), a top-up, a step-5 promotion
        off = office_state(j)
        cap = next(i for i, st in enumerate(off['staff']) if st['lv'] >= 2)
        OF._quit('pilot', off, cap, pm._seed(j.state))
        for i, st in enumerate(off['staff']):
            if st['r'] == 'pl' and st['lv'] >= 2 and i != cap:
                st['lv'] = 0
        OF._top_up('pilot', off)
        tin = next(i for i, st in enumerate(off['staff']) if st['r'] == 'pl' and st['lv'] < 2)
        j.act('pm_of_hr', mate=tin, act='promote')
        validate_state(j.state)
        out.append(copy.deepcopy(j.state))
        s = open_day('grocery')   # a neutral closing-time pick (good None) and a theft got back (cost 0)
        fire(s, 'grocery', 'fake_transfer')
        c = s['careers']['grocery']
        inc.on_close(s, c, 'grocery')
        self.assertIsNone(c['incidents']['history'][-1]['good'])
        ev.tick_career(s, c, 'grocery')
        for n in range(1, 30):
            c['ops']['shop_events']['seq'] = n
            c['ops']['shop_events']['pending'] = ev.make_event('theft', n, 'grocery', True)
            ev.choose_career(s, c, 'grocery', dict(event=f'shop-grocery-{n}', choice='report', confirm=True))
            if c['ops']['shop_events']['recent'][-1]['cost'] == 0:
                break
        self.assertEqual(c['ops']['shop_events']['recent'][-1]['cost'], 0)
        validate_state(s)
        out.append(copy.deepcopy(s))
        return out

    def test_live_build_reads_the_new_saves(self):
        import os
        import subprocess
        import sys
        old = os.environ.get('MNL_LIVE_TREE')
        if not old or not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no live tree (MNL_LIVE_TREE)')
        from scripts.strip_new_careers import strip   # 1.9.11: the live tree has no album shop (zpop) yet
        saves = [strip(s, ['zpop'])[0] for s in self.saves()]
        env = dict(os.environ, PYTHONPATH=old)
        r = subprocess.run([sys.executable, '-c', self.PROG], input=json.dumps(saves), capture_output=True, text=True, cwd=old,
                           env=env, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        self.assertEqual(r.stdout.strip(), 'ok')


if __name__ == '__main__':
    unittest.main()
