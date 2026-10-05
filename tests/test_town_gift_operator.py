import os
import unittest
import uuid
import psycopg
from game.system_gift import BROADCASTS, _broadcast_id
from scripts.grant_town_broadcast import queue_all


class TownGiftOperator(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(os.environ['TEST_DATABASE_URL'])
        self.addCleanup(self.conn.close)
        self.conn.execute('CREATE TEMP TABLE sessions(sid text PRIMARY KEY)')
        self.conn.execute('CREATE TEMP TABLE system_gifts(id text PRIMARY KEY,sid text,coins bigint,title text,text text,status text,created double precision)')
        self.conn.execute("INSERT INTO sessions VALUES('offline'),('online')")
        self.conn.commit()
        self.b = next(b for b in BROADCASTS if b['prefix'] == 'fair1005')

    def test_dry_run_then_repeat_queue_uses_same_lazy_ids(self):
        preview = queue_all(self.conn, self.b)
        self.assertEqual((preview['saves'], preview['missing'], preview['inserted']), (2,2,0))
        first = queue_all(self.conn, self.b, True)
        second = queue_all(self.conn, self.b, True)
        self.assertEqual((first['inserted'],second['inserted']), (2,0))
        rows = self.conn.execute('SELECT id,sid,coins,status FROM system_gifts').fetchall()
        self.assertEqual(set(rows), {(_broadcast_id('fair1005',sid),sid,300,'pending') for sid in ('offline','online')})

    def test_conflicting_existing_gift_aborts_every_insert(self):
        self.conn.execute("INSERT INTO system_gifts VALUES(%s,'online',500,%s,%s,'pending',0)",
                          (_broadcast_id('fair1005','online'),self.b['title'],self.b['text']))
        self.conn.commit()
        with self.assertRaises(ValueError): queue_all(self.conn,self.b,True)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM system_gifts').fetchone()[0],1)

    def test_concurrent_insert_is_checked_before_bulk_commit(self):
        # Shared disposable schema: unlike TEMP tables, both sessions see it.
        url = os.environ['TEST_DATABASE_URL']
        for competing_coins in (300, 500, None):
            with self.subTest(competing_coins=competing_coins):
                schema = 'gift_race_' + uuid.uuid4().hex
                with psycopg.connect(url, autocommit=True) as other:
                    other.execute('CREATE SCHEMA ' + schema)
                    try:
                        with psycopg.connect(url) as bulk:
                            for conn in (bulk, other):
                                conn.execute('SET search_path TO ' + schema)
                            bulk.execute('CREATE TABLE sessions(sid text PRIMARY KEY)')
                            bulk.execute('CREATE TABLE system_gifts(id text PRIMARY KEY,sid text,coins bigint,title text,text text,status text,created double precision)')
                            bulk.execute("INSERT INTO sessions VALUES('offline'),('online')")
                            bulk.commit()
                            b = self.b
                            if competing_coins is None:
                                other.execute("INSERT INTO system_gifts VALUES(%s,'online',300,%s,%s,'pending',0)",
                                              (_broadcast_id(b['prefix'], 'online'), b['title'], b['text']))

                            class InterleavedConnection:
                                inserted = False

                                def transaction(self):
                                    return bulk.transaction()

                                def cursor(self):
                                    return bulk.cursor()

                                def execute(self, sql, args=None):
                                    result = bulk.execute(sql, args)
                                    if sql.startswith('SELECT id,sid,coins,title,text') and not self.inserted:
                                        rows = result.fetchall()
                                        if competing_coins is None:
                                            other.execute('DELETE FROM system_gifts WHERE sid=%s', ('online',))
                                        else:
                                            other.execute("INSERT INTO system_gifts VALUES(%s,'online',%s,%s,%s,'pending',0)",
                                                          (_broadcast_id(b['prefix'], 'online'), competing_coins, b['title'], b['text']))
                                        self.inserted = True
                                        return rows
                                    return result

                            if competing_coins == b['coins']:
                                result = queue_all(InterleavedConnection(), b, True)
                                self.assertEqual(result['inserted'], 1)
                                expected = [('offline', 300), ('online', 300)]
                            else:
                                with self.assertRaises(ValueError):
                                    queue_all(InterleavedConnection(), b, True)
                                expected = [('online', 500)] if competing_coins is not None else []
                            self.assertEqual(bulk.execute('SELECT sid,coins FROM system_gifts ORDER BY sid').fetchall(), expected)
                    finally:
                        other.execute('DROP SCHEMA ' + schema + ' CASCADE')
