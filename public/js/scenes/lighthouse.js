/** Lighthouse scene (kind `lighthouse`, career lighthouse): the rock of đảo Hòn Gió. The sea and the sky behind (the
 * day's weather from the career's public data: room.data.mod), the white tower with its red band, the gallery and the
 * lamp room whose beam sweeps while the shift is open, the keeper's house with its solar panels, and on the rock: the
 * generator shed (warehouse), the vegetable boxes with Mun the cat (workbench), the radio desk (counter), the weather
 * mast with its anemometer (evidence), the logbook board (finance) and the A-frame sign at the landing (door).
 * Footprints follow the rig scene's plan (the airfield street plan without its terminal doors). */
import {R,E,L,T,P,fit,heart,streetBoard} from './kit.js';
import {PLAN as RIG} from './rig.js';

export const PLAN=RIG;

const SEA='#2f88a8',SEA_D='#1f5f7a',ROCK='#8d8a80',ROCK_D='#6c6a62',WHITE='#f8fafc',RED='#d6382b',LAMP='#f2c14e',DARK='#26303b',GREEN='#5e9f4a';
const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,curb:668,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,curb:800,sign:[135,30,430,104]}};
const mod=w=>w.c?.data?.mod?.id||'calm';

/* ------------------------------------------------------------ the sea and the sky */
function backdrop(c,w,f){const m=mod(w),storm=m==='storm',grey=storm||m==='breeze',fog=m==='fog';
  const g=c.createLinearGradient(0,f.y,0,f.base);g.addColorStop(0,storm?'#7f8b95':grey?'#b7c3cc':fog?'#dfe5e8':'#bfe0f2');g.addColorStop(1,storm?'#c3c9cd':'#f3efe2');
  c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  const port=f===F.port,hz=f.y+(f.base-f.y)*.6,t=w.reduced?0:w.time;
  if(!grey&&!fog)E(c,port?600:1040,port?190:178,28,28,'#fff3c4');
  const drift=Math.sin(t*.07)*18;
  for(const [x,y,s] of port?[[120,196,.8],[420,176,.6]]:[[210,172,1],[700,160,.8]]){const col=grey?'#97a3adcc':'#ffffffcc';E(c,x+drift,y,34*s,14*s,col);E(c,x+drift-24*s,y+5*s,22*s,11*s,col);E(c,x+drift+26*s,y+3*s,24*s,12*s,col);}
  const sg=c.createLinearGradient(0,hz,0,f.base);sg.addColorStop(0,storm?'#5d7380':SEA);sg.addColorStop(1,SEA_D);c.fillStyle=sg;c.fillRect(f.x,hz,f.w,f.base-hz);
  const amp=storm?7:grey?4:2;c.strokeStyle='#ffffff55';c.lineWidth=2;
  for(let row=0;row<4;row++){const y=hz+12+row*(f.base-hz-12)/4;c.beginPath();for(let x=f.x;x<=f.x+f.w;x+=12){const yy=y+Math.sin(x*.035+t*1.2+row)*amp;x===f.x?c.moveTo(x,yy):c.lineTo(x,yy);}c.stroke();}
  // a fishing boat far out
  const bx=f.x+f.w*(port?.18:.12)+Math.sin(t*.1)*10,by=hz+18;P(c,[[bx-18,by],[bx+18,by],[bx+12,by+8],[bx-12,by+8]],'#8a5a3c');L(c,bx,by,bx,by-22,'#5a4030',2);P(c,[[bx,by-22],[bx+12,by-6],[bx,by-6]],'#f3efe2');
  if(fog){c.fillStyle='#ffffff80';c.fillRect(f.x,f.y+40,f.w,f.base-f.y-40);}
  if(storm&&!w.reduced){for(let i=0;i<40;i++){const x=f.x+((i*97+t*160)%f.w),y=f.y+((i*53+t*300)%(f.base-f.y));L(c,x,y,x-8,y+16,'#ffffff40',1.5);}}}

/* ------------------------------------------------------------ the tower and the house behind the rock */
function tower(c,w,x,base,s){c.save();c.translate(x,base);c.scale(s,s);const t=w.reduced?0:w.time,on=w.c?.open;
  // the rock under the tower
  P(c,[[-150,0],[-110,-40],[-40,-58],[60,-54],[140,-30],[170,0]],ROCK);P(c,[[-90,-30],[-40,-50],[10,-44]],ROCK_D);
  // the keeper's house with solar panels
  R(c,40,-110,110,60,WHITE,6,'#9aa7b1',2);P(c,[[32,-110],[95,-146],[158,-110]],RED);
  R(c,58,-96,22,20,'#a9c7d6',3);R(c,110,-96,22,20,'#a9c7d6',3);R(c,86,-84,16,34,'#7a5a3c',3);
  P(c,[[60,-132],[100,-152],[112,-146],[72,-126]],'#2f4a6a');L(c,66,-129,106,-149,'#8fb3c4',1.2);
  // the tower: white, a red band, the gallery and the lamp room
  P(c,[[-34,-50],[34,-50],[22,-300],[-22,-300]],WHITE);L(c,-34,-50,-22,-300,'#c9d1d6',2);L(c,34,-50,22,-300,'#c9d1d6',2);
  P(c,[[-29,-150],[29,-150],[27,-190],[-27,-190]],RED);
  R(c,-30,-306,60,8,DARK,2);for(let i=0;i<7;i++)L(c,-28+i*9.3,-306,-28+i*9.3,-322,DARK,1.5);L(c,-30,-322,30,-322,DARK,2);
  R(c,-18,-344,36,30,on?'#fff5c8':'#cfe0e6',4,DARK,2);P(c,[[-22,-344],[22,-344],[0,-366]],RED);E(c,0,-369,3,3,DARK);
  for(let i=0;i<4;i++)R(c,-12,-292+i*60,10,14,'#a9c7d6',2);
  if(on){const a=t*1.2;const reach=420,spread=.08;
    c.save();c.globalAlpha=.35;c.fillStyle=LAMP;c.beginPath();c.moveTo(0,-330);c.lineTo(Math.cos(a-spread)*reach,-330+Math.sin(a-spread)*reach*.25);c.lineTo(Math.cos(a+spread)*reach,-330+Math.sin(a+spread)*reach*.25);c.closePath();c.fill();c.restore();
    E(c,0,-330,9,9,LAMP);}
  heart(c,-120,-20,.28,RED);
  c.restore();}

/* ------------------------------------------------------------ the rock the player walks on */
function ground(c,f){const {base,curb}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,bottom-base,'#b9b3a5',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,bottom-base);c.clip();
  for(let i=0;i<60;i++){const x=f.x+((i*137)%f.w),y=base+20+((i*61)%(bottom-base-20));E(c,x,y,18+(i%5)*4,8+(i%3)*3,i%2?'#aca596':'#c3bdaf');}
  for(let x=f.x;x<f.x+f.w;x+=46)R(c,x,curb-20,40,14,'#d8d1c0',4);
  c.restore();L(c,f.x,base-4,f.x+f.w,base-4,ROCK_D,4);for(let x=f.x+20;x<f.x+f.w;x+=40)L(c,x,base-4,x,base-26,'#8f8a7e',2);L(c,f.x,base-26,f.x+f.w,base-26,ROCK_D,3);}

/* ------------------------------------------------------------ props on the rock */
function shed(c,x0,x1,fy,port){const W=x1-x0+20,x=x0-10,h=port?78:70;E(c,x+W/2,fy+3,W/2+6,7,'#00000020');
  R(c,x,fy-h,W,h-6,'#e9ecef',6,'#6f7d88',2);P(c,[[x-6,fy-h],[x+W/2,fy-h-18],[x+W+6,fy-h]],'#6f7d88');
  R(c,x+8,fy-h+14,W*.5,h-26,'#4b5560',4);E(c,x+W*.33,fy-h/2,8,8,'#9aa7b1');T(c,'MÁY PHÁT',x+W/2,fy-10,port?9:8,DARK,800);
  R(c,x+W*.66,fy-h+22,W*.24,h-34,'#d9a45a',4,'#a67c3c',1.5);}
function garden(c,w,x0,x1,fy,port){const W=x1-x0,cx=(x0+x1)/2;E(c,cx,fy+3,W/2+8,8,'#00000020');
  for(let i=0;i<3;i++){const bx=x0+i*W/3+4,bw=W/3-8;R(c,bx,fy-28,bw,26,'#f3f5f6',4,'#c9d1d6',1.5);for(let k=0;k<4;k++){const lx=bx+6+k*(bw-12)/3;L(c,lx,fy-28,lx-4,fy-44,GREEN,2);E(c,lx-4,fy-46,5,4,GREEN);}}
  // Mun the cat
  const mx=x1-6;E(c,mx,fy-8,12,8,'#222');E(c,mx+9,fy-16,6,6,'#222');P(c,[[mx+5,fy-21],[mx+7,fy-27],[mx+9,fy-21]],'#222');P(c,[[mx+10,fy-21],[mx+13,fy-27],[mx+14,fy-20]],'#222');
  E(c,mx+11,fy-17,1.3,1.3,LAMP);L(c,mx-12,fy-6,mx-20,fy-16,'#222',3);}
function radioDesk(c,w,x0,x1,fy,port){const W=x1-x0,h=port?64:58,top=fy-h;E(c,(x0+x1)/2,fy+3,W/2+10,8,'#00000020');
  R(c,x0,top,W,h,'#eef2f5',8,'#6f7d88',2);R(c,x0,top,W,12,SEA_D,6);
  const label=w.words().counter;T(c,label,(x0+x1)/2,top+34,fit(c,label,W-20,port?14:12),'#2a3b4c',800);
  const bx=x0+W*.5;R(c,bx-40,top-40,80,34,DARK,5,'#1b232c',2);R(c,bx-32,top-34,36,12,'#8fe0a0',2);T(c,'CH 16',bx-14,top-28,8,DARK,800);
  E(c,bx+22,top-22,7,7,'#9aa7b1');L(c,bx+34,top-40,bx+40,top-70,'#6f7d88',2);}
function mast(c,w,cx,fy,port){const t=w.reduced?0:w.time,m=mod(w),sp=m==='storm'?9:m==='breeze'?5:2;L(c,cx,fy,cx,fy-100,'#6f7d88',4);
  const a=t*sp;for(let i=0;i<3;i++){const aa=a+i*2.09;L(c,cx,fy-100,cx+Math.cos(aa)*16,fy-100+Math.sin(aa)*5,'#6f7d88',2);E(c,cx+Math.cos(aa)*16,fy-100+Math.sin(aa)*5,4,3,'#c9d1d6');}
  P(c,[[cx,fy-80],[cx+28,fy-74],[cx,fy-68]],m==='storm'||m==='breeze'?RED:'#f2a25a');
  R(c,cx-16,fy-46,32,26,'#fffaf0',4,'#6f7d88',1.5);E(c,cx,fy-33,9,9,WHITE);L(c,cx,fy-33,cx+5,fy-38,RED,1.5);}
function logBoard(c,w,x0,x1,fy,port){const cx=(x0+x1)/2,bw=port?70:62,bh=port?52:46,top=fy-bh-6;E(c,cx,fy+2,bw/2+6,6,'#00000020');
  L(c,cx-bw/2+8,fy,cx-bw/2+8,top+bh,'#6f7d88',3);L(c,cx+bw/2-8,fy,cx+bw/2-8,top+bh,'#6f7d88',3);R(c,cx-bw/2,top,bw,bh,'#fffaf0',5,'#6f7d88',1.5);
  T(c,'SỔ TRỰC',cx,top+9,port?9:8,'#2a3b4c',800);for(let r=0;r<4;r++)L(c,cx-bw/2+8,top+18+r*7,cx+bw/2-8,top+18+r*7,'#c4ccd3',1);
  const label=w.words().ledger;R(c,cx-34,fy+2,68,port?20:18,'#fffaf0',8,'#c4ccd3',1);T(c,label,cx,fy+(port?12:11),fit(c,label,60,port?11:10),'#2a3b4c',800);}
function aFrame(c,w,cx,fy,port){const open=w.c?.open,s=w.words(),label=open?s.open_sign:s.closed_sign,bw=port?118:104,bh=port?48:42,top=fy-bh-22;
  L(c,cx-bw/2+10,top+bh,cx-bw/2+2,fy,'#6f7d88',4);L(c,cx+bw/2-10,top+bh,cx+bw/2-2,fy,'#6f7d88',4);R(c,cx-bw/2,top,bw,bh,SEA_D,8,'#1b232c',2);
  T(c,label,cx,top+bh/2,fit(c,label,bw-14,port?14:12,800),WHITE,800);}

/* ------------------------------------------------------------ rooms */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land;
  if(port){E(c,350,862,320,22,'#9aa6b122');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#8ea3b1',33);}
  else{E(c,600,742,520,22,'#9aa6b122');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#8ea3b1',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  backdrop(c,w,f);
  if(port)tower(c,w,330,f.base-20,.95);else tower(c,w,620,f.base-16,1.05);
  ground(c,f);
  streetBoard(c,p,port?30:1013,port?282:322,port?1.6:1);
  c.restore();
  const [sx,sy,sw,sh]=f.sign,title=p.title||'Đèn biển Hòn Gió';
  R(c,sx-5,sy+7,sw+10,sh,'#16455a',26);R(c,sx,sy,sw,sh,'#f4f8fb',24,'#8fb3c4',3);
  T(c,title,sx+sw/2,sy+40,fit(c,title,sw-80,30,800),SEA_D,800);T(c,p.sub||'',sx+sw/2,sy+sh-26,fit(c,p.sub||'',sw-60,13),'#4a5d70');
  heart(c,sx+36,sy+sh/2+4,.4,RED);E(c,sx+sw-36,sy+sh/2,12,12,LAMP);
}
function props(w,p){const c=w.ctx,port=w.isPortrait(),b=w.plan().blocks,out=[];
  const [wh,wb,co,ev,fi,dr]=b;
  out.push([wh[3],()=>shed(c,wh[0],wh[2],wh[3],port)]);
  out.push([wb[3],()=>garden(c,w,wb[0],wb[2],wb[3],port)]);
  out.push([co[3],()=>radioDesk(c,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>mast(c,w,(ev[0]+ev[2])/2,ev[3],port)]);
  out.push([fi[3],()=>logBoard(c,w,fi[0],fi[2],fi[3],port)]);
  out.push([dr[3],()=>aFrame(c,w,(dr[0]+dr[2])/2,dr[3],port)]);
  return out;
}

export default {
  id:'lighthouse',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
};
