/** Registered accounts, including TikTok accounts, searched by username or name. */
import {esc,icon,num,TZ,toast} from './ui.js';

const date=value=>{
  if(!value)return 'Chưa ghi nhận';
  const d=new Date(String(value).replace(' ','T')+'Z');
  return Number.isNaN(d.getTime())?'Chưa ghi nhận':d.toLocaleString('vi-VN',{timeZone:TZ,day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
};

export class UsersAdmin{
  constructor(api,hooks){
    this.api=api;this.hooks=hooks;this.dlg=null;this.el=null;this.back=null;this.write=null;this.reset();
    if(typeof globalThis.addEventListener==='function')globalThis.addEventListener('hashchange',()=>this.close(true,false));
  }
  reset(){this.close(true,false);this.ctl?.abort();this.ctl=null;this.data=null;this.busy=false;this.error=null;this.q='';this.draft='';this.offset=0;}
  async load(){
    this.ctl?.abort();
    const ctl=this.ctl=new AbortController();
    this.busy=true;this.error=null;this.hooks.rerender();
    const query=new URLSearchParams({q:this.q,offset:String(this.offset),limit:'50'});
    try{
      const data=await this.api.get('/api/admin/users?'+query,undefined,ctl.signal);
      if(this.ctl===ctl)this.data=data;
    }catch(e){
      if(this.ctl!==ctl||e.aborted)return;
      if(e.status===401||e.status===403){this.close(true,false);this.hooks.forbidden();return;}
      this.error=e.message||'Không tải được danh sách người dùng.';
    }finally{
      if(this.ctl===ctl){this.ctl=null;this.busy=false;this.hooks.rerender();}
    }
  }
  meta(){return this.data?`${num(this.data.total)} tài khoản${this.q?' khớp tìm kiếm':''} · giờ Việt Nam`:'Danh sách tài khoản đã đăng ký';}
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    const form=`<form class="chat-search users-search" data-form="usersSearch" role="search">
      <label class="sr-only" for="users-query">Tìm theo tên hoặc username</label>
      <input id="users-query" name="q" type="search" data-act="usersQuery" maxlength="80" value="${esc(this.draft)}" autocomplete="off" placeholder="Tìm theo tên hoặc username">
      <button type="submit" class="btn primary sm">${icon('search',15)} Tìm</button>
      ${this.q?'<button type="button" class="btn ghost sm" data-act="usersClear">Bỏ tìm</button>':''}</form>`;
    const error=this.error?`<div class="notice bad" role="alert">${icon('alert',16)}<div>${esc(this.error)} <button type="button" class="btn ghost sm" data-act="usersReload">Thử lại</button></div></div>`:'';
    const d=this.data;
    let body='<p class="note" role="status">Đang tải danh sách…</p>';
    if(d){
      const rows=d.items.map(u=>`<tr><td><b>${esc(u.name)}</b>${u.display!==u.name?`<small class="muted">Tên tài khoản: ${esc(u.display)}</small>`:''}</td><td class="users-username">@${esc(u.username)}</td><td>${esc(date(u.created_at))}</td><td>${esc(date(u.last_active_at))}</td><td><button type="button" class="btn ghost sm" data-act="usersPassword" data-id="${esc(u.id)}" data-username="${esc(u.username)}">Đổi mật khẩu</button></td></tr>`).join('');
      const table=rows?`<div class="scroll"><table class="tbl users-table"><thead><tr><th scope="col">Tên</th><th scope="col">Username</th><th scope="col">Ngày tạo</th><th scope="col">Hoạt động gần nhất</th><th scope="col">Thao tác</th></tr></thead><tbody>${rows}</tbody></table></div>`:`<p class="note" role="status">${this.q?'Không tìm thấy người dùng khớp tên hoặc username.':'Chưa có tài khoản nào.'}</p>`;
      const paging=d.total?`<div class="users-pages"><span class="muted">${num(d.offset+1)}–${num(d.offset+d.items.length)} / ${num(d.total)} tài khoản</span><div>
        <button type="button" class="btn ghost sm" data-act="usersPrev"${this.busy||!d.offset?' disabled':''}>Trang trước</button>
        <button type="button" class="btn ghost sm" data-act="usersNext"${this.busy||!d.has_more?' disabled':''}>Trang sau</button></div></div>`:'';
      body=`<section class="card"><div class="card-head"><h2>Danh sách người dùng <small>${num(d.total)}</small></h2></div>${table}${paging}</section>`;
    }else if(this.error)body='';
    return `<div class="users-admin" aria-busy="${this.busy}">${form}<p class="note">Tìm một phần tên hoặc username, không phân biệt hoa thường. Bao gồm tên tài khoản và tên nhân vật hiện tại.</p>${error}${body}</div>`;
  }
  input(el){if(el.name==='q'&&el.closest?.('[data-form="usersSearch"]'))this.draft=el.value;}
  submit(form){
    if(form.dataset.form!=='usersSearch')return false;
    this.q=(form.elements.q?.value||'').trim().slice(0,80);this.draft=this.q;this.offset=0;this.data=null;this.load();return true;
  }
  action(act,ds={},from){
    switch(act){
      case'usersPassword':{
        const user=this.data?.items.find(u=>String(u.id)===String(ds.id)&&u.username===ds.username);
        if(user)this.open(user,from);return true;
      }
      case'usersReload':this.load();return true;
      case'usersClear':this.q='';this.draft='';this.offset=0;this.data=null;this.load();return true;
      case'usersPrev':if(!this.busy&&this.offset){this.offset=Math.max(0,this.offset-50);this.data=null;this.load();}return true;
      case'usersNext':if(!this.busy&&this.data?.has_more){this.offset+=50;this.data=null;this.load();}return true;
    }
    return false;
  }

  /** Passwords stay in these native inputs, never in the dialog state or its HTML. */
  open(user,from){
    if(this.write||typeof document==='undefined')return;
    this.close(true,false);
    this.dlg={id:user.id,username:user.username,name:user.name||user.display||user.username,sending:false};
    this.back=from||document.activeElement;
    if(!this.el){
      this.el=document.createElement('div');this.el.id='users-password-modal';document.body.append(this.el);
      this.el.addEventListener('click',ev=>{if(ev.target.closest('[data-act="usersPasswordCancel"]'))this.close();});
      this.el.addEventListener('input',()=>{if(!this.dlg?.sending)this.errorPassword('');});
      this.el.addEventListener('submit',ev=>{ev.preventDefault();return this.send();});
      this.el.addEventListener('keydown',ev=>{
        if(ev.key==='Escape'){ev.stopPropagation();this.close();}
        else if(ev.key==='Tab')this.trap(ev);
      });
    }
    const g=this.dlg,el=this.el;
    el.innerHTML=`<div class="modal-back" data-act="usersPasswordCancel"></div><div class="modal users-password-dialog" role="dialog" aria-modal="true" aria-labelledby="users-password-title" aria-describedby="users-password-account users-password-note" tabindex="-1">
      <div class="modal-head"><h2 id="users-password-title">Đổi mật khẩu</h2><button type="button" class="modal-x" data-act="usersPasswordCancel" aria-label="Đóng">${icon('x',20)}</button></div>
      <p class="users-password-account" id="users-password-account"><b>${esc(g.name)}</b><span class="users-username">@${esc(g.username)}</span></p>
      <form class="users-password-form" novalidate>
        <label for="users-password-new">Mật khẩu mới</label>
        <input id="users-password-new" name="password" type="password" autocomplete="new-password" minlength="8" maxlength="128" required aria-describedby="users-password-hint users-password-error">
        <p class="note" id="users-password-hint">Mật khẩu cần 8–128 ký tự.</p>
        <label for="users-password-confirm">Nhập lại mật khẩu</label>
        <input id="users-password-confirm" name="confirm" type="password" autocomplete="new-password" minlength="8" maxlength="128" required aria-describedby="users-password-error">
        <p class="note" id="users-password-note">Các phiên đăng nhập cũ của tài khoản này sẽ cần đăng nhập lại.</p>
        <p class="users-password-error" id="users-password-error" data-password-error role="alert" aria-live="polite"></p>
        <div class="users-password-buttons"><button type="button" class="btn ghost" data-act="usersPasswordCancel">Hủy</button><button type="submit" class="btn primary" data-password-save>Đổi mật khẩu</button></div>
      </form></div>`;
    el.hidden=false;document.body.classList.add('modal-open');el.querySelector('[name=password]')?.focus();
  }
  close(force=false,restore=true){
    if(this.dlg?.sending&&!force)return;
    const g=this.dlg,back=this.back;
    this.dlg=null;this.back=null;
    if(!this.el)return;
    this.el.querySelectorAll('input').forEach(input=>{input.value='';});
    this.el.innerHTML='';this.el.hidden=true;
    if(!document.body.querySelector('[aria-modal="true"]'))document.body.classList.remove('modal-open');
    if(restore){
      const target=back?.isConnected?back:[...document.body.querySelectorAll('[data-act="usersPassword"]')].find(el=>el.dataset.id===String(g?.id)&&el.dataset.username===g?.username);
      target?.focus({preventScroll:true});
    }
  }
  trap(ev){
    if(!this.dlg)return;
    const controls=[...this.el.querySelectorAll('button:not(:disabled),input:not(:disabled)')];
    if(!controls.length){ev.preventDefault();this.el.querySelector('[role=dialog]')?.focus();return;}
    const first=controls[0],last=controls[controls.length-1];   // no .at(): Safari 15.4+
    if(ev.shiftKey&&(document.activeElement===first||!controls.includes(document.activeElement))){ev.preventDefault();last.focus();}
    else if(!ev.shiftKey&&(document.activeElement===last||!controls.includes(document.activeElement))){ev.preventDefault();first.focus();}
  }
  errorPassword(message,field){
    const error=this.el?.querySelector('[data-password-error]');if(error)error.textContent=message;
    this.el?.querySelectorAll('input').forEach(input=>input.setAttribute('aria-invalid',String(input.name===field)));
    if(field)this.el?.querySelector(`[name=${field}]`)?.focus();
  }
  controlsPassword(sending){
    const form=this.el?.querySelector('form');form?.setAttribute('aria-busy',String(sending));
    this.el?.querySelectorAll('button,input').forEach(control=>{control.disabled=sending;});
    const save=this.el?.querySelector('[data-password-save]');if(save)save.textContent=sending?'Đang đổi…':'Đổi mật khẩu';
    if(sending)this.el?.querySelector('[role=dialog]')?.focus();
  }
  async send(){
    const g=this.dlg;if(!g||g.sending||this.write)return;
    const password=this.el.querySelector('[name=password]')?.value||'',confirm=this.el.querySelector('[name=confirm]')?.value||'';
    if([...password].length<8||[...password].length>128){this.errorPassword('Mật khẩu cần 8–128 ký tự.','password');return;}
    if(password!==confirm){this.errorPassword('Hai lần nhập mật khẩu chưa khớp.','confirm');return;}
    g.sending=true;this.write=g;this.errorPassword('');this.controlsPassword(true);
    try{
      // Do not abort or automatically retry a write: its outcome may already be committed.
      const out=await this.api.post('/api/admin/users/password',{id:g.id,username:g.username,password,confirm});
      if(out?.ok){
        if(this.dlg===g){
          this.close(true);
          toast(`Đã đổi mật khẩu cho @${g.username}. Các phiên cũ cần đăng nhập lại.`,'good');
        }
        // A confirmed self-reset revoked this session even if navigation already closed the dialog.
        if(out.reauthenticate)this.hooks.forbidden();
        return;
      }
      if(this.dlg!==g)return;
      throw new Error('Unconfirmed password reset');
    }catch(e){
      if(this.dlg!==g)return;
      if(e.status===401||e.status===403){this.close(true,false);this.hooks.forbidden();return;}
      g.sending=false;this.controlsPassword(false);
      // Use fixed messages so a server/network error can never echo submitted secrets.
      const message=e.status===429?'Thao tác quá nhanh. Chờ một chút rồi thử lại nhé.':
        e.status===404||e.status===409?'Tài khoản đã thay đổi hoặc không còn tồn tại. Đóng hộp thoại rồi tải lại danh sách.':
        e.status===400||e.status===422?'Mật khẩu không hợp lệ. Kiểm tra mật khẩu và phần nhập lại.':
        'Chưa xác nhận được kết quả. Kiểm tra kết nối và thử đăng nhập bằng mật khẩu mới trước khi gửi lại.';
      this.errorPassword(message);this.el.querySelector('[name=password]')?.focus();
    }finally{
      if(this.write===g)this.write=null;
    }
  }
}
