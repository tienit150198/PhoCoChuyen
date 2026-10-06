/** 🌟 Trang trại — the farm's wall-clock garden, pens, buyers and upgrades (game/careers/farm_plus.py).
 *  The server decides everything; the page only counts down on the server clock (x.now()) so a crop ripens,
 *  a need comes up or the ducks lay while you watch, then re-renders. Four short panes, one at a time. */
const P=x=>x.room.data?.plus||{open:false};
const C=x=>x.cc.plus||{crops:[],cares:{},animals:[],products:{},upgrades:[],buyers:{}};
const crop=(x,id)=>(C(x).crops||[]).find(c=>c.id===id)||{id,name:id,emoji:'🌱',unit:''};
const prod=(x,id)=>C(x).products?.[id]||{name:id,emoji:'•',unit:''};
const care=(x,k)=>C(x).cares?.[k]||{icon:'•',label:k};
const animal=(x,id)=>(C(x).animals||[]).find(a=>a.id===id);
const xu=t=>(Math.round(t)/10).toLocaleString('vi-VN',{maximumFractionDigits:1});
/** mm:ss under an hour, then "1g 05p". */
export function clock(sec){
  sec=Math.max(0,Math.ceil(sec));
  if(sec>=3600){const h=Math.floor(sec/3600),m=Math.floor(sec%3600/60);return `${h}g ${String(m).padStart(2,'0')}p`;}
  return `${Math.floor(sec/60)}:${String(sec%60).padStart(2,'0')}`;
}
const cd=(end,x,cls='')=>`<b class="fp-cd ${cls}" data-end="${end}">${clock(end-x.now())}</b>`;

/* A plot as the page sees it now: stage, percent and the needs that have come up. */
function live(p,x){
  if(!p.crop)return p;
  const now=x.now(),pct=Math.max(0,Math.min(100,Math.floor((now-p.at)*100/Math.max(1,p.dur))));
  const stage=now<p.ripe_at?(pct<20?'seed':pct<55?'sprout':'grow'):now<=p.over_at?'ripe':'over';
  const due=(p.needs||[]).filter(([k,at])=>at<=pct&&!(p.done||[]).includes(k)).map(([k])=>k);
  return {...p,pct,stage,due};
}
/* The next moment the pane changes by itself (a need comes up, a crop ripens or goes over, a pen is ready). */
function nextChange(x){
  const g=P(x);if(!g.open)return null;
  const now=x.now(),t=[];
  for(const p of g.plots||[]){
    if(!p.crop)continue;
    for(const [k,at] of p.needs||[])if(!(p.done||[]).includes(k))t.push(p.at+Math.ceil(p.dur*at/100));
    t.push(p.ripe_at,p.over_at+1);
  }
  for(const v of Object.values(g.pens||{}))if(v.ready_at)t.push(v.ready_at);
  for(const o of g.orders||[])t.push(o.until);
  const f=t.filter(v=>v>now);
  return f.length?Math.min(...f):null;
}
let timer=null;
/** After each render: tick the countdowns every second; re-render once something changes on its own. */
export function plusTick(root,x){
  clearInterval(timer);timer=null;
  const els=()=>root.querySelectorAll('.fp-cd');
  if(!P(x).open||!els().length)return;
  const at=nextChange(x);
  timer=setInterval(()=>{
    if(!root.isConnected){clearInterval(timer);timer=null;return;}
    const now=x.now();
    for(const el of els())el.textContent=clock(Number(el.dataset.end)-now);
    if(at&&now>=at){clearInterval(timer);timer=null;x.render();}
  },1000);
}

/* ------------------------------------------------------------ panes */
const PANES=[['garden','🌱','Vườn'],['pens','🐄','Chuồng'],['sell','🧾','Bán'],['up','🛠️','Nâng cấp']];
function head(x){
  const g=P(x),span=g.next?Math.max(1,g.next-g.floor):1,pct=g.next?Math.min(100,(g.xp-g.floor)/span*100):100;
  const chips=[g.festival?`<span class="fp-chip fest">🎉 Hội mùa · giá +${(C(x).fest_pct||125)-100}%</span>`:'',(g.ups||[]).includes('gap')?'<span class="fp-chip gap">🏅 VietGAP</span>':''].join('');
  return `<div class="fp-head"><div class="fp-lv"><b>Cấp ${g.level}</b><span>${x.esc(g.title||'')}</span></div>
    <div class="fp-xp" role="img" aria-label="Điểm nông ${g.xp}${g.next?'/'+g.next:''}"><i style="width:${pct.toFixed(1)}%"></i></div>
    <small class="fp-xpn">${g.xp}${g.next?'/'+g.next:''}</small>${chips}</div>`;
}
function paneBar(x){
  const g=P(x),pane=x.ui.fpPane||'garden';
  const ripe=(g.plots||[]).map(p=>live(p,x)).filter(p=>p.crop&&(p.stage==='ripe'||p.due.length)).length;
  const pens=Object.entries(g.pens||{}).filter(([,v])=>!v.fed||v.ready_at<=x.now()).length;
  const ready=(g.orders||[]).filter(o=>!o.why).length;
  const badge={garden:ripe,pens,sell:ready};
  return `<div class="fp-panes" role="tablist">${PANES.map(([id,e,label])=>`<button type="button" class="fp-pane ${pane===id?'on':''}" data-action="car:fpPane" data-pane="${id}" role="tab" aria-selected="${pane===id}"><span aria-hidden="true">${e}</span>${label}${badge[id]?`<b class="fa-badge">${badge[id]}</b>`:''}</button>`).join('')}</div>`;
}

function plotCard(p,x){
  const g=P(x);
  if(!p.crop){
    const on=x.ui.fpPlot===p.i;
    return `<button type="button" class="fp-plot empty ${on?'on':''}" data-action="car:fpPlot" data-i="${p.i}" aria-pressed="${on}"><span class="fp-soil"><span class="fp-art">＋</span></span><small>Ô ${p.i+1} · gieo</small></button>`;
  }
  const q=live(p,x),c=crop(x,p.crop);
  const art=q.stage==='seed'?'🟤':q.stage==='sprout'?'🌱':q.stage==='grow'?(['tl','xoai','cafe'].includes(p.crop)?'🌳':'🌿'):c.emoji;
  const needs=q.stage==='ripe'||q.stage==='over'?'':q.due.map(k=>`<button type="button" class="btn fp-need" data-command="fa_v_care" data-payload="${x.esc(JSON.stringify({plot:p.i,need:k}))}" aria-label="${x.esc(care(x,k).label)}" title="${x.esc(care(x,k).label)}">${care(x,k).icon}</button>`).join('');
  const missed=(p.needs||[]).filter(([k])=>!(p.done||[]).includes(k)).length;
  let foot;
  if(q.stage==='ripe'||q.stage==='over')foot=x.cmd(`🧺 Thu${q.stage==='over'?' (quá lứa)':''}`,'fa_v_harvest',{plot:p.i},`small ${q.stage==='over'?'ghost':'primary'} fp-cut`);
  else foot=`<small class="fp-time">⏱ ${cd(p.ripe_at,x)}</small>`;
  const done=q.stage==='ripe'||q.stage==='over';
  const label=done?(q.stage==='over'?'Quá lứa · loại B':missed?'Chín · loại B':'Chín · loại A'):q.due.length?q.due.map(k=>care(x,k).label).join(' · '):c.name;
  return `<div class="fp-plot ${q.stage}${q.due.length?' needy':''}"><span class="fp-soil" style="--p:${q.pct}%"><span class="fp-art ${q.stage}" aria-hidden="true">${art}</span>${needs?`<span class="fp-needs">${needs}</span>`:''}<i class="fp-grow"></i></span>
    <small class="fp-name">${c.emoji} ${x.esc(label)}</small>${foot}</div>`;
}
function seedPicker(x){
  const g=P(x),i=x.ui.fpPlot;
  const p=(g.plots||[]).find(q=>q.i===i);if(!p||p.crop)return '';
  const all=(g.ups||[]).includes('tractor')&&(g.plots||[]).filter(q=>!q.crop).length>1&&x.ui.fpAll;
  const money=Number(x.room.money)||0;
  const empties=(g.plots||[]).filter(q=>!q.crop).length;
  const tiles=(g.crops||[]).map(v=>{const c=crop(x,v.id),poor=money<c.seed*(all?empties:1);const cmd=all?['fa_v_all',{what:'plant',crop:c.id}]:['fa_v_plant',{plot:i,crop:c.id}];
    return `<button type="button" class="tile fp-seed ${v.why?'locked':''}" data-command="${cmd[0]}" data-payload="${x.esc(JSON.stringify(cmd[1]))}"${v.why||poor?' disabled':''}><span class="tile-emoji">${c.emoji}</span><b>${x.esc(c.name)}</b><small>${v.why?'🔒 '+x.esc(v.why):`⏱ ${clock(v.dur)} · ${c.seed} xu`}</small><small class="fp-seed-x">${c.qty} ${x.esc(c.unit)} × ${c.price} xu</small></button>`;}).join('');
  const many=(g.ups||[]).includes('tractor')&&(g.plots||[]).filter(q=>!q.crop).length>1;
  return `<div class="fp-pick card"><div class="row spread"><b>🌱 Gieo ô ${i+1}</b>${many?`<button type="button" class="btn small ${x.ui.fpAll?'primary':'ghost'}" data-action="car:fpAll" aria-pressed="${!!x.ui.fpAll}">🚜 Cả vườn</button>`:''}</div><div class="tile-grid fp-seeds">${tiles}</div></div>`;
}
function garden(x){
  const g=P(x),plots=(g.plots||[]).map(p=>plotCard(p,x)).join('');
  const lock=g.plot_cost!=null?x.confirmCmd(`<span class="fp-soil"><span class="fp-art">🔒</span></span><small>Khai hoang · ${g.plot_cost} xu</small>`,'fa_v_buy',{up:'plot'},`Khai hoang thêm một ô đất giá ${g.plot_cost} xu?`,'fp-plot locked',(Number(x.room.money)||0)<g.plot_cost):'';
  const lv=(g.plots||[]).map(p=>live(p,x));
  const tractor=(g.ups||[]).includes('tractor')?[lv.some(p=>p.crop&&(p.stage==='ripe'||p.stage==='over'))?x.cmd('🚜 Thu cả vườn','fa_v_all',{what:'harvest'},'small primary'):'',lv.some(p=>p.crop&&p.due.length&&p.stage!=='ripe'&&p.stage!=='over')?x.cmd('🚜 Chăm cả vườn','fa_v_all',{what:'care'},'small'):''].join(''):'';
  const sky={hot:'☀️ Nắng gắt: cây khát',sun:'🌤️ Nắng: nhớ tưới',wind:'🍃 Gió: đất mau khô',rain:'🌧️ Mưa: coi chừng giông',cloud:'⛅ Râm: dễ có mưa'}[g.sky]||'';
  return `<p class="fp-sky small muted">${sky}${(g.ups||[]).includes('drip')?' · 💧 tưới nhỏ giọt':''}${(g.ups||[]).includes('green')?' · 🏠 nhà kính':''}</p>
    <div class="fp-plots">${plots}${lock}</div>${tractor?`<div class="row wrap fp-tractor">${tractor}</div>`:''}${seedPicker(x)}`;
}
function pens(x){
  const g=P(x),have=g.pens||{},barn=(g.ups||[]).includes('barn'),money=Number(x.room.money)||0,now=x.now();
  return `<div class="fp-pens">${(C(x).animals||[]).map(a=>{
    const v=have[a.id];let state,btn;
    if(!v){
      state=a.barn&&!barn?'🔒 Cần chuồng trại':a.id==='pig'?`Nuôi ${a.feeds} cữ rồi bán ${a.sell} xu`:`Mỗi ${a.mins} phút: ${a.qty} ${prod(x,a.product).unit} ${prod(x,a.product).name.toLowerCase()}`;
      btn=a.barn&&!barn?'':x.confirmCmd(`Mua · ${a.cost} xu`,'fa_v_animal',{animal:a.id},`Mua ${a.name.toLowerCase()} giá ${a.cost} xu?`,'small',money<a.cost);
    }else{
      const ready=v.fed&&v.ready_at<=now;
      if(a.id==='pig'){
        if(v.n>=a.feeds&&ready){state='Heo đã lớn!';btn=x.cmd(`💰 Bán heo`,'fa_v_collect',{animal:a.id},'small primary');}
        else if(v.fed&&!ready){state=`${v.n}/${a.feeds} cữ · no, ăn tiếp sau ${cd(v.ready_at,x)}`;btn='';}
        else{state=`${v.n}/${a.feeds} cữ · đói rồi`;btn=x.cmd(`🌾 Cho ăn · ${a.feed} xu`,'fa_v_feed',{animal:a.id},'small',money<a.feed);}
      }else if(!v.fed){state='Đói rồi';btn=x.cmd(`🌾 Cho ăn · ${a.feed} xu`,'fa_v_feed',{animal:a.id},'small',money<a.feed);}
      else if(!ready){state=`${prod(x,a.product).emoji} sau ${cd(v.ready_at,x)}`;btn='';}
      else{state='Xong rồi!';btn=x.cmd(`🧺 Thu ${a.qty} ${prod(x,a.product).unit}`,'fa_v_collect',{animal:a.id},'small primary');}
    }
    return `<div class="fp-pen ${v?'own':''}"><span class="fp-pen-art ${v&&v.fed?'busy':''}" aria-hidden="true">${a.emoji}</span><div class="grow"><b>${x.esc(a.name)}</b><small>${state}</small></div>${btn}</div>`;
  }).join('')}</div>`;
}
function sell(x){
  const g=P(x),slip=g.slip||8,depth=g.depth||40;
  const est=(unit,sold,q)=>{let t=0;for(let k=0;k<q;k++)t+=Math.floor(unit*Math.max(60,100-10*Math.floor((sold+k)/slip))/100);return Math.max(1,Math.floor((t+5)/10));};
  const rows=(g.store||[]).map(r=>{const p=prod(x,r.id),room=Math.max(0,depth-r.sold);
    const b=(grade,qty,unit)=>{const q=Math.min(qty,room);return q?x.cmd(`${grade} ${qty} → ${est(unit,r.sold,q)} xu`,'fa_v_sell',{item:r.id,grade,qty:q},`small ${grade==='A'?'':'ghost'}`):'';};
    return `<div class="fp-stock"><span aria-hidden="true">${p.emoji}</span><b class="grow">${x.esc(p.name)}<small>${xu(r.unit_a)} xu/${x.esc(p.unit)}${room?'':' · chợ đủ hàng'}</small></b>${r.a?b('A',r.a,r.unit_a):''}${r.b?b('B',r.b,r.unit_b):''}</div>`;}).join('');
  const now=x.now();
  const orders=(g.orders||[]).filter(o=>o.until>now).map(o=>{
    const b=C(x).buyers?.[o.buyer]||{name:o.buyer,emoji:'🧑'};
    const items=Object.entries(o.items).map(([k,q])=>{const p=prod(x,k),s=(g.store||[]).find(r=>r.id===k),have=s?(b.grade==='A'?s.a:s.a+s.b):0;return `<span class="fa-chip ${have>=q?'ok':''}">${p.emoji} ${Math.min(have,q)}/${q}</span>`;}).join('');
    const tags=[b.grade==='A'?'<span class="tag blue">Loại A</span>':'<span class="tag amber">A/B</span>',b.gap?'<span class="tag green">🏅 VietGAP</span>':''].join('');
    const act=o.asked?`${x.cmd(`🤝 Bớt · ${Math.floor(o.pay*(C(x).haggle_pct||85)/100)} xu`,'fa_v_deliver',{order:o.id,deal:'yes'},'small')}${x.cmd('✋ Giữ giá','fa_v_deliver',{order:o.id,deal:'no'},'small ghost')}`
      :`${x.cmd('🚚 Giao','fa_v_deliver',{order:o.id},'small primary',!!o.why)}${x.cmd('✕','fa_v_skip',{order:o.id},'small ghost fp-x')}`;
    return `<article class="fp-order${o.asked?' haggle':''}"><div class="row spread"><b>${b.emoji} ${x.esc(b.name)}</b><b class="price">${o.pay} xu</b></div>
      <p class="fp-line">${x.esc(o.asked?'“Bớt chút nha em?”':o.line)}</p><div class="row wrap fp-items">${items}${tags}<small class="muted">⏱ ${cd(o.until,x)}</small></div>
      ${o.why&&!o.asked?`<small class="fp-why">${x.esc(o.why)}</small>`:''}<div class="row wrap">${act}</div></article>`;}).join('');
  return `<h4 class="section-title">🧾 Đơn đặc sản</h4>${orders||'<p class="muted small">Chưa có đơn, thu hoạch thêm rồi quay lại nha.</p>'}
    <h4 class="section-title">📦 Kho · ${g.store_units||0}/${g.store_cap||0} <small class="muted">bán ở chợ</small></h4>${rows||'<p class="muted small">Kho trống.</p>'}`;
}
function upgrades(x){
  const g=P(x),own=g.ups||[],money=Number(x.room.money)||0,st=g.stats||{};
  const tiles=(C(x).upgrades||[]).map(u=>{const has=own.includes(u.id),gate=u.need_a&&(st.a||0)<u.need_a;
    const btn=has?'<span class="tag green">✓ Đã có</span>':x.confirmCmd(`${u.cost} xu`,'fa_v_buy',{up:u.id},`Mua ${u.name} giá ${u.cost} xu?`,'small',gate||money<u.cost);
    return `<div class="fp-up ${has?'own':''}"><span class="fp-up-art" aria-hidden="true">${u.emoji}</span><div class="grow"><b>${x.esc(u.name)}</b><small>${x.esc(u.text)}${gate?` · cần ${u.need_a} lần thu loại A (${st.a||0})`:''}</small></div>${btn}</div>`;}).join('');
  const rec=[`🧺 ${st.harvests||0} lần thu`,st.gold?`🌟 ${st.gold} trái vàng`:'',st.pumpkin?`🎃 ${st.pumpkin} kg`:'',st.melon?`🍉 ${st.melon} kg`:'',st.giant?`🏆 ${st.giant} bí khổng lồ`:'',`💰 ${st.income||0} xu`].filter(Boolean).join(' · ');
  return `<div class="fp-ups">${tiles}</div><p class="fp-rec small muted">${rec}</p>`;
}

/** The pane (the farm's 🌟 tab, and the walk view's drawer). */
export function plusTab(x){
  const g=P(x);
  if(!g.open)return `<div class="card fp-intro"><p class="fp-intro-art" aria-hidden="true">🌶️🍉🐄🚜</p><h4>Trang trại mới</h4>
    <ul class="fp-intro-list"><li>⏱ Cây lớn theo giờ thật, cả lúc bạn đi vắng</li><li>🐛 Mỗi vụ một kiểu chăm</li><li>🦆 Vịt, bò sữa, heo</li><li>🧾 Khách đặt hàng khó tính</li><li>🛠️ Nhà kính, máy cày, VietGAP</li></ul>
    ${x.cmd('🌟 Mở trang trại','fa_v_open',{},'primary full')}</div>`;
  const pane=x.ui.fpPane||'garden';
  const body=pane==='pens'?pens(x):pane==='sell'?sell(x):pane==='up'?upgrades(x):garden(x);
  return `<section class="fp">${head(x)}${paneBar(x)}<div class="fp-body">${body}</div></section>`;
}
/** The 🌟 tab's small line. */
export function plusSub(x){
  const g=P(x);if(!g.open)return 'MỚI';
  const n=(g.plots||[]).map(p=>live(p,x)).filter(p=>p.crop&&(p.stage==='ripe'||p.due.length)).length;
  return n?`${n} ô cần bạn`:`cấp ${g.level}`;
}
export function plusBadge(x){
  const g=P(x);if(!g.open)return '<b class="fa-badge new">!</b>';
  const n=(g.plots||[]).map(p=>live(p,x)).filter(p=>p.crop&&(p.stage==='ripe'||p.due.length)).length;
  return n?`<b class="fa-badge">${n}</b>`:'';
}
/** A between-orders hint row when the garden waits for you (lowest priority). */
export function plusStep(x,walk){
  const g=P(x),open=walk?{act:'car:fvmore',data:{more:'plus'}}:{act:'car:tab',data:{tab:'plus'}};
  if(!g.open)return {ok:null,label:'Mở trang trại mới',go:{...open,label:'🌟 Xem trang trại mới'}};
  const q=(g.plots||[]).map(p=>live(p,x)).find(p=>p.crop&&(p.stage==='ripe'||p.due.length));
  if(!q)return null;
  const c=crop(x,q.crop),what=q.stage==='ripe'||q.stage==='over'?`Thu ${c.name.toLowerCase()} ô ${q.i+1}`:`${care(x,q.due[0]).label} ô ${q.i+1}`;
  return {ok:null,label:what,go:{...open,label:`🌟 ${x.esc(what)}`}};
}
export const plusActions={
  async fpPane(d,el,x){x.ui.fpPane=['garden','pens','sell','up'].includes(d.pane)?d.pane:'garden';x.render();},
  async fpPlot(d,el,x){const i=Number(d.i);x.ui.fpPlot=x.ui.fpPlot===i?null:i;x.render();},
  async fpAll(d,el,x){x.ui.fpAll=!x.ui.fpAll;x.render();},
};
