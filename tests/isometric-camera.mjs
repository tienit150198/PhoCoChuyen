import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../public/js/isometric-shell.js',import.meta.url),'utf8')
  .replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'')
  .replace("import('./v4/live.js')",'Promise.resolve(liveModule)');
const listeners=new Map(),calls=[],observers=[];
let modalOpen=false;
const toggle={setAttribute:(...a)=>calls.push(a),focus:()=>calls.push(['focus'])};
const camera={classList:{remove:c=>calls.push(['remove',c])},querySelector:()=>toggle};
const root={dataset:{},classList:{contains:()=>false}};
const context=vm.createContext({
  liveModule:{live:{on(){}},liveBoot(){}},Promise,
  document:{documentElement:root,body:{classList:{add(){}}},getElementById:()=>({}),querySelector:s=>s==='dialog[open]'?(modalOpen?{}:null):s.endsWith('.iso-camera')?camera:s.includes('isoCamera')?toggle:null},
  window:{addEventListener:(type,fn,options)=>listeners.set(type,{fn,options})},MutationObserver:class{constructor(fn){this.fn=fn;}observe(target,options){observers.push({fn:this.fn,options});}},
});
vm.runInContext(source+'\nbootIsometricShell(()=>({api:{}}));globalThis.openCamera=()=>{cameraOpen=true;};globalThis.cameraIsOpen=()=>cameraOpen;',context);
await Promise.resolve();
const listener=listeners.get('keydown');
assert.equal(listener.options,true,'camera Escape runs before the existing game-pause shortcut');
context.openCamera();
const event={key:'Escape',preventDefault:()=>calls.push(['prevent']),stopPropagation:()=>calls.push(['stop'])};
listener.fn(event);
assert.ok(calls.some(c=>c[0]==='stop'),'closing camera must not also pause the game');
assert.ok(calls.some(c=>c[0]==='aria-expanded'&&c[1]==='false'));
assert.ok(calls.some(c=>c[0]==='focus'));
calls.length=0;listener.fn(event);
assert.equal(calls.length,0,'Escape retains the normal game behavior when no HUD disclosure is open');
context.openCamera();modalOpen=true;listener.fn(event);
assert.equal(calls.length,0,'a modal owns Escape even if the background disclosure has not reset yet');
assert.equal(context.cameraIsOpen(),true,'the capture guard does not steal focus from the dialog');
const modalObserver=observers.find(o=>o.options.subtree&&o.options.attributeFilter.includes('open'));
assert.ok(modalObserver,'opening a dialog resets background camera state, including keyboard activation');
modalObserver.fn([{target:{tagName:'DIALOG',open:true}}]);
assert.equal(context.cameraIsOpen(),false);
assert.equal(calls.some(c=>c[0]==='focus'),false,'modal opening does not refocus an inert HUD button');
context.openCamera();modalOpen=false;
listeners.get('mnl:iso-mode').fn();
assert.equal(context.cameraIsOpen(),false,'changing scenes resets camera disclosure state');
console.log('isometric-camera: disclosure Escape does not pause the game');
