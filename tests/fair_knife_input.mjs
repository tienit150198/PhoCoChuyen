import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../public/js/v4/fair-knife.js',import.meta.url),'utf8').replace(/export /g,'');
function fixture(){
 let now=1000;
 const handlers=new Map(),button={disabled:false,addEventListener:(name,fn)=>{const list=handlers.get(name)||[];list.push(fn);handlers.set(name,list);}};
 const cv={isConnected:true,getBoundingClientRect:()=>({width:300}),addEventListener(){}};
 const document={hidden:false,addEventListener(){}};
 const context=vm.createContext({document,performance:{now:()=>now},ResizeObserver:class{observe(){}},setTimeout:()=>1,clearTimeout(){},requestAnimationFrame:()=>1,cancelAnimationFrame(){}});
 const {setup}=vm.runInContext(source+'\n;({setup})',context);
 const k={fly:80,min_tap:120,gap:10,impact:90,level_ms:60000,run:{stage:'play',id:'input-round',lv:1,el:0,tp:[],board:{chance:true,need:11,pre:[],th0:0,segs:[[64000,240,0]]}}};
 const S={tab:'dt',dlg:{open:true,querySelector:sel=>sel==='.fh-kn-cv'?cv:sel==='[data-fh="knthrow"]'?button:null}};
 const ui=setup({S,F:()=>({knife:k,now:0}),serverNow:()=>0,render(){},sfx(){},send(){throw new Error('Early knife throws must not send commands');}});
 ui.mount();ui.mount(); // Rendering the retained button must not duplicate its handlers.
 const dispatch=(type,props={})=>{
  const e={button:0,isPrimary:true,detail:0,pointerType:'',preventDefault(){this.defaultPrevented=true;},stopPropagation(){this.stopped=true;},...props};
  for(const fn of handlers.get(type)||[])fn(e);
  if(type==='click'&&!e.stopped&&!button.disabled)ui.click('knthrow',{}); // Existing fair dialog click delegation.
  return e;
 };
 return {S,button,dispatch,at:t=>{now=1000+t;},count:()=>S.kn.L?.taps.length||0};
}

for(const [pointerType,detail] of [['mouse',1],['touch',0]])test(`${pointerType} launches on press and ignores its delayed compatibility click`,()=>{
 const f=fixture();f.dispatch('pointerdown',{pointerType});assert.equal(f.count(),1,'the knife starts before release');
 f.at(250);const click=f.dispatch('click',{pointerType,detail});assert.equal(f.count(),1,'a hold longer than min_tap is still a single throw');assert.equal(click.stopped,true);
});

test('keyboard and assistive clicks retain normal activation',()=>{
 const f=fixture();f.dispatch('click',{detail:0});assert.equal(f.count(),1);
 f.at(150);f.dispatch('click',{detail:0});assert.equal(f.count(),2);
});

test('disabled, secondary-button, and non-primary pointer presses do not throw',()=>{
 const f=fixture();f.button.disabled=true;f.dispatch('pointerdown',{pointerType:'touch'});assert.equal(f.count(),0);
 f.button.disabled=false;f.dispatch('pointerdown',{button:2,pointerType:'mouse'});f.dispatch('pointerdown',{isPrimary:false,pointerType:'touch'});assert.equal(f.count(),0);
});

test('a too-fast press is ignored without replaying at release and leaves min_tap unchanged',()=>{
 const f=fixture();f.dispatch('pointerdown',{pointerType:'touch'});f.dispatch('click',{pointerType:'touch',detail:0});
 f.at(50);f.dispatch('pointerdown',{pointerType:'touch'});f.at(200);f.dispatch('click',{pointerType:'touch',detail:0});assert.equal(f.count(),1);
 f.at(260);f.dispatch('pointerdown',{pointerType:'touch'});assert.equal(f.count(),2);
 assert.deepEqual(Array.from(f.S.kn.L.taps),[0,260]);
});
