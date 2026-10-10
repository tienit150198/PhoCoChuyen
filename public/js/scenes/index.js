/** Legacy canvas scenes. Vocabulary stays renderer-free for the main island and shared UI. */
import shop from './shop.js';
import {KIND_OF,kindOf} from './vocabulary.js';
export {KIND_OF,kindOf,wordsFor} from './vocabulary.js';

const loaded={shop},waiting={},listener={};
function load(kind){
  return waiting[kind]??=import(`./${kind}.js`).then(m=>{loaded[kind]=m.default;return m.default;})
    .catch(error=>{console.warn('Chưa có cảnh',kind,error);loaded[kind]=shop;return shop;})
    .then(scene=>{listener[kind]?.();delete listener[kind];return scene;});
}
/** The scene module for a career, or `shop` while its kind is still loading.
 * `onReady` runs once when the real one arrives (the latest caller wins; the
 * draw loop asks every frame, so nothing piles up). */
let hinted=null;
export function sceneFor(career,onReady){
  const kind=kindOf(career);
  // boot.js preloads this scene on the next visit (sceneFor runs every frame: store only on change).
  if(kind!==hinted){hinted=kind;try{localStorage.setItem('mnl.scene',`/js/scenes/${kind}.js`);}catch{/* storage blocked */}}
  if(loaded[kind])return loaded[kind];
  if(onReady)listener[kind]=onReady;
  load(kind);
  return shop;
}
/** Load every scene kind now (startup, tools) so no career flashes the shop. */
export const loadAllScenes=()=>Promise.all([...new Set(Object.values(KIND_OF))].filter(k=>!loaded[k]).map(load));
