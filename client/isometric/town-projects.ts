/** 🏗️ Công trình của phố on the 2.5D island (game/town_projects.py, lots `tp_<id>` in game/town_layout.json).
 *
 * Each lot is painted procedurally for its stage: an empty plot with a "Sắp xây" board (soon, and with bunting while
 * the street raises money for it), a frame in scaffolding with a crane (the 48 h build) and the finished building.
 * The scene only reads `{id, stage, pct, left}` from v4/town-projects-data.js; nothing here touches the save.
 */
import type {Rect} from './model';

export type TownProjectStage='soon'|'funding'|'building'|'done';
export interface TownProjectLot {id:string;stage:TownProjectStage;pct:number;left:number}
export const TOWN_PROJECT_STAGES:TownProjectStage[]=['soon','funding','building','done'];
export const TOWN_PROJECT_IDS=['cong_vien','rap_phim','thu_vien','san_van_dong','cau_ra_dao','benh_vien'];
const HEADROOM=250,PAD=24;

/** Untrusted input (the API) becomes a short, known list. */
export function normalizeTownProjects(value:unknown):TownProjectLot[]{
  if(!Array.isArray(value))return [];
  const out:TownProjectLot[]=[],seen=new Set<string>();
  for(const item of value){
    const id=String(item?.id||'');if(!TOWN_PROJECT_IDS.includes(id)||seen.has(id))continue;seen.add(id);
    const stage=TOWN_PROJECT_STAGES.includes(item.stage)?item.stage as TownProjectStage:'soon';
    const pct=Math.max(0,Math.min(100,Math.floor(Number(item.pct)||0))),left=Math.max(0,Math.min(48,Math.ceil(Number(item.left)||0)));
    out.push({id,stage,pct:stage==='funding'?pct:0,left:stage==='building'?left:0});
  }
  return out;
}
/** The short line above a lot: money raised while funding, hours left while building. */
export function townProjectBadge(p:TownProjectLot){return p.stage==='funding'?`🏗️ ${p.pct}%`:p.stage==='building'?`⏳ ${Math.max(1,p.left)}h`:'';}

/** Canvas size and the canvas point of the footprint's (x0,y0) corner, for an image placed at that corner. */
export function townProjectCanvas(r:Rect){
  const w=r.x1-r.x0,h=r.y1-r.y0;
  return {width:Math.ceil((w+h)*64+PAD*2),height:Math.ceil((w+h)*32+HEADROOM+PAD),originX:PAD+h*64,originY:HEADROOM};
}

type Ink=string;
export function drawTownProject(ctx:CanvasRenderingContext2D,id:string,stage:TownProjectStage,r:Rect){
  const w=r.x1-r.x0,h=r.y1-r.y0,{originX,originY}=townProjectCanvas(r);
  const P=(u:number,v:number,z=0):[number,number]=>[originX+(u-v)*64,originY+(u+v)*32-z];
  const poly=(pts:[number,number][],fill:Ink,stroke?:Ink,width=1.5)=>{ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fillStyle=fill;ctx.fill();if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width;ctx.stroke();}};
  const line=(a:[number,number],b:[number,number],color:Ink,width=2)=>{ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineCap='round';ctx.stroke();};
  const floor=(u0:number,v0:number,u1:number,v1:number,fill:Ink,stroke?:Ink,z=0)=>poly([P(u0,v0,z),P(u1,v0,z),P(u1,v1,z),P(u0,v1,z)],fill,stroke);
  /** An upright block: its top and the two faces that look at the viewer (+y on the left, +x on the right). */
  const box=(u0:number,v0:number,u1:number,v1:number,z0:number,z1:number,top:Ink,left:Ink,right:Ink,edge='rgba(80,60,45,.55)')=>{
    poly([P(u0,v1,z0),P(u1,v1,z0),P(u1,v1,z1),P(u0,v1,z1)],left,edge);
    poly([P(u1,v0,z0),P(u1,v1,z0),P(u1,v1,z1),P(u1,v0,z1)],right,edge);
    poly([P(u0,v0,z1),P(u1,v0,z1),P(u1,v1,z1),P(u0,v1,z1)],top,edge);
  };
  /** Window rows on both visible faces. */
  const windows=(u0:number,v0:number,u1:number,v1:number,z0:number,z1:number,rows:number,color:Ink)=>{
    const floorH=(z1-z0)/rows;
    for(let k=0;k<rows;k++){
      const za=z0+floorH*k+floorH*.3,zb=za+floorH*.42;
      for(let u=u0+.35;u<u1-.3;u+=.7)poly([P(u,v1,za),P(u+.32,v1,za),P(u+.32,v1,zb),P(u,v1,zb)],color);
      for(let v=v0+.35;v<v1-.3;v+=.7)poly([P(u1,v,za),P(u1,v+.32,za),P(u1,v+.32,zb),P(u1,v,zb)],color);
    }
  };
  const tree=(u:number,v:number,size=1)=>{const [x,y]=P(u,v);ctx.fillStyle='rgba(70,90,50,.25)';ctx.beginPath();ctx.ellipse(x,y,22*size,10*size,0,0,Math.PI*2);ctx.fill();line([x,y],[x,y-26*size],'#7a5a3c',5*size);ctx.fillStyle='#6f9a5c';ctx.beginPath();ctx.arc(x,y-42*size,22*size,0,Math.PI*2);ctx.fill();ctx.fillStyle='#8db56e';ctx.beginPath();ctx.arc(x-6*size,y-48*size,13*size,0,Math.PI*2);ctx.fill();};
  const text=(s:string,x:number,y:number,size:number,color:Ink,weight='bold')=>{ctx.font=`${weight} ${size}px "Be Vietnam Pro", "Segoe UI", sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(s,x,y);};
  // CanvasRenderingContext2D.roundRect is missing on older phones (iOS 15).
  const rounded=(x:number,y:number,rw:number,rh:number,k:number)=>{ctx.beginPath();ctx.moveTo(x+k,y);ctx.arcTo(x+rw,y,x+rw,y+rh,k);ctx.arcTo(x+rw,y+rh,x,y+rh,k);ctx.arcTo(x,y+rh,x,y,k);ctx.arcTo(x,y,x+rw,y,k);ctx.closePath();};
  const emoji=TOWN_EMOJI[id]||'🏗️';
  ctx.lineJoin='round';
  if(stage==='soon'||stage==='funding'){
    // Bare earth inside a low picket fence, a few stacked materials and a board on two posts.
    floor(0,0,w,h,'#d8bf91','#b49567');floor(.25,.25,w-.25,h-.25,'#cfb284');
    for(let k=0;k<5;k++){const u=.5+((k*1.7)%(w-1)),v=.6+((k*1.3)%(h-1.2));const [x,y]=P(u,v);ctx.fillStyle='rgba(150,120,80,.35)';ctx.beginPath();ctx.ellipse(x,y,9,4,0,0,Math.PI*2);ctx.fill();}
    const posts:[number,number][]=[];for(let u=0;u<=w+.01;u+=.5)posts.push([u,h]);for(let v=h-.5;v>=-.01;v-=.5)posts.push([w,v]);
    for(const [u,v] of posts)line(P(u,v),P(u,v,18),'#a07c55',3);
    line(P(0,h,12),P(w,h,12),'#c49d6f',3);line(P(w,h,12),P(w,0,12),'#c49d6f',3);
    box(w-1.3,.4,w-.5,1.1,0,14,'#c97f5d','#a9654a','#b8704f');box(w-1.25,.45,w-.55,.85,14,26,'#cf8a66','#a9654a','#b8704f');
    box(.5,.5,1.4,.9,0,8,'#9c9b95','#7f7e78','#8b8a84');
    const [bx,by]=P(w/2+.2,h/2+.2),bw=118,bh=62;
    line([bx-40,by],[bx-40,by-74],'#7d5d3f',5);line([bx+40,by],[bx+40,by-74],'#7d5d3f',5);
    ctx.fillStyle='#fff3da';ctx.strokeStyle='#8a6a48';ctx.lineWidth=4;rounded(bx-bw/2,by-74-bh,bw,bh,8);ctx.fill();ctx.stroke();
    text(emoji,bx,by-74-bh+20,22,'#000','normal');text('SẮP XÂY',bx,by-74-15,16,'#8a4f2d');
    if(stage==='funding'){
      // Bunting: the street is raising money for this one.
      const flags=['#e07a5f','#f2cc8f','#81b29a','#3d85c6'],a=P(0,h,40),b=P(w,h,40),c=P(w,0,40);
      line(P(0,h),a,'#7d5d3f',3);line(P(w,h),P(w,h,46),'#7d5d3f',3);line(P(w,0),c,'#7d5d3f',3);
      for(const [s,e] of [[a,b],[b,c]] as [[number,number],[number,number]][]){
        line(s,e,'#8a6a48',1.5);
        for(let t=.06;t<.96;t+=.12){const x=s[0]+(e[0]-s[0])*t,y=s[1]+(e[1]-s[1])*t;poly([[x-6,y],[x+6,y],[x,y+12]],flags[Math.round(t*8)%4]);}
      }
    }
    return;
  }
  if(stage==='building'){
    // Foundation, a rising concrete frame wrapped in scaffolding and green netting, and a tower crane.
    floor(0,0,w,h,'#c9b089','#a88d66');floor(.3,.3,w-.3,h-.3,'#b3b0a8','#8f8c84');
    const tall=TALL[id]||110,top=tall*.62,u0=.55,v0=.55,u1=w-.55,v1=h-.55;
    box(u0,v0,u1,v1,0,top,'#cfcac0','rgba(170,165,155,.55)','rgba(185,180,170,.55)');
    for(let z=0;z<=top;z+=top/3)line(P(u0,v1,z),P(u1,v1,z),'#9b968c',3),line(P(u1,v1,z),P(u1,v0,z),'#9b968c',3);
    for(let u=u0;u<=u1+.01;u+=(u1-u0)/3)line(P(u,v1),P(u,v1,top),'#8c877d',4);
    for(let v=v0;v<=v1+.01;v+=(v1-v0)/3)line(P(u1,v),P(u1,v,top),'#8c877d',4);
    // Scaffolding: poles a little outside the frame, ledgers each lift, braces on the left face.
    ctx.globalAlpha=.9;
    poly([P(u0-.15,v1+.15,0),P(u1+.15,v1+.15,0),P(u1+.15,v1+.15,top+12),P(u0-.15,v1+.15,top+12)],'rgba(122,170,110,.35)');
    ctx.globalAlpha=1;
    for(let u=u0-.15;u<=u1+.16;u+=.6)line(P(u,v1+.15),P(u,v1+.15,top+16),'#d39a3d',2.5);
    for(let v=v0-.15;v<=v1+.16;v+=.6)line(P(u1+.15,v),P(u1+.15,v,top+16),'#d39a3d',2.5);
    for(let z=14;z<=top+12;z+=22){line(P(u0-.15,v1+.15,z),P(u1+.15,v1+.15,z),'#c48a2f',2);line(P(u1+.15,v1+.15,z),P(u1+.15,v0-.15,z),'#c48a2f',2);}
    for(let u=u0-.15;u<u1;u+=1.2)line(P(u,v1+.15,4),P(u+.6,v1+.15,top+8),'#b98032',1.5);
    const mast=P(u0+.2,v0+.2),boom=tall+70;
    line(mast,[mast[0],mast[1]-boom],'#e0a419',6);for(let z=12;z<boom;z+=14)line([mast[0]-4,mast[1]-z],[mast[0]+4,mast[1]-z-10],'#b8860b',1.5);
    line([mast[0]-40,mast[1]-boom],[mast[0]+130,mast[1]-boom+18],'#e0a419',5);line([mast[0],mast[1]-boom-22],[mast[0]+120,mast[1]-boom+17],'#b8860b',1.5);line([mast[0],mast[1]-boom-22],[mast[0]-38,mast[1]-boom],'#b8860b',1.5);
    ctx.fillStyle='#6b6b6b';ctx.fillRect(mast[0]-46,mast[1]-boom-4,16,14);
    line([mast[0]+100,mast[1]-boom+14],[mast[0]+100,mast[1]-boom+70],'#555',1.5);ctx.fillStyle='#c97f5d';ctx.fillRect(mast[0]+92,mast[1]-boom+70,16,10);
    return;
  }
  // Finished.
  if(id==='cong_vien'){
    floor(0,0,w,h,'#9fc27f','#7f9f63');floor(.2,.2,w-.2,h-.2,'#a9cb88');
    floor(w/2-.3,0,w/2+.3,h,'#e7d3b5');floor(0,h/2-.3,w,h/2+.3,'#e7d3b5');
    const [cx,cy]=P(w*.27,h*.27);ctx.fillStyle='#7fb3c9';ctx.strokeStyle='#5f8fa5';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(cx,cy,48,22,0,0,Math.PI*2);ctx.fill();ctx.stroke();
    const [fx,fy]=P(w/2,h/2);ctx.fillStyle='#d9d4c8';ctx.beginPath();ctx.ellipse(fx,fy,26,12,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='#8cc3d8';ctx.beginPath();ctx.ellipse(fx,fy-4,18,8,0,0,Math.PI*2);ctx.fill();line([fx,fy-4],[fx,fy-24],'#bfe2ef',3);
    for(const [u,v,s] of [[.6,h-.6,1],[w-.6,.6,1.1],[w-.7,h-.7,.95],[.7,h*.6,.8],[w*.75,h*.25,.85],[w*.3,h-.5,.9]])tree(u,v,s);
    for(const [u,v] of [[w/2+.55,h*.75],[w*.75,h/2+.55]]){box(u-.3,v-.08,u+.3,v+.08,8,11,'#b8875a','#94683f','#a4744a');line(P(u-.25,v),P(u-.25,v,8),'#555',2);line(P(u+.25,v),P(u+.25,v,8),'#555',2);}
    for(const [u,v] of [[w/2+.4,.4],[w-.4,h/2+.4]]){const [x,y]=P(u,v);line([x,y],[x,y-46],'#4f5a5e',3);ctx.fillStyle='#ffe9a8';ctx.beginPath();ctx.arc(x,y-48,5,0,Math.PI*2);ctx.fill();}
    return;
  }
  if(id==='san_van_dong'){
    floor(0,0,w,h,'#b9b4aa','#8f8a80');
    const f={u0:.9,v0:.9,u1:w-.25,v1:h-.25};floor(f.u0,f.v0,f.u1,f.v1,'#6fae5a','#5a8f48');
    for(let k=0;k<4;k++){const a=f.u0+(f.u1-f.u0)*k/4,b=a+(f.u1-f.u0)/8;floor(a,f.v0,b,f.v1,'#79b863');}
    floor(f.u0+.15,f.v0+.15,f.u1-.15,f.v1-.15,'rgba(0,0,0,0)','#f4f4ee');
    const mu=(f.u0+f.u1)/2;line(P(mu,f.v0+.15),P(mu,f.v1-.15),'#f4f4ee',1.5);const [mx,my]=P(mu,(f.v0+f.v1)/2);ctx.strokeStyle='#f4f4ee';ctx.beginPath();ctx.ellipse(mx,my,30,15,0,0,Math.PI*2);ctx.stroke();
    // Stands along the back two sides, stepping up away from the pitch.
    for(let k=0;k<3;k++){box(.05+k*.25,.05+k*.25,.85,h-.25,0,10+k*14,'#d6d0c4','#b9b1a3','#c7bfb1');}
    for(let k=0;k<3;k++){box(.85,.05+k*.25,w-.25,.85,0,10+k*14,'#d6d0c4','#b9b1a3','#c7bfb1');}
    for(let v=.35;v<h-.4;v+=.3)line(P(.75,v,38),P(.75,v+.15,38),['#e07a5f','#3d85c6','#f2cc8f'][Math.round(v*10)%3],3);
    box(.05,.05,.95,.95,0,60,'#c7c1b4','#a59d8e','#b5ad9e');floor(.0,.0,1,1,'#e07a5f','#b85e47',60);
    for(const [u,v] of [[0,h],[w,0],[w,h]]){const [x,y]=P(u,v);line([x,y],[x,y-120],'#6d6d6d',3);ctx.fillStyle='#fff7d0';ctx.strokeStyle='#6d6d6d';ctx.lineWidth=1.5;ctx.fillRect(x-12,y-132,24,12);ctx.strokeRect(x-12,y-132,24,12);}
    return;
  }
  if(id==='cau_ra_dao'){
    floor(0,0,w,h,'#9cc6cb','#7aa7ad');for(let k=0;k<6;k++){const u=.4+k*.6,v=.4+((k*1.37)%(h-.8));line(P(u,v),P(u+.4,v),'#c4e1e3',2);}
    floor(0,0,.6,h,'#d8c7a0','#b8a67f');floor(w-.6,0,w,h,'#d8c7a0','#b8a67f');
    const v0=h/2-.45,v1=h/2+.45,deck=34;
    for(const u of [1,w-1]){box(u-.12,v0+.1,u+.12,v0+.3,0,deck,'#9c968c','#7f7a71','#8c867c');box(u-.12,v1-.3,u+.12,v1-.1,0,deck,'#9c968c','#7f7a71','#8c867c');}
    box(0,v0,w,v1,deck,deck+8,'#d9d3c6','#aaa397','#bdb6a9');floor(0,h/2-.06,w,h/2+.06,'#f2e7b6',undefined,deck+8);
    const pu=w/2,pylon=150;box(pu-.15,v0-.1,pu+.15,v0+.1,deck,deck+pylon,'#eae6dc','#c4bfb3','#d3cec2');box(pu-.15,v1-.1,pu+.15,v1+.1,deck,deck+pylon,'#eae6dc','#c4bfb3','#d3cec2');
    box(pu-.15,v0-.1,pu+.15,v1+.1,deck+pylon-14,deck+pylon,'#eae6dc','#c4bfb3','#d3cec2');
    for(const v of [v0,v1])for(let k=1;k<=5;k++){const t=k/5;line(P(pu,v,deck+pylon-20),P(pu-t*(pu-.2),v,deck+8),'#8f8a80',1.2);line(P(pu,v,deck+pylon-20),P(pu+t*(w-.2-pu),v,deck+8),'#8f8a80',1.2);}
    for(let u=.4;u<w;u+=.8){const [x,y]=P(u,v1,deck+8);line([x,y],[x,y-22],'#4f5a5e',2);ctx.fillStyle='#ffe9a8';ctx.beginPath();ctx.arc(x,y-23,3.5,0,Math.PI*2);ctx.fill();}
    return;
  }
  floor(0,0,w,h,'#d9ccb3','#b4a586');
  const u0=.45,v0=.45,u1=w-.45,v1=h-.45;
  if(id==='rap_phim'){
    box(u0,v0,u1,v1,0,120,'#5b4a6b','#7d4f6e','#8e5d7c');windows(u0,v0,u1,v1,70,120,1,'#f6d98d');
    box(u0+.6,v1-.05,u1-.6,v1+.25,74,108,'#2d2a36','#26232e','#2d2a36');
    const [sx,sy]=P((u0+u1)/2+.1,v1+.25,91);text('CINEMA',sx-4,sy+8,15,'#ffd36b');
    for(let u=u0+.7;u<u1-.6;u+=.35){const [x,y]=P(u,v1+.25,74);ctx.fillStyle='#ffe9a8';ctx.beginPath();ctx.arc(x,y,2.5,0,Math.PI*2);ctx.fill();}
    box(u0+.9,v1-.02,u1-.9,v1+.02,0,46,'#3b3542','#e9c46a','#d4b05b');
    box(u0+.6,v1+.1,u1-.6,v1+.7,46,52,'#c0392b','#a93226','#b03a2e');
    for(let v=v0+.3;v<v1-.4;v+=.9){poly([P(u1,v,14),P(u1,v+.55,14),P(u1,v+.55,58),P(u1,v,58)],'#f4e9d0','#8a6a48');}
    return;
  }
  if(id==='thu_vien'){
    box(u0,v0,u1,v1,0,96,'#e9dcc0','#e2d3b4','#d6c6a5');windows(u0,v0,u1,v1,8,96,2,'#7aa3b8');
    // A gabled roof along x and a columned porch on the front (+y) face.
    const zr=96,zt=140,mv=(v0+v1)/2;
    poly([P(u0,v1,zr),P(u1,v1,zr),P(u1,mv,zt),P(u0,mv,zt)],'#a4543d','rgba(80,40,30,.6)');
    poly([P(u1,v0,zr),P(u1,v1,zr),P(u1,mv,zt)],'#d6c6a5','rgba(80,60,45,.55)');
    box(u0+.5,v1,u1-.5,v1+.55,0,6,'#d8ccb4','#c2b49a','#cfc1a7');
    for(let u=u0+.65;u<u1-.5;u+=.55)box(u-.06,v1+.38,u+.06,v1+.5,6,80,'#f6efe0','#e8dfcc','#efe6d3');
    box(u0+.45,v1,u1-.45,v1+.6,80,90,'#efe6d3','#e2d6be','#e8dcc5');
    const [sx,sy]=P((u0+u1)/2+.15,v1+.6,85);text('📚',sx,sy,14,'#000','normal');
    return;
  }
  // benh_vien: a tall white block, a lower wing and a red cross on the roof sign.
  box(u0,v0,u1-1.2,v1,0,170,'#f4f4f2','#e6e6e2','#dadad5');windows(u0,v0,u1-1.2,v1,10,170,5,'#8fb7d1');
  box(u1-1.2,v0+.4,u1,v1,0,70,'#efefec','#e1e1dc','#d5d5cf');windows(u1-1.2,v0+.4,u1,v1,8,70,2,'#8fb7d1');
  box(u0+.4,v1,u0+1.6,v1+.5,0,34,'#d1e3ef','#a9c7da','#bad3e3');
  const [cx,cy]=P((u0+u1-1.2)/2+.2,v1,186);ctx.fillStyle='#fff';ctx.strokeStyle='#c0392b';ctx.lineWidth=2;rounded(cx-17,cy-17,34,34,6);ctx.fill();ctx.stroke();
  ctx.fillStyle='#d64541';ctx.fillRect(cx-4,cy-12,8,24);ctx.fillRect(cx-12,cy-4,24,8);
  line(P(u0+.2,v1,170),P(u0+.2,v1,186),'#999',2);line(P(u1-1.4,v1,170),P(u1-1.4,v1,186),'#999',2);
}
const TOWN_EMOJI:Record<string,string>={cong_vien:'🌳',rap_phim:'🎬',thu_vien:'📚',san_van_dong:'🏟️',cau_ra_dao:'🌉',benh_vien:'🏥'};
const TALL:Record<string,number>={cong_vien:50,rap_phim:120,thu_vien:130,san_van_dong:70,cau_ra_dao:60,benh_vien:170};
