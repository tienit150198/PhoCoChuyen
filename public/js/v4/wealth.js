/** 💰 "Tiền của bạn" (0.9.8, player feedback: "không biết tôi còn bao nhiêu tiền").
 *
 * The top bar shows two labelled chips, "🏪 Quỹ 358" (this workplace's fund) and "👛 Ví 14" (the personal
 * wallet, red when it is in debt). Tapping either opens one sheet that lists every pocket with its amount:
 * the wallet, the bank (account, savings, terms with their maturity, loans, card), each workplace's fund
 * with "Rút về ví" up to the most it can give, the couple's Quỹ chung, the home, then "Tổng tài sản" and "Tổng nợ".
 * Every row links to the screen that already manages it (Sổ ví, Ngân hàng, Nhà của bạn, Hôn nhân).
 *
 * Everything comes from the public state (journey.wallet, journey.places, journey.bank, journey.home); only
 * the joint fund is fetched (GET /api/marriage, like the house sheet). The pure helpers (no DOM, no imports)
 * are unit-tested by tests/wealth.mjs. */
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>Number.isFinite(Number(v))?Number(v):0;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');

/** Short numbers for the top bar on phones (no "xu"): 125.400 → 125,4k, 3.373.500 → 3,37tr. */
export function shortNum(n){
  const v=num(n),a=Math.abs(v);
  if(a>=999950)return `${(v/1e6).toLocaleString('vi-VN',{maximumFractionDigits:2})}tr`;
  if(a>=1e5)return `${(v/1e3).toLocaleString('vi-VN',{maximumFractionDigits:1})}k`;
  return fmt(v);
}

/** The two top-bar amounts: this workplace's fund and the wallet (null outside the story: free play has
 * no personal wallet). */
export function hudMoney(state,cid){
  const c=state?.careers?.[cid],j=state?.journey;
  const story=Boolean(j)&&j.story!==false;
  return {fund:c&&Number.isFinite(Number(c.money))?Number(c.money):null,
          wallet:story&&Number.isFinite(Number(j.wallet))?Number(j.wallet):null};
}

/** The chips' markup (inside the top bar's .cozy-till group); `short`: app.js passes its shortMoney. */
export function hudChipsHTML(m,{phone=false,short=shortNum}={}){
  if(!m)return '';
  const n=v=>phone?short(v):fmt(v);
  // Longer numbers on a 390px phone ("Quỹ 294 · Ví 3.000"): the chips drop their emoji, never the words.
  const tight=phone&&(n(Math.abs(m.fund??0))+n(Math.abs(m.wallet??0))).length>=7?' tight':'';
  const out=[];
  if(m.fund!=null)out.push(`<button type="button" class="hud-chip hud-fund${m.fund<0?' neg':''}${tight}" data-action="money" aria-label="Quỹ nơi làm việc: ${fmt(m.fund)} xu. Xem tiền của bạn"><span class="hud-ico" aria-hidden="true">🏪</span><small>Quỹ</small><b data-testid="money">${m.fund<0?'−'+n(-m.fund):n(m.fund)}</b></button>`);
  if(m.wallet!=null){
    const neg=m.wallet<0;
    out.push(`<button type="button" class="hud-chip hud-wallet${neg?' neg':''}${tight}" data-action="money" aria-label="${neg?`Ví đang nợ ${fmt(-m.wallet)} xu`:`Ví của bạn: ${fmt(m.wallet)} xu`}. Xem tiền của bạn"><span class="hud-ico" aria-hidden="true">👛</span>${neg?'':'<small>Ví</small>'}<b data-testid="wallet">${neg?'−'+n(-m.wallet):n(m.wallet)}</b></button>`);
  }
  return out.join('');
}

/** Every pocket, from the public state. `joint`: the couple's fund balance when known (null: not married,
 * or not loaded yet). `current`: the workplace on screen (listed first). */
export function pockets(state,{joint=null,current=null}={}){
  const j=state?.journey||null,story=Boolean(j)&&j.story!==false;
  const wallet=story?num(j.wallet):null;
  const b=story?j.bank:null;
  const bank=!story?null:!b?.open?{open:false}:{
    open:true,balance:num(b.balance),demand:num(b.savings?.demand),
    terms:(b.savings?.terms||[]).map(t=>({id:t.id,name:t.name,amount:num(t.amount),value:num(t.value),due:t.due,days_left:num(t.days_left)})),
    loans:(b.loans||[]).filter(l=>num(l.left)>0).map(l=>({id:l.id,name:l.name,emoji:l.emoji||'📝',left:num(l.left),overdue:num(l.overdue)})),
    card:num(b.card?.bal)};
  const places=Object.entries(j?.places||{}).map(([cid,p])=>({cid,fund:num(p.fund),max:story?Math.max(0,num(p.withdraw_max)):0,
    employed:Boolean(p.employed),paused:Boolean(p.paused)}))
    .sort((a,b2)=>(b2.cid===current)-(a.cid===current)||b2.fund-a.fund||a.cid.localeCompare(b2.cid));
  if(!places.length&&current&&state?.careers?.[current]&&Number.isFinite(Number(state.careers[current].money)))
    places.push({cid:current,fund:num(state.careers[current].money),max:0,employed:false,paused:false});
  const own=story?j.home?.own:null;
  const view=x=>({kind:x.kind,name:x.name,emoji:x.emoji||'🏠',value:num(x.value),loan:num(x.loan?.left)});
  const home=own?view(own):null;
  // 🏘️ Every home you own (housing.py VERSION 2): the one you live in first, then the others, empty or let.
  const props=story&&Array.isArray(j.home?.props)?j.home.props:[];
  const homes=[...(home?[{...home,live:true}]:[]),...props.map(x=>({...view(x),live:false,let:Boolean(x.let)}))];
  const jointFund=story&&joint!=null&&Number.isFinite(Number(joint))?Number(joint):null;
  let assets=Math.max(0,wallet||0)+places.reduce((s,p)=>s+Math.max(0,p.fund),0)+(jointFund||0)+homes.reduce((s,x)=>s+x.value,0);
  let debt=Math.max(0,-(wallet||0))+places.reduce((s,p)=>s+Math.max(0,-p.fund),0)+homes.reduce((s,x)=>s+x.loan,0);
  if(bank?.open){
    assets+=bank.balance+bank.demand+bank.terms.reduce((s,t)=>s+t.amount,0);
    debt+=bank.loans.reduce((s,l)=>s+l.left,0)+bank.card;
  }
  return {story,wallet,bank,places,joint:jointFund,home,homes,assets,debt,net:assets-debt};
}

/* ---------------------------------------------------------------- the sheet */
const xu=n=>`${fmt(n)} xu`;
const minus=n=>`−${fmt(n)} xu`;
const link=(label,action,data={})=>`<button type="button" class="wl-link" data-action="${action}"${attrs(data)}>${label}<span aria-hidden="true"> ›</span></button>`;
const row=(ico,label,amount,{sub='',cls='',extra='',id=''}={})=>`<li class="wl-row ${cls}"${id?` data-wl="${esc(id)}"`:''}><span class="wl-ico" aria-hidden="true">${ico}</span><span class="wl-name">${label}${sub?`<small>${sub}</small>`:''}</span><b class="wl-amt">${amount}</b>${extra?`<div class="wl-extra">${extra}</div>`:''}</li>`;
const section=(title,rows,action='')=>rows?`<section class="wl-card"><header class="wl-head"><h3>${title}</h3>${action}</header><ul class="wl-list">${rows}</ul></section>`:'';

/** The sheet's markup. `o`: {joint, current, place(cid) → {name, emoji}, head(title) → header markup,
 * lifeDay}. */
export function wealthHTML(state,o={}){
  const P=pockets(state,{joint:o.joint??null,current:o.current||null}),place=o.place||(cid=>({name:cid,emoji:'🏪'}));
  const day=Number(state?.journey?.life_day)||0;
  const parts=[];
  parts.push(`<section class="wl-total" data-testid="wealth-total"><div><small>Tổng tài sản</small><b data-wl-total="${P.assets}">${xu(P.assets)}</b></div>`+
    (P.debt?`<div class="bad"><small>Tổng nợ</small><b data-wl-debt="${P.debt}">${minus(P.debt)}</b></div>`:'')+`</section>`);
  if(P.wallet!=null)parts.push(section('Ví',row('👛','Tiền mặt',P.wallet<0?minus(-P.wallet):xu(P.wallet),{cls:P.wallet<0?'bad':'',id:'wallet',sub:P.wallet<0?'đang nợ tiền phòng':''}),link('Sổ ví','stView',{view:'wallet'})));
  if(P.bank){
    // A plain button into Ngân hàng Phố on the first row (feedback #110: since the bank sits in the "Ngân hàng & nhà"
    // hub, a player looking from their money did not see the small "Chi tiết" link).
    const B=P.bank,go=`<button type="button" class="btn small" data-action="bank"><span aria-hidden="true">🏦</span> ${B.open?'Vào Ngân hàng':'Mở tài khoản'}</button>`;let rows='';
    if(!B.open)rows=row('🏦','Chưa mở tài khoản','',{id:'bank-none',extra:go});
    else{
      rows+=row('🏦','Tài khoản',xu(B.balance),{id:'account',extra:go});
      if(B.demand)rows+=row('🐷','Tiết kiệm không kỳ hạn',xu(B.demand),{id:'demand'});
      for(const t of B.terms)rows+=row('📅',esc(t.name),xu(t.amount),{id:'term',sub:`đáo hạn Ngày ${fmt(t.due)}${t.days_left?` · còn ${fmt(t.days_left)} ngày`:' · hôm nay'}`});
      for(const l of B.loans)rows+=row(esc(l.emoji),esc(l.name),minus(l.left),{cls:'bad',id:'loan',sub:l.overdue?`quá hạn ${xu(l.overdue)}`:'còn nợ'});
      if(B.card)rows+=row('💳','Thẻ tín dụng',minus(B.card),{cls:'bad',id:'card',sub:'dư nợ thẻ'});
    }
    parts.push(section('Ngân hàng',rows));
  }
  if(P.places.length){
    const rows=P.places.map(p=>{const m=place(p.cid);
      const draw=!P.story?'':p.max>0?`<button type="button" class="btn small primary" data-action="wlDraw" data-career="${esc(p.cid)}" data-amount="${p.max}">Rút về ví · tối đa ${xu(p.max)}</button>`:`<small class="muted">Chưa rút được: quỹ giữ lại tiền dự phòng và hóa đơn.</small>`;
      return row(esc(m.emoji||'🏪'),esc(m.name||p.cid),p.fund<0?minus(-p.fund):xu(p.fund),{cls:(p.fund<0?'bad ':'')+(p.cid===o.current?'here':''),id:'fund',sub:p.cid===o.current?'đang ở đây':p.paused?'tạm đóng':p.employed?'làm thuê':'',extra:draw});
    }).join('');
    parts.push(section('Quỹ nơi làm việc',rows,P.story?link('Góp vốn, tạm đóng','stView',{view:'wallet'}):''));
  }
  if(P.joint!=null)parts.push(section('Quỹ chung',row('💞','Quỹ chung vợ chồng',xu(P.joint),{id:'joint'}),link('Hôn nhân','marriage')));
  if(P.homes.length)parts.push(section('Nhà',P.homes.map(x=>row(esc(x.emoji),esc(x.name),xu(x.value),{id:'home',sub:x.live?'giá thị trường hôm nay':x.let?'đang cho thuê':'đang để trống'})+
    (x.loan?row('📝',x.live?'Vay mua nhà':`Vay mua ${esc(x.name.slice(0,1).toLowerCase()+x.name.slice(1))}`,minus(x.loan),{cls:'bad',id:'home-loan',sub:'còn phải trả'}):'')).join(''),link('Chi tiết','house')));
  const title=typeof o.head==='function'?o.head('Tiền của bạn',day?`Ngày sống ${fmt(day)}`:''):`<header class="sheet-head"><h2>Tiền của bạn</h2></header>`;
  return title+`<div class="sheet-body wl-body">${parts.join('')}</div>`;
}

/* ---------------------------------------------------------------- joint fund + actions (browser only) */
const JOINT={value:null,at:0,busy:false};
export const married=state=>state?.marriage?.spouse?.status==='married'||Boolean(state?.journey?.home?.married);
export function jointBalance(){return JOINT.value;}

/** Load the couple's fund once in a while (15 s), then redraw the sheet if it is still open. */
export async function loadJoint(env,force=false){
  if(!married(env.api.state)){JOINT.value=null;return;}
  if(JOINT.busy||(!force&&Date.now()-JOINT.at<15000))return;
  JOINT.busy=true;JOINT.at=Date.now();
  try{const v=await env.api.json('/api/marriage');JOINT.value=v?.home?.fund?Number(v.home.fund.balance):null;}
  catch{JOINT.value=null;}
  finally{JOINT.busy=false;}
  if(env.ui.view==='money'&&document.getElementById('sheet')?.open)env.renderSheet();
}

/** 'wlDraw': withdraw the most a workplace can give, after a confirm. */
export async function wealthAction(action,data,el,env){
  if(action!=='wlDraw')return false;
  const amount=Number(data.amount),cid=data.career;
  if(!Number.isInteger(amount)||amount<1||!cid)return true;
  const name=env.placeName?.(cid)||cid;
  if(await env.confirmAction(`Rút ${fmt(amount)} xu về ví?`,`Từ quỹ ${name}. Quỹ vẫn giữ tiền dự phòng và tiền hóa đơn chưa trả.`,`Rút · ${fmt(amount)} xu`)){
    const r=await env.cmd('jr_withdraw',{career:cid,amount});
    if(r&&env.ui.view==='money')env.renderSheet();
  }
  return true;
}
