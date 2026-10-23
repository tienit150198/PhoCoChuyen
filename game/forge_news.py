"""📣 Báo cả phố khi lên SS+ (owner 23/10 "cho mọi người thông báo / ẩn thông tin nếu nâng hạng SS trở lên").

A piece that reaches rank SS or higher through a fusion or a Cường hóa (🪽 wings, 🧬 pets, 👗 pet clothes, 🧰 pet gear)
puts one line on the street's ticker (marriage._post_news, GET /api/news) for the whole town:

* the command marks what it raised (`mark`: result['fz'] = the best piece, the others counted by rank), and the
  storage layer's commit hook (game/pets.py command_commit, in the save's transaction) posts it (`post`);
* ONE line a command, ⚡ Cường hóa nhanh included: the highest rank reached in the run, "(và 2 món SS)" for the rest;
  the ref is the piece's and its rank (one line a piece and rank: a replay posts nothing);
* 🕶️ Ẩn tên: a player who picked it is shown as lux.ANON_NAME. The choice lives in an OPTIONAL journey key (KEY,
  {v, anon}) that every build keeps (journey.validate accepts extra keys), set by the `settings` command (forgeAnon)
  and shown in the settings the client reads; absent = the name shown (the default).
"""
from __future__ import annotations

KEY = 'fzn'
VERSION = 1
SS = 5                                  # D C B A S SS: index 5 and up
KINDS = {
    # kind: (ticker kind, ref prefix, unit, rank labels)
    'wing': ('forge', 'wingfz', 'đôi', ('D', 'C', 'B', 'A', 'S', 'SS', 'SSS', 'HUYỀN THOẠI')),
    'pet': ('pets', 'petfz', 'bé', ('D', 'C', 'B', 'A', 'S', 'SS', 'SSS')),
    'ward': ('forge', 'wardfz', 'món', ('D', 'C', 'B', 'A', 'S', 'SS', 'SSS')),
    'gear': ('forge', 'gearfz', 'món', ('D', 'C', 'B', 'A', 'S', 'SS', 'SSS')),
}
LEGEND = 'HUYỀN THOẠI'


# ---------------------------------------------------------------- 🕶️ the player's choice
def hidden(s: dict) -> bool:
    """True when this save hides its name on the SS+ lines."""
    j = s.get('journey') if isinstance(s, dict) else None
    b = j.get(KEY) if isinstance(j, dict) else None
    return isinstance(b, dict) and b.get('anon') is True


def set_hidden(s: dict, on: bool) -> None:
    j = s['journey']
    if on:
        j[KEY] = dict(v=VERSION, anon=True)
    else:
        j.pop(KEY, None)   # the default leaves no key


def validate(s: dict) -> None:
    j = s.get('journey') if isinstance(s, dict) else None
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    from .engine import need
    need(isinstance(b, dict) and set(b) == {'v', 'anon'} and b['v'] == VERSION and type(b['anon']) is bool,
         'Thiết lập bản lưu không hợp lệ.', 'invalid_save')


# ---------------------------------------------------------------- the command's mark
def _key(i: dict) -> tuple:
    return (bool(i.get('lg')), i['r'])


def mark(out: dict, kind: str, items: list) -> dict:
    """Mark `out` (a command's result) with what reached SS+: items [{id, r rank index, n name, lg legendary?}]; the
    best one is the line, the others counted. Returns `out`."""
    up = [i for i in items if i.get('lg') or i['r'] >= SS]
    if not up:
        return out
    up.sort(key=_key, reverse=True)
    best, rest = up[0], up[1:]
    labels = KINDS[kind][3]
    more: dict = {}
    for i in rest:
        lab = LEGEND if i.get('lg') else labels[i['r']]
        more[lab] = more.get(lab, 0) + 1
    out['fz'] = dict(k=kind, id=str(best['id']), r=int(best['r']), n=str(best['n'])[:60], lg=bool(best.get('lg')),
                     more=[[lab, c] for lab, c in more.items()])
    return out


def text(kind: str, who: str, fz: dict) -> str:
    _, _, unit, labels = KINDS[kind]
    lg = fz['lg'] or (kind == 'wing' and fz['r'] == len(labels) - 1)
    n = fz['n']
    if kind == 'pet':
        line = f'🌟 {who} vừa ghép ra HUYỀN THOẠI {n}!' if lg else f'🌈 {who} vừa ghép ra bé {n} hạng {labels[fz["r"]]}!'
    else:
        verb = 'ghép' if kind == 'ward' else 'cường hóa'
        icon = {'wing': '🪽', 'ward': '👗', 'gear': '🧰'}[kind]
        line = (f'🌟 {who} vừa {verb} {n} lên {LEGEND}!' if lg else f'{icon} {who} vừa {verb} {n} lên hạng {labels[fz["r"]]}!')
    if fz['more']:
        line = line[:-1] + ' (và ' + ', '.join(f'{c} {unit} {lab}' for lab, c in fz['more']) + ')!'
    return line


def post(db, sid: str, after: dict, result) -> bool:
    """The line of a command's mark (the save's transaction): once a piece and rank. True when posted."""
    fz = result.get('fz') if isinstance(result, dict) else None
    if not (isinstance(fz, dict) and fz.get('k') in KINDS and isinstance(fz.get('id'), str) and type(fz.get('r')) is int
            and 0 <= fz['r'] < len(KINDS[fz['k']][3]) and isinstance(fz.get('n'), str) and isinstance(fz.get('more'), list)):
        return False
    from . import lux, marriage
    kind = fz['k']
    news_kind, pre, _, _ = KINDS[kind]
    who = lux._display(db, sid, hidden(after))
    ref = f'{pre}:{sid[:16]}:{fz["id"]}:{"L" if fz["lg"] else fz["r"]}'
    return marriage._post_news(db, news_kind, ref, text(kind, who, fz), '', '')
