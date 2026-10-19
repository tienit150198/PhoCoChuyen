"""⚔️ How a bang takes new members (owner 20/10: "chủ bang được quyền tắt, mở hoặc tự động duyệt member vào bang tùy
chọn, hoặc là yêu cầu nghề gì trên xxx thì được … rồi được xem danh sách member, rồi đá khỏi bang"; game/bang.py
rules_of / _op_rules; PostgreSQL with TEST_DATABASE_URL):
* three join modes: 🚫 Đóng (no join, no request; an officer's invitation still opens the door, open requests may still
  be approved), 🔒 Cần duyệt (a request waits for an officer), 🚪 Tự động duyệt (in at once when the requirements hold;
  refused with the reason otherwise);
* optional, combinable requirements checked on the server from the player's real save and account: a career from a
  title of its real promotion ladder, a title step in any career, the account's age; on join, request, invitation and
  approval; members already in are never removed when they change;
* Bang chủ and Phó bang set them, the card in Tìm bang shows them, the member list (role, joined, points this week and
  in total, last active) and who may kick or appoint whom."""
from unittest.mock import patch

from game import bang
from game import bang_content as C
from game import marriage as mr
from game import promotion
from tests.test_bang import Base


class Rules(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)

    def ranked(self, name, rank=1, days=30, career='milk_tea'):
        tok = self.player(name=name, days=days, title=False)
        sid = self.sid(tok)

        def fn(s):
            if rank:
                promotion.record(s, career, True)['rank'] = rank
        mr._mutate(self.store, {sid: fn})
        return tok

    def rules(self, **data):
        return self.op(self.a, 'rules', **data)['done']

    def card(self):
        return next(c for c in bang.search(self.store, None) if c['id'] == self.bid)

    def test_three_modes(self):
        b, c, d = self.ranked('Minh'), self.ranked('Tú'), self.ranked('Dũng')
        self.assertEqual(bang.rules_of(self.one('SELECT * FROM bangs WHERE id=?', (self.bid,)))['mode'], 'auto')   # founded open
        self.op(b, 'join', bang=self.bid)                                         # 🚪 tự động duyệt: in at once
        self.assertEqual(self.mine(b)['bang'], self.bid)
        self.rules(mode='ask')                                                    # 🔒 cần duyệt
        self.assertEqual(self.one('SELECT open FROM bangs WHERE id=?', (self.bid,))['open'], 0)   # `open` in step
        out = self.op(c, 'join', bang=self.bid)['done']
        self.assertEqual(out.get('asked'), self.bid)
        self.assertIsNone(self.mine(c))
        self.rules(mode='closed')                                                 # 🚫 đóng
        self.assertIn('đang đóng', self.refused_op(d, 'join', 'closed_bang', bang=self.bid))
        self.assertEqual(self.card()['mode'], 'closed')
        self.op(self.a, 'approve', pid=self.pid(c))                               # a request already there: still decided
        self.assertEqual(self.mine(c)['bang'], self.bid)
        from game import marriage
        code = marriage.ensure_person(self.store, self.sid(d))['code']
        self.op(self.a, 'invite', code=code)                                      # an invitation opens the door
        self.op(d, 'accept', bang=self.bid)
        self.assertEqual(self.mine(d)['bang'], self.bid)
        self.rules(mode='auto')
        self.assertEqual(self.one('SELECT open FROM bangs WHERE id=?', (self.bid,))['open'], 1)

    def test_career_title_requirement(self):
        self.rules(career='milk_tea', rank=3)
        want = bang.title_name('milk_tea', 3)
        self.assertEqual(want, promotion.title({'journey': {}}, {}, 'milk_tea', 3))   # the game's real ladder
        req = self.card()['req']
        self.assertEqual(len(req), 1)
        self.assertIn(want, req[0])
        self.assertIn('bậc 3', req[0])
        low, high, other = self.ranked('Minh', 2), self.ranked('Tú', 3), self.ranked('Dũng', 4, career='grocery')
        msg = self.refused_op(low, 'join', 'requirements', bang=self.bid)         # auto: refused with the reason
        self.assertIn('chưa đủ yêu cầu', msg)
        self.assertIn(want, msg)
        self.refused_op(other, 'join', 'requirements', bang=self.bid)             # a high title elsewhere is not it
        self.op(high, 'join', bang=self.bid)
        self.assertEqual(self.mine(high)['bang'], self.bid)

    def test_any_career_and_account_age(self):
        self.rules(any=2, days=20)
        self.assertEqual(self.card()['req'], ['Chức danh bậc 2 trở lên ở một nghề bất kỳ', 'Tài khoản từ 20 ngày'])
        young, low, ok = self.ranked('Minh', 4, days=5), self.ranked('Tú', 1), self.ranked('Dũng', 2, career='grocery')
        msg = self.refused_op(young, 'join', 'requirements', bang=self.bid)
        self.assertIn('tài khoản từ 20 ngày', msg)
        self.assertNotIn('chức danh', msg)                                        # only what is missing
        self.refused_op(low, 'join', 'requirements', bang=self.bid)
        self.op(ok, 'join', bang=self.bid)
        self.assertEqual(self.mine(ok)['bang'], self.bid)

    def test_requests_and_approval_check_the_requirements(self):
        self.rules(mode='ask', career='milk_tea', rank=2)
        low, high = self.ranked('Minh', 1), self.ranked('Tú', 2)
        self.refused_op(low, 'join', 'requirements', bang=self.bid)               # no request from someone who cannot
        self.op(high, 'join', bang=self.bid)                                      # a request
        late = self.ranked('Dũng', 2)
        self.op(late, 'join', bang=self.bid)
        self.rules(career='milk_tea', rank=4)                                     # stricter since they asked
        msg = self.refused_op(self.a, 'approve', 'requirements', pid=self.pid(high))
        self.assertTrue(msg.startswith('Người này chưa đủ yêu cầu'), msg)
        self.op(self.a, 'approve', pid=self.pid(late), ok=False)                  # declining needs nothing
        self.rules(career='', rank=0)                                             # cleared
        self.op(self.a, 'approve', pid=self.pid(high))
        self.assertEqual(self.mine(high)['bang'], self.bid)

    def test_an_invitation_still_needs_the_requirements(self):
        self.rules(mode='closed', days=60)
        b = self.ranked('Minh', 1, days=10)
        from game import marriage
        self.op(self.a, 'invite', code=marriage.ensure_person(self.store, self.sid(b))['code'])
        self.assertIn('tài khoản từ 60 ngày', self.refused_op(b, 'accept', 'requirements', bang=self.bid))

    def test_members_stay_when_requirements_change(self):
        b = self.ranked('Minh', 1)
        self.op(b, 'join', bang=self.bid)
        self.rules(career='milk_tea', rank=5, days=300)
        self.assertEqual(self.mine(b)['bang'], self.bid)

    def test_who_sets_them_and_their_checks(self):
        pho, lao = self.ranked('Minh'), self.ranked('Tú')
        for tok in (pho, lao):
            self.op(tok, 'join', bang=self.bid)
        self.op(self.a, 'role', pid=self.pid(pho), role='pho')
        self.op(self.a, 'role', pid=self.pid(lao), role='lao')
        self.assertEqual(self.op(pho, 'rules', mode='ask')['done']['rules']['mode'], 'ask')   # Phó bang: yes
        self.refused_op(lao, 'rules', 'role', mode='auto')                        # Trưởng lão: no
        for bad in (dict(mode='open'), dict(career='nope', rank=1), dict(career='milk_tea', rank=9), dict(any=8),
                    dict(days=-1), dict(days=366), dict(extra=1), {}):
            self.refused_op(self.a, 'rules', None, **bad)
        self.assertEqual(self.op(self.a, 'rules', mode='ask')['done']['message'], 'Không có gì thay đổi.')
        log = self.rows("SELECT text FROM bang_log WHERE bang=? AND kind='set' ORDER BY id", (self.bid,))
        self.assertIn('Cần duyệt', log[-1]['text'])
        # an older page's open switch keeps the requirements
        self.rules(days=10)
        self.op(self.a, 'set', open=True)
        r = bang.rules_of(self.one('SELECT * FROM bangs WHERE id=?', (self.bid,)))
        self.assertEqual((r['mode'], r['days']), ('auto', 10))

    def test_the_save_is_read_only_for_a_bang_with_requirements(self):
        b = self.ranked('Minh')
        seen = []
        real = bang.profile_of
        with patch.object(bang, 'profile_of', lambda db, sid: seen.append(sid) or real(db, sid)):
            self.op(b, 'join', bang=self.bid)
            self.op(b, 'leave', confirm=True)
            self.assertEqual(seen, [])
            self.rules(days=1)
            self.op(b, 'join', bang=self.bid)
        self.assertEqual(seen, [self.sid(b)])
        # the page never sends its own profile
        self.op(b, 'leave', confirm=True)
        self.rules(days=300)
        with self.assertRaises(bang.BangError):
            self.op(b, 'join', bang=self.bid, _who=dict(ranks={'milk_tea': 7}, days=999))

    def test_ladder_for_the_picker(self):
        got = bang.get_view(self.store, self.a, {'careers': '1'})
        by = {c['id']: c for c in got['careers']}
        self.assertEqual(by['teacher']['titles'][4], 'Hiệu trưởng')
        self.assertEqual(len(by['police']['titles']), promotion.top('police'))
        self.assertEqual(set(got['modes']), set(C.JOIN_MODES))


class MemberList(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)
        self.toks = {r: self.player(name=n) for r, n in (('pho', 'Phó'), ('lao', 'Lão'), ('tinh', 'Tinh'), ('tv', 'Thường'))}
        for r, tok in self.toks.items():
            self.op(tok, 'join', bang=self.bid)
            if r != 'tv':
                self.op(self.a, 'role', pid=self.pid(tok), role=r)

    def test_the_list_members_see(self):
        self.give(self.a, 1_000_000)
        p = bang.page(self.store, self.sid(self.toks['tv']))
        rows = {m['name']: m for m in p['members']}
        self.assertEqual(set(rows), {'Lan', 'Phó', 'Lão', 'Tinh', 'Thường'})
        lan = rows['Lan']
        self.assertEqual((lan['role'], lan['week'], lan['earned']), ('chu', 1000, 1000))
        self.assertGreater(lan['joined'], 0)
        self.assertIsNotNone(lan['last'])
        self.assertEqual(lan['last'] % 900, 0)                                    # coarse: a quarter hour
        self.assertEqual([m['role'] for m in p['members']][:4], ['chu', 'pho', 'lao', 'tinh'])
        self.assertIn('rules', p)

    def test_who_kicks_whom(self):
        pho, lao, tinh, tv = (self.toks[r] for r in ('pho', 'lao', 'tinh', 'tv'))
        self.refused_op(lao, 'kick', 'role', pid=self.pid(tv), confirm=True)      # Trưởng lão: nobody
        self.refused_op(pho, 'kick', 'role', pid=self.pid(self.a), confirm=True)   # never a higher rank
        second = self.player(name='Phó Hai')
        self.op(second, 'join', bang=self.bid)
        self.op(self.a, 'role', pid=self.pid(second), role='pho')
        self.refused_op(pho, 'kick', 'role', pid=self.pid(second), confirm=True)  # nor the same rank
        for tok in (lao, tinh, tv):                                               # Phó bang: Trưởng lão and below
            self.op(pho, 'kick', pid=self.pid(tok), confirm=True)
            self.assertIsNone(self.mine(tok))
        self.op(self.a, 'kick', pid=self.pid(pho), confirm=True)                  # Bang chủ: anyone
        self.assertIsNone(self.mine(pho))

    def test_who_appoints(self):
        pho, tv = self.toks['pho'], self.toks['tv']
        self.refused_op(pho, 'role', 'role', pid=self.pid(tv), role='tinh')       # appointing: Bang chủ only
        self.op(self.a, 'role', pid=self.pid(pho), role='tv')                     # demote
        self.assertEqual(self.mine(pho)['role'], 'tv')
        self.op(self.a, 'role', pid=self.pid(tv), role='pho')                     # promote
        self.assertEqual(self.mine(tv)['role'], 'pho')
        third = self.player(name='Ba')
        self.op(third, 'join', bang=self.bid)
        self.op(self.a, 'role', pid=self.pid(pho), role='pho')
        self.refused_op(self.a, 'role', 'seats', pid=self.pid(third), role='pho')  # Phó bang: 2 seats
        self.assertEqual(C.ROLES['pho'][2], 2)
        self.assertEqual((C.ROLES['chu'][2], C.ROLES['lao'][2], C.ROLES['tinh'][2], C.ROLES['tv'][2]), (1, 3, 5, None))
