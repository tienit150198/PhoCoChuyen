"""Current account display names, resolved in batches without rewriting chat history."""
from .auth import clean_name, pid_of


async def names_of(chat, pids):
    ids = {pid for pid in pids if pid and pid != 'admin'}
    missing = [pid for pid in ids if chat.names.get(pid) is None]
    if not missing:
        return {pid: chat.names.get(pid) or '' for pid in ids}
    known = {p.pid: p.sid for p in chat.hub.players.values()}
    for player in chat.hub.players.values():
        known.update({pid: friend['sid'] for pid, friend in player.friends.items()})
    for start in range(0, len(missing), 200):
        part = missing[start:start + 200]
        got = {}
        sids = [known[pid] for pid in part if pid in known]
        if sids:
            rows = await chat.db.fetch(f"SELECT sid, display FROM accounts WHERE sid IN ({','.join('?' * len(sids))})", sids)
            got.update({pid_of(r['sid']): clean_name(r['display']) for r in rows})
        unknown = [pid for pid in part if pid not in known]
        if unknown:
            # Registration creates the public profile mapping. Use its primary key instead
            # of hashing every account for each cold history page or unknown/deleted pid.
            rows = await chat.db.fetch('SELECT p.pid, a.display FROM profiles p JOIN accounts a ON a.sid=p.sid '
                                       f"WHERE p.pid IN ({','.join('?' * len(unknown))})", unknown)
            got.update({r['pid']: clean_name(r['display']) for r in rows})
        for pid in part:
            # A rename notification may have populated this entry while SELECT was in flight.
            if chat.names.get(pid) is None:
                chat.names.put(pid, got.get(pid, ''))
    return {pid: chat.names.get(pid) or '' for pid in ids}
