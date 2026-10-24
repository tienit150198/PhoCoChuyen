// 👥 Hồ câu đông vui, the client side (public/js/v4/fish-lake-layout.js, public/js/v4/fish-lake.js): the places along the
// boardwalk (the service's pos()), packing a crowd, the view, who is drawn whole, the cast in perspective, the feed's
// line; the live room's frames (join, people near and far, hints, the server's catch, bubbles, leaving, a reconnect)
// and drawing a crowd on a canvas with cached characters.   node tests/fishing-lake.mjs
import assert from 'node:assert/strict';

globalThis.Path2D??=class{constructor(d){this.d=d;}};
const bad=v=>typeof v==='number'&&!Number.isFinite(v);
const calls={drawImage:0};
const mkCtx=()=>new Proxy({measureText:t=>({width:String(t).length*6})},{get:(o,k)=>k in o?o[k]:(...a)=>{for(const x of a)assert.ok(!bad(x),`canvas ${String(k)}: ${a}`);if(k in calls)calls[k]++;return {addColorStop(){}};},set:(o,k,v)=>{o[k]=v;return true;}});
let made=0;
globalThis.document={createElement:()=>{made++;return {width:0,height:0,getContext:()=>mkCtx()};}};

const L=await import('../public/js/v4/fish-lake-layout.js');
const {createLake,drawLake,sprite,spriteCount}=await import('../public/js/v4/fish-lake.js');

// 1. places: 0, 1, -1, 2, -2 … (live/fish_lake.py pos), all distinct
assert.deepEqual([0,1,2,3,4,5,6].map(L.posOf),[0,1,-1,2,-2,3,-3]);
assert.equal(new Set(Array.from({length:500},(_,s)=>L.posOf(s))).size,500);
// 2. a crowd packs closer but never under SP_MIN; few people stand wide; the scale follows
assert.equal(L.spacing(1,390),L.SP_MAX>390/4?390/4:L.SP_MAX);
assert.equal(L.spacing(50,390),L.SP_MIN);
assert.ok(L.spacing(3,1200)<=L.SP_MAX&&L.figScale(L.SP_MIN)<L.figScale(L.SP_MAX));
// 3. the view: x on screen, the boardwalk's extent, the camera kept over it, who stands past each edge
assert.equal(L.screenX(0,0,60,390),195);
assert.equal(L.screenX(2,0,60,390),315);
const crowd=Array.from({length:60},(_,s)=>({pid:'p'+s,s,name:'P'+s,lk:{hair:'toc_ngan'}}));
assert.deepEqual(L.extent(crowd),[-29,30]);
assert.equal(L.clampCam(99,[-3,4]),4);
const o=L.offscreen(crowd,0,46,390);
assert.ok(o.left>20&&o.right>20&&o.lp<0&&o.rp>0,'both sides of a big crowd');
assert.equal(o.left+o.right+crowd.filter(p=>L.inView(L.posOf(p.s),0,46,390,0)).length,60);
// 4. the whole ones: at most FULL_DRAW, the nearest to the view's middle, only those with a look and in sight
const whole=L.detailed(crowd,0,46,1400);
assert.equal(whole.size,L.FULL_DRAW);
assert.ok(whole.has('p0')&&whole.has('p1')&&!whole.has('p59'));
assert.ok(!L.detailed([{pid:'x',s:1,name:'X'}],0,46,390).size,'a name only (no look): a silhouette');
// 5. the shared water in perspective: a cast from the middle goes straight, from the side it leans to the middle
const g={w:400,shore:600,hor:80,yOf:d=>580-400*Math.min(1,d/100),half:y=>400*(.17+.36*(y-80)/520)};
const mid=L.waterPoint(g,200,50,0),side=L.waterPoint(g,340,50,0),far=L.waterPoint(g,340,100,0);
assert.equal(mid[0],200);assert.ok(side[0]<340&&side[0]>200&&far[0]<side[0],'farther is closer to the middle');
const top=L.arcPoint([0,0],[100,0],.5,40);assert.deepEqual(top,[50,-40]);
// 6. a tap finds the fisher under it
const hit=L.hitPeer(crowd,L.screenX(1,0,46,390)+5,500-20,{cam:0,sp:46,w:390,py:500,scale:.35});
assert.equal(hit?.pid,'p1');
assert.equal(L.hitPeer(crowd,10,100,{cam:0,sp:46,w:390,py:500,scale:.35}),null,'the sky: nobody');
// 7. the feed's line and how loud a catch is
assert.equal(L.feedLine({name:'Lan',g:34000},{name:'Cá Ngừ Vây Xanh'},{emoji:'🟣'}),'🎣 Lan vừa câu được 🟣 Cá Ngừ Vây Xanh 34 kg!');
assert.deepEqual([0,2,3,4,5,6].map(L.tierOf),['plain','plain','rare','rare','legend','legend']);

// 8. the live room: a fake socket
function fakeLive(){
  const subs=new Map(),sent=[];
  return {sent,flags:{fish:true},send(f){sent.push(f);return true;},on(t,fn){(subs.get(t)||subs.set(t,new Set()).get(t)).add(fn);return ()=>subs.get(t).delete(fn);},
    emit(t,f){for(const fn of subs.get(t)||[])fn({t,...f});}};
}
let now=10;
const live=fakeLive(),seen=[];
const lake=createLake({live,spot:'ho',me:{look:{hair:'toc_ngan',fh:{sp:'ca_ngu',kg:30,fam:'x',r:3}},gender:'female',rod:'truc'},clock:()=>now,
  on:{catch:(e,p,mine)=>seen.push(['catch',e.pid,mine]),change:k=>seen.push(['change',k]),card:f=>seen.push(['card',f.pid])}}).start();
assert.deepEqual(live.sent[0],{t:'fl_in',spot:'ho',look:{hair:'toc_ngan'},g:'female',rod:'truc',fh:{sp:'ca_ngu',kg:30}});
assert.equal(lake.online,false);assert.equal(lake.count,1);
live.emit('fl_room',{room:'fl:ho',spot:'ho',me:'me',s:3,n:42,people:[{pid:'a',name:'Lan',s:0,lk:{hair:'toc_dai'},g:'female',rod:'tre',a:{k:'bite'}}],
  far:[{pid:'b',name:'Minh',s:40}],feed:[{pid:'a',name:'Lan',s:'ca_chep',g:2000,r:0}]});
assert.equal(lake.online,true);assert.equal(lake.count,42);assert.equal(lake.pos,2);
assert.equal(lake.peers.get('a').a.k,'bite','already out when I came');
assert.equal(lake.peers.get('b').lk,undefined,'far: a name only');
assert.equal(lake.feed.length,1);
live.emit('fl',{room:'fl:ho',ev:[{k:'act',pid:'a',a:'cast',d:55,x:.1}]});
assert.deepEqual([lake.peers.get('a').a.k,lake.peers.get('a').a.d,lake.peers.get('a').a.t0],['cast',55,10]);
live.emit('fl',{room:'fl:other',ev:[{k:'act',pid:'a',a:'reel'}]});
assert.equal(lake.peers.get('a').a.k,'cast','another room: ignored');
live.emit('fl',{room:'fl:ho',ev:[{k:'catch',pid:'a',s:'ca_ngu',g:34000,r:3,feed:{pid:'a',name:'Lan',s:'ca_ngu',g:34000,r:3}}]});
assert.equal(lake.peers.get('a').a,null);assert.equal(lake.peers.get('a').got.g,34000);assert.equal(lake.feed.length,2);
live.emit('fl',{room:'fl:ho',ev:[{k:'catch',pid:'me',s:'ca_ngu',g:1000,r:3,feed:{pid:'me',name:'Tôi',s:'ca_ngu',g:1000,r:3}}]});
assert.deepEqual(seen.filter(x=>x[0]==='catch'),[['catch','a',false],['catch','me',true]]);
for(let i=0;i<30;i++)live.emit('fl',{room:'fl:ho',ev:[{k:'catch',pid:'a',s:'ca_chep',g:900,r:0,feed:{pid:'a',name:'Lan',s:'ca_chep',g:900,r:0}}]});
assert.equal(lake.feed.length,20,'the last 20 catches');
live.emit('fl',{room:'fl:ho',ev:[{k:'in',pid:'c',name:'Hoa',s:5,lk:{hair:'toc_bui'},g:'female'},{k:'said',pid:'c',text:'Chào cả hồ'}]});
assert.equal(lake.count,43);assert.equal(lake.peers.get('c').said.text,'Chào cả hồ');
live.emit('fl',{room:'fl:ho',ev:[{k:'said',pid:'me',text:'Chào'}]});assert.equal(lake.self.said.text,'Chào');
live.emit('fl_near',{room:'fl:ho',c:20,people:[{pid:'b',name:'Minh',s:40,lk:{hair:'toc_ngan'},g:'male'}]});
assert.equal(lake.peers.get('b').lk.hair,'toc_ngan','looking there: now whole');
live.emit('fl',{room:'fl:ho',ev:[{k:'out',pid:'c'}]});
assert.equal(lake.count,42);assert.equal(lake.peers.has('c'),false);
live.sent.length=0;
lake.act('cast',{d:40,x:.2,rod:'truc'});lake.view(2.5);lake.view(9);lake.card('a');lake.say('hi');
assert.deepEqual(live.sent.map(f=>f.t),['fl_act','fl_view','fl_card','fl_say'],'a small pan asks nothing');
live.emit('fl_card',{pid:'a',name:'Lan'});assert.deepEqual(seen.at(-1),['card','a']);
live.emit('down',{});assert.equal(lake.online,false);assert.equal(lake.peers.size,0);
live.sent.length=0;live.emit('welcome',{});assert.equal(live.sent[0].t,'fl_in','a reconnect joins again');
lake.stop();assert.equal(live.sent.at(-1).t,'fl_in');
const quiet=fakeLive();quiet.flags={};createLake({live:quiet,spot:'ho'}).start();assert.equal(quiet.sent.length,0,'an older service: nothing sent');

// 9. drawing a crowd of 300: characters painted once and reused, at most FULL_DRAW whole, finite numbers only
const crowdLake={peers:new Map(Array.from({length:300},(_,s)=>[`q${s}`,{pid:`q${s}`,s,name:`Q${s}`,lk:{hair:s%2?'toc_ngan':'toc_bui'},g:s%2?'male':'female',
  a:s%3?{k:'cast',d:40+s,x:.1,t0:9}:null,got:s===1?{s:null,junk:'dep',g:0,r:0,t0:9.5}:null}])),self:{}};
const view={cam:0,sp:46,scale:.31,py:560,dpr:2,dark:false,api:null,spOf:()=>({id:'ca_chep',name:'Cá chép',r:0,fam:'carp',body:'#c00',belly:'#fff',fin:'#a00',pat:'plain'}),
  rarOf:()=>({emoji:'⚪',name:'Phổ thông'}),rodColor:()=>'#c8a85a',junkEmoji:()=>'🩴',calm:false};
const ctx=mkCtx(),G={...g,M:200,shore:600};
now=10;let n1=drawLake(ctx,G,crowdLake,10,view);
const after=made;
for(let f=0;f<30;f++)drawLake(ctx,G,crowdLake,10+f/60,view);
assert.ok(n1<=L.FULL_DRAW&&n1>0,`${n1} drawn whole`);
assert.equal(made,after,'30 more frames paint no new canvas (sprites and tags cached)');
assert.ok(spriteCount()<=2*L.FULL_DRAW);
assert.ok(sprite({hair:'toc_ngan'},'male',{},.4,2)===sprite({hair:'toc_ngan'},'male',{},.4,2),'one sprite per look and size');
assert.equal(drawLake(ctx,G,{peers:new Map(),self:{}},10,view),0,'alone: only the boardwalk');
console.log('fishing-lake: ok');
