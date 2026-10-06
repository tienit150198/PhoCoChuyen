/** Ward scene (nurse, "Khoa Nội · Bệnh viện phường Lá Sen"): the nurses' end of a medical ward. The supply cart and
 * the medicine cabinet (warehouse), the bed board with the four beds' names (shelf), the handover clipboards on the
 * wall (evidence), the nurses' station (workbench = the computer and the charts, counter = the hand-rub bottle, the
 * phone and the call-bell panel), a hospital bed with an IV pole and its call light (property), the small desk of
 * paperwork (finance), a window onto the lotus pond and the ward door with its sign.
 * The walking plan is homestay's (scenes/lodging.js), like the nursery. Plan schema: see scenes/shop.js. */
import {R,E,L,T,fit,signBoard,streetBoard} from './kit.js';
import {PLAN} from './lodging.js';

export {PLAN};

const TEAL='#2f8a8a',TEAL_L='#cfeae7',MINT='#e3f4f1',STEEL='#9aa8b2',STEEL_D='#6f7d87',CREAM='#fbfaf6',RED='#d64545',WOOD='#c9a27e',WOOD_D='#9a7656';

/* ------------------------------------------------------------ small pieces */
function floorTiles(c,x,y,w,h,r){c.save();c.beginPath();c.roundRect(x,y,w,h,r);c.clip();
  for(let row=0,yy=y;yy<y+h;row++,yy+=44)for(let col=0,xx=x;xx<x+w;col++,xx+=44){c.fillStyle=['#eef3f1','#e4ece9'][(row+col)%2];c.fillRect(xx,yy,44,44);}
  c.restore();}
/** A green cross on a white disc (the hospital's sign). */
function cross(c,x,y,s,col=TEAL){E(c,x,y,s,s,'#ffffff');R(c,x-s*.22,y-s*.62,s*.44,s*1.24,col,2);R(c,x-s*.62,y-s*.22,s*1.24,s*.44,col,2);}
/** The supply cart with drawers, a sharps box and a bottle of hand rub (warehouse). */
function supplyCart(c,x,y,w,h){E(c,x+w/2,y+h+4,w/2+6,5,'#5a6b7322');R(c,x,y,w,h,'#f4f7f8',8,STEEL_D,2);
  for(let i=0;i<3;i++){R(c,x+6,y+8+i*h/3.4,w-12,h/4,'#e3eaee',4,'#b9c5cc',1.2);R(c,x+w/2-8,y+8+i*h/3.4+h/8-2,16,4,STEEL,2);}
  R(c,x+4,y-16,26,16,'#f5d442',3,'#c9a524',1.2);T(c,'⚠',x+17,y-8,10,'#2f2a24');R(c,x+w-20,y-26,12,26,'#dff1ff',4,'#9fb7c9',1.2);R(c,x+w-18,y-32,8,7,TEAL,2);
  E(c,x+10,y+h+2,5,5,'#55606a');E(c,x+w-10,y+h+2,5,5,'#55606a');}
/** The bed board (shelf): four beds and their names, a red dot for the allergy band. */
function bedBoard(c,p,x,y,w,h,label,fs){R(c,x,y,w,h,'#ffffff',8,STEEL_D,2);R(c,x,y,w,22,TEAL,[8,8,0,0]);T(c,label,x+w/2,y+11,fit(c,label,w-10,fs),'#ffffff',800);
  for(let i=0;i<4;i++){const yy=y+30+i*(h-36)/4;R(c,x+6,yy,w-12,(h-36)/4-4,i%2?'#f1f6f5':'#e8f2f0',4);T(c,`G${[3,5,6,8][i]}`,x+16,yy+(h-36)/8-2,10,p.dark,800);
    L(c,x+28,yy+(h-36)/8-2,x+w-18,yy+(h-36)/8-2,'#9db6b2',2);if(i!==1)E(c,x+w-12,yy+(h-36)/8-2,3.5,3.5,RED);}}
/** The handover clipboards on the wall (evidence). */
function clipboards(c,p,x,y,w,h){for(const [dx,rot] of [[0,-.05],[w*.5,.04]]){c.save();c.translate(x+dx+w*.24,y+h/2);c.rotate(rot);
    R(c,-w*.22,-h/2,w*.44,h,WOOD,4,WOOD_D,1.5);R(c,-w*.18,-h/2+8,w*.36,h-14,'#ffffff',2);R(c,-w*.08,-h/2-4,w*.16,9,STEEL,3);
    for(let i=0;i<4;i++)L(c,-w*.13,-h/2+18+i*9,w*.13,-h/2+18+i*9,'#c4ccd0',1.2);c.restore();}
  T(c,'GIAO CA',x+w/2,y-9,fit(c,'GIAO CA',w,10),p.dark,800);}
/** The window onto the hospital garden and its lotus pond. */
function pondWindow(c,x,y,w,h,t){R(c,x-8,y-8,w+16,h+16,'#9fbdb8',10,'#6f918b',2);
  c.save();c.beginPath();c.roundRect(x,y,w,h,6);c.clip();
  const g=c.createLinearGradient(0,y,0,y+h);g.addColorStop(0,'#d6ecf3');g.addColorStop(1,'#f0f2e6');c.fillStyle=g;c.fillRect(x,y,w,h);
  E(c,x+w*.5,y+h*.92,w*.55,h*.22,'#9fcfc4');for(const [dx,s] of [[.3,1],[.55,.8],[.72,1.1]]){E(c,x+w*dx,y+h*.86,12*s,5*s,'#6fae7c');}
  const b=Math.sin(t*1.4)*1.5;E(c,x+w*.56,y+h*.74+b,5,7,'#f2a3b8');E(c,x+w*.36,y+h*.78-b,4,6,'#f6c1cf');
  R(c,x+w*.08,y+h*.3,w*.05,h*.6,'#8a6b52',2);E(c,x+w*.1,y+h*.26,w*.16,h*.2,'#7fae86');
  c.restore();L(c,x+w/2,y,x+w/2,y+h*.62,'#6f918b',4);L(c,x,y+h*.4,x+w,y+h*.4,'#6f918b',3);}
/** A hospital bed with rails, an IV pole and the call light over it (property). */
function bed(c,cx,top,bottom,w,t,ring){const y=top+(bottom-top)*.5;
  E(c,cx,bottom,w/2+12,7,'#5a6b731c');
  L(c,cx+w/2+14,bottom-4,cx+w/2+14,top+6,STEEL_D,3);L(c,cx+w/2+4,top+6,cx+w/2+24,top+6,STEEL_D,3);R(c,cx+w/2+6,top+10,16,26,'#e8f6ff',5,'#9fb7c9',1.5);
  L(c,cx+w/2+14,top+36,cx+w/2-6,y+6,'#b8cbd6',1.5);
  R(c,cx-w/2,y,w,(bottom-y)-18,'#ffffff',8,STEEL_D,2);R(c,cx-w/2+8,y+8,w*.28,18,'#e8f2f0',8);R(c,cx-w/2+w*.3,y+6,w*.66,(bottom-y)*.42,TEAL_L,8);
  R(c,cx-w/2-6,y-18,8,(bottom-y),STEEL,3);R(c,cx+w/2-2,y-6,8,(bottom-y)-12,STEEL,3);L(c,cx-w*.2,y+2,cx+w*.35,y+2,STEEL_D,3);
  E(c,cx-w/2+8,bottom-8,6,6,'#55606a');E(c,cx+w/2-8,bottom-8,6,6,'#55606a');
  const on=ring&&Math.floor(t*2)%2===0;E(c,cx-w*.1,top+4,10,6,on?RED:'#e9b5b5');if(on){c.globalAlpha=.25;E(c,cx-w*.1,top+4,20,12,RED);c.globalAlpha=1;}}
/** The nurses' station: the computer and the charts (workbench end), the hand rub, the phone and the bell panel (counter end). */
function station(w,p,x0,x1,top,bottom,a,b,fs,port){const c=w.ctx,t=w.reduced?0:w.time,cx=(x0+x1)/2;
  E(c,cx,bottom,(x1-x0)/2+16,14,'#5a6b731d');
  R(c,x0,top+16,x1-x0,bottom-top-16,'#e6f1ef',10,'#8fb0aa',2);for(let k=1;k<4;k++)L(c,x0+(x1-x0)*k/4,top+22,x0+(x1-x0)*k/4,bottom-6,'#c8dcd8',1.5);
  const pw=port?250:230,ph=port?34:30,py=top+16+(bottom-top-16-ph)/2+8;R(c,cx-pw/2,py,pw,ph,CREAM,ph/2,'#a9c6c1',2);
  const motto='đúng người · đúng thuốc · báo kịp';T(c,motto,cx,py+ph/2+1,fit(c,motto,pw-56,fs),p.dark);cross(c,cx-pw/2+18,py+ph/2,8);cross(c,cx+pw/2-18,py+ph/2,8);
  R(c,x0-10,top,x1-x0+20,22,'#f4f8f7',8,'#b9cbc7',2);
  // Computer, a stack of charts.
  R(c,a-34,top-62,56,40,'#3b4a52',5);R(c,a-30,top-58,48,32,'#bfe6e2',3);L(c,a-26,top-50,a+10,top-50,TEAL,2);L(c,a-26,top-42,a+2,top-42,TEAL,2);R(c,a-10,top-22,16,8,'#55606a',2);
  for(let i=0;i<3;i++)R(c,a+30,top-14-i*6,34,6,['#f7e6b5','#cfe3f4','#f6d2d2'][i],1.5,'#c4ccd0',1);
  // Hand rub, phone, bell panel.
  R(c,b-64,top-34,16,34,'#e8f6ff',5,'#9fb7c9',1.5);R(c,b-62,top-42,12,9,TEAL,2);
  R(c,b-30,top-18,34,18,'#55606a',5);R(c,b-26,top-26,26,10,'#6f7d87',5);
  R(c,b+18,top-46,54,44,'#ffffff',6,STEEL_D,1.5);for(let i=0;i<4;i++){const on=!w.reduced&&i===Math.floor(t*.7)%4;E(c,b+30+(i%2)*28,top-32+Math.floor(i/2)*16,5,5,on?RED:'#d7dfe3');}
}
function wallClock(c,x,y,r){E(c,x,y,r+3,r+3,TEAL);E(c,x,y,r,r,CREAM);for(let i=0;i<12;i++){const a=i*Math.PI/6;L(c,x+Math.cos(a)*r*.8,y+Math.sin(a)*r*.8,x+Math.cos(a)*r*.92,y+Math.sin(a)*r*.92,STEEL_D,1.5);}
  L(c,x,y,x,y-r*.6,'#3e3e44',2.5);L(c,x,y,x+r*.45,y+r*.1,'#3e3e44',2);}
function paperDesk(c,x,y,wd){E(c,x+wd/2,y+48,wd/2+8,6,'#5a6b731c');L(c,x+10,y+12,x+10,y+46,WOOD_D,5);L(c,x+wd-10,y+12,x+wd-10,y+46,WOOD_D,5);
  R(c,x-4,y,wd+8,14,WOOD,6,WOOD_D,1.5);R(c,x+wd*.1,y-12,wd*.36,12,'#ffffff',2,'#cfc4b5',1);R(c,x+wd*.52,y-16,wd*.3,16,'#f7e6b5',2,'#d9c58a',1);R(c,x+wd*.86,y-14,6,14,'#2f5d8a',1.5);}
function doorSign(c,p,cx,bottom,open,words,port){const bw=port?150:120,bh=port?40:32,fs=port?16:12;
  L(c,cx-bw*.3,bottom,cx-bw*.22,bottom-bh-18,STEEL_D,4);L(c,cx+bw*.3,bottom,cx+bw*.22,bottom-bh-18,STEEL_D,4);
  R(c,cx-bw/2,bottom-bh-24,bw,bh,CREAM,13,'#9fbdb8',2);const s=open?words.open_sign:words.closed_sign;T(c,s,cx,bottom-bh/2-23,fit(c,s,bw-20,fs),p.dark);
  if(open)E(c,cx-bw/2+11,bottom-bh/2-24,3.5,3.5,'#5fb38a');}
function wheelchair(c,x,bottom,s){c.save();c.translate(x,bottom);c.scale(s,s);E(c,0,0,30,5,'#5a6b731c');
  c.beginPath();c.arc(-6,-16,16,0,Math.PI*2);c.strokeStyle=STEEL_D;c.lineWidth=3;c.stroke();E(c,18,-4,4,4,STEEL_D);
  R(c,-14,-44,26,6,TEAL,3);R(c,-16,-70,6,30,TEAL,3);L(c,-6,-38,18,-8,STEEL,3);c.restore();}
function security(c,p,items,port){
  const cam=port?[603,157]:[145,219];
  if(items.includes('camera')){L(c,cam[0]+2,cam[1]+22,cam[0]+17,cam[1]+11,'#9aa8b2',4);R(c,cam[0]+6,cam[1],39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,cam[0]+40,cam[1]+10,8,9,'#7a8992');E(c,cam[0]+41,cam[1]+10,4,5,'#b4d9df');}
  const lamp=port?[310,318]:[1062,392];
  if(items.includes('light')){R(c,lamp[0]-12,lamp[1]+4,24,30,'#fff0b8',8,'#b69b79',2);L(c,lamp[0],lamp[1]-4,lamp[0],lamp[1]+4,'#b69b79',3);}
  if(items.includes('lock')){const lk=port?[560,470]:[262,420];R(c,lk[0],lk[1],16,18,'#d8c596',4,'#a09675',1.2);}
}
const ringing=w=>!!(w.c?.tasks||[]).some(t=>t.kind==='bell'&&!['completed','cancelled','referred'].includes(t.status));

/* -------------------------------------------------------------- the room */
function landRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words();
  E(c,605,724,503,30,'#9fb0aa22');R(c,85,165,1030,550,'#9fbdb8',35);R(c,96,168,1008,533,'#fbfdfc',30,'#a9c6c1',3);
  c.save();c.beginPath();c.roundRect(108,179,984,280,[22,22,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(108,179,984,280);
  c.fillStyle='#e3f4f166';c.fillRect(108,179,984,140);R(c,108,380,984,6,'#bfdcd7',0);R(c,108,386,984,4,TEAL,0);c.restore();
  floorTiles(c,108,445,984,244,16);R(c,108,438,984,10,'#c8dcd8',3);
  // The corridor through the glass partition, a curtain rail.
  R(c,292,214,800,74,'#eaf3f1',[8,8,0,0],'#b9cbc7',1.5);for(let x=312;x<1080;x+=120){R(c,x,226,92,50,'#f7fbfa',4,'#cfe0dc',1);}
  for(const x of [520,690])cross(c,x,251,12);
  L(c,292,300,1092,300,STEEL_D,4);for(let x=300;x<1088;x+=36)E(c,x,300,3,3,STEEL);
  R(c,108,179,984,18,TEAL,[22,22,0,0]);
  supplyCart(c,206,384,90,56);
  streetBoard(c,p,310,322);
  wallClock(c,440,350,24);
  pondWindow(c,512,320,206,108,t);
  bedBoard(c,p,730,312,86,128,wd.shelf.toUpperCase(),10);
  clipboards(c,p,822,334,76,62);
  bed(c,972,226,450,128,t,ringing(w));
  R(c,930,660,120,16,'#cfe0dc',8,'#a9c6c1',1);
  security(c,p,items,false);
  signBoard(c,p,370,64,460,106);
}
function portRoom(w,p){const c=w.ctx,t=w.reduced?0:w.time,items=w.c?.ops?.security?.items||[],wd=w.words();
  E(c,350,857,324,23,'#9fb0aa22');R(c,22,114,656,738,'#9fbdb8',31);R(c,29,117,642,724,'#fbfdfc',26,'#a9c6c1',3);
  c.save();c.beginPath();c.roundRect(40,139,620,380,[21,21,0,0]);c.clip();c.fillStyle=p.wall;c.fillRect(40,139,620,380);c.fillStyle='#e3f4f166';c.fillRect(40,139,620,170);c.restore();
  floorTiles(c,40,506,620,323,15);R(c,40,500,620,10,'#c8dcd8',3);
  R(c,40,196,488,90,'#eaf3f1',[8,8,0,0],'#b9cbc7',1.5);for(let x=56;x<520;x+=116)R(c,x,208,96,64,'#f7fbfa',4,'#cfe0dc',1);
  cross(c,290,240,14);L(c,40,300,528,300,STEEL_D,4);
  R(c,40,139,620,17,TEAL,[21,21,0,0]);
  supplyCart(c,520,446,86,58);
  streetBoard(c,p,548,186,1.6);
  bed(c,130,318,512,150,t,ringing(w));
  pondWindow(c,230,332,160,136,t);
  bedBoard(c,p,405,330,105,170,wd.shelf.toUpperCase(),14);
  R(c,465,818,128,16,'#cfe0dc',8,'#a9c6c1',1);
  security(c,p,items,true);
  signBoard(c,p,135,30,430,106);
}

function landProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([586,()=>station(w,p,520,880,478,586,610,790,13,false)]);
  out.push([562,()=>wheelchair(c,1040,562,1)]);
  out.push([620,()=>{paperDesk(c,140,572,110);T(c,wd.ledger,195,604,fit(c,wd.ledger,90,11),p.dark);}]);
  out.push([668,()=>doorSign(c,p,988,668,open,wd,false)]);
  return out;}
function portProps(w,p){const c=w.ctx,wd=w.words(),open=!!w.c?.open,out=[];
  out.push([655,()=>station(w,p,215,515,570,655,290,440,16,true)]);
  out.push([652,()=>wheelchair(c,98,652,.95)]);
  out.push([746,()=>{paperDesk(c,556,700,98);T(c,wd.ledger,605,731,fit(c,wd.ledger,84,16),p.dark);}]);
  out.push([808,()=>doorSign(c,p,527,808,open,wd,true)]);
  return out;}

export default {
  id:'ward',
  plan:PLAN,
  room(w,p){if(w.isPortrait())portRoom(w,p);else landRoom(w,p);},
  props(w,p){return w.isPortrait()?portProps(w,p):landProps(w,p);},
};
