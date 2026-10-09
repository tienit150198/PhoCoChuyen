"""Persistent house invitations remain read-only and bound to a current home."""
import concurrent.futures
import copy
import json
import importlib.util
import threading
import uuid
from unittest.mock import patch

from game import marriage as mr, housing as hs, social
from tests.test_marriage import Base
from tests.test_housing import buy


class HomeGuests(Base):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('game.home_guests'), 'Persistent home invitations are not implemented')
        from game import home_guests
        self.hg = home_guests
        self.a, self.b, self.c = [self.user(n, 10000) for n in ('host', 'guest', 'stranger')]
        self.codes = {t: self.code(t) for t in (self.a, self.b, self.c)}
        self.befriend(self.sid(self.a), self.sid(self.b))
        mr._mutate(self.store, {self.sid(self.a): lambda s: s.update(buy(s, 'tap_the')[0])})

    def post(self, token, sub, **data):
        return self.hg.post(self.store, token, self.state(token), sub, data)

    def listing(self, token):
        return self.hg.get(self.store, token, self.state(token), '', {})

    def invite(self, kind='stay'):
        return self.post(self.a, 'invite', code=self.codes[self.b], kind=kind)['outgoing'][0]['id']

    def accept(self, kind='stay'):
        ident = self.invite(kind)
        self.post(self.b, 'answer', id=ident, answer='accept')
        return ident

    def view_home(self, token):
        return self.hg.get(self.store, token, self.state(token), 'view', {'code': self.codes[self.a]})

    def test_stay_is_offline_persistent_read_only_and_private(self):
        before = [self.store.read(t)[:2] for t in (self.a, self.b)]
        self.accept()
        self.clock.t += 100 * 86400
        out = self.view_home(self.b)
        self.assertEqual(out['access'], {'code': self.codes[self.a], 'kind': 'stay'})
        self.assertEqual(set(out), {'owner', 'deco', 'reno', 'mate', 'colors', 'access', 'live'})
        self.assertEqual(set(out['deco']), {'place', 'rooms', 'more', 'items'})
        self.assertFalse(out['deco']['place']['repairs'])
        self.assertNotIn(self.sid(self.a), json.dumps(out))
        self.assertNotIn(self.sid(self.b), json.dumps(self.listing(self.b)))
        self.assertEqual([self.store.read(t)[:2] for t in (self.a, self.b)], before)
        self.assertEqual(len(self.listing(self.b)['homes']), 1)
        out['deco']['rooms'].clear()
        self.assertTrue(self.view_home(self.b)['deco']['rooms'])

    def test_visit_expires_two_hours_after_acceptance(self):
        ident = self.invite('visit')
        self.clock.t += 500
        self.post(self.b, 'answer', id=ident, answer='accept')
        row = self.listing(self.b)['active'][0]
        self.assertEqual(row['expires_at'], self.clock.t + 7200)
        self.clock.t += 7199
        self.view_home(self.b)
        self.clock.t += 1
        with self.assertRaises(mr.MarriageError):
            self.view_home(self.b)
        self.assertEqual(self.listing(self.b)['homes'], [])

    def test_only_homeowner_and_current_friend_can_invite(self):
        for token, code in ((self.b, self.codes[self.a]), (self.a, self.codes[self.c])):
            with self.assertRaises(mr.MarriageError):
                self.post(token, 'invite', code=code, kind='stay')
        with self.assertRaises(mr.MarriageError):
            self.post(self.a, 'invite', code=self.codes[self.b], kind='forever')

    def test_accept_decline_revoke_leave_require_correct_actor(self):
        ident = self.invite()
        for token, op, data in ((self.a, 'answer', {'answer': 'accept'}),
                                (self.c, 'answer', {'answer': 'accept'}), (self.b, 'revoke', {})):
            with self.assertRaises(mr.MarriageError):
                self.post(token, op, id=ident, **data)
        self.post(self.b, 'answer', id=ident, answer='decline')
        with self.assertRaises(mr.MarriageError):
            self.post(self.b, 'answer', id=ident, answer='accept')
        ident = self.accept()
        self.post(self.b, 'leave', id=ident)
        with self.assertRaises(mr.MarriageError):
            self.view_home(self.b)
        ident = self.accept()
        self.post(self.a, 'revoke', id=ident)
        self.assertEqual(self.listing(self.b)['homes'], [])

    def test_duplicate_invites_and_concurrent_answers(self):
        ident = self.invite()
        with self.assertRaises(mr.MarriageError):
            self.invite('visit')
        def answer():
            try:
                self.post(self.b, 'answer', id=ident, answer='accept')
                return True
            except mr.MarriageError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(lambda _: answer(), range(2))), [False, True])

    def test_concurrent_invites_create_one_active_permission(self):
        def invite():
            try:
                self.invite()
                return True
            except mr.MarriageError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(lambda _: invite(), range(2))), [False, True])
        self.assertEqual(len(self.listing(self.a)['outgoing']), 1)

    def test_home_change_unfriend_and_both_blocks_remove_access(self):
        self.accept()
        owner, guest = self.sid(self.a), self.sid(self.b)
        for table, fields, args in (
            ('marriage_blocks', 'sid,target,at', (guest, owner, self.clock.t)),
            ('blocks', 'pid,target,at', (social.pid_of(owner), social.pid_of(guest), self.clock.t))):
            with self.store.connect() as db:
                db.execute(f'INSERT INTO {table}({fields}) VALUES(?,?,?)', args)
            with self.assertRaises(mr.MarriageError):
                self.view_home(self.b)
            with self.store.connect() as db:
                db.execute(f'DELETE FROM {table}')
            self.assertEqual(self.listing(self.b)['homes'], [])
            self.accept()
        with self.store.connect() as db:
            db.execute('DELETE FROM friends WHERE sid=? AND friend=?', (owner, guest))
        with self.assertRaises(mr.MarriageError):
            self.view_home(self.b)
        self.befriend(owner, guest)
        self.assertEqual(self.listing(self.b)['homes'], [])
        self.accept()
        with self.store.connect() as db:
            saved = json.loads(db.execute('SELECT state FROM sessions WHERE sid=?', (owner,)).fetchone()['state'])
            saved['journey']['home']['own']['id'] = 'h999'
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(saved), owner))
        with self.assertRaises(mr.MarriageError):
            self.view_home(self.b)

    def test_forget_removes_all_permissions(self):
        self.accept()
        with self.store.connect() as db:
            self.hg.forget(db, self.sid(self.b))
        self.assertEqual(self.listing(self.b)['homes'], [])

    def test_pure_access_projection_does_not_mutate_input(self):
        self.accept()
        with self.store.connect() as db:
            row = dict(db.execute(self.hg.ACCESS_SQL, (self.sid(self.b), self.codes[self.a])).fetchone())
        before = copy.deepcopy(row)
        access = self.hg.access_from_row(row, self.clock.t)
        self.assertEqual(access['kind'], 'stay')
        self.assertEqual(row, before)
        row['home_kind'] = 'biet_thu'
        self.assertIsNone(self.hg.access_from_row(row, self.clock.t))

    def command(self, token, action, **payload):
        return self.store.command(token, str(uuid.uuid4()), self.store.read(token)[1], None, action, payload)

    def test_real_import_revokes_identical_house_in_cas_and_locked_store(self):
        for tries in (4, 0):
            with self.subTest(tries=tries), patch('game.storage.OPTIMISTIC_TRIES', tries):
                ident = self.accept()
                saved = copy.deepcopy(self.state(self.a))
                self.command(self.a, 'import_save', save={'format': 'mot-ngay-lam-nghe/save-v1', 'state': saved})
                with self.store.connect() as db:
                    self.assertIsNone(db.execute('SELECT id FROM home_guest_invites WHERE id=?', (ident,)).fetchone())
                self.assertEqual(self.listing(self.b)['homes'], [])

    def test_real_move_back_does_not_restore_old_permission(self):
        self.command(self.a, 'jr_home_buy', kind='can_ho_mini', down=hs.HOMES['can_ho_mini']['price'], confirm=True, move_in=False)
        for tries in (4, 0):
            with self.subTest(tries=tries), patch('game.storage.OPTIMISTIC_TRIES', tries):
                old = self.state(self.a)['journey']['home']['own']['id']
                new = self.state(self.a)['journey']['home']['props'][-1]['id']
                ident = self.accept()
                self.command(self.a, 'jr_home_move', id=new, confirm=True)
                self.command(self.a, 'jr_home_move', id=old, confirm=True)
                with self.store.connect() as db:
                    self.assertEqual(db.execute('SELECT status FROM home_guest_invites WHERE id=?', (ident,)).fetchone()['status'], 'revoked')
                self.assertEqual(self.listing(self.b)['homes'], [])

    def test_real_sale_revokes_permission_in_both_store_paths(self):
        for tries in (4, 0):
            with self.subTest(tries=tries), patch('game.storage.OPTIMISTIC_TRIES', tries):
                ident = self.accept()
                state = self.state(self.a)
                value = hs.value_of(state['journey']['home']['own'], state['journey']['life_day'])
                self.command(self.a, 'jr_home_sell', confirm=True, value=value)
                with self.store.connect() as db:
                    self.assertEqual(db.execute('SELECT status FROM home_guest_invites WHERE id=?', (ident,)).fetchone()['status'], 'revoked')
                self.assertEqual(self.listing(self.b)['homes'], [])
                self.command(self.a, 'jr_home_buy', kind='tap_the', down=hs.HOMES['tap_the']['price'], confirm=True)

    def test_unfriend_then_befriend_cannot_restore_permission(self):
        from game import friends
        ident = self.accept()
        friends.unfriend(self.store, self.sid(self.a), 'Host', {'code': self.codes[self.b]})
        self.befriend(self.sid(self.a), self.sid(self.b))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM home_guest_invites WHERE id=?', (ident,)).fetchone()['status'], 'revoked')
        self.assertEqual(self.listing(self.b)['homes'], [])

    def test_invite_and_block_are_serialized_by_the_same_pair_lock(self):
        from game import friends
        entered, release = threading.Event(), threading.Event()
        original = self.hg._own
        def pause_owner(state):
            if threading.current_thread().name.startswith('invite-race') and not entered.is_set():
                entered.set()
                self.assertTrue(release.wait(8))
            return original(state)
        with patch.object(self.hg, '_own', pause_owner), concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix='invite-race') as pool:
            invitation = pool.submit(self.invite)
            self.assertTrue(entered.wait(8))
            blocked = pool.submit(friends.block, self.store, self.sid(self.b), 'Guest', {'code': self.codes[self.a]})
            release.set()
            ident = invitation.result(timeout=10)
            blocked.result(timeout=10)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM home_guest_invites WHERE id=?', (ident,)).fetchone()['status'], 'revoked')

    def test_only_placed_furniture_colors_are_projected(self):
        from tests.test_deco import place_new, into_bag
        pieces = {}
        def decorate(s):
            placed, result = place_new(s, 'sofa', 'living', 0, 1)
            pieces['visible'] = result['uid']
            placed, pieces['hidden'] = into_bag(placed, 'ban_tra')
            s.update(placed)
        mr._mutate(self.store, {self.sid(self.a): decorate})
        self.accept()
        out = self.view_home(self.b)
        self.assertEqual(set(out['colors']['deco']), {pieces['visible']})
        self.assertNotIn(pieces['hidden'], {p['id'] for p in out['deco']['items']})

    def test_owner_and_current_married_resident_can_view_without_invite(self):
        self.assertEqual(self.view_home(self.a)['access']['kind'], 'owner')
        with self.store.connect() as db:
            row = dict(db.execute(self.hg.ACCESS_SQL, (self.sid(self.b), self.codes[self.a])).fetchone())
        owner, guest = json.loads(row['owner_state']), json.loads(row['guest_state'])
        couple = 99
        for s in (owner, guest):
            s['marriage'] = {'spouse': {'status': 'married', 'couple': couple}}
        own = owner['journey']['home']['own']
        guest['journey']['home'] = dict(own=None, shared=None, rent=None)
        guest['journey']['home']['shared'] = dict(couple=couple, id=own['id'], kind=own['kind'])
        row.update(owner_state=owner, guest_state=guest, couple_id=couple, couple_status='married', friends_ok=False)
        self.assertEqual(self.hg.access_from_row(row, self.clock.t)['kind'], 'spouse')
        row['couple_status'] = 'divorced'
        self.assertIsNone(self.hg.access_from_row(row, self.clock.t))

    def incomplete_spouse_row(self):
        """A stored shared-home claim with only the homeowner's current bond."""
        owner, guest = self.state(self.a), self.state(self.b)
        own = owner['journey']['home']['own']
        with self.store.connect() as db:
            cid = db.execute("INSERT INTO couples(a,b,status,since) VALUES(?,?,'married',?) RETURNING id",
                             (self.sid(self.a), self.sid(self.b), self.clock.t)).fetchone()[0]
            db.execute('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', (self.sid(self.a), cid))
            for state, name, side in ((owner, 'Guest', 'a'), (guest, 'Host', 'b')):
                state['marriage'] = mr.blank()
                state['marriage']['spouse'] = dict(name=name, status='married', since=1, wed=1,
                                                   date='2026-10-04', couple=cid, side=side)
            guest['journey']['home'] = hs.initial(guest['journey']['life_day'])
            guest['journey']['home']['shared'] = dict(couple=cid, id=own['id'], kind=own['kind'], name='Host', since=1)
            for token, state in ((self.a, owner), (self.b, guest)):
                db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(state), self.sid(token)))
        return cid

    def access_row(self):
        with self.store.connect() as db:
            return dict(db.execute(self.hg.ACCESS_SQL, (self.sid(self.b), self.codes[self.a])).fetchone())

    def test_explicit_spouse_entry_requires_both_current_bonds(self):
        cid = self.incomplete_spouse_row()
        self.assertIsNone(self.hg.access_from_row(self.access_row(), self.clock.t))
        with self.store.connect() as db:
            db.execute('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', (self.sid(self.b), cid))
        self.assertEqual(self.hg.access_from_row(self.access_row(), self.clock.t)['kind'], 'spouse')

    def test_missing_spouse_bond_does_not_remove_accepted_friend_access(self):
        self.accept('stay')
        self.incomplete_spouse_row()
        self.assertEqual(self.hg.access_from_row(self.access_row(), self.clock.t)['kind'], 'stay')


    # 🏰 F 09/10 ("biệt thự đà lạt chưa cho người mời vào ở chung được"): a villa bought in Mua sắm (game/estates.py,
    # journey.lux) that its owner lives in is a home they own: invite to visit or to stay, the guest sees its rooms on
    # every floor, and moving out of it, selling it or a save import ends the permission.

    def villa(self, token=None, eid='bt_vuon_da_lat'):
        token = token or self.a
        mr._mutate(self.store, {self.sid(token): lambda s: s['journey'].update(wallet=s['journey']['wallet'] + 3_000_000)})
        self.command(token, 'jr_lux_buy', id=eid, confirm=True)
        self.command(token, 'jr_lux_live', id=eid)
        from game import deco as dc
        pl = dc.place(self.state(token)['journey'])
        self.assertEqual((pl['where'], pl['kind']), ('estate', eid))
        return pl['key']

    def status(self, ident):
        with self.store.connect() as db:
            return db.execute('SELECT status FROM home_guest_invites WHERE id=?', (ident,)).fetchone()['status']

    def test_villa_owner_without_a_house_invites_to_stay_and_visit(self):
        from game import estates as es
        owner, other = self.c, self.a          # 'stranger' owns no house at all: only the villa
        self.befriend(self.sid(owner), self.sid(self.b))
        self.befriend(self.sid(owner), self.sid(other))
        key = self.villa(owner)
        own = self.listing(owner)['own_home']
        self.assertEqual(own['home'], dict(id=key, kind=VILLA, name=es.ESTATE[VILLA]['name'], emoji='🌲'))
        stay = self.post(owner, 'invite', code=self.codes[self.b], kind='stay')['outgoing'][0]['id']
        self.post(self.b, 'answer', id=stay, answer='accept')
        visit = next(i['id'] for i in self.post(owner, 'invite', code=self.codes[other], kind='visit')['outgoing'])
        self.post(other, 'answer', id=visit, answer='accept')
        home = self.listing(self.b)['homes'][0]
        self.assertEqual((home['kind'], home['home']['name']), ('stay', 'Biệt thự vườn Đà Lạt'))
        for token, kind in ((self.b, 'stay'), (other, 'visit'), (owner, 'owner')):
            out = self.hg.get(self.store, token, self.state(token), 'view', {'code': self.codes[owner]})
            self.assertEqual(out['access']['kind'], kind)
            place = out['deco']['place']
            self.assertEqual((place['key'], place['where'], place['kind'], place['emoji']), (key, 'estate', VILLA, '🌲'))
            self.assertFalse(place['repairs'])
            self.assertIsNone(out['reno'])
            floors = {r['id']: r.get('fl') for r in out['deco']['rooms']}
            self.assertEqual(floors['living'], 1)
            self.assertEqual(floors['bed'], 2)   # the second floor reaches the guest too
            self.assertEqual({m.get('fl') for m in out['deco']['more']}, {2})
            self.assertNotIn(self.sid(owner), json.dumps(out))
        self.clock.t += 7201
        with self.assertRaises(mr.MarriageError):
            self.hg.get(self.store, other, self.state(other), 'view', {'code': self.codes[owner]})

    def test_moving_out_selling_or_moving_back_ends_villa_permission(self):
        self.villa()
        ident = self.accept()
        self.assertEqual(self.view_home(self.b)['deco']['place']['where'], 'estate')
        self.command(self.a, 'jr_lux_live', id=None)   # back to the tập thể: the villa invite ends at once
        self.assertEqual(self.status(ident), 'revoked')
        with self.assertRaises(mr.MarriageError):
            self.view_home(self.b)
        ident = self.accept()                           # the tập thể again: an invitation for it, not for the villa
        self.assertEqual(self.view_home(self.b)['deco']['place']['where'], 'own')
        self.command(self.a, 'jr_lux_live', id=VILLA)
        self.assertEqual(self.status(ident), 'revoked')
        ident = self.accept()
        self.command(self.a, 'jr_lux_sell', id=VILLA, confirm=True)
        self.assertEqual(self.status(ident), 'revoked')
        self.assertEqual(self.listing(self.b)['homes'], [])
        self.assertEqual(self.view_home(self.a)['deco']['place']['where'], 'own')

    def test_villa_bought_again_is_a_new_home(self):
        key = self.villa()
        ident = self.accept()
        row = self.access_row()
        self.assertEqual((row['home_id'], row['home_kind']), (key, VILLA))
        self.assertEqual(self.hg.access_from_row(row, self.clock.t)['home_id'], key)
        row = dict(row, home_id=key.rsplit(':', 1)[0] + ':999')   # the same villa bought on another day
        self.assertIsNone(self.hg.access_from_row(row, self.clock.t))
        owner = json.loads(self.access_row()['owner_state'])
        owner['journey']['lux']['live'] = None
        self.assertIsNone(self.hg.access_from_row(dict(self.access_row(), owner_state=owner), self.clock.t))
        self.assertEqual(self.status(ident), 'accepted')

    def test_villa_import_forgets_permission(self):
        self.villa()
        ident = self.accept()
        saved = copy.deepcopy(self.state(self.a))
        self.command(self.a, 'import_save', save={'format': 'mot-ngay-lam-nghe/save-v1', 'state': saved})
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT id FROM home_guest_invites WHERE id=?', (ident,)).fetchone())

    def test_spouse_is_not_let_into_a_villa_without_an_invitation(self):
        self.villa()
        cid = self.incomplete_spouse_row()   # the spouse lives in the tập thể the owner left for the villa
        with self.store.connect() as db:
            db.execute('INSERT INTO marriage_bonds(sid,couple) VALUES(?,?)', (self.sid(self.b), cid))
        self.assertIsNone(self.hg.access_from_row(self.access_row(), self.clock.t))
        self.accept('stay')                 # spouses are friends: an invitation to stay lets them in
        self.assertEqual(self.hg.access_from_row(self.access_row(), self.clock.t)['kind'], 'stay')

    def test_song_hong_three_floors_still_open_to_a_housemate(self):
        # regression: Biệt thự Sông Hồng is a house (game/housing.py) with its ':v2' three-floor inside
        price = hs.HOMES['biet_thu_song']['price']
        mr._mutate(self.store, {self.sid(self.a): lambda s: s['journey'].update(wallet=s['journey']['wallet'] + 2 * price)})
        self.command(self.a, 'jr_home_buy', kind='biet_thu_song', down=price, confirm=True, move_in=True)
        own = self.state(self.a)['journey']['home']['own']
        self.assertEqual(own['kind'], 'biet_thu_song')
        self.accept()
        row = self.access_row()
        self.assertEqual((row['home_id'], row['home_kind']), (own['id'], 'biet_thu_song'))
        out = self.view_home(self.b)
        self.assertTrue(out['deco']['place']['key'].endswith(':biet_thu_song:v2'))
        self.assertEqual(out['deco']['place']['where'], 'own')
        self.assertGreater(max(r.get('fl') or 1 for r in out['deco']['rooms']), 1)
        self.assertIsNotNone(out['reno'])
        self.assertEqual(self.listing(self.b)['homes'][0]['home']['name'], hs.HOMES['biet_thu_song']['name'])

    def test_home_names_never_fail_on_an_unknown_kind(self):
        self.assertEqual(self.hg._home(dict(id='estate:gone:3', kind='gone'))['name'], 'Nhà')
        self.assertEqual(self.hg._home(dict(id='h1', kind='tap_the'))['name'], 'Căn tập thể cũ')
        self.assertEqual(self.hg._home(dict(id='estate:bt_kinh:3', kind='bt_kinh'))['emoji'], '🏙️')


VILLA = 'bt_vuon_da_lat'
