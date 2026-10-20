"""🤖 Ghép tự động đồ thú cưng (owner: "ghép thú thì thêm chế độ ghép tự động cho áo quần nhé"): jr_pet_wfuse_auto runs
jr_pet_wfuse's own fusion (game/pet_wardrobe.py _fuse_three) again and again, the lowest-rank triple first. It equals the
same fusions made one by one (same rolls, same items, same money), keeps within the budget, the money and AUTO_MAX,
leaves worn items alone, refuses clearly with nothing to fuse, pays from the wallet then the account in one charge, is
charged once for a replayed request id, and its saves load on the live release and the one before (no new save key).
jr_pet_wfuse itself still gives exactly what the live release gives."""
import copy
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import pet_tiers as px
from game import pet_wardrobe as pw
from game import pet_wardrobe_content as W
from game import pets as pt
from game.engine import GameError, validate_state
from tests.test_bank import act, story
from tests.test_pet_buy_qty import PROG
from tests.test_pet_tiers import get

ROOT = Path(__file__).resolve().parents[1]
LIVE = '5ba2e147'                                    # 2.4.67, live when this was written
RELEASES = {'2.4.67': LIVE, '2.4.66': 'a808cb79'}
NOW = 1792500000.0


def WB(s):
    return s['journey']['petw']


def seeded(seed):
    rng = random.Random(seed)
    return mock.patch.object(px, 'roll', lambda n: rng.randrange(n))


def always(v):
    return mock.patch.object(px, 'roll', lambda n: min(v, n - 1))


def clock():
    return mock.patch.object(pt, 'now', lambda: NOW)


def money(s):
    return s['journey']['wallet'] + (s['journey']['bank']['balance'] if s['journey'].get('bank') else 0)


def refused(test, s, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, 'jr_pet_wfuse_auto', **p)
    test.assertEqual(s, before)
    return str(cm.exception)


def wardrobe(wallet=50_000_000, *buys):
    """A save with a pet and the pieces bought: (piece, rank, qty)…"""
    s = story()
    s['journey']['wallet'] = wallet
    s['journey']['stats']['max_wallet'] = wallet
    s, pid = get(s, 'Mun')
    for k, r, q in buys or (('canh_cong', 0, 11), ('no_hong', 0, 6), ('canh_cong', 1, 3), ('vong_chuong', 0, 2)):
        s, out = act(s, 'jr_pet_wbuy', id=k, rank=min(r, 1), qty=q, confirm=True)
        for i in WB(s)['it']:
            if i['id'] in out.get('items', [out['item']]):
                i['r'] = r                                                # B and up: as a fusion makes them
    return s, pid


def by_hand(s, budget, keep_worn=True):
    """The same fusions one jr_pet_wfuse at a time: the lowest rank, then the catalogue's order (worn ones kept out)."""
    order = [i['id'] for i in W.ITEMS]
    n = spent = 0
    while n < pw.AUTO_MAX:
        x = WB(s)
        count = {}
        for i in x['it']:
            if i['r'] < pw.TOP and not (keep_worn and pw.wearer(x, i['id'])):
                count[(i['k'], i['r'])] = count.get((i['k'], i['r']), 0) + 1
        ready = sorted((r, order.index(k), k) for (k, r), c in count.items() if c >= 3)
        if not ready or spent + pw.FUSE_FEE[ready[0][0]] > budget:
            break
        r, _, k = ready[0]
        s, _ = act(s, 'jr_pet_wfuse', k=k, r=r, confirm=True)
        spent += pw.FUSE_FEE[r]
        n += 1
    return s, n, spent


class Same(unittest.TestCase):
    def test_equals_the_fusions_one_by_one(self):
        for seed in (1, 7, 2024, 99):
            for budget in (10**7, 3_000, 1_700):
                with self.subTest(seed=seed, budget=budget):
                    s0, _ = wardrobe()
                    with seeded(seed), clock():
                        a, r = act(copy.deepcopy(s0), 'jr_pet_wfuse_auto', budget=budget, confirm=True)
                    with seeded(seed), clock():
                        b, n, spent = by_hand(copy.deepcopy(s0), budget)
                    self.assertEqual(WB(a), WB(b))
                    self.assertEqual(money(a), money(b))
                    self.assertEqual(money(s0) - money(a), spent)
                    self.assertEqual(a['journey']['pets']['stats']['xu'], b['journey']['pets']['stats']['xu'])
                    self.assertEqual((r['auto']['n'], r['auto']['spent']), (n, spent))
                    self.assertLessEqual(spent, budget)
                    validate_state(a)

    def test_the_summary(self):
        s, _ = wardrobe(50_000_000, ('canh_cong', 3, 3))
        with always(0), clock():
            s, r = act(s, 'jr_pet_wfuse_auto', budget=10**6, confirm=True)
        a = r['auto']
        self.assertEqual((a['n'], a['ok'], a['lux'], a['spent'], a['used'], a['stop'], a['left']),
                         (1, 1, 1, pw.FUSE_FEE[3], 3, 'done', 0))
        self.assertEqual(a['made'], [dict(id=WB(s)['it'][0]['id'], k=W.LUX['back'], r=4)])
        self.assertEqual(WB(s)['hot'], [a['made'][0]['id'], int(NOW)])
        self.assertIn('dòng sang', r['message'])
        self.assertTrue(r['ok'])
        # a cascade: nine D make three C, the three C a B, all in one command
        s, _ = wardrobe(50_000_000, ('no_hong', 0, 9))
        with always(0):
            s, r = act(s, 'jr_pet_wfuse_auto', budget=10**6, confirm=True)
        self.assertEqual([(i['k'], i['r']) for i in WB(s)['it']], [('no_hong', 2)])
        self.assertEqual((r['auto']['n'], r['auto']['used'], len(r['auto']['made'])), (4, 9, 1))
        # one scope: only that piece; a max rank: nothing above it
        s, _ = wardrobe()
        with always(0):
            t, r = act(copy.deepcopy(s), 'jr_pet_wfuse_auto', scope='no_hong', budget=10**6, confirm=True)
        self.assertEqual(sorted((i['k'], i['r']) for i in WB(t)['it'] if i['k'] == 'canh_cong'),
                         sorted((i['k'], i['r']) for i in WB(s)['it'] if i['k'] == 'canh_cong'))
        self.assertEqual(sorted(i['r'] for i in WB(t)['it'] if i['k'] == 'no_hong'), [1, 1])
        with always(0):
            t, r = act(copy.deepcopy(s), 'jr_pet_wfuse_auto', max_rank=1, budget=10**6, confirm=True)
        self.assertEqual(max(i['r'] for i in WB(t)['it']), 1)


class Limits(unittest.TestCase):
    def test_budget(self):
        s, _ = wardrobe()
        w = s['journey']['wallet']
        with always(9999):                                                   # every one fails: the triple stays
            t, r = act(copy.deepcopy(s), 'jr_pet_wfuse_auto', budget=500, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['spent'], r['auto']['stop']), (2, 400, 'budget'))
        self.assertEqual(t['journey']['wallet'], w - 400)
        self.assertEqual(len(WB(t)['it']), len(WB(s)['it']))
        self.assertFalse(r['ok'])
        self.assertIn('ngân sách', r['message'])
        self.assertIn('200 xu', refused(self, s, budget=199, confirm=True))   # not even the first one
        for bad in (0, -1, 2.5, '500', True, None, 10**13):
            with self.subTest(budget=bad):
                refused(self, s, budget=bad, confirm=True)
        refused(self, s, confirm=True)                                         # the budget is required
        for bad in (dict(scope='zzz'), dict(scope=3), dict(max_rank=0), dict(max_rank=7), dict(keep_worn='yes'),
                    dict(extra=1)):
            with self.subTest(**{k: str(v) for k, v in bad.items()}):
                refused(self, s, budget=10**6, confirm=True, **bad)
        self.assertIn('Xác nhận', refused(self, s, budget=10**6, confirm=False))

    def test_cap_of_fifty(self):
        s, _ = wardrobe(50_000_000, ('no_hong', 0, 20), ('canh_cong', 0, 20))
        with always(9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_wfuse_auto', budget=10**9, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['stop'], r['auto']['spent']), (pw.AUTO_MAX, 'cap', 200 * pw.AUTO_MAX))
        self.assertEqual(WB(t)['day']['f'], pw.AUTO_MAX)
        with always(0):
            t, r = act(copy.deepcopy(s), 'jr_pet_wfuse_auto', budget=10**9, confirm=True)
        self.assertLessEqual(r['auto']['n'], pw.AUTO_MAX)
        self.assertEqual(r['auto']['ok'], r['auto']['n'])
        validate_state(t)

    def test_no_triple_is_a_clear_refusal(self):
        s, _ = wardrobe(50_000_000, ('no_hong', 0, 2), ('canh_cong', 1, 2))
        msg = refused(self, s, budget=10**6, confirm=True)
        self.assertIn('Không còn ba món giống hệt nhau', msg)
        s, _ = wardrobe(50_000_000, ('no_hong', 0, 3))
        for i in WB(s)['it']:
            i['r'] = pw.TOP                                                   # SSS: nothing above
        self.assertIn('Không còn ba món', refused(self, s, budget=10**6, confirm=True))

    def test_the_money_wallet_then_the_account(self):
        s, _ = wardrobe(5_000_000, ('no_hong', 0, 3))
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=s['journey']['wallet'] - 300)
        bal = s['journey']['bank']['balance']
        self.assertEqual(s['journey']['wallet'], 300)
        with always(9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_wfuse_auto', budget=1_000, confirm=True)
        self.assertEqual((t['journey']['wallet'], t['journey']['bank']['balance']), (0, bal - 700))
        self.assertIn('300 xu tiền mặt và 700 xu từ tài khoản', r['message'])
        self.assertEqual(t['journey']['pets']['stats']['xu'], s['journey']['pets']['stats']['xu'] + 1_000)
        validate_state(t)
        # no account: what the wallet holds, then it stops
        s, _ = wardrobe(1_000_000, ('no_hong', 0, 3))
        s['journey']['wallet'] = 500
        with always(9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_wfuse_auto', budget=10_000, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['stop'], t['journey']['wallet']), (2, 'money', 100))
        s['journey']['wallet'] = 150
        self.assertIn('Còn thiếu 50 xu', refused(self, s, budget=10_000, confirm=True))


class Worn(unittest.TestCase):
    def test_worn_items_are_left_alone(self):
        s, pid = wardrobe(50_000_000, ('canh_cong', 0, 4))
        one = WB(s)['it'][0]['id']
        s, _ = act(s, 'jr_pet_wwear', pet=pid, slot='back', item=one)
        with always(0):
            t, r = act(copy.deepcopy(s), 'jr_pet_wfuse_auto', budget=10**6, confirm=True)
        self.assertEqual(r['auto']['n'], 1)
        self.assertEqual(WB(t)['on'], {pid: {'back': one}})
        self.assertIn(dict(id=one, k='canh_cong', r=0), WB(t)['it'])
        # three with one worn: nothing to fuse, unless keep_worn is false (then as jr_pet_wfuse: taken off)
        s, pid = wardrobe(50_000_000, ('canh_cong', 0, 3))
        s, _ = act(s, 'jr_pet_wwear', pet=pid, slot='back', item=WB(s)['it'][0]['id'])
        self.assertIn('đang mặc', refused(self, s, budget=10**6, confirm=True))
        with always(0):
            t, r = act(copy.deepcopy(s), 'jr_pet_wfuse_auto', keep_worn=False, budget=10**6, confirm=True)
        self.assertEqual(([(i['k'], i['r']) for i in WB(t)['it']], WB(t)['on']), ([('canh_cong', 1)], {}))
        validate_state(t)


class Replay(unittest.TestCase):
    """Through the store, as the browser sends it: a lost answer re-sent with its request id fuses and charges once."""

    def test_request_id(self):
        from game import marriage as mr
        from game.storage import Store
        tmp = tempfile.TemporaryDirectory(prefix='mnl-af-', ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / 's.db', story=True)
        self.addCleanup(store.close_pool)
        token, _, _ = store.session()
        store.read(token)

        def fn(s):
            s['journey']['wallet'] = 1_000_000
            x = pw._ensure(s)
            for _ in range(6):
                pw._new(x, 'no_hong', 0)
        mr._mutate(store, {store.key(token): fn})
        rev = store.read(token)[1]
        pay = dict(budget=600, confirm=True)
        with always(9999):
            one = store.command(token, 'req-afuse-0001', rev, None, 'jr_pet_wfuse_auto', pay)
            again = store.command(token, 'req-afuse-0001', rev, None, 'jr_pet_wfuse_auto', pay)
        self.assertEqual(one['result'], again['result'])
        self.assertEqual(one['result']['auto']['n'], 3)
        s, rev2 = store.read(token)[:2]
        self.assertEqual(s['journey']['wallet'], 1_000_000 - 600)
        self.assertEqual(WB(s)['day']['f'], 3)
        with self.assertRaises(GameError):
            store.command(token, 'req-afuse-0002', rev, None, 'jr_pet_wfuse_auto', pay)   # the stale revision
        with always(0):
            store.command(token, 'req-afuse-0003', rev2, None, 'jr_pet_wfuse_auto', pay)
        s = store.read(token)[0]
        self.assertEqual(s['journey']['wallet'], 1_000_000 - 1_000)
        self.assertEqual(sorted(i['r'] for i in WB(s)['it']), [1, 1])
        validate_state(s)


# ---------------------------------------------------------------- the live release
MANUAL = '''import copy,json,sys
from unittest import mock
from game import pet_tiers as px, pet_wardrobe as pw, pets as pt
from game import journey as jr
from game.engine import apply_action,new_state,validate_state
s=new_state();jr.enable_story(s,4242);s['journey'].update(gender='female',wallet=50000000)
s['journey']['stats']['max_wallet']=50000000
validate_state(s)
out=[]
rng=__import__('random').Random(5)
pick=(lambda n:rng.randrange(n)) if sys.argv[2]=='seed' else (lambda n:0)
with mock.patch.object(px,'roll',pick), mock.patch.object(pw,'vn_date',lambda:'2026-10-20'), \\
        mock.patch('time.time',lambda:1792500000.0):
    for name,p in json.loads(sys.argv[1]):
        try:
            s,r=apply_action(s,None,name,p);out.append([r.get('message'),r.get('ok'),r.get('item'),r.get('lux')])
        except Exception as e:
            out.append(['ERR',str(e)])
print(json.dumps([s['journey'],out],sort_keys=True,ensure_ascii=False))
'''


class Live(unittest.TestCase):
    def tree(self, rev):
        tmp = tempfile.mkdtemp(prefix=f'mnl-af-{rev}-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', rev, 'game', 'reference'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {rev}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def run_in(self, where, code, *args, stdin=''):
        env = dict(os.environ, PYTHONPATH=str(where), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', code, *args], input=stdin, capture_output=True, text=True, cwd=where,
                             env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return out.stdout.strip().splitlines()[-1]

    def test_manual_fuse_is_the_live_one(self):
        """jr_pet_wfuse after the refactor: the journey and the answers 2.4.67 gives (same save, rolls, clock)."""
        cmds = [['jr_pet_adopt', dict({'from': 'shop'}, breed='corgi', coat=1, nick='Tofu', confirm=True)],
                ['jr_pet_wbuy', dict(id='canh_cong', qty=20, confirm=True)],
                ['jr_pet_wbuy', dict(id='canh_cong', rank=1, qty=6, confirm=True)],
                ['jr_pet_wbuy', dict(id='no_hong', qty=3, confirm=True)]]
        cmds += [['jr_pet_wwear', dict(pet='p1', slot='back', item='o1')]]
        cmds += [['jr_pet_wfuse', dict(k=k, r=r, confirm=True)] for k, r in
                 [('canh_cong', 0)] * 8 + [('canh_cong', 1)] * 6 + [('canh_cong', 2)] * 4 + [('no_hong', 0)] * 3
                 + [('canh_cong', 3)] * 3 + [('no_hong', 5)]]
        live = self.tree(LIVE)
        args = (json.dumps(cmds), 'seed')
        old = json.loads(self.run_in(live, MANUAL, *args))
        new = json.loads(self.run_in(ROOT, MANUAL, *args))
        self.assertEqual(old, new)
        self.assertTrue(any(o[1] is True for o in new[1][5:]) and any(o[1] is False for o in new[1][5:]))
        # every roll 0: each one a success, A → S a luxury piece (the street's ticker too)
        cmds = cmds[:1] + [['jr_pet_wbuy', dict(id='canh_cong', rank=1, qty=20, confirm=True)]] * 3
        cmds += [['jr_pet_wfuse', dict(k='canh_cong', r=r, confirm=True)] for r, n in ((1, 20), (2, 6), (3, 2)) for _ in range(n)]
        args = (json.dumps(cmds), 'zero')
        old = json.loads(self.run_in(live, MANUAL, *args))
        new = json.loads(self.run_in(ROOT, MANUAL, *args))
        self.assertEqual(old, new)
        self.assertEqual([o[3] for o in new[1][-2:]], [True, True])
        self.assertIsNotNone(new[0]['petw']['hot'])

    def test_auto_fuse_saves_load_on_the_live_releases(self):
        saves = []
        for seed in (3, 11):
            s, pid = wardrobe(50_000_000, ('canh_cong', 0, 20), ('no_hong', 0, 9), ('canh_cong', 3, 6))
            s, _ = act(s, 'jr_pet_wwear', pet=pid, slot='back', item=WB(s)['it'][0]['id'])
            with seeded(seed):
                s, r = act(s, 'jr_pet_wfuse_auto', budget=10**7, confirm=True)
            self.assertGreater(r['auto']['n'], 3)
            self.assertEqual(set(WB(s)), pw.BLOCK_KEYS)                      # no new save key
            validate_state(s)
            saves.append(s)
        x = pw._ensure(saves[1])                                              # and one with a luxury piece and an SSS
        pw._new(x, W.LUX['back'], 4)
        pw._new(x, 'no_hong', pw.TOP)
        validate_state(saves[1])
        for label, rev in RELEASES.items():
            with self.subTest(release=label):
                got = json.loads(self.run_in(self.tree(rev), PROG, stdin=json.dumps(saves)))
                for (before, fed), x in zip(got, saves):
                    _, _, petw, _ = json.loads(before)
                    self.assertEqual(petw, x['journey']['petw'])
                    self.assertTrue(fed)


if __name__ == '__main__':
    unittest.main()
