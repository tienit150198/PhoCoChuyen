import {live} from './v4/live.js';
import {createTreasureController} from './isometric/treasure.js';
let controller=null,current=null;
export function attachTreasure(world,getEnv){
  controller?.stop();controller=createTreasureController(getEnv,{socket:live}).start();current=world;
  const previous=world.onInteract;
  world.onInteract=id=>{if(id.startsWith('treasure:')){void controller.claim(id.slice(9));return;}previous(id);};
}
/** The real town world (its chests, its route finder, the onInteract above): ♿ isometric-pickups.js (#428). */
export const townWorld=()=>current;
