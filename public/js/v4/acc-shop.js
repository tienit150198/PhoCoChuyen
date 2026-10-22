/** 🛍️ Tiệm phụ kiện Hạt Cườm (owner 22/10: "chuyển chỗ mua linh kiện từ avatar ra 1 nơi khác"): accessories are bought
 * here now, no longer in the wardrobe, which keeps trying on, colours and wearing (v4/wardrobe.js). Opened from the town
 * (Mua sắm, isometric/town-utilities.js), the menu (app.js) and the wardrobe (journey.js: jrView 'accshop', actions jrAs*).
 * Two shelves:
 * - 🎀 Phụ kiện: the wardrobe's accessories (game/wardrobe.py, slot acc), tried on the mirror, bought with jr_wd_buy as
 *   before (so every earlier purchase stays where it was) and worn with jr_wd_wear.
 * - 🤝 Phụ kiện đôi (góp ý #484): Chí cốt, Bạn thân, Tri kỉ, bought as a pair (charm_buy), one piece given to a friend
 *   (charm_offer), who accepts or declines; the box, the offers sent and received, every pair with its own switch (no
 *   limit on how many are worn). Rules on the server (game/friend_charms.py); data and the shared rows: v4/charms.js.
 *   💞 Under "Đang có", the relationship with that friend (charm_bond / charm_bond_answer / charm_bond_off): asked by one,
 *   shown once both agree; the asks waiting for this player on top.
 * - 🪽 Cánh (game/wings.py, owner 22/10): a style bought rolls hạng D or C on the server (jr_pet_wing_buy with a request id:
 *   a retry answers the same wings), shown in a small reveal; three wings ghép like the pets (jr_pet_wing_fuse, the first one
 *   picked is the main one and keeps its style); one worn at a time (jr_pet_wing_wear). The tier's badge and colour on
 *   every tile, what it adds (tiền kiếm được, sức thú khi đấu) under the mirror. */
import {icon,escapeHTML as esc} from '../icons.js';
import {confirmPurchase} from './payment.js';
import {lookOf,figureSVG,portrait,pairIcon,myPairs,wingIcon,wingOfState,WING_TIERS,WING_TIER_COLOR} from './look.js';
import {kinds,kindOf,adopt,refreshCharms,pairRows,waiting,relOf} from './charms.js';
import {wdStatus,wdItem} from './wardrobe.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const W=api=>api.content.journey?.wardrobe;
const S=ui=>ui.as??={tab:'acc',draft:null,to:'',wfz:[],reveal:null,wtry:null};
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
      <ul class="as-pairs">${pairRows(api,v.pairs)}</ul>
      <div class="as-mine-foot">${btn('Đeo hết','jrAsWearAll',{on:'1'},'ghost small',busy||on===v.pairs.length)}${btn('Cất hết','jrAsWearAll',{on:'0'},'ghost small',busy||!on)}</div></section>`:'';
  const full=v.can_buy===false?`<p class="wd-lock">🎀 Hộp quà đã đầy ${v.box_max} cặp chưa tặng. Tặng bớt rồi mua thêm nhé.</p>`:'';
  const bonds=(v.bond_in||[]).map(o=>({...o,r:relOf(api,o.label)})).filter(o=>o.r);
  const bondIn=bonds.length?`<section class="jr-card as-incoming" aria-label="Lời mời quan hệ"><h3>💞 Lời mời quan hệ</h3><ul class="as-list">${bonds.map(o=>`<li><span class="as-rel-emoji" aria-hidden="true">${esc(o.r.emoji)}</span>
      <span class="grow"><b>${esc(o.name)}</b><small>muốn hai bạn thành “${esc(o.r.name)}”</small></span>
      <span class="as-row-btns">${btn('Đồng ý','jrAsBondAnswer',{id:o.id,answer:'accept'},'primary small',busy)}${btn('Để sau','jrAsBondAnswer',{id:o.id,answer:'decline'},'ghost small',busy)}</span></li>`).join('')}</ul></section>`:'';
  return `${bondIn}${incoming}${forWho}${mine}${box}${sent}${full}<div class="as-shelf">${cat}</div>`;
}

/* ---- 🪽 Cánh ---- */
const WC=api=>api.content.journey?.wardrobe?.wings;
const wingsOf=api=>api.state.journey?.wings||null;
const tierName=r=>WING_TIERS[r]||'D';
const badge=r=>`<i class="wg-tier" style="--wt:${WING_TIER_COLOR[r]||WING_TIER_COLOR[0]}">${esc(tierName(r))}</i>`;
const styleOf=(api,k)=>WC(api)?.styles?.find(x=>x.id===k)||null;
const wName=(api,x)=>`${styleOf(api,x.k)?.name||'Cánh'} ${tierName(x.r)}`;
function wingPerks(api,r){const c=WC(api);if(!c)return '';
  return `<ul class="wg-perks"><li>💰 +${c.earn[r]}% tiền kiếm được khi làm việc <small>(tối đa ${fmt(c.cap[r])} xu/ngày)</small></li><li>⚔️ +${c.battle[r]}% máu và sức đánh cho thú khi đấu</li></ul>`;}
function fusePanel(api,st,own){
  const c=WC(api),xs=st.wfz.map(id=>own.find(x=>x.id===id)).filter(Boolean);
  if(!xs.length)return own.length>=3?`<p class="wd-hint">🧬 Chọn ba đôi để ghép lên hạng: đôi chọn đầu tiên là cánh chính, giữ nguyên kiểu.</p>`:'';
  const tiers=xs.map(x=>x.r),low=Math.min(...tiers),m=xs[0],top=WING_TIERS.length-1;
  const to=low===top-1?top:Math.max(m.r,low+1),fee=c.fee[Math.min(low,c.fee.length-1)],lose=low>=c.lose_from;
  const why=xs.length<3?`Chọn thêm ${3-xs.length} đôi nữa.`:m.r>=top?'Cánh chính đã là huyền thoại.':'';
  return `<section class="jr-card wg-fuse" aria-live="polite"><div class="wg-fuse-row">${xs.map((x,i)=>`<span class="wg-fuse-slot${i?'':' main'}">${wingIcon(x,48)}${badge(x.r)}</span>`).join('<b aria-hidden="true">+</b>')}</div>
    <p class="small">${why?esc(why):`Thành công: <b>${esc(styleOf(api,m.k)?.name||'Cánh')}</b> lên hạng <b>${esc(tierName(to))}</b>, hai đôi kia dùng hết. Trượt: ${lose?'⚠️ hai đôi kia sẽ mất, cánh chính ở lại':'ba đôi vẫn còn'}, mất phí.`}</p>
    <div class="as-row-btns">${btn(`🧬 Ghép · ${fmt(fee)} xu`,'jrAsWingFuse',{},'primary small',busy||!!why)}${btn('Bỏ chọn','jrAsWingPick',{id:''},'ghost small')}</div></section>`;
}
function wingShelf(env,st){
  const {api}=env,c=WC(api);
  if(!c)return `<p class="muted">Cánh đang về hàng, lát nữa quay lại nhé.</p>`;
  const w=wingsOf(api),own=Array.isArray(w?.own)?w.own:[],worn=wingOfState(api.state),g=api.state.journey.gender;
  st.wfz=st.wfz.filter(id=>own.some(x=>x.id===id));
  const show=st.wtry?{k:st.wtry,r:0}:worn,look=lookOf(api.state),pr=myPairs();
  const mirror=figureSVG({...look,...(pr?{pr}:{}),...(show?{wg:show}:{})},g,{w:150,h:212,label:show?'Nhân vật của bạn với đôi cánh':'Nhân vật của bạn'});
  const wx=worn&&own.find(x=>x.id===w.on);
  const side=st.wtry?`<h3>${esc(styleOf(api,st.wtry)?.name||'')}</h3><p class="small">Đang thử trước gương. Mua xong mới biết ra hạng D hay C nhé.</p>${btn('Bỏ thử','jrAsWingTry',{k:''},'ghost small')}`
    :wx?`<h3>${esc(wName(api,wx))} ${badge(wx.r)}</h3>${wingPerks(api,wx.r)}${w.got?`<p class="small muted">Hôm nay cánh đã thêm ${fmt(w.got)} xu.</p>`:''}`
    :`<h3>Chưa đeo cánh</h3><p class="small">Mỗi đôi mua về ra hạng D hoặc C, ghép ba đôi để lên hạng như nuôi thú. Hạng càng cao càng đẹp và càng được nhiều.</p>`;
  const rv=st.reveal?.length?`<section class="jr-card wg-reveal" aria-live="polite"><h3>🎉 Mở hộp cánh</h3><div class="wg-reveal-row">${st.reveal.map((x,i)=>`<span class="wg-reveal-item" style="--i:${i}">${wingIcon(x,72,wName(api,x))}${badge(x.r)}</span>`).join('')}</div>${btn('Tuyệt!','jrAsWingReveal',{},'primary small')}</section>`:'';
  const tiles=own.length?`<section class="jr-card wg-own"><div class="as-mine-head"><b>🪽 Tủ cánh</b><small class="muted">${own.length}/${c.own_max}</small></div>
    <ul class="wg-grid">${[...own].sort((a,b)=>b.r-a.r||String(a.k).localeCompare(b.k)).map(x=>{const on=x.id===w.on,pick=st.wfz.indexOf(x.id);
      return `<li class="wg-tile${on?' on':''}${pick>=0?' picked':''}" style="--wt:${WING_TIER_COLOR[x.r]}"><button type="button" class="wg-pick" data-action="jrAsWingPick" data-id="${esc(x.id)}" aria-pressed="${pick>=0}" aria-label="${esc(wName(api,x))}${pick===0?', cánh chính':''}">${wingIcon(x,64)}${badge(x.r)}${pick>=0?`<i class="wg-num" aria-hidden="true">${pick+1}</i>`:''}</button>
        <small>${esc(styleOf(api,x.k)?.name||'Cánh')}</small><span class="as-row-btns">${on?btn('Cất','jrAsWingWear',{id:''},'ghost small',busy):btn('Đeo','jrAsWingWear',{id:x.id},'small',busy)}${btn('Bỏ','jrAsWingDrop',{id:x.id},'ghost small',busy)}</span></li>`;}).join('')}</ul></section>`:'';
  const shelf=c.styles.map(x=>`<article class="jr-card as-kind wg-style"><button type="button" class="as-kind-art" data-action="jrAsWingTry" data-k="${esc(x.id)}" aria-label="Thử ${esc(x.name)} trước gương">${wingIcon({k:x.id,r:0},84)}</button>
      <div class="as-kind-text"><h3>${esc(x.emoji)} ${esc(x.name)}</h3><p class="small">${esc(x.desc)}</p><p class="as-hint">Ra hạng D hoặc C ngẫu nhiên</p>
      ${btn(`Mua · ${fmt(x.price)} xu`,'jrAsWingBuy',{k:x.id},'primary small',busy||own.length>=c.own_max)}</div></article>`).join('');
  const table=`<details class="jr-card wg-table"><summary>📈 Hạng cánh được gì</summary><table><thead><tr><th>Hạng</th><th>Tiền kiếm được</th><th>Thú khi đấu</th></tr></thead><tbody>${c.earn.map((e,r)=>`<tr><td>${badge(r)}</td><td>+${e}% <small class="muted">≤ ${fmt(c.cap[r])}/ngày</small></td><td>+${c.battle[r]}%</td></tr>`).join('')}</tbody></table></details>`;
  return `${rv}<section class="jr-card wd-stage"><div class="wd-mirror">${mirror}</div><div class="wd-side">${side}</div></section>${fusePanel(api,st,own)}${tiles}<div class="as-shelf">${shelf}</div>${table}`;
}

export function accShopView(env){
  const {api,ui}=env,c=W(api),st=S(ui);
  const name=c?.acc_shop?.title||'Tiệm phụ kiện';
  const top=`<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại">${icon('back',18)}</button><div class="grow"><span class="eyebrow">MUA SẮM</span><h2>${esc(name)}</h2></div></header>`;
  if(!c||!api.state.journey?.gender)return top+`<div class="sheet-body jr-body"><p class="muted">Tiệm đang bày hàng, lát nữa quay lại nhé.</p></div>`;
  if(!['acc','pair','wing'].includes(st.tab))st.tab='acc';
  const n=waiting(api);
  const tabs=[['acc','🎀','Phụ kiện'],['pair','🤝',`Phụ kiện đôi`],...(c.wings?[['wing','🪽','Cánh']]:[])].map(([id,e,label])=>`<button type="button" role="tab" class="wd-tab${st.tab===id?' active':''}" aria-selected="${st.tab===id}" data-action="jrAsTab" data-tab="${id}"><span aria-hidden="true">${e}</span>${label}${id==='pair'&&n?`<i class="as-badge" aria-label="${n} món quà đang chờ">${n}</i>`:''}</button>`).join('');
  return top+`<div class="sheet-body jr-body wd as">
    <nav class="wd-tabs" role="tablist" aria-label="Quầy hàng">${tabs}</nav>
    ${st.tab==='acc'?accShelf(env,st):st.tab==='wing'?wingShelf(env,st):pairShelf(env,st)}
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
    case'jrAsTab':st.tab=['pair','wing'].includes(data.tab)?data.tab:'acc';renderSheet(false);return true;
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
    // 💞 the relationship with a friend (game/friend_charms.py)
    case'jrAsBond':{const r=relOf(api,data.label);if(!r||busy)return true;await post(env,'charm_bond',{id:data.id,label:r.id});return true;}
    case'jrAsBondAnswer':await post(env,'charm_bond_answer',{id:data.id,answer:data.answer==='accept'?'accept':'decline'});return true;
    case'jrAsBondOff':{if(!await confirmAction('Về lại bạn bè?','Quan hệ đang đặt sẽ bỏ, hai bạn vẫn là bạn bè và vẫn giữ phụ kiện đôi.','Về bạn bè'))return true;
      await post(env,'charm_bond_off',{id:data.id});return true;}
    // 🪽 Cánh (game/wings.py)
    case'jrAsWingTry':st.wtry=data.k&&WC(api)?.styles?.some(x=>x.id===data.k)?(st.wtry===data.k?null:data.k):null;renderSheet(false);return true;
    case'jrAsWingReveal':st.reveal=null;renderSheet(false);return true;
    case'jrAsWingBuy':{const x=styleOf(api,data.k);if(!x||busy)return true;
      if(!await confirmAction(`Mua ${x.name}?`,`Giá ${fmt(x.price)} xu. Mở hộp ra hạng D hoặc C ngẫu nhiên, ghép ba đôi để lên hạng.`,`🪽 Mua · ${fmt(x.price)} xu`,{cost:x.price}))return true;
      busy=true;const r=await cmd('jr_pet_wing_buy',{style:x.id,rid:rid().replace(/[^A-Za-z0-9_.:-]/g,'').slice(0,64),confirm:true});busy=false;
      if(r?.wings?.length){st.reveal=r.wings.map(w=>({k:w.k,r:w.r}));st.wtry=null;}renderSheet(false);return true;}
    case'jrAsWingWear':if(busy)return true;busy=true;await cmd('jr_pet_wing_wear',{id:data.id||null});busy=false;renderSheet(false);return true;
    case'jrAsWingDrop':{const x=wingsOf(api)?.own?.find(o=>o.id===data.id);if(!x||busy)return true;
      if(!await confirmAction(`Bỏ ${wName(api,x)}?`,'Đôi cánh này sẽ mất hẳn, không lấy lại được.','Bỏ cánh'))return true;
      busy=true;await cmd('jr_pet_wing_drop',{id:x.id,confirm:true});busy=false;st.wfz=st.wfz.filter(id=>id!==x.id);renderSheet(false);return true;}
    case'jrAsWingPick':{if(!data.id){st.wfz=[];renderSheet(false);return true;}
      const i=st.wfz.indexOf(data.id);if(i>=0)st.wfz.splice(i,1);else if(st.wfz.length<3)st.wfz.push(data.id);else st.wfz=[...st.wfz.slice(0,2),data.id];renderSheet(false);return true;}
    case'jrAsWingFuse':{const own=wingsOf(api)?.own||[],xs=st.wfz.map(id=>own.find(x=>x.id===id)).filter(Boolean),c2=WC(api);if(xs.length!==3||busy||!c2)return true;
      const low=Math.min(...xs.map(x=>x.r)),fee=c2.fee[Math.min(low,c2.fee.length-1)];
      if(!await confirmAction('Ghép ba đôi cánh?',`Phí ${fmt(fee)} xu, thành hay trượt đều mất phí.${low>=c2.lose_from?' ⚠️ Trượt thì hai đôi phụ sẽ mất.':''}`,`🧬 Ghép · ${fmt(fee)} xu`,{cost:fee}))return true;
      busy=true;const r=await cmd('jr_pet_wing_fuse',{wings:xs.map(x=>x.id),main:xs[0].id,confirm:true});busy=false;
      if(r?.fuse){const lost=r.fuse.lost||[];st.wfz=r.fuse.ok?[]:st.wfz.filter(id=>!lost.includes(id));if(r.fuse.ok){const m=(wingsOf(api)?.own||[]).find(x=>x.id===r.fuse.main);if(m)st.reveal=[{k:m.k,r:m.r}];}}
      renderSheet(false);return true;}
  }
  return false;
}
