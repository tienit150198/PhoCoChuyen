"""Synthetic accounts only, inside the disposable capacity database."""
import copy, hashlib, json, os, secrets, sys, time
sys.path.insert(0, '/app')
from game import engine, storage, social, push, admin_stats

assert os.environ['DATABASE_URL'].endswith('@mnl-cap-pg:5432/capacity')
store = storage.Store('/tmp/capacity', story=False)
social.ensure(store); push.ensure(store); admin_stats.ensure(store)
base = engine.new_state()
base['current'] = 'milk_tea'
for cid, c in base['careers'].items():
    c['started'] = True
    npc = next(k for k,v in engine.NPC_INDEX.items() if v['career_id'] == cid)
    engine.add_feed(base, c, npc, 'Chuyen thu tai tong hop, khong phai du lieu nguoi choi.', 'test')
engine.validate_state(base)
small = storage.serialize(base, full=True)
large = copy.deepcopy(base)
for cid,c in large['careers'].items():
    post = c['feed'][0]
    post['text'] = 'Synthetic capacity test history. ' * 22
    npc = next(k for k,v in engine.NPC_INDEX.items() if v['career_id'] == cid)
    post['comments'] = [dict(author='Fixture',text='Synthetic comment. '*22,day=1,npc=npc)]
    c['feed'] = [dict(copy.deepcopy(post), id=f'capacity-{cid}-{j}') for j in range(80)]
engine.validate_state(large)
large_text = storage.serialize(large, full=True)
players=[]
now=time.time()
with store.connect() as db:
    for i in range(1000):
        token=secrets.token_hex(32); sid=hashlib.sha256(('acct:'+token).encode()).hexdigest(); csrf=secrets.token_hex(24)
        heavy=i%10==0
        state=large_text if heavy else small
        db.execute('INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)',(sid,csrf,state))
        db.execute('INSERT INTO leaderboard_players(sid,name,updated) VALUES(?,?,?)',(sid,f'Test {i}',now))
        db.execute("INSERT INTO stat_births(sid,day) VALUES(?,'2026-01-01') ON CONFLICT(sid) DO UPDATE SET day=excluded.day",(sid,))
        db.execute('INSERT INTO accounts(username,display,pw,sid) VALUES(?,?,?,?)',(f'capacity_{i}',f'Test {i}','disabled-test-only',sid))
        db.execute('INSERT INTO logins(token,sid,csrf) VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),sid,csrf))
        players.append(dict(index=i,token=token,csrf=csrf,pid=hashlib.sha256(('pid:'+sid).encode()).hexdigest()[:16],revision=0,heavy=heavy,
                            post=(large if heavy else base)['careers']['milk_tea']['feed'][0]['id']))
os.makedirs('/result',exist_ok=True)
with open('/result/players.json','w') as f: json.dump(players,f)
report=dict(players=len(players),heavy_players=100,small_bytes=len(small.encode()),large_bytes=len(large_text.encode()),careers=len(base['careers']),python=sys.version.split()[0],build=engine.BUILD)
with open('/result/fixture.json','w') as f: json.dump(report,f,indent=2)
print(json.dumps(report),flush=True)
store.close_pool()
