/** Lane scene (kind `lane`): the street trades at work outside. One frame of the
 * neighbourhood (old tube houses, overhead wires, a pavement of tiles, the road)
 * dressed by career:
 *   fruit    Dì Tư's fruit stall at the mouth of the market: a long table of
 *            bamboo baskets under an umbrella, the round spring scale, fruit crates;
 *   garbage  the rubbish round at dusk: the three-compartment hand cart, bags by
 *            the door in their sorting colours, the red box and the collection time;
 *   drain    chú Hai's call-out: the motorbike with its tool box, an open manhole
 *            behind cones, a coil of drain snake and the price list;
 *   ice_cream cô Hiền's ice-cream corner at the primary-school gate under a flame
 *            tree: the chest freezer with its glass lid, cones and coconuts, topping
 *            jars, the digital scale and the little stools.
 * The footprints are the sidewalk scene's (the same walkable street plan), so the
 * props below stand where that plan keeps the floor clear. */
import {R,E,L,T,P,fit,streetBoard} from './kit.js';
import {PLAN} from './sidewalk.js';

const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,curb:668,road:680,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,curb:800,road:812,sign:[135,30,430,104]}};
const WOOD='#b88b62',WOOD_D='#8f6746';
const data=w=>w.c?.data||{};
const dusk=w=>w.career==='garbage';

/* ------------------------------------------------------------ backdrop */
function sky(c,w,f){const g=c.createLinearGradient(0,f.y,0,f.base),rain=data(w).mod?.id==='rain';
  if(dusk(w)){g.addColorStop(0,'#3d4a6d');g.addColorStop(1,'#c98e6c');}
  else{g.addColorStop(0,rain?'#b8c4cc':'#cfe6e4');g.addColorStop(1,rain?'#dfe2dc':'#fbf0d8');}
  c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  const port=f===F.port,sx=port?610:1040,sy=port?180:172;
  if(dusk(w)){E(c,sx,sy,22,22,'#fbe7b5');E(c,sx+8,sy-6,20,20,'#56648a');}else if(!rain)E(c,sx,sy,26,26,'#fff3c4');}
function tube(c,x,top,wd,base,col,lit){R(c,x,top,wd,base-top+2,col,6,'#d6b394',2);R(c,x-6,top-12,wd+12,16,'#d98f73',7,'#b8765d',1.5);
  const n=Math.max(1,Math.floor(wd/90));for(let i=0;i<n;i++){const cx=x+wd*(i+.5)/n;R(c,cx-20,top+26,40,48,lit?'#ffd98a':'#cfe7ea',4,'#d6b394',1.5);R(c,cx-37,top+24,14,52,'#8fbfa6',3);R(c,cx+23,top+24,14,52,'#8fbfa6',3);}}
function wires(c,x0,x1,y0,y1,sag){c.strokeStyle='#8f7f7299';c.lineWidth=1.6;for(const [dy,k] of [[14,1],[30,.8]]){c.beginPath();c.moveTo(x0,y0+dy);c.quadraticCurveTo((x0+x1)/2,Math.max(y0,y1)+dy+sag*k,x1,y1+dy);c.stroke();}}
function pole(c,x,base,top){L(c,x,base,x,top,'#b7a391',7);L(c,x-20,top+14,x+20,top+14,'#a69280',4);}
function pavement(c,f){const {base,curb,road}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,curb-base,'#e9dcc6',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,curb-base);c.clip();const tw=f===F.port?46:52,th=f===F.port?46:40;
  for(let y=base,row=0;y<curb;y+=th,row++)for(let x=f.x;x<f.x+f.w;x+=tw){c.fillStyle=((x/tw|0)+row)%2?'#e2d1b6':'#eadfc9';c.fillRect(x+1.5,y+1.5,tw-3,th-3);}
  c.restore();R(c,f.x,curb,f.w,road-curb,'#c9c3b8',0);L(c,f.x,curb,f.x+f.w,curb,'#a79f93',2);R(c,f.x,road,f.w,bottom-road,'#9fa7aa',0);
  for(let x=f.x+30;x<f.x+f.w;x+=120)R(c,x,road+(bottom-road)/2-2,56,4,'#f1e7c8',2);}
/** The market's arched gate behind the fruit stall. */
function marketGate(c,x,base,wd,port){const top=base-(port?150:176);R(c,x,top+30,wd,base-top-30,'#f3e3c1',4,'#d6b394',2);
  P(c,[[x-12,top+34],[x+wd/2,top-6],[x+wd+12,top+34]],'#c9594a');R(c,x+wd/2-70,top+8,140,26,'#fff4dc',8,'#c9a06a',2);
  T(c,'CHỢ MÂY',x+wd/2,top+21,port?14:16,'#8a3f2c',800);R(c,x+wd/2-46,top+52,92,base-top-52,'#6d5a48',6);
  for(let i=0;i<6;i++){const a=x+i*wd/6;P(c,[[a,top+34],[a+wd/6,top+34],[a+wd/6+2,top+52],[a-2,top+52]],i%2?'#f2b134':'#fff4dc');}}
/** The street lamp that lights the rubbish round. */
function lamp(c,x,base,top){L(c,x,base,x,top,'#4f5560',6);L(c,x,top,x+26,top-2,'#4f5560',4);E(c,x+28,top+6,9,5,'#ffe7a8');
  const g=c.createRadialGradient(x+28,top+10,0,x+28,top+10,120);g.addColorStop(0,'rgba(255,221,140,.45)');g.addColorStop(1,'rgba(255,221,140,0)');c.fillStyle=g;c.fillRect(x-100,top-100,256,300);}

/** The primary-school gate and the flame tree behind the ice-cream corner. */
function schoolGate(c,x,base,wd,port){const top=base-(port?160:184);R(c,x,top+40,22,base-top-40,'#e8d8bf',3,'#c9a06a',2);R(c,x+wd-22,top+40,22,base-top-40,'#e8d8bf',3,'#c9a06a',2);
  for(let i=0;i<9;i++)L(c,x+30+i*(wd-60)/8,top+70,x+30+i*(wd-60)/8,base,'#5b6b78',3);L(c,x+22,top+70,x+wd-22,top+70,'#5b6b78',4);L(c,x+22,base-30,x+wd-22,base-30,'#5b6b78',3);
  R(c,x+wd/2-90,top+30,180,30,'#2f6f9f',6,'#22557a',2);T(c,'TRƯỜNG TIỂU HỌC MÂY',x+wd/2,top+45,port?11:12,'#fff',800);
  // The flame tree: a trunk and a red canopy.
  const tx=x+wd+(port?-10:30);L(c,tx,base,tx-6,top-10,'#7a5a3c',port?10:12);
  for(const [dx,dy,r] of [[-60,-30,46],[0,-50,56],[56,-26,44],[-20,-6,40],[30,4,36]])E(c,tx+dx,top+dy,r,r*.7,'#d94a3a');
  for(const [dx,dy] of [[-40,-40],[10,-60],[50,-30],[-10,-14],[24,-8]])E(c,tx+dx,top+dy,10,6,'#f28a5a');}
function freezer(c,w,x0,x1,fy,port){const W=x1-x0,h=port?66:58,top=fy-h,lid=!!data(w).fz?.lid;E(c,(x0+x1)/2,fy+3,W/2+8,7,'#6b584420');
  R(c,x0,top,W,h,'#f7fbfd',8,'#9fb6c3',2);R(c,x0+8,top+h-18,W-16,8,'#d5e7f0',3);
  if(lid){P(c,[[x0+6,top],[x1-6,top],[x1-18,top-30],[x0+18,top-30]],'#cfeaf7cc');L(c,x0+18,top-30,x1-18,top-30,'#9fb6c3',2);}
  else R(c,x0+6,top-6,W-12,10,'#cfeaf7',4,'#9fb6c3',1.5);
  const cols=['#fff4e0','#f7a8b8','#6b4a3a','#9ccf7a','#b48ad9','#fff9e8'];for(let i=0;i<6;i++)E(c,x0+14+i*(W-28)/5,top+12,(W-40)/14,6,cols[i]);
  const label=w.words().counter;T(c,label,(x0+x1)/2,top+h/2+6,fit(c,label,W-20,port?13:11),'#2f6f9f',800);}
function cones(c,x0,x1,fy){const W=x1-x0;for(let i=0;i<4;i++){const x=x0+10+i*(W-20)/3;P(c,[[x-8,fy-40],[x+8,fy-40],[x,fy-8]],'#d9a45a');E(c,x,fy-42,9,7,['#f7a8b8','#fff4e0','#6b4a3a','#9ccf7a'][i]);}
  R(c,x0+4,fy-8,W-8,8,WOOD,3,WOOD_D,1);}
function jars(c,x0,x1,fy){const W=x1-x0,cols=['#c98a4a','#ffffff','#5a3a2a','#e8c27a'];for(let i=0;i<4;i++){const x=x0+8+i*(W-16)/4;R(c,x,fy-30,(W-16)/4-6,28,'#e9f4f8',4,'#9fb6c3',1.5);R(c,x+3,fy-18,(W-16)/4-12,14,cols[i],3);R(c,x-1,fy-34,(W-16)/4-4,6,'#e0679a',2);}}
function stools(c,x0,x1,fy){for(let i=0;i<2;i++){const x=x0+12+i*(x1-x0-24);R(c,x-14,fy-26,28,6,'#2f6f9f',3);L(c,x-10,fy-20,x-12,fy,'#2f6f9f',3);L(c,x+10,fy-20,x+12,fy,'#2f6f9f',3);}}
function lcdScale(c,x0,x1,fy){const W=x1-x0;R(c,x0+8,fy-34,W-16,30,'#d9dee3',5,'#9aa4a8',1.5);R(c,x0+14,fy-30,(W-28)*.55,14,'#1e3b2c',3);T(c,'65 g',x0+14+(W-28)*.27,fy-23,9,'#9cf2b7',800);R(c,x0+12,fy-40,W-24,6,'#c9d3db',2);}

/* ------------------------------------------------------------ fruit */
const FRUIT_COL={xoai:'#f2b134',chuoi:'#f5d547',bo:'#5e8f3a',cam:'#f08a24',thanh_long:'#d9447a',nho:'#9bc45a',buoi:'#7fb04a'};
function fruitPile(c,x,y,col,n=5,s=1){for(let i=0;i<n;i++)E(c,x+(i-(n-1)/2)*9*s,y-4*s-(i%2)*6*s,7*s,6*s,col);}
function basket(c,x,y,wd,col){P(c,[[x-wd/2,y-16],[x+wd/2,y-16],[x+wd/2-6,y],[x-wd/2+6,y]],'#c49a55');for(let i=0;i<4;i++)L(c,x-wd/2+4,y-13+i*4,x+wd/2-4,y-13+i*4,'#a67c3c',1);fruitPile(c,x,y-14,col,Math.max(3,wd/12|0));}
function stallTable(c,w,x0,x1,fy,port){const W=x1-x0,h=port?50:44,top=fy-h;E(c,(x0+x1)/2,fy+3,W/2+10,8,'#6b584420');
  L(c,x0+10,top+10,x0+8,fy,WOOD_D,5);L(c,x1-10,top+10,x1-8,fy,WOOD_D,5);R(c,x0,top,W,12,WOOD,4,WOOD_D,2);
  const cols=Object.values(FRUIT_COL);for(let i=0;i<4;i++)basket(c,x0+W*(i+.5)/5,top,W/6,cols[i]);
  // The round spring scale at the end of the table.
  const sx=x1-W*.1;R(c,sx-18,top-30,36,30,'#3f7fbf',6,'#2d5f91',1.5);E(c,sx,top-18,12,12,'#fffdf6');L(c,sx,top-18,sx+6,top-26,'#d8342a',2);R(c,sx-20,top-36,40,6,'#c9d3db',2);
  const label=w.words().counter;T(c,label,(x0+x1)/2,top+26,fit(c,label,W-20,port?14:12),'#5a3f2c',800);}
function umbrella(c,cx,fy,s,[a1,a2]=['#e0892b','#fff1dc']){const top=fy-190*s,rw=130*s;L(c,cx,fy,cx,top,'#9aa4a8',5*s);
  for(let i=0;i<6;i++){const a=cx-rw+i*rw/3,b=a+rw/6;P(c,[[a,top+44*s],[cx,top],[b,top+44*s]],i%2?a1:a2);}
  for(let i=0;i<7;i++)E(c,cx-rw+i*rw/3,top+44*s,rw/6,6*s,i%2?a1:a2);}
function crates(c,x0,x1,fy){const W=x1-x0;for(let i=0;i<2;i++){const y=fy-i*26;R(c,x0+4+i*6,y-26,W-8-i*12,24,'#d9b97a',3,'#a67c3c',1.5);for(let k=1;k<4;k++)L(c,x0+4+i*6+k*(W-8-i*12)/4,y-26,x0+4+i*6+k*(W-8-i*12)/4,y-2,'#a67c3c',1);}
  fruitPile(c,(x0+x1)/2,fy-52,'#f08a24',5);}
function priceSign(c,cx,fy,port,lines){const bw=port?118:108,bh=port?56:50,top=fy-bh-22;L(c,cx-bw/2+12,top+bh,cx-bw/2+4,fy,WOOD_D,4);L(c,cx+bw/2-12,top+bh,cx+bw/2-4,fy,WOOD_D,4);
  R(c,cx-bw/2,top,bw,bh,'#3d4a44',8,WOOD_D,3);T(c,lines[0],cx,top+bh/2-8,fit(c,lines[0],bw-14,port?14:12,800),'#fdf7e8',800);T(c,lines[1],cx,top+bh-12,port?11:10,'#f3d98a',700);}

/* ------------------------------------------------------------ garbage */
function sack(c,x,y,col,s=1){E(c,x,y-12*s,12*s,13*s,col);E(c,x,y-26*s,4*s,4*s,col);E(c,x-3*s,y-16*s,4*s,5*s,'#ffffff22');}
function handCart(c,w,x0,x1,fy,port){const W=x1-x0,h=port?64:56,top=fy-h,cart=data(w).cart||{},cap=data(w).cap||{huu_co:8,tai_che:8,con_lai:10};
  E(c,(x0+x1)/2,fy+3,W/2+8,7,'#6b584420');E(c,x0+22,fy-6,12,12,'#3b3b3b');E(c,x1-22,fy-6,12,12,'#3b3b3b');
  const cols=[['huu_co','#3f9a55'],['tai_che','#e8b923'],['con_lai','#4a4a4a']],cw=(W-12)/3;
  cols.forEach(([k,col],i)=>{const x=x0+6+i*cw,full=Math.min(1,(cart[k]?.n||0)/(cap[k]||8));R(c,x,top,cw-4,h-12,col,5,'#00000033',1.5);
    if(full)R(c,x+3,top-6*full,cw-10,8,'#00000033',3);R(c,x+4,top+h-26,cw-12,6,'#ffffff55',2);});
  L(c,x1,top+8,x1+26,top-18,'#6b6b6b',4);R(c,x0+W*.3,top+h-30,W*.4,6,'#f28c28',2);
  const label=w.words().counter;T(c,label,(x0+x1)/2,fy+14,fit(c,label,W,port?13:11),'#e9e4d8',800);}
function redBox(c,x0,x1,fy){const W=x1-x0;R(c,x0+6,fy-36,W-12,34,'#d0342c',6,'#8f231d',2);T(c,'NGUY HẠI',(x0+x1)/2,fy-19,10,'#fff',800);R(c,x0+2,fy-42,W-4,8,'#b52b24',3);}
function bagPile(c,w,x0,x1,fy){const cols=['#3f9a55','#e8b923','#3b3b3b','#3f9a55','#3b3b3b'],n=w.c?.open?5:3;for(let i=0;i<n;i++)sack(c,x0+14+i*(x1-x0-28)/Math.max(1,n-1),fy-(i%2)*6,cols[i],.95);}

/* ------------------------------------------------------------ drain */
function motorbike(c,w,x0,x1,fy,port){const W=x1-x0,top=fy-(port?60:54),bike=(data(w).bike||[]).length;
  E(c,(x0+x1)/2,fy+3,W/2,7,'#6b584420');E(c,x0+24,fy-14,16,16,'#2f3a45');E(c,x0+24,fy-14,7,7,'#9aa4a8');E(c,x1-24,fy-14,16,16,'#2f3a45');E(c,x1-24,fy-14,7,7,'#9aa4a8');
  P(c,[[x0+24,fy-20],[x0+W*.45,top+18],[x1-40,top+22],[x1-24,fy-20]],'#3f6f8f');R(c,x0+W*.35,top+8,W*.25,10,'#2f3a45',4);L(c,x1-34,top+16,x1-26,top-6,'#6b6b6b',4);
  R(c,x0+6,top-6,W*.34,30,'#f2c230',4,'#b8921d',2);for(let i=0;i<Math.min(5,bike);i++)E(c,x0+14+i*10,top-10,4,4,'#3f6f8f');
  L(c,x0+10,top+6,x0+W*.34,top+6,'#222',2);
  const label=w.words().counter;T(c,label,(x0+x1)/2,fy+14,fit(c,label,W,port?13:11),'#5a3f2c',800);}
function manhole(c,x0,x1,fy,open){const cx=(x0+x1)/2;E(c,cx,fy-6,(x1-x0)/2+8,9,open?'#1d1d1d':'#6b6b6b');E(c,cx,fy-7,(x1-x0)/2+2,6,open?'#3a3a3a':'#7d7d7d');
  for(const dx of [-(x1-x0)/2-16,(x1-x0)/2+16]){P(c,[[cx+dx-9,fy],[cx+dx,fy-30],[cx+dx+9,fy]],'#f28c28');R(c,cx+dx-8,fy-18,16,5,'#fff',2);}}
function coil(c,x0,x1,fy){const cx=(x0+x1)/2;for(let i=0;i<4;i++){c.beginPath();c.ellipse(cx,fy-18,22-i*4,12-i*2,0,0,Math.PI*2);c.strokeStyle='#8a97a3';c.lineWidth=3;c.stroke();}L(c,cx+20,fy-18,x1,fy-4,'#8a97a3',3);}

/* ------------------------------------------------------------ rooms */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land,car=w.career;
  if(port){E(c,350,862,320,22,'#cba88d22');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#c9a27e',33);}
  else{E(c,600,742,520,22,'#cba88d22');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#c9a27e',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  const lit=dusk(w);
  if(port){pole(c,40,f.base,200);pole(c,664,f.base,214);wires(c,40,664,200,214,30);tube(c,24,250,150,f.base,'#f3dfb0',lit);tube(c,470,236,210,f.base,'#f2d2c4',lit);
    if(car==='fruit')marketGate(c,190,f.base,260,true);else if(car==='ice_cream')schoolGate(c,190,f.base,260,true);else tube(c,190,226,260,f.base,'#d6e8d8',lit);}
  else{pole(c,96,f.base,170);pole(c,1108,f.base,186);wires(c,96,1108,170,186,40);tube(c,78,226,230,f.base,'#f3dfb0',lit);tube(c,650,216,240,f.base,'#f2d2c4',lit);tube(c,900,240,230,f.base,'#d6e8d8',lit);
    if(car==='fruit')marketGate(c,330,f.base,300,false);else if(car==='ice_cream')schoolGate(c,330,f.base,300,false);else tube(c,330,206,300,f.base,'#efe3cf',lit);}
  pavement(c,f);
  if(car==='garbage')lamp(c,port?600:470,f.base+10,f.base-(port?230:250));
  streetBoard(c,p,port?30:1013,port?282:322,port?1.6:1);
  c.restore();
  const title=p.title||'',[sx,sy,sw,sh]=f.sign;R(c,sx-5,sy+7,sw+10,sh,'#8f6746',26);R(c,sx,sy,sw,sh,'#fff4dc',24,'#c9a06a',3);
  T(c,title,sx+sw/2,sy+40,fit(c,title,sw-60,30,800),'#5a3f2c',800);T(c,p.sub||'',sx+sw/2,sy+sh-26,fit(c,p.sub||'',sw-60,13),'#7b5b44');
  E(c,sx+36,sy+sh/2,14,14,p.primary||'#e0892b');E(c,sx+sw-36,sy+sh/2,14,14,p.primary||'#e0892b');}

/* ------------------------------------------------------------ props */
function props(w){const c=w.ctx,port=w.isPortrait(),b=w.plan().blocks,out=[],car=w.career,d=data(w);
  const [wh,wb,co,ev,fi,dr]=b,mid=r=>(r[0]+r[2])/2;
  if(car==='fruit'){
    out.push([wh[3],()=>crates(c,wh[0],wh[2],wh[3])]);
    out.push([wb[3],()=>{for(let i=0;i<3;i++)basket(c,wb[0]+(i+.5)*(wb[2]-wb[0])/3,wb[3],(wb[2]-wb[0])/3.4,['#f2b134','#9bc45a','#f08a24'][i]);}]);
    out.push([co[3]-1,()=>{if(d.stall?.cover==='bat'){R(c,co[0]-20,co[3]-150,co[2]-co[0]+40,10,'#3f7fbf',4);L(c,co[0]-16,co[3]-140,co[0]-16,co[3],'#9aa4a8',4);L(c,co[2]+16,co[3]-140,co[2]+16,co[3],'#9aa4a8',4);}
      else umbrella(c,mid(co)+(port?-30:-50),co[3],port?.9:1);}]);
    out.push([co[3],()=>stallTable(c,w,co[0],co[2],co[3],port)]);
    out.push([ev[3],()=>basket(c,mid(ev),ev[3],ev[2]-ev[0]+10,'#d9447a')]);
    out.push([fi[3],()=>{R(c,fi[0]+14,fi[3]-30,fi[2]-fi[0]-28,28,'#8fbfa6',4,'#5f8f76',1.5);T(c,w.words().ledger,mid(fi),fi[3]-16,fit(c,w.words().ledger,fi[2]-fi[0]-30,10),'#fff',800);}]);
    out.push([dr[3],()=>priceSign(c,mid(dr),dr[3],port,w.c?.open?['XOÀI CÁT 14 XU/KÝ','cân đủ, trừ bì']:[w.words().closed_sign,'mai mời ghé'])]);
  }else if(car==='ice_cream'){
    out.push([wh[3],()=>cones(c,wh[0],wh[2],wh[3])]);
    out.push([wb[3],()=>jars(c,wb[0],wb[2],wb[3])]);
    out.push([co[3]-1,()=>umbrella(c,mid(co)+(port?-30:-50),co[3],port?.9:1,['#e0679a','#fff1f6'])]);
    out.push([co[3],()=>freezer(c,w,co[0],co[2],co[3],port)]);
    out.push([ev[3],()=>stools(c,ev[0],ev[2],ev[3])]);
    out.push([fi[3],()=>lcdScale(c,fi[0],fi[2],fi[3])]);
    out.push([dr[3],()=>priceSign(c,mid(dr),dr[3],port,w.c?.open?['KEM DỪA 6 XU/VIÊN','viên nào cũng lên cân']:[w.words().closed_sign,'chiều mai mời ghé'])]);
  }else if(car==='garbage'){
    out.push([wh[3],()=>{for(const [i,col] of [[0,'#3f9a55'],[1,'#e8b923'],[2,'#4a4a4a']])R(c,wh[0]+i*(wh[2]-wh[0])/3,wh[3]-44,(wh[2]-wh[0])/3-4,44,col,5,'#00000033',1.5);}]);
    out.push([wb[3],()=>bagPile(c,w,wb[0],wb[2],wb[3])]);
    out.push([co[3],()=>handCart(c,w,co[0],co[2],co[3],port)]);
    out.push([ev[3],()=>{R(c,ev[0]-6,ev[3]-60,ev[2]-ev[0]+12,40,'#fffaf0',4,'#8f6746',2);T(c,'PHÂN LOẠI',mid(ev),ev[3]-46,9,'#2f8f5b',800);T(c,'🟢🟡⚫',mid(ev),ev[3]-30,10,'#000',400);L(c,mid(ev),ev[3]-20,mid(ev),ev[3],WOOD_D,3);}]);
    out.push([fi[3],()=>redBox(c,fi[0],fi[2],fi[3])]);
    out.push([dr[3],()=>priceSign(c,mid(dr),dr[3],port,['ĐỔ RÁC 18:00–19:30','đúng giờ, đúng túi'])]);
  }else{
    out.push([wh[3],()=>{R(c,wh[0]+6,wh[3]-40,wh[2]-wh[0]-12,38,'#f2c230',5,'#b8921d',2);for(let i=0;i<3;i++)L(c,wh[0]+14,wh[3]-30+i*9,wh[2]-14,wh[3]-30+i*9,'#b8921d',1.5);T(c,'ĐỒ NGHỀ',mid(wh),wh[3]-48,9,'#5a3f2c',800);}]);
    out.push([wb[3],()=>coil(c,wb[0],wb[2],wb[3])]);
    out.push([co[3],()=>motorbike(c,w,co[0],co[2],co[3],port)]);
    out.push([ev[3],()=>manhole(c,ev[0],ev[2],ev[3],!!w.c?.open)]);
    out.push([fi[3],()=>{R(c,fi[0]+8,fi[3]-54,fi[2]-fi[0]-16,46,'#fffaf0',4,'#3f6f8f',2);for(let i=0;i<4;i++)L(c,fi[0]+16,fi[3]-44+i*9,fi[2]-16,fi[3]-44+i*9,'#9aa9b5',1.5);T(c,'BẢNG GIÁ',mid(fi),fi[3]-60,9,'#3f6f8f',800);}]);
    out.push([dr[3],()=>priceSign(c,mid(dr),dr[3],port,w.c?.open?['THÔNG CỐNG','báo giá trước khi làm']:[w.words().closed_sign,'gọi là tới'])]);
  }
  return out;
}

export default {
  id:'lane',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
};
