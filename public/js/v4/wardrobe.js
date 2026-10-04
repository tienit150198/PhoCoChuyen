/** 👗 Tủ đồ: try on hair, clothes, shoes and one accessory, then wear the look or buy what is missing.
 * Loaded the first time the wardrobe opens (journey.js: jrView 'wardrobe', actions jrWd*). Markup only:
 * names, prices and unlocks come from api.content.journey.wardrobe (game/wardrobe.py), the art from
 * look.js, and every change is a jr_wd_* command checked by the server. Trying on is local (ui.wd.draft).
 * Bảng màu (1.3.1 accessories, góp ý #70; now clothes and shoes too): on the Áo, Quần · váy, Giày dép and Phụ kiện
 * tabs a row of colours to try on what is worn there (ui.wd.tint, per item). Màu gốc is free; another colour is
 * unlocked once for every item (v4/palette.js, jr_wd_unlock), then switching is free. A recoloured item is named
 * without its colour word: "Áo hoodie · Xanh navy". */
import {icon,escapeHTML as esc} from '../icons.js';
import {confirmPurchase} from './payment.js';
import {lookOf,portrait,figureSVG,SLOTS,ART,PALETTE,TINT_SLOTS,wornColor as wornOf} from './look.js';
import {GOC,colorList,haveColors,hasColor,priceOf as colorPrice,nameOf as colorName,swatch,unlockColor,openPalette} from './palette.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const C=api=>api.content.journey?.wardrobe;
const S=ui=>{const st=ui.wd??={tab:'top',draft:{}};st.tint??={};return st;};
const TAB_EMOJI={hair:'💇',shade:'🎨',skin:'🌼',top:'👕',bottom:'👖',shoes:'👟',acc:'🎀'};
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;

const staff=api=>!!api.state.careers?.[C(api).shop]?.started;
const off=(api,p)=>p&&staff(api)?p-Math.floor(p*C(api).staff_off/100):p;
const priceOf=(api,it)=>off(api,it.price);
const owned=api=>api.state.wardrobe?.owned||[];
const itemOf=(api,id)=>C(api).items.find(x=>x.id===id);

/* ---- bảng màu ---- */
/** Can this item take a colour? Accessories as in 1.3.1 (not "Không đeo gì"), every top, bottom and pair of shoes. */
function paintable(api,id){
  const it=itemOf(api,id);if(!it||!TINT_SLOTS.includes(it.slot)||!(C(api).colors||[]).length)return false;
  return it.slot==='acc'?(C(api).tintable||[]).includes(id)&&!!ART.acc[id]?.c:(C(api).clothes||[]).includes(id)&&!!ART[it.slot]?.[id];
}
const wornColor=(api,id)=>wornOf(api.state,id)||GOC;
/** The colour an item is shown in while trying on: the one picked here, else the one it is worn in. */
const tryColor=(api,st,id)=>id in st.tint?st.tint[id]:wornColor(api,id);
/** The look with the colours being tried on (look.tint), for the mirror and the tiles. */
function withTint(api,st,look){
  const L={...look},t={};delete L.tint;
  for(const k of TINT_SLOTS){const id=L[k];if(!paintable(api,id))continue;const c=tryColor(api,st,id);if(c!==GOC&&PALETTE[c])t[id]=c;}
  if(Object.keys(t).length)L.tint=t;
  return L;
}
/** The slots whose colour differs from what is worn. */
const recolored=(api,st,look)=>TINT_SLOTS.filter(k=>paintable(api,look[k])&&tryColor(api,st,look[k])!==wornColor(api,look[k]));
/** "Áo hoodie tím", or once recoloured "Áo hoodie · Xanh navy" (one element per piece for the English pack). */
const shownName=(api,it,c)=>c&&c!==GOC?`<span>${esc(it.plain||it.name)}</span> · <span>${esc(colorName(api,c))}</span>`:esc(it.name);

/** What stands between the player and wearing this item: {lock} (an unlock not reached), {buy, price}, or null. */
function status(api,it){
  const J=api.state.journey,need=it.need||'';
  if(need.startsWith('level:')){const n=Number(need.slice(6));if((J.maturity?.level||1)<n)return {lock:`Mở ở Trưởng thành cấp ${n}`};}
  else if(need.startsWith('title:')){const tid=need.slice(6);if(!(J.titles||[]).some(t=>t[0]===tid)){const t=api.content.journey.titles.find(x=>x.id===tid);return {lock:`Mở khi có danh hiệu “${t?.name||'đặc biệt'}”`};}}
  else if(need==='married'&&api.state.marriage?.spouse?.status!=='married')return {lock:'Mở sau đám cưới'};
  if(it.price&&!owned(api).includes(it.id)){
    if(need==='shop'&&!staff(api))return {lock:`Chỉ bán cho người làm ở ${C(api).shop_name}`};
    return {buy:true,price:priceOf(api,it)};
  }
  return null;
}

function thumb(look,gender,slot){
  if(slot==='top'&&ART.top[look.top]?.dress)return figureSVG(look,gender,{w:64,h:80});
  if(slot==='bottom'&&ART.top[look.top]?.dress)look={...look,top:'ao_quen'};
  if(slot==='bottom'||slot==='shoes')return figureSVG(look,gender,{w:64,h:64,box:slot==='shoes'?'-30 -30 60 36':'-36 -58 72 64'});
  return portrait(look,gender,64,'');
}

function tile(api,st,it,look,saved,gender){
  const worn=saved[it.slot]===it.id,on=look[it.slot]===it.id,stt=status(api,it);
  const tag=worn?'<small class="wd-tag worn">Đang mặc</small>'
    :stt?.lock?`<small class="wd-tag lock">🔒 ${esc(stt.lock)}</small>`
    :stt?.buy?`<small class="wd-tag price">${stt.price<it.price?`<s>${fmt(it.price)}</s> `:''}${fmt(stt.price)} xu</small>`
    :`<small class="wd-tag">${it.price?'Đã có':it.need?'Đã mở':'Miễn phí'}</small>`;
  const L=withTint(api,st,{...look,[it.slot]:it.id}),col=paintable(api,it.id)?tryColor(api,st,it.id):GOC;
  return `<button type="button" class="wd-item${on?' on':''}${stt?.lock?' locked':''}" data-action="jrWdTry" data-item="${esc(it.id)}" aria-pressed="${on}">
    <span class="wd-thumb" aria-hidden="true">${thumb(L,gender,it.slot)}</span><b>${shownName(api,it,col)}</b>${tag}</button>`;
}

/** Màu gốc of an item, as a swatch: its own main colour and the darker part. */
function ownColors(it){
  const a=ART[it.slot]?.[it.id]||{};
  return it.slot==='acc'?{c:a.c,d:a.d}:{c:a.c||'#e8b9a4',d:a.x||a.line||'#a8957e'};
}

/** The colour row of the item being tried on in this slot: Màu gốc + the palette, the ones that suit the hair marked ✨. */
function colorPanel(api,st,look,slot){
  const id=look[slot],it=itemOf(api,id);
  if(!it||!paintable(api,id))return `<p class="jr-card wd-colors wd-col-empty">🎨 Chọn kính, nón, mũ, nơ hay túi để thử màu.</p>`;
  const cur=tryColor(api,st,id),worn=wornColor(api,id),base=ownColors(it),have=haveColors(api),all=colorList(api);
  const shade=itemOf(api,look.shade),match=(C(api).match||{})[look.shade]||[];
  const wearing=slot==='acc'?'đang đeo':'đang mặc';
  const sw=(c,fill,ring,label)=>{
    const mine=hasColor(api,c),good=match.includes(c);
    const aria=[label,c===worn?wearing:mine?(c===GOC?'miễn phí':'đã mở'):`${fmt(colorPrice(api,c))} xu`,good?'hợp với tóc':''].filter(Boolean).join(' · ');
    return `<button type="button" class="wd-sw${c===cur?' on':''}${mine?'':' locked'}${good?' good':''}" role="radio" aria-checked="${c===cur}" data-action="jrWdTint" data-color="${esc(c)}" aria-label="${esc(aria)}" title="${esc(label)}">
      ${swatch(fill,ring,36,c===GOC)}${mine?'':'<i class="wd-sw-lock" aria-hidden="true">🔒</i>'}${good?'<i class="wd-sw-good" aria-hidden="true">✨</i>':''}</button>`;
  };
  const sws=[sw(GOC,base.c,base.d,'Màu gốc'),...all.map(x=>sw(x.id,PALETTE[x.id].c,PALETTE[x.id].d,x.name))].join('');
  const tag=cur===worn?`<small class="wd-tag worn">${slot==='acc'?'Đang đeo':'Đang mặc'}</small>`:cur===GOC?'<small class="wd-tag">Miễn phí</small>'
    :hasColor(api,cur)?'<small class="wd-tag">Đã mở</small>':`<small class="wd-tag price">🔒 ${fmt(colorPrice(api,cur))} xu</small>`;
  // One text node per piece, so the English pack finds each one whole ("Hợp với tóc nâu mật ong", "Xanh navy").
  const hint=match.length&&shade?`<p class="wd-match">✨ <span>Hợp với tóc ${esc(shade.name.charAt(0).toLowerCase()+shade.name.slice(1))}</span>: ${match.map(c=>`<span>${esc(colorName(api,c))}</span>`).join(', ')}</p>`:'';
  return `<section class="jr-card wd-colors" aria-label="Màu">
    <div class="wd-col-head"><b><span>🎨 Thử màu</span> · <span>${esc(it.plain||it.name)}</span></b><span class="wd-col-now">${esc(colorName(api,cur))} ${tag}</span></div>${hint}
    <div class="wd-swatches" role="radiogroup" aria-label="Màu cho ${esc(it.plain||it.name)}">${sws}</div>
    <div class="wd-col-foot"><p class="wd-note">Màu gốc miễn phí. Mở một màu một lần là dùng được cho mọi món: quần áo, giày dép, phụ kiện và đồ trong nhà.</p>
    ${btn(`🎨 Bảng màu của bạn · ${have.length}/${all.length}`,'jrWdPalette',{},'ghost small wd-pal')}</div>
  </section>`;
}

function actions(api,st,look,saved){
  const changed=SLOTS.filter(k=>look[k]!==saved[k]),recolor=recolored(api,st,look);
  if(!changed.length&&!recolor.length)return `<p class="wd-hint">👇 Chạm một món để mặc thử.</p>`;
  const rows=changed.map(k=>{const it=itemOf(api,look[k]);return {it,st:status(api,it)};});
  const buys=rows.filter(r=>r.st?.buy).map(r=>btn(`Mua ${esc(r.it.name)} · ${fmt(r.st.price)} xu`,'jrWdBuy',{item:r.it.id},'primary full'));
  const locks=rows.filter(r=>r.st?.lock).map(r=>`<p class="wd-lock">🔒 ${esc(r.it.name)}: ${esc(r.st.lock.charAt(0).toLowerCase()+r.st.lock.slice(1))}.</p>`);
  const need=[...new Set(recolor.map(k=>tryColor(api,st,look[k])).filter(c=>!hasColor(api,c)))];
  const paint=need.map(c=>btn(`Mở khóa màu ${esc(colorName(api,c))} · ${fmt(colorPrice(api,c))} xu`,'jrWdColorBuy',{color:c},'primary full')).join('');
  const wear=rows.every(r=>!r.st)&&!need.length?btn('✨ Mặc bộ này','jrWdWear',{},'primary full'):'';
  return `${locks.join('')}${buys.join('')}${paint}${wear}${btn('Bỏ thử, mặc lại bộ cũ','jrWdReset',{},'ghost small full')}`;
}

/** Phones: the mirror stays in sight while tiles scroll (sticky under the sheet header, whose height varies). */
function stick(){
  const d=document.getElementById('sheet'),h=d?.querySelector('#sheetContent>.sheet-head'),st=d?.querySelector('.wd-stage');
  if(h&&st)st.style.setProperty('--wd-top',`${h.offsetHeight}px`);
}

/** The look being tried on: the saved one with the draft slots, everything in the colours being tried. */
function tryLook(api,st){
  const saved=lookOf(api.state),look={...saved,...st.draft};
  return {saved,look:withTint(api,st,look)};
}

export function wardrobeView(env){
  const {api,ui}=env,c=C(api),J=api.state.journey,st=S(ui),g=J.gender;
  const top=`<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại hành trình">${icon('back',18)}</button><div class="grow"><span class="eyebrow">NHÂN VẬT</span><h2>Tủ đồ</h2></div></header>`;
  if(!c)return top+`<div class="sheet-body jr-body"><p class="muted">Tủ đồ đang được sắp xếp, lát nữa quay lại nhé.</p></div>`;
  if(!SLOTS.includes(st.tab))st.tab='top';
  const {saved,look}=tryLook(api,st),recolor=recolored(api,st,look);
  const shop=staff(api)?`<p class="wd-note good">🏷️ Giá nhân viên ${esc(c.shop_name)}: −${c.staff_off}%</p>`
    :`<p class="wd-note">🏷️ Làm ở ${esc(c.shop_name)}: giảm ${c.staff_off}%</p>`;
  const dot=id=>look[id]!==saved[id]||recolor.includes(id);
  const tabs=c.slots.map(s=>`<button type="button" role="tab" class="wd-tab${st.tab===s.id?' active':''}" aria-selected="${st.tab===s.id}" data-action="jrWdTab" data-tab="${s.id}"><span aria-hidden="true">${TAB_EMOJI[s.id]||'•'}</span>${esc(s.name)}${dot(s.id)?'<i class="wd-dot" aria-label="đang thử"></i>':''}</button>`).join('');
  const grid=c.items.filter(x=>x.slot===st.tab).map(it=>tile(api,st,it,look,saved,g)).join('');
  const paint=TINT_SLOTS.includes(st.tab)&&c.colors?colorPanel(api,st,look,st.tab):'';
  globalThis.requestAnimationFrame?.(stick);
  return top+`<div class="sheet-body jr-body wd">
    <section class="jr-card wd-stage">
      <div class="wd-mirror">${figureSVG(look,g,{w:150,h:212,label:'Nhân vật của bạn trong bộ đồ đang thử'})}</div>
      <div class="wd-side"><h3>${esc(api.state.name)}</h3>${shop}<div class="wd-actions" aria-live="polite">${actions(api,st,look,saved)}</div></div>
    </section>
    <nav class="wd-tabs" role="tablist" aria-label="Loại đồ">${tabs}</nav>
    ${paint}<div class="wd-grid">${grid}</div>
    <section class="jr-card wd-work"><label class="switch-row"><span class="grow"><b>Mặc đồ làm việc khi vào ca</b><small class="muted block">Tạp dề, áo blouse, yếm… theo nơi làm.</small></span><input type="checkbox" role="switch" data-action="jrWdUniform" ${saved.uniform?'checked':''}><i aria-hidden="true"></i></label></section>
  </div>`;
}

/** Wear what is being tried on (slots and colours). true when it was sent and accepted (or nothing to send). */
async function wearDraft(api,st,cmd){
  const {saved,look:tried}=tryLook(api,st),look={};
  for(const [k,v] of Object.entries(st.draft))if(saved[k]!==v)look[k]=v;
  const tint={};for(const k of recolored(api,st,tried))tint[tried[k]]=tryColor(api,st,tried[k]);
  if(Object.keys(tint).length)look.tint=tint;
  if(Object.keys(look).length&&!await cmd('jr_wd_wear',{look}))return false;
  st.draft={};st.tint={};return true;
}

export async function wardrobeAction(action,data,el,env){
  const {api,ui,cmd,renderSheet,confirmAction}=env,st=S(ui),c=C(api);
  if(!c)return false;
  switch(action){
    case'jrWdTab':st.tab=SLOTS.includes(data.tab)?data.tab:'top';renderSheet();return true;
    case'jrWdTry':{const it=itemOf(api,data.item);if(!it)return true;
      if(lookOf(api.state)[it.slot]===it.id)delete st.draft[it.slot];else st.draft[it.slot]=it.id;renderSheet();return true;}
    case'jrWdTint':{const slot=TINT_SLOTS.includes(st.tab)?st.tab:'acc',id={...lookOf(api.state),...st.draft}[slot],col=data.color;
      if(!paintable(api,id)||(col!==GOC&&!colorList(api).some(x=>x.id===col)))return true;
      if(col===wornColor(api,id))delete st.tint[id];else st.tint[id]=col;renderSheet();return true;}
    case'jrWdReset':st.draft={};st.tint={};renderSheet();return true;
    case'jrWdWear':await wearDraft(api,st,cmd);renderSheet();return true;
    case'jrWdPalette':openPalette(env,{onChange:()=>renderSheet()});return true;
    case'jrWdBuy':{const it=itemOf(api,data.item);if(!it)return true;
      const price=priceOf(api,it);
      const how=await confirmPurchase(env,{title:`Mua ${it.name}?`,message:`Giá ${fmt(price)} xu${price<it.price?` (giá nhân viên ${c.shop_name}, giá gốc ${fmt(it.price)} xu)`:''}.`,label:`Mua · ${fmt(price)} xu`,cost:price});
      if(!how)return true;
      if(await cmd('jr_wd_buy',{item:it.id,wear:true,pay:how})){if(st.draft[it.slot]===it.id)delete st.draft[it.slot];}
      renderSheet();return true;}
    case'jrWdColorBuy':{const col=data.color;if(!colorList(api).some(x=>x.id===col))return true;
      if(await unlockColor(env,col)){
        // Unlocked for good: wear the outfit being tried on right away when nothing else stands in the way.
        const {saved,look}=tryLook(api,st);
        const free=SLOTS.every(k=>look[k]===saved[k]||!status(api,itemOf(api,look[k])))&&recolored(api,st,look).every(k=>hasColor(api,tryColor(api,st,look[k])));
        if(free)await wearDraft(api,st,cmd);
      }
      renderSheet();return true;}
    case'jrWdUniform':{const on=el?.type==='checkbox'?el.checked:!lookOf(api.state).uniform;
      await cmd('jr_wd_wear',{look:{uniform:on}});renderSheet();return true;}
  }
  return false;
}
