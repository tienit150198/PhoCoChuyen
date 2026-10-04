import {escapeHTML as esc} from '../icons.js';
import {confirmPurchase} from './payment.js';

const btn=(label,action,data={},disabled=false)=>`<button type="button" class="btn cream small" data-action="${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${disabled?' disabled':''}>${label}</button>`;
const labels={food:'No bụng',clean:'Sạch sẽ',joy:'Vui vẻ'};
function portrait(m,v){
  const color=v.outfits.find(x=>x.id===m.outfit)?.color||'#efc78d';
  return `<svg viewBox="0 0 160 125" width="160" height="125" role="img" aria-label="${esc(m.name)} · ${esc(m.stage)}"><ellipse cx="80" cy="112" rx="59" ry="9" fill="#dbcbb5"/><rect x="18" y="14" width="124" height="96" rx="28" fill="#fff4de"/><circle cx="118" cy="35" r="13" fill="#f4d277"/>${m.kind==='child'?`<path d="M47 112V84Q80 63 113 84V112Z" fill="${color}"/><circle cx="80" cy="54" r="28" fill="#edbb94"/><path d="M56 42Q59 17 88 26Q108 26 107 44Q90 31 80 37Q64 29 56 42Z" fill="#604738"/><circle cx="71" cy="55" r="2.5"/><circle cx="90" cy="55" r="2.5"/><path d="M73 66Q81 72 88 66" fill="none" stroke="#9b574d" stroke-width="2"/>${m.outfit==='yem'?'<path d="M61 79V99H99V79" fill="none" stroke="#fff" stroke-width="7"/>':m.outfit==='flower'?'<text x="67" y="103" font-size="26">🌸</text>':''}`:`<text x="39" y="96" font-size="78">${m.emoji}</text>`}</svg>`;
}
export function householdView(env){
  const v=env.api.state.journey.household;
  if(!v)return '<p>Góc gia đình chỉ có trong hành trình.</p>';
  const members=v.members.map(m=>`<section class="jr-card"><div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">${portrait(m,v)}<div><h3>${esc(m.name)}</h3><p>${esc(m.stage)} · Gắn bó ${m.bond}/100</p><p>${m.care_days} ngày chăm sóc${m.next?` · Mốc tiếp theo: ${m.next} ngày`:''}</p></div></div><div style="display:flex;gap:16px;flex-wrap:wrap">${Object.entries(m.needs).map(([k,n])=>`<label>${labels[k]} ${n}/100<br><meter min="0" max="100" value="${n}">${n}</meter></label>`).join('')}</div><div class="jr-actions" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px">${m.acts.map(a=>btn(`${a.emoji} ${esc(a.name)}${a.cost?` · ${a.cost} xu`:''}${a.done?' ✓':''}`,'jrHhCare',{member:m.id,act:a.id},a.done)).join('')}</div><p class="muted">Mỗi ngày chăm một lần cho từng mục: ăn, vệ sinh, chơi hoặc đọc truyện. Ngày mới tính khi bạn khép ca làm việc.</p>${m.id==='child'?`<h4>Đồ của bé</h4><div style="display:flex;gap:8px;flex-wrap:wrap">${v.outfits.map(o=>btn(`${esc(o.name)}${m.outfit===o.id?' ✓':m.owned.includes(o.id)?'':` · ${o.cost} xu`}`,'jrHhStyle',{member:m.id,item:o.id},m.outfit===o.id)).join('')}</div>`:''}<form data-jr-form="hhName" data-member="${m.id}" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px"><label>Tên <input name="name" maxlength="24" required value="${esc(m.name)}"></label><button class="btn ghost small" type="submit">Đổi tên</button></form></section>`).join('');
  const choices=v.adopt.filter(x=>!v.members.some(m=>m.id===(x.id==='child'?'child':'pet')));
  return `<div class="jr-home"><header class="sheet-head"><div class="grow"><h2>🏡 Góc gia đình</h2><p>Một góc nhỏ để trở về cùng nhau</p></div>${btn('Quay lại','jrView',{view:'home'})}</header><section class="jr-card"><p>Gia đình của nhân vật bạn: tối đa một em bé và một mèo hoặc cún. Tự chọn đón về, đặt tên và chăm mỗi ngày sống. Các khoản mua chỉ trừ khi bạn xác nhận; không tự thu phí khi vắng mặt.</p><p>Em bé lớn lên sau 5 và 20 ngày được chăm sóc. Góc này lưu riêng theo nhân vật.</p></section>${members}${choices.length?`<section class="jr-card"><h3>Đón thành viên mới</h3>${v.locked?'<p>Mở từ ngày sống 10.</p>':`<form data-jr-form="hhAdopt"><p><label>Thành viên <select name="kind">${choices.map(x=>`<option value="${x.id}">${x.emoji} ${esc(x.name)}${x.cost?` · đồ dùng ${x.cost} xu`:' · nhận nuôi miễn phí'}</option>`).join('')}</select></label></p><p><label>Tên gọi <input name="name" maxlength="24" required placeholder="Tên bạn muốn gọi"></label></p><button class="btn primary" type="submit">Đón về nhà</button></form>`}</section>`:''}<section class="jr-card">${btn('💇 Đi làm đẹp · 🎨 DIY','jrView',{view:'outings'})}</section></div>`;
}
export async function householdAction(action,data,el,env){
  if(!action.startsWith('jrHh'))return false;
  const v=env.api.state.journey.household,m=v?.members.find(x=>x.id===data.member);
  if(!m)return true;
  let payload={member:m.id},command='';
  if(action==='jrHhCare'){
    const x=m.acts.find(a=>a.id===data.act);if(!x||x.done)return true;
    const how=x.cost?await confirmPurchase(env,{title:x.name,message:`Chuẩn bị cho ${m.name}: ${x.cost} xu.`,label:'Chăm sóc',cost:x.cost}):'cash';
    if(!how)return true;
    command='jr_hh_care';payload.act=x.id;payload.pay=how;
  }else if(action==='jrHhStyle'){
    const x=v.outfits.find(o=>o.id===data.item);if(!x)return true;
    const cost=m.owned.includes(x.id)?0:x.cost;
    const how=cost?await confirmPurchase(env,{title:'Mua đồ cho bé',message:`${x.name}: ${cost} xu.`,label:'Mua và mặc',cost}):'cash';
    if(!how)return true;
    command='jr_hh_style';payload={...payload,item:x.id,confirm:true,pay:how};
  }
  if(command){el.disabled=true;try{if(await env.cmd(command,payload))env.renderSheet(false);}finally{if(el.isConnected)el.disabled=false;}}
  return true;
}
export async function householdSubmit(f,env){
  const kind=f.dataset.jrForm;
  if(!['hhAdopt','hhName'].includes(kind))return false;
  const name=f.querySelector('[name="name"]').value.trim();
  if(!name)return true;
  const b=f.querySelector('[type="submit"]');b.disabled=true;
  try{
    if(kind==='hhName'){if(await env.cmd('jr_hh_rename',{member:f.dataset.member,name}))env.renderSheet(false);return true;}
    const id=f.querySelector('[name="kind"]').value,x=env.api.state.journey.household.adopt.find(a=>a.id===id);
    if(!x)return true;
    const how=await confirmPurchase(env,{title:`Đón ${name} về nhà?`,message:`${x.name}. ${x.cost?`Đồ dùng ban đầu ${x.cost} xu.`:'Nhận nuôi miễn phí.'} Chăm sóc theo ngày sống, không có phí tự động.`,label:'Đón về nhà',cost:x.cost});
    if(how){
      if(await env.cmd('jr_hh_adopt',{kind:id,name,confirm:true,pay:how}))env.renderSheet(false);
    }
  }finally{if(b.isConnected)b.disabled=false;}
  return true;
}
