/** 🧺 Đồ đạc của bạn (🏠 Nhà của bạn, v4/house.js): every thing the player owns, down to the smallest, with its name
 * and what it is (owner 06/10, góp ý #192): the furniture where it stands (room by room) and in the bag, the clothes
 * and accessories (worn or in the wardrobe), the vehicles (the one parked out front and the others), the food in the
 * fridge and the wallpapers bought. Read-only: it draws what the state already holds (journey.deco, journey.garage,
 * wardrobe, colors) with the static catalogues (content.journey.deco / wardrobe / garage); nothing is sent.
 * A fold's rows are drawn only while it is open (a home can hold hundreds of pieces); the same kind in the same
 * room is one row ×N. Pure: no DOM, no imports (tests/home_items.mjs). */
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const CLOTHES=['top','bottom','shoes','acc'];

/** Every room name of the place you live in, by id (the rooms every build draws, then the new ones by their kit). */
function roomNames(deco,CD){
  const out=new Map();
  for(const r of deco?.rooms||[])out.set(r.id,`${r.emoji||''} ${r.name}`.trim());
  for(const m of deco?.more||[]){const k=CD?.kits?.[m.t];if(k)out.set(k.id,`${k.emoji||''} ${k.name}`.trim());}
  return out;
}

/** What the player owns, counted: {deco, wear, cars, food, skins, total}. */
export function ownedCounts(state,content){
  const J=state?.journey||{},deco=J.deco,C=content?.journey||{};
  const n={deco:(deco?.items?.length||0)+(deco?.bag?.length||0),wear:wearList(state,C).length,cars:(J.garage?.cars||[]).length,
    food:(deco?.fridge?.foods||[]).reduce((a,f)=>a+(f.n||0),0),skins:(deco?.owned||[]).length};
  n.total=n.deco+n.wear+n.cars+n.food+n.skins;
  return n;
}

function wearList(state,C){
  const W=C.wardrobe,items=W?.items||[];if(!items.length)return [];
  const owned=new Set(state?.wardrobe?.owned||[]),look=state?.wardrobe?.look||{},worn=new Set(CLOTHES.map(s=>look[s]).filter(Boolean));
  return items.filter(it=>CLOTHES.includes(it.slot)&&it.id!=='pk_khong'&&(owned.has(it.id)||worn.has(it.id))).map(it=>({it,worn:worn.has(it.id),bought:owned.has(it.id)}));
}

/** The furniture rows: [{title, rows:[{it, n, uid, tint, back}]}], the rooms first (in their order), then the bag. */
export function decoGroups(state,content){
  const J=state?.journey||{},deco=J.deco,CD=content?.journey?.deco||{},byId=new Map((CD.items||[]).map(i=>[i.id,i]));
  if(!deco)return [];
  const names=roomNames(deco,CD),tints=state?.colors?.deco||{},groups=new Map();
  const add=(title,p)=>{const it=byId.get(p.k);if(!it)return;
    if(!groups.has(title))groups.set(title,new Map());
    const g=groups.get(title),key=`${p.k}|${tints[p.id]||''}|${p.face||''}`;
    if(g.has(key))g.get(key).n++;else g.set(key,{it,n:1,uid:p.id,tint:tints[p.id]||null,back:p.face==='back'});};
  for(const id of names.keys())for(const p of deco.items||[])if(p.r===id)add(names.get(id),p);
  for(const p of deco.items||[])if(!names.has(p.r))add('🏠 Trong nhà',p);
  for(const b of deco.bag||[])add('🎒 Trong túi đồ (chưa bày)',b);
  return [...groups.entries()].map(([title,g])=>({title,rows:[...g.values()].sort((a,b)=>a.it.name.localeCompare(b.it.name,'vi'))}));
}

/** One furniture row: its picture, name, what it is and what it is worth. */
function decoRow(r,CD,colorName,thumb){
  const cat=(CD.cats||[]).find(c=>c.id===r.it.cat),where=r.it.spot==='wall'?'treo tường':r.it.spot==='rug'?'trải sàn':r.it.spot==='top'?'đồ nhỏ, đặt lên bàn kệ':'đặt sàn';
  const bits=[cat?`${cat.emoji} ${cat.name}`:'',where,`ấm cúng +${r.it.cozy}`,`giá ${xu(r.it.price)}`,`bán lại ${xu(r.it.sell)}`,
    r.tint?`màu ${colorName(r.tint)}`:'',r.back?'đang quay mặt sau':''].filter(Boolean);
  return `<li class="hs-inv-row"><span class="hs-inv-pic" aria-hidden="true">${thumb?thumb(r.it,36,r.tint):esc(r.it.emoji)}</span><span class="hs-inv-txt"><b>${esc(r.it.name)}${r.n>1?` <i class="hs-inv-n">×${r.n}</i>`:''}</b><small>${esc(bits.join(' · '))}</small></span></li>`;
}

/** The card. opts: {open: Set of the folds open now, thumb(it, size, tint) (v4/deco-art.js), btn(label, op, data, cls)}. */
export function inventoryHTML(state,content,opts={}){
  const J=state?.journey||{},C=content?.journey||{},CD=C.deco||{},open=opts.open||new Set(),btn=opts.btn||(()=>'');
  const count=ownedCounts(state,content);
  const colors=new Map((C.wardrobe?.colors||[]).map(c=>[c.id,c.name]));
  const colorName=id=>colors.get(id)||id;
  const fold=(id,title,n,body,empty)=>`<details class="hs-inv-fold" data-inv="${id}"${open.has(id)?' open':''}><summary><b>${title}</b><small>${n?`${fmt(n)} món`:'chưa có'}</small></summary>${open.has(id)?(n?body():`<p class="bk-hint">${esc(empty)}</p>`):''}</details>`;
  const deco=()=>decoGroups(state,content).map(g=>`<h5 class="hs-inv-room">${esc(g.title)} <small>${fmt(g.rows.reduce((a,r)=>a+r.n,0))} món</small></h5><ul class="hs-inv-list">${g.rows.map(r=>decoRow(r,CD,colorName,opts.thumb)).join('')}</ul>`).join('')
    +(J.deco?`<div class="bk-actions">${btn('🚪 Vào phòng bày trí','inside',{mode:'decor'},'ghost small')}</div>`:'');
  const wear=()=>{const slots=new Map((C.wardrobe?.slots||[]).map(s=>[s.id,s.name])),tint=state?.colors?.wear||{},acc=state?.wardrobe_colors?.wear||{};
    return `<ul class="hs-inv-list">${wearList(state,C).sort((a,b)=>(b.worn-a.worn)||CLOTHES.indexOf(a.it.slot)-CLOTHES.indexOf(b.it.slot)).map(({it,worn,bought})=>{
      const c=tint[it.id]||acc[it.id];
      const bits=[slots.get(it.slot)||it.slot,worn?'đang mặc':'trong tủ đồ',bought&&it.price?`giá ${xu(it.price)}`:'có sẵn',c&&c!=='goc'?`màu ${colorName(c)}`:''].filter(Boolean);
      return `<li class="hs-inv-row"><span class="hs-inv-pic" aria-hidden="true">${it.slot==='acc'?'🧢':it.slot==='shoes'?'👟':it.slot==='bottom'?'👖':'👕'}</span><span class="hs-inv-txt"><b>${esc(it.name)}${worn?' <i class="hs-inv-tag">Đang mặc</i>':''}</b><small>${esc(bits.join(' · '))}</small></span></li>`;}).join('')}</ul>`
      +`<div class="bk-actions">${btn('👗 Mở tủ đồ','wardrobe',{},'ghost small')}</div>`;};
  const cars=()=>{const G=C.garage||{},V=new Map((G.vehicles||[]).map(v=>[v.id,v])),paint=new Map((G.paints||[]).map(p=>[p.id,p])),ride=J.garage?.ride;
    return `<ul class="hs-inv-list">${(J.garage?.cars||[]).map(c=>{const v=V.get(c.id);if(!v)return '';const p=paint.get(c.color);
      const bits=[p?`sơn ${p.name}`:'',c.plate?`biển “${c.plate}”`:'',`mua ngày ${c.day} · ${xu(c.paid)}`,c.upkeep?`bảo dưỡng ${xu(c.upkeep)}/tháng`:'',`bán lại ${xu(c.sell)}`,c.broken?`đang hỏng (sửa ${xu(c.broken)})`:''].filter(Boolean);
      return `<li class="hs-inv-row"><span class="hs-inv-pic" aria-hidden="true">${esc(v.emoji)}</span><span class="hs-inv-txt"><b>${esc(v.name)}${c.id===ride?' <i class="hs-inv-tag">🅿️ Đậu trước nhà</i>':''}</b><small>${esc(bits.join(' · '))}</small></span></li>`;}).join('')}</ul>`
      +`<div class="bk-actions">${btn('🚗 Mở ga-ra','garage',{},'ghost small')}</div>`;};
  const food=()=>`<ul class="hs-inv-list">${(J.deco?.fridge?.foods||[]).filter(f=>f.n>0).map(f=>`<li class="hs-inv-row"><span class="hs-inv-pic" aria-hidden="true">${esc(f.emoji)}</span><span class="hs-inv-txt"><b>${esc(f.name)} <i class="hs-inv-n">×${f.n}</i></b><small>${esc([f.full?`no bụng +${f.full}`:'',f.wake?`tỉnh táo +${f.wake}`:'',`giá ${xu(f.price)}`].filter(Boolean).join(' · '))}</small></span></li>`).join('')}</ul>`;
  const skins=()=>{const S=new Map((CD.skins||[]).map(s=>[s.id,s]));
    return `<ul class="hs-inv-list">${(J.deco?.owned||[]).map(id=>S.get(id)).filter(Boolean).map(s=>`<li class="hs-inv-row"><span class="hs-inv-pic" aria-hidden="true">${s.part==='wall'?'🧱':'🟫'}</span><span class="hs-inv-txt"><b>${esc(s.name)}</b><small>${esc(`${s.part==='wall'?'giấy dán tường':'sàn nhà'} · dùng được cho mọi phòng · giá ${xu(s.price)}`)}</small></span></li>`).join('')}</ul>`;};
  return `<section class="bk-card hs-inv" aria-labelledby="hs-inv-title"><h3 id="hs-inv-title">🧺 Đồ đạc của bạn · ${fmt(count.total)} món</h3>
    <p class="bk-hint">Mọi thứ bạn đang có, chạm từng mục để xem tên và thông tin. Dọn nhà thì đồ đi theo bạn.</p>
    ${fold('deco','🪴 Nội thất & đồ trang trí',count.deco,deco,'Chưa có món nào. Vào phòng, mở 🛒 Cửa hàng để mua món đầu tiên nhé.')}
    ${fold('wear','👗 Quần áo & phụ kiện',count.wear,wear,'Chưa có đồ nào.')}
    ${fold('cars','🚗 Xe & phương tiện',count.cars,cars,'Chưa có xe. Ghé Cửa hàng xe trong ga-ra nhé.')}
    ${fold('food','🧊 Đồ ăn trong tủ lạnh',count.food,food,'Tủ lạnh đang trống.')}
    ${fold('skins','🎨 Giấy dán tường & sàn đã mua',count.skins,skins,'Chưa mua mẫu nào (mẫu miễn phí luôn dùng được).')}</section>`;
}
