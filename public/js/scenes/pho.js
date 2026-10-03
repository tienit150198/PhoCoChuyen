/** Phở shop scene (kind `pho`): quán phở Cây Si, bác Lâm's shop at the ward corner. One frame of the
 * pavement in the early morning: the old banyan (cây si) with its hanging roots, the narrow tube house
 * with the open shutter, the yellow "PHỞ BÒ NAM ĐỊNH" board and the menu inside; in front, the quẩy
 * basket, the low table and plastic stools, the big broth pot on its stove (steam while the shop is
 * open), the herb basket, the cash box and the price board. The footprints are the sidewalk scene's
 * (the same walkable plan), so the props stand where that plan keeps the floor clear. */
import {R,E,L,T,P,fit} from './kit.js';
import {PLAN} from './sidewalk.js';

const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,sign:[135,30,430,104]}};
const WALL='#f0d79a',WALL_D='#d6b36c',RED='#b8432f',RED_D='#86301f',YEL='#f4c84a',WOOD='#9a6a43',WOOD_D='#6f4a2c',STEEL='#b9bec4',STEEL_D='#8a9097';
const STOOL=['#d9534f','#3f7fbf','#d9534f','#e2a93b'];
const data=w=>w.c?.data||{};
const mod=w=>data(w).mod?.id||'normal';

/* ------------------------------------------------------------ backdrop */
function sky(c,w,f){const m=mod(w),grey=m==='rain'||m==='cold',g=c.createLinearGradient(0,f.y,0,f.base);
  g.addColorStop(0,grey?'#aebac4':m==='early'?'#f3c9a0':'#d9ecf2');g.addColorStop(1,grey?'#dde0dc':'#fbecd2');
  c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  if(!grey)E(c,f===F.port?600:1040,f===F.port?182:170,24,24,m==='early'?'#ffd9a0':'#fff3c4');}
/** The old banyan: a thick trunk, a dark crown and hanging aerial roots. */
function banyan(c,x,base,port){const h=port?300:320,top=base-h;
  P(c,[[x-34,base],[x-20,top+120],[x+22,top+120],[x+38,base]],'#7b6248');L(c,x-6,base,x-10,top+140,'#634e39',4);L(c,x+16,base,x+12,top+150,'#634e39',3);
  for(const [dx,dy,rx,ry,col] of [[-90,40,110,70,'#4f7d45'],[60,30,120,75,'#5b8b4f'],[-10,-10,130,80,'#679a58'],[-120,90,70,45,'#5b8b4f'],[110,95,80,46,'#4f7d45']])E(c,x+dx,top+dy+60,rx,ry,col);
  for(let i=0;i<9;i++){const rx=x-120+i*30;L(c,rx,top+120+(i%3)*10,rx+(i%2?3:-2),top+210+(i%4)*22,'#7b624888',2);}}
/** The tube house: shutter rolled up, yellow board, the menu inside, an awning. */
function shop(c,x,base,wd,port){const h=port?250:270,top=base-h;
  R(c,x,top,wd,h,WALL,4,WALL_D,2);
  R(c,x+16,top+16,wd-32,port?40:46,YEL,6,RED_D,3);T(c,'PHỞ BÒ NAM ĐỊNH',x+wd/2,top+(port?36:39),fit(c,'PHỞ BÒ NAM ĐỊNH',wd-60,port?20:24,900),RED_D,900);
  const dy=top+(port?70:78),dh=base-dy;R(c,x+24,dy,wd-48,dh,'#4a3326',4);R(c,x+24,dy-10,wd-48,12,STEEL_D,3);
  for(let i=0;i<4;i++)L(c,x+26,dy-8+i*3,x+wd-26,dy-8+i*3,'#ffffff44',1);
  // Inside: warm light, the menu board on the back wall.
  const g=c.createLinearGradient(0,dy,0,base);g.addColorStop(0,'#8a5a36');g.addColorStop(1,'#5b3a26');c.fillStyle=g;c.fillRect(x+30,dy+4,wd-60,dh-4);
  const mw=Math.min(190,wd*.42),mx=x+wd/2-mw/2;R(c,mx,dy+18,mw,port?78:86,'#2f3b33',6,WOOD,3);
  T(c,'THỰC ĐƠN',mx+mw/2,dy+32,12,'#f3e3b4',800);
  ['Phở tái · chín · nạm','Phở gầu · gân · bò viên','Tô lớn · trứng trần · quẩy'].forEach((s,i)=>T(c,s,mx+mw/2,dy+50+i*16,fit(c,s,mw-16,11,600),'#fdf7e8',600));
  E(c,x+wd*.22,dy+20,16,9,'#ffe7a8');E(c,x+wd*.78,dy+20,16,9,'#ffe7a8');
  // The awning.
  P(c,[[x-10,dy-4],[x+wd+10,dy-4],[x+wd+26,dy+26],[x-26,dy+26]],'#c9563a');
  for(let i=0;i<8;i++){const sx=x-10+i*(wd+20)/8;P(c,[[sx,dy-4],[sx+(wd+20)/16,dy-4],[sx+(wd+20)/16+4,dy+26],[sx+4,dy+26]],'#f2e6d0');}}
function wires(c,f){c.strokeStyle='#3b3b3b88';c.lineWidth=1.5;for(let i=0;i<3;i++){c.beginPath();c.moveTo(f.x,f.y+30+i*12);c.quadraticCurveTo(f.x+f.w/2,f.y+70+i*14,f.x+f.w,f.y+36+i*10);c.stroke();}}
function pavement(c,f){const {base}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,bottom-base,'#d8c3a5',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,bottom-base);c.clip();const tw=f===F.port?52:60;
  for(let y=base,row=0;y<bottom;y+=tw/2,row++)for(let x=f.x;x<f.x+f.w;x+=tw){c.fillStyle=(row+(x/tw|0))%2?'#d2b998':'#cdb391';c.fillRect(x+1.5,y+1.5,tw-3,tw/2-3);}
  c.restore();L(c,f.x,base,f.x+f.w,base,'#a98c6b',2);}

/* ------------------------------------------------------------ props */
function quayBasket(c,w,x0,x1,fy){const W=x1-x0,cx=(x0+x1)/2;L(c,cx-W*.3,fy,cx-W*.22,fy-40,WOOD_D,4);L(c,cx+W*.3,fy,cx+W*.22,fy-40,WOOD_D,4);
  E(c,cx,fy-44,W*.45,12,'#c99a5a');E(c,cx,fy-48,W*.4,8,'#b07f45');
  for(let i=0;i<5;i++){const qx=cx-W*.3+i*W*.15;c.save();c.translate(qx,fy-54);c.rotate(-.5+i*.25);R(c,-5,-16,10,30,'#e0a64a',5,'#b8782f',1.2);c.restore();}
  const label=w.words().shelf;T(c,label,cx,fy+14,fit(c,label,W+30,12),'#5a3f2c',800);}
function seats(c,x0,x1,fy){const W=x1-x0;R(c,x0+W*.22,fy-44,W*.56,10,'#e7e2d8',3,'#b8b0a2',1.5);L(c,x0+W*.28,fy-34,x0+W*.28,fy-6,'#9aa0a6',3);L(c,x0+W*.72,fy-34,x0+W*.72,fy-6,'#9aa0a6',3);
  E(c,x0+W*.4,fy-48,10,4,'#fbf6ec');E(c,x0+W*.6,fy-48,8,3,'#e7c56a');
  for(const [i,sx] of [[0,x0+8],[1,x0+W-38]]){R(c,sx,fy-24,30,8,STOOL[i],3);L(c,sx+4,fy-16,sx+2,fy,STOOL[i],3);L(c,sx+26,fy-16,sx+28,fy,STOOL[i],3);}}
function potStove(c,w,x0,x1,fy,port){const W=x1-x0,cx=(x0+x1)/2,pw=Math.min(130,W*.72),ph=port?92:86,top=fy-ph-28;
  // The stove: a brick base with a fire mouth.
  R(c,cx-pw/2-8,fy-30,pw+16,30,'#9c5a3c',5,'#6f3b26',2);E(c,cx,fy-14,16,8,data(w).shop?.open||w.c?.open?'#f08a3a':'#5a3a2a');
  // The pot: steel, a lid half open, the ladle hanging on the rim.
  R(c,cx-pw/2,top,pw,ph,STEEL,10,STEEL_D,2.5);E(c,cx,top+2,pw/2,9,'#cfd3d7');E(c,cx,top+4,pw/2-6,6,'#c98a2c');
  R(c,cx-pw/2-10,top+18,10,8,STEEL_D,3);R(c,cx+pw/2,top+18,10,8,STEEL_D,3);
  for(let i=0;i<3;i++)L(c,cx-pw/2+8,top+30+i*18,cx+pw/2-8,top+30+i*18,'#ffffff33',1.5);
  L(c,cx+pw*.22,top-24,cx+pw*.3,top+8,'#b8782f',3);E(c,cx+pw*.21,top-26,8,5,'#c98a2c');
  if(w.c?.open)for(let i=0;i<3;i++){c.strokeStyle='#ffffffaa';c.lineWidth=4;c.beginPath();c.moveTo(cx-24+i*22,top-6);
    c.bezierCurveTo(cx-40+i*26,top-40,cx-6+i*20,top-62,cx-20+i*24,top-96);c.stroke();}
  const label=w.words().counter;T(c,label,cx,fy+14,fit(c,label,W+20,port?13:12),'#5a3f2c',800);}
function herbs(c,x0,x1,fy){const cx=(x0+x1)/2,W=x1-x0+16;E(c,cx,fy-8,W/2,10,'#b8915a');E(c,cx,fy-12,W/2-4,7,'#d8b47a');
  for(let i=0;i<7;i++)E(c,cx-W/2+10+i*(W-20)/6,fy-18-(i%2)*5,7,6,i%3?'#5f9a4f':'#7fb36a');for(let i=0;i<4;i++)E(c,cx-10+i*7,fy-14,3,2,'#f4f0dc');}
function cashBox(c,w,x0,x1,fy){const W=x1-x0,cx=(x0+x1)/2;L(c,x0+12,fy,x0+14,fy-30,WOOD_D,4);L(c,x1-12,fy,x1-14,fy-30,WOOD_D,4);R(c,x0+4,fy-36,W-8,8,WOOD,3);
  R(c,cx-24,fy-62,48,26,'#3f7fbf',4,'#2c5a88',2);R(c,cx-10,fy-58,20,4,'#2c5a88',2);
  const label=w.words().finance;T(c,label,cx,fy+12,fit(c,label,W+20,11),'#5a3f2c',800);}
function priceBoard(c,cx,fy,port){const bw=port?112:104,bh=port?62:58,top=fy-bh-18;L(c,cx-bw/2+12,top+bh,cx-bw/2+4,fy,WOOD_D,4);L(c,cx+bw/2-12,top+bh,cx+bw/2-4,fy,WOOD_D,4);
  R(c,cx-bw/2,top,bw,bh,'#2f3b33',8,WOOD,3);T(c,'PHỞ BÒ',cx,top+16,fit(c,'PHỞ BÒ',bw-14,15,900),'#fdf7e8',900);
  T(c,'Tô 30 · Lớn 38',cx,top+34,fit(c,'Tô 30 · Lớn 38',bw-12,11,700),'#f3d98a',700);T(c,'Mang về 32',cx,top+49,fit(c,'Mang về 32',bw-12,11,700),'#f3d98a',700);}

/* ------------------------------------------------------------ the frame */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land;
  if(port){E(c,350,862,320,22,'#cba88d22');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#b88b62',33);}
  else{E(c,600,742,520,22,'#cba88d22');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#b88b62',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);wires(c,f);
  if(port){shop(c,190,f.base,430,true);banyan(c,110,f.base,true);}
  else{R(c,820,f.base-230,300,230,'#e9c9a3',4,'#cfa77c',2);for(let i=0;i<3;i++)R(c,850+i*90,f.base-190,60,70,'#8fb3c9',4,'#6f8fa3',2);
    shop(c,330,f.base,470,false);banyan(c,190,f.base,false);}
  pavement(c,f);
  if(mod(w)==='rain'||mod(w)==='cold'){c.strokeStyle=mod(w)==='rain'?'#ffffff66':'#ffffff33';c.lineWidth=1.5;
    for(let i=0;i<40;i++){const rx=f.x+((i*97)%f.w),ry=f.y+((i*53)%(f.h-60));c.beginPath();c.moveTo(rx,ry);c.lineTo(rx-6,ry+18);c.stroke();}}
  c.restore();
  const title=p.title||'',[sx,sy,sw,sh]=f.sign;R(c,sx-5,sy+7,sw+10,sh,RED_D,26);R(c,sx,sy,sw,sh,'#fff4dc',24,YEL,3);
  T(c,title,sx+sw/2,sy+40,fit(c,title,sw-60,30,800),'#5a3f2c',800);T(c,p.sub||'',sx+sw/2,sy+sh-26,fit(c,p.sub||'',sw-60,13),'#7b5b44');
  E(c,sx+36,sy+sh/2,14,14,p.primary||RED);E(c,sx+sw-36,sy+sh/2,14,14,p.primary||RED);}

function props(w){const c=w.ctx,port=w.isPortrait(),b=w.plan().blocks,out=[];
  const [wh,wb,co,ev,fi,dr]=b,mid=r=>(r[0]+r[2])/2;
  out.push([wh[3],()=>quayBasket(c,w,wh[0],wh[2],wh[3])]);
  out.push([wb[3],()=>seats(c,wb[0],wb[2],wb[3])]);
  out.push([co[3],()=>potStove(c,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>herbs(c,ev[0],ev[2],ev[3])]);
  out.push([fi[3],()=>cashBox(c,w,fi[0],fi[2],fi[3])]);
  out.push([dr[3],()=>priceBoard(c,mid(dr),dr[3],port)]);
  return out;
}

export default {
  id:'pho',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
};
