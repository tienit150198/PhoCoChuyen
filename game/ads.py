"""📺 Quảng cáo có thưởng (owner 18/10: "reward ads thôi", "1 ngày 1 người được giới hạn 7 lần xem quảng cáo thôi",
"khai thác tối đa ads"; later: "mấy game khó ấy, ghép 3 thì có thêm này", "cho người ta xem thoải mái giới hạn làm gì,
clone cũng được, nhưng mỗi acc chỉ cho 7 lần/1 ngày là được", "giờ vàng thì kiểu 1 tiếng x1.5").

The ad itself is Google's (AdSense H5 games, the Ad Placement API's `adBreak({type: 'reward'})`, loaded by
public/js/v4/ads.js). The web has no server-side verification of a watched ad, so the server keeps what it can:

* ``ad_ticket {place, kind?}`` (a tap on a 📺 button): a ticket {id, p: place, at: server ms} in the save, refused once the
  Vietnam day's DAY_MAX views are used or the place has nothing to give.
* ``ad_claim {ticket}`` (the ad's adViewed): the ticket of this save, at least MIN_WATCH_S after it was issued and at
  most TICKET_TTL_S, pays the place's reward, counts one view, and the 3rd / 7th view of the day also opens a 🎁 chest.
  Amounts and times are the server's; nothing the page sends is a number of xu.

Places (PLACES):
* 'gold'  ⏰ Giờ vàng riêng: the save's shops and counters take ×1,5 (GOLD_MULT) for GOLD_S (one hour) more, on top of
  the street's Giờ vàng (game/golden_hour.py); staff orders (game/workplace_business.py _finish) and counter sales
  (game/quay_business.py sale) read gold_mult() at the sale's own time, like the street's.
* 'tile'  🧩 Ghép ba (game/tile_match.py): the tray is full → the page takes the last tile back and the save gets
  TILE_PACK more free boosters, kept until used (spent after the day's own free uses, before xu).
* 'jail'  🚔 Trại tạm giữ (game/jail.py): the jail day may end JAIL_S (5 minutes) sooner (its `since` moves back).
* 'shift' 💼 Thưởng khép ca: the last closed shift's base net × SHIFT_PCT % (at most SHIFT_CAP) into the wallet, once;
  journey._end_of_day writes the offer (offer_shift), the next closed shift replaces it.

Save: journey['ads'] (optional; older servers keep it untouched and ignore it)
  {v, d: VN date, n: views that day, tk?: ticket, g?: gold until (epoch s), tb?: {booster: n}, sh?: {c, x, day}}.
The count follows the save, so one account has DAY_MAX a day (reset_all carries it: journey.carry_reset). Clones are
allowed (owner). Off unless ADS_CLIENT (ca-pub-…) or ADS_FAKE=1 (a local stand-in ad, never in production) is set.
"""
from __future__ import annotations

import datetime
import hashlib
import html
import json
import os
import re
import secrets
import time

VN = datetime.timezone(datetime.timedelta(hours=7))
KEY = 'ads'
VERSION = 1
COMMANDS = ('ad_ticket', 'ad_claim')
DAY_MAX = 7                      # owner: 7 views a day, per account
MIN_WATCH_S = 8                  # a ticket is claimed at least this long after it was issued
TICKET_TTL_S = 15 * 60           # …and at most this long
PLACES = ('gold', 'tile', 'jail', 'shift')
GOLD_S = 3600                    # owner: "1 tiếng x1.5"
GOLD_MULT = 150                  # hundredths
GOLD_AHEAD = DAY_MAX * GOLD_S    # gold never runs further ahead than a day's views
TILE_PACK = {'undo': 1, 'shuffle': 1, 'push': 1}
TILE_KEEP = 30                   # boosters of one kind kept at most
JAIL_S = 300
SHIFT_PCT, SHIFT_CAP = 50, 3000  # as 🔥 x3_week.CAP: one shift's bonus at most
CHESTS = {3: (3000, 8000), 7: (10000, 30000)}   # 🎁 the day's 3rd and 7th views: xu, drawn from the save's seed
CLIENT = re.compile(r'ca-pub-[0-9]{10,20}')
NAMES = {'gold': '⏰ Giờ vàng riêng', 'tile': '🧩 Hồi sinh Ghép ba', 'jail': '🚔 Bớt giờ trong trại', 'shift': '💼 Thưởng khép ca'}


def _now() -> float:
    return time.time()


def today(t: float | None = None) -> str:
    return datetime.datetime.fromtimestamp(_now() if t is None else t, VN).date().isoformat()


def _flag(name: str) -> bool:
    return os.environ.get(name, '').strip().lower() in ('1', 'true', 'yes', 'on')


def client() -> str:
    """The AdSense publisher id, '' when unset or malformed."""
    v = os.environ.get('ADS_CLIENT', '').strip()
    return v if CLIENT.fullmatch(v) else ''


def fake() -> bool:
    """A stand-in ad for local play and browser tests: a countdown, no Google script."""
    return _flag('ADS_FAKE') and not client()


def enabled() -> bool:
    return not _flag('MNL_ADS_OFF') and bool(client() or fake())


# ---------------------------------------------------------------- the page: meta, CSP, ads.txt
def public_config() -> dict:
    if not enabled():
        return {}
    return dict(client=client(), test=_flag('ADS_TEST'), fake=fake(), max=DAY_MAX, min=MIN_WATCH_S)


def head_tags() -> list[str]:
    config = public_config()
    if not config:
        return []
    return [f'<meta name="mnl-bonus" content="{html.escape(json.dumps(config, separators=(",", ":")), quote=True)}">']


# Google's ad hosts (AdSense / H5 games): the loader, its frames, its beacons and the creatives' images.
CSP_SCRIPT = ('https://pagead2.googlesyndication.com https://*.googlesyndication.com https://*.doubleclick.net '
              'https://*.googleadservices.com https://*.google.com https://*.gstatic.com https://*.adtrafficquality.google')
CSP_FRAME = ('https://*.googlesyndication.com https://*.doubleclick.net https://*.google.com '
             'https://*.adtrafficquality.google')
CSP_CONNECT = ('https://*.googlesyndication.com https://*.doubleclick.net https://*.google.com '
               'https://*.adtrafficquality.google https://*.googleadservices.com')
CSP_IMG = 'https:'


def content_security_policy(base: str) -> str:
    """The page's CSP with Google's ad hosts, only while real ads are on (the stand-in needs nothing)."""
    if not enabled() or not client():
        return base
    base = base.replace("script-src 'self'", f"script-src 'self' {CSP_SCRIPT}", 1)
    base = base.replace('frame-src ', f'frame-src {CSP_FRAME} ', 1)
    base = base.replace("connect-src 'self'", f"connect-src 'self' {CSP_CONNECT}", 1)
    return base.replace("img-src 'self'", f"img-src 'self' {CSP_IMG}", 1)


def ads_txt() -> str | None:
    """/ads.txt (AdSense asks for it): the publisher line, None while unset."""
    c = client()
    return f'google.com, {c.replace("ca-pub-", "pub-")}, DIRECT, f08c47fec0942fa0\n' if c else None


# ---------------------------------------------------------------- the save
def _core():
    from . import engine
    return engine


def get(s: dict) -> dict | None:
    a = (s.get('journey') or {}).get(KEY)
    return a if isinstance(a, dict) else None


def _ensure(s: dict, t: float) -> dict:
    j = s['journey']
    a = j.get(KEY)
    if not isinstance(a, dict):
        a = j[KEY] = dict(v=VERSION, d=today(t), n=0)
    if a['d'] != today(t):
        a['d'], a['n'] = today(t), 0
        a.pop('tk', None)
    return a


def views_today(s: dict, t: float | None = None) -> int:
    a = get(s)
    t = _now() if t is None else t
    return int(a['n']) if a and a.get('d') == today(t) else 0


def gold_until(s) -> int:
    a = get(s) if isinstance(s, dict) else None
    g = a.get('g') if a else None
    return g if type(g) is int else 0


def gold_mult(s, t: float) -> int:
    """⏰ Giờ vàng riêng at time t (epoch s), in hundredths: GOLD_MULT inside the save's window, else 100."""
    if _flag('MNL_ADS_OFF'):
        return 100
    return GOLD_MULT if t < gold_until(s) else 100


def scale_take(s, percent: int, t: float) -> int:
    """A counter's profit-bonus percent such that the owner's take (margin × (100 + percent)) is × gold_mult."""
    g = gold_mult(s, t)
    return percent if g == 100 else (100 + percent) * g // 100 - 100


def tile_credits(s: dict) -> dict:
    a = get(s)
    tb = a.get('tb') if a else None
    return {k: int(v) for k, v in tb.items()} if isinstance(tb, dict) else {}


def spend_tile(s: dict, kind: str, n: int) -> None:
    """🧩 n boosters of `kind` used beyond the day's free ones (game/tile_match.py _end)."""
    if n <= 0:
        return
    a = get(s)
    tb = a['tb']
    left = tb[kind] - n
    _core().need(left >= 0, 'Trợ giúp không đủ.', 'tile_paid')
    if left:
        tb[kind] = left
    else:
        del tb[kind]
    if not tb:
        del a['tb']


def offer_shift(s: dict, career: str, net: int, day: int) -> int:
    """journey._end_of_day: the closed shift's bonus offer (replaces an older one); 0 and nothing kept when net ≤ 0."""
    if not enabled():
        return 0
    x = min(SHIFT_CAP, max(0, int(net)) * SHIFT_PCT // 100)
    a = get(s)
    if x <= 0:
        if a:
            a.pop('sh', None)
        return 0
    a = _ensure(s, _now())
    a['sh'] = dict(c=career, x=x, day=day)
    return x


def _chest(s: dict, a: dict) -> int:
    lo, hi = CHESTS[a['n']]
    seed = s['journey'].get('seed', 0)
    h = int(hashlib.sha256(f'ads-chest|{seed}|{a["d"]}|{a["n"]}'.encode()).hexdigest()[:8], 16)
    return lo + h % (hi - lo + 1) // 100 * 100


def _hhmm(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).strftime('%H:%M')


def _can(s: dict, place: str, t: float) -> None:
    """What the place gives, or why it gives nothing now."""
    e = _core()
    need = e.need
    from . import jail
    inside = jail.jailed(s, t)
    need(place == 'jail' or not inside, 'Trong trại chỉ xem quảng cáo để bớt giờ thôi nhé.', 'jailed')
    if place == 'jail':
        need(inside, 'Bạn đang không ở trong trại.', 'ads_place')
        b = s['journey'][jail.KEY]
        d = jail.day_of(s['journey'])
        need(b['since'] + jail._rules(d)[1] - int(t) > 0, 'Ngày trong trại đã có thể kết thúc rồi.', 'ads_place')
    elif place == 'shift':
        sh = (get(s) or {}).get('sh')
        need(isinstance(sh, dict), 'Chưa có ca nào vừa khép để nhận thưởng.', 'ads_place')
    elif place == 'gold':
        need(gold_until(s) < t + GOLD_AHEAD - GOLD_S + 1, 'Giờ vàng riêng đã đủ dài rồi, dùng bớt rồi xem tiếp nhé.', 'ads_place')
    elif place == 'tile':
        tb = tile_credits(s)
        need(all(tb.get(k, 0) < TILE_KEEP for k in TILE_PACK), 'Bạn còn nhiều trợ giúp Ghép ba lắm rồi.', 'ads_place')


def _give(s: dict, a: dict, place: str, t: float, result: dict) -> None:
    from . import journey as jr
    j = s['journey']
    if place == 'gold':
        a['g'] = until = int(max(gold_until(s), t) + GOLD_S)
        result['message'] = f'⏰ Giờ vàng riêng: lãi tiệm và quầy ×1,5 tới {_hhmm(until)}.'
    elif place == 'tile':
        tb = a.setdefault('tb', {})
        for k, n in TILE_PACK.items():
            tb[k] = min(TILE_KEEP, tb.get(k, 0) + n)
        result['message'] = '🧩 Hồi sinh! +1 Hoàn tác, +1 Xáo, +1 Đẩy ô.'
    elif place == 'jail':
        from . import jail
        b = j[jail.KEY]
        b['since'] = max(0, int(b['since']) - JAIL_S)
        result['message'] = f'🚔 Ngày trong trại ngắn lại {JAIL_S // 60} phút.'
    elif place == 'shift':
        sh = a.pop('sh')
        jr._wallet(j, sh['x'], 'salary', f'📺 Thưởng khép ca · {jr._place(sh["c"])}'[:120], sh['c'])
        result['message'] = f'💼 Thưởng khép ca: +{sh["x"]:,} xu vào ví.'.replace(',', '.')


def action(s: dict, name: str, p: dict) -> tuple[dict, dict]:
    e = _core()
    need = e.need
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict), 'Thao tác không hợp lệ.')
    need(enabled(), 'Quảng cáo đang tắt.', 'ads_off')
    j = s['journey']
    need(j.get('story'), 'Quảng cáo có thưởng mở khi bạn đã vào hành trình.', 'ads_story')
    t = _now()
    ms = int(t * 1000)
    result = dict(message='', effects=[])
    if name == 'ad_ticket':
        need(set(p) == {'place'} and p['place'] in PLACES, 'Quảng cáo không hợp lệ.', 'ads_place')
        place = p['place']
        a = _ensure(s, t)
        need(a['n'] < DAY_MAX, f'Hôm nay bạn đã xem đủ {DAY_MAX} quảng cáo rồi. Mai xem tiếp nhé!', 'ads_day')
        _can(s, place, t)
        a['tk'] = dict(id=secrets.token_hex(8), p=place, at=ms)
        result['ad'] = dict(ticket=a['tk']['id'], place=place)
    else:
        need(set(p) == {'ticket'} and isinstance(p['ticket'], str), 'Quảng cáo không hợp lệ.', 'ads_ticket')
        a = _ensure(s, t)
        tk = a.get('tk')
        need(isinstance(tk, dict) and secrets.compare_digest(tk['id'], p['ticket']),
             'Lượt quảng cáo này đã hết hạn, xem lại nhé.', 'ads_ticket')
        need(ms - tk['at'] >= MIN_WATCH_S * 1000, 'Xem hết quảng cáo mới nhận được thưởng nhé.', 'ads_fast')
        need(ms - tk['at'] <= TICKET_TTL_S * 1000, 'Lượt quảng cáo này đã hết hạn, xem lại nhé.', 'ads_ticket')
        need(a['n'] < DAY_MAX, f'Hôm nay bạn đã xem đủ {DAY_MAX} quảng cáo rồi. Mai xem tiếp nhé!', 'ads_day')
        place = tk['p']
        _can(s, place, t)
        del a['tk']
        a['n'] += 1
        _give(s, a, place, t, result)
        if a['n'] in CHESTS:
            from . import journey as jr
            x = _chest(s, a)
            jr._wallet(j, x, 'life', f'🎁 Rương nhà tài trợ · lượt {a["n"]}')
            result['effects'].append(f'🎁 Xem đủ {a["n"]} lượt hôm nay: rương nhà tài trợ +{x:,} xu!'.replace(',', '.'))
            result['chest'] = x
        result['ad'] = dict(place=place, n=a['n'], left=DAY_MAX - a['n'])
    e.validate_state(s)
    return s, result


def carry_reset(old: dict, fresh: dict) -> None:
    """reset_all: the day's views stay counted (and what was earned with them)."""
    a = (old.get('journey') or {}).get(KEY)
    if isinstance(a, dict):
        keep = {k: (dict(v) if isinstance(v, dict) else v) for k, v in a.items() if k not in ('tk', 'sh')}
        fresh['journey'][KEY] = keep


def public(s: dict) -> dict | None:
    """state.ads (None while ads are off): the day's views left, the gold window, the shift offer, the next chest."""
    if not enabled() or not (s.get('journey') or {}).get('story'):
        return None
    t = _now()
    a = get(s) or {}
    n = views_today(s, t)
    sh = a.get('sh') if isinstance(a.get('sh'), dict) else None
    nxt = next((k for k in sorted(CHESTS) if k > n), None)
    return dict(n=n, max=DAY_MAX, left=DAY_MAX - n, gold=gold_until(s) if gold_until(s) > t else 0,
                mult=GOLD_MULT, gold_s=GOLD_S, jail_s=JAIL_S, shift=sh['x'] if sh else 0,
                chest=dict(at=nxt, lo=CHESTS[nxt][0], hi=CHESTS[nxt][1]) if nxt else None, now=int(t))


def validate(s: dict) -> None:
    a = (s.get('journey') or {}).get(KEY)
    if a is None:
        return
    e = _core()
    need, integer = e.need, e.integer
    msg = 'Quảng cáo trong bản lưu không hợp lệ.'
    need(isinstance(a, dict) and {'v', 'd', 'n'} <= set(a) <= {'v', 'd', 'n', 'tk', 'g', 'tb', 'sh'}, msg)
    need(a['v'] == VERSION and isinstance(a['d'], str) and len(a['d']) == 10, msg)
    integer(a['n'], 0, DAY_MAX)
    if 'tk' in a:
        tk = a['tk']
        need(isinstance(tk, dict) and set(tk) == {'id', 'p', 'at'} and tk['p'] in PLACES, msg)
        need(isinstance(tk['id'], str) and re.fullmatch(r'[0-9a-f]{16}', tk['id']) is not None, msg)
        integer(tk['at'], 0, 10**14)
    if 'g' in a:
        integer(a['g'], 0, 10**11)
    if 'tb' in a:
        need(isinstance(a['tb'], dict) and a['tb'] and set(a['tb']) <= set(TILE_PACK), msg)
        for v in a['tb'].values():
            integer(v, 1, TILE_KEEP)
    if 'sh' in a:
        sh = a['sh']
        need(isinstance(sh, dict) and set(sh) == {'c', 'x', 'day'} and isinstance(sh['c'], str) and len(sh['c']) <= 40, msg)
        integer(sh['x'], 1, SHIFT_CAP)
        integer(sh['day'], 0, 10**7)
