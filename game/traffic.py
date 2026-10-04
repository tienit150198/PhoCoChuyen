"""Server-issued traffic-light crossings shared by courier and counter rides.

Approaching/refreshing a light never charges. Only an explicit cross with the issued
token evaluates the server clock. A crossing key has one receipt for the whole ride;
clients cannot supply a signal, timestamp or fine. Callers validate route checkpoints.
"""
import copy
import math
import secrets
from .careers import kit

FINE=12
RED_GRACE=1.0
MAX_CROSSINGS=40
LIT=frozenset(((1,1),(3,1),(5,1),(1,3),(3,3),(5,3),(3,2),(2,2),(4,2)))


def fresh():return dict(challenge=None,receipts=[])


def signal(challenge, now=None):
    phase=((kit.now() if now is None else now)+challenge['offset'])%16
    return ('green' if phase<6 else 'yellow' if phase<8 else 'red') if challenge['axis']=='y' else ('red' if phase<8 else 'green' if phase<14 else 'yellow')


def issue(d,key,offset,axis):
    kit.need(isinstance(key,str) and 1<=len(key)<=100 and type(offset) is int and 0<=offset<16 and axis in ('x','y'),'Ngã tư không hợp lệ.')
    ch=d['challenge']
    if ch and ch['key']==key:return copy.deepcopy(ch)
    old=next((r for r in d['receipts'] if r['key']==key),None)
    kit.need(old or len(d['receipts'])<MAX_CROSSINGS,'Đã đi đủ ngã tư của lượt này. Hoàn tất chặng rồi đi tiếp nhé.')
    d['challenge']=dict(key=key,token=old['token'] if old else secrets.token_hex(16),issued=round(kit.now(),3),offset=offset,axis=axis)
    return copy.deepcopy(d['challenge'])


def cross(d,token):
    ch=d['challenge']
    kit.need(ch and isinstance(token,str) and token==ch['token'],'Đèn đã đổi lượt. Xem đèn ở ngã tư hiện tại trước khi đi.')
    old=next((r for r in d['receipts'] if r['key']==ch['key']),None)
    if old:return dict(old,duplicate=True)
    now=kit.now();color=signal(ch,now)
    phase=(now+ch['offset'])%16
    red_age=phase-(8 if ch['axis']=='y' else 0)
    grace=color=='red' and 0<=red_age<RED_GRACE
    row=dict(key=ch['key'],token=token,at=round(now,3),signal=color,fine=FINE if color=='red' and not grace else 0,grace=grace)
    d['receipts'].append(row)
    return dict(row,duplicate=False)


def public(d):
    out=copy.deepcopy(d)
    out['server_now']=round(kit.now(),3);out['fine']=FINE
    if out['challenge']:out['challenge']['signal']=signal(out['challenge'])
    return out


def validate(d):
    need=kit.need;msg='Biên nhận giao thông không hợp lệ.'
    need(isinstance(d,dict) and set(d)=={'challenge','receipts'},msg)
    def base(x):
        need(isinstance(x,dict) and isinstance(x.get('key'),str) and 1<=len(x['key'])<=100,msg)
        token=x.get('token');need(isinstance(token,str) and len(token)==32 and all(k in '0123456789abcdef' for k in token),msg)
    def stamp(x):need(type(x) in (int,float) and math.isfinite(x) and x>=0,msg)
    ch=d['challenge']
    if ch is not None:
        base(ch);need(set(ch)=={'key','token','issued','offset','axis'},msg);stamp(ch['issued'])
        need(type(ch['offset']) is int and 0<=ch['offset']<16 and ch['axis'] in ('x','y'),msg)
    rows=d['receipts'];need(isinstance(rows,list) and len(rows)<=MAX_CROSSINGS,msg)
    keys=set()
    for r in rows:
        base(r);need(set(r)=={'key','token','at','signal','fine','grace'},msg);stamp(r['at'])
        need(r['signal'] in ('red','yellow','green') and type(r['fine']) is int and type(r['grace']) is bool and (not r['grace'] or r['signal']=='red') and r['fine']==(FINE if r['signal']=='red' and not r['grace'] else 0),msg)
        need(r['key'] not in keys,msg);keys.add(r['key'])
