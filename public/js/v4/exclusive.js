/** 🌧️ Danh hiệu độc nhất (game/exclusive.py, owner 24/10: "cho mnt2410 cái khung mưa rơi đi, xong rồi cái danh hiệu
 * Cuồng Vũ Tán Tiên. làm độc nhất nhé"): an honour the admin gives one player by name, never sold, won or traded. The
 * server decides who holds it (`tt` from live/honours.py, `ex` on a board's row, `rank.ex` on Phố nghề, api.exTitles
 * from the load); this module only draws it: the chip of its title (a rain shimmer), its frame "Mưa rơi" (a glass ring
 * of blue-violet cloud with rain falling through it, ripples at the bottom, sparkles, a cloud crest and a small
 * umbrella; animated SVG, a still one with reduced motion), its chat bubble and the canvas name tags (Đi dạo, the
 * fishing lake). EX mirrors game/exclusive.py EXCLUSIVE (tests/test_exclusive.py compares them). Nothing is sent. */
import {escapeHTML as esc} from '../icons.js';

export const EX={
  ex_cuong_vu:{emoji:'🌧️',name:'Cuồng Vũ Tán Tiên',frame:'Mưa rơi'},
};
export const EX_LABEL='Độc nhất';
export const EX_SRC='Độc nhất · cả phố chỉ một người có';
export const isEx=id=>typeof id==='string'&&Object.prototype.hasOwnProperty.call(EX,id);
/** {id, emoji, name, frame} of an exclusive honour id, or null. */
export const exOf=id=>isEx(id)?{id,...EX[id]}:null;
/** The first exclusive honour among `tt` ids, or null. */
export const firstEx=tt=>Array.isArray(tt)?tt.slice(0,16).map(exOf).find(Boolean)||null:null;

const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
/** Reduced motion (the system's or the game's setting): the rain stands still. */
export const exStill=()=>{try{return Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion')||document.body.classList.contains('reduce-motion');}catch{return false;}};

/* ---------------------------------------------------------------- the frame "Mưa rơi" (180 × 180, like an auction title's) */
const L='#f4f7ff',M='#9fb4ff',V='#8b7cf0',D='#4a3fae';
const url=svg=>`data:image/svg+xml,${encodeURIComponent(svg).replace(/'/g,'%27')}`;
const SVG=new Map();
/** The frame as an svg data url: `anim` with SMIL (the rain falls, ripples spread, sparkles twinkle), else still. */
export function rainFrame(anim=true){
  const key=anim?'a':'s';let u=SVG.get(key);if(u)return u;
  let drops='';
  for(let i=0;i<20;i++){   // a drop: a white streak over a soft violet one, so it reads on the light glass and the dark
    const x=8+i*8.7+(i%3)*2.5,y=8+((i*53)%150),dur=1+((i*7)%5)*.14,beg=((i*.41)%dur).toFixed(2),w=i%3?1.6:2.2,d=`M${x.toFixed(1)} ${anim?-16:y}l-2.8 12`;
    drops+=`<g class="dr"><path d="${d}" stroke="${D}" stroke-opacity=".38" stroke-width="${w+1.8}" stroke-linecap="round"/><path d="${d}" stroke="#fff" stroke-width="${w}" stroke-linecap="round"/>`+
      (anim?`<animateTransform attributeName="transform" type="translate" from="0 0" to="-12 200" dur="${dur.toFixed(2)}s" begin="-${beg}s" repeatCount="indefinite"/>`:'')+'</g>';
  }
  const star=(x,y,s,b)=>`<path transform="translate(${x} ${y}) scale(${s})" d="M0-5L1.2-1.2L5 0L1.2 1.2L0 5L-1.2 1.2L-5 0L-1.2-1.2Z" fill="#fff" opacity="${anim?.3:.9}">`+
    (anim?`<animate attributeName="opacity" values=".15;1;.15" dur="2.4s" begin="${b}s" repeatCount="indefinite"/>`:'')+'</path>';
  const rip=(x,b,still)=>`<ellipse cx="${x}" cy="164" rx="${still[0]}" ry="${still[1]}" fill="none" stroke="${L}" stroke-width="1.4" opacity="${anim?0:.8}">`+
    (anim?`<animate attributeName="rx" values="2;15" dur="1.8s" begin="${b}s" repeatCount="indefinite"/><animate attributeName="ry" values=".6;4" dur="1.8s" begin="${b}s" repeatCount="indefinite"/><animate attributeName="opacity" values="1;0" dur="1.8s" begin="${b}s" repeatCount="indefinite"/>`:'')+'</ellipse>';
  const crestDrop=(x,b)=>`<path d="M${x} 30l-1 4" stroke="#fff" stroke-width="2" stroke-linecap="round">`+
    (anim?`<animateTransform attributeName="transform" type="translate" values="0 -2;-1 7" dur="1.1s" begin="${b}s" repeatCount="indefinite"/><animate attributeName="opacity" values="1;0" dur="1.1s" begin="${b}s" repeatCount="indefinite"/>`:'')+'</path>';
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180" viewBox="0 0 180 180"><defs>`+
    `<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e9f0ff"/><stop offset=".38" stop-color="${M}"/><stop offset=".7" stop-color="${V}"/><stop offset="1" stop-color="${D}"/></linearGradient>`+
    `<linearGradient id="c" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#d9e0ff"/></linearGradient>`+
    `<clipPath id="b"><path clip-rule="evenodd" d="M90 5A85 85 0 1 0 90.01 5ZM90 31A59 59 0 1 1 89.99 31Z"/></clipPath></defs>`+
    `<circle cx="90" cy="90" r="80" fill="none" stroke="${M}" stroke-opacity=".28" stroke-width="7"/>`+
    `<circle cx="90" cy="90" r="68" fill="none" stroke="url(#g)" stroke-width="15" opacity=".95"/>`+
    `<circle cx="90" cy="90" r="76" fill="none" stroke="${D}" stroke-width="2.5"/><circle cx="90" cy="90" r="60.8" fill="none" stroke="${L}" stroke-width="2"/>`+
    `<circle cx="90" cy="90" r="70" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="70 370" transform="rotate(196 90 90)"/>`+
    `<g clip-path="url(#b)">${drops}</g>`+
    `${star(30,44,1,0)}${star(152,124,.85,.8)}${star(22,122,.7,1.6)}${star(160,74,.75,1.1)}${star(118,30,.6,.4)}`+
    // ☂️ a small umbrella on the ring (right), its handle hooked
    `<g transform="translate(148 50) rotate(28)"><path d="M-10 1A10 9 0 0 1 10 1Q7.5-1.5 5 1Q2.5-1.5 0 1Q-2.5-1.5-5 1Q-7.5-1.5-10 1Z" fill="${V}" stroke="${L}" stroke-width="1.4"/><path d="M0-8V-9.5M0 1V9.5A2.4 2.4 0 0 1-4.8 9.5" fill="none" stroke="${L}" stroke-width="1.8" stroke-linecap="round"/></g>`+
    // ☁️ the crest: a cloud raining a little
    `<g transform="translate(0 6)"><path d="M68 21A8 8 0 0 1 71 7A11.5 11.5 0 0 1 92 2.5A10 10 0 0 1 109 8A7.5 7.5 0 0 1 112 21Z" fill="url(#c)" stroke="${D}" stroke-width="2.2" stroke-linejoin="round"/>`+
    `<path d="M75 13Q80 9 86 11" fill="none" stroke="${M}" stroke-width="1.6" stroke-linecap="round"/></g>`+
    `${crestDrop(80,0)}${crestDrop(90,.37)}${crestDrop(100,.74)}`+
    // 💧 a puddle at the bottom, ripples spreading on it
    `<ellipse cx="90" cy="165" rx="32" ry="6" fill="${M}" opacity=".5"/><ellipse cx="90" cy="164" rx="32" ry="6" fill="none" stroke="${D}" stroke-width="1.2" opacity=".6"/>`+
    `${rip(72,0,[8,2.2])}${rip(92,.6,[13,3.4])}${rip(110,1.2,[6,1.8])}</svg>`;
  u=url(svg);SVG.set(key,u);return u;
}
/** The rain behind a chat bubble's text: a 48 px tile of slanted streaks falling (or still). */
function rainTile(anim,dark){
  const key=`t${anim?1:0}${dark?1:0}`;let u=SVG.get(key);if(u)return u;
  const c=dark?'#b9c8ff':'#7f98ff',op=dark?.32:.3,S=[[8,3],[30,17],[18,31],[42,6],[4,40],[36,38]];
  const streaks=dy=>S.map(([x,y])=>`<path d="M${x} ${y+dy}l-1.6 7" stroke="${c}" stroke-width="1.3" stroke-linecap="round"/>`).join('');
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><g opacity="${op}">${streaks(0)}${streaks(-48)}`+
    (anim?`<animateTransform attributeName="transform" type="translate" from="0 0" to="0 48" dur="1.5s" repeatCount="indefinite"/>`:'')+'</g></svg>';
  u=url(svg);SVG.set(key,u);return u;
}
/** Ripples along a bubble's bottom edge (84 × 10). */
function rippleStrip(anim,dark){
  const key=`r${anim?1:0}${dark?1:0}`;let u=SVG.get(key);if(u)return u;
  const c=dark?'#c9d4ff':'#7d8ff0';
  const one=(x,b,rx)=>`<ellipse cx="${x}" cy="6" rx="${anim?2:rx}" ry="${anim?1:rx/4}" fill="none" stroke="${c}" stroke-width="1" opacity="${anim?0:.6}">`+
    (anim?`<animate attributeName="rx" values="1;12" dur="2s" begin="${b}s" repeatCount="indefinite"/><animate attributeName="ry" values=".4;3" dur="2s" begin="${b}s" repeatCount="indefinite"/><animate attributeName="opacity" values=".9;0" dur="2s" begin="${b}s" repeatCount="indefinite"/>`:'')+'</ellipse>';
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="84" height="10" viewBox="0 0 84 10">${one(16,0,8)}${one(42,.7,11)}${one(68,1.4,6)}</svg>`;
  u=url(svg);SVG.set(key,u);return u;
}

/* ---------------------------------------------------------------- styles (one small stylesheet, on first use) */
let ready=false;
export function exCss(){
  if(ready||typeof document==='undefined')return;ready=true;
  const s=document.createElement('style');s.dataset.exCss='';
  const q=v=>`url("${v}")`;
  s.textContent=`:root{--ex-frame:${q(rainFrame(true))};--ex-frame-still:${q(rainFrame(false))};--ex-rain:${q(rainTile(true,false))};--ex-rain-still:${q(rainTile(false,false))};--ex-rain-d:${q(rainTile(true,true))};--ex-rain-d-still:${q(rainTile(false,true))};--ex-rip:${q(rippleStrip(true,false))};--ex-rip-still:${q(rippleStrip(false,false))};--ex-rip-d:${q(rippleStrip(true,true))};--ex-rip-d-still:${q(rippleStrip(false,true))}}
.hf-av.hf-ex::after{background-image:var(--ex-frame)}
.hn-chip.hn-ex{--hn-ink:#2e2a86;--hn-line:rgba(110,100,230,.5);background:linear-gradient(110deg,#dce7ff 0%,#cfc6ff 30%,#f4f7ff 45%,#cfc6ff 60%,#bcd0ff 100%);background-size:260% 100%;box-shadow:inset 0 0 0 1px var(--hn-line),0 0 7px rgba(130,120,255,.55);animation:exShine 3.6s linear infinite}
html[data-theme="dem"] .hn-chip.hn-ex{--hn-ink:#f1efff;--hn-line:rgba(190,180,255,.55);background:linear-gradient(110deg,#2c3b7a 0%,#4b3b9a 30%,#7b8cff 45%,#4b3b9a 60%,#2a3f86 100%);background-size:260% 100%}
.ex-ti{background:linear-gradient(100deg,#4f6df5,#8b5cf6 40%,#a5b8ff 50%,#8b5cf6 60%,#4338ca);background-size:250% 100%;-webkit-background-clip:text;background-clip:text;color:transparent!important;font-weight:800;animation:exShine 4s linear infinite}
html[data-theme="dem"] .ex-ti{background-image:linear-gradient(100deg,#a9bcff,#c9b2ff 40%,#ffffff 50%,#c9b2ff 60%,#9fb0ff)}
.ex-tag{display:inline-block;margin-left:4px;padding:0 5px;border-radius:999px;font:800 .62rem/1.5 system-ui,sans-serif;letter-spacing:.06em;color:#fff;background:linear-gradient(90deg,#6d8bff,#8b5cf6);vertical-align:middle;white-space:nowrap}
.jr-title-chip.ex-chip{background:linear-gradient(110deg,#e4ecff,#d6ceff 50%,#e4ecff);box-shadow:inset 0 0 0 1px rgba(110,100,230,.45),0 0 8px rgba(130,120,255,.4)}
html[data-theme="dem"] .jr-title-chip.ex-chip{background:linear-gradient(110deg,#2c3b7a,#4b3b9a 50%,#2c3b7a)}
.ch-bub.hf-ex{position:relative;margin-top:12px;padding:12px 16px 13px!important;border:2px solid transparent!important;border-radius:18px!important;color:#262457!important;
background:var(--ex-rip) center bottom 1px/84px 10px no-repeat padding-box,var(--ex-rain) 0 0/48px 48px repeat padding-box,linear-gradient(180deg,#f8faff,#eceeff) padding-box,linear-gradient(135deg,#d6e3ff,#8fa8ff 35%,#a58bf5 68%,#5d4fd0) border-box!important;box-shadow:0 0 12px -2px rgba(120,120,255,.65)!important}
.ch-bub.hf-ex::before{content:'🌧️';position:absolute;top:-13px;left:10px;display:grid;place-items:center;width:24px;height:24px;border-radius:50%;font-size:13px;line-height:1;background:linear-gradient(135deg,#ffffff,#c9d5ff);box-shadow:0 0 0 2px #7b6cf0,0 1px 4px rgba(60,50,160,.35);pointer-events:none}
.ch-bub.hf-ex::after{content:'ĐỘC NHẤT';position:absolute;top:-8px;right:10px;padding:1px 7px;border-radius:999px;font:800 8.5px/1.5 system-ui,sans-serif;letter-spacing:.08em;color:#fff;background:linear-gradient(90deg,#6d8bff,#8b5cf6);box-shadow:0 0 0 1.5px #fff;pointer-events:none}
.ch-msg.mine .ch-bub.hf-ex::before{left:auto;right:10px}.ch-msg.mine .ch-bub.hf-ex::after{right:auto;left:10px}
.ch-bub.hf-ex time{color:#5d5a96!important;opacity:1}.ch-bub.hf-ex a.ch-link{color:#4338ca!important}
html[data-theme="dem"] .ch-bub.hf-ex{color:#eef0ff!important;background:var(--ex-rip-d) center bottom 1px/84px 10px no-repeat padding-box,var(--ex-rain-d) 0 0/48px 48px repeat padding-box,linear-gradient(180deg,#24264d,#2c2558) padding-box,linear-gradient(135deg,#9fb4ff,#6d7cf0 40%,#8b5cf6 70%,#c9b2ff) border-box!important}
html[data-theme="dem"] .ch-bub.hf-ex time{color:#c3c0ee!important}html[data-theme="dem"] .ch-bub.hf-ex a.ch-link{color:#c9d4ff!important}
@keyframes exShine{from{background-position:100% 0}to{background-position:-160% 0}}
@media (prefers-reduced-motion:reduce){:root{--ex-frame:var(--ex-frame-still);--ex-rain:var(--ex-rain-still);--ex-rain-d:var(--ex-rain-d-still);--ex-rip:var(--ex-rip-still);--ex-rip-d:var(--ex-rip-d-still)}.hn-chip.hn-ex,.ex-ti{animation:none}}
html.reduce-motion,body.reduce-motion{--ex-frame:var(--ex-frame-still);--ex-rain:var(--ex-rain-still);--ex-rain-d:var(--ex-rain-d-still);--ex-rip:var(--ex-rip-still);--ex-rip-d:var(--ex-rip-d-still)}
html.reduce-motion .hn-chip.hn-ex,html.reduce-motion .ex-ti,body.reduce-motion .hn-chip.hn-ex,body.reduce-motion .ex-ti{animation:none}`;
  document.head.append(s);
}
/** A chip with an exclusive title ({id?, emoji, name}: a board's row `ex`), or ''. */
export function exChip(x,cls=''){
  if(!x||typeof x!=='object')return '';const k=exOf(x.id),emoji=k?.emoji||x.emoji||'🌧️',name=k?.name||x.name;
  if(!name)return '';exCss();
  return `<span class="hn-chip hn-ex${cls}" title="${esc(`${name} · ${EX_SRC}`)}"><i aria-hidden="true">${esc(emoji)}</i><span>${esc(name)}</span></span>`;
}

/* ---------------------------------------------------------------- canvas name tags (Đi dạo, the fishing lake) */
const rr=(c,x,y,w,h,r)=>{c.beginPath();if(c.roundRect)c.roundRect(x,y,w,h,r);else c.rect(x,y,w,h);};
/** The pill of a name tag wearing "Mưa rơi": glass in blue-violet, a glowing rim. (x, y) its top-left. */
export function exPill(c,x,y,w,h,dark,r=8){
  c.save();
  const g=c.createLinearGradient(x,y,x,y+h);
  if(dark){g.addColorStop(0,'rgba(38,42,92,.92)');g.addColorStop(1,'rgba(58,40,110,.92)');}else{g.addColorStop(0,'rgba(246,248,255,.95)');g.addColorStop(1,'rgba(226,222,255,.95)');}
  c.shadowColor=dark?'rgba(150,140,255,.65)':'rgba(110,100,240,.5)';c.shadowBlur=7;
  rr(c,x,y,w,h,r);c.fillStyle=g;c.fill();c.shadowColor='transparent';c.shadowBlur=0;
  const s=c.createLinearGradient(x,y,x+w,y+h);s.addColorStop(0,'#c9d8ff');s.addColorStop(.45,'#8fa8ff');s.addColorStop(1,'#8b5cf6');
  c.strokeStyle=s;c.lineWidth=1.8;c.stroke();
  c.restore();
}
/** Rain over a pill: slanted drops falling inside it, ripples on its bottom edge, two sparkles. `t` seconds (still: 0). */
export function exRain(c,x,y,w,h,t,dark,r=8){
  t=exStill()?0:t;
  c.save();rr(c,x,y,w,h,r);c.clip();
  c.strokeStyle=dark?'rgba(200,214,255,.55)':'rgba(110,135,250,.45)';c.lineWidth=1.1;c.lineCap='round';c.beginPath();
  const n=Math.max(4,Math.round(w/13));
  for(let i=0;i<n;i++){const sp=22+(i*7)%9,yy=((t*sp+i*37)%(h+10))-5,xx=x+((i*53+7)%Math.max(1,w))-yy*.18;c.moveTo(xx,y+yy);c.lineTo(xx-1.4,y+yy+5);}
  c.stroke();
  c.strokeStyle=dark?'rgba(210,220,255,.7)':'rgba(100,110,230,.55)';c.lineWidth=.9;
  for(let k=0;k<2;k++){const ph=((t*.6+k*.5)%1),rx=1.5+ph*7,cx=x+w*(k?.72:.28);c.globalAlpha=1-ph;c.beginPath();c.ellipse(cx,y+h-2.2,rx,rx*.28,0,0,7);c.stroke();}
  c.restore();
  c.save();c.fillStyle='#fff';
  for(let k=0;k<2;k++){const a=.35+.65*Math.abs(Math.sin(t*1.7+k*2.1)),sx=k?x+w-3:x+3,sy=k?y+h-4:y+3,s=2.6;c.globalAlpha=a;c.beginPath();c.moveTo(sx,sy-s);c.lineTo(sx+s*.3,sy-s*.3);c.lineTo(sx+s,sy);c.lineTo(sx+s*.3,sy+s*.3);c.lineTo(sx,sy+s);c.lineTo(sx-s*.3,sy+s*.3);c.lineTo(sx-s,sy);c.lineTo(sx-s*.3,sy-s*.3);c.closePath();c.fill();}
  c.restore();
}
/** The name's fill (a gradient from x0 to x1) and the title line's colour on a "Mưa rơi" pill. */
export function exInk(c,x0,x1,dark){
  const g=c.createLinearGradient(x0,0,x1,0);
  if(dark){g.addColorStop(0,'#c7d4ff');g.addColorStop(1,'#e2ccff');}else{g.addColorStop(0,'#3346c9');g.addColorStop(1,'#7a3fd6');}
  return {name:g,title:dark?'#cfc6ff':'#5a4fc6'};
}
/** 🗺️ The town's name tag (a Phaser text: one colour and background): the title's line, its ink and background. */
export function exTownTag(tt){
  const x=firstEx(tt);return x?{line:`${x.emoji} ${x.name}`,ink:'#3f37b5',tb:'#e8ecff'}:null;
}
