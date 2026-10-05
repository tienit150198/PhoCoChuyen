import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../public/js/v4/live.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
function harness({start=true,constructorError=false}={}){
 let now=100000,id=0;const sockets=[],timers=new Map(),intervals=new Map();
 class Socket{
  constructor(){if(constructorError)throw new Error('Invalid websocket URL');this.readyState=0;this.sent=[];this.closed=0;sockets.push(this);}
  send(s){this.sent.push(JSON.parse(s));}
  close(){this.closed++;this.readyState=2;} // The network may never deliver onclose.
  open(){this.readyState=1;this.onopen();}
  frame(f){this.onmessage({data:JSON.stringify(f)});}
 }
 class Clock extends Date{static now(){return now;}}
 const context=vm.createContext({WebSocket:Socket,Date:Clock,URLSearchParams,location:{protocol:'https:',host:'example.test',search:''},document:{visibilityState:'visible'},window:{},console,
 setTimeout:(f,ms)=>{timers.set(++id,{f,at:now+ms});return id;},clearTimeout:i=>timers.delete(i),
 setInterval:f=>{intervals.set(++id,f);return id;},clearInterval:i=>intervals.delete(i)});
 vm.runInContext(source+'\npaint=()=>{};deepLink=()=>{};syncFace=()=>{};env={api:{live:{url:"/live"}}};globalThis.h={live,connect,abandon};',context);
 const h=context.h;if(start)h.connect();
 const advance=ms=>{now+=ms;for(const [i,t] of [...timers])if(t.at<=now){timers.delete(i);t.f();}};
 const welcome=(s=sockets.at(-1),name='Current')=>{s.open();s.frame({t:'welcome',flags:{chat:true},me:{name}});};
 return {...h,sockets,advance,welcome,heartbeat:()=>{for(const f of [...intervals.values()])f();}};
}
test('transport changes notify the HUD even when a handshake silently times out',()=>{
 const h=harness({start:false}),seen=[];
 h.live.on('connection',f=>seen.push([f.state,h.live.state]));
 h.connect();h.advance(25000);
 assert.deepEqual(seen,[['connecting','connecting'],['down','down']]);
 h.advance(700000);h.welcome();
 h.sockets.at(-1).onclose({code:4001,wasClean:true});
 assert.deepEqual(seen.slice(2),[['connecting','connecting'],['open','open'],['off','off']]);
});
test('a welcome disabling every live feature announces off',()=>{
 const h=harness(),seen=[];h.live.on('connection',f=>seen.push(f.state));
 h.sockets[0].open();h.sockets[0].frame({t:'welcome',flags:{}});
 assert.deepEqual(seen,['off']);
});
test('a socket that cannot be constructed does not leave a connecting status',()=>{
 const h=harness({start:false,constructorError:true}),seen=[];
 h.live.on('connection',f=>seen.push(f.state));h.connect();
 assert.equal(h.live.state,'down');assert.deepEqual(seen,['connecting','down']);
});
test('a delayed browser heartbeat probes a healthy socket before closing it',()=>{
 const h=harness();h.welcome();const s=h.sockets[0];h.advance(80000);h.heartbeat();
 assert.equal(s.closed,0);assert.equal(s.sent.at(-1).t,'ping');
 h.advance(100);s.frame({t:'pong'});h.advance(5000);
 assert.equal(h.sockets.length,1);assert.equal(h.live.state,'open');
});
test('a silent half-open socket is replaced even if close never fires',()=>{
 const h=harness();h.welcome();h.advance(80000);h.heartbeat();h.advance(5000);
 assert.equal(h.sockets[0].closed,1);assert.equal(h.sockets.length,2);
});
test('a handshake that never opens times out and retries with backoff',()=>{
 const h=harness();h.advance(25000);assert.equal(h.sockets[0].closed,1);
 h.advance(700000);assert.equal(h.sockets.length,2);
});
test('an open transport without a welcome also has a bounded wait',()=>{
 const h=harness();h.sockets[0].open();h.advance(25000);
 assert.equal(h.sockets[0].closed,1);assert.equal(h.live.state,'down');
});
test('late frames from an abandoned socket cannot overwrite the active connection',()=>{
 const h=harness();const old=h.sockets[0];h.abandon();h.connect();h.welcome();
 old.frame({t:'welcome',flags:{chat:true},me:{name:'Stale'}});
 assert.equal(h.live.me.name,'Current');
});
test('welcome cancels the connection deadline',()=>{
 const h=harness();h.welcome();h.advance(25000);assert.equal(h.sockets[0].closed,0);assert.equal(h.live.state,'open');
});
test('town presence can keep the socket open when chat and other live phases are off',()=>{
 const h=harness();const s=h.sockets[0];s.open();s.frame({t:'welcome',flags:{town:true},me:{name:'Lan'}});
 assert.equal(h.live.state,'open');assert.equal(h.live.flags.town,true);
});
