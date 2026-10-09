"""One finish for a common home, with each purchaser retaining their own skin licenses.

The homeowner's layout is authoritative. A resident's paint command updates that layout and
their own payment/receipt atomically, under both session locks. Furniture never changes owner.
The context is private to this transaction; ordinary standalone reducers keep their behavior.
"""
from __future__ import annotations

from contextvars import ContextVar
import json

from . import archive as ar, deco as dc, deco_mate as dm, marriage as mr
from . import leaderboard as lb, retention as rt
from .engine import GameError, migrate_state, public_state, tree_copy, validate_state

SKINS = ContextVar('shared_home_skins', default=None)


def notify(db, sid: str, action: str) -> None:
    if action.startswith(('jr_deco_', 'jr_reno_', 'jr_home_')) or action == 'jr_wd_deco':
        db.execute('SELECT pg_notify(?, ?)', ('mnl_live', json.dumps(dict(t='home_changed', sid=sid), separators=(',', ':'))))


def command(store, h, who, request_id, expected, career, action, payload, internal, fingerprint):
    """Skin command route: actor receipt, purchase and owner mirror share one commit.

    Locks follow family.act's order: sorted sessions, then the current couple row. Holding
    the owner session prevents a move/sale racing the residency check; holding the couple
    prevents a divorce racing it. Other owner commands use revision guards and safely retry.
    """
    from .storage import Conflict, _archive_rows, _receipt, _write_archive, serialize

    with store.connect() as db:
        sid, _ = store._resolve(db, h)
        snapshot = mr._bond(db, sid)
    who[0] = sid
    members = sorted({sid, mr._other(snapshot, sid)} if snapshot and snapshot['status'] == 'married' else {sid})

    def run(db):
        store._patient(db)
        rows = {member: db.execute('SELECT revision,state FROM sessions WHERE sid=? FOR UPDATE', (member,)).fetchone()
                for member in members}
        row = rows[sid]
        if not row:
            raise GameError('Phiên chơi không tồn tại.', 'session_missing')
        receipt = db.execute('SELECT request_hash,result FROM receipts WHERE sid=? AND request_id=?', (sid, request_id)).fetchone()
        if receipt:
            return store._replay(sid, dict(row, rhash=receipt['request_hash'], rresult=receipt['result']), fingerprint), None
        if expected is not None and row['revision'] != expected:
            raise Conflict('Tiến trình đã thay đổi ở tab khác. Đã đồng bộ lại; hãy xem trạng thái trước khi thao tác tiếp.', 'revision_conflict')

        states, cuts = {}, {}
        for member, saved in rows.items():
            if not saved:
                continue
            with ar.collect() as box:
                state = store.parse_state(saved['state'], member)
                before = dict(state.get('careers') or {})
                states[member] = migrate_state(state, owned=True)
            cuts[member] = _archive_rows(box, before, states[member], '')
        state = states[sid]
        c = mr._row(db, 'SELECT * FROM couples WHERE id=? FOR UPDATE', (snapshot['id'],)) if snapshot else None
        bond = mr._bond(db, sid)
        # The membership was selected before taking locks. A changed bond requires a fresh command.
        if bond and bond['status'] == 'married' and (not c or bond['id'] != c['id']):
            raise Conflict('Gia đình vừa thay đổi. Tải lại rồi thử nhé.', 'revision_conflict')
        shared = bool(c and c['status'] == 'married' and bond and bond['id'] == c['id']
                      and mr._other(c, sid) in states
                      and dm.same_home(state['journey'], states[mr._other(c, sid)]['journey'], c['id']))
        if dc.place(state['journey'])['where'] == 'shared' and not shared:
            raise GameError('Hai bạn không còn cùng ở căn nhà này. Tải lại nhà rồi thử nhé.', 'not_same_home')
        owner_sid = (sid if dc.place(state['journey'])['where'] == 'own' else mr._other(c, sid)) if shared else None
        finishes = dc.layout(states[owner_sid])['skins'] if owner_sid else None
        context = SKINS.set(tree_copy(finishes) if finishes is not None else None)
        try:
            raw, result, serialized, cut, board, steps = store._compute(sid, row['state'], career, action,
                                                                       tree_copy(payload), internal, row['revision'])
        finally:
            SKINS.reset(context)
        # Journey maintenance can clear an inconsistent imported/stale sharing marker.
        # Its new private room must never be mirrored back into the previously shared home.
        if shared and not dm.same_home(raw['journey'], states[mr._other(c, sid)]['journey'], c['id']):
            raise GameError('Chỗ ở vừa thay đổi. Tải lại nhà rồi thử nhé.', 'not_same_home')
        revision = row['revision'] + 1
        db.execute('UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=?', (serialized, revision, sid))
        from . import couple
        couple.commit_holds(db, sid, state, raw)   # 💳 a joint-card hold this command made is settled with the save
        _write_archive(db, sid, cut)
        if board[1]:
            lb.write(db, sid, board[0])
        if steps[0]:
            rt.write_marks(db, sid, steps[0], steps[1])
        if owner_sid and owner_sid != sid and not result.get('duplicate'):
            owner = states[owner_sid]
            _, decor, _ = dc._ensure(owner)
            decor['skins'] = tree_copy(dc.layout(raw)['skins'])
            validate_state(owner)
            mr.validate_save(owner)
            db.execute('UPDATE sessions SET state=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE sid=?',
                       (serialize(owner, None, True), owner_sid))
            _write_archive(db, owner_sid, cuts[owner_sid])
        db.execute('INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?)',
                   (sid, request_id, fingerprint, _receipt(result)))
        notify(db, sid, action)
        return dict(raw=raw, revision=revision, result=result, replayed=False), (board, steps)

    out, metrics = store.transaction(run)
    if metrics:
        board, steps = metrics
        lb.remember(sid, out['revision'], board[0])
        if steps[0]:
            rt.emit_marks(sid, *steps)
        out['state'] = public_state(out.pop('raw'), migrated=True)
    return out
