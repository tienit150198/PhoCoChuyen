"""Persona cards for AI-voiced characters (read-only; never mutates the save).

`persona(state, career, npc)` builds a small, deterministic character card from the
content (NPC_INDEX, plugin people rows, feedback personalities, classroom facts) plus a
short memory of what the player and this character did together in the save.
`task_context(state, career, npc)` describes the character's open task in plain words.
Both are data for the prompt in game/ai.py; nothing here talks to a model.
"""
from __future__ import annotations
import hashlib
import re

from .content import NPC_INDEX, CAREER_META, PRODUCT_INDEX
from . import feedback as fbk

DONE = ('completed', 'referred', 'cancelled')
PLACEHOLDER_LIKES = {'Những câu chuyện có thật'}
PLACEHOLDER_MEMORY = {'Chỉ ghi sự kiện có nguồn.'}

AGE_LABEL = dict(child='trẻ nhỏ (tiểu học)', teen='học sinh lớn', young='người trẻ (sinh viên, mới đi làm)',
                 adult='người lớn', middle='trung niên', elder='người lớn tuổi')
REGION = (('miền Nam', ['nha', 'hen', 'á', 'nè']), ('miền Bắc', ['nhé', 'ạ', 'đấy', 'cơ']))
TEMPER_PARTICLES = dict(genz=['khum', 'xỉu', 'nha'], sour=['cơ', 'đấy', 'hả'], bossy=['đấy', 'cơ mà'],
                        warm=['nha', 'hihi'], picky=['nhé', 'đã'], quiet=[], child=['ạ'],
                        parent_worried=['ạ', 'nhé'], parent_strict=['đấy'], parent_kind=['ạ', 'nhé'])
CHILD_STYLE = 'trẻ con hồn nhiên, câu ngắn, hay kể chuyện nhỏ của mình, lễ phép với người lớn'


def _h(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def _first_word(name: str) -> str:
    return (name.split() or [''])[0].lower()


def _pupil_traits(npc: str) -> list[str]:
    """Sentences about a pupil in the classroom facts, plus their voice line."""
    from . import classroom as cl
    key = next((k for k, v in cl.NPC.items() if v == npc), None)
    name = (NPC_INDEX.get(npc) or {}).get('display_name', '')
    if not key or not name:
        return []
    out = []
    for a in cl.ACTIVITIES:
        for f in a.get('facts', []):
            for s in re.split(r'(?<=[.!?])\s+', f.get('text', '')):
                if s.startswith(name + ' ') and '“' not in s and s not in out:
                    out.append(s)
    try:
        from .teach_lesson import CLUES
        if key in CLUES:
            out.append('Khi chưa hiểu: ' + CLUES[key][1].replace('{Title}', 'Cô').replace('{title}', 'cô'))
    except ImportError:
        pass
    return out[:5]


def _age(npc: dict, career: str) -> str:
    role, name = npc.get('role', ''), npc.get('display_name', '')
    first = _first_word(name)
    if 'Học sinh' in role:
        return 'child' if career == 'teacher' or first == 'bé' else 'teen'
    if first == 'bé':
        return 'child'
    if first in ('bà', 'ông', 'cụ') or 'lớn tuổi' in role or 'Hưu trí' in role:
        return 'elder'
    if 'Sinh viên' in role or 'Phượt' in role:
        return 'young'
    if first in ('cô', 'chú', 'bác', 'dì') and career != 'teacher':
        return 'middle'
    return 'adult'


def _player_title(state: dict, career: str) -> tuple[str, str]:
    """(generic word for the player, teacher word) from the journey's gender, if known."""
    gender = (state.get('journey') or {}).get('gender') if isinstance(state.get('journey'), dict) else None
    if gender == 'male':
        return 'anh', 'thầy'
    if gender == 'female':
        return 'chị', 'cô'
    return 'anh/chị', 'cô'


def _address(state: dict, career: str, npc: dict, age: str, temper: str) -> dict:
    first = _first_word(npc.get('display_name', ''))
    elder_word, teacher_word = _player_title(state, career)
    role = npc.get('role', '')
    if career == 'teacher' and age == 'child':
        return dict(self='con', player=teacher_word)
    if career == 'teacher' and 'Phụ huynh' in role:
        return dict(self='tôi' if temper in ('parent_strict',) else 'chị', player=teacher_word)
    if age == 'child':
        return dict(self='em', player=elder_word)
    if age == 'elder':
        return dict(self=first if first in ('bà', 'ông') else 'tôi', player='con')
    if age == 'middle':
        return dict(self=first, player='con' if first in ('cô', 'chú', 'bác', 'dì') else 'cháu')
    if first in ('anh', 'chị'):
        return dict(self=first, player='em')
    if age in ('young', 'teen') or temper == 'genz':
        return dict(self='mình', player='bạn')
    if temper in ('bossy', 'sour', 'knowitall'):
        return dict(self='tôi', player='em')
    return dict(self='mình', player='bạn')


def _temper(career: str, npc_id: str, npc: dict, age: str) -> str:
    if career == 'teacher' and age == 'child':
        return 'child'
    if career == 'teacher' and 'Phụ huynh' not in npc.get('role', ''):
        return 'warm'  # colleagues in the staff room, not reviewers
    return fbk.persona_for(career, npc_id)


def _relation_label(value: int) -> str:
    return 'thân thiết' if value >= 40 else 'quen mặt' if value > 5 else 'đã từng gặp' if value else 'lần đầu gặp'


def _memory(state: dict, career: str, npc: str) -> dict:
    c = state['careers'][career]
    rel = int((c.get('relationships') or {}).get(npc, 0) or 0)
    past = [t for t in c.get('tasks', []) if t.get('npc') == npc and t.get('status') in DONE][-3:]
    outcome = dict(completed='xong', referred='được chuyển người phụ trách', cancelled='bị hủy')
    visits = [dict(title=t.get('title', ''), day=t.get('day'),
                   outcome=outcome.get(t['status'], t['status']) + ('' if not t.get('mistakes') else ', có sửa sai'))
              for t in past]
    notes = [m.get('text', '')[:160] for m in c.get('memories', []) if m.get('npc') == npc][-2:]
    review = next((p for p in reversed(c.get('feed', [])) if p.get('npc') == npc and p.get('stars')), None)
    return dict(relationship=_relation_label(rel), talked_today=npc in ((c.get('life') or {}).get('day_talked') or []),
                past_visits=visits, notes=notes,
                last_review=dict(stars=review['stars'], text=review.get('text', '')[:140]) if review else None)


def persona(state: dict, career: str, npc: str) -> dict:
    """Deterministic persona card for any NPC id (unknown ids get a neutral card)."""
    n = NPC_INDEX.get(npc) or dict(display_name='Khách', role='Khách', personality='')
    age = _age(n, career)
    temper = _temper(career, npc, n, age)
    per = fbk.PERSONAS.get(temper)
    region_name, particles = REGION[_h(npc) % 2]
    particles = list(dict.fromkeys(TEMPER_PARTICLES.get(temper, []) + particles))[:4]
    if temper == 'quiet':
        particles = particles[:1]
    cares = []
    likes = [x for x in (n.get('likes') or []) if x not in PLACEHOLDER_LIKES]
    if likes:
        cares.append('thích: ' + ', '.join(likes[:3]))
    if n.get('memory_policy') and n['memory_policy'] not in PLACEHOLDER_MEMORY:
        cares.append(n['memory_policy'])
    if career == 'teacher' and age == 'child':
        cares.append('được thầy cô để ý, khen đúng việc mình làm')
    elif career == 'teacher' and 'Phụ huynh' in n.get('role', ''):
        cares.append('con tiến bộ thật, được báo tin cụ thể')
    elif per and per.get('group') == 'customer':
        cares.append('được phục vụ đúng điều mình dặn')
    traits = _pupil_traits(npc) if career == 'teacher' else []
    style = CHILD_STYLE if temper == 'child' else (per or {}).get('style', '')
    return dict(
        id=npc, name=n.get('display_name', 'Khách'), role=n.get('role', ''), career=career,
        place=(CAREER_META.get(career) or {}).get('place', ''),
        age=age, age_label=AGE_LABEL[age],
        temperament=temper, temperament_label=(per or {}).get('name', 'Hồn nhiên' if temper == 'child' else ''),
        style=style, personality=n.get('personality', ''), traits=traits,
        address=_address(state, career, n, age, temper), region=region_name, particles=particles,
        cares=cares, memory=_memory(state, career, npc) if career in state.get('careers', {}) else {},
    )


# ---- the open task, in words ------------------------------------------------
def _mood(patience) -> str | None:
    if not isinstance(patience, (int, float)):
        return None
    return 'vui vẻ, thong thả' if patience >= 85 else 'bắt đầu sốt ruột' if patience >= 60 else 'đang bực vì chờ lâu'


def _value(v):
    if isinstance(v, bool):
        return 'có' if v else 'không'
    if isinstance(v, str):
        return (PRODUCT_INDEX.get(v) or {}).get('name', v)[:160]
    if isinstance(v, (int, float)):
        return v
    return None


def _needs_view(needs) -> dict:
    """Whitelisted, flat, short view of a task's needs (only once the player asked)."""
    out = {}
    if not isinstance(needs, dict):
        return out
    for k, v in needs.items():
        if len(out) >= 14 or k.startswith('_') or v in (None, '', [], {}):
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = _value(v)
        elif isinstance(v, list) and all(isinstance(x, (str, int, float)) for x in v):
            out[k] = ', '.join(str(_value(x)) for x in v[:6])
        elif isinstance(v, dict):
            for k2, v2 in list(v.items())[:6]:
                if isinstance(v2, (str, int, float, bool)) and not str(k2).startswith('_'):
                    out[f'{k}.{k2}'] = _value(v2)
    return out


def open_task(state: dict, career: str, npc: str) -> dict | None:
    c = (state.get('careers') or {}).get(career) or {}
    return next((t for t in c.get('tasks', []) if t.get('npc') == npc and t.get('status') not in DONE), None)


def task_context(state: dict, career: str, npc: str) -> dict | None:
    t = open_task(state, career, npc)
    if not t:
        return None
    ctx = dict(title=t.get('title', ''), opening=t.get('opening', ''), mood=_mood(t.get('patience')),
               asked=bool(t.get('known')), regular=bool(t.get('regular')) or None, vip=bool(t.get('vip')) or None)
    if t.get('known'):
        needs = _needs_view(t.get('needs'))
        if needs:
            ctx['needs'] = needs
    else:
        ctx['hint'] = 'Người chơi chưa hỏi kỹ nhu cầu: chỉ nói ý chung, gợi họ hỏi rõ hoặc mở việc để xem chi tiết.'
    return {k: v for k, v in ctx.items() if v not in (None, '')}
