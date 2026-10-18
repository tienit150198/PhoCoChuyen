"""📺 Quảng cáo có thưởng (owner 18/10: "reward ads thôi", "1 ngày 1 người được giới hạn 7 lần xem quảng cáo thôi",
"khai thác tối đa ads"; later: "mấy game khó ấy, ghép 3 thì có thêm này", "cho người ta xem thoải mái giới hạn làm gì,
clone cũng được, nhưng mỗi acc chỉ cho 7 lần/1 ngày là được", "giờ vàng thì kiểu 1 tiếng x1.5").

The ad itself is Google's (AdSense H5 games, the Ad Placement API's `adBreak({type: 'reward'})`, loaded by
public/js/v4/bonus-video.js). The web has no server-side verification of a watched ad, so the server keeps what it can:

* ``ad_ticket {place, what?, career?}`` (a tap on a 📺 button): a ticket {id, p: place, at: server ms} in the save, refused once the
  Vietnam day's DAY_MAX views are used or the place has nothing to give.
* ``ad_claim {ticket}`` (the ad's adViewed): the ticket of this save, at least MIN_WATCH_S after it was issued and at
  most TICKET_TTL_S, pays the place's reward and counts one view.
  Amounts and times are the server's; nothing the page sends is a number of xu.

Places (PLACES):
* 'gold'  ⏰ Giờ vàng riêng: the save's shops and counters take ×1,5 (GOLD_MULT) for GOLD_S (one hour) more, on top of
  the street's Giờ vàng (game/golden_hour.py); staff orders (game/workplace_business.py _finish) and counter sales
  (game/quay_business.py sale) read gold_mult() at the sale's own time, like the street's.
* 'tile'  🧩 Ghép ba (game/tile_match.py): the tray is full → the page takes the last tile back and the save gets
  TILE_PACK more free boosters, kept until used (spent after the day's own free uses, before xu).
* 'jail'  🚔 Trại tạm giữ (game/jail.py): out at once (owner 19/10: "trại giam giữ có thể ra tù ngay nếu xem quảng
  cáo"); the sentence block goes, jail.mark_commit drops the mark in the same transaction.
* 'theft' 💸 Bị trộm, bị lừa (owner 19/10 "ok"): half (LOSS_PCT) of the save's latest theft / scam loss back into the
  wallet, once, within LOSS_TTL. note_loss() keeps that loss where it happens: game/rui.py (móc túi, trộm, hack),
  game/mishap.py (giả danh, link giả, ATM, côn đồ…; never a police fine), game/happenings.py (theft at work),
  game/life.py (bị lừa).
* 'retake' 📝 Trượt thi, phỏng vấn (owner 19/10 "ok luôn"), {what, career?}: 'job' the workplace takes an application
  again today (employment cooldown_day), 'cert' the free self-study exam opens now (certificates: start and ready move
  back together, as its validator wants), 'promo' a review that did not pass comes again after the next shift (wait 0).
* 'rush'  📦 Hàng đang về (owner 19/10 "xem quảng cáo xong về ngay luôn"), {career}: every order still on its way to
  that workplace is at the door now (game/inventory.py orders and the stock desk's shipments: placed/lo/hi/at move to
  the door's minute, late cleared, the order their validators want kept).

Save: journey['ads'] (optional; older servers keep it untouched and ignore it)
  {v, d: VN date, n: views that day, tk?: ticket {id, p, at, k?}, g?: gold until (epoch s), tb?: {booster: n},
   ls?: the latest theft / scam loss {amt, w: what, at: epoch s}}.
The count follows the save, so one account has DAY_MAX a day (reset_all carries it: journey.carry_reset). Many accounts
on one device are fine (owner 19/10: "1 máy nhiều lần được k cần chặn nhé, dù sao người ta cũng ủng hộ mà").
Off unless ADS_REWARDED=1 (the AdSense account of game/observability.py, once H5 Games Ads approved it) or ADS_FAKE=1
(a local stand-in ad, never in production). MNL_ADS_OFF=1 switches everything off.
"""
from __future__ import annotations

import datetime
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
PLACES = ('gold', 'tile', 'jail', 'theft', 'retake', 'rush')
RETAKE = ('job', 'cert', 'promo')
LOSS_PCT = 50                    # owner: "bị trộm bị lừa", half back
LOSS_TTL = 86400                 # …within a day of the loss
GOLD_S = 3600                    # owner: "1 tiếng x1.5"
GOLD_MULT = 150                  # hundredths
GOLD_AHEAD = DAY_MAX * GOLD_S    # gold never runs further ahead than a day's views
TILE_PACK = {'undo': 1, 'shuffle': 1, 'push': 1}
TILE_KEEP = 30                   # boosters of one kind kept at most
CLIENT = re.compile(r'ca-pub-[0-9]{10,20}')


def _now() -> float:
    return time.time()


def today(t: float | None = None) -> str:
    return datetime.datetime.fromtimestamp(_now() if t is None else t, VN).date().isoformat()


def _flag(name: str) -> bool:
    return os.environ.get(name, '').strip().lower() in ('1', 'true', 'yes', 'on')


def client() -> str:
    """The AdSense publisher id while rewarded ads are switched on (ADS_REWARDED=1), else ''."""
    if not _flag('ADS_REWARDED'):
        return ''
    from .observability import ADSENSE_ACCOUNT
    return ADSENSE_ACCOUNT if CLIENT.fullmatch(ADSENSE_ACCOUNT) else ''


def fake() -> bool:
    """A stand-in ad for local play and browser tests: a countdown, no Google script."""
    return _flag('ADS_FAKE') and not client()


def enabled() -> bool:
    return not _flag('MNL_ADS_OFF') and bool(client() or fake())


# ---------------------------------------------------------------- the page: meta, CSP (/ads.txt: game/observability.py)
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


def note_loss(s: dict, amount, what: str) -> None:
    """💸 A theft or scam just took `amount` xu: the loss an ad may give half of back (a newer one replaces it)."""
    if not enabled() or type(amount) is not int or amount <= 0 or not (s.get('journey') or {}).get('story'):
        return
    t = _now()
    _ensure(s, t)['ls'] = dict(amt=min(amount, 10**9), w=str(what)[:80], at=int(t))


def _loss(s: dict, t: float) -> dict | None:
    ls = (get(s) or {}).get('ls')
    return ls if isinstance(ls, dict) and t - ls['at'] <= LOSS_TTL else None


def loss_back(s: dict, t: float | None = None) -> int:
    ls = _loss(s, _now() if t is None else t)
    return max(1, ls['amt'] * LOSS_PCT // 100) if ls else 0


def _career(s: dict, k: str | None):
    cid = (k or '').partition(':')[2]
    c = (s.get('careers') or {}).get(cid)
    return cid, (c if isinstance(c, dict) else None)


def _on_the_way(c: dict, career: str) -> list:
    """(order, door minute) of everything still on its way to this workplace: stock orders and stock-desk shipments,
    each against the minute its own receive check reads."""
    from . import engine, inventory
    out = []
    x = (c.get('ext') or {}).get('inv')
    if isinstance(x, dict) and isinstance(x.get('orders'), list):
        door = inventory.clock(c, career, turn=c['turn'] - 1)['abs']
        out += [(o, door) for o in x['orders'] if o.get('status') == 'in_transit' and 'at' in o and o['at'] > door]
    if isinstance(c.get('shipments'), list):
        door = engine._clock(c, career, c['turn'] - 1)['abs']
        out += [(o, door) for o in c['shipments'] if o.get('status') == 'in_transit' and 'at' in o and o['at'] > door]
    return out


def _retake(s: dict, k: str) -> str | None:
    """Why `k` ('job:<career>', 'cert', 'promo:<career>') has no wait to skip; None when it has one."""
    what = k.partition(':')[0]
    j = s['journey']
    if what == 'cert':
        from . import certificates
        st = j.get('study')
        if not isinstance(st, dict) or st.get('mode') == 'class' or j['life_day'] >= st['ready']:
            return 'Không có bài thi chứng chỉ nào đang phải chờ.'
        return None if j['life_day'] - certificates.SELF_DAYS >= 1 else 'Bài thi chứng chỉ mở vào ngày mai.'
    cid, c = _career(s, k)
    if c is None:
        return 'Nơi làm việc không hợp lệ.'
    if what == 'job':
        from . import employment
        job = c.get('job') or {}
        late = job.get('status') == 'rejected' and employment.today(s, c) < (job.get('cooldown_day') or 0)
        return None if late else 'Nơi này không hẹn bạn phỏng vấn lại.'
    from . import promotion
    rec = promotion.record(s, cid)
    return None if isinstance(rec, dict) and rec.get('wait', 0) > 0 else 'Không có buổi xét nào phải chờ.'


def _hhmm(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).strftime('%H:%M')


def _can(s: dict, place: str, t: float, k: str | None = None) -> None:
    """What the place gives, or why it gives nothing now."""
    e = _core()
    need = e.need
    from . import jail
    inside = jail.jailed(s, t)
    need(place == 'jail' or not inside, 'Trong trại chỉ xem quảng cáo để ra trại thôi nhé.', 'jailed')
    if place == 'jail':
        need(inside, 'Bạn đang không ở trong trại.', 'ads_place')
    elif place == 'gold':
        need(gold_until(s) < t + GOLD_AHEAD - GOLD_S + 1, 'Giờ vàng riêng đã đủ dài rồi, dùng bớt rồi xem tiếp nhé.', 'ads_place')
    elif place == 'tile':
        tb = tile_credits(s)
        need(all(tb.get(b, 0) < TILE_KEEP for b in TILE_PACK), 'Bạn còn nhiều trợ giúp Ghép ba lắm rồi.', 'ads_place')
    elif place == 'theft':
        need(_loss(s, t) is not None, 'Không có khoản tiền nào vừa bị trộm hay bị lừa để lấy lại.', 'ads_place')
    elif place == 'retake':
        why = _retake(s, k or '')
        need(why is None, why or '', 'ads_place')
    elif place == 'rush':
        cid, c = _career(s, k)
        need(c is not None and bool(_on_the_way(c, cid)), 'Không có hàng nào đang trên đường tới.', 'ads_place')


def _give(s: dict, a: dict, place: str, t: float, result: dict, k: str | None = None) -> None:
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
        jail.release(j)
        result['message'] = '🎉 Bạn được ra trại ngay. Về nhà thôi, sống tử tế nha!'
        result['jail'] = dict(free=True)
    elif place == 'theft':
        x = loss_back(s, t)
        ls = a.pop('ls')
        jr._wallet(j, x, 'life', f'📺 Lấy lại một nửa · {ls["w"]}')
        result['message'] = f'💸 Lấy lại được {x:,} xu vào ví.'.replace(',', '.')
    elif place == 'retake':
        what = k.partition(':')[0]
        cid, c = _career(s, k)
        if what == 'cert':
            from . import certificates
            st = j['study']
            st['start'], st['ready'] = j['life_day'] - certificates.SELF_DAYS, j['life_day']
            result['message'] = '📝 Bài thi chứng chỉ mở ngay bây giờ. Chúc bạn thi tốt!'
        elif what == 'job':
            from . import employment
            job = c['job']
            job['cooldown_day'] = job['retry_told'] = employment.today(s, c)
            result['message'] = '📝 Nơi tuyển dụng đồng ý cho bạn ứng tuyển lại ngay hôm nay.'
        else:
            from . import promotion
            promotion.record(s, cid)['wait'] = 0
            result['message'] = '📝 Hẹn xét lại ngay sau ca làm tới.'
    elif place == 'rush':
        cid, c = _career(s, k)
        for o, door in _on_the_way(c, cid):
            o.update(placed=min(o['placed'], door), lo=door, hi=door, at=door, late=None)
        result['message'] = '📦 Hàng đã về tới cửa rồi, ra nhận và kiểm đếm nhé!'


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
        need({'place'} <= set(p) <= {'place', 'what', 'career'} and p['place'] in PLACES, 'Quảng cáo không hợp lệ.', 'ads_place')
        place = p['place']
        k = None
        if place == 'retake':
            need(p.get('what') in RETAKE and set(p) <= {'place', 'what', 'career'}, 'Quảng cáo không hợp lệ.', 'ads_place')
            k = 'cert' if p['what'] == 'cert' else f"{p['what']}:{p.get('career')}"
        elif place == 'rush':
            need(set(p) == {'place', 'career'}, 'Quảng cáo không hợp lệ.', 'ads_place')
            k = f"rush:{p['career']}"
        else:
            need(set(p) == {'place'}, 'Quảng cáo không hợp lệ.', 'ads_place')
        need(k is None or (len(k) <= 60 and re.fullmatch(r'[a-z]+(:[a-z0-9_]+)?', k) is not None),
             'Quảng cáo không hợp lệ.', 'ads_place')
        a = _ensure(s, t)
        need(a['n'] < DAY_MAX, f'Hôm nay bạn đã xem đủ {DAY_MAX} quảng cáo rồi. Mai xem tiếp nhé!', 'ads_day')
        _can(s, place, t, k)
        a['tk'] = dict(id=secrets.token_hex(8), p=place, at=ms, **({'k': k} if k else {}))
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
        place, k = tk['p'], tk.get('k')
        _can(s, place, t, k)
        del a['tk']
        a['n'] += 1
        _give(s, a, place, t, result, k)
        result['ad'] = dict(place=place, n=a['n'], left=DAY_MAX - a['n'])
    e.validate_state(s)
    return s, result


def carry_reset(old: dict, fresh: dict) -> None:
    """reset_all: the day's views stay counted (and what was earned with them)."""
    a = (old.get('journey') or {}).get(KEY)
    if isinstance(a, dict):
        keep = {k: (dict(v) if isinstance(v, dict) else v) for k, v in a.items() if k not in ('tk', 'ls')}
        fresh['journey'][KEY] = keep


def public(s: dict) -> dict | None:
    """state.ads (None while ads are off): the day's views left and the gold window."""
    if not enabled() or not (s.get('journey') or {}).get('story'):
        return None
    t = _now()
    n = views_today(s, t)
    ls = _loss(s, t)
    return dict(n=n, max=DAY_MAX, left=DAY_MAX - n, gold=gold_until(s) if gold_until(s) > t else 0,
                mult=GOLD_MULT, gold_s=GOLD_S, now=int(t),
                theft=dict(back=loss_back(s, t), what=ls['w'], until=ls['at'] + LOSS_TTL) if ls else None)


def validate(s: dict) -> None:
    a = (s.get('journey') or {}).get(KEY)
    if a is None:
        return
    e = _core()
    need, integer = e.need, e.integer
    msg = 'Quảng cáo trong bản lưu không hợp lệ.'
    need(isinstance(a, dict) and {'v', 'd', 'n'} <= set(a) <= {'v', 'd', 'n', 'tk', 'g', 'tb', 'ls'}, msg)
    need(a['v'] == VERSION and isinstance(a['d'], str) and len(a['d']) == 10, msg)
    integer(a['n'], 0, DAY_MAX)
    if 'tk' in a:
        tk = a['tk']
        need(isinstance(tk, dict) and {'id', 'p', 'at'} <= set(tk) <= {'id', 'p', 'at', 'k'} and tk['p'] in PLACES, msg)
        need('k' not in tk or (isinstance(tk['k'], str) and re.fullmatch(r'[a-z]+(:[a-z0-9_]+)?', tk['k']) is not None
                                and len(tk['k']) <= 60), msg)
        need(isinstance(tk['id'], str) and re.fullmatch(r'[0-9a-f]{16}', tk['id']) is not None, msg)
        integer(tk['at'], 0, 10**14)
    if 'g' in a:
        integer(a['g'], 0, 10**11)
    if 'ls' in a:
        ls = a['ls']
        need(isinstance(ls, dict) and set(ls) == {'amt', 'w', 'at'} and isinstance(ls['w'], str) and len(ls['w']) <= 80, msg)
        integer(ls['amt'], 1, 10**9)
        integer(ls['at'], 0, 10**11)
    if 'tb' in a:
        need(isinstance(a['tb'], dict) and a['tb'] and set(a['tb']) <= set(TILE_PACK), msg)
        for v in a['tb'].values():
            integer(v, 1, TILE_KEEP)
