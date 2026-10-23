import Phaser from 'phaser';
// @ts-ignore a plain module shared with the old interface and the build sheet (bundled in: a relative path)
import {HOUSES,paintHouse,houseTop} from '../../public/js/house-art.js';
// @ts-ignore the same: a house style turned a quarter (🏝️ moved and turned in the build mode)
import {turnedView} from '../../public/js/island-decor-art.js';

/** 🏗️ Xây trên đảo on the new interface: the plots of a private island and what stands on them (game/island_build.py),
 * drawn isometrically by PrivateIslandRenderer (private-island.ts). Pure painting: every building is a few Phaser
 * graphics sorted by its front corner, its level adds details; a construction site is scaffolding (giàn giáo) with a
 * green net and, for the big ones, a crane. The map's numbers and the list come from public/js/island-layout.js
 * (withBuilds); nothing here decides a rule. 🏡 The house styles (20/10) are public/js/house-art.js models, painted
 * through a small adapter (houseView) in their colour (`look`). */
type Pt=[number,number];
export interface BuiltItem {plot:number;x:number;y:number;r?:number;coast:boolean;kind:string;look?:number;level:number;work:boolean;until:number;next:number;
  pier?:{rect:{x:number;y:number;w:number;h:number};end:Pt;dir:Pt}}

const N=14,HW=40,HH=20,PLOT=.072;
export const iso=(x:number,y:number):Pt=>[(x-y)*N*HW,(x+y)*N*HH];
const shade=(c:number,k:number)=>{const r=Math.min(255,Math.round(((c>>16)&255)*k)),g=Math.min(255,Math.round(((c>>8)&255)*k)),b=Math.min(255,Math.round((c&255)*k));return (r<<16)|(g<<8)|b;};
type Proj=(x:number,y:number,z?:number)=>Phaser.Geom.Point;
const TALL:Record<string,number>={nha_san:52,biet_thu:70,lau_dai:120,cong_vien:30,ho_boi:20,golf:24,cam_trai:34,ben_thuyen:30};
/** How much bigger than its plot's own scale each kind is drawn (from the plot's middle: still inside its square). */
const GROW:Record<string,number>={nha_san:1.4,biet_thu:1.3,lau_dai:1.35,cong_vien:1.25,ho_boi:1,golf:1.15,cam_trai:1.3,ben_thuyen:1};
const HOUSE_GROW=1.3;
const isHouse=(kind:string)=>Boolean((HOUSES as Record<string,unknown>)[kind]);
const tierOf=(kind:string)=>Number((HOUSES as Record<string,{tier?:number}>)[kind]?.tier)||0;
const num=(c:string)=>parseInt(c.slice(1),16)||0;
/** The house-art.js adapter on one Graphics: local plot points (relative to the plot's middle) through P. */
function houseView(gr:Phaser.GameObjects.Graphics,P:Proj,x:number,y:number){
  return {zs:1,depth:(a:number,b:number)=>a+b,
    P:(lx:number,ly:number,lz:number)=>{const q=P(x+lx,y+ly,lz);return [q.x,q.y];},
    fill:(pts:number[][],color:string,alpha=1)=>{gr.fillStyle(num(color),alpha).fillPoints(pts.map(p=>new Phaser.Geom.Point(p[0],p[1])),true);},
    circle:(cx:number,cy:number,r:number,color:string,alpha=1)=>{gr.fillStyle(num(color),alpha).fillCircle(cx,cy,r);},
    line:(a:number[],b:number[],color:string,w:number)=>{gr.lineStyle(w,num(color),1).lineBetween(a[0],a[1],b[0],b[1]);}};
}

/** A box over the map rectangle centred on (x, y), half sizes hx, hy, from height z0 to z1: two lit walls and a top. */
function prism(g:Phaser.GameObjects.Graphics,P:Proj,x:number,y:number,hx:number,hy:number,z0:number,z1:number,wall:number,top?:number){
  const W=P(x-hx,y+hy,z0),S=P(x+hx,y+hy,z0),E=P(x+hx,y-hy,z0),Wt=P(x-hx,y+hy,z1),St=P(x+hx,y+hy,z1),Et=P(x+hx,y-hy,z1),Nt=P(x-hx,y-hy,z1);
  g.fillStyle(shade(wall,.78),1).fillPoints([W,S,St,Wt],true);
  g.fillStyle(wall,1).fillPoints([S,E,Et,St],true);
  g.fillStyle(top??shade(wall,1.12),1).fillPoints([Nt,Et,St,Wt],true);
}
/** A hipped roof (a pyramid) over the rectangle at height z. */
function hip(g:Phaser.GameObjects.Graphics,P:Proj,x:number,y:number,hx:number,hy:number,z:number,h:number,roof:number){
  const W=P(x-hx,y+hy,z),S=P(x+hx,y+hy,z),E=P(x+hx,y-hy,z),Nw=P(x-hx,y-hy,z),A=P(x,y,z+h);
  g.fillStyle(shade(roof,.9),1).fillPoints([Nw,W,A],true);
  g.fillStyle(shade(roof,.75),1).fillPoints([W,S,A],true);
  g.fillStyle(roof,1).fillPoints([S,E,A],true);
  g.lineStyle(1.5,shade(roof,.55),1).lineBetween(S.x,S.y,A.x,A.y);
}
/** Windows along the two lit walls of a box (one row per floor); `lit`: warm evening light. */
function windows(g:Phaser.GameObjects.Graphics,P:Proj,x:number,y:number,hx:number,hy:number,z0:number,floorH:number,floors:number,lit=false,per=2){
  for(let f=0;f<floors;f++){
    const za=z0+f*floorH+floorH*.32,zb=z0+f*floorH+floorH*.72;
    for(let i=0;i<per;i++){
      const t0=(i+.3)/per,t1=(i+.7)/per;
      g.fillStyle(lit?0xffe08a:0x9fd0e4,1);
      g.fillPoints([P(x-hx+2*hx*t0,y+hy,za),P(x-hx+2*hx*t1,y+hy,za),P(x-hx+2*hx*t1,y+hy,zb),P(x-hx+2*hx*t0,y+hy,zb)],true);
      g.fillStyle(lit?0xfff0b8:0xb8e0ee,1);
      g.fillPoints([P(x+hx,y+hy-2*hy*t0,za),P(x+hx,y+hy-2*hy*t1,za),P(x+hx,y+hy-2*hy*t1,zb),P(x+hx,y+hy-2*hy*t0,zb)],true);
    }
  }
}
function door(g:Phaser.GameObjects.Graphics,P:Proj,x:number,y:number,hx:number,hy:number,z0:number,h:number,color=0x7a4b2a){
  g.fillStyle(color,1).fillPoints([P(x+hx,y+hy*.25,z0),P(x+hx,y-hy*.2,z0),P(x+hx,y-hy*.2,z0+h),P(x+hx,y+hy*.25,z0+h)],true);
}
function tree(g:Phaser.GameObjects.Graphics,P:Proj,x:number,y:number,size=1,leaf=0x4f9a4a){
  const b=P(x,y,0),t=P(x,y,18*size);
  g.fillStyle(0x000000,.14).fillEllipse(b.x+4,b.y+2,22*size,9*size);
  g.lineStyle(4*size,0x7a5432,1).lineBetween(b.x,b.y,t.x,t.y);
  g.fillStyle(shade(leaf,.8),1).fillCircle(t.x-4*size,t.y+2,10*size);g.fillStyle(leaf,1).fillCircle(t.x+3*size,t.y-3*size,11*size);
  g.fillStyle(shade(leaf,1.25),1).fillCircle(t.x-1,t.y-8*size,7*size);
}
function tile(g:Phaser.GameObjects.Graphics,P:Proj,x:number,y:number,h:number,color:number,edge?:number,alpha=1){
  const pts=[P(x-h,y-h),P(x+h,y-h),P(x+h,y+h),P(x-h,y+h)];
  g.fillStyle(color,alpha).fillPoints(pts,true);
  if(edge!==undefined){g.lineStyle(2,edge,.9).strokePoints(pts,true);}
}

/** One plot: empty (a faint square with four stakes), a construction site, or the building at its level. Returns the
 * objects drawn (the caller destroys them when the island changes). */
export function paintPlot(s:Phaser.Scene,it:BuiltItem|null,plot:{x:number;y:number;coast:boolean},rand:()=>number):Phaser.GameObjects.GameObject[]{
  const x=plot.x,y=plot.y,h=PLOT/2,[ox,oy]=iso(x,y),out:Phaser.GameObjects.GameObject[]=[];
  const P:Proj=(px,py,z=0)=>{const [a,b]=iso(px,py);return new Phaser.Geom.Point(a-ox,b-oy-z);};
  const flat=s.add.graphics().setPosition(ox,oy).setDepth(-1e6+5);out.push(flat);
  const g=s.add.graphics().setPosition(ox,oy).setDepth(iso(x+h,y+h)[1]-6);out.push(g);
  if(!it){   // ô đất trống
    tile(flat,P,x,y,h*.92,0xffffff,0xffffff,.16);
    for(const [cx,cy] of [[-1,-1],[1,-1],[1,1],[-1,1]]){const b=P(x+cx*h*.92,y+cy*h*.92),t=P(x+cx*h*.92,y+cy*h*.92,9);g.lineStyle(2.5,0x8a6038,1).lineBetween(b.x,b.y,t.x,t.y);}
    if(plot.coast){const a=P(x,y);const tx=s.add.text(ox+a.x,oy+a.y-4,'⚓',{fontSize:'16px'}).setOrigin(.5,.5).setAlpha(.7).setDepth(-1e6+6);out.push(tx);}
    return out;
  }
  if(it.work){   // an upgrade: the old level still stands under the net
    if(it.level>=1){flat.destroy();g.destroy();out.length=0;out.push(...paintPlot(s,{...it,work:false},plot,rand));
      const f2=s.add.graphics().setPosition(ox,oy).setDepth(-1e6+5),g2=s.add.graphics().setPosition(ox,oy).setDepth(iso(x+h,y+h)[1]-5);out.push(f2,g2);
      scaffold(s,g2,f2,P,x,y,h,it,out,false);}
    else scaffold(s,g,flat,P,x,y,h,it,out,true);
    return out;}
  const lv=Math.max(1,Math.min(3,it.level)),K=GROW[it.kind]||(isHouse(it.kind)?HOUSE_GROW:1);
  g.setScale(K);
  if(isHouse(it.kind)){   // 🏡 a house style: its yard flat under the people, the house sorted by its front corner
    flat.setScale(K);
    paintHouse(it.kind,lv,it.look||0,turnedView(houseView(flat,P,x,y),it.r||0),{only:'ground'});
    paintHouse(it.kind,lv,it.look||0,turnedView(houseView(g,P,x,y),it.r||0),{only:'parts'});
    return out;
  }
  /** A small moving part (a flag, a flame, a jet of water) at a point of `g`'s drawing, as big as the building. */
  const part=(gx:number,gy:number)=>s.add.graphics().setPosition(ox+gx*K,oy+gy*K).setScale(K).setDepth(g.depth+1);
  switch(it.kind){
    case 'nha_san':{
      tile(flat,P,x,y,h*.95,0xc9a77a,undefined,.5);
      const hx=lv>1?.024:.02,hy=lv>1?.02:.017,z=14;
      g.lineStyle(3,0x6e4a2e,1);for(const [a,b] of [[-1,1],[1,1],[1,-1],[-1,-1]]){const p0=P(x+a*hx,y+b*hy),p1=P(x+a*hx,y+b*hy,z);g.lineBetween(p0.x,p0.y,p1.x,p1.y);}
      prism(g,P,x+(lv>1?.004:0),y+(lv>1?.008:0),hx+.008,hy+.012,z,z+3,0x9b6a3c,0xb5844f);   // the floor and a veranda
      prism(g,P,x,y,hx,hy,z+3,z+24,0xd9b77a);
      windows(g,P,x,y,hx,hy,z+3,21,1,false,1);door(g,P,x,y,hx,hy,z+3,15);
      hip(g,P,x,y,hx+.007,hy+.007,z+24,18,lv>2?0x7f8f45:0xa8743a);
      if(lv>2){const a=P(x+hx+.006,y+hy+.012,z+16),b=P(x-hx,y+hy+.012,z+16);g.lineStyle(2,0xd9483b,1);g.beginPath();g.moveTo(a.x,a.y);g.lineTo((a.x+b.x)/2,(a.y+b.y)/2+7);g.lineTo(b.x,b.y);g.strokePath();}
      break;}
    case 'biet_thu':{
      tile(flat,P,x,y,h*.95,0xe9e2d2,undefined,.9);
      const hx=.028,hy=.024,fl=lv>1?2:1,fh=26;
      prism(g,P,x,y,hx,hy,0,fl*fh,0xfaf7f0);
      windows(g,P,x,y,hx,hy,0,fh,fl,lv>2,2);door(g,P,x,y,hx,hy,0,18,0x3f6f96);
      if(lv>1){const a=P(x-hx,y+hy+.004,fh+2),b=P(x+hx,y+hy+.004,fh+2),c=P(x+hx+.004,y-hy,fh+2);g.lineStyle(2,0x5a8fb0,1).lineBetween(a.x,a.y,b.x,b.y).lineBetween(b.x,b.y,c.x,c.y);}
      if(lv>2){prism(g,P,x,y,hx,hy,fl*fh,fl*fh+3,0xdcd4c4,0xe8e0cf);const u=P(x-.01,y-.006,fl*fh+3),t=P(x-.01,y-.006,fl*fh+22);
        g.lineStyle(2,0x777777,1).lineBetween(u.x,u.y,t.x,t.y);g.fillStyle(0xd9483b,1).fillTriangle(t.x-14,t.y+6,t.x+14,t.y+6,t.x,t.y-4);
        for(let i=0;i<5;i++){const q=P(x-hx+i*hx/2,y+hy,fl*fh+4);g.fillStyle(0xffe08a,1).fillCircle(q.x,q.y,2);}}
      else hip(g,P,x,y,hx+.004,hy+.004,fl*fh,20,0x3d7fb0);
      break;}
    case 'lau_dai':{
      tile(flat,P,x,y,h*.97,0xb9b3a8,undefined,.9);
      const stone=0xb7b0a6,hx=.022,hy=.02;
      const tower=(tx:number,ty:number,r:number,z:number,roof:number)=>{const b=P(tx,ty,0),t=P(tx,ty,z);
        g.fillStyle(shade(stone,.8),1).fillRect(b.x-r,t.y,r,b.y-t.y);g.fillStyle(stone,1).fillRect(b.x,t.y,r,b.y-t.y);
        g.fillStyle(shade(stone,.9),1).fillEllipse(b.x,b.y,r*2,r);g.fillStyle(shade(stone,1.1),1).fillEllipse(t.x,t.y,r*2,r);
        g.fillStyle(roof,1).fillTriangle(t.x-r-2,t.y,t.x+r+2,t.y,t.x,t.y-r*2.4);
        g.fillStyle(lv>2?0xffe08a:0x5c5650,1).fillRect(t.x-2,t.y+10,4,7);
        if(lv>1){const f=t.y-r*2.4;g.lineStyle(1.5,0x555555,1).lineBetween(t.x,f,t.x,f-14);const flag=part(t.x,f-14);
          flag.fillStyle(0xd9483b,1).fillTriangle(0,0,12,3,0,6);out.push(flag);s.tweens.add({targets:flag,scaleX:{from:K,to:K*.7},duration:600+rand()*300,yoyo:true,repeat:-1});}};
      if(lv>2){prism(g,P,x,y,hx+.012,hy+.012,0,14,shade(stone,.92));}
      prism(g,P,x,y-.004,hx,hy,0,56,stone);
      for(let i=0;i<4;i++){const a=P(x-hx+i*hx/1.5,y+hy-.004,56);g.fillStyle(shade(stone,.78),1).fillRect(a.x-3,a.y-6,6,6);const b=P(x+hx,y+hy-.004-i*hy/1.5,56);g.fillStyle(stone,1).fillRect(b.x-3,b.y-6,6,6);}
      windows(g,P,x,y-.004,hx,hy,0,28,2,lv>2,2);
      const d0=P(x,y+hy-.004,0),d1=P(x,y+hy-.004,22);g.fillStyle(0x5a3a22,1).fillEllipse(d0.x,d1.y+4,14,10).fillRect(d0.x-7,d1.y+4,14,d0.y-d1.y-4);
      tower(x+hx+.004,y+hy+.002,9,78,0xb5453a);
      if(lv>1)tower(x-hx-.002,y+hy+.004,8,70,0xb5453a);
      if(lv>2)tower(x+hx+.004,y-hy-.006,8,88,0x3f6f96);
      break;}
    case 'cong_vien':{
      tile(flat,P,x,y,h*.95,0x8fd06a,0x6fae58);
      const a=P(x-h*.9,y),b=P(x+h*.9,y),c=P(x,y-h*.9),d=P(x,y+h*.9);flat.lineStyle(5,0xe9d7a6,1).lineBetween(a.x,a.y,b.x,b.y).lineBetween(c.x,c.y,d.x,d.y);
      tree(g,P,x-.02,y-.02,1);if(lv>1){tree(g,P,x+.02,y-.02,.85,0x5aa94e);}
      const bench=P(x+.016,y+.018);g.fillStyle(0x8a6038,1).fillRect(bench.x-10,bench.y-6,20,4).fillRect(bench.x-9,bench.y-2,2,5).fillRect(bench.x+7,bench.y-2,2,5);
      if(lv>1)for(let i=0;i<10;i++){const q=P(x-h*.8+rand()*h*1.6,y+h*.45+rand()*h*.4);flat.fillStyle([0xff8aa0,0xffd25a,0xb48de0,0xffffff][i%4],1).fillCircle(q.x,q.y,2.6);}
      if(lv>2){const f=P(x,y);g.fillStyle(0xd8d2c8,1).fillEllipse(f.x,f.y,30,15);g.fillStyle(0x6ec6e0,1).fillEllipse(f.x,f.y-1,22,10);
        const jet=s.add.ellipse(ox+f.x*K,oy+(f.y-12)*K,6*K,18*K,0xffffff,.8).setDepth(g.depth+1);out.push(jet);s.tweens.add({targets:jet,scaleY:{from:.7,to:1.25},duration:700,yoyo:true,repeat:-1});}
      break;}
    case 'ho_boi':{
      tile(flat,P,x,y,h*.95,0xf1ebe0,0xd8cfbf);
      const w=lv>1?.024:.028;tile(flat,P,x-(lv>1?.006:0),y,w,0x3fb3d9);
      const hl=[P(x-w,y-w*.4),P(x+w*.5,y-w*.4),P(x+w*.5,y-w*.2),P(x-w,y-w*.2)];flat.fillStyle(0xffffff,.35).fillPoints(hl,true);
      const ring=s.add.ellipse(ox+P(x-.006,y+.004).x,oy+P(x-.006,y+.004).y,12,6,0xffffff,0).setStrokeStyle(2,0xffffff,.7).setDepth(-1e6+6);out.push(ring);
      s.tweens.add({targets:ring,scale:{from:.6,to:1.6},alpha:{from:1,to:0},duration:1800,repeat:-1});
      if(lv>1){for(const dy of [-.016,.0,.016]){const q=P(x+.026,y+dy);g.fillStyle(0xffffff,1).fillRect(q.x-7,q.y-3,14,4);g.fillStyle(0x3d7fb0,1).fillRect(q.x-7,q.y-5,5,3);}
        const u=P(x+.026,y-.026),t=P(x+.026,y-.026,24);g.lineStyle(2,0x888888,1).lineBetween(u.x,u.y,t.x,t.y);g.fillStyle(0xff7a59,1).fillEllipse(t.x,t.y,26,9);}
      if(lv>2){const top=P(x-.03,y-.03,26),bot=P(x-.012,y-.006,2);g.lineStyle(5,0xffc93c,1);g.beginPath();g.moveTo(top.x,top.y);g.lineTo((top.x+bot.x)/2+10,(top.y+bot.y)/2);g.lineTo(bot.x,bot.y);g.strokePath();
        const lb=P(x-.03,y-.03);g.lineStyle(2,0x999999,1).lineBetween(lb.x,lb.y,top.x,top.y);}
      break;}
    case 'golf':{
      tile(flat,P,x,y,h*.95,0x7ccf5a,0x5aa94e);
      const hole=P(x+.012,y-.008);flat.fillStyle(0x2f6d2a,1).fillEllipse(hole.x,hole.y,8,4);
      const flagAt=(fx:number,fy:number,c:number)=>{const b=P(fx,fy),t=P(fx,fy,30);g.lineStyle(2,0xf2f2f2,1).lineBetween(b.x,b.y,t.x,t.y);
        const fl=part(t.x,t.y);fl.fillStyle(c,1).fillTriangle(0,0,14,4,0,8);out.push(fl);
        s.tweens.add({targets:fl,scaleX:{from:K,to:K*.75},duration:700+rand()*200,yoyo:true,repeat:-1});};
      flagAt(x+.012,y-.008,0xd9483b);
      const ball=P(x-.012,y+.014);g.fillStyle(0xffffff,1).fillCircle(ball.x,ball.y-2,2.5);
      if(lv>1){const t2=P(x-.016,y-.016);flat.fillStyle(0xf0dca0,1).fillEllipse(t2.x,t2.y,24,11);flagAt(x-.02,y+.02,0xffc93c);}
      if(lv>2){const c=P(x+.022,y+.02);g.fillStyle(0xffffff,1).fillRect(c.x-9,c.y-12,18,8);g.fillStyle(0x3d7fb0,1).fillRect(c.x-9,c.y-16,18,4);
        g.fillStyle(0x333333,1).fillCircle(c.x-6,c.y-3,2.5).fillCircle(c.x+6,c.y-3,2.5);}
      break;}
    case 'cam_trai':{
      tile(flat,P,x,y,h*.95,0xb6c97a,undefined,.7);
      const tent=(tx:number,ty:number,sz:number,c:number)=>{const zt=24*sz/.012,W=P(tx-sz,ty+sz*.8),S=P(tx+sz,ty+sz*.8),E=P(tx+sz,ty-sz*.8),Top=P(tx,ty+sz*.8,zt),Top2=P(tx,ty-sz*.8,zt);
        g.fillStyle(shade(c,.8),1).fillPoints([W,S,Top],true);g.fillStyle(c,1).fillPoints([S,E,Top2,Top],true);g.fillStyle(0x3a2a1a,1).fillTriangle(Top.x,Top.y+6,W.x+(S.x-W.x)*.35,W.y+(S.y-W.y)*.35,W.x+(S.x-W.x)*.65,W.y+(S.y-W.y)*.65);};
      tent(x-.012,y-.012,.012,0xe8833a);
      if(lv>1){const f=P(x+.014,y+.014);g.fillStyle(0x6e4a2e,1).fillRect(f.x-8,f.y-2,16,3);
        const fire=part(f.x,f.y-2);fire.fillStyle(0xff9a3a,1).fillTriangle(-6,0,6,0,0,-14);fire.fillStyle(0xffe08a,1).fillTriangle(-3,0,3,0,0,-8);
        out.push(fire);s.tweens.add({targets:fire,scaleY:{from:K*.8,to:K*1.25},duration:300,yoyo:true,repeat:-1});}
      tent(x+.016,y-.016,lv>2?.014:.01,0x4f9a6a);
      if(lv>2){const a=P(x-.03,y+.024,22),b=P(x+.03,y-.03,22);for(let i=0;i<=8;i++){const t=i/8;g.fillStyle([0xffe08a,0xff8aa0,0x9fd0e4][i%3],1).fillCircle(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t+Math.sin(t*Math.PI)*8,2.2);}}
      break;}
    case 'ben_thuyen':{
      tile(flat,P,x,y,h*.95,0xd8c39a,undefined,.8);
      if(it.pier){const r=it.pier.rect,pts=[P(r.x-r.w/2,r.y-r.h/2),P(r.x+r.w/2,r.y-r.h/2),P(r.x+r.w/2,r.y+r.h/2),P(r.x-r.w/2,r.y+r.h/2)];
        flat.fillStyle(0x6e4a2e,1).fillPoints(pts.map(p=>new Phaser.Geom.Point(p.x,p.y+6)),true);flat.fillStyle(0xb5844f,1).fillPoints(pts,true);
        const [ex,ey]=it.pier.end,[dx,dy]=it.pier.dir,side:Pt=[ex-dx*.03+(dy?.03:0),ey-dy*.03+(dx?.03:0)];
        const boat=s.add.graphics().setPosition(ox+P(...side).x,oy+P(...side).y).setDepth(iso(...side)[1]);out.push(boat);
        const k=lv>2?1.3:lv>1?1.05:.8;boat.fillStyle(0xffffff,.45).fillEllipse(0,4,90*k,20*k);
        boat.fillStyle(0xffffff,1).fillPoints([new Phaser.Geom.Point(-40*k,-4*k),new Phaser.Geom.Point(40*k,-8*k),new Phaser.Geom.Point(30*k,8*k),new Phaser.Geom.Point(-34*k,8*k)],true);
        boat.fillStyle(0x24507a,1).fillRect(-34*k,3*k,64*k,4*k);
        if(lv>1&&lv<3){boat.lineStyle(2,0x6b5130,1).lineBetween(-2,-6*k,-2,-60*k);boat.fillStyle(0xfdfaf2,1).fillTriangle(0,-58*k,0,-10*k,26*k,-12*k);}
        if(lv>2){boat.fillStyle(0xeef3f7,1).fillRect(-20*k,-22*k,36*k,16*k);boat.fillStyle(0x3d6f96,1).fillRect(-16*k,-19*k,28*k,6*k);}
        s.tweens.add({targets:boat,angle:{from:-1.5,to:1.5},duration:1600,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});}
      const post=P(x,y),top=P(x,y,26);g.lineStyle(3,0x6e4a2e,1).lineBetween(post.x,post.y,top.x,top.y);
      const t=s.add.text(ox+top.x*K,oy+top.y*K,'⚓',{fontSize:'18px'}).setOrigin(.5,1).setDepth(g.depth+1);out.push(t);
      break;}
  }
  return out;
}

/** Giàn giáo: poles at the corners and the middles, planks every few metres, a green net over the front, a crane for
 * the big ones; how tall follows what is being built. */
function scaffold(s:Phaser.Scene,g:Phaser.GameObjects.Graphics,flat:Phaser.GameObjects.Graphics,P:Proj,x:number,y:number,h:number,it:BuiltItem,out:Phaser.GameObjects.GameObject[],ground:boolean){
  const hx=h*.78,hy=h*.78,top=Math.max(30,(TALL[it.kind]||(isHouse(it.kind)?houseTop(it.kind,Math.max(1,it.next))*HOUSE_GROW:40))*(it.next>1?1:.75));
  if(ground)tile(flat,P,x,y,h*.95,0xc9b48a,0xa8916a);
  if(ground)for(let i=0;i<8;i++){const q=P(x-h*.8+((i*37)%10)/10*h*1.6,y-h*.8+((i*53)%10)/10*h*1.6);flat.fillStyle(i%2?0x9b8a6a:0xd8cfbf,1).fillRect(q.x-3,q.y-2,6,3);}   // bricks, sand
  const corners:Pt[]=[[-1,1],[0,1],[1,1],[1,0],[1,-1],[-1,0],[-1,-1],[0,-1]];
  g.lineStyle(2.5,0x8a6038,1);
  for(const [a,b] of corners){const p0=P(x+a*hx,y+b*hy),p1=P(x+a*hx,y+b*hy,top);g.lineBetween(p0.x,p0.y,p1.x,p1.y);}
  for(let z=12;z<=top;z+=14){const W=P(x-hx,y+hy,z),S=P(x+hx,y+hy,z),E=P(x+hx,y-hy,z);g.lineStyle(3,0xc49a5c,1).lineBetween(W.x,W.y,S.x,S.y).lineBetween(S.x,S.y,E.x,E.y);}
  const W=P(x-hx,y+hy,4),S=P(x+hx,y+hy,4),E=P(x+hx,y-hy,4),Wt=P(x-hx,y+hy,top),St=P(x+hx,y+hy,top),Et=P(x+hx,y-hy,top);
  g.fillStyle(0x3f9a5a,.38).fillPoints([W,S,St,Wt],true);g.fillStyle(0x4fae6a,.32).fillPoints([S,E,Et,St],true);
  g.lineStyle(1,0x2f6d3a,.5);for(let k=1;k<4;k++){const a=P(x-hx+2*hx*k/4,y+hy,4),b=P(x-hx+2*hx*k/4,y+hy,top);g.lineBetween(a.x,a.y,b.x,b.y);}
  if(it.kind==='lau_dai'||it.kind==='biet_thu'||tierOf(it.kind)>=3){
    const base=P(x-hx,y-hy),mast=P(x-hx,y-hy,top+46),jib=P(x+hx*1.8,y-hy*2.2,top+46);
    g.lineStyle(4,0xf2b630,1).lineBetween(base.x,base.y,mast.x,mast.y);g.lineStyle(3,0xf2b630,1).lineBetween(mast.x-14,mast.y+4,jib.x,jib.y);
    const hook=s.add.graphics().setPosition(0,0).setDepth(g.depth+1);hook.lineStyle(1,0x444444,1);out.push(hook);
    const ox=(g as any).x,oy=(g as any).y,hx0=ox+jib.x-10,hy0=oy+jib.y;hook.lineBetween(hx0,hy0,hx0,hy0+30);hook.fillStyle(0x8a6038,1).fillRect(hx0-6,hy0+30,12,6);
    s.tweens.add({targets:hook,y:{from:0,to:8},duration:1500,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
  }
  const sign=s.add.text((g as any).x+P(x+hx,y+hy,top).x,(g as any).y+P(x+hx,y+hy,top).y,'🏗️',{fontSize:'18px'}).setOrigin(.5,1).setDepth(g.depth+1);out.push(sign);
  s.tweens.add({targets:sign,y:sign.y-5,duration:900,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
}
