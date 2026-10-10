import assert from 'node:assert/strict';
import {build} from 'esbuild';
const built=await build({entryPoints:['client/isometric/town-scenery.ts','client/isometric/model.ts'],bundle:true,write:false,outdir:'unused',platform:'node',format:'esm',logLevel:'silent'});
const read=name=>import('data:text/javascript;base64,'+Buffer.from(built.outputFiles.find(f=>f.path.endsWith(name)).text).toString('base64'));
const ground=await read('town-scenery.js'),model=await read('model.js');
function recorder(){const polygons=[];let color=0,vertices=0;const g=new Proxy({fillStyle(c){color=c;return g;},fillPoints(p){vertices+=p.length;polygons.push({color,points:p});return g;}},{get:(target,key)=>target[key]||(()=>g)});return {g,polygons,get vertices(){return vertices;}};}
const districts=[{id:'a',material:'brick',bounds:{x0:0,y0:0,x1:5,y1:5}},{id:'b',material:'slate',bounds:{x0:5,y0:0,x1:10,y1:5}}];
const trails=[{district:'a',width:2,points:[{x:0,y:2},{x:5,y:2}]},{district:'b',width:2,points:[{x:5,y:2},{x:10,y:2}]}];
const r=recorder();ground.drawNeighbourhoodGround(r.g,districts,trails,[],model.makeNavigation({bounds:{x0:-30,y0:-30,x1:90,y1:90},roads:[{x0:-30,y0:-30,x1:90,y1:90}],obstacles:[],step:.5}));
const contains=(points,p)=>{let yes=false;for(let i=0,j=points.length-1;i<points.length;j=i++){const a=points[i],b=points[j];if((a.y>p.y)!==(b.y>p.y)&&p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x)yes=!yes;}return yes;};
const surface=p=>r.polygons.filter(shape=>contains(shape.points,model.project(p))).at(-1)?.color;
assert.equal(surface({x:2,y:2}),surface({x:7,y:2}),'district transitions must keep the same main-road surface');
const dense=recorder();ground.drawNeighbourhoodGround(dense.g,districts,[{district:'a',width:2,sampled:true,points:Array.from({length:500},(_,i)=>({x:i*.02,y:2+Math.sin(i*.01)*.3}))}],[],model.makeNavigation({bounds:{x0:-30,y0:-30,x1:90,y1:90},roads:[],obstacles:[],step:.5}));
assert.ok(dense.vertices<5000,`smooth road geometry should be linear outlines, not a disc per sample: ${dense.vertices}`);
console.log('Town ground: coherent road surfaces; bounded ribbon geometry.',{vertices:dense.vertices});
