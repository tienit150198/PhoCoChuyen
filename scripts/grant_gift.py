#!/usr/bin/env python3
"""🎁 Quà từ Phố Có Chuyện: queue a private gift of coins for ONE save (server-side tool).

It only inserts a row in `system_gifts` (status 'pending'); it never touches a save. The game
pays the coins into that player's 👛 Ví on their next load (through the normal command path,
request id sysgift-<id>, once) and shows them a card with the title and text until they press
"Nhận quà 💛". See game/system_gift.py.

  python3 scripts/grant_gift.py --sid <sid> --coins 100 --title "..." --text "..." --dry-run
  python3 scripts/grant_gift.py --sid <sid> --coins 100 --title "..." --text "..." --id sorry-20261001-ab12

Idempotent by --id: running the same command again changes nothing ("đã có"). Reusing an id
for a different save, amount or text is refused. Without --id the id is derived from the save,
the coins and the words, so an exact repeat is a no-op too. --user <username> finds the sid of
an account. Coins: 1..1000.

With DATABASE_URL set (PostgreSQL, see docs/POSTGRES.md) --db is ignored. The table comes with
the release (schema 4); on PostgreSQL the tool refuses to run before that release is live.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game import db as dbm, system_gift as sg  # noqa: E402
from game.storage import Store  # noqa: E402


def _table_ready(path: str) -> bool:
    """PostgreSQL: the release that creates system_gifts is live (the tool never runs the DDL)."""
    pool = dbm.pool_for(path)
    if not pool:
        return True
    db = pool.connect()
    try:
        return db.raw.execute("SELECT to_regclass('system_gifts')").fetchone()[0] is not None
    finally:
        db.close()


def _when(t) -> str:
    if not t:
        return '-'
    return datetime.datetime.fromtimestamp(float(t), datetime.timezone(datetime.timedelta(hours=7))).strftime('%d/%m/%Y %H:%M:%S')


def describe(store: Store, sid: str) -> str:
    """Who this save is (account or guest, story, wallet): read only."""
    with store.connect() as db:
        acc = db.execute('SELECT username,display FROM accounts WHERE sid=?', (sid,)).fetchone()
        row = db.execute('SELECT state,updated_at FROM sessions WHERE sid=?', (sid,)).fetchone()
    who = f'tài khoản {acc["username"]} ({acc["display"]})' if acc else 'khách (không có tài khoản)'
    try:
        j = store.parse_state(row['state'], sid).get('journey') or {}
        save = f"hành trình: {'có' if j.get('story') else 'KHÔNG (quà sẽ chờ)'}, ví {j.get('wallet')} xu"
    except (ValueError, TypeError, AttributeError):
        save = 'không đọc được bản lưu'
    return f'{who}; {save}; lưu lần cuối {row["updated_at"]} UTC'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--db', default=os.environ.get('GAME_DB', str(ROOT / 'storage' / 'game.sqlite3')))
    who = ap.add_mutually_exclusive_group(required=True)
    who.add_argument('--sid', help='the save (sessions.sid)')
    who.add_argument('--user', help='an account username: its save')
    ap.add_argument('--coins', type=int, required=True, help=f'1..{sg.MAX_COINS}')
    ap.add_argument('--title', required=True, help=f'card title (<= {sg.TITLE_MAX} chars)')
    ap.add_argument('--text', required=True, help=f'card text (<= {sg.TEXT_MAX} chars)')
    ap.add_argument('--id', help='stable gift id (letters, digits, . _ -; 3-64 chars)')
    ap.add_argument('--dry-run', action='store_true', help='check and print, write nothing')
    a = ap.parse_args()
    if not dbm.database_url() and not Path(a.db).exists():
        sys.exit(f'Không thấy cơ sở dữ liệu: {a.db}')
    if not _table_ready(a.db):
        sys.exit('Chưa có bảng system_gifts: bản phát hành có quà chưa chạy trên máy chủ này. Không ghi gì.')
    store = Store(a.db, story=True)
    sid = a.sid
    if a.user:
        with store.connect() as db:
            row = db.execute('SELECT sid FROM accounts WHERE username=?', (a.user.strip().lower(),)).fetchone()
        if not row:
            sys.exit(f'Không có tài khoản {a.user}.')
        sid = row['sid']
    try:
        out = sg.grant(store, sid, a.coins, a.title, a.text, a.id, dry_run=a.dry_run)
    except sg.GiftError as e:
        print(f'Không ghi gì: {e}', file=sys.stderr)
        return 2
    g = out['gift']
    print(f'Người nhận: sid {sid[:12]}… · {describe(store, sid)}')
    print(json.dumps({k: g[k] for k in ('id', 'sid', 'coins', 'title', 'text')}, ensure_ascii=False, indent=1))
    if out['status'] == 'would_create':
        print(f'Thử (không ghi): sẽ tạo quà {g["id"]}, +{g["coins"]} xu, chờ người chơi tải game.')
    elif out['status'] == 'created':
        print(f'Đã tạo quà {g["id"]}: +{g["coins"]} xu, trạng thái pending. Người chơi nhận ở lần tải game tới.')
    else:
        print(f'Quà {g["id"]} đã có (không ghi thêm): trạng thái {g["status"]}, tạo {_when(g["created"])}, '
              f'vào ví {_when(g["applied_at"])}, đã xem {_when(g["seen_at"])} (giờ VN).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
