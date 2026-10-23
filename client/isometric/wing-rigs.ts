import Phaser from 'phaser';
// Namespace imports, like VehicleArt: a scene without these modules (an older cached copy, a test double) shows no wings.
// @ts-ignore runtime module: the wings' canvases (shared by everyone wearing the same wing)
import * as CharacterArt from '/js/isometric/character-art.js';
// @ts-ignore runtime module: the beat and the light, the same numbers as the classic street and the shop
import * as WingsArt from '/js/v4/wings-art.js';
const C:any=CharacterArt,W:any=WingsArt;
/** True when both runtime modules carry the wings. */
export const wingsAvailable=()=>typeof W.cleanWing==='function'&&typeof W.wingOfState==='function'&&typeof C.stampWingFrame==='function'&&!!C.STAMP_WING;
/** The wing a save wears (v4/wings-art.js wingOfState), or null. */
export const wornWing=(state:any)=>typeof W.wingOfState==='function'?W.wingOfState(state):null;

/** 🪽 Animated wings on the 2.5D map (owner 22/10 "cánh có hoạt họa, có tia sáng này kia nhé").
 * The chibi stamp is drawn without its wings (phaser-world.ts characterTexture); each winged character gets a rig of
 * plain images around it instead:
 *   glow   the tier's light behind it from S, breathing (alpha)
 *   rays   light rays from S, turning slowly (rotation), ADD blended
 *   ring   SSS / Huyền thoại: a ring of light sent out every 2.6 s (scale, alpha)
 *   wing   the pair (owner 23/10 "cho đẹp hơn, to hơn": spread wide past the head), one of FLAP_STEPS cached canvases
 *          picked by the style's own beat (butterfly quick, dragon slow), a gentle stroke standing, the full one walking:
 *          behind the chibi when it faces us, over its back seen from behind (the stamp's own layering); one set of
 *          canvases for both views and for everyone wearing that wing
 *   motes  sparkles drifting off the wings (pooled images moved by moteAt, a pure function of the time)
 * No canvas is drawn per frame: only textures picked and images moved. The scene sleeps as before; while a moving rig is
 * in view the world wakes it ~15 times a second for one frame (PhaserWorld.wingTick). Caps: LIVE characters move (me
 * first, then the nearest), the rest wear still wings; MAX_MOTES sparkles in all. Reduced motion: still wings, the
 * glow and rays still, no motes, no ring. */
export const LIVE=8,MAX_MOTES=48,WING_FPS=15;
type Rig={wg:string;glow?:Phaser.GameObjects.Image;rays?:Phaser.GameObjects.Image;ring?:Phaser.GameObjects.Image;wing:Phaser.GameObjects.Image;motes:Phaser.GameObjects.Image[];phase:number};
export type WingHost={image:Phaser.GameObjects.Image;wg:any;direction:string;top:[number,number]|null;show:boolean;live:boolean;walk?:boolean};
export class WingRigs{
  private rigs=new Map<string,Rig>();
  constructor(private scene:Phaser.Scene){}
  private texture(key:string,canvas:HTMLCanvasElement|null|undefined){
    if(!canvas)return '';if(!this.scene.textures.exists(key))this.scene.textures.addCanvas(key,canvas);return key;
  }
  /** One frame for `id`; returns how many motes it used. `budget` the motes still allowed. */
  sync(id:string,h:WingHost,t:number,budget:number){
    const w=W.cleanWing(h.wg),ADD=Phaser.BlendModes.ADD;
    if(!w||!h.show||!h.top){const rig=this.rigs.get(id);if(rig)this.hide(rig);if(!w&&rig)this.drop(id);return 0;}
    const sig=w.k+':'+w.r;let rig=this.rigs.get(id);
    if(rig&&rig.wg!==sig){this.drop(id);rig=undefined;}
    if(!rig){rig={wg:sig,wing:this.scene.add.image(0,0,'__DEFAULT'),motes:[],phase:(id.length*1.37+[...id].reduce((a,c)=>a+c.charCodeAt(0),0)*.071)%3};this.rigs.set(id,rig);}
    const back=h.direction==='nw'||h.direction==='ne',v=back?C.STAMP_WING.back:C.STAMP_WING.front,host=h.image,sc=host.scaleX,depth=host.depth;
    const rx=host.x+(h.top[0]-60)*sc,ry=host.y+(h.top[1]+v.dy-160)*sc,still=!h.live||W.stillMotion(),tt=t+rig.phase,ss=W.wingScale(w,v.s);
    // the wing: a cached flap
    const f=still?0:W.flapStep(W.flapAt(w.k,tt,!!h.walk)),frame=C.stampWingFrame(w,back,f),cy=(W.LIGHT_Y??32)*ss*sc;
    const key=this.texture(`wg-f:${w.k}:${w.r}:${f}`,frame?.canvas);
    if(key){if(rig.wing.texture.key!==key)rig.wing.setTexture(key);rig.wing.setOrigin(frame.ox/frame.w,frame.oy/frame.h).setScale(sc).setPosition(rx,ry).setDepth(depth+(back?.001:-.001)).setVisible(true);}else rig.wing.setVisible(false);
    // the light behind: glow, rays, ring (from S)
    if(w.r>=4){
      if(!rig.glow){const g=C.stampWingLight('glow',w,back),k=this.texture(`wg-g:${w.k}:${w.r}`,g?.canvas);if(k)rig.glow=this.scene.add.image(0,0,k).setOrigin(g.ox/g.canvas.width,g.oy/g.canvas.height);}
      if(rig.glow)rig.glow.setScale(sc).setPosition(rx,ry).setDepth(depth-.002).setAlpha(still?1:W.wingPulse(tt)).setVisible(true);
      if(!rig.rays){const g=C.stampWingLight('rays',w,back),k=this.texture(`wg-r:${w.r}`,g?.canvas);if(k)rig.rays=this.scene.add.image(0,0,k).setBlendMode(ADD);}
      const ry2=W.raysAt(w.r,tt);
      if(rig.rays&&ry2)rig.rays.setScale(sc).setPosition(rx,ry-cy).setDepth(depth-.0025).setRotation(still?0:ry2.rot).setAlpha(still?.85:ry2.a).setVisible(true);
      if(w.r>=6){
        if(!rig.ring){const g=C.stampWingLight('ring',w,back),k=this.texture(`wg-o:${w.r}`,g?.canvas);if(k)rig.ring=this.scene.add.image(0,0,k).setBlendMode(ADD);}
        const b=still?null:W.burstAt(tt);
        if(rig.ring){if(b)rig.ring.setScale(sc*ss*(16+b.ph*74)/44).setPosition(rx,ry-cy).setDepth(depth-.0015).setAlpha(b.a).setVisible(true);else rig.ring.setVisible(false);}
      }
    }
    // the motes over it
    let used=0;
    const motes=still?[]:W.wingMotes(w);
    motes.forEach((m:any,i:number)=>{
      let img=rig!.motes[i];const p=W.moteAt(m,tt);
      if(used>=budget||p.a<=.04){if(img)img.setVisible(false);return;}
      if(!img){const k=this.texture(`wg-m:${m.col}:${m.star?1:0}`,C.stampMote(m.col,m.star));if(!k)return;img=this.scene.add.image(0,0,k).setBlendMode(ADD);rig!.motes[i]=img;}
      const z=m.sz*ss*(.6+.4*p.a)*(m.star?1.4:1.6)/7;
      img.setPosition(rx+p.x*ss*sc,ry+p.y*ss*sc).setScale(z*sc*1.6).setAlpha(p.a).setDepth(depth+(m.burst?-.0012:.002)).setVisible(true);used++;   // a burst leaves from behind the body
    });
    for(let i=motes.length;i<rig.motes.length;i++)rig.motes[i].setVisible(false);
    return used;
  }
  private hide(rig:Rig){rig.wing.setVisible(false);rig.glow?.setVisible(false);rig.rays?.setVisible(false);rig.ring?.setVisible(false);for(const m of rig.motes)m.setVisible(false);}
  drop(id:string){const rig=this.rigs.get(id);if(!rig)return;rig.wing.destroy();rig.glow?.destroy();rig.rays?.destroy();rig.ring?.destroy();for(const m of rig.motes)m.destroy();this.rigs.delete(id);}
  /** Forget the ones not in `keep` (players who left). */
  keepOnly(keep:Set<string>){for(const id of [...this.rigs.keys()])if(!keep.has(id))this.drop(id);}
  clear(){for(const id of [...this.rigs.keys()])this.drop(id);}
  get size(){return this.rigs.size;}
}
