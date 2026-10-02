/** What a drawing read of the game, so a cached drawing is kept until something it used changes.
 *
 * BobaWorld paints its room into an offscreen backdrop (boba-world.js backdrop()). Before, every state from the
 * server repainted it; now the paint sees the game (world.c, world.state, world.game) through read-only views
 * that note each value read, and a new state only repaints when one of those values differs. A milk tea order
 * that changes the queue repaints (the order screen counts it); one that only moves the clock does not.
 *
 *   const reads=watch(world,['c','state','game']);try{paint();}finally{reads.stop();}
 *   ...
 *   if(reads.same(world))keep the drawing; else paint again (and watch again).
 *
 * Plain objects and arrays are watched; anything else (a Map, a class instance) is handed out as is and noted
 * by identity. A view never changes the data: writes go through to it, as they would without the view. */

/** Dev only, the same switch as api.js's state check (localhost with ?deltacheck=1 or localStorage
 * mnl.deltacheck=1): boba-world.js paints each kept backdrop again and compares the pixels. */
export const CHECK=(()=>{try{return /^(localhost|127\.0\.0\.1)$/.test(globalThis.location?.hostname||'')&&(/[?&]deltacheck=1\b/.test(globalThis.location.search)||globalThis.localStorage?.getItem('mnl.deltacheck')==='1');}catch{return false;}})();

const GONE=Symbol('gone');   // a path that no longer leads anywhere
const plain=v=>{const p=Object.getPrototypeOf(v);return p===Object.prototype||p===Array.prototype||p===null;};
const isObj=v=>v!==null&&typeof v==='object';
/** Compared value: objects by kind (their contents are noted read by read), others as they are. */
const shape=v=>!isObj(v)?v:!plain(v)?v:Array.isArray(v)?'[]':'{}';
const names=o=>Reflect.ownKeys(o).filter(k=>typeof k==='string').join('\u0000');

/** Start noting reads of world[root] for each root; world[root] is a view until stop(). */
export function watch(world,roots){
  const log=[],views=new Map(),saved=roots.map(r=>world[r]);let on=true;
  const note=(root,path,how,value)=>{if(on)log.push([root,path,how,value]);};
  const view=(obj,root,path)=>{
    if(!isObj(obj)||!plain(obj))return obj;
    let v=views.get(obj);if(v)return v;
    // A stand-in target: the dev check (api.js) freezes states, and a proxy of a frozen object must answer as it.
    v=new Proxy(Array.isArray(obj)?[]:{},{
      get(_,k){const x=Reflect.get(obj,k);if(typeof k==='symbol'||typeof x==='function')return x;
        const at=[...path,k];note(root,at,'get',shape(x));return view(x,root,at);},
      has(_,k){const x=Reflect.has(obj,k);if(typeof k!=='symbol')note(root,[...path,k],'has',x);return x;},
      ownKeys(){note(root,path,'keys',names(obj));return Reflect.ownKeys(obj);},
      getOwnPropertyDescriptor(_,k){const d=Reflect.getOwnPropertyDescriptor(obj,k);
        if(typeof k!=='symbol')note(root,[...path,k],'own',!!d);
        if(!d)return undefined;
        if(k==='length'&&Array.isArray(obj))return {value:obj.length,writable:true,enumerable:false,configurable:false};
        const at=[...path,k];if('value' in d)note(root,at,'get',shape(d.value));
        return {value:'value' in d?view(d.value,root,at):Reflect.get(obj,k),writable:true,enumerable:d.enumerable,configurable:true};},
      set(_,k,x){return Reflect.set(obj,k,x);},
      deleteProperty(_,k){return Reflect.deleteProperty(obj,k);},
      defineProperty(){return false;},
    });
    views.set(obj,v);return v;};
  roots.forEach((r,i)=>{note(r,[],'get',shape(saved[i]));world[r]=view(saved[i],r,[]);});
  return {
    log,
    /** Hand the real data back; later reads through a kept view are not noted. */
    stop(){on=false;roots.forEach((r,i)=>{if(world[r]===view(saved[i],r,[]))world[r]=saved[i];});return this;},
    /** Does every noted read give the same value on world as it is now? */
    same(w){for(const e of log)if(!Object.is(again(w,e),e[3]))return false;return true;},
  };
}

/** One noted read, done again on the world as it is now. */
function again(w,[root,path,how]){
  let o=w[root];const n=how==='has'||how==='own'?path.length-1:path.length;
  for(let i=0;i<n;i++){if(!isObj(o))return GONE;o=o[path[i]];}
  if(how==='get')return shape(o);
  if(!isObj(o))return GONE;
  if(how==='keys')return names(o);
  const k=path[path.length-1];return how==='has'?k in o:Object.prototype.hasOwnProperty.call(o,k);
}
