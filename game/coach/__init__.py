"""🧭 Hướng dẫn: the first-day coach of every workplace, as data (owner 21/10: "ngày đầu mình cho hướng dẫn các nghề
cả nhập hàng, mua bán, rồi đóng cửa… cho dễ hiểu, hướng dẫn từng cái từng nghề ở mode cũ và mới luôn").

public/js/tutorial/coach.js walks the player through one workplace over the real screen: it rings the control of
each step, says what to do in a few words and moves on when the player does it. The shared steps around every
workplace (open the shift; at the end close it and read the day's summary) live in coach-core.js; this package holds
each workplace's own steps, in the modules next to this file (one dict STEPS per module, career id → steps).

After editing, run `python -m game.coach` to rewrite public/js/tutorial/coach-content.js (loaded the first time the
coach runs; tests/test_coach.py checks it is current, that every workplace has a coach, that every [[button]] of
the guide's steps is either a step's target or shown as its words, and that the selectors and labels exist).

A step, S(emoji, words, labels, selectors, …):
  t   short player words, one line on a phone ("Bấm 📦 Nhập hàng để gọi hàng về."): what to do, not why.
  k   labels of the control as the player reads them (without the emoji), any of them; matched against the
      visible words and the aria-label of buttons, tabs and folds, in both layouts (gọn / đầy đủ).
  s   CSS selectors tried first: [data-coach="…"], [data-command="…"], [data-action="…"][data-tab="…"]…
  g   the guide line it comes from (game/guide_content.py): an index into `steps`, or ('prep', i). Shown under
      "Chi tiết", translated whole by the English pack.
  v   V(words, labels, selectors): a tab or fold that reveals the control when it is not on screen.
  w   where the control is when it is not on screen yet ("Nút ở thanh dưới, hiện khi khách đã gọi món.").
  o   optional: dropped quietly when its control is not around (a beer in the basket, a cold night).
  x   words only (a choice to make, a timing): no control to ring; "Tiếp" moves on, so does the next accepted tap.
  at  'any' when the control is outside the work sheet (the stock sheet, the town); default: the work sheet.

Text rules (like the guide): short player Vietnamese, whole literals (each line is translated whole: add the English
to i18n/overrides.json "strings"), no developer words.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..guide_content import CAREERS as GUIDE, ORDER

LABEL = re.compile(r'\[\[(.+?)\]\]')
EMOJI = re.compile(r'^([^\w\s\[“"(]+)\s*')


def S(e: str, t: str, k=(), s=(), *, g=None, v=None, w: str | None = None, o: bool = False, x: bool = False,
      at: str | None = None) -> dict:
    """One step of a workplace's coach (see the module doc)."""
    step = dict(e=e, t=t)
    if k:
        step['k'] = [k] if isinstance(k, str) else list(k)
    if s:
        step['s'] = [s] if isinstance(s, str) else list(s)
    if g is not None:
        step['g'] = g
    if v:
        step['v'] = v
    if w:
        step['w'] = w
    if o:
        step['o'] = 1
    if x:
        step['x'] = 1
    if at:
        step['at'] = at
    return step


def V(t: str, k=(), s=()) -> dict:
    """What reveals a step's control: a tab, a fold, a dock button."""
    via = dict(t=t)
    if k:
        via['k'] = [k] if isinstance(k, str) else list(k)
    if s:
        via['s'] = [s] if isinstance(s, str) else list(s)
    return via


def stock(k, s=(), *, g=('prep', 0), t: str = 'Bấm 📦 Kho để nhập hàng.', v=None, w: str | None = None,
          order: str = 'Chọn món sắp hết, chọn nơi nhập rồi bấm Đặt. Trả tiền ngay khi đặt.',
          receive: str = 'Hàng tới thì mở thùng, đếm đủ rồi nhận lên kệ.') -> list[dict]:
    """The stock round of a shop: open the stock, order, and (later in the day) count the crates onto the shelf."""
    return [S('📦', t, k, s, g=g, v=v, w=w or 'Nút Kho ở thanh dưới hoặc trong ⋯.'),
            S('🧾', order, x=True, at='any'),
            S('📬', receive, x=True, at='any')]


# The words of public/js/tutorial/coach.js and coach-core.js (shared steps, bubble buttons, the chip, toasts).
ENGINE_EN: dict[str, str] = {
    'Bấm Mở ca để bắt đầu ngày làm.': 'Tap Open shift to start the work day.',
    'Bấm Mở cửa để bắt đầu ngày làm.': 'Tap Open to start the work day.',
    'Bấm Chuẩn bị ngày mới, rồi mở cửa.': 'Tap Prepare a new day, then open.',
    'Bấm vào tiệm trước.': 'Go into the shop first.',
    'Bấm Làm tiếp để vào việc.': 'Tap Continue to get to work.',
    'Đóng bảng này, quay lại việc.': 'Close this page and go back to work.',
    'Mở mục này trước.': 'Open this first.',
    'Chưa thấy nút này: làm tiếp, tới lượt là nó hiện.': 'Not on screen yet: keep going, it shows up when its turn comes.',
    'Làm thêm vài khách. Hết khách thì bấm Khép ca.': 'Serve a few more. When it is quiet, tap Close shift.',
    'Tổng kết ngày: tiền vào quỹ, sao khách chấm. Xem kỹ rồi bấm Xong.': 'Day summary: money into the fund, the stars customers gave. Read it, then tap Done.',
    'Bấm xem tổng kết ngày.': 'Tap to see the day summary.',
    'Chi tiết': 'Details',
    'Bước': 'Step',
    'Tắt hướng dẫn': 'Turn off the guide',
    'Bỏ qua': 'Skip',
    'Tiếp': 'Next',
    'Xong 🎉': 'Done 🎉',
    'Có hướng dẫn mới cho nghề này': 'New step-by-step guide for this job',
    'Xem': 'View',
    'Để sau': 'Later',
    'Xem lại: ⋯ → 🧭 Hướng dẫn': 'See it again: ⋯ → 🧭 Guide',
    'Đã tắt. Xem lại: ⋯ → 🧭 Hướng dẫn': 'Turned off. See it again: ⋯ → 🧭 Guide',
    'Xong hướng dẫn nghề này! Xem lại: ⋯ → 🧭 Hướng dẫn': 'Guide done! See it again: ⋯ → 🧭 Guide',
    '🧭 Hướng dẫn': '🧭 Guide',
}

MODULES = ('shops', 'food', 'street', 'office', 'care', 'services')


def _mods():
    from . import care, food, office, services, shops, street   # static: the build id hashes game/ (tests/test_build_id.py)
    return [shops, food, street, office, care, services]


def _modules() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for mod in _mods():
        for cid, steps in mod.STEPS.items():
            assert cid not in out, f'{cid} has steps in two modules'
            out[cid] = steps
    return out


def english() -> dict[str, str]:
    """Every coach line with its English (i18n/overrides.json "strings" must hold each: `python -m game.coach --i18n`)."""
    out = dict(ENGINE_EN)
    for mod in _mods():
        out.update(getattr(mod, 'EN', {}))
    from . import people   # 💛 the feature coaches' words
    out.update(people.EN)
    return out


def words(cid: str) -> list[str]:
    """The lines of one workplace's own steps that the player reads (t, w, the via's t)."""
    out = []
    for step in _modules().get(cid, []):
        out += [step['t']] + ([step['w']] if step.get('w') else []) + ([step['v']['t']] if step.get('v') else [])
    return out


def derive(cid: str) -> list[dict]:
    """A workplace without its own steps: one step per guide line (its first emoji, the line as words, its
    [[buttons]] as targets). Every workplace has its own steps today; this keeps a new one covered."""
    out = []
    for i, line in enumerate(GUIDE[cid]['steps']):
        m = EMOJI.match(line)
        labels = LABEL.findall(line)
        out.append(S(m.group(1).strip() if m else '👉', line, labels, g=i, x=not labels))
    return out


def guide_line(cid: str, g) -> str:
    """The guide line a step points at: an index into `steps`, or (section, index)."""
    sec, i = ('steps', g) if isinstance(g, int) else g
    return GUIDE[cid][sec][i]


def steps_for(cid: str) -> list[dict]:
    """The steps of one workplace, with `d` (the guide line) filled in and `g` dropped (the browser needs the words)."""
    own = _modules().get(cid) or derive(cid)
    out = []
    for step in own:
        step = dict(step)
        g = step.pop('g', None)
        if g is not None:
            d = guide_line(cid, g)
            if d != step['t']:
                step['d'] = d
        out.append(step)
    return out


def raw(cid: str) -> list[dict]:
    """The steps as written (with `g`), for the tests."""
    return _modules().get(cid) or derive(cid)


def own(cid: str) -> bool:
    return cid in _modules()


def features() -> dict[str, list[dict]]:
    """Coaches of features outside the workplaces (game/coach/people.py: 💛 Thân thiết), shown by their own sheet."""
    from . import people   # static: the build id hashes game/
    return people.FEATURES


def public() -> dict:
    return dict(order=list(ORDER), careers={cid: dict(steps=steps_for(cid)) for cid in ORDER},
                features={k: dict(steps=[dict(x) for x in v]) for k, v in features().items()})


def render_js() -> str:
    dump = lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':'))
    data = public()
    careers = ',\n'.join(f'  {dump(k)}:{dump(v)}' for k, v in data['careers'].items())
    feats = ',\n'.join(f'  {dump(k)}:{dump(v)}' for k, v in data['features'].items())
    return ('/* GENERATED by `python -m game.coach` from game/coach/*.py: edit those files, not this one. */\n'
            f'export default {{\n "order":{dump(data["order"])},\n "careers":{{\n{careers}\n }},\n'
            f' "features":{{\n{feats}\n }}\n}};\n')


DATA_JS = Path(__file__).resolve().parents[2] / 'public' / 'js' / 'tutorial' / 'coach-content.js'
