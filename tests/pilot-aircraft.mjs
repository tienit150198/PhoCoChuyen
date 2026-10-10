import test from 'node:test';
import assert from 'node:assert/strict';
import {chaseCamera,drawAircraft} from '../public/js/careers/pilot_aircraft.js';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('flight retains fullscreen after dialog rerenders and releases it for another sheet',()=>{
  const source=readFileSync(new URL('../public/js/careers/pilot_fly.js',import.meta.url),'utf8');
  const body=source.slice(source.indexOf('function syncVisibility(){'),source.indexOf('export function close(){'));
  let here=true;const classes=new Set(),F={el:{isConnected:true},keys:new Set(),input:{},host:{classList:{toggle(name,on){on?classes.add(name):classes.delete(name);}}}};
  const context=vm.createContext({F,document:{querySelector:()=>here?{}:null},activityVisible:()=>here&&F.el.isConnected,requestAnimationFrame:()=>1,cancelAnimationFrame(){},frame(){}});
  vm.runInContext(body+';globalThis.refresh=syncVisibility;',context);
  context.refresh();assert.ok(classes.has('pl-expanded-host'));assert.equal(F.el.hidden,false);
  classes.clear();context.refresh();assert.ok(classes.has('pl-expanded-host'),'normal sheet render removed class');
  here=false;context.refresh();assert.equal(F.el.hidden,true);assert.equal(classes.has('pl-expanded-host'),false);
  here=true;context.refresh();assert.equal(F.hidden,false);assert.ok(classes.has('pl-expanded-host'));
  F.el.isConnected=false;context.refresh();assert.equal(classes.has('pl-expanded-host'),false);
});

test('outside camera tracks true position and keeps aircraft anchored across viewport sizes',()=>{
  for(const [w,h] of [[390,397],[1280,461],[820,600]])for(const psi of [0,Math.PI/2,Math.PI,-Math.PI/2]){
    const state={x:200,z:400,h:250,psi,th:.1},copy={...state},f=Math.max(w,h*1.25)*1.1,c=chaseCamera(state,{w,h},f);
    const dx=state.x-c.x,dz=state.z-c.z,dy=state.h-c.y,z1=dx*Math.sin(psi)+dz*Math.cos(psi);
    const py=dy*Math.cos(c.pitch)-z1*Math.sin(c.pitch),pz=dy*Math.sin(c.pitch)+z1*Math.cos(c.pitch);
    assert.ok(Math.abs(h*.42-f*py/pz-h*.66)<1e-6);
    assert.deepEqual(state,copy,'camera must never alter flight simulation');
  }
});
test('airport roofs and sides follow the active eye rather than the aircraft position',()=>{
  const source=readFileSync(new URL('../public/js/careers/pilot_fly.js',import.meta.url),'utf8');
  const fn=source.slice(source.indexOf('function boxes(c,sc){'),source.indexOf('function shadeOf('));
  const C={x:-10,z:-20,y:160},draws=[],context=vm.createContext({C,S:{x:30,z:40,h:0},EYE:3.2,NEAR:.6,P3:[0,0,100],cam(){},shadeOf:c=>c,polygon:(c,p,col)=>draws.push({p,col})});
  vm.runInContext(fn+';globalThis.draw=boxes;',context);
  context.draw({}, {night:false,boxes:[{x:0,z:0,w:10,d:20,h:15,col:'wall',roof:'roof'}]});
  assert.equal(draws.length,3);assert.equal(draws[0].p[0][0],-5);assert.equal(draws[1].p[0][2],-10);assert.equal(draws[2].col,'roof');
  C.y=3;draws.length=0;context.draw({}, {night:false,boxes:[{x:0,z:0,w:10,d:20,h:15,col:'wall',roof:'roof'}]});assert.equal(draws.length,2);
});
test('aircraft drawing is finite across ground, bank, altitude and portrait sizes',()=>{
  const c=new Proxy({createLinearGradient:()=>({addColorStop(){}})}, {get:(t,k)=>t[k]||((...args)=>{args.forEach(n=>{if(typeof n==='number')assert.ok(Number.isFinite(n));});}),set:()=>true});
  for(const h of [0,30,1000])for(const ph of [-.6,0,.6])drawAircraft(c,{w:390,h:400},{h,ph,ground:h===0,gear:h<100},2);
});
