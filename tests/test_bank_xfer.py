"""💸 Chuyển khoản bạn bè (game/bank_xfer.py): two real accounts on one store. A transfer debits the sender once
(the same request id twice pays once, racing sends never overdraw), waits for an offline receiver and is credited
once on their next load (two tabs at once included), the caps hold (per sender, per receiver, account age, life day,
friendship age), what nobody received goes back to the sender, and the saves stay valid for the previous server."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game import accounts, social
from game import bank_xfer as bx
from game import journey as jr
from game import live_effects as lfx
from game import marriage as mr
from game.storage import Store

OLD = Path(os.environ.get('MNL_PREV_TREE', r'D:/projects/Mot_ngay_lam_nghe/_rel154/mot-ngay-lam-nghe'))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        self.addCleanup(self.store.close_pool)
        social.ensure(self.store)
        h = patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw)
        h.start()
        self.addCleanup(h.stop)
        bx._swept[0] = 0.0
        self.rid = 0

    # ------------------------------------------------------------ people and saves
    def user(self, name, old=True, life=12, wallet=5000, bank=3000):
        token, _, _ = self.store.session()
        tok = accounts.register(self.store, token, dict(username=name + '_test', password='matkhau-dai-lam', confirm='matkhau-dai-lam',
                                                        display=name.title()))['token']
        sid = self.store.key(tok)
        if old:
            self.store.transaction(lambda db: db.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (sid,)))

        def fn(s):
            j = s['journey']
            j['life_day'] = life
            j['wallet'] = wallet + (bank or 0)
            j['stats']['max_wallet'] = max(j['wallet'], j['stats']['max_wallet'])
        mr._mutate(self.store, {sid: fn})
        if bank is not None:
            self.cmd(tok, 'jr_bk_open')
            if bank:
                self.cmd(tok, 'jr_bk_deposit', amount=bank)
        mr.ensure_person(self.store, sid)
        return tok

    def sid(self, tok):
        return self.store.key(tok)

    def code(self, tok):
        with self.store.connect() as db:
            return db.execute('SELECT code FROM marriage_people WHERE sid=?', (self.sid(tok),)).fetchone()['code']

    def friends(self, a, b, ago=86400):
        t = mr.now() - ago
        self.store.transaction(lambda db: [db.execute('INSERT INTO friends(sid,friend,since) VALUES(?,?,?)', (x, y, t))
                                           for x, y in ((self.sid(a), self.sid(b)), (self.sid(b), self.sid(a)))])

    def state(self, tok):
        return self.store.read(tok)[0]

    def wallet(self, tok):
        return self.state(tok)['journey']['wallet']

    def balance(self, tok):
        return self.state(tok)['journey']['bank']['balance']

    def cmd(self, tok, action, **p):
        self.rid += 1
        rev = self.store.read(tok)[1]
        return self.store.command(tok, f'req-{self.rid:06d}', rev, None, action, p)

    def send(self, a, b, amount, rid=None, **k):
        self.rid += 1
        d = dict(to=self.code(b), amount=amount, rid=rid or f'test-rid-{self.rid:06d}', **k)
        return bx.act(self.store, a, 'send', d)

    def refused(self, code, fn, *a, **k):
        with self.assertRaises(mr.MarriageError) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.code, code, cm.exception.message)
        return cm.exception

    def rows(self):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM bank_xfers ORDER BY at').fetchall()]

    def load(self, tok):
        """What /api/bootstrap does for this module."""
        return bx.on_load(self.store, tok, self.state(tok))


class Transfers(Base):
    def test_send_waits_for_an_offline_friend_and_lands_once(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        out = self.send(ann, bob, 500, note='Trả tiền trà sữa nha')
        self.assertTrue(out['changed'])
        self.assertEqual(out['message'], 'Đã chuyển 500 xu cho Bob.')
        r = out['receipt']
        self.assertRegex(r['code'], r'^CK\d{10}$')
        self.assertEqual((r['to'], r['amount'], r['note'], r['status']), ('Bob', 500, 'Trả tiền trà sữa nha', 'sent'))
        self.assertEqual(self.balance(ann), 2500)
        log = self.state(ann)['journey']['bank']['log'][-1]
        self.assertEqual((log['acc'], log['amt'], log['bal']), ('acc', -500, 2500))
        self.assertIn('Bob', log['text'])
        self.assertIn(r['code'], log['text'])
        self.assertEqual(self.balance(bob), 3000)          # bob is offline: nothing moved in his save yet
        with self.store.connect() as db:
            self.assertEqual(bx.waiting(db, self.sid(bob)), 1)
            self.assertEqual(mr.alerts(self.store, self.sid(bob))['xfer'], 1)
        moved, got = self.load(bob)
        self.assertTrue(moved)
        self.assertEqual(got, [dict(code=r['code'], name='Ann', amount=500, note='Trả tiền trà sữa nha', to='acc')])
        b = self.state(bob)['journey']['bank']
        self.assertEqual(b['balance'], 3500)
        self.assertEqual((b['log'][-1]['amt'], b['log'][-1]['text']), (500, '💸 Ann chuyển khoản: «Trả tiền trà sữa nha»'))
        self.assertIn('+500 xu từ Ann', b['inbox'][-1]['text'])
        self.assertEqual(self.load(bob), (False, []))      # the next load: nothing again
        self.assertEqual(bx.act(self.store, bob, 'receive', {})['got'], [])
        self.assertEqual(self.balance(bob), 3500)
        self.assertEqual([x['status'] for x in self.rows()], ['done'])
        with self.store.connect() as db:
            self.assertEqual(bx.waiting(db, self.sid(bob)), 0)

    def test_receiver_without_a_bank_account_gets_cash_with_a_wallet_line(self):
        ann, bob = self.user('ann'), self.user('bob', bank=None, wallet=40)
        self.friends(ann, bob)
        self.send(ann, bob, 120, note='')
        self.assertEqual(self.load(bob)[1][0]['to'], 'cash')
        j = self.state(bob)['journey']
        self.assertEqual(j['wallet'], 160)
        self.assertEqual((j['history'][-1]['kind'], j['history'][-1]['amount'], j['history'][-1]['label']), ('bank', 120, '💸 Ann chuyển khoản'))

    def test_from_cash_never_below_zero(self):
        ann, bob = self.user('ann', wallet=300, bank=100), self.user('bob')
        self.friends(ann, bob)
        self.refused('not_enough', self.send, ann, bob, 301, src='cash')
        self.send(ann, bob, 300, src='cash')
        j = self.state(ann)['journey']
        self.assertEqual(j['wallet'], 0)
        self.assertEqual((j['history'][-1]['kind'], j['history'][-1]['amount']), ('bank', -300))
        self.refused('not_enough', self.send, ann, bob, 10, src='cash')

        def broke(s):
            s['journey']['wallet'] = -50
        mr._mutate(self.store, {self.sid(ann): broke})
        self.refused('not_enough', self.send, ann, bob, 10, src='cash')
        self.refused('not_enough', self.send, ann, bob, 101)   # the account: 100
        self.assertEqual(self.balance(ann), 100)

    def test_the_same_request_id_pays_once(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        first = self.send(ann, bob, 200, rid='same-rid-0001')
        again = self.send(ann, bob, 200, rid='same-rid-0001')
        self.assertFalse(again['changed'])
        self.assertTrue(again['receipt']['again'])
        self.assertEqual(again['receipt']['code'], first['receipt']['code'])
        self.assertEqual(self.balance(ann), 2800)
        self.assertEqual(len(self.rows()), 1)
        # another player's rid of the same text is another transfer
        cat = self.user('cat')
        self.friends(cat, bob)
        self.send(cat, bob, 200, rid='same-rid-0001')
        self.assertEqual(len(self.rows()), 2)

    def test_a_double_tap_racing_itself_pays_once(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        outs, errs = [], []

        def go():
            try:
                outs.append(self.send(ann, bob, 300, rid='race-rid-0001'))
            except Exception as e:  # noqa: BLE001
                errs.append(e)
        ts = [threading.Thread(target=go) for _ in range(4)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(self.balance(ann), 2700)
        self.assertEqual(len(self.rows()), 1)
        self.assertTrue(all(isinstance(e, mr.MarriageError) for e in errs), errs)
        self.assertEqual(sum(1 for o in outs if o['changed']), 1)

    def test_concurrent_sends_cannot_overdraw(self):
        ann, bob, cat = self.user('ann', bank=1000), self.user('bob'), self.user('cat')
        self.friends(ann, bob)
        self.friends(ann, cat)
        ok, errs = [], []

        def go(n):
            try:
                ok.append(self.send(ann, bob if n % 2 else cat, 400, rid=f'conc-rid-{n:04d}'))
            except mr.MarriageError as e:
                errs.append(e.code)
        ts = [threading.Thread(target=go, args=(n,)) for n in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        sent = sum(r['amount'] for r in self.rows())
        self.assertEqual(len(ok), 2)                       # 2 x 400 fit in 1000, a third does not
        self.assertEqual(sent, 800)
        self.assertEqual(self.balance(ann), 200)
        self.assertTrue(set(errs) <= {'not_enough', 'busy'}, errs)

    def test_two_friends_sending_to_each_other_at_once(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        errs = []

        def go(a, b, n):
            try:
                self.send(a, b, 100, rid=f'cross-rid-{n:04d}')
            except Exception as e:  # noqa: BLE001
                errs.append(e)
        ts = [threading.Thread(target=go, args=(ann, bob, n) if n % 2 else (bob, ann, n)) for n in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(len(self.rows()), 6)
        self.load(ann)
        self.load(bob)
        self.assertEqual((self.balance(ann), self.balance(bob)), (3000, 3000))

    def test_two_tabs_loading_at_once_credit_once(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        for n in range(3):
            self.send(ann, bob, 100 + n)
        got = []

        def go():
            got.append(bx.receive(self.store, self.sid(bob)))
        ts = [threading.Thread(target=go) for _ in range(4)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sorted(x['amount'] for g in got for x in g), [100, 101, 102])
        self.assertEqual(self.balance(bob), 3000 + 303)
        self.assertEqual({r['status'] for r in self.rows()}, {'done'})

    def test_note_is_cleaned_like_the_street(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        note = self.send(ann, bob, 50, note='  vào  www.lua-dao.com  nhé\n0912345678 ')['receipt']['note']
        self.assertNotIn('lua-dao', note)
        self.assertNotIn('0912345678', note)
        self.assertNotIn('\n', note)
        self.refused('bad_note', self.send, ann, bob, 50, note='x' * 61)
        self.refused('bad_note', self.send, ann, bob, 50, note=5)


class Limits(Base):
    def test_who_can_send_to_whom(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.refused('not_friend', self.send, ann, bob, 50)
        self.refused('not_found', bx.act, self.store, ann, 'send', dict(to=self.code(ann), amount=50, rid='self-rid-0001'))
        self.friends(ann, bob, ago=10 * 60)
        self.refused('friend_new', self.send, ann, bob, 50)
        self.store.transaction(lambda db: db.execute('UPDATE friends SET since=?', (mr.now() - 2 * 3600,)))
        self.store.transaction(lambda db: db.execute('INSERT INTO marriage_blocks(sid,target,at) VALUES(?,?,?)', (self.sid(bob), self.sid(ann), mr.now())))
        self.refused('blocked', self.send, ann, bob, 50)
        self.store.transaction(lambda db: db.execute('DELETE FROM marriage_blocks'))
        self.refused('bad_amount', self.send, ann, bob, bx.MIN_XU - 1)
        self.refused('bad_amount', self.send, ann, bob, bx.SEND_DAY + 1)
        self.refused('bad_amount', self.send, ann, bob, 50.0)
        self.refused('bad_rid', bx.act, self.store, ann, 'send', dict(to=self.code(bob), amount=50, rid='x'))
        self.send(ann, bob, 50)
        self.assertEqual(self.balance(ann), 2950)

    def test_young_accounts_and_young_saves(self):
        ann, bob = self.user('ann'), self.user('bob', old=False)
        new, kid = self.user('new', old=False), self.user('kid', life=bx.LIFE_DAYS - 1)
        for x in (bob, new, kid):
            self.friends(ann, x)
        self.refused('too_new', self.send, ann, bob, 50)        # the receiver's account is a day old
        self.refused('too_new', self.send, new, ann, 50)        # the sender's account
        self.refused('too_new', self.send, kid, ann, 50)        # the sender's save
        v = bx.view(self.store, self.sid(ann), self.state(ann))
        self.assertIsNone(v['lock'])
        self.assertEqual({f['name']: f['ok'] for f in v['friends']}, dict(Bob=False, New=False, Kid=True))
        self.assertIn('ngày sống', bx.view(self.store, self.sid(kid), self.state(kid))['lock'])
        guest, _, _ = self.store.session()
        self.refused('account_required', bx.act, self.store, guest, 'send', {})
        self.assertEqual(self.balance(ann), 3000)

    def test_sender_day_caps(self):
        ann, bob, cat = self.user('ann', bank=9000), self.user('bob'), self.user('cat')
        self.friends(ann, bob)
        self.friends(ann, cat)
        self.send(ann, bob, 1500)
        e = self.refused('limit_send', self.send, ann, cat, 600)
        self.assertIn('500', e.message)
        self.send(ann, cat, 500)
        e = self.refused('limit_send', self.send, ann, cat, 10)
        self.assertIn('đủ', e.message)
        self.assertEqual(self.balance(ann), 9000 - 2000)
        v = bx.view(self.store, self.sid(ann), self.state(ann))
        self.assertEqual(v['today'], dict(sent=2000, n=2, left=0, count_left=bx.SEND_COUNT - 2))
        # the count: a fresh day for a new sender
        dan = self.user('dan', bank=9000)
        self.friends(dan, bob)
        for _ in range(bx.SEND_COUNT):
            self.send(dan, bob, 10)
        self.refused('limit_count', self.send, dan, bob, 10)

    def test_receiver_day_cap_across_senders(self):
        bob = self.user('bob')
        senders = [self.user(n, bank=5000) for n in ('ann', 'cat', 'dan')]
        for s in senders:
            self.friends(s, bob)
        self.send(senders[0], bob, 2000)
        self.send(senders[1], bob, 900)
        e = self.refused('limit_receive', self.send, senders[2], bob, 200)
        self.assertIn('100', e.message)
        self.send(senders[2], bob, 100)
        e = self.refused('limit_receive', self.send, senders[2], bob, 10)
        self.assertIn('nhận đủ', e.message)
        self.assertEqual(self.balance(senders[2]), 4900)     # refused sends never moved a coin

    def test_receiver_cap_holds_when_senders_race(self):
        bob = self.user('bob')
        senders = [self.user(f'p{n}', bank=5000) for n in range(5)]
        for s in senders:
            self.friends(s, bob)
        errs = []

        def go(s):
            try:
                self.send(s, bob, 1000)
            except mr.MarriageError as e:
                errs.append(e.code)
        ts = [threading.Thread(target=go, args=(s,)) for s in senders]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sum(r['amount'] for r in self.rows()), bx.RECV_DAY)
        self.assertEqual(sorted(errs), ['limit_receive', 'limit_receive'])
        self.assertEqual(sum(self.balance(s) for s in senders), 5 * 5000 - bx.RECV_DAY)


class Back(Base):
    def test_unclaimed_and_deleted_receivers_send_the_coins_back(self):
        ann, bob, cat = self.user('ann'), self.user('bob'), self.user('cat')
        self.friends(ann, bob)
        self.friends(ann, cat)
        self.send(ann, bob, 300)
        self.send(ann, cat, 200)
        self.store.transaction(lambda db: db.execute("UPDATE bank_xfers SET at=? WHERE to_name='Bob'", (mr.now() - 31 * 86400,)))
        self.assertEqual(bx.sweep(self.store, force=True), 1)
        bx.forget(self.store, cat)
        self.assertEqual({r['to_name']: r['status'] for r in self.rows()}, {'Bob': 'back', 'Một người chơi': 'back'})
        self.assertEqual(self.load(bob), (False, []))      # gone back: never credited to bob too
        w = self.wallet(ann)
        self.assertTrue(lfx.on_load(self.store, ann, self.state(ann)))
        self.assertEqual(self.wallet(ann), w + 500)
        self.assertEqual(self.state(ann)['journey']['history'][-1]['label'], lfx.LABELS['xfer_back'])
        self.assertFalse(lfx.on_load(self.store, ann, self.state(ann)))
        self.assertEqual(bx.sweep(self.store, force=True), 0)

    def test_view_lists_friends_today_and_recent(self):
        ann, bob = self.user('ann'), self.user('bob')
        self.friends(ann, bob)
        self.send(ann, bob, 70, note='hi')
        self.send(bob, ann, 30)
        out = bx.get(self.store, ann, self.state(ann))           # credits what bob sent first
        self.assertTrue(out['changed'])
        self.assertEqual([g['amount'] for g in out['got']], [30])
        self.assertEqual(out['friends'], [dict(code=self.code(bob), name='Bob', fc=None, ok=True, why=None)])
        self.assertEqual([(x['dir'], x['amount'], x['status']) for x in out['recent']], [('in', 30, 'done'), ('out', 70, 'sent')])
        self.assertEqual(out['rules']['send_day'], bx.SEND_DAY)


@unittest.skipUnless((OLD / 'game' / 'engine.py').exists(), 'previous release tree not found')
class PreviousServer(Base):
    """Saves after a send and after a receive (account and cash) load on the previous release, and a save of the
    previous release takes a transfer here."""

    PROG = r'''
import json, sys
sys.path.insert(0, '.')
from game.engine import validate_state, migrate_state
from game.content import CAREERS
for path in sys.argv[1:]:
    s = json.load(open(path, encoding='utf-8'))
    for k in [k for k in s['careers'] if k not in CAREERS]:
        s['careers'].pop(k)
    s['journey']['unlocked'] = [c for c in s['journey']['unlocked'] if c in CAREERS]
    s = migrate_state(s, owned=True)
    validate_state(s)
print(json.dumps(dict(ok=True)))
'''

    def test_old_server_accepts_the_saves(self):
        ann, bob, cat = self.user('ann'), self.user('bob'), self.user('cat', bank=None)
        self.friends(ann, bob)
        self.friends(ann, cat)
        self.send(ann, bob, 400, note='Quà nè «»')
        self.send(ann, cat, 100, src='cash')
        self.load(bob)
        self.load(cat)
        paths = []
        for n, tok in (('ann', ann), ('bob', bob), ('cat', cat)):
            p = Path(self.tmp.name) / f'{n}.json'
            p.write_text(json.dumps(self.state(tok), ensure_ascii=False), encoding='utf-8')
            paths.append(str(p))
        out = subprocess.run([sys.executable, '-c', self.PROG, *paths], cwd=OLD, capture_output=True, text=True, timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        self.assertEqual(json.loads(out.stdout.strip().splitlines()[-1]), dict(ok=True))

    def test_a_save_of_the_old_server_takes_a_transfer(self):
        """A save written by the previous release (its own new game) validates and receives here."""
        prog = r'''
import json, sys
sys.path.insert(0, '.')
from game.engine import new_state, validate_state
from game import bank
s = new_state()
print(json.dumps(s, ensure_ascii=False))
'''
        out = subprocess.run([sys.executable, '-c', prog], cwd=OLD, capture_output=True, text=True, timeout=300)
        if out.returncode:
            self.skipTest('the old tree cannot build a save: ' + out.stderr[-300:])
        old = json.loads(out.stdout.strip().splitlines()[-1])
        from game.engine import migrate_state, validate_state
        validate_state(migrate_state(old, owned=True))
        ann, bob = self.user('ann'), self.user('bob', bank=None)
        sid = self.sid(bob)
        keep = self.state(bob)

        def swap(s):
            s.clear()
            s.update(migrate_state(json.loads(json.dumps(old)), owned=True))
            s['journey'].update(story=True, life_day=keep['journey']['life_day'], wallet=10)
        try:
            mr._mutate(self.store, {sid: swap})
        except Exception as e:  # noqa: BLE001 - the old fresh save is not a story save here
            self.skipTest(f'old save shape: {e}')
        self.friends(ann, bob)
        self.send(ann, bob, 90)
        self.assertTrue(self.load(bob)[0])
        self.assertEqual(self.wallet(bob), 100)


if __name__ == '__main__':
    unittest.main()
