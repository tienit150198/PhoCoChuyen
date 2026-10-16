/** 🧧 Lì xì (game/lixi.py, live/lixi.py): the packets this page knows and their card in Cả phố. Small on purpose:
 * v4/chat.js imports it to draw the cards between the messages; v4/lixi.js (the falling envelopes, the dialog, grabbing,
 * giving) imports it for the same store. Both interfaces share it (the chat is one dialog for the old and the new map).
 *
 * The store fills from the live socket (`lixi`, `lixi_upd`, the welcome's `lx`) and from GET /api/lixi (the whole last
 * day, what I grabbed). A card shows the giver, the wish, how many envelopes are left, and one button: Giật while it is
 * open, then "+N xu" (mine) or "Xem" (who got how much). A blocked giver's packet comes without name or wish (`no`). */
import {escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
export const LX={packets:new Map(),got:new Map(),me:null,loaded:0,listeners:new Set()};
const valid=p=>p&&typeof p.id==='string'&&/^lx[0-9a-f]{14}$/.test(p.id);
const KEEP_S=86400;

function changed(){for(const f of [...LX.listeners]){try{f();}catch(e){console.warn('lixi:',e);}}}
/** Called again on every change of the store (the chat re-renders, the dialog too). Returns an unsubscribe. */
export function onChange(f){LX.listeners.add(f);return ()=>LX.listeners.delete(f);}

/** A packet from the live socket or the server's list (fields kept from what came before). */
export function upsert(p,quiet=false){
  if(!valid(p))return null;
  const old=LX.packets.get(p.id)||{};
  const at=Number(p.at)||old.at||Date.now()/1000;
  const q={...old,...p,at,n:Number(p.n??old.n)||1,left:Math.max(0,Number(p.left??old.left)||0),total:Number(p.total??old.total)||0};
  if('got' in p)LX.got.set(p.id,Number(p.got));
  if(!q.status)q.status=q.left>0?'open':'done';
  LX.packets.set(p.id,q);
  prune();
  if(!quiet)changed();
  return q;
}
/** `lixi_upd {id, left, done}`: an envelope taken, or the packet over. */
export function update(f){
  const p=valid(f)&&LX.packets.get(f.id);if(!p)return null;
  p.left=Math.max(0,Number(f.left)||0);
  if(f.done||p.left<=0)p.status=p.status==='open'?(p.left>0?'expired':'done'):p.status;
  changed();return p;
}
/** I grabbed this one: the amount (shown on the card). */
export function grabbed(id,amount){LX.got.set(id,Number(amount)||0);changed();}
function prune(){
  const t=Date.now()/1000;
  for(const [id,p] of LX.packets)if(t-p.at>KEEP_S)LX.packets.delete(id);
  if(LX.packets.size>60){const old=[...LX.packets.values()].sort((a,b)=>a.at-b.at).slice(0,LX.packets.size-60);for(const p of old)LX.packets.delete(p.id);}
}
export const openNow=p=>p.status==='open'&&p.left>0&&(!p.exp||p.exp>Date.now()/1000);
/** Oldest first. */
export const list=()=>[...LX.packets.values()].sort((a,b)=>a.at-b.at);

/** GET /api/lixi (at most every `every` ms): the last day's packets and what I grabbed. */
export async function refresh(api,every=15000){
  if(!api?.json||Date.now()-LX.loaded<every)return false;
  LX.loaded=Date.now();
  try{
    const d=await api.json('/api/lixi');
    for(const p of d?.packets||[])upsert(p,true);
    LX.me=d?.me||null;LX.caps=d?.caps||null;
    changed();return true;
  }catch{LX.loaded=0;return false;}
}

/** The card's button: [label, kind] — kind 'grab' (Giật), 'see' (Xem), or '' (nothing to do). */
export function cardAction(p){
  if(LX.got.has(p.id))return [`+${fmt(LX.got.get(p.id))} xu`,'see'];
  if(p.own)return ['Xem','see'];
  if(p.no)return ['',''];
  return openNow(p)?['Giật','grab']:['Xem','see'];
}
/** One card, a line of Cả phố (data-ch-act="lixi": v4/chat.js hands the tap to v4/lixi.js). */
export function cardHTML(p,act='data-ch-act="lixi"'){
  css();
  const [label,kind]=cardAction(p),open=openNow(p);
  const who=p.name?`<b data-no-translate>${esc(p.name)}</b>`:'<b>Một người hàng xóm</b>';
  const left=open?`Còn ${p.left}/${p.n} bao`:p.status==='expired'?'Đã hết giờ':'Đã giật hết';
  const btn=kind?`<button type="button" class="lxc-go ${kind}" ${act} data-id="${esc(p.id)}" data-do="${kind}">${esc(label)}</button>`:'';
  return `<div class="lxc${open?' on':''}" role="note"><span class="lxc-env" aria-hidden="true">🧧</span><div class="lxc-t"><div>${who} <span>phát lì xì ${fmt(p.total)} xu</span></div>`+
    `${p.wish?`<q data-no-translate>${esc(p.wish)}</q>`:''}<small>${left}</small></div>${btn}</div>`;
}

export function css(){
  if(!globalThis.document?.head||document.querySelector('style[data-lxc-css]'))return;
  const s=document.createElement('style');s.dataset.lxcCss='';
  s.textContent=`.lxc{display:flex;align-items:center;gap:10px;margin:8px auto;max-width:440px;width:calc(100% - 8px);box-sizing:border-box;padding:9px 10px;border-radius:14px;
  background:linear-gradient(135deg,#b3161b,#d8342a 60%,#e8572e);color:#fff;box-shadow:0 4px 14px rgba(120,10,10,.22),inset 0 0 0 1px rgba(255,214,102,.45)}
.lxc:not(.on){filter:saturate(.55);opacity:.85}
.lxc-env{font-size:30px;line-height:1;flex:none}
.lxc.on .lxc-env{animation:lxc-wob 1.8s ease-in-out infinite}
.lxc-t{flex:1;min-width:0;font-size:13.5px;line-height:1.35}
.lxc-t b{color:#ffe08a;overflow-wrap:anywhere}
.lxc-t q{display:block;font-style:italic;color:#fff1cf;overflow-wrap:anywhere}
.lxc-t small{display:block;opacity:.9;font-size:12px}
.lxc-go{flex:none;min-width:64px;min-height:36px;padding:6px 12px;border:0;border-radius:99px;font:800 14px/1.1 system-ui,sans-serif;cursor:pointer;background:#ffd25e;color:#7a1410}
.lxc-go.see{background:rgba(255,255,255,.18);color:#fff;font-weight:700}
.lxc-go:focus-visible{outline:2px solid #fff;outline-offset:2px}
@keyframes lxc-wob{0%,100%{transform:rotate(0)}50%{transform:rotate(-9deg) scale(1.08)}}
@media (prefers-reduced-motion:reduce){.lxc.on .lxc-env{animation:none}}
.reduce-motion .lxc.on .lxc-env{animation:none}
.ch-here .ch-lixi{margin-left:8px;background:#c8231e;color:#fff;border-color:transparent}`;
  document.head.append(s);
}

/** Cả phố with the cards between the messages, by time: [{lixi: packet} | message]. A packet older than the oldest
 * message loaded shows first while it is still open (an older finished one stays in the 🧧 list). */
export function interleave(msgs){
  css();const cards=list();if(!cards.length)return msgs;
  const first=msgs.find(m=>!m.sys&&Number(m.at));
  const out=[];let i=0;
  for(const m of msgs){
    const at=Number(m.at)||0;
    while(i<cards.length&&at&&cards[i].at<=at){const c=cards[i++];if(!first||c.at>=first.at||openNow(c))out.push({lixi:c});}
    out.push(m);
  }
  while(i<cards.length){const c=cards[i++];if(!first||c.at>=first.at||openNow(c))out.push({lixi:c});}
  return out;
}
