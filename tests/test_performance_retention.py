"""Client performance summaries are bounded numeric data in existing retention tables."""
import json
import unittest
from unittest.mock import patch

from game import retention as rt


class PerformanceRetentionTests(unittest.TestCase):
    def test_leave_preserves_only_known_numeric_summaries(self):
        data = {'parse': {'n': 2, 'total': 15, 'max': 9, 'text': 'private'},
                'render': {'n': 1, 'total': 0, 'max': 0},
                'url': 'private', 'unknown': {'n': 1, 'total': 2, 'max': 2}}
        leave = json.loads(rt.leave_payload({'v': 'job', 'perf': data, 'text': 'private'}))
        self.assertEqual(leave, {'v': 'job', 'perf': {'parse': {'n': 2, 'total': 15, 'max': 9},
                                                   'render': {'n': 1, 'total': 0, 'max': 0}}})

    def test_invalid_summary_fields_are_dropped(self):
        valid = {'n': 2, 'total': 12, 'max': 8}
        for field, values in {
            'n': [0, -1, 201, 2.5, '2', True, None, float('nan'), float('inf')],
            'total': [-1, 12000001, '12', True, None, float('nan'), float('inf'), -float('inf')],
            'max': [-1, 60001, '8', True, None, float('nan'), float('inf'), -float('inf')],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    result = json.loads(rt.leave_payload({'v': 'home', 'perf': {'parse': dict(valid, **{field: value})}}))
                    self.assertEqual(result, {'v': 'home'})
        for summary in [{'n': 2, 'total': 2, 'max': 8}, {'n': 2, 'total': 100, 'max': 8}, [], 'private', None]:
            self.assertEqual(json.loads(rt.leave_payload({'v': 'home', 'perf': {'render': summary}})), {'v': 'home'})

    def test_maximum_client_summary_stays_small(self):
        perf = {k: {'n': 200, 'total': 12000000, 'max': 60000} for k in ('parse', 'apply', 'render', 'longtask', 'interaction')}
        payload = rt.leave_payload({'v': 'job', 'perf': perf})
        self.assertEqual(json.loads(payload)['perf'], perf)
        self.assertLess(len(payload), 600)

    def test_load_summaries_become_existing_histogram_rows(self):
        class DB:
            def __init__(self):
                self.rows = []

            def execute(self, sql, values):
                if sql.startswith('INSERT INTO stat_loads'):
                    self.rows.append(values)
                return self

            def fetchone(self):
                return (1,)

        class Store:
            def __init__(self):
                self.db = DB()

            def transaction(self, write, _timeout):
                return write(self.db)

        store = Store()
        data = {'load': {'frame': 500, 'net': '4g', 'cache': 'warm', 'mem': 2,
                         'perf': {'render': {'n': 2, 'total': 750, 'max': 500},
                                  'private': {'n': 1, 'total': 5, 'max': 5},
                                  'parse': {'n': True, 'total': 5, 'max': 5}}}}
        with patch.object(rt, 'ENABLED', True), patch.object(rt, '_born', return_value='2026-10-05'):
            got = rt.beacon(store, 'performance-test', data, now=1791158400)
        by_metric = {r[1]: r for r in store.db.rows}
        self.assertEqual(set(by_metric), {'frame', 'render_avg', 'render_max'})
        self.assertEqual(by_metric['render_avg'][-1], rt.load_bucket(375))
        self.assertEqual(by_metric['render_max'][-1], rt.load_bucket(500))
        self.assertEqual(got['load'], 3)
        self.assertNotIn('private', json.dumps(store.db.rows))


if __name__ == '__main__':
    unittest.main()
