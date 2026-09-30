/** Tiền mặt ở quầy (shared by the careers that take cash by hand; server side: game/careers/till.py).
 * Shows the notes the customer hands over, the bill and the change tray the player builds from real
 * denominations. The tray lives in ctx.ui per task and bill total, and goes to the server with the
 * hand-over as `change: [notes]`: the server alone decides how the customer takes it.
 * A customer who hands over less than the bill: shortpay.js (count again, remind, call the police…). */
import {gapBlock,gapStep} from './shortpay.js';
export const DENOMS=[500,200,100,50,20,10,5,2,1];
const sum=a=>(a||[]).reduce((s,v)=>s+Number(v||0),0);
const box=x=>x.ui.till??={};
const key=(id,cash)=>`${id}:${cash?.price??0}`;
/** The notes the player has put in the change tray for this task and bill. */
export const tray=(x,id,cash)=>box(x)[key(id,cash)]||[];
const coin=(x,v)=>`<span class="till-money ${v>=10?'note':'coin'}">${x.fmt(v)}</span>`;
const attrs=(x,act,id,cash,extra={})=>`data-action="car:${act}" data-task="${x.esc(id)}" data-price="${Number(cash.price)||0}"${Object.entries(extra).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}`;

/** The cash card: what the customer gave, what the bill says, the change due and the tray. */
export function cashPanel(x,id,cash,{title='💵 Khách trả tiền mặt',disabled=false}={}){
  if(!cash)return '';
  const given=tray(x,id,cash),g=sum(given),paid=sum(cash.tender),due=cash.due;
  const state=g===due?'ok':g>due?'over':'';
  return `<div class="till card" data-till="${x.esc(id)}"><h4>${title}</h4>
    <div class="till-row"><span>Khách đưa</span><span class="till-notes">${(cash.tender||[]).map(v=>coin(x,v)).join('')}</span><b>${x.money(paid)}</b></div>
    ${gapBlock(x,id,cash)}
    <div class="till-due"><span>Hóa đơn</span><b>${x.money(cash.price)}</b><span>Cần thối</span><b>${x.money(Math.max(0,due))}</b><span>Đang đặt</span><b class="${state}">${x.money(g)}</b></div>
    ${due>0?`<div class="till-tray" aria-label="Khay thối tiền">${given.map(v=>coin(x,v)).join('')||'<small class="muted">Khay thối còn trống</small>'}</div>
    <div class="till-denoms">${DENOMS.map(v=>`<button type="button" class="till-denom ${v>=10?'note':'coin'}" ${attrs(x,'tillAdd',id,cash,{v})} aria-label="Thêm ${v} xu"${disabled?' disabled':''}>${x.fmt(v)}</button>`).join('')}</div>
    <div class="row wrap"><button type="button" class="btn small ghost" ${attrs(x,'tillUndo',id,cash)}${given.length?'':' disabled'}>↩︎ Bớt tờ cuối</button><button type="button" class="btn small ghost" ${attrs(x,'tillClear',id,cash)}${given.length?'':' disabled'}>Cất hết</button></div>`
    :due===0?'<p class="small muted">Khách đưa vừa đủ, không cần thối.</p>':'<p class="small muted">Không cần thối.</p>'}
    ${cash.asked?'<p class="notice amber small">Khách đếm lại thấy thối thiếu: thối thêm cho đủ rồi đưa lại.</p>':''}</div>`;
}

/** One guide row for the change (null when the customer gave the exact amount). */
export function changeStep(x,id,cash){
  const gap=gapStep(x,id,cash);if(gap)return gap;
  if(!cash||!(cash.due>0))return null;
  const g=sum(tray(x,id,cash)),due=cash.due,v=DENOMS.find(d=>d<=due-g);
  const back={act:'car:tillUndo',data:{task:id,price:cash.price},label:'↩︎ Bớt tờ vừa đặt'};
  return {ok:g===due?true:g>due?false:null,label:`Thối lại ${due} xu (khách đưa ${sum(cash.tender)}, hóa đơn ${cash.price})`,
    note:cash.asked&&g<due?'khách đòi thối thêm':g?`đang đặt ${g} xu`:'',
    go:g>due?back:g<due&&v?{act:'car:tillAdd',data:{task:id,price:cash.price,v},label:`➕ Đặt ${v} xu vào khay thối`}:null,
    pulse:g<due&&v?`[data-till] [data-action="car:tillAdd"][data-v="${v}"]`:''};
}

/** The payload part for the hand-over command. */
export const changePayload=(x,id,cash)=>cash?{change:[...tray(x,id,cash)]}:{};

/** Spread into a career module's `actions`. */
export const tillActions={
  async tillAdd(data,el,x){const v=Number(data.v);if(!DENOMS.includes(v))return;const b=box(x),k=`${data.task}:${Number(data.price)||0}`;b[k]??=[];if(b[k].length<40)b[k].push(v);x.render();},
  async tillUndo(data,el,x){const b=box(x),k=`${data.task}:${Number(data.price)||0}`;(b[k]||[]).pop();x.render();},
  async tillClear(data,el,x){box(x)[`${data.task}:${Number(data.price)||0}`]=[];x.render();},
};
