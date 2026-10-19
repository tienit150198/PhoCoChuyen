"""⚔️ Thách đấu bang (game/bang_challenge.py, owner 21/10 "đấu trường pets chỉ mở cho các bang hội đánh nhau thôi, thêm
hoạt động đó vào cho các bang hội nhé"): the standing roster (one pet a member, officers arrange the order, the first
five ready start), challenge → accept / decline / cancel / expire, the limits, exactly one match under concurrency
(two officers, accept against cancel), the rewards (the week's 👑 points, the challenge Elo, capped điểm cống hiến,
never xu, never a save write), and the replay."""
import json
import threading
import unittest
from unittest import mock

from game import bang
from game import bang_challenge as TC
from game import bang_pets
from game import pet_arena as A
from game import pet_tiers as px
from game import pet_war as PW
from tests.test_lb_titles import at
from tests.test_pet_arena import Store

WED = at(2026, 10, 21, 14)


class Base(Store):
    def setUp(self):
        super().setUp()
        A.BANG_ONLY = True
        bang_pets.install()
        self.addCleanup(bang_pets.install)
        bang._VIEW.clear()
        self.addCleanup(bang._VIEW.clear)
        TC._CACHE.clear()
        self.addCleanup(TC._CACHE.clear)
        self.t = [WED]
        for target in (A, bang):
            p = mock.patch.object(target, 'now', lambda: self.t[0])
            p.start()
            self.addCleanup(p.stop)
        self.rid = 0

    def mkbang(self, bid, name, toks, roles=('chu',), emoji='🐉', hidden=0, status='active'):
        sids = [self.sid(t) for t in toks]

        def run(db):
            db.execute('INSERT INTO bangs(id, name, key, emoji, color, leader, status, hidden, created, created_by, channel) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?,?)', (bid, name, bid, emoji, 'do', sids[0], status, hidden, WED - 86400, sids[0], 'g:' + bid[-6:]))
            for i, s in enumerate(sids):
                db.execute("INSERT INTO bang_members(bang, sid, pid, status, role, joined) VALUES(?,?,?,'in',?,?)",
                           (bid, s, bang.pid_of(s), roles[i] if i < len(roles) else 'tv', WED - 86400))
        self.store.transaction(run)
        return bid

    def two(self, na=5, nb=5, ranks=(3, 3), roles_a=('chu', 'lao'), roles_b=('chu', 'lao'), reg=True):
        a = [self.arena(('Mít',), rank=ranks[0]) for _ in range(na)]
        b = [self.arena(('Na',), rank=ranks[1]) for _ in range(nb)]
        ba = self.mkbang('b00000000a1', 'Rồng Đỏ', a, roles_a)
        bb = self.mkbang('b00000000b2', 'Cá Xanh', b, roles_b, emoji='🐟') if b else None
        if reg:
            for t in a + b:
                self.reg(t)
        return a, b, ba, bb

    def tc(self, tok, op, **data):
        state = self.store.read(tok)[0] if op not in A.LIGHT else None
        return A.act(self.store, tok, op, data, state, '1.1.1.1')

    def reg(self, tok, i=0):
        return self.tc(tok, 'tc_reg', pet=px.all_pets(self.store.read(tok)[0])[i]['id'])

    def send(self, tok, target, rid=None):
        self.rid += 1
        return self.tc(tok, 'tc_send', bang=target, rid=rid or f'rid-{self.rid:06d}')

    def refused(self, code, fn, *args, **kw):
        with self.assertRaises(A.ArenaError) as cm:
            fn(*args, **kw)
        self.assertEqual(cm.exception.code, code, str(cm.exception))
        return cm.exception

    def rows(self, sql, args=()):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]

    def sql(self, q, args=()):
        self.store.transaction(lambda db: db.execute(q, args))


class Roster(Base):
    def test_register_change_and_leave_the_roster(self):
        a, b, ba, _ = self.two(na=2, nb=0, reg=False)
        outsider = self.arena(('Bơ',))
        self.assertIn('đội hình thách đấu', self.reg(a[1])['message'])
        self.reg(a[0])
        v = self.tc(a[0], 'tc')
        self.assertEqual([x['me'] for x in v['roster']], [False, True], 'a new entry goes to the end')
        self.assertTrue(all(x['start'] for x in v['roster']))
        self.refused('no_bang', self.reg, outsider)
        # changing the pet keeps the place
        tok = self.arena(('Mít', 'Na'))
        self.sql("INSERT INTO bang_members(bang, sid, pid, status, role, joined) VALUES(?,?,?,'in','tv',?)", (ba, self.sid(tok), bang.pid_of(self.sid(tok)), WED))
        self.reg(tok, 0)
        self.reg(tok, 1)
        r = self.rows('SELECT pet, pos FROM bang_chal_roster WHERE sid=?', (self.sid(tok),))[0]
        self.assertEqual(r['pet'], px.all_pets(self.store.read(tok)[0])[1]['id'])
        self.assertEqual(r['pos'], 3)
        self.assertIn('Đã rút', self.tc(tok, 'tc_unreg')['message'])
        self.refused('none', self.tc, tok, 'tc_unreg')
        # a leaver's row stays but no longer counts
        self.sql("UPDATE bang_members SET status='out' WHERE sid=?", (self.sid(a[1]),))
        self.assertEqual(len(self.tc(a[0], 'tc')['roster']), 1)
        self.assertEqual(len(self.rows('SELECT * FROM bang_chal_roster WHERE bang=?', (ba,))), 2)

    def test_officers_arrange_the_order_and_the_first_five_ready_start(self):
        toks = [self.arena(('Mít',), rank=r) for r in (1, 2, 3, 4, 5, 6, 2)]
        bid = self.mkbang('b00000000c1', 'Hổ Xám', toks, ('chu', 'pho', 'lao', 'tinh'))
        for t in toks:
            self.reg(t)
        v = self.tc(toks[0], 'tc')
        self.assertEqual([x['start'] for x in v['roster']], [True] * 5 + [False] * 2)
        pids = [x['pid'] for x in v['roster']]
        new = list(reversed(pids))
        for who, ok in ((toks[3], False), (toks[6], False), (toks[2], True)):   # Tinh anh, Thành viên: no; Trưởng lão: yes
            if ok:
                self.assertIn('xếp lại', self.tc(who, 'tc_order', order=new)['message'])
            else:
                self.refused('role', self.tc, who, 'tc_order', order=new)
        v = self.tc(toks[0], 'tc')
        self.assertEqual([x['pid'] for x in v['roster']], new)
        starters = {x['pid'] for x in v['roster'] if x['start']}
        self.assertEqual(starters, set(new[:5]))
        # a partial order: listed first, the rest keep their order after
        self.tc(toks[1], 'tc_order', order=[pids[3]])
        self.assertEqual([x['pid'] for x in self.tc(toks[0], 'tc')['roster']], [pids[3]] + [p for p in new if p != pids[3]])
        self.refused('bad_order', self.tc, toks[0], 'tc_order', order=['x'])
        # a starter whose pet is gone (sold, at the grandparents'): the next substitute steps in, back when the pet is
        first = self.tc(toks[0], 'tc')['roster']
        gone_sid = next(t for t in toks if bang.pid_of(self.sid(t)) == first[0]['pid'])
        st = self.store.read(gone_sid)[0]
        empty = json.loads(json.dumps(st))
        empty['journey']['pets']['list'] = []
        self.store.transaction(lambda db: TC.on_pet_commit(db, self.sid(gone_sid), empty))
        v = self.tc(toks[0], 'tc')
        self.assertFalse(v['roster'][0]['ok'])
        self.assertFalse(v['roster'][0]['start'])
        self.assertEqual(sum(x['start'] for x in v['roster']), 5, 'a substitute steps in')
        self.store.transaction(lambda db: TC.on_pet_commit(db, self.sid(gone_sid), st))
        self.assertTrue(self.tc(toks[0], 'tc')['roster'][0]['start'])
        with self.store.connect() as db:
            self.assertEqual(TC.power_of(TC._roster(db, bid)), sum(x['pet']['pw'] for x in self.tc(toks[0], 'tc')['roster'] if x['start']))

    def test_the_snapshot_follows_a_pet_command(self):
        a, _, ba, _ = self.two(na=1, nb=0)
        before = self.rows('SELECT snap FROM bang_chal_roster WHERE bang=?', (ba,))[0]['snap']
        st = self.store.read(a[0])[0]
        p = px.all_pets(st)[0]
        st['journey']['petx']['t'][p['id']]['r'] = 5
        self.store.transaction(lambda db: TC.on_pet_commit(db, self.sid(a[0]), st))
        after = self.rows('SELECT snap, pw FROM bang_chal_roster WHERE bang=?', (ba,))[0]
        self.assertNotEqual(before, after['snap'])
        self.assertEqual(json.loads(after['snap'])['r'], 5)
        # through the real hook (game/pet_arena.py on_pet_commit, called by every jr_pet_* command)
        self.store.transaction(lambda db: A.on_pet_commit(db, self.sid(a[0]), self.store.read(a[0])[0]))
        self.assertEqual(json.loads(self.rows('SELECT snap FROM bang_chal_roster WHERE bang=?', (ba,))[0]['snap'])['r'], 3)


class Flow(Base):
    def test_send_accept_play_watch_and_rewards(self):
        a, b, ba, bb = self.two(ranks=(4, 3))
        self.sql("INSERT INTO bang_facilities(bang, fac, level) VALUES(?, 'san_pet', 3)", (ba,))
        saves = {t: self.store.read(t) for t in a + b}
        self.refused('role', self.send, a[2], bb)                  # a Thành viên does not send
        out = self.send(a[1], bb)                                   # a Trưởng lão does
        self.assertEqual(out['chal']['status'], 'open')
        cid = out['chal']['id']
        chat = self.rows("SELECT * FROM chat_messages WHERE channel=?", ('g:' + bb[-6:],))
        self.assertEqual(len(chat), 1)
        self.assertIn('thách đấu bang mình', chat[0]['text'])
        self.assertEqual((chat[0]['pid'], chat[0]['adm']), ('admin', 1))
        vb = self.tc(b[0], 'tc')
        self.assertEqual([x['id'] for x in vb['incoming']], [cid])
        self.assertEqual(vb['incoming'][0]['foe']['ready'], 5)
        self.assertEqual([x['id'] for x in self.tc(a[0], 'tc')['outgoing']], [cid])
        with self.store.connect() as db:
            me = bang.me_view(self.store, b[1])
        self.assertEqual(me['mine']['tc_in'], 1)
        self.assertNotIn('tc_in', bang.me_view(self.store, b[3])['mine'], 'a Thành viên has nothing to answer')
        self.refused('role', self.tc, b[2], 'tc_answer', id=cid, ok=True)
        self.refused('not_yours', self.tc, a[0], 'tc_answer', id=cid, ok=True)
        res = self.tc(b[1], 'tc_answer', id=cid, ok=True)
        self.assertEqual(res['match'], cid)
        row = self.rows('SELECT * FROM bang_chal WHERE id=?', (cid,))[0]
        self.assertEqual(row['status'], 'done')
        self.assertEqual(row['wa'] + row['wb'] + sum(1 for d in json.loads(row['data'])['duels'] if d['w'] == 2), 5)
        data = json.loads(row['data'])
        self.assertEqual(data['tb'], [3, 0], 'Sân luyện pet +1 %/level as in the war')
        self.assertEqual(data['n'], [5, 5])
        # the replay: five duels, each the same fight again
        m = self.tc(b[4], 'tc_match', id=cid)
        self.assertEqual(m['total'], 5)
        self.assertEqual(m['me'], 1)
        for d in m['duels']:
            self.assertTrue(d['ev'])
            self.assertEqual(d['ev'][-1]['w'], d['w'])
        self.assertEqual(self.tc(self.arena(), 'tc_match', id=cid)['me'], None, 'anyone may watch')
        # rewards: Elo both ways, the week's points, the winners' điểm cống hiến; no save written (no xu, pets as they were)
        win = row['win']
        self.assertIn(win, (0, 1))
        winners, losers, wbid, lbid = (a, b, ba, bb) if win == 0 else (b, a, bb, ba)
        teams = {r['bang']: r for r in self.rows('SELECT * FROM bang_chal_team')}
        self.assertEqual((teams[wbid]['w'], teams[wbid]['l'], teams[lbid]['w'], teams[lbid]['l']), (1, 0, 0, 1))
        self.assertGreater(teams[wbid]['rating'], A.START)
        self.assertLess(teams[lbid]['rating'], A.START)
        self.assertEqual(teams[wbid]['rating'] - A.START, A.START - teams[lbid]['rating'])
        with self.store.connect() as db:
            st = {x['bang']: x for x in bang.standings(db, A.vn_week(WED))}
        from game import bang_content as BC
        self.assertEqual((st[wbid]['chal'], st[lbid]['chal']), (BC.CHAL_WIN, 0), 'a win: 🐾 Pets points')
        for bid, chal in ((wbid, BC.CHAL_WIN), (lbid, 0)):
            self.assertEqual(st[bid]['pets'], chal + st[bid]['power'] // BC.POWER_DIV)
        self.assertEqual(row['sa' if win == 0 else 'sb'], BC.CHAL_WIN)
        pts = self.rows("SELECT sid, pts FROM bang_points WHERE kind='chal'")
        self.assertEqual(sorted(r['sid'] for r in pts), sorted(self.sid(t) for t in winners))
        self.assertTrue(all(r['pts'] == TC.PTS_WIN for r in pts))
        for t in winners:
            self.assertEqual(self.rows('SELECT points FROM bang_members WHERE sid=?', (self.sid(t),))[0]['points'], TC.PTS_WIN)
        for t in a + b:
            self.assertEqual(self.store.read(t), saves[t], 'never a save write')
        # both bangs told in their chat group and log; the page's card and the members' week column
        for bid in (ba, bb):
            self.assertTrue(any('Thách đấu:' in r['text'] for r in self.rows('SELECT text FROM chat_messages WHERE channel=?', ('g:' + bid[-6:],))))
            self.assertTrue(self.rows("SELECT 1 FROM bang_log WHERE bang=? AND kind='chal'", (bid,)))
        page = bang.page(self.store, self.sid(winners[0]))
        self.assertEqual(page['chal']['recent'][0]['res'], 'win')
        self.assertEqual(page['chal']['w'], 1)
        me = next(x for x in page['members'] if x['pid'] == bang.pid_of(self.sid(winners[0])))
        self.assertEqual(me['week'], TC.PTS_WIN)
        # a second answer (another officer, a retry) finds it played: the same match, nothing more
        again = self.tc(b[0], 'tc_answer', id=cid, ok=True)
        self.assertTrue(again['again'])
        self.assertEqual(again['match'], cid)
        self.assertEqual(len(self.rows("SELECT * FROM bang_points WHERE kind='chal'")), len(pts))
        self.refused('gone', self.tc, b[0], 'tc_answer', id=cid, ok=False)
        self.refused('gone', self.tc, a[0], 'tc_cancel', id=cid)

    def test_decline_cancel_and_expire(self):
        a, b, ba, bb = self.two()
        cid = self.send(a[0], bb)['chal']['id']
        self.assertIn('từ chối', self.tc(b[0], 'tc_answer', id=cid, ok=False)['message'])
        self.assertEqual(self.rows('SELECT status FROM bang_chal WHERE id=?', (cid,))[0]['status'], 'declined')
        self.refused('gone', self.tc, b[0], 'tc_answer', id=cid, ok=True)
        cid = self.send(a[0], bb)['chal']['id']
        self.refused('not_yours', self.tc, b[0], 'tc_cancel', id=cid)
        self.assertIn('hủy', self.tc(a[1], 'tc_cancel', id=cid)['message'])
        self.refused('gone', self.tc, b[0], 'tc_answer', id=cid, ok=True)
        # the pair cap counts open and played challenges only: two more can be sent (declined/cancelled do not count)
        cid = self.send(b[0], ba)['chal']['id']
        self.t[0] += TC.WINDOW + 1
        self.refused('gone', self.tc, a[0], 'tc_answer', id=cid, ok=True)
        self.assertEqual(self.tc(a[0], 'tc')['incoming'], [])
        self.assertEqual(TC.run_due(self.store), 1)
        self.assertEqual(self.rows('SELECT status FROM bang_chal WHERE id=?', (cid,))[0]['status'], 'expired')
        self.assertEqual(TC.run_due(self.store), 0)
        self.assertEqual(self.rows('SELECT COUNT(*) AS n FROM bang_points')[0]['n'], 0, 'nothing played, nothing earned')

    def test_auto_accept_plays_at_once_and_off_refuses(self):
        a, b, ba, bb = self.two()
        self.refused('role', self.tc, b[1], 'tc_set', mode='auto')      # Trưởng lão: no; Phó bang and up: yes
        self.assertIn('Tự nhận', self.tc(b[0], 'tc_set', mode='auto')['message'])
        out = self.send(a[0], bb)
        self.assertEqual(out['chal']['status'], 'done')
        self.assertEqual(out['match'], out['chal']['id'])
        self.assertEqual(self.rows('SELECT auto, ans_sid FROM bang_chal')[0], dict(auto=1, ans_sid=''))
        self.tc(b[0], 'tc_set', mode='off')
        self.refused('closed', self.send, a[0], bb)
        found = {c['id']: c for c in self.tc(a[0], 'tc_find')['list']}
        self.assertEqual(found[bb]['why'], 'Không nhận thách đấu')

    def test_idempotent_request_id(self):
        a, b, ba, bb = self.two()
        one = self.send(a[0], bb, rid='same-request-1')
        two = self.send(a[1], bb, rid='same-request-1')
        self.assertEqual(one['chal']['id'], two['chal']['id'])
        self.assertTrue(two['again'])
        self.assertEqual(len(self.rows('SELECT * FROM bang_chal')), 1)


class Limits(Base):
    def test_rosters_modes_and_targets(self):
        a, b, ba, bb = self.two(na=5, nb=2)
        self.refused('their_roster', self.send, a[0], bb)
        self.refused('self', self.send, a[0], ba)
        self.refused('bad_bang', self.send, a[0], 'nope')
        self.refused('not_found', self.send, a[0], 'b00000000ff')
        c = [self.arena(('Bơ',)) for _ in range(3)]
        bc = self.mkbang('b00000000c3', 'Mèo Mun', c, ('chu',), emoji='🐱')
        for t in c:
            self.reg(t)
        self.refused('roster', self.send, b[0], bc)                  # my own roster has 2
        found = {x['id']: x for x in self.tc(a[0], 'tc_find')['list']}
        self.assertEqual(found[bb]['why'], f'Chưa đủ {TC.MIN_FIELD} bé')
        self.assertEqual(found[bc]['why'], '')
        self.assertEqual(found[bc]['ready'], 3)
        self.assertNotIn(ba, found)
        self.assertEqual([x['id'] for x in self.tc(a[0], 'tc_find', q='meo')['list']], [bc])
        # a hidden bang: never listed, never challenged; its open challenges cancelled
        cid = self.send(a[0], bc)['chal']['id']
        bang.admin_act(self.store, 'admin', dict(op='hide', id=bc))
        TC._CACHE.clear()
        self.assertEqual(self.rows('SELECT status FROM bang_chal WHERE id=?', (cid,))[0]['status'], 'cancelled')
        self.assertNotIn(bc, {x['id'] for x in self.tc(a[0], 'tc_find')['list']})
        self.refused('not_found', self.send, a[0], bc)
        self.assertIsNone(self.tc(c[0], 'tc')['mine'], 'a hidden bang is nobody\'s bang here')

    def test_daily_caps(self):
        groups = [[self.arena(('Mít',)) for _ in range(3)] for _ in range(8)]
        ids = [self.mkbang(f'b0000000{i:03d}', f'Bang {i}', g, ('chu', 'pho', 'lao')) for i, g in enumerate(groups)]
        for g in groups:
            for t in g:
                self.reg(t)
        me, mine = groups[0], ids[0]
        # pair: at most PAIR_DAY (open or played) a day between two bangs; one open at a time between them
        c1 = self.send(me[0], ids[1])['chal']['id']
        self.refused('pending', self.send, me[0], ids[1])
        self.refused('pending', self.send, groups[1][0], mine)
        self.tc(groups[1][0], 'tc_answer', id=c1, ok=True)
        c2 = self.send(groups[1][0], mine)['chal']['id']
        self.tc(me[0], 'tc_answer', id=c2, ok=True)
        self.refused('pair_limit', self.send, me[0], ids[1])
        # played: PLAY_DAY a day (sent or received)
        for i in (2, 3, 4):
            cid = self.send(me[0], ids[i])['chal']['id']
            self.tc(groups[i][0], 'tc_answer', id=cid, ok=True)
        self.assertEqual(self.tc(me[0], 'tc')['mine']['today']['played'], TC.PLAY_DAY)
        self.refused('play_limit', self.send, me[0], ids[5])
        self.refused('their_limit', self.send, groups[5][0], mine)
        found = {x['id']: x for x in self.tc(groups[5][0], 'tc_find')['list']}
        TC._CACHE.clear()
        found = {x['id']: x for x in self.tc(groups[5][0], 'tc_find')['list']}
        self.assertEqual(found[mine]['why'], 'Đã đấu đủ hôm nay')
        # sent: SEND_DAY a day (whatever became of them)
        for i in (6, 7):
            cid = self.send(groups[5][0], ids[i])['chal']['id']
            self.tc(groups[5][1], 'tc_cancel', id=cid)
        for i in (6, 7, 6):
            cid = self.send(groups[5][0], ids[i])['chal']['id']
            self.tc(groups[i][0], 'tc_answer', id=cid, ok=False)
        self.refused('send_limit', self.send, groups[5][0], ids[7])
        # the fighters' điểm cống hiến: at most PTS_DAY_N times a day each
        n = {r['sid']: r['n'] for r in self.rows("SELECT sid, COUNT(*) AS n FROM bang_points WHERE kind='chal' GROUP BY sid")}
        self.assertTrue(all(v <= TC.PTS_DAY_N for v in n.values()), n)
        self.assertTrue(all(r['p'] <= TC.PTS_WIN * TC.PTS_DAY_N for r in self.rows("SELECT SUM(pts) AS p FROM bang_points WHERE kind='chal' GROUP BY sid")))
        # tomorrow: everything opens again
        self.t[0] += 86400
        TC._CACHE.clear()
        self.assertEqual(self.send(me[0], ids[1])['chal']['status'], 'open')

    def test_open_challenges_waiting_for_one_bang(self):
        groups = [[self.arena(('Mít',)) for _ in range(3)] for _ in range(TC.OPEN_IN + 2)]
        ids = [self.mkbang(f'b0000001{i:03d}', f'Bang {i}', g, ('chu',)) for i, g in enumerate(groups)]
        for g in groups:
            for t in g:
                self.reg(t)
        for i in range(1, TC.OPEN_IN + 1):
            self.send(groups[i][0], ids[0])
        self.refused('busy', self.send, groups[TC.OPEN_IN + 1][0], ids[0])
        self.assertEqual(len(self.tc(groups[0][0], 'tc')['incoming']), TC.OPEN_IN)

    def test_disband_cancels_open_challenges(self):
        a, b, ba, bb = self.two()
        cid = self.send(a[0], bb)['chal']['id']
        self.store.transaction(lambda db: bang._disband(db, bang._lock(db, bb)[bb], self.sid(b[0]), self.t[0], 'test'))
        self.assertEqual(self.rows('SELECT status FROM bang_chal WHERE id=?', (cid,))[0]['status'], 'cancelled')
        self.assertIsNone(self.tc(b[0], 'tc')['mine'])

    def test_missing_slots_lose_and_no_points_against_a_short_team(self):
        a, b, ba, bb = self.two(na=5, nb=3)
        cid = self.send(a[0], bb)['chal']['id']
        self.sql("UPDATE bang_members SET status='out' WHERE sid=?", (self.sid(b[2]),))
        self.refused('roster', self.tc, b[0], 'tc_answer', id=cid, ok=True)   # the accepting bang needs MIN_FIELD
        self.sql("UPDATE bang_members SET status='in' WHERE sid=?", (self.sid(b[2]),))
        self.tc(b[0], 'tc_answer', id=cid, ok=True)
        duels = json.loads(self.rows('SELECT data FROM bang_chal WHERE id=?', (cid,))[0]['data'])['duels']
        self.assertEqual(sum(1 for d in duels if d['b'] is None), 2)
        self.assertTrue(all(d['w'] == 0 for d in duels if d['b'] is None), 'a missing pet loses its duel')
        # the challenger has one pet left at the answer: it loses, and beating a team of one earns nothing
        cid = self.send(b[0], ba)['chal']['id']
        self.sql("UPDATE bang_members SET status='out' WHERE sid IN (?,?)", tuple(self.sid(t) for t in b[1:]))
        before = len(self.rows("SELECT * FROM bang_points WHERE kind='chal'"))
        self.tc(a[0], 'tc_answer', id=cid, ok=True)
        row = self.rows('SELECT * FROM bang_chal WHERE id=?', (cid,))[0]
        self.assertEqual(json.loads(row['data'])['n'], [1, 5])
        self.assertEqual(row['win'], 1)
        self.assertEqual(len(self.rows("SELECT * FROM bang_points WHERE kind='chal'")), before, 'no điểm cống hiến for beating a team of one')
        self.assertTrue(self.rows("SELECT 1 FROM bang_chal_team WHERE bang=? AND w>=1", (ba,)), 'the record and the Elo still move')


class Race(Base):
    def go(self, *fns):
        errors, outs, gate = [], [], threading.Barrier(len(fns))

        def run(fn):
            try:
                gate.wait(10)
                outs.append(fn())
            except Exception as e:  # noqa: BLE001
                errors.append(e)
        th = [threading.Thread(target=run, args=(f,)) for f in fns]
        for x in th:
            x.start()
        for x in th:
            x.join(30)
        return outs, errors

    def test_two_officers_accept_at_once_one_match(self):
        for _ in range(3):
            a, b, ba, bb = self.two(roles_b=('chu', 'pho', 'lao'))
            cid = self.send(a[0], bb)['chal']['id']
            outs, errors = self.go(*(lambda t=t: self.tc(t, 'tc_answer', id=cid, ok=True) for t in b[:3]))
            self.assertEqual(errors, [])
            self.assertEqual(sorted(o['again'] for o in outs), [False, True, True])
            self.assertEqual({o['match'] for o in outs}, {cid})
            row = self.rows('SELECT * FROM bang_chal WHERE id=?', (cid,))[0]
            self.assertEqual(row['status'], 'done')
            teams = self.rows('SELECT w + l + d AS n FROM bang_chal_team')
            self.assertEqual([r['n'] for r in teams], [1, 1], 'the record moved once')
            winners = 5 if row['win'] in (0, 1) else 10
            self.assertEqual(len(self.rows("SELECT * FROM bang_points WHERE kind='chal'")), winners)
            self.store.transaction(lambda db: [db.execute(f'DELETE FROM {x}') for x in (
                'bang_chal', 'bang_chal_team', 'bang_chal_roster', 'bang_points', 'bang_members', 'bangs', 'bang_log', 'chat_messages')])

    def test_accept_against_cancel(self):
        seen = set()
        for _ in range(4):
            a, b, ba, bb = self.two()
            cid = self.send(a[0], bb)['chal']['id']
            outs, errors = self.go(lambda: self.tc(b[0], 'tc_answer', id=cid, ok=True), lambda: self.tc(a[0], 'tc_cancel', id=cid))
            self.assertEqual(len(outs) + len(errors), 2)
            self.assertEqual(len(errors), 1, errors)
            self.assertEqual(errors[0].code, 'gone')
            row = self.rows('SELECT * FROM bang_chal WHERE id=?', (cid,))[0]
            seen.add(row['status'])
            played = len(self.rows("SELECT * FROM bang_points WHERE kind='chal'"))
            self.assertEqual(played > 0, row['status'] == 'done')
            self.store.transaction(lambda db: [db.execute(f'DELETE FROM {x}') for x in (
                'bang_chal', 'bang_chal_team', 'bang_chal_roster', 'bang_points', 'bang_members', 'bangs', 'bang_log', 'chat_messages')])
        self.assertTrue(seen <= {'done', 'cancelled'}, seen)

    def test_two_bangs_challenge_each_other_at_once(self):
        a, b, ba, bb = self.two()
        outs, errors = self.go(lambda: self.send(a[0], bb), lambda: self.send(b[0], ba))
        self.assertEqual(len(outs), 1)
        self.assertEqual([e.code for e in errors], ['pending'])
        self.assertEqual(len(self.rows("SELECT * FROM bang_chal WHERE status='open'")), 1)


class Gates(Base):
    def test_off_switch_and_lists(self):
        a, b, ba, bb = self.two()
        with mock.patch.dict('os.environ', {'MNL_BANG_CHAL_OFF': '1'}):
            self.refused('off', self.tc, a[0], 'tc')
            self.assertIsNone(bang.page(self.store, self.sid(a[0]))['chal'])
        self.assertEqual(TC.LIGHT, frozenset(x for x in A.LIGHT if x.startswith('tc')))
        self.assertTrue(set(TC.OPS) <= set(A.OPS))
        r = TC.rules()
        self.assertEqual((r['size'], r['min'], r['window'], r['send_day'], r['play_day'], r['pair_day']), (5, 3, 1800, 5, 5, 2))

    def test_town_feed_and_erasure(self):
        a, b, ba, bb = self.two()
        cid = self.send(a[0], bb)['chal']['id']
        self.tc(b[0], 'tc_answer', id=cid, ok=True)
        self.assertEqual([x['id'] for x in self.tc(self.arena(), 'tc')['town']], [cid])
        self.store.transaction(lambda db: A.forget(db, self.sid(a[0])))
        self.assertEqual(self.rows('SELECT * FROM bang_chal_roster WHERE sid=?', (self.sid(a[0]),)), [])
        self.assertEqual(self.rows('SELECT by_sid FROM bang_chal WHERE id=?', (cid,))[0]['by_sid'], '')
        self.assertNotIn(self.sid(a[0]), self.rows('SELECT data FROM bang_chal WHERE id=?', (cid,))[0]['data'], 'duels keep names and pids only')


class Island(Base):
    """Owner 21/10 "phải có mua đảo bang thì mới chơi được": sending, accepting and being listed need the bang's island
    (game/bang.py has_island from the island branch; without it every bang may)."""

    def test_has_island_gate(self):
        a, b, ba, bb = self.two()
        with self.store.connect() as db:
            self.assertTrue(TC.has_island(db, ba), 'a bang from before 21/10 holds cấp 1 (the column default)')
        self.sql('UPDATE bangs SET isle=0 WHERE id=?', (ba,))       # the real column: not bought
        e = self.refused('no_island', self.send, a[0], bb)
        self.assertEqual(str(e), TC.NO_ISLAND)
        self.refused('their_island', self.send, b[0], ba)
        self.sql('UPDATE bangs SET isle=1 WHERE id=?', (ba,))
        owns = {ba: True, bb: True}
        with mock.patch.object(bang, 'has_island', lambda db, bid: owns[bid], create=True):
            owns[ba] = False
            e = self.refused('no_island', self.send, a[0], bb)
            self.assertEqual(str(e), 'Bang cần mua Đảo bang để thách đấu.')
            TC._CACHE.clear()
            self.assertEqual({x['id']: x['why'] for x in self.tc(b[0], 'tc_find')['list']}[ba], 'Chưa có Đảo bang')
            owns.update({ba: True, bb: False})
            self.refused('their_island', self.send, a[0], bb)
            owns[bb] = True
            cid = self.send(a[0], bb)['chal']['id']
            owns[bb] = False                                   # the island went before the answer
            self.assertEqual(str(self.refused('no_island', self.tc, b[0], 'tc_answer', id=cid, ok=True)), TC.NO_ISLAND)
            owns.update({ba: False, bb: True})
            self.refused('their_island', self.tc, b[0], 'tc_answer', id=cid, ok=True)
            owns[ba] = True
            self.assertEqual(self.tc(b[0], 'tc_answer', id=cid, ok=True)['match'], cid)
            TC._CACHE.clear()
            self.assertEqual({x['id']: x['why'] for x in self.tc(b[0], 'tc_find')['list']}[ba], '')


class Ranking(Store):
    """Owner 21/10 "top bang thì bằng cách cống hiến và tính điểm chiến lực bằng pets": 👑 = 🙌 cống hiến of the week +
    💪 chiến lực (each member's strongest pet now) × POWER_X; nothing else."""

    def setUp(self):
        super().setUp()
        bang._VIEW.clear()
        self.addCleanup(bang._VIEW.clear)
        self.t = [WED]
        p = mock.patch.object(bang, 'now', lambda: self.t[0])
        p.start()
        self.addCleanup(p.stop)

    mkbang = Base.mkbang
    sql = Base.sql
    rows = Base.rows

    def points(self, bid, tok, pts, kind='checkin', ref=None):
        sid = self.sid(tok)
        self.sql('INSERT INTO bang_points(id, bang, sid, kind, pts, week, day, at) VALUES(?,?,?,?,?,?,?,?)',
                 (ref or f'{kind}:{sid[:8]}:{pts}:{bid}', bid, sid, kind, pts, bang.vn_week(self.t[0]), bang.vn_day(self.t[0]), self.t[0]))

    def power_up(self, tok):
        """A pet command: the strongest pet's power is kept (game/pet_arena.py on_pet_commit, the save's transaction)."""
        st = self.store.read(tok)[0]
        self.store.transaction(lambda db: A.on_pet_commit(db, self.sid(tok), st))
        return A.best_power(st)

    def war(self, week, pts: dict, shown=True):
        """A weekly war of `week` already played: its ladder points per bang (shown: its matches are over by now)."""
        end = self.t[0] - 60 if shown else self.t[0] + 3600
        self.sql("INSERT INTO pet_war(week, status, start, n, rounds, data, at) VALUES(?, 'done', ?, ?, 2, ?, ?)",
                 (week, end - 900, len(pts), json.dumps(dict(end=end)), end - 900))
        for bid, n in pts.items():
            self.sql("INSERT INTO pet_team_ladder(week, team_kind, team_id, name, pts, at) VALUES(?, 'bang', ?, ?, ?, ?)", (week, bid, bid, n, end))

    def levels(self, bid, **lv):
        for fac, n in lv.items():
            self.sql('INSERT INTO bang_facilities(bang, fac, level) VALUES(?,?,?) ON CONFLICT (bang, fac) DO UPDATE SET level=EXCLUDED.level', (bid, fac, n))

    def part(self, week):
        with self.store.connect() as db:
            return {x['bang']: x for x in bang.standings(db, week)}

    def test_three_parts_and_their_weights(self):
        """Owner 21/10: "đừng để cống hiến bang tính điểm nhé, hãy tính điểm của pets, công trình và cấp bang làm điểm nhé"."""
        from game import bang_content as BC
        toks = [self.arena(('Mít', 'Na'), rank=3) for _ in range(4)]
        champ = self.mkbang('b00000000d1', 'Vô Địch', toks[:1])
        donor = self.mkbang('b00000000d2', 'Nhà Giàu', toks[1:2], emoji='💰')
        builder = self.mkbang('b00000000d3', 'Thợ Xây', toks[2:3], emoji='🏗️')
        self.sql('UPDATE bangs SET isle=0 WHERE id = ANY(?)', ([champ, donor, builder],))   # no 🏝️ Đảo bang yet: the hall only
        week = bang.vn_week(self.t[0])
        self.points(donor, toks[1], 500_000, kind='give')                        # 500 million xu given this week…
        self.points(donor, toks[1], 350, kind='checkin')
        self.levels(builder, dai_sanh=5, kho=8, xuong_may=5, den_vang=4, cong=4, san_pet=4)   # the hall 5, 25 other levels
        self.war(week, {champ: PW.PTS_WIN * 3 + PW.PTS_CHAMP, donor: 0})                     # the champion: 3 wins + the title
        got = self.part(week)
        self.assertEqual(got[donor]['score'], BC.LEVEL_SCORE, '…counts for nothing: only its level 1')
        self.assertNotIn('cong', got[donor])
        self.assertEqual(got[champ]['war'], 14 * BC.PET_WAR_SCORE)
        self.assertEqual((got[builder]['levels'], got[builder]['hall']), (25, 5))
        self.assertEqual(got[builder]['build'], 25 * BC.FAC_SCORE)
        self.assertEqual(got[builder]['level'], 5 * BC.LEVEL_SCORE)
        for x in got.values():
            self.assertEqual(x['pets'], x['war'] + x['chal'] + x['power'] // BC.POWER_DIV)
            self.assertEqual(x['score'], (x['pets'] + x['build'] + x['level']) * (100 + x['tuong']) // 100)
        order = [x['bang'] for x in sorted(got.values(), key=lambda x: -x['score'])]
        self.assertEqual(order[-1], donor, 'a huge donor with no pets and no buildings ranks last')
        self.assertLess(order.index(champ), order.index(donor))
        self.assertLess(order.index(builder), order.index(donor))
        # pets weigh most: the champion's war alone beats a level-5 bang of 25 facility levels
        self.assertGreater(got[champ]['score'], got[builder]['score'])
        # the war counts once its matches have been shown, never sooner
        self.sql('DELETE FROM pet_war')
        self.sql('DELETE FROM pet_team_ladder')
        self.war(week, {champ: 14}, shown=False)
        self.assertEqual(self.part(week)[champ]['war'], 0)
        # Tượng bang: a facility level, and +2 % of the whole score a level
        self.levels(builder, tuong=5)
        b = self.part(week)[builder]
        self.assertEqual((b['tuong'], b['levels']), (10, 30))
        self.assertEqual(b['score'], (b['pets'] + b['build'] + b['level']) * 110 // 100)
        # the lists, the board and the page show the three parts
        board = bang.board(self.store)
        row = next(r for r in board['top'] if r['id'] == builder)
        self.assertEqual((row['pets'], row['build'], row['level'], row['score']), (b['pets'], b['build'], b['level'], b['score']))
        card = next(c for c in bang.search(self.store, None) if c['id'] == builder)
        self.assertEqual((card['build'], card['levels'], card['level']), (b['build'], 30, b['level']))
        page = bang.page(self.store, self.sid(toks[2]))
        self.assertEqual((page['bang']['score'], page['bang']['pets']), (b['score'], b['pets']))
        # ⭐ the 🏝️ Đảo bang's level (bangs.isle) joins the hall's; an upgrade whose time is up counts at once
        self.sql('UPDATE bangs SET isle=2 WHERE id=?', (builder,))
        self.sql('UPDATE bangs SET isle=0, isle_to=1, isle_started=?, isle_ready=? WHERE id=?', (self.t[0] - 120, self.t[0] - 60, donor))
        self.sql('UPDATE bangs SET isle=1, isle_to=2, isle_started=?, isle_ready=? WHERE id=?', (self.t[0] - 60, self.t[0] + 3600, champ))
        got = self.part(week)
        self.assertEqual((got[builder]['level'], got[builder]['island']), ((5 + 2) * BC.LEVEL_SCORE, 2))
        self.assertEqual((got[donor]['level'], got[donor]['island']), (2 * BC.LEVEL_SCORE, 1), 'cấp 1 built: counts')
        self.assertEqual((got[champ]['level'], got[champ]['island']), (2 * BC.LEVEL_SCORE, 1), 'cấp 2 still building: not yet')
        self.assertEqual(got[builder]['score'], (got[builder]['pets'] + got[builder]['build'] + got[builder]['level']) * 110 // 100)
        with self.store.connect() as db:
            self.assertEqual(bang.week_of(db, builder, week, self.t[0])['level'], (5 + 2) * BC.LEVEL_SCORE)
        page = bang.page(self.store, self.sid(toks[2]))
        self.assertEqual((page['bang']['island'], page['bang']['level'], page['bang']['isle']), (2, 7 * BC.LEVEL_SCORE, 2))

    def test_power_ties_and_leaving(self):
        from game import bang_content as BC
        strong = [self.arena(('Mít', 'Na'), rank=5) for _ in range(2)]
        weak = [self.arena(('Bơ',), rank=1) for _ in range(3)]
        x = self.mkbang('b00000000e1', 'Rồng Đỏ', strong)
        y = self.mkbang('b00000000e2', 'Cá Xanh', weak, emoji='🐟')
        pw = {t: self.power_up(t) for t in strong + weak}
        st = self.store.read(strong[0])[0]
        self.assertEqual(pw[strong[0]], max(px.power(st, p) for p in A.candidates(st)), 'the strongest pet, home or kennel')
        self.points(y, weak[0], 2000)
        self.points(y, weak[1], 30, kind='chal')
        week = bang.vn_week(self.t[0])
        got = self.part(week)
        self.assertEqual(got[x]['power'], pw[strong[0]] + pw[strong[1]])
        self.assertEqual(got[y]['power'], sum(pw[t] for t in weak))
        self.assertEqual(got[y]['score'], got[y]['power'] // BC.POWER_DIV + BC.LEVEL_SCORE, 'cống hiến never counts')
        with self.store.connect() as db:
            self.assertEqual(bang.scores(db, week), [(r['bang'], r['score']) for r in bang.standings(db, week)])
            self.assertEqual(bang.week_of(db, y, week)['score'], got[y]['score'])
        # a member leaving takes their pet power away at once
        self.sql("UPDATE bang_members SET status='out' WHERE sid=?", (self.sid(strong[1]),))
        with self.store.connect() as db:
            self.assertEqual(bang.power(db, [x])[x], pw[strong[0]])
        # ties: the same score → more 🐾 pets points first, then the older bang
        self.sql('DELETE FROM pet_power')
        self.sql('UPDATE bangs SET created=? WHERE id=?', (WED - 5 * 86400, y))
        with self.store.connect() as db:
            self.assertEqual([r['bang'] for r in bang.standings(db, week)], [y, x], 'equal: the older bang')
        self.war(week, {x: 3})                                       # 3 × 500 = 1.500 of pets…
        self.levels(y, kho=10)                                       # …against 10 × 150 = 1.500 of buildings
        self.assertEqual(3 * BC.PET_WAR_SCORE, 10 * BC.FAC_SCORE)
        with self.store.connect() as db:
            sc = bang.standings(db, week)
        self.assertEqual(sc[0]['score'], sc[1]['score'])
        self.assertEqual(sc[0]['bang'], x, 'equal score: more pets points first')

    def test_cheap_no_save_parsed_and_only_on_change(self):
        a = self.arena(('Mít',), rank=4)
        bid = self.mkbang('b00000000e1', 'Hổ', [a])
        self.power_up(a)
        at = self.rows('SELECT at FROM pet_power')[0]['at']
        self.power_up(a)
        self.assertEqual(self.rows('SELECT at FROM pet_power')[0]['at'], at, 'no write when nothing changed')
        with mock.patch.object(self.store, 'read', side_effect=AssertionError('a save was read')), \
                mock.patch('json.loads', side_effect=AssertionError('a save was parsed')):
            with self.store.connect() as db:
                self.assertGreater(bang.power(db)[bid], 0)
                bang.standings(db, bang.vn_week(self.t[0]))
        # a player without a pet command yet but with a pet on the challenge roster: that pet counts
        b = self.arena(('Na',), rank=6)
        self.sql("INSERT INTO bang_members(bang, sid, pid, status, role, joined) VALUES(?,?,?,'in','tv',?)", (bid, self.sid(b), bang.pid_of(self.sid(b)), WED))
        self.sql('INSERT INTO bang_chal_roster(bang, sid, pid, name, pet, snap, pw, ok, pos, at) VALUES(?,?,?,?,?,?,?,1,1,?)',
                 (bid, self.sid(b), bang.pid_of(self.sid(b)), 'Na', 'p1', '{}', 777, WED))
        with self.store.connect() as db:
            self.assertEqual(bang.power(db, [bid])[bid], self.rows('SELECT pw FROM pet_power')[0]['pw'] + 777)
        # erasing the data takes the row
        self.store.transaction(lambda db: A.forget(db, self.sid(a)))
        self.assertEqual(self.rows('SELECT * FROM pet_power WHERE sid=?', (self.sid(a),)), [])


if __name__ == '__main__':
    unittest.main()
