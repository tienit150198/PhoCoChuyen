#!/usr/bin/env python3
"""Make a test account that can try everything (server-side tool).

Creates the account if it does not exist (or resets its password with
--reset-password), then maxes its save: every chapter done, all workplaces
unlocked and started, every career at a high level, office jobs signed,
all titles, skills at the top step, and plenty of money in the wallet and
in each workplace's fund. The save still passes `validate_state`.

The password is never taken from the command line (it would land in the
shell history): it is read from $GRANT_PASSWORD or asked for.

  python3 scripts/grant_admin.py --db storage/game.sqlite3 --username admin

Run it on the machine that hosts the game's database. Players who are signed
in to that account see the new save after a reload. With DATABASE_URL set (the
game runs on PostgreSQL, see docs/POSTGRES.md) --db is ignored and the account is
made in that database.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game import accounts, db as dbm, employment, journey  # noqa: E402
from game.engine import migrate_state, money, validate_state  # noqa: E402
from game.storage import Store  # noqa: E402

XP = 2700          # career level 31; all careers together reach maturity 30
SERVED = 60        # tasks per career, enough for every skill's top step
WALLET = 1_000_000
FUND = 100_000


def max_out(s: dict) -> dict:
    j = s['journey']
    j['intro'] = True
    j['chapter'] = journey.LAST + 1
    j['done'] = list(range(1, journey.LAST + 1))
    j['in_debt'] = False
    for cid, c in s['careers'].items():
        c['started'] = True
        c['xp'] = max(int(c.get('xp', 0)), XP)
        c.setdefault('metrics', {})['served'] = max(int(c['metrics'].get('served', 0)), SERVED)
        if c['money'] < FUND:
            add = FUND - c['money']
            money(s, c, add, 'Vốn thử nghiệm của tài khoản quản trị', category='owner_capital')
            c['earnings'] -= add  # capital, not income (like jr_invest)
        if employment.required(cid) and c.get('job', {}).get('status') != 'hired':
            c['job'] = employment.hired_record(cid, day=int(c.get('day', 1)))
    j['unlocked'] = list(s['careers'])
    j['wallet'] = max(j['wallet'], WALLET)
    j['stats']['max_wallet'] = max(j['stats'].get('max_wallet', 0), j['wallet'])
    day = int(j['life_day'])
    for t in journey.TITLES:
        j['titles'].setdefault(t['id'], day)
    return s


def ensure_account(store: Store, username: str, display: str, password: str | None, reset: bool) -> str:
    username = accounts.clean_username(username)
    with store.connect() as db:
        row = db.execute('SELECT sid FROM accounts WHERE username=?', (username,)).fetchone()
    if row:
        if reset:
            accounts.clean_password(password)
            with store.connect() as db:
                db.execute('UPDATE accounts SET pw=?,updated_at=CURRENT_TIMESTAMP WHERE username=?',
                           (accounts.hash_password(password), username))
                db.execute('DELETE FROM logins WHERE sid=?', (row['sid'],))
            print(f'Đã đặt lại mật khẩu cho {username}; các máy đang đăng nhập cần đăng nhập lại.')
        return row['sid']
    token, _, _ = store.session()
    accounts.register(store, token, dict(username=username, password=password, confirm=password, display=display))
    with store.connect() as db:
        sid = db.execute('SELECT sid FROM accounts WHERE username=?', (username,)).fetchone()['sid']
    print(f'Đã tạo tài khoản {username}.')
    return sid


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--db', default=os.environ.get('GAME_DB', str(ROOT / 'storage' / 'game.sqlite3')))
    ap.add_argument('--username', default='admin')
    ap.add_argument('--display', default='Admin')
    ap.add_argument('--reset-password', action='store_true', help='set a new password on an existing account')
    a = ap.parse_args()
    if not dbm.database_url() and not Path(a.db).exists():
        sys.exit(f'Không thấy cơ sở dữ liệu: {a.db}')
    store = Store(a.db, story=True)
    with store.connect() as db:
        exists = db.execute('SELECT 1 FROM accounts WHERE username=?', (a.username.strip().lower(),)).fetchone()
    password = None
    if not exists or a.reset_password:
        password = os.environ.get('GRANT_PASSWORD') or getpass.getpass('Mật khẩu cho tài khoản: ')
    sid = ensure_account(store, a.username, a.display, password, a.reset_password)
    db = store.connect()
    try:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT state,revision FROM sessions WHERE sid=?' + dbm.for_update(db), (sid,)).fetchone()
        state = max_out(migrate_state(store.parse_state(row['state'], sid)))
        validate_state(state)
        db.execute('UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=?',
                   (json.dumps(state, ensure_ascii=False), row['revision'] + 1, sid))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(f'Xong: {a.username} đã mở toàn bộ {len(state["careers"])} nơi làm việc, đủ chương và danh hiệu. Tải lại trang để thấy.')


if __name__ == '__main__':
    main()
