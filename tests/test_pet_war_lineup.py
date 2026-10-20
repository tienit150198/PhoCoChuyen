"""👑 The leaders choose the 🛡️ Bang chiến pet lineup (owner, verbatim: "bang chủ được quyền chọn danh sách thú để
xuất chiến nhé, hiện tại bang chủ không chọn thú xuất chiến được"; game/pet_war.py war_team / war_lineup /
war_lineup_off, game/bang_pets.py can_lead): Trưởng lão and up (the ⚔️ Thách đấu roster's officers) list the members
with their pets and save 1…5 member + pet pairs; the lineup replaces the bang's picks of the week and wins over the
members' own picks until a leader hands it back; members still volunteer without one; the server checks the role,
the lock, the size, one pet a member, the pet's owner and the island; the war plays with the leaders' lineup; and the
release live before it (2.4.70 at aeb68cc0) plays the same war from the same table (no schema change)."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from game import pet_arena as A
from game import pet_tiers as px
from game import pet_war as PW
from tests.test_bang_challenge import Base, WED

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'aeb68cc0'   # 2.4.70 (live)
LOCK = PW.lock_of(WED)


class Help(Base):
    def bang(self, n=6, roles=('chu', 'pho', 'lao', 'tinh'), bid='b00000000a1', name='Rồng Đỏ', pets=('Mít',), ranks=None, emoji='🐉'):
        toks = [self.arena(pets, rank=(ranks[i] if ranks else 3)) for i in range(n)]
        self.mkbang(bid, name, toks, roles, emoji=emoji)
        return toks, bid

    def pets(self, tok):
        return px.all_pets(self.store.read(tok)[0])

    def pid(self, tok):
        from game import bang
        return bang.pid_of(self.sid(tok))

    def lineup(self, by, toks, i=0):
        return self.tc(by, 'war_lineup', picks=[dict(pid=self.pid(t), pet=self.pets(t)[i]['id']) for t in toks])

    def picks(self, bid):
        return self.rows("SELECT sid, pet, snap FROM pet_war_picks WHERE team_id=? AND sid NOT LIKE '~lead|%' ORDER BY at, sid", (bid,))

    def mypick(self, tok, i=0):
        return self.tc(tok, 'war_pick', pet=self.pets(tok)[i]['id'])

    def two_bangs(self):
        a, ba = self.bang(n=6, ranks=(1, 1, 1, 6, 6, 6))
        b, bb = self.bang(n=5, bid='b00000000b2', name='Cá Xanh', emoji='🐟')
        for t in a[:3] + b:                                    # the weak three of A volunteer first…
            self.mypick(t)
        chosen = [a[3], a[4], a[0]]                            # …the leader fields its strong two and one weak
        self.lineup(a[0], chosen)
        return a, b, ba, bb, chosen

    def assert_played(self, ba, bb, chosen, b):
        with self.store.connect() as db:
            war = dict(db.execute('SELECT * FROM pet_war').fetchone())
            m = dict(db.execute('SELECT * FROM pet_war_matches WHERE rd=1 AND b_name<>\'\'').fetchone())
        self.assertEqual((war['status'], war['n']), ('done', 2))
        teams = {x['id']: x for x in json.loads(war['data'])['teams']}
        self.assertEqual((teams[ba]['n'], teams[bb]['n']), (3, 5))
        side = 'a' if m['a_id'] == ba else 'b'
        duels = json.loads(m['data'])['duels']
        mine = {d[side]['sid'] for d in duels if d[side]}
        self.assertEqual(mine, {self.sid(t) for t in chosen}, "the leaders' lineup fought, not the volunteers")
        other = 'b' if side == 'a' else 'a'
        self.assertEqual({d[other]['sid'] for d in duels if d[other]}, {self.sid(t) for t in b})


class Lineup(Help):
    # ------------------------------------------------------------------ the editor and the save
    def test_leader_lists_members_and_sets_the_lineup(self):
        toks, bid = self.bang(n=6, ranks=(3, 4, 5, 2, 6, 1))
        self.mypick(toks[5])                                   # a volunteer before the leader's choice
        v = self.tc(toks[0], 'war_team')
        self.assertEqual(len(v['members']), 6)
        self.assertTrue(all(m['ok'] and m['pets'] and m['best'] == m['pets'][0]['id'] for m in v['members']))
        pws = [m['pw'] for m in v['members']]
        self.assertEqual(pws, sorted(pws, reverse=True), 'the strongest first: the suggestion')
        self.assertTrue(all('r' in p and 'pw' in p for m in v['members'] for p in m['pets']), 'rank and power of each pet')
        self.assertEqual(v['picks'], [dict(pid=self.pid(toks[5]), pet=self.pets(toks[5])[0]['id'])])
        self.assertIsNone(v['lead'])
        self.assertNotIn('sid', json.dumps(v), 'never a save id on the page')
        chosen = toks[:5]
        out = self.lineup(toks[0], chosen)
        self.assertIn('Đã chọn đội hình 5/5', out['message'])
        rows = self.picks(bid)
        self.assertEqual([r['sid'] for r in rows], [self.sid(t) for t in chosen], 'replaces the picks, in the order chosen')
        st = self.store.read(chosen[1])[0]
        self.assertEqual(json.loads(rows[1]['snap']), A.fighter(st, px.all_pets(st)[0]), 'the same snapshot as a pick of their own')
        w = self.tc(toks[3], 'war')
        self.assertEqual(w['lead']['role'], 'Bang chủ')
        self.assertFalse(w['can_lead'], 'a Tinh anh does not choose')
        self.assertTrue(self.tc(toks[0], 'war')['can_lead'])
        self.assertEqual(len(w['picks']), 5)
        self.assertEqual(self.tc(toks[0], 'war_team')['lead']['role'], 'Bang chủ')
        # the bang hears it: its log and its chat group name the members picked
        log = self.rows("SELECT text FROM bang_log WHERE bang=? AND kind='war'", (bid,))
        self.assertEqual(len(log), 1)
        self.assertIn('Bang chủ', log[0]['text'])
        self.assertIn('chọn đội hình Bang chiến pet', log[0]['text'])
        for i in range(5):
            self.assertIn(f'Người {i + 1} (Mít)', log[0]['text'])
        self.assertNotIn('Người 6', log[0]['text'])
        chat = self.rows("SELECT name, text FROM chat_messages WHERE channel=?", ('g:' + bid[-6:],))
        self.assertEqual([c['name'] for c in chat], ['🛡️ Bang chiến pet'])

    def test_members_cannot_override_and_the_leader_changes_until_the_lock(self):
        toks, bid = self.bang(n=7, pets=('Mít', 'Na'))
        self.lineup(toks[0], toks[:3])
        for t in (toks[1], toks[6]):                           # one in the lineup, one outside it
            e = self.refused('lead_set', self.mypick, t)
            self.assertIn('Bang chủ đã chọn đội hình', str(e))
        self.refused('lead_set', self.tc, toks[1], 'war_unpick')
        self.refused('lead_set', self.mypick, toks[0])        # the leader too: through the editor only
        self.assertEqual(len(self.picks(bid)), 3)
        # the leader (or a Phó bang / Trưởng lão) changes it: other members, another pet
        self.lineup(toks[2], [toks[4], toks[5], toks[1]], i=1)
        rows = self.picks(bid)
        self.assertEqual([r['sid'] for r in rows], [self.sid(t) for t in (toks[4], toks[5], toks[1])])
        self.assertEqual(rows[2]['pet'], self.pets(toks[1])[1]['id'])
        self.assertEqual(self.tc(toks[0], 'war')['lead']['role'], 'Trưởng lão', 'who chose last')
        # handed back: the members pick their own again, the lineup kept
        self.assertIn('tự chọn', self.tc(toks[1], 'war_lineup_off')['message'])
        self.assertEqual(len(self.picks(bid)), 3)
        self.assertIsNone(self.tc(toks[6], 'war')['lead'])
        self.mypick(toks[6])
        self.tc(toks[4], 'war_unpick')
        self.assertEqual({r['sid'] for r in self.picks(bid)}, {self.sid(t) for t in (toks[5], toks[1], toks[6])})
        self.refused('none', self.tc, toks[0], 'war_lineup_off')
        # after the lock nobody changes anything
        self.t[0] = LOCK + 1
        self.refused('locked', self.lineup, toks[0], toks[:2])
        self.refused('locked', self.tc, toks[0], 'war_lineup_off')

    def test_only_officers_choose(self):
        toks, bid = self.bang(n=5, roles=('chu', 'pho', 'lao', 'tinh', 'tv'))
        for t in (toks[3], toks[4]):                           # Tinh anh, Thành viên
            self.refused('role', self.tc, t, 'war_team')
            self.refused('role', self.lineup, t, toks[:2])
        self.assertEqual(self.picks(bid), [])
        for t in toks[:3]:                                     # Bang chủ, Phó bang, Trưởng lão (as the Thách đấu roster)
            self.assertTrue(self.tc(t, 'war_team')['members'])
        outsider = self.arena(('Bơ',))
        self.refused('no_team', self.tc, outsider, 'war_team')

    def test_the_server_checks_size_owner_and_members(self):
        toks, bid = self.bang(n=7, pets=('Mít', 'Na'))
        lead = toks[0]
        self.refused('bad_picks', self.tc, lead, 'war_lineup', picks=[])
        self.refused('bad_picks', self.lineup, lead, toks[:6])                       # more than SIZE
        self.refused('bad_picks', self.tc, lead, 'war_lineup', picks=[dict(pid=self.pid(toks[1]))])
        p1 = self.pets(toks[1])
        self.refused('twice', self.tc, lead, 'war_lineup', picks=[dict(pid=self.pid(toks[1]), pet=p1[0]['id']), dict(pid=self.pid(toks[1]), pet=p1[1]['id'])])
        # someone else's pet: refused (the pet must be the member's own, at home or in the kennel)
        one = self.arena(('Bơ',))                                                     # one pet (p1): Người 2's p2 is not theirs
        self.sql("INSERT INTO bang_members(bang, sid, pid, status, role, joined) VALUES(?,?,?,'in','tv',?)", (bid, self.sid(one), self.pid(one), WED))
        other = p1[1]['id']
        self.assertNotIn(other, [p['id'] for p in self.pets(one)])
        e = self.refused('not_owned', self.tc, lead, 'war_lineup', picks=[dict(pid=self.pid(one), pet=other)])
        self.assertIn('Người 8', str(e))
        self.refused('not_owned', self.tc, lead, 'war_lineup', picks=[dict(pid=self.pid(toks[1]), pet='p999')])
        # a player outside the bang, or one who left
        outsider = self.arena(('Bơ',))
        self.refused('not_member', self.tc, lead, 'war_lineup', picks=[dict(pid=self.pid(outsider), pet=self.pets(outsider)[0]['id'])])
        self.sql("UPDATE bang_members SET status='out' WHERE sid=?", (self.sid(toks[3]),))
        self.refused('not_member', self.lineup, lead, [toks[1], toks[3]])
        self.assertEqual(self.picks(bid), [], 'nothing saved by a refused lineup')
        self.assertEqual(self.rows("SELECT * FROM pet_war_picks WHERE sid LIKE '~lead|%'"), [])
        # 🏝️ a bang without its island fields nobody (as a member's own pick)
        self.sql("UPDATE bangs SET isle=0, isle_how='' WHERE id=?", (bid,))
        self.refused('no_island', self.lineup, lead, toks[1:3])
        self.refused('no_island', self.tc, lead, 'war_team')

    def test_members_volunteer_without_a_leader_lineup(self):
        toks, bid = self.bang(n=7)
        for t in toks[1:6]:
            self.assertIn('ra trận cho', self.mypick(t)['message'])
        self.refused('full', self.mypick, toks[6])
        w = self.tc(toks[1], 'war')
        self.assertIsNone(w['lead'])
        self.assertEqual(len(w['picks']), 5)
        self.assertEqual(len(self.tc(toks[0], 'war_team')['picks']), 5)

    # ------------------------------------------------------------------ the war
    def test_the_war_plays_with_the_leaders_lineup(self):
        a, b, ba, bb, chosen = self.two_bangs()
        self.assertTrue(PW.run_due(self.store, LOCK + 1))
        self.assert_played(ba, bb, chosen, b)
        self.t[0] = PW.start_of(WED) + PW.GAP + PW.SIZE * PW.DUEL_SECS + 1
        v = self.tc(a[1], 'war')
        self.assertIn(v['phase'], ('done', 'live'))

    def test_snapshot_follows_the_pet_until_the_lock(self):
        toks, bid = self.bang(n=3)
        self.lineup(toks[0], toks[1:3])
        st = self.store.read(toks[1])[0]
        p = px.all_pets(st)[0]
        st['journey']['petx']['t'][p['id']]['r'] = 6
        self.store.transaction(lambda db: PW.on_pet_commit(db, self.sid(toks[1]), st))
        snap = json.loads(self.picks(bid)[0]['snap'])
        self.assertEqual(snap, A.fighter(st, p))
        self.assertIsNotNone(self.tc(toks[2], 'war')['lead'], 'a snapshot refresh keeps the leaders’ lineup')


OLD = '''import json,sys
from game.storage import Store
from game import bang, bang_pets, pet_arena as A, pet_war as PW
store=Store(sys.argv[1])
tok=sys.argv[2]
t=float(sys.argv[3])
A.now=bang.now=lambda: float(sys.argv[4])
out={}
out['view']=len(A.act(store, tok, 'war', {}, None, '1.1.1.1')['picks'])
out['played']=PW.run_due(store, t)
store.close_pool()
print(json.dumps(out))
'''


class OldRelease(Help):
    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-warpick-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference', 'live'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {RELEASE}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def test_live_release_plays_the_war_from_the_leaders_lineup(self):
        a, b, ba, bb, chosen = self.two_bangs()
        old = self.old_tree()
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        got = subprocess.run([sys.executable, '-c', OLD, str(self.store.path), a[1], str(LOCK + 1), str(WED)], capture_output=True, text=True, cwd=old,
                             env=env, encoding='utf-8', timeout=300)
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        out = json.loads(got.stdout.strip().splitlines()[-1])
        self.assertEqual(out, dict(view=3, played=True), 'the marker row is no fighter for 2.4.70 either')
        self.assert_played(ba, bb, chosen, b)


if __name__ == '__main__':
    unittest.main()
