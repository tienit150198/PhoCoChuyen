/** Shared pieces of the step-slip trades: 🏍️ Tiệm sửa xe Út Lanh (moto.js), 🩺 Phòng khám Thú y Cỏ May (vet.js), 📱 Studio
 * Hẻm Xanh (kol.js), 🎤 Phòng trà Mây Chiều (singer.js) and 🎬 Hãng phim Bến Mây (actor.js).
 * A job is a list of server-graded steps (game/careers/stepkit.py), one open at a time: choice, order (tap in turn),
 * multi (tap the right lines) and number (with its unit). The second half is the card of other players' orders from
 * 🛎️ Phố dịch vụ, worked here step by step (<prefix>svc) and handed over with Giao (POST /api/svc/done).
 * Layout lives in public/css/careers/slip_kit.css; each career keeps its own colours in public/css/careers/<id>.css. */
import {data,act,amountBox} from './street_kit.js';
import {tip,buildUp} from '../ui-kit.js';

export const stepsOf=t=>t.needs?.steps||[];
export const current=t=>stepsOf(t)[t.at];

/** The job taking shape step by step (owner 21/10, like the milk-tea cup): one piece per step of the slip, the done ones
 * solid, the open one ringed (.now), the rest grey ghosts. Used by every step-slip trade (moto, vet, reception, teller,
 * research, radio, kol, singer, actor). `icons`: {step id | step name | job: emoji}; a step with none gets its kind's (choice 💬, number 🔢…). */
const TYPE_ICON={choice:'💬',number:'🔢',order:'🔢',multi:'☑️',times:'🕒',assign:'📌',tray:'💵'};
export function stepIcon(st,icons={}){const id=String(st.id||''),[job,name]=id.split('.');return icons[id]||icons[name]||icons[job]||TYPE_ICON[st.type]||'•';}
export function stepsArt(t,{kind='tray',icons={},head='',label=''}={}){
  const steps=stepsOf(t);if(!steps.length)return '';
  const at=Math.min(Number(t.at)||0,steps.length);
  // Steps after the open one stay blank ghosts: their parts would tell the fault before the player settles it.
  const items=steps.map((st,i)=>i>at?{e:'◌',t:'',cls:'todo'}:{e:stepIcon(st,icons),t:st.title,cls:i<at?'':'todo now'});
  return buildUp({kind,items,caption:`${head?head+' ':''}${at}/${steps.length}`,label,cls:'sl-art'});
}

/** Ordered or multiple picks, sent as one value: `cmd` with `payload` + {step, value}. */
function pickStep(key,st,x,ordered,cmd,payload){
  const opts=st.options||[],seq=((x.ui.slPick??={})[key]||[]).filter(v=>opts.some(o=>o.id===v));
  const rows=opts.map(o=>{
    const i=seq.indexOf(o.id),on=i>=0;
    const mark=on?`<i class="sl-num">${ordered?i+1:'✓'}</i>`:'<i class="sl-num off"></i>';
    return act(x,`${mark}<span>${x.esc(o.label)}</span>`,'slPick',{key,id:o.id},`sl-pick${on?' on':''}`,` aria-pressed="${on}"`);
  }).join('');
  const ready=ordered?seq.length===opts.length:seq.length>0;
  const send=x.cmd(ordered?'Xác nhận thứ tự':'Xác nhận lựa chọn',cmd,{...payload,step:st.id,value:ordered?seq:[...seq].sort()},'primary sl-send',!ready);
  return `${tip(ordered?'Bấm lần lượt theo thứ tự; bấm lại để bỏ.':'Bấm để chọn hoặc bỏ chọn từng dòng.','','p','small')}<div class="sl-picks" data-pick="${ordered?'order':'multi'}">${rows}</div>
    <div class="sl-row">${act(x,'Làm lại','slClear',{key},'ghost sl-clear',seq.length?'':' disabled')}${send}</div>`;
}

function choiceStep(st,x,cmd,payload){
  return `<div class="sl-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),cmd,{...payload,step:st.id,value:o.id},'sl-option')).join('')}</div>`;
}

/** The open step's answer area. `key`: what the picks and the typed number are remembered under. */
export function stepBody(st,x,cmd,payload,key){
  if(st.type==='choice')return choiceStep(st,x,cmd,payload);
  if(st.type==='order')return pickStep(key,st,x,true,cmd,payload);
  if(st.type==='multi')return pickStep(key,st,x,false,cmd,payload);
  return amountBox(x,`sl-${key}`,0,{min:0,max:100000,label:'Con số ghi vào phiếu',send:'Ghi vào phiếu',cmd,payload:{...payload,step:st.id},field:'value',unit:st.unit||''});
}

/** The open step of a slip: count, progress, what is in front of you and the answer area. `facts`: plain text shown under
 * the question (the numbers it works from, e.g. the weight weighed one step earlier); `said`: plain text only a screen
 * reader reads there (what a chart beside the slip shows, so the step is answerable without seeing it). */
export function stepCard(x,st,{at,total,quality,cmd,payload,key,label='phiếu',facts='',said=''}){
  return `<section class="card sl-step" aria-labelledby="sl-step-title-${x.esc(key)}">
    <p class="sl-step-count" role="status">Bước ${at+1}/${total}${quality===undefined?'':` · chất lượng ${x.esc(quality)}%`}</p>
    <progress value="${at}" max="${total}" aria-label="Tiến trình ${x.esc(label)}"></progress>
    <h3 id="sl-step-title-${x.esc(key)}">${x.esc(st.title)}</h3><p class="sl-evidence">${x.esc(st.evidence)}</p>
    ${facts?`<p class="sl-facts"><span aria-hidden="true">📋</span> ${x.esc(facts)}</p>`:''}${said?`<p class="sr-only">${x.esc(said)}</p>`:''}
    ${stepBody(st,x,cmd,payload,key)}</section>`;
}

/** The notebook (content().rules) as a list. */
export function rulesList(x){
  return `<ul class="sl-rules">${(x.cc?.rules||[]).map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`;
}

/** Today's count and the journey so far. `money`: the field and its label (moto: earned · công, vet: bonus · thưởng).
 * Players' orders are counted only where the career takes them (stats.svc). */
export function statsCard(x,{noun,money,moneyLabel,master,title}){
  const d=data(x),t=d.today||{},s=d.stats||{},today=t.day===x.room.day?t:{jobs:0,good:0,[money]:0};
  const badge=d.expert?' · 🏅 Chuyên gia':d.mastered?' · ⭐ Thành thạo':'';
  return `<details class="sl-stats"><summary>📊 Hôm nay: ${x.esc(today.jobs||0)} ${noun} · ${x.esc(today.good||0)} đạt · ${x.fmt(today[money]||0)} xu ${moneyLabel}</summary>
    <p class="small">${x.esc(title)}${badge}: ${x.esc(s.good||0)} ${noun} đạt / ${x.esc(s.jobs||0)} ${noun} · ${x.esc(s.active_days||0)} ngày làm · ${x.fmt(s[money]||0)} xu ${moneyLabel}${s.svc===undefined?'':` · ${x.esc(s.svc)} đơn người chơi`}.</p>
    <p class="small">${noun[0].toUpperCase()+noun.slice(1)} đạt từ 90% chất lượng mới được ghi; ngày có ${noun} đạt mới tính ngày làm. Thành thạo: ${x.esc(master[0])} ${noun} đạt và ${x.esc(master[1])} ngày làm.</p></details>`;
}

/* ------------------------------------------------------------ 🛎️ other players' orders worked in the career
 * GET /api/svc/inbox lists my orders; this career's provider orders that are 'held' (take them) or 'working' are
 * shown here. The open jobs (data.svc: order, service, at, total, wrong, step) and the finished ones (data.svc_ok) come
 * with the career's own save. Fetched lazily from meters() and kept 20 s. */
let INBOX={at:0,items:null,busy:false};
const STALE=20000;
/** Forget the cached inbox (another account in the same page, tests). */
export function inboxReset(){INBOX={at:0,items:null,busy:false};}
/** After a take or a delivery: the inbox is read again on the next tick, and the save is refreshed. */
async function reload(x){INBOX.at=0;try{await x.api.refresh?.();}catch{}x.render();}
const sig=items=>(items||[]).map(o=>o.id+o.status).join(',');

export function inboxTick(root,x){
  if(!root.querySelector?.('[data-sl-orders]')||INBOX.busy||Date.now()-INBOX.at<STALE||!x.api?.json)return;
  INBOX.busy=true;
  x.api.json('/api/svc/inbox').then(v=>{
    const first=!INBOX.items,before=sig(INBOX.items);INBOX={at:Date.now(),items:(v?.items||[]),busy:false};
    if(first||sig(INBOX.items)!==before)x.render();
  }).catch(()=>{const first=!INBOX.items;INBOX={at:Date.now(),items:INBOX.items||[],busy:false};if(first)x.render();});   // no inbox (yet): the open jobs still show
}

/** The card. `o`: {id (career), svcCmd, title, emoji, noun, empty, done, attrs (its data-coach)} */
export function ordersCard(x,o){
  const d=data(x),jobs=d.svc||[],ok=new Set(d.svc_ok||[]);
  const mine=(INBOX.items||[]).filter(r=>r.career===o.id&&r.role==='provider'&&(r.status==='working'||r.status==='held'));
  const shown=new Set(mine.map(r=>r.id));
  const rows=[...mine.map(r=>orderRow(x,o,r,jobs.find(j=>j.order===r.id),ok.has(r.id))),
    ...jobs.filter(j=>!shown.has(j.order)).map(j=>orderRow(x,o,null,j,false))];   // before the inbox arrives, or an order that left it: the job can still be finished
  const body=rows.length?rows.join(''):INBOX.items?`<p class="small sl-empty">${x.esc(o.empty)}</p>`:'<p class="small sl-empty">⏳</p>';
  return `<section class="card sl-orders" data-sl-orders ${o.attrs} aria-labelledby="sl-orders-${x.esc(o.id)}">
    <div class="sl-orders-head"><h3 id="sl-orders-${x.esc(o.id)}"><span aria-hidden="true">${o.emoji}</span> ${x.esc(o.title)}</h3>
    <button type="button" class="btn ghost small" data-action="svcMarket" data-inbox="1">🛎️ Phố dịch vụ</button></div>${body}</section>`;
}

const dropBtn=(x,cmd,payload)=>x.confirmCmd?x.confirmCmd('Bỏ đơn',cmd,payload,'Bỏ đơn này khỏi sổ? Không có tiền công, không có kinh nghiệm.','ghost small sl-drop')
  :x.cmd('Bỏ đơn',cmd,payload,'ghost small sl-drop');

function orderRow(x,o,r,job,done){
  const id=r?.id||job.order,service=r?.service||job.service;
  const head=r?`<div class="sl-order-head"><b>${x.esc(r.icon)} ${x.esc(r.name)}${r.qty>1?` <small>× ${x.esc(r.qty)} ${x.esc(r.unit)}</small>`:''}</b><small>Khách: ${x.esc(r.other?.name||'')}</small></div>${r.note?`<blockquote class="sl-note">${x.esc(r.note)}</blockquote>`:''}`
    :`<div class="sl-order-head"><b>${x.esc(o.noun)} · đơn ${x.esc(id.slice(-6))}</b></div>`;
  let body;
  if(r?.status==='held')body=act(x,'Nhận đơn','slTake',{order:id},'primary sl-take');
  else if(done)body=`<p class="sl-ready" role="status">${x.esc(o.done)}</p>${act(x,'Giao','slDone',{order:id},'primary sl-give')}`;
  else if(job?.step)body=stepCard(x,job.step,{at:job.at,total:job.total,cmd:o.svcCmd,payload:{order:id,service},key:`svc-${id}-${job.step.id}`,label:'đơn'})+
    (job.wrong?`<p class="small sl-wrong">Đã sai ${x.esc(job.wrong)} lần: mỗi lần sai bớt một sao khi giao.</p>`:'')+
    // An untouched order the buyer cancelled (or was refunded) can be dropped to free its slot: no pay, no xp.
    // A started one is finished instead (the server keeps its mistakes in the grade).
    (job.at===0&&!job.wrong?`<div class="sl-row">${dropBtn(x,o.svcCmd,{order:id,drop:true})}</div>`:'');
  else body=x.cmd('Bắt đầu làm',o.svcCmd,{order:id,service},'primary sl-start');
  return `<article class="sl-order" data-order="${x.esc(id)}">${head}${body}</article>`;
}

/** Client actions of the slip trades; spread into the module's `actions` after kitActions. */
export const slipActions={
  async slPick(d,el,x){
    const all=x.ui.slPick??={},seq=all[d.key]||[],i=seq.indexOf(d.id);
    all[d.key]=i>=0?seq.filter(id=>id!==d.id):[...seq,d.id];x.render();
  },
  async slClear(d,el,x){(x.ui.slPick??={})[d.key]=[];x.render();},
  async amtSend(d,el,x){
    // A reading can be 0 (a brake pad worn to the limit), so 0 goes too; the server grades it.
    const raw=x.ui.amt?.[d.key],value=Number(raw===undefined||raw===''?d.def:raw);
    if(!Number.isInteger(value)||value<0||value>100000){x.toast?.('Nhập số nguyên từ 0 đến 100000.');return;}
    await x.send(d.cmd,{...JSON.parse(d.extra||'{}'),[d.field]:value});
  },
  async slTake(d,el,x){
    try{const r=await x.api.post('/api/svc/take',{order:d.order});x.toast?.(r?.message||'Đã nhận đơn.');}
    catch(e){x.toast?.(e.message||'Chưa nhận được đơn. Thử lại nhé.');}
    await reload(x);
  },
  async slDone(d,el,x){
    try{const r=await x.api.post('/api/svc/done',{order:d.order});x.toast?.(r?.message||'Đã giao.');}
    catch(e){x.toast?.(e.message||'Chưa giao được. Thử lại nhé.');}
    await reload(x);
  },
};
