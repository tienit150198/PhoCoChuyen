import Phaser from 'phaser';
import {project} from './model';
import type {PetRef,Point} from './model';
// 🐾 Owner 19/10 ("đi thị trấn hoặc đi đâu cũng cho phép dẫn theo", "cún cưng to hơn tí"): the pet a player walks
// trails them through the town, sits when they stop, and wears its 🏅 rank's aura (public/js/v4/pet-art.js, the same
// art as the old street). A namespace import: a scene without the module simply shows no pets.
// @ts-ignore runtime module (public/js/v4/pet-art.js)
import * as PetArt from '/js/v4/pet-art.js';
const PA:any=PetArt;

/** How far behind (in tiles) a pet keeps; farther than JUMP (a door, a new map) it is simply put back beside you. */
const KEEP=.42,JUMP=3;
/** Base on-screen width of a walking / sitting pet (a character is ~100 px tall), before refBox and walkScale. */
const WALK_W=60,SIT_W=52;
/** Pet textures kept at most (2 poses each); the oldest unused ones go first. */
const MAX_TEXTURES=80;
const RES=150;

type Follower={ref:PetRef;sig:string;at:Point;face:number;still:number;pose:string;image:Phaser.GameObjects.Image;texture:string};
const px=(p:Point)=>project(p);

export class PetWalkers {
  private all=new Map<string,Follower>();
  private loading=new Set<string>();
  private order:string[]=[];
  constructor(private scene:Phaser.Scene,private ready:()=>void){}
  get size(){return this.all.size;}
  /**
   * One frame of the pet of `id` following `owner` (ground point; null: not shown, e.g. riding or off screen).
   * Returns whether it moved (the loop stays awake while a pet catches up).
   */
  step(id:string,ref:PetRef|undefined|null,owner:Point|null,dt:number,cat:any,reduced:boolean):boolean{
    let f=this.all.get(id);
    if(!ref||!owner||!PA.refURL){if(f)f.image.setVisible(false);return false;}
    const sig=JSON.stringify([ref.b,ref.c,ref.a,ref.r||0,ref.x||'']);
    if(!f){
      const image=this.scene.add.image(0,0,'__DEFAULT').setVisible(false);
      f={ref,sig,at:{x:owner.x-KEEP*.7,y:owner.y-KEEP*.7},face:1,still:1,pose:'',image,texture:''};this.all.set(id,f);
    }else if(f.sig!==sig){f.ref=ref;f.sig=sig;f.pose='';}
    const dx=f.at.x-owner.x,dy=f.at.y-owner.y,d=Math.hypot(dx,dy);let moved=false;
    if(d>JUMP){f.at={x:owner.x-KEEP*.7,y:owner.y-KEEP*.7};f.still=1;}
    else if(d>KEEP+.01){
      const goal={x:owner.x+dx/d*KEEP,y:owner.y+dy/d*KEEP},k=reduced?1:1-Math.exp(-dt*9),next={x:f.at.x+(goal.x-f.at.x)*k,y:f.at.y+(goal.y-f.at.y)*k};
      const sx=px(next).x-px(f.at).x;if(Math.abs(sx)>.3)f.face=sx>0?1:-1;
      moved=Math.hypot(next.x-f.at.x,next.y-f.at.y)>.0015;f.at=next;
    }
    f.still=moved?0:f.still+dt;
    const pose=reduced||f.still>.25?'sit':'walk';
    if(pose!==f.pose||!f.texture||!this.scene.textures.exists(f.texture)){
      const key=this.texture(cat,ref,pose,sig);
      if(key){f.image.setTexture(key);f.texture=key;f.pose=pose;
        const B=PA.refBox?PA.refBox(cat,ref,pose):{w:72,h:62,foot:58/62,k:1,base:72},w=(pose==='walk'?WALK_W:SIT_W)*B.w/B.base*B.k;
        f.image.setDisplaySize(w,w*B.h/B.w).setOrigin(.5,B.foot);}
    }
    const at=px(f.at),bob=pose==='walk'&&!reduced?-Math.abs(Math.sin(this.scene.time.now/70))*2:0;
    f.image.setVisible(!!f.texture).setFlipX(f.face<0).setPosition(at.x,at.y+bob).setDepth(at.y+.4);
    return moved||f.still<.3;
  }
  hide(id:string){this.all.get(id)?.image.setVisible(false);}
  drop(id:string){const f=this.all.get(id);if(f){f.image.destroy();this.all.delete(id);}}
  /** Forget the pets of everyone not in `keep`. */
  prune(keep:Set<string>){for(const id of [...this.all.keys()])if(!keep.has(id))this.drop(id);}
  clear(){for(const id of [...this.all.keys()])this.drop(id);}
  /** The texture of a pet in a pose, or '' while its picture loads (`ready` is called once it can be drawn). */
  private texture(cat:any,ref:PetRef,pose:string,sig:string):string{
    const key='iso-pet-'+pose+'-'+hash(sig);
    if(this.scene.textures.exists(key))return key;
    if(this.loading.has(key))return '';
    const url=PA.refURL(cat,ref,pose,RES);if(!url)return '';
    this.loading.add(key);const img=new Image();
    img.onload=()=>{this.loading.delete(key);if(!this.scene.sys?.isActive?.()||this.scene.textures.exists(key))return;this.scene.textures.addImage(key,img);this.order.push(key);this.trim();this.ready();};
    img.onerror=()=>{this.loading.delete(key);};
    img.src=url;return '';
  }
  private trim(){
    if(this.order.length<=MAX_TEXTURES)return;
    const used=new Set([...this.all.values()].map(f=>f.texture));
    for(let i=0;i<this.order.length&&this.order.length>MAX_TEXTURES;){const key=this.order[i];if(used.has(key)){i++;continue;}this.order.splice(i,1);if(this.scene.textures.exists(key))this.scene.textures.remove(key);}
  }
}
function hash(s:string){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return (h>>>0).toString(36);}
