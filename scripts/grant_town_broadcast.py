"""Queue an existing broadcast for every current save, including offline players.

Defaults to a read-only preview. --apply inserts pending gifts atomically; wallet
credits still use the normal idempotent on-load path. Repeat runs are safe.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game import system_gift as sg


def queue_all(conn, broadcast, apply=False):
    b = broadcast
    with conn.transaction():
        conn.execute("SET LOCAL statement_timeout = '60s'")
        if not apply:
            conn.execute('SET TRANSACTION READ ONLY')
        sids = [r[0] for r in conn.execute('SELECT sid FROM sessions')]
        expected = {sg._broadcast_id(b['prefix'], sid): sid for sid in sids}
        def checked_rows():
            rows = {}
            for gid, sid, coins, title, text in conn.execute(
                    'SELECT id,sid,coins,title,text FROM system_gifts WHERE id LIKE %s', (b['prefix'] + '-%',)):
                if gid in expected:
                    if (sid, coins, title, text) != (expected[gid], b['coins'], b['title'], b['text']):
                        raise ValueError('Broadcast ID already has different gift content; no gifts queued')
                    rows[gid] = sid
            return rows

        existing = checked_rows()
        missing = [(gid, sid, b['coins'], b['title'], b['text'], time.time())
                   for gid, sid in expected.items() if gid not in existing]
        inserted = 0
        if apply and missing:
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO system_gifts(id,sid,coins,title,text,status,created) "
                                "VALUES(%s,%s,%s,%s,%s,'pending',%s) ON CONFLICT(id) DO NOTHING", missing)
                inserted = cur.rowcount
        if apply:
            # ON CONFLICT may skip a gift committed after our preflight read.
            # Recheck in this transaction so any conflict rolls back our rows.
            if set(checked_rows()) != set(expected):
                raise ValueError('Expected broadcast gift is missing; no gifts queued')
        return dict(prefix=b['prefix'], coins=b['coins'], saves=len(sids),
                    already_queued=len(existing), missing=len(missing), inserted=inserted, applied=apply)


if __name__ == '__main__':
    import psycopg
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prefix', required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    broadcast = next((b for b in sg.BROADCASTS if b['prefix'] == args.prefix), None)
    if broadcast is None:
        ap.error('Unknown broadcast prefix')
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        print(json.dumps(queue_all(conn, broadcast, args.apply)))
