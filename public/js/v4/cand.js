/** 👮 Công an phường Mây giữa người chơi (game/cand_ops.py, live/cand.py): one small modal for every side of it.
 *   openStop(env, {pid,name})  an officer on duty taps a player at Chợ đen (v4/fair-walk.js): 🔎 Lục soát tư trang,
 *                              📝 Phạt hành chính, 🚓 Tạm giữ, ⛓️ Bắt giữ; then the wait for the answer, an envelope
 *                              (Nhận / Từ chối & lập biên bản), the outcome.
 *   onLive(env, frame)         the live push `cand` (app.js bootLive): 'ask' to the player stopped (🤝 Hợp tác /
 *                              💵 Đưa phong bì: a typed amount, 1..5000 and the wallet), 'offer' and 'done' to update
 *                              the modal that is up, 'done' also reloads the save (the fine, the jail).
 *   watch(env) / unwatch()     while the Chợ đen walk is up and the live service has no `cand` flag: a slow poll
 *                              (POST /api/marriage/cand_poll) for a question to answer.
 *   openForce(env)             👥 Toàn lực lượng for a commander (the rank card, v4/org.js): 🏅 Khen thưởng, 🚫 Khai trừ.
 *   onDuty(state)              a hint for the walk (the server decides everything; no odds are ever shown).
 * Names come from players: always escaped. */
import {escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const MAX=5000,POLL_MS=3000,WATCH_MS=10000;
const ACTS=[['search','🔎','Lục soát tư trang'],['fine','📝','Phạt hành chính'],['hold','🚓','Tạm giữ'],['arrest','⛓️','Bắt giữ']];
const NAME=Object.fromEntries(ACTS.map(([id,e,l])=>[id,`${e} ${l}`]));
export const COMMANDERS=['pho_truong_ca','truong_ca','pho_phong','truong_phong','tro_ly','pgd','gd'];

/** An officer on duty, as far as the page can tell (the shift open; not suspended, not in the trại). */
export function onDuty(st){
  const c=st?.careers?.police;if(!c||c.open!==true||st.jail)return false;
  const o=c.promo?.org;return !(o&&o.susp);
}
/** The rank card's 👥 button is shown to these (game/cand_ops.py COMMANDERS). */
export const commands=o=>Boolean(o&&!o.susp&&COMMANDERS.includes(o.post?.id));

let cssReady=null;
function loadCss(){
  if(cssReady)return cssReady;
  if(document.querySelector('link[data-cd-css]'))return cssReady=Promise.resolve();
  const href=globalThis.__mnlBoot?.asset?.('/css/cand.css')||'/css/cand.css';
  const l=document.createElement('link');l.rel='stylesheet';l.href=href;l.dataset.cdCss='1';
  cssReady=new Promise(done=>{l.onload=l.onerror=()=>done();setTimeout(done,4000);});
  document.head.append(l);return cssReady;
}
async function call(env,op,body={}){
  const api=env.api;
  const d=await api.json(`/api/marriage/${op}`,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body)});
  if(d?.state&&typeof d.revision==='number')api.accept({state:d.state,revision:d.revision});
  return d;
}

/* ------------------------------------------------------------------ the one modal */
const M={dlg:null,env:null,view:'',who:null,stop:null,until:0,poll:0,tick:0,busy:false,flash:null,give:false,force:null,sure:null,watch:0};
function dialog(){
  if(M.dlg)return M.dlg;
  const d=document.createElement('dialog');d.className='cd-dialog';d.setAttribute('aria-labelledby','cdTitle');
  d.addEventListener('cancel',e=>{e.preventDefault();if(M.view!=='ask')close();});   // the question waits for an answer
  d.addEventListener('click',e=>{const b=e.target.closest('[data-cd]');if(b&&!b.disabled)click(b.dataset.cd,b.dataset);});
  d.addEventListener('submit',e=>{e.preventDefault();click('give');});
  document.body.append(d);M.dlg=d;return d;
}
function close(){
  const told=M.view==='told';
  clearInterval(M.poll);clearInterval(M.tick);M.poll=M.tick=0;M.view='';M.stop=null;M.flash=null;M.give=false;M.sure=null;if(M.dlg?.open)M.dlg.close();
  // 🚔 Held or arrested: the outcome was read first (v4/jail.js waits while this modal is up); now the camp (it closes
  // the Chợ đen sheet behind, which has no arrest card of its own for a patrol's check).
  const env=M.env;
  if(told&&env?.api?.state?.jail)import('./jail.js').then(m=>m.openJail(env)).catch(()=>{/* the next state */});
}
function stopTimers(){clearInterval(M.poll);clearInterval(M.tick);M.poll=M.tick=0;}
async function show(){
  await loadCss();const d=dialog();
  const typed=d.querySelector('#cdAmount')?.value||'';   // a re-render (a wrong amount, a poll) keeps what was typed
  d.innerHTML=html();
  if(typed){const inp=d.querySelector('#cdAmount');if(inp)inp.value=typed;}
  if(!d.open){
    // Above whatever sheet is up (a modal dialog stacks on the top layer); the Chợ đen sheet stays under it.
    try{d.showModal();}catch{d.setAttribute('open','');}
  }
  const inp=d.querySelector('#cdAmount');if(inp)inp.focus();
}
const left=()=>Math.max(0,Math.ceil((M.until-Date.now())/1000));
function bar(){return M.until?`<div class="cd-bar" role="timer" aria-live="off"><i style="animation-duration:${Math.max(.1,(M.until-Date.now())/1000)}s"></i></div><p class="cd-left"><b data-cd-left>${left()}</b> giây</p>`:'';}
function timers(){
  stopTimers();
  const st=M.stop?.st;if(!(st==='ask'||st==='offer'))return;
  M.tick=setInterval(()=>{const el=M.dlg?.querySelector('[data-cd-left]');if(el)el.textContent=String(left());},500);
  // The push may not come (no live service, a socket down) and a stop past its time is settled by a call: ask now and then.
  M.poll=setInterval(refresh,M.env?.live?.()?.flags?.cand?POLL_MS*2:POLL_MS);
}
async function refresh(){
  if(!M.stop?.id||M.busy)return;
  try{const d=await call(M.env,'cand_poll',{id:M.stop.id});if(d.stop)take(d.stop);}catch{/* a moment offline: the next poll */}
}
const keyOf=s=>s?JSON.stringify([s.id,s.st,s.amount,s.text,s.acts]):'';
function take(stop){
  const was=M.stop?.st,same=keyOf(M.stop)===keyOf(stop);M.stop=stop;
  if(stop.left!=null)M.until=stop.st==='ask'||stop.st==='offer'?Date.now()+stop.left*1000:0;
  if(stop.st==='done'||stop.st==='gone'){M.until=0;if(was!=='done'&&was!=='gone')M.env?.api?.refresh?.().catch(()=>{});
    if(M.view==='ask')M.view='told';}
  if(same&&M.poll)return;   // nothing new (a poll): the page stays as it is (an amount being typed is kept)
  timers();if(M.dlg?.open)show();
}

function head(t,sub=''){return `<header class="cd-head"><span class="cd-badge" aria-hidden="true">👮</span><div class="grow"><h2 id="cdTitle">${t}</h2>${sub?`<p>${sub}</p>`:''}</div>${M.view==='ask'?'':'<button type="button" class="icon-btn" data-cd="close" aria-label="Đóng">✕</button>'}</header>`;}
function flash(){return M.flash?`<p class="cd-flash ${M.flash.kind}" role="status">${esc(M.flash.text)}</p>`:'';}
function html(){
  if(M.view==='force')return forceHTML();
  if(M.view==='stop')return stopHTML();
  return askHTML();
}

/* ------------------------------------------------------------------ the officer */
export async function openStop(env,who){
  M.env=env;M.view='stop';M.who={pid:who.pid,name:String(who.name||'Người chơi')};M.stop=null;M.until=0;M.flash=null;
  await show();
}
function stopHTML(){
  const s=M.stop,name=esc(M.who?.name||s?.name||'');
  if(s&&(s.st==='ask'||s.st==='offer')&&s.act!=='search'){
    const body=s.st==='ask'?`<p class="cd-line">⏳ Đang chờ <b>${name}</b> trả lời: ${esc(NAME[s.act])}.</p>`
      :`<p class="cd-line">💵 <b>${name}</b> đưa phong bì <b>${fmt(s.amount)} xu</b>.</p>
        <div class="cd-acts two"><button type="button" class="btn" data-cd="take">💵 Nhận</button><button type="button" class="btn primary" data-cd="refuse">Từ chối &amp; lập biên bản</button></div>`;
    return head('Kiểm tra',name)+`<div class="cd-body">${body}${bar()}${flash()}</div>`;
  }
  if(s&&s.act!=='search'&&(s.st==='done'||s.st==='gone')){
    // Nhận / Từ chối: the answer is the outcome (what was really taken, the Liêm chính): one line, not the same words twice.
    const dup=s.text&&M.flash?.text?.startsWith(s.text);
    return head('Kiểm tra',name)+`<div class="cd-body">${dup?'':`<p class="cd-line">${esc(s.text||'')}</p>`}${flash()}<div class="cd-acts"><button type="button" class="btn primary big" data-cd="close">Xong</button></div></div>`;
  }
  const can=s?.acts||null;   // after a search: what the evidence allows (before it: the server decides)
  const found=s?.text?`<p class="cd-found">${esc(s.text)}</p>`:'<p class="cd-line muted">Chọn việc cần làm. Chỉ xử lý người có dấu hiệu đánh bạc ăn tiền.</p>';
  const btns=ACTS.map(([id,e,l])=>{const off=M.busy||(can&&!can.includes(id))||(id==='search'&&s);
    return `<button type="button" class="btn cd-act${id==='search'?' search':''}" data-cd="act" data-act="${id}"${off?' disabled':''}><span aria-hidden="true">${e}</span>${l}</button>`;}).join('');
  return head('Kiểm tra',name)+`<div class="cd-body">${found}<div class="cd-grid">${btns}</div>${flash()}</div>`;
}

/* ------------------------------------------------------------------ the player stopped */
export function onLive(env,f){
  if(!f||!f.k||!f.id)return;
  M.env=env;
  if(f.k==='ask'){
    if(M.view==='ask'&&M.stop?.id===f.id)return;
    M.view='ask';M.give=false;M.flash=null;M.who={name:f.by||'Cán bộ'};
    take({id:f.id,act:f.act,st:'ask',role:'target',left:f.left??60,text:f.text});show();return;
  }
  if(M.stop?.id!==f.id){
    if(f.k==='done'){env.api?.refresh?.().catch(()=>{});if(f.text)env.toast?.(f.text,'info');}
    return;
  }
  if(f.k==='offer')take({...M.stop,st:'offer',amount:f.amount,left:f.left??60});
  else if(f.k==='done')take({...M.stop,st:'done',left:0,text:f.text?.replace(/^👮\s*/,'')||M.stop.text});
}
function askHTML(){
  const s=M.stop;if(!s)return head('Kiểm tra')+'<div class="cd-body"></div>';
  const by=esc(M.who?.name||'Cán bộ');
  if(M.view==='told'||s.st==='done'||s.st==='gone')
    return head('Kiểm tra',by)+`<div class="cd-body"><p class="cd-line">${esc(s.text||'')}</p>${flash()}<div class="cd-acts"><button type="button" class="btn primary big" data-cd="close">Đóng</button></div></div>`;
  if(s.st==='offer')
    return head('Kiểm tra',by)+`<div class="cd-body"><p class="cd-line">💵 Đã đưa phong bì ${fmt(s.amount)} xu. Chờ cán bộ…</p>${bar()}${flash()}</div>`;
  const wallet=Math.max(0,Number(M.env?.api?.state?.journey?.wallet)||0),top=Math.min(MAX,wallet);
  const give=M.give?`<form class="cd-give" novalidate><label for="cdAmount">Phong bì (xu)</label>
      <input id="cdAmount" type="number" inputmode="numeric" min="1" max="${top}" step="1" placeholder="1 – ${fmt(top)}" required>
      <div class="cd-acts two"><button type="button" class="btn" data-cd="nogive">Thôi</button><button type="submit" class="btn primary"${M.busy?' disabled':''}>Đưa</button></div></form>`
    :`<div class="cd-acts two"><button type="button" class="btn primary big" data-cd="coop"${M.busy?' disabled':''}>🤝 Hợp tác</button><button type="button" class="btn big" data-cd="envelope"${M.busy||top<1?' disabled':''}>💵 Đưa phong bì</button></div>`;
  return head('Công an kiểm tra',by)+`<div class="cd-body"><p class="cd-line"><b>${by}</b> yêu cầu: ${esc(NAME[s.act]||'')}.</p>${give}${bar()}<p class="cd-hint">Không trả lời: coi như hợp tác.</p>${flash()}</div>`;
}

/* ------------------------------------------------------------------ fallback: ask now and then while at Chợ đen */
export function watch(env){
  M.env=env;if(M.watch)return;
  M.watch=setInterval(async()=>{
    if(env.live?.()?.flags?.cand||M.view==='ask'||document.hidden)return;
    try{const d=await call(env,'cand_poll',{});const s=d?.stop;
      if(s&&s.role==='target'&&s.st==='ask')onLive(env,{k:'ask',id:s.id,act:s.act,by:s.name,left:s.left});}catch{/* offline a moment */}
  },WATCH_MS);
}
export function unwatch(){clearInterval(M.watch);M.watch=0;}

/* ------------------------------------------------------------------ 👥 commanders */
export async function openForce(env){
  M.env=env;M.view='force';M.force=null;M.flash=null;M.sure=null;await show();
  try{M.force=await call(env,'cand_force',{});}catch(e){M.flash={text:e.message||'Chưa tải được danh sách.',kind:'bad'};}
  if(M.view==='force')show();
}
function forceHTML(){
  const f=M.force;
  if(!f)return head('Toàn lực lượng')+`<div class="cd-body">${flash()||'<p class="cd-line muted">Đang tải…</p>'}</div>`;
  const rows=f.force.map(r=>{
    const sure=M.sure===r.pid;
    const btns=sure?`<div class="cd-sure"><p>Khai trừ <b>${esc(r.name)}</b> khỏi lực lượng? Không rút lại được.</p><div class="cd-acts two"><button type="button" class="btn" data-cd="unsure">Thôi</button><button type="button" class="btn danger" data-cd="out" data-pid="${esc(r.pid)}">Ký quyết định</button></div></div>`
      :`${r.can_hon&&f.hon_left?`<button type="button" class="btn small" data-cd="hon" data-pid="${esc(r.pid)}">🏅 Khen thưởng</button>`:r.hon?'<span class="cd-tag">🏅 Đã khen hôm nay</span>':''}${r.can_out?`<button type="button" class="btn small ghost" data-cd="sure" data-pid="${esc(r.pid)}">🚫 Khai trừ</button>`:''}`;
    return `<li class="cd-row${r.me?' me':''}"><div class="grow"><b data-no-translate>${esc(r.name)}</b>${r.me?' <small>(bạn)</small>':''}<small>${esc(r.grade)} · ${esc(r.post)}</small>${r.sev?'<small class="bad">⚠️ Có sai phạm nghiêm trọng</small>':''}</div><div class="cd-row-acts">${btns}</div></li>`;}).join('');
  const sub=`🏅 ${f.hon_left?'Còn 1 lượt khen hôm nay':'Hôm nay đã khen'} · 🚫 ${f.out_left} quyết định khai trừ`;
  return head('Toàn lực lượng',sub)+`<div class="cd-body">${flash()}<ul class="cd-list">${rows||'<li class="cd-line muted">Chưa có ai.</li>'}</ul>
    <p class="cd-hint">Khai trừ chỉ với cán bộ cấp dưới có sai phạm mức cao nhất trong 7 ngày (nhận hối lộ, xử lý sai gây nguy hiểm nghiêm trọng).</p></div>`;
}

/* ------------------------------------------------------------------ taps */
async function click(op,data={}){
  if(op==='close'){close();return;}
  if(M.busy)return;
  const env=M.env;
  const run=async(fn)=>{M.busy=true;M.flash=null;show();try{await fn();}catch(e){M.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};}finally{M.busy=false;if(M.view)show();}};
  switch(op){
    case'act':return run(async()=>{const d=await call(env,'cand_stop',{pid:M.who.pid,act:data.act});if(d.stop){if(!d.stop.name)d.stop.name=M.who.name;take(d.stop);}});
    case'take':case'refuse':return run(async()=>{const d=await call(env,'cand_decide',{id:M.stop.id,take:op==='take'});if(d.stop){if(d.message&&d.stop.st==='done')d.stop.text=d.message;take(d.stop);}M.flash={text:d.message,kind:op==='take'?'info':'good'};});
    // The answer's message counts what was really taken (a short wallet pays less than the fine as set, which the stop's
    // own line repeats): that one is shown, as the officer's page shows it.
    case'coop':return run(async()=>{const d=await call(env,'cand_answer',{id:M.stop.id,bribe:0});if(d.stop){if(d.message&&d.stop.st==='done')d.stop.text=d.message;take(d.stop);}M.view='told';env.api?.refresh?.().catch(()=>{});});
    case'envelope':M.give=true;show();return;
    case'nogive':M.give=false;show();return;
    case'give':{
      const n=Number(M.dlg.querySelector('#cdAmount')?.value);
      const wallet=Math.max(0,Number(env.api?.state?.journey?.wallet)||0);
      if(!Number.isInteger(n)||n<1||n>MAX){M.flash={text:`Phong bì từ 1 đến ${fmt(MAX)} xu.`,kind:'bad'};show();return;}
      if(n>wallet){M.flash={text:`Ví chỉ còn ${fmt(wallet)} xu.`,kind:'bad'};show();return;}
      return run(async()=>{const d=await call(env,'cand_answer',{id:M.stop.id,bribe:n});if(d.stop)take(d.stop);M.give=false;});
    }
    case'hon':return run(async()=>{const d=await call(env,'cand_hon',{pid:data.pid});M.force=await call(env,'cand_force',{});M.flash={text:d.message,kind:'good'};});
    case'sure':M.sure=data.pid;show();return;
    case'unsure':M.sure=null;show();return;
    case'out':return run(async()=>{const d=await call(env,'cand_out',{pid:data.pid,confirm:true});M.sure=null;M.force=await call(env,'cand_force',{});M.flash={text:d.message,kind:'good'};});
  }
}
