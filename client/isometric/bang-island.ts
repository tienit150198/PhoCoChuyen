import Phaser from 'phaser';
// @ts-ignore The illustrated atlas adapter preserves the game's actual wardrobe.
import {getCharacterStamp} from '/js/isometric/character-art.js';
// @ts-ignore a plain module shared with the old interface (bundled in: a relative path)
import {HOUSES,paintHouse,houseTop,DECOR,paintDecor} from '../../public/js/house-art.js';

/** ⚔️ Đảo bang on the new interface: a bang's island (public/js/bang-island-layout.js) drawn isometrically, in the
 * private islands' style (client/isometric/private-island.ts: sea, coast, sand, grass, palms, the pier) but bigger,
 * with the seven facilities on their fixed slots. Each facility has its own look per level band (1: levels 1–3 wood,
 * 2: 4–6 stone, 3: 7–10 gold), bamboo scaffolding while it is being built, and an empty staked plot before level 1.
 * The bang's colour flies on the gate, the hall, the arena and the bang's own boat; its emoji hangs on the banners.
 * The scene controller (public/js/v4/bang-island-scene.js) owns walking, the live room, the overlays and the panels;
 * this only paints. Static art is baked into textures once (the canvas renderer would replay every shape each
 * frame); only flags, flames, glows, palms and people move. Map positions are fractions of the island's square.
 * 🏝️ The island's level (21/10) is the layout's (public/js/bang-island-layout.js layout(level, building)): its coast
 * with the zones' capes, their plots (🥋 a sparring ring, 🍵 a tea pavilion over a koi pond, 🛕 a five-roof pagoda,
 * 🗼 a lighthouse), gold lanterns at level 5, and while the next level is built its raw sand bank with stakes,
 * scaffolding and a crane (`site`).
 * 🏯 20/10 (game/bang_extra.py): the hall may wear a house style (public/js/house-art.js, `bang.hall`), and the bang's
 * decorations (`bang.decor`) stand on their spots (layout.decorAt), drawn with the same models through houseView(). */
type Pt=[number,number];
type Facing='se'|'sw'|'ne'|'nw';
interface Rect {x:number;y:number;w:number;h:number}
export interface BangIslandLayout {
  size:number;sea:string;deep:string;sand:string;grass:string;grassDark:string;stone:string;stoneDark:string;
  shore:Pt[];sandWidth:number;plaza:{c:Pt;r:number};roads:Pt[][];dock:Pt[];gate:{a:number;b:number;half:number;post:number};
  slots:Record<string,Rect&{id:string;solid:boolean;door:Pt}>;plots:Array<Rect&{id:string;kind:string}>;
  spots:Array<{id:string;emoji:string;x:number;y:number}>;palms:Pt[];trees:Pt[];
  level?:number;lamps?:Pt[];site?:Rect&{id:string;kind:string;level:number;shore:Pt[]};
  decorAt?:Record<string,Pt[]>;hallArt?:{scale:number;level:(hall:number)=>number};
}
export interface BangFacilityLook {id:string;level:number;band?:number;state:string}
export interface BangLook {name:string;emoji:string;color:string;facilities:BangFacilityLook[];hall?:{style:string;look:number};decor?:string[]}
export interface BangPerson {id:string;x:number;y:number;look:any;gender:string;dir:Facing;walking:boolean;pose?:string|null;hidden?:boolean}
export interface BangFrame {people:BangPerson[];focus?:Pt|null;shift?:number}   // shift: CSS px to show the focus higher (a panel covers the bottom)

const HW=40,HH=20,SCALE=.6,FOOT=156,R2=Math.SQRT1_2,PAD=6;
const hex=(s:string|undefined,f=0x888888)=>s&&/^#[0-9a-f]{6}$/i.test(s)?parseInt(s.slice(1),16):f;
const shade=(c:number,k:number)=>{const r=Math.min(255,Math.round(((c>>16)&255)*k)),g=Math.min(255,Math.round(((c>>8)&255)*k)),b=Math.min(255,Math.round((c&255)*k));return (r<<16)|(g<<8)|b;};
const bandOf=(level:number)=>level<=0?0:level<=3?1:level<=6?2:3;
const atScreen=(a:number,b:number):Pt=>[.5+(a+b)*R2,.5+(b-a)*R2];
const known=(table:unknown,id:string|undefined)=>Boolean(id&&(table as Record<string,unknown>)[id]);
function seeded(seed:number){let s=seed>>>0||1;return ()=>((s=Math.imul(s^(s>>>15),2246822507)^Math.imul(s^(s>>>13),3266489909))>>>0)/4294967296;}
function inset(shore:Pt[],by:number):Pt[]{
  const cx=shore.reduce((s,p)=>s+p[0],0)/shore.length,cy=shore.reduce((s,p)=>s+p[1],0)/shore.length;
  return shore.map(([x,y])=>{const d=Math.hypot(x-cx,y-cy)||1,k=Math.max(0,1-by/d);return [cx+(x-cx)*k,cy+(y-cy)*k] as Pt;});
}
function inside(poly:Pt[],x:number,y:number){let r=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const [ax,ay]=poly[i],[bx,by]=poly[j];if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)r=!r;}return r;}
const sub=(r:Rect,k:number,kh=k):Rect=>({x:r.x,y:r.y,w:r.w*k,h:r.h*kh});
/** Where the hall's banner hangs per band (the bang's emoji is drawn on it): walls scale k, along the south-west face at t. */
const HALL_BANNER=[{k:.7,t:.2,z0:14,z1:54},{k:.7,t:.2,z0:14,z1:54},{k:.72,t:.18,z0:22,z1:70},{k:.78,t:.15,z0:28,z1:86}];

// The palette: wood, thatch, tiles, stone, lacquer, gold.
const C={wood:0x9a6a3c,woodD:0x6e4a2a,thatch:0xd6ad55,tile:0xb04a35,tileD:0x86362a,blueTile:0x3f6f9e,stone:0xd3cab8,stoneD:0x9f9584,
  marble:0xf4efe4,lacq:0xa3242a,red:0xc8312f,gold:0xe7b726,goldD:0xb68714,jade:0x2f6d55,cream:0xf2e4c4,iron:0x3d3e46,crate:0xc99a58,
  bamboo:0xc9a75c,bambooD:0x8f7238,net:0x3f9b5a,dirt:0xc6a06a,sandFloor:0xe6cf98,field:0x8fcd68,white:0xfbf7ee,ink:0x3b2a1d};

/** A drawing in local pixels around an anchor (a map point at height 0), measured first, then baked into one
 * texture. Every shape goes through p() so the same function draws the measuring pass and the real one. */
class Kit {
  g:Phaser.GameObjects.Graphics|null;minX=1e9;minY=1e9;maxX=-1e9;maxY=-1e9;dx=0;dy=0;top=0;
  constructor(readonly iso:(x:number,y:number)=>Pt,readonly ax:number,readonly ay:number,g:Phaser.GameObjects.Graphics|null){this.g=g;}
  private grow(x:number,y:number){if(x<this.minX)this.minX=x;if(x>this.maxX)this.maxX=x;if(y<this.minY)this.minY=y;if(y>this.maxY)this.maxY=y;}
  /** A map point at height z → local pixels (and the bounds grow). */
  p(x:number,y:number,z=0):Phaser.Geom.Point{const [a,b]=this.iso(x,y),lx=a-this.ax,ly=b-this.ay-z;this.grow(lx,ly);if(z>this.top)this.top=z;return new Phaser.Geom.Point(lx+this.dx,ly+this.dy);}
  /** Local pixels straight (for screen-aligned bits: a beam, a flag), relative to a map point at height z. */
  s(x:number,y:number,z:number,ox:number,oy:number):Phaser.Geom.Point{const q=this.p(x,y,z);const lx=q.x-this.dx+ox,ly=q.y-this.dy+oy;this.grow(lx,ly);return new Phaser.Geom.Point(lx+this.dx,ly+this.dy);}
  poly(points:Phaser.Geom.Point[],color:number,alpha=1){for(const q of points)this.grow(q.x-this.dx,q.y-this.dy);this.g?.fillStyle(color,alpha).fillPoints(points,true);}
  line(a:Phaser.Geom.Point,b:Phaser.Geom.Point,color:number,width=2,alpha=1){this.grow(a.x-this.dx-width,a.y-this.dy-width);this.grow(b.x-this.dx+width,b.y-this.dy+width);this.g?.lineStyle(width,color,alpha).lineBetween(a.x,a.y,b.x,b.y);}
  circle(c:Phaser.Geom.Point,r:number,color:number,alpha=1){this.grow(c.x-this.dx-r,c.y-this.dy-r);this.grow(c.x-this.dx+r,c.y-this.dy+r);this.g?.fillStyle(color,alpha).fillCircle(c.x,c.y,r);}
  ellipse(c:Phaser.Geom.Point,w:number,h:number,color:number,alpha=1){this.grow(c.x-this.dx-w/2,c.y-this.dy-h/2);this.grow(c.x-this.dx+w/2,c.y-this.dy+h/2);this.g?.fillStyle(color,alpha).fillEllipse(c.x,c.y,w,h);}
  corners(r:Rect,z:number){return {A:this.p(r.x-r.w/2,r.y-r.h/2,z),B:this.p(r.x+r.w/2,r.y-r.h/2,z),Cc:this.p(r.x+r.w/2,r.y+r.h/2,z),D:this.p(r.x-r.w/2,r.y+r.h/2,z)};}
  shadow(r:Rect,k=1.15){const q=sub(r,k);const {A,B,Cc,D}=this.corners({...q,x:q.x+.006,y:q.y+.006},0);this.poly([A,B,Cc,D],0x000000,.14);}
  /** An upright box: the two faces toward the viewer (south-west darker, south-east lit) and its top. */
  box(r:Rect,z0:number,z1:number,wall:number,top:number|null=shade(wall,1.08)){
    const a=this.corners(r,z0),b=this.corners(r,z1);
    this.poly([a.D,a.Cc,b.Cc,b.D],shade(wall,.8));this.poly([a.Cc,a.B,b.B,b.Cc],wall);
    if(top!==null)this.poly([b.A,b.B,b.Cc,b.D],top);
  }
  /** A quad on one of the two visible faces: `face` 'sw' (D→C) or 'se' (C→B), t along it, z up it. */
  face(r:Rect,face:'sw'|'se',t0:number,t1:number,z0:number,z1:number,color:number,alpha=1){
    const x0=r.x-r.w/2,x1=r.x+r.w/2,y0=r.y-r.h/2,y1=r.y+r.h/2;
    const at=(t:number):Pt=>face==='sw'?[x0+(x1-x0)*t,y1]:[x1,y1+(y0-y1)*t];
    const [ax,ay]=at(t0),[bx,by]=at(t1);
    this.poly([this.p(ax,ay,z0),this.p(bx,by,z0),this.p(bx,by,z1),this.p(ax,ay,z1)],color,alpha);
  }
  windows(r:Rect,z0:number,z1:number,n:number,color:number,skipDoor=true){
    for(const f of ['sw','se'] as const)for(let i=0;i<n;i++){const t=(i+.5)/n;if(skipDoor&&f==='sw'&&i===Math.floor(n/2))continue;this.face(r,f,t-.18/n*2,t+.18/n*2,z0,z1,color);}
  }
  /** A hipped roof over r (grown by `over`), its ridge along the longer side, eaves at z, `h` high. */
  roof(r0:Rect,z:number,h:number,color:number,over=0,eaves:number|null=null){
    const r={x:r0.x,y:r0.y,w:r0.w+over*2,h:r0.h+over*2},x0=r.x-r.w/2,x1=r.x+r.w/2,y0=r.y-r.h/2,y1=r.y+r.h/2;
    const A=this.p(x0,y0,z),B=this.p(x1,y0,z),Cc=this.p(x1,y1,z),D=this.p(x0,y1,z);
    if(r.w>=r.h){const R1=this.p(x0+r.h/2,r.y,z+h),R2_=this.p(x1-r.h/2,r.y,z+h);
      this.poly([A,B,R2_,R1],shade(color,.96));this.poly([A,R1,D],shade(color,.86));this.poly([D,R1,R2_,Cc],shade(color,.76));this.poly([B,Cc,R2_],color);
      this.line(R1,R2_,shade(color,.55),2.5);this.line(Cc,R2_,shade(color,.6),1.5);}
    else{const R1=this.p(r.x,y0+r.w/2,z+h),R2_=this.p(r.x,y1-r.w/2,z+h);
      this.poly([A,B,R1],shade(color,.96));this.poly([A,R1,R2_,D],shade(color,.86));this.poly([D,Cc,R2_],shade(color,.76));this.poly([B,Cc,R2_,R1],color);
      this.line(R1,R2_,shade(color,.55),2.5);this.line(Cc,R2_,shade(color,.6),1.5);}
    if(eaves!==null)for(const [cx,cy,ox,oy] of [[x0,y1,-1,1],[x1,y1,1,1],[x1,y0,1,-1]] as const){
      const base=this.p(cx,cy,z),tip=this.p(cx+ox*.012,cy+oy*.012,z+13),inner=this.p(cx-ox*.004,cy-oy*.004,z+4);
      this.poly([base,tip,inner],eaves);
    }
  }
  /** A roof tier between two floors: a sloped skirt from the eaves (r grown by `over`) at z up to `inner` at z + h. */
  skirt(r0:Rect,inner:Rect,z:number,h:number,color:number,over=0,eaves:number|null=null){
    const o={x:r0.x,y:r0.y,w:r0.w+over*2,h:r0.h+over*2},a=this.corners(o,z),b=this.corners(inner,z+h);
    this.poly([a.A,a.B,b.B,b.A],shade(color,.96));this.poly([a.A,b.A,b.D,a.D],shade(color,.86));
    this.poly([a.D,a.Cc,b.Cc,b.D],shade(color,.76));this.poly([a.Cc,a.B,b.B,b.Cc],color);
    this.line(a.Cc,b.Cc,shade(color,.6),1.5);this.line(a.D,a.Cc,shade(color,.55),2);this.line(a.Cc,a.B,shade(color,.7),2);
    if(eaves!==null){const x0=o.x-o.w/2,x1=o.x+o.w/2,y0=o.y-o.h/2,y1=o.y+o.h/2;
      for(const [cx,cy,ox,oy] of [[x0,y1,-1,1],[x1,y1,1,1],[x1,y0,1,-1]] as const)this.poly([this.p(cx,cy,z),this.p(cx+ox*.01,cy+oy*.01,z+11),this.p(cx-ox*.004,cy-oy*.004,z+4)],eaves);}
  }
  /** Lines down a roof's two front faces (tiles or straw). */
  stripes(r0:Rect,z:number,h:number,color:number,over=0,n=8){
    const r={x:r0.x,y:r0.y,w:r0.w+over*2,h:r0.h+over*2},x0=r.x-r.w/2,x1=r.x+r.w/2,y0=r.y-r.h/2,y1=r.y+r.h/2,cl=(t:number)=>Math.min(Math.max(t,.25),.75);
    for(let i=1;i<n;i++){const t=i/n;
      this.line(this.p(x0+(x1-x0)*t,y1,z),this.p(x0+(x1-x0)*cl(t),r.y+(y1-r.y)*.1,z+h*.92),color,1.2,.5);
      this.line(this.p(x1,y1+(y0-y1)*t,z),this.p(r.x+(x1-r.x)*.1,y1+(y0-y1)*cl(t),z+h*.92),color,1.2,.5);}
  }
  /** A pillar / pole / post: a vertical bar `wd` pixels wide. */
  bar(x:number,y:number,z0:number,z1:number,wd:number,color:number){
    const a=this.s(x,y,z0,-wd/2,0),b=this.s(x,y,z0,wd/2,0),c=this.s(x,y,z1,wd/2,0),d=this.s(x,y,z1,-wd/2,0);
    this.poly([a,b,c,d],color);this.poly([this.s(x,y,z0,wd*.15,0),b,c,this.s(x,y,z1,wd*.15,0)],shade(color,.78));
  }
  pillars(r:Rect,z0:number,z1:number,n:number,color:number,wd=6){
    const x0=r.x-r.w/2,x1=r.x+r.w/2,y0=r.y-r.h/2,y1=r.y+r.h/2,o=.004;
    for(let i=0;i<=n;i++){const t=i/n;this.bar(x0+(x1-x0)*t,y1+o,z0,z1,wd,color);if(i)this.bar(x1+o,y1+(y0-y1)*t,z0,z1,wd,color);}
  }
  /** A banner on a face (the bang colour), with a darker hem. */
  banner(r:Rect,face:'sw'|'se',t:number,z0:number,z1:number,color:number,wdt=.14){
    this.face(r,face,t-wdt/2,t+wdt/2,z0,z1,color);this.face(r,face,t-wdt/2,t+wdt/2,z0,z0+5,shade(color,.65));
    this.face(r,face,t-wdt/2,t+wdt/2,z1-3,z1,C.gold);
  }
  steps(r:Rect,n:number,hgt:number,color:number){
    for(let i=0;i<n;i++){const k=1+(n-i)*.06,q={x:r.x+r.w*.42*(1-i*.15),y:r.y+r.h*.42*(1-i*.15),w:r.w*.36*k,h:r.h*.36*k};this.box(q,i*hgt,(i+1)*hgt,color);}
  }
  /** Bamboo scaffolding around r up to z1: poles, ties, braces, planks and a green net on one side. */
  scaffold(r0:Rect,z1:number,back:boolean){
    const r=sub(r0,1.08),x0=r.x-r.w/2,x1=r.x+r.w/2,y0=r.y-r.h/2,y1=r.y+r.h/2,lv=Math.max(2,Math.round(z1/26));
    const poles:Pt[]=back?[[x0,y0],[x1,y0],[x0,y1-r.h/2]]:[[x0,y1],[r.x,y1],[x1,y1],[x1,r.y]];
    const edges:Array<[Pt,Pt]>=back?[[[x0,y0],[x1,y0]],[[x0,y0],[x0,y1]]]:[[[x0,y1],[x1,y1]],[[x1,y1],[x1,y0]]];
    for(const [x,y] of poles)this.bar(x,y,0,z1+10,4,C.bamboo);
    for(const [[ax,ay],[bx,by]] of edges)for(let i=1;i<=lv;i++){const z=z1*i/lv;this.line(this.p(ax,ay,z),this.p(bx,by,z),C.bambooD,2.5);}
    if(!back){
      for(const [[ax,ay],[bx,by]] of edges){for(let i=0;i<lv;i++){const za=z1*i/lv,zb=z1*(i+1)/lv;this.line(this.p(ax,ay,za),this.p((ax+bx)/2,(ay+by)/2,zb),C.bambooD,1.5,.9);}
        const zm=z1*Math.ceil(lv/2)/lv,o=.012,nx=ax===bx?o:0,ny=ay===by?o:0;
        this.poly([this.p(ax,ay,zm),this.p(bx,by,zm),this.p(bx+nx,by+ny,zm),this.p(ax+nx,ay+ny,zm)],0xb98b4e);}
      this.face(r,'se',.05,.62,z1*.15,z1*.95,C.net,.32);
    }
  }
}

export class BangIslandRenderer {
  readonly ready:Promise<void>;
  private engine:Phaser.Game;
  private scene:Phaser.Scene|null=null;
  private layout:BangIslandLayout;
  private bang:BangLook;
  private N:number;
  private actors=new Map<string,{image:Phaser.GameObjects.Image;ripple:Phaser.GameObjects.Ellipse;key:string}>();
  private textures=new Map<string,string>();
  private parts=new Map<string,{keys:string[];objects:Phaser.GameObjects.GameObject[];top:number}>();
  private revision=0;
  private baked=0;
  private latest:BangFrame={people:[]};
  private canvas:HTMLCanvasElement;
  private destroyed=false;
  private resizeObserver:ResizeObserver|null=null;
  private bounds={minX:-1e4,maxX:1e4,minY:-1e4,maxY:1e4};

  constructor(canvas:HTMLCanvasElement,layout:BangIslandLayout,bang:BangLook){
    this.canvas=canvas;this.layout=layout;this.bang=bang;this.N=layout.size||24;
    const rect=canvas.getBoundingClientRect(),owner=this;
    let done:()=>void=()=>{};this.ready=new Promise(resolve=>{done=resolve;});
    this.engine=new Phaser.Game({type:Phaser.CANVAS,canvas,width:Math.round(rect.width)||375,height:Math.round(rect.height)||560,backgroundColor:layout.deep,
      audio:{noAudio:true},input:{keyboard:false,mouse:false,touch:false,gamepad:false},fps:{target:60,forceSetTimeOut:false},
      render:{antialias:true,roundPixels:false,pixelArt:false},scale:{mode:Phaser.Scale.NONE,autoCenter:Phaser.Scale.NO_CENTER},
      scene:{key:'bang-island',create(this:Phaser.Scene){owner.scene=this;owner.paint();owner.resize();done();},update(this:Phaser.Scene){owner.tick(this.time.now);}}});
    if(typeof ResizeObserver==='function'){this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(canvas.parentElement||canvas);}
  }
  private iso=(x:number,y:number):Pt=>[(x-y)*this.N*HW,(x+y)*this.N*HH];

  /** The newest people; Phaser draws them on its next tick. */
  frame(model:BangFrame){this.latest=model;}
  /** New levels, states or colours from the server: repaint only the facilities whose look changed. */
  setBang(bang:BangLook){
    const old=this.bang;this.bang=bang;if(!this.scene)return;
    const flagChanged=old.color!==bang.color||old.emoji!==bang.emoji||old.name!==bang.name;
    for(const f of bang.facilities){const before=old.facilities.find(x=>x.id===f.id);
      if(flagChanged||!before||this.lookKey(before)!==this.lookKey(f))this.paintFacility(f.id);}
    if(flagChanged)this.paintBoat();
    if(JSON.stringify(old.hall||null)!==JSON.stringify(bang.hall||null))this.paintFacility('dai_sanh');
    if(flagChanged||JSON.stringify(old.decor||[])!==JSON.stringify(bang.decor||[]))this.paintDecor();
  }
  /** 🏯 The hall's house style when it has one this build knows (else its own art). */
  private styled():{style:string;look:number}|null{const h=this.bang.hall;return h&&h.style!=='dinh'&&known(HOUSES,h.style)?h:null;}
  /** The house-art.js adapter on a Kit: local model points around the map point (cx, cy), `scale` map units each. */
  private houseView(k:Kit,cx:number,cy:number,scale:number){
    const Z=scale*this.N*HW/560,pt=(p:number[])=>new Phaser.Geom.Point(p[0],p[1]);
    return {zs:Z,depth:(a:number,b:number)=>a+b,
      P:(x:number,y:number,z:number)=>{const q=k.p(cx+x*scale,cy+y*scale,z*Z);return [q.x,q.y];},
      fill:(pts:number[][],color:string,alpha=1)=>k.poly(pts.map(pt),hex(color),alpha),
      circle:(x:number,y:number,r:number,color:string,alpha=1)=>k.circle(new Phaser.Geom.Point(x,y),r,hex(color),alpha),
      line:(a:number[],b:number[],color:string,w:number)=>k.line(pt(a),pt(b),hex(color),w)};
  }
  /** 🎏 The bang's decorations on their spots (each its own baked image, sorted with the people). */
  private paintDecor(){
    const s=this.scene!,old=this.parts.get('decor');if(old){for(const o of old.objects)o.destroy();for(const k of old.keys)if(s.textures.exists(k))s.textures.remove(k);}
    const keys:string[]=[],objects:Phaser.GameObjects.GameObject[]=[],spots=this.layout.decorAt||{};
    for(const id of this.bang.decor||[]){if(!known(DECOR,id))continue;
      for(const [x,y] of spots[id]||[]){const o=this.bake(x,y,k=>{k.ellipse(k.p(x,y),id==='thuyen_rong'?150:30,id==='thuyen_rong'?24:10,id==='thuyen_rong'?0xffffff:0x000000,id==='thuyen_rong'?.35:.14);
        paintDecor(id,this.houseView(k,x,y,1),this.bang.color);},this.iso(x,y)[1]+.5);keys.push(o.key);objects.push(o.image);
        if(id==='thuyen_rong')s.tweens.add({targets:o.image,angle:{from:-1,to:1},duration:1800,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});}}
    this.parts.set('decor',{keys,objects,top:0});
  }
  /** A tap on the canvas → the map point under it, or null outside the map. */
  toMap(clientX:number,clientY:number):Pt|null{
    const cam=this.scene?.cameras.main;if(!cam)return null;
    const r=this.canvas.getBoundingClientRect(),w=cam.getWorldPoint(clientX-r.left,clientY-r.top);
    const a=w.x/(this.N*HW),b=w.y/(this.N*HH),x=(a+b)/2,y=(b-a)/2;
    return x>=-.1&&x<=1.1&&y>=-.1&&y<=1.1?[x,y]:null;
  }
  /** A map point → where it shows on the canvas (CSS pixels from its top left), `lift` pixels above the ground. */
  toScreen(x:number,y:number,lift=0):Pt|null{
    const cam=this.scene?.cameras.main;if(!cam)return null;
    const [wx,wy]=this.iso(x,y);
    return [(wx-cam.scrollX-cam.width/2)*cam.zoom+cam.width/2,(wy-lift-cam.scrollY-cam.height/2)*cam.zoom+cam.height/2];
  }
  /** Where a facility's label goes: its slot's middle and how tall it stands (pixels above the ground). */
  anchor(id:string):{x:number;y:number;lift:number}|null{
    const s=this.layout.slots[id];if(!s)return null;
    const part=this.parts.get('f:'+id);
    if(id==='cong_bang'){const [x,y]=atScreen(this.layout.gate.a,this.layout.gate.b);return {x,y,lift:(part?.top||100)+8};}
    return {x:s.x,y:s.y,lift:(part?.top||40)+10};
  }
  get personHeight(){return 150*SCALE*(this.scene?.cameras.main.zoom||1);}

  resize(){
    if(this.destroyed)return;
    const r=this.canvas.getBoundingClientRect(),w=Math.max(1,Math.round(r.width)),h=Math.max(1,Math.round(r.height));
    const scale=this.engine?.scale;
    if(scale&&(scale.width!==w||scale.height!==h))scale.resize(w,h);
    const cam=this.scene?.cameras.main;if(!cam)return;
    cam.setSize(w,h);
    // A wide screen sees the whole island; a phone follows the player at a size where faces still read.
    cam.setZoom(Math.max(.66,Math.min(1,Math.min(w/1850,h/950))));this.clamp();
  }

  destroy(){
    if(this.destroyed)return;this.destroyed=true;
    this.resizeObserver?.disconnect();
    this.engine.destroy(false);
  }

  /* ---- baking ------------------------------------------------------------------------------------------------ */
  /** Draw `fn` around the map point (x, y), bake it, and stand the image there (depth: its own, or the point's). */
  private bake(x:number,y:number,fn:(k:Kit)=>void,depth?:number):{image:Phaser.GameObjects.Image;top:number;key:string}{
    const s=this.scene!,[ax,ay]=this.iso(x,y);
    const m=new Kit(this.iso,ax,ay,null);fn(m);
    const w=Math.max(2,Math.ceil(m.maxX-m.minX+PAD*2)),h=Math.max(2,Math.ceil(m.maxY-m.minY+PAD*2));
    const g=s.add.graphics(),k=new Kit(this.iso,ax,ay,g);k.dx=PAD-m.minX;k.dy=PAD-m.minY;fn(k);
    const key='bi-'+(++this.baked);g.generateTexture(key,w,h);g.destroy();
    const image=s.add.image(ax,ay,key).setOrigin(k.dx/w,k.dy/h).setDepth(depth??ay);
    return {image,top:m.top,key};
  }

  /* ---- painting ---------------------------------------------------------------------------------------------- */
  private paint(){
    const s=this.scene!,L=this.layout,N=this.N,rand=seeded(977);
    // The sea and the island in one baked ground: the shelf, the cliff, the beach, grass, roads, the plaza, the pier.
    const ground=this.bake(.5,.5,k=>{
      const r=seeded(31),pts=(list:Pt[],z=0)=>list.map(([x,y])=>k.p(x,y,z));
      if(L.site){   // 🏝️ the next level's land, a raw sand bank still under work
        k.poly(pts(inset(L.site.shore,-.085)),hex(L.sea),1);k.poly(pts(L.site.shore,-12),0xa88a5c);k.poly(pts(L.site.shore),0xd9c08e);
        for(let i=0;i<40;i++){const x=r(),y=r();if(inside(L.site.shore,x,y)&&!inside(L.shore,x,y))k.ellipse(k.p(x,y),8+r()*8,3+r()*2,0xb89a68,.5);}
      }
      k.poly(pts(inset(L.shore,-.085)),hex(L.sea),1);
      k.poly(pts(inset(L.shore,-.03)),shade(hex(L.sea),1.08),1);
      k.poly(pts(L.dock.map(([x,y])=>[x,y] as Pt),-10),0x4a3423,.25);
      k.poly(pts(L.shore,-12),shade(hex(L.sand),.72));
      k.poly(pts(inset(L.shore,-.01)),0xffffff,.55);
      k.poly(pts(L.shore),hex(L.sand));
      const grass=inset(L.shore,L.sandWidth);
      k.poly(pts(grass,-3),hex(L.grassDark));k.poly(pts(grass),hex(L.grass));
      for(let i=0;i<260;i++){const x=r(),y=r();if(!inside(grass,x,y))continue;k.ellipse(k.p(x,y),6+r()*9,3+r()*3,hex(L.grassDark),.5);}
      // Stone roads and the plaza.
      for(const road of L.roads){k.poly(pts(road,-2),hex(L.stoneDark));k.poly(pts(road),hex(L.stone));}
      const [pcx,pcy]=L.plaza.c,circle:Pt[]=[];for(let i=0;i<48;i++){const t=i/48*Math.PI*2;circle.push([pcx+Math.cos(t)*L.plaza.r,pcy+Math.sin(t)*L.plaza.r]);}
      k.poly(pts(circle,-3),hex(L.stoneDark));k.poly(pts(circle),hex(L.stone));
      for(let ring=1;ring<=3;ring++){const rr=L.plaza.r*ring/3.4;const c2=circle.map(([x,y])=>[pcx+(x-pcx)*rr/L.plaza.r,pcy+(y-pcy)*rr/L.plaza.r] as Pt);
        for(let i=0;i<c2.length;i++)k.line(k.p(...c2[i]),k.p(...c2[(i+1)%c2.length]),hex(L.stoneDark),1,.6);}
      for(const road of L.roads){const [a,b,c,d]=road;for(let i=1;i<14;i++){const t=i/14;k.line(k.p(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t),k.p(d[0]+(c[0]-d[0])*t,d[1]+(c[1]-d[1])*t),hex(L.stoneDark),1,.45);}}
      // The pier: planks across.
      const [d0,d1,d2,d3]=L.dock;k.poly(pts(L.dock,-8),0x6e4a2e);k.poly(pts(L.dock),0xb5844f);
      for(let i=1;i<20;i++){const t=i/20;k.line(k.p(d0[0]+(d1[0]-d0[0])*t,d0[1]+(d1[1]-d0[1])*t),k.p(d3[0]+(d2[0]-d3[0])*t,d3[1]+(d2[1]-d3[1])*t),0x8b6038,1.5,.8);}
      for(const [x,y] of [d1,d2])k.ellipse(k.p(x,y),10,6,0x5a3c25);
      // Flat plots: the flower bed, the lotus pond, the yard's floor, the sparring ring's boards, the tea pavilion's pond.
      for(const p of L.plots){
        if(p.kind==='ring'){k.box(sub(p,1.06),-2,10,C.woodD,C.crate);const in2=sub(p,.72),c=k.corners(in2,10);k.poly([c.A,c.B,c.Cc,c.D],0xd9ad6a);
          for(let i=1;i<8;i++){const t=i/8;k.line(k.p(p.x-p.w*.53+p.w*1.06*t,p.y-p.h*.53,10),k.p(p.x-p.w*.53+p.w*1.06*t,p.y+p.h*.53,10),C.woodD,1,.5);}}
        if(p.kind==='teahouse'){const q=sub(p,1.55);k.box(q,-2,3,hex(L.stoneDark),hex(L.stone));const c=k.corners(sub(q,.92),3);k.poly([c.A,c.B,c.Cc,c.D],0x3f9fbf);
          for(let i=0;i<5;i++)k.ellipse(k.p(q.x+(r()-.5)*q.w*.8,q.y+(r()-.5)*q.h*.8,3),9,4,i%2?0xffffff:0xff7a2f,.9);}
        if(p.kind==='flowers'){const q=sub(p,1.1);k.box(q,0,6,hex(L.stoneDark),0x7a5a3a);
          for(let i=0;i<34;i++){const fx=p.x+(r()-.5)*p.w,fy=p.y+(r()-.5)*p.h;k.circle(k.p(fx,fy,7),2.6+r()*1.6,[0xff6f91,0xffd166,0xf8f4ff,0xc77dff,0xff9f43][i%5]);}}
        if(p.kind==='pond'){const q=sub(p,1.12);k.box(q,-2,4,hex(L.stoneDark),hex(L.stone));const {A,B,Cc,D}=k.corners(sub(p,.96),3);k.poly([A,B,Cc,D],0x3f9fbf);
          for(let i=0;i<9;i++){const fx=p.x+(r()-.5)*p.w*.8,fy=p.y+(r()-.5)*p.h*.8;k.ellipse(k.p(fx,fy,3),13,6,0x4f9a4a);if(i%3===0)k.circle(k.p(fx,fy,6),3.2,0xff9ec0);}
          for(let i=0;i<3;i++)k.ellipse(k.p(p.x+(r()-.5)*p.w*.6,p.y+(r()-.5)*p.h*.6,3),9,4,0xff7a2f,.9);}
      }
    },-1e6);
    void ground;void N;
    // Swell on the open sea, baked once and breathing slowly.
    const swell=this.bake(.5,.5,k=>{const r=seeded(7);for(let i=0;i<70;i++){const x=r()*1.7-.35,y=r()*1.7-.35;if(inside(inset(L.shore,-.06),x,y))continue;
      const c=k.p(x,y),rad=10+r()*16;k.g?.lineStyle(2,0xffffff,.4).beginPath().arc(c.x,c.y,rad,Math.PI*1.15,Math.PI*1.85).strokePath();k.ellipse(c,rad*2,rad*.4,0xffffff,0);}},-1e6+1);
    s.tweens.add({targets:swell.image,alpha:{from:.45,to:1},duration:2400,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
    for(const id of Object.keys(L.slots))this.paintFacility(id);
    for(const p of L.plots)this.paintPlot(p,rand);
    for(const [x,y] of L.lamps||[])this.lantern(x,y,rand);
    if(L.site)this.worksite(L.site);
    for(const [x,y] of L.palms)this.palm(x,y,rand);
    for(const [x,y] of L.trees)this.tree(x,y,rand);
    this.paintBoat();
    this.paintDecor();
    for(const sp of L.spots){const [a,b]=this.iso(sp.x,sp.y);
      s.add.ellipse(a,b,46,22,0xffffff,.26).setStrokeStyle(2,0xffffff,.8).setDepth(b-2);
      const icon=s.add.text(a,b-30,sp.emoji,{fontSize:'24px'}).setOrigin(.5,1).setDepth(b+1);
      s.tweens.add({targets:icon,y:b-38,duration:1400+rand()*500,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});}
    // The camera stays over the island: never more than a strip of open sea around it.
    const edge=[...inset(L.shore,-.03),...(L.site?inset(L.site.shore,-.03):[]),...L.dock].map(([x,y])=>this.iso(x,y));
    this.bounds={minX:Math.min(...edge.map(p=>p[0])),maxX:Math.max(...edge.map(p=>p[0])),minY:Math.min(...edge.map(p=>p[1]))-220,maxY:Math.max(...edge.map(p=>p[1]))+30};
    const [cx,cy]=this.iso(...L.plaza.c);s.cameras.main.centerOn(cx,cy);this.clamp();
  }
  private clamp(){
    const cam=this.scene?.cameras.main;if(!cam)return;const b=this.bounds,hw=cam.width/2/cam.zoom,hh=cam.height/2/cam.zoom;
    const fit=(c:number,lo:number,hi:number)=>lo>hi?(lo+hi)/2:Math.max(lo,Math.min(hi,c));
    const cx=fit(cam.scrollX+cam.width/2,b.minX+hw,b.maxX-hw),cy=fit(cam.scrollY+cam.height/2,b.minY+hh,b.maxY-hh);
    cam.centerOn(cx,cy);
  }

  private lookKey(f:BangFacilityLook){return `${f.band??bandOf(f.level)}|${f.state==='building'?'b':'d'}`;}
  private facility(id:string):BangFacilityLook{return this.bang.facilities.find(f=>f.id===id)||{id,level:0,state:'done'};}

  /** One facility: its look for the level band, scaffolding while building, a staked plot before level 1. */
  private paintFacility(id:string){
    const s=this.scene!,L=this.layout,slot=L.slots[id];if(!slot)return;
    const old=this.parts.get('f:'+id);if(old){for(const o of old.objects)o.destroy();for(const k of old.keys)if(s.textures.exists(k))s.textures.remove(k);}
    const f=this.facility(id),band=f.band??bandOf(f.level),building=f.state==='building',flag=hex(this.bang.color,0xc2410c);
    const objects:Phaser.GameObjects.GameObject[]=[],r:Rect=slot;
    const front=this.iso(r.x+r.w/2,r.y+r.h/2)[1];
    let top=0;const keys:string[]=[];
    const add=(o:{image:Phaser.GameObjects.Image;top:number;key:string})=>{objects.push(o.image);top=Math.max(top,o.top);keys.push(o.key);return o;};
    if(id==='san_pet'){
      add(this.bake(r.x,r.y,k=>this.yard(k,r,band,flag,'floor'),-1e6+3));
      add(this.bake(r.x,r.y,k=>{this.yard(k,r,band,flag,'back');if(building)k.scaffold(r,30,true);},this.iso(r.x-r.w/2,r.y-r.h/2)[1]+1));
      add(this.bake(r.x,r.y,k=>{this.yard(k,r,band,flag,'front');if(building)k.scaffold(r,30,false);},front));
    }else if(id==='cong_bang'){
      const [gx,gy]=atScreen(L.gate.a,L.gate.b);
      add(this.bake(gx,gy,k=>this.gate(k,band,flag,building),this.iso(gx,gy)[1]+2));
    }else{
      const around=sub(r,[.66,.7,.8,.9][band]),tall=this.height(id,Math.max(1,band));
      if(building)add(this.bake(r.x,r.y,k=>k.scaffold(around,tall,true),this.iso(r.x-r.w/2,r.y-r.h/2)[1]+1));
      add(this.bake(r.x,r.y,k=>{this.building(k,id,r,band,flag,building);if(building)k.scaffold(around,tall,false);},front));
    }
    // Moving bits: the bang's flags, the temple's glow, the statue's braziers.
    for(const o of this.living(id,r,band,flag,building))objects.push(o);
    if(this.bang.emoji&&band>=1&&!building&&(id==='cong_bang'||id==='dai_sanh'&&!this.styled())){
      let at:Pt,lift:number,depth:number;
      if(id==='dai_sanh'){const b=HALL_BANNER[band],w=sub(r,b.k);at=this.iso(w.x-w.w/2+w.w*b.t,w.y+w.h/2);lift=(b.z0+b.z1)/2;depth=front+.3;}
      else{at=this.iso(...atScreen(L.gate.a,L.gate.b));lift=[0,44,66,70][band];depth=at[1]+2.3;}
      objects.push(s.add.text(at[0],at[1]-lift,this.bang.emoji,{fontSize:'20px'}).setOrigin(.5,.5).setDepth(depth));
      if(id==='cong_bang'&&band>=2){
        const name=s.add.text(at[0],at[1]-(band===3?104:103),this.bang.name,{fontSize:'15px',fontStyle:'bold',color:'#ffe9a8',fontFamily:'"Be Vietnam Pro","Segoe UI",sans-serif'}).setOrigin(.5,.5).setDepth(at[1]+2.4);
        const room=band===3?94:82;if(name.width>room)name.setScale(room/name.width);objects.push(name);}
    }
    this.parts.set('f:'+id,{keys,objects,top});
  }

  /** How tall each facility stands per band (pixels), for scaffolding and labels. */
  private height(id:string,band:number){
    const st=id==='dai_sanh'?this.styled():null;
    if(st&&band>0){const art=this.layout.hallArt||{scale:2.15,level:(n:number)=>n>=5?3:n>=3?2:1};
      return houseTop(st.style,art.level(this.facility(id).level))*art.scale*this.N*HW/560;}
    const H:Record<string,number[]>={dai_sanh:[10,110,150,230],kho_bang:[8,62,84,96],xuong_may:[8,58,86,130],den_vang:[8,60,104,170],tuong_bang:[6,48,84,128],san_pet:[4,20,24,44],cong_bang:[6,90,130,140]};
    return (H[id]||[10,60,90,120])[band];
  }

  private building(k:Kit,id:string,r:Rect,band:number,flag:number,building:boolean){
    k.shadow(r,band?1.05:.95);
    if(band===0){this.plot(k,r,building);return;}
    const st=id==='dai_sanh'?this.styled():null;
    if(st){const art=this.layout.hallArt||{scale:2.15,level:(n:number)=>n>=5?3:n>=3?2:1};
      paintHouse(st.style,art.level(this.facility(id).level),st.look,this.houseView(k,r.x,r.y,art.scale));}
    else if(id==='dai_sanh')this.hall(k,r,band,flag);
    else if(id==='kho_bang')this.vault(k,r,band);
    else if(id==='xuong_may')this.tailor(k,r,band,flag);
    else if(id==='den_vang')this.temple(k,r,band);
    else if(id==='tuong_bang')this.statue(k,r,band,flag);
  }
  /** Before level 1: a cleared plot with stakes and a rope; while its first level is built, a foundation. */
  private plot(k:Kit,r0:Rect,building:boolean){
    const r=sub(r0,.86),{A,B,Cc,D}=k.corners(r,0);
    k.poly([A,B,Cc,D],C.dirt,.9);
    if(building){k.box(sub(r,.9),0,8,C.stoneD,C.stone);for(let i=0;i<5;i++)k.box({x:r.x-r.w*.3+i*r.w*.04,y:r.y+r.h*.3,w:.012,h:.01},8,14+i*2,C.crate);}
    const corners:Pt[]=[[r.x-r.w/2,r.y-r.h/2],[r.x+r.w/2,r.y-r.h/2],[r.x+r.w/2,r.y+r.h/2],[r.x-r.w/2,r.y+r.h/2]];
    for(const [x,y] of corners)k.bar(x,y,0,16,4,C.woodD);
    for(let i=0;i<4;i++){const [ax,ay]=corners[i],[bx,by]=corners[(i+1)%4];k.line(k.p(ax,ay,13),k.p(bx,by,13),0xe8d9b0,1.5);}
  }
  private hall(k:Kit,r:Rect,band:number,flag:number){
    if(band===1){
      k.box(sub(r,.82),0,7,C.stoneD,C.stone);const w=sub(r,.7);k.box(w,7,58,C.wood);
      k.face(w,'sw',.42,.58,7,44,C.woodD);k.windows(w,24,40,3,0xe9d6a8);k.banner(w,'sw',.2,14,54,flag,.14);
      k.roof(w,58,46,C.thatch,.016);k.stripes(w,58,46,shade(C.thatch,.7),.016,10);
      k.bar(r.x,r.y,104,150,3,C.woodD);
    }else if(band===2){
      k.box(sub(r,.88),0,11,C.stoneD,C.stone);k.steps(r,2,5,C.stone);
      const w=sub(r,.72),u=sub(r,.48);k.box(w,11,74,C.cream);k.windows(w,34,58,4,0x8a3b2a);k.face(w,'sw',.4,.6,11,60,C.lacq);k.face(w,'se',.4,.6,11,60,C.lacq);
      k.pillars(w,11,74,4,C.red,6);k.banner(w,'sw',.18,22,70,flag,.13);
      k.skirt(w,u,74,14,C.tile,.016,C.tileD);
      k.box(u,88,112,C.cream);k.windows(u,93,107,3,0x8a3b2a,false);k.roof(u,112,32,C.tile,.014,C.tileD);k.stripes(u,112,32,C.tileD,.014,8);
      k.bar(r.x,r.y,140,190,3,C.woodD);
    }else{
      k.box(sub(r,.96),0,16,0xd8d0c0,C.marble);k.steps(r,3,6,C.marble);
      const w=sub(r,.78),u=sub(r,.56),t=sub(r,.36);
      k.box(w,16,96,C.lacq);k.face(w,'sw',0,1,88,96,C.gold);k.face(w,'se',0,1,88,96,C.gold);
      k.windows(w,40,72,5,0xf4c95d);k.face(w,'sw',.4,.6,16,78,0x5a1215);k.face(w,'se',.4,.6,16,78,0x5a1215);
      k.pillars(w,16,96,5,C.gold,6);k.banner(w,'sw',.15,28,86,flag,.12);k.banner(w,'se',.85,28,86,flag,.12);
      k.skirt(w,u,96,16,C.gold,.018,C.red);
      k.box(u,112,146,C.lacq);k.face(u,'sw',0,1,140,146,C.gold);k.face(u,'se',0,1,140,146,C.gold);k.windows(u,118,138,3,0xf4c95d,false);
      k.skirt(u,t,146,14,C.gold,.014,C.red);
      k.box(t,160,182,C.lacq);k.roof(t,182,40,C.gold,.012,C.red);k.stripes(t,182,40,C.goldD,.012,8);
      const top=k.p(r.x,r.y,222);k.circle(top,7,C.gold);k.circle(top,4,0xfff1b0);
      k.bar(r.x,r.y,228,262,3,C.goldD);
    }
  }
  private vault(k:Kit,r:Rect,band:number){
    if(band===1){
      const w=sub(r,.58,.5);k.box(w,0,40,C.wood);k.face(w,'sw',.38,.62,0,30,C.woodD);k.roof(w,40,22,C.woodD,.01);
      for(const [dx,dy,hz] of [[.3,.2,14],[.36,.06,12],[.26,.34,10]] as const){const q={x:r.x+r.w*dx,y:r.y+r.h*dy,w:.022,h:.02};k.box(q,0,hz,C.crate);k.line(k.p(q.x-q.w/2,q.y+q.h/2,hz/2),k.p(q.x+q.w/2,q.y+q.h/2,hz/2),C.woodD,1.2);}
      k.ellipse(k.p(r.x-r.w*.05,r.y+r.h*.42,10),16,10,C.woodD);k.ellipse(k.p(r.x-r.w*.05,r.y+r.h*.42,16),16,8,C.wood);
    }else if(band===2){
      const w=sub(r,.74);k.box(w,0,58,C.stone);
      for(let z=12;z<58;z+=12){k.face(w,'sw',0,1,z,z+1.2,C.stoneD);k.face(w,'se',0,1,z,z+1.2,C.stoneD);}
      k.face(w,'sw',.36,.64,0,40,C.iron);for(let i=0;i<3;i++)for(let j=0;j<3;j++){const tt=.4+i*.1;k.face(w,'sw',tt-.01,tt+.01,8+j*12,11+j*12,C.gold);}
      k.roof(w,58,26,C.tileD,.012,C.tileD);k.stripes(w,58,26,0x5a2a20,.012,8);
      k.bar(r.x+r.w*.5,r.y+r.h*.45,0,30,3,C.iron);k.circle(k.p(r.x+r.w*.5,r.y+r.h*.45,34),5,C.red);
    }else{
      k.box(sub(r,.9),0,10,0xd8d0c0,C.marble);const w=sub(r,.7);k.box(w,10,62,0xf1e6cf);
      k.face(w,'sw',0,1,56,62,C.gold);k.face(w,'se',0,1,56,62,C.gold);k.face(w,'sw',.34,.66,10,48,C.goldD);k.face(w,'sw',.4,.6,14,44,0x6b4b10);
      k.pillars(w,10,62,2,C.gold,7);
      const c=k.p(r.x,r.y,62),rad=w.w*this.N*HW*.62;
      k.ellipse(c,rad*2,rad*.55,C.goldD);
      k.p(r.x,r.y,62+rad);k.g?.fillStyle(C.gold,1).slice(c.x,c.y,rad,Math.PI,0,false).fillPath();
      k.g?.fillStyle(0xfff0a8,.6).slice(c.x-rad*.3,c.y-rad*.4,rad*.25,Math.PI,0,false).fillPath();
      k.circle(k.p(r.x,r.y,62+rad+6),6,C.gold);
      for(const [dx,dy] of [[.48,.2],[.48,-.05],[.25,.48]] as const){const q=k.p(r.x+r.w*dx,r.y+r.h*dy,0);for(let i=0;i<5;i++)k.ellipse(new Phaser.Geom.Point(q.x,q.y-i*3.2),16-i*1.6,6,i%2?C.goldD:C.gold);}
      const chest={x:r.x+r.w*.08,y:r.y+r.h*.5,w:.026,h:.018};k.box(chest,0,12,0x7a4a22);k.roof(chest,12,5,0x8f5a2a,.002);k.face(chest,'sw',.4,.6,4,12,C.gold);
    }
  }
  private tailor(k:Kit,r:Rect,band:number,flag:number){
    const cloth=[0xe5484d,0xf2c14e,0x4fa3d9,0x8bc34a,0xc77dff,0xffffff];
    if(band===1){
      const w=sub(r,.7),x0=w.x-w.w/2,x1=w.x+w.w/2,y0=w.y-w.h/2,y1=w.y+w.h/2;
      for(const [x,y] of [[x0,y0],[x1,y0],[x0,y1],[x1,y1]] as const)k.bar(x,y,0,40,4,C.woodD);
      k.box({x:w.x-w.w*.1,y:w.y,w:.03,h:.022},0,16,C.wood);k.bar(w.x-w.w*.1,w.y,16,30,2,C.woodD);
      for(let i=0;i<3;i++)k.ellipse(k.p(w.x+w.w*.25,w.y-w.h*.25+i*w.h*.2,8),14,9,cloth[i]);
      const {A,B,Cc,D}=k.corners(w,40),peak=k.p(w.x,w.y,58);
      k.poly([A,B,peak],0xf3ecdf);k.poly([A,peak,D],0xe2d6c1);k.poly([D,Cc,peak],0xd3402f);k.poly([B,Cc,peak],0xec5a46);
      for(let i=1;i<6;i+=2){const t=i/6;k.poly([k.p(x0+(x1-x0)*(t-.08),y1,40),k.p(x0+(x1-x0)*(t+.08),y1,40),peak],0xf8f1e4,.9);}
    }else if(band===2){
      const w=sub(r,.68);k.box(w,0,56,0xf6efe0);k.windows(w,18,42,3,0x9cc9e0);k.face(w,'sw',.42,.58,0,38,C.woodD);
      k.roof(w,56,28,C.blueTile,.012,shade(C.blueTile,.7));k.stripes(w,56,28,shade(C.blueTile,.6),.012,8);
      const rx=r.x+r.w*.44,y0=r.y-r.h*.28,y1=r.y+r.h*.3;k.bar(rx,y0,0,34,3,C.woodD);k.bar(rx,y1,0,34,3,C.woodD);k.line(k.p(rx,y0,32),k.p(rx,y1,32),C.woodD,2.5);
      for(let i=0;i<6;i++){const t=(i+.5)/6,y=y0+(y1-y0)*t;k.poly([k.p(rx,y-.008,31),k.p(rx,y+.008,31),k.p(rx,y+.008,6+i%3*4),k.p(rx,y-.008,6+i%3*4)],cloth[i]);}
    }else{
      k.box(sub(r,.86),0,6,C.stoneD,C.stone);const w=sub(r,.74);k.box(w,6,96,0xf7dfe8);
      k.face(w,'sw',0,1,50,55,0xd9a3b8);k.face(w,'se',0,1,50,55,0xd9a3b8);k.windows(w,18,42,3,0xa6d4ea);k.windows(w,62,86,3,0xa6d4ea,false);k.face(w,'sw',.42,.58,6,42,0x8a5a9b);
      k.roof(w,96,32,0x7c4e9b,.014,0xe7b726);k.stripes(w,96,32,0x5b3576,.014,8);
      for(let i=0;i<5;i++){k.face(w,'sw',.08+i*.2,.15+i*.2,24,94,cloth[i%cloth.length],.95);k.face(w,'se',.1+i*.2,.17+i*.2,30,94,cloth[(i+2)%cloth.length],.95);}
      k.banner(w,'se',.5,58,94,flag,.12);
      for(const [dx,dy] of [[.5,.18],[.5,-.12]] as const){const x=r.x+r.w*dx,y=r.y+r.h*dy;k.bar(x,y,0,18,2,C.woodD);k.poly([k.s(x,y,18,-7,0),k.s(x,y,18,7,0),k.s(x,y,40,5,0),k.s(x,y,40,-5,0)],dx>0&&dy>0?0xe5484d:0x4fa3d9);k.circle(k.s(x,y,44,0,0),4,0xf0d2b0);}
    }
  }
  private temple(k:Kit,r:Rect,band:number){
    if(band===1){
      k.box(sub(r,.56),0,8,C.stoneD,C.stone);const w=sub(r,.42);k.box(w,8,40,C.red);k.face(w,'sw',.38,.62,8,30,0x4a1010);k.roof(w,40,20,C.tile,.012,C.tileD);
      const b=k.p(r.x+r.w*.38,r.y+r.h*.38,4);k.ellipse(b,16,8,C.goldD);for(let i=-1;i<=1;i++)k.line(new Phaser.Geom.Point(b.x+i*4,b.y),new Phaser.Geom.Point(b.x+i*4,b.y-14),0x8b4a2b,1.2);
    }else if(band===2){
      k.box(sub(r,.84),0,12,C.stoneD,C.stone);k.steps(r,2,5,C.stone);const w=sub(r,.66),u=sub(r,.44);k.box(w,12,62,0xf2c94c);
      k.face(w,'sw',.38,.62,12,48,C.lacq);k.face(w,'se',.38,.62,12,48,C.lacq);k.pillars(w,12,62,3,C.red,6);
      k.skirt(w,u,62,12,C.gold,.014,C.red);k.box(u,74,90,0xf2c94c);k.roof(u,90,26,C.gold,.012,C.red);k.stripes(u,90,26,C.goldD,.012,8);
    }else{
      k.box(sub(r,.94),0,14,0xd8d0c0,C.marble);k.steps(r,3,5,C.marble);
      const tiers=[.68,.54,.42,.3],walls=[38,26,20,16];let z=14;
      for(let i=0;i<tiers.length;i++){const w=sub(r,tiers[i]);k.box(w,z,z+walls[i],0xf0c23a);k.face(w,'sw',.4,.6,z,z+walls[i]*.75,C.lacq);k.face(w,'se',.4,.6,z,z+walls[i]*.75,C.lacq);
        k.face(w,'sw',0,1,z+walls[i]-3,z+walls[i],C.red);k.face(w,'se',0,1,z+walls[i]-3,z+walls[i],C.red);z+=walls[i];
        if(i<tiers.length-1){k.skirt(w,sub(r,tiers[i+1]),z,9,C.gold,.012,C.red);z+=9;}else{k.roof(w,z,26,C.gold,.01,C.red);z+=26;}}
      k.bar(r.x,r.y,z,z+30,3,C.goldD);k.circle(k.p(r.x,r.y,z+34),6,C.gold);
    }
  }
  private statue(k:Kit,r:Rect,band:number,flag:number){
    if(band===1){
      k.ellipse(k.p(r.x,r.y,2),r.w*this.N*HW*1.1,r.w*this.N*HW*.5,C.stoneD);k.ellipse(k.p(r.x,r.y,6),r.w*this.N*HW*.8,r.w*this.N*HW*.34,0x8a8173);
      const s={x:r.x,y:r.y,w:r.w*.5,h:r.h*.16};k.box(s,6,46,C.stone);k.circle(k.s(r.x,r.y,46,0,0),r.w*this.N*HW*.26,C.stone);
      for(let i=0;i<4;i++)k.face(s,'sw',.2,.8,14+i*7,15.5+i*7,C.stoneD);
    }else{
      const big=band===3,base=sub(r,big?1:.84);k.box(base,0,big?34:24,big?0xe9e1d0:C.stoneD,big?C.marble:C.stone);if(big){k.face(base,'sw',0,1,28,34,C.gold);k.face(base,'se',0,1,28,34,C.gold);}
      const z0=big?34:24,body=big?C.gold:0x9aa0a6,dark=shade(body,.75),hgt=big?84:56;
      const x=r.x,y=r.y;
      if(big)k.poly([k.s(x,y,z0+hgt*.78,-6,0),k.s(x,y,z0+hgt*.78,8,0),k.s(x,y,z0+6,20,0),k.s(x,y,z0+6,-18,0)],flag);
      k.poly([k.s(x,y,z0,-13,0),k.s(x,y,z0,13,0),k.s(x,y,z0+hgt*.72,8,0),k.s(x,y,z0+hgt*.72,-8,0)],body);
      k.poly([k.s(x,y,z0,2,0),k.s(x,y,z0,13,0),k.s(x,y,z0+hgt*.72,8,0),k.s(x,y,z0+hgt*.72,2,0)],dark);
      k.circle(k.s(x,y,z0+hgt*.84,0,0),hgt*.12,body);k.circle(k.s(x,y,z0+hgt*.84,hgt*.04,0),hgt*.07,dark,.4);
      k.line(k.s(x,y,z0+hgt*.6,9,0),k.s(x,y,z0+hgt*1.12,20,0),big?0xfff1b0:0xd7dde2,3);k.line(k.s(x,y,z0+hgt*.66,4,0),k.s(x,y,z0+hgt*.62,14,0),dark,4);
    }
  }
  /** The training yard in three layers (the floor under people, the back, the front). */
  private yard(k:Kit,r:Rect,band:number,flag:number,layer:'floor'|'back'|'front'){
    const q=sub(r,.96),x0=q.x-q.w/2,x1=q.x+q.w/2,y0=q.y-q.h/2,y1=q.y+q.h/2;
    if(layer==='floor'){
      const {A,B,Cc,D}=k.corners(q,0);
      if(band===0){k.poly([A,B,Cc,D],C.dirt,.85);return;}
      k.poly([A,B,Cc,D],band===1?C.dirt:band===2?C.field:C.sandFloor);
      if(band===2){const i=k.corners(sub(q,.86),0);k.line(i.A,i.B,0xffffff,2,.8);k.line(i.B,i.Cc,0xffffff,2,.8);k.line(i.Cc,i.D,0xffffff,2,.8);k.line(i.D,i.A,0xffffff,2,.8);k.g?.lineStyle(2,0xffffff,.8).strokeEllipse(k.p(q.x,q.y).x,k.p(q.x,q.y).y,44,22);}
      if(band===3){const i=k.corners(sub(q,.7),0);k.poly([i.A,i.B,i.Cc,i.D],shade(C.sandFloor,.93));k.g?.lineStyle(3,flag,.8).strokeEllipse(k.p(q.x,q.y).x,k.p(q.x,q.y).y,60,30);}
      return;
    }
    const back=layer==='back';
    const edges:Array<[Pt,Pt]>=back?[[[x0,y0],[x1,y0]],[[x0,y0],[x0,y1]]]:[[[x0,y1],[x1,y1]],[[x1,y1],[x1,y0]]];
    if(band===0){for(const [[ax,ay],[bx,by]] of edges){k.bar(ax,ay,0,14,4,C.woodD);k.bar(bx,by,0,14,4,C.woodD);k.line(k.p(ax,ay,11),k.p(bx,by,11),0xe8d9b0,1.5);}return;}
    if(band<3){
      const post=band===1?C.woodD:0xf4f1ea;
      for(const [[ax,ay],[bx,by]] of edges){for(let i=0;i<=6;i++){const t=i/6;k.bar(ax+(bx-ax)*t,ay+(by-ay)*t,0,band===1?16:12,3,post);}
        k.line(k.p(ax,ay,13),k.p(bx,by,13),post,2.5);k.line(k.p(ax,ay,7),k.p(bx,by,7),post,2);}
      if(back&&band===1){const x=q.x-q.w*.22,y=q.y-q.h*.22;k.bar(x,y,0,40,5,C.wood);const c=k.p(x,y,44);k.circle(c,11,0xffffff);k.circle(c,7,C.red);k.circle(c,3,0xffffff);}
      if(back&&band===2){for(const [dx,dy] of [[-.2,.1],[.1,-.2]] as const){const x=q.x+q.w*dx,y=q.y+q.h*dy;k.bar(x-.012,y+.012,0,14,3,0xffffff);k.bar(x+.012,y-.012,0,14,3,0xffffff);k.line(k.p(x-.012,y+.012,12),k.p(x+.012,y-.012,12),C.red,3);}
        const c=k.p(q.x-q.w*.25,q.y-q.h*.25,0);k.p(q.x-q.w*.25,q.y-q.h*.25,18);k.g?.lineStyle(7,0x4fa3d9,1).beginPath().arc(c.x,c.y,14,Math.PI,0,false).strokePath();}
      if(!back&&band===2)for(const [dx,dy] of [[.3,.3],[.36,.1]] as const)k.poly([k.p(q.x+q.w*dx-.004,q.y+q.h*dy,0),k.p(q.x+q.w*dx+.004,q.y+q.h*dy,0),k.p(q.x+q.w*dx,q.y+q.h*dy,12)],0xff8a1f);
      return;
    }
    // Band 3: an arena. Stands along the back, a low wall in front.
    if(back){
      for(let i=0;i<3;i++){const o=.012*(3-i);
        k.box({x:q.x,y:y0-o+.004,w:q.w+o*2,h:.012},i*12,(i+1)*12,C.stone,i===2?shade(flag,1.1):C.stoneD);
        k.box({x:x0-o+.004,y:q.y,w:.012,h:q.h+o*2},i*12,(i+1)*12,C.stone,i===2?shade(flag,1.1):C.stoneD);}
      k.bar(x0-.02,y0-.02,0,40,4,C.goldD);
    }else{
      k.box({x:q.x,y:y1,w:q.w,h:.008},0,12,C.stone,C.marble);k.box({x:x1,y:q.y,w:.008,h:q.h},0,12,C.stone,C.marble);
    }
  }
  /** The gate across the road, its pillars at ±half (screen-aligned). */
  private gate(k:Kit,band:number,flag:number,building:boolean){
    const G=this.layout.gate,[lx,ly]=atScreen(G.a-G.half,G.b),[rx,ry]=atScreen(G.a+G.half,G.b),[cx,cy]=atScreen(G.a,G.b);
    const span=(this.iso(rx,ry)[0]-this.iso(lx,ly)[0])/2;
    const beam=(z:number,th:number,color:number,over=10)=>k.poly([k.s(cx,cy,z,-span-over,0),k.s(cx,cy,z,span+over,0),k.s(cx,cy,z+th,span+over,0),k.s(cx,cy,z+th,-span-over,0)],color);
    const tileRoof=(z:number,wd:number,hgt:number,color:number,tip:number)=>{k.poly([k.s(cx,cy,z,-wd,0),k.s(cx,cy,z,wd,0),k.s(cx,cy,z+hgt,wd*.72,0),k.s(cx,cy,z+hgt,-wd*.72,0)],color);
      k.poly([k.s(cx,cy,z,-wd,0),k.s(cx,cy,z+hgt*.3,-wd-12,0),k.s(cx,cy,z+hgt*.15,-wd+10,0)],tip);k.poly([k.s(cx,cy,z,wd,0),k.s(cx,cy,z+hgt*.3,wd+12,0),k.s(cx,cy,z+hgt*.15,wd-10,0)],tip);
      k.poly([k.s(cx,cy,z+hgt,-wd*.72,0),k.s(cx,cy,z+hgt,wd*.72,0),k.s(cx,cy,z+hgt+4,wd*.7,0),k.s(cx,cy,z+hgt+4,-wd*.7,0)],shade(color,.6));};
    if(band===0){
      for(const [x,y] of [[lx,ly],[rx,ry]] as Pt[])k.bar(x,y,0,building?40:16,building?6:4,C.woodD);
      k.line(k.s(lx,ly,13,0,0),k.s(rx,ry,13,0,0),0xe8d9b0,1.5);
      if(building)beam(36,5,C.bamboo,4);
      return;
    }
    if(band===1){
      for(const [x,y] of [[lx,ly],[rx,ry]] as Pt[])k.bar(x,y,0,90,12,C.wood);
      beam(80,10,C.woodD,18);beam(64,6,C.wood,6);
      k.poly([k.s(cx,cy,62,-22,0),k.s(cx,cy,62,22,0),k.s(cx,cy,26,22,0),k.s(cx,cy,20,0,0),k.s(cx,cy,26,-22,0)],flag);
    }else if(band===2){
      for(const [x,y] of [[lx,ly],[rx,ry]] as Pt[]){k.bar(x,y,0,110,18,C.stone);k.bar(x,y,104,114,24,C.stoneD);k.bar(x,y,0,8,24,C.stoneD);}
      beam(92,12,C.stoneD,14);tileRoof(110,span+30,22,C.tile,C.tileD);
      k.poly([k.s(cx,cy,92,-46,0),k.s(cx,cy,92,46,0),k.s(cx,cy,114,46,0),k.s(cx,cy,114,-46,0)],0x7a1d1d);k.poly([k.s(cx,cy,94,-43,0),k.s(cx,cy,94,43,0),k.s(cx,cy,96,43,0),k.s(cx,cy,96,-43,0)],C.gold);
      for(const s of [-1,1]){const at=k.s(cx,cy,72,s*span*.55,0);k.line(k.s(cx,cy,92,s*span*.55,0),at,C.ink,1);k.ellipse(at,14,18,C.red);k.ellipse(new Phaser.Geom.Point(at.x,at.y-9),8,3,C.gold);}
      k.poly([k.s(cx,cy,88,-20,0),k.s(cx,cy,88,20,0),k.s(cx,cy,48,20,0),k.s(cx,cy,40,0,0),k.s(cx,cy,48,-20,0)],flag);
    }else{
      const [ox1,oy1]=atScreen(G.a-G.half*1.8,G.b),[ox2,oy2]=atScreen(G.a+G.half*1.8,G.b);
      for(const [x,y] of [[ox1,oy1],[ox2,oy2]] as Pt[]){k.bar(x,y,0,86,14,C.lacq);k.bar(x,y,0,8,20,C.marble);}
      const side=(sx:number)=>{const mid=k.s(cx,cy,0,sx*span*1.4,0);void mid;k.poly([k.s(cx,cy,86,sx*span*1.0,0),k.s(cx,cy,86,sx*(span*1.8+14),0),k.s(cx,cy,100,sx*(span*1.7),0),k.s(cx,cy,100,sx*span*1.05,0)],C.gold);
        k.poly([k.s(cx,cy,86,sx*(span*1.8+14),0),k.s(cx,cy,98,sx*(span*1.8+24),0),k.s(cx,cy,92,sx*(span*1.8+4),0)],C.red);};
      side(-1);side(1);
      for(const [x,y] of [[lx,ly],[rx,ry]] as Pt[]){k.bar(x,y,0,118,18,C.lacq);k.bar(x,y,0,10,26,C.marble);k.bar(x,y,108,116,22,C.gold);}
      beam(96,12,C.lacq,14);beam(106,4,C.gold,14);
      tileRoof(118,span+34,16,C.gold,C.red);tileRoof(134,span+6,20,C.gold,C.red);
      k.poly([k.s(cx,cy,92,-52,0),k.s(cx,cy,92,52,0),k.s(cx,cy,116,52,0),k.s(cx,cy,116,-52,0)],0x5a1215);k.poly([k.s(cx,cy,94,-49,0),k.s(cx,cy,94,49,0),k.s(cx,cy,96,49,0),k.s(cx,cy,96,-49,0)],C.gold);k.poly([k.s(cx,cy,112,-49,0),k.s(cx,cy,112,49,0),k.s(cx,cy,114,49,0),k.s(cx,cy,114,-49,0)],C.gold);
      k.circle(k.s(cx,cy,162,0,0),6,C.gold);
      k.poly([k.s(cx,cy,90,-22,0),k.s(cx,cy,90,22,0),k.s(cx,cy,52,22,0),k.s(cx,cy,44,0,0),k.s(cx,cy,52,-22,0)],flag);
    }
    if(building){for(const [x,y] of [[lx,ly],[rx,ry]] as Pt[]){k.bar(x-.01,y+.01,0,band*40+20,3,C.bamboo);k.bar(x+.01,y-.01,0,band*40+20,3,C.bamboo);}
      for(let z=20;z<band*40+20;z+=24)k.line(k.s(lx,ly,z,-14,0),k.s(rx,ry,z,14,0),C.bambooD,2);}
  }

  /** What moves: flags in the bang's colour, the temple's glow, braziers. Small, few, cheap. */
  private living(id:string,r:Rect,band:number,flag:number,building:boolean):Phaser.GameObjects.GameObject[]{
    const s=this.scene!,out:Phaser.GameObjects.GameObject[]=[],L=this.layout;
    const pennant=(x:number,y:number,z:number,size:number,depth:number)=>{
      const [a,b]=this.iso(x,y),g=s.add.graphics().setPosition(a,b-z).setDepth(depth);
      g.fillStyle(flag,1).fillPoints([new Phaser.Geom.Point(0,0),new Phaser.Geom.Point(size*1.5,size*.18),new Phaser.Geom.Point(size*1.35,size*.55),new Phaser.Geom.Point(size*1.5,size*.9),new Phaser.Geom.Point(0,size)],true);
      g.fillStyle(0x000000,.15).fillRect(0,size*.82,size*1.4,size*.12);
      s.tweens.add({targets:g,scaleX:{from:1,to:.82},duration:900+((x*1000)|0)%400,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});out.push(g);
    };
    const front=this.iso(r.x+r.w/2,r.y+r.h/2)[1];
    if(building||band===0)return out;
    if(id==='dai_sanh'){const z=this.styled()?this.height(id,band)+6:[0,150,190,262][band];pennant(r.x,r.y,z,band===3?24:18,front+.2);}
    if(id==='cong_bang'&&band>=2){const G=L.gate,k=band===3?1.8:1;for(const sgn of [-1,1]){const [x,y]=atScreen(G.a+sgn*G.half*k,G.b);
      if(band===3){const [a,b]=this.iso(x,y),pole=s.add.graphics().setDepth(b+2.1);pole.fillStyle(C.goldD,1).fillRect(a-2,b-136,4,50);out.push(pole);}
      pennant(x,y,band===3?136:114,band===3?22:16,this.iso(x,y)[1]+2.2);}}
    if(id==='san_pet'&&band===3){const q=sub(r,.96);pennant(q.x-q.w/2-.02,q.y-q.h/2-.02,40,16,this.iso(q.x-q.w/2,q.y-q.h/2)[1]+1.5);}
    if(id==='den_vang'&&band>=2){const [a,b]=this.iso(r.x,r.y),glow=s.add.ellipse(a,b-(band===3?90:50),r.w*this.N*HW*(band===3?2.6:1.9),band===3?190:110,0xffe37a,.0).setDepth(this.iso(r.x-r.w/2,r.y-r.h/2)[1]);
      s.tweens.add({targets:glow,fillAlpha:{from:.08,to:.26},duration:2200,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});out.push(glow);}
    if(id==='tuong_bang'&&band===3){for(const [dx,dy] of [[-1,1],[1,-1]] as const){const x=r.x+dx*r.w*.9,y=r.y+dy*r.h*.9,[a,b]=this.iso(x,y);
      const bowl=s.add.graphics().setDepth(b);bowl.fillStyle(C.iron,1).fillRect(a-2,b-22,4,22);bowl.fillStyle(C.goldD,1).fillEllipse(a,b-24,18,7);out.push(bowl);
      const fire=s.add.ellipse(a,b-32,12,18,0xff8a1f,.95).setDepth(b+.1),core=s.add.ellipse(a,b-30,6,10,0xffe37a,1).setDepth(b+.2);
      s.tweens.add({targets:[fire,core],scaleY:{from:.85,to:1.2},duration:300+dx*40+200,yoyo:true,repeat:-1});out.push(fire,core);}}
    return out;
  }

  private paintPlot(p:Rect&{id:string;kind:string},rand:()=>number){
    if(p.kind==='flowers'||p.kind==='pond')return;
    if(['ring','teahouse','pagoda','lighthouse'].includes(p.kind)){this.zone(p);return;}
    const seed=Math.round(rand()*1e6);
    if(p.kind==='bamboo')this.bake(p.x,p.y,k=>{const r=seeded(seed);for(let i=0;i<9;i++){const x=p.x+(r()-.5)*p.w,y=p.y+(r()-.5)*p.h,h=60+r()*40;k.bar(x,y,0,h,4,0x7fae4a);
      for(let j=1;j<4;j++)k.line(k.p(x,y,h*j/4),k.s(x,y,h*j/4,8,-6),0x5d8f35,1.5);
      for(let j=0;j<3;j++){const t=k.s(x,y,h-j*12,0,0);k.ellipse(new Phaser.Geom.Point(t.x+(j%2?8:-8),t.y),18,6,0x4f9a3a);}}},this.iso(p.x+p.w/2,p.y+p.h/2)[1]);
    if(p.kind==='lanterns')this.bake(p.x,p.y,k=>{for(let i=-1;i<=1;i++){const x=p.x+i*.03,y=p.y-i*.03;k.bar(x,y,0,46,3,C.woodD);k.line(k.s(x,y,44,0,0),k.s(x,y,44,12,0),C.woodD,2);
      const c=k.s(x,y,36,12,0);k.ellipse(c,12,15,C.red);k.ellipse(new Phaser.Geom.Point(c.x,c.y-7),6,2,C.gold);k.ellipse(new Phaser.Geom.Point(c.x,c.y),5,9,0xffd58a,.5);}},this.iso(p.x+p.w/2,p.y+p.h/2)[1]);
    if(p.kind==='pines')this.bake(p.x,p.y,k=>{const r=seeded(seed);k.ellipse(k.p(p.x,p.y),p.w*this.N*HW*2.6,p.w*this.N*HW*1.2,0x5c9a4a);k.ellipse(k.p(p.x,p.y,4),p.w*this.N*HW*2,p.w*this.N*HW*.9,0x6aa955);
      for(let i=0;i<5;i++){const x=p.x+(r()-.5)*p.w*1.4,y=p.y+(r()-.5)*p.h*1.4,h=46+r()*20;k.bar(x,y,0,14,5,0x6b4a2b);for(let j=0;j<3;j++){const b=k.s(x,y,10+j*h*.26,0,0),wd=24-j*6;k.poly([new Phaser.Geom.Point(b.x-wd,b.y),new Phaser.Geom.Point(b.x+wd,b.y),new Phaser.Geom.Point(b.x,b.y-h*.42)],j%2?0x2f6b3a:0x377a42);}}},this.iso(p.x+p.w/2,p.y+p.h/2)[1]);
    if(p.kind==='dummies')this.bake(p.x,p.y,k=>{for(const [dx,dy] of [[-.012,.012],[.016,-.016]] as const){const x=p.x+dx,y=p.y+dy;k.bar(x,y,0,42,5,C.wood);k.poly([k.s(x,y,34,-14,0),k.s(x,y,34,14,0),k.s(x,y,30,14,0),k.s(x,y,30,-14,0)],C.woodD);
      k.ellipse(k.s(x,y,24,0,0),16,22,C.thatch);k.circle(k.s(x,y,46,0,0),7,C.thatch);}},this.iso(p.x+p.w/2,p.y+p.h/2)[1]);
  }
  /** 🏝️ The zones of the island's levels (21/10): a ring, a tea pavilion, a pagoda, a lighthouse. */
  private zone(p:Rect&{id:string;kind:string}){
    const s=this.scene!,depth=this.iso(p.x+p.w/2,p.y+p.h/2)[1];
    if(p.kind==='ring')this.bake(p.x,p.y,k=>{const q=sub(p,1.02),xs=[q.x-q.w/2,q.x+q.w/2],ys=[q.y-q.h/2,q.y+q.h/2];
      for(const x of xs)for(const y of ys){k.bar(x,y,10,40,5,C.lacq);k.circle(k.p(x,y,42),4,C.gold);}
      for(const z of [24,34]){const c=k.corners(q,z);k.line(c.A,c.B,C.red,2);k.line(c.B,c.Cc,C.red,2);k.line(c.Cc,c.D,C.red,2);k.line(c.D,c.A,C.red,2);}},depth);
    if(p.kind==='teahouse')this.bake(p.x,p.y,k=>{const q=sub(p,.9);k.shadow(q);k.box(sub(q,1.1),0,6,C.woodD,C.wood);k.pillars(sub(q,.86),6,34,2,C.lacq,5);
      k.roof(sub(q,.86),34,22,C.jade,.012,C.gold);},depth);
    if(p.kind==='pagoda')this.bake(p.x,p.y,k=>{let r:Rect=sub(p,1),z=0;k.shadow(r);k.box(sub(r,1.15),0,8,C.stoneD,C.stone);z=8;
      for(let i=0;i<5;i++){const wall=sub(r,.72),h=i?16:22;k.box(wall,z,z+h,C.cream);k.face(wall,'sw',.4,.6,z,z+h*.8,C.lacq);z+=h;
        const nxt=sub(r,.78);if(i<4)k.skirt(r,nxt,z,9,C.tile,.008,C.gold);else k.roof(nxt,z,28,C.gold,.006,C.red);z+=9;r=nxt;}
      k.bar(p.x,p.y,z+26,z+48,3,C.gold);},depth);
    if(p.kind==='lighthouse'){const o=this.bake(p.x,p.y,k=>{const q=sub(p,1);k.shadow(q,1.4);k.box(sub(q,1.3),0,10,0x6b6b6b,0x8a8a8a);
      for(let i=0;i<6;i++){const a=sub(q,.8-i*.06),z0=10+i*24;k.box(a,z0,z0+24,i%2?C.red:C.white);}
      const top=sub(q,.5);k.box(top,154,170,C.iron,0xffe37a);k.roof(top,170,16,C.red,.004);},depth);
      const [a,b]=this.iso(p.x,p.y),glow=s.add.ellipse(a,b-162,46,30,0xfff0aa,.5).setDepth(depth+.1);
      s.tweens.add({targets:glow,alpha:{from:.25,to:.75},scaleX:{from:.8,to:1.25},duration:1200,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});void o;}
  }
  /** A gold lantern on a post along the roads (level 5). */
  private lantern(x:number,y:number,rand:()=>number){
    const s=this.scene!;this.bake(x,y,k=>{k.ellipse(k.s(x,y,0,4,2),18,6,0x000000,.14);k.bar(x,y,0,40,3,C.iron);k.ellipse(k.s(x,y,44,0,0),12,16,C.gold);k.ellipse(k.s(x,y,51,0,0),8,3,C.goldD);});
    const [a,b]=this.iso(x,y),glow=s.add.ellipse(a,b-44,26,26,0xffe37a,.35).setDepth(b+.2);
    s.tweens.add({targets:glow,alpha:{from:.15,to:.45},duration:1500+rand()*700,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
  }
  /** 🏝️ The next level's work site: a staked plot, scaffolding with its net, a crane and crates on the raw sand bank. */
  private worksite(r:Rect&{id:string;kind:string}){
    const depth=this.iso(r.x+r.w/2,r.y+r.h/2)[1];
    this.bake(r.x,r.y,k=>{this.plot(k,r,true);k.scaffold(sub(r,.8),56,true);},this.iso(r.x-r.w/2,r.y-r.h/2)[1]+1);
    this.bake(r.x,r.y,k=>{k.scaffold(sub(r,.8),56,false);const bx=r.x+r.w*.62,by=r.y-r.h*.1;
      k.bar(bx,by,0,128,6,C.gold);k.line(k.s(bx,by,124,0,0),k.s(bx,by,120,-80,0),C.goldD,4);k.line(k.s(bx,by,122,-60,0),k.s(bx,by,80,-60,0),C.iron,1.5);
      const hook=k.s(bx,by,80,-60,0);k.poly([new Phaser.Geom.Point(hook.x-7,hook.y),new Phaser.Geom.Point(hook.x+7,hook.y),new Phaser.Geom.Point(hook.x+7,hook.y+10),new Phaser.Geom.Point(hook.x-7,hook.y+10)],C.crate);
      for(let i=0;i<3;i++)k.box({x:r.x-r.w*.55+i*.012,y:r.y+r.h*.55,w:.011,h:.011},0,8+i*3,C.crate);},depth);
  }
  private palm(x:number,y:number,rand:()=>number){
    const lean=(rand()-.5)*30,h=88+rand()*26,leaves:Array<[number,number]>=[];for(let k=0;k<7;k++)leaves.push([40+rand()*10,rand()]);
    const o=this.bake(x,y,k=>{const top=k.s(x,y,h,lean,0);k.ellipse(k.s(x,y,0,lean*.4+18,4),50,16,0x000000,.15);
      for(let i=1;i<=8;i++){const t0=(i-1)/8,t1=i/8;k.line(k.s(x,y,h*t0,lean*t0*t0,0),k.s(x,y,h*t1,lean*t1*t1,0),0x8a6340,9);}
      for(let i=0;i<7;i++){const ang=i/7*Math.PI*2,len=leaves[i][0];k.poly([top,new Phaser.Geom.Point(top.x+Math.cos(ang)*len,top.y+Math.sin(ang)*len*.55+12),new Phaser.Geom.Point(top.x+Math.cos(ang+.35)*len*.7,top.y+Math.sin(ang+.35)*len*.4+6)],i%2?0x3f8a3e:0x4fa04a);}
      k.circle(new Phaser.Geom.Point(top.x-4,top.y+6),5,0x7a5a32);k.circle(new Phaser.Geom.Point(top.x+5,top.y+7),5,0x7a5a32);});
    this.scene!.tweens.add({targets:o.image,angle:{from:-1.2,to:1.2},duration:2600+rand()*1200,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
  }
  private tree(x:number,y:number,rand:()=>number){
    const h=40+rand()*16,tone=rand()>.5?0x4c9a4a:0x5aa650;
    this.bake(x,y,k=>{k.ellipse(k.s(x,y,0,10,3),46,14,0x000000,.15);k.bar(x,y,0,h,7,0x76532f);
      for(const [ox,oy,r] of [[-12,-4,18],[12,-6,17],[0,-18,20],[0,2,16]] as const)k.circle(k.s(x,y,h,ox,oy),r,shade(tone,oy<-10?1.1:.92));
      k.circle(k.s(x,y,h,-6,-22),5,0xffffff,.18);});
  }
  /** The bang's own boat beside the pier, its sail in the bang's colour. */
  private paintBoat(){
    const old=this.parts.get('boat');if(old){for(const o of old.objects)o.destroy();for(const k of old.keys)if(this.scene!.textures.exists(k))this.scene!.textures.remove(k);}
    const [x,y]=atScreen(.075,.5),flag=hex(this.bang.color,0xc2410c);
    const o=this.bake(x,y,k=>{const c=k.p(x,y);const pt=(dx:number,dy:number)=>new Phaser.Geom.Point(c.x+dx,c.y+dy);
      k.ellipse(pt(0,6),130,26,0xffffff,.4);
      k.poly([pt(-60,-6),pt(64,-12),pt(48,10),pt(-52,10)],0x8a5a32);k.poly([pt(-54,4),pt(46,4),pt(48,10),pt(-52,10)],0x5a3a20);
      k.poly([pt(-30,-8),pt(26,-8),pt(26,-20),pt(-30,-20)],0xb5844f);
      k.line(pt(0,-8),pt(0,-110),0x5a3a20,3);k.poly([pt(3,-106),pt(3,-22),pt(52,-30)],flag);k.poly([pt(-3,-100),pt(-3,-30),pt(-40,-34)],shade(flag,.85));
      k.poly([pt(0,-110),pt(20,-104),pt(0,-98)],C.gold);});
    this.scene!.tweens.add({targets:o.image,angle:{from:-1.3,to:1.3},duration:1600,yoyo:true,repeat:-1,ease:'Sine.easeInOut'});
    this.parts.set('boat',{keys:[o.key],objects:[o.image],top:110});
  }

  /* ---- people ------------------------------------------------------------------------------------------------ */
  private texture(p:BangPerson,frame:number){
    const id=JSON.stringify([p.look,p.gender,p.dir,frame,this.revision]);let key=this.textures.get(id);
    if(key&&this.scene!.textures.exists(key))return key;
    key='bp-'+this.textures.size+'-'+this.revision;
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
      const [x,y]=this.iso(p.x,p.y),sit=p.pose==='sit',bow=p.pose==='bow';
      a.image.setVisible(!p.hidden).setPosition(x,y+(sit?10:0)).setDepth(y+.5).setAngle(bow?8:0);
      if(sit)a.image.setCrop(0,0,120,128);else a.image.setCrop();
      a.ripple.setVisible(false);
    }
    for(const [id,a] of this.actors)if(!seen.has(id)){a.image.destroy();a.ripple.destroy();this.actors.delete(id);}
    const cam=s.cameras.main,focus=frame.focus;
    if(focus){const [fx,fy]=this.iso(focus[0],focus[1]);const tx=fx,ty=fy-40+(frame.shift||0)/cam.zoom,mx=cam.scrollX+cam.width/2,my=cam.scrollY+cam.height/2;
      const k=Math.abs(tx-mx)+Math.abs(ty-my)>1200?1:.12;cam.centerOn(mx+(tx-mx)*k,my+(ty-my)*k);this.clamp();}
  }
}
