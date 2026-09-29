/** Giao Nhanh Mây Chiều — courier dashboard (plugin career UI).
 * The server owns the clock, fuel, fees and COD; this view only builds a draft
 * route, a change-count and a settlement count before sending them. */
import {t,language} from '../v4/i18n.js';
import {reqList} from '../ui-kit.js';
import {stepRows,nextHint,stepCta,finalGo,pending,firstTime} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';

const CELL=60,PAD=30;
/** "Cỏ May Office Tower" → "Office Tower"; "Bồ Câu School" → "School". */
const enLabel=name=>{
  const w=name.split(' '),viet=s=>/[^\x00-\x7F]/.test(s);
  return w.length>1&&viet(w[w.length-2])&&!viet(w[w.length-1])?w[w.length-1]:w.slice(-2).join(' ');
};
const DONE=['completed','referred','cancelled'];
const PACK_TAG={bubble:'fragile',rainbag:'rain',coldpack:'cold',strap:'size'};

const nodes=x=>x.cc.nodes||{};
const nodeOf=(x,id)=>nodes(x)[id]||{name:id,emoji:'📍',x:0,y:0};
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
  return `<div class="dl-status" role="status">
    <div class="dl-clock"><span aria-hidden="true">🕔</span><b>${x.esc(hm(d.clock))}</b><small>${wx[0]} ${wx[1]} · ${x.esc(wx[2])}</small></div>
    ${meter('⛽ Xăng',`${fuel}%`,fuel,fuel<20?'bad':fuel<35?'warn':'')}
    ${meter('📦 Tải',`${kg(load)} / ${kg(limit)}`,load/limit*100,load>limit*.8?'warn':'')}
    ${meter('💵 Túi COD',`${d.owed||0} / ${cap} xu`,(d.owed||0)/cap*100,(d.owed||0)>cap*.7?'warn':'')}
    ${bikeMeter(x,meter)}
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
function careSection(x){
  return `<section class="dl-care" aria-label="Chăm xe và khách quen">${bikeFold(x)}${bookFold(x)}</section>`;
}
function wishes(t,x){
  const b=(x.room.data?.book||[]).find(e=>e.npc===t.npc);if(!b||!b.notes.length)return '';
  const r=t.run,care=r.care||[],kinds=x.cc.care_kinds||{};
  const rows=b.notes.map(n=>{const done=n.kind==='call'?r.called:n.kind==='gate'?true:care.includes(n.kind);
    return {ok:done?true:null,icon:KIND_EMOJI[n.kind]||'📝',label:n.text,note:n.kind==='gate'?'tự áp dụng khi tới cổng':done?'đã làm':n.kind==='call'?'bấm “Gọi khách”':''};});
  const btns=b.notes.filter(n=>kinds[n.kind]&&!care.includes(n.kind)).map(n=>x.cmd(`${KIND_EMOJI[n.kind]} ${kinds[n.kind].label} · +${kinds[n.kind].minutes} phút`,'dl_care',{task:t.id,kind:n.kind},'ghost')).join('');
  return `<div class="dl-wish"><p class="dl-sub">📒 ${x.esc(b.name)} từng dặn</p>${reqList(rows,x.esc,'Lời dặn của khách quen')}${btns?`<div class="row wrap space-top">${btns}</div>`:''}</div>`;
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
function lPath(x,from,route){
  const pts=[];let cur=nodeOf(x,from);pts.push([cur.x,cur.y]);
  for(const id of route){const n=nodeOf(x,id);pts.push([n.x,cur.y]);pts.push([n.x,n.y]);cur=n;}
  return pts.map(([a,b])=>`${PAD+a*CELL},${PAD+b*CELL}`).join(' ');
}
function map(x){
  const d=x.room.data||{},u=ui(x),all=nodes(x),W=PAD*2+6*CELL,H=PAD*2+4*CELL+16;
  const streets=[...Array(7).keys()].map(i=>`<line x1="${PAD+i*CELL}" y1="${PAD}" x2="${PAD+i*CELL}" y2="${H-PAD}"/>`).join('')+[...Array(5).keys()].map(i=>`<line x1="${PAD}" y1="${PAD+i*CELL}" x2="${W-PAD}" y2="${PAD+i*CELL}"/>`).join('');
  const marks=Object.entries(all).map(([id,n])=>{
    const s=stopsAt(x,id),cls=[s.pick.length?'pick':'',s.drop.length?'drop':'',id===d.at?'here':''].join(' ');
    const sign=(d.road?.signs||[]).find(g=>g.node===id),hz=sign?{jam:'🚦',works:'🚧',flood:'🌊'}[sign.kind]||'':'';
    // Short map label: the kind of place ("Chung cư" / "Apartments"), which
    // comes first in Vietnamese and last in English.
    const label=language()==='en'?enLabel(t(n.name)):n.name.split(' ').slice(0,2).join(' ');
    return `<g class="dl-node ${cls}" transform="translate(${PAD+n.x*CELL},${PAD+n.y*CELL})"><circle r="17"/><text class="e" y="6">${x.esc(n.emoji)}</text><text class="l" y="31" data-no-translate>${x.esc(label)}</text>${s.pick.length||s.drop.length?`<text class="n" x="15" y="-12">${s.pick.length+s.drop.length}</text>`:''}${hz?`<text class="h" x="-24" y="-10">${hz}</text>`:''}</g>`;
  }).join('');
  const here=nodeOf(x,d.at);
  const planned=(d.route||[]).length?`<polyline class="dl-route" points="${lPath(x,d.at,d.route)}"/>`:'';
  const draftFrom=(d.route||[]).length?d.route[d.route.length-1]:d.at;
  const draft=u.draft.length?`<polyline class="dl-draft" points="${lPath(x,draftFrom,u.draft)}"/>`:'';
  return `<figure class="dl-map"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Bản đồ khu phố: bạn đang ở ${x.esc(here.name)}"><g class="dl-streets">${streets}</g>${planned}${draft}${marks}<text class="dl-rider" x="${PAD+here.x*CELL-24}" y="${PAD+here.y*CELL-16}">🛵</text></svg>
    <figcaption class="small muted"><span class="dl-key pick"></span> có hàng cần lấy · <span class="dl-key drop"></span> có hàng cần giao · mỗi ô phố ${x.esc(d.mpu)} phút</figcaption></figure>`;
}

/* ---------- route planner ---------- */
function planner(x){
  const d=x.room.data||{},u=ui(x),all=nodes(x),mpu=Number(d.mpu)||3,rate=Number(d.rate)||2;
  const planned=d.route||[],eta=d.eta||[];
  let body='';
  if(planned.length){
    const next=eta[0]||{node:planned[0],blocks:dist(x,d.at,planned[0]),minutes:dist(x,d.at,planned[0])*mpu,at:(d.clock||0)+dist(x,d.at,planned[0])*mpu,fuel:(d.fuel||0)-dist(x,d.at,planned[0])*rate,notes:[]};
    body+=`<ol class="dl-eta">${eta.map((r,i)=>`<li class="${r.fuel<0?'bad':''}"><span>${i+1}</span><b>${x.esc(nodeOf(x,r.node).emoji)} ${x.esc(nodeOf(x,r.node).name)}</b><small>${x.esc(hm(r.at))} · ${r.blocks} ô · xăng còn ${r.fuel}%${(r.notes||[]).length?' · '+x.esc(r.notes.join(', ')):''}</small></li>`).join('')}</ol>`+rideChoice(x,next);
  }
  const from=u.draft.length?u.draft[u.draft.length-1]:(planned.length?planned[planned.length-1]:d.at);
  let clock=planned.length&&eta.length?eta[eta.length-1].at:(d.clock||0),fuel=planned.length&&eta.length?eta[eta.length-1].fuel:(d.fuel||0),prev=planned.length?planned[planned.length-1]:d.at;
  const draftRows=u.draft.map((id,i)=>{const b=dist(x,prev,id);clock+=b*mpu;fuel-=b*rate;prev=id;return `<li class="${fuel<0?'bad':''}"><span>${planned.length+i+1}</span><b>${x.esc(nodeOf(x,id).emoji)} ${x.esc(nodeOf(x,id).name)}</b><small>~${x.esc(hm(clock))} · ${b} ô · xăng ~${fuel}%</small></li>`;}).join('');
  const tiles=Object.entries(all).map(([id,n])=>{
    const s=stopsAt(x,id),b=dist(x,from,id),bits=[];
    if(s.pick.length)bits.push(`lấy ${s.pick.length}`);
    if(s.drop.length)bits.push(`giao ${s.drop.length}`);
    if(id==='hub'&&(d.owed||0)>0)bits.push('nộp COD');
    if(id==='gas')bits.push('đổ xăng');
    if(id==='garage'&&d.bike?.alert)bits.push('sửa xe');
    const hot=s.pick.length||s.drop.length||(id==='hub'&&(d.owed||0)>0)||(id==='garage'&&d.bike?.alert);
    return tile(x,{emoji:n.emoji,label:n.name,sub:`${b} ô · ${b*mpu} phút${bits.length?' · '+bits.join(', '):''}`,cls:`${hot?'hot':''} ${id===from?'here':''}`,attr:carAttr(x,'stop',{node:id}),off:id===from});
  }).join('');
  const sameAsPlan=!u.draft.length;
  return `${body}
    <p class="dl-sub">${planned.length?'Thêm điểm sau tuyến đang chạy':'Chọn điểm dừng theo thứ tự'}</p>
    ${u.draft.length?`<ol class="dl-eta draft">${draftRows}</ol>`:''}
    <div class="row wrap">
      <button type="button" class="btn primary" ${carAttr(x,'plan')} ${sameAsPlan?'disabled':''}>🗺️ Chốt lộ trình</button>
      <button type="button" class="btn ghost small" ${carAttr(x,'undo')} ${u.draft.length?'':'disabled'}>↶ Bỏ điểm cuối</button>
      <button type="button" class="btn ghost small" ${carAttr(x,'clear')} ${u.draft.length?'':'disabled'}>✕ Xóa nháp</button>
    </div>
    <div class="dl-grid stops">${tiles}</div>`;
}

function rideChoice(x,next){
  const name=x.esc(nodeOf(x,next.node).name),alt=next.short,soup=live(x).some(t=>t.known&&t.run.loaded&&t.needs.soup&&!t.run.spilled);
  const main=`<button type="button" class="btn primary big dl-way" ${cmdAttr(x,'dl_ride',{way:'main'})}><span>🛣️ Đường chính tới ${name}</span><small>${next.minutes??next.blocks*(x.room.data?.mpu||3)} phút · ${next.blocks} ô${(next.notes||[]).length?' · '+x.esc(next.notes.join(', ')):''}</small></button>`;
  if(!alt)return `<div class="dl-ways">${main}</div>`;
  if(alt.brake)return `<div class="dl-ways">${main}<button type="button" class="btn ghost dl-way" disabled><span>🏍️ Hẻm tắt</span><small>🛑 Má phanh mòn — hẻm dốc không an toàn. Thay ở tiệm Chú Bảy.</small></button></div>`;
  const bumpy=!alt.smooth,warn=[...(alt.notes||[]),...(soup&&bumpy?['đổ nước lèo trên xe']:[]),...(bumpy?['lốp mòn gấp đôi']:[])];
  return `<div class="dl-ways">${main}<button type="button" class="btn ghost dl-way ${alt.stall||soup&&bumpy?'risky':''} ${alt.smooth?'known':''}" ${cmdAttr(x,'dl_ride',{way:'short'})}><span>🏍️ Hẻm tắt</span><small>${alt.minutes} phút · ${alt.blocks} ô · ${x.esc(warn.join(', '))}</small></button></div>`;
}

/* ---------- orders at the current stop ---------- */
function head(t,x){
  const n=t.needs,who=x.npc(t.npc);
  return `<div class="dl-ohead"><span class="dl-oemoji" aria-hidden="true">${x.esc(n.emoji)}</span><div class="grow"><b>${x.esc(n.item)}</b><small>${x.esc(who.display_name)} · ${x.esc(n.address)}${t.run.unit?` · <strong>${x.esc(t.run.unit)}</strong>`:''}</small><div class="dl-tags">${tags(t,x)}</div></div></div>`;
}
function packTiles(t,x){
  const r=t.run,inv=x.room.inventory||{stock:{},locked:[]};
  return `<div class="dl-grid pack">${items(x).map(i=>{
    const used=r.packed.includes(i.id),locked=(inv.locked||[]).includes(i.id),q=inv.stock?.[i.id]??0;
    const off=used||locked||!q||(r.loaded&&i.id!=='rainbag');
    return tile(x,{emoji:i.emoji,label:i.name,sub:used?'✓ đã dùng':locked?`🔒 cấp ${i.unlock}`:`còn ${q} ${i.unit||''}`,cls:`${used?'selected':''} ${locked?'locked':''} ${!q&&!used?'empty':''}`,attr:cmdAttr(x,'dl_pack',{task:t.id,item:i.id}),off});
  }).join('')}</div>`;
}
function pickupCard(t,x){
  const n=t.needs,r=t.run,d=x.room.data||{},u=ui(x),limit=Number(d.limit)||200;
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
  body+=`<div class="row wrap">${x.cmd(r.checked?'✓ Đã cân & kiểm':'⚖️ Cân & kiểm hàng','dl_check',{task:t.id},r.checked?'ghost':'primary',r.checked)}</div>`;
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
function keypad(x,action,key,total,extra={}){
  const notes=x.cc.notes||[50,20,10,5,2,1];
  return `<div class="dl-keypad">${notes.map(v=>`<button type="button" class="btn dl-note" ${carAttr(x,action,{...extra,v})}>${v}</button>`).join('')}
    <button type="button" class="btn ghost dl-note" ${carAttr(x,action+'Clear',extra)} ${total?'':'disabled'}>Đếm lại</button></div>`;
}
function dropCard(t,x){
  const n=t.needs,r=t.run,d=x.room.data||{},u=ui(x);
  let body='';
  if(t.due!=null)body+=`<p class="dl-line">⏰ Hẹn trước <b>${x.esc(hm(t.due))}</b>${(d.clock||0)>t.due?` · <span class="bad-text">đang trễ ${(d.clock||0)-t.due} phút</span>`:''}</p>`;
  if(r.back!=null)body+=`<p class="dl-line">🏃 Khách hẹn về lúc <b>${x.esc(hm(r.back))}</b></p>`;
  if(r.discount)body+=`<p class="notice amber">Đã hứa bớt ${r.discount} xu: khách trả ${n.cod-r.discount} xu, túi COD hụt ${r.discount} xu (tự bù khi nộp).</p>`;
  if(r.dog==='ok')body+=`<p class="dl-line">🐕 Chó đã được giữ lại, vào giao được rồi.</p>`;
  if(r.knocks)body+=`<p class="notice amber">Đã bấm chuông ${r.knocks} lần, chưa ai mở.</p>`;
  if(r.broken_seen)body+=`<p class="notice red">Khách đồng kiểm thấy hàng hỏng và từ chối nhận.</p>`;
  if(r.expired)body+=`<p class="notice red">Khách đã hủy đơn vì chờ quá lâu.</p>`;
  const blocked=r.broken_seen||r.expired;
  body+=`<div class="row wrap">${x.cmd(r.called?'✓ Đã gọi khách':'📞 Gọi khách','dl_call',{task:t.id},r.called?'ghost':'',r.called||blocked)}</div>`;
  if(!blocked)body+=wishes(t,x);
  if(n.cod&&!blocked){
    const coins=u.change[t.id]||[],given=sum(coins);
    body+=`<div class="dl-cash"><p>Khách đưa <b>${n.cash} xu</b> · tiền hàng <b>${n.cod} xu</b></p>
      <p class="dl-change">Tiền thối đang đếm: <b>${given} xu</b> ${coins.length?`<small>(${coins.join(' + ')})</small>`:''}</p>
      ${keypad(x,'note',given,given,{task:t.id})}</div>
      <div class="row wrap">${x.cmd(`💵 Thu ${n.cash}, thối ${given} & giao`,'dl_deliver',{task:t.id,change:given},'primary big')}</div>`;
  }else if(!blocked){
    body+=`<div class="row wrap">${x.cmd('✅ Giao tận tay','dl_deliver',{task:t.id},'primary big')}
      ${n.safe_drop&&!n.cod?x.confirmCmd('📸 Gửi chòi bảo vệ','dl_safedrop',{task:t.id},'Gửi hàng ở chòi bảo vệ và chụp ảnh làm bằng chứng? Khách đã cho phép trong ghi chú.',''):''}
      ${!n.safe_drop&&!n.cod&&!n.paper?x.confirmCmd('📦 Gửi người nhận hộ','dl_safedrop',{task:t.id},'Khách chưa cho phép gửi người khác. Vẫn gửi nhận hộ và chụp ảnh?','ghost small'):''}</div>`;
  }
  if(r.knocks||blocked)body+=`<div class="row wrap">${x.confirmCmd('📝 Báo giao thất bại','dl_fail',{task:t.id},r.broken_seen?'Lập biên bản hàng hỏng? Bạn đền một nửa giá trị hàng.':'Báo giao thất bại cho đơn này?','danger small')}</div>`;
  return body;
}
function hubPanel(x){
  const d=x.room.data||{},u=ui(x),given=sum(u.settle);
  if(!(d.owed>0))return '';
  const rows=(d.cod||[]).map(r=>`<li><span>${x.esc(r.item)}</span><b>${r.cod} xu</b>${r.day<x.room.day?'<small>từ hôm trước</small>':''}</li>`).join('');
  return `<section class="dl-sec dl-hub"><h4 class="section-title">💵 Nộp tiền COD</h4>
    <ul class="dl-statement">${rows}</ul>
    <p class="small muted">Túi đang có ${d.bag} xu tiền mặt.</p>
    <p class="dl-change">Đang đếm: <b>${given} xu</b></p>${keypad(x,'snote',given,given)}
    <div class="row wrap">${x.confirmCmd(`Nộp ${given} xu cho kế toán`,'dl_settle',{amount:given},`Nộp ${given} xu COD cho kế toán bưu cục?`,'primary',!given)}</div></section>`;
}
function servicePanel(x){
  const d=x.room.data||{},b=d.bike;if(!b||d.at!=='gas')return '';
  const need=b.tyre<100||b.rim;
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
    ${gas?'':'<p class="small muted">Đắt gấp đôi, tối đa 20% — chỉ để chạy tới cây xăng.</p>'}
    <div class="row wrap">${opts.map(v=>x.confirmCmd(`+${v}% · ${v/step*unit} xu`,'dl_refuel',{amount:v},`Đổ thêm ${v}% xăng hết ${v/step*unit} xu?`,gas?'':'ghost')).join('')}</div></section>`;
}
function stopPanel(x){
  const d=x.room.data||{},here=nodeOf(x,d.at),s=stopsAt(x,d.at);
  const cards=[...s.pick.map(t=>`<article class="dl-order pick">${head(t,x)}${pickupCard(t,x)}</article>`),
               ...s.drop.map(t=>`<article class="dl-order drop">${head(t,x)}${dropCard(t,x)}</article>`)].join('');
  const expired=live(x).filter(t=>t.known&&t.needs.kind==='food'&&t.run.expired&&destOf(t)!==d.at);
  return `<section class="dl-sec focus"><h4 class="section-title">📍 Đang ở ${x.esc(here.emoji)} ${x.esc(here.name)} <small class="muted">${x.esc(here.note||'')}</small></h4>
    ${cards||'<p class="muted">Không có đơn cần lấy hay giao ở đây.</p>'}
    ${expired.map(t=>`<p class="notice red">${x.esc(t.needs.item)}: khách đã hủy đơn. ${x.confirmCmd('Báo thất bại','dl_fail',{task:t.id},'Báo giao thất bại cho đơn đã bị hủy?','danger small')}</p>`).join('')}
    <div class="row wrap">${x.cmd('⏳ Chờ 5 phút','dl_wait',{},'ghost small')} ${x.button('📦 Kho vật tư','inventory',{},'ghost small')}</div></section>
    ${d.at==='hub'?hubPanel(x):''}${fuelPanel(x)}${servicePanel(x)}${garagePanel(x)}`;
}

/* ---------- order board & checklist ---------- */
function board(x,active){
  const rows=live(x);
  return `<section class="dl-board"><h4 class="section-title">📱 Đơn trên app (${rows.length})</h4>${rows.map(t=>{
    const st=stage(t),n=t.needs,p=t.preview||{};
    const who=x.npc(t.npc);
    if(st==='new')return `<article class="dl-card new ${t.id===active?'active':''}"><div class="row"><span class="dl-oemoji">${x.esc(p.emoji||'📦')}</span><div class="grow"><b>${x.esc(nodeOf(x,p.pickup).name)} → ${x.esc(nodeOf(x,p.dest).name)}</b><small>${x.esc(who.display_name)}: “${x.esc(t.opening)}”</small></div></div>${x.cmd('✋ Nhận đơn','ask',{task:t.id},'primary full')}</article>`;
    const label={pickup:`Chờ lấy · ${nodeOf(x,n.pickup).name}`,bag:`Trên xe → ${nodeOf(x,destOf(t)).name}`}[st]||'';
    return `<article class="dl-card ${st} ${t.id===active?'active':''}"><div class="row"><span class="dl-oemoji">${x.esc(n.emoji)}</span><div class="grow"><b>${x.esc(n.item)}</b><small>${x.esc(label)}${t.due!=null?` · hẹn ${x.esc(hm(t.due))}`:''}${n.cod?` · COD ${n.cod}`:''}</small></div>${t.id===active?'':x.cmd('Xem','task_select',{task:t.id},'ghost small')}</div></article>`;
  }).join('')||'<p class="muted small">Chưa có đơn.</p>'}</section>`;
}
/* ---------- next step: one list of steps drives the checklist, the header hint and the bottom button ---------- */
/** The biggest note that still fits: how a courier counts change. */
const nextNote=(x,rest)=>(x.cc.notes||[50,20,10,5,2,1]).find(v=>v<=rest)||1;
const place=(x,id)=>`${nodeOf(x,id).emoji} ${nodeOf(x,id).name}`;
/** Ride the planned leg, or plan one to `to` (the player's own draft first). */
function rideGo(x,to){
  const d=x.room.data||{},next=(d.route||[])[0];
  if(next){const e=(d.eta||[])[0];return {cmd:'dl_ride',payload:{way:'main'},label:`🛵 Chạy tới ${x.esc(place(x,next))}${e?` · ${e.minutes} phút`:''}`};}
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
  return {...row,go:low?fuelGo(x):rideGo(x,to)};
}
/** Hand the COD cash in at the hub: count what the statement says, then give it to the accountant. */
function settleSteps(x){
  const d=x.room.data||{},owed=Number(d.owed)||0,given=sum(ui(x).settle),here=d.at==='hub';
  if(!(owed>0))return [];
  let go=null,pulse='';
  if(here&&given>owed)go={act:'car:snoteClear',label:'↺ Đếm lại tiền nộp'};
  else if(here&&given<owed){const v=nextNote(x,owed-given);go={act:'car:snote',data:{v},label:`➕ Đếm thêm tờ ${v} xu · ${given}/${owed}`};pulse=`.dl-hub [data-action="car:snote"][data-v="${v}"]`;}
  return [{ok:given===owed?true:given>owed?false:null,label:`Đếm đủ ${owed} xu COD theo bảng kê`,note:given&&!here?`đang đếm ${given} xu`:'',go,pulse},
    {ok:null,label:'Nộp tiền cho kế toán',go:here&&given===owed?{cmd:'dl_settle',payload:{amount:given},confirm:`Nộp ${given} xu COD cho kế toán bưu cục?`,label:`💵 Nộp ${given} xu cho kế toán`}:null}];
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
    if(wait)S.push({ok:null,label:`Chờ quán làm món (xong ${hm(t.ready)})`,go:here?{cmd:'dl_wait',payload:{},label:`⏳ Chờ quán 5 phút · xong ${hm(t.ready)}`}:null});
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
    const right=n.cash-n.cod;given=sum(u.change[t.id]||[]);
    let go=null,pulse='';
    if(here&&first&&given>right)go={act:'car:noteClear',data:{task:t.id},label:'↺ Đếm lại tiền thối'};
    else if(here&&first&&given<right){const v=nextNote(x,right-given);go={act:'car:note',data:{task:t.id,v},label:`➕ Thối thêm tờ ${v} xu · ${given}/${right}`};pulse=`.dl-cash [data-action="car:note"][data-v="${v}"]`;}
    else if(here&&!first&&!given)go={sel:'.dl-cash .dl-keypad .dl-note'};
    S.push({ok:first?(given===right?true:given>right?false:null):(given?true:null),
      label:first?`Thối lại ${right} xu (khách đưa ${n.cash}, hàng ${n.cod})`:`Đếm tiền thối (khách đưa ${n.cash}, hàng ${n.cod})`,note:given&&!first?`đang đếm ${given} xu`:'',go,pulse});
  }
  const stairs=(x.cc.stairs||{})[dest]||0;
  if(here&&r.back!=null&&(d.clock||0)+stairs<r.back)
    S.push({ok:null,label:`Chờ khách về (hẹn ${hm(r.back)})`,go:{cmd:'dl_wait',payload:{},label:`⏳ Chờ khách 5 phút · hẹn ${hm(r.back)}`}});
  const final={label:n.cod?`💵 Thu ${n.cash}, thối ${given} & giao`:'✅ Giao tận tay',go:finalGo(S,'dl_deliver',n.cod?{task:t.id,change:given}:{task:t.id}),ready:here&&!full,why:here?'':`tới ${nodeOf(x,dest).name}`};
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
function bar(t,x,g){
  // Every screen has a step to do; this only shows if something unexpected leaves none.
  const final=g.final||{label:'📍 Xem điểm dừng',go:{sel:'.dl-sec.focus'},ready:!pending(g.steps)?.go};
  return `<div class="dl-bar">${stepCta(x,g.steps,final)}</div>`;
}
function hintFor(t,x,g){
  const f=g.final&&g.final.ready!==false?{label:g.final.label.replace(/^[^\p{L}\d]+/u,''),go:g.final.go}:null;
  return nextHint(x,g.steps,{final:f});
}

export default {
  id:'delivery',
  css:true,
  next(t,x){
    try{const n=x&&pending(guide(t,x).steps);if(n)return x.esc(n.label);}catch{/* fall back to the fixed lines */}
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
  job(t,x){
    const g=guide(t,x),hint=hintFor(t,x,g);
    if(x.room.data?.desk?.ev)return `<div class="career-job dl">${hint}${status(x)}${deskCard(x)}</div>`;
    return `<div class="career-job dl">${hint}${status(x)}${t.known?'':board(x,t.id)}${deskCard(x)}<div class="workbench"><section class="wb-main">
      ${stopPanel(x)}
      <section class="dl-sec dl-route-sec"><h4 class="section-title">🗺️ Lộ trình</h4>${map(x)}${areaLine(x)}${planner(x)}</section>
      ${roadBoard(x)}${scoreStrip(x)}${careSection(x)}
    </section><aside class="wb-side">${t.known?`${stepRows(x,g.steps,'Việc của đơn')}${board(x,t.id)}`:''}</aside></div>${bar(t,x,g)}</div>`;
  },
  // Between orders: still ride to the hub to hand in COD cash or to refuel.
  idle(x){
    if(x.room.data?.desk?.ev)return `<div class="career-job dl">${status(x)}${deskCard(x)}</div>`;
    return `<div class="career-job dl">${status(x)}${roadBoard(x)}${scoreStrip(x)}${deskCard(x)}<div class="workbench"><section class="wb-main">
      ${stopPanel(x)}
      <section class="dl-sec"><h4 class="section-title">🗺️ Lộ trình</h4>${map(x)}${areaLine(x)}${planner(x)}</section>
      ${careSection(x)}
    </section><aside class="wb-side">${board(x,null)}</aside></div></div>`;
  },
  actions:{
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
    async fix(data,el,x){const u=ui(x),f=u.fix||[];u.fix=f.includes(data.part)?f.filter(p=>p!==data.part):[...f,data.part];x.render();},
  },
  // The sticky next-step bar rides above the sheet's own sticky footer.
  tick(root){keepBarAboveFooter(root);},
  dock:[['inventory','box','Vật tư','Xốp, keo, túi mưa']],
};
