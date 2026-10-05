/** Personal customer visits: local previews, explicit paid service, persistent keepsakes. */
import {escapeHTML as esc,icon} from '../icons.js';
import {lookOf,portrait} from './look.js';
import {confirmPurchase} from './payment.js';
import {communityView,communityAction} from './community-outings.js';
import {craftedArt} from './craft-art.js';
const tabs=[['salon','💇','Ghé salon'],['nails','💅','Làm móng'],['craft','🧵','Xưởng handmade'],['community','🏘️','Sách, CLB & gia đình']];
const st=ui=>ui.outings??={tab:'salon',hair:null,color:'rose',pattern:'plain',kind:'teddy'};
const button=(label,act,data={},cls='ghost')=>`<button type="button" class="btn ${cls}" data-action="${act}" ${Object.entries(data).map(([k,v])=>`data-${k}="${esc(v)}"`).join(' ')}>${label}</button>`;
const chosen=(s,key,value,label)=>`<button type="button" class="btn ${s[key]===value?'primary':'ghost'}" data-action="jrOutPick" data-key="${key}" data-value="${esc(value)}" aria-pressed="${s[key]===value}">${label}</button>`;
const patternMark={plain:'',flower:'✿',stars:'✦',waves:'≈'};
const name=(list,id)=>list.find(x=>x.id===id)?.name||'';
function art(c,value,nails=false){
 if(!nails&&(value.kind==='teddy'||value.work))return craftedArt(value,c.colors);
 const col=c.colors.find(x=>x.id===value.color)?.hex||'#eedcc4',mark=patternMark[value.pattern]||'',title=nails?'Bản xem màu móng':name(c.crafts,value.kind);
 let shape='';
 if(nails){shape=[0,1,2,3,4].map((i)=>`<rect x="${17+i*31}" y="${35+Math.abs(2-i)*9}" width="25" height="66" rx="12" fill="${col}" stroke="#8a6457" stroke-width="2"/><text x="${29+i*31}" y="${74+Math.abs(2-i)*5}" text-anchor="middle" fill="#fff8ef" font-size="18">${mark}</text>`).join('');}
 else if(value.kind==='bracelet'){shape=Array.from({length:12},(_,i)=>{const a=i*Math.PI/6;return `<circle cx="${95+55*Math.cos(a)}" cy="${78+43*Math.sin(a)}" r="10" fill="${col}" stroke="#866a55"/>`;}).join('')+`<text x="95" y="92" text-anchor="middle" fill="#826444" font-size="34">${mark}</text>`;}
 else if(value.kind==='card'){shape=`<rect x="30" y="20" width="130" height="115" rx="7" fill="${col}" stroke="#8a6457" stroke-width="2"/><path d="M42 30V125" stroke="#fff8ef" stroke-width="2"/><text x="100" y="95" text-anchor="middle" fill="#fff8ef" font-size="52">${mark||'♡'}</text>`;}
 else{shape=`<path d="M95 54Q57 28 62 14Q96 15 95 54Q117 15 138 29Q132 58 95 54" fill="#739d68"/><path d="M48 64H142L130 132H60Z" fill="${col}" stroke="#8a6457" stroke-width="2"/><rect x="42" y="53" width="106" height="17" rx="5" fill="${col}" stroke="#8a6457" stroke-width="2"/><text x="95" y="114" text-anchor="middle" fill="#fff8ef" font-size="38">${mark}</text>`;}
 return `<svg viewBox="0 0 190 155" width="190" height="155" role="img" aria-label="${esc(title)}"><ellipse cx="95" cy="141" rx="70" ry="7" fill="#d8c6ae44"/>${shape}</svg>`;
}
const styles=`<style>.outings{padding:18px}.outings .out-tabs,.outings .out-options{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.outings .out-preview{text-align:center;padding:12px;background:#faf3e6;border-radius:16px}.outings .out-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}.outings .out-hair{display:flex;flex-direction:column;align-items:center;gap:5px;border-radius:14px;border:1px solid #d7caba;background:#fffaf2;padding:12px}.outings .out-hair[aria-pressed=true]{outline:2px solid #a75037}.outings .out-swatch{display:inline-block;width:18px;height:18px;border:1px solid #826a55;border-radius:50%;vertical-align:middle;margin-right:6px}.outings .out-saved{border:1px solid #d7caba;border-radius:14px;padding:12px;text-align:center;background:#fffaf2}.outings .out-saved svg{width:100%;max-width:190px}.outings .out-saved p{margin:4px 0}.outings .out-price{font-weight:700}.outings .out-step{margin-top:18px;font-size:1rem}.outings .btn{white-space:normal}.outings p{line-height:1.5}</style>`;

export function outingsView({api,ui}){
 const s=st(ui),j=api.state.journey,d=j.outings,c=api.content.journey.outings;
 if(!c||!d)return '<p class="notice">Đang chuẩn bị góc đi chơi…</p>';
 if(!c.crafts.some(x=>x.id===s.kind))s.kind=c.crafts[0]?.id;
 const look=lookOf(api.state),hair=d.hairstyles.find(x=>x.id===s.hair)||d.hairstyles.find(x=>x.id===look.hair)||d.hairstyles[0];
 s.hair=hair?.id;
 let body='',price=0,done=false;
 if(s.tab==='community'){
  body=communityView({api,ui});
 }else if(s.tab==='salon'){
  price=hair?.price||c.salon_fee;done=d.salon?.hair===s.hair&&look.hair===s.hair;
  body=`<p>Chọn kiểu tóc và ngắm thử trong gương. Kiểu mới sẽ vào tủ đồ và theo nhân vật ra phố.</p><div class="out-preview">${portrait({...look,hair:s.hair},j.gender,120,'')}<p>${esc(hair?.name||'')}</p></div><h3 class="out-step">1. Chọn kiểu tóc</h3><div class="out-grid">${d.hairstyles.map(h=>`<button type="button" class="out-hair" data-action="jrOutPick" data-key="hair" data-value="${esc(h.id)}" aria-pressed="${s.hair===h.id}">${portrait({...look,hair:h.id},j.gender,72,'')}<b>${esc(h.name)}</b><small>${h.price} xu</small></button>`).join('')}</div><p>Phí làm tóc ${c.salon_fee} xu; kiểu chưa có trong tủ được mua thêm đúng giá hiển thị.</p>`;
 }else{
  const craft=s.tab==='craft';price=craft?c.craft_fee:c.nail_fee;
  done=craft?false:!!d.nails&&['color','pattern'].every(k=>d.nails[k]===s[k]);
  body=`<p>${craft?'Tự tay làm từng công đoạn trên bàn: đo, cắt, may hoặc xâu hạt. Có vạch hướng dẫn, làm lại được và không bị giục giờ.':'Thử màu và họa tiết trước khi sơn. Bộ móng được lưu để lần sau ghé lại vẫn thấy.'}</p><div class="out-preview">${art(c,s,!craft)}${craft&&s.kind==='teddy'?'<p><b>Gấu bông của riêng bạn</b><br>Đo · Cắt · May · Nhồi bông · Trang trí</p>':''}</div>${craft?`<h3 class="out-step">1. Chọn món để làm</h3><div class="out-options">${c.crafts.map(k=>chosen(s,'kind',k.id,`${k.emoji} ${esc(k.name)}`)).join('')}</div>`:''}<h3 class="out-step">${craft?'2':'1'}. Chọn màu</h3><div class="out-options">${c.colors.map(k=>chosen(s,'color',k.id,`<span class="out-swatch" style="background:${k.hex}"></span>${esc(k.name)}`)).join('')}</div><h3 class="out-step">${craft?'3':'2'}. Chọn họa tiết</h3><div class="out-options">${c.patterns.map(k=>chosen(s,'pattern',k.id,`${k.emoji} ${esc(k.name)}`)).join('')}</div>`;
 }
 const full=s.tab==='craft'&&d.crafts.length>=c.max_crafts;
 const pay=s.tab==='community'?'':done?'<p class="notice">Mẫu này đã lưu rồi, không cần trả thêm.</p>':full?'<p class="notice">Kệ đã đủ 24 món. Những món đã làm vẫn được giữ ở đây.</p>':s.tab==='craft'?`<p class="out-price">Vật liệu: ${price} xu · chỉ thanh toán khi hoàn thành</p>${button('🧵 Vào bàn làm','jrOutMake',{},'primary')}`:`<p class="out-price">Tổng: ${price} xu</p>${button(s.tab==='salon'?'Làm tóc & giữ kiểu':'Sơn & lưu bộ móng','jrOutBuy',{},'primary')}`;
 const nails=d.nails?`<section class="out-saved"><h3>Bộ móng đang giữ</h3>${art(c,d.nails,true)}<p>${esc(name(c.colors,d.nails.color))} · ${esc(name(c.patterns,d.nails.pattern))}</p><small>Ngày ${d.nails.day}</small></section>`:'';
 const shelf=`<h3 class="out-step">Kệ kỷ niệm · ${d.crafts.length}/${c.max_crafts}</h3>${d.crafts.length?`<div class="out-grid">${d.crafts.map(x=>`<article class="out-saved">${art(c,x)}<b>${esc(name(c.crafts,x.kind))}</b><p>${esc(name(c.colors,x.color))} · ${esc(name(c.patterns,x.pattern))}</p><small>Ngày ${x.day}</small></article>`).join('')}</div>`:'<p>Chưa có món thủ công. Thử phối một mẫu ở Xưởng DIY nhé.</p>'}`;
 return `<header class="sheet-head jr-head">${button(icon('back',18),'jrView',{view:'home'},'ghost small')}<div class="grow"><span class="eyebrow">MỘT BUỔI CHO MÌNH</span><h2>Đi chơi & làm đẹp</h2></div>${button(icon('x',18),'close',{},'ghost small')}</header>${styles}<div class="outings"><nav class="out-tabs" aria-label="Đi chơi">${tabs.map(([id,e,l])=>button(`${e} ${l}`,'jrOutTab',{tab:id},s.tab===id?'primary':'ghost')).join('')}</nav>${body}${pay}<hr>${nails}${shelf}</div>`;
}

export async function outingsAction(action,data,el,env){
 if(action==='jrOutCommunity')return communityAction(data,el,env);
 const {api,ui,cmd,renderSheet,confirmAction}=env,s=st(ui),c=api.content.journey.outings,d=api.state.journey.outings;
 if(action==='jrOutMake'||action==='jrOutBuy'&&s.tab==='craft'){
  if(d.crafts.length>=c.max_crafts)return true;
  const {openCraftWorkbench}=await import('./craft-workbench.js');
  await openCraftWorkbench(env,{kind:s.kind,color:s.color,pattern:s.pattern,materialChanges:{...s.materialChanges}});s.materialChanges={};return true;
 }
 if(action==='jrOutTab'){if(tabs.some(t=>t[0]===data.tab))s.tab=data.tab;renderSheet(false);return true;}
 if(action==='jrOutPick'){
  const list=data.key==='hair'?d.hairstyles:data.key==='kind'?c.crafts:data.key==='color'?c.colors:data.key==='pattern'?c.patterns:null;
  if(list?.some(x=>x.id===data.value)){
   s[data.key]=data.value;
   if(['color','pattern'].includes(data.key))(s.materialChanges??={})[data.key]=true;
  }
  renderSheet(false);return true;
 }
 if(action!=='jrOutBuy')return false;
 const salon=s.tab==='salon',craft=s.tab==='craft',hair=d.hairstyles.find(x=>x.id===s.hair);
 const price=salon?hair?.price:craft?c.craft_fee:c.nail_fee;if(!price)return true;
 const label=salon?hair.name:craft?name(c.crafts,s.kind):'Sơn và vẽ móng';
 const how=await confirmPurchase(env,{title:label,message:`Tổng ${price} xu.`,label:`Thanh toán · ${price} xu`,cost:price});
 if(!how)return true;
 await cmd(salon?'jr_out_salon':craft?'jr_out_craft':'jr_out_nails',salon?{hair:s.hair,pay:how}:{...(craft?{kind:s.kind}:{}),color:s.color,pattern:s.pattern,pay:how});
 renderSheet(false);return true;
}
