import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';

const source=readFileSync(new URL('../public/js/v4/fair-scratch.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace(/export /g,'');
function fixture(){
  const stats={paints:0,bindings:0},noop=()=>{};
  const context=new Proxy({createLinearGradient:()=>({addColorStop:noop}),fillRect:()=>stats.paints++},{get:(o,k)=>o[k]||noop});
  let box={width:0,height:0};
  const cv={getBoundingClientRect:()=>box,getContext:()=>context,addEventListener:()=>stats.bindings++};
  const S={dlg:{open:false,querySelector:()=>cv}};
  const ui=new Function('tr',source+';return setup;')(s=>s)({S,F:()=>({scratch:{}}),render:noop,sfx:noop,pick:a=>a[0],reduce:()=>true});
  S.xs.t={id:42,prize:10};
  return {S,ui,cv,stats,size:(width,height)=>{box={width,height};}};
}

test('late paid ticket mounts once only when the dialog reopens with dimensions',()=>{
  const f=fixture();f.ui.mount();
  assert.equal(f.cv._xs,undefined);assert.equal(f.stats.paints,0);assert.equal(f.stats.bindings,0);
  assert.equal(f.S.xs.t.id,42);assert.equal(f.ui.hold(),10);
  f.S.dlg.open=true;f.size(314,256);f.ui.mount();
  assert.equal(f.cv._xs,1);assert.equal(f.cv._w,314);assert.equal(f.cv._h,256);
  assert.equal(f.stats.bindings,5);
  const painted=f.stats.paints;
  f.ui.mount();f.S.dlg.open=false;f.ui.mount();f.S.dlg.open=true;f.ui.mount();
  assert.equal(f.stats.paints,painted);assert.equal(f.stats.bindings,5);
});

test('zero-size open canvas remains eligible for a later successful mount',()=>{
  const f=fixture();f.S.dlg.open=true;f.ui.mount();
  assert.equal(f.cv._xs,undefined);assert.equal(f.stats.bindings,0);
  f.size(0,256);f.ui.mount();assert.equal(f.cv._xs,undefined);
  f.size(314,256);f.ui.mount();assert.equal(f.cv._w,314);assert.equal(f.stats.bindings,5);
});
