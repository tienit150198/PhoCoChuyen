import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync,existsSync} from 'node:fs';
import vm from 'node:vm';

class Element {
  constructor(tag='div'){this.tagName=tag;this.children=[];this.dataset={};this.style={};this.attrs={};this.listeners=new Map();this.hidden=false;this.value='';this.textContent='';}
  append(...nodes){for(const n of nodes){n.parentNode=this;this.children.push(n);}}
  replaceChildren(...nodes){this.children=[];this.append(...nodes);}
  remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(x=>x!==this);this.parentNode=null;}
  setAttribute(k,v){this.attrs[k]=String(v);}
  addEventListener(t,f){this.listeners.set(t,f);}
  removeEventListener(t){this.listeners.delete(t);}
  focus(){this.focused=true;}
  fire(t){return this.listeners.get(t)?.({target:this,preventDefault(){},stopPropagation(){}});}
}
function harness(){
  const path=new URL('../public/js/isometric-social.js',import.meta.url);
  assert.ok(existsSync(path),'town social implementation exists');
  const source=readFileSync(path,'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
  let now=1000,serial=0;const frames=new Map(),listeners=new Map(),sent=[];
  const socket={state:'open',flags:{blocks:true},on(t,f){listeners.set(t,f);return()=>listeners.delete(t);},send(f){if(this.state!=='open')return false;sent.push(f);return true;}};
  const doc=new Element();doc.body=new Element('body');doc.createElement=t=>new Element(t);doc.visibilityState='visible';
  const events=new Element();events.requestAnimationFrame=f=>{frames.set(++serial,f);return serial;};events.cancelAnimationFrame=i=>frames.delete(i);
  const env={world:{getPresence:()=>({x:1,y:1}),getSocialAnchor:()=>({x:220,y:200}),canvas:{getBoundingClientRect:()=>({left:0,top:0,right:800,bottom:600})}},api:{}};
  const context=vm.createContext({console,live:socket,stylesheet:()=>Promise.resolve(),document:doc,window:events,Date,Math});
  vm.runInContext(source+'\nglobalThis.factory=createTownSocial;',context);
  const social=context.factory(()=>env,{transport:socket,document:doc,events,now:()=>now});
  const snapshot={room:'r',me:'me',enabled:true,active:true,peers:[{pid:'p',name:'Lan',x:2,y:2}]};
  const all=(root=doc.body)=>[root,...root.children.flatMap(all)];
  const find=k=>all().find(n=>n.dataset.social===k);
  const emit=(t,f)=>listeners.get(t)?.(f);
  social.update(snapshot);
  return {social,socket,doc,events,env,sent,snapshot,frames,find,all,emit,
    tick(ms){now+=ms;social.update(snapshot);for(const [id,f] of [...frames]){frames.delete(id);f();}},
    say(text){find('draft').value=text;find('draft').fire('input');find('composer').fire('submit');},
    speech(extra={}){emit('town_said',{room:'r',pid:'p',name:'Lan',id:10,ch:'iso-talk:abc',text:'Xin chào',...extra});}};
}
test('speech waits for acknowledgement, preserves newer drafts and plain text',()=>{
  const h=harness();h.say('<img src=x>');assert.equal(h.sent.at(-1).t,'town_say');assert.equal(h.find('draft').value,'<img src=x>');assert.equal(h.find('bubble-p'),undefined);
  const cid=h.sent.at(-1).cid;h.find('draft').value='Tin tiếp';h.find('draft').fire('input');
  h.speech({pid:'me',cid,text:'<img src=x>'});assert.equal(h.find('draft').value,'Tin tiếp');assert.equal(h.find('bubble-me').children.some(x=>x.textContent==='<img src=x>'),true);
  h.say('Đồng ý');h.speech({pid:'me',cid:h.sent.at(-1).cid,text:'Đồng ý'});assert.equal(h.find('draft').value,'');h.social.stop();
});
test('bubbles follow projection with one animation frame and expire',()=>{
  const h=harness();h.speech();h.emit('town_emoted',{room:'r',pid:'me',e:'👋'});assert.equal(h.frames.size,1);
  h.env.world.getSocialAnchor=()=>({x:300,y:260});h.tick(10);assert.equal(h.find('bubble-p').style.left,'300px');
  h.tick(3000);assert.equal(h.find('bubble-me'),undefined);assert.ok(h.find('bubble-p'));h.tick(3000);assert.equal(h.frames.size,0);assert.equal(h.find('bubble-p'),undefined);h.social.stop();
});
test('private and wrong-room traffic never become bubbles; deletions and blocks clear',()=>{
  const h=harness();h.emit('msg',{pid:'p',text:'secret',ch:'dm:me:p'});h.speech({room:'other'});assert.equal(h.find('bubble-p'),undefined);
  h.speech();h.emit('deleted',{id:10,ch:'iso-talk:abc'});assert.equal(h.find('bubble-p'),undefined);
  h.speech();h.emit('blocked',{pid:'p',on:true});assert.equal(h.find('bubble-p'),undefined);h.speech();assert.equal(h.find('bubble-p'),undefined);h.social.stop();
});
test('protocol errors preserve draft and reactions show only matching server counts',()=>{
  const h=harness();h.say('Xin chào');h.emit('error',{ref:h.sent.at(-1).cid,msg:'Bạn đang bị tạm khóa chat.'});assert.equal(h.find('send').disabled,false);assert.equal(h.find('draft').value,'Xin chào');assert.equal(h.find('status').textContent,'Bạn đang bị tạm khóa chat.');
  h.speech();h.find('reactions-p').children[0].fire('click');assert.equal(h.sent.at(-1).t,'react');assert.equal(h.sent.at(-1).id,10);
  h.emit('reacts',{ch:'dm:a:b',id:10,r:{'❤️':2},by:'me',e:'❤️'});assert.equal(h.find('counts-p').textContent,'');
  h.emit('reacts',{ch:'iso-talk:abc',id:10,r:{'❤️':2},by:'me',e:'❤️'});assert.equal(h.find('counts-p').textContent,'❤️ 2');
  h.emit('hid',{id:10,ch:'iso-talk:abc'});assert.equal(h.find('bubble-p'),undefined);h.social.stop();
});
test('capability and visibility gate UI; blocked peer frames cannot restore it',()=>{
  const h=harness();h.snapshot.enabled=false;h.social.update(h.snapshot);assert.equal(h.find('dock').hidden,true);h.speech();assert.equal(h.find('bubble-p'),undefined);
  h.snapshot.enabled=true;h.social.update(h.snapshot);h.speech();h.doc.visibilityState='hidden';h.doc.fire('visibilitychange');assert.equal(h.find('bubble-p'),undefined);assert.equal(h.find('dock').hidden,true);
  h.doc.visibilityState='visible';h.social.update(h.snapshot);h.emit('reply_hidden',{pid:'p'});h.speech();assert.equal(h.find('bubble-p'),undefined);assert.equal(h.find('peer-p'),undefined);h.social.stop();
});
test('disconnect, timeout, world change and inactive snapshots clear without resending',()=>{
  const h=harness();h.say('Còn bản nháp');h.tick(13000);assert.equal(h.find('draft').value,'Còn bản nháp');assert.equal(h.find('send').disabled,false);
  h.say('Còn bản nháp');const n=h.sent.length;h.socket.state='down';h.emit('down',{});h.socket.state='open';h.emit('welcome',{});h.social.update(h.snapshot);assert.equal(h.sent.length,n);assert.equal(h.find('draft').value,'Còn bản nháp');
  h.speech();h.env.world={...h.env.world};h.social.update(h.snapshot);assert.equal(h.find('bubble-p'),undefined);
  h.speech();h.snapshot.active=false;h.social.update(h.snapshot);assert.equal(h.find('bubble-p'),undefined);assert.equal(h.find('dock').hidden,true);h.social.stop();assert.equal(h.doc.body.children.length,0);assert.equal(h.frames.size,0);
});
test('nearby selection excludes far or busy peers and cards require matched request',()=>{
  const h=harness();h.snapshot.peers.push({pid:'far',x:50,y:50},{pid:'busy',x:1,y:1,activity:{kind:'fishing'}});h.social.update(h.snapshot);
  assert.ok(h.find('peer-p'));assert.equal(h.find('peer-far'),undefined);assert.equal(h.find('peer-busy'),undefined);
  h.find('peer-p').fire('click');const request=h.sent.at(-1);assert.equal(request.t,'town_card');
  h.emit('town_card',{room:'r',pid:'p',name:'Lan',friend:false,code:'ABCD',cid:'wrong'});assert.equal(h.find('greet'),undefined);
  h.emit('town_card',{room:'r',pid:'p',name:'Lan',friend:false,code:'ABCD',cid:request.cid});h.find('greet').fire('click');assert.equal(h.sent.at(-1).target,'p');assert.equal(h.sent.at(-1).e,'👋');h.social.stop();
});
test('targeted emoji names its recipient without creating a second bubble',()=>{
  const h=harness();h.emit('town_emoted',{room:'r',pid:'me',target:'p',e:'👋'});
  assert.equal(h.find('bubble-me').children[0].textContent,'Bạn → Lan');assert.equal(h.find('bubble-p'),undefined);h.social.stop();
});
test('friend requests use real API result; report and block wait for server replies',async()=>{
  const h=harness();let request;h.env.api={csrf:'csrf',async json(url,options){request={url,options};return {message:'Lời mời đã gửi.'};}};
  h.speech();h.find('peer-p').fire('click');h.emit('town_card',{room:'r',pid:'p',name:'Lan',friend:false,account:true,code:'ABCD',cid:h.sent.at(-1).cid});
  assert.equal(h.find('dm'),undefined);await h.find('friend').fire('click');assert.equal(request.url,'/api/marriage/friend_request');assert.equal(request.options.headers['X-Game-CSRF'],'csrf');assert.deepEqual(JSON.parse(request.options.body),{code:'ABCD'});assert.equal(h.find('status').textContent,'Lời mời đã gửi.');
  h.find('report').fire('click');h.all().find(n=>n.tagName==='button'&&n.textContent==='Spam').fire('click');assert.equal(h.sent.at(-1).t,'report');assert.equal(h.sent.at(-1).reason,'spam');assert.equal(h.find('status').textContent,'Đang gửi báo cáo…');
  h.emit('reported',{id:10});assert.equal(h.find('status').textContent,'Đã gửi báo cáo đến ban quản lý.');h.find('block').fire('click');assert.equal(h.sent.at(-1).t,'block');assert.ok(h.find('bubble-p'));h.emit('blocked',{pid:'p',on:true});assert.equal(h.find('bubble-p'),undefined);h.social.stop();
});
test('overlength text cannot send and server acknowledgement cannot erase edited draft',()=>{
  const h=harness();h.say('a'.repeat(121));assert.equal(h.sent.length,0);h.say('Tin cũ');const cid=h.sent.at(-1).cid;h.find('draft').value='Tin cũ';h.find('draft').fire('input');h.speech({pid:'me',cid});assert.equal(h.find('draft').value,'Tin cũ');h.social.stop();
});
test('late town out acknowledgement cannot clear a newly joined room',()=>{
  const h=harness();h.snapshot.room='new-room';h.social.update(h.snapshot);h.speech({room:'new-room'});h.emit('town_left',{why:'out'});assert.ok(h.find('bubble-p'));assert.equal(h.find('dock').hidden,false);h.social.stop();
});
test('an older card error or timeout cannot hide the latest selected card',()=>{
  const h=harness();h.snapshot.peers.push({pid:'q',name:'Minh',x:2,y:2});h.social.update(h.snapshot);
  h.find('peer-p').fire('click');const old=h.sent.at(-1).cid;h.find('peer-q').fire('click');const latest=h.sent.at(-1).cid;
  h.emit('town_card',{room:'r',pid:'q',name:'Minh',cid:latest});h.emit('error',{ref:old,msg:'Bạn ấy đã đi xa.'});assert.equal(h.find('card').hidden,false);assert.equal(h.find('card').children[0].textContent,'Minh');
  h.find('peer-q').fire('click');h.tick(6000);h.find('peer-q').fire('click');h.emit('town_card',{room:'r',pid:'q',name:'Minh mới',cid:h.sent.at(-1).cid});h.tick(6001);assert.equal(h.find('card').hidden,false);assert.equal(h.find('card').children[0].textContent,'Minh mới');h.social.stop();
});
test('only the latest same-peer card request can succeed, fail or restore actions',()=>{
  const h=harness();h.find('peer-p').fire('click');const old=h.sent.at(-1).cid;h.find('peer-p').fire('click');const latest=h.sent.at(-1).cid;
  h.emit('town_card',{room:'r',pid:'p',name:'Thông tin cũ',friend:true,cid:old});assert.equal(h.find('greet'),undefined);
  h.emit('error',{ref:latest,msg:'Bạn ấy đã đi xa.'});assert.equal(h.find('card').hidden,true);h.emit('town_card',{room:'r',pid:'p',name:'Thông tin cũ',friend:true,cid:old});assert.equal(h.find('card').hidden,true);assert.equal(h.find('greet'),undefined);h.social.stop();
});
test('changing identity clears local blocks and draft but same-account reconnect preserves both',()=>{
  const h=harness();h.say('Bản nháp của tôi');h.emit('blocked',{pid:'p',on:true});h.emit('down',{});h.emit('welcome',{});h.social.update({...h.snapshot});assert.equal(h.find('peer-p'),undefined);assert.equal(h.find('draft').value,'Bản nháp của tôi');
  h.emit('welcome',{});h.snapshot.me='new-person';h.social.update({...h.snapshot});assert.ok(h.find('peer-p'));assert.equal(h.find('draft').value,'');h.social.stop();
});
test('a friendship response from the previous identity cannot update the new identity UI',async()=>{
  const h=harness();let resolve;h.env.api={json:()=>new Promise(ok=>{resolve=ok;})};
  const select=()=>{h.find('peer-p').fire('click');h.emit('town_card',{room:'r',pid:'p',name:'Lan',account:true,code:'ABCD',cid:h.sent.at(-1).cid});};
  select();const request=h.find('friend').fire('click');h.social.update({...h.snapshot,me:'another-me'});select();const count=h.sent.length;
  resolve({message:'Phản hồi cho người cũ'});await request;assert.notEqual(h.find('status').textContent,'Phản hồi cho người cũ');assert.equal(h.sent.length,count);h.social.stop();
});

