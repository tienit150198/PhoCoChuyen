/** Small shared helpers for the operator site (/admin): escaping, icons, number and
 * time formats, toasts. Independent from the game's modules on purpose. */

export const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

const PATHS={
  chart:'M3 20h18M6 16v-5M11 16V5M16 16V9M20 16v-3',
  inbox:'M3 13l3-9h12l3 9v7H3v-7ZM3 13h5l2 3h4l2-3h5',
  chat:'M3 10a6.5 6 0 0113 0 6.5 6 0 01-6.5 6c-1 0-1.9-.2-2.7-.5L3 17l.9-3.1A5.7 5.7 0 013 10ZM18.6 8.2A5.6 5.2 0 0121 12.6c0 1.1-.3 2.1-.9 2.9L21 19l-3.5-1.3a6.3 6.3 0 01-6.7-.4',
  server:'M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3ZM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3',
  exit:'M9 3H3v18h6M9 12h12M16 7l5 5-5 5',
  sun:'M12 8a4 4 0 100 8 4 4 0 000-8ZM12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19',
  moon:'M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5Z',
  refresh:'M20 7a9 9 0 10-1 12M20 2v6h-6',
  lock:'M5 10h14v11H5V10ZM8 10V6a4 4 0 018 0v4M12 14v3',
  alert:'M12 3 2 20h20L12 3ZM12 10v4M12 17h.01',
  menu:'M3 6h18M3 12h18M3 18h18',
  x:'M6 6l12 12M18 6 6 18',
  user:'M12 12a5 5 0 100-10 5 5 0 000 10ZM3 22c0-5 4-8 9-8s9 3 9 8',
  send:'M22 2L2 9l8 4 4 9 8-20ZM10 13L22 2',
  back:'M20 12H4M11 5l-7 7 7 7',
  chevron:'M9 5l7 7-7 7',
  check:'M4 12l5 5L20 6',
  search:'M11 4a7 7 0 100 14 7 7 0 000-14ZM21 21l-5-5',
  eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12ZM12 9a3 3 0 100 6 3 3 0 000-6',
  external:'M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5',
  clock:'M12 2a10 10 0 100 20 10 10 0 000-20ZM12 6v6l4 3',
  sparkle:'M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7Z',
  pause:'M12 2a10 10 0 100 20 10 10 0 000-20ZM10 8.5v7M14 8.5v7',
  pulse:'M3 12h4l2-6 4 12 2-6h6',
  loop:'M17 2l4 4-4 4M3 11V9a3 3 0 013-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 01-3 3H3',
  download:'M12 3v12M7 10l5 5 5-5M4 19h16',
  trend:'M3 17l6-6 4 4 8-8M15 7h6v6',
  info:'M12 2a10 10 0 100 20 10 10 0 000-20ZM12 11v6M12 7.5h.01',
  print:'M6 9V3h12v6M6 18H4v-7h16v7h-2M7 14h10v7H7v-7Z',
};
export const icon=(name,size=18)=>`<svg class="ic" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${PATHS[name]||PATHS.sparkle}"/></svg>`;

const nf=new Intl.NumberFormat('vi-VN'),nf1=new Intl.NumberFormat('vi-VN',{maximumFractionDigits:1});
export const num=n=>n==null?'—':nf.format(Math.round(n));
export const dec=n=>n==null?'—':nf1.format(n);
export const pct=n=>n==null?'—':`${nf1.format(n)}%`;
export const share=(n,total)=>total?pct(Math.round(1000*n/total)/10):'';
export const dm=iso=>`${iso.slice(8,10)}/${iso.slice(5,7)}`;
/* Every time on this site is Vietnam time (the server's days are Vietnam days), whatever the
 * operator's own computer is set to. */
export const TZ='Asia/Ho_Chi_Minh';
export const clock=t=>new Date(t*1000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit',timeZone:TZ});
export const clockS=t=>new Date(t*1000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:TZ});
/** The Vietnam day of a unix time, "YYYY-MM-DD". */
export const vnDay=t=>new Date(t*1000).toLocaleDateString('en-CA',{timeZone:TZ});
/** "14:23", or "14:23 29/09" when not today (Vietnam days). */
export function hm(t){if(t==null)return'—';const d=vnDay(t);return d===vnDay(Date.now()/1000)?clock(t):`${clock(t)} ${dm(d)}`;}
export const stamp=t=>new Date(t*1000).toLocaleString('vi-VN',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit',year:'numeric',timeZone:TZ});
/** A UTC text of the database ("YYYY-MM-DD HH:MM:SS") as unix time. */
export const utcText=s=>s?Date.parse(String(s).replace(' ','T')+'Z')/1000:null;
export const last=a=>a?.length?a[a.length-1]:0;
export function bytes(b){if(b==null)return'—';const u=['B','KB','MB','GB'];let i=0;while(b>=1024&&i<u.length-1){b/=1024;i++;}return `${nf1.format(b)} ${u[i]}`;}
export function span(s){if(s==null)return'—';const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return d?`${d} ngày ${h} giờ`:h?`${h} giờ ${m} phút`:`${m} phút`;}
export function hours(h){if(h==null)return'—';return h<1?`${Math.max(1,Math.round(h*60))} phút`:h<48?`${dec(h)} giờ`:`${dec(h/24)} ngày`;}
export function ago(t){const s=Math.max(0,Date.now()/1000-t);if(s<60)return'vừa xong';if(s<3600)return`${Math.floor(s/60)} phút trước`;if(s<86400)return`${Math.floor(s/3600)} giờ trước`;return`${Math.floor(s/86400)} ngày trước`;}

export const KINDS=[['bug','🐞','Lỗi'],['idea','💡','Ý tưởng'],['praise','💖','Khen'],['hard','🤔','Khó dùng']];
export const kindOf=id=>KINDS.find(k=>k[0]===id)||[id,'•',id];
export const STATUS={new:['Mới','warn'],seen:['Đã xem','info'],done:['Xong','good']};
export const tag=(label,tone='')=>`<span class="tag ${tone}">${label}</span>`;

export function toast(message,tone=''){
  const box=document.getElementById('toasts');if(!box)return;
  const el=document.createElement('div');el.className=`toast ${tone}`;el.textContent=message;box.append(el);
  setTimeout(()=>{el.classList.add('out');setTimeout(()=>el.remove(),300);},tone==='bad'?5200:2800);
}
