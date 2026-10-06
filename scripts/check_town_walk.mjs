// Headless check of the walkable town on the home screen (public/js/scenes/town-place.js, v4/town-walk.js), no browser
// needed. For the full town (every career a save has today), a small save (a few careers) and one with a career this
// file does not know yet:
//   • every career has exactly one building, every landmark its place, no two buildings overlap;
//   • every door's standing point is on the floor, and every door is reachable from every other door, along paths
//     whose every few pixels are on the floor (a leg never cuts through a building);
//   • random taps anywhere give a path that ends on the floor, or none at all;
//   • a tap on a building's sign finds that building;
//   • drawing the town and its live layer throws nothing, in every state (locked, current, x3, lit, closed, off).
// Usage: node scripts/check_town_walk.mjs [--seed N]
const noop=()=>{};
const ctx2d=()=>new Proxy({measureText:s=>({width:String(s).length*7}),createRadialGradient:()=>({addColorStop:noop}),createLinearGradient:()=>({addColorStop:noop}),getImageData:()=>({data:[]})},{get:(t,k)=>k in t?t[k]:noop,set:(t,k,v)=>{t[k]=v;return true;}});
globalThis.document={hidden:false,createElement:()=>({getContext:ctx2d})};
globalThis.location={search:''};
const {plan,route,walkable,nearest,itemAt,districtAt,back,marks,LANDMARKS}=await import('../public/js/scenes/town-place.js');

const args=process.argv.slice(2);
let seed=Number(args[args.indexOf('--seed')+1])||20261003;
const rand=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
const ALL=['mother_baby','pharmacy','accounting','customer_care','restaurant','cafe_bakery','farm','grocery','pet_care','florist','salon','repair','homestay','teacher','tour_guide',
  'milk_tea','delivery','corp_accounting','tax_payroll','group_accounting','clothing','pet_shop','tra_da','fruit','garbage','drain','homemaker','ice_cream','nail','pagoda','pho','com',
  'photobooth','giupviec','naucom','babysitter','library','pilot','flight_attendant','oil','hr_admin','secretary','it_helpdesk','railway','nurse','police'];
const SAVES={full:[ALL,{}],small:[['milk_tea','grocery','delivery','pho','farm'],{}],newcareer:[[...ALL,'banh_mi','sua_xe_dap'],{banh_mi:'food',sua_xe_dap:'service'}]};
const problems=[];let paths=0;
const along=(pl,path)=>{for(let i=1;i<path.length;i++){const [a,b]=[path[i-1],path[i]],n=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/3));
  for(let k=0;k<=n;k++){const p=[a[0]+(b[0]-a[0])*k/n,a[1]+(b[1]-a[1])*k/n];if(!walkable(pl,p))return p;}}return null;};
for(const [name,[ids,cats]] of Object.entries(SAVES)){
  const pl=plan(ids,cats),tag=name;
  for(const id of ids){const n=pl.items.filter(it=>it.id===id).length;if(n!==1)problems.push(`${tag}: ${id} has ${n} buildings`);}
  for(const lm of Object.keys(LANDMARKS))if(!pl.items.some(it=>it.lm===lm))problems.push(`${tag}: landmark ${lm} missing`);
  for(const a of pl.items)for(const b of pl.items)if(a!==b&&a.row===b.row&&a.x0<b.x1-1&&b.x0<a.x1-1)problems.push(`${tag}: ${a.key} overlaps ${b.key}`);
  // A building's footprint is never floor (the walk passes in front of it, not through it).
  for(const it of pl.items)for(const p of [[it.cx,it.G-20],[it.x0+8,it.G-it.h/2],[it.x1-8,it.G-10]])if(walkable(pl,p))problems.push(`${tag}: ${it.key}'s building is floor at ${p.map(Math.round)}`);
  for(const it of pl.items){
    if(!walkable(pl,it.stand)){problems.push(`${tag}: ${it.key} stands off the floor ${it.stand}`);continue;}
    const sign=[it.cx,it.G-it.h+20];if(itemAt(pl,sign)!==it)problems.push(`${tag}: a tap on ${it.key}'s sign finds ${itemAt(pl,sign)?.key}`);
  }
  const stands=pl.items.map(it=>[it.key,it.stand]);
  for(const [ka,a] of stands)for(const [kb,b] of stands){if(ka===kb)continue;const r=route(pl,a,b);paths++;
    if(!r){problems.push(`${tag}: ${kb} unreachable from ${ka}`);continue;}
    const end=r[r.length-1];if(Math.hypot(end[0]-b[0],end[1]-b[1])>1)problems.push(`${tag}: ${ka}→${kb} ends off the door`);
    const bad=along(pl,r);if(bad)problems.push(`${tag}: ${ka}→${kb} leaves the floor at ${bad.map(Math.round)}`);}
  for(let i=0;i<600;i++){const from=nearest(pl,[rand()*pl.W,rand()*pl.H]),to=[rand()*pl.W*1.1-pl.W*.05,rand()*pl.H*1.1-pl.H*.05],r=route(pl,from,to);paths++;
    if(!r)continue;const bad=along(pl,r);if(bad)problems.push(`${tag}: tap ${to.map(Math.round)} walks off the floor at ${bad.map(Math.round)}`);
    if(!walkable(pl,r[r.length-1]))problems.push(`${tag}: tap ${to.map(Math.round)} ends off the floor`);}
  for(const row of pl.rows)for(const d of row.districts)if(districtAt(pl,[(d.x0+d.x1)/2,row.G+50])?.id!==d.id)problems.push(`${tag}: district ${d.id} not found on its street`);
  try{
    const c=ctx2d(),states=[{},{lock:true},{cur:true,x3:true},{glow:true,paused:true},{off:true}];
    for(const extra of states)back(c,pl,it=>({color:'#c4577a',emoji:'🧋',name:'Trà sữa',...extra}),{tint:{rgb:[40,40,90],alpha:.5,lamps:1}});
    marks(c,pl,{t:2,glow:pl.items.slice(0,5),arrow:pl.items[3],near:pl.items[4]});
  }catch(e){problems.push(`${tag}: drawing threw ${e.stack||e}`);}
}
for(const p of [...new Set(problems)].slice(0,60))console.log('✗ '+p);
console.log(`${problems.length?'✗':'✓'} khu phố: ${Object.keys(SAVES).length} towns, ${paths} paths, ${problems.length} problems`);
process.exit(problems.length?1:0);
