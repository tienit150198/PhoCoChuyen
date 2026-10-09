"""🚔 Báo công an (game/review_police.py; owner 09/10: "cho phép người dân báo công an nhé, báo công an thì sẽ có tỷ
lệ được tăng * nếu đánh giá của NPC vô lý, và có khi được cộng tiền nữa nhé"): a vô lý NPC review (stars below what
the job earned) may get its stars back and sometimes a bồi thường in the wallet; a fair one is kept at no cost; once
per review, a few a day, recent NPC reviews only; no chance ever reaches the client; saves still load on 1.9.27."""
import copy
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import engine, feedback as F, review_police as R
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey
from tests.test_feedback_reviews import find

ROOT = Path(__file__).resolve().parents[1]
OLD_RELEASE = '4533ee17'   # 1.9.27, the release this one may be rolled back to
CARE_RELEASE = 'a9777863'  # 1.9.28: a care card touched by the police still loads there


class Base(unittest.TestCase):
    career = 'milk_tea'

    def setUp(self):
        self.j = Journey(self.career)
        self.j.c['day'] = 15

    def post(self, stars=None, fair=None, kind='plain', day=None):
        t = find(kind)
        t = dict(t, id=f"{t['id']}-{len(self.j.c['feed'])}")
        made = F.make_review(self.j.state, dict(self.j.c, career='milk_tea'), t, 'completed')
        p = engine.add_feed(self.j.state, self.j.c, f'{self.career}_npc_01', made['text'], t['id'], made['stars'], 'review')
        F.attach(p, made)
        fb = p['feedback']
        fb['status'] = 'open'
        if stars is not None:
            p['stars'] = fb['stars_original'] = stars
        if fair is not None:
            fb['fair'] = fair
        if day is not None:
            p['day'] = day
        return p

    def get(self, pid):
        return next(p for p in self.j.c['feed'] if p['id'] == pid)

    def public(self, pid=None):
        room = public_state(self.j.state)['careers'][self.career]
        return room if pid is None else next(p for p in room['feed'] if p['id'] == pid)['feedback']

    def cop(self, pid):
        return self.j.act('fb_cop', post=pid)

    def wallet(self):
        return self.j.state['journey']['wallet']


class Verdicts(Base):
    def test_unfair_review_confirmed_raises_the_stars_and_the_average(self):
        p = self.post(2, 5)
        before = self.public()['rating']
        with mock.patch.object(R, 'CONFIRM_PCT', 100), mock.patch.object(R, 'PAY_PCT', 0):
            r = self.cop(p['id'])
        p = self.get(p['id'])
        self.assertEqual((r['cop'], r['stars'], r['paid']), ('raised', 5, 0))
        self.assertIn('⭐⭐⭐⭐⭐', r['message'])
        self.assertIn('★2 → ★5', r['message'])
        self.assertEqual(p['stars'], 5)
        self.assertEqual(p['feedback']['cop'], dict(day=15, verdict='raised', before=2, after=5, pay=0))
        self.assertEqual(p['feedback']['status'], 'closed')
        room = self.public()
        stars = [x['stars'] for x in room['feed'] if x.get('stars')]
        self.assertEqual(room['rating'], round(sum(stars) / len(stars), 1))
        self.assertGreater(room['rating'], before)
        self.assertEqual(room['feedback_stats']['improved'], 0)     # the police, not the reviewer
        self.assertEqual(F.day_summary(self.j.c, 15)['average'], room['rating'])
        f = self.public(p['id'])
        self.assertEqual(f['cop']['verdict'], 'raised')
        self.assertFalse(f['can_cop'])
        validate_state(json.loads(json.dumps(self.j.state)))

    def test_compensation_goes_to_the_wallet_with_a_so_vi_row(self):
        p = self.post(1, 4)
        w = self.wallet()
        with mock.patch.object(R, 'CONFIRM_PCT', 100), mock.patch.object(R, 'PAY_PCT', 100):
            r = self.cop(p['id'])
        self.assertEqual(r['cop'], 'raised')
        self.assertTrue(R.PAY_BASE <= r['paid'] <= R.PAY_MAX)
        self.assertEqual(self.wallet() - w, r['paid'])
        self.assertIn(f"+{r['paid']} xu bồi thường", r['message'])
        row = self.j.state['journey']['history'][-1]
        self.assertEqual((row['kind'], row['amount'], row['career']), ('incident', r['paid'], self.career))
        self.assertTrue(row['label'].startswith('🚔 Bồi thường'))
        self.assertEqual(self.get(p['id'])['feedback']['cop']['pay'], r['paid'])
        validate_state(json.loads(json.dumps(self.j.state)))

    def test_compensation_only_sometimes_and_confirmation_not_always(self):
        seen = {'raised': 0, 'unproven': 0, 'pay': 0}
        pays = set()
        for i in range(400):
            p = dict(id=f'post-{i}', day=15, stars=2, kind='review', npc='milk_tea_npc_01',
                     feedback=dict(fair=4, thread=[], task=f'task-{i}'))
            v, after, pay = R.verdict(p)
            self.assertEqual(R.verdict(p), (v, after, pay))      # seeded: a retry never rolls again
            seen[v] += 1
            if pay:
                seen['pay'] += 1
                pays.add(pay)
        self.assertGreater(seen['raised'], 400 * 0.45)
        self.assertGreater(seen['unproven'], 400 * 0.25)
        self.assertGreater(seen['pay'], 0)
        self.assertLess(seen['pay'], seen['raised'] * 0.5)
        self.assertTrue(all(R.PAY_BASE <= x <= R.PAY_MAX for x in pays))

    def test_unproven_changes_nothing(self):
        p = self.post(2, 5)
        w, stars = self.wallet(), p['stars']
        with mock.patch.object(R, 'CONFIRM_PCT', 0):
            r = self.cop(p['id'])
        self.assertEqual(r['cop'], 'unproven')
        self.assertIn('chưa đủ cơ sở', r['message'])
        self.assertEqual((self.get(p['id'])['stars'], self.wallet()), (stars, w))
        self.assertEqual(self.get(p['id'])['feedback']['status'], 'open')

    def test_fair_review_is_rejected_at_no_cost(self):
        p = self.post(3, 3)
        w, rel = self.wallet(), self.j.c['relationships'].get(p['npc'], 0)
        with mock.patch.object(R, 'CONFIRM_PCT', 100), mock.patch.object(R, 'PAY_PCT', 100):
            r = self.cop(p['id'])
        self.assertEqual((r['cop'], r['stars'], r['paid']), ('fair', 3, 0))
        self.assertIn('hợp lý', r['message'])
        self.assertEqual((self.get(p['id'])['stars'], self.wallet(), self.j.c['relationships'].get(p['npc'], 0)), (3, w, rel))

    def test_lowered_after_the_players_rude_reply_is_fair(self):
        p = self.post(2, 4)
        p['feedback']['thread'] = [dict(role='owner', text='Không thích thì đi chỗ khác.', day=15, offer='none'),
                                   dict(role='customer', text='Hạ sao.', day=15, decision='revise_down', stars=2, mode='scripted')]
        p['feedback']['rounds'] = 1
        p['feedback']['stars_original'] = 3
        self.assertIsNone(R.target(p))
        with mock.patch.object(R, 'CONFIRM_PCT', 100):
            self.assertEqual(self.cop(p['id'])['cop'], 'fair')

    def test_real_unfair_rolls_are_vo_ly(self):
        for kind in ('unfair', 'flip_low', 'demand'):
            p = self.post(kind=kind)
            self.assertLess(p['stars'], p['feedback']['fair'], kind)
            self.assertEqual(R.target(p), p['feedback']['fair'], kind)
        p = self.post(kind='plain')
        p['stars'] = p['feedback']['fair'] = 4
        self.assertIsNone(R.target(p))


class Limits(Base):
    def test_once_per_review(self):
        p = self.post(2, 5)
        with mock.patch.object(R, 'CONFIRM_PCT', 0):
            self.cop(p['id'])
        before = copy.deepcopy(self.j.state)
        with mock.patch.object(R, 'CONFIRM_PCT', 100):
            with self.assertRaisesRegex(GameError, 'đã báo công an'):
                self.cop(p['id'])
        self.assertEqual(self.j.state, before)
        self.assertFalse(self.public(p['id'])['can_cop'])

    def test_daily_limit(self):
        posts = [self.post(3, 3) for _ in range(R.COP_PER_DAY + 1)]
        self.assertEqual(self.public()['feedback_stats']['cop_left'], R.COP_PER_DAY)
        for p in posts[:R.COP_PER_DAY]:
            self.cop(p['id'])
        self.assertEqual(self.public()['feedback_stats']['cop_left'], 0)
        with self.assertRaisesRegex(GameError, 'đủ 3 lần'):
            self.cop(posts[-1]['id'])
        self.j.c['day'] += 1
        self.assertEqual(self.cop(posts[-1]['id'])['cop'], 'fair')

    def test_only_recent_npc_reviews(self):
        old = self.post(2, 5, day=15 - R.COP_DAYS)
        self.assertFalse(self.public(old['id'])['can_cop'])
        with self.assertRaisesRegex(GameError, 'ngày gần đây'):
            self.cop(old['id'])
        edge = self.post(2, 5, day=15 - R.COP_DAYS + 1)
        self.assertTrue(self.public(edge['id'])['can_cop'])

    def test_not_the_players_own_posts_nor_plain_event_reviews(self):
        mine = engine.add_feed(self.j.state, self.j.c, 'player', 'Hôm nay tiệm mở cửa sớm!', 'x', None, 'post')
        event = engine.add_feed(self.j.state, self.j.c, 'milk_tea_npc_02', 'Chờ hơi lâu.', 'x', 2, 'review')
        for p in (mine, event):
            with self.assertRaises(GameError):
                self.cop(p['id'])
        self.assertNotIn('can_cop', next(x for x in self.public()['feed'] if x['id'] == event['id']))
        with self.assertRaises(GameError):
            self.cop('post-999999')

    def test_not_another_workplaces_review(self):
        p = self.post(2, 5)
        other = Journey('mother_baby')
        other.c['day'] = 15
        with self.assertRaises(GameError):
            other.act('fb_cop', post=p['id'])

    def test_five_stars_removed_awaiting_pile_on_and_threats_are_not_offered(self):
        five = self.post(5, 5)
        removed = self.post(1, 5)
        removed['feedback'].update(report='accepted', report_day=15, removed_stars=1, status='closed')
        removed['stars'] = None
        waiting = self.post(2, 5)
        waiting['feedback'].update(status='awaiting', pending=dict(decision='keep', stars=2, text='Ừ.', turn=1))
        pile = self.post(1, 1)
        pile['feedback']['twist'] = dict(kind='pile_on', reportable=True)
        threat = self.post(1, 5)
        threat['feedback']['twist'] = dict(kind='bocphot', reportable=False)
        for p in (five, removed, waiting, pile, threat):
            self.assertFalse(self.public(p['id'])['can_cop'], p['feedback'].get('twist'))
            with self.assertRaises(GameError):
                self.cop(p['id'])
        self.j.act('fb_police', post=threat['id'], confirm=True)
        self.assertTrue(self.public(threat['id'])['can_cop'])     # the threat is filed: now the stars can be checked

    def test_unfair_review_shows_the_button(self):
        p = self.post(kind='unfair')
        self.assertTrue(self.public(p['id'])['can_cop'])


class Pagoda(Base):
    career = 'pagoda'

    def test_pagoda_visitors_are_not_reported(self):
        p = self.post(2, 5)
        self.assertFalse(self.public(p['id'])['can_cop'])
        with self.assertRaises(GameError):
            self.cop(p['id'])


class Client(Base):
    def test_no_chance_reaches_the_client(self):
        p = self.post(2, 5)
        with mock.patch.object(R, 'CONFIRM_PCT', 100), mock.patch.object(R, 'PAY_PCT', 100):
            r = self.cop(p['id'])
        f = self.public(p['id'])
        self.assertEqual(set(f['cop']), {'day', 'verdict', 'before', 'after', 'pay'})
        room = json.dumps(self.public(), ensure_ascii=False)
        for word in ('CONFIRM', 'PAY_PCT', 'chance', 'odds', 'percent'):
            self.assertNotIn(word, room)
        self.assertFalse({'chance', 'odds', 'pct', 'rate'} & set(r))
        self.assertNotRegex(r['message'], r'\d+\s*%')
        js = (ROOT / 'public/js/v4/views.js').read_text(encoding='utf-8')
        part = js[js.index('const copLeft'):]
        part = part[:part.index("const choice=")]
        self.assertNotRegex(part, r'\d+\s*%')
        for n in (str(R.CONFIRM_PCT), str(R.PAY_PCT)):
            self.assertNotIn(n, re.sub(r'\d+px', '', part))

    def test_malformed_record_is_refused(self):
        for bad in ({'day': 15}, {'day': 15, 'verdict': 'vip', 'before': 2, 'after': 5, 'pay': 0},
                    {'day': 15, 'verdict': 'fair', 'before': 2, 'after': 5, 'pay': 0},
                    {'day': 15, 'verdict': 'raised', 'before': 2, 'after': 5, 'pay': 10**6}, 'raised'):
            with self.subTest(bad=bad):
                p = self.post(2, 5)
                p['feedback']['cop'] = bad
                with self.assertRaises(GameError):
                    validate_state(self.j.state)
                self.j.c['feed'].remove(p)


class CareCard(Base):
    """Customer care keeps each person's last visits with that visit's stars (engine._cs_after_task): when the police
    raise a review's stars, that visit's snapshot follows (engine.cs_restar), other visits stay; same shape and range,
    so the save still loads on 1.9.28."""
    career = 'customer_care'

    def card(self, p):
        care = engine.cs_care(self.j.c)
        title = p['feedback']['title'][:120]
        care['people'][p['npc']] = dict(n=3, last=[dict(day=14, title=title, note='đã xử lý', stars=2),
                                                  dict(day=15, title='Việc khác', note='đã xử lý', stars=2),
                                                  dict(day=15, title=title, note='xử lý chuẩn', stars=2)])
        validate_state(self.j.state)
        return care['people'][p['npc']]['last']

    def test_raised_stars_reach_the_visit_snapshot(self):
        p = self.post(2, 5)
        last = self.card(p)
        with mock.patch.object(R, 'CONFIRM_PCT', 100), mock.patch.object(R, 'PAY_PCT', 0):
            self.assertEqual(self.cop(p['id'])['cop'], 'raised')
        last = engine.cs_care(self.j.c)['people'][p['npc']]['last']
        self.assertEqual([x['stars'] for x in last], [2, 2, 5])
        validate_state(self.j.state)
        old = OldServer.old_tree(self, CARE_RELEASE)
        prog = ('import json,sys;from game.engine import validate_state,migrate_state;'
                's=json.load(sys.stdin);validate_state(s);s=migrate_state(s);validate_state(s);'
                'print(json.dumps([x["stars"] for x in s["careers"]["customer_care"]["ext"]["data"]["care"]["people"]'
                f'["{p['npc']}"]["last"]]))')
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(self.j.state), capture_output=True,
                             text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        self.assertEqual(json.loads(out.stdout), [2, 2, 5])

    def test_kept_stars_leave_the_card_alone(self):
        p = self.post(3, 3)
        self.card(p)
        self.assertEqual(self.cop(p['id'])['cop'], 'fair')
        self.assertEqual([x['stars'] for x in engine.cs_care(self.j.c)['people'][p['npc']]['last']], [2, 2, 2])


class OldServer(Base):
    """Saves written here (raised with bồi thường, unproven, fair) validate on 1.9.27, the release a rollback lands on."""

    def old_tree(self, release=OLD_RELEASE):
        if os.environ.get('MNL_COP_OLD_TREE') and release == OLD_RELEASE:
            return Path(os.environ['MNL_COP_OLD_TREE'])
        tmp = tempfile.mkdtemp(prefix='mnl-1927-')
        try:
            data = subprocess.run(['git', 'archive', release, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {release} (MNL_COP_OLD_TREE)')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def test_new_saves_validate_on_1_9_27(self):
        a, b, c = self.post(1, 5), self.post(2, 4), self.post(3, 3)
        with mock.patch.object(R, 'CONFIRM_PCT', 100), mock.patch.object(R, 'PAY_PCT', 100):
            self.assertTrue(self.cop(a['id'])['paid'])
        with mock.patch.object(R, 'CONFIRM_PCT', 0):
            self.assertEqual(self.cop(b['id'])['cop'], 'unproven')
        self.assertEqual(self.cop(c['id'])['cop'], 'fair')
        s = json.loads(json.dumps(self.j.state))
        validate_state(s)
        old = self.old_tree()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state;'
                's=json.load(sys.stdin);validate_state(s);s=migrate_state(s);validate_state(s);public_state(s);'
                f'print(json.dumps([[p["stars"],p["feedback"]["cop"]["verdict"]] for p in s["careers"]["{self.career}"]["feed"] '
                'if (p.get("feedback") or {}).get("cop")]))')
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True,
                             text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        self.assertEqual(sorted(json.loads(out.stdout)), [[2, 'unproven'], [3, 'fair'], [5, 'raised']])


if __name__ == '__main__':
    unittest.main()
