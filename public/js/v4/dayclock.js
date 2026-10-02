/** Giờ trong ngày (server: game/dayclock.py → career.day_clock).
 *
 * HUD: the clock chip in the day button (time, part of day, a thin shift bar that turns amber → orange →
 * red towards closing), the clock card at the top of the status sheet, the "Đến giờ đóng cửa" prompt,
 * the day summary's closing line and the small "+20 phút" pop after an action.
 * Scene: `daylight(world)` tints the canvas by the time of day (morning light, bright noon, golden
 * afternoon, blue evening, dark night) and switches the lights on in the evening: glows at the workplace's
 * stations, windows and doors, lamp posts on outdoor scenes. It runs in the shared world layer
 * (BobaWorld.draw), after the room and the people and before name tags and speech, so every career gets it
 * and canvas text stays readable. The DOM UI is never darkened. Changes glide over ~2 s (instant with
 * reduced motion). Render-only: every time and word comes from the server. */
import {asset} from '../assets.js';

const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function dayclockBoot(){
  if(typeof document==='undefined'||document.querySelector('link[data-dayclock-css]'))return;
  const l=document.createElement('link');l.rel='stylesheet';l.href=asset('/css/dayclock.css');l.dataset.dayclockCss='1';document.head.append(l);
}

/* ------------------------------------------------------------------ HUD */
const WARN_CLASS={soon60:'dc-soon',soon30:'dc-late',closing:'dc-closing',prep:'dc-prep'};
/** Inside the top bar's day button: "🌤️ 09:40 · Sáng" and the thin shift bar. */
export function clockChip(dc){
  if(!dc)return '';
  const cls=WARN_CLASS[dc.level]||'';
  const bar=dc.is_open?`<i class="dc-bar" aria-hidden="true"><i style="width:${Math.round((dc.progress||0)*100)}%"></i></i>`:'';
  return `<span class="dc-chip ${cls}" data-testid="clock"><span class="dc-ico" aria-hidden="true">${esc(dc.part?.icon)}</span><b>${esc(dc.time)}</b><small>${esc(dc.part?.label)}</small>${bar}</span>`;
}
/** Words for the day button's aria-label. */
export const clockAria=dc=>dc?`${dc.time}, ${dc.part?.label||''}. ${dc.label}. ${dc.hours}.`:'';

/** The status sheet's first card: the big time, the shift bar with the hours, what is left, the rule. */
export function clockCard(dc){
  if(!dc)return '';
  const pct=Math.round((dc.progress||0)*100),cls=WARN_CLASS[dc.level]||'';
  const step=dc.step?`<li>Mỗi thao tác ở quầy mất khoảng ${dc.step} phút.</li>`:'<li>Mỗi việc làm tốn một ít thời gian trên đồng hồ của nơi làm.</li>';
  return `<section class="dc-card ${cls}" aria-label="Giờ trong ngày"><div class="dc-head"><span class="dc-big-ico" aria-hidden="true">${esc(dc.part?.icon)}</span>`+
    `<div class="grow"><strong class="dc-big">${esc(dc.time)}</strong><span class="dc-part">${esc(dc.part?.label)}${dc.is_open?'':' · chưa mở cửa'}</span></div><em class="dc-state">${esc(dc.label)}</em></div>`+
    `<div class="dc-shift"><div class="dc-track" role="progressbar" aria-label="Ca làm hôm nay" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i style="width:${pct}%"></i></div>`+
    `<div class="dc-ends"><span>Mở ${esc(dc.open_time)}</span><span>Đóng ${esc(dc.close_time)}</span></div></div>`+
    (dc.note?`<p class="dc-note">${esc(dc.note)}</p>`:'')+
    `<details class="dc-rules"><summary>Giờ giấc ở đây</summary><ul>${step}<li>Còn 60 phút và 30 phút có lời nhắc; tới giờ đóng cửa thì không đón thêm khách.</li><li>Khách đã vào quán vẫn được làm nốt. Khép ca lúc nào cũng được: việc dở giữ lại, khách hẹn quay lại khi mở cửa sáng mai, không bị tính là bỏ dở.</li></ul></details></section>`;
}
/** The day summary: when you closed and when tomorrow opens. */
export function clockSummary(s){
  const k=s?.clock;if(!k)return '';
  return `<article class="dc-sum"><span class="dc-big-ico" aria-hidden="true">${esc(k.part?.icon||'🌙')}</span><div class="grow"><b>${esc(k.text)}</b><p>${esc(k.next_text)}</p></div></article>`;
}
/** Past closing on the calm screen: the one clear next step. `busy` = a customer is still in hand. `gate` = the
 * room's more_gate (game/engine.py more_gate): no new customer either because the next one would arrive at closing
 * time (the press ticks the clock) or because today's customers are all dealt. */
export function closingNote(dc,busy,gate=null){
  const cap=gate?.why==='cap',shut=dc?.is_open&&(dc.level==='closing'||gate?.why==='closing');
  if(!cap&&!shut)return '';
  const head=cap?`✅ <b>Đủ ${esc(gate.cap)} khách hôm nay</b>`:dc.level==='closing'?'🔔 <b>Đến giờ đóng cửa</b>':'🔔 <b>Sắp đóng cửa</b>';
  return `<p class="dc-closing-line" role="status">${head} · ${busy?'làm nốt khách đang làm rồi khép ca nhé.':'không đón thêm khách nữa.'}</p>`;
}

/* ------------------------------------------------------------------ scene light */
// Key frames: minute → multiply tint (rgb), its strength, how much the lights are on (0..1).
const KEYS=[
  [0,[34,40,84],.6,1],[270,[34,40,84],.6,1],[330,[112,108,170],.4,.75],[390,[255,206,170],.2,.15],[480,[255,240,216],.08,0],
  [660,[255,255,255],0,0],[840,[255,255,255],0,0],[960,[255,228,176],.12,0],[1050,[255,190,112],.24,.1],
  [1110,[214,150,128],.3,.45],[1140,[124,134,196],.38,.85],[1260,[62,72,128],.52,1],[1380,[34,40,84],.6,1],[1440,[34,40,84],.6,1],
];
const mixN=(a,b,t)=>a+(b-a)*t;
/** Light at a time of day: {rgb, alpha, lamps}. */
export function lightAt(minute){
  const m=((Number(minute)||0)%1440+1440)%1440;let i=0;while(i<KEYS.length-2&&KEYS[i+1][0]<=m)i++;
  const [a,ra,aa,la]=KEYS[i],[b,rb,ab,lb]=KEYS[i+1],t=b>a?(m-a)/(b-a):0;
  return {rgb:ra.map((v,k)=>mixN(v,rb[k],t)),alpha:mixN(aa,ab,t),lamps:mixN(la,lb,t)};
}
const OUTDOOR=new Set(['sidewalk','street','farm','lane']);
/** Lamp post (outdoor scenes) standing at (x,y) in scene pixels; `on` 0..1. */
function lampPost(c,x,y,s,on){
  c.save();c.translate(x,y);c.scale(s,s);
  c.fillStyle='rgba(60,50,40,.22)';c.beginPath();c.ellipse(0,2,16,5,0,0,Math.PI*2);c.fill();
  c.fillStyle='#4f5560';c.fillRect(-4,-150,8,150);c.fillRect(-9,-8,18,8);
  c.beginPath();c.moveTo(0,-150);c.quadraticCurveTo(0,-168,22,-166);c.lineWidth=5;c.strokeStyle='#4f5560';c.stroke();
  c.fillStyle='#3f444d';c.beginPath();c.moveTo(12,-168);c.lineTo(36,-168);c.lineTo(30,-158);c.lineTo(18,-158);c.closePath();c.fill();
  const g=Math.round(150+100*on);c.fillStyle=`rgb(255,${g},${Math.round(120+60*on)})`;c.beginPath();c.ellipse(24,-156,7,4,0,0,Math.PI*2);c.fill();
  c.restore();
}
function glow(c,x,y,r,a,color='255,214,140'){
  if(a<=.01)return;const g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,`rgba(${color},${a})`);g.addColorStop(.55,`rgba(${color},${a*.35})`);g.addColorStop(1,`rgba(${color},0)`);
  c.fillStyle=g;c.fillRect(x-r,y-r,r*2,r*2);
}
/** Where the lights are: the stations (hotspots), the window glass and the door; outdoor lamp posts. */
function lightSpots(w){
  const plan=w.plan?.()||{},out=[],floor=plan.floor;
  for(const h of w.hotspots||[]){if(['workbench','counter','shelf','door','evidence'].includes(h.id)){const p=w.project(h.x,h.y);out.push([p.x,p.y-60,h.id==='door'?120:150]);}}
  const glass=plan.anchors?.glass;if(glass)out.push([glass[0],glass[1],130,'255,226,160']);
  if(!out.length&&Array.isArray(floor))out.push([(floor[0]+floor[2])/2,floor[1]+40,260]);
  return out;
}
function lampSpots(w){
  const floor=w.plan?.()?.floor;if(!Array.isArray(floor))return [];
  const port=w.isPortrait?.();return [[floor[0]+(port?30:50),floor[1]+(port?30:20)],[floor[2]-(port?30:50),floor[1]+(port?30:20)]];
}
/** Paint the time of day over the scene (canvas already in scene space). Call after people, before labels. */
export function daylight(w){
  const c=w.ctx,dc=w.c?.day_clock;if(!c||!dc)return;
  const target=lightAt(dc.minute),now=w._time||0,L=w._light;
  if(!L||w.reduced||L.career!==w.career){w._light={...target,rgb:[...target.rgb],career:w.career,at:now};}
  else{
    const dt=Math.max(0,Math.min(.5,now-L.at)),k=1-Math.exp(-dt*1.6);L.at=now;
    L.alpha=mixN(L.alpha,target.alpha,k);L.lamps=mixN(L.lamps,target.lamps,k);L.rgb=L.rgb.map((v,i)=>mixN(v,target.rgb[i],k));
    const far=Math.abs(L.alpha-target.alpha)>.004||Math.abs(L.lamps-target.lamps)>.004;
    if(far)w.wake?.(true);else Object.assign(L,{alpha:target.alpha,lamps:target.lamps,rgb:[...target.rgb]});
  }
  const cur=w._light,kind=w.scene?.()?.id,outdoor=w.outdoor?.()??OUTDOOR.has(kind);   // an interior says for itself (scenes/areas.js)
  c.save();
  // Outdoor lamp posts stand in every light; they only glow in the evening.
  if(outdoor)for(const [x,y] of lampSpots(w))lampPost(c,x,y,w.isPortrait?.()?.9:1,cur.lamps);
  if(cur.alpha>.005){
    // Multiply tint, a little lighter over the room itself (its lights are on) than around it.
    const rgb=cur.rgb.map(Math.round).join(','),port=w.isPortrait?.(),cx=port?350:600,cy=port?470:470,inner=outdoor?.85:1-.45*cur.lamps;
    const g=c.createRadialGradient(cx,cy,port?120:180,cx,cy,port?560:720);g.addColorStop(0,`rgba(${rgb},${cur.alpha*inner})`);g.addColorStop(1,`rgba(${rgb},${cur.alpha})`);
    c.globalCompositeOperation='multiply';c.fillStyle=g;
    const tl={x:-w.offset.x/w.scale,y:-w.offset.y/w.scale};c.fillRect(tl.x,tl.y,w.width/w.scale,w.height/w.scale);
    c.globalCompositeOperation='source-over';
  }
  if(cur.lamps>.02){
    c.globalCompositeOperation='lighter';const a=.34*cur.lamps;
    for(const [x,y,r,col] of lightSpots(w))glow(c,x,y,r,a,col);
    if(outdoor){const s=w.isPortrait?.()?.9:1;for(const [x,y] of lampSpots(w)){glow(c,x+24*s,y-150*s,90,a*1.2,'255,220,150');glow(c,x+10,y,110,a*.8,'255,214,140');}}
    c.globalCompositeOperation='source-over';
  }
  c.restore();
}

/* ------------------------------------------------------------------ "+20 phút" */
/** Minutes the clock moved between two readings {day, minute, is_open} of the same open day (0 when not comparable). */
export function clockStep(prev,next){
  if(!prev||!next||!prev.is_open||!next.is_open||prev.day!==next.day)return 0;
  const d=(next.minute||0)-(prev.minute||0);return d>0&&d<=240?d:0;
}
