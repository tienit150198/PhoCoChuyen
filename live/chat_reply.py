"""Resolve reply IDs at the read boundary; never cache another message's text."""
from .protocol import LiveError
from .player_names import names_of
from . import honours

MAX_ID = 2 ** 63 - 1
QUOTE_LEN = 160
VIEWER_BATCH = 100


def reply_id(frame):
    value = frame.get('reply_to')
    if 'reply_to' in frame and (type(value) is not int or not 0 < value <= MAX_ID):
        raise LiveError('bad', 'Yêu cầu trả lời không hợp lệ.')
    return value


async def project(chat, player, messages):
    """One batched source read per page, including current membership and personal visibility.

    Buffer frames contain only reply_to; projected copies alone carry quote text. Missing,
    recalled, moderated, blocked, hidden and cleared sources all have the same tombstone.
    """
    return (await project_many(chat, [player], messages))[player.pid]


async def project_many(chat, players, messages):
    """Read all source IDs for up to 100 recipients per query, then render without awaits.

    An invalidation during any read makes this in-flight projection unavailable. This
    prevents a delayed SELECT from restoring text after a deletion/hide event was sent.
    """
    ids = sorted({m['reply_to'] for m in messages if m.get('reply_to') and not m.get('del')})
    sources = {p.pid: {} for p in players}
    epoch = chat.reply_epoch
    if ids:
        personal = ''
        if chat.del_ok:
            personal = ('AND NOT EXISTS (SELECT 1 FROM chat_hides h WHERE h.pid=v.pid AND h.msg=m.id) '
                        'AND NOT EXISTS (SELECT 1 FROM chat_clears k WHERE k.pid=v.pid AND k.channel=m.channel AND k.upto>=m.id) ')
        for start in range(0, len(players), VIEWER_BATCH):
            batch = players[start:start + VIEWER_BATCH]
            values = ','.join('(?, ?)' for _ in batch)
            params = [value for p in batch for value in (p.pid, p.sid)]
            rows = await chat.db.fetch(
                'SELECT v.pid AS viewer, m.id, m.channel, m.pid, m.name, m.text FROM chat_messages m '
                f'CROSS JOIN (VALUES {values}) AS v(pid, sid) WHERE m.hidden=0 AND m.deleted=0 '
                "AND (m.channel='town' OR EXISTS (SELECT 1 FROM chat_members cm WHERE cm.channel=m.channel AND cm.pid=v.pid)) "
                'AND NOT EXISTS (SELECT 1 FROM blocks b WHERE (b.pid=v.pid AND b.target=m.pid) OR (b.target=v.pid AND b.pid=m.pid)) '
                "AND NOT EXISTS (SELECT 1 FROM marriage_blocks b WHERE (b.sid=v.sid AND "
                "substring(encode(sha256(convert_to('pid:' || b.target,'UTF8')),'hex'),1,16)=m.pid) OR (b.target=v.sid AND "
                "substring(encode(sha256(convert_to('pid:' || b.sid,'UTF8')),'hex'),1,16)=m.pid)) "
                + personal + f"AND m.id IN ({','.join('?' * len(ids))})", (*params, *ids))
            for r in rows:
                sources[r['viewer']][int(r['id'])] = r
    names = await names_of(chat, [m.get('pid') for m in messages] +
                           [source['pid'] for visible in sources.values() for source in visible.values()])
    quoted = [source['pid'] for visible in sources.values() for source in visible.values()]
    tt = await honours.of_app(chat.app).of(quoted) if quoted else {}   # 🏅 the quoted author's titles now (cached)
    if epoch != chat.reply_epoch:
        sources = {p.pid: {} for p in players}
    return {p.pid: _render(p, messages, sources[p.pid], names, tt) for p in players}


def _render(player, messages, sources, names, tt=None):
    out = []
    for message in messages:
        result = dict(message)
        if names.get(result.get('pid')):
            result['name'] = names[result['pid']]
        mid = result.pop('reply_to', None)
        result.pop('reply', None)
        if mid and not result.get('del'):
            source = sources.get(mid)
            if source and source['channel'] == result['ch'] and source['pid'] not in player.hidden:
                result['reply'] = dict(id=mid, pid=source['pid'], name=names.get(source['pid']) or source['name'], text=source['text'][:QUOTE_LEN])
                if (tt or {}).get(source['pid']):
                    result['reply']['tt'] = tt[source['pid']]
            else:
                result['reply'] = dict(id=mid, unavailable=True)
        out.append(result)
    return out


async def validate(chat, player, channel, mid):
    if mid is None:
        return
    projected = await project(chat, player, [dict(ch=channel, reply_to=mid)])
    if projected[0]['reply'].get('unavailable'):
        raise LiveError('gone', 'Tin nhắn gốc không còn hoặc bạn không xem được.')
