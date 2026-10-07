/** Album shop scene (kind `albumshop`): chị Thơ's Tiệm album Mây Pop on Phố chợ. A late-afternoon sky, the shophouse
 * with its pink neon "MÂY POP", posters of the (fictional) groups in the window drawn as shapes only (a pink heart for
 * BLANKPINK, a swirl for 7GIÓ, a kiwi slice for KIWIZ), the album shelf with stacks in many colours, the lightstick
 * cabinet where the pink hammers glow when the shop is open, the counter with the Zchart scanner, the fansign box and
 * a chalk standee on the pavement. The shop's own state (open, POB left, Zchart locked) comes from the career's public
 * data. Footprints follow the sidewalk plan (see shop.js for the PLAN schema). */
import {R,E,L,T,P,fit,heart,streetBoard} from './kit.js';
import {PLAN} from './sidewalk.js';

export {PLAN};
const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,curb:668,road:680,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,curb:800,road:812,sign:[135,30,430,104]}};
const PINK='#d6458f',PINK_L='#ffd3ea',WOOD='#b88b62',WOOD_D='#8f6746';
const ALBUM_COLS=['#f6a6c9','#fdfdfd','#bfe3ff','#ffd27a','#c7f0c1','#d9c7ff','#2f2a36'];
const d=w=>w.c?.data||{};
const mod=w=>d(w).mod?.id||'normal';

/* ------------------------------------------------------------ backdrop */
function sky(c,w,f){const rain=mod(w)==='rain',g=c.createLinearGradient(0,f.y,0,f.base);
  g.addColorStop(0,rain?'#5d6478':'#7a6fb0');g.addColorStop(.6,rain?'#8b8f9e':'#f2a6c3');g.addColorStop(1,rain?'#c9c4bd':'#ffe0b8');c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  for(let i=0;i<10;i++){const x=f.x+((i*131)%f.w),y=f.y+24+((i*61)%110);E(c,x,y,1.5,1.5,'#ffffff88');}}
function rainLines(c,w,f){if(mod(w)!=='rain')return;const t=w.reduced?0:(w.time*220)%40;c.strokeStyle='#cfd8e255';c.lineWidth=1.5;
  for(let x=f.x+10;x<f.x+f.w;x+=26)for(let y=f.y+((x/26|0)%3)*14-40+t;y<f.curb;y+=40){c.beginPath();c.moveTo(x,y);c.lineTo(x-6,y+16);c.stroke();}}
function neighbour(c,x,top,wd,base,col,shut){R(c,x,top,wd,base-top+2,col,6,'#7a5a6a',2);R(c,x-6,top-12,wd+12,16,'#8a6a7a',7);
  const n=Math.max(1,Math.floor(wd/90));for(let i=0;i<n;i++){const cx=x+wd*(i+.5)/n;R(c,cx-20,top+26,40,48,'#ffe7a8',4,'#7a5a6a',1.5);R(c,cx-37,top+24,14,52,shut,3);R(c,cx+23,top+24,14,52,shut,3);}}
function pavement(c,f){const {base,curb,road}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,curb-base,'#e6d7c6',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,curb-base);c.clip();const tw=f===F.port?46:52,th=f===F.port?46:40;
  for(let y=base,row=0;y<curb;y+=th,row++)for(let x=f.x;x<f.x+f.w;x+=tw){c.fillStyle=((x/tw|0)+row)%2?'#dfcdb8':'#ebdfcd';c.fillRect(x+1.5,y+1.5,tw-3,th-3);}
  c.restore();R(c,f.x,curb,f.w,road-curb,'#b9b2aa',0);L(c,f.x,curb,f.x+f.w,curb,'#958d84',2);R(c,f.x,road,f.w,bottom-road,'#6f7680',0);
  for(let x=f.x+30;x<f.x+f.w;x+=120)R(c,x,road+(bottom-road)/2-2,56,4,'#f1e7c8',2);}

/* ------------------------------------------------------------ the shop front */
function neon(c,w,x,y,wd,port){const open=w.c?.open,glow=open?(w.reduced?1:.85+.15*Math.sin(w.time*3)):.25;
  R(c,x,y,wd,port?50:56,'#2a2230',10,'#4a3a4a',3);c.save();c.shadowColor=PINK;c.shadowBlur=open?18*glow:0;
  T(c,'MÂY POP',x+wd/2,y+(port?25:28),fit(c,'MÂY POP',wd-60,port?28:32,900),open?PINK_L:'#8a6a7a',900);c.restore();
  heart(c,x+26,y+(port?30:33),.32,open?PINK:'#6a5a5a');heart(c,x+wd-26,y+(port?30:33),.32,open?PINK:'#6a5a5a');}
/** A poster in the window: a shape stands for the group, never a face. */
function poster(c,x,y,pw,ph,kind){R(c,x,y,pw,ph,'#fffaf4',4,'#a07a8a',1.5);const cx=x+pw/2,cy=y+ph*.45;
  if(kind===0){R(c,x+3,y+3,pw-6,ph-6,'#ffd3ea',3);heart(c,cx,cy+6,.62,PINK);T(c,'PINK',cx,y+ph-12,10,'#8a2b5a',900);}
  else if(kind===1){R(c,x+3,y+3,pw-6,ph-6,'#d8ecff',3);c.strokeStyle='#3f7fbf';c.lineWidth=3;c.beginPath();for(let a=0;a<12;a+=.3){const r=2+a*1.6;c.lineTo(cx+Math.cos(a)*r,cy+Math.sin(a)*r);}c.stroke();T(c,'7GIÓ',cx,y+ph-12,10,'#244f7a',900);}
  else{R(c,x+3,y+3,pw-6,ph-6,'#e4f6cf',3);E(c,cx,cy,pw*.3,pw*.3,'#6aa84f');E(c,cx,cy,pw*.22,pw*.22,'#b7e07a');E(c,cx,cy,pw*.06,pw*.06,'#fff6c8');T(c,'KIWIZ',cx,y+ph-12,9,'#3d6a2c',900);}}
function shopFront(c,w,f,x,wd,port){const top=f.base-(port?230:250);
  R(c,x,top,wd,f.base-top,'#f7e8ef',6,'#7a5a6a',2);R(c,x-8,top-14,wd+16,18,'#a0587e',7);
  neon(c,w,x+wd*.2,top+8,wd*.6,port);
  const gy=top+(port?70:76),gh=f.base-gy-6;R(c,x+12,gy,wd-24,gh,'#fff1f6',6,'#7a5a6a',2);
  const g=c.createLinearGradient(0,gy,0,gy+gh);g.addColorStop(0,'#ffe9f2');g.addColorStop(1,'#f7d3e2');c.fillStyle=g;c.fillRect(x+14,gy+2,wd-28,gh-4);
  // posters along the top of the glass
  const pw=port?50:58,ph=port?66:76,gap=port?10:16,n=port?3:4;
  for(let i=0;i<n;i++)poster(c,x+22+i*(pw+gap),gy+10,pw,ph,i%3);
  // the album wall behind the glass: rows of thin cases in many colours
  const wx=x+22+n*(pw+gap)+6,ww=x+wd-26-wx,rows=port?4:5;
  for(let r=0;r<rows;r++){const ry=gy+12+r*(port?30:28);R(c,wx,ry+22,ww,4,WOOD_D,2);
    for(let i=0;i<Math.floor(ww/12);i++){const col=ALBUM_COLS[(i*3+r*5)%ALBUM_COLS.length];R(c,wx+2+i*12,ry+2+((i+r)%3),10,20,col,2,'#6a5a6a',1);}}
  // the Búa hồng cabinet: pink hammers glow when the shop is open
  const open=w.c?.open,cx0=x+28,cy0=gy+ph+26,cw=port?120:150,ch=f.base-cy0-14;R(c,cx0,cy0,cw,ch,'#e9f4fb',6,'#7a8a9a',2);
  for(let i=0;i<3;i++){const hx=cx0+20+i*(cw-40)/2,hy=cy0+ch*.42,glow=open?(w.reduced?1:.75+.25*Math.sin(w.time*4+i)):0;
    if(open){c.save();c.shadowColor=PINK;c.shadowBlur=14*glow;}R(c,hx-10,hy-16,20,14,open?'#ff8cc6':'#d9a6bd',4);if(open)c.restore();
    L(c,hx,hy-2,hx,hy+ch*.36,'#efe6ee',5);}
  T(c,'BÚA HỒNG',cx0+cw/2,cy0+ch-10,port?10:11,'#6b3f5f',800);}

/* ------------------------------------------------------------ things on the pavement */
function boxes(c,x0,x1,fy,port){const W=x1-x0;E(c,(x0+x1)/2,fy+3,W/2+6,6,'#5a3a4a22');
  R(c,x0,fy-36,W,36,'#d9b58c',4,'#a5825e',1.5);R(c,x0+6,fy-62,W-16,26,'#e6c69c',4,'#a5825e',1.5);T(c,'ALBUM',x0+W/2,fy-18,port?10:11,'#6b4a33',800);
  T(c,'⇡ GIỮ KHÔ',x0+W/2,fy-49,port?9:10,'#6b4a33',800);}
function shelf(c,w,x0,x1,fy,port){const W=x1-x0,top=fy-(port?62:58);E(c,(x0+x1)/2,fy+3,W/2+8,7,'#5a3a4a22');
  R(c,x0,top,W,fy-top,'#f4e3d6',6,WOOD_D,2);for(let r=0;r<2;r++){const ry=top+6+r*((fy-top)/2);L(c,x0+4,ry+(fy-top)/2-8,x1-4,ry+(fy-top)/2-8,WOOD_D,3);
    for(let i=0;i<Math.floor((W-12)/11);i++)R(c,x0+6+i*11,ry+2,9,(fy-top)/2-12,ALBUM_COLS[(i+r*2)%ALBUM_COLS.length],2,'#6a5a6a',1);}
  const label=w.words().shelf;T(c,label,(x0+x1)/2,fy+12,fit(c,label,W,port?11:12),'#fff3f7',800);}
function counter(c,w,x0,x1,fy,port){const W=x1-x0,h=port?64:56,top=fy-h;E(c,(x0+x1)/2,fy+3,W/2+10,8,'#5a3a4a22');
  R(c,x0,top,W,h,'#f7e6ee',8,'#a0788a',2);R(c,x0-6,top-8,W+12,12,WOOD,5,WOOD_D,1.5);
  const label=w.words().counter;T(c,label,(x0+x1)/2,top+h/2+4,fit(c,label,W-24,port?15:13),'#6b3f5f',800);
  // the Zchart scanner: a red light when the shop is locked out
  const sx=x0+W*.7;R(c,sx,top-30,30,22,'#3a3340',4);R(c,sx+4,top-26,22,10,d(w).zban>=(w.c?.day||0)?'#e0573f':'#6fd08c',2);
  // a stack of albums waiting for their customer
  for(let i=0;i<4;i++)R(c,x0+W*.14,top-10-i*8,44,7,ALBUM_COLS[i%ALBUM_COLS.length],2,'#6a5a6a',1);}
function fansignBox(c,x0,x1,fy,port){const cx=(x0+x1)/2,h=port?90:96,top=fy-h;E(c,cx,fy+3,34,6,'#5a3a4a22');
  R(c,cx-32,top,64,h,'#ffd3ea',6,'#a0587e',2);R(c,cx-18,top+10,36,6,'#6a3a5a',3);heart(c,cx,top+48,.6,PINK);T(c,'FANSIGN',cx,top+h-14,port?9:10,'#6b2f47',900);}
function cashBox(c,w,x0,x1,fy,port){const cx=(x0+x1)/2;E(c,cx,fy+3,30,6,'#5a3a4a22');R(c,cx-14,fy-30,28,30,PINK,4);R(c,cx-28,fy-48,56,20,'#f2c84b',4,'#b88b2a',1.5);
  const label=w.words().ledger;R(c,cx-38,fy+2,76,port?20:18,'#fffaf0',8,'#c7ad90',1);T(c,label,cx,fy+(port?12:11),fit(c,label,68,port?11:10),'#6b3f5f',800);}
function standee(c,w,cx,fy,port){const open=w.c?.open,bw=port?118:104,bh=port?56:50,top=fy-bh-24;
  E(c,cx,fy+2,bw/2,6,'#5a3a4a22');L(c,cx-bw/2+12,top+bh,cx-bw/2+4,fy,WOOD_D,4);L(c,cx+bw/2-12,top+bh,cx+bw/2-4,fy,WOOD_D,4);
  R(c,cx-bw/2,top,bw,bh,'#3d3a44',8,WOOD_D,3);const s=open?(mod(w)==='comeback'?'COMEBACK!':'ALBUM MỚI'):w.words().closed_sign;
  T(c,s,cx,top+bh/2-7,fit(c,s,bw-14,port?15:13,800),'#fdf7e8',800);T(c,open?`POB còn ${Number(d(w).pob||0)}`:'mai mời ghé',cx,top+bh-11,port?11:10,'#ffb3d6',700);heart(c,cx+bw/2-12,top+10,.2,PINK);}

/* ------------------------------------------------------------ rooms */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land;
  if(port){E(c,350,862,320,22,'#cba88d22');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#a67a8a',33);}
  else{E(c,600,742,520,22,'#cba88d22');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#a67a8a',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  if(port){neighbour(c,24,262,150,f.base,'#e9d2c6','#9a7ab0');neighbour(c,520,250,160,f.base,'#d8e6c6','#7ab09a');shopFront(c,w,f,150,390,true);}
  else{neighbour(c,78,236,240,f.base,'#e9d2c6','#9a7ab0');neighbour(c,900,244,234,f.base,'#d8e6c6','#7ab09a');shopFront(c,w,f,320,580,false);}
  pavement(c,f);
  streetBoard(c,p,port?30:1013,port?282:322,port?1.6:1);
  rainLines(c,w,f);
  c.restore();
  const title=p.title||'Tiệm album Mây Pop';
  const [sx,sy,sw,sh]=f.sign;R(c,sx-5,sy+7,sw+10,sh,'#7a3a62',26);R(c,sx,sy,sw,sh,'#fff4fa',24,PINK,3);
  T(c,title,sx+sw/2,sy+40,fit(c,title,sw-60,30,800),'#6b2f57',800);T(c,p.sub||'',sx+sw/2,sy+sh-26,fit(c,p.sub||'',sw-60,13),'#8a5a7a');
  heart(c,sx+36,sy+sh/2+4,.5,PINK);P(c,[[sx+sw-48,sy+sh/2-12],[sx+sw-24,sy+sh/2],[sx+sw-48,sy+sh/2+12]],PINK);}

function props(w,p){const c=w.ctx,port=w.isPortrait(),b=w.plan().blocks,out=[];
  const [wh,wb,co,ev,fi,dr]=b;
  out.push([wh[3],()=>boxes(c,wh[0],wh[2],wh[3],port)]);
  out.push([wb[3],()=>shelf(c,w,wb[0],wb[2],wb[3],port)]);
  out.push([co[3],()=>counter(c,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>fansignBox(c,ev[0]-10,ev[2]+10,ev[3],port)]);
  out.push([fi[3],()=>cashBox(c,w,fi[0],fi[2],fi[3],port)]);
  out.push([dr[3],()=>standee(c,w,(dr[0]+dr[2])/2,dr[3],port)]);
  return out;
}

export default {
  id:'albumshop',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
};
