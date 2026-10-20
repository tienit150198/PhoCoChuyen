"""📸 Chụp ảnh cho người chơi (owner 21/10: "người chơi làm nhiếp ảnh chụp cho người chơi khác, giá ×3 NPC hoặc giá
thương lượng"). A photographer player (anyone who started the 📸 photobooth career, any level) photographs ANOTHER
player: the buyer's real character, with their spouse, baby or pet as props when they have them.

The flow (this file's own path; 🛎️ Phố dịch vụ lists the photographers and opens it, see "Phố dịch vụ" below):

1. 🛒 Order (buyer, POST /api/photo/order): from the photographer's place card (work visit) or profile. A package
   (PKGS), who comes along (the spouse, a baby, a pet: only what the buyer really has), a wish (backdrop, mood) and a
   price: the photographer's list price (the NPC base × MULT unless they set their own) or an offer of the buyer's
   between the package's FLOOR and CAP. The buyer's LOOK SNAPSHOT is taken now from the saves (wardrobe look and
   colours, the spouse's look from the spouse's own save, the baby's stage and outfit, the pet's breed, coat and
   clothes), so the photographer can shoot later while the buyer is away. The price is held in escrow: wallet first,
   then the bank account (never a loan), one wallet row of kind 'life'. One transaction: the buyer's save and the
   photo_orders row (marriage._mutate).
2. ✅ Accept / ✖ decline (photographer). A declined, cancelled (buyer, before it is accepted) or expired order gives
   the whole price back: the buyer's own cancel straight into their save, the others through a `live_effects` row of
   kind 'photo' (paid on the buyer's next load, once).
3. 📷 The session (photographer, a real mini-game on the client, judged here): backdrop (studio colours, street
   spots, the pagoda, the buyer's island when they own one, a wedding arch, a product table), light, framing (whole
   body / half / close-up), pose and expression (public/js/v4/booth-poses.js ids), a hand prop; then the shutter:
   a 3-2-1 countdown, then the subject settles (`lead`), holds the pose with eyes open (`hold`), blinks, then the pose
   is gone. Tap in the hold. SHOTS shots, each judged from the elapsed time the client measured (like the
   photobooth career's judge). The beat of every shot is rolled from the order id, so a retry is the same shot.
4. 🖼️ Deliver: pick the best of the shots, retouch lightly (brightness, warmth, smooth skin, vignette, each in a
   small range: too much costs a star), and send. The photo is stored (`photos`), the order is done, the photographer
   is paid PAY_PCT % of the price into their wallet (their own save, in the same transaction) and BURN_PCT % is burned
   (photo_orders.burn: buyer debit = pay + burn, exactly). Stars (1-5) from the shot, the wish, the light, the framing
   and the retouch.

The deliverable is the game's OWN render, not an upload: a small JSON (the look snapshot + the session's choices +
the retouch), ~1-2 KB, drawn by public/js/v4/portrait-art.js with the game's avatar painters (look.js figureOf,
booth-poses.js paintPeople, baby-art.js, pet-art.js). Nothing a player draws or uploads ever reaches another player:
every id is checked against the lists below, the names come from the accounts. "💾 Lưu ảnh" saves a PNG on the
device only.

🖼️ Album (buyer): the photos made for them (`photos.buyer`), newest first; past ALBUM_MAX the oldest move to the
archive (`archived` = 1: "Xem cũ hơn"), never deleted. Each photo can be:
* "🙂 Đặt làm ảnh hồ sơ": photo_pfp (one row a player), shown on the Phố nghề profile card (game/social.py).
* "🖼️ Treo trong nhà": a frame piece (`anh_chup`, game/deco_content.py, unique: not sold, not sellable) into the bag of
  furniture (journey.reno.items) and its photo in the small optional key journey['photo_wall'] = {uid: photo id}
  (validate below; 2.4.66 never reads it and keeps it, journey.validate allows extra keys).
* "👁 Ẩn khỏi bộ sưu tập của thợ": the photographer keeps a copy in their portfolio (`folio`), public on their place
  card; the buyer may hide it.

🛡️ Anti-abuse (a pipe between one's own accounts is what to stop): accounts for both, the photographer's ACCOUNT_DAYS
old; never one's own place; never across a block; prices only between FLOOR and CAP of the package; the same
network refused (the buyer's network tag, game/pet_arena.ip_tag, against the photographer's last one, at the order
and again when the photographer accepts and delivers); PAIR_DAY orders between the same two players a Vietnam day
(both ways); BUYER_OPEN open orders a buyer, SHOOTER_OPEN a photographer.

🛎️ Phố dịch vụ (game/service_market.py, SCHEMA 63): install() (server start, and the market's seed) registers
('photobooth', <package id>) for each package as an own-flow listing (spec `open`): the directory shows each public,
open studio (its work-visit place visible to everyone, the photographer's account ACCOUNT_DAYS old) with this
studio's price and record, and its button opens this file's order sheet for that place and package. Ordering, the
escrow (photo_orders), the session and the payout stay here: the market refuses to order, negotiate or set up these
services itself (one payment path, never a second escrow). Prices (×1–×5 of the NPC base) and open / closed are set
in 📸 Khách đặt chụp (set_studio). MNL_PHOTO_DIRECT_OFF=1 stops new orders while the open ones finish. 🛑
MNL_PHOTO_OFF=1: everything refused gracefully, nothing of any save changes.

Tables (game/pg_schema.py, SCHEMA_VERSION 66): photo_studios, photo_orders, photos, photo_pfp. Save: no root key;
journey['photo_wall'] optional; wallet rows of kind 'life'; 'photo' live_effects rows (an older build leaves them
pending: the refund waits, never lost).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time

from . import marriage as mr

# ---------------------------------------------------------------- packages and prices
CAREER = 'photobooth'
MULT = 3                  # a player photographer's default price: the NPC base × 3 (owner 21/10)
FLOOR_MULT = 1            # an offer goes down to the NPC price
CAP_MULT = 5              # and up to 5 × (no laundering through an absurd price)
BURN_PCT = 5              # burned on delivery
PAY_PCT = 100 - BURN_PCT
PKGS = {
    'chan_dung': dict(name='Chân dung', emoji='🧑‍🎨', base=300, hold=1.15, fit=('nua', 'can'), need=None),
    'doi': dict(name='Ảnh đôi · cưới', emoji='💑', base=500, hold=1.0, fit=('toan', 'nua'), need='mate'),
    'gia_dinh': dict(name='Gia đình', emoji='👨‍👩‍👧', base=700, hold=.85, fit=('toan',), need='family'),
    'day_thang': dict(name='Đầy tháng', emoji='👶', base=600, hold=.8, fit=('nua', 'can'), need='baby'),
    'san_pham': dict(name='Sản phẩm', emoji='🛍️', base=400, hold=1.5, fit=('can',), need='shop'),
}
ORDER = tuple(PKGS)


def floor_of(pkg: str) -> int:
    return PKGS[pkg]['base'] * FLOOR_MULT


def cap_of(pkg: str) -> int:
    return PKGS[pkg]['base'] * CAP_MULT


def default_of(pkg: str) -> int:
    return PKGS[pkg]['base'] * MULT


def split(price: int) -> tuple[int, int]:
    """(paid to the photographer, burned): burn = price × BURN_PCT %, rounded down; they add up to the price."""
    burn = price * BURN_PCT // 100
    return price - burn, burn


# ---------------------------------------------------------------- the session's choices (ids shared with the client)
BACKDROPS = {   # id: (name, emoji, group)
    'kem': ('Phông kem', '🤍', 'studio'), 'hong': ('Phông hồng', '🩷', 'studio'), 'xanh': ('Phông xanh', '🩵', 'studio'),
    'den': ('Phông đen', '🖤', 'studio'), 'giay': ('Giấy xám', '🩶', 'studio'),
    'pho_den': ('Phố đèn lồng', '🏮', 'street'), 'ho_sen': ('Hồ sen', '🪷', 'street'), 'cho_hoa': ('Chợ hoa', '💐', 'street'),
    'cau': ('Cầu gỗ hoàng hôn', '🌇', 'street'), 'chua': ('Chùa Gió Lành', '🛕', 'temple'), 'dao': ('Đảo riêng', '🏝️', 'island'),
    'cuoi': ('Cổng hoa cưới', '💒', 'wedding'), 'ban_sp': ('Bàn chụp sản phẩm', '📦', 'product'),
}
LIGHTS = {'mem': ('Đèn hộp mềm', '💡'), 'ven': ('Đèn ven tóc', '✨'), 'tu_nhien': ('Nắng tự nhiên', '☀️'),
          'vang': ('Nắng chiều vàng', '🌅'), 'kich': ('Đèn gắt một bên', '🔦')}
# which lights suit which backdrop group (the 💡 star)
LIGHT_FIT = {'studio': ('mem', 'ven'), 'street': ('tu_nhien', 'vang'), 'temple': ('vang', 'tu_nhien'), 'island': ('tu_nhien', 'vang'),
             'wedding': ('mem', 'ven', 'vang'), 'product': ('mem', 'kich')}
DARK_FIT = ('ven', 'kich')          # the black backdrop wants a rim or a hard light
FRAMINGS = {'toan': ('Toàn thân', '🧍'), 'nua': ('Nửa người', '👤'), 'can': ('Cận mặt', '🙂')}
# booth-poses.js ids (tests/test_photo_studio.py checks they exist there): portrait poses, and the ones made together
SOLO_POSES = ('dung', 'v', 'vay', 'tim', 'tim_nho', 'ma', 'nghieng', 'ngau', 'chong_nanh', 'cuoi', 'suy_nghi', 'ngai', 'om_tim',
              'hoan_ho', 'chao', 'nhay_mat', 'like', 'hon_gio', 'meo', 'xoay_vay')
GROUP_POSES = ('tim_to', 'khoac_vai', 'tua_vai', 'om_nhau', 'nam_tay', 'chum_dau', 'cung_nhay')
POSES = SOLO_POSES + GROUP_POSES
FACES = ('auto', 'cuoi_hip', 'cuoi_tit', 'lap_lanh', 'mat_tim', 'do_mat', 'hon', 'le_luoi', 'phong_ma', 'mat_meo')
PROPS = ('none', 'hoa', 'bong_bay', 'vuong_mien', 'non_la', 'kinh_ram', 'kinh_tim', 'long_den', 'tai_tho', 'mu_tn')   # photo-frames.js PROPS ids
MOODS = {'any': ('Thợ chọn', '🎲'), 'tuoi': ('Tươi tắn', '😊'), 'sang': ('Sang trọng', '🎩'), 'nghich': ('Tinh nghịch', '😜'),
         'tinh': ('Tình cảm', '💞')}
MOOD_FACES = {'tuoi': {'cuoi_hip', 'cuoi_tit', 'lap_lanh'}, 'sang': set(), 'nghich': {'le_luoi', 'phong_ma', 'mat_meo'},
              'tinh': {'mat_tim', 'hon', 'do_mat'}}
MOOD_POSES = {'tuoi': {'v', 'vay', 'hoan_ho', 'cuoi', 'tim', 'like', 'cung_nhay'},
              'sang': {'dung', 'chong_nanh', 'nghieng', 'ngau', 'suy_nghi', 'chao'},
              'nghich': {'meo', 'nhay_mat', 'ngai', 'hon_gio', 'xoay_vay'},
              'tinh': {'tim', 'tim_nho', 'om_tim', 'tim_to', 'tua_vai', 'om_nhau', 'nam_tay', 'khoac_vai', 'chum_dau'}}
PRODUCTS = {   # Sản phẩm: what the shop owner brings (drawn as an emoji on a pedestal)
    'tra_sua': ('Ly trà sữa', '🧋'), 'ca_phe': ('Ly cà phê', '☕'), 'banh': ('Bánh kem', '🎂'), 'banh_mi': ('Bánh mì', '🥖'),
    'hoa': ('Bó hoa', '💐'), 'vay': ('Bộ váy', '👗'), 'giay': ('Đôi giày', '👟'), 'son': ('Thỏi son', '💄'),
    'nhan': ('Chiếc nhẫn', '💍'), 'gau': ('Gấu bông', '🧸'), 'cay': ('Chậu cây', '🪴'), 'sach': ('Cuốn sách', '📚'),
}
RETOUCH = {'sang': (-2, 2), 'am': (-2, 2), 'min': (0, 2), 'vig': (0, 2)}   # brightness, warmth, smooth skin, vignette
RETOUCH_OVER = 4          # |sang| + |am| + min + vig above this: "chỉnh quá tay", one star less
SHOTS = 3                 # shots in a session ("chọn ảnh đẹp nhất trong 3 kiểu")
COUNT = 3.0               # 3-2-1
LEAD = (.3, .75)          # the subject settles (seconds after the count; rolled per shot)
BLINK = .9                # after the hold: a blink; later still the pose is gone
EL_MAX = 20.0             # an elapsed time past this is not a tap of this shot

# ---------------------------------------------------------------- limits
ACCOUNT_DAYS = 3          # the photographer's account (the one who gets the xu), like lì xì's grabbers
PAIR_DAY = 2              # orders between the same two players a Vietnam day (either way)
BUYER_OPEN = 5            # open orders (waiting + being shot) of one buyer
SHOOTER_OPEN = 20         # in one photographer's queue
OPEN_HOURS = 48           # not accepted in time: expired, the price goes back
SHOOT_HOURS = 72          # accepted, not delivered in time: the same
ALBUM_MAX = 60            # photos in a player's album; older ones go to the archive (Xem cũ hơn), never deleted
PAGE = 24
FOLIO_PAGE = 12
WALL_MAX = 12             # framed photos a save keeps (journey['photo_wall'])
NOTE_MAX = 80
KIND = 'life'             # wallet history kind (journey.HISTORY_KINDS): every build knows it
FX = 'photo'              # live_effects kind (game/live_effects.py PAYS)
FRAME_KIND = 'anh_chup'   # the frame piece (game/deco_content.py)
WALL_KEY = 'photo_wall'
DAY = 86400
GONE = 'Một người chơi'
STATUSES = ('open', 'shoot', 'done', 'declined', 'cancelled', 'expired')
ID_RX = re.compile(r'p[ho][0-9a-f]{16}')
RID_RX = re.compile(r'[A-Za-z0-9_-]{8,64}')
PLACE_RX = re.compile(r'wp_[0-9a-f]{24}')
PID_RX = re.compile(r'[0-9a-f]{16}')
UID_RX = re.compile(r'[A-Za-z0-9_-]{1,12}')
MARKET = dict(on=False)   # install(): Phố dịch vụ lists the packages


class PhotoError(mr.MarriageError):
    """A refusal shown as is (server.py answers it like Hôn nhân's)."""


def need(ok, message: str, code: str = 'photo', status: int = 400) -> None:
    if not ok:
        raise PhotoError(message, code, status)


def now() -> float:
    return time.time()


def vn_day(t: float | None = None) -> str:
    return time.strftime('%Y-%m-%d', time.gmtime((now() if t is None else t) + 7 * 3600))


def pid_of(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


def fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def off() -> bool:
    return os.environ.get('MNL_PHOTO_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


def direct_off() -> bool:
    return os.environ.get('MNL_PHOTO_DIRECT_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


OFF_TEXT = 'Chụp ảnh cho người chơi đang tạm nghỉ để bảo trì. Quay lại sau nhé!'


def _h(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16)


def _j(raw, default):
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return default
    return v if isinstance(v, type(default)) else default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def ip_tag(ip: str) -> str:
    from .pet_arena import ip_tag as tag   # one keyed hash of the network address for the anti-abuse rules
    return tag(ip)


# ---------------------------------------------------------------- 🔌 the marketplace seam
def _market_row(r: dict, pkg: str, t: float) -> dict:
    """A photographer's package as Phố dịch vụ lists it (service_market own-flow row)."""
    st = dict(prices=r.get('prices') or '{}')
    old = str(r.get('created_at') or '') <= time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t - ACCOUNT_DAYS * DAY))
    is_open = r.get('open') is None or bool(r['open'])
    why = ('' if r['visibility'] == 'public' and is_open and old else
           'Tiệm ảnh đang tạm nghỉ nhận đơn: mở lại ở 📸 Khách đặt chụp.' if not is_open else
           f'Tiệm ảnh hiện ở Phố dịch vụ khi tài khoản đủ {ACCOUNT_DAYS} ngày.' if not old else
           'Chỗ làm chưa mở cho mọi người: chọn “Mọi người” ở chỗ làm để hiện ở Phố dịch vụ.')
    return dict(sid=r['owner'], price=prices_of(st)[pkg], on=not why, stars=int(r.get('stars') or 0), rated=int(r.get('done') or 0),
                deals=int(r.get('done') or 0), at=float(r.get('updated_at') or 0), data=dict(place=r['id'], pkg=pkg), why=why)


_MARKET_SQL = ('SELECT p.id, p.owner, p.visibility, p.updated_at, s.open, s.prices, s.done, s.stars, a.created_at FROM work_visit_places p '
               'JOIN accounts a ON a.sid=p.owner LEFT JOIN photo_studios s ON s.sid=p.owner '
               "WHERE p.kind='career' AND p.target=? ")


def _providers(pkg: str):
    def rows(db, limit, offset):
        t = now()
        cut = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t - ACCOUNT_DAYS * DAY))
        got = _rows(db, _MARKET_SQL + "AND p.visibility='public' AND COALESCE(s.open,1)=1 AND a.created_at<=? "
                    'ORDER BY p.updated_at DESC, p.id LIMIT ? OFFSET ?', (CAREER, cut, int(limit), int(offset)))
        return [_market_row(r, pkg, t) for r in got]
    return rows


def _offer(pkg: str):
    def row(db, sid):
        r = _row(db, _MARKET_SQL + 'AND p.owner=?', (CAREER, sid))
        return _market_row(r, pkg, now()) if r and r['visibility'] != 'closed' else None
    return row


def market_spec(pkg: str) -> dict:
    """('photobooth', pkg) for service_market.register: an own-flow listing (keys the registry accepts)."""
    P = PKGS[pkg]
    return dict(name=P['name'], icon=P['emoji'], unit='buổi chụp', base=P['base'], floor=floor_of(pkg), max_price=cap_of(pkg),
                desc=f'Thợ ảnh người chơi chụp bạn, giao ảnh vào 🖼️ Album. Giá từ {fmt(floor_of(pkg))} đến {fmt(cap_of(pkg))} xu.',
                requires=dict(story=True), work_hours=OPEN_HOURS + SHOOT_HOURS,
                open=dict(action='photoStudio', data=dict(tab='order'), label='📸 Đặt chụp'),
                setup=dict(action='photoStudio', data=dict(tab='studio'), label='📸 Khách đặt chụp'),
                providers=_providers(pkg), offer=_offer(pkg))


def install(strict: bool = False) -> bool:
    """List the packages in 🛎️ Phố dịch vụ (game/service_market.py; idempotent). True when it took them. Called at server
    start and by the market's seed (never at import: no import cycle). A refusal is logged, never raised at runtime (the
    studio works without the listing); strict=True (tests) raises it."""
    try:
        from . import service_market as sm
    except ImportError:
        return False
    reg = getattr(sm, 'register', None)
    if not callable(reg):
        return False
    try:
        for pkg in ORDER:
            reg(CAREER, pkg, market_spec(pkg))
    except Exception:
        if strict:
            raise
        import logging
        logging.getLogger(__name__).exception('📸 photo packages: Phố dịch vụ refused the listing')
        return False
    MARKET['on'] = True
    return True


# ---------------------------------------------------------------- the look snapshot (at order time)
def _look(s: dict) -> dict:
    from . import wardrobe as wd
    lk = wd.look_of(s)
    return {k: v for k, v in lk.items() if k in ('hair', 'shade', 'skin', 'top', 'bottom', 'shoes', 'acc', 'tint')}


def _gender(s: dict) -> str:
    g = (s.get('journey') or {}).get('gender')
    return g if g in ('male', 'female') else 'none'


def _mate(store, sid: str) -> dict | None:
    """The spouse (engaged or married, another player): name, gender, look from their own save."""
    with store.connect() as db:
        c = mr._bond(db, sid)
        if not c or c.get('status') not in ('engaged', 'married'):
            return None
        other = mr._other(c, sid)
        name = mr._display(db, other)
    got = mr._read_state(store, other)
    if not got:
        return None
    st = got[0]
    return dict(n=name[:24], g=_gender(st), lk=_look(st))


def _babies(store, token: str | None, s: dict) -> list:
    """[{id, n, g (stage), o (outfit)}]: the save's own child (journey.household) and the couple's shared one."""
    from . import cradle as cr
    j = s.get('journey') or {}
    out = []
    m = (j.get('household') or {}).get('child')
    if isinstance(m, dict) and m.get('kind') == 'child':
        out.append(dict(id='child', n=str(m.get('name') or 'Bé')[:24], g=cr.grow(cr.household_age(j, m)), o=str(m.get('outfit') or 'basic')[:16]))
    if token:
        from . import family
        ch = (family.babies(store, token) or {}).get('child')
        if isinstance(ch, dict) and not ch.get('waiting'):
            out.append(dict(id='shared', n=str(ch.get('name') or 'Bé')[:24], g=str(ch.get('grow') or 'so_sinh')[:16], o=str(ch.get('outfit') or 'basic')[:16]))
    return out


def _pets(s: dict) -> list:
    """[{id, n, ref}]: the pets at home, as the street draws them (game/pets.py walk_ref)."""
    from . import pets as pt
    from . import pets_content as C
    from . import pet_wardrobe as pw
    from . import pet_tiers as px
    b = pt.get(s)
    out = []
    for p in (b['list'] if b else [])[:12]:
        if p.get('b') not in C.BREEDS:
            continue
        try:
            ref = dict(b=p['b'], c=p['c'], n=p['n'], **pw.walk_look(s, p), **px.walk_extra(s, p))
        except Exception:  # noqa: BLE001  (a pet this build cannot draw: left out)
            continue
        out.append(dict(id=p['id'], n=str(p.get('n') or '')[:24], ref=ref))
    return out


def _shops(s: dict) -> list:
    """[{c, n}]: the workplaces the buyer started (fixed names, never typed text)."""
    from .content import CAREER_META
    out = []
    for cid, c in (s.get('careers') or {}).items():
        if cid in CAREER_META and isinstance(c, dict) and c.get('started'):
            out.append(dict(c=cid, n=str(CAREER_META[cid].get('short') or CAREER_META[cid].get('name') or cid)[:40]))
    return out[:30]


def _island(s: dict) -> bool:
    try:
        from . import island
        return bool(island.owned(s))
    except Exception:  # noqa: BLE001
        return False


def options(store, token: str | None, s: dict) -> dict:
    """What a buyer can bring (the order sheet): spouse, babies, pets, island, shops."""
    sid = store.key(token) if token else None
    mate = _mate(store, sid) if sid else None
    return dict(mate=dict(n=mate['n']) if mate else None, babies=[dict(id=b['id'], n=b['n'], g=b['g']) for b in _babies(store, token, s)],
                pets=[dict(id=p['id'], n=p['n'], ref=p['ref']) for p in _pets(s)], island=_island(s), shops=_shops(s))


def snapshot_for(store, buyer_sid: str, opts: dict, token: str | None = None, state: dict | None = None) -> dict:
    """The look snapshot of an order, from the buyer's save (and the spouse's): {v, pkg, me, mate?, baby?, pet?, isl, shop?}.
    opts: {pkg, mate: bool, baby: id|None, pet: id|None, shop: career id|None, product: id|None}. Refusals: PhotoError."""
    pkg = opts.get('pkg')
    need(pkg in PKGS, 'Chọn gói chụp nhé.', 'bad_pkg')
    if state is None:
        got = mr._read_state(store, buyer_sid)
        need(got, 'Không tìm thấy tiến trình.', 'session_missing', 404)
        state = got[0]
    with store.connect() as db:
        name = mr._display(db, buyer_sid)
    snap = dict(v=1, pkg=pkg, me=dict(n=name[:24], g=_gender(state), lk=_look(state)), isl=_island(state))
    want_mate = opts.get('mate') is True or PKGS[pkg]['need'] == 'mate'
    if want_mate:
        mate = _mate(store, buyer_sid)
        need(mate or PKGS[pkg]['need'] != 'mate', 'Ảnh đôi cần người thương (đã đính hôn hoặc cưới) nhé.', 'no_mate', 409)
        if mate:
            snap['mate'] = mate
    bid = opts.get('baby')
    if bid or PKGS[pkg]['need'] == 'baby':
        bb = _babies(store, token, state)
        pick = next((b for b in bb if b['id'] == bid), bb[0] if bb and not bid else None)
        need(pick or PKGS[pkg]['need'] != 'baby', 'Ảnh đầy tháng cần có bé ở nhà nhé.', 'no_baby', 409)
        if pick:
            snap['baby'] = dict(n=pick['n'], g=pick['g'], o=pick['o'])
    pet = opts.get('pet')
    if pet:
        p = next((x for x in _pets(state) if x['id'] == pet), None)
        need(p, 'Bé cưng này không còn ở nhà.', 'no_pet', 409)
        snap['pet'] = p['ref']
    if pkg == 'gia_dinh':
        need(any(k in snap for k in ('mate', 'baby', 'pet')), 'Ảnh gia đình cần thêm người thương, em bé hoặc bé cưng nhé.', 'no_family', 409)
    if pkg == 'san_pham':
        prod = opts.get('product')
        need(prod in PRODUCTS, 'Chọn món muốn chụp nhé.', 'bad_product')
        shops = _shops(state)
        sh = next((x for x in shops if x['c'] == opts.get('shop')), shops[0] if shops and not opts.get('shop') else None)
        need(sh, 'Chụp sản phẩm cần có một chỗ làm đã mở nhé.', 'no_shop', 409)
        snap['shop'] = dict(c=sh['c'], n=sh['n'], p=prod)
    return snap


def valid_snap(snap) -> bool:
    return isinstance(snap, dict) and snap.get('v') == 1 and snap.get('pkg') in PKGS and isinstance(snap.get('me'), dict)


# ---------------------------------------------------------------- the session: beat, judge, stars
def people_of(snap: dict) -> int:
    return 1 + ('mate' in snap)


def beat(order_id: str, n: int, pkg: str) -> dict:
    """The rhythm of shot n: {count, lead, hold, blink} in seconds (rolled from the order id: a retry is the same)."""
    h = _h('photo-beat', order_id, n)
    lead = LEAD[0] + (h % 1000) / 1000 * (LEAD[1] - LEAD[0])
    hold = PKGS[pkg]['hold'] * (.85 + ((h >> 12) % 300) / 1000)
    return dict(count=COUNT, lead=round(lead, 3), hold=round(hold, 3), blink=BLINK)


def judge(b: dict, el: float) -> str:
    """good: in the hold; early: still settling (blurry); blink: just after; late: the pose is gone."""
    x = el - b['count']
    if x < b['lead']:
        return 'early'
    if x <= b['lead'] + b['hold']:
        return 'good'
    if x <= b['lead'] + b['hold'] + b['blink']:
        return 'blink'
    return 'late'


def clean_set(snap: dict, st) -> dict:
    """A shot's choices, every id checked (PhotoError on a wrong one)."""
    need(isinstance(st, dict), 'Thông tin buổi chụp không hợp lệ.', 'bad_set')
    pkg = snap['pkg']
    bd, light, frame = st.get('bd'), st.get('light'), st.get('frame')
    need(bd in BACKDROPS, 'Chọn phông nền nhé.', 'bad_set')
    need(BACKDROPS[bd][2] != 'island' or snap.get('isl'), 'Khách chưa có đảo riêng để chụp.', 'no_island')
    need(light in LIGHTS, 'Chọn đèn nhé.', 'bad_set')
    need(frame in FRAMINGS, 'Chọn khung hình nhé.', 'bad_set')
    pose, face, prop = st.get('pose', 'dung'), st.get('face', 'auto'), st.get('prop', 'none')
    need(pose in POSES, 'Chọn dáng nhé.', 'bad_set')
    need(pose not in GROUP_POSES or people_of(snap) > 1, 'Dáng này cần hai người.', 'bad_set')
    need(face in FACES, 'Chọn biểu cảm nhé.', 'bad_set')
    need(prop in PROPS, 'Chọn đạo cụ nhé.', 'bad_set')
    if pkg == 'san_pham':
        pose, face, prop = 'dung', 'auto', 'none'
    if 'baby' in snap:   # the arms hold the baby
        prop = 'none' if prop in ('hoa', 'bong_bay', 'long_den') else prop
    return dict(bd=bd, light=light, frame=frame, pose=pose, face=face, prop=prop)


def mood_ok(mood: str, pose: str, face: str) -> bool:
    if mood not in MOOD_FACES:
        return True
    if mood == 'sang':
        return pose in MOOD_POSES['sang'] and face in ('auto', 'cuoi_hip')
    return face in MOOD_FACES[mood] or (face == 'auto' and pose in MOOD_POSES[mood])


def light_ok(bd: str, light: str) -> bool:
    if bd == 'den':
        return light in DARK_FIT
    return light in LIGHT_FIT[BACKDROPS[bd][2]]


def score(snap: dict, wish: dict, shot: dict, rt: dict) -> tuple[int, list]:
    """(stars 1-5, [the misses, short]): 5 minus one a miss, two for a shot that is not good."""
    st, pkg, misses = shot['set'], snap['pkg'], []
    if shot['q'] != 'good':
        misses += [{'early': 'Ảnh hơi nhòe', 'blink': 'Có người nhắm mắt', 'late': 'Hết dáng mất rồi'}[shot['q']]] * 2
    want = wish.get('bd') or 'any'
    if want != 'any' and st['bd'] != want:
        misses.append('Không đúng phông khách muốn')
    if pkg != 'san_pham' and not mood_ok(wish.get('mood') or 'any', st['pose'], st['face']):
        misses.append('Chưa đúng không khí khách muốn')
    if not light_ok(st['bd'], st['light']):
        misses.append('Đèn chưa hợp phông')
    if st['frame'] not in PKGS[pkg]['fit']:
        misses.append('Khung hình chưa hợp gói chụp')
    if sum(abs(rt[k]) for k in RETOUCH) > RETOUCH_OVER:
        misses.append('Chỉnh ảnh quá tay')
    return max(1, 5 - len(misses)), misses


def clean_rt(rt) -> dict:
    need(isinstance(rt, dict), 'Thông tin chỉnh ảnh không hợp lệ.', 'bad_rt')
    out = {}
    for k, (lo, hi) in RETOUCH.items():
        v = rt.get(k, 0)
        need(type(v) is int and lo <= v <= hi, 'Mức chỉnh ảnh không hợp lệ.', 'bad_rt')
        out[k] = v
    return out


# ---------------------------------------------------------------- reading rows
def _row(db, sql, args=()):
    return mr._row(db, sql, args)


def _rows(db, sql, args=()):
    return mr._rows(db, sql, args)


def _who(store, token) -> tuple[str, str]:
    sid, display = mr.whoami(store, token)
    need(sid, 'Phiên chơi đã hết hạn. Tải lại trang nhé.', 'session_missing', 401)
    need(display, 'Tạo tài khoản để chụp ảnh với người chơi khác nhé.', 'account_required', 403)
    return sid, display


def _old_enough(db, sid: str, t: float, days: int) -> bool:
    r = db.execute('SELECT created_at FROM accounts WHERE sid=?', (sid,)).fetchone()
    return bool(r) and str(r['created_at']) <= time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t - days * DAY))


def _blocked(db, a: str, b: str) -> bool:
    from . import work_visits as wv
    return wv._blocked(db, a, b)


def _place_of(db, place: str) -> dict | None:
    return _row(db, "SELECT * FROM work_visit_places WHERE id=? AND kind='career' AND target=?", (place, CAREER))


def place_id(sid: str) -> str:
    from . import work_visits as wv
    return wv._place_id(sid, 'career', CAREER)


def _is_shooter(db, sid: str) -> bool:
    return bool(_place_of(db, place_id(sid)))


def _studio(db, sid: str) -> dict:
    r = _row(db, 'SELECT * FROM photo_studios WHERE sid=?', (sid,))
    return r or dict(sid=sid, open=1, prices='{}', ip='', done=0, stars=0)


def prices_of(studio: dict) -> dict:
    """{pkg: price}: the photographer's own (kept inside FLOOR..CAP) or the default ×MULT."""
    own = _j(studio.get('prices'), {})
    out = {}
    for pkg in ORDER:
        v = own.get(pkg)
        out[pkg] = v if type(v) is int and floor_of(pkg) <= v <= cap_of(pkg) else default_of(pkg)
    return out


def _touch(db, sid: str, tag: str, t: float) -> None:
    """The photographer's last network tag (the same-network rule) and pid."""
    db.execute('INSERT INTO photo_studios(sid, pid, name, open, prices, ip, done, stars, at) VALUES(?,?,?,1,?,?,0,0,?) '
               "ON CONFLICT(sid) DO UPDATE SET ip=CASE WHEN excluded.ip<>'' THEN excluded.ip ELSE photo_studios.ip END, at=excluded.at",
               (sid, pid_of(sid), mr._display(db, sid)[:24], '{}', tag, t))


def _pkg_view(prices: dict) -> list:
    return [dict(id=k, name=P['name'], emoji=P['emoji'], base=P['base'], floor=floor_of(k), cap=cap_of(k), price=prices[k], need=P['need'],
                 fit=list(P['fit'])) for k, P in PKGS.items()]


def catalog() -> dict:
    """The lists the client shows (names in Vietnamese; ids are what travels)."""
    return dict(pkgs=_pkg_view({k: default_of(k) for k in ORDER}),
                backdrops=[dict(id=k, name=v[0], emoji=v[1], group=v[2]) for k, v in BACKDROPS.items()],
                lights=[dict(id=k, name=v[0], emoji=v[1]) for k, v in LIGHTS.items()],
                framings=[dict(id=k, name=v[0], emoji=v[1]) for k, v in FRAMINGS.items()],
                poses=list(SOLO_POSES), group_poses=list(GROUP_POSES), faces=list(FACES), props=list(PROPS),
                moods=[dict(id=k, name=v[0], emoji=v[1]) for k, v in MOODS.items()],
                products=[dict(id=k, name=v[0], emoji=v[1]) for k, v in PRODUCTS.items()],
                retouch={k: list(v) for k, v in RETOUCH.items()}, retouch_over=RETOUCH_OVER, shots=SHOTS,
                burn=BURN_PCT, mult=MULT, pair_day=PAIR_DAY, open_hours=OPEN_HOURS, shoot_hours=SHOOT_HOURS, album_max=ALBUM_MAX)


def _order_view(r: dict, me: str) -> dict:
    sess = _j(r.get('sess'), {})
    out = dict(id=r['id'], pkg=r['pkg'], price=int(r['price']), list=int(r['list_price']), status=r['status'], at=float(r['at']),
               until=float(r['until']), buyer=dict(pid=r['buyer_pid'], name=r['buyer_name']), shooter=dict(pid=r['shooter_pid'], name=r['shooter_name']),
               wish=_j(r.get('wish'), {}), mine=r['buyer'] == me, photo=r.get('photo') or '', pay=int(r.get('pay') or 0), burn=int(r.get('burn') or 0))
    if r.get('note'):
        out['note'] = r['note']
    if r['shooter'] == me:
        out['snap'] = _j(r.get('snap'), {})
        if r['status'] == 'shoot':
            n = len(sess.get('shots') or [])
            out['sess'] = dict(shots=sess.get('shots') or [], beat=beat(r['id'], n, r['pkg']) if n < SHOTS else None)
    return out


def _photo_view(r: dict, me: str | None = None, full: bool = True) -> dict:
    out = dict(id=r['id'], pkg=r['pkg'], stars=int(r['stars']), at=float(r['at']), by=dict(pid=r['shooter_pid'], name=r['shooter_name']),
               archived=bool(r.get('archived')), folio=bool(r.get('folio')))
    if full:
        out['data'] = _j(r.get('data'), {})
    if me is not None:
        out['mine'] = r['buyer'] == me
        out['shot'] = r['shooter'] == me
    return out


# ---------------------------------------------------------------- GET /api/photo/<sub>
def get(store, token, state, sub: str, q: dict) -> dict:
    need(not off(), OFF_TEXT, 'off', 503)
    if sub == 'catalog':
        return dict(ok=True, catalog=catalog())
    if sub == 'one':   # a photo's render data by id (home frames, profile cards): ids are random and unguessable
        pid = q.get('id')
        need(isinstance(pid, str) and ID_RX.fullmatch(pid), 'Ảnh không hợp lệ.', 'bad_id')
        with store.connect() as db:
            r = _row(db, 'SELECT * FROM photos WHERE id=?', (pid,))
        need(r, 'Không tìm thấy ảnh.', 'gone', 404)
        return dict(ok=True, photo=_photo_view(r))
    if sub == 'folio':   # a photographer's public portfolio (profile card, place card)
        target = q.get('pid')
        need(isinstance(target, str) and PID_RX.fullmatch(target), 'Không tìm thấy thợ ảnh.', 'gone', 404)
        with store.connect() as db:
            rows = _rows(db, 'SELECT * FROM photos WHERE shooter_pid=? AND folio=1 ORDER BY at DESC LIMIT ?', (target, FOLIO_PAGE))
        return dict(ok=True, photos=[_photo_view(r) for r in rows])
    sid, _ = _who(store, token)
    if sub == 'studio':
        return studio_view(store, sid, q)
    if sub == 'place':
        return place_view(store, token, sid, q)
    if sub == 'album':
        return album_view(store, sid, q)
    need(False, 'Không có mục này.', 'unknown', 404)


def studio_view(store, sid: str, q: dict | None = None, ip: str = '') -> dict:
    """📸 The photographer's queue (open → shoot → done), their prices and portfolio count."""
    t = now()
    with store.connect() as db:
        shooter = _is_shooter(db, sid)
        if not shooter:
            return dict(ok=True, shooter=False, catalog=catalog())
        st = _studio(db, sid)
        rows = _rows(db, "SELECT * FROM photo_orders WHERE shooter=? AND status IN ('open','shoot') ORDER BY at LIMIT ?", (sid, SHOOTER_OPEN + 5))
        done = _rows(db, "SELECT * FROM photo_orders WHERE shooter=? AND status NOT IN ('open','shoot') ORDER BY at DESC LIMIT 8", (sid,))
        folio = int(db.execute('SELECT COUNT(*) FROM photos WHERE shooter=?', (sid,)).fetchone()[0])
    prices = prices_of(st)
    return dict(ok=True, shooter=True, now=t, open=bool(st['open']), prices=prices, pkgs=_pkg_view(prices),
                queue=[_order_view(r, sid) for r in rows], recent=[_order_view(r, sid) for r in done],
                stats=dict(done=int(st['done']), stars=round(int(st['stars']) / int(st['done']), 1) if int(st['done']) else 0, folio=folio),
                place=place_id(sid), catalog=catalog())


def place_view(store, token, sid: str, q: dict) -> dict:
    """The buyer's order sheet for one photographer's place: their prices, portfolio, rating; what the buyer can bring."""
    place = q.get('place')
    need(isinstance(place, str) and PLACE_RX.fullmatch(place), 'Không tìm thấy tiệm ảnh.', 'gone', 404)
    from . import work_visits as wv
    with store.connect() as db:
        row = _place_of(db, place)
        need(row and wv._accessible(db, row, sid), 'Tiệm ảnh này đang đóng với bạn.', 'closed', 404)
        owner = row['owner']
        st = _studio(db, owner)
        name = mr._display(db, owner)
        photos = _rows(db, 'SELECT * FROM photos WHERE shooter=? AND folio=1 ORDER BY at DESC LIMIT ?', (owner, FOLIO_PAGE))
        mine = _rows(db, "SELECT * FROM photo_orders WHERE buyer=? AND shooter=? ORDER BY at DESC LIMIT 5", (sid, owner))
    got = mr._read_state(store, sid)
    need(got, 'Không tìm thấy tiến trình.', 'session_missing', 404)
    prices = prices_of(st)
    return dict(ok=True, place=place, self=owner == sid, shooter=dict(pid=pid_of(owner), name=name[:24]), open=bool(st['open']),
                pkgs=_pkg_view(prices), stats=dict(done=int(st['done']), stars=round(int(st['stars']) / int(st['done']), 1) if int(st['done']) else 0),
                photos=[_photo_view(r) for r in photos], orders=[_order_view(r, sid) for r in mine],
                can=options(store, token, got[0]), catalog=catalog())


def album_view(store, sid: str, q: dict) -> dict:
    """🖼️ The buyer's album (newest first; old=1: the archive, paged by `before`), orders on their way, the profile photo."""
    old = q.get('old') in ('1', 1, True)
    try:
        before = float(q.get('before')) if q.get('before') not in (None, '') else None
    except (TypeError, ValueError):
        before = None
    with store.connect() as db:
        args = [sid, 1 if old else 0]
        sql = 'SELECT * FROM photos WHERE buyer=? AND archived=?'
        if before is not None:
            sql += ' AND at<?'
            args.append(before)
        rows = _rows(db, sql + ' ORDER BY at DESC LIMIT ?', (*args, PAGE + 1))
        n_old = int(db.execute('SELECT COUNT(*) FROM photos WHERE buyer=? AND archived=1', (sid,)).fetchone()[0])
        orders = _rows(db, "SELECT * FROM photo_orders WHERE buyer=? AND (status IN ('open','shoot') OR at>?) ORDER BY at DESC LIMIT 12",
                       (sid, now() - 3 * DAY))
        pfp = _row(db, 'SELECT photo FROM photo_pfp WHERE sid=?', (sid,))
    more = len(rows) > PAGE
    rows = rows[:PAGE]
    return dict(ok=True, photos=[_photo_view(r, sid) for r in rows], more=more, old=old, archived=n_old,
                next=float(rows[-1]['at']) if more and rows else None, orders=[_order_view(r, sid) for r in orders],
                pfp=(pfp or {}).get('photo') or '', catalog=catalog())


# ---------------------------------------------------------------- POST /api/photo/<op>
OPS = ('order', 'cancel', 'accept', 'decline', 'shot', 'deliver', 'studio', 'pfp', 'hang', 'folio')


def post(store, token, state, op: str, d: dict, ip: str = '') -> dict:
    need(not off(), OFF_TEXT, 'off', 503)
    need(op in OPS, 'Thao tác không hợp lệ.', 'unknown', 404)
    need(isinstance(d, dict), 'Thông tin không hợp lệ.', 'bad')
    sid, display = _who(store, token)
    if op == 'order':
        return order(store, token, sid, d, ip)
    if op == 'cancel':
        return cancel(store, sid, d)
    if op == 'accept':
        return accept(store, sid, d, ip)
    if op == 'decline':
        return decline(store, sid, d)
    if op == 'shot':
        return shot(store, sid, d, ip)
    if op == 'deliver':
        return deliver(store, sid, d, ip)
    if op == 'studio':
        return set_studio(store, sid, d, ip)
    if op == 'pfp':
        return set_pfp(store, sid, d)
    if op == 'hang':
        return hang(store, sid, d)
    return set_folio(store, sid, d)


def _have(s: dict) -> int:
    from . import bank as bk
    j = s['journey']
    b = bk.get(s)
    return max(0, j['wallet']) + (b['balance'] if b else 0)


def _take(s: dict, amount: int, label: str) -> None:
    """`amount` from the wallet first, then the bank account (checked by the caller), like lì xì."""
    from . import bank as bk
    from . import journey as jr
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    if cash:
        jr._wallet(j, -cash, KIND, label[:120])
    rest = amount - cash
    if rest:
        b = bk.get(s)
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label[:120], -rest)


def _credit(s: dict, amount: int, label: str) -> None:
    from . import journey as jr
    jr._wallet(s['journey'], amount, KIND, label[:120])


def order(store, token, sid: str, d: dict, ip: str = '') -> dict:
    """🛒 Escrow the price from the buyer's save and write the open order, in one transaction."""
    need(not direct_off(), 'Đặt chụp ảnh giờ ở Chợ dịch vụ nhé.', 'use_market', 409)
    rid, place, pkg = d.get('rid'), d.get('place'), d.get('pkg')
    need(isinstance(rid, str) and RID_RX.fullmatch(rid), 'Mã giao dịch không hợp lệ. Tải lại trang nhé.', 'bad_rid')
    need(isinstance(place, str) and PLACE_RX.fullmatch(place), 'Không tìm thấy tiệm ảnh.', 'gone', 404)
    need(pkg in PKGS, 'Chọn gói chụp nhé.', 'bad_pkg')
    price = d.get('price')
    need(type(price) is int, 'Giá không hợp lệ.', 'bad_price')
    need(floor_of(pkg) <= price <= cap_of(pkg), f'Giá gói {PKGS[pkg]["name"]} từ {fmt(floor_of(pkg))} đến {fmt(cap_of(pkg))} xu.', 'bad_price')
    wish = d.get('wish') if isinstance(d.get('wish'), dict) else {}
    bd, mood = wish.get('bd', 'any'), wish.get('mood', 'any')
    need(bd == 'any' or bd in BACKDROPS, 'Phông nền không hợp lệ.', 'bad_wish')
    need(mood in MOODS, 'Không khí ảnh không hợp lệ.', 'bad_wish')
    note = d.get('note', '')
    need(isinstance(note, str) and len(note) <= NOTE_MAX, 'Lời nhắn quá dài.', 'bad_note')
    t, day = now(), vn_day()
    tag = ip_tag(ip)
    from . import work_visits as wv
    with store.connect() as db:
        again = _row(db, 'SELECT * FROM photo_orders WHERE buyer=? AND rid=?', (sid, rid))
        if again:
            return dict(ok=True, again=True, order=_order_view(again, sid), changed=False)
        row = _place_of(db, place)
        need(row and wv._accessible(db, row, sid), 'Tiệm ảnh này đang đóng với bạn.', 'closed', 404)
        shooter = row['owner']
        need(shooter != sid, 'Không tự đặt chụp ở tiệm mình được nha 😄', 'self', 409)
        need(not _blocked(db, sid, shooter), 'Không đặt chụp được với người này.', 'blocked', 403)
        need(db.execute('SELECT 1 FROM accounts WHERE sid=?', (shooter,)).fetchone(), 'Thợ ảnh chưa có tài khoản.', 'gone', 404)
        need(_old_enough(db, shooter, t, ACCOUNT_DAYS), f'Tiệm ảnh mở nhận đơn khi tài khoản thợ đủ {ACCOUNT_DAYS} ngày.', 'too_new', 409)
        st = _studio(db, shooter)
        need(st['open'], 'Thợ ảnh đang tạm nghỉ nhận đơn.', 'studio_closed', 409)
        their = st.get('ip') or (_row(db, 'SELECT ip FROM pet_arena WHERE sid=?', (shooter,)) or {}).get('ip') or ''
        need(not tag or not their or tag != their, 'Hai tài khoản cùng một mạng không đặt chụp cho nhau được.', 'same_net', 409)
        shooter_name = mr._display(db, shooter)
    list_price = prices_of(st)[pkg]
    snap = snapshot_for(store, sid, dict(pkg=pkg, mate=d.get('mate') is True, baby=d.get('baby') if isinstance(d.get('baby'), str) else None,
                                         pet=d.get('pet') if isinstance(d.get('pet'), str) else None,
                                         shop=d.get('shop') if isinstance(d.get('shop'), str) else None, product=d.get('product')),
                        token=token)
    oid = 'po' + secrets.token_hex(8)
    label = f'📸 Đặt chụp {PKGS[pkg]["name"]} · {shooter_name}'

    def fn(s):
        j = s.get('journey') or {}
        need(j.get('story'), 'Đặt chụp ảnh chỉ có trong hành trình.', 'not_story')
        need(j['wallet'] >= 0, f'Ví đang nợ {fmt(-j["wallet"])} xu. Trả nợ trước nhé.', 'debt', 409)
        short = price - _have(s)
        need(short <= 0, f'Còn thiếu {fmt(short)} xu.', 'not_enough', 409)
        _take(s, price, label)

    def ops(db):
        # caps hold under concurrency: both players' rows of the day, in a stable order
        for k in sorted((sid, shooter)):
            db.execute('SELECT pg_advisory_xact_lock(17831, hashtext(?))', ('photo:' + k,))
        pair = int(db.execute("SELECT COUNT(*) FROM photo_orders WHERE day=? AND ((buyer=? AND shooter=?) OR (buyer=? AND shooter=?)) "
                              "AND status<>'cancelled'", (day, sid, shooter, shooter, sid)).fetchone()[0])
        need(pair < PAIR_DAY, f'Hôm nay hai bạn đã đặt chụp {PAIR_DAY} lần rồi. Mai đặt tiếp nhé!', 'pair_limit', 409)
        mine = int(db.execute("SELECT COUNT(*) FROM photo_orders WHERE buyer=? AND status IN ('open','shoot')", (sid,)).fetchone()[0])
        need(mine < BUYER_OPEN, f'Bạn đang chờ {BUYER_OPEN} đơn chụp rồi. Đợi thợ giao ảnh nhé.', 'buyer_full', 409)
        queue = int(db.execute("SELECT COUNT(*) FROM photo_orders WHERE shooter=? AND status IN ('open','shoot')", (shooter,)).fetchone()[0])
        need(queue < SHOOTER_OPEN, 'Thợ ảnh đang kín lịch. Đặt lại sau nhé.', 'shooter_full', 409)
        db.execute('INSERT INTO photo_orders(id, rid, buyer, buyer_pid, buyer_name, shooter, shooter_pid, shooter_name, pkg, price, list_price, '
                   "status, snap, wish, sess, note, ip, day, at, until, via) VALUES(?,?,?,?,?,?,?,?,?,?,?,'open',?,?,'{}',?,?,?,?,?,'direct')",
                   (oid, rid, sid, pid_of(sid), snap['me']['n'], shooter, pid_of(shooter), shooter_name[:24], pkg, price, list_price,
                    _dump(snap), _dump(dict(bd=bd, mood=mood)), note.strip()[:NOTE_MAX], tag, day, t, t + OPEN_HOURS * 3600))
        _tell(store, db, shooter, f'📸 {snap["me"]["n"]} đặt chụp {PKGS[pkg]["name"]} ({fmt(price)} xu). Mở Tiệm ảnh để nhận nhé!', 'studio')
    from . import db as dbm
    try:
        mr._mutate_retry(store, {sid: fn}, ops)
    except dbm.IntegrityError:   # the same rid landed first
        with store.connect() as db:
            again = _row(db, 'SELECT * FROM photo_orders WHERE buyer=? AND rid=?', (sid, rid))
        need(again, 'Thử lại sau một chút nhé.', 'busy', 409)
        return dict(ok=True, again=True, order=_order_view(again, sid), changed=False)
    with store.connect() as db:
        r = _row(db, 'SELECT * FROM photo_orders WHERE id=?', (oid,))
    return dict(ok=True, order=_order_view(r, sid), changed=True,
                message=f'📸 Đã đặt chụp {PKGS[pkg]["name"]}. {fmt(price)} xu được giữ cho đến khi thợ giao ảnh.')


def _tell(store, db, sid: str, text: str, ref: str) -> None:
    """A line in the player's Phố nghề inbox (kind 'photo', ref 'studio' | 'album': the inbox's "Xem" opens it; and a push
    when they allow it). Never fails the order."""
    try:
        from . import social
        social.notify(store, db, pid_of(sid), 'photo', text, ref)
    except Exception:  # noqa: BLE001
        pass


def _lock(db, oid: str) -> dict | None:
    return _row(db, 'SELECT * FROM photo_orders WHERE id=? FOR UPDATE', (oid,))


def _oid(d: dict) -> str:
    oid = d.get('id')
    need(isinstance(oid, str) and ID_RX.fullmatch(oid) and oid.startswith('po'), 'Không tìm thấy đơn chụp.', 'gone', 404)
    return oid


def refund_row(db, r: dict, why: str, t: float) -> None:
    """The whole price back to the buyer through live_effects (paid on their next load, once: the row id)."""
    db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?) ON CONFLICT(id) DO NOTHING",
               (f'photo:{r["id"]}:back', r['buyer'], FX, int(r['price']), _dump(dict(what='back', o=r['id'], pkg=r['pkg'], why=why)), t))


def cancel(store, sid: str, d: dict) -> dict:
    """The buyer takes an order back before the photographer accepted it: the price straight back into their save."""
    oid = _oid(d)
    with store.connect() as db:
        r = _row(db, 'SELECT * FROM photo_orders WHERE id=?', (oid,))
    need(r and r['buyer'] == sid, 'Không tìm thấy đơn chụp.', 'gone', 404)
    if r['status'] == 'cancelled':
        return dict(ok=True, again=True, changed=False)
    need(r['status'] == 'open', 'Thợ đã nhận đơn rồi, không hủy được nữa.', 'taken', 409)
    t = now()

    def fn(s):
        _credit(s, int(r['price']), f'📸 Hủy đặt chụp · {r["shooter_name"]}')

    def ops(db):
        if db.execute("UPDATE photo_orders SET status='cancelled', answered=? WHERE id=? AND status='open'", (t, oid)).rowcount != 1:
            raise PhotoError('Thợ đã nhận đơn rồi, không hủy được nữa.', 'taken', 409)
    mr._mutate_retry(store, {sid: fn}, ops)
    return dict(ok=True, changed=True, message=f'Đã hủy. {fmt(r["price"])} xu về lại ví.')


def _mine(db, sid: str, oid: str, statuses) -> dict:
    r = _lock(db, oid)
    need(r and r['shooter'] == sid, 'Không tìm thấy đơn chụp.', 'gone', 404)
    need(r['status'] in statuses, 'Đơn này không còn chờ bạn.', 'gone', 409)
    return r


def _same_net(r: dict, tag: str) -> None:
    need(not tag or not r.get('ip') or tag != r['ip'], 'Hai tài khoản cùng một mạng không chụp cho nhau được.', 'same_net', 409)


def accept(store, sid: str, d: dict, ip: str = '') -> dict:
    oid, t, tag = _oid(d), now(), ip_tag(ip)

    def run(db):
        r = _lock(db, oid)
        need(r and r['shooter'] == sid, 'Không tìm thấy đơn chụp.', 'gone', 404)
        if r['status'] == 'shoot':
            return r
        need(r['status'] == 'open', 'Đơn này không còn chờ bạn.', 'gone', 409)
        _same_net(r, tag)
        _touch(db, sid, tag, t)
        db.execute("UPDATE photo_orders SET status='shoot', answered=?, until=?, sess=? WHERE id=? AND status='open'",
                   (t, t + SHOOT_HOURS * 3600, _dump(dict(shots=[])), oid))
        _tell(store, db, r['buyer'], f'📸 {r["shooter_name"]} đã nhận chụp {PKGS[r["pkg"]]["name"]} cho bạn. Ảnh sẽ vào 🖼️ Album.', 'album')
        return _row(db, 'SELECT * FROM photo_orders WHERE id=?', (oid,))
    r = store.transaction(run)
    return dict(ok=True, order=_order_view(r, sid), message='Đã nhận đơn. Vào chụp thôi!')


def decline(store, sid: str, d: dict) -> dict:
    oid, t = _oid(d), now()

    def run(db):
        r = _mine(db, sid, oid, ('open', 'shoot'))
        db.execute("UPDATE photo_orders SET status='declined', answered=?, refund=1 WHERE id=?", (t, oid))
        refund_row(db, r, 'declined', t)
        _tell(store, db, r['buyer'], f'📸 {r["shooter_name"]} chưa nhận chụp được. {fmt(r["price"])} xu đã trả lại bạn.', 'album')
        return r
    store.transaction(run)
    return dict(ok=True, message='Đã từ chối. Tiền giữ đã trả lại khách.')


def shot(store, sid: str, d: dict, ip: str = '') -> dict:
    """📷 One shot: the choices and the elapsed time of the tap, judged on the order's row (SHOTS at most)."""
    oid, tag = _oid(d), ip_tag(ip)
    el = d.get('el')
    need(isinstance(el, (int, float)) and not isinstance(el, bool) and 0 <= el <= EL_MAX, 'Lượt bấm máy không hợp lệ.', 'bad_el')
    n_want = d.get('n')

    def run(db):
        r = _mine(db, sid, oid, ('shoot',))
        _same_net(r, tag)
        snap, sess = _j(r['snap'], {}), _j(r['sess'], {})
        shots = sess.get('shots') or []
        if type(n_want) is int and n_want < len(shots):   # a retry of a shot already taken: the same answer
            return r, shots[n_want], shots
        need(len(shots) < SHOTS, f'Đã chụp đủ {SHOTS} kiểu. Chọn ảnh đẹp nhất nhé.', 'full', 409)
        st = clean_set(snap, d.get('set'))
        b = beat(oid, len(shots), r['pkg'])
        one = dict(set=st, q=judge(b, float(el)), el=round(float(el), 3))
        shots = shots + [one]
        sess['shots'] = shots
        db.execute('UPDATE photo_orders SET sess=? WHERE id=?', (_dump(sess), oid))
        return r, one, shots
    r, one, shots = store.transaction(run)
    n = len(shots)
    return dict(ok=True, shot=one, n=n, left=SHOTS - n, beat=beat(oid, n, r['pkg']) if n < SHOTS else None)


def deliver_photo(db, order_id: str, buyer_sid: str, shooter_sid: str, pkg: str, snap: dict, result: dict, t: float | None = None) -> str:
    """Store a finished photo: the buyer's album (the oldest past ALBUM_MAX to the archive) and the photographer's
    portfolio. result: {set, q, rt, stars, misses}. The marketplace's `deliver` hook too. Returns the photo id."""
    t = now() if t is None else t
    pid = 'ph' + secrets.token_hex(8)
    shooter_name = mr._display(db, shooter_sid)[:24]
    data = dict(v=1, pkg=pkg, snap=snap, set=result['set'], q=result['q'], rt=result['rt'], by=shooter_name,
                day=time.strftime('%d.%m.%y', time.gmtime(t + 7 * 3600)))
    db.execute('INSERT INTO photos(id, order_id, buyer, buyer_pid, shooter, shooter_pid, shooter_name, pkg, data, stars, at, archived, folio) '
               'VALUES(?,?,?,?,?,?,?,?,?,?,?,0,1)', (pid, order_id, buyer_sid, pid_of(buyer_sid), shooter_sid, pid_of(shooter_sid), shooter_name,
                                                      pkg, _dump(data), int(result['stars']), t))
    extra = [x['id'] for x in _rows(db, 'SELECT id FROM photos WHERE buyer=? AND archived=0 ORDER BY at DESC, id DESC OFFSET ?', (buyer_sid, ALBUM_MAX))]
    if extra:   # 🗄️ the album keeps ALBUM_MAX; the older ones to the archive (Xem cũ hơn), never deleted
        marks = ','.join('?' * len(extra))
        db.execute(f'UPDATE photos SET archived=1 WHERE id IN ({marks})', tuple(extra))
    db.execute('UPDATE photo_studios SET done=done+1, stars=stars+? WHERE sid=?', (int(result['stars']), shooter_sid))
    return pid


def deliver(store, sid: str, d: dict, ip: str = '') -> dict:
    """🖼️ The best shot, retouched, to the buyer's album; PAY_PCT % into the photographer's wallet, BURN_PCT % burned."""
    oid, tag, t = _oid(d), ip_tag(ip), now()
    pick = d.get('pick')
    rt = clean_rt(d.get('rt', {}))
    with store.connect() as db:
        r = _row(db, 'SELECT * FROM photo_orders WHERE id=?', (oid,))
    need(r and r['shooter'] == sid, 'Không tìm thấy đơn chụp.', 'gone', 404)
    if r['status'] == 'done':
        return dict(ok=True, again=True, photo=r['photo'], changed=False)
    need(r['status'] == 'shoot', 'Đơn này không còn chờ bạn.', 'gone', 409)
    _same_net(r, tag)
    shots = _j(r['sess'], {}).get('shots') or []
    need(len(shots) >= SHOTS, f'Chụp đủ {SHOTS} kiểu rồi chọn ảnh đẹp nhất nhé.', 'not_enough_shots', 409)
    need(type(pick) is int and 0 <= pick < len(shots), 'Chọn một tấm để giao nhé.', 'bad_pick')
    snap, wish = _j(r['snap'], {}), _j(r['wish'], {})
    need(valid_snap(snap), 'Đơn chụp hỏng dữ liệu.', 'bad_order', 409)
    one = shots[pick]
    stars, misses = score(snap, wish, one, rt)
    pay, burn = split(int(r['price']))
    out = {}

    def fn(s):
        j = s.get('journey') or {}
        need(j.get('story'), 'Nhận tiền chụp ảnh chỉ có trong hành trình.', 'not_story')
        _credit(s, pay, f'📸 Chụp {PKGS[r["pkg"]]["name"]} cho {r["buyer_name"]}')

    def ops(db):
        cur = _lock(db, oid)
        if not cur or cur['status'] != 'shoot':
            raise PhotoError('Đơn này không còn chờ bạn.', 'gone', 409)
        _touch(db, sid, tag, t)
        photo = deliver_photo(db, oid, r['buyer'], sid, r['pkg'], snap, dict(set=one['set'], q=one['q'], rt=rt, stars=stars), t)
        db.execute("UPDATE photo_orders SET status='done', done_at=?, photo=?, pay=?, burn=? WHERE id=? AND status='shoot'", (t, photo, pay, burn, oid))
        _tell(store, db, r['buyer'], f'🖼️ {r["shooter_name"]} đã giao ảnh {PKGS[r["pkg"]]["name"]} ({stars}★). Mở 🖼️ Album xem nhé!', 'album')
        out['photo'] = photo
    mr._mutate_retry(store, {sid: fn}, ops)
    return dict(ok=True, changed=True, photo=out['photo'], stars=stars, misses=misses, pay=pay, burn=burn,
                message=f'🖼️ Đã giao ảnh {stars}★. +{fmt(pay)} xu ({BURN_PCT}% phí phố).')


def set_studio(store, sid: str, d: dict, ip: str = '') -> dict:
    """The photographer's studio: open or closed, their own prices (each between FLOOR and CAP)."""
    t, tag = now(), ip_tag(ip)
    with store.connect() as db:
        need(_is_shooter(db, sid), 'Mở Tiệm ảnh Tách Tách trước nhé.', 'not_shooter', 403)
        st = _studio(db, sid)
    prices = _j(st.get('prices'), {})
    if 'prices' in d:
        new = d['prices']
        need(isinstance(new, dict) and set(new) <= set(PKGS), 'Bảng giá không hợp lệ.', 'bad_price')
        for k, v in new.items():
            need(type(v) is int and floor_of(k) <= v <= cap_of(k), f'Giá gói {PKGS[k]["name"]} từ {fmt(floor_of(k))} đến {fmt(cap_of(k))} xu.', 'bad_price')
            prices[k] = v
    opened = d.get('open', bool(st['open']))
    need(type(opened) is bool, 'Thông tin không hợp lệ.', 'bad')

    def run(db):
        _touch(db, sid, tag, t)
        db.execute('UPDATE photo_studios SET open=?, prices=?, at=? WHERE sid=?', (1 if opened else 0, _dump(prices), t, sid))
    store.transaction(run)
    return studio_view(store, sid)


def _own_photo(db, sid: str, d: dict) -> dict:
    pid = d.get('id')
    need(isinstance(pid, str) and ID_RX.fullmatch(pid) and pid.startswith('ph'), 'Ảnh không hợp lệ.', 'bad_id')
    r = _row(db, 'SELECT * FROM photos WHERE id=?', (pid,))
    need(r and r['buyer'] == sid, 'Không tìm thấy ảnh trong album của bạn.', 'gone', 404)
    return r


def set_pfp(store, sid: str, d: dict) -> dict:
    """🙂 The profile photo (one a player): a photo of their own album, or none (id null)."""
    t = now()
    if d.get('id') is None:   # the choice cleared (the row stays, photo ''): nothing is ever deleted
        store.transaction(lambda db: db.execute("UPDATE photo_pfp SET photo='', at=? WHERE sid=?", (t, sid)))
        return dict(ok=True, pfp='', message='Đã bỏ ảnh hồ sơ.')
    with store.connect() as db:
        r = _own_photo(db, sid, d)
    store.transaction(lambda db: db.execute('INSERT INTO photo_pfp(sid, pid, photo, at) VALUES(?,?,?,?) ON CONFLICT(sid) DO UPDATE SET photo=excluded.photo, at=excluded.at',
                                            (sid, pid_of(sid), r['id'], t)))
    return dict(ok=True, pfp=r['id'], message='🙂 Đã đặt làm ảnh hồ sơ.')


def set_folio(store, sid: str, d: dict) -> dict:
    """👁 Show or hide one of my photos in its photographer's public portfolio."""
    show = d.get('show')
    need(type(show) is bool, 'Thông tin không hợp lệ.', 'bad')
    with store.connect() as db:
        r = _own_photo(db, sid, d)
    store.transaction(lambda db: db.execute('UPDATE photos SET folio=? WHERE id=? AND buyer=?', (1 if show else 0, r['id'], sid)))
    return dict(ok=True, folio=show, message='Ảnh hiện trong bộ sưu tập của thợ.' if show else 'Đã ẩn ảnh khỏi bộ sưu tập của thợ.')


def hang(store, sid: str, d: dict) -> dict:
    """🖼️ Treo trong nhà: a frame piece with this photo into the bag of furniture (journey.reno.items, kind FRAME_KIND)
    and its photo in journey['photo_wall'] {uid: photo id}. Once a photo; WALL_MAX frames."""
    with store.connect() as db:
        r = _own_photo(db, sid, d)
    out = {}

    def fn(s):
        from . import reno as rn
        j = s.get('journey') or {}
        need(j.get('story'), 'Treo ảnh chỉ có trong hành trình.', 'not_story')
        wall = j.get(WALL_KEY) if isinstance(j.get(WALL_KEY), dict) else {}
        blk = rn.ensure_block(s)
        have = {x.get('id') for x in blk['items']}
        wall = {u: p for u, p in wall.items() if u in have}   # a frame sold or gone: its line goes
        if r['id'] in wall.values():
            out['again'] = True
            j[WALL_KEY] = wall
            return
        need(len(wall) < WALL_MAX, f'Nhà đã treo {WALL_MAX} khung ảnh rồi.', 'wall_full', 409)
        uid = rn.new_uid(blk)
        blk['items'].append(dict(id=uid, k=FRAME_KIND, r=None, x=None))
        wall[uid] = r['id']
        j[WALL_KEY] = wall
        out['uid'] = uid
    mr._mutate_retry(store, {sid: fn})
    if out.get('again'):
        return dict(ok=True, changed=True, message='Khung ảnh này đã có trong túi đồ trang trí rồi.')
    return dict(ok=True, changed=True, uid=out['uid'], message='🖼️ Khung ảnh đã vào túi đồ trang trí. Mở Trang trí nhà để treo lên tường nhé!')


# ---------------------------------------------------------------- the save: journey['photo_wall'] (optional)
def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or WALL_KEY not in j:
        return
    from .engine import need as eneed
    w = j[WALL_KEY]
    eneed(isinstance(w, dict) and len(w) <= WALL_MAX and all(isinstance(u, str) and UID_RX.fullmatch(u) and isinstance(p, str)
                                                              and ID_RX.fullmatch(p) for u, p in w.items()),
          'Khung ảnh trong nhà không hợp lệ.', 'invalid_save')


def public(s: dict) -> dict | None:
    j = s.get('journey') or {}
    w = j.get(WALL_KEY)
    return dict(w) if isinstance(w, dict) and w else None


# ---------------------------------------------------------------- 🧾 a refund paid into the save (game/live_effects.py)
def apply_fx(s: dict, p: dict, amount: int) -> str:
    from . import engine as e
    data = p.get('data') if isinstance(p.get('data'), dict) else {}
    e.need(data.get('what') == 'back' and isinstance(data.get('o'), str) and ID_RX.fullmatch(data['o']) and data.get('pkg') in PKGS,
           'Dữ liệu hoàn tiền chụp ảnh không hợp lệ.')
    _credit(s, amount, f'📸 Hoàn tiền đặt chụp {PKGS[data["pkg"]]["name"]}')
    return f'📸 {fmt(amount)} xu đặt chụp ảnh đã về ví.'


# ---------------------------------------------------------------- 🧹 housekeeping: orders past their time
SWEEP_EVERY = 60.0
SWEEP_BATCH = 100
_SWEEP = dict(at=0.0)


def sweep(store, t: float | None = None) -> int:
    """Open orders not accepted in OPEN_HOURS and accepted ones not delivered in SHOOT_HOURS: expired, the whole price
    back (a live_effects row, once: under the row lock, only from open/shoot)."""
    t = now() if t is None else t

    def run(db):
        rows = _rows(db, "SELECT * FROM photo_orders WHERE status IN ('open','shoot') AND until<? ORDER BY until LIMIT ? FOR UPDATE SKIP LOCKED",
                     (t, SWEEP_BATCH))
        for r in rows:
            db.execute("UPDATE photo_orders SET status='expired', answered=?, refund=1 WHERE id=? AND status IN ('open','shoot')", (t, r['id']))
            refund_row(db, r, 'expired', t)
            _tell(store, db, r['buyer'], f'📸 Đơn chụp ở tiệm {r["shooter_name"]} đã quá hạn. {fmt(r["price"])} xu đã trả lại bạn.', 'album')
        return len(rows)
    return store.transaction(run)


def refund_waiting(store, token) -> bool:
    """A 'photo' refund waits for this save (one indexed query): GET /api/photo/album then pays it at once."""
    sid = store.key(token) if token else None
    if not sid:
        return False
    with store.connect() as db:
        return bool(db.execute("SELECT 1 FROM live_effects WHERE sid=? AND kind=? AND status='pending' LIMIT 1", (sid, FX)).fetchone())


def run_housekeeping(store) -> None:
    t = now()
    if t - _SWEEP['at'] < SWEEP_EVERY or off():
        return
    _SWEEP['at'] = t
    sweep(store, t)


# ---------------------------------------------------------------- 🗑️ a player erased their data ("Xóa dữ liệu")
def forget(store, token: str) -> None:
    """Their photos leave every portfolio and their profile photo goes (the buyers' albums keep what they paid for, the
    photographer's name becomes GONE); their own open orders close (the escrow went with their save); orders waiting in
    their studio are declined and the buyers get the whole price back (live_effects, once)."""
    sid = store.key(token) if token else None
    if not sid:
        return
    t = now()

    def run(db):
        db.execute('UPDATE photos SET folio=0 WHERE buyer=?', (sid,))
        db.execute("UPDATE photo_pfp SET photo='', at=? WHERE sid=?", (t, sid))
        db.execute("UPDATE photo_orders SET status='cancelled', answered=? WHERE buyer=? AND status IN ('open','shoot')", (t, sid))
        for r in _rows(db, "SELECT * FROM photo_orders WHERE shooter=? AND status IN ('open','shoot') FOR UPDATE", (sid,)):
            db.execute("UPDATE photo_orders SET status='declined', answered=?, refund=1 WHERE id=?", (t, r['id']))
            refund_row(db, r, 'gone', t)
        db.execute('UPDATE photos SET shooter_name=? WHERE shooter=?', (GONE, sid))
        db.execute("UPDATE photo_studios SET open=0, name=?, ip='' WHERE sid=?", (GONE, sid))
    store.transaction(run)


# ---------------------------------------------------------------- 🙂 the profile photo for other modules
def has_studio(db, sid: str) -> bool:
    """A photobooth workplace another player can order from (its work-visit place is not closed)."""
    try:
        r = _place_of(db, place_id(sid))
    except Exception:  # noqa: BLE001
        return False
    return bool(r) and r['visibility'] != 'closed'


def pfp_of(db, sid: str) -> dict | None:
    """The render data of a player's profile photo (game/social.py's profile card), or None."""
    try:
        r = _row(db, 'SELECT p.* FROM photo_pfp f JOIN photos p ON p.id=f.photo WHERE f.sid=?', (sid,))
    except Exception:  # noqa: BLE001  (an older database without the tables: no photo)
        return None
    return _photo_view(r) if r else None
