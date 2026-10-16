// 🔨 Biển đẹp and 🏎️ limited editions in the old interface, rendered from a real save (tests/test_vehicle_plates.py
// writes it with game/garage.py, game/auction.py and runs `node tests/vehicle-ui.mjs <fixture.json>`):
// the garage (gold plate on its vehicle, the "+x % lợi nhuận mỗi ca" line, the plates list, attach / move / take off,
// no sell for a limited edition, its own paints only on it, never in the shop tabs), the auction's art for the new kinds
// and ride.js carrying the gold plate to the live strolls.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const fx=JSON.parse(readFileSync(process.argv[2],'utf8'));
const store=new Map(),noop=()=>{};
globalThis.localStorage={getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)};
const root={innerHTML:''},body={scrollTop:0,scrollTo:noop};
const dlg={open:false,listeners:{},setAttribute:noop,addEventListener(t,f){this.listeners[t]=f;},showModal(){this.open=true;},close(){this.open=false;},
  querySelector:s=>s==='.gr-root'?root:s==='.gr-body'?body:null,contains:()=>true};
globalThis.document={querySelector:()=>({}),createElement:t=>t==='dialog'?dlg:{width:0,height:0,getContext:()=>new Proxy({},{get:()=>noop})},
  body:{append:noop},head:{append:noop},getElementById:()=>null};
globalThis.Path2D=class{constructor(){return new Proxy({},{get:()=>noop});}};

const G=await import('../public/js/v4/garage.js');
const D=await import('../public/js/v4/auction-display.js');
const R=await import('../public/js/v4/ride.js');

const calls=[];
const state={journey:fx.journey},content={journey:{garage:fx.garage}};
const env={api:{state,content,addEventListener:noop,command:async(a,p)=>{calls.push([a,p]);return {message:'Đã gắn.'};}},closeSheet:noop,confirmAction:async()=>true};
const tick=()=>new Promise(r=>setTimeout(r,0));
const click=async data=>{dlg.listeners.click({target:{closest:()=>({dataset:data,disabled:false})},preventDefault:noop});await tick();await tick();};
const html=()=>root.innerHTML;

await G.openGarage(env,'mine');
let h=html();
// the ridden limited edition with its gold plate and its bonus
assert.match(h,/gr-plate uq">29A-888\.88</,'the gold plate on its vehicle');
assert.match(h,/💰 Biển đẹp: lợi nhuận mỗi ca \+8%/,'the bonus of the vehicle ridden');
assert.match(h,/gr-bonus/);assert.match(h,/tối đa 2\.000 xu một ca/);
assert.match(h,/🏎️ Bản giới hạn 01\/01|🛞 Đang đi/);
assert.match(h,/Bản giới hạn của Nhà đấu giá · không bán lại/,'no sell button for a limited edition');
assert.equal((h.match(/data-gr="sell" data-id="lx_sieu_xe_01"/g)||[]).length,0);
assert.match(h,/data-gr="sell" data-id="o_to_suv"/,'an ordinary car still sells');
assert.match(h,/🔨 Biển đẹp của bạn/);assert.match(h,/đang cất/,'a plate in its box');
assert.match(h,/khi đi chiếc này/,'a plated vehicle not ridden says when it pays');
assert.doesNotMatch(h,/data-gr="plates" data-id="xe_dap"/,'a pedal bike takes no plate');
assert.match(h,/data-gr="plates" data-id="o_to_suv"/);
assert.doesNotMatch(h,/data-gr="plates" data-id="du_thuyen"/,'no yacht name won: no plate button on the yacht');
// attach a plate to the SUV
await click({gr:'plates',id:'o_to_suv'});
h=html();
assert.match(h,/🔨 Gắn biển · /);assert.match(h,/Gắn lên/);assert.match(h,/Đang trên|Đang cất|Đang gắn/);
assert.match(h,/Xe máy 3–5%, ô tô 4–7%, du thuyền 5–8%, máy bay 5–9%; bản giới hạn \+1%, tối đa 10%/,'the table, from the catalogue');
await click({gr:'attach',item:'pl_30k66666',id:'o_to_suv'});
assert.deepEqual(calls.at(-1),['jr_garage_plate',{item:'pl_30k66666',id:'o_to_suv'}]);
await click({gr:'attach',item:'pl_29a88888'});
assert.deepEqual(calls.at(-1),['jr_garage_plate',{item:'pl_29a88888',id:null}],'take off');
// paints: the special ones only on a limited edition; the shop tabs never list one
await click({gr:'back'});await click({gr:'edit',id:'o_to_suv'});
assert.doesNotMatch(html(),/data-color="vang_kim"/);
await click({gr:'back'});await click({gr:'edit',id:'lx_sieu_xe_01'});
assert.match(html(),/data-color="vang_kim"/);assert.match(html(),/Đang gắn biển đấu giá/);
await click({gr:'back'});await click({gr:'tab',tab:'car'});
assert.doesNotMatch(html(),/lx_sieu_xe_01/,'not in the showroom');
assert.match(html(),/data-id="sieu_xe"/);
// the auction's art for the new kinds
const it=id=>fx.auction.items.find(x=>x.id===id);
const art=(id,extra={})=>D.itemArt({...it(id),item:id,data:{...it(id),...extra}});
assert.match(art('lx_sieu_xe_01'),/au-ltd/);assert.match(art('lx_sieu_xe_01'),/--au-paint:#d4a838/);assert.match(art('lx_sieu_xe_01'),/BẢN GIỚI HẠN · 01\/01/);
assert.match(art('rg_vna888'),/SỐ ĐĂNG KÝ TÀU BAY/);assert.match(art('rg_vna888'),/VN-A888/);
assert.match(art('hn_hoang_hon'),/BIỂN TÊN DU THUYỀN/);
assert.match(D.collectionGallery(fx.journey.uniq.own,fx.auction),/Tia Chớp Vàng Kim số 01/,'the gallery shows both blocks');
assert.match(D.itemArt({kind:'art',id:'x',item:'x'}),/au-painting/,'the old kinds unchanged');
// ride.js: the gold plate travels with the ridden vehicle, a free name plate stays home
store.clear();
const v=R.choice(state,content);
assert.equal(v.id,'lx_sieu_xe_01');assert.equal(v.plate,'29A-888.88');assert.equal(v.uq,true);assert.equal(v.kind,'super');
assert.deepEqual(R.wire(v),{v:'lx_sieu_xe_01',c:'vang_kim',p:'29A-888.88'});
const free=R.options(state,content).find(x=>x.id==='o_to_suv');
assert.equal(free.uq,undefined);assert.equal('p' in R.wire(free),false,'a free biển tên never travels');
assert.equal(R.fromWire({v:'xe_ga',c:'hong',p:'30K-666.66'},content).uq,true);
assert.equal(R.fromWire({v:'xe_ga',c:'hong',p:'a\u0001b'},content).plate,'');
// an older server (no `plates`): the dearest won plate still shows on the vehicle ridden
const older={journey:{...fx.journey,garage:{...fx.journey.garage,plates:undefined,cars:fx.journey.garage.cars.map(c=>({...c,uq:undefined}))}}};
delete older.journey.garage.plates;
assert.equal(R.choice(older,content).plate,'29A-888.88');
console.log('vehicle-ui ok');
