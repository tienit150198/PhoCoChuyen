"""⚔️ Đảo bang: the island a bang owns (owner-approved 19/10). Its facilities stand on fixed slots, its members (and the
guests it lets in) walk there together. This module owns only the island side; every bang fact (who is in which bang,
the levels, the build timers, the fund) belongs to the Bang branch, which plugs in through a small contract:

* The input, BangIslandView (docs/BANG_ISLAND.md has the JSON schema):
      {bang_id, name, emoji, color, level, facilities: [{id, level, state: 'building'|'done', ready_at, note?}],
       members_online?}
  `level` of a facility is the level in effect now (0: not built yet), `max` its top level (optional, ≤ 10; a Bang
  facility has 5 or 10); `state == 'building'` means level + 1 is being built and is ready at `ready_at` (epoch
  seconds). A facility the view leaves out counts as level 0, done.
* The provider (BangIslandProvider below): bang_of / view / access for the game server (sync, game.storage.Store),
  access_live for the live service (async, live.db), and optionally act (the facility buttons). The Bang branch
  registers one with register(), or simply ships game/bang_island_source.py with PROVIDER = <its provider>: provider()
  finds it on first use (it ships: the real bangs). Without one the island stays closed ("Bang chưa mở"), except
  MNL_BANG_ISLAND_STUB=1 (dev and tests only, never with DATABASE_URL): a fake bang where every signed-in player is a member.

Switch: MNL_BANG_ISLAND (game server and live service read the same variable): on by default, 0 turns it off.
No table, no save key: rolling back to a build without this module loses nothing. Positions, gestures and bubbles of
the live room are memory only (live/bang_island.py); bubbles go through the chat's store (filters, reports).

HTTP (server.py): GET /api/bang-island[?bang=<id>]  → {now, me: {kind, role}, cap, bang: island_view(...)}
                  POST /api/bang-island/act {bang, facility, op} → {done: {placeholder?, message}, ...the GET answer}
"""
from __future__ import annotations

import math
import os
import re
import time
from dataclasses import dataclass, field
from typing import Literal, Mapping, Protocol, TypedDict

from . import marriage as mr

# ---------------------------------------------------------------- the contract ---------------------------------------
LEVEL_MAX = 10
BANG_LEVEL_MAX = 99
CAP = 40                                  # people on one bang island at once (the live room's cap)
BANG_ID = re.compile(r'[a-z0-9_-]{1,32}')
COLOR = re.compile(r'#[0-9a-fA-F]{6}')
NAME_MAX, NOTE_MAX, EMOJI_MAX = 40, 120, 16
READY_MAX = 4_102_444_800                 # 2100-01-01: a ready_at past this is a unit mistake (ms instead of s)
STATES = ('building', 'done')


class FacilityView(TypedDict, total=False):
    id: str                                # one of FACILITY_IDS; an unknown id (a newer Bang build) is ignored
    level: int                             # 0..max, the level in effect now (0: not built yet)
    max: int                               # optional, 1..LEVEL_MAX (default LEVEL_MAX): this facility's top level
    state: Literal['building', 'done']     # building: level + 1 is being built
    ready_at: float | None                 # epoch seconds when the build finishes (required while building)
    note: str                              # optional: one short line the panel shows (what the next level brings)


class BangIslandView(TypedDict, total=False):
    bang_id: str                           # [a-z0-9_-]{1,32}
    name: str                              # 1..40 characters
    emoji: str                             # the bang's sign, 1..16 characters (one emoji usually)
    color: str                             # '#rrggbb': the flag on the gate and the hall
    level: int                             # the bang's own level, 1..99
    facilities: list[FacilityView]
    members_online: int                    # optional


class Access(TypedDict, total=False):
    kind: Literal['member', 'guest']       # a member of this bang, or a guest the bang let in
    role: str | None                       # the Bang branch's role id (ROLES below), None for a guest


ROLES = {'bang_chu': 'Bang chủ', 'pho_bang': 'Phó bang', 'truong_lao': 'Trưởng lão', 'tinh_anh': 'Tinh anh', 'thanh_vien': 'Thành viên'}


class BangIslandProvider(Protocol):
    """What the Bang branch implements (docs/BANG_ISLAND.md). `store` is game.storage.Store, `db` is live.db."""
    def bang_of(self, store, sid: str) -> str | None: ...                          # the bang this save belongs to
    def view(self, store, bang_id: str) -> Mapping | None: ...                     # a BangIslandView, None: no such bang
    def access(self, store, sid: str, bang_id: str) -> Access | None: ...          # may this save be on that island
    async def access_live(self, db, sid: str, bang_id: str) -> Access | None: ...  # the same, for the live service
    # optional: def act(self, store, sid, bang_id, facility, op, data) -> dict  ({message, ...}; raise BangIslandError)


class BangIslandError(mr.MarriageError):
    pass


class ContractError(ValueError):
    """A view from the provider that breaks the contract (a bug on the Bang side): logged, the player sees a short line."""


def need(ok, message, code='bang_island', status=400):
    if not ok:
        raise BangIslandError(message, code, status)


# ---------------------------------------------------------------- the facilities (ids never renamed) -----------------
# The panel's buttons are placeholders until the Bang / pet branches wire them (provider.act, or the client hook
# registerBangIslandAction in public/js/v4/bang-island.js). `who`: the branch expected to wire it.
UPGRADE = ('nang_cap', '⬆️', 'Nâng cấp', 'bang')
FACILITIES = (
    dict(id='dai_sanh', emoji='🏯', name='Đại sảnh', desc='Trái tim của bang: nơi cả bang họp mặt, treo cờ bang.',
         actions=(UPGRADE, ('thanh_vien', '👥', 'Danh sách thành viên', 'bang'))),
    dict(id='kho_bang', emoji='💰', name='Kho bang', desc='Quỹ chung của bang, chỉ góp vào, không rút ra.',
         actions=(('gop_quy', '🪙', 'Góp quỹ', 'bang'), UPGRADE)),
    dict(id='xuong_may', emoji='🧵', name='Xưởng may', desc='Nơi may áo bang và đồ riêng của bang.',
         actions=(('xuong_may', '👘', 'Vào xưởng', 'bang'), UPGRADE)),
    dict(id='san_pet', emoji='🐾', name='Sân luyện pet', desc='Sân tập cho thú cưng, cửa vào đấu trường pet.',
         actions=(('thach_dau', '⚔️', 'Thách đấu bang', 'pet'), ('dau_truong', '🏟️', 'Đấu trường pet', 'pet'), ('luyen_pet', '🎯', 'Luyện pet', 'pet'),
                  UPGRADE)),
    dict(id='den_vang', emoji='🛕', name='Đền vàng', desc='Nơi thắp hương mở giờ vàng của bang.',
         actions=(('gio_vang', '✨', 'Giờ vàng bang', 'bang'), UPGRADE)),
    dict(id='tuong_bang', emoji='🗿', name='Tượng bang', desc='Tượng đài của bang giữa quảng trường, ghi danh bang mạnh.',
         actions=(('xep_hang', '🏆', 'Xếp hạng tuần', 'bang'), UPGRADE)),
    dict(id='cong_bang', emoji='⛩️', name='Cổng bang', desc='Cổng vào lãnh địa bên bến tàu, treo cờ và tên bang.',
         actions=(('moi_khach', '💌', 'Mời khách ra đảo', 'bang'), UPGRADE)),
)
FACILITY_IDS = tuple(f['id'] for f in FACILITIES)
FACILITY = {f['id']: f for f in FACILITIES}
OPS = frozenset(a[0] for f in FACILITIES for a in f['actions'])
BANDS = ((0, 'Đất trống'), (1, 'Gỗ'), (2, 'Đá'), (3, 'Vàng'))   # band 0: not built; 1: levels 1–3, 2: 4–6, 3: 7–10
# The decorative spots of public/js/bang-island-layout.js a player can walk up to (besides the facilities).
SPOTS = ('ben_tau', 'vuon_hoa', 'ao_sen', 'rung_truc', 'den_long', 'doi_thong')


def band(level: int, top: int = LEVEL_MAX) -> int:
    """The look of a facility at `level` of `top`: 0 not built, then on the 10-level scale 1 (1–3), 2 (4–6), 3 (7–10);
    a facility with fewer levels (a Bang facility of 5) is scaled onto it (its top level is gold too)."""
    if level <= 0:
        return 0
    lv = -(-level * LEVEL_MAX // max(1, top)) if top != LEVEL_MAX else level
    return 1 if lv <= 3 else 2 if lv <= 6 else 3


def _int(v, lo, hi) -> bool:
    return type(v) is int and lo <= v <= hi


def _text(v, hi: int) -> str | None:
    if not isinstance(v, str):
        return None
    s = ' '.join(v.replace('<', '‹').replace('>', '›').split())
    return s if 1 <= len(s) <= hi else None


def validate_view(raw) -> BangIslandView:
    """The provider's view, checked and cleaned (ContractError when it breaks the contract). Unknown facility ids
    and unknown keys are dropped (a newer Bang build may send more); a facility left out is level 0, done."""
    def bad(why):
        raise ContractError(f'bang_island view: {why}')
    if not isinstance(raw, Mapping):
        bad('not an object')
    bid = raw.get('bang_id')
    if not isinstance(bid, str) or not BANG_ID.fullmatch(bid):
        bad('bang_id')
    name, emoji = _text(raw.get('name'), NAME_MAX), _text(raw.get('emoji'), EMOJI_MAX)
    if not name:
        bad('name')
    if not emoji:
        bad('emoji')
    color = raw.get('color')
    if not isinstance(color, str) or not COLOR.fullmatch(color):
        bad('color')
    if not _int(raw.get('level'), 1, BANG_LEVEL_MAX):
        bad('level')
    fac = raw.get('facilities')
    if not isinstance(fac, (list, tuple)) or len(fac) > 32:
        bad('facilities')
    out: dict[str, FacilityView] = {}
    for f in fac:
        if not isinstance(f, Mapping) or f.get('id') not in FACILITY:
            continue
        fid = f['id']
        if fid in out:
            bad(f'{fid} twice')
        lv, st, ready, top = f.get('level'), f.get('state', 'done'), f.get('ready_at'), f.get('max', LEVEL_MAX)
        if not _int(top, 1, LEVEL_MAX):
            bad(f'{fid}.max')
        if not _int(lv, 0, top):
            bad(f'{fid}.level')
        if st not in STATES:
            bad(f'{fid}.state')
        if st == 'building':
            if lv >= top:
                bad(f'{fid}: building past the top level')
            if type(ready) not in (int, float) or not math.isfinite(ready) or not 0 < ready < READY_MAX:
                bad(f'{fid}.ready_at')
            ready = float(ready)
        else:
            ready = None
        one = FacilityView(id=fid, level=lv, max=top, state=st, ready_at=ready)
        note = _text(f.get('note'), NOTE_MAX)
        if note:
            one['note'] = note
        out[fid] = one
    view = BangIslandView(bang_id=bid, name=name, emoji=emoji, color=color.lower(), level=raw['level'],
                          facilities=[out.get(i) or FacilityView(id=i, level=0, max=LEVEL_MAX, state='done', ready_at=None) for i in FACILITY_IDS])
    mo = raw.get('members_online')
    if mo is not None:
        if not _int(mo, 0, 100_000):
            bad('members_online')
        view['members_online'] = mo
    return view


def island_view(view: BangIslandView, now: float | None = None) -> dict:
    """What the client draws: the checked view plus each facility's name, look band, next level, time left, buttons."""
    now = time.time() if now is None else now
    facilities = []
    for f in view['facilities']:
        meta, lv, top = FACILITY[f['id']], f['level'], f.get('max', LEVEL_MAX)
        building = f['state'] == 'building'
        ready = f['ready_at'] if building else None
        facilities.append(dict(
            id=f['id'], name=meta['name'], emoji=meta['emoji'], desc=meta['desc'], level=lv, max=top,
            band=band(lv, top), band_name=BANDS[band(lv, top)][1], state=f['state'], ready_at=ready,
            left=max(0, int(math.ceil(ready - now))) if building else 0,
            to=lv + 1 if building else None, next=lv + 1 if lv < top else None,
            next_band=band(lv + 1, top) if lv < top else None, note=f.get('note'),
            actions=[dict(op=op, emoji=e, label=label) for op, e, label, _ in meta['actions']]))
    out = dict(id=view['bang_id'], name=view['name'], emoji=view['emoji'], color=view['color'], level=view['level'],
               facilities=facilities)
    if 'members_online' in view:
        out['members_online'] = view['members_online']
    return out


# ---------------------------------------------------------------- the provider ---------------------------------------
_provider: BangIslandProvider | None = None
_looked = False


def enabled() -> bool:
    """On unless MNL_BANG_ISLAND says otherwise (0 / empty: off), now that the Bang provider ships
    (game/bang_island_source.py). The live service reads the same switch (live/config.py)."""
    return os.environ.get('MNL_BANG_ISLAND', '1').strip().lower() in ('1', 'true', 'yes', 'on')


def register(p: BangIslandProvider | None) -> None:
    """The Bang branch's provider (None: forget it; tests). Replaces the stub and the auto-discovered one."""
    global _provider, _looked
    _provider, _looked = p, True


def provider() -> BangIslandProvider | None:
    """The registered provider; else game/bang_island_source.py's PROVIDER (the Bang branch); else the stub when
    MNL_BANG_ISLAND_STUB=1; else None (the island stays closed)."""
    global _provider, _looked
    if not _looked:
        _looked = True
        try:
            from . import bang_island_source   # the Bang branch's module (absent until it merges)
            _provider = getattr(bang_island_source, 'PROVIDER', None)
        except ImportError:
            _provider = None
        if _provider is None and stub_allowed():
            _provider = StubProvider.from_env()
    return _provider


# ---------------------------------------------------------------- the stub (dev, tests) -------------------------------
def stub_allowed() -> bool:
    """MNL_BANG_ISLAND_STUB=1 only counts off production: never with DATABASE_URL set (the servers' database), and only
    when the Bang provider is missing (provider() tries it first)."""
    if os.environ.get('MNL_BANG_ISLAND_STUB', '').strip() not in ('1', 'true', 'yes', 'on'):
        return False
    if (os.environ.get('DATABASE_URL') or '').strip():
        print('[bang-island] MNL_BANG_ISLAND_STUB ignored: DATABASE_URL is set', flush=True)
        return False
    return True


def stub_view(bang_id: str = 'bang_thu', preset: str = 'mix', now: float | None = None) -> BangIslandView:
    """A fake bang. Presets: low (levels 1–3), mid (4–6), high (7–10), build (everything under scaffolding), empty
    (nothing built), mix (one of each)."""
    now = time.time() if now is None else now
    levels = dict(low=(2, 1, 3, 1, 2, 1, 3), mid=(5, 4, 6, 5, 4, 6, 5), high=(10, 8, 9, 7, 10, 9, 8), empty=(0,) * 7,
                  build=(3, 0, 6, 2, 9, 5, 1), mix=(8, 4, 2, 6, 7, 0, 5)).get(preset) or (8, 4, 2, 6, 7, 0, 5)
    building = {'build': set(FACILITY_IDS), 'mix': {'kho_bang', 'tuong_bang'}}.get(preset, set())
    fac = [dict(id=i, level=lv, state='building' if i in building else 'done',
                ready_at=now + 600 + 1800 * k if i in building else None)
           for k, (i, lv) in enumerate(zip(FACILITY_IDS, levels))]
    colours = dict(low='#2e7d5b', mid='#2457a6', high='#b8282e', build='#7b3fa0', empty='#6b6b6b', mix='#c2410c')
    return BangIslandView(bang_id=bang_id, name={'high': 'Long Môn Các', 'low': 'Trúc Lâm Bang', 'mid': 'Thanh Vân Môn'}.get(preset, 'Bang Thử Nghiệm'),
                          emoji={'high': '🐉', 'low': '🎋', 'mid': '🌊', 'build': '🔨', 'empty': '🏳️'}.get(preset, '🦅'),
                          color=colours.get(preset, '#c2410c'), level={'high': 18, 'low': 2, 'mid': 7}.get(preset, 5),
                          facilities=fac, members_online=3)


@dataclass
class StubProvider:
    """A fake Bang for dev and tests. `members`: sid → (bang id, role); `guests`: sid → {bang ids}; `everyone`: every
    signed-in save is a member of `default` (MNL_BANG_ISLAND_STUB=1). Views: bang id → BangIslandView (or a preset)."""
    views: dict = field(default_factory=dict)
    members: dict = field(default_factory=dict)
    guests: dict = field(default_factory=dict)
    everyone: bool = False
    default: str = 'bang_thu'
    acts: list = field(default_factory=list)

    @classmethod
    def from_env(cls) -> 'StubProvider':
        preset = os.environ.get('MNL_BANG_ISLAND_STUB_SET', 'mix').strip() or 'mix'
        return cls(views={'bang_thu': stub_view('bang_thu', preset)}, everyone=True)

    def _access(self, sid: str, bang_id: str) -> Access | None:
        if sid in self.members:
            b, role = self.members[sid]
            if b == bang_id:
                return Access(kind='member', role=role)
        elif self.everyone and bang_id == self.default and sid:
            return Access(kind='member', role='thanh_vien')
        if bang_id in self.guests.get(sid, ()):
            return Access(kind='guest', role=None)
        return None

    def bang_of(self, store, sid):
        if sid in self.members:
            return self.members[sid][0]
        return self.default if self.everyone and sid else None

    def view(self, store, bang_id):
        v = self.views.get(bang_id)
        return dict(v) if v else None

    def access(self, store, sid, bang_id):
        return self._access(sid, bang_id)

    async def access_live(self, db, sid, bang_id):
        return self._access(sid, bang_id)

    def act(self, store, sid, bang_id, facility, op, data):
        self.acts.append((sid, bang_id, facility, op))
        return dict(placeholder=True, message=placeholder_line(facility, op))


# ---------------------------------------------------------------- HTTP --------------------------------------------------
def placeholder_line(facility: str, op: str) -> str:
    meta = FACILITY.get(facility)
    label = next((a[2] for a in meta['actions'] if a[0] == op), op) if meta else op
    return f'“{label}” sắp mở, hẹn bạn ít hôm nữa nhé!'


def _ready(store, token):
    need(enabled(), 'Đảo bang chưa mở.', 'off', 404)
    sid, display = mr.whoami(store, token)
    need(sid and display, 'Đăng nhập để ra đảo bang nhé.', 'login_required', 401)
    p = provider()
    need(p is not None, 'Bang chưa mở. Đảo bang sẽ có khi Bang ra mắt.', 'no_bang', 503)
    return sid, p


def _bang_arg(v) -> str | None:
    return v if isinstance(v, str) and BANG_ID.fullmatch(v) else None


def _answer(store, sid, p, bang_id: str | None) -> dict:
    now = time.time()
    if bang_id is None:
        bang_id = p.bang_of(store, sid)
        if bang_id is None:
            return dict(now=now, bang=None, me=None, cap=CAP, why='Bạn chưa vào bang nào. Vào một bang để có đảo bang nhé.')
    acc = p.access(store, sid, bang_id)
    need(acc and acc.get('kind') in ('member', 'guest'), 'Bạn không phải thành viên hay khách của bang này.', 'not_member', 403)
    raw = p.view(store, bang_id)
    need(raw is not None, 'Không tìm thấy bang này.', 'not_found', 404)
    try:
        view = validate_view(raw)
    except ContractError as e:
        print(f'[bang-island] {e}', flush=True)
        need(False, 'Đảo bang đang bận sửa, thử lại sau nhé.', 'bang_view', 502)
    need(view['bang_id'] == bang_id, 'Không tìm thấy bang này.', 'not_found', 404)
    role = acc.get('role') if acc.get('kind') == 'member' else None
    return dict(now=now, cap=CAP, bang=island_view(view, now),
                me=dict(kind=acc['kind'], role=role if role in ROLES else None, role_name=ROLES.get(role) if role else None))


def get(store, token, query=None) -> dict:
    sid, p = _ready(store, token)
    q = query or {}
    if 'bang' in q:
        need(_bang_arg(q['bang']), 'Bang không hợp lệ.')
    return _answer(store, sid, p, _bang_arg(q.get('bang')))


def post(store, token, sub, data) -> dict:
    sid, p = _ready(store, token)
    need(sub == 'act', 'Không tìm thấy mục này.', 'not_found', 404)
    need(isinstance(data, dict) and set(data) <= {'bang', 'facility', 'op', 'data'}, 'Yêu cầu không hợp lệ.')
    bang_id, fid, op = _bang_arg(data.get('bang')), data.get('facility'), data.get('op')
    need(bang_id, 'Bang không hợp lệ.')
    need(fid in FACILITY and any(a[0] == op for a in FACILITY[fid]['actions']), 'Không có thao tác này.', 'unknown_action')
    acc = p.access(store, sid, bang_id)
    need(acc and acc.get('kind') in ('member', 'guest'), 'Bạn không phải thành viên hay khách của bang này.', 'not_member', 403)
    act = getattr(p, 'act', None)
    extra = data.get('data') if isinstance(data.get('data'), dict) else {}
    done = act(store, sid, bang_id, fid, op, extra) if callable(act) else dict(placeholder=True, message=placeholder_line(fid, op))
    if not isinstance(done, dict):
        done = dict(message=str(done or ''))
    out = _answer(store, sid, p, bang_id)
    out['done'] = done
    return out


def content() -> dict | None:
    """The bootstrap's `bang_island` (game/content.py): only while MNL_BANG_ISLAND=1, so the menus list ⚔️ Đảo bang."""
    if not enabled():
        return None
    return dict(cap=CAP, level_max=LEVEL_MAX, bands=[name for _, name in BANDS],
                facilities=[dict(id=f['id'], emoji=f['emoji'], name=f['name']) for f in FACILITIES], roles=ROLES)
