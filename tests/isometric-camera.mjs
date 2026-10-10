import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as townUtilities from '../public/js/isometric/town-utilities.js';

const source=readFileSync(new URL('../public/js/isometric-shell.js',import.meta.url),'utf8')
  .replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'')
  .replace("import('./v4/live.js')",'Promise.resolve(liveModule)');
const listeners=new Map(),calls=[],observers=[];
let modalOpen=false;
const toggle={setAttribute:(...a)=>calls.push(a),focus:()=>calls.push(['focus'])};
const cameraOptions={hidden:true};
const camera={classList:{remove:c=>calls.push(['remove',c])},querySelector:s=>s==='.iso-camera-options'?cameraOptions:toggle};
const disclosures=Object.fromEntries(['iso-tools','iso-mission','iso-outings'].map(name=>{
  const summary={dataset:{isoFocus:name},focus:()=>calls.push(['focus',name])};
  const node={open:false,querySelector:s=>s==='summary'?summary:null,matches:s=>s.split(',').some(part=>part.trim()==='.'+name),contains:target=>target===node||target===summary||target?.owner===node};
  return [name,node];
}));
const find=s=>{
  for(const [name,node] of Object.entries(disclosures))if(s===`#isoHUD .${name}`||s===`#isoHUD .${name}[open]`)return !s.endsWith('[open]')||node.open?node:null;
  return s==='dialog[open]'?(modalOpen?{}:null):s.endsWith('.iso-camera')?camera:s.includes('isoCamera')?toggle:null;
};
const root={dataset:{},classList:{contains:()=>false}};
const hud={dataset:{}};
const context=vm.createContext({
  ...townUtilities,
  liveModule:{live:{on(){}},liveBoot(){}},Promise,hudMoney:()=>({}),
  document:{documentElement:root,body:{classList:{add(){}}},getElementById:id=>id==='isoHUD'?hud:null,querySelector:find},
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
const tools=disclosures['iso-tools'],mission=disclosures['iso-mission'],outings=disclosures['iso-outings'];
calls.length=0;tools.open=true;listener.fn(event);
assert.equal(tools.open,false,'Escape closes utilities before the pause shortcut');
assert.ok(calls.some(c=>c[0]==='prevent'));
assert.ok(calls.some(c=>c[0]==='focus'&&c[1]==='iso-tools'),'Escape restores the utilities summary focus');
calls.length=0;tools.open=true;outings.open=true;listener.fn(event);
assert.equal(outings.open,false,'Escape closes the nested outings disclosure first');
assert.equal(tools.open,true,'the parent utilities remain open for another selection');
assert.ok(calls.some(c=>c[0]==='focus'&&c[1]==='iso-outings'));
listener.fn(event);assert.equal(tools.open,false);
mission.open=true;listener.fn(event);assert.equal(mission.open,false,'Escape also owns the task chip');
tools.open=true;listeners.get('pointerdown').fn({target:{closest:()=>null}});
assert.equal(tools.open,false,'an outside pointer closes utilities');
tools.open=true;listeners.get('pointerdown').fn({target:{owner:tools,closest:()=>null}});
assert.equal(tools.open,true,'pointerdown inside utilities preserves the clicked action until click');
const settings={dataset:{action:'settings'},owner:tools,closest:s=>s==='[data-action]'?settings:s==='.iso-tools'?tools:null};
listeners.get('click').fn({target:settings});
assert.equal(tools.open,false,'selecting an existing app action closes utilities without intercepting its route');
tools.open=true;modalObserver.fn([{target:{tagName:'DIALOG',open:true}}]);
assert.equal(tools.open,false,'dialog activation closes the background tools disclosure');
tools.open=true;mission.open=true;listeners.get('mnl:iso-mode').fn();
assert.equal(tools.open,false);assert.equal(mission.open,false,'scene changes reset all HUD disclosures');
tools.open=true;context.openCamera();listeners.get('toggle').fn({target:tools});
assert.equal(context.cameraIsOpen(),false,'opening utilities closes the camera to keep only one overlay');
mission.open=true;listeners.get('toggle').fn({target:mission});
assert.equal(tools.open,false,'opening task details closes utilities');
mission.open=false;tools.open=true;listeners.get('focusin').fn({target:{closest:()=>null}});
assert.equal(tools.open,false,'tabbing away dismisses utilities without trapping keyboard focus');
assert.equal(cameraOptions.hidden,true,'camera options are removed from keyboard navigation on close');

// Safari 15 has no :has(). Open overlays must still rise above the independent work HUD,
// and must relinquish that layer on every dismissal, rather than raising the HUD permanently.
tools.open=true;listeners.get('toggle').fn({target:tools});
assert.equal(hud.dataset.disclosureOpen,'true','native utilities open gives the HUD a compatible elevated-state marker');
outings.open=true;listeners.get('toggle').fn({target:outings});
listener.fn(event);
assert.equal(hud.dataset.disclosureOpen,'true','closing a nested outing keeps its open parent above task cards');
tools.open=false;listeners.get('toggle').fn({target:tools});
assert.equal(hud.dataset.disclosureOpen,'false','closing the native summary removes HUD elevation');
const localOnly={api:{},act:()=>assert.fail('disclosure state must not send an application action')};
await context.isometricAction('isoCamera',{},null,localOnly);
assert.equal(hud.dataset.disclosureOpen,'true','opening camera controls uses the same compatible layer');
listeners.get('pointerdown').fn({target:{closest:()=>null}});
assert.equal(hud.dataset.disclosureOpen,'false','outside dismissal removes camera elevation immediately');
mission.open=true;listeners.get('toggle').fn({target:mission});
assert.equal(hud.dataset.disclosureOpen,'true','expanded task details are also elevated');
listener.fn(event);
assert.equal(hud.dataset.disclosureOpen,'false','Escape restores the normal HUD layer');
tools.open=true;listeners.get('toggle').fn({target:tools});
modalOpen=true;modalObserver.fn([{target:{tagName:'DIALOG',open:true}}]);
assert.equal(hud.dataset.disclosureOpen,'false','dialog opening resets the background HUD layer');
modalOpen=false;tools.open=true;listeners.get('toggle').fn({target:tools});
listeners.get('mnl:iso-mode').fn();
assert.equal(hud.dataset.disclosureOpen,'false','scene changes cannot leave the whole HUD raised');
const css=readFileSync(new URL('../public/css/isometric.css',import.meta.url),'utf8');
assert.match(css,/#isoHUD\[data-disclosure-open="true"\]\s*\{z-index:34;/,'the actual elevated CSS rule accepts the JS state without :has support');
console.log('isometric-camera: disclosure Escape does not pause the game');
