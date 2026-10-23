import {escapeHTML as esc,icon} from '../icons.js';
import {paySection} from './paykit.js';   // 🧰 Bộ đồ nghề / 📒 Sổ khách quen / ⏩ Làm nhanh (game/pay_boost.py)

export function equipmentView(c,career,upgrades){
 const items=upgrades.filter(u=>u.kind==='equipment'&&u.careers.includes(career)),owned=new Set(c.upgrades),fmt=n=>Number(n).toLocaleString('vi-VN');
 const groups=[['speed','Làm nhanh hơn'],['demand','Đón thêm khách'],['quality','Kiếm thêm từ mỗi việc'],['online','Thêm đơn online'],['warehouse_count','Đếm kho nhanh hơn'],['warehouse_logistics','Kho & đơn nhập'],['warehouse_storage','Sức chứa kho nghề'],['warehouse_order','Nhập hàng mỗi lần']];
 const percent=u=>u.effect_percent??u.gear_rate-100;
 const shelfBase=Math.max(c.ops?.property?.details?.stock_cap||12,owned.has('shelf')?24:12);
 const effect=u=>u.effect_units!=null?`${fmt(u.effect_units)} ${esc(u.effect_label)}`:`+${percent(u)}%`;
 // Feedback #375/#378: the per-line ladder was bought for shelf room. While one line already fills a whole shelf, say so
 // here (the shelf size, else 0). Storage rows give the current shelf: the owned tier's units, or tier 1's "previous".
 const shelfFull=(rows,current)=>{const st=items.filter(u=>u.gear_group==='warehouse_storage').sort((a,b)=>a.gear_tier-b.gear_tier);if(!st.length)return 0;
  const have=st.filter(u=>owned.has(u.id)).pop(),shelf=have?have.effect_units:st[0].effect_previous,line=current?current.effect_units:rows[0].effect_previous;
  return line>=shelf&&have?.gear_tier!==st[st.length-1].gear_tier?shelf:0;};
 const transition=u=>u.effect_units!=null?`${fmt(u.effect_previous)} → ${effect(u)}`:`${effect(u)} ${esc(u.effect_label||'tốc độ')}`;
 const sections=groups.map(([group,title])=>{
  const rows=items.filter(u=>(u.gear_group||'speed')===group);if(!rows.length)return '';
  const current=rows.filter(u=>owned.has(u.id)).sort((a,b)=>b.gear_tier-a.gear_tier)[0];
  const full=group==='warehouse_order'?shelfFull(rows,current):0;
  return `<section class="space-top" data-gear-group="${group}" aria-label="${esc(title)}"><div class="row spread wrap"><h3>${esc(title)}</h3><span class="tag green">${current?`Đã lắp bậc ${current.gear_tier} · ${effect(current)}`:'Chưa nâng cấp'}</span></div>${rows[0].total_price?`<p class="muted small">Tổng đến bậc 10: ${fmt(rows[0].total_price)} xu. Mỗi bậc thay bậc trước.</p>`:''}${full?`<p class="small">Kho đang chứa ${fmt(full)} phần/mã: nhập mỗi dòng nhiều hơn chưa dùng được. Muốn chứa thêm, nâng Sức chứa kho nghề.</p>`:''}<div class="upgrade-grid">${rows.map(u=>{
   const installed=owned.has(u.id),missing=u.requires&&!owned.has(u.requires),locked=(c.level||1)<(u.min_level||1),short=c.money<u.price,disabled=installed||missing||locked||short;
   const old=installed&&current.gear_tier>u.gear_tier;
   return `<article class="upgrade-card"><div class="row spread">${icon('settings',27)}<span class="tag">${transition(u)}</span></div><h3>${esc(u.name)}</h3><p>${esc(u.description)}${(u.effect_resources||[]).map(r=>`<br>${esc(r.name)}: ${fmt(r.previous)} → ${fmt(r.capacity)} ${esc(r.unit)}`).join('')}${u.effect_capacity?`<br>${fmt(Math.max(shelfBase,u.effect_previous_capacity))} → ${fmt(Math.max(shelfBase,u.effect_capacity))} món / mã trên kệ`:''}</p><button class="btn ${installed?'ghost':'primary'} full" type="button" data-action="buyUpgrade" data-item="${esc(u.id)}"${disabled?' disabled':''}>${installed?(old?'Đã có · dùng bậc cao hơn':'Đã lắp'):missing?`Cần bậc ${u.gear_tier-1} trước`:locked?`Cần cấp ${u.min_level}`:short?`Thiếu ${fmt(u.price-c.money)} xu`:`Lắp thiết bị · ${fmt(u.price)} xu`}</button></article>`;
  }).join('')}</div></section>`;
 }).join('');
 // 🔁 Tự đặt hàng (game/auto_order.py, warehouse.reorder): one paid unlock per workplace with a stock room; quỹ first, then the wallet.
 const ro=c.warehouse?.reorder,esq=v=>esc(JSON.stringify(v));
 const roCard=ro?`<section class="space-top" data-gear-group="reorder" aria-label="Tự đặt hàng"><div class="row spread wrap"><h3>🔁 Tự đặt hàng</h3><span class="tag green">${ro.owned?'Đã mở':'Chưa mở'}</span></div><div class="upgrade-grid"><article class="upgrade-card"><div class="row spread">${icon('box',27)}<span class="tag">Kho tự đặt</span></div><h3>🔁 Tự đặt hàng</h3><p>Món nào sắp hết thì tự đặt lại, trả bằng quỹ. Chỉnh ở Kho.</p>${ro.owned?`<button class="btn ghost full" type="button" disabled>Đã mở</button>`:`<button class="btn primary full" type="button" data-action="v4Cmd" data-op="stock_reorder" data-payload="${esq({buy:true})}" data-confirm="${esc(`Mua 🔁 Tự đặt hàng? ${fmt(ro.price)} xu: quỹ trả trước, thiếu thì lấy ví.`)}"${ro.short?' disabled':''}>${ro.short?`Thiếu ${fmt(ro.short)} xu`:`Mua · ${fmt(ro.price)} xu`}</button>`}</article>${boxCard(ro)}</div></section>`:'';
 return `<section class="work-equipment" aria-labelledby="work-equipment-title"><span class="eyebrow">THIẾT BỊ NGHỀ</span><h3 id="work-equipment-title">Đầu tư để kiếm thêm</h3><p>Trả bằng quỹ của nghề này. Mỗi nhóm nâng riêng; bậc cao thay bậc thấp. Khách đang chờ giữ lịch cũ, lượt kế tiếp dùng nhịp mới. Thu nhập phụ thuộc hàng tồn, giá bán và chi phí.</p>${paySection(c)}${gadgetSection(c)}${sections}${roCard}</section>`;
}

/** 🧰 Phụ kiện nghề (game/career_gadgets.py, `c.gadgets`): one purchase each, from the fund. An older server sends no
 * `gadgets`: nothing shows. */
function gadgetSection(c){
  const list=Array.isArray(c.gadgets)?c.gadgets:[];if(!list.length)return '';
  const fmt=n=>Number(n||0).toLocaleString('vi-VN'),esq=v=>esc(JSON.stringify(v));
  return `<section class="space-top" data-gear-group="gadgets" aria-label="Phụ kiện nghề"><div class="row spread wrap"><h3>🧰 Phụ kiện nghề</h3><span class="tag green">${list.filter(g=>g.owned).length}/${list.length} đã có</span></div><div class="upgrade-grid">${list.map(g=>`<article class="upgrade-card gadget-card" data-gadget="${esc(g.id)}"><div class="row spread"><span class="upgrade-icon gadget-emoji" aria-hidden="true">${esc(g.emoji)}</span><span class="tag">${esc(g.tag)}</span></div><h3>${esc(g.emoji)} ${esc(g.name)}</h3><p>${esc(g.description)}</p><ul class="gadget-effects small">${(g.effects||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>${g.owned?`<button class="btn ghost full" type="button" disabled>✓ Đã lắp</button>`:`<button class="btn primary full" type="button" data-action="v4Cmd" data-op="gadget_buy" data-payload="${esq({item:g.id})}" data-confirm="${esc(`Mua ${g.emoji} ${g.name}? ${fmt(g.price)} xu từ quỹ nghề.`)}"${g.short?' disabled':''}>${g.short?`Thiếu ${fmt(g.short)} xu`:`Mua · ${fmt(g.price)} xu`}</button>`}</article>`).join('')}</div></section>`;
}

/** 📦 Gộp thùng tự đặt (game/auto_order.py `box`): bought after 🔁 Tự đặt hàng; an older server sends no `box`.
 * `box: null`: not sold there (🍼 💊 the older stock desks merge an automatic pass into one van by themselves). */
function boxCard(ro){
  const b=ro.box,fmt=n=>Number(n||0).toLocaleString('vi-VN'),esq=v=>esc(JSON.stringify(v));
  if(b===null||ro.owned&&!b)return '';
  const price=b?.price||10000,state=b?.owned?`<button class="btn ghost full" type="button" disabled>Đã mở</button>`
    :!ro.owned?`<button class="btn ghost full" type="button" disabled>Mở 🔁 Tự đặt hàng trước</button>`
    :`<button class="btn primary full" type="button" data-action="v4Cmd" data-op="stock_reorder" data-payload="${esq({buy_box:true})}" data-confirm="${esc(`Mua 📦 Gộp thùng tự đặt? ${fmt(price)} xu: quỹ trả trước, thiếu thì lấy ví.`)}"${b.short?' disabled':''}>${b.short?`Thiếu ${fmt(b.short)} xu`:`Mua · ${fmt(price)} xu`}</button>`;
  return `<article class="upgrade-card"><div class="row spread">${icon('box',27)}<span class="tag">Kho tự đặt</span></div><h3>📦 Gộp thùng tự đặt</h3><p>Hàng tự đặt về tới cửa gom chung một thùng: mở và kiểm một lần.</p>${state}</article>`;
}

// Reads only confirmed state. No sales, currency or clocks are simulated here.
export function hasWorkingStaff(state){return Object.values(state?.careers||{}).some(c=>c.business_running||c.ops?.business?.status==='running');}

export function staffRefreshPaused(ui,counterOpen=false,fairOpen=false){return !!(ui.busy||ui.ivBusy||ui.view==='home'&&ui.jrView==='invest'||counterOpen||fairOpen);}

// 60 s (was 30 s): each tick is a full GET /api/state + business_sync of a multi-MB save; the money waits a little longer, taps get the CPU (23/10 lag).
export function staffRefresh({state,refresh,busy,visible=()=>!document.hidden,interval=60000,lastSync=()=>0,now=()=>Date.now()}){
 let stopped=false,pending=false;
 const timer=setInterval(async()=>{if(stopped||pending||busy()||!visible()||now()-lastSync()<interval||!hasWorkingStaff(state()))return;pending=true;try{await refresh();}catch{/* next visible tick retries */}finally{pending=false;}},interval);
 return ()=>{stopped=true;clearInterval(timer);};
}

/* The open sheet while the player scrolls it (BACKLOG #12: review lists and details "jump back", decor items move away
 * before a tap lands). A background answer (the 60 s staff refresh, a minute's money, a friend's event) used to redraw
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
