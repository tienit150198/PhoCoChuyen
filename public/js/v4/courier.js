import {escapeHTML as esc} from '../icons.js';
import {confirmPurchase} from './payment.js';
const b=(label,op,data={},off=false)=>`<button type="button" class="btn cream small" data-action="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${off?' disabled':''}>${label}</button>`;
export function courierView(env){
  const v=env.api.state.journey.courier;
  if(!v)return '';
  const a=v.active;
  return `<div class="jr-home"><header class="sheet-head"><div class="grow"><h2>🛵 Sổ shipper</h2><p>Bậc ${v.level} · ${v.completed} hợp đồng · ${v.delivered} đơn hợp đồng đã giao</p></div>${b('Quay lại','jrView',{view:'home'})}</header><section class="jr-card"><p>Nhận hợp đồng, vào nghề Giao hàng giao đơn thật rồi trở lại nhận thưởng. Phí giao đơn và tiền COD vẫn nằm trong sổ nghề; ở đây chỉ tính thưởng hợp đồng.</p><p>Hoàn tất 3 hợp đồng mở tuyến nhanh, 10 hợp đồng mở đối tác chuỗi. Mỗi lần theo một hợp đồng; không hết hạn khi bạn nghỉ chơi.</p>${b('📦 Vào nghề Giao hàng','choose',{career:'delivery'},!v.unlocked)}</section>${!v.unlocked?'<section class="jr-card">Mở nghề Giao hàng trong hành trình để nhận hợp đồng.</section>':''}${a?`<section class="jr-card"><h3>${a.emoji} ${esc(a.name)}</h3><p>${a.done}/${a.target} đơn ${a.category==='food'?'đồ ăn':'giao thành công'} · ${a.bad} đơn bị trễ hoặc có sai sót</p><progress max="${a.target}" value="${a.done}">${a.done}/${a.target}</progress><p>Thưởng ${a.fee} − khấu trừ ${a.deduction} = <b>${a.bonus} xu</b>. Đã chi ${a.cost} xu chuẩn bị khi nhận.</p><p>Sai sót hoặc giao trễ giảm thưởng; từ chối/giao thất bại không tính tiến độ. Đồ nghề hỗ trợ giảm khấu trừ.</p><div style="display:flex;gap:8px;flex-wrap:wrap">${b('Nhận thưởng','jrShipCollect',{},!a.ready)}${b('Hủy hợp đồng','jrShipCancel')}</div></section>`:`<section class="jr-card"><h3>Hợp đồng đang có</h3>${v.contracts.map(x=>`<article style="padding:12px 0;border-bottom:1px solid var(--line)"><h4>${x.emoji} ${esc(x.name)}</h4><p>${x.target} đơn${x.category==='food'?' đồ ăn':''} · thưởng ${x.fee} xu · chuẩn bị ${x.cost} xu</p>${x.locked?`<p>Mở ở bậc ${x.level}</p>`:b('Nhận hợp đồng','jrShipAccept',{kind:x.id},!v.unlocked)}</article>`).join('')}</section>`}<section class="jr-card"><h3>Đồ nghề hợp đồng</h3>${v.gear.map(x=>`<p><b>${x.emoji} ${esc(x.name)}</b><br>${esc(x.desc)}<br>${b(x.owned?'Đã có':`Mua · ${x.cost} xu`,'jrShipGear',{item:x.id},x.owned||!v.completed&&!a)}</p>`).join('')}</section><section class="jr-card"><h3>Đã nhận ${v.earned} xu thưởng</h3>${v.history.map(r=>`<p>Ngày ${r.day}: thưởng ${r.fee} − khấu trừ ${r.deduction} = +${r.bonus} xu; chuẩn bị ${r.cost} xu.</p>`).join('')||'<p>Hợp đồng hoàn tất sẽ được ghi ở đây.</p>'}</section></div>`;
}
export async function courierAction(action,data,el,env){
  if(!action.startsWith('jrShip'))return false;
  const v=env.api.state.journey.courier;
  let cmd='',p={};
  if(action==='jrShipAccept'||action==='jrShipGear'){
    const accept=action==='jrShipAccept',x=(accept?v.contracts:v.gear).find(x=>x.id===(accept?data.kind:data.item));if(!x)return true;
    const pay=await confirmPurchase(env,{title:x.name,message:accept?`${x.target} đơn mới phù hợp, thưởng tối đa ${x.fee} xu. Chi phí chuẩn bị ${x.cost} xu không hoàn khi hủy.`:x.desc,label:'Xác nhận',cost:x.cost});
    if(!pay)return true;
    cmd=accept?'jr_ship_accept':'jr_ship_gear';p={...accept?{kind:x.id}:{item:x.id},confirm:true,pay};
  }else if(action==='jrShipCancel'){
    if(!await env.confirmAction('Hủy hợp đồng?','Không phạt thêm, nhưng chi phí chuẩn bị không hoàn lại.','Hủy hợp đồng'))return true;
    cmd='jr_ship_cancel';p.confirm=true;
  }else if(action==='jrShipCollect')cmd='jr_ship_collect';
  if(cmd){el.disabled=true;try{if(await env.cmd(cmd,p))env.renderSheet(false);}finally{if(el.isConnected)el.disabled=false;}}
  return true;
}
