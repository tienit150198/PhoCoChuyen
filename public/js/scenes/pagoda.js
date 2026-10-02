/** Pagoda scene (kind `pagoda`): chùa Gió Lành by the river landing. One frame of the pagoda yard:
 * the main hall with its curved tiled roof, the three-entrance gate with a row of areca palms, the
 * bell tower with the dented bronze bell, the brick yard; in front, the broom rack, the bonsai pots,
 * the big incense burner (smoke when the gate is open), the lotus basin, the donation box and the
 * "keep quiet" sign. The footprints are the sidewalk scene's (the same walkable plan), so the props
 * stand where that plan keeps the floor clear. */
import {R,E,L,T,P,fit} from './kit.js';
import {PLAN} from './sidewalk.js';

const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,sign:[135,30,430,104]}};
const RED='#a8432f',RED_D='#7d2f21',TILE='#8a4b33',GOLD='#d9a441',WALL='#f3e3c1',WALL_D='#d6b394';
const data=w=>w.c?.data||{};

/* ------------------------------------------------------------ backdrop */
function sky(c,w,f){const g=c.createLinearGradient(0,f.y,0,f.base),rain=data(w).mod?.id==='rain';
  g.addColorStop(0,rain?'#b8c4cc':'#d7ebe6');g.addColorStop(1,rain?'#dfe2dc':'#fbefd6');
  c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  if(data(w).mod?.id==='ram')E(c,f===F.port?600:1030,f===F.port?190:176,24,24,'#fff6d2');else if(!rain)E(c,f===F.port?610:1040,f===F.port?180:172,26,26,'#fff3c4');}
/** A tiled roof whose ends curl up like a boat. */
function roof(c,x,y,wd,h){P(c,[[x-24,y+h],[x+14,y],[x+wd-14,y],[x+wd+24,y+h]],TILE);
  for(let i=1;i<5;i++)L(c,x-24+i*6,y+h-i*h/5,x+wd+24-i*6,y+h-i*h/5,'#6d3a27',1.2);
  P(c,[[x-30,y+h+2],[x-44,y+h-18],[x-18,y+h-2]],TILE);P(c,[[x+wd+30,y+h+2],[x+wd+44,y+h-18],[x+wd+18,y+h-2]],TILE);
  L(c,x+10,y,x+wd-10,y,RED_D,5);E(c,x+wd/2,y-8,10,7,GOLD);}
function hall(c,x,base,wd,port){const h=port?150:170,top=base-h;R(c,x,top,wd,h,WALL,4,WALL_D,2);
  roof(c,x,top-(port?46:52),wd,port?46:52);
  const n=port?3:5,dw=wd/n;for(let i=0;i<n;i++){const dx=x+i*dw+dw*.18;R(c,dx,top+40,dw*.64,h-40,i===(n-1)/2?RED:'#b85c42',4,RED_D,2);
    for(let k=0;k<3;k++)L(c,dx+6,top+60+k*28,dx+dw*.64-6,top+60+k*28,'#ffffff33',1.5);}
  for(let i=0;i<=n;i++)R(c,x+i*dw-5,top+20,10,h-20,RED_D,3);
  R(c,x+wd/2-80,top+6,160,26,'#2f2a26',4,GOLD,2);T(c,'ĐẠI HÙNG BẢO ĐIỆN',x+wd/2,top+19,port?10:11,GOLD,800);}
function gate(c,x,base,wd,port){const h=port?120:136,top=base-h;
  for(const [gx,gw,gh] of [[x,wd*.28,h*.78],[x+wd*.72,wd*.28,h*.78],[x+wd*.3,wd*.4,h]]){const gt=base-gh;R(c,gx,gt,gw,gh,WALL,3,WALL_D,2);
    roof(c,gx+6,gt-22,gw-12,22);R(c,gx+gw*.25,gt+gh*.35,gw*.5,gh*.65,'#5a3a2a',gw*.25);}
  T(c,'CHÙA GIÓ LÀNH',x+wd/2,top+22,port?11:12,RED_D,800);}
function areca(c,x,base,h){L(c,x,base,x+3,base-h,'#9c8b6e',5);for(let i=0;i<6;i++){const a=-Math.PI/2+(i-2.5)*.5;
  L(c,x+3,base-h,x+3+Math.cos(a)*34,base-h+Math.sin(a)*22+16,'#5f8f4a',4);}E(c,x+3,base-h+8,6,8,'#c9a24a');}
function bellTower(c,x,base,port){const wd=port?70:84,h=port?170:196,top=base-h;L(c,x+8,base,x+8,top+30,RED_D,6);L(c,x+wd-8,base,x+wd-8,top+30,RED_D,6);
  roof(c,x+4,top,wd-8,30);L(c,x+wd/2,top+32,x+wd/2,top+50,'#3b3b3b',2);
  P(c,[[x+wd/2-18,top+92],[x+wd/2-13,top+52],[x+wd/2+13,top+52],[x+wd/2+18,top+92]],'#8a6a3a');E(c,x+wd/2+9,top+76,4,6,'#6b4f2a');
  R(c,x+4,base-34,wd-8,8,WALL_D,2);}
function yard(c,f){const {base}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,bottom-base,'#dcb995',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,bottom-base);c.clip();const tw=f===F.port?44:50,th=f===F.port?24:22;
  for(let y=base,row=0;y<bottom;y+=th,row++)for(let x=f.x-(row%2)*tw/2;x<f.x+f.w;x+=tw){c.fillStyle=((x/tw|0)+row)%3?'#d6ad86':'#cfa37b';c.fillRect(x+1.5,y+1.5,tw-3,th-3);}
  c.restore();L(c,f.x,base,f.x+f.w,base,'#b88b62',2);}

/* ------------------------------------------------------------ props */
function brooms(c,x0,x1,fy){const W=x1-x0;R(c,x0+4,fy-60,W-8,6,'#8f6746',2);for(let i=0;i<3;i++){const x=x0+14+i*(W-28)/2;L(c,x,fy-58,x+2,fy-18,'#b88b62',3);P(c,[[x-10,fy],[x+12,fy],[x+6,fy-20],[x-4,fy-20]],'#d9b97a');}}
function bonsai(c,x0,x1,fy){const W=x1-x0;for(let i=0;i<2;i++){const x=x0+W*(i+.5)/2;R(c,x-20,fy-18,40,16,'#4f6f8f',4,'#2f4f6f',1.5);
  L(c,x,fy-18,x-6,fy-34,'#7a5a3c',4);L(c,x-6,fy-34,x+8,fy-46,'#7a5a3c',3);E(c,x-10,fy-40,14,8,'#5f8f4a');E(c,x+10,fy-50,14,8,'#6f9f5a');}}
function burner(c,w,x0,x1,fy,port){const W=x1-x0,cx=(x0+x1)/2,h=port?70:62,top=fy-h;E(c,cx,fy+3,W/2+6,7,'#6b584420');
  L(c,cx-W*.3,fy,cx-W*.26,top+40,'#6b4f2a',5);L(c,cx+W*.3,fy,cx+W*.26,top+40,'#6b4f2a',5);
  E(c,cx,top+34,W*.42,22,'#8a6a3a');E(c,cx,top+18,W*.4,8,'#6b4f2a');R(c,cx-W*.42,top+12,10,18,'#8a6a3a',4);R(c,cx+W*.42-10,top+12,10,18,'#8a6a3a',4);
  for(let i=0;i<5;i++)L(c,cx-16+i*8,top+16,cx-16+i*8,top-6,'#b8432f',1.5);
  if(w.c?.open)for(let i=0;i<3;i++){c.strokeStyle='#ffffff88';c.lineWidth=3;c.beginPath();c.moveTo(cx-8+i*8,top-8);c.bezierCurveTo(cx-20+i*12,top-40,cx+10+i*6,top-60,cx-4+i*10,top-90);c.stroke();}
  const label=w.words().counter;T(c,label,cx,fy+14,fit(c,label,W+20,port?13:11),'#5a3f2c',800);}
function lotus(c,x0,x1,fy){const cx=(x0+x1)/2,W=x1-x0+16;E(c,cx,fy-10,W/2,14,'#8f6746');E(c,cx,fy-13,W/2-5,10,'#6fa3a8');
  E(c,cx-10,fy-14,9,4,'#5f8f4a');E(c,cx+12,fy-12,8,4,'#5f8f4a');for(let i=0;i<5;i++){const a=i*Math.PI/5;E(c,cx+2+Math.cos(a)*6,fy-22-Math.sin(a)*4,5,8,'#f2a8b8');}E(c,cx+2,fy-22,3,3,'#f3d590');}
function donation(c,w,x0,x1,fy){const W=x1-x0,cx=(x0+x1)/2;R(c,x0+8,fy-50,W-16,48,RED,5,RED_D,2);R(c,cx-14,fy-46,28,5,'#2f2a26',2);
  const label=w.words().finance;T(c,label,cx,fy-24,fit(c,label,W-24,10),GOLD,800);}
function quietSign(c,cx,fy,port){const bw=port?118:108,bh=port?56:50,top=fy-bh-22;L(c,cx-bw/2+12,top+bh,cx-bw/2+4,fy,'#8f6746',4);L(c,cx+bw/2-12,top+bh,cx+bw/2-4,fy,'#8f6746',4);
  R(c,cx-bw/2,top,bw,bh,'#3d4a44',8,'#8f6746',3);T(c,'XIN GIỮ YÊN LẶNG',cx,top+bh/2-8,fit(c,'XIN GIỮ YÊN LẶNG',bw-14,port?13:12,800),'#fdf7e8',800);T(c,'thắp hương ở lư ngoài sân',cx,top+bh-12,fit(c,'thắp hương ở lư ngoài sân',bw-12,10),'#f3d98a',700);}

/* ------------------------------------------------------------ the frame */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land;
  if(port){E(c,350,862,320,22,'#cba88d22');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#b88b62',33);}
  else{E(c,600,742,520,22,'#cba88d22');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#b88b62',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  if(port){bellTower(c,40,f.base,true);hall(c,150,f.base,330,true);gate(c,500,f.base,170,true);for(const x of [490,560,640])areca(c,x,f.base,170);}
  else{bellTower(c,96,f.base,false);hall(c,230,f.base,520,false);gate(c,800,f.base,250,false);for(const x of [780,880,990,1080])areca(c,x,f.base,190);}
  yard(c,f);
  c.restore();
  const title=p.title||'',[sx,sy,sw,sh]=f.sign;R(c,sx-5,sy+7,sw+10,sh,RED_D,26);R(c,sx,sy,sw,sh,'#fff4dc',24,GOLD,3);
  T(c,title,sx+sw/2,sy+40,fit(c,title,sw-60,30,800),'#5a3f2c',800);T(c,p.sub||'',sx+sw/2,sy+sh-26,fit(c,p.sub||'',sw-60,13),'#7b5b44');
  E(c,sx+36,sy+sh/2,14,14,p.primary||RED);E(c,sx+sw-36,sy+sh/2,14,14,p.primary||RED);}

function props(w){const c=w.ctx,port=w.isPortrait(),b=w.plan().blocks,out=[];
  const [wh,wb,co,ev,fi,dr]=b,mid=r=>(r[0]+r[2])/2;
  out.push([wh[3],()=>brooms(c,wh[0],wh[2],wh[3])]);
  out.push([wb[3],()=>bonsai(c,wb[0],wb[2],wb[3])]);
  out.push([co[3],()=>burner(c,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>lotus(c,ev[0],ev[2],ev[3])]);
  out.push([fi[3],()=>donation(c,w,fi[0],fi[2],fi[3])]);
  out.push([dr[3],()=>quietSign(c,mid(dr),dr[3],port)]);
  return out;
}

export default {
  id:'pagoda',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
};
