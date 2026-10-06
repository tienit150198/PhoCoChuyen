import {escapeHTML as esc,icon} from '../icons.js';

export function equipmentView(c,career,upgrades){
 const items=upgrades.filter(u=>u.kind==='equipment'&&u.careers.includes(career)),owned=new Set(c.upgrades),current=items.filter(u=>owned.has(u.id)).at(-1),fmt=n=>Number(n).toLocaleString('vi-VN');
 return `<section class="work-equipment" aria-labelledby="work-equipment-title"><div class="row spread wrap"><div><span class="eyebrow">THIẾT BỊ NGHỀ</span><h3 id="work-equipment-title">Làm nhanh hơn</h3></div><span class="tag green">${current?`Đã lắp bậc ${current.gear_tier} · +${current.gear_rate-100}%`:'Thiết bị cơ bản'}</span></div><p>Trả bằng quỹ của nghề này. Chọn bậc để xem đúng tác dụng trước khi mua; công việc đang chạy giữ tốc độ lúc bắt đầu.</p><div class="upgrade-grid">${items.map(u=>{const installed=owned.has(u.id),missing=u.requires&&!owned.has(u.requires),short=c.money<u.price,disabled=installed||missing||short;return `<article class="upgrade-card"><div class="row spread">${icon('settings',27)}<span class="tag">+${u.gear_rate-100}% tốc độ</span></div><h3>${esc(u.name)}</h3><p>${esc(u.description)}</p><button class="btn ${installed?'ghost':'primary'} full" type="button" data-action="buyUpgrade" data-item="${u.id}"${disabled?' disabled':''}>${installed?'Đã lắp':missing?`Cần bậc ${u.gear_tier-1} trước`:short?`Thiếu ${fmt(u.price-c.money)} xu`:`Lắp thiết bị · ${fmt(u.price)} xu`}</button></article>`;}).join('')}</div></section>`;
}

// Reads only confirmed state. No sales, currency or clocks are simulated here.
export function hasWorkingStaff(state){return Object.values(state?.careers||{}).some(c=>c.business_running||c.ops?.business?.status==='running');}

export function staffRefreshPaused(ui,counterOpen=false,fairOpen=false){return !!(ui.busy||ui.ivBusy||ui.view==='home'&&ui.jrView==='invest'||counterOpen||fairOpen);}

export function staffRefresh({state,refresh,busy,visible=()=>!document.hidden,interval=30000,lastSync=()=>0,now=()=>Date.now()}){
 let stopped=false,pending=false;
 const timer=setInterval(async()=>{if(stopped||pending||busy()||!visible()||now()-lastSync()<interval||!hasWorkingStaff(state()))return;pending=true;try{await refresh();}catch{/* next visible tick retries */}finally{pending=false;}},interval);
 return ()=>{stopped=true;clearInterval(timer);};
}

/* The open sheet while the player scrolls it (BACKLOG #12: review lists and details "jump back", decor items move away
 * before a tap lands). A background answer (the 30 s staff refresh, a minute's money, a friend's event) used to redraw
 * the sheet in the middle of a fling: the scroll was read and written back, which stops the fling, and an inner list
 * written anew started again from the top. scrollGuard() watches the sheet: while a finger is down or it scrolled in
 * the last `quiet` ms, busy() is true and later(fn) waits (the newest fn wins, once); restore() puts back the scroll
 * of inner lists the player scrolled that a redraw had to write anew (the same node keeps its own). A tap alone
 * (no scrolling) never holds anything up. */
export function scrollGuard({quiet=350,now=()=>performance.now(),setT=(f,ms)=>setTimeout(f,ms),clearT=t=>clearTimeout(t)}={}){
  let fingers=0,last=-1e9,timer=0,pending=null;const watched=new WeakSet(),spots=new Map();let seen=new WeakMap();
  const busy=()=>fingers>0||now()-last<quiet;
  const selOf=el=>el.tagName.toLowerCase()+[...el.classList].map(c=>'.'+(globalThis.CSS?.escape?CSS.escape(c):c)).join('');
  const keyOf=(el,root)=>el.id?{sel:'#'+(globalThis.CSS?.escape?CSS.escape(el.id):el.id),i:0}:{sel:selOf(el),i:[...root.querySelectorAll(selOf(el))].indexOf(el)};
  function kick(){
    clearT(timer);timer=0;if(!pending)return;
    if(busy()){timer=setT(kick,fingers>0?quiet:Math.max(16,quiet-(now()-last)));return;}
    const f=pending;pending=null;f();
  }
  return {
    busy,
    watch(root){
      if(!root||watched.has(root))return;watched.add(root);
      const opt={passive:true,capture:true};
      root.addEventListener('touchstart',e=>{fingers=e.touches?.length||1;},opt);
      const up=e=>{fingers=e.touches?.length||0;kick();};
      root.addEventListener('touchend',up,opt);root.addEventListener('touchcancel',up,opt);
      root.addEventListener('wheel',()=>{last=now();},opt);
      root.addEventListener('scroll',e=>{last=now();const t=e.target;
        if(t&&t!==root&&t.nodeType===1){const was=seen.get(t);   // a fling fires every frame: the key is worked out once per list
          if(was){was.top=t.scrollTop;was.left=t.scrollLeft;return;}
          const k=keyOf(t,root),id=k.sel+'|'+k.i,spot={...k,el:t,top:t.scrollTop,left:t.scrollLeft};seen.set(t,spot);spots.delete(id);spots.set(id,spot);
          if(spots.size>8)spots.delete(spots.keys().next().value);}},opt);
    },
    later(fn){pending=fn;kick();},
    restore(root){
      for(const [id,v] of spots){
        if(v.el.isConnected)continue;
        const el=[...root.querySelectorAll(v.sel)][v.i];
        if(!el){spots.delete(id);continue;}
        if(el.scrollTop!==v.top)el.scrollTop=v.top;
        if(el.scrollLeft!==v.left)el.scrollLeft=v.left;
        v.el=el;seen.set(el,v);
      }
    },
    reset(){spots.clear();seen=new WeakMap();},
  };
}
