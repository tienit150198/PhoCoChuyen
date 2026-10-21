"""📲 Máy quản lý từ xa: close the shift of a workplace from anywhere (player feedback #456, owner 21/10: allowed, but
only once the player has bought something for it).

#456: "khi làm ở nước ngoài thì có nút để đóng các cửa tiệm luôn, không cần về tiệm mới đóng ca được". Before a
contract abroad (game/abroad.py jr_abroad_work) every open shift must be closed, and until now that meant walking back
to each place.

* The device is an item of 📱 Mây Mobile (game/gadgets.py ITEMS[ITEM], its own 📲 Tiện ích tab): bought once from the
  wallet then the bank account like any gadget, sold back like one (and the remote close goes with it). No fee.
* With it, the command is the ordinary `end_day` on that workplace's career, payload {remote: true}: the very same
  engine branch, hooks (journey's wallet, living cost and life day, salary, staff wages, stock, incidents,
  happenings, promotion, x3, the bang's work point in storage, ...) and summary as "Khép ca" at the shop. Only two
  things differ, both about where the player stands: s['current'] is kept (the screen does not jump to that place),
  and leaving the place on screen is not checked (game/abandon.py check: nobody leaves it).
* A step the shop would ask for first takes the default the shop's own "Khép ca" already sends: a chuyện still running
  is carried to the next day (carry_event), an undecided incident or happening takes its default (engine end_day).
  Nothing else at a place has to be done before closing (game/dayclock.py: unfinished work is kept for tomorrow).
* Without the device the command is refused (code 'need_device') and changes nothing; a shift already closed answers
  quietly (`duplicate`) and changes nothing, so a second tap never closes a day twice.

No save key of its own: owning the device is journey['gadgets']['own'][ITEM], which an older build keeps by shape and
does not show; the `remote` payload flag is ignored by an older build (its end_day only reads carry_event).
"""
from __future__ import annotations

ITEM = 'quan_ly_xa'
NEED = 'Cần 📲 Máy quản lý từ xa (mua ở Mây Mobile, Phố dịch vụ) để khép ca từ xa.'   # one literal: the English pack
DONE = ('completed', 'referred', 'cancelled')


def _core():
    from . import engine
    return engine


def owned(s: dict) -> bool:
    j = s.get('journey')
    if not isinstance(j, dict) or not j.get('story'):
        return False
    g = j.get('gadgets')
    return isinstance(g, dict) and isinstance(g.get('own'), dict) and ITEM in g['own']


def asked(action: str, p: dict) -> bool:
    """engine: this command is a remote close."""
    return action == 'end_day' and isinstance(p, dict) and p.get('remote') is True


def gate(s: dict, career: str) -> dict | None:
    """engine, before anything changes: refuses without the device; None to go on, or the quiet answer for a shift
    already closed (nothing changes)."""
    e = _core()
    e.need(owned(s), NEED, 'need_device')
    c = s['careers'][career]
    if not c.get('open'):
        from .journey import _place
        return dict(message=f'{_place(career)} đã khép ca rồi.', duplicate=True)
    return None


def payload(p: dict) -> dict:
    """The shop's own "Khép ca" sends carry_event: a chuyện still running waits for tomorrow."""
    return dict(p, carry_event=True)


def _shop(s: dict, cid: str, c: dict) -> dict:
    ev = c.get('event')
    return dict(career=cid, day=int(c.get('day') or 1), done=int(c.get('day_completed') or 0),
                left=sum(t.get('status') not in DONE for t in c.get('tasks') or ()),
                event=bool(isinstance(ev, dict) and ev.get('stage') != 'resolved'), here=cid == s.get('current'))


def public(s: dict) -> dict | None:
    """journey.public `remote`: the open shifts and whether the device is owned. None (absent) with neither, so a
    save that never opens two places pays nothing in state size."""
    j = s.get('journey')
    if not isinstance(j, dict) or not j.get('story'):
        return None
    shops = [_shop(s, cid, c) for cid, c in (s.get('careers') or {}).items() if isinstance(c, dict) and c.get('open')]
    own = owned(s)
    if not own and not shops:
        return None
    return dict(own=own, item=ITEM, shops=shops)
