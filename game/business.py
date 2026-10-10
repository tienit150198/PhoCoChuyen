"""Atomic server-time settlement shared by commands and read refreshes."""
import secrets
import time
from . import quay_business, workplace_business

ACTION='business_sync'


def settle(s,now=None):
    now=time.time() if now is None else now
    quay=quay_business.settle(s,now=now)
    workplace=workplace_business.settle(s,now=now)
    return quay or workplace


def reconcile(s):
    """Anchor resumed work after receiving stock/funds; never pay new income here."""
    now=time.time();changed=quay_business.reconcile(s)
    for cid,c in s.get('careers',{}).items():
        if c.get('ops',{}).get('business') is not None:
            changed=workplace_business.refresh(c,cid,now=now) or changed
    return changed


def on_load(store,token,state):
    return on_load_result(store,token,state) is not None


def on_load_result(store,token,state):
    """Return the committed public view so read routes need not load it again."""
    now=time.time()
    if not (quay_business.due(state,now=now) or workplace_business.due(state,now=now)):
        return None
    # Each transaction rechecks the saved cursor. Concurrent tabs serialize via
    # Store's revision/CAS, so a new request id never means paying an order twice.
    return store.command(token,'business-'+secrets.token_hex(12),None,None,ACTION,{},internal=True)
