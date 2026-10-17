"""🛎️ Khách sạn Sông Mây (game/careers/hotel.py): a salaried shift rotating through six posts (check-in, housekeeping,
laundry, breakfast, repairs, decoration). Every step is graded on the server, a wrong step stays open and lowers the
quality; seasons follow the real Vietnam date (Valentine, Tết, Noel: x1.5 bonus, one more guest, the season's
lobby brief); twelve desk surprises; strict saves and the dormant record an untouched hotel leaves out."""
import copy
import json
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest import mock

from tests.helpers import Journey
from game import journey as jr
from game.careers import ORDER, PLUGINS
from game.engine import DORMANT, GameError, apply_action, dormant_out, initial_career, new_state, public_state, validate_state, wake

H = PLUGINS.get('hotel')
if H is not None:
    from game.careers import hotel_content as HC

VN = timezone(timedelta(hours=7))


def vn_ts(y, m, d, hour=10):
    return datetime(y, m, d, hour, tzinfo=VN).timestamp()


def slot_of(kind, day=3):
    return next(s for s in range(6) if H.kind_of(day, s) == kind)


def wrong_value(st, right):
    """A value of the right shape that is not the answer."""
    typ = st['type']
    if typ == 'choice':
        return next(o['id'] for o in st['options'] if o['id'] != right)
    if typ == 'number':
        return right + 1
    if typ == 'order':
        return list(reversed(right))
    if typ == 'multi':
        ids = sorted(o['id'] for o in st['options'])
        return [] if right == ids else ids
    first = st['fields'][0]['id']
    return dict(right, **{first: right[first] + 1})


def clear_desk(j):
    ev = j.c['ext']['data']['desk']['ev']
    if ev:
        x = next(x for x in HC.DESK if x['id'] == ev['script'])
        j.act('ht_desk', option=next(o['id'] for o in x['options'] if o.get('good')))


def solve(j, tid=None, limit=40):
    tid = tid or j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    for _ in range(limit):
        clear_desk(j)
        t = j.get(tid)
        if t['status'] == 'completed':
            return t
        _, steps, key = H._active(t)
        st = steps[t['at']]
        j.act('ht_step', task=tid, step=st['id'], value=key[st['id']])
    raise AssertionError('hotel task did not finish')


def roundtrip(j):
    j.state = json.loads(json.dumps(j.state))
    validate_state(j.state)


@unittest.skipUnless(H, 'hotel filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_last_dormant_and_salaried(self):
        from game import operations
        from game.career_voice import salaried_set
        self.assertEqual(ORDER[ORDER.index('customs') + 1], 'hotel')   # appended after customs (banquet came next)
        self.assertIn('hotel', DORMANT)
        self.assertIn('hotel', salaried_set())
        self.assertIn('hotel', operations.SALARIED)
        posting = H.SPEC['employment']['postings'][0]
        self.assertEqual(posting['org'], 'Khách sạn Sông Mây')
        self.assertEqual(H.SPEC['tip'], 0)

    def test_the_shift_rotates_through_all_six_posts(self):
        for day in range(1, 8):
            self.assertEqual({H.kind_of(day, s) for s in range(6)}, set(HC.KINDS))
        self.assertEqual(H.make_task(5, 2, 1), H.make_task(5, 2, 1))

    def test_journey_opens_the_hotel_from_chapter_three_without_listing_it(self):
        s = new_state()
        jr.enable_story(s, 12345)
        s['journey']['chapter'] = 1
        self.assertFalse(jr.is_unlocked(s, 'hotel'))
        s['journey']['chapter'] = 3
        self.assertTrue(jr.is_unlocked(s, 'hotel'))
        self.assertNotIn('hotel', s['journey']['unlocked'])   # an older build would refuse a save that lists it
        self.assertIn('hotel', public_state(s)['journey']['unlocked'])
        self.assertEqual(jr.content()['unlock_chapter']['hotel'], 3)


@unittest.skipUnless(H, 'hotel filtered out by MNL_CAREERS')
class Posts(unittest.TestCase):
    def test_each_post_end_to_end_with_a_mistake_fixed_in_place(self):
        for kind in HC.KINDS:
            with self.subTest(kind=kind):
                j = Journey('hotel', day=3, slot=slot_of(kind))
                tid = j.task['id']
                self.assertEqual(j.task['kind'], kind)
                self.assertEqual(j.task['season'], H.season_now())
                j.task['season'] = 'none'   # the same numbers whatever the real date
                j.act('ask', task=tid)
                _, steps, key = H._active(j.get(tid))
                st = steps[0]
                r = j.act('ht_step', task=tid, step=st['id'], value=wrong_value(st, key[st['id']]))
                self.assertFalse(r['correct'])
                t = j.get(tid)
                self.assertEqual((t['at'], t['wrong'], t['errors'], t['quality']), (0, 1, [st['id']], 88))
                roundtrip(j)   # a half-done job with a mistake is a valid save
                money = j.c['money']
                done = solve(j, tid)
                self.assertEqual(done['status'], 'completed')
                self.assertEqual(done['quality'], 88)
                self.assertEqual(done['work'], {s['id']: key[s['id']] for s in steps})
                self.assertEqual(done['paid'], max(3, round(HC.BONUS[kind] * 88 / 100)))
                self.assertEqual(j.c['money'], money + done['paid'])
                d = j.c['ext']['data']
                self.assertEqual((d['stats']['jobs'], d['stats']['good'], d['stats']['posts'][kind]), (1, 0, 0))
                roundtrip(j)

    def test_a_clean_job_counts_for_the_journey(self):
        j = Journey('hotel', day=3, slot=slot_of('repair'))
        j.task['season'] = 'none'
        done = solve(j)
        self.assertEqual((done['quality'], done['paid']), (100, HC.BONUS['repair']))
        d = j.c['ext']['data']
        self.assertEqual((d['stats']['good'], d['stats']['posts']['repair'], d['today']['good']), (1, 1, 1))
        H.on_close(j.state, j.c)
        H.on_close(j.state, j.c)
        self.assertEqual(d['stats']['active_days'], 1)
        roundtrip(j)

    def test_wrong_shapes_and_out_of_order_steps_change_nothing(self):
        j = Journey('hotel', day=3, slot=slot_of('housekeeping'))
        tid = j.task['id']
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):   # the job slip is read first
            j.act('ht_step', task=tid, step='housekeeping.order', value=[])
        self.assertEqual(j.state, before)
        j.act('ask', task=tid)
        _, steps, key = H._active(j.get(tid))
        for p in (dict(step='housekeeping.minibar', value=0), dict(step=steps[0]['id'], value=['linen']),
                  dict(step=steps[0]['id'], value='linen'), dict(step=steps[0]['id'], value=key[steps[0]['id']] + ['linen']),
                  dict(step={}, value=1), dict(step=steps[0]['id'], value=None)):
            before = copy.deepcopy(j.state)
            with self.assertRaises(GameError):
                j.act('ht_step', task=tid, **p)
            self.assertEqual(j.state, before)
        with self.assertRaises(GameError):
            j.act('ht_forge', task=tid)

    def test_counts_and_numbers_are_bounded(self):
        j = Journey('hotel', day=3, slot=slot_of('laundry'))
        tid = j.task['id']
        j.act('ask', task=tid)
        st = H._active(j.get(tid))[1][0]
        fields = [f['id'] for f in st['fields']]
        for value in ({fields[0]: 1}, {k: 999 for k in fields}, {k: -1 for k in fields}, {k: 'x' for k in fields}, [1, 2]):
            before = copy.deepcopy(j.state)
            with self.assertRaises(GameError):
                j.act('ht_step', task=tid, step=st['id'], value=value)
            self.assertEqual(j.state, before)

    def test_the_answer_key_never_reaches_the_client(self):
        t = H.make_task(3, 0, 1)
        self.assertIsNone(H.public_task(t)['needs'])
        t['known'] = True
        v = H.public_task(t)
        self.assertNotIn('_key', v)
        for st in v['needs']['steps']:
            self.assertNotIn('answer', st)
        self.assertEqual(v['post']['id'], t['kind'])

    def test_a_full_day_closes_with_the_contract_salary_once(self):
        with mock.patch.object(H, 'season_now', return_value='none'):
            j = Journey('hotel')
            for t in list(j.c['tasks']):
                solve(j, t['id'])
        self.assertFalse(any(r.get('category') == 'salary' for r in j.c['ops']['finance']['ledger']))
        j.act('end_day', carry_event=True)
        rows = [r for r in j.c['ops']['finance']['ledger'] if r.get('category') == 'salary']
        self.assertEqual(len(rows), 1)
        self.assertGreater(rows[0]['amount'], 0)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('end_day', carry_event=True)
        self.assertEqual(j.state, before)
        roundtrip(j)


@unittest.skipUnless(H, 'hotel filtered out by MNL_CAREERS')
class Saves(unittest.TestCase):
    def halfway(self):
        j = Journey('hotel', day=3, slot=slot_of('housekeeping'))
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = H._active(j.get(tid))
        st = steps[0]
        j.act('ht_step', task=tid, step=st['id'], value=wrong_value(st, key[st['id']]))
        for st in steps[:3]:
            j.act('ht_step', task=tid, step=st['id'], value=key[st['id']])
        roundtrip(j)
        return j

    def test_forged_task_fields_are_refused(self):
        j = self.halfway()
        forge = {
            'needs': lambda t: t['needs'].update(room='999'),
            '_key': lambda t: t['_key'].update({'housekeeping.minibar': 0 if t['_key']['housekeeping.minibar'] else 5}),
            'kind': lambda t: t.update(kind='decor'),
            'work': lambda t: t['work'].pop('housekeeping.order'),
            'work value': lambda t: t['work'].update({'housekeeping.linen': 'f' if t['work']['housekeeping.linen'] != 'f' else 'd'}),
            'at': lambda t: t.update(at=t['at'] + 1),
            'quality': lambda t: t.update(quality=100),
            'wrong': lambda t: t.update(wrong=0),
            'errors': lambda t: t.update(errors=[]),
            'errors ahead': lambda t: t['errors'].append('housekeeping.report'),
            'paid': lambda t: t.update(paid=50),
            'stage': lambda t: t.update(stage='done'),
            'season': lambda t: t.update(season='halloween'),
        }
        for name, fn in forge.items():
            with self.subTest(field=name):
                bad = copy.deepcopy(j.state)
                fn(bad['careers']['hotel']['tasks'][0])
                with self.assertRaises(GameError):
                    validate_state(bad)

    def test_forged_records_are_refused(self):
        j = Journey('hotel', day=3, slot=slot_of('repair'))
        j.task['season'] = 'none'
        solve(j)
        roundtrip(j)
        forge = {
            'good above jobs': lambda d: d['stats'].update(good=5),
            'post without a good job': lambda d: d['stats']['posts'].update(decor=1),
            'unknown post': lambda d: d['stats']['posts'].update(spa=0),
            'intro type': lambda d: d.update(intro=1),
            'extra key': lambda d: d.update(vip=True),
            'active days': lambda d: d['stats'].update(active_days=9),
            'desk script': lambda d: d['desk'].update(ev=dict(id='desk-9', script='free_room', day=3, at='between')),
        }
        for name, fn in forge.items():
            with self.subTest(record=name):
                bad = copy.deepcopy(j.state)
                fn(bad['careers']['hotel']['ext']['data'])
                with self.assertRaises(GameError):
                    validate_state(bad)

    def test_an_untouched_hotel_stays_out_of_the_stored_save(self):
        s = new_state()
        self.assertIn('hotel', s['careers'])
        out = dormant_out(s)
        self.assertNotIn('hotel', out['careers'])
        back = json.loads(json.dumps(out))
        self.assertTrue(wake(back))
        self.assertEqual(back['careers']['hotel'], initial_career('hotel'))
        j = Journey('hotel', day=3, slot=0)
        solve(j)
        self.assertIn('hotel', dormant_out(j.state)['careers'])   # once worked, never left out again


@unittest.skipUnless(H, 'hotel filtered out by MNL_CAREERS')
class Seasons(unittest.TestCase):
    def test_season_of_follows_the_vietnam_calendar(self):
        cases = {
            date(2026, 10, 16): None, date(2026, 2, 1): 'tet', date(2026, 2, 13): 'tet', date(2026, 2, 14): 'valentine',
            date(2026, 1, 26): None, date(2026, 1, 27): 'tet', date(2026, 2, 24): 'tet', date(2026, 2, 25): None,
            date(2028, 2, 10): 'valentine', date(2028, 2, 3): 'valentine', date(2028, 1, 20): 'tet',
            date(2027, 2, 14): 'valentine', date(2027, 2, 13): 'tet',
            date(2026, 12, 1): 'noel', date(2026, 12, 25): 'noel', date(2026, 12, 26): None, date(2026, 11, 30): None,
        }
        for d, want in cases.items():
            with self.subTest(day=d.isoformat()):
                self.assertEqual(H.season_of(d), want)

    def test_the_real_date_is_read_in_vietnam_time(self):
        # 30/11 23:30 in Hà Nội is still 30/11 in UTC, 1/12 00:30 is already Noel season
        with mock.patch('game.careers.kit.now', return_value=vn_ts(2026, 11, 30, 23)):
            self.assertEqual(H.season_now(), 'none')
        with mock.patch('game.careers.kit.now', return_value=datetime(2026, 12, 1, 0, 30, tzinfo=VN).timestamp()):
            self.assertEqual(H.season_now(), 'noel')
            self.assertEqual(H.season_view()['bonus'], 1.5)

    def test_a_task_taken_in_season_keeps_it_and_pays_more(self):
        with mock.patch('game.careers.kit.now', return_value=vn_ts(2026, 12, 20)):
            j = Journey('hotel', day=3, slot=slot_of('decor'))
        t = j.task
        self.assertEqual(t['season'], 'noel')
        brief = H.public_task(dict(t, known=True))['needs']
        self.assertEqual(brief['theme'], 'noel')
        season = H.decor_brief(3, slot_of('decor'), 'noel')[0]
        self.assertEqual(brief, dict(season, rule=H.decor_rule(season)))   # + the rule line shown on screen (#404)
        self.assertNotEqual(brief, t['needs'])   # the stored year-round brief stays as made
        roundtrip(j)   # validates on another (out of season) date too: the brief is a pure function
        done = solve(j)
        self.assertEqual(done['paid'], round(HC.BONUS['decor'] * 1.5))
        self.assertEqual(j.c['ext']['data']['stats']['seasonal'], 1)
        roundtrip(j)

    def test_season_adds_one_guest_to_the_day(self):
        with mock.patch('game.careers.kit.now', return_value=vn_ts(2026, 10, 16)):
            calm = Journey('hotel')
        with mock.patch('game.careers.kit.now', return_value=vn_ts(2027, 2, 10)):
            busy = Journey('hotel')
        self.assertEqual(len(busy.c['tasks']), len(calm.c['tasks']) + 1)
        self.assertTrue(all(t['season'] == 'tet' for t in busy.c['tasks']))
        self.assertTrue(all(t['season'] == 'none' for t in calm.c['tasks']))
        validate_state(busy.state)

    def test_every_season_brief_is_solvable_in_budget_and_safe(self):
        for theme in list(HC.THEMES):
            for day in range(1, 25):
                for slot in range(6):
                    brief, steps, key = H.decor_brief(day, slot, theme)
                    prices = {i['id']: i['price'] for i in brief['items']}
                    self.assertTrue(key['decor.items'])
                    self.assertEqual(sum(prices[i] for i in key['decor.items']), key['decor.cost'])
                    self.assertLessEqual(key['decor.cost'], brief['budget'])
                    self.assertIn(key['decor.place'], ('room', 'lobby'))
                    self.assertEqual(brief, H.decor_brief(day, slot, theme)[0])


@unittest.skipUnless(H, 'hotel filtered out by MNL_CAREERS')
class Desk(unittest.TestCase):
    def test_twelve_well_formed_surprises(self):
        self.assertEqual(len(HC.DESK), 12)
        self.assertEqual(len({x['id'] for x in HC.DESK}), 12)
        banned = ('NPC', 'người chơi', 'trong game', 'mô phỏng', 'anh ấy', 'cô ấy')
        for x in HC.DESK:
            with self.subTest(script=x['id']):
                self.assertTrue(x['title'] and x['text'] and x['emoji'])
                self.assertGreaterEqual(len(x['options']), 3)
                self.assertEqual(len({o['id'] for o in x['options']}), len(x['options']))
                self.assertEqual(sum(1 for o in x['options'] if o.get('good') is True), 1)
                self.assertIn(x.get('at', 'between'), ('open', 'between', 'any'))
                for o in x['options']:
                    ends = [o['luck']['win'], o['luck']['lose']] if o.get('luck') else [o]
                    self.assertTrue(o['label'] and all(e['outcome'] for e in ends))
                    self.assertGreaterEqual(o.get('effects', {}).get('money', 0), 0)   # a surprise never charges the player
                text = json.dumps(x, ensure_ascii=False)
                for b in banned:
                    self.assertNotIn(b, text)

    def test_each_surprise_blocks_the_desk_and_every_choice_saves(self):
        for x in HC.DESK:
            for o in x['options']:
                with self.subTest(script=x['id'], option=o['id']):
                    j = Journey('hotel', day=4, slot=0)
                    j.c['ext']['data']['desk']['ev'] = dict(id='desk-1', script=x['id'], day=4, at='between')
                    j.c['ext']['data']['desk'].update(seq=1, fired=1)
                    validate_state(j.state)
                    tid = j.task['id']
                    j.act('ask', task=tid)
                    st = H._active(j.get(tid))[1][0]
                    before = copy.deepcopy(j.state)
                    with self.assertRaises(GameError):
                        j.act('ht_step', task=tid, step=st['id'], value=H._active(j.get(tid))[2][st['id']])
                    self.assertEqual(j.state, before)
                    r = j.act('ht_desk', option=o['id'])
                    self.assertTrue(r['message'])
                    self.assertIsNone(j.c['ext']['data']['desk']['ev'])
                    self.assertEqual(j.c['ext']['data']['desk']['last']['choice'], o['id'])
                    roundtrip(j)

    def test_surprises_arrive_during_a_long_shift(self):
        seen = set()
        with mock.patch.object(H, 'season_now', return_value='none'):
            for day in range(2, 12):
                j = Journey('hotel')
                j.c['day'] = day
                j.c['ext']['data']['desk'] = H.kit.desk_initial()
                H.on_start(j.state, j.c)
                for t in list(j.c['tasks']):
                    solve(j, t['id'])
                seen.update(h['script'] for h in j.c['ext']['data']['desk']['log'])
                validate_state(j.state)
        self.assertGreater(len(seen), 1)

    def test_an_undecided_surprise_settles_itself_at_closing(self):
        j = Journey('hotel', day=4, slot=0)
        j.c['ext']['data']['desk']['ev'] = dict(id='desk-1', script='duck', day=4, at='between')
        j.c['ext']['data']['desk'].update(seq=1, fired=1)
        out = H.on_close(j.state, j.c)
        self.assertIsNone(j.c['ext']['data']['desk']['ev'])
        self.assertEqual(len(out['lines']), 2)
        validate_state(j.state)


@unittest.skipUnless(H, 'hotel filtered out by MNL_CAREERS')
class Content(unittest.TestCase):
    def test_every_task_is_consistent_and_solvable(self):
        for day in range(1, 31):
            for slot in range(8):
                t = H.make_task(day, slot, 1)
                H.validate_task(copy.deepcopy(t), t)
                for season in H.SEASON_IDS:
                    _, steps, key = H._active(dict(t, season=season))
                    self.assertEqual(set(key), {s['id'] for s in steps})
                    for st in steps:
                        self.assertIn(st['type'], H.TYPES)
                        if st['type'] == 'choice':
                            self.assertIn(key[st['id']], [o['id'] for o in st['options']])
                        elif st['type'] in ('order', 'multi'):
                            self.assertLessEqual(set(key[st['id']]), {o['id'] for o in st['options']})
                        elif st['type'] == 'counts':
                            self.assertEqual(set(key[st['id']]), {f['id'] for f in st['fields']})

    def test_the_copy_addresses_the_player_neutrally(self):
        text = json.dumps([H.content(), H.SPEC, HC.NOTEBOOK, HC.DESK, HC.PEOPLE], ensure_ascii=False)
        for word in ('anh ấy', 'cô ấy', 'người chơi', 'NPC'):
            self.assertNotIn(word, text)
        for day in range(1, 13):
            for slot in range(6):
                t = H.make_task(day, slot, 1)
                blob = json.dumps(t, ensure_ascii=False)
                self.assertNotIn('người chơi', blob)

    def test_milestones_need_good_jobs_days_and_posts(self):
        j = Journey('hotel', day=3, slot=0)
        st = j.c['ext']['data']['stats']
        st.update(jobs=20, good=20, active_days=6, posts=dict(checkin=20, housekeeping=0, laundry=0, breakfast=0, repair=0, decor=0))
        self.assertNotIn('desk', H.public_data(j.c)['progress']['earned'])
        st['posts'].update(checkin=10, laundry=5, decor=5)
        self.assertEqual(H.public_data(j.c)['progress']['earned'], ['desk'])
        validate_state(j.state)


@unittest.skipUnless(H, 'hotel filtered out by MNL_CAREERS')
class DecorHints(unittest.TestCase):
    """Feedback #404: a wrong decoration pick says what is wrong (items off the occasion and what they are for,
    items the guest avoids, over budget, how many fitting items are missing) and the step shows the rule. The
    generated brief and its key are unchanged (the hint is computed beside them)."""

    def brief(self, theme='honeymoon', limit='pollen', budget=16):
        return dict(theme=theme, title=HC.THEMES[theme][0], limit=HC.LIMITS[limit][0], budget=budget)

    def test_the_players_honeymoon_combo(self):
        # 17/10, room 204: Khung ảnh cưới 7 + Thiên nga 4 + Bóng bay trái tim 5 = 16 xu, "đúng ngân sách" yet wrong.
        hint = H.decor_hint(self.brief(), ['frame', 'heart', 'swan'], ['candle', 'card', 'swan'])
        self.assertIn('Có món không hợp dịp phòng trăng mật: Khung ảnh cưới in sẵn (dành cho kỷ niệm ngày cưới), '
                      'Bóng bay trái tim (dành cho sảnh valentine).', hint)
        self.assertIn('Còn thiếu 2 món hợp dịp phòng trăng mật.', hint)
        self.assertNotIn('Nến', hint)   # the missing items are counted, never named

    def test_avoided_and_over_budget_items(self):
        hint = H.decor_hint(self.brief(), ['candle', 'card', 'petal', 'swan'], ['candle', 'card', 'swan'])
        self.assertEqual(hint, 'Có món khách dặn tránh: Cánh hồng rải giường.')
        avoid = {text: cat for text, cat in HC.LIMITS.values()}
        found = None
        for day in range(1, 40):
            for slot in range(6):
                for theme in HC.THEMES:
                    b, _, k = H.decor_brief(day, slot, theme)
                    left = [i[0] for i in HC.ITEMS if theme in i[3] and i[0] not in k['decor.items'] and i[4] != avoid[b['limit']]]
                    if left and not found:
                        found = (b, k, left[0])
        b, k, top = found
        self.assertIn(f'Tổng tiền vượt ngân sách {b["budget"]} xu', H.decor_hint(b, k['decor.items'] + [top], k['decor.items']))

    def test_every_wrong_pick_gets_a_hint(self):
        import random
        rng = random.Random(404)
        for day in range(1, 25):
            for slot in range(6):
                for theme in HC.THEMES:
                    b, steps, k = H.decor_brief(day, slot, theme)
                    ids = [o['id'] for o in steps[0]['options']]
                    for _ in range(4):
                        pick = sorted(rng.sample(ids, rng.randint(0, len(ids))))
                        if pick != k['decor.items']:
                            hint = H.decor_hint(b, pick, k['decor.items'])
                            self.assertTrue(hint, (day, slot, theme, pick))
                            self.assertLess(len(hint), 420)

    def test_the_step_shows_the_rule_and_a_wrong_pick_explains_itself(self):
        j = Journey('hotel', day=3, slot=slot_of('decor'))
        tid = j.task['id']
        j.task['season'] = 'none'
        j.act('ask', task=tid)
        brief, steps, key = H._active(j.get(tid))
        view = public_state(j.state)['careers']['hotel']['tasks']
        needs = next(t for t in view if t['id'] == tid)['needs']
        self.assertEqual(needs['rule'], f'Chọn TẤT CẢ món hợp dịp {brief["title"].lower()}, bỏ món khách dặn tránh; '
                                        'tổng tiền vượt ngân sách thì bỏ món đắt nhất.')
        self.assertIn(needs['rule'], H.hint(j.c, j.get(tid)))
        r = j.act('ht_step', task=tid, step='decor.items', value=key['decor.items'][:-1])
        self.assertFalse(r['correct'])
        self.assertTrue(r['message'].startswith('Chưa đúng: chọn đồ trang trí. Còn thiếu 1 món hợp dịp'), r['message'])
        self.assertEqual(j.get(tid)['lines'][-1], r['message'])
        r = j.act('ht_step', task=tid, step='decor.items', value=key['decor.items'])
        self.assertTrue(r['correct'])
        r = j.act('ht_step', task=tid, step='decor.cost', value=key['decor.cost'] + 1)
        self.assertIn(f'({len(key["decor.items"])} món)', r['message'])
        roundtrip(j)
        again, _, key2 = H.decor_brief(3, slot_of('decor'), brief['theme'])
        self.assertEqual((brief, key), (again, key2))


if __name__ == '__main__':
    unittest.main()
