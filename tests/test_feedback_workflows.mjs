import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import cafe from '../public/js/careers/cafe_bakery.js';
import * as careers from '../public/js/v4/careers.js';
import {inventoryView,v4Action} from '../public/js/v4/views.js';
import {operationsView} from '../public/js/operations-ui.js';

const {cafe:coffee,clothing,tea,content}=JSON.parse(readFileSync(0,'utf8'));
const x=careers.careerContext({api:{state:coffee,content},ui:{}});
assert.match(cafe.job(x.room.tasks[0],x),/4×/);
assert.equal(typeof careers.careerSwitchButton,'function','career change has an obvious visible control');
assert.match(careers.careerSwitchButton(),/data-action="home"/);
assert.match(careers.careerSwitchButton(),/Đổi nghề/);

const element=dataset=>({dataset,flags:{},classList:{toggle(k,v){this.owner.flags[k]=v;}},closest:()=>null,
  label:{textContent:''},querySelector(sel){return sel==='.cb-meter-label'?this.label:this;}});
const steam=element({steamStart:'1000'}),oven=element({ovenStart:'1000',shift:'3',pace:'4',w:'8,12,16'});
for(const e of [steam,oven])e.classList.owner=e;
const scope={closest:()=>null,querySelectorAll:sel=>sel==='[data-steam-start]'?[steam]:sel==='[data-oven-start]'?[oven]:[]};
const motion=[];x.slide=(el,p,rate)=>motion.push({el,p,rate});
x.now=()=>1000+(54.96-5)/4.2;x.room.data.bar_pace=1;
cafe.meters(scope,x);
assert.equal(steam.flags.ready,true,'55.0°C rounds into the silky band, as the server grades it');
assert.match(steam.label.textContent,/TẮT VÒI/);
x.now=()=>1001.5;motion.length=0;cafe.meters(scope,x);
assert.equal(oven.flags.ready,true,'oven at4× reaches9 effective seconds including the hot-oven offset');
assert.equal(motion.at(-1).rate,4/22*100);

globalThis.document={addEventListener(){},getElementById(){return null;},querySelector(){return {};}};
globalThis.window={addEventListener(){}};
const ui={view:'inventory',orderItem:'tee',orderSize:{tee:'XL'}};
const sent=[];const env={api:{state:clothing,content},ui,renderSheet(){},openSheet(){},
  confirmAction:async()=>true,cmd:async(op,p)=>{sent.push([op,p]);return {message:'ok'};}};
const stock=inventoryView(env);
assert.match(stock,/Chọn size nhập/);
assert.match(stock,/data-action="v4OrderSize"[^>]*data-size="XL"/);
await v4Action('v4OrderGo',{item:'tee'},null,env);
assert.equal(sent[0][1].size,'XL','direct order carries the selected size');
ui.orderItem='tee';await v4Action('v4CartAdd',{item:'tee'},null,env);
assert.equal(sent[1][1].size,'XL','draft line carries the selected size');
const c=tea.careers.milk_tea;
const staff=operationsView('milk_tea',c,content.operations,{},tea);
assert.match(staff,/tự tay pha/);
assert.match(staff,/Quầy của bạn/);
assert.match(staff,/khép ca/);
console.log('Feedback work controls and meter boundaries passed.');
