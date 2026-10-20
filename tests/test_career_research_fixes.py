"""🔬 Review fixes of the research career (game/careers/research.py) and the players' orders (game/research_lab.py): a
step of a paid order shows its answer after two wrong tries like the career's own slips; every step carries the data it
asks about (the field plots on the mean step, the score sheet on the tasting total, the recipe card on the order step,
the blueprint's parts); a recipe takes every order its card allows; a dish's costing lists that dish's own
ingredients; a merged recipe never refills what it already paid."""
import itertools
import unittest.mock
import unittest

from tests.test_career_research import R, RC, clear_desk, data, job_journey, roundtrip, slot_of
from tests.test_research_lab import LabBase, wrong
from game import research_lab as rl
from game.careers import kit
from game.engine import validate_state

DAY = 86400


def builds(job, days=range(1, 40)):
    for day in days:
        for slot in range(6):
            yield R.BUILD[job](kit.rng(R.ID, job, day, slot), day, slot)


@unittest.skipUnless(R, 'research filtered out by MNL_CAREERS')
class Steps(unittest.TestCase):
    def test_every_order_the_recipe_card_allows_passes(self):
        many = 0
        for did, name, main, grams, order in RC.DISHES:
            right = [k for k, _ in order]
            st = dict(id='scale.order', type='order', options=[dict(id=k, label=v) for k, v in order])
            ok = [list(p) for p in itertools.permutations(right) if R.correct(st, list(p), right)]
            self.assertIn(right, ok)
            self.assertNotIn(list(reversed(right)), ok)
            after = RC.DISH_AFTER[did]
            for p in itertools.permutations(right):
                at = {k: i for i, k in enumerate(p)}
                fits = all(at[b] < at[a] for a, before in after.items() for b in before)
                self.assertEqual(R.correct(st, list(p), right), fits)
            many += len(ok) > 1
            self.assertIn(did, RC.DISH_CARD)
        self.assertGreaterEqual(many, 4)   # cơm gà, flan, chè, nước chấm, canh: more than one sensible order
        for b, key, *_ in builds('scale'):
            st = next(s for s in b['steps'] if s['id'] == 'scale.order')
            self.assertEqual(len(st['sheet']), 1)
            self.assertTrue(st['sheet'][0].startswith('Thẻ công thức'))

    def test_another_valid_order_finishes_the_job_and_the_save_validates(self):
        for day in range(3, 30):
            j = job_journey('scale', day=day)
            tid = j.task['id']
            j.act('ask', task=tid)
            _, steps, key = R._active(j.get(tid))
            right = key['scale.order']
            st = next(s for s in steps if s['id'] == 'scale.order')
            alt = next((list(p) for p in itertools.permutations(right) if list(p) != right and R.correct(st, list(p), right)), None)
            if alt is None:
                continue
            for _ in range(20):
                clear_desk(j)
                t = j.get(tid)
                if t['status'] == 'completed':
                    break
                cur = R._active(t)[1][t['at']]
                j.act('rs_step', task=t['id'], step=cur['id'], value=alt if cur['id'] == 'scale.order' else key[cur['id']])
            self.assertEqual(j.get(tid)['status'], 'completed')
            self.assertEqual(j.get(tid)['work']['scale.order'], alt)
            self.assertEqual(j.get(tid)['quality'], 100)
            roundtrip(j)
            return
        self.fail('no scale job with a second valid order')

    def test_the_field_mean_step_shows_the_plots(self):
        for b, key, *_ in builds('field'):
            mean = next(s for s in b['steps'] if s['id'] == 'field.mean')
            plots = next(s for s in b['steps'] if s['id'] == 'field.exclude')['options']
            self.assertEqual(mean['sheet'], [p['label'] for p in plots])

    def test_the_tasting_total_and_winner_show_the_score_sheet(self):
        for b, key, *_ in builds('taste'):
            sheet = next(s for s in b['steps'] if s['id'] == 'taste.exclude')['options']
            for sid in ('taste.total', 'taste.best'):
                st = next(s for s in b['steps'] if s['id'] == sid)
                self.assertEqual(st['sheet'], [row['label'] for row in sheet])

    def test_a_costing_lists_the_dishes_own_ingredients(self):
        for day in range(1, 40):
            for slot in range(6):
                r = kit.rng(R.ID, 'cost', day, slot)
                b, key, *_ = R.BUILD['cost'](r, day, slot)
                did = next(d[0] for d in RC.DISHES if d[1] == b['dish'])
                pool = RC.DISH_INGREDIENTS[did]
                st = next(s for s in b['steps'] if s['id'] == 'cost.allergen')
                listed = st['evidence'].split(': ', 1)[1].split('. ')[0].split(' · ')
                self.assertEqual(len(listed), 5)
                self.assertTrue(set(listed) <= {n.lower() for n, _ in pool})
                self.assertTrue({n.lower() for n, _ in pool[:RC.DISH_CORE]} <= set(listed))
                want = sorted({tag for n, tag in pool if tag and n.lower() in listed})
                self.assertEqual(key['cost.allergen'], want)
        self.assertEqual(RC.DISH_INGREDIENTS['flan'][0][1], 'egg')
        self.assertEqual(RC.DISH_INGREDIENTS['canh'][1][1], 'shrimp')

    def test_the_blueprint_lists_its_parts_and_the_solar_light_senses_light(self):
        for b, key, *_ in builds('proto'):
            st = next(s for s in b['steps'] if s['id'] == 'proto.parts')
            self.assertEqual(sorted(st['sheet']), sorted(RC.PARTS[p] for p in key['proto.parts']))
        solar = next(g for g in RC.GADGETS if g[0] == 'solar')
        self.assertIn('light', solar[2])
        self.assertNotIn('sensor', solar[2])

    def test_the_patent_search_reads_well(self):
        for b, key, *_ in builds('patent'):
            ev = b['steps'][0]['evidence']
            self.assertIn('đã có', ev)
            self.assertNotIn('đã đế', ev)

    def test_the_seed_order_hint_names_boosted_crops(self):
        from game.careers import farm_plus as fp
        boosted = {fp.CROP[c]['name'].lower() for c in rl.seed_crops()}
        hint = rl.SERVICES['giong']['note_hint']
        examples = hint.split('vd: ', 1)[1].rstrip(')').split(', ')
        self.assertTrue(examples and all(x in boosted for x in examples), (examples, boosted))


class LabFixes(LabBase):
    def test_a_wrong_step_shows_the_answer_on_the_second_try(self):
        a, b = self.researcher('rl_fx1'), self.farmer('rl_fxb1')
        self.sell(a, 'giong')
        o = self.order(b, a, 'giong')
        rl.post(self.store, a, None, 'take', dict(order=o['id']))
        steps, key, _ = rl.brief(o['id'], 'giong')
        for i, st in enumerate(steps):
            first = rl.post(self.store, a, None, 'step', dict(order=o['id'], step=st['id'], value=wrong(st, key[st['id']])))
            self.assertFalse(first['correct'])
            self.assertNotIn('Chị Nhàn chỉ', first['message'])
            second = rl.post(self.store, a, None, 'step', dict(order=o['id'], step=st['id'], value=wrong(st, key[st['id']])))
            self.assertIn('Chị Nhàn chỉ: ' + kit.answer_text(st, key[st['id']]).rstrip('.'), second['message'])
            self.assertTrue(second['revealed'])
            out = rl.post(self.store, a, None, 'step', dict(order=o['id'], step=st['id'], value=key[st['id']]))
            self.assertTrue(out['correct'])
        self.assertEqual(self.lab(b)['seed']['n'], rl.SEED_LOW)   # six slips: quality at the floor, the small effect

    def test_a_merged_recipe_never_refills_what_it_paid(self):
        from tests.helpers import Journey
        t0 = 2_000_000_000
        with unittest.mock.patch.object(rl, 'now', lambda: t0):
            j = Journey('pho')
            lab = rl.initial()
            lab['recipe'] = dict(o='sv_' + 'a' * 24, n=4, pct=rl.RECIPE_PCT, per=rl.RECIPE_PER, left=5, until=t0 + DAY, by='Thư', name='SM-10')
            j.state['journey']['lab'] = lab
            rl._on_buyer('mon')(j.state, dict(id='sv_' + 'b' * 24, result=dict(n=rl.RECIPE_USES, by='Lan', name='SM-11')))
            rec = j.state['journey']['lab']['recipe']
            self.assertEqual(rec['left'], 5)
            self.assertEqual(rec['n'], rl.RECIPE_USES)
            self.assertEqual(rec['until'], t0 + rl.RECIPE_DAYS * DAY)
            validate_state(j.state)
            # no running recipe: a fresh one starts full
            j.state['journey']['lab']['recipe'] = None
            rl._on_buyer('mon')(j.state, dict(id='sv_' + 'c' * 24, result=dict(n=rl.RECIPE_USES, by='Lan', name='SM-12')))
            self.assertEqual(j.state['journey']['lab']['recipe']['left'], rl.RECIPE_CAP)


if __name__ == '__main__':
    unittest.main()
