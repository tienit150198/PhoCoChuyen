"""Shared real-time market epochs; reads never draw a fresh outcome."""
import hashlib
import bisect

EPOCH_MS = 30 * 60 * 1000
PLANS = {
    'none': dict(label='Tự trông quầy', period_cost=0),
    'basic': dict(label='Bảo vệ cơ bản', period_cost=3),
    'premium': dict(label='Bảo vệ tăng cường', period_cost=7),
}
INCOME_TAX_PERCENT = 7
CYCLE_EPOCHS = 48


def _phase(epoch):
    value = int.from_bytes(hashlib.sha256(f'quay-market-v1:{epoch}'.encode()).digest()[:4], 'big')
    phase = value % 5
    if phase == 0:
        state, label, percent = 'downturn', 'Suy thoái', 25 + value % 26
    elif phase == 1:
        state, label, percent = 'boom', 'Hưng thịnh', 150 + value % 31
    else:
        state, label, percent = 'stable', 'Ổn định', 100
    return state, label, percent


_PHASES = tuple(_phase(i) for i in range(CYCLE_EPOCHS))
_PREFIX = [0]
for _state, _label, _percent in _PHASES:
    _PREFIX.append(_PREFIX[-1] + _percent * EPOCH_MS)
_CYCLE_WORK = _PREFIX[-1]
_CYCLE_MS = CYCLE_EPOCHS * EPOCH_MS


def snapshot(at):
    epoch = max(0, int(at)) // EPOCH_MS
    state, label, percent = _PHASES[epoch % CYCLE_EPOCHS]
    return dict(epoch=epoch, state=state, label=label, demand_factor=percent / 100,
                starts_at=epoch * EPOCH_MS / 1000, ends_at=(epoch + 1) * EPOCH_MS / 1000)


# F#263/#264 (08/10, "mở 5 tiệm quần áo, không độn giá mà suy thoái cả 5"): the phase is one calendar for the whole
# town, every counter of every player at once (not the price, not how many counters you own). These say so on screen.
DAY_PERCENT = round(_CYCLE_WORK / _CYCLE_MS)          # the day's average demand, percent of a normal hour
DOWN_MINUTES = sum(EPOCH_MS for p in _PHASES if p[0] == 'downturn') // 60000   # downturn minutes in a day


def outlook(at, runs=4):
    """The market from `at`: the current run of one phase (same state and demand, epochs merged) and the next ones,
    [{state, label, demand_factor, starts_at, ends_at}] (seconds). Read-only, from the fixed calendar: a client whose
    state is a little old can still pick the run of its own clock."""
    epoch = max(0, int(at)) // EPOCH_MS
    out = []
    while len(out) < runs:
        state, label, percent = _PHASES[epoch % CYCLE_EPOCHS]
        start = epoch
        while _PHASES[(epoch + 1) % CYCLE_EPOCHS][::2] == (state, percent) and epoch + 1 - start < CYCLE_EPOCHS:
            epoch += 1
        out.append(dict(state=state, label=label, demand_factor=percent / 100,
                        starts_at=start * EPOCH_MS / 1000, ends_at=(epoch + 1) * EPOCH_MS / 1000))
        epoch += 1
    return out


def demand_clock(at):
    """Exact integrated demand in percent-milliseconds, including full days."""
    cycles, tail = divmod(max(0, int(at)), _CYCLE_MS)
    epoch, offset = divmod(tail, EPOCH_MS)
    return cycles * _CYCLE_WORK + _PREFIX[epoch] + offset * _PHASES[epoch][2]


def advance(at, baseline_ms):
    """Invert the market calendar in O(log 48), even after centuries offline.

    Future NPC arrivals include each intervening epoch's actual demand. No
    polling, epoch reset, or floating-point rescaling can change that deadline.
    """
    target = demand_clock(at) + max(1, baseline_ms) * 100
    cycles, tail = divmod(target, _CYCLE_WORK)
    epoch = bisect.bisect_right(_PREFIX, tail) - 1
    percent = _PHASES[epoch][2]
    offset = (tail - _PREFIX[epoch] + percent - 1) // percent
    return cycles * _CYCLE_MS + epoch * EPOCH_MS + offset


def migrate(st):
    b = st['business']
    changed = False
    for k in ('income_tax', 'environment', 'protection'):
        if k not in b['expenses']:
            b['expenses'][k] = 0
            changed = True
    for k in ('environment', 'protection'):
        if k not in b['carry']:
            b['carry'][k] = 0
            changed = True
    defaults = dict(income_tax=dict(loss=b.get('profit_boost', {}).get('costs', 0), carry=0),
                    protection=dict(level='none'), market_epoch=b['cursor'] // EPOCH_MS)
    if b['paused'] and 'closed_at' not in b:
        defaults['closed_at'] = b['cursor']
    for k, value in defaults.items():
        if k not in b:
            b[k] = value
            changed = True
    return changed


def enter_epoch(st, at):
    # Arrival deadlines already integrate all epochs via advance().
    st['business']['market_epoch'] = max(0, int(at)) // EPOCH_MS
