"""💤 Cold careers keep a slim record (perf 23/10: "lag lắm, cái nào cũ cũ giảm tải được xóa được thì bỏ bớt";
owner after review: "đừng để ảnh hưởng và làm chậm").

The biggest saves (6–12 MB) are ~70 career records, each with its full lists: the cash book (≈250 rows), the
journal (100 rows)... Every command parses, validates (each career a staff order moved), serializes and writes all
of it. Most of those careers have not been played for a long time: their staff work, but the player is elsewhere.
Such a career is COLD: it is not the current career and none of the last COLD_DAYS days of the journey
(journey.days, one row per closed day) was spent there. A save with fewer recorded days than that has no cold career.

Player commands never compact (no extra work in them, ever). The night job scripts/slim_saves.py (04:00–05:00, big
saves only) sends the internal command ACTION through the normal Store path: the same transaction writes the cut
rows to the archive (game/archive.py, never dropped), the revision check skips a save that moved, and the command
settles nothing (no staff work, no fees: only these lists change). A cold career then keeps:
* cash book: the newest LEDGER_KEEP rows (the Sổ dòng tiền shows 24), every row of the day its lãi/lỗ card shows
  and after (today while the shift is open, else the day just closed) and every row of a job still on the desk; the
  rows before them go to the archive, their sum into the opening balance (opening_balance + rows == wallet, as
  operations.trim_ledger). The lãi/lỗ chart's days among them (7 days back from the career's day) leave a per-day,
  per-category total in ops.finance.day_sums (v4/pnl.js adds it: the same chart);
* journal: the newest JOURNAL_KEEP rows (the Sổ tay shows 80), and today's rows while the shift is open
  (inventory._turn0 reads the "Mở ca" row); "Xem cũ hơn" pages the rest, as before;
* life histories nothing shows (the played trò nhỏ, the price changes): the newest LIFE_KEEP of each.
What was moved is counted in c["ext"]["slim"] (the view's c.slim: "Xem cũ hơn" stays offered on the shortened
lists, the cash book's header counts the moved rows too). Photos (the Kỷ niệm sheet shows all six on open), reviews
(ratings and boards read them), jobs (slot numbers), histories whose length picks what comes next and everything
else stay as they are. A career played again simply grows its lists back.
"""
from __future__ import annotations

from . import archive as ar

ACTION = 'slim_compact'   # internal only (engine._apply_action): scripts/slim_saves.py
COLD_DAYS = 10        # closed days (journey.days) without this career: cold
PER_COMMAND = 24      # careers compacted per night command at most (its row lock stays short)
MAX_PER_COMMAND = 80
LEDGER_KEEP = 30      # cash-book rows a cold career keeps at least (the Sổ dòng tiền lists the newest 24)
JOURNAL_KEEP = 80     # journal rows a cold career keeps at least (the Sổ tay lists the newest 80; the save keeps 100)
JOURNAL_SLACK = 10
CHART_DAYS = 7        # the lãi/lỗ chart: 7 days ending at the summary day (the career's day or the day before)
SLACK = 20            # a list is compacted again only once it is this much over its keep
SUMS_DAYS = CHART_DAYS + 1   # day_sums keeps the days day-CHART_DAYS .. day
LIFE_KEEP = 10        # rows of each life history (experiences.py) a cold career keeps
LIFE = (('activity_history', 'life.activities'), ('price_history', 'life.prices'))   # goals_history keeps 3 already
COUNTS = ('ledger', 'journal', 'life')


def cold(s: dict) -> list:
    """Ids of the cold careers of this save (see the module doc), in save order."""
    j = s.get('journey') if type(s) is dict else None
    days = j.get('days') if isinstance(j, dict) else None
    careers = s.get('careers') if type(s) is dict else None
    if not isinstance(days, list) or len(days) < COLD_DAYS or type(careers) is not dict:
        return []
    warm = {r.get('c') for r in days[-COLD_DAYS:] if isinstance(r, dict)}
    warm.add(s.get('current'))
    return [cid for cid, c in careers.items() if cid not in warm and type(c) is dict and c.get('started') is True]


def _summary_day(c: dict) -> int:
    """The day the career's lãi/lỗ card shows (v4/pnl.js pnlCard): today while the shift is open, else the day just
    closed. Its cash-book rows (and every later one) always stay."""
    return c['day'] if c.get('open') else c['day'] - 1


def _prefix(rows: list, keep: int, first_day: int, refs=frozenset()) -> int:
    """How many rows from the start may go: never the newest `keep`, never from the first row of a day >= first_day
    or whose ref is in `refs` on (only a prefix is cut: the archive stays in order, oldest first)."""
    limit = len(rows) - keep
    cut = 0
    while cut < limit:
        r = rows[cut]
        if type(r) is not dict or type(r.get('day')) is not int or r['day'] >= first_day or (refs and r.get('ref') in refs):
            break
        cut += 1
    return max(0, cut)


def needs(c: dict) -> bool:
    """This cold career has something to compact (cheap: lengths only)."""
    f = ((c.get('ops') or {}).get('finance') or {}) if isinstance(c.get('ops'), dict) else {}
    ledger = f.get('ledger') if isinstance(f, dict) else None
    return ((isinstance(ledger, list) and len(ledger) > LEDGER_KEEP + SLACK)
            or (isinstance(c.get('journal'), list) and len(c['journal']) > JOURNAL_KEEP + JOURNAL_SLACK)
            or (isinstance(c.get('life'), dict) and any(isinstance(c['life'].get(k), list) and len(c['life'][k]) > LIFE_KEEP + SLACK for k, _ in LIFE)))


def _count(c: dict, kind: str, n: int) -> None:
    ext = c.get('ext')
    if not n or not isinstance(ext, dict):
        return
    mark = ext.get('slim')
    if not isinstance(mark, dict):
        mark = ext['slim'] = {}
    mark[kind] = min(10**9, (mark.get(kind) if type(mark.get(kind)) is int else 0) + n)


def day_sums(f: dict, rows: list, day: int) -> None:
    """Add the chart days' totals of `rows` (cash-book rows leaving the save) to f['day_sums']:
    {"<day>": {"<category>": [money in, money out, rows]}}; days the chart can no longer show are dropped."""
    low = day - CHART_DAYS
    sums = f.get('day_sums') if isinstance(f.get('day_sums'), dict) else {}
    for r in rows:
        if r['day'] < low:
            continue
        cat = r.get('category') if isinstance(r.get('category'), str) else 'other_cost'
        row = sums.setdefault(str(r['day']), {}).setdefault(cat[:60], [0, 0, 0])
        a = r['amount']
        if a >= 0:
            row[0] = min(10**12, row[0] + a)
        else:
            row[1] = max(-10**12, row[1] + a)
        row[2] = min(10**9, row[2] + 1)
    sums = {d: v for d, v in sums.items() if d.isdigit() and low <= int(d) <= day}
    if sums:
        f['day_sums'] = sums
    else:
        f.pop('day_sums', None)


def ledger(c: dict, cid: str) -> int:
    """Cash-book rows of a cold career moved to the archive (see the module doc)."""
    f = (c.get('ops') or {}).get('finance')
    if (not isinstance(f, dict) or not isinstance(f.get('ledger'), list) or type(f.get('opening_balance')) is not int
            or type(c.get('day')) is not int):
        return 0
    rows = f['ledger']
    refs = frozenset(t['id'] for t in c.get('tasks') or () if isinstance(t, dict) and isinstance(t.get('id'), str))
    cut = _prefix(rows, LEDGER_KEEP, _summary_day(c), refs)
    gone = rows[:cut]
    if cut <= 0 or not all(type(x.get('amount')) is int for x in gone):   # (rows that would not validate stay)
        return 0
    ar.record(gone, 'ledger', cid)
    f['opening_balance'] += sum(x['amount'] for x in gone)
    f['ledger'] = rows[cut:]
    day_sums(f, gone, c['day'])
    return cut


def journal(c: dict, cid: str) -> int:
    rows = c.get('journal')
    if not isinstance(rows, list) or type(c.get('day')) is not int:
        return 0
    cut = _prefix(rows, JOURNAL_KEEP, c['day'] if c.get('open') else c['day'] + 1)
    if cut <= 0:
        return 0
    ar.record(rows[:cut], 'journal', cid)
    c['journal'] = rows[cut:]
    return cut


def life(c: dict, cid: str) -> int:
    x = c.get('life')
    if not isinstance(x, dict):
        return 0
    n = 0
    for key, kind in LIFE:
        rows = x.get(key)
        if isinstance(rows, list) and len(rows) > LIFE_KEEP:
            n += len(rows) - LIFE_KEEP
            x[key] = ar.last(rows, LIFE_KEEP, kind, cid)
    return n


def plan(s: dict) -> list:
    """Ids of the cold careers that have something to compact (lengths only: the night job's dry run)."""
    careers = s.get('careers') if type(s) is dict else None
    return [cid for cid in cold(s) if needs(careers[cid])]


def compact(s: dict, limit: int = PER_COMMAND) -> list:
    """Compact up to `limit` cold careers that need it; their ids. Nothing happens outside a command whose cut rows
    are written to the archive (archive.collecting()): a copy, a preview, a test without a collector."""
    if not ar.collecting():
        return []
    done = []
    careers = s['careers']
    for cid in cold(s):
        if len(done) >= limit:
            break
        c = careers[cid]
        if not needs(c):
            continue
        moved = 0
        for kind, fn in (('ledger', ledger), ('journal', journal), ('life', life)):
            n = fn(c, cid)
            _count(c, kind, n)
            moved += n
        if moved:
            done.append(cid)
    return done


def apply(s: dict, p: dict) -> dict:
    """The internal command ACTION: {"careers": how many at most}. Nothing to do: refused (nothing is written)."""
    from .engine import GameError
    n = p.get('careers', PER_COMMAND)
    limit = n if type(n) is int and 1 <= n <= MAX_PER_COMMAND else PER_COMMAND
    done = compact(s, limit)
    if not done:
        raise GameError('Bản lưu đã gọn.', 'slim_nothing')
    return dict(message='Đã cất bớt sổ cũ của các nghề lâu không ghé.', slim=dict(careers=done, left=len(plan(s))))


def view(c: dict) -> dict | None:
    """The focus view's c.slim: what compaction moved to the archive ({kind: rows}), None when nothing."""
    mark = (c.get('ext') or {}).get('slim') if isinstance(c.get('ext'), dict) else None
    if not isinstance(mark, dict):
        return None
    return {k: v for k, v in mark.items() if k in COUNTS and type(v) is int and v > 0} or None


def validate(c: dict) -> None:
    """c["ext"]["slim"] and ops.finance.day_sums, both optional (a career never compacted has neither)."""
    from .engine import need, integer
    mark = (c.get('ext') or {}).get('slim')
    if mark is not None:
        need(isinstance(mark, dict) and set(mark) <= set(COUNTS), 'Dữ liệu sổ gọn không hợp lệ.')
        for v in mark.values():
            integer(v, 0, 10**9)
    sums = ((c.get('ops') or {}).get('finance') or {}).get('day_sums')
    if sums is not None:
        need(isinstance(sums, dict) and len(sums) <= SUMS_DAYS, 'Tổng thu chi theo ngày không hợp lệ.')
        for d, cats in sums.items():
            need(isinstance(d, str) and d.isdigit() and len(d) <= 9 and isinstance(cats, dict) and len(cats) <= 80, 'Tổng thu chi theo ngày không hợp lệ.')
            for cat, row in cats.items():
                need(isinstance(cat, str) and 1 <= len(cat) <= 60 and isinstance(row, list) and len(row) == 3, 'Tổng thu chi theo ngày không hợp lệ.')
                integer(row[0], 0, 10**12)
                integer(row[1], -10**12, 0)
                integer(row[2], 0, 10**9)
