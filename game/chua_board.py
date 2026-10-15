"""Explicit, revocable temple-card sharing; canonical saves and archives stay private.

Only published cards have projection rows. Public reads use the cursor index,
never saves or archives. Owner changes lock their session like Store commands;
imports/resets revoke in that same transaction, and deletion cascades via FK.
No backfill, public cache, or publication authority in exported save data.
"""
from __future__ import annotations

import json
import re

from . import chua
from .engine import GameError, need

MAX_CURSOR = 2**63 - 1
BAD = 'Tham số bảng lời chúc không hợp lệ.'
MISSING = 'Không tìm thấy bảng lời chúc của bạn.'


def parse_query(query: dict) -> dict:
    """Accept parse_qs lists, rejecting duplicate, blank and unknown fields."""
    need(set(query) <= {'scope', 'before', 'limit'} and all(len(v) == 1 for v in query.values()), BAD)
    out = {}
    for key, values in query.items():
        value = values[0]
        if key == 'scope':
            out[key] = value
        else:
            need(isinstance(value, str) and len(value) <= 19 and re.fullmatch(r'[0-9]+', value), BAD)
            out[key] = int(value)
    _query(**out)
    return out


def _query(scope='public', before=None, limit=20):
    need(isinstance(scope, str) and scope in ('public', 'mine'), BAD)
    need(type(limit) is int and 1 <= limit <= 50, BAD)
    need(before is None or type(before) is int and 0 <= before <= MAX_CURSOR, BAD)


def _session(store, db, token, *, lock=False, with_state=False):
    need(isinstance(token, str) and len(token) == 64, 'Phiên chơi không tồn tại.', 'session_missing')
    sid, _ = store._resolve(db, store.digest(token))
    fields = 'state' if lock or with_state else 'sid'
    row = db.execute(f'SELECT {fields} FROM sessions WHERE sid=?' + (' FOR UPDATE' if lock else ''), (sid,)).fetchone()
    need(row is not None, 'Phiên chơi không tồn tại.', 'session_missing')
    return sid, row


def _checked(card: dict) -> dict:
    """Validate archived/imported rows as strictly as current canonical cards."""
    need(isinstance(card, dict) and type(card.get('day')) is int, MISSING)
    chua.validate(dict(journey=dict(life_day=card['day'], chua=dict(
        v=chua.VERSION, day=card['day'], n=1, did=['nguyen'], cards=[card]))))
    return {key: card[key] for key in chua.CARD_KEYS}


def _publish(db, sid: str, card: dict):
    card = _checked(card)
    db.execute('INSERT INTO chua_public_cards(sid,card_id,card) VALUES(?,?,?) '
               'ON CONFLICT (sid,card_id) DO NOTHING',
               (sid, card['id'], json.dumps(card, ensure_ascii=False, separators=(',', ':'))))


def command_commit(db, sid: str, action: str, after: dict, result: dict):
    """Run inside either Store commit path, before save and receipt commit."""
    if action in ('import_save', 'reset_all'):
        db.execute('DELETE FROM chua_public_cards WHERE sid=?', (sid,))
    elif action == 'jr_chua_do' and (result or {}).get('chua_card', {}).get('public') is True:
        card_id = result['chua_card']['id']
        card = next((c for c in after['journey']['chua']['cards'] if c['id'] == card_id), None)
        need(card is not None, MISSING)
        _publish(db, sid, card)


def page(store, token: str, *, scope='public', before=None, limit=20) -> dict:
    _query(scope, before, limit)
    with store.connect() as db:
        if scope == 'mine':
            # A new card can move the oldest live row into the archive. Keep
            # both halves and visibility flags in one snapshot so positions
            # never shift or duplicate within a page; no writer row lock.
            db.begin()
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        sid, session = _session(store, db, token, with_state=scope == 'mine')
        if scope == 'public':
            # 📜 since the wish garden shows these cards (game/chua_wish.py), what reports or an admin took off the
            # trees is off this older board too (an older client still reads it)
            rows = list(db.execute('SELECT p.position,p.card FROM chua_public_cards p WHERE p.position<? AND NOT EXISTS '
                                   '(SELECT 1 FROM chua_card_marks m WHERE m.sid=p.sid AND m.card_id=p.card_id '
                                   "AND m.status<>'live') ORDER BY p.position DESC LIMIT ?",
                                   (before if before is not None else MAX_CURSOR, limit + 1)))
            visible = rows[:limit]
            return dict(rows=[_tree(dict(json.loads(r['card']), public=True, position=r['position'])) for r in visible],
                        before=visible[-1]['position'] if len(rows) > limit else None)
        state = store.parse_state(session['state'], sid)
        live = (state.get('journey', {}).get('chua') or {}).get('cards', [])
        stored = db.execute("SELECT COALESCE(MAX(seq)+1,0) FROM archive WHERE sid=? AND career='' AND kind='chua.cards'",
                            (sid,)).fetchone()[0]
        total = stored + len(live)
        end = min(total, before) if before is not None else total
        start = max(0, end - limit)
        history = [dict(pos=r['seq'], row=json.loads(r['row'])) for r in db.execute(
            "SELECT seq,row FROM archive WHERE sid=? AND career='' AND kind='chua.cards' AND seq>=? AND seq<? ORDER BY seq",
            (sid, start, min(end, stored)))]
        history.extend(dict(pos=pos, row=live[pos-stored]) for pos in range(max(start, stored), end))
        history.reverse()
        rows = []
        for item in history:
            try:
                card = _checked(item['row'])
            except GameError:
                continue  # malformed imported archive rows cannot become public
            rows.append(dict(card, position=item['pos']))
        ids = [r['id'] for r in rows]
        shared = {r['card_id'] for r in db.execute(
            'SELECT card_id FROM chua_public_cards WHERE sid=? AND card_id=ANY(?)', (sid, ids))} if ids else set()
    for row in rows:
        row['public'] = row['id'] in shared
        _tree(row)
    return dict(rows=rows, before=start if start > 0 else None, total=total)


def _tree(row: dict) -> dict:
    """📜 the wish tree a card hangs on once shared (game/chua_wish.py card_tree; the garden says where it is)."""
    from .chua_wish import card_tree
    row['tree'] = card_tree(row.get('recipient'), row.get('blessing'))
    return row


def set_visibility(store, token: str, payload: dict) -> dict:
    need(isinstance(payload, dict) and {'id', 'public'} <= set(payload) <= {'id', 'public', 'position'}, BAD)
    card_id, public = payload['id'], payload['public']
    need(isinstance(card_id, str) and re.fullmatch(r'[0-9a-f]{32}', card_id), BAD)
    need(type(public) is bool, BAD)
    if 'position' in payload:
        need(type(payload['position']) is int and 0 <= payload['position'] <= MAX_CURSOR, BAD)
    with store.connect() as db:
        db.begin()
        sid, row = _session(store, db, token, lock=True)
        state = store.parse_state(row['state'], sid)
        recent = (state.get('journey', {}).get('chua') or {}).get('cards', [])
        card = next((c for c in recent if isinstance(c, dict) and c.get('id') == card_id), None)
        if card is None:
            if 'position' in payload:
                archived = db.execute("SELECT row FROM archive WHERE sid=? AND career='' AND kind='chua.cards' AND seq=?",
                                      (sid, payload['position'])).fetchone()
            else:
                # Old links may lack a position: restrict the existing composite
                # index to this owner's temple cards, never the global archive.
                archived = db.execute("SELECT row FROM archive WHERE sid=? AND career='' AND kind='chua.cards' "
                                      "AND row::jsonb->>'id'=? ORDER BY seq DESC LIMIT 1", (sid, card_id)).fetchone()
            card = json.loads(archived['row']) if archived is not None else None
        need(isinstance(card, dict) and card.get('id') == card_id, MISSING)
        card = _checked(card)
        if public:
            _publish(db, sid, card)
        else:
            db.execute('DELETE FROM chua_public_cards WHERE sid=? AND card_id=?', (sid, card_id))
    return dict(id=card_id, public=public)
