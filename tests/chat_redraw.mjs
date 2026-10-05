import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import {escapeHTML} from '../public/js/icons.js';
const source=readFileSync(new URL('../public/js/v4/chat.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
function harness(){
  const listeners=new Map(),nodes=new Map();let writes=0,html='',headWrites=0,headHTML='';
  const body={dataset:{},scrollHeight:1000,scrollTop:200,clientHeight:200,onlineChecked:false,get innerHTML(){return html;},set innerHTML(v){writes++;html=v;this.onlineChecked=/data-ch-field="online" checked/.test(v);}};
  const ta={value:'Bản nháp',maxLength:300};
  for(const s of ['.ch-head','.ch-net','.ch-flash','.ch-ro','.ch-pinbar','.ch-reply-compose','.ch-count'])nodes.set(s,{});
  nodes.set('.ch-head',{get innerHTML(){return headHTML;},set innerHTML(v){headWrites++;headHTML=v;}});
  nodes.set('.ch-body',body);nodes.set('textarea',ta);nodes.set('.ch-compose',{querySelector:()=>ta});
  nodes.set('.ch-send',{classList:{remove(){}},querySelector:()=>true,setAttribute(){}});
  const live={state:'open',welcomed:true,me:{pid:'me',name:'Mình',account:true},flags:{},friends:[],limits:{},chans:[],on:(t,f)=>listeners.set(t,f),unread:()=>live.unreadCount||0,friend:()=>null,send(){}};
  const document={visibilityState:'visible',createElement:()=>({dataset:{}})};
  const ctx=vm.createContext({live,esc:escapeHTML,icon:()=>'',avInner:()=>'',faceCode:()=>'',stylesheet:async()=>{},clearTimeout(){},setTimeout(){},document,console});
  nodes.get('.ch-ro').append=()=>{};
  vm.runInContext(source+'\nglobalThis.h={S,render,bind,onClose,onAct,openChat};',ctx);
  const h=ctx.h;h.S.dlg={open:true,querySelector:s=>nodes.get(s)};h.S.town.loaded=true;
  h.S.town.msgs=[{id:1,pid:'peer',name:'Bạn',text:'Tin nhắn',at:1700000000}];h.bind();
  return {...h,live,body,ta,nodes,document,writes:()=>writes,headWrites:()=>headWrites,emit:(t,frame={})=>listeners.get(t)?.(frame)};
}
test('incoming messages preserve the unchanged header and the composer draft',()=>{
  const h=harness();h.render();const writes=h.headWrites();
  h.S.town.msgs.push({id:2,pid:'peer',name:'Bạn',text:'Tin thứ hai',at:1700000060});h.render();
  assert.equal(h.headWrites(),writes);assert.equal(h.ta.value,'Bản nháp');
});
test('incoming messages restore keyboard focus to the same message control',()=>{
  const h=harness();h.render();let focused=false;
  h.document.activeElement={dataset:{chAct:'msg',id:'1'}};
  h.body.contains=e=>e===h.document.activeElement;
  h.body.querySelectorAll=()=>[{dataset:{chAct:'msg',id:'1'},focus:()=>{focused=true;}}];
  h.S.town.msgs.push({id:2,pid:'peer',name:'Bạn',text:'Tin thứ hai',at:1700000060});h.render();
  assert.equal(focused,true);assert.equal(h.ta.value,'Bản nháp');
});
test('message dates split groups at local midnight, even within five minutes',()=>{
  const h=harness(),before=new Date(2026,9,5,23,59).getTime()/1000;
  h.S.town.msgs=[{id:1,pid:'peer',name:'Bạn',text:'Hôm trước',at:before},{id:2,pid:'peer',name:'Bạn',text:'Ngày mới',at:before+120}];h.render();
  assert.equal((h.body.innerHTML.match(/class="ch-day"/g)||[]).length,2);
  assert.equal((h.body.innerHTML.match(/class="ch-msg first"/g)||[]).length,2);
});
test('guest gate states read-only access and routes its login action to the existing account screen',()=>{
  const h=harness(),calls=[];h.live.me.account=false;h.S.dlg.close=()=>{};h.S.env={act:(...args)=>calls.push(args)};
  h.render();assert.match(h.nodes.get('.ch-ro').textContent,/khách.*Đăng nhập/i);assert.equal(h.nodes.get('.ch-compose').hidden,true);
  h.onAct('account',{});assert.equal(calls[0][0],'v4AccountOpen');assert.equal(calls[0][1].mode,'login');
});
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
test('an unavailable connection offers an explicit retry without discarding the draft',()=>{
  const h=harness();let retries=0;
  h.live.state='down';h.live.welcomed=false;h.live.reconnect=force=>{if(force)retries++;};
  h.render();assert.match(h.body.innerHTML,/data-ch-act="reconnect"/);
  h.onAct('reconnect',{});assert.equal(retries,1);assert.equal(h.ta.value,'Bản nháp');
});
test('a server-disabled chat gives a settled explanation with no active composer',()=>{
  const h=harness();h.live.flags.chat=false;h.S.town.loaded=false;h.render();
  assert.match(h.body.innerHTML,/Trò chuyện đang tạm nghỉ/);
  assert.equal(h.nodes.get('.ch-compose').hidden,true);
  assert.doesNotMatch(h.body.innerHTML,/Đang vào phố/);
});
test('opening a server-disabled chat does not send unsupported sync or join frames',async()=>{
  const h=harness(),sent=[];h.live.flags.chat=false;h.live.send=frame=>sent.push(frame);
  await h.openChat({});assert.deepEqual(sent,[]);
});
