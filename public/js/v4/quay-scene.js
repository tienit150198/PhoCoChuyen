/** 🏪 Quầy của bạn: your own counter drawn on a canvas, in the scenes' style (scenes/kit.js pens, the characters of
 * v4/look.js). A cart, a market stall or a street kiosk with its awning in your colour, the sign with your counter's
 * name, the menu board with today's dishes and prices, your decor, the tables, you (or your staff) behind it and the
 * customers waiting in front. Drawn once per change (no animation loop): the stall card, the editors' live preview
 * and the day at the counter all call paintCounter() after their render.
 * Logical size 360 x 210 (scaled to the canvas width, devicePixelRatio aware). */
import {R,E,L,P,T,fit,plantAt,bloom,heart} from '../scenes/kit.js';
import {ART,figureOf,defaultLook,paintPlayer,CANVAS} from './look.js';
import {t as tr} from './i18n.js';

const W=360,H=210;
const shade=(hex,k)=>{const n=parseInt(hex.slice(1),16);const f=v=>Math.max(0,Math.min(255,Math.round(v*k)));
  return `#${[(n>>16)&255,(n>>8)&255,n&255].map(f).map(v=>v.toString(16).padStart(2,'0')).join('')}`;};
const hash=(seed,i)=>{const v=Math.sin((seed+1)*12.9898+i*78.233)*43758.5453;return v-Math.floor(v);};
const pick=(seed,i,list)=>list[Math.floor(hash(seed,i)*list.length)%list.length];
const KEYS=k=>Object.keys(ART[k]);
const NOT_TOPS=new Set(['ao_cuoi','vest_cuoi']);
const figures=new Map(),sprites=new WeakMap();
/** A passer-by's look from a number (the same customer always looks the same). */
export function customerFigure(seed){
  if(figures.has(seed))return figures.get(seed);
  const g=hash(seed,1)<.5?'female':'male',L=defaultLook(g);
  L.hair=pick(seed,2,KEYS('hair'));L.shade=pick(seed,3,['mau_nau','mau_den','mau_mat_ong','mau_nau','mau_den']);
  L.skin=pick(seed,4,KEYS('skin'));L.top=pick(seed,5,KEYS('top').filter(k=>!NOT_TOPS.has(k)&&k!=='ao_quen'));
  L.bottom=pick(seed,6,KEYS('bottom'));L.shoes=pick(seed,7,KEYS('shoes'));L.acc=hash(seed,8)<.7?'pk_khong':pick(seed,9,['kinh_tron','non_la','mu_len','no_toc']);
  L.uniform=false;
  const figure=figureOf(L,g);if(figures.size>=96)figures.delete(figures.keys().next().value);figures.set(seed,figure);return figure;
}
const STAFF_SEED=[11,23,37];
function person(c,F,x,y,s){
  let sprite=sprites.get(F);
  if(!sprite){sprite=document.createElement('canvas');sprite.width=240;sprite.height=340;const pen=sprite.getContext('2d');pen.setTransform(2,0,0,2,120,310);try{paintPlayer(pen,F,CANVAS);}catch{/* a look this build does not know */}sprites.set(F,sprite);}
  c.drawImage(sprite,x-60*s,y-155*s,120*s,170*s);
}
function actor(c,p,x,y,s){person(c,customerFigure(p.seed),x,y,s);if(p.state==='completed')T(c,p.emoji||'🛍️',x+21*s,y-29*s,19*s,'#4d382a',500);}
function apron(c,x,y,s,col){c.save();c.translate(x,y);c.scale(s,s);R(c,-17,-44,34,30,col,8);L(c,-12,-44,-16,-56,col,2.5);L(c,12,-44,16,-56,col,2.5);c.restore();}

/* ---- the pieces ---- */
function street(c,place){
  const g=c.createLinearGradient(0,0,0,H);g.addColorStop(0,'#fdf3e3');g.addColorStop(1,'#f6e3c8');c.fillStyle=g;c.fillRect(0,0,W,H);
  // the house behind: a wall, two shuttered windows (a kiosk is its own facade)
  if(place!=='kiot'){R(c,8,18,344,140,'#f3dcc0',10);for(const x of [30,282]){R(c,x,36,48,46,'#e7c39f',6);R(c,x+4,40,40,38,'#bfe0e3',4);L(c,x+24,40,x+24,78,'#e7c39f',3);}}
  R(c,0,166,W,44,'#e9d4b8',0);
  for(let i=0;i<12;i++)L(c,i*32,166,i*32-10,H,'#dcc3a2',1.2);
  L(c,0,166,W,166,'#d8bb98',2);
}
function awning(c,x,y,w,h,col,scallop=true){
  const n=Math.max(4,Math.round(w/26)),sw=w/n,dark=shade(col,.82);
  for(let i=0;i<n;i++)P(c,[[x+i*sw,y],[x+(i+1)*sw,y],[x+(i+1)*sw+(i===n-1?6:0),y+h],[x+i*sw-(i===0?6:0),y+h]],i%2?'#fff8ef':col);
  if(scallop)for(let i=0;i<n;i++){c.beginPath();c.arc(x+i*sw+sw/2,y+h,sw/2,0,Math.PI);c.fillStyle=i%2?'#fff8ef':col;c.fill();}
  L(c,x-6,y+h,x+w+6,y+h,dark,1.5);R(c,x-4,y-4,w+8,6,dark,3);
}
function sign(c,name,x,y,w,h,col){
  R(c,x+3,y+4,w,h,'#00000018',9);R(c,x,y,w,h,'#fffaf0',9,shade(col,.75),2.5);
  T(c,name,x+w/2,y+h/2+1,fit(c,name,w-18,Math.min(17,h-6),800),'#5a3d33',800);
}
/** The (translated) text cut with "…" to fit `max` pixels at the current font: small chalk letters, no overflow. */
function clip(c,s,max){
  let t=tr(String(s));if(c.measureText(t).width<=max)return t;
  while(t.length>1&&c.measureText(t+'…').width>max)t=t.slice(0,-1);
  return t.trimEnd()+'…';
}
function board(c,items,x,y,w,h){
  R(c,x-3,y-3,w+6,h+6,'#9a7356',6);R(c,x,y,w,h,'#2f4a3e',4);
  T(c,'MENU',x+w/2,y+9,9,'#f6e7c8',800);
  const rows=items.slice(0,4),lh=(h-18)/Math.max(3,rows.length);
  rows.forEach((it,i)=>{const ty=y+20+i*lh+lh/2-3;
    T(c,it.emoji,x+9,ty,10,'#fff',400);
    c.font='700 8px "Trebuchet MS", "Segoe UI", sans-serif';
    T(c,clip(c,it.name,w-18-6-String(it.price).length*6-4),x+18,ty,8,'#f6f1e3',700,'left');
    T(c,String(it.price),x+w-6,ty,9,'#ffd98a',800,'right');});
}
function stool(c,x,y){E(c,x,y+16,9,3,'#8b735322');R(c,x-8,y,16,4,'#c98b5a',2);L(c,x-5,y+4,x-6,y+16,'#9a6a45',2);L(c,x+5,y+4,x+6,y+16,'#9a6a45',2);}
function table(c,x,y){E(c,x,y+22,18,4,'#8b735322');E(c,x,y,17,6,'#f4e7d3');L(c,x,y+4,x,y+20,'#9a6a45',3);E(c,x,y,17,6,'#00000000');R(c,x-7,y-10,6,9,'#fff',2,'#d8c2a8',1);stool(c,x-24,y+6);stool(c,x+24,y+6);}
const DECOR={
  cay:(c,a)=>plantAt(c,a.plant[0],a.plant[1],.42),
  long_den:(c,a)=>{for(const [x,y] of a.lanterns){L(c,x,y-10,x,y-4,'#7a5a3c',1.2);E(c,x,y+5,8,10,'#e0483e');R(c,x-5,y-6,10,3,'#f2c14e',1);R(c,x-5,y+13,10,3,'#f2c14e',1);L(c,x,y+16,x,y+22,'#f2c14e',1.5);}},
  co_day:(c,a)=>{const [x0,x1,y]=a.flags,n=9;L(c,x0,y,x1,y,'#8a6a50',1);for(let i=0;i<n;i++){const x=x0+(i+.5)*(x1-x0)/n;P(c,[[x-7,y],[x+7,y],[x,y+11]],['#e0483e','#f2c14e','#4fa361','#3f86c9','#ec7fa3'][i%5]);}},
  meo:(c,a)=>{const [x,y]=a.cat;E(c,x,y-9,10,11,'#fff7ea');E(c,x,y-23,9,8,'#fff7ea');P(c,[[x-8,y-28],[x-4,y-34],[x-2,y-28]],'#fff7ea');P(c,[[x+8,y-28],[x+4,y-34],[x+2,y-28]],'#fff7ea');
    E(c,x-3,y-24,1.3,1.3,'#5b4038');E(c,x+3,y-24,1.3,1.3,'#5b4038');E(c,x,y-12,4,4,'#f2c14e');L(c,x+9,y-14,x+13,y-26,'#fff7ea',4);E(c,x-7,y-4,3,2,'#e0483e');},
  hoa:(c,a)=>{const [x,y]=a.flower;R(c,x-9,y-12,18,13,'#d98a5f',4);for(const [dx,dy,col] of [[-5,-18,'#ec7fa3'],[5,-20,'#f2c14e'],[0,-25,'#e0483e']]){L(c,x,y-12,x+dx,y+dy,'#4fa361',1.5);bloom(c,x+dx,y+dy,5,col);}},
  bang_phan:(c,a)=>{const [x,y]=a.chalk;P(c,[[x-15,y],[x-2,y-38],[x+2,y-38],[x+15,y]],'#9a7356');R(c,x-13,y-36,26,28,'#2f4a3e',3);T(c,'HÔM NAY',x,y-28,5.5,'#f6e7c8',800);heart(c,x,y-17,.22,'#ec7fa3');},
  den_day:(c,a)=>{const [x0,x1,y]=a.lights;c.strokeStyle='#6b5040';c.lineWidth=1;c.beginPath();c.moveTo(x0,y);for(let i=1;i<=10;i++){const x=x0+i*(x1-x0)/10;c.quadraticCurveTo(x-(x1-x0)/20,y+6,x,y);}c.stroke();
    for(let i=0;i<10;i++){const x=x0+(i+.5)*(x1-x0)/10;E(c,x,y+5,4.5,4.5,'#ffe9a033');E(c,x,y+4,2.4,3,'#ffd65a');}},
  radio:(c,a)=>{const [x,y]=a.radio;R(c,x-12,y-14,24,14,'#c9514a',3);E(c,x-5,y-7,4,4,'#3a3230');R(c,x+2,y-11,7,3,'#fff1d8',1);L(c,x+6,y-14,x+11,y-24,'#3a3230',1.2);},
};
/** Where things go, per place (the counter's top is `top`). */
const LAYOUT={
  xe:{counter:[105,124,150,46],top:124,awn:[95,38,170,16],sign:[120,6,120,24],board:[18,92,74,64],behind:[[158,0],[204,0]],
    plant:[292,168],lanterns:[[104,76],[256,76]],flags:[60,300,14],cat:[238,124],flower:[278,168],chalk:[316,170],lights:[96,264,58],radio:[130,124],
    tables:[[302,152],[256,186]],cust:[[60,198],[28,202]]},
  sap:{counter:[86,126,196,44],top:126,awn:[70,40,228,16],sign:[110,6,148,26],board:[14,88,66,70],behind:[[150,0],[204,0],[258,0]],
    plant:[302,168],lanterns:[[80,78],[288,78]],flags:[20,340,12],cat:[262,126],flower:[64,168],chalk:[332,172],lights:[72,296,60],radio:[110,126],
    tables:[[314,152],[318,194],[272,197],[228,200]],cust:[[50,198],[22,202]]},
  kiot:{counter:[70,128,220,42],top:128,awn:[56,46,248,14],sign:[60,4,240,30],board:[302,74,52,84],behind:[[132,0],[186,0],[240,0]],
    plant:[44,168],lanterns:[[64,82],[296,82]],flags:[8,352,40],cat:[272,128],flower:[320,172],chalk:[24,172],lights:[58,302,64],radio:[96,128],
    tables:[[318,187],[272,197],[228,200],[184,202],[140,202],[96,202]],cust:[[44,198],[16,202]]},
};
function counterBody(c,place,A,col){
  const [x,y,w,h]=A.counter;
  if(place==='kiot'){R(c,36,30,288,140,'#f7e6cf',8,'#e2c7a4',2);R(c,84,84,192,42,'#cfe8ea',4,'#b9d3d6',2);L(c,180,84,180,126,'#b9d3d6',2);}
  if(place==='xe'){E(c,x+28,y+h+14,14,14,'#5b4436');E(c,x+28,y+h+14,6,6,'#c9a978');E(c,x+w-28,y+h+14,14,14,'#5b4436');E(c,x+w-28,y+h+14,6,6,'#c9a978');
    L(c,x+w,y+16,x+w+26,y+4,'#8a6a50',4);L(c,x+4,y,x+4,A.awn[1]+A.awn[3],'#8a6a50',3);L(c,x+w-4,y,x+w-4,A.awn[1]+A.awn[3],'#8a6a50',3);}
  if(place==='sap'){for(const px of [x+4,x+w-4])L(c,px,y,px,A.awn[1]+A.awn[3],'#8a6a50',3.5);}
  R(c,x,y,w,h,'#fff4e4',8,'#d9b994',2);R(c,x,y,w,10,shade(col,.95),5);
  for(let i=1;i<4;i++)L(c,x+i*w/4,y+14,x+i*w/4,y+h-4,'#ead6bb',1.2);
  R(c,x+w/2-26,y+16,52,22,'#fffaf2',5,'#e5cfb3',1.5);
}

/** Paint `opts` on `canvas`: {place, name, color, decor[], tables, menu:[{emoji,name,price}], me (a figure) or null,
 * staff (count), actors [{seed,state,emoji}], online, closed}. */
export function paintCounter(canvas,o){
  if(o.firstPerson)return paintBehindCounter(canvas,o);
  if(!canvas?.getContext)return;
  const cssW=canvas.clientWidth||W,dpr=Math.min(2,globalThis.devicePixelRatio||1),k=cssW/W;
  const pw=Math.round(cssW*dpr),ph=Math.round(H*k*dpr);
  if(canvas.width!==pw||canvas.height!==ph){canvas.width=pw;canvas.height=ph;}
  const c=canvas.getContext('2d');c.setTransform(dpr*k,0,0,dpr*k,0,0);c.clearRect(0,0,W,H);
  const place=LAYOUT[o.place]?o.place:'xe',A=LAYOUT[place],col=o.color||'#d9534f',has=new Set(o.decor||[]);
  street(c,place);
  if(has.has('co_day'))DECOR.co_day(c,A);
  // behind the counter: you, then your staff (or only the staff when you are away)
  const people=[];
  if(o.me)people.push(['me',o.me]);
  for(let i=0;i<Math.min(o.staff||0,A.behind.length-people.length);i++)people.push(['staff',customerFigure(STAFF_SEED[i])]);
  const mid=(A.behind[0][0]+A.behind[A.behind.length-1][0])/2,step=people.length>1?(A.behind[1][0]-A.behind[0][0]):0;
  people.forEach(([who,F],i)=>{const x=mid+(i-(people.length-1)/2)*step;person(c,F,x,A.top+28,.55);apron(c,x,A.top+28,.55,who==='me'?shade(col,.9):'#6f8ea8');});
  if(!people.length&&!o.closed)T(c,'🙋',A.behind[0][0],A.top-12,22,'#000',400);
  counterBody(c,place,A,col);
  awning(c,...A.awn,col);
  if(has.has('den_day'))DECOR.den_day(c,A);
  sign(c,o.name||'Quầy của bạn',...A.sign,col);
  if(place==='xe'){L(c,A.sign[0]+20,A.sign[1]+26,A.awn[0]+30,A.awn[1]-4,'#8a6a50',2);L(c,A.sign[0]+A.sign[2]-20,A.sign[1]+26,A.awn[0]+A.awn[2]-30,A.awn[1]-4,'#8a6a50',2);}
  board(c,o.menu||[],...A.board);
  // on the counter: a cup or two of the trade, the cat, the radio
  T(c,(o.menu?.[0]?.emoji)||'🧋',A.counter[0]+A.counter[2]/2-12,A.top-6,14,'#000',400);
  T(c,(o.menu?.[1]?.emoji)||'',A.counter[0]+A.counter[2]/2+12,A.top-6,14,'#000',400);
  for(const id of ['long_den','meo','radio'])if(has.has(id))DECOR[id](c,A);
  if(o.online){R(c,A.counter[0]+A.counter[2]-38,A.top+18,30,20,'#2f3a4a',4);T(c,'📱',A.counter[0]+A.counter[2]-23,A.top+28,11,'#fff',400);}
  // in front: tables, plants, flowers, the chalkboard
  const tb=Math.min(o.tables||0,A.tables.length);
  for(let i=0;i<tb;i++)table(c,...A.tables[i]);
  for(const id of ['cay','hoa','bang_phan'])if(has.has(id))DECOR[id](c,A);
  // customers: the one being served by the counter, the queue behind
  const actors=(o.actors||[]).slice(0,8);
  actors.slice(4).forEach((p,i)=>actor(c,p,42+i*86,179,.39));
  actors.slice(0,4).forEach((p,i)=>actor(c,p,70+i*76,209,.48));
  if(o.activityLabel){R(c,82,72,196,21,'#fff8e8',7);T(c,o.activityLabel,180,83,10,'#6a503c',700);}
  if(o.closed){c.fillStyle='#3a2a2055';c.fillRect(0,0,W,H);R(c,W/2-70,H/2-18,140,36,'#fffaf0',10,'#c79879',2);T(c,'ĐÓNG CỬA',W/2,H/2,15,'#8a4b1f',800);}
}

/** The owner's eye level: the customer is across the worktop, tools are in reach.
 * Each portrait represents a real current customer or a clearly labelled recent receipt. */
export function paintBehindCounter(canvas,o){
 if(!canvas?.getContext)return;
 const h=270,cssW=canvas.clientWidth||W,dpr=Math.min(2,globalThis.devicePixelRatio||1),k=cssW/W;
 const pw=Math.round(cssW*dpr),ph=Math.round(h*k*dpr);if(canvas.width!==pw||canvas.height!==ph){canvas.width=pw;canvas.height=ph;}
 const c=canvas.getContext('2d');c.setTransform(dpr*k,0,0,dpr*k,0,0);
 const col=o.color||'#a86d51';
 R(c,0,0,W,h,'#f8edda');R(c,0,80,W,118,'#d7c5a7');
 // Looking out into a small neighbourhood through the shop opening.
 R(c,24,49,84,89,'#e8c9a8',2);R(c,255,47,84,96,'#cbd8c8',2);
 for(const x of [35,69,265,301]){R(c,x,65,24,38,'#f7e7cd',3);R(c,x+3,68,18,27,'#98b7b6',2);}
 R(c,122,45,113,91,'#f1dabb',2);R(c,147,62,51,64,'#a3bdba',4);R(c,146,61,54,9,'#be9370',2);
 P(c,[[0,139],[360,139],[360,210],[0,210]],'#dfcdb0');
 for(let i=0;i<6;i++)L(c,i*80-60,270,180+(i-3)*20,139,'#cfb797',1);
 awning(c,0,0,360,24,col);R(c,0,0,12,213,'#835b42');R(c,348,0,12,213,'#835b42');
 const actors=(o.actors||[]).slice(0,8);
 if(actors.length){
  const spots=[[33,173,.42],[80,174,.44],[124,177,.46],[240,177,.46],[283,174,.44],[326,173,.42],[302,205,.56]];
  actors.slice(1).forEach((p,i)=>actor(c,p,...spots[i]));
  actor(c,actors[0],180,224,.92);
 }else{
  R(c,106,111,148,45,'#fff8e9',10,'#d9c3a1',1);
  T(c,o.observe?'Tiệm đang mở':'Chờ khách ghé quầy',180,127,12,'#6f543e',700);
  T(c,o.observe?'Sổ bán hàng ở bên dưới':'Mọi đơn đều được ghi tại quầy',180,143,8,'#94795d',500);
 }
 if(o.activityLabel){R(c,184,38,156,26,'#fff8e8',8);T(c,o.activityLabel,262,52,9,'#6a503c',700);}
 if(o.orderLabel){R(c,25,41,150,40,'#fff8e8',8,'#dfc8aa',1);c.font='700 11px sans-serif';T(c,clip(c,o.orderLabel,132),100,56,11,'#6a503c',700);T(c,o.observe?'LƯỢT BÁN VỪA GHI NHẬN':'KHÁCH ĐANG CHỜ',100,71,7,'#95765c',700);}
 // Broad oak worktop hides lower bodies, placing the owner behind the counter.
 P(c,[[9,184],[351,184],[378,270],[-18,270]],'#b8865d');
 P(c,[[13,181],[347,181],[365,237],[-5,237]],'#e6bd88');
 for(const y of [197,218,239,258])L(c,0,y,360,y,'#a4714f33',1);
 R(c,13,190,75,50,'#f6e9cf',7,'#bd986b',1);T(c,'KHAY MÓN',50,201,7,'#8d6e51',800);
 (o.menu||[]).slice(0,3).forEach((dish,i)=>T(c,dish.emoji,29+i*21,221,17,'#4e3828',500));
 R(c,265,190,68,49,'#655344',7);R(c,271,196,56,15,'#dae5cc',3);T(c,'KÉT QUẦY',299,204,8,'#4d5d43',700);
 for(let i=0;i<3;i++)for(let j=0;j<2;j++)R(c,275+i*17,216+j*9,12,6,'#cfb79a',2);
 R(c,112,202,103,29,'#f7ead3',5,'#c4a070',1);T(c,o.name||'Quầy của bạn',163,216,fit(c,o.name||'Quầy của bạn',93,11,700),'#775239',700);
 // Your apron and hands frame the lower edge without covering controls or stock.
 E(c,112,265,32,19,'#d9a685');E(c,245,265,32,19,'#d9a685');R(c,132,248,93,23,col,12);
 if(o.closed){R(c,73,98,214,47,'#fff7e8',10);T(c,'Quầy đang tạm dừng',180,117,14,'#705139',800);T(c,o.reason||'Xem nguyên liệu và vốn ở bên dưới',180,135,8,'#95765c',500);}
}
