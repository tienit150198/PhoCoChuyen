"""`python -m game.coach`: rewrite public/js/tutorial/coach-content.js from game/coach/*.py.
`python -m game.coach --i18n`: also add the English of every new coach line to i18n/overrides.json "strings" (a text
insert at the end of "strings", the existing lines untouched), then run `scripts/i18n_extract.py build`."""
import json
import sys
from pathlib import Path

from . import DATA_JS, english, render_js

DATA_JS.write_text(render_js(), encoding='utf-8', newline='\n')
print(f'wrote {DATA_JS}')
if '--i18n' in sys.argv:
    path = Path(__file__).resolve().parents[2] / 'i18n' / 'overrides.json'
    text = path.read_text(encoding='utf-8')
    have = json.loads(text)['strings']
    add = {vi: en for vi, en in english().items() if vi not in have}
    if add:
        anchor = '\n  },\n  "patterns": {'
        at = text.index(anchor)
        lines = ''.join(f',\n  {json.dumps(vi, ensure_ascii=False)}: {json.dumps(en, ensure_ascii=False)}' for vi, en in add.items())
        text = text[:at] + lines + text[at:]
        json.loads(text)   # still valid JSON
        path.write_text(text, encoding='utf-8')
    print(f'i18n/overrides.json: {len(add)} coach lines added')
