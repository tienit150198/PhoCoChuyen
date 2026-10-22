/** 🤝 Phụ kiện đôi on the client (game/friend_charms.py, góp ý #484, owner 22/10): a pair bought at Tiệm phụ kiện
 * (v4/acc-shop.js), one piece given to a friend; both wear it, each sees the other's name. No save key: the rows live in
 * the database, so the bootstrap carries `charms` {worn, incoming} (server.py) and every /api/marriage/charm_* answer the
 * whole view {box, sent, incoming, pairs, worn, friends…}. What the character wears goes to look.js (setPairs), which
 * draws it on the classic scene, the 2.5D map and the portraits. Small and loaded with the journey: the profile and the
 * wardrobe list the pairs; buying, giving and answering are in the shop module. */
import {escapeHTML as esc} from '../icons.js';
import {setPairs,myPairs,pairIcon} from './look.js';

export const kinds=api=>api.content?.journey?.wardrobe?.pairs?.kinds||[];
export const kindOf=(api,id)=>kinds(api).find(k=>k.id===id)||null;
export const shopName=api=>api.content?.journey?.wardrobe?.acc_shop?.name||'Tiệm phụ kiện';
/** Offers waiting for this player (the view's list once read, else the bootstrap's count). */
export const waiting=api=>Array.isArray(api.charmView?.incoming)?api.charmView.incoming.length:Number(api.charms?.incoming)||0;

/** The bootstrap's part (app.js, right after api.init): what the character wears from the first frame. */
export function charmsBoot(api){setPairs(api.charms?.worn);}

/** Take an answer of /api/marriage/charm_*: the pairs worn first (the redraw that follows already has them), then the
 * save when money moved (api.accept: everything redraws), else `redraw` (the scenes' player texture keys on the pairs). */
export function adopt(api,data,redraw){
  const v=data?.charms;
  if(v&&typeof v==='object'){
    api.charmView={...v,at:Date.now()};api.charms={worn:v.worn||{},incoming:Array.isArray(v.incoming)?v.incoming.length:0};
    setPairs(v.worn);
  }
  if(data?.state&&typeof data.revision==='number')api.accept({state:data.state,revision:data.revision});
  else redraw?.();
  globalThis.document?.dispatchEvent?.(new Event('mnl:badges'));   // the menu's badge (app.js)
}

let loading=null;
/** Read the view again (charm_view) unless one younger than `fresh` ms is in: the promise of the new view (null for a guest
 * or offline), or null when nothing was asked (so a caller redraws only after a real read). */
export function refreshCharms(env,fresh=30000){
  const {api}=env;
  if(api.charmView&&Date.now()-api.charmView.at<fresh)return null;
  if(!api.account?.username&&!api.charms)return null;
  return loading??=api.json('/api/marriage/charm_view',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:'{}'})
    .then(d=>{adopt(api,d,null);return api.charmView;}).catch(()=>null).finally(()=>{loading=null;});
}

/** A pair's row: the two pieces, the kind, the friend, and its own wear switch (actions jrAs*, v4/acc-shop.js). */
export function pairRow(api,p){
  const k=kindOf(api,p.kind);if(!k)return '';
  return `<li class="as-pair${p.on?' on':''}"><label class="switch-row"><span class="as-pair-art">${pairIcon(p.kind,44)}</span>
    <span class="grow"><b>${esc(k.emoji)} ${esc(k.name)}</b><small class="block">với ${esc(p.name||'một người bạn')}</small></span>
    <input type="checkbox" role="switch" data-action="jrAsWear" data-id="${esc(p.id)}" ${p.on?'checked':''} aria-label="Đeo cặp ${esc(k.name)} với ${esc(p.name||'bạn')}"><i aria-hidden="true"></i></label></li>`;
}

/** What is worn by kind, as chips: "🏎️ Chí cốt ×2". */
export function wornChips(api,worn=myPairs()){
  return Object.entries(worn||{}).map(([id,n])=>{const k=kindOf(api,id);return k?`<span class="as-chip">${esc(k.emoji)} ${esc(k.name)}${n>1?` ×${n}`:''}</span>`:'';}).join('');
}

/** 👤 Nhân vật của bạn, 👗 Tủ đồ: the pairs with the friends' names (read on first sight), the switches, the way to the shop. */
export function pairsCard(env,{title='🤝 Phụ kiện đôi'}={}){
  const {api}=env,v=api.charmView,n=waiting(api);
  refreshCharms(env)?.then(x=>{if(x)env.renderSheet?.(false);});
  const pairs=v?.pairs||[],on=pairs.filter(p=>p.on).length;
  const offer=n?`<button type="button" class="btn primary small" data-action="jrAccShop" data-tab="pair">🎁 ${n} món quà đang chờ bạn nhận</button>`:'';
  const list=pairs.length?`<ul class="as-pairs">${pairs.map(p=>pairRow(api,p)).join('')}</ul>`
    :v?`<p class="muted small">Chưa có cặp nào. Mua một cặp ở ${esc(shopName(api))} rồi tặng một chiếc cho bạn thân nhé.</p>`
    :`<div class="as-chips">${wornChips(api)||'<span class="muted small">Đang xem…</span>'}</div>`;
  const all=pairs.length>1?`<button type="button" class="btn ghost small" data-action="jrAsWearAll" data-on="${on?'0':'1'}">${on?'Cất hết':'Đeo hết'}</button>`:'';
  return `<section class="jr-card as-mine" aria-label="Phụ kiện đôi"><div class="as-mine-head"><b>${title}</b>${pairs.length?`<small class="muted">đang đeo ${on}/${pairs.length}</small>`:''}</div>
    ${offer}${list}<div class="as-mine-foot">${all}<button type="button" class="btn ghost small" data-action="jrAccShop" data-tab="pair">🛍️ ${esc(shopName(api))}</button></div></section>`;
}
