/** 👗 Tủ đồ: try on hair, clothes, shoes and one accessory, then wear the look or buy what is missing.
 * Loaded the first time the wardrobe opens (journey.js: jrView 'wardrobe', actions jrWd*). Markup only:
 * names, prices and unlocks come from api.content.journey.wardrobe (game/wardrobe.py), the art from
 * look.js, and every change is a jr_wd_* command checked by the server. Trying on is local (ui.wd.draft).
 * Màu phụ kiện (1.3, góp ý #70): on the Phụ kiện tab a row of colours to try on the accessory (ui.wd.tint,
 * per accessory); Màu gốc is free, another colour is unlocked once (jr_wd_color buy), then switching is free. */
import {icon,escapeHTML as esc} from '../icons.js';
import {lookOf,portrait,figureSVG,SLOTS,ACC_COLORS,ART} from './look.js';

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

/* ---- màu phụ kiện ---- */
const GOC='goc';
const colors=api=>(C(api).colors||[]).filter(x=>ACC_COLORS[x.id]);
const colorOf=(api,id)=>colors(api).find(x=>x.id===id);
const tintable=(api,id)=>(C(api).tintable||[]).includes(id)&&!!ART.acc[id]?.c;
const wornColor=(api,id)=>{const c=api.state.wardrobe_colors?.wear?.[id];return ACC_COLORS[c]?c:GOC;};
const colorOwned=(api,id,c)=>c===GOC||(api.state.wardrobe_colors?.owned||[]).includes(`${id}:${c}`);
const colorName=(api,c)=>c===GOC?'Màu gốc':colorOf(api,c)?.name||c;
/** The colour the accessory is shown in while trying on: the one picked here, else the one it is worn in. */
const tryColor=(api,st,id)=>id in st.tint?st.tint[id]:wornColor(api,id);
const withTint=(look,id,c)=>{const L={...look};delete L.tint;if(c&&c!==GOC)L.tint={[id]:c};return L;};
const tintChanged=(api,st,look)=>tintable(api,look.acc)&&tryColor(api,st,look.acc)!==wornColor(api,look.acc);

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
  if(slot==='bottom'||slot==='shoes')return figureSVG(look,gender,{w:64,h:64,box:slot==='shoes'?'-30 -30 60 36':'-36 -58 72 64'});
  return portrait(look,gender,64,'');
}

function tile(api,st,it,look,saved,gender){
  const worn=saved[it.slot]===it.id,on=look[it.slot]===it.id,stt=status(api,it);
  const tag=worn?'<small class="wd-tag worn">Đang mặc</small>'
    :stt?.lock?`<small class="wd-tag lock">🔒 ${esc(stt.lock)}</small>`
    :stt?.buy?`<small class="wd-tag price">${stt.price<it.price?`<s>${fmt(it.price)}</s> `:''}${fmt(stt.price)} xu</small>`
    :`<small class="wd-tag">${it.price?'Đã có':it.need?'Đã mở':'Miễn phí'}</small>`;
  const L=it.slot==='acc'?withTint({...look,acc:it.id},it.id,tintable(api,it.id)?tryColor(api,st,it.id):GOC):{...look,[it.slot]:it.id};
  return `<button type="button" class="wd-item${on?' on':''}${stt?.lock?' locked':''}" data-action="jrWdTry" data-item="${esc(it.id)}" aria-pressed="${on}">
    <span class="wd-thumb" aria-hidden="true">${thumb(L,gender,it.slot)}</span><b>${esc(it.name)}</b>${tag}</button>`;
}

/** The colour row of the accessory being tried on: Màu gốc + the palette, the ones that suit the hair marked ✨. */
function colorPanel(api,st,look){
  const id=look.acc,it=itemOf(api,id);
  if(!it||!tintable(api,id))return `<p class="jr-card wd-colors wd-col-empty">🎨 Chọn kính, nón, mũ, nơ hay túi để thử màu.</p>`;
  const cur=tryColor(api,st,id),worn=wornColor(api,id),base=ART.acc[id];
  const shade=itemOf(api,look.shade),match=(C(api).match||{})[look.shade]||[];
  const sw=(c,fill,ring,label)=>{
    const have=colorOwned(api,id,c),price=c===GOC?0:off(api,colorOf(api,c)?.price||0),good=match.includes(c);
    const aria=[label,c===worn?'đang đeo':have?'đã mở':`${price} xu`,good?'hợp với tóc':''].filter(Boolean).join(' · ');
    return `<button type="button" class="wd-sw${c===cur?' on':''}${have?'':' locked'}${good?' good':''}" role="radio" aria-checked="${c===cur}" data-action="jrWdTint" data-color="${esc(c)}" aria-label="${esc(aria)}" title="${esc(label)}">
      <svg viewBox="0 0 36 36" width="36" height="36" aria-hidden="true" focusable="false"><circle cx="18" cy="18" r="15" fill="${fill}" stroke="${ring}" stroke-width="2"/>${c===GOC?`<path d="M18 3a15 15 0 0 1 0 30z" fill="${ring}" opacity=".45"/>`:''}</svg>${have?'':'<i class="wd-sw-lock" aria-hidden="true">🔒</i>'}${good?'<i class="wd-sw-good" aria-hidden="true">✨</i>':''}</button>`;
  };
  const sws=[sw(GOC,base.c,base.d,'Màu gốc'),...colors(api).map(x=>sw(x.id,ACC_COLORS[x.id].c,ACC_COLORS[x.id].d,x.name))].join('');
  const have=colorOwned(api,id,cur),price=cur===GOC?0:off(api,colorOf(api,cur)?.price||0);
  const state=cur===worn?'<small class="wd-tag worn">Đang đeo</small>':cur===GOC?'<small class="wd-tag">Miễn phí</small>'
    :have?'<small class="wd-tag">Đã mở</small>':`<small class="wd-tag price">🔒 ${fmt(price)} xu</small>`;
  // One text node per piece, so the English pack finds each one whole ("Hợp với tóc nâu mật ong", "Xanh navy").
  const hint=match.length&&shade?`<p class="wd-match">✨ <span>Hợp với tóc ${esc(shade.name.charAt(0).toLowerCase()+shade.name.slice(1))}</span>: ${match.map(c=>`<span>${esc(colorName(api,c))}</span>`).join(', ')}</p>`:'';
  return `<section class="jr-card wd-colors" aria-label="Màu phụ kiện">
    <div class="wd-col-head"><b><span>🎨 Thử màu</span> · <span>${esc(it.name)}</span></b><span class="wd-col-now">${esc(colorName(api,cur))} ${state}</span></div>${hint}
    <div class="wd-swatches" role="radiogroup" aria-label="Màu cho ${esc(it.name)}">${sws}</div>
    <p class="wd-note">Màu gốc miễn phí. Mỗi màu khác mở khóa một lần cho món này, sau đó đổi qua lại không mất xu.</p>
  </section>`;
}

function actions(api,st,look,saved){
  const changed=SLOTS.filter(k=>look[k]!==saved[k]),recolor=tintChanged(api,st,look);
  if(!changed.length&&!recolor)return `<p class="wd-hint">👇 Chạm một món để mặc thử.</p>`;
  const rows=changed.map(k=>{const it=itemOf(api,look[k]);return {it,st:status(api,it)};});
  const buys=rows.filter(r=>r.st?.buy).map(r=>btn(`Mua ${esc(r.it.name)} · ${fmt(r.st.price)} xu`,'jrWdBuy',{item:r.it.id},'primary full'));
  const locks=rows.filter(r=>r.st?.lock).map(r=>`<p class="wd-lock">🔒 ${esc(r.it.name)}: ${esc(r.st.lock.charAt(0).toLowerCase()+r.st.lock.slice(1))}.</p>`);
  let paint='',colorOk=true;
  if(recolor){
    const c=tryColor(api,st,look.acc),acc=itemOf(api,look.acc);
    if(!colorOwned(api,look.acc,c)){
      colorOk=false;
      paint=status(api,acc)?`<p class="wd-lock">🎨 Có ${esc(acc.name)} rồi mới mở khóa màu được nhé.</p>`
        :btn(`Mở khóa màu · ${fmt(off(api,colorOf(api,c)?.price||0))} xu`,'jrWdColorBuy',{item:look.acc,color:c},'primary full');
    }
  }
  const wear=rows.every(r=>!r.st)&&colorOk?btn('✨ Mặc bộ này','jrWdWear',{},'primary full'):'';
  return `${locks.join('')}${buys.join('')}${paint}${wear}${btn('Bỏ thử, mặc lại bộ cũ','jrWdReset',{},'ghost small full')}`;
}

/** Phones: the mirror stays in sight while tiles scroll (sticky under the sheet header, whose height varies). */
function stick(){
  const d=document.getElementById('sheet'),h=d?.querySelector('#sheetContent>.sheet-head'),st=d?.querySelector('.wd-stage');
  if(h&&st)st.style.setProperty('--wd-top',`${h.offsetHeight}px`);
}

/** The look being tried on: the saved one with the draft slots, and the accessory in the colour being tried. */
function tryLook(api,st){
  const saved=lookOf(api.state),look={...saved,...st.draft};
  return {saved,look:withTint(look,look.acc,tintable(api,look.acc)?tryColor(api,st,look.acc):GOC)};
}

export function wardrobeView(env){
  const {api,ui}=env,c=C(api),J=api.state.journey,st=S(ui),g=J.gender;
  const top=`<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại hành trình">${icon('back',18)}</button><div class="grow"><span class="eyebrow">NHÂN VẬT</span><h2>Tủ đồ</h2></div></header>`;
  if(!c)return top+`<div class="sheet-body jr-body"><p class="muted">Tủ đồ đang được sắp xếp, lát nữa quay lại nhé.</p></div>`;
  if(!SLOTS.includes(st.tab))st.tab='top';
  const {saved,look}=tryLook(api,st);
  const shop=staff(api)?`<p class="wd-note good">🏷️ Giá nhân viên ${esc(c.shop_name)}: −${c.staff_off}%</p>`
    :`<p class="wd-note">🏷️ Làm ở ${esc(c.shop_name)}: giảm ${c.staff_off}%</p>`;
  const dot=id=>look[id]!==saved[id]||(id==='acc'&&tintChanged(api,st,look));
  const tabs=c.slots.map(s=>`<button type="button" role="tab" class="wd-tab${st.tab===s.id?' active':''}" aria-selected="${st.tab===s.id}" data-action="jrWdTab" data-tab="${s.id}"><span aria-hidden="true">${TAB_EMOJI[s.id]||'•'}</span>${esc(s.name)}${dot(s.id)?'<i class="wd-dot" aria-label="đang thử"></i>':''}</button>`).join('');
  const grid=c.items.filter(x=>x.slot===st.tab).map(it=>tile(api,st,it,look,saved,g)).join('');
  const paint=st.tab==='acc'&&c.colors?colorPanel(api,st,look):'';
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

/** Wallet first; not enough and no card: a friendly toast instead of the confirm. Returns false to stop. */
function canAfford(api,env,price,what){
  const w=api.state.journey.wallet,card=api.state.journey.bank?.card;
  if(w<price&&!card){env.toast?.(`Ví mới có ${fmt(Math.max(0,w))} xu, chưa đủ ${fmt(price)} xu để mua ${what}. Làm thêm vài ca rồi quay lại nhé.`,true);return false;}
  return true;
}
const payNote=(api,price)=>{const w=api.state.journey.wallet;return w>=price?`Ví của bạn đang có ${fmt(w)} xu.`:`Ví chưa đủ nên sẽ quẹt thẻ Ngân hàng Phố.`;};

export async function wardrobeAction(action,data,el,env){
  const {api,ui,cmd,renderSheet,confirmAction}=env,st=S(ui),c=C(api);
  if(!c)return false;
  switch(action){
    case'jrWdTab':st.tab=SLOTS.includes(data.tab)?data.tab:'top';renderSheet();return true;
    case'jrWdTry':{const it=itemOf(api,data.item);if(!it)return true;
      if(lookOf(api.state)[it.slot]===it.id)delete st.draft[it.slot];else st.draft[it.slot]=it.id;renderSheet();return true;}
    case'jrWdTint':{const acc={...lookOf(api.state),...st.draft}.acc,col=data.color;
      if(!tintable(api,acc)||(col!==GOC&&!colorOf(api,col)))return true;
      if(col===wornColor(api,acc))delete st.tint[acc];else st.tint[acc]=col;renderSheet();return true;}
    case'jrWdReset':st.draft={};st.tint={};renderSheet();return true;
    case'jrWdWear':{const {saved,look:tried}=tryLook(api,st),look={};
      for(const [k,v] of Object.entries(st.draft))if(saved[k]!==v)look[k]=v;
      if(tintChanged(api,st,tried))look.tint={[tried.acc]:tryColor(api,st,tried.acc)};
      if(Object.keys(look).length&&!await cmd('jr_wd_wear',{look}))return true;
      st.draft={};st.tint={};renderSheet();return true;}
    case'jrWdBuy':{const it=itemOf(api,data.item);if(!it)return true;
      const price=priceOf(api,it);
      if(!canAfford(api,env,price,it.name))return true;
      if(!await confirmAction(`Mua ${it.name}?`,`Giá ${fmt(price)} xu${price<it.price?` (giá nhân viên ${c.shop_name}, giá gốc ${fmt(it.price)} xu)`:''}. ${payNote(api,price)}`,`Mua · ${fmt(price)} xu`))return true;
      if(await cmd('jr_wd_buy',{item:it.id,wear:true})){if(st.draft[it.slot]===it.id)delete st.draft[it.slot];}
      renderSheet();return true;}
    case'jrWdColorBuy':{const it=itemOf(api,data.item),col=colorOf(api,data.color);if(!it||!col||!tintable(api,it.id))return true;
      const price=off(api,col.price),what=`màu ${col.name} cho ${it.name}`;
      if(!canAfford(api,env,price,what))return true;
      if(!await confirmAction(`Mở khóa màu ${col.name} cho ${it.name}?`,`Giá ${fmt(price)} xu${price<col.price?` (giá nhân viên ${c.shop_name}, giá gốc ${fmt(col.price)} xu)`:''}. Mở một lần, sau đó đổi qua lại miễn phí. ${payNote(api,price)}`,`Mở khóa · ${fmt(price)} xu`))return true;
      if(await cmd('jr_wd_color',{item:it.id,color:col.id,buy:true,wear:true})){delete st.tint[it.id];if(st.draft.acc===it.id)delete st.draft.acc;}
      renderSheet();return true;}
    case'jrWdUniform':{const on=el?.type==='checkbox'?el.checked:!lookOf(api.state).uniform;
      await cmd('jr_wd_wear',{look:{uniform:on}});renderSheet();return true;}
  }
  return false;
}
