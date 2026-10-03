/** Tủ đồ, the art: how the player's character is drawn from the look saved in state.wardrobe
 * (game/wardrobe.py holds the rules, names and prices under the same ids).
 *   lookOf(state)            the look to draw (the saved one, or the gender's default = the pre-0.9.5 look)
 *   portrait(look,gender,…)  the round bust used on the journey card, stories, the board, the ranking…
 *   figure(state), paint*()  the walking character in a workplace (BobaWorld.character, canvas)
 *   look.tint                the colours of what is worn {item id: colour id} (bảng màu: accessories from
 *                            state.wardrobe_colors, clothes and shoes from state.colors): every painter above reads
 *                            it (accPaint, art), so portraits, the street, the wedding and its photos all match
 * Small and always loaded; the wardrobe sheet itself (v4/wardrobe.js) loads on first use. The chat face (v4/face.js)
 * draws the wardrobe top and accessory with art(), topDetail() and accBust(). */
import {R,E,L,P,heart,bloom} from '../scenes/kit.js';

export const SLOTS=['hair','shade','skin','top','bottom','shoes','acc'];
// Same as game/wardrobe.py DEFAULTS (tests/test_wardrobe.py compares them).
const DEFAULTS={"male":{"hair":"toc_ngan","shade":"mau_nau","skin":"da_sang","top":"ao_quen","bottom":"quan_xam","shoes":"giay_nau","acc":"pk_khong","uniform":true},"female":{"hair":"toc_bui","shade":"mau_nau","skin":"da_sang","top":"ao_quen","bottom":"quan_kem","shoes":"giay_nau","acc":"pk_khong","uniform":true},"none":{"hair":"toc_ngan","shade":"mau_nau","skin":"da_sang","top":"ao_quen","bottom":"quan_kem","shoes":"giay_nau","acc":"pk_khong","uniform":true}};

/* ---- art per item id ---- */
export const ART={
  hair:{toc_ngan:{},toc_bui:{long:1},toc_dai:{long:1},toc_bob:{},toc_duoi_ngua:{},toc_xoan:{}},
  shade:{mau_nau:{c:'#5b4436'},mau_den:{c:'#2f2826'},mau_mat_ong:{c:'#9a6a3f'},mau_hong:{c:'#d98fa3'},mau_xanh_khoi:{c:'#6f8ea8'},mau_bach_kim:{c:'#e3d5b8'}},
  skin:{da_sang:{c:'#f5cfae',neck:'#e6b692',face:'#f8dcc2',ear:'#f3ceb1',hand:'#f5d5ba'},da_hong:{c:'#f8d8c6',neck:'#eab9a3',face:'#fbe2d4',ear:'#f2c9b6',hand:'#f7dccb'},
    da_trung:{c:'#e3b389',neck:'#c9966d',face:'#ebbf98',ear:'#dcaa80',hand:'#e6b890'},da_ngam:{c:'#c48d64',neck:'#a8744e',face:'#cc976e',ear:'#b9825b',hand:'#c79168'}},
  // tx: which shade of a chosen colour (look.tint) the detail takes, 'd' darker or 'l' lighter (none: it keeps its own).
  top:{ao_quen:{c:null},ao_thun_kem:{c:'#efdfc4',d:'tee',x:'#dcc7a6',tx:'d'},ao_thun_xanh:{c:'#9cc39a',d:'tee',x:'#84ab82',tx:'d'},ao_so_mi:{c:'#f7f4ec',d:'collar',x:'#ddd6c6',tx:'d'},
    ao_len:{c:'#c9806a',d:'knit',x:'#e8b49f',tx:'l'},ao_hoodie:{c:'#9d8cc4',d:'hood',x:'#8676b0',tx:'d'},ao_dai:{c:'#5d9ea0',d:'aodai',x:'#f2d38a',long:1},
    ao_chi_may:{c:'#e7a0a8',d:'logo',x:'#fff5ee'},ao_hoa:{c:'#7cc0c8',d:'flowers',x:'#fff3d6'},ao_vest:{c:'#56627a',d:'suit',x:'#9b5b6b'},
    ao_cuoi:{c:'#c8453c',d:'aodai',x:'#f2c86a',long:1},vest_cuoi:{c:'#3e4a5c',d:'suit',x:'#c8453c',bow:1}},
  bottom:{quan_kem:{c:'#f0d3b8'},quan_xam:{c:'#6f6a78'},quan_jean:{c:'#5b7ea6'},quan_short:{c:'#c9a978',short:1},vay_xoe:{c:'#e39ab0',skirt:'flare'},vay_dai:{c:'#9fb7d8',skirt:'long'}},
  shoes:{giay_nau:{c:'#785c51'},dep_lao:{c:'#5b8fc0',flat:1},giay_trang:{c:'#f4f1ea',line:'#cfc8bb'},giay_do:{c:'#c9514a'},bot_den:{c:'#3d3533',tall:1}},
  // Each accessory's own colours ("Màu gốc"): c main, d the darker part (frame, band, knot, strap), l the light part.
  acc:{pk_khong:{},kinh_tron:{c:'#6b4f3f',d:'#6b4f3f'},kinh_ram:{c:'#3a3230',d:'#3a3230'},non_la:{c:'#ecd394',d:'#c9a95e',line:'#d6b86f',brim:'#d9bb72'},
    mu_len:{c:'#d8736a',d:'#b95a52',l:'#f3e6d6'},no_toc:{c:'#e0708a',d:'#c85873'},tui_cheo:{c:'#b07a4f',d:'#8a5a3c',l:'#d9a878'}},
};
/* Bảng màu (1.3.1 accessories, góp ý #70; then clothes, shoes and furniture): look.tint = {item id: colour id};
 * ids, names and prices in game/wardrobe.py COLORS. c main, d darker, l lighter. Furniture: v4/deco-art.js tint.
 * A null-prototype map: an id from someone else's look ("__proto__") finds nothing. */
export const ACC_COLORS=Object.freeze(Object.assign(Object.create(null),{
  den:{c:'#3a3436',d:'#221e1f',l:'#6b6365'},nau:{c:'#8a5a3c',d:'#5f3c27',l:'#c08f68'},vang:{c:'#e0b43f',d:'#b0821f',l:'#f6df8f'},
  bac:{c:'#c7ccd4',d:'#8b94a1',l:'#eef1f5'},hong:{c:'#f4b0c4',d:'#d77d9a',l:'#fde2ea'},do:{c:'#d2453d',d:'#9e2c27',l:'#f19089'},
  dao:{c:'#f6a882',d:'#d67b55',l:'#fdd5c1'},mint:{c:'#8fd5c0',d:'#4e9f87',l:'#d3f2e8'},navy:{c:'#3a4e7c',d:'#24345a',l:'#7d8fba'},
  lavender:{c:'#bba6e2',d:'#8a72c0',l:'#e5dcf7'},trang:{c:'#f8f4ec',d:'#c8bead',l:'#ffffff'},
}));
/** The colours an accessory is drawn in: its chosen colour (look.tint), else its own. */
export function accPaint(L,a=L?.acc){
  const base=ART.acc[a]||{},t=ACC_COLORS[L?.tint?.[a]];
  return t&&base.c?{...base,...t,line:t.d,brim:t.d}:base;
}
export const PALETTE=ACC_COLORS;
/** The slots whose item may carry a colour (hair has its own shades). */
export const TINT_SLOTS=['top','bottom','shoes','acc'];
const CLASSIC={female:'#e39a8a',male:'#78a3b6'};   // "Áo quen thuộc" on the portrait (in a workplace: the place's colour)

export function defaultLook(gender){return {...DEFAULTS[gender==='male'||gender==='female'?gender:'none']};}
/** The colour item `id` is worn in, from the state (null: its own): accessories in state.wardrobe_colors (1.3.1),
 * clothes and shoes in state.colors. */
export function wornColor(state,id){
  const c=(ART.acc[id]?state?.wardrobe_colors?.wear:state?.colors?.wear)?.[id];
  return typeof c==='string'&&ACC_COLORS[c]?c:null;
}
/** The look to draw for this state: saved slots that this build knows, the gender's default elsewhere, and the
 * colours of what is worn (tint, only those that are not the item's own). */
export function lookOf(state){
  const d=defaultLook(state?.journey?.gender),w=state?.wardrobe?.look;
  if(w&&typeof w==='object'){
    for(const k of SLOTS)if(typeof w[k]==='string'&&ART[k][w[k]])d[k]=w[k];
    if(typeof w.uniform==='boolean')d.uniform=w.uniform;
  }
  const tint={};
  for(const k of TINT_SLOTS){const id=d[k],col=wornColor(state,id);if(col&&(k!=='acc'||ART.acc[id]?.c))tint[id]=col;}
  if(Object.keys(tint).length)d.tint=tint;
  return d;
}
/** An item's art in the colour it is worn in (look.tint): clothes and shoes take c, their detail its d or l shade. */
export const art=(L,slot)=>{
  const b=ART[slot][L[slot]]||ART[slot][DEFAULTS.none[slot]];
  if(slot!=='top'&&slot!=='bottom'&&slot!=='shoes')return b;
  const t=ACC_COLORS[L?.tint?.[L[slot]]];if(!t||!ART[slot][L[slot]])return b;
  const o={...b,c:t.c};if(b.tx)o.x=t[b.tx];if(b.line)o.line=t.d;return o;
};
export const hairColour=L=>art(L,'shade').c;
export const topColour=(L,gender)=>art(L,'top').c||CLASSIC[gender]||'#c3ab83';

/* ---- the bust (80×80) ---- */
function hairBack(h,c){
  switch(h){
    case'toc_bui':return `<circle cx="40" cy="12" r="9" fill="${c}"/><path d="M18 44C12 10 68 10 62 44L64 68H16Z" fill="${c}"/>`;
    case'toc_dai':return `<path d="M18 44C12 10 68 10 62 44L65 72H15Z" fill="${c}"/>`;
    case'toc_bob':return `<path d="M17 50C11 10 69 10 63 50Q52 56 40 54Q28 56 17 50Z" fill="${c}"/>`;
    case'toc_duoi_ngua':return `<path d="M52 18Q74 20 70 46Q67 60 59 54Q66 40 54 28Z" fill="${c}"/>`;
    case'toc_xoan':return `<g fill="${c}"><circle cx="23" cy="27" r="10"/><circle cx="31" cy="16" r="11"/><circle cx="48" cy="15" r="11"/><circle cx="57" cy="26" r="10"/><circle cx="61" cy="39" r="8"/><circle cx="19" cy="39" r="8"/></g>`;
  }
  return '';
}
function hairFront(h,c){
  switch(h){
    case'toc_ngan':return `<path d="M20 37Q18 13 40 12Q62 13 60 37Q56 25 45 22Q35 30 20 37Z" fill="${c}"/>`;
    case'toc_bob':return `<path d="M21 35Q20 14 40 14Q60 14 59 35Q51 28 40 29Q29 28 21 35Z" fill="${c}"/>`;
    case'toc_xoan':return `<path d="M21 34Q22 17 40 16Q58 17 59 34Q54 26 47 27Q42 22 36 27Q28 25 21 34Z" fill="${c}"/>`;
    case'toc_duoi_ngua':return `<path d="M21 38Q21 15 40 15Q59 15 59 38Q52 25 41 22Q31 26 21 38Z" fill="${c}"/><circle cx="56" cy="22" r="3" fill="#e0708a"/>`;
  }
  return `<path d="M21 38Q21 15 40 15Q59 15 59 38Q52 25 41 22Q31 26 21 38Z" fill="${c}"/>`;
}
export function topDetail(t){
  const x=t.x;
  switch(t.d){
    case'tee':return `<path d="M33 61q7 5 14 0" fill="none" stroke="${x}" stroke-width="2.4"/>`;
    case'collar':return `<path d="M31 60L40 66L35 71ZM49 60L40 66L45 71Z" fill="${x}"/><circle cx="40" cy="71" r="1.1" fill="#bdb5a3"/><circle cx="40" cy="76" r="1.1" fill="#bdb5a3"/>`;
    case'knit':return `<path d="M17 70H63M14 76H66" stroke="${x}" stroke-width="2.6"/><path d="M33 61q7 5 14 0" fill="none" stroke="${x}" stroke-width="3"/>`;
    case'hood':return `<ellipse cx="40" cy="61" rx="15" ry="5.5" fill="${x}"/><path d="M36 64L35 75M44 64L45 75" stroke="#f3ecff" stroke-width="1.5" stroke-linecap="round"/>`;
    case'aodai':return `<rect x="33" y="57" width="14" height="6" rx="2.5" fill="${x}"/><path d="M40 63Q48 66 55 73" fill="none" stroke="${x}" stroke-width="1.8"/><g fill="${x}"><circle cx="24" cy="72" r="1.4"/><circle cx="30" cy="77" r="1.4"/><circle cx="56" cy="77" r="1.4"/></g>`;
    case'logo':return `<path d="M50 70c-3-3-6 0-3 3l3 3 3-3c3-3 0-6-3-3z" fill="${x}"/><path d="M33 61q7 5 14 0" fill="none" stroke="#d98d96" stroke-width="2.2"/>`;
    case'flowers':return `<g fill="${x}"><circle cx="22" cy="73" r="2.2"/><circle cx="31" cy="68" r="1.8"/><circle cx="52" cy="69" r="2.2"/><circle cx="59" cy="76" r="1.8"/><circle cx="44" cy="77" r="1.8"/></g><path d="M31 60L40 66L35 70ZM49 60L40 66L45 70Z" fill="#6aaab2"/>`;
    case'suit':return `<path d="M33 60H47L40 76Z" fill="#f7f4ec"/><path d="M33 60L40 76M47 60L40 76" stroke="#00000030" stroke-width="1.2"/>`+
      (t.bow?`<path d="M40 64l-6-3.5v7zM40 64l6-3.5v7z" fill="${x}"/><circle cx="40" cy="64" r="1.7" fill="${x}"/><circle cx="54" cy="69" r="2.6" fill="#f4a6b8"/><circle cx="54" cy="69" r="1" fill="#f3d590"/>`
        :`<path d="M39 62h2l1.2 9L40 74l-2.2-3z" fill="${x}"/>`);
  }
  return '';
}
export function accBust(a,k){
  switch(a){
    case'kinh_tron':return `<g fill="none" stroke="${k.d}" stroke-width="1.6"><circle cx="33" cy="40" r="5.8"/><circle cx="47" cy="40" r="5.8"/><path d="M38.8 40h2.4M27.2 39l-5-2M52.8 39l5-2"/></g>`;
    case'kinh_ram':return `<g fill="${k.d}"><rect x="26" y="35.5" width="12.5" height="9" rx="4"/><rect x="41.5" y="35.5" width="12.5" height="9" rx="4"/></g><path d="M38.5 39h3" stroke="${k.d}" stroke-width="1.6"/><path d="M29 38.5h4" stroke="#fff" stroke-opacity=".5" stroke-width="1.2" stroke-linecap="round"/>`;
    case'non_la':return `<path d="M5 27L40 1L75 27Q40 33 5 27Z" fill="${k.c}" stroke="${k.d}" stroke-width="1.2"/><path d="M23 14H57M14 21H66" stroke="${k.line}" stroke-width="1.1"/>`;
    case'mu_len':return `<path d="M18 31Q18 6 40 6Q62 6 62 31Z" fill="${k.c}"/><rect x="16.5" y="25" width="47" height="8.5" rx="4.2" fill="${k.d}"/><circle cx="40" cy="5" r="5" fill="${k.l}"/>`;
    case'no_toc':return `<path d="M55 19l-8-5v10zM55 19l8-5v10z" fill="${k.c}"/><circle cx="55" cy="19" r="2.4" fill="${k.d}"/>`;
    case'tui_cheo':return `<path d="M22 63L58 79" stroke="${k.d}" stroke-width="3" stroke-linecap="round"/><rect x="55" y="70" width="17" height="12" rx="3" fill="${k.c}"/><rect x="58" y="72" width="11" height="3" rx="1.5" fill="${k.l}"/>`;
  }
  return '';
}
/** Warm little portrait (80×80 viewBox), drawn inline. `look` null: the gender's default look. */
export function portrait(look,gender,size=56,label){
  const Lk=look||defaultLook(gender),hair=hairColour(Lk),sk=art(Lk,'skin'),top=art(Lk,'top'),ak=accPaint(Lk);
  const f=gender==='female',m=gender==='male';
  label??=f?'Nhân vật nữ':m?'Nhân vật nam':'Nhân vật của bạn';
  const eyes=Lk.acc==='kinh_ram'?'':`<ellipse cx="33" cy="40" rx="2.8" ry="3.4" fill="#4b3936"/><ellipse cx="47" cy="40" rx="2.8" ry="3.4" fill="#4b3936"/><circle cx="32.3" cy="38.8" r="1" fill="#fff"/><circle cx="46.3" cy="38.8" r="1" fill="#fff"/>`;
  return `<svg class="jr-av" width="${size}" height="${size}" viewBox="0 0 80 80" role="img" aria-label="${label}"><rect width="80" height="80" rx="26" fill="#f4e4cf"/>`+
    hairBack(Lk.hair,hair)+`<path d="M12 80c2-23 54-23 56 0" fill="${topColour(Lk,gender)}"/>`+topDetail(top)+(Lk.acc==='tui_cheo'?accBust('tui_cheo',ak):'')+
    `<rect x="34" y="50" width="12" height="12" rx="5" fill="${sk.neck}"/><ellipse cx="40" cy="38" rx="19" ry="21" fill="${sk.c}"/>${hairFront(Lk.hair,hair)}`+eyes+
    `<ellipse cx="28" cy="46" rx="3.6" ry="2.2" fill="#e08f86" opacity=".55"/><ellipse cx="52" cy="46" rx="3.6" ry="2.2" fill="#e08f86" opacity=".55"/><path d="M36 48q4 4 8 0" fill="none" stroke="#a46e5e" stroke-width="1.8" stroke-linecap="round"/>`+
    (Lk.acc==='tui_cheo'?'':accBust(Lk.acc,ak))+`</svg>`;
}
/** The player's own portrait from the state (board, ranking, marriage, stories…). */
export const myPortrait=(state,size=40,label='Bạn')=>portrait(lookOf(state),state?.journey?.gender,size,label);

/* ---- the full character (origin at the feet, up is negative) ----
 * The same painters draw the walking character on the scene canvas (BobaWorld.character, pen CANVAS)
 * and the wardrobe mirror as inline SVG (pen SVG, v4/wardrobe.js), so both always match. */
export const CANVAS={R,E,L,P,heart,bloom,
  ring:(c,x,y,r,col,w)=>{c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.strokeStyle=col;c.lineWidth=w;c.stroke();},
  path:(c,d,fill)=>{c.fillStyle=fill;c.fill(new Path2D(d));},
  stroke:(c,d,col,w)=>{c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.stroke(new Path2D(d));}};
const n1=v=>Math.round(v*10)/10;
/** SVG pen: `c` is an array of markup strings. */
export const SVG={
  R:(c,x,y,w,h,fill,r=12,stroke=null,lw=2)=>c.push(`<rect x="${n1(x)}" y="${n1(y)}" width="${n1(w)}" height="${n1(h)}" rx="${n1(Math.min(r,w/2,h/2))}" fill="${fill}"${stroke?` stroke="${stroke}" stroke-width="${lw}"`:''}/>`),
  E:(c,x,y,rx,ry,fill)=>c.push(`<ellipse cx="${n1(x)}" cy="${n1(y)}" rx="${n1(rx)}" ry="${n1(ry)}" fill="${fill}"/>`),
  L:(c,x,y,x2,y2,col,w=2)=>c.push(`<line x1="${n1(x)}" y1="${n1(y)}" x2="${n1(x2)}" y2="${n1(y2)}" stroke="${col}" stroke-width="${w}" stroke-linecap="round"/>`),
  P:(c,pts,fill)=>c.push(`<polygon points="${pts.map(([x,y])=>n1(x)+','+n1(y)).join(' ')}" fill="${fill}"/>`),
  heart:(c,x,y,s=1,col='#cf839c')=>c.push(`<path transform="translate(${n1(x)} ${n1(y)}) scale(${s})" d="M0 6C-25-9-15-27 0-13C15-27 25-9 0 6Z" fill="${col}"/>`),
  bloom:(c,x,y,size=12,col='#efb5ca')=>{for(let i=0;i<5;i++){const a=i*Math.PI*2/5;SVG.E(c,x+Math.cos(a)*size*.6,y+Math.sin(a)*size*.6,size*.5,size*.5,col);}SVG.E(c,x,y,size*.33,size*.33,'#f3d590');},
  ring:(c,x,y,r,col,w)=>c.push(`<circle cx="${n1(x)}" cy="${n1(y)}" r="${r}" fill="none" stroke="${col}" stroke-width="${w}"/>`),
  path:(c,d,fill)=>c.push(`<path d="${d}" fill="${fill}"/>`),
  stroke:(c,d,col,w)=>c.push(`<path d="${d}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round"/>`),
};
const FRONT={short:'M-31 -80C-35 -118 24 -124 32 -84Q26 -95 12 -99Q-4 -92 -18 -97Q-26 -92 -31 -80Z',
  soft:'M-30 -88C-33 -119 19 -120 31 -90Q19 -93 7 -105Q5 -88 -12 -84Q-17 -91 -16 -101Q-21 -89 -30 -88Z'};
/** Resolved colours and shapes of the player's look (from the state, or a look + gender). */
export const figure=state=>figureOf(lookOf(state),state?.journey?.gender);
export function figureOf(Lk,g){
  const top=art(Lk,'top');
  // The default shade keeps the two browns the scene always used.
  const hair=Lk.shade==='mau_nau'?(Lk.hair==='toc_ngan'&&g==='male'?'#4f3a30':'#74503f'):hairColour(Lk);
  return {g,L:Lk,hair,skin:art(Lk,'skin'),top,topC:top.c,classic:topColour(Lk,g),bottom:art(Lk,'bottom'),shoes:art(Lk,'shoes'),long:!!art(Lk,'hair').long,short:Lk.hair==='toc_ngan'};
}
/** Legs, shoes and skirts (before the torso). */
export function paintLegs(c,F,step,K=CANVAS){
  const b=F.bottom,sk=F.skin.hand,bare=b.short||b.skirt,s=F.shoes;
  K.R(c,-19,-20,15,20,bare?sk:b.c,5);K.R(c,4,-20,15,20,bare?sk:b.c,5);
  if(b.short){K.R(c,-20,-21,17,10,b.c,4);K.R(c,3,-21,17,10,b.c,4);}
  if(s.tall){K.R(c,-20,-13+step,17,16,s.c,5);K.R(c,3,-13-step,17,16,s.c,5);}
  K.R(c,-21,(s.flat?-4:-7)+step,19,s.flat?7:10,s.c,5,s.line||null,1.2);K.R(c,3,(s.flat?-4:-7)-step,19,s.flat?7:10,s.c,5,s.line||null,1.2);
  if(b.skirt==='flare')K.P(c,[[-21,-24],[21,-24],[28,-9],[-28,-9]],b.c);
  if(b.skirt==='long'){K.P(c,[[-21,-24],[21,-24],[25,-5],[-25,-5]],b.c);for(const [x,y] of [[-14,-14],[0,-10],[13,-16],[-6,-19],[8,-7]])K.E(c,x,y,1.8,1.8,'#fff8ee');}
  if(F.top.long)K.P(c,[[-17,-22],[17,-22],[13,-5],[-13,-5]],F.topC);   // áo dài flaps
}
/** Hair behind the body and head (long hair, tail, curls). */
export function paintHairBack(c,F,K=CANVAS){
  const h=F.L.hair,col=F.hair;
  if(F.long)K.R(c,-28,-92,56,64,col,22);
  else if(h==='toc_bob')K.R(c,-31,-99,62,46,col,20);
  else if(h==='toc_duoi_ngua'){K.E(c,31,-90,10,22,col);K.E(c,34,-70,7,10,col);}
  else if(h==='toc_xoan')for(const [x,y,r] of [[-29,-94,13],[29,-94,13],[-21,-112,14],[20,-113,14],[0,-120,14],[-33,-76,9],[33,-76,9]])K.E(c,x,y,r,r,col);
}
/** What the character wears on the torso when the work layer is off. */
export function paintTop(c,F,K=CANVAS){
  const t=F.top,x=t.x;
  switch(t.d){
    case'tee':K.L(c,-8,-51,8,-51,x,3);break;
    case'collar':K.P(c,[[-10,-52],[0,-44],[10,-52]],x);K.E(c,0,-38,1.5,1.5,'#bdb5a3');K.E(c,0,-29,1.5,1.5,'#bdb5a3');break;
    case'knit':K.L(c,-21,-38,21,-38,x,3);K.L(c,-21,-27,21,-27,x,3);break;
    case'hood':K.E(c,0,-52,16,6,x);K.L(c,-4,-48,-5,-36,'#f3ecff',1.5);K.L(c,4,-48,5,-36,'#f3ecff',1.5);break;
    case'aodai':K.R(c,-7,-56,14,6,x,3);K.L(c,0,-50,14,-40,x,1.8);K.E(c,-12,-30,1.8,1.8,x);K.E(c,10,-26,1.8,1.8,x);break;
    case'logo':K.heart(c,9,-32,.26,x);break;
    case'flowers':for(const [px,py] of [[-13,-42],[10,-45],[-6,-28],[13,-27],[1,-36]])K.bloom(c,px,py,4,x);break;
    case'suit':K.P(c,[[-8,-52],[8,-52],[0,-32]],'#f7f4ec');if(t.bow){K.P(c,[[0,-47],[-7,-51],[-7,-43]],x);K.P(c,[[0,-47],[7,-51],[7,-43]],x);K.E(c,13,-40,3,3,'#f4a6b8');}else K.P(c,[[-2,-49],[2,-49],[3,-37],[0,-33],[-3,-37]],x);break;
  }
}
/** Bun, flower and ties (after the front hair). */
export function paintHairFront(c,F,K=CANVAS){
  const h=F.L.hair;
  if(h==='toc_bui'){K.E(c,-18,-113,17,15,F.hair);K.L(c,-25,-112,-12,-120,'#9f7660',2);K.bloom(c,20,-99,8,'#ffe5b0');}
  else if(h==='toc_duoi_ngua')K.E(c,27,-104,4.5,4.5,'#e0708a');
}
/** The one accessory (last, over the face and hair). */
export function paintAcc(c,F,K=CANVAS){
  const k=accPaint(F.L);
  switch(F.L.acc){
    case'kinh_tron':K.ring(c,-11,-78,8.5,k.d,1.8);K.ring(c,11,-78,8.5,k.d,1.8);K.L(c,-2.5,-78,2.5,-78,k.d,1.6);break;
    case'kinh_ram':K.R(c,-21,-85,19,13,k.d,6);K.R(c,2,-85,19,13,k.d,6);K.L(c,-2,-80,2,-80,k.d,2);K.L(c,-17,-81,-11,-81,'#ffffff70',1.5);break;
    case'non_la':K.P(c,[[-46,-103],[0,-140],[46,-103]],k.c);K.E(c,0,-103,46,5,k.brim);K.L(c,-24,-122,24,-122,k.line,1.3);break;
    case'mu_len':K.R(c,-31,-128,62,34,k.c,16);K.R(c,-33,-104,66,11,k.d,5);K.E(c,0,-129,7,7,k.l);break;
    case'no_toc':K.P(c,[[22,-108],[11,-115],[11,-101]],k.c);K.P(c,[[22,-108],[33,-115],[33,-101]],k.c);K.E(c,22,-108,3,3,k.d);break;
    case'tui_cheo':K.L(c,-18,-50,15,-25,k.d,3);K.R(c,9,-31,17,13,k.c,4);K.R(c,12,-29,11,3,k.l,1.5);break;
  }
}
/** The whole player as BobaWorld draws it, with the work layer off (the wardrobe mirror). `arms` (optional, the fair's
 * photobooth poses): {l, r} hand points [x, y]; a side given gets a sleeve from the shoulder to that hand instead of the
 * hand resting at the side (drawn last, over the face and hair). */
export function paintPlayer(c,F,K=SVG,arms=null){
  const sk=F.skin,male=F.g==='male';
  K.E(c,0,0,26,8,'#81644823');
  paintLegs(c,F,0,K);paintHairBack(c,F,K);
  K.R(c,-23,-52,46,36,F.topC||F.classic,15);if(!arms?.l)K.E(c,-25,-36,8,14,sk.hand);if(!arms?.r)K.E(c,25,-36,8,14,sk.hand);
  paintTop(c,F,K);
  K.E(c,0,-84,33,35,F.hair);K.E(c,-29,-71,5,8,sk.ear);K.E(c,29,-71,5,8,sk.ear);K.E(c,0,-77,29,28,sk.face);
  K.path(c,F.short?FRONT.short:FRONT.soft,F.hair);
  K.E(c,-20,-67,7,4,male?'#efb3a466':'#efa7a0');K.E(c,20,-67,7,4,male?'#efb3a466':'#efa7a0');
  for(const ex of [-11,11]){K.E(c,ex,-78,5,7,'#705140');K.E(c,ex-1.3,-80.4,1.8,2.3,'#fffdf3');K.E(c,ex+1,-75,1,1,'#d7b895');}
  if(male){K.L(c,-16,-89,-6,-90,F.hair,2.4);K.L(c,6,-90,16,-89,F.hair,2.4);}
  K.stroke(c,'M4 -66A4 4 0 0 1 -4 -66','#b17c69',1.6);
  paintHairFront(c,F,K);paintAcc(c,F,K);
  if(arms)for(const [s,p] of [[-1,arms.l],[1,arms.r]])if(p){K.L(c,s*20,-44,p[0],p[1],F.topC||F.classic,11);K.E(c,p[0],p[1],7,7.5,sk.hand);}
}
/** Full-body SVG of a look (the wardrobe mirror and the item tiles). */
export function figureSVG(Lk,gender,{w=120,h=170,label='',box='-50 -146 100 154'}={}){
  const out=[];paintPlayer(out,figureOf(Lk,gender),SVG);
  return `<svg class="wd-fig" width="${w}" height="${h}" viewBox="${box}" ${label?`role="img" aria-label="${label}"`:'aria-hidden="true"'} focusable="false">${out.join('')}</svg>`;
}
