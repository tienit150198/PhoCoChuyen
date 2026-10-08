/** 👶 Bé nhà mình on the client (feedback #252: "cho em bé xuất hiện trong nhà… có thể bế đi chơi").
 * Every rule lives on the server (game/cradle.py, game/household.py, game/family.py); this file only knows:
 *   babies(state)        every baby of this player, as the room and the arms draw it: the couple's shared child (GET
 *                        /api/family/baby, loadFamily: cached a minute, only for a married save or one that had a custody
 *                        copy), the personal child of journey.household, the custody copies. Not one still awaited.
 *   carried(state)       the baby in the character's arms now, or null. "Bế bé đi chơi" is this browser's choice
 *                        (localStorage mnl.carry, like the ride toggle of ./ride.js: no save key, nothing to pay);
 *                        carrying means walking (ride.js choice() is null while a baby is carried).
 *   withBaby(F,state)    a figure of ./look.js with the baby in its arms (F.bb), when one is carried
 *   wire(state)          what the live presence carries (`bb` {n, g, o, sh?}, live/babies.py)
 *   taken(f)             the room said the spouse already carries the shared child (`bb_taken`): not drawn this visit
 *   moment(env,b,act)    a free moment with a baby (jr_cradle_do / POST /api/marriage/family_child_moment)
 *   greet(env)           the announcement card, once per baby on this device, at a quiet moment (./break-gate.js)
 * Styles: /css/baby.css. */
import {escapeHTML as esc} from '../icons.js';
import {babyPortrait} from './baby-art.js';
import {stylesheet} from '../lazy.js';
import {why,whenQuiet} from './break-gate.js';

const KEY='mnl.carry',HELLO='mnl.babyHello',COPIES='mnl.babyCopies';
const GROW={so_sinh:'Sơ sinh',biet_bo:'Biết bò',chap_chung:'Chập chững'};
const MEM={};   // storage blocked: this visit only
const ls={
  get(k){try{const v=localStorage.getItem(k);return v===null?(MEM[k]||''):v;}catch{return MEM[k]||'';}},
  set(k,v){MEM[k]=v||'';try{if(v)localStorage.setItem(k,v);else localStorage.removeItem(k);}catch{/* this visit only */}},
};
let FAM=null,FAM_AT=0,FAM_GO=null,TAKEN='';
export const css=()=>stylesheet('/css/baby.css');
export const growName=g=>GROW[g]||GROW.so_sinh;
const subs=new Set();
/** fn() after the shared child was (re)loaded or the carry changed. Returns the unsubscribe. */
export function onChange(fn){subs.add(fn);return ()=>subs.delete(fn);}
const tell=()=>{for(const fn of subs)try{fn();}catch(e){console.warn('baby:',e);}};

/** The shared child and the custody copies (GET /api/family/baby), cached a minute; null when there is none to ask for
 * (not married, never had a copy here), an older server or a network error. Never throws. */
export function loadFamily(api,force=false){
  if(!api?.json)return Promise.resolve(FAM);
  const married=api.state?.marriage?.spouse?.status==='married';
  if(!married&&!ls.get(COPIES)){const had=!!FAM;FAM=null;if(had)tell();return Promise.resolve(null);}
  if(FAM_GO)return FAM_GO;
  if(!force&&FAM_AT&&Date.now()-FAM_AT<60000)return Promise.resolve(FAM);
  FAM_GO=api.json('/api/family/baby').then(d=>{
    FAM=d&&typeof d==='object'&&Array.isArray(d.copies)?d:null;FAM_AT=Date.now();
    ls.set(COPIES,FAM?.copies?.length?'1':'');tell();return FAM;
  }).catch(()=>FAM).finally(()=>{FAM_GO=null;});
  return FAM_GO;
}
export const family=()=>FAM;
const shared=(c,id)=>({id,name:String(c.name||'Bé'),grow:GROW[c.grow]?c.grow:'so_sinh',outfit:c.outfit||'basic',bond:Number(c.bond)||0,
  age:Number(c.age)||0,hello:`${id}:${c.born||''}`,acts:c.acts||[],personal:!!c.personal});
/** Every baby at home: [{id ('shared' | 'child' | 'copy:N'), name, grow, outfit, bond, age, hello}]. */
export function babies(state){
  const out=[],f=FAM,J=state?.journey;
  if(f?.child&&!f.child.waiting)out.push(shared(f.child,'shared'));
  const m=J?.story?(J.household?.members||[]).find(x=>x.id==='child'):null;
  if(m)out.push({id:'child',name:String(m.name||'Bé'),grow:GROW[m.grow]?m.grow:'so_sinh',outfit:m.outfit||'basic',bond:Number(m.bond)||0,
    age:Number(m.age)||0,hello:`child:${(Number(J.life_day)||0)-(Number(m.age)||0)}:${m.name}`,acts:m.acts||[],personal:true});
  for(const c of f?.copies||[])if(!c.waiting)out.push(shared(c,c.id));
  return out;
}
export const hasBaby=state=>babies(state).length>0;
/** The baby carried now (null: none, or the spouse has the shared one this visit). */
export function carried(state){
  const id=ls.get(KEY);if(!id||id===TAKEN)return null;
  return babies(state).find(b=>b.id===id)||null;
}
export const carrying=state=>!!carried(state);
export function setCarry(id){ls.set(KEY,id||'');TAKEN='';tell();}
/** The 👶 toggle: the next baby in turn, then none. Returns the baby carried now (or null). */
export function nextCarry(state){
  const list=babies(state),now=carried(state),i=now?list.findIndex(b=>b.id===now.id):-1,b=i<0?list[0]:list[i+1]||null;
  setCarry(b?.id||'');return b||null;
}
export const label=b=>b?`👶 Đang bế ${b.name}`:'👶 Bế bé đi chơi';
export function withBaby(F,state){const b=carried(state);if(F&&b)F.bb={g:b.grow,o:b.outfit};return F;}
export function wire(state){const b=carried(state);return b?{n:b.name.slice(0,16),g:b.grow,o:b.outfit,...(b.id==='shared'?{sh:1}:{})}:null;}
/** `bb_taken {by, name}` in a room reply: the husband / wife already carries the shared child. Returns the line to show. */
export function taken(f){
  if(!f||typeof f!=='object')return '';
  TAKEN=ls.get(KEY);tell();
  return `${String(f.name||'Người ấy')} đang bế bé rồi, bạn đi cùng nhé.`;
}

/** A free moment (🍼 / 🎶 / 🧸) with baby `b`. Returns the server's line, or throws its error (message). */
export async function moment(env,b,act){
  if(b.id==='child'){const r=await env.cmd('jr_cradle_do',{baby:'child',act});return r?.message||'';}
  const {api}=env,rid=(globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`).replace(/[^A-Za-z0-9_-]/g,'').slice(0,40);
  const d=await api.json('/api/marriage/family_child_moment',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify({child:b.id,act,rid})});
  if(d?.state&&typeof d.revision==='number')api.accept({state:d.state,revision:d.revision});
  await loadFamily(api,true);
  return d?.message||'';
}

/* ---- 🎉 the announcement card ---- */
let dlg=null,shownAt=0;
const seen=()=>{try{const a=JSON.parse(ls.get(HELLO)||'[]');return Array.isArray(a)?a.filter(x=>typeof x==='string'):[];}catch{return [];}};
function remember(key){ls.set(HELLO,JSON.stringify([...seen().filter(k=>k!==key),key].slice(-12)));}
function card(env,b,here=false){
  if(!dlg){
    dlg=document.createElement('dialog');dlg.className='bb-hello';dlg.setAttribute('aria-labelledby','bb-hello-t');
    dlg.addEventListener('cancel',e=>{e.preventDefault();dlg.close();});
    dlg.addEventListener('click',async e=>{
      const el=e.target.closest?.('[data-bb]');if(!el||performance.now()-shownAt<350)return;
      dlg.close();
      if(el.dataset.bb==='home'){try{(await import('./reno.js')).openReno(env);}catch(err){console.warn('baby: home',err);}}
    });
    document.body.append(dlg);
  }
  const fresh=b.age<=2;
  dlg.innerHTML=`<div class="bb-hello-card"><div class="bb-hello-art">${babyPortrait({g:b.grow,o:b.outfit},{size:168,asleep:b.grow==='so_sinh',label:b.name})}</div>
    <h2 id="bb-hello-t">${fresh?`🎉 Chào bé ${esc(b.name)}!`:`👶 ${esc(b.name)} đang ở nhà`}</h2>
    <p>${fresh?'Nhà mình có thêm một thành viên nhỏ.':'Bé đã có góc riêng trong nhà rồi.'} Ghé nhà để ru bé ngủ, chơi cùng bé, hoặc bế bé đi dạo phố nhé.</p>
    <p class="bb-hello-small">Mọi việc chơi với bé đều miễn phí.</p>
    <div class="bb-hello-row">${here?'':'<button type="button" class="btn ghost" data-bb="close">Để sau</button>'}${here?'<button type="button" class="btn primary" data-bb="close">💗 Chơi với bé</button>':'<button type="button" class="btn primary" data-bb="home">🏡 Vào nhà thăm bé</button>'}</div></div>`;
  shownAt=performance.now();
  dlg.showModal();
}
/** Show the card for a baby this device has not greeted yet (one at a time, at a quiet moment; `here`: in the home
 * room itself, at once unless another popup is up (then on a later visit), its button just closes the card). */
export function greet(env,{here=false}={}){
  if(typeof document==='undefined'||dlg?.open)return;
  const state=env?.api?.state,done=new Set(seen()),b=babies(state).find(x=>!done.has(x.hello));
  if(!b)return;
  const show=()=>{
    const now=babies(env.api.state).find(x=>x.hello===b.hello);if(!now||dlg?.open||new Set(seen()).has(b.hello))return;
    remember(b.hello);css().then(()=>card(env,now,here));
  };
  if(here){if(!why(document.querySelector('dialog.dc-sheet[open]')))show();}
  else if(why(null))whenQuiet(show);else show();
}

/* ---- test hooks (scratch browser checks) ---- */
globalThis.__baby={babies:s=>babies(s),carried:s=>carried(s)?.id||null,set:id=>setCarry(id),family:()=>FAM,seen};
