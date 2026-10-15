"""⚖️ Điều lệnh cán bộ (owner spec "Nội dung update game 14/10/2026", II. Bổ sung cập nhật nghề Công an): what an officer
of the state must never do, and the kỷ luật it brings on the org ladder (game/org.py discipline: giáng N bậc hàm at once
+ kỷ luật D ngày = the grade held D worked days, no grade step and no appointment while it runs; each one counted in the
hồ sơ công tác, org.svc_count). The rules are shown before they can be broken (the police career's 📜 Điều lệnh card,
RULES) and each act asks first:

* 🚔 Chuộc người thân (jail.bail): an officer on the CAND ladder bailing out a friend, a registered spouse or a fiancé(e)
  serving a sentence (bail is between friends only, so every bail by an officer is one). The bail answers with the rule
  first (cop_rule, nothing done); sent again with officer_ok it goes ahead and the officer is disciplined at once, for
  certain (the bail is a signed, paid act): giáng 2 bậc hàm, kỷ luật 15 ngày (BAIL).
* 🎲 Cá độ, đỏ đen ở chợ đen (fair.apply): a staked round (GAMBLE_COMMANDS: bầu cua, chiếu trong, a lô tô tờ, a vé cào,
  đua chó, phóng dao) by an officer. The first one is refused with the rule (GameError 'cop_gamble'); the page asks and
  sends the round again with cop_ok. Each staked round then may be found out ("nếu bị phát hiện"): GAMBLE_P of the time
  (its own salted draw, never shown), for certain when the Chợ đen raid catches the round. Found out: giáng 1 bậc hàm,
  kỷ luật 10 ngày (GAMBLE), at most once a working day (org.discipline's key). The round itself plays as usual.

Only an officer on duty's ladder counts (promotion.org_live: hired at a posting that wears the org, not on the way out);
a part-time helper at the ward desk is not an officer. Nothing here is in the save but the effects (the org record, the
journey's hồ sơ công tác count).
"""
from __future__ import annotations

import random
import secrets

CAREER = 'police'
BAIL = dict(grades=2, days=15)
GAMBLE = dict(grades=1, days=10)
GAMBLE_P = 0.2
GAMBLE_COMMANDS = ('fair_bc', 'fair_xd', 'fair_loto_buy', 'fair_xs', 'fair_dg', 'fair_kn_start')
OK_KEY = 'cop_ok'
GD_VIOL_MAX = 6

RULES = {
    'police': [
        dict(id='gd', icon='🎖️', text=f'Bổ nhiệm Giám đốc Công an Thành phố: hồ sơ công tác không quá {GD_VIOL_MAX} lần vi phạm trong cả quá trình công tác.'),
        dict(id='bail_kin', icon='🚔', text=(f'TUYỆT ĐỐI không chuộc (bảo lãnh) người thân đang chấp hành án: bạn bè, vợ/chồng đã đăng ký kết hôn, '
                                            f'người đã đính hôn. Vi phạm: giáng {BAIL["grades"]} bậc hàm, kỷ luật {BAIL["days"]} ngày.')),
        dict(id='gamble', icon='🎲', text=(f'TUYỆT ĐỐI không tham gia cá độ, đỏ đen có dùng xu ở chợ đen. Bị phát hiện: giáng {GAMBLE["grades"]} '
                                          f'bậc hàm, kỷ luật {GAMBLE["days"]} ngày.')),
        dict(id='svc', icon='📁', text='Mỗi lần vi phạm (cảnh cáo, phong bì, kỷ luật) đều ghi vào hồ sơ công tác, theo bạn qua mọi đơn vị nhà nước.'),
    ],
}
BAIL_ASK = (f'⚖️ Điều lệnh: cán bộ Công an TUYỆT ĐỐI không chuộc người thân (bạn bè, vợ/chồng, người đính hôn) đang chấp hành án. '
            f'Vẫn bảo lãnh thì bị giáng {BAIL["grades"]} bậc hàm, kỷ luật {BAIL["days"]} ngày.')
GAMBLE_ASK = (f'⚖️ Điều lệnh: cán bộ Công an TUYỆT ĐỐI không cá độ, đỏ đen bằng xu ở chợ đen. Bị phát hiện thì giáng {GAMBLE["grades"]} '
              f'bậc hàm, kỷ luật {GAMBLE["days"]} ngày.')


def _pm():
    from . import promotion
    return promotion


def officer(s) -> dict | None:
    """The police career of a save on the CAND ladder now, on duty's terms (not expelled, not banned); else None."""
    c = (s.get('careers') or {}).get(CAREER) if isinstance(s, dict) else None
    if not isinstance(c, dict):
        return None
    pm = _pm()
    try:
        rec, x = pm.org_live(s, c, CAREER)
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    if x is None or pm.banned(s, CAREER) or pm.expel_due(rec):
        return None
    return c


# ---------------------------------------------------------------- 🚔 chuộc người thân (game/jail.py bail)
def bail_ask(s) -> str | None:
    """The rule to show before an officer bails someone out (None: not an officer)."""
    return BAIL_ASK if officer(s) is not None else None


def bail_discipline(s) -> str:
    """The officer's save, as the bail is paid: giáng 2 bậc hàm, kỷ luật 15 ngày ('' when not an officer)."""
    c = officer(s)
    if c is None:
        return ''
    return _pm().discipline(s, c, CAREER, BAIL['grades'], BAIL['days'], 'bail_kin', f'bail-{c["day"]}-{_day(s)}')


def _day(s) -> int:
    return int((s.get('journey') or {}).get('life_day') or 1)


# ---------------------------------------------------------------- 🎲 cá độ, đỏ đen ở chợ đen (game/fair.py apply)
def gamble_gate(s: dict, name: str, p) -> tuple:
    """Before a Chợ đen command: (the payload without cop_ok, whether it is an officer's staked round). An officer's
    staked round without cop_ok is refused with the rule (the page asks, then sends it again with cop_ok)."""
    from .engine import GameError
    ok = isinstance(p, dict) and p.get(OK_KEY) is True
    if isinstance(p, dict) and OK_KEY in p:
        p = {k: v for k, v in p.items() if k != OK_KEY}
    if name not in GAMBLE_COMMANDS or officer(s) is None:
        return p, False
    if not ok:
        raise GameError(GAMBLE_ASK, 'cop_gamble')
    return p, True


_SALT = secrets.token_hex(8)   # per process: the draw cannot be worked out


def _roll(key: str, p: float) -> bool:
    """The detection draw (tests patch it). Never shown."""
    return random.Random(f'cop-gamble|{key}|{_SALT}|{secrets.token_hex(4)}').random() < p


def gamble_after(s: dict, result: dict, t: float) -> None:
    """After an officer's staked round: found out (GAMBLE_P, or the raid caught it) → giáng 1 bậc hàm, kỷ luật 10 ngày,
    once a working day; the line joins the round's message."""
    c = officer(s)
    if c is None:
        return
    raided = bool(((result or {}).get('fair') or {}).get('arrest'))
    if not raided and not _roll(f'{_day(s)}|{t}', GAMBLE_P):
        return
    line = _pm().discipline(s, c, CAREER, GAMBLE['grades'], GAMBLE['days'], 'gamble', f'gamble-{c["day"]}')
    if line:
        result['message'] = f'{result.get("message", "")} 🚨 Bị phát hiện cán bộ đánh bạc ở chợ đen. {line}'.strip()
        result['cop_discipline'] = line


def content() -> dict:
    return {k: [dict(r) for r in v] for k, v in RULES.items()}
