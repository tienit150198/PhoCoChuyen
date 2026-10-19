/** ⚔️ Đảo bang: the entry (data-action="bangIsland", optional data-bang="<bang id>") and the hooks of the facility
 * buttons. Shown only while the server has it on (bootstrap content.bang_island: MNL_BANG_ISLAND=1, game/bang_island.py).
 * The Bang branch's own sheet opens it with openBangIsland(env, {bang}) and wires its buttons with
 * registerBangIslandAction(op, handler) (or 'facility:op'); a button without a hook asks the server
 * (POST /api/bang-island/act, the provider's act or a "sắp có" line). Styles: /css/bang-island.css. */
import {layout} from '../bang-island-layout.js';

export const ACTIONS={bangIsland:''};
const HOOKS=new Map();
/** `handler({env, bang, facility, op})` → {message?, placeholder?} (shown in the panel) or nothing; may open its own sheet. */
export function registerBangIslandAction(op,handler){if(typeof handler==='function')HOOKS.set(String(op),handler);else HOOKS.delete(String(op));}
globalThis.__mnlBangIsland={register:registerBangIslandAction,open:(env,o)=>openBangIsland(env,o)};

const url=bang=>'/api/bang-island'+(bang?`?bang=${encodeURIComponent(bang)}`:'');
async function load(env,bang){return env.api.json(url(bang));}
async function act(env,bang,facility,op){
  const hook=HOOKS.get(`${facility}:${op}`)||HOOKS.get(op);
  if(hook)return (await hook({env,bang,facility,op}))||null;
  const api=env.api;
  const out=await api.json('/api/bang-island/act',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify({bang,facility,op})});
  return {...(out.done||{}),bang:out.bang,now:out.now};
}

let active=null;
/** Open a bang's island: the player's own bang, or `bang` (a guest's invitation). */
export function openBangIsland(env,{bang=''}={}){
  if(active)return active;
  if(env.api.state?.jail)return env.act?.('jail');
  active=(async()=>{
    try{
      const [{stylesheet},scene]=await Promise.all([import('../lazy.js'),import('./bang-island-scene.js')]);
      await stylesheet('/css/bang-island.css');
      const isle=await load(env,bang);
      if(!isle?.bang){active=null;env.toast?.(isle?.why||'Bạn chưa vào bang nào.');return null;}
      const id=isle.bang.id,L=layout();
      const session=scene.createBangIslandSession(env,{isle,view:scene.createView(),
        actions:{run:(facility,op)=>act(env,id,facility,op),refresh:()=>load(env,id)},
        loadRenderer:(view,looks)=>scene.loadRendererFor(env,view,L,looks),
        loadLive:async()=>{const network=await import('./live.js');env.bootLive?.(network);return network.live;},
        onClose:()=>{active=null;}});
      await session.start();return session;
    }catch(e){active=null;env.toast?.(e?.message||'Chưa mở được đảo bang. Thử lại nhé.',true);return null;}
  })();
  return active;
}
export async function bangIslandAction(action,data,el,env){
  if(!(action in ACTIONS))return false;
  await openBangIsland(env,{bang:data?.bang||''});return true;
}
