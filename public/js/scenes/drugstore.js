/** Drugstore scene (pharmacy): "Quầy Bình An", a small neighbourhood pharmacy
 * counter. Clean white and teal, calm and tidy; fiction only (coded boxes,
 * no real medicines or doses).
 * Back wall, left to right: the glass entrance door (`door`, landscape) with
 * the framed shop picture (`property`) above it, the queue-number display,
 * the street notice board (`board`) and a wall bench for waiting guests; then,
 * behind the counter, tall white shelves of uniform coded boxes (`shelf`), a
 * lit green cross over a bank of small drawers, the "Khay & phiếu" rack of
 * trays and slips (`evidence`), the medicine fridge with its thermometer and
 * cold-chain log (Mướp naps on top, `pet`) and the stock-room door
 * (`warehouse`).
 * Floor: the glass consultation counter across the middle with the two-step
 * check tray (`workbench`) and the small hand-over screen (`counter`), a
 * blood-pressure corner, a hand-sanitiser stand and the ledger desk
 * (`finance`). Portrait keeps the same pieces; its door is a sign stand at the
 * front. PLAN schema: see scenes/shop.js. */
import {R,E,L,T,P,fit,heart,bloom,plantAt,streetBoard} from './kit.js';

/* ------------------------------------------------------------ Floor plan */
export const PLAN={
 land:{floor:[130,452,1070,682],lane:512,line:604,home:[600,512],kx:82,ky:45,sway:30,
   blocks:[[405,448,775,460],[788,448,877,466],[430,540,880,582],[262,452,392,486],[229,478,249,488],[140,598,214,620],[980,596,1066,622],[1048,672,1070,682]],
   bench:[150,652,262,676],garden:[[318,680],[930,682]],
   customers:[[520,628],[650,634],[780,628],[330,640]],event:[420,668],officer:[930,648],
   staff:{x:470,step:115,y:476},cat:[832,262],counterSpan:[430,880],
   decor:{corner:[140,540],front:[700,676],center:[560,676]},sill:{plant:[282,438],lamp:[310,438],seat:[368,440],rug:[600,652]},
   wall:{poster:[1037,352]},
   badge:{workbench:[0,-4],counter:[0,-4],board:[34,-38],'ops:finance':[-58,-6]},
   spots:{shelf:[[475,330],90,[[475,512]]],evidence:[[725,330],70,[[725,512]]],workbench:[[522,452],55,[[522,512]]],counter:[[772,452],55,[[772,512]]],
     warehouse:[[935,370],50,[[935,492]]],board:[[268,300],42,[[268,512]]],finance:[[1023,600],42,[[1023,650],[945,610]]],
     property:[[173,242],32,[[173,490],[205,512]]],security:[[150,196],30,[[215,512]]],door:[[173,370],50,[[173,490]]],pet:[[832,245],36,[[832,512]]]}},
 port:{floor:[62,512,638,822],lane:578,line:672,home:[330,578],kx:51,ky:57,sway:24,
   blocks:[[136,505,492,518],[496,505,584,522],[150,616,520,656],[66,792,196,816],[578,690,638,714],[566,752,640,778],[462,806,572,820],[212,800,230,810]],
   bench:[244,800,330,818],garden:[[364,826],[616,826]],
   customers:[[215,702],[335,696],[455,702],[290,780]],event:[150,740],officer:[430,772],
   staff:{x:190,step:95,y:542},cat:[542,300],counterSpan:[150,520],
   decor:{corner:[92,682],front:[412,812],center:[340,748]},sill:{plant:[168,214],lamp:[232,214],seat:[430,216],rug:[330,745]},
   wall:{poster:[455,182]},
   badge:{workbench:[0,-6],counter:[0,-6],board:[30,-34],'ops:finance':[-50,-10]},
   spots:{shelf:[[200,360],70,[[200,578]]],evidence:[[430,360],60,[[430,578]]],workbench:[[250,532],50,[[250,578]]],counter:[[440,532],50,[[440,578]]],
     warehouse:[[88,412],45,[[92,548]]],board:[[88,245],40,[[100,578]]],finance:[[603,760],40,[[603,733],[540,765]]],
     property:[[622,332],30,[[612,570]]],security:[[70,180],28,[[100,578]]],door:[[517,800],45,[[517,782],[440,794]]],pet:[[542,282],36,[[542,578]]]}},
};

/* ------------------------------------------------------------ Palette & helpers */
const WHITE='#fcfffe',LINE='#cfe3de',LINE_D='#a9ccc4',TEAL='#6bbab1',TEAL_D='#2f7d78',TEAL_L='#e1f3ef',GLASS='#e4f4f6',GLASS_E='#a6d0d4',
  CROSS='#34b27b',CROSS_D='#23895d',STEEL='#d3dee0',STEEL_D='#8fa3a8',BIRCH='#f0dcbd',BIRCH_D='#cfae86',SHADOW='#46706a1f',INK='#4f716c';
const STRIPES=['#7fc7bc','#9dc0ea','#f1b2a8','#f0cf83','#c3b1e3','#a8d8a0'];
/** Draw `fn` with the origin at (x,y) scaled by s. */
const at=(c,x,y,s,fn)=>{c.save();c.translate(x,y);c.scale(s,s);fn();c.restore();};
/** A plus-shaped cross centred at (x,y), half-size r. */
function cross(c,x,y,r,col){const a=r*.36;R(c,x-a,y-r,a*2,r*2,col,a*.45);R(c,x-r,y-a,r*2,a*2,col,a*.45);}
/** A water drop (sanitiser, posters). */
function drop(c,x,y,r,col){P(c,[[x,y-r*1.7],[x-r*.86,y-r*.35],[x+r*.86,y-r*.35]],col);E(c,x,y,r,r,col);E(c,x-r*.35,y-r*.2,r*.28,r*.34,'#ffffff90');}
/** Tiny snowflake drawn with lines. */
function flake(c,x,y,r,col){for(let i=0;i<3;i++){const a=i*Math.PI/3;L(c,x-Math.cos(a)*r,y-Math.sin(a)*r,x+Math.cos(a)*r,y+Math.sin(a)*r,col,1.6);}}
const pad=(n,k=2)=>String(n).padStart(k,'0');

/* ------------------------------------------------------------ Wall pieces */
/** Title sign (landscape only; in portrait the title card covers the top). */
function sign(c,p,x,y,w,h){R(c,x-4,y+7,w+8,h,'#9fcfc6',30);R(c,x,y,w,h,WHITE,28,TEAL,3);R(c,x+10,y+10,w-20,h-20,'#f6fcfa',21,LINE,1.5);
  E(c,x+52,y+h/2,30,30,'#e6f7ee');cross(c,x+52,y+h/2,20,CROSS);
  const cx=x+w/2+24;T(c,p.title,cx,y+40,fit(c,p.title,w-150,30,800),TEAL_D,800);T(c,p.sub,cx,y+h-26,fit(c,p.sub,w-130,13),INK);heart(c,x+w-34,y+h/2+4,.34,p.primary);}

/** The green cross lightbox; it glows while the pharmacy is open. */
function crossBox(c,cx,cy,s,lit,time,reduced){
  L(c,cx-s*.32,cy-s/2-10,cx-s*.32,cy-s/2,STEEL_D,3);L(c,cx+s*.32,cy-s/2-10,cx+s*.32,cy-s/2,STEEL_D,3);
  if(lit){const k=reduced?1:.85+.15*Math.sin(time*2.2),g=c.createRadialGradient(cx,cy,s*.2,cx,cy,s*1.05);g.addColorStop(0,`rgba(96,220,150,${.34*k})`);g.addColorStop(1,'rgba(96,220,150,0)');c.fillStyle=g;c.fillRect(cx-s*1.1,cy-s*1.1,s*2.2,s*2.2);}
  R(c,cx-s/2-4,cy-s/2-4,s+8,s+8,'#e9f3f0',s*.22,STEEL_D,2);R(c,cx-s/2,cy-s/2,s,s,lit?'#f2fff7':'#eef3f1',s*.18,lit?CROSS_D:'#a4bab2',2.5);
  cross(c,cx,cy,s*.36,lit?CROSS:'#a7cbb8');if(lit){R(c,cx-s*.1,cy-s*.32,s*.06,s*.24,'#ffffff90',2);R(c,cx-s*.32,cy-s*.1,s*.2,s*.05,'#ffffff70',2);}}

/** Queue number display ("MỜI SỐ 024 → QUẦY 1"). */
function queueDisplay(c,x,y,w,h,hs,num,open){R(c,x-3,y+4,w+6,h,'#46706a26',12);R(c,x,y,w,h,'#2d4a48',11,'#1d3533',2);
  const hh=h*.36;R(c,x+5,y+5,w-10,hh,TEAL,7);T(c,'MỜI SỐ',x+w/2,y+5+hh/2+1,fit(c,'MỜI SỐ',w-24,hs,800),'#ffffff',800);
  const s=open?num:'– – –',dy=y+5+hh+(h-hh-5)/2;T(c,s,x+w*.38,dy,hs*1.7,open?'#8ef5c6':'#6f8d88',800);
  T(c,'→',x+w*.68,dy,hs*1.1,'#cfeee4',800);T(c,'QUẦY 1',x+w*.84,dy,fit(c,'QUẦY 1',w*.26,hs*.8,800),'#cfeee4',800);}

/** Tall white shelf of uniform coded boxes (P-01…) with lot strips (`shelf`). */
function boxShelf(c,p,x,y,w,h,label,rows,cols,hs){
  R(c,x-4,y-4,w+8,h+8,'#d7e9e5',9);R(c,x,y,w,h,WHITE,7,LINE_D,1.5);R(c,x+5,y+hs*2+10,w-10,h-hs*2-14,'#f1f8f6',4);
  const head=hs*1.9;R(c,x+6,y+6,w-12,head,TEAL_L,7,'#b7ddd5',1);T(c,label,x+w/2,y+6+head/2+1,fit(c,label,w-22,hs,800),TEAL_D,800);
  const top=y+head+12,rh=(h-head-18)/rows,bw=(w-14)/cols;let n=1;
  for(let r=0;r<rows;r++){const base=top+rh*(r+1)-5,bh=rh*.72;
    for(let i=0;i<cols;i++){const bx=x+7+i*bw,col=STRIPES[r%STRIPES.length];
      R(c,bx+2,base-bh,bw-4,bh,'#ffffff',3,'#bfd6d1',1);R(c,bx+2,base-bh,bw-4,bh*.26,col,[3,3,0,0]);
      R(c,bx+bw*.18,base-bh*.62,bw*.64,bh*.36,'#f4faf9',2);T(c,'P-'+pad(n++),bx+bw/2,base-bh*.44,Math.max(7,Math.min(bw*.28,rh*.2)),INK,700);}
    R(c,x+3,base,w-6,5,'#d3e7e2',2);for(let i=0;i<cols;i+=2)R(c,x+7+i*bw+bw/2-9,base+1,18,4,'#fff3cf',1);}
}

/** Bank of small white drawers under the cross. */
function drawerBank(c,x,y,w,h,cols,rows){R(c,x-3,y-3,w+6,h+6,'#d7e9e5',7);R(c,x,y,w,h,WHITE,5,LINE_D,1.5);
  const dw=(w-8)/cols,dh=(h-8)/rows;
  for(let r=0;r<rows;r++)for(let i=0;i<cols;i++){const dx=x+4+i*dw,dy=y+4+r*dh;R(c,dx+1,dy+1,dw-2,dh-2,'#f7fbfa',3,'#c7dcd7',1);
    R(c,dx+dw*.22,dy+dh*.2,dw*.56,dh*.26,(r+i)%3===0?'#fff3cf':'#e8f4f1',1);E(c,dx+dw/2,dy+dh*.68,2.4,2.4,TEAL);}}

/** Rack of labelled trays holding request slips (`evidence`). */
function trayRack(c,p,x,y,w,h,label,rows,hs){
  R(c,x-4,y-4,w+8,h+8,'#d7e9e5',9);R(c,x,y,w,h,WHITE,7,LINE_D,1.5);
  const head=hs*1.9;R(c,x+6,y+6,w-12,head,'#fdf3e0',7,'#e6d2ad',1);T(c,label,x+w/2,y+6+head/2+1,fit(c,label,w-22,hs,800),'#8a6a44',800);
  const top=y+head+12,rh=(h-head-18)/rows;
  for(let r=0;r<rows;r++){const base=top+rh*(r+1)-6;
    // slips standing in the tray, a numbered tag on its lip
    for(let i=0;i<3;i++){const sx=x+12+i*(w-24)/3,sw=(w-24)/3-6,sh=rh*(.55+.12*((r+i)%2));R(c,sx+2,base-sh,sw,sh,'#fffdf6',2,'#d9d0bd',1);
      L(c,sx+6,base-sh+6,sx+sw-4,base-sh+6,i===1?p.primary:'#c9c1ad',1.5);L(c,sx+6,base-sh+11,sx+sw-8,base-sh+11,'#d8d0bd',1.2);}
    R(c,x+6,base-rh*.26,w-12,rh*.26+3,TEAL,4);R(c,x+6,base-rh*.26,w-12,3,'#ffffff55',2);
    R(c,x+w/2-11,base-rh*.2,22,rh*.16,'#ffffff',2);T(c,pad(r+1),x+w/2,base-rh*.12,Math.max(7,rh*.13),TEAL_D,800);}
}

/** Medicine fridge: glass door, thermometer read-out, a cold-chain log on its side. */
function fridge(c,x,y,w,h,k,time,reduced){
  R(c,x+4,y+h-4,w-8,8,'#8fa3a84a',4);R(c,x,y,w,h,'#f4f8f9',9,STEEL_D,2);
  const ph=h*.13;R(c,x+4,y+4,w-8,ph,'#e2ebed',6);R(c,x+w-40*k,y+8,32*k,ph-8,'#23403e',4);T(c,'5°C',x+w-24*k,y+4+ph/2,Math.max(9,11*k),'#69f0b0',800);
  flake(c,x+14*k,y+4+ph/2,6*k,'#7fb7d9');
  const gx=x+7,gy=y+ph+10,gw=w-14,gh=h-ph-26;R(c,gx,gy,gw,gh,'#dff1f6',6,'#9fc3c9',2);
  for(let r=0;r<3;r++){const sy=gy+gh*(r+1)/3.2;L(c,gx+4,sy,gx+gw-4,sy,'#b9d5da',2);
    for(let i=0;i<4;i++){const bx=gx+10+i*(gw-20)/4;if((r+i)%3===1){R(c,bx,sy-17*k,9*k,17*k,'#ffffff',2,'#b7ccd0',1);R(c,bx,sy-21*k,9*k,5*k,['#8fc4e8','#f1b2a8','#9ad6c2'][r],2);}
      else{R(c,bx-1,sy-13*k,15*k,13*k,'#ffffff',2,'#b7ccd0',1);R(c,bx-1,sy-13*k,15*k,4*k,STRIPES[(r+i)%6],1);}}}
  c.save();c.beginPath();c.roundRect(gx,gy,gw,gh,6);c.clip();c.globalAlpha=.55;L(c,gx+gw*.2,gy+gh,gx+gw*.9,gy+gh*.1,'#ffffff',6);L(c,gx+gw*.05,gy+gh*.85,gx+gw*.55,gy+gh*.05,'#ffffff',3);c.restore();
  R(c,x+w-13,gy+gh*.3,5,gh*.28,STEEL_D,3);R(c,x+8,y+h-12,w-16,6,'#e2ebed',3);
  // Cold-chain log clipped to the left side: a little temperature line.
  const lx=x-30*k,ly=y+ph+22*k,lw=26*k,lh=40*k;L(c,x,ly+4,lx+lw,ly+4,STEEL_D,1.5);R(c,lx,ly,lw,lh,'#fffdf6',3,'#c9bfa9',1.2);R(c,lx+lw*.3,ly-3,lw*.4,6,STEEL_D,2);
  c.strokeStyle=TEAL_D;c.lineWidth=1.4;c.beginPath();for(let i=0;i<5;i++){const px=lx+4+i*(lw-8)/4,py=ly+lh*.55+Math.sin(i*1.7)*lh*.08;i?c.lineTo(px,py):c.moveTo(px,py);}c.stroke();
  L(c,lx+4,ly+lh*.3,lx+lw-4,ly+lh*.3,'#e4a8a0',1);L(c,lx+4,ly+lh*.8,lx+lw-4,ly+lh*.8,'#9dc0ea',1);
  if(!reduced&&Math.sin(time*1.3)>.2)E(c,x+w-16*k,y+ph/2+4,1.6,1.6,'#69f0b0');}

/** Stock-room door with its plate and an optional padlock (`warehouse`). */
function khoDoor(c,p,x,y,w,h,label,locked,hs){R(c,x-7,y-7,w+14,h+7,'#d4e6e2',9);R(c,x,y,w,h,'#eef6f4',5,'#a9c7c1',2);
  R(c,x+w*.2,y+h*.1,w*.6,h*.18,'#d4ecef',8,'#a9c7c1',1.5);L(c,x+w/2,y+h*.1,x+w/2,y+h*.28,'#ffffff',2);
  R(c,x+w*.12,y+h*.36,w*.76,hs*1.9,WHITE,6,TEAL,1.5);T(c,label,x+w/2,y+h*.36+hs*.97,fit(c,label,w*.66,hs,800),TEAL_D,800);
  R(c,x+w*.12,y+h*.72,w*.76,h*.22,'#e2efec',4);R(c,x+w-16,y+h*.52,6,18,STEEL_D,3);
  if(locked){const lx=x+w-13,ly=y+h*.6;c.beginPath();c.arc(lx,ly,5,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=3;c.stroke();R(c,lx-8,ly,16,15,'#d8c596',4,'#a59470',1);}}

/** Glass entrance door with its open / closed sign (`door`, landscape). */
function entranceDoor(c,p,x,y,w,h,open,words,hs){R(c,x-7,y-7,w+14,h+7,TEAL,9);R(c,x,y,w,h,open?'#e6f7f1':'#d6e7ea',4);
  c.save();c.beginPath();c.rect(x,y,w,h);c.clip();
  if(open){E(c,x+w*.25,y+h*.5,w*.4,h*.16,'#bfe0c4');E(c,x+w*.85,y+h*.46,w*.35,h*.2,'#a9d3b6');R(c,x,y+h*.62,w,h*.38,'#e9e4d6',0);L(c,x,y+h*.62,x+w,y+h*.62,'#d6cdb5',2);E(c,x+w*.7,y+h*.14,10,10,'#fff0be');}
  c.globalAlpha=.6;L(c,x+w*.15,y+h*.5,x+w*.55,y+h*.1,'#ffffff',6);L(c,x+w*.35,y+h*.62,x+w*.8,y+h*.2,'#ffffff',3);c.restore();
  L(c,x+w/2,y,x+w/2,y+h,TEAL_D,3);L(c,x+w/2-14,y+h*.52,x+w/2-4,y+h*.52,STEEL_D,4);L(c,x+w/2+4,y+h*.52,x+w/2+14,y+h*.52,STEEL_D,4);
  cross(c,x+w/4,y+h*.3,7,open?CROSS:'#a7cbb8');cross(c,x+w*.75,y+h*.3,7,open?CROSS:'#a7cbb8');
  const s=open?words.open_sign:words.closed_sign,sw=w+16,sy=y+h*.36;L(c,x+w/2,sy-14,x+w/2-18,sy,'#8fa3a8',1.5);L(c,x+w/2,sy-14,x+w/2+18,sy,'#8fa3a8',1.5);
  R(c,x+w/2-sw/2,sy,sw,hs*1.9,'#ffffff',9,open?CROSS:'#d59a9a',2);T(c,s,x+w/2,sy+hs*.97,fit(c,s,sw-10,hs,800),open?TEAL_D:'#a35f63',800);}

/** Framed little house over the door: the `property` hotspot. */
function plaque(c,p,cx,y,w,h){R(c,cx-w/2,y,w,h,'#bcd8d1',7);R(c,cx-w/2+4,y+4,w-8,h-8,WHITE,5);const s=h/34,b=y+h-7;
  P(c,[[cx-12*s,b-11*s],[cx,b-21*s],[cx+12*s,b-11*s]],p.primary);R(c,cx-9*s,b-12*s,18*s,12*s,TEAL_L,2);cross(c,cx,b-6*s,3.6*s,CROSS);}

/** Small health poster: water, sleep, a smile. */
function healthPoster(c,p,x,y,w,h){R(c,x,y,w,h,'#ffffff',7,LINE_D,1.5);R(c,x+4,y+4,w-8,18,TEAL,5);T(c,'SỐNG KHỎE',x+w/2,y+13,fit(c,'SỐNG KHỎE',w-14,11,800),'#ffffff',800);
  const cy=y+h*.62;drop(c,x+w*.22,cy+4,7,'#7cc2e0');
  c.beginPath();c.arc(x+w*.5,cy,9,Math.PI*.35,Math.PI*1.65);c.arc(x+w*.5+5,cy-2,7,Math.PI*1.55,Math.PI*.45,true);c.closePath();c.fillStyle='#f0cf83';c.fill();
  heart(c,x+w*.78,cy+6,.36,'#eea0b0');L(c,x+10,y+h-10,x+w-10,y+h-10,'#dcebe7',2);}

/** Wall clock. */
function clock(c,p,x,y,r,time,reduced){E(c,x+2,y+3,r+3,r+3,'#46706a1c');E(c,x,y,r+3,r+3,TEAL);E(c,x,y,r,r,'#ffffff');
  for(let i=0;i<12;i++){const a=i*Math.PI/6;E(c,x+Math.cos(a)*r*.8,y+Math.sin(a)*r*.8,1.3,1.3,'#9fb3b0');}
  L(c,x,y,x+r*.05,y-r*.55,INK,3);L(c,x,y,x+r*.45,y+r*.12,INK,3);const a=reduced?1:time*Math.PI/30;L(c,x,y,x+Math.sin(a)*r*.75,y-Math.cos(a)*r*.75,'#e08a86',1.3);E(c,x,y,2.4,2.4,INK);}

/** Opening hours plate. */
function hoursPlate(c,x,y,w,h,hs){R(c,x,y,w,h,'#ffffff',8,LINE_D,1.5);T(c,'GIỜ MỞ CỬA',x+w/2,y+h*.32,fit(c,'GIỜ MỞ CỬA',w-12,hs,800),TEAL_D,800);
  L(c,x+10,y+h*.52,x+w-10,y+h*.52,'#dcebe7',1.5);T(c,'7:00 – 21:00',x+w/2,y+h*.74,fit(c,'7:00 – 21:00',w-12,hs,700),INK,700);}

/** Waiting bench against the wall (landscape; drawn with the room so Mướp's sill things sit on it). */
function wallBench(c,p,x0,x1,seat,feet){const w=x1-x0;
  R(c,x0+4,seat-50,w-8,34,'#e6f4f0',12,LINE_D,1.5);for(let i=0;i<3;i++)R(c,x0+14+i*(w-28)/3,seat-44,(w-28)/3-8,22,'#d3ece6',8);
  L(c,x0+12,seat+6,x0+12,feet,BIRCH_D,5);L(c,x1-12,seat+6,x1-12,feet,BIRCH_D,5);L(c,x0+w/2,seat+6,x0+w/2,feet,BIRCH_D,5);
  R(c,x0-3,seat-6,w+6,14,BIRCH,6,BIRCH_D,1.5);R(c,x0+2,seat-12,w-4,9,TEAL,5);R(c,x0+6,seat-11,w-12,3,'#ffffff50',2);}

/** Security gear: dome camera (or a safety plaque), door bell, a warm lamp. */
function security(c,p,items,cam,bell,lamp){
  if(items.includes('camera')){const [x,y]=cam;L(c,x-8,y+12,x+2,y+2,STEEL_D,4);R(c,x-4,y-10,36,20,'#f5f7f6',7,'#a7aaa2',2);E(c,x+26,y,7,8,'#7a8992');E(c,x+27,y,3,4,'#b4d9df');E(c,x+2,y-5,2,2,'#90bd8b');}
  else{const [x,y]=cam;R(c,x-6,y-11,38,22,'#ffffff',8,LINE_D,1);T(c,'♧',x+13,y,14,TEAL_D);}
  if(items.includes('bell')){const [x,y]=bell;L(c,x,y-14,x,y-4,STEEL_D,2);P(c,[[x-10,y+11],[x+10,y+11],[x+7,y-3],[x-7,y-3]],'#f0ce85');E(c,x,y-3,7,4,'#f0ce85');E(c,x,y+13,4,3,'#d4ad64');}
  if(items.includes('light')){const [x,y]=lamp,g=c.createRadialGradient(x,y+16,0,x,y+16,80);g.addColorStop(0,'#ffe1a44a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(x-80,y-64,160,160);
    L(c,x,y-16,x,y-6,STEEL_D,3);R(c,x-13,y-8,26,20,'#fff0b8',8,'#b69b79',2);}}

/* ------------------------------------------------------------ Floor pieces (origin: middle of the feet line) */
/** Glass consultation counter; `top` is the height of the worktop above the feet. */
function counter(w,p,half,top,k,port){const c=w.ctx,worn=(w.c?.ops?.equipment?.condition??100)<100,check=w.c?.upgrades?.includes('workbench'),open=!!w.c?.open;
  E(c,0,4,half+16,10,SHADOW);
  R(c,-half+6,-top+12,half*2-12,top-12,WHITE,10,LINE_D,2);
  const gy=-top+22,gh=top*.36;R(c,-half+18,gy,half*2-36,gh,GLASS,6,GLASS_E,1.5);
  // Little boxes on the display shelf behind the glass.
  for(let i=0,x=-half+30;x<half-40;i++,x+=34){R(c,x,gy+gh-18,24,15,'#ffffff',3,'#c1d7d2',1);R(c,x,gy+gh-18,24,5,STRIPES[i%6],[3,3,0,0]);}
  L(c,-half+22,gy+gh*.42,half-22,gy+gh*.42,'#cbe4e6',2);
  for(let i=0,x=-half+40;x<half-40;i++,x+=52){R(c,x,gy+gh*.42-14,12,14,'#ffffff',3,'#c1d7d2',1);R(c,x,gy+gh*.42-17,12,4,['#8fc4e8','#9ad6c2','#f1b2a8'][i%3],2);}
  c.save();c.beginPath();c.roundRect(-half+18,gy,half*2-36,gh,6);c.clip();c.globalAlpha=.5;for(let x=-half+30;x<half;x+=150){L(c,x,gy+gh,x+50,gy,'#ffffff',8);L(c,x+22,gy+gh,x+62,gy,'#ffffff',3);}c.restore();
  // Drawer fronts under the glass, the teal kick plate with little crosses.
  const dy=gy+gh+8,dh=-20-dy;for(let x=-half+18;x<half-18;x+=(half*2-36)/4)R(c,x+2,dy,(half*2-36)/4-4,dh,'#f5faf9',4,'#d2e4e0',1);
  for(let x=-half+18,i=0;i<4;i++,x+=(half*2-36)/4)R(c,x+(half*2-36)/8-12,dy+dh/2-2,24,4,TEAL,2);
  R(c,-half+6,-20,half*2-12,20,TEAL,[0,0,9,9]);for(let x=-half+40;x<half-30;x+=90)cross(c,x,-10,5,'#ffffffa0');
  // Worktop.
  R(c,-half-4,-top,half*2+8,17,'#f7fcfb',8,'#b5d3cc',2);R(c,-half,-top+2,half*2,4,'#ffffff',2);
  const y=-top+1;
  // Two-step check tray (workbench): ① read the code, ② match the slip.
  const tx=-half+92*k;R(c,tx-52*k,y-15*k,104*k,15*k,'#eaf6f3',5,TEAL,1.5);L(c,tx,y-14*k,tx,y-1,TEAL,1.5);
  R(c,tx-44*k,y-26*k,16*k,14*k,'#ffffff',2,'#b9d0cb',1);R(c,tx-44*k,y-26*k,16*k,4*k,STRIPES[0],1);R(c,tx-24*k,y-22*k,16*k,10*k,'#ffffff',2,'#b9d0cb',1);R(c,tx-24*k,y-22*k,16*k,3*k,STRIPES[2],1);
  P(c,[[tx+8*k,y-4*k],[tx+40*k,y-6*k],[tx+38*k,y-28*k],[tx+10*k,y-26*k]],'#fffdf6');L(c,tx+14*k,y-21*k,tx+34*k,y-22*k,'#c9c1ad',1.3);L(c,tx+14*k,y-15*k,tx+30*k,y-16*k,'#c9c1ad',1.3);
  for(const [n,dx] of [['1',-30],['2',24]]){E(c,tx+dx*k,y-38*k,8*k,8*k,TEAL_D);T(c,n,tx+dx*k,y-37.5*k,10*k,'#ffffff',800);}
  if(check){R(c,tx+44*k,y-30*k,20*k,26*k,'#ffffff',4,'#9dc6b0',1.5);L(c,tx+48*k,y-18*k,tx+52*k,y-13*k,CROSS,2);L(c,tx+52*k,y-13*k,tx+60*k,y-24*k,CROSS,2);}
  // Pen cup and the service bell in the middle (portrait: the player stands there).
  if(!port){R(c,-18*k,y-20*k,14*k,20*k,TEAL_L,3,LINE_D,1);L(c,-14*k,y-20*k,-16*k,y-32*k,'#e8b85c',2.5);L(c,-8*k,y-20*k,-5*k,y-31*k,'#7cb2d8',2.5);
  E(c,20*k,y-2,13*k,4*k,STEEL_D);c.beginPath();c.arc(20*k,y-4*k,10*k,Math.PI,0);c.fillStyle='#e9eef0';c.fill();E(c,20*k,y-15*k,2.5*k,2.5*k,STEEL_D);}
  // Small hand-over screen (counter) and a paper bag waiting for its guest.
  const sx=half-104*k;R(c,sx-8*k,y-4*k,16*k,4*k,STEEL_D,2);R(c,sx-3*k,y-14*k,6*k,11*k,STEEL_D,2);R(c,sx-34*k,y-54*k,68*k,42*k,'#2d4a48',7);R(c,sx-30*k,y-50*k,60*k,34*k,open?'#e6f8f2':'#c9d8d6',4);
  if(open){cross(c,sx-17*k,y-33*k,8*k,CROSS);for(let i=0;i<3;i++)R(c,sx-4*k,y-44*k+i*9*k,(28-i*6)*k,4*k,i?'#bcd8d1':TEAL,2);}
  const bx=half-40*k;P(c,[[bx-14*k,y],[bx+14*k,y],[bx+12*k,y-30*k],[bx-12*k,y-30*k]],'#fffaf0');L(c,bx-12*k,y-30*k,bx+12*k,y-30*k,'#e2d6bf',2);cross(c,bx,y-15*k,6*k,CROSS);
  c.beginPath();c.arc(bx,y-30*k,6*k,Math.PI,0);c.strokeStyle='#d8c9ac';c.lineWidth=1.5;c.stroke();
  if(worn){R(c,-half+14,y-16*k-2,62*k,15*k,'#f7d995',4);T(c,'CẦN KIỂM',-half+14+31*k,y-9*k-2,9*k,'#94643d',800);}
  if(port)return;
  // "QUẦY 1" tent card.
  P(c,[[-66,y],[-40,y],[-44,y-18],[-62,y-18]],'#ffffff');R(c,-66,y-19,26,18,TEAL_L,3,LINE_D,1);T(c,'1',-53,y-10,11,TEAL_D,800);}

/** Blood-pressure corner: a little table with the monitor and its cuff. */
function bpCorner(c,p,hs){E(c,0,2,40,6,SHADOW);L(c,-26,-44,-28,0,BIRCH_D,4);L(c,26,-44,28,0,BIRCH_D,4);R(c,-36,-52,72,11,WHITE,5,LINE_D,1.5);
  R(c,-26,-86,40,35,'#ffffff',7,STEEL_D,1.5);R(c,-21,-81,30,17,'#e2f7ef',3);heart(c,-14,-70,.2,'#e9899d');for(let i=0;i<2;i++)R(c,-6,-78+i*6,12-i*4,3,TEAL,1.5);
  E(c,-16,-58,2.5,2.5,TEAL);E(c,-6,-58,2.5,2.5,'#bcd8d1');E(c,4,-58,2.5,2.5,'#bcd8d1');
  c.beginPath();c.moveTo(14,-66);c.quadraticCurveTo(30,-66,26,-54);c.strokeStyle='#8fa3a8';c.lineWidth=2;c.stroke();R(c,16,-58,20,9,TEAL,4);R(c,19,-56,14,2,'#ffffff60',1);
  R(c,-30,-40,60,hs*1.5,'#ffffff',4,LINE_D,1);T(c,'ĐO HUYẾT ÁP',0,-40+hs*.77,fit(c,'ĐO HUYẾT ÁP',54,hs,800),TEAL_D,800);}

/** Hand-sanitiser stand. */
function sanitiser(c){E(c,0,1,13,4,'#8fa3a855');E(c,0,0,10,3,STEEL_D);L(c,0,0,0,-62,STEEL,4);L(c,0,0,0,-62,'#ffffff70',1);R(c,-8,-60,16,4,STEEL_D,2);
  R(c,-10,-92,20,30,'#ffffff',5,STEEL_D,1.5);R(c,-6,-66,12,4,'#e2ebed',2);drop(c,0,-76,4.5,'#7cc2e0');E(c,0,-54,2,2.5,'#bfe3f1');}

/** Ledger desk (finance). */
function financeDesk(c,p,label,hs){E(c,0,2,46,6,SHADOW);R(c,-42,-40,84,38,WHITE,9,LINE_D,2);R(c,-36,-34,72,24,TEAL_L,5);
  T(c,label,0,-22,fit(c,label,66,hs,800),TEAL_D,800);R(c,-46,-50,92,12,'#f7fcfb',5,LINE_D,1.5);
  P(c,[[-24,-52],[0,-49],[0,-61],[-22,-64]],'#fff8e7');P(c,[[24,-52],[0,-49],[0,-61],[22,-64]],'#fffdf5');L(c,0,-49,0,-61,'#c7ad90',1.5);L(c,-18,-58,-5,-56,TEAL,1.5);L(c,5,-56,18,-58,'#c4b3a0',1.5);
  R(c,28,-64,14,14,'#eaf4f5',4,'#a9c9d0',1);E(c,35,-54,4,2,'#e6c36b');}

/** Floor waiting bench (portrait). */
function floorBench(c,p){E(c,0,2,70,6,SHADOW);for(const x of [-56,48])R(c,x,-22,8,22,BIRCH_D,3);
  R(c,-64,-68,128,28,'#e6f4f0',11,LINE_D,1.5);for(let i=0;i<3;i++)R(c,-56+i*40,-63,34,18,'#d3ece6',7);
  R(c,-68,-34,136,12,BIRCH,6,BIRCH_D,1.5);R(c,-62,-42,124,11,TEAL,6);R(c,-58,-41,116,3,'#ffffff50',2);}

/** Two padded chairs and a side table (sunny / garden tiers). */
function restNook(c,p,garden){E(c,0,2,56,6,SHADOW);for(const cx of [-30,30]){R(c,cx-20,-46,40,28,'#cdeae3',10,LINE_D,1.5);R(c,cx-22,-22,44,12,TEAL,6);L(c,cx-16,-10,cx-17,0,BIRCH_D,3);L(c,cx+16,-10,cx+17,0,BIRCH_D,3);}
  R(c,-8,-30,16,4,BIRCH,2);L(c,0,-26,0,0,BIRCH_D,3);R(c,-5,-40,10,10,'#ffffff',3,LINE_D,1);if(garden)bloom(c,0,-46,6,p.primary);}

/** Front door sign stand (portrait `door`). */
function doorStand(c,p,open,words,hs,bell){const s=open?words.open_sign:words.closed_sign;L(c,-50,-14,-56,2,STEEL_D,4);L(c,50,-14,56,2,STEEL_D,4);
  if(bell){L(c,54,-50,54,-62,STEEL_D,2);L(c,54,-62,44,-62,STEEL_D,2);P(c,[[36,-40],[52,-40],[49,-52],[39,-52]],'#f0ce85');E(c,44,-52,6,3,'#f0ce85');E(c,44,-38,3,2.5,'#d4ad64');}
  R(c,-68,-50,136,40,'#ffffff',14,open?CROSS:'#d59a9a',2);cross(c,-51,-30,7,open?CROSS:'#c9b0b0');T(c,s,10,-30,fit(c,s,100,hs,800),open?TEAL_D:'#a35f63',800);}

/* ------------------------------------------------------------ Rooms */
const qnum=w=>pad(((w.c?.day||1)*7+(w.c?.turn||0)*3+12)%1000,3);
function wallTiles(c,x,y,w,h,size){R(c,x,y,w,h,'#fbfefd',0);for(let yy=y+size;yy<y+h;yy+=size)L(c,x,yy,x+w,yy,'#e3efec',1.2);for(let xx=x+size;xx<x+w;xx+=size)L(c,xx,y,xx,y+h,'#e3efec',1.2);
  R(c,x,y-7,w,7,TEAL_L,0);L(c,x,y,x+w,y,'#a8d6cc',2);}
function floorTiles(c,x,y,w,h,size){c.save();c.beginPath();c.roundRect(x,y,w,h,15);c.clip();
  for(let xx=x,i=0;xx<x+w;xx+=size,i++)for(let yy=y,j=0;yy<y+h;yy+=size,j++){c.fillStyle=(i+j)%2?'#eef6f3':'#f8fbfa';c.fillRect(xx,yy,size,size);}
  for(let yy=y;yy<y+h;yy+=size)L(c,x,yy,x+w,yy,'#dde9e6',1);c.restore();}

function landRoom(w,p){const c=w.ctx,words=w.words(),items=w.c?.ops?.security?.items||[],open=!!w.c?.open,t=w.time,rd=w.reduced;
  E(c,600,724,505,28,'#46706a1a');R(c,85,150,1030,570,'#bcd8d1',35);R(c,96,154,1008,556,'#f7fcfb',30,'#cfe3de',3);
  R(c,108,164,984,292,p.wall,22);wallTiles(c,108,372,984,78,19);
  floorTiles(c,108,448,984,242,48);R(c,108,444,984,7,'#cfe3de',3);
  // Queue guide on the floor in front of the counter.
  c.setLineDash([14,10]);L(c,452,604,858,604,'#8fcfc3',3);c.setLineDash([]);
  sign(c,p,360,40,480,100);
  // Public side: door, queue display, notice board, poster, bench.
  plaque(c,p,173,224,62,36);
  entranceDoor(c,p,132,272,82,176,open,words,11);R(c,126,452,94,9,'#cfe3de',4);
  queueDisplay(c,232,180,160,60,13,qnum(w),open);
  streetBoard(c,p,236,262,1);
  healthPoster(c,p,314,258,76,84);
  wallBench(c,p,262,392,446,486);
  // Behind the counter: coded shelves, the cross over the drawers, trays & slips, fridge, stock room.
  boxShelf(c,p,405,196,140,254,p.shelves[0],5,5,12);
  crossBox(c,610,246,76,open,t,rd);
  drawerBank(c,556,300,108,150,4,5);
  trayRack(c,p,675,196,100,254,p.shelves[1],4,12);
  fridge(c,790,262,86,188,1,t,rd);
  khoDoor(c,p,896,272,78,176,words.store,items.includes('lock'),13);
  clock(c,p,1038,200,19,t,rd);
  hoursPlate(c,992,236,92,54,11);
  security(c,p,items,[146,196],[173,212],[1040,420]);
  if(w.c?.ops?.property?.tier==='garden')for(let i=0;i<3;i++)bloom(c,1010+i*30,316,6,[p.primary,'#f2b9c9','#f3d98a'][i]);}

function portRoom(w,p){const c=w.ctx,words=w.words(),items=w.c?.ops?.security?.items||[],open=!!w.c?.open,t=w.time,rd=w.reduced;
  E(c,350,857,324,23,'#46706a1a');R(c,22,114,656,738,'#bcd8d1',31);R(c,29,117,642,724,'#f7fcfb',26,'#cfe3de',3);
  R(c,40,139,620,372,p.wall,21);wallTiles(c,40,436,620,70,23);
  floorTiles(c,40,505,620,324,56);R(c,40,501,620,7,'#cfe3de',3);
  c.setLineDash([14,10]);L(c,168,676,506,676,'#8fcfc3',3);c.setLineDash([]);
  // Left: notice board over the stock-room door.
  streetBoard(c,p,56,206,1);
  khoDoor(c,p,52,318,72,187,words.store,items.includes('lock'),16);
  // Behind the counter.
  boxShelf(c,p,136,214,126,291,p.shelves[0],6,4,16);
  crossBox(c,314,262,70,open,t,rd);
  drawerBank(c,272,314,84,191,3,6);
  trayRack(c,p,366,214,126,291,p.shelves[1],4,16);
  // Right: queue display, fridge, clock, framed picture, hours.
  queueDisplay(c,500,166,152,66,16,qnum(w),open);
  fridge(c,500,300,84,205,1.1,t,rd);
  clock(c,p,623,268,19,t,rd);
  plaque(c,p,622,314,54,40);
  hoursPlate(c,594,368,58,64,16);
  security(c,p,items.filter(i=>i!=='bell'),[62,180],[0,0],[622,470]);
  if(w.c?.ops?.property?.tier==='garden')for(let i=0;i<3;i++)bloom(c,602+i*20,444,5,[p.primary,'#f2b9c9','#f3d98a'][i]);}

/* ------------------------------------------------------------ Floor props */
function landProps(w,p){const c=w.ctx,words=w.words(),tier=w.c?.ops?.property?.tier||'cozy',out=[];
  out.push([582,()=>at(c,655,582,1,()=>counter(w,p,225,112,1,false))]);
  out.push([488,()=>at(c,239,488,1,()=>sanitiser(c))]);
  out.push([620,()=>at(c,177,620,1,()=>bpCorner(c,p,9))]);
  out.push([622,()=>at(c,1023,622,1,()=>financeDesk(c,p,words.ledger,12))]);
  out.push([682,()=>plantAt(c,1060,680,.62)]);
  if(tier!=='cozy')out.push([676,()=>at(c,206,676,1,()=>restNook(c,p,tier==='garden'))]);
  if(tier==='garden')for(const [x,y] of PLAN.land.garden)out.push([y+4,()=>plantAt(c,x,y,.55)]);
  return out;}

function portProps(w,p){const c=w.ctx,words=w.words(),tier=w.c?.ops?.property?.tier||'cozy',open=!!w.c?.open,out=[];
  out.push([656,()=>at(c,335,656,1,()=>counter(w,p,185,108,1.1,true))]);
  out.push([816,()=>at(c,131,816,1,()=>floorBench(c,p))]);
  out.push([810,()=>at(c,221,810,1.05,()=>sanitiser(c))]);
  out.push([714,()=>at(c,608,714,.95,()=>bpCorner(c,p,12))]);
  out.push([778,()=>at(c,603,778,.95,()=>financeDesk(c,p,words.ledger,16))]);
  out.push([820,()=>at(c,517,820,1,()=>doorStand(c,p,open,words,17,(w.c?.ops?.security?.items||[]).includes('bell')))]);
  if(tier!=='cozy')out.push([818,()=>at(c,287,818,.8,()=>restNook(c,p,tier==='garden'))]);
  if(tier==='garden')for(const [x,y] of PLAN.port.garden)out.push([y+4,()=>plantAt(c,x,y,.5)]);
  return out;}

export default {
  id:'drugstore',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
