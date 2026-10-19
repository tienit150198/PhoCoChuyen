"""⚔️ Bang → ⚔️ Đảo bang: the Bang tables (game/bang.py) behind the island's contract (game/bang_island.py,
docs/BANG_ISLAND.md). Found by bang_island.provider() on first use (PROVIDER below); the live service uses the same
object (access_live).

* bang_of: the player's bang now (a membership row 'in' of an active bang).
* view: the bang's name, emoji, colour (C.COLORS hex), its level (the Đại sảnh's level) and its seven facilities
  mapped onto the island's ids (FAC: kho → kho_bang, tuong → tuong_bang, cong → cong_bang, the others the same), each
  with its own top level (`max`: 5 or 10) and the line of what the next level brings. A build whose time is up counts
  as done before anybody opened the bang's page (read only: bang.finish_builds writes it on the next write).
  A disbanded bang has no island (404); a bang an operator hid keeps it for its members only (like its page).
* access: a member (role mapped onto the island's role ids) or a guest: a player the bang invited (an open invitation,
  bang_asks kind 'invite'): they may look around before they accept. Anyone else: None. 🏝️ 21/10: with the island's
  level (`isle`, 0 while the bang has not bought it: a member gets the offer, the live room refuses; a guest of such a
  bang is nobody) and the room's cap (C.isle_cap). The view carries `isle` {level, max, state, ready_at, cap}.
* offer: what a member sees before the island is bought (the price, the fund, whether they may buy it).
* act: the facility buttons that change something on the server: ⬆️ Nâng cấp = the bang's own build command
  (bang.OPS['build'], Phó bang and up, paid from the fund, the same checks and log), asked to confirm first
  ({confirm: {title, text, label}}: the client asks, then sends {confirm: true}). The buttons that open a sheet
  (members, fund, shop, golden hour, ranking, invitations, the pet arena) are client hooks (public/js/v4/bang-island.js).

Notices: game/bang.py _isle() tells the live service on join / leave / kick / role / invitation / build / disband.
"""
from __future__ import annotations

from . import bang as BG
from . import bang_content as C
from . import bang_island as BI

FAC = {'dai_sanh': 'dai_sanh', 'kho': 'kho_bang', 'xuong_may': 'xuong_may', 'san_pet': 'san_pet', 'den_vang': 'den_vang',
       'tuong': 'tuong_bang', 'cong': 'cong_bang'}
ISLE = {v: k for k, v in FAC.items()}
ROLE = {'chu': 'bang_chu', 'pho': 'pho_bang', 'lao': 'truong_lao', 'tinh': 'tinh_anh', 'tv': 'thanh_vien'}

ISLE_COLS = 'b.isle AS isle, b.isle_to AS isle_to, b.isle_ready AS isle_ready'
MEMBER_SQL = (f"SELECT m.role AS role, {ISLE_COLS} FROM bang_members m JOIN bangs b ON b.id=m.bang "
              "WHERE m.sid=? AND m.bang=? AND m.status='in' AND b.status='active'")
GUEST_SQL = (f"SELECT 1 AS x, {ISLE_COLS} FROM bang_asks k JOIN bangs b ON b.id=k.bang WHERE k.sid=? AND k.bang=? AND k.kind='invite' "
             "AND k.status='open' AND b.status='active' AND b.hidden=0")


def _answer(member, guest) -> BI.Access | None:
    row = member or guest
    if not row:
        return None
    lv = BG.island_of(dict(row), BG.now())['level']
    if member:
        return BI.Access(kind='member', role=ROLE.get(member['role'], 'thanh_vien'), isle=lv, cap=C.isle_cap(lv))
    if lv < 1:                     # 🏝️ nothing to look around yet
        return None
    return BI.Access(kind='guest', role=None, isle=lv, cap=C.isle_cap(lv))


def _note(fac: str, level: int) -> str:
    return f'Cấp {level}: {C.perk(fac, level)}'[:BI.NOTE_MAX]


class BangIslandSource:
    def bang_of(self, store, sid):
        with store.connect() as db:
            r = db.execute("SELECT m.bang FROM bang_members m JOIN bangs b ON b.id=m.bang WHERE m.sid=? AND m.status='in' "
                           "AND b.status='active'", (sid,)).fetchone()
        return str(r['bang']) if r else None

    def view(self, store, bang_id):
        t = BG.now()
        with store.connect() as db:
            b = db.execute("SELECT id, name, emoji, color, isle, isle_to, isle_ready FROM bangs WHERE id=? AND status='active'",
                           (bang_id,)).fetchone()
            if not b:
                return None
            il = BG.island_of(dict(b), t)
            if il['level'] < 1:          # 🏝️ not bought: no island to draw (access answers the offer first)
                return None
            rows = {r['fac']: r for r in db.execute('SELECT fac, level, target, ready_at FROM bang_facilities WHERE bang=?',
                                                    (bang_id,)).fetchall()}
        facilities, hall = [], 1
        for fac, isle in FAC.items():
            top = C.max_level(fac)
            r = rows.get(fac)
            lv = int(r['level'] or 0) if r else 0
            target, ready = (r['target'], r['ready_at']) if r else (None, None)
            if target is not None and ready is not None and float(ready) <= t:
                lv, target = max(lv, int(target)), None          # done by now: finish_builds writes it later
            if fac == C.HALL:
                lv = max(1, lv)                                   # every bang starts with its hall (bang.levels)
                hall = lv
            lv = min(lv, top)
            one = dict(id=isle, level=lv, max=top, state='done', ready_at=None)
            if target is not None and lv < top:
                one.update(state='building', ready_at=float(ready))
                one['note'] = _note(fac, lv + 1)
            elif lv < top:
                one['note'] = _note(fac, lv + 1)
            facilities.append(one)
        color = (C.COLORS.get(b['color']) or C.COLORS['do'])[1]
        lv = il['level']
        isle_view = dict(level=lv, max=C.ISLE_MAX, state='done', ready_at=None, cap=C.isle_cap(lv))
        if il['to'] is not None and lv < C.ISLE_MAX:
            isle_view.update(state='building', ready_at=float(il['ready']))
        return dict(bang_id=str(b['id']), name=str(b['name'])[:BI.NAME_MAX], emoji=str(b['emoji'])[:BI.EMOJI_MAX] or '⚔️',
                    color=color, level=max(1, min(BI.BANG_LEVEL_MAX, hall)), facilities=facilities, isle=isle_view)

    def access(self, store, sid, bang_id):
        if not sid:
            return None
        with store.connect() as db:
            member = db.execute(MEMBER_SQL, (sid, bang_id)).fetchone()
            guest = None if member else db.execute(GUEST_SQL, (sid, bang_id)).fetchone()
        return _answer(member, guest)

    async def access_live(self, db, sid, bang_id):
        if not sid:
            return None
        member = await db.fetchrow(MEMBER_SQL, (sid, bang_id))
        guest = None if member else await db.fetchrow(GUEST_SQL, (sid, bang_id))
        return _answer(member, guest)

    def offer(self, store, sid, bang_id):
        """🏝️ Before the island is bought: its price, the fund, whether this member may buy it (Phó bang and up)."""
        with store.connect() as db:
            b = db.execute('SELECT fund FROM bangs WHERE id=?', (bang_id,)).fetchone()
            m = db.execute(MEMBER_SQL, (sid, bang_id)).fetchone()
        xu, _ = C.isle_cost(1)
        officer = bool(m) and C.ROLES.get(m['role'], C.ROLES['tv'])[3] >= C.BUILD_FROM
        return dict(cost=xu, fund=int(b['fund']) if b else 0, officer=officer, cap=C.isle_cap(1), zone=C.ISLE_ZONES[0],
                    top=C.ISLE_MAX, top_cost=sum(C.ISLE_PRICES), top_cap=C.isle_cap(C.ISLE_MAX))

    def act(self, store, sid, bang_id, facility, op, data):
        acc = self.access(store, sid, bang_id)
        BI.need(acc and acc.get('kind') == 'member', 'Chỉ thành viên của bang mới dùng được.', 'not_member', 403)
        if op != 'nang_cap':   # the client opens the right sheet for every other button (bang-island.js hooks)
            return dict(message='Mở mục này trong ⚔️ Bang nhé.')
        fac = ISLE.get(facility)
        BI.need(fac in C.FACILITIES, 'Không có công trình này.', 'unknown_action')
        confirm = isinstance(data, dict) and data.get('confirm') is True
        f = C.FACILITIES[fac]
        try:
            if not confirm:
                # the same checks as the build, nothing written: the question with the price
                def ask(db):
                    mine = BG._mine(db, sid)
                    BI.need(mine and mine['bang'] == bang_id, 'Bạn đang ở bang khác.', 'not_member', 403)
                    try:
                        BG.OPS['build'](db, sid, dict(fac=fac), BG.now())
                    except BG.BangError as e:
                        if e.code != 'bang_error':   # a real refusal (max, hall, slots, fund…)
                            raise
                    lv = BG.levels(db, bang_id)[fac]
                    xu, secs = C.cost(fac, lv + 1)
                    return dict(confirm=dict(title=f'Xây {f["emoji"]} {f["name"]} cấp {lv + 1}?',
                                             text=f'Dùng {BG.fmt(xu)} xu quỹ bang, xây {secs // 3600} giờ. {C.perk(fac, lv + 1)}.',
                                             label=f'Xây · {BG.fmt(xu)} xu'),
                                message=f'Xây {f["name"]} cấp {lv + 1}: {BG.fmt(xu)} xu quỹ bang.')
                return store.transaction(ask)

            def build(db):
                mine = BG._mine(db, sid)
                BI.need(mine and mine['bang'] == bang_id, 'Bạn đang ở bang khác.', 'not_member', 403)
                return BG.OPS['build'](db, sid, dict(fac=fac, confirm=True), BG.now())
            out = store.transaction(build)
        except BG.BangError as e:
            raise BI.BangIslandError(e.message, e.code, getattr(e, 'status', 400)) from None
        BG._VIEW.clear()
        return out


PROVIDER = BangIslandSource()
