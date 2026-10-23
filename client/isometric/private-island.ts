import Phaser from 'phaser';
// @ts-ignore The illustrated atlas adapter preserves the game's actual wardrobe.
import {getCharacterStamp} from '/js/isometric/character-art.js';
import {paintPlot,type BuiltItem} from './island-builds';
import {paintDecor,type DecorItem} from './island-decor';

/** 🏝️ Đảo riêng on the new interface: one private island (public/js/island-layout.js) drawn isometrically.
 * The scene controller (public/js/v4/island-scene.js) owns walking, the live room and the overlays (names, bubbles);
 * this only paints: the sea, the coast, the villa, palms, the island's own art, the people and the boat or plane that
 * brought them. Map positions are fractions of the island's square (x east, y south), as on the old interface.
 * 🏗️ setBuilds(): what stands on the island (island-builds.ts), painted again when it changes. 🏝️ setLayout(): the island
 * at its size with its decorations (public/js/island-layout.js withDesign; island-decor.ts), painted again when it
 * changes; the sea moves, the waves break on the beach, gulls fly over, crabs walk the sand, the light follows the hour
 * of the day in Vietnam (lamps lit after dark). */
type Pt=[number,number];
type Facing='se'|'sw'|'ne'|'nw';
interface Rect {x:number;y:number;w:number;h:number}
export interface IslandLayout {
  sea:string;deep:string;sand:string;grass:string;grassDark:string;rock?:string;shore:Pt[];sandWidth:number;palms:Pt[];
  villa:Rect&{floors:number;roof:string;wall:string};dock:Rect;pad:{x:number;y:number;kind:string};
  spots:Array<{id:string;emoji:string;x:number;y:number;build?:unknown}>;deco:Array<{t:string;x:number;y:number;r?:number;w?:number;h?:number}>;walk?:Rect[];
  plots?:Array<[number,number,number]>;
  bounds?:[number,number];decor?:DecorItem[];tier?:number;paths?:boolean;
}
export interface IslandPerson {id:string;x:number;y:number;look:any;gender:string;dir:Facing;walking:boolean;pose?:string;hidden?:boolean}
export interface IslandFrame {people:IslandPerson[];vehicle?:{kind:string;big?:boolean;x:number;y:number;lift:number;dir:number}|null;focus?:Pt|null}

const N=14,HW=40,HH=20,SCALE=.6,FOOT=156;
const iso=(x:number,y:number):Pt=>[(x-y)*N*HW,(x+y)*N*HH];
const hex=(s:string|undefined,f=0x888888)=>s&&/^#[0-9a-f]{6}$/i.test(s)?parseInt(s.slice(1),16):f;
const shade=(c:number,k:number)=>{const r=Math.min(255,Math.round(((c>>16)&255)*k)),g=Math.min(255,Math.round(((c>>8)&255)*k)),b=Math.min(255,Math.round((c&255)*k));return (r<<16)|(g<<8)|b;};
const pts=(list:Pt[],dx=0,dy=0)=>list.map(([x,y])=>{const [a,b]=iso(x,y);return new Phaser.Geom.Point(a-dx,b-dy);});
/** The coast pulled in toward its middle by `by` (the grass inside the beach). */
function inset(shore:Pt[],by:number):Pt[]{
  const cx=shore.reduce((s,p)=>s+p[0],0)/shore.length,cy=shore.reduce((s,p)=>s+p[1],0)/shore.length;
  return shore.map(([x,y])=>{const d=Math.hypot(x-cx,y-cy)||1,k=Math.max(0,1-by/d);return [cx+(x-cx)*k,cy+(y-cy)*k] as Pt;});
}
/** A tiny seeded random, so every visit paints the same grass and waves. */
function seeded(seed:number){let s=seed>>>0||1;return ()=>((s=Math.imul(s^(s>>>15),2246822507)^Math.imul(s^(s>>>13),3266489909))>>>0)/4294967296;}

export class PrivateIslandRenderer {
  readonly ready:Promise<void>;
  private engine:Phaser.Game;
  private scene:Phaser.Scene|null=null;
  private layout:IslandLayout;
  private actors=new Map<string,{image:Phaser.GameObjects.Image;ripple:Phaser.GameObjects.Ellipse;key:string}>();
  private textures=new Map<string,string>();
  private revision=0;
  private vehicle:Phaser.GameObjects.Container|null=null;
  private rotor:Phaser.GameObjects.Graphics|null=null;
  private latest:IslandFrame={people:[]};
  private canvas:HTMLCanvasElement;
  private destroyed=false;
  private resizeObserver:ResizeObserver|null=null;
  private plotArt:Phaser.GameObjects.GameObject[]=[];
  private built:BuiltItem[]|null=null;
  private builtKey='';
  private layoutKey='';
  private lights:Phaser.GameObjects.GameObject[]=[];
  private shadeRect:Phaser.GameObjects.Graphics|null=null;
  private hourAt=-1;
  private lightAt=0;
  /** Footpaths to draw (public/js/island-layout.js footpaths()), from the scene controller. */
  private paths:Pt[][]=[];

  constructor(canvas:HTMLCanvasElement,layout:IslandLayout){
    this.canvas=canvas;this.layout=layout;this.layoutKey=PrivateIslandRenderer.keyOf(layout,[]);
    const rect=canvas.getBoundingClientRect(),owner=this;
    let done:()=>void=()=>{};this.ready=new Promise(resolve=>{done=resolve;});
    this.engine=new Phaser.Game({type:Phaser.CANVAS,canvas,width:Math.round(rect.width)||375,height:Math.round(rect.height)||560,backgroundColor:layout.deep,
      audio:{noAudio:true},input:{keyboard:false,mouse:false,touch:false,gamepad:false},fps:{target:60,forceSetTimeOut:false},
      render:{antialias:true,roundPixels:false,pixelArt:false},scale:{mode:Phaser.Scale.NONE,autoCenter:Phaser.Scale.NO_CENTER},
      scene:{key:'private-island',create(this:Phaser.Scene){owner.scene=this;owner.paint();owner.resize();done();},update(this:Phaser.Scene){owner.tick(this.time.now);}}});
    if(typeof ResizeObserver==='function'){this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(canvas.parentElement||canvas);}
  }

  /** 🏗️ What stands on the island now (public/js/island-layout.js withBuilds().built): painted again only when it changed. */
  setBuilds(built:BuiltItem[]){
    const key=JSON.stringify(built.map(b=>[b.plot,b.kind,b.look||0,b.level,b.work,b.next,b.x,b.y,b.r||0]));
    if(key===this.builtKey&&this.built)return;
    this.builtKey=key;this.built=built;if(this.scene)this.paintPlots();
  }
  /** 🏝️ The island at its size with its decorations (withDesign) and its footpaths: everything but the people and the
   * vehicle painted again when it changed. */
  private static keyOf(layout:IslandLayout,paths:Pt[][]){return JSON.stringify([layout.tier||0,layout.shore[0],(layout.decor||[]).map(d=>[d.id,d.kind,d.x,d.y,d.r]),paths.map(p=>p.length)]);}
  setLayout(layout:IslandLayout,paths:Pt[][]=[]){
    const key=PrivateIslandRenderer.keyOf(layout,paths);
    this.layout=layout;this.paths=paths;
    if(key===this.layoutKey)return;this.layoutKey=key;
    const s=this.scene;if(!s||this.destroyed)return;
    const keep=new Set<Phaser.GameObjects.GameObject>();for(const a of this.actors.values()){keep.add(a.image);keep.add(a.ripple);}
    if(this.vehicle)keep.add(this.vehicle);
    for(const o of [...s.children.list])if(!keep.has(o)){s.tweens.killTweensOf?.(o);o.destroy();}
    this.plotArt=[];this.lights=[];this.shadeRect=null;this.hourAt=-1;
    this.paint(false);
  }
  private paintPlots(){
    const s=this.scene;if(!s||this.destroyed)return;
    for(const o of this.plotArt){s.tweens.killTweensOf?.(o);o.destroy();}this.plotArt=[];
    const rand=seeded((this.built||[]).length*131+7);
    for(const it of this.built||[])this.plotArt.push(...paintPlot(s,it,{x:it.x,y:it.y,coast:Boolean(it.coast)},rand));
  }

  /** The newest people and vehicle; Phaser draws them on its next tick. */
  frame(model:IslandFrame){this.latest=model;}

  /** A tap on the canvas → the map point under it, or null outside the map. */
  toMap(clientX:number,clientY:number):Pt|null{
    const cam=this.scene?.cameras.main;if(!cam)return null;
    const r=this.canvas.getBoundingClientRect(),w=cam.getWorldPoint(clientX-r.left,clientY-r.top);
    const a=w.x/(N*HW),b=w.y/(N*HH),x=(a+b)/2,y=(b-a)/2,[lo,hi]=this.layout.bounds||[0,1];
    return x>=lo-.1&&x<=hi+.1&&y>=lo-.1&&y<=hi+.1?[x,y]:null;
  }
  /** A map point → where it shows on the canvas (CSS pixels from its top left), `lift` pixels above the ground. */
  toScreen(x:number,y:number,lift=0):Pt|null{
    const cam=this.scene?.cameras.main;if(!cam)return null;
    const [wx,wy]=iso(x,y);
    return [(wx-cam.scrollX-cam.width/2)*cam.zoom+cam.width/2,(wy-lift-cam.scrollY-cam.height/2)*cam.zoom+cam.height/2];
  }
  /** How tall a person stands on screen (the overlays sit over the head). */
  get personHeight(){return 150*SCALE*(this.scene?.cameras.main.zoom||1);}

  resize(){
    if(this.destroyed)return;
    const r=this.canvas.getBoundingClientRect(),w=Math.max(1,Math.round(r.width)),h=Math.max(1,Math.round(r.height));
    const scale=this.engine?.scale;   // undefined while Phaser is still booting (create runs before the constructor returns)
    if(scale&&(scale.width!==w||scale.height!==h))scale.resize(w,h);
    const cam=this.scene?.cameras.main;if(!cam)return;
    cam.setSize(w,h);
    // The whole island on a wide screen; a phone follows the player at a size where faces still read.
    cam.setZoom(Math.max(.7,Math.min(1.1,Math.min(w/1180,h/640)*1.15)));
  }

  destroy(){
    if(this.destroyed)return;this.destroyed=true;
    this.resizeObserver?.disconnect();
    this.engine.destroy(false);
  }

  /* ---- painting --------------------------------------------------------------------------------------------- */
  private paint(centre=true){
    const s=this.scene!,L=this.layout,rand=seeded(L.shore.length*977+Math.round(L.villa.x*1000)),[lo,hi]=L.bounds||[0,1];
    const ground=s.add.graphics().setDepth(-1e6);
    // The sea: a lighter shelf around the island, sparkles and slow swell lines drifting.
    const pad=.45,sea=pts([[lo-pad,lo-pad],[hi+pad,lo-pad],[hi+pad,hi+pad],[lo-pad,hi+pad]]);
    ground.fillStyle(hex(L.deep),1).fillPoints(sea,true);
    ground.fillStyle(shade(hex(L.sea),.92),1).fillPoints(pts(inset(L.shore,-.16)),true);
    ground.fillStyle(hex(L.sea),1).fillPoints(pts(inset(L.shore,-.09)),true);
    const swell=s.add.graphics().setDepth(-1e6+1);swell.lineStyle(2,0xffffff,.35);
    for(let i=0;i<70;i++){const x=lo-.3+rand()*(hi-lo+.6),y=lo-.3+rand()*(hi-lo+.6);if(this.onLand(x,y,.05))continue;const [a,b]=iso(x,y);swell.beginPath();swell.arc(a,b,10+rand()*14,Math.PI*1.15,Math.PI*1.85);swell.strokePath();}
    s.tweens.add({targets:swell,alpha:{from:.45,to:1},duration:2200,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
    s.tweens.add({targets:swell,x:{from:-6,to:6},duration:5200,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
    for(const d of L.deco)if(d.t==='reef'){const [a,b]=iso(d.x,d.y),r=(d.r||.05)*N*HW;
      for(let i=0;i<9;i++){ground.fillStyle([0xff8a7a,0xffc56b,0xb48de0,0x7fd6c2][i%4],.75).fillEllipse(a+(rand()-.5)*r*1.6,b+(rand()-.5)*r*.8,r*.35+rand()*r*.3,r*.18+rand()*r*.15);}}
    // The coast: a sandy cliff edge, the beach, then grass.
    ground.fillStyle(shade(hex(L.sand),.72),1).fillPoints(pts(L.shore,0,-12),true);
    // 🌊 the surf: a white band breaking on the beach, coming and going
    const surf=s.add.graphics().setDepth(-1e6+2);surf.fillStyle(0xffffff,.6).fillPoints(pts(inset(L.shore,-.014)),true);
    s.tweens.add({targets:surf,alpha:{from:.35,to:.95},duration:2600,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
    const land=s.add.graphics().setDepth(-1e6+3);
    land.fillStyle(shade(hex(L.sand),.9),1).fillPoints(pts(L.shore),true);
    land.fillStyle(hex(L.sand),1).fillPoints(pts(inset(L.shore,.006)),true);
    const grass=inset(L.shore,L.sandWidth);
    land.fillStyle(hex(L.grassDark),1).fillPoints(pts(grass,0,-3),true);
    land.fillStyle(hex(L.grass),1).fillPoints(pts(grass),true);
    land.fillStyle(shade(hex(L.grass),1.06),.8).fillPoints(pts(inset(L.shore,L.sandWidth+.05)),true);
    for(let i=0;i<260;i++){const x=lo+rand()*(hi-lo),y=lo+rand()*(hi-lo);if(!this.inside(grass,x,y))continue;const [a,b]=iso(x,y);land.fillStyle(hex(L.grassDark),.5).fillEllipse(a,b,6+rand()*8,3+rand()*3);
      if(rand()<.18){land.fillStyle([0xffffff,0xffd25a,0xff8aa0][Math.floor(rand()*3)],.9).fillCircle(a+4,b-1,1.6);}}
    for(let i=0;i<60;i++){const x=lo+rand()*(hi-lo),y=lo+rand()*(hi-lo);if(!this.inside(L.shore,x,y)||this.inside(grass,x,y))continue;const [a,b]=iso(x,y);land.fillStyle(shade(hex(L.sand),.85),.6).fillEllipse(a,b,3,1.6);}
    // 🛤️ the footpaths (the owner's choice): sandy ways from the pier to the doors
    for(const [wd,color] of [[9,shade(hex(L.sand),.9)],[5,0xf4e6c4]] as Array<[number,number]>){land.lineStyle(wd,color,.9);
      for(const line of this.paths){const p=pts(line);if(p.length<2)continue;land.beginPath();land.moveTo(p[0].x,p[0].y);for(const q of p.slice(1))land.lineTo(q.x,q.y);land.strokePath();}}
    // Flat things on the ground: piers, the runway, the pool, the helipad.
    const top=s.add.graphics().setDepth(-1e6+3.5);
    for(const r of [L.dock,...(L.walk||[])])this.planks(top,r);
    for(const d of L.deco){
      if(d.t==='strip'){const r={x:d.x,y:d.y,w:d.w||.5,h:d.h||.06};top.fillStyle(0x5d5a5f,1).fillPoints(this.rect(r),true);
        top.lineStyle(3,0xffffff,.9);for(let k=-.45;k<.45;k+=.08){const [a,b]=iso(r.x+r.w*k,r.y),[c,e]=iso(r.x+r.w*(k+.04),r.y);top.lineBetween(a,b,c,e);}}
      if(d.t==='pool'){const r={x:d.x,y:d.y,w:d.w||.14,h:d.h||.06};top.fillStyle(0xf4efe6,1).fillPoints(this.rect({...r,w:r.w+.015,h:r.h+.015}),true);top.fillStyle(0x47b7d8,1).fillPoints(this.rect(r),true);
        top.fillStyle(0xffffff,.35).fillPoints(this.rect({...r,y:r.y-r.h*.2,h:r.h*.2}),true);}
    }
    if(L.pad.kind==='heli'){const [a,b]=iso(L.pad.x,L.pad.y);top.fillStyle(0x6b6f74,1).fillEllipse(a,b,96,48);top.lineStyle(3,0xffd75a,1).strokeEllipse(a,b,80,40);
      top.lineStyle(5,0xffffff,1);top.lineBetween(a-12,b-9,a-12,b+9);top.lineBetween(a+12,b-9,a+12,b+9);top.lineBetween(a-12,b,a+12,b);}
    // Standing things, sorted by where they touch the ground.
    for(const d of L.deco){
      if(d.t==='peak')this.peak(d.x,d.y,d.r||.12);
      else if(d.t==='rocks')this.rocks(d.x,d.y,rand);
      else if(d.t==='hut')this.box(d.x,d.y,.05,.04,26,0xc9a77a,0x9b6a3c,14);
      else if(d.t==='lighthouse')this.lighthouse(d.x,d.y);
      else if(d.t==='steam')this.steam(d.x,d.y);
    }
    const v=L.villa;this.box(v.x,v.y,v.w,v.h,34*v.floors,hex(v.wall),hex(v.roof),26,v.floors);
    for(const [x,y] of L.palms)this.palm(x,y,rand);
    this.paintPlots();
    // 🏝️ the decorations, then life around: gulls over the sea, crabs on the sand
    const drand=seeded((L.decor||[]).length*313+11);
    for(const it of L.decor||[])this.lights.push(...paintDecor(s,it,drand).lights);
    this.ambient(rand);
    for(const sp of L.spots){if(sp.build||(sp as {decor?:unknown}).decor)continue;const [a,b]=iso(sp.x,sp.y);
      const ring=s.add.ellipse(a,b,46,22,0xffffff,.28).setStrokeStyle(2,0xffffff,.8).setDepth(b-2);
      const icon=s.add.text(a,b-30,sp.emoji,{fontSize:'26px'}).setOrigin(.5,1).setDepth(b+1);
      s.tweens.add({targets:icon,y:b-38,duration:1400+rand()*500,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});void ring;}
    if(centre){const [cx,cy]=iso(L.villa.x,L.villa.y+L.villa.h);s.cameras.main.centerOn(cx,cy);}
    this.daylight(true);
  }
  /** Gulls gliding over the sea, crabs scuttling along the beach (a few: cheap on a phone). */
  private ambient(rand:()=>number){
    const s=this.scene!,L=this.layout,[lo,hi]=L.bounds||[0,1];
    for(let i=0;i<3;i++){
      const y0=lo+.1+rand()*(hi-lo-.2),[a,b]=iso(lo-.3,y0),[c,d]=iso(hi+.3,y0+(rand()-.5)*.3),g=s.add.graphics().setDepth(1e6),up=260+rand()*120;
      g.lineStyle(2,0xffffff,.95);g.beginPath();g.moveTo(-7,0);g.lineTo(-2,-4);g.lineTo(0,-1);g.lineTo(2,-4);g.lineTo(7,0);g.strokePath();
      g.setPosition(a,b-up);
      s.tweens.add({targets:g,x:c,y:d-up,duration:26000+rand()*14000,repeat:-1,delay:rand()*9000});
      s.tweens.add({targets:g,scaleY:{from:1,to:.4},duration:420,yoyo:true,repeat:-1});
    }
    const beach=inset(L.shore,L.sandWidth*.45);
    for(let i=0;i<3;i++){
      const k=Math.floor(rand()*beach.length),p0=beach[k],p1=beach[(k+2)%beach.length],[a,b]=iso(p0[0],p0[1]),[c,d]=iso(p1[0],p1[1]);
      const crab=s.add.graphics().setPosition(a,b).setDepth(b);crab.fillStyle(0xd9483b,1).fillEllipse(0,-3,9,5);crab.fillStyle(0xb5352b,1).fillCircle(-5,-5,1.6).fillCircle(5,-5,1.6);
      crab.lineStyle(1,0xb5352b,1).lineBetween(-4,-1,-7,1).lineBetween(4,-1,7,1);
      s.tweens.add({targets:crab,x:c,y:d,duration:9000+rand()*6000,yoyo:true,repeat:-1,ease:'Sine.easeInOut',hold:2500,repeatDelay:3000,onUpdate:()=>{crab.setDepth(crab.y);}});
    }
  }
  /** ☀️ The light of the hour in Vietnam (UTC+7): a warm dawn, plain day, a golden evening, a blue night with lamps lit. */
  private daylight(force=false){
    const s=this.scene;if(!s||this.destroyed)return;
    const h=(new Date().getUTCHours()+7)%24;if(!force&&h===this.hourAt)return;this.hourAt=h;
    const [color,alpha]=h>=19||h<5?[0x1d2b5e,.3]:h>=17?[0xff8a3d,.13]:h<7?[0xffc58a,.1]:[0xffffff,0];
    if(!this.shadeRect)this.shadeRect=s.add.graphics().setScrollFactor(0).setDepth(2e6);
    const cam=s.cameras?.main,w=(cam?.width||800)/(cam?.zoom||1),hh=(cam?.height||600)/(cam?.zoom||1);
    this.shadeRect.clear();if(alpha>0)this.shadeRect.fillStyle(color,alpha).fillRect(-w/2-40,-hh/2-40,w*2+80,hh*2+80);
    this.shadeRect.setVisible(alpha>0);
    const night=h>=18||h<6;for(const l of this.lights)(l as Phaser.GameObjects.Ellipse).setVisible(night);
  }
  private inside(poly:Pt[],x:number,y:number){let r=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const [ax,ay]=poly[i],[bx,by]=poly[j];if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)r=!r;}return r;}
  private onLand(x:number,y:number,margin:number){return this.inside(inset(this.layout.shore,-margin),x,y);}
  private rect(r:Rect,lift=0){return pts([[r.x-r.w/2,r.y-r.h/2],[r.x+r.w/2,r.y-r.h/2],[r.x+r.w/2,r.y+r.h/2],[r.x-r.w/2,r.y+r.h/2]],0,lift);}
  private planks(g:Phaser.GameObjects.Graphics,r:Rect){
    g.fillStyle(0x6e4a2e,1).fillPoints(this.rect(r,-8),true);g.fillStyle(0xb5844f,1).fillPoints(this.rect(r),true);
    g.lineStyle(1.5,0x8b6038,.8);const long=r.h>r.w;
    for(let k=1;k<12;k++){const t=-.5+k/12;const [a,b]=long?iso(r.x-r.w/2,r.y+r.h*t):iso(r.x+r.w*t,r.y-r.h/2),[c,e]=long?iso(r.x+r.w/2,r.y+r.h*t):iso(r.x+r.w*t,r.y+r.h/2);g.lineBetween(a,b,c,e);}
  }
  /** A house: an isometric box with windows per floor and a hipped roof, sorted by its front corner. */
  private box(x:number,y:number,w:number,h:number,height:number,wall:number,roof:number,roofH:number,floors=1){
    const s=this.scene!,[ox,oy]=iso(x+w/2,y+h/2),g=s.add.graphics().setDepth(oy);g.setPosition(ox,oy);
    const p=(px:number,py:number,z=0)=>{const [a,b]=iso(px,py);return new Phaser.Geom.Point(a-ox,b-oy-z);};
    const Nw=p(x-w/2,y-h/2),E=p(x+w/2,y-h/2),S=p(x+w/2,y+h/2),W=p(x-w/2,y+h/2),up=(q:Phaser.Geom.Point)=>new Phaser.Geom.Point(q.x,q.y-height);
    g.fillStyle(0x000000,.16).fillEllipse(0,-((S.y-Nw.y)/2)+6,(E.x-W.x)*1.1,(S.y-Nw.y)*1.1);
    g.fillStyle(shade(wall,.82),1).fillPoints([W,S,up(S),up(W)],true);
    g.fillStyle(wall,1).fillPoints([S,E,up(E),up(S)],true);
    const win=(a:Phaser.Geom.Point,b:Phaser.Geom.Point,f:number,t:number,lit:number)=>{const fl=height/floors,z0=f*fl+fl*.35,z1=f*fl+fl*.75,q=(k:number,z:number)=>new Phaser.Geom.Point(a.x+(b.x-a.x)*k,a.y+(b.y-a.y)*k-z);
      g.fillStyle(lit,1).fillPoints([q(t,z0),q(t+.12,z0),q(t+.12,z1),q(t,z1)],true);};
    for(let f=0;f<floors;f++)for(const t of [.15,.45,.73]){win(W,S,f,t,0x8fc6dc);if(!(f===0&&t===.45))win(S,E,f,t,0xa8d6e8);}
    const door=(k:number,z:number)=>new Phaser.Geom.Point(S.x+(E.x-S.x)*k,S.y+(E.y-S.y)*k-z);
    g.fillStyle(0x7a4b2a,1).fillPoints([door(.43,0),door(.57,0),door(.57,height/floors*.7),door(.43,height/floors*.7)],true);
    const apex=new Phaser.Geom.Point((Nw.x+S.x)/2,(Nw.y+S.y)/2-height-roofH);
    g.fillStyle(shade(roof,.78),1).fillPoints([up(W),up(S),apex],true);g.fillStyle(roof,1).fillPoints([up(S),up(E),apex],true);
    g.fillStyle(shade(roof,.9),1).fillPoints([up(Nw),up(W),apex],true);g.lineStyle(2,shade(roof,.6),1).lineBetween(up(S).x,up(S).y,apex.x,apex.y);
  }
  private palm(x:number,y:number,rand:()=>number){
    const s=this.scene!,[a,b]=iso(x,y),g=s.add.graphics().setDepth(b).setPosition(a,b),lean=(rand()-.5)*30,h=88+rand()*26;
    g.fillStyle(0x000000,.15).fillEllipse(lean*.4+18,4,50,16);
    g.lineStyle(9,0x8a6340,1);const top=new Phaser.Geom.Point(lean,-h);
    g.beginPath();g.moveTo(0,0);for(let k=1;k<=8;k++){const t=k/8;g.lineTo(lean*t*t,-h*t);}g.strokePath();
    for(let k=0;k<7;k++){const ang=k/7*Math.PI*2,len=40+rand()*10;g.fillStyle(k%2?0x3f8a3e:0x4fa04a,1);
      g.fillTriangle(top.x,top.y,top.x+Math.cos(ang)*len,top.y+Math.sin(ang)*len*.55+12,top.x+Math.cos(ang+.35)*len*.7,top.y+Math.sin(ang+.35)*len*.4+6);}
    g.fillStyle(0x7a5a32,1).fillCircle(top.x-4,top.y+6,5).fillCircle(top.x+5,top.y+7,5);
    s.tweens.add({targets:g,angle:{from:-1.2,to:1.2},duration:2600+rand()*1200,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
  }
  private peak(x:number,y:number,r:number){
    const s=this.scene!,[a,b]=iso(x,y+r*.5),g=s.add.graphics().setDepth(b).setPosition(a,b),wd=r*N*HW*1.1,ht=r*N*HW*1.3,rock=hex(this.layout.rock,0x5d5560);
    g.fillStyle(shade(rock,.8),1).fillTriangle(-wd,0,0,-ht,wd*.1,10);g.fillStyle(rock,1).fillTriangle(wd*.1,10,0,-ht,wd,0);
    g.fillStyle(0xf5f2ee,1).fillTriangle(-wd*.22,-ht*.78,0,-ht,wd*.24,-ht*.76);g.fillStyle(0xe2ded8,1).fillTriangle(-wd*.08,-ht*.72,0,-ht,wd*.24,-ht*.76);
  }
  private rocks(x:number,y:number,rand:()=>number){
    const s=this.scene!,[a,b]=iso(x,y),g=s.add.graphics().setDepth(b).setPosition(a,b),rock=hex(this.layout.rock,0x6f6a70);
    for(let k=0;k<4;k++){const rx=(rand()-.5)*60,ry=(rand()-.5)*20,w=22+rand()*20;g.fillStyle(shade(rock,.85+k*.06),1).fillEllipse(rx,ry-w*.25,w,w*.7);}
  }
  private lighthouse(x:number,y:number){
    const s=this.scene!,[a,b]=iso(x,y),g=s.add.graphics().setDepth(b).setPosition(a,b);
    g.fillStyle(0x000000,.18).fillEllipse(14,4,52,16);
    for(let k=0;k<5;k++){g.fillStyle(k%2?0xd9483b:0xfaf6ee,1).fillRect(-14+k*1.5,-30-k*30,28-k*3,31);}
    g.fillStyle(0x34383f,1).fillRect(-12,-188,24,10);g.fillStyle(0xffe17a,1).fillRect(-9,-176+0,18,14);
    const beam=s.add.graphics().setDepth(b+1).setPosition(a,b-170);beam.fillStyle(0xfff3b0,.35).fillTriangle(0,0,140,-22,140,22);
    s.tweens.add({targets:beam,angle:360,duration:7000,repeat:-1});
  }
  private steam(x:number,y:number){
    const s=this.scene!,[a,b]=iso(x,y);
    for(let k=0;k<3;k++){const c=s.add.ellipse(a+(k-1)*14,b-10,26,18,0xffffff,.5).setDepth(b+2);
      s.tweens.add({targets:c,y:b-70,alpha:0,scale:1.8,duration:2600,delay:k*850,repeat:-1});}
  }

  /* ---- people and the vehicle ---------------------------------------------------------------------------------- */
  private texture(p:IslandPerson,frame:number){
    const id=JSON.stringify([p.look,p.gender,p.dir,frame,this.revision]);let key=this.textures.get(id);
    if(key&&this.scene!.textures.exists(key))return key;
    key='pi-'+this.textures.size+'-'+this.revision;
    const stamp=getCharacterStamp({look:p.look,gender:p.gender,direction:p.dir,walkFrame:frame,onReady:()=>{this.revision++;}});
    const t=this.scene!.textures.create(key,stamp.canvas);
    if(t){t.add('__BASE',0,0,0,stamp.canvas.width,stamp.canvas.height);t.setFilter(Phaser.Textures.FilterMode.LINEAR);}
    this.textures.set(id,key);return key;
  }
  private tick(now:number){
    const s=this.scene;if(!s||this.destroyed)return;
    const seen=new Set<string>(),frame=this.latest;
    for(const p of frame.people){
      seen.add(p.id);let a=this.actors.get(p.id);
      const walk=p.walking?1+Math.floor(now/140)%2:0,key=this.texture(p,walk);
      if(!a){const ripple=s.add.ellipse(0,0,64,22,0xffffff,.55).setVisible(false);a={image:s.add.image(0,0,key).setOrigin(.5,FOOT/160).setScale(SCALE),ripple,key};this.actors.set(p.id,a);}
      if(a.key!==key){a.image.setTexture(key);a.key=key;}
      const [x,y]=iso(p.x,p.y),swim=p.pose==='swim';
      a.image.setVisible(!p.hidden).setPosition(x,y+(swim?52:0)).setDepth(y+.5);
      if(swim)a.image.setCrop(0,0,120,104);else a.image.setCrop();
      a.ripple.setVisible(swim&&!p.hidden).setPosition(x,y).setDepth(y+.6);
    }
    for(const [id,a] of this.actors)if(!seen.has(id)){a.image.destroy();a.ripple.destroy();this.actors.delete(id);}
    this.drawVehicle(frame.vehicle||null,now);
    if(!this.lightAt||now-this.lightAt>60000){this.lightAt=now;this.daylight();}
    const cam=s.cameras.main,focus=frame.focus;
    if(focus){const [fx,fy]=iso(focus[0],focus[1]);const tx=fx,ty=fy-40,mx=cam.scrollX+cam.width/2,my=cam.scrollY+cam.height/2;
      const k=Math.abs(tx-mx)+Math.abs(ty-my)>900?1:.12;cam.centerOn(mx+(tx-mx)*k,my+(ty-my)*k);}
  }
  private drawVehicle(v:IslandFrame['vehicle'],now:number){
    const s=this.scene!;
    if(!v){this.vehicle?.setVisible(false);return;}
    if(!this.vehicle||this.vehicle.getData('kind')!==v.kind+(v.big?'+':'')){
      this.vehicle?.destroy();const g=s.add.graphics(),c=s.add.container(0,0,[g]);c.setData('kind',v.kind+(v.big?'+':''));this.vehicle=c;this.rotor=null;
      const k=v.big?1.35:1;
      if(v.kind==='heli'){
        g.fillStyle(0x000000,.18).fillEllipse(0,0,90*k,30*k);
        const body=s.add.graphics();body.fillStyle(0x2f4f7a,1).fillEllipse(0,-34*k,70*k,34*k);body.fillStyle(0x9fd3ea,1).fillEllipse(18*k,-38*k,26*k,18*k);
        body.fillStyle(0x2f4f7a,1).fillRect(-70*k,-38*k,40*k,7*k);body.fillStyle(0x3a3a3a,1).fillRect(-28*k,-14*k,56*k,4*k);
        const rotor=s.add.graphics();rotor.lineStyle(4,0x2a2a2a,.85).lineBetween(-70*k,0,70*k,0);rotor.setPosition(0,-54*k);
        c.add([body,rotor]);this.rotor=rotor;c.setData('lift',body);
      }else if(v.kind==='plane'){
        g.fillStyle(0x000000,.16).fillEllipse(0,0,150*k,30*k);
        const body=s.add.graphics();body.fillStyle(0xf3f4f6,1).fillEllipse(0,-26*k,150*k,26*k);body.fillStyle(0xd9dde3,1).fillTriangle(-20*k,-24*k,30*k,-24*k,-10*k,6*k);
        body.fillStyle(0xd9dde3,1).fillTriangle(-20*k,-28*k,30*k,-28*k,-6*k,-60*k);body.fillStyle(0xc0392b,1).fillTriangle(-74*k,-30*k,-56*k,-30*k,-72*k,-62*k);
        body.fillStyle(0x4a6d8c,1);for(let i=0;i<6;i++)body.fillCircle(-36*k+i*14*k,-30*k,3*k);
        c.add(body);c.setData('lift',body);
      }else{
        const hull=v.kind==='solo'?.7:k;
        g.fillStyle(0xffffff,.45).fillEllipse(0,4,130*hull,30*hull);
        const body=s.add.graphics();body.fillStyle(0xffffff,1).fillPoints([new Phaser.Geom.Point(-62*hull,-6*hull),new Phaser.Geom.Point(62*hull,-12*hull),new Phaser.Geom.Point(46*hull,10*hull),new Phaser.Geom.Point(-54*hull,10*hull)],true);
        body.fillStyle(0x24507a,1).fillRect(-54*hull,4*hull,100*hull,5*hull);
        if(v.kind==='solo'){body.fillStyle(0xd9a25a,1).fillRect(-30*hull,-14*hull,40*hull,8*hull);}
        else{body.fillStyle(0xeef3f7,1).fillRect(-30*hull,-30*hull,56*hull,22*hull);body.fillStyle(0x3d6f96,1).fillRect(-24*hull,-26*hull,44*hull,8*hull);
          if(!v.big){body.lineStyle(3,0x6b5130,1).lineBetween(-4*hull,-30*hull,-4*hull,-96*hull);body.fillStyle(0xfdfaf2,1).fillTriangle(-2*hull,-94*hull,-2*hull,-34*hull,40*hull,-36*hull);}}
        c.add(body);c.setData('lift',body);
      }
    }
    const [x,y]=iso(v.x,v.y),c=this.vehicle;c.setVisible(true).setPosition(x,y).setDepth(y+.2).setScale(v.dir<0?-1:1,1);
    const body=c.getData('lift') as Phaser.GameObjects.Graphics|undefined;if(body)body.y=-v.lift;
    if(this.rotor){this.rotor.y=-54*(v.big?1.35:1)-v.lift;this.rotor.scaleX=Math.cos(now/40);}
    if(v.kind==='boat'||v.kind==='solo')c.angle=Math.sin(now/700)*1.5;
  }
}
