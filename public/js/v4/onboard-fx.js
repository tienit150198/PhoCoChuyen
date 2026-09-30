/** A brand-new player's first day, made to feel good (loaded only for a save in its first life day):
 *
 * - a heart burst over the first customer's tip (the tip card itself is v4/tips.js, paid by game/tips.py);
 * - a progress line, "⭐ Còn 2 khách nữa là lên cấp", on the work screen and the task card;
 * - the first level-up (the 3rd customer) with a little celebration naming what it opens
 *   (a topping, a recipe, a bake… whatever the workplace unlocks at that level);
 * - Bà Tám's welcome gift when the first day ends (game/journey.py WELCOME_GIFT).
 *
 * Render-only: every level, amount and unlock comes from the save and the catalogue. Nothing here is modal:
 * the cheer card takes no taps and leaves by itself. */
import {firstDay,servedAll} from './onboard.js';
import {asset} from '../assets.js';

let E=null,prev=null,booted=false;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reduced=()=>document.documentElement.classList.contains('reduce-motion')||matchMedia('(prefers-reduced-motion: reduce)').matches;
const S=()=>E?.api?.state;

/** The level a player sees at this workplace: the counter skill at the milk-tea bar, the workplace level elsewhere.
 * {level, left}: `left` customers until the next level (the engine gives 30 XP a job, a level every 90). */
export function levelOf(s,cid){
  const c=s?.careers?.[cid];if(!c)return null;
  const b=c.data?.boba;
  if(b&&Number.isFinite(b.level)){const left=b.next_tier!=null?Math.max(0,b.next_tier-(b.total||0)):null;return {level:b.level,left};}
  const lv=Number(c.level)||1,inLv=Number.isFinite(c.xp_in_level)?c.xp_in_level:(Number(c.xp)||0)%90;
  return {level:lv,left:Math.max(1,Math.ceil((90-inLv)/30))};
}

/** What a level opens at this workplace, as "🍃 Lục trà" names (at most 3). */
export function unlocksAt(api,cid,level){
  const out=[],add=(e,n)=>{if(n&&out.length<3&&!out.some(x=>x.n===n))out.push({e:e||'✨',n});};
  if(cid==='milk_tea'){
    for(const i of api.content?.experiences?.ingredients||[])if(Number(i.level||1)===level)add(i.emoji,i.name);
    for(const u of api.state?.careers?.[cid]?.data?.boba?.upgrades||[])if(Number(u.level)===level)add(u.emoji,u.name);
  }else{
    const seen=new Set(),walk=(o,d)=>{
      if(!o||typeof o!=='object'||d>3||seen.has(o))return;seen.add(o);
      if(Array.isArray(o)){o.forEach(x=>walk(x,d+1));return;}
      if(Number(o.unlock)===level&&typeof o.name==='string')add(o.emoji,o.name);
      for(const v of Object.values(o))walk(v,d+1);
    };
    walk(api.content?.careers?.[cid],0);
  }
  if(!out.length)for(const u of api.content?.upgrades||[])if(u.min_level===level&&(!u.careers||u.careers.includes(cid)))add('🛠️',u.name);
  return out;
}

/* ------------------------------------------------------------ cheer card */
function mount(){return document.querySelector('#confirmDialog[open]')||[...document.querySelectorAll('dialog[open]')].pop()||document.body;}
/** A small card over everything that takes no taps and leaves by itself; `burst` adds a few floating emoji. */
function cheer({emoji,title,line,burst='',ms=4800}){
  document.querySelectorAll('.onb-cheer').forEach(x=>x.remove());
  const el=document.createElement('div');el.className='onb-cheer';el.setAttribute('role','status');el.setAttribute('aria-live','polite');
  const bits=burst&&!reduced()?`<span class="onb-burst" aria-hidden="true">${[...Array(7)].map((_,i)=>`<i style="--i:${i}">${burst}</i>`).join('')}</span>`:'';
  el.innerHTML=`${bits}<span class="onb-cheer-emoji" aria-hidden="true">${esc(emoji)}</span><div><b>${esc(title)}</b>${line?`<small>${esc(line)}</small>`:''}</div>`;
  mount().append(el);
  setTimeout(()=>{el.classList.add('leaving');setTimeout(()=>el.remove(),reduced()?0:320);},ms);
}
/** Just the floating hearts (over the tip card of the first customer). */
function hearts(){
  if(reduced())return;
  const el=document.createElement('div');el.className='onb-hearts';el.setAttribute('aria-hidden','true');
  el.innerHTML=[...Array(9)].map((_,i)=>`<i style="--i:${i}">${i%3?'❤️':'💖'}</i>`).join('');
  mount().append(el);
  // Rising from the tip card's heart when it is up (v4/tips.js), else from the middle of the screen.
  const r=document.querySelector('.tip-pop:not(.leaving) .tip-pop-emoji')?.getBoundingClientRect();
  if(r&&r.width){el.style.left=Math.round(r.left+r.width/2)+'px';el.style.top=Math.round(r.top+r.height/2)+'px';el.style.bottom='auto';}
  setTimeout(()=>el.remove(),2600);
}

/* ------------------------------------------------------------ progress line */
function lineText(){
  const s=S(),cid=s?.current,c=s?.careers?.[cid];
  if(!firstDay(s)||!c?.open)return '';
  const lv=levelOf(s,cid);if(!lv||lv.level!==1||!lv.left)return '';
  return lv.left===1?'⭐ 1 khách nữa là lên cấp!':`⭐ Còn ${lv.left} khách nữa là lên cấp`;
}
function paintLine(){
  const text=lineText();
  const spots=[document.querySelector('#sheet[open].cozy-job .sheet-head > .grow'),document.querySelector('#taskHUD .task-card .calm-what')?.parentElement];
  for(const host of spots){
    if(!host)continue;
    let el=host.querySelector(':scope > .onb-lv');
    if(!text){el?.remove();continue;}
    if(!el){el=document.createElement('p');el.className='onb-lv';host.append(el);}
    if(el.textContent!==text)el.textContent=text;
  }
  if(!text)document.querySelectorAll('.onb-lv').forEach(x=>x.remove());
}

/* ------------------------------------------------------------ moments */
function snap(s){
  const cid=s?.current;
  return {cid,served:servedAll(s),lv:levelOf(s,cid)?.level||1,day:Number(s?.journey?.life_day)||1,wallet:s?.journey?.wallet};
}
function onState(){
  const s=S();if(!s)return;
  const now=snap(s),was=prev;prev=now;
  if(!was)return;
  // The very first customer: hearts over the tip card (it follows a moment later).
  if(was.served===0&&now.served===1&&firstDay(s))setTimeout(hearts,1000);
  // The first level-up at this workplace, on the first day.
  if(now.cid===was.cid&&now.lv>was.lv&&firstDay(s)){
    const got=unlocksAt(E.api,now.cid,now.lv);
    setTimeout(()=>cheer({emoji:'🎉',title:`Lên cấp ${now.lv}!`,line:got.length?'Mở: '+got.map(x=>`${x.e} ${x.n}`).join(' · '):'',burst:'✨',ms:5600}),1400);   // the chime is v4/sounds.js
  }
  // The first day is over: Bà Tám's welcome gift (already in the wallet, see the day summary).
  if(was.day===1&&now.day===2){
    const gift=(s.journey?.history||[]).slice(-6).find(h=>h.day===1&&/Quà chào hàng xóm mới/.test(h.label||''));
    if(gift)setTimeout(()=>cheer({emoji:'🎁',title:`Quà của Bà Tám: +${gift.amount} xu`,line:'Chào hàng xóm mới! Đã vào ví của bạn.',burst:'🌸'}),900);
  }
  requestAnimationFrame(paintLine);
}

export function onboardBoot(env){
  E=env;if(booted)return;booted=true;
  if(!document.querySelector('link[data-onboard-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/onboard.css');l.dataset.onboardCss='1';document.head.append(l);}
  prev=snap(env.api.state);
  env.api.addEventListener('state',()=>{try{onState();}catch(error){console.warn('onboard',error);}});
  document.addEventListener('sheetrender',()=>requestAnimationFrame(paintLine));
  const hud=document.getElementById('taskHUD');
  if(hud)new MutationObserver(()=>{if(!hud.querySelector('.onb-lv')&&lineText())requestAnimationFrame(paintLine);}).observe(hud,{childList:true,subtree:true});
  paintLine();
}
