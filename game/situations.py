"""Real-life situations with several points of view (v0.4).

A situation is read → chosen → confirmed → resolved, like the v0.1 events, but
authored per career (plugin SPEC['situations'] or situation_content.py). After a
decision the player sees how the customer, staff and bystanders experienced it,
so the same day can be understood from more than one side. Practice replays
never change money, reviews or relationships.
"""
from __future__ import annotations
import copy

MAX_COST = 80
MAX_REWARD = 60


def scripts(career: str) -> list[dict]:
    from .careers import PLUGINS
    from .situation_content import SITUATIONS
    mod = PLUGINS.get(career)
    rows = list(mod.SPEC.get('situations', [])) if mod else []
    return rows + [x for x in SITUATIONS if x['career'] == career]


def script(career: str, sid: str) -> dict | None:
    return next((x for x in scripts(career) if x['id'] == sid), None)


def initial() -> dict:
    return dict(situation=None, sit_history=[], sit_day=0)


def _npc(career: str, x: dict) -> str:
    return f'{career}_npc_{x.get("npc", 0) + 1:02d}'


def _start(s: dict, c: dict, career: str, x: dict, practice: bool) -> dict:
    s['seq'] += 1
    row = dict(id=f'sit-{s["seq"]}', script=x['id'], stage='open', read=[], choice=None, day=c['day'], practice=practice)
    c['ext']['situation'] = row
    return row


def director(s: dict, c: dict, career: str) -> None:
    """At most one real situation per game day, after the first finished task."""
    ext = c.get('ext')
    if not ext or not c['open'] or c['day_completed'] < 1 or ext['sit_day'] == c['day']:
        return
    current = ext['situation']
    if current and current['stage'] != 'resolved':
        return
    if c.get('event') and c['event'].get('stage') != 'resolved':
        return
    rows = [x for x in scripts(career) if x.get('min_day', 1) <= c['day']]
    if c['life']['mode'] == 'calm':
        rows = [x for x in rows if x.get('tone', 'gentle') == 'gentle'] or rows
    if not rows:
        return
    recent = [h['script'] for h in ext['sit_history'][-max(1, len(rows) - 1):]]
    fresh = [x for x in rows if x['id'] not in recent] or rows
    x = fresh[(c['day'] * 7 + len(ext['sit_history'])) % len(fresh)]
    ext['sit_day'] = c['day']
    row = _start(s, c, career, x, False)
    from . import engine as e
    e.log(s, c, 'situation', x['opening'], _npc(career, x), row['id'])


def action(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    from . import engine as e
    need = e.need
    ext = c['ext']
    if name == 'sit_practice':
        x = script(career, p.get('script'))
        need(x, 'Tình huống không thuộc nghề này.')
        cur = ext['situation']
        need(not cur or cur['stage'] == 'resolved' or cur['practice'], 'Đang có một tình huống thật. Xử lý xong rồi hãy diễn tập nhé.')
        _start(s, c, career, x, True)
        return dict(message='Diễn tập: ' + x['title'] + '. Không đổi tiền, đánh giá hay quan hệ.')
    row = ext['situation']
    need(row, 'Không có tình huống đang mở.')
    x = script(career, row['script'])
    need(x, 'Tình huống này không còn nữa.')
    if name == 'sit_read':
        fact = next((f for f in x['facts'] if f['id'] == p.get('fact')), None)
        need(fact, 'Không có dữ kiện này.')
        if fact['id'] not in row['read']:
            row['read'].append(fact['id'])
        if row['stage'] == 'open':
            row['stage'] = 'investigating'
        return dict(message=fact['text'])
    if name == 'sit_choose':
        need(row['stage'] in ('open', 'investigating', 'proposed'), 'Tình huống đã được quyết định.')
        opt = next((o for o in x['options'] if o['id'] == p.get('option')), None)
        need(opt, 'Phương án không có trong tình huống.')
        need(set(opt.get('requires', [])) <= set(row['read']), 'Xem đủ dữ kiện liên quan trước khi chọn phương án này.')
        row['choice'] = opt['id']
        row['stage'] = 'proposed'
        return dict(message=opt.get('preview', opt['label']))
    if name == 'sit_confirm':
        need(row['stage'] == 'proposed' and row['choice'], 'Chọn một phương án trước.')
        need(p.get('confirm') is True, 'Xác nhận cách xử lý trước nhé.')
        opt = next(o for o in x['options'] if o['id'] == row['choice'])
        npc = _npc(career, x)
        if not row['practice']:
            cost = min(MAX_COST, opt.get('cost', 0))
            if cost:
                e.money(s, c, -cost, 'Tình huống: ' + x['title'], row['id'], category='situation')
            reward = min(MAX_REWARD, opt.get('reward', 0))
            if reward:
                e.money(s, c, reward, 'Tình huống: ' + x['title'], row['id'], category='situation_reward')
            e.metric(c, 'situations')
            e.metric(c, 'situations_' + opt.get('quality', 'ok'))
            c['xp'] += 12 if opt.get('quality') == 'good' else 6
            if npc in e.NPC_INDEX:
                if opt.get('quality') != 'bad':
                    e.remember(s, c, npc, f'Bạn đã xử lý “{x["title"]}”: {opt["label"]}.', row['id'])
                else:
                    c['relationships'][npc] = max(0, c['relationships'].get(npc, 0) - 3)
                if opt.get('stars'):
                    post = e.add_feed(s, c, npc, opt.get('review', opt['outcome']), row['id'], opt['stars'], 'review')
                    post['situation'] = x['id']
                else:
                    e.add_feed(s, c, npc, 'Chuyện ở quán: ' + x['title'] + '. ' + opt['outcome'], row['id'], kind='story')
            ext['sit_history'] = (ext['sit_history'] + [dict(id=row['id'], script=x['id'], choice=opt['id'], day=c['day'], quality=opt.get('quality', 'ok'))])[-120:]
        row['stage'] = 'resolved'
        return dict(message=opt['outcome'], celebrate=opt.get('quality') == 'good')
    if name == 'sit_dismiss':
        need(row['stage'] == 'resolved' or row['practice'], 'Tình huống thật chưa xử lý xong.')
        ext['situation'] = None
        return dict(message='Đã cất tình huống vào sổ.')
    raise e.GameError('Thao tác tình huống không hợp lệ.')


def public(c: dict, career: str) -> dict | None:
    row = c.get('ext', {}).get('situation')
    if not row:
        return None
    x = script(career, row['script'])
    if not x:
        return None
    v = dict(row)
    v.update(title=x['title'], opening=x['opening'], tone=x.get('tone', 'gentle'), swap=x.get('swap'), npc=_npc(career, x),
             facts=[dict(id=f['id'], title=f['title'], source=f.get('source', ''), text=f['text'] if f['id'] in row['read'] else None) for f in x['facts']],
             options=[dict(id=o['id'], label=o['label'], requires=o.get('requires', []), cost=o.get('cost', 0), reward=o.get('reward', 0),
                           preview=o.get('preview')) for o in x['options']])
    if row['stage'] == 'resolved':
        opt = next(o for o in x['options'] if o['id'] == row['choice'])
        v.update(outcome=opt['outcome'], quality=opt.get('quality', 'ok'), perspectives=copy.deepcopy(opt.get('perspectives', [])),
                 lesson=x.get('lesson'))
    return v


def catalogue(career: str) -> list[dict]:
    return [dict(id=x['id'], title=x['title'], tone=x.get('tone', 'gentle'), swap=bool(x.get('swap'))) for x in scripts(career)]


def validate(c: dict, career: str) -> None:
    from .engine import need, integer, clean_text
    ext = c['ext']
    integer(ext.get('sit_day'), 0, 10**7)
    need(isinstance(ext.get('sit_history'), list) and len(ext['sit_history']) <= 120, 'Lịch sử tình huống sai.')
    for h in ext['sit_history']:
        need(isinstance(h, dict) and script(career, h.get('script')), 'Tình huống đã lưu không tồn tại.')
    row = ext.get('situation')
    if row is None:
        return
    need(isinstance(row, dict), 'Tình huống sai.')
    x = script(career, row.get('script'))
    need(x, 'Tình huống không thuộc nghề.')
    clean_text(row.get('id'), 80)
    need(row.get('stage') in ('open', 'investigating', 'proposed', 'resolved'), 'Bước tình huống sai.')
    need(isinstance(row.get('read'), list) and set(row['read']) <= {f['id'] for f in x['facts']}, 'Dữ kiện tình huống sai.')
    need(row.get('choice') in (None, *[o['id'] for o in x['options']]), 'Lựa chọn tình huống sai.')
    need(type(row.get('practice')) is bool, 'Cờ diễn tập sai.')
    integer(row.get('day'), 1, 10**7)
