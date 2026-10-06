"""Thư viện – Lưu trữ phường Mây (plugin career library): the morning (hygrometer, traps, the reading room), the desk
(borrowing with the card rules, returns with a fee the player names and the reader decides, repairs, a recommendation
by hidden taste), cataloguing (class, author mark, weeding junk donations), the reading-room round (answers taken by
hidden traits), the archive window (the briefing, papers, access levels, the right box, a misfiled or lent record,
certified copies, the log), the awkward asks, surprises, the debt book, determinism and save validation."""
import copy
import json
import unittest

from tests.helpers import Journey
from game.careers import kit, PLUGINS
from game.engine import GameError, public_state, validate_state

LB = PLUGINS.get('library')
LC = LB.LC if LB else None


def ledger(c, ref):
    return [r for r in c['ops']['finance']['ledger'] if r.get('ref') == ref]


class Base(unittest.TestCase):
    def setUp(self):
        if LB is None:
            raise unittest.SkipTest('library is filtered out by MNL_CAREERS')
        self.j = Journey('library')

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, pick, days=range(2, 400), slots=range(1, 12)):
        """A journey on the first (day, slot) whose job matches `pick`."""
        day, slot = next((d, s) for d in days for s in slots if pick(LB.make_task(d, s, 1)))
        j = Journey('library', slot=slot, day=day)
        j.c['ext']['data']['intro'] = True
        return j

    def settle_desk(self, j=None):
        j = j or self.j
        ev = j.c['ext']['data']['desk']['ev']
        if ev:
            j.act('tv_desk', option=kit.desk_script(LC.DESK, ev['script'])['default'])

    def answer_ask(self, j, tid, choice=None):
        t = j.get(tid)
        dm = t.get('dm')
        if dm and dm['state'] == 'on':
            x = LC.DEMAND[dm['id']]
            j.act('tv_ask', task=tid, choice=choice or x['best'][0])

    def act(self, j, name, **p):
        """An action on a job; when someone steps in with an ask, answer the right way and carry on."""
        r = j.act(name, **p)
        t = j.get(p['task'])
        if t.get('dm') and t['dm']['state'] == 'on':
            self.answer_ask(j, p['task'])
            r = j.act(name, **p)
        return r

    def open_day(self, j=None):
        j = j or self.j
        self.settle_desk(j)
        t = next(x for x in j.c['tasks'] if x['kind'] == 'open' and x['status'] not in ('completed', 'cancelled'))
        for w in ('am', 'bay', 'phong', 'bang'):
            j.act('tv_look', task=t['id'], what=w)
        if t['_x']['hum'] > LC.HUM_OK[1]:
            j.act('tv_dehum', task=t['id'])
        j.act('tv_pest', task=t['id'], how=LC.PEST_BEST[t['_x']['pest']])
        return j.act('tv_openup', task=t['id'])

    # ---------------------------------------------------------------- the careful way through each kind
    def do_borrow(self, j, tid):
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        self.act(j, 'tv_lookup', task=tid)
        self.act(j, 'tv_card', task=tid)
        t = j.get(tid)
        x = t['_x']
        if x['status'] == 'ref':
            return self.act(j, 'tv_offer', task=tid, how='room')
        if x['status'] == 'out':
            return self.act(j, 'tv_offer', task=tid, how='reserve')
        if x['card'] == 'expired':
            self.act(j, 'tv_renew', task=tid)
        if x['card'] == 'debt':
            self.act(j, 'tv_settle', task=tid, amount=x['owe'])
        if x['card'] == 'limit':
            return self.act(j, 'tv_offer', task=tid, how='return_first')
        return self.act(j, 'tv_lend', task=tid)

    def do_return(self, j, tid):
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        for a in ('tv_inspect', 'tv_date', 'tv_why'):
            self.act(j, a, task=tid)
        x = j.get(tid)['_x']
        full, least = LB.fee_due(x)
        if full:
            r = self.act(j, 'tv_fine', task=tid, amount=least, tone='soft')
            if j.get(tid)['fee']['state'] == 'open':
                c = j.get(tid)['fee']['counter']
                if c is not None and c >= least:
                    self.act(j, 'tv_fine', task=tid, amount=c, tone='soft')
                if j.get(tid)['fee']['state'] == 'open':
                    self.act(j, 'tv_fee', task=tid, how='boss')
        if x['damage'] not in ('none', 'lost'):
            fix = next(k for k, v in LC.REPAIR.items() if v[1] == x['damage'])
            self.act(j, 'tv_repair', task=tid, how=fix)
        return self.act(j, 'tv_shelve', task=tid)

    def do_recommend(self, j, tid):
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        self.act(j, 'tv_q', task=tid, q='last')
        self.act(j, 'tv_q', task=tid, q='mood')
        x = j.get(tid)['_x']
        book = next(b for b in j.get(tid)['needs']['cands'] if LC.TASTE[b][0] == x['genre'] and LC.TASTE[b][1] == x['easy'])
        return self.act(j, 'tv_rec', task=tid, book=book)

    def do_catalog(self, j, tid):
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        for b in j.get(tid)['needs']['books']:
            row = LC.BOOKS[b]
            if row[4]:
                self.act(j, 'tv_weed', task=tid, book=b, reason=row[4])
            else:
                self.act(j, 'tv_class', task=tid, book=b, cls=row[2])
                self.act(j, 'tv_mark', task=tid, book=b, mark=LB.author_mark(row[1]))
        return self.act(j, 'tv_catdone', task=tid)

    def do_room(self, j, tid):
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        for o in j.get(tid)['needs']['offenders']:
            how = LC.OFFENCES[o][3][0]
            self.act(j, 'tv_deal', task=tid, who=o, how=how)
            if j.get(tid)['st']['done'][o]['res'] == 'blowup':
                self.act(j, 'tv_deal', task=tid, who=o, how='rule')
        return self.act(j, 'tv_rounddone', task=tid)

    def do_archive(self, j, tid):
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        d = j.c['ext']['data']
        if not d['trained']:
            j.act('tv_train', answers=[q[2] for q in LC.TRAINING])
        for w in ('id', 'form', 'index'):
            self.act(j, 'tv_see', task=tid, what=w)
        x = j.get(tid)['_x']
        r = self.act(j, 'tv_decide', task=tid, choice=x['right'])
        if x['right'] in ('paper', 'refuse'):
            return r
        self.act(j, 'tv_gear', task=tid, item='gang')
        self.act(j, 'tv_gear', task=tid, item='khau_trang')
        self.act(j, 'tv_box', task=tid, box=x['box'])
        if x['lost']:
            self.act(j, 'tv_search', task=tid, where='neighbour' if x['lost'] == 'misfiled' else 'log')
        self.act(j, 'tv_copy', task=tid, how='original' if x['orig'] else 'copy')
        self.act(j, 'tv_log', task=tid)
        return self.act(j, 'tv_handover', task=tid)

    def do(self, j, tid):
        t = j.get(tid)
        if t['kind'] == 'desk':
            return {'borrow': self.do_borrow, 'return': self.do_return, 'recommend': self.do_recommend}[t['needs']['mode']](j, tid)
        return {'catalog': self.do_catalog, 'room': self.do_room, 'archive': self.do_archive}[t['kind']](j, tid)


class Spec(Base):
    def test_spec_shape(self):
        s = LB.SPEC
        self.assertEqual((s['id'], s['prefix']), ('library', 'tv_'))
        self.assertTrue(6 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertEqual(len(s['staff']), 4)
        self.assertEqual(len(s['stories']), 3)
        self.assertTrue(5 <= len(s['situations']) <= 8)
        for k in s['no_tick'] + s['free_actions'] + tuple(LB.ACTIONS) + s['physical']:
            self.assertTrue(k.startswith('tv_'), k)
            self.assertTrue(k in LB.ACTIONS or k in ('tv_intro', 'tv_desk'), k)

    def test_many_awkward_asks(self):
        self.assertGreaterEqual(len(LC.DEMANDS), 50)
        self.assertEqual(len({x['id'] for x in LC.DEMANDS}), len(LC.DEMANDS))
        for x in LC.DEMANDS:
            self.assertTrue(set(x['best']) <= set(LC.CHOICES) and set(x['bad']) <= set(LC.CHOICES), x['id'])
            self.assertFalse(set(x['best']) & set(x['bad']), x['id'])
            self.assertTrue(set(x['kinds']) <= {'desk', 'catalog', 'room', 'archive'}, x['id'])
            if x['bad']:
                self.assertTrue(x['lose'], x['id'])
            if x['typ'] in ('bribe', 'flirt', 'privacy'):
                self.assertIn('yes', x['bad'], x['id'])   # giving in is never rewarded
            self.assertLessEqual(len(x['id']), 30)
        for kind in ('desk', 'catalog', 'room', 'archive'):
            self.assertGreaterEqual(sum(kind in x['kinds'] for x in LC.DEMANDS), 15, kind)

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'người chơi', 'mô phỏng', 'giả lập', 'nhiệm vụ', 'anh/chị')
        blob = json.dumps([LC.DEMANDS, LC.DESK, LC.SITUATIONS, LC.REG_STORY, LC.INTRO, LB.SPEC['meta'], LC.OFFENCES, LC.REQUESTS,
                           LC.BOOKS, LC.TRAINING, LC.STORIES], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_rules(self):
        self.assertEqual(LB.late_fee(3), 3)
        self.assertEqual(LB.late_fee(40), LC.FINE_CAP)
        self.assertEqual(LB.author_mark('Nguyễn Nhật Ánh'), 'ANH')
        self.assertEqual(LB.author_mark('Đỗ Quang Bình'), 'BIN')
        x = dict(late=10, damage='wet', excuse='vien', price=30)
        self.assertEqual(LB.fee_due(x), (20, 10))
        x.update(excuse='quen')
        self.assertEqual(LB.fee_due(x), (20, 20))
        x.update(damage='lost', late=0)
        self.assertEqual(LB.fee_due(x), (30, 30))
        for b, row in LC.BOOKS.items():
            self.assertIn(row[2], LC.CLASS_IDS, b)
            self.assertIn(row[4], (None, *LC.WEED), b)

    def test_tasks_are_deterministic_and_varied(self):
        kinds, modes = set(), set()
        for day in range(1, 40):
            for slot in range(12):
                t = LB.make_task(day, slot, 1)
                self.assertEqual(t, LB.make_task(day, slot, 1))
                kinds.add(t['kind'])
                if t['kind'] == 'desk':
                    modes.add(t['needs']['mode'])
                if t['kind'] == 'catalog':
                    for b in t['needs']['books']:
                        self.assertIn(LB.author_mark(LC.BOOKS[b][1]), t['needs']['marks'][b])
        self.assertEqual(kinds, set(LB.KINDS))
        self.assertEqual(modes, set(LB.MODES))
        self.assertEqual(LB.make_task(5, 0, 1)['kind'], 'open')


class Morning(Base):
    def test_open_the_careful_way(self):
        r = self.open_day()
        t = next(x for x in self.j.c['tasks'] if x['kind'] == 'open')
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertTrue(r.get('celebrate'))

    def test_damp_store_without_the_dehumidifier(self):
        j = self.at(lambda t: t['kind'] == 'open' and t['_x']['hum'] > 60, slots=(0,))
        tid = j.task['id']
        for w in ('am', 'bay', 'phong', 'bang'):
            j.act('tv_look', task=tid, what=w)
        j.act('tv_pest', task=tid, how=LC.PEST_BEST[j.get(tid)['_x']['pest']])
        j.act('tv_openup', task=tid)
        self.assertIn('damp', {s['code'] for s in j.get(tid)['slips']})

    def test_spraying_the_shelves(self):
        j = self.at(lambda t: t['kind'] == 'open' and t['_x']['pest'] == 'mot', slots=(0,))
        tid = j.task['id']
        for w in ('am', 'bay', 'phong', 'bang'):
            j.act('tv_look', task=tid, what=w)
        j.act('tv_dehum', task=tid)
        j.act('tv_pest', task=tid, how='xit')
        j.act('tv_openup', task=tid)
        self.assertIn('spray', {s['code'] for s in j.get(tid)['slips']})

    def test_room_must_open(self):
        tid = self.j.task['id']
        with self.assertRaises(GameError):
            self.j.act('tv_openup', task=tid)


class Desk(Base):
    def test_borrow_happy_path_pays_and_reviews(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'borrow' and t['_x']['status'] == 'avail' and t['_x']['card'] == 'ok')
        tid = j.task['id']
        money = j.c['money']
        r = self.do_borrow(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        if not t.get('slips'):
            self.assertGreater(j.c['money'], money)
        self.assertTrue(any(f.get('source') == tid and f['kind'] == 'review' for f in j.c['feed']), r)

    def test_hidden_before_asking(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'borrow')
        tid = j.task['id']
        pub = next(t for t in public_state(j.state)['careers']['library']['tasks'] if t['id'] == tid)
        self.assertIsNone(pub['needs'])
        self.assertNotIn('_x', pub)
        j.act('ask', task=tid)
        pub = next(t for t in public_state(j.state)['careers']['library']['tasks'] if t['id'] == tid)
        self.assertNotIn('status', pub['info'])
        self.assertIsNone(pub['cardinfo'])

    def test_lending_a_reference_book_is_a_mistake(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'borrow' and t['_x']['status'] == 'ref' and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_lookup', task=tid)
        with self.assertRaises(GameError):
            j.act('tv_lend', task=tid)          # the card first
        j.act('tv_card', task=tid)
        j.act('tv_lend', task=tid)
        self.assertIn('ref_out', {s['code'] for s in j.get(tid)['slips']})

    def test_book_out_cannot_be_lent(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'borrow' and t['_x']['status'] == 'out' and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_lookup', task=tid)
        j.act('tv_card', task=tid)
        with self.assertRaises(GameError):
            j.act('tv_lend', task=tid)
        j.act('tv_offer', task=tid, how='reserve')
        self.assertFalse(j.get(tid).get('slips'))

    def test_expired_card_renewal_takes_the_fee(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'borrow' and t['_x']['card'] == 'expired' and t['_x']['status'] == 'avail'
                    and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_lookup', task=tid)
        j.act('tv_card', task=tid)
        j.act('tv_renew', task=tid)
        self.assertEqual(sum(r['amount'] for r in ledger(j.c, tid) if r['category'] == 'card_fee'), LC.CARD_FEE)
        with self.assertRaises(GameError):
            j.act('tv_renew', task=tid)
        j.act('tv_lend', task=tid)
        self.assertNotIn('card', {s['code'] for s in j.get(tid).get('slips', [])})

    def test_needless_refusal(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'borrow' and t['_x']['status'] == 'avail' and t['_x']['card'] == 'ok'
                    and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_lookup', task=tid)
        j.act('tv_card', task=tid)
        j.act('tv_offer', task=tid, how='decline')
        self.assertIn('needless_no', {s['code'] for s in j.get(tid)['slips']})

    def test_return_the_careful_way(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'return' and t['_x']['late'] > 3 and t['_x']['damage'] == 'torn')
        tid = j.task['id']
        self.do_return(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertNotIn('overcharge', {s['code'] for s in t.get('slips', [])})
        self.assertIn(t['fee']['state'], ('paid', 'debt'))

    def test_overcharging_a_fee(self):
        # A reader who knows the rules points at the board; one who does not pays and hears about it later.
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'return' and t['_x']['late'] > 2 and t['_x']['damage'] == 'none'
                    and LB.demand_of(t) is None and LB._tr(t)['savvy'] >= 50)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_inspect', task=tid)
        j.act('tv_date', task=tid)
        full, _ = LB.fee_due(j.get(tid)['_x'])
        r = j.act('tv_fine', task=tid, amount=full + 20, tone='strict')
        self.assertFalse(r.get('correct', True))
        self.assertIn('overcharge_caught', {s['code'] for s in j.get(tid)['slips']})
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'return' and t['_x']['late'] > 2 and t['_x']['damage'] == 'none'
                    and LB.demand_of(t) is None and LB._tr(t)['savvy'] < 50
                    and LB.folk.judge_price(LB._tr(t), LB.fee_due(t['_x'])[0], LB.fee_due(t['_x'])[0] + 2, 0)['kind'] == 'accept')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_inspect', task=tid)
        j.act('tv_date', task=tid)
        full, _ = LB.fee_due(j.get(tid)['_x'])
        j.act('tv_fine', task=tid, amount=full + 2, tone='soft')
        self.assertIn('overcharge', {s['code'] for s in j.get(tid)['slips']})
        self.assertEqual(j.c['ext']['data']['today']['overcharged'], 2)

    def test_waiving_without_a_reason(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'return' and t['_x']['late'] > 2 and t['_x']['damage'] == 'none'
                    and t['_x']['excuse'] in ('quen', 'none') and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_inspect', task=tid)
        j.act('tv_date', task=tid)
        j.act('tv_fee', task=tid, how='waive')
        self.assertIn('lenient', {s['code'] for s in j.get(tid)['slips']})

    def test_waiving_with_a_good_reason_is_fine(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'return' and t['_x']['late'] > 2 and t['_x']['damage'] == 'none'
                    and t['_x']['excuse'] in ('vien', 'lu') and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        for a in ('tv_inspect', 'tv_date', 'tv_why'):
            j.act(a, task=tid)
        j.act('tv_fee', task=tid, how='waive')
        j.act('tv_shelve', task=tid)
        self.assertFalse(j.get(tid).get('slips'))

    def test_debt_book_and_chasing(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'return' and t['_x']['late'] > 4 and t['_x']['damage'] == 'none'
                    and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_inspect', task=tid)
        j.act('tv_date', task=tid)
        j.act('tv_fee', task=tid, how='later')
        debts = j.c['ext']['data']['debts']
        self.assertEqual(len(debts), 1)
        r = j.act('tv_chase', debt=debts[0]['id'], tone='soft')
        self.assertTrue(r['message'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_shelving_waits_for_the_fee(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'return' and t['_x']['late'] > 2 and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_inspect', task=tid)
        j.act('tv_date', task=tid)
        with self.assertRaises(GameError):
            j.act('tv_shelve', task=tid)

    def test_bad_repair(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'return' and t['_x']['damage'] == 'wet' and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_inspect', task=tid)
        j.act('tv_repair', task=tid, how='say')
        self.assertIn('heat', {s['code'] for s in j.get(tid)['slips']})

    def test_recommend_by_hidden_taste(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'recommend')
        tid = j.task['id']
        self.do_recommend(j, tid)
        self.assertFalse({s['code'] for s in j.get(tid).get('slips', [])} & {'rec_miss', 'rec_meh'})
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'recommend' and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        x = j.get(tid)['_x']
        wrong = next(b for b in j.get(tid)['needs']['cands'] if LC.TASTE[b][0] != x['genre'])
        j.act('tv_rec', task=tid, book=wrong)
        self.assertIn('rec_miss', {s['code'] for s in j.get(tid)['slips']})


class Catalog(Base):
    def test_catalog_the_careful_way(self):
        j = self.at(lambda t: t['kind'] == 'catalog' and any(LC.BOOKS[b][4] for b in t['needs']['books']))
        tid = j.task['id']
        labels = kit.stock(j.c, 'nhan')
        self.do_catalog(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse({s['code'] for s in t.get('slips', [])} & {'wrong_class', 'wrong_mark', 'junk_shelved', 'weeded_good'})
        kept = sum(1 for b in t['needs']['books'] if not LC.BOOKS[b][4])
        self.assertEqual(kit.stock(j.c, 'nhan'), labels - kept)

    def test_wrong_class_and_junk_on_the_shelf(self):
        j = self.at(lambda t: t['kind'] == 'catalog' and any(LC.BOOKS[b][4] for b in t['needs']['books']) and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        for b in j.get(tid)['needs']['books']:
            j.act('tv_class', task=tid, book=b, cls='800' if LC.BOOKS[b][2] != '800' else '900')
            j.act('tv_mark', task=tid, book=b, mark=j.get(tid)['needs']['marks'][b][0])
        j.act('tv_catdone', task=tid)
        codes = {s['code'] for s in j.get(tid)['slips']}
        self.assertIn('wrong_class', codes)
        self.assertIn('junk_shelved', codes)

    def test_all_books_need_a_class(self):
        j = self.at(lambda t: t['kind'] == 'catalog' and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('tv_catdone', task=tid)
        with self.assertRaises(GameError):
            j.act('tv_class', task=tid, book='nope', cls='800')
        with self.assertRaises(GameError):
            j.act('tv_class', task=tid, book=j.get(tid)['needs']['books'][0], cls='850')


class Room(Base):
    def test_room_round(self):
        j = self.at(lambda t: t['kind'] == 'room')
        tid = j.task['id']
        self.do_room(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_ignoring_smoke_by_the_archive_is_a_safety_mistake(self):
        j = self.at(lambda t: t['kind'] == 'room' and 'hut_thuoc' in t['needs']['offenders'] and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tv_deal', task=tid, who='hut_thuoc', how='ignore')
        rows = [s for s in j.get(tid)['slips'] if s['code'] == 'r_hut_thuoc']
        self.assertTrue(rows and rows[0]['safety'])

    def test_round_needs_every_one(self):
        j = self.at(lambda t: t['kind'] == 'room' and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('tv_rounddone', task=tid)
        with self.assertRaises(GameError):
            j.act('tv_deal', task=tid, who='nobody', how='soft')

    def test_reactions_are_deterministic(self):
        j1 = self.at(lambda t: t['kind'] == 'room' and LB.demand_of(t) is None)
        j2 = self.at(lambda t: t['kind'] == 'room' and LB.demand_of(t) is None)
        tid = j1.task['id']
        for j in (j1, j2):
            j.act('ask', task=tid)
            for o in j.get(tid)['needs']['offenders']:
                j.act('tv_deal', task=tid, who=o, how='rule')
        self.assertEqual(j1.get(tid)['st'], j2.get(tid)['st'])


class Archive(Base):
    def test_training_comes_first(self):
        j = self.at(lambda t: t['kind'] == 'archive' and LB.demand_of(t) is None)
        tid = j.task['id']
        j.act('ask', task=tid)
        for w in ('id', 'form', 'index'):
            j.act('tv_see', task=tid, what=w)
        with self.assertRaises(GameError):
            j.act('tv_decide', task=tid, choice='give')
        r = j.act('tv_train', answers=['a'] * len(LC.TRAINING))
        self.assertFalse(r.get('correct', True))
        self.assertFalse(j.c['ext']['data']['trained'])
        j.act('tv_train', answers=[q[2] for q in LC.TRAINING])
        self.assertTrue(j.c['ext']['data']['trained'])

    def test_each_request_the_careful_way(self):
        for i, req in enumerate(LC.REQUESTS):
            with self.subTest(req=req[1]):
                j = self.at(lambda t, i=i: t['kind'] == 'archive' and t['needs']['req'] == i)
                tid = j.task['id']
                self.do_archive(j, tid)
                t = j.get(tid)
                self.assertEqual(t['status'], 'completed')
                self.assertFalse([s for s in t.get('slips', []) if not s['code'].startswith('d_')], t.get('slips'))

    def test_privacy_breach(self):
        j = self.at(lambda t: t['kind'] == 'archive' and t['_x']['right'] == 'refuse' and LB.demand_of(t) is None)
        tid = j.task['id']
        j.c['ext']['data']['trained'] = True
        j.act('ask', task=tid)
        j.act('tv_see', task=tid, what='id')
        j.act('tv_see', task=tid, what='index')
        j.act('tv_decide', task=tid, choice='give')
        rows = [s for s in j.get(tid)['slips'] if s['code'] == 'privacy']
        self.assertTrue(rows and rows[0]['sev'] == 3)

    def test_originals_stay_and_hasty_reports(self):
        j = self.at(lambda t: t['kind'] == 'archive' and t['_x']['lost'] == 'misfiled' and LB.demand_of(t) is None)
        tid = j.task['id']
        j.c['ext']['data']['trained'] = True
        j.act('ask', task=tid)
        for w in ('id', 'form', 'index'):
            j.act('tv_see', task=tid, what=w)
        j.act('tv_decide', task=tid, choice='give')
        x = j.get(tid)['_x']
        r = j.act('tv_box', task=tid, box=(x['box'] + 1) % 3)
        self.assertFalse(r.get('correct', True))
        j.act('tv_box', task=tid, box=x['box'])
        with self.assertRaises(GameError):
            j.act('tv_copy', task=tid, how='copy')
        j.act('tv_search', task=tid, where='report')
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertIn('hasty_report', {s['code'] for s in t['slips']})
        self.assertIn('bare', {s['code'] for s in t['slips']})


class Asks(Base):
    def test_ask_blocks_until_answered(self):
        j = self.at(lambda t: t['kind'] == 'desk' and t['needs']['mode'] == 'borrow' and LB.demand_of(t) is not None
                    and 'yes' in LC.DEMAND[LB.demand_of(t)]['bad'])
        tid = j.task['id']
        j.act('ask', task=tid)
        r = j.act('tv_lookup', task=tid)
        self.assertTrue(r.get('surprise'))
        self.assertEqual(j.get(tid)['dm']['state'], 'on')
        with self.assertRaises(GameError):
            j.act('tv_lookup', task=tid)
        pub = next(t for t in public_state(j.state)['careers']['library']['tasks'] if t['id'] == tid)
        self.assertEqual(pub['ask']['state'], 'on')
        self.assertNotIn('dm', pub)
        j.act('tv_ask', task=tid, choice='yes')
        self.assertTrue(any(s['code'].startswith('d_') for s in j.get(tid)['slips']))
        j.act('tv_lookup', task=tid)

    def test_every_ask_every_choice(self):
        seen = set()
        for day in range(1, 200):
            for slot in range(1, 12):
                t = LB.make_task(day, slot, 1)
                dm = LB.demand_of(t)
                if dm and dm not in seen:
                    seen.add(dm)
        self.assertGreaterEqual(len(seen), 50)
        x = LC.DEMANDS[0]
        for choice in LC.CHOICES:
            j = self.at(lambda t: LB.demand_of(t) == x['id'])
            tid = j.task['id']
            j.act('ask', task=tid)
            j.act('tv_lookup', task=tid)
            r = j.act('tv_ask', task=tid, choice=choice)
            self.assertTrue(r['message'])
            self.assertEqual(j.get(tid)['dm']['choice'], choice)
            validate_state(json.loads(json.dumps(j.state)))


class Days(Base):
    def test_a_few_full_days(self):
        j = self.j
        for _ in range(4):
            self.open_day(j)
            for _ in range(8):
                self.settle_desk(j)
                todo = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred') and t['kind'] != 'open']
                if not todo:
                    break
                self.do(j, todo[0]['id'])
            self.settle_desk(j)
            for t in [t for t in j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred')]:
                self.settle_desk(j)
                if t['status'] not in ('completed', 'cancelled', 'referred'):
                    self.do(j, t['id'])
            validate_state(json.loads(json.dumps(j.state)))
            public_state(j.state)
            self.settle_desk(j)
            r = j.act('end_day')
            self.assertIn('career', r.get('summary', r) if isinstance(r.get('summary'), dict) else {'career': 1})
            j.act('start_day')
        self.assertGreater(j.c['ext']['data']['stats']['jobs'], 6)

    def test_surprises_choose(self):
        for x in LC.DESK:
            for o in x['options']:
                j = Journey('library')
                d = j.c['ext']['data']
                d['desk']['ev'] = dict(id='desk-99', script=x['id'], day=j.c['day'], at='between')
                r = j.act('tv_desk', option=o['id'])
                self.assertTrue(r['message'], (x['id'], o['id']))
                self.assertIsNone(j.c['ext']['data']['desk']['ev'])

    def test_situations_play(self):
        for x in LB.SPEC['situations']:
            for opt in x['options']:
                j = Journey('library')
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])


class Saves(Base):
    def test_round_trip_and_tamper(self):
        j = self.at(lambda t: t['kind'] == 'catalog')
        tid = j.task['id']
        validate_state(json.loads(json.dumps(j.state)))
        bad = copy.deepcopy(j.state)
        t = next(x for x in bad['careers']['library']['tasks'] if x['id'] == tid)
        t['needs']['books'] = list(reversed(t['needs']['books']))
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(j.state)
        t = next(x for x in bad['careers']['library']['tasks'] if x['id'] == tid)
        t['_x'] = {'junk': 1}
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(j.state)
        t = next(x for x in bad['careers']['library']['tasks'] if x['id'] == tid)
        t['st']['cls'] = {t['needs']['books'][0]: '999'}
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_bad_data_rejected(self):
        bad = copy.deepcopy(self.j.state)
        bad['careers']['library']['ext']['data']['trained'] = 'yes'
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(self.j.state)
        bad['careers']['library']['ext']['data']['today']['jobs'] = -1
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_old_data_without_new_keys_loads(self):
        s = copy.deepcopy(self.j.state)
        d = s['careers']['library']['ext']['data']
        for k in ('trained', 'debts', 'regulars'):
            d.pop(k)
        validate_state(json.loads(json.dumps(s)))


if __name__ == '__main__':
    unittest.main()
