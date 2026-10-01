#!/usr/bin/env python3
"""📌 Pin (or unpin) one message at the top of Cả phố, from the server (server-side tool).

It only writes the one row of `chat_pins` (channel 'town'); the live service shows the pin to everyone on
Cả phố within 30 s (it reads that row by primary key every 30 s), at once on PostgreSQL (a NOTIFY), and on
its next start in any case. The message must be on Cả phố, not hidden and not deleted. Typical use: an
announcement written straight into the database (pid 'admin', name '📢 Ban quản lý Phố').

  python3 scripts/chat_pin.py --show                       # what is pinned now
  python3 scripts/chat_pin.py --msg 5496 --dry-run         # check the message, write nothing
  python3 scripts/chat_pin.py --msg 5496                   # pin it (replaces the current pin)
  python3 scripts/chat_pin.py --unpin

The database: --pg <postgresql://...> or DATABASE_URL (production), else --db <SQLite file> (GAME_DB,
storage/game.sqlite3). It never runs DDL: before the release that creates `chat_pins` (schema 10) is live,
it refuses to run.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTIFY_CHANNEL = 'mnl_live'      # game/live_chat.py NOTIFY_CHANNEL, live/app.py


def _when(t) -> str:
    return datetime.datetime.fromtimestamp(float(t), datetime.timezone(datetime.timedelta(hours=7))).strftime('%d/%m/%Y %H:%M:%S')


class Side:
    """One connection, `?` placeholders on both backends."""

    def __init__(self, pg_url: str | None, db_path: str | None, schema: str | None = None):
        self.pg = bool(pg_url)
        if self.pg:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError:
                sys.exit('Thiếu thư viện psycopg (PYTHONPATH tới shared/pyvendor?).')
            self.conn = psycopg.connect(pg_url, autocommit=False, row_factory=dict_row, application_name='mnl-chat-pin')
            self.conn.execute("SELECT set_config('statement_timeout', '5000', false), set_config('lock_timeout', '3000', false)")
            if schema:
                self.conn.execute("SELECT set_config('search_path', %s, false)", (schema,))
        else:
            if not db_path or not Path(db_path).exists():
                sys.exit(f'Không thấy cơ sở dữ liệu: {db_path}')
            self.conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute('PRAGMA busy_timeout=10000')

    def q(self, sql: str, args=()):
        if self.pg:
            return self.conn.execute(sql.replace('?', '%s'), args)
        return self.conn.execute(sql, args)

    def one(self, sql: str, args=()):
        r = self.q(sql, args).fetchone()
        return dict(r) if r is not None else None

    def has_table(self, name: str) -> bool:
        if self.pg:
            return self.one('SELECT to_regclass(?) AS t', (name,))['t'] is not None
        return self.one("SELECT 1 AS t FROM sqlite_master WHERE type='table' AND name=?", (name,)) is not None

    def begin(self):
        if not self.pg:
            self.conn.execute('BEGIN IMMEDIATE')

    def commit(self):
        self.conn.commit() if self.pg else self.conn.execute('COMMIT')

    def rollback(self):
        self.conn.rollback() if self.pg else self.conn.execute('ROLLBACK')

    def notify(self):
        if self.pg:
            self.q('SELECT pg_notify(?, ?)', (NOTIFY_CHANNEL, json.dumps(dict(op='pin'))))

    def close(self):
        self.conn.close()


def show_msg(m: dict) -> str:
    text = (m['text'] or '').replace('\n', ' ⏎ ')
    return f"#{m['id']} [{m['channel']}] {m['name']} (pid {m['pid']}, {_when(m['at'])}): {text[:160]}{'…' if len(text) > 160 else ''}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pg', default=os.environ.get('DATABASE_URL') or None, help='PostgreSQL URL (default: DATABASE_URL)')
    ap.add_argument('--db', default=os.environ.get('GAME_DB', str(ROOT / 'storage' / 'game.sqlite3')), help='SQLite file (when no --pg)')
    ap.add_argument('--schema', help='PostgreSQL search_path (tests)')
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument('--msg', type=int, help='the chat_messages.id to pin on Cả phố')
    what.add_argument('--unpin', action='store_true', help='remove the pin of Cả phố')
    what.add_argument('--show', action='store_true', help='print the current pin, write nothing')
    ap.add_argument('--by', default='admin', help="who pinned it (chat_pins.by_pid; default 'admin')")
    ap.add_argument('--dry-run', action='store_true', help='check and print, write nothing')
    a = ap.parse_args(argv)
    side = Side(a.pg, None if a.pg else a.db, a.schema)
    try:
        if not side.has_table('chat_pins'):
            print('Chưa có bảng chat_pins: bản phát hành có ghim tin chưa chạy trên máy chủ này. Không ghi gì.', file=sys.stderr)
            return 2
        cur = side.one("SELECT p.msg, p.by_pid, p.at, m.id, m.channel, m.pid, m.name, m.text, m.at AS mat FROM chat_pins p "
                       "LEFT JOIN chat_messages m ON m.id=p.msg WHERE p.channel='town'")
        if cur:
            m = dict(cur, at=cur['mat']) if cur['id'] is not None else None
            print(f"Đang ghim: {show_msg(m) if m else '#' + str(cur['msg']) + ' (tin không còn)'} · ghim bởi {cur['by_pid']} lúc {_when(cur['at'])}")
        else:
            print('Đang ghim: (không có)')
        if a.show:
            return 0
        if a.unpin:
            if not cur:
                print('Không có gì để bỏ ghim.')
                return 0
            if a.dry_run:
                print('Thử (không ghi): sẽ bỏ ghim.')
                return 0
            side.begin()
            try:
                side.q("DELETE FROM chat_pins WHERE channel='town'")
                side.notify()
                side.commit()
            except BaseException:
                side.rollback()
                raise
            print('Đã bỏ ghim. Người chơi thấy trong vòng 30 giây.')
            return 0
        m = side.one('SELECT id, channel, pid, name, text, at, hidden, deleted FROM chat_messages WHERE id=?', (a.msg,))
        if not m:
            print(f'Không có tin #{a.msg}. Không ghi gì.', file=sys.stderr)
            return 2
        if m['channel'] != 'town' or m['hidden'] or m['deleted']:
            print(f"Tin #{a.msg} không ghim được (kênh {m['channel']}, ẩn {m['hidden']}, thu hồi {m['deleted']}). Không ghi gì.", file=sys.stderr)
            return 2
        print('Tin sẽ ghim: ' + show_msg(m))
        if a.dry_run:
            print('Thử (không ghi).')
            return 0
        by = str(a.by or 'admin')[:40]
        side.begin()
        try:
            side.q("INSERT INTO chat_pins(channel, msg, by_pid, at) VALUES('town', ?, ?, ?) "
                   'ON CONFLICT(channel) DO UPDATE SET msg=excluded.msg, by_pid=excluded.by_pid, at=excluded.at', (a.msg, by, time.time()))
            side.notify()
            side.commit()
        except BaseException:
            side.rollback()
            raise
        print(f'Đã ghim tin #{a.msg} lên đầu Cả phố. Người chơi thấy trong vòng 30 giây.')
        return 0
    finally:
        side.close()


if __name__ == '__main__':
    sys.exit(main())
