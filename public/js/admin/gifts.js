/** "🎁 Tặng xu": the accounts list of the operator site, with a gift of coins per player.
 *  GET  /api/admin/gifts?q=   accounts whose username starts with q (else the 50 newest), their latest gifts,
 *                             and "Quà đã tặng" (the last 50 gifts of the game)
 *  POST /api/admin/gift       {user, coins, rid, large?, title?, text?} -> {status: created | exists, gift}
 * The server queues the gift (game/system_gift.py, like scripts/grant_gift.py): the coins reach the player's
 * wallet at their next load, once, with the gift card. Nothing is written into a save from here.
 * One key (rid) per confirmed gift: a double click or a retry after a lost answer finds the same gift.
 * The dialog lives outside #view (its own element on <body>), so a list refresh never resets what is typed. */
import {esc,icon,hm,num,toast,tag} from './ui.js';

const CHIPS=[1000,10000,50000,100000];
const STATUS={pending:['Chờ vào game','warn'],applied:['Đã vào ví','info'],seen:['Đã xem thiệp','good']};
const defText=n=>`Ban quản lý phố tặng bạn ${num(n)} xu. Chơi vui nha! 💛`;
const newRid=()=>{try{return crypto.randomUUID();}catch{return [...crypto.getRandomValues(new Uint8Array(16))].map(b=>b.toString(16).padStart(2,'0')).join('');}};
/** "100.000" / "100 000" / "1e5" typed: the digits only. */
const parseCoins=s=>{const d=String(s??'').replace(/\D/g,'');return d?Number(d.slice(0,9)):0;};
const statusTag=s=>{const [l,t]=STATUS[s]||[s,''];return tag(l,t);};

export class GiftAdmin{
  /** hooks: {rerender(), forbidden()} */
  constructor(api,hooks){
    this.api=api;this.hooks=hooks;this.data=null;this.busy=false;this.error=null;this.q='';this.dlg=null;this.el=null;this.back=null;
    addEventListener('hashchange',()=>{if(this.dlg&&!this.dlg.sending)this.close();});  // another view: the dialog goes
  }
  reset(){this.data=null;this.error=null;this.close();}
  load(){
    if(this.busy)return;
    this.busy=true;this.error=null;
    this.api.get('/api/admin/gifts?'+new URLSearchParams({q:this.q}),20000)
      .then(d=>{this.data=d;})
      .catch(e=>{if(e.status===403||e.status===401){this.hooks.forbidden(e);return;}this.error=e.status===429?'Chậm lại một chút nhé.':e.message;})
      .finally(()=>{this.busy=false;this.hooks.rerender();});
  }
  get max(){return this.data?.max||100000;}
  get large(){return this.data?.large||1000;}
  meta(){const d=this.data;return d?`${num(d.users.length)} tài khoản${d.q?` bắt đầu bằng “${esc(d.q)}”`:' mới nhất'} · ${num(d.recent.length)} quà gần nhất`:'Tặng xu vào ví người chơi';}

  /* ---- the page ------------------------------------------------------------------------------ */
  view(){
    if(!this.data&&!this.busy&&!this.error)this.load();
    const form=`<form class="chat-search gift-search" data-form="giftSearch" role="search"><input type="search" name="q" value="${esc(this.q)}" maxlength="25" autocapitalize="none" autocorrect="off" spellcheck="false" placeholder="Tên đăng nhập (vd. be_na)" aria-label="Tìm tài khoản theo tên đăng nhập"><button type="submit" class="btn primary sm"${this.busy?' disabled':''}>${icon('search',15)} Tìm</button>${this.q?`<button type="button" class="btn ghost sm" data-act="giftClear">Bỏ tìm</button>`:''}</form>`;
    const note=`<p class="note">Tìm theo đầu tên đăng nhập; để trống: 50 tài khoản mới nhất. Xu vào 👛 Ví khi người chơi vào game lần tới (một lần, kèm thiệp “Quà từ Phố Có Chuyện”).</p>`;
    if(this.error&&!this.data)return `<div class="gift-admin">${form}<div class="notice bad">${icon('alert',16)}<div>${esc(this.error)}<br><button type="button" class="btn ghost sm" data-act="giftReload">Thử lại</button></div></div></div>`;
    if(!this.data)return `<div class="gift-admin">${form}<p class="note">Đang tải…</p></div>`;
    const d=this.data;
    const users=d.users.length?d.users.map(u=>this.userRow(u)).join(''):`<p class="note">${d.q?`Không có tài khoản nào bắt đầu bằng “${esc(d.q)}”.`:'Chưa có tài khoản nào.'}</p>`;
    const recent=d.recent.length?d.recent.map(g=>this.giftRow(g,true)).join(''):'<p class="note">Chưa tặng quà nào.</p>';
    return `<div class="gift-admin${this.busy?' is-busy':''}">${form}${note}
      <section class="card"><div class="card-head"><h2>Người chơi <small>${num(d.users.length)}</small></h2></div><div class="gift-users">${users}</div></section>
      <section class="card"><div class="card-head"><h2>Quà đã tặng <small>50 gần nhất</small></h2></div><div class="gift-list">${recent}</div></section></div>`;
  }
  userRow(u){
    const gifts=u.gifts.length?`<div class="gift-mini">${u.gifts.map(g=>this.giftRow(g,false)).join('')}${u.gift_count>u.gifts.length?`<small class="muted">và ${num(u.gift_count-u.gifts.length)} quà cũ hơn</small>`:''}</div>`:'';
    const sum=u.gift_count?`<small class="muted"> · đã tặng ${num(u.gift_count)} quà, ${num(u.gift_coins)} xu</small>`:'';
    return `<div class="gift-user"><div class="grow"><b>@${esc(u.username)}</b> <span class="gift-name">${esc(u.display)}</span><br><small class="muted">tạo ${esc(String(u.created_at||'').slice(0,10))}</small>${sum}${gifts}</div>`+
      `<button type="button" class="btn primary sm" data-act="giftOpen" data-id="${esc(u.username)}" data-value="${esc(u.display)}">🎁 Tặng xu</button></div>`;
  }
  giftRow(g,who){
    const to=who?(g.user?`<b>@${esc(g.user)}</b> `:'<b>khách</b> '):'';
    const when=`tặng ${hm(g.created)}`+(g.applied_at?` · vào ví ${hm(g.applied_at)}`:'')+(g.seen_at?` · xem ${hm(g.seen_at)}`:'');
    return `<div class="gift-row">${to}<b class="gift-coins">+${num(g.coins)} xu</b> ${statusTag(g.status)} <small class="muted">${when} · ${g.by?`bởi @${esc(g.by)}`:'bằng công cụ'}</small>`+
      (who?`<div class="gift-words"><b>${esc(g.title)}</b> — ${esc(g.text)}</div>`:'')+`</div>`;
  }

  /* ---- the dialog ---------------------------------------------------------------------------- */
  open(user,display,from){
    this.back=from||null;
    this.dlg={user,display,coins:0,amount:'',title:this.data?.title||'Quà từ Phố Có Chuyện',text:'',edited:false,step:'form',sure:false,rid:'',sending:false,error:''};
    if(!this.el){
      this.el=document.createElement('div');this.el.id='gift-modal';document.body.append(this.el);
      this.el.addEventListener('click',ev=>this.click(ev));
      this.el.addEventListener('input',ev=>this.input(ev.target));
      this.el.addEventListener('change',ev=>{if(ev.target.name==='sure'){this.dlg.sure=ev.target.checked;this.paint();}});
      this.el.addEventListener('submit',ev=>{ev.preventDefault();this.next();});
      this.el.addEventListener('keydown',ev=>{if(ev.key==='Escape'&&this.dlg&&!this.dlg.sending){ev.stopPropagation();this.close();}else if(ev.key==='Tab')this.trap(ev);});
    }
    this.paint();
    this.el.querySelector('[name=amount]')?.focus();
  }
  close(){
    if(!this.el)return;
    this.dlg=null;this.el.innerHTML='';this.el.hidden=true;document.body.classList.remove('modal-open');
    const b=this.back;this.back=null;if(b?.isConnected)b.focus({preventScroll:true});
  }
  /** Keep Tab inside the dialog. */
  trap(ev){
    const f=[...this.el.querySelectorAll('button:not(:disabled),input:not(:disabled),textarea:not(:disabled)')];if(!f.length)return;
    const first=f[0],last=f[f.length-1];
    if(ev.shiftKey&&document.activeElement===first){ev.preventDefault();last.focus();}
    else if(!ev.shiftKey&&document.activeElement===last){ev.preventDefault();first.focus();}
  }
  problem(){
    const g=this.dlg;
    if(!g.coins)return 'Nhập số xu.';
    if(g.coins>this.max)return `Tối đa ${num(this.max)} xu một lần.`;
    if(!g.title.trim())return 'Cần tiêu đề thiệp.';
    if(g.title.trim().length>(this.data?.title_max||80))return `Tiêu đề tối đa ${num(this.data?.title_max||80)} ký tự.`;
    if(g.text.trim().length>(this.data?.text_max||300))return `Lời nhắn tối đa ${num(this.data?.text_max||300)} ký tự.`;
    return '';
  }
  words(){const g=this.dlg;return g.edited&&g.text.trim()?g.text:defText(g.coins||0);}
  input(t){
    const g=this.dlg;if(!g)return;
    if(t.name==='amount'){g.amount=t.value;g.coins=parseCoins(t.value);this.paintForm();}
    else if(t.name==='title'){g.title=t.value;this.paintForm();}
    else if(t.name==='text'){g.text=t.value;g.edited=true;this.paintForm();}
  }
  /** Redraw only the live parts of the form (the fields keep their caret). */
  paintForm(){
    const g=this.dlg,el=this.el;if(!g||g.step!=='form')return;
    const p=this.problem(),out=el.querySelector('[data-out]'),err=el.querySelector('[data-err]'),go=el.querySelector('[data-go-next]'),cnt=el.querySelector('[data-count]');
    if(out)out.innerHTML=g.coins?`= <b>${num(g.coins)} xu</b>${g.coins>this.large?` ${tag('trên '+num(this.large)+' xu: sẽ hỏi lại','warn')}`:''}`:'&nbsp;';
    if(err)err.textContent=g.coins||g.amount?p:'';
    if(go)go.disabled=!!p;
    el.querySelectorAll('[data-chip]').forEach(c=>{const on=Number(c.dataset.chip)===g.coins;c.classList.toggle('on',on);c.setAttribute('aria-pressed',on);});
    const ta=el.querySelector('[name=text]');if(ta&&!g.edited)ta.value=defText(g.coins||0);
    if(cnt)cnt.textContent=`${num(this.words().length)}/${num(this.data?.text_max||300)}`;
  }
  paint(){
    const g=this.dlg,el=this.el;if(!g||!el)return;
    el.hidden=false;document.body.classList.add('modal-open');
    const who=`<b>@${esc(g.user)}</b>${g.display?` <span class="gift-name">(${esc(g.display)})</span>`:''}`;
    let body;
    if(g.step==='form'){
      body=`<form class="gift-form" novalidate>
        <label for="gift-amount">Số xu</label>
        <div class="chips gift-chips">${CHIPS.map(n=>`<button type="button" class="chip" data-chip="${n}" aria-pressed="false">${num(n)}</button>`).join('')}</div>
        <input id="gift-amount" name="amount" inputmode="numeric" autocomplete="off" maxlength="12" placeholder="vd. 10.000" value="${esc(g.amount)}">
        <p class="gift-out" data-out aria-live="polite">&nbsp;</p>
        <label for="gift-title">Tiêu đề thiệp</label>
        <input id="gift-title" name="title" maxlength="${this.data?.title_max||80}" value="${esc(g.title)}">
        <label for="gift-text">Lời nhắn <small>(để như mẫu hoặc sửa tùy ý)</small></label>
        <textarea id="gift-text" name="text" rows="3" maxlength="${this.data?.text_max||300}">${esc(g.edited?g.text:defText(g.coins||0))}</textarea>
        <div class="gift-foot"><span class="count" data-count></span><span class="gift-err" data-err role="alert"></span></div>
        <div class="gift-btns"><button type="button" class="btn ghost" data-act="giftCancel">Hủy</button><button type="submit" class="btn primary" data-go-next disabled>Tiếp tục ${icon('chevron',15)}</button></div>
      </form>`;
    }else{
      const big=g.coins>this.large;
      body=`<div class="gift-confirm">
        <p class="gift-ask">Tặng <b class="gift-big">${num(g.coins)} xu</b> cho ${who}?</p>
        <div class="gift-card"><b>🎁 ${esc(g.title.trim())}</b><span>${esc(this.words().trim())}</span></div>
        <p class="note">Xu vào ví khi @${esc(g.user)} vào game lần tới. Gửi rồi thì không rút lại được.</p>
        ${big?`<div class="notice warn">${icon('alert',16)}<div><b>Số lớn: ${num(g.coins)} xu</b> (trên ${num(this.large)} xu).<label class="gift-sure"><input type="checkbox" name="sure"${g.sure?' checked':''}${g.sending?' disabled':''}><span>Tôi chắc chắn tặng đúng <b>${num(g.coins)} xu</b> cho @${esc(g.user)}</span></label></div></div>`:''}
        ${g.error?`<div class="notice bad" role="alert">${icon('alert',16)}<div>${esc(g.error)}</div></div>`:''}
        <div class="gift-btns"><button type="button" class="btn ghost" data-act="giftBack"${g.sending?' disabled':''}>${icon('back',15)} Sửa lại</button><button type="button" class="btn primary" data-act="giftSend"${g.sending||big&&!g.sure?' disabled':''}>${g.sending?'Đang gửi…':g.error?'Thử lại':`Xác nhận tặng ${num(g.coins)} xu`}</button></div>
      </div>`;
    }
    el.innerHTML=`<div class="modal-back" data-act="giftCancel"></div><div class="modal" role="dialog" aria-modal="true" aria-labelledby="gift-h"><div class="modal-head"><h2 id="gift-h">🎁 Tặng xu cho ${who}</h2><button type="button" class="modal-x" data-act="giftCancel" aria-label="Đóng"${g.sending?' disabled':''}>${icon('x',20)}</button></div>${body}</div>`;
    if(g.step==='form')this.paintForm();
  }
  next(){
    const g=this.dlg;if(!g||g.step!=='form'||this.problem())return;
    g.step='confirm';g.sure=false;g.error='';g.rid=newRid();   // one key per confirmed gift: retries reuse it
    this.paint();this.el.querySelector(g.coins>this.large?'[name=sure]':'[data-act=giftSend]')?.focus();
  }
  async send(){
    const g=this.dlg;if(!g||g.sending||g.step!=='confirm')return;
    const big=g.coins>this.large;if(big&&!g.sure)return;
    g.sending=true;g.error='';this.paint();
    try{
      const out=await this.api.post('/api/admin/gift',{user:g.user,coins:g.coins,rid:g.rid,large:big,title:g.title.trim(),text:this.words().trim()},20000);
      const n=num(out.gift?.coins??g.coins);
      toast(out.status==='exists'?`Quà này đã có rồi (không tặng thêm): ${n} xu cho @${g.user}.`:`Đã tặng ${n} xu cho @${g.user}. Xu vào ví ở lần vào game tới.`,'good');
      this.close();this.load();
    }catch(e){
      if(!this.dlg)return;
      g.sending=false;
      if(e.status===403||e.status===401){this.close();this.hooks.forbidden(e);return;}
      g.error=e.status===429?'Chậm lại một chút rồi thử lại nhé.':e.message;   // the same key: a retry cannot make a second gift
      this.paint();this.el.querySelector('[data-act=giftSend]')?.focus();
    }
  }
  click(ev){
    const g=this.dlg;if(!g)return;
    const chip=ev.target.closest('[data-chip]');
    if(chip){g.coins=Number(chip.dataset.chip);g.amount=num(g.coins);const a=this.el.querySelector('[name=amount]');if(a)a.value=g.amount;this.paintForm();return;}
    const el=ev.target.closest('[data-act]');if(!el)return;
    switch(el.dataset.act){
      case'giftCancel':if(!g.sending)this.close();return;
      case'giftBack':g.step='form';g.error='';this.paint();this.el.querySelector('[name=amount]')?.focus();return;
      case'giftSend':this.send();return;
    }
  }

  /* ---- hooks from main.js ---------------------------------------------------------------------- */
  /** true when the click was ours. */
  action(act,ds,el){
    switch(act){
      case'giftReload':this.error=null;this.load();this.hooks.rerender();return true;
      case'giftClear':this.q='';this.load();this.hooks.rerender();return true;
      case'giftOpen':this.open(ds.id,ds.value,el);return true;
    }
    return false;
  }
  submit(form){
    if(form.dataset.form!=='giftSearch')return false;
    this.q=(form.elements.q?.value||'').trim().slice(0,25);this.data=null;this.load();this.hooks.rerender();return true;
  }
}
