import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {execFileSync} from 'node:child_process';
const load=async file=>{const b=await build({entryPoints:[file],bundle:true,write:false,platform:'node',format:'esm',logLevel:'silent'});return import('data:text/javascript;base64,'+Buffer.from(b.outputFiles[0].text).toString('base64'));};
const m=await load('client/isometric/model.ts'),g=await load('client/isometric/trail-geometry.ts');
const cat=JSON.parse(execFileSync('python',['-c','import json; from game.content import public_content; print(json.dumps(public_content()["catalogue"]))'],{encoding:'utf8'}));
const buildings=m.townBuildings(cat),nav=m.townNavigation(buildings),trails=m.townTrails();
const samples=trails.map(t=>g.sampleTrailCurve(t.points,t.sampled));
const doors=[...buildings.map(b=>b.door),...m.townShopLots().map(b=>b.door)];
const distance=(p,a,b)=>{const dx=b.x-a.x,dy=b.y-a.y,t=Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy||1)));return Math.hypot(p.x-a.x-dx*t,p.y-a.y-dy*t);};
const connected=(a,b)=>a.some(p=>b.some((q,i)=>i&&distance(p,b[i-1],q)<.18))||b.some(p=>a.some((q,i)=>i&&distance(p,a[i-1],q)<.18));
const reached=new Set([0]);let changed=true;
while(changed){changed=false;for(let i=0;i<samples.length;i++)if(!reached.has(i)&&[...reached].some(j=>connected(samples[i],samples[j]))){reached.add(i);changed=true;}}
assert.equal(reached.size,trails.length,`painted roads must form one network, not rely on grass shortcuts; disconnected: ${trails.map((t,i)=>reached.has(i)?null:i+':'+t.district).filter(Boolean)}`);
for(let i=0;i<samples.length;i++){
  const path=samples[i];
  for(let k=0;k<path.length;k++){
    assert.ok(m.isWalkable(nav,path[k]),`road ${i} is walkable`);
    if(k)assert.ok(m.lineClear(nav,path[k-1],path[k]),`road ${i} cannot cross an obstacle`);
  }
  for(const end of [0,path.length-1]){
    const p=path[end],nearDoor=doors.some(d=>Math.hypot(d.x-p.x,d.y-p.y)<.2);
    const joinsOther=samples.some((other,j)=>i!==j&&other.some((q,k)=>k&&distance(p,other[k-1],q)<.18));
    const closesLoop=path.some((q,k)=>k&&Math.abs(k-end)>24&&distance(p,path[k-1],q)<.18);
    assert.ok(nearDoor||joinsOther||closesLoop,`road ${i} ${end===0?'start':'end'} stops in empty grass (${p.x},${p.y})`);
  }
}
console.log(`Street network: ${trails.length} linked roads; no unexplained dead ends; all centerlines walkable.`);
