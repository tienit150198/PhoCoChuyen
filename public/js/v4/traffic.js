import {t as tr} from './i18n.js';
import {escapeHTML as esc} from '../icons.js';
export function signalState(now,offset,axis){
 const p=((now+offset)%16+16)%16;
 const color=axis==='y'?(p<6?'green':p<8?'yellow':'red'):(p<8?'red':p<14?'green':'yellow');
 const end=axis==='y'?(p<6?6:p<8?8:16):(p<8?8:p<14?14:16);
 const grace=color==='red'&&(axis==='y'?p-8:p)<1;
 return {color,left:Math.max(1,Math.ceil(end-p)),grace};
}
const clocks=new Map(),mounted=new WeakMap();
const COLORS={red:'#b9362c',yellow:'#936c14',green:'#246945'};
const LABELS={red:'Đèn đỏ · giữ phanh',yellow:'Đèn vàng · giảm tốc',green:'Đèn xanh · có thể qua'};
function clock(token,server){
 const now=performance.now();let value=clocks.get(token);
 if(!value||server>value.sample){
  const projected=value?value.time+(now-value.at)/1000:server;
  value={sample:server,time:Math.max(server,projected),at:now};clocks.set(token,value);
  if(clocks.size>128)clocks.delete(clocks.keys().next().value);
 }
 return value.time+(now-value.at)/1000;
}
const label=s=>tr(s.grace?'Đèn đỏ · dừng trước vạch':LABELS[s.color]);
export function signalHTML(traffic){
 const ch=traffic?.challenge;if(!ch)return '';
 const token=String(ch.token||`${ch.offset}:${ch.axis}`),s=signalState(clock(token,Number(traffic.server_now)),ch.offset,ch.axis),color=COLORS[s.color];
 const lamps=['red','yellow','green'].map(k=>`<i data-light-lamp="${k}" style="display:block;width:20px;height:20px;border-radius:50%;background:${k===s.color?COLORS[k]:'#46524e'};border:2px solid ${k===s.color?'#fff':'transparent'}"></i>`).join('');
 return `<div class="traffic-light" data-traffic-light data-token="${esc(token)}" data-offset="${ch.offset}" data-axis="${ch.axis}" data-server="${traffic.server_now}" style="padding:12px;border:2px solid ${color};border-radius:14px;background:#fff8e9;color:#283e3d">
 <div style="display:flex;align-items:center;gap:10px;min-height:76px"><span aria-hidden="true" style="display:flex;gap:5px;padding:7px;border-radius:12px;background:#263c36">${lamps}</span><b data-light-text style="flex:1;font-size:16px;line-height:1.35">${esc(label(s))}</b><strong data-light-count style="min-width:3ch;text-align:right;font-size:24px;font-variant-numeric:tabular-nums">${s.left}s</strong></div>
 <p style="margin:6px 0 0;font-size:12px;line-height:1.45">${esc(tr('Dừng chờ không mất xu. Qua vạch khi đèn đỏ: phạt 12 xu; 1 giây đầu mới chuyển đỏ được miễn để kịp dừng.'))}</p></div>`;
}
export function mountSignals(root){
 for(const box of root.querySelectorAll('[data-traffic-light]')){
  if(mounted.has(box)){mounted.get(box)();continue;}
  const draw=()=>{const s=signalState(clock(box.dataset.token,Number(box.dataset.server)),Number(box.dataset.offset),box.dataset.axis);
   box.style.borderColor=COLORS[s.color];
   const text=box.querySelector('[data-light-text]'),count=box.querySelector('[data-light-count]');
   if(text.textContent!==label(s))text.textContent=label(s);
   if(count.textContent!==s.left+'s')count.textContent=s.left+'s';
   for(const lamp of box.querySelectorAll('[data-light-lamp]')){
    const active=lamp.dataset.lightLamp===s.color;
    lamp.style.background=active?COLORS[s.color]:'#46524e';lamp.style.borderColor=active?'#fff':'transparent';
   }
  };
  mounted.set(box,draw);draw();
  const timer=setInterval(()=>{if(!box.isConnected){clearInterval(timer);mounted.delete(box);return;}draw();},200);
 }
}
