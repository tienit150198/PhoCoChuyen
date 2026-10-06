/** Rig scene (kind `rig`, career oil): the main deck of giàn Hải Âu on mỏ Sao Biển. The sea and the sky behind (the
 * day's weather from the career's public data: room.data.mod), the platform on its legs with the derrick, the crane, the
 * flare boom with its flame, the helideck with its H and the orange lifeboat on its davits, the grey deck plates with a
 * yellow walkway, and on deck: the LOTO cabinet with the red locks (warehouse), the pump skid with its valves (workbench),
 * the permit desk under the control-room window (counter), the gauge panel with the gas detectors (evidence), the POB
 * board with the T-cards (finance) and the A-frame sign at the stairs (door). Footprints follow the airfield's street
 * plan (see shop.js for the PLAN schema), without its doors into the terminal. */
import {R,E,L,T,P,fit,heart,streetBoard} from './kit.js';
import {PLAN as AIRFIELD} from './airfield.js';

const strip=v=>({...v,spots:Object.fromEntries(Object.entries(v.spots).filter(([k])=>!k.startsWith('go:')))});
export const PLAN={land:strip(AIRFIELD.land),port:strip(AIRFIELD.port)};

const SEA='#2f88a8',SEA_D='#1f5f7a',STEEL='#9aa7b1',STEEL_D='#6f7d88',DECK='#c3c9cd',YEL='#f2c14e',ORANGE='#e07a2f',RED='#d9534f',WHITE='#f8fafc',DARK='#26303b';
const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,curb:668,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,curb:800,sign:[135,30,430,104]}};
const mod=w=>w.c?.data?.mod?.id||'calm';

/* ------------------------------------------------------------ the sea and the sky */
function backdrop(c,w,f){const m=mod(w),storm=m==='typhoon',grey=storm||m==='monsoon',fog=m==='fog';
  const g=c.createLinearGradient(0,f.y,0,f.base);g.addColorStop(0,storm?'#8d99a3':grey?'#b7c3cc':fog?'#dfe5e8':'#bfe0f2');g.addColorStop(1,storm?'#c9cfd3':'#eef3f1');
  c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  const port=f===F.port,hz=f.y+(f.base-f.y)*.62;
  if(!grey&&!fog){E(c,port?600:1040,port?190:178,28,28,'#fff3c4');}
  const t=w.reduced?0:w.time,drift=Math.sin(t*.07)*18;
  for(const [x,y,s] of port?[[120,196,.8],[420,176,.6]]:[[210,172,1],[700,160,.8]]){const col=grey?'#97a3adcc':'#ffffffcc';E(c,x+drift,y,34*s,14*s,col);E(c,x+drift-24*s,y+5*s,22*s,11*s,col);E(c,x+drift+26*s,y+3*s,24*s,12*s,col);}
  const sg=c.createLinearGradient(0,hz,0,f.base);sg.addColorStop(0,storm?'#5d7380':SEA);sg.addColorStop(1,SEA_D);c.fillStyle=sg;c.fillRect(f.x,hz,f.w,f.base-hz);
  const amp=storm?7:m==='swell'?5:2.5;c.strokeStyle='#ffffff55';c.lineWidth=2;
  for(let row=0;row<4;row++){const y=hz+12+row*(f.base-hz-12)/4;c.beginPath();for(let x=f.x;x<=f.x+f.w;x+=12){const yy=y+Math.sin(x*.035+t*1.2+row)*amp;x===f.x?c.moveTo(x,yy):c.lineTo(x,yy);}c.stroke();}
  if(fog){c.fillStyle='#ffffff70';c.fillRect(f.x,f.y+60,f.w,f.base-f.y-60);}
  if(storm&&!w.reduced){c.strokeStyle='#ffffff40';c.lineWidth=1.5;for(let i=0;i<40;i++){const x=f.x+((i*97+t*160)%f.w),y=f.y+((i*53+t*300)%(f.base-f.y));L(c,x,y,x-8,y+16,'#ffffff40',1.5);}}}

/* ------------------------------------------------------------ the platform behind the deck */
function platform(c,w,x,base,s,port){c.save();c.translate(x,base);c.scale(s,s);const t=w.reduced?0:w.time;
  // legs into the sea
  for(const lx of [-170,-60,60,170]){R(c,lx-9,-60,18,62,STEEL_D,2);L(c,lx,-20,lx+(lx<0?50:-50),-58,STEEL,3);}
  // the main deck box and the living quarters
  R(c,-210,-120,420,62,'#dde2e5',6,STEEL_D,2);for(let i=0;i<9;i++)R(c,-196+i*44,-108,30,14,'#a9c7d6',3);
  R(c,-210,-62,420,8,ORANGE,2);
  R(c,90,-196,110,76,WHITE,6,STEEL_D,2);for(let r=0;r<3;r++)for(let k=0;k<4;k++)R(c,100+k*24,-186+r*22,16,12,'#a9c7d6',2);
  // helideck on top of the quarters
  P(c,[[70,-200],[220,-200],[232,-214],[58,-214]],'#4b5560');T(c,'H',145,-207,14,YEL,800);
  E(c,145,-207,30,5,'#00000000');L(c,70,-200,220,-200,YEL,2);
  // the derrick
  P(c,[[-150,-120],[-90,-120],[-112,-290],[-128,-290]],'#00000000');
  for(const [a,b] of [[[-150,-120],[-122,-290]],[[-90,-120],[-118,-290]]])L(c,a[0],a[1],b[0],b[1],'#c0533f',4);
  for(let i=1;i<8;i++){const y=-120-i*21,dx=28-i*3.4;L(c,-120-dx,y,-120+dx,y,'#c0533f',2);L(c,-120-dx,y,-120+dx-3.4,y-21,'#c0533f',1.4);}
  R(c,-130,-298,20,10,DARK,2);
  // the crane
  R(c,-20,-160,26,40,YEL,4,STEEL_D,1.5);L(c,-7,-158,70,-262,YEL,6);L(c,70,-262,70,-228,'#3b3f45',1.5);R(c,64,-230,12,10,ORANGE,2);
  // the flare boom and its flame
  L(c,200,-130,300,-236,STEEL_D,5);const fl=w.reduced?0:Math.sin(t*6)*3;
  P(c,[[300,-236],[292-fl,-262],[302,-284+fl],[312+fl,-262]],'#f08a3c');P(c,[[300,-238],[296,-254],[302,-266],[308,-254]],YEL);
  // the lifeboat on its davits
  P(c,[[-200,-66],[-130,-66],[-138,-50],[-192,-50]],ORANGE);R(c,-190,-80,52,14,ORANGE,7);L(c,-200,-66,-206,-96,STEEL_D,3);L(c,-130,-66,-124,-96,STEEL_D,3);
  T(c,'A',-165,-58,10,WHITE,800);
  heart(c,-40,-90,.28,'#e07a2f');
  c.restore();}

/* ------------------------------------------------------------ the deck the player walks on */
function deck(c,f){const {base,curb}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,bottom-base,DECK,0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,bottom-base);c.clip();
  for(let x=f.x;x<f.x+f.w;x+=60)L(c,x,base,x,bottom,'#b3b9be',1.5);for(let y=base+40;y<bottom;y+=40)L(c,f.x,y,f.x+f.w,y,'#b3b9be',1.5);
  L(c,f.x,base+26,f.x+f.w,base+26,YEL,5);L(c,f.x,curb-12,f.x+f.w,curb-12,YEL,5);
  for(let x=f.x+30;x<f.x+f.w;x+=70)P(c,[[x,base+20],[x+18,base+20],[x+30,base+32],[x+12,base+32]],'#2b2f33');
  c.restore();
  L(c,f.x,base-4,f.x+f.w,base-4,STEEL_D,4);for(let x=f.x+20;x<f.x+f.w;x+=40)L(c,x,base-4,x,base-30,STEEL,2);L(c,f.x,base-30,f.x+f.w,base-30,STEEL_D,3);}

/* ------------------------------------------------------------ props on deck */
function lotoCabinet(c,x0,x1,fy,port){const W=x1-x0+20,x=x0-10,h=port?78:70;E(c,x+W/2,fy+3,W/2+6,7,'#00000020');
  R(c,x,fy-h,W,h-6,'#f3f5f6',6,STEEL_D,2);R(c,x,fy-h,W,12,RED,5);T(c,'KHÓA · THẺ',x+W/2,fy-h+7,port?9:8,WHITE,800);
  for(let r=0;r<2;r++)for(let k=0;k<4;k++){const lx=x+10+k*(W-20)/4,ly=fy-h+22+r*20;R(c,lx,ly,10,9,RED,2);L(c,lx+2,ly,lx+2,ly-5,STEEL_D,1.5);L(c,lx+8,ly,lx+8,ly-5,STEEL_D,1.5);L(c,lx+2,ly-5,lx+8,ly-5,STEEL_D,1.5);}}
function pumpSkid(c,w,x0,x1,fy,port){const W=x1-x0,h=port?70:62,cx=(x0+x1)/2;E(c,cx,fy+3,W/2+8,8,'#00000020');
  R(c,x0,fy-14,W,12,STEEL_D,3);R(c,x0+W*.12,fy-h,W*.42,h-16,'#5f8fb0',10,'#2f5d7a',2);E(c,x0+W*.12,fy-h/2-6,10,18,'#4c7a99');
  R(c,x0+W*.56,fy-h+12,W*.3,h-28,'#7d8a94',6,STEEL_D,1.5);L(c,x0+W*.86,fy-h+20,x1+6,fy-h+20,STEEL_D,6);
  E(c,x0+W*.34,fy-h-10,10,4,RED);L(c,x0+W*.34,fy-h-6,x0+W*.34,fy-h,STEEL_D,2);E(c,x0+W*.72,fy-h-2,9,4,RED);
  const on=w.c?.open&&!w.reduced;if(on){const a=w.time*8;L(c,x0+W*.12,fy-h/2-6,x0+W*.12+Math.cos(a)*8,fy-h/2-6+Math.sin(a)*14,'#ffffff',2);}}
function permitDesk(c,w,x0,x1,fy,port){const W=x1-x0,h=port?64:58,top=fy-h;E(c,(x0+x1)/2,fy+3,W/2+10,8,'#00000020');
  R(c,x0,top,W,h,'#eef2f5',8,STEEL_D,2);R(c,x0,top,W,12,SEA_D,6);
  const label=w.words().counter;T(c,label,(x0+x1)/2,top+34,fit(c,label,W-20,port?14:12),'#2a3b4c',800);
  const bx=x0+W*.5;R(c,bx-46,top-60,92,52,'#fffaf0',5,STEEL_D,2);
  for(let i=0;i<3;i++){R(c,bx-40+i*28,top-54,22,30,['#cfe8d7','#ffe1c2','#d7e3f4'][i],2);L(c,bx-36+i*28,top-46,bx-22+i*28,top-46,'#9aa',1);L(c,bx-36+i*28,top-40,bx-24+i*28,top-40,'#9aa',1);}
  T(c,'GIẤY PHÉP',bx,top-16,port?9:8,'#2a3b4c',800);}
function gaugePanel(c,w,cx,fy,port){const bw=port?74:66,bh=port?64:58,top=fy-bh-34,m=mod(w);L(c,cx,fy,cx,top+bh,STEEL_D,4);
  R(c,cx-bw/2,top,bw,bh,DARK,6,'#1b232c',2);
  for(let i=0;i<2;i++){const gx=cx-bw/4+i*bw/2,gy=top+20;E(c,gx,gy,12,12,WHITE);E(c,gx,gy,9,9,'#f5f2eb');const a=-.9+i*.8+(w.reduced?0:Math.sin(w.time+i)*.05);L(c,gx,gy,gx+Math.cos(a)*8,gy+Math.sin(a)*8,RED,1.8);}
  T(c,m==='typhoon'?'BÃO':m==='monsoon'?'GIÓ 32 kt':'0% LEL',cx,top+bh-14,port?11:10,'#8fe0a0',800);}
function pobBoard(c,w,x0,x1,fy,port){const cx=(x0+x1)/2,bw=port?70:62,bh=port?52:46,top=fy-bh-6;E(c,cx,fy+2,bw/2+6,6,'#00000020');
  L(c,cx-bw/2+8,fy,cx-bw/2+8,top+bh,STEEL_D,3);L(c,cx+bw/2-8,fy,cx+bw/2-8,top+bh,STEEL_D,3);R(c,cx-bw/2,top,bw,bh,'#fffaf0',5,STEEL_D,1.5);
  T(c,'POB',cx,top+9,port?10:9,'#2a3b4c',800);for(let r=0;r<3;r++)for(let k=0;k<5;k++)R(c,cx-bw/2+6+k*(bw-12)/5,top+16+r*9,(bw-12)/5-3,6,(r+k)%3?'#cfe8d7':'#ffe1c2',1);
  const label=w.words().ledger;R(c,cx-34,fy+2,68,port?20:18,'#fffaf0',8,'#c4ccd3',1);T(c,label,cx,fy+(port?12:11),fit(c,label,60,port?11:10),'#2a3b4c',800);}
function aFrame(c,w,cx,fy,port){const open=w.c?.open,s=w.words(),label=open?s.open_sign:s.closed_sign,bw=port?118:104,bh=port?48:42,top=fy-bh-22;
  L(c,cx-bw/2+10,top+bh,cx-bw/2+2,fy,STEEL_D,4);L(c,cx+bw/2-10,top+bh,cx+bw/2-2,fy,STEEL_D,4);R(c,cx-bw/2,top,bw,bh,SEA_D,8,'#1b232c',2);
  T(c,label,cx,top+bh/2,fit(c,label,bw-14,port?14:12,800),WHITE,800);}

/* ------------------------------------------------------------ rooms */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land;
  if(port){E(c,350,862,320,22,'#9aa6b122');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#8ea3b1',33);}
  else{E(c,600,742,520,22,'#9aa6b122');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#8ea3b1',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  backdrop(c,w,f);
  if(port)platform(c,w,350,f.base-30,.95,true);else platform(c,w,600,f.base-26,1.25,false);
  deck(c,f);
  streetBoard(c,p,port?30:1013,port?282:322,port?1.6:1);
  c.restore();
  const [sx,sy,sw,sh]=f.sign,title=p.title||'Giàn Hải Âu';
  R(c,sx-5,sy+7,sw+10,sh,'#16455a',26);R(c,sx,sy,sw,sh,'#f4f8fb',24,'#8fb3c4',3);
  T(c,title,sx+sw/2,sy+40,fit(c,title,sw-80,30,800),SEA_D,800);T(c,p.sub||'',sx+sw/2,sy+sh-26,fit(c,p.sub||'',sw-60,13),'#4a5d70');
  heart(c,sx+36,sy+sh/2+4,.4,ORANGE);E(c,sx+sw-36,sy+sh/2,12,12,YEL);
}
function props(w,p){const c=w.ctx,port=w.isPortrait(),b=w.plan().blocks,out=[];
  const [wh,wb,co,ev,fi,dr]=b;
  out.push([wh[3],()=>lotoCabinet(c,wh[0],wh[2],wh[3],port)]);
  out.push([wb[3],()=>pumpSkid(c,w,wb[0],wb[2],wb[3],port)]);
  out.push([co[3],()=>permitDesk(c,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>gaugePanel(c,w,(ev[0]+ev[2])/2,ev[3],port)]);
  out.push([fi[3],()=>pobBoard(c,w,fi[0],fi[2],fi[3],port)]);
  out.push([dr[3],()=>aFrame(c,w,(dr[0]+dr[2])/2,dr[3],port)]);
  return out;
}

export default {
  id:'rig',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
};
