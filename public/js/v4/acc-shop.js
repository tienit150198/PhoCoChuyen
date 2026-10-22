/** 🛍️ Tiệm phụ kiện Hạt Cườm (owner 22/10: "chuyển chỗ mua linh kiện từ avatar ra 1 nơi khác"): accessories are bought
 * here now, no longer in the wardrobe, which keeps trying on, colours and wearing (v4/wardrobe.js). Opened from the town
 * (Mua sắm, isometric/town-utilities.js), the menu (app.js) and the wardrobe (journey.js: jrView 'accshop', actions jrAs*).
 * Two shelves:
 * - 🎀 Phụ kiện: the wardrobe's accessories (game/wardrobe.py, slot acc), tried on the mirror, bought with jr_wd_buy as
 *   before (so every earlier purchase stays where it was) and worn with jr_wd_wear.
 * - 🤝 Phụ kiện đôi (góp ý #484): Chí cốt, Bạn thân, Tri kỉ, bought as a pair (charm_buy), one piece given to a friend
 *   (charm_offer), who accepts or declines; the box, the offers sent and received, every pair with its own switch (no
 *   limit on how many are worn). Rules on the server (game/friend_charms.py); data and the shared rows: v4/charms.js. */
import {icon,escapeHTML as esc} from '../icons.js';
import {confirmPurchase} from './payment.js';
import {lookOf,figureSVG,portrait,pairIcon,myPairs} from './look.js';
import {kinds,kindOf,adopt,refreshCharms,pairRow,waiting} from './charms.js';
import {wdStatus,wdItem} from './wardrobe.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const W=api=>api.content.journey?.wardrobe;
const S=ui=>ui.as??={tab:'acc',draft:null,to:''};
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,action,data={},style='',dis=false)=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${dis?' disabled':''}>${label}</button>`;
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
let busy=false;

/* ---- 🎀 Phụ kiện ---- */
function accTile(api,st,it,saved,look,g){
  const worn=saved.acc===it.id,on=look.acc===it.id,stt=wdStatus(api,it);
  const tag=worn?'<small class="wd-tag worn">Đang đeo</small>'
    :stt?.lock?`<small class="wd-tag lock">🔒 ${esc(stt.lock)}</small>`
    :stt?.buy?`<small class="wd-tag price">${stt.price<it.price?`<s>${fmt(it.price)}</s> `:''}${fmt(stt.price)} xu</small>`
    :`<small class="wd-tag">${it.price?'Đã có':it.need?'Đã mở':'Miễn phí'}</small>`;
  return `<button type="button" class="wd-item${on?' on':''}${stt?.lock?' locked':''}" data-action="jrAsTry" data-item="${esc(it.id)}" aria-pressed="${on}">
    <span class="wd-thumb" aria-hidden="true">${portrait({...look,acc:it.id},g,64,'')}</span><b>${esc(it.name)}</b>${tag}</button>`;
}
function accActions(api,st,saved,look){
  if(!st.draft||st.draft===saved.acc)return `<p class="wd-hint">👇 Chạm một món để đeo thử trước gương.</p>`;
  const it=wdItem(api,st.draft),stt=it&&wdStatus(api,it);if(!it)return '';
  const main=stt?.lock?`<p class="wd-lock">🔒 ${esc(it.name)}: ${esc(stt.lock.charAt(0).toLowerCase()+stt.lock.slice(1))}.</p>`
    :stt?.buy?btn(`Mua ${esc(it.name)} · ${fmt(stt.price)} xu`,'jrAsBuy',{item:it.id},'primary full',busy)
    :btn(`🎀 Đeo ${esc(it.name)}`,'jrAsWearAcc',{item:it.id},'primary full',busy);
  return main+btn('Bỏ thử','jrAsReset',{},'ghost small full');
}
function accShelf(env,st){
  const {api}=env,c=W(api),g=api.state.journey.gender,saved=lookOf(api.state),look={...saved,...(st.draft?{acc:st.draft}:{})};
  const pr=myPairs(),mirror=figureSVG(pr?{...look,pr}:look,g,{w:150,h:212,label:'Nhân vật của bạn đang đeo thử'});
  const items=c.items.filter(x=>x.slot==='acc'&&x.id!=='pk_khong');
  const staff=c.staff_off&&api.state.careers?.[c.shop]?.started?`<p class="wd-note good">🏷️ Giá nhân viên ${esc(c.shop_name)}: −${c.staff_off}%</p>`:'';
  return `<section class="jr-card wd-stage">
      <div class="wd-mirror">${mirror}</div>
      <div class="wd-side"><h3>${esc(api.state.name)}</h3>${staff}<div class="wd-actions" aria-live="polite">${accActions(api,st,saved,look)}</div></div>
    </section>
    <div class="wd-grid">${items.map(it=>accTile(api,st,it,saved,look,g)).join('')}</div>
    <p class="wd-note as-foot">🎨 Đổi màu, phối với áo quần: ${btn('👗 Tủ đồ','jrWardrobe',{},'ghost small')}</p>`;
}

/* ---- 🤝 Phụ kiện đôi ---- */
function friendPick(v,st,id){
  const fr=v.friends||[];
  if(!fr.length)return `<p class="muted small">Kết bạn trước rồi tặng nhé.</p>`;
  const opts=fr.map(f=>`<option value="${esc(f.code)}"${f.code===st.to?' selected':''}>${esc(f.name)}</option>`).join('');
  return `<div class="as-give"><label class="sr-only" for="as-to-${esc(id)}">Tặng cho</label><select class="input" id="as-to-${esc(id)}" data-as-to>${st.to&&fr.some(f=>f.code===st.to)?'':'<option value="">Chọn một người bạn…</option>'}${opts}</select>
    ${btn('🎁 Tặng','jrAsGive',{id},'primary small',busy)}</div>`;
}
function pairShelf(env,st){
  const {api}=env,v=api.charmView,list=kinds(api);
  refreshCharms(env,15000)?.then(x=>{if(x)env.renderSheet(false);});   // a gift may have come in since
  const canBuy=!v||v.can_buy!==false,toName=st.to&&v?.friends?.find(f=>f.code===st.to)?.name;
  const forWho=toName?`<p class="jr-card as-for">🎁 <span class="grow">Đang chọn quà cho <b>${esc(toName)}</b>: mua xong là gửi luôn.</span>${btn('Bỏ chọn','jrAsTo',{code:''},'ghost small')}</p>`:'';
  const cat=list.map(k=>`<article class="jr-card as-kind as-${esc(k.id)}">
      <span class="as-kind-art">${pairIcon(k.id,84,`Cặp ${k.name}`)}</span>
      <div class="as-kind-text"><h3>${esc(k.emoji)} ${esc(k.name)}</h3><p class="as-item">${esc(k.item)}</p><p class="small">${esc(k.desc)}</p><p class="as-hint">${esc(k.hint)}</p>
      ${btn(`${toName?'Mua & tặng':'Mua cặp'} · ${fmt(k.price)} xu`,'jrAsPairBuy',{kind:k.id},'primary small',busy||!canBuy)}</div></article>`).join('');
  if(!v)return `<div class="as-shelf">${cat}</div><p class="muted small">Đang mở hộp quà…</p>`;
  const K=id=>kindOf(api,id)||{emoji:'🎁',name:'Phụ kiện'};
  const incoming=v.incoming.length?`<section class="jr-card as-incoming" aria-label="Quà đang chờ bạn"><h3>🎁 Quà đang chờ bạn</h3><ul class="as-list">${v.incoming.map(o=>`<li><span class="as-pair-art">${pairIcon(o.kind,44)}</span>
      <span class="grow"><b>${esc(o.name)}</b><small>tặng bạn một chiếc ${esc(K(o.kind).emoji)} ${esc(K(o.kind).name)}, mỗi người đeo một chiếc</small></span>
      <span class="as-row-btns">${btn('Nhận','jrAsAnswer',{id:o.id,answer:'accept'},'primary small',busy)}${btn('Từ chối','jrAsAnswer',{id:o.id,answer:'decline'},'ghost small',busy)}</span></li>`).join('')}</ul></section>`:'';
  const box=v.box.length?`<section class="jr-card as-box" aria-label="Hộp quà"><h3>🎀 Hộp quà <small class="muted">${v.box.length}/${v.box_max}</small></h3><p class="muted small">Tặng một chiếc cho bạn bè, cặp này thành của hai người.</p><ul class="as-list">${v.box.map(b=>`<li class="as-box-row"><span class="as-pair-art">${pairIcon(b.kind,44)}</span>
      <span class="grow"><b>${esc(K(b.kind).emoji)} ${esc(K(b.kind).name)}</b>${friendPick(v,st,b.id)}</span>
      ${btn(`Bán lại · ${fmt(b.sell)} xu`,'jrAsSell',{id:b.id},'ghost small',busy)}</li>`).join('')}</ul></section>`:'';
  const sent=v.sent.length?`<section class="jr-card as-sent" aria-label="Đã gửi"><h3>⏳ Chờ bạn nhận</h3><ul class="as-list">${v.sent.map(o=>`<li><span class="as-pair-art">${pairIcon(o.kind,44)}</span>
      <span class="grow"><b>${esc(K(o.kind).emoji)} ${esc(K(o.kind).name)}</b><small>đã gửi tới ${esc(o.name)}</small></span>${btn('Rút lại','jrAsCancel',{id:o.id},'ghost small',busy)}</li>`).join('')}</ul></section>`:'';
  const on=v.pairs.filter(p=>p.on).length;
  const mine=v.pairs.length?`<section class="jr-card as-mine" aria-label="Cặp của bạn"><div class="as-mine-head"><b>🤝 Đang có ${v.pairs.length} cặp</b><small class="muted">đang đeo ${on}</small></div>
      <ul class="as-pairs">${v.pairs.map(p=>pairRow(api,p)).join('')}</ul>
      <div class="as-mine-foot">${btn('Đeo hết','jrAsWearAll',{on:'1'},'ghost small',busy||on===v.pairs.length)}${btn('Cất hết','jrAsWearAll',{on:'0'},'ghost small',busy||!on)}</div></section>`:'';
  const full=v.can_buy===false?`<p class="wd-lock">🎀 Hộp quà đã đầy ${v.box_max} cặp chưa tặng. Tặng bớt rồi mua thêm nhé.</p>`:'';
  return `${incoming}${forWho}${mine}${box}${sent}${full}<div class="as-shelf">${cat}</div>`;
}

export function accShopView(env){
  const {api,ui}=env,c=W(api),st=S(ui);
  const name=c?.acc_shop?.title||'Tiệm phụ kiện';
  const top=`<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại">${icon('back',18)}</button><div class="grow"><span class="eyebrow">MUA SẮM</span><h2>${esc(name)}</h2></div></header>`;
  if(!c||!api.state.journey?.gender)return top+`<div class="sheet-body jr-body"><p class="muted">Tiệm đang bày hàng, lát nữa quay lại nhé.</p></div>`;
  if(!['acc','pair'].includes(st.tab))st.tab='acc';
  const n=waiting(api);
  const tabs=[['acc','🎀','Phụ kiện'],['pair','🤝',`Phụ kiện đôi`]].map(([id,e,label])=>`<button type="button" role="tab" class="wd-tab${st.tab===id?' active':''}" aria-selected="${st.tab===id}" data-action="jrAsTab" data-tab="${id}"><span aria-hidden="true">${e}</span>${label}${id==='pair'&&n?`<i class="as-badge" aria-label="${n} món quà đang chờ">${n}</i>`:''}</button>`).join('');
  return top+`<div class="sheet-body jr-body wd as">
    <nav class="wd-tabs" role="tablist" aria-label="Quầy hàng">${tabs}</nav>
    ${st.tab==='acc'?accShelf(env,st):pairShelf(env,st)}
  </div>`;
}

async function post(env,op,body){
  const {api,toast}=env;
  busy=true;env.renderSheet(false);
  try{
    const d=await api.json(`/api/marriage/${op}`,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body)});
    adopt(api,d,()=>env.renderMain?.());
    if(d?.message)toast(d.message,'good');
    return d;
  }catch(e){toast(e.message||'Chưa làm được. Thử lại nhé.',true);return null;}
  finally{busy=false;env.renderSheet(false);}
}

export async function accShopAction(action,data,el,env){
  const {api,ui,cmd,renderSheet,confirmAction}=env,st=S(ui),c=W(api);
  if(!c)return false;
  switch(action){
    case'jrAsTab':st.tab=data.tab==='pair'?'pair':'acc';renderSheet(false);return true;
    case'jrAsTry':{const it=wdItem(api,data.item);if(!it||it.slot!=='acc')return true;st.draft=st.draft===it.id?null:it.id;renderSheet(false);return true;}
    case'jrAsReset':st.draft=null;renderSheet(false);return true;
    case'jrAsBuy':{const it=wdItem(api,data.item),stt=it&&wdStatus(api,it);if(!stt?.buy||busy)return true;
      const how=await confirmPurchase(env,{title:`Mua ${it.name}?`,message:`Giá ${fmt(stt.price)} xu${stt.price<it.price?` (giá nhân viên ${c.shop_name}, giá gốc ${fmt(it.price)} xu)`:''}. Mua xong đeo luôn, đổi màu trong Tủ đồ.`,label:`Mua · ${fmt(stt.price)} xu`,cost:stt.price});
      if(!how)return true;
      if(await cmd('jr_wd_buy',{item:it.id,wear:true,pay:how}))st.draft=null;
      renderSheet(false);return true;}
    case'jrAsWearAcc':{const it=wdItem(api,data.item);if(!it||wdStatus(api,it))return true;
      if(await cmd('jr_wd_wear',{look:{acc:it.id}}))st.draft=null;renderSheet(false);return true;}
    case'jrAsPairBuy':{const k=kindOf(api,data.kind);if(!k||busy)return true;
      const who=st.to&&api.charmView?.friends?.find(f=>f.code===st.to)?.name;
      const how=await confirmPurchase(env,{title:`Mua cặp ${k.name}?`,message:`${k.item}, hai chiếc. Giá ${fmt(k.price)} xu. ${who?`Bạn giữ một chiếc, chiếc còn lại gửi tới ${who}.`:'Bạn giữ một chiếc, tặng chiếc còn lại cho một người bạn.'}`,label:`Mua · ${fmt(k.price)} xu`,cost:k.price});
      if(!how)return true;
      const to=st.to&&api.charmView?.friends?.find(f=>f.code===st.to);
      if(await post(env,'charm_buy',{kind:k.id,pay:how,rid:rid(),...(to?{code:to.code}:{})})&&to)st.to='';renderSheet(false);return true;}
    case'jrAsTo':st.to=typeof data.code==='string'?data.code:'';renderSheet(false);return true;
    case'jrAsGive':{const sel=document.getElementById(`as-to-${data.id}`),code=sel?.value||st.to;
      if(!code){env.toast('Chọn một người bạn để tặng nhé.','hint');sel?.focus?.();return true;}
      st.to=code;await post(env,'charm_offer',{id:data.id,code});return true;}
    case'jrAsAnswer':{if(data.answer==='decline'&&!await confirmAction('Từ chối món quà?','Món quà sẽ trở về hộp quà của bạn ấy.','Từ chối'))return true;
      await post(env,'charm_respond',{id:data.id,answer:data.answer==='accept'?'accept':'decline'});return true;}
    case'jrAsCancel':await post(env,'charm_cancel',{id:data.id});return true;
    case'jrAsSell':{const b=api.charmView?.box?.find(x=>x.id===data.id),k=b&&kindOf(api,b.kind);if(!b)return true;
      if(!await confirmAction(`Bán lại cặp ${k?.name||''}?`,`Tiệm mua lại ${fmt(b.sell)} xu.`,`Bán · ${fmt(b.sell)} xu`))return true;
      await post(env,'charm_sell',{id:b.id,rid:rid()});return true;}
    case'jrAsWear':{const on=el?.type==='checkbox'?el.checked:!api.charmView?.pairs?.find(p=>p.id===data.id)?.on;
      await post(env,'charm_wear',{id:data.id,on});return true;}
    case'jrAsWearAll':await post(env,'charm_wear',{all:true,on:data.on==='1'});return true;
  }
  return false;
}
