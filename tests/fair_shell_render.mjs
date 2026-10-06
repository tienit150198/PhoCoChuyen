import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const src=readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8');
const a=src.indexOf('function renderMain(){'),b=src.indexOf('/* Toasts',a);
let covered=true,worldUpdates=0,domUpdates=0,latest=null,onClose;
const api={state:{settings:{},seq:0},content:{}};
const element={classList:{toggle(){}},textContent:''};
const context=vm.createContext({api,mainDeferred:false,document:{body:element,querySelector:()=>covered?{open:true}:null,addEventListener(type,fn,capture){assert.equal(type,'close');assert.equal(capture,true);onClose=fn;}},$:()=>element,room:()=>({life:{},day:75}),meta:()=>({}),shell:{career(){},mark(){return '';}},setHTML(){domUpdates++;},hudHTML(){},railHTML(){},esc:x=>x,careerSwitchButton(){},taskCards(){},dockHTML(){},layout:()=> 'phone',hudFeedback(){},stepHint(){},sound:{configure(){}},world:{update(state){worldUpdates++;latest=state.seq;}}});
// The shared workspace may also host a separate renderer integration.
context.env=()=>({api});context.updateIsometricShell=()=>{};context.iso={booted:()=>false};   // the 2.5D HUD is not up in this slice
vm.runInContext(src.slice(a,b),context);
for(let i=1;i<=50;i++){api.state={...api.state,seq:i};vm.runInContext('renderMain()',context);}
assert.equal(worldUpdates,0,'confirmed fair states must not repeatedly rebuild/repaint the obscured workplace');
assert.equal(domUpdates,0,'the obscured career DOM does not contend with the minigame canvas');
onClose();assert.equal(worldUpdates,0,'closing an inner dialog cannot resume the obscured workplace');
covered=false;onClose();
assert.equal(worldUpdates,1);assert.equal(latest,50,'closing paints the latest authoritative state once');
assert.equal(context.mainDeferred,false,'flushing clears the pending update');
onClose();assert.equal(worldUpdates,1,'unrelated close events do not repaint after the flush');
console.log('Fair shell: 50 background updates coalesce into one current-state paint after closing.');
