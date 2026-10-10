// Deterministic geometry contact sheets for review when browser capture is not
// available. Projects the real Three triangles with a depth buffer; this is a
// geometry review artifact, not a screenshot or an alternate game renderer.
import * as T from 'three';
import sharp from 'sharp';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createResidenceKit,districtArchitecture} from '../client/district3d/architecture.js';
import {roomStructure,resources} from '../client/home3d/meshes.js';
const directory=resolve(process.argv[2]||'tmp/architecture-preview');await mkdir(directory,{recursive:true});
const geometries=new Set(),materials=new Map(),kit=createResidenceKit(color=>{if(!materials.has(color))materials.set(color,new T.MeshStandardMaterial({color}));return materials.get(color);},geometries);
const camera=new T.OrthographicCamera(-5.15,5.15,6,-4.25,.1,80);camera.position.set(10,11,15);camera.lookAt(0,2,0);camera.updateMatrixWorld();
const sun=new T.Vector3(-.5,1,.65).normalize(),eye=new T.Vector3().copy(camera.position).normalize();
function picture(group,fit=false){
  if(fit){const b=new T.Box3().setFromObject(group),center=b.getCenter(new T.Vector3()),s=b.getSize(new T.Vector3()),span=Math.max(s.x,s.z)*.64+s.y*.28;camera.left=-span;camera.right=span;camera.top=span*.91;camera.bottom=-span*.91;camera.position.copy(center).add(new T.Vector3(10,11,15));camera.lookAt(center);camera.updateProjectionMatrix();camera.updateMatrixWorld();}
  const width=760,height=720,rgba=Buffer.alloc(width*height*4),depth=new Float32Array(width*height);depth.fill(Infinity);
  group.updateMatrixWorld(true);const a=new T.Vector3(),b=new T.Vector3(),c=new T.Vector3(),normal=new T.Vector3(),u=new T.Vector3(),v=new T.Vector3();
  group.traverse(o=>{if(!o.isMesh)return;const geo=o.geometry,position=geo.attributes.position,index=geo.index,n=index?index.count:position.count;
    for(let i=0;i<n;i+=3){a.fromBufferAttribute(position,index?index.getX(i):i).applyMatrix4(o.matrixWorld);b.fromBufferAttribute(position,index?index.getX(i+1):i+1).applyMatrix4(o.matrixWorld);c.fromBufferAttribute(position,index?index.getX(i+2):i+2).applyMatrix4(o.matrixWorld);
      normal.crossVectors(u.subVectors(b,a),v.subVectors(c,a)).normalize();if(normal.dot(eye)<0)continue;
      const light=.67+.33*Math.max(0,normal.dot(sun)),color=parseInt(o.material.color.clone().multiplyScalar(light).getHexString(),16);
      a.project(camera);b.project(camera);c.project(camera);const ax=(a.x+1)*width/2,ay=(1-a.y)*height/2,bx=(b.x+1)*width/2,by=(1-b.y)*height/2,cx=(c.x+1)*width/2,cy=(1-c.y)*height/2;
      const area=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy);if(Math.abs(area)<.0001)continue;
      const x0=Math.max(0,Math.floor(Math.min(ax,bx,cx))),x1=Math.min(width-1,Math.ceil(Math.max(ax,bx,cx))),y0=Math.max(0,Math.floor(Math.min(ay,by,cy))),y1=Math.min(height-1,Math.ceil(Math.max(ay,by,cy)));
      for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){const aa=((by-cy)*(x+.5-cx)+(cx-bx)*(y+.5-cy))/area,bb=((cy-ay)*(x+.5-cx)+(ax-cx)*(y+.5-cy))/area,cc=1-aa-bb;if(aa<0||bb<0||cc<0)continue;const z=aa*a.z+bb*b.z+cc*c.z,p=y*width+x;if(z>=depth[p])continue;depth[p]=z;rgba[p*4]=color>>16;rgba[p*4+1]=(color>>8)&255;rgba[p*4+2]=color&255;rgba[p*4+3]=255;}
    }
  });return sharp(rgba,{raw:{width,height,channels:4}}).resize(380,360).png().toBuffer();
}
for(const type of ['rent','apartment','townhouse','villa']){
  let svg='<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="810"><rect width="1600" height="810" fill="#eee5d5"/>';const pictures=[];
  for(const [i,plan]of districtArchitecture(type).entries()){const x=(i%4)*400+10,y=Math.floor(i/4)*400;
    svg+=`<rect x="${x}" y="${y+5}" width="380" height="390" rx="14" fill="#f8f2e5"/><text x="${x+15}" y="${y+379}" font-family="sans-serif" font-size="15" fill="#625442">${plan.id}</text>`;
    pictures.push({input:await picture(kit.build(plan)),left:x,top:y+5});
  }
  await sharp(Buffer.from(svg+'</svg>')).composite(pictures).png().toFile(resolve(directory,type+'.png'));
}
const R=resources(),source=JSON.parse(execFileSync('python',['-c',"from game import housing,deco; import json; print(json.dumps({k:deco.rooms_of('rent:'+k+':1' if v['kind']=='rent' else 'own:p:'+k) for k,v in housing.HOMES.items()}))"],{encoding:'utf8'}));
const interiors=Object.entries(source).map(([kind,rooms])=>({label:kind,room:rooms.find(r=>r.type==='living')||rooms[0],scope:'own:p:'+kind}));
for(const [name,rows]of [['interior-homes',interiors],['interior-estate',[
  ['study','bookwall','wall'],['cinema','screen','wall'],['cellar','racks','wall'],['gym','mirror','wall'],['closet','rails','wall'],['showroom','gate','wall'],['pavilion','gazebo','floor'],['infinity','pool','floor']
].map(([type,fixture,layer])=>({label:type,scope:'estate:vuon:1',room:{id:type,type,cols:7,frows:4,wrows:2,out:['pavilion','infinity'].includes(type),fix:[{t:fixture,layer,x:2,y:0,w:3,h:2}]}}))]]){
  const height=Math.ceil(rows.length/4)*400+10,pictures=[];let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="${height}"><rect width="1600" height="${height}" fill="#eee5d5"/>`;
  for(const [i,row]of rows.entries()){const x=(i%4)*400+10,y=Math.floor(i/4)*400;svg+=`<rect x="${x}" y="${y+5}" width="380" height="390" rx="14" fill="#f8f2e5"/><text x="${x+15}" y="${y+379}" font-family="sans-serif" font-size="15" fill="#625442">${row.label}</text>`;pictures.push({input:await picture(roomStructure(row.room,{},R,row.scope),true),left:x,top:y+5});}
  await sharp(Buffer.from(svg+'</svg>')).composite(pictures).png().toFile(resolve(directory,name+'.png'));
}
R.dispose();
for(const g of geometries)g.dispose();for(const m of materials.values())m.dispose();
console.log(directory);
