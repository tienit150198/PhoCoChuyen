import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import {GameAPI} from '../public/js/api.js';

test('accepted rename updates display before observers, without changing login or accepting stale names',()=>{
  const api=new GameAPI();api.account={username:'unchanged_login',display:'An'};api.state={name:'An'};
  let observed;api.addEventListener('state',()=>observed=api.account.display);
  api.accept({state:{name:'An mới'},revision:2});
  assert.equal(observed,'An mới');assert.equal(api.account.username,'unchanged_login');
  assert.equal(api.accept({state:{name:'An'},revision:1},0),false);assert.equal(api.account.display,'An mới');
});

test('bootstrap and unchanged default character do not replace an existing account display',()=>{
  const api=new GameAPI();api.account={username:'login',display:'Tên tài khoản'};
  api.accept({state:{name:'Mây'},revision:1});api.accept({state:{name:'Mây'},revision:2});
  assert.equal(api.account.display,'Tên tài khoản');
});

function socket(){
  const events=[],api={account:{username:'login',display:'An'},state:{name:'An'},refresh:async()=>{api.refreshes++;},refreshes:0};
  const source=readFileSync(new URL('../public/js/v4/live.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
  const ctx=vm.createContext({URLSearchParams,location:{search:''},window:{dispatchEvent:e=>events.push(e.type)},CustomEvent,console,setTimeout:()=>1,clearTimeout:()=>{}});
  vm.runInContext(source+'\npaint=()=>{};syncFace=()=>{};deepLink=()=>{};globalThis.setInterval=()=>1;globalThis.clearInterval=()=>{};globalThis.h={live,frame,setEnv:e=>env=e};',ctx);
  const h=ctx.h;h.setEnv({api});h.live.me={pid:'me',name:'An'};h.live.friends=[{pid:'peer',name:'Cũ'},{pid:'other',name:'Giữ'}];
  h.live.chans=[{id:'dm:me:peer',peer:{pid:'peer',name:'Cũ'},last:{pid:'peer',name:'Cũ',reply:{pid:'peer',name:'Cũ'}}}];
  return {...h,api,events,ctx};
}
test('rename frame updates friend, DM, preview and quotes, and invalidates the friends sheet',()=>{
  const h=socket();h.frame({t:'renamed',pid:'peer',name:'Bình mới'});
  assert.equal(h.live.friends[0].name,'Bình mới');assert.equal(h.live.friends[1].name,'Giữ');
  const c=h.live.chans[0];assert.equal(c.peer.name,'Bình mới');assert.equal(c.last.name,'Bình mới');assert.equal(c.last.reply.name,'Bình mới');
  assert.ok(h.events.includes('mnl:marriage'));assert.equal(h.api.refreshes,0);
});
test('own rename updates own display and refreshes other-tab state without modifying username',()=>{
  const h=socket();h.frame({t:'renamed',pid:'me',name:'An mới'});
  assert.equal(h.live.me.name,'An mới');assert.equal(h.api.account.display,'An mới');assert.equal(h.api.account.username,'login');assert.equal(h.api.refreshes,1);
});

test('own rename waits for an older state read then fetches the committed name',async()=>{
  const h=socket(),api=new GameAPI();api.account={username:'login',display:'An'};api.state={name:'An'};
  let calls=0,finishOld;api.json=()=>++calls===1?new Promise(r=>finishOld=r):Promise.resolve({state:{name:'An mới'},revision:2});
  h.setEnv({api});const old=api.refresh();h.frame({t:'renamed',pid:'me',name:'An mới'});
  finishOld({state:{name:'An'},revision:1});await old;await new Promise(setImmediate);
  assert.equal(calls,2);assert.equal(api.state.name,'An mới');assert.equal(api.account.display,'An mới');assert.equal(api.account.username,'login');
});

for(const t of ['welcome','state'])test(`${t} repairs own display after missing a rename while disconnected`,()=>{
  const h=socket();h.frame({t,flags:{chat:true},me:{pid:'me',name:'Tên từ máy khác'}});
  assert.equal(h.api.account.display,'Tên từ máy khác');assert.equal(h.api.refreshes,1);assert.equal(h.api.account.username,'login');
});
