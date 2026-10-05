import assert from 'node:assert/strict';
import {crowd} from '../public/js/v4/home-crowd.js';
import {figureOf,defaultLook} from '../public/js/v4/look.js';

const tasks=new Map();let seq=0;
globalThis.setTimeout=(fn,ms)=>{tasks.set(++seq,{fn,ms});return seq;};
globalThis.clearTimeout=id=>tasks.delete(id);
function client(me,other,x,otherX){
  const events=new Map(),sent=[];let arrival,walking=false;
  const live={state:'open',flags:{home:true},on:(k,f)=>{events.set(k,f);return ()=>events.delete(k);},send:f=>{sent.push(f);return true;}};
  const c=crowd({live,state:()=>({}),redraw:()=>{},still:()=>true,svg:()=>null,xy:p=>p.map(n=>n*300),approach:(p,fn)=>{arrival=fn;},isWalking:()=>walking});
  c.join('bed',[x,.7]);events.get('home_room')({r:'bed',room:'shared',me,people:[{pid:other,x:otherX,y:.7,name:other,lk:defaultLook('female'),g:'female'}]});
  return {c,events,sent,arrive:()=>arrival?.(),walking:value=>walking=value};
}
const a=client('a','b',.4,.5),b=client('b','a',.5,.4);
a.c.emote('hug','b');
assert.match(a.c.panel(),/Đang lại gần/,'approach is visible before acknowledgement');
const n=a.sent.length;a.c.emote('kiss','b');assert.equal(a.sent.length,n,'approach blocks another request');
a.arrive();assert.equal(a.sent.at(-1).kind,'hug');
const F=figureOf({skin:'da_nau',top:'ao_quen'},'female');
assert.doesNotMatch(a.c.figure(F),/hc-pose/,'no pose before server accepts');
const event={ev:[{k:'emote',id:'pair-1',pid:'a',to:'b',kind:'hug',ttl:15}]};
a.events.get('home')(event);b.events.get('home')(event);
assert.match(a.c.figure(F),/hc-pose-hug/,'local sender changes the actual figure');
assert.doesNotMatch(b.c.figure(F),/hc-pose/,'recipient stays neutral until choosing a reply');
assert.match(b.c.panel(),/Đáp lại/,'recipient can answer in room');
assert.match(b.c.panel(),/Ngại ngùng/);
assert.match(b.c.panel(),/Giận dỗi/);
assert.match(b.c.panel(),/Để sau/);
b.c.reply('accept','wrong-id');assert.equal(b.sent.at(-1).t,'home_in','stale response is ignored');
b.walking(true);b.c.reply('accept','pair-1');assert.equal(b.sent.at(-1).t,'home_in','recipient must stop before posing');b.walking(false);
b.c.reply('accept','pair-1');assert.deepEqual(b.sent.at(-1),{t:'home_reply',id:'pair-1',answer:'accept'});
assert.doesNotMatch(b.c.figure(F),/hc-pose/,'reply waits for server confirmation');
const accepted={ev:[{k:'reaction',id:'pair-1',pid:'b',to:'a',kind:'hug',answer:'accept'}]};
a.events.get('home')(accepted);b.events.get('home')(accepted);
assert.match(b.c.figure(F),/data-role="receive"/,'local receiver responds');
assert.match(a.c.markup(),/data-role="receive"/,'sender sees receiver reaction');
assert.match(b.c.markup(),/data-role="send"/,'receiver sees sender pose');
assert.match(a.c.figure(F),new RegExp(F.skin.hand),'gesture keeps worn skin');
assert.match(a.c.panel(),/disabled/,'busy lasts throughout the pair pose');
assert.match(a.c.figure(F),/hc-pose-hug/,'redraw preserves the active pose');
const before=a.sent.length;a.c.emote('heart','b');assert.equal(a.sent.length,before);
a.c.walk([[.4,.7],[.2,.7]],100);
assert.doesNotMatch(a.c.figure(F),/hc-pose/,'new walk clears local pose');
assert.doesNotMatch(a.c.markup(),/hc-pose/,'new walk clears paired pose');
b.events.get('home')({ev:[{k:'mv',pid:'a',p:[[.4,.7],[.2,.7]],ms:0}]});
assert.doesNotMatch(b.c.figure(F),/hc-pose/,'partner walk clears receiver pose');
for(const kind of ['kiss','heart']){
  a.events.get('home')({ev:[{k:'emote',pid:'a',to:'b',kind}]});
  assert.match(a.c.figure(F),new RegExp('hc-pose-'+kind));
  a.events.get('down')({});assert.doesNotMatch(a.c.figure(F),/hc-pose/,'disconnect resets');
  a.c.leave();a.c.join('bed',[.4,.7]);a.events.get('home_room')({r:'bed',room:'shared',me:'a',people:[{pid:'b',x:.5,y:.7}]});
}
for(const answer of ['shy','sulk']){
  a.events.get('home')({ev:[{k:'emote',id:answer,pid:'b',to:'a',kind:'kiss',ttl:15}]});
  a.events.get('home')({ev:[{k:'reaction',id:answer,pid:'a',to:'b',kind:'kiss',answer}]});
  assert.match(a.c.figure(F),new RegExp('hc-pose-'+answer),'playful reply changes real avatar');
  a.c.walk([[.4,.7],[.4,.7]],0);
}
a.events.get('home')({ev:[{k:'emote',id:'ignored',pid:'b',to:'a',kind:'hug',ttl:15}]});
const expiry=[...tasks.values()].find(t=>t.ms===15000);assert.ok(expiry);expiry.fn();
assert.doesNotMatch(a.c.figure(F),/hc-pose/,'ignored invitation expires without recipient pose');
assert.doesNotMatch(a.c.panel(),/data-answer=/);
a.c.emote('kiss','b');a.c.walk([[.4,.7],[.1,.7]],300);const cancelled=a.sent.length;a.arrive();
assert.equal(a.sent.length,cancelled,'new walk invalidates delayed approach callback');
a.events.get('home')({room:'old-room',ev:[{k:'emote',pid:'a',to:'b',kind:'hug'}]});
assert.doesNotMatch(a.c.figure(F),/hc-pose/,'old room event cannot animate current room');
a.c.walk([[.1,.7],[.45,.7]],500);a.c.join('bed',[.1,.7]);
a.events.get('home')({ev:[{k:'emote',id:'final-position',pid:'a',to:'b',kind:'heart',ttl:15}]});
assert.match(a.c.markup(),/translate\(135,173\)/,'redraw during walk preserves its reported endpoint for the paired effect');
a.c.leave();b.c.leave();assert.equal(tasks.size,0,'leave clears all animation and acknowledgement timers');
// Both players send: the server accepts d's offer before rejecting c's pending send.
const simultaneous=client('c','d',.4,.5);
simultaneous.c.emote('hug','d');simultaneous.arrive();
assert.equal(simultaneous.sent.at(-1).t,'home_emote');
simultaneous.events.get('home')({room:'shared',ev:[{k:'emote',id:'winning-offer',pid:'d',to:'c',kind:'kiss',ttl:15}]});
simultaneous.events.get('error')({ref:'home_emote',msg:'Hai bạn đang có một cử chỉ chờ đáp lại.'});
assert.match(simultaneous.c.panel(),/data-id="winning-offer"/,'rejected simultaneous send preserves the incoming authoritative invitation');
assert.match(simultaneous.c.markup(),/hc-pose-kiss/,'stale outgoing error preserves the accepted sender pose');
simultaneous.c.reply('accept','winning-offer');
assert.deepEqual(simultaneous.sent.at(-1),{t:'home_reply',id:'winning-offer',answer:'accept'},'recipient can still accept the winning offer');
simultaneous.events.get('error')({ref:'home_reply',msg:'Thử lại nhé.'});
assert.match(simultaneous.c.panel(),/data-id="winning-offer"/,'reply rejection releases the button without destroying the offer');
simultaneous.c.reply('accept','winning-offer');
simultaneous.events.get('home')({ev:[{k:'reaction',id:'winning-offer',pid:'c',to:'d',kind:'kiss',answer:'accept'}]});
simultaneous.events.get('error')({ref:'home_emote',msg:'Lỗi đến trễ'});
assert.match(simultaneous.c.figure(F),/hc-pose-kiss/,'late outgoing error cannot erase a confirmed paired reaction');
simultaneous.c.leave();assert.equal(tasks.size,0);
console.log('Home affection: two-client roles, actual avatar pose, wardrobe, busy, redraw, movement and room cleanup passed');
