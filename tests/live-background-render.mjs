import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {escapeHTML as esc,icon} from '../public/js/icons.js';
import {avInner} from '../public/js/v4/face.js';
import * as visitUI from '../public/js/v4/workplace-visit-ui.js';
import * as quayUI from '../public/js/v4/quay-business-ui.js';
import {T,isShop} from '../public/js/v4/terms.js';

const source=name=>readFileSync(new URL(`../public/js/v4/${name}.js`,import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
const flush=async()=>{for(let i=0;i<15;i++)await Promise.resolve();};

// Instrument DOM write boundaries while running the real frame handlers/renderers.
// No browser, socket, server, or native timer is needed for these operation counts.
function fixture(){
 const writes=[];let now=100000,id=0;const timers=new Map(),intervals=new Map();
 class Element{
  constructor(tag='div'){
   this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.attrs=new Map();this.listeners=new Map();this.open=false;this.scrollTop=0;
   this.classList={contains:k=>this.classes?.has(k)||false,toggle:(k,on)=>{const classes=this.classes??=new Set();on??=!classes.has(k);if(classes.has(k)!==on){on?classes.add(k):classes.delete(k);writes.push(['class',this,k]);}return on;}};
  }
  append(child){child.remove();this.children.push(child);child.parentElement=this;writes.push(['append',this]);}
  before(child){const parent=this.parentElement;child.remove();parent.children.splice(parent.children.indexOf(this),0,child);child.parentElement=parent;writes.push(['before',parent]);}
  remove(){if(this.parentElement){this.parentElement.children=this.parentElement.children.filter(x=>x!==this);this.parentElement=null;writes.push(['remove',this]);}}
  setAttribute(k,v){this.attrs.set(k,String(v));writes.push(['attribute',this,k]);}
  getAttribute(k){return this.attrs.get(k)??null;}
  hasAttribute(k){return this.attrs.has(k);}
  toggleAttribute(k,on){on??=!this.hasAttribute(k);if(on&&!this.hasAttribute(k))this.setAttribute(k,'');else if(!on&&this.hasAttribute(k)){this.attrs.delete(k);writes.push(['attribute',this,k]);}return on;}
  set hidden(v){if(v)this.setAttribute('hidden','');else this.toggleAttribute('hidden',false);}
  get hidden(){return this.hasAttribute('hidden');}
  set textContent(v){this.text=String(v);writes.push(['text',this]);}
  get textContent(){return this.text||'';}
  set innerHTML(v){
   this.html=v;this.children.forEach(c=>c.parentElement=null);this.children=[];writes.push(['html',this]);
   if(v.includes('class="badge"')){this.badge=new Element('em');this.badge.attrs.set('hidden','');}
   if(v.includes('id="wv-owner-chat"')){this.input=new Element('input');this.input.id='wv-owner-chat';this.input.value=v.match(/id="wv-owner-chat" value="([^"]*)"/)?.[1]||'';this.input.selectionStart=0;this.input.selectionEnd=0;}
   else this.input=null;
  }
  get innerHTML(){return this.html||'';}
  querySelector(selector){return selector==='.badge'?this.badge:selector.includes('wv-owner-chat')?this.input:null;}
  querySelectorAll(){return [];}
  addEventListener(type,fn){const list=this.listeners.get(type)||new Set();list.add(fn);this.listeners.set(type,list);}
  removeEventListener(type,fn){this.listeners.get(type)?.delete(fn);}
  emit(type,event={}){for(const fn of [...(this.listeners.get(type)||[])])fn(event);}
  showModal(){this.open=true;}
  close(){this.open=false;this.emit('close');}
  focus(){doc.activeElement=this;}
  setSelectionRange(a,b){this.selectionStart=a;this.selectionEnd=b;}
 }
 const body=new Element('body'),side=new Element(),hud=new Element(),sheet=new Element('dialog'),stage=new Element(),html=new Element('html');
 html.dataset.layout='desktop';side.append(hud);body.append(side);body.append(sheet);body.append(stage);
 const doc=new Element();Object.assign(doc,{body,head:new Element('head'),documentElement:html,hidden:false,visibilityState:'visible',activeElement:null,createElement:tag=>new Element(tag),getElementById:id=>({side,taskHUD:hud,sheet,stage})[id]||null});
 const setTimer=(fn,ms)=>{timers.set(++id,{fn,at:now+ms});return id;},clearTimer=i=>timers.delete(i);
 const advance=async ms=>{const end=now+ms;while(true){const next=[...timers].sort((a,b)=>a[1].at-b[1].at)[0];if(!next||next[1].at>end)break;now=next[1].at;timers.delete(next[0]);await next[1].fn();await flush();}now=end;};
 class Clock extends Date{static now(){return now;}}
 const globals={document:doc,window:new Element(),navigator:{},location:{search:'',protocol:'https:',host:'example.test'},URLSearchParams,Date:Clock,console,Promise,
  setTimeout:setTimer,clearTimeout:clearTimer,setInterval:fn=>{intervals.set(++id,fn);return id;},clearInterval:i=>intervals.delete(i),MutationObserver:class{observe(){}disconnect(){}},
  stylesheet:async()=>{},icon,esc,avInner,T,isShop,...visitUI,...quayUI,createQuayPoller:options=>quayUI.createQuayPoller({...options,setTimer,clearTimer})};
 return {globals,doc,body,side,hud,sheet,stage,writes,Element,advance,reset:()=>{writes.length=0;},timers};
}

async function liveFixture(){
 const f=fixture(),sockets=[];let renders=0;
 class Socket{constructor(){this.readyState=0;sockets.push(this);}send(){}close(){this.readyState=2;}open(){this.readyState=1;this.onopen();}frame(data){this.onmessage({data:JSON.stringify(data)});}}
 const api=new f.Element();Object.assign(api,{live:{url:'/live'},state:{name:'Owner'}});
 const env={api,renderMain:()=>renders++};
 const context=vm.createContext({...f.globals,WebSocket:Socket,faceCode:()=>''});
 vm.runInContext(source('live')+'\nglobalThis.module={live,liveBoot};',context);
 const mod=context.module;mod.liveBoot(env);await flush();const socket=sockets[0];socket.open();socket.frame({t:'welcome',flags:{chat:true,visits:true,town:true},me:{pid:'owner',name:'Owner'},chans:[{id:'dm:owner:friend',unread:0}]});await flush();await f.advance(250);f.reset();renders=0;
 return {...f,mod,env,socket,sockets,renders:()=>renders};
}

test('town and visit traffic delivers every event without touching unchanged chat DOM',async t=>{
 const f=await liveFixture();let events=0;const off=f.mod.live.on('*',()=>events++);
 for(let i=0;i<100;i++)for(const type of ['town_mv','visit_mv','pong'])f.socket.frame({t:type,pid:'friend',p:[[0,0],[i,1]]});
 await f.advance(250);
 t.diagnostic(`300 unchanged live packets: ${f.writes.length} DOM writes, ${f.renders()} main renders, ${events} delivered events`);
 assert.equal(events,300);assert.equal(f.writes.length,0);assert.equal(f.renders(),0);
 off();f.socket.frame({t:'pong'});assert.equal(events,300,'unsubscribe still removes the listener');
});

test('unread, quiet, reconnect and chat availability still refresh the badge',async()=>{
 const f=await liveFixture(),fab=f.stage.children.find(e=>e.className==='live-fab');
 f.socket.frame({t:'msg',ch:'dm:owner:friend',pid:'friend',id:1,text:'hello'});await f.advance(250);
 assert.equal(f.mod.live.unread(),1);assert.equal(fab.badge.textContent,'1');assert.equal(fab.badge.hidden,false);assert.equal(f.renders(),1);
 f.socket.frame({t:'quiet',ch:'dm:owner:friend',until:999999});await f.advance(250);assert.equal(fab.badge.hidden,true);assert.equal(f.mod.live.chan('dm:owner:friend').unread,1);
 f.socket.frame({t:'quiet',ch:'dm:owner:friend',until:0});await f.advance(250);assert.equal(fab.badge.textContent,'1');
 f.socket.frame({t:'read',ch:'dm:owner:friend',id:1});await f.advance(250);assert.equal(fab.badge.hidden,true);assert.equal(fab.getAttribute('aria-label'),'Chat');
 f.socket.onclose({code:1006,wasClean:false});assert.equal(fab.classList.contains('is-down'),true);
 f.mod.live.reconnect(true);const socket=f.sockets.at(-1);socket.open();socket.frame({t:'welcome',flags:{chat:true,town:true},me:{name:'Owner'}});assert.equal(fab.classList.contains('is-down'),false);
 socket.frame({t:'welcome',flags:{town:true},me:{name:'Owner'}});assert.equal(fab.hidden,true);
 socket.frame({t:'welcome',flags:{chat:true,town:true},me:{name:'Owner'}});assert.equal(fab.hidden,false);
 f.mod.liveBoot(f.env);assert.equal(f.sockets.length,2,'boot does not add another socket');
});

async function ownerFixture(){
 const f=fixture(),listeners=new Map(),sent=[],orders={incoming:[],outgoing:[]};let polls=0;
 const live={state:'open',flags:{visits:true},send:frame=>{sent.push(frame);return true;},on:(type,fn)=>{const set=listeners.get(type)||new Set();set.add(fn);listeners.set(type,set);return()=>set.delete(fn);}};
 const emit=(type,event={})=>{for(const fn of [...(listeners.get(type)||[])])fn(event);};
 const api=new f.Element();Object.assign(api,{account:{username:'owner'},state:{current:'tea'},refresh:async()=>{},json:async url=>{polls++;return url.includes('/orders')?orders:{places:[{id:'career:owner:tea',kind:'career',target:'tea',name:'Tea'}]};}});
 const env={api,live:()=>live};const context=vm.createContext(f.globals);
 vm.runInContext(source('workplace-visit')+'\nglobalThis.module={workVisitsBoot,openWorkplaceVisit};globalThis.owner=O;',context);
 const mod=context.module;mod.workVisitsBoot(env);await flush();const box=context.owner.box;
 const room={place:'career:owner:tea',me:'owner',people:[{pid:'friend',name:'Friend',av:'🙂',x:.5,y:.5}]};emit('visit_state',room);
 box.emit('click',{target:{closest:()=>({dataset:{ownerVisit:'toggle'}})}});f.reset();
 return {...f,mod,env,box,emit,room,orders,sent,listeners,owner:context.owner,polls:()=>polls};
}

test('stationary owner polls and moving visitors retain DOM and current people state',async t=>{
 const f=await ownerFixture();for(let i=0;i<60;i++)f.emit('visit_mv',{place:f.room.place,pid:'friend',p:[[.5,.5],[.1+i/100,.8]]});
 const movementWrites=f.writes.filter(([kind])=>kind==='html').length;
 assert.equal(f.owner.people[0].x,.69,'coordinates still update when the owner list has no positional UI');
 f.reset();await f.advance(30000);const pollWrites=f.writes.filter(([kind])=>kind==='html').length;
 t.diagnostic(`60 visitor moves: ${movementWrites} HTML replacements; 6 owner poll ticks: ${pollWrites} HTML replacements`);
 assert.equal(movementWrites,0);assert.equal(pollWrites,0);
 assert.equal(f.writes.length,0,'unchanged polls do not rewrite visibility or classes either');
});

test('visible owner changes repaint, preserve drafts, and resume after visiting or hiding',async()=>{
 const f=await ownerFixture();let input=f.box.input;input.value='draft';input.selectionStart=2;input.selectionEnd=4;f.doc.activeElement=input;f.box.emit('input',{target:input});
 f.emit('visit_chat',{place:f.room.place,pid:'friend',name:'Friend',text:'hello'});
 assert.match(f.box.innerHTML,/hello/);assert.equal(f.doc.activeElement.value,'draft');assert.equal(f.doc.activeElement.selectionStart,2);assert.equal(f.doc.activeElement.selectionEnd,4);
 f.reset();f.emit('visit_emote',{place:f.room.place,pid:'friend',kind:'wave'});assert.match(f.box.innerHTML,/👋/);assert.equal(f.writes.filter(([kind])=>kind==='html').length,1);
 f.emit('visit_people',{...f.room,people:[{pid:'friend',name:'Renamed',av:'🌷'}]});assert.match(f.box.innerHTML,/Renamed/);assert.match(f.box.innerHTML,/🌷/);
 f.orders.incoming.push({id:'order',status:'requested',price:10});await f.advance(30000);assert.match(f.box.innerHTML,/1 đơn khách/);
 const subscriptions=f.listeners.get('visit_mv').size;f.mod.workVisitsBoot(f.env);assert.equal(f.listeners.get('visit_mv').size,subscriptions);
 await f.mod.openWorkplaceVisit(f.env,{inbox:true});assert.equal(f.box.hidden,true);
 const dialog=f.body.children.find(e=>e.className==='wv-dialog');dialog.close();await flush();assert.equal(f.box.hidden,false);assert.equal(f.listeners.get('visit_mv').size,subscriptions,'closing removes visitor subscriptions');
 f.doc.hidden=true;f.doc.emit('visibilitychange');const polls=f.polls();await f.advance(30000);assert.equal(f.polls(),polls);
 f.doc.hidden=false;f.doc.emit('visibilitychange');await flush();assert.equal(f.owner.joined,true);assert.match(f.box.innerHTML,/wv-owner-chat/);
 f.env.api.account=null;await f.advance(5000);assert.equal(f.box.hidden,true);
});

test('sending an owner draft clears the textbox even when the cached markup is unchanged',async()=>{
 const f=await ownerFixture(),input=f.box.input;
 input.value='hello';f.box.emit('input',{target:input});
 f.box.emit('submit',{preventDefault(){}});
 assert.equal(f.sent.at(-1).t,'visit_chat');assert.equal(f.sent.at(-1).text,'hello');
 assert.equal(f.owner.chat,'');assert.equal(f.box.input.value,'','successful send clears the live input property');
 assert.equal(f.box.input,input,'clearing a sent draft does not replace the unchanged panel');
 f.env.live().send=()=>false;
 input.value='keep this';f.box.emit('input',{target:input});f.box.emit('submit',{preventDefault(){}});
 assert.equal(f.owner.chat,'keep this');assert.equal(input.value,'keep this','failed send preserves the draft');
 f.emit('visit_mv',{place:f.room.place,pid:'friend',p:[[.5,.5],[.7,.8]]});
 assert.equal(f.box.input.value,'keep this','visitor movement keeps the unsent draft');
});
