/** 💍 Sống chung (game/wedding_life.py, góp ý #442 / #444): the tab of the Hôn nhân sheet where a couple holds the lễ rước dâu
 * + lễ gia tiên together (six steps, taking turns), goes on a trip together (a ticket, a rented plane or yacht, or their
 * own; both accept, the money held until then) with a photo a day in the shared album, and does the day's chores
 * together. Every rule and every price lives on the server (POST /api/marriage/wl_*; the view's `life`); this only
 * draws it. Photos are the game's own render (./portrait-art.js), never an upload. Names are escaped display names. */
import {escapeHTML as esc} from '../icons.js';
import {confirmPurchase} from './payment.js';

const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,act,data={},cls='cream',dis=false)=>`<button type="button" class="btn ${cls}" data-mr="wl:${act}"${attrs(data)}${dis?' disabled':''}>${label}</button>`;
const hhmm=at=>{const d=new Date(at*1000+7*3600*1000);return d.toISOString().slice(11,16);};
const PAY={fund:'🏦 Quỹ chung',split:'✂️ Chia đôi',me:'🙋 Mình bao'};
const PHOTOS=new Map();   // photo id -> render data (the album and the trip cards share it)

/** The tab's label: the ceremony for an engaged couple, life together once married. */
export const lifeLabel=c=>c?.status==='married'?'🏠 Sống chung':'🧺 Lễ gia tiên';

export function lifeView(life,c,form,busy){
  if(!life)return `<section class="mr-card"><h3>🏠 Sống chung</h3><p>Chưa tải được mục này.</p>${btn('Thử tải lại','retry')}</section>`;
  const parts=[bigView(form),riteCard(life.rite,form,busy)];
  if(life.married)parts.push(tripCard(life,form,busy),choresCard(life.chores,c,busy),albumCard(life,form));
  return `<div class="wl">${parts.join('')}</div>`;
}

/* ---- 🧺 lễ rước dâu + lễ gia tiên ---- */
function riteCard(r,form,busy){
  if(!r)return `<section class="mr-card"><h3>🧺 Lễ rước dâu &amp; lễ gia tiên</h3><p class="mr-hint">Chốt kế hoạch cưới trước, rồi hai bạn cùng làm lễ với hai họ nhé.</p></section>`;
  if(r.state==='none'){
    const trays=r.trays_fixed||Number(form.trays)||5,tp=r.trays_fixed?0:(r.trays.find(x=>x.n===trays)?.price||0),cost=r.fee+tp;
    const pick=r.trays_fixed?`<p>🧺 ${r.trays_fixed} mâm quả (đã có trong kế hoạch ăn hỏi).</p>`
      :`<div class="segmented" role="radiogroup" aria-label="Số mâm quả">${r.trays.map(x=>`<button type="button" role="radio" aria-checked="${x.n===trays}" class="${x.n===trays?'active':''}" data-mr="wl:trays" data-n="${x.n}">${x.n} mâm · ${xu(x.price)}</button>`).join('')}</div>`;
    return `<section class="mr-card mr-accent wl-rite"><h3>🧺 Lễ rước dâu &amp; lễ gia tiên</h3>
      <p>Người bắt đầu là họ đi rước, người kia là họ đón. Sáu bước, mỗi người lần lượt chọn cách làm, hai họ cùng chứng kiến.</p>${pick}
      <p class="mr-hint">${cost?`Chi phí ${xu(cost)}${r.fee?' (gồm lễ gia tiên)':''}, người bắt đầu trả. Hoãn lễ là được hoàn lại.`:'Miễn phí: lễ đã có trong kế hoạch cưới.'} Khách dự tiệc cưới sẽ được MC kể lại.</p>
      ${r.party_live?'<p class="mr-flash warn">Tiệc cưới đang diễn ra. Làm lễ sau tiệc nhé.</p>':''}
      <div class="mr-actions">${btn('🧺 Bắt đầu lễ','rite-start',{cost,trays},'primary',busy||r.party_live)}</div></section>`;
  }
  const rows=r.steps.map((s,i)=>{
    const now=r.state==='on'&&i===r.step;
    if(s.picked)return `<li class="done"><b>${s.emoji} ${esc(s.title)}</b><small>${esc(s.by)}: ${esc(s.picked.text)}</small><i>${esc(s.who)}: ${esc(s.picked.reply)}</i></li>`;
    if(!now)return `<li class="later"><b>${s.emoji} ${esc(s.title)}</b><small>${s.mine?'Phần của bạn':'Phần của '+esc(s.by)}</small></li>`;
    const opts=s.mine?`<div class="wl-opts">${s.options.map(o=>btn(esc(o.text),'rite-step',{rite:r.id,step:i,pick:o.id},'cream wl-opt',busy)).join('')}</div>`:`<p class="mr-hint">Chờ ${esc(s.by)} chọn…</p>`;
    return `<li class="now"><b>${s.emoji} ${esc(s.title)}</b><p class="wl-say"><span>${esc(s.who)}:</span> “${esc(s.line)}”</p>${opts}</li>`;
  }).join('');
  const head=r.state==='done'?`<p class="wl-grade">${esc(r.grade||'')}</p><p class="mr-hint">Họ nhà ${esc(r.lead.name)} sang rước dâu nhà ${esc(r.host.name)} với ${r.trays} mâm quả. Ảnh lễ gia tiên đã vào album.</p>`
    :`<p>Họ nhà <b>${esc(r.lead.name)}</b> sang rước dâu nhà <b>${esc(r.host.name)}</b> · ${r.trays} mâm quả · bước ${Math.min(r.step+1,r.steps.length)}/${r.steps.length}</p>${r.my_turn?'<span class="tag">Đến lượt bạn</span>':''}`;
  return `<section class="mr-card${r.my_turn?' mr-accent':''} wl-rite"><h3>${r.state==='done'?'🕯️ Lễ gia tiên đã xong':'🧺 Lễ rước dâu đang diễn ra'}</h3>${head}${r.state==='done'?`<details class="mr-more"><summary>Xem lại từng bước</summary><ol class="wl-steps">${rows}</ol></details>`:`<ol class="wl-steps">${rows}</ol>`}
    ${r.state==='on'?`<details class="mr-more"><summary>Hoãn lễ</summary><p class="mr-hint">Hoãn thì làm lại từ đầu sau${r.paid?`, ${xu(r.paid)} được hoàn về ví người trả`:''}.</p>${btn('Hoãn lễ','rite-cancel',{rite:r.id},'ghost small',busy)}</details>`:''}</section>`;
}

/* ---- ✈️ đi chơi cùng nhau ---- */
function scene(t){
  const go=t.status==='on';
  return `<div class="wl-scene${go?' go':''}" aria-hidden="true"><span class="wl-dest">${t.dest.emoji}</span><span class="wl-ride">${t.ride.vehicle?t.ride.vehicle.split(' ')[0]:t.ride.emoji}</span><span class="wl-couple">💑</span></div>`;
}
function photoStrip(list){
  if(!list?.length)return '';
  for(const p of list)PHOTOS.set(p.id,p);
  return `<div class="wl-strip">${list.map(p=>`<button type="button" class="wl-tile" data-mr="wl:photo" data-id="${esc(p.id)}" aria-label="${esc(p.head||'Ảnh')}"><img alt="" data-wl-photo="${esc(p.id)}"></button>`).join('')}</div>`;
}
function tripCard(life,form,busy){
  const t=life.trip;
  if(t&&t.status==='proposed'){
    const left=t.pay_by==='split'?t.price-Math.ceil(t.price/2):0;   // the partner's half (the server takes exactly what is left)
    const who=t.pay_by==='fund'?'Quỹ chung đã giữ':t.pay_by==='me'?`${esc(t.proposer)} bao`:`Chia đôi, mỗi người khoảng ${xu(Math.ceil(t.price/2))}`;
    return `<section class="mr-card mr-accent wl-trip">${scene(t)}<h3>✈️ ${t.mine?'Đã rủ':'Lời rủ'} đi ${esc(t.dest.name)}</h3>
      <p>${t.ride.emoji} ${esc(t.ride.name)}${t.ride.vehicle?` · ${esc(t.ride.vehicle)}`:''} · ${t.days} ngày · ${xu(t.price)} (${who})</p>
      ${t.mine?`<p class="mr-hint">Chờ ${esc(t.partner)} đồng ý. Hết hạn lúc ${hhmm(t.expires)}, tiền đã giữ sẽ tự hoàn.</p><div class="mr-actions">${btn('Hủy lời rủ','trip-cancel',{trip:t.id},'ghost',busy)}</div>`
        :`<p class="mr-hint">${left?`Bạn góp ${xu(left)} khi bấm đi.`:'Bạn không phải trả thêm.'} Không đi thì tiền đã giữ được hoàn lại.</p><div class="mr-actions">${btn('✈️ Đi thôi!','trip-accept',{trip:t.id,share:left},'primary',busy)}${btn('Để lần sau','trip-decline',{trip:t.id},'cream',busy)}</div>`}</section>`;
  }
  if(t&&t.status==='on'){
    const dots=Array.from({length:t.days},(_,i)=>`<i class="${i<t.day?'done':i===t.day?'now':''}"></i>`).join('');
    const hist=t.history.map(h=>`<li><b>Ngày ${h.day}: ${h.emoji} ${esc(h.text)}</b><small>${esc(h.event)}</small></li>`).join('');
    const today=t.my_turn&&t.ready?`<p><b>Ngày ${t.day+1}:</b> hôm nay hai bạn đi đâu?</p><div class="wl-opts">${t.options.map(o=>btn(`${o.emoji} ${esc(o.text)}`,'trip-pick',{trip:t.id,day:t.day,pick:o.id},'cream wl-opt',busy)).join('')}</div>`
      :!t.ready?`<p class="mr-hint">Ngày ${t.day+1} bắt đầu lúc ${hhmm(t.opens)}. Nghỉ ngơi chút đã!</p>`:`<p class="mr-hint">Ngày ${t.day+1}: chờ ${esc(t.chooser)} chọn đi đâu…</p>`;
    return `<section class="mr-card mr-accent wl-trip">${scene(t)}<h3>${t.dest.emoji} Đang ở ${esc(t.dest.name)}</h3><p class="mr-hint">${esc(t.line)}</p>
      <div class="wl-dots" aria-label="Ngày ${t.day+1}/${t.days}">${dots}</div>${hist?`<ul class="mr-feed wl-days">${hist}</ul>`:''}${photoStrip(t.photos)}${today}</section>`;
  }
  return planner(life,form,busy)+(life.last?lastTrip(life.last):'');
}
function lastTrip(t){
  return `<section class="mr-card wl-trip"><h3>🏡 Chuyến vừa rồi: ${t.dest.emoji} ${esc(t.dest.name)}</h3><ul class="mr-feed wl-days">${t.history.map(h=>`<li><b>Ngày ${h.day}: ${h.emoji} ${esc(h.text)}</b><small>${esc(h.event)}</small></li>`).join('')}</ul>${photoStrip(t.photos)}</section>`;
}
function rides(d,assets){
  const out=[];
  for(const r of ['ve','thue_bay','thue_thuyen'])if(d.prices[r]!=null)out.push({id:r,price:d.prices[r]});
  for(const v of assets?.vehicles||[]){
    if(v.arrive==='boat'&&!d.sea)continue;if(v.arrive==='heli'&&d.kind==='abroad')continue;
    const fuel=v.arrive==='boat'?d.fuel.boat:d.fuel.plane;if(fuel==null)continue;
    out.push({id:'nha',vehicle:v.id,price:fuel,label:`🔑 ${v.emoji} ${v.name}${v.mine?'':' (của người ấy)'}`});
  }
  return out;
}
function planner(life,form,busy){
  const cat=life.catalog;if(!cat)return '';
  const islands=form.assets?.islands?.length;
  const dests=cat.dests.filter(d=>d.kind!=='island'||islands);
  const d=dests.find(x=>x.id===form.dest)||dests[0];
  const ride=rides(d,form.assets),R=Object.fromEntries(cat.rides.map(r=>[r.id,r]));
  const cur=ride.find(r=>r.id===form.ride&&(r.vehicle||'')===(form.vehicle||''))||ride[0];
  const pay=form.pay_by||'split',half=Math.ceil(cur.price/2);
  const groups=[['vn','Trong nước'],['abroad','Nước ngoài'],['island','Đảo riêng']].map(([k,label])=>{const list=dests.filter(x=>x.kind===k);return list.length?`<p class="wl-group">${label}</p><div class="wl-dests">${list.map(x=>`<button type="button" class="wl-dest-btn${x.id===d.id?' on':''}" data-mr="wl:dest" data-id="${x.id}" aria-pressed="${x.id===d.id}"><span aria-hidden="true">${x.emoji}</span><b>${esc(x.name)}</b><small>${x.days} ngày · từ ${xu(x.prices.ve)}</small></button>`).join('')}</div>`:'';}).join('');
  const rideBtns=ride.map(r=>{const on=r===cur;return `<button type="button" class="wl-ride-btn${on?' on':''}" data-mr="wl:ride" data-id="${r.id}" data-vehicle="${esc(r.vehicle||'')}" aria-pressed="${on}"><b>${esc(r.label||`${R[r.id].emoji} ${R[r.id].name}`)}</b><small>${xu(r.price)}${r.id==='nha'?' tiền xăng':''}</small></button>`;}).join('');
  const payBtns=Object.entries(PAY).map(([k,label])=>`<button type="button" role="radio" aria-checked="${k===pay}" class="${k===pay?'active':''}" data-mr="wl:pay" data-id="${k}">${label}</button>`).join('');
  const payLine=pay==='fund'?`Quỹ chung đang có ${xu(life.fund)}.`:pay==='split'?`Bạn ${xu(half)}, người ấy ${xu(cur.price-half)} khi đồng ý.`:`Bạn trả cả ${xu(cur.price)}.`;
  return `<section class="mr-card wl-plan"><h3>✈️ Đi chơi cùng nhau</h3><p>Chọn nơi, chọn cách đi, rủ người ấy. Mỗi ngày trên chuyến đi một người chọn chỗ chơi, có ảnh đôi vào album chung.</p>
    ${life.today_done?'<p class="mr-flash warn">Hôm nay hai bạn vừa đi chơi rồi. Mai đi tiếp nha!</p>':''}
    ${groups}<p class="wl-group">Cách đi</p><div class="wl-rides">${rideBtns}</div>${form.assets?'':`<button type="button" class="btn ghost small" data-mr="wl:assets"${busy?' disabled':''}>🔑 Dùng máy bay, du thuyền, đảo nhà mình</button>`}
    <p class="wl-group">Ai trả</p><div class="segmented" role="radiogroup" aria-label="Ai trả">${payBtns}</div><p class="mr-hint">${payLine} Tiền được giữ tới khi người ấy đồng ý; không đi thì hoàn lại đúng chỗ đã trả.</p>
    <div class="mr-actions">${btn(`✈️ Rủ đi ${esc(d.name)} · ${xu(cur.price)}`,'trip-propose',{dest:d.id,ride:cur.id,vehicle:cur.vehicle||'',price:cur.price},'primary',busy||life.today_done)}</div></section>`;
}

/* ---- 🏠 sống chung mỗi ngày ---- */
function choresCard(list,c,busy){
  const partner=esc(c?.partner?.name||'người ấy');
  const rows=(list||[]).map(x=>{
    const role=id=>x.roles.find(r=>r.id===id)?.text||'';
    let body;
    if(x.locked)body=`<small>Khi có bé ở nhà, hai bạn cùng chăm bé ở đây.</small>`;
    else if(x.state==='done')body=`<small>✅ Bạn ${esc(role(x.mine?x.role:x.role2).toLowerCase())}, ${partner} ${esc(role(x.mine?x.role2:x.role).toLowerCase())}. Xong rồi!</small>`;
    else if(x.state==='open'&&x.mine)body=`<small>Bạn nhận ${esc(role(x.role).toLowerCase())}, chờ ${partner} vào làm cùng…</small>`;
    else if(x.state==='open')body=`<small>${partner} rủ: “${esc(x.ask)}” và nhận ${esc(role(x.role).toLowerCase())}.</small><div class="wl-roles">${x.roles.filter(r=>r.id!==x.role).map(r=>btn(`Mình ${esc(r.text.toLowerCase())}`,'chore-join',{kind:x.kind,role:r.id},'cream small',busy)).join('')}</div>`;
    else body=`<div class="wl-roles">${x.roles.map(r=>btn(`Mình ${esc(r.text.toLowerCase())}`,'chore-start',{kind:x.kind,role:r.id},'cream small',busy)).join('')}</div>`;
    return `<li class="wl-chore ${x.state}${x.locked?' locked':''}"><b>${x.emoji} ${esc(x.name)}</b>${body}</li>`;
  }).join('');
  return `<section class="mr-card"><h3>🏠 Sống chung hôm nay</h3><p class="mr-hint">Một người rủ và nhận một phần, người kia nhận phần còn lại. Mỗi việc một lần mỗi ngày: thêm điểm hạnh phúc và tinh thần.</p><ul class="wl-chores">${rows}</ul></section>`;
}

/* ---- 📸 album chung ---- */
function albumCard(life,form){
  const open=Array.isArray(form.album);
  const grid=open?(form.album.length?photoStrip(form.album):'<p class="mr-hint">Chưa có tấm nào. Đi chơi hoặc làm lễ là có ảnh nha!</p>')+(form.albumMore?btn('Xem cũ hơn','album-more'):''):'';
  return `<section class="mr-card"><h3>📸 Album của hai bạn</h3><p>${life.album?`${life.album} tấm ảnh đôi từ lễ gia tiên và những chuyến đi.`:'Ảnh lễ gia tiên và ảnh mỗi ngày đi chơi sẽ nằm ở đây.'}</p>
    ${open?grid:btn('📸 Mở album','album',{},'cream',!life.album)}</section>`;
}

/** Paint the photo tiles (./portrait-art.js, loaded only when a photo is on screen). */
export function lifePaint(root){
  const imgs=[...root.querySelectorAll('img[data-wl-photo]')].filter(im=>!im.src);
  if(!imgs.length)return;
  import('./portrait-art.js').then(({photoURL})=>{for(const im of imgs){const p=PHOTOS.get(im.dataset.wlPhoto);if(p)photoURL(p,{width:Number(im.dataset.w)||240}).then(u=>{if(u)im.src=u;});}}).catch(e=>console.warn('wedlife: photos',e));
}

/** The photo tapped, big, at the top of the tab (one at a time). */
function bigView(form){
  const p=form.big&&PHOTOS.get(form.big);if(!p)return '';
  return `<section class="mr-card wl-bigcard"><h3>${esc(p.head||'Ảnh đôi')}</h3><img class="wl-big" alt="${esc(p.sub||'')}" data-wl-photo="${esc(p.id)}" data-w="480"><div class="mr-actions">${btn('Đóng ảnh','photo-close')}</div></section>`;
}

export async function lifeAction(action,data,{env,life,form,post,render,top}){
  if(!action.startsWith('wl:'))return false;
  const op=action.slice(3);
  const api=env.api;
  switch(op){
    case'trays':form.trays=Number(data.n);render();return true;
    case'dest':form.dest=data.id;form.ride='';form.vehicle='';render();return true;
    case'ride':form.ride=data.id;form.vehicle=data.vehicle||'';render();return true;
    case'pay':form.pay_by=data.id;render();return true;
    case'assets':{
      try{const d=await api.json('/api/marriage/wl_assets',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:'{}'});form.assets=d.assets||{islands:[],vehicles:[]};}
      catch{form.assets={islands:[],vehicles:[]};}
      render();return true;}
    case'album':case'album-more':{
      const before=op==='album-more'&&form.album?.length?form.album[form.album.length-1].at:undefined;
      try{const d=await api.json('/api/marriage/wl_album',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(before!=null?{before}:{})});
        form.album=[...(op==='album-more'?form.album||[]:[]),...(d.photos||[])];form.albumMore=Boolean(d.more);}
      catch{form.album=form.album||[];}
      render();return true;}
    case'photo':form.big=data.id;render();top?.();return true;
    case'photo-close':form.big=null;render();return true;
    case'rite-start':{
      const cost=Number(data.cost)||0;let pay='cash';
      if(cost){pay=await confirmPurchase(env,{title:'Bắt đầu lễ rước dâu?',message:`${data.trays} mâm quả và lễ gia tiên: ${xu(cost)}. Hoãn lễ là được hoàn lại.`,label:`Bắt đầu · ${xu(cost)}`,cost,noJoint:true});if(!pay)return true;}
      else if(!await env.confirmAction('Bắt đầu lễ rước dâu?','Bạn là họ đi rước. Hai bạn lần lượt chọn từng bước nhé.','Bắt đầu'))return true;
      await post('wl_rite_start',{trays:Number(data.trays),pay,rid:rid()});return true;}
    case'rite-step':await post('wl_rite_step',{rite:Number(data.rite),step:Number(data.step),pick:data.pick});return true;
    case'rite-cancel':if(await env.confirmAction('Hoãn lễ rước dâu?','Lễ dừng ở đây, hai bạn làm lại từ đầu khi sẵn sàng.','Hoãn lễ'))await post('wl_rite_cancel',{rite:Number(data.rite)});return true;
    case'trip-propose':{
      const price=Number(data.price)||0,payBy=form.pay_by||'split',mine=payBy==='me'?price:payBy==='split'?Math.ceil(price/2):0;
      let pay='cash';
      const d=life?.catalog?.dests?.find(x=>x.id===data.dest),title=`Rủ người ấy đi ${d?.name||''}?`;
      if(mine){pay=await confirmPurchase(env,{title,message:`Giữ ${xu(mine)} của bạn tới khi người ấy đồng ý. Không đi thì hoàn lại.`,label:`Rủ đi · ${xu(mine)}`,cost:mine,noJoint:true});if(!pay)return true;}
      else if(!await env.confirmAction(title,`Giữ ${xu(price)} từ quỹ chung tới khi người ấy đồng ý. Không đi thì hoàn lại vào quỹ.`,'Rủ đi'))return true;
      await post('wl_trip_propose',{dest:data.dest,ride:data.ride,vehicle:data.vehicle||'',pay_by:payBy,pay,rid:rid()});return true;}
    case'trip-accept':{
      const share=Number(data.share)||0;let pay='cash';
      if(share){pay=await confirmPurchase(env,{title:'Lên đường?',message:`Phần của bạn: ${xu(share)}.`,label:`Đi thôi · ${xu(share)}`,cost:share,noJoint:true});if(!pay)return true;}
      await post('wl_trip_answer',{trip:Number(data.trip),answer:'accept',pay,rid:rid()});return true;}
    case'trip-decline':await post('wl_trip_answer',{trip:Number(data.trip),answer:'decline',rid:rid()});return true;
    case'trip-cancel':if(await env.confirmAction('Hủy lời rủ?','Tiền đã giữ được hoàn lại đúng chỗ đã trả.','Hủy lời rủ'))await post('wl_trip_cancel',{trip:Number(data.trip)});return true;
    case'trip-pick':await post('wl_trip_pick',{trip:Number(data.trip),day:Number(data.day),pick:data.pick});form.album=null;return true;
    case'chore-start':await post('wl_chore_start',{kind:data.kind,role:data.role});return true;
    case'chore-join':await post('wl_chore_join',{kind:data.kind,role:data.role});return true;
  }
  return true;
}
