/** Tiệm Bánh & Cà Phê Sớm Mai — espresso bar + bakery. The day strip, the
 * guest queue, the order (a mood to read, or a tray of cups done one by one),
 * station tabs whose tiles carry stock badges and padlocks, live timing bars
 * with a green zone, the display case that walk-in buyers shop from, and one
 * big "Giao". Only renders server state and sends commands; the server checks
 * every rule and keeps a mood order's drink hidden until it is found. */
import {dayStrip,flash,eventCard,queue,actionBar,keepBarAboveFooter,idlePanel,gradeCard,patience} from './food_kit.js';

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
  const attrs=o.cmd?`data-command="${o.cmd}" data-payload="${pay(x,o.payload||{})}"`
    :o.action?`data-action="car:${o.action}"${Object.entries(o.data||{}).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}`:'';
  const cls=['tile',o.cls||'',o.selected?'is-selected':'',o.locked?'is-locked':'',o.empty?'is-empty':'',o.wanted?'wanted':''].filter(Boolean).join(' ');
  const badge=o.count!=null&&!o.locked?`<span class="count-badge${o.empty?' is-empty':''}" data-count="${x.esc(String(o.count))}">${x.esc(String(o.count))}</span>`:'';
  return `<button type="button" class="${cls}" ${attrs}${o.disabled||o.locked?' disabled':''} aria-pressed="${o.selected?'true':'false'}"${o.label?` aria-label="${x.esc(o.label)}"`:''}>${badge}<span class="tile-emoji" aria-hidden="true">${x.esc(o.emoji||'')}</span><b>${x.esc(o.name)}</b>${o.sub?`<small>${x.esc(o.sub)}</small>`:''}</button>`;
}
const seg=(x,action,key,value,label,current)=>`<button type="button" class="cb-seg ${current===value?'on is-selected':''}" data-action="car:${action}" data-${key}="${x.esc(value)}" aria-pressed="${current===value}">${x.esc(label)}</button>`;
const checklist=(x,rows)=>`<ul class="checklist">${rows.map(([ok,label,note])=>`<li class="${ok===true?'ok':ok===false?'bad':''}"><span aria-hidden="true">${ok===true?'✓':ok===false?'✗':'○'}</span>${x.esc(label)}${note?`<small>${x.esc(note)}</small>`:''}</li>`).join('')}</ul>`;
const bar=(cls,attrs,zones,fill,label)=>`<div class="cb-meter ${cls}" ${attrs}><div class="cb-track">${zones.map(([k,a,b])=>`<i class="cb-zone ${k}" style="left:${a}%;width:${Math.max(0,b-a)}%"></i>`).join('')}<b class="cb-fill" style="width:${Math.min(100,Math.max(0,fill))}%"></b></div><small class="cb-meter-label">${label}</small></div>`;

/* ---------- real-time meters (the server decides the result from its own clock) ---------- */
function shotMeter(x,start,flow){
  const e=cc(x).extract||{sour:20,bright:25,balanced:30,strong:35},s=SHOT_SCALE,p=v=>v/s*100;
  const eff=start?Math.max(0,x.now()-start)*flow:0;
  return bar('shot',`data-shot-start="${start||''}" data-flow="${flow||1}"`,[['sour',0,p(e.sour)],['bright',p(e.sour),p(e.bright)],['balanced',p(e.bright),p(e.balanced)],['strong',p(e.balanced),p(e.strong)],['bitter',p(e.strong),100]],p(eff),start?eff.toFixed(1)+' giây chiết':'Họng pha đang nghỉ · vùng xanh là chuẩn');
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
  return `<p class="cb-traycups" aria-label="Khay ly">${t.cups.map((c,i)=>`<span class="${c?'on':''}${i===t.cur&&!c?' cur':''}" title="Ly ${i+1}">${c?'☕':i===t.cur?'🫗':'◌'}<small>${i+1}</small></span>`).join('')}</p>`;
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

/* ---------- checklists ---------- */
function drinkRows(t,x){
  if(hidden(t))return [[null,'Đoán đúng món khách đang thèm','']];
  if(plated(t))return [[true,`Đủ ${t.cups.length} ly trên khay, giao một lượt`,'']];
  const n=spec(t),d=t.drink,dk=drink(x,n.drink),rows=[];
  const want=n.takeaway?'paper':n.iced?'glass':'mug';
  const cname={paper:'Ly giấy mang về',glass:'Ly thủy tinh',mug:'Tách sứ'}[want];
  rows.push([d.container?d.container===want&&d.size===n.size:null,`${cname} · ly ${n.size==='L'?'lớn':'nhỏ'}`,'']);
  if(n.iced)rows.push([d.ice?true:null,'Đá đầy ly','']);
  const good=d.shots.filter(s=>['balanced','bright','strong'].includes(s.x)&&s.beans===n.beans).length;
  rows.push([d.shots.length?d.shots.length===n.shots&&good===n.shots:null,`${n.shots} shot ${bean(x,n.beans).name} · 25–30 giây`,d.shots.map(s=>`${s.sec}s ${(cc(x).shot_label||{})[s.x]||s.x}`).join(' · ')]);
  if(dk.water)rows.push([d.water?true:null,n.iced?'Nước lạnh':'Nước nóng','']);
  if(n.milk){
    const m=milk(x,n.milk),mode=n.iced?'rót lạnh':`đánh 55–68 °C, bọt ${n.foam==='thick'?'dày':'mỏng'}`;
    const ok=d.milk?d.milk.kind===n.milk&&(n.iced?d.milk.mode==='cold':d.milk.mode==='steam'&&d.milk.tex==='silky'&&d.milk.foam===n.foam):null;
    rows.push([ok,`${m.name} · ${mode}`,d.milk?.temp?Math.round(d.milk.temp)+' °C':'']);
  }else if(d.milk)rows.push([false,'Món này không có sữa','']);
  if(n.art)rows.push([d.art?d.art===n.art:null,`Vẽ ${lower(art(x,n.art)?.name||n.art)}`,d.art==='blob'?'hình bị loang':'']);
  for(const [k,q] of Object.entries(n.pastry||{})){const have=t.bag.items.filter(i=>i.item===k).length;rows.push([have?have===q:null,`${q} ${lower(bake(x,k).name)} (bánh hôm nay)`,have?`${have}/${q}`:'']);}
  if(Object.keys(n.pastry||{}).length&&n.takeaway)rows.push([t.bag.bagged?true:null,'Cho bánh vào túi','']);
  if(want==='paper')rows.push([d.lid?true:null,'Đậy nắp + tem tên','']);
  if(n.lactose)rows.push([d.milk?!milk(x,d.milk.kind).lactose:null,'⚠️ Không sữa bò (không dung nạp lactose)','']);
  if(n.decaf)rows.push([d.shots.length?d.shots.every(s=>s.beans==='decaf'):null,'⚠️ Chỉ hạt decaf','']);
  return rows;
}
function pastryRows(t,x){
  const n=t.needs,rows=[],items=t.bag.items,day=x.room.day;
  for(const [k,q] of Object.entries(n.items)){const have=items.filter(i=>i.item===k).length;rows.push([have?have===q:null,`${q} ${lower(bake(x,k).name)}`,have?`${have}/${q}`:'']);}
  for(const i of items)if(!n.items[i.item])rows.push([false,`${bake(x,i.item).name} (khách không gọi)`,'']);
  const old=items.filter(i=>day-i.day>bake(x,i.item).fresh).length;
  rows.push([items.length?(n.day_old_ok||!old):null,n.day_old_ok?'Bánh hôm qua −50% (khách đồng ý)':'Bánh ra lò hôm nay',old?`${old} bánh hôm qua`:'']);
  if(n.allergy)rows.push([items.length?!items.some(i=>bake(x,i.item).allergens.includes(n.allergy)):null,`⚠️ Không có ${(cc(x).allergen_label||{})[n.allergy]||n.allergy}`,'']);
  if(n.takeaway)rows.push([t.bag.bagged?true:null,'Túi giấy + tem ngày','']);
  return rows;
}
function cakeRows(t,x){
  const n=t.needs,k=t.cake,cool=data(x).cooling?.[t.id];
  return [
    [k.sponge?['golden','dark'].includes(k.sponge):null,'Cốt bông lan vàng đều',k.sponge?{pale:'sống ruột',golden:'vàng đều',dark:'hơi sậm',burnt:'cháy'}[k.sponge]:''],
    [k.cream?!k.melted:k.sponge?(cool?null:true):null,'Để nguội trước khi phủ kem',k.sponge&&!k.cream&&cool?`chờ ${cool} nhịp`:''],
    [k.cream?k.cream===n.cream&&k.color===n.color:null,`${cream(x,n.cream).name} · ${lower(color(x,n.color).name)}`,''],
    [k.text?letters(k.text)===letters(n.text):null,`Chữ: “${n.text}”`,k.text&&letters(k.text)!==letters(n.text)?`đang ghi “${k.text}”`:''],
    [k.boxed?true:null,'Hộp + nến + dao','']];
}
const rowsOf=(t,x)=>t.needs.kind==='drink'?drinkRows(t,x):t.needs.kind==='pastry'?pastryRows(t,x):cakeRows(t,x);

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
    <div class="cb-shelf-row">${wants.map(id=>{const b=bake(x,id),q=freshCount(x,id);return `<span class="cb-shelf-item${q?'':' is-empty'}" title="${x.esc(b.name)}: ${q} cái ra lò hôm nay"><span class="count-badge${q?'':' is-empty'}" data-count="${q}">${q}</span><span class="cb-shelf-emoji" aria-hidden="true">${x.esc(b.emoji)}</span><small>${x.esc(b.name)}</small></span>`;}).join('')}</div></section>`;
}
const extras=x=>banners(x)+boxCard(x);

/* ---------- the order ---------- */
function drinkLine(n,x){
  const d=drink(x,n.drink);
  return `${x.esc(d.emoji)} <b>${x.esc(d.name)}</b> ${n.iced?'đá':'nóng'} · ly ${n.size==='L'?'lớn':'nhỏ'} · ${n.takeaway?'🥤 mang về':'☕ tại quán'} · ${n.shots} shot ${x.esc(bean(x,n.beans).name)}${n.milk?' · '+x.esc(lower(milk(x,n.milk).name)):''}${n.art?' · vẽ '+x.esc(lower(art(x,n.art)?.name||'')):''}${n.lactose?' · <b class="cb-warn">⚠️ không lactose</b>':''}${n.decaf?' · <b class="cb-warn">⚠️ không caffeine</b>':''}`;
}
/** Mood order: the guest's feeling and three drinks to pick from. */
function moodCard(t,x){
  const m=t.needs.mood,used=t.guesses||[];
  return `<div class="cb-mood"><p class="cb-bubble">💭 “${x.esc(m.text)}”</p>${m.clue?`<p class="cb-clue">🔎 Khách lắc đầu, nói thêm: “${x.esc(m.clue)}”</p>`:''}
    <p class="cb-ask"><b>Khách đang thèm món nào?</b><small>Hiểu ý ngay lần đầu, khách vui sẽ boa thêm.</small></p>
    <div class="tile-grid cb-guess" role="group" aria-label="Chọn món hợp ý khách">${m.options.map(id=>{const d=drink(x,id),no=used.includes(id);
      return tile(x,{emoji:d.emoji,name:d.name,sub:no?'khách lắc đầu':'',cmd:'cb_guess',payload:{task:t.id,drink:id},disabled:no,cls:no?'struck':'',label:no?`${d.name}: khách đã lắc đầu`:`Mời khách ${d.name}`});}).join('')}</div></div>`;
}
/** A tray: one row per cup. Tap a waiting cup to switch, a finished one to take it back. */
function trayTabs(t,x){
  const busy=started(t.drink)&&!plated(t);
  return `<div class="cb-party" role="tablist" aria-label="Các ly trong khay">${t.needs.party.map((p,i)=>{
    const sp={...t.needs,...p},done=!!t.cups[i],on=i===t.cur&&!done,off=on||(busy&&!on);
    return `<button type="button" role="tab" class="cb-cupline${on?' on is-selected':''}${done?' done':''}" data-command="cb_tab" data-payload="${pay(x,{task:t.id,index:i})}" aria-selected="${on}"${off?' disabled':''}>
      <span class="cb-cupno" aria-hidden="true">${done?'✓':i+1}</span><span class="cb-cuptext"><small>Ly ${i+1} · ${done?'đã trên khay, bấm để lấy xuống sửa':on?'đang làm':busy?'chờ ly đang làm xong':'bấm để làm ly này'}</small>${drinkLine(sp,x)}</span></button>`;
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
      if(isTray(t)){tags.push(`<span class="tag">☕ Khay ${n.party.length} ly</span>`);body=trayTabs(t,x);}
      else body=`<p class="order-line">${drinkLine(n,x)}${Object.entries(n.pastry||{}).map(([k,q])=>` · +${q} ${x.esc(bake(x,k).emoji)} ${x.esc(lower(bake(x,k).name))}`).join('')}</p>`;
      if(n.style==='mood'&&n.mood?.text)body=`<p class="cb-bubble small">💭 “${x.esc(n.mood.text)}”</p>`+body;
    }
  }else if(n.kind==='pastry'){
    body=`<p class="order-line">${Object.entries(n.items).map(([k,q])=>`${x.esc(bake(x,k).emoji)} ${q} ${x.esc(lower(bake(x,k).name))}`).join(' · ')}${n.takeaway?' · 🛍️ mang về':''}</p>`;
    if(n.day_old_ok)tags.push('<span class="tag amber">Bánh hôm qua −50%</span>');
    if(n.allergy)tags.push(`<span class="tag danger">⚠️ Dị ứng ${x.esc((cc(x).allergen_label||{})[n.allergy]||n.allergy)}</span>`);
  }else{
    body=`<p class="order-line">🎂 ${x.esc(cream(x,n.cream).name)} · <i class="cb-dot" style="background:${x.esc(color(x,n.color).hex)}"></i> ${x.esc(lower(color(x,n.color).name))} · chữ: <b class="cb-order-text">“${x.esc(n.text)}”</b></p>`;
  }
  const price=t.quoted_price!=null?x.money(t.quoted_price):'…';
  return `<article class="card ticket cb-ticket"><div class="cb-ticket-head">${x.portrait(who,44)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3><b class="price">${price}</b></div>
    <p class="cb-tags">${tags.join(' ')}</p></div></div>
    ${body}${n.note?`<p class="muted small">“${x.esc(n.note)}”</p>`:''}${patience(t.patience)}</article>`;
}

/* ---------- station panels ---------- */
function barPanel(t,x){
  if(hidden(t))return `<p class="notice amber">🤔 Chưa rõ khách muốn món gì. Chọn món hợp với lời khách ở phiếu order trước đã.</p>`;
  if(plated(t))return `<p class="notice">☕ Đủ ${t.cups.length} ly trên khay. Giao cả khay, hoặc bấm một ly ở phiếu order để lấy xuống sửa.</p>`;
  const n=spec(t),d=t.drink,ui=x.ui,level=lvl(x),dd=data(x),groups=dd.groups||[],wand=dd.wand||[],r=dd.rules||{};
  const size=d.size||ui.size||'S',want=n.takeaway?'paper':n.iced?'glass':'mug';
  const cups=(cc(x).containers||[]).map(c=>{const q=c.id==='paper'?stock(x,'cup'):null;
    return tile(x,{emoji:c.emoji,name:c.name,sub:c.note,count:q,empty:q===0,cmd:'cb_cup',payload:{task:t.id,kind:c.id,size},selected:d.container===c.id,wanted:!d.container&&c.id===want,disabled:!!d.container||q===0,
      label:`${c.name}${q!=null?`, còn ${q}`:''}`});}).join('');
  const sizes=`<div class="cb-segs" role="group" aria-label="Cỡ ly">${seg(x,'size','size','S','Ly nhỏ',size)}${seg(x,'size','size','L','Ly lớn',size)}</div>`;
  const extra=`<div class="row wrap">${x.cmd('🧊 Múc đá','cb_ice',{task:t.id},'ghost small',!d.container||d.ice||d.container==='mug')}${x.cmd('💧 Thêm nước','cb_water',{task:t.id},'ghost small',!d.container||d.water)}</div>`;
  const beans=(cc(x).beans||[]).map(b=>{const locked=b.unlock>level&&n.beans!==b.id,q=stock(x,'beans_'+b.id);
    return tile(x,{emoji:b.emoji,name:b.name,sub:locked?`cấp ${b.unlock}`:b.note,count:q,empty:!q,action:'beans',data:{beans:b.id},selected:ui.beans===b.id,locked,wanted:!d.shots.length&&n.beans===b.id,
      label:locked?`Hạt ${b.name}, mở ở cấp ${b.unlock}`:`Hạt ${b.name}, còn ${q} liều`});}).join('');
  const grinds=`<div class="cb-segs" role="group" aria-label="Độ xay">${Object.entries(cc(x).grind_label||{}).map(([k,l])=>seg(x,'grind','grind',k,l,ui.grind)).join('')}</div>`;
  const grams=ui.grams??(cc(x).dose?.target||18);
  const dose=`<div class="cb-stepper" role="group" aria-label="Định lượng bột"><button type="button" class="btn ghost small" data-action="car:grams" data-step="-1" aria-label="Bớt 1 gam">−</button><b>${grams} g</b><button type="button" class="btn ghost small" data-action="car:grams" data-step="1" aria-label="Thêm 1 gam">+</button></div>`;
  const canDose=d.container&&!d.dose&&!d.pulling&&ui.beans&&ui.grind&&d.shots.length<3&&stock(x,'beans_'+ui.beans)>0;
  const full=groups.length>=(cc(x).groups||2);
  const pullBtn=d.pulling?x.cmd('⏹️ Dừng chiết','cb_stop',{task:t.id},'primary'):x.cmd('▶️ Chiết shot','cb_pull',{task:t.id},d.dose?'primary':'',!d.dose||full);
  const myFlow=groups.find(g=>g.task===t.id)?.flow||1;
  const others=groups.filter(g=>g.task!==t.id).map(g=>`<div class="cb-other"><small class="muted">Họng pha kia · ly khác</small>${shotMeter(x,g.start,g.flow)}${x.cmd('⏹️ Dừng ly đó','cb_stop',{task:g.task},'ghost small')}</div>`).join('');
  const shots=d.shots.length?`<div class="row wrap cb-shots">${d.shots.map((s,i)=>`<span class="tag ${s.x==='balanced'?'green':['sour','bitter'].includes(s.x)?'danger':'amber'}">Shot ${i+1}: ${s.sec}s · ${x.esc((cc(x).shot_label||{})[s.x]||s.x)}</span>`).join('')}</div>`:'';
  const milks=(cc(x).milks||[]).map(m=>{const locked=m.unlock>level&&n.milk!==m.id,q=stock(x,m.id),sour=r.sour_milk&&m.id==='milk';
    return tile(x,{emoji:m.emoji,name:m.name,sub:locked?`cấp ${m.unlock}`:sour?'⚠️ có mùi':m.lactose?'có lactose':'không lactose',count:q,empty:!q,action:'milk',data:{milk:m.id},selected:ui.milk===m.id,locked,wanted:!d.milk&&n.milk===m.id,
      label:locked?`${m.name}, mở ở cấp ${m.unlock}`:`${m.name}, còn ${q} ca`});}).join('');
  const foam=`<div class="cb-segs" role="group" aria-label="Độ bọt">${seg(x,'foam','foam','thin','Bọt mỏng (latte)',ui.foam)}${seg(x,'foam','foam','thick','Bọt dày (cappu)',ui.foam)}</div>`;
  const mk=ui.milk?milk(x,ui.milk):null,busyWand=wand.some(w=>w.task!==t.id);
  const milkBtns=d.steaming?x.cmd('⏹️ Tắt vòi hơi','cb_milk_stop',{task:t.id},'primary')
    :`${x.cmd('♨️ Đánh nóng','cb_milk',{task:t.id,milk:ui.milk||'',mode:'steam',foam:ui.foam||''},'',!d.container||!!d.milk||!mk||!mk.steam||!ui.foam||busyWand||!stock(x,ui.milk))}${x.cmd('🧊 Rót lạnh','cb_milk',{task:t.id,milk:ui.milk||'',mode:'cold'},'ghost',!d.container||!!d.milk||!mk||!stock(x,ui.milk))}`;
  const arts=(cc(x).arts||[]).map(a=>{const locked=a.unlock>level&&n.art!==a.id;
    return tile(x,{emoji:a.emoji,name:a.name,sub:locked?`cấp ${a.unlock}`:'rót tạo hình',cmd:'cb_art',payload:{task:t.id,pattern:a.id},locked,selected:d.art===a.id,wanted:!d.art&&n.art===a.id,
      disabled:!d.milk||d.milk.mode!=='steam'||!!d.art||!d.shots.length,label:locked?`Hình ${a.name}, mở ở cấp ${a.unlock}`:`Rót hình ${a.name}`});}).join('');
  const pastryPick=Object.keys(n.pastry||{}).length?`<h4 class="section-title">7 · Bánh gọi kèm</h4>${casePicker(t,x,true)}`:'';
  return `<p class="cb-recipe small">📋 Công thức quầy: <b>xay mịn · 18 g · chiết 25–30 giây</b> · sữa nóng <b>55–68 °C</b></p>
    ${r.grinder?'<p class="notice amber small">⚙️ Máy xay đang xay không đều hôm nay.</p>':''}
    <h4 class="section-title">1 · Ly</h4>${sizes}<div class="tile-grid cb-grid3">${cups}</div>${extra}
    <h4 class="section-title">2 · Xay & định lượng</h4><div class="tile-grid cb-grid3">${beans}</div>${grinds}
    <div class="row wrap spread">${dose}${x.cmd('⚖️ Xay & nén','cb_dose',{task:t.id,beans:ui.beans||'',grind:ui.grind||'',grams},'',!canDose)}</div>
    <h4 class="section-title">3 · Chiết shot</h4>${shotMeter(x,d.pulling,myFlow)}<div class="row wrap">${pullBtn}<small class="muted">${groups.length}/${cc(x).groups||2} họng pha bận${d.dose?' · tay cầm đã có bột':''}</small></div>${others}${shots}
    <h4 class="section-title">4 · Sữa</h4><div class="tile-grid cb-grid3">${milks}</div>${foam}${thermo(x,d.steaming)}<div class="row wrap">${milkBtns}</div>${busyWand&&!d.steaming?'<p class="muted small">Vòi hơi đang đánh sữa cho ly khác.</p>':''}
    <h4 class="section-title">5 · Latte art</h4><div class="tile-grid cb-grid3">${arts}</div>
    <h4 class="section-title">6 · Nắp</h4>${x.cmd('🥤 Đậy nắp + dán tem','cb_lid',{task:t.id},'ghost',d.container!=='paper'||d.lid)}
    ${pastryPick}`;
}
function casePicker(t,x,compact){
  const lots=(data(x).case||[]).filter(l=>l.qty>0);
  if(!lots.length)return `<p class="notice amber">Tủ kính trống. Qua tab 🔥 Lò để nướng mẻ mới.</p>`;
  const canPick=!!(t&&t.known&&t.needs&&t.needs.kind!=='cake'&&!hidden(t)&&!t.bag.bagged);
  const stateTag={fresh:'hôm nay',day_old:'hôm qua',expired:'quá hạn'};
  const want=id=>!!(t?.needs&&((t.needs.items||t.needs.pastry||{})[id]));
  return `<div class="tile-grid cb-case">${lots.map(l=>{const b=bake(x,l.item);
    return tile(x,{emoji:b.emoji,name:b.name,sub:`${stateTag[l.state]} · ${(cc(x).lot_q_label||{})[l.q]||l.q}${l.sale?' · −50%':''}${b.allergens?.length?' · '+b.allergens.map(a=>(cc(x).allergen_label||{})[a]||a).join('/'):''}`,
      count:l.qty,cmd:'cb_pick',payload:{task:t?.id,lot:l.id},disabled:!canPick||l.state==='expired',wanted:want(l.item)&&l.state==='fresh',cls:`lot-${l.state}`,label:`${b.name}, ${l.qty} cái, ${stateTag[l.state]}`});}).join('')}</div>
    ${compact?'':`<div class="cb-lot-actions">${lots.filter(l=>l.state!=='fresh').map(l=>{const b=bake(x,l.item);return `<div class="cb-lot-row"><span>${x.esc(b.emoji)} <b>${x.esc(b.name)}</b> <small class="muted">${l.qty} cái · ${stateTag[l.state]}</small></span><span class="row wrap">
      ${l.state==='day_old'&&!l.sale?x.cmd('🏷️ Rổ −50%','cb_markdown',{lot:l.id},'ghost small'):''}
      ${b.donate&&l.state!=='expired'?x.confirmCmd('💛 Tặng bếp cơm','cb_donate',{lot:l.id},`Tặng ${l.qty} ${lower(b.name)} (ra lò ngày ${l.day}) cho Bếp Cơm 0 Đồng, kèm nhãn ngày?`,'ghost small'):''}
      ${x.confirmCmd('🗑️ Bỏ','cb_discard',{lot:l.id},`Bỏ ${l.qty} ${lower(b.name)}? Giá trị được ghi hao hụt.`,'danger small')}</span></div>`;}).join('')}</div>`}`;
}
function casePanel(t,x){
  const n=t.needs,bag=t.bag;
  const tray=bag.items.length?`<div class="cb-tray">${bag.items.map((i,ix)=>`<button type="button" class="cb-chip" data-command="cb_return" data-payload="${pay(x,{task:t.id,index:ix})}" title="Trả về tủ">${x.esc(bake(x,i.item).emoji)} ${x.esc(bake(x,i.item).name)}${x.room.day-i.day>bake(x,i.item).fresh?' · hôm qua':''} ✕</button>`).join('')}</div>`:'<p class="muted small">Khay đang trống. Gắp bánh bằng kẹp từ tủ kính.</p>';
  const rules=`<details class="cb-rules"><summary>Quy định tủ kính</summary><ul class="small"><li>Bánh khô (croissant, bánh mì): bán trong ngày; hôm sau lên rổ −50% hoặc tặng kèm nhãn ngày; ngày thứ ba bỏ.</li><li>Cookie giữ được 3 ngày.</li><li>Bông lan trứng muối có sốt: chỉ bán trong ngày, không tặng.</li><li>Khách mua lẻ lấy bánh mới trước, hết bánh mới mới lấy rổ −50%.</li></ul></details>`;
  return `${shelf(x)}<h4 class="section-title">Tủ kính</h4>${casePicker(t,x,false)}${rules}
    ${n.kind!=='cake'&&!hidden(t)?`<h4 class="section-title">Khay của order</h4>${tray}<div class="row wrap">${x.cmd(`🛍️ Cho vào túi (${stock(x,'bag')})`,'cb_bag',{task:t.id},'',!bag.items.length||bag.bagged||(!bag.has_bag&&!stock(x,'bag')))}</div>`:''}`;
}
function ovenPanel(t,x){
  const d=data(x),level=lvl(x),proof=d.proof||[],oven=d.oven||[];
  const recipe=b=>Object.entries(b.recipe).map(([k,q])=>`${q} ${lower(inv(x,k).name)}`).join(' + ');
  const enough=b=>Object.entries(b.recipe).every(([k,q])=>stock(x,k)>=q);
  const wanted=id=>(x.room.tasks||[]).some(v=>v.known&&v.needs&&((v.needs.items||v.needs.pastry||{})[id]))||(d.rules?.box?.status==='open'&&d.rules.box.item===id);
  const racksFull=oven.length>=2;
  const bakeTile=(b,o)=>{const locked=b.unlock>level&&!wanted(b.id),q=freshCount(x,b.id);
    return tile(x,{emoji:b.emoji,name:o.name,sub:locked?`cấp ${b.unlock}`:recipe(b),count:locked?null:q,empty:!q,cmd:o.cmd,payload:o.payload,locked,wanted:wanted(b.id)&&!q,disabled:o.disabled||!enough(b),
      label:locked?`${b.name}, mở ở cấp ${b.unlock}`:`${o.name}: tủ kính còn ${q} cái mới`});};
  const shape=(cc(x).bakes||[]).filter(b=>b.proof).map(b=>bakeTile(b,{name:'Nhào '+lower(b.name),cmd:'cb_shape',payload:{item:b.id},disabled:proof.length>=2})).join('');
  const direct=(cc(x).bakes||[]).filter(b=>!b.proof&&!b.cake).map(b=>bakeTile(b,{name:b.name,cmd:'cb_bake',payload:{item:b.id},disabled:racksFull})).join('');
  const trays=proof.length?proof.map(p=>{const b=bake(x,p.item);return `<div class="cb-slot ${p.left?'':'ready'}"><span class="tile-emoji" aria-hidden="true">${x.esc(b.emoji)}</span><div class="grow"><b>${p.qty} ${x.esc(lower(b.name))}</b><small class="muted">${p.left?`đang nở · còn ${p.left} nhịp`:p.over?'⚠️ ủ quá lâu, bánh sẽ xẹp':'✓ bột đã nở, sẵn sàng nướng'}</small></div>${x.cmd('🔥 Vào lò','cb_bake',{item:p.item,tray:p.id},p.left||racksFull?'small':'primary small',!!p.left||racksFull)}</div>`;}).join(''):'<p class="muted small">Tủ ủ trống (2 ngăn).</p>';
  const sp=bake(x,'sponge');
  const sponge=t&&t.known&&t.needs?.kind==='cake'?`<div class="row wrap">${x.cmd(`🎂 Nướng cốt bánh kem (${x.esc(recipe(sp))})`,'cb_bake',{item:'sponge',task:t.id},'primary',racksFull||!!t.cake.sponge||t.cake.baking||!enough(sp))}</div>`:'';
  const racks=[0,1].map(i=>{const r=oven[i];if(!r)return `<div class="cb-rack-row empty"><b>Tầng ${i+1}</b><small class="muted">trống</small></div>`;const b=bake(x,r.item);
    return `<div class="cb-rack-row"><b>Tầng ${i+1} · ${x.esc(b.emoji)} ${x.esc(b.name)}</b>${rackMeter(x,r)}${x.cmd('🧤 Lấy ra','cb_unload',{rack:r.id},'primary small')}</div>`;}).join('');
  return `${t?shelf(x):''}<h4 class="section-title">Lò nướng 2 tầng</h4>${d.oven_shift?`<p class="notice amber small">🔥 Lò đang nóng hơn thường: bánh vàng sớm hơn ${d.oven_shift} giây.</p>`:''}<div class="cb-oven">${racks}</div>
    <p class="muted small">Lấy bánh ra khi thanh vào vùng xanh (vàng đều). Bánh cháy phải bỏ; bánh nhạt màu bán được nhưng khách chê. Số trên góc là bánh mới đang có trong tủ kính.</p>
    ${sponge}
    <h4 class="section-title">Tủ ủ bột</h4><div class="stack cb-proof">${trays}</div>
    <h4 class="section-title">Nhào & tạo hình (cần ủ)</h4><div class="tile-grid">${shape}</div>
    <h4 class="section-title">Trộn & nướng ngay</h4><div class="tile-grid">${direct}</div>`;
}
function cakePanel(t,x){
  const k=t.cake,ui=x.ui,cool=data(x).cooling?.[t.id];
  const status=k.baking?'<p class="notice">🔥 Cốt bánh đang trong lò. Xem tab Lò.</p>':!k.sponge?`<div class="row wrap">${x.cmd('🎂 Nướng cốt bánh','cb_bake',{item:'sponge',task:t.id},'primary',(data(x).oven||[]).length>=2)}</div>`
    :`<p class="small">Cốt bánh: <b>${x.esc({pale:'sống ruột',golden:'vàng đều',dark:'hơi sậm',burnt:'cháy'}[k.sponge])}</b>${!k.cream&&cool?` · <span class="tag amber">còn ấm, chờ ${cool} nhịp</span>`:''}</p>`;
  const creams=(cc(x).creams||[]).map(c=>{const q=c.id==='whipped'?stock(x,'cream'):stock(x,'butter');
    return tile(x,{emoji:c.emoji,name:c.name,sub:c.id==='whipped'?'hộp kem':'khối bơ',count:q,empty:!q,action:'cream',data:{cream:c.id},selected:(k.cream||ui.cream)===c.id,wanted:!k.cream&&t.needs.cream===c.id,disabled:!!k.cream});}).join('');
  const swatches=`<div class="cb-swatches" role="group" aria-label="Màu kem">${(cc(x).colors||[]).map(c=>`<button type="button" class="cb-swatch ${(k.color||ui.color)===c.id?'on is-selected':''}" data-action="car:color" data-color="${x.esc(c.id)}" aria-pressed="${(k.color||ui.color)===c.id}" ${k.cream?'disabled':''}><i style="background:${x.esc(c.hex)}"></i>${x.esc(c.name)}</button>`).join('')}</div>`;
  const frost=x.cmd('🍦 Phủ kem','cb_frost',{task:t.id,cream:ui.cream||'',color:ui.color||''},'',!['golden','dark'].includes(k.sponge)||!!k.cream||!ui.cream||!ui.color);
  const write=k.text?`<p class="cb-written">✍️ “${x.esc(k.text)}”</p>${x.confirmCmd('🧽 Cạo chữ, viết lại','cb_scrape',{task:t.id},'Cạo lớp chữ và láng lại mặt kem?','ghost small',k.boxed)}`
    :`<div class="cb-write"><label class="field grow">Chữ trên mặt bánh<input id="cb-cake-text" class="input" maxlength="40" autocomplete="off" spellcheck="false" value="${x.esc(ui.cakeText||'')}" placeholder="Gõ đúng từng dấu như phiếu đặt"></label>${x.button('✍️ Viết lên bánh','car:write',{task:t.id},'primary')}</div>`;
  return `<h4 class="section-title">1 · Cốt bánh</h4>${status}
    <h4 class="section-title">2 · Kem & màu</h4><div class="tile-grid">${creams}</div>${swatches}<div class="row wrap">${frost}</div>
    <h4 class="section-title">3 · Viết chữ</h4>${k.cream?write:'<p class="muted small">Phủ kem xong mới viết chữ được.</p>'}
    <h4 class="section-title">4 · Đóng hộp</h4>${x.cmd(`📦 Đóng hộp (${stock(x,'cake_box')})`,'cb_box',{task:t.id},'',!k.cream||!k.text||k.boxed||!stock(x,'cake_box'))}
    <p class="muted small space-top">Mẹo nghề: đọc lại tên với khách, có dấu, trước khi bắt bông viết.</p>`;
}
/** Between guests: bake for the case (walk-in buyers, the office box). */
function prep(x){
  const d=data(x),busy=(d.oven||[]).length||(d.proof||[]).some(p=>!p.left);
  const open=x.ui.cbPrep??!!busy;
  return `<details class="card cb-prep"${open?' open':''}><summary data-action="car:prep">🔥 Lò nướng & tủ kính${busy?' · <b>đang có mẻ bánh</b>':''}</summary>${ovenPanel(null,x)}<h4 class="section-title">Bánh trong tủ</h4>${casePicker(null,x,false)}</details>`;
}

/* ---------- next step & the one primary action ---------- */
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
function primary(t,x,rows,big){
  const cls='primary'+(big?' big':''),d=t.drink;
  if(t.needs.kind==='drink'&&!hidden(t)&&pendingOthers(t).length&&!plated(t)){
    const ready=d.container&&d.shots.length&&!d.pulling&&!d.steaming&&!d.dose&&(d.container!=='paper'||d.lid);
    return x.cmd(`✅ Xong ly ${t.cur+1}`,'cb_done',{task:t.id},cls,!ready);
  }
  const blocked=!!data(x).day?.open_event,label=big?'🛎️ Giao cho khách':'🛎️ Giao';
  const allOk=rows.every(r=>r[0]===true);
  return allOk&&!blocked?x.cmd(label,'cb_serve',{task:t.id,confirm:true},cls,!canServe(t))
    :x.confirmCmd(label,'cb_serve',{task:t.id,confirm:true},blocked?'Có chuyện bất ngờ đang chờ bạn quyết. Xử lý xong rồi hãy giao nhé.':'Chưa khớp hết phiếu. Vẫn giao? Khách sẽ đánh giá đúng những gì bạn làm.',cls,!canServe(t));
}

export default {
  id:'cafe_bakery',
  css:true,
  next(t,x){return nextStep(t,x);},
  idle(x){
    const d=data(x);
    return idlePanel(x,d.day,'cb_event',extras(x)+shelf(x)+prep(x),null,'cb');
  },
  job(t,x){
    const d=data(x),day=d.day;
    const head=`${dayStrip(x,day,true)}${flash(x,day)}${eventCard(x,day,'cb_event')}${queue(x,t)}`;
    if(!t.known){
      const who=x.npc(t.npc),g=t.guest||{};
      return `<div class="career-job cb food">${head}<article class="card ticket cb-ticket"><div class="cb-ticket-head">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3>
        <p class="cb-tags"><span class="tag">${x.esc(g.emoji||'🙂')} ${x.esc(g.label||'Khách')}</span></p></div></div>
        <p class="cb-say">“${x.esc(t.opening)}”</p>${patience(t.patience)}${x.cmd('📝 Nhận order','ask',{task:t.id},'primary full')}</article>${extras(x)}</div>`;
    }
    const n=t.needs,ui=x.ui;
    if(ui.tabFor!==t.id){ui.tabFor=t.id;ui.tab=n.kind==='drink'?'bar':n.kind==='pastry'?'case':'cake';ui.cakeText='';}
    const tabs=[['bar','☕','Quầy pha'],['oven','🔥','Lò & ủ bột'],['case','🥐','Tủ kính'],['cake','🎂','Bánh kem']];
    const racks=(d.oven||[]).length,ready=(d.proof||[]).filter(p=>!p.left).length,inCase=(d.case||[]).filter(l=>l.state==='fresh'&&!l.sale).reduce((a,l)=>a+l.qty,0);
    const badge=k=>k==='oven'&&(racks||ready)?`<em class="cb-badge">${racks+ready}</em>`:k==='case'?`<em class="cb-badge${inCase?' calm':' zero'}">${inCase}</em>`:'';
    const tabBar=`<div class="cb-tabs" role="tablist" aria-label="Khu làm việc">${tabs.map(([k,e,l])=>`<button type="button" role="tab" class="cb-tab ${ui.tab===k?'on':''}" data-action="car:tab" data-tab="${k}" aria-selected="${ui.tab===k}">${e} ${l}${badge(k)}</button>`).join('')}</div>`;
    const panel={bar:()=>n.kind==='drink'?barPanel(t,x):'<p class="notice">Order này không có đồ uống. Bạn vẫn có thể xem máy pha.</p>',oven:()=>ovenPanel(t,x),case:()=>casePanel(t,x),cake:()=>n.kind==='cake'?cakePanel(t,x):'<p class="notice">Order này không phải bánh kem.</p>'}[ui.tab]?.()||'';
    const preview=n.kind==='drink'?cupArt(t,x)+(Object.keys(n.pastry||{}).length?bagArt(t,x):''):n.kind==='pastry'?bagArt(t,x):cakeArt(t,x);
    const rows=rowsOf(t,x),ok=rows.filter(r=>r[0]===true).length;
    const part=n.kind==='cake'?'cake':'drink';
    const dumpable=n.kind==='drink'?!plated(t)&&!!(t.drink.container||t.drink.shots.length||t.drink.milk):n.kind==='cake'?!!(t.cake.sponge||t.cake.cream):false;
    const dump=n.kind!=='pastry'?x.confirmCmd(n.kind==='cake'?'🗑️ Bỏ bánh':'🗑️ Đổ ly','cb_dump',{task:t.id,part},'Đổ bỏ và làm lại? Nguyên liệu đã dùng được ghi hao hụt.','danger small',!dumpable):'';
    const side=`<div class="cb-side"><div class="cb-look">${preview}<div class="cb-look-txt"><p class="cb-status" aria-live="polite">${x.esc(status(t,x))}</p>${trayCups(t)}</div></div>
      <div class="fk-wide-only">${checklist(x,rows)}${primary(t,x,rows,true)}${dump}</div>
      <details class="cb-check cb-narrow-only"${ui.cbCheck?' open':''}><summary data-action="car:check">📋 Kiểm ly · ${ok}/${rows.length} đúng</summary>${checklist(x,rows)}</details></div>`;
    const tools=`<p class="row wrap cb-tools">${dump?`<span class="cb-narrow-only">${dump}</span>`:''}${d.clean_day===x.room.day?'<span class="tag green">🧽 Đã vệ sinh máy hôm nay</span>':x.cmd('🧽 Vệ sinh máy pha','cb_clean',{},'ghost small')} ${x.button('📦 Kho & nhập hàng','inventory',{},'ghost small')}</p>`;
    const barEl=actionBar(x.esc(nextStep(t,x)),primary(t,x,rows,false));
    return `<div class="career-job cb food">${head}${extras(x)}${ticket(t,x)}${tabBar}<div class="workbench"><section class="wb-main" role="tabpanel">${panel}${tools}</section><aside class="wb-side">${side}</aside></div>${barEl}</div>`;
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
    async check(data,el,x){x.ui.cbCheck=!x.ui.cbCheck;},
    async prep(data,el,x){const d=el.closest('details');x.ui.cbPrep=d?!d.open:!x.ui.cbPrep;},
    async write(data,el,x){
      const input=el.closest('.career-job')?.querySelector('#cb-cake-text');
      const text=(input?.value||'').trim();
      x.ui.cakeText=text;
      if(text.length<2){x.toast('Gõ chữ cần viết lên bánh trước nhé.');return;}
      await x.send('cb_write',{task:data.task,text});
    },
  },
  tick(root,x){
    keepBarAboveFooter(root);
    const e=x.cc.extract||{sour:20,bright:25,balanced:30,strong:35},st=x.cc.steam||{base:5,rate:4.2,cool:55,silky:68,hot:76};
    root.querySelectorAll('[data-shot-start]').forEach(el=>{
      const start=Number(el.dataset.shotStart);if(!start)return;
      const s=Math.max(0,x.now()-start)*Number(el.dataset.flow||1);
      el.querySelector('.cb-fill').style.width=Math.min(100,s/SHOT_SCALE*100)+'%';
      el.querySelector('.cb-meter-label').textContent=s.toFixed(1)+' giây · '+(s<e.sour?'chua':s<e.bright?'hơi chua':s<=e.balanced?'DỪNG NGAY!':s<=e.strong?'hơi đậm':'đắng khét');
      el.classList.toggle('ready',s>=e.bright&&s<=e.balanced);el.classList.toggle('over',s>e.strong);
    });
    root.querySelectorAll('[data-steam-start]').forEach(el=>{
      const start=Number(el.dataset.steamStart);if(!start)return;
      const temp=st.base+st.rate*Math.max(0,x.now()-start);
      el.querySelector('.cb-fill').style.width=Math.min(100,temp/TEMP_SCALE*100)+'%';
      el.querySelector('.cb-meter-label').textContent=Math.round(temp)+' °C · '+(temp<st.cool?'còn nguội':temp<=st.silky?'TẮT VÒI!':temp<=st.hot?'quá nóng':'khét sữa');
      el.classList.toggle('ready',temp>=st.cool&&temp<=st.silky);el.classList.toggle('over',temp>st.hot);
    });
    root.querySelectorAll('[data-oven-start]').forEach(el=>{
      const start=Number(el.dataset.ovenStart);if(!start)return;
      const [a,g,z]=(el.dataset.w||'10,20,30').split(',').map(Number),shift=Number(el.dataset.shift)||0,sec=Math.max(0,x.now()-start)+shift;
      el.querySelector('.cb-fill').style.width=Math.min(100,sec/(z+6)*100)+'%';
      el.querySelector('.cb-meter-label').textContent=sec.toFixed(1)+' giây · '+(sec<a?'còn nhạt':sec<g?'VÀNG ĐỀU, LẤY RA!':sec<z?'sậm màu':'cháy rồi!');
      el.classList.toggle('ready',sec>=a&&sec<g);el.classList.toggle('over',sec>=z);
    });
  },
  summary(data,x){return gradeCard(data,x);},
  dock:[['inventory','box','Kho','Nhập & đếm hàng']],
};
