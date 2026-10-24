"""🥉 Tranh hạng 3 of the weekly 🛡️ Bang chiến pet (owner 25/10, game/pet_war.py): with two real semi-finals the two
losers play once more, at the final's start, by the same rules (team_match, tie-breaks by seed), stored as one more
pet_war_matches row (rd = rounds + 1, slot 0). The winner gets PTS_WIN (no champion bonus), Elo moves for both, the
ladder puts the third before the fourth, the third's fighters hold 🥉 Hạng ba bang chiến pet (ranks 11–15 of board
'pet_war'); with 3 bangs the lone real semi-final's loser is third without a match. Results stay fixed at the lock and
are shown from each match's start. An older build (2.6.7, origin/main before this) reads the extra row without
crashing and without drawing a second final."""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from game import lb_titles as lbt
from game import pet_arena as A
from game import pet_tiers as px
from game import pet_war as PW
from tests.test_lb_titles import at
from tests.test_pet_arena import Store, Teams

ROOT = Path(__file__).resolve().parents[1]
OLD_REF = '1a1f6846'          # 2.6.7 (prod when the 3rd-place match was added)


class Base(Store):
    SAT = PW.start_of(at(2026, 10, 21, 12, 0))

    def setUp(self):
        super().setUp()
        from game import bang_pets       # imported (and registered) now, never in the middle of a test over our Teams
        self.addCleanup(bang_pets.install)
        self.addCleanup(PW.unregister, 'bang')

    # ---------------------------------------------------------------- helpers
    def war(self, n, per=1, ranks=None):
        """n teams 'T1'…'Tn' (per fighters each), every pick made on Wednesday, the war played at the lock."""
        toks, team = [], {}
        for i in range(n):
            for j in range(per):
                r = (ranks or [3] * n)[i]
                tok = self.arena(('Mít',), rank=r)
                toks.append((i, tok))
                team[self.sid(tok)] = (f'T{i + 1}', f'Bang {i + 1:02d}')
        PW.register('bang', Teams(team))
        with mock.patch.object(A, 'now', return_value=at(2026, 10, 21, 12)):
            for _, tok in toks:
                self.op(tok, 'war_pick', pet=px.all_pets(self.store.read(tok)[0])[0]['id'])
        self.assertTrue(PW.run_due(self.store, self.SAT - 5 * 60))
        self.assertFalse(PW.run_due(self.store, self.SAT - 4 * 60), 'played once')
        self.team = team
        self.toks = toks
        return toks, team

    def rows(self):
        with self.store.connect() as db:
            war = dict(db.execute('SELECT * FROM pet_war').fetchone())
            ms = [dict(m) for m in db.execute('SELECT * FROM pet_war_matches ORDER BY rd, slot').fetchall()]
            lad = {r['team_id']: dict(r) for r in db.execute('SELECT * FROM pet_team_ladder').fetchall()}
        return war, ms, lad

    def fighters(self, tid):
        return sorted(s for s, (t, _) in self.team.items() if t == tid)

    def tok_of(self, tid):
        return next(tok for _, tok in self.toks if self.team[self.sid(tok)][0] == tid)

    def card(self, tid, t):
        with self.store.connect() as db:
            return PW.team_card(db, 'bang', tid, self.sid(self.tok_of(tid)), t)

    @staticmethod
    def ids(m, side):
        return m[f'{side}_id']


class Third(Base):
    # ---------------------------------------------------------------- 4 teams: the plain case
    def test_four_teams_play_for_third(self):
        self.war(4)
        war, ms, lad = self.rows()
        self.assertEqual((war['n'], war['rounds']), (4, 2), 'rounds stays the bracket')
        self.assertEqual([(m['rd'], m['slot']) for m in ms], [(1, 0), (1, 1), (2, 0), (3, 0)])
        semis, final, third = ms[:2], ms[2], ms[3]
        self.assertTrue(all(m['b_name'] for m in ms), 'no bye with 4 teams')
        self.assertEqual(third['start'], final['start'], 'the 3rd-place match starts with the final')
        self.assertTrue(json.loads(third['data'])['third'])
        self.assertNotIn('third', json.loads(final['data']))
        losers = [self.ids(m, 'b' if m['win'] == 0 else 'a') for m in semis]
        self.assertEqual([third['a_id'], third['b_id']], losers, 'the semi-final losers, top half first')
        third_w = self.ids(third, 'a' if third['win'] == 0 else 'b')
        fourth = self.ids(third, 'b' if third['win'] == 0 else 'a')
        champ = self.ids(final, 'a' if final['win'] == 0 else 'b')
        second = self.ids(final, 'b' if final['win'] == 0 else 'a')
        data = json.loads(war['data'])
        self.assertEqual(data['third_team']['id'], third_w)
        self.assertEqual(data['fourth_team']['id'], fourth)
        self.assertTrue(data['third_match'])
        self.assertEqual(sorted(data['third']), self.fighters(third_w))
        # end_of: every match is over by then
        self.assertEqual(PW.end_of(war), max(m['start'] for m in ms) + PW.SIZE * PW.DUEL_SECS)
        # points: a win PTS_WIN, the champion PTS_CHAMP more, the third no bonus; `best` stays the semi-final
        self.assertEqual((lad[champ]['w'], lad[champ]['l'], lad[champ]['pts'], lad[champ]['best']), (2, 0, 2 * PW.PTS_WIN + PW.PTS_CHAMP, 3))
        self.assertEqual((lad[second]['w'], lad[second]['l'], lad[second]['pts'], lad[second]['best']), (1, 1, PW.PTS_WIN, 2))
        self.assertEqual((lad[third_w]['w'], lad[third_w]['l'], lad[third_w]['pts'], lad[third_w]['best']), (1, 1, PW.PTS_WIN, 1))
        self.assertEqual((lad[fourth]['w'], lad[fourth]['l'], lad[fourth]['pts'], lad[fourth]['best']), (0, 2, 0, 1))
        # Elo: every match in its order (rd, slot), the 3rd-place match last, from the start rating
        rating = {tid: A.START for tid in lad}
        for m in ms:
            a, b = m['a_id'], m['b_id']
            da = A.elo(rating[a], rating[b], 1.0 if m['win'] == 0 else 0.0, PW.K_TEAM)
            db_ = A.elo(rating[b], rating[a], 1.0 if m['win'] == 1 else 0.0, PW.K_TEAM)
            rating[a] += da
            rating[b] += db_
        self.assertEqual({k: v['rating'] for k, v in lad.items()}, rating)
        with self.store.connect() as db:
            self.assertEqual({k: PW.team_rating(db, 'bang', k)['rating'] for k in lad}, rating)
        # the ladder: champion, runner-up, third, fourth
        end = PW.end_of(war) + 1
        with self.store.connect() as db:
            board = PW.ladder(db, t=end)
            self.assertEqual([x['id'] for x in board], [champ, second, third_w, fourth])
            self.assertEqual([x['place'] for x in board], [0, 0, 3, 4])
            self.assertEqual(PW.ladder(db, t=end, n=3)[-1]['id'], third_w)
            st = PW.standings(db, end)
            self.assertEqual(PW.standings(db, PW.end_of(war) - 1), [], 'no title before the war is over')
        self.assertEqual(sorted(s for b, r, s, _ in st if 11 <= r <= 15), self.fighters(third_w))
        self.assertEqual(sorted(s for b, r, s, _ in st if r <= 5), self.fighters(champ))
        self.assertFalse(set(self.fighters(fourth)) & {s for _, _, s, _ in st}, 'the fourth holds nothing')
        self.assertEqual(lbt.title_of('pet_war', 11), dict(emoji='🥉', name='Hạng ba bang chiến pet', text='🥉 Hạng ba bang chiến pet',
                                                          tier=2, label='Bang hạng ba'))
        self.assertEqual(lbt.reward_of('pet_war', 11), 0, 'no weekly xu for the third (owner did not set one)')
        self.assertEqual([t['emoji'] for t in lbt.tiers_of('pet_war')], ['🏆', '🥈', '🥉'])
        # bang.war_scores-like: the ladder points, the 3rd-place win counted as any win
        from game import bang
        with self.store.connect() as db:
            sc = bang.war_scores(db, war['week'], end)
        self.assertEqual(sc.get(third_w), PW.PTS_WIN * bang.C.PET_WAR_SCORE)
        self.assertNotIn(fourth, sc)

    def test_views_reveal_the_third_match_by_its_start(self):
        self.war(4)
        war, ms, lad = self.rows()
        semis, final, third = ms[:2], ms[2], ms[3]
        fourth = self.ids(third, 'b' if third['win'] == 0 else 'a')
        third_w = self.ids(third, 'a' if third['win'] == 0 else 'b')
        tok = self.tok_of(third['a_id'])
        # during the semi-finals: the column is there, the pairing is not
        with mock.patch.object(A, 'now', return_value=self.SAT + 10):
            v = self.op(tok, 'war')
            self.assertEqual([r['name'] for r in v['rounds']], ['Bán kết', 'Chung kết', 'Tranh hạng 3'])
            self.assertTrue(v['rounds'][-1]['third'])
            b3 = next(b for b in v['bracket'] if b['third'])
            self.assertEqual((b3['rd'], b3['slot'], b3['a'], b3['b'], b3['state']), (3, 0, '', '', 'wait'))
            self.assertFalse(b3['mine'])
            self.assertIsNone(v['third'])
            with self.assertRaises(A.ArenaError) as cm:
                self.op(tok, 'war_match', rd=3, slot=0)
            self.assertEqual(cm.exception.code, 'not_yet')
            c = self.card(third['a_id'], self.SAT + 10)
            self.assertEqual([m['round'] for m in c['matches']], ['Bán kết'])
            self.assertFalse(c['third'])
        # the semi-finals over: the pairing shows, the card says the team plays for third
        t = self.SAT + PW.SIZE * PW.DUEL_SECS + 1
        c = self.card(third['a_id'], t)
        self.assertEqual([(m['round'], m['third'], m['state']) for m in c['matches']], [('Bán kết', False, 'done'), ('Tranh hạng 3', True, 'wait')])
        self.assertEqual(c['matches'][1]['vs'], third['b_name'])
        self.assertTrue(c['third'])
        self.assertIsNone(c['result'])
        self.assertFalse(self.card(final['a_id'], t)['third'], 'finalists do not play for third')
        with mock.patch.object(A, 'now', return_value=t):
            b3 = next(b for b in self.op(tok, 'war')['bracket'] if b['third'])
            self.assertEqual((b3['a'], b3['b'], b3['mine']), (third['a_name'], third['b_name'], True))
        # live, duel by duel, like any match
        t = third['start'] + PW.DUEL_SECS + 1
        with mock.patch.object(A, 'now', return_value=t):
            mv = self.op(tok, 'war_match', rd=3, slot=0)
            self.assertEqual((mv['round'], mv['third'], len(mv['duels']), mv['over']), ('Tranh hạng 3', True, 2, False))
            self.assertNotIn('win', mv)
            self.assertEqual(self.op(tok, 'war')['phase'], 'live')
            fm = self.op(tok, 'war_match', rd=2, slot=0)
            self.assertEqual((fm['round'], fm['third']), ('Chung kết', False))
        self.assertEqual(self.card(third['a_id'], t)['matches'][1]['state'], 'live')
        # over: the bracket, the champion's line with the third, each card's result
        end = PW.end_of(war) + 1
        with mock.patch.object(A, 'now', return_value=end):
            v = self.op(tok, 'war')
            self.assertEqual(v['phase'], 'done')
            self.assertEqual(v['third'], next(x['name'] for x in v['ladder'] if x['place'] == 3))
            b3 = next(b for b in v['bracket'] if b['third'])
            self.assertEqual((b3['state'], b3['win'], b3['wa'], b3['wb']), ('done', third['win'], third['wa'], third['wb']))
            mv = self.op(tok, 'war_match', rd=3, slot=0)
            self.assertTrue(mv['over'])
            self.assertEqual(len(mv['duels']), 5)
        r3, r4 = self.card(third_w, end)['result'], self.card(fourth, end)['result']
        self.assertEqual((r3['third'], r3['place'], r3['second'], r3['champ'], r3['round'], r3['pts']), (True, 3, False, False, 'Bán kết', PW.PTS_WIN))
        self.assertEqual((r4['third'], r4['place'], r4['second']), (False, 4, False))
        champ = self.ids(final, 'a' if final['win'] == 0 else 'b')
        second = self.ids(final, 'b' if final['win'] == 0 else 'a')
        self.assertEqual(self.card(champ, end)['result']['place'], 1)
        self.assertEqual((self.card(second, end)['result']['place'], self.card(second, end)['result']['second']), (2, True))
        won = self.card(third_w, end)['matches'][-1]
        self.assertEqual((won['round'], won['won'], won['score'][0] >= won['score'][1]), ('Tranh hạng 3', True, True))

    # ---------------------------------------------------------------- 3 teams: no match, the semi-final's loser is third
    def test_three_teams_third_without_a_match(self):
        self.war(3)
        war, ms, lad = self.rows()
        self.assertEqual(war['rounds'], 2)
        self.assertEqual(len(ms), 3, 'a bye, a semi-final, the final: no 3rd-place match')
        self.assertFalse(any(m['rd'] == 3 for m in ms))
        semi = next(m for m in ms if m['rd'] == 1 and m['b_name'])
        loser = self.ids(semi, 'b' if semi['win'] == 0 else 'a')
        data = json.loads(war['data'])
        self.assertEqual((data['third_team']['id'], data['fourth_team'], data['third_match']), (loser, None, False))
        self.assertEqual((lad[loser]['w'], lad[loser]['l'], lad[loser]['pts']), (0, 1, 0))
        end = PW.end_of(war) + 1
        with self.store.connect() as db:
            st = PW.standings(db, end)
            self.assertEqual(PW.ladder(db, t=end)[-1]['place'], 3)
        self.assertEqual(sorted(s for _, r, s, _ in st if r > 10), self.fighters(loser))
        self.assertEqual(self.card(loser, end)['result']['third'], True)
        self.assertFalse(self.card(loser, end)['third'], 'no 3rd-place match to play')
        with mock.patch.object(A, 'now', return_value=end):
            v = self.op(self.tok_of(loser), 'war')
        self.assertEqual([r['name'] for r in v['rounds']], ['Bán kết', 'Chung kết'])
        self.assertEqual(v['third'], lad[loser]['name'])

    def test_two_teams_final_only(self):
        self.war(2)
        war, ms, lad = self.rows()
        self.assertEqual([(m['rd'], m['slot']) for m in ms], [(1, 0)])
        data = json.loads(war['data'])
        self.assertEqual((data['third'], data['third_team'], data['third_match']), ([], None, False))
        with self.store.connect() as db:
            self.assertFalse([x for x in PW.standings(db, PW.end_of(war) + 1) if x[1] > 10])

    # ---------------------------------------------------------------- 5 and 8 teams: byes, a bigger bracket
    def test_five_teams_byes_then_third(self):
        self.war(5)
        war, ms, lad = self.rows()
        self.assertEqual(war['rounds'], 3)
        self.assertEqual(sum(1 for m in ms if not m['b_name']), 3, 'three byes for the best seeds')
        self.assertEqual([(m['rd'], m['slot']) for m in ms if m['b_name']], [(1, 1), (2, 0), (2, 1), (3, 0), (4, 0)])
        semis = [m for m in ms if m['rd'] == 2]
        third = next(m for m in ms if m['rd'] == 4)
        final = next(m for m in ms if m['rd'] == 3)
        self.assertEqual(third['start'], final['start'])
        self.assertEqual(final['start'], self.SAT + 2 * PW.GAP)
        self.assertEqual([third['a_id'], third['b_id']], [self.ids(m, 'b' if m['win'] == 0 else 'a') for m in semis])
        third_w = self.ids(third, 'a' if third['win'] == 0 else 'b')
        fourth = self.ids(third, 'b' if third['win'] == 0 else 'a')
        self.assertEqual((lad[third_w]['best'], lad[fourth]['best']), (2, 2), 'both stay at the semi-final')
        self.assertEqual((lad[third_w]['l'], lad[fourth]['l']), (1, 2))
        end = PW.end_of(war) + 1
        with self.store.connect() as db:
            board = PW.ladder(db, t=end)
        self.assertEqual([x['place'] for x in board[2:4]], [3, 4], 'the third before the fourth whatever their points (byes)')
        self.assertEqual(board[2]['id'], third_w)
        with mock.patch.object(A, 'now', return_value=end):
            v = self.op(self.tok_of(third_w), 'war')
        self.assertEqual([r['name'] for r in v['rounds']], ['Tứ kết', 'Bán kết', 'Chung kết', 'Tranh hạng 3'])
        self.assertEqual([r['rd'] for r in v['rounds']], [1, 2, 3, 4])
        self.assertEqual(PW.end_of(war), self.SAT + 2 * PW.GAP + PW.SIZE * PW.DUEL_SECS)

    def test_eight_teams(self):
        self.war(8)
        war, ms, lad = self.rows()
        self.assertEqual(war['rounds'], 3)
        self.assertEqual([(m['rd'], m['slot']) for m in ms], [(1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (3, 0), (4, 0)])
        self.assertTrue(all(m['b_name'] for m in ms))
        third = ms[-1]
        third_w = self.ids(third, 'a' if third['win'] == 0 else 'b')
        fourth = self.ids(third, 'b' if third['win'] == 0 else 'a')
        # every team's points are PTS_WIN a win (+ PTS_CHAMP for the champion)
        self.assertEqual(len(json.loads(war['data'])['teams']), 8)
        for tid, r in lad.items():
            self.assertEqual(r['pts'], PW.PTS_WIN * r['w'] + (PW.PTS_CHAMP if r['champ'] else 0))
        wl = sorted((r['best'], r['w'], r['l']) for r in lad.values())
        self.assertEqual(wl, [(1, 0, 1)] * 4 + [(2, 1, 2), (2, 2, 1), (3, 2, 1), (4, 3, 0)])
        self.assertEqual((lad[third_w]['w'], lad[third_w]['l']), (2, 1))
        self.assertEqual((lad[fourth]['w'], lad[fourth]['l']), (1, 2))
        end = PW.end_of(war) + 1
        with self.store.connect() as db:
            board = PW.ladder(db, t=end)
            st = PW.standings(db, end)
        self.assertEqual([x['place'] for x in board[:4]], [0, 0, 3, 4])
        self.assertEqual(len(st), 3, 'one fighter each: champion, runner-up, third')
        self.assertEqual(sorted(r for _, r, _, _ in st), [1, 6, 11])

    # ---------------------------------------------------------------- tie-breaks
    def test_a_tied_third_place_match_goes_to_the_better_seed(self):
        real = PW.team_match

        def tied(a, b, key, size=PW.SIZE):
            res = real(a, b, key, size)
            if key.endswith('-3-0'):        # 4 teams: the 3rd-place match is round 3
                res = dict(res, w=2, wa=2, wb=2, hp=[500, 500])
            return res
        with mock.patch.object(PW, 'team_match', tied):
            self.war(4)
        war, ms, lad = self.rows()
        third = ms[-1]
        seeds = {x['id']: x['seed'] for x in json.loads(war['data'])['teams']}
        self.assertEqual((third['wa'], third['wb']), (2, 2))
        self.assertTrue(json.loads(third['data'])['tie'])
        want = 0 if seeds[third['a_id']] < seeds[third['b_id']] else 1
        self.assertEqual(third['win'], want, 'a tie goes to the better seed')

    def test_hp_breaks_a_duel_tie_before_the_seed(self):
        real = PW.team_match

        def hp(a, b, key, size=PW.SIZE):
            res = real(a, b, key, size)
            if key.endswith('-3-0'):
                res = dict(res, w=1, wa=2, wb=2, hp=[400, 600])   # team_match's own tie-break: b had more HP left
            return res
        with mock.patch.object(PW, 'team_match', hp):
            self.war(4)
        war, ms, lad = self.rows()
        self.assertEqual(ms[-1]['win'], 1)
        self.assertFalse(json.loads(ms[-1]['data'])['tie'])
        self.assertEqual(json.loads(war['data'])['third_team']['id'], ms[-1]['b_id'])

    def test_deterministic_and_fixed_at_the_lock(self):
        self.war(4)
        war, ms, lad = self.rows()
        third = ms[-1]
        d = json.loads(third['data'])
        self.assertEqual({x['seed'] for x in d['duels']}, {f'w{war["week"]}-3-0'}, 'its own key, as match_view replays it')
        # the same lineups and key give the same result (deterministic)
        mem = lambda side: [dict(sid=x[side]['sid'], name=x[side]['name'], f=x[side]['f']) for x in d['duels'] if x[side]]
        a, b = dict(kind='bang', id=third['a_id'], members=mem('a'), tb=0), dict(kind='bang', id=third['b_id'], members=mem('b'), tb=0)
        res = PW.team_match(a, b, f'w{war["week"]}-3-0')
        self.assertEqual((res['wa'], res['wb']), (third['wa'], third['wb']))
        # a pick changed after the lock changes nothing: the war is already stored
        with mock.patch.object(A, 'now', return_value=self.SAT + 1):
            with self.assertRaises(A.ArenaError):
                tok = self.tok_of(third['a_id'])
                self.op(tok, 'war_unpick')
        self.assertEqual(self.rows()[1], ms)


class OlderBuild(Base):
    """2.6.7 (before the 3rd-place match) reading a war played by this build: nothing crashes, no second final."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.old = {}
        for name in ('pet_war', 'lb_titles'):
            try:
                src = subprocess.run(['git', 'show', f'{OLD_REF}:game/{name}.py'], cwd=ROOT, capture_output=True, check=True).stdout
            except Exception:  # noqa: BLE001 - no git history here: the compatibility check is skipped
                continue
            spec = importlib.util.spec_from_loader(f'game._old_{name}', loader=None, origin=f'{OLD_REF}:game/{name}.py')
            mod = importlib.util.module_from_spec(spec)
            mod.__package__ = 'game'
            exec(compile(src.decode('utf-8'), f'{OLD_REF}:game/{name}.py', 'exec'), mod.__dict__)
            sys.modules[spec.name] = mod
            cls.old[name] = mod

    def test_old_build_reads_the_extra_row(self):
        if 'pet_war' not in self.old:
            self.skipTest('no git history')
        old = self.old['pet_war']
        self.assertFalse(hasattr(old, 'is_third'), 'really the old module')
        old.PROVIDERS = PW.PROVIDERS            # the same registered teams
        self.war(4)
        war, ms, lad = self.rows()
        third = ms[-1]
        end = PW.end_of(war) + 1
        with self.store.connect() as db:
            self.assertEqual(old.end_of(war), PW.end_of(war))
            for t in (self.SAT + 10, self.SAT + PW.SIZE * PW.DUEL_SECS + 1, end):
                c = old.team_card(db, 'bang', third['a_id'], self.sid(self.tok_of(third['a_id'])), t)
                names = [m['round'] for m in c['matches']]
                self.assertNotIn('Chung kết', names, 'a semi-final loser never sees a final')
            self.assertEqual(names, ['Bán kết', 'Vòng 3'])
            self.assertFalse(c['result']['second'], 'never runner-up')
            self.assertEqual(c['result']['round'], 'Bán kết')
            board = old.ladder(db, t=end)
            self.assertEqual(len(board), 4)
            self.assertEqual(old.standings(db, end), [x for x in PW.standings(db, end) if x[1] <= 10])
        with mock.patch.object(A, 'now', return_value=end):
            v = old.view(self.store, self.tok_of(third['a_id']))
            self.assertEqual([r['rd'] for r in v['rounds']], [1, 2], 'its bracket draws rounds 1…rounds only: the row is not drawn')
            self.assertEqual(sum(1 for b in v['bracket'] if b['rd'] in (1, 2)), 3)
            mv = old.match_view(self.store, self.tok_of(third['a_id']), dict(rd=3, slot=0))
            self.assertEqual(len(mv['duels']), 5)
        # its titles: ranks 11–15 hold nothing there (no tier), the weekly reward skips them, the holders too
        olt = self.old.get('lb_titles')
        if olt:
            self.assertIsNone(olt.tier_of('pet_war', 11))
            self.assertIsNone(olt.title_of('pet_war', 15))
            self.assertEqual(olt.reward_of('pet_war', 12), 0)
            self.assertEqual(len(olt.tiers_of('pet_war')), 2)

    def test_old_lb_rows_survive_this_build_and_back(self):
        """A frozen week written by this build (ranks 11–15) read by the old lb_titles: no crash, no reward, no title."""
        olt = self.old.get('lb_titles')
        if not olt:
            self.skipTest('no git history')
        with self.store.connect() as db:
            lbt._insert(db, '2026-W44', [('pet_war', 1, 'a' * 64, 2), ('pet_war', 11, 'b' * 64, 0)], 1, '2026-11-02', at(2026, 11, 2, 1))
            with mock.patch('game.player_feedback.admin_users', return_value=set()):
                n = olt.reward_week(db, '2026-W44', at(2026, 11, 2, 1))
            ids = {r['id'] for r in db.execute("SELECT id FROM system_gifts WHERE id LIKE 'lbw-2026-W44-%'").fetchall()}
        self.assertNotIn('lbw-2026-W44-pet_war-11', ids)
        self.assertLessEqual(n, 1)


if __name__ == '__main__':
    unittest.main()
