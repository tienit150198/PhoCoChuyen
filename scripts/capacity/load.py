"""Authenticated localhost load generator. Four client processes outside server CPU quotas.
No production endpoints, no real player data. Deadline schedule records missed work rather
than silently reducing the requested rate when a player has an outstanding command.
Movement latency: send to receive on same-process peers (including self), matched by pid/y.
"""
import argparse, asyncio, collections, json, math, multiprocessing as mp, os, random, sys, time, subprocess, urllib.request
from pathlib import Path
import aiohttp, psutil
from websockets.asyncio.client import connect

ROOT=Path(__file__).resolve().parent
API=os.environ.get('CAP_API','http://127.0.0.1:18893'); LIVE=os.environ.get('CAP_LIVE','ws://127.0.0.1:18894/live'); ORIGIN='http://127.0.0.1:18893'
assert API in ('http://127.0.0.1:18893','http://mnl-cap-api:8765')
assert LIVE in ('ws://127.0.0.1:18894/live','ws://mnl-cap-live:8770/live')

def pct(v):
    v=sorted(v)
    return dict(n=len(v),p50=round(v[int((len(v)-1)*.5)],2),p95=round(v[int((len(v)-1)*.95)],2),p99=round(v[int((len(v)-1)*.99)],2),max=round(v[-1],2)) if v else dict(n=0)

def sample_span(a, b):
    # Use the same clock for average and peak CPU when the VM adjusts wall time.
    return b.get('mono', b['at']) - a.get('mono', a['at'])

def clockword():
    n=int(time.perf_counter()*1e6); out=''
    while n: out=chr(97+n%26)+out; n//=26
    return out
def wordclock(word):
    n=0
    for c in word: n=n*26+ord(c)-97
    return n/1e6

async def clients(part, args, ready, go, q):
    stats=collections.Counter(); errors=collections.Counter(); lat=collections.defaultdict(list)
    rooms={}; moved={}; tasks=[]; commands=[]; socks=[]; users=[]; active=False; deadline=0
    process=psutil.Process(); cpu0=process.cpu_times(); start0=time.monotonic(); initial_lag=[]
    async def watch_loop():
        last_report=time.monotonic()
        while True:
            before=time.monotonic(); await asyncio.sleep(.1)
            if active: lat['generator_loop_lag'].append(max(0,(time.monotonic()-before-.1)*1000))
            if active and time.monotonic()-last_report>=30:
                print(json.dumps(dict(phase='progress',worker=os.getpid(),started=stats['commands_started'],ok=stats['commands_ok'],missed=stats['command_slots_missed'],errors=dict(errors),recent_command_ms=pct(lat['command_all'][-1000:]))),flush=True)
                last_report=time.monotonic()
    tasks.append(asyncio.create_task(watch_loop()))
    def remember(user,data):
        user['revision']=data.get('revision',user['revision'])
        for _,h in data.get('delta',{}).get('keys',[]): user['known'].add(h)
        if len(user['known'])>8000: user['known']=set(h for _,h in data.get('delta',{}).get('keys',[]))
    async def read_socket(ws,user):
        try:
            async for raw in ws:
                now=time.monotonic(); f=json.loads(raw)
                if active: stats['ws_frames']+=1; stats['ws_bytes']+=len(raw.encode() if isinstance(raw,str) else raw)
                if f.get('t')=='error': errors['ws:'+str(f.get('ref'))+':'+str(f.get('code'))]+=1
                if f.get('t')=='town' and active:
                    for ev in f.get('ev',[]):
                        if ev['k']=='mv':
                            stats['move_deliveries']+=1
                            at=moved.get((ev['pid'],ev.get('y')))
                            if at is not None and 0<=now-at<4:
                                lat['move'].append((now-at)*1000)
                                if ev['pid']!=user['pid']: lat['move_peer'].append((now-at)*1000)
                if f.get('t')=='msg' and active:
                    stats['chat_deliveries']+=1
                    # Text carries the actual sending clock from this same machine.
                    try:
                        prefix,stamp=f['text'].split(':')
                        if prefix=='Capacity' and stamp.isalpha(): lat['chat'].append((time.perf_counter()-wordclock(stamp))*1000)
                    except (KeyError,ValueError): pass
        except Exception as e:
            if active: errors['socket:'+type(e).__name__]+=1
        finally:
            if active: stats['unexpected_socket_close']+=1
    timeout=aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout,connector=aiohttp.TCPConnector(limit=180),auto_decompress=True) as session:
        sem=asyncio.Semaphore(8)
        async def boot(user):
            nonlocal users
            await asyncio.sleep(user['order']/args.ramp)
            async with sem:
                user=dict(user,known=set()); user['headers']={'Cookie':'mnl_session='+user['token'],'Origin':ORIGIN,'Host':'127.0.0.1:18893','X-Game-CSRF':user['csrf'],'X-Game-Delta':'1','Accept-Encoding':'gzip'}
                t=time.monotonic()
                try:
                    if args.period:
                        async with session.get(API+'/api/state',headers=user['headers']) as r:
                            data=await r.json(); stats['bootstrap_status_'+str(r.status)]+=1
                            if r.status!=200: raise RuntimeError('bootstrap:'+str(r.status))
                            remember(user,data)
                    ws=await connect(LIVE,origin=ORIGIN,additional_headers={'Cookie':'mnl_session='+user['token']},compression=None,open_timeout=30,ping_interval=None,max_queue=128)
                    await ws.send(json.dumps(dict(t='hello',v=1)))
                    f=json.loads(await asyncio.wait_for(ws.recv(),30))
                    if f.get('t')!='welcome': raise RuntimeError('welcome')
                    await ws.send(json.dumps(dict(t='town_in',map='iso-town-v1',x=6,y=6,direction='se',look={},g='female')))
                    while True:
                        f=json.loads(await asyncio.wait_for(ws.recv(),30))
                        if f.get('t')=='error': raise RuntimeError(str(f))
                        if f.get('t')=='town_room': break
                    user['pid']=f['me']; rooms[user['pid']]=f['room']
                    await ws.send(json.dumps(dict(t='join',ch='town')))
                    socks.append(ws); users.append((ws,user)); stats['opened']+=1
                    lat['connect'].append((time.monotonic()-t)*1000)
                    tasks.append(asyncio.create_task(read_socket(ws,user)))
                except Exception as e:
                    errors['boot:'+type(e).__name__+':'+str(e)[:100]]+=1
        await asyncio.gather(*(boot(u) for u in part))
        ready.put(dict(open=stats['opened'],errors=dict(errors)))
        while not go.is_set(): await asyncio.sleep(.05)
        active=True; started=time.time(); begin=time.monotonic(); deadline=begin+args.duration
        async def move(ws,user):
            step=0; nxt=begin+(user['index']%101)/101*.3
            while time.monotonic()<deadline:
                await asyncio.sleep(max(0,nxt-time.monotonic()))
                if time.monotonic()>=deadline: break
                step+=1; phase=step%132; y=round(6+.5*(phase if phase<=66 else 132-phase),3)
                moved[(user['pid'],y)]=time.monotonic()
                try: await ws.send(json.dumps(dict(t='town_mv',x=6,y=y,direction='se' if phase<66 else 'nw'))); stats['moves_sent']+=1
                except Exception as e: errors['move_send:'+type(e).__name__]+=1; break
                # The real UI polls every 100ms with a 270ms minimum gap: ~300ms.
                nxt=max(nxt+.3,time.monotonic()+.3)
        async def ping(ws):
            while time.monotonic()<deadline:
                await asyncio.sleep(20)
                try: await ws.send('{"t":"ping"}')
                except Exception: break
        async def chat(ws,user):
            nxt=begin+user['order']/(max(1,args.chat_rate)*11)*11
            while nxt<deadline:
                await asyncio.sleep(max(0,nxt-time.monotonic()))
                if time.monotonic()>=deadline: break
                try: await ws.send(json.dumps(dict(t='send',ch='town',text='Capacity:'+clockword(),cid='cap-'+str(user['index'])+'-'+str(int(nxt))))); stats['chat_sent']+=1
                except Exception as e: errors['chat_send:'+type(e).__name__]+=1; break
                nxt+=11
        async def command(user):
            nxt=begin+(user['order']%args.users)/args.users*args.period
            seq=0
            while nxt<deadline:
                await asyncio.sleep(max(0,nxt-time.monotonic()))
                if time.monotonic()>=deadline: break
                seq+=1; stats['commands_started']+=1; at=time.monotonic(); kind='heavy' if user['heavy'] else 'small'
                body=dict(action='feed_like',career='milk_tea',payload={'post':user['post']},expected_revision=user['revision'],request_id=f'cap-{os.getpid()}-{user["index"]}-{int(started)}-{seq}',known=''.join(sorted(user['known'])))
                try:
                    async with session.post(API+'/api/command',headers=dict(user['headers'],**({'Connection':'close'} if os.environ.get('CAP_CLOSE_COMMANDS')=='1' else {})),json=body) as r:
                        raw=await r.read(); data=json.loads(raw); ms=(time.monotonic()-at)*1000
                        stats['http_status_'+str(r.status)]+=1; stats['http_response_bytes']+=r.content.total_raw_bytes
                        lat['command_all'].append(ms); lat['command_'+kind].append(ms)
                        if 'server_time' in data and 'server_recv' in data:
                            # Diagnostic hint only: these server fields use wall time,
                            # which can jump. Acceptance uses monotonic command_all.
                            server_ms=(data['server_time']-data['server_recv'])*1000
                            lat['server_command'].append(server_ms); lat['outside_handler'].append(max(0,ms-server_ms))
                        if r.status==200:
                            stats['commands_ok']+=1; remember(user,data)
                            if time.monotonic()<=deadline: stats['commands_ok_in_window']+=1
                        else:
                            errors['http:'+str(r.status)+':'+str(data.get('code'))]+=1
                            if r.status==409: remember(user,data)
                except Exception as e:
                    errors['http:'+type(e).__name__]+=1; stats['http_failures']+=1; lat['command_all'].append((time.monotonic()-at)*1000)
                nxt+=args.period
                late_until=min(time.monotonic(),deadline)
                if nxt<late_until:
                    skip=math.ceil((late_until-nxt)/args.period); stats['command_slots_missed']+=skip; nxt+=skip*args.period
        for ws,user in users:
            if user['order']<args.movers: tasks.append(asyncio.create_task(move(ws,user)))
            else: tasks.append(asyncio.create_task(ping(ws)))
            if user['order']<args.chat_rate*11: tasks.append(asyncio.create_task(chat(ws,user)))
            if args.period: commands.append(asyncio.create_task(command(user)))
        await asyncio.sleep(args.duration)
        # Capture end while connections remain open, then allow HTTP in-flight to finish.
        measured_end=time.time(); measured_seconds=time.monotonic()-begin; active=False
        await asyncio.gather(*commands,return_exceptions=True)
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        await asyncio.gather(*(ws.close() for ws in socks),return_exceptions=True)
    cpu1=process.cpu_times(); duration=time.monotonic()-start0
    q.put(dict(stats=dict(stats),errors=dict(errors),lat=dict(lat),rooms=list(rooms.values()),start=started,end=measured_end,measured_seconds=measured_seconds,known_sizes=[len(u['known']) for _,u in users],generator_cpu_seconds=cpu1.user+cpu1.system-cpu0.user-cpu0.system,generator_elapsed=duration,generator_rss=process.memory_info().rss))

def worker(part,args,ready,go,q): asyncio.run(clients(part,args,ready,go,q))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--users',type=int,default=1000); ap.add_argument('--movers',type=int,default=1000); ap.add_argument('--duration',type=int,default=60); ap.add_argument('--period',type=float,default=0); ap.add_argument('--chat-rate',type=int,default=3); ap.add_argument('--ramp',type=int,default=40); ap.add_argument('--profile',choices=['mixed','small'],default='mixed'); ap.add_argument('--name',required=True); ap.add_argument('--procs',type=int,default=4); args=ap.parse_args()
    # Wait for the service to finish restart before counting any simulated user.
    until=time.monotonic()+60
    while True:
        try:
            req=urllib.request.Request(API+'/api/health',headers={'Host':'127.0.0.1:18893'})
            with urllib.request.urlopen(req,timeout=2) as response:
                if response.status==200: break
        except Exception:
            if time.monotonic()>=until: raise
            time.sleep(.25)
    players=json.loads((ROOT/'players.json').read_text())
    if args.profile=='small': players=[p for p in players if not p['heavy']]
    players=players[:args.users]
    if len(players)!=args.users: raise SystemExit('not enough fixture players')
    for n,p in enumerate(players): p['order']=n
    ready=mp.Queue(); go=mp.Event(); q=mp.Queue()
    procs=[mp.Process(target=worker,args=(players[i::args.procs],args,ready,go,q)) for i in range(args.procs)]
    for p in procs: p.start()
    boot=[ready.get(timeout=240) for _ in procs]
    print(json.dumps(dict(phase='connected',workers=boot)),flush=True)
    def pgstat():
        if os.name!='nt': return None
        raw=subprocess.check_output(['docker','exec','mnl-cap-pg','sh','-c','cat /sys/fs/cgroup/cpu.stat; cat /sys/fs/cgroup/memory.current'],text=True).splitlines()
        return dict(at=time.time(),cpu=dict(s.split() for s in raw[:-1]),memory_bytes=int(raw[-1]))
    pg_before=pgstat(); go.set()
    time.sleep(min(args.duration/2,30))
    health=json.load(urllib.request.urlopen(LIVE.replace('ws:','http:')+'/health',timeout=5))
    print(json.dumps(dict(phase='steady',health=health)),flush=True)
    results=[q.get(timeout=args.duration+100) for _ in procs]
    pg_after=pgstat()
    for p in procs: p.join(10)
    stats=collections.Counter(); errors=collections.Counter(); lat=collections.defaultdict(list); rooms=collections.Counter()
    for r in results:
        stats.update(r['stats']); errors.update(r['errors']); rooms.update(r['rooms'])
        for k,v in r['lat'].items(): lat[k]+=v
    report=dict(name=args.name,config=vars(args),start=min(r['start'] for r in results),end=max(r['end'] for r in results),stats=dict(stats),errors=dict(errors),latency_ms={k:pct(v) for k,v in lat.items()},rooms=dict(count=len(rooms),max=max(rooms.values(),default=0)),generator=dict(cpu_seconds=sum(r['generator_cpu_seconds'] for r in results),rss_bytes=sum(r['generator_rss'] for r in results)),command_rps=round(stats['commands_ok_in_window']/args.duration,2),ws_mbps=round(stats['ws_bytes']*8/args.duration/1e6,3))
    report['health_midpoint']=health
    report['close_command_connections']=os.environ.get('CAP_CLOSE_COMMANDS')=='1'
    report['measured_seconds']=max(r['measured_seconds'] for r in results)
    report['known_hashes_per_user']=pct([n for r in results for n in r['known_sizes']])
    report['resources']={}
    if pg_before: report['resources']['pg']=dict(average_cores=round((int(pg_after['cpu']['usage_usec'])-int(pg_before['cpu']['usage_usec']))/1e6/(pg_after['at']-pg_before['at']),3),memory_end_mib=round(pg_after['memory_bytes']/2**20,1),includes_command_drain=True)
    for role,quota in [('api',6),('live',1)]:
        samples=[json.loads(line) for line in (ROOT/(role+'-resources.jsonl')).read_text().splitlines()]
        samples=[s for s in samples if report['start']<=s['at']<=report['end']]
        if len(samples)>1:
            a,b=samples[0],samples[-1]; span=sample_span(a,b); cg0,cg1=a['cgroup'],b['cgroup']
            report['resources'][role]=dict(quota_cores=quota,average_cores=round((cg1['usage_usec']-cg0['usage_usec'])/1e6/span,3),peak_1s_cores=round(max((b['cgroup']['usage_usec']-a['cgroup']['usage_usec'])/1e6/sample_span(a,b) for a,b in zip(samples,samples[1:])),3),peak_memory_mib=round(max(s['memory_bytes'] for s in samples)/2**20,1),throttled_periods=cg1['nr_throttled']-cg0['nr_throttled'],periods=cg1['nr_periods']-cg0['nr_periods'],processes=max(s['processes'] for s in samples))
    (ROOT/(args.name+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)
if __name__=='__main__': mp.freeze_support(); main()
