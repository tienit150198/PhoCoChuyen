/** Optional account (Settings → Tài khoản, day-summary nudge, journey chip).
 * Play starts anonymously; an account keeps the same save across devices and
 * browser resets. Every rule lives in game/accounts.py; this only renders forms
 * and posts them. Passwords never touch the game state or local storage. */
import {icon,escapeHTML as esc} from '../icons.js';
import {disablePush} from './push.js';

const NUDGE_KEY='mnl.accountNudge';
const btn=(label,action,data={},style='',extra='')=>`<button type="button" class="btn ${style}" data-action="${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${extra}>${label}</button>`;
const dismissed=()=>{try{return localStorage.getItem(NUDGE_KEY)==='off';}catch{return false;}};
const field=(id,label,type,auto,extra='')=>`<label class="field" for="${id}">${label}<input class="input" id="${id}" name="${id.replace(/^acct-/,'')}" type="${type}" autocomplete="${auto}" data-preserve ${extra}></label>`;
const USER_ATTRS='required minlength="3" maxlength="24" autocapitalize="none" autocorrect="off" spellcheck="false" pattern="[A-Za-z0-9_.]{3,24}"';

function errorLine(ui){return `<p class="acct-error" role="alert" aria-live="polite">${ui.acctError?`${icon('alert',15)} ${esc(ui.acctError)}`:''}</p>`;}

/** Small card: "keep your progress". Hidden once signed in or dismissed on this device. */
export function accountNudge(env){
  const {api}=env;
  if(api.account||dismissed())return '';
  return `<article class="acct-nudge"><span class="acct-nudge-ic" aria-hidden="true">${icon('cloud',22)}</span><div class="grow"><b>Tạo tài khoản để giữ tiến trình</b><p class="small muted">Đổi máy hay lỡ xóa dữ liệu trình duyệt vẫn chơi tiếp được.</p>
    <div class="row wrap">${btn('Tạo tài khoản','v4AccountOpen',{mode:'register'},'cream small')}${btn('Để sau','v4AccountDismiss',{},'ghost small')}</div></div></article>`;
}

/** Chip for the journey header: who is signed in, or a way in. */
export function accountChip(env){
  const a=env.api.account;
  return a?btn(`${icon('user',16)}<span>${esc(a.display)}</span>`,'v4AccountOpen',{},'ghost small acct-chip',` aria-label="Tài khoản: ${esc(a.display)}"`)
    :btn(`${icon('user',16)}<span>Tài khoản</span>`,'v4AccountOpen',{mode:'login'},'ghost small acct-chip');
}

/** Settings → Tài khoản. */
export function accountPane(env){
  const {api,ui}=env,a=api.account;
  if(a)return `<section class="settings-block"><h3>${icon('user',18)} Tài khoản</h3>
      <p class="acct-who">${icon('cloud',18)}<span>Đang đăng nhập: <b>${esc(a.display)}</b> <small class="muted">(${esc(a.username)})</small></span></p>
      <div class="row wrap">${btn('💍 Hôn nhân · mã người chơi','marriage',{},'cream')}${btn(`${icon('exit',16)} Đăng xuất`,'v4AccountLogout',{},'ghost')}</div></section>
    <form id="accountPasswordForm" class="settings-block acct-form" novalidate><h3>${icon('lock',18)} Đổi mật khẩu</h3>
      <input type="text" name="username" autocomplete="username" value="${esc(a.username)}" hidden>
      ${field('acct-current','Mật khẩu hiện tại','password','current-password','required maxlength="128"')}
      ${field('acct-new','Mật khẩu mới','password','new-password','required minlength="8" maxlength="128"')}
      ${field('acct-new2','Nhập lại mật khẩu mới','password','new-password','required minlength="8" maxlength="128"')}
      <p class="small acct-warn">${icon('alert',15)} Nhớ kỹ mật khẩu — hiện chưa có cách lấy lại.</p>
      ${errorLine(ui)}<button class="btn primary full" type="submit">Đổi mật khẩu</button></form>`;
  const mode=ui.acctMode==='login'?'login':'register';
  const tabs=`<div class="segmented acct-switch" role="tablist">${[['register','Tạo tài khoản'],['login','Đăng nhập']].map(([id,label])=>`<button type="button" role="tab" aria-selected="${id===mode}" class="${id===mode?'active':''}" data-action="v4AccountMode" data-mode="${id}">${label}</button>`).join('')}</div>`;
  const form=mode==='register'
    ?`<form id="accountRegisterForm" class="acct-form" novalidate>
      <p class="small muted">Tiến trình đang chơi được giữ nguyên và gắn vào tài khoản mới.</p>
      ${field('acct-username','Tên đăng nhập','text','username',USER_ATTRS)}
      <small class="muted acct-hint">3–24 ký tự: chữ không dấu, số, dấu chấm hoặc gạch dưới.</small>
      ${field('acct-display','Tên hiển thị','text','nickname','required maxlength="24"')}
      ${field('acct-password','Mật khẩu','password','new-password','required minlength="8" maxlength="128"')}
      ${field('acct-confirm','Nhập lại mật khẩu','password','new-password','required minlength="8" maxlength="128"')}
      <p class="small acct-warn">${icon('alert',15)} Nhớ kỹ mật khẩu — hiện chưa có cách lấy lại.</p>
      ${errorLine(ui)}<button class="btn primary full" type="submit">Tạo tài khoản</button></form>`
    :`<form id="accountLoginForm" class="acct-form" novalidate>
      ${field('acct-username','Tên đăng nhập','text','username',USER_ATTRS)}
      ${field('acct-password','Mật khẩu','password','current-password','required maxlength="128"')}
      ${errorLine(ui)}<button class="btn primary full" type="submit">Đăng nhập</button></form>`;
  return `<section class="settings-block"><h3>${icon('cloud',18)} Giữ tiến trình</h3>${tabs}${form}</section>`;
}

async function send(env,form,route,body){
  const {api,ui,renderSheet}=env,submit=form.querySelector('[type=submit]');
  ui.acctError='';if(submit)submit.disabled=true;
  try{return await api.accountPost(route,body);}
  catch(error){
    if(error.data?.code==='confirm_replace')throw error;
    ui.acctError=error.message||'Chưa thực hiện được. Thử lại nhé.';renderSheet();return null;
  }finally{if(submit&&submit.isConnected)submit.disabled=false;}
}
const val=(f,name)=>f.querySelector(`[name="${name}"]`)?.value??'';

export async function accountSubmit(f,env){
  const {api,ui,toast,renderSheet,confirmAction}=env;
  if(f.id==='accountRegisterForm'){
    const body={username:val(f,'username').trim(),display:val(f,'display').trim(),password:val(f,'password'),confirm:val(f,'confirm')};
    const local=!/^[A-Za-z0-9_.]{3,24}$/.test(body.username)?'Tên đăng nhập cần 3–24 ký tự: chữ thường không dấu, số, dấu chấm hoặc gạch dưới.'
      :!body.display?'Nhập tên hiển thị nhé.':body.password.length<8?'Mật khẩu cần ít nhất 8 ký tự.':body.password!==body.confirm?'Hai lần nhập mật khẩu chưa khớp.':'';
    if(local){ui.acctError=local;renderSheet();return true;}
    const r=await send(env,f,'register',body);
    if(r){f.reset();toast(r.message);await api.refresh().catch(()=>{});renderSheet();}
    return true;
  }
  if(f.id==='accountLoginForm'){
    const body={username:val(f,'username').trim(),password:val(f,'password')};
    if(!body.username||!body.password){ui.acctError='Nhập tên đăng nhập và mật khẩu nhé.';renderSheet();return true;}
    let r;
    try{r=await send(env,f,'login',body);}
    catch(error){
      if(!await confirmAction('Thay tiến trình trên máy này?','Tiến trình đang chơi trên máy này sẽ được thay bằng tiến trình của tài khoản. Muốn giữ thì xuất bản lưu trước nhé.','Đăng nhập'))return true;
      try{r=await send(env,f,'login',{...body,replace:true});}catch{r=null;}
    }
    if(r){toast(r.message);setTimeout(()=>location.replace('/'),600);}
    return true;
  }
  if(f.id==='accountPasswordForm'){
    const body={current:val(f,'current'),password:val(f,'new'),confirm:val(f,'new2')};
    const local=!body.current?'Nhập mật khẩu hiện tại nhé.':body.password.length<8?'Mật khẩu mới cần ít nhất 8 ký tự.':body.password!==body.confirm?'Hai lần nhập mật khẩu chưa khớp.':'';
    if(local){ui.acctError=local;renderSheet();return true;}
    const r=await send(env,f,'password',body);
    if(r){f.reset();toast(r.message);renderSheet();}
    return true;
  }
  return false;
}

export async function accountAction(action,data,el,env){
  const {api,ui,renderSheet,openSheet,toast,confirmAction}=env;
  switch(action){
    case'v4AccountOpen':ui.acctError='';if(data.mode)ui.acctMode=data.mode;openSheet('settings',{setTab:'account'});return true;
    case'v4AccountMode':ui.acctMode=data.mode;ui.acctError='';renderSheet();return true;
    case'v4AccountDismiss':try{localStorage.setItem(NUDGE_KEY,'off');}catch{/* storage blocked: hide for now */}el.closest('.acct-nudge')?.remove();return true;
    case'v4AccountLogout':{
      if(!await confirmAction('Đăng xuất khỏi máy này?','Tiến trình vẫn nằm trong tài khoản. Máy này sẽ bắt đầu một phiên chơi mới.','Đăng xuất'))return true;
      try{
        // Only this browser's own push subscription leaves with it (never the other devices').
        const reg=await navigator.serviceWorker?.getRegistration('/').catch(()=>null),sub=reg?await reg.pushManager?.getSubscription().catch(()=>null):null;
        if(sub)await disablePush(api).catch(()=>{});
        const r=await api.accountPost('logout',{});toast(r.message);setTimeout(()=>location.replace('/'),600);}catch(e){toast(e.message,true);}
      return true;
    }
  }
  return false;
}
