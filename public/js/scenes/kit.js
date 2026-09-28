/** Canvas drawing helpers shared by the world and every scene kind
 * (public/js/scenes/<kind>.js). Scene pixels: landscape 1200×790,
 * portrait 700×890. Text goes through the i18n layer. */
import {t as tr} from '../v4/i18n.js';

const FONT='"Trebuchet MS", "Segoe UI", sans-serif';
/** Rounded rect, optional stroke. */
export const R=(c,x,y,w,h,fill,r=12,stroke=null,lw=2)=>{c.beginPath();c.roundRect(x,y,w,h,r);c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=lw;c.stroke();}};
/** Filled ellipse. */
export const E=(c,x,y,rx,ry,fill)=>{c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fillStyle=fill;c.fill();};
/** Round-capped line. */
export const L=(c,x,y,x2,y2,color,width=2)=>{c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.beginPath();c.moveTo(x,y);c.lineTo(x2,y2);c.stroke();};
/** Font size that makes `s` fit `max` pixels (never below 10). */
export const fit=(c,s,max,size,weight=700)=>{c.font=`${weight} ${size}px ${FONT}`;const w=c.measureText(tr(String(s))).width;return w>max?Math.max(10,Math.floor(size*max/w)):size;};
/** Centered (by default) translated text. */
export const T=(c,s,x,y,size=16,color='#765952',weight=700,align='center')=>{c.font=`${weight} ${size}px ${FONT}`;c.fillStyle=color;c.textAlign=align;c.textBaseline='middle';c.fillText(tr(String(s)),x,y);};
/** Filled polygon from [[x,y],…]. */
export const P=(c,points,fill)=>{c.beginPath();points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fillStyle=fill;c.fill();};
export function heart(c,x,y,scale=1,col='#cf839c'){c.save();c.translate(x,y);c.scale(scale,scale);c.beginPath();c.moveTo(0,6);c.bezierCurveTo(-25,-9,-15,-27,0,-13);c.bezierCurveTo(15,-27,25,-9,0,6);c.fillStyle=col;c.fill();c.restore();}
export function bloom(c,x,y,size=12,color='#efb5ca'){for(let i=0;i<5;i++){const a=i*Math.PI*2/5;E(c,x+Math.cos(a)*size*.6,y+Math.sin(a)*size*.6,size*.5,size*.5,color);}E(c,x,y,size*.33,size*.33,'#f3d590');}
/** Potted plant standing at (x,y). */
export function plantAt(c,x,y,size=1){c.save();c.translate(x,y);c.scale(size,size);E(c,0,5,23,7,'#8b73531a');R(c,-17,-30,34,32,'#efcab9',8,'#c79b85',1.5);R(c,-20,-34,40,9,'#e4b19a',3);L(c,0,-34,0,-92,'#6c9f78',3);
  for(let i=0;i<5;i++){const dir=i%2?1:-1;c.save();c.translate(0,-40-i*10);c.rotate(dir*.7);E(c,dir*12,-5,20,8,i%2?'#a4c896':'#78ad91');c.restore();}c.restore();}
/** The bear mascot on signs. */
export function mascot(c,x,y,scale=1){c.save();c.translate(x,y);c.scale(scale,scale);E(c,-20,-24,12,14,'#e2b892');E(c,20,-24,12,14,'#e2b892');E(c,0,-4,33,30,'#f2d6b0');E(c,-10,-8,3,4,'#805a49');E(c,10,-8,3,4,'#805a49');E(c,-20,1,6,3,'#e9a89c');E(c,20,1,6,3,'#e9a89c');E(c,0,1,5,3,'#a97764');L(c,0,4,0,8,'#a97764',1.5);c.restore();}
/** A framed sign with mascot, title and subtitle that always fit.
 * (x,y) is the top-left; w,h the outer size. */
export function signBoard(c,p,x,y,w,h){R(c,x-5,y+7,w+10,h,'#c79879',31);R(c,x,y,w,h,'#fff9ed',30,'#e7c9ad',3);R(c,x+10,y+10,w-20,h-21,'#fffaf2',25,'#efdcc0',2);
  mascot(c,x+45,y+49,.56);const cx=x+w/2+20;T(c,p.title,cx,y+42,fit(c,p.title,w-130,30,800),p.dark,800);T(c,p.sub,cx,y+h-27,fit(c,p.sub,w-110,13),p.dark);heart(c,x+w-33,y+51,.36,p.primary);}
/** Small "CHUYỆN PHỐ" notice board (the `board` hotspot). */
export function streetBoard(c,p,x,y,s=1){R(c,x,y,65*s,77*s,'#c89f7f',9);R(c,x+6*s,y+6*s,53*s,65*s,'#fff7e7',6);T(c,'CHUYỆN',x+32*s,y+24*s,10*s,p.dark);T(c,'PHỐ',x+32*s,y+40*s,14*s,p.dark);heart(c,x+32*s,y+59*s,.35*s,p.primary);}
/** Door sign showing open/closed; returns nothing. */
export function openSign(c,p,x,y,open,words){R(c,x,y,114,32,'#fff8e8',13,'#c6a182',2);T(c,open?words.open_sign:words.closed_sign,x+57,y+17,12,p.dark);}
