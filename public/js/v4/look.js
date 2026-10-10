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
import {paintRank} from './insignia.js';
// 👶 F.bb: the baby in the character's arms (v4/baby.js)
import {paintCarried} from './baby-art.js';

export const SLOTS=['hair','shade','skin','top','bottom','shoes','acc'];
// Same as game/wardrobe.py DEFAULTS (tests/test_wardrobe.py compares them).
const DEFAULTS={"male":{"hair":"toc_ngan","shade":"mau_nau","skin":"da_sang","top":"ao_quen","bottom":"quan_xam","shoes":"giay_nau","acc":"pk_khong","uniform":true},"female":{"hair":"toc_bui","shade":"mau_nau","skin":"da_sang","top":"ao_quen","bottom":"quan_kem","shoes":"giay_nau","acc":"pk_khong","uniform":true},"none":{"hair":"toc_ngan","shade":"mau_nau","skin":"da_sang","top":"ao_quen","bottom":"quan_kem","shoes":"giay_nau","acc":"pk_khong","uniform":true}};

/* ---- art per item id ---- */
export const ART={
  hair:{toc_ngan:{},toc_bui:{long:1},toc_dai:{long:1},toc_bob:{},toc_duoi_ngua:{},toc_xoan:{},toc_bui_cao:{},toc_bui_doi:{},toc_bui_thap:{},
    // 1.9.2 (góp ý #200): worn from state.wardrobe_plus (lookOf)
    toc_song_dai:{long:1},toc_bob_mai:{},toc_duoi_cao:{},toc_bui_tron:{},toc_wolf:{},toc_undercut:{},toc_mai_bay:{},toc_tet:{}},
  shade:{mau_nau:{c:'#5b4436'},mau_den:{c:'#2f2826'},mau_mat_ong:{c:'#9a6a3f'},mau_hong:{c:'#d98fa3'},mau_xanh_khoi:{c:'#6f8ea8'},mau_bach_kim:{c:'#e3d5b8'}},
  skin:{da_sang:{c:'#f5cfae',neck:'#e6b692',face:'#f8dcc2',ear:'#f3ceb1',hand:'#f5d5ba'},da_hong:{c:'#f8d8c6',neck:'#eab9a3',face:'#fbe2d4',ear:'#f2c9b6',hand:'#f7dccb'},
    da_trung:{c:'#e3b389',neck:'#c9966d',face:'#ebbf98',ear:'#dcaa80',hand:'#e6b890'},da_ngam:{c:'#c48d64',neck:'#a8744e',face:'#cc976e',ear:'#b9825b',hand:'#c79168'}},
  // tx: which shade of a chosen colour (look.tint) the detail takes, 'd' darker or 'l' lighter (none: it keeps its own).
  top:{ao_quen:{c:null},ao_thun_kem:{c:'#efdfc4',d:'tee',x:'#dcc7a6',tx:'d'},ao_thun_xanh:{c:'#9cc39a',d:'tee',x:'#84ab82',tx:'d'},ao_so_mi:{c:'#f7f4ec',d:'collar',x:'#ddd6c6',tx:'d'},
    ao_len:{c:'#c9806a',d:'knit',x:'#e8b49f',tx:'l'},ao_hoodie:{c:'#9d8cc4',d:'hood',x:'#8676b0',tx:'d'},ao_dai:{c:'#5d9ea0',d:'aodai',x:'#f2d38a',long:1},
    ao_chi_may:{c:'#e7a0a8',d:'logo',x:'#fff5ee'},ao_hoa:{c:'#7cc0c8',d:'flowers',x:'#fff3d6'},ao_vest:{c:'#56627a',d:'suit',x:'#9b5b6b'},
    ao_cuoi:{c:'#c8453c',d:'aodai',x:'#f2c86a',long:1},vest_cuoi:{c:'#3e4a5c',d:'suit',x:'#c8453c',bow:1},
    dam_cong_chua:{c:'#c3a4df',d:'princess',dress:'princess',x:'#eee0fa',tx:'l'},
    dam_du_tiec:{c:'#395c81',d:'gala',dress:'gala',x:'#d9bd77'},
    dam_yem:{c:'#c68468',d:'pinafore',dress:'pinafore',x:'#8f533e',tx:'d'},
    dam_maxi:{c:'#e7a72a',d:'gala',dress:'gala',x:'#fff3d6'},vay_babydoll:{c:'#f2c1cf',d:'princess',dress:'princess',x:'#fff5f8',tx:'d'},
    ao_blazer:{c:'#2f3340',d:'suit',x:'#c9b48a'},ao_cardigan:{c:'#efe1c3',d:'knit',x:'#cdb98f',tx:'d'},ao_polo:{c:'#2f4f7a',d:'collar',x:'#e9e4d8',tx:'l'},
    ao_croptop:{c:'#f7f4ec',d:'crop',x:'#e8b9c4',tx:'d'},ao_baby_tee:{c:'#f4b6c8',d:'babytee',x:'#ffffff',tx:'l'},
    ao_bomber:{c:'#5d6b4a',d:'bomber',x:'#d98c3a'},ao_hoodie_os:{c:'#a9a6a8',d:'hood',x:'#8f8b8e',tx:'d',os:1},
    ao_so_mi_os:{c:'#b9d3ea',d:'overshirt',x:'#f7f4ec',os:1},ao_khoac_jean:{c:'#6f8fb8',d:'denim',x:'#d9c38a',tx:'l'},
    vay_hai_day:{c:'#2e2a30',d:'slip',dress:'slip',x:'#c9b48a'},ao_dai_cach_tan:{c:'#f2a7bd',d:'aodai',x:'#fff1c9',long:1,mini:1},
    ao_ba_lo:{c:'#f2efe6',d:'tank',x:'#cfc8bb',tx:'d'},dam_suong:{c:'#7fa88f',d:'tee',dress:'shift',x:'#f3ead2',tx:'l'},
    vay_maxi_hoa:{c:'#f0b9a4',d:'gala',dress:'maxi',x:'#fff3d6'},dam_so_mi:{c:'#9ec1dc',d:'collar',dress:'shirt',x:'#f7f4ec',tx:'l'},
    vay_yem_jean:{c:'#6f8fb8',d:'pinafore',dress:'pinafore',x:'#d9c38a',tx:'l'},dam_hoa_nhi:{c:'#f6d7a7',d:'princess',dress:'princess',x:'#e58fa6',dots:1},
    dam_kim_sa:{c:'#9b7cc9',d:'gala',dress:'gala',x:'#fff6d0',sparkle:1}},
  bottom:{quan_kem:{c:'#f0d3b8'},quan_xam:{c:'#6f6a78'},quan_jean:{c:'#5b7ea6'},quan_short:{c:'#c9a978',short:1},vay_xoe:{c:'#e39ab0',skirt:'flare'},vay_dai:{c:'#9fb7d8',skirt:'long'},vay_chu_a:{c:'#2d2a2e',skirt:'flare'},
    quan_ong_rong:{c:'#e6d3b3',wide:1},quan_cargo:{c:'#6b7350',cargo:1},vay_tennis:{c:'#f7f4ec',skirt:'pleat'},quan_jogger:{c:'#34313a',cuff:1},
    quan_short_jean:{c:'#6f8fb8',short:1,stitch:1},chan_vay_jean:{c:'#6f8fb8',skirt:'flare',stitch:1},vay_xep_ly_dai:{c:'#d9a6b5',skirt:'long',pleats:1}},
  shoes:{giay_nau:{c:'#785c51'},dep_lao:{c:'#5b8fc0',flat:1},giay_trang:{c:'#f4f1ea',line:'#cfc8bb'},giay_do:{c:'#c9514a'},bot_den:{c:'#3d3533',tall:1},sandal_nau:{c:'#8a5a3b',flat:1},
    sneaker_chunky:{c:'#f4f1ea',line:'#cfc8bb',chunky:1},giay_mary_jane:{c:'#2d2a2e',strap:1},boot_co_ngan:{c:'#8a5a3b',ankle:1},dep_quai_ngang:{c:'#3d3533',flat:1,slide:1}},
  // Each accessory's own colours ("Màu gốc"): c main, d the darker part (frame, band, knot, strap), l the light part.
  acc:{pk_khong:{},kinh_tron:{c:'#6b4f3f',d:'#6b4f3f'},kinh_ram:{c:'#3a3230',d:'#3a3230'},non_la:{c:'#ecd394',d:'#c9a95e',line:'#d6b86f',brim:'#d9bb72'},
    mu_len:{c:'#d8736a',d:'#b95a52',l:'#f3e6d6'},no_toc:{c:'#e0708a',d:'#c85873'},tui_cheo:{c:'#b07a4f',d:'#8a5a3c',l:'#d9a878'},
    tui_xach:{c:'#3a3436',d:'#221e1f',l:'#d4af37'},bong_tai:{c:'#f3eee4',d:'#c8bead',l:'#ffffff'},khan_lua:{c:'#8e2437',d:'#5f1724',l:'#e7a7b2'},
    kinh_mat_meo:{c:'#2f2a2e',d:'#2f2a2e',l:'#e0b43f'},mu_bucket:{c:'#e9dcc0',d:'#b8a47a',l:'#f7efdc'},mu_luoi_trai:{c:'#3a4e7c',d:'#24345a',l:'#f8f4ec'},
    vong_co:{c:'#e0b43f',d:'#b0821f',l:'#fff6d0'},dong_ho:{c:'#c7ccd4',d:'#8b94a1',l:'#ffffff'},kep_toc:{c:'#e0708a',d:'#c85873',l:'#fde2ea'},
    kinh_can:{c:'#2f2a2e',d:'#2f2a2e',l:'#ffffff'},no_lua:{c:'#f4b0c4',d:'#d77d9a',l:'#fde2ea'},khuyen_tron:{c:'#e0b43f',d:'#b0821f',l:'#fff6d0'},
    khan_bandana:{c:'#c9514a',d:'#9e2c27',l:'#f8f4ec'},balo_mini:{c:'#e7c56a',d:'#b0821f',l:'#fff6d0'},
    mu_beret:{c:'#bd716b',d:'#8d4d4e',l:'#f0b5a3',anchor:'head',back:1},mu_cao_boi:{c:'#c39761',d:'#785439',l:'#ead2a0',anchor:'head',back:1},
    tai_nghe:{c:'#60799f',d:'#36455f',l:'#c1d8ee',anchor:'head',back:1},vuong_mien:{c:'#dab04d',d:'#94702d',l:'#fff0ba',anchor:'head',back:1},
    bang_do_tai_meo:{c:'#9c879e',d:'#665468',l:'#e3b9cd',anchor:'head',back:1},vong_hoa:{c:'#e69eb4',d:'#71855c',l:'#fff3ce',anchor:'head',back:1},
    khau_trang:{c:'#a4cbbd',d:'#648d7d',l:'#e3f3ec',anchor:'head',back:1},khan_choang:{c:'#c58363',d:'#895638',l:'#efd2ab',anchor:'body',back:1}},
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
  const plus=state?.wardrobe_plus?.wear;   // 1.9.2 pieces keep their colours in their own block
  const c=plus&&Object.hasOwn(plus,id)?plus[id]:(ART.acc[id]?state?.wardrobe_colors?.wear:state?.colors?.wear)?.[id];
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
  // 1.9.2 pieces (game/wardrobe.py PLUS_KEY): {slot: [piece, the id state.wardrobe wore there]}; a stale entry is ignored.
  const plus=state?.wardrobe_plus?.look;
  if(plus&&typeof plus==='object')for(const k of SLOTS){const e=plus[k];
    if(Array.isArray(e)&&typeof e[0]==='string'&&Object.hasOwn(ART[k],e[0])&&e[1]===d[k])d[k]=e[0];}
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
    case'toc_bui_cao':return `<ellipse cx="40" cy="10" rx="9" ry="8" fill="${c}"/><path d="M33 15H47" stroke="#e0b43f" stroke-width="2"/>`;
    case'toc_bui_doi':return `<g fill="${c}"><circle cx="18" cy="20" r="9"/><circle cx="62" cy="20" r="9"/></g><path d="M14 27l7 1M59 28l7-1" stroke="#e0708a" stroke-width="2"/>`;
    case'toc_bui_thap':return `<ellipse cx="60" cy="48" rx="9" ry="8" fill="${c}"/><path d="M57 44l5 7" stroke="#dfc795" stroke-width="2"/>`;
    case'toc_bui':return `<circle cx="40" cy="12" r="9" fill="${c}"/><path d="M18 44C12 10 68 10 62 44L64 68H16Z" fill="${c}"/>`;
    case'toc_dai':return `<path d="M18 44C12 10 68 10 62 44L65 72H15Z" fill="${c}"/>`;
    case'toc_bob':return `<path d="M17 50C11 10 69 10 63 50Q52 56 40 54Q28 56 17 50Z" fill="${c}"/>`;
    case'toc_duoi_ngua':return `<path d="M52 18Q74 20 70 46Q67 60 59 54Q66 40 54 28Z" fill="${c}"/>`;
    case'toc_xoan':return `<g fill="${c}"><circle cx="23" cy="27" r="10"/><circle cx="31" cy="16" r="11"/><circle cx="48" cy="15" r="11"/><circle cx="57" cy="26" r="10"/><circle cx="61" cy="39" r="8"/><circle cx="19" cy="39" r="8"/></g>`;
    case'toc_song_dai':return `<path d="M18 44C12 10 68 10 62 44Q68 52 63 60Q68 68 62 76H18Q12 68 17 60Q12 52 18 44Z" fill="${c}"/>`;
    case'toc_bob_mai':return `<path d="M17 50C11 10 69 10 63 50Q52 56 40 54Q28 56 17 50Z" fill="${c}"/>`;
    case'toc_mai_bay':return `<path d="M18 48C12 10 68 10 62 48Q58 58 52 56H28Q22 58 18 48Z" fill="${c}"/>`;
    case'toc_duoi_cao':return `<path d="M50 12Q72 6 70 34Q68 52 60 50Q66 34 54 20Z" fill="${c}"/>`;
    case'toc_bui_tron':return `<g fill="${c}"><circle cx="25" cy="13" r="9"/><circle cx="55" cy="13" r="9"/></g>`;
    case'toc_wolf':return `<path d="M19 40Q14 52 20 58L24 50L27 58L30 48M61 40Q66 52 60 58L56 50L53 58L50 48" fill="${c}"/>`;
    case'toc_tet':return `<g fill="${c}"><circle cx="58" cy="52" r="5"/><circle cx="60" cy="60" r="4.8"/><circle cx="61" cy="68" r="4.5"/><circle cx="62" cy="75" r="4.2"/></g><circle cx="62" cy="79" r="2" fill="#e0708a"/>`;
  }
  return '';
}
function hairFront(h,c){
  switch(h){
    case'toc_bui_cao':return `<path d="M21 35Q20 14 40 14Q60 14 59 35Q51 25 40 23Q29 25 21 35Z" fill="${c}"/>`;
    case'toc_bui_doi':return `<path d="M21 36Q20 14 40 14Q60 14 59 36Q48 31 40 22Q32 31 21 36Z" fill="${c}"/>`;
    case'toc_bui_thap':return `<path d="M21 37Q18 14 40 14Q62 15 59 36L51 25Q34 32 21 37Z" fill="${c}"/>`;
    case'toc_ngan':return `<path d="M20 37Q18 13 40 12Q62 13 60 37Q56 25 45 22Q35 30 20 37Z" fill="${c}"/>`;
    case'toc_bob':return `<path d="M21 35Q20 14 40 14Q60 14 59 35Q51 28 40 29Q29 28 21 35Z" fill="${c}"/>`;
    case'toc_xoan':return `<path d="M21 34Q22 17 40 16Q58 17 59 34Q54 26 47 27Q42 22 36 27Q28 25 21 34Z" fill="${c}"/>`;
    case'toc_duoi_ngua':return `<path d="M21 38Q21 15 40 15Q59 15 59 38Q52 25 41 22Q31 26 21 38Z" fill="${c}"/><circle cx="56" cy="22" r="3" fill="#e0708a"/>`;
    case'toc_bob_mai':return `<path d="M21 36Q20 14 40 14Q60 14 59 36L58 33H22Z" fill="${c}"/><path d="M22 33H58" stroke="${c}" stroke-width="1"/>`;
    case'toc_mai_bay':return `<path d="M21 38Q20 14 40 14Q60 14 59 38Q55 27 46 25Q42 28 40 24Q38 28 34 25Q25 27 21 38Z" fill="${c}"/>`;
    case'toc_duoi_cao':return `<path d="M21 37Q21 15 40 15Q59 15 59 37Q52 25 41 22Q31 26 21 37Z" fill="${c}"/><circle cx="50" cy="13" r="3" fill="#e0708a"/>`;
    case'toc_bui_tron':return `<path d="M21 36Q20 15 40 15Q60 15 59 36Q49 30 40 22Q31 30 21 36Z" fill="${c}"/>`;
    case'toc_wolf':return `<path d="M20 38Q16 12 40 12Q64 12 60 38L56 28L52 33L49 24Q40 30 31 24L28 33L24 28Z" fill="${c}"/>`;
    case'toc_undercut':return `<path d="M22 32Q24 12 42 12Q60 13 58 30Q50 22 40 22Q30 22 22 32Z" fill="${c}"/><path d="M20 36V44M60 36V44" stroke="${c}" stroke-opacity=".45" stroke-width="3"/>`;
    case'toc_tet':return `<path d="M21 37Q21 15 40 15Q59 15 59 37Q50 26 40 24Q30 26 21 37Z" fill="${c}"/>`;
  }
  return `<path d="M21 38Q21 15 40 15Q59 15 59 38Q52 25 41 22Q31 26 21 38Z" fill="${c}"/>`;
}
export function topDetail(t,sk){
  const x=t.x;
  switch(t.d){
    case'crop':return `<path d="M33 61q7 5 14 0" fill="none" stroke="${x}" stroke-width="2.4"/><path d="M14 77H66" stroke="${x}" stroke-width="2"/>`;
    case'babytee':return `<path d="M33 61q7 5 14 0" fill="none" stroke="${x}" stroke-width="2.6"/><path d="M40 69l1.6 3.2 3.5.5-2.5 2.4.6 3.5-3.2-1.7-3.2 1.7.6-3.5-2.5-2.4 3.5-.5z" fill="${x}"/>`;
    case'bomber':return `<path d="M31 60Q40 67 49 60" fill="none" stroke="${x}" stroke-width="3.4"/><path d="M40 65V80" stroke="#e8e2d4" stroke-width="1.4"/><circle cx="54" cy="70" r="1.6" fill="${x}"/>`;
    case'overshirt':return `<path d="M33 60H47L45 80H35Z" fill="${x}"/><path d="M31 60L37 68L34 71ZM49 60L43 68L46 71Z" fill="#00000022"/>`;
    case'denim':return `<path d="M31 60L40 66L35 71ZM49 60L40 66L45 71Z" fill="${x}"/><path d="M24 70h9v6h-9zM47 70h9v6h-9z" fill="none" stroke="${x}" stroke-width="1.2"/><g fill="#d9d4c8"><circle cx="40" cy="72" r="1"/><circle cx="40" cy="77" r="1"/></g>`;
    case'tank':return `<path d="M12 80c2-15 54-15 56 0Z" fill="${sk||'#f5cfae'}"/><path d="M24 66Q40 72 56 66L58 80H22Z" fill="${t.c}"/><path d="M26 66V60h7v6M47 66V60h7v6" fill="${t.c}"/><path d="M33 67q7 4 14 0" fill="none" stroke="${x}" stroke-width="1.6"/>`;
    case'slip':return `<path d="M12 80c2-15 54-15 56 0Z" fill="${sk||'#f5cfae'}"/><path d="M27 66Q40 74 53 66L56 80H24Z" fill="${t.c}"/><path d="M29 66V59M51 66V59" stroke="${x}" stroke-width="1.4"/>`;
    case'princess':return `<path d="M28 64Q40 72 52 64M18 76Q40 82 62 76" fill="none" stroke="${x}" stroke-width="3"/><path d="M40 72l-5-3v6zM40 72l5-3v6z" fill="${x}"/>`;
    case'gala':return `<path d="M29 62Q40 74 51 62" fill="none" stroke="${x}" stroke-width="2"/><path d="M40 70l2 3-2 3-2-3z" fill="${x}"/>`;
    case'pinafore':return `<path d="M25 62h5v18h-5zM50 62h5v18h-5zM30 70h20v10H30z" fill="${x}"/><g fill="#f8edcf"><circle cx="28" cy="70" r="1.8"/><circle cx="52" cy="70" r="1.8"/></g>`;
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
  if(ART.acc[a]?.anchor){const out=[];paintAccessoryShape(out,a,k,SVG);return `<g transform="translate(40 83) scale(.55)">${out.join('')}</g>`;}
  switch(a){
    case'kinh_tron':return `<g fill="none" stroke="${k.d}" stroke-width="1.6"><circle cx="33" cy="40" r="5.8"/><circle cx="47" cy="40" r="5.8"/><path d="M38.8 40h2.4M27.2 39l-5-2M52.8 39l5-2"/></g>`;
    case'kinh_ram':return `<g fill="${k.d}"><rect x="26" y="35.5" width="12.5" height="9" rx="4"/><rect x="41.5" y="35.5" width="12.5" height="9" rx="4"/></g><path d="M38.5 39h3" stroke="${k.d}" stroke-width="1.6"/><path d="M29 38.5h4" stroke="#fff" stroke-opacity=".5" stroke-width="1.2" stroke-linecap="round"/>`;
    case'non_la':return `<path d="M5 27L40 1L75 27Q40 33 5 27Z" fill="${k.c}" stroke="${k.d}" stroke-width="1.2"/><path d="M23 14H57M14 21H66" stroke="${k.line}" stroke-width="1.1"/>`;
    case'mu_len':return `<path d="M18 31Q18 6 40 6Q62 6 62 31Z" fill="${k.c}"/><rect x="16.5" y="25" width="47" height="8.5" rx="4.2" fill="${k.d}"/><circle cx="40" cy="5" r="5" fill="${k.l}"/>`;
    case'no_toc':return `<path d="M55 19l-8-5v10zM55 19l8-5v10z" fill="${k.c}"/><circle cx="55" cy="19" r="2.4" fill="${k.d}"/>`;
    case'tui_cheo':return `<path d="M22 63L58 79" stroke="${k.d}" stroke-width="3" stroke-linecap="round"/><rect x="55" y="70" width="17" height="12" rx="3" fill="${k.c}"/><rect x="58" y="72" width="11" height="3" rx="1.5" fill="${k.l}"/>`;
    case'tui_xach':return `<path d="M58 70q6-8 12 0" fill="none" stroke="${k.d}" stroke-width="2.2"/><rect x="55" y="69" width="18" height="12" rx="3" fill="${k.c}"/><rect x="62" y="72" width="4" height="3" rx="1" fill="${k.l}"/>`;
    case'bong_tai':return `<g fill="${k.c}" stroke="${k.d}" stroke-width=".6"><circle cx="21.5" cy="48" r="2.4"/><circle cx="58.5" cy="48" r="2.4"/></g>`;
    case'khan_lua':return `<path d="M29 57Q40 65 51 57L52 62Q40 71 28 62Z" fill="${k.c}"/><path d="M43 63l5 11-7-3z" fill="${k.d}"/><path d="M33 61q7 4 14 0" fill="none" stroke="${k.l}" stroke-width="1"/>`;
    case'kinh_mat_meo':return `<g fill="${k.d}"><path d="M25 36H38.5L38 43Q31 46 27 42Z"/><path d="M55 36H41.5L42 43Q49 46 53 42Z"/></g><path d="M38.5 38.5h3" stroke="${k.d}" stroke-width="1.6"/><g fill="${k.l}"><circle cx="25.5" cy="36.5" r="1.2"/><circle cx="54.5" cy="36.5" r="1.2"/></g>`;
    case'mu_bucket':return `<path d="M20 29Q20 9 40 9Q60 9 60 29Z" fill="${k.c}"/><path d="M12 33Q40 22 68 33L64 27H16Z" fill="${k.d}"/><path d="M21 26H59" stroke="${k.l}" stroke-width="1.4"/>`;
    case'mu_luoi_trai':return `<path d="M19 30Q19 8 40 8Q61 8 61 30Z" fill="${k.c}"/><path d="M22 29Q46 23 70 31Q62 35 44 33Z" fill="${k.d}"/><circle cx="40" cy="8.5" r="2.2" fill="${k.l}"/>`;
    case'vong_co':return `<path d="M31 58Q40 68 49 58" fill="none" stroke="${k.c}" stroke-width="1.2"/><path d="M42 66a3.2 3.2 0 1 1-2.6-4.6a2.5 2.5 0 1 0 2.6 4.6z" fill="${k.c}" stroke="${k.d}" stroke-width=".4"/>`;
    case'dong_ho':return `<rect x="62" y="72" width="9" height="5" rx="2" fill="${k.d}"/><circle cx="66.5" cy="74.5" r="2.3" fill="${k.l}" stroke="${k.c}" stroke-width=".8"/>`;
    case'kinh_can':return `<g fill="#ffffff30" stroke="${k.d}" stroke-width="1.7"><rect x="26" y="35" width="12" height="10" rx="2.5"/><rect x="42" y="35" width="12" height="10" rx="2.5"/></g><path d="M38 39h4M26 38l-4-2M54 38l4-2" stroke="${k.d}" stroke-width="1.5"/>`;
    case'no_lua':return `<path d="M40 14L26 5L25 22ZM40 14L54 5L55 22Z" fill="${k.c}"/><circle cx="40" cy="14" r="3.4" fill="${k.d}"/>`;
    case'khuyen_tron':return `<g fill="none" stroke="${k.c}" stroke-width="1.5"><circle cx="21" cy="52" r="3.6"/><circle cx="59" cy="52" r="3.6"/></g>`;
    case'khan_bandana':return `<path d="M20 26Q40 14 60 26L60 31Q40 20 20 31Z" fill="${k.c}"/><path d="M59 28l9 6-6 3z" fill="${k.d}"/><g fill="${k.l}"><circle cx="32" cy="24" r="1"/><circle cx="40" cy="22" r="1"/><circle cx="48" cy="24" r="1"/></g>`;
    case'balo_mini':return `<path d="M25 62L27 80M55 62L53 80" stroke="${k.d}" stroke-width="3" stroke-linecap="round"/><rect x="62" y="64" width="10" height="14" rx="3" fill="${k.c}"/>`;
    case'kep_toc':return `<g transform="rotate(-20 55 22)"><rect x="49" y="18" width="13" height="7" rx="3" fill="${k.c}"/><path d="M51 25v3M54.5 25v3M58 25v3" stroke="${k.d}" stroke-width="1.4"/></g>`;
  }
  return '';
}
/** v4/wardrobe.js shows the mirror's "Xoay" control once the island portrait renderer is active. */
let cozyOn=false;
export const cozyActive=()=>cozyOn;
export function cozyPortraits(on){cozyOn=Boolean(on);}
const labelHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
/** The island portrait observer reads the current wardrobe ids, including wardrobe_plus. The SVG fallback
 * and cropped wardrobe item illustrations retain all their existing details. */
function cozyMark(Lk,gender,mode,facing='se'){
  if(!cozyOn)return '';
  const g=gender==='female'||gender==='male'?gender:'none',look=defaultLook(g);
  for(const slot of SLOTS)if(typeof Lk?.[slot]==='string'&&Object.hasOwn(ART[slot],Lk[slot]))look[slot]=Lk[slot];
  if(typeof Lk?.uniform==='boolean')look.uniform=Lk.uniform;
  const dress=mode==='figure'&&ART.top[look.top]?.dress;
  if(dress)look.bottom=DEFAULTS.none.bottom;
  const tint={};
  for(const slot of TINT_SLOTS){const id=look[slot],colour=Lk?.tint?.[id];if(!(dress&&slot==='bottom')&&typeof colour==='string'&&Object.hasOwn(ACC_COLORS,colour))tint[id]=colour;}
  if(Object.keys(tint).length)look.tint=tint;
  const direction=mode==='figure'?{facing:['se','sw','nw','ne'].includes(facing)?facing:'se'}:{};
  return ` data-cozy-portrait="${encodeURIComponent(JSON.stringify({v:1,mode,gender:g,look,...direction}))}"`;
}
/** Warm little portrait (80×80 viewBox), drawn inline. `look` null: the gender's default look. */
export function portrait(look,gender,size=56,label){
  const Lk=look||defaultLook(gender),hair=hairColour(Lk),sk=art(Lk,'skin'),top=art(Lk,'top'),ak=accPaint(Lk);
  const f=gender==='female',m=gender==='male';
  label??=f?'Nhân vật nữ':m?'Nhân vật nam':'Nhân vật của bạn';
  const eyes=Lk.acc==='kinh_ram'?'':`<ellipse cx="33" cy="40" rx="2.8" ry="3.4" fill="#4b3936"/><ellipse cx="47" cy="40" rx="2.8" ry="3.4" fill="#4b3936"/><circle cx="32.3" cy="38.8" r="1" fill="#fff"/><circle cx="46.3" cy="38.8" r="1" fill="#fff"/>`;
  return `<svg class="jr-av" width="${size}" height="${size}" viewBox="0 0 80 80" role="img" aria-label="${cozyOn?labelHTML(label):label}"${cozyMark(Lk,gender,'face')}><rect width="80" height="80" rx="26" fill="#f4e4cf"/>`+
    hairBack(Lk.hair,hair)+`<path d="M12 80c2-23 54-23 56 0" fill="${topColour(Lk,gender)}"/>`+topDetail(top,sk.c)+(Lk.acc==='tui_cheo'?accBust('tui_cheo',ak):'')+
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
export const FRONT={short:'M-31 -80C-35 -118 24 -124 32 -84Q26 -95 12 -99Q-4 -92 -18 -97Q-26 -92 -31 -80Z',
  soft:'M-30 -88C-33 -119 19 -120 31 -90Q19 -93 7 -105Q5 -88 -12 -84Q-17 -91 -16 -101Q-21 -89 -30 -88Z'};
/** Resolved colours and shapes of the player's look (from the state, or a look + gender). */
export const figure=state=>{const L=lookOf(state),h=state?.journey?.gadgets?.hand?.color;if(typeof h==='string'&&/^#[0-9a-f]{6}$/i.test(h))L.held=h;const F=figureOf(L,state?.journey?.gender),rk=rankRef(state);if(rk)F.rk=rk;return F;};
/** 🎖️ The rank the character wears (game/org.py, v4/insignia.js): the current career's org grade, while "Mặc đồ làm việc"
 * is on. {o: org id, g: grade id}; never in lookOf (live frames carry it apart, as `rk`). */
export function rankRef(state){
  const o=state?.careers?.[state?.current]?.promo?.org;
  if(!o?.grade?.id||!o.org||lookOf(state).uniform===false)return null;
  return {o:o.org,g:o.grade.id};
}   // 📱 held: the phone in use (game/gadgets.py); never in lookOf (live frames refuse unknown keys)
const SHORT_HAIR=new Set(['toc_ngan','toc_wolf','toc_undercut']);
export function figureOf(Lk,g){
  const top=art(Lk,'top');
  // The default shade keeps the two browns the scene always used.
  const hair=Lk.shade==='mau_nau'?(Lk.hair==='toc_ngan'&&g==='male'?'#4f3a30':'#74503f'):hairColour(Lk);
  const bottom=top.dress?{c:top.c,skirt:top.dress==='gala'||top.dress==='slip'||top.dress==='maxi'?'long':'flare',dress:top.dress,x:top.x}:art(Lk,'bottom');
  return {g,L:Lk,hair,skin:art(Lk,'skin'),top,topC:top.c,classic:topColour(Lk,g),bottom,shoes:art(Lk,'shoes'),long:!!art(Lk,'hair').long,short:SHORT_HAIR.has(Lk.hair)};
}
/** Dress hems share the top's palette and cover the stored bottom in every pose. */
export function paintDress(c,F,K=CANVAS){
  const t=F.top,x=t.x;
  if(t.dress==='princess'){
    K.path(c,'M-18 -28H18L31 -7Q0 4 -31 -7Z',t.c);
    K.stroke(c,'M-23 -20Q0 -12 23 -20M-27 -12Q0 -3 27 -12',x,2.2);
    for(const px of [-14,0,14])K.L(c,px*.6,-25,px,-8,x,1);
  }else if(t.dress==='gala'){
    K.path(c,'M-19 -28H19L16 -14Q20 -7 29 -3Q0 5 -29 -3Q-20 -7 -16 -14Z',t.c);
    K.stroke(c,'M9 -26L11 -12L20 -4',x,1.5);
    K.E(c,-8,-20,1.3,1.3,x);K.E(c,4,-11,1,1,x);
  }else if(t.dress==='pinafore'){
    K.P(c,[[-18,-28],[18,-28],[26,-7],[-26,-7]],t.c);
    K.R(c,-8,-22,16,9,x,2);K.L(c,-20,-9,20,-9,x,1.5);
  }else if(t.dress==='slip'){
    K.P(c,[[-18,-28],[18,-28],[22,-4],[-22,-4]],t.c);
    K.L(c,8,-25,13,-7,'#ffffff40',2);
  }else if(t.dress==='shift'){
    K.P(c,[[-19,-28],[19,-28],[21,-9],[-21,-9]],t.c);
    K.R(c,8,-22,8,6,'#00000018',2);
  }else if(t.dress==='maxi'){
    K.P(c,[[-19,-28],[19,-28],[25,-3],[-25,-3]],t.c);
    for(const [px,py] of [[-14,-22],[6,-25],[14,-14],[-6,-12],[-18,-7],[10,-6]])K.bloom(c,px,py,3.2,x);
  }else if(t.dress==='shirt'){
    K.P(c,[[-18,-28],[18,-28],[26,-8],[-26,-8]],t.c);
    K.L(c,-18,-27,18,-27,x,3);K.L(c,0,-27,0,-9,'#00000022',1.2);
  }
  if(t.dots)for(const [px,py] of [[-16,-15],[-6,-21],[5,-13],[15,-19],[-10,-9],[11,-9]])K.E(c,px,py,1.6,1.6,x);
  if(t.sparkle)for(const [px,py] of [[-12,-22],[6,-17],[14,-8],[-7,-9],[0,-25],[-17,-6]])K.E(c,px,py,1.1,1.1,x);
}
/** Legs, shoes and skirts (before the torso). */
export function paintLegs(c,F,step,K=CANVAS){
  const b=F.bottom,sk=F.skin.hand,bare=b.short||b.skirt,s=F.shoes;
  K.R(c,-19,-20,15,20,bare?sk:b.c,5);K.R(c,4,-20,15,20,bare?sk:b.c,5);
  if(b.short){K.R(c,-20,-21,17,10,b.c,4);K.R(c,3,-21,17,10,b.c,4);}
  if(b.cargo){K.R(c,-21,-14,6,7,'#00000026',2);K.R(c,15,-14,6,7,'#00000026',2);}
  if(b.cuff){K.R(c,-19,-7,15,4,'#00000033',2);K.R(c,4,-7,15,4,'#00000033',2);}
  if((s.strap||s.slide)&&bare){K.R(c,-19,-10,15,5,'#fbf7ee',2);K.R(c,4,-10,15,5,'#fbf7ee',2);}
  if(s.tall){K.R(c,-20,-13+step,17,16,s.c,5);K.R(c,3,-13-step,17,16,s.c,5);}
  if(s.ankle){K.R(c,-20,-10+step,17,12,s.c,5);K.R(c,3,-10-step,17,12,s.c,5);}
  if(s.chunky){K.R(c,-22,-1+step,21,5,'#e3dccd',3);K.R(c,2,-1-step,21,5,'#e3dccd',3);}
  K.R(c,-21,(s.flat?-4:-7)+step,19,s.flat?7:10,s.c,5,s.line||null,1.2);K.R(c,3,(s.flat?-4:-7)-step,19,s.flat?7:10,s.c,5,s.line||null,1.2);
  if(s.strap){K.L(c,-19,-5+step,-5,-5+step,'#fbf7ee',1.4);K.L(c,5,-5-step,19,-5-step,'#fbf7ee',1.4);}
  if(s.slide){K.R(c,-21,-4+step,19,3,'#ffffff55',1.5);K.R(c,3,-4-step,19,3,'#ffffff55',1.5);}
  if(b.wide){K.P(c,[[-19,-20],[-3,-20],[-1,-2],[-23,-2]],b.c);K.P(c,[[3,-20],[19,-20],[23,-2],[1,-2]],b.c);}
  if(b.dress)paintDress(c,F,K);
  else if(b.skirt==='flare')K.P(c,[[-21,-24],[21,-24],[28,-9],[-28,-9]],b.c);
  else if(b.skirt==='pleat'){K.P(c,[[-21,-24],[21,-24],[28,-7],[-28,-7]],b.c);for(const x of [-16,-8,0,8,16])K.L(c,x*.85,-23,x*1.1,-8,'#00000026',1);}
  if(b.pleats)for(const x of [-15,-7,1,9,17])K.L(c,x*.85,-22,x*1.15,-6,'#00000022',1);
  if(b.stitch){K.L(c,-20,-22,20,-22,'#f1d78f',1);if(b.skirt)K.L(c,-25,-12,25,-12,'#f1d78f',1);else{K.L(c,-19,-12,-3,-12,'#f1d78f',1);K.L(c,4,-12,20,-12,'#f1d78f',1);}}
  else if(b.skirt==='long'){K.P(c,[[-21,-24],[21,-24],[25,-5],[-25,-5]],b.c);for(const [x,y] of [[-14,-14],[0,-10],[13,-16],[-6,-19],[8,-7]])K.E(c,x,y,1.8,1.8,'#fff8ee');}
  if(F.top.long)K.P(c,[[-17,-22],[17,-22],[13,F.top.mini?-11:-5],[-13,F.top.mini?-11:-5]],F.topC);   // áo dài flaps (cách tân: shorter)
}
/** Hair behind the body and head (long hair, tail, curls). */
export function paintHairBack(c,F,K=CANVAS){
  const h=F.L.hair,col=F.hair;
  if(F.long)K.R(c,-28,-92,56,64,col,22);
  else if(h==='toc_bob')K.R(c,-31,-99,62,46,col,20);
  else if(h==='toc_duoi_ngua'){K.E(c,31,-90,10,22,col);K.E(c,34,-70,7,10,col);}
  else if(h==='toc_xoan')for(const [x,y,r] of [[-29,-94,13],[29,-94,13],[-21,-112,14],[20,-113,14],[0,-120,14],[-33,-76,9],[33,-76,9]])K.E(c,x,y,r,r,col);
  else if(h==='toc_bui_thap'){K.E(c,29,-63,12,11,col);K.L(c,26,-69,33,-58,'#dfc795',2);}
  else if(h==='toc_bob_mai'||h==='toc_mai_bay')K.R(c,-31,-99,62,h==='toc_mai_bay'?52:46,col,20);
  else if(h==='toc_duoi_cao'){K.E(c,24,-116,9,9,col);K.E(c,36,-96,8,22,col);K.E(c,38,-76,6,9,col);}
  else if(h==='toc_wolf'){K.R(c,-31,-96,62,34,col,14);for(const s of [-1,1])K.P(c,[[s*31,-80],[s*37,-62],[s*24,-70]],col);}
  else if(h==='toc_tet')for(const [x,y,r] of [[26,-62,6],[28,-52,5.8],[29,-42,5.5],[29,-33,5]])K.E(c,x,y,r,r,col);
  if(h==='toc_song_dai')for(const s of [-1,1])for(const [y,r] of [[-48,8],[-38,8],[-30,7]])K.E(c,s*28,y,r,r,col);
}
/** What the character wears on the torso when the work layer is off. */
export function paintTop(c,F,K=CANVAS){
  const t=F.top,x=t.x;
  switch(t.d){
    case'princess':K.E(c,-19,-45,8,7,x);K.E(c,19,-45,8,7,x);K.stroke(c,'M-12 -49Q0 -39 12 -49',x,2.5);K.L(c,-18,-27,18,-27,x,3);K.P(c,[[0,-27],[-7,-31],[-7,-23]],x);K.P(c,[[0,-27],[7,-31],[7,-23]],x);break;
    case'gala':K.stroke(c,'M-13 -49Q0 -36 13 -49',x,1.8);K.P(c,[[0,-42],[2,-38],[0,-35],[-2,-38]],x);K.L(c,-17,-27,17,-27,x,1.5);break;
    case'pinafore':K.L(c,-12,-50,-12,-25,x,5);K.L(c,12,-50,12,-25,x,5);K.R(c,-12,-39,24,14,x,2);K.E(c,-12,-39,2,2,'#f8edcf');K.E(c,12,-39,2,2,'#f8edcf');break;
    case'tee':K.L(c,-8,-51,8,-51,x,3);break;
    case'collar':K.P(c,[[-10,-52],[0,-44],[10,-52]],x);K.E(c,0,-38,1.5,1.5,'#bdb5a3');K.E(c,0,-29,1.5,1.5,'#bdb5a3');break;
    case'knit':K.L(c,-21,-38,21,-38,x,3);K.L(c,-21,-27,21,-27,x,3);break;
    case'hood':K.E(c,0,-52,16,6,x);K.L(c,-4,-48,-5,-36,'#f3ecff',1.5);K.L(c,4,-48,5,-36,'#f3ecff',1.5);break;
    case'aodai':K.R(c,-7,-56,14,6,x,3);K.L(c,0,-50,14,-40,x,1.8);K.E(c,-12,-30,1.8,1.8,x);K.E(c,10,-26,1.8,1.8,x);break;
    case'logo':K.heart(c,9,-32,.26,x);break;
    case'flowers':for(const [px,py] of [[-13,-42],[10,-45],[-6,-28],[13,-27],[1,-36]])K.bloom(c,px,py,4,x);break;
    case'suit':K.P(c,[[-8,-52],[8,-52],[0,-32]],'#f7f4ec');if(t.bow){K.P(c,[[0,-47],[-7,-51],[-7,-43]],x);K.P(c,[[0,-47],[7,-51],[7,-43]],x);K.E(c,13,-40,3,3,'#f4a6b8');}else K.P(c,[[-2,-49],[2,-49],[3,-37],[0,-33],[-3,-37]],x);break;
    case'crop':K.R(c,-21,-27,42,10,F.skin.c,4);K.L(c,-21,-28,21,-28,x,2.5);K.L(c,-8,-51,8,-51,x,2.5);break;
    case'babytee':K.L(c,-8,-51,8,-51,x,3);K.P(c,[[0,-42],[2,-38],[6,-38],[3,-35],[4,-31],[0,-33],[-4,-31],[-3,-35],[-6,-38],[-2,-38]],x);break;
    case'bomber':K.L(c,-21,-19,21,-19,x,4);K.stroke(c,'M-10 -51Q0 -44 10 -51',x,3);K.L(c,0,-47,0,-20,'#e8e2d4',1.4);K.E(c,13,-42,2,2,x);break;
    case'overshirt':K.P(c,[[-7,-52],[7,-52],[6,-18],[-6,-18]],x);K.R(c,-24,-22,48,9,t.c,4);K.P(c,[[-10,-52],[-3,-44],[-8,-41]],'#00000022');K.P(c,[[10,-52],[3,-44],[8,-41]],'#00000022');break;
    case'denim':K.P(c,[[-10,-52],[0,-44],[-5,-40]],x);K.P(c,[[10,-52],[0,-44],[5,-40]],x);K.R(c,-17,-42,9,7,'#00000022',2);K.R(c,8,-42,9,7,'#00000022',2);K.E(c,0,-36,1.4,1.4,'#e8e2d4');K.E(c,0,-28,1.4,1.4,'#e8e2d4');break;
    case'tank':K.R(c,-23,-52,46,12,F.skin.c,12);K.R(c,-14,-52,7,10,t.c,2);K.R(c,7,-52,7,10,t.c,2);K.stroke(c,'M-8 -45Q0 -40 8 -45',x,2);break;
    case'slip':K.R(c,-23,-52,46,14,F.skin.c,12);K.L(c,-10,-51,-10,-38,x,1.5);K.L(c,10,-51,10,-38,x,1.5);K.stroke(c,'M-14 -39Q0 -33 14 -39',t.c,3);break;
  }
  if(t.os&&t.d==='hood')K.R(c,-25,-22,50,9,t.c,4);   // oversize: the hem falls over the hips
}
/** Bun, flower and ties (after the front hair). */
export function paintHairFront(c,F,K=CANVAS){
  const h=F.L.hair;
  if(h==='toc_bui'){K.E(c,-18,-113,17,15,F.hair);K.L(c,-25,-112,-12,-120,'#9f7660',2);K.bloom(c,20,-99,8,'#ffe5b0');}
  else if(h==='toc_bui_cao'){K.E(c,0,-126,14,12,F.hair);K.stroke(c,'M-8 -129Q0 -136 8 -128','#ffffff30',1.5);K.L(c,-10,-118,10,-118,'#e0b43f',3);}
  else if(h==='toc_bui_doi'){for(const x of [-30,30]){K.E(c,x,-111,13,12,F.hair);K.L(c,x-7,-101,x+7,-101,'#e0708a',3);}}
  else if(h==='toc_duoi_ngua')K.E(c,27,-104,4.5,4.5,'#e0708a');
  else if(h==='toc_duoi_cao')K.E(c,22,-117,4.5,4.5,'#e0708a');
  else if(h==='toc_bui_tron'){for(const x of [-22,22]){K.E(c,x,-118,13,12,F.hair);K.stroke(c,`M${x-6} -122Q${x} -127 ${x+6} -121`,'#ffffff30',1.4);}}
  else if(h==='toc_bob_mai')K.R(c,-25,-106,50,13,F.hair,5);
  else if(h==='toc_mai_bay'){K.stroke(c,'M0 -108Q-14 -104 -22 -86',F.hair,6);K.stroke(c,'M0 -108Q14 -104 22 -86',F.hair,6);}
  else if(h==='toc_wolf')for(const x of [-14,-2,10])K.P(c,[[x-5,-112],[x+5,-112],[x+1,-100]],F.hair);
  else if(h==='toc_undercut'){K.E(c,4,-117,22,9,F.hair);for(const s of [-1,1])K.R(c,s>0?24:-33,-96,9,16,F.skin.ear,4);}
  else if(h==='toc_tet')K.E(c,29,-29,3.4,3.4,'#e0708a');
}
/** The one accessory (last, over the face and hair). */
export function paintAcc(c,F,K=CANVAS,direction='se'){
  const k=accPaint(F.L);
  if(ART.acc[F.L.acc]?.anchor){paintAccessoryShape(c,F.L.acc,k,K,direction);return;}
  switch(F.L.acc){
    case'kinh_tron':K.ring(c,-11,-78,8.5,k.d,1.8);K.ring(c,11,-78,8.5,k.d,1.8);K.L(c,-2.5,-78,2.5,-78,k.d,1.6);break;
    case'kinh_ram':K.R(c,-21,-85,19,13,k.d,6);K.R(c,2,-85,19,13,k.d,6);K.L(c,-2,-80,2,-80,k.d,2);K.L(c,-17,-81,-11,-81,'#ffffff70',1.5);break;
    case'non_la':K.P(c,[[-46,-103],[0,-140],[46,-103]],k.c);K.E(c,0,-103,46,5,k.brim);K.L(c,-24,-122,24,-122,k.line,1.3);break;
    case'mu_len':K.R(c,-31,-128,62,34,k.c,16);K.R(c,-33,-104,66,11,k.d,5);K.E(c,0,-129,7,7,k.l);break;
    case'no_toc':K.P(c,[[22,-108],[11,-115],[11,-101]],k.c);K.P(c,[[22,-108],[33,-115],[33,-101]],k.c);K.E(c,22,-108,3,3,k.d);break;
    case'tui_cheo':K.L(c,-18,-50,15,-25,k.d,3);K.R(c,9,-31,17,13,k.c,4);K.R(c,12,-29,11,3,k.l,1.5);break;
    case'tui_xach':K.stroke(c,'M22 -32Q28 -42 34 -32',k.d,2.4);K.R(c,19,-33,18,14,k.c,4);K.R(c,26,-29,4,3,k.l,1);break;
    case'bong_tai':K.E(c,-29,-61,2.8,2.8,k.c);K.E(c,29,-61,2.8,2.8,k.c);break;
    case'khan_lua':K.P(c,[[-15,-53],[15,-53],[11,-46],[-11,-46]],k.c);K.P(c,[[4,-47],[11,-35],[1,-39]],k.d);K.L(c,-9,-50,9,-50,k.l,1);break;
    case'kinh_mat_meo':K.P(c,[[-23,-86],[-3,-84],[-4,-75],[-17,-73]],k.d);K.P(c,[[23,-86],[3,-84],[4,-75],[17,-73]],k.d);K.L(c,-3,-81,3,-81,k.d,2);K.E(c,-22,-85,1.6,1.6,k.l);K.E(c,22,-85,1.6,1.6,k.l);break;
    case'mu_bucket':K.R(c,-27,-129,54,28,k.c,13);K.P(c,[[-38,-98],[38,-98],[29,-106],[-29,-106]],k.d);K.L(c,-27,-108,27,-108,k.l,2);break;
    case'mu_luoi_trai':K.R(c,-30,-129,60,28,k.c,14);K.E(c,10,-102,28,6,k.d);K.E(c,0,-129,3,3,k.l);break;
    case'vong_co':K.stroke(c,'M-10 -52Q0 -42 10 -52',k.c,1.4);K.E(c,0,-43,3,3,k.c);K.E(c,1,-44,2,2,k.d);break;
    case'dong_ho':K.R(c,19,-42,12,5,k.d,2);K.E(c,25,-39.5,3,3,k.l);break;
    case'kinh_can':K.R(c,-20,-84,16,12,'#ffffff30',3,k.d,1.8);K.R(c,4,-84,16,12,'#ffffff30',3,k.d,1.8);K.L(c,-4,-79,4,-79,k.d,1.6);break;
    case'no_lua':K.P(c,[[0,-118],[-18,-130],[-20,-108]],k.c);K.P(c,[[0,-118],[18,-130],[20,-108]],k.c);K.L(c,-3,-117,-8,-100,k.d,3);K.L(c,3,-117,8,-100,k.d,3);K.E(c,0,-118,4.5,4.5,k.d);break;
    case'khuyen_tron':K.ring(c,-29,-58,4.2,k.c,1.6);K.ring(c,29,-58,4.2,k.c,1.6);break;
    case'khan_bandana':K.R(c,-31,-112,62,10,k.c,5);K.P(c,[[26,-108],[38,-100],[33,-96]],k.d);K.E(c,-14,-107,1.4,1.4,k.l);K.E(c,0,-108,1.4,1.4,k.l);K.E(c,14,-107,1.4,1.4,k.l);break;
    case'balo_mini':K.R(c,-33,-48,10,22,k.c,5);K.R(c,23,-48,10,22,k.c,5);K.L(c,-15,-52,-17,-30,k.d,3);K.L(c,15,-52,17,-30,k.d,3);K.E(c,-28,-36,1.6,1.6,k.l);break;
    case'kep_toc':K.R(c,17,-113,13,7,k.c,3);K.L(c,20,-106,20,-103,k.d,1.4);K.L(c,24,-106,24,-103,k.d,1.4);K.L(c,28,-106,28,-103,k.d,1.4);break;
  }
}

/** One vector silhouette shared by classic SVG, scene Canvas, chat and four-view atlas overlays. */
function paintAccessoryShape(c,id,k,K,direction='se'){
  const back=direction==='nw'||direction==='ne',side=direction==='sw'||direction==='nw'?-1:1;
  switch(id){
    case'mu_beret':
      K.E(c,side*7,-118,36,17,k.c);K.P(c,[[-29,-109],[30,-109],[25,-101],[-25,-101]],k.d);
      K.L(c,side*9,-130,side*12,-138,k.d,3);K.E(c,side*21,-122,8,3,k.l);break;
    case'mu_cao_boi':
      K.P(c,[[-46,-110],[-39,-99],[-18,-95],[19,-95],[40,-100],[46,-110],[26,-104],[-25,-104]],k.c);
      K.R(c,-25,-135,50,32,k.c,12);K.P(c,[[-25,-112],[25,-112],[25,-104],[-25,-104]],k.d);
      if(!back)K.P(c,[[0,-113],[4,-108],[0,-103],[-4,-108]],k.l);break;
    case'tai_nghe':
      K.P(c,[[-35,-82],[-34,-111],[-23,-127],[0,-132],[23,-127],[34,-111],[35,-82],[28,-82],[27,-109],[20,-121],[0,-126],[-20,-121],[-27,-109],[-28,-82]],k.d);
      for(const x of [-34,34]){K.R(c,x-7,-96,14,27,k.c,6);K.R(c,x-4,-91,8,16,k.l,3);}break;
    case'vuong_mien':
      K.P(c,[[-28,-102],[-32,-129],[-16,-116],[0,-138],[16,-116],[32,-129],[28,-102]],k.c);
      K.R(c,-29,-107,58,8,k.d,3);
      for(const x of [-18,0,18])K.P(c,[[x,-115],[x+3,-111],[x,-107],[x-3,-111]],back?k.c:k.l);break;
    case'bang_do_tai_meo':
      K.P(c,[[-31,-97],[-33,-111],[-22,-122],[0,-126],[22,-122],[33,-111],[31,-97],[26,-109],[18,-117],[0,-121],[-18,-117],[-26,-109]],k.d);
      for(const x of [-22,22]){K.P(c,[[x-12,-115],[x-9,-141],[x+12,-121]],k.c);if(!back)K.P(c,[[x-7,-119],[x-6,-133],[x+6,-122]],k.l);}break;
    case'vong_hoa':
      K.P(c,[[-31,-107],[-25,-117],[0,-123],[25,-117],[31,-107],[26,-103],[20,-111],[0,-116],[-20,-111],[-26,-103]],k.d);
      for(const [x,y] of [[-27,-110],[-14,-118],[0,-121],[14,-118],[27,-110]]){K.bloom(c,x,y,6.5,k.c);K.E(c,x,y,2,2,k.l);}break;
    case'khau_trang':
      for(const s of [-1,1]){K.L(c,s*20,-70,s*31,-77,k.c,2);K.L(c,s*20,-60,s*31,-67,k.c,2);}
      if(!back){K.P(c,[[-23,-75],[0,-78],[23,-75],[20,-57],[0,-53],[-20,-57]],k.c);K.L(c,-16,-67,16,-67,k.l,1.2);K.L(c,-14,-61,14,-61,k.d,1);}break;
    case'khan_choang':
      K.P(c,[[-20,-55],[20,-55],[22,-43],[10,-39],[-20,-44]],k.c);
      if(back){K.P(c,[[-12,-44],[3,-43],[8,-13],[-6,-11]],k.d);K.P(c,[[2,-44],[14,-44],[18,-21],[7,-18]],k.c);}
      else{K.P(c,[[side*9,-45],[side*21,-43],[side*17,-15],[side*4,-18]],k.d);K.P(c,[[side*2,-44],[side*12,-45],[side*6,-25],[-side*4,-27]],k.c);}
      K.L(c,-15,-49,15,-47,k.l,2);for(let x=-6;x<7;x+=4)K.L(c,back?x:x+side*10,back?-13:-17,back?x+1:x+side*10,back?-8:-12,k.l,1.3);break;
  }
}
/** The whole player as BobaWorld draws it, with the work layer off (the wardrobe mirror). `arms` (optional, the fair's
 * photobooth poses): {l, r} hand points [x, y]; a side given gets a sleeve from the shoulder to that hand instead of the
 * hand resting at the side (drawn last, over the face and hair). */
export function paintPlayer(c,F,K=SVG,arms=null){
  const sk=F.skin,male=F.g==='male',bb=!arms&&F.bb&&typeof F.bb==='object'?F.bb:null;   // 👶 carrying: the arms hold the baby
  K.E(c,0,0,26,8,'#81644823');
  paintLegs(c,F,0,K);paintHairBack(c,F,K);
  K.R(c,-23,-52,46,36,F.topC||F.classic,15);if(!arms?.l&&!bb)K.E(c,-25,-36,8,14,sk.hand);if(!arms?.r&&!bb)K.E(c,25,-36,8,14,sk.hand);
  paintTop(c,F,K);
  if(!bb&&!arms?.r&&/^#[0-9a-f]{6}$/i.test(F.L?.held||'')){K.R(c,19,-47,12,19,F.L.held,3,'#3b2a22',1.5);K.R(c,21.5,-44,7,12,'#bfe0f2',2);K.E(c,25,-33,6,5,sk.hand);}   // 📱 the phone in use, in the right hand
  K.E(c,0,-84,33,35,F.hair);K.E(c,-29,-71,5,8,sk.ear);K.E(c,29,-71,5,8,sk.ear);K.E(c,0,-77,29,28,sk.face);
  K.path(c,F.short?FRONT.short:FRONT.soft,F.hair);
  K.E(c,-20,-67,7,4,male?'#efb3a466':'#efa7a0');K.E(c,20,-67,7,4,male?'#efb3a466':'#efa7a0');
  for(const ex of [-11,11]){K.E(c,ex,-78,5,7,'#705140');K.E(c,ex-1.3,-80.4,1.8,2.3,'#fffdf3');K.E(c,ex+1,-75,1,1,'#d7b895');}
  if(male){K.L(c,-16,-89,-6,-90,F.hair,2.4);K.L(c,6,-90,16,-89,F.hair,2.4);}
  K.stroke(c,'M4 -66A4 4 0 0 1 -4 -66','#b17c69',1.6);
  paintHairFront(c,F,K);paintAcc(c,F,K);
  if(F.rk)paintRank(c,F,K);   // 🎖️ cấp hiệu and huy hiệu over the top
  if(bb)paintCarried(c,bb,K,F);   // 👶 in front of everything: held to the chest
  if(arms)for(const [s,p] of [[-1,arms.l],[1,arms.r]])if(p){K.L(c,s*20,-44,p[0],p[1],F.topC||F.classic,11);K.E(c,p[0],p[1],7,7.5,sk.hand);}
}
/** Full-body SVG of a look (the wardrobe mirror and the item tiles). */
export function figureSVG(Lk,gender,{w=120,h=170,label='',box='-50 -146 100 154',facing='se'}={}){
  const out=[];paintPlayer(out,figureOf(Lk,gender),SVG);
  const marker=box==='-50 -146 100 154'?cozyMark(Lk,gender,'figure',facing):'';
  return `<svg class="wd-fig" width="${w}" height="${h}" viewBox="${box}" ${label?`role="img" aria-label="${cozyOn?labelHTML(label):label}"`:'aria-hidden="true"'} focusable="false"${marker}>${out.join('')}</svg>`;
}
