// Headless check of the walkable fairground (public/js/scenes/fair-place.js, v4/fair-walk.js), no browser needed.
// For both compositions (landscape, portrait) × the optional stalls (phóng dao, vay nóng: an older server has neither):
//   • the way in (the Cổng hội) and every hotspot's standing point are on free floor, and every hotspot is reachable
//     from the gate and from every other hotspot, along paths whose every few pixels are free floor;
//   • random taps give paths over free floor only (no walking through a tent, the mat, a cart or a person);
//   • no two hotspots share a tap point, every stall of the fair has a hotspot;
//   • the vé số cào stand keeps clear of the two food carts;
//   • drawing the backdrop and every prop throws nothing.
// Usage: node scripts/check_fair_walk.mjs [--seed N]
const noop=()=>{};
const ctx2d=()=>new Proxy({measureText:s=>({width:String(s).length*7}),createRadialGradient:()=>({addColorStop:noop}),createLinearGradient:()=>({addColorStop:noop}),getImageData:()=>({data:[]}),getLineDash:()=>[]},{get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>{t[k]=v;return true;}});
globalThis.document={hidden:false,createElement:()=>({getContext:ctx2d})};
globalThis.location={search:''};
const {plan,route,blocked,back,props,marks,STALLS}=await import('../public/js/scenes/fair-place.js');

const args=process.argv.slice(2);
const SEED=Number(args[args.indexOf('--seed')+1])||20261003;
let seed=SEED;
const rand=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
const problems=[];
// a path may graze a footprint's edge (the path finder's segment test is exact); half a pixel inside is a crossing
const PAD={x:20,y:7},inside=(pl,x,y)=>{const f=pl.floor;if(x<f[0]-.5||x>f[2]+.5||y<f[1]-.5||y>f[3]+.5)return true;
  return pl.blocks.some(b=>x>b[0]-PAD.x+.5&&x<b[2]+PAD.x-.5&&y>b[1]-PAD.y+.5&&y<b[3]+PAD.y-.5);};
const along=(pl,path)=>{for(let i=1;i<path.length;i++){const [a,b]=[path[i-1],path[i]],n=Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/3);
  for(let k=0;k<=n;k++){const x=a[0]+(b[0]-a[0])*k/n,y=a[1]+(b[1]-a[1])*k/n;if(inside(pl,x,y))return [x,y];}}return null;};
let paths=0,combos=0;
for(const port of [false,true])for(const dt of [true,false])for(const loan of [true,false])for(const xs of [true,false]){
  combos++;seed=SEED+combos*7919;   // each layout its own taps (a new optional stall does not reshuffle the others)
  const pl=plan(port,{dt,loan,xs}),tag=`${port?'portrait':'landscape'}${dt?'':' no-knife'}${loan?'':' no-loan'}${xs?'':' no-scratch'}`;
  for(const id of Object.keys(STALLS)){const want=id==='dt'?dt:id==='loan'?loan:id==='xs'?xs:true,has=pl.spots.some(s=>s.id===id);
    if(want!==has)problems.push(`${tag}: stall ${id} ${has?'shown but off':'missing'}`);}
  const gate=pl.entry.gate;if(blocked(pl,gate[0],gate[1]))problems.push(`${tag}: the gate is not free floor`);
  for(const s of pl.spots){
    if(blocked(pl,s.stand[0],s.stand[1])){problems.push(`${tag}: ${s.id} stands on a footprint ${s.stand}`);continue;}
    for(const from of [gate,...pl.spots.map(t=>t.stand)]){const r=route(pl,from,s.stand);paths++;
      if(!r){problems.push(`${tag}: ${s.id} unreachable from ${from}`);continue;}
      const end=r[r.length-1];if(Math.hypot(end[0]-s.stand[0],end[1]-s.stand[1])>1)problems.push(`${tag}: ${s.id} path ends off its spot`);
      const bad=along(pl,r);if(bad)problems.push(`${tag}: path ${from.map(Math.round)}→${s.id} crosses a footprint at ${bad.map(Math.round)}`);}
  }
  for(const s of pl.spots)for(const t of pl.spots)if(s!==t&&Math.hypot(s.hit[0]-t.hit[0],s.hit[1]-t.hit[1])<16)problems.push(`${tag}: ${s.id} and ${t.id} overlap`);
  const [x0,y0,x1,y1]=pl.floor;
  for(let i=0;i<150;i++){const from=pl.spots[Math.floor(rand()*pl.spots.length)].stand,to=[x0-80+rand()*(x1-x0+160),y0-150+rand()*(y1-y0+230)];
    const r=route(pl,from,to);paths++;if(!r)continue;const bad=along(pl,r);if(bad)problems.push(`${tag}: tap ${to.map(Math.round)} walks through ${bad.map(Math.round)}`);}
  {const x=pl.spots.find(s=>s.id==='xs');if(x)for(const id of ['candy','cane']){const q=pl.spots.find(s=>s.id===id);
    if(Math.hypot(x.stand[0]-q.stand[0],x.stand[1]-q.stand[1])<120)problems.push(`${tag}: the vé số stand is next to the ${id} cart`);}}
  try{const c=ctx2d(),o={t:3,reduced:false,live:{lt:true,oaq:true}};back(c,port,{dt,loan,xs},o);for(const [,fn] of props(c,pl,o))fn();marks(c,pl,o,'bc');}
  catch(e){problems.push(`${tag}: drawing threw ${e.stack||e}`);}
}
for(const p of problems)console.log('✗ '+p);
console.log(`${problems.length?'✗':'✓'} hội chợ: ${combos} layouts, ${paths} paths, ${problems.length} problems`);
process.exit(problems.length?1:0);
