"""💌 Thiệp mời cưới cả phố (game/wed_invite.py, live/wedinvite.py; owner 08/10: "thông báo cưới toàn server ... hiển
thị cho toàn server 1 lần ... mất 10k cho mỗi lần mời"): who may send, 10.000 xu paid exactly once (rid), nothing paid
when refused, the text cleaned and masked, the sender's limits, every other player shown each card once and at most
PER_DAY a day, blocks both ways, the party's own window, cheers, the admin's delete, the kill switch, the live frame,
and the sender's save still loading on the previous release."""
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import marriage as mr
from game import pg_schema
from game import social
from game import wed_invite as wi
from game import wedding_live as wl
from game.engine import validate_state
from tests.test_marriage import DAY, PLAN, Base
from tests import test_admin_gift as _ag
from tests.live_support import HAVE_WS, LiveCase

ROOT = Path(__file__).resolve().parents[1]
TEXT = 'Trân trọng kính mời cả phố tới chung vui cùng hai đứa mình nha!'


class InvBase(Base):
    def setUp(self):
        super().setUp()
        for target in ('game.wedding_live.now', 'game.wed_invite.now', 'game.live_effects.now'):
            p = patch(target, self.clock)
            p.start()
            self.addCleanup(p.stop)
        wi._invalidate()
        self.addCleanup(wi._invalidate)
        self.rids = 0

    def send(self, tok, text=TEXT, rid=None, **kw):
        self.rids += 1
        wi._invalidate()
        return wi.send(self.store, tok, dict(text=text, rid=rid or f'rid-{self.rids:06d}', **kw))

    def due(self, tok):
        wi._invalidate()
        return wi.due(self.store, self.sid(tok))

    def show(self, tok, cid, cheer=False):
        return wi.seen(self.store, self.sid(tok), dict(id=cid, cheer=cheer))

    def booked(self, a_name='lananh', b_name='minhtu', at_in=2 * 3600):
        """An engaged couple with their wedding (and its live party) booked; both with 20.000 xu after paying."""
        a, b = self.user(a_name), self.user(b_name)
        self.engage(a, b)
        wid = self.plan_and_confirm(a, b, plan=dict(PLAN, at=self.clock.t + at_in))
        self.fund(a, 20_000)
        self.fund(b, 20_000)
        return a, b, wid

    def married_plain(self, a_name='an', b_name='binh'):
        """A married couple without a live party (an older life-day wedding)."""
        a, b = self.user(a_name), self.user(b_name)
        self.engage(a, b)
        self.plan_and_confirm(a, b)
        self.clock.t += 10 * DAY
        mr.on_load(self.store, a, self.state(a))
        self.assertEqual(self.view(a)['couple']['status'], 'married')
        self.fund(a, 20_000)
        self.fund(b, 20_000)
        return a, b


class Sending(InvBase):
    def test_who_may_send(self):
        single = self.user('doc_than', wallet=50_000)
        v = wi.me(self.store, single)
        self.assertFalse(v['can'])
        self.assertIn('đính hôn', v['why'])
        with self.assertRaises(mr.MarriageError) as e:
            self.send(single)
        self.assertEqual(e.exception.code, 'wedinv_refused')
        self.assertEqual(self.wallet(single), 50_000)
        guest, _, _ = self.store.session()
        self.assertFalse(wi.me(self.store, guest)['can'])
        with self.assertRaises(mr.MarriageError) as e:
            wi.send(self.store, guest, dict(text=TEXT))
        self.assertEqual(e.exception.code, 'account_required')
        # an engaged couple with a booked party: the card is tied to it
        a, b, wid = self.booked()
        v = wi.me(self.store, b)
        self.assertTrue(v['can'], v['why'])
        self.assertEqual((v['names'], v['party']['id'], v['price']), (dict(a='Minhtu', b='Lananh'), wid, 10_000))
        # a married couple without a party: a plain announcement
        c, d = self.married_plain()
        v = wi.me(self.store, c)
        self.assertTrue(v['can'], v['why'])
        self.assertIsNone(v['party'])
        # not in story mode (a dev save): refused, nothing paid
        mr._mutate(self.store, {self.sid(d): lambda s: s['journey'].__setitem__('story', False)})
        with self.assertRaises(mr.MarriageError) as e:
            self.send(d)
        self.assertEqual(e.exception.code, 'not_story')
        self.assertIsNone(self.row('SELECT * FROM wed_invites'))

    def test_paid_exactly_once_and_announced(self):
        a, b, wid = self.booked()
        sent = []
        from game import live_chat
        real = live_chat.notify
        with patch.object(live_chat, 'notify', side_effect=lambda db, e: (sent.append(e), real(db, e))):
            out = self.send(a, rid='same-request-01')
            again = self.send(a, rid='same-request-01')                      # a resent request
        self.assertTrue(out['changed'])
        self.assertTrue(again.get('again'))
        self.assertEqual(self.wallet(a), 10_000)
        self.assertEqual(self.wallet(b), 20_000)
        hist = self.state(a)['journey']['history'][-1]
        self.assertEqual((hist['kind'], hist['amount']), ('life', -10_000))
        rows = self.rows('SELECT * FROM wed_invites')
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r['sid'], r['partner'], r['wedding'], r['name_a'], r['name_b'], r['status']),
                         (self.sid(a), self.sid(b), wid, 'Lananh', 'Minhtu', 'live'))
        self.assertEqual(self.row('SELECT status, amount FROM marriage_effects WHERE id=?', r['rid']), dict(status='applied', amount=-10_000))
        self.assertEqual(sent, [dict(op='wedinvite', id=r['id'], pids=[social.pid_of(self.sid(a)), social.pid_of(self.sid(b))])])
        self.assertIn('thiệp mời', self.view(b)['me']['notice'])               # the partner is told
        validate_state(self.state(a))

    def test_not_enough_money_pays_nothing_and_sends_nothing(self):
        a, b, wid = self.booked()
        self.fund(a, 9_999)
        with self.assertRaises(mr.MarriageError) as e:
            self.send(a)
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(self.wallet(a), 9_999)
        self.assertIsNone(self.row('SELECT * FROM wed_invites'))
        self.assertIsNone(self.row("SELECT * FROM marriage_effects WHERE id LIKE 'wedinv:%'"))
        self.fund(a, 10_000)
        self.send(a)                                                           # exactly enough
        self.assertEqual(self.wallet(a), 0)

    def test_text_is_cleaned_and_masked(self):
        a, b, wid = self.booked()
        for bad in (None, 7, '', '   ngắn  ', 'x' * 201):
            with self.assertRaises(mr.MarriageError) as e:
                self.send(a, text=bad)
            self.assertEqual(e.exception.code, 'bad_text')
        self.assertEqual(self.wallet(a), 20_000)
        self.send(a, text='Mời cả phố\x00 ăn cưới‮ nha <b>vui</b>, gọi 0912 345 678 nhé')
        r = self.row('SELECT text, raw FROM wed_invites')
        self.assertNotIn('\x00', r['text'])
        self.assertNotIn('‮', r['text'])
        self.assertNotIn('0912', r['text'])                                    # the chat's mask: phone numbers
        self.assertIn('<b>vui</b>', r['text'])                                 # kept as text: the page escapes it
        self.assertIn('0912', r['raw'])                                        # the original, for admins only
        self.assertNotIn('raw', json.dumps(self.due(self.user('khach'))))

    def test_one_a_day_one_per_party_one_plain_per_couple(self):
        a, b, wid = self.booked(at_in=3 * DAY)
        self.send(a)
        with self.assertRaises(mr.MarriageError) as e:
            self.send(a)
        self.assertIn('tiệc này', e.exception.message)
        self.send(b)                                                           # the partner has their own
        self.clock.t += DAY + 60
        with self.assertRaises(mr.MarriageError) as e:
            self.send(a)
        self.assertIn('tiệc này', e.exception.message)
        self.assertFalse(wi.me(self.store, a)['can'])
        self.assertEqual(self.wallet(a), 10_000)
        # a married couple without a party: one plain card; then a party booked the same day waits for the next day
        c, d = self.married_plain()
        self.send(c)
        with self.assertRaises(mr.MarriageError) as e:
            self.send(c)
        self.assertIn('thông báo cưới', e.exception.message)
        self.act(c, 'party', at=self.clock.t + 2 * DAY)
        with self.assertRaises(mr.MarriageError) as e:
            self.send(c)
        self.assertIn('Mỗi ngày', e.exception.message)
        self.assertEqual(self.wallet(c), 10_000)
        self.clock.t += DAY + 60
        self.send(c)                                                           # the party's own card
        self.assertEqual(self.wallet(c), 0)
        self.assertEqual([r['wedding'] is None for r in self.rows('SELECT wedding FROM wed_invites WHERE sid=? ORDER BY id', self.sid(c))], [True, False])

    def test_kill_switch(self):
        a, b, wid = self.booked()
        self.send(a)
        viewer = self.user('khach')
        with patch.dict(os.environ, MNL_WED_INVITE_OFF='1'):
            self.assertEqual(self.due(viewer), [])
            self.assertFalse(wi.me(self.store, b)['can'])
            with self.assertRaises(mr.MarriageError) as e:
                self.send(b)
            self.assertEqual(e.exception.code, 'wedinv_off')
        self.assertEqual(self.wallet(b), 20_000)
        self.assertEqual(len(self.due(viewer)), 1)


class Delivery(InvBase):
    def test_every_other_player_once(self):
        a, b, wid = self.booked()
        viewer, other = self.user('khach'), self.user('hang_xom')
        guest, _, _ = self.store.session()
        self.assertEqual(self.due(viewer), [])
        self.send(a)
        cards = self.due(viewer)
        self.assertEqual(len(cards), 1)
        c = cards[0]
        at = float(self.row('SELECT at FROM wedding_parties WHERE wedding=?', wid)['at'])
        self.assertEqual((c['a'], c['b'], c['text'], c['party']['id'], c['party']['at_label']), ('Lananh', 'Minhtu', TEXT, wid, wl.fmt_at(at)))
        self.assertEqual(self.due(viewer), cards)                              # not shown yet: still due (a reload)
        self.assertTrue(self.show(viewer, c['id'])['shown'])
        self.assertEqual(self.due(viewer), [])                                 # two loads: once
        self.assertFalse(self.show(viewer, c['id'])['shown'])                  # a second tab: nothing more
        self.assertEqual(len(self.due(other)), 1)
        self.assertEqual(len(wi.due(self.store, self.store.key(guest))), 1)    # guests too
        self.assertEqual(self.due(a), [])                                      # never the couple's own card
        self.assertEqual(self.due(b), [])
        self.assertEqual(len(self.rows('SELECT * FROM wed_invite_seen')), 1)   # one row, written when shown

    def test_at_most_three_a_day_the_rest_wait(self):
        viewer = self.user('khach')
        ids = []
        for i in range(4):
            x, y, _ = self.booked(f'co{i}', f'chu{i}', at_in=3 * DAY)
            self.send(x)
        for _ in range(3):
            cards = self.due(viewer)
            self.assertTrue(cards)
            ids.append(cards[0]['id'])
            self.show(viewer, cards[0]['id'])
        self.assertEqual(self.due(viewer), [])                                 # three today
        self.assertEqual(ids, sorted(ids))
        self.clock.t += DAY
        left = self.due(viewer)
        self.assertEqual(len(left), 1)
        self.assertGreater(left[0]['id'], ids[-1])

    def test_blocks_both_ways(self):
        a, b, wid = self.booked()
        x, y, z = self.user('khach'), self.user('ban_be'), self.user('hang_xom')

        def block(sid, target, chat=False):
            with self.store.connect() as db:
                if chat:
                    db.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?)', (social.pid_of(sid), social.pid_of(target), time.time()))
                else:
                    db.execute('INSERT INTO marriage_blocks(sid, target, at) VALUES(?, ?, ?)', (sid, target, time.time()))
        block(self.sid(x), self.sid(a))                     # x blocked the sender
        block(self.sid(b), self.sid(y))                     # the partner blocked y
        block(self.sid(z), self.sid(a), chat=True)          # z blocked the sender in chat
        free = self.user('nguoi_la')
        self.send(a)
        self.assertEqual((self.due(x), self.due(y), self.due(z)), ([], [], []))
        self.assertEqual(len(self.due(free)), 1)

    def test_a_party_card_ends_with_the_party_a_plain_one_after_two_days(self):
        c, d = self.married_plain('co', 'chu')
        a, b, wid = self.booked(at_in=2 * 3600)
        viewer = self.user('khach')
        self.send(a)
        self.send(c)
        self.assertEqual([bool(x.get('party')) for x in self.due(viewer)], [True, False])
        at = float(self.row('SELECT at FROM wedding_parties WHERE wedding=?', wid)['at'])
        self.clock.t = at + wl.PARTY_SECS + 1
        cards = self.due(viewer)
        self.assertEqual([x.get('party') for x in cards], [None])
        self.clock.t += wi.PLAIN_SECS
        self.assertEqual(self.due(viewer), [])

    def test_a_divorce_takes_the_card_down(self):
        c, d = self.married_plain()
        viewer = self.user('khach')
        self.send(c)
        self.act(d, 'divorce', confirm='LY HON')
        self.assertEqual(self.due(viewer), [])

    def test_cheer_once(self):
        a, b, wid = self.booked()
        viewer = self.user('khach')
        self.send(a)
        cid = self.due(viewer)[0]['id']
        self.assertFalse(self.show(self.user('chua_xem'), cid, cheer=False)['cheered'])
        r = self.show(viewer, cid, cheer=True)
        self.assertTrue(r['shown'] and r['cheered'])
        self.assertFalse(self.show(viewer, cid, cheer=True)['cheered'])        # once
        self.assertEqual(wi.me(self.store, a)['sent']['cheers'], 1)
        for bad in (dict(id='1'), dict(id=cid, cheer='yes'), dict(id=0)):
            with self.assertRaises(mr.MarriageError):
                wi.seen(self.store, self.sid(viewer), bad)
        with self.assertRaises(mr.MarriageError) as e:
            self.show(viewer, cid + 999)
        self.assertEqual(e.exception.code, 'gone')

    def test_admin_delete(self):
        a, b, wid = self.booked()
        viewer = self.user('khach')
        self.send(a, text='Mời cả phố ăn cưới, gọi 0912 345 678 nhé')
        items = wi.admin_view(self.store)['items']
        self.assertEqual((len(items), items[0]['username'], items[0]['status']), (1, 'lananh_test', 'live'))
        self.assertIn('0912', items[0]['raw'])
        self.assertTrue(wi.admin_act(self.store, 'boss', dict(act='delete', id=items[0]['id']))['deleted'])
        self.assertEqual(self.due(viewer), [])
        self.assertEqual(wi.admin_view(self.store)['items'][0]['by'], 'boss')
        with self.assertRaises(mr.MarriageError):
            wi.admin_act(self.store, 'boss', dict(act='nuke', id=1))

    def test_forget(self):
        a, b, wid = self.booked()
        viewer = self.user('khach')
        self.send(a)
        self.show(viewer, self.due(viewer)[0]['id'])
        wi.forget(self.store, a)
        wi.forget(self.store, viewer)
        self.assertEqual((self.rows('SELECT * FROM wed_invites'), self.rows('SELECT * FROM wed_invite_seen')), ([], []))

    def test_schema(self):
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 32)
        self.assertIn('wed_invites', pg_schema.TABLE)
        self.assertIn('wed_invite_seen', pg_schema.TABLE)


class OlderServer(InvBase):
    def old_tree(self):
        old = os.environ.get('MNL_OLD_TREE') or str(ROOT.parent / '_rel1920' / 'mot-ngay-lam-nghe')
        if not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no 1.9.20 tree (MNL_OLD_TREE)')
        return old

    def test_the_senders_save_loads_on_the_previous_release(self):
        old = self.old_tree()
        a, b, wid = self.booked()
        self.send(a)
        self.clock.t += DAY + 60
        c, d = self.married_plain()
        self.send(c)
        code = ('import json, sys\n'
                'from game.engine import migrate_state, validate_state\n'
                'for s in json.loads(sys.stdin.read()):\n'
                '    s = migrate_state(s)\n'
                '    validate_state(s)\n'
                "print('ok')\n")
        env = dict(os.environ, PYTHONPATH=old + os.pathsep + os.environ.get('PYTHONPATH', ''))
        r = subprocess.run([sys.executable, '-c', code], cwd=old, input=json.dumps([self.state(a), self.state(b), self.state(c)]),
                           capture_output=True, text=True, encoding='utf-8', env=env)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'ok'), r.stderr[-2000:])


class AdminHTTP(unittest.TestCase):
    """GET/POST /api/admin/wedinvite: ADMIN_USERS only (the HTTP setup of tests/test_admin_gift.py)."""
    _h = _ag.AdminGiftHTTP.__dict__
    setUpClass, tearDownClass, setUp = _h['setUpClass'], _h['tearDownClass'], _h['setUp']
    req, signed_up = _h['req'], _h['signed_up']

    def test_only_admins(self):
        self.assertEqual(self.req(self.player, '/api/admin/wedinvite')[0], 403)
        self.assertEqual(self.req(self.player, '/api/admin/wedinvite', 'POST', dict(act='delete', id=1))[0], 403)
        status, data = self.req(self.admin, '/api/admin/wedinvite')
        self.assertEqual((status, type(data.get('items'))), (200, list), data)
        status, data = self.req(self.player, '/api/wedinvite')
        self.assertEqual((status, data.get('items')), (200, []), data)
        status, data = self.req(self.player, '/api/wedinvite/send', 'POST', dict(text='Mời cả phố đến chung vui nhé!', rid='rid-wi-http-1'))
        self.assertEqual((status, data.get('code')), (409, 'wedinv_refused'), data)   # not engaged: nothing is sent, nothing is paid


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class LiveFrame(LiveCase):
    """live/wedinvite.py: every open page but the couple's and the blocked ones; no text, no pid."""

    def notify(self, event):
        from live.app import NOTIFY_CHANNEL
        with self.store.connect() as db:
            db.execute('SELECT pg_notify(?, ?)', (NOTIFY_CHANNEL, json.dumps(event)))

    async def test_open_pages_are_told(self):
        (ta, sa), (tb, sb), (tc, sc), (td, _sd) = self.account('Lan'), self.account('Minh'), self.account('Hoa'), self.account('Tú')
        with self.store.connect() as db:   # Hoa blocked Minh (the partner)
            db.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?)', (self.pid(sc), self.pid(sb), time.time()))
        a, b, c, d = await self.connect(ta), await self.connect(tb), await self.connect(tc), await self.connect(td)
        self.notify(dict(op='wedinvite', id=5, pids=[self.pid(sa), self.pid(sb)]))
        f = await d.expect('wedinvite')
        self.assertEqual(f, dict(t='wedinvite', id=5))
        await a.nothing('wedinvite', wait=.2)
        await b.nothing('wedinvite', wait=.1)
        await c.nothing('wedinvite', wait=.1)
        for bad in (dict(id='5'), dict(id=5), dict(id=4), dict(id=None)):   # odd ids, a repeat, an older one
            self.notify(dict(dict(op='wedinvite', pids=[]), **bad))
        await d.nothing('wedinvite', wait=.2)


if __name__ == '__main__':
    unittest.main()
