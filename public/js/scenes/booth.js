/** Photobooth scene (kind `booth`): chị Lam's Tiệm ảnh Tách Tách on the night-market street. An evening sky
 * with strings of bulbs, the shophouse with its pink neon "TÁCH TÁCH", the booth with a red velvet curtain and a
 * ring light, a wall of sample strips in many frames, the counter with the little dye-sub printer, the props
 * basket, boxes of photo paper, the sample-frame easel, the cash box and the chalk standee on the pavement.
 * The shop's own state (open, lens, ink) comes from the career's public data. Footprints follow the sidewalk
 * plan (see shop.js for the PLAN schema). */
import {R,E,L,T,P,fit,heart,streetBoard} from './kit.js';
import {PLAN} from './sidewalk.js';

export {PLAN};
const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,curb:668,road:680,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,curb:800,road:812,sign:[135,30,430,104]}};
const PINK='#e0568a',PINK_L='#ffd0e0',CURTAIN='#b8344a',CURTAIN_D='#8a2438',WOOD='#b88b62',WOOD_D='#8f6746';
const FRAME_COLS=[['#f6c9d6','#d0567f'],['#c9e7da','#3f8f7a'],['#f3e1b4','#c0392b'],['#d9d2f0','#6b5bb5'],['#fde3c4','#e08a3a'],['#cfe3f4','#3f7fbf'],['#2f2a36','#f2c84b']];
const d=w=>w.c?.data||{};
const mod=w=>d(w).mod?.id||'normal';

/* ------------------------------------------------------------ backdrop */
function sky(c,w,f){const rain=mod(w)==='rain',g=c.createLinearGradient(0,f.y,0,f.base);
  g.addColorStop(0,rain?'#5d6478':'#4b3f73');g.addColorStop(.55,rain?'#8b8f9e':'#c86f8a');g.addColorStop(1,rain?'#c9c4bd':'#f7c48f');c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  if(!rain){const port=f===F.port;E(c,port?600:1050,port?190:180,22,22,'#fff3c4');E(c,port?606:1056,port?186:176,18,18,rain?'#5d6478':'#4b3f73');}
  for(let i=0;i<14;i++){const x=f.x+((i*97)%f.w),y=f.y+20+((i*53)%120);E(c,x,y,1.4,1.4,'#fff6d899');}}
function bulbs(c,w,x0,x1,y,sag){c.strokeStyle='#3a2f3a';c.lineWidth=1.5;c.beginPath();c.moveTo(x0,y);c.quadraticCurveTo((x0+x1)/2,y+sag,x1,y);c.stroke();
  const n=Math.max(6,Math.round((x1-x0)/46)),cols=['#ffd36e','#ff9fbf','#9fd8ff','#c6f09a'];
  for(let i=1;i<n;i++){const t=i/n,x=x0+(x1-x0)*t,yy=y+2*sag*t*(1-t),on=w.reduced?1:.6+.4*Math.sin(w.time*2+i);
    E(c,x,yy+7,9,9,cols[i%4]+Math.round(on*60).toString(16).padStart(2,'0'));E(c,x,yy+7,3.4,4.4,cols[i%4]);}}
function rainLines(c,w,f){if(mod(w)!=='rain')return;const t=w.reduced?0:(w.time*220)%40;c.strokeStyle='#cfd8e255';c.lineWidth=1.5;
  for(let x=f.x+10;x<f.x+f.w;x+=26)for(let y=f.y+((x/26|0)%3)*14-40+t;y<f.curb;y+=40){c.beginPath();c.moveTo(x,y);c.lineTo(x-6,y+16);c.stroke();}}
function tube(c,x,top,wd,base,col,shut){R(c,x,top,wd,base-top+2,col,6,'#7a5a6a',2);R(c,x-6,top-12,wd+12,16,'#8a5a6a',7);
  const n=Math.max(1,Math.floor(wd/90));for(let i=0;i<n;i++){const cx=x+wd*(i+.5)/n;R(c,cx-20,top+26,40,48,'#ffe7a8',4,'#7a5a6a',1.5);R(c,cx-37,top+24,14,52,shut,3);R(c,cx+23,top+24,14,52,shut,3);}}
function pavement(c,f){const {base,curb,road}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,curb-base,'#e3d3c0',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,curb-base);c.clip();const tw=f===F.port?46:52,th=f===F.port?46:40;
  for(let y=base,row=0;y<curb;y+=th,row++)for(let x=f.x;x<f.x+f.w;x+=tw){c.fillStyle=((x/tw|0)+row)%2?'#dccab3':'#e8dac6';c.fillRect(x+1.5,y+1.5,tw-3,th-3);}
  const g=c.createRadialGradient(f.x+f.w/2,base,10,f.x+f.w/2,base,f.w*.5);g.addColorStop(0,'#ff8fb133');g.addColorStop(1,'#ff8fb100');c.fillStyle=g;c.fillRect(f.x,base,f.w,curb-base);
  c.restore();R(c,f.x,curb,f.w,road-curb,'#b9b2aa',0);L(c,f.x,curb,f.x+f.w,curb,'#958d84',2);R(c,f.x,road,f.w,bottom-road,'#6f7680',0);
  for(let x=f.x+30;x<f.x+f.w;x+=120)R(c,x,road+(bottom-road)/2-2,56,4,'#f1e7c8',2);}

/* ------------------------------------------------------------ the shop front */
function neon(c,w,x,y,wd,port){const open=w.c?.open,glow=open?(w.reduced?1:.85+.15*Math.sin(w.time*3)):.25;
  R(c,x,y,wd,port?50:56,'#2a2230',10,'#4a3a4a',3);c.save();c.shadowColor=PINK;c.shadowBlur=open?18*glow:0;
  T(c,'TÁCH TÁCH',x+wd/2,y+(port?25:28),fit(c,'TÁCH TÁCH',wd-60,port?28:32,900),open?PINK_L:'#8a6a7a',900);c.restore();
  E(c,x+24,y+(port?25:28),9,9,open?'#ffd36e':'#6a5a5a');E(c,x+wd-24,y+(port?25:28),9,9,open?'#9fd8ff':'#6a5a5a');}
function shopFront(c,w,f,x,wd,port){const top=f.base-(port?230:250);
  R(c,x,top,wd,f.base-top,'#f4e3d6',6,'#7a5a6a',2);R(c,x-8,top-14,wd+16,18,'#9a5a72',7);
  neon(c,w,x+wd*.18,top+8,wd*.64,port);
  // the glass front, lit warm inside
  const gy=top+(port?70:76),gh=f.base-gy-6;R(c,x+12,gy,wd-24,gh,'#fff1d8',6,'#7a5a6a',2);
  const g=c.createLinearGradient(0,gy,0,gy+gh);g.addColorStop(0,'#ffe9c2');g.addColorStop(1,'#f7cfb3');c.fillStyle=g;c.fillRect(x+14,gy+2,wd-28,gh-4);
  // the booth: a cabin with a red velvet curtain, a ring light beside it
  const bx=x+24,bw=port?wd*.36:wd*.32,bt=gy+12,bb=f.base-8;R(c,bx,bt,bw,bb-bt,'#3a2f3e',6);R(c,bx-4,bt-10,bw+8,16,'#2a2230',5);
  T(c,'PHOTO',bx+bw/2,bt-2,port?11:12,'#ffd0e0',900);
  const folds=7,open=w.c?.open;for(let i=0;i<folds;i++){const fx=bx+6+i*(bw-12)/folds,fw=(bw-12)/folds;
    P(c,[[fx,bt+8],[fx+fw,bt+8],[fx+fw+(open&&i>4?6:0),bb],[fx+(open&&i>4?6:0),bb]],i%2?CURTAIN:CURTAIN_D);}
  if(open)P(c,[[bx+bw-24,bt+8],[bx+bw-6,bt+8],[bx+bw-6,bb],[bx+bw-30,bb]],'#ffdca8');
  const rx=bx+bw+(port?30:38),ry=bt+(port?50:60),rr=port?24:28;c.strokeStyle='#fff';c.lineWidth=port?7:8;c.beginPath();c.arc(rx,ry,rr,0,Math.PI*2);c.stroke();
  c.strokeStyle='#ffe9a8aa';c.lineWidth=2;c.beginPath();c.arc(rx,ry,rr+5,0,Math.PI*2);c.stroke();L(c,rx,ry+rr,rx,bb,'#4a4048',4);L(c,rx-16,bb,rx+16,bb,'#4a4048',4);
  // the wall of sample strips: many frames
  const sx=rx+rr+(port?14:22),sw=x+wd-24-sx,cols=Math.max(3,Math.floor(sw/(port?24:28)));
  for(let i=0;i<cols*2;i++){const col=FRAME_COLS[i%FRAME_COLS.length],cx=sx+(i%cols)*(sw/cols)+4,cy=gy+14+Math.floor(i/cols)*(port?70:80),sh=port?58:66,swd=port?16:19;
    c.save();c.translate(cx+swd/2,cy+sh/2);c.rotate(((i*37)%7-3)*.02);R(c,-swd/2,-sh/2,swd,sh,col[0],2,col[1],1.5);
    for(let k=0;k<4;k++)R(c,-swd/2+3,-sh/2+3+k*(sh-10)/4,swd-6,(sh-10)/4-2,k%2?'#e9d6c8':'#d8c2b2',1);c.restore();
    if(i%cols===cols-1&&i>0)heart(c,cx+swd+4,cy+6,.22,PINK);}}

/* ------------------------------------------------------------ props on the pavement */
function paperBoxes(c,x0,x1,fy,port){const W=x1-x0;E(c,(x0+x1)/2,fy+3,W/2+6,6,'#5a3a4a22');
  R(c,x0,fy-36,W,36,'#d9b58c',4,'#a5825e',1.5);R(c,x0+6,fy-62,W-16,26,'#e6c69c',4,'#a5825e',1.5);T(c,'GIẤY IN',x0+W/2,fy-18,port?10:11,'#6b4a33',800);
  R(c,x0+W*.2,fy-70,W*.5,8,'#fff',2,'#c9b39a',1);}
function propsTable(c,w,x0,x1,fy,port){const W=x1-x0,top=fy-(port?34:30);E(c,(x0+x1)/2,fy+3,W/2+8,7,'#5a3a4a22');
  L(c,x0+8,top+8,x0+6,fy,WOOD_D,4);L(c,x1-8,top+8,x1-6,fy,WOOD_D,4);R(c,x0,top,W,10,WOOD,4,WOOD_D,1.5);
  const bx=x0+W*.12,bw=W*.5;R(c,bx,top-24,bw,24,'#d8a35c',6,'#a8743a',1.5);for(let i=1;i<5;i++)L(c,bx+i*bw/5,top-24,bx+i*bw/5,top,'#a8743a',1);
  // bunny ears, heart glasses, a party hat, a crown
  E(c,bx+bw*.25,top-38,5,14,'#fff');E(c,bx+bw*.38,top-38,5,14,'#fff');E(c,bx+bw*.25,top-38,2.4,9,'#f7b6c8');E(c,bx+bw*.38,top-38,2.4,9,'#f7b6c8');
  heart(c,bx+bw*.62,top-30,.3,'#e0568a');heart(c,bx+bw*.78,top-30,.3,'#e0568a');
  P(c,[[x0+W*.72,top],[x0+W*.8,top-34],[x0+W*.88,top]],'#6fb8e8');E(c,x0+W*.8,top-35,4,4,'#f2c84b');
  P(c,[[x0+W*.62,top-26],[x0+W*.65,top-34],[x0+W*.68,top-28],[x0+W*.71,top-36],[x0+W*.74,top-26]],'#f2c84b');
  T(c,'ĐẠO CỤ',(x0+x1)/2,fy+12,port?10:11,'#fff3f7',800);}
function counter(c,w,x0,x1,fy,port){const W=x1-x0,h=port?64:56,top=fy-h;E(c,(x0+x1)/2,fy+3,W/2+10,8,'#5a3a4a22');
  R(c,x0,top,W,h,'#f7e6d8',8,'#a0786a',2);R(c,x0-6,top-8,W+12,12,WOOD,5,WOOD_D,1.5);
  const label=w.words().counter;T(c,label,(x0+x1)/2,top+h/2+4,fit(c,label,W-24,port?15:13),'#6b3f4f',800);
  // the dye-sub printer with a strip coming out
  const px=x0+W*.66,pw=W*.26;R(c,px,top-34,pw,26,'#e9e4ea',5,'#9a8f9a',1.5);R(c,px+6,top-20,pw-12,4,'#3a3340',2);
  const ink=Number(d(w).ribbon??24);E(c,px+pw-10,top-28,3,3,ink<4?'#e0573f':'#6fd08c');
  if(w.c?.open){R(c,px+pw*.3,top-62,pw*.4,40,'#fffaf2',2,'#d0b8a8',1);for(let k=0;k<3;k++)R(c,px+pw*.34,top-58+k*12,pw*.32,9,['#f6c9d6','#c9e7da','#f3e1b4'][k],1);}
  // a little camera on the counter
  R(c,x0+W*.12,top-24,40,22,'#2d2730',5);E(c,x0+W*.12+20,top-13,8,8,'#6a7ea8');E(c,x0+W*.12+20,top-13,4,4,'#1a1820');R(c,x0+W*.12+28,top-28,8,5,'#2d2730',2);}
function easel(c,x0,x1,fy,port){const cx=(x0+x1)/2,h=port?96:104,top=fy-h;L(c,cx-22,fy,cx,top,WOOD_D,4);L(c,cx+22,fy,cx,top,WOOD_D,4);L(c,cx,top+20,cx,fy,WOOD_D,3);
  R(c,cx-30,top+10,60,64,'#fffaf2',4,WOOD_D,2);for(let i=0;i<3;i++){const col=FRAME_COLS[(i*2)%FRAME_COLS.length];R(c,cx-24+i*17,top+16,14,52,col[0],2,col[1],1.2);}
  T(c,'KHUNG MẪU',cx,top+84,port?9:10,'#6b3f4f',800);}
function cashBox(c,w,x0,x1,fy,port){const cx=(x0+x1)/2;E(c,cx,fy+3,30,6,'#5a3a4a22');R(c,cx-14,fy-30,28,30,'#e0568a',4);R(c,cx-28,fy-48,56,20,'#f2c84b',4,'#b88b2a',1.5);
  const label=w.words().ledger;R(c,cx-38,fy+2,76,port?20:18,'#fffaf0',8,'#c7ad90',1);T(c,label,cx,fy+(port?12:11),fit(c,label,68,port?11:10),'#6b3f4f',800);}
function standee(c,w,cx,fy,port){const open=w.c?.open,bw=port?118:104,bh=port?56:50,top=fy-bh-24;
  E(c,cx,fy+2,bw/2,6,'#5a3a4a22');L(c,cx-bw/2+12,top+bh,cx-bw/2+4,fy,WOOD_D,4);L(c,cx+bw/2-12,top+bh,cx+bw/2-4,fy,WOOD_D,4);
  R(c,cx-bw/2,top,bw,bh,'#3d3a44',8,WOOD_D,3);const s=open?'CHỤP 4 Ô':w.words().closed_sign;
  T(c,s,cx,top+bh/2-7,fit(c,s,bw-14,port?15:13,800),'#fdf7e8',800);T(c,open?'in liền tay':'mai mời ghé',cx,top+bh-11,port?11:10,'#ffb3cc',700);heart(c,cx+bw/2-12,top+10,.2,PINK);}

/* ------------------------------------------------------------ rooms */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land;
  if(port){E(c,350,862,320,22,'#cba88d22');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#a67a8a',33);}
  else{E(c,600,742,520,22,'#cba88d22');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#a67a8a',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  if(port){tube(c,24,262,150,f.base,'#e9d2c6','#9a7ab0');tube(c,520,250,160,f.base,'#d8c6e6','#e09ab0');shopFront(c,w,f,150,390,true);bulbs(c,w,24,676,228,40);}
  else{tube(c,78,236,240,f.base,'#e9d2c6','#9a7ab0');tube(c,900,244,234,f.base,'#d8c6e6','#e09ab0');shopFront(c,w,f,320,580,false);bulbs(c,w,66,1134,196,54);}
  pavement(c,f);
  streetBoard(c,p,port?30:1013,port?282:322,port?1.6:1);
  rainLines(c,w,f);
  c.restore();
  const title=p.title||'Tiệm ảnh Tách Tách';
  const [sx,sy,sw,sh]=f.sign;R(c,sx-5,sy+7,sw+10,sh,'#7a3a52',26);R(c,sx,sy,sw,sh,'#fff4f7',24,'#e0568a',3);
  T(c,title,sx+sw/2,sy+40,fit(c,title,sw-60,30,800),'#6b2f47',800);T(c,p.sub||'',sx+sw/2,sy+sh-26,fit(c,p.sub||'',sw-60,13),'#8a5a6a');
  heart(c,sx+36,sy+sh/2+4,.5,PINK);E(c,sx+sw-36,sy+sh/2,12,12,'#2d2730');E(c,sx+sw-36,sy+sh/2,6,6,'#6a7ea8');}

function props(w,p){const c=w.ctx,port=w.isPortrait(),b=w.plan().blocks,out=[];
  const [wh,wb,co,ev,fi,dr]=b;
  out.push([wh[3],()=>paperBoxes(c,wh[0],wh[2],wh[3],port)]);
  out.push([wb[3],()=>propsTable(c,w,wb[0],wb[2],wb[3],port)]);
  out.push([co[3],()=>counter(c,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>easel(c,ev[0]-10,ev[2]+10,ev[3],port)]);
  out.push([fi[3],()=>cashBox(c,w,fi[0],fi[2],fi[3],port)]);
  out.push([dr[3],()=>standee(c,w,(dr[0]+dr[2])/2,dr[3],port)]);
  return out;
}

export default {
  id:'booth',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
};
