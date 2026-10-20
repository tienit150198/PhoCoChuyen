"""🚪 Rời bang thì 24 giờ sau mới vào bang khác (owner 21/10), and a Bang chủ disbands without handing over.

Leaving (Rời bang) starts the wait for any OTHER bang: join, ask, an invitation accepted, an officer's approval, founding
(nothing paid when refused). The same bang takes you back at once. A kick or a disband never makes anyone wait. A member of
one bang leaves it before joining another (no more straight switch). MNL_BANG_REJOIN_HOURS=0 turns it off.
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from game import bang
from game.engine import GameError
from tests.test_bang import Base

H = 24 * 3600


class Rejoin(Base):
    def setUp(self):
        super().setUp()
        p = patch.dict(os.environ, {'MNL_BANG_REJOIN_HOURS': '24'})
        p.start()
        self.addCleanup(p.stop)
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)
        self.c = self.player(name='Tú')
        self.other = self.found(self.c, 'Hổ Xám')
        self.b = self.player(name='Minh')
        self.op(self.b, 'join', bang=self.bid)

    def test_a_member_leaves_first_then_waits_48h_for_another_bang(self):
        self.refused_op(self.b, 'join', 'in_other', bang=self.other)          # no straight switch any more
        self.assertEqual(self.mine(self.b)['bang'], self.bid)
        self.op(self.b, 'leave', confirm=True)
        self.refused_op(self.b, 'join', 'rejoin_wait', bang=self.other)
        self.t[0] += H - 60
        self.refused_op(self.b, 'join', 'rejoin_wait', bang=self.other)       # a minute short
        self.t[0] += 61
        self.op(self.b, 'join', bang=self.other)
        self.assertEqual(self.mine(self.b)['bang'], self.other)

    def test_the_same_bang_takes_you_back_at_once(self):
        self.op(self.b, 'leave', confirm=True)
        self.op(self.b, 'join', bang=self.bid)
        self.assertEqual(self.mine(self.b)['bang'], self.bid)

    def test_an_ask_and_an_approval_wait_too(self):
        with self.store.connect() as db:
            db.execute("UPDATE bangs SET rules=?, open=0 WHERE id=?", ('{"mode":"ask"}', self.other))
        bang._VIEW.clear()
        self.op(self.b, 'leave', confirm=True)
        self.refused_op(self.b, 'join', 'rejoin_wait', bang=self.other)       # no ask that could never be approved
        with self.store.connect() as db:                                      # an ask made before (an older build)
            db.execute("INSERT INTO bang_asks(bang, sid, kind, by_sid, status, at) VALUES(?, ?, 'ask', ?, 'open', ?)",
                       (self.other, self.sid(self.b), self.sid(self.b), self.t[0]))
        self.refused_op(self.c, 'approve', 'rejoin_wait', pid=self.pid(self.b), ok=True)
        self.assertIsNone(self.mine(self.b))

    def test_founding_waits_and_pays_nothing(self):
        self.op(self.b, 'leave', confirm=True)
        before = self.wallet(self.b)
        with self.assertRaises(GameError):
            self.found(self.b, 'Mèo Mun')
        self.assertEqual(self.wallet(self.b), before)
        self.assertIsNone(self.mine(self.b))
        self.t[0] += H + 1
        self.found(self.b, 'Mèo Mun')
        self.assertEqual(self.mine(self.b)['role'], 'chu')

    def test_a_kick_never_makes_anyone_wait(self):
        self.op(self.a, 'kick', pid=self.pid(self.b), confirm=True)
        self.op(self.b, 'join', bang=self.other)
        self.assertEqual(self.mine(self.b)['bang'], self.other)

    def test_the_leader_disbands_without_handing_over_and_nobody_waits(self):
        self.refused_op(self.a, 'leave', 'leader', confirm=True)
        self.op(self.a, 'disband', confirm=True, name='Rồng Đỏ')
        self.assertIsNone(self.mine(self.a))
        self.assertIsNone(self.mine(self.b))
        self.op(self.b, 'join', bang=self.other)                              # the members are free at once
        self.assertEqual(self.mine(self.b)['bang'], self.other)
        self.found(self.a, 'Rồng Xanh')                                       # and so is the leader
        self.assertEqual(self.mine(self.a)['role'], 'chu')

    def test_disband_needs_only_a_confirmation(self):
        self.refused_op(self.a, 'disband', 'confirm')                         # a tap alone is not enough
        self.refused_op(self.a, 'disband', 'confirm', confirm=True, name='Hổ Xám')   # an older client: another bang's name
        self.op(self.a, 'disband', confirm=True)                              # the new client: the second tap
        self.assertIsNone(self.mine(self.a))

    def test_an_older_client_name_is_read_loosely(self):
        self.op(self.c, 'disband', confirm=True, name='  hổ xám ')            # case, spaces, diacritics as typed on a phone
        self.assertIsNone(self.mine(self.c))

    def test_name_and_badge_change_twice_each(self):
        self.refused_op(self.b, 'set', 'role', name='Rồng Vàng')              # a member cannot
        self.refused_op(self.a, 'set', 'name_taken', name='hổ xám')          # another active bang's name (any case)
        self.op(self.a, 'set', name='Rồng Vàng', emoji='🦄')
        b = self.one('SELECT name, emoji, channel FROM bangs WHERE id=?', (self.bid,))
        self.assertEqual((b['name'], b['emoji']), ('Rồng Vàng', '🦄'))
        self.assertEqual(self.one('SELECT title FROM chat_channels WHERE id=?', (b['channel'],))['title'], '🦄 Rồng Vàng')
        self.op(self.a, 'set', name='Rồng Bạc', emoji='🐉')                   # the second time each
        self.refused_op(self.a, 'set', 'rename_used', name='Rồng Đồng')        # owner: at most 2
        self.refused_op(self.a, 'set', 'badge_used', emoji='🦁')
        self.op(self.a, 'set', name='Rồng Bạc', emoji='🐉', motto='Vẫn đổi được khẩu hiệu')   # same name/badge: not a change
        self.assertEqual(self.one("SELECT COUNT(*) AS n FROM bang_log WHERE bang=? AND kind='rename'", (self.bid,))['n'], 2)
        self.op(self.c, 'set', name='Rồng Vàng')                             # a freed name is free again

    def test_off_switch(self):
        with patch.dict(os.environ, {'MNL_BANG_REJOIN_HOURS': '0'}):
            self.op(self.b, 'join', bang=self.other)                          # the old free switch
            self.assertEqual(self.mine(self.b)['bang'], self.other)


if __name__ == '__main__':
    unittest.main()
