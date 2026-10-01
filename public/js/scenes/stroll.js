/** 🚶 Đi dạo: the places drawn from above (v4/walk.js; live/street.py holds the same geometry). World units:
 * every place is 600 × 900, the walkable rectangles come from the server (`geo.walk`) and are paved; the rest is
 * grass, water, stalls and buildings. Night (the "Phố đêm" theme, and always a little at Chợ đêm) dims the
 * scene and lights the lamps and lanterns. Decorations are seeded, so a place looks the same every time. */
import {R,E,L,P,bloom,heart} from './kit.js';

export const WORLD={w:600,h:900};

const seeded=seed=>()=>{seed=(seed*16807)%2147483647;return seed/2147483647;};

/* ---- little things ---- */
function lawn(c,base,tuft,seed){
  c.fillStyle=base;c.fillRect(-400,-400,1400,1700);
  const r=seeded(seed);for(let i=0;i<220;i++)E(c,-40+r()*680,-40+r()*980,2+r()*6,1+r()*2.2,tuft);
}
function pave(c,rects,fill,line,step=30){
  c.save();c.beginPath();for(const [x0,y0,x1,y1] of rects)c.roundRect(x0-8,y0-8,x1-x0+16,y1-y0+16,16);
  c.fillStyle=fill;c.fill();c.clip();c.strokeStyle=line;c.lineWidth=1.2;c.beginPath();
  for(let x=0;x<=600;x+=step){c.moveTo(x,0);c.lineTo(x,900);}for(let y=0;y<=900;y+=step){c.moveTo(0,y);c.lineTo(600,y);}c.stroke();c.restore();
}
function tree(c,x,y,s=1,tones=['#8dbf86','#a2cf98','#7cae79']){
  E(c,x+8*s,y+12*s,30*s,13*s,'#43553a22');
  for(const [dx,dy,rr,k] of [[-12,4,20,2],[12,2,21,0],[0,-10,22,1],[-4,8,16,0],[8,-14,13,1]])E(c,x+dx*s,y+dy*s,rr*s,rr*.92*s,tones[k]);
  E(c,x-6*s,y-14*s,6*s,4*s,'#ffffff40');
}
function willow(c,x,y,s=1){
  E(c,x+6*s,y+34*s,38*s,12*s,'#43553a22');c.lineCap='round';
  for(let i=0;i<17;i++){const dx=(i-8)*4.4*s,len=(30+((i*11)%7)*5)*s,sway=((i%3)-1)*5*s;   // strands hang behind the crown
    c.strokeStyle=['#8fc283','#7cb173','#a3d197'][i%3];c.lineWidth=3*s;c.beginPath();c.moveTo(x+dx*.7,y-6*s);c.quadraticCurveTo(x+dx*1.1+sway,y+len*.5,x+dx*1.25+sway*.5,y+len);c.stroke();}
  for(const [dx,dy,rx,ry,col] of [[-12,0,20,15,'#86b97c'],[12,-2,21,16,'#8fc283'],[0,-10,22,14,'#9ccb8f'],[-4,-16,10,7,'#b3dba6']])E(c,x+dx*s,y+dy*s,rx*s,ry*s,col);
}
function bush(c,x,y,s=1,col='#93c48a'){E(c,x+3,y+5,18*s,8*s,'#43553a1f');E(c,x-8*s,y,11*s,10*s,col);E(c,x+8*s,y,11*s,10*s,col);E(c,x,y-6*s,12*s,10*s,'#a6d19b');}
function flowers(c,x,y,w,h,cols,seed){R(c,x,y,w,h,'#b98f6a',10);R(c,x+4,y+4,w-8,h-8,'#8fbf7d',8);const r=seeded(seed);for(let i=0;i<Math.max(4,w*h/260);i++)bloom(c,x+10+r()*(w-20),y+10+r()*(h-20),4.5,cols[i%cols.length]);}
function lamp(c,x,y,lights){E(c,x+3,y+4,7,3,'#00000022');E(c,x,y,7,7,'#6f6a66');E(c,x,y,4.2,4.2,'#fff1c4');lights.push([x,y,56,'255,200,120']);}
function bench(c,x,y,vertical=false){
  if(vertical){R(c,x-9,y-26,18,52,'#a8754f',4);for(let k=-18;k<=18;k+=9)L(c,x-8,y+k,x+8,y+k,'#8a5d3c',1.4);R(c,x-12,y-28,5,56,'#6c6158',2);return;}
  R(c,x-28,y-9,56,18,'#a8754f',4);for(let k=-19;k<=19;k+=9.5)L(c,x+k,y-8,x+k,y+8,'#8a5d3c',1.4);R(c,x-30,y-12,60,5,'#6c6158',2);
}
function lanternString(c,x0,y0,x1,y1,lights,seed){
  c.strokeStyle='#5c4a3e';c.lineWidth=1.4;c.beginPath();c.moveTo(x0,y0);c.quadraticCurveTo((x0+x1)/2,(y0+y1)/2+26,x1,y1);c.stroke();
  const r=seeded(seed),cols=['#e8524a','#f2b33d','#e8524a','#f07f3c','#d9455f'];
  for(let i=1;i<9;i++){const t=i/9,x=(1-t)*(1-t)*x0+2*(1-t)*t*(x0+x1)/2+t*t*x1,y=(1-t)*(1-t)*y0+2*(1-t)*t*((y0+y1)/2+26)+t*t*y1,col=cols[Math.floor(r()*cols.length)];
    E(c,x,y+5,6,7.5,col);R(c,x-3,y-3,6,3,'#7a5a2e',1);lights.push([x,y+5,26,'255,170,90']);}
}
function stall(c,x,y,w,h,awn,goods,right,seed){
  E(c,x+w/2+4,y+h/2+6,w/2+6,h/2+4,'#00000018');R(c,x,y,w,h,'#f7f1e6',6);
  c.save();c.beginPath();c.roundRect(x,y,w,h,6);c.clip();
  for(let i=0;i*14<h;i++){c.fillStyle=i%2?'#f7f1e6':awn;c.fillRect(x,y+i*14,w,14);}c.restore();
  const fx=right?x-6:x+w-12,r=seeded(seed);R(c,fx,y+6,18,h-12,'#c49a72',4);
  for(let k=0;k<6;k++)E(c,fx+9,y+16+k*(h-30)/5,5.5,5.5,goods[Math.floor(r()*goods.length)]);
}
function roofRow(c,x,y,w,h,col,ridge){R(c,x,y,w,h,col,5);L(c,x+8,y+h/2,x+w-8,y+h/2,ridge,3);for(let k=x+14;k<x+w-6;k+=14)L(c,k,y+4,k,y+h-4,'#00000014',1);}

/* ---- the places ---- */
function boho(c,g,lights){
  lawn(c,'#cfe3b1','#c2d9a2',11);
  E(c,300,300,232,214,'#d9ccb0');E(c,300,300,222,204,'#8ec4d2');E(c,300,300,186,168,'#83bccc');
  c.strokeStyle='#b8e0e8';c.lineWidth=1.6;for(const [x,y,rx] of [[200,180,26],[380,380,34],[240,400,20],[420,200,22],[160,300,18]]){c.beginPath();c.ellipse(x,y,rx,rx*.35,0,0,Math.PI*2);c.stroke();}
  // Tháp Rùa on its island, the red bridge to the temple island
  E(c,300,280,48,30,'#b9d39c');E(c,300,284,32,19,'#d4c29c');R(c,288,256,24,30,'#ece0c4',4,'#b9a27c',1.5);R(c,284,250,32,10,'#b06f55',4);R(c,292,244,16,8,'#b06f55',3);bush(c,328,292,.6);
  E(c,400,168,40,24,'#b9d39c');R(c,382,152,36,26,'#c46a52',6);R(c,388,157,24,16,'#e0876c',4);
  L(c,452,78,414,154,'#a63a33',17);L(c,452,78,414,154,'#d6564b',12);for(let k=0;k<=1;k+=.2)L(c,452-38*k-6,78+76*k,452-38*k+6,78+76*k,'#f08b7c',1.4);
  pave(c,g.walk,'#efe4cf','#e3d5bb');
  for(const [x,y] of [[96,118],[504,118],[92,452],[508,452]])willow(c,x,y,.9);for(const [x,y] of [[60,884],[540,884],[300,894]])tree(c,x,y,.8);
  for(let x=70;x<=530;x+=115)lamp(c,x,524,lights);
  for(const y of [150,300,450]){lamp(c,26,y,lights);lamp(c,574,y,lights);}
  bench(c,170,532);bench(c,430,532);
  c.strokeStyle='#e2d0b0';c.lineWidth=3;c.beginPath();c.arc(300,720,62,0,Math.PI*2);c.stroke();c.beginPath();c.arc(300,720,34,0,Math.PI*2);c.stroke();
  flowers(c,262,682,76,76,['#f2a3b5','#f6d06b','#fff3e8'],5);
}
function chodem(c,g,lights){
  c.fillStyle='#d3c4b2';c.fillRect(-400,-400,1400,1700);
  pave(c,g.walk,'#e4d6c2','#d6c6ae',36);
  const awn=['#d9534f','#3d8fc6','#e9a23b','#4fa274','#c4568b'],goods=['#e8524a','#f2c14e','#7fbf6a','#f08b3c','#a76fd1','#5aa6d8'];
  for(let i=0;i<5;i++){stall(c,24,46+i*120,120,100,awn[i%5],goods,false,21+i);stall(c,456,46+i*120,120,100,awn[(i+2)%5],goods,true,41+i);}
  for(const y of [110,270,430,590])lanternString(c,148,y,452,y+10,lights,y);
  R(c,190,8,220,30,'#7a3b2e',8);R(c,194,12,212,22,'#b84d39',6);
  c.font='800 15px "Trebuchet MS", sans-serif';c.fillStyle='#ffe7b8';c.textAlign='center';c.textBaseline='middle';c.fillText('CHỢ ĐÊM',300,24);
  for(const x of [40,560])for(const y of [670,860])lamp(c,x,y,lights);
  for(let i=0;i<8;i++)E(c,60+i*70,892,26,12,'#7f9f6f');
}
function congvien(c,g,lights){
  lawn(c,'#c7e2a9','#b9d898',31);
  c.strokeStyle='#ecdfc2';c.lineWidth=44;c.lineCap='round';c.beginPath();c.moveTo(60,900);c.bezierCurveTo(160,720,300,560,250,420);c.bezierCurveTo(210,300,180,160,150,30);c.stroke();
  c.beginPath();c.moveTo(250,600);c.bezierCurveTo(380,640,480,560,600,620);c.stroke();
  c.strokeStyle='#e0d2b2';c.lineWidth=2;c.setLineDash([3,9]);c.beginPath();c.moveTo(60,900);c.bezierCurveTo(160,720,300,560,250,420);c.bezierCurveTo(210,300,180,160,150,30);c.stroke();c.setLineDash([]);
  E(c,440,230,138,160,'#d8cbaf');E(c,440,230,128,150,'#93cbd7');E(c,450,250,96,112,'#86c0ce');
  for(const [x,y,r] of [[400,160,12],[488,300,14],[410,320,10],[500,170,9]]){E(c,x,y,r,r*.8,'#7fb36c');P(c,[[x,y],[x+r,y-3],[x+r,y+3]],'#86c0ce');}
  bloom(c,404,166,4,'#f7c6d6');E(c,470,240,8,6,'#fffaf0');E(c,476,236,3.5,3,'#fffaf0');P(c,[[479,236],[485,237],[479,239]],'#f2b33d');
  E(c,150,290,92,66,'#e7d3b0');c.strokeStyle='#cdb38c';c.lineWidth=2;c.beginPath();c.ellipse(150,290,92,66,0,0,Math.PI*2);c.stroke();
  for(const [x,y,s] of [[340,40,1],[560,50,1.1],[580,400,.9],[330,420,.8],[40,40,.9],[40,500,1],[575,860,1],[300,890,.8]])tree(c,x,y,s);
  for(const [x,y] of [[300,380],[580,320],[560,450]])bush(c,x,y,1);
  flowers(c,470,560,80,56,['#f2a3b5','#f6d06b','#c9a3f2'],7);flowers(c,60,800,70,60,['#ffffff','#f6d06b','#f28c8c'],9);
  R(c,500,800,74,58,'#efd9a6',14,'#d6bb85',2);E(c,520,822,8,5,'#d9534f');E(c,546,836,7,5,'#3d8fc6');
  for(const [x,y] of [[40,250],[290,560],[40,700],[560,700]])lamp(c,x,y,lights);
}
function phodibo(c,g,lights){
  c.fillStyle='#e8dcc6';c.fillRect(-400,-400,1400,1700);
  pave(c,[[0,150,600,900]],'#ece1cd','#e0d2bb',40);
  c.save();c.strokeStyle='#e3d4bb';c.lineWidth=1;for(let k=-900;k<900;k+=40){c.beginPath();c.moveTo(k,150);c.lineTo(k+750,900);c.stroke();}c.restore();
  const roofs=[['#d98b6a','#b86b4e'],['#8fb8c9','#6f98aa'],['#e8c06a','#c9a04e'],['#b7a0d6','#9682b8'],['#9cc79a','#7ca97a'],['#e39aa8','#c47a88']];
  for(let i=0;i<6;i++){roofRow(c,i*100+4,10,92,118,roofs[i][0],roofs[i][1]);R(c,i*100+10,128,80,22,['#d9534f','#3d8fc6','#4fa274','#e9a23b','#c4568b','#7a6ad8'][i],4);
    for(let k=0;k<5;k++)R(c,i*100+12+k*16,130,8,18,'#ffffff55',2);}
  for(const [x,y] of [[225,355],[375,355],[225,505],[375,505]]){R(c,x-22,y-22,44,44,'#c9b79a',8);bush(c,x,y,.9,'#86b97c');}
  E(c,300,430,80,80,'#d3c7b4');E(c,300,430,70,70,'#9fd1de');E(c,300,430,58,58,'#93c8d6');E(c,300,430,28,28,'#d3c7b4');E(c,300,430,18,18,'#b9e3ec');
  for(let a=0;a<8;a++){const x=300+Math.cos(a*Math.PI/4)*44,y=430+Math.sin(a*Math.PI/4)*44;E(c,x,y,4,4,'#eaf7fa');}
  lights.push([300,430,110,'150,215,255']);
  for(const x of [36,564])for(let y=200;y<=860;y+=165)lamp(c,x,y,lights);
  for(const [x,y] of [[160,880],[440,880]])flowers(c,x-40,y-14,80,22,['#f2a3b5','#f6d06b'],x);
}
function cafe(c,g,lights){
  c.fillStyle='#b98d6c';c.fillRect(-400,-400,1400,1700);
  R(c,30,20,540,870,'#ead5b6',18);c.save();c.beginPath();c.roundRect(30,20,540,870,18);c.clip();c.strokeStyle='#dcc3a0';c.lineWidth=1.4;for(let y=20;y<900;y+=26){c.beginPath();c.moveTo(30,y);c.lineTo(570,y);c.stroke();}c.restore();
  R(c,60,40,220,80,'#3d4a44',8,'#7a5a3e',4);c.font='700 15px "Trebuchet MS", sans-serif';c.fillStyle='#f5efe0';c.textAlign='left';c.textBaseline='middle';
  for(const [k,s] of [[0,'Cà phê muối'],[1,'Bạc xỉu'],[2,'Trà đào']])c.fillText(s,78,62+k*22);
  R(c,330,48,90,60,'#cfe7ea',6,'#a0805f',4);R(c,440,48,90,60,'#cfe7ea',6,'#a0805f',4);
  R(c,60,150,480,96,'#8f5f44',12);R(c,66,154,468,30,'#b98762',8);R(c,90,160,46,40,'#7d7d84',6);E(c,113,170,9,6,'#c9c9cf');
  for(const x of [200,240,280])E(c,x,170,9,9,'#fff8ec');E(c,470,170,22,14,'#8cbf7d');bloom(c,470,166,6,'#f6d06b');
  E(c,300,560,150,104,'#d98b6a');E(c,300,560,138,92,'#e39c7c');
  for(const [x,y] of [[70,860],[530,860],[70,300],[530,300]])bush(c,x,y,.9,'#86b97c');
  R(c,250,876,100,14,'#7a5a3e',4);
  lights.push([300,560,140,'255,214,150'],[110,170,60,'255,230,170']);
}
/** 💍 A wedding party (live/wedding.py): the tent and its stage with 囍, the red carpet, the flower gate, four tables. */
function wedding(c,g,lights){
  lawn(c,'#d3e8bd','#c6dfac',53);
  pave(c,g.walk,'#f3ead9','#e9dcc6',34);
  // the tent: a striped canopy over the stage
  R(c,90,30,420,190,'#fbf6ee',18,'#e8d9c4',2);
  c.save();c.beginPath();c.roundRect(90,30,420,190,18);c.clip();for(let x=90;x<510;x+=42){c.fillStyle='#f6dbe1';c.fillRect(x,30,21,190);}c.restore();
  for(let x=90;x<510;x+=28){c.beginPath();c.arc(x+14,220,14,0,Math.PI);c.fillStyle='#f3c9d3';c.fill();}
  L(c,100,48,500,48,'#d8b98a',2);for(let x=110;x<500;x+=26){E(c,x,52,4,4,'#fff3c4');lights.push([x,52,30,'255,214,150']);}
  // the stage and its backdrop
  R(c,165,196,270,116,'#f1d9c6',12,'#d9b79c',2);R(c,180,120,240,80,'#c8463e',10,'#a9352f',2);
  E(c,300,160,30,30,'#f2c14e');c.font='900 36px serif';c.fillStyle='#c8463e';c.textAlign='center';c.textBaseline='middle';c.fillText('囍',300,162);
  for(const x of [206,394]){bloom(c,x,150,10,'#fbe3ea');bloom(c,x,150,5,'#f6a8bd');}
  // the wedding cake and the tower of glasses on the stage, the feast table by the tent
  R(c,176,252,40,26,'#fffdf8',6,'#ecdccb',1.5);c.font='26px serif';c.textAlign='center';c.textBaseline='middle';c.fillText('🎂',196,248);
  c.font='18px serif';c.fillText('🥂',196,286);
  R(c,40,236,40,62,'#fffdf8',6,'#ecdccb',1.5);c.font='14px serif';for(const [y,e] of [[250,'🍤'],[268,'🍮'],[286,'🍉']])c.fillText(e,60,y);
  // the red carpet from the gate to the stage, petals on it
  R(c,262,300,76,560,'#c8463e',4);L(c,264,300,264,860,'#e8b44f',2);L(c,336,300,336,860,'#e8b44f',2);
  const r=seeded(91);for(let i=0;i<26;i++)E(c,270+r()*60,320+r()*520,2.6,1.8,['#fbe3ea','#f6a8bd','#fff'][i%3]);
  // flower stands along the carpet and heart balloons
  for(let y=380;y<=780;y+=130)for(const x of [244,356]){R(c,x-5,y,10,26,'#d8c3a5',3);bloom(c,x,y-4,9,'#f6a8bd');bloom(c,x,y-4,4,'#fff');}
  for(const [x,y,col] of [[60,330,'#f28c9e'],[540,330,'#f7b6c2'],[52,860,'#f6a8bd'],[548,860,'#f28c9e']]){L(c,x,y+40,x,y+6,'#b9a690',1.2);heart(c,x,y,.9,col);}
  // the flower gate at the entrance
  c.lineCap='round';c.strokeStyle='#ffffff';c.lineWidth=14;c.beginPath();c.arc(300,872,78,Math.PI,0);c.stroke();
  for(let a=Math.PI;a<=Math.PI*2+.01;a+=Math.PI/11){const x=300+Math.cos(a)*78,y=872+Math.sin(a)*78;bloom(c,x,y,8,['#f6a8bd','#fbe3ea','#f28c9e'][Math.round(a*7)%3]);}
  R(c,214,850,14,40,'#e9e0d2',4);R(c,372,850,14,40,'#e9e0d2',4);
  for(const [x,y] of [[40,560],[560,560],[40,760],[560,760]])lights.push([x,y,60,'255,206,140']);
}
const DRAW={boho,chodem,congvien,phodibo,cafe,wedding};
/** Plastic street tables at the market, wooden ones elsewhere. */
export function paintTable(c,t,place){
  if(place==='wedding'){   // white cloth, chairs with bows, a vase of pink flowers
    for(const [x,y] of t.seats){E(c,x+2,y+3,13,6,'#00000014');E(c,x,y,12,12,'#f4ebe1');E(c,x,y-7,6,4,'#f3a5b8');}
    E(c,t.x+3,t.y+6,36,15,'#0000001c');E(c,t.x,t.y,33,27,'#fffdf8');c.strokeStyle='#ecdccb';c.lineWidth=2;c.beginPath();c.ellipse(t.x,t.y,33,27,0,0,Math.PI*2);c.stroke();
    bloom(c,t.x,t.y-4,7,'#f6a8bd');bloom(c,t.x,t.y-4,3,'#fff');
    c.font='11px serif';c.textAlign='center';c.textBaseline='middle';   // the cỗ: gà luộc, tôm, nem, canh, xôi gấc
    for(const [dx,dy,e] of [[-17,-6,'🍗'],[16,-7,'🦐'],[-15,9,'🥟'],[15,9,'🍲'],[0,13,'🍚']])c.fillText(e,t.x+dx,t.y+dy);
    return;
  }
  const plastic=place==='chodem',top=plastic?'#5da4d6':place==='cafe'?'#9a6b4f':'#c9a27a',stool=plastic?'#d9534f':place==='cafe'?'#7d5a42':'#a7845f';
  for(const [x,y] of t.seats){E(c,x+2,y+3,13,6,'#00000018');E(c,x,y,12,12,stool);E(c,x-3,y-3,4,4,'#ffffff40');}
  E(c,t.x+3,t.y+6,34,14,'#00000022');E(c,t.x,t.y,31,26,top);E(c,t.x,t.y-3,26,20,plastic?'#79b6e0':place==='cafe'?'#b88762':'#dcb98f');
  if(!plastic){E(c,t.x-6,t.y-5,6,4,'#fff8ec');E(c,t.x+8,t.y-1,5,3.5,'#fff8ec');}else{E(c,t.x-5,t.y-4,5,5,'#f2c14e99');E(c,t.x+7,t.y,4.5,4.5,'#ffffffaa');}
}
/** The whole static place (ground, decor, tables, the bench spot) in world units; night: dim + lights. */
export function paintPlace(c,place,geo,night){
  const lights=[];(DRAW[place]||boho)(c,geo,lights);
  for(const t of geo.tables)paintTable(c,t,place);
  const b=geo.spots?.bench;if(b)bench(c,b[0],b[1]);
  const dim=place==='chodem'?(night?.6:.3):night?.56:0;
  if(dim){c.save();c.fillStyle=`rgba(14,16,40,${dim})`;c.fillRect(-400,-400,1400,1700);c.globalCompositeOperation='lighter';
    for(const [x,y,r,rgb] of lights){const gr=c.createRadialGradient(x,y,0,x,y,r);gr.addColorStop(0,`rgba(${rgb},.5)`);gr.addColorStop(.35,`rgba(${rgb},.2)`);gr.addColorStop(1,`rgba(${rgb},0)`);
      c.fillStyle=gr;c.fillRect(x-r,y-r,r*2,r*2);}
    c.restore();}
  return lights.length;
}
/** The edge colour around the 600×900 world (letterboxing on wide or tall screens). */
export const EDGE={boho:'#cfe3b1',chodem:'#d3c4b2',congvien:'#c7e2a9',phodibo:'#e8dcc6',cafe:'#b98d6c',wedding:'#d3e8bd'};

/* ---- happenings (drawn every frame, world units) ---- */
export function paintLion(c,x,y,t,rtl){
  c.save();c.translate(x,y);if(rtl)c.scale(-1,1);
  for(let i=4;i>=1;i--){const wob=Math.sin(t*9-i*.8)*6;E(c,-i*22,wob,20,15,i%2?'#d8433a':'#f2c14e');}
  for(const [dx,ph] of [[-70,0],[-30,1.6]]){const s=Math.sin(t*12+ph)*5;E(c,dx+s,14,5,4,'#3a2f2a');E(c,dx-s,-14,5,4,'#3a2f2a');}
  for(let a=0;a<12;a++){const an=a/12*Math.PI*2;E(c,8+Math.cos(an)*22,Math.sin(an)*20,8,8,a%2?'#f2c14e':'#fff2c6');}
  E(c,8,0,22,20,'#d8433a');E(c,16,-7,5,5,'#fff');E(c,16,7,5,5,'#fff');E(c,17,-7,2.5,2.5,'#222');E(c,17,7,2.5,2.5,'#222');
  R(c,22,-6,8,12,'#f2c14e',3);E(c,0,0,5,5,'#ffe08a');
  c.restore();
  c.font='22px serif';c.textAlign='center';c.textBaseline='middle';c.fillText('🥁',x+(rtl?60:-120),y+4+Math.sin(t*14)*2);
}
export function paintVendor(c,x,y,who,t){
  E(c,x+4,y+16,34,12,'#00000022');R(c,x-30,y-14,60,32,'#c98f5a',8);E(c,x-22,y+18,7,7,'#3a2f2a');E(c,x+22,y+18,7,7,'#3a2f2a');
  E(c,x,y-16,34,22,'#f2f2ec');for(let a=0;a<8;a+=2){c.beginPath();c.moveTo(x,y-16);c.ellipse(x,y-16,34,22,0,a*Math.PI/4,(a+1)*Math.PI/4);c.closePath();c.fillStyle='#d9534f';c.fill();}
  c.font='26px serif';c.textAlign='center';c.textBaseline='middle';c.fillText(who,x,y-18+Math.sin(t*6)*2);
}
export function paintEnvelope(c,x,y,t,left){
  const bob=Math.sin(t*4)*4,glow=c.createRadialGradient(x,y+bob,0,x,y+bob,44);glow.addColorStop(0,'rgba(255,200,90,.55)');glow.addColorStop(1,'rgba(255,200,90,0)');
  c.fillStyle=glow;c.fillRect(x-44,y-44+bob,88,88);
  c.save();c.translate(x,y+bob);c.rotate(Math.sin(t*2.4)*.12);R(c,-15,-20,30,40,'#d8322e',5,'#a3201d',1.5);P(c,[[-15,-20],[15,-20],[0,-6]],'#e9534c');E(c,0,-4,7,7,'#f5c542');E(c,0,-4,4,4,'#d8322e');c.restore();
  if(left!=null){c.strokeStyle='#f5c542';c.lineWidth=3;c.lineCap='round';c.beginPath();c.arc(x,y+bob,26,-Math.PI/2,-Math.PI/2+Math.PI*2*Math.max(0,Math.min(1,left)));c.stroke();}
}
