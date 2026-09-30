/** Pet shop scene (pet_shop): "Tiệm Thú Nhỏ Chú Út", the old corner shop that
 * Nhã, a vet student, is turning into a caring one with the Chân Nhỏ rescue.
 * Back wall: sea-glass tiles with a bubble frieze, the shop sign (Chú Út's
 * faded board at first, Nhã's new one once the shop grows), a wall rack of
 * betta cups, the window with the budgie cage swinging in it, the lost-pet
 * cork board, the street notice board, the plaque and the door.
 * Floor: the stock rack of sacks (`warehouse`), the food shelves with the old
 * discount basket (`shelf`), the aquarium stand with swimming fish
 * (`workbench`), the till counter with the scanner and a hamster wheel
 * (`counter`), the ledger desk (`finance`) and, near the entrance, the
 * adoption corner (litter sacks until the corner opens).
 * The look grows with the shop (w.c.data.stage 0–3): stage 1 opens the
 * adoption corner, stage 2 clears the water and adds the quarantine tank and
 * a plant, stage 3 hangs the adoption-day bunting.
 * Colours come from the server (w.c.data): `palette` is the paint the player
 * chose for the shop (wall, tiles, main, accent, sand) plus the sign ink;
 * `coat_colors` are the animals on show today ([main, second] per animal) and
 * `corner_fur` the kittens and puppies waiting in the adoption corner.
 * PLAN schema: see scenes/shop.js (same floor plan as the flower shop). */
import {R,E,L,T,P,fit,heart,streetBoard} from './kit.js';
import flowershop from './flowershop.js';

export const PLAN=flowershop.plan;

/* ------------------------------------------------------------ Palette & helpers */
const BASE={wall:'#dff3ef',wall_d:'#a9d8cf',tile_a:'#e7f7f3',tile_b:'#d6efe9',main:'#2f9e8f',main_d:'#1f6f66',accent:'#f08a6c',accent_l:'#f7b9a3',sand:'#f3e3c4',sand_d:'#d9c29a',ink:''};
let SEA,SEA_D,TILE_A,TILE_B,TEAL,TEAL_D,CORAL,CORAL_L,SAND,SAND_D,INK;
/** Paint the shop in the chosen palette (called at the start of each frame). */
function paint(w){const p={...BASE,...(w?.c?.data?.palette||{})};
  ({wall:SEA,wall_d:SEA_D,tile_a:TILE_A,tile_b:TILE_B,main:TEAL,main_d:TEAL_D,accent:CORAL,accent_l:CORAL_L,sand:SAND,sand_d:SAND_D}=p);INK=p.ink||'';}
paint(null);
const
  WOOD='#dcb58c',WOOD_L='#f0d6b6',WOOD_D='#b48a64',EDGE='#9c7454',CREAM='#fffaf2',SHADOW='#2f6f6622',GLASS='#c9ecf3',GLASS_D='#8cc7d3';
const solid=list=>list.map(x=>[x,x]);
const FALLBACK={betta:solid(['#e5484d','#5b8def','#b56ee8']),goldfish:solid(['#f59a3b','#f7b545','#ef7d2d']),guppy:solid(['#5b8def','#f2c94c','#39b58f']),
  barb:[['#f2b84c','#2a2a30']],hamster:[['#e8b77a','#e8b77a'],['#f0c992','#f0c992']],budgie:[['#7fd36a','#f4e04d'],['#6fb8ef','#ffffff']]};
/** Today's colours of one kind of animal on show: [[main, second], …]. */
const coats=(w,k)=>{const v=w.c?.data?.coat_colors?.[k];return Array.isArray(v)&&v.length?v:FALLBACK[k];};
const dark=h=>parseInt(String(h).slice(1,3),16)<80;
const at=(c,x,y,s,fn)=>{c.save();c.translate(x,y);c.scale(s,s);fn();c.restore();};
const stageOf=w=>Math.max(0,Math.min(3,Number(w.c?.data?.stage)||0));
const tick=w=>w.reduced?0:w.time;

/** A small fish facing its swimming direction, centre (0,0). */
function fish(c,col,s=1,dir=1,col2=col){c.save();c.scale(dir*s,s);P(c,[[-7,0],[-15,-6],[-15,6]],col2);E(c,0,0,9,5,col);if(col2!==col)E(c,2,-1,3.5,2.6,col2);
  E(c,5,-1,1.4,1.4,dark(col)?'#f2f2f2':'#1d2b33');c.restore();}
/** A betta with a long flowing tail. */
function betta(c,col,s=1,t=0,col2=col){c.save();c.scale(s,s);const f=Math.sin(t*3)*3;E(c,0,0,7,4,col);
  c.beginPath();c.moveTo(-5,0);c.bezierCurveTo(-14,-12+f,-24,-6,-22,4);c.bezierCurveTo(-18,12-f,-10,8,-5,0);c.fillStyle=col2;c.globalAlpha=.85;c.fill();c.globalAlpha=1;
  E(c,4,-1,1.2,1.2,'#1d2b33');c.restore();}
/** Rising bubbles inside a box. */
function bubbles(w,x,y,h,n=4,seed=0){const c=w.ctx;for(let i=0;i<n;i++){const k=((tick(w)*.35+i/n+seed)%1);E(c,x+Math.sin(k*9+i)*3,y+h-k*h,2+i%2,2+i%2,'#ffffffb0');}}

/* ------------------------------------------------------------ Walls */
function wall(c,x,y,w,h){R(c,x,y,w,h,SEA,22);c.save();c.beginPath();c.roundRect(x,y,w,h,22);c.clip();
  for(let yy=y;yy<y+h;yy+=30)for(let xx=x;xx<x+w;xx+=30)R(c,xx+2,yy+2,26,26,((xx+yy)/30)%3?TILE_A:TILE_B,5);c.restore();}
function wainscot(c,x,y0,w,y1){R(c,x,y0,w,y1-y0,SAND,0);for(let xx=x+10;xx<x+w-30;xx+=48)R(c,xx,y0+10,38,y1-y0-18,'#f7ebd2',4,SAND_D,1.2);R(c,x,y0-7,w,9,CREAM,2,SAND_D,1);}
/** Bubble frieze along the top of the wall. */
function frieze(c,x0,x1,y){R(c,x0,y,x1-x0,14,SEA_D,3);for(let x=x0+10,i=0;x<x1;x+=22,i++)E(c,x,y+7,3+i%3,3+i%3,i%4?'#ffffffc0':CORAL_L);}
function floor(c,x,y,w,h){c.save();c.beginPath();c.roundRect(x,y,w,h,16);c.clip();R(c,x,y,w,h,'#eadcc2',0);
  for(let r=0,yy=y;yy<y+h;r++,yy+=34)for(let xx=x-(r%2)*34;xx<x+w;xx+=68)R(c,xx+2,yy+2,64,30,(r+xx/68)%2?'#f1e5ce':'#e4d3b5',3);c.restore();}
/** Shop sign: Chú Út's faded board, then Nhã's sea-glass sign with a paw. */
function sign(c,p,x,y,w,h,stage){
  if(stage===0){R(c,x-4,y+8,w+8,h,'#9d8a74',16);R(c,x,y,w,h,'#eee3cf',14,'#c3ad8c',3);T(c,'TIỆM CÁ CẢNH CHÚ ÚT',x+w/2,y+h*.42,fit(c,'TIỆM CÁ CẢNH CHÚ ÚT',w-60,28,800),INK||'#8a765f',800);
    T(c,'CÁ · CHIM · THỨC ĂN',x+w/2,y+h*.76,fit(c,'CÁ · CHIM · THỨC ĂN',w-80,13),'#a38f76');L(c,x+w-80,y+16,x+w-40,y+26,'#d6c8b2',2);return;}
  R(c,x-4,y+8,w+8,h,TEAL_D,30);R(c,x,y,w,h,CREAM,28,TEAL,3);R(c,x+9,y+9,w-18,h-18,'#f6fdfb',22,SEA_D,1.5);
  at(c,x+56,y+h/2,1,()=>{E(c,0,6,15,13,CORAL);E(c,-15,-10,6,7,CORAL);E(c,-5,-17,6,7,CORAL);E(c,7,-17,6,7,CORAL);E(c,16,-9,6,7,CORAL);});
  const cx=x+w/2+26;T(c,p.title,cx,y+h*.42,fit(c,p.title,w-160,30,800),INK||TEAL_D,800);T(c,p.sub,cx,y+h-25,fit(c,p.sub,w-140,13),TEAL);}
/** Rack of little betta cups on the wall, each with its own colour. */
function bettaWall(w,x,y,ww,h){const c=w.ctx,t=tick(w),bc=coats(w,'betta');R(c,x-6,y-6,ww+12,h+12,WOOD_D,10);R(c,x,y,ww,h,'#f6efe2',6);
  const rows=3,cols=3,cw=ww/cols,rh=h/rows;
  for(let r=0;r<rows;r++){R(c,x+4,y+(r+1)*rh-8,ww-8,6,WOOD,2,EDGE,1);
    for(let k=0;k<cols;k++){const cx=x+k*cw+cw/2,cy=y+r*rh+rh/2;R(c,cx-cw*.32,cy-rh*.34,cw*.64,rh*.6,GLASS,5,GLASS_D,1.2);
      const [b1,b2]=bc[(r*3+k)%bc.length];at(c,cx+Math.sin(t*.8+r+k)*cw*.12,cy-rh*.05,1,()=>betta(c,b1,Math.min(1.1,cw/40),t+r+k,b2));}}
  R(c,x+ww*.18,y-18,ww*.64,16,CREAM,4,TEAL,1);T(c,'CÁ BETTA',x+ww/2,y-10,fit(c,'CÁ BETTA',ww*.6,10,800),TEAL_D,800);}
/** Window with the budgie cage swinging inside. */
function windowCage(w,x,y,ww,h){const c=w.ctx,t=tick(w);R(c,x-10,y-10,ww+20,h+14,WOOD_D,[14,14,6,6]);
  c.save();c.beginPath();c.roundRect(x,y,ww,h,[10,10,4,4]);c.clip();const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#d7eef7');g.addColorStop(1,'#f4fbf8');c.fillStyle=g;c.fillRect(x,y,ww,h);
  E(c,x+ww*.82,y+h*.2,15,15,'#fff3c9');for(let i=0;i<3;i++)E(c,x+ww*(.12+i*.3),y+h*.9,ww*.16,h*.12,'#bfe1c8');c.restore();
  const sw=Math.sin(t*1.2)*.05,cx=x+ww/2,top=y+8;L(c,cx,y-4,cx,top+10,'#8f969b',2);
  c.save();c.translate(cx,top+10);c.rotate(sw);const cw=Math.min(ww*.5,110),ch=h*.62;
  c.beginPath();c.moveTo(-cw/2,ch*.3);c.quadraticCurveTo(0,-ch*.12,cw/2,ch*.3);c.lineTo(cw/2,ch);c.lineTo(-cw/2,ch);c.closePath();c.fillStyle='#ffffff38';c.fill();
  for(let i=0;i<=8;i++){const bx=-cw/2+i*cw/8;L(c,bx,ch*.3-(1-Math.abs(i-4)/4)*ch*.2,bx,ch,'#b7a27c',1.4);}
  R(c,-cw/2-4,ch-4,cw+8,8,WOOD_D,3);L(c,-cw*.35,ch*.66,cw*.35,ch*.66,WOOD_D,2.5);
  const hop=w.reduced?0:Math.abs(Math.sin(t*2))*4;
  const bb=coats(w,'budgie'),b0=bb[0],b1=bb[1]||bb[0];
  [[b0[0],b0[1],-cw*.18],[b1[0],b1[1],cw*.16]].forEach(([body,head,bx],i)=>{const hy=ch*.66-(i?hop:0);
    E(c,bx,hy-11,7,10,body);E(c,bx+(i?-2:2),hy-21,5,5,head);P(c,[[bx+(i?-6:6),hy-21],[bx+(i?-10:10),hy-19],[bx+(i?-6:6),hy-17]],'#f09a3e');L(c,bx,hy-2,bx+(i?4:-4),hy+10,body,3);});
  c.restore();R(c,x-14,y+h,ww+28,12,WOOD,5);}
/** The cork board where lost-pet notices go up. */
function lostBoard(c,x,y,ww,h){R(c,x-4,y-4,ww+8,h+8,WOOD_D,8);R(c,x,y,ww,h,'#d9b27f',5);for(let i=0;i<40;i++)E(c,x+((i*37)%ww),y+((i*23)%h),1.2,1.2,'#b88f5d');
  R(c,x+6,y+5,ww-12,16,CREAM,3);T(c,'TÌM THÚ LẠC',x+ww/2,y+13,fit(c,'TÌM THÚ LẠC',ww-18,10,800),CORAL,800);
  const n=[[.08,.3,-.06,'#fffdf5'],[.52,.34,.05,'#fff4e8'],[.28,.62,.03,'#f7fbff']];
  for(const [fx,fy,a,col] of n){c.save();c.translate(x+fx*ww+ww*.2,y+fy*h+h*.15);c.rotate(a);R(c,-ww*.2,-h*.15,ww*.4,h*.3,col,2,'#e0d3bf',1);E(c,0,-h*.15+3,2.5,2.5,CORAL);
    E(c,0,-2,ww*.07,ww*.06,'#8f8f96');for(let i=0;i<3;i++)L(c,-ww*.13,h*.06+i*4,ww*.13,h*.06+i*4,'#c7bba8',1);c.restore();}}
function door(c,x,y,ww,h,size,open,words){R(c,x-8,y-8,ww+16,h+8,WOOD_D,[12,12,0,0]);R(c,x,y,ww,h,SEA_D,[8,8,0,0],TEAL,2);
  R(c,x+ww*.16,y+h*.08,ww*.68,h*.42,open?'#eef9fb':'#d8e8ec',6,TEAL,2);L(c,x+ww*.2,y+h*.32,x+ww*.44,y+h*.12,'#ffffffb0',3);
  at(c,x+ww*.5,y+h*.72,.7,()=>{E(c,0,6,11,9,TEAL_D);E(c,-11,-7,4,5,TEAL_D);E(c,-4,-12,4,5,TEAL_D);E(c,4,-12,4,5,TEAL_D);E(c,11,-7,4,5,TEAL_D);});
  E(c,x+ww-12,y+h*.56,4,4,CORAL);if(open)P(c,[[x+ww-3,y],[x+ww+10,y-4],[x+ww+10,y+h],[x+ww-3,y+h]],'#86c3b7');
  const s=open?words.open_sign:words.closed_sign,sw=ww+14,sy=y+h*.46;R(c,x+ww/2-sw/2,sy,sw,size*1.9,CREAM,9,open?'#7fbf8a':'#d59a9a',2);
  T(c,s,x+ww/2,sy+size*.97,fit(c,s,sw-10,size,800),open?TEAL_D:'#a35f63',800);}
function plaque(c,x,y,ww,h){R(c,x,y,ww,h,WOOD_D,7);R(c,x+4,y+4,ww-8,h-8,CREAM,5);at(c,x+ww/2,y+h/2,ww/64,()=>fish(c,CORAL,1.6));}
function security(c,items,[cx,cy],[bx,by],[lx,ly]){
  if(items.includes('camera')){L(c,cx-18,cy+12,cx-4,cy+3,'#8aa3a0',4);R(c,cx-12,cy-10,38,20,'#f2f8f7',7,'#9fb3b0',2);E(c,cx+21,cy,7,8,'#5f7f7b');E(c,cx+22,cy,3,4,'#b4d9df');}
  if(items.includes('bell')){L(c,bx,by-14,bx,by-4,'#ac8f73',2);P(c,[[bx-10,by+12],[bx+10,by+12],[bx+7,by-3],[bx-7,by-3]],'#f3d27a');E(c,bx,by+14,4,3,'#d9a521');}
  if(items.includes('light')){const g=c.createRadialGradient(lx,ly+18,0,lx,ly+18,80);g.addColorStop(0,'#ffe1a44a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(lx-80,ly-62,160,160);R(c,lx-12,ly-6,24,22,'#fff0b8',[4,4,9,9],'#b69b79',2);}}
/** Adoption-day bunting (stage 3). */
function bunting(c,x0,x1,y){c.strokeStyle='#8a7a6e';c.lineWidth=1.2;c.beginPath();c.moveTo(x0,y);c.quadraticCurveTo((x0+x1)/2,y+26,x1,y);c.stroke();
  const n=Math.floor((x1-x0)/34);for(let i=1;i<n;i++){const k=i/n,x=x0+(x1-x0)*k,yy=y+26*4*k*(1-k)*.5;P(c,[[x-9,yy],[x+9,yy],[x,yy+16]],[CORAL,TEAL,'#f2c94c',CORAL_L][i%4]);}}

/* ------------------------------------------------------------ Floor pieces */
/** Stock rack of sacks and boxes: the `warehouse`. */
function stockRack(c,W,H,ts){E(c,0,2,W/2+8,7,SHADOW);R(c,-W/2,-H,W,H,WOOD_L,8,EDGE,2);R(c,-W/2+6,-H+6,W-12,ts*1.8,CREAM,5);T(c,'KHO',0,-H+6+ts*.9,fit(c,'KHO',W-20,ts,800),TEAL_D,800);
  const rows=3,top=-H+ts*1.8+12,rh=(H-ts*1.8-20)/rows;
  for(let r=0;r<rows;r++){const y=top+(r+1)*rh;R(c,-W/2+4,y-5,W-8,6,WOOD_D,2);
    for(let k=0;k<2;k++){const x=-W/2+10+k*(W-20)/2,sw=(W-20)/2-8;P(c,[[x,y-6],[x+sw,y-6],[x+sw-4,y-rh+14],[x+4,y-rh+14]],r===2?'#e9e2d6':[SAND,CORAL_L,SEA_D][(r+k)%3]);
      R(c,x+sw*.2,y-rh*.62,sw*.6,rh*.24,CREAM,3);}}}
/** Food shelves: kibble bags, cans, and Chú Út's discount basket until the shop changes. */
function foodShelf(c,W,stage){const hw=W/2;E(c,0,2,hw+8,7,SHADOW);R(c,-hw,-170,W,170,WOOD_L,8,EDGE,2);
  R(c,-hw+10,-164,W-20,18,CREAM,4);T(c,'HẠT · PATE · CÁT',0,-155,fit(c,'HẠT · PATE · CÁT',W-30,11,800),TEAL_D,800);
  const bag=['#f59a3b','#5b8def','#e5484d','#39b58f','#b56ee8','#f2c94c'];
  for(let r=0;r<3;r++){const y=-140+r*46;R(c,-hw+4,y+38,W-8,6,WOOD_D,2);
    const n=r===2?8:5;for(let i=0;i<n;i++){const x=-hw+12+i*(W-24)/n,bw=(W-24)/n-6;
      if(r===2){R(c,x,y+18,bw,20,'#d9dde0',4,'#9aa3a8',1);R(c,x,y+24,bw,7,bag[i%6],1);}
      else{P(c,[[x,y+38],[x+bw,y+38],[x+bw-2,y+4],[x+2,y+4]],bag[(i+r*2)%6]);R(c,x+bw*.18,y+14,bw*.64,12,CREAM,3);E(c,x+bw/2,y+20,3,3,bag[(i+r*2+3)%6]);}}}
  if(stage>=1){R(c,hw-58,-186,52,18,CREAM,4,TEAL,1);T(c,'HSD RÕ',hw-32,-177,9,TEAL_D,800);}
  if(stage===0){at(c,-hw+34,0,1,()=>{E(c,0,2,34,5,SHADOW);P(c,[[-30,-28],[30,-28],[24,0],[-24,0]],'#caa472');for(let i=-24;i<24;i+=8)L(c,i,-26,i+2,-2,'#a9844f',1.5);
    for(let i=0;i<4;i++)R(c,-20+i*10,-38,9,12,'#d9dde0',2,'#9aa3a8',1);R(c,-26,-56,52,16,'#ffe07a',3,'#c9a227',1);T(c,'GIẢM GIÁ',0,-48,9,'#8a5b00',800);});}}
/** One aquarium: glass, gravel, plants, fish; murky before the shop clears the water. */
function tank(w,x,y,tw,th,kind,clear,seed){const c=w.ctx,t=tick(w);R(c,x-3,y-3,tw+6,th+6,'#51656b',5);
  const water=kind==='gold'?(clear?'#cfeef6':'#d6e6c4'):(clear?'#a9e3ee':'#bcd9b8');R(c,x,y,tw,th,water,3);R(c,x,y,tw,6,'#ffffff55',2);
  R(c,x,y+th-9,tw,9,'#d7c19a',2);for(let i=0;i<tw;i+=7)E(c,x+i+3,y+th-5,2.4,2,i%14?'#bda27a':'#e9d6b0');
  for(let i=0;i<2;i++){const px=x+tw*(.18+i*.62);for(let k=0;k<3;k++)E(c,px+Math.sin(t+k+i)*2,y+th-14-k*9,3,7,'#56a86f');}
  const cols=kind==='gold'?coats(w,'goldfish'):kind==='sick'?[['#e5484d','#e5484d']]:[...coats(w,'guppy').slice(0,3),...coats(w,'barb').slice(0,2)];
  const n=kind==='sick'?1:kind==='gold'?3:5;
  for(let i=0;i<n;i++){const ph=t*(.35+i*.07)+seed+i*1.7,dir=Math.cos(ph)>0?1:-1;const fx=x+tw/2+Math.sin(ph)*(tw/2-14),fy=y+th*(.3+.12*(i%4))+Math.sin(ph*2)*3;
    const [f1,f2]=cols[i%cols.length];at(c,fx,fy,1,()=>fish(c,f1,kind==='gold'?1.1:.8,dir,f2));}
  bubbles(w,x+tw-10,y+8,th-20,3,seed);if(!clear)for(let i=0;i<5;i++)E(c,x+((i*29+seed*13)%tw),y+th*.25+((i*17)%(th*.5)),2,2,'#7a9a6a55');}
/** Aquarium stand: the `workbench`. */
function aquarium(w,p,W,ts,stage){const c=w.ctx,hw=W/2,top=-124;E(c,0,3,hw+14,8,SHADOW);
  R(c,-hw,top+64,W,-top-64,WOOD,6,EDGE,1.5);for(let x=-hw+W/3;x<hw-4;x+=W/3)L(c,x,top+70,x,-6,EDGE,1.5);
  const lab=w.game?.catalogue?.find(x=>x.id===w.career)?.station||'Dãy bể';const lw=Math.min(W*.46,ts*9);
  R(c,-lw/2,top+72,lw,16,CREAM,4,TEAL,1);T(c,lab,0,top+80.5,fit(c,lab,lw-12,ts,800),TEAL_D,800);
  const clear=stage>=2,gap=8,n=stage>=2?3:2,tw=(W-gap*(n+1))/n;
  tank(w,-hw+gap,top,tw*(n===2?1:1),58,'trop',clear,1);tank(w,-hw+gap*2+tw,top,tw,58,'gold',clear,3);
  if(n===3){tank(w,-hw+gap*3+tw*2,top+14,tw,44,'sick',true,5);R(c,-hw+gap*3+tw*2+tw*.1,top+2,tw*.8,12,CORAL,3);T(c,'CÁCH LY',-hw+gap*3+tw*2.5,top+8,fit(c,'CÁCH LY',tw*.75,9,800),CREAM,800);}
  R(c,-hw-4,top+58,W+8,8,'#51656b',3);}
/** Till counter with the scanner and the hamster cage: the `counter`. */
function counter(w,p,W,big){const c=w.ctx,t=tick(w),hw=W/2,top=-94;E(c,0,3,hw+12,8,SHADOW);
  R(c,-hw,top+12,W,-top-12,SEA_D,8,TEAL,2);for(let i=0;i<5;i++)E(c,-hw+20+i*(W-40)/4,top+50+(i%2)*10,6,6,'#ffffff70');R(c,-hw,-12,W,12,TEAL,[0,0,8,8]);
  R(c,-hw-6,top,W+12,14,WOOD_L,6,EDGE,1.5);
  // Hamster cage with a turning wheel.
  const hx=-hw+(big?40:36);R(c,hx-28,top-44,56,44,'#fffdf6',6,'#b7a27c',1.5);for(let i=0;i<7;i++)L(c,hx-24+i*8,top-42,hx-24+i*8,top-2,'#c9b894',1);
  R(c,hx-26,top-8,52,7,'#e9d6a8',2);c.beginPath();c.arc(hx+10,top-22,12,0,Math.PI*2);c.strokeStyle=CORAL;c.lineWidth=2.5;c.stroke();
  for(let i=0;i<4;i++){const a=i*Math.PI/4+t*2.5;L(c,hx+10+Math.cos(a)*12,top-22+Math.sin(a)*12,hx+10-Math.cos(a)*12,top-22-Math.sin(a)*12,CORAL_L,1);}
  const hm=coats(w,'hamster'),[h1,h1b]=hm[0],[h2,h2b]=hm[1]||hm[0];
  E(c,hx+10,top-14,6,5,h1);E(c,hx+14,top-17,3,3,h1);if(h1b!==h1)E(c,hx+8,top-15,2.5,2,h1b);E(c,hx+15,top-18,.9,.9,'#3b2a20');
  E(c,hx-12,top-10,7,5,h2);if(h2b!==h2)E(c,hx-14,top-11,3,2.4,h2b);
  // Scanner and till.
  const rx=hw-(big?34:38);R(c,rx-24,top-30,48,30,'#e3f3f0',7,TEAL_D,1.5);R(c,rx-18,top-42,26,12,CREAM,3,SEA_D,1);
  for(let i=0;i<4;i++)for(let j=0;j<2;j++)E(c,rx-14+i*8,top-22+j*7,2.4,2.4,j?CREAM:TEAL);R(c,rx-22,top-6,44,5,SEA_D,2);
  const sx=(hx+rx)/2;P(c,[[sx-6,top],[sx+6,top],[sx+10,top-22],[sx-2,top-26]],'#46545a');if(!w.reduced&&Math.floor(t*1.5)%3===0)L(c,sx+10,top-22,sx+24,top-4,'#ff5a5a',1.5);}
function ledgerDesk(w,ts){const c=w.ctx,words=w.words();E(c,0,2,44,6,SHADOW);R(c,-38,-44,6,44,EDGE,2);R(c,32,-44,6,44,EDGE,2);
  R(c,-40,-44,80,32,WOOD,7,EDGE,1.5);R(c,-33,-38,66,20,CREAM,4);T(c,words.ledger,0,-28,fit(c,words.ledger,60,ts,800),TEAL_D,800);
  R(c,-46,-54,92,12,WOOD_L,5,EDGE,1.5);P(c,[[-26,-55],[-2,-52],[-2,-64],[-24,-67]],CREAM);P(c,[[22,-55],[-2,-52],[-2,-64],[20,-67]],'#fffdf5');L(c,-18,-60,-6,-58,TEAL,1.5);}
/** The adoption corner (stage 1+): a low pen with kittens and a puppy, or litter sacks before it opens. */
function corner(w,c,stage){const t=tick(w),fur=w.c?.data?.corner_fur;
  const pick=(kind,def)=>{if(!Array.isArray(fur))return def;const f=fur.find(v=>v[0]===kind);return f?[f[1],f[2]]:null;};
  const cat=pick('cat',['#f2f2ee','#f2f2ee']),dog=pick('dog',['#e8b36a','#e8b36a']);
  if(stage<1){E(c,0,2,40,6,SHADOW);for(let i=0;i<3;i++)R(c,-34+i*4,-14-i*14,64,14,['#f3e3c4','#e9d0a0','#f7ebd2'][i],5,'#c9b089',1);T(c,'CÁT',0,-26,9,'#8a6a3e',800);return;}
  E(c,0,2,54,7,SHADOW);R(c,-50,-30,100,30,'#fff3e6',6,CORAL,2);for(let i=-44;i<48;i+=10)L(c,i,-28,i,-2,CORAL_L,1.5);
  R(c,-46,-6,92,6,'#f7c9b8',2);
  const bob=w.reduced?0:Math.sin(t*2)*2;
  // kitten: a second colour gives tabby stripes or calico patches
  if(cat){const [k1,k2]=cat;
    E(c,-22,-14-bob,10,8,k1);E(c,-14,-22-bob,7,6,k1);P(c,[[-19,-26-bob],[-17,-33-bob],[-14,-27-bob]],k1);P(c,[[-12,-27-bob],[-9,-33-bob],[-8,-25-bob]],k1);
    if(k2!==k1){E(c,-25,-16-bob,4,4,k2);E(c,-17,-12-bob,3,3,k2);E(c,-15,-25-bob,2.5,2,k2);}E(c,-12,-22-bob,1.2,1.2,dark(k1)?'#f2c94c':'#333');}
  // puppy
  if(dog){const [d1,d2]=dog,ear=d2!==d1?d2:dark(d1)?'#1c1a1d':'#c98c45';
    E(c,18,-14,12,8,d1);if(d2!==d1){E(c,14,-15,4,3,d2);E(c,22,-11,3,2.5,d2);}E(c,28,-22,7,7,d1);E(c,24,-22,3,6,ear);E(c,30,-22,1.2,1.2,dark(d1)?'#f2c94c':'#333');L(c,6,-16,0,-22+bob,d1,3);}
  R(c,-30,-58,60,20,CREAM,4,TEAL,1.5);T(c,'NHẬN NUÔI',0,-48,fit(c,'NHẬN NUÔI',54,10,800),TEAL_D,800);L(c,0,-38,0,-30,WOOD_D,2);heart(c,22,-54,.22,CORAL);}
function plant(c){E(c,0,2,20,5,SHADOW);for(const [x,y,a] of [[-12,-50,-2.4],[12,-54,-.7],[0,-62,-1.6],[-16,-34,-2.8],[16,-38,-.3]]){c.save();c.translate(x,y);c.rotate(a);E(c,10,0,12,5,'#6fb389');c.restore();}
  P(c,[[-15,-26],[15,-26],[11,0],[-11,0]],CORAL_L);R(c,-17,-29,34,6,CORAL,2);}

/* ------------------------------------------------------------ Rooms */
function landRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words(),stage=stageOf(w);
  E(c,605,724,503,30,'#2f6f6622');R(c,85,165,1030,550,WOOD_D,35);R(c,96,168,1008,533,CREAM,30,WOOD,3);
  wall(c,108,179,984,270);wainscot(c,108,380,984,446);floor(c,108,445,984,244);R(c,108,440,984,9,WOOD,3);
  frieze(c,120,1080,186);
  sign(c,p,360,56,480,102,stage);
  if(stage>=3)bunting(c,130,1070,208);
  bettaWall(w,250,246,116,150);
  windowCage(w,500,214,240,178);
  lostBoard(c,772,262,96,112);
  streetBoard(c,p,888,258);
  plaque(c,1003,212,44,40);
  door(c,980,262,90,183,12,open,words);
  security(c,items,[170,222],[962,266],[262,302]);}
function portRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words(),stage=stageOf(w);
  E(c,350,857,324,23,'#2f6f6622');R(c,22,114,656,738,WOOD_D,31);R(c,29,117,642,724,CREAM,26,WOOD,3);
  wall(c,40,139,620,372);wainscot(c,40,440,620,506);floor(c,40,506,620,323);R(c,40,500,620,9,WOOD,3);
  frieze(c,50,650,146);
  sign(c,p,125,30,450,100,stage);
  if(stage>=3)bunting(c,50,650,168);
  lostBoard(c,54,272,100,90);
  bettaWall(w,190,268,112,150);
  windowCage(w,356,200,174,190);
  streetBoard(c,p,547,194,.86);
  plaque(c,610,206,40,40);
  door(c,550,300,94,206,15,open,words);
  security(c,items,[86,240],[536,212],[443,176]);}

/* ------------------------------------------------------------ Floor props */
function landProps(w,p){const c=w.ctx,stage=stageOf(w),out=[];
  out.push([502,()=>at(c,196,500,1,()=>stockRack(c,112,212,14))]);
  out.push([502,()=>at(c,375,500,1,()=>foodShelf(c,206,stage))]);
  out.push([594,()=>at(c,570,594,1,()=>aquarium(w,p,300,13,stage))]);
  out.push([594,()=>at(c,890,594,1,()=>counter(w,p,180,false))]);
  out.push([628,()=>at(c,195,628,1,()=>corner(w,c,stage))]);
  out.push([656,()=>at(c,1028,656,1,()=>ledgerDesk(w,12))]);
  if(stage>=2)out.push([680,()=>at(c,126,678,1,()=>plant(c))]);
  return out;}
function portProps(w,p){const c=w.ctx,stage=stageOf(w),out=[];
  out.push([598,()=>at(c,98,598,1,()=>stockRack(c,104,226,16))]);
  out.push([566,()=>at(c,253,566,.85,()=>foodShelf(c,206,stage))]);
  out.push([700,()=>at(c,260,700,1,()=>aquarium(w,p,284,16,stage))]);
  out.push([700,()=>at(c,525,700,1,()=>counter(w,p,170,true))]);
  out.push([818,()=>at(c,600,818,1,()=>ledgerDesk(w,16))]);
  out.push([818,()=>at(c,130,818,.9,()=>corner(w,c,stage))]);
  return out;}

export default {
  id:'petshop',
  plan:PLAN,
  room(w,p){paint(w);if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){paint(w);return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
