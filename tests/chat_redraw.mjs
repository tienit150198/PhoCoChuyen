import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import {escapeHTML} from '../public/js/icons.js';
const source=readFileSync(new URL('../public/js/v4/chat.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
function harness(){
  const listeners=new Map(),nodes=new Map();let writes=0,html='';
  const body={dataset:{},scrollHeight:1000,scrollTop:200,clientHeight:200,onlineChecked:false,get innerHTML(){return html;},set innerHTML(v){writes++;html=v;this.onlineChecked=/data-ch-field="online" checked/.test(v);}};
  const ta={value:'Bản nháp',maxLength:300};
  for(const s of ['.ch-head','.ch-net','.ch-flash','.ch-ro','.ch-pinbar','.ch-reply-compose','.ch-count'])nodes.set(s,{});
  nodes.set('.ch-body',body);nodes.set('textarea',ta);nodes.set('.ch-compose',{querySelector:()=>ta});
  nodes.set('.ch-send',{classList:{remove(){}},querySelector:()=>true,setAttribute(){}});
  const live={state:'open',welcomed:true,me:{pid:'me',name:'Mình',account:true},flags:{},friends:[],limits:{},chans:[],on:(t,f)=>listeners.set(t,f),unread:()=>live.unreadCount||0,friend:()=>null,send(){}};
  const ctx=vm.createContext({live,esc:escapeHTML,icon:()=>'',avInner:()=>'',faceCode:()=>'',clearTimeout(){},setTimeout(){},document:{visibilityState:'visible'},console});
  vm.runInContext(source+'\nglobalThis.h={S,render,bind,onClose};',ctx);
  const h=ctx.h;h.S.dlg={open:true,querySelector:s=>nodes.get(s)};h.S.town.loaded=true;
  h.S.town.msgs=[{id:1,pid:'peer',name:'Bạn',text:'Tin nhắn',at:1700000000}];h.bind();
  return {...h,live,body,ta,nodes,writes:()=>writes,emit:(t,frame={})=>listeners.get(t)?.(frame)};
}
test('presence and read refresh header without replacing unchanged messages or moving scroll',()=>{
  const h=harness();h.render();const count=h.writes();
  h.live.friends=[{pid:'friend',on:true}];h.live.unreadCount=2;h.emit('presence');h.emit('read');
  assert.equal(h.writes(),count);assert.equal(h.body.scrollTop,200);assert.equal(h.ta.value,'Bản nháp');
  assert.match(h.nodes.get('.ch-head').innerHTML,/ch-on-n/);assert.match(h.nodes.get('.ch-head').innerHTML,/>2<\/em>/);
});
test('changed message content and actions redraw while older-history scroll anchoring remains intact',()=>{
  const h=harness();h.render();const count=h.writes();
  h.S.town.msgs[0].text='Tin mới';h.render();assert.equal(h.writes(),count+1);assert.match(h.body.innerHTML,/Tin mới/);
  h.S.act=1;h.render();assert.equal(h.writes(),count+2);assert.match(h.body.innerHTML,/ch-actbar/);
  h.render(false,true);assert.equal(h.body.scrollTop,200);
  h.render(true);assert.equal(h.body.scrollTop,1000);
});
test('closing chat invalidates its body cache for the next opening',()=>{
  const h=harness();h.render();const count=h.writes();h.onClose();h.render();
  assert.equal(h.writes(),count+1);
});
for(const event of ['presence','error'])test(`${event} restores authoritative online preference after an unsaved toggle`,()=>{
  const h=harness();h.S.tab='friends';h.live.me.online=true;h.render();
  assert.equal(h.body.onlineChecked,true);
  h.body.onlineChecked=false;h.live.send=()=>event==='error';h.live.send({t:'prefs',online:false});
  h.emit(event,{ref:'prefs',msg:'Không lưu được.'});
  assert.equal(h.body.onlineChecked,true);assert.equal(h.live.me.online,true);
});
