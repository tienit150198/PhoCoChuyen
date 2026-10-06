"""Real PostgreSQL coverage for incremental, transactional visit snapshots."""
import json
from unittest.mock import patch

from game import quay_self, work_visits as visits
from game.content import CAREER_META
from tests.test_quay_hire import Base


class WorkVisitSync(Base):
    def setUp(self):
        super().setUp()
        self.token = self.user('snapshot_owner')
        self.cmd(self.token, 'select_career', career='milk_tea')
        self.cmd(self.token, 'start_day', career='milk_tea')
        self.owner = self.sid(self.token)
        self.save = self.state(self.token)
        for career in self.save['careers'].values():
            career['started'] = True

    def sync(self, now=100):
        with self.store.connect() as db:
            with patch.object(db, 'execute', wraps=db.execute) as execute:
                visits.sync(db, self.owner, self.save, now=now)
            return [call.args[0] for call in execute.call_args_list]

    def rows(self):
        with self.store.connect() as db:
            return {row['target']: dict(row) for row in db.execute(
                'SELECT * FROM work_visit_places WHERE owner=? ORDER BY id',
                (self.owner,)).fetchall()}

    @staticmethod
    def writes(queries):
        return [q for q in queries if 'work_visit_places' in q and
                q.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))]

    def test_unchanged_46_careers_read_places_once_without_writing(self):
        self.sync()
        before = self.rows()
        self.assertEqual(len(before), 46)   # 41 + library (thư viện), oil (thợ dầu khí), railway (gác chắn đường sắt), nurse (điều dưỡng), lifeguard (cứu hộ hồ bơi)
        queries = self.sync(now=200)
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.writes(queries), [])
        self.assertEqual(sum('SELECT' in q and 'work_visit_places' in q for q in queries), 1)

    def test_changed_snapshots_batch_and_keep_visibility_and_stable_ids(self):
        self.sync()
        with self.store.connect() as db:
            db.execute("UPDATE work_visit_places SET visibility='public' WHERE owner=? AND target='milk_tea'", (self.owner,))
            db.execute("UPDATE work_visit_places SET visibility='closed' WHERE owner=? AND target='accounting'", (self.owner,))
        before = self.rows()
        for career in self.save['careers'].values():
            career['theme'] = 'Vườn mùa thu'
        queries = self.sync(now=200)
        after = self.rows()
        for target, row in after.items():
            expected = json.loads(before[target]['data'])
            expected['theme'] = 'Vườn mùa thu'
            self.assertEqual(json.loads(row['data']), expected)
            self.assertEqual(row['id'], before[target]['id'])
            self.assertEqual(row['visibility'], before[target]['visibility'])
            self.assertEqual(row['updated_at'], 200)
        self.assertEqual(len(self.writes(queries)), 1)

    def test_snapshot_still_projects_only_allowlisted_career_fields(self):
        self.save['careers']['accounting'].update(
            open=False, day=7, theme='a' * 90, decor={'plant': {'private': 'secret'}},
            active_task='active', tasks=[dict(id='active', day=7, known=True,
                title='Private answer stays in task', answer='SECRET', status='completed')])
        self.sync()
        row = self.rows()['accounting']
        with self.store.connect() as db:
            person = visits._person(db, self.owner)
        self.assertEqual(json.loads(row['data']), dict(
            name=CAREER_META['accounting'].get('short') or CAREER_META['accounting']['name'],
            owner=person, activity=dict(label='Đang nghỉ', status='resting',
                tasktitle='Private answer stays in task', progress=dict(done=1, total=1)),
            theme='a' * 80, decor=['plant'], staffed=False, offers=[], available=False,
            status='waiting', reason='Chủ tiệm cần chuẩn bị một yêu cầu nghề nghiệp còn trống.'))
        self.assertEqual(row['visibility'], 'friends')

    def test_offer_changes_and_removed_places_keep_existing_close_semantics(self):
        self.sync()
        before = self.rows()
        self.assertTrue(json.loads(before['milk_tea']['data'])['offers'])
        self.save['careers']['milk_tea']['open'] = False
        self.save['careers']['accounting']['started'] = False
        self.sync(now=200)
        after = self.rows()
        milk = json.loads(after['milk_tea']['data'])
        self.assertEqual(milk['offers'], [])
        self.assertFalse(milk['available'])
        self.assertEqual(milk['activity']['status'], 'resting')
        closed = json.loads(before['accounting']['data'])
        closed.update(offers=[], available=False, status='closed', reason='Chỗ làm này đã đóng.')
        self.assertEqual(json.loads(after['accounting']['data']), closed)
        self.assertEqual(after['accounting']['id'], before['accounting']['id'])
        self.assertEqual(after['accounting']['visibility'], 'closed')
        self.assertEqual(after['accounting']['updated_at'], 200)
        self.sync(now=300)
        repeated = self.rows()
        self.assertEqual(repeated['milk_tea']['updated_at'], 200)
        self.assertEqual(repeated['accounting']['updated_at'], 300)
        self.save['careers']['accounting']['started'] = True
        self.sync(now=400)
        reopened = self.rows()['accounting']
        self.assertEqual(reopened['visibility'], 'closed')
        self.assertEqual(reopened['id'], before['accounting']['id'])
        self.assertEqual(reopened['data'], before['accounting']['data'])

    def test_profile_rename_updates_every_place_in_one_batch(self):
        self.sync()
        with self.store.connect() as db:
            db.execute('UPDATE profiles SET name=?,avatar=? WHERE sid=?',
                       ('Tên mới', '🌿', self.owner))
        queries = self.sync(now=200)
        for row in self.rows().values():
            person = json.loads(row['data'])['owner']
            self.assertEqual((person['name'], person['avatar']), ('Tên mới', '🌿'))
            self.assertEqual(row['updated_at'], 200)
        self.assertEqual(len(self.writes(queries)), 1)

    def test_failed_save_rolls_back_changed_and_removed_places_together(self):
        self.sync()
        before = self.rows()
        self.save['careers']['milk_tea']['theme'] = 'New theme'
        self.save['careers']['accounting']['started'] = False
        with self.assertRaisesRegex(RuntimeError, 'later save failure'):
            with self.store.connect() as db:
                visits.sync(db, self.owner, self.save, now=200)
                raise RuntimeError('later save failure')
        self.assertEqual(self.rows(), before)

    def test_one_changed_career_preserves_other_snapshot_timestamps(self):
        self.sync()
        before = self.rows()
        self.save['careers']['accounting']['theme'] = 'Autumn'
        queries = self.sync(now=200)
        after = self.rows()
        changed = after.pop('accounting')
        before.pop('accounting')
        self.assertEqual(after, before)
        self.assertEqual(json.loads(changed['data'])['theme'], 'Autumn')
        self.assertEqual(changed['updated_at'], 200)
        self.assertEqual(len(self.writes(queries)), 1)

    def test_quay_price_stock_and_removal_refresh_the_retained_snapshot(self):
        self.open_stall(self.token)
        self.save['journey']['quay'] = self.state(self.token)['journey']['quay']
        stall = self.save['journey']['quay']['stalls'][0]
        menu = quay_self.menu(stall)
        dish = menu['on'][0]
        stall['business']['stock'] = {dish: 3}
        self.sync()
        before = self.rows()[stall['id']]
        offer = json.loads(before['data'])['offers'][0]
        self.assertEqual((offer['dish'], offer['price']), (dish, menu['p'][dish]))
        stall['menu'] = menu
        menu['p'][dish] += 1
        self.sync(now=200)
        changed = self.rows()[stall['id']]
        self.assertEqual(json.loads(changed['data'])['offers'][0]['price'], offer['price'] + 1)
        stall['business']['stock'][dish] = 0
        self.sync(now=300)
        empty = json.loads(self.rows()[stall['id']]['data'])
        self.assertEqual(empty['offers'], [])
        self.assertFalse(empty['available'])
        self.save['journey']['quay']['stalls'] = []
        self.sync(now=400)
        removed = self.rows()[stall['id']]
        self.assertEqual(removed['id'], before['id'])
        self.assertEqual(removed['visibility'], 'closed')
        self.assertEqual(json.loads(removed['data'])['status'], 'closed')
        self.assertEqual(removed['updated_at'], 400)
