/** Tiệm Bánh & Cà Phê Sớm Mai — espresso bar + bakery. The day strip, the
 * guest queue, the order (a mood to read, or a tray of cups done one by one),
 * station tabs whose tiles carry stock badges and padlocks, live timing bars
 * with a green zone, the display case that walk-in buyers shop from, and one
 * big "Giao". Only renders server state and sends commands; the server checks
 * every rule and keeps a mood order's drink hidden until it is found.
 * The order is a requirement list (ui-kit reqList) checked live against the cup.
 * Care loop: Bé Men the sourdough starter, dough chilled overnight in the fridge,
 * yesterday's pastries each morning, and the regulars' notes card. */
import {dayStrip,flash,eventCard,queue,keepBarAboveFooter,idlePanel,gradeCard,patience,openTasks} from './food_kit.js';
import {fold} from '../ui-kit.js';
import {nextHint,stepCta,finalGo,todoAttrs,todoArrow} from '../v4/guide.js';
import {restockFor,restockGo} from '../v4/restock.js';

const SHOT_SCALE=45;   // effective seconds shown on the extraction bar
const TEMP_SCALE=90;   // °C shown on the milk thermometer
const SHOT_COLOR={sour:'#c48a45',bright:'#a3652d',balanced:'#6b3b1f',strong:'#4a2814',bitter:'#24130a'};
const DONE_COLOR={pale:'#f1dfb4',golden:'#d9a24a',dark:'#9a5a24',burnt:'#3a2618'};

const pay=(x,o)=>x.esc(JSON.stringify(o));
const cc=x=>x.cc||{};
const data=x=>x.room.data||{};
const lower=s=>String(s||'').toLowerCase();
const inv=(x,id)=>(x.content.inventory?.items?.cafe_bakery||[]).find(i=>i.id===id)||{id,name:id,emoji:'•',unit:''};
const bake=(x,id)=>(cc(x).bakes||[]).find(b=>b.id===id)||{id,name:id,emoji:'•',window:[10,20,30],allergens:[]};
const drink=(x,id)=>(cc(x).drinks||[]).find(d=>d.id===id)||{id,name:id,emoji:'☕'};
const bean=(x,id)=>(cc(x).beans||[]).find(b=>b.id===id)||{id,name:id,emoji:'🫘',unlock:1};
const milk=(x,id)=>(cc(x).milks||[]).find(m=>m.id===id)||{id,name:id,emoji:'🥛',unlock:1};
const art=(x,id)=>(cc(x).arts||[]).find(a=>a.id===id);
const cream=(x,id)=>(cc(x).creams||[]).find(c=>c.id===id)||{id,name:id,emoji:'🍦'};
const color=(x,id)=>(cc(x).colors||[]).find(c=>c.id===id)||{id,name:id,hex:'#fbf7ef'};
const stock=(x,id)=>x.room.inventory?.stock?.[id]??0;
const lvl=x=>x.room.level||1;
const letters=s=>String(s||'').normalize('NFC').toLocaleLowerCase('vi').replace(/[^\p{L}\p{N}\s]/gu,' ').split(/\s+/).filter(Boolean).join(' ');
const freshCount=(x,id)=>(data(x).case||[]).filter(l=>l.item===id&&l.state==='fresh'&&!l.sale).reduce((a,l)=>a+l.qty,0);

/* ---------- order shape (mirrors the server) ---------- */
const hidden=t=>t.needs?.style==='mood'&&!t.guessed;
const isTray=t=>!!t.needs?.party?.length;
const spec=(t,i)=>{const n=t.needs,p=n?.party;if(!p?.length)return n;return {...n,...p[i??t.cur??0]};};
const plated=t=>isTray(t)&&!!t.cups?.[t.cur];
const pendingOthers=t=>isTray(t)?(t.cups||[]).map((c,i)=>c?-1:i).filter(i=>i>=0&&i!==t.cur):[];
const started=d=>!!(d&&(d.container||d.shots?.length||d.dose||d.milk||d.pulling||d.steaming));

/* ---------- building blocks ---------- */
/** A tile button: stock badge (red at 0), selected outline, padlock, ★ for what the order needs. */
function tile(x,o){
  const attrs=o.go?`data-action="${o.go.act}"${Object.entries(o.go.data||{}).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}`:o.cmd?`data-command="${o.cmd}" data-payload="${pay(x,o.payload||{})}"`
    :o.action?`data-action="car:${o.action}"${Object.entries(o.data||{}).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}`:'';
  const cls=['tile',o.cls||'',o.selected?'is-selected':'',o.locked?'is-locked':'',o.empty?'is-empty':'',o.wanted?'wanted':''].filter(Boolean).join(' ');
  const badge=o.count!=null&&!o.locked?`<span class="count-badge${o.empty?' is-empty':''}" data-count="${x.esc(String(o.count))}">${x.esc(String(o.count))}</span>`:'';
  return `<button type="button" class="${cls}" ${attrs}${o.disabled||o.locked?' disabled':''} aria-pressed="${o.selected?'true':'false'}"${o.label?` aria-label="${x.esc(o.label)}"`:''}>${badge}<span class="tile-emoji" aria-hidden="true">${x.esc(o.emoji||'')}</span><b>${x.esc(o.name)}</b>${o.sub?`<small>${x.esc(o.sub)}</small>`:''}</button>`;
}
const seg=(x,action,key,value,label,current)=>`<button type="button" class="cb-seg ${current===value?'on is-selected':''}" data-action="car:${action}" data-${key}="${x.esc(value)}" aria-pressed="${current===value}">${x.esc(label)}</button>`;
/** One requirement row for ui-kit reqList (ok: true ✓ / false ✗ / null ○). */
const R=(ok,icon,label,value='',note='',tone='',go=null)=>({ok,icon,label,value,note,tone,go});
const bar=(cls,attrs,zones,fill,label)=>`<div class="cb-meter ${cls}" ${attrs}><div class="cb-track">${zones.map(([k,a,b])=>`<i class="cb-zone ${k}" style="left:${a}%;width:${Math.max(0,b-a)}%"></i>`).join('')}<b class="cb-fill" style="transform:translateX(${Math.min(100,Math.max(0,fill))-100}%)"></b></div><small class="cb-meter-label">${label}</small></div>`;

/* ---------- real-time meters (the server decides the result from its own clock) ---------- */
function shotMeter(x,start,flow){
  const e=cc(x).extract||{sour:20,bright:25,balanced:30,strong:35},s=SHOT_SCALE,p=v=>v/s*100;
  const eff=start?Math.max(0,x.now()-start)*flow:0;
  return bar('shot',`data-shot-start="${start||''}" data-flow="${flow||1}"`,[['sour',0,p(e.sour)],['bright',p(e.sour),p(e.bright)],['balanced',p(e.bright),p(e.balanced)],['strong',p(e.balanced),p(e.strong)],['bitter',p(e.strong),100]],p(eff),start?eff.toFixed(1)+' giây chiết':'Họng pha đang nghỉ');
}
function thermo(x,start){
  const st=cc(x).steam||{base:5,rate:4.2,cool:55,silky:68,hot:76},p=v=>v/TEMP_SCALE*100;
  const temp=start?st.base+st.rate*Math.max(0,x.now()-start):0;
  return bar('therm',`data-steam-start="${start||''}"`,[['cool',0,p(st.cool)],['silky',p(st.cool),p(st.silky)],['hot',p(st.silky),p(st.hot)],['scalded',p(st.hot),100]],p(temp),start?Math.round(temp)+' °C':'Vòi hơi tắt');
}
function rackMeter(x,r){
  const b=bake(x,r.item),[a,g,z]=b.window,scale=z+6,p=v=>v/scale*100,shift=Number(r.shift)||0,sec=Math.max(0,x.now()-r.start)+shift;
  return bar('rack',`data-oven-start="${r.start}" data-shift="${shift}" data-w="${a},${g},${z}"`,[['pale',0,p(a)],['golden',p(a),p(g)],['dark',p(g),p(z)],['burnt',p(z),100]],p(sec),sec.toFixed(1)+' giây'+(shift?' · lò nóng':''));
}

/* ---------- previews ---------- */
function cupArt(t,x){
  const d=t.drink,cls=['cb-cup',d.container||'none',d.size==='L'?'large':'',d.lid?'lidded':''].join(' ');
  if(hidden(t))return `<div class="cb-preview-empty"><span aria-hidden="true">💭</span><p class="muted small">Đoán món trước đã</p></div>`;
  if(plated(t))return `<div class="cb-preview-empty ok"><span aria-hidden="true">🛎️</span><p class="small">Khay đã đủ ly</p></div>`;
  if(!d.container)return `<div class="cb-preview-empty"><span aria-hidden="true">☕</span><p class="muted small">Chọn ly để bắt đầu</p></div>`;
  const layers=[];
  d.shots.forEach(s=>layers.push(`<i class="cb-layer coffee" style="--c:${SHOT_COLOR[s.x]||'#6b3b1f'}"></i>`));
  if(d.water)layers.push(`<i class="cb-layer water"></i>`);
  if(d.milk)layers.push(`<i class="cb-layer milk ${x.esc(d.milk.kind)}"></i>`);
  if(d.milk&&d.milk.mode==='steam')layers.push(`<i class="cb-layer foam ${d.milk.foam==='thick'?'thick':''}"></i>`);
  const a=d.art&&d.art!=='blob'?art(x,d.art)?.emoji:d.art==='blob'?'🫧':'';
  return `<div class="${cls}" role="img" aria-label="Ly đang pha">
    <div class="cb-cup-body">${layers.join('')}${d.ice?'<span class="cb-ice" aria-hidden="true">🧊🧊🧊</span>':''}${a?`<span class="cb-art-mark" aria-hidden="true">${a}</span>`:''}</div>
    ${d.container==='mug'?'<i class="cb-handle"></i>':''}${d.lid?'<i class="cb-lid"></i>':''}</div>`;
}
function bagArt(t,x){
  const items=t.bag.items;
  if(!items.length)return `<div class="cb-preview-empty"><span aria-hidden="true">🥐</span><p class="muted small">Gắp bánh từ tủ kính</p></div>`;
  return `<div class="cb-bag ${t.bag.bagged?'closed':''}" role="img" aria-label="Khay bánh"><div class="cb-bag-items">${items.map(i=>`<span title="${x.esc(bake(x,i.item).name)}">${x.esc(bake(x,i.item).emoji)}</span>`).join('')}</div>${t.bag.bagged?'<small>🛍️ đã gấp miệng túi</small>':''}</div>`;
}
function cakeArt(t,x){
  const k=t.cake;
  if(!k.sponge&&!k.baking)return `<div class="cb-preview-empty"><span aria-hidden="true">🎂</span><p class="muted small">Nướng cốt bánh trước</p></div>`;
  if(k.baking)return `<div class="cb-preview-empty"><span aria-hidden="true">🔥</span><p class="muted small">Cốt bánh đang trong lò</p></div>`;
  const hex=k.cream?color(x,k.color).hex:DONE_COLOR[k.sponge];
  return `<div class="cb-cake ${k.melted?'melted':''} ${k.boxed?'boxed':''}" role="img" aria-label="Bánh kem">
    <div class="cb-cake-top" style="--cream:${x.esc(hex)}">${k.text?`<span class="cb-cake-text">${x.esc(k.text)}</span>`:''}</div>
    <div class="cb-cake-side" style="--cream:${x.esc(hex)}"></div>${k.boxed?'<i class="cb-box"></i>':''}</div>`;
}
/** Tray of cups: ☕ done, 🫗 the one in hand, ◌ waiting. */
function trayCups(t){
  if(!isTray(t))return '';
  return `<p class="cb-traycups" aria-label="Khay ly">${t.cups.map((c,i)=>`<span class="${c?'on':''}${i===t.cur&&!c?' cur':''}">${c?'☕':i===t.cur?'🫗':'◌'}<small>${i+1}</small></span>`).join('')}</p>`;
}
/** Live one-line status of what is in hand. */
function status(t,x){
  const n=t.needs;
  if(n.kind==='pastry')return t.bag.items.length?`${t.bag.items.length} bánh trên khay${t.bag.bagged?' · đã vào túi':''}`:'Khay bánh còn trống';
  if(n.kind==='cake'){const k=t.cake;return k.baking?'Cốt bánh đang trong lò':!k.sponge?'Chưa có cốt bánh':[k.cream?`kem ${lower(color(x,k.color).name)}`:'chưa phủ kem',k.text?'đã viết chữ':'chưa viết chữ',k.boxed?'đã đóng hộp':''].filter(Boolean).join(' · ');}
  if(hidden(t))return 'Chưa rõ khách muốn món gì';
  if(plated(t))return `Đủ ${t.cups.length} ly trên khay`;
  const d=t.drink,tag=isTray(t)?`Ly ${t.cur+1}: `:'';
  if(!d.container)return tag+'chưa lấy ly';
  const c=(cc(x).containers||[]).find(v=>v.id===d.container);
  const parts=[`${c?.name||''} ${d.size==='L'?'lớn':'nhỏ'}`];
  if(d.ice)parts.push('có đá');
  parts.push(d.pulling?'đang chiết shot':d.shots.length?`${d.shots.length} shot`:d.dose?'tay cầm có bột':'chưa có espresso');
  if(d.water)parts.push('có nước');
  if(d.steaming)parts.push('đang đánh sữa');
  else if(d.milk)parts.push(lower(milk(x,d.milk.kind).name)+(d.milk.mode==='steam'?(d.milk.temp?` ${Math.round(d.milk.temp)} °C`:' nóng'):' lạnh'));
  if(d.art)parts.push(d.art==='blob'?'hình bị loang':'vẽ '+lower(art(x,d.art)?.name||''));
  if(d.container==='paper')parts.push(d.lid?'đã đậy nắp':'chưa đậy nắp');
  return tag+parts.join(' · ');
}

/* ---------- the order as a requirement list (checked live against what is in hand) ----------
 * Each row is also a step for the guide (guide.js): `go` is the one tap that does it (right cup,
 * right beans, right milk…), or the fix when it went wrong. The same rows drive the ticket, the
 * "Bước tiếp theo" hint and the bottom button. */
const CUP_ICON={paper:'🥤',glass:'🥃',mug:'☕'};
/** The shop's first day: the machine's timer stops shots and the steam wand (server AUTO_DAYS). */
const timer=x=>(x.room.day||1)<=1;
const dumpGo=(t,part='drink')=>part==='cake'?{cmd:'cb_dump',payload:{task:t.id,part},confirm:'Bỏ bánh này và làm lại? Nguyên liệu đã dùng được ghi hao hụt.',label:'🗑️ Bỏ bánh, làm lại'}
  :{cmd:'cb_dump',payload:{task:t.id,part},confirm:'Đổ ly này và làm lại từ đầu? Nguyên liệu đã dùng được ghi hao hụt.',label:'🗑️ Đổ ly, làm lại'};
// Out of a supply: the stock room, filtered to it (restock.js: opens an arrived crate first).
const restock=(x,name,ids)=>restockFor(x,ids,name);
/** What the shelf lacks for a recipe, as the server's _consume() checks it (each item at least its count): [{id, need, have}]. */
const lacks=(x,recipe)=>Object.entries(recipe||{}).filter(([k,q])=>q>0&&stock(x,k)<q).map(([id,q])=>({id,need:q,have:stock(x,id)}));
/** "🥚 thiếu 2 trứng gà": the first missing item, the words a short tile or button shows. */
const lackText=(x,short)=>{const s=short[0],i=inv(x,s.id);return `${i.emoji&&i.emoji!=='•'?i.emoji+' ':''}thiếu ${s.need-s.have} ${lower(i.name)}`;};
/** The step the shelf cannot supply becomes the way to supply it: "📦 Nhập trứng gà · thiếu 2" (an arrived crate is
 * opened first, an order on the way shows when it comes). A guide `go`; lackBtn is the same tap as a button. */
function lackGo(x,short,task){
  const g=restockGo(x.room,short,{task}),s=short[0],name=x.esc(lower(inv(x,s.id).name));
  return {...g,label:g.full||g.coming?g.label:g.ready?`📦 Mở thùng ${name} lên kệ`:`📦 Nhập ${name} · thiếu ${s.need-s.have}`};
}
const lackBtn=(x,short,task,style='small primary')=>{const g=lackGo(x,short,task);return x.button(g.label,g.act,g.data||{},style+' cb-lack');};
/** The lot to pick: today's bake first (yesterday's −50% when the guest asked for it). */
const lotFor=(x,id,old)=>(data(x).case||[]).find(l=>l.item===id&&l.qty>0&&(old?l.state==='day_old':l.state==='fresh'&&!l.sale));
function pickGo(t,x,id,old=false){
  const l=lotFor(x,id,old)||(old?lotFor(x,id,false):null),b=bake(x,id);
  if(!l)return bakeGo(t,x,id);
  return {cmd:'cb_pick',payload:{task:t.id,lot:l.id},label:`${x.esc(b.emoji)} Gắp ${x.esc(lower(b.name))}${l.state==='day_old'?' hôm qua':''}`};
}
const backGo=(t,x,i)=>({cmd:'cb_return',payload:{task:t.id,index:i},label:`↩️ Trả ${x.esc(lower(bake(x,t.bag.items[i].item).name))} về tủ`});
const bagGo=(t,x)=>t.bag.bagged||!t.bag.items.length?null:!t.bag.has_bag&&!stock(x,'bag')?restock(x,'túi giấy','bag'):{cmd:'cb_bag',payload:{task:t.id},label:'🛍️ Cho bánh vào túi'};
/** A small live bar for the bottom button and the hint (meters() moves it). */
const mini=(attrs,a,b)=>`<span class="cb-mini" ${attrs} style="--a:${a}%;--b:${b}%"><span class="cb-mini-track"><b class="cb-fill"></b></span><small class="cb-meter-label"></small></span>`;
const pct=(v,s)=>(v/s*100).toFixed(1);
function shotMini(x,start,flow){const e=cc(x).extract||{bright:25,balanced:30};return mini(`data-shot-start="${start}" data-flow="${flow||1}"`,pct(e.bright,SHOT_SCALE),pct(e.balanced,SHOT_SCALE));}
function thermMini(x,start){const st=cc(x).steam||{cool:55,silky:68};return mini(`data-steam-start="${start}"`,pct(st.cool,TEMP_SCALE),pct(st.silky,TEMP_SCALE));}
function rackMini(x,r){const [a,g,z]=bake(x,r.item).window;return mini(`data-oven-start="${r.start}" data-shift="${Number(r.shift)||0}" data-w="${a},${g},${z}"`,pct(a,z+6),pct(g,z+6));}

/** What latte art still waits for (game/careers/cafe_bakery.py cb_art), '' when it can be poured now. */
const artWait=d=>!d.shots.length?'Chiết shot trước':d.steaming?'Tắt vòi hơi trước':!(d.milk&&d.milk.mode==='steam')?'Đánh sữa nóng trước':'';
function drinkRows(t,x){
  if(hidden(t))return [R(null,'💭','Đoán đúng món khách đang thèm','','','',{sel:'.cb-guess'})];
  if(plated(t))return [R(true,'🛎️',`Đủ ${t.cups.length} ly trên khay, giao một lượt`)];
  const n=spec(t),d=t.drink,dk=drink(x,n.drink),rows=[],sl=cc(x).shot_label||{},id=t.id,dump=dumpGo(t),auto=timer(x);
  const cowMilk=!!(d.milk&&milk(x,d.milk.kind).lactose);
  if(n.lactose)rows.push(R(d.milk?!cowMilk:null,'⚠️','Không sữa bò','','Khách không dung nạp lactose','danger',cowMilk?dump:null));
  if(n.decaf){const bad=d.shots.some(s=>s.beans!=='decaf');rows.push(R(d.shots.length?!bad:null,'⚠️','Chỉ hạt decaf','','Khách phải kiêng caffeine','danger',bad?dump:null));}
  const want=n.takeaway?'paper':n.iced?'glass':'mug';
  const cname={paper:'Ly giấy mang về',glass:'Ly thủy tinh',mug:'Tách sứ'}[want],size=n.size==='L'?'ly lớn':'ly nhỏ';
  const wrongCup=d.container&&(d.container!==want||d.size!==n.size);
  const cupGo=d.container?(wrongCup?dump:null):want==='paper'&&!stock(x,'cup')?restock(x,'ly giấy','cup')
    :{cmd:'cb_cup',payload:{task:id,kind:want,size:n.size},label:`${CUP_ICON[want]} ${x.esc(cname)} · ${n.size==='L'?'lớn':'nhỏ'}`};
  rows.push(R(d.container?!wrongCup:null,CUP_ICON[want],cname,size,wrongCup?`đang dùng ${lower((cc(x).containers||[]).find(c=>c.id===d.container)?.name||'')} ${d.size==='L'?'lớn':'nhỏ'}`:'','',cupGo));
  if(n.iced)rows.push(R(d.ice?true:null,'🧊','Đá đầy ly','','','',d.ice?null:{cmd:'cb_ice',payload:{task:id},label:'🧊 Múc đá đầy ly'}));
  else if(d.ice)rows.push(R(false,'🧊','Món nóng: không bỏ đá','','','',dump));
  const got=d.shots.length,good=d.shots.filter(s=>['balanced','bright','strong'].includes(s.x)&&s.beans===n.beans).length;
  const grams=cc(x).dose?.target||18;
  let shotGo=null;
  if(d.pulling)shotGo={cmd:'cb_stop',payload:{task:id},label:`⏹️ Dừng chiết ở vạch xanh${shotMini(x,d.pulling,(data(x).groups||[]).find(g=>g.task===id)?.flow)}`};
  else if(d.dose)shotGo={cmd:'cb_pull',payload:auto?{task:id,auto:true}:{task:id},label:auto?'▶️ Chiết shot · tự dừng':'▶️ Chiết shot'};
  else if(got<n.shots)shotGo=stock(x,'beans_'+n.beans)?{cmd:'cb_dose',payload:{task:id,beans:n.beans,grind:'fine',grams},label:`⚖️ Xay ${grams} g ${x.esc(bean(x,n.beans).name)}`}:restock(x,'hạt '+bean(x,n.beans).name,'beans_'+n.beans);
  else if(got>n.shots)shotGo=dump;
  rows.push(R(!got?null:got<n.shots&&good===got?null:got===n.shots&&good===got,'☕',`${n.shots} shot ${bean(x,n.beans).name}`,got?`${got}/${n.shots}`:'25–30 giây',d.shots.map(s=>`${s.sec}s ${sl[s.x]||s.x}`).join(' · '),'',shotGo));
  if(dk.water)rows.push(R(d.water?true:null,'💧',n.iced?'Nước lạnh':'Nước nóng 90 °C','','','',d.water?null:{cmd:'cb_water',payload:{task:id},label:'💧 Thêm nước'}));
  else if(d.water)rows.push(R(false,'💧','Món này không pha nước','','','',dump));
  if(n.milk){
    const m=milk(x,n.milk),mm=d.milk,wrong=!!(mm&&(mm.kind!==n.milk||mm.mode!==(n.iced?'cold':'steam')));
    const ok=mm?!wrong&&(n.iced||(mm.foam===n.foam&&['silky','hot'].includes(mm.tex))):null;
    const foam=n.foam==='thick'?'dày':'mỏng';
    const go=d.steaming?{cmd:'cb_milk_stop',payload:{task:id},label:`⏹️ Tắt vòi ở vạch xanh${thermMini(x,d.steaming)}`}
      :mm?(wrong?dump:null):!stock(x,n.milk)?restock(x,lower(m.name),n.milk)
      :n.iced?{cmd:'cb_milk',payload:{task:id,milk:n.milk,mode:'cold'},label:`${x.esc(m.emoji||'🥛')} Rót ${x.esc(lower(m.name))} lạnh`}
      :{cmd:'cb_milk',payload:auto?{task:id,milk:n.milk,mode:'steam',foam:n.foam,auto:true}:{task:id,milk:n.milk,mode:'steam',foam:n.foam},label:`♨️ Đánh ${x.esc(lower(m.name))}${auto?' · tự tắt':''}`};
    rows.push(R(ok,m.emoji||'🥛',n.iced?m.name:`${m.name}, bọt ${foam}`,mm?.temp?Math.round(mm.temp)+' °C':n.iced?'rót lạnh':'55–68 °C','','',go));
  }else if(d.milk)rows.push(R(false,'🚫','Món này không có sữa','','','',dump));
  if(n.art){
    // cb_art pours steamed milk onto a pulled shot: until both are in the cup the row says which comes first
    // and offers no tap (the server would refuse "Rót sữa lên espresso — chiết shot trước đã.").
    const a=art(x,n.art),hot=d.milk&&d.milk.mode==='steam'&&d.milk.tex!=='silky',wait=artWait(d);
    rows.push(R(d.art?d.art===n.art:null,a?.emoji||'🎨',`Vẽ ${lower(a?.name||n.art)}`,'',d.art==='blob'?'hình bị loang — sữa phải 55–68 °C':!d.art&&wait?wait:!d.art&&hot?'sữa không mịn, hình sẽ loang':'','',
      d.art||wait?null:{cmd:'cb_art',payload:{task:id,pattern:n.art},label:`${x.esc(a?.emoji||'🎨')} Rót hình ${x.esc(lower(a?.name||n.art))}`}));
  }
  const items=t.bag.items;
  for(const [k,q] of Object.entries(n.pastry||{})){
    const have=items.filter(i=>i.item===k).length,b=bake(x,k);
    const go=t.bag.bagged?null:have<q?pickGo(t,x,k):have>q?backGo(t,x,items.findIndex(i=>i.item===k)):null;
    rows.push(R(have===q?true:have>q?false:null,b.emoji,`${q} ${lower(b.name)} ra lò hôm nay`,have?`${have}/${q}`:'','','',go));
  }
  if(Object.keys(n.pastry||{}).length&&n.takeaway)rows.push(R(t.bag.bagged?true:null,'🛍️','Cho bánh vào túi','','','',bagGo(t,x)));
  if(want==='paper')rows.push(R(d.lid?true:null,'🏷️','Đậy nắp + tem tên','','','',d.lid||d.container!=='paper'?null:{cmd:'cb_lid',payload:{task:id},label:'🥤 Đậy nắp + dán tem tên'}));
  return rows;
}
function pastryRows(t,x){
  const n=t.needs,rows=[],items=t.bag.items,day=x.room.day,open=!t.bag.bagged;
  if(n.allergy){const a=(cc(x).allergen_label||{})[n.allergy]||n.allergy,hit=items.findIndex(i=>bake(x,i.item).allergens.includes(n.allergy));
    rows.push(R(items.length?hit<0:null,'⚠️',`Không có ${a}`,'',`Khách dị ứng ${a}`,'danger',hit>=0?backGo(t,x,hit):null));}
  for(const [k,q] of Object.entries(n.items)){const have=items.filter(i=>i.item===k).length,b=bake(x,k);
    rows.push(R(have===q?true:have>q?false:null,b.emoji,`${q} ${lower(b.name)}`,have?`${have}/${q}`:'','','',!open?null:have<q?pickGo(t,x,k,n.day_old_ok):have>q?backGo(t,x,items.findIndex(i=>i.item===k)):null));}
  for(const k of new Set(items.map(i=>i.item)))if(!n.items[k])rows.push(R(false,bake(x,k).emoji,`${bake(x,k).name}: khách không gọi`,'','','',backGo(t,x,items.findIndex(i=>i.item===k))));
  const old=items.findIndex(i=>day-i.day>bake(x,i.item).fresh),weak=items.filter(i=>['pale','flat','dense'].includes(i.q)).length,olds=items.filter(i=>day-i.day>bake(x,i.item).fresh).length;
  rows.push(R(items.length?(n.day_old_ok||old<0):null,'🕐',n.day_old_ok?'Bánh hôm qua −50% (khách đồng ý)':'Bánh ra lò hôm nay',olds?`${olds} bánh hôm qua`:'',weak?`${weak} bánh nướng chưa đạt`:'','',!n.day_old_ok&&old>=0?backGo(t,x,old):null));
  if(n.takeaway)rows.push(R(t.bag.bagged?true:null,'🛍️','Túi giấy + tem ngày','','','',bagGo(t,x)));
  return rows;
}
/** Waiting some beats (a sponge cooling, dough rising): something useful that lets time pass. */
function waitGo(t,x,why='chờ bánh nguội'){
  const d=data(x),s=d.starter||{},w=` · ${x.esc(why)}`;
  if(d.clean_day!==x.room.day)return {cmd:'cb_clean',payload:{},label:`🧽 Vệ sinh máy${w}`};
  if(s.fed_today===false&&stock(x,'flour')>=1)return {cmd:'cb_feed',payload:{},label:`🫙 Cho Bé Men ăn${w}`};
  const o=openTasks(x).find(v=>v.id!==t.id);
  return o?{act:'job',data:{task:o.id},label:`👉 Làm order khác${w}`}:x.room.more_gate?{cmd:'advance',payload:{},label:`⏳ Chờ một nhịp${w}`}:{cmd:'more_work',payload:{},label:`＋ Đón khách mới${w}`};
}
/** The case has none of this bake: the next step of making it (shape → rise → bake → take out).
 * `early` steps go first in the guide: shaping (the dough rises while the drink is made) and
 * taking a tray out (it burns if it waits). Baking itself waits for its turn, so a tray is not
 * left in the oven while the barista times a shot. */
function bakeGo(t,x,id){
  const d=data(x),b=bake(x,id),name=x.esc(lower(b.name)),oven=d.oven||[],full={act:'car:tab',data:{tab:'oven'},label:'🔥 Lò đầy: lấy bớt một khay ra'};
  const rack=oven.find(r=>r.item===id&&!r.task);
  if(rack)return {cmd:'cb_unload',payload:{rack:rack.id},label:`🧤 Lấy ${name} ra ở vạch xanh${rackMini(x,rack)}`,early:true};
  const tray=[...(d.proof||[]).filter(p=>!p.left),...(d.cold||[]).filter(c=>c.bakeable)].find(p=>p.item===id);
  if(tray)return oven.length>=2?full:{cmd:'cb_bake',payload:{item:id,tray:tray.id},label:`🔥 Cho khay ${name} vào lò`};
  const rising=(d.proof||[]).find(p=>p.item===id);
  if(rising)return waitGo(t,x,`bột nở, còn ${rising.left} nhịp`);
  const short=lacks(x,b.recipe);if(short.length)return lackGo(x,short,t?.id);
  if(!b.proof)return oven.length>=2?full:{cmd:'cb_bake',payload:{item:id},label:`🔥 Nướng một mẻ ${name}`};
  if((d.proof||[]).length>=2)return {act:'car:tab',data:{tab:'oven'},label:'🔥 Tủ ủ đầy: nướng bớt một khay'};
  return {cmd:'cb_shape',payload:{item:id},label:`${x.esc(b.emoji)} Nhào một khay ${name}`,early:true};
}
function cakeRows(t,x){
  const n=t.needs,k=t.cake,cool=data(x).cooling?.[t.id],id=t.id,oven=data(x).oven||[];
  const wrongText=k.text&&letters(k.text)!==letters(n.text),rack=oven.find(r=>r.task===id),cr=cream(x,n.cream),col=color(x,n.color);
  const spongeGo=k.baking?(rack?{cmd:'cb_unload',payload:{rack:rack.id},label:`🧤 Lấy cốt bánh ra ở vạch xanh${rackMini(x,rack)}`}:null)
    :!k.sponge?(oven.length>=2?{act:'car:tab',data:{tab:'oven'},label:'🔥 Lò đầy: lấy bớt một khay ra'}:lacks(x,bake(x,'sponge').recipe).length?lackGo(x,lacks(x,bake(x,'sponge').recipe),id):{cmd:'cb_bake',payload:{item:'sponge',task:id},label:'🎂 Nướng cốt bánh kem'})
    :['pale','burnt'].includes(k.sponge)?dumpGo(t,'cake'):null;
  const warm=k.sponge&&!k.cream&&cool;
  const crShort=lacks(x,cr.recipe);
  const frostGo=['golden','dark'].includes(k.sponge)&&!k.cream&&!cool?crShort.length?lackGo(x,crShort,id):{cmd:'cb_frost',payload:{task:id,cream:n.cream,color:n.color},label:`${x.esc(cr.emoji)} Phủ ${x.esc(lower(cr.name))} ${x.esc(lower(col.name))}`}:null;
  const textGo=wrongText?(k.boxed?null:{cmd:'cb_scrape',payload:{task:id},confirm:'Cạo lớp chữ và láng lại mặt kem?',label:'🧽 Cạo chữ, viết lại'}):k.cream&&!k.text?{act:'car:write',data:{task:id},label:'✍️ Viết chữ lên bánh'}:null;
  const boxGo=k.cream&&k.text&&!wrongText&&!k.boxed?(stock(x,'cake_box')?{cmd:'cb_box',payload:{task:id},label:'📦 Đóng hộp + nến + dao'}:restock(x,'hộp bánh','cake_box')):null;
  return [
    R(k.sponge?['golden','dark'].includes(k.sponge):null,'🍰','Cốt bông lan vàng đều',k.sponge?{pale:'sống ruột',golden:'vàng đều',dark:'hơi sậm',burnt:'cháy'}[k.sponge]:k.baking?'đang trong lò':'','','',spongeGo),
    R(k.cream?!k.melted:k.sponge?(cool?null:true):null,'🌬️','Để nguội rồi mới phủ kem',warm?`chờ ${cool} nhịp`:'',k.melted?'kem chảy xệ':'','',warm?waitGo(t,x):null),
    R(k.cream?k.cream===n.cream&&k.color===n.color:null,cr.emoji,cr.name,lower(col.name),'','',frostGo),
    R(k.text?!wrongText:null,'✍️',`“${n.text}”`,'',wrongText?`đang ghi “${k.text}”`:'Viết đúng từng dấu',k.text&&!wrongText?'':'warn',textGo),
    R(k.boxed?true:null,'📦','Hộp + nến + dao','','','',boxGo)];
}
const rowsOf=(t,x)=>t.needs.kind==='drink'?drinkRows(t,x):t.needs.kind==='pastry'?pastryRows(t,x):cakeRows(t,x);
const MARK={true:['ok','✓','đúng'],false:['bad','✗','sai'],null:['','○','chưa làm']};
/** ui-kit reqList, with rows that are not done yet tappable (they do the step). */
function rlist(rows,x,label){
  return `<ul class="req-list" aria-label="${x.esc(label)}">${rows.map(r=>{
    const [cls,mark,said]=MARK[r.ok===true?'true':r.ok===false?'false':'null'],tap=todoAttrs(r);
    return `<li class="req-row ${cls}${r.tone?' tone-'+x.esc(r.tone):''}${tap?' gd-todo':''}"${tap}><span class="req-mark" aria-label="${said}">${mark}</span>${r.icon?`<span class="req-icon" aria-hidden="true">${x.esc(r.icon)}</span>`:''}<span class="req-label">${x.esc(r.label)}${r.note?`<small>${x.esc(r.note)}</small>`:''}</span>${r.value?`<b class="req-value">${x.esc(r.value)}</b>`:''}${todoArrow(r)}</li>`;
  }).join('')}</ul>`;
}

/* ---------- today: rules, the office box, the display case ---------- */
function banners(x){
  const d=data(x),r=d.rules||{},out=[];
  if(r.influencer==='next')out.push('📱 Có người đang quay clip ly tiếp theo. Làm thật chuẩn nhé!');
  if(r.grinder)out.push('⚙️ Máy xay xay không đều: hôm nay vị cà phê khó đạt điểm tuyệt đối.');
  if(r.sour_milk)out.push('🥛 Sữa tươi hôm nay có mùi: ly có sữa tươi sẽ bị khách chê.');
  if(r.hot_oven)out.push(`🔥 Lò nóng hơn thường: bánh chín sớm hơn ${d.oven_shift||cc(x).hot_oven||3} giây.`);
  return out.length?`<ul class="cb-today">${out.map(s=>`<li>${x.esc(s)}</li>`).join('')}</ul>`:'';
}
function boxCard(x){
  const d=data(x),b=d.rules?.box;
  if(!b||b.status!=='open')return '';
  const it=bake(x,b.item),have=freshCount(x,b.item),left=Math.max(0,b.due+1-(Number(d.day?.served)||0)),ok=have>=b.goal;
  return `<article class="card cb-boxorder"><div class="cb-box-head"><h4>📦 Hộp bánh cho văn phòng</h4><b class="cb-box-count${ok?' ok':''}">${Math.min(have,b.goal)}/${b.goal} ${x.esc(it.emoji)}</b></div>
    <div class="cb-progress" aria-hidden="true"><i style="width:${Math.min(100,have/b.goal*100)}%"></i></div>
    <p class="small">Cần ${b.goal} ${x.esc(lower(it.name))} ra lò hôm nay, ${b.pay} xu mỗi cái. Văn phòng chỉ chờ thêm ${left} lượt khách.</p>
    ${x.cmd('📦 Gửi hộp bánh','cb_box_send',{},ok?'primary small':'ghost small',!ok)}</article>`;
}
function shelf(x){
  const d=data(x),wants=d.wants||[];
  if(!wants.length)return '';
  const sale=(d.case||[]).filter(l=>l.sale&&l.state==='day_old').reduce((a,l)=>a+l.qty,0),buyers=d.buyers??1;
  return `<section class="cb-shelf" aria-label="Tủ kính bán lẻ"><p class="cb-shelf-head"><b>🧁 Tủ kính</b><small>${buyers?`Mỗi lượt giao có ${buyers} khách ghé mua bánh lẻ`:'Hôm nay vắng khách mua lẻ'}${sale?` · rổ −50%: ${sale}`:''}</small></p>
    <div class="cb-shelf-row">${wants.map(id=>{const b=bake(x,id),q=freshCount(x,id);return `<span class="cb-shelf-item${q?'':' is-empty'}"><span class="count-badge${q?'':' is-empty'}" data-count="${q}">${q}</span><span class="cb-shelf-emoji" aria-hidden="true">${x.esc(b.emoji)}</span><small>${x.esc(b.name)}</small></span>`;}).join('')}</div></section>`;
}
const extras=x=>banners(x)+boxCard(x);

/* ---------- the order ---------- */
/** Short headline of one drink: what it is, hot or iced, where it is drunk. */
function drinkLine(n,x){
  const d=drink(x,n.drink);
  return `${x.esc(d.emoji)} <b>${x.esc(d.name)}</b> · ${n.iced?'đá':'nóng'} · ${n.takeaway?'mang về':'tại quán'}`;
}
/** Mood order: the guest's feeling and three drinks to pick from. */
function moodCard(t,x){
  const m=t.needs.mood,used=t.guesses||[];
  return `<div class="cb-mood"><p class="cb-bubble">💭 “${x.esc(m.text)}”</p>${m.clue?`<p class="cb-clue">🔎 Khách lắc đầu, nói thêm: “${x.esc(m.clue)}”</p>`:''}
    <p class="cb-ask"><b>Khách đang thèm món nào?</b></p>
    <div class="tile-grid cb-guess" role="group" aria-label="Chọn món hợp ý khách">${m.options.map(id=>{const d=drink(x,id),no=used.includes(id);
      return tile(x,{emoji:d.emoji,name:d.name,sub:no?'khách lắc đầu':'',cmd:'cb_guess',payload:{task:t.id,drink:id},disabled:no,cls:no?'struck':'',label:no?`${d.name}: khách đã lắc đầu`:`Mời khách ${d.name}`});}).join('')}</div></div>`;
}
/** A tray: one row per cup. Tap a waiting cup to switch, a finished one to take it back. */
function trayTabs(t,x){
  const busy=started(t.drink)&&!plated(t);
  return `<div class="cb-party" role="tablist" aria-label="Các ly trong khay">${t.needs.party.map((p,i)=>{
    const sp={...t.needs,...p},done=!!t.cups[i],on=i===t.cur&&!done,off=on||(busy&&!on);
    return `<button type="button" role="tab" class="cb-cupline${on?' on is-selected':''}${done?' done':''}" data-command="cb_tab" data-payload="${pay(x,{task:t.id,index:i})}" aria-selected="${on}"${off?' disabled':''}>
      <span class="cb-cupno" aria-hidden="true">${done?'✓':i+1}</span><span class="cb-cuptext"><small>Ly ${i+1} · ${done?'trên khay · bấm để sửa':on?'đang làm':busy?'chờ ly đang làm':'bấm để làm'}</small><span>${drinkLine(sp,x)}${sp.lactose||sp.decaf?' <b class="cb-warn">⚠️</b>':''}</span></span></button>`;
  }).join('')}</div>`;
}
function ticket(t,x){
  const who=x.npc(t.npc),n=t.needs,g=t.guest||{};
  const tags=[`<span class="tag">${x.esc(g.emoji||'🙂')} ${x.esc(g.label||'Khách')}</span>`];
  let body='';
  if(n.kind==='drink'){
    if(hidden(t)){tags.push('<span class="tag amber">💭 Đoán ý khách</span>');body=moodCard(t,x);}
    else{
      if(n.style==='mood')tags.push(`<span class="tag green">💡 Đã hiểu ý${(t.guesses||[]).length===1?' ngay':''}</span>`);
      const list=rlist(drinkRows(t,x),x,isTray(t)?`Phiếu ly ${t.cur+1}`:'Phiếu order');
      if(isTray(t)){tags.push(`<span class="tag">☕ Khay ${n.party.length} ly</span>`);body=trayTabs(t,x)+list;}
      else body=`<p class="cb-order-head">${drinkLine(n,x)}</p>${list}`;
      if(n.style==='mood'&&n.mood?.text)body=`<p class="cb-bubble small">💭 “${x.esc(n.mood.text)}”</p>`+body;
    }
  }else if(n.kind==='pastry'){
    body=`<p class="cb-order-head">🛍️ <b>Bánh ở tủ kính</b> · ${n.takeaway?'mang về':'tại quán'}</p>${rlist(pastryRows(t,x),x,'Phiếu order')}`;
    if(n.day_old_ok)tags.push('<span class="tag amber">Bánh hôm qua −50%</span>');
    if(n.allergy)tags.push(`<span class="tag danger">⚠️ Dị ứng ${x.esc((cc(x).allergen_label||{})[n.allergy]||n.allergy)}</span>`);
  }else{
    body=`<p class="cb-order-head">🎂 <b>Bánh kem đặt trước</b> · <i class="cb-dot" style="background:${x.esc(color(x,n.color).hex)}"></i> ${x.esc(lower(color(x,n.color).name))}</p>${rlist(cakeRows(t,x),x,'Phiếu đặt bánh')}`;
  }
  const price=t.quoted_price!=null?x.money(t.quoted_price):'…';
  return `<article class="card ticket cb-ticket"><div class="cb-ticket-head">${x.portrait(who,44)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3><b class="price">${price}</b></div>
    <p class="cb-tags">${tags.join(' ')}</p></div></div>
    ${body}${n.note?`<p class="cb-note">💬 “${x.esc(n.note)}”</p>`:''}${regularNotes(t,x)}${patience(t.patience)}</article>`;
}
/** What the notes card knows about this guest, with a greeting (once per visit). */
function regularNotes(t,x){
  const r=(data(x).book||[]).find(b=>b.npc===t.npc);
  if(!t.regular||!r?.notes?.length)return '';
  const greet=t.greeted?'<span class="tag green">👋 Đã chào món quen</span>':x.cmd('👋 Chào món quen','cb_greet',{task:t.id},'small');
  return `<div class="cb-regular">${fold(`📒 Khách quen · ${r.visits} lần ghé${t.greeted?' · đã chào':''}`,`${noteList(r.notes,x)}<div class="row wrap">${greet}</div>`,!t.greeted&&!t.known)}</div>`;
}
const noteList=(notes,x)=>`<ul class="cb-notes">${notes.map(n=>`<li class="${n.tone==='danger'?'danger':''}"><span aria-hidden="true">${x.esc(n.icon)}</span><span>${x.esc(n.text)}</span></li>`).join('')}</ul>`;

/* ---------- station panels ---------- */
/** Locked things in one line, "🔒 2 món mở ở cấp 2–3" (names and levels in the tooltip). */
function lockChip(x,list){
  if(!list.length)return '';
  const lv=list.map(i=>Number(i.unlock)||1),lo=Math.min(...lv),hi=Math.max(...lv);
  const names=list.map(i=>`${i.name} (cấp ${Number(i.unlock)||1})`).join(', ');
  return `<p class="cb-lock" title="${x.esc(names)}" aria-label="${x.esc(`Chưa mở: ${names}`)}">🔒 ${list.length} món mở ở cấp ${lo===hi?lo:`${lo}–${hi}`}</p>`;
}
/** The bar station the cup in hand is at (1 cup … 7 pastry; 0 = nothing left), read from the cup
 * in the same order as the ticket rows. Only this station is open; the others are one line. */
function stationNow(t,x){
  const n=spec(t),d=t.drink,dk=drink(x,n.drink);
  if(!d.container)return 1;
  if(d.pulling||d.dose)return 3;
  if(d.steaming)return 4;
  if(n.iced&&!d.ice)return 1;
  if(d.shots.length<n.shots)return 2;
  if(dk.water&&!d.water)return 1;
  if(n.milk&&!d.milk)return 4;
  if(n.art&&!d.art)return 5;
  if(Object.entries(n.pastry||{}).some(([k,q])=>t.bag.items.filter(i=>i.item===k).length<q))return 7;
  if(d.container==='paper'&&!d.lid)return 6;
  return 0;
}
/** One bar station: open when it is the current one (until the player folds it), else one line
 * "✓ 2 · Xay … · 18 g" that a tap opens. Not a <details>: the sheet host restores every <details> by
 * position after a re-render, which would keep the old station open. The body is drawn only when open. */
function station(x,t,cur,no,title,note,done,body){
  const key=`${t.id}-${t.cur||0}-${cur}-${no}`,open=x.ui.cbSt?.[key]??no===cur;
  return `<section class="cb-st${no===cur?' now':''}${done?' done':''}${open?' open':''}"><button type="button" class="cb-st-sum" data-action="car:st" data-key="${x.esc(key)}" data-open="${open?1:0}" aria-expanded="${open}">${done?'✓ ':''}${no} · ${x.esc(title)}${note?` <small>· ${x.esc(note)}</small>`:''}</button>${open?`<div class="cb-st-body">${body}</div>`:''}</section>`;
}
function barPanel(t,x){
  if(hidden(t))return `<p class="notice amber">🤔 Chưa rõ khách muốn món gì.</p>`;
  if(plated(t))return `<p class="notice">☕ Đủ ${t.cups.length} ly trên khay.</p>`;
  const n=spec(t),d=t.drink,ui=x.ui,level=lvl(x),dd=data(x),groups=dd.groups||[],wand=dd.wand||[],r=dd.rules||{};
  const size=d.size||ui.size||'S',want=n.takeaway?'paper':n.iced?'glass':'mug';
  const cups=(cc(x).containers||[]).map(c=>{const q=c.id==='paper'?stock(x,'cup'):null;
    return tile(x,{emoji:c.emoji,name:c.name,sub:c.note,count:q,empty:q===0,cmd:'cb_cup',payload:{task:t.id,kind:c.id,size},selected:d.container===c.id,wanted:!d.container&&c.id===want,disabled:!!d.container||q===0,
      label:`${c.name}${q!=null?`, còn ${q}`:''}`});}).join('');
  const sizes=`<div class="cb-segs" role="group" aria-label="Cỡ ly">${seg(x,'size','size','S','Ly nhỏ',size)}${seg(x,'size','size','L','Ly lớn',size)}</div>`;
  const extra=`<div class="row wrap">${x.cmd('🧊 Múc đá','cb_ice',{task:t.id},'ghost small',!d.container||d.ice||d.container==='mug')}${x.cmd('💧 Thêm nước','cb_water',{task:t.id},'ghost small',!d.container||d.water)}</div>`;
  const beanShut=(cc(x).beans||[]).filter(b=>b.unlock>level&&n.beans!==b.id);
  const beans=(cc(x).beans||[]).filter(b=>!beanShut.includes(b)).map(b=>{const locked=b.unlock>level&&n.beans!==b.id,q=stock(x,'beans_'+b.id);
    return tile(x,{emoji:b.emoji,name:b.name,sub:locked?`cấp ${b.unlock}`:b.note,count:q,empty:!q,action:'beans',data:{beans:b.id},selected:ui.beans===b.id,locked,wanted:!d.shots.length&&n.beans===b.id,
      label:locked?`Hạt ${b.name}, mở ở cấp ${b.unlock}`:`Hạt ${b.name}, còn ${q} liều`});}).join('');
  const grinds=`<div class="cb-segs" role="group" aria-label="Độ xay">${Object.entries(cc(x).grind_label||{}).map(([k,l])=>seg(x,'grind','grind',k,l,ui.grind)).join('')}</div>`;
  const grams=ui.grams??(cc(x).dose?.target||18);
  const dose=`<div class="cb-stepper" role="group" aria-label="Định lượng bột"><button type="button" class="btn ghost small" data-action="car:grams" data-step="-1" aria-label="Bớt 1 gam">−</button><b>${grams} g</b><button type="button" class="btn ghost small" data-action="car:grams" data-step="1" aria-label="Thêm 1 gam">+</button></div>`;
  const canDose=d.container&&!d.dose&&!d.pulling&&ui.beans&&ui.grind&&d.shots.length<3&&stock(x,'beans_'+ui.beans)>0;
  const full=groups.length>=(cc(x).groups||2);
  const auto=timer(x),pullBtn=d.pulling?x.cmd('⏹️ Dừng chiết','cb_stop',{task:t.id},'primary'):x.cmd(auto?'▶️ Chiết shot (máy tự dừng)':'▶️ Chiết shot','cb_pull',auto?{task:t.id,auto:true}:{task:t.id},d.dose?'primary':'',!d.dose||full);
  const myFlow=groups.find(g=>g.task===t.id)?.flow||1;
  const others=groups.filter(g=>g.task!==t.id).map(g=>`<div class="cb-other"><small class="muted">Họng pha kia · ly khác</small>${shotMeter(x,g.start,g.flow)}${x.cmd('⏹️ Dừng ly đó','cb_stop',{task:g.task},'ghost small')}</div>`).join('');
  const shots=d.shots.length?`<div class="row wrap cb-shots">${d.shots.map((s,i)=>`<span class="tag ${s.x==='balanced'?'green':['sour','bitter'].includes(s.x)?'danger':'amber'}">Shot ${i+1}: ${s.sec}s · ${x.esc((cc(x).shot_label||{})[s.x]||s.x)}</span>`).join('')}</div>`:'';
  const milkShut=(cc(x).milks||[]).filter(m=>m.unlock>level&&n.milk!==m.id);
  const milks=(cc(x).milks||[]).filter(m=>!milkShut.includes(m)).map(m=>{const locked=m.unlock>level&&n.milk!==m.id,q=stock(x,m.id),sour=r.sour_milk&&m.id==='milk';
    return tile(x,{emoji:m.emoji,name:m.name,sub:locked?`cấp ${m.unlock}`:sour?'⚠️ có mùi':m.lactose?'có lactose':'không lactose',count:q,empty:!q,action:'milk',data:{milk:m.id},selected:ui.milk===m.id,locked,wanted:!d.milk&&n.milk===m.id,
      label:locked?`${m.name}, mở ở cấp ${m.unlock}`:`${m.name}, còn ${q} ca`});}).join('');
  const foam=`<div class="cb-segs" role="group" aria-label="Độ bọt">${seg(x,'foam','foam','thin','Bọt mỏng (latte)',ui.foam)}${seg(x,'foam','foam','thick','Bọt dày (cappu)',ui.foam)}</div>`;
  const mk=ui.milk?milk(x,ui.milk):null,busyWand=wand.some(w=>w.task!==t.id);
  const milkBtns=d.steaming?x.cmd('⏹️ Tắt vòi hơi','cb_milk_stop',{task:t.id},'primary')
    :`${x.cmd(auto?'♨️ Đánh nóng (máy tự tắt)':'♨️ Đánh nóng','cb_milk',{task:t.id,milk:ui.milk||'',mode:'steam',foam:ui.foam||'',...(auto?{auto:true}:{})},'',!d.container||!!d.milk||!mk||!mk.steam||!ui.foam||busyWand||!stock(x,ui.milk))}${x.cmd('🧊 Rót lạnh','cb_milk',{task:t.id,milk:ui.milk||'',mode:'cold'},'ghost',!d.container||!!d.milk||!mk||!stock(x,ui.milk))}`;
  const artShut=(cc(x).arts||[]).filter(a=>a.unlock>level&&n.art!==a.id);
  const arts=(cc(x).arts||[]).filter(a=>!artShut.includes(a)).map(a=>{const locked=a.unlock>level&&n.art!==a.id;
    const wait=d.art?'':artWait(d);
    return tile(x,{emoji:a.emoji,name:a.name,sub:locked?`cấp ${a.unlock}`:wait||'rót tạo hình',cmd:'cb_art',payload:{task:t.id,pattern:a.id},locked,selected:d.art===a.id,wanted:!d.art&&!wait&&n.art===a.id,
      disabled:!!wait||!!d.art,label:locked?`Hình ${a.name}, mở ở cấp ${a.unlock}`:wait?`Rót hình ${a.name}: ${wait.toLowerCase()}`:`Rót hình ${a.name}`});}).join('');
  const pastry=Object.keys(n.pastry||{}).length,cur=stationNow(t,x),dk=drink(x,n.drink),S=(...a)=>station(x,t,cur,...a);
  const cname=(cc(x).containers||[]).find(c=>c.id===d.container)?.name||'';
  const shotLine=d.shots.map((s,i)=>`Shot ${i+1}: ${s.sec}s`).join(' · ');
  const picked=t.bag.items.length,wantPastry=Object.values(n.pastry||{}).reduce((a,b)=>a+b,0);
  // Every station stays reachable (a wrong tap is still possible and still costs); only the current one is open.
  return `<div class="cb-stations">${S(1,'Ly',d.container?`${cname} ${d.size==='L'?'lớn':'nhỏ'}${d.ice?' · có đá':''}${d.water?' · có nước':''}`:'',
      !!d.container&&(!n.iced||d.ice)&&(!dk.water||d.water),`${sizes}<div class="tile-grid cb-grid3">${cups}</div>${extra}`)}
    ${S(2,'Xay & định lượng',d.dose?'tay cầm đã có bột':`☕ xay mịn ${cc(x).dose?.target||18} g`,d.shots.length>=n.shots||!!d.dose,
      `<div class="tile-grid cb-grid3">${beans}</div>${lockChip(x,beanShut)}${grinds}<div class="row wrap spread">${dose}${x.cmd('⚖️ Xay & nén','cb_dose',{task:t.id,beans:ui.beans||'',grind:ui.grind||'',grams},'',!canDose)}</div>`)}
    ${S(3,'Chiết shot',shotLine||'25–30 giây',d.shots.length>=n.shots&&!d.pulling&&!d.dose,
      `${shotMeter(x,d.pulling,myFlow)}<div class="row wrap">${pullBtn}<small class="muted">${groups.length}/${cc(x).groups||2} họng pha bận${d.dose?' · tay cầm đã có bột':''}</small></div>${others}${shots}`)}
    ${S(4,'Sữa',d.milk?`${milk(x,d.milk.kind).name}${d.milk.temp?` ${Math.round(d.milk.temp)} °C`:''}`:d.steaming?'đang đánh':'🥛 55–68 °C',!!n.milk&&!!d.milk&&!d.steaming,
      `<div class="tile-grid cb-grid3">${milks}</div>${lockChip(x,milkShut)}${foam}${thermo(x,d.steaming)}<div class="row wrap">${milkBtns}</div>${busyWand&&!d.steaming?'<p class="muted small">Vòi hơi đang đánh sữa cho ly khác.</p>':''}`)}
    ${S(5,'Latte art',d.art?(d.art==='blob'?'hình bị loang':art(x,d.art)?.name||''):'',!!n.art&&!!d.art,`<div class="tile-grid cb-grid3">${arts}</div>${lockChip(x,artShut)}`)}
    ${S(6,'Nắp',d.lid?'đã đậy':'',!!d.lid,x.cmd('🥤 Đậy nắp + dán tem','cb_lid',{task:t.id},'ghost',d.container!=='paper'||d.lid))}
    ${pastry?S(7,'Bánh gọi kèm',`${picked}/${wantPastry}`,picked>=wantPastry,casePicker(t,x,true)):''}</div>`;
}
function casePicker(t,x,compact){
  const lots=(data(x).case||[]).filter(l=>l.qty>0);
  if(!lots.length)return `<p class="notice amber">Tủ kính trống.</p>`;
  const canPick=!!(t&&t.known&&t.needs&&t.needs.kind!=='cake'&&!hidden(t)&&!t.bag.bagged);
  const stateTag={fresh:'hôm nay',day_old:'hôm qua',expired:'quá hạn'};
  const want=id=>!!(t?.needs&&((t.needs.items||t.needs.pastry||{})[id]));
  return `<div class="tile-grid cb-lots">${lots.map(l=>{const b=bake(x,l.item);
    return tile(x,{emoji:b.emoji,name:b.name,sub:`${stateTag[l.state]} · ${(cc(x).lot_q_label||{})[l.q]||l.q}${l.sale?' · −50%':''}${b.allergens?.length?' · '+b.allergens.map(a=>(cc(x).allergen_label||{})[a]||a).join('/'):''}`,
      count:l.qty,cmd:'cb_pick',payload:{task:t?.id,lot:l.id},disabled:!canPick||l.state==='expired',wanted:want(l.item)&&l.state==='fresh',cls:`lot-${l.state}`,label:`${b.name}, ${l.qty} cái, ${stateTag[l.state]}`});}).join('')}</div>
    ${compact?'':`<div class="cb-lot-actions">${lots.filter(l=>l.state!=='fresh').map(l=>{const b=bake(x,l.item);return `<div class="cb-lot-row"><span>${x.esc(b.emoji)} <b>${x.esc(b.name)}</b> <small class="muted">${l.qty} cái · ${stateTag[l.state]}</small></span><span class="row wrap">
      ${l.state==='day_old'&&!l.sale?x.cmd('🏷️ Rổ −50%','cb_markdown',{lot:l.id},'ghost small'):''}
      ${b.donate&&l.state!=='expired'?x.confirmCmd('💛 Tặng bếp cơm','cb_donate',{lot:l.id},`Tặng ${l.qty} ${lower(b.name)} (ra lò ngày ${l.day}) cho Bếp Cơm 0 Đồng, kèm nhãn ngày?`,'ghost small'):''}
      ${x.confirmCmd('🗑️ Bỏ','cb_discard',{lot:l.id},`Bỏ ${l.qty} ${lower(b.name)}? Giá trị được ghi hao hụt.`,'danger small')}</span></div>`;}).join('')}</div>`}`;
}
function casePanel(t,x){
  const n=t.needs,bag=t.bag;
  const tray=bag.items.length?`<div class="cb-tray">${bag.items.map((i,ix)=>`<button type="button" class="cb-chip" data-command="cb_return" data-payload="${pay(x,{task:t.id,index:ix})}" title="Trả về tủ">${x.esc(bake(x,i.item).emoji)} ${x.esc(bake(x,i.item).name)}${x.room.day-i.day>bake(x,i.item).fresh?' · hôm qua':''} ✕</button>`).join('')}</div>`:'<p class="muted small">Khay bánh còn trống</p>';
  const rules=`<details class="fold gd-rules cb-rules"><summary>📜 Quy tắc tủ kính</summary><ul class="small"><li>Bánh khô (croissant, bánh mì): bán trong ngày; hôm sau lên rổ −50% hoặc tặng kèm nhãn ngày; ngày thứ ba bỏ.</li><li>Cookie giữ được 3 ngày.</li><li>Bông lan trứng muối có sốt: chỉ bán trong ngày, không tặng.</li><li>Khách mua lẻ lấy bánh mới trước, hết bánh mới mới lấy rổ −50%.</li></ul></details>`;
  return `${shelf(x)}<h4 class="section-title">Tủ kính</h4>${casePicker(t,x,false)}${rules}
    ${n.kind!=='cake'&&!hidden(t)?`<h4 class="section-title">Khay của order</h4>${tray}<div class="row wrap">${x.cmd(`🛍️ Cho vào túi (${stock(x,'bag')})`,'cb_bag',{task:t.id},'',!bag.items.length||bag.bagged||(!bag.has_bag&&!stock(x,'bag')))}</div>`:''}`;
}
function ovenPanel(t,x){
  const d=data(x),level=lvl(x),proof=d.proof||[],oven=d.oven||[];
  const recipe=b=>Object.entries(b.recipe).map(([k,q])=>`${q} ${lower(inv(x,k).name)}`).join(' + ');
  const enough=b=>Object.entries(b.recipe).every(([k,q])=>stock(x,k)>=q);
  // Not enough for a tray: the tile says what is missing ("🧈 thiếu 1 bơ lạt") instead of the whole recipe.
  const missing=b=>{const m=Object.entries(b.recipe).find(([k,q])=>stock(x,k)<q);if(!m)return '';const i=inv(x,m[0]);return `${i.emoji&&i.emoji!=='•'?i.emoji+' ':''}thiếu ${m[1]-stock(x,m[0])} ${lower(i.name)}`;};
  const wanted=id=>(x.room.tasks||[]).some(v=>v.known&&v.needs&&((v.needs.items||v.needs.pastry||{})[id]))||(d.rules?.box?.status==='open'&&d.rules.box.item===id);
  const racksFull=oven.length>=2;
  const bakeTile=(b,o)=>{const locked=b.unlock>level&&!wanted(b.id),q=freshCount(x,b.id);
    const short=!locked&&missing(b),go=short?lackGo(x,lacks(x,b.recipe),t?.id):null;
    // Short of an ingredient: the tile says what ("🧈 thiếu 1 bơ lạt") and a tap opens the stock room for it.
    return tile(x,{emoji:b.emoji,name:o.name,sub:locked?`cấp ${b.unlock}`:short?`${short} · 📦 nhập`:recipe(b)+(o.extra?' · '+o.extra:''),count:locked?null:q,empty:!q,cmd:o.cmd,payload:o.payload,go,locked,wanted:wanted(b.id)&&!q,disabled:!go&&(o.disabled||!enough(b)),
      label:locked?`${b.name}, mở ở cấp ${b.unlock}`:short?`${o.name}: ${short}, chạm để nhập ở Kho`:`${o.name}: tủ kính còn ${q} cái mới`});};
  const st=d.starter||{};
  const shut=b=>b.unlock>level&&!wanted(b.id),bakeShut=(cc(x).bakes||[]).filter(b=>!b.cake&&shut(b));
  const shape=(cc(x).bakes||[]).filter(b=>b.proof&&!shut(b)).map(b=>bakeTile(b,{name:'Nhào '+lower(b.name),cmd:'cb_shape',payload:{item:b.id},disabled:proof.length>=2,
    extra:b.starter&&st.beats?`ủ ${st.beats} nhịp · men ${lower(st.label)}`:''})).join('');
  const direct=(cc(x).bakes||[]).filter(b=>!b.proof&&!b.cake&&!shut(b)).map(b=>bakeTile(b,{name:b.name,cmd:'cb_bake',payload:{item:b.id},disabled:racksFull})).join('');
  const cold=d.cold||[],fridgeFull=cold.length>=2;
  const trays=proof.length?proof.map(p=>{const b=bake(x,p.item);return `<div class="cb-slot ${p.left?'':'ready'}"><span class="tile-emoji" aria-hidden="true">${x.esc(b.emoji)}</span><div class="grow"><b>${p.qty} ${x.esc(lower(b.name))}</b><small class="muted">${p.left?`đang nở · còn ${p.left} nhịp`:p.over?'⚠️ ủ quá lâu, bánh sẽ xẹp':'✓ bột đã nở, sẵn sàng nướng'}${p.dense?' · men đói: sẽ đặc ruột':''}</small></div>
    <div class="cb-slot-btns">${x.cmd('🔥 Vào lò','cb_bake',{item:p.item,tray:p.id},p.left||racksFull?'small':'primary small',!!p.left||racksFull)}${x.cmd('❄️ Cất tủ mát','cb_chill',{tray:p.id},'ghost small',fridgeFull)}</div></div>`;}).join(''):'<p class="muted small">Tủ ủ trống (2 ngăn).</p>';
  const fridge=[0,1].map(i=>{const c=cold[i];if(!c)return `<div class="cb-slot empty"><span class="tile-emoji" aria-hidden="true">❄️</span><small class="muted">Ngăn ${i+1} trống</small></div>`;const b=bake(x,c.item);
    const when=c.bakeable?(c.last?'⚠️ đêm cuối — nướng hôm nay kẻo chua':`✓ ủ lạnh ${c.nights} đêm · vào lò ngay`):'đang ủ lạnh · nướng từ sáng mai';
    return `<div class="cb-slot cold${c.bakeable?' ready':''}${c.last?' last':''}"><span class="tile-emoji" aria-hidden="true">${x.esc(b.emoji)}</span><div class="grow"><b>${c.qty} ${x.esc(lower(b.name))}</b><small class="muted">${when}${c.dense?' · men đói':''}</small></div>
      ${c.bakeable?`<div class="cb-slot-btns">${x.cmd('🔥 Vào lò','cb_bake',{item:c.item,tray:c.id},racksFull?'small':'primary small',racksFull)}</div>`:''}</div>`;}).join('');
  const sp=bake(x,'sponge');
  const spShort=!t?.cake?.sponge&&!t?.cake?.baking?lacks(x,sp.recipe):[];
  const sponge=t&&t.known&&t.needs?.kind==='cake'?`<div class="row wrap">${x.cmd(`🎂 Nướng cốt bánh kem (${x.esc(spShort.length?lackText(x,spShort):recipe(sp))})`,'cb_bake',{item:'sponge',task:t.id},spShort.length?'ghost':'primary',racksFull||!!t.cake.sponge||t.cake.baking||!enough(sp))}${spShort.length?lackBtn(x,spShort,t.id):''}</div>`:'';
  const racks=[0,1].map(i=>{const r=oven[i];if(!r)return `<div class="cb-rack-row empty"><b>Tầng ${i+1}</b><small class="muted">trống</small></div>`;const b=bake(x,r.item);
    return `<div class="cb-rack-row"><b>Tầng ${i+1} · ${x.esc(b.emoji)} ${x.esc(b.name)}</b>${rackMeter(x,r)}${x.cmd('🧤 Lấy ra','cb_unload',{rack:r.id},'primary small')}</div>`;}).join('');
  return `${t?shelf(x):''}<h4 class="section-title">Lò nướng 2 tầng</h4><div class="cb-oven">${racks}</div>
    ${sponge}
    <h4 class="section-title">Tủ ủ bột</h4><div class="stack cb-proof">${trays}</div>
    <h4 class="section-title">❄️ Tủ mát ủ lạnh qua đêm</h4><div class="stack cb-proof">${fridge}</div>
    ${starterCard(x)}
    <h4 class="section-title">Nhào & tạo hình (cần ủ)</h4><div class="tile-grid">${shape}</div>
    <h4 class="section-title">Trộn & nướng ngay</h4><div class="tile-grid">${direct}</div>${lockChip(x,bakeShut)}`;
}
function cakePanel(t,x){
  const k=t.cake,ui=x.ui,cool=data(x).cooling?.[t.id];
  const spShort=lacks(x,bake(x,'sponge').recipe);
  const status=k.baking?'<p class="notice">🔥 Cốt bánh đang trong lò. Xem tab Lò.</p>':!k.sponge?`<div class="row wrap">${spShort.length?`${x.cmd(`🎂 Nướng cốt bánh <small>(${x.esc(lackText(x,spShort))})</small>`,'cb_bake',{},'ghost',true)}${lackBtn(x,spShort,t.id)}`:x.cmd('🎂 Nướng cốt bánh','cb_bake',{item:'sponge',task:t.id},'primary',(data(x).oven||[]).length>=2)}</div>`
    :`<p class="small">Cốt bánh: <b>${x.esc({pale:'sống ruột',golden:'vàng đều',dark:'hơi sậm',burnt:'cháy'}[k.sponge])}</b>${!k.cream&&cool?` · <span class="tag amber">còn ấm, chờ ${cool} nhịp</span>`:''}</p>`;
  const creams=(cc(x).creams||[]).map(c=>{const q=c.id==='whipped'?stock(x,'cream'):stock(x,'butter');
    return tile(x,{emoji:c.emoji,name:c.name,sub:c.id==='whipped'?'hộp kem':'khối bơ',count:q,empty:!q,action:'cream',data:{cream:c.id},selected:(k.cream||ui.cream)===c.id,wanted:!k.cream&&t.needs.cream===c.id,disabled:!!k.cream});}).join('');
  const swatches=`<div class="cb-swatches" role="group" aria-label="Màu kem">${(cc(x).colors||[]).map(c=>`<button type="button" class="cb-swatch ${(k.color||ui.color)===c.id?'on is-selected':''}" data-action="car:color" data-color="${x.esc(c.id)}" aria-pressed="${(k.color||ui.color)===c.id}" ${k.cream?'disabled':''}><i style="background:${x.esc(c.hex)}"></i>${x.esc(c.name)}</button>`).join('')}</div>`;
  const crShort=!k.cream&&ui.cream?lacks(x,cream(x,ui.cream).recipe):[];
  const frost=x.cmd(`🍦 Phủ kem${crShort.length?` <small>(${x.esc(lackText(x,crShort))})</small>`:''}`,'cb_frost',{task:t.id,cream:ui.cream||'',color:ui.color||''},'',!['golden','dark'].includes(k.sponge)||!!k.cream||!ui.cream||!ui.color||crShort.length>0)+(crShort.length?lackBtn(x,crShort,t.id):'');
  const write=k.text?`<p class="cb-written">✍️ “${x.esc(k.text)}”</p>${x.confirmCmd('🧽 Cạo chữ, viết lại','cb_scrape',{task:t.id},'Cạo lớp chữ và láng lại mặt kem?','ghost small',k.boxed)}`
    :`<div class="cb-write"><label class="field grow">Chữ trên mặt bánh<input id="cb-cake-text" class="input" maxlength="40" autocomplete="off" spellcheck="false" value="${x.esc(ui.cakeText||'')}" placeholder="Gõ đúng từng dấu như phiếu đặt"></label>${x.button('✍️ Viết lên bánh','car:write',{task:t.id},'primary')}</div>`;
  return `<h4 class="section-title">1 · Cốt bánh</h4>${status}
    <h4 class="section-title">2 · Kem & màu</h4><div class="tile-grid">${creams}</div>${swatches}<div class="row wrap">${frost}</div>
    <h4 class="section-title">3 · Viết chữ</h4>${k.cream?write:'<p class="muted small">Phủ kem xong mới viết chữ được.</p>'}
    <h4 class="section-title">4 · Đóng hộp</h4>${x.cmd(`📦 Đóng hộp (${stock(x,'cake_box')})`,'cb_box',{task:t.id},'',!k.cream||!k.text||k.boxed||!stock(x,'cake_box'))}`;
}
/* ---------- care from one day to the next ---------- */
/** Bé Men, the sourdough starter: strength, what it does to the bread, feed once a day. */
function starterCard(x){
  const s=data(x).starter;if(!s)return '';
  const feed=s.fed_today?'<span class="tag green">✓ Đã ăn hôm nay</span>':x.cmd(`🥄 Cho ăn (+${s.gain}%)`,'cb_feed',{},'primary small',!x.room.open||stock(x,'flour')<1);
  return `<section class="cb-starter ${x.esc(s.band)}" aria-label="Bé Men, hũ men tự nhiên"><div class="cb-starter-head"><span class="cb-jar" aria-hidden="true">🫙</span><p class="grow"><b>Bé Men · ${x.esc(s.emoji)} ${x.esc(s.label)}</b></p><b class="cb-starter-pct">${s.strength}%</b></div>
    <div class="cb-progress" role="meter" aria-label="Sức men" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${s.strength}"><i style="width:${s.strength}%"></i></div>
    <p class="small cb-starter-note">${x.esc(s.effect)}.${s.fed_today?'':` Chưa ăn: đêm nay −${s.night}%.`}</p><div class="row wrap">${feed}</div></section>`;
}
/** Today's care list (computed on the server), with last night's news on top. */
function careCard(x,open){
  const d=data(x),rows=d.care||[],left=rows.filter(r=>r.ok!==true).length,night=d.night||[];
  const news=night.length?`<div class="cb-night"><p class="eyebrow">🌙 Qua đêm</p><ul>${night.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul></div>`:'';
  const tm=d.tomorrow;
  const chip=tm?`<p class="cb-tomorrow small"><span aria-hidden="true">${x.esc(tm.emoji)}</span> Ngày mai: <b>${x.esc(tm.label)}</b>${tm.busy?' · đông khách mua lẻ':''}</p>`:'';
  const s=d.starter||{};
  const feed=s.fed_today===false?`<div class="row wrap">${x.cmd(`🫙 Cho Bé Men ăn (+${s.gain}%)`,'cb_feed',{},'primary small',!x.room.open||stock(x,'flour')<1)}</div>`:'';
  // A tap-to-open line (not a <details>, whose open state the host carries over between screens).
  const key=`care-${open?'idle':'job'}-${x.room.day}`,on=x.ui.cbSt?.[key]??open;
  return `<section class="cb-care cb-st${on?' open':''}"><button type="button" class="cb-st-sum" data-action="car:st" data-key="${key}" data-open="${on?1:0}" aria-expanded="${on}">🫙 Việc chăm tiệm · ${left?`${left} việc chờ`:'xong hết ✓'}</button>${on?`<div class="cb-st-body">${news}${rlist(rows,x,'Việc chăm tiệm hôm nay')}${feed}${chip}</div>`:''}</section>`;
}
/** The regulars' notes card: only what the shop has learned. */
function bookFold(x){
  const book=data(x).book||[];
  if(!book.length)return '';
  const rows=book.map(r=>{const who=x.npc(r.npc);return `<li class="cb-book-row">${x.portrait(who,36)}<div class="grow"><p><b>${x.esc(who.display_name||r.name)}</b> <small class="muted">${r.visits} lần ghé${r.next?` · ghé thêm ${r.next} lần để biết thêm`:''}</small></p>${r.notes.length?noteList(r.notes,x):'<p class="muted small">Chưa ghi được gì.</p>'}</div></li>`;}).join('');
  return `<section class="cb-bookcard">${fold(`📒 Sổ khách quen · ${book.length} khách`,`<ul class="cb-book">${rows}</ul>`)}</section>`;
}

/** Between guests: bake for the case (walk-in buyers, the office box). */
function prep(x){
  const d=data(x),busy=(d.oven||[]).length||(d.proof||[]).some(p=>!p.left)||(d.cold||[]).some(c=>c.bakeable);
  const open=x.ui.cbPrep??!!busy;
  return `<details class="card cb-prep"${open?' open':''}><summary data-action="car:prep"><span>🔥 Lò nướng & tủ kính${busy?' · <b>đang có mẻ bánh</b>':''}</span></summary>${ovenPanel(null,x)}<h4 class="section-title">Bánh trong tủ</h4>${casePicker(null,x,false)}</details>`;
}

/* ---------- next step & the one primary action (guide.js) ---------- */
/** Short action line for the task card and the queue (the hint says the exact tap). */
function nextStep(t,x){
  if(!t.known)return 'Nhận order của khách';
  const n=t.needs;
  if(n.kind==='cake'){const k=t.cake;if(k.baking)return 'Canh lò: lấy cốt bánh khi vàng đều';if(!k.sponge)return 'Nướng cốt bánh kem';if(['pale','burnt'].includes(k.sponge))return 'Cốt hỏng: bỏ và nướng lại';if(!k.cream)return data(x).cooling?.[t.id]?'Chờ cốt bánh nguội':'Phủ kem đúng màu';if(!k.text)return 'Viết chữ đúng từng dấu';if(!k.boxed)return 'Đóng hộp bánh';return 'Giao bánh kem!';}
  if(n.kind==='pastry'){const want=Object.values(n.items).reduce((a,b)=>a+b,0);if(t.bag.items.length<want)return `Gắp bánh (${t.bag.items.length}/${want})`;if(n.takeaway&&!t.bag.bagged)return 'Cho bánh vào túi';return 'Giao bánh cho khách!';}
  if(hidden(t))return (t.guesses||[]).length?'Đọc lời khách rồi đoán lại món':'Đoán món khách đang thèm';
  if(plated(t))return `Đủ ${t.cups.length} ly, giao cả khay!`;
  const sp=spec(t),d=t.drink,tag=isTray(t)?`Ly ${t.cur+1}: `:'';
  if(!d.container)return tag+'lấy đúng ly';
  if(d.pulling)return tag+'dừng chiết khi vào vùng xanh';
  if(d.steaming)return tag+'tắt vòi hơi ở 55–68 °C';
  if(sp.iced&&!d.ice)return tag+'múc đá vào ly';
  if(d.shots.length<sp.shots)return tag+(d.dose?'chiết shot':'xay & nén bột');
  if(drink(x,sp.drink).water&&!d.water)return tag+'thêm nước';
  if(sp.milk&&!d.milk)return tag+(sp.iced?'rót sữa lạnh':'đánh sữa');
  if(sp.art&&!d.art)return tag+'rót latte art';
  if(Object.keys(n.pastry||{}).length&&!t.bag.items.length)return 'Gắp bánh gọi kèm';
  if(d.container==='paper'&&!d.lid)return tag+'đậy nắp ly';
  const next=pendingOthers(t);
  if(next.length)return `Ly ${t.cur+1} xong! Đặt lên khay rồi làm ly ${next[0]+1}`;
  return isTray(t)?'Đủ ly rồi, giao cả khay!':'Giao đồ uống!';
}
function canServe(t){
  const n=t.needs;
  if(n.kind==='pastry')return t.bag.items.length>0;
  if(n.kind==='cake')return !!t.cake.boxed;
  if(hidden(t))return false;
  if(plated(t))return true;
  const d=t.drink;
  return !!(d.container&&d.shots.length&&!d.pulling&&!d.steaming&&!d.dose);
}
function serveFinal(t,x,steps){
  const ev=!!data(x).day?.open_event;
  return {label:t.needs.kind==='cake'?'🛎️ Giao bánh kem':'🛎️ Giao cho khách',go:finalGo(steps,'cb_serve',{task:t.id},{question:'Khách sẽ nhận và nếm thử.',confirm:true}),
    ready:canServe(t)&&!ev,why:ev?'chọn cách xử lý chuyện bất ngờ trước':'làm món trước đã'};
}
/** {steps, final, pulse}: the order's rows as steps, and what finishes it. */
function taskGuide(t,x){
  if(data(x).day?.open_event)return {steps:[{ok:null,label:'Chọn cách xử lý chuyện bất ngờ',go:{sel:'.fk-ev-choices .fk-choice'},pulse:''}]};
  if(!t.known)return {steps:[{ok:null,label:'Nhận order của khách',go:{cmd:'ask',payload:{task:t.id},label:'📝 Nhận order'}}],pulse:'.cb-ask'};
  // Starting a batch of pastry goes first: the dough rises while the drink is made.
  const rows=rowsOf(t,x),early=r=>r.ok!==true&&r.go?.early,steps=[...rows.filter(early),...rows.filter(r=>!early(r))],d=t.drink;
  if(t.needs.kind==='drink'&&hidden(t))return {steps,final:null};
  if(t.needs.kind==='drink'&&isTray(t)&&pendingOthers(t).length&&!plated(t)){
    const ready=!!(d.container&&d.shots.length&&!d.pulling&&!d.steaming&&!d.dose&&(d.container!=='paper'||d.lid));
    return {steps,final:{label:`✅ Xong ly ${t.cur+1}, đặt lên khay`,go:finalGo(steps,'cb_done',{task:t.id},{question:'Đặt ly này lên khay?'}),ready,why:'làm ly này trước đã'}};
  }
  return {steps,final:serveFinal(t,x,steps)};
}
function hintFor(x,g){
  const f=g.final&&g.final.ready!==false?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  return nextHint(x,g.steps,{final:f,pulse:g.pulse||''});
}
const ctaFor=(x,g)=>stepCta(x,g.steps,g.final||{label:'🛎️ Giao cho khách',go:null,ready:false,why:''});

export default {
  id:'cafe_bakery',
  css:true,
  next(t,x){return nextStep(t,x);},
  idle(x){
    const d=data(x);
    const pending=(d.care||[]).some(r=>r.ok!==true);
    return idlePanel(x,d.day,'cb_event',extras(x)+careCard(x,pending)+shelf(x)+prep(x)+bookFold(x),null,'cb');
  },
  job(t,x){
    const d=data(x),day=d.day,g=taskGuide(t,x),hint=hintFor(x,g);
    // The last result is shown in full once; after that it is two lines (tap it to read it all).
    const head=`${dayStrip(x,day,true)}${flash(x,day).replace('<p class="fk-flash','<p tabindex="0" class="fk-flash')}${eventCard(x,day,'cb_event')}${queue(x,t)}`;
    if(!t.known){
      const who=x.npc(t.npc),gu=t.guest||{};
      return `<div class="career-job cb food">${hint}${head}<article class="card ticket cb-ticket"><div class="cb-ticket-head">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3>
        <p class="cb-tags"><span class="tag">${x.esc(gu.emoji||'🙂')} ${x.esc(gu.label||'Khách')}</span></p></div></div>
        <p class="cb-say">“${x.esc(t.opening)}”</p>${regularNotes(t,x)}${patience(t.patience)}${x.cmd('📝 Nhận order','ask',{task:t.id},`${day?.open_event?'ghost':'primary'} full cb-ask`)}</article>${extras(x)}${careCard(x,false)}</div>`;
    }
    const n=t.needs,ui=x.ui;
    if(ui.tabFor!==t.id){ui.tabFor=t.id;ui.tab=n.kind==='drink'?'bar':n.kind==='pastry'?'case':'cake';ui.cakeText='';}
    const tabs=[['bar','☕','Quầy pha'],['oven','🔥','Lò & ủ bột'],['case','🥐','Tủ kính'],['cake','🎂','Bánh kem']];
    const racks=(d.oven||[]).length,ready=(d.proof||[]).filter(p=>!p.left).length+(d.cold||[]).filter(c=>c.bakeable).length+(d.starter&&!d.starter.fed_today?1:0),inCase=(d.case||[]).filter(l=>l.state==='fresh'&&!l.sale).reduce((a,l)=>a+l.qty,0);
    const badge=k=>k==='oven'&&(racks||ready)?`<em class="cb-badge">${racks+ready}</em>`:k==='case'?`<em class="cb-badge${inCase?' calm':' zero'}">${inCase}</em>`:'';
    const tabBar=`<div class="cb-tabs" role="tablist" aria-label="Khu làm việc">${tabs.map(([k,e,l])=>`<button type="button" role="tab" class="cb-tab ${ui.tab===k?'on':''}" data-action="car:tab" data-tab="${k}" aria-selected="${ui.tab===k}">${e} ${l}${badge(k)}</button>`).join('')}</div>`;
    const panel={bar:()=>n.kind==='drink'?barPanel(t,x):'<p class="notice">Order này không có đồ uống.</p>',oven:()=>ovenPanel(t,x),case:()=>casePanel(t,x),cake:()=>n.kind==='cake'?cakePanel(t,x):'<p class="notice">Order này không phải bánh kem.</p>'}[ui.tab]?.()||'';
    const preview=n.kind==='drink'?cupArt(t,x)+(Object.keys(n.pastry||{}).length?bagArt(t,x):''):n.kind==='pastry'?bagArt(t,x):cakeArt(t,x);
    const part=n.kind==='cake'?'cake':'drink';
    const dumpable=n.kind==='drink'?!plated(t)&&!!(t.drink.container||t.drink.shots.length||t.drink.milk):n.kind==='cake'?!!(t.cake.sponge||t.cake.cream):false;
    const dump=n.kind!=='pastry'?x.confirmCmd(n.kind==='cake'?'🗑️ Bỏ bánh':'🗑️ Đổ ly','cb_dump',{task:t.id,part},'Đổ bỏ và làm lại? Nguyên liệu đã dùng được ghi hao hụt.','danger small',!dumpable):'';
    // One bottom button (phones) and the same one in the side column (wide screens); only the
    // phone one is the guide's .gd-cta, so the first-time pulse lands on the visible one.
    const cta=ctaFor(x,g);
    const side=`<div class="cb-side"><div class="cb-look">${preview}<div class="cb-look-txt"><p class="cb-status" aria-live="polite">${x.esc(status(t,x))}</p>${trayCups(t)}</div></div>
      <div class="fk-wide-only">${cta.replace(/ gd-cta/g,'')}${dump}</div></div>`;
    const tools=`<p class="row wrap cb-tools">${dump?`<span class="cb-narrow-only">${dump}</span>`:''}${d.clean_day===x.room.day?'<span class="tag green">🧽 Đã vệ sinh máy hôm nay</span>':x.cmd('🧽 Vệ sinh máy pha','cb_clean',{},'ghost small')}</p>`;
    return `<div class="career-job cb food">${hint}${head}${extras(x)}${careCard(x,false)}${ticket(t,x)}${tabBar}<div class="workbench"><section class="wb-main" role="tabpanel">${panel}${tools}</section><aside class="wb-side">${side}</aside></div><div class="fk-bar cb-dock"><p class="cb-dock-status" aria-hidden="true">${x.esc(status(t,x))}</p>${cta}</div></div>`;
  },
  actions:{
    async tab(data,el,x){x.ui.tab=data.tab;x.render();},
    async size(data,el,x){x.ui.size=data.size;x.render();},
    async beans(data,el,x){x.ui.beans=data.beans;x.render();},
    async grind(data,el,x){x.ui.grind=data.grind;x.render();},
    async grams(data,el,x){const d=x.cc.dose||{min:12,max:24,target:18};x.ui.grams=Math.max(d.min,Math.min(d.max,(x.ui.grams??d.target)+Number(data.step||0)));x.render();},
    async milk(data,el,x){x.ui.milk=data.milk;x.render();},
    async foam(data,el,x){x.ui.foam=data.foam;x.render();},
    async cream(data,el,x){x.ui.cream=data.cream;x.render();},
    async color(data,el,x){x.ui.color=data.color;x.render();},
    async st(data,el,x){(x.ui.cbSt??={})[data.key]=data.open!=='1';x.render();},
    async prep(data,el,x){const d=el.closest('details');x.ui.cbPrep=d?!d.open:!x.ui.cbPrep;},
    async write(data,el,x){
      // Also sent from the header hint / bottom button: find the box anywhere in the sheet.
      const input=document.querySelector('#sheet[open] #cb-cake-text')||document.querySelector('#cb-cake-text');
      const text=(input?.value||'').trim();
      x.ui.cakeText=text;
      if(text.length<2){
        if(!input||x.ui.tab!=='cake'){x.ui.tab='cake';x.render();}
        setTimeout(()=>{const box=document.querySelector('#cb-cake-text');if(box){box.scrollIntoView({block:'center'});box.focus();}},60);
        x.toast('Gõ đúng chữ trên phiếu vào ô, rồi bấm “Viết lên bánh”.');return;
      }
      await x.send('cb_write',{task:data.task,text});
    },
  },
  tick(root){keepBarAboveFooter(root);},
  // The live bars (shot, steam wand, oven racks; v4/careers.js): they glide on the compositor, their words change
  // five times a second. The hint sits in the sheet header (outside root): every live bar in the sheet.
  // A bar inside a button (bottom button, hint) makes that button glow in the good window. A stop tap holds them
  // where they were when the finger came down (tapStop).
  meters(root,x){
    const scope=root.closest('dialog')||root,now=(el,on)=>el.closest('button')?.classList.toggle('cb-now',on);
    const e=x.cc.extract||{sour:20,bright:25,balanced:30,strong:35},st=x.cc.steam||{base:5,rate:4.2,cool:55,silky:68,hot:76};
    const draw=(el,p,perSec,text)=>{x.slide(el.querySelector('.cb-fill'),p,perSec,true);const l=el.querySelector('.cb-meter-label');if(l.textContent!==text)l.textContent=text;};
    for(const el of scope.querySelectorAll('[data-shot-start]')){
      const start=Number(el.dataset.shotStart);if(!start)continue;
      const s=Math.max(0,x.now()-start)*Number(el.dataset.flow||1);
      draw(el,s/SHOT_SCALE*100,Number(el.dataset.flow||1)/SHOT_SCALE*100,s.toFixed(1)+' giây · '+(s<e.sour?'chua':s<e.bright?'hơi chua':s<=e.balanced?'DỪNG NGAY!':s<=e.strong?'hơi đậm':'đắng khét'));
      el.classList.toggle('ready',s>=e.bright&&s<=e.balanced);el.classList.toggle('over',s>e.strong);now(el,s>=e.bright&&s<=e.balanced);
    }
    for(const el of scope.querySelectorAll('[data-steam-start]')){
      const start=Number(el.dataset.steamStart);if(!start)continue;
      const temp=st.base+st.rate*Math.max(0,x.now()-start);
      draw(el,temp/TEMP_SCALE*100,st.rate/TEMP_SCALE*100,Math.round(temp)+' °C · '+(temp<st.cool?'còn nguội':temp<=st.silky?'TẮT VÒI!':temp<=st.hot?'quá nóng':'khét sữa'));
      el.classList.toggle('ready',temp>=st.cool&&temp<=st.silky);el.classList.toggle('over',temp>st.hot);now(el,temp>=st.cool&&temp<=st.silky);
    }
    for(const el of scope.querySelectorAll('[data-oven-start]')){
      const start=Number(el.dataset.ovenStart);if(!start)continue;
      const [a,g,z]=(el.dataset.w||'10,20,30').split(',').map(Number),shift=Number(el.dataset.shift)||0,sec=Math.max(0,x.now()-start)+shift;
      draw(el,sec/(z+6)*100,100/(z+6),sec.toFixed(1)+' giây · '+(sec<a?'còn nhạt':sec<g?'VÀNG ĐỀU, LẤY RA!':sec<z?'sậm màu':'cháy rồi!'));
      el.classList.toggle('ready',sec>=a&&sec<g);el.classList.toggle('over',sec>=z);now(el,sec>=a&&sec<g);
    }
  },
  tapStop:op=>op==='cb_stop'||op==='cb_milk_stop'||op==='cb_unload',
  summary(data,x){
    const care=data&&data.care;
    const night=care?`<article class="card space-top cb-care-sum"><h4>🌙 Qua đêm ở tiệm</h4><ul class="small">${(care.lines||[]).map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>${care.tip?`<p class="fk-tomorrow"><span aria-hidden="true">❄️</span> <b>${x.esc(care.tip)}</b></p>`:''}</article>`:'';
    return gradeCard(data,x)+night;
  },
  dock:[['inventory','box','Kho','Nhập & đếm hàng']],
};
