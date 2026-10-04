import {t as tr} from './i18n.js';
import {escapeHTML as esc} from '../icons.js';
export function signalState(now,offset,axis){
 const p=((now+offset)%16+16)%16;
 const color=axis==='y'?(p<6?'green':p<8?'yellow':'red'):(p<8?'red':p<14?'green':'yellow');
 const end=axis==='y'?(p<6?6:p<8?8:16):(p<8?8:p<14?14:16);
 const grace=color==='red'&&(axis==='y'?p-8:p)<1;
 return {color,left:Math.max(1,Math.ceil(end-p)),grace};
}
export function signalHTML(traffic){
 const ch=traffic?.challenge;if(!ch)return '';
 return `<div class="traffic-light" data-traffic-light data-offset="${ch.offset}" data-axis="${ch.axis}" data-server="${traffic.server_now}" style="padding:12px;border:2px solid #d6c4a4;border-radius:14px;background:#fff8e9"><b data-light-text></b><p style="margin:6px 0 0">${esc(tr('Dừng chờ không mất xu. Qua vạch khi đèn đỏ: phạt 12 xu; 1 giây đầu mới chuyển đỏ được miễn để kịp dừng.'))}</p></div>`;
}
export function mountSignals(root){
 for(const box of root.querySelectorAll('[data-traffic-light]')){
  if(box.dataset.mounted)return;box.dataset.mounted='1';const at=performance.now(),base=Number(box.dataset.server);
  const draw=()=>{const s=signalState(base+(performance.now()-at)/1000,Number(box.dataset.offset),box.dataset.axis);
   const color={red:'#b9362c',yellow:'#936c14',green:'#246945'}[s.color],label={red:'🔴 Đèn đỏ · giữ phanh',yellow:'🟡 Đèn vàng · giảm tốc',green:'🟢 Đèn xanh · có thể qua'}[s.color];
   box.style.borderColor=color;box.querySelector('[data-light-text]').textContent=tr(s.grace?'🔴 Vừa chuyển đỏ · dừng trước vạch':label)+' · '+s.left+'s';};
  draw();const timer=setInterval(()=>{if(!box.isConnected){clearInterval(timer);return;}draw();},200);
 }
}
