import {escapeHTML as esc} from '../icons.js';
import {confirmPurchase} from './payment.js';

export async function visitCommunity(id,env){
  const place=env.api.content.journey.outings.community?.find(p=>p.id===id);
  if(!place)return true;
  const {visitVenue}=await import('./venue-routing.js');
  await visitVenue(env,id,()=>new Promise(resolve=>{
    const d=document.createElement('dialog');d.className='sheet v4-sheet medium';
    const paint=()=>{
      const state=env.api.state.journey.outings.community,done=state.last[id]===state.day;
      d.innerHTML=`<header class="sheet-head"><h2 class="grow">${esc(place.name)}</h2><button type="button" class="btn ghost small" data-exit>Quay lại phòng</button></header><div class="sheet-body"><p>${esc(place.intro)}</p><p>${place.cost?`${place.cost} xu / buổi`:'Tham gia miễn phí'}</p>${place.choices.map(c=>`<p><button type="button" class="btn primary" data-choice="${esc(c.id)}"${done?' disabled':''}>${esc(c.name)}</button></p>`).join('')}${done?'<p>Đã lưu buổi hôm nay. Bạn vẫn có thể đi dạo trong phòng.</p>':''}</div>`;
    };
    d.addEventListener('close',()=>{d.remove();resolve();},{once:true});
    d.addEventListener('click',async e=>{
      if(e.target.closest('[data-exit]')){d.close();return;}
      const button=e.target.closest('[data-choice]');if(!button||button.disabled)return;
      try{await communityAction({place:id,choice:button.dataset.choice},button,{...env,renderSheet:paint});}
      catch(error){env.toast?.(error.message,true);}
    });
    paint();document.body.append(d);d.showModal();
  }));return true;
}

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
      return `<section class="out-saved"><h3>${p.emoji} ${esc(p.name)}</h3><small>${esc(p.host)} · Đã ghé ${d.visits[p.id]||0} buổi</small><p>${esc(p.intro)}</p><p>${p.cost?`${p.cost} xu / buổi`:'Tham gia miễn phí'}</p><p><button type="button" class="btn primary small" data-action="jrOutVenue" data-place="${p.id}">Vào đi dạo</button></p>${done?'<p>✓ Đã lưu buổi hôm nay. Ngày sống mới có câu chuyện tiếp theo.</p>':''}${p.id==='karaoke'?(kara?'<p><button type="button" class="btn small" data-action="liveKara">🎤 Vào Phòng hát</button></p>':'<p><a href="https://www.youtube.com/results?search_query=karaoke+beat" target="_blank" rel="noopener noreferrer">Mở YouTube để chọn beat ↗</a></p>'):''}</section>`;
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
