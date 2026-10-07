#!/usr/bin/env python3
"""Rollback helper: make saves written by a newer release readable by an older one that lacks some careers.

An older build refuses a save whose `careers` holds a career it does not know ("Bản lưu cần đủ các nghề."), so a
code rollback past a release that added careers (1.9.11: `zpop`, the album shop) needs the saves stripped first.
Nothing is thrown away: every piece taken out goes to an archive (JSON lines, one per save) that `restore` puts
back after rolling forward again. Money never moves: a career's own fund stays inside its archived block (not
spendable until it is restored), and the wallet, the bank and every other career are untouched.

What is taken out, per career id CID: exactly what an older build validates against its own careers, titles and
people (read from rel-1.9.10's validators); anything else that merely mentions the id stays (journey.lux has a
sponsorship kind 'zpop' that is not the career, for one).
  * careers.CID                       the career's whole record (its fund, stock, staff, days, tasks)
  * current == CID                    None (the player is in town)
  * journey.unlocked, journey.board.touched: the CID entry; journey.paused.CID, journey.promo.CID
  * journey.needs.seen                None when it is [CID, day, minutes] (the last shift's clock)
  * journey.titles.c_CID              the career title; also out of journey.equipped / journey.worn / the news items
  * journey.history rows at CID       amount and label kept, `career` cleared
  * journey.study.career == CID       cleared (the course itself stays)
  * journey.days rows of CID, closeness people / snap / log / inbox of the career's own people (ids 'CID_...'),
    stories.arcs.CID, stories.queue beats of CID
  * check                             the build stamp (career digests): the older build then validates in full
Restore puts back every one of these except rows of rolling logs (journey.days, the news, closeness log and inbox,
the stories queue, the history rows' place): those stay in the archive, since the log moved on meanwhile.

Usage
  # files: IN is one save, {name: save} or [save, ...]; OUT has the same shape
  python scripts/strip_new_careers.py strip --careers zpop IN.json OUT.json --archive removed.jsonl
  python scripts/strip_new_careers.py restore --archive removed.jsonl IN.json OUT.json

  # PostgreSQL sessions (DATABASE_URL); without --write it only counts. Each changed save gets revision + 1 and is
  # written only if nobody saved it meanwhile (WHERE revision = the one read). The archive line is flushed to disk
  # before the row is updated.
  python scripts/strip_new_careers.py strip --careers zpop --db --archive removed.jsonl [--write]
  python scripts/strip_new_careers.py restore --db --archive removed.jsonl [--write]

Restoring puts a career back only when the save has no record for it, or the record is still the fresh one a newer
build adds on load (no day worked: day 1, never opened); otherwise that save is reported and left as it is.

Proof (1.9.11 → 1.9.10): saves of a story player, a player mid-shift at the album shop and one who worked days there
then moved on, with pets and Mua sắm items, all pass rel-1.9.10's migrate_state + validate_state + public_state and
play a day once stripped; restored on 1.9.11, they validate and the career record is byte for byte the archived one.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys

# Lists outside the careers that name career ids and that older validators check against their own CAREERS.
ID_LISTS = (('journey', 'unlocked'), ('journey', 'board', 'touched'))
# Rolling logs: rows naming the career are archived; restore does not put them back (the log moved on meanwhile).
LOGS = 'days', 'news', 'closeness.log', 'closeness.inbox', 'stories.queue'


def _at(s: dict, path: tuple):
    o = s
    for k in path:
        if not isinstance(o, dict):
            return None
        o = o.get(k)
    return o


def _is_save(o) -> bool:
    return isinstance(o, dict) and isinstance(o.get('careers'), dict)


def _npc(cid: str, pid) -> bool:
    """One of the career's own people (closeness ids 'zpop_npc_01')."""
    return isinstance(pid, str) and pid.startswith(cid + '_')


def strip(state: dict, careers: list[str]) -> tuple[dict, dict]:
    """(stripped copy, removed). `removed` is {} when the save names none of `careers`. Only the places an older
    build validates against its own careers, titles and people are touched (journey.lux's own 'zpop' sponsorship
    kind, for one, is not a career and stays)."""
    s = copy.deepcopy(state)
    removed: dict = {}
    j = s.get('journey') if isinstance(s.get('journey'), dict) else {}
    for cid in careers:
        r: dict = {}
        title = 'c_' + cid
        if cid in s['careers']:
            r['career'] = s['careers'].pop(cid)
        if s.get('current') == cid:
            r['current'] = cid
            s['current'] = None
        for path in ID_LISTS:
            lst = _at(s, path)
            if isinstance(lst, list) and cid in lst:
                r.setdefault('lists', {})['.'.join(path)] = [i for i, v in enumerate(lst) if v == cid]
                lst[:] = [v for v in lst if v != cid]
        nd = j.get('needs')   # 🍚 seen = [career, day, minutes]: the last shift's clock
        if isinstance(nd, dict) and isinstance(nd.get('seen'), list) and nd['seen'][:1] == [cid]:
            r['seen'] = nd['seen']
            nd['seen'] = None
        for key in ('paused', 'promo'):   # {career: ...}
            d = j.get(key)
            if isinstance(d, dict) and cid in d:
                r.setdefault('keys', {})[key] = d.pop(cid)
        # 🏷️ the career's title: owned, worn, equipped, in the news of titles
        if isinstance(j.get('titles'), dict) and title in j['titles']:
            r['title'] = j['titles'].pop(title)
        if j.get('equipped') == title:
            r['equipped'] = title
            j['equipped'] = None
        if isinstance(j.get('worn'), list) and title in j['worn']:
            r['worn'] = j['worn'].index(title)
            j['worn'] = [x for x in j['worn'] if x != title]
        for i, n in enumerate(j.get('news') or ()):
            if isinstance(n, dict) and isinstance(n.get('items'), list) and title in n['items']:
                r.setdefault('news', []).append([i, n['id'] if 'id' in n else None, list(n['items'])])
                n['items'] = [x for x in n['items'] if x != title]
        # 💵 wallet rows paid at the career keep their amount and label; only the place is cleared
        for i, row in enumerate(j.get('history') or ()):
            if isinstance(row, dict) and row.get('career') == cid:
                r.setdefault('history', []).append(i)
                row['career'] = None
        if isinstance(j.get('study'), dict) and j['study'].get('career') == cid:   # a course paid at the workplace
            r['study'] = cid
            j['study']['career'] = None
        days = j.get('days')
        if isinstance(days, list) and any(isinstance(x, dict) and x.get('c') == cid for x in days):
            r['days'] = [x for x in days if isinstance(x, dict) and x.get('c') == cid]
            days[:] = [x for x in days if not (isinstance(x, dict) and x.get('c') == cid)]
        # 🤝 closeness with the career's own people
        cl = j.get('closeness')
        if isinstance(cl, dict):
            ppl = cl.get('people')
            if isinstance(ppl, dict) and any(_npc(cid, k) for k in ppl):
                r['people'] = {k: ppl.pop(k) for k in [k for k in ppl if _npc(cid, k)]}
            snap = cl.get('snap')
            if isinstance(snap, dict) and any(_npc(cid, k) for k in snap):
                r['snap'] = {k: snap.pop(k) for k in [k for k in snap if _npc(cid, k)]}
            for key in ('log', 'inbox'):
                lst = cl.get(key)
                if isinstance(lst, list) and any(isinstance(x, dict) and _npc(cid, x.get('who')) for x in lst):
                    r['closeness.' + key] = [x for x in lst if isinstance(x, dict) and _npc(cid, x.get('who'))]
                    lst[:] = [x for x in lst if not (isinstance(x, dict) and _npc(cid, x.get('who')))]
        # 📖 the career's story arc and its queued beats
        st = s.get('stories')
        if isinstance(st, dict):
            if isinstance(st.get('arcs'), dict) and cid in st['arcs']:
                r['arc'] = st['arcs'].pop(cid)
            q = st.get('queue')
            if isinstance(q, list) and any(isinstance(x, dict) and x.get('career') == cid for x in q):
                r['stories.queue'] = [x for x in q if isinstance(x, dict) and x.get('career') == cid]
                q[:] = [x for x in q if not (isinstance(x, dict) and x.get('career') == cid)]
        if r:
            removed[cid] = r
    if removed:
        s.pop('check', None)   # the build stamp: the older build validates the whole save
    return s, removed


def _fresh(c: dict) -> bool:
    """The record a newer build adds on load for a career never worked."""
    return isinstance(c, dict) and int(c.get('day') or 1) <= 1 and not c.get('started') and not c.get('open')


def restore(state: dict, removed: dict) -> tuple[dict, list[str]]:
    """(restored copy, problems). Puts back what strip() took, career by career; rows of rolling logs stay in the
    archive (see LOGS)."""
    s = copy.deepcopy(state)
    problems = []
    j = s.get('journey') if isinstance(s.get('journey'), dict) else {}
    for cid, r in removed.items():
        title = 'c_' + cid
        if 'career' in r:
            have = s['careers'].get(cid)
            if have is not None and not _fresh(have):
                problems.append(f'{cid}: the save already has a worked record, left as it is')
                continue
            s['careers'][cid] = r['career']
        if r.get('current') == cid and s.get('current') is None:
            s['current'] = cid
        for dotted, idx in (r.get('lists') or {}).items():
            lst = _at(s, tuple(dotted.split('.')))
            if isinstance(lst, list) and cid not in lst:
                for i in idx:
                    lst.insert(min(i, len(lst)), cid)
        for key, v in (r.get('keys') or {}).items():
            if isinstance(j.get(key), dict):
                j[key].setdefault(cid, v)
            elif key == 'promo':
                j[key] = {cid: v}
        if 'title' in r and isinstance(j.get('titles'), dict):
            j['titles'].setdefault(title, r['title'])
        if r.get('equipped') == title and j.get('equipped') is None:
            j['equipped'] = title
        if 'worn' in r and isinstance(j.get('worn'), list) and title not in j['worn']:
            j['worn'].insert(min(r['worn'], len(j['worn'])), title)
        nd = j.get('needs')
        if r.get('seen') and isinstance(nd, dict) and nd.get('seen') is None:
            nd['seen'] = r['seen']
        if r.get('study') == cid and isinstance(j.get('study'), dict) and j['study'].get('career') is None:
            j['study']['career'] = cid
        cl = j.get('closeness')
        if isinstance(cl, dict):
            for key in ('people', 'snap'):
                if r.get(key) and isinstance(cl.get(key), dict):
                    for k, v in r[key].items():
                        cl[key].setdefault(k, v)
        st = s.get('stories')
        if 'arc' in r and isinstance(st, dict) and isinstance(st.get('arcs'), dict):
            st['arcs'].setdefault(cid, r['arc'])
    s.pop('check', None)
    return s, problems


# ---------------------------------------------------------------- files

def _each(doc):
    if _is_save(doc):
        yield None, doc
    elif isinstance(doc, list):
        yield from enumerate(doc)
    elif isinstance(doc, dict):
        yield from doc.items()
    else:
        raise SystemExit('IN must be a save, {name: save} or [save, ...]')


def _put(doc, key, value):
    if key is None:
        return value
    doc[key] = value
    return doc


def files(a) -> int:
    doc = json.load(open(a.inp, encoding='utf-8'))
    out = copy.deepcopy(doc)
    n = 0
    if a.cmd == 'strip':
        with open(a.archive, 'a', encoding='utf-8') as arc:
            for key, s in list(_each(doc)):
                new, removed = strip(s, a.careers)
                if removed:
                    arc.write(json.dumps(dict(key=key, removed=removed), ensure_ascii=False) + '\n')
                    n += 1
                out = _put(out, key, new)
    else:
        lines = [json.loads(x) for x in open(a.archive, encoding='utf-8') if x.strip()]
        by = {json.dumps(x['key']): x['removed'] for x in lines}
        for key, s in list(_each(doc)):
            removed = by.get(json.dumps(key))
            if not removed:
                continue
            new, problems = restore(s, removed)
            for p in problems:
                print(f'{key}: {p}', file=sys.stderr)
            out = _put(out, key, new)
            n += 1
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{a.cmd}: {n} save(s) changed -> {a.out}')
    return 0


# ---------------------------------------------------------------- PostgreSQL sessions

def db(a) -> int:
    import psycopg
    url = os.environ.get('DATABASE_URL') or ''
    if not url:
        raise SystemExit('DATABASE_URL is not set')
    dumps = lambda v: json.dumps(v, ensure_ascii=False, allow_nan=False, separators=(',', ':'))   # game/storage.py
    changed = skipped = 0
    with psycopg.connect(url, application_name='mnl-strip-careers') as conn:
        if a.cmd == 'strip':
            like = [f'%"{cid}"%' for cid in a.careers]
            with conn.cursor() as cur:
                cur.execute('SELECT sid FROM sessions WHERE ' + ' OR '.join(['state LIKE %s'] * len(like)), like)
                sids = [r[0] for r in cur.fetchall()]
            arc = open(a.archive, 'a', encoding='utf-8') if a.write else None
            for sid in sids:
                with conn.cursor() as cur:
                    cur.execute('SELECT revision, state FROM sessions WHERE sid=%s', (sid,))
                    row = cur.fetchone()
                if not row:
                    continue
                rev, text = row
                new, removed = strip(json.loads(text), a.careers)
                if not removed:
                    continue
                changed += 1
                if not a.write:
                    continue
                arc.write(json.dumps(dict(sid=sid, revision=rev, removed=removed), ensure_ascii=False) + '\n')
                arc.flush()
                os.fsync(arc.fileno())
                with conn.cursor() as cur:
                    cur.execute('UPDATE sessions SET state=%s, revision=revision+1, updated_at=CURRENT_TIMESTAMP '
                                'WHERE sid=%s AND revision=%s', (dumps(new), sid, rev))
                    if cur.rowcount != 1:
                        skipped += 1
                        print(f'{sid}: saved meanwhile, left as it is (run again)', file=sys.stderr)
                conn.commit()
            if arc:
                arc.close()
        else:
            lines = [json.loads(x) for x in open(a.archive, encoding='utf-8') if x.strip()]
            for x in lines:
                sid = x['sid']
                with conn.cursor() as cur:
                    cur.execute('SELECT revision, state FROM sessions WHERE sid=%s', (sid,))
                    row = cur.fetchone()
                if not row:
                    print(f'{sid}: no such save', file=sys.stderr)
                    continue
                rev, text = row
                cur_state = json.loads(text)
                new, problems = restore(cur_state, x['removed'])
                for p in problems:
                    print(f'{sid}: {p}', file=sys.stderr)
                if dict(new, check=None) == dict(cur_state, check=None):
                    continue   # already back (or left as it is)
                changed += 1
                if not a.write:
                    continue
                with conn.cursor() as cur:
                    cur.execute('UPDATE sessions SET state=%s, revision=revision+1, updated_at=CURRENT_TIMESTAMP '
                                'WHERE sid=%s AND revision=%s', (dumps(new), sid, rev))
                    if cur.rowcount != 1:
                        skipped += 1
                        print(f'{sid}: saved meanwhile, left as it is (run again)', file=sys.stderr)
                conn.commit()
    verb = 'changed' if a.write else 'would change (dry run, add --write)'
    print(f'{a.cmd}: {changed - skipped} save(s) {verb}' + (f', {skipped} skipped' if skipped else ''))
    return 1 if skipped else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('cmd', choices=('strip', 'restore'))
    p.add_argument('--careers', default='zpop', help='comma-separated career ids (strip), default zpop')
    p.add_argument('--archive', required=True, help='JSON lines: what strip took out, what restore puts back')
    p.add_argument('--db', action='store_true', help='PostgreSQL sessions at DATABASE_URL instead of files')
    p.add_argument('--write', action='store_true', help='with --db: really update the rows')
    p.add_argument('inp', nargs='?')
    p.add_argument('out', nargs='?')
    a = p.parse_args(argv)
    a.careers = [c.strip() for c in a.careers.split(',') if c.strip()]
    if a.db:
        return db(a)
    if not a.inp or not a.out:
        p.error('IN and OUT are needed without --db')
    return files(a)


if __name__ == '__main__':
    sys.exit(main())
