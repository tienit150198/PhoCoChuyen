"""🏆 Weekly kéo co chó sủa prizes: the game is removed (game/dog_bark.py), so no week is settled any more and no new
prize is made. What stays, for rollback safety and for what players already hold:

* the five secret titles (journey.TITLES): a save holding one must keep validating, on this build and older ones;
* apply_fx: a 'bark_weekly' live_effects row already written by 2.4.15 or older still pays once (game/live_effects.py);
* forget: an erased account loses its link to past trophies (as before).

The past snapshots (leaderboard_meta 'bark-weekly:*') and the cursor stay untouched in the database.
"""
from __future__ import annotations

import datetime

from . import dog_bark as bark

MINIMUM = 30
FX = 'bark_weekly'
META = 'bark-weekly:'
CURSOR = META + 'cursor'
COINS = (2_000_000, 1_000_000, 500_000, 250_000, 100_000)
TITLE_IDS = ('bark_king', 'bark_silver', 'bark_bronze', 'bark_fourth', 'bark_fifth')
TITLE_NAMES = dict(zip(TITLE_IDS, ('Vua kéo co chó sủa', 'Á quân kéo co chó sủa', 'Đệ tam kéo co chó sủa',
                                 'Cao thủ kéo co chó sủa', 'Tài năng kéo co chó sủa')))
EMOJI = ('👑', '🥈', '🥉', '🏅', '🎖️')


def titles(make):
    return [make(tid, 'secret', EMOJI[i], TITLE_NAMES[tid],
                 f'Đạt hạng {i+1} giải kéo co chó sủa tuần, ít nhất {MINIMUM} trận hợp lệ.', lambda x: False, True)
            for i, tid in enumerate(TITLE_IDS)]


def apply_fx(s, p, amount):
    from . import engine as e, journey as jr
    data = p.get('data') if isinstance(p.get('data'), dict) else {}
    rank, week = data.get('rank'), data.get('week')
    e.need(type(rank) is int and 1<=rank<=len(COINS), 'Hạng giải kéo co không hợp lệ.')
    tid = TITLE_IDS[rank-1]
    try:
        day = datetime.date.fromisoformat(week)
        valid_week = day.weekday() == 0 and day.isoformat() == week
    except (TypeError, ValueError):
        valid_week = False
    e.need(valid_week and data.get('title') == tid and amount == COINS[rank-1], 'Giải kéo co không hợp lệ.')
    j = s['journey']
    jr._wallet(j, amount, 'life', f'🐕 Giải kéo co tuần {week} · hạng {rank}')
    if tid not in j['titles']:
        j['titles'][tid] = j['life_day']
        jr._news(j, 'titles', 'titles', [tid])
    return f'🏆 Hạng {rank} kéo co tuần: +{bark.fmt(amount)} xu và danh hiệu {TITLE_NAMES[tid]}.'


def forget(db, sid):
    """Keep final numbers but erase the deleted account's link to past trophies."""
    import json
    # Serialize with a 2.4.15 worker settling a week (it locks the same cursor row), so a deleting account cannot
    # receive a new weekly effect between cleanup and account removal in Store.delete.
    db.execute('SELECT v FROM leaderboard_meta WHERE k=? FOR UPDATE', (CURSOR,)).fetchone()
    db.execute('DELETE FROM live_effects WHERE sid=? AND kind=?', (sid, FX))
    rows = db.execute('SELECT k,v FROM leaderboard_meta WHERE k LIKE ? AND v LIKE ? FOR UPDATE',
                      (META+'____-__-__', '%'+sid+'%')).fetchall()
    for r in rows:
        winners = json.loads(r['v'])
        for winner in winners:
            if winner.get('sid') == sid:
                winner['sid'] = ''
        db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(winners), r['k']))
