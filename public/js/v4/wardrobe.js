/** 👗 Tủ đồ: try on hair, clothes, shoes and one accessory, then wear the look or buy what is missing.
 * Loaded the first time the wardrobe opens (journey.js: jrView 'wardrobe', actions jrWd*). Markup only:
 * names, prices and unlocks come from api.content.journey.wardrobe (game/wardrobe.py), the art from
 * look.js, and every change is a jr_wd_* command checked by the server. Trying on is local (ui.wd.draft). */
import {icon,escapeHTML as esc} from '../icons.js';
import {lookOf,portrait,figureSVG,SLOTS} from './look.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const C=api=>api.content.journey?.wardrobe;
const S=ui=>ui.wd??={tab:'top',draft:{}};
const TAB_EMOJI={hair:'💇',shade:'🎨',skin:'🌼',top:'👕',bottom:'👖',shoes:'👟',acc:'🎀'};
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;

const staff=api=>!!api.state.careers?.[C(api).shop]?.started;
const priceOf=(api,it)=>it.price&&staff(api)?it.price-Math.floor(it.price*C(api).staff_off/100):it.price;
const owned=api=>api.state.wardrobe?.owned||[];
const itemOf=(api,id)=>C(api).items.find(x=>x.id===id);

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

function tile(api,it,look,saved,gender){
  const worn=saved[it.slot]===it.id,on=look[it.slot]===it.id,st=status(api,it);
  const tag=worn?'<small class="wd-tag worn">Đang mặc</small>'
    :st?.lock?`<small class="wd-tag lock">🔒 ${esc(st.lock)}</small>`
    :st?.buy?`<small class="wd-tag price">${st.price<it.price?`<s>${fmt(it.price)}</s> `:''}${fmt(st.price)} xu</small>`
    :`<small class="wd-tag">${it.price?'Đã có':it.need?'Đã mở':'Miễn phí'}</small>`;
  return `<button type="button" class="wd-item${on?' on':''}${st?.lock?' locked':''}" data-action="jrWdTry" data-item="${esc(it.id)}" aria-pressed="${on}">
    <span class="wd-thumb" aria-hidden="true">${thumb({...look,[it.slot]:it.id},gender,it.slot)}</span><b>${esc(it.name)}</b>${tag}</button>`;
}

function actions(api,look,saved){
  const changed=SLOTS.filter(k=>look[k]!==saved[k]);
  if(!changed.length)return `<p class="wd-hint">Đây là bộ bạn đang mặc. Chạm một món bên dưới để mặc thử.</p>`;
  const rows=changed.map(k=>{const it=itemOf(api,look[k]);return {it,st:status(api,it)};});
  const buys=rows.filter(r=>r.st?.buy).map(r=>btn(`Mua ${esc(r.it.name)} · ${fmt(r.st.price)} xu`,'jrWdBuy',{item:r.it.id},'primary full'));
  const locks=rows.filter(r=>r.st?.lock).map(r=>`<p class="wd-lock">🔒 ${esc(r.it.name)}: ${esc(r.st.lock.charAt(0).toLowerCase()+r.st.lock.slice(1))}.</p>`);
  const wear=rows.every(r=>!r.st)?btn('✨ Mặc bộ này','jrWdWear',{},'primary full'):'';
  return `${locks.join('')}${buys.join('')}${wear}${btn('Bỏ thử, mặc lại bộ cũ','jrWdReset',{},'ghost small full')}`;
}

export function wardrobeView(env){
  const {api,ui}=env,c=C(api),J=api.state.journey,st=S(ui),g=J.gender;
  const top=`<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại hành trình">${icon('back',18)}</button><div class="grow"><span class="eyebrow">NHÂN VẬT</span><h2>Tủ đồ</h2><p>Mặc thử thoải mái, ưng bộ nào thì mặc bộ đó.</p></div></header>`;
  if(!c)return top+`<div class="sheet-body jr-body"><p class="muted">Tủ đồ đang được sắp xếp, lát nữa quay lại nhé.</p></div>`;
  if(!SLOTS.includes(st.tab))st.tab='top';
  const saved=lookOf(api.state),look={...saved,...st.draft};
  const purse=J.story?`<p class="wd-purse">${icon('coin',16)} Ví của bạn <b>${J.wallet<0?`nợ ${fmt(-J.wallet)}`:fmt(J.wallet)} xu</b></p>`:'';
  const shop=staff(api)?`<p class="wd-note good">🏷️ Bạn là người của ${esc(c.shop_name)}: mọi món giảm ${c.staff_off}%.</p>`
    :`<p class="wd-note">🏷️ Làm ở ${esc(c.shop_name)} sẽ được giá nhân viên, giảm ${c.staff_off}%.</p>`;
  const tabs=c.slots.map(s=>`<button type="button" role="tab" class="wd-tab${st.tab===s.id?' active':''}" aria-selected="${st.tab===s.id}" data-action="jrWdTab" data-tab="${s.id}"><span aria-hidden="true">${TAB_EMOJI[s.id]||'•'}</span>${esc(s.name)}${look[s.id]!==saved[s.id]?'<i class="wd-dot" aria-label="đang thử"></i>':''}</button>`).join('');
  const grid=c.items.filter(x=>x.slot===st.tab).map(it=>tile(api,it,look,saved,g)).join('');
  return top+`<div class="sheet-body jr-body wd">
    <section class="jr-card wd-stage">
      <div class="wd-mirror">${figureSVG(look,g,{w:150,h:212,label:'Nhân vật của bạn trong bộ đồ đang thử'})}</div>
      <div class="wd-side"><h3>${esc(api.state.name)}</h3>${purse}${shop}<div class="wd-actions" aria-live="polite">${actions(api,look,saved)}</div></div>
    </section>
    <nav class="wd-tabs" role="tablist" aria-label="Loại đồ">${tabs}</nav>
    <div class="wd-grid">${grid}</div>
    <section class="jr-card wd-work"><label class="switch-row"><span class="grow"><b>Mặc đồ làm việc khi vào ca</b><small class="muted block">Tạp dề, áo blouse, yếm… theo nơi bạn làm. Tắt đi thì ở tiệm bạn mặc đúng bộ trong tủ.</small></span><input type="checkbox" role="switch" data-action="jrWdUniform" ${saved.uniform?'checked':''}><i aria-hidden="true"></i></label></section>
  </div>`;
}

export async function wardrobeAction(action,data,el,env){
  const {api,ui,cmd,renderSheet,confirmAction}=env,st=S(ui),c=C(api);
  if(!c)return false;
  switch(action){
    case'jrWdTab':st.tab=SLOTS.includes(data.tab)?data.tab:'top';renderSheet();return true;
    case'jrWdTry':{const it=itemOf(api,data.item);if(!it)return true;
      if(lookOf(api.state)[it.slot]===it.id)delete st.draft[it.slot];else st.draft[it.slot]=it.id;renderSheet();return true;}
    case'jrWdReset':st.draft={};renderSheet();return true;
    case'jrWdWear':{const saved=lookOf(api.state),look={};
      for(const [k,v] of Object.entries(st.draft))if(saved[k]!==v)look[k]=v;
      if(Object.keys(look).length&&!await cmd('jr_wd_wear',{look}))return true;
      st.draft={};renderSheet();return true;}
    case'jrWdBuy':{const it=itemOf(api,data.item);if(!it)return true;
      const price=priceOf(api,it),w=api.state.journey.wallet,card=api.state.journey.bank?.card;
      if(w<price&&!card){env.toast?.(`Ví mới có ${fmt(Math.max(0,w))} xu, chưa đủ ${fmt(price)} xu để mua ${it.name}. Làm thêm vài ca rồi quay lại nhé.`,true);return true;}
      const note=w>=price?`Ví của bạn đang có ${fmt(w)} xu.`:`Ví chưa đủ nên sẽ quẹt thẻ Ngân hàng Phố.`;
      if(!await confirmAction(`Mua ${it.name}?`,`Giá ${fmt(price)} xu${price<it.price?` (giá nhân viên ${c.shop_name}, giá gốc ${fmt(it.price)} xu)`:''}. ${note}`,`Mua · ${fmt(price)} xu`))return true;
      if(await cmd('jr_wd_buy',{item:it.id,wear:true})){if(st.draft[it.slot]===it.id)delete st.draft[it.slot];}
      renderSheet();return true;}
    case'jrWdUniform':{const on=el?.type==='checkbox'?el.checked:!lookOf(api.state).uniform;
      await cmd('jr_wd_wear',{look:{uniform:on}});renderSheet();return true;}
  }
  return false;
}
