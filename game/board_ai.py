"""HTTP glue for Nhóm Cư Dân Phố (kept out of server.py).

GET  /api/board?before=<seq>  -> {board, cast}                       (read only)
POST /api/ai/board            -> {state, revision, result, board, mode, reason}
  {op:'post', text}            runs `bd_post`   (authored replies stored first)
  {op:'reply', post, text?, tone?} runs `bd_reply` (tone: clarify|joke|confront|ignore on a rumour)
  {op:'open'}                  may add one AI NPC-to-NPC comment (<= board.AI_PER_DAY a life day)
  request_id / expected_revision like /api/command.

With AI allowed (consent, a provider, the per-player chat budget), each stored scripted
reply is reworded in character and saved through the internal `bd_voice` command, only
if it is still the same scripted line. Without AI everything above still works: the
authored replies are already stored. Design: docs/superpowers/specs/2026-09-29-board-design.md
"""
from __future__ import annotations

import secrets
from concurrent.futures import ThreadPoolExecutor

from . import ai, board
from .engine import GameError, public_state
from .storage import Conflict

MAX_VOICED = 3


def get_view(state: dict, query: dict | None = None) -> dict:
    before = (query or {}).get('before')
    try:
        before = int(before) if before not in (None, '') else None
    except (TypeError, ValueError):
        before = None
    return dict(board=board.public(state, before=before), cast=board.cast_public())


def _allowed(h, token: str, settings: dict) -> str | None:
    """None when AI may run, else the reason. Consumes one chat-budget unit when allowed."""
    if not settings.get('aiConsent'):
        return 'no_consent'
    if not ai.available():
        return 'not_configured'
    if not h.ai_chat_budget(token):
        return 'rate_limit'
    return None


def _internal(h, token: str, rid: str, action: str, payload: dict):
    try:
        return h.server.store.command(token, rid[:100], None, None, action, payload, internal=True)
    except (Conflict, GameError):
        return None


def ai_board(h, token: str, state: dict, revision: int, data: dict) -> dict:
    """POST /api/ai/board (see module doc). `h` is the request handler (store, budgets)."""
    store = h.server.store
    op = data.get('op')
    if op not in ('post', 'reply', 'open'):
        raise GameError('Thao tác nhóm không hợp lệ.')
    rid = data.get('request_id')
    if not (isinstance(rid, str) and 8 <= len(rid) <= 90):
        rid = 'ai-board-' + secrets.token_hex(12)
    mode, reason = 'scripted', None
    if op == 'open':
        out = dict(state=public_state(state), revision=revision, result=dict(message=''))
        job = board.open_job(state)
        if not job:
            reason = 'nothing_to_do'
        else:
            reason = _allowed(h, token, state.get('settings') or {})
            if not reason:
                answer = board.ai_generate(state, job)
                reason = answer.get('reason')
                if answer['mode'] == 'ai':
                    stored = _internal(h, token, rid + '-npc', 'bd_npc',
                                       dict(post=job['post'], who=job['who'], text=answer['text'], canonical=job['canonical']))
                    if stored:
                        out, mode = stored, 'ai'
                    else:
                        reason = 'superseded'
    else:
        payload = dict(text=data.get('text')) if op == 'post' else {k: data[k] for k in ('post', 'text', 'tone') if k in data}
        if op == 'post' and not isinstance(payload.get('text'), str):
            raise GameError('Viết gì đó rồi đăng nhé.')
        expected = data.get('expected_revision')
        out = store.command(token, rid, expected if type(expected) is int else revision, data.get('career'),
                            'bd_post' if op == 'post' else 'bd_reply', payload)
        if out.get('replayed'):
            reason = 'replayed'
        else:
            fresh, _, _ = store.read(token)
            settings = fresh.get('settings') or {}
            jobs = [board.voice_job(fresh, r['post'], r['cmt']) for r in (out['result'].get('replies') or [])[:MAX_VOICED]]
            jobs = [j for j in jobs if j]
            if not jobs:
                reason = 'nothing_to_voice'
            elif not settings.get('aiConsent'):
                reason = 'no_consent'
            elif not ai.available():
                reason = 'not_configured'
            else:
                ready = []
                for job in jobs:
                    if not h.ai_chat_budget(token):
                        reason = 'rate_limit'
                        break
                    ready.append(job)
                if ready:
                    with ThreadPoolExecutor(max_workers=len(ready)) as pool:
                        answers = list(pool.map(lambda j: board.ai_generate(fresh, j), ready))
                    lines = [dict(post=j['post'], cmt=j['cmt'], canonical=j['canonical'], text=a['text'], mode='ai')
                             for j, a in zip(ready, answers) if a['mode'] == 'ai']
                    reason = reason or next((a.get('reason') for a in answers if a['mode'] != 'ai'), None)
                    if lines:
                        stored = _internal(h, token, rid + '-voice', 'bd_voice', dict(lines=lines))
                        if stored and stored['result'].get('voiced'):
                            out = dict(out, state=stored['state'], revision=stored['revision'])
                            mode = 'ai'
                        elif not stored:
                            reason = 'superseded'
    raw, _, _ = store.read(token)
    return dict(state=out['state'], revision=out['revision'], result=out['result'], mode=mode, reason=reason,
                board=board.public(raw), cast=board.cast_public())
