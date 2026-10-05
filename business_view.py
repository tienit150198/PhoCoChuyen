"""Small, confirmed Quay reads; all settlement stays in the existing command.

Idle projections can be reused only after resolving this request's cookie and
checking its saved revision. No raw saves are retained. A future due check is
conservative: both predicates are monotone in time for a fixed saved state.
Running counters therefore still settle every read, including elapsed costs.
"""
import copy
import threading
import time
import weakref
from collections import OrderedDict

from game import business, quay, quay_business, workplace_business
from game.engine import GameError, migrate_state

_TTL = 30
_MAX_ENTRIES = 32
_lock = threading.Lock()
_caches = weakref.WeakKeyDictionary()
_FIELDS = ('story', 'life_day', 'wallet', 'quay')


def _identity(store, token):
    with store.connect() as db:
        sid, _ = store._resolve(db, store.digest(token))
        row = db.execute('SELECT revision FROM sessions WHERE sid=?', (sid,)).fetchone()
    if row is None:
        raise GameError('Phiên chơi không còn tồn tại. Tải lại trang nhé.', 'session_missing')
    return sid, row['revision']


def quay_snapshot(store, token):
    sid, revision = _identity(store, token)
    now = time.time()
    with _lock:
        cache = _caches.setdefault(store, OrderedDict())
        entry = cache.get(sid)
        if entry and entry[0] == revision and now < entry[1]:
            cache.move_to_end(sid)
            return copy.deepcopy(entry[2])
        cache.pop(sid, None)

    state, revision, _ = store.read(token)
    state = migrate_state(state, owned=True)
    settled = business.on_load_result(store, token, state)
    if settled is not None:
        # The command already projected its committed state. Never read again:
        # that could combine one revision's money with another revision's Quay.
        journey = settled['state']['journey']
        return {'revision': settled['revision'], 'journey': {k: journey.get(k) for k in _FIELDS}}

    journey = state['journey']
    result = {'revision': revision, 'journey': {
        'story': journey['story'], 'life_day': journey['life_day'], 'wallet': journey['wallet'],
        'quay': quay.public(state) if quay.visible(state) else None}}
    expires = now + _TTL
    if not (quay_business.due(state, now=expires) or workplace_business.due(state, now=expires)):
        # Resolve once more after a cache miss: an account cookie may have been
        # rotated/remapped while Store.read or settlement was in flight.
        current_sid, current_revision = _identity(store, token)
        if current_sid == sid and current_revision == revision:
            with _lock:
                cache[sid] = (revision, expires, copy.deepcopy(result))
                cache.move_to_end(sid)
                while len(cache) > _MAX_ENTRIES:
                    cache.popitem(last=False)
    return result
