// Headless check of the shop scene's navigation model (no browser needed).
// For every career × composition (phone portrait, desktop landscape) × a set
// of scene variants (customers, event, officer, staff, lease tier, decor):
//   • people stand on the floor, not in furniture, and don't overlap;
//   • every hotspot has a reachable approach spot on free floor;
//   • random taps anywhere give paths whose every few pixels are free floor
//     (no walking through counters/tables/people, no corner cutting) or
//     no walk at all when the tap is far from the floor;
//   • keyboard walking never enters a footprint;
//   • drawing the scene throws nothing.
// Usage: node scripts/check_nav.mjs [--seed N] [--verbose]
import {readdirSync} from 'node:fs';

const noop=()=>{};
const ctx2d=()=>new Proxy({measureText:s=>({width:String(s).length*7}),createRadialGradient:()=>({addColorStop:noop}),createLinearGradient:()=>({addColorStop:noop}),getImageData:()=>({data:[]})},{get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>{t[k]=v;return true;}});
globalThis.ResizeObserver=class{observe(){}disconnect(){}};
globalThis.requestAnimationFrame=()=>0;globalThis.cancelAnimationFrame=noop;
globalThis.devicePixelRatio=1;globalThis.location={search:''};
globalThis.document={hidden:false,createElement:()=>({getContext:ctx2d,toDataURL:()=>'data:,'})};
const {BobaWorld}=await import('../public/js/boba-world.js');
// Scene kinds load lazily in the browser; load them all so each career is checked in its own place.
await (await import('../public/js/scenes/index.js')).loadAllScenes();

const args=process.argv.slice(2),verbose=args.includes('--verbose');
let seed=Number(args[args.indexOf('--seed')+1])||20260928;
const rand=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
const pick=a=>a[Math.floor(rand()*a.length)];

const careers=[...new Set(['mother_baby','pharmacy','accounting','customer_care','teacher','tour_guide','milk_tea',
  ...readdirSync(new URL('../public/js/careers/',import.meta.url)).filter(f=>f.endsWith('.js')&&!f.endsWith('_kit.js')).map(f=>f.slice(0,-3))])];
const VIEWS={phone:{width:390,height:700},desktop:{width:1300,height:820}};
const SPOTS=['window','corner','front','center'];

function canvas(size){return {getContext:ctx2d,addEventListener:noop,focus:noop,style:{},width:0,height:0,getBoundingClientRect:()=>({left:0,top:0,...size})};}
function careerState(v){
  const tasks=Array.from({length:v.customers},(_,i)=>({id:'t'+i,npc:'npc_0'+(i+1),status:'new'}));
  const staff=Array.from({length:v.staff},(_,i)=>({id:'e'+i,name:'Bạn '+i,status:'hired',on_shift:v.working,rest_until:0,avatar:i,color:'#aacabb'}));
  const decor={};for(const [id,spot] of Object.entries(v.decor))decor[id]={spot};
  return {open:v.open,turn:3,day:2,tasks,active_task:tasks[0]?.id,upgrades:[...Object.keys(decor),...(v.assistant?['assistant']:[]),...(v.shelf?['shelf']:[])],decor,
    event:v.event?{npc:'npc_09',stage:'open',title:'x'}:null,life:{},
    ops:{property:{tier:v.tier},staff,security:{items:['camera','bell','light','lock'],current_case:v.officer?{status:'reported'}:null},equipment:{condition:v.worn?80:100}}};
}
function variants(){
  const out=[{customers:0,staff:0,tier:'cozy',decor:{},open:false},{customers:4,staff:4,working:true,tier:'garden',decor:{plant:'window',lamp:'corner',seat:'front',rug:'center',poster:'wall'},event:true,officer:true,open:true,shelf:true,worn:true},
    {customers:4,staff:4,working:false,tier:'garden',decor:{plant:'corner',lamp:'front',seat:'center'},event:true,officer:true,open:true}];
  for(let i=0;i<14;i++){const decor={};for(const id of ['plant','lamp','seat','rug'])if(rand()<.6)decor[id]=pick(SPOTS);if(rand()<.5)decor.poster='wall';
    out.push({customers:Math.floor(rand()*5),staff:Math.floor(rand()*5),working:rand()<.6,tier:pick(['cozy','sunny','garden']),decor,event:rand()<.5,officer:rand()<.4,open:rand()<.8,assistant:rand()<.3,shelf:rand()<.4,worn:rand()<.3});}
  return out;
}

const problems=[];let checks=0;
const fail=(where,msg)=>{problems.push(`${where}: ${msg}`);};
for(const [vname,size] of Object.entries(VIEWS))for(const career of careers){
  const w=new BobaWorld(canvas(size),noop);w.resize();
  variants().forEach((v,vi)=>{
    const where=`${vname}/${career}/v${vi}`;
    const state={current:career,careers:{[career]:careerState(v)},settings:{reduceMotion:false},journey:{gender:pick(['male','female',null])}};
    try{w.update(state,{npcs:[],catalogue:[]});}catch(e){fail(where,'update threw '+e.stack);return;}
    const m=w.navMetric(),px=(a,b)=>Math.hypot((a.x-b.x)*m.kx,(a.y-b.y)*m.ky),g=w.nav;
    // People: on the floor and apart. Sway is part of their footprint.
    for(const q of w.people){checks++;if(w.navStaticBlocked(q.x,q.y))fail(where,`${q.id} stands inside furniture or off the floor`);}
    for(let i=0;i<w.people.length;i++)for(let j=i+1;j<w.people.length;j++){const a=w.people[i],b=w.people[j],sa=w.project(a.x,a.y),sb=w.project(b.x,b.y);checks++;
      const rx=Math.max(a.rx,b.rx),dx=(sa.x-sb.x)/rx,dy=(sa.y-sb.y)/15;if(dx*dx+dy*dy<1)fail(where,`${a.id} overlaps ${b.id}`);}
    // Home and hotspots.
    const home=w.navHome(),hk=w.navNearest(home.x,home.y),region=g.comp[hk];
    checks++;if(!w.navFree(home.x,home.y))fail(where,'home spot is blocked');
    for(const h of w.hotspots){checks++;const ok=(h.approach||[]).filter(a=>w.navFree(a.x,a.y)&&g.comp[w.navNearest(a.x,a.y)]===region&&px(w.navPoint(w.navNearest(a.x,a.y)),a)<14);
      if(!ok.length)fail(where,`${h.id} has no reachable approach spot`);}
    // Random taps from random walkable starts.
    const cells=[...g.walk.keys()].filter(k=>g.walk[k]&&g.comp[k]===region);
    for(let n=0;n<(vi<3?90:30);n++){
      const s=w.navPoint(pick(cells));Object.assign(w.player,{x:s.x,y:s.y,path:[],goal:null});
      const frame=w.isPortrait()?{w:700,h:890}:{w:1200,h:790},t=w.unproject(rand()*frame.w*1.2-frame.w*.1,rand()*frame.h*1.2-frame.h*.1);
      const path=w.navPath(t.x,t.y);checks++;
      if(!path){const near=w.navNearest(t.x,t.y,region,150);if(near>=0)fail(where,`tap near floor gave no path (${t.x.toFixed(2)},${t.y.toFixed(2)})`);continue;}
      let a={x:s.x,y:s.y};
      for(const b of path){const steps=Math.max(1,Math.ceil(px(a,b)/1.5));for(let i=1;i<=steps;i++){const x=a.x+(b.x-a.x)*i/steps,y=a.y+(b.y-a.y)*i/steps;if(!w.navFree(x,y)){fail(where,`path crosses a blocked point at ${JSON.stringify(w.project(x,y))}`);i=steps;n=1e9;}}a=b;}
      const end=path.at(-1)||s;if(!w.navFree(end.x,end.y))fail(where,'path ends on a blocked point');
    }
    // Keyboard walking with wall sliding.
    const s=w.navPoint(pick(cells));Object.assign(w.player,{x:s.x,y:s.y,path:[],goal:null});
    for(let n=0;n<400;n++){const dx=pick([-1,0,1]),dy=pick([-1,0,1]);for(let k=0;k<6;k++)w.keyMove(dx,dy,1/30,230);checks++;if(!w.navFree(w.player.x,w.player.y)){fail(where,'keyboard walked into a footprint');break;}}
    // Rendering all layers must not throw.
    try{Object.assign(w.player,{path:[{x:w.player.x+.3,y:w.player.y}]});w.time=3;w.draw();w.navDebug=true;w.draw();w.navDebug=false;}catch(e){fail(where,'draw threw '+e.stack.split('\n').slice(0,3).join(' | '));}
  });
  w.destroy();
}
const unique=[...new Set(problems)];
if(verbose||unique.length)for(const p of unique.slice(0,60))console.log('✗',p);
console.log(`${careers.length} careers × 2 compositions: ${checks} checks, ${unique.length} problems`);
process.exit(unique.length?1:0);
