import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source=readFileSync(new URL('../public/js/v4/chat.js',import.meta.url),'utf8')
  .replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
const CH='dm:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb';
const message=(id,text=`tin ${id}`)=>({t:'msg',ch:CH,id,pid:'bbbbbbbbbbbbbbbb',name:'Bạn',text,at:1700000000+id,av:'🌸'});

function harness(){
  const listeners=new Map(),sent=[];
  const live={state:'open',me:{pid:'aaaaaaaaaaaaaaaa',account:true},flags:{},chans:[],friends:[],limits:{},
    on(type,fn){listeners.set(type,fn);},send(frame){sent.push(frame);return this.state==='open';},
    chan(ch){return this.chans.find(c=>c.id===ch);},friend(){return null;},unread(){return 0;},quiet(){return false;}};
  const ctx=vm.createContext({live,document:{visibilityState:'visible'},icon:()=>'',esc:value=>String(value??''),
    avInner:()=>'',stylesheet:async()=>{},faceCode:()=>'',setTimeout,clearTimeout,console});
  vm.runInContext(source+'\nrender=()=>{};globalThis.chat={S,bind,thread,enter,openThread,body};',ctx);
  const chat=ctx.chat;
  chat.bind();
  return {...chat,live,sent,emit:(type,frame={})=>listeners.get(type)?.(frame)};
}
const ids=t=>Array.from(t.msgs,m=>m.id);

test('a message received while initial history loads remains inside the conversation',()=>{
  const h=harness();
  h.openThread(CH,false);h.enter();
  assert.equal(h.thread(CH).busy,true);
  h.emit('msg',message(12,'tin mới đến trong lúc tải'));
  h.emit('history',{ch:CH,msgs:[message(11)],more:false});
  assert.deepEqual(ids(h.thread(CH)),[11,12]);
  assert.match(h.body(),/tin mới đến trong lúc tải/);
});

test('overlapping history and live deliveries are deduplicated and ordered',()=>{
  const h=harness();h.openThread(CH,false);h.enter();
  h.emit('msg',message(13));h.emit('msg',message(12));h.emit('msg',message(13));
  h.emit('history',{ch:CH,msgs:[message(11),message(12)],more:true});
  assert.deepEqual(ids(h.thread(CH)),[11,12,13]);
});

test('reopening a cached chat whose inbox preview is newer requests fresh history',()=>{
  const h=harness();
  Object.assign(h.thread(CH),{msgs:[message(10)],loaded:true});
  h.live.chans=[{id:CH,kind:'dm',unread:1,last:message(20)}];
  h.openThread(CH);
  assert.equal(h.sent.some(f=>f.t==='history'&&f.ch===CH),true);
  assert.equal(h.sent.some(f=>f.t==='read'&&f.id===10),false,'do not clear unread before showing the new message');
  h.emit('history',{ch:CH,msgs:[message(20)],more:false});
  assert.deepEqual(ids(h.thread(CH)),[20]);
});

test('reconnect invalidates cached closed chats before they are opened again',()=>{
  const h=harness();
  Object.assign(h.thread(CH),{msgs:[message(10)],loaded:true});
  h.S.thread=null;h.emit('down');h.emit('welcome');
  h.live.chans=[{id:CH,kind:'dm',last:message(20),unread:1}];
  h.openThread(CH);
  assert.equal(h.thread(CH).loaded,false);
  assert.equal(h.sent.some(f=>f.t==='history'&&f.ch===CH),true);
});

test('a history request interrupted by disconnect is retried after welcome',()=>{
  const h=harness();h.openThread(CH,false);h.enter();
  h.S.dlg={open:true};
  h.emit('down');h.emit('welcome');
  assert.equal(h.sent.filter(f=>f.t==='history'&&f.ch===CH).length,2);
});

test('reconnect loads a contiguous latest page even when more than 50 messages were missed',()=>{
  const h=harness();
  h.openThread(CH,false);Object.assign(h.thread(CH),{msgs:[message(1)],loaded:true});
  assert.deepEqual(Object.keys(h.live.resume()),[],'fresh history avoids the truncated resume window');
  h.emit('welcome');h.enter();
  h.emit('history',{ch:CH,msgs:Array.from({length:30},(_,n)=>message(n+101)),more:true});
  assert.deepEqual(ids(h.thread(CH)),Array.from({length:30},(_,n)=>n+101));
  assert.equal(h.thread(CH).more,true);
  assert.match(h.body(),/Xem cũ hơn/);
});

test('opening an up-to-date cached chat preserves its history without another request',()=>{
  const h=harness();Object.assign(h.thread(CH),{msgs:[message(10)],loaded:true});
  h.live.chans=[{id:CH,kind:'dm',last:message(10),unread:0,read:10}];
  h.openThread(CH);
  assert.equal(h.sent.some(f=>f.t==='history'),false);
  assert.deepEqual(ids(h.thread(CH)),[10]);
});

test('older history pages preserve the newer visible messages',()=>{
  const h=harness();h.openThread(CH,false);Object.assign(h.thread(CH),{msgs:[message(20)],loaded:true});
  h.emit('history',{ch:CH,before:20,msgs:[message(18),message(19)],more:false});
  assert.deepEqual(ids(h.thread(CH)),[18,19,20]);
});

test('an inbox sync with a newer preview refreshes the currently open conversation',()=>{
  const h=harness();h.openThread(CH,false);Object.assign(h.thread(CH),{msgs:[message(10)],loaded:true});
  h.S.dlg={open:true};h.live.chans=[{id:CH,kind:'dm',last:message(20)}];
  h.emit('state',{chans:h.live.chans});
  assert.equal(h.sent.some(f=>f.t==='history'&&f.ch===CH),true);
});

test('a rejected history request offers a retry instead of staying stuck loading',()=>{
  const h=harness();h.openThread(CH,false);h.enter();
  h.emit('error',{ref:'history',code:'busy',msg:'Máy chủ đang bận'});
  assert.equal(h.thread(CH).busy,false);
  assert.match(h.body(),/Thử lại/);
  h.openThread(CH);
  assert.equal(h.sent.filter(f=>f.t==='history'&&f.ch===CH).length,2);
});
