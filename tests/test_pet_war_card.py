"""🛡️ The Bang chiến tuần card every member sees on the bang page (owner, verbatim: "có nơi nào đó cho mọi người ở bang
thấy sự kiện bang chiến cuối tuần đi"; game/pet_war.py team_card through game/bang.py page['war']): when, the lock,
the phase, the lineup and who chose it, what each member may do, the matches and the result; the ⚔️ Bang entry's hours
(me_view mine.war); and the reminder the hour before the lock (remind_due: once a bang a week, only bangs that can
play, nothing outside that hour)."""
import unittest

from game import bang
from game import pet_war as PW
from tests.test_bang_challenge import WED
from tests.test_pet_war_lineup import Help

LOCK = PW.lock_of(WED)
START = PW.start_of(WED)


class Card(Help):
    def setUp(self):
        super().setUp()
        PW._REMIND.clear()
        self.addCleanup(PW._REMIND.clear)

    def card(self, tok):
        return bang.page(self.store, self.sid(tok))['war']

    def test_member_and_leader_before_the_lock(self):
        toks, bid = self.bang(n=6, roles=('chu', 'pho', 'lao', 'tinh', 'tv', 'tv'))
        c = self.card(toks[4])
        self.assertEqual((c['phase'], c['start'], c['lock'], c['size'], c['n']), ('pick', START, LOCK, 5, 0))
        self.assertEqual(PW._clock(START), '20:00')
        self.assertEqual(PW._clock(LOCK), '19:50')
        self.assertIsNone(c['lead'])
        self.assertTrue(c['can_pick'])
        self.assertFalse(c['can_lead'], 'a member does not choose the lineup')
        self.assertTrue(self.card(toks[0])['can_lead'])
        self.assertTrue(self.card(toks[1])['can_lead'], 'Phó bang too')
        self.assertFalse(self.card(toks[2])['can_lead'], 'not a Trưởng lão')
        self.mypick(toks[4])
        self.mypick(toks[5])
        c = self.card(toks[4])
        self.assertEqual(c['n'], 2)
        self.assertEqual(sorted(s['name'] for s in c['slots']), ['Người 5', 'Người 6'])   # same second: by sid
        self.assertEqual({s['name']: s['me'] for s in c['slots']}, {'Người 5': True, 'Người 6': False})
        self.assertTrue(c['mine'])
        self.assertEqual(c['slots'][0]['pet']['n'], 'Mít')
        self.assertIn('pw', c['slots'][0]['pet'])
        self.assertIn('r', c['slots'][0]['pet'])
        self.assertNotIn('sid', repr(c))
        # a leaver's pick no longer shows (as at the lock)
        self.sql("UPDATE bang_members SET status='out' WHERE sid=?", (self.sid(toks[5]),))
        self.assertEqual(self.card(toks[4])['n'], 1)
        # the leaders choose: everybody sees who did, members can no longer pick
        self.lineup(toks[1], toks[:3])
        c = self.card(toks[4])
        self.assertEqual(c['lead'], dict(role='Phó bang'))
        self.assertEqual(c['n'], 3)
        self.assertFalse(c['can_pick'])
        self.assertFalse(c['mine'])
        self.assertTrue(self.card(toks[0])['can_lead'])

    def test_after_the_lock_and_after_the_war(self):
        a, b, ba, bb, chosen = self.two_bangs()
        lone, bc = self.bang(n=2, bid='b00000000c3', name='Hổ Xám', emoji='🐯')   # a bang that fields nobody
        self.t[0] = LOCK + 1
        c = self.card(a[1])
        self.assertEqual(c['phase'], 'locked')
        self.assertFalse(c['can_pick'] or c['can_lead'])
        self.assertEqual(c['n'], 3)
        self.assertEqual(c['lead'], dict(role='Bang chủ'))
        self.assertTrue(PW.run_due(self.store, LOCK + 1))
        self.assertEqual(self.card(a[1])['phase'], 'locked', 'played at the lock, shown from the start')
        self.assertEqual(self.card(a[1])['matches'][0]['state'], 'wait')
        self.t[0] = START + 1
        c = self.card(a[1])
        self.assertEqual(c['phase'], 'live')
        self.assertEqual([(m['state'], m['vs']) for m in c['matches']], [('live', '🐟 Cá Xanh')])
        self.assertIsNone(c['result'])
        self.t[0] = c['end'] + 1
        ca, cb = self.card(a[1]), self.card(b[0])
        self.assertEqual((ca['phase'], cb['phase']), ('done', 'done'))
        self.assertEqual(ca['matches'][0]['state'], 'done')
        self.assertEqual(ca['matches'][0]['round'], 'Chung kết')
        self.assertEqual(ca['matches'][0]['won'], not cb['matches'][0]['won'])
        self.assertEqual(ca['matches'][0]['score'], list(reversed(cb['matches'][0]['score'])))
        win, lose = (ca, cb) if ca['matches'][0]['won'] else (cb, ca)
        self.assertTrue(win['result']['champ'])
        self.assertFalse(lose['result']['champ'])
        self.assertTrue(lose['result']['second'])
        self.assertEqual(lose['result']['champ_name'], win['result']['champ_name'])
        out = self.card(lone[0])
        self.assertEqual(out['phase'], 'done')
        self.assertTrue(out['result']['out'])
        self.assertFalse(out['entered'])

    def test_a_war_without_enough_bangs(self):
        toks, bid = self.bang(n=3)
        self.mypick(toks[1])
        self.assertTrue(PW.run_due(self.store, LOCK + 1))
        self.t[0] = START + 60
        c = self.card(toks[1])
        self.assertEqual(c['phase'], 'cancelled')
        self.assertEqual(c['matches'], [])

    def test_the_entry_knows_the_war_hours(self):
        toks, bid = self.bang(n=1)
        m = bang.me_view(self.store, toks[0])['mine']
        self.assertEqual((m['war']['start'], m['war']['lock']), (START, LOCK))

    def test_reminder_once_a_bang_the_hour_before_the_lock(self):
        a, ba = self.bang(n=2)
        b, bb = self.bang(n=2, bid='b00000000b2', name='Cá Xanh', emoji='🐟')
        c, bc = self.bang(n=1, bid='b00000000c3', name='Hổ Xám', emoji='🐯')
        d, bd = self.bang(n=1, bid='b00000000d4', name='Mèo Mun', emoji='🐈')
        self.sql("UPDATE bangs SET isle=0 WHERE id=?", (bc,))            # no island: cannot play, no reminder
        self.sql('UPDATE bangs SET hidden=1 WHERE id=?', (bd,))         # hidden by an operator
        self.assertEqual(PW.remind_due(self.store, LOCK - PW.REMIND_SECS - 1), 0, 'too early')
        self.assertEqual(PW.remind_due(self.store, LOCK - 1800), 2)
        logs = self.rows("SELECT bang, text FROM bang_log WHERE kind='war_remind' ORDER BY bang")
        self.assertEqual([x['bang'] for x in logs], [ba, bb])
        self.assertIn('Bang chiến 20:00 tối nay, đội hình chốt lúc 19:50', logs[0]['text'])
        chat = self.rows("SELECT channel, name FROM chat_messages WHERE name='🛡️ Bang chiến pet' ORDER BY channel")
        self.assertEqual(len(chat), 2)
        self.assertEqual(PW.remind_due(self.store, LOCK - 1700), 0, 'done this week (this process)')
        PW._REMIND.clear()                                              # another process: the log rows are the marker
        self.assertEqual(PW.remind_due(self.store, LOCK - 1600), 0)
        self.assertEqual(len(self.rows("SELECT 1 FROM bang_log WHERE kind='war_remind'")), 2)
        # batches: the rest the next tick
        PW._REMIND.clear()
        e, be = self.bang(n=1, bid='b00000000e5', name='Gà Trống', emoji='🐓')
        f, bf = self.bang(n=1, bid='b00000000f6', name='Vịt Bầu', emoji='🦆')
        batch = PW.REMIND_BATCH
        PW.REMIND_BATCH = 1
        try:
            self.assertEqual(PW.remind_due(self.store, LOCK - 1500), 1)
            self.assertEqual(PW.remind_due(self.store, LOCK - 1470), 1)
            self.assertEqual(PW.remind_due(self.store, LOCK - 1440), 0)
        finally:
            PW.REMIND_BATCH = batch
        self.assertEqual(len(self.rows("SELECT 1 FROM bang_log WHERE kind='war_remind'")), 4)
        PW._REMIND.clear()
        self.assertEqual(PW.remind_due(self.store, LOCK + 1), 0, 'never after the lock')
        # the card shows it in the bang's story too
        self.assertIn('war_remind', [x['kind'] for x in bang.page(self.store, self.sid(a[0]))['log']])


if __name__ == '__main__':
    unittest.main()
