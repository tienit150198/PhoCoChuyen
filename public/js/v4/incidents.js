/** Chuyện đời (incidents): fines, the ward police, tax, theft, scams and people
 * who cross a line. A decision card pops up when the server opens one; the
 * player picks one of 2–4 choices with visible stakes; the result card shows
 * what it cost and how the street sees you now. Render-only: every rule, roll
 * and amount lives in game/incidents.py. */
import {icon,escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const signed=n=>`${n<0?'−':'+'}${fmt(Math.abs(n))}`;
const CAT_NAMES={fine:'Tiền phạt',tax:'Thuế',theft_loss:'Mất trộm',scam_loss:'Bị lừa',bad_debt:'Bị quỵt',under_table:'Chi không chứng từ',legal:'Luật sư',
  compensation:'Bồi thường',recovery:'Thu hồi',damage:'Đồ bị phá hỏng',insurance_recovery:'Bảo hiểm chi trả',repair:'Sửa chữa',security:'An ninh',rent:'Tiền thuê',gift:'Quà',incident:'Chuyện đời',
  service:'Tiền dịch vụ',commission:'Hoa hồng',security_reward:'Thưởng khu phố',stock:'Nhập hàng',upgrade:'Nâng cấp',office:'Giấy tờ',
  refund:'Hoàn tiền',marketing:'Quảng bá',promotion:'Khuyến mãi'};
const catName=c=>CAT_NAMES[c]||'Chuyện đời';
const head=(title,eyebrow)=>`<header class="sheet-head"><div class="grow"><span class="eyebrow">${eyebrow}</span><h2>${title}</h2></div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const btn=(label,action,data={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${disabled?' disabled':''}>${label}</button>`;

function stake(x){
  const where=x.where==='wallet'?'ví':'quỹ';
  return `<span class="inc-stake ${x.amount<0?'out':'in'}">${signed(x.amount)} xu ${where}</span>`;
}
function line(x){
  const where=x.where==='wallet'?'Ví của bạn':'Quỹ nơi làm';
  return `<li class="${x.amount<0?'out':'in'}"><span>${where} · ${esc(catName(x.cat))}</span><b>${signed(x.amount)} xu</b></li>`;
}
function trustChip(n){
  if(!n)return '';
  return `<span class="inc-trust ${n>0?'up':'down'}">${n>0?'Uy tín tăng':'Uy tín giảm'} ${n>0?'+':'−'}${Math.abs(n)}</span>`;
}
const verdict=g=>g===true?['good','Xử lý đúng mực']:g===false?['bad','Để lại hậu quả']:['mid','Tạm ổn'];

function trustMeter(box){
  const t=Math.max(0,Math.min(100,box.trust|0));
  return `<div class="inc-meter" role="img" aria-label="Uy tín với khu phố: ${t} trên 100, ${esc(box.trust_name)}"><div class="row spread"><b>${icon('shield',15)} Uy tín với khu phố</b><span>${esc(box.trust_name)}</span></div><div class="inc-bar"><i style="width:${Math.max(4,t)}%"></i></div></div>`;
}

function decisionView(x){
  const ticket=x.ticket?`<div class="inc-ticket"><span class="inc-stamp">BIÊN BẢN</span><dl><dt>Lỗi</dt><dd>${esc(x.ticket.violation)}</dd><dt>Mức phạt</dt><dd><b>${fmt(x.ticket.amount)} xu</b></dd></dl></div>`:'';
  const ev=x.evidence.length?`<h4 class="section-title">Dữ kiện</h4><ul class="inc-evidence">${x.evidence.map(t=>`<li>${icon('search',14)}<span>${esc(t)}</span></li>`).join('')}</ul>`:'';
  const choices=x.options.map(o=>{
    const stakes=o.stakes.length?o.stakes.map(stake).join(''):'<span class="inc-stake none">Không tốn tiền</span>';
    return `<button type="button" class="inc-choice" data-action="incChoose" data-id="${esc(x.id)}" data-option="${esc(o.id)}" data-label="${esc(o.label)}"${o.affordable?'':' disabled'}><strong>${esc(o.label)}</strong><span class="inc-stakes">${stakes}${o.hint&&!/xu$/.test(o.hint)?`<small>${esc(o.hint)}</small>`:''}${o.affordable?'':'<small class="inc-warn">Chưa đủ tiền cho cách này</small>'}</span></button>`;
  }).join('');
  return head(esc(x.title),`${esc(x.cat_emoji)} ${esc(x.cat_label).toUpperCase()}`)+`<div class="sheet-body inc-body">
    ${x.practice?`<p class="inc-replay-note">${icon('refresh',14)} Chỉ là nhớ lại chuyện cũ: tiền và tiếng không đổi.</p>`:''}
    <div class="inc-hero ${x.tone==='tense'?'tense':''}"><span class="inc-emoji" aria-hidden="true">${esc(x.emoji)}</span><p>${esc(x.text)}</p></div>
    ${ticket}${ev}
    <h4 class="section-title">Bạn chọn cách nào?</h4><div class="inc-choices" role="group" aria-label="Các cách xử lý">${choices}</div>
    ${x.practice?`<div class="row space-top">${btn('Cất chuyện cũ lại','incClose',{},'ghost small')}</div>`:''}
  </div>`;
}

function resultView(r,box){
  const [cls,label]=verdict(r.good);
  const lines=r.lines?.length?`<ul class="inc-lines">${r.lines.map(line).join('')}</ul>`:'';
  return head(esc(r.title),`${esc(r.emoji)} ${esc(r.cat_label).toUpperCase()}`)+`<div class="sheet-body inc-body" aria-live="polite">
    <div class="inc-result ${cls}"><span class="eyebrow">${r.practice?'NẾU HÔM ĐÓ CHỌN VẬY':label.toUpperCase()}</span><p class="inc-picked">${esc(r.label)}</p><p>${esc(r.outcome)}</p>${lines}${r.practice?'':trustChip(r.trust)}</div>
    ${r.practice?'':trustMeter(box)}
    <div class="row wrap space-top inc-foot">${btn('Xem sổ chuyện đời','incLog',{},'ghost')}${btn('Làm tiếp '+icon('arrow',14),'close',{},'primary big')}</div>
  </div>`;
}

function logView(box){
  const rows=box.log.map(h=>{const [cls]=verdict(h.good);return `<article class="inc-log ${cls}"><span class="inc-log-emoji" aria-hidden="true">${esc(h.emoji)}</span><div class="grow"><div class="row spread"><b>${esc(h.title)}</b><small class="muted">Ngày ${h.day}</small></div><small class="muted block">${h.auto?'Chưa kịp quyết · ':''}${esc(h.label)}</small><p class="small">${esc(h.outcome)}</p><div class="inc-stakes">${h.fund?stake({where:'fund',amount:h.fund}):''}${h.wallet?stake({where:'wallet',amount:h.wallet}):''}${trustChip(h.trust)}</div></div></article>`;}).join('');
  const replay=box.replay.length?`<h4 class="section-title">Nhớ lại chuyện cũ</h4><div class="row wrap">${box.replay.map(id=>{const h=box.log.find(x=>x.script===id);return h?btn(`${esc(h.emoji)} ${esc(h.title)}`,'incReplay',{script:id},'ghost small'):'';}).join('')}</div>`:'';
  return head('Chuyện đời','SỔ CHUYỆN ĐỜI')+`<div class="sheet-body inc-body">${trustMeter(box)}
    ${rows?`<h4 class="section-title">Đã xảy ra</h4><div class="stack">${rows}</div>`:`<div class="empty">${icon('shield',30)}<h3>Chưa có chuyện gì</h3></div>`}
    ${replay}<div class="row space-top">${btn('Về quầy','close',{},'primary')}</div></div>`;
}

/** Sheet body for ui.view==='incident'. */
export function incidentView(env){
  const {api,ui}=env,c=api.state.careers[api.state.current],box=c.incidents;
  if(!box)return head('Chuyện đời','SỔ CHUYỆN ĐỜI')+`<div class="sheet-body"><div class="empty">${icon('shield',30)}<h3>Chưa có chuyện gì</h3></div></div>`;
  if(box.active)return decisionView(box.active);
  if(box.last&&ui.incResult===box.last.id)return resultView(box.last,box);
  return logView(box);
}

/** Short block for the day summary. */
export function incidentSummary(x){
  if(!x?.items?.length)return '';
  const rows=x.items.map(h=>{const [cls,label]=verdict(h.good);return `<li class="${cls}"><span aria-hidden="true">${esc(h.emoji)}</span><span class="grow"><b>${esc(h.title)}</b><small>${h.auto?'Chưa kịp quyết · ':''}${esc(h.label)} · ${label}</small></span>${h.fund||h.wallet?`<b class="${(h.fund+h.wallet)<0?'out':'in'}">${signed(h.fund+h.wallet)} xu</b>`:''}</li>`;}).join('');
  return `<article class="notice inc-sum">${icon('shield',17)}<div class="grow"><b>Chuyện đời hôm nay</b><ul>${rows}</ul><p class="small">Uy tín với khu phố: <b>${esc(x.trust_name)}</b> (${x.trust}/100)</p><button type="button" class="btn small" data-action="incident">Mở sổ chuyện đời</button></div></article>`;
}

/** Note row for the HUD "Cần để ý" card. */
export const incidentNote=c=>{const a=c.incidents?.active;return a&&!a.practice?['incident',{},'shield',a.cat_label,a.title]:null;};
export const incidentBadge=c=>c.incidents?.active&&!c.incidents.active.practice?'dot':0;

export async function incidentAction(action,data,el,env){
  const {ui,openSheet,cmd,confirmAction,renderSheet}=env;
  switch(action){
    case'incident':case'incLog':ui.incResult=null;openSheet('incident');return true;
    case'incChoose':{
      const box=env.api.state.careers[env.api.state.current].incidents,x=box?.active;if(!x||x.id!==data.id)return true;
      const o=x.options.find(v=>v.id===data.option);if(!o)return true;
      const cost=o.stakes.filter(s=>s.amount<0).map(s=>`${fmt(-s.amount)} xu ${s.where==='wallet'?'từ ví của bạn':'từ quỹ nơi làm'}`).join(' và ');
      const text=x.practice?'Chỉ là nhớ lại, tiền và tiếng không đổi.':cost?`Cách này tốn ${cost}. Quyết rồi thì không đổi lại được.`:'Quyết rồi thì không đổi lại được.';
      if(!await confirmAction(o.label,text,'Chốt cách này'))return true;
      ui.incResult=x.id;
      const r=await cmd('inc_choose',{id:x.id,option:o.id});
      if(!r)ui.incResult=null;
      openSheet('incident');return true;
    }
    case'incReplay':{const r=await cmd('inc_practice',{script:data.script},{quiet:true});if(r)openSheet('incident');return true;}
    case'incClose':{await cmd('inc_close',{},{quiet:true});ui.incResult=null;renderSheet(false);return true;}
  }
  return false;
}

/** Pops the decision card up when the server opens a new incident. */
export function incidentBoot(env){
  if(!document.querySelector('link[data-incidents-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href='/css/incidents.css';l.dataset.incidentsCss='1';document.head.append(l);}
  const seen=new Set();
  const check=()=>{
    const s=env.api.state,c=s?.current&&s.careers?.[s.current],a=c?.incidents?.active;
    if(!a||a.practice||seen.has(a.id))return;
    seen.add(a.id);
    setTimeout(()=>{
      const now=env.api.state?.careers?.[env.api.state.current]?.incidents?.active;
      if(!now||now.id!==a.id||document.querySelector('#confirmDialog')?.open)return;
      if(['incident','home','settings','social'].includes(env.ui.view))return;
      env.openSheet('incident');
    },650);
  };
  env.api.addEventListener('state',check);check();
}
