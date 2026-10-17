/** Nhà hàng tiệc Hồng Mây: the shift's role (Phụ bếp, Đầu bếp after probation, Sảnh sự kiện), the kitchen's opening
 * hygiene and closing power-off checklists, then one job slip at a time, one step at a time. The server grades each step;
 * a wrong one stays open to fix and lowers the job's quality. */
import {data,cc,person,askCard,introCard,deskCard,kitActions,amountBox,kitInput,notesPage,act} from './street_kit.js';

const wrap=body=>`<div class="career-job sk banquet">${body}</div>`;
const stepsOf=t=>t.needs?.steps||[];
const current=t=>stepsOf(t)[t.at];
const keyOf=(id,st)=>`${id}:${st.id}`;
const ROLE_EMOJI={prep:'🥕',chef:'👨‍🍳',hall:'🎀'};

function rushBanner(x,r){
  if(!r)return '';
  return `<p class="bq-rush" role="status"><span aria-hidden="true">${x.esc(r.emoji)}</span> <b>${x.esc(r.label)}</b> · ${x.esc(r.note)}</p>`;
}

/** The role of this shift: Phụ bếp, Đầu bếp (locked until the probation is done) or Sảnh sự kiện. */
function rolePicker(x){
  const d=data(x),roles=cc(x).roles||[],p=d.progress||{},cur=d.role||'prep';
  const btn=r=>{
    const locked=r.id==='chef'&&!d.promoted,on=r.id===cur;
    const sub=locked?`Mở sau ${p.probation||3} ca phụ bếp đạt (${p.prep_days||0}/${p.probation||3})`:r.work;
    return x.cmd(`<span aria-hidden="true">${x.esc(r.emoji||ROLE_EMOJI[r.id]||'')}</span><b>${x.esc(r.label)}</b><small>${x.esc(sub)}</small>`,
      'bq_role',{role:r.id},`bq-role${on?' on':''}${locked?' locked':''}`,locked);
  };
  return `<section class="bq-roles" aria-label="Vị trí trong ca"><h4>Ca này bạn làm</h4><div class="bq-role-row">${roles.map(btn).join('')}</div></section>`;
}

function progress(x){
  const d=data(x),s=d.stats||{},p=d.progress||{};
  const prob=d.promoted?'<p class="small">👨‍🍳 Đã lên Đầu bếp.</p>':`<p class="small">🥕 Thử việc phụ bếp: ${p.prep_days||0}/${p.probation||3} ca bếp đạt.</p>`;
  return `<details class="bq-progress"><summary>Hành trình Hồng Mây · ${s.good||0} việc đạt · ${s.active_days||0} ngày · ${p.roles||0}/3 vị trí</summary>${prob}
    <p class="small">Việc đạt từ 90% chất lượng mới được ghi; ngày có việc đạt mới tính ngày.</p>
    <ul>${(p.milestones||[]).map(m=>`<li><b>${m.achieved?'✓ ':''}${x.esc(m.label)}</b><span>${Math.min(s.good||0,m.jobs)}/${m.jobs} việc · ${Math.min(s.active_days||0,m.days)}/${m.days} ngày · ${Math.min(p.roles||0,m.roles)}/${m.roles} vị trí</span></li>`).join('')}</ul></details>`;
}

function notebook(x){
  return `<ul class="bq-rules">${(cc(x).notebook||[]).map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`;
}

/** Ordered or multiple picks, sent as one value: `cmd` with `payload` + {step, value}. */
function pickStep(id,st,x,ordered,cmd,payload){
  const key=keyOf(id,st),seq=((x.ui.bqPick??={})[key]||[]).filter(v=>(st.options||[]).some(o=>o.id===v));
  const opts=(st.options||[]).map(o=>{
    const i=seq.indexOf(o.id),on=i>=0;
    const mark=on?(ordered?`<i class="bq-num">${i+1}</i>`:'<i class="bq-num">✓</i>'):'';
    return act(x,`${mark}<span>${x.esc(o.label)}</span>`,'bqPick',{key,id:o.id},`bq-pick${on?' on':''}`,` aria-pressed="${on}"`);
  }).join('');
  const ready=ordered?seq.length===(st.options||[]).length:true;
  const value=ordered?seq:[...seq].sort();
  const send=x.cmd(ordered?'Xác nhận thứ tự':'Xác nhận lựa chọn',cmd,{...payload,step:st.id,value},'primary bq-send',!ready);
  return `<p class="small">${ordered?'Bấm lần lượt theo thứ tự; bấm lại để bỏ.':'Bấm để chọn hoặc bỏ chọn từng món.'}</p><div class="bq-picks">${opts}</div>
    <div class="bq-row">${act(x,'Làm lại','bqClear',{key},'ghost')}${send}</div>`;
}

function choiceStep(st,x,cmd,payload){
  return `<div class="bq-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),cmd,{...payload,step:st.id,value:o.id},'bq-option')).join('')}</div>`;
}

function numberStep(t,st,x){
  return amountBox(x,`bq-${t.id}-${st.id}`,0,{min:0,max:100000,label:'Con số ghi vào phiếu',send:'Ghi vào phiếu',
    cmd:'bq_step',payload:{task:t.id},field:'value',unit:st.unit||''});
}

function stepBody(st,x,cmd,payload,id,t){
  if(st.type==='choice')return choiceStep(st,x,cmd,payload);
  if(st.type==='order')return pickStep(id,st,x,true,cmd,payload);
  if(st.type==='multi')return pickStep(id,st,x,false,cmd,payload);
  return numberStep(t,st,x);
}

/** 📋 The sheet on the kitchen door (the notebook's own line): the order the step asks for, one tap away. */
function poster(x,head){
  const line=(cc(x).notebook||[]).find(n=>String(n).startsWith(head));
  return line?`<details class="bq-poster"><summary>📋 Tờ dán cửa bếp</summary><p>${x.esc(line)}</p></details>`:'';
}

/** The kitchen's opening hygiene and closing power-off checklists (a kitchen role, or once the kitchen was used). */
function shiftCard(x,t){
  const d=data(x),sh=d.shift||{},kitchen=(d.role||'prep')!=='hall'||sh.kitchen;
  if(!kitchen||!sh.open)return '';
  const f=cc(x).fire||{},fine=d.fire_fine??f.min;
  const busy=t&&t.at>0&&current(t)&&t.role_info?.kitchen;
  let body='';
  if(!sh.open.done){
    const st=sh.open.step;
    body=`<h4>🧼 Đầu ca: ${x.esc(st.title)}</h4><p class="bq-evidence">${x.esc(st.evidence)}</p>${poster(x,'Đầu ca bếp:')}${stepBody(st,x,'bq_shift',{part:'open'},'open',null)}`;
  }else if(!sh.close.done){
    const st=sh.close.step;
    const head=`<p class="small">✓ Đã vệ sinh đầu ca.${sh.insp==='pass'?' 🔎 Đoàn kiểm tra: đạt.':sh.insp==='fail'?' 🔎 Đoàn kiểm tra: bị nhắc nhở.':''}</p>`;
    const warn=`<p class="bq-fire" role="note">🔥 Về mà chưa tắt thiết bị điện: đêm đó có thể cháy bếp (khoảng ${x.esc(f.chance??40)}% số lần). Tiền đền bù ${x.esc(fine)} xu (${x.esc(f.pct??8)}% lương ca, tối đa ${x.esc(f.cap??6)} xu) trừ vào ví, không bao giờ quá số tiền đang có.</p>`;
    body=busy?`${head}${warn}<p class="small">Xong món đang làm rồi mới dọn bếp.</p>`:
      `${head}<details class="bq-close"${sh.close.at>0?' open':''}><summary>🔌 Cuối ca: dọn bếp và tắt điện (${sh.close.at}/${sh.close.total})</summary>${warn}
        <h4>${x.esc(st.title)}</h4><p class="bq-evidence">${x.esc(st.evidence)}</p>${poster(x,'Cuối ca bếp:')}${stepBody(st,x,'bq_shift',{part:'close'},'close',null)}</details>`;
  }else{
    body='<p class="small">✓ Đã vệ sinh đầu ca. ✓ Đã dọn bếp, khóa gas, tắt điện. Việc bếp còn lại để ca sau.</p>';
  }
  return `<section class="card bq-shift" aria-label="Việc đầu ca và cuối ca bếp">${body}</section>`;
}

/** The event brief: the client's ask and the halls with their capacity and rent. */
function eventBrief(t,x){
  const n=t.needs||{};
  if(t.job?.id!=='event'||!n.halls)return '';
  return `<section class="bq-brief" aria-label="Phiếu đặt tiệc"><h4>${x.esc(n.emoji||'🎀')} ${x.esc(n.event_name||'')} · ${x.esc(n.client||'')}</h4>
    <ul><li>Khoảng ${x.esc(n.guests)} khách</li><li>${x.esc(n.concept_wish)}</li><li>Ngân sách ${x.esc(n.budget)} xu mỗi bàn · ${x.esc(n.rule)}</li><li>${x.esc(n.limit)}</li></ul>
    <table class="bq-halls"><caption>Phòng tiệc</caption><thead><tr><th scope="col">Phòng</th><th scope="col">Tối đa</th><th scope="col">Thuê</th></tr></thead>
    <tbody>${n.halls.map(h=>`<tr><th scope="row">${x.esc(h.label)}</th><td>${x.esc(h.tables)} bàn</td><td>${x.esc(h.rent)} xu</td></tr>`).join('')}</tbody></table></section>`;
}

function briefCard(t,x){
  const j=t.job||{},r=t.role_info||{};
  return `<article class="bq-post"><small>${x.esc(r.emoji||'🍲')} ${x.esc(r.label||'')} · ${x.esc(j.emoji||'')} ${x.esc(j.label||'')}</small><h3>${x.esc(t.title)}</h3></article>`;
}

function stepCard(t,x){
  const st=current(t),steps=stepsOf(t);
  if(!st)return `<p class="bq-finished" role="status">✓ Xong việc · chất lượng ${x.esc(t.quality)}% · thưởng ${x.fmt(t.paid||0)} xu.</p>`;
  const d=data(x),sh=d.shift||{};
  if(t.role_info?.kitchen&&sh.close?.done)return '<p class="bq-finished" role="status">Bếp đã dọn và tắt điện cho ca này. Việc bếp còn lại để ca sau.</p>';
  return `<section class="card bq-step" aria-labelledby="bq-step-title">
    <p class="bq-step-count" role="status">Bước ${t.at+1}/${steps.length} · chất lượng ${x.esc(t.quality??100)}%</p>
    <progress value="${t.at}" max="${steps.length}" aria-label="Tiến trình phiếu việc"></progress>
    <h3 id="bq-step-title">${x.esc(st.title)}</h3><p class="bq-evidence">${x.esc(st.evidence)}</p>
    ${stepBody(st,x,'bq_step',{task:t.id},t.id,t)}</section>`;
}

const top=x=>`${introCard(x,'bq_intro','👨‍🍳')}${deskCard(x,'bq_desk','Chuyện ở nhà hàng')}`;
const fresh=t=>!t.known&&!(t.at>0);

export default {
  id:'banquet',css:true,
  next(t,x){return x.esc(!t.known?'Đọc phiếu việc':current(t)?.title||'Đã xong việc');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'bq_intro','👨‍🍳'));
    if(!t.known)return wrap(top(x)+rushBanner(x,data(x).rush)+(fresh(t)?rolePicker(x):'')+shiftCard(x,null)+askCard(x,t,'Đọc phiếu việc')+progress(x));
    return wrap(top(x)+rushBanner(x,t.rush_info)+shiftCard(x,t)+person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+briefCard(t,x)+
      eventBrief(t,x)+stepCard(t,x)+
      (t.lines?.length?`<p class="bq-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+
      `<details class="bq-notebook"><summary>Sổ bếp và sổ sảnh Hồng Mây</summary>${notebook(x)}</details>`+progress(x));
  },
  idle(x){return wrap(top(x)+rushBanner(x,data(x).rush)+rolePicker(x)+shiftCard(x,null)+progress(x)+notebook(x));},
  input(el,x){return kitInput(el,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'banquet',eyebrow:'Nhà hàng tiệc Hồng Mây',title:'Sổ bếp và sổ sảnh',body:notebook(x)}):'';},
  actions:{...kitActions,
    async bqPick(d,el,x){
      const all=x.ui.bqPick??={},seq=all[d.key]||[],i=seq.indexOf(d.id);
      all[d.key]=i>=0?seq.filter(id=>id!==d.id):[...seq,d.id];x.render();
    },
    async bqClear(d,el,x){(x.ui.bqPick??={})[d.key]=[];x.render();},
    async amtSend(d,el,x){
      // Zero can be typed, but every answer here is a positive count; the server grades it.
      const raw=x.ui.amt?.[d.key],value=Number(raw===undefined||raw===''?d.def:raw);
      if(!Number.isInteger(value)||value<0||value>100000){x.toast?.('Nhập số nguyên từ 0 đến 100000.');return;}
      await x.send(d.cmd,{...JSON.parse(d.extra||'{}'),[d.field]:value});
    },
  },
  dock:[['car:notes','book','Sổ bếp và sổ sảnh','Vệ sinh, thớt màu, nhiệt độ, sảnh tiệc và tắt điện'],['car:intro','question','Giới thiệu nghề','Bếp (phụ bếp → đầu bếp) hoặc sảnh sự kiện']],
};
