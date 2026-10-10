import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {build} from 'esbuild';

const html=readFileSync('public/career-gallery.html','utf8');
const ids=JSON.parse(readFileSync('game/town_layout.json','utf8')).careerOrder;
const catalogue=ids.map(id=>({id,short:id,place:'Nơi làm việc '+id,focus:'Công việc '+id,playable:false}));
catalogue.find(c=>c.id==='teacher').short='Giáo viên';
catalogue.find(c=>c.id==='railway').short='Đường sắt';
const compiled=await build({entryPoints:['client/isometric/career-gallery.ts'],bundle:true,write:false,platform:'browser',format:'iife',logLevel:'silent',plugins:[{
  name:'gallery-renderer-boundary',setup(b){
    b.onResolve({filter:/^\/js\/isometric\/phaser-world\.js$/},()=>({path:'renderer',namespace:'gallery-test'}));
    b.onLoad({filter:/.*/,namespace:'gallery-test'},()=>({contents:'export const PhaserWorld=globalThis.GalleryTestWorld;',loader:'js'}));
  },
}]});
const script=compiled.outputFiles[0].text;
const flush=async()=>{for(let i=0;i<16;i++)await Promise.resolve();};
const copy=value=>JSON.parse(JSON.stringify(value));

function harness({hash='',responseOK=true}={}){
  const nodes=new Map(),requests=[],errors=[],forbidden=[],worlds=[];
  class Target{
    listeners=new Map();
    addEventListener(type,listener){const rows=this.listeners.get(type)||[];rows.push(listener);this.listeners.set(type,rows);}
    removeEventListener(type,listener){this.listeners.set(type,(this.listeners.get(type)||[]).filter(row=>row!==listener));}
    dispatchEvent(event){for(const fn of this.listeners.get(event.type)||[])fn(event);}
  }
  class Element extends Target{
    children=[];hidden=false;value='';textContent='';attributes={};dataset={};classes=new Set();
    constructor(tag='div'){super();this.tagName=tag.toUpperCase();this.classList={toggle:(key,on)=>on?this.classes.add(key):this.classes.delete(key),add:(...keys)=>keys.forEach(key=>this.classes.add(key)),remove:(...keys)=>keys.forEach(key=>this.classes.delete(key)),contains:key=>this.classes.has(key)};}
    set id(value){this._id=value;nodes.set(value,this);}get id(){return this._id;}
    setAttribute(key,value){this.attributes[key]=String(value);}
    append(...items){for(const item of items)this.children.push(...(item.tagName==='#FRAGMENT'?item.children:[item]));}
    add(option){this.children.push(option);}
    scrollIntoView(){this.scrolled=true;}
    focus(){this.focused=true;}
    setPointerCapture(id){this.capture=id;}
  }
  for(const [,tag,attrs] of html.matchAll(/<([a-z][a-z\d]*)\b([^>]*\bid="[^"]+"[^>]*)>/gi)){
    const node=new Element(tag);node.id=attrs.match(/\bid="([^"]+)"/)[1];node.hidden=/\bhidden\b/.test(attrs);
  }
  const pad=[...html.matchAll(/<button\b([^>]*\bdata-x="[^"]+"[^>]*)>/g)].map(([,attrs])=>{
    const node=new Element('button');node.dataset={x:attrs.match(/data-x="([^"]+)"/)[1],y:attrs.match(/data-y="([^"]+)"/)[1]};return node;
  });
  const document=new Target();Object.assign(document,{hidden:false,body:new Element('body'),getElementById:id=>nodes.get(id),createElement:tag=>new Element(tag),createDocumentFragment:()=>new Element('#fragment'),querySelectorAll:selector=>selector==='#walk-pad button'?pad:[]});
  const window=new Target(),location={pathname:'/career-gallery.html',hash,search:''};
  const history={replaceState(_state,_title,url){location.hash=url.startsWith('#')?url:'';}};
  class World{
    updates=[];calls=[];hotspots=[{id:'desk',label:'Bàn thao tác'}];movement={x:0,y:0};destroyed=false;_paused=false;
    constructor(canvas,interact){this.canvas=canvas;this.interact=interact;this.ready=new Promise((resolve,reject)=>{this.resolve=resolve;this.reject=reject;});worlds.push(this);}
    update(state,content){this.state=state;this.content=content;this.updates.push(copy(state));this.calls.push('update');}
    setMode(mode){this.mode=mode;this.calls.push('mode');}
    set paused(value){this._paused=!!value;if(value)this.movement={x:0,y:0};}get paused(){return this._paused;}
    resize(){this.calls.push('resize');}resetCamera(){this.calls.push('center');}zoomBy(amount){this.calls.push(['zoom',amount]);}setZoom(amount){this.calls.push(['setZoom',amount]);}
    setMovementInput(x,y){this.movement=this.paused?{x:0,y:0}:{x,y};this.calls.push(['input',x,y]);}
    destroy(){this.destroyed=true;this.destroyCount=(this.destroyCount||0)+1;this.calls.push('destroy');}
  }
  const rejectAccess=name=>{forbidden.push(name);throw new Error('Account access forbidden: '+name);};
  const context={document,window,location,history,GalleryTestWorld:World,Option:class extends Element{constructor(text,value){super('option');this.textContent=text;this.value=value;}},
    console:{error:error=>errors.push(String(error))},matchMedia:()=>({matches:true}),Promise,
    fetch:async(url,options={})=>{requests.push({url,...copy(options)});assert.equal(url,'/api/content?part=core','gallery cannot call an account/gameplay endpoint');assert.equal(options.method||'GET','GET');assert.equal(options.credentials,'omit');return {ok:responseOK,status:responseOK?200:503,json:async()=>({catalogue:copy(catalogue)})};},
    XMLHttpRequest:()=>rejectAccess('XMLHttpRequest'),WebSocket:()=>rejectAccess('WebSocket'),navigator:{sendBeacon:()=>rejectAccess('sendBeacon')},
  };
  for(const obj of [context,window])for(const name of ['localStorage','sessionStorage'])Object.defineProperty(obj,name,{get:()=>rejectAccess(name)});
  Object.defineProperty(document,'cookie',{get:()=>rejectAccess('cookie read'),set:()=>rejectAccess('cookie write')});
  vm.runInNewContext(script,context);
  const fire=(target,type,extra={})=>target.dispatchEvent({type,preventDefault(){},...extra});
  return {nodes,pad,requests,errors,forbidden,worlds,window,document,location,fire,
    click:id=>fire(nodes.get(id),'click'),
    select:id=>{nodes.get('career').value=id;fire(nodes.get('career'),'change');},
    search:value=>{nodes.get('search').value=value;fire(nodes.get('search'),'input');},
  };
}
async function interior(){const h=harness();await flush();h.click('card-'+ids[0]);h.click('inside');await flush();h.worlds[0].resolve();await flush();return h;}

test('the HTML mounts the tested gallery module and accessible career controls',()=>{
  assert.match(html,/<script type="module" src="\/js\/isometric\/career-gallery\.js">/);
  const idsInHTML=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
  assert.equal(new Set(idsInHTML).size,idsInHTML.length,'mounted controls have no duplicate IDs');
  for(const id of ['career','search','viewer','gallery','inside','outside','all','next','previous','walk-pad','scene'])assert.ok(idsInHTML.includes(id),id);
  assert.match(html,/id="status"[^>]*role="status"[^>]*aria-live="polite"/);
});

test('all 50 catalogue professions are reachable through cards, selector and wrapping pager without unlocks',async()=>{
  const h=harness();await flush();
  assert.equal(h.nodes.get('gallery').children.length,50);assert.equal(h.nodes.get('career').children.length,50);assert.equal(h.worlds.length,0,'outside collection does not construct a renderer');
  for(const id of ids){h.click('card-'+id);await flush();assert.equal(h.nodes.get('career').value,id);assert.equal(h.nodes.get('building').src,'/icons/careers-v1/'+id+'.webp');assert.equal(h.nodes.get('viewer').hidden,false);}
  h.click('next');await flush();assert.equal(h.nodes.get('career').value,ids[0]);h.click('previous');await flush();assert.equal(h.nodes.get('career').value,ids.at(-1));
  h.click('inside');await flush();h.worlds[0].resolve();await flush();
  for(const id of ids){h.select(id);await flush();assert.equal(h.worlds[0].state.current,id);assert.equal(h.worlds[0].state.careers[id].open,true);}
  assert.equal(h.worlds.length,1,'switching careers reuses one renderer');assert.deepEqual(h.errors,[]);
});

test('preview interactions remain in memory and never access saved progress, cookies or write APIs',async()=>{
  const h=await interior(),world=h.worlds[0];
  world.interact('desk');world.interact('missing');h.click('zoom-in');h.click('zoom-out');h.click('center');
  world.state.careers[ids[0]].tasks.push({id:'local-example'});
  h.click('next');await flush();h.click('previous');await flush();
  assert.deepEqual(copy(world.state.careers[ids[0]].tasks),[],'changing the preview recreates its example state');
  assert.equal(world.state.settings.reduceMotion,true);
  assert.deepEqual(h.requests,[{url:'/api/content?part=core',credentials:'omit'}]);assert.deepEqual(h.forbidden,[]);assert.deepEqual(h.errors,[]);
});

test('switching outside or returning to the collection pauses the renderer and reopening reuses it',async()=>{
  const h=await interior(),world=h.worlds[0];
  h.click('outside');await flush();assert.equal(world.paused,true);assert.equal(h.nodes.get('interior').hidden,true);
  h.click('inside');await flush();assert.equal(world.paused,false);h.click('all');assert.equal(world.paused,true);assert.equal(h.nodes.get('viewer').hidden,true);
  h.click('card-'+ids[1]);h.click('inside');await flush();assert.equal(world.paused,false);assert.equal(h.worlds.length,1);
});

test('latest selection wins while renderer startup is pending; outside view never wakes stale work',async()=>{
  const h=harness();await flush();h.click('card-'+ids[0]);h.click('inside');h.select(ids[2]);h.select(ids[3]);
  assert.equal(h.worlds.length,1);h.worlds[0].resolve();await flush();assert.equal(h.worlds[0].state.current,ids[3]);
  const other=harness();await flush();other.click('card-'+ids[0]);other.click('inside');other.click('outside');other.worlds[0].resolve();await flush();
  assert.equal(other.worlds[0].paused,true);assert.equal(other.nodes.get('interior').hidden,true);assert.deepEqual(other.errors,[]);
});

test('pointer cancellation, focus loss and page visibility reset held movement',async()=>{
  const h=await interior(),world=h.worlds[0],right=h.pad.find(b=>b.dataset.x==='1');
  for(const end of ['pointerup','pointercancel','lostpointercapture']){h.fire(right,'pointerdown',{pointerId:7});assert.deepEqual(world.movement,{x:1,y:0});h.fire(right,end,{pointerId:7});assert.deepEqual(world.movement,{x:0,y:0});}
  h.fire(right,'pointerdown',{pointerId:7});h.fire(h.window,'blur');assert.deepEqual(world.movement,{x:0,y:0});
  h.fire(right,'pointerdown',{pointerId:7});h.document.hidden=true;h.fire(h.document,'visibilitychange');assert.deepEqual(world.movement,{x:0,y:0});
});

test('pagehide destroys the active renderer once and discards its movement',async()=>{
  const h=await interior(),world=h.worlds[0];h.fire(h.window,'pagehide');h.fire(h.window,'pagehide');
  assert.equal(world.destroyCount,1);assert.deepEqual(world.movement,{x:0,y:0});assert.deepEqual(h.errors,[]);
});

test('pagehide invalidates a pending interior before its ready promise resumes',async()=>{
  const h=harness();await flush();h.click('card-'+ids[0]);h.click('inside');const world=h.worlds[0];
  h.fire(h.window,'pagehide');world.resolve();await flush();
  assert.equal(world.destroyCount,1);assert.deepEqual(h.errors,[],'stale startup must not dereference the cleared renderer');assert.equal(h.nodes.get('error').hidden,true);
});

test('a persisted pageshow restores an interior destroyed for the back-forward cache',async()=>{
  const h=await interior();h.fire(h.window,'pagehide',{persisted:true});h.fire(h.window,'pageshow',{persisted:true});await flush();
  assert.equal(h.worlds.length,2,'returning from browser history restores the visible interior');h.worlds[1].resolve();await flush();assert.equal(h.worlds[1].paused,false);assert.deepEqual(h.errors,[]);
});

test('changing careers clears held pad movement before the new room becomes active',async()=>{
  const h=await interior(),world=h.worlds[0],right=h.pad.find(b=>b.dataset.x==='1');
  h.fire(right,'pointerdown',{pointerId:7});h.click('next');await flush();
  assert.deepEqual(world.movement,{x:0,y:0},'a carried pointer press must not walk the next career automatically');
});

test('Vietnamese search is case-insensitive including uppercase Đ',async()=>{
  const h=harness();await flush();h.search('giao vien');assert.equal(h.nodes.get('card-teacher').hidden,false);
  h.search('duong sat');assert.equal(h.nodes.get('card-railway').hidden,false,'uppercase Đ in a career title folds to d');
  h.search('ĐƯỜNG SẮT');assert.equal(h.nodes.get('card-railway').hidden,false);
  h.search('');assert.equal(h.nodes.get('count').textContent,'50 / 50 nghề');
});

test('catalogue failures show an accessible error without creating a renderer',async()=>{
  const h=harness({responseOK:false});await flush();assert.equal(h.nodes.get('error').hidden,false);assert.equal(h.worlds.length,0);assert.equal(h.requests.length,1);
});

test('a deep link opens its exact profession and interior without game account state',async()=>{
  const h=harness({hash:'#pharmacy/inside'});await flush();assert.equal(h.nodes.get('career').value,'pharmacy');assert.equal(h.worlds.length,1);
  h.worlds[0].resolve();await flush();assert.equal(h.worlds[0].state.current,'pharmacy');assert.equal(h.nodes.get('interior').hidden,false);assert.deepEqual(h.forbidden,[]);
  const unknown=harness({hash:'#unreleased/inside'});await flush();assert.equal(unknown.worlds.length,0);assert.equal(unknown.nodes.get('viewer').hidden,true);assert.deepEqual(unknown.errors,[]);
});
