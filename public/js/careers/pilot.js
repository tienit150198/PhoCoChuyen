/** Phi công Cánh Cò — first officer on the turboprop (server: game/careers/pilot.py).
 * One hop at a time, one panel at a time: the briefing and the fuel, the walk-around on the
 * aircraft drawing, the switch panel in the checklist's order and the announcement, a decision
 * on the way, then the two approach gates. Dark cockpit look, amber for what needs a decision.
 * Everything is decided on the server; the client shows it and sends one command per tap.
 * ✈️ Tự bay (./pilot_fly.js, loaded when first needed): the take-off, a storm cell on the track and the approach are
 * flown in a first-person cockpit; ⏩ Bay nhanh keeps these panels. The cockpit shows this file's own decision
 * panels (turbulence, a sick passenger, weather over the field, the rain set-up) over its instrument panel. */
import {nextHint,stepCta,finalGo,pending,firstTime,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import * as air from './air_kit.js';
import {insignia} from '../v4/promo.js';
const data=x=>x.room.data||{};
const cc=x=>x.cc||{};
const kg=n=>`${Number(n||0).toLocaleString('vi-VN')} kg`;
const carBtn=(x,label,action,d={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-action="car:${action}"${Object.entries(d).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}${extra}>${label}</button>`;
const cmdTile=(x,command,payload,inner,cls='',disabled=false,extra='')=>`<button type="button" class="pl-tile ${cls}" data-command="${command}" data-payload="${x.esc(JSON.stringify(payload))}"${disabled?' disabled':''}${extra}>${inner}</button>`;
/* ------------------------------------------------------------ ✈️ Tự bay / ⏩ Bay nhanh */
// The player's choice, kept in this browser like the other display choices (mnl.*). Tự bay unless they chose
// Bay nhanh, the cockpit cannot run here (or ran too slowly), or a script drives the browser (the first-day sweeps
// press what glows: nobody flies them).
const FLY_KEY='mnl.plFly';
function flyPref(){try{const v=localStorage.getItem(FLY_KEY);if(v==='1')return true;if(v==='0')return false;}catch{/* storage blocked */}return !navigator.webdriver;}
function setFly(on){try{localStorage.setItem(FLY_KEY,on?'1':'0');}catch{/* storage blocked */}}
let FLY=null,flyLoad=null,flyFail=false,shown=null;
const flyAuto=new Set();   // the hop states the cockpit already opened by itself on (never twice: no loop after a fallback)
function flyMod(){
  if(FLY||flyFail)return Promise.resolve(FLY);
  return flyLoad??=import('./pilot_fly.js').then(m=>(FLY=m)).catch(e=>{flyFail=true;console.warn('Chưa mở được buồng lái',e);return null;});
}
const flyCan=()=>!flyFail&&(!FLY||FLY.canFly());
const flyOn=()=>flyCan()&&flyPref();
/** What the cockpit shows over its panel while the autopilot flies: this file's decision panels. */
function flyAsk(t,x){
  if(t.stage==='cruise')return cruisePanel(t,x);
  if(t.stage==='approach'&&(t.problem||skyOf(t,x)))return approachPanel(t,x);
  return '';
}
async function openFly(x,t){
  const m=await flyMod();
  if(!m||!m.canFly()){x.render();return;}
  m.open(x,t,{ask:flyAsk,fallback:()=>{setFly(false);x.render();},done:()=>x.render()});
  m.sync(x,t);
}
/** After each render and a few times a second: keep the cockpit current, or open it on a hop in the air. */
function flyTick(x){
  const t=shown;if(!x||!t)return;
  const live=t&&x.room.tasks?.find(r=>r.id===t.id)||t;
  if(FLY?.isOpen()){FLY.sync(x,live);return;}
  if(!flyOn()||!['cruise','approach'].includes(live.stage))return;
  const d=data(x);
  if(d.desk?.ev||d.odd?.ev){flyAuto.clear();return;}   // after that answer the cockpit comes back
  if(!d.intro||x.ui.intro)return;
  const key=`${live.id}|${live.stage}|${live.ap}|${live.gate}|${live.arounds}|${live.problem||''}|${live.at||''}`;
  if(flyAuto.has(key))return;
  flyAuto.add(key);openFly(x,live);
}
function modeSwitch(x){
  if(!flyCan())return '';
  const on=flyPref();
  return `<div class="pl-mode" role="radiogroup" aria-label="Cách bay">${carBtn(x,'✈️ Tự bay','flyMode',{on:1},on?'on':'',` role="radio" aria-checked="${on}"`)}${carBtn(x,'⏩ Bay nhanh','flyMode',{on:0},on?'':'on',` role="radio" aria-checked="${!on}"`)}</div>`;
}

const STAGES=[['brief','📋','Bản tin'],['walk','🚶','Vòng tàu'],['start','✅','Checklist'],['cruise','✈️','Bay'],['approach','🛬','Hạ cánh']];

/* ------------------------------------------------------------ cards on top */
function introCard(x,force=false){
  const d=data(x),i=cc(x).intro;if(!i||(d.intro&&!force))return '';
  const list=(title,rows)=>`<section><h4>${x.esc(title)}</h4><ul class="pl-icons">${rows.map(([e,s])=>`<li><span aria-hidden="true">${x.esc(e)}</span>${x.esc(s)}</li>`).join('')}</ul></section>`;
  const go=d.intro?carBtn(x,'Đã hiểu','introClose',{},'primary full'):x.cmd('✈️ Vào ca bay','pl_intro',{},'primary full pl-intro-go');
  return `<article class="pl-intro card" role="dialog" aria-labelledby="pl-intro-title"><h3 id="pl-intro-title">🧑‍✈️ ${x.esc(i.title)}</h3><p>${x.esc(i.lead)}</p>
    <div class="pl-intro-grid">${list('Công việc gồm…',i.work)}${list('Bạn sẽ gặp…',i.meet)}${list('Được khen khi…',i.stars)}</div>${go}</article>`;
}
function deskCard(x){
  const desk=data(x).desk;if(!desk)return '';
  const ev=desk.ev;
  if(ev){
    const opts=ev.options.map(o=>x.cmd(`<span class="pl-opt-label">${x.esc(o.label)}</span>${o.hint?`<small>${x.esc(o.hint)}</small>`:''}`,'pl_desk',{option:o.id},'pl-opt')).join('');
    return `<section class="pl-event ${ev.tone==='tense'?'tense':''}" role="group" aria-labelledby="pl-ev-title"><div class="pl-ev-head"><span aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>Chuyện ở sân bay</small><h3 id="pl-ev-title">${x.esc(ev.title)}</h3></div></div>
      <p>${x.esc(ev.text)}</p><div class="pl-opts pl-desk-opts">${opts}</div></section>`;
  }
  const last=desk.last,key=last?`${last.script}-${last.choice}-${last.day}-${(desk.log||[]).length}`:'';
  if(last&&last.day===x.room.day&&x.ui.seen!==key)
    return `<div class="pl-last ${last.good===true?'good':last.good===false?'bad':''}" role="status"><span aria-hidden="true">${x.esc(last.emoji)}</span><p><b>${x.esc(last.title)}</b> · ${x.esc(last.outcome)}</p>${carBtn(x,'✕','seen',{key},'ghost small pl-x',' aria-label="Đã đọc"')}</div>`;
  return '';
}
function arcCard(x){
  const due=data(x).arc?.due;if(!due)return '';
  return `<article class="pl-arc card"><small>Chuyện nghề bay</small><h3>${x.esc(due.emoji)} ${x.esc(due.title)}</h3>${due.text.map(s=>`<p>${x.esc(s)}</p>`).join('')}${x.cmd('Ghi nhớ','pl_arc',{},'small primary')}</article>`;
}
function dayLine(x){
  const m=data(x).mod||{},s=data(x).schedule;
  const roster=s&&x.room.open?`<p class="small">✈️ Lịch hôm nay: ${x.esc(s.total)} chặng · ${x.esc(s.completed)} đã bay · ${x.esc(s.remaining)} còn lại</p>`:'';
  return `<div class="pl-day"><span aria-hidden="true">${x.esc(m.emoji||'🌤️')}</span><b class="grow">${x.esc(m.label||'')}</b><small>${x.esc(m.hint||'')}</small>${carBtn(x,'❔','intro',{},'ghost small pl-help',' aria-label="Giới thiệu nghề"')}</div>${roster}`;
}
/** The flight strip: code, route, time, passengers and where the hop is. */
function strip(t,x){
  const n=t.needs||{},leg=n.leg||{},at=STAGES.findIndex(s=>s[0]===t.stage),stage=t.stage==='landed'||t.stage==='done'?STAGES.length:at;
  const dots=STAGES.map(([id,e,label],i)=>`<li class="${i<stage?'done':i===stage?'now':''}"><span aria-hidden="true">${e}</span><small>${x.esc(label)}</small></li>`).join('');
  const late=(t.delay||0)+(t.air_late||0);
  return `<article class="pl-strip"><div class="pl-strip-top"><b class="pl-code">${x.esc(leg.code||'')}</b><span class="pl-route">${x.esc(leg.frm||'')} → ${x.esc(t.where||leg.to||'')} ${x.esc(leg.emoji||'')}</span></div>
    <div class="pl-strip-sub"><span>⏱️ ${leg.minutes||0}′</span><span>👥 ${n.pax||0}</span><span>Thưởng dự kiến ${x.esc(t.expected_bonus??12)} xu</span>${late?`<span class="pl-late">+${late}′</span>`:''}${t.at?`<span class="pl-late">↪️ ${x.esc(t.at)}</span>`:''}</div>
    <p class="small muted">Thưởng đủ khi bay đúng quy trình; lỗi an toàn mất thưởng. Lương theo hợp đồng.</p>
    <ol class="pl-stages" aria-label="Các bước chuyến bay">${dots}</ol></article>`;
}

/* ------------------------------------------------------------ brief */
function needFuel(t){const f=t.needs?.fuel||{};return (f.trip||0)+(f.alt||0)+(f.reserve||0)+(t.needs?.wx?.id==='storm'?(f.hold||0):0);}
function briefPanel(t,x){
  if(!t.known){
    const who=x.npc(t.npc);
    return `<article class="card pl-brief-ask"><div class="row">${x.portrait(who,48)}<div class="grow"><h3>${x.esc(who.display_name)}</h3><p class="small">${x.esc(t.opening)}</p></div></div></article>`;
  }
  const n=t.needs,wx=n.wx||{},f=n.fuel||{},c=cc(x);
  const wxCard=`<article class="pl-wx wx-${x.esc(wx.id)}"><span class="pl-wx-emoji" aria-hidden="true">${x.esc(wx.emoji)}</span><div><small>Thời tiết ở ${x.esc(n.leg.to)}</small><b>${x.esc(wx.name)}</b><p>${x.esc(wx.text)}</p></div></article>`;
  let body='';
  if(t.fuel==null){
    const rows=[['🛫',`Chặng ${n.leg.frm} → ${n.leg.to}`,f.trip],['↪️',`Bay đi dự bị ${n.leg.alt}`,f.alt],['⏳','Dự phòng 30 phút',f.reserve]];
    const tiles=(f.options||[]).map(v=>cmdTile(x,'pl_fuel',{task:t.id,kg:v},`<b>${kg(v)}</b><small>${v===c.tanks?'đầy bình':''}</small>`,'pl-fuel-tile','',` data-kg="${v}"`)).join('');
    body=`<article class="card pl-fuel"><h4>⛽ Nạp dầu</h4><ul class="pl-sum">${rows.map(([e,l,v])=>`<li><span aria-hidden="true">${e}</span><span class="grow">${x.esc(l)}</span><b>${kg(v)}</b></li>`).join('')}</ul>
      <p class="pl-rule small">⛈️ Dự báo giông lúc tới: thêm dầu chờ 20 phút (${kg(f.hold)}).${n.full?` · 🧳 Kín khách: đừng đổ đầy bình.`:''}</p><div class="pl-tiles pl-fuel-tiles">${tiles}</div></article>`;
  }else if(wx.id==='fog'&&!t.fog){
    body=`<article class="card pl-fog"><h4>🌫️ Sương ở ${x.esc(n.leg.to)}</h4><p class="small">Dầu đã nạp ${kg(t.fuel)}.</p>
      <div class="pl-opts">${x.cmd('<span class="pl-opt-label">🌫️ Lùi giờ cất cánh, chờ sương tan</span><small>Trễ 30 phút, chờ dưới đất</small>','pl_fog',{task:t.id,wait:true},'pl-opt pl-fog-wait')}
      ${x.cmd('<span class="pl-opt-label">🛫 Giữ giờ cất cánh</span><small>Tới nơi mà sương chưa tan thì…</small>','pl_fog',{task:t.id,wait:false},'pl-opt')}</div></article>`;
  }
  return wxCard+body;
}

/* ------------------------------------------------------------ the walk-around */
const PLANE=`<svg class="pl-plane" viewBox="0 0 320 130" aria-hidden="true"><path d="M18 70 Q14 58 34 56 L232 52 Q262 52 290 62 Q304 67 300 74 Q296 80 280 81 L40 84 Q20 84 18 70Z" fill="var(--pl-body)" stroke="var(--pl-edge)" stroke-width="2"/>
<path d="M36 56 L20 22 L42 22 L70 55Z" fill="var(--pl-body)" stroke="var(--pl-edge)" stroke-width="2"/><path d="M110 58 L170 30 L196 30 L160 60Z" fill="var(--pl-wing)" stroke="var(--pl-edge)" stroke-width="2"/>
<rect x="150" y="40" width="34" height="14" rx="6" fill="var(--pl-edge)"/><line x1="186" y1="30" x2="186" y2="64" stroke="var(--pl-edge)" stroke-width="3"/>
${[80,100,120,140,200,220,240].map(cx=>`<rect x="${cx}" y="61" width="10" height="8" rx="3" fill="var(--pl-window)"/>`).join('')}<path d="M270 60 Q286 60 294 68 L276 68Z" fill="var(--pl-window)"/>
<line x1="90" y1="84" x2="90" y2="104" stroke="var(--pl-edge)" stroke-width="4"/><circle cx="90" cy="110" r="9" fill="var(--pl-tyre)"/><line x1="262" y1="81" x2="262" y2="104" stroke="var(--pl-edge)" stroke-width="3"/><circle cx="262" cy="110" r="7" fill="var(--pl-tyre)"/>
<text x="120" y="80" font-size="9" font-weight="700" fill="var(--pl-edge)">CÁNH CÒ</text></svg>`;
// Spread so the four tiles never cover each other, down to 320 px (the wing tile used to sit on the engine's).
const SPOT={gear:[18,78],engine:[60,18],wing:[44,62],hold:[84,50]};
function walkPanel(t,x){
  const n=t.needs,df=n.defect,points=cc(x).points||[];
  const spots=points.map(p=>{const done=(t.checked||[]).includes(p.id),bad=df&&df.point===p.id,[l,tp]=SPOT[p.id]||[50,50];
    const cls=bad&&!t.handled?'bad':done?'done':'';
    return `<button type="button" class="pl-spot ${cls}" style="left:${l}%;top:${tp}%" data-command="pl_check" data-payload="${x.esc(JSON.stringify({task:t.id,point:p.id}))}"${done?' disabled':''} aria-label="${x.esc(p.name)}"><span aria-hidden="true">${done?(bad&&!t.handled?'⚠️':'✓'):x.esc(p.emoji)}</span><small>${x.esc(p.name)}</small></button>`;}).join('');
  let defect='';
  if(df&&!t.handled){
    defect=`<section class="pl-event tense pl-defect"><div class="pl-ev-head"><span aria-hidden="true">⚠️</span><div><small>Phát hiện khi kiểm tàu</small><h3>${x.esc(df.text)}</h3></div></div>
      <div class="pl-opts">${df.own?x.cmd(`<span class="pl-opt-label">🔧 ${x.esc(df.fix)}</span><small>Tự xử lý</small>`,'pl_defect',{task:t.id,how:'fix'},'pl-opt pl-fix'):''}
      ${x.cmd('<span class="pl-opt-label">📞 Gọi chú Mẫn kiểm tra, ghi sổ kỹ thuật</span><small>Có thể trễ chuyến</small>','pl_defect',{task:t.id,how:'report'},'pl-opt pl-report')}
      ${x.cmd('<span class="pl-opt-label">⏩ Bỏ qua cho kịp giờ</span>','pl_defect',{task:t.id,how:'ignore'},'pl-opt ghost')}</div></section>`;
  }
  return `${defect}<article class="card pl-walk"><h4>🚶 Một vòng quanh tàu <small class="muted">${(t.checked||[]).length}/${points.length}</small></h4><div class="pl-plane-box">${PLANE}${spots}</div></article>`;
}

/* ------------------------------------------------------------ checklist, switches, announcement */
function startPanel(t,x){
  const c=cc(x),list=c.checklist||[],done=t.switches||[],by=Object.fromEntries(list.map(r=>[r.id,r]));
  const card=`<ol class="pl-check">${list.map((r,i)=>`<li class="${i<done.length?'done':i===done.length?'now':''}"><span aria-hidden="true">${i<done.length?'✓':i+1}</span><span class="grow">${x.esc(r.name)}</span><b>${x.esc(r.state)}</b></li>`).join('')}</ol>`;
  const panel=(c.panel||[]).map(id=>{const r=by[id]||{},on=done.includes(id);
    return cmdTile(x,'pl_switch',{task:t.id,id},`<span class="pl-led ${on?'on':''}" aria-hidden="true"></span><span class="pl-sw-emoji" aria-hidden="true">${x.esc(r.emoji||'')}</span><b>${x.esc(r.name||id)}</b><small>${on?x.esc(r.state):'—'}</small>`,`pl-switch ${on?'on':''}`,on,` data-sw="${x.esc(id)}"`);}).join('');
  let pa='';
  if(t.delay&&!t.pa){
    pa=`<article class="card pl-pa-card"><h4>📢 Thông báo cho khách <small class="muted">trễ ${t.delay} phút</small></h4><div class="pl-opts pl-pa">${(c.pa||[]).map(o=>x.cmd(`<span class="pl-opt-label">${x.esc(o.label)}</span>`,'pl_pa',{task:t.id,option:o.id},`pl-opt pl-pa-${o.id}`)).join('')}</div></article>`;
  }
  return `<article class="card pl-cockpit"><h4>✅ Checklist trước khi nổ máy</h4>${card}<div class="pl-panel">${panel}</div></article>${pa}`;
}

/* ------------------------------------------------------------ on the way */
function cruisePanel(t,x){
  const ev=t.needs?.event;if(!ev)return '';
  return `<section class="pl-event tense pl-cruise"><div class="pl-ev-head"><span aria-hidden="true">${x.esc(ev.emoji)}</span><div><small>Trên đường bay</small><h3>${x.esc(ev.title)}</h3></div></div>
    <p>${x.esc(ev.text)}</p><div class="pl-opts pl-cruise-opts">${ev.options.map(o=>x.cmd(`<span class="pl-opt-label">${x.esc(o.label)}</span>`,'pl_decide',{task:t.id,option:o.id},'pl-opt')).join('')}</div></section>`;
}

/* ------------------------------------------------------------ arrival and the gates */
function approachPanel(t,x){
  const n=t.needs,c=cc(x);
  if(t.problem){
    const holdOk=(t.fuel||0)>=(n.fuel.trip+n.fuel.alt+n.fuel.reserve+n.fuel.hold);
    const w=t.problem==='storm'?'Giông đang ở trên sân bay':'Sương còn dày dưới mức tối thiểu';
    return `<section class="pl-event tense pl-arrive"><div class="pl-ev-head"><span aria-hidden="true">${t.problem==='storm'?'⛈️':'🌫️'}</span><div><small>Tới ${x.esc(n.leg.to)}</small><h3>${w}</h3></div></div>
      <div class="pl-opts">${x.cmd(`<span class="pl-opt-label">🔄 Bay chờ 20 phút</span><small>${holdOk?'Đủ dầu chờ':'Không có dầu chờ'}</small>`,'pl_arrive',{task:t.id,how:'hold'},'pl-opt',!holdOk)}
      ${x.cmd(`<span class="pl-opt-label">↪️ Bay đi sân bay dự bị ${x.esc(n.leg.alt)}</span>`,'pl_arrive',{task:t.id,how:'divert'},'pl-opt')}
      ${x.cmd('<span class="pl-opt-label">⬇️ Cố hạ cánh ngay</span>','pl_arrive',{task:t.id,how:'land'},'pl-opt')}</div></section>`;
  }
  const sk=skyOf(t,x);
  if(sk)return skyCard(t,sk,x);
  const g=(n.gates[t.ap]||[])[t.gate];
  if(!g)return '';
  const rows=g.rows.map(([label,value,limit])=>`<tr><th>${x.esc(label)}</th><td><b>${x.esc(value)}</b></td><td><small>${x.esc(limit)}</small></td></tr>`).join('');
  const round=t.arounds?`<small class="muted"> · lần tiếp cận ${t.arounds+1}</small>`:'';
  return `<article class="card pl-gate"><h4>🛬 ${x.esc(g.name)}${round}</h4><p class="small muted">Tới ${x.esc(t.where)} · số liệu phải nằm trong giới hạn mới được xuống tiếp.</p>
    <table class="pl-read">${rows}</table>
    <div class="pl-gate-btns">${x.cmd('✅ Ổn định · tiếp tục','pl_gate',{task:t.id},'primary big pl-gate-go')}${x.cmd('↗️ Bay lại','pl_around',{task:t.id},'big pl-gate-around')}</div></article>`;
}

/* ------------------------------------------------------------ rain and squalls on arrival */
/** The airport's weather for this hop, while the approach is not set up yet. */
function skyOf(t,x){const sk=data(x).sky;return sk&&sk.task===t.id&&!sk.set?sk:null;}
/** Read the report, then set up the approach yourself: wipers, autobrake, the speed margin, which side of the cell, land or not. */
function skyCard(t,sk,x){
  const u=x.ui.sky&&x.ui.sky.task===t.id?x.ui.sky:(x.ui.sky={task:t.id,wipers:null,brake:'',add:null,dodge:sk.cell?'':'keep',go:''});
  const seg=(k,opts)=>`<div class="pl-sky-seg">${opts.map(([v,l])=>carBtn(x,l,'sky',{k,v},`pl-sky-opt${String(u[k])===String(k==='wipers'?(v==='1'):v)?' on':''}`)).join('')}</div>`;
  const rows=[['Tầm nhìn',`${Number(sk.vis).toLocaleString('vi-VN')} m`],['Phanh đường băng',sk.braking],['Gió giật',sk.gust?`${sk.gust} kt`:'không'],
    ...(sk.cell?[['Ô giông',sk.cell==='left'?'bên trái đường tiếp cận':'bên phải đường tiếp cận']]:[])];
  const ready=u.wipers!==null&&u.brake&&u.add!==null&&u.dodge&&u.go;
  const payload={task:t.id,wipers:!!u.wipers,brake:u.brake||'med',add:u.add??0,dodge:u.dodge||'keep',go:u.go||'land'};
  return `<section class="pl-event tense pl-sky"><div class="pl-ev-head"><span aria-hidden="true">${x.esc(sk.emoji)}</span><div><small>Bản tin sân bay ${x.esc(t.needs.leg.to)}</small><h3>${x.esc(sk.name)}</h3></div></div>
    <table class="pl-read">${rows.map(([a,b])=>`<tr><th>${x.esc(a)}</th><td><b>${x.esc(b)}</b></td></tr>`).join('')}</table>
    <div class="pl-sky-rows"><small>Gạt mưa</small>${seg('wipers',[['1','Bật'],['0','Tắt']])}
      <small>Phanh tự động</small>${seg('brake',[['low','Thấp'],['med','Vừa'],['max','Tối đa']])}
      <small>Cộng tốc độ</small>${seg('add',[['0','+0'],['5','+5 kt'],['10','+10 kt']])}
      ${sk.cell?`<small>Né ô giông</small>${seg('dodge',[['left','⬅️ Trái'],['right','Phải ➡️']])}`:''}
      <small>Quyết định</small>${seg('go',[['land','🛬 Tiếp cận'],['divert',`↪️ Đi ${t.needs.leg.alt}`]])}</div>
    ${x.cmd(ready?'✅ Xác nhận cài đặt':'Chọn đủ các mục',`pl_sky`,payload,'primary big pl-sky-go',!ready)}</section>`;
}

/* ------------------------------------------------------------ guide */
function guide(t,x){
  const d=data(x),first=firstTime(x),c=cc(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở sân bay',go:{sel:'.pl-desk-opts',label:'👉 Chọn cách xử lý'},pulse:''}],final:null};
  const o=air.oddStep(x);if(o)return {steps:[o],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'pl_intro',payload:{},label:'✈️ Vào ca bay'}}],final:null};
  if(!t.known)return {steps:[{ok:null,label:'Nhận bản tin bay',go:{cmd:'ask',payload:{task:t.id},label:'📋 Nhận bản tin bay'}}],final:null};
  const n=t.needs,id=t.id;
  if(t.stage==='brief'){
    if(t.fuel==null)return {steps:[{ok:null,label:'Nạp dầu cho chặng bay',go:{sel:'.pl-fuel-tiles',label:'⛽ Chọn lượng dầu'},pulse:first?`.pl-fuel-tile[data-kg="${needFuel(t)}"]`:''}],final:null};
    return {steps:[{ok:null,label:'Quyết: chờ sương hay giữ giờ',go:{sel:'.pl-fog',label:'🌫️ Chờ sương hay giữ giờ?'},pulse:first?'.pl-fog-wait':''}],final:null};
  }
  if(t.stage==='walk'){
    const steps=(c.points||[]).map(p=>({ok:(t.checked||[]).includes(p.id)?true:null,label:`${p.emoji} ${p.name}`,go:{cmd:'pl_check',payload:{task:id,point:p.id},label:`${x.esc(p.emoji)} Kiểm ${x.esc(p.name.toLowerCase())}`}}));
    const df=n.defect;
    if(df&&!t.handled)steps.unshift({ok:false,label:df.text,go:{cmd:'pl_defect',payload:{task:id,how:df.own?'fix':'report'},label:df.own?`🔧 ${x.esc(df.fix)}`:'📞 Gọi chú Mẫn kiểm tra'}});
    return {steps,final:null};
  }
  if(t.stage==='start'){
    const done=t.switches||[];
    const steps=(c.checklist||[]).map((r,i)=>({ok:i<done.length?true:null,label:`${r.name}: ${r.state}`,go:i===done.length?{cmd:'pl_switch',payload:{task:id,id:r.id},label:`${x.esc(r.emoji)} ${x.esc(r.name)}: ${x.esc(r.state)}`}:null}));
    if(t.delay)steps.push({ok:t.pa?true:null,label:'Thông báo trễ chuyến cho khách',go:t.pa?null:{sel:'.pl-pa',label:'📢 Chọn câu thông báo'},pulse:first?'.pl-pa-clear':''});
    const go=flyOn()?{act:'car:fly',data:{task:id}}:finalGo(steps,'pl_takeoff',{task:id});
    return {steps,final:{label:'🛫 CẤT CÁNH',go,ready:done.length===(c.checklist||[]).length&&(!t.delay||!!t.pa),why:'làm xong checklist'}};
  }
  if(t.stage==='cruise')return {steps:[{ok:null,label:'Quyết định trên đường bay',go:{sel:'.pl-cruise-opts',label:'👉 Chọn cách xử lý'},pulse:''}],final:null};
  if(t.stage==='approach'){
    if(t.problem)return {steps:[{ok:null,label:'Thời tiết ở đích: chờ, dự bị hay hạ cánh',go:{sel:'.pl-arrive',label:'👉 Quyết định khi tới'},pulse:''}],final:null};
    if(skyOf(t,x))return {steps:[{ok:null,label:'Đọc bản tin sân bay, cài đặt tiếp cận',go:{sel:'.pl-sky',label:'🌧️ Cài đặt tiếp cận'},pulse:''}],final:null};
    const g=(n.gates[t.ap]||[])[t.gate];
    return {steps:[{ok:null,label:`${g?.name||'Cổng'}: đọc số liệu rồi quyết`,go:{sel:'.pl-gate-btns',label:'🛬 Đọc số liệu, quyết định'},pulse:first?'.pl-gate-go':''}],final:null};
  }
  if(t.stage==='landed')return {steps:[],final:{label:'🅿️ TẮT MÁY · GHI SỔ',go:{cmd:'pl_park',payload:{task:id}},ready:true}};
  return {steps:[],final:null};
}
function hintFor(g,x){
  const f=g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  return nextHint(x,g.steps,{final:f,pulse:g.pulse});
}
function bottom(t,x,g){
  if(!g.final)return g.steps.length?`<div class="pl-bar">${stepCta(x,g.steps,{label:'',go:null,ready:false})}</div>`:'';
  return `<div class="pl-bar">${stepCta(x,g.steps,g.final)}</div>`;
}

/* ------------------------------------------------------------ idle: the logbook */
function logbook(x){
  const d=data(x),lb=d.logbook||{},h=Math.floor((lb.minutes||0)/60),m=(lb.minutes||0)%60;
  const log=(d.log||[]).slice().reverse().map(r=>`<li><span>Ngày ${r.day}</span><b>${x.esc(r.code)}</b><span class="grow">→ ${x.esc(r.to)}</span><small>${r.late?`+${r.late}′`:'đúng giờ'}${r.arounds?` · ↗️${r.arounds}`:''}</small><span aria-hidden="true">${r.ok?'✓':'•'}</span></li>`).join('');
  return `<article class="card pl-logbook"><h4>📘 Sổ giờ bay</h4><div class="pl-stats"><div><b>${lb.flights||0}</b><small>chặng</small></div><div><b>${h}h${m?String(m).padStart(2,'0'):''}</b><small>giờ bay</small></div><div><b>${lb.arounds||0}</b><small>lần bay lại</small></div><div><b>${lb.safe||0}</b><small>chặng an toàn</small></div></div>
    ${log?`<ul class="pl-log">${log}</ul>`:'<p class="small muted">Chưa có chặng nào. Chuyến đầu tiên đang chờ.</p>'}</article>`;
}

/* ------------------------------------------------------------ the airline shell (air_kit.js) */
/* ------------------------------------------------------------ 🎖️ the rank (F#193: stripes and stars, game/promotion.py) */
const RANK_CODE=['CƠ PHÓ','CƠ PHÓ CAO CẤP','CƠ TRƯỞNG','CƠ TRƯỞNG HL','TRƯỞNG ĐỘI BAY','PGĐ KHAI THÁC','GĐ KHAI THÁC','PHÓ TGĐ'];
/** The airline shell's words for the rank held (the pass shows a short code, the sheets the full title and insignia). */
function crew(x){
  const p=x?.room?.promo;
  if(!p||!Number.isInteger(p.rank)||p.rank<0)return AIR;
  return {...AIR,role:RANK_CODE[p.rank]||AIR.role,role_line:`${p.title}${p.insignia?` · ${p.insignia.label}`:''}`};
}
function rankCard(x){
  const p=x.room?.promo;if(!p||!p.insignia)return '';
  const of=p.office,n=of?.inbox?.length||0;
  const office=of?`<button type="button" class="btn small ${of.live?'primary':''}" data-action="pmOffice">🏢 ${x.esc(of.name)}${n?` · ${n}`:''}</button>`:'';
  return `<article class="card pl-rank"><button type="button" class="pl-rank-btn" data-action="promo" aria-label="Thăng tiến: ${x.esc(p.title)}">${insignia(p.insignia,84)}<span><b>${x.esc(p.title)}</b><small>${x.esc(p.insignia.label)}${p.next?` · ${p.next.good}/${p.next.need} ngày tốt`:''}${(r=>r?` · 🏢 ${r.got}/${r.need} ngày điều hành tốt`:'')(p.next?.requirements?.find(r=>r.id==='office'&&r.need))}</small></span></button>${office}</article>`;
}
const done=t=>['completed','cancelled','referred'].includes(t.status);
const pct=(a,b)=>b?`${Math.round(100*a/b)}%`:'—';
const AIR={id:'pilot',airline:'Hãng bay Cánh Cò',role:'CƠ PHÓ',role_down:'CƠ PHÓ DỰ BỊ',odd:'pl_odd',rest:'pl_rest',role_line:'Cơ phó · bay cùng cơ trưởng Vân',back:'✈️ Về buồng lái',
  more:'Nhận thêm một chặng',done_word:'chặng',crew:[0,1,2,3],
  row(t){
    if(t.status==='completed')return {status:t.at?`Hạ cánh ${t.at}`:'Đã hạ cánh',tone:'done'};
    if(done(t))return {status:'Hủy',tone:'bad'};
    if(!t.known)return {status:`Chờ bản tin · Thưởng dự kiến ${t.expected_bonus??12} xu`};
    const late=(t.delay||0)+(t.air_late||0);
    if(t.stage==='cruise'||t.stage==='approach')return {status:'Đang bay',tone:'air'};
    if(t.stage==='landed')return {status:'Đã hạ cánh',tone:'done'};
    return late?{status:`Trễ ${late}′`,tone:'late'}:{status:t.stage==='start'?'Lên tàu':'Chuẩn bị',tone:'now'};
  },
  log(x){
    const lb=data(x).logbook||{},n=lb.flights||0,h=Math.floor((lb.minutes||0)/60),m=(lb.minutes||0)%60;
    return {tiles:[[n,'chặng bay'],[`${h}h${String(m).padStart(2,'0')}`,'giờ bay'],[pct(lb.ontime||0,n),'đúng giờ'],[pct(lb.fuel_ok||0,n),'dầu đúng kế hoạch'],
      [lb.arounds||0,'lần bay lại'],[n-(lb.safe||0),'chặng có lỗi an toàn']],
      rows:(data(x).log||[]).slice().reverse().map(r=>({day:`N${r.day}`,code:r.code,text:`→ ${r.to}`,status:r.late?`+${r.late}′`:'Đúng giờ',tone:r.ok?'done':'late'}))};
  },
  close:d=>[[d.flights||0,'chặng bay'],[`${d.minutes||0}′`,'trên trời'],[pct(d.ontime||0,d.flights||0),'đúng giờ']],
};

export default {
  id:'pilot',
  css:true,
  next(t,x){
    try{const n=x&&pending(guide(t,x).steps);if(n)return x.esc(stepLine(n));const g=guide(t,x);if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    if(!t.known)return 'Nhận bản tin bay';
    return {brief:'Nạp dầu',walk:'Kiểm quanh tàu',start:'Checklist, cất cánh',cruise:'Quyết định trên đường bay',approach:'Tiếp cận, hạ cánh',landed:'Tắt máy, ghi sổ'}[t.stage]||'Chuyến bay';
  },
  job(t,x){
    shown=t;
    if(flyPref()&&flyCan()&&t.known)flyMod();   // the cockpit's code on its way before the take-off
    const g=guide(t,x),hint=hintFor(g,x),d=data(x);
    const top=`${dayLine(x)}${introCard(x,!!x.ui.intro)}${deskCard(x)}${air.oddCard(x,crew(x))}${air.groundCard(x)}`;
    if(d.desk?.ev||d.odd?.ev||(d.odd?.conduct?.ground&&['brief','walk','start'].includes(t.stage))||!d.intro||x.ui.intro)return `<div class="career-job pl">${hint}${top}${bottom(t,x,g)}</div>`;
    let main='';
    if(!t.known||t.stage==='brief')main=briefPanel(t,x);
    else if(t.stage==='walk')main=walkPanel(t,x);
    else if(t.stage==='start')main=startPanel(t,x);
    else if(t.stage==='cruise')main=cruisePanel(t,x);
    else if(t.stage==='approach')main=approachPanel(t,x);
    else if(t.stage==='landed')main=`<article class="card pl-landed"><h3>🛬 Đã hạ cánh ở ${x.esc(t.where)}</h3><p class="small">Lăn vào bến, tắt máy, ghi sổ bay.</p></article>`;
    const mode=t.known&&['brief','walk','start','cruise','approach'].includes(t.stage)?modeSwitch(x):'';
    return `<div class="career-job pl">${hint}${top}${t.known?strip(t,x):''}${mode}
      <div class="workbench"><section class="wb-main">${main}</section></div>${bottom(t,x,g)}</div>`;
  },
  idle(x){
    const d=data(x),steps=d.desk?.ev?[{ok:null,label:'Quyết chuyện ở sân bay',go:{sel:'.pl-desk-opts',label:'👉 Chọn cách xử lý'},pulse:''}]:air.oddStep(x)?[air.oddStep(x)]:!d.intro?[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'pl_intro',payload:{},label:'✈️ Vào ca bay'}}]:[];
    const hint=pending(steps)?.go?nextHint(x,steps,{}):'';
    const bar=pending(steps)?.go?`<div class="pl-bar">${stepCta(x,steps,{label:'',go:null,ready:false})}</div>`:'';
    const top=`${introCard(x,!!x.ui.intro)}${deskCard(x)}${air.oddCard(x,crew(x))}${air.groundCard(x)}`;
    if(d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro)return `<div class="career-job pl">${hint}${top}${bar}</div>`;
    return `<div class="career-job pl">${hint}${top}${arcCard(x)}${dayLine(x)}${rankCard(x)}${logbook(x)}${bar}</div>`;
  },
  tick(root,x){keepBarAboveFooter(root);try{flyTick(x);}catch(e){console.error(e);}},
  hudCard(c,t,x,o){
    const card=air.hudCard(c,t,x,{...crew(x),next:t=>this.next(t,x)},o),s=data(x).schedule;
    if(!c.open||!s)return card;
    const summary=`<div class="pl-flight-summary"><span>Lịch hôm nay: ${x.esc(s.total)} chặng · ${x.esc(s.remaining)} còn lại</span>${t?`<span>Thưởng dự kiến ${x.esc(t.expected_bonus??12)} xu</span>`:''}</div>`;
    return card.replace(/<\/article>$/,summary+'</article>');
  },
  board(x){return `<div class="pl pl-board">${dayLine(x)}${rankCard(x)}${air.board(x,crew(x))}</div>`;},
  page(view,x){return air.page(view,x,crew(x));},
  daySummary(s,x){return air.daySummary(s,x,crew(x));},
  nav(items){return air.nav(items,AIR);},
  spots:air.SPOTS,
  noDecor:true,  // no "Chăm chút không gian" on the workbench: a crew has no shop to decorate
  actions:{
    ...air.ACTIONS,
    async seen(d,el,x){x.ui.seen=d.key;x.render();},
    async sky(d,el,x){x.ui.sky={...(x.ui.sky||{}),[d.k]:d.k==='wipers'?d.v==='1':d.k==='add'?Number(d.v):d.v};x.render();},
    async intro(d,el,x){x.ui.intro=true;x.render();},
    async introClose(d,el,x){x.ui.intro=false;x.render();},
    async fly(d,el,x){const t=(x.room.tasks||[]).find(r=>r.id===d.task);if(t)await openFly(x,t);},
    async flyMode(d,el,x){const on=d.on==='1';setFly(on);if(!on&&FLY?.isOpen())FLY.close();x.render();},
  },
};
