"""🏫 Trường học: the shapes of the question banks (game/school_bank_*.py) and their checker.

A subject is three lessons (each a short lecture of two or three key lines and three questions tied to it) plus one
extra review question: ten questions. Kinds:
  C(text, options, ok, why)   multiple choice: 3–4 options, `ok` the index of the right one (shown shuffled)
  T(text, ok, why)            true / false: `ok` True when the statement is right
  O(text, items, why)         put in order: 3–4 items written in the RIGHT order (shown shuffled)
  N(text, ok, why)            a whole number to type
Pure data, no game imports. Question ids are their place (lesson index, question index): banks are append-only in
spirit (fix a wording freely, never reorder questions of a released subject).
"""
from __future__ import annotations

TEXT_MAX = 160
OPT_MAX = 70
WHY_MAX = 170
POINT_MAX = 130
TITLE_MAX = 48


def C(text, options, ok, why):
    return dict(k='c', text=text, options=tuple(options), ok=ok, why=why)


def T(text, ok, why):
    return dict(k='t', text=text, ok=bool(ok), why=why)


def O(text, items, why):
    return dict(k='o', text=text, items=tuple(items), why=why)


def N(text, ok, why):
    return dict(k='n', text=text, ok=int(ok), why=why)


def L(title, points, qs):
    return dict(title=title, points=tuple(points), qs=tuple(qs))


def S(name, emoji, lessons, extra):
    return dict(name=name, emoji=emoji, lessons=tuple(lessons), extra=tuple(extra))


def questions(subject: dict) -> list[dict]:
    """The subject's ten questions in their fixed order: lesson 1's three, lesson 2's, lesson 3's, the extra one."""
    return [q for l in subject['lessons'] for q in l['qs']] + list(subject['extra'])


def _q(q: dict, where: str) -> list[str]:
    bad = []
    t = q.get('text')
    if not isinstance(t, str) or not 8 <= len(t) <= TEXT_MAX:
        bad.append(f'{where}: text length')
    w = q.get('why')
    if not isinstance(w, str) or not 4 <= len(w) <= WHY_MAX:
        bad.append(f'{where}: why length')
    k = q.get('k')
    if k == 'c':
        o = q.get('options')
        if not (isinstance(o, tuple) and 3 <= len(o) <= 4 and all(isinstance(x, str) and 1 <= len(x) <= OPT_MAX for x in o)):
            bad.append(f'{where}: options')
        elif len(set(o)) != len(o):
            bad.append(f'{where}: duplicate options')
        if type(q.get('ok')) is not int or not (0 <= q['ok'] < len(o or ())):
            bad.append(f'{where}: ok index')
    elif k == 't':
        if type(q.get('ok')) is not bool:
            bad.append(f'{where}: ok bool')
    elif k == 'o':
        it = q.get('items')
        if not (isinstance(it, tuple) and 3 <= len(it) <= 4 and all(isinstance(x, str) and 1 <= len(x) <= OPT_MAX for x in it)
                and len(set(it)) == len(it)):
            bad.append(f'{where}: items')
    elif k == 'n':
        if type(q.get('ok')) is not int or not (0 <= q['ok'] <= 10**7):
            bad.append(f'{where}: number')
    else:
        bad.append(f'{where}: kind')
    return bad


def check(subjects: dict, ids=None) -> list[str]:
    """Every problem of a bank (empty when it is fine). `ids`: the subject ids it must hold."""
    bad = []
    if ids is not None and set(subjects) != set(ids):
        bad.append(f'subject ids: missing {sorted(set(ids) - set(subjects))}, extra {sorted(set(subjects) - set(ids))}')
    for sid, s in subjects.items():
        if not isinstance(s.get('name'), str) or not s['name'] or not isinstance(s.get('emoji'), str):
            bad.append(f'{sid}: name/emoji')
        ls = s.get('lessons')
        if not isinstance(ls, tuple) or len(ls) != 3:
            bad.append(f'{sid}: needs 3 lessons')
            continue
        for i, l in enumerate(ls):
            if not isinstance(l.get('title'), str) or not 3 <= len(l['title']) <= TITLE_MAX:
                bad.append(f'{sid}.L{i}: title')
            p = l.get('points')
            if not (isinstance(p, tuple) and 2 <= len(p) <= 3 and all(isinstance(x, str) and 8 <= len(x) <= POINT_MAX for x in p)):
                bad.append(f'{sid}.L{i}: points (2-3 lines, <= {POINT_MAX} chars)')
            if not isinstance(l.get('qs'), tuple) or len(l['qs']) != 3:
                bad.append(f'{sid}.L{i}: needs 3 questions')
                continue
            for k, q in enumerate(l['qs']):
                bad += _q(q, f'{sid}.L{i}.Q{k}')
        ex = s.get('extra')
        if not isinstance(ex, tuple) or len(ex) != 1:
            bad.append(f'{sid}: needs 1 extra question')
        else:
            bad += _q(ex[0], f'{sid}.extra')
        qs = [q for l in ls if isinstance(l.get('qs'), tuple) for q in l['qs']] + list(ex or ())
        texts = [q.get('text') for q in qs]
        if len(set(texts)) != len(texts):
            bad.append(f'{sid}: duplicate question text')
        kinds = [q.get('k') for q in qs]
        if kinds.count('c') < 4 or 't' not in kinds or 'o' not in kinds:
            bad.append(f'{sid}: mix needs >= 4 choice, >= 1 true/false, >= 1 order')
    return bad
