import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {UsersAdmin} from '../public/js/admin/users.js';

// Only the DOM surface used by this body-owned dialog; real rendering is also browser-tested.
const decode=s=>s.replace(/&(amp|lt|gt|quot|#39);/g,(_,k)=>({amp:'&',lt:'<',gt:'>',quot:'"','#39':"'"}[k]));
class Element{
  constructor(tag,doc){this.tagName=tag.toUpperCase();this.doc=doc;this.children=[];this.listeners={};this.attrs={};this.dataset={};this.value='';this.disabled=false;this.hidden=false;this._html='';this.textContent='';this.classes=new Set();this.classList={add:x=>this.classes.add(x),remove:x=>this.classes.delete(x),contains:x=>this.classes.has(x)};}
  get isConnected(){return this===this.doc.body||!!this.parentElement?.isConnected;}
  setAttribute(k,v){this.attrs[k]=String(v);if(k==='id')this.id=String(v);if(k==='name')this.name=String(v);if(k==='type')this.type=String(v);if(k==='value')this.value=String(v);if(k==='disabled')this.disabled=true;if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=String(v);}
  getAttribute(k){return this.attrs[k]??null;}
  append(child){child.parentElement=this;this.children.push(child);}
  remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(x=>x!==this);this.parentElement=null;}
  set innerHTML(html){for(const c of this.children)c.parentElement=null;this.children=[];this._html=html;const stack=[this];for(const m of html.matchAll(/<\/?([\w-]+)([^>]*)>/g)){if(m[0][1]==='/'){if(stack.length>1)stack.pop();continue;}const child=new Element(m[1],this.doc);for(const a of m[2].matchAll(/([\w-]+)(?:="([^"]*)"|'([^']*)'|=([^\s>]+))?/g))child.setAttribute(a[1],decode(a[2]??a[3]??a[4]??''));stack.at(-1).append(child);if(!['input','br','hr','img','path'].includes(m[1]))stack.push(child);}}
  get innerHTML(){return this._html;}
  matches(selector){if(selector.includes(':not(:disabled)')){if(this.disabled)return false;selector=selector.replace(':not(:disabled)','');}if(selector.startsWith('#'))return this.id===selector.slice(1);const attr=selector.match(/^\[([^=\]]+)(?:=["']?([^"'\]]+)["']?)?\]$/);if(attr)return Object.hasOwn(this.attrs,attr[1])&&(attr[2]===undefined||this.attrs[attr[1]]===attr[2]);return this.tagName===selector.toUpperCase();}
  querySelectorAll(selector){const choices=selector.split(',').map(s=>s.trim()),out=[];const visit=p=>{for(const c of p.children){if(choices.some(s=>c.matches(s)))out.push(c);visit(c);}};visit(this);return out;}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  closest(selector){for(let p=this;p;p=p.parentElement)if(p.matches(selector))return p;return null;}
  focus(){this.doc.activeElement=this;}
  addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}
  async emit(type,extra={}){const ev={target:this,key:'',shiftKey:false,preventDefault(){this.prevented=true;},stopPropagation(){this.stopped=true;},...extra};await Promise.all((this.listeners[type]||[]).map(fn=>fn(ev)));return ev;}
}
const account={id:7,username:'hong.nguyen',display:'Nguyễn Hồng',name:'Bé Đào',created_at:'2026-10-01 12:00:00',last_active_at:'2026-10-04 01:00:00'};
const page=()=>({q:'Bé',offset:50,limit:50,total:101,has_more:true,items:[account,{...account,id:8,username:'other',name:'Người khác'}]});
function fixture(post=async()=>({ok:true,username:account.username,display:account.display,message:'Đã đổi mật khẩu.',reauthenticate:false})){
  const doc={activeElement:null,createElement:tag=>new Element(tag,doc),getElementById:id=>doc.body.querySelector('#'+id)};doc.body=new Element('body',doc);
  const toasts=doc.createElement('div');toasts.setAttribute('id','toasts');doc.body.append(toasts);
  const view=doc.createElement('div');view.setAttribute('id','view');doc.body.append(view);
  const from=doc.createElement('button');view.append(from);from.focus();
  const listeners={};globalThis.document=doc;globalThis.addEventListener=(type,fn)=>(listeners[type]??=[]).push(fn);globalThis.setTimeout=()=>0;
  const writes=[],events=[];
  const api={get:async()=>page(),post:(...args)=>{writes.push(args);return post(...args);}};
  const users=new UsersAdmin(api,{rerender:()=>events.push('render'),forbidden:()=>events.push('forbidden')});users.data=page();users.q='Bé';users.draft='Bé';users.offset=50;
  const open=(u=account)=>{assert.equal(users.action('usersPassword',{id:String(u.id),username:u.username},from),true,'recognizes the row password action');const modal=doc.getElementById('users-password-modal');assert.ok(modal&&!modal.hidden,'opens the body-owned password dialog');return modal;};
  const fill=(modal,password='new-password-123',confirm=password)=>{modal.querySelector('[name=password]').value=password;modal.querySelector('[name=confirm]').value=confirm;};
  const submit=modal=>modal.emit('submit',{target:modal.querySelector('form')});
  const cancel=modal=>modal.emit('click',{target:modal.querySelector('[data-act=usersPasswordCancel]')});
  return {users,doc,view,from,toasts,listeners,writes,events,open,fill,submit,cancel};
}
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};

test('constructor and directory still work without browser globals',()=>{
  delete globalThis.document;delete globalThis.addEventListener;
  const users=new UsersAdmin({},{});users.data=page();assert.match(users.view(),/Bé Đào/);
});
test('every directory row includes an escaped password action with the account identity',()=>{
  const f=fixture();const html=f.users.view();assert.equal((html.match(/data-act="usersPassword"/g)||[]).length,2);
  assert.match(html,/data-id="7" data-username="hong\.nguyen"/);assert.match(html,/Đổi mật khẩu/);
  f.users.data.items=[{...account,name:'<img onerror="bad">',display:'&alias',username:'x" onclick="bad'}];
  const escaped=f.users.view();assert.ok(!escaped.includes('<img onerror='));assert.ok(!escaped.includes('data-username="x" onclick='));assert.ok(escaped.includes('&quot;'));
});
test('selected account opens outside the refreshed view with safe labels and empty native inputs',()=>{
  const f=fixture();const modal=f.open();assert.equal(modal.parentElement,f.doc.body);assert.match(modal.innerHTML,/Bé Đào/);assert.match(modal.innerHTML,/@hong\.nguyen/);
  for(const name of ['password','confirm']){const input=modal.querySelector(`[name=${name}]`);assert.equal(input.type,'password');assert.equal(input.getAttribute('autocomplete'),'new-password');assert.equal(input.getAttribute('minlength'),'8');assert.equal(input.getAttribute('maxlength'),'128');assert.equal(input.value,'');}
  assert.equal(f.doc.activeElement,modal.querySelector('[name=password]'));f.fill(modal);f.view.innerHTML=f.users.view();assert.equal(modal.querySelector('[name=password]').value,'new-password-123');
  assert.ok(!JSON.stringify(f.users.dlg).includes('new-password-123'));assert.ok(!modal.innerHTML.includes('new-password-123'));
});
test('unmatched row identities cannot select a different account',()=>{
  const f=fixture();assert.equal(f.users.action('usersPassword',{id:'7',username:'other'},f.from),true);assert.equal(f.doc.getElementById('users-password-modal'),null);assert.equal(f.writes.length,0);
});
test('cancel clears native values, closes and returns focus without sending',async()=>{
  const f=fixture();const modal=f.open();f.fill(modal);const input=modal.querySelector('[name=password]');await f.cancel(modal);assert.equal(f.writes.length,0);assert.equal(input.value,'');assert.equal(modal.innerHTML,'');assert.equal(modal.hidden,true);assert.equal(f.users.dlg,null);assert.equal(f.doc.activeElement,f.from);
});
test('short, long and mismatched passwords leave the same dialog open without a mutation',async()=>{
  for(const [password,confirm] of [['short','short'],['a'.repeat(129),'a'.repeat(129)],['good-password','different-password']]){
    const f=fixture();const modal=f.open();f.fill(modal,password,confirm);await f.submit(modal);assert.equal(f.writes.length,0);assert.equal(modal.hidden,false);assert.ok(modal.querySelector('[data-password-error]').textContent);assert.equal(modal.querySelector('[name=password]').value,password);assert.ok(!JSON.stringify(f.users.dlg).includes(password));
  }
});
test('one submit locks all controls, resists cancel/reopen and sends the exact selected identity',async()=>{
  const pending=deferred();const f=fixture(()=>pending.promise);const modal=f.open();f.fill(modal,'  strong password  ');const sending=f.submit(modal);await Promise.resolve();await f.submit(modal);
  assert.equal(f.writes.length,1);assert.equal(f.writes[0][0],'/api/admin/users/password');assert.deepEqual(f.writes[0][1],{id:7,username:'hong.nguyen',password:'  strong password  ',confirm:'  strong password  '});
  assert.ok(modal.querySelectorAll('button,input').every(el=>el.disabled));assert.equal(f.writes[0][3],undefined,'write is never given an abort signal');await f.cancel(modal);assert.equal(modal.hidden,false);
  f.users.action('usersPassword',{id:'8',username:'other'},f.from);assert.match(modal.innerHTML,/@hong\.nguyen/);assert.ok(!JSON.stringify(f.users.dlg).includes('strong password'));
  pending.resolve({ok:true,username:account.username,display:account.display,message:'Đã đổi mật khẩu.',reauthenticate:false});await sending;
  assert.equal(modal.hidden,true);assert.equal(f.toasts.children.length,1);assert.match(f.toasts.children[0].textContent,/@hong\.nguyen/);assert.equal(f.users.q,'Bé');assert.equal(f.users.offset,50);
});
test('an API error stays inline, retains editable inputs and does not echo a password or retry',async()=>{
  const f=fixture(async()=>{throw Object.assign(new Error('new-password-123 leaked upstream'),{status:429});});const modal=f.open();f.fill(modal);await f.submit(modal);
  const error=modal.querySelector('[data-password-error]').textContent;assert.ok(error);assert.ok(!error.includes('new-password-123'));assert.equal(modal.querySelector('[name=password]').value,'new-password-123');assert.ok(modal.querySelectorAll('button,input').every(el=>!el.disabled));assert.equal(f.writes.length,1);assert.equal(f.toasts.children.length,0);
});
test('network errors say the outcome is unconfirmed and require an explicit retry',async()=>{
  const f=fixture(async()=>{throw new Error('Disconnected');});const modal=f.open();f.fill(modal);await f.submit(modal);assert.match(modal.querySelector('[data-password-error]').textContent,/Chưa xác nhận|chưa xác nhận/);assert.equal(f.writes.length,1);
});
test('reset removes passwords and a pending self-reset reauthenticates without a stale toast or dialog',async()=>{
  const pending=deferred();const f=fixture(()=>pending.promise);const modal=f.open();f.fill(modal);const input=modal.querySelector('[name=password]');const sending=f.submit(modal);await Promise.resolve();f.users.reset();assert.equal(input.value,'');assert.equal(modal.hidden,true);
  f.users.data=page();f.users.action('usersPassword',{id:'8',username:'other'},f.from);assert.equal(modal.hidden,true,'cannot reopen before the previous write settles');pending.resolve({ok:true,reauthenticate:true});await sending;assert.equal(f.toasts.children.length,0);assert.ok(f.events.includes('forbidden'),'confirmed self-reset reauthenticates even after cleanup');assert.equal(f.users.dlg,null);
  const next=f.open(page().items[1]);assert.match(next.innerHTML,/@other/);assert.equal(next.querySelector('[name=password]').value,'');
});
test('navigation closes and clears the dialog even during a write, suppressing stale errors',async()=>{
  const pending=deferred();const f=fixture(()=>pending.promise);const modal=f.open();f.fill(modal);const input=modal.querySelector('[name=password]');const sending=f.submit(modal);await Promise.resolve();for(const fn of f.listeners.hashchange||[])fn();assert.equal(modal.hidden,true);assert.equal(input.value,'');
  pending.reject(Object.assign(new Error('Expired'),{status:403}));await sending;assert.ok(!f.events.includes('forbidden'));assert.equal(f.toasts.children.length,0);
});
test('self reset shows success before calling the existing reauthentication hook',async()=>{
  const f=fixture(async()=>({ok:true,username:account.username,display:account.display,message:'Đã đổi mật khẩu.',reauthenticate:true}));const modal=f.open();f.fill(modal);await f.submit(modal);assert.equal(modal.hidden,true);assert.equal(f.toasts.children.length,1);assert.ok(f.events.includes('forbidden'));
});
test('forbidden writes and directory reads clear password fields before reauthentication',async()=>{
  for(const status of [401,403]){const f=fixture(async()=>{throw Object.assign(new Error('Expired'),{status});});const modal=f.open();f.fill(modal);const input=modal.querySelector('[name=password]');await f.submit(modal);assert.equal(input.value,'');assert.equal(modal.hidden,true);assert.ok(f.events.includes('forbidden'));assert.equal(f.toasts.children.length,0);}
  const f=fixture();const modal=f.open();f.fill(modal);f.users.api.get=async()=>{throw Object.assign(new Error('Expired'),{status:403});};await f.users.load();assert.equal(modal.hidden,true);assert.ok(f.events.includes('forbidden'));
});
test('the app forbidden flow clears an open dialog before its bootstrap request settles',async()=>{
  const f=fixture();const modal=f.open();f.fill(modal);const password=modal.querySelector('[name=password]');const pending=deferred();
  const main=readFileSync(new URL('../public/js/admin/main.js',import.meta.url),'utf8');
  // Exercise the app's real closure with its API and sibling controllers supplied as dependencies.
  const source=main.slice(main.indexOf('function reauth(){'),main.indexOf('async function login('));
  const sibling={reset(){}};
  const reauth=new Function('api','usersAdmin','toast','resetStats','inbox','chatAdmin','giftAdmin','decide',`let reauthing=null;${source};return reauth;`)({bootstrap:()=>pending.promise,admin:true},f.users,()=>{},()=>{},sibling,sibling,sibling,()=>{});
  const authenticating=reauth();assert.equal(modal.hidden,true,'forbidden flow clears secrets while authentication is pending');assert.equal(password.value,'');pending.resolve();await authenticating;
});
test('Escape cancels and Tab stays within the dialog, including while controls are disabled',async()=>{
  const pending=deferred();const f=fixture(()=>pending.promise);const modal=f.open();const controls=modal.querySelectorAll('button,input');controls.at(-1).focus();let ev=await modal.emit('keydown',{key:'Tab'});assert.equal(ev.prevented,true);assert.equal(f.doc.activeElement,controls[0]);ev=await modal.emit('keydown',{key:'Tab',shiftKey:true});assert.equal(ev.prevented,true);assert.equal(f.doc.activeElement,controls.at(-1));
  ev=await modal.emit('keydown',{key:'Escape'});assert.equal(modal.hidden,true);assert.equal(ev.stopped,true);
  f.open();f.fill(modal);const sending=f.submit(modal);await Promise.resolve();ev=await modal.emit('keydown',{key:'Tab'});assert.equal(ev.prevented,true);await modal.emit('keydown',{key:'Escape'});assert.equal(modal.hidden,false);pending.resolve({ok:true});await sending;
});
test('selected names are escaped in the dialog',()=>{
  const f=fixture();const target={...account,name:'<img src=x onerror="bad">',display:'&alias'};f.users.data.items=[target];const modal=f.open(target);assert.ok(!modal.innerHTML.includes('<img src=x'));assert.ok(modal.innerHTML.includes('&lt;img'));assert.ok(!modal.innerHTML.includes('value="new-password'));
});
