/** Sidewalk scene (kind `sidewalk`): bà Lựu's iced-tea stall under the big bàng
 * tree at the mouth of a lane. A pavement of old tiles, the closed tailor's
 * shop with its awning (where the stall moves when it rains), the tea table
 * with the big thermos and the jars of kẹo lạc, the ice box, a row of low
 * plastic stools, the umbrella, the tab book on its stool and the chalk sign.
 * The stall's own state (spot, umbrella, stools, banner) comes from the
 * career's public data (room.data.stall / owned). Footprints follow the
 * street plan (see shop.js for the PLAN schema). */
import {R,E,L,T,P,fit,heart,streetBoard} from './kit.js';

export const PLAN={
 land:{badge:{board:[31,-23]},floor:[110,470,1090,658],lane:525,line:580,home:[800,530],kx:82,ky:45,sway:38,
   blocks:[[120,478,215,540],[175,592,330,622],[570,462,750,492],[872,478,928,496],[990,560,1080,585],[995,628,1065,645]],
   bench:[640,642,765,658],garden:[[300,484],[780,484]],
   customers:[[455,620],[580,634],[705,620],[830,638]],event:[340,652],officer:[885,598],
   staff:{x:360,step:125,y:565},cat:[262,440],counterSpan:[570,750],
   decor:{corner:[140,652],front:[880,655],center:[520,656]},sill:{plant:[420,266],lamp:[480,266],seat:[540,266],rug:[600,622]},
   spots:{shelf:[[450,372],100,[[450,525]]],evidence:[[900,418],60,[[900,525]]],workbench:[[252,560],62,[[360,606],[252,572]]],counter:[[660,428],60,[[660,525]]],
     warehouse:[[167,470],48,[[167,566],[250,525]]],board:[[1045,360],48,[[1045,525]]],finance:[[1035,540],42,[[950,572],[1035,606]]],
     property:[[332,232],35,[[380,525]]],security:[[262,228],30,[[250,525]]],door:[[1030,606],45,[[950,636],[1030,612]]],pet:[[262,420],38,[[262,525]]]}},
 port:{badge:{board:[46,-40]},floor:[48,512,652,792],lane:575,line:630,home:[165,615],kx:51,ky:57,sway:24,
   blocks:[[50,515,132,582],[66,690,222,722],[340,512,492,542],[578,522,634,545],[562,678,652,700],[470,764,574,782]],
   bench:[548,742,648,758],garden:[[190,522],[520,522]],
   customers:[[230,650],[350,660],[470,648],[330,740]],event:[290,790],officer:[410,790],
   staff:{x:250,step:105,y:612},cat:[505,500],counterSpan:[340,492],
   decor:{corner:[72,770],front:[622,792],center:[430,712]},sill:{plant:[220,300],lamp:[275,300],seat:[340,300],rug:[330,700]},
   spots:{shelf:[[280,412],100,[[280,575]]],evidence:[[606,470],55,[[606,582]]],workbench:[[144,650],58,[[262,706],[144,676]]],counter:[[416,470],56,[[416,575]]],
     warehouse:[[92,545],45,[[92,615],[165,575]]],board:[[82,342],50,[[165,575]]],finance:[[607,655],42,[[520,690],[607,730]]],
     property:[[168,240],35,[[230,575]]],security:[[85,247],30,[[165,575]]],door:[[522,742],45,[[430,772],[522,742]]],pet:[[505,480],38,[[520,578]]]}},
};

const WOOD='#b88b62',WOOD_D='#8f6746',LEAF=['#6fa36b','#7fb277','#8fc184','#5f9460','#a2cc8f'],STOOL=['#3f7fbf','#d9534f','#3f7fbf','#e2a93b'];
const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,curb:668,road:680,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,curb:800,road:812,sign:[135,30,430,104]}};
const stall=w=>w.c?.data?.stall||{};
const owned=w=>w.c?.data?.owned||{};
const mod=w=>w.c?.data?.mod?.id||'normal';

/* ------------------------------------------------------------ backdrop */
function sky(c,w,f){const m=mod(w),rain=m==='rain',g=c.createLinearGradient(0,f.y,0,f.base);
  g.addColorStop(0,rain?'#b8c4cc':m==='heat'?'#f6dcb0':'#cfe6e4');g.addColorStop(1,rain?'#dfe2dc':'#fbf0d8');c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  const port=f===F.port,sx=port?610:1040,sy=port?180:172;
  if(!rain){E(c,sx,sy,m==='heat'?38:28,m==='heat'?38:28,m==='heat'?'#ffe0a0':'#fff3c4');E(c,sx,sy,20,20,'#fde8a6');}
}
function rainLines(c,w,f){if(mod(w)!=='rain')return;const t=w.reduced?0:(w.time*220)%40;c.strokeStyle='#8fa6b855';c.lineWidth=1.5;
  for(let x=f.x+10;x<f.x+f.w;x+=26)for(let y=f.y+((x/26|0)%3)*14-40+t;y<f.curb;y+=40){c.beginPath();c.moveTo(x,y);c.lineTo(x-6,y+16);c.stroke();}}
function pole(c,x,base,top){L(c,x,base,x,top,'#b7a391',7);L(c,x-20,top+14,x+20,top+14,'#a69280',4);L(c,x-15,top+30,x+15,top+30,'#a69280',4);}
function wires(c,x0,x1,y0,y1,sag){c.strokeStyle='#8f7f7299';c.lineWidth=1.6;for(const [dy,k] of [[14,1],[30,.8],[22,1.2]]){c.beginPath();c.moveTo(x0,y0+dy);c.quadraticCurveTo((x0+x1)/2,Math.max(y0,y1)+dy+sag*k,x1,y1+dy);c.stroke();}}
/** An old tube house: wall, shutters, a tiled roof edge. */
function tube(c,x,top,wd,base,col,shut='#8fbfa6'){R(c,x,top,wd,base-top+2,col,6,'#d6b394',2);R(c,x-6,top-12,wd+12,16,'#d98f73',7,'#b8765d',1.5);
  for(let i=0;i<Math.max(1,Math.floor(wd/90));i++){const cx=x+wd*(i+.5)/Math.max(1,Math.floor(wd/90));R(c,cx-20,top+26,40,48,'#cfe7ea',4,'#d6b394',1.5);R(c,cx-37,top+24,14,52,shut,3);R(c,cx+23,top+24,14,52,shut,3);}}
/** The tailor's shop, shutter down, with its striped awning (the dry spot). */
function tailor(c,p,x,base,wd,port){const top=base-(port?150:170);R(c,x,top,wd,base-top,'#efe3cf',4,'#d6b394',2);
  R(c,x+10,top+46,wd-20,base-top-46,'#d9dbd6',3,'#a8aca6',1.5);for(let y=top+54;y<base-4;y+=9)L(c,x+14,y,x+wd-14,y,'#c3c6c0',1.2);
  R(c,x+wd/2-44,top+12,88,24,'#fff8ea',6,'#c9a585',1.5);T(c,'MAY ĐO',x+wd/2,top+24,port?12:13,'#8a5d4a',800);
  const aw=top+40;P(c,[[x-10,aw],[x+wd+10,aw],[x+wd+26,aw+34],[x-26,aw+34]],'#e8e1d2');
  for(let i=0;i<8;i++){const a=x-10+i*(wd+20)/8,b=a+(wd+20)/16;P(c,[[a,aw],[b,aw],[b+(i-3.5)*1.2+2,aw+34],[a+(i-3.5)*1.2-2,aw+34]],i%2?'#d9534f':'#fff6ea');}
  for(let i=0;i<9;i++)E(c,x-22+i*(wd+44)/8,aw+34,(wd+44)/16,5,i%2?'#d9534f':'#fff6ea');}
/** The big bàng tree: grey trunk, a wide flat crown of large leaves, a few red ones. */
function bang(c,w,x,base,top,s){const sway=w.reduced?0:Math.sin(w.time*.7)*3;
  E(c,x,base+4,90*s,10*s,'#6b584418');
  P(c,[[x-16*s,base],[x+16*s,base],[x+10*s,top+90*s],[x-8*s,top+90*s]],'#8f8577');L(c,x-4*s,base-20*s,x-6*s,top+110*s,'#a59b8c',3);
  for(const [dx,dy] of [[-70,70],[70,62],[0,40]])L(c,x,top+100*s,x+dx*s,top+dy*s,'#8f8577',9*s);
  for(let tier=0;tier<3;tier++){const ty=top+tier*34*s,wd=(150-tier*28)*s;
    for(let i=-4;i<=4;i++)E(c,x+i*wd/4.4+sway*(tier+1)*.3,ty+Math.abs(i)*5*s,wd/4,15*s,LEAF[(i+tier+8)%5]);}
  for(const [dx,dy] of [[-96,40],[64,14],[110,58],[-30,4]])E(c,x+dx*s+sway,top+dy*s,9*s,6*s,'#d86a4c');}
/** Old pavement tiles, the curb and the road. */
function pavement(c,f){const {base,curb,road}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,curb-base,'#e9dcc6',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,curb-base);c.clip();const tw=f===F.port?46:52,th=f===F.port?46:40;
  for(let y=base,row=0;y<curb;y+=th,row++)for(let x=f.x;x<f.x+f.w;x+=tw){c.fillStyle=((x/tw|0)+row)%2?'#e2d1b6':'#eadfc9';c.fillRect(x+1.5,y+1.5,tw-3,th-3);E(c,x+tw/2,y+th/2,tw/7,th/7,'#d7c4a633');}
  c.restore();R(c,f.x,curb,f.w,road-curb,'#c9c3b8',0);L(c,f.x,curb,f.x+f.w,curb,'#a79f93',2);R(c,f.x,road,f.w,bottom-road,'#9fa7aa',0);
  for(let x=f.x+30;x<f.x+f.w;x+=120)R(c,x,road+(bottom-road)/2-2,56,4,'#f1e7c8',2);}

/* ------------------------------------------------------------ the stall */
function glass(c,x,y,s=1,ice=true){R(c,x-5*s,y-14*s,10*s,14*s,'#f5e7b8cc',2,'#d9c89a',1);R(c,x-4*s,y-9*s,8*s,8*s,'#d9a53d',1);if(ice)for(const dx of [-2,2])R(c,x+dx*s-2,y-12*s,4*s,4*s,'#ffffffcc',1);}
function stool(c,x,y,col,s=1,cup=false){P(c,[[x-15*s,y],[x-11*s,y-26*s],[x+11*s,y-26*s],[x+15*s,y]],col);R(c,x-16*s,y-32*s,32*s,8*s,col,3);E(c,x,y-28*s,12*s,3*s,'#ffffff33');
  P(c,[[x-7*s,y-4*s],[x-5*s,y-20*s],[x+5*s,y-20*s],[x+7*s,y-4*s]],'#00000022');if(cup)glass(c,x,y-32*s,s);}
function thermos(c,x,base,s){R(c,x-20*s,base-72*s,40*s,70*s,'#d9534f',14*s,'#a53f3b',1.5);R(c,x-20*s,base-54*s,40*s,20*s,'#f3d98a',3);heart(c,x,base-40*s,.28*s,'#d9534f');
  R(c,x-14*s,base-84*s,28*s,14*s,'#9aa4a8',6);L(c,x-20*s,base-62*s,x-32*s,base-50*s,'#9aa4a8',4*s);}
function iceBox(c,p,x0,x1,fy,full,port){const W=x1-x0,H=port?58:50;E(c,(x0+x1)/2,fy+3,W/2+8,7,'#6b584420');
  R(c,x0,fy-H,W,H,'#3f7fbf',8,'#2d5f91',2);R(c,x0-4,fy-H-10,W+8,14,'#4f8fcf',6,'#2d5f91',1.5);R(c,x0+W/2-14,fy-H+10,28,10,'#fff7e8',3);
  T(c,'ĐÁ',x0+W/2,fy-H+15,port?9:8,'#2d5f91',800);if(full)for(let i=0;i<4;i++)R(c,x0+8+i*(W-16)/4,fy-H-16,(W-16)/4-4,8,'#e8f6fb',2,'#b8dbe6',1);
  L(c,x0+6,fy-H+26,x1-6,fy-H+26,'#ffffff44',2);}
function teaTable(c,p,w,x0,x1,fy,port){const W=x1-x0,h=port?64:56,top=fy-h;E(c,(x0+x1)/2,fy+3,W/2+10,8,'#6b584420');
  L(c,x0+10,top+10,x0+8,fy,WOOD_D,5);L(c,x1-10,top+10,x1-8,fy,WOOD_D,5);R(c,x0,top,W,14,WOOD,5,WOOD_D,2);R(c,x0+6,top+14,W-12,port?26:22,'#caa07a',4);
  const label=w.words().counter;T(c,label,(x0+x1)/2,top+14+(port?13:11),fit(c,label,W-20,port?15:12),'#5a3f2c',800);
  // Glass candy case with jars of kẹo lạc and hướng dương on the table.
  const cx=x0+W*.62;R(c,cx-34,top-38,68,38,'#e8f3f3aa',4,'#b8cdd0',1.5);for(let i=0;i<3;i++){R(c,cx-28+i*20,top-30,16,28,['#e7c27a','#d9a066','#f0d7a0'][i],4,'#c9a06a',1);}
  thermos(c,x0+W*.2,top,port?.95:.85);
  for(let i=0;i<4;i++)glass(c,x0+W*.36+i*11,top,port?1:.9,i%2===0);
  R(c,x1-22,top-12,16,12,'#8fbfa6',3);}
function tabBook(c,p,w,x0,x1,fy,port){const cx=(x0+x1)/2;stool(c,cx,fy,'#e2a93b',port?1.25:1.1);
  const top=fy-(port?40:35);R(c,cx-22,top-14,44,14,'#fff8e7',2,'#b99476',1.5);L(c,cx,top-14,cx,top,'#b99476',1.5);
  for(let i=0;i<3;i++){L(c,cx-18,top-10+i*4,cx-4,top-10+i*4,'#9a8a7a',1);L(c,cx+4,top-10+i*4,cx+18,top-10+i*4,'#9a8a7a',1);}
  const label=w.words().ledger;R(c,cx-34,fy+2,68,port?20:18,'#fffaf0',8,'#c7ad90',1);T(c,label,cx,fy+(port?12:11),fit(c,label,60,port?11:10),'#6b5040',800);}
function chalkSign(c,p,w,cx,fy,port){const open=w.c?.open,bw=port?118:104,bh=port?54:48,top=fy-bh-24;
  E(c,cx,fy+2,bw/2,6,'#6b584420');L(c,cx-bw/2+12,top+bh,cx-bw/2+4,fy,WOOD_D,4);L(c,cx+bw/2-12,top+bh,cx+bw/2-4,fy,WOOD_D,4);
  R(c,cx-bw/2,top,bw,bh,'#3d4a44',8,WOOD_D,3);const s=open?'TRÀ ĐÁ 3 XU':w.words().closed_sign;
  T(c,s,cx,top+bh/2-6,fit(c,s,bw-14,port?15:13,800),'#fdf7e8',800);T(c,open?'có sổ ghi':'mai mời ghé',cx,top+bh-11,port?11:10,'#f3d98a',700);}
function umbrella(c,p,w,cx,fy,s,level){const up=stall(w).umbrella;if(!up)return;const col=level>=2?'#4f9a5b':'#d9a066',col2=level>=2?'#e9f3e1':'#f3e2c4',top=fy-190*s,rw=(level>=2?150:118)*s;
  L(c,cx,fy,cx,top,'#9aa4a8',5*s);P(c,[[cx-rw,top+44*s],[cx,top],[cx+rw,top+44*s]],col);
  for(let i=0;i<6;i++){const a=cx-rw+i*rw/3,b=a+rw/6;P(c,[[a,top+44*s],[cx,top],[b,top+44*s]],i%2?col:col2);}
  for(let i=0;i<7;i++)E(c,cx-rw+i*rw/3,top+44*s,rw/6,6*s,i%2?col:col2);E(c,cx,top-4*s,5*s,5*s,'#9aa4a8');}
function banner(c,p,x,y,wd,port){R(c,x,y,wd,port?34:30,'#fff3cf',6,'#c9a06a',2);L(c,x+6,y,x+6,y-16,'#8f8577',2);L(c,x+wd-6,y,x+wd-6,y-16,'#8f8577',2);
  const s='Trà đá bà Lựu';T(c,s,x+wd/2,y+(port?17:15),fit(c,s,wd-16,port?16:14,800),'#8a3f2c',800);}
function stoolRow(c,w,x0,x1,fy,port){const n=Math.max(0,Math.min(8,stall(w).stools??0))||(w.c?.open?0:3),s=port?1.05:1;
  const step=(x1-x0)/Math.max(1,Math.min(n,4));for(let i=0;i<Math.min(n,4);i++)stool(c,x0+step*(i+.5),fy-(i%2)*10,STOOL[i%4],s,i%2===0);
  for(let i=4;i<n;i++)stool(c,x0+step*(i-4+.5)+14,fy+22,STOOL[i%4],s*.92,false);}
function chess(c,x,y,s){R(c,x-22*s,y-10*s,44*s,20*s,'#f3d98a',3,'#b9894f',1);for(let i=1;i<4;i++)L(c,x-22*s+i*11*s,y-10*s,x-22*s+i*11*s,y+10*s,'#b9894f',1);
  for(const [dx,dy,col] of [[-14,-4,'#d9534f'],[6,3,'#2f3a45'],[14,-5,'#d9534f'],[-3,5,'#2f3a45']])E(c,x+dx*s,y+dy*s,3.5*s,3.5*s,col);}

/* ------------------------------------------------------------ rooms */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land;
  if(port){E(c,350,862,320,22,'#cba88d22');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#c9a27e',33);}
  else{E(c,600,742,520,22,'#cba88d22');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#c9a27e',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  if(port){pole(c,40,f.base,200);pole(c,664,f.base,214);wires(c,40,664,200,214,30);
    tube(c,24,250,150,f.base,'#f3dfb0');tube(c,470,236,210,f.base,'#f2d2c4','#e8a9a0');tailor(c,p,190,f.base,260,true);}
  else{pole(c,96,f.base,170);pole(c,1108,f.base,186);wires(c,96,1108,170,186,40);
    tube(c,78,226,230,f.base,'#f3dfb0');tailor(c,p,330,f.base,300,false);tube(c,650,216,240,f.base,'#f2d2c4','#e8a9a0');tube(c,900,240,230,f.base,'#d6e8d8');}
  pavement(c,f);
  if(port)bang(c,w,590,f.base+40,236,1.05);else bang(c,w,250,f.base+36,212,1.3);
  if(owned(w).banner){if(port)banner(c,p,210,f.base-196,170,true);else banner(c,p,370,f.base-212,200,false);}
  streetBoard(c,p,port?30:1013,port?282:322,port?1.6:1);
  rainLines(c,w,f);
  c.restore();
  const sign={title:p.title||'Trà đá gốc bàng',sub:p.sub||'',dark:p.dark,primary:p.primary};
  const [sx,sy,sw,sh]=f.sign;R(c,sx-5,sy+7,sw+10,sh,'#8f6746',26);R(c,sx,sy,sw,sh,'#fff4dc',24,'#c9a06a',3);
  T(c,sign.title,sx+sw/2,sy+40,fit(c,sign.title,sw-60,30,800),'#5a3f2c',800);T(c,sign.sub,sx+sw/2,sy+sh-26,fit(c,sign.sub,sw-60,13),'#7b5b44');
  E(c,sx+36,sy+sh/2,14,14,'#d9534f');E(c,sx+sw-36,sy+sh/2,14,14,'#3f7fbf');
}

/* ------------------------------------------------------------ props */
function props(w,p){const c=w.ctx,port=w.isPortrait(),pl=w.plan(),b=pl.blocks,out=[],lvl=owned(w).umbrella||1,full=(w.c?.data?.ice?.portions||0)>0;
  const [wh,wb,co,ev,fi,dr]=b;
  out.push([wh[3],()=>iceBox(c,p,wh[0],wh[2],wh[3],full,port)]);
  out.push([wb[3],()=>stoolRow(c,w,wb[0],wb[2],wb[3],port)]);
  out.push([co[3]-1,()=>umbrella(c,p,w,(co[0]+co[2])/2+(port?-40:-60),co[3],port?.9:1,lvl)]);
  out.push([co[3],()=>teaTable(c,p,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>{stool(c,(ev[0]+ev[2])/2,ev[3],'#3f7fbf',port?1.2:1.1);if(owned(w).chess)chess(c,(ev[0]+ev[2])/2,ev[3]-(port?42:38),port?1.1:1);}]);
  out.push([fi[3],()=>tabBook(c,p,w,fi[0],fi[2],fi[3],port)]);
  out.push([dr[3],()=>chalkSign(c,p,w,(dr[0]+dr[2])/2,dr[3],port)]);
  return out;
}

export default {
  id:'sidewalk',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
};
