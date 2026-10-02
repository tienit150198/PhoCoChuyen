/** 🙂 Ảnh đại diện, the art: a small round bust (80×80, inline SVG) from a face code (./face-code.js), with the
 * clothes the player wears in the Tủ đồ (top and accessory in their colours: ./look.js art, topDetail, accBust).
 *   faceSVG(code|parsed, size, label)  the face, or '' for a code it cannot read
 *   avInner(who)                       what a chat avatar holds for a person or a message {av, fc}: the face, else the emoji
 *   NAMES, COLORS                      the builder's names and swatches (./avatar.js)
 * Everything drawn comes from the id tables below: a code never brings markup or colours of its own. */
import {escapeHTML as esc} from '../icons.js';
import {ART,ACC_COLORS,accPaint,art,topDetail,accBust,topColour} from './look.js';
import {parseFace,DEFAULT_FACE} from './face-code.js';

const SKIN={s1:['#fde4d0','#efc7aa'],s2:['#f6d3b3','#e6b692'],s3:['#efc29c','#dca67d'],s4:['#e3b087','#c9966d'],
  s5:['#cd9467','#b47b50'],s6:['#b07650','#94603d'],s7:['#8b5a3c','#734730'],s8:['#62402c','#4f3222']};
const HC={den:'#2a2423',nau:'#5b4436',mat_ong:'#9a6a3f',vang:'#e0bd67',do:'#a5452e',hong:'#d98fa3',xanh:'#6f8ea8',tim:'#8a6bb8',
  bach_kim:'#e8dcc2',xam:'#a9a6a1',trang:'#efece7'};
const BG={kem:'#f4e4cf',hong:'#f8d7df',dao:'#fbd9c4',vang:'#f7e7a8',mint:'#cdeee2',xanh:'#cfe3f5',lavender:'#e2d9f5',xam:'#e3e1dd',
  navy:'#3d4f78',la:'#d3e8c0'};
const LIGHT_HAIR=new Set(['vang','bach_kim','xam','trang']);
const DARK_SKIN=new Set(['s6','s7','s8']);
/** Swatches for the builder: skin, hair colour, background (the palette ids use look.js ACC_COLORS). */
export const COLORS={skin:Object.fromEntries(Object.entries(SKIN).map(([k,v])=>[k,v[0]])),hc:HC,bg:BG,
  hwc:Object.fromEntries(Object.entries(ACC_COLORS).map(([k,v])=>[k,v.c])),shirt:Object.fromEntries(Object.entries(ACC_COLORS).map(([k,v])=>[k,v.c]))};
export const NAMES={
  skin:{s1:'Da trắng hồng',s2:'Da sáng',s3:'Da ngà',s4:'Da trung bình',s5:'Da bánh mật',s6:'Da nâu',s7:'Da nâu đậm',s8:'Da nâu sẫm'},
  shape:{tron:'Mặt tròn',oval:'Mặt trái xoan',vuong:'Mặt vuông',tim:'Cằm nhọn'},
  age:{be:'Nhóc tì',teen:'Tuổi teen',lon:'Người lớn',gia:'Lớn tuổi'},
  hair:{ngan:'Tóc ngắn',dinh:'Đầu đinh',hoi:'Đầu hói',lech:'Tóc rẽ ngôi',dung:'Tóc dựng',xoan:'Tóc xoăn',afro:'Tóc xù',bob:'Tóc bob',dai:'Tóc dài',
    bui:'Búi cao',duoi:'Đuôi ngựa',bim:'Hai bím',mai:'Mái bằng',song:'Tóc lượn sóng',tet:'Tết lệch',chom:'Búi củ tỏi'},
  hc:{den:'Tóc đen',nau:'Tóc nâu',mat_ong:'Tóc mật ong',vang:'Tóc vàng',do:'Tóc đỏ',hong:'Tóc hồng',xanh:'Tóc xanh khói',tim:'Tóc tím',
    bach_kim:'Tóc bạch kim',xam:'Tóc muối tiêu',trang:'Tóc bạc trắng'},
  expr:{cuoi:'Cười hiền',toe:'Cười toe',nhay:'Nháy mắt',diu:'Dịu dàng',ngac:'Ngạc nhiên',then:'Bẽn lẽn',ngau:'Ngầu'},
  glasses:{0:'Không kính',tron:'Gọng tròn',vuong:'Gọng vuông',ram:'Kính râm',meo:'Mắt mèo'},
  head:{0:'Không đội',hijab:'Khăn hijab',khan:'Khăn buộc',luoi_trai:'Mũ lưỡi trai',len:'Mũ len',non_la:'Nón lá',tai_beo:'Mũ tai bèo',
    bang_do:'Băng đô',hoa:'Hoa cài',khan_dong:'Khăn đóng'},
  beard:{0:'Không râu',lun:'Lún phún',ria:'Ria mép',de:'Râu dê',quai:'Quai nón'},
  extra:{0:'Không thêm',bong_tai:'Bông tai',not_ruoi:'Nốt ruồi',bang_ca:'Băng cá nhân',tai_nghe:'Tai nghe'},
  bg:{kem:'Nền kem',hong:'Nền hồng',dao:'Nền đào',vang:'Nền vàng',mint:'Nền bạc hà',xanh:'Nền trời',lavender:'Nền oải hương',xam:'Nền xám',
    navy:'Nền đêm',la:'Nền lá non'},
};
/** Headwear that hides the top of the hair (a bun or a top knot is left out under it). */
const COVER=new Set(['hijab','luoi_trai','len','non_la','tai_beo','khan_dong']);
/** Headwear drawn without a colour of its own choosing. */
export const PLAIN_HEAD=new Set(['0','non_la']);

/* ---- hair (the head of a grown-up: centre 40,38; top ≈ 17; sides 21…59) ---- */
function hairBack(h,c,covered){
  switch(h){
    case'dai':case'mai':return `<path d="M18 44C12 10 68 10 62 44L65 72H15Z" fill="${c}"/>`;
    case'bui':return covered?'':`<circle cx="40" cy="12" r="8.5" fill="${c}"/>`;
    case'chom':return covered?'':`<circle cx="40" cy="12.5" r="6" fill="${c}"/>`;
    case'bob':return `<path d="M17 50C11 10 69 10 63 50Q52 56 40 54Q28 56 17 50Z" fill="${c}"/>`;
    case'duoi':return `<path d="M52 18Q74 20 70 46Q67 60 59 54Q66 40 54 28Z" fill="${c}"/>`;
    case'xoan':return `<g fill="${c}"><circle cx="23" cy="27" r="10"/><circle cx="31" cy="16" r="11"/><circle cx="48" cy="15" r="11"/><circle cx="57" cy="26" r="10"/><circle cx="61" cy="39" r="8"/><circle cx="19" cy="39" r="8"/></g>`;
    case'afro':return `<circle cx="40" cy="31" r="28" fill="${c}"/><g fill="${c}"><circle cx="15" cy="40" r="8"/><circle cx="65" cy="40" r="8"/></g>`;
    case'bim':return `<g fill="${c}"><ellipse cx="15" cy="46" rx="6" ry="11"/><ellipse cx="65" cy="46" rx="6" ry="11"/></g><g fill="#e0708a"><circle cx="16" cy="35" r="3"/><circle cx="64" cy="35" r="3"/></g>`;
    case'song':return `<path d="M18 42C12 10 68 10 62 42Q67 49 62 56Q66 63 59 67Q52 64 52 58H28Q28 64 21 67Q14 63 18 56Q13 49 18 42Z" fill="${c}"/>`;
    case'tet':return `<path d="M20 42C14 12 66 12 60 42Z" fill="${c}"/><g fill="${c}"><circle cx="58" cy="50" r="4.6"/><circle cx="60" cy="57.5" r="4.4"/><circle cx="61.5" cy="65" r="4.2"/><circle cx="62.5" cy="72" r="4"/></g><circle cx="62.5" cy="76.5" r="2" fill="#e0708a"/>`;
  }
  return '';
}
function hairFront(h,c){
  switch(h){
    case'ngan':return `<path d="M20 37Q18 13 40 12Q62 13 60 37Q56 25 45 22Q35 30 20 37Z" fill="${c}"/>`;
    case'dinh':return `<path d="M21 33Q21 15 40 15Q59 15 59 33Q55 22 40 21Q25 22 21 33Z" fill="${c}" opacity=".85"/>`;
    case'hoi':return `<g fill="${c}"><path d="M20 38Q19 30 23 27Q22 34 24.5 41Z"/><path d="M60 38Q61 30 57 27Q58 34 55.5 41Z"/></g><ellipse cx="33" cy="22" rx="5" ry="2.4" fill="#fff" opacity=".35"/>`;
    case'lech':return `<path d="M20 38Q18 14 38 13Q60 12 61 35Q57 24 47 21Q37 21 30 26Q24 30 20 38Z" fill="${c}"/><path d="M31 15Q34 20 30 26" fill="none" stroke="#00000022" stroke-width="1.2"/>`;
    case'dung':return `<path d="M20 36L19 22L25 25L26 14L32 20L36 10L41 18L46 10L49 19L55 13L55 23L61 21L60 36Q54 24 40 23Q26 24 20 36Z" fill="${c}"/>`;
    case'xoan':return `<path d="M21 34Q22 17 40 16Q58 17 59 34Q54 26 47 27Q42 22 36 27Q28 25 21 34Z" fill="${c}"/>`;
    case'afro':return `<path d="M21 33Q23 18 40 17Q57 18 59 33Q53 25 40 25Q27 25 21 33Z" fill="${c}"/>`;
    case'bob':return `<path d="M21 35Q20 14 40 14Q60 14 59 35Q51 28 40 29Q29 28 21 35Z" fill="${c}"/>`;
    case'mai':return `<path d="M20 40Q18 14 40 14Q62 14 60 40L58 31H22Z" fill="${c}"/>`;
    case'chom':return `<path d="M21 34Q22 17 40 16Q58 17 59 34Q54 25 40 24Q26 25 21 34Z" fill="${c}"/>`;
    case'duoi':return `<path d="M21 38Q21 15 40 15Q59 15 59 38Q52 25 41 22Q31 26 21 38Z" fill="${c}"/><circle cx="56" cy="22" r="3" fill="#e0708a"/>`;
  }
  return `<path d="M21 38Q21 15 40 15Q59 15 59 38Q52 25 41 22Q31 26 21 38Z" fill="${c}"/>`;
}
function headShape(s,fill){
  switch(s){
    case'oval':return `<ellipse cx="40" cy="38.5" rx="17.5" ry="21.5" fill="${fill}"/>`;
    case'vuong':return `<path d="M21 31Q21 17 40 17Q59 17 59 31V44Q58 58 40 59Q22 58 21 44Z" fill="${fill}"/>`;
    case'tim':return `<path d="M21 33Q21 17 40 17Q59 17 59 33Q58 47 40 59.5Q22 47 21 33Z" fill="${fill}"/>`;
  }
  return `<ellipse cx="40" cy="38" rx="19" ry="20.5" fill="${fill}"/>`;
}

/* ---- the face: eyes, brows, mouth (eyes at y 40, x 33 and 47; mouth at y 48) ---- */
const EYE='#3f302c';
function eyes(e,big){
  const rx=big?3.2:2.8,ry=big?3.9:3.4,dot=(x,r=1)=>`<circle cx="${x-.7}" cy="38.8" r="${r}" fill="#fff"/>`;
  const open=(x,k=1)=>`<ellipse cx="${x}" cy="40" rx="${rx*k}" ry="${ry*k}" fill="${EYE}"/>`+dot(x,big?1.2:1);
  const arc=(x,d)=>`<path d="M${x-3} 41q3 ${d} 6 0" fill="none" stroke="${EYE}" stroke-width="2" stroke-linecap="round"/>`;
  switch(e){
    case'toe':return arc(33,-3.5)+arc(47,-3.5);
    case'nhay':return open(33)+arc(47,-3);
    case'diu':return arc(33,2)+arc(47,2);
    case'ngac':return open(33,1.15)+open(47,1.15);
    case'then':return arc(33,2.4)+arc(47,2.4);
    case'ngau':return `<ellipse cx="33" cy="40.6" rx="${rx}" ry="${ry*.7}" fill="${EYE}"/><ellipse cx="47" cy="40.6" rx="${rx}" ry="${ry*.7}" fill="${EYE}"/>`;
  }
  return open(33)+open(47);
}
function brows(e,c){
  const y=e==='ngac'?31.5:33.5,l=e==='ngau'?`M29 33.2l8 1`:`M29 ${y}q4-2.2 8 0`,r=e==='ngau'?`M43 34.2l8-1`:`M43 ${y}q4-2.2 8 0`;
  return `<path d="${l}${r}" fill="none" stroke="${c}" stroke-width="1.7" stroke-linecap="round" opacity=".9"/>`;
}
function mouth(e,dark){
  const m=dark?'#4a2a20':'#a46e5e';
  switch(e){
    case'toe':return `<path d="M34.5 47.5q5.5 7.5 11 0Z" fill="#7a3b35"/><path d="M37.5 51.2q2.5-2 5 0q-2.5 1.6-5 0Z" fill="#e57d7d"/>`;
    case'nhay':return `<path d="M36 48q4 4 8 0" fill="none" stroke="${m}" stroke-width="1.8" stroke-linecap="round"/><path d="M41 50.3q1.5 2.2 3 0" fill="#e57d7d"/>`;
    case'diu':return `<path d="M37 49q3 1.6 6 0" fill="none" stroke="${m}" stroke-width="1.8" stroke-linecap="round"/>`;
    case'ngac':return `<ellipse cx="40" cy="50" rx="2.4" ry="3" fill="#7a3b35"/>`;
    case'then':return `<path d="M36.5 49q1.75-1.4 3.5 0t3.5 0" fill="none" stroke="${m}" stroke-width="1.6" stroke-linecap="round"/>`;
    case'ngau':return `<path d="M36 49.5q5 1.5 8.5-2" fill="none" stroke="${m}" stroke-width="1.8" stroke-linecap="round"/>`;
  }
  return `<path d="M36 48q4 4 8 0" fill="none" stroke="${m}" stroke-width="1.8" stroke-linecap="round"/>`;
}
function beard(b,c){
  const ria=`<path d="M33.5 46.6q3.5-2.6 6.5 0q3-2.6 6.5 0q-3 2.7-6.5 1q-3.5 1.7-6.5-1Z" fill="${c}"/>`;
  switch(b){
    case'lun':return `<path d="M23 44Q25 58 40 59.5Q55 58 57 44Q53 54 40 55Q27 54 23 44Z" fill="${c}" opacity=".35"/>`;
    case'ria':return ria;
    case'de':return ria+`<path d="M37 53.5q3 3 6 0q-.4 5-3 6.2q-2.6-1.2-3-6.2Z" fill="${c}"/>`;
    case'quai':return `<path d="M21.5 40Q22 59 40 62Q58 59 58.5 40Q56 52 50 53.5Q46 51.5 40 52.5Q34 51.5 30 53.5Q24 52 21.5 40Z" fill="${c}"/>`+ria;
  }
  return '';
}
function glasses(g){
  const k='#3a3230';
  switch(g){
    case'tron':return `<g fill="none" stroke="${k}" stroke-width="1.6"><circle cx="33" cy="40" r="5.8"/><circle cx="47" cy="40" r="5.8"/><path d="M38.8 40h2.4M27.2 39l-5-2M52.8 39l5-2"/></g>`;
    case'vuong':return `<g fill="none" stroke="${k}" stroke-width="1.6"><rect x="26.5" y="35.2" width="12.5" height="9.6" rx="2"/><rect x="41" y="35.2" width="12.5" height="9.6" rx="2"/><path d="M39 39.5h2M26.5 38.5l-4.5-1.6M53.5 38.5l4.5-1.6"/></g>`;
    case'ram':return `<g fill="${k}"><rect x="26" y="35.5" width="12.5" height="9" rx="4"/><rect x="41.5" y="35.5" width="12.5" height="9" rx="4"/></g><path d="M38.5 39h3" stroke="${k}" stroke-width="1.6"/><path d="M29 38.5h4" stroke="#fff" stroke-opacity=".5" stroke-width="1.2" stroke-linecap="round"/>`;
    case'meo':return `<g fill="none" stroke="#b8475f" stroke-width="1.7" stroke-linejoin="round"><path d="M25 35L38.6 36.6Q39 44 32.5 44.3Q26.2 44 25 35Z"/><path d="M55 35L41.4 36.6Q41 44 47.5 44.3Q53.8 44 55 35Z"/><path d="M38.6 39.5h2.8"/></g>`;
  }
  return '';
}
/** Headwear behind the head (the hijab's drape) and over it. k: the colour (look.js ACC_COLORS entry). */
function headBack(h,k){return h==='hijab'?`<path d="M40 11C18 11 14 33 15.5 52Q17 70 40 74Q63 70 64.5 52C66 33 62 11 40 11Z" fill="${k.c}"/>`:'';}
function headFront(h,k){
  switch(h){
    case'hijab':return `<path d="M21 42Q19 16 40 15.5Q61 16 59 42Q58 21 40 20.5Q22 21 21 42Z" fill="${k.c}"/><path d="M22 45Q25 61 40 63Q55 61 58 45Q60 67 40 68Q20 67 22 45Z" fill="${k.c}"/><path d="M24 26Q40 17 56 26" fill="none" stroke="${k.d}" stroke-width="1" opacity=".5"/>`;
    case'khan':return `<path d="M20 30Q21 14 40 14Q59 14 60 30Q50 25 40 25Q30 25 20 30Z" fill="${k.c}"/><g fill="${k.l}"><circle cx="30" cy="20" r="1.3"/><circle cx="40" cy="18" r="1.3"/><circle cx="50" cy="20" r="1.3"/><circle cx="35" cy="23.5" r="1.1"/><circle cx="45" cy="23.5" r="1.1"/></g><ellipse cx="60.5" cy="30" rx="3.2" ry="2.6" fill="${k.d}"/><path d="M61 31l5 7-3.2 1.2ZM60 31.5l1 8.5-3.2-.6Z" fill="${k.c}"/>`;
    case'luoi_trai':return `<path d="M20 30Q20 11 40 11Q60 11 60 30Z" fill="${k.c}"/><path d="M17 30Q40 24.5 63 30Q63 34.5 40 32.5Q17 34.5 17 30Z" fill="${k.d}"/><circle cx="40" cy="11.2" r="2" fill="${k.d}"/><path d="M40 12V29" stroke="${k.d}" stroke-width=".9" opacity=".6"/>`;
    case'len':return `<path d="M18 31Q18 6 40 6Q62 6 62 31Z" fill="${k.c}"/><rect x="16.5" y="25" width="47" height="8.5" rx="4.2" fill="${k.d}"/><circle cx="40" cy="5" r="5" fill="${k.l}"/>`;
    case'non_la':return `<path d="M5 27L40 1L75 27Q40 33 5 27Z" fill="#ecd394" stroke="#c9a95e" stroke-width="1.2"/><path d="M23 14H57M14 21H66" stroke="#d6b86f" stroke-width="1.1"/>`;
    case'tai_beo':return `<path d="M23 26Q24 11 40 11Q56 11 57 26Z" fill="${k.c}"/><path d="M14 30Q16 23.5 40 23.5Q64 23.5 66 30Q64 34 40 31Q16 34 14 30Z" fill="${k.d}"/>`;
    case'bang_do':return `<path d="M20.5 29Q22 16.5 40 16.5Q58 16.5 59.5 29" fill="none" stroke="${k.c}" stroke-width="3.6" stroke-linecap="round"/><path d="M52 19l-5-5v9zM52 19l6-3v8z" fill="${k.d}"/>`;
    case'hoa':return `<g fill="${k.c}"><circle cx="56" cy="19" r="3.2"/><circle cx="60" cy="22" r="3.2"/><circle cx="58.5" cy="26.5" r="3.2"/><circle cx="53.5" cy="26.5" r="3.2"/><circle cx="52" cy="22" r="3.2"/></g><circle cx="56" cy="23" r="2.2" fill="#f3d590"/>`;
    case'khan_dong':return `<path d="M19.5 31Q19.5 14 40 14Q60.5 14 60.5 31Q60.5 36.5 40 34.5Q19.5 36.5 19.5 31Z" fill="${k.c}"/><path d="M21 24.5Q40 20 59 24.5M20.5 29Q40 24.5 59.5 29" fill="none" stroke="${k.d}" stroke-width="1.3"/>`;
  }
  return '';
}
function extra(x,hijab){
  switch(x){
    case'bong_tai':return hijab?'':`<g fill="#e0b43f"><circle cx="21" cy="47" r="1.9"/><circle cx="59" cy="47" r="1.9"/></g>`;
    case'not_ruoi':return `<circle cx="49.5" cy="50.5" r="1" fill="#4a3530"/>`;
    case'bang_ca':return `<g transform="rotate(-25 53 44)"><rect x="48.5" y="42.2" width="9" height="3.8" rx="1.8" fill="#f3c99a"/><rect x="51.6" y="42.2" width="2.8" height="3.8" fill="#e8b27c"/></g>`;
    case'tai_nghe':return `<path d="M17 40Q17 7 40 7Q63 7 63 40" fill="none" stroke="#3a3436" stroke-width="3.2"/><rect x="13" y="35" width="8" height="13" rx="3.5" fill="#3a3436"/><rect x="59" y="35" width="8" height="13" rx="3.5" fill="#3a3436"/>`;
  }
  return '';
}
const FRECKLES=[[27,44],[29.6,46.2],[25.5,46.6],[53,44],[50.4,46.2],[54.5,46.6]];
// Grown-up head and body: [head scale, head centre y, body scale]. A child: a big head on small shoulders.
const AGE={be:[.95,44,.68],teen:[.97,40,.86],lon:[1,38,1],gia:[1,38,1]};

/** The bust of a parsed face (./face-code.js parseFace): background, body and clothes, then the head. */
function draw(o){
  const f={...DEFAULT_FACE,...o.f},[hs,hy,bs]=AGE[f.age]||AGE.lon,sk=SKIN[f.skin]||SKIN.s2,hair=HC[f.hc]||HC.nau;
  const hk=ACC_COLORS[f.hwc]||ACC_COLORS.do,hijab=f.head==='hijab',dark=DARK_SKIN.has(f.skin);
  // the clothes: the wardrobe's (shirt 'tu', ids the art knows; a colour the palette has) or a plain tee
  const tu=f.shirt==='tu',L={top:ART.top[o.top]?o.top:'ao_quen',acc:ART.acc[o.acc]?o.acc:'pk_khong',tint:{}};
  if(tu&&ACC_COLORS[o.topTint])L.tint[L.top]=o.topTint;
  if(tu&&ACC_COLORS[o.accTint])L.tint[L.acc]=o.accTint;
  const tee=ACC_COLORS[f.shirt],top=art(L,'top');
  const body=tu?`<path d="M12 80c2-23 54-23 56 0" fill="${topColour(L,o.g)}"/>`+topDetail(top)+(L.acc==='tui_cheo'?accBust('tui_cheo',accPaint(L)):'')
    :`<path d="M12 80c2-23 54-23 56 0" fill="${tee.c}"/><path d="M33 61q7 5 14 0" fill="none" stroke="${tee.d}" stroke-width="2.4"/>`;
  // the wardrobe accessory on the head, unless the face has its own glasses / headwear there
  const wa=tu&&L.acc!=='pk_khong'&&L.acc!=='tui_cheo'&&!((L.acc==='kinh_tron'||L.acc==='kinh_ram')&&f.glasses!=='0')&&
    !((L.acc==='non_la'||L.acc==='mu_len'||L.acc==='no_toc')&&f.head!=='0')?accBust(L.acc,accPaint(L)):'';
  const browC=LIGHT_HAIR.has(f.hc)?'#8a7a66':hair,covered=COVER.has(f.head);
  const old=f.age==='gia'?`<g fill="none" stroke="#5a3a2a" stroke-opacity=".35" stroke-width="1.3" stroke-linecap="round"><path d="M33 26.5q7-1.8 14 0M27.5 46.5q1 3 3 4M52.5 46.5q-1 3-3 4M30 44.6q3 1.4 6 0M44 44.6q3 1.4 6 0"/></g>`:'';
  const head=headBack(f.head,hk)+(hijab?'':hairBack(f.hair,hair,covered))+
    (hijab?'':`<g fill="${sk[1]}"><ellipse cx="21" cy="40" rx="3.2" ry="4.6"/><ellipse cx="59" cy="40" rx="3.2" ry="4.6"/></g>`)+headShape(f.shape,sk[0])+old+
    (f.age==='be'?'':beard(f.beard,hair))+
    `<g fill="#e08f86" opacity="${f.expr==='then'?.85:dark?.3:.5}"><ellipse cx="28" cy="46" rx="${f.expr==='then'?4.4:3.6}" ry="2.3"/><ellipse cx="52" cy="46" rx="${f.expr==='then'?4.4:3.6}" ry="2.3"/></g>`+
    (f.freckles?`<g fill="${dark?'#4a2d1f':'#b9774f'}" opacity=".8">${FRECKLES.map(([x,y])=>`<circle cx="${x}" cy="${y}" r=".8"/>`).join('')}</g>`:'')+
    (hijab?'':hairFront(f.hair,hair))+brows(f.expr,hijab?'#4b3936':browC)+(f.glasses==='ram'?'':eyes(f.expr,f.age==='be'))+mouth(f.expr,dark)+
    extra(f.extra==='tai_nghe'?'0':f.extra,hijab)+glasses(f.glasses)+headFront(f.head,hk)+wa+(f.extra==='tai_nghe'?extra('tai_nghe'):'');
  // scale(s) about (40, cy), moved to (40, y): the body about its bottom edge, the head about its centre
  const tf=(s,cy,y)=>s===1&&cy===y?'':` transform="translate(40 ${y}) scale(${s}) translate(-40 -${cy})"`;
  return `<rect width="80" height="80" fill="${BG[f.bg]||BG.kem}"/><g${tf(bs,80,80)}><rect x="34" y="50" width="12" height="13" rx="5" fill="${sk[1]}"/>${body}</g><g${tf(hs,38,hy)}>${head}</g>`;
}

/** The face of `code` (a string or parseFace's result) as an inline SVG, '' when it is not a face. */
export function faceSVG(code,size=40,label=''){
  const o=typeof code==='string'?parseFace(code):code;
  if(!o||o.kind!=='face')return '';
  return `<svg class="fc-svg" width="${size}" height="${size}" viewBox="0 0 80 80" ${label?`role="img" aria-label="${esc(label)}"`:'aria-hidden="true"'} focusable="false">${draw(o)}</svg>`;
}
/** What a chat avatar shows for a person or a message: the drawn face, the emoji of an emoji code, else its `av`. */
export function avInner(who){
  const o=parseFace(who?.fc);
  if(o?.kind==='face')return faceSVG(o,64);
  return esc(o?.kind==='emoji'?o.emoji:(who?.av||'🌸'));
}
