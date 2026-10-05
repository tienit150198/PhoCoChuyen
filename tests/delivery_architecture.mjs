import assert from 'node:assert/strict';
import {drawHouseFacade,drawLandmarkFacade} from '../public/js/careers/delivery_architecture.js';

const pal={lamps:0,tint:color=>color};
function render(draw,b,z,{clipped=false,lamps=0}={}){
  const quads=[],labels=[],vertices=[],stack=[];
  const c={fillStyle:'original',globalAlpha:.6,
    save(){stack.push([this.fillStyle,this.globalAlpha]);},
    restore(){[this.fillStyle,this.globalAlpha]=stack.pop();},
    beginPath(){},closePath(){},fill(){},
    moveTo(x,y){vertices.push([x,y]);},lineTo(x,y){vertices.push([x,y]);}
  };
  const H={shade:color=>color,windowCol:p=>p.lamps>.45?'#ffd284':'#728e91',
    label(ctx,s,text,color){labels.push({s,text,color});},
    fquad(ctx,box,u0,u1,v0,v1,color){
      assert.ok([u0,u1,v0,v1].every(Number.isFinite),'finite facade coordinates');
      assert.ok(u0>=0&&u1<=1&&u0<u1,'decoration remains within facade width');
      assert.ok(v0>=(box.zb||0)-1e-9&&v1<=(box.zb||0)+box.h+1e-9,'decoration remains within building height');
      assert.ok(v0<v1&&color,'non-empty coloured facade');
      quads.push({u0,u1,v0,v1,color});
      return clipped?null:[[u0*100,200-v0*10],[u1*100,201-v0*10],[u1*100,201-v1*10],[u0*100,200-v1*10]];
    }};
  const before=JSON.stringify(b);
  draw(c,b,z,{...pal,lamps},H);
  assert.equal(JSON.stringify(b),before,'renderer does not mutate world data');
  assert.equal(c.globalAlpha,.6,'inherited fog opacity preserved');
  assert.equal(c.fillStyle,'original','canvas state restored');
  assert.equal(stack.length,0,'balanced canvas save/restore');
  assert.ok(vertices.flat().every(Number.isFinite),'finite projected reflections');
  return {quads,labels,vertices};
}
const house={h:8.5,zb:0,col:'#d7c6a8',no:12,shop:true,awn:'#a66e54',win:2};
const near=render(drawHouseFacade,house,12),far=render(drawHouseFacade,house,85);
assert.ok(near.quads.length>far.quads.length*3,'distant facades omit fine detail');
assert.ok(near.vertices.length>0,'near glass has attached reflections');
assert.equal(render(drawHouseFacade,house,12,{lamps:1}).vertices.length,0,'lit windows omit daylight reflections');
assert.deepEqual(render(drawHouseFacade,house,12),near,'stable details across frames');
render(drawHouseFacade,house,12,{clipped:true});
assert.ok(render(drawHouseFacade,{...house,h:5.5,no:1},20).quads.some(q=>q.v0>3.5&&q.v1>4.9),'short tube houses have an upper window');
for(const h of [5.5,6.5,8.5,9.5,11.5])for(const no of [0,1,2,3,12]){
  render(drawHouseFacade,{...house,h,no,shop:no%2===0,win:no%2+1},15);
}
const L={name:'Chợ Bến Thành',emoji:'🛒'};
const mark={h:8.5,zb:0,col:'#d7c6a8',L,sign:true};
for(const shape of [{tower:true,h:20},{shopfront:true},{open:true},{stalls:true,awn:'#957b59'},{win:3},{gate:true,h:2.2,sign:false},{pump:true,h:1.6,sign:false},{canopy:true,zb:4.3,h:.7,sign:false},{arch:true,zb:4,h:1.1}]){
  const b={...mark,...shape};
  for(const z of [12,55,90]){
    const result=render(drawLandmarkFacade,b,z);
    if(b.sign)assert.ok(result.labels.some(l=>l.text.includes(L.name)),'destination name passed to translation-aware label helper');
  }
  render(drawLandmarkFacade,b,12,{clipped:true});
}
console.log(`Courier architecture: projection bounds, stable details, state, all landmark shapes and LOD passed (${near.quads.length} near / ${far.quads.length} far house quads).`);
