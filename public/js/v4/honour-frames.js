/** 🖼️ Khung danh hiệu (owner 18/10: "thêm logo, danh hiệu vào cho các top … với khung chat", "chỉ các danh hiệu top này
 * kia có giá trị thôi … sưu tầm cũng có"): the holder of a top title wears its avatar frame and chat bubble.
 * Which frame: the first of `tt` (live/honours.py, best first) that has one: a one-of-a-kind auction title, then the
 * weekly leaderboard titles (game/lb_titles.py: every tier of the main boards, the top 1 of a workplace); else the
 * worn title (`st.t`) when it is a builder's of a town project or an island owner's. Fair, wedding and bought titles
 * have none. Art: public/icons/frames/<n>_av.webp, <n>_chat.webp, cut from the owner's 72-board pack
 * (scripts/build_honour_frames.py); its sizes: ./honour-frames-data.js. Purely a view: nothing here is sent.
 * #508 (23/10): a top title's frame wears its board's halo (and hue) and a medal of its rank; an auction title wears
 * a frame drawn for it alone (UQ); the chooser lists the auction titles owned. */
import {escapeHTML as esc} from '../icons.js';
import {FRAMES} from './honour-frames-data.js';
import {isEx,exOf,exCss,rainFrame,EX_LABEL} from './exclusive.js';   // 🌧️ an exclusive honour's frame (game/exclusive.py)

const DIR='/icons/frames/';
// game/lb_titles.py BOARD_TITLES: [top 1, top 2–3, top 4–10]
const TIERS={all:['25','26','27'],titles:['36','35','34'],certs:['31','32','33'],wealth:['28','30','29'],collection:['60','59','58'],
  online:['73','71','69'],pets:['57','20','35'],island:['68','66','62'],wings:['36','57','27'],   // 🪽 Cánh (23/10): the crowned laurels, the starry frame, the winged TOP 10
  arena:['65','20','57'],pet_cup:['25','26','27'],pet_war:['25','20'],
  race_drag_bike:['65','26'],race_drag_car:['65','26'],race_deo_bike:['65','26'],race_deo_car:['65','26']};   // 🏁 Đường đua Bến Mây (22/10): the stadium, the laurels   // ⚔️ 🏟️ 🛡️ the pet arena's boards (19/10): the stadium, the corgi, the starry pets; the laurels; the war's two tiers   // 🏝️ Đảo đẹp (19/10): Chúa đảo's frame, the island bridge, the park   // 🐾 Thú cưng (19/10): the starry cat-and-dog frame, the corgi, the hearts (#508: never an everyday frame)   // 🦉 Cú đêm của phố (owner's own board 18/10), the night-lantern frame, the sunset frame
/* 🏅 Player feedback #508 (lii, 23/10: "khung danh hiệu top có nhiều cái giống nhau và có mấy cái giống khung thường"): every
 * board wears its own look on top of the art: [hue turn of the art (deg; a board that shares another board's art is
 * recoloured), its halo]; the rank wears a medal (gold top 1, silver top 2–3, bronze top 4–10). No two (board, rank tier)
 * look alike (tests/honour_frames_508.mjs), and an everyday frame has neither halo nor medal. */
const LOOK={all:[0,'#f2b632'],titles:[0,'#b46cff'],certs:[0,'#3d7bff'],wealth:[0,'#25b86a'],collection:[0,'#d4a017'],
  online:[0,'#6a5cff'],pets:[0,'#ff7eb6'],island:[0,'#18c3c9'],wings:[200,'#7fd3ff'],arena:[330,'#ff5a4e'],pet_cup:[300,'#ff4fa3'],
  pet_war:[150,'#00b894'],race_drag_bike:[40,'#ff9f1c'],race_drag_car:[100,'#9bd832'],race_deo_bike:[160,'#2ec4b6'],race_deo_car:[230,'#c77dff'],
  wedding:[0,'#ff8fb1'],fish_big:[0,'#2fb4e8'],fish_dex:[0,'#36d1b0']};
const METAL=['g','s','b'];   // the medal of a rank tier: gold, silver, bronze
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
const tierOf=(r,b)=>b==='pet_war'?(r<=5?0:1):r===1?0:r<=3?1:2;   // 🛡️ game/lb_titles.py BOARD_TIERS: the champion bang's five, the runner-up's five

/* 👑 Khung độc bản (#508: "nếu vật phẩm đấu giá có ghi khung độc bản thì sẽ là 1 khung không ai có được"): each title of
 * the auction house (game/auction_content.py; one owner ever: the unique index auction_lots_item) wears a frame of its
 * own, drawn here and never a top board's art: [emoji, light, main, deep colour, ornament, how many]. Nothing is
 * stored: the frame follows the title's id, so a holder keeps theirs. A title missing here (a newer catalogue) still
 * gets one of its own from its id (uqSpec). tests/test_honour_frames_508.py: every catalogue title has its row. */
const UQ={
  dh_mat_trang:['🌕','#fbf6e4','#c9cbd6','#4b4f7a','moon',10],
  dh_rong_vang:['🐉','#fff1a8','#e0a21b','#8a2b0e','scale',14],
  dh_ky_lan:['🦄','#ffd6f5','#b28dff','#3fa9e8','star',10],
  dh_chia_khoa:['🗝️','#f3e2b3','#b08d57','#4a3a2a','key',8],
  dh_thuyen_truong:['⛵','#d6f3ff','#2f8fd8','#0d3b66','wave',12],
  dh_cong_tuoc:['🦚','#c8f7e1','#139e8a','#1d3c8f','eye',12],
  dh_bac_dau:['🌟','#fffbe0','#7aa2ff','#1b2a6b','ray',16],
  dh_den_long:['🏮','#ffd08a','#e8412c','#7a1010','lantern',8],
  dh_nghe_si:['🎻','#f9e0c0','#a0522d','#3b1f14','note',8],
  dh_gio_mua:['🍃','#e6ffd9','#5cbf6a','#1f6b45','leaf',12],
  dh_phuong_hoang:['🔥','#fff0a0','#ff7a1a','#b0101e','flame',12],
  dh_ngan_ha:['🌌','#e9d9ff','#6a4bd8','#121a4a','star',14],
  dh_hoang_hon:['🌇','#ffe1b0','#ff8a5c','#7b3b8f','ray',10],
  dh_hai_dang:['🗼','#fff7d1','#ffcc33','#1e4f7a','beam',8],
  dh_ca_phe:['☕','#f3e1c7','#9b6a43','#3e2618','bean',12],
  dh_mua_sao:['🌠','#fdf3ff','#ffb3e6','#4d5bd6','gem',12],
};
// one ornament, centred on 0,0 and pointing out of the ring (L light, M main, D deep)
const ORN={
  moon:'<path d="M2-6A6 6 0 1 0 2 6A4.5 4.5 0 1 1 2-6Z" fill="L" stroke="D" stroke-width="1"/>',
  scale:'<path d="M-5-3Q0-8 5-3V2Q0 7-5 2Z" fill="M" stroke="L" stroke-width="1.2"/>',
  star:'<path d="M0-7L2-2H7L3 1L4.5 6L0 3L-4.5 6L-3 1L-7-2H-2Z" fill="L" stroke="D" stroke-width=".8"/>',
  key:'<circle cy="-3" r="3" fill="none" stroke="L" stroke-width="2"/><path d="M0 0V7M0 4H3M0 6.5H2.5" stroke="L" stroke-width="2" fill="none"/>',
  wave:'<path d="M-6 2Q-3-4 0 0T6-1" fill="none" stroke="L" stroke-width="2.2" stroke-linecap="round"/>',
  eye:'<ellipse rx="4.5" ry="6.5" fill="M" stroke="L" stroke-width="1.2"/><circle r="2.2" fill="D"/>',
  ray:'<path d="M0-8L2 0L0 8L-2 0Z" fill="L"/>',
  lantern:'<path d="M0-8V-5M0 5V8" stroke="L" stroke-width="1.5"/><rect x="-4" y="-5" width="8" height="10" rx="4" fill="M" stroke="L" stroke-width="1.2"/>',
  note:'<path d="M1-6V3.5A2.5 2.5 0 1 1-1 1.5V-6L5-7.5V-4.5L1-3.5" fill="L" stroke="D" stroke-width=".6"/>',
  leaf:'<path d="M0-7Q5-2 0 7Q-5-2 0-7Z" fill="M" stroke="L" stroke-width="1.2"/>',
  flame:'<path d="M0-8C5-3 4 3 0 7C-4 3-5-3 0-8Z" fill="M" stroke="L" stroke-width="1"/><path d="M0-2C2 1 1 4 0 5C-1 4-2 1 0-2Z" fill="L"/>',
  beam:'<path d="M-2.5 6L0-8L2.5 6Z" fill="L"/>',
  bean:'<ellipse rx="3.5" ry="5.5" fill="M" stroke="L" stroke-width="1.2"/><path d="M0-5Q-1.5 0 0 5" stroke="D" fill="none"/>',
  gem:'<path d="M0-6L5 0L0 6L-5 0Z" fill="L" stroke="D" stroke-width="1"/>',
  heart:'<path d="M0 6C-6 1-6-5-2.5-5C-1-5 0-4 0-3C0-4 1-5 2.5-5C6-5 6 1 0 6Z" fill="M" stroke="L" stroke-width="1"/>',
  ring:'<circle cy="1" r="4.2" fill="none" stroke="L" stroke-width="2"/><path d="M-2.2-3.5L0-7L2.2-3.5Z" fill="M" stroke="L" stroke-width=".8"/>',
  hook:'<path d="M1-7V2.5A3 3 0 1 1-5 2.5" fill="none" stroke="M" stroke-width="2.2" stroke-linecap="round"/><path d="M-5 2.5L-6.6-.6" stroke="M" stroke-width="2" stroke-linecap="round"/><circle cx="1" cy="-7" r="1.6" fill="L" stroke="D" stroke-width=".8"/>',
  wave:'<path d="M-6 1Q-4.5-3-3 1T0 1T3 1T6 1" fill="none" stroke="L" stroke-width="2" stroke-linecap="round"/><path d="M-6 4.5Q-4.5 1-3 4.5T0 4.5T3 4.5T6 4.5" fill="none" stroke="M" stroke-width="1.6" stroke-linecap="round"/>',
  scale:'<path d="M-5-1A5 5 0 0 1 5-1L0 6Z" fill="M" stroke="L" stroke-width="1"/><path d="M-3-1A3 3 0 0 1 3-1" fill="none" stroke="D" stroke-width=".9"/>',
  fish:'<path d="M-6 0Q-1-5 4 0Q-1 5-6 0Z" fill="M" stroke="L" stroke-width="1"/><path d="M4 0L7-3V3Z" fill="L"/><circle cx="-3" cy="-.8" r=".9" fill="D"/>',
};
/* 💒 Boards with a frame drawn for them, not cut from the art pack: [top 1, top 2–3] like an auction title's row plus
 * the ribbon's text (game/lb_titles.py WEDDING, owner 23/10 "cái đám cưới nữa, mình cho danh hiệu với khung riêng"). */
const DRAWN={wedding:[['💒','#fff4f7','#f7a8c4','#a8556f','heart',12,'TOP 1'],['💐','#fffaf0','#f1d39a','#9a6b3c','ring',10,'TOP 3']],
  // 🎣 the fishing boards (owner 24/10 "khung riêng … nước, sóng, vảy cá, lưỡi câu vàng cho top 1"), three tiers each, with a medal of the rank
  fish_big:[['🐋','#fff6d2','#f2b632','#0b5f8a','hook',10,'TOP 1'],['🎣','#e9f9ff','#38b6e8','#0d5476','wave',12,'TOP 3'],['🐟','#eef9fc','#8fd3e8','#2b6f86','scale',14,'TOP 10']],
  fish_dex:[['📖','#fff8e6','#e9b949','#0e6a63','fish',10,'TOP 1'],['🐠','#eafff8','#3fcfae','#0f5e52','scale',12,'TOP 3'],['🐡','#f1fffa','#86dcc3','#2a7564','wave',14,'TOP 10']]};
const DRAWN_MEDAL=new Set(['fish_big','fish_dex']);   // 🎣 these drawn frames wear the rank's medal too
/** The tables, for tests/honour_frames_508.mjs. */
export const TABLES={TIERS,LOOK,FREE,UQ,CAREER,WORN,DRAWN};
const UQ_AV=[180,180,90,90,60,0];   // the drawn frame's box, like the art's (honour-frames-data.js av)
const UQ_RE=/^dh_[a-z0-9_]{1,40}$/;
/** [emoji, light, main, deep, ornament, count] of an auction title's frame. */
export function uqSpec(id){
  if(Object.prototype.hasOwnProperty.call(UQ,id))return UQ[id];
  let h=2166136261;for(const c of String(id))h=Math.imul(h^c.codePointAt(0),16777619)>>>0;
  const hue=h%360,orn=Object.keys(ORN);
  return ['👑',`hsl(${hue},90%,90%)`,`hsl(${hue},70%,55%)`,`hsl(${(hue+40)%360},65%,22%)`,orn[(h>>>9)%orn.length],8+((h>>>5)%9)];
}
const UQ_SVG=new Map();
/** The frame of an auction title as an svg data url: a ring in its colours, its ornaments, a crest on top, "01/01" below. */
export function uqSvg(id){return drawSvg(`uq:${id}`,uqSpec(id));}
/** 💒 The drawn frame of a board's tier (DRAWN), or ''. */
export function drawnSvg(board,tier){const d=DRAWN[board]?.[tier];return d?drawSvg(`dr:${board}:${tier}`,d):'';}
function drawSvg(key,spec){
  let u=UQ_SVG.get(key);if(u)return u;
  const [,L,M,D,orn,n,tag='01/01']=spec,C={L,M,D},shape=ORN[orn].replace(/"([LMD])"/g,(_,k)=>`"${C[k]}"`);
  let o='';
  for(let i=0;i<n;i++){const a=(i+.5)*360/n;if(a<24||a>336||Math.abs(a-180)<34)continue;   // clear of the crest and the ribbon
    o+=`<g transform="rotate(${Math.round(a*10)/10} 90 90) translate(90 22) scale(1.3)">${shape}</g>`;}
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180" viewBox="0 0 180 180"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${L}"/><stop offset=".5" stop-color="${M}"/><stop offset="1" stop-color="${D}"/></linearGradient></defs>`+
    `<circle cx="90" cy="90" r="68" fill="none" stroke="url(#g)" stroke-width="15"/><circle cx="90" cy="90" r="76" fill="none" stroke="${D}" stroke-width="2.5"/><circle cx="90" cy="90" r="60.8" fill="none" stroke="${L}" stroke-width="2"/>`+
    `<circle cx="90" cy="90" r="68" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.2" stroke-dasharray="1 6"/>${o}`+
    `<path d="M90 2L108 18L90 34L72 18Z" fill="url(#g)" stroke="${L}" stroke-width="2"/><path d="M48 150H132L124 160L132 170H48L56 160Z" fill="${D}" stroke="${L}" stroke-width="1.5"/>`+
    `<text x="90" y="164" text-anchor="middle" font-family="sans-serif" font-size="11" font-weight="800" letter-spacing="1" fill="${L}">${tag}</text></svg>`;
  u=`data:image/svg+xml,${encodeURIComponent(svg).replace(/'/g,'%27')}`;UQ_SVG.set(key,u);return u;
}

/** {n, tier, …} of one honour id: n the art, tier the chip's colour (0 top 1, 1 top 2–3, 2 top 4–10, 3 trùm, 4 độc bản,
 * 7 độc nhất); a board's {board, rank}; a workplace's {career}; an auction title's {uq: its id} (its own drawn frame, no
 * art); 🌧️ an exclusive honour's {ex: its id} ("Mưa rơi", ./exclusive.js). */
export function ofId(id){
  if(typeof id!=='string')return null;
  if(id.startsWith('ex_'))return isEx(id)?{n:null,tier:7,ex:id}:null;
  if(id.startsWith('dh_'))return UQ_RE.test(id)?{n:null,tier:4,uq:id}:null;
  const m=LB.exec(id);if(!m)return null;
  const b=m[1],r=Number(m[2]);
  if(DRAWN[b]){const t=tierOf(r,b);return DRAWN[b][t]?{n:null,tier:t,board:b,rank:r,drawn:true}:{n:undefined,tier:t,board:b,rank:r};}   // 💒 top 3 only
  if(TIERS[b])return {n:TIERS[b][tierOf(r,b)],tier:tierOf(r,b),board:b,rank:r};
  if(r!==1||b==='pagoda')return null;   // a workplace: its top 1 only; nobody is the boss of a pagoda
  return {n:CAREER[b]||CAREER_ANY,tier:3,career:b};
}
const geo=f=>f?.uq||f?.drawn||f?.ex?UQ_AV:FRAMES[f?.n]?.av;
const spec=f=>f.uq?uqSpec(f.uq):DRAWN[f.board][f.tier];   // a drawn frame's row
const svgOf=f=>f.ex?rainFrame(false):f.uq?uqSvg(f.uq):drawnSvg(f.board,f.tier);   // 🌧️ the still frame (the stylesheet animates it)
const has=f=>Boolean(f&&geo(f));
/** 🏅 How a frame shows it is an honour (#508): {fx: the art's filter, cls, medal: the text on its medal (a board's rank)},
 * or null: an everyday frame and a town project's stay as drawn. */
export function look(f){
  if(!f)return null;
  if(f.ex){exCss();return {fx:'drop-shadow(0 0 4px #8fa8ff)',cls:' hf-ex',medal:''};}   // 🌧️ Mưa rơi
  if(f.uq){const [,,M]=uqSpec(f.uq);return {fx:`drop-shadow(0 0 4px ${M})`,cls:' hf-uq',medal:''};}
  if(f.drawn){const [,,M]=spec(f),halo=LOOK[f.board]?.[1]||M,m=METAL[f.tier]||'b',medal=DRAWN_MEDAL.has(f.board);   // 💒 its ribbon says TOP 1 / TOP 3: no medal (🎣 the fish boards wear one)
    return {fx:`drop-shadow(0 0 4px ${halo})`,cls:` hf-uq hf-top${medal?` hf-m${m}`:''}`,medal:medal?String(f.rank):'',hue:0,halo,metal:m,drawn:true};}
  if(f.board&&LOOK[f.board]){const [hue,halo]=LOOK[f.board],m=METAL[f.tier]||'b';
    return {fx:`${hue?`hue-rotate(${hue}deg) `:''}drop-shadow(0 0 3px ${halo})`,cls:` hf-top hf-m${m}`,medal:f.board==='pet_war'?String(f.tier+1):String(f.rank),hue,halo,metal:m};}
  if(f.tier===3)return {fx:'drop-shadow(0 0 3px #f2b632)',cls:' hf-top',medal:''};   // 🏆 Trùm: the art itself says TRÙM
  return null;
}
/** The frame a player wears: {n, tier, career?, board?, uq?} or null. Their own choice leads `tt` (live/honours.py,
 * game/journey.py HF_PICK): 'hf_off' wears none; a worn title's id (t_…) counts only while `st.t` is that title. */
export function pick(tt,st){
  if(Array.isArray(tt)){
    if(tt.includes('hf_off'))return null;
    for(const id of tt.slice(0,16)){
      const w=WORN[id];if(w){if(st?.t===id&&FRAMES[w])return {n:w,tier:5};continue;}
      const k=FREE[id];if(k){if(FRAMES[k[0]])return {n:k[0],tier:6};continue;}
      const f=ofId(id);if(has(f))return f;}
  }
  const w=WORN[st?.t];return w&&FRAMES[w]?{n:w,tier:5}:null;
}
/** 🖼️ The frames this player may choose between (owner 18/10 "nhiều khung thì chủ động đổi khung được k"): the titles
 * won at the auction house (journey.uniq.own; #508: they were missing, "không thấy trong danh sách khung để đổi"), the
 * weekly leaderboard titles held now (api.lbTitles, from the load), the worn title of a town project / an island
 * (journey.spend.wear.title); [{id, emoji, name, label, n, f}]. */
export function choices(api){
  const out=[],J=api?.state?.journey,items=api?.content?.journey?.auction?.items||[];
  const own=J?.uniq?.own&&typeof J.uniq.own==='object'?J.uniq.own:{};
  for(const [id,x] of Object.entries(own)){
    if(x?.k!=='title'||!UQ_RE.test(id))continue;
    const it=items.find(i=>i?.id===id);
    out.push({id,emoji:it?.emoji||uqSpec(id)[0],name:String(x.t||it?.name||'Danh hiệu độc bản'),label:'Độc bản · Nhà đấu giá',n:null,f:{n:null,tier:4,uq:id}});
  }
  for(const x of api?.exTitles||[]){const k=exOf(x?.id);if(k&&!out.some(o=>o.id===k.id))out.push({id:k.id,emoji:k.emoji,name:k.frame,label:`${EX_LABEL} · ${k.name}`,n:null,f:{n:null,tier:7,ex:k.id}});}   // 🌧️ first
  for(const h of api?.lbTitles||[]){const id=`lb_${h.board}_${h.rank}`,f=ofId(id);if(has(f)&&!out.some(x=>x.id===id))out.push({id,emoji:h.emoji,name:h.name,label:h.label,n:f.n,f});}
  const t=J?.spend?.wear?.title,w=WORN[t];
  if(w&&FRAMES[w]){const it=(api.content?.journey?.spend?.titles||[]).find(x=>x.id===t);out.push({id:t,emoji:it?.emoji||'🏗️',name:it?.name||'Danh hiệu đang đeo',label:'Phong cách',n:w,f:{n:w,tier:5}});}
  return out;
}
/** {cls, style, lk} of the span around a picture wearing frame `f`, or null. */
function wrap(f,cls=''){
  const d=geo(f);if(!d)return null;ensureCss();
  const [w,h,cx,cy,r,sq]=d,box=2*r*PAD,lk=look(f);
  return {lk,cls:`hf-av${lk?lk.cls:''}${cls}`,style:`--hf-img:url('${f.uq||f.drawn||f.ex?svgOf(f):`${DIR}${f.n}_av.webp`}');--hf-l:${pct(-(cx-box/2)/box)};--hf-t:${pct(-(cy-box/2)/box)};--hf-w:${pct(w/box)};--hf-h:${pct(h/box)}${sq?';--hf-rad:18%':''}${lk?`;--hf-fx:${lk.fx}`:''}`};
}
const badge=(f,inner,cls='')=>{const a=wrap(f,` hf-logo${cls}`);return a?`<span class="${a.cls}" aria-hidden="true" style="${a.style}"><b>${inner}</b></span>`:'';};
/** 👑 An auction title's own frame around its emoji (the lot card, Của tôi), or ''. */
export function uqBadge(id,emoji){return UQ_RE.test(String(id))?badge({n:null,tier:4,uq:id},esc(emoji||uqSpec(id)[0]),' hf-uq-big'):'';}
/** The "Khung" chooser (Hành trình → Danh hiệu): automatic and each frame held (an auction title, a top title), the
 * everyday frames anyone may wear, and none. */
export function chooser(api){
  const L=choices(api),J=api.state.journey;ensureCss();
  const cur=J.hf_pick||'auto',off=L.length?'off':'auto';   // with no top title, automatic is no frame
  const opt=(id,art,name,sub,on=cur===id)=>`<button type="button" class="hf-opt${on?' on':''}" data-action="jrFrame" data-id="${esc(id)}" aria-pressed="${on}">${art}<span><b>${esc(name)}</b><small>${esc(sub)}</small></span></button>`;
  const top=L.length?[opt('auto',badge(L[0].f,'✨'),'Tự động','Luôn đeo khung của danh hiệu cao nhất'),...L.map(x=>opt(x.id,badge(x.f,esc(x.emoji)),x.name,x.label))]:[];
  const free=Object.entries(FREE).filter(([,k])=>FRAMES[k[0]]).map(([id,[n,emoji,name]])=>opt(id,badge({n,tier:6},emoji),name,'Khung thường'));
  const none=opt(off,'<span class="hf-none" aria-hidden="true">🚫</span>','Không dùng khung','Avatar và tin nhắn như bình thường',cur==='off'||(!L.length&&cur==='auto'));
  const known=cur==='auto'||cur==='off'||FREE[cur]||L.some(x=>x.id===cur);
  const gone=known?'':`<p class="muted small">Danh hiệu đã chọn không còn giữ: đang dùng khung ${L.length?'tự động':'thường như cũ'}.</p>`;
  return `<section class="hf-pick" aria-label="Khung avatar và khung chat"><h3>🖼️ Khung avatar và khung chat</h3><p class="muted small">Khung hiện quanh avatar và tin nhắn của bạn ở Cả phố, khi đi dạo. Danh hiệu top và độc bản có khung riêng, có huy hiệu; khung thường thì ai cũng chọn được. Không thích thì bỏ khung.</p>${gone}`+
    `${top.length?`<h4 class="hf-sub">Khung danh hiệu top và độc bản</h4><div class="hf-opts">${top.join('')}</div>`:''}<h4 class="hf-sub">Khung thường</h4><div class="hf-opts">${free.join('')}${none}</div></section>`;
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
.hf-av::after{filter:var(--hf-fx,none)}.ch-bub.hf::before{filter:var(--hf-fx,none)}
.hf-av[data-hf-rank]::before,.ch-bub.hf[data-hf-rank]::after{content:attr(data-hf-rank);position:absolute;z-index:2;display:grid;place-items:center;box-sizing:border-box;width:17px;height:17px;border-radius:50%;font:800 10px/1 system-ui,sans-serif;color:var(--hf-metal-ink,#4a2c00);background:var(--hf-metal,#f6c945);box-shadow:0 0 0 1.5px #fff,0 1px 3px rgba(0,0,0,.35);pointer-events:none}
.hf-av[data-hf-rank]::before{right:-4%;top:-4%}
.ch-bub.hf[data-hf-rank]::after{top:-6px;left:-4px}.ch-msg.mine .ch-bub.hf[data-hf-rank]::after{left:auto;right:-4px}
.hf-mg{--hf-metal:radial-gradient(circle at 35% 30%,#fffbe0,#f6c945 45%,#b07a0c);--hf-metal-ink:#4a2c00}
.hf-ms{--hf-metal:radial-gradient(circle at 35% 30%,#fff,#d3dbe8 45%,#7f8ca3);--hf-metal-ink:#1f2a40}
.hf-mb{--hf-metal:radial-gradient(circle at 35% 30%,#ffe6cc,#d38b4f 45%,#8a4a1c);--hf-metal-ink:#3a1604}
.ch-bub.hf-uq{position:relative;margin-top:10px;padding:11px 16px 7px!important;border:2.5px solid transparent!important;border-radius:16px!important;color:#3d2a1e!important;background:linear-gradient(var(--uq-paper,#fffaf2),var(--uq-paper,#fffaf2)) padding-box,linear-gradient(135deg,var(--uq-a),var(--uq-b) 40%,var(--uq-c) 72%,var(--uq-a)) border-box!important;box-shadow:0 0 9px -1px var(--uq-b)!important}
.ch-bub.hf-uq::before{content:var(--uq-emo);position:absolute;top:-12px;left:12px;display:grid;place-items:center;width:22px;height:22px;border-radius:50%;font-size:12px;line-height:1;background:linear-gradient(135deg,var(--uq-a),var(--uq-b));box-shadow:0 0 0 2px var(--uq-c),0 1px 3px rgba(0,0,0,.3);pointer-events:none}
.ch-bub.hf-uq::after{content:var(--uq-tag,'01/01');position:absolute;top:-8px;right:12px;padding:1px 7px;border-radius:999px;font:800 9px/1.5 system-ui,sans-serif;letter-spacing:.06em;color:var(--uq-a);background:var(--uq-c);box-shadow:0 0 0 1.5px var(--uq-a);pointer-events:none}
.ch-msg.mine .ch-bub.hf-uq::before{left:auto;right:12px}.ch-msg.mine .ch-bub.hf-uq::after{right:auto;left:12px}
.ch-bub.hf-uq time{color:#7a6252!important;opacity:1}.ch-bub.hf-uq a.ch-link{color:#9a3412!important}
html[data-theme="dem"] .ch-bub.hf-uq{--uq-paper:#2a2233;color:#f6efff!important}html[data-theme="dem"] .ch-bub.hf-uq time{color:#cbbfd9!important}html[data-theme="dem"] .ch-bub.hf-uq a.ch-link{color:#ffc58a!important}
.hf-av.hf-uq[data-hf-icon]::before{font-size:14px;top:-17%}.hf-uq-big.hf-logo{width:58px;height:58px;margin:12px}.hf-uq-big>b{font-size:1.6rem}
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
  const f=pick(tt,st),a=wrap(f);if(!a)return html;
  // the crest: the workplace's emoji on the shared "Trùm" frame, the title's own on an auction frame
  const icon=f.ex?'':f.uq?(auctionEmoji(api,f.uq)||uqSpec(f.uq)[0]):f.drawn?spec(f)[0]:f.career&&!CAREER[f.career]?careerIcon(api,f.career):'';
  const medal=a.lk?.medal;
  return `<span class="${a.cls}" style="${a.style}"${icon?` data-hf-icon="${esc(icon)}"`:''}${medal?` data-hf-rank="${esc(medal)}"`:''}>${html}</span>`;
}
/** The rank badge of a leaderboard row: the frame of that board's title around the rank. */
export function logo(board,rank){
  return badge(ofId(`lb_${board}_${rank}`),esc(rank));
}
const K=.5;   // css px per pixel of the saved bubble art (2× for a sharp phone screen)
// art with words on it ("TRÙM", "TOP 10"): my own bubble keeps it as drawn, not mirrored (it read "MÙRT")
const WORDS=new Set(['27',...Array.from({length:19},(_,i)=>String(37+i))]);
const cssStr=v=>`'${String(v).replace(/[\'"<>&\n]/g,'')}'`;
/** ` hf` and the style attribute for a chat bubble of a player wearing a frame, or {cls:'',attrs:''}. An auction
 * title's bubble (` hf-uq`) is drawn in its own colours with its crest and "01/01"; a top board's wears its medal. */
export function bubble(tt,st){
  const f=pick(tt,st);
  if(f?.ex){exCss();return {cls:' hf-ex',attrs:''};}   // 🌧️ Mưa rơi: glass, rain behind the words, ripples (./exclusive.js)
  if(f?.uq||f?.drawn){ensureCss();const [emo,L,M,D,,,tag]=spec(f);
    return {cls:' hf-uq',attrs:` style="--uq-a:${L};--uq-b:${M};--uq-c:${D};--uq-emo:${cssStr(emo)}${tag?`;--uq-tag:${cssStr(tag)}`:''}"`};}
  const d=f&&FRAMES[f.n]?.chat;if(!d)return {cls:'',attrs:''};ensureCss();
  const [w,h,x0,y0,x1,y1]=d,ry=Math.min(.32*(y1-y0),40),rx=Math.min(ry,.2*(x1-x0));
  // the cuts: from the data (scripts/build_honour_frames.py slices(): only a plain strip of the rim stretches), else the rim
  const s=(d.length>=10?d.slice(6,10):[y0+ry,w-x1+rx,h-y1+ry,x0+rx]).map(Math.round),px=v=>`${Math.round(v*K*10)/10}px`;
  const o=[y0,w-x1,h-y1,x0],lk=look(f);
  return {cls:`${WORDS.has(f.n)?' hf hf-nf':' hf'}${lk?lk.cls:''}`,attrs:` style="--hf-img:url('${DIR}${f.n}_chat.webp');--hf-s:${s.join(' ')};--hf-wt:${px(s[0])};--hf-wr:${px(s[1])};--hf-wb:${px(s[2])};--hf-wl:${px(s[3])};`+
    `--hf-minw:${px(x1-x0)};--hf-ot:${px(o[0])};--hf-or:${px(o[1])};--hf-ob:${px(o[2])};--hf-ol:${px(o[3])};--hf-mt:${px(o[0]*.7)};--hf-mr:${px(o[1])};--hf-mb:${px(o[2]*.8)};--hf-ml:${px(o[3])}${lk?`;--hf-fx:${lk.fx}`:''}"${lk?.medal?` data-hf-rank="${esc(lk.medal)}"`:''}`};
}
const auctionEmoji=(api,id)=>(api?.content?.journey?.auction?.items||[]).find(x=>x?.id===id)?.emoji||'';
/** The chip class of a title id: the top tiers wear colours (game/lb_titles.py), others the plain chip. */
export function chipClass(id){
  const f=ofId(id);if(!f)return '';ensureCss();
  if(f.ex){exCss();return ' hn-ex';}   // 🌧️ a rain shimmer
  return [' hn-top',' hn-t1',' hn-t2',' hn-t3',' hn-t4'][f.tier]||'';
}
function careerIcon(api,b){
  const ic=api?.content?.careers?.[b]?.meta?.icon;
  return {coffee:'☕',cake:'🍰',bag:'👜',book:'📚',calculator:'🧮',headphones:'🎧',shield:'🛡️',bike:'🛵',wrench:'🔧',tractor:'🚜',bell:'🔔',
    flower:'💐',basket:'🧺',truck:'🚛',sparkles:'✨',cart:'🛒',building:'🏢',home:'🏠',bed:'🛏️',people:'👥',settings:'💻',shirt:'👕',sun:'🌅',
    gift:'🎁',cross:'➕',flame:'🔥',paw:'🐾',fish:'🐠',camera:'📷',mail:'✉️',bowl:'🍜',scissors:'✂️',calendar:'📅',compass:'🧭',music:'🎵',palette:'🎨',send:'✈️'}[ic]||'🏆';
}
