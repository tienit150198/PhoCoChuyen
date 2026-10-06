/** Giao Nhanh Mây Chiều — courier dashboard (plugin career UI).
 * The server owns the clock, fuel, fees and COD; this view only builds a draft
 * route, a change-count and a settlement count before sending them. */
import {t,language} from '../v4/i18n.js';
import {reqList,clean,tip,few,withWhy} from '../ui-kit.js';
import {stepRows,nextHint,finalGo,pending,firstTime,stepLine,stepBar} from '../v4/guide.js';
import {onLeg} from './delivery_navigation.js';
import {keepBarAboveFooter} from './food_kit.js';
import {planBox,stockLines,figures} from './plan_kit.js';
import {renderNeighborhoodMap} from './delivery_map.js';

/* ---------- 🛵 Tự lái / ⏩ Đi nhanh: ride each leg yourself (careers/delivery_drive.js, loaded on the first leg) or tap ---------- */
const MODE_KEY='mnl.dlDrive',HINT_KEY='mnl.dlDriveHint';
let drv=null,drvLoad=null,drvOff=false,lastX=null,canvasOk=null;
const readPref=k=>{try{return localStorage.getItem(k);}catch{return null;}};
const savePref=(k,v)=>{try{localStorage.setItem(k,v);}catch{/* private mode: this visit only */}};
const canDraw=()=>{if(canvasOk===null){try{canvasOk=!!document.createElement('canvas').getContext('2d');}catch{canvasOk=false;}}return canvasOk;};
/** Tự lái is the default; "⏩ Đi nhanh" (remembered) or a phone that cannot draw it keeps the tap flow. */
const driving=()=>!drvOff&&readPref(MODE_KEY)!=='fast'&&canDraw();
/** "Cỏ May Office Tower" → "Office Tower"; "Bồ Câu School" → "School". */
const enLabel=name=>{
  const w=name.split(' '),viet=s=>/[^\x00-\x7F]/.test(s);
  return w.length>1&&viet(w[w.length-2])&&!viet(w[w.length-1])?w[w.length-1]:w.slice(-2).join(' ');
};
const DONE=['completed','referred','cancelled'];
const PACK_TAG={bubble:'fragile',rainbag:'rain',coldpack:'cold',strap:'size'};

const nodes=x=>x.cc.nodes||{};
const nodeOf=(x,id)=>nodes(x)[id]||{name:id,emoji:'📍',x:0,y:0};
/* Clean layout (docs/UI_KIT.md, wave 5): a stop by its emoji and its own name ("🏢 Mây Xanh" for "Chung cư Mây Xanh"):
 * the emoji says what kind of place it is, the last two words are the name every stop has. Classic: the full name. */
const shortName=(x,id)=>{const n=nodeOf(x,id);if(!clean())return n.name;const s=t(n.name);return language()==='en'?enLabel(s):s.split(' ').slice(-2).join(' ');};
/* Pack supplies in one word (clean layout); the full name stays in aria-label. */
const PACK_WORD={bubble:'Xốp',tape:'Keo',rainbag:'Nilon',coldpack:'Đá gel',strap:'Dây ràng'};
/* Order tags in a word or two (clean layout); the full text stays in the title. */
const TAG_WORD={'Dễ vỡ':'Dễ vỡ','Giữ lạnh':'Lạnh','Giấy tờ gốc':'Giấy gốc','Cồng kềnh':'Cồng kềnh','Cho gửi bảo vệ':'Gửi bảo vệ','Trời mưa':'Mưa','Có nước lèo · tránh hẻm xóc':'Nước lèo'};
const dist=(x,a,b)=>{const A=nodeOf(x,a),B=nodeOf(x,b);return Math.abs(A.x-B.x)+Math.abs(A.y-B.y);};
const hm=m=>{const t=17*60+Math.round(Number(m)||0);return `${String(Math.floor(t/60)%24).padStart(2,'0')}:${String(t%60).padStart(2,'0')}`;};
const kg=w=>`${(Number(w||0)/10).toLocaleString('vi-VN')} kg`;
const items=x=>x.content.inventory?.items?.delivery||[];
const itemOf=(x,id)=>items(x).find(i=>i.id===id)||{id,name:id,emoji:'•'};
const ui=x=>x.ui.dl??={draft:[],change:{},settle:[],report:{}};
const live=x=>(x.room.tasks||[]).filter(t=>t.career==='delivery'&&!DONE.includes(t.status));
const destOf=t=>t.dest||t.run?.dest||t.needs?.dest;
const sum=a=>a.reduce((s,v)=>s+Number(v||0),0);
const cmdAttr=(x,command,payload)=>`data-command="${command}" data-payload="${x.esc(JSON.stringify(payload))}"`;
const carAttr=(x,action,data={})=>`data-action="car:${action}" ${Object.entries(data).map(([k,v])=>`data-${k}="${x.esc(v)}"`).join(' ')}`;
function tile(x,{emoji,label,sub='',cls='',attr='',off=false,badge=''}){
  return `<button type="button" class="tile ${cls}" ${attr} ${off?'disabled':''}><span class="tile-emoji" aria-hidden="true">${x.esc(emoji)}</span><b>${x.esc(label)}</b>${sub!==''?`<small>${x.esc(sub)}</small>`:''}${badge}</button>`;
}

function stage(t){
  if(!t.known)return 'new';
  const r=t.run;
  if(r.outcome)return 'done';
  return r.loaded?'bag':'pickup';
}
function tags(t,x){
  const n=t.needs,d=x.room.data||{},out=[];
  if(n.fragile)out.push(['🥚','Dễ vỡ','warn']);
  if(n.cold)out.push(['🧊','Giữ lạnh','info']);
  if(n.paper)out.push(['📄','Giấy tờ gốc','info']);
  if(n.size==='L')out.push(['📐','Cồng kềnh','warn']);
  if(n.cod)out.push(['💵',`COD ${n.cod} xu`,'good']);
  if(n.safe_drop)out.push(['🛡️','Cho gửi bảo vệ','']);
  if(n.kind==='parcel'&&d.weather==='rain')out.push(['🌧️','Trời mưa','info']);
  if(n.soup)out.push(['🍲','Có nước lèo · tránh hẻm xóc','warn']);
  if(t.run?.dest)out.push(['📍',`Địa chỉ mới: ${nodeOf(x,t.run.dest).name}`,'info']);
  const reg=(d.book||[]).find(b=>b.npc===t.npc);
  if(reg?.bond)out.push(['💛',`${reg.level} ${reg.bond}/${x.cc.bond_max||10}`,'good']);
  if(clean())return out.map(([e,l,k])=>{
    const s=TAG_WORD[l]||(e==='💵'?l.replace(/ xu$/,''):e==='📍'?`Mới: ${nodeOf(x,t.run.dest).emoji} ${shortName(x,t.run.dest)}`:e==='💛'?l.replace(/^.*?(\d+\/\d+)$/,'$1'):l);
    return `<span class="dl-tag ${k}" title="${x.esc(l)}" aria-label="${x.esc(l)}">${e} ${x.esc(s)}</span>`;}).join('');
  return out.map(([e,l,k])=>`<span class="dl-tag ${k}">${e} ${x.esc(l)}</span>`).join('');
}
function stopsAt(x,node){
  const rows=live(x),pick=rows.filter(t=>t.known&&!t.run.loaded&&t.needs.pickup===node),drop=rows.filter(t=>t.known&&t.run.loaded&&destOf(t)===node);
  return {pick,drop};
}

/* ---------- status bar ---------- */
function status(x){
  const d=x.room.data||{},fuel=Number(d.fuel)||0,load=Number(d.load)||0,limit=Number(d.limit)||200,cap=Number(d.cap)||250;
  const wx=d.weather==='rain'?['🌧️','Mưa',`${d.mpu} phút/ô · ${d.rate}% xăng/ô`]:['☀️','Nắng',`${d.mpu} phút/ô · ${d.rate}% xăng/ô`];
  const meter=(label,val,max,cls)=>`<div class="dl-meter ${cls}"><div class="dl-meter-top"><span>${label}</span><b>${x.esc(val)}</b></div><div class="bar"><i style="width:${Math.max(0,Math.min(100,max))}%"></i></div></div>`;
  if(clean()){
    // One row of icons and numbers; the words live in each chip's aria-label (and the rates in the "?").
    const chip=(icon,val,max,cls,label)=>`<span class="dl-sc ${cls}" title="${x.esc(label)}" aria-label="${x.esc(label)}"><span aria-hidden="true">${icon}</span><b>${x.esc(val)}</b><i class="dl-sc-bar" aria-hidden="true"><i style="width:${Math.max(0,Math.min(100,max))}%"></i></i></span>`;
    const b=d.bike,w=b?(b.parts||[]).find(p=>p.id===b.worst)||{emoji:'🛞',name:'Lốp',value:b.tyre,low:b.flat_at}:null;
    const bike=w?chip('🔧',`${w.value}%`,w.value,w.value<w.low||b.rim?'bad':w.value<w.low+15?'warn':'',`Xe: ${w.name} ${w.value}%`):'';
    return `<div class="dl-status dl-status-c" role="status">
      <span class="dl-sc dl-sc-clock" aria-label="${x.esc(`Giờ ${hm(d.clock)}, ${wx[1]}, ${wx[2]}`)}"><span aria-hidden="true">🕔</span><b>${x.esc(hm(d.clock))}</b><small aria-hidden="true">${wx[0]} ${d.mpu}′/ô</small></span>
      ${chip('⛽',`${fuel}%`,fuel,fuel<20?'bad':fuel<35?'warn':'',`Xăng ${fuel}% · ${d.rate}% mỗi ô phố`)}
      ${chip('📦',`${(load/10).toLocaleString('vi-VN')}/${limit/10}`,load/limit*100,load>limit*.8?'warn':'',`Tải ${(load/10).toLocaleString('vi-VN')}/${kg(limit)}`)}
      ${chip('💵',`${d.owed||0}/${cap}`,(d.owed||0)/cap*100,(d.owed||0)>cap*.7?'warn':'',`Túi COD ${d.owed||0}/${cap} xu`)}${bike}
    </div>`;
  }
  return `<div class="dl-status" role="status">
    <div class="dl-clock"><span aria-hidden="true">🕔</span><b>${x.esc(hm(d.clock))}</b><small>${wx[0]} ${wx[1]} · ${x.esc(wx[2])}</small></div>
    <div class="dl-meters">${meter('⛽ Xăng',`${fuel}%`,fuel,fuel<20?'bad':fuel<35?'warn':'')}
    ${meter('📦 Tải',`${(load/10).toLocaleString('vi-VN')}/${kg(limit)}`,load/limit*100,load>limit*.8?'warn':'')}
    ${meter('💵 Túi COD',`${d.owed||0}/${cap} xu`,(d.owed||0)/cap*100,(d.owed||0)>cap*.7?'warn':'')}
    ${bikeMeter(x,meter)}</div>
  </div>`;
}

function bikeMeter(x,meter){
  const b=x.room.data?.bike;if(!b)return '';
  const w=(b.parts||[]).find(p=>p.id===b.worst)||{emoji:'🛞',name:'Lốp',value:b.tyre,low:b.flat_at};
  const cls=w.value<w.low||b.rim?'bad':w.value<w.low+15?'warn':'';
  return meter('🔧 Xe',`${w.emoji} ${w.value}%`,w.value,cls);
}

/* ---------- care: folds that remember whether the player opened them ---------- */
function foldBox(x,key,summary,body,auto=false,cls=''){
  const u=ui(x),open=u.open?.[key]??auto;
  return `<details class="fold dl-fold ${cls}"${open?' open':''}><summary ${carAttr(x,'fold',{key})}>${summary}</summary><div class="fold-body">${body}</div></details>`;
}
/** A one-line fold whose open state follows the step (`auto`) until the player taps it. Not a <details>:
 * the sheet host restores every <details> by position after a re-render, which would undo `auto`.
 * The body is only drawn while open. */
function pane(x,key,summary,body,auto=false,cls=''){
  const open=(ui(x).pane??={})[key]??auto;
  return `<div class="dl-pane ${cls}${open?' open':''}"><button type="button" class="dl-pane-sum" data-action="car:pane" data-key="${x.esc(key)}" data-open="${open?1:0}" aria-expanded="${open}">${summary}</button>${open?`<div class="dl-pane-body">${body}</div>`:''}</div>`;
}
const partState=p=>p.value<p.low?'bad':p.value<p.low+15?'warn':'';
function partList(x,b){
  return `<ul class="dl-parts" aria-label="Tình trạng xe">${b.parts.map(p=>{const st=partState(p)||(p.id==='tyre'&&b.rim?'bad':'');
    return `<li class="${st}"><span class="dl-part-emoji" aria-hidden="true">${x.esc(p.emoji)}</span><span class="dl-part-name"><b>${x.esc(p.name)}</b>${st||p.id==='tyre'&&b.rim?`<small>${x.esc(p.id==='tyre'&&b.rim?'Vành móp vì chạy bánh xẹp. ':'')}${x.esc(p.effect)}</small>`:''}</span><span class="dl-part-val"><b>${p.value}%</b><span class="bar" aria-hidden="true"><i style="width:${p.value}%"></i></span></span></li>`;}).join('')}</ul>`;
}
function bikeFold(x){
  const d=x.room.data||{},b=d.bike;if(!b?.parts)return '';
  const w=b.parts.find(p=>p.id===b.worst)||b.parts[0],st=partState(w);
  const summary=`🔧 Chăm xe · <span class="${st==='bad'?'bad-text':st==='warn'?'warn-text':''}">${x.esc(w.name)} ${w.value}%</span>${b.alert?' · cần sửa':''}`;
  const where=d.at==='garage'?'':`<p class="small muted">Sửa ở ${x.esc(nodeOf(x,'garage').emoji)} ${x.esc(nodeOf(x,'garage').name)} — thêm vào lộ trình. Cây xăng chỉ thay ruột lốp.</p>`;
  return foldBox(x,'bike',summary,partList(x,b)+where,b.alert&&d.at!=='garage');
}
function garagePanel(x){
  const d=x.room.data||{},b=d.bike;if(!b?.parts||d.at!=='garage')return '';
  const u=ui(x),need=b.parts.filter(p=>p.need);
  if(!u.fix||u.fixDay!==x.room.day){u.fix=need.filter(p=>partState(p)||p.id==='tyre'&&b.rim).map(p=>p.id);u.fixDay=x.room.day;}
  u.fix=u.fix.filter(id=>need.some(p=>p.id===id));
  const sel=u.fix,cost=sum(need.filter(p=>sel.includes(p.id)).map(p=>p.price)),mins=(x.cc.fix_minutes||3)*sel.length;
  const tiles=b.parts.map(p=>{const on=sel.includes(p.id),st=partState(p);
    return `<button type="button" class="tile dl-fix ${on?'selected':''} ${st}" ${carAttr(x,'fix',{part:p.id})} aria-pressed="${on}" ${p.need?'':'disabled'}><span class="tile-emoji" aria-hidden="true">${x.esc(p.emoji)}</span><b>${x.esc(p.name)}</b><small>${p.value}% · ${p.need?`${p.price} xu`:'còn mới'}</small></button>`;}).join('');
  const names=b.parts.filter(p=>sel.includes(p.id)).map(p=>p.name.toLowerCase()).join(', ');
  return `<section class="dl-sec dl-garage"><h4 class="section-title">🔧 Tiệm sửa xe Chú Bảy</h4>
    ${need.length?`<div class="dl-grid pack">${tiles}</div>
    <div class="row wrap space-top">${x.confirmCmd(sel.length?`🔧 Sửa ${sel.length} món · ${cost} xu`:'Chọn bộ phận để sửa','dl_fix',{parts:sel},`Sửa ${names} hết ${cost} xu (mất ${mins} phút)?`,'primary',!sel.length||cost>(Number(x.room.money)||0))}</div>
    ${cost>(Number(x.room.money)||0)?'<p class="small bad-text">Ví chưa đủ — bỏ bớt, sửa món gấp nhất trước.</p>':''}`:'<p class="muted">Chú Bảy xem qua: “Xe ngon lành, chưa cần làm gì hết con.”</p>'}</section>`;
}
function forecastFold(x){
  const f=x.room.data?.forecast;if(!f)return '';
  const summary=`📡 ${x.esc(f.label)}: ${x.esc(f.emoji)} ${x.esc(f.name)} · ${f.advice.length} lời khuyên`;
  return foldBox(x,'fc',summary,`<p class="small muted">${x.esc(f.text)}</p><ul class="dl-advice">${f.advice.map(a=>`<li>${x.esc(a)}</li>`).join('')}</ul>`,false,'dl-fc');
}
const hearts=(n,max)=>'💛'.repeat(Math.min(n,5))+(n>5?`+${n-5}`:'');
function bookFold(x){
  const book=x.room.data?.book;if(!book)return '';
  const known=book.filter(b=>b.visits>0).length,max=x.cc.bond_max||10;
  const rows=book.map(b=>`<li class="dl-reg ${b.visits?'':'new'}"><div class="dl-reg-head"><b>${x.esc(b.name)}</b><small>${x.esc(b.role)}</small><span class="dl-bond" aria-label="Thân thiết ${b.bond} trên ${max}">${b.bond?hearts(b.bond,max):'🤍'} ${b.bond}/${max}</span></div>
    <small class="dl-reg-level">${x.esc(b.level)}${b.tip?` · +${b.tip} xu tiền cà phê mỗi đơn sạch`:''} · đã giao ${b.visits} đơn${nextLevel(x,b)}</small>
    ${b.notes.length?`<ul class="dl-notes">${b.notes.map(n=>`<li><span aria-hidden="true">${x.esc(KIND_EMOJI[n.kind]||'📝')}</span> ${x.esc(n.text)}</li>`).join('')}</ul>`:''}
    ${b.locked?`<small class="muted">🔒 ${b.next_in?`Giao thêm ${b.next_in} đơn`:'Giao thêm'} để biết thêm một lời dặn.</small>`:''}</li>`).join('');
  return foldBox(x,'book',`📒 Sổ tay khách quen · ${known}/${book.length} người đã quen`,`<ul class="dl-book">${rows}</ul>`);
}
const KIND_EMOJI={call:'📞',gate:'🔢',carry:'🤲',photo:'📸',check:'🔍'};
/** " · 3💛 → khách quen (+2 xu)": the next reward on the bond ladder. */
function nextLevel(x,b){
  const up=[...(x.cc.bond_tip||[])].sort((p,q)=>p.at-q.at).find(l=>l.at>b.bond);
  return up?` · ${up.at}💛 → ${x.esc(up.label)} (+${up.tip} xu/đơn)`:'';
}
function areaLine(x){
  const a=x.room.data?.areas||{},sm=x.cc.area_smooth||2,lo=x.cc.area_local||5;
  const rows=Object.entries(a).filter(([,n])=>n>=sm).sort((p,q)=>q[1]-p[1]).map(([id,n])=>`${nodeOf(x,id).emoji} ${nodeOf(x,id).name}${n>=lo?' (lối tắt riêng)':''}`);
  return rows.length?`<p class="small dl-areas">🗺️ Thuộc hẻm: ${x.esc(rows.join(', '))}.</p>`:'';
}
/** Everything about the day that is not the current step (road, goals, bike, regulars), in one fold.
 * A bike that needs fixing stays outside it, open, so the warning is never hidden. */
function careSection(x,key='today'){
  const d=x.room.data||{},r=d.road,sc=d.score,q=sc?.quest,alert=d.bike?.alert&&d.at!=='garage';
  const bits=[r?`${x.esc(r.mod.emoji)} ${x.esc(r.mod.name)}`:'',sc?`🔥 ${sc.streak}`:'',q?`🎯 ${q.done}/${q.goal}${q.paid?' ✓':''}`:''].filter(Boolean);
  const inner=`${roadBoard(x)}${scoreStrip(x)}${alert?'':bikeFold(x)}${bookFold(x)}`;
  // Clean layout: the road's name goes (its emoji stays, the board is one tap away), "Hôm nay" only when nothing follows.
  const head=clean()?`<span aria-hidden="true">📅</span>${bits.length?' '+[r?x.esc(r.mod.emoji):'',...bits.slice(r?1:0)].filter(Boolean).join(' · '):' Hôm nay'}`:`📅 Hôm nay${bits.length?' · '+bits.join(' · '):''}`;
  return `<section class="dl-care" aria-label="Chăm xe và khách quen">${alert?bikeFold(x):''}${pane(x,key,head,`<div class="dl-today">${inner}</div>`,false,'dl-today-fold')}</section>`;
}
function wishes(t,x){
  const b=(x.room.data?.book||[]).find(e=>e.npc===t.npc);if(!b||!b.notes.length)return '';
  const r=t.run,care=r.care||[],kinds=x.cc.care_kinds||{},c=clean();
  const rows=b.notes.map(n=>{const done=n.kind==='call'?r.called:n.kind==='gate'?true:care.includes(n.kind);
    return {ok:done?true:null,icon:KIND_EMOJI[n.kind]||'📝',label:n.text,note:c?'':n.kind==='gate'?'tự áp dụng khi tới cổng':done?'đã làm':n.kind==='call'?'bấm “Gọi khách”':''};});
  const btns=b.notes.filter(n=>kinds[n.kind]&&!care.includes(n.kind)).map(n=>x.cmd(c?`${KIND_EMOJI[n.kind]} ${x.esc(few(kinds[n.kind].label,2))} +${kinds[n.kind].minutes}′`:`${KIND_EMOJI[n.kind]} ${kinds[n.kind].label} · +${kinds[n.kind].minutes} phút`,'dl_care',{task:t.id,kind:n.kind},'ghost')).join('');
  return `<div class="dl-wish"><p class="dl-sub">📒 ${x.esc(b.name)} ${c?'dặn':'từng dặn'}</p>${reqList(rows,x.esc,'Lời dặn của khách quen')}${btns?`<div class="row wrap space-top">${btns}</div>`:''}</div>`;
}

/* ---------- road board, courier score, surprises ---------- */
function roadBoard(x){
  const r=x.room.data?.road;if(!r)return '';
  const signs=(r.signs||[]).map(g=>`<span class="dl-sign ${g.kind} ${g.now?'now':''}">${x.esc(g.text)}</span>`).join('');
  return `<section class="dl-road" aria-label="Đường hôm nay"><div class="dl-road-head"><span class="dl-road-emoji" aria-hidden="true">${x.esc(r.mod.emoji)}</span><div><b>Đường hôm nay: ${x.esc(r.mod.name)}</b><small>${x.esc(r.mod.text)}</small></div></div>${signs?`<div class="dl-signs">${signs}</div>`:''}${forecastFold(x)}</section>`;
}
function scoreStrip(x){
  const sc=x.room.data?.score;if(!sc)return '';
  const num=v=>(v/10).toLocaleString('vi-VN',{minimumFractionDigits:1});
  const star=sc.rating==null?`⭐ Chấm điểm sau ${Math.max(1,5-(sc.rated||0))} đơn`:`⭐ ${num(sc.rating)}${sc.top?` · ưu tiên +${sc.top_bonus} xu/đơn`:` · ${num(sc.top_at)} được ưu tiên`}`;
  const q=sc.quest;
  const chips=[`<span class="dl-chip ${sc.top?'good':''}">${x.esc(star)}</span>`,
    `<span class="dl-chip">🔥 Chuỗi sạch ${sc.streak} · +${sc.streak_bonus} xu mỗi ${sc.every} đơn</span>`];
  if(q)chips.push(`<span class="dl-chip ${q.paid?'good':''}">🎯 Mốc ca ${q.done}/${q.goal}${q.paid?' ✓':` · +${q.bonus} xu`}</span>`);
  return `<div class="dl-score" aria-label="Điểm tài xế">${chips.join('')}</div>`;
}
function deskCard(x){
  const desk=x.room.data?.desk;if(!desk)return '';
  const ev=desk.ev;
  if(ev){
    const opts=ev.options.map(o=>{
      const poor=o.cost>(Number(x.room.money)||0);
      const inner=`<span class="dl-opt-label">${x.esc(o.label)}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}${o.cost?`<em class="dl-cost">−${x.fmt(o.cost)} xu${poor?' · ví chưa đủ':''}</em>`:''}`;
      return o.cost?x.confirmCmd(inner,'dl_decide',{option:o.id},`Lựa chọn này tốn ${x.fmt(o.cost)} xu. Đồng ý?`,'dl-opt',poor):x.cmd(inner,'dl_decide',{option:o.id},'dl-opt');
    }).join('');
    return `<section class="dl-event ${ev.tone==='tense'?'tense':''}" role="group" aria-labelledby="dl-ev-title"><div class="dl-ev-head"><span class="dl-ev-emoji" aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>Chuyện dọc đường</small><h3 id="dl-ev-title">${x.esc(ev.title)}</h3></div></div>
      <p>${x.esc(ev.text)}</p><div class="dl-opts">${opts}</div></section>`;
  }
  const last=desk.last,key=last?`${last.script}-${last.choice}-${last.day}-${(desk.log||[]).length}`:'';
  if(last&&last.day===x.room.day&&ui(x).seen!==key){
    return `<div class="dl-last ${last.good===true?'good':last.good===false?'bad':''}" role="status"><span aria-hidden="true">${x.esc(last.emoji)}</span><p><b>${x.esc(last.title)}</b> · ${x.esc(last.outcome)}</p><button type="button" class="btn ghost small dl-x" ${carAttr(x,'seen',{key})} aria-label="Đã đọc">✕</button></div>`;
  }
  return '';
}

/* ---------- map ---------- */
function map(x){
  const d=x.room.data||{},all={},status={};
  for(const [id,n] of Object.entries(nodes(x))){
    all[id]={...n,name:t(n.name),label:clean()?shortName(x,id):language()==='en'?enLabel(t(n.name)):n.name.split(' ').slice(0,2).join(' ')};
    const s=stopsAt(x,id);status[id]={pick:s.pick.length,drop:s.drop.length};
  }
  return renderNeighborhoodMap({nodes:all,at:d.at,route:d.route||[],draft:ui(x).draft,status,signs:d.road?.signs||[],minutes:d.mpu,
    text:{title:t('Khu phố Mây Chiều'),here:t('Bạn đang ở'),planned:t('Tuyến đã chốt'),draft:t('Tuyến nháp'),pick:t('Điểm lấy hàng'),drop:t('Điểm giao hàng'),
      residential:t('Khu dân cư'),services:t('Khu dịch vụ'),garden:t('Khu nhà vườn'),order:t('Thứ tự điểm dừng'),scale:t(`Mỗi ô phố ${d.mpu} phút`)},bare:clean()});
}

/* ---------- route planner ---------- */
function planner(x,ride=true){
  const d=x.room.data||{},u=ui(x),all=nodes(x),mpu=Number(d.mpu)||3,rate=Number(d.rate)||2,c=clean();
  const planned=d.route||[],eta=d.eta||[];
  let body='';
  if(planned.length){
    const next=eta[0]||{node:planned[0],blocks:dist(x,d.at,planned[0]),minutes:dist(x,d.at,planned[0])*mpu,at:(d.clock||0)+dist(x,d.at,planned[0])*mpu,fuel:(d.fuel||0)-dist(x,d.at,planned[0])*rate,notes:[]};
    body+=`<ol class="dl-eta">${eta.map((r,i)=>`<li class="${r.fuel<0?'bad':''}"><span>${i+1}</span><b>${x.esc(place(x,r.node))}</b><small>${x.esc(hm(r.at))} · ${r.blocks} ô · ${c?'⛽':'xăng còn '}${r.fuel}%${(r.notes||[]).length?' · '+x.esc(r.notes.join(', ')):''}</small></li>`).join('')}</ol>`+(ride?rideChoice(x,next):'');
  }
  const from=u.draft.length?u.draft[u.draft.length-1]:(planned.length?planned[planned.length-1]:d.at);
  let clock=planned.length&&eta.length?eta[eta.length-1].at:(d.clock||0),fuel=planned.length&&eta.length?eta[eta.length-1].fuel:(d.fuel||0),prev=planned.length?planned[planned.length-1]:d.at;
  const draftRows=u.draft.map((id,i)=>{const b=dist(x,prev,id);clock+=b*mpu;fuel-=b*rate;prev=id;return `<li class="${fuel<0?'bad':''}"><span>${planned.length+i+1}</span><b>${x.esc(place(x,id))}</b><small>~${x.esc(hm(clock))} · ${b} ô · ${c?'⛽':'xăng '}~${fuel}%</small></li>`;}).join('');
  const tiles=Object.entries(all).map(([id,n])=>{
    const s=stopsAt(x,id),b=dist(x,from,id),bits=[];
    if(s.pick.length)bits.push(`lấy ${s.pick.length}`);
    if(s.drop.length)bits.push(`giao ${s.drop.length}`);
    if(id==='hub'&&(d.owed||0)>0)bits.push(c?'💵':'nộp COD');
    if(id==='gas'&&!c)bits.push('đổ xăng');
    if(id==='garage'&&d.bike?.alert)bits.push(c?'🔧!':'sửa xe');
    const hot=s.pick.length||s.drop.length||(id==='hub'&&(d.owed||0)>0)||(id==='garage'&&d.bike?.alert);
    return tile(x,{emoji:n.emoji,label:shortName(x,id),sub:`${c?'':`${b} ô · `}${b*mpu}${c?'′':' phút'}${bits.length?' · '+bits.join(', '):''}`,cls:`${hot?'hot':''} ${id===from?'here':''}`,attr:`${carAttr(x,'stop',{node:id})}${c?` aria-label="${x.esc(n.name)}"`:''}`,off:id===from});
  }).join('');
  const sameAsPlan=!u.draft.length;
  return `${body}
    <p class="dl-sub">${c?(planned.length?'➕ Điểm sau':'👆 Chọn điểm dừng'):planned.length?'Thêm điểm sau tuyến đang chạy':'Chọn điểm dừng theo thứ tự'}</p>
    ${u.draft.length?`<ol class="dl-eta draft">${draftRows}</ol>`:''}
    <div class="row wrap">
      <button type="button" class="btn primary" ${carAttr(x,'plan')} ${sameAsPlan?'disabled':''}>🗺️ Chốt lộ trình</button>
      <button type="button" class="btn ghost small" ${carAttr(x,'undo')} ${u.draft.length?'':'disabled'}${c?' aria-label="Bỏ điểm cuối"':''}>${c?'↶':'↶ Bỏ điểm cuối'}</button>
      <button type="button" class="btn ghost small" ${carAttr(x,'clear')} ${u.draft.length?'':'disabled'}${c?' aria-label="Xóa nháp"':''}>${c?'✕':'✕ Xóa nháp'}</button>
    </div>
    <div class="dl-grid stops">${tiles}</div>`;
}

/** The leg the scooter rides next (the server's ETA row, or an estimate before it has one). */
function nextLeg(x){
  const d=x.room.data||{},planned=d.route||[],mpu=Number(d.mpu)||3,rate=Number(d.rate)||2;
  if(!planned.length)return null;
  const b=dist(x,d.at,planned[0]);
  return (d.eta||[])[0]||{node:planned[0],blocks:b,minutes:b*mpu,at:(d.clock||0)+b*mpu,fuel:(d.fuel||0)-b*rate,notes:[]};
}
/** What the current step is about: planning the route, riding the planned leg, or work at this stop. */
function phaseOf(g){
  const go=pending(g?.steps)?.go||{};
  return go.cmd==='dl_plan'||go.act==='car:plan'?'plan':go.cmd==='dl_ride'||go.act==='car:quick'?'ride':'stop';
}
/** The route: the whole planner (map, stops) is open only while planning is the step; riding shows the
 * two ways to go above it; any other step keeps it as one closed line. */
function routeSec(x,phase,tag,dn=null){
  const d=x.room.data||{},planned=d.route||[],leg=nextLeg(x),drv=dn&&driving(),ride=phase==='ride'&&leg&&!drv;
  const sum=clean()?(planned.length?`🗺️ ${planned.length} điểm · → ${x.esc(place(x,planned[0]))}`:'🗺️ Bản đồ'):planned.length?`🗺️ Lộ trình · ${planned.length} điểm · tiếp theo ${x.esc(place(x,planned[0]))}`:'🗺️ Lộ trình · bản đồ & điểm dừng';
  const body=`${map(x)}${areaLine(x)}${planner(x,!ride)}`;
  const sw=dn&&!drv?modeSwitch(x):'';
  const auto=phase==='plan'&&!drv&&(!clean()||ui(x).draft.length>0);
  return `${ride?`<section class="dl-sec dl-ride">${sw}${rideChoice(x,leg)}</section>`:sw?`<div class="dl-modebar">${sw}</div>`:''}<section class="dl-sec dl-route-sec">${pane(x,`route-${tag}-${phase}-${planned.length}`,sum,body,auto,'dl-route-fold')}</section>`;
}
function rideChoice(x,next){
  const name=x.esc(nodeOf(x,next.node).name),alt=next.short,soup=live(x).some(t=>t.known&&t.run.loaded&&t.needs.soup&&!t.run.spilled);
  const c=clean(),can=(x.room.data?.can||{}).dl_ride,mins=next.minutes??next.blocks*(x.room.data?.mpu||3);
  // Clean layout: minutes as ′, the stop by its short name; every warning of the leg (jam, works, flood, spilt broth,
  // tyre wear) stays on its button. The main road is dimmed with the server's fuel reason when it cannot go.
  const main=withWhy(`<button type="button" class="btn primary big dl-way" ${cmdAttr(x,'dl_ride',{way:'main'})}${c?` aria-label="${x.esc(`Đường chính tới ${nodeOf(x,next.node).name}`)}"`:''}><span>${c?`🛣️ Đường chính → ${x.esc(place(x,next.node))}`:`🛣️ Đường chính tới ${name}`}</span><small>${c?`${mins}′`:`${mins} phút`} · ${next.blocks} ô${(next.notes||[]).length?' · '+x.esc(next.notes.join(', ')):''}</small></button>`,next.node===(x.room.data?.route||[])[0]?can:true);
  if(!alt)return `<div class="dl-ways">${main}</div>`;
  if(alt.brake)return `<div class="dl-ways">${main}<button type="button" class="btn ghost dl-way" disabled><span>🏍️ Hẻm tắt</span><small>${c?'🛑 Má phanh mòn: không an toàn':'🛑 Má phanh mòn — hẻm dốc không an toàn. Thay ở tiệm Chú Bảy.'}</small></button></div>`;
  const bumpy=!alt.smooth,warn=[...(alt.notes||[]),...(soup&&bumpy?['đổ nước lèo trên xe']:[]),...(bumpy?[c?'lốp mòn ×2':'lốp mòn gấp đôi']:[])];
  return `<div class="dl-ways">${main}<button type="button" class="btn ghost dl-way ${alt.stall||soup&&bumpy?'risky':''} ${alt.smooth?'known':''}" ${cmdAttr(x,'dl_ride',{way:'short'})}><span>🏍️ Hẻm tắt</span><small>${alt.minutes}${c?'′':' phút'} · ${alt.blocks} ô · ${x.esc(warn.join(', '))}</small></button></div>`;
}

/* ---------- orders at the current stop ---------- */
function head(t,x){
  const n=t.needs,who=x.npc(t.npc);
  if(clean()){
    const dn=nodeOf(x,n.dest),addr=String(n.address||'').replace(dn.name,`${dn.emoji} ${shortName(x,n.dest)}`).replace(t.run.unit?/\s*\([^)]*phòng[^)]*\)\s*$/:/$^/,'');
    return `<div class="dl-ohead"><span class="dl-oemoji" aria-hidden="true">${x.esc(n.emoji)}</span><div class="grow"><b>${x.esc(n.item)}</b><small>${x.esc(who.display_name)} · ${x.esc(addr)}${t.run.unit?` · <strong>${x.esc(t.run.unit)}</strong>`:''}</small><div class="dl-tags">${tags(t,x)}</div></div></div>`;
  }
  return `<div class="dl-ohead"><span class="dl-oemoji" aria-hidden="true">${x.esc(n.emoji)}</span><div class="grow"><b>${x.esc(n.item)}</b><small>${x.esc(who.display_name)} · ${x.esc(n.address)}${t.run.unit?` · <strong>${x.esc(t.run.unit)}</strong>`:''}</small><div class="dl-tags">${tags(t,x)}</div></div></div>`;
}
/** "🔒 2 món mở ở cấp 2–3": locked things in one line (names and levels in the tooltip). */
function lockChip(x,list){
  if(!list.length)return '';
  const lv=list.map(i=>Number(i.unlock)||1),lo=Math.min(...lv),hi=Math.max(...lv);
  const names=list.map(i=>`${i.name} (cấp ${Number(i.unlock)||1})`).join(', ');
  return `<p class="dl-lock" title="${x.esc(names)}" aria-label="${x.esc(`Chưa mở: ${names}`)}">🔒 ${list.length}${clean()?'':` món mở ở cấp ${lo===hi?lo:`${lo}–${hi}`}`}</p>`;
}
function packTiles(t,x){
  const r=t.run,inv=x.room.inventory||{stock:{},locked:[]},shut=items(x).filter(i=>(inv.locked||[]).includes(i.id));
  return `<div class="dl-grid pack">${items(x).filter(i=>!shut.includes(i)).map(i=>{
    const used=r.packed.includes(i.id),locked=(inv.locked||[]).includes(i.id),q=inv.stock?.[i.id]??0;
    const off=used||locked||!q||(r.loaded&&i.id!=='rainbag');
    if(clean())return tile(x,{emoji:i.emoji,label:PACK_WORD[i.id]||i.name,sub:used?'✓':locked?`🔒 ${i.unlock}`:`×${q}`,cls:`${used?'selected':''} ${locked?'locked':''} ${!q&&!used?'empty':''}`,attr:`${cmdAttr(x,'dl_pack',{task:t.id,item:i.id})} aria-label="${x.esc(`${i.name}: ${used?'đã dùng':`còn ${q} ${i.unit||''}`}`)}"`,off});
    return tile(x,{emoji:i.emoji,label:i.name,sub:used?'✓ đã dùng':locked?`🔒 cấp ${i.unlock}`:`còn ${q} ${i.unit||''}`,cls:`${used?'selected':''} ${locked?'locked':''} ${!q&&!used?'empty':''}`,attr:cmdAttr(x,'dl_pack',{task:t.id,item:i.id}),off});
  }).join('')}</div>${lockChip(x,shut)}`;
}
function pickupCard(t,x){
  const n=t.needs,r=t.run,d=x.room.data||{},u=ui(x),limit=Number(d.limit)||200;
  if(clean())return pickupClean(t,x);
  let body='';
  if(n.kind==='food'){
    const wait=(d.clock||0)<t.ready;
    body+=`<p class="dl-line">🍳 Quán báo xong lúc <b>${x.esc(hm(t.ready))}</b> · hẹn khách trước <b>${x.esc(hm(t.due))}</b></p>`;
    if(wait)body+=`<p class="notice amber">Món chưa xong — còn khoảng ${t.ready-(d.clock||0)} phút.</p>`;
    body+=`<div class="row wrap">${wait?x.cmd('⏳ Chờ quán 5 phút','dl_wait',{},'ghost'):''}
      ${x.cmd(r.checked?'✓ Đã so túi với bill':'🧾 So túi với bill','dl_check',{task:t.id},r.checked?'ghost':'',r.checked||wait)}
      ${x.cmd('🛵 Nhận món lên thùng','dl_load',{task:t.id},'primary',wait)}</div>`;
    if(r.missing)body+=`<p class="small">Đã bổ sung: ${x.esc(r.missing)}.</p>`;
    return body;
  }
  body+=r.checked?'<p class="dl-done">✓ Đã cân & kiểm</p>':`<div class="row wrap">${x.cmd('⚖️ Cân & kiểm hàng','dl_check',{task:t.id},'primary')}</div>`;
  if(r.checked){
    const diff=r.w!==n.w;
    body+=`<dl class="dl-kv"><dt>Cân thực tế</dt><dd class="${diff?'warn-text':''}">${kg(r.w)} ${diff?`(khai ${kg(n.w)})`:'— khớp'}</dd><dt>Vỏ thùng</dt><dd>${r.seam?'⚠️ hở mép keo':'nguyên vẹn'}</dd></dl>`;
    if(diff&&r.w<=limit){const on=!!u.report[t.id];body+=`<button type="button" class="btn dl-toggle ${on?'on':''}" ${carAttr(x,'report',{task:t.id})} aria-pressed="${on}">${on?'☑':'☐'} Báo lệch cân lên app (phụ phí đúng quy định)</button>`;}
  }
  body+=`<p class="dl-sub">Đóng gói</p>${packTiles(t,x)}`;
  const tooHeavy=r.checked&&r.w>limit,noStrap=n.size==='L'&&!r.packed.includes('strap');
  body+=`<div class="row wrap space-top">${x.cmd('🛵 Nhận hàng lên xe','dl_load',{task:t.id,report:!!u.report[t.id]},'primary',!r.checked||tooHeavy)}
    ${r.checked&&(tooHeavy||noStrap)?x.confirmCmd('🚫 Từ chối nhận','dl_refuse',{task:t.id},tooHeavy?`Hàng ${kg(r.w)} vượt tải ${kg(limit)} của xe máy. Từ chối và báo bưu cục chuyển xe tải?`:'Hàng cồng kềnh mà không có dây ràng. Từ chối nhận?','danger'):''}</div>`;
  return body;
}
/** Clean layout: the facts to check stay (time the kitchen is done and the customer's deadline, the weight against what
 * the shop declared, the box's seam); the step's own button is the bar's, so the card has no second one. The supplies
 * wait in one line until the parcel is weighed, then open by themselves. */
function pickupClean(t,x){
  const n=t.needs,r=t.run,d=x.room.data||{},u=ui(x),limit=Number(d.limit)||200;
  let body='';
  if(n.kind==='food'){
    const wait=(d.clock||0)<t.ready;
    body+=`<p class="dl-line" aria-label="${x.esc(`Quán báo xong lúc ${hm(t.ready)}, hẹn khách trước ${hm(t.due)}`)}">🍳 xong <b>${x.esc(hm(t.ready))}</b> · ⏰ <b>${x.esc(hm(t.due))}</b>${wait?` · ⏳ còn ${t.ready-(d.clock||0)}′`:''}</p>`;
    body+=`<div class="row wrap">${wait?x.cmd('⏳ 5′','dl_wait',{},'ghost small'):''}${r.checked?'<span class="dl-done">✓ So bill</span>':x.cmd('🧾 So bill','dl_check',{task:t.id},'',wait)}</div>`;
    if(r.missing)body+=`<p class="small">+ ${x.esc(r.missing)}</p>`;
    return body;
  }
  if(r.checked){
    const diff=r.w!==n.w;
    body+=`<p class="dl-line" aria-label="${x.esc(`Cân thực tế ${kg(r.w)}${diff?`, shop khai ${kg(n.w)}`:', khớp'}. Vỏ thùng ${r.seam?'hở mép keo':'nguyên vẹn'}`)}">⚖️ <b class="${diff?'warn-text':''}">${kg(r.w)}</b>${diff?` ≠ khai ${kg(n.w)}`:' ✓'} · 📦 ${r.seam?'<b class="warn-text">⚠️ hở keo</b>':'✓'}</p>`;
    if(diff&&r.w<=limit){const on=!!u.report[t.id];body+=`<button type="button" class="btn dl-toggle ${on?'on':''}" ${carAttr(x,'report',{task:t.id})} aria-pressed="${on}">${on?'☑':'☐'} Báo lệch cân</button>${tip('Báo lệch cân lên app: shop trả phụ phí đúng quy định.','☐ Báo lệch cân')}`;}
  }
  const pk=`pack-${t.id}`,packOpen=(u.pane||{})[pk]??!!r.checked;
  body+=pane(x,pk,packOpen?'<span aria-label="Đóng gói">📦</span>':'📦 Gói',packTiles(t,x),!!r.checked,'dl-pack-fold');
  const tooHeavy=r.checked&&r.w>limit,noStrap=n.size==='L'&&!r.packed.includes('strap');
  if(r.checked&&(tooHeavy||noStrap))body+=`<div class="row wrap space-top">${x.confirmCmd('🚫 Từ chối nhận','dl_refuse',{task:t.id},tooHeavy?`Hàng ${kg(r.w)} vượt tải ${kg(limit)} của xe máy. Từ chối và báo bưu cục chuyển xe tải?`:'Hàng cồng kềnh mà không có dây ràng. Từ chối nhận?','danger')}</div>`;
  return body;
}
function keypad(x,action,key,total,extra={}){
  const notes=x.cc.notes||[50,20,10,5,2,1],c=clean();
  return `<div class="dl-keypad">${notes.map(v=>`<button type="button" class="btn dl-note" ${carAttr(x,action,{...extra,v})}>${v}</button>`).join('')}
    <button type="button" class="btn ghost dl-note" ${carAttr(x,action+'Clear',extra)} ${total?'':'disabled'}${c?' aria-label="Đếm lại"':''}>${c?'↺':'Đếm lại'}</button></div>`;
}
function dropCard(t,x){
  const n=t.needs,r=t.run,d=x.room.data||{},u=ui(x);
  if(clean())return dropClean(t,x);
  let body='';
  if(t.due!=null)body+=`<p class="dl-line">⏰ Hẹn trước <b>${x.esc(hm(t.due))}</b>${(d.clock||0)>t.due?` · <span class="bad-text">đang trễ ${(d.clock||0)-t.due} phút</span>`:''}</p>`;
  if(r.back!=null)body+=`<p class="dl-line">🏃 Khách hẹn về lúc <b>${x.esc(hm(r.back))}</b></p>`;
  if(r.discount)body+=`<p class="notice amber">Đã hứa bớt ${r.discount} xu: khách trả ${n.cod-r.discount} xu, túi COD hụt ${r.discount} xu (tự bù khi nộp).</p>`;
  if(r.dog==='ok')body+=`<p class="dl-line">🐕 Chó đã được giữ lại, vào giao được rồi.</p>`;
  if(r.knocks)body+=`<p class="notice amber">Đã bấm chuông ${r.knocks} lần, chưa ai mở.</p>`;
  if(r.broken_seen)body+=`<p class="notice red">Khách đồng kiểm thấy hàng hỏng và từ chối nhận.</p>`;
  if(r.expired)body+=`<p class="notice red">Khách đã hủy đơn vì chờ quá lâu.</p>`;
  const blocked=r.broken_seen||r.expired;
  body+=r.called?'<p class="dl-done">✓ Đã gọi khách</p>':`<div class="row wrap">${x.cmd('📞 Gọi khách','dl_call',{task:t.id},'',blocked)}</div>`;
  if(!blocked)body+=wishes(t,x);
  if(n.cod&&!blocked){
    const coins=u.change[t.id]||[],given=sum(coins);
    body+=`<div class="dl-cash"><p>Khách đưa <b>${n.cash} xu</b> · tiền hàng <b>${n.cod} xu</b>${r.discount?` − bớt ${r.discount} = <b>${n.cod-r.discount} xu</b>`:''}</p>
      <p class="dl-change">Tiền thối đang đếm: <b>${given} xu</b> ${coins.length?`<small>(${coins.join(' + ')})</small>`:''}</p>
      ${r.asked?'<p class="notice amber small">Khách đếm lại thấy thối thiếu: thối thêm cho đủ rồi đưa lại.</p>':''}
      ${keypad(x,'note',given,given,{task:t.id})}</div>
      <div class="row wrap">${x.cmd(`💵 Thu ${n.cash}, thối ${given} & giao`,'dl_deliver',{task:t.id,change:given},'primary big')}</div>`;
  }else if(!blocked){
    body+=`<div class="row wrap">${x.cmd('✅ Giao tận tay','dl_deliver',{task:t.id},'primary big')}
      ${n.safe_drop&&!n.cod?x.confirmCmd('📸 Gửi chòi bảo vệ','dl_safedrop',{task:t.id},'Gửi hàng ở chòi bảo vệ và chụp ảnh làm bằng chứng? Khách đã cho phép trong ghi chú.',''):''}
      ${!n.safe_drop&&!n.cod&&!n.paper?x.confirmCmd('📦 Gửi người nhận hộ','dl_safedrop',{task:t.id},'Khách chưa cho phép gửi người khác. Vẫn gửi nhận hộ và chụp ảnh?','ghost small'):''}</div>`;
  }
  if(r.knocks||blocked)body+=`<div class="row wrap">${x.confirmCmd('📝 Báo giao thất bại','dl_fail',{task:t.id},r.broken_seen?'Lập biên bản hàng hỏng? Bạn đền một phần giá trị hàng, bảo hiểm trả phần còn lại.':'Báo giao thất bại cho đơn này?','danger small')}</div>`;
  return body;
}
/** Clean layout: the deadline, when the customer is back, a promised discount, the dog, knocks, the customer's cash and
 * the price, the change counted so far, the regular's notes: all stay, in numbers and a few words. The hand-over itself
 * is the bar's button. */
function dropClean(t,x){
  const n=t.needs,r=t.run,d=x.room.data||{},u=ui(x),now=d.clock||0;
  let body='';
  const times=[t.due!=null?`⏰ <b>${x.esc(hm(t.due))}</b>${now>t.due?` · <span class="bad-text">trễ ${now-t.due}′</span>`:''}`:'',r.back!=null?`🏃 về <b>${x.esc(hm(r.back))}</b>`:''].filter(Boolean);
  if(times.length)body+=`<p class="dl-line">${times.join(' · ')}</p>`;
  if(r.discount)body+=`<p class="notice amber">🏷️ Bớt ${r.discount}: thu ${n.cod-r.discount}, túi COD hụt ${r.discount}</p>`;
  if(r.dog==='ok')body+='<p class="dl-line">🐕 Đã giữ chó</p>';
  if(r.knocks)body+=`<p class="notice amber">🔔 ×${r.knocks}, chưa ai mở</p>`;
  if(r.broken_seen)body+='<p class="notice red">❌ Hàng hỏng, khách không nhận</p>';
  if(r.expired)body+='<p class="notice red">❌ Khách đã hủy (chờ lâu)</p>';
  const blocked=r.broken_seen||r.expired;
  body+=r.called?'<p class="dl-done">✓ Đã gọi</p>':`<div class="row wrap">${x.cmd('📞 Gọi khách','dl_call',{task:t.id},'',blocked)}</div>`;
  if(!blocked)body+=wishes(t,x);
  if(n.cod&&!blocked){
    const coins=u.change[t.id]||[],given=sum(coins);
    body+=`<div class="dl-cash"><p aria-label="${x.esc(`Khách đưa ${n.cash} xu, tiền hàng ${n.cod} xu`)}">💵 đưa <b>${n.cash}</b> · hàng <b>${n.cod}</b>${r.discount?` − ${r.discount} = <b>${n.cod-r.discount}</b>`:''}</p>
      <p class="dl-change">Thối: <b>${given}</b> ${coins.length?`<small>(${coins.join(' + ')})</small>`:''}</p>
      ${r.asked?'<p class="notice amber small">⚠️ Khách đòi thối thêm</p>':''}
      ${keypad(x,'note',given,given,{task:t.id})}</div>`;
  }else if(!blocked){
    const alt=[n.safe_drop&&!n.cod?x.confirmCmd('📸 Gửi bảo vệ','dl_safedrop',{task:t.id},'Gửi hàng ở chòi bảo vệ và chụp ảnh làm bằng chứng? Khách đã cho phép trong ghi chú.',''):'',
      !n.safe_drop&&!n.cod&&!n.paper?x.confirmCmd('📦 Gửi nhận hộ','dl_safedrop',{task:t.id},'Khách chưa cho phép gửi người khác. Vẫn gửi nhận hộ và chụp ảnh?','ghost small'):''].join('');
    if(alt)body+=`<div class="row wrap">${alt}</div>`;
  }
  if(r.knocks||blocked)body+=`<div class="row wrap">${x.confirmCmd('📝 Báo thất bại','dl_fail',{task:t.id},r.broken_seen?'Lập biên bản hàng hỏng? Bạn đền một phần giá trị hàng, bảo hiểm trả phần còn lại.':'Báo giao thất bại cho đơn này?','danger small')}</div>`;
  return body;
}
function hubPanel(x,open=true){
  const d=x.room.data||{},u=ui(x),given=sum(u.settle);
  if(!(d.owed>0))return '';
  const rows=(d.cod||[]).map(r=>`<li><span>${x.esc(r.item)}</span><b>${r.cod} xu</b>${r.day<x.room.day?'<small>từ hôm trước</small>':''}</li>`).join('');
  const c=clean();
  const body=`<ul class="dl-statement">${rows}</ul>
    <p class="small muted"${c?` aria-label="Túi đang có ${d.bag} xu tiền mặt"`:''}>${c?`👜 ${d.bag}`:`Túi đang có ${d.bag} xu tiền mặt.`}</p>
    <p class="dl-change">${c?'Đếm':'Đang đếm'}: <b>${given}${c?'':' xu'}</b></p>${keypad(x,'snote',given,given)}
    <div class="row wrap">${x.confirmCmd(`Nộp ${given} xu cho kế toán`,'dl_settle',{amount:given},`Nộp ${given} xu COD cho kế toán bưu cục?`,'primary',!given)}</div>`;
  if(open||given)return `<section class="dl-sec dl-hub"><h4 class="section-title">💵 ${c?`Nộp COD · ${d.owed}`:'Nộp tiền COD'}</h4>${body}</section>`;
  return `<section class="dl-hub folded">${pane(x,`hub-${x.room.day}`,`💵 Nộp tiền COD · ${d.owed} xu`,body)}</section>`;
}
function servicePanel(x){
  const d=x.room.data||{},b=d.bike;if(!b||d.at!=='gas')return '';
  const need=b.tyre<100||b.rim;
  if(clean())return `<section class="dl-sec"><h4 class="section-title">🛞 Thay ruột</h4><p class="small">🛞 <b>${b.tyre}%</b> (xẹp &lt;${b.flat_at}%)${b.rim?' · vành móp':''}</p>
    <div class="row wrap">${x.confirmCmd(`🛞 Thay ruột · ${b.service} xu`,'dl_service',{},`Thay ruột lốp hết ${b.service} xu (mất 6 phút)?`,b.tyre<b.flat_at?'primary':'ghost',!need)}</div></section>`;
  return `<section class="dl-sec"><h4 class="section-title">🛞 Thay ruột ở cây xăng</h4><p class="small">Lốp còn <b>${b.tyre}%</b>${b.rim?' · vành móp vì chạy bánh xẹp':''}. Dưới ${b.flat_at}% là dễ xẹp bánh giữa đường.</p>
    <div class="row wrap">${x.confirmCmd(`🛞 Thay ruột, bơm lốp · ${b.service} xu`,'dl_service',{},`Thay ruột lốp hết ${b.service} xu (mất 6 phút)?`,b.tyre<b.flat_at?'primary':'ghost',!need)}</div></section>`;
}
function fuelPanel(x){
  const d=x.room.data||{},fuel=Number(d.fuel)||0,gas=d.at==='gas'&&!d.bike?.nogas,step=x.cc.fuel_step||5,price=x.cc.fuel_price||{gas:1,bottle:2};
  if(d.at==='gas'&&d.bike?.nogas&&fuel>=30)return '<p class="notice amber">🔌 Cây xăng mất điện tới 18:00, bơm chưa chạy.</p>';
  if(!gas&&fuel>=30)return '';
  const room=100-fuel,opts=(gas?[10,20,30,40,room]:[10,20]).filter((v,i,a)=>v>0&&v<=room&&v%step===0&&a.indexOf(v)===i);
  if(!opts.length)return '';
  const unit=gas?price.gas:price.bottle;
  return `<section class="dl-sec"><h4 class="section-title">${gas?'⛽ Cây xăng':'🍾 Xăng chai ven đường'}</h4>
    ${gas?'':clean()?tip('Đắt gấp đôi, tối đa 20% — chỉ để chạy tới cây xăng.','🍾 Xăng chai'):'<p class="small muted">Đắt gấp đôi, tối đa 20% — chỉ để chạy tới cây xăng.</p>'}
    <div class="row wrap">${opts.map(v=>x.confirmCmd(`+${v}% · ${v/step*unit} xu`,'dl_refuel',{amount:v},`Đổ thêm ${v}% xăng hết ${v/step*unit} xu?`,gas?'':'ghost')).join('')}</div></section>`;
}
/** `settle`: handing the COD cash in is the current step (the hub panel then opens by itself). */
function stopPanel(x,settle=true){
  const d=x.room.data||{},here=nodeOf(x,d.at),s=stopsAt(x,d.at);
  const cards=[...s.pick.map(t=>`<article class="dl-order pick">${head(t,x)}${pickupCard(t,x)}</article>`),
               ...s.drop.map(t=>`<article class="dl-order drop">${head(t,x)}${dropCard(t,x)}</article>`)].join('');
  const expired=live(x).filter(t=>t.known&&t.needs.kind==='food'&&t.run.expired&&destOf(t)!==d.at);
  if(clean()){
    const rest=`${d.at==='hub'?hubPanel(x,settle||!cards):''}${fuelPanel(x)}${servicePanel(x)}${garagePanel(x)}`;
    // An empty stop on the order's first screen: nothing to say (the order card and the bar lead).
    if(!cards&&!expired.length&&!rest.trim()&&!settle)return '';
    return `<section class="dl-sec focus"><h4 class="section-title" aria-label="${x.esc(`Đang ở ${here.name}`)}">📍 ${x.esc(here.emoji)}${cards?'':` ${x.esc(shortName(x,d.at))}`}${tip(x.esc(here.note||''),`${here.emoji} ${here.name}`)}</h4>
    ${cards}
    ${expired.map(t=>`<p class="notice red">${x.esc(t.needs.item)}: khách hủy. ${x.confirmCmd('Báo thất bại','dl_fail',{task:t.id},'Báo giao thất bại cho đơn đã bị hủy?','danger small')}</p>`).join('')}
    <div class="row wrap">${x.cmd('⏳ 5′','dl_wait',{},'ghost small')} <button type="button" class="btn ghost small" data-action="inventory" aria-label="Kho vật tư">📦</button></div></section>${rest}`;
  }
  return `<section class="dl-sec focus"><h4 class="section-title">📍 Đang ở ${x.esc(here.emoji)} ${x.esc(here.name)} <small class="muted">${x.esc(here.note||'')}</small></h4>
    ${cards||'<p class="muted">Không có đơn cần lấy hay giao ở đây.</p>'}
    ${expired.map(t=>`<p class="notice red">${x.esc(t.needs.item)}: khách đã hủy đơn. ${x.confirmCmd('Báo thất bại','dl_fail',{task:t.id},'Báo giao thất bại cho đơn đã bị hủy?','danger small')}</p>`).join('')}
    <div class="row wrap">${x.cmd('⏳ Chờ 5 phút','dl_wait',{},'ghost small')} ${x.button('📦 Kho vật tư','inventory',{},'ghost small')}</div></section>
    ${d.at==='hub'?hubPanel(x,settle||!cards):''}${fuelPanel(x)}${servicePanel(x)}${garagePanel(x)}`;
}

/* ---------- order board & checklist ---------- */
function board(x,active,folded=false){
  const rows=live(x);
  if(folded){
    const fresh=rows.filter(t=>!t.known).length;
    return `<section class="dl-board folded">${pane(x,`board-${active}`,clean()?`📱 ${rows.length}${fresh?` · 🆕 ${fresh}`:''}`:`📱 Đơn trên app (${rows.length})${fresh?` · ${fresh} đơn mới`:''}`,boardCards(x,rows,active))}</section>`;
  }
  // Clean layout, a new order open: its card alone (where from and to, the customer's words, the deadline); its
  // ✋ Nhận đơn is the bar's. The other orders wait in one line.
  const mine=clean()&&active?rows.find(t=>t.id===active&&!t.known):null;
  if(mine){
    const others=rows.filter(t=>t!==mine);
    return `<section class="dl-board dl-board-one">${boardCards(x,[mine],active,false)}${others.length?pane(x,`board-more-${active}`,`<span aria-label="${others.length} đơn khác trên app">📱 +${others.length}</span>`,boardCards(x,others,active)):''}</section>`;
  }
  return `<section class="dl-board"><h4 class="section-title">📱 Đơn trên app (${rows.length})</h4>${boardCards(x,rows,active)}</section>`;
}
/** A new order's deadline before ✋ Nhận đơn (its clock may already run): the time, or on day 1 how long after accept. */
function dueLine(x,p){
  const now=Number(x.room.data?.clock)||0;
  if(clean()){
    if(p.due!=null)return `<small class="dl-due${now>p.due?' bad-text':''}" aria-label="${x.esc(`Hẹn giao trước ${hm(p.due)}`)}">⏰ trước <b>${x.esc(hm(p.due))}</b>${now>p.due?' · quá giờ':''}</small>`;
    if(p.within)return `<small class="dl-due" aria-label="${x.esc(`Giao trong ${Number(p.within)} phút sau khi nhận`)}">⏰ ${Number(p.within)}′ sau nhận</small>`;
    return '';
  }
  if(p.due!=null)return `<small class="dl-due${now>p.due?' bad-text':''}">⏰ Hẹn giao trước <b>${x.esc(hm(p.due))}</b>${now>p.due?' · đã quá giờ hẹn':''}</small>`;
  if(p.within)return `<small class="dl-due">⏰ Giao trong ${Number(p.within)} phút sau khi nhận</small>`;
  return '';
}
function boardCards(x,rows,active,ask=true){
  const c=clean();
  return `${rows.map(t=>{
    const st=stage(t),n=t.needs,p=t.preview||{};
    const who=x.npc(t.npc);
    if(st==='new'){
      const route=c?`${x.esc(place(x,p.pickup))} → ${x.esc(place(x,p.dest))}`:`${x.esc(nodeOf(x,p.pickup).name)} → ${x.esc(nodeOf(x,p.dest).name)}`;
      const btn=ask?x.cmd('✋ Nhận đơn','ask',{task:t.id},c&&active?'full':'primary full'):'';   // a work screen's one primary is the bar's
      return `<article class="dl-card new ${t.id===active?'active':''}"><div class="row"><span class="dl-oemoji">${x.esc(p.emoji||'📦')}</span><div class="grow"><b${c?` aria-label="${x.esc(`${nodeOf(x,p.pickup).name} → ${nodeOf(x,p.dest).name}`)}"`:''}>${route}</b><small>${x.esc(who.display_name)}: “${x.esc(t.opening)}”</small>${dueLine(x,p)}</div></div>${btn}</article>`;
    }
    const label=c?{pickup:`Chờ lấy · ${place(x,n.pickup)}`,bag:`→ ${place(x,destOf(t))}`}[st]||'':{pickup:`Chờ lấy · ${nodeOf(x,n.pickup).name}`,bag:`Trên xe → ${nodeOf(x,destOf(t)).name}`}[st]||'';
    return `<article class="dl-card ${st} ${t.id===active?'active':''}"><div class="row"><span class="dl-oemoji">${x.esc(n.emoji)}</span><div class="grow"><b>${x.esc(n.item)}</b><small>${x.esc(label)}${t.due!=null?` · hẹn ${x.esc(hm(t.due))}`:''}${n.cod?` · COD ${n.cod}`:''}</small></div>${t.id===active?'':x.cmd('Xem','task_select',{task:t.id},'ghost small')}</div></article>`;
  }).join('')||'<p class="muted small">Chưa có đơn.</p>'}`;
}
/* ---------- next step: one list of steps drives the checklist, the header hint and the bottom button ---------- */
/** The biggest note that still fits: how a courier counts change. */
const nextNote=(x,rest)=>(x.cc.notes||[50,20,10,5,2,1]).find(v=>v<=rest)||1;
/** " phút" on the classic layout, "′" on the clean one. */
const mn=()=>clean()?'′':' phút';
const place=(x,id)=>`${nodeOf(x,id).emoji} ${shortName(x,id)}`;
/** Ride the planned leg, or plan one to `to` (the player's own draft first). */
function rideGo(x,to){
  const d=x.room.data||{},next=(d.route||[])[0];
  if(next){const e=(d.eta||[])[0];return {cmd:'dl_ride',payload:{way:'main'},label:`🛵 Chạy tới ${x.esc(place(x,next))}${e?` · ${e.minutes}${mn()}`:''}`};}
  if(ui(x).draft.length)return {act:'car:plan',label:'🗺️ Chốt lộ trình'};
  return {cmd:'dl_plan',payload:{route:[to]},label:`🗺️ Lên lộ trình tới ${x.esc(place(x,to))}`};
}
/** Not enough fuel for the next leg: fill up at the station, ride there, or buy a bottle. */
function fuelGo(x){
  const d=x.room.data||{},fuel=Number(d.fuel)||0,rate=Number(d.rate)||2,step=x.cc.fuel_step||5,price=x.cc.fuel_price||{gas:1,bottle:2};
  const fill=(amount,unit,label)=>({cmd:'dl_refuel',payload:{amount},confirm:`Đổ thêm ${amount}% xăng hết ${amount/step*unit} xu?`,label:`${label} · ${amount/step*unit} xu`});
  if(d.at==='gas'&&d.bike?.nogas)return {cmd:'dl_wait',payload:{},label:'⏳ Cây xăng mất điện — chờ 5 phút'};
  if(d.at==='gas')return fill(Math.floor((100-fuel)/step)*step,price.gas,'⛽ Đổ đầy bình');
  if(fuel>=dist(x,d.at,'gas')*rate+1)return (d.route||[])[0]==='gas'?rideGo(x,'gas'):{cmd:'dl_plan',payload:{route:['gas']},label:'⛽ Sắp hết xăng: lên lộ trình tới cây xăng'};
  return fill(Math.min(x.cc.bottle_max||20,Math.floor((100-fuel)/step)*step),price.bottle,'🍾 Mua xăng chai');
}
function travel(x,to){
  const d=x.room.data||{},row={ok:d.at===to?true:null,label:`Tới ${place(x,to)}`};
  if(d.at===to)return row;
  const hop=(d.route||[])[0]||to,fuel=Number(d.fuel)||0,low=fuel<dist(x,d.at,hop)*(Number(d.rate)||2)+1;
  return {...row,...driveStep(x,low?fuelGo(x):rideGo(x,to))};
}
/** The stop a ride step goes to (planned leg, a plan to make, the player's draft), else null. */
function goNode(x,go){
  const d=x.room.data||{};
  if(go?.cmd==='dl_ride')return (d.route||[])[0]||null;
  if(go?.cmd==='dl_plan')return go.payload?.route?.[0]||null;
  if(go?.act==='car:plan')return ui(x).draft[0]||null;
  return null;
}
/** A ride step: `drive` names its stop. In Tự lái the rider rides there on the street view; its button is the
 * shortcut "⏩ Đi nhanh" (the same commands as the tap flow) and nothing pulses (the stop's person waves). */
function driveStep(x,go){
  const node=goNode(x,go);
  if(!node)return {go};
  if(!driving())return {go,drive:node};
  return {go:{act:'car:quick',data:{node},label:`⏩ Đi nhanh tới ${x.esc(place(x,node))}`},drive:node,pulse:''};
}
/** Ride to `node` the way the tap flow does: plan it first if it is not the next stop, then the main road. */
async function rideTo(x,node){
  const d=x.room.data||{};
  if(!node||d.at===node)return {ok:false};
  const route=d.route||[];
  if(route[0]!==node){
    const want=[node,...route.filter(n=>n!==node)].filter((n,i,a)=>!i||n!==a[i-1]).slice(0,10);
    if(!await x.send('dl_plan',{route:want},{quiet:true}))return {ok:false};
  }
  return {ok:!!await x.send('dl_ride',{way:'main'})};
}
/** Stopped in front of a stop on the street view. The server still decides (fuel, the leg's minutes). */
async function arrive(node){
  const x=lastX;if(!x)return {ok:false};
  const d=x.room.data||{},need=dist(x,d.at,node)*(Number(d.rate)||2),can=(d.can||{}).dl_ride;
  if((Number(d.fuel)||0)<need)return {ok:false,say:'⛽ Không đủ xăng tới đây'};
  // The server's own check of the planned leg (jams, works, a worn part all cost fuel too): its words, not a refusal.
  if(node===(d.route||[])[0]&&can&&can!==true&&can.why)return {ok:false,say:can.why};
  return rideTo(x,node);
}
/** dl_signal would be refused (server can.dl_signal, docs/UI_KIT.md "Disabled with a reason"): the scooter already
 * stands at `target`, or the junction is off the leg from where the scooter is now (the latest state, not the one the
 * street view was mounted with). The light is then scenery: no request. */
function signalWhy(x,target,i,j){
  const d=x?.room?.data||{},sig=(d.can||{}).dl_signal||{};
  const off=sig[target]||sig[`${target}:${i},${j}`];
  if(off?.why)return off.why;
  if(d.at===target)return 'Chọn điểm đến trước khi lái.';
  if(!onLeg(nodes(x),d.at,target,i,j))return 'Ngã tư này ngoài chặng đang giao. Quay lại theo mũi tên nhé.';
  return '';
}
/** Stops where stopping does something: what waits there (its emoji rides in the waving person's bubble). */
function usefulStops(x){
  const d=x.room.data||{},out={};
  for(const t of live(x)){if(!t.known||t.run.outcome)continue;const at=t.run.loaded?destOf(t):t.needs.pickup;out[at]??={kind:t.run.loaded?'drop':'pick',emoji:t.needs.emoji};}
  if((Number(d.owed)||0)>0)out.hub??={kind:'hub',emoji:'💵'};
  if((Number(d.fuel)||0)<100&&!d.bike?.nogas)out.gas??={kind:'gas',emoji:'⛽'};
  if((d.bike?.parts||[]).some(p=>p.need))out.garage??={kind:'garage',emoji:'🔧'};
  return out;
}
function driveOpts(x,node){
  const d=x.room.data||{},first=!readPref(HINT_KEY);
  if(first)savePref(HINT_KEY,'1');
  // Clean layout: the goal by its short name and the distance alone (terse); the street view itself is unchanged.
  const c=clean();
  return {nodes:nodes(x),at:d.at,target:node,useful:usefulStops(x),fuel:d.fuel,weather:d.weather,driveFactor:d.drive_factor||1,signs:d.road?.signs||[],
    terse:c,label:c?id=>shortName(x,id):null,
    minute:x.room.day_clock?.minute??17*60+(Number(d.clock)||0),first,arrive,now:()=>lastX?.now?.()||x.now(),
    signal:(i,j,axis)=>signalWhy(lastX,node,i,j)?Promise.resolve(null):lastX?.send('dl_signal',{target:node,i,j,axis},{quiet:true}),
    cross:token=>lastX?.room?.data?.at===node?Promise.resolve(null):lastX?.send('dl_cross',{target:node,token},{quiet:true}),
    slow:()=>{savePref(MODE_KEY,'fast');lastX?.toast?.('📱 Máy hơi chậm: đã chuyển sang ⏩ Đi nhanh. Bấm 🛵 Tự lái để thử lại.');lastX?.render();},
    fail:()=>{drvOff=true;lastX?.render();}};
}
/** After every render: the street view into its slot (or its frames stopped when there is no leg to ride). */
function driveTick(root,x){
  lastX=x;
  const slot=root.querySelector('[data-dl-drive]');
  if(!slot){drv?.park();return;}
  if(!drv){
    drvLoad??=import('./delivery_drive.js').then(m=>{drv=m;const s=document.querySelector('#sheet[open] [data-dl-drive]');if(s&&lastX)drv.mount(s,driveOpts(lastX,s.dataset.dlDrive));})
      .catch(error=>{console.warn('Tự lái chưa tải được',error);drvOff=true;drvLoad=null;lastX?.render();});
    return;
  }
  drv.mount(slot,driveOpts(x,slot.dataset.dlDrive));
}
/** Clean layout: the sheet header names the order by its emoji and where it goes ("👗 → 🏢 Mây Xanh"), not the whole
 * "Bưu cục Mây Chiều → Chung cư Mây Xanh" (app.js shortens only the street-kit and desk titles). The full title stays
 * in title= and aria-label. A local stand-in for app.js header's 4-word title. */
function shortHead(root,x){
  if(!clean())return;
  const h=root.closest('dialog')?.querySelector('.sheet-head h2');if(!h)return;
  const full=h.getAttribute('title')||h.textContent||'',m=/^(\S+)\s.*→\s*(.+)$/u.exec(full.trim());if(!m)return;
  const id=Object.keys(nodes(x)).find(k=>nodeOf(x,k).name===m[2].trim()||t(nodeOf(x,k).name)===m[2].trim());if(!id)return;
  const s=`${m[1]} → ${place(x,id)}`;
  if(h.textContent!==s){h.textContent=s;h.setAttribute('aria-label',full);}
}
function modeSwitch(x){
  const on=driving();
  return `<div class="dl-mode" role="group" aria-label="Cách chạy xe"><button type="button" class="dl-mode-b${on?' on':''}" data-action="car:mode" data-mode="drive" aria-pressed="${on}">🛵 Tự lái</button><button type="button" class="dl-mode-b${on?'':' on'}" data-action="car:mode" data-mode="fast" aria-pressed="${!on}">⏩ Đi nhanh</button></div>`;
}
function driveSec(x,node){
  return `<section class="dl-drive" aria-label="Tự lái tới ${x.esc(nodeOf(x,node).name)}"><div class="dl-drive-slot" data-morph-static data-dl-drive="${x.esc(node)}"></div>${modeSwitch(x)}</section>`;
}
/** Hand the COD cash in at the hub: count what the statement says, then give it to the accountant. */
function settleSteps(x){
  const d=x.room.data||{},owed=Number(d.owed)||0,given=sum(ui(x).settle),here=d.at==='hub';
  if(!(owed>0))return [];
  let go=null,pulse='';
  if(here&&given>owed)go={act:'car:snoteClear',label:'↺ Đếm lại tiền nộp'};
  else if(here&&given<owed){const v=nextNote(x,owed-given);go={act:'car:snote',data:{v},label:clean()?`➕ Đếm tờ ${v} · ${given}/${owed}`:`➕ Đếm thêm tờ ${v} xu · ${given}/${owed}`};pulse=`.dl-hub [data-action="car:snote"][data-v="${v}"]`;}
  return [{ok:given===owed?true:given>owed?false:null,label:`Đếm đủ ${owed} xu COD theo bảng kê`,note:given&&!here?`đang đếm ${given} xu`:'',go,pulse},
    {ok:null,label:'Nộp tiền cho kế toán',go:here&&given===owed?{cmd:'dl_settle',payload:{amount:given},confirm:`Nộp ${given} xu COD cho kế toán bưu cục?`,label:clean()?`💵 Nộp ${given} xu`:`💵 Nộp ${given} xu cho kế toán`}:null}];
}
function packWant(t,x){
  const n=t.needs,r=t.run,rain=x.room.data?.weather==='rain';
  return [...(n.fragile?['bubble']:[]),...(r.seam?['tape']:[]),...(rain?['rainbag']:[]),...(n.cold?['coldpack']:[]),...(n.size==='L'?['strap']:[])];
}
function pickupSteps(t,x,S){
  const n=t.needs,r=t.run,d=x.room.data||{},u=ui(x),here=d.at===n.pickup,limit=Number(d.limit)||200;
  S.push(travel(x,n.pickup));
  if(n.kind==='food'){
    const wait=(d.clock||0)<t.ready;
    if(wait)S.push({ok:null,label:`Chờ quán làm món (xong ${hm(t.ready)})`,go:here?{cmd:'dl_wait',payload:{},label:`⏳ Chờ quán 5${mn()} · xong ${hm(t.ready)}`}:null});
    S.push({ok:r.checked?true:null,label:'So túi với bill',note:r.missing?`bổ sung ${r.missing}`:'',go:here&&!wait?{cmd:'dl_check',payload:{task:t.id},label:'🧾 So túi với bill'}:null});
    S.push({ok:null,label:'Nhận món lên thùng',go:here&&!wait?{cmd:'dl_load',payload:{task:t.id},label:'🛵 Nhận món lên thùng'}:null});
    return S;
  }
  S.push({ok:r.checked?true:null,label:'Cân & kiểm hàng',note:r.checked?kg(r.w):'',go:here?{cmd:'dl_check',payload:{task:t.id},label:'⚖️ Cân & kiểm hàng'}:null});
  if(r.checked){
    const inv=x.room.inventory||{},strap=!(inv.locked||[]).includes('strap')&&(inv.stock?.strap??0)>0;
    const heavy=r.w>limit,noStrap=n.size==='L'&&!r.packed.includes('strap')&&!strap;
    if(heavy||noStrap){
      S.push({ok:null,label:heavy?`Nặng ${kg(r.w)}, quá tải xe máy: từ chối nhận`:'Hàng cồng kềnh, không có dây ràng: từ chối nhận',
        go:{cmd:'dl_refuse',payload:{task:t.id},confirm:heavy?`Hàng ${kg(r.w)} vượt tải ${kg(limit)} của xe máy. Từ chối và báo bưu cục chuyển xe tải?`:'Hàng cồng kềnh mà không có dây ràng. Từ chối nhận?',label:'🚫 Từ chối nhận'}});
      return S;
    }
    if(r.w!==n.w)S.push({ok:u.report[t.id]?true:null,label:'Báo lệch cân lên app',note:`shop khai ${kg(n.w)}`,go:{act:'car:report',data:{task:t.id},label:'☑ Báo lệch cân lên app'}});
  }
  for(const id of packWant(t,x)){
    const it=itemOf(x,id),q=x.room.inventory?.stock?.[id]??0,done=r.packed.includes(id);
    S.push({ok:done?true:null,label:`Gói: ${it.name}`,go:!here||done?null:q?{cmd:'dl_pack',payload:{task:t.id,item:id},label:`${x.esc(it.emoji)} Dùng ${x.esc(it.name.toLowerCase())}`}:{act:'inventory',label:`📦 Hết ${x.esc(it.name.toLowerCase())}: mở kho vật tư`}});
  }
  S.push({ok:null,label:'Nhận hàng lên xe',go:here&&r.checked?{cmd:'dl_load',payload:{task:t.id,report:!!u.report[t.id]},label:'🛵 Nhận hàng lên xe'}:null});
  return S;
}
function dropSteps(t,x,S){
  const n=t.needs,r=t.run,d=x.room.data||{},u=ui(x),dest=destOf(t),here=d.at===dest,first=firstTime(x);
  const owed=Number(d.owed)||0,cap=Number(d.cap)||250,full=n.cod&&owed+n.cod>cap;
  S.push({ok:true,label:n.kind==='food'?'Món lên thùng':'Hàng lên xe'});
  const notes=(d.book||[]).find(b=>b.npc===t.npc)?.notes||[];
  if(n.unit_missing||r.knocks||notes.some(o=>o.kind==='call'))
    S.push({ok:r.called?true:null,label:n.unit_missing?'Gọi khách hỏi số phòng':'Gọi khách trước khi tới',note:r.unit||(r.back!=null?`khách về lúc ${hm(r.back)}`:''),go:{cmd:'dl_call',payload:{task:t.id},label:'📞 Gọi khách'}});
  // The COD bag is full: hand the cash in at the hub before collecting more.
  if(full)S.push({...travel(x,'hub'),label:`Về ${place(x,'hub')} nộp COD (túi đầy)`},...settleSteps(x));
  S.push(travel(x,dest));
  const kinds=x.cc.care_kinds||{};
  for(const o of notes)if(kinds[o.kind])S.push({ok:r.care.includes(o.kind)?true:null,label:`${kinds[o.kind].label} (khách dặn)`,go:here&&!r.care.includes(o.kind)?{cmd:'dl_care',payload:{task:t.id,kind:o.kind},label:`${KIND_EMOJI[o.kind]} ${x.esc(kinds[o.kind].label)}`}:null});
  let given=0;
  if(n.cod){
    const pays=n.cod-(r.discount||0),right=n.cash-pays;given=sum(u.change[t.id]||[]);
    let go=null,pulse='';
    if(here&&first&&given>right)go={act:'car:noteClear',data:{task:t.id},label:'↺ Đếm lại tiền thối'};
    else if(here&&first&&given<right){const v=nextNote(x,right-given);go={act:'car:note',data:{task:t.id,v},label:clean()?`➕ Thối tờ ${v} · ${given}/${right}`:`➕ Thối thêm tờ ${v} xu · ${given}/${right}`};pulse=`.dl-cash [data-action="car:note"][data-v="${v}"]`;}
    else if(here&&!first&&!given)go={sel:'.dl-cash .dl-keypad .dl-note'};
    S.push({ok:first||r.asked?(given===right?true:given>right?false:null):(given?true:null),
      label:first?`Thối lại ${right} xu (khách đưa ${n.cash}, hàng ${pays})`:`Đếm tiền thối (khách đưa ${n.cash}, hàng ${pays})`,note:r.asked&&given<right?'khách đòi thối thêm':given&&!first?`đang đếm ${given} xu`:'',go,pulse});
  }
  const stairs=(x.cc.stairs||{})[dest]||0;
  if(here&&r.back!=null&&(d.clock||0)+stairs<r.back)
    S.push({ok:null,label:`Chờ khách về (hẹn ${hm(r.back)})`,go:{cmd:'dl_wait',payload:{},label:`⏳ Chờ khách 5${mn()} · hẹn ${hm(r.back)}`}});
  const final={label:n.cod?`💵 Thu ${n.cash}, thối ${given} & giao`:'✅ Giao tận tay',alt:clean()?(n.cod?'💵 giao luôn':'✅ giao luôn'):'',go:finalGo(S,'dl_deliver',n.cod?{task:t.id,change:given}:{task:t.id}),ready:here&&!full,why:here?'':`tới ${nodeOf(x,dest).name}`};
  return {steps:S,final};
}
const FAIL_ASK='Báo giao thất bại cho đơn này?';
/** {steps, final} for the active order. */
function guide(t,x){
  const d=x.room.data||{};
  if(d.desk?.ev)return {steps:[{ok:null,label:'Chọn cách xử lý chuyện dọc đường',go:{sel:'.dl-opts .dl-opt'}}]};
  if(!t.known)return {steps:[{ok:null,label:'Nhận đơn trên app',go:{cmd:'ask',payload:{task:t.id},label:'✋ Nhận đơn'}}]};
  const n=t.needs,r=t.run,S=[{ok:true,label:'Nhận đơn'}];
  if(r.outcome)return {steps:S};
  const fail=label=>({ok:null,label,go:{cmd:'dl_fail',payload:{task:t.id},confirm:FAIL_ASK,label:'📝 Báo giao thất bại'}});
  if(r.expired||n.kind==='food'&&t.due!=null&&(d.clock||0)>t.due+(x.cc.grace||25))return {steps:[...S,fail('Khách đã hủy vì chờ quá lâu')]};
  if(r.broken_seen)return {steps:[...S,fail('Hàng hỏng, khách không nhận: lập biên bản')]};
  if(!r.loaded)return {steps:pickupSteps(t,x,S)};
  return dropSteps(t,x,S);
}
/** Bottom bar: the next step as one big button. */
/** The shared bar (ui-kit actBar via guide.js stepBar): the next step's button on the right, the finish early (or a
 * pointer) on the left. */
function bar(t,x,g){
  // Every screen has a step to do; this only shows if something unexpected leaves none.
  const final=g.final||{label:'📍 Xem điểm dừng',go:{sel:'.dl-sec.focus'},ready:!pending(g.steps)?.go};
  const ride=pending(g.steps)?.drive&&driving();   // Tự lái: the button is only the shortcut, the street view leads
  return stepBar(x,g.steps,final,{cls:'dl-bar',style:ride?'ghost big':undefined});
}
function hintFor(t,x,g){
  const f=g.final&&g.final.ready!==false?{label:g.final.label.replace(/^[^\p{L}\d]+/u,''),go:g.final.go}:null;
  const n=pending(g.steps),steps=n?.drive&&driving()?g.steps.map(s=>s===n?{...s,go:{act:'car:look',label:`🛵 Lái tới ${x.esc(place(x,n.drive))}`}}:s):g.steps;
  return nextHint(x,steps,{final:f});
}

export default {
  id:'delivery',
  css:true,
  next(t,x){
    try{const n=x&&pending(guide(t,x).steps);if(n)return x.esc(n.drive&&driving()?`🛵 Lái tới ${place(x,n.drive)}`:stepLine(n));}catch{/* fall back to the fixed lines */}
    if(!t.known)return 'Nhận đơn trên app';
    const r=t.run,n=t.needs;
    if(r.outcome)return 'Đơn đã xong';
    if(!r.loaded){
      if(n.kind==='parcel'&&!r.checked)return 'Tới điểm lấy, cân & kiểm hàng';
      return n.kind==='food'?'Tới quán, chờ món, so bill rồi nhận':'Đóng gói đúng loại và nhận lên xe';
    }
    if(n.unit_missing&&!r.unit)return 'Gọi khách hỏi số phòng';
    if(r.dest)return `Giao tới địa chỉ mới`;
    return n.cod?'Tới nơi, thối tiền đúng và giao':'Tới nơi và giao hàng';
  },
  // The control for the current step comes first (the door hand-over, the scale, the two ways to
  // ride, or the planner); everything else is one closed line (route, app board, the day).
  job(t,x){
    const g=guide(t,x),hint=hintFor(t,x,g);
    if(x.room.data?.desk?.ev)return `<div class="career-job dl">${hint}${status(x)}${deskCard(x)}</div>`;
    const phase=t.known?phaseOf(g):'stop',n=pending(g.steps),go=n?.go||{},dn=t.known&&n?.drive||null,route=routeSec(x,phase,t.id,dn);
    const stop=stopPanel(x,go.cmd==='dl_settle'||/^car:snote/.test(go.act||''));
    // Clean layout: a new order's screen is the order and its ✋ (the route and the day come with the next step); the
    // order's checklist is a header chip.
    const c=clean(),main=c&&!t.known?stop:`${phase==='stop'?stop+route:route+stop}${careSection(x)}`;
    const side=t.known?`<aside class="wb-side">${stepRows(x,g.steps,'Việc của đơn',{chip:c})}${board(x,t.id,true)}</aside>`:'';
    return `<div class="career-job dl">${hint}${dn&&driving()?driveSec(x,dn):''}${status(x)}${t.known?'':board(x,t.id)}${deskCard(x)}${main.trim()||side?`<div class="workbench"><section class="wb-main">
      ${main}
    </section>${side}</div>`:''}${bar(t,x,g)}</div>`;
  },
  // Between orders: new orders first, then this stop (hand in COD cash, refuel), the route folded.
  idle(x){
    if(x.room.data?.desk?.ev)return `<div class="career-job dl">${status(x)}${deskCard(x)}</div>`;
    return `<div class="career-job dl">${status(x)}<button type="button" class="ghost small" data-action="jrView" data-view="courier">🛵 Sổ shipper</button>${deskCard(x)}${board(x,null)}<div class="workbench"><section class="wb-main">
      ${stopPanel(x)}${routeSec(x,(x.room.data?.route||[]).length?'ride':'stop','idle')}${careSection(x,'today-idle')}
    </section></div></div>`;
  },
  actions:{
    async quick(data,el,x){await rideTo(x,data.node);},
    async look(data,el,x){const c=document.querySelector('#sheet[open] .dd-cv');c?.scrollIntoView?.({block:'nearest',behavior:'smooth'});c?.focus?.({preventScroll:true});},
    async mode(data,el,x){const on=data.mode==='drive';savePref(MODE_KEY,on?'drive':'fast');if(on){drvOff=false;drv?.again();}else drv?.park();x.render();},
    async stop(data,el,x){const u=ui(x);if(u.draft.length<10&&u.draft[u.draft.length-1]!==data.node)u.draft.push(data.node);x.render();},
    async undo(data,el,x){ui(x).draft.pop();x.render();},
    async clear(data,el,x){ui(x).draft=[];x.render();},
    async plan(data,el,x){
      const u=ui(x),d=x.room.data||{},route=[...(d.route||[]),...u.draft];
      if(!route.length)return;
      const ok=await x.send('dl_plan',{route});
      if(ok){u.draft=[];x.render();}
    },
    async report(data,el,x){const u=ui(x);u.report[data.task]=!u.report[data.task];x.render();},
    async note(data,el,x){const u=ui(x);(u.change[data.task]??=[]).push(Number(data.v));x.render();},
    async noteClear(data,el,x){ui(x).change[data.task]=[];x.render();},
    async snote(data,el,x){ui(x).settle.push(Number(data.v));x.render();},
    async snoteClear(data,el,x){ui(x).settle=[];x.render();},
    async seen(data,el,x){ui(x).seen=data.key;x.render();},
    // <details> toggles natively before this runs; just remember the state for the next render.
    async fold(data,el,x){const u=ui(x);(u.open??={})[data.key]=!!el.closest('details')?.open;},
    async pane(data,el,x){(ui(x).pane??={})[data.key]=data.open!=='1';x.render();},
    async fix(data,el,x){const u=ui(x),f=u.fix||[];u.fix=f.includes(data.part)?f.filter(p=>p!==data.part):[...f,data.part];x.render();},
  },
  // The sticky next-step bar rides above the sheet's own sticky footer.
  tick(root,x){keepBarAboveFooter(root);shortHead(root,x);try{driveTick(root,x);}catch(error){console.error(error);}},
  // Day summary: "Ngày mai" first (tomorrow's road, fuel, a worn part, supplies), one way to the supplies, the day's
  // figures folded.
  summary(data,x){
    if(!data||data.delivered==null)return '';
    const d=x.room.data||{},lines=Array.isArray(data.lines)?data.lines:[],fc=lines.find(l=>typeof l==='string'&&l.startsWith('📡'));
    const fuel=Number(d.fuel??data.fuel),worn=(d.bike?.parts||[]).filter(p=>partState(p));
    const plan=[fc?x.esc(fc):'',
      Number.isFinite(fuel)&&fuel<35?`⛽ Xăng còn ${fuel}%: ghé cây xăng trước khi nhận đơn`:'',
      worn.length?`<span>🔧 Ghé tiệm Chú Bảy:</span> ${worn.map(p=>`<span class="pk-it">${x.esc(p.name)} <b>${p.value}%</b></span>`).join(' · ')}`:'',
      ...stockLines(x)];
    const rows=[['Đơn đã giao',data.delivered],['Giao thất bại',data.failed],['Đơn đã từ chối nhận',data.refused],['Đơn đồ ăn bị hủy',data.food_cancelled],
      ['Quãng đường (ô phố)',data.km],['Phí giao (xu)',data.fees],['Xăng còn (%)',data.fuel],['COD tự nộp cuối ca (xu)',data.settled_at_close]];
    return planBox(x,{lines:plan,go:['📦 Mở kho vật tư','inventory'],
      more:[`🛵 Hôm nay · ${data.delivered} đơn · ${data.fees||0} xu phí giao`,figures(x,rows,lines.filter(l=>l!==fc))]});
  },
  dock:[['inventory','box','Vật tư','Xốp, keo, túi mưa']],
};
