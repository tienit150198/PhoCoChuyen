/** Tiếp viên Cánh Cò — the cabin of the turboprop (server: game/careers/flight_attendant.py).
 * The door (boarding passes and bags), the safety demonstration (hold up the prop the purser
 * is reading) and the aisle check on a seat map, the cart row by row on the same seat map,
 * the belt-sign countdown, a difficult passenger in three lines, and first aid from the kit.
 * Teal and coral cabin look. Everything is decided on the server; one command per tap. */
import {stepRows,nextHint,stepBar,finalGo,pending,firstTime,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import * as air from './air_kit.js';
import {introCard as shortIntro,introHelp} from './street_kit.js';
import {tip,clean,whyAttrs,helpBtn} from '../ui-kit.js';
const data=x=>x.room.data||{};
const cc=x=>x.cc||{};
const lower=s=>s?s[0].toLowerCase()+s.slice(1):'';
const carBtn=(x,label,action,d={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-action="car:${action}"${Object.entries(d).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}${extra}>${label}</button>`;
const tile=(x,command,payload,inner,cls='',disabled=false,extra='')=>`<button type="button" class="tv-tile ${cls}${/aria-disabled/.test(extra)?' is-why':''}" data-command="${command}" data-payload="${x.esc(JSON.stringify(payload))}"${disabled?' disabled':''}${extra}>${inner}</button>`;
const item=(x,id)=>[...(cc(x).drinks||[]),...(cc(x).snacks||[])].find(i=>i.id===id)||{id,name:id,emoji:'•'};
const HOT=new Set(['tea','coffee']);
const WHO_EMOJI=w=>/bé|Bé/.test(w)?'👶':/Ông|ông|Bà|bà|Cụ/.test(w)?'🧓':/Chú|chú|Anh|anh|Cậu/.test(w)?'🧑':'👩';

/** What a seat should get: the purser's list, the peanut row, small children, sleepers (same rules as the server). */
function rightItems(s,ssr,row){
  if(s.kind==='sleep')return [];
  const drink=s.kind==='kid'&&HOT.has(s.drink)?'juice':s.drink;
  let snack=s.snack;
  if(ssr?.veg===s.seat)snack='veg';
  else if(snack==='nuts'&&ssr?.nut===row)snack='cake';
  return [drink,...(snack?[snack]:[])];
}
function leftItems(s,ssr,row){
  const got=[...(s.given||[])];
  return rightItems(s,ssr,row).filter(i=>{const k=got.indexOf(i);if(k>=0){got.splice(k,1);return false;}return true;});
}

/* ------------------------------------------------------------ cards on top */
/** The job's intro: the street trades' short card (name, three icon rows of ≤ 5 words, "?" with the lead and the
 * lists); the start button is the bar's (the guide's intro step). Shown until the player starts, or reopened by ❔. */
function introCard(x){return shortIntro(x,'fa_intro','💁');}
function deskCard(x){
  const desk=data(x).desk;if(!desk)return '';
  const ev=desk.ev;
  if(ev){
    const opts=ev.options.map(o=>x.cmd(`<span class="tv-opt-label">${x.esc(o.label)}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}`,'fa_desk',{option:o.id},'tv-opt')).join('');
    return `<section class="tv-event ${ev.tone==='tense'?'tense':''}" role="group" aria-labelledby="tv-ev-title"><div class="tv-ev-head"><span aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>Chuyện trong khoang</small><h3 id="tv-ev-title">${x.esc(ev.title)}</h3></div></div>
      <p>${x.esc(ev.text)}</p><div class="tv-opts tv-desk-opts">${opts}</div></section>`;
  }
  const last=desk.last,key=last?`${last.script}-${last.choice}-${last.day}-${(desk.log||[]).length}`:'';
  if(last&&last.day===x.room.day&&x.ui.seen!==key)
    return `<div class="tv-last ${last.good===true?'good':last.good===false?'bad':''}" role="status"><span aria-hidden="true">${x.esc(last.emoji)}</span><p><b>${x.esc(last.title)}</b> · ${x.esc(last.outcome)}</p>${carBtn(x,'✕','seen',{key},'ghost small tv-x',' aria-label="Đã đọc"')}</div>`;
  return '';
}
function turbCard(x){
  const tb=data(x).turb;if(!tb||tb.stage!=='coming')return '';
  const left=Math.max(0,Math.ceil(tb.start+tb.limit-x.now())),done=tb.done||[];
  const btns=(cc(x).secure||[]).map(s=>x.cmd(`${x.esc(s.emoji)} ${x.esc(s.name)}${done.includes(s.id)?' ✓':''}`,'fa_secure',{what:s.id},`big ${done.includes(s.id)?'ghost':'primary'}`,done.includes(s.id))).join('');
  return `<section class="tv-turb" role="alert" aria-live="assertive"><div class="tv-turb-head"><span aria-hidden="true">〰️</span><div><small>Đèn thắt dây vừa sáng</small><h3>Cất xe, về ghế ngay!</h3></div><b class="tv-clock" data-tv-turb="${tb.start+tb.limit}">${left}s</b></div>
    <div class="tv-turb-btns">${btns}</div></section>`;
}
function arcCard(x){
  const due=data(x).arc?.due;if(!due)return '';
  return `<article class="tv-arc card"><small>Chuyện nghề tiếp viên</small><h3>${x.esc(due.emoji)} ${x.esc(due.title)}</h3>${due.text.map(s=>`<p>${x.esc(s)}</p>`).join('')}${x.cmd('Ghi nhớ','fa_arc',{},'small primary')}</article>`;
}
const KIND_LABEL={board:'🚪 Đón khách',demo:'🦺 Hướng dẫn an toàn',service:'🛒 Xe đẩy',calm:'🗣️ Khách khó chịu',medical:'🩺 Khách không khỏe'};
function strip(t,x){
  const leg=t.needs?.leg||{};
  let q='';
  if(clean()){const m=data(x).mod||{},i=cc(x).intro;
    q=helpBtn(`day-${x.state?.current||'fa'}`,`💁 ${String(i?.title||'Tiếp viên').replace(/^Giới thiệu nghề:?\s*/,'')}`,[...(m.hint?[{title:`${m.emoji||''} ${m.label||'Hôm nay'}`,body:`<p>${x.esc(m.hint)}</p>`}]:[]),...(i?introHelp(x,i):[])],{tips:true,cls:'tv-help'});}
  const kind=KIND_LABEL[t.kind]||'';
  return `<div class="tv-strip">${leg.code?`<b>${x.esc(leg.code)}</b><span class="grow">→ ${x.esc(leg.to||'')} ${x.esc(leg.emoji||'')}</span>`:'<span class="grow"></span>'}<span class="tv-kind"${clean()?` aria-label="${x.esc(kind.replace(/^\S+\s/,''))}"`:''}>${clean()?kind.split(' ')[0]:kind}</span>${q}</div>`;
}

/* ------------------------------------------------------------ the door */
function boardPanel(t,x){
  const q=t.needs.queue,step=t.step||0,p=q[step],c=cc(x);
  const dots=q.map((_,i)=>`<span class="${i<step?'done':i===step?'now':''}" aria-hidden="true">${i<step?'✓':i+1}</span>`).join('');
  if(!p)return `<article class="card tv-door"><div class="tv-dots">${dots}</div><p>Khách đã lên đủ. Đóng cửa khoang.</p></article>`;
  const face=p.npc?x.portrait(x.npc(p.npc),52):`<span class="tv-face" aria-hidden="true">${WHO_EMOJI(p.who)}</span>`;
  const acts=(c.door||[]).map(a=>tile(x,'fa_door',{task:t.id,act:a.id},`<span class="tv-tile-emoji" aria-hidden="true">${x.esc(a.emoji)}</span><b>${x.esc(a.name)}</b>`,'tv-door-act','',` data-act="${x.esc(a.id)}"`)).join('');
  return `<article class="card tv-door"><div class="tv-dots">${dots}</div><div class="row tv-pax">${face}<div class="grow"><h3>${x.esc(p.who)}</h3><p class="tv-say">“${x.esc(p.say.replace(/^“|”$/g,''))}”</p></div></div>
    <div class="tv-pass"><span>🎫 Thẻ lên tàu</span><b>${x.esc(p.seat)}</b>${p.exit?'<span class="tv-exit">🚪 Hàng thoát hiểm</span>':''}<span class="tv-bag">${p.bag==='case'?'🧳 Vali lớn':'🎒 Túi nhỏ'}</span></div>
    <div class="tv-tiles tv-door-acts">${acts}</div></article>`;
}

/* ------------------------------------------------------------ the safety demo and the aisle */
function seatMap(x,rows,cellFn){
  return `<div class="tv-map">${rows.map(r=>`<div class="tv-map-row"><span class="tv-row-no">${r}</span>${['A','B'].map(l=>cellFn(`${r}${l}`)).join('')}<span class="tv-aisle" aria-hidden="true"></span>${['C','D'].map(l=>cellFn(`${r}${l}`)).join('')}</div>`).join('')}</div>`;
}
function demoPanel(t,x){
  const c=cc(x),demo=c.demo||[],step=t.step||0,cab=t.needs.cabin;
  if(step<demo.length){
    const next=demo[step];
    const props=[...demo].sort((a,b)=>a.name.length-b.name.length).map(d=>tile(x,'fa_demo',{task:t.id,part:d.id},`<span class="tv-tile-emoji" aria-hidden="true">${x.esc(d.emoji)}</span><b>${x.esc(d.name)}</b>`,'tv-prop','',` data-part="${x.esc(d.id)}"`)).join('');
    return `<article class="card tv-demo"><div class="tv-dots">${demo.map((_,i)=>`<span class="${i<step?'done':i===step?'now':''}" aria-hidden="true">${i<step?'✓':i+1}</span>`).join('')}</div>
      <p class="tv-mic">🎙️ ${clean()?'':'Chị Thu đọc: '}<b>“${x.esc(next.line)}”</b></p>${clean()?tip('Chị Thu đọc từng câu: giơ đúng món làm mẫu cho câu chị đang đọc.','Làm mẫu','p'):'<p class="small muted">Giơ đúng món làm mẫu cho câu chị đang đọc.</p>'}<div class="tv-tiles tv-props">${props}</div></article>`;
  }
  if(!t.walked)return `<article class="card tv-demo"><p>${clean()?`✅ Làm mẫu xong · 🚶 hàng ${cab.rows[0]}–${cab.rows[cab.rows.length-1]}`:`✅ Xong phần làm mẫu. Đi dọc lối hàng ${cab.rows[0]}–${cab.rows[cab.rows.length-1]} kiểm tra.`}</p></article>`;
  const st=cab.state||{},names=c.cabin||{};
  const cell=s=>{const v=st[s]||'ok',bad=v!=='ok',n=names[v]||{};
    return `<button type="button" class="tv-seat ${bad?'bad':'ok'}" data-command="fa_fix" data-payload="${x.esc(JSON.stringify({task:t.id,seat:s}))}"${bad?'':' disabled'} aria-label="Ghế ${s}: ${x.esc(n.name||'')}"><small>${s.slice(-1)}</small><span aria-hidden="true">${x.esc(n.emoji||'🙂')}</span></button>`;};
  const legend=Object.entries(names).filter(([k])=>k!=='ok').map(([,v])=>`<span>${x.esc(v.emoji)} ${x.esc(v.name)}</span>`).join('');
  return `<article class="card tv-cabin"><h4>🚶 ${clean()?'Khoang':'Khoang trước cất cánh'}</h4>${seatMap(x,cab.rows,cell)}${clean()?tip(legend.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim(),'Ký hiệu','p'):`<p class="tv-legend small">${legend}</p>`}</article>`;
}

/* ------------------------------------------------------------ the cart */
function ssrCard(t,x){
  const s=t.needs.ssr||{},rows=[];
  if(s.veg)rows.push(`<li>🥬 Suất chay · ghế <b>${x.esc(s.veg)}</b></li>`);
  if(s.nut)rows.push(`<li>🥜 Dị ứng đậu phộng · ghế <b>${x.esc(s.allergic||'')}</b>: cả hàng <b>${s.nut}</b> không phát đậu phộng</li>`);
  return `<article class="tv-ssr"><h4>📋 ${clean()?'Suất đặc biệt':'Phiếu suất ăn đặc biệt'}</h4><ul>${rows.join('')||'<li>Không có suất đặc biệt.</li>'}</ul></article>`;
}
function servicePanel(t,x){
  const rows=t.needs.rows,cur=rows[t.row],ssr=t.needs.ssr,c=cc(x);
  const seats=Object.fromEntries((cur.seats||[]).map(s=>[s.seat,s]));
  const sel=(x.ui.sel??={})[t.id]&&seats[x.ui.sel[t.id]]?x.ui.sel[t.id]:(cur.seats.find(s=>!s.skipped&&leftItems(s,ssr,cur.row).length)||{}).seat;
  const cell=id=>{const s=seats[id];if(!s)return `<span class="tv-seat empty" aria-hidden="true"><small>${id.slice(-1)}</small></span>`;
    const left=s.skipped?[]:leftItems(s,ssr,cur.row),done=!left.length;
    const face=s.kind==='sleep'?'😴':s.kind==='kid'?'👶':'🙂';
    return `<button type="button" class="tv-seat ${done?'done':'todo'} ${sel===id?'sel':''}" data-action="car:pick" data-task="${x.esc(t.id)}" data-seat="${x.esc(id)}" aria-label="Ghế ${id}"><small>${id.slice(-1)}</small><span aria-hidden="true">${done?'✓':face}</span></button>`;};
  const s=seats[sel];
  const who=s?`<div class="tv-order"><b>Ghế ${x.esc(s.seat)}</b> · ${x.esc(s.who)}<p class="tv-say">${x.esc(s.say)}</p>${(s.given||[]).length?`<p class="small">Đã mời: ${s.given.map(i=>x.esc(item(x,i).emoji)).join(' ')}</p>`:''}
    ${s.kind==='sleep'&&!s.skipped?x.cmd('😴 Để khách ngủ','fa_skip',{task:t.id,seat:s.seat},'small tv-skip'):''}</div>`:'<p class="small muted">Hàng này đã xong.</p>';
  const can=(t.can?.fa_give||{})[sel]||{};
  const cart=[...(c.drinks||[]),...(c.snacks||[])].map(i=>tile(x,'fa_give',{task:t.id,seat:sel||'',item:i.id},`<span class="tv-tile-emoji" aria-hidden="true">${x.esc(i.emoji)}</span><b>${x.esc(i.name)}</b>`,'tv-cart-item',!s||s.skipped||s.kind==='sleep',` data-item="${x.esc(i.id)}"${whyAttrs(can[i.id])}`)).join('');
  return `${ssrCard(t,x)}<article class="card tv-service"><h4>🛒 Hàng ${cur.row} <small class="muted">${t.row+1}/${rows.length}</small></h4>${seatMap(x,[cur.row],cell)}${who}<div class="tv-tiles tv-cart">${cart}</div></article>`;
}

/* ------------------------------------------------------------ a difficult passenger */
function calmPanel(t,x){
  const m=t.needs.calm,who=x.npc(t.npc);
  const said=(m.said||[]).map(s=>`<li>💬 ${x.esc(s)}</li>`).join('');
  return `<article class="card tv-calm"><div class="row">${x.portrait(who,52)}<div class="grow"><h3>${x.esc(m.emoji)} ${x.esc(m.title)}</h3><div class="tv-dots">${Array.from({length:m.beats},(_,i)=>`<span class="${i<(t.step||0)?'done':i===(t.step||0)?'now':''}" aria-hidden="true">${i+1}</span>`).join('')}</div></div></div>
    ${said?`<ul class="tv-said">${said}</ul>`:''}${m.now?`<p class="tv-say">${x.esc(m.now.text)}</p><div class="tv-opts tv-says">${m.now.options.map(o=>x.cmd(`<span class="tv-opt-label">${x.esc(o.label)}</span>`,'fa_calm',{task:t.id,option:o.id},`tv-opt tv-say-${o.id}`)).join('')}</div>`:''}</article>`;
}

/* ------------------------------------------------------------ first aid */
function medicalPanel(t,x){
  const m=t.needs.case,c=cc(x),used=t.used||[];
  const qs=(c.questions||[]).map(q=>m.answers[q.id]?`<li class="done"><span aria-hidden="true">${x.esc(q.emoji)}</span><span>${x.esc(m.answers[q.id])}</span></li>`
    :`<li>${x.cmd(`${x.esc(q.emoji)} ${x.esc(q.name)}`,'fa_ask',{task:t.id,q:q.id},'small ghost tv-q')}</li>`).join('');
  const kit=(c.kit||[]).map(k=>tile(x,'fa_care',{task:t.id,item:k.id},`<span class="tv-tile-emoji" aria-hidden="true">${x.esc(k.emoji)}</span><b>${x.esc(k.name)}</b>${used.includes(k.id)?'<small>✓ đã làm</small>':''}`,`tv-kit-item ${used.includes(k.id)?'used':''} ${k.id==='own_med'?'warn':''}`,used.includes(k.id))).join('');
  return `<article class="card tv-medical"><div class="row">${x.portrait(x.npc(t.npc),52)}<div class="grow"><h3>🩺 ${x.esc(m.title)}</h3><p class="tv-say">${x.esc(m.seen)}</p></div></div>
    <ul class="tv-qs">${qs}</ul><h4>🧰 Túi sơ cứu</h4><div class="tv-tiles tv-kit">${kit}</div></article>`;
}

/* ------------------------------------------------------------ guide */
function guide(t,x){
  const d=data(x),first=firstTime(x),c=cc(x);
  if(d.turb?.stage==='coming')return {steps:[{ok:null,label:'Cất xe, cất bình nóng, về ghế',go:{sel:'.tv-turb-btns',label:'〰️ Cất xe, về ghế!'},pulse:''}],final:null};
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện trong khoang',go:{sel:'.tv-desk-opts',label:'👉 Chọn cách xử lý'},pulse:''}],final:null};
  const o=air.oddStep(x);if(o)return {steps:[o],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'fa_intro',payload:{},label:'🧣 Vào ca bay'}}],final:null};
  const id=t.id;
  if(!t.known){
    const label=t.kind==='service'?(clean()?'📋 Nhận phiếu suất ăn':'📋 Nhận phiếu suất ăn đặc biệt'):t.kind==='board'?(clean()?'🚪 Ra cửa':'🚪 Ra cửa đón khách'):'👂 Hỏi chuyện khách';
    return {steps:[{ok:null,label:lower(label.replace(/^\S+\s/,'')),go:{cmd:'ask',payload:{task:id},label}}],final:null};
  }
  const n=t.needs;
  if(t.kind==='board'){
    const p=n.queue[t.step||0];
    if(!p)return {steps:[],final:{label:'🚪 ĐÓNG CỬA KHOANG',go:{cmd:'fa_close',payload:{task:id}},ready:true}};
    const guess=p.bag==='case'&&!/pin|sạc/i.test(p.say)?'hold':'seat';
    return {steps:[{ok:null,label:`Giúp ${lower(p.who)} (ghế ${p.seat})`,go:{sel:'.tv-door-acts',label:'👉 Đọc thẻ, chọn cách giúp'},pulse:first?`.tv-door-act[data-act="${guess}"]`:''}],final:null};
  }
  if(t.kind==='demo'){
    const demo=c.demo||[],step=t.step||0;
    if(step<demo.length)return {steps:demo.map((p,i)=>({ok:i<step?true:null,label:p.name,go:i===step?{cmd:'fa_demo',payload:{task:id,part:p.id},label:`${x.esc(p.emoji)} ${x.esc(p.name)}`}:null})),final:null};
    if(!t.walked)return {steps:[{ok:null,label:'Đi dọc lối kiểm tra',go:{cmd:'fa_walk',payload:{task:id},label:'🚶 Đi dọc lối kiểm tra'}}],final:null};
    const st=n.cabin.state||{},names=c.cabin||{};
    const steps=Object.entries(st).filter(([,v])=>v!=='ok').map(([s,v])=>({ok:null,label:`Ghế ${s}: ${lower(names[v]?.name||'')}`,go:{cmd:'fa_fix',payload:{task:id,seat:s},label:`${x.esc(names[v]?.emoji||'')} Ghế ${s}: ${x.esc(lower(names[v]?.name||''))}`}}));
    return {steps,final:{label:'📞 BÁO BUỒNG LÁI: SẴN SÀNG',go:finalGo(steps,'fa_ready',{task:id}),ready:true}};
  }
  if(t.kind==='service'){
    const cur=n.rows[t.row],steps=[];
    for(const s of cur.seats||[]){
      if(s.kind==='sleep'){steps.push({ok:s.skipped?true:null,label:`Ghế ${s.seat}: khách đang ngủ`,go:s.skipped?null:{cmd:'fa_skip',payload:{task:id,seat:s.seat},label:`😴 Để khách ghế ${s.seat} ngủ`}});continue;}
      const left=leftItems(s,n.ssr,cur.row);
      for(const i of left){const it=item(x,i),why=s.kind==='kid'&&HOT.has(s.drink)&&i==='juice'?' (trẻ nhỏ không uống đồ nóng)':n.ssr?.veg===s.seat&&i==='veg'?' (suất chay)':n.ssr?.nut===cur.row&&i==='cake'&&s.snack==='nuts'?' (hàng dị ứng đậu phộng)':'';
        steps.push({ok:null,label:`Ghế ${s.seat}: ${lower(it.name)}${why}`,go:{cmd:'fa_give',payload:{task:id,seat:s.seat,item:i},label:`${x.esc(it.emoji)} Ghế ${s.seat}: ${x.esc(lower(it.name))}`}});}
      if(!left.length)steps.push({ok:true,label:`Ghế ${s.seat}`});
    }
    const last=t.row>=n.rows.length-1;
    if(!last)steps.push({ok:null,label:'Đẩy xe lên hàng sau',go:{cmd:'fa_next',payload:{task:id},label:`🛒 Đẩy xe lên hàng ${n.rows[t.row+1].row}`}});
    const open=steps.filter(s=>s.ok!==true&&s.go?.cmd!=='fa_next');
    if(!last&&open.length)steps[steps.length-1].go=null;     // finish this row first
    return {steps,final:last?{label:'🛒 THU LY, CẤT XE',go:finalGo(steps,'fa_stow',{task:id}),ready:true}:null};
  }
  if(t.kind==='calm')return {steps:[{ok:null,label:'Chọn cách nói với khách',go:{sel:'.tv-says',label:'🗣️ Chọn cách nói'},pulse:first?'.tv-say-a':''}],final:null};
  const asked=Object.keys(n.case.answers||{}).length,used=(t.used||[]).length;
  const steps=[{ok:asked?true:null,label:'Hỏi han khách',go:asked?null:{sel:'.tv-qs',label:'🗣️ Hỏi khách trước'},pulse:''},{ok:used?true:null,label:'Chăm sóc bằng túi sơ cứu',go:used?null:{sel:'.tv-kit',label:'🧰 Chọn đồ trong túi sơ cứu'},pulse:''}];
  return {steps,final:{label:'✔️ XONG, THEO DÕI KHÁCH',go:{cmd:'fa_done',payload:{task:id}},ready:used>0,why:'chăm sóc khách trước'}};
}
function hintFor(g,x){
  const f=g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  return nextHint(x,g.steps,{final:f,pulse:g.pulse});
}
/** The shared bottom bar (.ui-bar via guide.js stepBar): the next step on the left, the one main button on the right. */
function bottom(t,x,g){
  if(!g.final&&!g.steps.length)return '';
  return stepBar(x,g.steps,g.final,{cls:'tv-cta'});
}
function askCard(t,x){
  // Clean layout: who is speaking and the quote (the ask); the task's title is the sheet header, the scene folds into "?".
  if(clean()){const {who,scene,say}=air.splitSay(t.opening);
    if(who)return `<article class="card tv-ask-card"><div class="row">${x.portrait(x.npc(t.npc),52)}<div class="grow"><h3>${x.esc(who)}</h3><p class="small">${x.esc(say)}</p>${scene!==who?tip(x.esc(scene),who,'p'):''}</div></div></article>`;}
  return `<article class="card tv-ask-card"><div class="row">${x.portrait(x.npc(t.npc),52)}<div class="grow"><h3>${x.esc(t.title)}</h3><p class="small">${x.esc(t.opening)}</p></div></div></article>`;
}

/* ------------------------------------------------------------ idle: the crew book */
function crewBook(x){
  const d=data(x),s=d.stats||{},log=(d.log||[]).slice().reverse().map(r=>`<li><span>Ngày ${r.day}</span><span class="grow">${x.esc(r.title)}</span><span aria-hidden="true">${r.ok?'✓':'•'}</span></li>`).join('');
  return `<article class="card tv-book"><h4>📘 Sổ tiếp viên</h4><div class="tv-stats"><div><b>${s.jobs||0}</b><small>việc</small></div><div><b>${s.pax||0}</b><small>khách đón</small></div><div><b>${s.served||0}</b><small>món đã mời</small></div><div><b>${s.medical||0}</b><small>lần sơ cứu</small></div></div>
    ${log?`<ul class="tv-log">${log}</ul>`:'<p class="small muted">Chuyến đầu tiên đang chờ ở cửa tàu.</p>'}</article>`;
}
function dayLine(x){
  const m=data(x).mod||{};
  return `<div class="tv-day"><span aria-hidden="true">${x.esc(m.emoji||'🌤️')}</span><b class="grow">${x.esc(m.label||'')}</b>${carBtn(x,'❔','intro',{},'ghost small tv-help',' aria-label="Giới thiệu nghề"')}<small>${x.esc(m.hint||'')}</small></div>`;
}

/* ------------------------------------------------------------ the airline shell (air_kit.js) */
const JOB={board:'Đón khách',demo:'An toàn',service:'Xe đẩy',calm:'Khách khó chịu',medical:'Sơ cứu'};
const AIR={id:'flight_attendant',airline:'Hãng bay Cánh Cò',role:'TIẾP VIÊN',role_down:'TIẾP VIÊN DỰ BỊ',odd:'fa_odd',rest:'fa_rest',role_line:'Tiếp viên · cùng chị Thu lo khoang khách',back:'💺 Về khoang khách',
  more:'Nhận thêm một việc',done_word:'việc',crew:[0,6],
  row(t){
    if(t.status==='completed')return {status:`✓ ${JOB[t.kind]||'Xong'}`,tone:'done'};
    if(['cancelled','referred'].includes(t.status))return {status:'Hủy',tone:'bad'};
    return {status:JOB[t.kind]||'Khoang khách',tone:t.status==='in_progress'?'now':''};
  },
  log(x){
    const s=data(x).stats||{};
    return {tiles:[[s.jobs||0,'việc'],[s.pax||0,'khách đón ở cửa'],[s.served||0,'món đã mời'],[s.fixed||0,'ghế chỉnh trước cất cánh'],[s.medical||0,'lần sơ cứu'],[s.turb_ok||0,'lần cất xe kịp']],
      rows:(data(x).log||[]).slice().reverse().map(r=>({day:`N${r.day}`,code:JOB[r.kind]||'',text:r.title,status:r.ok?'Chu đáo':'Có lỗi',tone:r.ok?'done':'late'}))};
  },
  close:d=>[[d.jobs||0,'việc'],[d.pax||0,'khách đón'],[d.served||0,'món đã mời']],
};

export default {
  id:'flight_attendant',
  css:true,
  next(t,x){
    try{const n=x&&pending(guide(t,x).steps);if(n)return x.esc(stepLine(n));const g=guide(t,x);if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return {board:'Đón khách ở cửa',demo:'Làm mẫu an toàn',service:'Đẩy xe phục vụ',calm:'Nói chuyện với khách',medical:'Chăm sóc khách'}[t.kind]||'Khoang khách';
  },
  job(t,x){
    const g=guide(t,x),hint=hintFor(g,x),d=data(x);
    const top=`${introCard(x)}${turbCard(x)}${deskCard(x)}${air.oddCard(x,AIR)}${air.groundCard(x)}`;
    if(d.turb?.stage==='coming'||d.desk?.ev||d.odd?.ev||d.odd?.conduct?.ground||!d.intro||x.ui.intro)return `<div class="career-job tv">${hint}${top}${bottom(t,x,g)}</div>`;
    let main='',side='';
    if(!t.known)main=askCard(t,x);
    else if(t.kind==='board')main=boardPanel(t,x);
    else if(t.kind==='demo'){main=demoPanel(t,x);if(t.walked)side=stepRows(x,g.steps,'Ghế cần chỉnh',{chip:true});}
    else if(t.kind==='service'){main=servicePanel(t,x);side=stepRows(x,g.steps,`Hàng ${t.needs.rows[t.row].row}`,{chip:true});}
    else if(t.kind==='calm')main=calmPanel(t,x);
    else main=medicalPanel(t,x);
    return `<div class="career-job tv">${hint}${top}${strip(t,x)}
      <div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(t,x,g)}</div>`;
  },
  idle(x){
    const d=data(x),steps=d.turb?.stage==='coming'?[{ok:null,label:'Cất xe, về ghế',go:{sel:'.tv-turb-btns',label:'〰️ Cất xe, về ghế!'},pulse:''}]
      :d.desk?.ev?[{ok:null,label:'Quyết chuyện trong khoang',go:{sel:'.tv-desk-opts',label:'👉 Chọn cách xử lý'},pulse:''}]
      :air.oddStep(x)?[air.oddStep(x)]
      :!d.intro?[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'fa_intro',payload:{},label:'🧣 Vào ca bay'}}]:[];
    const hint=pending(steps)?.go?nextHint(x,steps,{}):'';
    const bar=pending(steps)?.go?stepBar(x,steps,null,{cls:'tv-cta'}):'';
    const top=`${introCard(x)}${turbCard(x)}${deskCard(x)}${air.oddCard(x,AIR)}${air.groundCard(x)}`;
    if(d.turb?.stage==='coming'||d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro)return `<div class="career-job tv">${hint}${top}${bar}</div>`;
    return `<div class="career-job tv">${hint}${top}${arcCard(x)}${dayLine(x)}${crewBook(x)}${bar}</div>`;
  },
  hudCard(c,t,x,o){return air.hudCard(c,t,x,{...AIR,next:t=>this.next(t,x)},o);},
  board(x){return air.board(x,AIR);},
  page(view,x){return air.page(view,x,AIR);},
  daySummary(s,x){return air.daySummary(s,x,AIR);},
  nav(items){return air.nav(items,AIR);},
  spots:air.SPOTS,
  noDecor:true,  // no "Chăm chút không gian" on the workbench: a crew has no shop to decorate
  tick(root,x){
    keepBarAboveFooter(root);
    const clock=root.querySelector('[data-tv-turb]');
    if(clock){
      const end=Number(clock.dataset.tvTurb),left=Math.max(0,Math.ceil(end-x.now()));
      const s=`${left}s`;if(clock.textContent!==s)clock.textContent=s;clock.classList.toggle('late',left<=5);
      if(left<=0&&x.ui.turbSent!==end){x.ui.turbSent=end;x.send('fa_turb_end',{});}
    }
  },
  actions:{
    ...air.ACTIONS,
    async seen(d,el,x){x.ui.seen=d.key;x.render();},
    async intro(d,el,x){x.ui.intro=true;x.render();},
    async introClose(d,el,x){x.ui.intro=false;x.render();},
    async pick(d,el,x){(x.ui.sel??={})[d.task]=d.seat;x.render();},
  },
};
