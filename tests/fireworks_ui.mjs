// 🎆 public/js/v4/fireworks.js never in the way of play (#299 "bấm x thì thoát hoạt động đang làm", #300 "tắt hiệu
// ứng pháo hoa ở đâu", #301 "đang chơi phóng dao mà pháo hoa che hết màn hình"), with a tiny fake DOM.
// Run: node --test tests/fireworks_ui.mjs   (tests/test_fireworks_show.py runs it too)
import assert from 'node:assert/strict';
import test from 'node:test';

/* ---- a tiny DOM: what fireworks.js touches ---- */
class El{
  constructor(tag){
    this.tagName=tag.toUpperCase();this.children=[];this.parent=null;this.dataset={};this.attrs={};this.listeners={};
    this.style={props:{},setProperty(k,v){this.props[k]=v;},cssText:''};this.cls=new Set();this.className='';this._html='';this.parts={};
    this.open=false;this.modal=false;this.id='';this.closes=0;this.popoverOpen=false;this.textContent='';
    const self=this;this.classList={add:c=>self.cls.add(c),remove:c=>self.cls.delete(c),contains:c=>self.cls.has(c)};
  }
  set innerHTML(v){this._html=v;this.parts={};}
  get innerHTML(){return this._html;}
  append(...els){for(const e of els){if(e.parent)e.parent.children=e.parent.children.filter(x=>x!==e);e.popoverOpen=false;e.parent=this;this.children.push(e);}}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);this.parent=null;this.popoverOpen=false;}
  get isConnected(){for(let p=this;p;p=p.parent)if(p===doc.body||p===doc.head)return true;return false;}
  setAttribute(k,v){this.attrs[k]=v;}
  addEventListener(t,f){(this.listeners[t]??=[]).push(f);}
  fire(t,ev){for(const f of this.listeners[t]||[])f(ev);return ev;}
  querySelector(sel){
    const key={'canvas':'<canvas','.fw-tint':'fw-tint','.fw-banner':'fw-banner'}[sel];
    if(!key||!this._html.includes(key))return null;
    return this.parts[sel]??=Object.assign(new El(sel==='canvas'?'canvas':'div'),{getContext:()=>null});
  }
  showPopover(){if(!this.isConnected)throw new Error('not connected');this.popoverOpen=true;}
  hidePopover(){this.popoverOpen=false;}
  matches(sel){return sel===':modal'?this.modal&&this.open:false;}
  closest(sel){for(let p=this;p;p=p.parent)if(sel==='dialog[open]'&&p.tagName==='DIALOG'&&p.open)return p;return null;}
  close(){this.open=false;this.closes++;}
}
const all=el=>[el,...el.children.flatMap(all)];
const doc={
  head:new El('head'),body:new El('body'),documentElement:{classList:{contains:()=>false}},fullscreenElement:null,listeners:{},stack:[],
  createElement:t=>new El(t),
  querySelector(sel){return sel==='style[data-fw-css]'?all(this.head).find(e=>e.tagName==='STYLE')||null:null;},
  querySelectorAll(sel){return sel==='dialog[open]'?all(this.body).filter(e=>e.tagName==='DIALOG'&&e.open):[];},
  elementFromPoint(){return this.stack.filter(d=>d.open).at(-1)||this.body;},   // the last modal opened takes the taps
  addEventListener(t,f){(this.listeners[t]??=[]).push(f);},
  removeEventListener(t,f){this.listeners[t]=(this.listeners[t]||[]).filter(x=>x!==f);},
  key(key){const ev={key,prevented:false,stopped:false,preventDefault(){this.prevented=true;},stopPropagation(){this.stopped=true;}};for(const f of [...(this.listeners.keydown||[])])f(ev);return ev;},
};
globalThis.document=doc;
globalThis.requestAnimationFrame=()=>1;globalThis.cancelAnimationFrame=()=>{};
let reduce=false;globalThis.matchMedia=q=>({matches:reduce&&q.includes('reduce')});
const store=new Map();let blocked=false;
globalThis.localStorage={getItem:k=>{if(blocked)throw new Error('blocked');return store.has(k)?store.get(k):null;},setItem:(k,v)=>{if(blocked)throw new Error('blocked');store.set(k,String(v));}};
globalThis.sessionStorage={getItem:()=>null,setItem:()=>{}};

function reset(){
  for(const e of [...doc.body.children])e.remove();for(const e of [...doc.head.children])e.remove();
  doc.stack=[];doc.listeners={};doc.fullscreenElement=null;store.clear();blocked=false;reduce=false;
}
function dialog(id=''){const d=new El('dialog');d.id=id;d.open=true;d.modal=true;doc.body.append(d);doc.stack.push(d);return d;}
let n=0;
const fresh=async()=>{reset();return import(`../public/js/v4/fireworks.js?t=${++n}`);};
const env=(view=null)=>({ui:{view},api:{state:{journey:{}}},toasts:[],toast(t){this.toasts.push(t);}});
const show=(id,extra={})=>({id,size:'nho',name:'Lan',wish:'',ago:0,...extra});
const roots=(el=doc.body)=>all(el).filter(e=>e.className.startsWith('fw-root'));
const chips=(el=doc.body)=>all(el).filter(e=>e.className==='fw-chip');
const tap=fw=>({target:{closest:()=>({dataset:{fw}})},stopped:false,stopPropagation(){this.stopped=true;}});
const wait=ms=>new Promise(r=>setTimeout(r,ms));

test('what to show: the setting, a game in progress, the buyer',async()=>{
  const m=await fresh();
  assert.equal(m.howToShow({mode:'on'}),'full');
  assert.equal(m.howToShow({mode:'on',busy:true}),'chip','never the full show over a game or a sheet');
  assert.equal(m.howToShow({mode:'small'}),'chip');
  assert.equal(m.howToShow({mode:'off'}),'none');
  assert.equal(m.howToShow({mode:'off',busy:true,mine:true}),'full','the buyer always sees their own');
  assert.deepEqual(m.FW_MODES.map(x=>x[0]),['on','small','off']);
});

test('the show never takes a tap: the layers are pointer-events none, only the banner and the chip take taps',async()=>{
  const m=await fresh();
  m.onFireworks(env(),show('a'));
  const css=doc.head.children[0].textContent;
  assert.match(css,/\.fw-root\{[^}]*pointer-events:none/);
  assert.match(css,/\.fw-tint\{[^}]*pointer-events:none/);
  assert.match(css,/\.fw-root canvas\{[^}]*pointer-events:none/);
  assert.match(css,/@media \(prefers-reduced-motion:reduce\)/);
  const [root]=roots();root.fire('click',tap('x'));
  await wait(450);
});

test('#301: in a fair game (any dialog but the home sheet) only a small chip, inside that dialog',async()=>{
  const m=await fresh(),fair=dialog();
  m.onFireworks(env(),show('b'));
  assert.equal(roots().length,0,'no full show over phóng dao');
  const [chip]=chips();
  assert.ok(chip,'a chip');assert.equal(chip.parent,fair,'inside the open dialog: never an inert layer over it');
  assert.equal(chip.popoverOpen,true);
  assert.match(chip.innerHTML,/<b data-no-translate>Lan<\/b> <span>đang bắn pháo hoa<\/span>/);
  assert.match(chip.innerHTML,/data-fw="see">Xem</);
  // its ✕: the chip goes, the game stays
  const ev=chip.fire('click',tap('x'));
  assert.equal(ev.stopped,true,'the tap stops at the chip');
  assert.equal(fair.open,true);assert.equal(fair.closes,0);
  await wait(350);assert.equal(chips().length,0);
});

test('#299: on the home sheet the show lives inside it, ✕ and Escape close only the show',async()=>{
  const m=await fresh(),home=dialog('sheet');
  m.onFireworks(env('home'),show('c'));
  const [root]=roots();
  assert.ok(root,'the full show on the town screen');
  assert.equal(root.parent,home,'inside the modal sheet (a popover outside it is inert: taps fell through to its backdrop)');
  assert.equal(root.popoverOpen,true);
  assert.match(root.innerHTML,/data-fw="x" aria-label="Đóng pháo hoa"/);
  for(const t of ['click','pointerdown','touchstart'])assert.ok(root.listeners[t]?.length,`${t} stops at the show`);
  const ev=root.fire('click',tap('x'));
  assert.equal(ev.stopped,true);assert.equal(home.open,true);assert.equal(home.closes,0,'the activity under it stays');
  await wait(450);assert.equal(roots().length,0,'the show is gone');

  m.onFireworks(env('home'),show('d'));
  const k=doc.key('Escape');
  assert.equal(k.prevented,true,'Escape closes the show, not the sheet');assert.equal(k.stopped,true);
  assert.equal(home.open,true);
  await wait(450);assert.equal(roots().length,0);
  assert.equal(doc.key('Escape').prevented,false,'no show: Escape is the dialog\'s again');
});

test('a show on screen gives way when a game opens, and follows the player back to an open screen',async()=>{
  const m=await fresh(),e=env(null);
  m.onFireworks(e,show('e'));
  let [root]=roots();assert.equal(root.parent,doc.body);
  const home=dialog('sheet');e.ui.view='home';m.watch();
  [root]=roots();assert.equal(root.parent,home,'moved into the home sheet: its ✕ still takes taps');
  e.ui.view='job';m.watch();   // a work task in the same sheet
  await wait(450);assert.equal(roots().length,0,'ended when the work sheet opened');
  home.close();
});

test('#300: Tắt shows nothing, Chỉ báo nhỏ only the chip; kept on this device, and storage blocked still works',async()=>{
  let m=await fresh();
  assert.equal(m.fwMode(),'on','default on');
  m.setFwMode('off');assert.equal(store.get('mnl.fw.mode'),'off');
  m.onFireworks(env(),show('f'));assert.equal(roots().length+chips().length,0);
  m=await import(`../public/js/v4/fireworks.js?t=${++n}`);   // a new tab, the same device
  assert.equal(m.fwMode(),'off');
  m.setFwMode('small');m.onFireworks(env(),show('g'));
  assert.equal(roots().length,0);assert.equal(chips().length,1,'only the chip, even on an open screen');
  assert.equal(m.setFwMode('loud'),false);assert.equal(m.fwMode(),'small');
  m=await fresh();blocked=true;
  assert.equal(m.fwMode(),'on');m.setFwMode('off');assert.equal(m.fwMode(),'off','this tab remembers');
  m.onFireworks(env(),show('h'));assert.equal(roots().length+chips().length,0);
});

test('the buyer sees their own show in full, whatever the setting and the screen',async()=>{
  const m=await fresh(),shop=dialog();
  m.setFwMode('off');m.markMine('lon');
  m.onFireworks(env(),show('i',{size:'dai_tiec'}));
  assert.equal(roots().length+chips().length,0,'another size: not theirs');
  m.onFireworks(env(),show('j',{size:'lon'}));
  const [root]=roots();assert.ok(root,'their show');assert.equal(root.parent,shop);
  assert.doesNotMatch(root.innerHTML,/data-fw="calm"/,'no "Chỉ báo nhỏ" on their own show');
  shop.close();m.watch();assert.equal(root.parent,doc.body,'the shop closed: the show stays on the page');
  root.fire('click',tap('x'));await wait(450);
  m.markMine('nho');m.markMine(null);m.onFireworks(env(),show('k'));
  assert.equal(roots().length,0,'a refused purchase is not theirs');
});

test('"Xem" on the chip plays the show over the game it was asked in; "Chỉ báo nhỏ" on the banner switches the setting',async()=>{
  const m=await fresh(),fair=dialog(),e=env();
  m.onFireworks(e,show('l'));
  const [chip]=chips();chip.fire('click',tap('see'));
  const [root]=roots();assert.ok(root);assert.equal(root.parent,fair);
  m.watch();assert.equal(root.cls.has('out'),false,'stays: the player asked for it');
  root.fire('click',tap('x'));assert.equal(fair.closes,0);await wait(450);
  fair.close();
  m.onFireworks(e,show('m'));
  const [r2]=roots();assert.match(r2.innerHTML,/data-fw="calm">🔕 Chỉ báo nhỏ</);
  r2.fire('click',tap('calm'));
  assert.equal(m.fwMode(),'small');assert.match(e.toasts[0],/Cài đặt → Cách chơi/);
  await wait(450);assert.equal(roots().length,0);
});

test('reduced motion and a fullscreen game',async()=>{
  const m=await fresh();
  doc.fullscreenElement=new El('div');
  assert.equal(m.idleScreen(null),false);
  m.onFireworks(env(),show('n'));assert.equal(roots().length+chips().length,0,'nothing over a fullscreen game');
  doc.fullscreenElement=null;reduce=true;
  m.onFireworks(env(),show('o'));const [root]=roots();assert.ok(root,'the light show (calm sky) still plays');
  root.fire('click',tap('x'));await wait(450);
});
