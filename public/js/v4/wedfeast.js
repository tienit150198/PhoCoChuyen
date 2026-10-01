/** 💍 The wedding party's show (live/wedding.py, drawn by ./walk.js in the 'wedding' scene): the MC's programme, the
 * neighbours at the tables, the kids and teens running about with their sayings, the lion dance, twinkling lights and
 * the wedding music. Everything follows the party clock (seconds from the start, `s`; negative while guests gather),
 * and the lines are picked from the wedding id and the clock, so every guest sees the same thing at the same moment.
 * No server frames: the show is the same for everyone without a single extra message.
 * The music is synthesised here (Web Audio, no recordings): Wagner's Bridal Chorus (1850, public domain) as the couple
 * comes in, then a cheerful pentatonic tune written for the game, and drums under the lion dance. */
import {audioContext,wantAudio} from '../audio.js';
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
const KID_TIMES=[[-200,-130],[50,125],[170,260],[330,400],[470,560]];   // when the kids run in (party seconds)
const LION=[[55,110,false],[320,375,true]];                            // [from, to, right to left]
const SAY=5.5;                                                          // seconds a line stays up

const MC_LINES=[
  [-290,'Kính mời quý khách vào chỗ, tiệc sắp bắt đầu rồi ạ! 💐'],
  [-180,'Cô chú anh chị cứ tự nhiên dùng trà bánh nha, còn ít phút nữa thôi!'],
  [-60,'Một phút nữa thôi! Ai chưa có chỗ thì nhanh chân nào 🏃'],
  [0,'Kính thưa quý vị! Chào mừng đến lễ cưới của {a} và {b} 💍'],
  [8,'Xin một tràng pháo tay thật lớn cho đôi uyên ương nào! 👏👏👏'],
  [50,'Đoàn lân về chúc mừng hai họ rồi! Tùng tùng cắc! 🦁'],
  [120,'Khai tiệc! Mời cả nhà nâng ly: Một, hai, ba… dzô! 🥂'],
  [150,'Cỗ hôm nay có gà luộc, nem rán, tôm hấp, canh măng… cả nhà ăn thật no nha!'],
  [230,'Mời cô dâu chú rể cắt bánh cưới và rót tháp ly! 🎂'],
  [290,'Chúc {a} và {b} trăm năm hạnh phúc, đầu bạc răng long! 💕'],
  [318,'Đoàn lân lại tới kìa! Lì xì cho lân lấy hên nào! 🧧'],
  [420,'Ai có tiết mục văn nghệ thì lên sân khấu luôn nha, micro sẵn rồi! 🎤'],
  [500,'Cảm ơn cô chú anh chị đã đến chung vui cùng hai bạn!'],
  [560,'Tiệc sắp tàn rồi, cả nhà chụp chung tấm ảnh nào! 📸'],
  [592,'Chúc mọi người về nhà bình an. Hẹn gặp ở đám cưới sau nha! 👋'],
];
const NB_LINES=[
  'Chúc hai cháu trăm năm hạnh phúc, sớm có tin vui nha!','Cỗ hôm nay ngon ghê, nem rán giòn rụm luôn!',
  'Hồi xưa bác cưới có năm mâm thôi, giờ linh đình quá!','Cô dâu chú rể đẹp đôi quá trời đất ơi!',
  'Bao giờ có cháu bế đây hai đứa? 👶','Nhạc vui quá, bà đứng dậy nhảy một bài nè 💃',
  'Thằng cu nhà tui cũng sắp cưới rồi đó, nhớ qua ăn cỗ nha!','Ai gắp giùm tui miếng gà với, xa quá với không tới 🍗',
  'Đám cưới này đông vui nhất phố từ đầu năm tới giờ!','Lân múa đẹp quá, năm nay chắc làm ăn phát đạt!',
  'Ăn từ từ thôi tụi nhỏ, cỗ còn nhiều lắm!','Một, hai, ba, dzô! Chúc mừng hai đứa nha! 🍻',
  'Nhìn {a} với {b} là biết trời sinh một cặp rồi!','Canh măng này ai nấu mà ngọt nước dữ vậy!',
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
];

/* ---- the clock and the picks (the same on every guest's screen) ---- */
const hash=n=>{n=Math.imul(n^n>>>16,0x45d9f3b);n=Math.imul(n^n>>>16,0x45d9f3b);return (n^n>>>16)>>>0;};
const fill=(text,w)=>text.replaceAll('{a}',w.a).replaceAll('{b}',w.b);
const kidsOn=s=>KID_TIMES.some(([a,b])=>s>=a&&s<b);
const lionAt=s=>LION.find(([a,b])=>s>=a&&s<b)||null;
/** Who speaks in this slot of 7 seconds: a neighbour, or a kid while the kids are about. */
function chatter(w,s){
  if(s<-300||s>=600)return null;
  const slot=Math.floor(s/7),from=slot*7;if(s-from>SAY)return null;
  const h=hash(w.id*7919+slot+1000);
  if(MC_LINES.some(([t])=>Math.abs(t-from)<4))return null;   // the MC has the floor
  const kid=kidsOn(from)&&h%5<3;
  if(kid){const i=h%KIDS.length;return {who:'kid',i,text:KID_LINES[(h>>>3)%KID_LINES.length],t0:from};}
  if(h%4===3)return null;                                      // a quiet moment now and then
  return {who:'nb',i:h%NB.length,text:fill(NB_LINES[(h>>>3)%NB_LINES.length],w),t0:from};
}
function mcLine(w,s){for(const [t,text] of MC_LINES)if(s>=t&&s<t+SAY+1)return {text:fill(text,w),t0:t};return null;}
/** A kid's spot: running a loop around the lawn while the kids are about, in from the gate and out again. */
function kidPos(i,s,sec){
  const win=KID_TIMES.find(([a,b])=>s>=a&&s<b);if(!win)return null;
  const [a,b]=win,f=Math.min(1,(s-a)/4,(b-s)/4),an=s*.42+i*Math.PI/2;
  const x=300+Math.cos(an)*(150+i*18),y=600+Math.sin(an)*(115-i*8);
  return [300+(x-300)*f,860+(y-860)*f,Math.abs(Math.sin(sec*9+i))*4];
}

/* ---- drawing (world units: the 600 × 900 scene) ---- */
const PALETTE=['#ff5d73','#ffd166','#06d6a0','#4cc9f0','#f78fb3'];
function bulbs(c,pts,sec,dark,phase){
  pts.forEach(([x,y],i)=>{
    const col=PALETTE[(i+Math.floor(sec*2.5+phase))%PALETTE.length],tw=.55+.45*Math.sin(sec*5+i*1.7+phase);
    if(dark){const g=c.createRadialGradient(x,y,0,x,y,14);g.addColorStop(0,col+'aa');g.addColorStop(1,col+'00');c.fillStyle=g;c.fillRect(x-14,y-14,28,28);}
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
/** Under and among the guests: the lights, the MC, the neighbours, the kids. */
export function ground(c,fx){
  const {s,sec,dark}=fx;
  STRINGS.forEach((pts,k)=>{c.strokeStyle=dark?'#ffffff33':'#5a4a3a40';c.lineWidth=1;c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke();bulbs(c,pts,sec,dark,k*1.3);});
  figure(c,MC,MC.x,MC.y,Math.abs(Math.sin(sec*3))*1.5,fx);
  c.fillStyle='#3a3a3a';c.fillRect(MC.x+11,MC.y-40,3,12);c.fillStyle='#777';c.beginPath();c.arc(MC.x+12.5,MC.y-42,4,0,Math.PI*2);c.fill();   // the microphone
  NB.forEach((n,i)=>figure(c,n,n.x,n.y,Math.max(0,Math.sin(sec*2+i))*1.2,fx));
  KIDS.forEach((k,i)=>{const p=kidPos(i,s,sec);if(p)figure(c,k,p[0],p[1],p[2],fx);});
}
/** Over the guests: the lion dance. */
export function over(c,{s,sec}){
  const l=lionAt(s);if(!l)return;
  const [a,b,rtl]=l,f=(s-a)/(b-a),x=rtl?690-780*f:-90+780*f,y=578+Math.sin(sec*2.2)*10;
  paintLion(c,x,y,sec,rtl);
}
/** Name tags and speech bubbles in screen units (walk.js passes its own tag and bubble painters). */
export function talk(c,{w,s,sec,sx,sy,tag,bubble,dark}){
  const fit=x=>Math.max(sx(0)+92,Math.min(sx(600)-92,x));   // bubbles stay on the screen
  const say=(p,x,y,line)=>{const t=sy(y-top(p))-2;tag(c,sx(x),t,p.name,p.role,false,dark);
    if(line){const age=s-line.t0,alpha=Math.max(0,Math.min(1,age*3,(SAY-age)*2));if(alpha>0)bubble(c,fit(sx(x)),t-28,line.text,alpha,dark);}};
  const mc=mcLine(w,s),ch=chatter(w,s);
  say(MC,MC.x,MC.y,mc);
  NB.forEach((n,i)=>say(n,n.x,n.y,ch?.who==='nb'&&ch.i===i?ch:null));
  KIDS.forEach((k,i)=>{const p=kidPos(i,s,sec);if(p)say(k,p[0],p[1]-p[2],ch?.who==='kid'&&ch.i===i?ch:null);});
  const l=lionAt(s);
  if(l){const [a,b,rtl]=l,f=(s-a)/(b-a),x=rtl?690-780*f:-90+780*f;bubble(c,fit(sx(x)),sy(540),'Tùng tùng cắc! Tùng dinh dinh! 🦁',1,dark);}
}
/** Something is moving: the scene keeps drawing. */
export const lively=s=>s>-305&&s<605;

/* ---- the music (Web Audio, scheduled a little ahead; the party clock picks the section) ---- */
const hz=m=>440*2**((m-69)/12);
// Wagner, Bridal Chorus (Lohengrin, 1850; public domain): [midi, beats]
const MARCH=[[67,1],[72,.75],[72,.25],[72,2],[67,1],[74,.75],[71,.25],[72,2],[67,1],[72,.75],[77,.25],[77,1.5],[76,.5],[74,.75],[72,.25],[71,.75],[72,.25],[74,2],
  [67,1],[72,.75],[72,.25],[72,2],[67,1],[74,.75],[71,.25],[72,2],[67,1],[72,.75],[77,.25],[76,1],[74,.75],[72,.25],[71,1],[72,3]];
// A cheerful tune written for the game (C major pentatonic, two bars of eighths) and its oom-pah bass.
const TUNE=[72,76,79,76,74,72,74,76,79,81,79,76,74,72,69,72,76,79,81,84,81,79,76,74,72,74,76,72,69,67,69,72];
const BASS=[48,55,52,55,45,52,48,55];
const DRUM='T.T.C.TCT.TTC.C.';   // tùng tùng cắc …
const M={on:false,timer:0,ctx:null,out:null,next:0,i:0,sec:'',clock:null};
function tone(f,t,d,type,v){const c=M.ctx,o=c.createOscillator(),g=c.createGain();o.type=type;o.frequency.value=f;
  g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(v,t+.015);g.gain.exponentialRampToValueAtTime(.0008,t+d);o.connect(g).connect(M.out);o.start(t);o.stop(t+d+.05);}
function hit(t,low){const c=M.ctx;
  if(low){const o=c.createOscillator(),g=c.createGain();o.frequency.setValueAtTime(130,t);o.frequency.exponentialRampToValueAtTime(48,t+.22);
    g.gain.setValueAtTime(.9,t);g.gain.exponentialRampToValueAtTime(.001,t+.3);o.connect(g).connect(M.out);o.start(t);o.stop(t+.32);return;}
  const n=c.createBufferSource(),b=c.createBuffer(1,Math.floor(c.sampleRate*.12),c.sampleRate),d=b.getChannelData(0);
  for(let i=0;i<d.length;i++)d[i]=(Math.random()*2-1)*(1-i/d.length)**3;
  const f=c.createBiquadFilter(),g=c.createGain();f.type='highpass';f.frequency.value=2500;g.gain.value=.55;n.buffer=b;n.connect(f).connect(g).connect(M.out);n.start(t);}
function section(s){if(lionAt(s))return 'lion';if(s>=0&&s<36)return 'march';return s>=-300&&s<600?'tune':'';}
function pump(){
  const c=M.ctx;if(!c||!M.on)return;
  if(M.next<c.currentTime)M.next=c.currentTime+.05;
  while(M.next<c.currentTime+.35){
    const s=M.clock()+(M.next-c.currentTime),sec=section(s);
    if(sec!==M.sec){M.sec=sec;M.i=0;}
    if(sec==='march'){const [m,b]=MARCH[M.i%MARCH.length],d=b*.62;tone(hz(m),M.next,d*.95,'triangle',.32);tone(hz(m-12),M.next,d*.9,'sine',.12);M.next+=d;M.i++;}
    else if(sec==='tune'){const i=M.i%TUNE.length;tone(hz(TUNE[i]),M.next,.24,'square',.07);tone(hz(TUNE[i]),M.next,.3,'triangle',.18);
      if(i%2===0)tone(hz(BASS[(i/2|0)%BASS.length]),M.next,.28,'triangle',.22);M.next+=.24;M.i++;}
    else if(sec==='lion'){const ch=DRUM[M.i%DRUM.length];if(ch!=='.')hit(M.next,ch==='T');if(M.i%8===0)tone(hz(84),M.next,.18,'square',.05);M.next+=.17;M.i++;}
    else M.next+=.25;
  }
}
/** Music on or off; clock() → the party second now. Off when the party ends or the scene closes. */
export function music(on,clock){
  if(on&&!M.on){
    const c=audioContext();if(!c)return;
    M.ctx=c;M.clock=clock;M.on=true;M.sec='';M.next=0;
    M.out=c.createGain();M.out.gain.value=.16;M.out.connect(c.destination);
    wantAudio('wedding',true);M.timer=setInterval(pump,90);pump();
  }else if(!on&&M.on){
    M.on=false;clearInterval(M.timer);wantAudio('wedding',false);
    const out=M.out;M.out=null;if(out){try{out.gain.setTargetAtTime(0,M.ctx.currentTime,.08);setTimeout(()=>out.disconnect(),400);}catch{/* closed */}}
  }else if(on)M.clock=clock;
}
export const musicOn=()=>M.on;
