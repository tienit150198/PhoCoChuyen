// Headless check of the walkable trại tạm giữ (public/js/scenes/jail-place.js; v4/jail-map.js), no browser needed.
// For both compositions (landscape, portrait):
//   • the way in (the bunk) and every hotspot's standing point are free floor, every hotspot is reachable from the way
//     in and from every other hotspot, and no path crosses a footprint (the desk, the tree, the bench, the bed, the
//     kiosk, the gate's posts);
//   • every công ích task of game/jail.py has its own place (one place per task, none shared);
//   • hotspots do not overlap (each tap point is closest to its own spot), the camp's strollers walk on free floor;
//   • random taps walk on free floor only; drawing everything (all tasks, none done, all done) throws nothing;
//   • at many screen sizes (old phones to wide desktops, with and without the panel up) standing at any hotspot
//     keeps the player and the hotspot on screen, and the scale is never silly.
// Usage: node tests/jail_place.mjs [--seed N]
import {readFileSync} from 'node:fs';
const noop=()=>{};
const ctx2d=()=>new Proxy({measureText:s=>({width:String(s).length*7}),createRadialGradient:()=>({addColorStop:noop}),createLinearGradient:()=>({addColorStop:noop}),getImageData:()=>({data:[]}),getLineDash:()=>[]},{get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>{t[k]=v;return true;}});
globalThis.document={hidden:false,createElement:()=>({getContext:ctx2d}),documentElement:{lang:'vi'}};
globalThis.location={search:''};
const J=await import('../public/js/scenes/jail-place.js');
const {plan,route,blocked,back,props,marks,bubble,leafAt,frame,portraitFor,VIEW,TASK_SPOT,PLACES,PEOPLE,cap}=J;

const args=process.argv.slice(2);
let seed=Number(args[args.indexOf('--seed')+1])||20261009;
const rand=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
const problems=[];
const along=(pl,path)=>{for(let i=1;i<path.length;i++){const [a,b]=[path[i-1],path[i]],n=Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/3);
  for(let k=0;k<=n;k++){const x=a[0]+(b[0]-a[0])*k/n,y=a[1]+(b[1]-a[1])*k/n;if(blocked(pl,x,y))return [x,y];}}return null;};

// the server's task list (game/jail.py TASKS) has one place each
const py=readFileSync(new URL('../game/jail.py',import.meta.url),'utf8');
const tasks=[...py.slice(py.indexOf('TASKS = {'),py.indexOf('TASK_IDS')).matchAll(/^\s+'([a-z]+)': dict\(/gm)].map(m=>m[1]);
if(tasks.length<5)problems.push(`read only ${tasks.length} tasks from game/jail.py`);
for(const t of tasks)if(!TASK_SPOT[t])problems.push(`task ${t} has no place in the camp`);
if(new Set(Object.values(TASK_SPOT)).size!==Object.keys(TASK_SPOT).length)problems.push('two tasks share a place');
for(const id of Object.values(TASK_SPOT))if(!PLACES[id])problems.push(`place ${id} has no name`);

let paths=0,views=0;
for(const port of [false,true]){
  const pl=plan(port),tag=port?'portrait':'landscape',[v0,w0,v1,w1]=VIEW[port?'port':'land'],f=pl.floor;
  if(f[0]<v0||f[2]>v1||f[1]<w0||f[3]>w1)problems.push(`${tag}: the floor ${f} is outside the view`);
  for(const [from,p] of Object.entries(pl.entry))if(blocked(pl,p[0],p[1]))problems.push(`${tag}: the way in (${from}) is not free floor`);
  for(const kind of ['bunk','guard','visit','gate'])if(!pl.spots.some(s=>s.kind===kind))problems.push(`${tag}: no ${kind}`);
  for(const t of tasks)if(!pl.spots.some(s=>s.kind==='task'&&s.task===t))problems.push(`${tag}: no spot for ${t}`);
  for(const s of pl.spots){
    if(blocked(pl,s.stand[0],s.stand[1])){problems.push(`${tag}: ${s.id} stands on a footprint ${s.stand}`);continue;}
    for(const p of [pl.entry.bunk,...pl.spots.map(q=>q.stand)]){const r=route(pl,p,s.stand);paths++;
      if(!r){problems.push(`${tag}: ${s.id} unreachable from ${p}`);continue;}
      const end=r[r.length-1];if(Math.hypot(end[0]-s.stand[0],end[1]-s.stand[1])>1)problems.push(`${tag}: ${s.id} path ends off its spot`);
      const bad=along(pl,r);if(bad)problems.push(`${tag}: path ${p}→${s.id} crosses a footprint at ${bad.map(Math.round)}`);}
    const [x,y]=s.hit;if(x<v0||x>v1||y<w0||y>w1)problems.push(`${tag}: ${s.id} hit ${s.hit} is outside the view`);
    if(s.mark&&(s.mark[0]<v0||s.mark[0]>v1||s.mark[1]-20<w0))problems.push(`${tag}: ${s.id} badge ${s.mark} is cut off`);
    if(s.r<36)problems.push(`${tag}: ${s.id} is too small to tap (${s.r})`);
  }
  // a tap on a spot's own point picks that spot
  for(const s of pl.spots){let best=null,bd=Infinity;for(const t of pl.spots){const d=Math.hypot(t.hit[0]-s.hit[0],t.hit[1]-s.hit[1]);if(d<=t.r&&d<bd){bd=d;best=t;}}
    if(best!==s)problems.push(`${tag}: a tap on ${s.id} picks ${best?.id}`);}
  for(const s of pl.spots)for(const t of pl.spots)if(s!==t&&Math.hypot(s.stand[0]-t.stand[0],s.stand[1]-t.stand[1])<30)problems.push(`${tag}: ${s.id} and ${t.id} stand on the same place`);
  for(const w of pl.walkers){
    if(!PEOPLE[w.who])problems.push(`${tag}: walker ${w.who} unknown`);
    for(const p of w.path)if(blocked(pl,p[0],p[1]))problems.push(`${tag}: ${w.who} waypoint ${p} is not free floor`);
    for(let i=0;i<w.path.length;i++){const r=route(pl,w.path[i],w.path[(i+1)%w.path.length]);paths++;if(!r||along(pl,r))problems.push(`${tag}: ${w.who} cannot stroll ${w.path[i]}`);}
  }
  const cells=new Set();for(let i=0;i<12;i++){const p=leafAt(port,i);cells.add(p.map(Math.round).join());if(p[0]<f[0]||p[0]>f[2]||p[1]<f[1]||p[1]>f[3])problems.push(`${tag}: leaf pile ${i} off the floor`);}
  if(cells.size!==12)problems.push(`${tag}: leaf piles share a place`);
  for(let i=0;i<120;i++){const from=pl.spots[Math.floor(rand()*pl.spots.length)].stand,to=[f[0]-80+rand()*(f[2]-f[0]+160),f[1]-120+rand()*(f[3]-f[1]+200)];
    const r=route(pl,from,to);paths++;if(!r)continue;const bad=along(pl,r);if(bad)problems.push(`${tag}: tap ${to.map(Math.round)} walks through ${bad.map(Math.round)}`);}
  for(const state of [{today:[],done:[]},{today:tasks.slice(0,3),done:[]},{today:tasks,done:tasks},{today:['sweep'],done:[],piles:[0,3,5,7,11]}]){
    try{const c=ctx2d(),o={t:3.2,reduced:false,ready:true,left:2,...state};back(c,port,o);for(const [,fn] of props(c,pl,o))fn();marks(c,pl,o,'bunk');
      bubble(c,300,500,'Một câu nói rất dài để thử bóng chữ có bị tràn ra ngoài hay không nhé',{x0:v0,x1:v1});cap(c,300,500,1);
      back(c,port,{...o,reduced:true});}
    catch(e){problems.push(`${tag}: drawing threw ${e.stack||e}`);}
  }
}
// the stage at many sizes: standing at any spot, the player and the spot's tap point are on screen
const SIZES=[[320,460],[360,560],[375,600],[390,640],[414,700],[430,760],[600,900],[768,900],[820,1000],[1024,640],[1280,720],[1366,700],[1440,820],[1920,960],[2560,1300],[700,520],[960,540]];
for(const [cw,ch] of SIZES)for(const band of [ch,Math.round(ch*.55)]){
  const port=portraitFor(cw,ch),pl=plan(port);
  for(const s of pl.spots){
    const cam=[s.stand[0],s.stand[1]-(port?110:90)],{k,ox,oy}=frame(port,cw,ch,cam,band);views++;
    if(!(k>0)||!isFinite(ox)||!isFinite(oy)){problems.push(`${cw}×${ch}: a broken view`);continue;}
    const scr=p=>[p[0]*k+ox,p[1]*k+oy],me=scr(s.stand),head=scr([s.stand[0],s.stand[1]-120]),hit=scr(s.hit);
    if(me[0]<0||me[0]>cw||me[1]>band+2||head[1]<-2)problems.push(`${cw}×${ch} band ${band}: standing at ${s.id} is off screen (${me.map(Math.round)})`);
    if(hit[0]<-4||hit[0]>cw+4||hit[1]<-30||hit[1]>band+4)problems.push(`${cw}×${ch} band ${band}: ${s.id}'s tap point is off screen (${hit.map(Math.round)})`);
    if(band===ch&&k*(port?150:150)*(port?.9:.74)<44)problems.push(`${cw}×${ch}: the player is tiny (${(k*150).toFixed(0)}px)`);
  }
}
for(const p of problems)console.log('✗ '+p);
console.log(`${problems.length?'✗':'✓'} trại tạm giữ: 2 views, ${tasks.length} tasks, ${paths} paths, ${views} screen views, ${problems.length} problems`);
process.exit(problems.length?1:0);
