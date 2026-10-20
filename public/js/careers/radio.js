/** Đài phát thanh Sóng Mây: the studio check at the start of every shift, the shift's role (Phát thanh viên, DJ after
 * probation), the outage drill when the power goes out mid-show, then one work slip at a time, one step at a time. The server
 * grades each step; a wrong one stays open to fix and lowers the job's quality. Players' ads and songs on the town ticker
 * (game/radio_station.py) are aired from 📻 Đơn lên sóng (../v4/radio.js), the same entry in both layouts. */
import {data,cc,person,askCard,introCard,deskCard,kitActions,amountBox,kitInput,notesPage,act} from './street_kit.js';
import {clean,tip} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk radio">${body}</div>`;
const stepsOf=t=>t.needs?.steps||[];
const current=t=>stepsOf(t)[t.at];
const keyOf=(id,st)=>`${id}:${st.id}`;
const ROLE_EMOJI={news:'🎙️',dj:'🎧'};

/** The role of this shift: Phát thanh viên, or DJ ca nhạc (locked until the probation is done). */
function rolePicker(x){
  const d=data(x),roles=cc(x).roles||[],p=d.progress||{},cur=d.role||'news';
  const btn=r=>{
    const locked=r.id==='dj'&&!d.promoted,on=r.id===cur;
    const sub=locked?`Mở sau ${p.probation||3} ca phát thanh viên đạt (${p.news_days||0}/${p.probation||3})`:r.work;
    return x.cmd(`<span aria-hidden="true">${x.esc(r.emoji||ROLE_EMOJI[r.id]||'')}</span><b>${x.esc(r.label)}</b><small>${x.esc(sub)}</small>`,
      'rd_role',{role:r.id},`rd-role${on?' on':''}${locked?' locked':''}`,locked);
  };
  return `<section class="rd-roles" aria-label="Vị trí trong ca"><h4>Ca này bạn làm</h4><div class="rd-role-row">${roles.map(btn).join('')}</div></section>`;
}

function progress(x){
  const d=data(x),s=d.stats||{},p=d.progress||{};
  const prob=d.promoted?'<p class="small">🎧 Đã làm được DJ ca nhạc.</p>':`<p class="small">🎙️ Thử việc phát thanh viên: ${p.news_days||0}/${p.probation||3} ca đạt.</p>`;
  return `<details class="rd-progress"><summary>Hành trình Sóng Mây · ${s.good||0} việc đạt · ${s.active_days||0} ngày · ${p.roles||0}/2 vị trí</summary>${prob}
    <p class="small">Việc đạt từ 90% chất lượng mới được ghi; ngày có việc đạt mới tính ngày. Mất điện xử lý gọn: ${s.restored||0} lần · sóng câm: ${s.dead_air||0} lần.</p>
    <ul>${(p.milestones||[]).map(m=>`<li><b>${m.achieved?'✓ ':''}${x.esc(m.label)}</b><span>${Math.min(s.good||0,m.jobs)}/${m.jobs} việc · ${Math.min(s.active_days||0,m.days)}/${m.days} ngày · ${Math.min(p.roles||0,m.roles)}/${m.roles} vị trí</span></li>`).join('')}</ul></details>`;
}

function notebook(x){
  return `<ul class="rd-rules">${(cc(x).notebook||[]).map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`;
}

/** Ordered or multiple picks, sent as one value: `cmd` with `payload` + {step, value}. */
function pickStep(id,st,x,ordered,cmd,payload){
  const key=keyOf(id,st),seq=((x.ui.rdPick??={})[key]||[]).filter(v=>(st.options||[]).some(o=>o.id===v));
  const opts=(st.options||[]).map(o=>{
    const i=seq.indexOf(o.id),on=i>=0;
    const mark=on?(ordered?`<i class="rd-num">${i+1}</i>`:'<i class="rd-num">✓</i>'):'';
    return act(x,`${mark}<span>${x.esc(o.label)}</span>`,'rdPick',{key,id:o.id},`rd-pick${on?' on':''}`,` aria-pressed="${on}"`);
  }).join('');
  const ready=ordered?seq.length===(st.options||[]).length:seq.length>0;
  const value=ordered?seq:[...seq].sort();
  const send=x.cmd(ordered?'Xác nhận thứ tự':'Xác nhận lựa chọn',cmd,{...payload,step:st.id,value},'primary rd-send',!ready);
  return `${tip(ordered?'Bấm lần lượt theo thứ tự; bấm lại để bỏ.':'Bấm để chọn hoặc bỏ chọn từng dòng.','','p','small')}<div class="rd-picks">${opts}</div>
    <div class="rd-row">${act(x,'Làm lại','rdClear',{key},'ghost')}${send}</div>`;
}

function choiceStep(st,x,cmd,payload){
  return `<div class="rd-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),cmd,{...payload,step:st.id,value:o.id},'rd-option')).join('')}</div>`;
}

function numberStep(t,st,x){
  return amountBox(x,`rd-${t.id}-${st.id}`,0,{min:0,max:100000,label:'Con số ghi vào phiếu',send:'Ghi vào phiếu',
    cmd:'rd_step',payload:{task:t.id,step:st.id},field:'value',unit:st.unit||''});   // the server takes only the step that is open
}

function stepBody(st,x,cmd,payload,id,t){
  if(st.type==='choice')return choiceStep(st,x,cmd,payload);
  if(st.type==='order')return pickStep(id,st,x,true,cmd,payload);
  if(st.type==='multi')return pickStep(id,st,x,false,cmd,payload);
  return numberStep(t,st,x);
}

/** 📋 The sheet taped by the mixing desk (the notebook's own line): the order the step asks for, one tap away. */
function poster(x,head){
  const line=(cc(x).notebook||[]).find(n=>String(n).startsWith(head));
  return line?`<details class="rd-poster"><summary>📋 Tờ dán cạnh bàn trộn âm</summary><p>${x.esc(line)}</p></details>`:'';
}

/** The studio check (before the first step on air) and, when the power went out, the outage drill. */
function shiftCard(x){
  const d=data(x),sh=d.shift||{};
  if(!sh.open)return '';
  const o=cc(x).outage||{};
  let body='';
  if(sh.outage?.state==='cut'&&sh.outage.step){
    const st=sh.outage.step;
    body=`<h4>⚡ ${x.esc(st.title)}</h4><p class="rd-alarm" role="alert">${x.esc(st.evidence)}</p>
      <p class="small">Sai ${x.esc(sh.outage.slips)}/${x.esc(sh.outage.limit)} bước: sai từ ${x.esc(o.slips??3)} bước là sóng câm quá lâu, thính giả chê.</p>
      ${poster(x,'Mất điện giữa sóng:')}${stepBody(st,x,'rd_shift',{part:'outage'},'outage',null)}`;
    return `<section class="card rd-shift rd-outage" aria-label="Xử lý mất điện giữa sóng">${body}</section>`;
  }
  if(!sh.open.done){
    const st=sh.open.step;
    body=`<h4>🎚️ Đầu ca: ${x.esc(st.title)}</h4><p class="rd-evidence">${x.esc(st.evidence)}</p>${poster(x,'Đầu ca:')}${stepBody(st,x,'rd_shift',{part:'open'},'open',null)}`;
  }else{
    body=`<p class="small">✓ Đã kiểm phòng thu, đèn ĐANG PHÁT SÓNG đã sáng.${sh.outage?.state==='back'?' 🔌 Sự cố mất điện đã xử lý.':''}</p>`;
  }
  return `<section class="card rd-shift" aria-label="Việc đầu ca ở đài">${body}</section>`;
}

function briefCard(t,x){
  const j=t.job||{},r=t.role_info||{};
  return `<article class="rd-post"><small>${x.esc(r.emoji||'🎙️')} ${x.esc(r.label||'')} · ${x.esc(j.emoji||'')} ${x.esc(j.label||'')}</small><h3>${x.esc(t.title)}</h3></article>`;
}

function stepCard(t,x){
  const st=current(t),steps=stepsOf(t),sh=data(x).shift||{};
  if(!st)return `<p class="rd-finished" role="status">✓ Xong việc · chất lượng ${x.esc(t.quality)}% · thưởng ${x.fmt(t.paid||0)} xu.</p>`;
  if(sh.open&&!sh.open.done)return '<p class="rd-finished" role="status">Kiểm phòng thu đầu ca xong rồi mới lên sóng.</p>';
  if(sh.outage?.state==='cut')return '<p class="rd-finished" role="status">⚡ Đang mất điện: xử lý sự cố trước rồi mới lên sóng tiếp.</p>';
  return `<section class="card rd-step" aria-labelledby="rd-step-title">
    <p class="rd-step-count" role="status">Bước ${t.at+1}/${steps.length} · chất lượng ${x.esc(t.quality??100)}%</p>
    <progress value="${t.at}" max="${steps.length}" aria-label="Tiến trình phiếu việc"></progress>
    <h3 id="rd-step-title">${x.esc(st.title)}</h3><p class="rd-evidence">${x.esc(st.evidence)}</p>
    ${stepBody(st,x,'rd_step',{task:t.id},t.id,t)}</section>`;
}

/* ------------------------------------------------------------ 📻 players' ads and songs (../v4/radio.js, game/radio_station.py)
 * The same entry in both layouts: the orders of other players waiting to go on air. The count is filled in after the render
 * from GET /api/radio/desk (cached half a minute). */
const deskEntry=x=>`<section class="card rd-air"><button type="button" class="btn ghost rd-air-go" data-action="radioDesk" data-coach="radio-desk" aria-label="${x.esc('Đơn lên sóng của người chơi')}">📻 Đơn lên sóng <b class="rd-air-n" data-rd-count></b></button>
  <p class="small">Người chơi đặt 📢 quảng cáo tiệm hoặc 🎵 bài hát tặng ở 🛎️ Phố dịch vụ. Bạn duyệt lời rồi bấm Lên sóng.</p></section>`;
let QN=null;
function deskCount(root,x){
  const b=root.querySelector?.('[data-rd-count]');if(!b)return;
  if(QN!==null){const t=QN?String(QN):'';if(b.textContent!==t)b.textContent=t;}
  if(b._asked)return;b._asked=true;
  import('../v4/radio.js').then(m=>m.queueCount({api:x.api})).then(n=>{QN=n;const t=n?String(n):'';if(b.isConnected&&b.textContent!==t)b.textContent=t;}).catch(()=>{});
}

const top=x=>`${introCard(x,'rd_intro','📻')}${deskCard(x,'rd_desk','Chuyện ở đài')}`;
const fresh=t=>!t.known&&!(t.at>0);

export default {
  id:'radio',css:true,
  next(t,x){return x.esc(!t.known?'Đọc phiếu việc':current(t)?.title||'Đã xong việc');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'rd_intro','📻'));
    if(!t.known)return wrap(top(x)+(fresh(t)?rolePicker(x):'')+shiftCard(x)+askCard(x,t,'Đọc phiếu việc')+deskEntry(x)+progress(x));
    return wrap(top(x)+shiftCard(x)+person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+briefCard(t,x)+stepCard(t,x)+
      (t.lines?.length?`<p class="rd-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+
      `<details class="rd-notebook"><summary>Sổ tay phát sóng Sóng Mây</summary>${notebook(x)}</details>`+progress(x));
  },
  // Compact layout: the notebook folds like on the work screen (the full layout keeps it open, as before).
  idle(x){return wrap(top(x)+rolePicker(x)+shiftCard(x)+deskEntry(x)+progress(x)+(clean()?`<details class="rd-notebook"><summary>Sổ tay phát sóng Sóng Mây</summary>${notebook(x)}</details>`:notebook(x)));},
  input(el,x){return kitInput(el,x);},
  meters(root,x){deskCount(root,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'radio',eyebrow:'Đài phát thanh Sóng Mây',title:'Sổ tay phát sóng',body:notebook(x)}):'';},
  actions:{...kitActions,
    async rdPick(d,el,x){
      const all=x.ui.rdPick??={},seq=all[d.key]||[],i=seq.indexOf(d.id);
      all[d.key]=i>=0?seq.filter(id=>id!==d.id):[...seq,d.id];x.render();
    },
    async rdClear(d,el,x){(x.ui.rdPick??={})[d.key]=[];x.render();},
    async amtSend(d,el,x){
      // Every answer here is a positive count of seconds; the server grades it.
      const raw=x.ui.amt?.[d.key],value=Number(raw===undefined||raw===''?d.def:raw);
      if(!Number.isInteger(value)||value<0||value>100000){x.toast?.('Nhập số nguyên từ 0 đến 100000.');return;}
      await x.send(d.cmd,{...JSON.parse(d.extra||'{}'),[d.field]:value});
    },
  },
  dock:[['car:notes','book','Sổ tay phát sóng','Kiểm phòng thu, bản tin, quảng cáo duyệt, lời chúc, mất điện'],['car:intro','question','Giới thiệu nghề','Phát thanh viên, hết thử việc làm DJ ca nhạc']],
};
