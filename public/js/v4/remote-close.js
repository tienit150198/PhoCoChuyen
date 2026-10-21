/** 📲 Đóng ca từ xa (game/remote_close.py → state.journey.remote {own, item, shops}, player feedback #456). Loaded lazily
 * by app.js (L.remote), its sheet opened with data-action="remoteClose" (the menu, the journey page); v4/abroad.js shows
 * the same list above "Lên đường". Each button sends the ordinary end_day of that workplace with {remote:true}: the
 * server runs the shop's own close (money, wages, stock, the day) and keeps the player where they are. Without the
 * 📲 Máy quản lý từ xa the list says what to buy and where (📱 Mây Mobile, its 📲 Tiện ích tab). */
import {icon,escapeHTML as esc} from '../icons.js';

export const ACTIONS=new Set(['remoteClose','rcClose']);

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const act=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;
const head=(title,sub='')=>`<header class="sheet-head"><div class="grow"><span class="eyebrow">MÁY QUẢN LÝ TỪ XA</span><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const place=(api,cid)=>{const m=api.content?.catalogue?.find(x=>x.id===cid);return m?(m.place||m.short):cid;};
const R=api=>api.state?.journey?.story?api.state.journey.remote||null:null;
/** The device in Mây Mobile's catalogue (content.journey.gadgets): its name and price for the locked hint. */
function device(api,R0){
  const G=api.content?.journey?.gadgets,it=G?.items?.find(x=>x.id===R0.item);
  return {name:it?.name||'Máy quản lý từ xa',price:it?.price||0,shop:G?.shop||'Mây Mobile'};
}
/** The open shifts the player is not standing in (what the menu and the journey page count). */
export const away=api=>(R(api)?.shops||[]).filter(x=>!x.here);

function row(api,sh,own){
  const bits=[`Ngày ${fmt(sh.day)}`,`xong ${fmt(sh.done)} việc`,sh.left?`còn ${fmt(sh.left)} việc để mai`:'',sh.event?'chuyện đang dở mang sang mai':''].filter(Boolean).join(' · ');
  const go=own?act('📲 Đóng ca từ xa','rcClose',{career:sh.career},'primary small'):act('Về tiệm khép ca','choose',{career:sh.career},'cream small');
  return `<li class="rc-row"><span class="grow"><b>${esc(place(api,sh.career))}</b>${sh.here?' <span class="tag">Đang ở đây</span>':''}<small>${esc(bits)}</small></span>${go}</li>`;
}

/** The list of open shifts with their state and a button each; '' when nothing is open. `back`: also the "Về tiệm"
 * buttons for a player without the device (the sheet; v4/abroad.js keeps its own). */
export function remoteList(env,{back=true}={}){
  const {api,ui}=env,R0=R(api);if(!R0||!R0.shops?.length)return '';
  const last=ui?.rcLast&&!R0.shops.some(x=>x.career===ui.rcLast.career)?`<p class="ab-last good">${esc(ui.rcLast.text)}</p>`:'';
  if(!R0.own){
    const d=device(api,R0);
    return `${last}<p class="ab-why rc-lock">${d.price?`🔒 Muốn khép ca từ xa, khỏi về từng tiệm: mua 📲 ${esc(d.name)} (${fmt(d.price)} xu) ở 📱 ${esc(d.shop)}, mục 📲 Tiện ích.`:`🔒 Muốn khép ca từ xa, khỏi về từng tiệm: mua 📲 ${esc(d.name)} ở 📱 ${esc(d.shop)}, mục 📲 Tiện ích.`}</p>
      <div class="row wrap">${act(`📱 Tới ${esc(d.shop)}`,'gadgets',{tab:'tool'},'ghost small')}</div>${back?`<ul class="rc-list">${R0.shops.map(x=>row(api,x,false)).join('')}</ul>`:''}`;
  }
  return `${last}<ul class="rc-list">${R0.shops.map(x=>row(api,x,true)).join('')}</ul><p class="small muted">Lương, điện nước, kho và ngày sống tính y như khép ca tại tiệm.</p>`;
}

export function remoteView(env){
  const {api}=env,R0=R(api),n=R0?.shops?.length||0;
  const body=n?remoteList(env):`${env.ui?.rcLast?`<p class="ab-last good">${esc(env.ui.rcLast.text)}</p>`:''}<p class="muted">Không còn ca nào đang mở.</p>`;
  return head('📲 Đóng ca từ xa',n?`${n} ca đang mở`:'')+`<div class="sheet-body ab-body">${body}</div>`;
}

export async function remoteAction(action,data,el,env){
  if(!ACTIONS.has(action))return false;
  const {api,ui,cmd,confirmAction,openSheet,renderSheet}=env;
  if(action==='remoteClose'){ui.rcLast=null;openSheet('remoteClose');return true;}
  const sh=(R(api)?.shops||[]).find(x=>x.career===data?.career);
  if(!sh){renderSheet();return true;}
  const where=place(api,sh.career);
  if(!(await confirmAction(`Khép ca ở ${where}?`,'Lương, điện nước, kho tính y như khép ca tại tiệm. Việc dở để mai, chuyện đang dở mang sang ngày sau.','Khép ca từ xa')))return true;
  const r=await cmd('end_day',{remote:true},{career:sh.career});
  if(r&&!r.duplicate){const net=Number(r.summary?.net)||0,v=`${net>=0?'+':'−'}${fmt(Math.abs(net))}`;ui.rcLast={career:sh.career,text:`✓ Đã khép ca ở ${where}, ${v} xu trong ca.`};}
  renderSheet();return true;
}
