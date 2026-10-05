/** Retain a character's twelve small poses until their outfit changes or they leave.
 * Walking must not allocate/destroy textures or GPU uploads on every animation tick.
 */
export class TextureFrames {
  private owners=new Map<string,{appearance:string;poses:Map<string,string>}>();
  private sequence=0;
  constructor(private remove:(key:string)=>void){}
  get(owner:string,appearance:string,pose:string,create:(key:string)=>void){
    let entry=this.owners.get(owner);
    if(entry?.appearance!==appearance){this.release(owner);entry={appearance,poses:new Map()};this.owners.set(owner,entry);}
    const existing=entry.poses.get(pose);if(existing)return existing;
    const key=`character-frame-${++this.sequence}`;create(key);entry.poses.set(pose,key);return key;
  }
  release(owner:string){const entry=this.owners.get(owner);if(!entry)return;for(const key of entry.poses.values())this.remove(key);this.owners.delete(owner);}
  clear(){for(const owner of this.owners.keys())this.release(owner);}
  get size(){let count=0;for(const entry of this.owners.values())count+=entry.poses.size;return count;}
}
