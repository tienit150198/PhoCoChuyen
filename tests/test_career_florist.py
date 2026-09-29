import copy
import json
import unittest

import game.careers.kit as kit
from game import inventory
from game.engine import GameError, public_state, validate_state
from game.careers import florist as FL
from game.careers import food_service as FS
from tests.helpers import Journey


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t


def find_slot(title, days=range(1, 15)):
    for day in days:
        for slot in range(12):
            if FL.make_task(day, slot, 1)['title'] == title:
                return day, slot
    raise AssertionError('no matching order in the order book: ' + title)


GRAD = 'Bó hoa tốt nghiệp cho bạn thân'
APOLOGY = 'Hoa xin lỗi vợ'
CATS = 'Hoa sinh nhật cho mẹ chị Hạnh'
MUMS = 'Bó cúc trắng đi viếng bạn già'
WREATH = 'Kệ hoa viếng cụ Tư đầu hẻm'
OPENING = 'Giỏ hoa khai trương tiệm sửa xe'
PROPOSAL = 'Bó 9 hồng đỏ cầu hôn'
VASE = 'Bình hoa 8/3 cho quầy lễ tân'

# A florist's good answer for each brief.
RECIPES = {
    GRAD: dict(stems=dict(sunflower=3, rose_white=2, babys_breath=3, eucalyptus=2), paper='kraft', ribbon='white',
               card='Chúc mừng tốt nghiệp nha, tương lai rực rỡ như hướng dương!'),
    APOLOGY: dict(stems=dict(rose_pink=5, rose_white=4, babys_breath=3, eucalyptus=2), paper='pink', ribbon='pink',
                  card='Anh xin lỗi em vì đã quên ngày của chúng mình.'),
    CATS: dict(stems=dict(rose_pink=7, rose_white=6), paper='white', ribbon='pink', card='Chúc mừng sinh nhật mẹ, con thương mẹ nhiều!'),
    MUMS: dict(stems=dict(mum_white=10, eucalyptus=3), paper='white', ribbon='white', card='Thành kính phân ưu cùng gia đình.'),
    WREATH: dict(stems=dict(mum_white=16, lily=4, rose_white=3), banner='Thành kính phân ưu · Tổ dân phố 5'),
    OPENING: dict(stems=dict(sunflower=7, rose_red=6, eucalyptus=3), card='Chúc mừng khai trương, làm ăn hồng phát!'),
    PROPOSAL: dict(stems=dict(rose_red=9, rose_white=2, babys_breath=3, eucalyptus=2), paper='black', ribbon='red',
                   card='Mình ở bên nhau mãi mãi nhé. Lấy anh nha!'),
    VASE: dict(stems=dict(rose_pink=5, rose_red=4, babys_breath=3, eucalyptus=2), card='Chúc các chị em ngày 8/3 thật xinh đẹp và hạnh phúc!'),
}


class FloristTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock
        self.j = Journey('florist')

    def tearDown(self):
        kit.clock = self.old

    # --- helpers --------------------------------------------------------------
    def journey(self, title, days=range(1, 15), cull=False):
        day, slot = find_slot(title, days)
        j = Journey('florist', slot=slot, day=day)
        self.stock_up(j, cull=cull)
        self.j = j
        return j

    def stock_up(self, j, qty=20, cull=False):
        if cull:  # a careful florist bins stems with fewer than two days left before a big order
            x = j.c['ext']['inv']
            x['lots'] = [l for l in x['lots'] if l['item'] not in FL.FLOWERS or l['expires'] - j.c['day'] >= 2]
        for it in FL.ITEMS:
            room = 40 - kit.stock(j.c, it['id'])
            if room > 0:
                inventory.add_lot(j.c, it['id'], min(qty, room), 1, 4, 'partner')

    def prep(self, stems, tid=None, soak=9, angle='angled'):
        j = self.j
        tid = tid or j.task['id']
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        for item, q in stems.items():
            for _ in range(q):
                j.act('fl_pick', task=tid, item=item)
        j.act('fl_cut', task=tid, angle=angle)
        j.act('fl_strip', task=tid)
        if soak:
            j.act('fl_soak', task=tid)
            self.clock.t += soak
            j.act('fl_lift', task=tid)
        return tid

    def build(self, recipe, tid=None, **over):
        j = self.j
        r = dict(recipe, **over)
        tid = self.prep(r['stems'], tid)
        n = j.get(tid)['needs']
        j.act('fl_base', task=tid, kind=r.get('base', n['format']))
        if FL.FORMATS[r.get('base', n['format'])]['foam']:
            self.clock.t += FL.FOAM_MIN + 1
        j.act('fl_arrange', task=tid)
        if r.get('base', n['format']) == 'bouquet':
            j.act('fl_wrap', task=tid, paper=r['paper'])
        j.act('fl_ribbon', task=tid, color=r.get('ribbon', 'white'))
        if r.get('banner'):
            j.act('fl_banner', task=tid, text=r['banner'])
        if r.get('card'):
            j.act('fl_card', task=tid, text=r['card'])
        return tid

    def deliver(self, tid, slot=None):
        n = self.j.get(tid)['needs']
        payload = dict(task=tid, confirm=True)
        if n['delivery']:
            payload['slot'] = slot or n['delivery']
        return self.j.act('fl_deliver', **payload)

    def review(self, tid):
        return next(p for p in self.j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def crit(self, tid):
        return {x['key']: x for x in self.review(tid)['feedback']['criteria']}

    # --- happy paths ------------------------------------------------------------
    def test_happy_bouquet_review_and_money(self):
        j = self.journey(GRAD, days=[1])
        money = j.c['money']
        tid = self.build(RECIPES[GRAD])
        price = j.get(tid)['quoted_price']
        self.assertEqual(price, 120)
        r = self.deliver(tid)
        self.assertTrue(r.get('celebrate'))
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(j.c['money'], money + price + FL.SPEC['tip'])
        self.assertEqual(self.review(tid)['stars'], 5)
        self.assertEqual(set(self.crit(tid)), {'meaning', 'look', 'fresh', 'card', 'value', 'speed'})
        validate_state(json.loads(json.dumps(j.state)))

    def test_every_order_has_a_five_star_answer(self):
        for title, recipe in RECIPES.items():
            with self.subTest(title=title):
                self.clock.t += 100
                j = self.journey(title, cull=True)
                tid = self.build(recipe)
                self.deliver(tid)
                self.assertEqual(j.get(tid)['status'], 'completed')
                self.assertEqual(j.get(tid)['mistakes'], 0)
                low = {k: v for k, v in self.crit(tid).items() if v['score'] < 5}
                self.assertEqual(low, {}, title)

    def test_delivery_fee_and_slot(self):
        j = self.journey(OPENING, days=[1])
        tid = self.build(RECIPES[OPENING])
        self.assertEqual(j.get(tid)['quoted_price'], 260 + FL.DELIVERY_FEE)
        with self.assertRaises(GameError):
            j.act('fl_deliver', task=tid, confirm=True)  # the courier needs a time slot
        money = j.c['money']
        self.deliver(tid, slot='14-16')
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 1)
        self.assertEqual(j.c['money'], money + 260 + FL.DELIVERY_FEE)  # late: paid, no tip
        self.assertEqual(self.crit(tid)['delivery']['score'], 2)

    def test_needs_hidden_until_ask(self):
        for view in public_state(self.j.state)['careers']['florist']['tasks']:
            self.assertIsNone(view['needs'])
        raw = json.dumps(public_state(self.j.state)['careers']['florist']['tasks'], ensure_ascii=False)
        for t in self.j.c['tasks']:
            self.assertNotIn(t['needs']['note'], raw)
        with self.assertRaises(GameError):
            self.j.act('fl_pick', item='rose_red')
        self.j.act('ask')
        view = next(v for v in public_state(self.j.state)['careers']['florist']['tasks'] if v['id'] == self.j.task['id'])
        self.assertEqual(view['needs']['note'], self.j.task['needs']['note'])

    # --- meaning & safety ---------------------------------------------------------
    def test_lily_in_a_home_with_cats_is_a_safety_mistake(self):
        # Behaviour change: the lily is no longer refused at the door; it reaches the cat.
        j = self.journey(CATS, days=[1])
        rec = RECIPES[CATS]
        money = j.c['money']
        tid = self.build(rec, stems=dict(rose_pink=6, rose_white=6, lily=1))
        r = self.deliver(tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertIn('mèo', r['message'])
        self.assertEqual(j.c['money'], money)
        post = self.review(tid)
        self.assertEqual(post['stars'], 1)
        self.assertIn('hoa ly', post['text'])
        self.assertTrue(any(p.get('report') for p in j.c['feed']))
        self.assertTrue(j.c['incidents']['follow'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_filler_is_a_soft_warning_with_cats(self):
        j = self.journey(CATS, days=[1])
        tid = self.build(RECIPES[CATS], stems=dict(rose_pink=7, rose_white=6, eucalyptus=2))
        self.deliver(tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        look = self.crit(tid)['look']
        self.assertEqual(look['score'], 4)
        self.assertIn('mèo', look['note'])

    def test_white_chrysanthemum_only_for_funerals(self):
        j = self.journey(APOLOGY, days=[1])
        tid = self.build(RECIPES[APOLOGY], stems=dict(rose_pink=5, mum_white=4, babys_breath=3))
        r = self.deliver(tid)
        self.assertTrue(r.get('refused'))
        self.assertIn('cúc trắng', r['message'])

    def test_condolence_refuses_red_flowers_bright_ribbon_and_happy_card(self):
        j = self.journey(MUMS, days=[1])
        rec = RECIPES[MUMS]
        tid = self.build(rec, ribbon='red', card='Chúc mừng, vui vẻ nhé!')
        r = self.deliver(tid)
        self.assertTrue(r.get('refused'))
        self.assertIn('ruy băng', r['message'])
        j.act('fl_unwrap', task=tid)
        j.act('fl_wrap', task=tid, paper='white')
        j.act('fl_ribbon', task=tid, color='white')
        r = self.deliver(tid)
        self.assertTrue(r.get('refused'))
        self.assertIn('thiệp', r['message'])
        view = next(v for v in public_state(j.state)['careers']['florist']['tasks'] if v['id'] == tid)
        self.assertEqual(view['card_tone'], 'wrong')
        j.act('fl_card', task=tid, text='Kính viếng, thành kính phân ưu.')
        self.deliver(tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['refused'], 2)
        j2 = self.journey(MUMS, days=[1])
        tid = self.build(rec, stems=dict(mum_white=10, rose_red=1, eucalyptus=2))
        r = self.deliver(tid)
        self.assertTrue(r.get('refused'))
        self.assertIn('hồng đỏ', r['message'])

    def test_card_tone_is_accent_insensitive(self):
        self.assertEqual(FL.card_tone('condolence', 'Thành kính phân ưu'), 'fit')
        self.assertEqual(FL.card_tone('condolence', 'thanh kinh phan uu'), 'fit')
        self.assertEqual(FL.card_tone('condolence', 'Chúc mừng'), 'wrong')
        self.assertEqual(FL.card_tone('birthday', 'Chuc mung sinh nhat!'), 'fit')
        self.assertEqual(FL.card_tone('birthday', 'Mãi thương'), 'plain')
        self.assertEqual(FL.card_tone('opening', 'Chúc mừng khai trương hồng phát'), 'fit')
        self.assertEqual(FL.card_tone('opening', 'Chia buồn'), 'wrong')
        self.assertIsNone(FL.card_tone('apology', None))

    def test_plain_card_and_missing_card(self):
        j = self.journey(APOLOGY, days=[1])
        rec = dict(RECIPES[APOLOGY], card=None)
        tid = self.build(rec)
        with self.assertRaises(GameError):
            self.deliver(tid)  # the customer asked for a handwritten card
        j.act('fl_card', task=tid, text='Tặng em.')
        self.deliver(tid)
        self.assertEqual(self.crit(tid)['card']['score'], 3)

    def test_wreath_banner_letters_must_match(self):
        j = self.journey(WREATH, days=[2])
        rec = RECIPES[WREATH]
        tid = self.build(rec, banner='Thành kính phân ưu · Tổ dân phố 3')
        r = self.deliver(tid)
        self.assertTrue(r.get('refused'))
        self.assertIn('băng rôn', r['message'])
        j.act('fl_banner', task=tid, text='Thanh kinh phan uu - To dan pho 5')  # accents matter
        self.assertTrue(self.deliver(tid).get('refused'))
        j.act('fl_banner', task=tid, text='THÀNH KÍNH PHÂN ƯU — TỔ DÂN PHỐ 5')
        self.deliver(tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(j.c['ext']['data']['wreaths'], 1)
        self.assertEqual(self.crit(tid)['card']['label'], 'Băng rôn')
        with self.assertRaises(GameError):
            j2 = self.journey(GRAD, days=[1])
            self.prep(RECIPES[GRAD]['stems'])
            j2.act('fl_base', kind='bouquet')
            j2.act('fl_arrange')
            j2.act('fl_banner', text='Chúc mừng')  # banners only go on wreaths

    def test_wrong_format_refused(self):
        j = self.journey(OPENING, days=[1])
        tid = self.build(RECIPES[OPENING], base='bouquet', paper='kraft')
        r = self.deliver(tid)
        self.assertTrue(r.get('refused'))
        self.assertIn('giỏ', r['message'].lower())

    # --- conditioning -------------------------------------------------------------
    def test_soak_needs_real_seconds_and_cut_stems(self):
        j = self.journey(GRAD, days=[1])
        j.act('ask')
        j.act('fl_pick', item='sunflower')
        with self.assertRaises(GameError):
            j.act('fl_soak')  # dry old cut: recut first
        j.act('fl_cut', angle='angled')
        j.act('fl_soak')
        with self.assertRaises(GameError):
            j.act('fl_pick', item='sunflower')  # stems are in the bucket
        self.clock.t += 3
        r = j.act('fl_lift')
        self.assertIn('chưa kịp', r['message'])
        self.assertFalse(j.task['work']['stems'][0]['h'])
        j.act('fl_soak')
        self.clock.t += FL.SOAK_MIN
        j.act('fl_lift')
        self.assertTrue(j.task['work']['stems'][0]['h'])

    def test_unhydrated_unstripped_straight_cut_lower_freshness(self):
        j = self.journey(GRAD, days=[1])
        j.act('ask')
        for item, q in RECIPES[GRAD]['stems'].items():
            for _ in range(q):
                j.act('fl_pick', item=item)
        j.act('fl_cut', angle='straight')
        self.assertEqual(j.task['mistakes'], 1)
        tid = j.task['id']
        j.act('fl_base', kind='bouquet')
        j.act('fl_arrange')
        j.act('fl_wrap', paper='kraft')
        j.act('fl_ribbon', color='white')
        j.act('fl_card', text=RECIPES[GRAD]['card'])
        self.deliver(tid)
        fresh = self.crit(tid)['fresh']
        self.assertEqual(fresh['score'], 2)
        self.assertIn('cắt thẳng', fresh['note'])
        self.assertIn('tuốt', fresh['note'])

    def test_foam_must_sink_by_itself(self):
        j = self.journey(OPENING, days=[1])
        tid = self.prep(RECIPES[OPENING]['stems'], soak=0)
        j.act('fl_base', kind='basket')
        with self.assertRaises(GameError):
            j.act('fl_arrange')
        pub = public_state(j.state)['careers']['florist']
        self.assertIsNotNone(next(v for v in pub['tasks'] if v['id'] == tid)['work']['foam'])
        j.act('fl_push')
        self.assertEqual(j.task['mistakes'], 1)
        j.act('fl_arrange')
        j.act('fl_ribbon', color='gold')
        j.act('fl_card', text=RECIPES[OPENING]['card'])
        self.deliver(tid)
        fresh = self.crit(tid)['fresh']
        self.assertEqual(fresh['score'], 4)
        self.assertIn('mút', fresh['note'])

    def test_two_soak_buckets(self):
        j = self.j
        day = j.c['day']
        extra = [FL.make_task(day, s, 1) for s in (5, 6)]
        j.c['tasks'].extend(t for t in extra if t['id'] not in {x['id'] for x in j.c['tasks']})
        self.stock_up(j)
        ids = [t['id'] for t in j.c['tasks']][:3]
        self.assertEqual(len(ids), 3)
        for tid in ids:
            j.act('ask', task=tid)
            j.act('fl_pick', task=tid, item='rose_white')
            j.act('fl_cut', task=tid, angle='angled')
        j.act('fl_soak', task=ids[0])
        j.act('fl_soak', task=ids[1])
        with self.assertRaises(GameError):
            j.act('fl_soak', task=ids[2])
        self.assertEqual(len(public_state(j.state)['careers']['florist']['data']['buckets']), 2)
        j.act('fl_lift', task=ids[0])
        j.act('fl_soak', task=ids[2])

    # --- stock & freshness -----------------------------------------------------------
    def test_oldest_stems_come_first_and_wilt(self):
        j = self.journey(APOLOGY, days=[2, 3, 4])
        x = j.c['ext']['inv']
        x['lots'] = [l for l in x['lots'] if l['item'] != 'rose_pink']
        inventory.add_lot(j.c, 'rose_pink', 20, 1, 4, 'partner')
        old = inventory.add_lot(j.c, 'rose_pink', 2, 1, 1, 'partner')  # last day in the cooler
        pub = public_state(j.state)['careers']['florist']['data']['cooler']['rose_pink']
        self.assertEqual(pub['next'], 0)
        self.assertEqual(pub['fresh'][0], 2)
        tid = self.build(RECIPES[APOLOGY])
        self.assertEqual(sum(1 for st in j.get(tid)['work']['stems'] if st['e'] == old['expires']), 2)
        self.deliver(tid)
        self.assertEqual(self.crit(tid)['fresh']['score'], 2)

    def test_wilted_stem_refused(self):
        j = self.journey(APOLOGY, days=[2, 3])
        tid = self.build(RECIPES[APOLOGY])
        j.get(tid)['work']['stems'][0]['e'] = j.c['day'] - 1  # the stem sat on the bench overnight
        r = self.deliver(tid)
        self.assertTrue(r.get('refused'))
        self.assertIn('héo', r['message'])

    def test_uncut_stems_go_back_to_the_bucket(self):
        j = self.journey(GRAD, days=[1])
        j.act('ask')
        before = kit.stock(j.c, 'sunflower')
        j.act('fl_pick', item='sunflower')
        j.act('fl_pick', item='sunflower')
        self.assertEqual(kit.stock(j.c, 'sunflower'), before - 2)
        j.act('fl_remove', item='sunflower')
        spare = j.c['ext']['data']['spare']
        self.assertEqual(len(spare), 1)
        j.act('fl_pick', item='sunflower')  # the loose stem is used before the cooler
        self.assertEqual(kit.stock(j.c, 'sunflower'), before - 2)
        self.assertEqual(j.c['ext']['data']['spare'], [])
        j.act('fl_remove', item='sunflower')
        self.assertEqual(len(j.c['ext']['data']['spare']), 1)
        j.c['ext']['data']['spare'][0]['e'] = j.c['day']
        summary = j.act('end_day', carry_event=True)['summary']
        self.assertEqual(summary['career']['wilted'], 1)
        self.assertEqual(j.c['ext']['data']['spare'], [])
        validate_state(j.state)

    def test_locked_items_by_level(self):
        j = self.journey(GRAD, days=[1])
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('fl_pick', item='carnation')
        with self.assertRaises(GameError):
            j.act('fl_base', kind='vase')
        j.c['xp'] = 90
        j.act('fl_pick', item='carnation')
        j2 = self.journey(VASE, days=[3, 4, 5])
        tid = self.build(RECIPES[VASE])  # the order itself asks for a vase
        self.deliver(tid)
        self.assertEqual(j2.get(tid)['status'], 'completed')

    # --- softer mistakes ---------------------------------------------------------------
    def test_focal_count_parity_and_value(self):
        j = self.journey(PROPOSAL, cull=True)
        tid = self.build(RECIPES[PROPOSAL], stems=dict(rose_red=8, rose_white=2))
        self.deliver(tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')  # accepted, but it shows in the review
        crit = self.crit(tid)
        self.assertEqual(crit['meaning']['score'], 3)
        self.assertIn('số chẵn', crit['meaning']['note'])
        self.assertLess(crit['look']['score'], 5)  # thin, no greenery
        self.assertLess(crit['value']['score'], 5)
        self.assertLess(self.review(tid)['stars'], 5)

    def test_off_palette_and_mixed_message(self):
        j = self.journey(PROPOSAL, cull=True)
        tid = self.build(RECIPES[PROPOSAL], stems=dict(rose_red=9, rose_yellow=2, babys_breath=3, eucalyptus=2), paper='pink')
        self.deliver(tid)
        crit = self.crit(tid)
        self.assertEqual(crit['meaning']['score'], 3)
        self.assertIn('bạn', crit['meaning']['note'])
        self.assertEqual(crit['look']['score'], 3)

    def test_dump_is_waste_and_a_mistake(self):
        j = self.journey(GRAD, days=[1])
        self.prep(dict(sunflower=3))
        with self.assertRaises(GameError):
            j.act('fl_dump')
        j.act('fl_dump', confirm=True)
        self.assertEqual(j.task['work']['stems'], [])
        self.assertEqual(j.task['mistakes'], 1)
        self.assertEqual(j.c['life']['waste'][-1]['item'], 'bouquet')

    # --- integrity -----------------------------------------------------------------
    def test_validation_errors(self):
        j = self.journey(GRAD, days=[1])
        j.act('ask')
        bad = [('fl_pick', dict(item='cactus')), ('fl_pick', dict(item=['rose_red'])), ('fl_cut', dict(angle='zigzag')),
               ('fl_cut', dict(angle='angled')),  # nothing on the bench
               ('fl_base', dict(kind='box')), ('fl_arrange', {}), ('fl_wrap', dict(paper='kraft')),
               ('fl_ribbon', dict(color='white')), ('fl_card', dict(text='')), ('fl_card', dict(text=5)),
               ('fl_card', dict(text='x' * 400)), ('fl_banner', dict(text='Chúc mừng')), ('fl_lift', {}),
               ('fl_push', {}), ('fl_unwrap', {}), ('fl_untie', {}), ('fl_deliver', dict(confirm=True)),
               ('fl_remove', dict(item='rose_red')), ('fl_teleport', {})]
        for name, payload in bad:
            snapshot = json.dumps(j.state, sort_keys=True)
            with self.subTest(name=name, payload=payload):
                with self.assertRaises(GameError):
                    j.act(name, **payload)
                self.assertEqual(json.dumps(j.state, sort_keys=True), snapshot)
        j.act('fl_pick', item='sunflower')
        j.act('fl_pick', item='sunflower')
        j.act('fl_cut', angle='angled')
        with self.assertRaises(GameError):
            j.act('fl_arrange')  # no base chosen
        j.act('fl_base', kind='bouquet')
        with self.assertRaises(GameError):
            j.act('fl_arrange')  # fewer than 3 stems
        with self.assertRaises(GameError):
            j.act('fl_deliver', confirm=True)

    def test_tampered_state_rejected(self):
        j = self.journey(GRAD, days=[1])
        self.prep(dict(sunflower=3))
        cases = [lambda s: s['careers']['florist']['tasks'][0]['needs'].__setitem__('budget', 9999),
                 lambda s: s['careers']['florist']['tasks'][0]['work']['stems'][0].__setitem__('c', 7),
                 lambda s: s['careers']['florist']['tasks'][0]['work']['stems'][0].__setitem__('i', 'gold_rose'),
                 lambda s: s['careers']['florist']['tasks'][0].__setitem__('quoted_price', 5000),
                 lambda s: s['careers']['florist']['tasks'][0]['work'].__setitem__('paper', 'gold'),
                 lambda s: s['careers']['florist']['ext']['data']['spare'].append(dict(item='money', e=1, k=1)),
                 lambda s: s['careers']['florist']['ext']['data']['spare'].extend([dict(item='lily', e=1, k=1)] * 61)]
        for i, mutate in enumerate(cases):
            s = copy.deepcopy(j.state)
            mutate(s)
            with self.subTest(case=i):
                with self.assertRaises(GameError):
                    validate_state(s)

    def test_price_is_server_side(self):
        j = self.journey(GRAD, days=[1])
        tid = self.build(RECIPES[GRAD])
        money = j.c['money']
        j.act('fl_deliver', task=tid, confirm=True, price=99999, budget=99999)
        self.assertEqual(j.c['money'] - money, 120 + FL.SPEC['tip'])

    def test_save_round_trip_mid_work(self):
        j = self.journey(OPENING, days=[1])
        j.act('ask')
        j.act('fl_pick', item='sunflower')
        j.act('fl_cut', angle='angled')
        j.act('fl_soak')
        validate_state(json.loads(json.dumps(j.state)))
        j.act('fl_lift')
        j.act('fl_base', kind='basket')
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        pub = public_state(s)['careers']['florist']
        self.assertIn('cooler', pub['data'])
        self.assertEqual(pub['data']['buckets'], [])
        view = next(v for v in pub['tasks'] if v['id'] == j.task['id'])
        self.assertEqual(view['foam_min'], FL.FOAM_MIN)

    def test_staff_assist_never_breaks(self):
        j = self.journey(GRAD, days=[1])
        j.act('ask')
        j.act('fl_pick', item='sunflower')
        for role in ('prep', 'designer', 'courier', 'patrol'):
            note = FL.assist(j.state, j.c, dict(role=role, name='X'), j.task)
            self.assertTrue(note is None or isinstance(note, str))
        st = j.task['work']['stems'][0]
        self.assertEqual((st['c'], st['s']), (1, True))
        self.assertIsNotNone(FL.assist(j.state, j.c, dict(role='prep', name='X'), None))
        validate_state(j.state)

    def test_all_situations_playable(self):
        j = self.j
        for x in FL.SPEC['situations']:
            self.assertGreaterEqual(len(x['options']), 2)
            for opt in x['options']:
                self.assertTrue(2 <= len(opt['perspectives']) <= 3, opt['id'])
                self.assertLessEqual(opt.get('cost', 0), 80)
                self.assertLessEqual(opt.get('reward', 0), 60)
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_content_and_spec_shape(self):
        spec = FL.SPEC
        self.assertEqual(spec['id'], 'florist')
        self.assertEqual(spec['prefix'], 'fl_')
        self.assertTrue(5 <= len(spec['people']) <= 7)
        self.assertEqual(len(spec['staff']), 4)
        self.assertTrue(5 <= len(spec['situations']) <= 8)
        self.assertEqual(len(spec['stories']), 3)
        ids = {x['id'] for x in spec['inventory']['items']}
        self.assertTrue({'rose_red', 'lily', 'mum_white', 'sunflower', 'babys_breath', 'eucalyptus', 'carnation', 'orchid',
                         'paper_kraft', 'ribbon', 'foam', 'vase', 'card'} <= ids)
        for o in FL.ORDERS:
            self.assertIn(o['occasion'], FL.OCCASIONS)
            self.assertTrue(set(o['palette']) <= set(FL.COLORS))
        json.dumps(FL.content())


CARDS = dict(birthday='Chúc mừng sinh nhật, tuổi mới thật vui!', condolence='Thành kính phân ưu cùng gia đình.',
             opening='Chúc mừng khai trương, làm ăn hồng phát!', apology='Anh xin lỗi, tha thứ cho anh nhé.',
             oct20='Kính chúc cô ngày 20/10 thật vui, cảm ơn cô!', mar8='Chúc mừng ngày 8/3, luôn xinh đẹp và hạnh phúc!',
             graduation='Chúc mừng tốt nghiệp, tương lai rực rỡ!', proposal='Mình ở bên nhau mãi mãi nhé. Lấy anh nha!')


class Shop:
    """Plays the florist's bench like a careful florist (used by the day tests)."""

    def __init__(self, test, j):
        self.test, self.j = test, j

    def stock_up(self, item, qty):
        c = self.j.c
        if kit.stock(c, item) < qty:
            x = c['ext']['inv']
            x['lots'] = [l for l in x['lots'] if l['item'] != item or l['expires'] - c['day'] >= 2]
            inventory.add_lot(c, item, qty + 2, 1, 4, 'partner')

    def compose(self, sp):
        """A bunch that fits the brief: meaning, palette, parity, stem range and value."""
        c = self.j.c
        occ = sp['occasion']

        def ok(f):
            return (occ not in f['taboo'] and occ not in f['bad'] and f['unlock'] <= kit.level(c)
                    and not (sp['cats'] and f.get('cats')))
        stems = {}
        if sp['focal']:
            stems[sp['focal']['item']] = sp['focal']['count']
        if not sp['cats']:
            stems['eucalyptus'] = 2
            stems['babys_breath'] = 2
        mains = sorted((f for f in FL.FLOWERS.values() if f['role'] == 'focal' and f['color'] in sp['palette'] and ok(f)
                        and f['id'] != (sp['focal'] or {}).get('item')), key=lambda f: -FL.ITEM_INDEX[f['id']]['price'])

        def value():
            return sum(FL.ITEM_INDEX[k]['price'] * q for k, q in stems.items()) + FL.SPEC['prices'][sp['format']]

        def total():
            return sum(stems.values())

        def focal_total():
            return sum(q for k, q in stems.items() if FL.FLOWERS[k]['role'] == 'focal')
        i = 0
        while mains and (value() < 0.9 * sp['budget'] or total() < sp['stems'][0]) and total() < sp['stems'][1] - 1:
            f = mains[i % len(mains)]['id']
            stems[f] = stems.get(f, 0) + 1
            i += 1
        exempt = sp['focal'] and stems.get(sp['focal']['item']) == sp['focal']['count']
        if FL.OCCASIONS[occ]['celebrate'] and focal_total() % 2 == 0 and not exempt and mains:
            f = mains[0]['id']
            stems[f] = stems.get(f, 0) + 1
        return stems

    def ask_all(self, tid):
        j = self.j
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        t = j.get(tid)
        for topic in t['needs']['hidden']:
            if topic not in j.get(tid)['asked']:
                j.act('fl_ask', task=tid, topic=topic)

    def cull(self):
        """A careful florist bins stems with fewer than two days left before an order."""
        c = self.j.c
        x = c['ext']['inv']
        x['lots'] = [l for l in x['lots'] if l['item'] not in FL.FLOWERS or l['expires'] - c['day'] >= 2]

    def make_piece(self, tid, sp):
        j = self.j
        self.cull()
        for k in ('ribbon', 'card', 'paper_white', 'foam', 'basket', 'vase', 'stand', 'banner'):
            self.stock_up(k, 6)
        stems = self.compose(sp)
        for k, q in stems.items():
            self.stock_up(k, q)
        for k, q in stems.items():
            for _ in range(q):
                j.act('fl_pick', task=tid, item=k)
        j.act('fl_cut', task=tid, angle='angled')
        j.act('fl_strip', task=tid)
        fm = FL.FORMATS[sp['format']]
        if fm['soak']:
            j.act('fl_soak', task=tid)
            self.test.clock.t += FL._soak_min(j.c) + 1
            j.act('fl_lift', task=tid)
        j.act('fl_base', task=tid, kind=sp['format'])
        if fm['foam']:
            self.test.clock.t += FL.FOAM_MIN + 1
        j.act('fl_arrange', task=tid)
        if sp['format'] == 'bouquet':
            j.act('fl_wrap', task=tid, paper='white')
        j.act('fl_ribbon', task=tid, color='white')
        if sp['banner']:
            j.act('fl_banner', task=tid, text=sp['banner'])
        if sp['card']:
            j.act('fl_card', task=tid, text=CARDS[sp['occasion']])
        if FL._plan(j.c)['mod'] == 'rain' and sp['delivery']:
            j.act('fl_cover', task=tid)

    def make(self, tid, deliver=True):
        j = self.j
        self.ask_all(tid)
        t = j.get(tid)
        n = FL._total(t)
        for i in range(n):
            self.make_piece(tid, FL._spec(j.get(tid), i))
            if i < n - 1:
                j.act('fl_done', task=tid)
        if not deliver:
            return None
        payload = dict(task=tid, confirm=True)
        if t['needs']['delivery']:
            payload['slot'] = t['needs']['delivery']
        return j.act('fl_deliver', **payload)

    def resolve_open_event(self, pick=0):
        pl = FL._plan(self.j.c)
        e = FS.open_event(pl)
        if not e:
            return None
        spec = FL.EVENT_INDEX[e['id']]
        choices = [x for x in spec['choices'] if FS.choice_ok(None, self.j.c, pl, spec, x) is None]
        return self.j.act('fl_event', event=e['id'], choice=choices[min(pick, len(choices) - 1)]['id'])

    def pins(self):
        j = self.j
        p = FL._plan(j.c)['rules'].get('pins')
        while isinstance(p, dict) and p['status'] == 'open':
            for k in FL.PIN_RECIPE:
                self.stock_up(k, 2)
            j.act('fl_pin')
            p = FL._plan(j.c)['rules']['pins']

    def play_day(self, max_orders=8, pick=0):
        j = self.j
        if not j.c['open']:
            j.act('start_day')
        served = 0
        while served < max_orders:
            self.resolve_open_event(pick)
            self.pins()
            todo = [t for t in j.c['tasks'] if t['status'] not in FS.DONE]
            if not todo:
                break
            r = self.make(todo[0]['id'])
            self.test.assertFalse(r.get('refused'), r['message'])
            served += 1
        self.resolve_open_event(pick)
        self.pins()
        return j.act('end_day')


class FloristDayTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock
        self.j = Journey('florist')
        self.shop = Shop(self, self.j)

    def tearDown(self):
        kit.clock = self.old

    def at(self, pred, days=range(2, 30), slots=range(0, 8)):
        for d in days:
            for slot in slots:
                t = FL.make_task(d, slot, 1)
                if pred(t):
                    j = Journey('florist', slot=slot, day=d)
                    self.j, self.shop.j = j, j
                    return j
        self.fail('no such order')

    def view(self, tid, j=None):
        j = j or self.j
        return next(v for v in public_state(j.state)['careers']['florist']['tasks'] if v['id'] == tid)

    def force_event(self, eid, j=None):
        j = j or self.j
        pl = FL._plan(j.c)
        pl['events'] = [dict(id=eid, at=0, status='waiting', choice=None, good=None, note=None)]
        FS.trigger(j.state, j.c, pl, FL.EVENT_INDEX)
        self.assertEqual(FS.open_event(pl)['id'], eid)
        return pl

    def crit(self, tid):
        r = next(p for p in self.j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
        return {x['key']: x for x in r['feedback']['criteria']}

    def delivery(self, tid):
        t = self.j.get(tid)
        payload = dict(task=tid, confirm=True)
        if t['needs']['delivery']:
            payload['slot'] = t['needs']['delivery']
        return payload

    # --- consultation -------------------------------------------------------------
    def test_day_one_says_everything(self):
        for slot in range(8):
            t = FL.make_task(1, slot, 1)
            self.assertEqual(t['needs']['hidden'], [])
            self.assertEqual(t['needs']['style'], 'single')
        self.assertEqual(FL.make_task(1, 0, 1)['title'], GRAD)
        titles = [FL.make_task(1, s, 1)['title'] for s in range(6)]
        self.assertEqual(len(set(titles)), 6)  # no repeats on the first day

    def test_hidden_topics_grow_with_days(self):
        self.assertTrue(all(len(FL.make_task(d, s, 1)['needs']['hidden']) <= 1 for d in (2, 3) for s in range(8)))
        self.assertTrue(any(len(FL.make_task(d, s, 1)['needs']['hidden']) == 2 for d in (4, 5, 6) for s in range(8)))

    def test_palette_stays_with_the_customer_until_asked(self):
        j = self.at(lambda t: 'palette' in t['needs']['hidden'] and t['needs']['style'] == 'single'
                    and t['guest']['kind'] not in ('chatty', 'rush'))
        tid = j.task['id']
        j.act('ask', task=tid)
        v = self.view(tid)
        self.assertIsNone(v['needs']['palette'])
        self.assertNotIn('palette', v['needs']['clues'])
        secret = j.get(tid)['needs']['clues']['palette']
        self.assertNotIn(secret, json.dumps(public_state(j.state), ensure_ascii=False))
        before = j.get(tid)['patience']
        r = j.act('fl_ask', task=tid, topic='palette')
        self.assertIn(secret, r['message'])
        self.assertEqual(j.get(tid)['patience'], before - FL.ASK_COST)
        self.assertEqual(self.view(tid)['needs']['palette'], j.get(tid)['needs']['palette'])
        with self.assertRaises(GameError):
            j.act('fl_ask', task=tid, topic='palette')  # asked already
        known = [t for t in ('recipient', 'slot') if t not in j.get(tid)['needs']['hidden']]
        with self.assertRaises(GameError):
            j.act('fl_ask', task=tid, topic=known[0])  # the customer said it up front
        with self.assertRaises(GameError):
            j.act('fl_ask', task=tid, topic='weather')

    def test_cat_warning_only_after_asking_about_the_recipient(self):
        j = self.at(lambda t: t['needs']['cats'] and 'recipient' in t['needs']['hidden'] and t['needs']['style'] == 'single'
                    and t['guest']['kind'] not in ('regular', 'chatty'), days=range(2, 60))
        tid = j.task['id']
        j.act('ask', task=tid)
        self.assertIsNone(self.view(tid)['needs']['cats'])
        self.assertNotIn('mèo', json.dumps(self.view(tid), ensure_ascii=False))  # not even in the title
        self.assertNotIn('mèo', FL.known_request(j.c, j.get(tid)))
        j.act('fl_ask', task=tid, topic='recipient')
        self.assertTrue(self.view(tid)['needs']['cats'])
        self.assertIn('mèo', FL.known_request(j.c, j.get(tid)))

    def test_slot_hidden_until_asked_but_delivery_known(self):
        j = self.at(lambda t: 'slot' in t['needs']['hidden'] and t['guest']['kind'] != 'chatty')
        tid = j.task['id']
        j.act('ask', task=tid)
        n = self.view(tid)['needs']
        self.assertIsNone(n['delivery'])
        self.assertTrue(n['deliver'])
        self.assertIn('chưa hỏi giờ', FL.known_request(j.c, j.get(tid)))

    def test_chatty_customer_answers_two_questions(self):
        j = self.at(lambda t: t['guest']['kind'] == 'chatty' and len(t['needs']['hidden']) == 2, days=range(4, 60))
        tid = j.task['id']
        j.act('ask', task=tid)
        first = j.get(tid)['needs']['hidden'][0]
        r = j.act('fl_ask', task=tid, topic=first)
        self.assertEqual(len(r['topics']), 2)
        self.assertEqual(sorted(j.get(tid)['asked']), sorted(j.get(tid)['needs']['hidden']))

    def test_regular_knows_the_recipient(self):
        j = self.at(lambda t: t['guest']['kind'] == 'regular' and 'recipient' in t['needs']['hidden'], days=range(2, 60))
        self.assertIn('recipient', j.task['asked'])

    def test_asked_order_scores_five_stars(self):
        j = self.at(lambda t: len(t['needs']['hidden']) == 2 and t['needs']['style'] == 'single'
                    and t['guest']['kind'] != 'picky', days=range(4, 40))
        FL._plan(j.c)['events'] = []
        tid = j.task['id']
        self.shop.make(tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        low = {k: v for k, v in self.crit(tid).items() if v['score'] < 5}
        self.assertEqual(low, {})

    # --- sets -------------------------------------------------------------------
    def test_set_is_made_piece_by_piece_and_delivered_once(self):
        j = self.at(lambda t: t['needs']['style'] == 'set' and t['needs']['party'][0]['format'] != t['needs']['party'][1]['format'],
                    days=range(3, 40))
        FL._plan(j.c)['events'] = []
        tid = j.task['id']
        self.shop.ask_all(tid)
        t = j.get(tid)
        fee = FL.DELIVERY_FEE if t['needs']['delivery'] else 0
        self.assertEqual(t['quoted_price'], sum(p['budget'] for p in t['needs']['party']) + fee)
        self.assertEqual(self.view(tid)['pieces_total'], 2)
        with self.assertRaises(GameError):
            j.act('fl_done', task=tid)  # nothing made yet
        self.shop.make_piece(tid, FL._spec(j.get(tid), 0))
        with self.assertRaises(GameError):
            j.act('fl_tab', task=tid, index=1)  # piece 1 is on the bench, unfinished business
        j.act('fl_done', task=tid)
        self.assertEqual(j.get(tid)['cur'], 1)
        with self.assertRaises(GameError):
            j.act('fl_deliver', **self.delivery(tid))  # piece 2 missing
        self.shop.make_piece(tid, FL._spec(j.get(tid), 1))
        j.act('fl_deliver', **self.delivery(tid))
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(len(t['served']['pieces']), 2)
        self.assertEqual({k: v for k, v in self.crit(tid).items() if v['score'] < 5}, {})
        validate_state(json.loads(json.dumps(j.state)))

    def test_set_refused_piece_comes_back_to_the_bench(self):
        j = self.at(lambda t: t['needs']['style'] == 'set' and t['needs']['occasion'] == 'oct20', days=range(3, 40))
        FL._plan(j.c)['events'] = []
        tid = j.task['id']
        self.shop.ask_all(tid)
        self.shop.make_piece(tid, FL._spec(j.get(tid), 0))
        j.act('fl_done', task=tid)
        self.shop.make_piece(tid, FL._spec(j.get(tid), 1))
        j.get(tid)['pieces'][0]['card'] = 'Thành kính phân ưu'  # a wrong card slipped into piece 1
        r = j.act('fl_deliver', **self.delivery(tid))
        self.assertTrue(r.get('refused'))
        self.assertIn('món 1', r['message'])
        t = j.get(tid)
        self.assertEqual(t['cur'], 0)
        self.assertIsNotNone(t['pieces'][1])
        self.assertEqual(t['work']['card'], 'Thành kính phân ưu')
        j.act('fl_card', task=tid, text=CARDS['oct20'])
        j.act('fl_deliver', **self.delivery(tid))
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(self.crit(tid)['care']['score'], 2)

    def test_set_piece_can_be_reopened(self):
        j = self.at(lambda t: t['needs']['style'] == 'set', days=range(3, 40))
        tid = j.task['id']
        self.shop.ask_all(tid)
        self.shop.make_piece(tid, FL._spec(j.get(tid), 0))
        j.act('fl_done', task=tid)
        j.act('fl_tab', task=tid, index=0)  # take piece 1 back (piece 2 not started)
        t = j.get(tid)
        self.assertEqual((t['cur'], t['pieces'][0]), (0, None))
        self.assertTrue(t['work']['arranged'])
        with self.assertRaises(GameError):
            j.act('fl_tab', task=tid, index=1)  # piece 1 is back on the bench
        j.act('fl_done', task=tid)
        self.assertEqual(j.get(tid)['cur'], 1)

    # --- luck of the day ------------------------------------------------------------
    def test_modifier_is_deterministic_and_stored(self):
        for d in range(1, 12):
            self.assertEqual(FS.pick_mod(FL.ID, d, FL.MODS)['id'], FS.pick_mod(FL.ID, d, FL.MODS)['id'])
        self.assertEqual(FS.pick_mod(FL.ID, 1, FL.MODS)['id'], 'normal')
        pl = FL._plan(self.j.c)
        self.assertIs(FL._plan(self.j.c), pl)
        view = public_state(self.j.state)['careers']['florist']['data']['day']
        self.assertEqual(view['mod']['id'], pl['mod'])

    def test_rain_needs_cover_for_deliveries(self):
        j = self.at(lambda t: FS.pick_mod(FL.ID, t['day'], FL.MODS)['id'] == 'rain' and t['needs']['delivery']
                    and t['needs']['style'] == 'single' and t['guest']['kind'] != 'picky', days=range(2, 60))
        FL._plan(j.c)['events'] = []
        tid = j.task['id']
        self.shop.ask_all(tid)
        sp = FL._spec(j.get(tid))
        FL._plan(j.c)['mod'] = 'normal'  # built on a dry morning…
        with self.assertRaises(GameError):
            j.act('fl_cover', task=tid)
        self.shop.make_piece(tid, sp)
        FL._plan(j.c)['mod'] = 'rain'  # …then it starts raining
        j.act('fl_deliver', **self.delivery(tid))
        if j.get(tid)['status'] != 'completed':  # the customer may hand the wet bouquet back once
            j.act('fl_deliver', **self.delivery(tid))
        self.assertIn('mưa', self.crit(tid)['fresh']['note'])
        self.assertEqual(self.crit(tid)['fresh']['score'], 4)

    def test_cover_only_for_deliveries_in_rain(self):
        j = self.j
        FL._plan(j.c)['mod'] = 'rain'
        tid = j.task['id']
        self.shop.ask_all(tid)
        self.shop.make_piece(tid, FL._spec(j.get(tid)))  # GRAD: picked up at the shop
        with self.assertRaises(GameError):
            j.act('fl_cover', task=tid)

    def test_heat_needs_a_longer_soak(self):
        j = self.j
        FL._plan(j.c)['mod'] = 'heat'
        self.assertEqual(FL._soak_min(j.c), FL.SOAK_MIN + 4)
        self.shop.stock_up('rose_white', 4)
        j.act('ask')
        j.act('fl_pick', item='rose_white')
        j.act('fl_cut', angle='angled')
        j.act('fl_soak')
        self.clock.t += FL.SOAK_MIN + 1
        r = j.act('fl_lift')
        self.assertIn('chưa kịp', r['message'])
        self.assertEqual(public_state(j.state)['careers']['florist']['data']['soak_min'], FL.SOAK_MIN + 4)

    def test_market_gift_arrives_once(self):
        j = self.at(lambda t: FS.pick_mod(FL.ID, t['day'], FL.MODS)['id'] == 'market', days=range(3, 80))
        before = kit.stock(j.c, 'rose_pink')
        FL.on_start(j.state, j.c)
        after = kit.stock(j.c, 'rose_pink')
        FL.on_start(j.state, j.c)
        self.assertEqual(kit.stock(j.c, 'rose_pink'), after)
        self.assertIn(after - before, (0, 6))
        self.assertTrue(FL._plan(j.c)['rules']['market_gift'])
        validate_state(j.state)

    # --- surprises ----------------------------------------------------------------
    def test_event_opens_after_a_delivery_and_blocks_the_next(self):
        j = self.j
        pl = FL._plan(j.c)
        pl['events'] = [dict(id='overpay', at=1, status='waiting', choice=None, good=None, note=None)]
        r = self.shop.make(j.task['id'])
        self.assertIn('chuyển khoản dư', r['message'])
        view = public_state(j.state)['careers']['florist']['data']['day']
        self.assertEqual(view['open_event']['id'], 'overpay')
        nxt = next(t for t in j.c['tasks'] if t['status'] not in FS.DONE)
        self.shop.make(nxt['id'], deliver=False)
        with self.assertRaises(GameError):
            j.act('fl_deliver', **self.delivery(nxt['id']))
        with self.assertRaises(GameError):
            j.act('fl_event', event='overpay', choice='nope')
        j.act('fl_event', event='overpay', choice='return')
        j.act('fl_deliver', **self.delivery(nxt['id']))
        self.assertEqual(j.get(nxt['id'])['status'], 'completed')
        validate_state(j.state)

    def test_waiting_surprises_stay_secret(self):
        pl = FL._plan(self.j.c)
        pl['events'] = [dict(id='funeral', at=3, status='waiting', choice=None, good=None, note=None)]
        view = public_state(self.j.state)['careers']['florist']['data']['day']
        self.assertEqual(view['events'], [])
        self.assertNotIn('funeral', json.dumps(public_state(self.j.state)['careers']['florist']['data']))

    def test_every_event_choice_is_playable(self):
        self.assertGreaterEqual(len(FL.EVENTS), 8)
        for eid, spec in FL.EVENT_INDEX.items():
            for choice in spec['choices']:
                j = Journey('florist')
                self.j, self.shop.j = j, j
                for k in ('rose_pink', 'lily', 'babys_breath', 'rose_red', 'paper_kraft', 'card'):
                    self.shop.stock_up(k, 6)
                delta = 200 - j.c['money']
                j.c['money'] += delta
                j.c['ops']['finance']['opening_balance'] += delta
                self.force_event(eid, j)
                money = j.c['money']
                r = j.act('fl_event', event=eid, choice=choice['id'])
                self.assertTrue(r['message'], (eid, choice['id']))
                e = next(x for x in FL._plan(j.c)['events'] if x['id'] == eid)
                self.assertEqual((e['status'], e['choice']), ('done', choice['id']))
                if choice.get('cost'):
                    self.assertEqual(j.c['money'], money - choice['cost'])
                validate_state(json.loads(json.dumps(j.state)))

    def test_pins_pay_when_complete(self):
        j = self.j
        self.force_event('pins')
        j.act('fl_event', choice='half')
        pins = FL._plan(j.c)['rules']['pins']
        self.assertEqual((pins['goal'], pins['status']), (2, 'open'))
        for k in FL.PIN_RECIPE:
            self.shop.stock_up(k, 4)
        white = kit.stock(j.c, 'rose_white')
        money = j.c['money']
        j.act('fl_pin')
        self.assertEqual(kit.stock(j.c, 'rose_white'), white - 1)
        self.assertEqual(j.c['money'], money)
        j.act('fl_pin')
        self.assertEqual(j.c['money'], money + 2 * 14)
        self.assertEqual(FL._plan(j.c)['rules']['pins']['status'], 'sent')
        with self.assertRaises(GameError):
            j.act('fl_pin')
        e = next(x for x in FL._plan(j.c)['events'] if x['id'] == 'pins')
        self.assertTrue(e['good'])

    def test_pins_fail_when_left_too_long(self):
        j = self.j
        self.force_event('pins')
        j.act('fl_event', choice='all')
        FL._plan(j.c)['rules']['pins']['due'] = 0
        self.shop.make(j.task['id'])
        self.assertEqual(FL._plan(j.c)['rules']['pins']['status'], 'failed')
        e = next(x for x in FL._plan(j.c)['events'] if x['id'] == 'pins')
        self.assertFalse(e['good'])

    def test_power_cut_caps_freshness(self):
        j = self.j
        self.force_event('power')
        j.act('fl_event', choice='ignore')
        tid = j.task['id']
        self.shop.make(tid)
        fresh = self.crit(tid)['fresh']
        self.assertEqual(fresh['score'], 3)
        self.assertIn('mất điện', fresh['note'])

    def test_bruised_roses_show_in_the_look(self):
        j = self.at(lambda t: t['needs']['style'] == 'single' and t['needs']['focal'] and t['needs']['focal']['item'] == 'rose_red',
                    days=range(1, 40))
        self.force_event('bruised')
        j.act('fl_event', choice='use')
        tid = j.task['id']
        self.shop.make(tid)
        self.assertIn('dập', self.crit(tid)['look']['note'])

    def test_influencer_clip_after_a_perfect_order(self):
        j = self.j
        self.force_event('influencer')
        j.act('fl_event', choice='welcome')
        r = self.shop.make(j.task['id'])
        self.assertIn('Clip', r['message'])
        e = next(x for x in FL._plan(j.c)['events'] if x['id'] == 'influencer')
        self.assertTrue(e['good'])

    def test_unanswered_event_is_missed_at_close(self):
        j = self.j
        self.force_event('photo')
        r = j.act('end_day')
        evs = r['summary']['career']['events']
        self.assertTrue(any(x['id'] == 'photo' and x['good'] is False for x in evs))

    # --- integrity -------------------------------------------------------------------
    def test_tampered_new_fields_rejected(self):
        j = self.at(lambda t: t['needs']['style'] == 'set', days=range(3, 40))
        self.shop.ask_all(j.task['id'])
        FL._plan(j.c)
        cases = [lambda t: t.__setitem__('asked', ['weather']),
                 lambda t: t.__setitem__('asked', ['palette', 'palette']),
                 lambda t: t.__setitem__('pieces', [None]),
                 lambda t: t.__setitem__('cur', 5),
                 lambda t: t['work'].__setitem__('cover', 'yes'),
                 lambda t: t['needs']['party'][1].__setitem__('budget', 999),
                 lambda t: t.__setitem__('guest', dict(kind='generous', emoji='x', label='y'))]
        for i, mutate in enumerate(cases):
            s = copy.deepcopy(j.state)
            mutate(s['careers']['florist']['tasks'][0])
            with self.subTest(case=i):
                with self.assertRaises(GameError):
                    validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['florist']['ext']['data']['plan']['rules']['pins'] = dict(goal=99, done=0, pay=14, due=3, status='open')
        with self.assertRaises(GameError):
            validate_state(s)

    def test_old_save_upgrades(self):
        j = self.at(lambda t: t['needs']['hidden'] and t['needs']['style'] == 'single', days=range(2, 40))
        tid = j.task['id']
        j.act('ask', task=tid)
        s = copy.deepcopy(j.state)
        c = s['careers']['florist']
        for t in c['tasks']:
            for k in ('guest', 'gen', 'asked', 'cur', 'pieces'):
                t.pop(k, None)
            t['work'].pop('cover', None)
            t['needs'] = {k: v for k, v in t['needs'].items() if k not in ('style', 'clues', 'hidden')}
        for k in ('plan', 'regulars', 'grades', 'ev_hist', 'pins'):
            c['ext']['data'].pop(k, None)
        view = public_state(s)['careers']['florist']
        self.assertTrue(all('guest' in t for t in view['tasks']))
        validate_state(s)
        t = next(x for x in s['careers']['florist']['tasks'] if x['id'] == tid)
        self.assertEqual(sorted(t['asked']), sorted(t['needs']['hidden']))  # what was heard stays heard
        from game.engine import apply_action
        s, _ = apply_action(s, 'florist', 'fl_pick', dict(task=tid, item='rose_white'))
        validate_state(s)

    def test_streak_bonus_and_grade_on_close(self):
        j = self.j
        FL._plan(j.c)['events'] = []
        j.c['life']['streak'] = 4
        money = j.c['money']
        self.shop.make(j.task['id'])
        self.assertTrue(FL._plan(j.c)['streak_paid'])
        nxt = next(t for t in j.c['tasks'] if t['status'] not in FS.DONE)
        self.shop.make(nxt['id'])
        r = j.act('end_day')
        g = r['summary']['career']['grade']
        self.assertIn(g['letter'], ('S', 'A'))
        self.assertEqual(j.c['ext']['data']['grades'][-1]['letter'], g['letter'])
        self.assertIn('tomorrow', r['summary']['career'])
        self.assertGreater(j.c['money'], money)

    def test_autoplay_ten_days(self):
        j = self.j
        styles, events, mods = set(), set(), set()
        for _ in range(10):
            j.c['xp'] = max(j.c['xp'], 90)
            r = self.shop.play_day(max_orders=6)
            s = r['summary']['career']
            validate_state(json.loads(json.dumps(j.state)))
            events |= {e['id'] for e in s['events']}
            styles |= {t['needs']['style'] for t in j.c['tasks']}
            mods.add(s['today']['label'])
        self.assertEqual(j.c['day'], 11)
        self.assertGreaterEqual(len(events), 5)
        self.assertEqual(styles, {'single', 'set'})
        self.assertGreaterEqual(len(mods), 4)
        self.assertEqual(len(j.c['ext']['data']['grades']), 10)


class FloristConsequenceTests(unittest.TestCase):
    """Làm sai thì phải chịu: slips at the hand-off, the customer's reaction, stars."""
    setUp, tearDown = FloristTests.setUp, FloristTests.tearDown
    journey, stock_up, prep, build, deliver, review = (FloristTests.journey, FloristTests.stock_up, FloristTests.prep,
                                                       FloristTests.build, FloristTests.deliver, FloristTests.review)

    def paid(self, tid, n0):
        return sum(e['amount'] for e in self.j.c['ops']['finance']['ledger'][n0:] if e['ref'] == tid)

    def hand_over(self, tid, slot=None):
        r = self.deliver(tid, slot)
        if self.j.get(tid)['status'] != 'completed':
            r = self.deliver(tid, slot)
        return r

    def test_right_bouquet_no_slips(self):
        j = self.journey(GRAD, days=[1], cull=True)
        tid = self.build(RECIPES[GRAD])
        n0 = len(j.c['ops']['finance']['ledger'])
        self.deliver(tid)
        t = j.get(tid)
        self.assertFalse(t.get('slips'))
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertEqual(self.review(tid)['stars'], 5)
        self.assertGreaterEqual(self.paid(tid, n0), t['quoted_price'])

    def test_plain_card_is_smaller_than_a_mixed_message(self):
        j = self.journey(APOLOGY, days=[1], cull=True)
        tid = self.build(RECIPES[APOLOGY], card='Tặng em.')
        self.hand_over(tid)
        plain = self.review(tid)
        j = self.journey(APOLOGY, days=[1], cull=True)
        tid = self.build(RECIPES[APOLOGY], stems=dict(rose_pink=5, rose_yellow=4, babys_breath=3, eucalyptus=2))
        self.hand_over(tid)
        mixed = self.review(tid)
        self.assertLessEqual(mixed['stars'], 3)
        self.assertGreater(plain['stars'], mixed['stars'])
        self.assertIn('hờ hững', mixed['text'])
        self.assertIn('thiệp chung chung', plain['text'])

    def test_short_focal_count_costs_and_never_pays_twice(self):
        j = self.journey(PROPOSAL, days=range(1, 15), cull=True)
        tid = self.build(RECIPES[PROPOSAL], stems=dict(rose_red=5, rose_white=2, babys_breath=3, eucalyptus=2))
        n0 = len(j.c['ops']['finance']['ledger'])
        self.hand_over(tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        post = self.review(tid)
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('Đặt 9 cành hồng đỏ', post['text'])
        self.assertIn(t['reaction']['kind'], ('grumble', 'discount', 'refund', 'walkout'))
        self.assertEqual(self.paid(tid, n0), t['quoted_price'] - t['reaction']['cut'])
        money = j.c['money']
        from game import consequences as cq
        cq.react(j.state, j.c, t, t['quoted_price'])
        with self.assertRaises(GameError):
            self.deliver(tid)
        self.assertEqual(j.c['money'], money)
        validate_state(json.loads(json.dumps(j.state)))

    def test_late_delivery_is_a_small_slip(self):
        j = self.journey(OPENING, days=[1], cull=True)
        tid = self.build(RECIPES[OPENING])
        self.deliver(tid, '14-16')
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual([x['code'] for x in t['slips']], ['late'])
        self.assertEqual(self.review(tid)['stars'], 4)

    def test_funeral_flower_refused_then_fixed_is_remembered(self):
        j = self.journey(MUMS, days=[1], cull=True)
        tid = self.build(RECIPES[MUMS], stems=dict(mum_white=10, rose_red=1, eucalyptus=2))
        self.assertTrue(self.deliver(tid).get('refused'))
        j.act('fl_unwrap', task=tid)
        j.act('fl_untie', task=tid)
        j.act('fl_remove', task=tid, item='rose_red')
        j.act('fl_arrange', task=tid)
        j.act('fl_wrap', task=tid, paper='white')
        j.act('fl_ribbon', task=tid, color='white')
        self.deliver(tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual([x['code'] for x in t['slips']], ['returned'])
        post = self.review(tid)
        self.assertLessEqual(post['stars'], 4)
        self.assertIn('hồng đỏ', post['text'])
        validate_state(json.loads(json.dumps(j.state)))


class FloristCareTests(unittest.TestCase):
    """Chăm tiệm qua nhiều ngày: tủ mát, đơn đặt trước, gói hoa định kỳ, sổ khách quen."""

    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock
        self.j = Journey('florist')
        self.shop = Shop(self, self.j)

    def tearDown(self):
        kit.clock = self.old

    @property
    def d(self):
        return self.j.c['ext']['data']

    def next_day(self):
        j = self.j
        FL._plan(j.c)['events'] = [e for e in FL._plan(j.c)['events'] if e['status'] != 'open']
        r = j.act('end_day', carry_event=True)
        j.act('start_day')
        validate_state(json.loads(json.dumps(j.state)))
        return r['summary']['career']

    def lot(self, item, qty, life=4):
        return inventory.add_lot(self.j.c, item, qty, 2, life, 'partner')['id']

    def exp(self, lid):
        return next(l for l in self.j.c['ext']['inv']['lots'] if l['id'] == lid)['expires']

    def money(self):
        return self.j.c['money']

    def drop(self, *items):
        x = self.j.c['ext']['inv']
        x['lots'] = [l for l in x['lots'] if l['item'] not in items]

    def view(self):
        return public_state(self.j.state)['careers']['florist']['data']['care']

    def book(self, kind, due_in=None):
        c = self.j.c
        day = c['day']
        self.d['pre'] = [b for b in self.d['pre'] if b['id'] != f'pre-{day}']
        self.d['pre'].append(dict(id=f'pre-{day}', kind=kind, day=day, due=day + FL.PRE[kind]['lead'], status='offer', stars=None))
        validate_state(self.j.state)
        return f'pre-{day}'

    def posts(self, ref):
        return [p for p in self.j.c['feed'] if p['kind'] == 'review' and p['source'] == ref]

    # --- the cooler ------------------------------------------------------------
    def test_stages_bud_bloom_wilt(self):
        c = self.j.c
        bud = inventory.add_lot(c, 'rose_red', 3, 2, 4, 'partner')
        old = inventory.add_lot(c, 'rose_pink', 2, 2, 1, 'partner')
        self.assertEqual(FL._stage(c['day'], bud), 'bud')
        self.assertEqual(FL._stage(c['day'], old), 'wilt')
        self.assertEqual(FL._stage(c['day'] + 1, bud), 'bloom')
        opening = next(l for l in c['ext']['inv']['lots'] if l['item'] == 'rose_white' and l['supplier'] == 'opening')
        self.assertEqual(FL._stage(c['day'], opening), 'bloom')   # opening stock is already open
        st = public_state(self.j.state)['careers']['florist']['data']['cooler']['rose_red']['stages']
        self.assertGreaterEqual(st['bud'], 3)

    def test_water_change_keeps_lots_two_nights(self):
        j = self.j
        lot = self.lot('lily', 4)
        exp = self.exp(lot)
        r = j.act('fl_water')
        self.assertIn('không già thêm', r['message'])
        with self.assertRaises(GameError):
            j.act('fl_water')
        self.assertTrue(self.view()['water']['done'])
        care = self.next_day()['care']
        self.assertEqual(self.exp(lot), exp + 1)
        self.assertEqual(self.d['kept'][lot], 1)
        self.assertTrue(any('không già thêm' in x for x in care))
        for _ in range(2):
            j.act('fl_water')
            self.next_day()
        self.assertEqual(self.exp(lot), exp + 2)                   # at most two nights per lot
        self.assertEqual(self.d['kept'][lot], 2)

    def test_one_skipped_day_is_free_two_age_the_cooler(self):
        lot = self.lot('lily', 4)
        exp = self.exp(lot)
        self.next_day()                                             # day 1 closes: water was "yesterday" → free
        self.assertEqual(self.exp(lot), exp)
        last = self.lot('rose_pink', 3, life=2)                     # expires tomorrow: never jumps straight to gone
        exp2 = self.exp(last)
        care = self.next_day()['care']                              # day 2: two days without fresh water
        self.assertEqual(self.exp(lot), exp - 1)
        self.assertTrue(any('đục' in x for x in care))
        self.assertEqual(self.exp(last), exp2)
        self.assertFalse(self.view()['water']['done'])

    def test_prep_helper_changes_the_water(self):
        note = FL.assist(self.j.state, self.j.c, dict(role='prep', name='Tuấn'), None)
        self.assertIn('thay nước', note)
        self.assertEqual(self.d['water'], self.j.c['day'])
        self.assertNotIn('thay nước tủ mát', FL.assist(self.j.state, self.j.c, dict(role='prep', name='Tuấn'), None))

    # --- pre-orders ---------------------------------------------------------------
    def test_offers_are_seeded_and_capped(self):
        self.assertEqual([FL._pre_offer(d, 'normal') for d in range(1, 30)], [FL._pre_offer(d, 'normal') for d in range(1, 30)])
        self.assertIsNone(FL._pre_offer(1, 'normal'))
        days = [d for d in range(2, 60) if FL._pre_offer(d, 'normal')]
        self.assertTrue(10 < len(days) < 50)
        self.assertGreater(sum(1 for d in range(2, 60) if FL._pre_offer(d, 'wedding')), len(days))
        self.d['pre'] = [dict(id=f'pre-{d}', kind='funeral', day=d, due=d + 1, status='booked', stars=None) for d in (1, 2, 3)]
        self.j.c['day'] = days[0]
        FL._care_start(self.j.state, self.j.c, self.d, FL._plan(self.j.c))
        self.assertEqual(len(self.d['pre']), 3)                     # three open: no new call

    def test_preorder_planned_ahead_is_five_stars(self):
        j = self.j
        bid = self.book('anniv')                                    # due in 2 days
        money = self.money()
        with self.assertRaises(GameError):
            j.act('fl_pre', id=bid, do='accept')                    # needs confirm
        j.act('fl_pre', id=bid, do='accept', confirm=True)
        self.assertEqual(self.money(), money + 60)
        with self.assertRaises(GameError):
            j.act('fl_pre', id=bid, do='make', confirm=True)        # not the due day yet
        v = next(b for b in self.view()['pre'] if b['id'] == bid)
        roses = next(r for r in v['rows'] if r['item'] == 'rose_red')
        day = j.c['day']
        self.assertEqual(roses['buy'], [day, day + 1])              # roses: 1–2 days ahead
        self.next_day()
        self.drop('rose_red', 'babys_breath', 'eucalyptus')
        self.lot('rose_red', 12)
        self.lot('babys_breath', 4, life=3)
        self.lot('eucalyptus', 3, life=5)
        v = next(b for b in self.view()['pre'] if b['id'] == bid)
        self.assertTrue(all(r['ready'] >= r['need'] for r in v['rows'] if r['flower']))
        j.act('fl_water')                                           # a careful florist keeps the water fresh
        self.next_day()
        self.assertEqual(j.c['day'], day + 2)
        money = self.money()
        r = j.act('fl_pre', id=bid, do='make', confirm=True)
        self.assertIn('+140 xu', r['message'])
        self.assertEqual(self.money(), money + 140)
        self.assertEqual(self.posts(bid)[0]['stars'], 5)
        b = next(b for b in self.d['pre'] if b['id'] == bid)
        self.assertEqual((b['status'], b['stars']), ('done', 5))
        self.assertEqual(self.d['book']['5']['visits'], 1)
        with self.assertRaises(GameError):
            j.act('fl_pre', id=bid, do='make', confirm=True)
        validate_state(json.loads(json.dumps(j.state)))

    def test_preorder_with_stems_bought_on_the_day_has_buds(self):
        j = self.j
        bid = self.book('funeral')
        j.act('fl_pre', id=bid, do='accept', confirm=True)
        self.next_day()
        self.drop('lily', 'mum_white')
        self.lot('lily', 4)                                         # lilies bought this morning: buds
        self.lot('mum_white', 16)
        money = self.money()
        r = j.act('fl_pre', id=bid, do='make', confirm=True)
        self.assertIn('nụ', r['message'])
        self.assertEqual(self.money(), money + 300 - 100 - 10)
        self.assertEqual(self.posts(bid)[0]['stars'], 4)

    def test_preorder_short_stock_is_refused_and_named(self):
        j = self.j
        bid = self.book('funeral')
        j.act('fl_pre', id=bid, do='accept', confirm=True)
        self.next_day()
        self.drop('stand')
        with self.assertRaises(GameError) as e:
            j.act('fl_pre', id=bid, do='make', confirm=True)
        self.assertIn('chân kệ', str(e.exception).lower())
        v = next(b for b in self.view()['pre'] if b['id'] == bid)
        self.assertTrue(v['short'])

    def test_preorder_not_made_refunds_the_deposit(self):
        j = self.j
        bid = self.book('funeral')
        j.act('fl_pre', id=bid, do='accept', confirm=True)
        self.next_day()
        care = self.next_day()['care']
        refund = [e for e in j.c['ops']['finance']['ledger'] if e['ref'] == bid and e['amount'] < 0]
        self.assertEqual(refund[0]['amount'], -100)
        self.assertEqual(self.posts(bid)[0]['stars'], 1)
        self.assertEqual(next(b for b in self.d['pre'] if b['id'] == bid)['status'], 'failed')
        self.assertTrue(any('Không kịp' in x for x in care))

    def test_offer_decline_and_lapse(self):
        j = self.j
        bid = self.book('wedding')
        j.act('fl_pre', id=bid, do='decline')
        self.assertFalse(any(b['id'] == bid for b in self.d['pre']))
        bid = self.book('wedding')
        self.next_day()
        self.assertFalse(any(b['id'] == bid for b in self.d['pre']))
        with self.assertRaises(GameError):
            j.act('fl_pre', id='pre-999', do='accept', confirm=True)
        with self.assertRaises(GameError):
            j.act('fl_pre', id=['x'], do='accept', confirm=True)
        with self.assertRaises(GameError):
            j.act('fl_pre', id=bid, do='steal', confirm=True)

    # --- the subscription ---------------------------------------------------------
    def subscribe(self):
        j = self.j
        self.d['sub'].update(status='offer')
        j.act('fl_sub', do='accept', confirm=True)
        self.assertEqual(self.d['sub']['known'], ['fresh'])
        self.next_day()

    def round_with(self, tid):
        return next(r for r in range(200) if tid in FL._sub_menu(self.j.c, r))

    def test_subscription_offered_from_day_three(self):
        for _ in range(2):
            self.assertEqual(self.d['sub']['status'], 'none')
            self.next_day()
        self.assertEqual(self.d['sub']['status'], 'offer')
        self.assertEqual(self.view()['sub']['status'], 'offer')
        self.j.act('fl_sub', do='decline')
        self.assertEqual(self.d['sub']['retry'], self.j.c['day'] + 5)

    def test_every_menu_has_a_vase_she_likes(self):
        for r in range(60):
            menu = FL._sub_menu(self.j.c, r)
            self.assertEqual(len(set(menu)), 3)
            self.assertTrue(any(FL.TEMPLATE_INDEX[k]['tags'] == ('pink',) for k in menu))

    def test_lily_vase_teaches_her_card(self):
        j = self.j
        self.subscribe()
        self.d['sub']['round'] = self.round_with('lily')
        self.shop.stock_up('lily', 3)
        money = self.money()
        r = j.act('fl_sub', do='make', pick='lily', confirm=True)
        self.assertIn('hắt hơi', r['message'])
        self.assertEqual(self.money(), money + FL.SUB_PRICE)
        self.assertEqual(self.d['sub']['stars'][-1], 2)             # lily −2, not pink −1
        self.assertEqual(set(self.d['sub']['known']), {'fresh', 'lily', 'pink'})
        self.assertIn(FL.SUB_NOTES['lily'], self.view()['sub']['notes'])
        self.assertEqual(self.d['sub']['next'], j.c['day'] + FL.SUB_EVERY)
        with self.assertRaises(GameError):
            j.act('fl_sub', do='make', pick='lily', confirm=True)   # not due again today

    def test_liked_vase_is_five_stars_and_menu_is_enforced(self):
        j = self.j
        self.subscribe()
        c = j.c
        rnd = self.round_with('pinkrose')
        self.d['sub']['round'] = rnd
        menu = FL._sub_menu(c, rnd)
        other = next(k for k in FL.TEMPLATE_INDEX if k not in menu)
        with self.assertRaises(GameError):
            j.act('fl_sub', do='make', pick=other, confirm=True)
        for k in ('rose_pink', 'babys_breath', 'eucalyptus'):
            x = c['ext']['inv']
            x['lots'] = [l for l in x['lots'] if l['item'] != k]
            inventory.add_lot(c, k, 6, 1, 3, 'partner')
            next(l for l in x['lots'][::-1] if l['item'] == k)['received'] = c['day'] - 1   # bought yesterday: open
        j.act('fl_sub', do='make', pick='pinkrose', confirm=True)
        self.assertEqual(self.d['sub']['stars'][-1], 5)
        self.assertEqual(self.posts(f'sub-{rnd + 1}')[0]['stars'], 5)

    def test_two_missed_vases_end_the_subscription(self):
        self.subscribe()
        self.next_day()                                             # due day passes
        self.assertEqual(self.d['sub']['misses'], 1)
        for _ in range(FL.SUB_EVERY):
            self.next_day()
        self.assertEqual(self.d['sub']['status'], 'off')
        self.assertEqual(len([p for p in self.j.c['feed'] if p['kind'] == 'review' and p['source'].startswith('sub-miss')]), 2)

    def test_stop_subscription(self):
        self.subscribe()
        with self.assertRaises(GameError):
            self.j.act('fl_sub', do='stop')
        self.j.act('fl_sub', do='stop', confirm=True)
        self.assertEqual(self.d['sub']['status'], 'off')

    # --- the regulars' book, projection and saves -------------------------------------
    def test_regulars_book_learns_after_visits_and_hides_the_rest(self):
        j = self.j
        FL._plan(j.c)['events'] = []
        t = j.task
        npc = int(t['npc'].rsplit('_', 1)[1]) - 1
        r = self.shop.make(t['id'])
        first, second = FL.NOTES[npc][0][1], FL.NOTES[npc][1][1]
        self.assertIn(first, r['message'])
        self.assertEqual(self.d['book'][str(npc)], dict(visits=1, notes=[FL.NOTES[npc][0][0]]))
        text = json.dumps(public_state(j.state), ensure_ascii=False)
        self.assertIn(first, text)
        self.assertNotIn(second, text)
        row = next(b for b in self.view()['book'] if b['npc'] == t['npc'])
        self.assertEqual(row['more'], 2)

    def test_tampered_care_data_rejected(self):
        cases = [
            lambda d: d.update(water='x'),
            lambda d: d['kept'].update({'lot-1': 3}),
            lambda d: d['book'].update({'2': dict(visits=1, notes=['banner', 'early'])}),
            lambda d: d['book'].update({'9': dict(visits=1, notes=[])}),
            lambda d: d['pre'].append(dict(id='pre-1', kind='wedding', day=1, due=2, status='offer', stars=None)),
            lambda d: d['pre'].append(dict(id='pre-1', kind='cake', day=1, due=4, status='offer', stars=None)),
            lambda d: d['pre'].append(dict(id='pre-1', kind='wedding', day=1, due=4, status='done', stars=None)),
            lambda d: d['sub'].update(misses=2),
            lambda d: d['sub'].update(known=['secret']),
            lambda d: d['sub'].update(status='forever'),
        ]
        for i, bad in enumerate(cases):
            s = copy.deepcopy(self.j.state)
            bad(s['careers']['florist']['ext']['data'])
            with self.assertRaises(GameError, msg=str(i)):
                validate_state(s)

    def test_old_save_without_care_keys(self):
        s = copy.deepcopy(self.j.state)
        d = s['careers']['florist']['ext']['data']
        for k in ('water', 'kept', 'book', 'pre', 'sub'):
            d.pop(k)
        view = public_state(s)['careers']['florist']['data']['care']
        self.assertFalse(view['water']['done'])
        self.assertEqual(view['pre'], [])
        validate_state(s)
        self.assertEqual(d['water'], s['careers']['florist']['day'] - 1)
        from game.engine import apply_action
        s, _ = apply_action(s, 'florist', 'fl_water', {})
        validate_state(s)

    def test_public_view_does_not_write(self):
        s = copy.deepcopy(self.j.state)
        d = s['careers']['florist']['ext']['data']
        for k in ('water', 'kept', 'book', 'pre', 'sub'):
            d.pop(k)
        before = json.dumps(s, sort_keys=True)
        public_state(s)
        self.assertEqual(json.dumps(s, sort_keys=True), before)

    def test_autoplay_a_caring_week(self):
        """Eight days of a florist who changes the water, takes bookings and keeps Bà Tám's vases."""
        j, shop = self.j, self.shop
        made = subs = 0
        for _ in range(8):
            j.c['xp'] = max(j.c['xp'], 90)
            if self.d['water'] != j.c['day']:
                j.act('fl_water')
            for b in list(self.d['pre']):
                if b['status'] == 'offer':
                    j.act('fl_pre', id=b['id'], do='accept', confirm=True)
                if b['status'] == 'booked' and b['due'] == j.c['day']:
                    for k, q in FL.PRE[b['kind']]['recipe'].items():
                        shop.stock_up(k, q)
                    j.act('fl_pre', id=b['id'], do='make', confirm=True)
                    made += 1
            sub = self.d['sub']
            if sub['status'] == 'offer':
                j.act('fl_sub', do='accept', confirm=True)
            elif sub['status'] == 'on' and sub['next'] == j.c['day']:
                pick = next(k for k in FL._sub_menu(j.c, sub['round']) if FL.TEMPLATE_INDEX[k]['tags'] == ('pink',))
                for k, q in {**FL.TEMPLATE_INDEX[pick]['stems'], **FL.SUB_WRAP}.items():
                    shop.stock_up(k, q)
                j.act('fl_sub', do='make', pick=pick, confirm=True)
                subs += 1
            shop.play_day(max_orders=2)
            j.act('start_day')
            validate_state(json.loads(json.dumps(j.state)))
        self.assertGreaterEqual(made, 1)
        self.assertGreaterEqual(subs, 1)
        self.assertFalse(any(b['status'] == 'failed' for b in self.d['pre']))
        self.assertTrue(self.d['book'])


if __name__ == '__main__':
    unittest.main()
