import Phaser from 'phaser';
// @ts-ignore a plain module shared with the old interface and the build mode (bundled in: a relative path)
import {paintDecorItem,decorFx} from '../../public/js/island-decor-art.js';

/** 🏝️ Thiết kế đảo on the new interface: one decoration of a private island (game/island_design.py; its place from
 * public/js/island-layout.js withDesign().decor) painted with its model (public/js/island-decor-art.js) on two Phaser
 * graphics: what lies flat under the people, what stands sorted by its front corner. What moves (FX): trees sway,
 * pools shimmer, flames flicker, a fountain plays, floats bob, a waterfall foams, lamps glow at night (setNight()). */
type Pt=[number,number];
export interface DecorItem {id:number;kind:string;x:number;y:number;w:number;h:number;r:number}
const N=14,HW=40,HH=20,CELL=.024;
const iso=(x:number,y:number):Pt=>[(x-y)*N*HW,(x+y)*N*HH];
const num=(c:string)=>parseInt(String(c).slice(1,7),16)||0;
const turn=(x:number,y:number,r:number):Pt=>{r=r&3;return r===0?[x,y]:r===1?[-y,x]:r===2?[-x,-y]:[y,-x];};

/** The house-art.js adapter on one Graphics drawn at (ox, oy): local points around the item's middle (x, y). */
function view(gr:Phaser.GameObjects.Graphics,x:number,y:number,ox:number,oy:number){
  return {zs:1,depth:(a:number,b:number)=>a+b,
    P:(lx:number,ly:number,lz:number)=>{const [a,b]=iso(x+lx,y+ly);return [a-ox,b-oy-lz];},
    fill:(pts:number[][],color:string,alpha=1)=>{gr.fillStyle(num(color),alpha).fillPoints(pts.map(p=>new Phaser.Geom.Point(p[0],p[1])),true);},
    circle:(cx:number,cy:number,r:number,color:string,alpha=1)=>{gr.fillStyle(num(color),alpha).fillCircle(cx,cy,r);},
    line:(a:number[],b:number[],color:string,w:number)=>{gr.lineStyle(w,num(color),1).lineBetween(a[0],a[1],b[0],b[1]);}};
}

/** Paint one decoration; returns the objects drawn and its night lights (shown after dark). */
export function paintDecor(s:Phaser.Scene,it:DecorItem,rand:()=>number):{objects:Phaser.GameObjects.GameObject[];lights:Phaser.GameObjects.GameObject[]}{
  const out:Phaser.GameObjects.GameObject[]=[],lights:Phaser.GameObjects.GameObject[]=[];
  const [ox,oy]=iso(it.x,it.y),hx=it.w*CELL/2,hy=it.h*CELL/2,front=iso(it.x+hx,it.y+hy)[1];
  const flat=s.add.graphics().setPosition(ox,oy).setDepth(-1e6+4);out.push(flat);
  const g=s.add.graphics().setPosition(ox,oy).setDepth(front-4);out.push(g);
  paintDecorItem(it.kind,it.r,view(flat,it.x,it.y,ox,oy),{only:'ground'});
  paintDecorItem(it.kind,it.r,view(g,it.x,it.y,ox,oy),{only:'parts'});
  const fx=decorFx(it.kind)||{},at=(p:number[]):[number,number,number]=>{const [a,b]=turn(p[0],p[1],it.r);const [px,py]=iso(it.x+a,it.y+b);return [px,py,p[2]||0];};
  if(fx.sway)s.tweens.add({targets:g,angle:{from:-1.4,to:1.4},duration:2400+rand()*1600,yoyo:true,repeat:-1,ease:'Sine.easeInOut',delay:rand()*1200});
  if(fx.bob){s.tweens.add({targets:[g,flat],y:{from:oy-1.5,to:oy+1.5},duration:1600+rand()*600,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});}
  if(fx.water){const [wx,wy,whx,why]=fx.water,[a,b]=turn(whx,why,it.r),[cx,cy]=turn(wx,wy,it.r),mx=it.x+cx,my=it.y+cy,ax=Math.abs(a),ay=Math.abs(b);
    const sh=s.add.graphics().setDepth(-1e6+4.5);out.push(sh);
    for(let k=0;k<3;k++){const t=.2+k*.28,[p0x,p0y]=iso(mx-ax*.7,my-ay+ay*2*t),[p1x,p1y]=iso(mx+ax*.2,my-ay+ay*2*t);sh.lineStyle(1.6,0xffffff,.55).lineBetween(p0x,p0y-3,p1x,p1y-3);}
    s.tweens.add({targets:sh,alpha:{from:.15,to:.85},duration:1500+rand()*700,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
    const [rx,ry]=iso(mx,my),ring=s.add.ellipse(rx,ry-3,14,7,0xffffff,0).setStrokeStyle(1.5,0xffffff,.7).setDepth(-1e6+4.6);out.push(ring);
    s.tweens.add({targets:ring,scale:{from:.5,to:1.8},alpha:{from:1,to:0},duration:2200,repeat:-1,delay:rand()*1500});}
  if(fx.fire){const [a,b,z]=at(fx.fire),f=s.add.graphics().setPosition(a,b-z).setDepth(front-3);out.push(f);
    f.fillStyle(0xff9a3a,.95).fillTriangle(-4,0,4,0,0,-12);f.fillStyle(0xffe08a,1).fillTriangle(-2,0,2,0,0,-7);
    s.tweens.add({targets:f,scaleY:{from:.75,to:1.3},scaleX:{from:1.1,to:.85},duration:240+rand()*120,yoyo:true,repeat:-1});
    const glow=s.add.ellipse(a,b-z,40,20,0xffb35a,.22).setDepth(-1e6+4.7);out.push(glow);s.tweens.add({targets:glow,alpha:{from:.12,to:.3},duration:500,yoyo:true,repeat:-1});}
  if(fx.jet){const [a,b,z]=at(fx.jet),j=s.add.ellipse(a,b-z+6,5,16,0xffffff,.85).setDepth(front-3);out.push(j);
    s.tweens.add({targets:j,scaleY:{from:.6,to:1.3},alpha:{from:.6,to:.95},duration:650,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});}
  if(fx.fall){const [a,b,z]=at(fx.fall);for(let k=0;k<3;k++){const d=s.add.ellipse(a+(k-1)*6,b-z,12,6,0xffffff,.8).setDepth(front-3);out.push(d);
    s.tweens.add({targets:d,scale:{from:.6,to:1.6},alpha:{from:.9,to:0},duration:1400,repeat:-1,delay:k*460});}}
  if(fx.glow){const [a,b,z]=at(fx.glow),l=s.add.ellipse(a,b-z,34,34,0xffe7a0,.35).setDepth(front-2).setVisible(false);out.push(l);lights.push(l);
    s.tweens.add({targets:l,scale:{from:.9,to:1.12},duration:1800,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});}
  return {objects:out,lights};
}
