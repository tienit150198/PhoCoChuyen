"""🐾 Đấu trường pet (game/pet_battle.py, game/pet_arena.py, game/pet_cup.py, game/pet_war.py, owner 19/10): the engine is
deterministic and balanced (rank and gear matter, upsets happen), ranked battles move ratings and keep the anti-farm
rules (one network, the same two players, recent opponents, daily caps, a new account), friendly and practice fights,
the weekly season and its titles, the weekly Swiss cup, the bang war's 5-vs-5 bracket through a team provider, and no
battle ever writes a save (pets are never harmed)."""
import copy
import json
import random
import statistics
import unittest
from unittest import mock

from game import lb_titles as lbt
from game import pet_arena as A
from game import pet_battle as B
from game import pet_cup as PC
from game import pet_tiers as px
from game import pet_war as PW
from game import pets_content as C
from game.engine import validate_state
from tests.test_bank import act, story
from tests.test_leaderboard import Base
from tests.test_lb_titles import at

BREEDS = [b for b in C.ORDER if C.BREEDS[b]['fuse'] == '']


def rand_pet(R, rank, gear=None, train=0, el=None, kind=None):
    """A fighter like the ones the arena makes: a random breed, potential, its rank's range (+ a full kit of gear)."""
    breed = R.choice(BREEDS)
    br = C.BREEDS[breed]
    lo, hi = px.RANGE[rank]
    s = []
    for i in range(5):
        v = lo + (hi - lo) * R.randint(0, 100) // 100 + br['st'][i] + train
        if gear:
            v += px.GBASE[gear[0]] + px.GBASE[gear[0]] * gear[1] // 10
        s.append(max(1, v))
    return dict(n='Bé', b=breed, c=0, r=rank, k=kind or br['kind'], e=el or B.element_of(breed), s=s, pw=sum(s))


def win_rate(R, fa, fb, n):
    """a's share of wins (a draw counts half), each side attacking first half the time."""
    w = 0.0
    for i in range(n):
        a, b = fa(), fb()
        if i % 2:
            r = B.battle([b], [a], R.getrandbits(64))
            w += 1 if r['w'] == 1 else 0.5 if r['w'] == 2 else 0
        else:
            r = B.battle([a], [b], R.getrandbits(64))
            w += 1 if r['w'] == 0 else 0.5 if r['w'] == 2 else 0
    return w / n


class Engine(unittest.TestCase):
    def test_same_seed_same_battle(self):
        R = random.Random(1)
        a = [rand_pet(R, 3) for _ in range(3)]
        b = [rand_pet(R, 3) for _ in range(3)]
        keep = copy.deepcopy((a, b))
        one = B.battle(a, b, 12345)
        self.assertEqual(one, B.battle(copy.deepcopy(a), copy.deepcopy(b), 12345))
        self.assertEqual((a, b), keep, 'a battle never changes its fighters')
        self.assertEqual(B.seed_of('r00ff'), B.seed_of('r00ff'))
        self.assertNotEqual(B.seed_of('r00ff'), B.seed_of('r00fe'))
        logs = {json.dumps(B.battle(a, b, s)['ev']) for s in range(20)}
        self.assertGreater(len(logs), 15, 'another seed, another fight')

    def test_log_shape(self):
        R = random.Random(2)
        res = B.battle([rand_pet(R, 2), rand_pet(R, 2)], [rand_pet(R, 2)], 99)
        ev = res['ev']
        self.assertEqual(ev[0]['k'], 'in')
        self.assertEqual(ev[-1], dict(k='end', w=res['w']))
        kinds = {e['k'] for e in ev}
        self.assertTrue(kinds <= {'in', 'hit', 'sk', 'miss', 'ko', 'end'}, kinds)
        self.assertIn(res['w'], (0, 1, 2))
        self.assertEqual(len(res['hp'][0]), 2)
        for e in ev:
            if e['k'] in ('hit', 'sk'):
                self.assertGreaterEqual(e['h'], 0)
                self.assertGreaterEqual(e['d'], 0)
        # the loser has nobody standing, unless the clock ran out
        if res['w'] in (0, 1) and res['n'] < B.MAX_ACTIONS:
            self.assertEqual(res['left'][1 - res['w']], 0)

    def test_elements_and_skills(self):
        self.assertEqual(B.BEATS, dict(kim='moc', moc='tho', tho='thuy', thuy='hoa', hoa='kim'))
        self.assertEqual(set(B.SKILLS), set(B.ELEMENT_IDS))
        for bid in C.ORDER:
            self.assertIn(B.element_of(bid), B.ELEMENT_IDS, bid)
        self.assertEqual(B.element_of('than_tai'), 'kim')
        self.assertEqual(B.element_of('rong_con'), 'hoa')
        self.assertEqual(B.element_of('husky'), 'tho')       # leans to sức bền
        self.assertEqual(B.element_of('pom'), 'moc')         # leans to đáng yêu

    def test_bad_fighters_do_not_fight(self):
        self.assertIsNone(B.clean(dict(s=[1, 2])))
        self.assertIsNone(B.clean('x'))
        res = B.battle([dict(s='bad')], [], 1)
        self.assertEqual(res['w'], 2)


class Balance(unittest.TestCase):
    """Thousands of simulated 1-vs-1 battles of random pets: rank and gear matter, upsets happen."""
    N = 1500

    def test_ranks(self):
        R = random.Random(11)
        adj = [win_rate(R, lambda r=r: rand_pet(R, r + 1), lambda r=r: rand_pet(R, r), self.N) for r in range(6)]
        for r, x in enumerate(adj):
            self.assertTrue(0.62 <= x <= 0.86, (px.RANKS[r + 1], x))     # one rank up wins most, not all
        self.assertTrue(0.70 <= statistics.mean(adj) <= 0.80, adj)
        two = [win_rate(R, lambda r=r: rand_pet(R, r + 2), lambda r=r: rand_pet(R, r), self.N) for r in range(5)]
        for x in two:
            self.assertTrue(0.80 <= x <= 0.97, two)
        far = win_rate(R, lambda: rand_pet(R, 6), lambda: rand_pet(R, 0), 400)
        self.assertGreater(far, 0.97)
        same = win_rate(R, lambda: rand_pet(R, 3), lambda: rand_pet(R, 3), self.N * 2)
        self.assertTrue(0.46 <= same <= 0.54, same)

    def test_gear_training_elements_kinds(self):
        R = random.Random(12)
        kit = win_rate(R, lambda: rand_pet(R, 3, gear=(3, 0)), lambda: rand_pet(R, 3), self.N)
        self.assertTrue(0.68 <= kit <= 0.9, kit)
        up = win_rate(R, lambda: rand_pet(R, 3, gear=(3, 10)), lambda: rand_pet(R, 3, gear=(3, 0)), self.N)
        self.assertTrue(0.66 <= up <= 0.9, up)
        tr = win_rate(R, lambda: rand_pet(R, 3, train=10), lambda: rand_pet(R, 3), self.N)
        self.assertTrue(0.6 <= tr <= 0.8, tr)
        for a, b in B.BEATS.items():
            x = win_rate(R, lambda a=a: rand_pet(R, 3, el=a), lambda b=b: rand_pet(R, 3, el=b), 1200)
            self.assertTrue(0.54 <= x <= 0.8, (a, b, x))
        dc = win_rate(R, lambda: rand_pet(R, 3, kind='dog'), lambda: rand_pet(R, 3, kind='cat'), self.N * 2)
        self.assertTrue(0.45 <= dc <= 0.55, dc)

    def test_length_and_speed(self):
        import time
        R = random.Random(13)
        acts = [B.battle([rand_pet(R, 3)], [rand_pet(R, 3)], i)['n'] for i in range(400)]
        self.assertTrue(6 <= statistics.mean(acts) <= 18, statistics.mean(acts))   # short enough to watch on a phone
        t = time.perf_counter()
        for i in range(300):
            B.battle([rand_pet(R, 4) for _ in range(3)], [rand_pet(R, 4) for _ in range(3)], i)
        self.assertLess((time.perf_counter() - t) / 300, 0.01, 'a 3-vs-3 battle costs well under 10 ms')


def pet_save(names, wallet=500_000, rank=3, seed=4242):
    """A story save with pets bought at the shop, given `rank`."""
    s = story(wallet, seed)
    for i, nick in enumerate(names):
        s, _ = act(s, 'jr_pet_adopt', **{'from': 'shop'}, breed=('corgi', 'meo_mun', 'husky', 'pom')[i % 4], coat=0, nick=nick, confirm=True)
        p = next(q for q in px.all_pets(s) if q['n'] == nick)
        s['journey']['petx']['t'][p['id']]['r'] = rank
        s['journey']['petx']['t'][p['id']]['fx'] = px.FX[0][0] if rank == px.TOP else ''
    validate_state(s)
    return s


class Store(Base):
    def setUp(self):
        super().setUp()
        self.n_acc = 0
        lbt.clear_cache()
        lbt._done.clear()

    def arena(self, names=('Mít', 'Na'), rank=3, account=None, old=True, seed=None):
        self.n_acc += 1
        tok = self.player(pet_save(names, rank=rank, seed=seed or 4000 + self.n_acc), account=account or f'Người {self.n_acc}')
        if old:
            self.age(tok)
        return tok

    def age(self, tok, days=3):
        def w(db):
            db.execute("UPDATE accounts SET created_at='2020-01-01 00:00:00' WHERE sid=?", (self.sid(tok),))
        self.store.transaction(w)

    def op(self, tok, op, ip='1.1.1.1', **data):
        state = self.store.read(tok)[0] if op not in A.LIGHT else None
        return A.act(self.store, tok, op, data, state, ip)

    def row(self, tok):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM pet_arena WHERE sid=?', (self.sid(tok),)).fetchone())


class Arena(Store):
    def test_view_lineup_and_snapshot(self):
        a = self.arena(('Mít', 'Na', 'Bơ'))
        v = self.op(a, 'view')
        self.assertEqual(len(v['team']), 3)
        self.assertEqual(v['me']['rating'], A.START)
        st = self.store.read(a)[0]
        p = px.all_pets(st)[0]
        f = A.fighter(st, p)
        self.assertEqual(f['s'], px.stats(st, p))
        self.assertIn(f['e'], B.ELEMENT_IDS)
        one = v['pets'][1]['id']
        out = self.op(a, 'lineup', pets=[one])
        self.assertIn('Đã xếp đội', out['message'])
        self.assertEqual(A._j(self.row(a)['lineup'], []), [one])
        with self.assertRaises(A.ArenaError):
            self.op(a, 'lineup', pets=['p999'])
        with self.assertRaises(A.ArenaError):
            self.op(a, 'lineup', pets=[one, one])

    def test_locked_without_account_story_or_pet(self):
        tok = self.player(story(500))
        self.assertEqual(self.op(tok, 'view')['locked'], 'account')
        tok2 = self.player(story(500), account='Không bé')
        self.assertEqual(self.op(tok2, 'view')['locked'], 'pet')
        with self.assertRaises(A.ArenaError) as cm:
            self.op(tok2, 'fight')
        self.assertEqual(cm.exception.code, 'no_pet')

    def test_ranked_fight_moves_ratings_and_never_touches_a_save(self):
        a, b = self.arena(), self.arena()
        self.op(b, 'view', ip='2.2.2.2')
        before = {t: self.store.read(t) for t in (a, b)}
        out = self.op(a, 'fight')['match']
        self.assertEqual(out['kind'], 'rank')
        self.assertEqual(out['me'], 0)
        self.assertEqual(out['sides'][1]['name'], 'Người 2')
        self.assertTrue(out['ev'])
        ra, rb = self.row(a), self.row(b)
        self.assertEqual(ra['rating'], A.START + out['da'])
        self.assertEqual(rb['rating'], A.START + out['db'])
        if out['w'] == 0:
            self.assertGreater(out['da'], 0)
            self.assertLess(out['db'], 0)
            self.assertEqual(out['da'], 16)                       # K_ATT 32 × (1 − 0.5)
            self.assertEqual(out['db'], -8)                       # K_DEF 16
        # the replay is the same fight
        rep = self.op(b, 'replay', id=out['id'])['match']
        self.assertEqual(rep['ev'], out['ev'])
        self.assertEqual(rep['me'], 1)
        for t in (a, b):   # 🐾 never harmed: the saves are exactly as they were (no revision moved)
            self.assertEqual(self.store.read(t), before[t])
        self.assertNotIn(self.sid(a), json.dumps(rep))
        self.assertNotIn(self.sid(b), json.dumps(rep))

    def test_same_network_never_meets_and_spar_instead(self):
        a, b = self.arena(), self.arena()
        self.op(b, 'view', ip='9.9.9.9')
        out = self.op(a, 'fight', ip='9.9.9.9')['match']
        self.assertEqual(out['kind'], 'spar')                     # Bé nhà Mây, unrated
        self.assertEqual(self.row(a)['rating'], A.START)
        self.assertIn('Bé nhà Mây', out['sides'][1]['name'])

    def test_recent_and_daily_cap(self):
        a, b, c = self.arena(), self.arena(), self.arena()
        for t, ip in ((b, '2.0.0.1'), (c, '3.0.0.1')):
            self.op(t, 'view', ip=ip)
        two = {self.op(a, 'fight')['match']['sides'][1]['name'] for _ in range(2)}
        self.assertEqual(two, {'Người 2', 'Người 3'})
        third = self.op(a, 'fight')['match']   # RECENT 3: two opponents in all, both met just now
        self.assertEqual(third['kind'], 'spar', 'the last RECENT opponents are not met again at once')
        with mock.patch.object(A, 'RANK_DAY', 3):
            with self.assertRaises(A.ArenaError) as cm:
                self.op(a, 'fight')
            self.assertEqual(cm.exception.code, 'limit')

    def test_pair_limit(self):
        a, b, c = self.arena(), self.arena(), self.arena()
        for t, ip in ((b, '2.0.0.1'), (c, '3.0.0.1')):
            self.op(t, 'view', ip=ip)
        with mock.patch.object(A, 'RECENT', 1):
            opp = [self.op(a, 'fight')['match']['sides'][1]['name'] for _ in range(4)]
            self.assertEqual(sorted(opp[:2]), ['Người 2', 'Người 3'])            # the last opponent is not met again at once
            self.assertEqual(opp[2:], opp[:2])
            fifth = self.op(a, 'fight')['match']
            self.assertEqual(fifth['kind'], 'spar', 'both met PAIR_DAY times today: nobody fits')
            # the defender attacking back counts too
            self.assertEqual(self.op(b, 'fight', ip='2.0.0.1')['match']['sides'][1]['name'], 'Người 3')
        with mock.patch.object(A, 'RANK_DAY', 5):
            with self.assertRaises(A.ArenaError) as cm:
                self.op(a, 'fight')
            self.assertEqual(cm.exception.code, 'limit')

    def test_new_account_and_blocks(self):
        a = self.arena(old=False)
        b = self.arena()
        self.op(b, 'view', ip='4.4.4.4')
        with self.assertRaises(A.ArenaError) as cm:
            self.op(a, 'fight')
        self.assertEqual(cm.exception.code, 'too_new')
        self.age(a)

        def block(db):
            db.execute('INSERT INTO blocks(pid, target, at) VALUES(?,?,?)', (A.pid_of(self.sid(a)), A.pid_of(self.sid(b)), 1.0))
        try:
            self.store.transaction(block)
        except Exception:   # noqa: BLE001 - an older blocks table shape: the marriage blocks then
            def mblock(db):
                db.execute('INSERT INTO marriage_blocks(sid, target, at) VALUES(?,?,?)', (self.sid(a), self.sid(b), 1.0))
            self.store.transaction(mblock)
        self.assertEqual(self.op(a, 'fight')['match']['kind'], 'spar')

    def test_friend_fight_is_unrated(self):
        a, b, c = self.arena(), self.arena(), self.arena()
        self.op(b, 'view')

        def befriend(db):
            for x, y in ((a, b), (b, a)):
                db.execute('INSERT INTO friends(sid, friend, since) VALUES(?,?,?)', (self.sid(x), self.sid(y), 1.0))
        self.store.transaction(befriend)
        fl = self.op(a, 'friends')['friends']
        self.assertEqual([f['name'] for f in fl], ['Người 2'])
        out = self.op(a, 'friend', pid=fl[0]['pid'])['match']
        self.assertEqual(out['kind'], 'friend')
        self.assertEqual((self.row(a)['rating'], self.row(b)['rating']), (A.START, A.START))
        self.op(c, 'view')
        with self.assertRaises(A.ArenaError) as cm:
            self.op(a, 'friend', pid=A.pid_of(self.sid(c)))
        self.assertEqual(cm.exception.code, 'not_friend')

    def test_npc_stars_once_a_stage_a_day(self):
        a = self.arena(rank=6)
        v = self.op(a, 'view')
        self.assertEqual([x['name'] for x in v['npc']], ['Dễ', 'Vừa', 'Khó'])
        self.assertLess(v['npc'][0]['pw'], v['npc'][2]['pw'])
        self.assertEqual(v['npc'], self.op(a, 'view')['npc'], 'the same lineups all day')
        stars = 0
        for _ in range(4):
            out = self.op(a, 'npc', stage=0)['match']
            stars += out['star']
        self.assertLessEqual(stars, 1)
        with mock.patch.object(A, 'NPC_DAY', 4):
            with self.assertRaises(A.ArenaError):
                self.op(a, 'npc', stage=1)

    def test_snapshot_follows_training(self):
        a = self.arena(('Mít',))
        self.op(a, 'view')
        before = A._j(self.row(a)['snap'], [])[0]['s']
        st = self.store.read(a)[0]
        pid = px.all_pets(st)[0]['id']
        self.cmd(a, 'jr_pet_train', {'pet': pid, 'stat': 'spd'})
        after = A._j(self.row(a)['snap'], [])[0]['s']
        self.assertEqual(after[0], before[0] + px.TRAIN_STEP)

    def test_season_ladder_and_titles(self):
        toks = [self.arena() for _ in range(5)]
        for i, t in enumerate(toks):
            self.op(t, 'view', ip=f'10.0.0.{i}')
        with mock.patch.object(A, 'MIN_GAMES', 2), mock.patch.object(A, 'MIN_OPP', 2):
            for _ in range(3):
                self.op(toks[0], 'fight', ip='10.0.0.0')
            lad = self.op(toks[0], 'ladder')
            self.assertEqual([r['me'] for r in lad['top']][:1], [True])
            with self.store.connect() as db:
                rows = A.standings(db, A.now(), 10)
            self.assertEqual(rows[0][:3], ('arena', 1, self.sid(toks[0])))
            # the daily refresh of the weekly titles takes it (game/lb_titles.py)
            lbt.ensure(self.store)   # (the ladder view above already ran today's refresh)
            lbt.clear_cache()
            mine = lbt.held(self.store, self.sid(toks[0]))
            self.assertIn(('arena', 1), [(h['board'], h['rank']) for h in mine])
            self.assertEqual(next(h for h in mine if h['board'] == 'arena')['text'], '🏆 Vua đấu trường tuần')
        self.assertEqual(lbt.title_of('arena', 1)['text'], '🏆 Vua đấu trường tuần')
        self.assertEqual(lbt.title_of('pet_cup', 2)['name'], 'Top 3 giải pet tuần')
        self.assertIn('arena', lbt.MAIN)

    def test_season_pulls_halfway_back(self):
        a = self.arena()
        self.op(a, 'view')

        def w(db):
            db.execute('UPDATE pet_arena SET rating=1400 WHERE sid=?', (self.sid(a),))
            db.execute('DELETE FROM pet_arena_season WHERE sid=?', (self.sid(a),))
        self.store.transaction(w)
        self.assertEqual(self.op(a, 'view')['me']['rating'], 1200)

    def test_forget(self):
        a = self.arena()
        self.op(a, 'view')
        self.store.delete(a)
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM pet_arena WHERE sid=?', (self.sid(a),)).fetchone())


class Cup(Store):
    def test_swiss_cup(self):
        toks = [self.arena(rank=r) for r in (1, 2, 3, 4, 5, 6)]
        sun = at(2026, 10, 25, 21, 0)
        with mock.patch.object(A, 'now', return_value=at(2026, 10, 21, 12)):
            for i, t in enumerate(toks):
                self.op(t, 'view', ip=f'20.0.0.{i}')
                self.assertTrue(self.op(t, 'cup_join')['joined'])
            self.assertFalse(PC.run_due(self.store, at(2026, 10, 21, 12)))
            self.assertEqual(self.op(toks[0], 'view')['cup']['n'], 6)
        week = A.vn_week(sun)
        with mock.patch.object(A, 'now', return_value=sun + 60):
            with self.assertRaises(A.ArenaError):
                self.op(toks[0], 'cup_join')
            self.assertTrue(PC.run_due(self.store, sun + 60))
            self.assertFalse(PC.run_due(self.store, sun + 90), 'once')
            board = self.op(toks[5], 'cup_board')
        self.assertEqual(board['cup']['status'], 'done')
        self.assertEqual(board['cup']['rounds'], 3)
        self.assertEqual([r['rank'] for r in board['top']], [1, 2, 3, 4, 5, 6])
        self.assertEqual(len(board['matches']), 3)
        with self.store.connect() as db:
            rows = db.execute("SELECT a, b FROM pet_arena_matches WHERE week=? AND kind='cup'", (week,)).fetchall()
            self.assertEqual(len(rows), 9)
            pairs = [frozenset((r['a'], r['b'])) for r in rows]
            self.assertEqual(len(pairs), len(set(pairs)), 'no rematch')
            st = PC.standings(db, 10)
        self.assertEqual([x[1] for x in st], [1, 2, 3, 4, 5, 6])
        # the strongest lineup is usually on top; at least it is in the top half
        self.assertIn(self.sid(toks[5]), [x[2] for x in st[:3]])

    def test_too_few_is_cancelled(self):
        toks = [self.arena() for _ in range(2)]
        with mock.patch.object(A, 'now', return_value=at(2026, 10, 20, 12)):
            for t in toks:
                self.op(t, 'cup_join')
        self.assertTrue(PC.run_due(self.store, at(2026, 10, 25, 21, 5)))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM pet_cup').fetchone()['status'], 'cancelled')

    def test_pairing_avoids_a_rematch_greedy_would_force(self):
        mk = lambda sid, *met: dict(sid=sid, opps=list(met))
        order = [mk('A', 'C'), mk('B'), mk('C', 'A', 'D'), mk('D', 'C')]
        got = [(p['sid'], q['sid']) for p, q in PC.pair_round(order)]
        self.assertEqual(got, [('A', 'D'), ('B', 'C')])     # greedy: A–B, then C–D again
        order = [mk('A', 'B'), mk('B', 'A')]
        self.assertEqual([(p['sid'], q['sid']) for p, q in PC.pair_round(order)], [('A', 'B')], 'no way out: the rematch')

    def test_rounds(self):
        self.assertEqual([PC.rounds_for(n) for n in (4, 5, 8, 9, 16, 100, 1024)], [3, 3, 3, 4, 4, 7, 7])


class Teams(PW.TeamProvider):
    """A test provider: teams from a dict sid -> (team id, name), a training ground level per team."""
    label = 'Bang'

    def __init__(self, of, levels=None):
        self.of, self.levels = of, levels or {}

    def team_of(self, db, sid):
        return self.of.get(sid)

    def name(self, db, tid):
        return tid

    def facility(self, db, tid, key):
        return self.levels.get(tid, 0) if key == PW.TRAINING_KEY else 0


class War(Store):
    SAT = at(2026, 10, 24, 21, 0)

    def setUp(self):
        super().setUp()
        self.addCleanup(PW.unregister, 'bang')

    def test_team_match_api(self):
        R = random.Random(3)
        mk = lambda n, r: [dict(sid=f's{i}', name=f'P{i}', f=rand_pet(R, r)) for i in range(n)]
        a, b = dict(kind='bang', id='a', members=mk(5, 5)), dict(kind='bang', id='b', members=mk(3, 5))
        one = PW.team_match(a, b, 'k1')
        self.assertEqual(one, PW.team_match(copy.deepcopy(a), copy.deepcopy(b), 'k1'), 'deterministic')
        self.assertEqual(len(one['duels']), 5)
        missing = [d for d in one['duels'] if d['b'] is None]
        self.assertEqual(len(missing), 2)
        self.assertTrue(all(d['w'] == 0 for d in missing), 'a missing pet loses its duel')
        self.assertEqual(one['wa'] + one['wb'] + sum(d['w'] == 2 for d in one['duels']), 5)
        orders = {tuple(d['a']['sid'] for d in PW.team_match(a, b, f'k{i}')['duels']) for i in range(10)}
        self.assertGreater(len(orders), 3, 'the order is shuffled from the seed')
        self.assertEqual(PW.seed_order(8), [1, 8, 4, 5, 2, 7, 3, 6])

    def test_war_bracket_titles_and_views(self):
        toks = [self.arena(('Mít',), rank=r) for r in (2, 3, 4, 5, 6, 2, 3)]
        sids = [self.sid(t) for t in toks]
        team = {sids[0]: ('A', 'Bang A'), sids[1]: ('A', 'Bang A'), sids[2]: ('B', 'Bang B'), sids[3]: ('B', 'Bang B'),
                sids[4]: ('C', 'Bang C'), sids[5]: ('C', 'Bang C'), sids[6]: ('C', 'Bang C')}
        PW.register('bang', Teams(team, {'C': 3}))
        wed = at(2026, 10, 21, 12)
        with mock.patch.object(A, 'now', return_value=wed):
            for t in toks:
                st = self.store.read(t)[0]
                out = self.op(t, 'war_pick', pet=px.all_pets(st)[0]['id'])
                self.assertIn('ra trận', out['message'])
            v = self.op(toks[0], 'war')
            self.assertEqual(v['phase'], 'pick')
            self.assertEqual(v['team']['name'], 'Bang A')
            self.assertEqual(len(v['picks']), 2)
            self.assertEqual(self.op(toks[4], 'view')['war']['pick']['n'], 'Mít')
        with mock.patch.object(A, 'now', return_value=self.SAT - 5 * 60):   # locked
            with self.assertRaises(A.ArenaError) as cm:
                self.op(toks[0], 'war_unpick')
            self.assertEqual(cm.exception.code, 'locked')
            self.assertTrue(PW.run_due(self.store, self.SAT - 5 * 60))
            self.assertFalse(PW.run_due(self.store, self.SAT - 4 * 60))
            v = self.op(toks[0], 'war')
            self.assertEqual(v['phase'], 'live')
            self.assertTrue(all(m['state'] == 'wait' for m in v['bracket']))
            self.assertTrue(all(m['a'] == '' for m in v['bracket'] if m['rd'] > 1), 'later rounds unknown yet')
            with self.assertRaises(A.ArenaError):
                self.op(toks[0], 'war_match', rd=1, slot=0)
        with self.store.connect() as db:
            war = db.execute('SELECT * FROM pet_war').fetchone()
            self.assertEqual((war['status'], war['n'], war['rounds']), ('done', 3, 2))
            data = json.loads(war['data'])
            self.assertEqual(data['teams'][0]['tb'] if data['teams'][0]['id'] == 'C' else next(x['tb'] for x in data['teams'] if x['id'] == 'C'), 3)
            ms = db.execute('SELECT * FROM pet_war_matches ORDER BY rd, slot').fetchall()
        self.assertEqual(len(ms), 3)                      # a bye, a semi-final, the final
        self.assertEqual(sum(1 for m in ms if not m['b_name']), 1)
        final = ms[-1]
        self.assertEqual(final['rd'], 2)
        self.assertEqual(final['wa'] + final['wb'] + sum(d['w'] == 2 for d in json.loads(final['data'])['duels']), 5)
        # watching the first real match: duels one by one
        semi = next(m for m in ms if m['rd'] == 1 and m['b_name'])
        with mock.patch.object(A, 'now', return_value=semi['start'] + PW.DUEL_SECS + 1):
            mv = self.op(toks[0], 'war_match', rd=1, slot=semi['slot'])
            self.assertEqual(len(mv['duels']), 2)
            self.assertFalse(mv['over'])
            self.assertNotIn('win', mv)
        with mock.patch.object(A, 'now', return_value=semi['start'] + PW.SIZE * PW.DUEL_SECS + 1):
            mv = self.op(toks[0], 'war_match', rd=1, slot=semi['slot'])
            self.assertEqual(len(mv['duels']), 5)
            self.assertTrue(mv['over'])
            vacant = [d for d in mv['duels'] if not d['sides'][0]['pets'] or not d['sides'][1]['pets']]
            self.assertEqual(len(vacant), 3, 'two pets a side at most here: three duels without a pet')
        end = self.SAT + PW.GAP + PW.SIZE * PW.DUEL_SECS + 1
        with mock.patch.object(A, 'now', return_value=end):
            v = self.op(toks[0], 'war')
            self.assertEqual(v['phase'], 'done')
            self.assertTrue(v['champ'])
            self.assertTrue(all(m['state'] == 'done' for m in v['bracket']))
            self.assertEqual(len(v['ladder']), 3)
            self.assertEqual(v['ladder'][0]['name'], v['champ'])
        with self.store.connect() as db:
            st = PW.standings(db, end)
            self.assertEqual(PW.standings(db, self.SAT), [], 'no title before the war is over')
        champ_team = v['ladder'][0]['id']
        champs = [s for s, (tid, _) in team.items() if tid == champ_team]
        self.assertEqual(sorted(x[2] for x in st if x[1] <= 5), sorted(champs))
        self.assertTrue(all(lbt.tier_of('pet_war', x[1]) == (0 if x[1] <= 5 else 1) for x in st))
        self.assertEqual(lbt.title_of('pet_war', 5)['text'], '🏆 Bang vô địch đấu pet')
        self.assertEqual(lbt.title_of('pet_war', 6)['label'], 'Bang á quân')
        self.assertIsNone(lbt.title_of('pet_war', 11))
        with self.store.connect() as db:
            self.assertEqual(PW.team_rating(db, 'bang', champ_team)['titles'], 1)

    def test_five_a_team_and_unpick(self):
        toks = [self.arena(('Mít',)) for _ in range(6)]
        PW.register('bang', Teams({self.sid(t): ('A', 'Bang A') for t in toks}))
        with mock.patch.object(A, 'now', return_value=at(2026, 10, 21, 12)):
            for t in toks[:5]:
                self.op(t, 'war_pick', pet=px.all_pets(self.store.read(t)[0])[0]['id'])
            with self.assertRaises(A.ArenaError) as cm:
                self.op(toks[5], 'war_pick', pet=px.all_pets(self.store.read(toks[5])[0])[0]['id'])
            self.assertEqual(cm.exception.code, 'full')
            self.op(toks[0], 'war_unpick')
            self.op(toks[5], 'war_pick', pet=px.all_pets(self.store.read(toks[5])[0])[0]['id'])
        PW.unregister('bang')
        with self.assertRaises(A.ArenaError) as cm:
            with mock.patch.object(A, 'now', return_value=at(2026, 10, 21, 12)):
                self.op(toks[0], 'war_pick', pet='p1')
        self.assertEqual(cm.exception.code, 'no_team')

    def test_one_team_is_cancelled(self):
        toks = [self.arena(('Mít',)) for _ in range(2)]
        PW.register('bang', Teams({self.sid(t): ('A', 'Bang A') for t in toks}))
        with mock.patch.object(A, 'now', return_value=at(2026, 10, 21, 12)):
            for t in toks:
                self.op(t, 'war_pick', pet=px.all_pets(self.store.read(t)[0])[0]['id'])
        self.assertTrue(PW.run_due(self.store, self.SAT))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM pet_war').fetchone()['status'], 'cancelled')


class English(unittest.TestCase):
    def test_main_words(self):
        from pathlib import Path
        en = json.loads((Path(__file__).resolve().parents[1] / 'public' / 'i18n' / 'en.json').read_text(encoding='utf-8'))['strings']
        for vi in ('Đấu trường pet', '⚔️ Tìm đối thủ', '🛡️ Bang chiến pet', 'Vua đấu trường tuần', 'Bang vô địch đấu pet', 'Cầu lửa',
                   'Luật đấu', 'Nhánh đấu', '🎉 Thắng rồi!', 'Trận gần đây', 'Vào một bang để cùng ra trận nhé.'):
            self.assertTrue(en.get(vi), vi)
        for title in [n for tiers in (lbt.BOARD_TITLES[b] for b in ('arena', 'pet_cup', 'pet_war')) for _, n in tiers]:
            self.assertTrue(en.get(title), title)


class Schema(unittest.TestCase):
    def test_additive(self):
        from game import pg_schema
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 58)
        ddl = pg_schema.TABLES_DDL
        i = ddl.index('CREATE TABLE IF NOT EXISTS pet_arena (')
        part = ddl[i:ddl.index('-- ', ddl.index('pet_team_rating')) if '-- ' in ddl[ddl.index('pet_team_rating'):] else len(ddl)]
        self.assertNotIn('DROP', part.upper())
        self.assertNotIn('ALTER', part.upper())
        for t in ('pet_arena', 'pet_arena_season', 'pet_arena_matches', 'pet_cup', 'pet_cup_entries', 'pet_war', 'pet_war_picks',
                  'pet_war_matches', 'pet_team_ladder', 'pet_team_rating'):
            self.assertIn(t, pg_schema.TABLE)


if __name__ == '__main__':
    unittest.main()
