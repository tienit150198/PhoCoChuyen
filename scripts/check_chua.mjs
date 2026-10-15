// Headless check of the walkable pagoda, no browser needed. Since 15/10 (owner: "theo dạng 2.5d") the pagoda is one
// 2.5D courtyard (public/js/scenes/chua-iso.js); for every day (who is in the yard changes with the lunar day) and
// every number of wish trees the server may send (0…9):
//   • every hotspot's standing point is on free floor and reachable from the gate;
//   • random taps give paths whose every step is free floor (no walking through the burner, the pond, a tree or a
//     person), or no walk at all;
//   • no two hotspots sit on the same place; the grove's trees each have a spot;
//   • drawing the whole courtyard (without the images too: they may still be loading) throws nothing.
// The older frontal scene (public/js/scenes/chua-place.js) keeps its people, the Buddha and the "look" lines.
// Usage: node scripts/check_chua.mjs [--seed N]
const noop=()=>{};
const ctx2d=()=>new Proxy({measureText:s=>({width:String(s).length*7}),createRadialGradient:()=>({addColorStop:noop}),createLinearGradient:()=>({addColorStop:noop}),getImageData:()=>({data:[]}),getLineDash:()=>[]},{get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>{t[k]=v;return true;}});
globalThis.document={hidden:false,createElement:()=>({getContext:ctx2d})};
globalThis.location={search:''};
const {N,GROVE,plan,route,free,project,unproject,ground,props,treeBoard,groveSign,npc}=await import('../public/js/scenes/chua-iso.js');
const {buddha}=await import('../public/js/scenes/chua-place.js');

const args=process.argv.slice(2);
let seed=Number(args[args.indexOf('--seed')+1])||20261015;
const rand=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
const problems=[];
const DAYS=[{lunar:11,feast:false},{lunar:12,feast:false},{lunar:15,feast:true},{lunar:1,feast:true}];
const TREES=['binh_an','gia_dao','suc_khoe','hoc_hanh','su_nghiep','tai_loc','tinh_duyen','uoc_mo','tuong_nho'].map((id,i)=>({id,name:id,emoji:'🌳',count:i*3,ribbons:Array(i).fill('do')}));
const along=(pl,path,from)=>{let a=from;for(const b of path){const n=Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/.1);
  for(let k=1;k<=n;k++){const x=a[0]+(b[0]-a[0])*k/n,y=a[1]+(b[1]-a[1])*k/n;if(!free(pl,x,y))return [x,y];}a=b;}return null;};
const r2=p=>p.map(v=>Math.round(v*10)/10);
// the projection round-trips
for(const p of [[0,0],[N,0],[3.5,7.25],[N,N]]){const q=unproject(...project(...p));if(Math.hypot(q[0]-p[0],q[1]-p[1])>1e-9)problems.push(`projection does not round-trip at ${p}`);}
let paths=0;
for(const day of DAYS)for(const n of [0,4,9]){
  const trees=TREES.slice(0,n),pl=plan(day,trees),tag=`lunar ${day.lunar}/${n} trees`;
  if(!free(pl,...pl.entry))problems.push(`${tag}: the gate is not free floor`);
  if(pl.spots.filter(s=>s.kind==='tree').length!==Math.min(n,GROVE.length))problems.push(`${tag}: not one spot per tree`);
  for(const s of pl.spots){
    if(!free(pl,...s.stand)){problems.push(`${tag}: ${s.id} stands on a footprint ${r2(s.stand)}`);continue;}
    const r=route(pl,pl.entry,s.stand);paths++;
    if(!r){problems.push(`${tag}: ${s.id} unreachable from the gate`);continue;}
    const end=r[r.length-1]||pl.entry;if(Math.hypot(end[0]-s.stand[0],end[1]-s.stand[1])>.05)problems.push(`${tag}: ${s.id} path ends off its spot`);
    const bad=along(pl,r,pl.entry);if(bad)problems.push(`${tag}: path gate→${s.id} crosses a footprint at ${r2(bad)}`);
  }
  for(const s of pl.spots)for(const t of pl.spots)if(s.id<t.id&&Math.hypot(s.stand[0]-t.stand[0],s.stand[1]-t.stand[1])<.35)problems.push(`${tag}: ${s.id} and ${t.id} share a standing point`);
  for(let i=0;i<80;i++){const from=pl.spots[Math.floor(rand()*pl.spots.length)].stand,to=[-2+rand()*(N+4),-2+rand()*(N+4)];
    const r=route(pl,from,to);paths++;if(!r)continue;const bad=along(pl,r,from);if(bad)problems.push(`${tag}: tap ${to} from ${from} walks through ${bad}`);}
  for(const images of [{},{hall:{complete:true,naturalWidth:512,naturalHeight:498},tree:{complete:true,naturalWidth:768,naturalHeight:784},veg:{complete:true,naturalWidth:1536,naturalHeight:1024}}])
    try{const c=ctx2d(),o={t:3,reduced:false,feast:day.feast,lit:true,bell:.5,mo:true,images,trees,near:trees[0]?.id||'',ls:1.4};
      ground(c,o);for(const [,fn] of props(c,o))fn();for(const q of pl.people)npc(c,q,.44,3);groveSign(c,o);trees.forEach((t,i)=>treeBoard(c,t,i,o));buddha(c,600,400,300);}
    catch(e){problems.push(`${tag}: drawing threw ${e.stack||e}`);}
}
for(const p of problems)console.log('✗ '+p);
console.log(`${problems.length?'✗':'✓'} chùa 2.5D: ${DAYS.length} days × 3 groves, ${paths} paths, ${problems.length} problems`);
process.exit(problems.length?1:0);
