// Unit test of public/js/update.js ("Đã có phiên bản mới" pill) with a tiny fake DOM.
// Run by tests/test_webassets.py (node tests/update_pill.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {shouldOffer,compareRelease,UpdateNotice,TEXT,FIRM,RELOAD_GAP,releaseUrls,prewarmRelease} from '../public/js/update.js';

assert.equal(compareRelease('0.9.0+a','0.8.10+b'),1);
assert.equal(compareRelease('0.8.0+a','0.8.0+b'),0);
assert.equal(compareRelease('0.8.0','0.10.0'),-1);
assert.equal(compareRelease('dev','0.8.0'),null);
assert.equal(shouldOffer('0.8.0+a','0.8.0+a',''),false,'same version');
assert.equal(shouldOffer('0.8.0+a','0.8.0+b',''),true,'same release, new build');
assert.equal(shouldOffer('0.8.0+a','0.8.1+b',''),true,'newer release');
assert.equal(shouldOffer('0.8.1+a','0.8.0+b',''),false,'an older worker during a rolling restart is not an update');
assert.equal(shouldOffer('0.8.0+a','0.8.0+b','0.8.0+b'),false,'dismissed version');
assert.equal(shouldOffer('0.8.0+a','0.8.0+b','0.8.0+b',true),true,'incompatible wins over dismissal');
assert.equal(shouldOffer('0.8.0+a',null,''),false);

function fakeDoc(){
  const body={children:[],append(el){this.children.push(el);el.isConnected=true;el.parent=this;}};
  const make=tag=>({tag,children:[],attrs:{},dataset:{},listeners:{},classList:{set:new Set(),add(c){this.set.add(c);}},isConnected:false,
    append(...els){this.children.push(...els);},setAttribute(k,v){this.attrs[k]=v;},addEventListener(t,f){this.listeners[t]=f;},
    remove(){this.isConnected=false;if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);}});
  const listeners={};
  return {body,visibilityState:'visible',createElement:make,addEventListener(t,f){listeners[t]=f;},listeners};
}
const store=()=>{const m=new Map();return {getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,String(v))};};

{ // page with its own version: a new build shows the pill once; reload is only on tap; dismiss hides until next version
  const doc=fakeDoc(),storage=store();let reloads=0;
  const n=new UpdateNotice('0.8.0+aaa',{doc,storage,reload:()=>reloads++});
  assert.equal(n.seen('0.8.0+aaa'),false);assert.equal(doc.body.children.length,0);
  assert.equal(n.seen('0.8.0+bbb'),true);assert.equal(doc.body.children.length,1);
  const pill=doc.body.children[0];assert.equal(pill.className,'update-pill');assert.equal(pill.children[0].textContent,TEXT);
  n.seen('0.8.0+bbb');assert.equal(doc.body.children.length,1,'one pill per version');
  assert.equal(reloads,0,'never reloads by itself');
  pill.children[0].listeners.click();assert.equal(reloads,1,'tap reloads');
  pill.children[1].listeners.click();assert.equal(doc.body.children.length,0,'dismissed');
  assert.equal(n.seen('0.8.0+bbb'),false,'dismissed version stays hidden');
  assert.equal(n.seen('0.8.0+ccc'),true,'next version shows again');
  n.dismiss();
  assert.equal(n.seen('0.8.0+ccc',true),true,'incompatible shows at once');
}
{ // page without a stamped version adopts the first one it sees (bootstrap)
  const doc=fakeDoc(),n=new UpdateNotice('',{doc,storage:store(),reload:()=>{}});
  assert.equal(n.seen('0.8.0+aaa'),false);assert.equal(n.own,'0.8.0+aaa');
  assert.equal(n.seen('0.8.0+bbb'),true);
}
{ // /api/health is polled when the tab becomes visible again
  const doc=fakeDoc(),n=new UpdateNotice('0.8.0+aaa',{doc,storage:store(),reload:()=>{}});let checks=0;
  n.watch(async()=>{checks++;});doc.listeners.visibilitychange();assert.equal(checks,1);
  doc.visibilityState='hidden';doc.listeners.visibilitychange();assert.equal(checks,1);
  clearInterval(n.timer);
}
{ // back to the tab after a deploy: reload by itself when idle, once per version; otherwise the pill
  const doc=fakeDoc(),session=store(),win={listeners:{},addEventListener(t,f){this.listeners[t]=f;}};
  let reloads=0,idle=true,server='0.8.0+aaa';
  const n=new UpdateNotice('0.8.0+aaa',{doc,storage:store(),session,reload:()=>reloads++,idle:()=>idle});
  let clock=1e6;n.now=()=>clock;   // RELOAD_GAP: at most one reload by itself every 2 minutes
  const check=async()=>{n.seen(server);};
  n.watch(check,win);clearInterval(n.timer);
  assert.equal(n.seen('0.8.0+bbb'),true);assert.equal(reloads,0,'on the page: the pill only');
  doc.listeners.visibilitychange();await Promise.resolve();
  assert.equal(reloads,0,'same release on the server: no reload');
  server='0.8.1+bbb';doc.listeners.visibilitychange();await new Promise(r=>setTimeout(r,0));
  assert.equal(reloads,1,'back to the tab, idle, new release: reloads');
  assert.equal(n.returning,false);
  doc.listeners.visibilitychange();await new Promise(r=>setTimeout(r,0));
  assert.equal(reloads,1,'never twice for one version (no reload loop)');
  server='0.8.2+ccc';idle=false;doc.listeners.visibilitychange();await new Promise(r=>setTimeout(r,0));
  assert.equal(reloads,1,'typing or sending: no reload');assert.equal(n.shown,'0.8.2+ccc','the pill instead');
  idle=true;win.listeners.pageshow({persisted:true});await new Promise(r=>setTimeout(r,0));
  assert.equal(reloads,1,'within RELOAD_GAP of the last reload: no second one (no loop during a rolling deploy)');
  clock+=RELOAD_GAP;win.listeners.pageshow({persisted:true});await new Promise(r=>setTimeout(r,0));
  assert.equal(reloads,2,'a page restored from the back/forward cache counts as coming back');
  assert.equal(n.seen('0.8.3+ddd'),true);assert.equal(reloads,2,'while on the page: never by itself');
  clock+=RELOAD_GAP;assert.equal(n.seen('0.8.3+ddd',true),true);assert.equal(reloads,3,'incompatible + idle: reloads');
  clearTimeout(n.later);
  const broken=new UpdateNotice('0.8.0+aaa',{doc:fakeDoc(),storage:store(),session:{getItem(){throw new Error('blocked');},setItem(){throw new Error('blocked');}},reload:()=>reloads++,idle:()=>true});
  broken.returning=true;assert.equal(broken.seen('0.9.0+x'),true);assert.equal(reloads,3,'no session storage: no auto reload (no loop guard), pill');
}
{ // the pill prewarms the new release once per version (never its own, never "incompatible")
  const warmed=[];const n=new UpdateNotice('0.8.0+aaa',{doc:fakeDoc(),storage:store(),reload:()=>{},prewarm:v=>warmed.push(v)});
  n.seen('0.8.0+bbb');n.seen('0.8.0+bbb');n.seen('0.8.0+aaa',true);await Promise.resolve();await Promise.resolve();
  assert.deepEqual(warmed,['0.8.0+bbb']);
  const urls=releaseUrls('<link rel="modulepreload" href="/js/v4/a.js?v=0123456789ab"><link rel="preload" as="style" href="/css/app.css?v=abcdefabcdef"><script type="module" src="/js/app.js?v=111111111111"></script><img src="/icons/x.webp?v=222222222222"><link href="/js/raw.js">');
  assert.deepEqual([...urls],['/js/v4/a.js?v=0123456789ab','/css/app.css?v=abcdefabcdef','/js/app.js?v=111111111111']);
}
{ // prewarmRelease: the new page's first-frame files, this browser's workplace through its import map, minus this page's own
  const page=`<script type="importmap">{"imports":{"/js/careers/farm.js":"/js/careers/farm.js?v=bbbbbbbbbbbb","/js/scenes/farm.js":"/js/scenes/farm.js?v=cccccccccccc"}}</script><meta name="mnl-content" content="/api/content?v=dddddddddddd"><link rel="modulepreload" href="/js/api.js?v=aaaaaaaaaaaa"><link rel="modulepreload" href="/js/same.js?v=eeeeeeeeeeee">`;
  globalThis.fetch=async url=>{assert.equal(url,'/');return new Response(page,{status:200});};
  const head={children:[],append(el){this.children.push(el);}};
  const doc={head,createElement:()=>({}),querySelector:s=>s.startsWith('script')?{textContent:'{"imports":{"/js/same.js":"/js/same.js?v=eeeeeeeeeeee"}}'}:s.startsWith('meta')?{content:'/api/content?v=0000000000'}:null};
  const storage=store();storage.setItem('mnl.warm',JSON.stringify(['/js/careers/farm.js']));storage.setItem('mnl.scene','/js/scenes/farm.js');
  assert.equal(await prewarmRelease(doc,storage),4);
  assert.deepEqual(head.children.map(l=>[l.rel,l.href]),[['prefetch','/js/api.js?v=aaaaaaaaaaaa'],['prefetch','/js/careers/farm.js?v=bbbbbbbbbbbb'],['prefetch','/js/scenes/farm.js?v=cccccccccccc'],['prefetch','/api/content?v=dddddddddddd&part=core']]);
}
{ // 07/10: a page behind the server's RELEASE (tabs from before 1.9.5 sent offers the server no longer takes): the pill
  // keeps itself (no ✕, a dismissed version shows again) and the next navigation reloads when idle, once per version
  const doc=fakeDoc(),storage=store(),session=store();let reloads=0,idle=false;
  const n=new UpdateNotice('1.9.4+aaa',{doc,storage,session,reload:()=>reloads++,idle:()=>idle});
  assert.equal(n.navigated(),false,'nothing newer seen: navigation is just navigation');
  assert.equal(n.seen('1.9.4+bbb'),true);assert.equal(n.behind,null,'a new build of the same release is not "behind"');
  assert.equal(doc.body.children[0].children.length,2,'a new build: the pill keeps its ✕');
  assert.equal(n.navigated(),false);
  storage.setItem('mnl.update.dismissed','1.9.10+ccc');
  assert.equal(n.seen('1.9.10+ccc'),true,'behind: a dismissed version shows again');
  const pill=doc.body.children.at(-1);
  assert.equal(pill.children.length,1,'no ✕');assert.equal(pill.children[0].textContent,'🔄 '+FIRM);assert.match(pill.className,/is-firm/);
  assert.equal(reloads,0,'never by itself while on the page');
  assert.equal(n.navigated(),false);assert.equal(reloads,0,'typing or sending: no reload');
  idle=true;assert.equal(n.navigated(),true);assert.equal(reloads,1,'next navigation, idle: reloads');
  assert.equal(n.navigated(),false);assert.equal(reloads,1,'once per version (no reload loop)');
  assert.equal(new UpdateNotice('1.9.10+ccc',{doc:fakeDoc(),storage:store(),reload:()=>reloads++}).seen('1.9.9+ddd'),false,'an older worker during a rolling deploy: nothing');
}
{ // 426 client_outdated (server.py MIN_CLIENT) while a command is still being answered (not idle): tried again a
  // moment later, then at the next navigation
  const doc=fakeDoc();let reloads=0,idle=false;
  const n=new UpdateNotice('1.9.10+aaa',{doc,storage:store(),session:store(),reload:()=>reloads++,idle:()=>idle});
  assert.equal(n.seen('1.9.11+bbb',true),true);assert.equal(reloads,0);
  idle=true;await new Promise(r=>setTimeout(r,1600));
  assert.equal(reloads,1,'reloads once the command is answered');
  assert.equal(n.seen('1.9.11+bbb',true),true);await new Promise(r=>setTimeout(r,1600));
  assert.equal(reloads,1,'never twice for one version');
}
console.log('update pill: ok');
