#!/usr/bin/env python3
"""Pre-deploy gate: tasks made by the live release must still validate after the new one ships.

A save keeps every generated task. On each command the server regenerates the task's
"original" from (career, day, slot, created_turn) with the NEW code and compares the fixed
facts with what the save holds (engine.validate_career, experiences.validate_task and each
career's validate_task, desk.validate_task, procedures.validate, tour_trip.validate,
teach_lesson.validate). If a release changes what generation produces, every player with an
open task of that kind is stuck on "Dữ kiện gốc của nhiệm vụ không hợp lệ" (0.9.6: clothing
lines gained 'ask'/'told').

    python scripts/check_task_compat.py OLD_TREE NEW_TREE [--days 40] [--careers a,b] [--show 20]

OLD_TREE / NEW_TREE are source checkouts (e.g. `git worktree add /tmp/live rel096`, or
`git archive rel096 | tar -x -C /tmp/live`). Each tree is imported in its own subprocess
(`python -I`, sys.path = that tree only), never in this process.

For every career, day 1..DAYS, slot 0..11 and classic False/True (the desk flag the
validator passes: pre-desk counter tasks, mother_baby before gift generation) it compares
engine.make_task of both trees field by field, recursively. Also compared, because the
validators regenerate them on their own:
  - tour_trip.roll(..., legacy=True) (tour trips made before the care loop),
  - the situation script ids (a saved situation must still find its script).

Allowed difference: a key listed in the NEW tree's engine.LATE_TASK_KEYS that the old output
simply does not have, inside a field the validators compare with that tolerance (engine's
task fields, the plugin's FIXED, teacher/tour_guide fixed fields). Anything else fails.

Exit code: 0 compatible, 1 differences found, 2 a tree could not be loaded.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SLOTS = 12
# Fields engine.validate_career compares with _without_late_keys (keep in sync with game/engine.py).
ENGINE_TOLERANT = ('npc', 'title', 'opening', 'kind', 'needs', 'variant', 'solution', 'value', 'evidence')
# experiences.validate_task: the non-plugin careers' fixed fields (also compared with the tolerance).
LIFE_TOLERANT = {'teacher': ('lesson', 'students'), 'tour_guide': ('required', 'budget', 'limit', 'visitors', 'weather')}


# ------------------------------------------------------------------ worker (runs inside one tree)
def _tag(x):
    """JSON-safe copy that keeps tuple vs list apart (a stored task is lists only)."""
    if isinstance(x, dict):
        return {str(k): _tag(v) for k, v in x.items()}
    if isinstance(x, tuple):
        return {'__tuple__': [_tag(v) for v in x]}
    if isinstance(x, list):
        return [_tag(v) for v in x]
    return x


def worker(tree: str, career: str, days: int, out: str) -> None:
    sys.path.insert(0, tree)
    os.chdir(tree)
    from game.content import make_task, CAREERS
    from game import engine
    rows = {}
    if career == '__meta__':
        from game.careers import PLUGINS
        from game import situations
        meta = dict(careers=list(CAREERS), late=sorted(getattr(engine, 'LATE_TASK_KEYS', ())),
                    fixed={c: list(getattr(PLUGINS[c], 'FIXED', ())) for c in CAREERS if c in PLUGINS},
                    scripts={c: sorted(x['id'] for x in situations.scripts(c)) for c in CAREERS})
        Path(out).write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
        return
    for day in range(1, days + 1):
        for slot in range(SLOTS):
            serial = (day * SLOTS + slot) * 7   # created_turn: any value, the same on both sides
            for classic in (False, True):
                key = f'{day}/{slot}/{"classic" if classic else "desk"}'
                try:
                    rows[key] = _tag(make_task(career, day, slot, serial, classic))
                except Exception as e:  # noqa: BLE001 - a crash is a difference too
                    rows[key] = {'__error__': f'{type(e).__name__}: {e}'}
    if career == 'tour_guide':
        from game import tour_trip
        from game.extra_content import WEATHERS
        for day in range(1, days + 1):
            for slot in range(SLOTS):
                for w in WEATHERS:
                    try:
                        rows[f'{day}/{slot}/legacy-trip/{w["id"]}'] = _tag(tour_trip.roll(day, slot, w['id'], True))
                    except Exception as e:  # noqa: BLE001
                        rows[f'{day}/{slot}/legacy-trip/{w["id"]}'] = {'__error__': f'{type(e).__name__}: {e}'}
    Path(out).write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')


# ------------------------------------------------------------------ parent
def run_worker(tree: Path, career: str, days: int, tmp: Path) -> dict:
    out = tmp / f'{tree.name}-{abs(hash(str(tree)))}-{career}.json'
    env = {k: v for k, v in os.environ.items() if not k.startswith('PYTHON')}
    env['MNL_TASK_COMPAT'] = '1'
    code = ('import sys; sys.path.insert(0, sys.argv[1]); '
            'import importlib.util as u; s=u.spec_from_file_location("gate", sys.argv[2]); m=u.module_from_spec(s); s.loader.exec_module(m); '
            'm.worker(sys.argv[3], sys.argv[4], int(sys.argv[5]), sys.argv[6])')
    # The worker code comes from this file; the game code comes only from `tree` (-I: no cwd, no PYTHONPATH).
    p = subprocess.run([sys.executable, '-I', '-c', code, str(tree), __file__, str(tree), career, str(days), str(out)],
                       cwd=str(tree), env=env, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f'{tree} {career}: worker failed\n{p.stderr[-3000:]}')
    data = json.loads(out.read_text(encoding='utf-8'))
    out.unlink()
    return data


def diff(old, new, path: str, late: frozenset, tolerant: bool, out: list) -> None:
    """Append (path, old, new) for every difference; `tolerant` allows missing LATE keys in old."""
    if isinstance(old, dict) and isinstance(new, dict):
        for k in sorted(set(old) | set(new)):
            p = f'{path}.{k}'
            if k not in new:
                out.append((p, old[k], '<absent>'))
            elif k not in old:
                if not (tolerant and k in late):
                    out.append((p, '<absent>', new[k]))
            else:
                diff(old[k], new[k], p, late, tolerant, out)
        return
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            out.append((f'{path}[len]', len(old), len(new)))
        for i, (a, b) in enumerate(zip(old, new)):
            diff(a, b, f'{path}[{i}]', late, tolerant, out)
        return
    if type(old) is not type(new) and not ({type(old), type(new)} <= {int, float}) or old != new:
        out.append((path, old, new))


def compare_career(career: str, old: dict, new: dict, late: frozenset, fixed: list) -> list:
    tolerant_roots = set(ENGINE_TOLERANT) | set(fixed) | set(LIFE_TOLERANT.get(career, ()))
    found = []
    for key in sorted(set(old) | set(new), key=lambda k: [int(x) if x.isdigit() else x for x in k.split('/')]):
        where = f'{career} {key}'
        if key not in new:
            found.append((where, '<generated>', '<absent>'))
            continue
        if key not in old:
            continue   # a new kind of row (e.g. legacy trips of a new weather): nothing old to break
        a, b = old[key], new[key]
        if isinstance(a, dict) and isinstance(b, dict) and '__error__' not in a and '__error__' not in b:
            for k in sorted(set(a) | set(b)):
                if k not in b:
                    found.append((f'{where} .{k}', a[k], '<absent>'))
                elif k not in a:
                    found.append((f'{where} .{k}', '<absent>', b[k]))
                else:
                    diff(a[k], b[k], f'{where} .{k}', late, k in tolerant_roots and '/legacy-trip/' not in key, found)
        elif a != b:
            found.append((where, a, b))
    return found


def short(x, n: int = 160) -> str:
    s = json.dumps(x, ensure_ascii=False) if not isinstance(x, str) else x
    return s if len(s) <= n else s[:n - 1] + '…'


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('old', type=Path, help='source tree of the live release')
    ap.add_argument('new', type=Path, help='source tree about to ship')
    ap.add_argument('--days', type=int, default=40)
    ap.add_argument('--careers', default='', help='comma list (default: every career of the old tree)')
    ap.add_argument('--show', type=int, default=25, help='differences printed per career')
    ap.add_argument('--jobs', type=int, default=min(8, os.cpu_count() or 2))
    a = ap.parse_args(argv)
    old, new = a.old.resolve(), a.new.resolve()
    for t in (old, new):
        if not (t / 'game' / 'engine.py').exists():
            print(f'not a source tree: {t}', file=sys.stderr)
            return 2
    with tempfile.TemporaryDirectory(prefix='task-compat-') as d:
        tmp = Path(d)
        try:
            m_old, m_new = run_worker(old, '__meta__', a.days, tmp), run_worker(new, '__meta__', a.days, tmp)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return 2
        late = frozenset(m_new['late'])
        careers = [c for c in a.careers.split(',') if c] or m_old['careers']
        problems: dict[str, list] = {}
        gone = [c for c in careers if c not in m_new['careers']]
        for c in gone:
            problems[c] = [(c, '<career>', '<absent in new tree>')]
        for c in careers:
            lost = sorted(set(m_old['scripts'].get(c, [])) - set(m_new['scripts'].get(c, [])))
            if lost:
                problems.setdefault(c, []).extend((f'{c} situation script', sid, '<absent>') for sid in lost)
        todo = [c for c in careers if c not in gone]
        count = 0
        with cf.ThreadPoolExecutor(a.jobs) as pool:
            futs = {c: (pool.submit(run_worker, old, c, a.days, tmp), pool.submit(run_worker, new, c, a.days, tmp)) for c in todo}
            for c in todo:
                try:
                    o, n = futs[c][0].result(), futs[c][1].result()
                except RuntimeError as e:
                    print(e, file=sys.stderr)
                    return 2
                count += len(o)
                found = compare_career(c, o, n, late, m_new['fixed'].get(c, []))
                if found:
                    problems.setdefault(c, []).extend(found)
    print(f'task compat: {old} -> {new}')
    print(f'  {len(todo)} careers, days 1..{a.days}, slots 0..{SLOTS - 1}, desk+classic: {count} generated rows compared')
    print(f'  LATE_TASK_KEYS (new tree): {", ".join(sorted(late)) or "none"}')
    if not problems:
        print('OK: every task the old tree generates still matches the new tree.')
        return 0
    total = sum(len(v) for v in problems.values())
    print(f'FAIL: {total} differing fields in {len(problems)} careers. Old open tasks of these kinds would be refused.')
    for c, rows in problems.items():
        print(f'\n[{c}] {len(rows)} differences')
        for where, a_, b_ in rows[:a.show]:
            print(f'  {where}\n    old: {short(a_)}\n    new: {short(b_)}')
        if len(rows) > a.show:
            print(f'  … {len(rows) - a.show} more')
    print('\nFix: keep generation identical (change display code instead), or add a display-only key to'
          ' engine.LATE_TASK_KEYS where the validators already tolerate it.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
