/** 🔬 Viện nghiên cứu Sông Mây: the shift's track (Giống cây, Công thức món, Sáng chế), the lab's opening safety and
 * closing checklists, then one job slip at a time, one step at a time. The server grades each step; a wrong one stays
 * open to fix and lowers the job's quality. 📬 Đơn nghiên cứu: other players' orders from 🛎️ Phố dịch vụ, three graded
 * research steps each (GET/POST /api/lab/…, game/research_lab.py); the last step delivers the result. */
import {data,cc,person,askCard,introCard,deskCard,kitActions,amountBox,kitInput,notesPage,act} from './street_kit.js';
import {clean,tip} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk research">${body}</div>`;
const stepsOf=t=>t.needs?.steps||[];
const current=t=>stepsOf(t)[t.at];
const keyOf=(id,st)=>`${id}:${st.id}`;
const TRACK_EMOJI={seed:'🌱',recipe:'🍳',invent:'🛠️'};

/** The track of this shift: Giống cây, Công thức món or Sáng chế (any of them, any day). */
function trackPicker(x){
  const d=data(x),tracks=cc(x).tracks||[],cur=d.track||'seed';
  const btn=r=>x.cmd(`<span aria-hidden="true">${x.esc(r.emoji||TRACK_EMOJI[r.id]||'')}</span><b>${x.esc(r.label)}</b><small>${x.esc(r.work)}</small>`,
    'rs_track',{track:r.id},`rs-track${r.id===cur?' on':''}`);
  return `<section class="rs-tracks" aria-label="Hướng nghiên cứu"><h4>Ca này bạn nghiên cứu</h4><div class="rs-track-row">${tracks.map(btn).join('')}</div></section>`;
}

function progress(x){
  const d=data(x),s=d.stats||{},p=d.progress||{};
  return `<details class="rs-progress"><summary>Hành trình ở viện · ${s.good||0} việc đạt · ${s.active_days||0} ngày · ${p.tracks||0}/3 hướng</summary>
    <p class="small">Việc đạt từ 90% chất lượng mới được ghi; ngày có việc đạt mới tính ngày.</p>
    <ul>${(p.milestones||[]).map(m=>`<li><b>${m.achieved?'✓ ':''}${x.esc(m.label)}</b><span>${Math.min(s.good||0,m.jobs)}/${m.jobs} việc · ${Math.min(s.active_days||0,m.days)}/${m.days} ngày · ${Math.min(p.tracks||0,m.tracks)}/${m.tracks} hướng</span></li>`).join('')}</ul></details>`;
}

function notebook(x){
  return `<ul class="rs-rules">${(cc(x).notebook||[]).map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`;
}

/** Ordered or multiple picks, sent as one value through `send(value)`: a game command or a lab order step. */
function pickStep(id,st,x,ordered,sendBtn){
  const key=keyOf(id,st),seq=((x.ui.rsPick??={})[key]||[]).filter(v=>(st.options||[]).some(o=>o.id===v));
  const opts=(st.options||[]).map(o=>{
    const i=seq.indexOf(o.id),on=i>=0;
    const mark=on?(ordered?`<i class="rs-num">${i+1}</i>`:'<i class="rs-num">✓</i>'):'';
    return act(x,`${mark}<span>${x.esc(o.label)}</span>`,'rsPick',{key,id:o.id},`rs-pick${on?' on':''}`,` aria-pressed="${on}"`);
  }).join('');
  const ready=ordered?seq.length===(st.options||[]).length:true;
  const value=ordered?seq:[...seq].sort();
  return `${tip(ordered?'Bấm lần lượt theo thứ tự; bấm lại để bỏ.':'Bấm để chọn hoặc bỏ chọn từng mục.','','p','small')}<div class="rs-picks">${opts}</div>
    <div class="rs-row">${act(x,'Làm lại','rsClear',{key},'ghost')}${sendBtn(ordered?'Xác nhận thứ tự':'Xác nhận lựa chọn',value,!ready)}</div>`;
}

function stepBody(st,x,cmd,payload,id,t){
  const send=(label,value,off)=>x.cmd(label,cmd,{...payload,step:st.id,value},'primary rs-send',off);
  if(st.type==='choice')return `<div class="rs-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),cmd,{...payload,step:st.id,value:o.id},'rs-option')).join('')}</div>`;
  if(st.type==='order')return pickStep(id,st,x,true,send);
  if(st.type==='multi')return pickStep(id,st,x,false,send);
  return amountBox(x,`rs-${id}-${st.id}`,0,{min:0,max:100000,label:'Con số ghi vào sổ',send:'Ghi vào sổ',cmd,payload:{...payload,step:st.id},field:'value',unit:st.unit||''});
}

/** The lab's opening safety and closing checklists. */
function shiftCard(x,t){
  const d=data(x),sh=d.shift||{};
  if(!sh.open)return '';
  const n=cc(x).night||{},fine=d.night_fine??n.min;
  const busy=t&&t.at>0&&current(t);
  let body='';
  if(!sh.open.done){
    const st=sh.open.step;
    body=`<h4>🥽 Đầu ca: ${x.esc(st.title)}</h4><p class="rs-evidence">${x.esc(st.evidence)}</p>${stepBody(st,x,'rs_shift',{part:'open'},'open',null)}`;
  }else if(!sh.close.done){
    const st=sh.close.step;
    const head=`<p class="small">✓ Đã làm an toàn đầu ca.${sh.safety==='pass'?' 🦺 Viện trưởng kiểm tra: đạt.':sh.safety==='fail'?' 🦺 Viện trưởng kiểm tra: bị nhắc nhở.':''}</p>`;
    const warn=`<p class="rs-night" role="note">🌙 Về mà chưa tắt thiết bị: đêm đó có thể hỏng mẫu (khoảng ${x.esc(n.chance??15)}% số lần). Tiền đền ${x.esc(fine)} xu (${x.esc(n.pct??8)}% lương ca, tối đa ${x.esc(n.cap??6)} xu) trừ vào ví, không bao giờ quá số tiền đang có.</p>`;
    body=busy?`${head}${warn}<p class="small">Xong việc đang làm rồi mới dọn phòng.</p>`:
      `${head}<details class="rs-close"${sh.close.at>0?' open':''}><summary>🔌 Cuối ca: cất mẫu và tắt thiết bị (${sh.close.at}/${sh.close.total})</summary>${warn}
        <h4>${x.esc(st.title)}</h4><p class="rs-evidence">${x.esc(st.evidence)}</p>${stepBody(st,x,'rs_shift',{part:'close'},'close',null)}</details>`;
  }else{
    body='<p class="small">✓ Đã làm an toàn đầu ca. ✓ Đã cất mẫu, khóa tủ hóa chất, tắt thiết bị. Việc còn lại để ca sau.</p>';
  }
  return `<section class="card rs-shift" aria-label="Việc đầu ca và cuối ca ở phòng thí nghiệm">${body}</section>`;
}

function briefCard(t,x){
  const j=t.job||{},r=t.track_info||{};
  return `<article class="rs-post"><small>${x.esc(r.emoji||'🔬')} ${x.esc(r.label||'')} · ${x.esc(j.emoji||'')} ${x.esc(j.label||'')}</small><h3>${x.esc(t.title)}</h3></article>`;
}

function stepCard(t,x){
  const st=current(t),steps=stepsOf(t);
  if(!st)return `<p class="rs-finished" role="status">✓ Xong việc · chất lượng ${x.esc(t.quality)}% · thưởng ${x.fmt(t.paid||0)} xu.</p>`;
  if(data(x).shift?.close?.done)return '<p class="rs-finished" role="status">Phòng thí nghiệm đã dọn và tắt thiết bị cho ca này. Việc còn lại để ca sau.</p>';
  const council=st.id.endsWith('.council');
  return `<section class="card rs-step${council?' council':''}" aria-labelledby="rs-step-title">
    <p class="rs-step-count" role="status">Bước ${t.at+1}/${steps.length} · chất lượng ${x.esc(t.quality??100)}%</p>
    <progress value="${t.at}" max="${steps.length}" aria-label="Tiến trình phiếu việc"></progress>
    <h3 id="rs-step-title">${council?'🧐 ':''}${x.esc(st.title)}</h3><p class="rs-evidence">${x.esc(st.evidence)}</p>
    ${stepBody(st,x,'rs_step',{task:t.id},t.id,t)}</section>`;
}

/* ------------------------------------------------------------ 📬 Đơn nghiên cứu (other players, Phố dịch vụ) */
async function loadLab(x,quiet=false){
  const ui=x.ui;if(ui.labBusy)return;
  ui.labBusy=true;if(!quiet)x.render();
  try{ui.lab=await x.api.json('/api/lab/orders');ui.labErr='';}
  catch(e){ui.labErr=e.message||'Chưa tải được đơn nghiên cứu.';}
  finally{ui.labBusy=false;ui.labAt=Date.now();x.render();}
}

async function labPost(x,route,body){
  const ui=x.ui;if(ui.labBusy)return;
  ui.labBusy=true;x.render();
  try{const r=await x.api.post('/api/lab/'+route,body);ui.lab=r;ui.labMsg=r.message||'';ui.labOk=r.correct!==false;x.api.refresh?.().catch(()=>{});}
  catch(e){ui.labMsg=e.message||'Chưa gửi được. Thử lại nhé.';ui.labOk=false;}
  finally{ui.labBusy=false;x.render();}
}

function labStep(o,x){
  const st=o.step;if(!st)return '<p class="small">✓ Xong ba bước, đang giao kết quả.</p>';
  const last=o.at===o.total-1;
  const nameBox=last?`<label class="rs-name">Đặt tên kết quả (không bắt buộc)<input type="text" maxlength="24" data-car="labName" data-order="${x.esc(o.id)}" value="${x.esc(x.ui.labName?.[o.id]||'')}" placeholder="${o.service==='giong'?'vd: Mây chịu hạn':o.service==='mon'?'vd: Phở thơm quế':'vd: Quạt Mây Mini'}"></label>`:'';
  const send=(label,value,off)=>act(x,label,'labSend',{order:o.id,step:st.id,value:JSON.stringify(value)},'primary rs-send',off?' disabled':'');
  let body;
  if(st.type==='choice')body=`<div class="rs-options">${(st.options||[]).map(op=>send(x.esc(op.label),op.id,false).replace('primary rs-send','rs-option')).join('')}</div>`;
  else if(st.type==='order'||st.type==='multi')body=pickStep(o.id,st,x,st.type==='order',send);
  else{
    const v=x.ui.labNum?.[o.id]??'';
    body=`<div class="rs-row rs-num-row"><label class="rs-num-in">Con số ghi vào sổ <input type="number" inputmode="numeric" min="0" max="100000" data-car="labNum" data-order="${x.esc(o.id)}" value="${x.esc(v)}"> <small>${x.esc(st.unit||'')}</small></label>${act(x,'Ghi vào sổ','labSendNum',{order:o.id,step:st.id},'primary rs-send')}</div>`;
  }
  return `<p class="rs-step-count">Bước ${o.at+1}/${o.total} · chất lượng ${x.esc(o.quality)}%</p><h4>${x.esc(st.title)}</h4><p class="rs-evidence">${x.esc(st.evidence)}</p>${nameBox}${body}`;
}

function labCard(x){
  const ui=x.ui,v=ui.lab;
  if(!v&&!ui.labBusy&&!ui.labErr&&!(ui.labAt&&Date.now()-ui.labAt<5000))setTimeout(()=>loadLab(x,true),0);
  const list=v?.orders||[];
  const head=`<summary>📬 Đơn nghiên cứu của người chơi${list.length?` · ${list.length}`:''}</summary>`;
  if(v?.off)return `<details class="rs-lab" open>${head}<p class="small">Viện tạm nghỉ nhận đơn của người chơi.</p></details>`;
  const msg=ui.labMsg?`<p class="rs-lab-msg ${ui.labOk?'good':'bad'}" role="status">${x.esc(ui.labMsg)}</p>`:'';
  const rows=list.map(o=>`<article class="rs-order"><header><span aria-hidden="true">${x.esc(o.icon)}</span><b>${x.esc(o.name)}</b><small>${x.esc(o.buyer)} · ${x.fmt(o.price)} xu</small></header>
    ${o.note?`<p class="rs-note">“${x.esc(o.note)}”</p>`:''}
    ${o.status==='held'?`<div class="rs-row">${act(x,'Nhận đơn','labTake',{order:o.id},'primary')}</div>`:labStep(o,x)}</article>`).join('');
  const empty=!list.length?`<p class="small">${ui.labBusy?'Đang tải…':ui.labErr?x.esc(ui.labErr):'Chưa có đơn nào. Bật dịch vụ ở Phố dịch vụ để người chơi khác đặt giống, công thức hay đồ sáng chế.'}</p>`:'';
  const services=(v?.services||[]).map(s=>`<li>${x.esc(s.icon)} <b>${x.esc(s.name)}</b> · ${x.esc(s.desc)}</li>`).join('');
  return `<details class="rs-lab"${list.length?' open':''}>${head}${msg}${rows}${empty}
    ${services?`<ul class="rs-services">${services}</ul>`:''}
    <div class="rs-row">${act(x,'↻ Tải lại','labReload',{},'ghost small')}<button type="button" class="btn ghost small" data-action="svcMarket" data-tab="mine">🛎️ Dịch vụ của tôi</button></div></details>`;
}

const top=x=>`${introCard(x,'rs_intro','🔬')}${deskCard(x,'rs_desk','Chuyện ở viện')}`;
const fresh=t=>!t.known&&!(t.at>0);

export default {
  id:'research',css:true,
  next(t,x){return x.esc(!t.known?'Đọc phiếu việc':current(t)?.title||'Đã xong việc');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'rs_intro','🔬'));
    if(!t.known)return wrap(top(x)+(fresh(t)?trackPicker(x):'')+shiftCard(x,null)+askCard(x,t,'Đọc phiếu việc')+labCard(x)+progress(x));
    return wrap(top(x)+shiftCard(x,t)+person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+briefCard(t,x)+stepCard(t,x)+
      (t.lines?.length?`<p class="rs-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+labCard(x)+
      `<details class="rs-notebook"><summary>Sổ tay Viện Sông Mây</summary>${notebook(x)}</details>`+progress(x));
  },
  idle(x){return wrap(top(x)+trackPicker(x)+shiftCard(x,null)+labCard(x)+progress(x)+(clean()?`<details class="rs-notebook"><summary>Sổ tay Viện Sông Mây</summary>${notebook(x)}</details>`:notebook(x)));},
  input(el,x){
    if(el.dataset?.car==='labName'){(x.ui.labName??={})[el.dataset.order]=el.value;return true;}
    if(el.dataset?.car==='labNum'){(x.ui.labNum??={})[el.dataset.order]=el.value;return true;}
    return kitInput(el,x);
  },
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'research',eyebrow:'Viện nghiên cứu Sông Mây',title:'Sổ tay của viện',body:notebook(x)}):'';},
  actions:{...kitActions,
    async rsPick(d,el,x){
      const all=x.ui.rsPick??={},seq=all[d.key]||[],i=seq.indexOf(d.id);
      all[d.key]=i>=0?seq.filter(id=>id!==d.id):[...seq,d.id];x.render();
    },
    async rsClear(d,el,x){(x.ui.rsPick??={})[d.key]=[];x.render();},
    async amtSend(d,el,x){
      const raw=x.ui.amt?.[d.key],value=Number(raw===undefined||raw===''?d.def:raw);
      if(!Number.isInteger(value)||value<0||value>100000){x.toast?.('Nhập số nguyên từ 0 đến 100000.');return;}
      await x.send(d.cmd,{...JSON.parse(d.extra||'{}'),[d.field]:value});
    },
    async labReload(d,el,x){x.ui.labMsg='';await loadLab(x);},
    async labTake(d,el,x){await labPost(x,'take',{order:d.order});},
    async labSend(d,el,x){
      const body={order:d.order,step:d.step,value:JSON.parse(d.value)};
      const name=x.ui.labName?.[d.order];if(name)body.name=name;
      await labPost(x,'step',body);
    },
    async labSendNum(d,el,x){
      const raw=x.ui.labNum?.[d.order],value=Number(raw);
      if(raw===undefined||raw===''||!Number.isInteger(value)||value<0||value>100000){x.toast?.('Nhập số nguyên từ 0 đến 100000.');return;}
      const body={order:d.order,step:d.step,value};
      const name=x.ui.labName?.[d.order];if(name)body.name=name;
      await labPost(x,'step',body);
    },
  },
  dock:[['car:notes','book','Sổ tay của viện','An toàn, đối chứng, nếm mù, nhãn, thử mẫu, hồ sơ sáng chế, hội đồng'],['car:intro','question','Giới thiệu nghề','Giống cây, công thức món hoặc sáng chế']],
};
