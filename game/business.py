"""Atomic server-time settlement shared by commands and read refreshes."""
import secrets
import time
from . import quay_business, workplace_business, business_progression

ACTION='business_sync'


def settle(s,now=None):
    now=time.time() if now is None else now
    quay=quay_business.settle(s,now=now)
    workplace=workplace_business.settle(s,now=now)
    return quay or workplace


def reconcile(s):
    """Anchor resumed work after receiving stock/funds; never pay new income here."""
    now=time.time();changed=quay_business.reconcile(s)
    changed=business_progression.reconcile(s,now=now) or changed
    for cid,c in s.get('careers',{}).items():
        if c.get('ops',{}).get('business') is not None:
            changed=workplace_business.refresh(c,cid,now=now) or changed
    return changed


def on_load(store,token,state):
    return on_load_result(store,token,state) is not None


def on_load_result(store,token,state,own=False):
    """Return the committed public view so read routes need not load it again.
    `own`: `state` is what this thread's Store.read just returned and the caller hands it over (it
    uses only the returned view afterwards): the sync then starts from it if the save has not moved,
    instead of reading and parsing the same save a second time (Store.command `own`)."""
    now=time.time()
    from . import auto_stock  # 🤖 Tự nhận hàng: deliveries that came while the player was away
    from . import auto_order  # 🔁 Tự đặt hàng: what ran low while away (staff sales, lots that expired)
    if not (business_progression.owner_due(state,now=now) or quay_business.due(state,now=now) or workplace_business.due(state,now=now) or auto_stock.due(state) or auto_order.due(state)):
        return None
    # Each transaction rechecks the saved cursor. Concurrent tabs serialize via
    # Store's revision/CAS, so a new request id never means paying an order twice.
    if own:return store.command(token,'business-'+secrets.token_hex(12),None,None,ACTION,{},internal=True,own=state)
    return store.command(token,'business-'+secrets.token_hex(12),None,None,ACTION,{},internal=True)
