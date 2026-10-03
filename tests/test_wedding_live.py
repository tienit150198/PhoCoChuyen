"""💍 Live weddings, the game server's side (game/wedding_live.py, game/marriage.py booking, game/live_effects.py kinds):
booking a real date and time, legacy couples' dates, the party cancelled by a divorce, anniversaries paid once, the
reward kinds (title, closeness, the private card), the weekly race view (ties) and the group photo upload."""
import base64
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from game import live_effects as lfx
from game import marriage as mr
from game import push
from game import system_gift as sg
from game import wedding_live as wl
from game.engine import migrate_state, validate_state
from tests.test_marriage import DAY, PLAN, Base

WEBP = 'data:image/webp;base64,' + base64.b64encode(b'RIFF\x24\x00\x00\x00WEBPVP8 ' + b'\x00' * 24).decode()


class WedBase(Base):
    def setUp(self):
        super().setUp()
        p = patch('game.wedding_live.now', self.clock)
        p.start()
        self.addCleanup(p.stop)
        q = patch('game.live_effects.now', self.clock)
        q.start()
        self.addCleanup(q.stop)

    def couple(self, at_in=2 * 3600):
        a, b = self.user('lananh'), self.user('minhtu')
        self.engage(a, b)
        at = self.clock.t + at_in
        wid = self.plan_and_confirm(a, b, plan=dict(PLAN, at=at))
        return a, b, wid, int(at) // 60 * 60

    def pay(self, tok):
        changed = lfx.on_load(self.store, tok, self.state(tok))
        return changed

    def resolve(self, a):
        return mr.on_load(self.store, a, self.state(a))


class Booking(WedBase):
    def test_a_real_date_and_time_is_booked_for_good(self):
        a, b, wid, at = self.couple()
        w = self.row('SELECT * FROM weddings WHERE id=?', wid)
        self.assertEqual((w['status'], w['target_a'], w['target_b'], w['due_at']), ('confirmed', None, None, float(at)))
        party = self.row('SELECT * FROM wedding_parties WHERE wedding=?', wid)
        self.assertEqual((party['status'], party['at']), ('booked', float(at)))
        self.assertEqual(self.row('SELECT at, source FROM wedding_dates')['source'], 'booked')
        label = f'💍 Cưới ngày {wl.fmt_at(at)}'
        self.assertEqual(self.view(a)['couple']['wed_label'], label)
        self.assertEqual(self.view(b)['wedding']['at_label'], wl.fmt_at(at))
        # the ceremony waits for the real time, whatever the life days
        mr._mutate(self.store, {self.sid(a): lambda s: s['journey'].__setitem__('life_day', s['journey']['life_day'] + 30)})
        self.assertFalse(self.resolve(a))
        self.clock.t = at + 1
        self.resolve(a)
        self.assertEqual(self.view(a)['couple']['status'], 'married')
        self.assertEqual(self.view(b)['couple']['wed_label'], label, 'the booked time stays the date, not the resolution time')
        self.assertEqual(len(self.rows('SELECT * FROM wedding_dates')), 1)

    def test_the_phố_is_told_the_date_and_time_when_both_agree(self):
        a, b, wid, at = self.couple()
        n = self.row("SELECT text FROM news WHERE kind='booked'")
        self.assertIn(wl.fmt_at(at), n['text'])                  # e.g. "sẽ cưới lúc 04/10/2026 · 20:30 tại …"
        self.assertIn('Lịch cưới', n['text'])

    def test_no_booked_news_when_one_of_them_keeps_it_quiet(self):
        a, b = self.user('lananh'), self.user('minhtu')
        self.engage(a, b)
        self.plan_and_confirm(a, b, plan=dict(PLAN, at=self.clock.t + 2 * 3600), announce_b=False)
        self.assertIsNone(self.row("SELECT text FROM news WHERE kind='booked'"))

    def test_the_window_and_a_late_confirmation(self):
        a, b = self.user('an'), self.user('binh')
        self.engage(a, b)
        for bad in (self.clock.t + 1800, self.clock.t + 15 * DAY, 'tối nay'):
            with self.assertRaises(mr.MarriageError) as e:
                self.act(a, 'plan', plan=dict(PLAN, at=bad), mine=50, announce=True)
            self.assertEqual(e.exception.code, 'bad_plan')
        self.act(a, 'plan', plan=dict(PLAN, at=self.clock.t + 3700), mine=50, announce=True)
        w = self.view(b)['wedding']
        self.clock.t += 3700 - 600     # 10 minutes before: too late to confirm, nothing is taken
        before = self.wallet(b)
        with self.assertRaises(mr.MarriageError) as e:
            self.act(b, 'confirm', id=w['id'], version=w['version'], announce=True)
        self.assertEqual(e.exception.code, 'too_late')
        self.assertEqual(self.wallet(b), before)
        self.assertIsNone(self.row('SELECT * FROM wedding_parties'))

    def test_older_clients_keep_life_days_and_a_divorce_cancels_the_party(self):
        a, b = self.user('an'), self.user('binh')
        self.engage(a, b)
        wid = self.plan_and_confirm(a, b)          # no `at`: as before
        w = self.row('SELECT * FROM weddings WHERE id=?', wid)
        self.assertIsNotNone(w['target_a'])
        self.assertIsNone(self.row('SELECT * FROM wedding_parties'))
        c, d, wid2, at = self.couple()
        self.act(c, 'divorce', confirm='HUY')
        self.assertEqual(self.row('SELECT status FROM wedding_parties WHERE wedding=?', wid2)['status'], 'cancelled')


class LegacyDates(WedBase):
    def test_legacy_couples_get_their_wedding_time_then_married_at(self):
        a, b = self.user('an'), self.user('binh')
        self.engage(a, b)
        wid = self.plan_and_confirm(a, b)
        self.clock.t += 10 * DAY
        self.resolve(a)
        done_at = self.row('SELECT done_at FROM weddings WHERE id=?', wid)['done_at']
        self.assertIsNone(self.row('SELECT * FROM wedding_dates'))
        self.assertEqual(self.view(a)['couple']['wed_label'], f'💍 Cưới ngày {wl.fmt_at(done_at)}')
        with self.store.connect() as db:
            c = mr._bond(db, self.sid(a))
        self.store.transaction(lambda db: wl.date_of(db, c, write=True))
        r = self.row('SELECT * FROM wedding_dates')
        self.assertEqual((r['source'], r['at']), ('legacy', done_at))
        # nothing else was rewritten
        self.assertEqual(self.row('SELECT married_at FROM couples')['married_at'], c['married_at'])
        # a married couple without a done wedding row: married_at
        self.store.transaction(lambda db: db.execute('DELETE FROM wedding_dates'))
        self.store.transaction(lambda db: db.execute("UPDATE weddings SET status='x' WHERE id=?", (wid,)))
        with self.store.connect() as db:
            self.assertEqual(wl.date_of(db, c), c['married_at'])


class Party(WedBase):
    """🎉 "Tổ chức tiệc cưới" for every couple with a wedding (owner, 01/10): a free date and time for the one 10-minute
    party, which also becomes the date of couples married without one; "Mời khách" is free and once."""
    def married_legacy(self):
        a, b = self.user('an'), self.user('binh')
        self.engage(a, b)
        wid = self.plan_and_confirm(a, b)             # an older plan: life days, no party
        self.clock.t += 10 * DAY
        self.resolve(a)
        return a, b, wid

    def test_a_couple_married_without_a_time_picks_one(self):
        a, b, wid = self.married_legacy()
        self.assertEqual(self.view(a)['couple']['party']['state'], 'none')
        for bad in (self.clock.t + 5 * 60, self.clock.t + 15 * DAY, 'tối nay'):
            with self.assertRaises(mr.MarriageError) as e:
                self.act(a, 'party', at=bad)
            self.assertEqual(e.exception.code, 'bad_plan')
        before = (self.wallet(a), self.wallet(b))
        at = self.clock.t + 20 * 60
        self.act(a, 'party', at=at)
        at = int(at) // 60 * 60
        self.assertEqual((self.wallet(a), self.wallet(b)), before, 'free')
        r = self.row('SELECT * FROM wedding_parties')
        self.assertEqual((r['wedding'], r['status'], r['at']), (wid, 'booked', float(at)))
        self.assertEqual(self.row('SELECT source, at FROM wedding_dates'), dict(source='party', at=float(at)))
        self.assertEqual(self.view(b)['couple']['wed_label'], f'💍 Cưới ngày {wl.fmt_at(at)}')
        self.assertIn('hẹn tiệc cưới', self.view(b)['me']['notice'])
        v = self.view(b)['couple']['party']
        self.assertEqual((v['state'], v['at'], v['can_move'], v['invited']), ('booked', at, True, False))
        self.act(b, 'party', at=at + 3600)                      # moved by the other spouse
        self.assertEqual(self.row('SELECT at FROM wedding_parties')['at'], float(at + 3600))
        self.assertEqual(self.row('SELECT at FROM wedding_dates')['at'], float(at + 3600))
        self.clock.t = at + 3600 - 5 * 60                        # the room is open: too late to move
        self.assertEqual(self.view(a)['couple']['party']['state'], 'live')
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'party', at=self.clock.t + 3600)
        self.assertEqual(e.exception.code, 'too_late')
        self.store.transaction(lambda db: db.execute("UPDATE wedding_parties SET status='done'"))
        self.assertEqual(self.view(a)['couple']['party']['state'], 'done')
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'party', at=self.clock.t + 3600)
        self.assertEqual(e.exception.code, 'done', 'one party per wedding')
        self.assertEqual(len(self.rows('SELECT * FROM wedding_parties')), 1)

    def test_invite_is_free_once_and_reaches_friends_and_the_phố(self):
        a, b, wid = self.married_legacy()
        f = self.user('ban')
        self.befriend(self.sid(a), self.sid(f))
        push.ensure(self.store)
        self.store.transaction(lambda db: db.execute("INSERT INTO push_subs(endpoint, sid, created, prefs) VALUES('https://push.example/9', ?, 1, '{}')", (self.sid(f),)))
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'party_invite')
        self.assertEqual(e.exception.code, 'no_party')
        self.act(a, 'party', at=self.clock.t + 3600)
        before = self.wallet(a)
        out = self.act(b, 'party_invite')
        self.assertIn('Miễn phí', out['message'])
        self.assertEqual(self.wallet(a), before)
        self.assertIn('mời bạn dự tiệc cưới', self.view(f)['me']['notice'])
        self.assertEqual(len(self.rows("SELECT * FROM push_queue WHERE sid=? AND kind='wedding'", self.sid(f))), 1)
        self.assertEqual(len(self.rows("SELECT * FROM news WHERE kind='invite'")), 1)
        self.act(a, 'party_invite')                              # again: nothing more is sent
        self.assertEqual(len(self.rows("SELECT * FROM push_queue WHERE sid=? AND kind='wedding'", self.sid(f))), 1)
        self.assertTrue(self.view(a)['couple']['party']['invited'])

    def test_who_can_hold_one(self):
        a, b = self.user('an'), self.user('binh')
        self.engage(a, b)
        self.assertIsNone(self.view(a)['couple']['party'], 'engaged without a confirmed plan: no wedding yet')
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'party', at=self.clock.t + 3600)
        self.assertEqual(e.exception.code, 'no_wedding')
        wid = self.plan_and_confirm(a, b)                        # confirmed with life days: the party can be set now
        self.act(a, 'party', at=self.clock.t + 3600)
        self.assertEqual(self.row('SELECT wedding FROM wedding_parties')['wedding'], wid)
        c, d, wid2, at = self.couple()                           # booked with the plan: its time is the ceremony's
        v = self.view(c)['couple']['party']
        self.assertEqual((v['state'], v['id'], v['at'], v['can_move']), ('booked', wid2, at, False))
        with self.assertRaises(mr.MarriageError):
            self.act(c, 'party', at=self.clock.t + 3 * 3600)
        self.assertEqual(self.row('SELECT source FROM wedding_dates WHERE wedding=?', wid2)['source'], 'booked')


class Envelopes(WedBase):
    """🧧 A guest's red envelope for the couple at a party that is on (feedback #56): from the guest's wallet, half to
    each spouse, once per request id; one of ENVELOPES each time, as many as the wallet allows (no cap), never minting."""
    def guest_at(self, wid, tok, ok=1):
        self.store.transaction(lambda db: db.execute("INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) "
                                                     "VALUES(?, ?, 'p', ?, 0, 0, ?, 'd', 'w')", (wid, self.sid(tok), ok, self.clock.t)))

    def give(self, tok, wid, amount, rid, wish=0):
        return self.act(tok, 'envelope', wedding=wid, amount=amount, wish=wish, rid=rid)

    def test_from_the_wallet_half_to_each_spouse_once(self):
        a, b, wid, at = self.couple()
        g = self.user('khach', wallet=1000)
        self.guest_at(wid, g)
        with self.assertRaises(mr.MarriageError) as e:
            self.give(g, wid, 50, 'rid-early-0001')
        self.assertEqual(e.exception.code, 'not_open', 'not before the room opens')
        self.clock.t = at - 60
        out = self.give(g, wid, 50, 'rid-first-0001', wish=2)
        self.assertTrue(out['changed'])
        self.assertEqual(out['rid'], 'rid-first-0001')
        self.assertEqual(self.wallet(g), 950)
        rows = self.rows("SELECT sid, amount, data FROM live_effects WHERE id LIKE 'wedenv:%' ORDER BY id")
        self.assertEqual([(r['sid'], r['amount']) for r in rows], [(self.sid(a), 25), (self.sid(b), 25)])
        self.assertEqual(json.loads(rows[0]['data'])['src'], 'env')
        self.assertEqual(json.loads(self.row("SELECT data FROM marriage_effects WHERE id=?", f'wenv:{wid}:rid-first-0001')['data'])['wish'], 2)
        again = self.give(g, wid, 50, 'rid-first-0001')               # a double tap: nothing more moves
        self.assertFalse(again['changed'])
        self.assertEqual(self.wallet(g), 950)
        self.assertEqual(len(self.rows("SELECT * FROM live_effects WHERE id LIKE 'wedenv:%'")), 2)
        before = self.wallet(a)
        self.pay(a)
        self.assertEqual(self.wallet(a), before + 25)
        self.assertIn('Phong bì mừng cưới', json.dumps(self.state(a)['journey'], ensure_ascii=False))
        with self.store.connect() as db:
            self.assertEqual(wl.envelopes_of(db, self.sid(b), wid, 'b'), 25)

    def test_the_rules(self):
        a, b, wid, at = self.couple()
        g, h, poor = self.user('khach'), self.user('lac'), self.user('ngheo', wallet=30)
        self.clock.t = at + 60
        for bad in (dict(amount=15), dict(amount=0), dict(amount=1000), dict(amount=True), dict(amount=50, wish=99), dict(amount='50')):
            with self.assertRaises(mr.MarriageError) as e:
                self.act(g, 'envelope', wedding=wid, **{'wish': 0, **bad})
            self.assertEqual(e.exception.code, 'bad_envelope')
        with self.assertRaises(mr.MarriageError) as e:
            self.give(g, wid, 50, 'rid-notguest-1')
        self.assertEqual(e.exception.code, 'not_guest', 'only a guest recorded at the party')
        self.guest_at(wid, h, ok=0)
        with self.assertRaises(mr.MarriageError) as e:
            self.give(h, wid, 50, 'rid-notok-0001')
        self.assertEqual(e.exception.code, 'not_guest')
        self.guest_at(wid, a)
        with self.assertRaises(mr.MarriageError) as e:
            self.give(a, wid, 50, 'rid-own-00001')
        self.assertEqual(e.exception.code, 'own_wedding')
        self.guest_at(wid, poor)
        with self.assertRaises(mr.MarriageError) as e:
            self.give(poor, wid, 50, 'rid-poor-0001')
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual((self.wallet(poor), len(self.rows("SELECT * FROM live_effects WHERE id LIKE 'wedenv:%'"))), (30, 0))
        self.guest_at(wid, g)
        for i, n in enumerate((200, 200, 100, 10)):              # past the old 500 a wedding
            self.give(g, wid, n, f'rid-max-000{i}')
        self.assertEqual(self.wallet(g), 2000 - 510)
        self.clock.t = at + wl.PARTY_SECS
        with self.assertRaises(mr.MarriageError) as e:
            self.give(poor, wid, 10, 'rid-late-0001')
        self.assertEqual(e.exception.code, 'not_open', 'the party is over')


    def test_no_cap_a_pure_transfer(self):
        """Many envelopes at one wedding until the wallet is empty: the couple gets exactly what left the guest's wallet,
        and an envelope the wallet cannot cover is refused (never below 0)."""
        a, b, wid, at = self.couple()
        g = self.user('khach', wallet=3000)
        self.guest_at(wid, g)
        self.clock.t = at + 60
        wa, wb = self.wallet(a), self.wallet(b)
        for i in range(15):                                         # 15 × 200 = 3000: six times the old cap
            self.give(g, wid, 200, f'rid-many-{i:04d}')
        self.assertEqual(self.wallet(g), 0)
        with self.assertRaises(mr.MarriageError) as e:
            self.give(g, wid, 10, 'rid-zero-0001')
        self.assertEqual(e.exception.code, 'not_enough', 'never below 0')
        self.assertEqual(self.wallet(g), 0)
        rows = self.rows("SELECT amount FROM live_effects WHERE id LIKE 'wedenv:%'")
        self.assertEqual((len(rows), sum(r['amount'] for r in rows)), (30, 3000), 'no xu made, none lost')
        debit = self.row("SELECT COALESCE(SUM(amount), 0) AS n FROM marriage_effects WHERE sid=? AND id LIKE 'wenv:%'", self.sid(g))['n']
        self.assertEqual(debit, -3000)
        while self.pay(a):                                          # paid in batches of live_effects.BATCH rows
            pass
        while self.pay(b):
            pass
        self.assertEqual((self.wallet(a) - wa, self.wallet(b) - wb), (1500, 1500))
        self.assertFalse(self.pay(a), 'each row once')


class WedGift(WedBase):
    """🎁 Quà từ admin: 500 xu once per save ever, while a party is open (owner 03/10)."""
    def test_once_per_save_while_a_party_is_open(self):
        a, b, wid, at = self.couple()
        g = self.user('khach', wallet=100)
        self.assertIs(self.state(g)['journey'].get('wed_gift'), None)
        with self.assertRaises(mr.MarriageError) as e:
            self.act(g, 'wed_gift')
        self.assertEqual(e.exception.code, 'no_party', 'no party open yet')
        self.clock.t = at - wl.OPEN_BEFORE + 1                      # the room is open
        with self.assertRaises(mr.MarriageError) as e:
            self.act(g, 'wed_gift', x=1)
        self.assertEqual(e.exception.code, 'bad_gift')
        out = self.act(g, 'wed_gift')
        self.assertEqual((out['changed'], out['gift']), (True, wl.GIFT_XU))
        self.assertIn('Quà từ admin', out['message'])
        j = self.state(g)['journey']
        self.assertEqual((j['wallet'], j['wed_gift']['v'], j['history'][-1]['kind'], j['history'][-1]['label']),
                         (600, wl.GIFT_VERSION, 'life', wl.GIFT_LABEL))
        validate_state(migrate_state(self.state(g)))
        with self.assertRaises(mr.MarriageError) as e:
            self.act(g, 'wed_gift')
        self.assertEqual(e.exception.code, 'wed_gift_done', 'once per save')
        self.clock.t = at + wl.PARTY_SECS + 3600                    # another wedding later: still once ever
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'wed_gift')
        self.assertEqual(e.exception.code, 'no_party', 'the party is over')
        self.store.transaction(lambda db: db.execute("INSERT INTO wedding_parties(wedding, couple, a, b, at, status, created) "
                                                     "VALUES(?, 99, 'x', 'y', ?, 'booked', ?)", (wid + 100, self.clock.t, self.clock.t)))
        with self.assertRaises(mr.MarriageError) as e:
            self.act(g, 'wed_gift')
        self.assertEqual(e.exception.code, 'wed_gift_done')
        self.assertEqual(self.wallet(g), 600)
        self.assertTrue(self.act(a, 'wed_gift')['changed'], 'everyone gets it once, a bride too')

    def test_public_flag_and_validation(self):
        from game.journey import public
        a, b, wid, at = self.couple()
        self.assertIs(public(migrate_state(self.state(a)))['wed_gift'], False)
        self.clock.t = at
        self.act(a, 'wed_gift')
        s = migrate_state(self.state(a))
        self.assertIs(public(s)['wed_gift'], True)
        for bad in (None, {}, dict(v=2, got=1), dict(v=1, got=0), dict(v=1, got=1, x=1)):
            s['journey']['wed_gift'] = bad
            with self.assertRaises(Exception):
                validate_state(s)

    @unittest.skipUnless(os.environ.get('MNL_OLD_TREE'), 'MNL_OLD_TREE: an older release to load the save with')
    def test_an_older_server_loads_the_save(self):
        """Rolling release: a save with journey['wed_gift'] validates on the older build; its marriage API has no
        wed_gift (not_found, which the client ignores)."""
        a, b, wid, at = self.couple()
        self.clock.t = at
        self.act(a, 'wed_gift')
        code = ('import json, sys\n'
                'from game.engine import migrate_state, validate_state\n'
                'from game import marriage as mr\n'
                's = migrate_state(json.loads(sys.stdin.read()))\n'
                'validate_state(s)\n'
                "print(s['journey']['wed_gift']['v'], 'wed_gift' in mr.ACTIONS)\n")
        old = os.environ['MNL_OLD_TREE']
        r = subprocess.run([sys.executable, '-c', code], cwd=old, input=json.dumps(self.state(a)), capture_output=True,
                           text=True, encoding='utf-8', env=dict(os.environ, PYTHONPATH=old))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, '1 False'), r.stderr[-2000:])


class Anniversaries(WedBase):
    def married(self):
        a, b, wid, at = self.couple()
        self.clock.t = at + 60
        self.resolve(a)
        self.resolve(b)
        return a, b, at

    def test_paid_once_per_milestone_with_the_card_and_title(self):
        a, b, at = self.married()
        self.assertFalse(wl.on_load(self.store, a, self.state(a)))
        self.clock.t = at + 100 * DAY + 60
        w0 = self.wallet(a)
        self.assertTrue(wl.on_load(self.store, a, self.state(a)))
        self.assertFalse(wl.on_load(self.store, b, self.state(b)), 'the other spouse has the same rows already')
        rows = self.rows("SELECT id, kind, amount FROM live_effects WHERE sid=? ORDER BY id", self.sid(a))
        self.assertEqual([r['kind'] for r in rows], ['coins', 'coins', 'title'])
        npc = next(r['amount'] for r in rows if r['id'].endswith(':npc'))
        self.assertTrue(self.pay(a))
        self.assertEqual(self.wallet(a), w0 + 200 + npc)
        s = self.state(a)
        self.assertIn('w_100', s['journey']['titles'])
        validate_state(migrate_state(s))
        changed, cards = sg.on_load(self.store, a, self.state(a))
        self.assertEqual([(g['coins'], g['title']) for g in cards], [(200, '💞 Trăm ngày bên nhau')])
        self.assertFalse(self.pay(a))
        self.assertFalse(wl.on_load(self.store, a, self.state(a)))
        self.assertEqual(self.wallet(a), w0 + 200 + npc)
        news = self.rows("SELECT text FROM news WHERE kind='anniversary'")
        self.assertEqual(len(news), 1)
        self.assertIn('tròn 100 ngày cưới', news[0]['text'])
        # a year later: only the year
        self.clock.t = at + 365 * DAY + 60
        wl.on_load(self.store, a, self.state(a))
        self.pay(a)
        self.assertIn('w_1y', self.state(a)['journey']['titles'])
        self.assertEqual(len(self.rows("SELECT id FROM live_effects WHERE sid=? AND kind='title'", self.sid(a))), 2)

    def test_a_divorce_stops_the_count(self):
        a, b, at = self.married()
        self.act(a, 'divorce', confirm='LY HON')
        self.clock.t = at + 100 * DAY + 60
        self.assertFalse(wl.on_load(self.store, a, self.state(a)))
        self.assertEqual(self.rows('SELECT * FROM live_effects'), [])

    def test_the_1000_days_pays_1500(self):
        a, b, at = self.married()
        self.clock.t = at + 1000 * DAY + 60
        wl.on_load(self.store, a, self.state(a))
        w0 = self.wallet(a)
        for _ in range(3):
            self.pay(a)
        gained = self.wallet(a) - w0
        npc = sum(r['amount'] for r in self.rows("SELECT amount FROM live_effects WHERE sid=? AND id LIKE '%npc'", self.sid(a)))
        self.assertEqual(gained, 200 + 500 + 800 + 1500 + npc)
        self.assertTrue({'w_100', 'w_1y', 'w_500', 'w_1000'} <= set(self.state(a)['journey']['titles']))


class Kinds(WedBase):
    def test_closeness_title_and_card_rows_are_applied_once(self):
        a, b = self.user('an'), self.user('binh')
        sa, sb = self.sid(a), self.sid(b)
        self.store.transaction(lambda db: (wl.grant(db, sa, 'closeness', 2, 'wedc:1:x:a', {'with': sb}),
                                           wl.grant(db, sa, 'closeness', 2, 'wedc:2:x:a', {'with': sb}),
                                           wl.grant(db, sa, 'title', 1, 'wedhost:1:a:w_crowd', dict(title='w_crowd')),
                                           wl.grant(db, sa, 'title', 1, 'bad:1', dict(title='st_local')),
                                           wl.grant(db, sa, 'coins', 1100, 'wedhost:1:a', dict(src='host', popup=dict(title='💍', text='25 khách')))))
        w0 = self.wallet(a)
        self.pay(a)
        self.pay(a)
        with self.store.connect() as db:
            self.assertEqual(wl.close_points(db, sa, sb), 4)
        s = self.state(a)
        self.assertIn('w_crowd', s['journey']['titles'])
        self.assertNotIn('st_local', s['journey']['titles'], 'only the wedding titles come this way')
        self.assertEqual(self.row("SELECT status FROM live_effects WHERE id='bad:1'")['status'], 'pending')
        self.assertEqual(self.wallet(a), w0 + 1100)
        hist = [r for r in s['journey']['history'] if r['label'] == lfx.LABELS['host']]
        self.assertEqual(len(hist), 1)
        self.assertEqual(len(self.rows("SELECT * FROM system_gifts WHERE sid=? AND status='applied'", sa)), 1)
        # friends see the closeness on the card
        self.befriend(sa, sb)
        from game import friends as fr
        with self.store.connect() as db:
            card = fr._card(db, sa, sb)
        self.assertEqual(card['close'], 4)


class Race(WedBase):
    def guest(self, wid, sid, at, ok=1, steps=2):
        week = wl.vn_week(at)
        self.store.transaction(lambda db: db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,?,1,?,?,?,?)',
                                                     (wid, sid, 'p' + sid[:15], ok, steps, at, wl.vn_day(at), week)))

    def test_most_weddings_first_and_ties_to_whoever_got_there_first(self):
        a, b, c = self.user('an'), self.user('binh'), self.user('chi')
        sa, sb, sc = self.sid(a), self.sid(b), self.sid(c)
        t = wl.week_start(self.clock.t) + 3600
        self.clock.t = t + 5 * 3600
        for i, (sid, dt) in enumerate([(sa, 10), (sa, 400), (sb, 20), (sb, 300), (sc, 30)]):
            self.guest(100 + i, sid, t + dt)
        self.guest(200, sc, t + 40, ok=0)          # not a counted guest
        self.guest(201, sc, t + 50, steps=1)       # stayed 1 minute: not "đi ăn cưới" (2 minutes, owner)
        v = wl.race_view(self.store, sc)
        self.assertEqual([(r['name'], r['n']) for r in v['top']], [('Binh', 2), ('An', 2), ('Chi', 1)])
        self.assertTrue(v['top'][2]['me'])
        self.assertEqual([p['xu'] for p in v['prizes']], [300, 150, 150])


class WeekScript(WedBase):
    def test_settles_last_week_once(self):
        import os
        import subprocess
        import sys
        import time
        from pathlib import Path
        if self.store.pg:
            self.skipTest('the script is run against SQLite here')
        a, b = self.user('an'), self.user('binh')
        prev = wl.week_start(time.time()) - 7 * DAY + 3600
        for i, tok in enumerate((a, b, a)):
            sid = self.sid(tok)
            self.store.transaction(lambda db, sid=sid, i=i: db.execute(
                'INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,1,1,2,?,?,?)',
                (10 + i, sid, 'p' + sid[:15], prev + i, 'd', wl.vn_week(prev))))
        env = {k: v for k, v in os.environ.items() if k != 'DATABASE_URL'}
        root = Path(__file__).resolve().parents[1]
        run = lambda *x: subprocess.run([sys.executable, str(root / 'scripts' / 'wedding_week.py'), '--db', str(self.store.path), *x],
                                         capture_output=True, text=True, env=env, timeout=60)
        dry = run('--dry-run')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn('not settled yet', dry.stdout)
        self.assertEqual(self.rows('SELECT * FROM live_effects'), [])
        for _ in range(2):
            out = run()
            self.assertEqual(out.returncode, 0, out.stderr)
        coins = self.rows("SELECT sid, amount FROM live_effects WHERE kind='coins' ORDER BY amount DESC")
        self.assertEqual([(c['sid'], c['amount']) for c in coins], [(self.sid(a), 300), (self.sid(b), 150)])
        self.assertEqual(len(self.rows('SELECT * FROM wedding_race')), 1)


class Schema(unittest.TestCase):
    def test_version_and_tables(self):
        from game import pg_schema
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 8)   # 8: the wedding tables (7 went to dates in 1.0.1)
        names = {t['name'] for t in pg_schema.TABLES}
        for t in ('wedding_dates', 'wedding_parties', 'wedding_guests', 'wedding_photos', 'wedding_race', 'player_closeness'):
            self.assertIn(t, names)
            self.assertIn(f'CREATE TABLE IF NOT EXISTS {t} ', pg_schema.TABLES_DDL)
            self.assertIn(f'CREATE TABLE IF NOT EXISTS {t} ', wl.SCHEMA)


class Photos(WedBase):
    def test_upload_once_by_the_taker(self):
        a, b, wid, at = self.couple()
        g = self.user('khach')
        self.store.transaction(lambda db: db.execute('INSERT INTO wedding_photos(wedding, n, sid, at) VALUES(?, 1, ?, ?)', (wid, self.sid(g), self.clock.t)))
        with self.assertRaises(wl.WeddingError):
            wl.save_photo(self.store, self.sid(a), dict(wedding=wid, n=1, image=WEBP))     # not the taker
        with self.assertRaises(wl.WeddingError):
            wl.save_photo(self.store, self.sid(g), dict(wedding=wid, n=1, image='data:image/png;base64,AAAA'))
        self.assertEqual(wl.save_photo(self.store, self.sid(g), dict(wedding=wid, n=1, image=WEBP)), dict(ok=True))
        with self.assertRaises(wl.WeddingError) as e:
            wl.save_photo(self.store, self.sid(g), dict(wedding=wid, n=1, image=WEBP))
        self.assertEqual(e.exception.code, 'gone')
        self.assertEqual([p['n'] for p in wl.photos(self.store, self.sid(b))], [1])
        self.assertEqual(wl.photos(self.store, self.sid(g)), [], 'only the couple sees them')


if __name__ == '__main__':
    unittest.main()
