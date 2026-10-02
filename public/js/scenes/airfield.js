/** Airfield scene (kind `airfield`): the apron of Hãng bay Cánh Cò at the city airport.
 * The terminal with its tall windows and the control tower behind, the white turboprop
 * "Cò Trắng" parked with its propellers still, a windsock, the grey apron with yellow lines,
 * the airstairs, and per career:
 *   pilot: the fuel bowser, the dispatch desk with the weather screen, the weather board;
 *   flight_attendant: the galley carts, the boarding gate desk, the life-vest demo stand.
 * The day's weather comes from the career's public data (room.data.mod). Footprints follow
 * the street plan (see shop.js for the PLAN schema). The apron is the main area of the airport: its doors
 * (`go:` spots) lead into the gate and up the airstairs into the cabin (scenes/airport.js). */
import {R,E,L,T,P,fit,heart,streetBoard} from './kit.js';
import {AREAS,areaFor} from './airport.js';   // inside: crew room, terminal, gate, cabin, cockpit

export const PLAN={
 land:{badge:{board:[31,-23]},floor:[110,470,1090,658],lane:525,line:580,home:[800,530],kx:82,ky:45,sway:38,
   blocks:[[120,478,215,540],[175,592,330,622],[570,462,750,492],[872,478,928,496],[990,560,1080,585],[995,628,1065,645]],
   bench:[640,642,765,658],garden:[[300,484],[780,484]],
   customers:[[455,620],[580,634],[705,620],[830,638]],event:[340,652],officer:[885,598],
   staff:{x:360,step:125,y:565},cat:[262,440],counterSpan:[570,750],
   decor:{corner:[140,652],front:[880,655],center:[520,656]},sill:{plant:[420,266],lamp:[480,266],seat:[540,266],rug:[600,622]},
   spots:{shelf:[[450,372],100,[[450,525]]],evidence:[[900,418],60,[[900,525]]],workbench:[[252,560],62,[[360,606],[252,572]]],counter:[[660,428],60,[[660,525]]],
     warehouse:[[167,470],48,[[167,566],[250,525]]],board:[[1045,360],48,[[1045,525]]],finance:[[1035,540],42,[[950,572],[1035,606]]],
     property:[[332,232],35,[[380,525]]],security:[[262,228],30,[[250,525]]],door:[[1030,606],45,[[950,636],[1030,612]]],pet:[[262,420],38,[[262,525]]],
     'go:gate':[[330,410],40,[[300,505]]],'go:cabin':[[557,404],40,[[520,520]]]}},
 port:{badge:{board:[46,-40]},floor:[48,512,652,792],lane:575,line:630,home:[165,615],kx:51,ky:57,sway:24,
   blocks:[[50,515,132,582],[66,690,222,722],[340,512,492,542],[578,522,634,545],[562,678,652,700],[470,764,574,782]],
   bench:[548,742,648,758],garden:[[190,522],[520,522]],
   customers:[[230,650],[350,660],[470,648],[330,740]],event:[290,790],officer:[410,790],
   staff:{x:250,step:105,y:612},cat:[505,500],counterSpan:[340,492],
   decor:{corner:[72,770],front:[622,792],center:[430,712]},sill:{plant:[220,300],lamp:[275,300],seat:[340,300],rug:[330,700]},
   spots:{shelf:[[280,412],100,[[280,575]]],evidence:[[606,470],55,[[606,582]]],workbench:[[144,650],58,[[262,706],[144,676]]],counter:[[416,470],56,[[416,575]]],
     warehouse:[[92,545],45,[[92,615],[165,575]]],board:[[82,342],50,[[165,575]]],finance:[[607,655],42,[[520,690],[607,730]]],
     property:[[168,240],35,[[230,575]]],security:[[85,247],30,[[165,575]]],door:[[522,742],45,[[430,772],[522,742]]],pet:[[505,480],38,[[520,578]]],
     'go:gate':[[200,400],36,[[185,560]]],'go:cabin':[[356,452],36,[[300,575]]]}},
};

const NAVY='#2f5d8a',TEAL='#1f7a78',GREY='#b9c1c8',GREY_D='#8d979f',WHITE='#f8fafc',GLASS='#bcd9ea',YEL='#f2c14e',RED='#d9534f';
const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,curb:668,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,curb:800,sign:[135,30,430,104]}};
const mod=w=>w.c?.data?.mod?.id||'clear';
const cabin=w=>w.career==='flight_attendant';

/* ------------------------------------------------------------ backdrop */
function sky(c,w,f){const m=mod(w),dim=m==='storms'||m==='rough',fog=m==='fog'||m==='early',g=c.createLinearGradient(0,f.y,0,f.base);
  g.addColorStop(0,dim?'#aeb9c4':fog?'#dde3e6':'#bfe0f2');g.addColorStop(1,dim?'#dfe3e6':'#f4f1e6');c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  const port=f===F.port,sx=port?600:1040,sy=port?180:170;
  if(!dim&&!fog){E(c,sx,sy,30,30,'#fff3c4');E(c,sx,sy,21,21,'#fde8a6');}
  const drift=w.reduced?0:Math.sin(w.time*.07)*18;
  for(const [x,y,s] of port?[[120,190,.8],[430,172,.6]]:[[210,170,1],[720,160,.8]]){const col=dim?'#9aa6b1cc':'#ffffffcc';E(c,x+drift,y,34*s,14*s,col);E(c,x+drift-24*s,y+5*s,22*s,11*s,col);E(c,x+drift+26*s,y+3*s,24*s,12*s,col);}
  if(fog){c.fillStyle='#ffffff66';c.fillRect(f.x,f.base-90,f.w,90);}}
/** The terminal: long low building, tall windows, the airline's name. */
function terminal(c,p,x,top,wd,base,port){R(c,x,top,wd,base-top,'#eef2f5',6,'#c4ccd3',2);R(c,x-6,top-10,wd+12,14,'#d7dde2',6,GREY_D,1.2);
  const n=Math.max(3,Math.floor(wd/70));for(let i=0;i<n;i++){const wx=x+14+i*(wd-28)/n;R(c,wx,top+30,(wd-28)/n-10,base-top-44,GLASS,4,'#9fb8c8',1.5);L(c,wx+8,top+38,wx+8,base-22,'#ffffff88',3);}
  R(c,x+wd/2-(port?70:90),top+6,port?140:180,20,NAVY,5);T(c,'SÂN BAY',x+wd/2,top+16,port?12:13,WHITE,800);}
function tower(c,x,base,top){R(c,x-10,top+40,20,base-top-40,'#e3e8ec',3,GREY_D,1.5);P(c,[[x-30,top+40],[x+30,top+40],[x+22,top+8],[x-22,top+8]],'#9fc4d8');R(c,x-26,top,52,10,'#d7dde2',4,GREY_D,1);
  L(c,x,top,x,top-18,GREY_D,2);E(c,x,top-20,3,3,RED);}
function windsock(c,w,x,base,top){L(c,x,base,x,top,GREY_D,4);const m=mod(w),wave=w.reduced?0:Math.sin(w.time*3)*4,len=m==='wind'||m==='rough'?54:34,dir=1;
  for(let i=0;i<4;i++){const x0=x+dir*i*len/4,x1=x0+dir*len/4,dy=wave*i/4;P(c,[[x0,top+2+i*1.2+dy],[x1,top+3+(i+1)*1.2+dy],[x1,top+15-(i+1)*1.2+dy],[x0,top+16-i*1.2+dy]],i%2?WHITE:'#f08a3c');}}
/** Cò Trắng: the white turboprop parked side-on. s scales it; x is the nose. */
function plane(c,w,x,base,s,door){c.save();c.translate(x,base);c.scale(s,s);
  E(c,-190,6,210,10,'#00000018');
  P(c,[[0,-58],[18,-66],[40,-74],[330,-78],[380,-88],[420,-130],[446,-130],[430,-78],[440,-60],[420,-44],[40,-40],[10,-44]],WHITE);
  L(c,40,-42,420,-46,'#d9e0e6',2);R(c,40,-62,380,6,NAVY,3);R(c,40,-56,380,3,TEAL,1);
  P(c,[[384,-92],[418,-128],[444,-128],[426,-90]],NAVY);heart(c,418,-104,.3,WHITE);
  P(c,[[22,-66],[46,-72],[52,-62],[26,-58]],'#7fa7c4');
  for(let i=0;i<9;i++)R(c,80+i*30,-70,12,10,GLASS,4,'#8fa9bd',1);
  if(door){R(c,60,-72,20,32,'#e9eef2',3,GREY_D,1.2);}else R(c,60,-72,20,32,WHITE,3,'#c4ccd3',1.2);
  // Wing on top, the engine and its four-bladed propeller.
  P(c,[[150,-80],[330,-82],[300,-88],[170,-86]],'#e3e8ec');R(c,160,-96,70,18,'#e3e8ec',8,GREY_D,1.5);E(c,160,-87,6,9,GREY_D);
  const a=w.reduced||!w.c?.open?0:w.time*10;for(let i=0;i<4;i++){const t=a+i*Math.PI/2;L(c,160,-87,160+Math.cos(t)*4,-87+Math.sin(t)*24,'#4b5560',4);}
  L(c,70,-40,70,-16,GREY_D,4);E(c,70,-10,8,8,'#3b3f45');L(c,260,-42,256,-16,GREY_D,5);E(c,250,-10,10,10,'#3b3f45');E(c,272,-10,10,10,'#3b3f45');
  T(c,'CÒ TRẮNG',250,-50,11,NAVY,800);c.restore();}
/** Grey apron, a taxi line and the yellow parking marks. */
function apron(c,f){const {base,curb}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,bottom-base,'#d3d8dc',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,bottom-base);c.clip();
  for(let x=f.x;x<f.x+f.w;x+=90){L(c,x,base,x-40,bottom,'#c6ccd1',2);}
  L(c,f.x,base+28,f.x+f.w,base+22,YEL,4);L(c,f.x,curb-10,f.x+f.w,curb-10,'#e6e9eb',3);
  for(let x=f.x+40;x<f.x+f.w;x+=110)R(c,x,curb+4,60,6,YEL,3);
  c.restore();}

/* ------------------------------------------------------------ props */
function bowser(c,p,x0,x1,fy,port){const W=x1-x0+30,x=x0-12,h=port?60:54;E(c,x+W/2,fy+3,W/2+6,7,'#00000020');
  R(c,x,fy-h,W*.66,h-10,'#e9eef2',10,GREY_D,2);T(c,'DẦU',x+W*.33,fy-h/2-4,port?12:11,NAVY,800);R(c,x+W*.66,fy-h+6,W*.34,h-16,NAVY,6);R(c,x+W*.72,fy-h+12,W*.2,14,GLASS,3);
  for(const dx of [.18,.5,.84])E(c,x+W*dx,fy-8,9,9,'#3b3f45');L(c,x+8,fy-h+14,x-8,fy-10,'#4b5560',3);}
function galleyCarts(c,p,x0,x1,fy,port){const W=x1-x0,h=port?64:58;E(c,(x0+x1)/2,fy+3,W/2+6,7,'#00000020');
  for(let i=0;i<2;i++){const x=x0+i*W/2+2;R(c,x,fy-h,W/2-6,h-6,'#dfe5ea',5,GREY_D,1.5);R(c,x+4,fy-h+6,W/2-14,8,TEAL,2);L(c,x+6,fy-h+26,x+W/2-12,fy-h+26,'#c4ccd3',2);E(c,x+8,fy-3,4,4,'#3b3f45');E(c,x+W/2-14,fy-3,4,4,'#3b3f45');}}
function stairs(c,p,x0,x1,fy,port){const W=x1-x0,h=port?92:84;E(c,(x0+x1)/2,fy+3,W/2+8,8,'#00000020');
  P(c,[[x0,fy-6],[x0+W*.25,fy-6],[x1,fy-h],[x1-W*.18,fy-h]],'#e3e8ec');for(let i=1;i<7;i++){const t=i/7;L(c,x0+W*.12+t*W*.7,fy-6-t*(h-6),x0+W*.3+t*W*.62,fy-6-t*(h-6),GREY_D,2);}
  L(c,x0+W*.1,fy-26,x1-W*.04,fy-h-20,NAVY,3);R(c,x0-4,fy-10,W*.42,10,GREY_D,3);E(c,x0+6,fy,6,6,'#3b3f45');E(c,x0+W*.34,fy,6,6,'#3b3f45');}
function desk(c,p,w,x0,x1,fy,port){const W=x1-x0,h=port?64:58,top=fy-h;E(c,(x0+x1)/2,fy+3,W/2+10,8,'#00000020');
  R(c,x0,top,W,h,'#eef2f5',8,GREY_D,2);R(c,x0,top,W,12,cabin(w)?TEAL:NAVY,6);
  const label=w.words().counter;T(c,label,(x0+x1)/2,top+34,fit(c,label,W-20,port?14:12),'#2a3b4c',800);
  const sx=x0+W*.72,m=mod(w);R(c,sx-26,top-48,52,40,'#26303b',5,'#1b232c',2);
  if(cabin(w)){T(c,'CỬA 3',sx,top-34,11,YEL,800);T(c,'ĐÚNG GIỜ',sx,top-20,9,'#8fe0a0',700);}
  else{T(c,m==='storms'?'⛈️':m==='fog'?'🌫️':m==='wind'?'🌬️':'☀️',sx,top-28,20,WHITE,700);}}
function weatherBoard(c,p,w,cx,fy,port){const bw=port?70:64,bh=port?60:54,top=fy-bh-34;L(c,cx,fy,cx,top+bh,GREY_D,4);
  R(c,cx-bw/2,top,bw,bh,'#26303b',6,'#1b232c',2);const m=mod(w);T(c,m==='storms'?'GIÔNG':m==='fog'?'SƯƠNG':m==='wind'?'GIÓ':'ĐẸP',cx,top+18,port?12:11,YEL,800);
  T(c,m==='wind'?'22 kt':'6 kt',cx,top+36,port?12:11,'#8fe0a0',700);}
function vestStand(c,p,cx,fy,port){const s=port?1.1:1;L(c,cx,fy,cx,fy-70*s,GREY_D,4);L(c,cx-14,fy,cx+14,fy,GREY_D,4);E(c,cx,fy-78*s,9*s,10*s,'#e7d2bd');
  P(c,[[cx-16*s,fy-66*s],[cx+16*s,fy-66*s],[cx+18*s,fy-30*s],[cx-18*s,fy-30*s]],'#f5c542');L(c,cx,fy-66*s,cx,fy-32*s,'#c99a1a',2);R(c,cx-5*s,fy-40*s,10*s,8*s,RED,2);}
function crewBag(c,p,w,x0,x1,fy,port){const cx=(x0+x1)/2,bw=port?50:46,bh=port?40:36;E(c,cx,fy+2,bw/2+6,6,'#00000020');
  R(c,cx-bw/2,fy-bh,bw,bh-4,cabin(w)?TEAL:NAVY,6,'#1b232c',1.5);L(c,cx-8,fy-bh,cx-8,fy-bh-12,GREY_D,3);L(c,cx+8,fy-bh,cx+8,fy-bh-12,GREY_D,3);L(c,cx-8,fy-bh-12,cx+8,fy-bh-12,GREY_D,3);
  E(c,cx-bw/2+6,fy-2,4,4,'#3b3f45');E(c,cx+bw/2-6,fy-2,4,4,'#3b3f45');
  const label=w.words().ledger;R(c,cx-34,fy+2,68,port?20:18,'#fffaf0',8,'#c4ccd3',1);T(c,label,cx,fy+(port?12:11),fit(c,label,60,port?11:10),'#2a3b4c',800);}
function aFrame(c,p,w,cx,fy,port){const open=w.c?.open,s=w.words(),label=open?s.open_sign:s.closed_sign,bw=port?118:104,bh=port?48:42,top=fy-bh-22;
  L(c,cx-bw/2+10,top+bh,cx-bw/2+2,fy,GREY_D,4);L(c,cx+bw/2-10,top+bh,cx+bw/2-2,fy,GREY_D,4);R(c,cx-bw/2,top,bw,bh,cabin(w)?TEAL:NAVY,8,'#1b232c',2);
  T(c,label,cx,top+bh/2,fit(c,label,bw-14,port?14:12,800),WHITE,800);}

/* ------------------------------------------------------------ rooms */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land;
  if(port){E(c,350,862,320,22,'#9aa6b122');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#9fb0bf',33);}
  else{E(c,600,742,520,22,'#9aa6b122');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#9fb0bf',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  if(port){tower(c,610,f.base,262);terminal(c,p,28,300,230,f.base,true);windsock(c,w,275,f.base,300);plane(c,w,300,f.base+6,.8,!!w.c?.open);}
  else{tower(c,432,f.base,236);terminal(c,p,90,262,300,f.base,false);windsock(c,w,960,f.base,262);plane(c,w,480,f.base+8,1.1,!!w.c?.open);}
  apron(c,f);
  streetBoard(c,p,port?30:1013,port?282:322,port?1.6:1);
  c.restore();
  const [sx,sy,sw,sh]=f.sign,title=p.title||(cabin(w)?'Khoang khách Cánh Cò':'Hãng bay Cánh Cò');
  R(c,sx-5,sy+7,sw+10,sh,'#1b3550',26);R(c,sx,sy,sw,sh,'#f4f8fb',24,'#9fb8c8',3);
  T(c,title,sx+sw/2,sy+40,fit(c,title,sw-80,30,800),NAVY,800);T(c,p.sub||'',sx+sw/2,sy+sh-26,fit(c,p.sub||'',sw-60,13),'#4a5d70');
  heart(c,sx+36,sy+sh/2+4,.4,TEAL);E(c,sx+sw-36,sy+sh/2,12,12,YEL);
}
function props(w,p){const c=w.ctx,port=w.isPortrait(),b=w.plan().blocks,out=[],fa=cabin(w);
  const [wh,wb,co,ev,fi,dr]=b;
  out.push([wh[3],()=>fa?galleyCarts(c,p,wh[0],wh[2],wh[3],port):bowser(c,p,wh[0],wh[2],wh[3],port)]);
  out.push([wb[3],()=>stairs(c,p,wb[0],wb[2],wb[3],port)]);
  out.push([co[3],()=>desk(c,p,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>fa?vestStand(c,p,(ev[0]+ev[2])/2,ev[3],port):weatherBoard(c,p,w,(ev[0]+ev[2])/2,ev[3],port)]);
  out.push([fi[3],()=>crewBag(c,p,w,fi[0],fi[2],fi[3],port)]);
  out.push([dr[3],()=>aFrame(c,p,w,(dr[0]+dr[2])/2,dr[3],port)]);
  return out;
}

export default {
  id:'airfield',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
  areas:AREAS,
  areaFor,
};
