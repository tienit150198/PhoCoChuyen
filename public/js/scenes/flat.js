/** Giúp việc scene (kind `flat`): the lobby of chung cư Mây where cô Mai's Nhà Thơm team sets off. A morning sky,
 * the tower block with its balconies and potted plants, the glass lobby door, a clothesline with the three colours of
 * cloth (blue, yellow, red), the crate of bottles, the cleaning cart with bucket and mop, the booking board with
 * today's flats, the little wallet for the pay and the chalk standee on the pavement. The cart's own state (out,
 * cloths, bottles) comes from the career's public data. Footprints follow the sidewalk plan (see shop.js). */
import {R,E,L,T,P,fit,heart,streetBoard} from './kit.js';
import {PLAN} from './sidewalk.js';

export {PLAN};
const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,curb:668,road:680,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,curb:800,road:812,sign:[135,30,430,104]}};
const TEAL='#3f9d8f',TEAL_L='#e2f4f0',TEAL_D='#2c7166',WALL='#efe6da',WALL_D='#cdbfae',GLASS='#cfe6ee';
const CLOTH={xanh:'#4f8fd8',vang:'#f2c84b',do:'#e0573f'};
const d=w=>w.c?.data||{};
const mod=w=>d(w).mod?.id||'normal';
const cart=w=>d(w).cart||{};

/* ------------------------------------------------------------ backdrop */
function sky(c,w,f){const wet=mod(w)==='mua'||mod(w)==='nom',g=c.createLinearGradient(0,f.y,0,f.base);
  g.addColorStop(0,wet?'#8a95a3':'#9fd3ea');g.addColorStop(1,wet?'#d4d6d4':'#fdf1d8');c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  if(!wet){const port=f===F.port;E(c,port?600:1060,port?186:176,26,26,'#fff3b0');}
  for(let i=0;i<4;i++){const x=f.x+80+i*f.w/4,y=f.y+40+(i%2)*26;E(c,x,y,46,13,'#ffffffaa');E(c,x+26,y-8,30,12,'#ffffffaa');}}
function rainLines(c,w,f){if(mod(w)!=='mua')return;const t=w.reduced?0:(w.time*220)%40;c.strokeStyle='#e8eef455';c.lineWidth=1.5;
  for(let x=f.x+10;x<f.x+f.w;x+=26)for(let y=f.y+((x/26|0)%3)*14-40+t;y<f.curb;y+=40){c.beginPath();c.moveTo(x,y);c.lineTo(x-6,y+16);c.stroke();}}
function dust(c,w,f){if(mod(w)!=='bui')return;for(let i=0;i<22;i++){const x=f.x+((i*131+(w.reduced?0:w.time*18))%f.w),y=f.y+60+((i*71)%(f.base-f.y-80));E(c,x,y,2,2,'#d9b98a88');}}
function pavement(c,f){const {base,curb,road}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,curb-base,'#e6ddd0',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,curb-base);c.clip();const tw=f===F.port?46:52,th=f===F.port?46:40;
  for(let y=base,row=0;y<curb;y+=th,row++)for(let x=f.x;x<f.x+f.w;x+=tw){c.fillStyle=((x/tw|0)+row)%2?'#ddd2c3':'#ece4d8';c.fillRect(x+1.5,y+1.5,tw-3,th-3);}
  c.restore();R(c,f.x,curb,f.w,road-curb,'#b9b2aa',0);L(c,f.x,curb,f.x+f.w,curb,'#958d84',2);R(c,f.x,road,f.w,bottom-road,'#6f7680',0);
  for(let x=f.x+30;x<f.x+f.w;x+=120)R(c,x,road+(bottom-road)/2-2,56,4,'#f1e7c8',2);}

/* ------------------------------------------------------------ the tower block */
function windows(c,x,top,wd,base,cols,rows){const cw=wd/cols,rh=(base-top)/rows;
  for(let r=0;r<rows;r++)for(let k=0;k<cols;k++){const wx=x+k*cw+cw*.18,wy=top+r*rh+rh*.18;
    R(c,wx,wy,cw*.64,rh*.5,(r+k)%3?GLASS:'#fff1c8',4,WALL_D,1.5);R(c,wx-4,wy+rh*.5,cw*.64+8,6,'#d8cbbb',2);
    if((r*3+k)%4===1){E(c,wx+cw*.12,wy+rh*.5-6,7,7,'#6fae6a');E(c,wx+cw*.22,wy+rh*.5-10,6,6,'#82c27c');}}}
function tower(c,w,f,x,wd,port){const top=f.y+(port?26:20),base=f.base;
  R(c,x,top,wd,base-top,WALL,8,WALL_D,2);R(c,x-8,top-10,wd+16,16,'#c9b8a6',6);
  windows(c,x+8,top+14,wd-16,base-(port?150:140),port?4:6,port?4:3);
  // the lobby: a glass door and the name over it
  const lx=x+wd*.3,lw=wd*.4,lt=base-(port?120:112);R(c,lx-10,lt-30,lw+20,30,TEAL,6);
  const name='CHUNG CƯ MÂY';T(c,name,lx+lw/2,lt-15,fit(c,name,lw-10,port?15:16,800),'#fff',800);
  R(c,lx,lt,lw,base-lt,'#b9dce6',4,TEAL_D,2.5);L(c,lx+lw/2,lt,lx+lw/2,base,TEAL_D,2);
  const out=cart(w).out;if(out){P(c,[[lx+lw/2,lt+2],[lx+lw-4,lt+8],[lx+lw-4,base-2],[lx+lw/2,base]],'#e6f4f8');}
  E(c,lx+lw/2-8,lt+(base-lt)/2,3,3,'#8a8a8a');E(c,lx+lw/2+8,lt+(base-lt)/2,3,3,'#8a8a8a');
  // the clothesline with the three colours of cloth
  const cy=lt-(port?70:62),cx0=x+16,cx1=lx-18;L(c,cx0,cy,cx1,cy,'#7a6a5a',1.5);
  const clean=cart(w).cloths==='clean',cols=[CLOTH.xanh,CLOTH.vang,CLOTH.do,CLOTH.xanh,CLOTH.vang];
  for(let i=0;i<cols.length;i++){const px=cx0+12+i*(cx1-cx0-24)/cols.length,sway=w.reduced?0:Math.sin(w.time*1.6+i)*2;
    P(c,[[px,cy],[px+18,cy],[px+20+sway,cy+26],[px+2+sway,cy+26]],clean?cols[i]:cols[i]+'99');R(c,px+6,cy-3,5,7,'#c9a46a',1);}}

/* ------------------------------------------------------------ props on the pavement */
function bottleCrate(c,w,x0,x1,fy,port){const W=x1-x0;E(c,(x0+x1)/2,fy+3,W/2+6,6,'#3a4a4a22');
  R(c,x0,fy-34,W,34,'#8fc1b8',5,TEAL_D,1.5);for(let i=1;i<4;i++)L(c,x0+i*W/4,fy-34,x0+i*W/4,fy,TEAL_D,1);
  const cols=['#9fd8ff','#f7b6c8','#f2c84b','#9be0a0','#e9a0ff'];
  for(let i=0;i<5;i++){const bx=x0+8+i*(W-16)/5;R(c,bx,fy-58,(W-16)/5-6,26,cols[i],5,'#6a7a7a',1);R(c,bx+((W-16)/5-6)/2-3,fy-66,6,9,'#fff',2,'#6a7a7a',1);}
  T(c,'CHAI',(x0+x1)/2,fy-15,port?10:11,'#fff',800);}
function cleaningCart(c,w,x0,x1,fy,port){const W=x1-x0,top=fy-(port?70:64),out=cart(w).out;E(c,(x0+x1)/2,fy+3,W/2+8,7,'#3a4a4a22');
  if(out){T(c,'🛵',(x0+x1)/2,fy-22,port?30:28,'#333',400);T(c,'Đã lên đường',(x0+x1)/2,fy+12,port?11:12,'#fff',800);return;}
  R(c,x0+6,top,W-12,top>0?fy-top-12:0,'#e9eef0',6,'#7a8a8a',2);L(c,x0+6,top+22,x1-6,top+22,'#7a8a8a',1.5);
  E(c,x0+18,fy-6,7,7,'#3a3a3a');E(c,x1-18,fy-6,7,7,'#3a3a3a');L(c,x1-6,top+4,x1+10,top-18,'#7a8a8a',3);
  // a bucket and a mop on the cart, folded cloths on the top shelf
  P(c,[[x0+16,top+30],[x0+W*.45,top+30],[x0+W*.42,fy-14],[x0+19,fy-14]],'#4f8fd8');R(c,x0+14,top+26,W*.45-12,6,'#3a6fae',2);
  L(c,x0+W*.3,top+28,x0+W*.36,top-40,'#b88b62',4);R(c,x0+W*.28,top-48,W*.18,10,'#f2f2f2',4,'#c0c0c0',1);
  const cl=cart(w).cloths==='clean';[CLOTH.xanh,CLOTH.vang,CLOTH.do].forEach((col,i)=>R(c,x0+W*.55+i*(W*.13),top+6,W*.11,12,cl?col:col+'88',3));
  T(c,w.words().counter,(x0+x1)/2,fy+12,fit(c,w.words().counter,W,port?11:12),'#fff',800);}
function washTub(c,w,x0,x1,fy,port){const W=x1-x0,cx=(x0+x1)/2,clean=cart(w).cloths==='clean';E(c,cx,fy+3,W/2+6,7,'#3a4a4a22');
  P(c,[[x0+W*.12,fy-34],[x1-W*.12,fy-34],[x1-W*.2,fy],[x0+W*.2,fy]],'#e07a5f');R(c,x0+W*.1,fy-38,W*.8,8,'#c85f45',4);
  E(c,cx,fy-36,W*.36,5,clean?'#cfe9f2':'#c9c0a8');for(let i=0;i<5;i++)E(c,x0+W*(.25+i*.12),fy-40-(i%2)*4,5,5,'#ffffffcc');
  [CLOTH.xanh,CLOTH.vang,CLOTH.do].forEach((col,i)=>R(c,x1-W*.12+4,fy-30+i*9,W*.1,7,clean?col:col+'88',2));
  T(c,w.words().shelf,cx,fy+12,fit(c,w.words().shelf,W,port?11:12),'#fff',800);}
function bookingBoard(c,w,x0,x1,fy,port){const cx=(x0+x1)/2,h=port?96:104,top=fy-h;L(c,cx-22,fy,cx,top,'#8f6746',4);L(c,cx+22,fy,cx,top,'#8f6746',4);
  R(c,cx-36,top+8,72,70,'#fffaf2',4,'#8f6746',2);T(c,'LỊCH HẸN',cx,top+18,port?9:10,TEAL_D,800);
  for(let i=0;i<4;i++){L(c,cx-28,top+32+i*11,cx+18,top+32+i*11,'#b8a898',1.5);E(c,cx+24,top+32+i*11,3,3,i<(d(w).today?.jobs||0)?'#3fae6a':'#d8cbbb');}
  T(c,w.words().evidence,cx,top+90,fit(c,w.words().evidence,80,port?9:10),'#4a3a2a',800);}
function wallet(c,w,x0,x1,fy,port){const cx=(x0+x1)/2;E(c,cx,fy+3,30,6,'#3a4a4a22');R(c,cx-22,fy-30,44,28,TEAL,6,TEAL_D,1.5);R(c,cx-22,fy-30,44,10,TEAL_D,4);
  E(c,cx+12,fy-18,4,4,'#f2c84b');const label=w.words().ledger;R(c,cx-40,fy+2,80,port?20:18,'#fffaf0',8,'#c7ad90',1);T(c,label,cx,fy+(port?12:11),fit(c,label,72,port?11:10),'#2c5a52',800);}
function standee(c,w,cx,fy,port){const open=w.c?.open,bw=port?118:104,bh=port?56:50,top=fy-bh-24;
  E(c,cx,fy+2,bw/2,6,'#3a4a4a22');L(c,cx-bw/2+12,top+bh,cx-bw/2+4,fy,'#8f6746',4);L(c,cx+bw/2-12,top+bh,cx+bw/2-4,fy,'#8f6746',4);
  R(c,cx-bw/2,top,bw,bh,'#3d4a48',8,'#8f6746',3);const s=open?w.words().open_sign:w.words().closed_sign;
  T(c,s,cx,top+bh/2-7,fit(c,s,bw-14,port?14:12,800),'#fdf7e8',800);T(c,open?'dọn theo giờ':'mai mời gọi',cx,top+bh-11,port?11:10,'#9fe0d4',700);heart(c,cx+bw/2-12,top+10,.2,TEAL);}

/* ------------------------------------------------------------ rooms */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land;
  if(port){E(c,350,862,320,22,'#a8c8c022');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#7aa79f',33);}
  else{E(c,600,742,520,22,'#a8c8c022');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#7aa79f',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  if(port)tower(c,w,f,70,560,true);else tower(c,w,f,240,720,false);
  pavement(c,f);
  streetBoard(c,p,port?30:1013,port?282:322,port?1.6:1);
  rainLines(c,w,f);dust(c,w,f);
  c.restore();
  const title=p.title||'Tổ giúp việc Nhà Thơm';
  const [sx,sy,sw,sh]=f.sign;R(c,sx-5,sy+7,sw+10,sh,TEAL_D,26);R(c,sx,sy,sw,sh,TEAL_L,24,TEAL,3);
  T(c,title,sx+sw/2,sy+40,fit(c,title,sw-60,30,800),'#22574f',800);T(c,p.sub||'',sx+sw/2,sy+sh-26,fit(c,p.sub||'',sw-60,13),'#3f6f67');
  heart(c,sx+36,sy+sh/2+4,.5,TEAL);[CLOTH.xanh,CLOTH.vang,CLOTH.do].forEach((col,i)=>R(c,sx+sw-50+i*10,sy+sh/2-10,8,20,col,2));}

function props(w,p){const c=w.ctx,port=w.isPortrait(),b=w.plan().blocks,out=[];
  const [wh,wb,co,ev,fi,dr]=b;
  out.push([wh[3],()=>bottleCrate(c,w,wh[0],wh[2],wh[3],port)]);
  out.push([wb[3],()=>washTub(c,w,wb[0],wb[2],wb[3],port)]);
  out.push([co[3],()=>cleaningCart(c,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>bookingBoard(c,w,ev[0]-12,ev[2]+12,ev[3],port)]);
  out.push([fi[3],()=>wallet(c,w,fi[0],fi[2],fi[3],port)]);
  out.push([dr[3],()=>standee(c,w,(dr[0]+dr[2])/2,dr[3],port)]);
  return out;
}

export default {
  id:'flat',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
};
