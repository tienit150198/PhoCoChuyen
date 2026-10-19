/** 🖼️ Khung danh hiệu (owner 18/10: "thêm logo, danh hiệu vào cho các top … với khung chat", "chỉ các danh hiệu top này
 * kia có giá trị thôi … sưu tầm cũng có"): the holder of a top title wears its avatar frame and chat bubble.
 * Which frame: the first of `tt` (live/honours.py, best first) that has one: a one-of-a-kind auction title, then the
 * weekly leaderboard titles (game/lb_titles.py: every tier of the main boards, the top 1 of a workplace); else the
 * worn title (`st.t`) when it is a builder's of a town project or an island owner's. Fair, wedding and bought titles
 * have none. Art: public/icons/frames/<n>_av.webp, <n>_chat.webp, cut from the owner's 72-board pack
 * (scripts/build_honour_frames.py); its sizes: ./honour-frames-data.js. Purely a view: nothing here is sent. */
import {escapeHTML as esc} from '../icons.js';
import {FRAMES} from './honour-frames-data.js';

const DIR='/icons/frames/';
// game/lb_titles.py BOARD_TITLES: [top 1, top 2–3, top 4–10]
const TIERS={all:['25','26','27'],titles:['36','35','34'],certs:['31','32','33'],wealth:['28','30','29'],collection:['60','59','59'],
  online:['73','71','69'],pets:['57','02','19'],island:['68','66','62']};   // 🏝️ Đảo đẹp (19/10): Chúa đảo's frame, the island bridge, the park   // 🐾 Thú cưng (19/10): the starry cat-and-dog frame, the orange cat, the bunny   // 🦉 Cú đêm của phố (owner's own board 18/10), the night-lantern frame, the sunset frame
// 🏆 Trùm <nghề>: the workplace's own art; the others wear "Top tổng hợp nghề" with the workplace's icon
const CAREER={milk_tea:'37',clothing:'38',pharmacy:'39',accounting:'40',pilot:'41',grocery:'42',police:'43',flight_attendant:'44',
  it_helpdesk:'45',lawyer:'46',group_accounting:'47',corp_accounting:'48',art_studio:'49',post_office:'50',banquet:'51',hotel:'52',
  customs:'53',delivery:'54',pet_care:'55',cafe_bakery:'21',florist:'14',teacher:'16',tax_payroll:'18',tra_da:'03',pet_shop:'20'};
const CAREER_ANY='56';   // "Cao thủ đa nghề" (owner 18/10: 72 "Top tổng hợp nghề" has the delivery box and helmet, it looked like Trùm giao hàng)
// game/spend_content.py TOWN_TITLES (the top sponsors) and LUX_TITLES (Chúa đảo), worn as `st.t`
const WORN={t_ct_cong_vien:'62',t_ct_rap_phim:'63',t_ct_thu_vien:'64',t_ct_san_vd:'65',t_ct_cau_dao:'66',t_ct_benh_vien:'67',
  t_ct_vang:'61',t_chu_dao:'68'};
// 🆓 Everyday frames anyone may choose (game/journey.py FREE_FRAMES, owner 18/10 "cho người ta chọn khung mặc định nữa"): k_<n>
const FREE={k_01:['01','🧋','Trà sữa trân châu'],k_02:['02','🐱','Mèo cam tinh nghịch'],k_05:['05','⭐','Chủ tiệm năm sao'],k_19:['19','🐰','Thỏ bánh mochi'],
  k_22:['22','👻','Phố ma dễ thương'],k_23:['23','🎄','Giáng sinh trong phố'],k_24:['24','🧧','Tết có lộc']};
const LB=/^lb_([a-z][a-z0-9_]{0,39})_([1-9]|10)$/;
const tierOf=r=>r===1?0:r<=3?1:2;

/** {n, tier} of one honour id: n the art, tier the chip's colour (0 top 1, 1 top 2–3, 2 top 4–10, 3 trùm, 4 độc bản). */
export function ofId(id){
  if(typeof id!=='string')return null;
  if(id.startsWith('dh_'))return {n:'60',tier:4};
  const m=LB.exec(id);if(!m)return null;
  const b=m[1],r=Number(m[2]);
  if(TIERS[b])return {n:TIERS[b][tierOf(r)],tier:tierOf(r)};
  if(r!==1||b==='pagoda')return null;   // a workplace: its top 1 only; nobody is the boss of a pagoda
  return {n:CAREER[b]||CAREER_ANY,tier:3,career:b};
}
/** The frame a player wears: {n, tier, career?} or null. Their own choice leads `tt` (live/honours.py, game/journey.py
 * HF_PICK): 'hf_off' wears none; a worn title's id (t_…) counts only while `st.t` is that title. */
export function pick(tt,st){
  if(Array.isArray(tt)){
    if(tt.includes('hf_off'))return null;
    for(const id of tt.slice(0,16)){
      const w=WORN[id];if(w){if(st?.t===id&&FRAMES[w])return {n:w,tier:5};continue;}
      const k=FREE[id];if(k){if(FRAMES[k[0]])return {n:k[0],tier:6};continue;}
      const f=ofId(id);if(f&&FRAMES[f.n])return f;}
  }
  const w=WORN[st?.t];return w&&FRAMES[w]?{n:w,tier:5}:null;
}
/** 🖼️ The frames this player may choose between (owner 18/10 "nhiều khung thì chủ động đổi khung được k"): the weekly
 * leaderboard titles held now (api.lbTitles, from the load), the worn title of a town project / an island
 * (journey.spend.wear.title); [{id, emoji, name, n}]. */
export function choices(api){
  const out=[];
  for(const h of api?.lbTitles||[]){const id=`lb_${h.board}_${h.rank}`,f=ofId(id);if(f&&FRAMES[f.n]&&!out.some(x=>x.id===id))out.push({id,emoji:h.emoji,name:h.name,label:h.label,n:f.n});}
  const t=api?.state?.journey?.spend?.wear?.title,w=WORN[t];
  if(w&&FRAMES[w]){const it=(api.content?.journey?.spend?.titles||[]).find(x=>x.id===t);out.push({id:t,emoji:it?.emoji||'🏗️',name:it?.name||'Danh hiệu đang đeo',label:'Phong cách',n:w});}
  return out;
}
const badge=(n,inner,cls='')=>{const d=FRAMES[n]?.av;if(!d)return '';ensureCss();const [w,h,cx,cy,r,sq]=d,box=2*r*PAD;
  return `<span class="hf-av hf-logo${cls}" aria-hidden="true" style="--hf-img:url('${DIR}${n}_av.webp');--hf-l:${pct(-(cx-box/2)/box)};--hf-t:${pct(-(cy-box/2)/box)};--hf-w:${pct(w/box)};--hf-h:${pct(h/box)}${sq?';--hf-rad:18%':''}"><b>${inner}</b></span>`;};
/** The "Khung" chooser (Hành trình → Danh hiệu): automatic and each frame held (a top title), the everyday frames
 * anyone may wear, and none. */
export function chooser(api){
  const L=choices(api),J=api.state.journey;ensureCss();
  const cur=J.hf_pick||'auto',off=L.length?'off':'auto';   // with no top title, automatic is no frame
  const opt=(id,art,name,sub,on=cur===id)=>`<button type="button" class="hf-opt${on?' on':''}" data-action="jrFrame" data-id="${esc(id)}" aria-pressed="${on}">${art}<span><b>${esc(name)}</b><small>${esc(sub)}</small></span></button>`;
  const top=L.length?[opt('auto',badge(L[0].n,'✨'),'Tự động','Luôn đeo khung của danh hiệu cao nhất'),...L.map(x=>opt(x.id,badge(x.n,esc(x.emoji)),x.name,x.label))]:[];
  const free=Object.entries(FREE).filter(([,k])=>FRAMES[k[0]]).map(([id,[n,emoji,name]])=>opt(id,badge(n,emoji),name,'Khung thường'));
  const none=opt(off,'<span class="hf-none" aria-hidden="true">🚫</span>','Không dùng khung','Avatar và tin nhắn như bình thường',cur==='off'||(!L.length&&cur==='auto'));
  const known=cur==='auto'||cur==='off'||FREE[cur]||L.some(x=>x.id===cur);
  const gone=known?'':`<p class="muted small">Danh hiệu đã chọn không còn giữ: đang dùng khung ${L.length?'tự động':'thường như cũ'}.</p>`;
  return `<section class="hf-pick" aria-label="Khung avatar và khung chat"><h3>🖼️ Khung avatar và khung chat</h3><p class="muted small">Khung hiện quanh avatar và tin nhắn của bạn ở Cả phố, khi đi dạo. Danh hiệu top có khung riêng; khung thường thì ai cũng chọn được. Không thích thì bỏ khung.</p>${gone}`+
    `${top.length?`<h4 class="hf-sub">Khung danh hiệu top</h4><div class="hf-opts">${top.join('')}</div>`:''}<h4 class="hf-sub">Khung thường</h4><div class="hf-opts">${free.join('')}${none}</div></section>`;
}

let ready=false;
function ensureCss(){
  if(ready||typeof document==='undefined')return;ready=true;
  const s=document.createElement('style');s.dataset.hfCss='';
  s.textContent=`.hf-av{position:relative;display:inline-grid;flex:none;isolation:isolate}
.hf-av>:first-child{border-radius:var(--hf-rad,50%)!important;overflow:hidden}
.hf-av::after{content:'';position:absolute;left:var(--hf-l);top:var(--hf-t);width:var(--hf-w);height:var(--hf-h);background:var(--hf-img) center/100% 100% no-repeat;pointer-events:none;z-index:1}
.hf-av[data-hf-icon]::before{content:attr(data-hf-icon);position:absolute;left:50%;top:-14%;transform:translateX(-50%);z-index:2;font-size:max(10px,38%);line-height:1;filter:drop-shadow(0 1px 1px rgba(0,0,0,.35));pointer-events:none}
.ch-bub.hf{position:relative;z-index:0;isolation:isolate;background:transparent!important;border:0!important;box-shadow:none!important;color:#3d2a1e!important;margin:var(--hf-mt) var(--hf-mr) var(--hf-mb) var(--hf-ml);padding:10px 22px 8px!important;min-width:var(--hf-minw,9.5em);min-height:3.4em!important}
.ch-bub.hf::before{content:'';position:absolute;z-index:-1;pointer-events:none;top:calc(-1*var(--hf-ot));bottom:calc(-1*var(--hf-ob));left:calc(-1*var(--hf-ol));right:calc(-1*var(--hf-or));
border-style:solid;border-color:transparent;border-width:0;border-image-source:var(--hf-img);border-image-slice:var(--hf-s) fill;border-image-width:var(--hf-wt) var(--hf-wr) var(--hf-wb) var(--hf-wl);border-image-repeat:stretch}
.ch-msg.mine .ch-bub.hf::before{left:calc(-1*var(--hf-or));right:calc(-1*var(--hf-ol));transform:scaleX(-1)}
.ch-msg.mine .ch-bub.hf{margin-left:var(--hf-mr);margin-right:var(--hf-ml)}
.ch-msg.mine .ch-bub.hf.hf-nf::before{left:calc(-1*var(--hf-ol));right:calc(-1*var(--hf-or));transform:none}
.ch-msg.mine .ch-bub.hf.hf-nf{margin-left:var(--hf-ml);margin-right:var(--hf-mr)}
.ch-bub.hf time{color:#7a6252!important;opacity:1;text-align:center}
.ch-bub.hf a.ch-link{color:#9a3412!important}
.hn-chip.hn-top{--hn-bg:linear-gradient(135deg,#fff3c4,#f6c945 55%,#e8a317);--hn-ink:#5a3700;--hn-line:rgba(160,104,0,.45);background:var(--hn-bg);box-shadow:inset 0 0 0 1px var(--hn-line),0 0 6px rgba(246,201,69,.55)}
.hn-chip.hn-t1{--hn-bg:linear-gradient(135deg,#ffffff,#dfe7f3 50%,#b7c4d9);--hn-ink:#26344d;--hn-line:rgba(70,90,130,.4);background:var(--hn-bg)}
.hn-chip.hn-t2{--hn-bg:linear-gradient(135deg,#fff1e2,#f6c49a 55%,#e3945e);--hn-ink:#5a2a08;--hn-line:rgba(150,80,30,.4);background:var(--hn-bg)}
.hn-chip.hn-t3{--hn-bg:linear-gradient(135deg,#f6ecff,#dcb8ff 50%,#f5a3c7);--hn-ink:#43176a;--hn-line:rgba(110,50,160,.4);background:var(--hn-bg)}
.hn-chip.hn-t4{--hn-bg:linear-gradient(120deg,#c9f7ff,#d9c8ff 45%,#ffd1ea 80%,#fff3c4);--hn-ink:#2e2370;--hn-line:rgba(80,60,170,.4);background:var(--hn-bg);box-shadow:inset 0 0 0 1px var(--hn-line),0 0 6px rgba(160,140,255,.5)}
html[data-theme="dem"] .hn-chip.hn-top{--hn-bg:linear-gradient(135deg,#7a5300,#c08a12 55%,#f2c440);--hn-ink:#fff8e1;--hn-line:rgba(255,220,120,.5)}
html[data-theme="dem"] .hn-chip.hn-t1{--hn-bg:linear-gradient(135deg,#3a4458,#66748e 60%,#a9b6cc);--hn-ink:#f4f7fc;--hn-line:rgba(220,230,250,.35)}
html[data-theme="dem"] .hn-chip.hn-t2{--hn-bg:linear-gradient(135deg,#5c2e10,#9a5527 60%,#d68a52);--hn-ink:#fff1e4;--hn-line:rgba(255,200,160,.35)}
html[data-theme="dem"] .hn-chip.hn-t3{--hn-bg:linear-gradient(135deg,#3e1763,#7a3ca8 55%,#b9568a);--hn-ink:#fbefff;--hn-line:rgba(240,200,255,.35)}
html[data-theme="dem"] .hn-chip.hn-t4{--hn-bg:linear-gradient(120deg,#1f5563,#4a3c8a 50%,#7d3a66);--hn-ink:#f3f0ff;--hn-line:rgba(210,200,255,.4)}
.hf-logo{width:34px;height:34px;margin:6px}
.lb-rank>.hf-logo{margin:0;width:34px;height:34px}.lb-row.hf-row .lb-rank{background:transparent}
.lb-week-emoji .hf-logo{width:26px;height:26px;margin:5px 12px 5px 6px}.lb-week-emoji .hf-logo>b{font-size:.85rem;background:var(--surface,#fff)}
.hf-pick{margin:0 0 14px}.hf-pick h3{margin:0 0 4px}.hf-sub{margin:12px 0 0;font-size:.82rem;color:var(--muted,#8a7768)}.hf-opts{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:8px}
.hf-opt{display:flex;align-items:center;gap:8px;min-width:0;padding:6px 10px 6px 4px;border-radius:14px;border:1px solid var(--line,rgba(0,0,0,.1));background:var(--surface,#fff);color:inherit;text-align:left;font:inherit;cursor:pointer}
.hf-opt.on{border-color:var(--accent,#c44b30);box-shadow:0 0 0 2px var(--accent-soft,rgba(196,75,48,.25))}
.hf-opt>span:last-child{display:grid;min-width:0}.hf-opt b{font-size:.86rem;line-height:1.25;overflow:hidden;text-overflow:ellipsis}.hf-opt small{font-size:.72rem;color:var(--muted,#8a7768);line-height:1.25}
.hf-opt .hf-logo{width:30px;height:30px;margin:7px}.hf-none{display:grid;place-items:center;flex:none;width:44px;height:44px;font-size:1.2rem}
.hf-logo>b{display:grid;place-items:center;width:100%;height:100%;background:var(--surface-2,#f6ecdf);font-size:.95rem;font-weight:800;color:var(--ink,#3a2a20)}`;
  document.head.append(s);
}
const pct=v=>`${Math.round(v*10000)/100}%`;
const PAD=1.08;   // the picture is a little bigger than the window, so the frame's inner rim covers its edge

/** Wrap an avatar's html in its frame: `html` unchanged when the player wears none. `icon`: an emoji drawn on top
 * (the workplace's, on the shared "Trùm" frame). */
export function avatar(tt,st,html,api=null){
  const f=pick(tt,st),d=f&&FRAMES[f.n]?.av;if(!d)return html;ensureCss();
  const [w,h,cx,cy,r,sq]=d,box=2*r*PAD;
  const icon=f.career&&!CAREER[f.career]?careerIcon(api,f.career):'';
  return `<span class="hf-av" style="--hf-img:url('${DIR}${f.n}_av.webp');--hf-l:${pct(-(cx-box/2)/box)};--hf-t:${pct(-(cy-box/2)/box)};--hf-w:${pct(w/box)};--hf-h:${pct(h/box)}${sq?';--hf-rad:18%':''}"${icon?` data-hf-icon="${esc(icon)}"`:''}>${html}</span>`;
}
/** The rank badge of a leaderboard row: the frame of that board's title around the rank. */
export function logo(board,rank){
  const f=ofId(`lb_${board}_${rank}`),d=f&&FRAMES[f.n]?.av;if(!d)return '';ensureCss();
  const [w,h,cx,cy,r,sq]=d,box=2*r*PAD;
  return `<span class="hf-av hf-logo" aria-hidden="true" style="--hf-img:url('${DIR}${f.n}_av.webp');--hf-l:${pct(-(cx-box/2)/box)};--hf-t:${pct(-(cy-box/2)/box)};--hf-w:${pct(w/box)};--hf-h:${pct(h/box)}${sq?';--hf-rad:18%':''}"><b>${rank}</b></span>`;
}
const K=.5;   // css px per pixel of the saved bubble art (2× for a sharp phone screen)
// art with words on it ("TRÙM", "TOP 10"): my own bubble keeps it as drawn, not mirrored (it read "MÙRT")
const WORDS=new Set(['27',...Array.from({length:19},(_,i)=>String(37+i))]);
/** ` hf` and the style attribute for a chat bubble of a player wearing a frame, or {cls:'',attrs:''}. */
export function bubble(tt,st){
  const f=pick(tt,st),d=f&&FRAMES[f.n]?.chat;if(!d)return {cls:'',attrs:''};ensureCss();
  const [w,h,x0,y0,x1,y1]=d,ry=Math.min(.32*(y1-y0),40),rx=Math.min(ry,.2*(x1-x0));
  // the cuts: from the data (scripts/build_honour_frames.py slices(): only a plain strip of the rim stretches), else the rim
  const s=(d.length>=10?d.slice(6,10):[y0+ry,w-x1+rx,h-y1+ry,x0+rx]).map(Math.round),px=v=>`${Math.round(v*K*10)/10}px`;
  const o=[y0,w-x1,h-y1,x0];
  return {cls:WORDS.has(f.n)?' hf hf-nf':' hf',attrs:` style="--hf-img:url('${DIR}${f.n}_chat.webp');--hf-s:${s.join(' ')};--hf-wt:${px(s[0])};--hf-wr:${px(s[1])};--hf-wb:${px(s[2])};--hf-wl:${px(s[3])};`+
    `--hf-minw:${px(x1-x0)};--hf-ot:${px(o[0])};--hf-or:${px(o[1])};--hf-ob:${px(o[2])};--hf-ol:${px(o[3])};--hf-mt:${px(o[0]*.7)};--hf-mr:${px(o[1])};--hf-mb:${px(o[2]*.8)};--hf-ml:${px(o[3])}"`};
}
/** The chip class of a title id: the top tiers wear colours (game/lb_titles.py), others the plain chip. */
export function chipClass(id){
  const f=ofId(id);if(!f)return '';ensureCss();
  return [' hn-top',' hn-t1',' hn-t2',' hn-t3',' hn-t4'][f.tier]||'';
}
function careerIcon(api,b){
  const ic=api?.content?.careers?.[b]?.meta?.icon;
  return {coffee:'☕',cake:'🍰',bag:'👜',book:'📚',calculator:'🧮',headphones:'🎧',shield:'🛡️',bike:'🛵',wrench:'🔧',tractor:'🚜',bell:'🔔',
    flower:'💐',basket:'🧺',truck:'🚛',sparkles:'✨',cart:'🛒',building:'🏢',home:'🏠',bed:'🛏️',people:'👥',settings:'💻',shirt:'👕',sun:'🌅',
    gift:'🎁',cross:'➕',flame:'🔥',paw:'🐾',fish:'🐠',camera:'📷',mail:'✉️',bowl:'🍜',scissors:'✂️',calendar:'📅',compass:'🧭',music:'🎵',palette:'🎨',send:'✈️'}[ic]||'🏆';
}
