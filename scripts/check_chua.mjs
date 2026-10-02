// Headless check of the walkable pagoda (public/js/scenes/chua-place.js, "Vào chùa"), no browser needed.
// For every area × composition (landscape, portrait) × day (who is in the yard changes with the lunar day):
//   • every hotspot's standing point is on free floor and reachable from every way in;
//   • random taps give paths whose every few pixels are free floor (no walking through the burner, the pond,
//     the altar or a person), or no walk when the tap is far off the floor;
//   • the ways in are free floor; drawing every area throws nothing.
// Usage: node scripts/check_chua.mjs [--seed N]
const noop=()=>{};
const ctx2d=()=>new Proxy({measureText:s=>({width:String(s).length*7}),createRadialGradient:()=>({addColorStop:noop}),createLinearGradient:()=>({addColorStop:noop}),getImageData:()=>({data:[]}),getLineDash:()=>[]},{get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>{t[k]=v;return true;}});
globalThis.document={hidden:false,createElement:()=>({getContext:ctx2d})};
globalThis.location={search:''};
const {AREAS,plan,route,blocked,paintRoom,areaProps,person,buddha}=await import('../public/js/scenes/chua-place.js');

const args=process.argv.slice(2);
let seed=Number(args[args.indexOf('--seed')+1])||20261002;
const rand=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
const problems=[];
const DAYS=[{lunar:11,feast:false},{lunar:12,feast:false},{lunar:15,feast:true},{lunar:1,feast:true}];
const along=(pl,path)=>{for(let i=1;i<path.length;i++){const [a,b]=[path[i-1],path[i]],n=Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/3);
  for(let k=0;k<=n;k++){const x=a[0]+(b[0]-a[0])*k/n,y=a[1]+(b[1]-a[1])*k/n;if(blocked(pl,x,y))return [x,y];}}return null;};
let paths=0;
for(const port of [false,true])for(const day of DAYS)for(const {id:area} of AREAS){
  const pl=plan(area,port,day),tag=`${area}/${port?'portrait':'landscape'}/lunar ${day.lunar}`;
  for(const [from,p] of Object.entries(pl.entry))if(blocked(pl,p[0],p[1]))problems.push(`${tag}: the way in from ${from} is not free floor`);
  for(const s of pl.spots){
    if(blocked(pl,s.stand[0],s.stand[1])){problems.push(`${tag}: ${s.id} stands on a footprint ${s.stand}`);continue;}
    for(const [from,p] of Object.entries(pl.entry)){const r=route(pl,p,s.stand);paths++;
      if(!r){problems.push(`${tag}: ${s.id} unreachable from ${from}`);continue;}
      const end=r[r.length-1];if(Math.hypot(end[0]-s.stand[0],end[1]-s.stand[1])>1)problems.push(`${tag}: ${s.id} path ends off its spot`);
      const bad=along(pl,r);if(bad)problems.push(`${tag}: path ${from}→${s.id} crosses a footprint at ${bad.map(Math.round)}`);}
  }
  // spots may not share a standing point, and each spot's hit must be closer to it than to any other spot
  for(const s of pl.spots)for(const t of pl.spots)if(s!==t&&Math.hypot(s.hit[0]-t.hit[0],s.hit[1]-t.hit[1])<12)problems.push(`${tag}: ${s.id} and ${t.id} overlap`);
  const [x0,y0,x1,y1]=pl.floor;
  for(let i=0;i<60;i++){const from=pl.spots[Math.floor(rand()*pl.spots.length)].stand,to=[x0-80+rand()*(x1-x0+160),y0-120+rand()*(y1-y0+200)];
    const r=route(pl,from,to);paths++;if(!r)continue;const bad=along(pl,r);if(bad)problems.push(`${tag}: tap ${to.map(Math.round)} walks through ${bad.map(Math.round)}`);}
  try{const c=ctx2d(),w={ctx:c,isPortrait:()=>port,reduced:false,time:3,c:null},o={t:3,reduced:false,feast:day.feast,lit:true,bell:.5,wish:true,mo:true};
    paintRoom(w,area,o);for(const [,fn] of areaProps(c,area,port,o))fn();for(const q of pl.people)person(c,q.x,q.y,1,q.who,{pose:q.sit?'sit':''});buddha(c,600,400,300);}
  catch(e){problems.push(`${tag}: drawing threw ${e.stack||e}`);}
}
for(const p of problems)console.log('✗ '+p);
console.log(`${problems.length?'✗':'✓'} chùa: ${AREAS.length} areas × 2 views × ${DAYS.length} days, ${paths} paths, ${problems.length} problems`);
process.exit(problems.length?1:0);
