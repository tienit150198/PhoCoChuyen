/** 💍 The wedding party's show (live/wedding.py, drawn by ./walk.js in the 'wedding' scene): the MC's programme, the
 * neighbours at the tables, the kids and teens running about with their sayings, the lion dance (múa lân, with its
 * drum, biting a lì xì off a pole), the stage with its dance floor, a disco ball and coloured beams, four loa in the
 * corners pulsing on the beat, confetti when the couple comes in and fireworks at the end, and the music.
 * Everything follows the party clock (seconds from the start, `s`; negative while guests gather), and the lines are
 * picked from the wedding id and the clock, so every guest sees and hears the same thing at the same moment. No
 * server frames: the show is the same for everyone without a single extra message.
 * The music is recorded, royalty free (CC0, public/music/CREDITS.md): a funky house and a disco loop for the party,
 * Wagner's Bridal Chorus (Musopen's recording) as the couple comes in, lion dance drums under the lion. Each guest
 * plays the part the party clock is at (a track's position = party seconds into its section, modulo its length), and
 * the speakers and lights follow each track's tempo (beat()), heard or not.
 * 🎧 The groom picks the music (live/wedding.py `wed_music`; the bride when he is away): setPick() takes the room's
 * choice {k, at}, and from party second `at` on that track plays at (s − at) modulo its length for everyone; the march
 * and the lion drums still come first, then the pick again. The MC says so when the song changes.
 * Gentle on the eyes: colour changes at most on the beat (≤ 2.9 a second, the 170 BPM EDM), only on the stage, the beams and the
 * speakers, never the whole screen; with "Giảm chuyển động" (or prefers-reduced-motion) the beams stand still and the
 * colours change slowly. */
import {audioContext,wantAudio,duck} from '../audio.js';
import {paintLion} from '../scenes/stroll.js';

// Drawn like the players (./look.js items): [hair, shade, skin, top, bottom, shoes, acc]
const look=([hair,shade,skin,top,bottom,shoes,acc])=>({hair,shade,skin,top,bottom,shoes,acc,uniform:false});
const MC={id:'mc',name:'MC Thanh Tâm',role:'MC',g:'male',lk:look(['toc_ngan','mau_den','da_sang','ao_vest','quan_xam','giay_nau','pk_khong']),x:480,y:272};
const NB=[   // neighbours, standing by the tables (never on the red carpet)
  {name:'Bác Tư',g:'male',lk:look(['toc_ngan','mau_bach_kim','da_trung','ao_so_mi','quan_xam','dep_lao','kinh_tron']),x:205,y:430},
  {name:'Bà Năm',g:'female',lk:look(['toc_bui','mau_bach_kim','da_trung','ao_dai','vay_dai','dep_lao','pk_khong']),x:395,y:430},
  {name:'Chú Sáu',g:'male',lk:look(['toc_ngan','mau_den','da_ngam','ao_thun_xanh','quan_jean','giay_nau','pk_khong']),x:205,y:735},
  {name:'Cô Ba',g:'female',lk:look(['toc_bob','mau_den','da_sang','ao_hoa','vay_xoe','giay_do','pk_khong']),x:395,y:735},
  {name:'Anh Tèo',g:'male',lk:look(['toc_xoan','mau_nau','da_trung','ao_hoodie','quan_jean','giay_trang','kinh_ram']),x:56,y:585},
  {name:'Chị Mận',g:'female',lk:look(['toc_duoi_ngua','mau_mat_ong','da_hong','ao_len','quan_kem','giay_trang','pk_khong']),x:544,y:585},
].map((n,i)=>({...n,id:`nb${i}`,role:'Hàng xóm'}));
const KIDS=[
  {name:'Bé Na',g:'female',lk:look(['toc_duoi_ngua','mau_den','da_sang','ao_chi_may','vay_xoe','giay_do','pk_khong'])},
  {name:'Cu Tí',g:'male',lk:look(['toc_ngan','mau_den','da_trung','ao_thun_kem','quan_short','dep_lao','pk_khong'])},
  {name:'Bin',g:'male',lk:look(['toc_xoan','mau_nau','da_sang','ao_hoodie','quan_jean','giay_trang','mu_len'])},
  {name:'Su Su',g:'female',lk:look(['toc_bob','mau_hong','da_hong','ao_thun_xanh','quan_short','giay_trang','kinh_ram'])},
].map((k,i)=>({...k,id:`kid${i}`,role:'Bạn nhỏ',small:true}));
const KID_K=.78;   // kids are drawn smaller
const KID_TIMES=[[-200,-130],[120,190],[200,265],[380,440],[520,575]];   // when the kids run in (party seconds), never with the lion
export const LION=[[40,110,false],[280,350,true],[450,505,false]];       // [from, to, comes from the right]
const SAY=5.5;                                                           // seconds a line stays up
/** The dishes of the mâm cỗ (game/wedding_live.py DISHES, same order) and what the drinks look like. */
export const DISH_ICONS=['🍗','🍙','🥟','🍲','🥩','🫕','🦐','🍧'];
export const STAGE=[170,205,430,310];   // the stage (live/street_data.py: the wedding's second walkable rectangle): the dance floor

const MC_LINES=[
  [-290,'Kính mời quý khách vào chỗ, tiệc sắp bắt đầu rồi ạ! 💐'],
  [-180,'Cô chú anh chị cứ tự nhiên dùng trà bánh nha, còn ít phút nữa thôi!'],
  [-60,'Một phút nữa thôi! Ai chưa có chỗ thì nhanh chân nào 🏃'],
  [0,'Kính thưa quý vị! Chào mừng đến lễ cưới của {a} và {b} 💍'],
  [8,'Xin một tràng pháo tay thật lớn cho đôi uyên ương nào! 👏👏👏'],
  [34,'Đoàn lân về chúc mừng hai họ rồi! Tùng tùng cắc! 🦁'],
  [116,'Khai tiệc! Mời cả nhà nâng ly: Một, hai, ba… dzô! 🥂'],
  [150,'Cỗ hôm nay có gà luộc, xôi gấc, nem rán, lẩu thái… cả nhà gắp thật nhiều vào nha!'],
  [196,'Sàn nhảy mở rồi! Ai thích quẩy thì lên sân khấu cùng cô dâu chú rể nào 💃'],
  [236,'Mời cô dâu chú rể cắt bánh cưới và rót tháp ly! 🎂'],
  [274,'Đoàn lân lại tới kìa! Lì xì cho lân lấy hên nào! 🧧'],
  [370,'Chúc {a} và {b} trăm năm hạnh phúc, đầu bạc răng long! 💕'],
  [410,'Ai có tiết mục văn nghệ thì lên sân khấu luôn nha, micro sẵn rồi! 🎤'],
  [444,'Lân múa thêm một vòng nữa nè, cả nhà vỗ tay nào! 👏'],
  [518,'Màn tung hoa cưới đây! Các bạn độc thân lại gần sân khấu nào 💐'],
  [548,'Tiệc sắp tàn rồi, cả nhà chụp chung tấm ảnh nào! 📸'],
  [575,'Pháo hoa nè! Chúc hai bạn trăm năm hạnh phúc! 🎆'],
  [592,'Chúc mọi người về nhà bình an. Hẹn gặp ở đám cưới sau nha! 👋'],
];
/** What the MC says when the groom (the bride, the couple) changes the song. */
const PICK_BY={groom:'Chú rể',bride:'Cô dâu',couple:'Cô dâu chú rể'};
function pickLine(P){
  const who=PICK_BY[P.who]||PICK_BY.couple;
  if(P.k==='auto')return `${who} cho nhạc chạy theo chương trình tiệc nha cả nhà! 🎶`;
  if(P.k==='love')return `${who} chọn nhạc chậm rồi, mời cô dâu chú rể nhảy điệu đầu tiên nào 💞`;
  return `${who} đổi nhạc rồi: ${TRACKS[P.k]?.name||'nhạc mới'}! Quẩy lên nào! 🎧`;
}
const NB_LINES=[
  'Chúc hai cháu trăm năm hạnh phúc, sớm có tin vui nha!','Cỗ hôm nay ngon ghê, nem rán giòn rụm luôn!',
  'Hồi xưa bác cưới có năm mâm thôi, giờ linh đình quá!','Cô dâu chú rể đẹp đôi quá trời đất ơi!',
  'Bao giờ có cháu bế đây hai đứa? 👶','Nhạc vui quá, bà đứng dậy nhảy một bài nè 💃',
  'Thằng cu nhà tui cũng sắp cưới rồi đó, nhớ qua ăn cỗ nha!','Ai gắp giùm tui miếng gà với, xa quá với không tới 🍗',
  'Đám cưới này đông vui nhất phố từ đầu năm tới giờ!','Lân múa đẹp quá, năm nay chắc làm ăn phát đạt!',
  'Ăn từ từ thôi tụi nhỏ, cỗ còn nhiều lắm!','Một, hai, ba, dzô! Chúc mừng hai đứa nha! 🍻',
  'Nhìn {a} với {b} là biết trời sinh một cặp rồi!','Canh măng này ai nấu mà ngọt nước dữ vậy!',
  'Loa to quá, nhưng mà vui! Quẩy lên mọi người ơi 🔊','Xôi gấc đỏ au, ăn lấy may cả năm nha!',
  'Bia thì ít thôi nha, còn chạy xe về đó 🛵','Đèn sân khấu đẹp ghê, như đi xem ca nhạc vậy!',
];
const KID_LINES=[
  'Trúc xinh trúc mọc đầu đình, em xinh em đứng một mình cũng xinh 🎶','Tùng dinh dinh tùng tùng tùng dinh dinh! 🥁',
  'Cô dâu xinh xỉu up xỉu down luôn á 😍','Chú rể hôm nay đẹp trai mười điểm không có nhưng 🤩',
  'Đám cưới này đỉnh nóc kịch trần bay phấp phới 🚀','Mãi keo, mãi đỉnh nha cô dâu chú rể 💯',
  'Chúc anh chị hạnh phúc như điện thoại sạc đầy 100% pin 🔋','Ủa có gà luộc không ạ? Em đang ăn kiêng… kiêng đói 🐔',
  'Mlem mlem, cỗ ngon quá trời quá đất 😋','Ai ế thì giơ tay lên nào! 🙋 …ủa sao cả bàn giơ tay vậy',
  'Con mèo mà trèo cây cau, hỏi thăm chú chuột đi đâu vắng nhà 🎶','Bống bống bang bang, lên ăn cơm vàng cơm bạc nhà ta 🎶',
  'Đi đám cưới mà vui như đi concert vậy đó 🎤','Cô dâu chú rể visual quá, cho em xin vía với ✨',
  'Real hay fake đây, đẹp đôi dữ vậy trời 👀','Tình yêu của anh chị là chân ái, còn em là… chân gà 🍗',
  'Gì chứ ăn cỗ là em có mặt đầu tiên 🙋','Lân ơi lân, cho em lì xì với 🧧',
  'Hôm nay em không ăn kiêng, hôm nay em ăn cỗ 🍤','Anh chị cưới nhau rồi thì nhớ chia kẹo cho tụi em nha 🍬',
  'Lên sân khấu nhảy đi mọi người, em nhảy trước nè 💃','Có pháo hoa không ạ? Em muốn xem pháo hoa 🎆',
];

/* ---- the clock and the picks (the same on every guest's screen) ---- */
export const hash=n=>{n=Math.imul(n^n>>>16,0x45d9f3b);n=Math.imul(n^n>>>16,0x45d9f3b);return (n^n>>>16)>>>0;};
const fill=(text,w)=>text.replaceAll('{a}',w.a).replaceAll('{b}',w.b);
const kidsOn=s=>KID_TIMES.some(([a,b])=>s>=a&&s<b);
const lionAt=s=>LION.find(([a,b])=>s>=a&&s<b)||null;
const ease=x=>x<=0?0:x>=1?1:x*x*(3-2*x);
const lerp=(a,b,k)=>a+(b-a)*k;
/** Who speaks in this slot of 7 seconds: a neighbour, or a kid while the kids are about. */
function chatter(w,s){
  if(s<-300||s>=600)return null;
  const slot=Math.floor(s/7),from=slot*7;if(s-from>SAY)return null;
  const h=hash(w.id*7919+slot+1000);
  if(MC_LINES.some(([t])=>Math.abs(t-from)<4)||(PICK&&Math.abs(PICK.s-from)<6))return null;   // the MC has the floor
  const kid=kidsOn(from)&&h%5<3;
  if(kid){const i=h%KIDS.length;return {who:'kid',i,text:KID_LINES[(h>>>3)%KID_LINES.length],t0:from};}
  if(h%4===3)return null;                                      // a quiet moment now and then
  return {who:'nb',i:h%NB.length,text:fill(NB_LINES[(h>>>3)%NB_LINES.length],w),t0:from};
}
function mcLine(w,s){
  const P=PICK;if(P&&s>=P.s&&s<P.s+SAY+1)return {text:pickLine(P),t0:P.s};   // 🎧 a new song: the MC says so
  for(const [t,text] of MC_LINES)if(s>=t&&s<t+SAY+1)return {text:fill(text,w),t0:t};return null;}
/** A kid's spot: running a loop around the lawn while the kids are about, in from the gate and out again. */
function kidPos(i,s,sec){
  const win=KID_TIMES.find(([a,b])=>s>=a&&s<b);if(!win)return null;
  const [a,b]=win,f=Math.min(1,(s-a)/4,(b-s)/4),an=s*.42+i*Math.PI/2;
  const x=300+Math.cos(an)*(150+i*18),y=600+Math.sin(an)*(115-i*8);
  return [300+(x-300)*f,860+(y-860)*f,Math.abs(Math.sin(sec*9+i))*4];
}

/* ---- the music's clock: which track, where in it, and its beat (heard or not) ---- */
const TRACKS={   // public/music/CREDITS.md; len: the file's length (s), bpm and off: its tempo and first beat; name: the picker's label
  house:{f:'wedding-house',len:67.5,bpm:128,off:.035,name:'Funky house',icon:'🏖️'},
  disco:{f:'wedding-disco',len:133.09,bpm:110,off:0,name:'Disco sôi động',icon:'🪩'},
  march:{f:'wedding-march',len:42,bpm:71,off:.3,once:true},
  lion:{f:'wedding-lion',len:42,bpm:105.6,off:0},
  edm:{f:'wedding-edm',len:93.176,bpm:170,off:0,name:'Quẩy EDM',icon:'🔥'},
  remix:{f:'wedding-remix',len:68.571,bpm:140,off:0,name:'Remix bay phòng 140',icon:'🚀'},
  electro:{f:'wedding-electro',len:60,bpm:128,off:0,name:'Electro house',icon:'⚡'},
  latin:{f:'wedding-latin',len:80,bpm:120,off:0,name:'House Latin',icon:'🌴'},
  funk:{f:'wedding-funk',len:66.207,bpm:87,off:.103,name:'Funk nhún nhảy',icon:'🎸'},
  love:{f:'wedding-love',len:80.842,bpm:95,off:0,name:'Nhạc chậm cho cặp đôi',icon:'💞'},
};
const KEYS=Object.keys(TRACKS);
/** The picker's list (live/wedding.py WL.MUSIC order): [key, icon, label]. */
export function playlist(keys){
  return (keys||['auto',...KEYS.filter(k=>TRACKS[k].name)]).filter(k=>k==='auto'||TRACKS[k]?.name)
    .map(k=>k==='auto'?[k,'🎶','Theo chương trình']:[k,TRACKS[k].icon,TRACKS[k].name]);
}
let PICK=null;   // the room's choice: {k, s: the party second it was made, who}
/** The room's music choice (live/wedding.py wed_music {k, at, who}; null: the programme); partyAt: the party's start. */
export function setPick(m,partyAt){PICK=m&&(m.k==='auto'||TRACKS[m.k]?.name)&&typeof m.at==='number'?{k:m.k,s:m.at-partyAt,who:m.who}:null;}
export const picked=()=>PICK?.k||'auto';
/** What plays at party second s: [track, seconds into its section]. The march and the lion first, then the pick. */
export function track(s){
  const l=lionAt(s);if(l)return ['lion',s-l[0]];
  if(s>=0&&s<38)return ['march',s];
  const P=PICK;if(P&&P.k!=='auto'&&s>=P.s)return [P.k,s-P.s];
  if(s<0)return ['disco',s+300];
  if(s<280)return ['house',s-38];
  return ['disco',s-280];
}
const BT={k:'',n:0,ph:0};
/** The beat at party second s: {k: the track, n: beat number, ph: 0..1 within the beat}. One shared object. */
export function beat(s){
  const [k,pos]=track(s),T=TRACKS[k],p=T.once?pos:((pos%T.len)+T.len)%T.len,b=(p-T.off)*T.bpm/60,n=Math.floor(b);
  BT.k=k;BT.n=n+(KEYS.indexOf(k)+1)*1e5;BT.ph=b-n;return BT;
}

/* ---- drawing (world units: the 600 × 900 scene) ---- */
const PALETTE=['#ff5d73','#ffd166','#06d6a0','#4cc9f0','#f78fb3','#b388ff'];
const FW_DAY=['#e5383b','#f4a300','#0aa36c','#1e88e5','#d81b60','#7e57c2'];   // fireworks by day: deeper colours
function bulbs(c,pts,sec,dark,phase){
  pts.forEach(([x,y],i)=>{
    const col=PALETTE[(i+Math.floor(sec*2.5+phase))%5],tw=.55+.45*Math.sin(sec*5+i*1.7+phase);
    if(dark){c.globalAlpha=.28*tw;c.fillStyle=col;c.beginPath();c.arc(x,y,9,0,Math.PI*2);c.fill();}
    c.globalAlpha=.45+.55*tw;c.fillStyle=col;c.beginPath();c.arc(x,y,dark?3.6:3,0,Math.PI*2);c.fill();c.globalAlpha=1;
  });
}
const sag=(x0,y0,x1,y1,n,d)=>Array.from({length:n+1},(_,i)=>{const t=i/n;return [x0+(x1-x0)*t,y0+(y1-y0)*t+Math.sin(t*Math.PI)*d];});
const STRINGS=[sag(96,226,504,226,20,6),sag(30,330,262,330,9,16),sag(338,330,570,330,9,16),sag(30,860,262,860,9,14),sag(338,860,570,860,9,14),
  sag(40,330,40,860,14,0),sag(560,330,560,860,14,0)];
/** A character from walk.js's sprite cache (`sprite(id, look, gender)`: 110 × 160 player units, feet at 55,150). */
function figure(c,p,x,y,bob,{sprite,av}){
  const k=av*(p.small?KID_K:1),sp=sprite(p.id,p.lk,p.g);
  c.drawImage(sp,x-55*k,y-150*k-bob,110*k,160*k);
}
const top=p=>(p.small?KID_K:1)*66;   // the name tag's height above the feet
const pulseOf=(fx)=>fx.still?0:Math.max(0,1-fx.bt.ph*2.6);   // 1 on the beat, 0 a third of a beat later
const colourOf=(fx,k=0)=>PALETTE[((fx.still?Math.floor(fx.sec/4):fx.bt.n)+k)%PALETTE.length];

/** 🔊 A loa: a floor speaker, its cone pushing out on the beat, two sound waves. */
const SPEAKERS=[[22,322,1],[578,322,-1],[22,884,1],[578,884,-1]];
function speaker(c,x,y,side,fx){
  const p=pulseOf(fx),col=colourOf(fx,side>0?0:2);
  c.fillStyle='rgba(0,0,0,.18)';c.beginPath();c.ellipse(x+2,y+1,18,5,0,0,Math.PI*2);c.fill();
  c.fillStyle='#2a2a33';c.beginPath();c.roundRect(x-15,y-54,30,54,5);c.fill();
  c.strokeStyle='#4a4a58';c.lineWidth=1.5;c.stroke();
  c.fillStyle='#3b3b47';c.beginPath();c.arc(x,y-43,5.5,0,Math.PI*2);c.fill();c.fillStyle='#8c8c99';c.beginPath();c.arc(x,y-43,2.4,0,Math.PI*2);c.fill();
  const r=10.5+p*1.8;
  c.fillStyle='#45455a';c.beginPath();c.arc(x,y-19,r+1.5,0,Math.PI*2);c.fill();
  c.fillStyle='#17171e';c.beginPath();c.arc(x,y-19,r-1.5,0,Math.PI*2);c.fill();
  c.fillStyle='#5b5b6e';c.beginPath();c.arc(x,y-19,3.6+p*1.2,0,Math.PI*2);c.fill();
  c.fillStyle=col;c.globalAlpha=.55+.45*p;c.beginPath();c.arc(x+10,y-50,1.8,0,Math.PI*2);c.fill();   // the LED
  if(!fx.still){c.strokeStyle=col;c.lineWidth=2;   // waves toward the lawn
    for(let k=0;k<2;k++){const a=(fx.bt.ph+k*.5)%1;c.globalAlpha=(1-a)*.6;c.beginPath();c.arc(x,y-19,16+a*20,side>0?-.7:Math.PI-.7,side>0?.7:Math.PI+.7);c.stroke();}}
  c.globalAlpha=1;
}
/** The dance floor on the stage: lit tiles that change on the beat. */
function floor(c,fx){
  const [x0,y0,x1]=[224,214,376],tw=25.3,th=23,cols=6,rows=4,n=fx.still?Math.floor(fx.sec/4):fx.bt.n;
  c.globalAlpha=fx.dark?.32:.2;c.fillStyle=fx.dark?'#ffffff':'#7a5a4a';c.fillRect(x0,y0,x1-x0,rows*th);c.globalAlpha=1;
  for(let i=0;i<cols*rows;i++){const h=hash(n*31+i*7+fx.w.id);if(h%3)continue;
    c.globalAlpha=(fx.dark?.6:.42)*(fx.still?1:.6+.4*pulseOf(fx));c.fillStyle=PALETTE[h%PALETTE.length];
    c.fillRect(x0+(i%cols)*tw+1,y0+Math.floor(i/cols)*th+1,tw-2,th-2);}
  c.globalAlpha=1;c.strokeStyle=fx.dark?'#ffffff40':'#ffffff90';c.lineWidth=1;c.beginPath();
  for(let i=0;i<=cols;i++){c.moveTo(x0+i*tw,y0);c.lineTo(x0+i*tw,y0+rows*th);}for(let j=0;j<=rows;j++){c.moveTo(x0,y0+j*th);c.lineTo(x1,y0+j*th);}c.stroke();
}
/** Under and among the guests: the lights, the dance floor, the speakers, the MC, the neighbours, the kids, the pole. */
export function ground(c,fx){
  const {s,sec,dark}=fx;
  STRINGS.forEach((pts,k)=>{c.strokeStyle=dark?'#ffffff33':'#5a4a3a40';c.lineWidth=1;c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke();bulbs(c,pts,sec,dark,k*1.3);});
  floor(c,fx);
  for(const [x,y,side] of SPEAKERS)speaker(c,x,y,side,fx);
  figure(c,MC,MC.x,MC.y,Math.abs(Math.sin(sec*3))*1.5,fx);
  c.fillStyle='#3a3a3a';c.fillRect(MC.x+11,MC.y-40,3,12);c.fillStyle='#777';c.beginPath();c.arc(MC.x+12.5,MC.y-42,4,0,Math.PI*2);c.fill();   // the microphone
  NB.forEach((n,i)=>figure(c,n,n.x,n.y,Math.max(0,Math.sin(sec*2+i))*1.2,fx));
  KIDS.forEach((k,i)=>{const p=kidPos(i,s,sec);if(p)figure(c,k,p[0],p[1],p[2],fx);});
  const l=lionState(s,fx);if(l&&l.pole)pole(c,l,sec);
}

/* ---- 🦁 the lion dance: in from one side, dancing about the lawn, a jump now and then, it walks up to the pole,
 * rears and bites the lì xì, then dances off holding it ---- */
const ENTER=7,EXIT=7,ENV_X=300,ENV_Y=462,LY=590;
const LS={x:0,y:0,rtl:false,pole:false,u:0,o:{rear:0,hop:0,mouth:undefined,env:false,beat:0}};
function lionX(u,dur,dir){
  const x0=dir<0?700:-100,x1=dir<0?-100:700,ub=dur*.55;
  let x=300-dir*130*Math.cos((u-ENTER)*.4+Math.PI/2);   // wander about the middle of the lawn
  x=lerp(x,ENV_X-dir*84,ease(Math.max(0,1-Math.abs(u-ub)/6)*1.5));   // up to the pole, then a lunge for the bite
  x=lerp(x,ENV_X-dir*50,u<ub?ease((u-(ub-1.3))/1.2):ease(1-(u-ub)/2.5));
  x=lerp(x0,x,ease(u/ENTER));x=lerp(x,x1,ease((u-(dur-EXIT))/EXIT));
  return x;
}
function lionState(s,fx){
  const l=lionAt(s);if(!l)return null;
  const [a,b,rtl]=l,u=s-a,dur=b-a,dir=rtl?-1:1,ub=dur*.55,o=LS.o;
  LS.u=u;LS.x=lionX(u,dur,dir);
  const dx=lionX(u+.25,dur,dir)-LS.x,near=Math.abs(u-ub)<3.5;
  LS.rtl=near?rtl:dx<-.4?true:dx>.4?false:rtl;
  LS.y=LY+Math.sin(u*1.3)*7;
  LS.pole=u<ub+.2;
  o.rear=u>ub-1.8&&u<ub+.6?Math.sin(Math.min(1,(u-(ub-1.8))/2.4)*Math.PI):0;
  o.mouth=u>ub-1.4&&u<ub?1:u>=ub&&u<ub+.3?0:undefined;
  o.env=u>=ub;
  const hp=u%2.7;o.hop=!near&&u>ENTER&&u<dur-EXIT&&hp<.5?Math.sin(hp/.5*Math.PI):0;
  o.beat=fx.bt.ph;
  return LS;
}
function pole(c,l,sec){   // a bamboo pole with the lì xì hanging on a red string
  const px=ENV_X+(l.rtl?-30:30),sway=Math.sin(sec*2)*2;
  c.strokeStyle='#8b6a3e';c.lineWidth=4;c.lineCap='round';c.beginPath();c.moveTo(px,LY+8);c.lineTo(px,ENV_Y-40);c.lineTo(ENV_X+sway,ENV_Y-44);c.stroke();
  c.fillStyle='#6b5030';c.beginPath();c.ellipse(px,LY+9,9,3.5,0,0,Math.PI*2);c.fill();
  c.strokeStyle='#d8322e';c.lineWidth=1.4;c.beginPath();c.moveTo(ENV_X+sway,ENV_Y-44);c.lineTo(ENV_X+sway*1.5,ENV_Y-10);c.stroke();
  c.save();c.translate(ENV_X+sway*1.5,ENV_Y-10);c.rotate(sway*.04);
  c.fillStyle='#a3201d';c.fillRect(-9,0,18,25);c.fillStyle='#e02d28';c.fillRect(-8,1,16,23);c.fillStyle='#f5c242';c.fillRect(-8,7,16,3);
  c.beginPath();c.arc(0,16,3.4,0,Math.PI*2);c.fill();c.restore();
}
function drum(c,x,y,sec,fx){   // the drum on its little cart, beaten on the beat
  const hit=pulseOf(fx);
  c.fillStyle='rgba(0,0,0,.15)';c.beginPath();c.ellipse(x,y+3,22,5,0,0,Math.PI*2);c.fill();
  c.fillStyle='#5b3a22';c.fillRect(x-16,y-10,32,10);c.fillStyle='#333';c.beginPath();c.arc(x-11,y,4,0,Math.PI*2);c.arc(x+11,y,4,0,Math.PI*2);c.fill();
  c.fillStyle='#b8322c';c.beginPath();c.ellipse(x,y-24,17,15,0,0,Math.PI*2);c.fill();
  c.fillStyle='#f3e3c3';c.beginPath();c.ellipse(x,y-36,16,5.5,0,0,Math.PI*2);c.fill();c.strokeStyle='#f5c242';c.lineWidth=2;c.stroke();
  c.strokeStyle='#7a4a1e';c.lineWidth=2.4;c.lineCap='round';
  for(const k of [-1,1]){const lift=(k<0?hit:1-hit)*10;c.beginPath();c.moveTo(x+k*16,y-48-lift);c.lineTo(x+k*5,y-38-lift*.3);c.stroke();}
}
/** Over the guests: the lion dance, the beams and the disco ball, confetti and fireworks. */
export function over(c,fx){
  const {s,sec}=fx,l=lionState(s,fx);
  if(l){drum(c,l.x-(l.rtl?-105:105),l.y+26,sec,fx);c.save();c.translate(l.x,l.y);c.scale(1.15,1.15);paintLion(c,0,0,sec,l.rtl,l.o);c.restore();}
  if(s>-300&&s<fx.L)disco(c,fx);
  if(!fx.still&&s>=0&&s<7)confetti(c,s,fx);
  if(s>=fx.L-26&&s<fx.L+2)fireworks(c,s,fx);
}
/** 🪩 The disco ball under the tent and its beams sweeping the lawn (colours change on the beat). */
function disco(c,fx){
  const bx=300,by=82,sec=fx.sec,still=fx.still,p=pulseOf(fx),dark=fx.dark;
  c.save();c.globalCompositeOperation=dark?'lighter':'source-over';
  for(let i=0;i<6;i++){
    const an=Math.PI/2+(i-2.5)*.33+(still?0:Math.sin(sec*.7+i*1.3)*.32),len=300+(i%3)*90,w=.075;
    const ex=bx+Math.cos(an)*len,ey=by+Math.sin(an)*len;
    c.globalAlpha=(dark?.16:.1)+(dark?.08:.04)*p;c.fillStyle=colourOf(fx,i);
    c.beginPath();c.moveTo(bx,by);c.lineTo(bx+Math.cos(an-w)*len,by+Math.sin(an-w)*len);c.lineTo(bx+Math.cos(an+w)*len,by+Math.sin(an+w)*len);c.closePath();c.fill();
    c.globalAlpha=(dark?.3:.18);c.beginPath();c.ellipse(ex,ey,30,11,0,0,Math.PI*2);c.fill();
  }
  c.restore();
  c.strokeStyle='#9a9aa8';c.lineWidth=1;c.beginPath();c.moveTo(bx,32);c.lineTo(bx,by-13);c.stroke();
  c.fillStyle='#c9ccd6';c.beginPath();c.arc(bx,by,13,0,Math.PI*2);c.fill();
  c.save();c.beginPath();c.arc(bx,by,13,0,Math.PI*2);c.clip();   // the mirror tiles, turning
  const turn=still?0:(sec*1.2)%1;
  for(let j=-3;j<=3;j++)for(let i=-4;i<=4;i++){const h=hash(i*13+j*7+50),lit=(h+Math.floor(still?sec/4:sec*3))%5===0;
    c.fillStyle=lit?'#ffffff':(h%2?'#a8acb8':'#e3e6ee');c.fillRect(bx+(i+turn)*4-1.8,by+j*4-1.8,3.4,3.4);}
  c.restore();
  if(!still)for(let k=0;k<3;k++){const h=hash(Math.floor(sec*2.5)*3+k),x=bx-11+h%22,y=by-11+(h>>>5)%22,a=.5+.5*Math.sin(sec*9+k);   // sparkles
    c.globalAlpha=a;c.strokeStyle='#ffffff';c.lineWidth=1.3;c.beginPath();c.moveTo(x-4,y);c.lineTo(x+4,y);c.moveTo(x,y-4);c.lineTo(x,y+4);c.stroke();}
  c.globalAlpha=1;
}
/** 🎊 Confetti as the couple comes in (party seconds 0 to 7), falling over the whole lawn. */
function confetti(c,s,fx){
  for(let i=0;i<110;i++){const h=hash(fx.w.id*131+i),d=(h%100)/60,t=s-d;if(t<0)continue;
    const x=(h>>>7)%600+Math.sin(t*2.2+i)*18,y=-10+t*(90+(h>>>3)%70),a=Math.min(1,(7-s)/1.5);if(y>900)continue;
    c.globalAlpha=a;c.fillStyle=(i%2?PALETTE:FW_DAY)[i%PALETTE.length];const wd=7*Math.abs(Math.cos(t*5+i));c.fillRect(x-wd/2,y,wd+.8,9);}
  c.globalAlpha=1;
}
/** 🎆 Fireworks at the end: a rocket about every second over the lawn, each bursting into sparks. */
function fireworks(c,s,fx){
  const L=fx.L,dark=fx.dark;
  c.save();if(dark)c.globalCompositeOperation='lighter';
  c.lineCap='round';
  for(let k=0;k<40;k++){
    const h=hash(fx.w.id*977+k),t0=L-25+k*.6+(h%5)*.08,age=s-t0;if(age<0||age>2.9)continue;
    const x=60+(h>>>4)%480,hy=320+(h>>>12)%260,col=(dark?PALETTE:FW_DAY)[(h>>>9)%PALETTE.length];
    if(age<.9){const y=880-(880-hy)*ease(age/.9);c.globalAlpha=1;c.strokeStyle=dark?'#ffe9a8':'#e0a020';c.lineWidth=2.4;c.beginPath();c.moveTo(x,y);c.lineTo(x,y+16);c.stroke();continue;}
    const b=age-.9,fade=Math.max(0,1-b/2),r=1+b*1.4;
    c.globalAlpha=fade;c.strokeStyle=col;c.lineWidth=2.6*fade+1;
    c.beginPath();
    for(let i=0;i<28;i++){const an=i/28*Math.PI*2+(h%7)*.1,sp=(70+((h>>>i%13)&31))/r,gy=26*b*b,b0=Math.max(0,b-.12);
      c.moveTo(x+Math.cos(an)*sp*b0*1.4,hy+Math.sin(an)*sp*b0*1.4+26*b0*b0);c.lineTo(x+Math.cos(an)*sp*b*1.4,hy+Math.sin(an)*sp*b*1.4+gy);}
    c.stroke();c.fillStyle=col;
    for(let i=0;i<28;i+=2){const an=i/28*Math.PI*2+(h%7)*.1,sp=(70+((h>>>i%13)&31))/r;c.fillRect(x+Math.cos(an)*sp*b*1.4-1.6,hy+Math.sin(an)*sp*b*1.4+26*b*b-1.6,3.2,3.2);}
    if(b<.3){c.globalAlpha=(1-b/.3)*.6;c.fillStyle=dark?'#ffffff':'#fff3b0';c.beginPath();c.arc(x,hy,18,0,Math.PI*2);c.fill();}
  }
  c.restore();c.globalAlpha=1;
}
/** 💐 The bouquet (walk.js flies it from the couple to whoever catches it). */
export function bouquet(c,x,y,rot){
  c.save();c.translate(x,y);c.rotate(rot);c.scale(1.45,1.45);   // big enough to follow in the air on a phone
  c.fillStyle='#7cae79';c.beginPath();c.moveTo(-4,4);c.lineTo(0,20);c.lineTo(4,4);c.closePath();c.fill();
  c.fillStyle='#fff3e8';c.fillRect(-4,8,8,4);
  for(const [dx,dy,col] of [[-7,-2,'#f28c9e'],[7,-2,'#f6a8bd'],[0,-8,'#fbe3ea'],[-3,3,'#ff6f91'],[4,3,'#fff'],[0,-1,'#f28c9e']]){
    c.fillStyle=col;c.beginPath();c.arc(dx,dy,5.2,0,Math.PI*2);c.fill();}
  c.restore();
}
/** A little burst of confetti at (x, y), age in seconds (the bouquet's catch). */
export function burst(c,x,y,age,seed){
  if(age<0||age>1.6)return;
  for(let i=0;i<26;i++){const h=hash(seed*31+i),an=(h%628)/100,sp=50+(h>>>9)%60;
    c.globalAlpha=Math.max(0,1-age/1.6);c.fillStyle=PALETTE[i%PALETTE.length];
    c.fillRect(x+Math.cos(an)*sp*age-2,y+Math.sin(an)*sp*age+40*age*age-2,4,5);}
  c.globalAlpha=1;
}
/** Name tags and speech bubbles in screen units (walk.js passes its own tag and bubble painters). */
export function talk(c,{w,s,sec,sx,sy,tag,bubble,dark,bt}){
  const fit=x=>Math.max(sx(0)+92,Math.min(sx(600)-92,x));   // bubbles stay on the screen
  const say=(p,x,y,line)=>{const t=sy(y-top(p))-2;tag(c,sx(x),t,p.name,p.role,false,dark);
    if(line){const age=s-line.t0,alpha=Math.max(0,Math.min(1,age*3,(SAY-age)*2));if(alpha>0)bubble(c,fit(sx(x)),t-28,line.text,alpha,dark);}};
  const mc=mcLine(w,s),ch=chatter(w,s);
  say(MC,MC.x,MC.y,mc);
  NB.forEach((n,i)=>say(n,n.x,n.y,ch?.who==='nb'&&ch.i===i?ch:null));
  KIDS.forEach((k,i)=>{const p=kidPos(i,s,sec);if(p)say(k,p[0],p[1]-p[2],ch?.who==='kid'&&ch.i===i?ch:null);});
  const l=lionState(s,{bt});
  if(l){const u=l.u,line=u%14<6?'Tùng tùng cắc! Tùng dinh dinh! 🦁':l.o.env&&u%14<10?'Lân bắt được lì xì rồi! 🧧':null;
    if(line)bubble(c,fit(sx(l.x)),sy(l.y-145),line,1,dark);}
}
/** Something is moving: the scene keeps drawing. */
export const lively=s=>s>-305&&s<605;

/* ---- the music (recorded tracks, Web Audio; the party clock picks the track and the place in it) ---- */
const VOL=.5;
const M={on:false,timer:0,ctx:null,out:null,clock:null,end:600,cur:null,loading:'',bytes:new Map(),bufs:new Map()};
const url=f=>globalThis.__mnlBoot?.asset?.(`/music/${f}.mp3`)||`/music/${f}.mp3`;
/** Decode at 32 kHz mono (the files are 32 kHz mono): ~4 MB a minute of music instead of ~11 at 48 kHz stereo. */
function decode(data,ctx){
  const OAC=window.OfflineAudioContext||window.webkitOfflineAudioContext;
  let dec=ctx;try{if(OAC)dec=new OAC(1,1,32000);}catch{/* rate not supported: the page context */}
  return new Promise((ok,fail)=>{const p=dec.decodeAudioData(data,ok,fail);p?.catch?.(()=>{/* fail() had it */});});
}
function bytesOf(k){let p=M.bytes.get(k);if(!p){p=fetch(url(TRACKS[k].f)).then(r=>{if(!r.ok)throw new Error(r.status);return r.arrayBuffer();});M.bytes.set(k,p);p.catch(()=>M.bytes.delete(k));}return p;}
function bufferOf(k){let p=M.bufs.get(k);if(!p){p=bytesOf(k).then(b=>decode(b.slice(0),M.ctx));M.bufs.set(k,p);p.catch(()=>M.bufs.delete(k));}return p;}
function stopCur(f=.4){
  const cur=M.cur;M.cur=null;if(!cur||!M.ctx)return;
  const t=M.ctx.currentTime;try{cur.g.gain.cancelScheduledValues(t);cur.g.gain.setValueAtTime(cur.g.gain.value,t);cur.g.gain.linearRampToValueAtTime(0,t+f);cur.src.stop(t+f+.05);}catch{/* stopped */}
}
function startAt(k,buf,pos){
  const c=M.ctx,T=TRACKS[k],t=c.currentTime+.06,d=buf.duration,p=T.once?Math.min(pos+.06,d-.01):(((pos+.06)%d)+d)%d;
  const g=c.createGain(),src=c.createBufferSource();src.buffer=buf;src.loop=!T.once;
  g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(1,t+.45);src.connect(g).connect(M.out);src.start(t,Math.max(0,p));
  stopCur(.45);M.cur={k,src,g,d,t0:t,p0:p};
}
function pump(){
  if(!M.on||!M.ctx)return;
  const s=M.clock();
  if(s<-300||s>=M.end){stopCur();return;}
  const [k,pos]=track(s),T=TRACKS[k],next=track(s+12)[0];
  for(const key of [...M.bufs.keys()])if(key!==k&&key!==next&&key!==M.cur?.k)M.bufs.delete(key);   // a decoded track is MBs: keep two
  if(next!==k)bufferOf(next).catch(()=>{/* later */});
  if(T.once&&pos>=T.len-.3){if(M.cur?.k===k)stopCur(1);return;}
  const cur=M.cur;
  if(cur?.k===k){   // still in step with the party clock? (a phone that slept, a clock correction)
    const el=M.ctx.currentTime-cur.t0+cur.p0,play=T.once?el:el%cur.d,want=T.once?pos:((pos%cur.d)+cur.d)%cur.d;
    let off=Math.abs(play-want);if(!T.once)off=Math.min(off,cur.d-off);
    if(off<.35)return;
  }
  if(M.loading===k)return;
  M.loading=k;
  bufferOf(k).then(buf=>{M.loading='';if(!M.on)return;const [k2,pos2]=track(M.clock());if(k2===k)startAt(k,buf,pos2);}).catch(()=>{M.loading='';});
}
/** Music on or off; clock() → the party second now; len: the party's length (s). Off when the party ends or the
 * scene closes. While it plays, the game's background music steps aside (audio.js duck). */
export function music(on,clock,len){
  if(on&&!M.on){
    const c=audioContext();if(!c)return;
    M.ctx=c;M.clock=clock;M.end=len||600;M.on=true;M.loading='';
    M.out=c.createGain();M.out.gain.value=VOL;M.out.connect(c.destination);
    wantAudio('wedding',true);duck('wedding',true);M.timer=setInterval(pump,250);pump();
  }else if(!on&&M.on){
    M.on=false;clearInterval(M.timer);wantAudio('wedding',false);duck('wedding',false);stopCur(.3);
    const out=M.out;M.out=null;M.bufs.clear();M.loading='';if(out)setTimeout(()=>{try{out.disconnect();}catch{/* gone */}},500);
  }else if(on){M.clock=clock;if(len)M.end=len;}
}
export const musicOn=()=>M.on;
