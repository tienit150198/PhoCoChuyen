/** Quầy trà sữa — hands-on boba counter. game/boba.py is the referee: every
 * tap is a command, the server keeps stock, patience, sealing time and grades.
 * Care loop: tea brewed in pots and pearls cooked in batches go stale by the
 * shop clock, supplier orders arrive at real times of day, the heat sealer needs
 * cleaning, the regulars' card and tomorrow's forecast. A sticky bar on phones
 * keeps the order recap and the serve button in reach. */
import {Sound} from '../audio.js';
import {keepBarAboveFooter} from './food_kit.js';
import {nextHint,stepCta,barParts,finalGo,pending as nextOf,firstTime,stepLine,todoAttrs} from '../v4/guide.js';
import {actBar,clean,tip,headChip,helpBtn,whyAttrs} from '../ui-kit.js';
// Typed numbers in the − N + steppers (owner 07/10: "cho nhập số nhé").
import {qtyBox,QTY} from '../qty-input.js';

const ICE=[['none','Không đá'],['little','Ít đá'],['normal','Đá vừa'],['extra','Nhiều đá']];
const ICE_TEXT={none:'không đá',little:'ít đá',normal:'đá vừa',extra:'nhiều đá'};
const SEAL_TEXT={perfect:'✨ Nắp căng đẹp',ok:'✓ Đã dán nắp',burnt:'🟫 Nắp hơi cháy xém'};
const DONE=['completed','referred','cancelled'];

const pay=(x,o)=>x.esc(JSON.stringify(o));
// The room can be missing for a moment (a sheet re-rendered while the day reloads): read it softly.
const B=x=>x?.room?.data?.boba||{};
const ings=x=>x.content.experiences?.ingredients||[];
const ing=(x,id)=>ings(x).find(i=>i.id===id)||{id,name:id,emoji:'•',color:'#d8c7a8',group:'topping',level:1,cost:0};
const low=s=>s?s[0].toLocaleLowerCase('vi')+s.slice(1):'';
const open=t=>!DONE.includes(t.status);
const station0=(x,id)=>(B(x).stations||[]).find(s=>s.id===id)||{id,unlocked:true,stock:0,level:1};
// A pick shown ahead of the server (see "picks at once" below) counts off the shelf at once too.
const station=(x,id)=>{const s=station0(x,id),n=unsent(x,id);return n?{...s,stock:Math.max(0,s.stock-n)}:s;};
// Counter taps go through actions.go: quiet (feedback shows next to the cup), toasts only for results that matter.
const pick=(x,id)=>`data-action="job" data-task="${x.esc(id)}"`;
const cmdAttr=(x,op,payload)=>`data-action="car:go" data-op="${op}" data-payload="${pay(x,payload)}"${QUICK.has(op)?' data-quick data-own-busy':''}`;
/* After end_day the unfinished cups stay and the counter still opens, but game/boba.py refuses every brewing step
 * ("Mở cửa quán trước khi pha nhé."): a quick pick lit up and fell back, the bar still said "Lấy ly". While the shop
 * is closed the brewing controls are dimmed but tappable (docs/UI_KIT.md "Disabled with a reason": a tap says
 * "Mở ca trước" with the ☀️ Mở ca fix) and the bar's main button opens the shift. Kho (tea_prepare, tea_order…) still
 * works. A room not drawn yet counts as open (no flash of dimmed tiles). */
const closedNow=x=>!!x?.room&&!x.room.open;
const BREW=new Set(['tea_cup','tea_add','tea_ice','tea_sugar','tea_seal','tea_seal_start','tea_check','tea_discard','tea_serve','tea_greet','tea_swap']);
const OPEN_GO={act:'startHere',label:'☀️ Mở ca'};
const shutAttrs=()=>whyAttrs({why:'Mở ca trước',fix:OPEN_GO});
const jb=(x,label,op,payload={},style='',disabled=false)=>BREW.has(op)&&closedNow(x)
  ?`<button type="button" class="btn ${style} is-why"${shutAttrs()}>${label}</button>`
  :`<button type="button" class="btn ${style}" ${cmdAttr(x,op,payload)}${disabled?' disabled':''}>${label}</button>`;
const LOUD=new Set(['tea_menu','tea_serve','tea_seal','tea_event','tea_event_ok','tea_discard','tea_check','tea_prepare','tea_cups','tea_wipe','tea_order','tea_clean','tea_toss','tea_swap','tea_greet','more_work','life_mode','life_goal']);
const sfx=new Sound();
const hasGroup=(x,cup,g)=>(cup.items||[]).some(k=>ing(x,k).group===g);
const seal=x=>B(x).seal||{loose:.8,good_lo:1.4,good_hi:2.6,burn:4.2,max:5};

/* ---------------------------------------------------------------- picks at once
 * Feedback #116 "pha trà chọn đồ nhanh ko bị lag": a pick (cup, tea, syrup, topping, ice, sugar) showed only after
 * its command came back and the whole counter was drawn again (twice), and a second pick meanwhile was held or
 * landed on a tile still drawn as off. Now a pick the server would take (the same checks as game/boba.py _station)
 * shows at once: the tile lights up in the same frame, then the cup, the shelf counts and the next step follow from
 * x.ui.mtLocal (picks sent, not answered yet) laid over the server's cup. The commands still go one by one through
 * the queue and the server decides; once each is answered its pick leaves mtLocal and the screen is the server's
 * again (a refusal undoes the pick, with its toast). The commands and saves are the same as before. */
const QUICK=new Set(['tea_cup','tea_add','tea_ice','tea_sugar']);
const localOf=(x,tid)=>(x.ui.mtLocal||[]).filter(p=>p.payload.task===tid);
const serverTask=(x,tid)=>(x.room?.tasks||[]).find(t=>t.id===tid);
/** Portions of `id` picked but not yet taken off by the server (not in its cup yet). */
function unsent(x,id){
  const L=x.ui.mtLocal;if(!L?.length)return 0;
  return L.filter(p=>p.op==='tea_add'&&p.payload.item===id&&!(serverTask(x,p.payload.task)?.cup?.items||[]).includes(id)).length;
}
/** The cup with the picks on their way. Laying a pick the server has taken again changes nothing. */
function laid(x,cup,list){
  const c={...cup,items:[...(cup.items||[])]};
  for(const {op,payload:p} of list){
    if(op==='tea_cup'){if(!c.items.length&&!(c.placed&&c.size===p.size))Object.assign(c,{placed:true,size:p.size,checked:false});}
    else if(op==='tea_add'){if(!c.items.includes(p.item)){c.items.push(p.item);c.checked=false;}}
    else if(op==='tea_ice'){if(c.ice!==p.level)Object.assign(c,{ice:p.level,checked:false});}
    else if(op==='tea_sugar'){if(c.sugar!==p.level)Object.assign(c,{sugar:p.level,checked:false});}
  }
  return c;
}
/** The order ticket read again for a cup (game/boba.py ticket(): the same rows, in the same order). */
function reTicket(x,rows,cup){
  const want=k=>rows.find(r=>r.k===k)?.want,fl=rows.some(r=>r.k==='flavor')?want('flavor'):null,wantTops=rows.filter(r=>r.k==='topping').map(r=>r.want);
  const items=cup.items||[],placed=!!(cup.placed??items.length),g=k=>items.filter(i=>ing(x,i).group===k);
  const base=g('base')[0]??null,flavor=g('flavor')[0]??null,tops=g('topping');
  const out=[{k:'size',want:want('size'),ok:placed?cup.size===want('size'):null},{k:'base',want:want('base'),ok:base==null?null:base===want('base')}];
  if(fl)out.push({k:'flavor',want:fl,ok:flavor==null?null:flavor===fl,got:flavor});
  for(const w of wantTops)out.push({k:'topping',want:w,ok:tops.includes(w)?true:null});
  for(const e of [...(flavor&&!fl?[flavor]:[]),...tops.filter(k=>!wantTops.includes(k))])out.push({k:'extra',want:null,got:e,ok:false});
  out.push({k:'ice',want:want('ice'),ok:cup.ice==null?null:cup.ice===want('ice')},{k:'sugar',want:want('sugar'),ok:cup.sugar==null?null:cup.sugar===want('sugar')},
    {k:'seal',want:null,ok:cup.sealed?true:null});
  return out;
}
/** The task as it will be once the picks on their way land. */
function withLocal(t,x){
  const list=t&&t.cup?localOf(x,t.id):[];if(!list.length)return t;
  const cup=laid(x,t.cup,list);
  return {...t,cup,...t.ticket?.length?{ticket:reTicket(x,t.ticket,cup)}:{}};
}
/** Whether the server would take this pick on this (laid) task: game/boba.py _station's checks. If not, the pick
 * is sent the usual way and the server's answer says why. */
function canQuick(x,t,op,p){
  if(closedNow(x))return false;   // the server refuses every brewing step while the shop is closed
  const cup=t?.cup;if(!t||!t.known||!cup||cup.sealed)return false;
  if(op==='tea_cup')return ['M','L'].includes(p.size)&&!(cup.items||[]).length&&!(cup.placed&&cup.size===p.size)&&cupsOf(x)[p.size]>0;
  if(!cup.placed)return false;
  if(op==='tea_ice')return ICE.some(([v])=>v===p.level);
  if(op==='tea_sugar')return (B(x).sugars||[0,30,50,70,100]).includes(p.level);
  if(op!=='tea_add')return false;
  const i=ings(x).find(v=>v.id===p.item),s=i&&station(x,p.item),items=cup.items||[];
  if(!i||!s.unlocked||!(s.stock>0)||items.includes(p.item))return false;
  if(items.filter(k=>ing(x,k).group===i.group).length>=({base:1,flavor:1,topping:3}[i.group]||0))return false;
  return i.group==='base'||hasGroup(x,cup,'base');
}
/** Cups on the stack, less the one a pick took (and plus the one it put back). */
function cupsOf(x){
  const c={M:0,L:0,...B(x).cups||{}};
  for(const {op,payload:p} of x.ui.mtLocal||[]){
    const cup=op==='tea_cup'?serverTask(x,p.task)?.cup:null;
    if(!cup||cup.placed&&cup.size===p.size)continue;
    c[p.size]=Math.max(0,(c[p.size]||0)-1);if(cup.placed)c[cup.size]=(c[cup.size]||0)+1;
  }
  return c;
}
/** For tests/milk_tea_quick.mjs (the same verdicts as the server: tests/test_milk_tea_quick.py). */
export const quickParts={laid,reTicket,canQuick,withLocal};
/** The tapped tile (or the tile a bottom button stands for) lights up now, before anything is drawn again. */
function lightUp(op,p){
  if(typeof document==='undefined')return;
  const k=op==='tea_add'?p.item:op==='tea_cup'?'cup_'+p.size:op==='tea_ice'?'ice-'+p.level:'sugar-'+p.level;
  const el=document.querySelector(`#sheet[open] .mt-stations [data-k="${CSS.escape(String(k))}"]`);if(!el)return;
  if(op!=='tea_add')for(const o of el.parentElement?.querySelectorAll('.on')||[]){o.classList.remove('on');o.setAttribute('aria-pressed','false');}
  el.classList.add('on');el.setAttribute('aria-pressed','true');
}

/* ---------------------------------------------------------------- art */
function piece(k,top,i,color){
  const y=146-top*11-(i%2)*4,x0=36+(i*9)%48;
  if(['pearls','white_pearl','popping'].includes(k))return `<circle cx="${x0+4}" cy="${y}" r="${k==='popping'?4:4.4}" fill="${color}" stroke="#00000022"/>`;
  if(k==='red_bean')return `<ellipse cx="${x0+4}" cy="${y}" rx="3.4" ry="2.4" fill="${color}"/>`;
  if(['pudding','flan'].includes(k))return i===0?`<rect x="34" y="${y-6}" width="52" height="10" rx="4" fill="${color}"/>`:'';
  return `<rect x="${x0}" y="${y-4}" width="7" height="7" rx="2" fill="${color}" stroke="#00000018"/>`;
}
export function cupArt(x,cup,small=false){
  const size=small?64:132;
  if(!cup.placed)return `<svg class="mt-cup mt-cup-empty" width="${size}" height="${size*1.2}" viewBox="0 0 120 160" role="img" aria-label="Chưa có ly trên quầy"><path d="M22 34H98L90 150Q90 154 86 154H34Q30 154 30 150Z" fill="none" stroke="currentColor" stroke-width="2.4" stroke-dasharray="6 5" opacity=".45"/><text x="60" y="102" text-anchor="middle" font-size="${small?22:17}" font-weight="800" fill="currentColor" opacity=".7">Lấy ly</text></svg>`;
  const top=cup.size==='L'?18:34,items=cup.items||[];
  const base=items.map(k=>ing(x,k)).find(i=>i.group==='base'),flavor=items.map(k=>ing(x,k)).find(i=>i.group==='flavor');
  const tops=items.map(k=>ing(x,k)).filter(i=>i.group==='topping');
  const caps=tops.filter(i=>['foam','cheese'].includes(i.id)),bits=tops.filter(i=>!['foam','cheese'].includes(i.id));
  const shape=`M22 ${top}H98L90 150Q90 154 86 154H34Q30 154 30 150Z`;
  const liquid=base?`<rect x="20" y="${top+12}" width="84" height="150" fill="${base.color}"/>`:'';
  const tint=flavor?`<rect x="20" y="104" width="84" height="60" fill="${flavor.color}" opacity=".75"/>`:'';
  const cap=caps.map((c,i)=>`<rect x="20" y="${top+8+i*7}" width="84" height="9" fill="${c.color}"/>`).join('');
  const dots=bits.map((b,t)=>Array.from({length:8},(_,i)=>piece(b.id,t,i,b.color)).join('')).join('');
  const ice=Array.from({length:{none:0,little:2,normal:3,extra:5}[cup.ice]||0},(_,i)=>`<rect x="${34+(i*17)%46}" y="${top+22+(i%2)*14}" width="15" height="15" rx="4" fill="#ffffff8c" stroke="#ffffffcc" transform="rotate(${i*13-10} ${41+(i*17)%46} ${top+29})"/>`).join('');
  const film={perfect:'#f39ab8',ok:'#e9c4d0',burnt:'#b98a5e'}[cup.seal_q]||'#e9c4d0';
  const lid=cup.dome?`<path d="M20 ${top}Q60 ${top-30} 100 ${top}Z" fill="#ffffffb0" stroke="#8a6a50" stroke-width="2"/>`:cup.sealed?`<rect x="18" y="${top-4}" width="84" height="7" rx="3" fill="${film}" stroke="#8a6a50" stroke-width="1.6"/>${cup.seal_q==='perfect'?`<path d="M30 ${top-2}H52" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".8"/>`:''}`:`<rect x="18" y="${top-4}" width="84" height="7" rx="3" fill="none" stroke="#8a6a50" stroke-width="1.6" stroke-dasharray="4 3" opacity=".5"/>`;
  const straw=cup.sealed?`<rect x="66" y="${top-34}" width="9" height="46" rx="3" fill="#e8849f" transform="rotate(14 70 ${top})"/>`:'';
  return `<svg class="mt-cup" width="${size}" height="${size*1.2}" viewBox="0 0 120 160" role="img" aria-label="Ly size ${cup.size} đang pha"><defs><clipPath id="mtClip${small?'s':''}"><path d="${shape}"/></clipPath></defs><ellipse cx="60" cy="155" rx="36" ry="4" fill="#00000018"/>${straw}<path d="${shape}" fill="#fffdf8cc"/><g clip-path="url(#mtClip${small?'s':''})">${liquid}${tint}${cap}${dots}${ice}</g><path d="${shape}" fill="none" stroke="#8a6a50" stroke-width="2.4"/>${lid}<text x="60" y="${top+30}" text-anchor="middle" font-size="12" font-weight="800" fill="#5a4436" opacity=".55">${cup.size}</text></svg>`;
}
/** "Hồng trà · chưa có topping": what is in the cup right now, in words. */
function status(x,cup){
  if(!cup.placed)return 'Chưa lấy ly';
  const items=(cup.items||[]).map(k=>ing(x,k));
  const base=items.find(i=>i.group==='base'),flavor=items.find(i=>i.group==='flavor'),tops=items.filter(i=>i.group==='topping');
  const parts=[`Ly ${cup.size}`,base?base.name:'chưa có trà'];
  if(flavor)parts.push('vị '+low(flavor.name));
  parts.push(tops.length?tops.map(i=>low(i.name)).join(', '):'chưa có topping');
  parts.push(cup.ice?ICE_TEXT[cup.ice]:'chưa thêm đá');
  parts.push(cup.sugar!=null?cup.sugar+'% đường':'chưa chọn đường');
  if(cup.sealed)parts.push(cup.dome?'nắp cầu':'đã dán nắp');
  return parts.join(' · ');
}
const face=(t,x,size=58)=>t.walkin?`<span class="mt-face" style="--s:${size}px" aria-hidden="true">${x.esc(t.walkin.emoji||'🙂')}</span>`:`<span class="mt-face portrait" style="--s:${size}px" aria-hidden="true">${x.portrait(x.npc(t.npc),size)}</span>`;
const ring=(p,inner)=>`<span class="mt-ring ${p<40?'low':p<70?'mid':''}" style="--p:${Math.max(0,Math.min(100,p))}">${inner}</span>`;

/* ---------------------------------------------------------------- counter parts */
function hud(x){
  const b=B(x),mod=b.modifier||{},st=b.streak||0,c=clean();
  return `<div class="mt-hud" role="status">
    <span class="mt-chip${overtime(b)?' hot':''}">🕐 <b>${x.esc(b.clock||'08:00')}</b>${overtime(b)?' · tăng ca':''}</span>
    ${b.left!=null?`<span class="mt-chip" aria-label="Còn ${b.left} khách">${c?`👥 <b>${b.left}</b>`:`👥 Còn <b>${b.left}</b> khách`}</span>`:''}
    ${st>=2?`<span class="mt-chip hot" aria-label="${st} ly liên tiếp">🔥 <b>${st}</b>${c?'':' ly liên tiếp'}</span>`:''}
    <span class="mt-chip" aria-label="Tay nghề ${b.level||1}">⭐ ${c?'':'Tay nghề '}<b>${b.level||1}</b>${b.next_tier!=null?` · ${b.total||0}/${b.next_tier}${c?'':' ly'}`:''}</span>
    ${mod.title?`<span class="mt-chip mod" title="${x.esc(mod.title)}" aria-label="${x.esc(mod.title)}">${x.esc(mod.emoji||'')}${c?'':` ${x.esc(mod.title)}`}</span>`:''}${c?helpBtn('mt-counter','🧋 Quầy trà sữa',[{title:'Một ly đúng phiếu',body:'<ul class="ui-rows"><li>🥤 Lấy ly đúng cỡ</li><li>🫖 Rót trà nền, 🍑 siro, 🧋 topping</li><li>🧊 Đá, 🍯 đường như khách dặn</li><li>✅ Dán nắp rồi giao</li></ul>'},{title:'Ủ, nấu & đặt hàng',body:'<p>Ủ trà, nấu trân châu, đặt hàng đều trừ vào quỹ tiệm. Ủ trà, nấu trân châu mất 20 phút khi quán mở. Trà ủ và trân châu không để qua đêm.</p>'}],{tips:true,cls:'mt-help'}):''}
  </div>${(x.room.ops?.staff||[]).some(e=>e.status==='hired')?(c?tip('👥 Người phụ kiếm thêm xu khi khép ca; bạn vẫn tự pha từng ly.','Người phụ','p'):`<p class="muted small">👥 Người phụ kiếm thêm xu khi khép ca; bạn vẫn tự pha từng ly. ${x.button('Xem việc đội đang làm','staff',{},'ghost small')}</p>`):''}`;
}
function alerts(x){
  const b=B(x),out=[];
  if(b.sealer_off)out.push(`<p class="mt-alert warn">🔌 Cúp điện: máy dán nắp đang ngưng.${b.dome?' Đang dùng nắp cầu (1 xu mỗi ly).':''}</p>`);
  if(b.office)out.push(`<p class="mt-alert info">💼 Đơn văn phòng: ${b.office.done}/${b.office.count} ly · còn ${b.office.deadline_in} nhịp${b.office.bonus?` · thưởng ${b.office.bonus} xu nếu kịp`:''}</p>`);
  if(b.mess)out.push(`<div class="mt-alert warn row-inline"><span>💦 Quầy còn vệt trà đổ.</span>${jb(x,'🧽 Lau quầy','tea_wipe',{},'small')}</div>`);
  if(b.sealer?.state==='dirty')out.push(`<div class="mt-alert warn row-inline"><span>⚙️ Máy dán nắp bám keo (${b.sealer.wear} ly): khó dán đẹp.</span>${jb(x,'🧽 Lau máy · 20 phút','tea_clean',{},'small')}</div>`);
  const w=(b.warnings||[]).filter(v=>v.where==='stock');
  if(w.length)out.push(`<div class="mt-alert warn row-inline"><span>⚠ ${w.map(v=>x.esc(v.text)).join(' · ')}</span>${x.button('🧺 Mở kho','prepare',{},'small')}</div>`);
  return out.join('');
}
const overtime=b=>b.now?.is_open&&(b.now.time||'')>(b.now.close||'20:00');
const pending=(x,id)=>(B(x).orders||[]).filter(o=>o.item===id);
const soonest=(x,id)=>pending(x,id)[0];
/** What the guest ordered, as the server holds it now: the pinned ticket (game/boba.py ticket(t['needs'])), so a
 * usual order and an order already changed by a swap count right. The notebook's usual is only the guest's habit. */
function ordered(t){
  const r=t.ticket||[];
  if(!r.length)return t.needs?{flavor:t.needs.flavor||null,toppings:t.needs.toppings||[],size:t.needs.size}:null;
  return {flavor:r.find(v=>v.k==='flavor')?.want||null,toppings:r.filter(v=>v.k==='topping').map(v=>v.want),size:r.find(v=>v.k==='size')?.want};
}
/** tea_swap can offer something else for `k` (game/boba.py swap_to): a syrup can always be swapped or dropped;
 * a topping needs another one that is unlocked, on the menu, in stock and not already in the order. */
const swappable=(x,k,want,t=null)=>swapOk(x,t,k)&&(ing(x,k).group!=='topping'||(B(x).stations||[]).some(s=>s.group==='topping'&&s.id!==k&&!want.toppings.includes(s.id)&&s.unlocked&&s.on!==false&&s.stock>0));
/** The server's pre-check for tea_swap (game/boba.py _swap_rules, can.tea_swap[item]): only a bought syrup or topping
 * of the order. Pearls, foam or a tea the counter makes are never offered as a swap (it was refused 80 times). */
function swapOk(x,t,k){const c=t?.can?.tea_swap;return c&&k in c?c[k]===true:!station(x,k).made;}
/** The order in hand needs something the counter has run out of: offer a swap (only when the server can make one) or an express order. */
function outOfStock(t,x){
  if(!t?.known||t.cup?.sealed)return '';
  const b=B(x),want=ordered(t);if(!want)return '';
  const items=t.cup?.items||[],rows=[];
  // Made at the counter (pearls, foam, a tea): only when the counter cannot make it now (fund, shelf).
  const made=k=>station(x,k).made,blocked=k=>made(k)&&prepPlan(x,k).why;
  const miss=[...(want.flavor?[want.flavor]:[]),...want.toppings].filter(k=>!items.includes(k)&&station(x,k).stock===0&&(!made(k)||blocked(k)));
  for(const k of miss){
    const i=ing(x,k),o=soonest(x,k),swap=swappable(x,k,want,t),why=blocked(k);
    if(why){rows.push(`<div class="mt-alert warn mt-out"><span>🚫 Hết <b>${x.esc(low(i.name))}</b> · chưa ${x.esc(low(verb(k)))} thêm được: ${x.esc(low(why))}</span><span class="mt-out-btns">${swap?jb(x,'🙏 Mời khách đổi','tea_swap',{task:t.id,item:k},'small cream'):''}${why.startsWith('Thiếu')?topUp(x):''}</span></div>`);continue;}
    rows.push(`<div class="mt-alert warn mt-out"><span>🚫 Hết <b>${x.esc(low(i.name))}</b>${o?` · 📦 ${x.esc(o.eta_label)}`:swap?'':' · không còn topping khác để mời đổi'}</span><span class="mt-out-btns">${swap?jb(x,'🙏 Mời khách đổi','tea_swap',{task:t.id,item:k},'small cream'):''}${o?'':expressBtn(x,k,5,'small ghost')}</span></div>`);
  }
  // The tea itself (made here): out and the counter cannot brew more now.
  const base=(t.ticket||[]).find(r=>r.k==='base')?.want||t.needs?.base;
  if(base&&!hasGroup(x,t.cup||{},'base')&&station(x,base).stock===0&&blocked(base)){const why=blocked(base);
    rows.push(`<div class="mt-alert warn mt-out"><span>🚫 Hết <b>${x.esc(low(ing(x,base).name))}</b> · chưa ủ thêm được: ${x.esc(low(why))}</span><span class="mt-out-btns">${why.startsWith('Thiếu')?topUp(x):''}</span></div>`);}
  const cups=b.cups||{},size=want.size;
  if(!t.cup?.placed&&cups[size]===0){
    const o=soonest(x,'cup_'+size),other=size==='M'?'L':'M';
    rows.push(`<div class="mt-alert warn mt-out"><span>🚫 Hết ly <b>${size}</b>${o?` · 📦 ${x.esc(o.eta_label)}`:''}</span><span class="mt-out-btns">${cups[other]?jb(x,size==='M'?'🥤 Mời lên ly L, giữ giá':'🧋 Mời xuống ly M','tea_swap',{task:t.id,item:'cup_'+size},'small cream'):''}${o?'':expressBtn(x,'cup_'+size,1,'small ghost')}</span></div>`);
  }
  return rows.join('');
}
const unitCost=(x,id)=>id.startsWith('cup_')?(B(x).cup_pack?.cost||4):ing(x,id).cost||0;
// Rounded like the server (game/boba.py _order: Python round, ties to even), so the price shown is the price taken.
const orderCost=(x,id,qty,factor)=>Math.max(1,pyRound(qty*unitCost(x,id)*factor));
const expressCost=(x,id,qty)=>orderCost(x,id,qty,B(x).express?.factor||1.35);
/* A paid tap the server must refuse (game/boba.py _prepare/_order, engine.money "Chưa đủ xu…") is drawn
 * disabled with its reason ("Thiếu 3 xu", "Kho đầy 60/60", "Đang chờ 12/12 đơn") and never sent.
 * stations[].held, shelf_cap, max_orders and cup_cap come from the server (1.4.4); older servers: fallbacks. */
const fund=x=>Number(x.room?.money)||0;
const shelfCap=x=>B(x).shelf_cap||60;
const heldOf=(x,id)=>{const s=station(x,id);return s.held??s.stock??0;};
/** A batch made at the counter: five portions, or as many as the shop fund pays for and the shelf still takes
 * (the label says which); {why} when not even one can be made now. */
// The full batch's words as the guide names them ("[[Nấu +5]] trân châu", game/guide_content.py).
const FULL={'Nấu':'Nấu +5','Ủ':'Ủ +5','Đánh':'Đánh +5'};
function prepPlan(x,id){
  const unit=ing(x,id).cost||0,cap=shelfCap(x),held=heldOf(x,id),room=Math.max(0,cap-held),money=fund(x);
  if(!room)return {qty:0,cost:0,why:`Kho đầy ${held}/${cap}`,label:FULL[verb(id)]};
  const qty=Math.min(5,room,unit?Math.floor(money/unit):5);
  if(qty<1)return {qty:0,cost:unit,why:`Thiếu ${unit-money} xu`,label:`${verb(id)} +1 · ${unit} xu`,poor:true};
  return {qty,cost:qty*unit,why:'',label:`${qty===5?FULL[verb(id)]:`${verb(id)} +${qty}`} · ${qty*unit} xu`,poor:qty<5&&qty<room};
}
/** Why a supplier order of `qty` for `cost` xu would be refused now; '' when it goes through. */
function orderWhy(x,id,qty,cost){
  const b=B(x),n=(b.orders||[]).length,max=b.max_orders||12,p=b.pending?.[id]||0;
  if(n>=max)return `Đang chờ ${n}/${max} đơn`;
  if(id.startsWith('cup_')){
    const cap=b.cup_cap||120,pack=b.cup_pack?.qty||20,have=(b.cups?.[id.slice(4)]||0)+p*pack;
    if(have+qty*pack>cap)return have>=cap?`Chồng ly đầy ${have}/${cap}`:`Chồng ly chỉ còn chỗ ${cap-have} ly`;
  }else{
    const cap=shelfCap(x),have=heldOf(x,id)+p;
    if(have+qty>cap)return have>=cap?`Kho đầy ${have}/${cap}`:`Kho chỉ còn chỗ ${cap-have} phần`;
  }
  return cost>fund(x)?`Thiếu ${cost-fund(x)} xu`:'';
}
const whyBtn=(x,label,why,style='')=>`<button type="button" class="btn ${style}" disabled>${label}<small class="mt-why">${x.esc(why)}</small></button>`;
const prepBtn=(x,id,style='small')=>{const p=prepPlan(x,id);return p.why?whyBtn(x,p.label,p.why,style):jb(x,p.label,'tea_prepare',{item:id,qty:p.qty,confirm:true},style);};
const expressBtn=(x,id,qty,style)=>{const cost=expressCost(x,id,qty),label=`⚡ Gọi hỏa tốc · ${cost} xu`,why=orderWhy(x,id,qty,cost);
  return why?whyBtn(x,label,why,style):jb(x,label,'tea_order',{item:id,qty,supplier:'express',confirm:true},style);};
/** Story mode: the fund is short, so the free way out is named: move money from the wallet into the shop fund. */
const topUp=x=>x.state?.journey?.story?x.button('👛 Góp tiền từ ví vào quỹ','stView',{view:'wallet'},'small ghost'):'';
function eventCard(x){
  const ev=B(x).event;if(!ev)return '';
  const body=ev.stage==='open'
    ?`<p>${x.esc(ev.text)}</p><div class="mt-choices">${(ev.choices||[]).map(o=>`<button type="button" class="btn ${o.cost?'':'cream'}" ${cmdAttr(x,'tea_event',{choice:o.id})}${o.cost&&fund(x)<o.cost?' disabled':''}><span>${x.esc(o.label)}</span>${o.cost||o.hint?`<small>${o.cost?`${o.cost} xu`:''}${o.cost&&fund(x)<o.cost?` · thiếu ${o.cost-fund(x)} xu`:''}${o.cost&&o.hint?' · ':''}${o.hint?x.esc(o.hint):''}</small>`:''}</button>`).join('')}</div>`
    :`<p class="mt-result ${ev.good?'good':'bad'}">${x.esc(ev.result||'')}</p>${(ev.effects||[]).length?`<ul class="mt-effects">${ev.effects.map(e=>`<li>${x.esc(e)}</li>`).join('')}</ul>`:''}${jb(x,ev.good?'Tuyệt, làm tiếp':'Buồn ghê, làm tiếp','tea_event_ok',{},'primary')}`;
  // Shown as a modal over the counter so it is never scrolled out of view; focus is moved in by tick().
  return `<div class="mt-modal"><section class="mt-event ${ev.stage}" role="alertdialog" aria-modal="true" aria-labelledby="mtEvTitle"><h3 id="mtEvTitle"><span aria-hidden="true">${x.esc(ev.emoji||'❗')}</span> ${x.esc(ev.title)}</h3>${body}</section></div>`;
}
function appRow(t,x){
  const b=B(x),apps=x.room.tasks.filter(v=>open(v)&&v.app);
  if(!apps.length)return '';
  const turn=b.turn||0;
  return `<section class="mt-apps" aria-label="Đơn app"><h4>📱 Đơn app <small>app giữ ${b.app_fee||20}% mỗi đơn</small></h4><div class="mt-app-list">${apps.map(a=>{
    const leftTurns=a.app.deadline-turn,pct=Math.max(0,Math.min(100,leftTurns/a.app.span*100)),n=a.needs;
    const spec=n?`${ing(x,n.base).name} ${n.size}${n.toppings.length?` · ${n.toppings.length} topping`:''}`:'';
    return `<button type="button" class="mt-app ${a.id===t?.id?'on':''} ${leftTurns<0?'late':pct<35?'hurry':''}" ${pick(x,a.id)} aria-pressed="${a.id===t?.id}">
      <b>${x.esc(a.app.code)} · ${x.esc(a.customer)}</b><small>${x.esc(spec)}${a.cup?.sealed?' · ✓ đã dán nắp':''}</small>
      <span class="mt-bar" aria-hidden="true"><i style="width:${pct}%"></i></span><small>${leftTurns>=0?`Tài xế tới sau ${leftTurns} nhịp`:'Trễ giờ lấy đơn!'}</small></button>`;}).join('')}</div></section>`;
}
function queueRow(t,x){
  const seen=new Set(),chips=[];
  for(const v of x.room.tasks){
    if(!open(v)||v.app)continue;
    const g=v.group?.id;if(g&&seen.has(g))continue;if(g)seen.add(g);
    const sibs=g?x.room.tasks.filter(s=>s.group?.id===g):[v],first=sibs.find(open)||v;
    const active=sibs.some(s=>s.id===t?.id),p=x.room.life?.mode==='calm'?100:(first.patience??100);
    chips.push(`<button type="button" class="mt-guest ${active?'on':''}" ${pick(x,first.id)} aria-pressed="${active}" aria-label="${x.esc(first.customer)}, kiên nhẫn ${p}%${g?`, ${sibs.length} ly`:''}">
      ${ring(p,face(first,x,40))}<small>${x.esc(first.customer)}</small>${g?`<em class="mt-cups-badge">${sibs.length} ly</em>`:''}</button>`);
  }
  if(!chips.length||(chips.length<2&&!t?.app))return '';
  return `<section class="mt-queue" aria-label="Hàng chờ">${clean()?'':'<h4>Hàng chờ</h4>'}<div class="mt-queue-list">${chips.join('')}</div></section>`;
}
const usualText=(x,u)=>`${ing(x,u.base).name} size ${u.size}${u.flavor?`, vị ${low(ing(x,u.flavor).name)}`:''}, ${u.toppings.length?u.toppings.map(k=>low(ing(x,k).name)).join(', '):'không topping'}, ${u.sugar}% đường, ${ICE_TEXT[u.ice]}`;
/** The regulars' card: usual cup (for "như mọi khi"), what the shop has learned, and a greeting. */
function notebookFor(t,x){
  const row=(B(x).notebook||[]).find(r=>r.npc===t.npc);
  if(t.walkin||!row)return '';
  if(!row.usual&&t.usual&&t.known)return `<p class="muted small">Sổ khách quen chưa ghi ly của ${x.esc(t.customer)}. Hỏi lại khách nhé.</p>`;
  const notes=row.notes||[];
  if(!(t.usual&&t.known)&&!notes.length)return '';
  const greet=notes.length&&!t.greeted?jb(x,'👋 “Như mọi khi hả?”','tea_greet',{task:t.id},'small cream'):t.greeted?'<span class="tag green">✓ Đã chào khách quen</span>':'';
  return `<details class="mt-notebook" ${t.usual||!t.greeted?'open':''}><summary>📒 Sổ khách quen · ${x.esc(row.name)} · ghé ${row.visits} lần</summary>
    ${t.usual&&t.known&&row.usual?`<p>${x.esc(usualText(x,row.usual))}.</p>`:''}
    ${notes.length?`<ul class="mt-notes">${notes.map(n=>`<li><span aria-hidden="true">${x.esc(n.emoji)}</span> ${x.esc(n.text)}</li>`).join('')}</ul>`:''}
    ${row.next_note?`<small>Ghé đủ ${row.next_note} lần để biết thêm.</small>`:''}${greet?`<div class="mt-greet">${greet}</div>`:''}</details>`;
}
function customer(t,x,steps){
  // Order heard: the pinned ticket carries the order, the patience bar and the price.
  if(t.known&&(t.ticket||[]).length)return orderTicket(t,x,steps)+notebookFor(t,x);
  const calm=x.room.life?.mode==='calm',p=calm?100:(t.patience??100),b=B(x);
  const tags=[t.usual?'🔁 Như mọi khi':'',t.vip?'🎥 Đang quay video':'',t.office?'💼 Văn phòng':'',t.discount?`🏷️ Bớt ${t.discount} xu`:''].filter(Boolean);
  let meter;
  if(t.app){const left=t.app.deadline-(b.turn||0),pct=Math.max(0,Math.min(100,left/t.app.span*100));meter=`<div class="mt-patience app"><span>TÀI XẾ</span><div class="mt-bar"><i style="width:${pct}%"></i></div><small>${left>=0?`${left} nhịp`:'trễ'}</small></div>`;}
  else meter=`<div class="mt-patience ${p<40?'low':p<70?'mid':''}"><span>${clean()?'<span aria-label="Kiên nhẫn">⏳</span>':'KIÊN NHẪN'}</span><div class="mt-bar" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p}" aria-label="Kiên nhẫn"><i style="width:${p}%"></i></div><small>${calm?'thong thả':p+'%'}</small></div>`;
  const words=t.known?(t.order_text||t.opening):t.opening;
  return `<section class="mt-customer ${t.app?'is-app':''}">
    <div class="mt-who">${t.app?'<span class="mt-face" style="--s:58px" aria-hidden="true">🛵</span>':face(t,x)}<small>${x.esc(t.customer)}</small></div>
    <div class="mt-bubble">${t.app?`<span class="mt-ticket-head">PHIẾU APP ${x.esc(t.app.code)}</span>`:''}<p>“${x.esc(words)}”</p>
      ${tags.length?`<div class="mt-tags">${tags.map(v=>`<span>${x.esc(v)}</span>`).join('')}</div>`:''}
      ${meter}
      ${!t.known?jb(x,'👂 Nghe gọi món','ask',{task:t.id},'ghost mt-ask'):''}
      ${notebookFor(t,x)}
      <b class="mt-price">${t.quoted_price!=null?`${t.quoted_price} xu`:''}</b>
    </div></section>`;
}
function tile(x,o){
  const zero=o.count===0&&!o.locked;
  // Closed: a brewing tile (cup, tea, syrup, topping) is dimmed with "Mở ca trước"; restocking tiles still work.
  const shut=!o.locked&&closedNow(x)&&(o.cmd?BREW.has(o.cmd):!!o.k&&!/\b(off|restock)\b/.test(o.cls||''));
  const act=shut?shutAttrs():o.locked||o.disabled?'':o.cmd?cmdAttr(x,o.cmd,o.payload):'';
  return `<button type="button" class="mt-tile ${o.cls||''}${o.on?' on':''}${o.locked?' locked':''}${zero?' zero':''}${shut?' is-why':''}"${o.k?` data-k="${x.esc(o.k)}"`:''} ${act} ${!shut&&(o.locked||o.disabled)?'disabled':''} aria-pressed="${!!o.on}" aria-label="${x.esc(shut?`${o.name}: mở ca trước`:o.label||o.name)}">
    ${o.art||`<span class="mt-emo" aria-hidden="true">${o.emoji}</span>`}<b>${x.esc(o.name)}</b>${o.sub?`<small>${x.esc(o.sub)}</small>`:''}
    ${o.locked?`<small class="mt-lock">🔒 Cấp ${o.level}</small>`:o.count!=null?`<em class="mt-count${o.count===0?' zero':''}" aria-hidden="true">${o.count}</em>`:''}</button>`;
}
function shelf(t,x,group,title){
  const cup=t.cup,items=cup.items||[],b=B(x);
  const ready=t.known&&cup.placed&&!cup.sealed;
  const limit={base:1,flavor:1,topping:3}[group],have=items.filter(k=>ing(x,k).group===group).length;
  const needBase=group!=='base'&&!hasGroup(x,cup,'base');
  const all=ings(x).filter(i=>i.group===group),shut=all.filter(i=>!station(x,i.id).unlocked);
  // Off the menu (Bảng giá → Món đang bán): hidden unless this order still needs it or it is in the cup;
  // a chip shows them again, muted.
  const want=new Set((t.ticket||[]).map(r=>r.want)),off=all.filter(i=>!shut.includes(i)&&station(x,i.id).on===false&&!want.has(i.id)&&!items.includes(i.id));
  const showOff=!!x.ui.mtShowOff,list=all.filter(i=>!shut.includes(i)&&(showOff||!off.includes(i)));
  const offChip=off.length?`<button type="button" class="mt-lockchip mt-offchip" data-action="car:showoff" aria-pressed="${showOff}">🚫 ${off.length} món ngừng bán · ${showOff?'ẩn':'hiện'}</button>`:'';
  return `<section class="mt-shelf ${group}"><h4>${title}${group==='topping'?` <small>${have}/${limit}</small>`:''}</h4><div class="mt-grid">${list.map(i=>{
    const s=station(x,i.id),inCup=items.includes(i.id);
    if(off.includes(i))return tile(x,{k:i.id,name:i.name,emoji:i.emoji,count:s.stock,cls:'off',disabled:true,sub:'Ngừng bán',label:`${i.name}: ngừng bán`});
    if(s.stock===0&&!inCup){
      if(s.made){const p=prepPlan(x,i.id);
        if(p.why)return tile(x,{k:i.id,name:i.name,emoji:i.emoji,count:0,cls:'restock',disabled:true,sub:p.why,label:`${i.name} đã hết. Chưa ${low(verb(i.id))} thêm được: ${low(p.why)}`});
        return tile(x,{k:i.id,name:i.name,emoji:i.emoji,count:0,cls:'restock',cmd:'tea_prepare',payload:{item:i.id,qty:p.qty,confirm:true},sub:p.label,label:`${i.name} đã hết. ${verb(i.id)} ${p.qty} phần, ${p.cost} xu${s.fresh?', mất 20 phút':''}`});}
      const o=soonest(x,i.id);
      if(o)return tile(x,{name:i.name,emoji:i.emoji,count:0,cls:'restock wait',disabled:true,sub:`📦 ${o.eta_label}`,label:`${i.name} đã hết, hàng tới ${o.eta_label}`});
      const cost=expressCost(x,i.id,5),why=orderWhy(x,i.id,5,cost);
      if(why)return tile(x,{name:i.name,emoji:i.emoji,count:0,cls:'restock',disabled:true,sub:why,label:`${i.name} đã hết. Chưa gọi hỏa tốc được: ${low(why)}`});
      return tile(x,{name:i.name,emoji:i.emoji,count:0,cls:'restock',cmd:'tea_order',payload:{item:i.id,qty:5,supplier:'express',confirm:true},sub:`⚡ +5 · ${cost} xu`,label:`${i.name} đã hết. Gọi hỏa tốc 5 phần, ${cost} xu, tới trong 15–30 phút`});
    }
    const disabled=!ready||inCup||have>=limit||needBase;
    return tile(x,{k:i.id,name:i.name,emoji:i.emoji,count:s.stock,on:inCup,disabled,cls:s.tired?'tired':'',sub:s.tired?(s.tired>=s.stock?(i.group==='base'?'hơi chát':'hơi cứng'):`${s.tired} phần cũ`):'',cmd:'tea_add',payload:{task:t.id,item:i.id},label:`${i.name}, còn ${s.stock} phần${s.tired?`, ${s.tired} phần để lâu`:''}${inCup?', đã có trong ly':''}`});
  }).join('')}</div>${offChip||shut.length?`<div class="mt-chips">${offChip}${lockChip(x,shut)}</div>`:''}</section>`;
}
/** "🔒 3 món mở ở cấp 2–4": the locked tiles of a shelf in one line (names and levels in the tooltip). */
function lockChip(x,list){
  if(!list.length)return '';
  const lv=list.map(i=>station(x,i.id).level||i.level||1),lo=Math.min(...lv),hi=Math.max(...lv);
  const names=list.map((i,n)=>`${i.name} (cấp ${lv[n]})`).join(', ');
  return `<p class="mt-lockchip" title="${x.esc(names)}" aria-label="${x.esc(`Chưa mở: ${names}`)}">🔒 ${list.length}${clean()?' · ':' món mở ở '}cấp ${lo===hi?lo:`${lo}–${hi}`}</p>`;
}
/** The station the next step is at ('cups', 'base', 'flavor', 'topping', 'dials'); '' = none (all open). */
const STATION_OF={size:'cups',base:'base',flavor:'flavor',topping:'topping',ice:'dials',sugar:'dials'};
/** Only the station of the next step is open; the others are one line ("✓ 🫖 Trà nền · Matcha") that a
 * tap opens. With no step to follow (a usual order read from the notebook) every station stays open. */
function stations(t,x,steps){
  const cup=t.cup||{},items=cup.items||[],n=nextOf(steps),cur=n?STATION_OF[n.k]||'':'';
  const names=g=>items.filter(k=>ing(x,k).group===g).map(k=>ing(x,k).name).join(', ');
  const done=keys=>{const r=steps.filter(s=>keys.includes(s.k));return r.length&&r.every(s=>s.ok===true);};
  const parts=[['cups',()=>cupStack(t,x),`🥤 Chồng ly${cup.placed?` · Ly ${cup.size}`:''}`,['size']],
    ['base',()=>shelf(t,x,'base','🫖 Trà nền'),`🫖 Trà nền${names('base')?` · ${names('base')}`:''}`,['base']],
    ['flavor',()=>shelf(t,x,'flavor','🍑 Siro'),`🍑 Siro${names('flavor')?` · ${names('flavor')}`:''}`,['flavor']],
    ['topping',()=>shelf(t,x,'topping','🧋 Topping'),`🧋 Topping ${items.filter(k=>ing(x,k).group==='topping').length}/3${names('topping')?` · ${names('topping')}`:''}`,['topping']],
    ['dials',()=>dials(t,x),`🧊 Đá${cup.ice?` · ${ICE_TEXT[cup.ice]}`:''} · 🍯 Đường${cup.sugar!=null?` ${cup.sugar}%`:''}`,['ice','sugar']]];
  return parts.map(([k,html,sum,keys])=>{
    const key=`${t.id}|${cur}|${k}`,open=!steps.length||k===cur||!!x.ui.mtShelf?.[key];
    if(open)return html();
    return `<section class="mt-shelf ${k} mt-folded${done(keys)?' done':''}"><button type="button" class="mt-fold-sum" data-action="car:shelf" data-key="${x.esc(key)}" aria-expanded="false">${done(keys)?'✓ ':''}${x.esc(sum)}</button></section>`;
  }).join('');
}
const verb=id=>['pearls','white_pearl'].includes(id)?'Nấu':['foam','cheese'].includes(id)?'Đánh':'Ủ';
function cupStack(t,x){
  const b=B(x),cup=t.cup,cups=cupsOf(x);
  return `<section class="mt-shelf cups"><h4>🥤 Chồng ly</h4><div class="mt-grid two">${['M','L'].map(size=>{
    // Tea in the cup: neither size can be taken (game/boba.py tea_cup: "Ly đã có trà…"); the other one says why.
    const on=cup.placed&&cup.size===size,filled=!!(cup.items||[]).length,locked=filled&&!on&&!cup.sealed;
    if(!cups[size]){
      const o=soonest(x,'cup_'+size);
      if(o)return tile(x,{name:`Ly ${size}`,emoji:'🥤',count:0,cls:'restock wait',disabled:true,sub:`📦 ${o.eta_label}`,label:`Hết ly ${size}, hàng tới ${o.eta_label}`});
      const cost=expressCost(x,'cup_'+size,1),why=orderWhy(x,'cup_'+size,1,cost);
      if(why)return tile(x,{name:`Ly ${size}`,emoji:'🥤',count:0,cls:'restock',disabled:true,sub:why,label:`Hết ly ${size}. Chưa gọi hỏa tốc được: ${low(why)}`});
      return tile(x,{name:`Ly ${size}`,emoji:'🥤',count:0,cls:'restock',cmd:'tea_order',payload:{item:'cup_'+size,qty:1,supplier:'express',confirm:true},sub:`⚡ +${b.cup_pack?.qty||20} · ${cost} xu`,label:`Hết ly ${size}. Gọi hỏa tốc ${b.cup_pack?.qty||20} ly, ${cost} xu`});
    }
    return tile(x,{k:'cup_'+size,name:`Ly ${size}`,emoji:size==='L'?'🥤':'🧋',count:cups[size],on,disabled:!t.known||cup.sealed||filled,cmd:'tea_cup',payload:{task:t.id,size},sub:locked?'Đổ ly để đổi cỡ':'',label:`Ly size ${size}, còn ${cups[size]} ly${locked?'. Ly đang có trà: đổ ly rồi mới đổi cỡ':''}`});
  }).join('')}</div></section>`;
}
function dials(t,x){
  const cup=t.cup,ok=t.known&&cup.placed&&!cup.sealed,sugars=B(x).sugars||[0,30,50,70,100];
  const shut=closedNow(x);
  const seg=(cmd,val,label,on)=>`<button type="button" class="mt-seg ${on?'on':''}${shut?' is-why':''}" data-k="${cmd.slice(4)}-${val}" ${shut?shutAttrs():ok?cmdAttr(x,cmd,{task:t.id,level:val}):'disabled'} aria-pressed="${on}">${label}</button>`;
  return `<section class="mt-shelf dials"><h4>🧊 Đá</h4><div class="mt-segs four">${ICE.map(([v,l])=>seg('tea_ice',v,l,cup.ice===v)).join('')}</div>
    <h4>🍯 Đường</h4><div class="mt-segs five">${sugars.map(v=>seg('tea_sugar',v,v+'%',cup.sugar===v)).join('')}</div></section>`;
}
function sealer(t,x){
  const b=B(x),cup=t.cup,S=seal(x),auto=(b.upgrades||[]).some(u=>u.id==='sealer'&&u.owned);
  const ready=t.known&&cup.placed&&hasGroup(x,cup,'base')&&cup.sugar!=null&&cup.ice!=null&&!cup.sealed;
  if(cup.sealed)return `<div class="mt-sealer done ${cup.seal_q||''}"><b>${cup.dome?'🫧 Đã đậy nắp cầu':SEAL_TEXT[cup.seal_q]||SEAL_TEXT.ok}</b></div>`;
  if(auto)return `<div class="mt-sealer">${jb(x,'⚙️ Dán nắp tự động','tea_seal',{task:t.id},'cream full',!ready)}</div>`;
  if(b.sealer_off)return `<div class="mt-sealer">${b.dome?jb(x,'🫧 Đậy nắp cầu · 1 xu','tea_seal',{task:t.id},'cream full',!ready):'<p class="muted small">Máy dán nắp đang ngưng.</p>'}</div>`;
  const pct=v=>v/S.max*100,start=cup.seal_t||0,held=start?Math.max(0,x.now()-start):0;
  const zones=[['loose',0,S.loose],['ok',S.loose,S.good_lo],['good',S.good_lo,S.good_hi],['ok',S.good_hi,S.burn],['burn',S.burn,S.max]];
  return `<div class="mt-sealer ${start?'running':''}">
    <div class="mt-gauge" data-seal-start="${start||''}" data-s="${[S.loose,S.good_lo,S.good_hi,S.burn,S.max].join(',')}" aria-hidden="true">${zones.map(([k,a,z])=>`<i class="z ${k}" style="left:${pct(a)}%;width:${pct(z-a)}%"></i>`).join('')}<b class="mt-needle" style="transform:translateX(${Math.min(100,pct(held))}%)"></b></div>
    <small class="mt-gauge-label" aria-live="polite">${start?'Đang ép nhiệt…':ready?(clean()?`✨ +1 xu: nhả tay ở vùng xanh (${S.good_lo}–${S.good_hi} giây)`:`Nắp đẹp +1 xu: ép rồi nhả tay khi kim vào vùng xanh (${S.good_lo}–${S.good_hi} giây)`):clean()?'':'Pha xong trà, đá, đường rồi mới dán nắp'}</small>${!start&&!ready?tip('Pha xong trà, đá, đường rồi mới dán nắp','Dán nắp'):''}
    <div class="mt-seal-btns">${start?jb(x,'✋ Nhả tay!','tea_seal',{task:t.id},'cream big'):jb(x,'🔥 Ép nắp','tea_seal_start',{task:t.id},'cream',!ready)}
    ${start?'':jb(x,'Dán thường','tea_seal',{task:t.id},'ghost small',!ready)}</div>${start?'':wear(x)}</div>`;
}
/** Glue on the sealing plate: the green zone narrows until someone cleans it. */
function wear(x){
  const w=B(x).sealer;if(!w||w.state==='clean')return '';
  return `<p class="mt-wear ${x.esc(w.state)}"><span>${w.state==='dirty'?'⚠ Khuôn dán bẩn: vùng xanh chỉ còn một vạch.':'Khuôn dán bám keo: vùng xanh hẹp lại.'}</span>${jb(x,'🧽 Lau máy','tea_clean',{},'ghost small')}</p>`;
}
function finish(t,x){
  const cup=t.cup;
  return `<div class="mt-finish">${sealer(t,x)}
    <div class="mt-minor">${x.confirmCmd('🗑️ Đổ ly','tea_discard',{task:t.id},'Đổ ly đang làm? Nguyên liệu đã dùng được ghi hao hụt và tính là một lần làm lại.','ghost small',!(cup.placed||(cup.items||[]).length))}
    ${jb(x,'🔎 So phiếu','tea_check',{task:t.id},'ghost small',!t.known||!(cup.items||[]).length||cup.sealed)}</div>
    ${tip('So phiếu miễn phí: không tính lỗi, không trôi thời gian. Trao ly sai hoặc đổ làm lại vẫn tính lỗi.','🔎 So phiếu','p')}</div>`;
}
function nextStep(t,x,detail=true){
  if(!t)return 'Chờ khách ghé quầy';
  const ev=B(x).event;
  if(ev&&ev.stage==='open')return 'Trả lời chuyện đang xảy ra ở quầy trước đã';
  if(ev&&ev.stage==='done')return 'Đọc kết quả rồi làm tiếp';
  if(!t.known)return 'Nghe khách gọi món';
  const n=detail?t.needs:null,cup=t.cup,items=cup.items||[];
  if(cup.sealed)return t.app?'Giao ly cho tài xế':'Trao ly cho khách';
  if(!cup.placed)return n?`Lấy ly size ${n.size}`:'Lấy ly đúng cỡ khách gọi';
  if(!hasGroup(x,cup,'base'))return n?`Rót ${low(ing(x,n.base).name)}`:'Rót trà nền khách gọi';
  if(n){
    if(n.flavor&&!items.includes(n.flavor))return `Thêm siro ${low(ing(x,n.flavor).name)}`;
    const miss=n.toppings.find(k=>!items.includes(k));if(miss)return `Múc ${low(ing(x,miss).name)}`;
    if(cup.ice!==n.ice)return `Cho đá: ${ICE_TEXT[n.ice]}`;
    if(cup.sugar!==n.sugar)return `Đường ${n.sugar}%`;
  }else{
    if(cup.ice==null)return 'Chọn mức đá khách dặn';
    if(cup.sugar==null)return 'Chọn mức đường khách dặn';
  }
  return 'Ép nắp, nhả tay khi kim vào vùng xanh';
}

/* ---------------------------------------------------------------- next step (v4/guide.js) */
// A step's tap goes through actions.go like every counter tap (quiet, feedback next to the cup).
const run=(op,payload,label)=>({act:'car:go',data:{op,payload:JSON.stringify(payload),...QUICK.has(op)?{quick:'','own-busy':''}:{}},label});
const kSel=k=>`.mt-stations [data-k="${k}"]`;
const CRIT=new Set(['size','base','flavor','topping','extra']);
/** The order as steps, read from the server's ticket (game/boba.py ticket(): the same fields the
 * referee grades): cup size, tea, syrup, toppings, anything not ordered, ice, sugar, lid. On a first
 * task the bottom button does each step and the right tile glows; later it names the step and points
 * at the tile. Each step keeps its ticket row (`row`) for the pinned order ticket. */
function brewSteps(t,x){
  const b=B(x),cup=t.cup||{},items=cup.items||[],rows=t.ticket||[],id=t.id,first=firstTime(x),sealed=!!cup.sealed;
  if(!rows.length)return [];
  const redo={cmd:'tea_discard',payload:{task:id,confirm:true},confirm:'Ly này sai rồi. Đổ ly và pha lại từ đầu?',label:'🗑️ Đổ ly, pha lại'};
  // The right tile: tap it for the player on a first task, otherwise point at it.
  const tap=(k,op,payload,label)=>first?run(op,payload,label):{sel:kSel(k),label};
  // A needed ingredient that has run out: make more at the counter, or ask the guest to swap.
  // The counter cannot make more now (fund, shelf): the step points at the out-of-stock row that says why.
  const refill=k=>{const s=station(x,k),i=ing(x,k),want=ordered(t);
    if(s.made){const p=prepPlan(x,k);
      if(!p.why)return run('tea_prepare',{item:k,qty:p.qty,confirm:true},`${verb(k)} thêm ${x.esc(low(i.name))} · ${p.cost} xu`);
      return {sel:'.mt-out',label:want&&i.group!=='base'&&swappable(x,k,want,t)?`🙏 Hết ${x.esc(low(i.name))}: mời khách đổi`:`🚫 Hết ${x.esc(low(i.name))}: ${x.esc(low(p.why))}`};}
    if(want&&!swappable(x,k,want,t))return {sel:'.mt-out',label:soonest(x,k)?`📦 Hết ${x.esc(low(i.name))}: chờ hàng về`:`⚡ Hết ${x.esc(low(i.name))}: gọi hỏa tốc`};
    return {sel:'.mt-out',label:`🙏 Hết ${x.esc(low(i.name))}: mời khách đổi`};};
  const name=k=>low(ing(x,k).name),hasBase=hasGroup(x,cup,'base');
  const tops=items.filter(k=>ing(x,k).group==='topping').length;
  // Only a new cup fixes a wrong size with tea in it, a wrong tea or syrup, or something not ordered:
  // then that comes first, before more ingredients go into a cup that will be poured out anyway.
  const broken=rows.some(r=>r.ok===false&&(['base','flavor','extra'].includes(r.k)||(r.k==='size'&&items.length)));
  const pulseOf=(g,k)=>first&&g?.act?kSel(k):g?.sel?'.mt-out .btn':'';
  const steps=rows.filter(r=>r.k!=='seal').map(r=>{
    let label='',at='',go=null,pk='';
    if(r.k==='size'){
      label=`Lấy ly ${r.want}`;at=kSel('cup_'+r.want);pk='cup_'+r.want;
      if(r.ok!==true){
        if(items.length&&(r.ok===false||sealed))go=redo;
        else if(sealed){/* nothing to do on a sealed cup */}
        else if(!(b.cups||{})[r.want])go={sel:'.mt-out',label:`🙏 Hết ly ${r.want}: mời khách đổi cỡ`};
        else go=tap('cup_'+r.want,'tea_cup',{task:id,size:r.want},`${r.want==='L'?'🥤':'🧋'} Lấy ly ${r.want}`);
      }
    }else if(['base','flavor','topping'].includes(r.k)){
      const icon={base:'🫖',flavor:'🍑',topping:'🧋'}[r.k];
      label={base:`Rót ${name(r.want)}`,flavor:`Thêm siro ${name(r.want)}`,topping:`Múc ${name(r.want)}`}[r.k];at=kSel(r.want);pk=r.want;
      if(r.ok===false||(sealed&&r.ok!==true))go=redo;
      else if(r.ok==null&&!broken&&cup.placed&&(r.k==='base'||hasBase)&&(r.k!=='topping'||tops<3))
        go=station(x,r.want).stock?tap(r.want,'tea_add',{task:id,item:r.want},`${icon} ${x.esc(label)}`):refill(r.want);
    }else if(r.k==='extra'){
      label=`Bỏ ${name(r.got)} (khách không gọi)`;go=redo;
    }else{
      const want=r.want;
      label=r.k==='ice'?`Đá: ${ICE_TEXT[want]}`:`Đường ${want}%`;at=kSel(`${r.k}-${want}`);pk=`${r.k}-${want}`;
      if(!sealed&&cup.placed&&r.ok!==true)go=tap(`${r.k}-${want}`,'tea_'+r.k,{task:id,level:want},`${r.k==='ice'?'🧊':'🍯'} ${x.esc(label)}`);
    }
    const pulse=go===redo?'':r.k==='ice'||r.k==='sugar'?(first&&go?kSel(pk):''):pulseOf(go,pk);
    return {k:r.k,row:r,at,ok:r.ok,label,go,pulse};
  });
  // The lid: the bottom button always does a plain press (safe); the press-and-release game for a
  // perfect lid (+1 xu) stays on the sealer, and once it runs the bottom button lets go.
  const ready=steps.every(r=>r.ok===true),auto=(b.upgrades||[]).some(u=>u.id==='sealer'&&u.owned);
  let lid=null,note='';
  if(!sealed&&ready){
    if(auto)lid=run('tea_seal',{task:id},'⚙️ Dán nắp');
    else if(b.sealer_off){if(b.dome)lid=run('tea_seal',{task:id},'🫧 Đậy nắp cầu · 1 xu');else note='máy dán nắp đang ngưng, chờ có điện';}
    else if(cup.seal_t)lid=run('tea_seal',{task:id},'✋ Nhả tay!');
    else lid=run('tea_seal',{task:id},'✅ Dán nắp');
  }
  steps.push({k:'seal',at:'.mt-sealer',ok:sealed||null,label:'Dán nắp',note,go:lid});
  // After the lid only a wrong cup, tea, syrup or topping still matters (the guest hands it back).
  return sealed?steps.filter(r=>r.ok!==false||CRIT.has(r.k)):steps;
}
/** The pinned order ticket: "Ly 1: trà sữa size L, trân châu, 50% đường, ít đá", each part ticked
 * (✓), marked wrong (✗ needs a new cup, ! fix it on the dial) or still to do, in the order the guest
 * said it. Group orders get Ly 1…Ly n tabs; one patience bar and the price. Sticks to the top of the
 * counter while the stations scroll under it. */
/** A wrong part the player fixes where it is (a dial, or the size of an empty cup): amber "!", not "✗". */
const fixable=(t,r)=>r.ok===false&&(r.k==='ice'||r.k==='sugar'||(r.k==='size'&&!(t.cup?.items||[]).length));
const SAY=['base','size','flavor','topping','extra','sugar','ice'];
function orderTicket(t,x,steps){
  const b=B(x),calm=x.room.life?.mode==='calm',p=calm?100:(t.patience??100);
  const name=k=>low(ing(x,k).name);
  const text=r=>r.k==='base'?ing(x,r.want).name:r.k==='size'?`size ${r.want}`:r.k==='flavor'?`vị ${name(r.want)}`:r.k==='topping'?name(r.want)
    :r.k==='extra'?`${name(r.got)} (không gọi)`:r.k==='sugar'?`${r.want}% đường`:ICE_TEXT[r.want];
  const said=steps.filter(s=>s.row&&SAY.includes(s.k)).sort((a,c)=>SAY.indexOf(a.k)-SAY.indexOf(c.k));
  const chip=s=>{
    const r=s.row,fix=fixable(t,r);
    const cls=r.ok===true?'ok':r.ok===false?(fix?'warn':'bad'):'todo',mark=r.ok===true?'✓':r.ok===false?(fix?'!':'✗'):'';
    const why=r.ok===false?(fix?' (đang sai, chỉnh lại)':' (sai, cần đổ ly làm lại)'):r.ok===true?' (đã đúng)':' (chưa làm)';
    return `<li class="mt-req ${cls}"${closedNow(x)?"":todoAttrs(s)} aria-label="${x.esc(text(r)+why)}">${mark?`<b aria-hidden="true">${mark}</b>`:''}${x.esc(text(r))}</li>`;};
  const noTop=!said.some(s=>s.k==='topping'||s.k==='extra')?`<li class="mt-req none">không topping</li>`:'';
  const chips=said.map(chip),at=said.findIndex(s=>s.k==='sugar');
  chips.splice(at<0?chips.length:at,0,noTop);
  const g=t.group,sibs=g?x.room.tasks.filter(v=>v.group?.id===g.id).sort((a,c)=>a.group.i-c.group.i):[];
  const tabs=g?`<div class="mt-ticket-tabs" role="tablist" aria-label="Các ly trong đơn">${sibs.map(v=>{
    const done=v.status==='completed',gone=DONE.includes(v.status),on=v.id===t.id;
    return `<button type="button" role="tab" class="mt-cuptab ${on?'on':''} ${done?'done':''}" ${gone?'disabled':pick(x,v.id)} aria-selected="${on}">${done?'✓ ':''}Ly ${v.group.i}${v.cup?.sealed&&!done?' 🔒':''}</button>`;}).join('')}</div>`
    :`<b class="mt-ticket-who">${x.esc(t.app?`Đơn app ${t.app.code}`:t.customer)}</b>`;
  let meter;
  if(t.app){const left=t.app.deadline-(b.turn||0),pct=Math.max(0,Math.min(100,left/t.app.span*100));meter=`<div class="mt-patience app"><span>TÀI XẾ</span><div class="mt-bar"><i style="width:${pct}%"></i></div><small>${left>=0?`${left} nhịp`:'trễ'}</small></div>`;}
  else meter=`<div class="mt-patience ${p<40?'low':p<70?'mid':''}"><span>${clean()?'<span aria-label="Kiên nhẫn">⏳</span>':'KIÊN NHẪN'}</span><div class="mt-bar" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p}" aria-label="Kiên nhẫn"><i style="width:${p}%"></i></div><small>${calm?'thong thả':p+'%'}</small></div>`;
  const tags=[t.usual?'🔁 Như mọi khi':'',t.vip?'🎥 Quay video':'',t.office?'💼 Văn phòng':'',t.discount?`🏷️ Bớt ${t.discount} xu`:''].filter(Boolean);
  // Clean layout: the ticket no longer sticks (one pinned box: the bar); its digest is a header chip that opens it
  // over the counter once it has scrolled away. Every part of the order stays on the ticket itself.
  const okN=said.filter(s=>s.row.ok===true).length;
  return `${headChip('🧾',`${okN}/${said.length}`,'.mt-ticket',{label:`Phiếu gọi món: ${okN}/${said.length} đúng`,tone:said.some(s=>s.row.ok===false)?'bad':okN===said.length?'ok':''})}<section class="mt-ticket${t.app?' is-app':''}" aria-label="Phiếu gọi món">
    <div class="mt-ticket-top">${t.app?'<span class="mt-face" style="--s:34px" aria-hidden="true">🛵</span>':face(t,x,34)}${tabs}${tags.length?`<span class="mt-ticket-tags">${tags.map(v=>`<em>${x.esc(v)}</em>`).join('')}</span>`:''}<b class="mt-price">${t.quoted_price!=null?`${t.quoted_price} xu`:''}</b></div>
    <div class="mt-ticket-order"><b>Ly ${g?g.i:1}:</b><ul class="mt-reqs" aria-label="Món khách gọi">${chips.join('')}</ul></div>
    ${meter}</section>`;
}
/** The bottom line: how many steps the cup still needs ("Còn 3 bước"), and any part that is wrong.
 * The button under it names the step it does and the pinned ticket above shows every part, so the
 * steps are not listed again here (owner 03/10: "chữ ít thôi"). Before the order: nothing (the button says it). */
function todoLine(t,x,steps){
  if(!t.known)return '';
  if(!steps.length)return x.esc(status(x,t.cup||{}));
  const left=steps.filter(s=>s.ok!==true);
  if(!left.length)return t.app?'✓ Ly đã xong · giao cho tài xế':'✓ Ly đã xong · trao cho khách';
  return `<b>Còn ${left.length} bước</b>${left.filter(s=>s.ok===false).map(s=>{const fix=s.row&&fixable(t,s.row);
    return ` · <span class="${fix?'warn':'bad'}">${fix?'! ':'✗ '}${x.esc(s.label)}</span>`;}).join('')}`;
}
/** Python's round() (ties to even), so the app fee shown is the fee the server takes. */
const pyRound=v=>{const f=Math.floor(v),d=v-f;return d>0.5||(d===0.5&&f%2)?f+1:f;};
/** What the shop actually books for this cup, with the math when it is not the menu price. */
function netText(t,x){
  const q=t.quoted_price,off=t.discount||0,fee=t.app?pyRound(q*(B(x).app_fee||20)/100):0,net=Math.max(0,q-off-fee);
  return net===q?`${q} xu`:`${q}${off?` − bớt ${off}`:''}${fee?` − app ${fee}`:''} = ${net} xu`;
}
/** {steps, final} for the counter: the hint, the ticket rows and the bottom button all read it. */
function teaGuide(t,x){
  // Closed (after end_day the cup waits): the one step is opening the shift; the bar's main button does it.
  if(closedNow(x))return {steps:[{ok:null,label:'Mở ca trước',go:OPEN_GO}]};
  const ev=B(x).event,id=t.id;
  if(ev&&ev.stage==='open')return {steps:[{ok:null,label:'Chọn cách xử lý chuyện ở quầy',go:{sel:'.mt-event .mt-choices'},pulse:'.mt-event .mt-choices .btn'}]};
  if(ev&&ev.stage==='done')return {steps:[{ok:null,label:'Đọc kết quả rồi làm tiếp',go:run('tea_event_ok',{},'👍 Làm tiếp')}]};
  if(!t.known)return {steps:[{ok:null,label:'Nghe khách gọi món',go:run('ask',{task:id},'👂 Nghe gọi món'),pulse:'.mt-ask',at:'.mt-ask'}]};
  const steps=brewSteps(t,x),sealed=!!t.cup?.sealed;
  const label=`${t.app?'🛵 Giao tài xế':'🛎️ Giao món'}${t.quoted_price!=null?` · ${netText(t,x)}`:''}`;
  const go=nextOf(steps)?finalGo(steps,'tea_serve',{task:id},{question:'Khách có thể trả ly.',confirm:true}):run('tea_serve',{task:id,confirm:true},label);
  return {steps,final:{label,go,ready:sealed}};
}
function hintFor(t,x){
  const g=teaGuide(t,x);
  const final=g.final?.ready?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  return nextHint(x,g.steps.filter(s=>s.ok!==false||s.go),{final});
}

/* ---------------------------------------------------------------- care loop */
const TONE={ok:'✓',warn:'!',danger:'✗'};
/** Buttons a care row offers right where it is read. */
function careBtns(r,x,sheet=false){
  const b=B(x),open=!!x.room.open;
  if(r.id.startsWith('pot-')){
    const id=r.id.slice(4);
    return prepBtn(x,id)+(r.tone==='warn'&&station(x,id).tired?jb(x,'Đổ mẻ cũ','tea_toss',{item:id},'small ghost'):'');
  }
  if(r.id==='sealer'&&r.tone!=='ok'&&open)return jb(x,'🧽 Lau máy · 20 phút','tea_clean',{},'small');
  if(['tea','tea-empty','cups'].includes(r.id)&&!sheet)return x.button('🧺 Mở kho','prepare',{},'small ghost');
  return '';
}
function careRows(x,rows,sheet=false){
  return `<ul class="mt-care">${rows.map(r=>{const btns=careBtns(r,x,sheet);return `<li class="${x.esc(r.tone)}"><span class="mt-care-mark" aria-label="${r.tone==='ok'?'ổn':r.tone==='warn'?'cần để ý':'cần làm ngay'}">${TONE[r.tone]||'•'}</span><span class="mt-care-icon" aria-hidden="true">${x.esc(r.icon||'')}</span><span class="mt-care-text">${x.esc(r.text)}</span>${btns?`<span class="mt-care-btns">${btns}</span>`:''}</li>`;}).join('')}</ul>`;
}
/** Folded care list on the counter; opens by itself when something needs doing now. */
function careFold(x){
  const rows=B(x).care||[];if(!rows.length)return '';
  const bad=rows.filter(r=>r.tone!=='ok').length,danger=rows.some(r=>r.tone==='danger');
  const open=x.ui.mtCare??danger;
  return `<details class="mt-care-fold"${open?' open':''}><summary data-action="car:fold" data-key="mtCare"><span>🧋 Việc chăm quầy</span>${bad?`<em class="mt-care-count ${danger?'danger':''}">${bad}</em>`:'<em class="mt-care-count ok">ổn</em>'}</summary>${careRows(x,rows)}</details>`;
}
function orderRows(x){
  const list=B(x).orders||[];
  if(!list.length)return '<p class="muted small">Chưa có đơn nào đang giao.</p>';
  return `<div class="mt-rows">${list.map(o=>`<div class="mt-row mt-order ${o.late_note?'late':''}"><span class="mt-emo" aria-hidden="true">${x.esc(o.emoji)}</span><div class="grow"><b>${o.cups?`${o.qty} thùng ${x.esc(o.name)}`:`${o.qty} phần ${x.esc(o.name)}`}</b><small>${x.esc(o.supplier_name)} · dự kiến <b>${x.esc(o.eta_label)}</b> · ${x.esc(o.left_label)}</small>${o.late_note?`<small class="mt-late">⏰ ${x.esc(o.late_note)}</small>`:''}<span class="mt-bar" aria-hidden="true"><i style="width:${Math.round((o.progress||0)*100)}%"></i></span></div></div>`).join('')}</div>`;
}
/** The order form under a picked row: quantity − n +, then the bill (total and what the shop fund keeps),
 * the suppliers as compact chips and ONE order button, disabled with the reason when it cannot go
 * (orderWhy). The quantity starts at the old default (5 portions, 1 crate of cups); the player sets it. */
function supplierPicker(x,id){
  const b=B(x),cups=id.startsWith('cup_'),max=cups?5:20,quick=cups?[1,2,3]:[5,10,20],pack=b.cup_pack?.qty||20;
  const qty=Math.max(1,Math.min(max,Number(x.ui.mtQty)||quick[0]));
  const sups=b.suppliers||[],sells=s=>!s.items||s.items.includes(id),cheapest=Math.min(...sups.filter(sells).map(s=>s.factor));
  const sup=sups.find(s=>s.id===x.ui.mtSup&&sells(s))||sups.find(s=>s.id==='partner'&&sells(s))||sups.find(sells);
  if(!sup)return '<p class="muted small">Chưa nhà nào bán mặt hàng này.</p>';
  const cost=orderCost(x,id,qty,sup.factor),why=orderWhy(x,id,qty,cost);
  const step=(q,label,aria,off)=>`<button type="button" class="btn ghost" data-action="car:qty" data-qty="${q}" aria-label="${aria}"${off?' disabled':''}>${label}</button>`;
  const chips=quick.map(q=>`<button type="button" class="mt-seg ${q===qty?'on':''}" data-action="car:qty" data-qty="${q}" aria-pressed="${q===qty}">${q}</button>`).join('');
  const chip=s=>{const ok=sells(s),on=s.id===sup.id,tags=[s.factor===cheapest?'rẻ nhất':s.factor>1?'đắt':'',s.late>=12?'hay trễ':''].filter(Boolean);
    return `<button type="button" class="mt-sup-chip ${on?'on':''}" data-action="car:sup" data-sup="${x.esc(s.id)}" aria-pressed="${on}"${ok?'':' disabled'}><b><span aria-hidden="true">${x.esc(s.emoji)}</span> ${x.esc(s.name)}</b><small>${ok?`${x.esc(s.quote?.label||s.window)} · ×${String(s.factor).replace('.',',')}${tags.length?' · '+tags.map(v=>x.esc(v)).join(' · '):''}`:'Không bán mặt hàng này'}</small></button>`;};
  const go=why?whyBtn(x,`🚚 Đặt · ${cost} xu`,why,'primary'):jb(x,cups?`🚚 Đặt ${qty} thùng · ${cost} xu`:`🚚 Đặt ${qty} phần · ${cost} xu`,'tea_order',{item:id,qty,supplier:sup.id,confirm:true},'primary');
  return `<div class="mt-picker"><div class="mt-order-qty"><div class="mt-stepper" role="group" aria-label="Số lượng">${step(qty-1,'−','Bớt một',qty<=1)}<label class="mt-typed">${qtyBox({value:qty,min:1,max,label:cups?'Số thùng':'Số phần',go:step(QTY,'','',false),live:true})}<small aria-live="polite">${cups?`thùng · ${qty*pack} ly`:'phần'}</small></label>${step(qty+1,'+','Thêm một',qty>=max)}</div><div class="mt-qty-chips" role="group" aria-label="Chọn nhanh">${chips}</div></div>
    <p class="mt-bill" role="status"><b>Tổng ${cost.toLocaleString('vi-VN')} xu</b><span>Quỹ còn ${Math.max(0,fund(x)-cost).toLocaleString('vi-VN')} xu</span></p>
    <div class="mt-sup-chips" role="group" aria-label="Nhà cung cấp">${sups.map(chip).join('')}</div>
    <details class="mt-sup-more"><summary>${x.esc(sup.emoji)} ${x.esc(sup.name)}: giờ giao</summary><p>${x.esc(sup.window)}${sup.note?` · ${x.esc(sup.note)}`:''}</p></details>
    <div class="mt-order-go">${go}</div></div>`;
}
/* ---------------------------------------------------------------- prepare */
const TABS=[['stock','🧺','Kho'],['upgrade','🛠️','Nâng cấp'],['price','🏷️','Giá bán'],['reviews','⭐','Đánh giá'],['recap','📒','Tổng kết']];
function board(x){
  const b=B(x),pr=b.prices||{},prices=x.room.life?.prices||{};
  const bases=ings(x).filter(i=>i.group==='base');
  return `<div class="chalkboard mt-board"><h2>🧋 Menu hôm nay</h2><div class="chalk-columns">${bases.map(i=>{const s=station(x,i.id),off=s.on===false;return `<div class="${s.unlocked?'':'locked'}${off?' off':''}"><span>${x.esc(i.name)}</span><b>${!s.unlocked?`🔒 cấp ${s.level}`:off?'ngừng bán':`${prices[i.id]||pr.base?.[i.id]||30} xu`}</b></div>`;}).join('')}</div>
    <p class="center">Siro +${pr.flavor??6} xu · Topping +${pr.topping??5} xu · Size L +${pr.size_l??7} xu</p></div>`;
}
/** Thresholds for the "Cần nhập / cần ủ" group: cups as the server warns (boba.warnings), a few portions for the rest. */
const LOW_CUPS=5,LOW_PORTIONS=3;
/** Kho: what needs making or buying first ("Cần nhập / cần ủ": out, low, old or going off today), then the
 * pots and the goods to buy, the locked ones folded into one line, the deliveries on the way, the care
 * list and the how-to folded. A picked row opens its order form right under it. */
function stockTab(x){
  const b=B(x),pantry=x.room.life?.pantry||[],day=x.room.day,cups=b.cups||{},now=b.now||{},pick=x.ui.mtItem;
  const lot=id=>{const l=pantry.filter(v=>v.item===id&&v.qty>0&&v.expires>=day);return l.length?Math.min(...l.map(v=>v.expires)):null;};
  const batch=id=>(b.batches||[]).find(v=>v.item===id);
  const all=ings(x),madeIds=all.filter(i=>station(x,i.id).made),boughtIds=all.filter(i=>!station(x,i.id).made);
  const shut=all.filter(i=>!station(x,i.id).unlocked);
  // Made at the counter: brewed pots, pearl batches, whipped foam.
  const madeRow=i=>{
    const s=station(x,i.id),bt=batch(i.id),first=bt?.lots?.[0],exp=lot(i.id);
    const fresh=s.fresh?(first?`${first.made?`${verb(i.id)} ${first.made} · `:''}<span class="${first.band==='fresh'?'':'warn'}">${x.esc(first.word)}${first.band==='fresh'&&first.good_until?` tới ${first.good_until}`:first.ok_until?` · bỏ lúc ${first.ok_until}`:''}</span>${bt.lots.length>1?` · ${bt.lots.length} mẻ`:''}`:'chưa có mẻ nào'):(exp!=null?`dùng hết ngày ${exp}`:'');
    if(s.on===false&&!s.stock)return `<div class="mt-row off"><span class="mt-emo" aria-hidden="true">${i.emoji}</span><div class="grow"><b>${x.esc(i.name)}</b><small>🚫 Ngừng bán · không cần ${verb(i.id).toLowerCase()}</small></div></div>`;
    return `<div class="mt-row ${s.stock===0?'empty':''}${s.on===false?' off':''}"><span class="mt-emo" aria-hidden="true">${i.emoji}</span><div class="grow"><b>${x.esc(i.name)}${s.on===false?' <small>· ngừng bán</small>':''}</b><small><span class="mt-count-inline ${s.stock===0?'zero':''}">Còn ${s.stock}</span>${fresh?` · ${fresh}`:''}</small></div><div class="mt-row-btns">${s.tired?jb(x,'Đổ mẻ cũ','tea_toss',{item:i.id},'small ghost'):''}${prepBtn(x,i.id)}</div></div>`;
  };
  // Bought from suppliers: cups, syrups, jellies…
  const buyRow=(id,emoji,name,have,sub,off=false)=>{
    const o=pending(x,id),on=pick===id;
    return `<div class="mt-buy ${on?'on':''}"><div class="mt-row ${have===0&&!off?'empty':''}${off?' off':''}"><span class="mt-emo" aria-hidden="true">${emoji}</span><div class="grow"><b>${x.esc(name)}</b><small><span class="mt-count-inline ${have===0?'zero':''}">Còn ${have}</span>${sub?` · ${sub}`:''}${o.length?` · 📦 ${x.esc(o[0].eta_label)}`:''}</small></div><button type="button" class="btn small ${on?'primary':''}" data-action="car:pick" data-item="${x.esc(id)}" aria-expanded="${on}">${on?'Đóng':'Đặt hàng'}</button></div>${on?supplierPicker(x,id):''}</div>`;
  };
  const cupRow=size=>buyRow('cup_'+size,'🥤',`Ly ${size}`,cups[size]||0,`${b.cup_pack?.qty||20} ly/thùng`);
  const boughtRow=i=>{const s=station(x,i.id),exp=lot(i.id);
    return buyRow(i.id,i.emoji,i.name,s.stock,`${s.on===false?'🚫 ngừng bán · ':''}${i.cost} xu/phần${exp!=null&&exp<=day+1?` · ${exp<=day?'hết hạn tối nay':'dùng hết ngày mai'}`:''}`,s.on===false);};
  // What needs doing first: on the menu and out, low, past its best, or going off tonight.
  const madeOpen=madeIds.filter(i=>!shut.includes(i)),boughtOpen=boughtIds.filter(i=>!shut.includes(i));
  const needMade=madeOpen.filter(i=>{const s=station(x,i.id);return s.on!==false&&(s.stock===0||s.tired>0);});
  const needCups=['M','L'].filter(size=>(cups[size]||0)<LOW_CUPS);
  const needBought=boughtOpen.filter(i=>{const s=station(x,i.id),exp=lot(i.id);return s.on!==false&&(s.stock<=LOW_PORTIONS||(exp!=null&&exp<=day));});
  // A hint from yesterday's book (boba history), never a number put into the form.
  const last=(b.history||[]).filter(h=>Number(h.day)<Number(day)).at(-1);
  const yday=last&&last.served!=null?`<p class="mt-need-hint"><span>📒 Ngày ${last.day} bán ${last.served} ly</span>${last.dumped?`<span>🗑️ Bỏ cuối ca ${last.dumped} phần</span>`:''}${b.left!=null?`<span>👥 Hôm nay còn ${b.left} khách</span>`:''}</p>`:'';
  const needN=needMade.length+needCups.length+needBought.length;
  const need=needN?`<section class="mt-need" aria-labelledby="mtNeedH"><h3 class="section-title" id="mtNeedH">⚠ Cần nhập / cần ủ <small>${needN} món</small></h3>${yday}<div class="mt-rows">${needMade.map(madeRow).join('')}${needCups.map(cupRow).join('')}${needBought.map(boughtRow).join('')}</div></section>`:'';
  const restMade=madeOpen.filter(i=>!needMade.includes(i)),restCups=['M','L'].filter(s=>!needCups.includes(s)),restBought=boughtOpen.filter(i=>!needBought.includes(i));
  const lockedFold=shut.length?(()=>{const lv=shut.map(i=>station(x,i.id).level||i.level||1),lo=Math.min(...lv),hi=Math.max(...lv);
    return `<details class="mt-locked"><summary>🔒 ${shut.length} món mở ở tay nghề cấp ${lo===hi?lo:`${lo}–${hi}`}</summary><p>${shut.map((i,n)=>`${x.esc(i.emoji)} ${x.esc(i.name)} (cấp ${lv[n]})`).join(' · ')}</p></details>`;})():'';
  const night=(b.night||[]).length?`<div class="mt-night">${b.night.map(l=>`<p>${x.esc(l)}</p>`).join('')}</div>`:'';
  const wait=x.room.open&&(b.orders||[]).length?jb(x,'⏳ Chờ thêm 20 phút','tea_wait',{},'ghost small'):'';
  // The money every paid button here comes out of, in sight; when it cannot pay for a full batch of
  // something on the menu, the ways that cost nothing are named.
  const money=fund(x),J=x.state?.journey,wallet=J?.story&&Number.isFinite(Number(J.wallet))?Number(J.wallet):null;
  const poor=all.some(i=>{const s=station(x,i.id);return s.made&&s.unlocked&&s.on!==false&&prepPlan(x,i.id).poor;});
  const clock=now.is_open?`🕑 <b>${x.esc(now.time||b.clock||'')}</b>${overtime(b)?' · tăng ca, nhà cung cấp đã nghỉ':''}`:`🕑 Đóng cửa · mở lại ${x.esc(now.open||'08:00')}`;
  const purse=`<div class="mt-fund${poor?' poor':''}" role="status"><p>${poor?`🏪 Quỹ tiệm <b>${money.toLocaleString('vi-VN')} xu</b> · `:''}${clock}</p>${poor?`<p class="mt-fund-tip">Quỹ mỏng: bán ly từ hàng còn trong kho để có thêm xu, tắt bớt món ở 🏷️ Giá bán${wallet>0?', hoặc góp tiền từ ví vào quỹ':''}.</p>${wallet>0?topUp(x):''}`:''}</div>`;
  const nOrd=(b.orders||[]).length,maxOrd=b.max_orders||12;
  const care=b.care||[],bad=care.filter(r=>r.tone!=='ok').length,danger=care.some(r=>r.tone==='danger');
  const careBox=care.length?`<details class="mt-care-fold"${x.ui.mtPrepCare??danger?' open':''}><summary data-action="car:fold" data-key="mtPrepCare"><span>🧋 Việc chăm quầy</span>${bad?`<em class="mt-care-count ${danger?'danger':''}">${bad}</em>`:'<em class="mt-care-count ok">ổn</em>'}</summary>${careRows(x,care,true)}</details>`:'';
  return `${purse}${night}${need}
    ${restMade.length?`<h3 class="section-title">🫖 Nồi, bình & mẻ hôm nay</h3><div class="mt-rows">${restMade.map(madeRow).join('')}</div>`:''}
    ${restCups.length||restBought.length?`<h3 class="section-title">🛒 Đặt hàng</h3><div class="mt-rows">${restCups.map(cupRow).join('')}${restBought.map(boughtRow).join('')}</div>`:''}${lockedFold}
    ${nOrd?`<h3 class="section-title">📦 Đang giao <small>${nOrd}/${maxOrd} đơn${nOrd>=maxOrd?' · đợi hàng tới rồi mới đặt thêm':''}</small></h3>${orderRows(x)}${wait?`<p class="row wrap">${wait}</p>`:''}`:''}
    ${careBox}
    <details class="mt-how"><summary>❔ Ủ, nấu & đặt hàng thế nào?</summary><p class="muted small">Ủ trà, nấu trân châu, đặt hàng đều trừ vào quỹ tiệm. Ủ trà, nấu trân châu mất 20 phút khi quán mở; làm trước giờ mở cửa thì không mất thời gian. Trà ủ và trân châu không để qua đêm.</p><p class="muted small">Trả tiền khi đặt. Mỗi nhà giao một kiểu: hỏa tốc 15–30 phút, xe bốn chuyến mỗi ngày, chợ chiều nay hoặc sáng mai, xưởng 1–2 ngày.</p></details>`;
}
function upgradeTab(x){
  return `<div class="mt-upgrades">${(B(x).upgrades||[]).map(u=>`<article class="mt-upgrade ${u.owned?'owned':''}"><span class="mt-emo big" aria-hidden="true">${x.esc(u.emoji)}</span><div class="grow"><h4>${x.esc(u.name)}</h4><p>${x.esc(u.text)}</p></div>${u.owned?'<span class="tag green">✓ Đã lắp</span>':!u.ready?`<span class="tag">🔒 Tay nghề cấp ${u.level}</span>`:fund(x)<u.price?whyBtn(x,`Lắp · ${u.price} xu`,`Thiếu ${u.price-fund(x)} xu`,'small'):x.confirmCmd(`Lắp · ${u.price} xu`,'tea_upgrade',{id:u.id},`Lắp ${u.name} với giá ${u.price} xu?`,'primary small')}</article>`).join('')}</div>`;
}
/** "Món đang bán": one switch per tea, syrup and topping, on the same two-column leader rows as the menu.
 * Off: new customers never order it and the counter needs none of it in stock. The last tea stays on. */
function menuPanel(x){
  const teas=ings(x).filter(i=>i.group==='base'&&station(x,i.id).unlocked&&station(x,i.id).on!==false).length;
  const off=ings(x).filter(i=>station(x,i.id).on===false).length;
  const row=i=>{
    const s=station(x,i.id),on=s.on!==false,last=on&&i.group==='base'&&teas<=1;
    const ctl=!s.unlocked?`<b class="mt-menu-lock">🔒 cấp ${s.level}</b>`
      :`<button type="button" role="switch" class="mt-switch" data-item="${x.esc(i.id)}" aria-checked="${on}" aria-label="${x.esc(`Bán ${i.name}`)}" ${last?'disabled title="Quán cần bán ít nhất một loại trà nền"':cmdAttr(x,'tea_menu',{item:i.id,on:!on})}><i aria-hidden="true"></i><small>${on?'Đang bán':'Ngừng'}</small></button>`;
    return `<div class="${on?'':'off'}${s.unlocked?'':' locked'}"><span><span aria-hidden="true">${x.esc(i.emoji)}</span> ${x.esc(i.name)}</span>${ctl}</div>`;};
  const group=(g,title)=>`<h4>${title}</h4><div class="chalk-columns mt-menu-cols">${ings(x).filter(i=>i.group===g).map(row).join('')}</div>`;
  return `<section class="mt-menu" aria-labelledby="mtMenuH"><h3 class="section-title" id="mtMenuH">🧾 Món đang bán${off?` <small>· ${off} món ngừng bán</small>`:''}</h3>
    <p class="muted small">Tắt món không muốn bán: khách mới sẽ không gọi, quầy cũng không cần nhập. Ly khách đã gọi vẫn pha như cũ. Luôn giữ ít nhất một loại trà nền.</p>
    ${group('base','🫖 Trà nền')}${group('flavor','🍑 Siro')}${group('topping','🧋 Topping')}</section>`;
}
/** The trial price band of a base tea, as life_price checks it (game/boba.py prices.range; 75%–125%, Python rounding). */
const priceBand=(x,id)=>{const b=B(x).prices||{},g=b.base?.[id]||30;return b.range?.[id]||[pyRound(g*.75),pyRound(g*1.25)];};
const clampPrice=(x,id,v)=>{const [lo,hi]=priceBand(x,id),n=Math.round(Number(v));return Number.isFinite(n)&&String(v).trim()!==''?Math.min(hi,Math.max(lo,n)):null;};
function priceTab(x){
  const b=B(x),base=b.prices?.base||{},prices=x.room.life?.prices||{},closed=!x.room.open;
  return `${board(x)}${menuPanel(x)}<p class="muted">Đổi giá trà nền trước khi mở cửa.</p><div class="price-editor">${ings(x).filter(i=>i.group==='base').map(i=>{
    const s=station(x,i.id),g=base[i.id]||30,v=prices[i.id]||g,[lo,hi]=priceBand(x,i.id);
    return `<div><strong>${x.esc(i.emoji)} ${x.esc(i.name)}${s.unlocked?'':' 🔒'}<small class="mt-price-band">${lo}–${hi} xu</small></strong><input class="input" type="number" inputmode="numeric" id="price-${i.id}" data-price="${x.esc(i.id)}" min="${lo}" max="${hi}" step="1" value="${v}" data-preserve aria-label="Giá ${x.esc(i.name)}, từ ${lo} đến ${hi} xu" ${closed?'':'disabled'}>${x.button('Lưu giá','car:price',{item:i.id},'small',!closed)}</div>`;}).join('')}</div>`;
}
function reviewsTab(x){
  const posts=(x.room.feed||[]).filter(p=>p.stars),dist=[5,4,3,2,1].map(s=>[s,posts.filter(p=>p.stars===s).length]),max=Math.max(1,...dist.map(d=>d[1]));
  return `<div class="mt-rating"><div class="mt-rating-big"><strong>${x.room.rating||'—'}</strong><small>${posts.length} đánh giá</small></div><div class="mt-dist">${dist.map(([s,n])=>`<div><span>${s}★</span><i><b style="width:${n/max*100}%"></b></i><small>${n}</small></div>`).join('')}</div></div>
    <div class="mt-reviews">${posts.slice(0,6).map(p=>`<article><div class="row spread"><b>${x.esc(p.author||'Khách')}</b><span class="mt-stars" aria-label="${p.stars} sao">${'★'.repeat(p.stars)}${'☆'.repeat(5-p.stars)}</span></div><p>${x.esc(p.text)}</p><small>Ngày ${p.day}</small></article>`).join('')||'<p class="muted">Chưa có đánh giá nào.</p>'}</div>${x.button('Đọc & trả lời đánh giá','feedback',{},'ghost')}`;
}
function recapTab(x){
  const b=B(x),h=(b.history||[]).slice().reverse(),pct=b.next_tier?Math.min(100,(b.total||0)/b.next_tier*100):100;
  return `<div class="mt-tier"><b>⭐ Tay nghề cấp ${b.level||1}</b><div class="mt-bar"><i style="width:${pct}%"></i></div><small>${b.next_tier!=null?`${b.total||0}/${b.next_tier} ly để lên cấp: mở thêm trà, topping và nâng cấp mới`:'Đã lên bậc cao nhất'}</small></div>
    ${h.length?`<div class="mt-table" role="table" aria-label="Các ngày gần đây"><div role="row" class="head"><span>Ngày</span><span>Ly</span><span>Chuẩn</span><span>Bỏ về</span><span>Thu</span></div>${h.map(r=>`<div role="row"><span>${r.day}</span><span>${r.served}</span><span>${r.perfect}</span><span>${r.walkouts}</span><span>${r.revenue} xu</span></div>`).join('')}</div>`:'<p class="muted">Khép ca đầu tiên để xem tổng kết từng ngày.</p>'}
    <h3 class="section-title">📒 Sổ khách quen</h3><div class="mt-rows">${(b.notebook||[]).map(r=>`<div class="mt-row mt-regular"><span class="mt-emo" aria-hidden="true">📒</span><div class="grow"><b>${x.esc(r.name)}</b><small>${r.usual?`${x.esc(ing(x,r.usual.base).name)} ${r.usual.size} · ${r.usual.sugar}% đường · ${ICE_TEXT[r.usual.ice]}`:'Chưa ghi ly quen'} · ghé ${r.visits} lần</small>${(r.notes||[]).map(n=>`<small class="mt-note">${x.esc(n.emoji)} ${x.esc(n.text)}</small>`).join('')}${r.next_note?`<small class="muted">Ghé đủ ${r.next_note} lần để biết thêm một điều.</small>`:''}</div></div>`).join('')}</div>`;
}
/** Chuẩn bị opens on the work: a compact head (shop name, a one-line level bar), the day and its missions
 * folded into one line (open by itself when a gift can be claimed), the warnings, then the tabs (Kho first). */
function prepare(x,tab){
  const c=x.room,b=B(x),mod=b.modifier||{},w=b.warnings||[],tm=b.tomorrow||{};
  tab=TABS.some(v=>v[0]===tab)?tab:'stock';
  const panel={stock:stockTab,upgrade:upgradeTab,price:priceTab,reviews:reviewsTab,recap:recapTab}[tab](x);
  const list=c.life?.goals||[],n=list.length,claim=list.some(g=>!g.claimed&&g.current>=g.goal),done=list.filter(g=>g.claimed||g.current>=g.goal).length;
  const goals=list.map(g=>`<li class="${g.claimed?'done':''}"><div><strong>${x.esc(g.title)}</strong><small>Thưởng ${g.reward} xu</small></div><div class="prep-goal-end">${g.claimed?'<span class="done-mark">✓ Đã nhận</span>':g.current>=g.goal?jb(x,'Nhận quà','life_goal',{goal:g.id},'small primary'):`<b>${Math.min(g.current,g.goal)}/${g.goal}</b>`}</div></li>`).join('');
  const dayNo=x.state?.journey?.story?x.state.journey.life_day:c.day,today=c.open?mod:tm,lv=b.level||1,made=b.total||0,pct=b.next_tier?Math.min(100,(b.total||0)/b.next_tier*100):100;
  const open=x.ui.mtToday??claim;
  const todayLine=`<details class="mt-today"${open?' open':''}><summary data-action="car:fold" data-key="mtToday"><span class="mt-today-em" aria-hidden="true">${x.esc(today.emoji||'🌤️')}</span><span class="mt-today-t">${x.esc(today.title||'Hôm nay')}</span>${n?`<span class="mt-today-q">· Nhiệm vụ ${done}/${n}</span>`:''}${claim?'<span class="mt-today-gift" aria-label="Có quà để nhận">🎁</span>':''}</summary>
      <div class="prep-today-grid"><div class="prep-weather"><div><p>${x.esc(c.open?(mod.text||''):(tm.advice||''))}</p></div></div>${c.open&&tm.title&&(b.care||[]).some(r=>r.id==='tomorrow')?`<div class="prep-weather mt-tomorrow"><span class="prep-weather-em" aria-hidden="true">${x.esc(tm.emoji)}</span><div><strong>Mai: ${x.esc(tm.title)}</strong><p>${x.esc(tm.advice)}</p></div></div>`:''}${goals?`<div class="prep-quests"><h3 class="prep-sub">🌞 Nhiệm vụ hôm nay</h3><ul class="prep-goals">${goals}</ul></div>`:''}</div></details>`;
  return `<div class="preparation-topline">${x.button('← Hành trình','home',{},'ghost small')}<span>CHUẨN BỊ NGÀY ${c.day}</span>${x.button(x.icon('x',20),'close',{},'ghost small')}</div>
  <div class="life-content career-job mt mt-prep prep-v2">
    <header class="prep-head mt-prep-head"><div class="prep-id"><span class="sign-kicker">QUẦY TRÀ SỮA</span><h1>${x.esc(c.life?.shop_name||'Trà Mây & Trân Châu')}</h1></div><div class="mt-level"><span>⭐ Cấp ${lv} · ${made} ly</span><div class="prep-xp" aria-hidden="true"><i style="width:${pct}%"></i></div></div><button type="button" class="btn small ghost mt-rename" data-action="expRename" aria-label="Đổi tên quán">✏️</button></header>
    ${todayLine}
    ${w.length?`<div class="mt-warns">${w.map(v=>`<button type="button" class="btn mt-warn" data-action="car:prep" data-tab="stock">⚠ ${x.esc(v.text)}</button>`).join('')}</div>`:''}
    <nav class="mt-tabs" role="tablist" aria-label="Chuẩn bị quầy">${TABS.map(([id,e,l])=>`<button type="button" role="tab" class="mt-tab ${tab===id?'on':''}" data-action="car:prep" data-tab="${id}" aria-selected="${tab===id}"><span aria-hidden="true">${e}</span> ${l}</button>`).join('')}</nav>
    <section class="mt-panel" role="tabpanel">${panel}</section>
  </div>
  <footer class="life-sticky">${x.button(c.open?'Về quầy · pha tiếp':`Mở cửa ngày ${dayNo}`,c.open?'workbench':'start',{},'primary jumbo'+(c.metrics?.served>0?'':' gd-pulse'))}</footer>`;
}

/* ---------------------------------------------------------------- module */
/** The words next to the cup (x.ui.flash), written in place. False: no counter on screen to write them in. */
function showFlash(x){
  const box=typeof document!=='undefined'&&document.querySelector('#sheet[open] .career-job.mt .mt-preview'),said=box&&box.querySelector('.mt-said');
  if(!said)return false;
  box.classList.toggle('quiet',!x.ui.flash);
  said.innerHTML=x.ui.flash?`<p class="mt-flash" role="status">${x.esc(x.ui.flash)}</p>`:'';
  return true;
}
let focusKey='';
const flying=new Set();  // counter taps on the wire (op|payload): a double tap is not sent twice
/** Bring the next step's control into view once when the step changes, unless it is already
 * visible between the sheet header and the pinned bar. Scrolls only; never rebuilds the DOM. */
function focusStep(root){
  const key=root.dataset.mtKey||'';
  if(!key||key===focusKey)return;
  focusKey=key;
  const at=root.dataset.mtAt,el=at&&[...root.querySelectorAll(at)].find(e=>e.offsetParent!==null);
  if(!el)return;
  const r=el.getBoundingClientRect(),head=root.closest('dialog')?.querySelector('.sheet-head')?.getBoundingClientRect().bottom||0;
  const bar=root.querySelector('.fk-bar'),bottom=bar&&bar.offsetParent!==null?bar.getBoundingClientRect().top:innerHeight;
  if(r.top>=head&&r.bottom<=bottom)return;
  el.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
}
/** The order ticket sticks just under the sheet header when both scroll in the same box (phones);
 * where the header sits outside the scrolling body it sticks at the top edge. */
function pinTicket(root){
  // It walks the ancestors' computed styles (a style pass): once a second is plenty for a header that rarely moves.
  const t=performance.now();if(t-(root._pinAt||0)<1000)return;root._pinAt=t;
  if(!root.querySelector('.mt-ticket'))return;
  const head=root.closest('dialog')?.querySelector('.sheet-head');
  let sc=root.parentElement;
  while(sc&&!/(auto|scroll)/.test(getComputedStyle(sc).overflowY))sc=sc.parentElement;
  const v=`${head&&sc&&sc.contains(head)&&getComputedStyle(head).position==='sticky'?head.offsetHeight:0}px`;
  if(root.style.getPropertyValue('--mt-stick')!==v)root.style.setProperty('--mt-stick',v);
}
export default {
  id:'milk_tea',
  css:true,
  autoNext:true,
  next(t,x){
    t=x?withLocal(t,x):t;
    try{const n=x&&nextOf(teaGuide(t,x).steps);if(n)return x.esc(stepLine(n));}catch{/* fall back to the fixed lines */}
    return nextStep(t,x,(B(x).level||1)<=3);
  },
  clock(c){return c.data?.boba?.clock||'';},
  // app.js: an answer that another pick's answer follows does not draw the counter again (see "picks at once").
  settling(x){return (x.ui.mtLocal||[]).length>1;},
  job(t,x){
    t=withLocal(t,x);
    const g=teaGuide(t,x),brew=t.known?brewSteps(t,x):[];
    // Stations in the order a cup is made (cup, tea, syrup, toppings, ice & sugar), then the sealer.
    // The cup picture sits beside them on wide screens; on phones the mini cup in the bottom bar shows it.
    const layout=`<div class="mt-bench"><div class="mt-side"><section class="mt-preview${x.ui.flash?'':' quiet'}">${cupArt(x,t.cup)}<div class="mt-said">${x.ui.flash?`<p class="mt-flash" role="status">${x.esc(x.ui.flash)}</p>`:''}</div></section>${finish(t,x)}</div>
      <div class="mt-stations">${stations(t,x,g.final?g.steps:[])}</div></div>`;
    // The order recap and the next step (then the hand-over) stay pinned above the sheet footer.
    // The mini cup keeps the result in view next to whichever station the step scrolled to.
    // The shared bar (ui-kit actBar, UI wave 4): the mini cup and the recap (or the pointer / "hoặc giao" link) on the
    // left, the one main button on the right. fk-bar stays as a hook (tick, focusStep, food_kit keepBarAboveFooter).
    const {next,main}=barParts(x,g.steps,g.final||{label:'',go:null,ready:false});
    const cup=t.known?`<span class="mt-bar-cup" aria-hidden="true">${cupArt(x,t.cup,true)}</span>`:'';
    const recap=todoLine(t,x,brew),left=`${cup}${next||(recap?`<p class="fk-next" aria-live="polite">${recap}</p>`:'')}`;
    const bar=actBar({next:left,main,cls:'fk-bar mt-bar'});
    // After each step the screen scrolls to the control of the next one (tick), once per step.
    const n=nextOf(g.steps),at=!n||B(x).event?'':n.go?.sel||(n.go?.cmd==='tea_discard'?'.mt-minor':'')||n.at||'';
    return `<div class="career-job mt" data-mt-at="${x.esc(at)}" data-mt-key="${x.esc(`${t.id}|${n?.label||''}|${n?.ok}`)}">${hintFor(t,x)}${hud(x)}${eventCard(x)}${alerts(x)}${(B(x).care||[]).some(r=>r.tone!=='ok')?careFold(x):''}${appRow(t,x)}${queueRow(t,x)}${customer(t,x,brew)}${outOfStock(t,x)}${t.known?layout:''}${bar}</div>`;
  },
  idle(x){
    if(!x?.room)return '';
    const b=B(x),waiting=x.room.tasks.filter(open),left=b.left||0,orders=b.orders||[];
    const who=waiting[0]?.customer||'khách';
    // more_gate (engine.more_gate): the server would refuse one more guest (closing time, the day's 12 dealt): close the day instead.
    const gate=x.room.more_gate,shut=gate&&gate.why!=='full'?{ok:null,label:'Khép ca hôm nay',go:{act:'end',label:gate.why==='cap'?'🌙 Khép ca · đủ khách hôm nay':'🌙 Khép ca · hết giờ đón khách'}}:null;
    const step=waiting.length?{ok:null,label:`Mời ${who} lên quầy`,go:{act:'job',data:{task:waiting[0].id},label:`👋 Mời ${x.esc(who)} lên quầy`}}
      :shut?shut:left&&!gate?{ok:null,label:'Mời khách tiếp theo',go:run('more_work',{},'🔔 Mời khách tiếp theo')}
      :{ok:null,label:'Khép ca hôm nay',go:{act:'end',label:'🌙 Khép ca hôm nay'}};
    const next=stepCta(x,[step],{label:'',go:null,ready:false},{style:'primary'});
    const wait=x.room.open&&orders.length&&!waiting.length?jb(x,'⏳ Chờ hàng · 20 phút','tea_wait',{},'ghost'):'';
    const night=(b.night||[]).length?`<div class="mt-night">${b.night.map(l=>`<p>${x.esc(l)}</p>`).join('')}</div>`:'';
    return `<div class="career-job mt">${B(x).event?'':nextHint(x,[step])}${hud(x)}${eventCard(x)}${alerts(x)}${night}${careFold(x)}${orders.length?`<section class="mt-orders"><h4>📦 Đang giao</h4>${orderRows(x)}</section>`:''}<div class="row wrap">${next}${wait}${x.button('🧺 Kho & đặt hàng','prepare',{},'ghost')}</div></div>`;
  },
  page(view,x){
    if(!['prepare','prices'].includes(view)||!x?.room)return '';
    // "Bảng giá" opens on the price tab; tabs switch inside the same sheet.
    if(view==='prices'&&x.ui.lastPage!=='prices')x.ui.prep='price';
    // Chuẩn bị opened anew (not a re-render of the open sheet) lands on Kho, its first tab.
    else if(view==='prepare'&&(x.ui.lastPage!=='prepare'||typeof document!=='undefined'&&!document.querySelector('#sheet[open] .mt-prep')))x.ui.prep='stock';
    x.ui.lastPage=view;
    return prepare(x,x.ui.prep);
  },
  // A typed price snaps into the band as soon as the field is left, so the number on screen is the one saved.
  input(el,x,type){if(!el.dataset?.price)return false;if(type==='change'){const v=clampPrice(x,el.dataset.price,el.value);if(v!=null)el.value=v;}return true;},
  actions:{
    async prep(data,el,x){x.ui.prep=data.tab;x.render();},
    // Bảng giá: the price goes out inside the band the server accepts (a typed 50 becomes the top of the band).
    async price(data,el,x){const i=document.getElementById('price-'+data.item),v=clampPrice(x,data.item,i?.value);if(v==null){x.toast('Nhập giá bằng số nhé.',true);return;}if(i)i.value=v;await x.send('life_price',{item:data.item,price:v});},
    async pick(data,el,x){x.ui.mtItem=x.ui.mtItem===data.item?null:data.item;x.ui.mtQty=null;x.render();},
    async sup(data,el,x){x.ui.mtSup=data.sup||null;x.render();},
    async shelf(data,el,x){(x.ui.mtShelf??={})[data.key]=true;x.render();},
    async showoff(data,el,x){x.ui.mtShowOff=!x.ui.mtShowOff;x.render();},
    async qty(data,el,x){x.ui.mtQty=Number(data.qty)||null;x.render();},
    async fold(data,el,x){const d=el.closest('details');if(data.key)x.ui[data.key]=d?!d.open:!x.ui[data.key];},
    async go(data,el,x){
      let payload={};try{payload=JSON.parse(data.payload||'{}');}catch{return;}
      // A second tap on the same control while it is on the wire is a double tap: once it lands the screen has
      // moved on (the greeting is done, the batch is made), so sending it again only earns a refusal.
      const key=`${data.op}|${data.payload||''}`;if(flying.has(key))return;
      // Drawn before the gate closed (engine.more_gate): say why instead of pressing into a sure refusal.
      if(data.op==='more_work'&&x.room?.more_gate){const g=x.room.more_gate;x.toast(g.why==='full'?'Đang có đủ khách: làm nốt ly đang chờ nhé.':g.why==='cap'?'Hôm nay đủ khách rồi: làm nốt rồi khép ca nhé.':'Sắp đóng cửa: không đón thêm khách. Làm nốt rồi khép ca nhé.','hint');x.render();return;}
      if(data.op==='tea_greet'&&x.room?.tasks?.find(t=>t.id===payload.task)?.greeted){x.render();return;}
      // A pick the server would take shows now (see "picks at once"); its command follows through the queue.
      const quick=QUICK.has(data.op)&&canQuick(x,withLocal(serverTask(x,payload.task),x),data.op,payload)?{op:data.op,payload}:null;
      flying.add(key);
      sfx.configure(x.state.settings||{});sfx.unlock();
      if(quick){
        (x.ui.mtLocal??=[]).push(quick);lightUp(data.op,payload);sfx.click();
        // The rest of the counter (cup, counts, next step) is drawn once the frame with the lit tile is on screen
        // (one drawing for the picks of that frame).
        if(!x.ui.mtDraw){x.ui.mtDraw=true;requestAnimationFrame(()=>setTimeout(()=>{x.ui.mtDraw=false;if(x.ui.mtLocal?.length)x.render();},0));}
      }
      const settle=()=>{if(quick)x.ui.mtLocal=(x.ui.mtLocal||[]).filter(p=>p!==quick);};
      try{
        const r=await x.api.command(data.op,payload,"milk_tea")||{};   // the career named: a new account has no `current` yet
        settle();
        x.ui.flash=data.op==='ask'?'':r.message||'';
        if(r.celebrate)sfx.success();else if(!quick)sfx.click();
        if(r.message&&(LOUD.has(data.op)||r.celebrate||/khách mới|bỏ về|hủy|quá giờ/.test(r.message)))x.toast(r.message,r.correct===false?'error':r.celebrate?'good':false);
        for(const note of new Set(r.effects||[]))x.toast(note);
        // A pick that landed was drawn already (its state, with the pick laid on top, is the same screen): only the
        // words next to the cup change. Drawing the whole counter again cost a second full render per pick.
        if(quick&&!r.duplicate&&showFlash(x))return;
        x.render();
      }catch(error){settle();sfx.error();x.toast(error.status?error.message:'Mất kết nối. Việc đã xác nhận vẫn được giữ, thử lại sau một chút nhé.',true);if(quick)x.render();}
      finally{flying.delete(key);}
    },
  },
  tick(root,x){
    keepBarAboveFooter(root);
    pinTicket(root);
    focusStep(root);
    // First task: the pinned bottom button glows too, since the glowing tile may be out of view on a phone.
    if(root.closest('dialog')?.querySelector('.gd-next[data-first]'))root.querySelector('.fk-bar .gd-cta:not([disabled])')?.classList.add('gd-pulse');
    const modal=root.querySelector('.mt-modal');
    if(modal){
      const d=root.closest('dialog'),h=`${d?.querySelector('.sheet-head')?.offsetHeight||0}px`;
      if(d&&d.style.getPropertyValue('--job-head')!==h)d.style.setProperty('--job-head',h);
      if(!modal.contains(document.activeElement))modal.querySelector('button:not([disabled])')?.focus({preventScroll:true});
    }
  },
  // The sealer needle while the lever is down (v4/careers.js): it glides on the compositor, its words change five
  // times a second. "Nhả tay" holds it where it was when the finger came down (tapStop).
  meters(root,x){
    for(const el of root.querySelectorAll('[data-seal-start]')){
      const start=Number(el.dataset.sealStart);if(!start)continue;
      const [loose,lo,hi,burn,max]=el.dataset.s.split(',').map(Number),held=Math.max(0,x.now()-start);
      x.slide(el.querySelector('.mt-needle'),held/max*100,100/max);
      const label=el.parentElement.querySelector('.mt-gauge-label'),text=`${held.toFixed(1)} giây · `+(held<loose?'màng chưa dính…':held<lo?'sắp được rồi…':held<=hi?'VÙNG XANH — NHẢ TAY!':held<=burn?'hơi lâu rồi…':'cháy màng mất!');
      if(label&&label.textContent!==text)label.textContent=text;
      el.classList.toggle('ready',held>=lo&&held<=hi);el.classList.toggle('over',held>burn);
    }
  },
  tapStop:op=>op==='tea_seal',
  summary(data,x){
    if(!data||data.served==null)return '';
    const row=(l,v)=>`<div class="kv-row"><span>${l}</span><b>${v}</b></div>`;
    const tm=data.tomorrow,b=B(x),cups=b.cups;
    // "Ngày mai" first: what was thrown away at closing, the cups left, what runs low, then one way to Kho.
    // Each line only from a field that is there (an older server leaves it out, the line goes too).
    const low=ings(x).filter(i=>{const s=station(x,i.id);return !s.made&&s.unlocked&&s.on!==false&&s.stock<=LOW_PORTIONS;});
    const lines=[data.dumped?`🗑️ Bỏ cuối ca <b>${data.dumped} phần</b> trà & trân châu: mai ủ, nấu vừa đủ`:'',
      cups&&cups.M!=null?`🥤 Ly còn <b>M ${cups.M}</b> · <b>L ${cups.L??0}</b>${['M','L'].some(k=>(cups[k]||0)<LOW_CUPS)?' · sắp hết':''}`:'',
      low.length?`📦 Sắp hết: ${low.slice(0,4).map(i=>`${x.esc(i.name)} <b>${station(x,i.id).stock}</b>`).join(' · ')}${low.length>4?` · +${low.length-4}`:''}`:'',
      data.orders?`🚚 Đang giao <b>${data.orders}</b> đơn`:''].filter(Boolean);
    const plan=`<section class="mt-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>${tm?`<p class="mt-tomorrow-line"><span aria-hidden="true">${x.esc(tm.emoji)}</span> <b>Mai: ${x.esc(tm.title)}</b><small>${x.esc(tm.advice)}</small></p>`:''}${lines.length?`<ul class="mt-plan-list">${lines.map(l=>`<li>${l}</li>`).join('')}</ul>`:''}${x.button('🧺 Mở Kho','warehouse',{},'primary small mt-plan-go')}</section>`;
    const kv=`<div class="kv">${row('Ly đã trao',data.served)}${row('Ly chuẩn từng lớp',data.perfect)}${data.returned?row('Ly bị trả lại',data.returned):''}${data.walkouts?row('Khách bỏ về / đơn hủy',data.walkouts):''}${row('Doanh thu quầy',`${data.revenue} xu`)}${data.bonus?row('Thưởng thêm',`${data.bonus} xu`):''}${data.fines?row('Tiền phạt',`${data.fines} xu`):''}${data.dumped?row('Trà & trân châu bỏ cuối ca',`${data.dumped} phần`):''}${data.sealer!=null?row('Máy dán nắp',`${data.sealer} ly từ lần lau trước`):''}${data.orders?row('Đơn hàng đang giao',data.orders):''}${row('Tay nghề',`cấp ${data.level}`)}</div>`;
    return `<article class="card space-top mt-sum">${plan}<details class="mt-sum-more"><summary>🧋 Quầy trà hôm nay · ${data.served} ly · ${data.revenue} xu</summary>${kv}</details></article>`;
  },
};
