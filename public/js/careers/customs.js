/** 🛃 Hải quan cửa khẩu Bến Mây — a day at the Chi cục Hải quan (server: game/careers/customs.py).
 * Each file is a list of steps with its evidence (the lane the system gave, the paper file, the goods, the scan, the
 * duty in numbers, the decision); a slip on an evidence step is answered again, the decision is final. An offer may
 * come before the decision (refuse and report, or go along). After the shift people write in (📮 phản ánh): accept,
 * dismiss, or send to Công an Thành phố. Officers past Tập sự inspect the warehouses of shops on the street
 * (v4/hq.js, game/hq_ops.py). The server decides everything; nothing here says which option is right. */
import {stepRows,nextHint} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,act,pane,introCard,askCard,bottom,kitActions} from './street_kit.js';
import {boardSVG} from '../v4/insignia.js';
import {tip} from '../ui-kit.js';   // compact layout: the how-to lines go to "?" (owner 19/10: every career has both sides)   // 🎖️ cấp hiệu (game/org.py)

const KIND={lane:['🚦','Phân luồng, kiểm tra'],smuggle:['🔦','Chống buôn lậu'],tax:['🧮','Thuế xuất nhập khẩu'],control:['🛡️','Kiểm soát']};
const NUMERIC=new Set(['duty','vat']);
const step=t=>(t.needs?.steps||[])[t.at]||null;
const lanes=x=>cc(x).lanes||{};

/* ------------------------------------------------------------ cards */
function fileCard(t,x){
  const n=t.needs||{},[e,k]=KIND[t.kind]||['📄',''],l=n.lane?lanes(x)[n.lane]:null;
  const tags=[`<span class="tag blue">${x.esc(e)} ${x.esc(k)}</span>`,l&&!n.pax?`<span class="tag hq-lane hq-${x.esc(n.lane)}">${x.esc(l.emoji)} ${x.esc(l.name)}</span>`:'',
    n.value?`<span class="tag">💱 ${x.fmt(n.value)} xu</span>`:''].join('');
  return `<article class="card sk-ticket hq-file"><div class="row"><span class="hq-big" aria-hidden="true">${x.esc(e)}</span><div class="grow"><h3>${x.esc(t.title)}</h3>
    <p class="small">${x.esc(t.opening)}</p>${n.declared?`<p class="small hq-decl">📄 ${x.esc(n.declared)}</p>`:''}<div class="hq-tags">${tags}</div></div></div></article>`;
}
function stepCard(t,x){
  const s=step(t);if(!s)return '';
  const pay=v=>({task:t.id,step:s.id,value:v});
  let body;
  if(NUMERIC.has(s.kind)){
    const v=(x.ui.num??={})[`${t.id}:${s.id}`]??'';
    body=`<label class="hq-num"><span>Số xu</span><input class="input" type="number" inputmode="numeric" min="0" step="1" value="${x.esc(v)}" data-car="num" data-key="${x.esc(`${t.id}:${s.id}`)}" aria-label="${x.esc(s.title)}"></label>
      ${x.cmd('✍️ Ghi vào tờ khai','hq_step',pay(Number(v)),'primary full',v===''||!Number.isInteger(Number(v)))}`;
  }else body=`<div class="sk-opts">${(s.options||[]).map(o=>x.cmd(`<span class="sk-opt-label">${x.esc(o.label)}</span>`,'hq_step',pay(o.id),`sk-opt${s.kind==='offer'?' hq-offer':''}`)).join('')}</div>`;
  const head=s.kind==='offer'?`<h4>🤫 ${x.esc(s.title)}</h4>`:`<h4>${s.final?'⚖️':'🔎'} ${x.esc(s.title)}</h4>`;
  return `<section class="card hq-step${s.kind==='offer'?' hq-tempt':''}">${head}<p class="hq-ev">${x.esc(s.evidence)}</p>${body}</section>`;
}
function trail(t,x){
  const steps=t.needs?.steps||[];if(!t.at&&!(t.lines||[]).length)return '';
  const done=steps.slice(0,t.at).map(s=>`<li>✓ ${x.esc(s.title)}${t.work?.[s.id]!=null&&NUMERIC.has(s.kind)?`: <b>${x.fmt(t.work[s.id])} xu</b>`:''}</li>`).join('');
  const log=(t.lines||[]).slice(-4).map(l=>`<li class="muted">${x.esc(l)}</li>`).join('');
  return `<section class="card hq-trail"><h4>📋 Biên bản</h4><ul class="small">${done}${log}</ul></section>`;
}
function notebook(x){
  const rows=cc(x).notebook||[];if(!rows.length)return '';
  return pane(x,'hq-notebook','📘 <b>Sổ tay nghiệp vụ</b>',`<ul class="small hq-notes">${rows.map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul>`,false,'hq-nb');
}
function rulesCard(x){
  const rows=cc(x).rules||[];if(!rows.length)return '';
  return `<details class="card hq-rules"><summary><b>📜 Quy định công chức Hải quan</b> <small class="muted">đọc trước khi làm</small></summary><ul class="small">${rows.map(r=>`<li>${x.esc(r.icon||'•')} ${x.esc(r.text)}</li>`).join('')}</ul></details>`;
}
/** 📮 What people wrote after a shift (game/npc_complaints.py): the kind shows only once decided. */
function complaints(x){
  const d=data(x),rows=d.cmp||[],ops=cc(x).ops||{};if(!rows.length)return '';
  const open=rows.filter(r=>r.st==='open');
  const li=r=>`<li class="hq-cmp${r.st==='open'?' open':''}"><p><b>${x.esc(r.who)}</b> <small class="muted">${x.esc(r.role)} · ngày ${x.esc(r.d)}</small></p><p>“${x.esc(r.text)}”</p>
    ${r.st==='open'?`<div class="sk-opts hq-cmp-ops">${Object.entries(ops).map(([k,l])=>x.cmd(`<span class="sk-opt-label">${x.esc(l)}</span>`,'hq_cmp',{id:r.id,op:k},'sk-opt')).join('')}</div>`
      :`<p class="small">${x.esc(r.kind||'')} · ${x.esc(r.out)}</p>`}</li>`;
  return `<section class="card hq-cmps"><h4>📮 Phản ánh của người dân${open.length?` <span class="tag amber">${open.length} mới</span>`:''}</h4>
    <ul class="hq-cmp-list">${[...open,...rows.filter(r=>r.st!=='open').slice(-3)].map(li).join('')}</ul>
    ${tip('Phản ánh đúng thì ghi nhận; không liên quan thì gỡ; đòi tiền, dọa bóc phốt thì gửi Công an Thành phố. Gỡ hay tố cáo một phản ánh đúng là vi phạm.','📮 Phản ánh','p','small muted')}</section>`;
}
function rankLine(x){
  const o=x.room.promo?.org;if(!o?.grade)return '';
  const svg=(()=>{try{return boardSVG(o.org||'hq',o.grade.id,{size:28})||'';}catch{return '';}})();
  return `<p class="hq-rank">${svg}<b>${x.esc(o.grade.name||'')}</b>${o.post?.name?` · ${x.esc(o.post.name)}`:''}${typeof o.svc==='number'?` · 📁 ${o.svc} lần vi phạm trong hồ sơ công tác`:''}</p>`;
}
function inspectCard(x){
  const o=x.room.promo?.org;if(!o||o.susp||!o.post?.id||o.post.id==='hq_ts')return '';
  return `<section class="card hq-inspect"><h4>🏪 Kiểm tra kho cửa hàng</h4>${tip('Đọc sổ thuế, kho hàng của các cửa hàng trên phố; đề xuất biện pháp có căn cứ, qua cấp trên duyệt.','🏪 Kiểm tra kho','p','small')}${act(x,'🔎 Mở danh sách','desk',{},'primary full')}</section>`;
}

/* ------------------------------------------------------------ the guide */
function guide(t,x){
  const d=data(x);
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'hq_intro',payload:{},label:'🛃 Vào ca thôi!'}}],final:null};
  if(!t.known)return {steps:[{ok:null,label:'Đọc hồ sơ',go:{cmd:'ask',payload:{task:t.id},label:'📄 Đọc hồ sơ'}}],final:null,pulse:'.sk-ask'};
  const steps=(t.needs?.steps||[]).map((s,i)=>({ok:i<t.at?true:null,label:s.kind==='offer'?'Trả lời lời đề nghị':s.title,go:i===t.at?{sel:'.hq-step',label:`👉 ${s.title}`}:null,pulse:''}));
  return {steps,final:null};
}
const hint=(g,x)=>nextHint(x,g.steps,{pulse:g.pulse});
const top=x=>`${introCard(x,'hq_intro','🛃')}${rankLine(x)}`;

export default {
  id:'customs',
  css:true,
  next(t,x){const s=step(t);return !t.known?'Đọc hồ sơ':s?x.esc(s.title):'Khép hồ sơ';},
  job(t,x){
    const g=guide(t,x),d=data(x),head=top(x);
    if(!d.intro||x.ui.intro)return `<div class="career-job sk hq">${hint(g,x)}${head}${bottom(x,g)}</div>`;
    if(!t.known)return `<div class="career-job sk hq">${hint(g,x)}${head}${askCard(x,t,'📄 Đọc hồ sơ')}${bottom(x,g)}</div>`;
    const main=`${fileCard(t,x)}${stepCard(t,x)}${trail(t,x)}`;
    const side=`${stepRows(x,g.steps,'Các bước',{chip:true})}${notebook(x)}`;
    return `<div class="career-job sk hq">${hint(g,x)}${head}<div class="workbench"><section class="wb-main">${main}</section><aside class="wb-side">${side}</aside></div>${complaints(x)}${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),head=top(x);
    if(!d.intro||x.ui.intro){const g={steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'hq_intro',payload:{},label:'🛃 Vào ca thôi!'}}],final:null};
      return `<div class="career-job sk hq">${hint(g,x)}${head}${bottom(x,g)}</div>`;}
    const td=d.today||{},st=d.stats||{};
    const tiles=[[td.jobs||0,'hồ sơ'],[td.clean||0,'không sai sót'],[td.seized||0,'vụ tạm giữ đúng'],[x.fmt(td.duty||0),'xu thu ngân sách']];
    const ms=(d.progress?.milestones||[]).map(m=>`<li>${m.achieved?'🏅':'▫️'} ${x.esc(m.label)} <small class="muted">${m.jobs} hồ sơ đạt, ${m.days} ngày</small></li>`).join('');
    return `<div class="career-job sk hq">${head}<section class="card hq-today"><h4>🛃 Ca hôm nay</h4><div class="hq-tiles">${tiles.map(([v,l])=>`<div><b>${x.esc(v)}</b><small>${x.esc(l)}</small></div>`).join('')}</div>
      ${tip(`Cả nghề: ${x.fmt(st.jobs||0)} hồ sơ · ${x.fmt(st.clean||0)} hồ sơ đạt · ${x.fmt(st.active_days||0)} ngày làm tốt`,'','p','small muted')}</section>
      ${complaints(x)}${inspectCard(x)}${ms?`<section class="card"><h4>🎖️ Mốc nghề</h4><ul class="small">${ms}</ul></section>`:''}${notebook(x)}${rulesCard(x)}</div>`;
  },
  tick(root){keepBarAboveFooter(root);},
  input(el,x,type){
    if(el.dataset?.car!=='num')return false;
    (x.ui.num??={})[el.dataset.key]=el.value;
    if(type==='change')x.render();
    return true;
  },
  actions:{...kitActions,
    async desk(d,el,x){try{const m=await import('../v4/hq.js');m.openDesk({api:x.api});}catch(e){x.toast(e.message||'Chưa mở được.','bad');}},
  },
};
