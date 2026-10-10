"""Publish the approved 2.0 notice once, only after production verification.

Default prints the draft and checks health/event state without writing.
After deployment smoke checks: python scripts/publish_major_release.py --publish
Uses the existing DATABASE_URL / GAME_NAMESPACE. Never prints credentials.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = '2.0.0'
KEY = 'release_notice_2_0_0'


def message(ends: float) -> str:
    until = dt.datetime.fromtimestamp(ends, dt.timezone(dt.timedelta(hours=7))).strftime('%H:%M ngày %d/%m/%Y')
    return (
        '✨ PHỐ CÓ CHUYỆN 2.0 — Khu phố khoác áo mới!\n'
        '🏝️ Giao diện 2.5D mới, 50 nơi làm nghề có ngoại thất và nội thất riêng, thêm cảnh phố, avatar và phụ kiện. '
        'Nhà ở có không gian 3D để ghé thăm, sơn sửa và trang trí.\n'
        '⚙️ Muốn dùng lại giao diện cũ? Vào Cài đặt → Giao diện, tắt “Giao diện mới”. '
        'Bật lại bất cứ lúc nào, nhân vật và tiến độ vẫn giữ nguyên.\n'
        '📷 Gặp lỗi? Vào Góp ý, mô tả giúp mình và gửi tối đa 3 ảnh trong một lần.\n'
        '🎪 2 ngày vàng, tăng tỷ lệ thắng cược Chợ Đen: Chiếu trong, lô tô và vé cào! '
        f'Chương trình kết thúc lúc {until} (giờ Việt Nam). Chúc cả phố chơi vui!'
    )


def publish(db, *, health_version: str) -> dict:
    """One transaction for the message, pin and retry marker; caller commits."""
    if health_version != VERSION:
        raise ValueError('Máy chủ chưa chạy đúng bản 2.0.0; chưa thông báo.')
    # Transaction-scoped lock prevents two operators/retries creating duplicate messages.
    db.begin()
    db.execute('SELECT pg_advisory_xact_lock(?)', (20001011,))
    found = db.execute('SELECT value FROM mnl_meta WHERE key=?', (KEY,)).fetchone()
    if found:
        return {'id': int(found[0]), 'already_published': True}
    # A wait for the lock can cross the deadline. Only fresh persisted state may authorize a new notice.
    from game import fair_golden_days as golden
    event = golden.status(db)
    if not event.get('active'):
        raise ValueError('Hai ngày vàng chưa hoạt động; chưa thông báo.')
    ends = event['ends']
    now = float(db.execute('SELECT EXTRACT(EPOCH FROM statement_timestamp())').fetchone()[0])
    row = db.execute(
        "INSERT INTO chat_messages(channel,pid,name,av,text,at,adm) VALUES('town','admin',?,'',?,?,1) RETURNING id",
        ('📢 Ban quản lý Phố', message(ends), now),
    ).fetchone()
    mid = row[0]
    db.execute("INSERT INTO chat_pins(channel,msg,by_pid,at) VALUES('town',?,'admin',?) "
               'ON CONFLICT(channel) DO UPDATE SET msg=excluded.msg,by_pid=excluded.by_pid,at=excluded.at', (mid, now))
    db.execute('INSERT INTO mnl_meta(key,value) VALUES(?,?)', (KEY, str(mid)))
    # Existing unhide notification also delivers a newly inserted operator message to live buffers.
    db.execute('SELECT pg_notify(?,?)', ('mnl_live', json.dumps({'op': 'unhide', 'id': mid})))
    db.execute('SELECT pg_notify(?,?)', ('mnl_live', '{"op":"pin"}'))
    return {'id': mid, 'already_published': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--health', default='http://127.0.0.1:8765/api/health')
    args = parser.parse_args()
    from game import fair_golden_days as golden
    from game.storage import Store
    with urlopen(args.health, timeout=10) as response:
        health = json.load(response)
    store = Store(Path(os.environ.get('GAME_NAMESPACE', str(ROOT / 'storage' / 'game'))))
    try:
        with store.connect() as db:
            event = golden.status(db)
            version = health.get('version', health.get('game_version', ''))
            if args.publish:
                print(json.dumps(publish(db, health_version=version), ensure_ascii=False))
            else:
                print(json.dumps({'publish': False, 'version': version, 'event': event}, ensure_ascii=False))
                if event.get('ends'):
                    print(message(event['ends']))
    finally:
        store.close_pool()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
