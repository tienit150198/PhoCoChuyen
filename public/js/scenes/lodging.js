/** Lodging scene (homestay "Homestay Mây Đà Lạt"): a cosy pine-wood lobby
 * in misty Đà Lạt. A loft gallery with three room doors (Đồi Thông, Sương
 * Sớm, Ban Công Hồ) is reached by a wooden staircase; under the stairs sits
 * the linen cubby (warehouse). Below: a big window onto pines and misty
 * hills, the key board (shelf) and room calendar (evidence) behind the
 * reception desk (workbench = check-in with bell and guest book, counter =
 * check-out tray), a stone fireplace with rug, armchair and the cat, a small
 * guest-ledger desk (finance) and the front door sign with luggage.
 * Plan schema: see scenes/shop.js. */
import {R,E,L,T,P,fit,heart,signBoard,streetBoard} from './kit.js';

const WOOD='#c4946c',WOOD_D='#a87a57',WOOD_L='#dcb08a';
const TAGS=['#a9c79f','#b6c9e3','#e8cc95','#efb5ca','#c9b5dc','#a9d6c6'];
const HYD=['#a9c1ea','#c6b3e3','#f0b8cc'];
const ROOMS=[['Đồi Thông','#7fa98a'],['Sương Sớm','#9fb9d8'],['Ban Công Hồ','#86bdbb']];

export const PLAN={
 land:{badge:{board:[30,-40],shelf:[30,-22]},wall:{poster:[1062,332]},anchors:{window:[615,505],glass:[615,350]},floor:[130,452,1070,682],lane:505,line:563,home:[680,505],kx:82,ky:45,sway:38,
   blocks:[[520,540,880,586],[108,445,300,468],[900,445,1045,470],[940,470,1005,490],[1000,522,1080,562],[140,590,250,620],[945,652,1030,668],[1040,655,1092,675]],
   bench:[300,522,420,545],garden:[[470,684],[525,684]],
   customers:[[590,624],[710,630],[830,622],[650,676]],event:[440,655],officer:[320,665],
   staff:{x:560,step:125,y:462},cat:[972,482],counterSpan:[530,870],
   decor:{corner:[130,668],front:[880,675],center:[150,522]},sill:{plant:[545,432],lamp:[600,432],seat:[670,432],rug:[420,610]},
   spots:{shelf:[[770,352],48,[[765,505]]],evidence:[[859,360],45,[[860,505]]],workbench:[[610,470],58,[[610,505]]],counter:[[790,470],52,[[790,505]]],
     warehouse:[[258,404],45,[[250,505]]],board:[[343,361],45,[[343,505]]],finance:[[195,566],42,[[195,652],[282,600]]],
     property:[[972,326],35,[[925,505]]],security:[[166,230],30,[[215,505]]],door:[[988,632],45,[[900,655],[990,615]]],pet:[[972,462],38,[[972,505]]]}},
 port:{badge:{board:[-50,-40],shelf:[50,-18]},wall:{poster:[546,410]},anchors:{window:[310,572],glass:[310,380]},floor:[62,512,638,822],lane:572,line:626,home:[330,572],kx:51,ky:57,sway:24,
   blocks:[[215,612,515,655],[45,506,215,530],[100,530,165,552],[515,506,660,530],[58,622,138,652],[556,730,654,746],[470,790,580,808],[595,780,655,800]],
   bench:[70,795,190,815],garden:[[215,826],[265,826]],
   customers:[[250,705],[370,700],[490,706],[240,772]],event:[120,735],officer:[430,772],
   staff:{x:260,step:95,y:526},cat:[135,545],counterSpan:[225,505],
   decor:{corner:[85,700],front:[600,640],center:[350,812]},sill:{plant:[255,474],lamp:[300,474],seat:[355,474],rug:[330,740]},
   spots:{shelf:[[457,372],45,[[457,572]]],evidence:[[457,462],45,[[480,572]]],workbench:[[290,582],55,[[290,572]]],counter:[[440,582],50,[[440,572]]],
     warehouse:[[562,472],45,[[565,572]]],board:[[600,246],55,[[560,572]]],finance:[[605,712],42,[[605,698],[520,745]]],
     property:[[130,372],35,[[130,572]]],security:[[622,168],30,[[595,572]]],door:[[525,795],45,[[410,800],[525,765]]],pet:[[135,528],38,[[135,572]]]}},
};

/* ------------------------------------------------------------ small pieces */
function floorBoards(c,x,y,w,h,r){c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();
  for(let row=0,yy=y;yy<y+h;row++,yy+=30){c.fillStyle=row%2?'#f2dab6':'#ecd1aa';c.fillRect(x,yy,w,30);L(c,x,yy,x+w,yy,'#dcb68d',1.3);
    for(let xx=x+40+(row%3)*72;xx<x+w;xx+=216)L(c,xx,yy+4,xx,yy+26,'#dcb68d',1.2);}
  c.restore();}
function pine(c,x,y,h,col){R(c,x-h*.05,y-h*.17,h*.1,h*.17,'#9c7b5f',2);for(let k=0;k<3;k++){const a=y-h+k*h*.24,hw=h*(.15+k*.07);P(c,[[x,a],[x-hw,a+h*.42],[x+hw,a+h*.42]],col);}}
function hydrangea(c,x,y,r,col){E(c,x-r*.95,y+r*.55,r*.6,r*.28,'#88b48c');E(c,x+r*.95,y+r*.55,r*.6,r*.28,'#7aa982');
  for(let i=0;i<9;i++){const a=i*2.4,d=i?r*.55:0;E(c,x+Math.cos(a)*d,y+Math.sin(a)*d*.85,r*.42,r*.42,col);}
  for(let i=0;i<5;i++){const a=i*1.3+.4;E(c,x+Math.cos(a)*r*.45,y+Math.sin(a)*r*.4-r*.15,r*.12,r*.12,'#ffffff90');}}
function pot(c,x,y,s,col){R(c,x-13*s,y-20*s,26*s,21*s,'#e9c5ab',6*s,'#c99c82',1.2);R(c,x-15*s,y-23*s,30*s,7*s,'#dfb398',3*s);hydrangea(c,x,y-32*s,13*s,col);}
function flame(c,x,y,h,r,col){c.beginPath();c.moveTo(x,y-h);c.bezierCurveTo(x+r*1.1,y-h*.45,x+r,y,x,y);c.bezierCurveTo(x-r,y,x-r*1.1,y-h*.45,x,y-h);c.fillStyle=col;c.fill();}
function lantern(c,x,y,s,on){L(c,x,y-14*s,x,y-4*s,'#b08a66',1.5);if(on){const g=c.createRadialGradient(x,y+9*s,0,x,y+9*s,30*s);g.addColorStop(0,'#ffe2a466');g.addColorStop(1,'#ffe2a400');c.fillStyle=g;c.fillRect(x-30*s,y-21*s,60*s,60*s);}
  R(c,x-8*s,y-4*s,16*s,4*s,WOOD_D,2);R(c,x-7*s,y,14*s,19*s,on?'#fff0bf':'#f3e3c4',5*s,'#c79b6f',1.2);R(c,x-8*s,y+19*s,16*s,4*s,WOOD_D,2);}
/** The big window: pines, misty hills, a pale sun, curtains and sill. */
function bigWindow(c,x,y,w,h,t){R(c,x-10,y-10,w+20,h+20,WOOD,16,WOOD_D,2);
  c.save();c.beginPath();c.roundRect(x,y,w,h,10);c.clip();
  const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#cfe2ea');g.addColorStop(1,'#f4f0e1');c.fillStyle=g;c.fillRect(x,y,w,h);
  E(c,x+w*.76,y+h*.2,h*.1,h*.1,'#fff5d2');
  E(c,x+w*.22,y+h*.74,w*.45,h*.28,'#c9dbd2');E(c,x+w*.82,y+h*.7,w*.46,h*.32,'#bbd1c6');
  c.globalAlpha=.75;R(c,x-10,y+h*.56,w+20,h*.1,'#ffffff',h*.05);c.globalAlpha=1;
  const n=Math.max(4,Math.round(w/30));for(let i=0;i<n;i++){const px=x+12+i*(w-24)/(n-1),ph=h*(.3+((i*37)%5)*.05);pine(c,px,y+h*.95,ph,i%2?'#6f9a7f':'#5f8b71');}
  E(c,x+w*.5,y+h*1.08,w*.75,h*.17,'#a3c1a0');
  const d=(t*7)%(w+120);c.globalAlpha=.5;E(c,x-60+d,y+h*.4,w*.2,h*.045,'#ffffff');E(c,x+w+60-((d*1.4)%(w+120)),y+h*.62,w*.16,h*.04,'#ffffff');c.globalAlpha=1;
  c.restore();
  L(c,x+w/2,y+2,x+w/2,y+h-2,'#fbf3e6',6);L(c,x+2,y+h*.46,x+w-2,y+h*.46,'#fbf3e6',6);
  P(c,[[x-13,y-12],[x+w*.17,y-12],[x+w*.05,y+h*.52],[x+w*.09,y+h+2],[x-13,y+h+2]],'#f8e7d5');R(c,x-11,y+h*.5,w*.14,7,'#e2b7a1',3);
  P(c,[[x+w+13,y-12],[x+w*.83,y-12],[x+w*.95,y+h*.52],[x+w*.91,y+h+2],[x+w+13,y+h+2]],'#f8e7d5');R(c,x+w*.86+11,y+h*.5,w*.14-11,7,'#e2b7a1',3);
  R(c,x-18,y-19,w+36,13,'#e6c3a3',6,'#c99a76',1.2);
  R(c,x-16,y+h+6,w+32,11,'#d2a57d',5,WOOD_D,1);}
/** A room door on the loft with its name plate hanging from the beam. */
function roomDoor(c,p,cx,top,bottom,w,name,tint,fs,plateY,plateH,plateW){const h=bottom-top;
  R(c,cx-w/2-5,top-5,w+10,h+5,WOOD_D,[w/2+5,w/2+5,2,2]);R(c,cx-w/2,top,w,h,'#dfae82',[w/2,w/2,2,2],'#a97a55',1.5);
  R(c,cx-w/2+7,top+w*.55,w-14,h*.24,'#e9c197',5);R(c,cx-w/2+7,top+w*.55+h*.3,w-14,h*.26,'#e9c197',5);
  E(c,cx,top+w*.3,w*.2,w*.15,'#d9edf0');L(c,cx,top+w*.16,cx,top+w*.45,'#dfae82',2);
  E(c,cx+w*.33,top+h*.62,3.5,3.5,'#f0cf86');
  E(c,cx,top+w*.3,w*.08,w*.08,tint);
  L(c,cx-plateW*.3,plateY-9,cx-plateW*.3,plateY,'#b08a66',1.5);L(c,cx+plateW*.3,plateY-9,cx+plateW*.3,plateY,'#b08a66',1.5);
  R(c,cx-plateW/2,plateY,plateW,plateH,'#fff8ea',plateH/2,tint,2);T(c,name,cx,plateY+plateH/2+1,fit(c,name,plateW-14,fs),p.dark,800);}
/** Loft floor beam and railing from x0 to x1 at floor height gy. */
function gallery(c,x0,x1,gy){R(c,x0,gy+16,x1-x0,7,'#a87a5722',0);R(c,x0,gy,x1-x0,17,WOOD,0);R(c,x0,gy,x1-x0,4,WOOD_L,0);
  for(let x=x0+10;x<x1-4;x+=19)L(c,x,gy-24,x,gy-2,'#c79b72',4);R(c,x0,gy-32,x1-x0,8,'#d2a67d',4,WOOD_D,1);}
/** Solid wooden staircase from the bottom (bx,by) to the top (tx,ty). */
function stairs(c,bx,by,tx,ty,n){const pts=[[bx,by]];for(let i=0;i<n;i++){const xs=bx+(tx-bx)*i/n,xe=bx+(tx-bx)*(i+1)/n,y=by-(by-ty)*(i+1)/n;pts.push([xs,y],[xe,y]);}pts.push([tx,by]);
  P(c,pts,'#e3b98f');c.strokeStyle=WOOD_D;c.lineWidth=2;c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.stroke();
  for(let i=0;i<n;i++){const xs=bx+(tx-bx)*i/n,xe=bx+(tx-bx)*(i+1)/n,y=by-(by-ty)*(i+1)/n;R(c,Math.min(xs,xe)-2,y-1,Math.abs(xe-xs)+4,6,'#f1d0a6',2);}
  // Banister: posts on each step, rail along the slope.
  const hgt=40,step=(tx-bx)/n,rise=(by-ty)/n;
  for(let i=0;i<n;i++){const x=bx+step*(i+.5),y=by-rise*(i+1);L(c,x,y,x,y-hgt,'#c79b72',3);}
  L(c,bx+step*.5,by-rise-hgt,tx-step*.5,ty-hgt,'#b8875f',7);L(c,bx+step*.5,by-rise-hgt-2,tx-step*.5,ty-hgt-2,WOOD_L,2);
  R(c,bx+step*.5-6,by-rise-hgt-8,12,hgt+8+rise,WOOD,4,WOOD_D,1.2);E(c,bx+step*.5,by-rise-hgt-9,7,6,WOOD_L);}
/** Under-stairs linen cubby (warehouse): folded towels and blankets. */
function linenCubby(c,x,y,w,h,lock){R(c,x-4,y-4,w+8,h+8,WOOD_D,8);R(c,x,y,w,h,'#f7ebd8',6);R(c,x,y+h/2-3,w,6,WOOD,2);
  const stacks=Math.max(2,Math.floor(w/30)),cols=['#ffffff','#cfe3d6','#f4d3dc','#d8e2f2','#f3e2bd'];
  for(let row=0;row<2;row++)for(let i=0;i<stacks;i++){const sx=x+6+i*(w-12)/stacks,sw=(w-12)/stacks-5,base=y+(row?h-3:h/2-4);
    for(let k=0;k<3;k++)R(c,sx,base-(k+1)*(h/2-10)/3,sw,(h/2-12)/3,cols[(i+k+row*2)%5],3,'#d9c7ae',1);}
  if(lock){R(c,x+w-20,y+h/2-8,16,18,'#d8c596',4,'#a09675',1.2);c.beginPath();c.arc(x+w-12,y+h/2-8,5,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=2.5;c.stroke();}}
/** Key board (shelf): hooks with keys on coloured wooden tags. */
function keyBoard(c,p,x,y,w,h,cols,rows,fs){R(c,x,y,w,h,'#c89f7f',9,WOOD_D,1.5);R(c,x+5,y+5,w-10,h-10,'#fff6e6',6);
  const kx=(w-16)/cols,ky=(h-12)/rows;
  for(let r=0;r<rows;r++)for(let k=0;k<cols;k++){const i=r*cols+k,hx=x+8+kx*(k+.5),hy=y+10+ky*r;E(c,hx,hy,2.6,2.6,'#a98563');if(i===2)continue;
    c.beginPath();c.arc(hx,hy+7,4,0,Math.PI*2);c.strokeStyle='#d0a651';c.lineWidth=2;c.stroke();L(c,hx,hy+11,hx,hy+ky*.42,'#d0a651',2.2);L(c,hx,hy+ky*.36,hx+4,hy+ky*.36,'#d0a651',2);
    const tw=Math.min(kx-5,fs*1.6),th=ky*.42;R(c,hx-tw/2,hy+ky*.44,tw,th,TAGS[i%6],4,'#b3906f',1);T(c,String(i+1),hx,hy+ky*.44+th/2+1,fs,'#6d5445',800);}}
/** Room calendar (evidence): coloured stays across the week. */
function calendar(c,p,x,y,w,h,title,fs){R(c,x,y,w,h,'#fffdf6',7,'#d3b597',2);const hh=fs+10;R(c,x,y,w,hh,p.primary,[7,7,0,0]);T(c,title,x+w/2,y+hh/2+1,fit(c,title,w-10,fs,800),'#fffaf0',800);
  for(let i=0;i<3;i++)E(c,x+w*(i+1)/4,y-1,3,4,'#8d7663');
  const gx=x+6,gy=y+hh+5,cw=(w-12)/7,rows=4,ch=(h-hh-10)/rows;
  for(let r=0;r<=rows;r++)L(c,gx,gy+r*ch,gx+cw*7,gy+r*ch,'#eadcc8',1);for(let k=0;k<=7;k++)L(c,gx+k*cw,gy,gx+k*cw,gy+ch*rows,'#eadcc8',1);
  for(const [r,a,b,col] of [[0,0,3,'#a9c79f'],[0,4,7,'#efb5ca'],[1,1,5,'#b6c9e3'],[2,0,2,'#e8cc95'],[2,3,6,'#a9c79f'],[3,2,4,'#c9b5dc']])R(c,gx+a*cw+2,gy+r*ch+ch*.22,(b-a)*cw-4,ch*.56,col,ch*.25);
  c.beginPath();c.arc(gx+cw*5.5,gy+ch*3.5,Math.min(cw,ch)*.45,0,Math.PI*2);c.strokeStyle='#d9837f';c.lineWidth=2;c.stroke();}
/** Stone fireplace: chimney breast from `top`, mantle, burning logs. */
function fireplace(c,p,cx,top,mantle,bottom,w,fw,t,hood){
  if(hood)P(c,[[cx-w*.34,top],[cx+w*.34,top],[cx+w/2,mantle],[cx-w/2,mantle]],'#eadfce');else R(c,cx-w/2,top,w,mantle-top,'#eadfce',0);
  c.save();c.beginPath();if(hood){c.moveTo(cx-w*.34,top);c.lineTo(cx+w*.34,top);c.lineTo(cx+w/2,mantle);c.lineTo(cx-w/2,mantle);c.closePath();}else c.rect(cx-w/2,top,w,bottom-top);c.clip();
  for(let row=0,y=top+4;y<bottom;row++,y+=21)for(let x=cx-w/2-(row%2?14:2);x<cx+w/2;x+=30)R(c,x+2,y,26,17,(row+Math.round(x/30))%3?'#e2d5c1':'#f1e8da',7);
  c.restore();
  R(c,cx-w/2,mantle,w,bottom-mantle,'#e7dac6',[4,4,0,0],'#cdbba4',1.5);
  c.save();c.beginPath();c.rect(cx-w/2,mantle,w,bottom-mantle);c.clip();for(let row=0,y=mantle+14;y<bottom;row++,y+=19)for(let x=cx-w/2-(row%2?12:0);x<cx+w/2;x+=26)R(c,x+2,y,22,15,row%2?'#dfd0bb':'#efe5d5',6);c.restore();
  const fy=mantle+(bottom-mantle)*.28;R(c,cx-fw/2-6,fy-6,fw+12,bottom-fy+6,'#cbb9a1',[fw/2+6,fw/2+6,0,0]);R(c,cx-fw/2,fy,fw,bottom-fy,'#5e4640',[fw/2,fw/2,0,0]);
  const glow=c.createRadialGradient(cx,bottom-8,2,cx,bottom-8,fw*.9);glow.addColorStop(0,'#ffcf7a88');glow.addColorStop(1,'#ffcf7a00');c.fillStyle=glow;c.fillRect(cx-fw,fy-10,fw*2,bottom-fy+20);
  const fh=(bottom-fy)*.72;for(let k=0;k<3;k++){const f=1+.12*Math.sin(t*7+k*2.1),dx=(k-1)*fw*.2;flame(c,cx+dx,bottom-9,fh*(k===1?1:.72)*f,fw*.13,'#ffae63');flame(c,cx+dx,bottom-9,fh*(k===1?.72:.5)*f,fw*.08,'#ffd982');flame(c,cx+dx,bottom-9,fh*(k===1?.38:.26)*f,fw*.04,'#fff5c6');}
  R(c,cx-fw*.36,bottom-11,fw*.72,8,'#8b604a',4);R(c,cx-fw*.3,bottom-17,fw*.5,7,'#a0725a',4);E(c,cx+fw*.2,bottom-13,4,4,'#c89878');
  R(c,cx-w/2-10,mantle-7,w+20,13,WOOD,4,WOOD_D,1.5);R(c,cx-w/2-8,mantle-7,w+16,3,WOOD_L,2);
  // Candles and a pine-cone jar on the mantle.
  for(const [dx,hh] of [[-.36,18],[-.28,13]]){R(c,cx+w*dx-4,mantle-7-hh,8,hh,'#fff5e2',2,'#e0cfb4',1);flame(c,cx+w*dx,mantle-8-hh,9*(1+.1*Math.sin(t*9+dx*9)),3,'#ffc86e');}
  R(c,cx+w*.24,mantle-25,18,18,'#e3f0ee',5,'#b8cfcc',1);E(c,cx+w*.24+9,mantle-14,5,6,'#a07352');}
/** Framed picture of the homestay among pines (the `property` spot). */
function housePicture(c,x,y,w,h){R(c,x-4,y-4,w+8,h+8,WOOD,6,WOOD_D,1.2);R(c,x,y,w,h,'#dcebee',3);E(c,x+w*.5,y+h*.95,w*.7,h*.3,'#a9c7a4');
  pine(c,x+w*.14,y+h*.92,h*.62,'#6f9a7f');pine(c,x+w*.88,y+h*.92,h*.7,'#5f8b71');
  R(c,x+w*.3,y+h*.48,w*.42,h*.36,'#fff2dc',2);P(c,[[x+w*.24,y+h*.5],[x+w*.51,y+h*.2],[x+w*.78,y+h*.5]],'#c98f7a');R(c,x+w*.46,y+h*.63,w*.1,h*.21,'#b98a64',1);E(c,x+w*.36,y+h*.62,w*.04,w*.04,'#ffe39c');}
function coatRack(c,x,y,w){R(c,x,y,w,9,WOOD,4,WOOD_D,1);const pegs=[.12,.38,.64,.88].map(f=>x+w*f);pegs.forEach(px=>E(c,px,y+13,4,4,WOOD_D));
  R(c,pegs[0]-8,y+14,16,64,'#e39686',6);for(let i=0;i<4;i++)L(c,pegs[0]-7,y+26+i*13,pegs[0]+7,y+26+i*13,'#fff3e6',2);R(c,pegs[0]-9,y+74,18,6,'#e39686',2);
  R(c,pegs[1]-7,y+14,14,56,'#e8c06d',6);L(c,pegs[1],y+18,pegs[1],y+66,'#f5dca0',2);
  c.beginPath();c.arc(pegs[2],y+34,15,Math.PI,0);c.fillStyle='#9fb9d8';c.fill();R(c,pegs[2]-16,y+32,32,7,'#c4d4e8',3);E(c,pegs[2],y+17,6,6,'#fff6ea');
  L(c,pegs[3],y+15,pegs[3],y+60,'#8b6b56',2.5);c.beginPath();c.arc(pegs[3]+5,y+60,5,0,Math.PI);c.strokeStyle='#8b6b56';c.stroke();P(c,[[pegs[3]-8,y+20],[pegs[3]+8,y+20],[pegs[3]+3,y+56],[pegs[3]-3,y+56]],'#b7cfb0');}
function security(c,p,items,port){
  const cam=port?[603,157]:[145,219];
  if(items.includes('camera')){L(c,cam[0]+2,cam[1]+22,cam[0]+17,cam[1]+11,'#b79b85',4);R(c,cam[0]+6,cam[1],39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,cam[0]+40,cam[1]+10,8,9,'#7a8992');E(c,cam[0]+41,cam[1]+10,4,5,'#b4d9df');E(c,cam[0]+12,cam[1]+5,2,2,'#90bd8b');}
  else{R(c,cam[0]+4,cam[1]+1,40,22,'#fff6e9',8,'#d5b59a',1);T(c,'♧',cam[0]+24,cam[1]+13,port?16:14,p.dark);}
  const bell=port?[217,318]:[1062,206];
  if(items.includes('bell')){L(c,bell[0],bell[1],bell[0],bell[1]+14,'#ac8f73',2);P(c,[[bell[0]-10,bell[1]+31],[bell[0]+10,bell[1]+31],[bell[0]+7,bell[1]+18],[bell[0]-7,bell[1]+18]],'#f0ce85');E(c,bell[0],bell[1]+33,4,3,'#d4ad64');}
  const lamp=port?[310,318]:[1062,392];
  if(items.includes('light')){const g=c.createRadialGradient(lamp[0],lamp[1]+12,0,lamp[0],lamp[1]+12,port?70:90);g.addColorStop(0,'#ffe1a45a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(lamp[0]-90,lamp[1]-80,180,180);
    R(c,lamp[0]-12,lamp[1]+4,24,30,'#fff0b8',8,'#b69b79',2);L(c,lamp[0],lamp[1]-4,lamp[0],lamp[1]+4,'#b69b79',3);}
}

/* -------------------------------------------------------------- the room */
function landRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,open=!!w.c?.open,items=w.c?.ops?.security?.items||[];
  E(c,605,724,503,30,'#cba88d22');R(c,85,165,1030,550,'#dcae8a',35);R(c,96,168,1008,533,'#fff9ee',30,'#d9ac90',3);
  c.save();c.beginPath();c.roundRect(108,179,984,280,[22,22,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(108,179,984,280);
  c.fillStyle='#f0d9b944';c.fillRect(108,179,984,112);for(let x=134;x<1092;x+=26)L(c,x,179,x,459,'#dcc2a052',1.2);c.restore();
  floorBoards(c,108,445,984,244,16);R(c,108,438,984,10,'#d8b08a',3);
  // Loft: beam, railing, the three room doors with hanging name plates.
  const fs=12;ROOMS.forEach(([name,tint],i)=>roomDoor(c,p,395+i*150,216,290,64,name,tint,fs,199,17,90));
  for(const bx of [470,620])lantern(c,bx,226,1,open);
  E(c,835,240,30,30,WOOD);E(c,835,240,24,24,'#d6e8ea');c.save();c.beginPath();c.arc(835,240,24,0,Math.PI*2);c.clip();E(c,835,262,30,10,'#b9d0c3');pine(c,822,262,30,'#6f9a7f');pine(c,846,264,24,'#5f8b71');c.restore();L(c,811,240,859,240,'#fbf3e6',3);
  gallery(c,292,1092,290);
  for(const [bx,k] of [[470,0],[620,1],[775,2],[1068,0]]){R(c,bx-22,250,44,13,'#b98a64',4);hydrangea(c,bx-10,246,9,HYD[k]);hydrangea(c,bx+10,247,8,HYD[(k+1)%3]);}
  // Ceiling beam (over everything on the wall).
  R(c,108,179,984,18,WOOD,[22,22,0,0]);R(c,108,193,984,4,WOOD_D,0);
  // Stairwell: little pine print, staircase to the loft, linen cubby under it.
  housePicture(c,128,262,56,40);
  stairs(c,118,450,292,292,8);
  linenCubby(c,228,372,58,70,items.includes('lock'));
  // Lower wall: notice board, coat rack, window, keys, calendar, fireplace.
  streetBoard(c,p,310,322);
  coatRack(c,392,322,100);
  bigWindow(c,512,320,206,108,t);
  keyBoard(c,p,732,322,76,70,3,2,9);
  calendar(c,p,818,322,82,80,w.words().evidence.toUpperCase(),10);
  fireplace(c,p,972,197,368,450,114,74,t,false);
  housePicture(c,944,300,56,46);
  R(c,898,442,150,24,'#dccdb7',8,'#c2b096',1.5);
  // Rug in front of the fire, doormat at the entrance.
  E(c,965,512,92,21,'#e8c4b5');E(c,965,512,80,16,'#f3dccf');for(let i=-3;i<=3;i++)E(c,965+i*22,512,4,4,'#d9a898');
  R(c,930,660,120,16,'#dcc39a',8,'#c4a67c',1);for(let x=942;x<1044;x+=10)L(c,x,663,x,673,'#caa97e',1);
  security(c,p,items,false);
  signBoard(c,p,370,64,460,106);
}
function portRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,open=!!w.c?.open,items=w.c?.ops?.security?.items||[];
  E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#dcae8a',31);R(c,29,117,642,724,'#fff9ed',26,'#d9ae91',3);
  c.save();c.beginPath();c.roundRect(40,139,620,380,[21,21,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(40,139,620,380);
  c.fillStyle='#f0d9b944';c.fillRect(40,139,620,162);for(let x=64;x<660;x+=24)L(c,x,139,x,519,'#dcc2a052',1.2);c.restore();
  floorBoards(c,40,506,620,323,15);R(c,40,500,620,10,'#d8b08a',3);
  // Loft with the three rooms.
  ROOMS.forEach(([name,tint],i)=>roomDoor(c,p,120+i*160,198,300,70,name,tint,16,162,28,122));
  for(const bx of [200,360])lantern(c,bx,222,1.15,open);
  gallery(c,40,528,300);
  for(const [bx,k] of [[200,0],[360,1],[480,2]]){R(c,bx-26,258,52,14,'#b98a64',4);hydrangea(c,bx-12,253,10,HYD[k]);hydrangea(c,bx+12,254,9,HYD[(k+1)%3]);}
  R(c,40,139,620,17,WOOD,[21,21,0,0]);R(c,40,152,620,4,WOOD_D,0);
  // Stairwell on the right: notice board above, linen cubby below.
  stairs(c,652,512,522,306,9);
  linenCubby(c,527,442,70,64,items.includes('lock'));
  streetBoard(c,p,548,186,1.6);
  // Lower wall: fireplace, window, keys and calendar.
  fireplace(c,p,130,316,420,512,164,86,t,true);
  housePicture(c,102,350,56,42);
  R(c,40,503,184,22,'#dccdb7',8,'#c2b096',1.5);
  bigWindow(c,230,332,160,136,t);
  keyBoard(c,p,405,336,105,74,3,2,16);
  calendar(c,p,405,420,105,84,w.words().evidence.toUpperCase(),16);
  E(c,135,566,96,20,'#e8c4b5');E(c,135,566,84,15,'#f3dccf');for(let i=-3;i<=3;i++)E(c,135+i*23,566,4,4,'#d9a898');
  R(c,465,818,128,16,'#dcc39a',8,'#c4a67c',1);for(let x=477;x<586;x+=10)L(c,x,821,x,831,'#caa97e',1);
  security(c,p,items,true);
  signBoard(c,p,135,30,430,106);
}

/* ------------------------------------------------------------- furniture */
/** Reception desk: check-in end (bell, guest book) and check-out tray. */
function desk(w,p,x0,x1,top,bottom,a,b,fs,port){const c=w.ctx,cx=(x0+x1)/2;
  E(c,cx,bottom,(x1-x0)/2+16,14,'#bb97781d');
  R(c,x0,top+16,x1-x0,bottom-top-16,'#d9ab80',12,'#b3845d',2);for(let x=x0+24;x<x1-10;x+=24)L(c,x,top+26,x,bottom-6,'#c4956b66',1.4);
  const pw=port?250:230,ph=port?34:30,py=top+16+(bottom-top-16-ph)/2;R(c,cx-pw/2,py,pw,ph,'#fff7e9',ph/2,'#c7ad90',2);T(c,'ấm áp như ở nhà',cx,py+ph/2+1,fit(c,'ấm áp như ở nhà',pw-60,fs),p.dark);heart(c,cx-pw/2+20,py+ph/2+5,.33,p.primary);heart(c,cx+pw/2-20,py+ph/2+5,.33,p.primary);
  R(c,x0-10,top,x1-x0+20,22,'#ecc9a2',10,'#b99476',2);R(c,x0-5,top+2,x1-x0+10,6,'#f6dcbc',3);
  // Check-in: bell and open guest book with a pen; a small hydrangea vase.
  P(c,[[a-58,top+4],[a-8,top+4],[a-4,top-12],[a-54,top-12]],'#fffaf0');P(c,[[a-6,top+4],[a+44,top+4],[a+40,top-12],[a-2,top-12]],'#fff6e6');L(c,a-7,top+4,a-5,top-12,'#d8c3a6',1.5);
  for(let i=0;i<3;i++){L(c,a-48,top-7+i*4,a-16,top-7+i*4,i?'#cdbfae':p.primary,1.2);L(c,a+4,top-7+i*4,a+34,top-7+i*4,'#cdbfae',1.2);}L(c,a+22,top-2,a+46,top-20,'#7c6a8e',2.5);
  E(c,a+72,top+3,14,4,'#c7a15f');c.beginPath();c.arc(a+72,top+1,12,Math.PI,0);c.fillStyle='#f2cd73';c.fill();E(c,a+68,top-4,4,3,'#fff4c8');R(c,a+70,top-15,4,5,'#d5ac5a',2);
  R(c,a-100,top-20,18,22,'#e3f0ee',6,'#b8cfcc',1);hydrangea(c,a-91,top-28,11,HYD[0]);
  // Check-out: woven tray with a bill and a returned key.
  R(c,b-40,top-6,80,12,'#e6cc9c',5,'#c2a06c',1.2);for(let x=b-34;x<b+36;x+=8)L(c,x,top-5,x,top+5,'#d4b47f',1);
  R(c,b-30,top-22,30,22,'#fffdf5',2,'#d8cbb5',1);for(let i=0;i<3;i++)L(c,b-26,top-16+i*5,b-6,top-16+i*5,i===2?p.primary:'#c7bcb0',1.2);
  c.beginPath();c.arc(b+14,top-12,5,0,Math.PI*2);c.strokeStyle='#d0a651';c.lineWidth=2;c.stroke();L(c,b+19,top-12,b+32,top-12,'#d0a651',2.2);R(c,b+22,top-8,14,9,TAGS[1],3);
  // Little green desk lamp.
  R(c,b+56,top-3,22,5,'#6e8f69',2);L(c,b+67,top-3,b+67,top-26,'#8a7a62',2);P(c,[[b+54,top-24],[b+80,top-24],[b+74,top-36],[b+60,top-36]],'#7ea277');
  if(w.c?.open){const g=c.createRadialGradient(b+67,top-20,0,b+67,top-20,40);g.addColorStop(0,'#fff0b855');g.addColorStop(1,'#fff0b800');c.fillStyle=g;c.fillRect(b+27,top-60,80,80);}
  if((w.c?.ops?.equipment?.condition??100)<100){R(c,x0+10,top+3,port?112:90,port?22:15,'#f7d995',4);T(c,'CẦN KIỂM',x0+10+(port?56:45),top+(port?14.5:11),port?16:9,'#94643d');}
}
function armchair(c,cx,bottom,s){c.save();c.translate(cx,bottom);c.scale(s,s);
  E(c,0,0,44,8,'#8b73531c');L(c,-30,-12,-32,0,'#9a7457',5);L(c,30,-12,32,0,'#9a7457',5);
  R(c,-36,-78,72,52,'#c9d8b8',24,'#9fb58f',2);R(c,-28,-70,56,34,'#d8e4c9',16);
  R(c,-38,-34,76,24,'#bfd0ad',10,'#9fb58f',2);R(c,-46,-50,18,38,'#c9d8b8',9,'#9fb58f',2);R(c,28,-50,18,38,'#c9d8b8',9,'#9fb58f',2);
  R(c,-30,-40,60,12,'#e1ebd3',6);
  // Knitted blanket over the arm and a heart cushion.
  P(c,[[18,-60],[40,-54],[44,-12],[26,-16]],'#f2c7b4');for(let i=0;i<3;i++)L(c,21+i*2,-50+i*12,41+i,-44+i*12,'#e4a996',2);
  R(c,-18,-66,26,22,'#f7e6d4',8,'#e2c3a8',1);heart(c,-5,-52,.25,'#e39aa9');c.restore();}
function luggage(c,x,bottom,s){c.save();c.translate(x,bottom);c.scale(s,s);
  E(c,0,0,26,5,'#8b73531c');R(c,-18,-58,36,54,'#b6c9e3',8,'#8ea4c4',1.6);L(c,-8,-54,-8,-8,'#a4b9d8',2);L(c,8,-54,8,-8,'#a4b9d8',2);
  R(c,-7,-70,14,14,'transparent',4,'#8ea4c4',3);E(c,-11,-2,4,4,'#6f7c8c');E(c,11,-2,4,4,'#6f7c8c');
  R(c,-4,-40,16,12,'#fff4d6',3,'#d9b58a',1);heart(c,-10,-18,.28,'#efb5ca');
  R(c,-44,-30,30,28,'#e8cc95',10,'#c7a466',1.5);L(c,-40,-26,-18,-26,'#d6b271',2);c.beginPath();c.arc(-29,-30,9,Math.PI,0);c.strokeStyle='#b8925a';c.lineWidth=2.5;c.stroke();c.restore();}
function doorSign(c,p,cx,bottom,open,words,port){const bw=port?140:112,bh=port?40:32,fs=port?16:12;
  L(c,cx-bw*.3,bottom,cx-bw*.22,bottom-bh-18,'#b08a66',4);L(c,cx+bw*.3,bottom,cx+bw*.22,bottom-bh-18,'#b08a66',4);
  R(c,cx-bw/2,bottom-bh-24,bw,bh,'#fff8e8',13,'#c6a182',2);T(c,open?words.open_sign:words.closed_sign,cx,bottom-bh/2-23,fit(c,open?words.open_sign:words.closed_sign,bw-16,fs),p.dark);
  if(open)E(c,cx-bw/2+11,bottom-bh/2-24,3.5,3.5,'#7fb28a');pot(c,cx-bw/2-10,bottom+2,port?.9:.75,HYD[1]);}
function ledgerDesk(c,p,x,y,wd,fs){ // top-left of the desk top, desk width wd; returns nothing
  E(c,x+wd/2,y+62,wd/2+8,6,'#8b73531c');L(c,x+8,y+14,x+8,y+60,'#a87a57',5);L(c,x+wd-8,y+14,x+wd-8,y+60,'#a87a57',5);
  R(c,x+4,y+12,wd-8,fs+16,'#d9ab80',6,'#b3845d',1.5);
  R(c,x-4,y,wd+8,14,'#ecc9a2',6,'#b99476',1.5);
  P(c,[[x+wd*.2,y+2],[x+wd*.48,y+2],[x+wd*.48,y-12],[x+wd*.22,y-12]],'#fffaf0');P(c,[[x+wd*.5,y+2],[x+wd*.78,y+2],[x+wd*.76,y-12],[x+wd*.5,y-12]],'#fff6e6');
  for(let i=0;i<2;i++){L(c,x+wd*.25,y-7+i*4,x+wd*.44,y-7+i*4,'#cdbfae',1.1);L(c,x+wd*.54,y-7+i*4,x+wd*.72,y-7+i*4,'#cdbfae',1.1);}
  R(c,x+wd*.84-5,y-10,10,10,'#f3d590',3,'#c8a667',1);L(c,x+wd*.84,y-10,x+wd*.84,y-20,'#9e8264',2);E(c,x+wd*.84,y-24,6,6,'#fff0b8');}

function landProps(w,p){const c=w.ctx,wd=w.words(),tier=w.c?.ops?.property?.tier||'cozy',open=!!w.c?.open,out=[];
  out.push([586,()=>desk(w,p,520,880,478,586,610,790,13,false)]);
  out.push([562,()=>armchair(c,1040,562,1)]);
  out.push([620,()=>{ledgerDesk(c,p,140,560,110,11);T(c,wd.ledger,195,590,fit(c,wd.ledger,90,11),p.dark);}]);
  out.push([668,()=>doorSign(c,p,988,668,open,wd,false)]);
  out.push([675,()=>luggage(c,1068,675,1)]);
  if(tier!=='cozy')out.push([545,()=>bench(c,p,300,420,545,false,tier==='garden')]);
  if(tier==='garden')for(const [x,y] of PLAN.land.garden)out.push([y+2,()=>pot(c,x,y,.8,HYD[(x/5|0)%3])]);
  return out;}
function portProps(w,p){const c=w.ctx,wd=w.words(),tier=w.c?.ops?.property?.tier||'cozy',open=!!w.c?.open,out=[];
  out.push([655,()=>desk(w,p,215,515,570,655,290,440,16,true)]);
  out.push([652,()=>armchair(c,98,652,.95)]);
  out.push([746,()=>{ledgerDesk(c,p,556,688,98,16);T(c,wd.ledger,605,719,fit(c,wd.ledger,84,16),p.dark);}]);
  out.push([808,()=>doorSign(c,p,527,808,open,wd,true)]);
  out.push([800,()=>luggage(c,628,800,.92)]);
  if(tier!=='cozy')out.push([815,()=>bench(c,p,70,190,815,true,tier==='garden')]);
  if(tier==='garden')for(const [x,y] of PLAN.port.garden)out.push([y+2,()=>pot(c,x,y,.75,HYD[(x/5|0)%3])]);
  return out;}
function bench(c,p,x0,x1,bottom,port,garden){const w=x1-x0;
  L(c,x0+12,bottom-18,x0+12,bottom,'#a87a57',6);L(c,x1-12,bottom-18,x1-12,bottom,'#a87a57',6);
  R(c,x0,bottom-58,w,26,WOOD,9,WOOD_D,1.5);R(c,x0-2,bottom-30,w+4,14,'#dcb08a',6,WOOD_D,1.5);
  R(c,x0+10,bottom-44,34,18,p.mint,8);R(c,x1-44,bottom-44,34,18,'#f2c7b4',8);
  T(c,'ngồi nghỉ nhé',x0+w/2,bottom-46,port?16:11,'#fff8ec');if(garden)hydrangea(c,x1-6,bottom-64,12,HYD[2]);}

export default {
  id:'lodging',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
