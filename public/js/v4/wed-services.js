/** 💒 Dịch vụ cưới từ người chơi (game/wed_services.py holds every rule, price and grade; Phố dịch vụ holds the money).
 * Two tabs, its own dialog:
 *   💍 Cưới của bạn  the couple: who serves the wedding (the team), the orders of both spouses, then each service
 *                   (Tiệc · Hoa · Váy & vest · Trang điểm) with the players who offer it in Phố dịch vụ: pick one, choose
 *                   the brief (thực đơn, màu hoa, mẫu váy…), the price (×3 NPC, or 🤝 an offer) → the money is held.
 *                   📸 Ảnh cưới opens a photographer's own order sheet (v4/portrait.js, the 'doi' package).
 *   🧰 Đơn cưới     the provider (their career's entry): turn the services on, take an order, then do the job step by
 *                   step (the brief, craft steps, three oái ăm demands, the last check), then hand it over (paid at once).
 * GET /api/wedsvc/couple|work · POST /api/wedsvc/hire|step|deliver|sell · POST /api/svc/take|decline|cancel.
 * Opened by app.js handleAction('wedServices', {tab}). Styles: /css/spend.css (sd-*), /css/service-market.css, /css/wed-services.css. */
import {escapeHTML as esc,icon} from '../icons.js';
import {stylesheet} from '../lazy.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const STATUS={talk:'🤝 Đang trả giá',held:'💰 Đã giữ tiền · chờ nhận',working:'🛠️ Đang làm',delivered:'✅ Đã giao',ready:'✅ Đã giao',done:'✅ Đã giao',
  refund:'↩️ Đang hoàn tiền',refunded:'↩️ Đã hoàn tiền',declined:'✕ Bị từ chối',cancelled:'Đã hủy',expired:'⌛ Hết hạn'};
const TABS=[['couple','💍','Cưới của bạn'],['work','🧰','Đơn cưới']];
const S={dlg:null,env:null,tab:'couple',couple:null,work:null,busy:false,loading:false,flash:null,pick:null,form:{},open:{},arm:'',seq:0};
const api=()=>S.env.api;
const wallet=()=>Math.max(0,Number(api().state?.journey?.wallet)||0);
const stars=n=>n?`<span class="ws-stars" aria-label="${n} sao">${'★'.repeat(n)}${'☆'.repeat(5-n)}</span>`:'';
const btn=(label,op,data={},cls='ghost',extra='')=>`<button type="button" class="btn ${cls}" data-ws="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${S.busy?' disabled':''}${extra}>${label}</button>`;
const WORK_CAREERS=['banquet','florist','clothing','salon'];
/** A career as the directory and the street name it ("Nhà hàng tiệc", not the service's "Tiệc cưới"). */
const careerName=(c,fallback)=>api().content?.catalogue?.find(x=>x.id===c)?.name||fallback||c;

/** app.js handleAction('wedServices', data): data.tab 'couple' | 'work'. */
export async function openWedServices(env,data={}){
  S.env=env;
  await Promise.all([stylesheet('/css/spend.css'),stylesheet('/css/service-market.css'),stylesheet('/css/wed-services.css')]);
  if(!S.dlg){
    const d=document.createElement('dialog');
    d.className='sheet v4-sheet medium sd-sheet svc-sheet ws-sheet';d.setAttribute('aria-labelledby','ws-title');
    d.innerHTML='<div class="sd-root"></div>';document.body.append(d);S.dlg=d;
    d.addEventListener('click',e=>{if(e.target===d){d.close();return;}const el=e.target.closest('[data-ws]');if(!el||el.disabled)return;e.preventDefault();
      click(el.dataset.ws,el.dataset).catch(err=>{console.warn('💒',err);S.flash={kind:'bad',text:err.message||'Chưa làm được. Thử lại nhé.'};render();});});
    d.addEventListener('input',input);d.addEventListener('change',input);
    d.addEventListener('close',()=>{S.seq++;});
  }
  const cur=api().state?.current;
  S.tab=data.tab||(WORK_CAREERS.includes(cur)&&!api().state?.marriage?.spouse?'work':S.tab||'couple');
  S.flash=null;S.pick=null;
  if(!S.dlg.open){S.dlg.showModal();S.dlg.scrollTop=0;}
  render();await load();
}

async function load(quiet=false){
  const seq=++S.seq;if(!quiet){S.loading=true;render();}
  try{
    const v=await api().json('/api/wedsvc/'+S.tab);
    if(seq!==S.seq)return;
    S[S.tab]=v;
  }catch(e){if(seq===S.seq)S.flash={kind:'bad',text:e.message||'Chưa tải được. Thử lại nhé.'};}
  finally{if(seq===S.seq){S.loading=false;render();}}
}

async function post(route,body,after){
  if(S.busy)return null;S.busy=true;S.flash=null;render();
  try{
    const r=await api().post(route,body);
    S.flash=r?.message?{kind:'good',text:r.message}:null;
    api().refresh?.().catch(()=>{});
    if(after)await after(r);
    return r;
  }catch(e){S.flash={kind:'bad',text:e.message||'Chưa gửi được. Thử lại nhé.'};return null;}
  finally{S.busy=false;render();}
}

function input(e){
  const t=e.target,f=t.dataset.wsf;if(!f||!S.pick)return;
  const x=S.form;
  if(f==='note')x.note=t.value.slice(0,120);
  else if(f==='price'){x.price=t.value.replace(/[^\d]/g,'');renderBar();}
  else if(f==='qty'){x.qty=Math.max(1,Math.min(S.pick.svc.qty_max,Number(t.value)||1));if(e.type==='change')render();else renderBar();}
}

async function click(op,d){
  if(op==='close'){S.dlg.close();return;}
  if(op==='tab'){S.tab=d.tab;S.pick=null;S.flash=null;render();await load();return;}
  if(op==='retry'){await load();return;}
  if(op==='pick'){
    const svc=S.couple.services.find(s=>s.key===d.svc),prov=svc?.providers.find(p=>p.pid===d.pid);if(!svc||!prov)return;
    S.pick={svc,prov};
    const brief={};for(const f of svc.brief)brief[f.field]=f.options[0].id;
    S.form={brief,qty:svc.key==='tiec'?Math.max(1,Math.min(svc.qty_max,S.couple.tables||10)):1,note:'',price:'',rid:null,fp:null};
    if(prov.mode==='nego')S.form.price=String(Math.min(prov.hi,Math.max(prov.lo,(prov.base||prov.lo)*3))*S.form.qty);
    render();S.dlg.scrollTop=0;return;
  }
  if(op==='unpick'){S.pick=null;render();return;}
  if(op==='brief'){S.form.brief[d.field]=d.id;render();return;}
  if(op==='qtyn'){const q=Math.max(1,Math.min(S.pick.svc.qty_max,(Number(S.form.qty)||1)+Number(d.n)));
    if(S.pick.prov.mode==='nego'&&S.form.price){const per=Math.round(Number(S.form.price)/Math.max(1,S.form.qty));S.form.price=String(per*q);}
    S.form.qty=q;render();return;}
  if(op==='hire'){await hire();return;}
  if(op==='photo'){S.dlg.close();S.env.act('photoStudio',{tab:'order',place:d.place});return;}
  if(op==='market'){S.dlg.close();S.env.act('svcMarket',d.tab?{tab:d.tab}:{});return;}
  if(op==='marriage'){S.dlg.close();S.env.act('marriage',{});return;}
  if(op==='sell'){const m=S.work?.mine?.find(x=>x.key===d.svc);if(!m)return;await post('/api/wedsvc/sell',{svc:m.key,on:!m.on},r=>{if(r?.work)S.work=r.work;});return;}
  if(op==='svc'){   // take · decline · cancel (Phố dịch vụ's own steps; a second tap within 4 s confirms a decline / cancel)
    if(d.do!=='take'&&S.arm!==d.do+d.id){S.arm=d.do+d.id;setTimeout(()=>{if(S.arm===d.do+d.id){S.arm='';render();}},4000);render();return;}
    S.arm='';await post('/api/svc/'+d.do,{order:d.id},()=>load(true));return;}
  if(op==='open'){S.open[d.id]=!S.open[d.id];render();return;}
  if(op==='step'){await post('/api/wedsvc/step',{order:d.id,at:Number(d.at),pick:d.pick},r=>{S.flash=null;const o=S.work?.orders?.find(x=>x.id===d.id);if(o&&r?.job)o.job=r.job;});return;}   // the reply shows in the job itself
  if(op==='deliver'){await post('/api/wedsvc/deliver',{order:d.id},()=>load(true));return;}
}

function priceOf(){
  const p=S.pick?.prov,q=Math.max(1,Number(S.form.qty)||1);if(!p)return 0;
  return p.mode==='nego'?Number(S.form.price)||0:p.price*q;
}
async function hire(){
  const {svc,prov}=S.pick,x=S.form,price=priceOf(),nego=prov.mode==='nego';
  const body={svc:svc.key,pid:prov.pid,qty:Math.max(1,Number(x.qty)||1),brief:{...x.brief}};
  if(x.note)body.note=x.note;
  if(nego)body.price=price;else body.expected_price=price;
  const fp=JSON.stringify(body);if(x.fp!==fp){x.fp=fp;x.rid=rid();}
  body.rid=x.rid;
  const r=await post('/api/wedsvc/hire',body);
  if(r){S.pick=null;S.form={};await load(true);S.dlg.scrollTop=0;}
}

/* ---------------------------------------------------------------- views */
function render(){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.sd-root'),top=S.dlg.scrollTop,active=document.activeElement,fid=active?.dataset?.wsf;
  root.innerHTML=page();
  S.dlg.scrollTop=top;
  if(fid){const el=root.querySelector(`[data-wsf="${fid}"]`);if(el){el.focus();try{const n=el.value.length;el.setSelectionRange?.(n,n);}catch{/* number inputs */}}}
  S.dlg.setAttribute('aria-busy',String(!!(S.busy||S.loading)));
}
function renderBar(){const bar=S.dlg?.querySelector('.ws-bar');if(bar)bar.outerHTML=barView();}
function page(){
  const t=TABS.find(x=>x[0]===S.tab)||TABS[0],alerts=Number(api().wedsvcAlerts)||0;
  const head=`<div class="svc-stick"><header class="sheet-head sd-head"><span class="sd-logo" aria-hidden="true">💒</span><div class="grow"><h2 id="ws-title">Dịch vụ cưới</h2><small class="svc-sub">${esc(t[2])}</small></div>
    <span class="sd-wallet" title="Ví">👛 ${fmt(wallet())}</span><button class="icon-btn" type="button" data-ws="close" aria-label="Đóng">${icon('x',21)}</button></header>
    <nav class="sd-tabs" role="tablist" aria-label="Dịch vụ cưới">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${t[0]===id}" class="${t[0]===id?'on':''}" data-ws="tab" data-tab="${id}">${e} <span>${esc(l)}</span>${id==='work'&&alerts?`<em class="badge">${alerts}</em>`:''}</button>`).join('')}</nav></div>`;
  const body=S.tab==='work'?workView():S.pick?hireView():coupleView();
  return head+`<div class="sheet-body sd-body ws-body">${body}</div>`+barView();
}
function barView(){
  const flash=`<p class="sd-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  let main='';
  if(S.tab==='couple'&&S.pick){
    const p=S.pick.prov,price=priceOf(),short=price>wallet(),nego=p.mode==='nego',q=Math.max(1,Number(S.form.qty)||1);
    const lo=p.lo*q,hi=p.hi*q,bad=nego&&(price<lo||price>hi);
    main=`${btn('‹','unpick',{},'ghost',' aria-label="Quay lại"')}${btn(nego?`🤝 Gửi giá ${fmt(price)} xu`:`💒 Thuê · giữ ${fmt(price)} xu`,'hire',{},'primary sd-main',bad||!price?' disabled':'')}`;
    if(short&&!nego)main+=`<small class="ws-short">Ví còn ${fmt(wallet())} xu; thiếu thì lấy từ tài khoản ngân hàng.</small>`;
  }
  return `<div class="sd-bar svc-bar ws-bar">${flash}${main}</div>`;
}
const wait=()=>S.loading?'<div class="mnl-skel" role="status" aria-busy="true"><i></i><i></i><i></i></div>':`<p class="sd-empty">💒</p>${btn('Thử lại','retry',{},'ghost full')}`;

function teamView(list,title='Đội ngũ người chơi'){
  if(!list?.length)return '';
  return `<section class="sd-card ws-team"><h3>💒 ${esc(title)}</h3><ul class="ws-credits">${list.map(x=>`<li class="${x.state}"><span class="ws-ico" aria-hidden="true">${esc(x.icon)}</span>
    <div class="grow"><b>${esc(x.line)}</b>${x.detail?`<small>${esc(x.detail)}</small>`:''}</div><span class="ws-state">${x.state==='done'?(stars(x.stars)||'✅'):'⏳ Đang chuẩn bị'}</span></li>`).join('')}</ul></section>`;
}

function coupleView(){
  const v=S.couple;if(!v)return wait();
  if(v.why&&!v.status)return `<section class="sd-card svc-empty ws-why"><p class="tp-big">💍</p><p>${esc(v.why)}</p>${btn('Mở Hôn nhân','marriage',{},'primary')}</section>`;
  const wed=v.status==='married'&&v.why&&!v.off;   // married, the wedding (or its party) already behind them
  const head=wed?`<section class="sd-card ws-head ws-wed"><h3>💍 Bạn & ${esc(v.partner)}</h3><p>${v.why.includes('🎉')?'':'🎉 '}${esc(v.why)}</p>
    <p class="svc-note">${v.orders?.length||v.credits?.length?'Đơn và đội ngũ cưới của hai bạn ở dưới đây.':'Dịch vụ cưới dành cho các cặp sắp cưới.'}</p></section>`
    :`<section class="sd-card ws-head"><h3>💍 Bạn & ${esc(v.partner)}</h3><p>${v.when?esc(v.when):'Chưa chốt ngày giờ'}${v.tables?` · ${v.tables} bàn`:''}</p>
    <p class="svc-note">Thuê bạn bè làm nghề tiệc, hoa, váy cưới, trang điểm, chụp ảnh. Giá người chơi mặc định ×3 giá NPC, người bán chọn ×1–×10 hoặc thương lượng. Tiền được giữ tới khi họ giao việc: họ nhận 95 %, 5 % là phí. Không thuê ai thì đám cưới vẫn như kế hoạch với NPC.</p>
    ${v.why?`<p class="sd-flash bad">${esc(v.why)}</p>`:''}</section>`;
  const orders=v.orders?.length?`<section class="sd-card"><h3>🧾 Đơn của hai bạn</h3><ul class="ws-orders">${v.orders.map(o=>`<li><span class="ws-ico" aria-hidden="true">${esc(o.icon)}</span><div class="grow">
      <b>${esc(o.label)} · ${esc(o.who)}</b><small>${esc(STATUS[o.status]||o.status)}${o.status==='working'?` · ${o.progress}/${o.total} bước`:''} · ${fmt(o.price)} xu${o.mine?'':' · người ấy đặt'}</small>${o.detail?`<small>${esc(o.detail)}</small>`:''}</div>
      ${stars(o.stars)}${o.mine&&o.status==='held'?btn(S.arm==='cancel'+o.id?'Chắc chưa?':'Hủy','svc',{do:'cancel',id:o.id},'ghost small'):''}</li>`).join('')}</ul>
      <p class="svc-note">Đánh giá, báo cáo, trả giá: ở <button type="button" class="ws-link" data-ws="market" data-tab="inbox">🛎️ Phố dịch vụ</button>.</p></section>`:'';
  if(wed)return head+teamView(v.credits)+orders;
  const svc=v.services.map(s=>{
    const list=s.providers.length?`<ul class="ws-providers">${s.providers.map(p=>`<li><button type="button" class="svc-card" data-ws="pick" data-svc="${esc(s.key)}" data-pid="${esc(p.pid)}"${v.why?' disabled':''}>
        <div class="grow"><b class="svc-name">${esc(p.who?.name||'')}${p.online?' <i class="svc-on">● online</i>':''}</b><span class="svc-meta">${p.rep?.n?`⭐ ${String(p.rep.avg).replace('.',',')} (${fmt(p.rep.n)})`:'⭐ Chưa có đánh giá'} · ${fmt(p.rep?.deals||0)} đơn</span></div>
        <span class="svc-right">${p.mode==='nego'?`<span class="svc-price nego">🤝 <small>từ</small> <b>${fmt(p.lo)}</b></span>`:`<span class="svc-price"><b>${fmt(p.price)}</b> <small>xu/${esc(s.unit)}</small></span>`}</span></button></li>`).join('')}</ul>`
      :`<p class="svc-note ws-none">Chưa có ai mở dịch vụ này. Rủ bạn bè làm nghề “${esc(careerName(s.career,s.short))}” bật nó trong 🧰 Đơn cưới nhé.</p>`;
    return `<section class="sd-card ws-svc"><div class="ws-svc-head"><span class="ws-big" aria-hidden="true">${esc(s.icon)}</span><div class="grow"><h3>${esc(s.name)}</h3><small>${esc(s.desc)}</small>
      <small class="ws-npc">Giá NPC ${fmt(s.npc)} xu/${esc(s.unit)} · người chơi ×3 = ${fmt(s.npc*3)} xu</small></div></div>${list}</section>`;
  }).join('');
  const ph=v.photographers||[];
  const photo=`<section class="sd-card ws-svc"><div class="ws-svc-head"><span class="ws-big" aria-hidden="true">📸</span><div class="grow"><h3>Ảnh cưới</h3><small>Gói “Ảnh đôi · cưới” ở tiệm ảnh của người chơi: cổng hoa cưới, cả hai cùng lên hình.</small></div></div>
    ${ph.length?`<ul class="ws-providers">${ph.map(p=>`<li><button type="button" class="svc-card" data-ws="photo" data-place="${esc(p.place)}"><div class="grow"><b class="svc-name">${esc(p.name)}</b><span class="svc-meta">${p.done?`⭐ ${String(p.stars).replace('.',',')} · ${fmt(p.done)} ảnh đã giao`:'Tiệm mới'}</span></div>
      <span class="svc-right"><span class="svc-price"><b>${fmt(p.price)}</b> <small>xu</small></span></span></button></li>`).join('')}</ul>`:'<p class="svc-note ws-none">Chưa có tiệm ảnh nào đang mở.</p>'}</section>`;
  return head+teamView(v.credits)+orders+svc+photo;
}

function hireView(){
  const {svc,prov}=S.pick,x=S.form,q=Math.max(1,Number(x.qty)||1),nego=prov.mode==='nego';
  const fields=svc.brief.map(f=>`<fieldset class="ws-field"><legend>${esc(f.label)}</legend><div class="sd-chips">${f.options.map(o=>`<button type="button" class="sd-chip${x.brief[f.field]===o.id?' on':''}" aria-pressed="${x.brief[f.field]===o.id}" data-ws="brief" data-field="${esc(f.field)}" data-id="${esc(o.id)}">${esc(o.emoji)} ${esc(o.name)}</button>`).join('')}</div></fieldset>`).join('');
  const qty=svc.qty_max>1?`<fieldset class="ws-field"><legend>Số ${esc(svc.unit)}</legend><div class="ws-qty">${btn('−','qtyn',{n:-1},'ghost',' aria-label="Bớt một"')}<input class="input" type="number" inputmode="numeric" min="1" max="${svc.qty_max}" value="${q}" data-wsf="qty" aria-label="Số ${esc(svc.unit)}">${btn('+','qtyn',{n:1},'ghost',' aria-label="Thêm một"')}<small>tối đa ${svc.qty_max}</small></div></fieldset>`:'';
  const price=nego?`<label class="field ws-field" for="ws-price">🤝 Giá bạn trả (xu) <small>từ ${fmt(prov.lo*q)} đến ${fmt(prov.hi*q)}</small><input class="input" id="ws-price" inputmode="numeric" data-wsf="price" value="${esc(x.price)}"></label>
      <p class="svc-note">Người bán đồng ý, trả giá lại hoặc từ chối (tối đa ${S.couple.rules?.max_rounds||6} lượt). Tiền chỉ giữ khi hai bên chốt.</p>`
    :`<p class="ws-sum">${fmt(prov.price)} xu × ${q} ${esc(svc.unit)} = <b>${fmt(prov.price*q)} xu</b> <i class="svc-mult">×${prov.mult}</i></p>`;
  return `<section class="sd-card ws-hire"><div class="ws-svc-head"><span class="ws-big" aria-hidden="true">${esc(svc.icon)}</span><div class="grow"><h3>${esc(svc.name)}</h3><small>do <b>${esc(prov.who?.name||'')}</b> làm · ${prov.rep?.n?`⭐ ${String(prov.rep.avg).replace('.',',')}`:'chưa có đánh giá'}</small></div></div>
    ${fields}${qty}<label class="field ws-field" for="ws-note">Dặn thêm (không bắt buộc)<input class="input" id="ws-note" maxlength="120" data-wsf="note" value="${esc(x.note||'')}" placeholder="Ví dụ: cô dâu thích tông pastel, nhà trai đông người…"></label>
    ${price}<p class="svc-note">Người làm có ${S.couple.rules?.hold_hours||24} giờ để nhận đơn, 72 giờ để giao; không kịp thì tiền tự hoàn về ví. Họ sẽ gặp vài chuyện oái ăm, làm khéo thì đám cưới vui hơn.</p></section>`;
}

/* ---------------------------------------------------------------- 🧰 the provider */
function workView(){
  const v=S.work;if(!v)return wait();
  const mine=v.mine.length?`<section class="sd-card ws-mine"><h3>🧰 Dịch vụ cưới của bạn</h3><ul class="ws-orders">${v.mine.map(m=>`<li><span class="ws-ico" aria-hidden="true">${esc(m.icon)}</span><div class="grow"><b>${esc(m.name)}</b>
      <small>${m.mode==='nego'?'🤝 Thương lượng':`${fmt(m.price)} xu/${esc(m.unit)} · ×${m.mult}`} · NPC ${fmt(m.npc)} xu</small>${m.can?'':'<small class="svc-off">Cần làm nghề này mới nhận được</small>'}</div>
      <button type="button" class="ws-switch${m.on?' on':''}" role="switch" aria-checked="${m.on}" aria-label="${esc(m.short)}: ${m.on?'đang nhận đơn':'đang tắt'}" data-ws="sell" data-svc="${esc(m.key)}"${S.busy||(!m.can&&!m.on)?' disabled':''}><i aria-hidden="true"></i></button></li>`).join('')}</ul>
      <p class="svc-note">Đổi hệ số giá, thương lượng: <button type="button" class="ws-link" data-ws="market" data-tab="mine">🛎️ Phố dịch vụ › Dịch vụ của tôi</button>.</p></section>`
    :`<section class="sd-card svc-empty"><p class="tp-big">🧰</p><p>Làm một trong các nghề này để nhận đơn cưới của người chơi:</p><ul class="ws-careers">${v.careers.map(c=>`<li><span aria-hidden="true">${esc(c.icon)}</span> <span>${esc(careerName(c.career,c.short))}</span></li>`).join('')}</ul></section>`;
  const orders=v.orders.length?v.orders.map(orderCard).join(''):`<section class="sd-card svc-empty ws-none"><p class="tp-big">💒</p><p>Chưa có đơn cưới nào. Bật dịch vụ ở trên, cô dâu chú rể sẽ tìm thấy bạn.</p></section>`;
  return (v.why?`<p class="sd-flash bad">${esc(v.why)}</p>`:'')+mine+orders;
}
function orderCard(o){
  const head=`<div class="ws-svc-head"><span class="ws-big" aria-hidden="true">${esc(o.icon)}</span><div class="grow"><h3>${esc(o.label)} · ${esc(o.couple||o.who)}</h3>
    <small>${esc(STATUS[o.status]||o.status)} · ${fmt(o.price)} xu (bạn nhận ${fmt(o.price-o.fee)})${o.when?` · ${esc(o.when)}`:''}</small>${o.note?`<small class="ws-note">✏️ ${esc(o.note)}</small>`:''}</div></div>`;
  let body='';
  if(o.status==='held')body=`<div class="mr-actions ws-acts">${btn('✅ Nhận đơn','svc',{do:'take',id:o.id},'primary')}${btn(S.arm==='decline'+o.id?'Chắc chưa? Bấm lần nữa':'Từ chối','svc',{do:'decline',id:o.id},'ghost')}</div>`;
  else if(o.status==='working')body=jobView(o);
  else if(o.result)body=`<p class="ws-result">${esc(o.result.line||'')} ${stars(o.result.stars)}${o.result.detail?`<small>${esc(o.result.detail)}</small>`:''}</p>`;
  return `<section class="sd-card ws-order ${esc(o.status)}">${head}${body}</section>`;
}
function jobView(o){
  const j=o.job;
  if(!j)return `<p class="svc-note">⏳</p>`;
  const brief=`<ul class="ws-brief">${j.brief.map(b=>`<li><small>${esc(b.label)}</small><b>${esc(b.value)}</b></li>`).join('')}</ul>`;
  const bar=`<div class="ws-progress" role="progressbar" aria-valuemin="0" aria-valuemax="${j.total}" aria-valuenow="${j.steps.length}" aria-label="Tiến độ"><i style="width:${Math.round(j.steps.length/j.total*100)}%"></i></div><small class="ws-count">${j.steps.length}/${j.total} bước</small>`;
  const done=j.steps.length?`<details class="ws-done"${S.open[o.id]?' open':''}><summary data-ws="open" data-id="${esc(o.id)}">Đã làm ${j.steps.length} bước</summary><ol>${j.steps.map(s=>`<li class="p${s.pts}"><small>${esc(s.name)} · <b>${esc(s.mark)}</b></small><p>${esc(s.q)}</p><p>➜ ${esc(s.pick)}</p>${s.reply?`<p class="ws-reply">${esc(s.reply)}</p>`:''}</li>`).join('')}</ol></details>`:'';
  const last=j.steps[j.steps.length-1];
  const lastLine=last?`<p class="ws-last p${last.pts}"><b>${esc(last.mark)}</b> ${esc(last.reply)}</p>`:'';
  let next='';
  if(j.next){
    const n=j.next;
    next=`<div class="ws-step ${n.k==='d'?'odd':''}"><small class="ws-kind">${n.k==='d'?'😵 ':''}${esc(n.name)}</small><p class="ws-q">${esc(n.q)}</p><div class="ws-opts">${n.options.map(x=>btn(esc(x.text),'step',{id:o.id,at:n.i,pick:x.id},'ws-opt')).join('')}</div></div>`;
  }else{
    next=`<div class="ws-finish"><p>Xong hết các bước: <b>${j.score}/${j.max} điểm</b> ${stars(j.stars)}</p>${btn('💒 Giao cho cô dâu chú rể','deliver',{id:o.id},'primary')}</div>`;
  }
  return `<div class="ws-job">${brief}${bar}${lastLine}${next}${done}</div>`;
}
