import type {Point,Rect} from './model';

export const intersects=(a:Rect,b:Rect)=>a.x0<=b.x1&&a.x1>=b.x0&&a.y0<=b.y1&&a.y1>=b.y0;
/** Immutable scene bounds are indexed once, not recomputed for every rendered frame. */
export class SpatialIndex<T> {
  private cells=new Map<string,Array<{value:T;bounds:Rect}>>();
  constructor(private size=256){}
  clear(){this.cells.clear();}
  add(value:T,bounds:Rect){
    const entry={value,bounds};
    for(let y=Math.floor(bounds.y0/this.size);y<=Math.floor(bounds.y1/this.size);y++)for(let x=Math.floor(bounds.x0/this.size);x<=Math.floor(bounds.x1/this.size);x++){
      const key=x+':'+y;let cell=this.cells.get(key);if(!cell){cell=[];this.cells.set(key,cell);}cell.push(entry);
    }
  }
  query(bounds:Rect):T[]{
    const found=new Set<T>();
    for(let y=Math.floor(bounds.y0/this.size);y<=Math.floor(bounds.y1/this.size);y++)for(let x=Math.floor(bounds.x0/this.size);x<=Math.floor(bounds.x1/this.size);x++){
      for(const item of this.cells.get(x+':'+y)||[])if(intersects(bounds,item.bounds))found.add(item.value);
    }
    return [...found];
  }
}
export interface AlphaMask {width:number;height:number;alpha:Uint8Array}
export interface OccludingShape {bounds:Rect;depth:number;mask:AlphaMask}
export function coversPlayer(player:Point&{depth:number},shape:OccludingShape){
  if(shape.depth<=player.depth)return false;
  const r=shape.bounds,m=shape.mask,w=r.x1-r.x0,h=r.y1-r.y0;
  // Chest and head, not the feet: a soft ground shadow should never fade a house.
  for(const dy of [-27,-52,-77])for(const dx of [-13,0,13]){
    const x=player.x+dx,y=player.y+dy;if(x<r.x0||x>=r.x1||y<r.y0||y>=r.y1)continue;
    const column=Math.floor((x-r.x0)/w*m.width),row=Math.floor((y-r.y0)/h*m.height);
    if(m.alpha[row*m.width+column]>=64)return true;
  }
  return false;
}
export function fadeAlpha(current:number,target:number,dt:number,reduced=false){
  if(reduced)return target;
  if(!Number.isFinite(dt)||dt<=0)return current;
  const next=current+(target-current)*(1-Math.exp(-16*Math.min(.06,dt)));
  return Math.abs(next-target)<.008?target:next;
}
