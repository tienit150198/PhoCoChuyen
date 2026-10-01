/* 🎓 Giấy chứng nhận (1.3): the diploma a player receives for every certificate they pass, and the
 * souvenir photo of their character holding it at a little "Lễ trao chứng chỉ".
 *
 * Owner (02/10): "thi xong có chứng chỉ thì nên cấp cho người ta chứng chỉ thiệt, thấy được luôn nhé"
 * and "chụp ảnh lưu niệm (lưu trên máy) được nha".
 *
 * Data-driven: any group in content.journey.certs.groups (game/certificate_content.py GROUPS) that the
 * player holds (journey.certificates[id].earned_day) gets a diploma, old passes included. Nothing new is
 * stored for it: the number comes from the server (journey.cert_serials, game/certificates.serial(),
 * derived from the save), the real date from the optional `earned_on` (passes from 1.3 on; older ones
 * print the life day only), the name is the player's current name.
 *
 * The issuer is the game's own fictional "Trung tâm Đào tạo Nghề Phố Có Chuyện": no real ministry,
 * school, emblem or state seal is imitated, and the paper says it is an in-game certificate.
 *
 *   diplomaSVG(d)          the paper (inline SVG, 1000×1414, light whatever the theme)
 *   drawPhoto(c,W,H,d,img) the souvenir photo on a canvas (character from v4/look.js, current outfit)
 *   openDiploma(env,id,{reveal})  the dialog (reveal: right after passing, with confetti)
 *   diplomaAction(...)     jrCertDip* actions (routed by v4/certificates.js certAction)
 * Downloads: PNG through a canvas; on a phone the Web Share sheet with the file when it can, on iOS
 * without it the image is shown to long-press and save. "Lưu vào Kỷ niệm" stores a small 3:2 copy of the
 * photo with the existing `photo` command (the current workplace's album). */
import {escapeHTML as esc} from '../icons.js';
import {language,t} from './i18n.js';
import {lookOf,figureOf,paintPlayer,CANVAS} from './look.js';
import {certCss} from './certificates.js';

const PW=1000,PH=1414;
const SERIF=`'Times New Roman','Noto Serif','Liberation Serif','DejaVu Serif',Georgia,serif`;
const SANS=`'Be Vietnam Pro','Segoe UI',Roboto,'Helvetica Neue',Arial,'Noto Sans',sans-serif`;
const INK='#1c2b4a',WINE='#7d1d2a',GOLD='#b08a3a',MUTED='#6d5e4b',SEAL='#c4161c';
const DIRECTOR='Trần Bảo Ngọc';
// Fictional teachers of the centre; each certificate gets one (stable per id), any new group included.
const TEACHERS=['Phạm Quốc Hưng','Lâm Thu Hà','Đỗ Thanh Tâm','Nguyễn Hoài An','Võ Minh Châu','Hồ Gia Bảo','Lê Ngọc Diệp','Trịnh Khánh Linh','Mai Đức Toàn','Đặng Mỹ Duyên'];

/* ------------------------------------------------------------------ words (the paper and the photo are
 * images: their words are picked here by language, not by the page translator) */
const W_=en=>en?{
  org:'PHỐ CÓ CHUYỆN VOCATIONAL TRAINING CENTRE',with:'In partnership with',title:'CERTIFICATE',title2:'OF ACHIEVEMENT',
  certify:'This is to certify that',done:'has completed the course and passed the vocational examination',field:'Field',
  score:'EXAM SCORE',grade:'GRADE',day:'LIFE DAY',valid:'Recognised when applying at',teacher:'COURSE INSTRUCTOR',director:'CENTRE DIRECTOR',
  serial:'Certificate no.',game:'Phố Có Chuyện · a job-life simulation game',note1:'An in-game certificate,',note2:'not valid in real life.',
  seal:'PHỐ CÓ CHUYỆN • VOCATIONAL TRAINING CENTRE •',micro:'PHỐ CÓ CHUYỆN • VOCATIONAL TRAINING CENTRE • ',
  ceremony:'CERTIFICATE CEREMONY',centre:'Phố Có Chuyện Vocational Training Centre',lifeDay:'Life day',gradeOf:'Grade',
}:{
  org:'TRUNG TÂM ĐÀO TẠO NGHỀ PHỐ CÓ CHUYỆN',with:'Đơn vị đào tạo',title:'GIẤY CHỨNG NHẬN',title2:'',
  certify:'Chứng nhận',done:'đã hoàn thành khóa học và đạt kỳ thi sát hạch nghề',field:'Ngành',
  score:'ĐIỂM THI',grade:'XẾP LOẠI',day:'NGÀY SỐNG',valid:'Có giá trị khi ứng tuyển tại',teacher:'GIẢNG VIÊN HƯỚNG DẪN',director:'GIÁM ĐỐC TRUNG TÂM',
  serial:'Số hiệu',game:'Phố Có Chuyện · trò chơi mô phỏng nghề',note1:'Chứng chỉ trong trò chơi,',note2:'không có giá trị pháp lý ngoài đời thực.',
  seal:'TRUNG TÂM ĐÀO TẠO NGHỀ • PHỐ CÓ CHUYỆN •',micro:'PHỐ CÓ CHUYỆN • TRUNG TÂM ĐÀO TẠO NGHỀ • ',
  ceremony:'LỄ TRAO CHỨNG CHỈ',centre:'Trung tâm Đào tạo Nghề Phố Có Chuyện',lifeDay:'Ngày sống',gradeOf:'Xếp loại',
};
/** Xuất sắc / Giỏi / Khá / Đạt from the best exam score (0–100). */
export function gradeOf(score,en=false){
  const i=score>=90?0:score>=80?1:score>=70?2:3;
  return (en?['Excellent','Very good','Good','Pass']:['Xuất sắc','Giỏi','Khá','Đạt'])[i];
}
const MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
/** 'YYYY-MM-DD' → {long:'ngày 02 tháng 10 năm 2026' | '2 October 2026', short:'02/10/2026' | '2 Oct 2026'} */
function dateWords(iso,en){
  const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(iso||'');if(!m)return null;
  const [,y,mo,d]=m;
  return en?{long:`${Number(d)} ${MONTHS[mo-1]} ${y}`,short:`${Number(d)} ${MONTHS[mo-1].slice(0,3)} ${y}`}
    :{long:`ngày ${d} tháng ${mo} năm ${y}`,short:`${d}/${mo}/${y}`};
}
const fnv=s=>{let h=0x811c9dc5;for(const ch of String(s)){h^=ch.codePointAt(0);h=Math.imul(h,16777619)>>>0;}return h>>>0;};
const rng=seed=>()=>{seed=seed+0x6D2B79F5|0;let x=Math.imul(seed^seed>>>15,1|seed);x=x+Math.imul(x^x>>>7,61|x)^x;return ((x^x>>>14)>>>0)/4294967296;};
const n1=v=>Math.round(v*10)/10;
const tr=(s,en)=>en?t(s):s;

/** Everything printed on a diploma, from the save. null when the player does not hold it. */
export function diplomaData(api,gid){
  const k=api?.content?.journey?.certs,J=api?.state?.journey,g=k?.groups?.find(x=>x.id===gid),rec=J?.certificates?.[gid];
  if(!g||!rec||rec.earned_day==null)return null;
  const en=language()==='en';
  const own=String(api.state.name||'').trim(),acct=api.account?.display;
  const name=own&&!(own==='Mây'&&acct)?own:(acct||own||(en?'You':'Bạn'));
  const places=(g.careers||[]).filter(cid=>api.state.careers?.[cid]).map(cid=>{const m=(api.content.catalogue||[]).find(x=>x.id===cid);return tr(m?(m.place||m.short):cid,en);});
  const code=(p=>(p.length>1?p.map(x=>x[0]).join(''):gid.slice(0,3)).toUpperCase())(gid.split('_').filter(Boolean));
  const serial=J.cert_serials?.[gid]||`PCC-${code}-${(fnv(`${gid}|${rec.earned_day}`)%887503681).toString(36).toUpperCase().padStart(6,'0').slice(-6)}`;
  return {gid,en,name,serial,emoji:g.emoji,certName:tr(g.name,en),field:tr(g.short,en),
    issuer:tr(String(g.issuer||'').replace(/\s*\((?:lớp\s+)?giả lập\)\s*$/u,''),en),
    score:Number(rec.best)||0,grade:gradeOf(Number(rec.best)||0,en),day:rec.earned_day,on:rec.earned_on||null,
    teacher:TEACHERS[fnv(gid)%TEACHERS.length],director:DIRECTOR,places,
    look:lookOf(api.state),gender:J.gender};
}

/* ------------------------------------------------------------------ text measuring (fit long names) */
let meter=null;
function textWidth(text,font,spacing=0){
  try{meter??=document.createElement('canvas').getContext('2d');meter.font=font;return meter.measureText(text).width+spacing*[...text].length;}
  catch{const size=Number(/(\d+(?:\.\d+)?)px/.exec(font)?.[1]||16);return [...text].length*size*.55+spacing*[...text].length;}
}
/** The font size (≤ size) at which `text` fits in `max` px. */
function fit(text,size,max,{family=SERIF,weight=400,style='normal',spacing=0}={}){
  const w=textWidth(text,`${style} ${weight} ${size}px ${family}`,spacing);
  return w>max?Math.max(8,Math.floor(size*max/w*10)/10):size;
}
function txt(x,y,text,{size=20,family=SERIF,weight=400,style='normal',fill=INK,anchor='middle',spacing=0,max=0,extra=''}={}){
  const s=max?fit(text,size,max,{family,weight,style,spacing}):size;
  return `<text x="${n1(x)}" y="${n1(y)}" font-family="${family}" font-size="${s}" font-weight="${weight}" font-style="${style}" fill="${fill}" text-anchor="${anchor}"${spacing?` letter-spacing="${spacing}"`:''}${extra}>${esc(text)}</text>`;
}

/* ------------------------------------------------------------------ guilloche & ornaments */
/** A rosette: m copies of the polar wave r = r0 + a·sin(n·θ), each turned a little (banknote style). */
function rosette(r0,a,n,m,pts=240){
  let d='';
  for(let j=0;j<m;j++){
    const off=j*2*Math.PI/(n*m);
    for(let i=0;i<=pts;i++){const th=i*2*Math.PI/pts,r=r0+a*Math.sin(n*(th+off));d+=(i?'L':'M')+n1(r*Math.cos(th))+' '+n1(r*Math.sin(th));}
    d+='Z';
  }
  return d;
}
/** One tile of the border's woven band: phase-shifted sine waves both ways (seamless every `w`). */
function waveTile(w,h,k=5){
  let a='',b='';
  for(let j=0;j<k;j++){
    const ph=j*2*Math.PI/k;
    let p='',q='';
    for(let x=0;x<=w;x+=2){const s=Math.sin(2*Math.PI*x/w+ph);p+=(x?'L':'M')+x+' '+n1(h/2+(h/2-3)*s);q+=(x?'L':'M')+x+' '+n1(h/2-(h/2-3)*Math.sin(2*Math.PI*x/w*2+ph)*.55);}
    a+=p;b+=q;
  }
  return {a,b};
}
function laurel(side){
  // leaves along an arc on the left of the medallion (side -1) or the right (+1, mirrored)
  let out='';
  for(let i=0;i<9;i++){
    const th=(112+i*15.5)*Math.PI/180,r=68+(i%2?5:-5),x=r*Math.cos(th),y=r*Math.sin(th),rot=th*180/Math.PI+(i%2?60:120);
    out+=`<ellipse cx="${n1(x)}" cy="${n1(y)}" rx="10" ry="3.8" transform="rotate(${n1(rot)} ${n1(x)} ${n1(y)})"/>`;
  }
  return `<g transform="scale(${side} 1)" fill="${GOLD}"><path d="M-30 62A68 68 0 0 1-66-20" fill="none" stroke="${GOLD}" stroke-width="2"/>${out}</g>`;
}
/** The centre's mark: a roof over an open book (fictional; no star, no national symbol). */
function mark(c1='#f6ecd3',c2='#e2c072'){
  return `<path d="M0 22Q-12 13-27 15V-3Q-13-5 0 5Z" fill="${c1}" stroke="${c2}" stroke-width=".9"/><path d="M0 22Q12 13 27 15V-3Q13-5 0 5Z" fill="${c1}" stroke="${c2}" stroke-width=".9"/>`+
    `<path d="M-20-8L0-26L20-8" fill="none" stroke="${c2}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/><rect x="9" y="-24" width="5" height="9" fill="${c2}"/>`;
}
/** A handwritten-looking signature, stable for a seed (Catmull-Rom through a scribble). */
function signature(seed){
  const r=rng(seed);
  // a tall looped capital, then a run of small humps (now and then a tall stroke or a little loop), slanted
  const cap=34+r()*14;
  let pts=[[0,8],[5,-cap*.55],[13,-cap],[19,-cap*.72],[11,-8],[3,5],[15,-3]];
  let x=17;
  const n=4+Math.floor(r()*4);
  for(let i=0;i<n;i++){
    const tall=r()<.22,h=tall?22+r()*12:7+r()*9,step=9+r()*9;
    pts.push([x+step*.45,-h],[x+step,1+r()*4]);
    if(r()<.28)pts.push([x+step*.62,-h*.45],[x+step*1.08,3]);
    x+=step;
  }
  pts.push([x+9,-5],[x+20,-1]);
  const lean=.26+r()*.14;
  pts=pts.map(([px,py])=>[px-py*lean,py]);
  let d=`M${n1(pts[0][0])} ${n1(pts[0][1])}`;
  for(let i=0;i<pts.length-1;i++){
    const p0=pts[Math.max(0,i-1)],p1=pts[i],p2=pts[i+1],p3=pts[Math.min(pts.length-1,i+2)];
    d+=`C${n1(p1[0]+(p2[0]-p0[0])/6)} ${n1(p1[1]+(p2[1]-p0[1])/6)} ${n1(p2[0]-(p3[0]-p1[0])/6)} ${n1(p2[1]-(p3[1]-p1[1])/6)} ${n1(p2[0])} ${n1(p2[1])}`;
  }
  d+=`M${n1(-8)} ${n1(15+r()*4)}C${n1(x*.3)} ${n1(24+r()*6)} ${n1(x*.8)} ${n1(20+r()*6)} ${n1(x+28)} ${n1(-2-r()*6)}`;
  return {d,w:x+30};
}
/** A decorative QR-looking block (random modules: it encodes nothing). */
function pseudoQR(seed,x,y,cell=3,n=21){
  const r=rng(seed);let d='';
  const finder=(fx,fy)=>{d+=`M${fx} ${fy}h${7*cell}v${7*cell}h${-7*cell}ZM${fx+cell} ${fy+cell}v${5*cell}h${5*cell}v${-5*cell}ZM${fx+2*cell} ${fy+2*cell}h${3*cell}v${3*cell}h${-3*cell}Z`;};
  const inF=(i,j)=>(i<8&&j<8)||(i>n-9&&j<8)||(i<8&&j>n-9);
  for(let j=0;j<n;j++)for(let i=0;i<n;i++)if(!inF(i,j)&&r()<.48)d+=`M${x+i*cell} ${y+j*cell}h${cell}v${cell}h${-cell}Z`;
  finder(x,y);finder(x+(n-7)*cell,y);finder(x,y+(n-7)*cell);
  return `<rect x="${x-3}" y="${y-3}" width="${n*cell+6}" height="${n*cell+6}" fill="#fffdf6" stroke="#cdbb8e" stroke-width=".8"/><path d="${d}" fill="#2b2a28" fill-rule="evenodd"/>`;
}

/* ------------------------------------------------------------------ the paper */
/** The diploma as a standalone SVG document (also drawn on a canvas for the PNG). */
export function diplomaSVG(d){
  const w=W_(d.en),seed=fnv(d.serial);
  const tile=waveTile(64,44);
  const date=dateWords(d.on,d.en);
  const where=date?`Phố Có Chuyện, ${date.long}`:d.en?`Phố Có Chuyện, life day ${d.day}`:`Phố Có Chuyện, Ngày sống thứ ${d.day}`;
  const sigT=signature(fnv('t|'+d.teacher)),sigD=signature(fnv('d|'+d.director));
  const band=(x,y,len,rot)=>`<g transform="translate(${x} ${y})${rot?' rotate(90)':''}"><rect width="${len}" height="44" fill="#efe2c2"/><rect width="${len}" height="44" fill="url(#dp-wave)"/></g>`;
  const corner=(x,y)=>`<g transform="translate(${x} ${y})"><circle r="30" fill="#f7efda" stroke="${GOLD}" stroke-width="1.6"/><path d="${CORNER}" fill="none" stroke="#2e6b66" stroke-width=".7" opacity=".85"/><circle r="5" fill="${WINE}"/><circle r="30" fill="none" stroke="#8a6a25" stroke-width=".6" stroke-dasharray="1.5 2.5" transform="scale(.82)"/></g>`;
  const curl=(x,y,sx,sy)=>`<path transform="translate(${x} ${y}) scale(${sx} ${sy})" d="M0 34C0 12 12 0 34 0M8 40C8 18 18 8 40 8M0 34c6 0 10-4 10-10s-6-8-9-4M34 0c0 6-4 10-10 10s-8-6-4-9" fill="none" stroke="${GOLD}" stroke-width="1.6" stroke-linecap="round"/>`;
  const cell=(cx,label,value,fill=INK)=>`<rect x="${cx-92}" y="818" width="184" height="84" rx="9" fill="#fffaf0" fill-opacity=".72" stroke="${GOLD}" stroke-width="1.2"/><rect x="${cx-87}" y="823" width="174" height="74" rx="6" fill="none" stroke="${GOLD}" stroke-width=".5" stroke-dasharray="2 2"/>`+
    txt(cx,848,label,{size:13,family:SANS,weight:700,fill:'#8a7558',spacing:2,max:160})+txt(cx,888,value,{size:33,weight:700,fill,max:166});
  const valid=d.places.length?txt(500,952,`${w.valid}: ${d.places.join(', ')}`,{size:18,style:'italic',fill:MUTED,max:740}):'';
  const title=d.en?txt(500,418,w.title,{size:76,weight:700,fill:WINE,spacing:6,max:780,extra:' stroke="#c9a24f" stroke-width=".6"'})+txt(500,448,w.title2,{size:19,family:SANS,weight:700,fill:GOLD,spacing:9,max:600})
    :txt(500,432,w.title,{size:76,weight:700,fill:WINE,spacing:4,max:800,extra:' stroke="#c9a24f" stroke-width=".6"'});
  const star=[];for(let i=0;i<64;i++){const a=i*Math.PI/32,r=i%2?45.5:52;star.push(`${n1(r*Math.cos(a))},${n1(r*Math.sin(a))}`);}
  return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 ${PW} ${PH}" width="${PW}" height="${PH}" role="img" aria-label="${esc(`${w.title} · ${d.certName} · ${d.name}`)}">
<defs>
 <radialGradient id="dp-paper" cx="50%" cy="45%" r="75%"><stop offset="0" stop-color="#fffbf1"/><stop offset=".72" stop-color="#fbf3e0"/><stop offset="1" stop-color="#efdfbd"/></radialGradient>
 <linearGradient id="dp-gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f7e2a0"/><stop offset=".45" stop-color="#d5ab4c"/><stop offset=".7" stop-color="#f3d98e"/><stop offset="1" stop-color="#a87b25"/></linearGradient>
 <linearGradient id="dp-navy" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2d4878"/><stop offset="1" stop-color="#1a2b4d"/></linearGradient>
 <linearGradient id="dp-wine" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9b2a37"/><stop offset="1" stop-color="#6e1622"/></linearGradient>
 <pattern id="dp-wave" width="64" height="44" patternUnits="userSpaceOnUse"><path d="${tile.a}" fill="none" stroke="#2e6b66" stroke-width=".75" opacity=".7"/><path d="${tile.b}" fill="none" stroke="#8a2432" stroke-width=".6" opacity=".55"/></pattern>
 <pattern id="dp-hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><path d="M0 0V7" stroke="#b49d6c" stroke-width=".5" opacity=".16"/></pattern>
 <filter id="dp-tex" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".022 .03" numOctaves="3" seed="${seed%997}"/><feColorMatrix type="matrix" values="0 0 0 0 .45  0 0 0 0 .36  0 0 0 0 .2  .3 0 0 0 -.11"/></filter>
 <filter id="dp-ink" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="2" seed="${seed%89}" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2.4" result="d"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -3.4 0 0 0 2.75" result="m"/><feComposite in="d" in2="m" operator="in"/></filter>
 <path id="dp-arc" d="M-56 0A56 56 0 1 1 56 0A56 56 0 1 1-56 0"/>
</defs>
<rect width="${PW}" height="${PH}" fill="url(#dp-paper)"/>
<rect width="${PW}" height="${PH}" filter="url(#dp-tex)"/>
<rect x="100" y="100" width="${PW-200}" height="${PH-200}" fill="url(#dp-hatch)"/>
<g transform="translate(500 760)" opacity=".11" fill="none" stroke="#2e6b66" stroke-width=".9"><path d="${rosette(205,32,16,8)}"/><path d="${rosette(120,18,12,6,180)}" stroke="#8a2432"/></g>
<rect x="24" y="24" width="${PW-48}" height="${PH-48}" fill="none" stroke="url(#dp-gold)" stroke-width="5"/>
<rect x="34" y="34" width="${PW-68}" height="${PH-68}" fill="none" stroke="${INK}" stroke-width="1.2"/>
${band(40,40,PW-80)}${band(40,PH-84,PW-80)}${band(84,40,PH-80,true)}${band(PW-40,40,PH-80,true)}
<rect x="40" y="40" width="${PW-80}" height="${PH-80}" fill="none" stroke="${GOLD}" stroke-width="1"/>
<rect x="88" y="88" width="${PW-176}" height="${PH-176}" fill="none" stroke="${INK}" stroke-width="1.5"/>
<rect x="94" y="94" width="${PW-188}" height="${PH-188}" fill="none" stroke="${GOLD}" stroke-width="1"/>
${corner(62,62)}${corner(PW-62,62)}${corner(62,PH-62)}${corner(PW-62,PH-62)}
${curl(104,104,1,1)}${curl(PW-104,104,-1,1)}${curl(104,PH-104,1,-1)}${curl(PW-104,PH-104,-1,-1)}
${txt(500,114,w.micro.repeat(6),{size:7,family:SANS,weight:600,fill:'#a08a5f',extra:' textLength="700" lengthAdjust="spacingAndGlyphs"'})}
${txt(500,PH-106,w.micro.repeat(6),{size:7,family:SANS,weight:600,fill:'#a08a5f',extra:' textLength="700" lengthAdjust="spacingAndGlyphs"'})}
<g transform="translate(500 192)">${laurel(-1)}${laurel(1)}<circle r="52" fill="url(#dp-gold)"/><circle r="47" fill="url(#dp-navy)"/><circle r="42" fill="none" stroke="#e2c072" stroke-width=".9" stroke-dasharray="2 3"/>${mark()}<text y="36" font-family="${SANS}" font-size="8.5" font-weight="700" fill="#e2c072" text-anchor="middle" letter-spacing="2">PCC</text></g>
${txt(500,290,w.org,{size:22,family:SANS,weight:700,fill:INK,spacing:2.5,max:760})}
${d.issuer?txt(500,322,`${w.with}: ${d.issuer}`,{size:18,style:'italic',fill:MUTED,max:720}):''}
<g transform="translate(500 346)" fill="${GOLD}"><path d="M-170 0H-14M14 0H170" stroke="${GOLD}" stroke-width="1.2"/><path d="M0-7L7 0L0 7L-7 0Z"/><circle cx="-176" r="2.5"/><circle cx="176" r="2.5"/></g>
${title}
<g><path d="M150 478H206V534H150L168 506Z" fill="#5a111b"/><path d="M850 478H794V534H850L832 506Z" fill="#5a111b"/><path d="M180 520L206 534V520Z" fill="#3e0b12"/><path d="M820 520L794 534V520Z" fill="#3e0b12"/>
<rect x="180" y="464" width="640" height="56" fill="url(#dp-wine)"/><path d="M180 469H820M180 515H820" stroke="#d9b25a" stroke-width="1" opacity=".8"/>
${txt(500,502,d.certName,{size:30,style:'italic',weight:700,fill:'#fbf1d6',max:600})}</g>
${txt(500,586,w.certify,{size:25,style:'italic',fill:MUTED})}
${txt(500,664,d.name,{size:66,style:'italic',weight:700,fill:INK,max:760})}
<g transform="translate(500 690)"><path d="M-300 0H-16M16 0H300" stroke="${GOLD}" stroke-width="1.4"/><path d="M0-6L6 0L0 6L-6 0Z" fill="${GOLD}"/><path d="M-300 0c-14 0-18-10-10-14M300 0c14 0 18-10 10-14" fill="none" stroke="${GOLD}" stroke-width="1.2"/></g>
${txt(500,742,w.done,{size:23,fill:'#3d342b',max:760})}
<text x="500" y="784" font-family="${SERIF}" font-size="${fit(`${w.field}: ${d.field}`,24,700)}" fill="#3d342b" text-anchor="middle">${esc(w.field)}: <tspan font-weight="700" fill="${INK}">${esc(d.field)}</tspan></text>
${cell(300,w.score,`${d.score}/100`)}${cell(500,w.grade,d.grade,WINE)}${cell(700,w.day,String(d.day))}
${valid}
${txt(720,1012,where,{size:19,style:'italic',fill:'#3d342b',max:330})}
${txt(280,1052,w.teacher,{size:14,family:SANS,weight:700,fill:INK,spacing:1.5,max:250})}
${txt(720,1052,w.director,{size:14,family:SANS,weight:700,fill:INK,spacing:1.5,max:250})}
<path transform="translate(${n1(280-sigT.w*.6)} 1110) scale(1.2)" d="${sigT.d}" fill="none" stroke="#1f3f8f" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>
<g transform="translate(500 1122)"><path d="M-20 34L-34 92L-22 84L-11 94L-4 38Z" fill="url(#dp-wine)"/><path d="M20 34L34 92L22 84L11 94L4 38Z" fill="url(#dp-wine)"/><polygon points="${star.join(' ')}" fill="url(#dp-gold)" stroke="#a87b25" stroke-width=".8"/><circle r="40" fill="url(#dp-gold)" stroke="#9a7424" stroke-width="1.2"/><circle r="35" fill="none" stroke="#8a6a1e" stroke-width=".8" stroke-dasharray="1.5 2"/><g transform="translate(0 -2) scale(.8)">${mark('#fbeec8','#7a5a14')}</g></g>
<path transform="translate(${n1(720-sigD.w*.6)} 1110) scale(1.2)" d="${sigD.d}" fill="none" stroke="#1f3f8f" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>
<g transform="translate(664 1114) rotate(-13) scale(.86)" filter="url(#dp-ink)" opacity=".86"><g fill="none" stroke="${SEAL}"><circle r="68" stroke-width="4.5"/><circle r="63.5" stroke-width="1"/><circle r="47" stroke-width="2"/></g>
<text font-family="${SANS}" font-size="${d.en?10.2:11.4}" font-weight="700" fill="${SEAL}" letter-spacing=".6"><textPath href="#dp-arc" xlink:href="#dp-arc" textLength="345" lengthAdjust="spacingAndGlyphs">${esc(w.seal)}</textPath></text>
<g transform="translate(0 -9) scale(.62)">${mark('none',SEAL)}</g><text y="25" font-family="${SANS}" font-size="20" font-weight="800" fill="${SEAL}" text-anchor="middle" letter-spacing="2">PCC</text><path d="M-24 31H24" stroke="${SEAL}" stroke-width="1.4"/></g>
${txt(280,1198,d.teacher,{size:22,weight:700,fill:INK,max:250})}
${txt(720,1198,d.director,{size:22,weight:700,fill:INK,max:250})}
${pseudoQR(seed,116,1226)}
${txt(194,1246,`${w.serial}: ${d.serial}`,{size:16,family:SANS,weight:700,fill:INK,anchor:'start',max:330})}
${txt(194,1270,w.game,{size:12.5,family:SANS,fill:MUTED,anchor:'start',max:330})}
${txt(888,1246,w.note1,{size:14,style:'italic',fill:MUTED,anchor:'end',max:330})}
${txt(888,1268,w.note2,{size:14,style:'italic',fill:MUTED,anchor:'end',max:330})}
</svg>`;
}
const CORNER=rosette(19,7,10,5,160);

/* ------------------------------------------------------------------ images */
/** The paper as an <img> (for the canvas: PNG, the photo's frame). */
function paperImage(d){
  return new Promise((ok,fail)=>{
    const url=URL.createObjectURL(new Blob([diplomaSVG(d)],{type:'image/svg+xml;charset=utf-8'}));
    const img=new Image();
    img.onload=()=>{ok(img);setTimeout(()=>URL.revokeObjectURL(url),1000);};
    img.onerror=()=>{URL.revokeObjectURL(url);fail(new Error('diploma image'));};
    img.src=url;
  });
}
const toBlob=(cv,type='image/png',q)=>new Promise((ok,fail)=>cv.toBlob(b=>b?ok(b):fail(new Error('toBlob')),type,q));
async function paperPNG(img,scale=1.2){
  const cv=document.createElement('canvas');cv.width=Math.round(PW*scale);cv.height=Math.round(PH*scale);
  const c=cv.getContext('2d');c.imageSmoothingQuality='high';c.drawImage(img,0,0,cv.width,cv.height);
  return toBlob(cv);
}

/* ------------------------------------------------------------------ the souvenir photo */
function star4(c,x,y,r,col){c.save();c.translate(x,y);c.beginPath();for(let i=0;i<8;i++){const a=i*Math.PI/4,rr=i%2?r*.28:r;c.lineTo(rr*Math.cos(a-Math.PI/2),rr*Math.sin(a-Math.PI/2));}c.closePath();c.fillStyle=col;c.fill();c.restore();}
function ctext(c,s,x,y,{size,family=SANS,weight=700,style='normal',color=INK,max=0,align='center',spacing=0}){
  let px=size;c.font=`${style} ${weight} ${px}px ${family}`;
  if(max){const w=c.measureText(s).width+spacing*[...s].length;if(w>max){px=Math.max(8,size*max/w);c.font=`${style} ${weight} ${px}px ${family}`;}}
  try{c.letterSpacing=`${spacing}px`;}catch{}
  c.fillStyle=color;c.textAlign=align;c.textBaseline='middle';c.fillText(s,x,y);
  try{c.letterSpacing='0px';}catch{}
}
function flowerStand(c,x,y,s,r){
  c.save();c.translate(x,y);c.scale(s,s);
  c.strokeStyle='#8a5a33';c.lineWidth=5;c.lineCap='round';
  c.beginPath();c.moveTo(-26,10);c.lineTo(-40,200);c.moveTo(26,10);c.lineTo(40,200);c.moveTo(0,14);c.lineTo(0,204);c.stroke();
  c.lineWidth=3;c.beginPath();c.moveTo(-34,120);c.lineTo(34,120);c.stroke();
  // basket
  c.fillStyle='#c99a5b';c.beginPath();c.moveTo(-46,-6);c.lineTo(46,-6);c.lineTo(32,24);c.lineTo(-32,24);c.closePath();c.fill();
  c.strokeStyle='#a87a40';c.lineWidth=1.5;for(let i=-36;i<=36;i+=9){c.beginPath();c.moveTo(i,-6);c.lineTo(i*.72,24);c.stroke();}
  // leaves and blooms
  const leaf=(lx,ly,a,len)=>{c.save();c.translate(lx,ly);c.rotate(a);c.fillStyle='#5f9e6e';c.beginPath();c.ellipse(0,-len/2,len*.22,len/2,0,0,Math.PI*2);c.fill();c.restore();};
  for(let i=0;i<9;i++)leaf(-40+i*10,-6,(i-4)*.28,46+r()*26);
  const cols=['#f28fa8','#ffd36e','#ffffff','#f6a463','#e46f8f','#fbe3ef','#c77ddb'];
  for(let i=0;i<16;i++){
    const a=-Math.PI+i/15*Math.PI,rr=34+r()*30,bx=Math.cos(a)*rr*1.15,by=-14+Math.sin(a)*rr*.95,sz=9+r()*7;
    CANVAS.bloom(c,bx,by,sz,cols[Math.floor(r()*cols.length)]);
  }
  for(let i=0;i<5;i++)CANVAS.bloom(c,-28+i*14,-20-r()*14,10+r()*4,cols[i%cols.length]);
  // ribbon
  c.fillStyle='#c8453c';c.beginPath();c.moveTo(-10,24);c.lineTo(-22,62);c.lineTo(-12,58);c.lineTo(-4,66);c.lineTo(0,26);c.closePath();c.fill();
  c.beginPath();c.moveTo(10,24);c.lineTo(22,62);c.lineTo(12,58);c.lineTo(4,66);c.lineTo(0,26);c.closePath();c.fill();
  c.restore();
}
/** The player holding the framed diploma, with a mortarboard (origin at the feet, look.js units). */
function graduate(c,d,paper){
  const L={...d.look};if(L.acc==='non_la'||L.acc==='mu_len')L.acc='pk_khong';   // the cap replaces a hat
  const F=figureOf(L,d.gender);let hand=F.skin.hand;
  // The two hanging hands move onto the frame: the pen skips them here and draws them last.
  const pen={...CANVAS,E:(cv,x,y,rx,ry,fill)=>{if(rx===8&&ry===14&&Math.abs(x)===25&&y===-36){hand=fill;return;}CANVAS.E(cv,x,y,rx,ry,fill);}};
  paintPlayer(c,F,pen);
  const sleeve=F.topC||F.classic;
  CANVAS.L(c,-21,-46,-18,-30,sleeve,9);CANVAS.L(c,21,-46,18,-30,sleeve,9);
  // the frame
  const fw=34,fh=46,fx=-fw/2,fy=-48;
  c.save();c.shadowColor='rgba(40,25,10,.35)';c.shadowBlur=3;c.shadowOffsetY=1.5;CANVAS.R(c,fx,fy,fw,fh,'#6b4226',1.8);c.restore();
  CANVAS.R(c,fx+1.4,fy+1.4,fw-2.8,fh-2.8,'#d9b25a',1);
  if(paper){c.imageSmoothingQuality='high';c.drawImage(paper,fx+2.4,fy+2.4,fw-4.8,fh-4.8);}
  else CANVAS.R(c,fx+2.4,fy+2.4,fw-4.8,fh-4.8,'#fbf3e0',.5);
  c.fillStyle='rgba(255,255,255,.18)';c.beginPath();c.moveTo(fx+2.4,fy+2.4);c.lineTo(fx+14,fy+2.4);c.lineTo(fx+2.4,fy+20);c.closePath();c.fill();
  CANVAS.E(c,-17.5,-27,5.4,7,hand);CANVAS.E(c,17.5,-27,5.4,7,hand);
  // the mortarboard (mũ cử nhân)
  CANVAS.R(c,-25,-123,50,16,'#24242c',6);
  CANVAS.P(c,[[-48,-125],[0,-139],[48,-125],[0,-112]],'#2f2f3a');
  CANVAS.P(c,[[-48,-125],[0,-139],[0,-136],[-42,-125]],'#45455a');
  CANVAS.E(c,0,-125.5,3.2,2,'#d9b25a');
  CANVAS.L(c,0,-125.5,33,-121,'#e0b955',1.6);CANVAS.L(c,33,-121,35,-104,'#e0b955',1.6);
  CANVAS.R(c,32.4,-107,5.4,11,'#e8c25e',2);
}
/** The souvenir photo on a canvas W×H (portrait 4:5 to keep, or 3:2 for Kỷ niệm). */
export function drawPhoto(c,W,H,d,paper){
  const w=W_(d.en),port=H>W,r=rng(fnv(d.serial+'|photo'));
  const Lt=port?{band:210,floor:905,feet:1092,k:4.45,bx:70,by:64,bw:W-140,bh:850,t1:182,t1s:80,t2:250,t2s:32,t3:318,t3s:40,stand:[205,W-205],standY:690,standS:1.25,sag:30,flag:44}
    :{band:132,floor:515,feet:652,k:2.72,bx:54,by:34,bw:W-108,bh:490,t1:122,t1s:56,t2:166,t2s:23,t3:206,t3s:28,sag:16,flag:32,stand:[185,W-185],standY:418,standS:.95};
  const u=port?W/1080:H/800;
  // wall
  let g=c.createLinearGradient(0,0,0,H);g.addColorStop(0,'#fbe8cf');g.addColorStop(1,'#efcfa9');c.fillStyle=g;c.fillRect(0,0,W,H);
  c.fillStyle='rgba(255,255,255,.18)';for(let x=0;x<W;x+=36*u)c.fillRect(x,0,14*u,H);
  // backdrop board
  const {bx,by,bw,bh}=Lt;
  c.save();c.shadowColor='rgba(60,30,10,.28)';c.shadowBlur=24*u;c.shadowOffsetY=8*u;
  g=c.createLinearGradient(0,by,0,by+bh);g.addColorStop(0,'#2b5d66');g.addColorStop(1,'#173b44');c.fillStyle=g;c.beginPath();c.roundRect(bx,by,bw,bh,22*u);c.fill();c.restore();
  c.strokeStyle='#d9b25a';c.lineWidth=6*u;c.beginPath();c.roundRect(bx+10*u,by+10*u,bw-20*u,bh-20*u,16*u);c.stroke();
  c.lineWidth=1.5*u;c.beginPath();c.roundRect(bx+22*u,by+22*u,bw-44*u,bh-44*u,10*u);c.stroke();
  // faint rosettes on the board
  c.save();c.globalAlpha=.12;c.strokeStyle='#f3d98e';c.lineWidth=1.2*u;
  for(const [x,y,rr] of [[bx+bw*.14,by+bh*.62,110*u],[bx+bw*.86,by+bh*.62,110*u]]){c.save();c.translate(x,y);c.stroke(new Path2D(rosette(rr,rr*.16,12,6,200)));c.restore();}
  c.restore();
  // bunting
  const cols=['#e8a33d','#d9534f','#4f9d8f','#f2d16b','#8e6cc6','#ef8fb0'];
  const sag=y0=>x=>y0+Math.sin(Math.PI*x/W)*Lt.sag*u;
  const yb=sag(by-6*u);c.strokeStyle='#7a5a3a';c.lineWidth=2*u;c.beginPath();for(let x=0;x<=W;x+=8)c.lineTo(x,yb(x));c.stroke();
  for(let i=0,x=18*u;x<W-10*u;i++,x+=52*u){const y=yb(x);c.fillStyle=cols[i%cols.length];c.beginPath();c.moveTo(x,y);c.lineTo(x+40*u,yb(x+40*u));c.lineTo(x+20*u,y+Lt.flag*u);c.closePath();c.fill();}
  // title
  c.save();c.shadowColor='rgba(0,0,0,.35)';c.shadowBlur=6*u;c.shadowOffsetY=3*u;
  ctext(c,w.ceremony,W/2,Lt.t1,{size:Lt.t1s,family:SERIF,weight:700,color:'#f3d27a',max:bw-120*u,spacing:3*u});c.restore();
  ctext(c,w.centre,W/2,Lt.t2,{size:Lt.t2s,weight:600,color:'#f6ecd3',max:bw-140*u});
  c.fillStyle='#d9b25a';c.fillRect(W/2-160*u,(Lt.t2+Lt.t3)/2-1*u,320*u,2*u);
  ctext(c,`${d.emoji} ${d.field}`,W/2,Lt.t3,{size:Lt.t3s,family:SERIF,style:'italic',weight:700,color:'#ffffff',max:bw-160*u});
  // floor: a little stage and a red carpet
  g=c.createLinearGradient(0,Lt.floor,0,H);g.addColorStop(0,'#c8925e');g.addColorStop(1,'#9a6638');c.fillStyle=g;c.fillRect(0,Lt.floor,W,H-Lt.floor);
  c.strokeStyle='rgba(90,50,20,.25)';c.lineWidth=2*u;for(let y=Lt.floor+28*u;y<H;y+=34*u){c.beginPath();c.moveTo(0,y);c.lineTo(W,y);c.stroke();}
  c.fillStyle='#e7b98a';c.fillRect(0,Lt.floor,W,7*u);
  c.fillStyle='#b3262f';c.beginPath();c.moveTo(W/2-120*u,Lt.floor+7*u);c.lineTo(W/2+120*u,Lt.floor+7*u);c.lineTo(W/2+230*u,H);c.lineTo(W/2-230*u,H);c.closePath();c.fill();
  c.strokeStyle='#e0b955';c.lineWidth=3*u;c.beginPath();c.moveTo(W/2-112*u,Lt.floor+7*u);c.lineTo(W/2-214*u,H);c.moveTo(W/2+112*u,Lt.floor+7*u);c.lineTo(W/2+214*u,H);c.stroke();
  // spotlight
  const k=Lt.k*u,cx=W/2,fy=Lt.feet;
  g=c.createRadialGradient(cx,fy-70*k,10*u,cx,fy-70*k,120*k);g.addColorStop(0,'rgba(255,248,220,.55)');g.addColorStop(1,'rgba(255,248,220,0)');c.fillStyle=g;c.fillRect(0,0,W,H);
  // flower stands
  for(const x of Lt.stand)flowerStand(c,x,Lt.standY,Lt.standS*u,r);
  // confetti
  for(let i=0;i<46;i++){const x=r()*W,y=by+r()*(Lt.floor-by),s=(5+r()*7)*u;c.save();c.translate(x,y);c.rotate(r()*Math.PI);c.fillStyle=cols[i%cols.length];c.globalAlpha=.85;c.fillRect(-s/2,-s/4,s,s/2);c.restore();}
  // the graduate
  c.save();c.translate(cx,fy);c.scale(k,k);graduate(c,d,paper);c.restore();
  // sparkles
  for(let i=0;i<9;i++){const a=r()*Math.PI*2,rr=(60+r()*40)*k;star4(c,cx+Math.cos(a)*rr*.9,fy-80*k+Math.sin(a)*rr*.7,(8+r()*10)*u,i%3?'#fff6d5':'#f3d27a');}
  // caption band
  const top=H-Lt.band;
  c.fillStyle='rgba(255,252,246,.97)';c.fillRect(0,top,W,Lt.band);
  c.fillStyle='#d9b25a';c.fillRect(0,top,W,5*u);
  const date=dateWords(d.on,d.en);
  const line3=[date?.short,`${w.lifeDay} ${d.day}`,`${w.gradeOf}${d.en?":":""} ${d.grade}`].filter(Boolean).join(' · ');
  ctext(c,`🎓 ${d.certName}`,W/2,top+(port?58:36)*u,{size:(port?42:30)*u,color:WINE,max:W-80*u});
  ctext(c,d.name,W/2,top+(port?114:74)*u,{size:(port?50:32)*u,family:SERIF,style:'italic',weight:700,color:INK,max:W-120*u});
  ctext(c,line3,W/2,top+(port?166:108)*u,{size:(port?28:19)*u,weight:500,color:MUTED,max:W-100*u});
  ctext(c,'Phố Có Chuyện',W-20*u,H-14*u,{size:(port?18:13)*u,weight:600,color:'#b9a27a',align:'right'});
}
async function photoCanvas(d,paper,W,H){
  const cv=document.createElement('canvas');cv.width=W;cv.height=H;
  drawPhoto(cv.getContext('2d'),W,H,d,paper);return cv;
}
/** A small copy for Kỷ niệm (3:2 like its polaroids): WebP, else JPEG (Safari), under ~120 KB. */
async function albumImage(d,paper){
  const big=await photoCanvas(d,paper,1200,800);
  for(const w of [720,600,480]){
    const cv=document.createElement('canvas');cv.width=w;cv.height=Math.round(w*2/3);
    const c=cv.getContext('2d');c.imageSmoothingQuality='high';c.drawImage(big,0,0,cv.width,cv.height);
    for(const q of [.8,.68,.55]){
      let url=cv.toDataURL('image/webp',q);
      if(!url.startsWith('data:image/webp'))url=cv.toDataURL('image/jpeg',q);
      if(url.length<=120000)return url;
    }
  }
  return null;
}

/* ------------------------------------------------------------------ the dialog */
let S=null;
const IOS=()=>/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
const media=q=>!!globalThis.matchMedia?.(q)?.matches;
const reduced=api=>document.documentElement.classList.contains('reduce-motion')||!!api?.state?.settings?.reduceMotion||media('(prefers-reduced-motion: reduce)');
const button=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}>${label}</button>`;

function dialog(){
  let d=document.getElementById('dpDialog');
  if(!d){d=document.createElement('dialog');d.id='dpDialog';d.className='dp-dialog';d.setAttribute('aria-labelledby','dpTitle');
    d.addEventListener('close',cleanup);document.body.appendChild(d);}
  return d;
}
function cleanup(){
  if(!S)return;
  for(const u of S.urls)URL.revokeObjectURL(u);
  S=null;const d=document.getElementById('dpDialog');if(d)d.innerHTML='';
}
function confetti(){
  const cols=['#e8a33d','#d9534f','#4f9d8f','#f2d16b','#8e6cc6','#ef8fb0','#ffffff'];
  return `<div class="dp-confetti" aria-hidden="true">${Array.from({length:34},(_,i)=>`<i style="--x:${(i*29+7)%100}%;--d:${((i*37)%17)/10}s;--c:${cols[i%cols.length]};--r:${(i*53)%360}deg"></i>`).join('')}</div>`;
}
function render(){
  const d=document.getElementById('dpDialog');if(!d||!S)return;
  const {data:x,view,reveal}=S;
  const head=reveal?`<div class="dp-cheer"><span class="dp-cap" aria-hidden="true">🎓</span><h2 id="dpTitle">Chúc mừng! Bạn đã được cấp chứng chỉ</h2><p>${esc(x.certName)} · ${x.en?'Grade':'Xếp loại'} <b>${esc(x.grade)}</b></p></div>`
    :`<div class="dp-head"><span class="dp-emoji" aria-hidden="true">${esc(x.emoji)}</span><div class="grow"><h2 id="dpTitle">Giấy chứng nhận</h2><small>${esc(x.certName)}</small></div></div>`;
  const tabs=`<div class="dp-tabs" role="group" aria-label="Xem">${[['paper','📜 Giấy chứng nhận'],['photo','📸 Ảnh lưu niệm']].map(([v,l])=>`<button type="button" data-action="jrCertDipView" data-view="${v}" aria-pressed="${view===v||(view==='hold'&&S.holdOf===v)}">${l}</button>`).join('')}</div>`;
  let stage,acts,hint='';
  if(view==='hold'){
    stage=`<figure class="dp-stage dp-hold"><img src="${S.hold}" alt="${esc(x.certName)}"></figure>`;
    hint=`<p class="dp-hint"><b>Nhấn giữ ảnh</b> rồi chọn “Lưu vào Ảnh” để giữ trên máy.</p>`;
    acts=button('← Quay lại','jrCertDipView',{view:S.holdOf},'cream')+button('Đóng','jrCertDipClose',{},'ghost');
  }else if(view==='photo'){
    stage=S.photoURL?`<figure class="dp-stage dp-photo"><img src="${S.photoURL}" alt="Ảnh lưu niệm: ${esc(x.name)} nhận ${esc(x.certName)}"></figure>`
      :`<figure class="dp-stage dp-photo dp-wait"><p>📸 Đang chụp ảnh…</p></figure>`;
    acts=button('⬇️ Tải ảnh','jrCertDipSave',{kind:'photo'},'primary')+button('🖼️ Lưu vào Kỷ niệm','jrCertDipKeep',{},'cream')+button('Đóng','jrCertDipClose',{},'ghost');
  }else{
    stage=`<div class="dp-stage dp-paper${S.zoom?' zoom':''}"><button type="button" class="dp-zoom" data-action="jrCertDipZoom" aria-label="${S.zoom?'Thu nhỏ giấy chứng nhận':'Phóng to giấy chứng nhận'}"><span class="dp-sheet" data-no-translate>${S.svg}</span></button></div>`;
    hint=`<p class="dp-hint">${S.zoom?'Kéo để xem các góc · chạm lần nữa để thu nhỏ.':'Chạm vào giấy để phóng to.'}</p>`;
    acts=button('⬇️ Tải ảnh','jrCertDipSave',{kind:'paper'},'primary')+button('📸 Chụp ảnh lưu niệm','jrCertDipView',{view:'photo'},'cream')+button(reveal?'Tuyệt!':'Đóng','jrCertDipClose',{},'ghost');
  }
  const fresh=reveal&&!S.seen&&!S.calm;S.seen=true;   // the celebration plays once, not on every redraw
  d.className=`dp-dialog${fresh?' reveal':''}`;
  d.innerHTML=`${fresh?confetti():''}<div class="dp-inner">${head}${tabs}${stage}${hint}<div class="dp-actions">${acts}</div></div>`;
}

/** Open the diploma of certificate `gid` (reveal: the celebration right after passing). */
export async function openDiploma(env,gid,{reveal=false}={}){
  const data=diplomaData(env.api,gid);
  if(!data){env.toast?.('Chưa có chứng chỉ này.',true);return false;}
  certCss();const d=dialog();
  if(S)cleanup();
  S={env,gid,data,view:'paper',reveal,calm:reduced(env.api),seen:false,zoom:false,urls:[],svg:diplomaSVG(data),
    paper:null,png:{},photoURL:null,hold:null,holdOf:'paper'};
  render();
  if(!d.open)d.showModal();
  d.scrollTop=0;
  // Ready the images now, so a tap on "Tải ảnh" shares at once (a phone's share sheet needs the tap's moment).
  const s=S;
  s.paper=paperImage(data);
  s.png.paper=s.paper.then(img=>paperPNG(img));
  s.png.paper.catch(()=>{});
  return true;
}
function photoReady(){
  const s=S;if(!s)return Promise.reject(new Error('closed'));
  if(!s.png.photo){
    s.png.photo=s.paper.catch(()=>null).then(async img=>{const cv=await photoCanvas(s.data,img,1080,1350);return toBlob(cv);});
    s.png.photo.then(b=>{if(S!==s)return;const u=URL.createObjectURL(b);s.urls.push(u);s.photoURL=u;if(s.view==='photo')render();}).catch(()=>{if(S===s)s.env.toast?.('Chưa chụp được ảnh, thử lại nhé.',true);});
  }
  return s.png.photo;
}
const fileName=(x,kind)=>(x.en?(kind==='photo'?`souvenir-${x.gid}`:`certificate-${x.serial}`):(kind==='photo'?`anh-luu-niem-${x.gid}`:`chung-chi-${x.serial}`)).toLowerCase()+'.png';
const asDataURL=blob=>new Promise((ok,fail)=>{const fr=new FileReader();fr.onload=()=>ok(fr.result);fr.onerror=fail;fr.readAsDataURL(blob);});

/** Keep a PNG on the device: share sheet on a phone (with the file), long-press on iOS without it, else a download. */
async function deliver(blob,name,kind){
  const s=S,toast=s?.env.toast||(()=>{});
  const touch=media('(pointer: coarse)');
  let file=null;try{file=new File([blob],name,{type:'image/png'});}catch{}
  if(touch&&file&&navigator.canShare?.({files:[file]})){
    try{await navigator.share({files:[file],title:s?.data.certName||''});return;}
    catch(e){if(e?.name==='AbortError')return;}
  }
  if(IOS()){
    if(S!==s)return;
    s.hold=await asDataURL(blob);s.holdOf=kind;s.view='hold';render();return;
  }
  const url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=name;a.rel='noopener';document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),15000);
  toast(kind==='photo'?'Đã tải ảnh lưu niệm về máy.':'Đã tải giấy chứng nhận về máy.','good');
}

/** jrCertDiploma (open), jrCertDip* (inside the dialog). */
export async function diplomaAction(action,data,el,env){
  if(action==='jrCertDiploma'){await openDiploma(env,data.cert,{reveal:false});return true;}
  const s=S;if(!s)return true;
  switch(action){
    case'jrCertDipClose':document.getElementById('dpDialog')?.close();return true;
    case'jrCertDipZoom':s.zoom=!s.zoom;render();return true;
    case'jrCertDipView':{
      s.view=data.view==='photo'?'photo':'paper';render();
      if(s.view==='photo')photoReady().catch(()=>{});
      return true;}
    case'jrCertDipSave':{
      const kind=data.kind==='photo'?'photo':'paper';
      try{const blob=await(kind==='photo'?photoReady():s.png.paper);if(S!==s)return true;await deliver(blob,fileName(s.data,kind),kind);}
      catch{env.toast?.('Chưa tạo được ảnh, thử lại nhé.',true);}
      return true;}
    case'jrCertDipKeep':{
      if(s.kept){env.toast?.('Ảnh này đã ở trong Kỷ niệm rồi.');return true;}
      let image=null;
      try{const img=await s.paper.catch(()=>null);image=await albumImage(s.data,img);}catch{}
      if(S!==s)return true;
      if(!image){env.toast?.('Ảnh hơi lớn để lưu vào Kỷ niệm: bấm Tải ảnh để giữ trên máy nhé.',true);return true;}
      const title=`🎓 ${s.data.certName}`.slice(0,60);
      const r=await env.cmd('photo',{image,title});
      if(r&&S===s){s.kept=true;}
      return true;}
  }
  return false;
}
