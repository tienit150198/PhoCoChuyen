// Unit test of public/js/update.js ("Đã có phiên bản mới" pill) with a tiny fake DOM.
// Run by tests/test_webassets.py (node tests/update_pill.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {shouldOffer,compareRelease,UpdateNotice,TEXT} from '../public/js/update.js';

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
console.log('update pill: ok');
