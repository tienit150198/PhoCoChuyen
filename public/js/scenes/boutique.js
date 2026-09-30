/** Clothes shop scene (clothing): "Tiệm Áo Chỉ Mây", Bà Tư's old tailoring shop
 * that her daughter Vy reopened as a small modern clothes shop.
 * Back wall: lilac paint over white wainscot, a tape-measure frieze, the shop
 * sign (the faded "MAY ĐO" board at first, the new sign once the shop grows),
 * the display window with a mannequin dressed from the shop's display, the
 * fitting-room booth with its curtain, a tall mirror, the street notice board,
 * the door with the open / closed sign (`door`) and the plaque (`property`).
 * Floor: folded-stock cubbies (`warehouse`), the garment rail with coloured
 * hangers (`shelf`), Bà Tư's cutting table with the old sewing machine and a
 * steamer (`workbench`), the counter with receipts (`evidence`) and the till
 * (`counter`), the ledger desk (`finance`), a floor mannequin by the entrance.
 * The look grows with the shop (w.c.data.look 0–3): new sign, mannequin,
 * velvet curtain, fairy lights and plants.
 * PLAN schema: see scenes/shop.js. Floor pieces use local units with the
 * origin at the middle of their feet line, placed with `at(x, y, scale)`. */
import {R,E,L,T,P,fit,streetBoard} from './kit.js';
import flowershop from './flowershop.js';

// Same floor plan and hotspots as the flower shop (the furniture sits in the same places).
export const PLAN=flowershop.plan;

/* ------------------------------------------------------------ Palette & helpers */
const LILAC='#ece6f7',LILAC_D='#c9bde6',VIOLET='#6a58a6',VIOLET_D='#4d3f82',MUSTARD='#d9a521',MUSTARD_L='#f0cf6e',
  WOOD='#d9b48e',WOOD_L='#efd6b8',WOOD_D='#b28a66',EDGE='#9c7656',CREAM='#fffaf3',PANEL='#fbf8ff',PANEL_D='#e2dbef',SHADOW='#4a3f6a22';
const SW={'trắng':'#f7f5ef','đen':'#2d2a2e','xanh than':'#2f3f63','be':'#dcc7a4','xanh nhạt':'#a9c9e8','hồng phấn':'#f2c1cf','xanh đậm':'#2f4f86',
  'hoa nhí':'#f3d4dc','đỏ đô':'#8e2437','xanh mint':'#a6dcc8','đỏ':'#d23b3b','vàng':'#f0c23b','xanh ngọc':'#3aa6a0','hồng':'#f4a7bb','xanh':'#6fa3d6','caro':'#c9a27e','cói':'#d9bb7c','nâu':'#8a5a3b','sọc':'#9aa3b5'};
const HANG=['#f2c1cf','#a9c9e8','#f7f5ef','#2f3f63','#a6dcc8','#8e2437','#dcc7a4','#6fa3d6','#f0c23b','#3aa6a0'];
const at=(c,x,y,s,fn)=>{c.save();c.translate(x,y);c.scale(s,s);fn();c.restore();};
const look=w=>Math.max(0,Math.min(3,Number(w.c?.data?.look)||0));
/** The pieces the shop last dressed its mannequin in (or a default outfit). */
function outfit(w){const d=w.c?.data?.display;const ps=(d&&Array.isArray(d.pieces)&&d.pieces.length)?d.pieces:[{item:'dress',colour:'hoa nhí'},{item:'hat',colour:'cói'}];
  const col=it=>SW[(ps.find(p=>p.item===it)||{}).colour];return {dress:col('dress')||col('aodai'),aodai:!!ps.find(p=>p.item==='aodai'),top:col('shirt')||col('tee'),bottom:col('jeans'),hat:col('hat'),belt:col('belt')};}

/* ------------------------------------------------------------ Garments */
/** A shirt on a hanger, hook at (0,0). */
function shirt(c,col,s=1){at(c,0,0,s,()=>{L(c,0,0,0,6,'#9aa3b5',1.5);L(c,-12,12,0,6,'#9aa3b5',1.5);L(c,0,6,12,12,'#9aa3b5',1.5);
  P(c,[[-13,11],[-4,8],[0,12],[4,8],[13,11],[18,20],[12,22],[11,44],[-11,44],[-12,22],[-18,20]],col);L(c,0,12,0,44,'#00000018',1);P(c,[[-4,8],[0,15],[4,8]],'#ffffff70');});}
/** A dress on a hanger. */
function dress(c,col,s=1){at(c,0,0,s,()=>{L(c,0,0,0,6,'#9aa3b5',1.5);L(c,-9,11,0,6,'#9aa3b5',1.5);L(c,0,6,9,11,'#9aa3b5',1.5);
  P(c,[[-8,10],[8,10],[7,24],[18,56],[-18,56],[-7,24]],col);R(c,-8,22,16,3,'#00000020',1);});}
/** Jeans folded over a hanger bar. */
function jeans(c,col,s=1){at(c,0,0,s,()=>{L(c,0,0,0,6,'#9aa3b5',1.5);L(c,-11,8,11,8,'#9aa3b5',2);P(c,[[-11,8],[11,8],[12,40],[2,40],[0,20],[-2,40],[-12,40]],col);L(c,-9,12,9,12,'#ffffff40',1);});}

/** A dressor's mannequin at (0,0) = feet. */
function mannequin(c,o,s=1){at(c,0,0,s,()=>{E(c,0,2,16,4,SHADOW);L(c,0,0,0,-24,'#8a7a5e',3);E(c,0,0,12,3,'#8a7a5e');
  E(c,0,-112,9,10,'#efe3cf');R(c,-3,-104,6,8,'#efe3cf',2);
  if(o.dress){P(c,[[-13,-96],[13,-96],[11,-70],[24,-26],[-24,-26],[-11,-70]],o.dress);if(o.aodai){L(c,0,-70,0,-26,'#ffffff55',1.5);P(c,[[-13,-96],[-20,-66],[-15,-64]],o.dress);P(c,[[13,-96],[20,-66],[15,-64]],o.dress);}R(c,-12,-72,24,3,'#00000022',1);}
  else{P(c,[[-15,-96],[15,-96],[19,-70],[13,-66],[12,-54],[-12,-54],[-13,-66],[-19,-70]],o.top||'#f7f5ef');P(c,[[-12,-54],[12,-54],[11,-24],[2,-24],[0,-44],[-2,-24],[-11,-24]],o.bottom||'#2f4f86');if(o.belt)R(c,-12,-57,24,4,o.belt,1);}
  if(o.hat){E(c,0,-117,19,4,o.hat);E(c,0,-121,9,6,o.hat);R(c,-9,-119,18,2,VIOLET,1);}});}

/* ------------------------------------------------------------ Walls */
function wall(c,p,x,y,w,h){R(c,x,y,w,h,LILAC,22);c.save();c.beginPath();c.roundRect(x,y,w,h,22);c.clip();
  for(let xx=x+10;xx<x+w;xx+=36)for(let yy=y+14;yy<y+h;yy+=36){E(c,xx+(Math.round((yy-y)/36)%2?18:0),yy,2.2,2.2,'#d9cff0');}c.restore();}
/** White panelled wainscot from y0 to y1. */
function wainscot(c,x,y0,w,y1){R(c,x,y0,w,y1-y0,PANEL,0);for(let xx=x+12;xx<x+w-40;xx+=70)R(c,xx,y0+10,56,y1-y0-18,PANEL,4,PANEL_D,1.5);
  R(c,x,y0-7,w,9,'#fff',2,PANEL_D,1);}
/** Tape-measure frieze along the top of the wall. */
function tape(c,x0,x1,y){R(c,x0,y,x1-x0,12,MUSTARD_L,2);for(let x=x0+4,i=0;x<x1;x+=8,i++)L(c,x,y+1,x,y+(i%5?5:9),'#6b4f12',1);
  for(let x=x0+44,i=1;x<x1-20;x+=80,i++)T(c,String(i*10),x,y+8,7,'#6b4f12',700);}
/** Herringbone wooden floor. */
function floor(c,x,y,w,h){c.save();c.beginPath();c.roundRect(x,y,w,h,16);c.clip();R(c,x,y,w,h,'#e3c7a6',0);
  const u=26;for(let r=0,yy=y-u;yy<y+h+u;r++,yy+=u/2)for(let i=0,xx=x-u*2+(r%2)*u;xx<x+w+u;i++,xx+=u*2){
    P(c,[[xx,yy],[xx+u,yy+u/2],[xx+u,yy+u/2+8],[xx,yy+8]],(r+i)%3?'#ecd3b4':'#e6c9a7');P(c,[[xx+u,yy+u/2],[xx+u*2,yy],[xx+u*2,yy+8],[xx+u,yy+u/2+8]],(r+i)%3?'#e3c4a0':'#efd9bd');}
  c.restore();}
/** The shop sign: the old faded "MAY ĐO" board, then the new one. */
function sign(c,p,x,y,w,h,stage){
  if(stage===0){R(c,x-4,y+8,w+8,h,'#a88f78',16);R(c,x,y,w,h,'#efe4d2',14,'#c8b294',3);T(c,'TIỆM MAY BÀ TƯ',x+w/2,y+h*.4,fit(c,'TIỆM MAY BÀ TƯ',w-60,30,800),'#8f7a66',800);
    T(c,'MAY ĐO · SỬA ĐỒ',x+w/2,y+h*.75,fit(c,'MAY ĐO · SỬA ĐỒ',w-80,13),'#a8937c');L(c,x+30,y+18,x+70,y+26,'#d9ccb8',2);return;}
  R(c,x-4,y+8,w+8,h,VIOLET_D,30);R(c,x,y,w,h,CREAM,28,VIOLET,3);R(c,x+9,y+9,w-18,h-18,'#fdfbff',22,LILAC_D,1.5);
  // A spool of thread with the needle: the shop mark.
  at(c,x+54,y+h/2,1,()=>{R(c,-16,-22,32,6,WOOD_D,2);R(c,-16,16,32,6,WOOD_D,2);R(c,-12,-16,24,32,VIOLET,3);for(let i=-12;i<16;i+=5)L(c,-12,i,12,i+3,'#ffffff40',1.2);
    L(c,14,-26,26,10,'#8a8f99',2);c.beginPath();c.moveTo(12,0);c.bezierCurveTo(30,4,20,26,34,30);c.strokeStyle=MUSTARD;c.lineWidth=1.5;c.stroke();});
  const cx=x+w/2+26;T(c,p.title,cx,y+h*.42,fit(c,p.title,w-160,30,800),VIOLET_D,800);T(c,p.sub,cx,y+h-25,fit(c,p.sub,w-140,13),VIOLET);
  if(stage>=3)for(let i=0;i<9;i++){const bx=x+20+i*(w-40)/8;E(c,bx,y-4+(i%2)*4,4,4,i%3?MUSTARD_L:'#f2c1cf');}}
/** Display window with the dressed mannequin. */
function windowBox(w,p,x,y,ww,h){const c=w.ctx,stage=look(w);R(c,x-10,y-10,ww+20,h+14,WOOD_D,[14,14,6,6]);
  c.save();c.beginPath();c.roundRect(x,y,ww,h,[10,10,4,4]);c.clip();const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#dfe9f5');g.addColorStop(1,'#f7f1fb');c.fillStyle=g;c.fillRect(x,y,ww,h);
  E(c,x+ww*.8,y+h*.22,16,16,'#fff4cf');R(c,x,y+h*.8,ww,h*.2,'#efe6f5',0);const drift=w.reduced?0:(w.time*6)%(ww+60);
  E(c,x+((ww*.3+drift)%(ww+60))-30,y+h*.25,18,6,'#ffffffc0');
  if(stage>=1)at(c,x+ww*.5,y+h*.95,.95*h/170,()=>mannequin(c,outfit(w)));
  else{for(let i=0;i<3;i++)R(c,x+ww*.2+i*ww*.22,y+h*.62-i*6,ww*.18,h*.3+i*6,['#d9cbb4','#c9b8e0','#e7c1cc'][i],3);}
  c.restore();L(c,x+ww/2,y+2,x+ww/2,y+h*.25,'#fffaf0',3);R(c,x-14,y+h,ww+28,12,WOOD,5);
  if(stage>=3)for(let i=0;i<8;i++)E(c,x+i*ww/7,y+6+(i%2)*6,3.5,3.5,i%2?MUSTARD_L:'#fff6d6');}
/** Fitting-room booth: plain cotton curtain at first, violet velvet later. */
function fittingRoom(c,p,x,y,ww,h,stage){R(c,x-6,y-8,ww+12,h+8,WOOD_D,[10,10,0,0]);R(c,x,y,ww,h,'#f6f2fb',[6,6,0,0]);
  L(c,x-2,y+8,x+ww+2,y+8,'#9aa3b5',4);const col=stage>=2?VIOLET:'#e8e0cc',dk=stage>=2?VIOLET_D:'#cbbf9f';
  for(let i=0;i<7;i++){const fx=x+4+i*(ww*.62)/7;E(c,fx+4,y+8,3,3,'#9aa3b5');}
  P(c,[[x+2,y+10],[x+ww*.64,y+10],[x+ww*.6,y+h],[x+2,y+h]],col);for(let i=1;i<6;i++)L(c,x+2+i*ww*.11,y+14,x+2+i*ww*.105,y+h-2,dk,2);
  E(c,x+ww*.6,y+h*.55,5,10,MUSTARD);R(c,x+ww*.7,y+h*.3,ww*.24,ww*.24,'#fffdf8',4,PANEL_D,1);T(c,'THỬ',x+ww*.82,y+h*.3+ww*.12,fit(c,'THỬ',ww*.2,11,800),VIOLET_D,800);
  if(stage>=2){const g=c.createRadialGradient(x+ww/2,y+12,0,x+ww/2,y+12,70);g.addColorStop(0,'#ffe4a455');g.addColorStop(1,'#ffe4a400');c.fillStyle=g;c.fillRect(x-40,y-30,ww+80,120);}}
/** Tall standing mirror. */
function mirror(c,x,y,h){R(c,x-16,y,32,h,WOOD_D,16);R(c,x-12,y+4,24,h-8,'#dfe8f1',12);L(c,x-6,y+16,x+4,y+h*.4,'#ffffffc0',3);L(c,x-4,y+h*.5,x+2,y+h*.62,'#ffffff90',2);}
function door(c,p,x,y,ww,h,size,open,words){R(c,x-8,y-8,ww+16,h+8,WOOD_D,[12,12,0,0]);R(c,x,y,ww,h,'#b9ade0',[8,8,0,0],VIOLET,2);
  R(c,x+ww*.16,y+h*.08,ww*.68,h*.42,open?'#eef6fb':'#dde6f0',6,VIOLET,2);L(c,x+ww*.2,y+h*.32,x+ww*.44,y+h*.12,'#ffffffb0',3);
  R(c,x+ww*.16,y+h*.6,ww*.68,h*.32,'#c9bfe9',5,VIOLET,1.5);E(c,x+ww-12,y+h*.56,4,4,MUSTARD);
  // Hanger-shaped door sign.
  const hx=x+ww/2,hy=y+h*.24;L(c,hx,hy-12,hx,hy-4,'#9aa3b5',2);P(c,[[hx,hy-4],[hx-18,hy+8],[hx+18,hy+8]],'#00000000');L(c,hx,hy-4,hx-18,hy+8,'#9aa3b5',2);L(c,hx,hy-4,hx+18,hy+8,'#9aa3b5',2);L(c,hx-18,hy+8,hx+18,hy+8,'#9aa3b5',2);
  if(open)P(c,[[x+ww-3,y],[x+ww+10,y-4],[x+ww+10,y+h],[x+ww-3,y+h]],'#a497d4');
  const s=open?words.open_sign:words.closed_sign,sw=ww+14,sy=y+h*.5;L(c,hx,sy-12,hx-16,sy,'#9aa3b5',1.5);L(c,hx,sy-12,hx+16,sy,'#9aa3b5',1.5);
  R(c,hx-sw/2,sy,sw,size*1.9,CREAM,9,open?'#8fb77f':'#d59a9a',2);T(c,s,hx,sy+size*.97,fit(c,s,sw-10,size,800),open?VIOLET_D:'#a35f63',800);}
function plaque(c,p,x,y,ww,h){R(c,x,y,ww,h,WOOD_D,7);R(c,x+4,y+4,ww-8,h-8,CREAM,5);at(c,x+ww/2,y+5,ww/64,()=>shirt(c,VIOLET));}
function security(c,p,items,[cx,cy],[bx,by],[lx,ly]){
  if(items.includes('camera')){L(c,cx-18,cy+12,cx-4,cy+3,'#9c8aa8',4);R(c,cx-12,cy-10,38,20,'#f5f2f8',7,'#a7a2b2',2);E(c,cx+21,cy,7,8,'#6f6789');E(c,cx+22,cy,3,4,'#b4d9df');}
  if(items.includes('bell')){L(c,bx,by-14,bx,by-4,'#ac8f73',2);P(c,[[bx-10,by+12],[bx+10,by+12],[bx+7,by-3],[bx-7,by-3]],MUSTARD_L);E(c,bx,by+14,4,3,MUSTARD);}
  if(items.includes('light')){const g=c.createRadialGradient(lx,ly+18,0,lx,ly+18,80);g.addColorStop(0,'#ffe1a44a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(lx-80,ly-62,160,160);R(c,lx-12,ly-6,24,22,'#fff0b8',[4,4,9,9],'#b69b79',2);}}
/** String of fairy lights (the prettiest shop in the alley). */
function lights(w,x0,x1,y){const c=w.ctx;c.strokeStyle='#8a7a9e';c.lineWidth=1.2;c.beginPath();c.moveTo(x0,y);for(let x=x0;x<x1;x+=60)c.quadraticCurveTo(x+30,y+14,x+60,y);c.stroke();
  for(let x=x0+10,i=0;x<x1;x+=30,i++){const on=w.reduced||Math.floor(w.time*2+i)%3!==0;E(c,x,y+6+Math.sin(i)*3,3.5,3.5,on?(i%2?MUSTARD_L:'#fff4d0'):'#d8cfe0');}}

/* ------------------------------------------------------------ Floor pieces */
/** Cubbies of folded stock: the `warehouse`. */
function cubbies(c,W,H,ts){E(c,0,2,W/2+8,7,SHADOW);R(c,-W/2,-H,W,H,WOOD_L,8,EDGE,2);R(c,-W/2+6,-H+6,W-12,ts*1.8,CREAM,5);T(c,'KHO',0,-H+6+ts*.9,fit(c,'KHO',W-20,ts,800),VIOLET_D,800);
  const rows=4,cols=2,top=-H+ts*1.8+12,ch=(H-ts*1.8-24)/rows,cw=(W-16)/cols;
  for(let r=0;r<rows;r++)for(let k=0;k<cols;k++){const x=-W/2+8+k*cw,y=top+r*ch;R(c,x+2,y+2,cw-4,ch-4,'#e8d3b8',3);
    for(let s=0;s<3;s++)R(c,x+6,y+ch-8-s*6-6,cw-12,6,HANG[(r*2+k+s*3)%HANG.length],2,'#00000018',.8);}}
/** Garment rail with coloured hangers: the `shelf`. */
function rail(c,p,W,stage){const hw=W/2;E(c,0,2,hw+8,7,SHADOW);for(const d of [-1,1]){L(c,d*hw,0,d*hw,-150,'#8a8f99',4);L(c,d*hw-10,0,d*hw+10,0,'#8a8f99',4);}
  L(c,-hw-6,-150,hw+6,-150,'#9aa3b5',5);const n=Math.max(6,Math.floor(W/24));
  for(let i=0;i<n;i++){const x=-hw+14+i*(W-28)/(n-1),col=HANG[i%HANG.length];at(c,x,-150,1,()=>(i%4===2?dress(c,col,.9):i%4===3?jeans(c,col,.9):shirt(c,col,.9)));}
  // Low shelf of folded tees and shoe boxes.
  R(c,-hw+6,-30,W-12,7,WOOD,2,EDGE,1);for(let i=0;i<4;i++)R(c,-hw+16+i*(W-32)/4,-44,(W-32)/4-8,14,HANG[(i*3+1)%HANG.length],3,'#00000018',1);
  if(stage>=2){R(c,hw-44,-172,38,20,CREAM,4,VIOLET,1);T(c,'MỚI',hw-25,-162,10,VIOLET_D,800);}}
/** Bà Tư's cutting table with the old treadle sewing machine and a steamer: the `workbench`. */
function cuttingTable(w,p,W,ts){const c=w.ctx,hw=W/2,top=-90;E(c,0,3,hw+14,8,SHADOW);
  for(const d of [-1,1])R(c,d*(hw-12)-5,top+12,10,-top-12,WOOD_D,3);
  // Treadle under the machine.
  at(c,-hw+70,0,1,()=>{R(c,-26,-10,52,8,'#3c3a44',3);c.beginPath();c.arc(0,-40,20,0,Math.PI*2);c.strokeStyle='#3c3a44';c.lineWidth=3;c.stroke();for(let i=0;i<4;i++){const a=i*Math.PI/4+(w.reduced?0:w.time*.4);L(c,Math.cos(a)*-20,-40+Math.sin(a)*-20,Math.cos(a)*20,-40+Math.sin(a)*20,'#3c3a44',1.5);}});
  R(c,-hw+2,top+10,W-4,20,WOOD,3,EDGE,1.5);const lab=w.game?.catalogue?.find(x=>x.id===w.career)?.station||'Bàn may';const lw=Math.min(W*.42,ts*8.5);
  R(c,-lw/2,top+12,lw,16,MUSTARD_L,4,MUSTARD,1);T(c,lab,0,top+20.5,fit(c,lab,lw-12,ts,800),'#5b4312',800);
  R(c,-hw-6,top,W+12,13,WOOD_L,5,EDGE,1.5);
  // The black sewing machine with gold lettering.
  at(c,-hw+70,top,1,()=>{R(c,-40,-8,80,8,'#2d2a2e',2);P(c,[[-34,-8],[-34,-40],[24,-44],[30,-36],[-18,-34],[-18,-8]],'#2d2a2e');R(c,20,-40,14,32,'#2d2a2e',3);
    L(c,-28,-36,16,-39,MUSTARD,1.5);E(c,-30,-24,7,7,'#3c3a44');E(c,-30,-24,3,3,MUSTARD);L(c,27,-8,27,4,'#c9ccd4',1.5);
    R(c,-8,-56,8,12,VIOLET,2);L(c,-4,-56,-4,-44,'#ffffff60',1);});
  // Fabric on the table, tape measure and pincushion.
  P(c,[[-hw+130,top-2],[hw-120,top-4],[hw-110,top+18],[-hw+120,top+22]],'#f2c1cf');for(let x=-hw+140;x<hw-120;x+=18)L(c,x,top,x+6,top+18,'#e7a7ba',1);
  c.beginPath();c.moveTo(-10,top-2);c.bezierCurveTo(10,-8+top,30,top+4,46,top-4);c.strokeStyle=MUSTARD;c.lineWidth=4;c.stroke();
  E(c,56,top-6,9,7,'#d23b3b');for(let i=0;i<4;i++)L(c,52+i*3,top-12,50+i*4,top-20,'#8a8f99',1);
  // Steamer.
  at(c,hw-40,top,1,()=>{R(c,-12,-30,24,30,'#e9e6f2',6,'#9aa3b5',1.5);L(c,0,-30,4,-64,'#9aa3b5',2);R(c,-2,-78,12,16,'#c9ccd4',3);
    if(!w.reduced){const k=(w.time*.8)%1;E(c,6+k*6,-86-k*18,5+k*4,4+k*3,`rgba(255,255,255,${.7-k*.6})`);}});}
/** Counter with receipts (`evidence`) and the till (`counter`). */
function counter(w,p,W,big){const c=w.ctx,hw=W/2,top=-94;E(c,0,3,hw+12,8,SHADOW);
  R(c,-hw,top+12,W,-top-12,'#d9d0ef',8,VIOLET,2);for(let x=-hw+14;x<hw-6;x+=14)L(c,x,top+20,x,-10,'#c9bde6',2);R(c,-hw,-12,W,12,LILAC_D,[0,0,8,8]);
  at(c,0,top+50,1,()=>shirt(c,CREAM,.7));
  R(c,-hw-6,top,W+12,14,WOOD_L,6,EDGE,1.5);
  // Receipt book and a paper shopping bag.
  const ox=-hw+(big?36:30);R(c,ox-16,top-16,32,16,CREAM,2,PANEL_D,1);for(let i=0;i<3;i++)L(c,ox-12,top-12+i*4,ox+10,top-12+i*4,'#c4b3a0',1);
  const bx=ox+(big?40:34);P(c,[[bx-12,top],[bx+12,top],[bx+10,top-30],[bx-10,top-30]],'#e8d1b0');c.beginPath();c.arc(bx,top-30,6,Math.PI,0);c.strokeStyle=VIOLET;c.lineWidth=2;c.stroke();T(c,'♡',bx,top-14,10,VIOLET);
  // Till.
  const rx=hw-(big?34:38);R(c,rx-24,top-30,48,30,'#e7e1f5',7,VIOLET_D,1.5);R(c,rx-18,top-42,26,12,CREAM,3,LILAC_D,1);
  for(let i=0;i<4;i++)for(let j=0;j<2;j++)E(c,rx-14+i*8,top-22+j*7,2.4,2.4,j?CREAM:VIOLET);R(c,rx-22,top-6,44,5,LILAC_D,2);}
function ledgerDesk(w,p,ts){const c=w.ctx,words=w.words();E(c,0,2,44,6,SHADOW);R(c,-38,-44,6,44,EDGE,2);R(c,32,-44,6,44,EDGE,2);
  R(c,-40,-44,80,32,WOOD,7,EDGE,1.5);R(c,-33,-38,66,20,CREAM,4);T(c,words.ledger,0,-28,fit(c,words.ledger,60,ts,800),VIOLET_D,800);
  R(c,-46,-54,92,12,WOOD_L,5,EDGE,1.5);P(c,[[-26,-55],[-2,-52],[-2,-64],[-24,-67]],CREAM);P(c,[[22,-55],[-2,-52],[-2,-64],[20,-67]],'#fffdf5');L(c,-18,-60,-6,-58,VIOLET,1.5);}
/** Bolt stack of fabric (first days) or a floor mannequin (the shop has grown). */
function entrance(w,c,stage){if(stage>=1){mannequin(c,{top:'#f7f5ef',bottom:'#2f4f86',belt:'#8a5a3b'});return;}
  E(c,0,2,40,6,SHADOW);['#c9b8e0','#e7c1cc','#d9cbb4','#a9c9e8'].forEach((col,i)=>{R(c,-34,-12-i*12,68,12,col,6,'#00000020',1);E(c,-34,-6-i*12,4,6,'#00000018');});}
function plant(c){E(c,0,2,20,5,SHADOW);for(const [x,y,a] of [[-12,-50,-2.4],[12,-54,-.7],[0,-62,-1.6],[-16,-34,-2.8],[16,-38,-.3]]){c.save();c.translate(x,y);c.rotate(a);E(c,10,0,12,5,'#78ab80');c.restore();}
  P(c,[[-15,-26],[15,-26],[11,0],[-11,0]],'#d9c7ef');R(c,-17,-29,34,6,LILAC_D,2);}

/* ------------------------------------------------------------ Rooms */
function landRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words(),stage=look(w);
  E(c,605,724,503,30,'#6a58a622');R(c,85,165,1030,550,WOOD_D,35);R(c,96,168,1008,533,CREAM,30,WOOD,3);
  wall(c,p,108,179,984,270);wainscot(c,108,380,984,446);floor(c,108,445,984,244);R(c,108,440,984,9,WOOD,3);
  tape(c,120,1080,186);
  sign(c,p,360,56,480,102,stage);
  if(stage>=3)lights(w,120,1080,206);
  fittingRoom(c,p,248,236,120,196,stage);
  windowBox(w,p,500,214,240,178);
  mirror(c,780,250,170);
  streetBoard(c,p,888,258);
  plaque(c,p,1003,212,44,40);
  door(c,p,980,262,90,183,12,open,words);
  security(c,p,items,[170,222],[962,266],[262,302]);}
function portRoom(w,p){const c=w.ctx,items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words(),stage=look(w);
  E(c,350,857,324,23,'#6a58a622');R(c,22,114,656,738,WOOD_D,31);R(c,29,117,642,724,CREAM,26,WOOD,3);
  wall(c,p,40,139,620,372);wainscot(c,40,440,620,506);floor(c,40,506,620,323);R(c,40,500,620,9,WOOD,3);
  tape(c,50,650,146);
  sign(c,p,125,30,450,100,stage);
  if(stage>=3)lights(w,50,650,166);
  fittingRoom(c,p,186,260,120,170,stage);
  windowBox(w,p,356,200,174,190);
  streetBoard(c,p,547,194,.86);
  plaque(c,p,610,206,40,40);
  door(c,p,550,300,94,206,15,open,words);
  security(c,p,items,[86,240],[536,212],[443,176]);}

/* ------------------------------------------------------------ Floor props */
function landProps(w,p){const c=w.ctx,stage=look(w),out=[];
  out.push([502,()=>at(c,196,500,1,()=>cubbies(c,112,212,14))]);
  out.push([502,()=>at(c,375,500,1,()=>rail(c,p,206,stage))]);
  out.push([594,()=>at(c,570,594,1,()=>cuttingTable(w,p,300,13))]);
  out.push([594,()=>at(c,890,594,1,()=>counter(w,p,180,false))]);
  out.push([628,()=>at(c,195,628,1,()=>entrance(w,c,stage))]);
  out.push([656,()=>at(c,1028,656,1,()=>ledgerDesk(w,p,12))]);
  if(stage>=2)out.push([680,()=>at(c,126,678,1,()=>plant(c))]);
  return out;}
function portProps(w,p){const c=w.ctx,stage=look(w),out=[];
  out.push([598,()=>at(c,98,598,1,()=>cubbies(c,104,226,16))]);
  out.push([566,()=>at(c,253,566,.85,()=>rail(c,p,206,stage))]);
  out.push([700,()=>at(c,260,700,1,()=>cuttingTable(w,p,284,16))]);
  out.push([700,()=>at(c,525,700,1,()=>counter(w,p,170,true))]);
  out.push([818,()=>at(c,600,818,1,()=>ledgerDesk(w,p,16))]);
  if(stage>=1)out.push([818,()=>at(c,130,818,.9,()=>entrance(w,c,stage))]);
  return out;}

export default {
  id:'boutique',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
