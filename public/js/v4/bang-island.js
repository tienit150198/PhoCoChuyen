/** ⚔️ Đảo bang: the entry (data-action="bangIsland", optional data-bang="<bang id>") and the hooks of the facility
 * buttons. Shown only while the server has it on (bootstrap content.bang_island: MNL_BANG_ISLAND=1, game/bang_island.py).
 * The Bang branch's own sheet opens it with openBangIsland(env, {bang}) and wires its buttons with
 * registerBangIslandAction(op, handler) (or 'facility:op'); a button without a hook asks the server
 * (POST /api/bang-island/act, the provider's act or a "sắp có" line). Styles: /css/bang-island.css.
 * Wired to the real bangs (game/bang_island_source.py): ⬆️ Nâng cấp asks the server (the bang's build, confirmed
 * first: {confirm} → env.confirmAction → {confirm: true}); the other buttons open the right sheet (DEFAULT_HOOKS). */
import {layout} from '../bang-island-layout.js';

export const ACTIONS={bangIsland:''};
const HOOKS=new Map();
let meKind='';   // 'member' | 'guest' of the island open now (the last GET)
/** `handler({env, bang, facility, op})` → {message?, placeholder?} (shown in the panel) or nothing; may open its own sheet. */
export function registerBangIslandAction(op,handler){if(typeof handler==='function')HOOKS.set(String(op),handler);else HOOKS.delete(String(op));}
globalThis.__mnlBangIsland={register:registerBangIslandAction,open:(env,o)=>openBangIsland(env,o)};

const url=bang=>'/api/bang-island'+(bang?`?bang=${encodeURIComponent(bang)}`:'');
async function load(env,bang){const out=await env.api.json(url(bang));meKind=out?.me?.kind||'';return out;}
const post=(api,body)=>api.json('/api/bang-island/act',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body)});
async function act(env,bang,facility,op){
  const hook=HOOKS.get(`${facility}:${op}`)||HOOKS.get(op);
  if(hook)return (await hook({env,bang,facility,op,guest:meKind==='guest'}))||null;
  const api=env.api;
  let out=await post(api,{bang,facility,op});
  const ask=out?.done?.confirm;
  if(ask){   // the bang's build: one confirmation with the price, then the real command
    const yes=await env.confirmAction?.(ask.title||'Xác nhận',ask.text||'',ask.label||'Xác nhận');
    if(!yes)return {message:'Chưa xây gì cả.',bang:out.bang,now:out.now};
    out=await post(api,{bang,facility,op,data:{confirm:true}});
  }
  return {...(out.done||{}),bang:out.bang,now:out.now};
}
/* The buttons that open a sheet of their own: the bang's (v4/bang.js, on top of the island) or the pet arena. */
const GUEST_LINE='Bạn đang là khách của bang này. Vào bang để dùng nhé.';
const sheet=(action,data,members=true)=>async({env,guest})=>{
  if(members&&guest)return {message:GUEST_LINE,placeholder:true};
  await env.act?.(action,data);return {message:'Đã mở.'};
};
const DEFAULT_HOOKS={
  thanh_vien:sheet('bang',{tab:'members'}), moi_khach:sheet('bang',{tab:'members'}),
  gop_quy:sheet('bang',{tab:'home'}), gio_vang:sheet('bang',{tab:'home'}),
  xuong_may:sheet('bang',{tab:'shop'}), xep_hang:sheet('bang',{tab:'rank'}),
  dau_truong:sheet('petArena',{tab:'war',sec:'war'},false), luyen_pet:sheet('petArena',{tab:'npc'},false),
  thach_dau:sheet('petArena',{tab:'war',sec:'tc'}),   // ⚔️ Thách đấu bang (owner 21/10): members only, the bang's roster and its challenges
};
for(const [op,fn] of Object.entries(DEFAULT_HOOKS))HOOKS.set(op,fn);

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
      // 🏝️ the bang has not bought its island (21/10): the Bang sheet's island card (buy it, or ask an officer to)
      if(!isle?.bang&&isle?.offer){active=null;env.act?.('bang',{tab:'home',isle:1});return null;}
      if(!isle?.bang){active=null;env.toast?.(isle?.why||'Bạn chưa vào bang nào.');env.act?.('bang',{});return null;}   // in no bang: the Bang sheet (find or found one)
      const id=isle.bang.id;
      const session=scene.createBangIslandSession(env,{isle,view:scene.createView(),
        actions:{run:(facility,op)=>act(env,id,facility,op),refresh:()=>load(env,id)},
        loadRenderer:(view,looks,L)=>scene.loadRendererFor(env,view,L||layout(),looks),
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
