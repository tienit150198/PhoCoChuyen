"""💾 Nhập bản lưu: who may restore a backup, and which backups (09/10: cloned and edited saves were imported for xu).

* A save that belongs to an account (registered user) never imports: its progress already lives on the server, and
  "Đăng nhập" brings it to any device. Only an operator (ADMIN_USERS, player_feedback.is_admin) may still restore one;
  server.py tells the store so by setting payload["admin_restore"] itself (a client's own value is dropped).
* A guest save imports only a backup this server exported (an HMAC over the save's own id, its revision and the
  sha256 of the state, under SAVE_SIGN_SECRET), never one older than the save it replaces (revision), and never one
  holding more xu than the save it replaces (wallet + bank + savings + funds: kpi.xu). An edited file, a clone into a
  fresh save and "export, gamble, import back" are all refused.
* MNL_IMPORT_GUARD_OFF=1 (tests/__init__.py only) keeps the old behaviour for the tests that build a save by import.

The signature lives in the export envelope (key "sign"), outside the state: no save key is added.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys

from .engine import GameError
from . import kpi

_warned = False


def enabled() -> bool:
    return os.environ.get('MNL_IMPORT_GUARD_OFF', '') != '1'


def _secret() -> bytes:
    """SAVE_SIGN_SECRET; else a key derived from DATABASE_URL (server-side only, the same on every worker and
    across restarts), else a fixed local key (a single-player local server: nothing to protect)."""
    global _warned
    own = os.environ.get('SAVE_SIGN_SECRET', '').strip()
    if own:
        return own.encode()
    if not _warned:
        _warned = True
        print('[import] SAVE_SIGN_SECRET is not set: signing exports with a key derived from DATABASE_URL',
              file=sys.stderr, flush=True)
    base = os.environ.get('DATABASE_URL', '') or 'mot-ngay-lam-nghe/local'
    return hashlib.sha256(('save-sign:' + base).encode()).digest()


def _plain(v):
    """The value a JSON round trip through a browser gives back: 3.0 comes back as 3."""
    if type(v) is float and v.is_integer():
        return int(v)
    if type(v) is dict:
        return {k: _plain(x) for k, x in v.items()}
    if type(v) is list:
        return [_plain(x) for x in v]
    return v


def digest(state) -> str:
    text = json.dumps(_plain(state), sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def save_tag(sid: str) -> str:
    """Which save a backup came from, without the save id itself in the file."""
    return hashlib.sha256(('save:' + str(sid)).encode()).hexdigest()[:16]


def _mac(tag: str, revision: int, dig: str) -> str:
    return hmac.new(_secret(), f'{tag}|{int(revision)}|{dig}'.encode(), hashlib.sha256).hexdigest()


def sign(sid: str, revision: int, state) -> dict:
    """The "sign" block of an export (GET /api/save/export)."""
    tag = save_tag(sid)
    return dict(save=tag, revision=int(revision), mac=_mac(tag, revision, digest(state)))


def money(state) -> int:
    return kpi.xu(state) or 0


def check(envelope: dict, candidate, current: dict, sid: str, revision: int, *, account: bool, admin: bool) -> None:
    """Raise GameError unless this import is allowed (see the module docstring). `candidate` is the backup's state
    as sent, before migration; `current` the save it would replace, at `revision`."""
    if admin or not enabled():
        return
    if account:
        raise GameError('Tài khoản đã lưu tiến trình trên máy chủ, không cần nhập bản lưu. '
                        'Đăng nhập trên máy mới là chơi tiếp.', 'import_account')
    sig = envelope.get('sign')
    ok = (type(sig) is dict and type(sig.get('save')) is str and type(sig.get('revision')) is int
          and type(sig.get('mac')) is str and isinstance(candidate, dict))
    if ok:
        ok = hmac.compare_digest(sig['mac'], _mac(sig['save'], sig['revision'], digest(candidate)))
    if not ok:
        raise GameError('Tệp lưu không phải bản xuất nguyên vẹn từ máy chủ, không nhập được.', 'import_unsigned')
    if sig['revision'] < revision:
        raise GameError('Bản lưu này cũ hơn tiến trình hiện tại, không nhập được.', 'import_older')
    if money(candidate) > money(current):
        raise GameError('Bản lưu này giữ nhiều xu hơn tiến trình hiện tại, không nhập được. '
                        'Muốn chơi trên máy khác, hãy tạo tài khoản rồi đăng nhập ở máy đó.', 'import_richer')


def log(who: str, outcome: str, revision=None, xu=None) -> None:
    """One stderr line per import attempt: `[import] uid=<username>|guest=<save tag> rev=… xu=… ok|refused:<code>`."""
    print(f'[import] {who} rev={revision} xu={xu} {outcome}', file=sys.stderr, flush=True)
