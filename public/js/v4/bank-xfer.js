/** 💸 Chuyển khoản bạn bè: the bank app's transfer screen. Every rule and number lives in game/bank_xfer.py.
 * Pick a friend → amount (quick chips or typed) and a short note → confirm (who, how much, from where) → receipt.
 * GET /api/bank/xfer: friends who can receive, today's room, recent transfers (and what friends sent, credited).
 * POST /api/bank/xfer/send {to, amount, note, src, rid}: one rid per confirmation, the same one on a retry (the server
 * pays once per rid), so the call may retry on a flaky network.
 * Incoming: bootstrap's `xfers` (app.js) and the ticker's poll (me.xfer, ticker.js) → POST /api/bank/xfer/receive;
 * each arrival is a toast. Rendered inside the bank dialog (bank.js calls xferPage / xferClick / xferInput). */
import {escapeHTML as esc} from '../icons.js';
import {avInner} from './face.js';

const X={step:'pick',view:null,loading:false,to:null,amount:0,note:'',src:'acc',rid:'',receipt:null,err:'',at:0,busy:false};
let C=null;   // {env:()=>env, render, B:()=>bank view, J:()=>journey, ting}
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const b=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-bk="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${X.busy?' disabled':''}${extra}>${label}</button>`;
const av=(f,cls='')=>`<span class="bx-av ${cls}" aria-hidden="true">${avInner({fc:f?.fc,av:'🙂'})}</span>`;
const srcName=s=>s==='cash'?'Tiền mặt':'Tài khoản';
const two=n=>String(n).padStart(2,'0');
const when=t=>{const d=new Date(t*1000);return `${two(d.getDate())}/${two(d.getMonth()+1)} ${two(d.getHours())}:${two(d.getMinutes())}`;};

export function bindXfer(ctx){C=ctx;}

/** Opens the screen at its first step and loads the friends. */
export function xferOpen(){
  Object.assign(X,{step:'pick',to:null,amount:0,note:'',rid:'',receipt:null,err:''});
  if(!X.view||Date.now()-X.at>5000)load();
}
async function load(){
  const env=C.env();X.loading=true;C.render();
  try{
    const v=await env.api.json('/api/bank/xfer');
    if(v.state&&typeof v.revision==='number')env.api.accept({state:v.state,revision:v.revision});
    if(v.got?.length)showIncoming(env,v.got);
    X.view=v;X.at=Date.now();X.err='';
  }catch(e){X.err=e.message||'Chưa tải được. Thử lại nhé.';}
  finally{X.loading=false;C.render();}
}

const room=()=>{const v=X.view||{},bk=C.B();const have=X.src==='cash'?Math.max(0,C.J().wallet||0):(bk.balance||0);return Math.min(v.today?.left??0,have);};

export function xferPage(){
  const v=X.view,top=`<button type="button" class="bx-back" data-bk="${X.step==='pick'||X.step==='done'?'tab':'x-back'}" data-tab="home">‹ ${X.step==='pick'||X.step==='done'?'Tổng quan':'Quay lại'}</button>`;
  if(!v)return top+`<section class="bk-card bx"><h3>💸 Chuyển khoản</h3>${X.loading?'<p class="bk-hint">Đang tải…</p>':`<p class="bk-alert bad">${esc(X.err||'Chưa tải được.')}</p>${b('Thử lại','x-reload',{},'ghost')}`}</section>`;
  return top+({pick,amount,confirm,done}[X.step]||pick)(v);
}

function pick(v){
  const R=v.rules;
  const list=v.friends.map(f=>`<li><button type="button" class="bx-friend" data-bk="x-to" data-code="${esc(f.code)}"${f.ok&&!v.lock?'':' disabled'}>${av(f)}<span class="bx-name"><b>${esc(f.name)}</b>${f.why?`<small>${esc(f.why)}</small>`:''}</span><span class="bx-go" aria-hidden="true">›</span></button></li>`).join('');
  const recent=(v.recent||[]).map(r=>`<li><div class="bk-tx-main"><small>${when(r.at)} · ${esc(r.code)}</small><span>${r.dir==='out'?`Tới ${esc(r.name)}`:`Từ ${esc(r.name)}`}${r.note?` · «${esc(r.note)}»`:''}</span></div>
    <div class="bk-tx-amt"><b class="${r.dir==='out'?'down':'up'}">${r.dir==='out'?'−':'+'}${fmt(r.amount)}</b><small>${r.dir==='in'?'Đã nhận':r.status==='done'?'Bạn ấy đã nhận':r.status==='back'?'Đã trả lại':'Chờ bạn ấy vào game'}</small></div></li>`).join('');
  return `<section class="bk-card bx"><h3>💸 Chuyển khoản cho bạn bè</h3>
    ${v.lock?`<p class="bk-alert warn">${esc(v.lock)}</p>`:`${R.admin?'':`<p class="bk-hint">Hôm nay còn chuyển được <b>${xu(v.today.left)}</b>.</p>`}`}
    ${list?`<ul class="bx-friends" aria-label="Chọn người nhận">${list}</ul>`:'<p class="bk-hint">Chưa có bạn bè nào. Kết bạn ở mục Bạn bè nhé.</p>'}
    ${R.admin?'<p class="bk-hint">🛡️ Admin: chuyển ngay, không giới hạn.</p>':`<details class="bk-tips"><summary>Quy định</summary><ul class="bk-bullets"><li>Mỗi ngày chuyển tối đa ${xu(R.send_day)}, ${R.send_count} lần.</li><li>Mỗi người nhận tối đa ${xu(R.recv_day)} một ngày.</li><li>Tài khoản đã chơi game đủ ${R.account_days} ngày (đời thực), kết bạn đủ ${R.friend_minutes} phút.</li></ul></details>`}</section>
    ${recent?`<section class="bk-card"><h3>Gần đây</h3><ul class="bk-tx">${recent}</ul></section>`:''}`;
}

function who(){const f=X.to;return `<div class="bx-who">${av(f,'big')}<div><small>Người nhận</small><b>${esc(f.name)}</b></div></div>`;}
function amount(v){
  const R=v.rules,bk=C.B(),most=room();
  const chips=R.chips.map(n=>`<button type="button" class="bx-chip${X.amount===n?' on':''}" data-bk="x-chip" data-n="${n}"${n>most?' disabled':''}>${fmt(n)}</button>`).join('');
  return `<section class="bk-card bx">${who()}
    <label class="bk-field"><span>Số xu</span><input id="bx-amt" type="number" inputmode="numeric" min="${R.min}" max="${Math.max(R.min,most)}" step="1" value="${X.amount||''}" placeholder="Ít nhất ${R.min} xu"></label>
    <div class="bx-chips" role="group" aria-label="Chọn nhanh">${chips}</div>
    <label class="bk-field"><span>Lời nhắn (không bắt buộc)</span><input id="bx-note" type="text" maxlength="${R.note_max}" value="${esc(X.note)}" placeholder="Ví dụ: Cảm ơn nha!" autocomplete="off"></label>
    <label class="bk-field"><span>Chuyển từ</span><select id="bx-src"><option value="acc"${X.src==='acc'?' selected':''}>Tài khoản (${xu(bk.balance)})</option><option value="cash"${X.src==='cash'?' selected':''}>Tiền mặt (${xu(Math.max(0,C.J().wallet||0))})</option></select></label>
    ${X.err?`<p class="bk-alert bad" role="alert">${esc(X.err)}</p>`:(R.admin?'':`<p class="bk-hint">Hôm nay còn chuyển được ${xu(v.today.left)}.</p>`)}
    <div class="bk-actions">${b('Tiếp tục','x-next',{},'primary big')}</div></section>`;
}

function confirm(){
  return `<section class="bk-card bx bx-confirm"><h3>Kiểm tra lại nhé</h3>${who()}
    <strong class="bx-amount">${xu(X.amount)}</strong>
    <dl class="bx-dl"><div><dt>Chuyển từ</dt><dd>${srcName(X.src)}</dd></div>${X.note?`<div><dt>Lời nhắn</dt><dd>«${esc(X.note)}»</dd></div>`:''}</dl>
    <p class="bk-alert warn">Chuyển rồi không lấy lại được.</p>
    ${X.err?`<p class="bk-alert bad" role="alert">${esc(X.err)}</p>`:''}
    <div class="bk-actions">${b('Sửa','x-back',{},'ghost')}${b(`Chuyển ${xu(X.amount)}`,'x-send',{},'primary big')}</div></section>`;
}

function done(){
  const r=X.receipt;
  return `<section class="bk-card bx bx-done"><div class="bx-tick" aria-hidden="true">✅</div>
    <h3>Đã chuyển ${xu(r.amount)} cho ${esc(r.to)}</h3>
    <dl class="bx-dl"><div><dt>Mã giao dịch</dt><dd><b>${esc(r.code)}</b></dd></div><div><dt>Thời gian</dt><dd>${when(r.at)}</dd></div>
      <div><dt>Chuyển từ</dt><dd>${srcName(r.src)}</dd></div>${r.note?`<div><dt>Lời nhắn</dt><dd>«${esc(r.note)}»</dd></div>`:''}</dl>
    <p class="bk-hint">${esc(r.to)} nhận được khi vào game. 💛</p>
    <div class="bk-actions">${b('Chuyển thêm','x-again',{},'ghost')}${b('Xong','tab',{tab:'home'},'primary')}</div></section>`;
}

/** Field edits: kept as typed, no re-render (the bank's own keepFocus is not needed). */
export function xferInput(el){
  if(el.id==='bx-amt'){const n=Number(el.value);X.amount=Number.isInteger(n)&&n>0?n:0;S_chips();}
  else if(el.id==='bx-note')X.note=el.value;
  else if(el.id==='bx-src'){X.src=el.value;C.render();}
}
function S_chips(){C.dlg()?.querySelectorAll('.bx-chip').forEach(c=>c.classList.toggle('on',Number(c.dataset.n)===X.amount));}

export async function xferClick(op,data){
  const v=X.view;X.err='';
  switch(op){
    case'x-reload':load();return;
    case'x-to':{const f=v?.friends.find(x=>x.code===data.code);if(!f?.ok)return;X.to=f;X.step='amount';X.amount=0;X.note='';X.src=(C.B().balance||0)>=v.rules.min?'acc':'cash';C.render();return;}
    case'x-chip':X.amount=Number(data.n);C.render();return;
    case'x-back':X.step=X.step==='confirm'?'amount':'pick';X.rid='';C.render();return;
    case'x-next':{
      const R=v.rules,most=room(),a=X.amount;X.note=X.note.trim();
      if(!a||a<R.min)X.err=`Chuyển ít nhất ${xu(R.min)} nhé.`;
      else if(a>v.today.left)X.err=v.today.left?`Hôm nay bạn còn chuyển được ${xu(v.today.left)} thôi.`:'Hôm nay bạn đã chuyển đủ rồi. Mai chuyển tiếp nhé.';
      else if(a>most)X.err=X.src==='cash'?`Tiền mặt chỉ còn ${fmt(Math.max(0,C.J().wallet||0))} xu.`:`Tài khoản chỉ còn ${fmt(C.B().balance)} xu.`;
      else if(X.note.length>R.note_max)X.err=`Lời nhắn tối đa ${R.note_max} ký tự nhé.`;
      else{X.step='confirm';X.rid=rid();}
      C.render();return;}
    case'x-send':{
      if(X.busy)return;const env=C.env(),api=env.api;X.busy=true;C.render();
      try{
        const d=await api.json('/api/bank/xfer/send',{method:'POST',retry:true,headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},
          body:JSON.stringify({to:X.to.code,amount:X.amount,note:X.note,src:X.src,rid:X.rid})});
        if(d.state&&typeof d.revision==='number')api.accept({state:d.state,revision:d.revision});
        X.receipt=d.receipt;X.step='done';X.rid='';X.at=0;C.ting?.();load();
      }catch(e){X.err=e.message||'Chưa chuyển được. Thử lại nhé.';if(e.status&&e.status<500)X.rid=rid();}
      finally{X.busy=false;C.render();}
      return;}
    case'x-again':Object.assign(X,{step:'pick',to:null,amount:0,note:'',receipt:null});C.render();return;
  }
}

/* ---- arrivals ---- */
export function showIncoming(env,list){
  for(const g of list||[])env.toast(g.note?`💸 ${g.name} chuyển cho bạn ${fmt(g.amount)} xu: «${g.note}»`:`💸 ${g.name} chuyển cho bạn ${fmt(g.amount)} xu`,'good');
}
let receiving=false;
/** The ticker saw a transfer waiting: credit it now and say so. */
export async function receiveNow(env){
  if(receiving)return;receiving=true;
  try{
    const api=env.api,d=await api.post('/api/bank/xfer/receive',{});
    if(d.state&&typeof d.revision==='number')api.accept({state:d.state,revision:d.revision});
    if(d.got?.length){showIncoming(env,d.got);X.at=0;}
  }catch{/* the next poll or load tries again */}
  finally{receiving=false;}
}
