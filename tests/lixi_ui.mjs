// 🧧 public/js/v4/lixi.js and lixi-cards.js: what shows where (falling envelopes on an open screen, a small chip over a
// game or a sheet, nothing for a blocked giver), the card in Cả phố, grabbing, with a tiny fake DOM.
// Run: node --test tests/lixi_ui.mjs   (tests/test_lixi.py runs it too)
import assert from 'node:assert/strict';
import test from 'node:test';

/* ---- a tiny DOM: what lixi.js and lixi-cards.js touch ---- */
class El{
  constructor(tag){
    this.tagName=tag.toUpperCase();this.children=[];this.parent=null;this.dataset={};this.attrs={};this.listeners={};
    this.style={};this.cls=new Set();this.className='';this._html='';this.parts={};this.open=false;this.modal=false;this.id='';
    this.textContent='';this.popoverOpen=false;
    const self=this;this.classList={add:c=>self.cls.add(c),remove:c=>self.cls.delete(c),contains:c=>self.cls.has(c)};
  }
  set innerHTML(v){this._html=v;this.parts={};}
  get innerHTML(){return this._html;}
  append(...els){for(const e of els){if(e.parent)e.parent.children=e.parent.children.filter(x=>x!==e);e.parent=this;this.children.push(e);}}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);this.parent=null;}
  get isConnected(){for(let p=this;p;p=p.parent)if(p===doc.body||p===doc.head)return true;return false;}
  setAttribute(k,v){this.attrs[k]=v;}
  addEventListener(t,f){(this.listeners[t]??=[]).push(f);}
  fire(t,ev){for(const f of this.listeners[t]||[])f(ev);return ev;}
  querySelector(sel){   // '.lxi-banner', '.lxi-won', '.lxi-text small': a part when the markup has it
    const key=sel.split(' ')[0].replace('.','');
    if(![this._html,...Object.values(this.parts).map(x=>x._html)].some(h=>h.includes(key)))return null;
    return this.parts[sel]??=new El('div');
  }
  querySelectorAll(){return [];}
  showPopover(){if(!this.isConnected)throw new Error('not connected');this.popoverOpen=true;}
  hidePopover(){this.popoverOpen=false;}
  matches(sel){return sel===':modal'?this.modal&&this.open:false;}
  closest(){return null;}
}
const all=el=>[el,...el.children.flatMap(all)];
const doc={
  head:new El('head'),body:new El('body'),documentElement:{classList:{contains:()=>false}},fullscreenElement:null,listeners:{},
  createElement:t=>new El(t),
  querySelector(sel){const m=/^style\[data-(\w+)-css\]$/.exec(sel);return m?all(this.head).find(e=>e.tagName==='STYLE'&&e.textContent.includes(`.${m[1]}`))||null:null;},
  querySelectorAll(sel){return sel==='dialog[open]'?all(this.body).filter(e=>e.tagName==='DIALOG'&&e.open):[];},
  elementFromPoint(){return this.body;},
  addEventListener(t,f){(this.listeners[t]??=[]).push(f);},
  removeEventListener(t,f){this.listeners[t]=(this.listeners[t]||[]).filter(x=>x!==f);},
  key(key){const ev={key,preventDefault(){},stopPropagation(){}};for(const f of [...(this.listeners.keydown||[])])f(ev);return ev;},
};
globalThis.document=doc;
globalThis.requestAnimationFrame=f=>{f();return 1;};
globalThis.matchMedia=()=>({matches:false});
globalThis.localStorage={getItem:()=>null,setItem:()=>{}};

const C={min:10000,max:10000000,n_min:1,n_max:100,env_min:100,text_max:40};   // game/lixi.py catalogue()
const cards=await import('../public/js/v4/lixi-cards.js');
let n=0;
const fresh=async()=>{for(const e of [...doc.body.children])e.remove();doc.listeners={};doc.fullscreenElement=null;return import(`../public/js/v4/lixi.js?t=${++n}`);};
const hex=()=>Array.from({length:14},()=>'0123456789abcdef'[Math.floor(Math.random()*16)]).join('');
const pk=()=>'lx'+hex();
const now=()=>Date.now()/1000;
const packet=(extra={})=>({id:pk(),name:'Lan',n:10,left:10,total:100000,wish:'Vạn sự như ý',at:now(),exp:now()+86400,ago:0,...extra});
const env=(view='home',post=null)=>({ui:{view},toasts:[],toast(t,k){this.toasts.push([t,k]);},
  api:{state:{journey:{story:true}},content:{journey:{lixi:C}},accepted:[],accept(x){this.accepted.push(x);},post:post||(async()=>({amount:1234,message:'ok'}))}});
const sheet=()=>{const d=new El('dialog');d.open=true;d.modal=true;doc.body.append(d);return d;};
const roots=(el=doc.body)=>all(el).filter(e=>e.className==='lxi-root');
const chips=(el=doc.body)=>all(el).filter(e=>e.className==='lxi-chip');
const tap=lxi=>({target:{closest:()=>({dataset:{lxi},classList:{contains:()=>false,add(){}}})},stopPropagation(){}});
const wait=ms=>new Promise(r=>setTimeout(r,ms));

test('what to show: an open screen rains, anything else gets the chip, a blocked giver nothing',async()=>{
  const m=await fresh();
  assert.equal(m.howToShow({mode:'on'}),'rain');
  assert.equal(m.howToShow({mode:'on',busy:true}),'chip','never over a game or a sheet');
  assert.equal(m.howToShow({mode:'small'}),'chip');
  assert.equal(m.howToShow({mode:'off'}),'chip','⚙️ Tắt pháo hoa still tells about a packet, quietly');
  assert.equal(m.howToShow({own:true}),'chip');
  assert.equal(m.howToShow({no:true}),'none');
  assert.equal(m.howToShow({open:false}),'none');
  assert.equal(m.rainHere(null,{ui:{view:'work'}}),true);
  const walk=new El('dialog');walk.classList.add('walk-sheet');
  assert.equal(m.rainHere(walk,{ui:{view:'work'}}),true,'a 🚶 stroll (old map) is an open screen');
  const home=new El('dialog');home.id='sheet';
  assert.equal(m.rainHere(home,{ui:{view:'home'}}),true,'the 🗺️ home sheet too');
  assert.equal(m.rainHere(home,{ui:{view:'work'}}),false);
});

test('the rain: as many envelopes as are left, inside the screen',async()=>{
  const m=await fresh();
  let i=0;const rnd=()=>[0,.5,.999][i++%3];
  assert.equal(m.planRain(1,9,rnd).length,3);
  assert.equal(m.planRain(8,9,rnd).length,8);
  const many=m.planRain(100,9,rnd);
  assert.equal(many.length,14);
  for(const d of many){
    assert.ok(d.x>=4&&d.x<=92,`x ${d.x}`);
    assert.ok(d.delay>=0&&d.delay+d.dur<=9+6.1);
    assert.ok(d.size>=40&&d.size<=56);
  }
});

test('the give form follows the server rules',async()=>{
  const m=await fresh();
  assert.deepEqual(m.giveWhy({total:100000,n:20,have:200000},C),[true,'']);
  assert.equal(m.giveWhy({total:100000,n:20,have:200000},null)[0],false);
  assert.match(m.giveWhy({total:9999,n:1,have:1e9},C)[1],/^Tổng từ/);
  assert.match(m.giveWhy({total:20000000,n:1,have:1e9},C)[1],/^Tổng từ/);
  assert.match(m.giveWhy({total:50000,n:0,have:1e9},C)[1],/bao$/);
  assert.match(m.giveWhy({total:50000,n:101,have:1e9},C)[1],/bao$/);
  assert.equal(m.giveWhy({total:50000,n:5,have:1e9,debt:true},C)[1],'Ví đang nợ');
  assert.match(m.giveWhy({total:50000,n:5,have:20000},C)[1],/^Còn thiếu 30.000 xu$/);
});

test('the store and the Cả phố card',async()=>{
  assert.equal(cards.upsert({id:'nope'}),null);
  assert.equal(cards.upsert({id:'lx'+'Z'.repeat(14)}),null);
  const p=cards.upsert(packet({name:'<img src=x onerror=alert(1)>',wish:'"><b>hi</b>'}),true);
  assert.equal(p.status,'open');
  assert.deepEqual(cards.cardAction(p),['Giật','grab']);
  const html=cards.cardHTML(p);
  assert.ok(!html.includes('<img'),'the name is escaped');
  assert.ok(!html.includes('<b>hi'),'the wish is escaped');
  assert.match(html,/data-ch-act="lixi"/);
  assert.match(html,/data-do="grab"/);
  assert.match(html,/Còn 10\/10 bao/);
  assert.match(html,/data-no-translate/);
  let calls=0;const off=cards.onChange(()=>calls++);
  cards.update({id:p.id,left:3});
  assert.equal(p.left,3);assert.equal(calls,1);
  cards.grabbed(p.id,4321);
  assert.deepEqual(cards.cardAction(p),['+4.321 xu','see']);
  cards.update({id:p.id,left:0,done:true});
  assert.equal(p.status,'done');assert.equal(cards.openNow(p),false);
  assert.match(cards.cardHTML(p),/Đã giật hết/);
  off();
  const q=cards.upsert(packet({left:4}),true);
  cards.update({id:q.id,left:4,done:true});
  assert.equal(q.status,'expired','over with envelopes left: time ran out');
  assert.match(cards.cardHTML(q),/Đã hết giờ/);
  const own=cards.upsert(packet({own:true}),true);
  assert.deepEqual(cards.cardAction(own),['Xem','see']);
  const hidden=cards.upsert(packet({no:true,name:'',wish:''}),true);
  assert.deepEqual(cards.cardAction(hidden),['','']);
  assert.match(cards.cardHTML(hidden),/Một người hàng xóm/);
  assert.ok(!cards.cardHTML(hidden).includes('<button'));
  assert.ok(doc.querySelector('style[data-lxc-css]'),'the card style is in the page');
});

test('cards sit between the messages by time',async()=>{
  for(const p of [...cards.LX.packets.values()])cards.LX.packets.delete(p.id);
  const t=now()-1000;
  const early=cards.upsert(packet({at:t-500,left:0,status:'done'}),true);   // finished before the first message: in the 🧧 list only
  const open=cards.upsert(packet({at:t-400}),true);                         // still open: shows first
  const mid=cards.upsert(packet({at:t+15}),true);
  const late=cards.upsert(packet({at:t+100}),true);
  const msgs=[{sys:true,text:'hi'},{at:t,text:'a'},{at:t+10,text:'b'},{at:t+20,text:'c'}];
  const out=cards.interleave(msgs).map(x=>x.lixi?x.lixi.id:x.text);
  assert.deepEqual(out,['hi',open.id,'a','b',mid.id,'c',late.id]);
  assert.ok(!out.includes(early.id));
  assert.deepEqual(cards.interleave([]).map(x=>x.lixi.id),[early.id,open.id,mid.id,late.id]);
});

test('a packet on an open screen: envelopes fall, a tap grabs one, Escape closes',async()=>{
  const m=await fresh();
  const posts=[];
  const e=env('home',async(url,body)=>{posts.push([url,body]);return {amount:2500,message:'ok',state:{journey:{wallet:2500}},revision:7};});
  const p=packet({name:'Lan Mây'});
  m.onLixi(e,{...p,t:'lixi'});
  const [root]=roots();
  assert.ok(root,'the rain is on the page');
  assert.equal(root.parent,doc.body);
  assert.ok(root.cls.has('on'));
  assert.match(root.innerHTML,/class="lxi-env"/);
  assert.match(root.querySelector('.lxi-banner').innerHTML,/Lan Mây/);
  assert.match(root.querySelector('.lxi-banner').innerHTML,/data-lxi="grab"/);
  m.onLixi(e,{...p,t:'lixi'});
  assert.equal(roots().length,1,'the same packet once');
  await root.fire('click',tap('grab'));
  await wait(0);
  assert.deepEqual(posts,[['/api/lixi/grab',{id:p.id}]]);
  assert.deepEqual(e.api.accepted,[{state:{journey:{wallet:2500}},revision:7}],'the wallet moves at once');
  assert.equal(cards.LX.got.get(p.id),2500);
  assert.match(root.querySelector('.lxi-won').innerHTML,/\+2\.500 xu/);
  assert.match(root.querySelector('.lxi-banner').innerHTML,/\+2\.500 xu/);
  assert.match(root.querySelector('.lxi-banner').innerHTML,/data-lxi="see"/,'grabbed: no second Giật');
  doc.key('Escape');
  await wait(450);
  assert.equal(roots().length,0);
});

test('over a game or a sheet: only the chip; my own packet says Xem; a blocked giver shows nothing',async()=>{
  const m=await fresh();
  const d=sheet();
  const e=env('work');
  const p=packet();
  m.onLixi(e,p);
  assert.equal(roots().length,0,'never rains over a game');
  const [c]=chips(d);
  assert.ok(c,'the chip is in the top dialog (a tap reaches it)');
  assert.match(c.innerHTML,/data-lxi="grab"/);
  c.fire('click',tap('x'));
  await wait(400);
  assert.equal(chips().length,0);
  m.markMine(50000,5);
  m.onLixi(e,packet({total:50000,n:5,left:5}));
  const [mine]=chips(d);
  assert.match(mine.innerHTML,/<b>Bạn<\/b>/);
  assert.match(mine.innerHTML,/data-lxi="see"/);
  assert.ok(!mine.innerHTML.includes('data-lxi="grab"'));
  mine.fire('click',tap('x'));
  await wait(400);
  m.onLixi(e,packet({no:true,name:'',wish:''}));
  assert.equal(chips().length+roots().length,0);
  m.onLixi(e,packet({ago:120}));
  assert.equal(chips().length+roots().length,0,'a late page only gets the card');
  d.remove();
});

test('the last envelope gone: the rain says so and ends; a failed grab marks the packet empty',async()=>{
  const m=await fresh();
  const e=env('home',async()=>{const err=new Error('Hết bao rồi! Lần sau nhanh tay hơn nhé.');err.data={code:'empty'};throw err;});
  const p=packet({left:2});
  m.onWelcome(e,[p]);
  const [root]=roots();
  assert.ok(root,'the welcome rains a packet just given');
  m.onUpdate(e,{id:p.id,left:0,done:true});
  assert.ok(root.cls.has('out'));
  await wait(450);
  assert.equal(roots().length,0);
  const q=packet();
  m.onLixi(e,q);
  const [r2]=roots();
  await r2.fire('click',tap('grab'));
  await wait(0);
  assert.equal(cards.LX.packets.get(q.id).status,'done');
  assert.equal(r2.querySelector('.lxi-text small').textContent,'Hết bao rồi! Lần sau nhanh tay hơn nhé.');
  doc.key('Escape');
  await wait(450);
  const s=sheet();   // grabbing from a chip over a game: a toast
  const ok=env('work');
  const z=packet();
  m.onLixi(ok,z);
  const [c]=chips(s);
  c.fire('click',tap('grab'));
  await wait(10);
  assert.deepEqual(ok.toasts,[['ok','good']]);
  s.remove();
  await wait(400);
});

test('the 🧧 list puts what I can still grab first (owner 17/10)',()=>{
  const t=now();
  const done=cards.upsert(packet({at:t-10,left:0,status:'done'}),true);
  const mine=cards.upsert(packet({at:t-5,own:true}),true);
  const got=cards.upsert(packet({at:t-4}),true);cards.LX.got.set(got.id,500);
  const old=cards.upsert(packet({at:t-300}),true);
  const fresh2=cards.upsert(packet({at:t-1}),true);
  const ids=cards.ranked().map(p=>p.id);
  const at=id=>ids.indexOf(id);
  assert.ok(at(fresh2.id)<at(old.id),'newest grabbable first');
  for(const x of [mine,got,done])assert.ok(at(old.id)<at(x.id),'every grabbable one before the rest');
  assert.ok(at(got.id)<at(done.id)&&at(mine.id)<at(done.id),'open ones before finished ones');
  assert.ok(cards.grabbable(old)&&!cards.grabbable(got)&&!cards.grabbable(mine)&&!cards.grabbable(done));
});
