import './phaser25d-wired.mjs';  // skipped while the 2.5D client is not wired (docs/PHASER_25D.md)
import test from 'node:test';
import assert from 'node:assert/strict';
import {ART,defaultLook,portrait,figureSVG,cozyPortraits} from '../public/js/v4/look.js';

test('the classic UI keeps its portrait markup: no marker until the 2.5D client turns them on',()=>{
  const look={...defaultLook('female'),hair:'toc_bui_doi'};
  assert.doesNotMatch(portrait(look,'female',42,'Mây'),/data-cozy-portrait/);
  assert.doesNotMatch(figureSVG(look,'female'),/data-cozy-portrait/);
  cozyPortraits(true);   // what public/js/iso-boot.js does
});

const marker=svg=>svg.match(/data-cozy-portrait="([^"]+)"/)?.[1];
test('portrait markers safely carry saved wardrobe and keep cropped item tiles native',()=>{
  const look={...defaultLook('female'),hair:'toc_bui_doi',top:'dam_cong_chua',acc:'kinh_tron',uniform:false,tint:{dam_cong_chua:'mint',kinh_tron:'rose'}};
  const svg=portrait(look,'female',42,'Bạn "<Mây> & An');
  assert.ok(marker(svg),'decorative portrait is explicitly tagged');
  const data=JSON.parse(decodeURIComponent(marker(svg)));
  assert.equal(data.mode,'face');assert.equal(data.gender,'female');
  assert.equal(data.look.hair,'toc_bui_doi');assert.equal(data.look.tint.dam_cong_chua,'mint');
  assert.match(svg,/aria-label="Bạn &quot;&lt;Mây&gt; &amp; An"/);
  assert.equal(JSON.parse(decodeURIComponent(marker(figureSVG(look,'female')))).mode,'figure');
  assert.equal(marker(figureSVG(look,'female',{box:'-30 -30 60 36'})),undefined,'shoe crop stays a focused item picture');
});

class Element {
  constructor(name,doc){this.nodeType=1;this.localName=name;this.ownerDocument=doc;this.attrs=new Map();this.children=[];this.parentNode=null;}
  setAttribute(k,v){this.attrs.set(k,String(v));}
  getAttribute(k){return this.attrs.get(k)??null;}
  hasAttribute(k){return this.attrs.has(k);}
  get isConnected(){return this.ownerDocument.contains(this);}
  contains(node){return node===this||this.children.some(c=>c.contains(node));}
  matches(s){return s==='svg[data-cozy-portrait]'?this.localName==='svg'&&this.hasAttribute('data-cozy-portrait'):s.split(',').some(x=>{x=x.trim();return x===this.localName||x==='[data-action]'&&this.hasAttribute('data-action')||x==='[tabindex]'&&this.hasAttribute('tabindex')||x==='[onclick]'&&this.hasAttribute('onclick')||x==='[role="button"]'&&this.getAttribute('role')==='button';});}
  querySelectorAll(s){const out=[];for(const child of this.children){if(child.matches(s))out.push(child);out.push(...child.querySelectorAll(s));}return out;}
  querySelector(s){return this.querySelectorAll(s)[0]||null;}
  replaceChildren(...nodes){for(const n of this.children)n.parentNode=null;this.children=[];for(const n of nodes){n.parentNode=this;this.children.push(n);}}
  append(...nodes){for(const n of nodes){n.parentNode=this;this.children.push(n);}}
  remove(){if(this.parentNode)this.parentNode.children=this.parentNode.children.filter(n=>n!==this);this.parentNode=null;}
  cloneNode(){const n=new Element(this.localName,this.ownerDocument);n.attrs=new Map(this.attrs);return n;}
}
function fixture(){
  const root=new Element('document',null);root.nodeType=9;root.ownerDocument=root;root.createElementNS=(_,name)=>new Element(name,root);
  const frames=new Map();let next=0,requests=0,observer,reads=0,ready=false;const callbacks=new Set();
  const options={root,requestFrame:fn=>{requests++;frames.set(++next,fn);return next;},cancelFrame:id=>frames.delete(id),Observer:class {constructor(fn){this.callback=fn;observer=this;}observe(){}disconnect(){this.disconnected=true;}},getStamp:o=>{reads++;callbacks.add(o.onReady);return {canvas:{},ready};},makeThumbnail:(_,mode)=>`data:image/png;base64,${mode}`};
  const svg=(look=defaultLook('female'))=>{const n=new Element('svg',root);n.setAttribute('data-cozy-portrait',marker(portrait(look,'female',42,'Bạn')));n.setAttribute('viewBox','0 0 80 80');n.setAttribute('width','42');n.setAttribute('role','img');n.setAttribute('aria-label','Bạn');root.append(n);return n;};
  return {root,options,svg,flush:()=>{const fs=[...frames.values()];frames.clear();fs.forEach(f=>f());},mutate:r=>observer.callback(r),loaded:()=>{ready=true;callbacks.forEach(f=>f());},stats:()=>({reads,requests,queued:frames.size,observer})};
}

test('enhancer batches changes, keeps accessible roots, refreshes loaded art and releases removed nodes',async()=>{
  const {bootCozyPortraits}=await import('../public/js/isometric/portraits.js');
  const f=fixture(),a=f.svg(),b=f.svg(),title=new Element('title',f.root);a.append(title,new Element('path',f.root));
  const interactive=f.svg();interactive.setAttribute('data-action','craft');
  const controller=bootCozyPortraits(f.options);
  assert.equal(bootCozyPortraits(f.options),controller,'one observer per root');
  assert.equal(f.stats().queued,1);f.flush();
  assert.equal(f.stats().reads,1,'identical portraits share the thumbnail');
  assert.equal(a.getAttribute('aria-label'),'Bạn');assert.equal(a.getAttribute('width'),'42');
  assert.ok(a.querySelector('title'));assert.ok(a.querySelector('image'));assert.equal(interactive.querySelector('image'),null);
  assert.equal(a.getAttribute('data-cozy-ready'),'false');
  const requests=f.stats().requests;
  f.mutate([{type:'childList',target:a,addedNodes:a.children,removedNodes:[]}]);
  assert.equal(f.stats().requests,requests,'own generated image does not start an observer loop');
  f.loaded();assert.equal(f.stats().queued,1);f.flush();
  assert.equal(f.stats().reads,2);assert.equal(a.getAttribute('data-cozy-ready'),'true');
  a.setAttribute('data-cozy-portrait',marker(portrait({...defaultLook('female'),top:'ao_len',tint:{ao_len:'mint'}},'female')));
  f.mutate([{type:'attributes',attributeName:'data-cozy-portrait',target:a}]);f.flush();
  assert.equal(f.stats().reads,3,'new wardrobe palette requests a new thumbnail');
  a.remove();b.remove();interactive.remove();f.mutate([{type:'childList',target:f.root,addedNodes:[],removedNodes:[a,b,interactive]}]);
  f.loaded();f.flush();assert.equal(f.stats().reads,3,'removed roots are released');
  controller.disconnect();assert.ok(f.stats().observer.disconnected);f.loaded();assert.equal(f.stats().queued,0);
});

test('thumbnail cache remains bounded at 64 wardrobe combinations',async()=>{
  const {bootCozyPortraits}=await import('../public/js/isometric/portraits.js');
  const f=fixture(),base=defaultLook('female'),hair=Object.keys(ART.hair),shade=Object.keys(ART.shade),skin=Object.keys(ART.skin),looks=[];
  for(let n=0;n<65;n++){const look={...base,hair:hair[n%hair.length],shade:shade[Math.floor(n/hair.length)%shade.length],skin:skin[Math.floor(n/(hair.length*shade.length))%skin.length]};looks.push(look);f.svg(look);}
  const controller=bootCozyPortraits(f.options);f.flush();assert.equal(f.stats().reads,65);
  const first=f.svg(looks[0]);f.mutate([{type:'childList',target:f.root,addedNodes:[first],removedNodes:[]}]);f.flush();assert.equal(f.stats().reads,66,'oldest combination was evicted');
  const last=f.svg(looks[64]);f.mutate([{type:'childList',target:f.root,addedNodes:[last],removedNodes:[]}]);f.flush();assert.equal(f.stats().reads,66,'recent combination is still cached');
  controller.disconnect();
});

test('malformed and oversized markers keep their SVG fallback',async()=>{
  const {decodeCozyPortrait}=await import('../public/js/isometric/portraits.js');
  assert.equal(decodeCozyPortrait('%broken'),null);assert.equal(decodeCozyPortrait('x'.repeat(9000)),null);
  assert.equal(decodeCozyPortrait(encodeURIComponent(JSON.stringify({v:1,mode:'workbench',gender:'female',look:{}}))),null);
  const clean=decodeCozyPortrait(encodeURIComponent(JSON.stringify({v:1,mode:'face',gender:'female',look:{hair:'__proto__',top:'ao_len',tint:{ao_len:'constructor'}}})));
  assert.equal(clean.look.hair,defaultLook('female').hair);assert.equal(clean.look.tint,undefined);
});

test('wardrobe rotation reaches the illustrated renderer and uses distinct thumbnails',async()=>{
 const {decodeCozyPortrait,bootCozyPortraits}=await import('../public/js/isometric/portraits.js');
 const f=fixture(),seen=[];f.options.getStamp=o=>{seen.push(o.direction);return {canvas:{},ready:true};};
 for(const facing of ['se','sw','nw','ne']){const n=f.svg();n.setAttribute('data-cozy-portrait',marker(figureSVG(defaultLook('female'),'female',{facing})));}
 const ctl=bootCozyPortraits(f.options);f.flush();assert.deepEqual(seen,['se','sw','nw','ne']);ctl.disconnect();
 assert.equal(decodeCozyPortrait(encodeURIComponent(JSON.stringify({v:1,mode:'figure',gender:'male',look:{},facing:'bad'}))).facing,'se');
});
