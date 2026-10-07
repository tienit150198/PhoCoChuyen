import {escapeHTML as esc} from '../icons.js';
import {confirmPurchase} from './payment.js';

export function communityView(env){
  const places=env.api.content.journey.outings.community||[],d=env.api.state.journey.outings.community;
  if(!d)return '<p>Đang mở sổ sinh hoạt…</p>';
  const lv=env.live?.(),kara=!!(lv?.flags?.kara&&lv.welcomed);   // 🎤 Phòng hát Mây (v4/karaoke.js) while the live service has it on
  const memories=[...d.memories].reverse().map(m=>{
    const p=places.find(x=>x.id===m.place),c=p?.choices.find(x=>x.id===m.choice);
    if(!c)return '';
    return `<article class="out-saved"><small>Ngày sống ${m.day} · ${esc(p.name)}</small><h4>${esc(c.keepsake)}</h4><p>${esc(c.story[(m.visit-1)%c.story.length])}</p></article>`;
  }).join('');
  return `<p>Ghé hiệu sách, tham gia câu lạc bộ cùng các nhân vật trong phố hoặc dành một buổi cho gia đình. Mỗi nơi lưu một buổi mỗi ngày sống; chỉ thanh toán khi bạn xác nhận. Kỷ niệm gần nhất được giữ ở cuối trang.</p>
    <div class="out-grid">${places.map(p=>{
      const done=d.last[p.id]===d.day;
      return `<section class="out-saved"><h3>${p.emoji} ${esc(p.name)}</h3><small>${esc(p.host)} · Đã ghé ${d.visits[p.id]||0} buổi</small><p>${esc(p.intro)}</p><p>${p.cost?`${p.cost} xu / buổi`:'Tham gia miễn phí'}</p><div class="out-options">${p.choices.map(c=>`<button type="button" class="btn ghost small" data-action="jrOutCommunity" data-place="${p.id}" data-choice="${c.id}"${done?' disabled':''}>${esc(c.name)}</button>`).join('')}</div>${done?'<p>✓ Đã lưu buổi hôm nay. Ngày sống mới có câu chuyện tiếp theo.</p>':''}${p.id==='karaoke'?(kara?'<p><button type="button" class="btn small" data-action="liveKara">🎤 Vào Phòng hát</button></p>':'<p><a href="https://www.youtube.com/results?search_query=karaoke+beat" target="_blank" rel="noopener noreferrer">Mở YouTube để chọn beat ↗</a></p>'):''}</section>`;
    }).join('')}</div><h3 class="out-step">Sổ kỷ niệm trong phố</h3>${memories?`<div class="out-grid">${memories}</div>`:'<p>Chưa có kỷ niệm. Chọn một hoạt động ở trên để bắt đầu.</p>'}`;
}

export async function communityAction(data,el,env){
  const p=env.api.content.journey.outings.community?.find(x=>x.id===data.place),c=p?.choices.find(x=>x.id===data.choice);
  if(!c)return true;
  const how=p.cost?await confirmPurchase(env,{title:p.name,message:`${c.name}. Tổng ${p.cost} xu; lưu một buổi trong ngày sống này.`,label:'Tham gia',cost:p.cost}):'cash';
  if(!how)return true;
  el.disabled=true;
  try{if(await env.cmd('jr_out_community',{place:p.id,choice:c.id,pay:how}))env.renderSheet();}
  finally{if(el.isConnected){const d=env.api.state.journey.outings.community;el.disabled=d?.last[p.id]===d?.day;}}
  return true;
}
