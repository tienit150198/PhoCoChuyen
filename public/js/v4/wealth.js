/** 💰 "Tiền của bạn" (0.9.8, player feedback: "không biết tôi còn bao nhiêu tiền").
 *
 * The top bar shows two labelled chips, "🏪 Quỹ 358" (this workplace's fund) and "👛 Ví 14" (the personal
 * wallet, red when it is in debt). Tapping either opens one sheet that lists every pocket with its amount:
 * the wallet, the bank (account, savings, terms with their maturity, loans, card), each workplace's fund
 * with "Rút về ví" up to the most it can give, the couple's Quỹ chung, the home, then "Tổng tài sản" and "Tổng nợ".
 * Every row links to the screen that already manages it (Sổ ví, Ngân hàng, Nhà của bạn, Hôn nhân).
 *
 * Everything comes from the public state (journey.wallet, journey.places, journey.bank, journey.home); only
 * the joint fund is fetched (GET /api/marriage, like the house sheet). The pure helpers (no DOM) are unit-tested
 * by tests/wealth.mjs.
 *
 * 💼 Rút / góp vốn (F#259, 08/10: "lỡ bấm rút hết vốn tiệm… cho góp vốn, hoặc điều chỉnh số tiền rút"): every
 * workplace fund row has the two moves side by side, a typed amount (− N + with 25% / 50% / Tất cả chips, never "all"
 * by default) and a confirm that says what stays in the fund. Góp vốn takes the wallet first, then the bank account
 * (game/journey.py invest_max, like 🏪 Góp vốn quầy). The journey's Sổ ví draws the same block (fundMoveHTML). */
import {qtyBox,qtyVal,QTY} from '../qty-input.js';
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
      const move=P.story&&state?.journey?.places?.[p.cid]?fundMoveHTML(state,p.cid,{open:p.cid===o.current}):'';
      return row(esc(m.emoji||'🏪'),esc(m.name||p.cid),p.fund<0?minus(-p.fund):xu(p.fund),{cls:(p.fund<0?'bad ':'')+(p.cid===o.current?'here':''),id:'fund',sub:p.cid===o.current?'đang ở đây':p.paused?'tạm đóng':p.employed?'làm thuê':'',extra:move});
    }).join('');
    parts.push(section('Quỹ nơi làm việc',rows));
  }
  if(P.joint!=null)parts.push(section('Quỹ chung',row('💞','Quỹ chung vợ chồng',xu(P.joint),{id:'joint'}),link('Hôn nhân','marriage')));
  if(P.homes.length)parts.push(section('Nhà',P.homes.map(x=>row(esc(x.emoji),esc(x.name),xu(x.value),{id:'home',sub:x.live?'giá thị trường hôm nay':x.let?'đang cho thuê':'đang để trống'})+
    (x.loan?row('📝',x.live?'Vay mua nhà':`Vay mua ${esc(x.name.slice(0,1).toLowerCase()+x.name.slice(1))}`,minus(x.loan),{cls:'bad',id:'home-loan',sub:'còn phải trả'}):'')).join(''),link('Chi tiết','house')));
  const title=typeof o.head==='function'?o.head('Tiền của bạn',day?`Ngày sống ${fmt(day)}`:''):`<header class="sheet-head"><h2>Tiền của bạn</h2></header>`;
  return title+`<div class="sheet-body wl-body">${parts.join('')}</div>`;
}

/* ---------------------------------------------------------------- 💼 Rút / góp vốn (F#259) */
/** What the page remembers between redraws: the open move of each place ('draw' | 'invest') and the typed amounts. */
export const MOVE={mode:{},amt:{}};
const STEP=10;
/** The most Góp vốn can put in: the server's journey.invest_max (wallet, then bank account; 0 in debt). */
export function investMax(state){
  const j=state?.journey;if(!j||j.story===false)return 0;
  if(j.invest_max!=null&&Number.isFinite(Number(j.invest_max)))return Math.max(0,Math.floor(num(j.invest_max)));
  const w=num(j.wallet);return w<0?0:w+(j.bank?.open?Math.max(0,num(j.bank.balance)):0);
}
/** The amount shown first: a quarter of what can be drawn (never "all" unless only 1 xu can move), up to 50 xu to put in. */
export function firstAmount(mode,max){
  if(!(max>=1))return 0;
  return mode==='draw'?Math.max(1,Math.floor(max/4)):Math.min(max,50);
}
/** One place's move, from the public state: {mode, open, max, n, fund, draw, invest, cash, bank}. `cash`/`bank`: what
 * Góp vốn would take from the wallet and from the account. */
export function fundMove(state,cid,{open=false}={}){
  const j=state?.journey||{},p=j.places?.[cid]||{};
  const fund=num(p.fund),draw=Math.max(0,Math.floor(num(p.withdraw_max))),invest=investMax(state);
  const chosen=MOVE.mode[cid];
  const mode=chosen||(draw>0?'draw':'invest');
  const max=mode==='draw'?draw:invest;
  const typed=MOVE.amt[`${cid}:${mode}`];
  const n=max<1?0:Math.min(max,Math.max(1,Math.round(num(typed??firstAmount(mode,max)))));
  const cash=mode==='invest'?Math.min(Math.max(0,num(j.wallet)),n):0;
  return {mode,open:Boolean(open||chosen),max,n,fund,draw,invest,cash,bank:mode==='invest'?n-cash:0,debt:num(j.wallet)<0};
}
const tab=(cid,mode,on,label,fold)=>`<button type="button" class="wl-tab${on?' on':''}" data-action="wlMode" data-quick data-career="${esc(cid)}" data-mode="${mode}"${fold?' data-fold="1"':''} aria-pressed="${on}">${label}</button>`;
/** The block under a workplace fund: the two moves side by side; the open one has its amount and its button. */
export function fundMoveHTML(state,cid,o={}){
  const M=fundMove(state,cid,o),c=esc(cid);
  const tabs=`<div class="wl-tabs" role="group" aria-label="Rút về ví hay góp vốn">${tab(cid,'draw',M.open&&M.mode==='draw','👛 Rút về ví',!o.open)}${tab(cid,'invest',M.open&&M.mode==='invest','📈 Góp vốn',!o.open)}</div>`;
  if(!M.open)return `<div class="wl-move" data-wl-move="${c}">${tabs}</div>`;
  let body;
  if(M.max<1){
    body=`<p class="wl-why">${M.mode==='draw'?'Chưa rút được: quỹ phải giữ 80 xu dự phòng và đủ tiền hóa đơn chưa trả.'
      :M.debt?'Ví đang nợ. Trả nợ trước rồi góp vốn nhé.':'Ví và tài khoản ngân hàng đang trống, chưa có tiền để góp.'}</p>`;
  }else{
    const step=(by,label,aria)=>`<button type="button" class="btn ghost small wl-st" data-action="wlAmt" data-quick data-career="${c}" data-n="${M.n+by}" aria-label="${aria}"${(by<0?M.n<=1:M.n>=M.max)?' disabled':''}>${label}</button>`;
    const box=qtyBox({value:M.n,min:1,max:M.max,money:true,live:true,label:M.mode==='draw'?'Số xu rút về ví':'Số xu góp vốn',
      go:`data-action="wlAmt" data-quick data-career="${c}" data-n="${QTY}"`,attrs:`id="wl-amt-${c}"`});
    const chips=[[25,'25%'],[50,'50%'],[100,'Tất cả']].map(([pc,l])=>{const v=Math.max(1,Math.floor(M.max*pc/100));
      return `<button type="button" class="wl-chip${v===M.n?' on':''}" data-action="wlAmt" data-quick data-career="${c}" data-n="${v}" aria-pressed="${v===M.n}">${l}</button>`;}).join('');
    const from=!M.bank?`lấy ${xu(M.cash)} từ ví`:M.cash?`lấy ${xu(M.cash)} từ ví, ${xu(M.bank)} từ tài khoản ngân hàng`:`lấy ${xu(M.bank)} từ tài khoản ngân hàng`;
    const after=M.mode==='draw'?`Quỹ còn lại <b>${xu(M.fund-M.n)}</b>`:`Quỹ thành <b>${xu(M.fund+M.n)}</b> · ${from}`;
    body=`<div class="wl-amount">${step(-STEP,'−','Bớt 10 xu')}${box}${step(STEP,'+','Thêm 10 xu')}<small class="wl-of">tối đa ${xu(M.max)}</small></div>
      <div class="wl-chips">${chips}</div><p class="wl-after">${after}</p>
      <button type="button" class="btn small ${M.mode==='draw'?'primary':'cream'} wl-go" data-action="${M.mode==='draw'?'wlDraw':'wlInvest'}" data-career="${c}" data-amount="${M.n}">${M.mode==='draw'?`Rút ${xu(M.n)} về ví`:`Góp ${xu(M.n)} vào quỹ`}</button>`;
  }
  return `<div class="wl-move open" data-wl-move="${c}">${tabs}${body}</div>`;
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

/** 'wlMode' / 'wlAmt' (page only, data-quick: they work while a command is on the wire): open a move, set its amount
 * (the − / + buttons, the chips and the typed box). 'wlDraw' /
 * 'wlInvest': the amount in the box (or the button's), after a confirm that says what stays in the fund. */
export const WEALTH_ACTIONS=['wlMode','wlAmt','wlDraw','wlInvest'];
export async function wealthAction(action,data,el,env){
  if(!WEALTH_ACTIONS.includes(action))return false;
  const cid=data.career,state=env.api?.state;
  if(!cid||!state?.journey?.places?.[cid])return true;
  if(action==='wlMode'){
    const was=MOVE.mode[cid];MOVE.mode[cid]=data.mode==='invest'?'invest':'draw';
    if(was===MOVE.mode[cid]&&data.fold)delete MOVE.mode[cid];   // a folding row: tap the open move again to fold it
    env.renderSheet();return true;
  }
  const M=fundMove(state,cid,{open:true});
  if(action==='wlAmt'){
    if(M.max>=1)MOVE.amt[`${cid}:${M.mode}`]=Math.min(M.max,Math.max(1,Math.round(num(data.n))));
    env.renderSheet();return true;
  }
  const box=globalThis.document?.getElementById?.(`wl-amt-${cid}`);
  const amount=Math.min(M.max,Math.max(0,Math.round(qtyVal(box)||num(data.amount))));
  if(!Number.isInteger(amount)||amount<1)return true;
  const name=env.placeName?.(cid)||cid;
  if(action==='wlDraw'){
    const rest=M.fund-amount,all=amount>=M.draw;
    if(!await env.confirmAction(`Rút ${fmt(amount)} xu về ví?`,
      all?`Từ quỹ ${name}: đây là mức rút tối đa, quỹ chỉ còn ${fmt(rest)} xu để nhập hàng, trả lương và hóa đơn. Rút nhầm thì bấm Góp vốn để bỏ lại vào quỹ.`
        :`Từ quỹ ${name}: quỹ còn lại ${fmt(rest)} xu để nhập hàng, trả lương và hóa đơn. Rút nhầm thì bấm Góp vốn để bỏ lại vào quỹ.`,
      `Rút · ${fmt(amount)} xu`))return true;
    const r=await env.cmd('jr_withdraw',{career:cid,amount});
    if(r)delete MOVE.amt[`${cid}:draw`];
  }else{
    const cash=Math.min(Math.max(0,num(state.journey.wallet)),amount),bank=amount-cash;
    if(!await env.confirmAction(`Góp ${fmt(amount)} xu vào ${name}?`,
      !bank?`Lấy ${fmt(cash)} xu từ ví. Quỹ thành ${fmt(M.fund+amount)} xu.`
        :cash?`Lấy ${fmt(cash)} xu từ ví và ${fmt(bank)} xu từ tài khoản ngân hàng. Quỹ thành ${fmt(M.fund+amount)} xu.`
        :`Lấy ${fmt(bank)} xu từ tài khoản ngân hàng. Quỹ thành ${fmt(M.fund+amount)} xu.`,
      `Góp vốn · ${fmt(amount)} xu`))return true;
    const r=await env.cmd('jr_invest',{career:cid,amount});
    if(r)delete MOVE.amt[`${cid}:invest`];
  }
  env.renderSheet();
  return true;
}
