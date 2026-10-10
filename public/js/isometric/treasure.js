/** A small controller shared by map renderers. Currency is only adopted from the server. */
export function createTreasureController(getEnv,options){
  const socket=options.socket,doc=options.document||globalThis.document,now=options.now||Date.now;
  const every=options.setInterval||setInterval,cancelEvery=options.clearInterval||clearInterval;
  const later=options.setTimeout||setTimeout,cancelLater=options.clearTimeout||clearTimeout;
  const uuid=options.uuid||(()=>crypto.randomUUID());
  let snapshot=null,offset=0,seen='',timer=null,lastRead=-Infinity,reading=false,started=false,seq=0,pending=null,busy=false,lastWorld=null,epoch=0;
  const off=[];
  const env=()=>typeof getEnv==='function'?getEnv():getEnv;
  const allowed=()=>socket.state==='open'&&socket.flags?.town&&socket.flags?.treasure;
  const serverNow=()=>now()/1000+offset;
  const active=()=>allowed()&&snapshot?.enabled&&snapshot.wave?.expires_at>serverNow();
  const chests=()=>active()?(snapshot.chests||[]).filter(c=>!c.claimed&&c.map_id==='iso-town-v1'&&typeof c.id==='string'&&Number.isFinite(c.x)&&Number.isFinite(c.y)).slice(0,5):[];
  function draw(){const w=env()?.world;if(w!==lastWorld){lastWorld?.setTreasure?.([]);lastWorld=w;}w?.setTreasure?.(chests());}
  function receive(value){
    if(!started||!value||typeof value.enabled!=='boolean')return;
    if(snapshot?.wave&&value.wave&&Number(value.wave.starts_at)<Number(snapshot.wave.starts_at))return;
    if(Number.isFinite(snapshot?.server_time)&&Number.isFinite(value.server_time)&&value.server_time<snapshot.server_time)return;
    if(snapshot?.wave?.id===value.wave?.id&&value.wave){
      const claimed=new Set(snapshot.chests.filter(c=>c.claimed).map(c=>c.id));
      value={...value,chests:(value.chests||[]).map(c=>claimed.has(c.id)?{...c,claimed:true}:c)};
    }
    snapshot=value;if(Number.isFinite(value.server_time))offset=value.server_time-now()/1000;
    draw();if(active()&&seen!==value.wave.id){seen=value.wave.id;if(!doc.hidden)env()?.toast?.(value.wave.notice||'Rương đã xuất hiện trên đảo! Mỗi rương thưởng 10.000 xu.');}
  }
  async function read(){
    if(reading||!allowed()||doc.hidden||!started)return;
    reading=true;lastRead=now();const generation=epoch;
    try{const value=await env().api.json('/api/town/treasure');if(generation===epoch)receive(value);}catch{/* bounded polling retries on next interval */}finally{reading=false;}
  }
  function tick(){draw();if(now()-lastRead>=20000)void read();}
  function fail(text='Kết nối khu phố đã thay đổi. Thử nhặt lại nhé.'){
    if(pending){cancelLater(pending.timer);pending.reject(new Error(text));pending=null;}
  }
  async function claim(id){
    const e=env(),w=e?.world,c=chests().find(c=>c.id===id),at=w?.getPresence?.();
    if(busy||doc.hidden||w?.mode!=='town'||e?.api?.state?.jail||!c||!at)return;
    if(Math.hypot(at.x-c.x,at.y-c.y)>1.5){e.toast?.('Đi lại gần rương để nhặt nhé.');return;}
    busy=true;const generation=epoch;
    try{
      // Acquire the short-lived proof only after earlier commands have settled.
      const run=async()=>{
        const point=w.getPresence?.(),chest=chests().find(c=>c.id===id);
        if(!started||generation!==epoch||doc.hidden||w.mode!=='town'||e.api.state?.jail||!point||!chest||Math.hypot(point.x-chest.x,point.y-chest.y)>1.5)throw new Error('Hãy đứng gần rương trên phố rồi thử lại nhé.');
        const proof=await new Promise((resolve,reject)=>{
          const cid=`treasure-${++seq}`;
          pending={cid,id,resolve,reject,timer:later(()=>fail('Chưa nhận được xác nhận. Thử lại nhé.'),5000)};
          if(!socket.send({t:'town_mv',x:point.x,y:point.y,direction:point.direction||'se'})||!socket.send({t:'town_treasure_prepare',chest_id:id,cid}))fail();
        });
        const body={chest_id:id,proof,request_id:uuid()},since=e.api.accepted;
        try{
          // The server replays this exact receipt if its first response was lost.
          const result=await e.api.retrying(()=>e.api.post('/api/town/treasure/claim',body));
          e.api.accept(result,since);e.toast?.(result.result?.message||'Bạn nhận được 10.000 xu!');
          if(snapshot)snapshot={...snapshot,chests:snapshot.chests.map(c=>c.id===id?{...c,claimed:true}:c)};draw();
        }catch(error){await e.api.refresh().catch(()=>{});throw error;}
      };
      const job=(e.api.queue||Promise.resolve()).then(run,run);e.api.queue=job.catch(()=>{});await job;
    }catch(error){e.toast?.(error.message||'Rương đã được người khác nhặt.',true);lastRead=-Infinity;void read();}
    finally{busy=false;}
  }
  function clear(){epoch++;fail();snapshot=null;draw();}
  function start(){
    if(started)return api;started=true;
    off.push(socket.on('town_treasure',receive),socket.on('welcome',()=>{clear();lastRead=-Infinity;tick();}),socket.on('down',clear),socket.on('town_left',()=>fail()),
      socket.on('town_treasure_ready',f=>{if(pending&&f.cid===pending.cid&&f.chest_id===pending.id&&typeof f.proof==='string'){const p=pending;pending=null;cancelLater(p.timer);p.resolve(f.proof);}}),
      socket.on('error',f=>{if(pending&&f.ref===pending.cid)fail(f.msg||f.message||f.error||'Chưa thể nhặt rương ở đây.');}));
    doc.addEventListener?.('visibilitychange',tick);timer=every(tick,1000);tick();return api;
  }
  function stop(){if(!started)return;started=false;clear();cancelEvery(timer);for(const fn of off.splice(0))fn();doc.removeEventListener?.('visibilitychange',tick);}
  const api={start,stop,claim,receive,tick};return api;
}
