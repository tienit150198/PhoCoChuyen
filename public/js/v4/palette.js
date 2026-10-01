/** 🎨 Bảng màu của bạn: the colour wallet (game/wardrobe.py, "Bảng màu"). A colour is unlocked once (jr_wd_unlock)
 * and is then free on every item: clothes, shoes and accessories (v4/wardrobe.js) and furniture in any home, a rented
 * room or the dorm (v4/reno.js, jr_wd_deco). Màu gốc, each item's own colour, is always free.
 *   openPalette(env,{onChange})   the sheet: every colour, which ones are yours, unlock the others
 *   pickColor(env,{title,current,preview,onTry,apply,onClose})   a small picker (the decor toolbar's 🎨 Màu)
 *   haveColors, hasColor, priceOf, nameOf, unlockColor, swatch   shared with the wardrobe
 * Loaded on first use, with /css/palette.css. Markup only: the server checks every command. */
import {icon,escapeHTML as esc} from '../icons.js';
import {PALETTE} from './look.js';

export const GOC='goc';
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const W=api=>api?.content?.journey?.wardrobe||{};
/** The palette in its order (game/wardrobe.py COLORS), only colours this page can draw. */
export const colorList=api=>(W(api).colors||[]).filter(x=>PALETTE[x.id]);
/** The colours that are yours: the wallet's (state.colors.have) and any 1.3.1 sold for one accessory. */
export function haveColors(api){
  const st=api?.state||{},got=new Set(Array.isArray(st.colors?.have)?st.colors.have:[]);
  for(const p of Array.isArray(st.wardrobe_colors?.owned)?st.wardrobe_colors.owned:[])if(typeof p==='string')got.add(p.slice(p.indexOf(':')+1));
  return colorList(api).map(c=>c.id).filter(id=>got.has(id));
}
export const hasColor=(api,c)=>c===GOC||haveColors(api).includes(c);
const staff=api=>!!api?.state?.careers?.[W(api).shop]?.started;
const fullPrice=(api,c)=>colorList(api).find(x=>x.id===c)?.price||0;
export function priceOf(api,c){const p=fullPrice(api,c);return p&&staff(api)?p-Math.floor(p*(W(api).staff_off||0)/100):p;}
export const nameOf=(api,c)=>c===GOC?'Màu gốc':colorList(api).find(x=>x.id===c)?.name||c;

/** A round swatch (36 px by default): the colour, or Màu gốc as the item's own colour split with its darker part. */
export function swatch(fill,ring,size=36,goc=false){
  return `<svg viewBox="0 0 36 36" width="${size}" height="${size}" aria-hidden="true" focusable="false"><circle cx="18" cy="18" r="15" fill="${fill}" stroke="${ring}" stroke-width="2"/>${goc?`<path d="M18 3a15 15 0 0 1 0 30z" fill="${ring}" opacity=".45"/>`:''}</svg>`;
}
const GOC_ART={c:'#f6ecdf',d:'#b9a58c'};   // the picker's "Màu gốc" chip when the item has no single colour

/* ---- styles on first use (like reno.js) ---- */
let cssReady=null;
function ensureCss(){
  return cssReady??=new Promise(done=>{
    if(document.querySelector('link[data-pl-css]')){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.('/css/palette.css')||'/css/palette.css';l.setAttribute('data-pl-css','');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}

/* ---- unlocking: one confirm, one command; the server pays (wallet, then the card) and never goes below zero ---- */
let busy=false;
function say(env,text,bad=false){
  const open=[...document.querySelectorAll('dialog.pl-dlg[open] .pl-say')].pop();
  if(open){open.textContent=text||'';open.className=`pl-say${bad?' bad':text?' good':''}`;return;}
  if(text)env.toast?.(text,bad);
}
/** Unlock colour `c` for good (asks first). true when it is yours afterwards. */
export async function unlockColor(env,c){
  const api=env.api;
  if(hasColor(api,c))return true;
  if(busy)return false;
  const price=priceOf(api,c),full=fullPrice(api,c),name=nameOf(api,c),w=api.state.journey?.wallet??0,card=api.state.journey?.bank?.card;
  if(!price)return false;
  if(w<price&&!card){say(env,`Ví mới có ${fmt(Math.max(0,w))} xu, chưa đủ ${fmt(price)} xu để mở khóa màu ${name}. Làm thêm vài ca rồi quay lại nhé.`,true);return false;}
  const off=price<full?` (giá nhân viên ${W(api).shop_name}, giá gốc ${fmt(full)} xu)`:'';
  const pay=w>=price?`Ví của bạn đang có ${fmt(w)} xu.`:'Ví chưa đủ nên sẽ quẹt thẻ Ngân hàng Phố.';
  if(!await env.confirmAction(`Mở khóa màu ${name}?`,`Giá ${fmt(price)} xu${off}. Mở một lần, dùng được cho mọi món: quần áo, giày dép, phụ kiện và đồ trong nhà. ${pay}`,`Mở khóa · ${fmt(price)} xu`))return false;
  busy=true;
  try{const r=await api.command('jr_wd_unlock',{color:c});say(env,r?.message||'');return hasColor(api,c)||!!r;}
  catch(e){if(!e.quiet)say(env,e.message||'Chưa mở khóa được. Thử lại nhé.',true);return false;}
  finally{busy=false;}
}

/* ---- dialogs ---- */
function dialog(cls,label){
  const d=document.createElement('dialog');
  d.className=`sheet v4-sheet narrow pl-dlg ${cls}`;d.setAttribute('aria-labelledby',label);
  document.body.append(d);
  return d;
}
const closeBtn=`<button class="icon-btn" type="button" data-pl="close" aria-label="Đóng">${icon('x',21)}</button>`;

/** The sheet: every colour of the palette, which ones are yours, and the price of the others. */
export async function openPalette(env,{onChange}={}){
  await ensureCss();
  const api=env.api,d=dialog('pl-sheet','pl-title');
  const draw=()=>{
    const have=haveColors(api),list=colorList(api);
    const tiles=list.map(x=>{const t=PALETTE[x.id],own=have.includes(x.id),p=priceOf(api,x.id);
      return `<li><button type="button" class="pl-tile${own?' have':''}" data-pl="${own?'':'unlock'}" data-c="${esc(x.id)}" ${own?'aria-disabled="true"':''} aria-label="${esc(`${x.name} · ${own?'đã mở':`${fmt(p)} xu`}`)}">
        <span class="pl-dot">${swatch(t.c,t.d,46)}${own?'<i class="pl-ok" aria-hidden="true">✓</i>':'<i class="pl-lock" aria-hidden="true">🔒</i>'}</span>
        <b>${esc(x.name)}</b><small class="pl-chip${own?' ok':''}">${own?'Đã mở':`${fmt(p)} xu`}</small></button></li>`;}).join('');
    const sale=staff(api)?`<p class="pl-note good">🏷️ Giá nhân viên ${esc(W(api).shop_name)}: −${W(api).staff_off}%</p>`:`<p class="pl-note">🏷️ Làm ở ${esc(W(api).shop_name)}: giảm ${W(api).staff_off}%</p>`;
    d.innerHTML=`<header class="sheet-head pl-head"><div class="grow"><span class="eyebrow">BẢNG MÀU</span><h2 id="pl-title">🎨 Bảng màu của bạn</h2>
        <p>Mở một màu một lần là dùng được ở mọi nơi: áo, quần, giày dép, phụ kiện và đồ đạc trong nhà, cả phòng trọ lẫn ký túc xá.</p></div>${closeBtn}</header>
      <div class="sheet-body pl-body">
        <div class="pl-count"><span class="pl-count-num"><b>${have.length}</b>/${list.length}</span><span>màu đã mở</span><i class="pl-bar" aria-hidden="true"><b style="width:${list.length?Math.round(have.length/list.length*100):0}%"></b></i></div>
        <ul class="pl-grid" aria-label="Các màu">${tiles}</ul>
        <p class="pl-note">✨ Màu gốc của mỗi món luôn miễn phí. Đổi qua lại giữa các màu đã mở không mất xu.</p>${sale}
        <p class="pl-say" role="status" aria-live="polite"></p>
      </div>`;
  };
  const onState=()=>{if(d.open&&!busy)draw();};
  api.addEventListener?.('state',onState);
  d.addEventListener('click',async e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-pl]');if(!el||!d.contains(el))return;
    const op=el.dataset.pl;
    if(op==='close'){d.close();return;}
    if(op==='unlock'&&await unlockColor(env,el.dataset.c)){const msg=d.querySelector('.pl-say')?.textContent||'';draw();say(env,msg);onChange?.();}
  });
  d.addEventListener('close',()=>{api.removeEventListener?.('state',onState);d.remove();onChange?.();});
  draw();d.showModal();
  return d;
}

/** The picker for one item: try a colour (onTry previews it), then wear it: apply(c) → true when done.
 * o: {title, current, preview(c) → svg, onTry(c), apply(c), onClose()} */
export async function pickColor(env,o){
  await ensureCss();
  const api=env.api,d=dialog('pl-pick','pl-pick-title');
  let cur=o.current||GOC,done=false;
  const choose=c=>{cur=c;o.onTry?.(c);draw();};
  const draw=()=>{
    const have=haveColors(api),list=colorList(api),own=hasColor(api,cur),price=priceOf(api,cur);
    const sw=(c,t,label,goc=false)=>{const mine=c===GOC||have.includes(c);
      return `<button type="button" class="pl-sw${c===cur?' on':''}${mine?'':' locked'}" role="radio" aria-checked="${c===cur}" data-pl="try" data-c="${esc(c)}" aria-label="${esc(`${label} · ${c===o.current?'đang dùng':mine?(c===GOC?'miễn phí':'đã mở'):`${fmt(priceOf(api,c))} xu`}`)}" title="${esc(label)}">${swatch(t.c,t.d,36,goc)}${mine?'':'<i class="pl-sw-lock" aria-hidden="true">🔒</i>'}</button>`;};
    const sws=[sw(GOC,GOC_ART,'Màu gốc',true),...list.map(x=>sw(x.id,PALETTE[x.id],x.name))].join('');
    const now=cur===o.current?'<small class="pl-chip ok">Đang dùng</small>':cur===GOC?'<small class="pl-chip ok">Miễn phí</small>'
      :own?'<small class="pl-chip ok">Đã mở</small>':`<small class="pl-chip">🔒 ${fmt(price)} xu</small>`;
    const go=cur===o.current?`<button type="button" class="btn primary" data-pl="close">Xong</button>`
      :own?`<button type="button" class="btn primary" data-pl="apply">✨ Dùng màu này</button>`
      :`<button type="button" class="btn primary" data-pl="buy">Mở khóa · ${fmt(price)} xu</button>`;
    d.innerHTML=`<div class="pl-pick-in"><header class="pl-pick-head"><span class="pl-prev" aria-hidden="true">${o.preview?.(cur)||''}</span>
        <div class="grow"><span class="eyebrow">🎨 CHỌN MÀU</span><h2 id="pl-pick-title">${esc(o.title||'')}</h2><p class="pl-now"><span>${esc(nameOf(api,cur))}</span> ${now}</p></div>${closeBtn}</header>
      <div class="pl-sws" role="radiogroup" aria-label="Màu cho ${esc(o.title||'')}">${sws}</div>
      <p class="pl-note">Màu gốc miễn phí. Mở một màu một lần là dùng được cho mọi món đồ.</p>
      <p class="pl-say" role="status" aria-live="polite"></p>
      <div class="pl-go">${go}<button type="button" class="btn ghost" data-pl="wallet">🎨 Bảng màu · ${have.length}/${list.length}</button></div></div>`;
  };
  const finish=async c=>{if(await o.apply?.(c)){done=true;d.close();}else draw();};
  d.addEventListener('click',async e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-pl]');if(!el||!d.contains(el)||busy)return;
    switch(el.dataset.pl){
      case'close':d.close();return;
      case'try':choose(el.dataset.c);return;
      case'apply':busy=true;try{await finish(cur);}finally{busy=false;}return;
      case'buy':if(await unlockColor(env,cur)){busy=true;try{await finish(cur);}finally{busy=false;}}else draw();return;
      case'wallet':openPalette(env,{onChange:()=>{if(d.open)draw();}});return;
    }
  });
  d.addEventListener('keydown',e=>{   // arrows walk the colours, as in a radio group
    const k={ArrowRight:1,ArrowDown:1,ArrowLeft:-1,ArrowUp:-1}[e.key];if(!k||!e.target.closest?.('.pl-sw'))return;
    e.preventDefault();const ids=[GOC,...colorList(api).map(x=>x.id)],i=(ids.indexOf(cur)+k+ids.length)%ids.length;
    choose(ids[i]);d.querySelector('.pl-sw.on')?.focus();
  });
  d.addEventListener('close',()=>{if(!done)o.onTry?.(o.current||GOC);d.remove();o.onClose?.();});
  draw();d.showModal();
  d.querySelector('.pl-sw.on')?.focus({preventScroll:true});
  return d;
}
