/** Office scene kind. One floor plan (PLAN) for all five office careers, but
 * each career dresses it as a different place, with its own palette, back
 * wall, floor and furniture:
 *
 *  - accounting "Góc Sổ Xinh": a cosy attic corner above a shop. Sloped wooden
 *    ceiling, wallpaper, a window over the street's tube houses, one wooden
 *    desk with a green lamp, ledgers, a floor lamp, a reading nook and a rug.
 *  - corp_accounting "Mây Tre Xanh": a bright open-plan finance room. White
 *    and bamboo green, carpet tiles, a row of desks with stamps and approval
 *    trays, a company logo wall and a glass meeting room.
 *  - tax_payroll "Minh Bạch": a service counter. Three numbered windows
 *    behind glass, a "now serving" LED board, a deadline calendar, a wall of
 *    filing drawers, a queue-ticket kiosk and terrazzo with a queue line.
 *  - group_accounting "Sông Hồng Group": a high-rise HQ at night. Dark walls,
 *    a glass wall over the river skyline, a video wall of charts, black desks
 *    carrying the four subsidiaries' logos, and a marble floor.
 *  - customer_care "Trạm Lắng Nghe": a call centre. Colourful pods with
 *    headsets, a big queue board, hexagonal sound panels and a bright carpet.
 *
 * Hotspots stay where PLAN puts them (w.plan() reads the kind's plan, so it
 * is shared): security camera and "CHUYỆN PHỐ" board top left, the filing
 * cabinet (warehouse), the shelf, the window (property) with Mướp on its
 * sill, the originals rack (evidence), the manager's room (counter), the
 * door, your own desk (workbench) and the expense desk (finance). Floor
 * footprints (`blocks`) are also shared; each career draws its own thing on
 * them. Portrait moves the manager's room to the left and the window up into
 * a ribbon; nothing that matters sits above y≈150 there (the title card
 * covers it). PLAN schema: see shop.js.
 */
import {R,E,L,T,P,fit,heart,bloom,plantAt,mascot} from './kit.js';
import {t as tr} from '../v4/i18n.js';

export const PLAN={
 land:{floor:[130,452,1070,682],lane:505,line:563,home:[600,505],kx:82,ky:45,sway:28,
   blocks:[[232,540,862,584],[134,452,214,528],[692,452,726,468],[962,548,1070,568],[988,626,1068,648],[100,570,136,582]],
   bench:[150,652,290,676],garden:[[790,684],[845,684]],
   customers:[[540,622],[665,626],[790,618],[600,672]],event:[440,666],officer:[336,666],
   staff:{x:270,step:112,y:462},cat:[458,420],counterSpan:[245,850],
   decor:{corner:[160,616],front:[905,672],center:[712,674]},sill:{plant:[592,420],lamp:[556,420],seat:[510,420],rug:[600,648]},badge:{board:[30,-22]},wall:{poster:[1030,402]},
   anchors:{door:[1038,505],window:[540,478],glass:[513,330],car:[1150,730]},
   spots:{shelf:[[319,330],95,[[319,505]]],evidence:[[784,316],48,[[784,505]]],workbench:[[510,452],62,[[451,505]]],counter:[[900,262],70,[[900,505]]],
     warehouse:[[174,470],48,[[174,560],[250,505]]],board:[[172,262],45,[[250,505]]],finance:[[1016,520],42,[[934,558],[1016,600]]],
     property:[[513,262],35,[[513,505]]],security:[[160,196],30,[[250,505]]],door:[[1038,380],48,[[1038,505]]],pet:[[458,404],38,[[458,505]]]}},
 port:{floor:[62,512,638,822],lane:572,line:626,home:[440,572],kx:51,ky:57,sway:20,
   blocks:[[150,604,520,650],[52,510,110,546],[560,672,648,692],[540,752,656,770],[56,676,122,700],[38,810,62,822]],
   bench:[80,808,210,826],garden:[[279,826],[330,826],[381,826]],
   customers:[[215,700],[335,696],[455,702],[260,770]],event:[165,750],officer:[455,776],
   staff:{x:246,step:88,y:528},cat:[512,288],counterSpan:[160,510],
   decor:{corner:[520,700],front:[410,812],center:[335,760]},sill:{plant:[238,288],lamp:[628,288],seat:[440,288],rug:[335,740]},wall:{poster:[526,458]},
   anchors:{door:[569,572],window:[435,560],glass:[435,232],car:[660,880]},
   spots:{shelf:[[283,400],80,[[283,572]]],evidence:[[604,640],45,[[604,652],[604,722]]],workbench:[[372,540],56,[[321,572]]],counter:[[128,262],60,[[150,572]]],
     warehouse:[[81,470],45,[[90,592],[150,572]]],board:[[422,494],45,[[422,572]]],finance:[[598,720],42,[[604,722],[508,766]]],
     property:[[435,228],35,[[435,572]]],security:[[72,158],30,[[150,572]]],door:[[569,420],50,[[569,572]]],pet:[[512,272],38,[[512,572]]]}},
};

// Shared drawing geometry (scene pixels); each career's room moves the wall pieces it needs to.
const G={
 land:{wall:[108,179,984,268],floor:[108,445,984,244],sign:[370,60,460,104],camera:[150,197],board:[140,224],
   cabinet:[132,336,84,192],shelf:[234,232,170,198],rack:[752,258,64,108],door:[992,250,92,196],
   desk:{x0:232,x1:862,top:480,bottom:576,n:4,chairY:500},cooler:[709,468],finance:[962,568,108],copier:[988,648,80],plant:[118,578],fs:12},
 port:{wall:[40,139,620,370],floor:[40,506,620,323],camera:[62,158],board:[382,404],
   cabinet:[50,404,62,142],shelf:[218,334,130,146],mgr:[48,186,158,322],door:[484,332,170,176],
   evidence:[560,692,88],desk:{x0:150,x1:520,top:562,bottom:640,n:3,chairY:568},finance:[540,770,116],copier:[56,700,66],plant:[50,818],fs:16},
};
const FONT='"Trebuchet MS", "Segoe UI", sans-serif';
const SUBS=[['SH Food','#e0864f'],['SH Logistics','#3f9fd4'],['SH Pack','#6cbf7a'],['SH Nami','#c49ae8']];
const POD=['#f39c86','#f4cc62','#6ec6b6','#ab92e2'];

const hex2=n=>Math.max(0,Math.min(255,Math.round(n))).toString(16).padStart(2,'0');
/** Blend two #rrggbb colours. */
const mix=(a,b,t)=>{const p=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));const A=p(a),B=p(b);return '#'+A.map((v,i)=>hex2(v+(B[i]-v)*t)).join('');};
/** #rrggbb with alpha. */
const A=(h,a)=>h.slice(0,7)+hex2(a*255);
/** Stable pseudo-random 0…1 for index i (no flicker between frames). */
const rnd=i=>{const x=Math.sin(i*127.1+11.7)*43758.5453;return x-Math.floor(x);};
const port=w=>w.isPortrait();
const isOpen=w=>!!w.c?.open;
const lit=(w,speed,phase=0)=>w.reduced||Math.sin(w.time*speed+phase)>0;
function glow(c,x,y,r,col){const g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,col);g.addColorStop(1,col.slice(0,7)+'00');c.fillStyle=g;c.fillRect(x-r,y-r,r*2,r*2);}
function vgrad(c,x,y,w,h,a,b,r=0){const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,a);g.addColorStop(1,b);c.beginPath();c.roundRect(x,y,w,h,r);c.fillStyle=g;c.fill();}
function clip(c,x,y,w,h,r,fn){c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();fn();c.restore();}
function hexagon(c,x,y,r,fill,stroke){c.beginPath();for(let i=0;i<6;i++){const a=Math.PI/6+i*Math.PI/3;i?c.lineTo(x+Math.cos(a)*r,y+Math.sin(a)*r):c.moveTo(x+Math.cos(a)*r,y+Math.sin(a)*r);}c.closePath();c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=1.5;c.stroke();}}

/* ============================================================ Shell & floors */
const SHELL={
 accounting:{outer:'#c38d63',inner:'#fff3e3',edge:'#a8754f'},
 corp_accounting:{outer:'#a9cdb8',inner:'#f8fcf9',edge:'#8fb8a0'},
 tax_payroll:{outer:'#9ebfc6',inner:'#f5f9f8',edge:'#86aab2'},
 group_accounting:{outer:'#28313f',inner:'#394456',edge:'#b8975a'},
 customer_care:{outer:'#a9bff0',inner:'#f6f8ff',edge:'#8ea6dc'},
};
function frame(c,s,portrait){
  if(portrait){E(c,350,857,324,23,'#8b735322');R(c,22,114,656,738,s.outer,31);R(c,29,117,642,724,s.inner,26,s.edge,3);}
  else{E(c,605,724,503,30,'#8b735322');R(c,85,165,1030,550,s.outer,35);R(c,96,168,1008,533,s.inner,30,s.edge,3);}
}
function floorWood(c,[fx,fy,fw,fh],cols){for(let y=fy,r=0;y<fy+fh;y+=28,r++){c.fillStyle=cols[r%2];c.fillRect(fx,y,fw,28);L(c,fx,y,fx+fw,y,cols[2],1);for(let x=fx+((r*71)%140);x<fx+fw;x+=140)L(c,x,y+3,x,y+25,cols[2],1);}}
function floorTiles(c,[fx,fy,fw,fh],tw,th,a,b,line){for(let y=fy,r=0;y<fy+fh;y+=th,r++)for(let x=fx,k=0;x<fx+fw;x+=tw,k++){c.fillStyle=(r+k)%2?a:b;c.fillRect(x,y,tw,th);}
  if(line){for(let x=fx;x<fx+fw;x+=tw)L(c,x,fy,x,fy+fh,line,1);for(let y=fy;y<fy+fh;y+=th)L(c,fx,y,fx+fw,y,line,1);}}
function terrazzo(c,[fx,fy,fw,fh],tw,th){floorTiles(c,[fx,fy,fw,fh],tw,th,'#eef1ec','#e8ece6','#d3d9d2');
  const dots=['#b5c9c3','#e2bcaa','#aab4bd','#d6d1b6'];for(let i=0;i<Math.floor(fw*fh/2200);i++)E(c,fx+rnd(i)*fw,fy+rnd(i+999)*fh,1.2+rnd(i+77)*1.6,1+rnd(i+55)*1.2,dots[i%4]);}
function marble(c,[fx,fy,fw,fh],tw,th){floorTiles(c,[fx,fy,fw,fh],tw,th,'#eceef2','#e3e7ec','#cfd5de');
  c.lineCap='round';for(let i=0;i<14;i++){const x=fx+rnd(i+3)*fw,y=fy+rnd(i+31)*fh;c.beginPath();c.moveTo(x,y);c.bezierCurveTo(x+40,y+rnd(i)*20-10,x+70,y+rnd(i+9)*24-12,x+120,y+rnd(i+4)*18-9);c.strokeStyle=i%3?'#c9cfd988':'#b8c0cc99';c.lineWidth=i%3?1:1.8;c.stroke();}}
function funCarpet(c,[fx,fy,fw,fh],portrait){c.fillStyle='#8fb2e6';c.fillRect(fx,fy,fw,fh);
  const s=portrait?58:52;
  for(let y=fy+s/2,r=0;y<fy+fh+s;y+=s,r++)for(let x=fx+(r%2?s/2:0),k=0;x<fx+fw+s;x+=s,k++){const col=POD[(r+k*3)%4];
    if((r+k)%3===0)E(c,x,y,s*.26,s*.26,A(col,.85));else if((r+k)%3===1){R(c,x-s*.22,y-s*.08,s*.44,s*.16,A(col,.8),s*.08);}else hexagon(c,x,y,s*.2,A(col,.75));}
  for(let y=fy+18;y<fy+fh;y+=s*1.5){c.beginPath();for(let x=fx;x<=fx+fw;x+=8)c.lineTo(x,y+Math.sin(x/34)*5);c.strokeStyle='#ffffff55';c.lineWidth=3;c.stroke();}}
/** Wall + floor fill and the skirting line. */
function base(c,g,portrait,wall,floorFn,skirt){
  const [wx,wy,ww,wh]=g.wall,f=g.floor;
  R(c,wx,wy,ww,wh,wall,portrait?21:22);
  clip(c,f[0],f[1],f[2],f[3],16,()=>floorFn(f));
  R(c,wx,f[1]-7,ww,9,skirt,3);
}

/* ============================================================ Shared wall pieces */
function camera(c,p,x,y,has,dark){
  if(has){L(c,x-16,y+8,x-4,y-1,'#b79b85',4);R(c,x-8,y-12,36,19,'#f5f2eb',7,'#a7aaa2',2);E(c,x+24,y-3,7,8,'#7a8992');E(c,x+25,y-3,3,4,'#b4d9df');E(c,x-2,y-7,2,2,'#90bd8b');}
  else{R(c,x-8,y-12,34,21,dark?'#3b4658':'#fff6e9',8,dark?'#6b7890':'#d5b59a',1);T(c,'♧',x+9,y-1,14,dark?'#e9d3a2':p.dark);}
}
/** "CHUYỆN PHỐ" notice board (the `board` hotspot), tinted per place. */
function noticeBoard(c,p,x,y,s,st){R(c,x,y,65*s,77*s,st.frame,9);R(c,x+6*s,y+6*s,53*s,65*s,st.paper,6);T(c,'CHUYỆN',x+32*s,y+24*s,10*s,st.ink);T(c,'PHỐ',x+32*s,y+40*s,14*s,st.ink);heart(c,x+32*s,y+59*s,.35*s,st.heart||p.primary);}
function clock(c,x,y,r,w,st={}){
  const still=w.reduced,time=w.time;E(c,x,y+2,r+4,r+4,'#0000001a');E(c,x,y,r+4,r+4,st.rim||'#c9a585');E(c,x,y,r,r,st.face||'#fffaf0');
  for(let i=0;i<12;i++){const a=i*Math.PI/6;L(c,x+Math.cos(a)*r*.74,y+Math.sin(a)*r*.74,x+Math.cos(a)*r*.88,y+Math.sin(a)*r*.88,st.tick||'#b89c86',i%3?1:2);}
  const m=still?Math.PI*1.35:time*.3,h=still?-Math.PI*.18:time*.025,hand=st.hand||'#7d6356';
  L(c,x,y,x+Math.sin(h)*r*.48,y-Math.cos(h)*r*.48,hand,3);L(c,x,y,x+Math.sin(m)*r*.72,y-Math.cos(m)*r*.72,hand,2);E(c,x,y,2.5,2.5,'#cf839c');
}
/** A label chip above a piece of furniture. */
function chip(c,label,cx,cy,w,fs,fill,edge,ink){const th=fs+14;R(c,cx-w/2,cy-th/2,w,th,fill,th/2,edge,1.5);T(c,label,cx,cy,fit(c,label,w-16,fs,800),ink,800);}
/** Shelf of binders or ledgers; `st` picks wood, binder colours and label colours. */
function binderShelf(c,p,x,y,w,h,label,fs,st){
  R(c,x-4,y-20,w+8,h+28,st.wood,10,st.edge,2);R(c,x+5,y+6,w-10,h-9,st.back,7);
  chip(c,label,x+w/2,y-24,w-24,fs,st.chip,st.edge,st.ink);
  const rows=3,rh=(h-6)/rows;
  for(let r=0;r<rows;r++){const b=y+6+rh*(r+1)-6;let bx=x+12,i=0;
    if(st.led)R(c,x+6,b-rh+8,w-12,3,A(st.led,.8),2);
    while(bx<x+w-24){const col=st.spines[(i*2+r)%st.spines.length];
      if((i+r*2)%6===4){c.save();c.translate(bx+4,b);c.rotate(-.28);R(c,0,-(rh-18),14,rh-18,col,3,st.spineEdge,1);c.restore();bx+=22;i++;continue;}
      const bw=13+(i*7+r*3)%6,bh=rh-14-((i+r)%3)*5;
      R(c,bx,b-bh,bw,bh,col,3,st.spineEdge,1);
      if(st.bands){R(c,bx+1,b-bh+7,bw-2,3,st.bands,1);R(c,bx+1,b-12,bw-2,3,st.bands,1);}else R(c,bx+3,b-bh+6,bw-6,Math.min(16,bh*.35),st.tab||'#fff8e8',2);
      bx+=bw+2;i++;}
    R(c,x,b,w,9,st.plank,2);R(c,x+3,b-1,w-6,3,A('#ffffff',.35),1);}
}
/** Wall-hung sorter of originals (landscape evidence). */
function trayRack(c,p,x,y,rw,rh,fs,st){
  chip(c,'BẢN GỐC',x+rw/2,y-15,rw+10,fs,st.chip,st.edge,st.ink);
  R(c,x,y,rw,rh,st.wood,8,st.edge,2);R(c,x+5,y+5,rw-10,rh-10,st.back,5);
  const n=3,gap=(rh-10)/n;
  for(let k=0;k<n;k++){const ty=y+5+gap*(k+1)-6;
    for(let j=0;j<3;j++){c.save();c.translate(x+12+j*3,ty-4-j*3);c.rotate(-.05*j);R(c,0,-gap*.52,rw-28,gap*.52,['#fffdf6','#fbe9c9','#e8f1f7'][(j+k)%3],2,'#d9cfbf',1);c.restore();}
    if(st.stamp&&k!==1){c.beginPath();c.arc(x+rw-20,ty-gap*.32,7,0,Math.PI*2);c.strokeStyle=k?'#d9534f':'#3f8f6b';c.lineWidth=2;c.stroke();}
    R(c,x+4,ty,rw-8,7,st.plank,2);}
  c.beginPath();c.arc(x+rw-14,y+rh-20,7,0,Math.PI*2);c.strokeStyle='#a98f74';c.lineWidth=2.5;c.stroke();L(c,x+rw-9,y+rh-15,x+rw-4,y+rh-9,'#a98f74',3);
}
/** Door with the open/closed sign; `st` = {frame,jamb,leaf,glass,kick,handle,wood}. */
function officeDoor(c,p,w,x,y,dw,dh,fs,leaves,signW,signAt,st){
  const items=w.c?.ops?.security?.items||[],open=isOpen(w),words=w.words();
  R(c,x-8,y-10,dw+16,dh+10,st.frame,9);R(c,x-3,y-5,dw+6,dh+5,st.jamb,6);
  const lw=dw/leaves;
  for(let k=0;k<leaves;k++){const lx=x+k*lw;
    if(st.wood){R(c,lx+3,y+1,lw-6,dh-1,st.leaf,4,st.frame,2);R(c,lx+12,y+dh*.52,lw-24,dh*.38,mix(st.leaf,'#000000',.08),4,A('#000000',.12),1.5);
      E(c,lx+lw/2,y+dh*.3,lw*.2,lw*.2,st.frame);E(c,lx+lw/2,y+dh*.3,lw*.2-4,lw*.2-4,st.glass);E(c,lx+lw/2-4,y+dh*.3-4,3,3,'#ffffffaa');
      E(c,k?lx+12:lx+lw-12,y+dh*.55,4,4,st.handle);}
    else{R(c,lx+3,y+1,lw-6,dh-1,st.glass,4,st.leaf,2);
      c.save();c.globalAlpha=.5;L(c,lx+10,y+dh*.5,lx+lw*.5,y+18,'#ffffff',5);c.restore();
      R(c,lx+7,y+dh-24,lw-14,18,st.kick,3);R(c,leaves>1?(k?lx+9:lx+lw-15):lx+lw-17,y+dh*.52,6,30,st.handle,3);}}
  const txt=open?words.open_sign:words.closed_sign,sh=fs+18,sy=y+dh*signAt,cx=x+dw/2;
  L(c,cx-signW*.28,y+8,cx-signW*.22,sy,'#b99b80',1.5);L(c,cx+signW*.28,y+8,cx+signW*.22,sy,'#b99b80',1.5);E(c,cx,y+7,3,3,'#b99b80');
  R(c,cx-signW/2,sy,signW,sh,'#fff8e8',11,'#c6a182',2);E(c,cx-signW/2+13,sy+sh/2,5,5,open?'#6fae7c':'#c9b8a6');
  T(c,txt,cx+8,sy+sh/2,fit(c,txt,signW-34,fs,800),p.dark,800);
  R(c,x+6,y+dh+3,dw-12,8,A(st.mat||p.primary,.45),4);
  if(items.includes('bell')){const bx=x+dw-8,by=y+4;L(c,bx,by-10,bx,by,'#ac8f73',2);P(c,[[bx-9,by+15],[bx+9,by+15],[bx+6,by+2],[bx-6,by+2]],'#f0ce85');E(c,bx,by+17,3.5,3,'#d4ad64');}
  if(items.includes('light')){const lx=x-22,ly=y+26;glow(c,lx,ly+8,90,'#ffe1a455');R(c,lx-10,ly-6,20,26,'#fff0b8',7,'#b69b79',2);R(c,lx-3,ly-14,6,8,'#b69b79',2);}
}
/** Glass box with a frosted name band; `inside(x,y,w,h)` draws the room behind the glass. */
function glassRoom(c,p,x,y,w,h,label,fs,st,inside){
  R(c,x-6,y-6,w+12,h+6,st.frame,10);R(c,x,y,w,h,st.back,6);
  clip(c,x,y,w,h,6,()=>inside(x,y,w,h));
  R(c,x,y,w,h,st.tint||'#dff1f84a',6);
  c.save();c.globalAlpha=.45;L(c,x+w*.08,y+h*.62,x+w*.3,y+h*.3,'#ffffff',7);L(c,x+w*.18,y+h*.64,x+w*.36,y+h*.38,'#ffffff',3);c.restore();
  const band=y+h*(st.bandAt??.4),bh=fs+14;R(c,x,band,w,bh,st.band||'#ffffffc8',0);R(c,x,band,w,2,A('#ffffff',.6),0);R(c,x,band+bh-2,w,2,A('#ffffff',.6),0);
  T(c,label,x+w/2,band+bh/2,fit(c,label,w-16,fs,800),st.ink||p.dark,800);
  c.beginPath();c.roundRect(x,y,w,h,6);c.strokeStyle=st.edge||'#b3c3cb';c.lineWidth=3;c.stroke();
}
/** Window with a view drawn by `view(x,y,w,h)`; returns nothing. */
function windowFrame(c,x,y,w,h,st,view){
  const r=st.arch?[Math.min(w/2,56),Math.min(w/2,56),6,6]:8;
  c.beginPath();c.roundRect(x-9,y-9,w+18,h+18,st.arch?[Math.min(w/2,64),Math.min(w/2,64),12,12]:14);c.fillStyle=st.frame;c.fill();
  c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();view(x,y,w,h);c.restore();
  for(let k=1;k<(st.panes||2);k++)L(c,x+w*k/(st.panes||2),y+2,x+w*k/(st.panes||2),y+h-2,st.mull,st.mw||6);
  if(st.cross)L(c,x+2,y+h*st.cross,x+w-2,y+h*st.cross,st.mull,st.mw||6);
  R(c,x-14,y+h+1,w+28,11,st.sill,5);R(c,x-12,y+h+1,w+24,3,A('#ffffff',.4),2);
}
function dayCity(c,x,y,w,h,tall){
  vgrad(c,x,y,w,h,'#bfe3f2','#e6f4f1');E(c,x+w*.8,y+h*.24,Math.min(w,h)*.09+4,Math.min(w,h)*.09+4,'#fff1c2');
  E(c,x+w*.25,y+h*.18,26,9,'#ffffffcc');E(c,x+w*.33,y+h*.14,16,9,'#ffffffcc');E(c,x+w*.62,y+h*.3,20,7,'#ffffffaa');
  const cols=['#bccfe2','#cbc5e4','#a9c8d8','#d4dcea','#bdd6d1'];
  for(let bx=x-8,i=0;bx<x+w;i++){const bw=20+(i*37)%24,bh=h*(tall?.42:.3)+((i*53)%40)/100*h*.45,top=y+h-bh;
    R(c,bx,top,bw,bh+8,cols[i%5],3);c.fillStyle='#f7f9fcb0';for(let wy=top+7;wy<y+h-8;wy+=10)for(let wx=bx+4;wx<bx+bw-5;wx+=7)c.fillRect(wx,wy,3,4);bx+=bw+5;}
  for(let i=0;i<6;i++)E(c,x+i*w/5,y+h+4,w/9,h*.1+6,i%2?'#a8cdb0':'#b9d8b9');
}
/** Across the street from the attic: tube houses, balconies, wires and a shop awning. */
function streetView(c,x,y,w,h){
  vgrad(c,x,y,w,h,'#a9d8ec','#fde9cf');E(c,x+w*.82,y+h*.18,14,14,'#fff4c8');
  const cols=['#f3cf8e','#f2b8a8','#bfdab4','#f7e3b8','#c9d7ec'];
  for(let bx=x-10,i=0;bx<x+w;i++){const bw=58+(i*23)%22,top=y+h*(.22+((i*37)%30)/100);
    R(c,bx,top,bw,h,cols[i%5],2,mix(cols[i%5],'#6b4a3a',.2),1.5);R(c,bx-3,top-6,bw+6,8,mix(cols[i%5],'#6b4a3a',.25),2);
    for(let fy=top+12,k=0;fy<y+h-30;fy+=36,k++){R(c,bx+bw*.22,fy,bw*.56,22,'#fdf8ec',3,'#a98f74',1);L(c,bx+bw/2,fy,bx+bw/2,fy+22,'#a98f74',1);
      R(c,bx+bw*.14,fy+22,bw*.72,4,'#8f6b53',1);if((i+k)%2)E(c,bx+bw*.3,fy+19,6,4,'#86b37e');}
    bx+=bw+2;}
  // Awning of the shop downstairs across the road.
  const ay=y+h-22;for(let i=0;i<w/18;i++)R(c,x+i*18,ay,18,14,i%2?'#fff5ea':'#e27b6c',0);for(let i=0;i<w/18;i++)E(c,x+i*18+9,ay+14,9,5,i%2?'#fff5ea':'#e27b6c');
  c.strokeStyle='#5d4a3f';c.lineWidth=1.5;c.beginPath();c.moveTo(x,y+h*.2);c.quadraticCurveTo(x+w/2,y+h*.34,x+w,y+h*.16);c.stroke();
  c.beginPath();c.moveTo(x,y+h*.26);c.quadraticCurveTo(x+w/2,y+h*.42,x+w,y+h*.24);c.stroke();
}
/** Night skyline over the river with a lit bridge. */
function nightCity(c,x,y,w,h,time,reduced){
  vgrad(c,x,y,w,h,'#0b1530','#2a3e6c');
  for(let i=0;i<22;i++){const tw=reduced?1:.6+.4*Math.sin(time*2+i);E(c,x+rnd(i)*w,y+rnd(i+40)*h*.4,1.3,1.3,A('#ffffff',.5*tw));}
  E(c,x+w*.82,y+h*.16,11,11,'#fff4d0');E(c,x+w*.82+4,y+h*.16-3,10,10,'#1a2748');
  const river=y+h*.8;
  for(const [layer,col,hh] of [[0,'#223156',.55],[1,'#141e38',.42]])for(let bx=x-6,i=0;bx<x+w;i++){const bw=18+rnd(i+layer*50)*26,bh=h*(hh+rnd(i+layer*70)*.25),top=river-bh;
    R(c,bx,top,bw,bh,col,2);
    for(let wy=top+6;wy<river-4;wy+=8)for(let wx=bx+3;wx<bx+bw-4;wx+=6)if(rnd(wx*7+wy*3)>.55)c.fillStyle=rnd(wx+wy)>.3?'#ffd98a':'#9fd3ff',c.fillRect(wx,wy,3,3);
    if(layer&&i%4===1){L(c,bx+bw/2,top,bx+bw/2,top-12,col,2);E(c,bx+bw/2,top-13,2,2,lit({reduced,time},3,i)?'#ff6b6b':'#6b2b3b');}
    bx+=bw+(layer?4:10);}
  R(c,x,river,w,h-river+y,'#101a33',0);
  for(let i=0;i<14;i++){const rx=x+rnd(i+5)*w;R(c,rx,river+4+rnd(i+8)*(h*.16),10+rnd(i)*18,2,A(i%3?'#ffd98a':'#9fd3ff',.5),1);}
  // Bridge: deck, arches and lamps.
  const by=river-6;L(c,x,by,x+w,by,'#6b7ea8',4);
  for(let bx=x+10;bx<x+w;bx+=46){c.beginPath();c.arc(bx+23,by+2,20,Math.PI,0);c.strokeStyle='#4f608a';c.lineWidth=2;c.stroke();E(c,bx,by-4,2,2,'#ffe3a0');}
}

/* ============================================================ Shared floor pieces */
function fileCabinet(c,p,w,x,y,cw,ch,fs,st){
  const items=w.c?.ops?.security?.items||[],label=w.words().store,drawers=st.n||(ch>170?4:3);
  E(c,x+cw/2,y+ch+3,cw*.62,6,'#00000020');
  R(c,x,y,cw,ch,st.body,8,st.edge,2);R(c,x+3,y+3,cw-6,7,A('#ffffff',.3),4);
  const cols=st.cols||1,dh=(ch-18)/drawers,dw=(cw-12)/cols;
  for(let i=0;i<drawers;i++)for(let k=0;k<cols;k++){const dy=y+12+i*dh,dx=x+6+k*dw,col=st.doors?st.doors[(i+k*2)%st.doors.length]:st.drawer;
    R(c,dx,dy,dw-(cols>1?3:0),dh-5,col,6,st.edge,1.2);
    if(st.doors){E(c,dx+dw-12,dy+dh/2,2.5,2.5,st.handle);for(let v=0;v<3;v++)L(c,dx+8,dy+8+v*5,dx+dw-20,dy+8+v*5,A('#000000',.12),1.5);}
    else{R(c,dx+dw/2-11,dy+5,22,8,st.card||'#fffdf7',2,A('#000000',.18),1);R(c,dx+dw/2-9,dy+dh*.58,18,5,st.handle,3);}}
  const tw=Math.max(cw+10,fs*4.4);chip(c,label,x+cw/2,y-4-(fs+14)/2,tw,fs,st.chip,st.edge,st.ink);
  if(items.includes('lock')){const lx=x+cw-16,ly=y+16;R(c,lx-7,ly,14,14,'#d8c596',4,'#a59470',1);c.beginPath();c.arc(lx,ly,5,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=2.5;c.stroke();}
  if(st.keypad){R(c,x+6,y+14,14,18,'#11161d',3);E(c,x+13,y+19,2,2,isOpen(w)?'#62e28a':'#e26262');}
}
/** "CẦN KIỂM" tag when equipment is worn. */
function wornTag(c,w,x,y,wd,fs){if((w.c?.ops?.equipment?.condition??100)<100){R(c,x,y,wd,fs+6,'#f7d995',5,'#d9b56a',1);T(c,'CẦN KIỂM',x+wd/2,y+(fs+6)/2,fit(c,'CẦN KIỂM',wd-8,fs,800),'#94643d',800);}}
function copier(c,p,w,x,y,cw,fs,dark){
  const on=isOpen(w),h=cw*.95,top=y-h,body=dark?'#2d3542':'#f2efe8',lid=dark?'#3c4757':'#dcd6cc',edge=dark?'#1b212b':'#bdb5a8';
  E(c,x+cw/2,y+2,cw*.66,7,'#00000020');
  R(c,x,top+16,cw,h-16,body,8,edge,2);R(c,x-3,top+6,cw+6,13,lid,5,edge,1.5);R(c,x+5,top,cw-10,8,dark?'#4c5869':'#c9c2b7',4);
  R(c,x+cw*.52,top+22,cw*.4,13,dark?'#1b212b':'#e3ded4',3);R(c,x+cw*.55,top+25,cw*.2,7,on?(dark?'#5fd0ff':'#bfe3cf'):'#6b7280',2);E(c,x+cw*.85,top+28,2.5,2.5,on&&lit(w,2.4)?'#6fcf8a':'#8b8f96');
  R(c,x-14,top+30,16,6,dark?'#3c4757':'#e0d9ce',2);R(c,x-16,top+25,18,6,'#ffffff',1,'#d7cfc3',1);
  for(let k=0;k<2;k++){const dy=top+42+k*(h-50)/2;R(c,x+6,dy,cw-12,(h-50)/2-4,dark?'#353f4e':'#ebe6dd',4,edge,1);L(c,x+cw/2-9,dy+6,x+cw/2+9,dy+6,dark?'#8c97a8':'#b5ab9d',2);}
  wornTag(c,w,x+2,top+h*.52,cw-4,fs);
}
function cooler(c,x,y,s){
  E(c,x,y+2,20*s,5*s,'#00000020');R(c,x-16*s,y-56*s,32*s,56*s,'#f3f1ec',6*s,'#c5bdb1',1.5);R(c,x-11*s,y-48*s,22*s,12*s,'#e7e2d9',3*s);
  E(c,x-5*s,y-42*s,2.6*s,3*s,'#e39a9a');E(c,x+5*s,y-42*s,2.6*s,3*s,'#8fb8d8');R(c,x-9*s,y-24*s,18*s,4*s,'#dcd5ca',2);
  R(c,x-5*s,y-63*s,10*s,8*s,'#9cc6dc',2);R(c,x-14*s,y-96*s,28*s,36*s,'#c4e3f2d8',11*s,'#9cc6dc',1.5);R(c,x-10*s,y-84*s,20*s,3*s,'#ffffff99',1);L(c,x-8*s,y-90*s,x-8*s,y-68*s,'#ffffffaa',2);
  R(c,x+18*s,y-38*s,7*s,12*s,'#fffdf7',1,'#d6cbbd',1);
}
function docTable(c,p,x,y,tw,fs,st){
  E(c,x+tw/2,y+2,tw*.62,5,'#00000020');L(c,x+5,y-30,x+5,y,st.leg,4);L(c,x+tw-5,y-30,x+tw-5,y,st.leg,4);
  for(let k=0;k<3;k++){const ty=y-40-k*13;R(c,x+5,ty-7,tw-10,9,st.tray,2,st.trayEdge,1.5);R(c,x+9,ty-11,tw-18,5,['#fffdf6','#fbe9c9','#e8f1f7'][k],1,'#d9cfbf',1);}
  L(c,x+8,y-64,x+8,y-38,st.trayEdge,1.5);L(c,x+tw-8,y-64,x+tw-8,y-38,st.trayEdge,1.5);
  R(c,x-4,y-38,tw+8,10,st.top,4,st.leg,1.5);
  const lh=fs+6;R(c,x+2,y-28,tw-4,lh,st.plate,4,st.leg,1);T(c,'BẢN GỐC',x+tw/2,y-28+lh/2,fit(c,'BẢN GỐC',tw-10,fs),st.ink,800);
  c.beginPath();c.arc(x+tw-10,y-80,7,0,Math.PI*2);c.strokeStyle='#a98f74';c.lineWidth=2.5;c.stroke();L(c,x+tw-5,y-75,x+tw+1,y-68,'#a98f74',3);
}
/** Expense desk (finance). `st` = {body,top,edge,paper,ink,extra}. */
function ledgerDesk(c,p,w,x,y,dw,label,fs,st){
  const top=y-46;E(c,x+dw/2,y+3,dw*.58,6,'#00000020');
  R(c,x,top+10,dw,y-top-10,st.body,10,st.edge,1.5);R(c,x-6,top,dw+12,14,st.top,7,st.edge,1.5);
  R(c,x+dw*.14,top-26,dw*.44,28,st.paper,5,'#d9b596',1);L(c,x+dw*.36,top-25,x+dw*.36,top+1,'#d9b596',1.5);for(let k=0;k<3;k++){L(c,x+dw*.18,top-18+k*6,x+dw*.32,top-18+k*6,k?'#cdbcaa':p.primary,1.5);L(c,x+dw*.4,top-18+k*6,x+dw*.54,top-18+k*6,'#cdbcaa',1.5);}
  st.extra?.(c,x+dw*.78,top+1);
  T(c,label,x+dw/2,top+(y-top)/2+6,fit(c,label,dw-14,fs,800),st.ink,800);
}
function sofa(c,p,[x0,,x1,y1],garden,col=p.mint){
  const w=x1-x0,base=y1-4,edge=mix(col,'#4b3a2e',.25);
  E(c,x0+w/2,y1+2,w*.55,6,'#00000022');L(c,x0+10,base-6,x0+10,y1,'#af8b6c',5);L(c,x1-10,base-6,x1-10,y1,'#af8b6c',5);
  R(c,x0+6,base-58,w-12,36,col,13,edge,1.5);R(c,x0,base-30,w,22,col,9,edge,1.5);R(c,x0-6,base-44,16,34,mix(col,'#4b3a2e',.08),8,edge,1.5);R(c,x1-10,base-44,16,34,mix(col,'#4b3a2e',.08),8,edge,1.5);
  R(c,x0+18,base-52,w/2-24,24,mix(col,'#ffffff',.35),9);R(c,x0+w/2+6,base-52,w/2-24,24,mix(col,'#ffffff',.35),9);heart(c,x0+w*.3,base-38,.3,p.primary);
  if(garden){bloom(c,x1-4,base-62,13,p.primary);bloom(c,x0+10,base-60,10,'#f3d590');}
}
/** A row of joined waiting-room seats on the bench footprint (tax office). */
function waitingSeats(c,[x0,,x1,y1],garden,p){
  const w=x1-x0,n=3,sw=w/n,base=y1-4;E(c,x0+w/2,y1+2,w*.55,6,'#00000022');
  R(c,x0,base-24,w,6,'#9aa7ad',3);L(c,x0+12,base-20,x0+12,y1,'#7f8c92',4);L(c,x1-12,base-20,x1-12,y1,'#7f8c92',4);
  for(let i=0;i<n;i++){const sx=x0+i*sw;R(c,sx+4,base-62,sw-8,36,'#4f8fa8',10,'#3b7085',1.5);R(c,sx+2,base-32,sw-4,12,'#5fa3bd',6,'#3b7085',1.5);R(c,sx+10,base-56,sw-20,10,'#ffffff30',5);}
  if(garden)bloom(c,x1-6,base-66,11,p.primary);
}
/** Potted plants in a few styles. */
function plant(c,kind,x,y,s){
  c.save();c.translate(x,y);c.scale(s,s);E(c,0,4,24,7,'#00000018');
  if(kind==='monstera'){R(c,-18,-34,36,36,'#c9764f',8,'#9e5a3b',1.5);R(c,-21,-38,42,9,'#d98a62',3);
    for(let i=0;i<6;i++){const a=-Math.PI/2+(i-2.5)*.42;c.save();c.translate(0,-36);c.rotate(a+Math.PI/2);L(c,0,0,0,-44-i%2*14,'#5f8f5b',2.5);E(c,0,-50-i%2*14,17,12,i%2?'#4f8f5f':'#6aa56a');L(c,-8,-50-i%2*14,8,-50-i%2*14,'#3f7a4e',1.5);c.restore();}}
  else if(kind==='bamboo'){R(c,-19,-30,38,32,'#f4f6f2',8,'#b9c7bd',1.5);for(const [dx,h] of [[-9,118],[0,140],[9,104]]){L(c,dx,-30,dx,-30-h,'#7fb069',5);for(let k=1;k<h/24;k++)L(c,dx-3,-30-k*24,dx+3,-30-k*24,'#5c8f4d',2);
      E(c,dx+12,-30-h+6,14,5,'#8cc278');E(c,dx-12,-30-h+22,14,5,'#6fae5f');}}
  else if(kind==='snake'){R(c,-16,-28,32,30,'#9aa6ad',6,'#77838a',1.5);for(let i=0;i<5;i++){const dx=-12+i*6,h=58+(i*17)%30;P(c,[[dx-4,-28],[dx+4,-28],[dx+1+(i%2?3:-3),-28-h]],i%2?'#4f8f5b':'#6aa66b');L(c,dx,-30,dx+(i%2?3:-3)*.8,-24-h,'#d9d98a',1);}}
  else if(kind==='orchid'){R(c,-15,-26,30,28,'#f8f9fb',9,'#c6ccd5',1.5);E(c,-8,-28,14,5,'#3f7a55');E(c,8,-29,14,5,'#4f8f5f');c.beginPath();c.moveTo(0,-28);c.quadraticCurveTo(4,-90,26,-96);c.strokeStyle='#6b7f5a';c.lineWidth=2;c.stroke();
    for(let i=0;i<5;i++){const t=i/4,px=2+t*22+Math.sin(t*3)*4,py=-60-t*36;bloom(c,px,py,7,i%2?'#f3d3ec':'#fbe7f5');}}
  else if(kind==='olive'){R(c,-20,-34,40,36,'#1c232d',8,'#39434f',1.5);R(c,-22,-38,44,7,'#2c3542',3);L(c,0,-36,-4,-80,'#6e5a48',4);L(c,-4,-70,12,-96,'#6e5a48',3);
    for(let i=0;i<14;i++)E(c,-22+rnd(i)*44,-120+rnd(i+20)*50,9,5,i%2?'#8aa77a':'#a3bd92');}
  else if(kind==='rubber'){R(c,-18,-32,36,34,'#f4cc62',8,'#d6a93c',1.5);L(c,0,-32,0,-104,'#5c7a4c',3);for(let i=0;i<6;i++){const dir=i%2?1:-1;c.save();c.translate(0,-44-i*11);c.rotate(dir*.6);E(c,dir*13,-4,16,8,i%2?'#3f7a55':'#2f6a48');c.restore();}}
  c.restore();
}
/** Floor lamp with a warm glow (the attic). */
function floorLamp(c,x,y,on){E(c,x,y+2,16,5,'#00000022');E(c,x,y-2,13,4,'#8d6a4f');L(c,x,y-2,x,y-104,'#8d6a4f',4);
  if(on)glow(c,x,y-112,92,'#ffd58a66');P(c,[[x-14,y-128],[x+14,y-128],[x+22,y-100],[x-22,y-100]],'#f6d7a4');R(c,x-22,y-103,44,4,'#e8bf7f',2);}
/** Payslip printer on a stand (tax office, staff side). */
function payslipPrinter(c,p,w,x,y){E(c,x,y+2,22,5,'#00000022');L(c,x-14,y,x-14,y-38,'#8f9ca3',3);L(c,x+14,y,x+14,y-38,'#8f9ca3',3);R(c,x-20,y-42,40,6,'#c7d0d4',2);
  R(c,x-18,y-66,36,24,'#eef2f2',5,'#9fb0b6',1.5);R(c,x-12,y-60,24,4,'#2d3b40',2);
  const out=isOpen(w)&&!w.reduced?(w.time*6)%14:8;R(c,x-10,y-78-out,20,14+out,'#fffdf7',1,'#d6c8b5',1);L(c,x-6,y-72-out,x+6,y-72-out,A(p.primary,.7),1.5);T(c,'₫',x,y-64-out/2,9,'#8f6b53',800);}
/** Queue-ticket kiosk (tax office, customer side). */
function ticketKiosk(c,w,x,y,s){
  E(c,x,y+2,26*s,6*s,'#00000022');R(c,x-24*s,y-12*s,48*s,12*s,'#2f5f73',4);R(c,x-20*s,y-112*s,40*s,102*s,'#3f7d8f',10*s,'#2f5f73',2);
  R(c,x-15*s,y-104*s,30*s,24*s,'#152329',4);T(c,String(13+(w.c?.tasks||[]).length).padStart(3,'0'),x,y-92*s,Math.round(13*s),'#ffb86b',800);
  E(c,x,y-64*s,9*s,9*s,'#e05d4f');E(c,x,y-64*s,5*s,5*s,'#ff9a8a');
  R(c,x-12*s,y-46*s,24*s,4*s,'#152329',2);R(c,x-8*s,y-46*s,16*s,14*s,'#fffdf7',1,'#d6c8b5',1);T(c,'№',x,y-40*s,Math.round(8*s),'#8f6b53',800);
  wornTag(c,w,x-22*s,y-30*s,44*s,Math.round(10*s));
}
/** Low rack of blank tax forms beside a small plant (tax office, customer side). */
function formsRack(c,p,x,y,rw){E(c,x+rw/2,y+2,rw*.6,6,'#00000020');R(c,x+4,y-34,rw-30,34,'#9fb3b8',5,'#6b7f86',1.5);
  for(let k=0;k<3;k++){const fx=x+10+k*(rw-42)/3;R(c,fx,y-44,(rw-42)/3-4,26,['#fffdf7','#e8f4f1','#fff4d6'][k],2,'#b9c7cc',1);L(c,fx+4,y-38,fx+(rw-42)/3-8,y-38,A(p.primary,.7),1.5);L(c,fx+4,y-33,fx+(rw-42)/3-10,y-33,'#c9d2d4',1.2);}
  plant(c,'snake',x+rw-12,y,.6);}
/** Headset charging trolley (call centre). */
function headsetCart(c,p,w,x,y,cw,fs){
  const top=y-70;E(c,x+cw/2,y+2,cw*.6,6,'#00000020');E(c,x+8,y-2,5,5,'#556');E(c,x+cw-8,y-2,5,5,'#556');
  R(c,x,top,cw,62,'#eef3fb',8,'#9fb0d0',2);R(c,x+4,top+30,cw-8,4,'#c8d4ea',2);
  for(let i=0;i<3;i++){const hx=x+14+i*(cw-28)/2;c.beginPath();c.arc(hx,top+18,8,Math.PI,0);c.strokeStyle='#44506a';c.lineWidth=2.5;c.stroke();R(c,hx-10,top+16,5,9,POD[i],2);R(c,hx+5,top+16,5,9,POD[i],2);E(c,hx,top+44,3,3,isOpen(w)&&lit(w,2,i)?'#62d38a':'#9aa3b5');}
  wornTag(c,w,x+2,top+48,cw-4,fs);
}

/* ============================================================ Desk bits */
function screen(c,p,x,base,s,on,style,mark,dark){
  const sw=62*s,sh=42*s,top=base-15*s-sh,bez=dark?'#0f141b':'#5f6b75';
  R(c,x-14*s,base-5*s,28*s,6*s,dark?'#3a4452':'#9aa3aa',3);R(c,x-4*s,base-17*s,8*s,14*s,dark?'#4a5566':'#aab3b9',2);
  if(on&&dark)glow(c,x,top+sh/2,sw*.9,'#5fb7ff33');
  R(c,x-sw/2,top,sw,sh,bez,7*s);const ix=x-sw/2+4*s,iy=top+4*s,iw=sw-8*s,ih=sh-8*s;R(c,ix,iy,iw,ih,on?(dark?'#0f2440':'#f6fbff'):'#3f4a53',4*s);
  if(!on){L(c,ix+6,iy+ih-4,ix+iw*.45,iy+4,'#ffffff22',4);return;}
  if(style==='chat'){R(c,ix+4,iy+4,iw*.55,ih*.3,p.light,4);R(c,ix+iw*.4,iy+ih*.45,iw*.55,ih*.3,mix(p.primary,'#ffffff',.4),4);E(c,ix+8,iy+ih-5,2,2,p.primary);E(c,ix+14,iy+ih-5,2,2,p.primary);}
  else if(style==='chart'){for(let i=0;i<4;i++){const hh=ih*(.3+((i*37)%50)/100);R(c,ix+5+i*iw/4.4,iy+ih-hh-2,iw/6,hh,SUBS[i][1],1);}}
  else if(style==='line'){c.beginPath();for(let i=0;i<6;i++){const px=ix+4+i*(iw-8)/5,py=iy+ih*(.75-((i*29)%50)/100);i?c.lineTo(px,py):c.moveTo(px,py);}c.strokeStyle='#5fd0ff';c.lineWidth=2;c.stroke();R(c,ix+4,iy+4,iw*.4,3,'#f3d9a0',1);}
  else{for(let r=0;r<4;r++)L(c,ix+3,iy+4+r*ih/4.4,ix+iw-3,iy+4+r*ih/4.4,'#dbe5ec',1);for(let k=1;k<3;k++)L(c,ix+k*iw/3,iy+2,ix+k*iw/3,iy+ih-2,'#dbe5ec',1);
    R(c,ix+3,iy+3,iw-6,ih/5,style==='pay'?mix(p.primary,'#ffffff',.45):p.light,1);R(c,ix+iw*.55,iy+ih*.55,iw*.3,ih*.2,A(p.primary,.35),1);}
  if(mark)heart(c,x+sw/2-6,top+8,.22,p.primary);
}
function keyboard(c,x,y,s,dark){R(c,x-22*s,y,44*s,7*s,dark?'#2a323e':'#f4f1ea',3,dark?'#475366':'#c8c0b4',1);for(let k=0;k<5;k++)L(c,x-17*s+k*8.5*s,y+2.5*s,x-13*s+k*8.5*s,y+2.5*s,dark?'#56637a':'#d6cec2',1.5);}
function mug(c,x,y,col){R(c,x-6,y-13,12,13,col,3,'#c9ad96',1);c.beginPath();c.arc(x+7,y-7,4,-Math.PI/2,Math.PI/2);c.strokeStyle='#c9ad96';c.lineWidth=2;c.stroke();}
function stamp(c,x,y,s,ink='#d9534f'){R(c,x-11*s,y-5*s,22*s,5*s,ink,2);R(c,x-5*s,y-18*s,10*s,13*s,'#8a5a3c',3);E(c,x,y-21*s,7*s,5*s,'#a9714c');}
function trayStack(c,x,y,s){for(let k=0;k<2;k++){const ty=y-k*11*s;R(c,x-15*s,ty-9*s,30*s,9*s,k?'#e5f4ec':'#f3efe6',2,'#9fb8a8',1.5);R(c,x-12*s,ty-12*s,24*s,4*s,'#fffdf6',1,'#d9cfbf',1);}
  c.beginPath();c.arc(x+6*s,y-25*s,5*s,0,Math.PI*2);c.strokeStyle='#d9534f';c.lineWidth=1.5;c.stroke();}
function calc(c,x,y,s){R(c,x-9*s,y-20*s,18*s,20*s,'#cfe0e6',3,'#9fb5bf',1);R(c,x-6*s,y-17*s,12*s,5*s,'#e8f6e9',1);for(let k=0;k<6;k++)E(c,x-4*s+(k%3)*4*s,y-8*s+Math.floor(k/3)*4*s,1.3*s,1.3*s,'#7f96a1');}
function deskPhone(c,x,y,s,on){R(c,x-12*s,y-10*s,24*s,10*s,'#6f7f8e',4);R(c,x-14*s,y-16*s,28*s,7*s,'#5c6b78',4);E(c,x+7*s,y-5*s,2*s,2*s,on?'#7bd48f':'#c9c9c9');}
function headsetStand(c,x,y,s,col){L(c,x,y,x,y-30*s,'#8a93a6',2.5);E(c,x,y-1,7*s,2.5*s,'#8a93a6');c.beginPath();c.arc(x,y-30*s,10*s,Math.PI,0);c.strokeStyle='#3c465c';c.lineWidth=3;c.stroke();R(c,x-13*s,y-33*s,6*s,12*s,col,3);R(c,x+7*s,y-33*s,6*s,12*s,col,3);}
function chair(c,x,y,col,s=1,kind='office'){
  const rim=mix(col,'#2b2320',.3);
  if(kind==='wood'){L(c,x-18*s,y-2,x-18*s,y-40*s,'#8d5f3f',4);L(c,x+18*s,y-2,x+18*s,y-40*s,'#8d5f3f',4);R(c,x-22*s,y-72*s,44*s,34*s,'#b27a52',12*s,'#8d5f3f',1.5);
    for(let k=-1;k<=1;k++)L(c,x+k*10*s,y-68*s,x+k*10*s,y-44*s,'#8d5f3f',2);R(c,x-20*s,y-40*s,40*s,10*s,col,5);return;}
  if(kind==='exec'){R(c,x-3*s,y-24*s,6*s,20*s,'#4a5566',2);E(c,x,y-3,18*s,4*s,'#2a323e');R(c,x-24*s,y-76*s,48*s,54*s,'#1c232d',16*s,'#3c4758',1.5);R(c,x-17*s,y-70*s,34*s,30*s,'#2c3542',11*s);L(c,x-13*s,y-30*s,x+13*s,y-30*s,'#475366',2);return;}
  R(c,x-3*s,y-24*s,6*s,20*s,rim,2);R(c,x-28*s,y-30*s,11*s,8*s,rim,4);R(c,x+17*s,y-30*s,11*s,8*s,rim,4);
  R(c,x-23*s,y-58*s,46*s,36*s,col,14*s,rim,1.5);R(c,x-17*s,y-53*s,34*s,20*s,mix(col,'#ffffff',.32),10*s);
  if(kind==='mesh')for(let k=1;k<4;k++)L(c,x-18*s,y-58*s+k*8*s,x+18*s,y-58*s+k*8*s,A(rim,.5),1);
}
/** Headsets on hired staff at the support desk (drawn over the sprite). */
function staffHeadsets(w,p){
  const c=w.ctx,out=[];
  (w.c?.ops?.staff||[]).filter(e=>e.status==='hired').forEach((e,i)=>{const pos=w.staffPosition(i,e),pt=w.project(pos.x,pos.y),n=e.avatar??(Number(String(e.id).slice(-2))||0);
    out.push([pt.y+.02,()=>{const bob=w.reduced?0:Math.sin(w.time*(pos.moving?7:1.8)+n)*(pos.moving?2:1);c.save();c.translate(pt.x,pt.y+bob);c.scale(1.08,1.08);
      c.beginPath();c.arc(0,-84,33,Math.PI*1.05,Math.PI*1.95);c.strokeStyle=p.dark;c.lineWidth=4;c.stroke();R(c,-37,-84,9,16,p.primary,4);R(c,28,-84,9,16,p.primary,4);L(c,-32,-70,-16,-63,p.dark,2);E(c,-15,-63,2.5,2.5,p.dark);c.restore();}]);});
  return out;
}

/* ============================================================ Sign (landscape) */
const SIGN={
 accounting:{back:'#a8754f',face:'#fff3df',edge:'#d7a878',inner:'#fbe7cc',ink:'#7a4f3a'},
 corp_accounting:{back:'#3f8f6b',face:'#ffffff',edge:'#bfe0cc',inner:'#f3faf6',ink:'#2f6f53'},
 tax_payroll:{back:'#2f5f73',face:'#f4fbfb',edge:'#9cc3cc',inner:'#e7f3f5',ink:'#2f5f73'},
 group_accounting:{back:'#0d1219',face:'#1f2937',edge:'#c9a45c',inner:'#253142',ink:'#f3d9a0',sub:'#c3cad6',night:true},
 customer_care:{back:'#8ea6dc',face:'#fffdf7',edge:'#b9ccf2',inner:'#f3f7ff',ink:'#527a9a'},
};
function sign(c,p,w,[x,y,sw,sh]){
  const st=SIGN[w.career]||SIGN.corp_accounting;
  R(c,x-5,y+7,sw+10,sh,st.back,31);R(c,x,y,sw,sh,st.face,30,st.edge,3);R(c,x+10,y+10,sw-20,sh-21,st.inner,25,A(st.edge,.6),2);
  if(st.night){E(c,x+45,y+49,24,24,'#c9a45c');E(c,x+45,y+49,19,19,'#1f2937');c.beginPath();c.moveTo(x+30,y+56);c.quadraticCurveTo(x+45,y+40,x+60,y+56);c.strokeStyle='#f3d9a0';c.lineWidth=3;c.stroke();L(c,x+32,y+62,x+58,y+62,'#6fb4e8',3);}
  else mascot(c,x+45,y+49,.56);
  const cx=x+sw/2+20;T(c,p.title,cx,y+42,fit(c,p.title,sw-130,30,800),st.ink,800);let sub=String(tr(p.sub||''));c.font=`700 10px ${FONT}`;if(c.measureText(sub).width>sw-110)sub=sub.split(' · ')[0];
  T(c,sub,cx,y+sh-27,fit(c,sub,sw-110,13),st.sub||st.ink);
  if(w.career==='corp_accounting'){E(c,x+sw-36,y+50,11,6,'#7fb069');E(c,x+sw-28,y+42,9,5,'#5c8f4d');}
  else if(w.career==='tax_payroll'){E(c,x+sw-33,y+50,9,9,'#e05d4f');T(c,'₫',x+sw-33,y+50,11,'#fff',800);}
  else if(!st.night)heart(c,x+sw-33,y+51,.36,st.ink);
}

/* ============================================================ Desk rows (the workbench) */
const WORK=1; // the player's own desk in each row
function cosyDesk(c,p,w,D,portrait){
  const {x0,x1,top,bottom,n}=D,uw=(x1-x0)/n,on=isOpen(w),s=portrait?.9:1,dEnd=x0+uw*2;
  E(c,(x0+x1)/2,bottom+8,(x1-x0)/2+14,12,'#8b735320');
  R(c,x0+4,top+12,uw*.42,bottom-top-6,'#c98f5f',6,'#9c6b45',1.5);for(let k=0;k<3;k++){const dy=top+18+k*(bottom-top-16)/3;R(c,x0+10,dy,uw*.42-12,(bottom-top-16)/3-5,'#dba473',4);E(c,x0+4+uw*.21,dy+8,3,3,'#8d5f3f');}
  R(c,x0+uw*.46,top+12,dEnd-x0-uw*.46-6,(bottom-top)*.5,'#dba473',5,'#9c6b45',1);L(c,dEnd-8,top+10,dEnd-8,bottom+6,'#9c6b45',6);
  R(c,x0-6,top,dEnd-x0+8,15,'#d9a06c',6,'#9c6b45',1.5);R(c,x0,top+2,dEnd-x0-4,4,'#ffffff55',2);
  const mx=x0+uw*1.62;
  // Green banker's lamp, stacked ledgers, a calculator, the laptop-ish screen and a mug of tea.
  const lx=x0+uw*.2;if(on)glow(c,lx+6,top-26,70,'#ffe2a066');E(c,lx,top,11*s,3*s,'#b08a4c');L(c,lx,top,lx,top-24*s,'#b08a4c',3);R(c,lx-16*s,top-36*s,34*s,13*s,'#3f7a55',6,'#2c5a3e',1);R(c,lx-12*s,top-24*s,26*s,3*s,'#ffe9a8',1);
  ['#8c4a3c','#3f6b4f','#a0703a'].forEach((col,k)=>R(c,x0+uw*.5-14*s+k*2,top-6*s-k*6*s,30*s,6*s,col,2,'#5a3a2a',1));
  calc(c,x0+uw*.82,top+2,s);keyboard(c,x0+uw*1.28,top+2,s);screen(c,p,mx,top+2,s,on,'sheet',true);mug(c,dEnd-18,top+2,'#f3d6dc');
  // A low sideboard of ledgers, a teapot and a plant.
  const sx=dEnd+8,sw=x1-sx,st=top+18;
  R(c,sx,st+12,sw,bottom-st-6,'#c98f5f',8,'#9c6b45',1.5);R(c,sx-4,st,sw+8,14,'#d9a06c',6,'#9c6b45',1.5);
  const doors=portrait?2:3;for(let k=0;k<doors;k++){const dx=sx+8+k*(sw-16)/doors;R(c,dx,st+20,(sw-16)/doors-6,bottom-st-26,'#dba473',5,'#b07a50',1);E(c,dx+(sw-16)/doors-14,st+20+(bottom-st-26)/2,3,3,'#8d5f3f');}
  let bx=sx+8;for(let i=0;i<(portrait?4:7);i++){const bh=(34+(i*7)%12)*s,bw=12*s;R(c,bx,st-bh,bw,bh,['#8c4a3c','#3f6b4f','#a0703a','#5a4a7a','#b5563f'][i%5],2,'#5a3a2a',1);R(c,bx+1,st-bh+6,bw-2,3,'#e8c77a',1);R(c,bx+1,st-10,bw-2,3,'#e8c77a',1);bx+=bw+2;}
  if(!portrait){R(c,bx+14,st-26,30,26,'#fff8ef',8,'#d9c3ad',1);E(c,bx+29,st-28,8,3,'#e7d5c2');R(c,bx+48,st-12,10,12,'#fff8ef',3,'#d9c3ad',1);plantAt(c,x1-26,st+2,.5);}
  else plantAt(c,x1-20,st+2,.42);
}
function openDesks(c,p,w,D,portrait){
  const {x0,x1,top,bottom,n}=D,uw=(x1-x0)/n,on=isOpen(w),s=portrait?.9:1;
  E(c,(x0+x1)/2,bottom+8,(x1-x0)/2+14,12,'#00000018');
  // Frosted green screens along the back of the row.
  R(c,x0-4,top-56*s,x1-x0+8,58*s,'#cfeedb99',6,'#8cc4a2',2);for(let i=1;i<n;i++)L(c,x0+i*uw,top-56*s,x0+i*uw,top,'#8cc4a2',3);
  for(let i=0;i<n;i++){const ux=x0+i*uw;R(c,ux+10,top+14,uw-20,(bottom-top)*.56,'#ffffff',6,'#cfd8d2',1);R(c,ux+10,top+14+(bottom-top)*.4,uw-20,6,'#8cc4a2',2);L(c,ux+7,top+10,ux+7,bottom+6,'#b9c4bd',5);L(c,ux+uw-7,top+10,ux+uw-7,bottom+6,'#b9c4bd',5);}
  R(c,x0-6,top,x1-x0+12,15,'#fbfcfb',6,'#c8d3cc',1.5);R(c,x0,top+2,x1-x0,4,'#ffffff90',2);
  for(let i=0;i<n;i++){const ux=x0+i*uw,seat=ux+uw*.4,mx=ux+uw*.74;
    if(i%2)trayStack(c,ux+(portrait?20:24),top+2,s);else stamp(c,ux+(portrait?18:22),top+2,s,i?'#3f8f6b':'#d9534f');
    keyboard(c,seat,top+2,s);screen(c,p,mx,top+2,s,on,'sheet',i===WORK);}
}
function serviceCounter(c,p,w,D,portrait){
  const {x0,x1,top,bottom,n}=D,uw=(x1-x0)/n,on=isOpen(w),s=portrait?.9:1,fs=portrait?18:14;
  E(c,(x0+x1)/2,bottom+8,(x1-x0)/2+14,12,'#00000018');
  // Staff side: papers, monitor backs and a stamp behind the glass.
  for(let i=0;i<n;i++){const cx=x0+i*uw+uw/2;R(c,cx+uw*.08,top-44*s,uw*.3,36*s,'#5f6b75',5);R(c,cx+uw*.21,top-10*s,8*s,10*s,'#8f9aa3',2);
    R(c,cx-uw*.34,top-8*s,uw*.3,8*s,'#fffdf7',1,'#d6c8b5',1);if(i===WORK)mug(c,cx-uw*.08,top,'#e3f3ee');}
  // Glass screens with a speaking grille and a paper slot, numbered plates on top.
  for(let i=0;i<n;i++){const gx=x0+i*uw+8,gw=uw-16,gy=top-66*s,cx=gx+gw/2;
    R(c,gx,gy,gw,66*s,'#d8eff266',6,'#9cc3cc',2);c.save();c.globalAlpha=.5;L(c,gx+10,gy+60*s,gx+gw*.35,gy+10,'#ffffff',6);c.restore();
    for(let k=0;k<5;k++)E(c,cx-12+k*6,gy+26*s,1.6,1.6,'#7f9ca3');
    R(c,cx-gw*.26,top-9,gw*.52,9,'#ffffff99',3,'#9cc3cc',1);
    const tw=fs+12,served=i===WORK&&on;R(c,gx+5,gy+5,tw,tw,served&&lit(w,2.2)?'#ffb86b':'#2f5f73',5);T(c,String(i+1),gx+5+tw/2,gy+5+tw/2+1,fs,'#ffffff',800);}
  // Counter top and the customer-side front panel.
  R(c,x0-8,top,x1-x0+16,16,'#f2ede2',6,'#b9b1a2',1.5);R(c,x0-2,top+2,x1-x0+4,4,'#ffffff90',2);
  R(c,x0,top+15,x1-x0,bottom-top-12,p.primary,6,mix(p.primary,'#000000',.25),2);
  for(let i=0;i<n;i++){const ux=x0+i*uw;R(c,ux+10,top+24,uw-20,bottom-top-32,mix(p.primary,'#ffffff',.14),6,mix(p.primary,'#000000',.15),1);
    R(c,ux+uw/2-26*s,top+34,52*s,22*s,'#fffdf7',6,mix(p.primary,'#000000',.2),1);T(c,String(i+1),ux+uw/2,top+34+11*s,fs,p.primary,800);
    R(c,ux+uw-34*s,top+32,18*s,24*s,'#ffffffcc',3,'#9cc3cc',1);R(c,ux+uw-31*s,top+36,12*s,6*s,'#f7d995',1);R(c,ux+uw-31*s,top+44,12*s,6*s,'#bfe3cf',1);}
}
function execDesks(c,p,w,D,portrait){
  const {x0,x1,top,bottom,n}=D,uw=(x1-x0)/n,on=isOpen(w),s=portrait?.9:1,fs=portrait?15:11;
  E(c,(x0+x1)/2,bottom+8,(x1-x0)/2+14,12,'#00000030');
  for(let i=0;i<n;i++){const ux=x0+i*uw,[name,col]=SUBS[i%4];
    R(c,ux+8,top+14,uw-16,(bottom-top)*.62,'#242d3a',6,'#3f4b5e',1.5);R(c,ux+8,top+14,uw-16,3,A(col,.9),1);
    const ly=top+14+(bottom-top)*.31;E(c,ux+26*s,ly,11*s,11*s,col);E(c,ux+26*s,ly,6*s,6*s,'#242d3a');E(c,ux+26*s,ly,3*s,3*s,col);
    T(c,name,ux+uw/2+10*s,ly,fit(c,name,uw-70*s,fs,800),'#e8edf5',800);
    L(c,ux+10,top+10,ux+10,bottom+6,'#9aa6b8',3);L(c,ux+uw-10,top+10,ux+uw-10,bottom+6,'#9aa6b8',3);}
  R(c,x0-6,top,x1-x0+12,15,'#151b24',6,'#475366',1.5);R(c,x0,top+2,x1-x0,3,'#6b7a9066',2);
  for(let i=0;i<n;i++){const ux=x0+i*uw,seat=ux+uw*.34,mx=ux+uw*.7;
    keyboard(c,seat,top+2,s,true);screen(c,p,mx-17*s,top+2,s*.74,on,'chart',false,true);screen(c,p,mx+19*s,top+2,s*.74,on,'line',i===WORK,true);}
}
function pods(c,p,w,D,portrait){
  const {x0,x1,top,bottom,n}=D,uw=(x1-x0)/n,on=isOpen(w),s=portrait?.9:1;
  E(c,(x0+x1)/2,bottom+8,(x1-x0)/2+14,12,'#00000018');
  for(let i=0;i<n;i++){const ux=x0+i*uw,col=POD[i%4];R(c,ux+4,top-30*s,uw-8,34*s,col,12,mix(col,'#000000',.18),2);R(c,ux+10,top-26*s,uw-20,6*s,A('#ffffff',.3),3);for(let k=0;k<6;k++)for(let j=0;j<2;j++)E(c,ux+18+k*(uw-36)/5,top-14*s+j*9*s,1.6,1.6,A('#ffffff',.45));}
  for(let i=0;i<n;i++){const ux=x0+i*uw;R(c,ux+10,top+14,uw-20,(bottom-top)*.56,'#f7f8fc',6,'#c9d0e0',1);L(c,ux+7,top+10,ux+7,bottom+6,'#aab3c6',5);L(c,ux+uw-7,top+10,ux+uw-7,bottom+6,'#aab3c6',5);}
  R(c,x0-6,top,x1-x0+12,15,'#ffffff',6,'#c3cce0',1.5);
  for(let i=0;i<=n;i++){const dx=x0+i*uw,col=POD[(i+3)%4];R(c,dx-8,top-78*s,16,bottom-top+84*s,col,8,mix(col,'#000000',.2),1.5);R(c,dx-4,top-72*s,8,20*s,A('#ffffff',.35),4);}
  for(let i=0;i<n;i++){const ux=x0+i*uw,seat=ux+uw*.4,mx=ux+uw*.72;
    headsetStand(c,ux+(portrait?26:30),top+2,s,POD[i%4]);deskPhone(c,ux+uw*.18+22*s,top+2,s*.8,on&&lit(w,1.6,i));keyboard(c,seat,top+2,s);screen(c,p,mx,top+2,s,on,'chat',i===WORK);}
}

/* ============================================================ Rooms, one per career */
function roomAccounting(c,p,w,g,portrait){
  const [wx,wy,ww,wh]=g.wall,f=g.floor,fy=f[1],on=isOpen(w),fs=portrait?16:12;
  base(c,g,portrait,'#f6e1c6',q=>{floorWood(c,q,['#d9a877','#d29f6d','#b98457']);},'#9c6b45');
  clip(c,wx,wy,ww,wh,portrait?21:22,()=>{
    // Wallpaper with little flowers, then wooden wainscot.
    for(let y=wy+26,r=0;y<fy-86;y+=30,r++)for(let x=wx+(r%2?15:0);x<wx+ww;x+=30){E(c,x,y,3,3,'#eac39c');E(c,x,y,1.2,1.2,'#f9eee0');}
    R(c,wx,fy-86,ww,86,'#c98f5f',0);for(let x=wx+12;x<wx+ww-30;x+=56)R(c,x,fy-76,44,62,'#d39b69',6,'#b07a50',1);R(c,wx,fy-90,ww,7,'#9c6b45',2);
    // Sloped attic ceiling with rafters, and a beam with fairy lights.
    const sl=portrait?170:160,sh=portrait?50:66;
    for(const [ax,dir] of [[wx,1],[wx+ww,-1]]){P(c,[[ax,wy],[ax+dir*sl,wy],[ax,wy+sh]],'#a8754f');for(let k=1;k<4;k++){const t=k/4;L(c,ax+dir*sl*t,wy,ax,wy+sh*t,'#8d5f3f',3);}L(c,ax+dir*sl,wy,ax,wy+sh,'#7a4f35',4);}
    R(c,wx,wy,ww,portrait?14:16,'#8d5f3f',0);
    c.strokeStyle='#7a4f35';c.lineWidth=1.5;c.beginPath();c.moveTo(wx+sl,wy+14);c.quadraticCurveTo(wx+ww/2,wy+(portrait?40:34),wx+ww-sl,wy+14);c.stroke();
    for(let i=0;i<=10;i++){const t=i/10,x=wx+sl+(ww-2*sl)*t,y=wy+14+(portrait?26:20)*4*t*(1-t);E(c,x,y+6,4,5,on&&lit(w,1.5,i)?'#ffe29a':'#f3dcb0');}
  });
  if(on)glow(c,portrait?300:330,portrait?420:420,portrait?220:300,'#ffd89a33');
  const wood={frame:'#b98458',mull:'#f3e3cc',sill:'#9c6b45',panes:2,cross:.45,arch:true};
  const shelf={wood:'#b98458',edge:'#8d5f3f',back:'#f3dcc0',plank:'#9c6b45',chip:'#fff3df',ink:'#7a4f3a',spines:['#8c4a3c','#3f6b4f','#a0703a','#5a4a7a','#b5563f','#6b5a3f'],spineEdge:'#4a2f22',bands:'#e8c77a'};
  const nb={frame:'#9c6b45',paper:'#fff4e3',ink:'#7a4f3a'};
  const door={frame:'#8d5f3f',jamb:'#c98f5f',leaf:'#d39b69',glass:'#cfe7ee',handle:'#e0b85a',wood:true,mat:'#c07b5d'};
  if(portrait){
    windowFrame(c,236,184,300,98,{...wood,panes:3,cross:0,arch:false},(x,y,ww2,hh)=>streetView(c,x,y,ww2,hh));
    curtains(c,222,550,176,288,portrait);
    nook(c,p,w,48,196,158,312,'TRƯỞNG PHÒNG',17);
    officeDoor(c,p,w,520,334,104,174,17,1,128,.07,door);
    binderShelf(c,p,218,334,130,146,w.words().shelf,16,shelf);
    corkBoard(c,p,358,304,112,74);
    pendant(c,590,151,196,on);
    noticeBoard(c,p,382,404,1.25,nb);
    camera(c,p,62,158,(w.c?.ops?.security?.items||[]).includes('camera'));
    rug(c,345,736,250,60,portrait);
  }else{
    windowFrame(c,428,236,170,182,wood,(x,y,ww2,hh)=>streetView(c,x,y,ww2,hh));
    curtains(c,404,622,224,418,portrait);
    nook(c,p,w,836,214,138,232,'TRƯỞNG PHÒNG',13);
    officeDoor(c,p,w,996,258,88,188,11,1,112,.3,door);
    binderShelf(c,p,234,232,170,198,w.words().shelf,13,shelf);
    corkBoard(c,p,640,246,104,94);
    clock(c,692,212,14,w,{rim:'#8d5f3f'});
    trayRack(c,p,756,262,60,104,12,{wood:'#b98458',edge:'#8d5f3f',back:'#f3dcc0',plank:'#9c6b45',chip:'#fff3df',ink:'#7a4f3a'});
    noticeBoard(c,p,140,224,1,nb);
    camera(c,p,150,197,(w.c?.ops?.security?.items||[]).includes('camera'));
    rug(c,548,630,300,46,portrait);
  }
}
function curtains(c,xl,xr,y,bottom,portrait){
  L(c,xl-6,y,xr+6,y,'#7a4f35',4);E(c,xl-6,y,5,5,'#7a4f35');E(c,xr+6,y,5,5,'#7a4f35');
  const cw=portrait?30:28,tie=y+(bottom-y)*.62;
  for(const [x,dir] of [[xl,1],[xr,-1]]){c.beginPath();c.moveTo(x,y);c.lineTo(x+dir*cw,y);c.quadraticCurveTo(x+dir*cw*.4,tie,x+dir*cw*.9,bottom);c.lineTo(x,bottom);c.closePath();c.fillStyle='#e7907a';c.fill();
    for(let k=0;k<5;k++)E(c,x+dir*cw*.35,y+14+k*(bottom-y-20)/5,2.5,2.5,'#fff1e6');R(c,x-(dir<0?cw*.7:0),tie-4,cw*.7,7,'#c86f5b',3);}
}
function corkBoard(c,p,x,y,bw,bh){
  R(c,x-6,y-6,bw+12,bh+12,'#a8754f',8);R(c,x,y,bw,bh,'#e1b98e',5);
  for(let i=0;i<6;i++){c.fillStyle='#caa27a';c.fillRect(x+8+(i*29)%(bw-16),y+6+(i*17)%(bh-12),3,3);}
  const notes=[[.06,.08,.4,.46,'#fffdf5'],[.52,.06,.4,.4,'#fff1c9'],[.1,.6,.32,.32,'#ffe3e8'],[.52,.54,.42,.38,'#fffdf5']];
  notes.forEach(([nx,ny,nw,nh,col],i)=>{c.save();c.translate(x+bw*(nx+nw/2),y+bh*(ny+nh/2));c.rotate([-.06,.05,.04,-.03][i]);R(c,-bw*nw/2,-bh*nh/2,bw*nw,bh*nh,col,3,'#d8c3a5',1);
    if(i===2)heart(c,0,4,.34,p.primary);else for(let k=0;k<3;k++)L(c,-bw*nw/2+6,-bh*nh/2+9+k*6,bw*nw/2-6-(k===2?10:0),-bh*nh/2+9+k*6,k?'#cbbcae':'#b5563f',1.5);
    E(c,0,-bh*nh/2+2,3,3,['#e57f7f','#7fb2e5','#8ccf8c','#e5c07f'][i]);c.restore();});
}
function pendant(c,x,top,y,on){L(c,x,top,x,y-16,'#5a3a2a',1.5);if(on)glow(c,x,y,90,'#ffd58a55');P(c,[[x-8,y-18],[x+8,y-18],[x+20,y],[x-20,y]],'#3f7a55');E(c,x,y+1,8,3,on?'#ffe9a8':'#e8d8b0');}
function rug(c,x,y,rx,ry,portrait){E(c,x,y,rx,ry,'#c07b5d');E(c,x,y,rx-8,ry-6,'#e8b08c');E(c,x,y,rx-18,ry-13,'#d98f6c');E(c,x,y,rx-26,ry-19,'#f1c7a2');
  for(let i=0;i<9;i++){const a=i/9*Math.PI*2;hexagon(c,x+Math.cos(a)*(rx-40),y+Math.sin(a)*(ry-26),5,'#c07b5d');}heart(c,x,y+4,portrait?.5:.45,'#c07b5d');}
/** The owner's reading nook behind a wooden arch (accounting's `counter`). */
function nook(c,p,w,x,y,nw,nh,label,fs){
  c.beginPath();c.roundRect(x-8,y-8,nw+16,nh+8,[nw/2+8,nw/2+8,6,6]);c.fillStyle='#8d5f3f';c.fill();
  c.save();c.beginPath();c.roundRect(x,y,nw,nh,[nw/2,nw/2,4,4]);c.clip();
  vgrad(c,x,y,nw,nh,'#e9c7a0','#d8ae84');
  // Tall bookcase, armchair, side table with a teapot, and a lamp's glow.
  R(c,x+nw*.06,y+nh*.18,nw*.34,nh*.62,'#9c6b45',4);for(let r=0;r<4;r++){const by=y+nh*.18+8+r*nh*.15;for(let k=0;k<5;k++)R(c,x+nw*.08+k*nw*.06,by,nw*.05,nh*.12,['#8c4a3c','#3f6b4f','#a0703a','#5a4a7a','#b5563f'][(k+r)%5],1);R(c,x+nw*.06,by+nh*.12,nw*.34,3,'#7a4f35',1);}
  if(isOpen(w))glow(c,x+nw*.8,y+nh*.35,nw*.55,'#ffd58a66');
  L(c,x+nw*.82,y+nh*.95,x+nw*.82,y+nh*.36,'#7a4f35',3);P(c,[[x+nw*.74,y+nh*.3],[x+nw*.9,y+nh*.3],[x+nw*.95,y+nh*.39],[x+nw*.69,y+nh*.39]],'#f6d7a4');
  const ay=y+nh*.94;R(c,x+nw*.42,ay-nh*.3,nw*.36,nh*.22,'#d9a441',14,'#a8792a',1.5);R(c,x+nw*.38,ay-nh*.14,nw*.44,nh*.12,'#e6b552',9,'#a8792a',1.5);R(c,x+nw*.36,ay-nh*.22,nw*.08,nh*.16,'#d9a441',6);R(c,x+nw*.76,ay-nh*.22,nw*.08,nh*.16,'#d9a441',6);
  L(c,x+nw*.44,ay-nh*.02,x+nw*.44,ay,'#7a4f35',3);L(c,x+nw*.78,ay-nh*.02,x+nw*.78,ay,'#7a4f35',3);
  c.restore();
  const bh=fs+12,by=y+nh*.08+nw*.18;R(c,x+nw*.14,by,nw*.72,bh,'#fff3df',6,'#9c6b45',2);T(c,label,x+nw/2,by+bh/2,fit(c,label,nw*.72-12,fs,800),'#7a4f35',800);
}

function roomCorp(c,p,w,g,portrait){
  const [wx,wy,ww,wh]=g.wall,f=g.floor,fy=f[1],fs=portrait?16:12,green='#3f8f6b';
  base(c,g,portrait,'#f8fbf9',q=>{floorTiles(c,q,portrait?62:60,portrait?40:30,'#e3ece7','#dbe6e0','#cfdcd4');const mid=portrait?q[1]+q[3]*.62:q[1]+q[3]*.58;R(c,q[0],mid,q[2],portrait?30:24,'#cfe3d6',0);},'#8cc4a2');
  R(c,wx,fy-46,ww,46,'#e3f1e8',0);R(c,wx,fy-48,ww,4,'#8cc4a2',0);
  // Bright ceiling: a strip with a grid of panel lights.
  const ch=portrait?34:26;R(c,wx,wy,ww,ch,'#ffffff',portrait?21:22);R(c,wx,wy+ch-3,ww,3,'#dfe9e3',1);
  for(let x=wx+50;x<wx+ww-30;x+=portrait?110:120){R(c,x-36,wy+ch/2-6,72,12,'#fffbe6',4,'#d8e4dc',1);L(c,x,wy+ch/2-6,x,wy+ch/2+6,'#e3ece6',1);}
  const glassSt={frame:'#b9d3c4',back:'#f4faf6',band:'#ffffffd8',ink:'#2f6f53',edge:'#8cc4a2',bandAt:.36};
  const meeting=(x,y,rw,rh)=>{// wall TV with the month-end chart, a table and chairs
    const tvw=rw*.5,tvx=x+rw*.25,tvy=y+rh*.08;R(c,tvx,tvy,tvw,rh*.2,'#2d3542',5);R(c,tvx+4,tvy+4,tvw-8,rh*.2-8,'#f6fbff',3);
    [.35,.5,.42,.7].forEach((v,i)=>R(c,tvx+10+i*(tvw-20)/4,tvy+rh*.2-6-(rh*.2-16)*v,(tvw-20)/4-5,(rh*.2-16)*v,i===3?green:'#a9d6bb',1));
    const ty=y+rh*.78;for(const j of [0,1]){const cx=x+rw*(.3+j*.4);R(c,cx-13,ty-rh*.2,26,rh*.13,'#4f9f74',8,'#3b7a58',1.5);}
    E(c,x+rw/2,ty,rw*.4,rh*.07,'#caa27a');E(c,x+rw/2,ty-2,rw*.38,rh*.06,'#e3c9a3');for(const j of [0,1]){const cx=x+rw*(.3+j*.4);R(c,cx-12,ty+rh*.03,24,rh*.1,'#5fae80',8,'#3b7a58',1.5);}L(c,x+rw/2,ty+rh*.05,x+rw/2,ty+rh*.14,'#b9c4bd',4);
    R(c,x+rw*.4,ty-rh*.035,rw*.12,rh*.03,'#fffdf6',1,'#d9cfbf',1);plant(c,'bamboo',x+rw*.88,y+rh-4,rh>300?.42:.34);};
  const door={frame:'#8cc4a2',jamb:'#e3f1e8',leaf:'#6fae8a',glass:'#dff1ea',kick:'#e3f1e8',handle:'#5f8f76',mat:green};
  const shelf={wood:'#dfe6e2',edge:'#9fb3a8',back:'#f7faf8',plank:'#b9c7bf',chip:'#e5f4ec',ink:'#2f6f53',spines:['#3f8f6b','#8cc4a2','#6fa0c8','#f2f4f3','#c9e3d3','#2f6f53'],spineEdge:'#7f978a',tab:'#ffffff'};
  const nb={frame:'#8cc4a2',paper:'#ffffff',ink:'#2f6f53',heart:green};
  if(portrait){
    windowFrame(c,216,182,438,98,{frame:'#dfe8e3',mull:'#ffffff',sill:'#b9c7bf',panes:4},(x,y,ww2,hh)=>dayCity(c,x,y,ww2,hh,false));
    glassRoom(c,p,48,186,158,322,'TRƯỞNG PHÒNG',17,glassSt,meeting);
    officeDoor(c,p,w,484,332,170,176,17,2,176,.07,door);
    binderShelf(c,p,218,334,130,146,w.words().shelf,16,shelf);
    logoWall(c,358,300,112,82,portrait);
    clock(c,569,308,15,w,{rim:'#9fb3a8'});
    noticeBoard(c,p,382,404,1.25,nb);
    camera(c,p,62,158,(w.c?.ops?.security?.items||[]).includes('camera'));
  }else{
    windowFrame(c,416,212,194,206,{frame:'#dfe8e3',mull:'#ffffff',sill:'#b9c7bf',panes:2},(x,y,ww2,hh)=>dayCity(c,x,y,ww2,hh,false));
    glassRoom(c,p,812,198,172,248,'TRƯỞNG PHÒNG',14,glassSt,meeting);
    officeDoor(c,p,w,996,250,88,196,11,1,112,.3,door);
    binderShelf(c,p,234,232,170,198,w.words().shelf,13,shelf);
    logoWall(c,626,234,112,118,portrait);
    clock(c,682,378,13,w,{rim:'#9fb3a8'});
    trayRack(c,p,752,262,60,112,12,{wood:'#dfe6e2',edge:'#9fb3a8',back:'#f7faf8',plank:'#b9c7bf',chip:'#e5f4ec',ink:'#2f6f53',stamp:true});
    noticeBoard(c,p,140,224,1,nb);
    camera(c,p,150,197,(w.c?.ops?.security?.items||[]).includes('camera'));
  }
}
/** "MÂY TRE XANH" logo panel with bamboo leaves. */
function logoWall(c,x,y,lw,lh,portrait){
  R(c,x,y,lw,lh,'#3f8f6b',10,'#2f6f53',2);R(c,x+5,y+5,lw-10,lh-10,'#48a07a',7);
  const cx=x+lw/2,cy=y+lh*.36;L(c,cx-6,cy+lh*.2,cx-6,cy-lh*.22,'#dff1e6',4);L(c,cx+6,cy+lh*.2,cx+6,cy-lh*.12,'#dff1e6',4);
  for(const [dx,dy,a] of [[-18,-10,-.5],[16,-4,.5],[-14,6,-.3],[20,10,.3]]){c.save();c.translate(cx+dx*(lw/112),cy+dy*(lh/110));c.rotate(a);E(c,0,0,13*(lw/112),5*(lh/110),'#dff1e6');c.restore();}
  const fs=portrait?15:12;T(c,'MÂY TRE',cx,y+lh*.74,fit(c,'MÂY TRE',lw-14,fs,800),'#ffffff',800);T(c,'XANH',cx,y+lh*.74+fs+2,fit(c,'XANH',lw-14,fs,800),'#ffffff',800);
}

function roomTax(c,p,w,g,portrait){
  const [wx,wy,ww,wh]=g.wall,f=g.floor,fy=f[1],on=isOpen(w),fs=portrait?16:12,teal='#2f5f73';
  base(c,g,portrait,'#e8f0f1',q=>{terrazzo(c,q,portrait?78:90,portrait?52:45);
    // Queue line and footprints in front of the counter.
    const ly=portrait?684:600,x0=portrait?150:240,x1=portrait?520:850;for(let x=x0;x<x1;x+=28)R(c,x,ly,16,5,'#f2c94c',2);
    for(let i=0;i<3;i++){const cx=x0+(x1-x0)*(i+.5)/3;E(c,cx-7,ly+16,4,7,'#f2c94c99');E(c,cx+7,ly+16,4,7,'#f2c94c99');}},'#7faab1');
  const rail=portrait?fy-150:fy-86;R(c,wx,rail,ww,fy-rail,'#d3e6e1',0);R(c,wx,rail-3,ww,6,'#9cc3b9',2);
  const ch=portrait?30:22;R(c,wx,wy,ww,ch,'#f6fafa',portrait?21:22);R(c,wx,wy+ch-3,ww,3,'#d8e4e6',1);
  const fan=(x,y)=>{L(c,x,wy+ch,x,y,'#6b7f86',3);const a=w.reduced?0:w.time*3;for(let k=0;k<3;k++){const t=Math.cos(a+k*2.09);E(c,x+t*34,y,Math.abs(t)*34+4,5,'#8a9ea5');}E(c,x,y,9,6,'#5d7077');};
  const blinds=(x,y,rw,rh)=>{R(c,x,y,rw,rh,'#f3efe3',0);for(let k=0;k<rw;k+=12)R(c,x+k,y,10,rh,k%24?'#e6ddc8':'#d8ceb6',1);
    R(c,x+rw*.25,y+rh*.72,rw*.5,rh*.2,'#5f6b75',4);R(c,x+rw*.3,y+rh*.66,rw*.4,rh*.08,'#eef2f2',3);};
  const glassSt={frame:'#9cc3cc',back:'#eef4f4',band:'#ffffffe0',ink:teal,edge:'#7faab1',bandAt:.3,tint:'#dff1f822'};
  const door={frame:'#7faab1',jamb:'#e8f0f1',leaf:'#5f8f9c',glass:'#dcecf0',kick:'#d3e6e1',handle:'#51707a',mat:'#7faab1'};
  const drawers={wood:'#b7c7cc',edge:'#7f949b',back:'#e4ecee',chip:'#ffffff',ink:teal};
  const nb={frame:'#7faab1',paper:'#ffffff',ink:teal,heart:'#e05d4f'};
  const served=String(12+(w.c?.tasks||[]).filter(t=>['completed','referred'].includes(t.status)).length).padStart(3,'0');
  if(portrait){
    windowFrame(c,216,184,286,96,{frame:'#cfdde0',mull:'#ffffff',sill:'#9fb3b8',panes:3},(x,y,ww2,hh)=>{dayCity(c,x,y,ww2,hh,false);for(let k=0;k<hh*.4;k+=7)R(c,x,y+k,ww2,4,'#f3efe3',1);});
    ledBoard(c,w,522,178,132,110,served,on,portrait);
    fan(330,portrait?164:200);
    glassRoom(c,p,48,186,158,322,'TRƯỞNG PHÒNG',17,glassSt,blinds);
    officeDoor(c,p,w,484,332,170,176,17,2,176,.07,door);
    pigeonholes(c,p,218,334,130,146,w.words().shelf,16,drawers,portrait);
    calendar(c,p,358,298,112,86,16);
    noticeBoard(c,p,382,404,1.25,nb);
    camera(c,p,62,158,(w.c?.ops?.security?.items||[]).includes('camera'));
  }else{
    windowFrame(c,424,292,178,126,{frame:'#cfdde0',mull:'#ffffff',sill:'#9fb3b8',panes:2},(x,y,ww2,hh)=>{dayCity(c,x,y,ww2,hh,false);for(let k=0;k<hh*.35;k+=7)R(c,x,y+k,ww2,4,'#f3efe3',1);});
    ledBoard(c,w,418,194,190,82,served,on,portrait);
    fan(690,206);
    glassRoom(c,p,824,196,154,250,'TRƯỞNG PHÒNG',14,glassSt,blinds);
    officeDoor(c,p,w,992,250,92,196,11,1,112,.3,door);
    pigeonholes(c,p,234,232,170,198,w.words().shelf,13,drawers,portrait);
    calendar(c,p,618,236,126,122,13);
    trayRack(c,p,756,262,60,104,12,{wood:'#b7c7cc',edge:'#7f949b',back:'#eef4f4',plank:'#9fb3b8',chip:'#ffffff',ink:teal});
    noticeBoard(c,p,140,224,1,nb);
    camera(c,p,150,197,(w.c?.ops?.security?.items||[]).includes('camera'));
  }
}
/** "Now serving" LED board: ticket number and the window it goes to. */
function ledBoard(c,w,x,y,bw,bh,served,on,portrait){
  L(c,x+bw*.2,y-14,x+bw*.2,y,'#6b7f86',2);L(c,x+bw*.8,y-14,x+bw*.8,y,'#6b7f86',2);
  R(c,x,y,bw,bh,'#1c262b',10,'#44565e',3);R(c,x+6,y+6,bw-12,bh-12,'#0f1619',6);
  const fs=portrait?15:12;T(c,'ĐANG PHỤC VỤ',x+bw/2,y+8+fs*.8,fit(c,'ĐANG PHỤC VỤ',bw-18,fs,800),on?'#ff9f8a':'#5b3d38',800);
  const big=portrait?38:34,col=on?'#ffb347':'#4a3a26';
  T(c,on?served:'---',x+bw*(portrait?.5:.36),y+bh*.66,big,col,800);
  if(!portrait){T(c,'→',x+bw*.66,y+bh*.66,22,col,800);E(c,x+bw*.82,y+bh*.66,15,15,on?'#ffb347':'#4a3a26');T(c,String(WORK+1),x+bw*.82,y+bh*.67,20,'#1c262b',800);}
  else{T(c,'→ '+(WORK+1),x+bw/2,y+bh-14,20,col,800);}
  if(on&&lit(w,3))E(c,x+bw-14,y+14,3,3,'#ff6b5b');
}
function calendar(c,p,x,y,bw,bh,fs){
  R(c,x-4,y-4,bw+8,bh+8,'#b9c7cc',8);R(c,x,y,bw,bh,'#fffdf7',5);R(c,x,y,bw,fs+10,'#d9534f',5);R(c,x,y+fs+2,bw,8,'#d9534f',0);
  L(c,x+bw*.3,y-8,x+bw*.3,y+6,'#6b7f86',3);L(c,x+bw*.7,y-8,x+bw*.7,y+6,'#6b7f86',3);
  T(c,'HẠN NỘP',x+bw/2,y+(fs+10)/2+1,fit(c,'HẠN NỘP',bw-12,fs),'#fff8ef',800);
  const gy=y+fs+14,cw=(bw-12)/7,rh=(bh-fs-20)/4;
  for(let r=0;r<4;r++)for(let k=0;k<7;k++){const cx=x+6+k*cw+cw/2,cy=gy+r*rh+rh/2;if(r*7+k<25)E(c,cx,cy,1.8,1.8,k>4?'#e9a19a':'#b8c2c6');}
  for(const [r,k,n] of [[2,5,'20'],[3,3,'25']]){const cx=x+6+k*cw+cw/2,cy=gy+r*rh+rh/2;c.beginPath();c.ellipse(cx,cy,cw*.75,rh*.5,0,0,Math.PI*2);c.strokeStyle='#d9534f';c.lineWidth=2.5;c.stroke();T(c,n,cx,cy,Math.round(fs*.72),'#b4403b',800);}
  L(c,x+8,gy+rh*.5,x+6+cw*3.6,gy+rh*.5,A(p.primary,.55),5);
  c.save();c.translate(x+bw-16,y+bh-10);c.rotate(.12);R(c,-18,-16,34,24,'#fff1a8',2,'#e0cf7a',1);L(c,-12,-8,10,-8,'#b4403b',1.5);L(c,-12,-2,6,-2,'#c9b86a',1.5);c.restore();
}
/** Wall of labelled filing drawers (tax office shelf). */
function pigeonholes(c,p,x,y,w,h,label,fs,st,portrait){
  R(c,x-4,y-20,w+8,h+28,st.wood,10,st.edge,2);chip(c,label,x+w/2,y-24,w-24,fs,st.chip,st.edge,st.ink);
  const cols=portrait?3:4,rows=portrait?4:5,cw=(w-8)/cols,rh=(h+4)/rows,tabs=['#f39c86','#f4cc62','#6ec6b6','#8fb2e6','#c49ae8'];
  for(let r=0;r<rows;r++)for(let k=0;k<cols;k++){const dx=x+4+k*cw,dy=y-12+r*rh;R(c,dx+2,dy+2,cw-4,rh-4,st.back,4,st.edge,1.2);
    R(c,dx+cw/2-(portrait?16:13),dy+6,portrait?32:26,portrait?12:10,'#ffffff',2,st.edge,1);R(c,dx+cw/2-(portrait?16:13),dy+6,5,portrait?12:10,tabs[(r+k)%5],1);
    R(c,dx+cw/2-9,dy+rh-12,18,5,'#7f949b',3);}
}

function roomGroup(c,p,w,g,portrait){
  const [wx,wy,ww,wh]=g.wall,f=g.floor,fy=f[1],on=isOpen(w),fs=portrait?16:12,gold='#c9a45c';
  base(c,g,portrait,'#1f2836',q=>{marble(c,q,portrait?110:120,portrait?64:56);
    // Reflections of the glass wall and the screens on the polished floor.
    const rx=portrait?[216,654]:[412,632];for(let x=rx[0];x<rx[1];x+=18){R(c,x,q[1],8,q[3]*.5,A(rnd(x)>.5?'#ffd98a':'#9fd3ff',.08),2);}},'#0f141b');
  // Walnut slats on the solid wall, a dark ceiling with downlights.
  clip(c,wx,wy,ww,wh,portrait?21:22,()=>{for(let x=wx+6;x<wx+ww;x+=14)R(c,x,wy,6,wh,'#263142',1);R(c,wx,fy-40,ww,40,'#18202b',0);R(c,wx,fy-42,ww,3,A(gold,.6),0);});
  const ch=portrait?30:22;R(c,wx,wy,ww,ch,'#141a23',portrait?21:22);
  for(let x=wx+60;x<wx+ww-40;x+=portrait?96:110){E(c,x,wy+ch-4,6,3,'#ffe9b8');c.save();c.globalAlpha=.1;P(c,[[x-5,wy+ch],[x+5,wy+ch],[x+40,fy],[x-40,fy]],'#ffe9b8');c.restore();}
  const glassSt={frame:'#3b4658',back:'#18202b',band:'#0f141bd8',ink:'#f3d9a0',edge:gold,bandAt:.34,tint:'#9fd3ff12'};
  const office=(x,y,rw,rh)=>{clip(c,x+rw*.12,y+rh*.06,rw*.76,rh*.26,4,()=>nightCity(c,x+rw*.12,y+rh*.06,rw*.76,rh*.26,w.time,w.reduced));
    const dy=y+rh*.8;if(on)glow(c,x+rw*.3,dy-rh*.1,rw*.4,'#ffd58a44');R(c,x+rw*.4,dy-rh*.24,rw*.2,rh*.2,'#1c232d',10,'#3c4758',1.5);
    R(c,x+rw*.12,dy,rw*.76,8,'#5a4636',3);R(c,x+rw*.16,dy+8,rw*.68,rh*.12,'#3f3228',3);L(c,x+rw*.24,dy-2,x+rw*.24,dy-rh*.1,'#c9a45c',2);E(c,x+rw*.24,dy-rh*.11,8,4,'#f3d9a0');
    R(c,x+rw*.62,dy-18,24,16,'#0f141b',3);R(c,x+rw*.62+2,dy-16,20,11,'#0f2440',2);
    for(let i=0;i<4;i++){E(c,x+rw*(.2+i*.2),y+rh*.52,rw*.07,rw*.07,SUBS[i][1]);E(c,x+rw*(.2+i*.2),y+rh*.52,rw*.035,rw*.035,'#18202b');}};
  const door={frame:'#0f141b',jamb:'#2c3542',leaf:gold,glass:'#23324a',kick:'#2c3542',handle:gold,mat:gold};
  const shelf={wood:'#2c3542',edge:'#465265',back:'#1a212c',plank:'#3b4658',chip:'#0f141b',ink:'#f3d9a0',spines:['#0f141b','#2f4a6f','#c9a45c','#3a4250','#6b7a90','#20344f'],spineEdge:'#465265',tab:'#e7eaf0',led:'#ffe9b8'};
  const nb={frame:'#3b4658',paper:'#eef1f5',ink:'#1f2937',heart:gold};
  if(portrait){
    windowFrame(c,216,176,438,106,{frame:'#3b4658',mull:'#465265',sill:'#2c3542',panes:5,mw:3},(x,y,ww2,hh)=>nightCity(c,x,y,ww2,hh,w.time,w.reduced));
    glassRoom(c,p,48,186,158,322,'TRƯỞNG PHÒNG',17,glassSt,office);
    officeDoor(c,p,w,484,332,170,176,17,2,176,.07,door);
    binderShelf(c,p,218,334,130,146,w.words().shelf,16,shelf);
    videoWall(c,w,352,296,124,90,on,portrait);
    noticeBoard(c,p,382,404,1.25,nb);
    camera(c,p,62,158,(w.c?.ops?.security?.items||[]).includes('camera'),true);
  }else{
    windowFrame(c,412,200,220,218,{frame:'#3b4658',mull:'#465265',sill:'#2c3542',panes:3,mw:3},(x,y,ww2,hh)=>nightCity(c,x,y,ww2,hh,w.time,w.reduced));
    videoWall(c,w,642,212,104,130,on,portrait);
    subsidiaryStrip(c,642,356,104,34);
    glassRoom(c,p,824,196,154,250,'TRƯỞNG PHÒNG',14,glassSt,office);
    officeDoor(c,p,w,992,250,92,196,11,1,112,.3,door);
    binderShelf(c,p,234,232,170,198,w.words().shelf,13,shelf);
    clock(c,784,216,13,w,{rim:gold,face:'#1f2937',tick:'#c3cad6',hand:'#f3d9a0'});
    trayRack(c,p,756,262,60,104,12,{wood:'#2c3542',edge:'#465265',back:'#1a212c',plank:'#3b4658',chip:'#0f141b',ink:'#f3d9a0'});
    noticeBoard(c,p,140,224,1,nb);
    camera(c,p,150,197,(w.c?.ops?.security?.items||[]).includes('camera'),true);
  }
}
/** 2×2 video wall with the consolidation dashboard. */
function videoWall(c,w,x,y,vw,vh,on,portrait){
  const fs=portrait?14:11,head=fs+10;R(c,x-5,y-5,vw+10,vh+10,'#0b0f15',8,'#465265',2);
  R(c,x,y,vw,head,'#0f141b',3);T(c,'HỢP NHẤT',x+vw/2,y+head/2,fit(c,'HỢP NHẤT',vw-10,fs,800),on?'#f3d9a0':'#6b7890',800);
  const sw=(vw-4)/2,sh=(vh-head-6)/2;
  for(let r=0;r<2;r++)for(let k=0;k<2;k++){const sx=x+k*(sw+4),sy=y+head+4+r*(sh+2);R(c,sx,sy,sw,sh,on?'#0f2440':'#1a212c',3);if(!on)continue;
    const i=r*2+k;glow(c,sx+sw/2,sy+sh/2,sw*.7,'#5fb7ff22');
    if(i===0){for(let b=0;b<4;b++){const hh=sh*(.25+rnd(b+3)*.55);R(c,sx+5+b*(sw-10)/4,sy+sh-4-hh,(sw-10)/4-3,hh,SUBS[b][1],1);}}
    else if(i===1){c.beginPath();for(let q=0;q<7;q++){const px=sx+4+q*(sw-8)/6,py=sy+sh*(.75-rnd(q+11)*.5+(w.reduced?0:Math.sin(w.time+q)*.04));q?c.lineTo(px,py):c.moveTo(px,py);}c.strokeStyle='#5fd0ff';c.lineWidth=2;c.stroke();}
    else if(i===2){let a=-Math.PI/2;const cx=sx+sw/2,cy=sy+sh/2,rr=Math.min(sw,sh)*.36;[.4,.25,.2,.15].forEach((v,b)=>{c.beginPath();c.moveTo(cx,cy);c.arc(cx,cy,rr,a,a+v*Math.PI*2);c.closePath();c.fillStyle=SUBS[b][1];c.fill();a+=v*Math.PI*2;});E(c,cx,cy,rr*.5,rr*.5,'#0f2440');}
    else{for(let q=0;q<3;q++){R(c,sx+5,sy+6+q*(sh-8)/3,(sw-10)*(.5+rnd(q+21)*.45),(sh-8)/3-4,q===1?'#f3d9a0':'#3f6fa8',1);}}}
}
/** Lit wall panel with the four subsidiaries' marks (landscape). */
function subsidiaryStrip(c,x,y,sw,sh){R(c,x,y,sw,sh,'#141a23',6,'#465265',1.5);
  for(let i=0;i<4;i++){const cx=x+sw*(i+.5)/4,cy=y+sh/2;E(c,cx,cy,10,10,SUBS[i][1]);E(c,cx,cy,5,5,'#141a23');E(c,cx,cy,2.2,2.2,SUBS[i][1]);}}

function roomCare(c,p,w,g,portrait){
  const [wx,wy,ww,wh]=g.wall,f=g.floor,fy=f[1],on=isOpen(w),fs=portrait?16:12;
  base(c,g,portrait,'#e9f2fd',q=>funCarpet(c,q,portrait),'#6f8fcf');
  R(c,wx,fy-40,ww,40,'#d6e4f7',0);
  const ch=portrait?30:22;R(c,wx,wy,ww,ch,'#ffffff',portrait?21:22);R(c,wx,wy+ch-3,ww,3,'#d9e3f3',1);
  // Hanging felt baffles.
  const baffles=portrait?[[230,650]]:[[420,600],[820,1080]];
  for(const [a,b] of baffles)for(let x=a,i=0;x<b;x+=26,i++)R(c,x,wy+ch-2,16,portrait?20:26,POD[i%4],4);
  const hexes=(cx,cy,r,n)=>{for(let i=0;i<n;i++){const col=POD[(i*3+1)%4],row=Math.floor(i/3),k=i%3;hexagon(c,cx+k*r*1.8+(row%2)*r*.9,cy+row*r*1.56,r,col,mix(col,'#000000',.15));hexagon(c,cx+k*r*1.8+(row%2)*r*.9,cy+row*r*1.56,r*.55,A('#ffffff',.25));}};
  const booth=(x,y,rw,rh)=>{// supervisor dashboard with a donut, desk with two screens, a mic on a stand
    R(c,x+rw*.12,y+rh*.06,rw*.76,rh*.22,'#2d3542',6);let a=-Math.PI/2;const dx=x+rw*.32,dy=y+rh*.17,rr=rh*.07;[.5,.3,.2].forEach((v,i)=>{c.beginPath();c.moveTo(dx,dy);c.arc(dx,dy,rr,a,a+v*Math.PI*2);c.closePath();c.fillStyle=POD[i];c.fill();a+=v*Math.PI*2;});E(c,dx,dy,rr*.5,rr*.5,'#2d3542');
    for(let i=0;i<3;i++)R(c,x+rw*.5,y+rh*(.1+i*.055),rw*.3*(1-i*.2),rh*.03,POD[(i+2)%4],2);
    const ty=y+rh*.82;R(c,x+rw*.1,ty-rh*.06,rw*.8,rh*.06,'#b9c7e6',3);R(c,x+rw*.06,ty,rw*.88,8,'#ffffff',4,'#c3cce0',1);R(c,x+rw*.1,ty+8,rw*.8,rh*.1,'#e5ecf8',4);
    R(c,x+rw*.2,ty-26,30,20,'#5f6b75',4);R(c,x+rw*.2+3,ty-23,24,14,'#eaf4fb',2);R(c,x+rw*.55,ty-26,30,20,'#5f6b75',4);R(c,x+rw*.55+3,ty-23,24,14,'#eaf4fb',2);headsetStand(c,x+rw*.82,ty,1,POD[3]);};
  const glassSt={frame:'#9fb0d0',back:'#f3f6fd',band:'#ffffffd8',ink:'#527a9a',edge:'#8ea6dc',bandAt:.4};
  const door={frame:'#8ea6dc',jamb:'#e9f2fd',leaf:'#6f8fcf',glass:'#dcebfa',kick:'#d6e4f7',handle:'#56709e',mat:'#6f8fcf'};
  const shelf={wood:'#dfe6f5',edge:'#9fb0d0',back:'#f7f9ff',plank:'#b9c7e6',chip:'#eaf1fd',ink:'#527a9a',spines:POD.concat(['#8fb2e6','#ffffff']),spineEdge:'#8a93a6',tab:'#ffffff'};
  const nb={frame:'#8ea6dc',paper:'#ffffff',ink:'#527a9a'};
  const boss=w.words().counter==='Trưởng ca'?'TRƯỞNG CA':'TRƯỞNG PHÒNG';
  if(portrait){
    hexes(230,196,20,6);
    windowFrame(c,356,186,298,94,{frame:'#c9d6ee',mull:'#ffffff',sill:'#9fb0d0',panes:3},(x,y,ww2,hh)=>dayCity(c,x,y,ww2,hh,false));
    glassRoom(c,p,48,186,158,322,boss,17,glassSt,booth);
    officeDoor(c,p,w,484,332,170,176,17,2,176,.07,door);
    binderShelf(c,p,218,334,130,146,w.words().shelf,16,shelf);
    queueBoard(c,p,w,352,292,126,100,16);
    noticeBoard(c,p,382,404,1.25,nb);
    camera(c,p,62,158,(w.c?.ops?.security?.items||[]).includes('camera'));
  }else{
    hexes(440,226,18,6);hexes(1000,208,11,3);
    windowFrame(c,428,306,170,112,{frame:'#c9d6ee',mull:'#ffffff',sill:'#9fb0d0',panes:2},(x,y,ww2,hh)=>dayCity(c,x,y,ww2,hh,false));
    queueBoard(c,p,w,610,214,132,132,13);
    glassRoom(c,p,824,204,154,242,boss,14,glassSt,booth);
    officeDoor(c,p,w,992,250,92,196,11,1,112,.3,door);
    binderShelf(c,p,234,232,170,198,w.words().shelf,13,shelf);
    trayRack(c,p,756,262,60,104,12,{wood:'#dfe6f5',edge:'#9fb0d0',back:'#f7f9ff',plank:'#b9c7e6',chip:'#eaf1fd',ink:'#527a9a'});
    noticeBoard(c,p,140,224,1,nb);
    camera(c,p,150,197,(w.c?.ops?.security?.items||[]).includes('camera'));
  }
}
/** Big queue board: waiting calls, lines and a satisfaction bar. */
function queueBoard(c,p,w,x,y,bw,bh,fs){
  const on=isOpen(w);R(c,x-6,y-6,bw+12,bh+12,'#44506a',12);R(c,x,y,bw,bh,on?'#26324a':'#3d465a',8);
  if(!on){L(c,x+12,y+bh-12,x+bw*.4,y+12,'#ffffff22',6);T(c,'HÀNG CHỜ',x+bw/2,y+fs,fit(c,'HÀNG CHỜ',bw-14,fs),'#8a93a6',800);return;}
  const waiting=(w.c?.tasks||[]).filter(t=>!['completed','referred','cancelled'].includes(t.status)).length;
  T(c,'HÀNG CHỜ',x+bw/2,y+fs*.95,fit(c,'HÀNG CHỜ',bw-14,fs),'#fff3d6',800);
  T(c,String(waiting).padStart(2,'0'),x+bw*.3,y+bh*.5,Math.round(fs*2.6),'#ffe29a',800);
  for(let i=0;i<4;i++){const ly=y+bh*.3+i*bh*.1;E(c,x+bw*.6,ly,4,4,i<Math.min(4,waiting)?POD[i]:'#56607a');R(c,x+bw*.66,ly-3,bw*.24,6,'#ffffff40',3);}
  const sy=y+bh*.8;R(c,x+10,sy-5,bw-20,10,'#ffffff22',5);R(c,x+10,sy-5,(bw-20)*.78,10,'#7bd48f',5);T(c,'☺',x+bw-18,sy-16,fs,'#7bd48f',800);
  if(lit(w,3))E(c,x+bw-9,y+9,3,3,'#ff9d8f');
  const ly=y+bh+14;R(c,x+8,ly-8,bw-16,16,'#f7f3ec',8,'#cbbcaa',1);for(let i=0;i<4;i++)E(c,x+22+i*(bw-44)/3,ly,4,4,lit(w,2,i*1.7)?POD[i]:'#d5ccc0');
}

/* ============================================================ Hooks */
const ROOM={accounting:roomAccounting,corp_accounting:roomCorp,tax_payroll:roomTax,group_accounting:roomGroup,customer_care:roomCare};
function room(w,p){
  const c=w.ctx,portrait=port(w),g=portrait?G.port:G.land,kind=ROOM[w.career]?w.career:'corp_accounting';
  frame(c,SHELL[kind],portrait);
  ROOM[kind](c,p,w,g,portrait);
  if(!portrait)sign(c,p,w,g.sign);
}
const CAB={
 accounting:{body:'#b98458',edge:'#8d5f3f',drawer:'#d39b69',handle:'#e0b85a',card:'#fff3df',chip:'#fff3df',ink:'#7a4f3a',n:5,cols:2},
 corp_accounting:{body:'#eef2ef',edge:'#a9b8af',drawer:'#f8faf8',handle:'#8cc4a2',chip:'#e5f4ec',ink:'#2f6f53'},
 tax_payroll:{body:'#9fb3b8',edge:'#6b7f86',drawer:'#c7d5d8',handle:'#51707a',chip:'#ffffff',ink:'#2f5f73',n:5},
 group_accounting:{body:'#2c3542',edge:'#465265',drawer:'#353f4e',handle:'#c9a45c',card:'#e7eaf0',chip:'#0f141b',ink:'#f3d9a0',keypad:true},
 customer_care:{body:'#dfe6f5',edge:'#8a93a6',doors:POD,handle:'#ffffff',chip:'#eaf1fd',ink:'#527a9a',n:3,cols:2},
};
const LEDGER={
 accounting:{body:'#c98f5f',top:'#d9a06c',edge:'#9c6b45',paper:'#fff8e7',ink:'#5a3a2a',extra:(c,x,y)=>{R(c,x-14,y-20,28,20,'#6b8f5b',4,'#4a6a3e',1);R(c,x-10,y-24,20,5,'#577a49',2);E(c,x,y-10,3,3,'#e0b85a');}},
 corp_accounting:{body:'#f2f5f3',top:'#ffffff',edge:'#b9c7bf',paper:'#fff8e7',ink:'#2f6f53',extra:(c,x,y)=>stamp(c,x,y,1,'#3f8f6b')},
 tax_payroll:{body:'#5f8f9c',top:'#e8f0f1',edge:'#44707b',paper:'#fff8e7',ink:'#ffffff',extra:(c,x,y)=>{R(c,x-13,y-18,26,18,'#eef2f2',3,'#9fb0b6',1);R(c,x-8,y-30,16,13,'#fffdf7',1,'#d6c8b5',1);}},
 group_accounting:{body:'#1c232d',top:'#a9c3d633',edge:'#9aa6b8',paper:'#eef1f5',ink:'#f3d9a0',extra:(c,x,y)=>{R(c,x-14,y-4,28,4,'#0f141b',2);R(c,x-12,y-20,24,16,'#0f141b',3);R(c,x-10,y-18,20,12,'#0f2440',2);}},
 customer_care:{body:'#f7f8fc',top:'#ffffff',edge:'#9fb0d0',paper:'#fff8e7',ink:'#527a9a',extra:(c,x,y)=>deskPhone(c,x,y,1,true)},
};
const DOC={
 accounting:{leg:'#8d5f3f',tray:'#f3dcc0',trayEdge:'#9c6b45',top:'#d9a06c',plate:'#fff3df',ink:'#7a4f3a'},
 corp_accounting:{leg:'#9fb3a8',tray:'#f3faf6',trayEdge:'#8cc4a2',top:'#ffffff',plate:'#e5f4ec',ink:'#2f6f53'},
 tax_payroll:{leg:'#7f949b',tray:'#eef4f4',trayEdge:'#7f949b',top:'#e8f0f1',plate:'#ffffff',ink:'#2f5f73'},
 group_accounting:{leg:'#465265',tray:'#2c3542',trayEdge:'#6b7890',top:'#1c232d',plate:'#0f141b',ink:'#f3d9a0'},
 customer_care:{leg:'#9fb0d0',tray:'#f7f9ff',trayEdge:'#8ea6dc',top:'#ffffff',plate:'#eaf1fd',ink:'#527a9a'},
};
const DESK={accounting:cosyDesk,corp_accounting:openDesks,tax_payroll:serviceCounter,group_accounting:execDesks,customer_care:pods};
function props(w,p){
  const c=w.ctx,portrait=port(w),g=portrait?G.port:G.land,pl=w.plan(),kind=DESK[w.career]?w.career:'corp_accounting',words=w.words(),fs=g.fs,tier=w.c?.ops?.property?.tier||'cozy',out=[],on=isOpen(w);
  const D=g.desk,uw=(D.x1-D.x0)/D.n,s=portrait?.92:1;
  out.push([pl.line,()=>DESK[kind](c,p,w,D,portrait)]);
  // Chairs behind the row.
  if(kind==='accounting')out.push([D.chairY,()=>chair(c,D.x0+uw*1.28,D.chairY,'#e7907a',s,'wood')]);
  else for(let i=0;i<D.n;i++){const x=D.x0+i*uw+uw*(kind==='tax_payroll'?.5:.4);
    const [col,style]={corp_accounting:['#7fbf95','mesh'],tax_payroll:['#5f8f9c','office'],group_accounting:['#1c232d','exec'],customer_care:[POD[i%4],'office']}[kind];
    out.push([D.chairY,()=>chair(c,x,D.chairY,col,s,style)]);}
  const [cx,cy,cw,ch]=g.cabinet;out.push([cy+ch,()=>fileCabinet(c,p,w,cx,cy,cw,ch,fs,CAB[kind])]);
  if(g.evidence){const [ex,ey,ew]=g.evidence;out.push([ey,()=>docTable(c,p,ex,ey,ew,fs,DOC[kind])]);}
  const [fx,fy,fw]=g.finance;out.push([fy,()=>ledgerDesk(c,p,w,fx,fy,fw,words.ledger,fs,LEDGER[kind])]);
  // The copier footprint (front) and the cooler footprint (back, landscape only).
  const [ox,oy,ow]=g.copier;
  out.push([oy,{
    accounting:()=>{const sx=ox+ow*.55;L(c,sx-18,oy,sx-14,oy-34,'#8d5f3f',4);L(c,sx+18,oy,sx+14,oy-34,'#8d5f3f',4);R(c,sx-22,oy-40,44,8,'#b98458',3);R(c,sx-19,oy-62,38,22,'#f3efe6',5,'#b9ae9f',1.5);R(c,sx-12,oy-70,24,9,'#fffdf7',1,'#d6c8b5',1);
      E(c,ox+10,oy-8,15,10,'#d9b77a');R(c,ox-3,oy-20,26,14,'#d9b77a',5,'#a8874f',1);for(let k=0;k<3;k++)R(c,ox+k*7-2,oy-30,6,14,'#fffdf7',3,'#d6c8b5',1);wornTag(c,w,sx-24,oy-58,48,fs-2);},
    corp_accounting:()=>copier(c,p,w,ox,oy,ow,fs),
    tax_payroll:()=>portrait?ticketKiosk(c,w,ox+ow/2,oy,.9):formsRack(c,p,ox,oy,ow),
    group_accounting:()=>copier(c,p,w,ox,oy,ow,fs,true),
    customer_care:()=>headsetCart(c,p,w,ox,oy,ow,fs),
  }[kind]]);
  if(g.cooler){const [qx,qy]=g.cooler;out.push([qy,{
    accounting:()=>floorLamp(c,qx,qy,on),corp_accounting:()=>cooler(c,qx,qy,1),tax_payroll:()=>payslipPrinter(c,p,w,qx,qy),
    group_accounting:()=>plant(c,'orchid',qx,qy,1.1),customer_care:()=>cooler(c,qx,qy,1)}[kind]]);}
  const [px,py]=g.plant,ps=portrait?.72:1.15;
  if(kind==='tax_payroll'&&!portrait)out.push([py+4,()=>ticketKiosk(c,w,px,py,.9)]);
  else out.push([py+4,()=>plant(c,{accounting:'monstera',corp_accounting:'bamboo',tax_payroll:'snake',group_accounting:'olive',customer_care:'rubber'}[kind],px,py,ps)]);
  if(tier!=='cozy')out.push([pl.bench[3],()=>kind==='tax_payroll'?waitingSeats(c,pl.bench,tier==='garden',p):sofa(c,p,pl.bench,tier==='garden',{accounting:'#d9a441',group_accounting:'#3b4658',customer_care:'#f39c86'}[kind]||p.mint)]);
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y+3,()=>plantAt(c,x,y,portrait?.7:.62)]);
  if(kind==='customer_care')out.push(...staffHeadsets(w,p));
  return out;
}

export default {id:'office',plan:PLAN,room,props};
