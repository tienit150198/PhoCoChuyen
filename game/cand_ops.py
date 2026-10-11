"""👮 Công an phường Mây across players (owner spec 11/10, the player-written "Công an Phường Mây" doc the owner approved).

Two things one player officer does to another player, both through POST /api/marriage/<op> (game/marriage.py act →
_more_actions → ACTIONS here), every rule checked here, nothing decided by the page.

A. Commanders (posts COMMANDERS: Phó Trưởng Công an phường and up) "xét thi đua … toàn quân, … khai trừ … sai phạm mức
   cao nhất":
   * cand_force {}: 👥 Toàn lực lượng, the force from game/cand_roster.py (a pid per row, never a sid);
   * cand_hon {pid}: 🏅 Khen thưởng thi đua: the officer's ext hon += {t, by}, +HON_ADJ to their next close's ★
     (org adj, capped at 10), an inbox line. One per commander per Vietnam day, one per officer per Vietnam day (whoever
     gives it), never oneself: two cand_acts rows with fixed ids ('hon:<by>:<day>', 'hont:<target>:<day>') inserted
     ON CONFLICT DO NOTHING in the same transaction as the save (a second one finds a row: nothing written);
   * cand_out {pid, confirm}: 🚫 Khai trừ: only an officer whose ext sev has a grave fault (a bribe, a case gone
     badly wrong) within SEV_DAYS real days, whose post ranks below the commander's, never oneself; promotion.mark_expel
     on their save (done at their next end_day: jail, the contract ended, the ban), a cand_acts row, an inbox line. At
     most OUT_DAY_MAX a commander a Vietnam day.
   A commander acts only while on the ladder at such a post, not suspended, not jailed, not on the way out.

B. The patrol at Chợ đen (PvP). An officer on duty (the police shift open, hired at 'cap-kv' on the ladder, not
   suspended, not jailed, not on the way out) taps another player there → cand_stop {pid, act}, act one of ACTS:
   🔎 Lục soát tư trang / 📝 Phạt hành chính / 🚓 Tạm giữ / ⛓️ Bắt giữ. The evidence is the target's own save:
   journey['fair_ev'] {t, s} (game/fair_bm.py note_round, written by every paid luck round, the round's stake), today's
   journey['fair'].net and journey['fair_big'].n (50k+ rounds today):
   * no paid luck round in the last EVIDENCE_S (15 min): nothing to stop for (refused, nothing recorded);
   * level() — owner rules 09/10–11/10 kept: a small player (that round's stake < 50,000 and today's net ≤ 300,000)
     is never fined, held or arrested: level 0, a search only. Otherwise level 1 (📝 the fine); level 2 (🚓 also) for
     a heavy player: HOLD_BIG (20) or more 50k+ rounds today or that round's stake ≥ HOLD_STAKE (300,000); level 3 (⛓️
     also) for the heaviest: more than ARREST_BIG (50) 50k+ rounds today or today's net above 300,000. A lighter act
     than the level allows is always allowed.
   * 📝 Phạt hành chính: 30 % of THAT round's stake (fair_bm.round_fine, the owner's rule for every Chợ đen fine; the
     stake is the one read when the stop opened, cand_stops.stake), taken by fair_bm.take_total (wallet, then bank,
     then the Mây savings / gold / Mây Coin like the raid) and gone (never paid to the officer). 🚓 Tạm giữ:
     HOLD_DAYS (1) day in the trại tạm giữ ('bm'), no fine. ⛓️ Bắt giữ: ARREST_DAYS (3) days and the 30 % fine.
   * 🔎 Lục soát: done at once (no prompt): the officer reads what was found and which acts the evidence allows; the
     target is told. A search never holds back a follow-up penalty (by any officer).
   * Limits: a target at most once per TARGET_GAP_S (30 min) across all officers (a search holds back only the same
     officer's next search); an officer at most OFFICER_DAY_MAX (10) stops a Vietnam day, one open stop at a time, one
     penalty stop on the same player a day. No xu for a stop ever: the reward is +0.1 ★ (org adj +1) for a stop that
     ends in a penalty, or the Liêm chính of a refused envelope (promotion.report_bribe), for at most REWARD_DAY_MAX (3)
     stops a Vietnam day and never when the two are friends (no farming between friends).
   The penalty acts open a stop (cand_stops status 'ask') and the target is asked (a live push: pg_notify 'mnl_live'
   {op: 'cand'} → live/cand.py; the page polls cand_poll while it waits when the live service has no 'cand'):
   * cand_answer {id, bribe: 0} 🤝 Hợp tác: the penalty now. No answer within ASK_S (60 s): the same ('late').
   * cand_answer {id, bribe: 1..BRIBE_MAX (5000), ≤ the wallet}: 💵 Đưa phong bì: status 'offer'; the officer sees the
     amount: cand_decide {id, take: true} 💵 Nhận: the envelope moves target → officer in ONE marriage._mutate of both
     saves, and the officer's detection is rolled: p = min(P_MAX 85 %, P0 5 % + P_STEP 0.5 % × n), n the envelopes
     this officer took before (journey 'cand_br', fair_bm.BR_KEY; back to 0 after BR_RESET_S, 7 days without one).
     Caught: promotion.bribe (one grade down, the integrity mark, the grave fault 'bribe' a commander may expel for)
     and the envelope confiscated (the officer keeps nothing; the player lost it). Not caught: the officer keeps it
     and the player walks. cand_decide {take: false} Từ chối & lập biên bản: the penalty applies and the officer gets
     promotion.report_bribe (Liêm chính +1). The officer silent past OFFER_S: the penalty applies ('lapse').
     The odds are never shown or sent.
   A stop nobody settles (both pages gone) is settled by either party's next cand_* call; past STALE_S it lapses
   without a penalty ('gone').
   Every move of a stop is a guarded UPDATE from the status before, in the same transaction as the saves, so a stop
   is settled once. Tables: cand_stops, cand_acts (game/pg_schema.py SCHEMA_VERSION 40). Nothing here is in the save
   but the effects (wallets, jail, the org record), so older builds load every save.

Pure rules (officer_block, evidence, level, penalize, take_bribe, commend, expel_check…) take a save and a time and are
unit-tested without a database (tests/test_cand_ops.py); the handlers reach the database and the saves only through
_read, _mutate, _notify, _lock, _push (the tests put an in-memory SQLite store and in-memory saves behind them).
"""
from __future__ import annotations

import json
import random
import re
import secrets
import time

from . import org as ORG
from . import org_content as OC

CAREER = 'police'
ORG_ID = 'cand'
COMMANDERS = ('pho_truong_ca', 'truong_ca', 'pho_phong', 'truong_phong', 'tro_ly', 'pgd', 'gd')
POST_ORDER = {p['id']: i for i, p in enumerate(OC.CAND_POSTS)}   # a later post ranks above an earlier one

# ---- the patrol (B)
ACTS = ('search', 'fine', 'hold', 'arrest')
ACT_LEVEL = dict(search=0, fine=1, hold=2, arrest=3)
ACT_NAME = dict(search='🔎 Lục soát tư trang', fine='📝 Phạt hành chính', hold='🚓 Tạm giữ', arrest='⛓️ Bắt giữ')
EVIDENCE_S = 15 * 60          # the target's last paid luck round at most this old
TARGET_GAP_S = 30 * 60        # a target stopped at most once in this window (all officers)
FOLLOW_S = 5 * 60             # ... except the same officer following up their own search
OFFICER_DAY_MAX = 10          # stops an officer may open a Vietnam day (searches included)
REWARD_DAY_MAX = 3            # stops a Vietnam day that earn the officer anything (★ or Liêm chính)
REWARD_ADJ = 1                # +0.1 ★ (org adj, tenths) for a stop ending in a penalty
ASK_S = 60                    # the target's time to answer
OFFER_S = 60                  # the officer's time to decide on an envelope (after ASK_S)
STALE_S = 30 * 60             # an open stop older than this lapses without a penalty
BRIBE_MAX = 5000
SMALL_STAKE = 50_000          # fair_bm.BIG_STAKE_FROM: below it (and a net ≤ SMALL_NET) a small player
SMALL_NET = 300_000           # fair_bm.ARREST_FROM
HOLD_BIG = 20                 # 50k+ rounds today from which 🚓 Tạm giữ is allowed
HOLD_STAKE = 300_000          # ... or a round staking this much
ARREST_BIG = 50               # fair_bm.SPAM_ROUNDS: past it ⛓️ Bắt giữ is allowed (or a net above SMALL_NET)
HOLD_DAYS = 1
ARREST_DAYS = 3               # fair_bm.JAIL_DAYS
FINE_LABEL = '👮 Công an phường phạt hành chính (chợ đen)'
GIVE_LABEL = '💵 Phong bì đưa công an (chợ đen)'
TAKE_LABEL = '💵 Phong bì ở chợ đen'
WALLET_KIND = 'life'
# ---- the envelopes (never shown)
P0, P_STEP, P_MAX = 0.05, 0.005, 0.85
BR_RESET_S = 7 * 86400
# ---- commanders (A)
SEV_DAYS = 7
HON_ADJ = 3                   # +0.3 ★ at the officer's next close
OUT_DAY_MAX = 3
ROSTER_MAX = 100

OPEN = ('ask', 'offer')
PENALTY_OUTCOMES = ('coop', 'late', 'refused', 'lapse', 'void')   # the penalty applied
PID_RE = re.compile(r'[0-9a-f]{16}')
ID_RE = re.compile(r'cs[0-9a-f]{16}')
INBOX = 'cand'


def now() -> float:
    return time.time()


def vn_day(t: float) -> str:
    from .fair import vn_date
    return vn_date(t)


def _xu(n) -> str:
    return f'{int(n):,}'.replace(',', '.')


def _mr():
    from . import marriage as mr
    return mr


def need(cond, message: str, code: str = 'cand_error', status: int = 409):
    _mr().need(cond, message, code, status)


# ===================================================================================== pure rules (no database)
def police_of(s: dict):
    """(career, record, org block) of a save on the CAND ladder now; (c, None, None) when it is not."""
    c = (s.get('careers') or {}).get(CAREER) if isinstance(s, dict) else None
    if not isinstance(c, dict):
        return None, None, None
    from . import promotion as pm
    rec, x = pm.org_live(s, c, CAREER)
    if not x or x.get('org') != ORG_ID:
        return c, None, None
    return c, rec, x


def _out(s: dict, rec) -> bool:
    from . import promotion as pm
    return pm.banned(s, CAREER) or pm.expel_due(rec)


def officer_block(s: dict, t: float) -> str | None:
    """Why this save may not patrol Chợ đen now; None: an officer on duty."""
    from . import jail
    if jail.active((s or {}).get('journey'), t):
        return 'Bạn đang ở trại tạm giữ.'
    c, rec, x = police_of(s)
    if x is None:
        return 'Chỉ cán bộ Công an phường Mây đang công tác mới được kiểm tra người khác.'
    if _out(s, rec):
        return 'Bạn đã có quyết định khai trừ, không còn làm nhiệm vụ.'
    if ORG.suspended(x):
        return 'Bạn đang bị tạm đình chỉ công tác.'
    if not c.get('open'):
        return 'Mở ca trực ở Công an phường rồi hẵng đi tuần nhé.'
    return None


def commander_block(s: dict, t: float) -> str | None:
    """Why this save may not act as a commander now; None: it may."""
    from . import jail
    if jail.active((s or {}).get('journey'), t):
        return 'Bạn đang ở trại tạm giữ.'
    c, rec, x = police_of(s)
    if x is None or x['p'] not in COMMANDERS:
        return 'Chỉ chỉ huy từ Phó Trưởng Công an phường trở lên mới xét thi đua, khai trừ.'
    if _out(s, rec):
        return 'Bạn đã có quyết định khai trừ.'
    if ORG.suspended(x):
        return 'Bạn đang bị tạm đình chỉ công tác.'
    return None


def level(stake: int, net: int, big: int) -> int:
    """0 a small player (search only), 1 the fine, 2 also Tạm giữ, 3 also Bắt giữ (see the module's doc)."""
    if stake < SMALL_STAKE and net <= SMALL_NET:
        return 0
    if net > SMALL_NET or big > ARREST_BIG:
        return 3
    if big >= HOLD_BIG or stake >= HOLD_STAKE:
        return 2
    return 1


def allowed(lvl: int) -> list[str]:
    return [a for a in ACTS if ACT_LEVEL[a] <= lvl]


def evidence(j, t: float) -> dict | None:
    """What the target's save shows: their last paid luck round (stake, how long ago), today's net and 50k+ rounds,
    the level. None: no such round in the last EVIDENCE_S."""
    from . import fair_bm as bm
    if not isinstance(j, dict):
        return None
    ev = j.get(bm.EV_KEY)
    if not isinstance(ev, dict) or type(ev.get('t')) is not int or type(ev.get('s')) is not int or ev['s'] <= 0:
        return None
    age = t - ev['t'] / 1000
    if age > EVIDENCE_S or age < -60:
        return None
    today = vn_day(t)
    f = j.get('fair')
    net = f['net'] if isinstance(f, dict) and f.get('date') == today and type(f.get('net')) is int else 0
    b = j.get(bm.SPAM_KEY)
    big = b['n'] if isinstance(b, dict) and b.get('d') == today and type(b.get('n')) is int else 0
    stake = ev['s']
    return dict(stake=stake, net=net, big=big, ago=int(max(0, age)), lvl=level(stake, net, big))


def fine_of(stake: int) -> int:
    from . import fair_bm as bm
    return bm.round_fine(stake)


def findings(ev: dict) -> str:
    """🔎 What a search turns up (no odds, no percentages: the receipts in the pocket)."""
    mins = max(1, -(-ev['ago'] // 60))
    line = f'🔎 Tìm thấy biên lai cược {_xu(ev["stake"])} xu, cách đây {mins} phút.'
    if ev['big']:
        line += f' Hôm nay {ev["big"]} ván lớn.'
    if ev['lvl'] == 0:
        return line + ' Chơi nhỏ: nhắc nhở, cho đi.'
    acts = [ACT_NAME[a] for a in allowed(ev['lvl']) if a != 'search']
    return line + ' Đủ căn cứ: ' + ', '.join(acts) + '.'


def penalize(s: dict, act: str, stake: int, t: float) -> dict:
    """The target's save: the act's penalty. {fine: xu taken, days: jail days now}."""
    from . import fair as FA
    from . import fair_bm as bm
    from . import jail
    j = s['journey']
    out = dict(fine=0, days=0)
    if act in ('fine', 'arrest'):
        due = fine_of(stake)
        if due > 0:
            f = FA._state(j, t)
            fine = bm.take_total(j, f, due, FINE_LABEL)
            if fine < due:   # like the raid: the rest from the Mây savings, gold, Mây Coin
                from .fair_hai import _take_parked
                fine += _take_parked(j, f, due - fine, FINE_LABEL)
            out['fine'] = fine
    if act in ('hold', 'arrest'):
        out['days'] = jail.arrest(j, 'bm', HOLD_DAYS if act == 'hold' else ARREST_DAYS, t)
    return out


def penalty_text(act: str, pen: dict) -> str:
    bits = []
    if pen.get('fine'):
        bits.append(f'nộp phạt {_xu(pen["fine"])} xu')
    if pen.get('days'):
        bits.append(f'tạm giữ {pen["days"]} ngày')
    return ACT_NAME[act] + (': ' + ', '.join(bits) if bits else '') + '.'


def br_count(j: dict | None, t: float) -> int:
    """Envelopes this officer took that still count (journey[fair_bm.BR_KEY]): 0 after BR_RESET_S without one."""
    from . import fair_bm
    b = j.get(fair_bm.BR_KEY) if isinstance(j, dict) else None
    if not isinstance(b, dict):
        return 0
    return 0 if b['t'] and t - b['t'] > BR_RESET_S else int(b['n'])


def detect_p(n: int) -> float:
    """The chance an envelope is found out, n envelopes taken before it (never shown)."""
    return min(P_MAX, P0 + P_STEP * max(0, int(n)))


_SALT = secrets.token_hex(8)   # per process: the draw cannot be worked out from the stop's id


def _roll(stop_id: str, p: float) -> bool:
    """The detection draw, fixed by the stop (a retried transaction draws the same); tests patch it."""
    return random.Random(f'cand-br|{stop_id}|{_SALT}').random() < p


def give_bribe(s: dict, amount: int) -> None:
    """The target's save: the envelope leaves the wallet (never on credit)."""
    from . import journey as jr
    j = s['journey']
    need(j['wallet'] >= amount, 'Ví không còn đủ tiền cho phong bì này.', 'cand_short')
    jr._wallet(j, -amount, WALLET_KIND, GIVE_LABEL)


def take_bribe(s: dict, amount: int, t: float, stop_id: str, roll=None) -> dict:
    """The officer's save takes the envelope: count it (journey cand_br), roll the detection. Caught: promotion.bribe (one grade
    down, the integrity mark, the grave fault) and nothing kept. Else the envelope in the wallet. {caught, line}."""
    from . import journey as jr
    from . import promotion as pm
    c, rec, x = police_of(s)
    if x is None:   # off the ladder meanwhile (fired, a new contract): a citizen pocketing it, nobody to demote
        jr._wallet(s['journey'], amount, WALLET_KIND, TAKE_LABEL)
        return dict(caught=False, line='')
    from . import fair_bm
    e = ORG.ext_of(rec, x)
    n = br_count(s['journey'], t)
    caught = (roll or _roll)(stop_id, detect_p(n))
    s['journey'][fair_bm.BR_KEY] = dict(n=min(10**6, n + 1), t=int(t))
    if caught:
        line = pm.bribe(s, c, CAREER, f'cand-{stop_id}')   # the demotion, the mark and the grave fault 'bribe'
        if not line:   # (the same stop's key seen today: never twice, but the grave fault is written all the same)
            ORG.add_sev(e, 'bribe', t)
        return dict(caught=True, line=line or '💵 Nhận phong bì: bị phát hiện, phong bì bị tịch thu.')
    jr._wallet(s['journey'], amount, WALLET_KIND, TAKE_LABEL)
    return dict(caught=False, line='')


def reward(s: dict, refused: bool) -> str:
    """The officer's save after a stop ending in a penalty: +0.1 ★, or the Liêm chính of a refused envelope."""
    from . import promotion as pm
    c, rec, x = police_of(s)
    if x is None:
        return ''
    if refused:
        return pm.report_bribe(s, c, CAREER)
    x['adj'] = min(10, x['adj'] + REWARD_ADJ)
    return '⭐ Hoàn thành nhiệm vụ tuần tra: +0,1★ ngày công tác.'


def commend(s: dict, by: str, t: float) -> None:
    """🏅 The officer's save: a commendation (ext hon) and +HON_ADJ to the next close's ★."""
    c, rec, x = police_of(s)
    need(x is not None, 'Người này không còn trong lực lượng.', 'cand_gone')
    need(not _out(s, rec), 'Người này đã có quyết định khai trừ.', 'cand_gone')
    e = ORG.ext_of(rec, x)
    e['hon'] = (e['hon'] + [dict(t=int(t), by=str(by)[:40])])[-ORG.HON_MAX:]
    x['adj'] = min(10, x['adj'] + HON_ADJ)


def recent_sev(e: dict | None, t: float) -> dict | None:
    """The newest grave fault within SEV_DAYS real days, else None."""
    rows = [r for r in (e or {}).get('sev') or () if t - int(r.get('t') or 0) <= SEV_DAYS * 86400]
    return max(rows, key=lambda r: r['t']) if rows else None


def expel_check(s: dict, cmd_post: str, t: float):
    """(rec, x, the fault) of an officer a commander at cmd_post may expel now; raises otherwise."""
    c, rec, x = police_of(s)
    need(x is not None, 'Người này không còn trong lực lượng.', 'cand_gone')
    need(not _out(s, rec), 'Người này đã có quyết định khai trừ rồi.', 'cand_gone')
    need(POST_ORDER.get(x['p'], 99) < POST_ORDER.get(cmd_post, -1), 'Chỉ khai trừ được cán bộ cấp dưới.', 'cand_rank')
    sev = recent_sev(rec.get('cx') if isinstance(rec.get('cx'), dict) else None, t)
    need(sev is not None, f'Chưa có sai phạm mức cao nhất trong {SEV_DAYS} ngày qua: không đủ căn cứ khai trừ.', 'cand_no_sev')
    return rec, x, sev


def expel(s: dict, cmd_post: str, t: float) -> str:
    from . import promotion as pm
    rec, x, sev = expel_check(s, cmd_post, t)
    pm.mark_expel(rec, x, s, sev['c'])
    return sev['c']


def rank_name(s: dict) -> str:
    c, rec, x = police_of(s)
    return ORG.shown_grade(x)['name'] if x else ''


# ===================================================================================== the database (thin)
def _read(store, sid: str):
    """(state, revision) of a save, or None."""
    return _mr()._read_state(store, sid)


def _mutate(store, fns: dict, ops=None):
    return _mr()._mutate_retry(store, fns, ops)


def _notify(db, event: dict) -> None:
    """A live push (live/cand.py), in the transaction: only what committed is told."""
    db.execute('SELECT pg_notify(?, ?)', ('mnl_live', json.dumps(event, ensure_ascii=False, separators=(',', ':'))))


def _lock(db, key: str) -> None:
    """One stop decision per officer / target at a time (PostgreSQL transaction lock)."""
    db.execute('SELECT pg_advisory_xact_lock(17841, hashtext(?))', (key,))


def _push(store, sid: str, text: str) -> None:
    from . import push
    try:
        store.transaction(lambda db: push.queue(db, sid, INBOX, text[:160], '/'), 250)
    except Exception:  # noqa: BLE001 - best effort (no push tables in a dev database, a busy moment)
        pass


def _pid(sid: str) -> str:
    from .social import pid_of
    return pid_of(sid)


def _inbox(db, sid: str, text: str) -> None:
    db.execute('INSERT INTO inbox(pid,kind,text,ref,at) VALUES(?,?,?,?,?)', (_pid(sid), INBOX, text[:300], None, now()))


def _sid_of(db, pid) -> str | None:
    if not isinstance(pid, str) or not PID_RE.fullmatch(pid):
        return None
    r = db.execute('SELECT sid FROM profiles WHERE pid=?', (pid,)).fetchone()
    return r['sid'] if r else None


def _account(db, sid: str) -> bool:
    return bool(db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone())


def _name(db, sid: str) -> str:
    return _mr()._display(db, sid)


def _friends(db, a: str, b: str) -> bool:
    from . import friends as fr
    return fr.are_friends(db, a, b)


COLS = 'id,officer,target,at,status,act,bribe,outcome,done_at,day,stake'


def _stop(db, stop_id) -> dict | None:
    if not isinstance(stop_id, str) or not ID_RE.fullmatch(stop_id):
        return None
    r = db.execute(f'SELECT {COLS} FROM cand_stops WHERE id=?', (stop_id,)).fetchone()
    return dict(r) if r else None


def _move(db, stop_id: str, frm: str, to: str, **kw) -> bool:
    sets = ['status=?'] + [f'{k}=?' for k in kw]
    return db.execute(f'UPDATE cand_stops SET {",".join(sets)} WHERE id=? AND status=?',
                      (to, *kw.values(), stop_id, frm)).rowcount == 1


def _open_of(db, sid: str) -> list[dict]:
    rows = db.execute(f"SELECT {COLS} FROM cand_stops WHERE status IN ('ask','offer') AND (officer=? OR target=?) "
                      'ORDER BY at LIMIT 5', (sid, sid)).fetchall()
    return [dict(r) for r in rows]


def _day_stops(db, officer: str, day: str, t: float) -> list[dict]:
    rows = db.execute('SELECT target,act,status,outcome FROM cand_stops WHERE officer=? AND at>? AND day=?',
                      (officer, t - 2 * 86400, day)).fetchall()
    return [dict(r) for r in rows]


def _recent_on(db, target: str, t: float) -> list[dict]:
    rows = db.execute('SELECT officer,act,at FROM cand_stops WHERE target=? AND at>?', (target, t - TARGET_GAP_S)).fetchall()
    return [dict(r) for r in rows]


def _rewarded(rows: list[dict]) -> int:
    return sum(1 for r in rows if r['status'] == 'done' and r['outcome'] in PENALTY_OUTCOMES)


def stop_checks(db, officer: str, target: str, act: str, t: float) -> None:
    """The limits of a new stop (inside the transaction that records it, both locked)."""
    day = vn_day(t)
    mine = _day_stops(db, officer, day, t)
    need(len(mine) < OFFICER_DAY_MAX, f'Hôm nay bạn đã kiểm tra đủ {OFFICER_DAY_MAX} lượt. Mai tuần tra tiếp nhé.', 'cand_day_max', 429)
    need(not any(r['status'] in OPEN for r in mine), 'Xử lý xong người đang kiểm tra đã nhé.', 'cand_busy')
    if act != 'search':
        need(not any(r['target'] == target and r['act'] != 'search' for r in mine),
             'Hôm nay bạn đã xử lý người này rồi.', 'cand_pair')
    # A search holds back only the same officer's next search: never another officer (a friend searching every half
    # hour would shield a gambler) and never the follow-up penalty.
    recent = [r for r in _recent_on(db, target, t) if r['act'] != 'search' or (act == 'search' and r['officer'] == officer)]
    need(not recent, 'Người này vừa bị kiểm tra, để lúc khác nhé.', 'cand_recent', 429)


# ===================================================================================== views
def _left(row: dict, t: float) -> int:
    if row['status'] == 'ask':
        return max(0, int(row['at'] + ASK_S - t))
    if row['status'] == 'offer':
        return max(0, int(row['at'] + ASK_S + OFFER_S - t))
    return 0


def outcome_text(row: dict, role: str, pen: dict | None = None) -> str:
    """A settled stop in one short line for either side: `pen` what was really taken (when settling), else the
    amounts read from the row (the fine as set: a short wallet may have paid less)."""
    act, out, n = row['act'], row['outcome'], row['bribe']
    pen = pen or dict(fine=fine_of(row['stake']) if act in ('fine', 'arrest') else 0,
                      days=HOLD_DAYS if act == 'hold' else ARREST_DAYS if act == 'arrest' else 0)
    if out == 'search':
        return 'Đã lục soát tư trang.'
    if out == 'taken':
        return f'Đã nhận phong bì {_xu(n)} xu, cho qua.' if role == 'officer' else f'Cán bộ nhận phong bì {_xu(n)} xu, cho bạn đi.'
    if out == 'caught':
        return ('Nhận phong bì bị phát hiện: phong bì bị tịch thu, hạ bậc hàm, ghi dấu liêm chính.' if role == 'officer'
                else f'Phong bì {_xu(n)} xu bị tịch thu, cán bộ bị xử lý. Bạn được cho đi.')
    if out == 'gone':
        return 'Lượt kiểm tra đã hết hiệu lực.'
    head = {'refused': 'Từ chối phong bì, lập biên bản. ', 'lapse': '', 'late': '', 'void': 'Phong bì không đủ, lập biên bản. ',
            'coop': ''}.get(out, '')
    return head + penalty_text(act, pen)


def view(row: dict, sid: str, t: float, names: dict | None = None) -> dict:
    role = 'officer' if row['officer'] == sid else 'target'
    v = dict(id=row['id'], act=row['act'], act_name=ACT_NAME[row['act']], st=row['status'], role=role, left=_left(row, t))
    if row['status'] == 'offer' or row['outcome'] in ('taken', 'caught'):
        v['amount'] = int(row['bribe'])
    if row['status'] in ('done', 'gone'):
        v['text'] = outcome_text(row, role)
    if names:
        v['name'] = names.get(row['target'] if role == 'officer' else row['officer'], '')
    return v


def _tell(db, sid: str, k: str, row: dict, text: str = '', **extra) -> None:
    """The live frame to one party (live/cand.py)."""
    _notify(db, dict(op='cand', to=_pid(sid), k=k, id=row['id'], act=row['act'], text=text[:200], **extra))


# ===================================================================================== settling a stop
def _officer_name(state: dict | None, display: str) -> str:
    rn = rank_name(state) if state else ''
    return f'{rn} {display}'.strip()


def settle(store, row: dict, outcome: str, t: float | None = None) -> dict | None:
    """Settle an open stop with the penalty (outcome in PENALTY_OUTCOMES) or without ('gone'). Returns the row as
    settled, or None when someone else settled it first."""
    mr = _mr()
    t = now() if t is None else t
    sid_o, sid_t = row['officer'], row['target']
    if outcome == 'gone':
        done = store.transaction(lambda db: _move(db, row['id'], row['status'], 'gone', outcome='gone', done_at=t))
        return dict(row, status='gone', outcome='gone', done_at=t) if done else None
    with store.connect() as db:
        rows = _day_stops(db, sid_o, row['day'], t)
        pay = _rewarded(rows) < REWARD_DAY_MAX and not _friends(db, sid_o, sid_t)
    res: dict = {}

    def tgt(s):
        res['pen'] = penalize(s, row['act'], int(row['stake']), t)

    def off(s):
        res['rw'] = reward(s, outcome == 'refused') if pay else ''

    final = dict(row, status='done', outcome=outcome, done_at=t)

    def ops(db):
        need(_move(db, row['id'], row['status'], 'done', outcome=outcome, done_at=t), 'Lượt kiểm tra này đã xong rồi.', 'cand_stale')
        pen = res.get('pen') or None
        text_t = '👮 ' + outcome_text(final, 'target', pen)
        _inbox(db, sid_t, text_t)
        _tell(db, sid_t, 'done', final, text_t)
        _tell(db, sid_o, 'done', final, outcome_text(final, 'officer', pen))
    try:
        _mutate(store, {sid_t: tgt, sid_o: off} if pay else {sid_t: tgt}, ops)
    except mr.MarriageError as e:
        if e.code == 'cand_stale':
            return None
        if e.code == 'session_missing':   # a save gone: the stop lapses
            return settle(store, row, 'gone', t)
        raise
    final['pen'], final['rw'] = res.get('pen') or {}, res.get('rw') or ''
    return final


def sweep(store, sid: str, t: float | None = None) -> None:
    """Settle this player's open stops whose time is over (either side): no answer = cooperation, an envelope the
    officer never looked at = the penalty, past STALE_S = lapsed."""
    t = now() if t is None else t
    with store.connect() as db:
        rows = _open_of(db, sid)
    for r in rows:
        if t - r['at'] > STALE_S:
            settle(store, r, 'gone', t)
        elif r['status'] == 'ask' and t > r['at'] + ASK_S:
            settle(store, r, 'late', t)
        elif r['status'] == 'offer' and t > r['at'] + ASK_S + OFFER_S:
            settle(store, r, 'lapse', t)


# ===================================================================================== handlers (POST /api/marriage/<op>)
def _me(store, sid: str):
    loaded = _read(store, sid)
    need(loaded, 'Không tìm thấy tiến trình.', 'session_missing', 404)
    return loaded[0]


def op_stop(store, sid: str, display: str, d: dict) -> dict:
    """cand_stop {pid, act}: an officer on duty stops a player at Chợ đen."""
    act = d.get('act')
    need(act in ACTS, 'Chọn việc cần làm nhé.', 'bad_act', 400)
    t = now()
    me = _me(store, sid)
    why = officer_block(me, t)
    need(why is None, why or '', 'cand_off', 403)
    sweep(store, sid, t)
    with store.connect() as db:
        target = _sid_of(db, d.get('pid'))
        need(target, 'Không tìm thấy người này.', 'not_found', 404)
        need(target != sid, 'Không tự kiểm tra mình được.', 'self')
        need(_account(db, target), 'Người này chưa có tài khoản, không trả lời được: để họ chơi tiếp nhé.', 'cand_guest')
        stop_checks(db, sid, target, act, t)   # the cheap limits first (unlocked; again under the locks below)
        name = _name(db, target)
    loaded = _read(store, target)
    need(loaded, 'Không tìm thấy người này.', 'not_found', 404)
    from . import jail
    tj = loaded[0].get('journey')
    need(not jail.active(tj, t), f'{name} đang bị tạm giữ rồi.', 'cand_jailed')
    ev = evidence(tj, t)
    need(ev is not None, 'Không thấy dấu hiệu đánh bạc ăn tiền: chưa đủ căn cứ kiểm tra.', 'cand_no_ev')
    if ACT_LEVEL[act] > ev['lvl']:
        need(ev['lvl'] > 0, 'Chơi nhỏ, chưa tới mức xử lý: chỉ lục soát, nhắc nhở thôi.', 'cand_small')
        need(False, f'Chưa đủ căn cứ để {ACT_NAME[act].split(" ", 1)[1].lower()}.', 'cand_level')
    stop_id = 'cs' + secrets.token_hex(8)
    row = dict(id=stop_id, officer=sid, target=target, at=t, status='done' if act == 'search' else 'ask', act=act, bribe=0,
               outcome='search' if act == 'search' else '', done_at=t if act == 'search' else None, day=vn_day(t),
               stake=int(ev['stake']))
    who = _officer_name(me, display)

    def rec(db):
        for k in sorted((f'o:{sid}', f't:{target}')):
            _lock(db, k)
        stop_checks(db, sid, target, act, t)
        db.execute(f'INSERT INTO cand_stops({COLS}) VALUES(?,?,?,?,?,?,?,?,?,?,?)', tuple(row[k] for k in COLS.split(',')))
        if act == 'search':
            text = f'👮 {who} vừa lục soát tư trang của bạn ở chợ đen.'
            _inbox(db, target, text)
            _tell(db, target, 'done', row, text)
        else:
            _tell(db, target, 'ask', row, f'👮 {who} yêu cầu kiểm tra: {ACT_NAME[act]}.', by=who[:40], left=ASK_S)
    store.transaction(rec)
    if act == 'search':
        return dict(message=findings(ev), quiet=True, stop=dict(id=stop_id, act=act, st='done', role='officer', left=0,
                                                                text=findings(ev), acts=allowed(ev['lvl']), name=name))
    _push(store, target, f'👮 {who} yêu cầu kiểm tra ở chợ đen. Trả lời trong {ASK_S} giây.')
    return dict(message=f'Đã yêu cầu {name} hợp tác.', quiet=True, stop=view(row, sid, t, {target: name}))


def op_answer(store, sid: str, display: str, d: dict) -> dict:
    """cand_answer {id, bribe}: the target cooperates (0) or offers an envelope (1..BRIBE_MAX)."""
    t = now()
    amount = d.get('bribe', 0)
    need(type(amount) is int and 0 <= amount <= BRIBE_MAX, f'Phong bì từ 1 đến {_xu(BRIBE_MAX)} xu thôi.', 'bad_bribe', 400)
    sweep(store, sid, t)
    with store.connect() as db:
        row = _stop(db, d.get('id'))
        need(row and row['target'] == sid, 'Không có lượt kiểm tra này.', 'not_found', 404)
        name = _name(db, row['officer'])
        # no envelope between friends: it would be a transfer outside the bank's limits
        need(amount == 0 or row['status'] != 'ask' or not _friends(db, row['officer'], sid),
             'Cán bộ là bạn bè của bạn: không đưa phong bì được, hãy hợp tác nhé.', 'cand_friend')
    if row['status'] != 'ask':
        return dict(message=outcome_text(row, 'target') if row['status'] in ('done', 'gone') else 'Đã trả lời rồi.', quiet=True,
                    stop=view(row, sid, t, {row['officer']: name}))
    if amount == 0:
        done = settle(store, row, 'coop', t)
        if not done:
            with store.connect() as db:
                done = _stop(db, row['id'])
        return dict(message=outcome_text(done, 'target', done.get('pen')), changed=True, quiet=True, stop=view(done, sid, t, {row['officer']: name}))
    me = _me(store, sid)
    need(me['journey']['wallet'] >= amount, f'Ví chỉ còn {_xu(max(0, me["journey"]["wallet"]))} xu.', 'cand_short')

    def ops(db):
        need(_move(db, row['id'], 'ask', 'offer', bribe=amount), 'Lượt kiểm tra này đã xong rồi.', 'cand_stale')
        _tell(db, row['officer'], 'offer', dict(row, status='offer', bribe=amount), f'💵 {display} đưa phong bì {_xu(amount)} xu.',
              amount=amount, left=OFFER_S)
    store.transaction(ops)
    row.update(status='offer', bribe=amount)
    return dict(message=f'Đã đưa phong bì {_xu(amount)} xu. Chờ cán bộ…', quiet=True, stop=view(row, sid, t, {row['officer']: name}))


def op_decide(store, sid: str, display: str, d: dict) -> dict:
    """cand_decide {id, take}: the officer takes the envelope or refuses it (biên bản: the penalty applies)."""
    t = now()
    take = d.get('take')
    need(type(take) is bool, 'Chọn nhận hay từ chối nhé.', 'bad_take', 400)
    with store.connect() as db:
        row = _stop(db, d.get('id'))
        need(row and row['officer'] == sid, 'Không có lượt kiểm tra này.', 'not_found', 404)
        name = _name(db, row['target'])
    names = {row['target']: name}
    if row['status'] == 'offer' and t > row['at'] + ASK_S + OFFER_S:
        sweep(store, sid, t)
        with store.connect() as db:
            row = _stop(db, row['id'])
    need(row['status'] == 'offer', 'Lượt kiểm tra này đã xong rồi.', 'cand_stale')
    if not take:
        done = settle(store, row, 'refused', t)
        need(done, 'Lượt kiểm tra này đã xong rồi.', 'cand_stale')
        return dict(message=outcome_text(done, 'officer', done.get('pen')) + (f' {done["rw"]}' if done.get('rw') else ''), changed=True, quiet=True,
                    stop=view(done, sid, t, names))
    amount = int(row['bribe'])
    res: dict = {}

    def tgt(s):
        give_bribe(s, amount)

    def off(s):
        res.update(take_bribe(s, amount, t, row['id']))

    def ops(db):
        out = 'caught' if res.get('caught') else 'taken'
        need(_move(db, row['id'], 'offer', 'done', outcome=out, done_at=t), 'Lượt kiểm tra này đã xong rồi.', 'cand_stale')
        fin = dict(row, status='done', outcome=out, done_at=t)
        res['row'] = fin
        _tell(db, row['target'], 'done', fin, '👮 ' + outcome_text(fin, 'target'))
        if out == 'caught':
            _inbox(db, sid, '🚨 ' + outcome_text(fin, 'officer'))
    try:
        _mutate(store, {row['target']: tgt, sid: off}, ops)
    except _mr().MarriageError as e:
        if e.code != 'cand_short':
            raise
        done = settle(store, row, 'void', t)   # the envelope is not there any more: the biên bản
        need(done, 'Lượt kiểm tra này đã xong rồi.', 'cand_stale')
        return dict(message=outcome_text(done, 'officer', done.get('pen')), changed=True, quiet=True, stop=view(done, sid, t, names))
    fin = res['row']
    msg = res.get('line') or outcome_text(fin, 'officer')
    return dict(message=msg, changed=True, quiet=True, stop=view(fin, sid, t, names))


def op_poll(store, sid: str, display: str, d: dict) -> dict:
    """cand_poll {id?}: a stop of mine as it stands (its time over: settled first); without id the stop waiting for
    my answer, if any (the page's fallback when the live service has no 'cand')."""
    t = now()
    sweep(store, sid, t)
    with store.connect() as db:
        if d.get('id') is not None:
            row = _stop(db, d.get('id'))
            need(row and sid in (row['officer'], row['target']), 'Không có lượt kiểm tra này.', 'not_found', 404)
        else:
            row = next((r for r in _open_of(db, sid) if r['target'] == sid and r['status'] == 'ask'), None)
        if not row:
            return dict(message='', quiet=True, stop=None)
        other = row['target'] if row['officer'] == sid else row['officer']
        names = {other: _name(db, other)}
    return dict(message='', quiet=True, stop=view(row, sid, t, names))


def op_force(store, sid: str, display: str, d: dict) -> dict:
    """cand_force {}: 👥 Toàn lực lượng for a commander."""
    from . import cand_roster as CR
    from .social import pid_of
    t = now()
    me = _me(store, sid)
    why = commander_block(me, t)
    need(why is None, why or '', 'cand_off', 403)
    mine = police_of(me)[2]['p']
    day = vn_day(t)
    with store.connect() as db:
        rows = CR.roster(db, ROSTER_MAX)
        honed = {r['target'] for r in db.execute("SELECT target FROM cand_acts WHERE kind='hon' AND day=?", (day,)).fetchall()}
        gave = db.execute("SELECT COUNT(*) AS n FROM cand_acts WHERE by_sid=? AND kind='hon' AND day=?", (sid, day)).fetchone()['n']
        outs = db.execute("SELECT COUNT(*) AS n FROM cand_acts WHERE by_sid=? AND kind='out' AND day=?", (sid, day)).fetchone()['n']
    o = OC.ORGS[ORG_ID]
    out = []
    for r in rows:
        self_ = r['sid'] == sid
        sev = float(r.get('sev') or 0) >= t - SEV_DAYS * 86400
        below = POST_ORDER.get(r['post'], 99) < POST_ORDER.get(mine, -1)
        post = ORG._post(o, r['post'])['short'] if r['post'] in POST_ORDER else r['post']
        grade = next((g['name'] for g in o['grades'] if g['id'] == r['grade']), r['grade'])
        out.append(dict(pid=pid_of(r['sid']), name=r['name'] or 'Cán bộ', post=post, grade=grade, me=self_, sev=bool(sev),
                        hon=r['sid'] in honed, can_hon=not self_ and not gave and r['sid'] not in honed,
                        can_out=not self_ and sev and below and outs < OUT_DAY_MAX))
    return dict(message='', quiet=True, force=out, hon_left=0 if gave else 1, out_left=max(0, OUT_DAY_MAX - int(outs)))


def _commander(store, sid: str, d: dict, t: float):
    me = _me(store, sid)
    why = commander_block(me, t)
    need(why is None, why or '', 'cand_off', 403)
    with store.connect() as db:
        target = _sid_of(db, d.get('pid'))
        need(target, 'Không tìm thấy cán bộ này.', 'not_found', 404)
        need(target != sid, 'Không tự xét cho mình được.', 'self')
        name = _name(db, target)
    return me, target, name


def op_hon(store, sid: str, display: str, d: dict) -> dict:
    """cand_hon {pid}: 🏅 Khen thưởng thi đua."""
    t = now()
    me, target, name = _commander(store, sid, d, t)
    day = vn_day(t)
    by = _officer_name(me, display)

    def fn(s):
        commend(s, by, t)

    def ops(db):
        a = db.execute('INSERT INTO cand_acts(id,by_sid,target,kind,day,at,note) VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
                       (f'hon:{sid}:{day}', sid, target, 'hon', day, t, '')).rowcount
        need(a == 1, 'Hôm nay bạn đã khen thưởng một cán bộ rồi. Mai xét tiếp nhé.', 'cand_hon_day', 429)
        b = db.execute('INSERT INTO cand_acts(id,by_sid,target,kind,day,at,note) VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
                       (f'hont:{target}:{day}', sid, target, 'hon_t', day, t, '')).rowcount
        need(b == 1, f'Hôm nay {name} đã được khen thưởng rồi.', 'cand_hon_target', 429)
        _inbox(db, target, f'🏅 {by} khen thưởng thi đua cho bạn: +0,3★ ngày công tác tới.')
    _mutate(store, {target: fn}, ops)
    _push(store, target, f'🏅 {by} khen thưởng thi đua cho bạn.')
    return dict(message=f'🏅 Đã khen thưởng {name}.', quiet=True)


def op_out(store, sid: str, display: str, d: dict) -> dict:
    """cand_out {pid, confirm: true}: 🚫 Khai trừ an officer below with a grave fault in the last SEV_DAYS days."""
    t = now()
    need(d.get('confirm') is True, 'Xác nhận khai trừ nhé.', 'confirm', 400)
    me, target, name = _commander(store, sid, d, t)
    post = police_of(me)[2]['p']
    day = vn_day(t)
    by = _officer_name(me, display)
    got: dict = {}

    def fn(s):
        got['code'] = expel(s, post, t)

    def ops(db):
        n = db.execute("SELECT COUNT(*) AS n FROM cand_acts WHERE by_sid=? AND kind='out' AND day=?", (sid, day)).fetchone()['n']
        need(int(n) < OUT_DAY_MAX, f'Hôm nay bạn đã ký {OUT_DAY_MAX} quyết định khai trừ.', 'cand_out_day', 429)
        a = db.execute('INSERT INTO cand_acts(id,by_sid,target,kind,day,at,note) VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
                       (f'out:{target}:{day}', sid, target, 'out', day, t, got.get('code', '')[:40])).rowcount
        need(a == 1, f'{name} đã có quyết định khai trừ hôm nay.', 'cand_gone')
        _inbox(db, target, f'🚨 {by} ký quyết định khai trừ bạn khỏi lực lượng. Hết ca này bàn giao công việc.')
    _mutate(store, {target: fn}, ops)
    _push(store, target, f'🚨 {by} ký quyết định khai trừ bạn khỏi lực lượng.')
    return dict(message=f'🚫 Đã ký quyết định khai trừ {name}. Hết ca của người này, quyết định có hiệu lực.', quiet=True)


ACTIONS = dict(cand_stop=op_stop, cand_answer=op_answer, cand_decide=op_decide, cand_poll=op_poll,
               cand_force=op_force, cand_hon=op_hon, cand_out=op_out)
