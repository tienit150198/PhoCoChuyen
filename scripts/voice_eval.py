"""Offline eval of NPC attitude (game/spice.py) against the configured model. Not run in CI.

Picks real town NPCs (one per archetype, plus a pupil and a parent), builds the same chat prompt
as ai.persona_reply for a few player lines, calls the model once per case and checks the reply:
guard result (ai.clean_reply), >=2 angles (keyword hits), a stance word, no assistant phrase,
length. With --compare each case also runs with AI_SPICE=0 to measure the prompt-token cost.
Also prints scripted (AI off) lines for the same NPCs. Writes a CSV (default: system temp dir).

    python scripts/voice_eval.py --env ../mot-ngay-lam-nghe/.env --cases 12 --compare
Never point it at production. The API key is read from the environment / env file and never printed.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PLAYER_LINES = [
    ('smalltalk', 'Hôm nay sao rồi, có gì vui không?'),
    ('bargain', 'Bớt cho em chút đi mà, cuối tháng rồi.'),
    ('sad', 'Hôm nay em mệt quá, bị khách chê hoài.'),
    ('task', 'Bạn cần gì nè?'),
    ('kind', 'Cảm ơn nha, lần sau ghé nữa nhé!'),
    ('rude', 'Nói nhiều quá, im đi.'),
    ('mistake', 'Ơ chết, em đưa nhầm món rồi.'),
]
ANGLE_WORDS = dict(
    vi=r'ngọt|đắng|nhạt|béo|thơm|giòn|mềm|dai|vị|ngon|dở|nhừ', gia=r'giá|tiền|ví|mắc|đắt|rẻ|bớt|cái lẻ', toc_do=r'chờ|đợi|lâu|nhanh|lẹ|chậm',
    thai_do=r'cười|lễ phép|ăn nói|nói chuyện|thái độ', sach=r'sạch|dơ|bẩn|lau|khăn', bay_tri=r'đèn|bảng|biển|trang trí|chụp|story|góc',
    tien=r'xe|ổ cắm|mang đi|chỗ', troi=r'nắng|mưa|gió|nóng|lạnh|trời', doi_minh=r'deadline|sếp|con|cháu|lưng|thi|họp|nhà',
    hem=r'hẻm|ngõ|hàng xóm|đầu phố|chợ', am_thanh=r'nhạc|ồn|karaoke|tiếng', tay_nghe=r'tay nghề|pha|gói|làm kỹ|khéo',
)
STANCE = r'ưng|thích|chê|khen|nói thật|thấy|công nhận|tiếc|nghi|bực|không chịu|được đấy|ghê|dữ'


def load_env(path: str | None) -> None:
    if not path or not Path(path).exists():
        return
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            if key.strip().startswith('LLM_'):
                os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def call(messages: list[dict], max_tokens: int, temperature: float) -> tuple[str | None, dict]:
    base, model, key = os.environ.get('LLM_BASE_URL', '').rstrip('/'), os.environ.get('LLM_MODEL', ''), os.environ.get('LLM_API_KEY', '')
    extra = int(os.environ.get('LLM_THINKING_TOKENS', '1024') or 0)
    body = dict(model=model, temperature=temperature, max_tokens=max_tokens + extra, stream=False, messages=messages)
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    req = urllib.request.Request(base + '/chat/completions', json.dumps(body).encode(), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read(400000))
    except Exception as e:  # noqa: BLE001 - an eval run just records the failure
        return None, dict(error=type(e).__name__)
    text = data['choices'][0]['message'].get('content')
    if isinstance(text, list):
        text = ''.join(x.get('text', '') for x in text if isinstance(x, dict))
    return (text or '').strip() or None, data.get('usage') or {}


def pick_cast():
    """(career, npc, archetype) for one NPC per archetype, plus a pupil and a parent."""
    from game.content import NPCS
    from game import personas, spice, voices
    seen, out = set(), []
    for n in sorted(NPCS, key=lambda x: x['id']):
        c = n['career_id']
        age = personas._age(n, c)
        temper = personas._temper(c, n['id'], n, age)
        v = voices.for_npc(n['id'], n.get('role', ''), age, temper, c)
        arch = spice.archetype_for(n['id'], v['id'], n.get('role', ''), age, temper, c)
        if arch and arch not in seen and c != 'teacher':
            seen.add(arch)
            out.append((c, n['id'], arch, 'chat'))
    parent = next(n['id'] for n in NPCS if n['career_id'] == 'teacher' and 'Phụ huynh' in n['role'])
    out.append(('teacher', parent, 'me_bim_ky', 'parent_message'))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', help='file with LLM_* settings (only LLM_* keys are read)')
    ap.add_argument('--cases', type=int, default=12, help='model calls with the block (compare doubles it)')
    ap.add_argument('--compare', action='store_true', help='also run each case with AI_SPICE=0 (token cost)')
    ap.add_argument('--out', default=str(Path(tempfile.gettempdir()) / 'voice_eval.csv'))
    args = ap.parse_args()
    load_env(args.env)
    from game import ai, personas, spice, voices
    from tests.helpers import Journey
    if not ai.available():
        print('LLM_* not configured: scripted lines only.')
    rows, journeys = [], {}
    cast = pick_cast()
    print('--- scripted (AI off) ---')
    for career, npc, arch, _ in cast:
        j = journeys.setdefault(career, Journey(career))
        for kind in ('idle', 'greet'):
            for i in range(6):
                j.c.setdefault('chats', {})[npc] = [dict(role='user', text='ừ')] * i
                line = voices.scripted(j.state, career, npc, kind, '')
                p = personas.persona(j.state, career, npc)
                if any(line == spice._fill(x, p['address']) for b in ('smalltalk', 'greet') for x in spice.ARCHETYPES[arch]['lines'][b]):
                    print(f'[{arch}] {p["name"]} ({kind}): {line}')
                    break
    if not ai.available():
        return
    print('--- model ---')
    n = 0
    for i in range(args.cases):
        career, npc, arch, purpose = cast[i % len(cast)]
        sit, said = PLAYER_LINES[(i * 3 + i // len(cast)) % len(PLAYER_LINES)]
        j = journeys.setdefault(career, Journey(career))
        p = ai._voice_card(personas.persona(j.state, career, npc), purpose)
        task = personas.task_context(j.state, career, npc)
        canonical = ('Dạ, cô nhắn hỏi chuyện của bé ạ.' if purpose == 'parent_message' else
                     engine_reply(j, career, npc, said))
        lim = ai.reply_limits(p, purpose, canonical, task)
        data = json.dumps(dict(persona=p, task=task, canonical=canonical, recent_turns=[], player_says=said), ensure_ascii=False)
        situation = spice.situation_of(said, task, canonical)
        for off in ((False, True) if args.compare else (False,)):
            if off:
                os.environ['AI_SPICE'] = '0'
            system = ai._persona_system(p, purpose, 'vi', lim, situation=situation, seed=i)
            os.environ.pop('AI_SPICE', None)
            text, usage = call([dict(role='system', content=system), dict(role='user', content=data)], lim['max_tokens'],
                               voices.temperature(p['voice'], p.get('mood')))
            n += 1
            allowed = ai._numbers(dict(persona=p, task=task, canonical=canonical))
            line, why = ai.clean_reply(text, allowed, p['name'], sentences=lim['sentences'], chars=lim['chars'],
                                       emoji=(spice.for_card(p, purpose)[1] or {}).get('emoji')) if text else (None, usage.get('error', 'empty'))
            angles = [k for k, rx in ANGLE_WORDS.items() if re.search(rx, (text or '').lower())]
            rows.append(dict(case=i, spice='off' if off else 'on', arch=arch, purpose=purpose, npc=p['name'], verbosity=lim['verbosity'],
                             situation=situation, said=said, reply=text or '', guard=why or 'ok', angles=len(angles),
                             stance=bool(re.search(STANCE, (text or '').lower())), chars=len(text or ''),
                             system_chars=len(system), prompt_tokens=usage.get('prompt_tokens'),
                             completion_tokens=usage.get('completion_tokens'), total_tokens=usage.get('total_tokens')))
            r = rows[-1]
            print(f'[{r["spice"]}] {arch}/{purpose} {p["name"]} ({lim["verbosity"]}, {situation}) «{said}» -> {text!r} '
                  f'| guard={r["guard"]} angles={r["angles"]} tokens={r["prompt_tokens"]}/{r["total_tokens"]}')
            time.sleep(0.3)
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    on = [r for r in rows if r['spice'] == 'on' and r['total_tokens']]
    off = [r for r in rows if r['spice'] == 'off' and r['total_tokens']]
    print(f'calls={n} csv={args.out}')
    print(f'guard ok {sum(r["guard"] == "ok" for r in on)}/{len(on)}, >=2 angles {sum(r["angles"] >= 2 for r in on)}/{len(on)}, '
          f'stance {sum(r["stance"] for r in on)}/{len(on)}')
    if on and off:
        avg = lambda rs, k: sum(r[k] or 0 for r in rs) / len(rs)  # noqa: E731
        print(f'prompt tokens on/off {avg(on, "prompt_tokens"):.0f}/{avg(off, "prompt_tokens"):.0f}, '
              f'total on/off {avg(on, "total_tokens"):.0f}/{avg(off, "total_tokens"):.0f}')


def engine_reply(j, career, npc, said):
    from game.engine import chat_reply
    return chat_reply(j.state, j.c, career, npc, said)[0]


if __name__ == '__main__':
    main()
