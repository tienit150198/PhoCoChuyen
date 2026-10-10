/** Pure auction presentation. Strings from players/API are escaped at this boundary. */
import {escapeHTML as esc} from '../icons.js';
import {paintingSVG,landmarkSVG} from './auction-art.js';
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const TIERS={1:'Phổ thông',2:'Quý hiếm',3:'Huyền thoại'};

export function lotPicker(lots,selected){
  return `<nav class="au-lots" aria-label="Chọn món đấu giá">${lots.map(l=>`<button class="au-pick${l.id===selected?' on':''}" type="button" data-au="lot" data-id="${esc(l.id)}" aria-pressed="${l.id===selected}" aria-label="${esc(l.name)}"><span class="au-mini" aria-hidden="true">${l.kind==='art'?paintingSVG(l.item):esc(l.emoji)}</span><span class="au-lot-name" data-no-translate>${esc(l.name)}</span></button>`).join('')}</nav>`;
}

export function itemArt(l){
  const d=l.data||{},tier=[1,2,3].includes(l.tier)?l.tier:1;
  if(l.kind==='art')return `<figure class="au-art au-painting">${paintingSVG(l.item||l.id)}<figcaption>${esc(d.artist||'')}${d.year?` · ${Number(d.year)}`:''}</figcaption></figure>`;
  if(l.kind==='plate')return `<div class="au-art au-plate au-tier-${tier}" aria-hidden="true"><small>PHỐ MÂY · ĐỘC BẢN</small><span>${esc(l.name)}</span><i>◆ &nbsp; 01 / 01 &nbsp; ◆</i></div>`;
  if(l.kind==='phone')return `<div class="au-art au-phone au-tier-${tier}" aria-hidden="true"><div class="au-handset"><small>PHỐ MÂY</small><span>✦</span><b>${esc(l.name)}</b><i>SIM ĐỘC BẢN · 01/01</i></div></div>`;
  if(l.kind==='land')return `<figure class="au-art au-landscape">${landmarkSVG(l.item||l.id)}<figcaption>${esc(d.where||'')}</figcaption></figure>`;
  return `<div class="au-art au-emblem au-tier-${tier}" aria-hidden="true"><svg viewBox="0 0 260 160"><path d="M55 128Q12 75 60 29M205 128Q248 75 200 29" fill="none" stroke="currentColor" stroke-width="3"/>${[0,1,2,3,4].map(i=>`<ellipse cx="${36+i*2}" cy="${49+i*16}" rx="6" ry="12" transform="rotate(-35 ${36+i*2} ${49+i*16})"/><ellipse cx="${224-i*2}" cy="${49+i*16}" rx="6" ry="12" transform="rotate(35 ${224-i*2} ${49+i*16})"/>`).join('')}<path d="M80 26L130 10L180 26V80Q180 122 130 142Q80 122 80 80Z" fill="none" stroke="currentColor" stroke-width="2"/><path d="M73 129H187L177 149H83Z" fill="currentColor"/></svg><span>${esc(l.emoji||'👑')}</span><small>ĐỘC BẢN · 01/01</small></div>`;
}

export function collectibleDetails(l){
  const d=l.data||{},points=Number(l.collector_points)||0,rarity=l.rarity??(points?l.tier:null);
  return `<p class="au-rarity au-tier-${Number(rarity)||1}"><span>${esc(TIERS[rarity]||'Độc bản')}</span><b>${points?`${fmt(points)} điểm`:'01/01'}</b></p>`
    +`<details class="au-provenance"><summary>Về món đồ</summary>${d.medium?`<b>${esc(d.medium)}</b>`:''}<p>${esc(d.story||'Độc bản của phố, chỉ một chủ nhân.')}</p><small>${points?'Điểm sưu tầm khi nhận món. Giá trả không tăng điểm.':'Số đặt riêng ngoài danh mục chưa tính điểm sưu tầm.'}</small></details>`;
}

export function collectionGallery(own,catalogue){
  const items=new Map((catalogue?.items||[]).map(it=>[it.id,it]));
  const rows=Object.entries(own||{}).map(([id,x])=>{
    const it=items.get(id)||{},l={...it,item:id,kind:x.k,name:x.t,data:it};
    return `<li class="sd-card au-collection-piece">${itemArt(l)}<h3 data-no-translate>${esc(x.t)}</h3>${collectibleDetails(l)}<small>Giá chốt · ${fmt(x.p)} xu</small></li>`;
  });
  return rows.length?`<ul class="au-gallery">${rows.join('')}</ul>`:'<p class="sd-empty">🎁</p><p class="au-note">Món độc bản bạn thắng sẽ ở đây.</p>';
}

export function collectorBoard(data){
  if(!data)return '<p class="au-note" role="status">Đang tải bảng sưu tầm…</p>';
  if(data.error)return '<p class="au-note" role="alert">Chưa tải được bảng sưu tầm.</p><button class="btn" type="button" data-au="topRetry">Thử lại</button>';
  const rows=(data.rows||[]).map(r=>`<li class="au-collector${r.me?' me':''}"><span class="au-position">${['🥇','🥈','🥉'][r.rank-1]||fmt(r.rank)}</span><div><b data-no-translate>${esc(r.name)}</b>${r.me?' <small>· Bạn</small>':''}<small>${fmt(r.items)} món · ${fmt(r.legendary)} huyền thoại</small></div><strong>${fmt(r.score)}<small>điểm</small></strong></li>`).join('');
  const me=data.me;
  const mine=me?`<p class="au-my-rank">${me.rank?`${me.visible?'Bạn':'Nếu hiện tên'} · #${fmt(me.rank)} · ${fmt(me.score)} điểm`:'Nhận độc bản đầu tiên để lên bảng.'}${!me.visible?'<small>Tên bạn đang ẩn. Đổi tại Cài đặt → Dữ liệu.</small>':''}</p>`:'';
  return `<details class="au-provenance"><summary>Cách tính điểm</summary><p>Phổ thông 10 · Quý hiếm 40 · Huyền thoại 120. Chỉ tính đồ đã nhận trong danh mục.</p><p>Bằng điểm: nhiều món hơn, nhiều huyền thoại hơn, rồi ai đạt trước. Giá trả không tăng điểm.</p><p>Quyền ẩn tên dùng chung với Bảng xếp hạng.</p></details>${mine}`
    +(rows?`<ol class="au-collectors" aria-label="Top nhà sưu tầm">${rows}</ol>`:'<p class="sd-empty">💎</p><p class="au-note">Chưa có nhà sưu tầm hiện tên.</p>');
}
