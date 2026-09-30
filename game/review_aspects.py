"""Review aspects: many more angles in reviews (the logic; the catalogue is review_aspects_content.py).

Reviewers now talk about concrete things: the coffee too bland, the paper straw going soggy, the
restroom, a sticky table, the music, the teacher's patience or homework load, the new colleague who
wears flip-flops to the office ("con nhỏ khó ưa"). `plan()` picks zero, one or two aspects for a
fresh review; `render()` writes them in the reviewer's persona (teencode, sarcastic praise, one
word, parent-group style, regulars...).

Fairness:
* grounded aspects come from real state (`signals`): criteria the job scored low or high, recorded
  slips, slow or quick service, a messy counter, a dirty sealer, grimy cups, dirty bowls, the day's
  weather, a crowd, a regular customer, a shift that ran past closing time;
* flavour aspects (wifi, restroom, music, clothing...) have nothing in the game behind them: they
  are seeded, at a modest rate, and mostly mild. Now and then one costs a star; it is then stored as
  `unfair` (key 'aspect'), so the owner can answer it with facts through the usual reply flow;
* an aspect whose complaint needs state (a sticky table, a leaking lid) never complains without it;
* stars stay driven by the job. Only that rare flavour complaint moves them, by one star.

Variety: no aspect repeats for the same workplace within the last RECENT reviews (c['review_aspects'],
capped and validated). Everything is seeded from the task id and day and stored on the review.
"""
from __future__ import annotations

import re
import unicodedata

from .review_aspects_content import (ASPECTS, FAMILY, WRAP, VOICE_WRAP, REGULAR_WRAP, COMBO, STYLE_WRAP, NV, NV_FAM, NV_CAREER,
                                     NHO, REPLY, LABEL, CLUE, TRUTH, SITUATION, UNSAFE)

RECENT = 6                       # aspects remembered per workplace (no repeats within this window)
RECENT_KEY = 'review_aspects'
MAX_ON_REVIEW = 4
HARSH_WORDS = ('sour', 'rude', 'knowitall', 'entitled', 'drama', 'troll', 'bossy', 'parent_rude', 'parent_knowitall')
SOFT = ('warm', 'parent_kind', 'quiet', 'genz')
TALKATIVE = ('bossy', 'knowitall', 'picky', 'warm', 'parent_worried', 'parent_knowitall', 'drama')
SARC = ('sour', 'rude', 'genz', 'drama', 'troll', 'knowitall')
# Styled reviews that take an aspect line; the others ("ok", emoji only, life stories) keep their exact words.
STYLES_OK = tuple(STYLE_WRAP)
_UNSAFE = re.compile(r'(?<!\w)(' + '|'.join(UNSAFE) + r')(?!\w)', re.I)


# ------------------------------------------------------------------ helpers
def _h(*parts) -> int:
    from .feedback import _hash
    return _hash('aspect', *parts)


def _roll(*parts) -> float:
    from .feedback import _roll as r
    return r('aspect', *parts)


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:] if text and text[0] not in '“"' else text


def _gender(s: dict):
    j = (s or {}).get('journey')
    g = j.get('gender') if isinstance(j, dict) else None
    return g if g in ('male', 'female') else None


def family(career: str) -> str | None:
    return FAMILY.get(career)


def voice_of(t: dict, group: str | None = None) -> str | None:
    """Teacher reviews: 'p' parent, 's' student, 'o' colleague. None elsewhere.
    A parent persona always writes as a parent, whoever the task's contact was."""
    if t.get('career') != 'teacher':
        return None
    if group == 'parent' or t.get('students'):
        return 'p'                   # engine signs these "Mẹ của …" / "Bố của …"
    try:
        from .content import NPC_INDEX
        role = str((NPC_INDEX.get(t.get('npc')) or {}).get('role') or '')
    except Exception:  # noqa: BLE001 - content is optional in unit calls
        role = ''
    if 'Học sinh' in role:
        return 's'
    if 'Đồng nghiệp' in role:
        return 'o'
    return 'p'


def lines(a: dict, pol: str, career: str, voice: str | None = None, tied: str | None = None) -> list[str]:
    rows = a.get(pol) or ()
    if isinstance(rows, (list, tuple)):
        return list(rows) if FAMILY.get(career) != 'school' else []
    if tied and ('@' + tied) in rows:
        return list(rows['@' + tied])      # lines only true for this signal ("trời mưa mà…")
    fam = FAMILY.get(career)
    if fam == 'school':
        return list(rows.get(voice or 'p', ()))
    return list(rows.get(career, ())) + list(rows.get(fam, ())) + list(rows.get('*', ()))


def eligible(career: str, sig: set) -> list[dict]:
    fam = FAMILY.get(career)
    out = []
    for a in ASPECTS.values():
        if fam not in a['fams'] or (a['only'] and career not in a['only']) or career in a['skip']:
            continue
        if a['need'] and not any(x in sig for x in a['need']):
            continue
        out.append(a)
    return out


# ------------------------------------------------------------------ signals
def _data(c: dict) -> dict:
    ext = c.get('ext') if isinstance(c.get('ext'), dict) else {}
    d = ext.get('data') if isinstance(ext, dict) else None
    return d if isinstance(d, dict) else {}


def signals(s: dict, c: dict, t: dict, criteria: list) -> set:
    """What is really true about this job and this place right now."""
    from . import review_gripes as rg
    try:
        out = set(rg.signals(s, c, t))
    except Exception:  # noqa: BLE001 - a partial test state must not break a review
        out = set()
    career = t.get('career', '')
    for x in criteria or []:
        k, sc = x.get('key'), x.get('score')
        if isinstance(k, str) and type(sc) is int:
            if sc <= 3:
                out.add(f'crit:{k}:lo')
            elif sc >= 5:
                out.add(f'crit:{k}:hi')
    for r in t.get('slips') or []:
        if isinstance(r, dict) and r.get('code'):
            out.add('slip:' + str(r['code']))
    if 'patience' in t and type(t.get('patience')) is int:
        if t['patience'] < 60:
            out.add('slow')
        elif t['patience'] >= 90 and not t.get('slips') and not t.get('mistakes'):
            out.add('quick')
    if out & {'crit:speed:hi', 'crit:time:hi'} and not t.get('slips'):
        out.add('quick')
    if 'crowded' in out and 'slow' in out:
        out.add('slow_crowd')
    if 'crowded' in out and 'quick' in out:
        out.add('fast_crowd')
    npc = t.get('npc')
    served = int((c.get('metrics') or {}).get(f'served:{npc}', 0) or 0) if isinstance(c.get('metrics'), dict) else 0
    tier = 0
    if s and npc:
        try:
            from . import closeness
            tier = closeness.tier(s, npc)
        except Exception:  # noqa: BLE001
            tier = 0
    if served >= 3 or tier >= 3:
        out.add('regular')
    if c.get('ext') and career:
        try:
            from . import dayclock
            if dayclock.past_close(c, career):
                out.add('overtime')
        except Exception:  # noqa: BLE001
            pass
    d = _data(c)
    if career == 'milk_tea':
        b = d.get('boba') if isinstance(d.get('boba'), dict) else {}
        if int(b.get('sealer_wear', 0) or 0) >= 20:
            out.add('sealer_dirty')
        cup = t.get('cup') if isinstance(t.get('cup'), dict) else {}
        if cup.get('seal_q') == 'perfect':
            out.add('seal_good')
        elif cup.get('seal_q') == 'burnt':
            out.add('slip:seal')
    elif career == 'tra_da':
        g = d.get('glasses') if isinstance(d.get('glasses'), dict) else {}
        if int(g.get('grimy', 0) or 0) > 0 or int(g.get('dirty', 0) or 0) >= 4:
            out.add('grimy_cups')
        ice = d.get('ice') if isinstance(d.get('ice'), dict) else None
        if ice is not None and not ice.get('portions'):
            out.add('no_ice')
    elif career == 'restaurant':
        p = d.get('plan')
        rules = p.get('rules') if isinstance(p, dict) and p.get('day') == c.get('day') and isinstance(p.get('rules'), dict) else {}
        if int(rules.get('dirty', 0) or 0) >= 3:
            out.add('dirty_bowls')
    kind = str(t.get('kind') or '')
    title = str(t.get('title') or '').lower()
    if kind in ('return', 'ret') or 'đổi' in title or 'trả' in title:
        out.add('return_task')
    return out


# ------------------------------------------------------------------ choosing
def _options(career: str, sig: set, recent: list, voice) -> tuple[list, list, list]:
    """(grounded, flavour, slipped): grounded (id, pol, signal), flavour (id, pol), slipped (id, signal)."""
    grounded, flavour, slipped = [], [], []
    for a in eligible(career, sig):
        neg, pos = lines(a, 'neg', career, voice), lines(a, 'pos', career, voice)
        slip = next((x for x in a['sig_neg'] if x.startswith('slip:') and x in sig), None)
        if slip:
            slipped.append((a['id'], slip))   # the mistake itself is already in the review (mistake_lines)
            continue
        if a['id'] in recent:
            continue
        gneg = next((x for x in a['sig_neg'] if x in sig), None)
        gpos = next((x for x in a['sig_pos'] if x in sig), None)
        if gneg and neg:
            grounded.append((a['id'], 'neg', gneg))
        elif gpos and pos:
            grounded.append((a['id'], 'pos', gpos))
        elif a['claim']:
            if pos:
                flavour.append((a['id'], 'pos'))
            if neg and (a['subjective'] or not a['sig_neg']):
                flavour.append((a['id'], 'neg'))
    return grounded, flavour, slipped


# Signals about the weather, the crowd or the look of the street: true, but not the player's doing.
AMBIENT = frozenset(('rain', 'sunny', 'breeze', 'festival', 'crowded', 'calm', 'busy_day', 'cat', 'small_place', 'garden',
                     'dark_porch', 'plant', 'bare', 'slow_crowd', 'fast_crowd'))


def perfect(t: dict, sig: set, fair: int) -> bool:
    """The job was done without a flaw: top fair grade, no slip, no mistake, no weak criterion."""
    return (fair >= 5 and not t.get('slips') and not t.get('mistakes')
            and not any(x.startswith(('slip:', 'crit:')) and x.endswith(':lo') or x.startswith('slip:') for x in sig))


def aspect_rate(day: int) -> float:
    """Share of eligible reviews that mention an aspect. Day one: grounded ones only."""
    return 0.45 if day <= 1 else 0.6


def _neg_share(stars: int, persona: str) -> int:
    base = 25 if stars >= 5 else 40 if stars == 4 else 60 if stars == 3 else 75
    if persona in HARSH_WORDS or persona in ('picky', 'parent_strict'):
        base += 20
    if persona in ('warm', 'parent_kind'):
        base -= 15
    return max(5, min(90, base))


def plan(s: dict, c: dict, t: dict, persona: str, group: str, stars: int, fair: int, criteria: list, *, day1_ok: bool = True) -> dict | None:
    """Pick aspects for one fresh review. Returns dict(picks, slipped, drop, voice) or None."""
    career = t.get('career', '')
    if career not in FAMILY or not isinstance(t.get('id'), str):
        return None
    day = int(c.get('day', 1) or 1)
    tid = t['id']
    sig = signals(s, c, t, criteria)
    voice = voice_of(t, group)
    recent = [x for x in (c.get(RECENT_KEY) or []) if isinstance(x, str)] if isinstance(c.get(RECENT_KEY), list) else []
    grounded, flavour, slipped = _options(career, sig, recent, voice)
    if perfect(t, sig, fair):
        # Flawless work: no invented complaints and no weather/crowd grumbles; only what the player really left behind
        # (grimy cups, a worn sealer...) may still be said, and praise.
        flavour = [o for o in flavour if o[1] == 'pos']
        grounded = [o for o in grounded if o[1] == 'pos' or o[2] not in AMBIENT]
    slip_rows = [dict(id=aid, pos=False, tied=sg[:40], said=False) for aid, sg in slipped[:2]]
    if _roll('rate', tid, day) >= aspect_rate(day) or (day <= 1 and not grounded) or not (grounded or flavour):
        return dict(picks=[], slipped=slip_rows, drop=False, voice=voice, sig=sig) if slip_rows else None
    picks = []
    h = _h('first', tid, day)
    if grounded and (not flavour or day <= 1 or h % 100 < 70):
        aid, pol, tied = grounded[(h // 100) % len(grounded)]
        picks.append(dict(id=aid, pol=pol, tied=tied))
    else:
        want = 'neg' if _h('pol', tid) % 100 < _neg_share(stars, persona) else 'pos'
        pool = [o for o in flavour if o[1] == want] or flavour
        aid, pol = pool[(h // 100) % len(pool)]
        picks.append(dict(id=aid, pol=pol, tied=None))
    if day >= 2 and _h('two', tid) % 100 < (45 if persona in TALKATIVE else 28):
        topic = ASPECTS[picks[0]['id']]['topic']
        g2 = [o for o in grounded if o[0] != picks[0]['id'] and ASPECTS[o[0]]['topic'] != topic]
        f2 = [o for o in flavour if o[0] != picks[0]['id'] and ASPECTS[o[0]]['topic'] != topic]
        h2 = _h('second', tid, day)
        if g2 and (not f2 or h2 % 2 == 0):
            aid, pol, tied = g2[(h2 // 2) % len(g2)]
            picks.append(dict(id=aid, pol=pol, tied=tied))
        elif f2:
            # A second flavour aspect leans the other way half the time ("Cà phê ngon, mà nhà vệ sinh hơi bí").
            other = [o for o in f2 if o[1] != picks[0]['pol']]
            pool = other if other and h2 % 3 else f2
            aid, pol = pool[(h2 // 3) % len(pool)]
            picks.append(dict(id=aid, pol=pol, tied=None))
    first = picks[0]
    drop = (first['pol'] == 'neg' and not first['tied'] and stars == fair == 4 and persona not in SOFT
            and day >= 2 and _h('drop', tid) % 100 < 30)
    return dict(picks=picks, slipped=slip_rows, drop=drop, voice=voice, sig=sig)


# ------------------------------------------------------------------ writing
def _tokens(s: dict, career: str, persona: str) -> dict:
    from .feedback_voices import owner_call
    g = _gender(s)
    tone = 'harsh' if persona in HARSH_WORDS else 'polite'
    fam = FAMILY.get(career)
    nv = (NV_CAREER.get(career) or NV_FAM.get(fam) or NV)[tone][g]
    return dict(nv=nv, nho=NHO[tone][g], owner=owner_call(s, fam == 'school'))


def _fill(text: str, **kw) -> str:
    out = text
    for k, v in kw.items():
        out = out.replace('{' + k + '}', v).replace('{' + k[:1].upper() + k[1:] + '}', _cap(v))
    return re.sub(r'\s{2,}', ' ', out).strip()


def clause(aid: str, pol: str, career: str, voice, tok: dict, seed: int, tied: str | None = None) -> str:
    rows = lines(ASPECTS[aid], pol, career, voice, tied)
    return _fill(rows[seed % len(rows)], **tok) if rows else ''


def _end(text: str) -> str:
    return text if re.search(r'[.!?…]$|[^\w\s)”"]$', text) else text + '.'


def render(p: dict, s: dict, t: dict, persona: str, group: str, style: str | None, item: str, seed: int, single: bool = False) -> tuple[str, list]:
    """(sentence, rows for fb['aspects']) for a plan. `single`: use the first aspect only."""
    career = t.get('career', '')
    voice = p.get('voice')
    tok = dict(_tokens(s, career, persona), item=item)
    picks = p['picks'][:1] if single else p['picks']
    rows, parts = [], []
    for i, k in enumerate(picks):
        x = clause(k['id'], k['pol'], career, voice, tok, _h('line', t['id'], k['id'], seed) // 7 + i, k['tied'])
        if not x:
            continue
        parts.append((k, x))
        rows.append(dict(id=k['id'], pos=k['pol'] == 'pos', tied=(k['tied'] or None) and k['tied'][:40], text=x[:200]))
    if not parts:
        return '', []
    h = _h('wrap', t['id'], seed)
    pick = lambda r, n=0: r[(h // 11 + n) % len(r)]
    if len(parts) == 1:
        (k, x), = parts
        pol = k['pol']
        a = ASPECTS[k['id']]
        if persona == 'quiet' and style is None and a['word'][0 if pol == 'neg' else 1]:
            return a['word'][0 if pol == 'neg' else 1], rows
        if pol == 'neg' and a['sarc'] and persona in SARC and style in (None, 'sarcastic') and h % 100 < 45:
            return _end(_cap(_fill(pick(a['sarc']), **tok))), rows
    else:
        (k1, x1), (k2, x2) = parts[:2]
        if persona == 'quiet' and style is None:
            w = [ASPECTS[k['id']]['word'][0 if k['pol'] == 'neg' else 1] for k, _ in parts[:2]]
            if all(w):
                return ' '.join(w), rows
        if k1['pol'] != k2['pol']:
            pos, neg = (x1, x2) if k1['pol'] == 'pos' else (x2, x1)
            x = _fill(pick(COMBO['mix'], 1), pos=pos, neg=neg)
            pol = 'mix'
        else:
            pol = k1['pol']
            x = _fill(pick(COMBO[pol], 1), a=x1, b=x2)
    if style in STYLE_WRAP:
        tpl = pick(STYLE_WRAP[style][pol])
    elif FAMILY.get(career) == 'school' and voice in VOICE_WRAP:
        tpl = pick(VOICE_WRAP[voice][pol])
    elif 'regular' in (p.get('sig') or ()) and persona not in HARSH_WORDS and pol != 'mix' and h % 3 == 0:
        tpl = pick(REGULAR_WRAP[pol])
    else:
        w = WRAP.get(persona) or (WRAP['parent_kind'] if group == 'parent' else WRAP['warm'])
        rows_w = w[pol]
        if FAMILY.get(career) in ('office', 'school'):   # no shop words ("quán", "mở cửa đón khách") at a desk or a school
            rows_w = [r for r in rows_w if 'quán' not in r.lower() and 'đón khách' not in r] or rows_w
        tpl = pick(rows_w)
    return _fill(tpl, x=x), rows


def weave(text: str, p: dict, s: dict, t: dict, persona: str, group: str, style: str | None, item: str, seed: int,
          limit: int = 590) -> tuple[str, list]:
    """Append the aspect sentence to a review text, within the length cap. Returns (text, rows said)."""
    for single in (False, True):
        line, rows = render(p, s, t, persona, group, style, item, seed, single)
        if not line:
            return text, []
        joined = (text.rstrip() + ' ' + line) if text else _cap(line)
        if len(joined) <= limit:
            return joined, rows
    return text, []


def unfair_for(p: dict) -> dict:
    a = ASPECTS[p['picks'][0]['id']]
    return dict(key='aspect', label=a['label'] or LABEL, claim=a['claim'], truth=TRUTH, aspect=a['id'])


def commit(c: dict, rows: list) -> None:
    """Remember what was said here so the next reviews talk about something else."""
    if not isinstance(c, dict):
        return
    said = [r['id'] for r in rows if r.get('said', True)]
    if not said:
        return
    have = [x for x in (c.get(RECENT_KEY) or []) if isinstance(x, str) and x in ASPECTS] if isinstance(c.get(RECENT_KEY), list) else []
    c[RECENT_KEY] = (have + said)[-RECENT:]


# ------------------------------------------------------------------ AI, replies, safety
def ai_facts(fb: dict) -> list[dict]:
    out = []
    for r in fb.get('aspects') or []:
        a = ASPECTS.get(r.get('id'))
        if not a:
            continue
        row = dict(goc=a['label'], danh_gia='khen' if r.get('pos') else 'chê',
                   nguon='có thật trong ca làm' if r.get('tied') else 'cảm nhận riêng của người viết')
        if r.get('text'):
            row['chi_tiet'] = r['text']
        if r.get('said') is False:
            row['nguon'] = 'lỗi đã ghi nhận (đã có trong review)'
        out.append(row)
    return out


def situation(fb: dict) -> str | None:
    return SITUATION if (fb.get('unfair') or {}).get('aspect') else None


def unsafe(text: str) -> bool:
    """True if a line talks about bodies, looks, age, region, religion, sex, or names a real brand."""
    if not isinstance(text, str):
        return False
    return bool(_UNSAFE.search(unicodedata.normalize('NFC', text)))


def validate(fb: dict) -> None:
    from .engine import need, clean_text
    rows = fb.get('aspects')
    if rows is not None:
        need(isinstance(rows, list) and len(rows) <= MAX_ON_REVIEW, 'Góc nhận xét sai.')
        for r in rows:
            need(isinstance(r, dict) and set(r) <= {'id', 'pos', 'tied', 'text', 'said'} and r.get('id') in ASPECTS
                 and type(r.get('pos')) is bool and type(r.get('said', True)) is bool
                 and (r.get('tied') is None or (isinstance(r['tied'], str) and len(r['tied']) <= 40)), 'Góc nhận xét sai.')
            if 'text' in r:
                clean_text(r['text'], 200, 0)
    u = fb.get('unfair')
    if isinstance(u, dict) and 'aspect' in u:
        need(u['aspect'] in ASPECTS, 'Góc nhận xét sai.')


def validate_recent(c: dict) -> None:
    """c['review_aspects']: optional (older saves), at most RECENT known ids."""
    from .engine import need
    rows = c.get(RECENT_KEY)
    if rows is None:
        return
    need(isinstance(rows, list) and len(rows) <= RECENT and all(isinstance(x, str) and x in ASPECTS for x in rows),
         'Danh sách góc nhận xét gần đây sai.')


def install(ns: dict) -> None:
    """Add the aspect replies to feedback.py's TWIST_REPLY."""
    for k, rows in REPLY.items():
        ns['TWIST_REPLY'].setdefault(k, list(rows))


def catalogue() -> dict:
    """Counts per family, for the report and tests."""
    out = {}
    for fam in ('food', 'shop', 'service', 'school', 'office'):
        rows = [a for a in ASPECTS.values() if fam in a['fams']]
        out[fam] = len(rows)
    return out
