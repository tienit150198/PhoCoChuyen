/** Office scene kind: a bookkeeping corner (accounting), a company finance
 * room (corp_accounting), a payroll service (tax_payroll), a group HQ
 * (group_accounting) and a support desk (customer_care).
 *
 * Back wall, left → right: security camera and "CHUYỆN PHỐ" board over a
 * filing cabinet (warehouse), a shelf of binders (shelf), city windows with
 * Mướp on the sill, a whiteboard / queue screen / deadline calendar, the
 * originals table (evidence), the glass-walled manager room (counter) and
 * the entrance door with its open/closed sign (door). On the floor: a row of
 * desks with monitors, keyboards and chairs (your own desk is the
 * workbench), the expense desk (finance), a photocopier and a water cooler.
 * Portrait moves the manager room to the left and the windows up into a
 * ribbon so everything stays large on a phone. PLAN schema: see shop.js.
 */
import {R,E,L,T,P,fit,heart,bloom,plantAt,signBoard,streetBoard} from './kit.js';
import {t as tr} from '../v4/i18n.js';

const FONT='"Trebuchet MS", "Segoe UI", sans-serif';

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

// Drawing geometry that goes with each plan (scene pixels).
const G={
 land:{wall:[108,179,984,268],floor:[108,445,984,244],sign:[370,60,460,104],camera:[150,197],board:[140,224],
   cabinet:[132,336,84,192],shelf:[234,232,170,198],win:[416,212,194,206],clock:[681,207,17],wb:[622,238,118,108],
   cooler:[709,468],rack:[752,258,64,108],mgr:[824,196,154,250],door:[992,250,92,196],
   desk:{x0:232,x1:862,top:480,bottom:576,n:4,chairY:500},finance:[962,568,108],copier:[988,648,80],plant:[118,578,1.2],fs:12},
 port:{wall:[40,139,620,370],floor:[40,506,620,323],sign:[115,30,470,108],camera:[62,158],board:[382,404],
   cabinet:[50,404,62,142],shelf:[218,334,130,146],win:[216,182,438,98],clock:[569,308,15],wb:[358,302,112,76],
   evidence:[560,692,88],mgr:[48,186,158,322],door:[484,332,170,176],
   desk:{x0:150,x1:520,top:562,bottom:640,n:3,chairY:568},finance:[540,770,116],copier:[56,700,66],plant:[50,818,.72],fs:16},
};

// Per-career dressing.
const LOOK={
 accounting:{floor:'wood',desk:'wood',chair:'#e8b4a0',board:'cork',screen:'sheet'},
 corp_accounting:{floor:'plank',desk:'white',chair:null,board:'close',screen:'sheet'},
 tax_payroll:{floor:'birch',desk:'birch',chair:null,board:'calendar',screen:'pay'},
 group_accounting:{floor:'tile',desk:'white',chair:'#6f8193',board:'hq',screen:'chart',tall:true},
 customer_care:{floor:'carpet',desk:'white',chair:null,board:'queue',screen:'chat'},
};
const LOGO=['#2f6f9f','#3f8f6b','#d28a5a','#9b7cc0'];
const BINDERS=['#eeb8c7','#a9d6c6','#b6c9e3','#e8cc95','#c9b5dc','#f6d8c1'];

const hex2=n=>Math.max(0,Math.min(255,Math.round(n))).toString(16).padStart(2,'0');
/** Blend two #rrggbb colours. */
const mix=(a,b,t)=>{const p=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));const A=p(a),B=p(b);return '#'+A.map((v,i)=>hex2(v+(B[i]-v)*t)).join('');};
/** #rrggbb with alpha. */
const A=(h,a)=>h.slice(0,7)+hex2(a*255);
const look=w=>LOOK[w.career]||LOOK.corp_accounting;
const port=w=>w.isPortrait();

/* ------------------------------------------------------------ Wall pieces */
function shell(c,p,g,lk,portrait){
  const [wx,wy,ww,wh]=g.wall,[fx,fy,fw,fh]=g.floor;
  if(portrait){E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#e1b594',31);R(c,29,117,642,724,'#fff9ed',26,'#d9ae91',3);}
  else{E(c,605,724,503,30,'#cba88d22');R(c,85,165,1030,550,'#e3b694',35);R(c,96,168,1008,533,'#fff9ee',30,'#d9ac90',3);}
  R(c,wx,wy,ww,wh,lk.tall?mix(p.wall,'#e3ecf3',.6):p.wall,portrait?21:22);
  // Cosy wood panelling (bookkeeping corner) or a soft painted band.
  if(lk.floor==='wood'){R(c,wx,fy-78,ww,78,'#f3dfc8',0);for(let x=wx+14;x<wx+ww-40;x+=58)R(c,x,fy-68,46,56,'#f8eadb',6,'#e4c8aa',1);R(c,wx,fy-82,ww,6,'#e2c09f',2);}
  else R(c,wx,fy-46,ww,46,mix(p.wall,p.light,.55),0);
  // Ceiling strip with panel lights.
  const ch=portrait?34:24;R(c,wx,wy,ww,ch,'#fbf6ee',portrait?21:22);R(c,wx,wy+ch-3,ww,3,'#eadcc8',1);
  const lights=portrait?[70,630]:[160,300,880,1040];
  for(const x of lights){R(c,x-34,wy+ch/2-5,68,10,'#fff3c8',5,'#e8d6a8',1);}
  // Floor.
  c.save();c.beginPath();c.roundRect(fx,fy,fw,fh,16);c.clip();
  if(lk.floor==='carpet'){const a=mix(p.light,'#ffffff',.35),b=mix(p.light,p.wall,.35);for(let x=fx;x<fx+fw;x+=62)for(let y=fy;y<fy+fh;y+=62){c.fillStyle=((x-fx)/62+(y-fy)/62)%2?a:b;c.fillRect(x,y,62,62);E(c,x+31,y+31,2,2,A(p.primary,.18));}}
  else if(lk.floor==='tile'){for(let x=fx;x<fx+fw;x+=96)for(let y=fy,r=0;y<fy+fh;y+=58,r++){c.fillStyle=((x-fx)/96+r)%2?'#f1efea':'#e8e5de';c.fillRect(x,y,96,58);}
    for(let i=0;i<5;i++){c.save();c.globalAlpha=.35;L(c,fx+80+i*(fw/5),fy+fh,fx+160+i*(fw/5),fy,'#ffffff',10);c.restore();}}
  else{const col={wood:['#f3dcc0','#eed4b5','#dcb994'],plank:['#f8eddd','#f3e5d1','#e3cdb1'],birch:['#f8efdc','#f2e5cc','#e0cba8']}[lk.floor];
    for(let y=fy,r=0;y<fy+fh;y+=30,r++){c.fillStyle=col[r%2];c.fillRect(fx,y,fw,30);L(c,fx,y,fx+fw,y,col[2],1);for(let x=fx+((r*67)%150);x<fx+fw;x+=150)L(c,x,y+3,x,y+27,col[2],1);}}
  c.restore();
  R(c,wx,fy-7,ww,9,'#e6cbad',3);
}
/** City windows with a skyline; `panes` mullions; sill at the bottom. */
function cityWindow(c,p,x,y,w,h,panes,tall){
  R(c,x-9,y-9,w+18,h+18,tall?'#b9c6cf':'#e0bf9f',16);R(c,x,y,w,h,'#d3ebf2',10);
  c.save();c.beginPath();c.roundRect(x,y,w,h,10);c.clip();
  R(c,x,y+h*.5,w,h*.5,'#e3f1ee',0);E(c,x+w*.8,y+h*.24,Math.min(w,h)*.09+4,Math.min(w,h)*.09+4,'#fff1c2');
  E(c,x+w*.25,y+h*.18,26,9,'#ffffffcc');E(c,x+w*.33,y+h*.14,16,9,'#ffffffcc');E(c,x+w*.62,y+h*.3,20,7,'#ffffffaa');
  const cols=['#bccfe2','#cbc5e4','#a9c8d8','#d4dcea','#bdd6d1'];
  for(let bx=x-8,i=0;bx<x+w;i++){const bw=20+(i*37)%24,bh=h*(tall?.42:.3)+((i*53)%40)/100*h*.45,top=y+h-bh;
    R(c,bx,top,bw,bh+8,cols[i%5],3);c.fillStyle='#f7f9fcb0';for(let wy=top+7;wy<y+h-8;wy+=10)for(let wx=bx+4;wx<bx+bw-5;wx+=7)c.fillRect(wx,wy,3,4);
    if(i%3===1)R(c,bx+bw/2-1,top-10,2,10,cols[i%5],1);bx+=bw+5;}
  for(let i=0;i<6;i++)E(c,x+i*w/5,y+h+4,w/9,h*.1+6,i%2?'#a8cdb0':'#b9d8b9');
  c.restore();
  for(let k=1;k<panes;k++)L(c,x+w*k/panes,y+2,x+w*k/panes,y+h-2,'#fffaf0',6);
  R(c,x,y,w,10,'#f6ecdb',6);for(let i=1;i<3;i++)L(c,x+4,y+3*i,x+w-4,y+3*i,'#e7d8c1',1);
  R(c,x-14,y+h+1,w+28,11,tall?'#aebbc4':'#d4a487',5);R(c,x-12,y+h+1,w+24,3,tall?'#d3dde3':'#e8c2a4',2);
}
function binderShelf(c,p,x,y,w,h,label,fs){
  R(c,x-4,y-20,w+8,h+28,'#dcb396',10,'#b78b6c',2);R(c,x+5,y+6,w-10,h-9,'#fff3e0',7);
  const th=fs+16;R(c,x+12,y-24-th/2,w-24,th,p.light,12,'#d9b7a1',1.5);T(c,label,x+w/2,y-24,fit(c,label,w-40,fs),p.dark);
  const rows=3,rh=(h-6)/rows;
  for(let r=0;r<rows;r++){const base=y+6+rh*(r+1)-6;let bx=x+12,i=0;
    while(bx<x+w-24){if((i+r*2)%6===4){// a binder leaning into a gap
        c.save();c.translate(bx+4,base);c.rotate(-.28);R(c,0,-(rh-18),14,rh-18,BINDERS[(i+r)%6],3,'#b89d97',1);c.restore();bx+=22;i++;continue;}
      const bw=13+(i*7+r*3)%6,bh=rh-14-((i+r)%3)*5,col=BINDERS[(i*2+r)%6];
      R(c,bx,base-bh,bw,bh,col,3,'#b89d97',1);R(c,bx+3,base-bh+6,bw-6,Math.min(16,bh*.35),'#fff8e8',2);E(c,bx+bw/2,base-9,2.5,2.5,'#ffffffb0');bx+=bw+2;i++;}
    R(c,x,base,w,9,'#d6a581',2);R(c,x+3,base-1,w-6,3,'#efcbaa',1);}
}
function clock(c,x,y,r,time,still){
  E(c,x,y+2,r+4,r+4,'#b0906e33');E(c,x,y,r+4,r+4,'#c9a585');E(c,x,y,r,r,'#fffaf0');
  for(let i=0;i<12;i++){const a=i*Math.PI/6;L(c,x+Math.cos(a)*r*.74,y+Math.sin(a)*r*.74,x+Math.cos(a)*r*.88,y+Math.sin(a)*r*.88,'#b89c86',i%3?1:2);}
  const m=still?Math.PI*1.35:time*.3,h=still?-Math.PI*.18:time*.025;
  L(c,x,y,x+Math.sin(h)*r*.48,y-Math.cos(h)*r*.48,'#7d6356',3);L(c,x,y,x+Math.sin(m)*r*.72,y-Math.cos(m)*r*.72,'#7d6356',2);E(c,x,y,2.5,2.5,'#cf839c');
}
/** Whiteboard slot: chart, cork board, deadline calendar, queue screen or HQ screen. */
function boardSlot(c,p,w,x,y,bw,bh,kind,fs){
  const on=!!w.c?.open,dark=mix(p.dark,'#2d3a44',.45);
  if(kind==='cork'){R(c,x-6,y-6,bw+12,bh+12,'#c79a74',8);R(c,x,y,bw,bh,'#e5c39b',5);
    for(let i=0;i<6;i++){c.fillStyle='#d4ae84';c.fillRect(x+8+(i*29)%(bw-16),y+6+(i*17)%(bh-12),3,3);}
    const notes=[[.08,.1,.36,.48,'#fffdf5'],[.52,.08,.38,.4,'#fff1c9'],[.12,.62,.3,.3,'#ffe3e8'],[.52,.56,.4,.36,'#fffdf5']];
    notes.forEach(([nx,ny,nw,nh,col],i)=>{c.save();c.translate(x+bw*(nx+nw/2),y+bh*(ny+nh/2));c.rotate([-.06,.05,.04,-.03][i]);R(c,-bw*nw/2,-bh*nh/2,bw*nw,bh*nh,col,3,'#d8c3a5',1);
      if(i===2)heart(c,0,4,.34,p.primary);else for(let k=0;k<3;k++)L(c,-bw*nw/2+6,-bh*nh/2+9+k*6,bw*nw/2-6-(k===2?10:0),-bh*nh/2+9+k*6,k?'#cbbcae':p.primary,1.5);
      E(c,0,-bh*nh/2+2,3,3,['#e57f7f','#7fb2e5','#8ccf8c','#e5c07f'][i]);c.restore();});
    return;}
  if(kind==='calendar'){R(c,x-4,y-4,bw+8,bh+8,'#c9b8a6',8);R(c,x,y,bw,bh,'#fffdf7',5);R(c,x,y,bw,fs+8,'#d9776f',5);R(c,x,y+fs,bw,8,'#d9776f',0);
    T(c,'HẠN NỘP',x+bw/2,y+(fs+8)/2+1,fit(c,'HẠN NỘP',bw-12,fs),'#fff8ef',800);
    const gy=y+fs+12,cw=(bw-12)/5,rh=(bh-fs-18)/3;
    for(let r=0;r<3;r++)for(let k=0;k<5;k++){const cx=x+6+k*cw+cw/2,cy=gy+r*rh+rh/2;E(c,cx,cy,2,2,'#d8cdbf');}
    for(const [r,k,n] of [[1,3,'20'],[2,4,'30']]){const cx=x+6+k*cw+cw/2,cy=gy+r*rh+rh/2;c.beginPath();c.ellipse(cx,cy,cw*.62,rh*.55,0,0,Math.PI*2);c.strokeStyle='#d9776f';c.lineWidth=2.5;c.stroke();T(c,n,cx,cy,Math.round(fs*.85),'#b4534b',800);}
    L(c,x+10,gy+rh*.5,x+6+cw*2.6,gy+rh*.5,A(p.primary,.6),5);
    return;}
  if(kind==='queue'||kind==='hq'){R(c,x-6,y-6,bw+12,bh+12,'#5d6770',10);R(c,x,y,bw,bh,on?dark:'#3d464e',6);
    if(!on){L(c,x+12,y+bh-12,x+bw*.4,y+12,'#ffffff22',6);return;}
    if(kind==='queue'){const waiting=(w.c?.tasks||[]).filter(t=>!['completed','referred','cancelled'].includes(t.status)).length;
      T(c,'HÀNG CHỜ',x+bw/2,y+fs*.9,fit(c,'HÀNG CHỜ',bw-14,fs),'#fff3d6',800);
      T(c,String(waiting).padStart(2,'0'),x+bw*.32,y+bh*.62,Math.round(fs*2),'#ffe29a',800);
      for(let i=0;i<3;i++){const ly=y+bh*.42+i*bh*.17;E(c,x+bw*.62,ly,4,4,i<Math.min(3,waiting)?'#7bd48f':'#6b7780');R(c,x+bw*.68,ly-3,bw*.22,6,'#ffffff40',3);}
      if(!w.reduced&&Math.sin(w.time*3)>0)E(c,x+bw-9,y+9,3,3,'#ff9d8f');}
    else{T(c,'HỢP NHẤT',x+bw/2,y+fs*.9,fit(c,'HỢP NHẤT',bw-14,fs),'#eaf3ff',800);
      const n=5,gw=(bw-24)/n;for(let i=0;i<n;i++){let top=y+bh-8;[.16,.12,.1,.08].forEach((f,k)=>{const hh=bh*f*(.7+((i*3+k)%4)*.15);R(c,x+12+i*gw+3,top-hh,gw-6,hh,LOGO[k],1);top-=hh;});}}
    return;}
  // Whiteboard with a chart (corp: month-end close).
  R(c,x-5,y-5,bw+10,bh+10,'#b9c3c9',8);R(c,x,y,bw,bh,'#fdfefe',5);
  T(c,'KHÓA SỔ',x+bw/2,y+fs*.9,fit(c,'KHÓA SỔ',bw-14,fs),p.dark,800);
  const base=y+bh-10,gw=(bw-30)/4;
  [.3,.45,.38,.6].forEach((f,i)=>R(c,x+14+i*gw,base-(bh-fs-24)*f,gw-8,(bh-fs-24)*f,[p.light,p.mint,p.light,p.primary][i],2,mix(p.primary,'#ffffff',.3),1));
  c.beginPath();[.35,.5,.45,.8].forEach((f,i)=>{const px=x+14+i*gw+gw/2-4,py=base-(bh-fs-24)*f-8;i?c.lineTo(px,py):c.moveTo(px,py);});c.strokeStyle='#d9776f';c.lineWidth=2;c.stroke();
  R(c,x+12,y+bh+3,bw-24,5,'#c8d0d4',2);R(c,x+20,y+bh+1,14,4,'#7fb2e5',2);R(c,x+38,y+bh+1,14,4,'#e57f7f',2);
}
/** Glass-walled manager room with a frosted name band. */
function bossRoom(c,p,x,y,w,h,label,fs,lk,deskAt){
  R(c,x-6,y-6,w+12,h+6,'#cdb9a6',10);R(c,x,y,w,h,mix(p.wall,'#e9dfd2',.55),6);
  // Inside: a window with blinds, a certificate, a big chair, a desk and a plant.
  const bx=x+w*.18,by=y+14,bw=w*.64,bh=h*.22;R(c,bx,by,bw,bh,'#d5ebf2',5);for(let i=1;i<6;i++)L(c,bx+2,by+i*bh/6,bx+bw-2,by+i*bh/6,'#f6efe3',2);
  const dx=x+w*deskAt,dy=y+h*.74;
  R(c,dx-20,dy-h*.2,40,h*.2+6,lk.tall?'#5d6f80':p.dark,13);R(c,dx-15,dy-h*.2+5,30,h*.12,'#ffffff26',9);
  R(c,dx-w*.34,dy,w*.68,9,'#c79a76',4);R(c,dx-w*.3,dy+9,w*.6,h*.16,'#dcb592',4);
  R(c,dx+w*.08,dy-24,26,19,'#5f6b75',4);R(c,dx+w*.08+3,dy-21,20,13,'#eaf4fb',2);R(c,dx+w*.08+10,dy-5,6,5,'#8f9aa3',1);
  R(c,dx-w*.22,dy-8,24,8,'#fff8e6',2,'#d6b995',1);
  plantAt(c,x+(deskAt>.55?w*.16:w*.86),y+h-6,h>300?.55:.45);
  // Glass, glare, door split and frosted band.
  R(c,x,y,w,h,'#dff1f84a',6);
  c.save();c.globalAlpha=.55;L(c,x+w*.08,y+h*.62,x+w*.3,y+h*.3,'#ffffff',7);L(c,x+w*.18,y+h*.64,x+w*.36,y+h*.38,'#ffffff',3);c.restore();
  const split=x+w*(deskAt>.55?.3:.66);L(c,split,y+2,split,y+h,'#b3c3cb',4);R(c,split+(deskAt>.55?-12:6),y+h*.56,6,28,'#9fb0b8',3);
  const band=y+h*.4,bh2=fs+14;R(c,x,band,w,bh2,'#ffffffc8',0);R(c,x,band,w,2,'#e3edf1',0);R(c,x,band+bh2-2,w,2,'#e3edf1',0);
  if(lk.tall)for(let i=0;i<4;i++){R(c,x+w/2-39+i*20,band-22,18,16,'#ffffffd0',4);E(c,x+w/2-30+i*20,band-14,5,5,LOGO[i]);}
  T(c,label,x+w/2,band+bh2/2,fit(c,label,w-16,fs),p.dark,800);
  c.beginPath();c.roundRect(x,y,w,h,6);c.strokeStyle='#b3c3cb';c.lineWidth=3;c.stroke();
}
function officeDoor(c,p,w,x,y,dw,dh,fs,double,signW,signAt=.3){
  const items=w.c?.ops?.security?.items||[],open=!!w.c?.open,words=w.words();
  R(c,x-8,y-10,dw+16,dh+10,'#c9a283',9);R(c,x-3,y-5,dw+6,dh+5,'#e8cdb0',6);
  const leaves=double?2:1,lw=dw/leaves;
  for(let k=0;k<leaves;k++){const lx=x+k*lw;R(c,lx+3,y+1,lw-6,dh-1,'#d6ecf2',4,'#a9bcc4',2);
    c.save();c.globalAlpha=.6;L(c,lx+10,y+dh*.5,lx+lw*.5,y+18,'#ffffff',5);c.restore();
    R(c,lx+7,y+dh-24,lw-14,18,'#eae1d3',3);R(c,double?(k?lx+9:lx+lw-15):lx+lw-17,y+dh*.52,6,30,'#b09a86',3);}
  // Open / closed sign hanging on the door.
  const txt=open?words.open_sign:words.closed_sign,sh=fs+18,sy=y+dh*signAt,cx=x+dw/2;
  L(c,cx-signW*.28,y+8,cx-signW*.22,sy,'#b99b80',1.5);L(c,cx+signW*.28,y+8,cx+signW*.22,sy,'#b99b80',1.5);E(c,cx,y+7,3,3,'#b99b80');
  R(c,cx-signW/2,sy,signW,sh,'#fff8e8',11,'#c6a182',2);E(c,cx-signW/2+13,sy+sh/2,5,5,open?'#6fae7c':'#c9b8a6');
  T(c,txt,cx+8,sy+sh/2,fit(c,txt,signW-34,fs,800),p.dark,800);
  R(c,x+6,y+dh+3,dw-12,8,A(p.primary,.35),4);
  if(items.includes('bell')){const bx=x+dw-8,by=y+4;L(c,bx,by-10,bx,by,'#ac8f73',2);P(c,[[bx-9,by+15],[bx+9,by+15],[bx+6,by+2],[bx-6,by+2]],'#f0ce85');E(c,bx,by+17,3.5,3,'#d4ad64');}
  if(items.includes('light')){const lx=x-22,ly=y+26,g=c.createRadialGradient(lx,ly+8,0,lx,ly+8,90);g.addColorStop(0,'#ffe1a455');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(lx-90,ly-82,180,180);
    R(c,lx-10,ly-6,20,26,'#fff0b8',7,'#b69b79',2);R(c,lx-3,ly-14,6,8,'#b69b79',2);}
}
function camera(c,p,x,y,has){
  if(has){L(c,x-16,y+8,x-4,y-1,'#b79b85',4);R(c,x-8,y-12,36,19,'#f5f2eb',7,'#a7aaa2',2);E(c,x+24,y-3,7,8,'#7a8992');E(c,x+25,y-3,3,4,'#b4d9df');E(c,x-2,y-7,2,2,'#90bd8b');}
  else{R(c,x-8,y-12,34,21,'#fff6e9',8,'#d5b59a',1);T(c,'♧',x+9,y-1,14,p.dark);}
}
/** Company-specific touches on the wall. */
function wallExtras(c,p,w,g,lk,portrait){
  if(w.career==='accounting'){// framed "sổ sạch" certificate and a hanging plant
    const [x,y]=portrait?[400,470]:[636,372];if(!portrait){R(c,x,y,52,40,'#d9b48c',5);R(c,x+5,y+5,42,30,'#fffaf0',3);heart(c,x+26,y+22,.3,p.primary);}
    if(!portrait){L(c,440,203,440,226,'#b79b85',1.5);E(c,440,234,16,9,'#e4b19a');for(let i=0;i<5;i++)E(c,428+i*6,242+(i%2)*10,6,12,i%2?'#a4c896':'#78ad91');}}
  if(w.career==='customer_care'){// phone line lights under the queue screen
    const [bx,by,bw,bh]=g.wb,on=!!w.c?.open,y=by+bh+(portrait?14:12);
    R(c,bx+8,y-8,bw-16,16,'#f7f3ec',8,'#cbbcaa',1);for(let i=0;i<4;i++)E(c,bx+22+i*(bw-44)/3,y,4,4,on&&(w.reduced||Math.sin(w.time*2+i*1.7)>-.3)?['#7bd48f','#f0c46a','#7bd48f','#e98f8f'][i]:'#d5ccc0');}
  if(w.career==='tax_payroll'&&!portrait){// a pinned payslip beside the calendar
    const x=636,y=372;c.save();c.translate(x+22,y+22);c.rotate(-.05);R(c,-22,-20,44,40,'#fffdf7',3,'#d6c8b5',1);T(c,'₫',-11,-7,13,p.dark,800);for(let k=0;k<3;k++)L(c,-2,-10+k*8,16,-10+k*8,'#c9bcad',1.5);R(c,-16,10,32,4,A(p.primary,.6),2);c.restore();}
}

/* ------------------------------------------------------------ Floor pieces */
function fileCabinet(c,p,w,x,y,cw,ch,fs){
  const items=w.c?.ops?.security?.items||[],label=w.words().store,drawers=ch>170?4:3;
  E(c,x+cw/2,y+ch+3,cw*.62,6,'#8b735320');
  R(c,x,y,cw,ch,'#e8dfd3',8,'#b9a58f',2);R(c,x+3,y+3,cw-6,7,'#f6efe5',4);
  const dh=(ch-18)/drawers;
  for(let i=0;i<drawers;i++){const dy=y+12+i*dh;R(c,x+6,dy,cw-12,dh-5,'#f5efe6',6,'#cdbba5',1.5);R(c,x+cw/2-11,dy+6,22,8,'#fffdf7',2,'#c8b39b',1);R(c,x+cw/2-10,dy+dh*.58,20,5,'#bda78f',3);}
  const tw=Math.max(cw+10,fs*4.4),th=fs+10;R(c,x+cw/2-tw/2,y-th-4,tw,th,p.light,9,'#d4b8a0',1.5);T(c,label,x+cw/2,y-4-th/2,fit(c,label,tw-10,fs),p.dark,800);
  if(items.includes('lock')){const lx=x+cw-16,ly=y+16;R(c,lx-7,ly,14,14,'#d8c596',4,'#a59470',1);c.beginPath();c.arc(lx,ly,5,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=2.5;c.stroke();}
}
function copier(c,p,w,x,y,cw,fs){
  const on=!!w.c?.open,worn=(w.c?.ops?.equipment?.condition??100)<100,h=cw*.95,top=y-h;
  E(c,x+cw/2,y+2,cw*.66,7,'#8b735320');
  R(c,x,top+16,cw,h-16,'#f2efe8',8,'#bdb5a8',2);R(c,x-3,top+6,cw+6,13,'#dcd6cc',5,'#b8afa2',1.5);R(c,x+5,top,cw-10,8,'#c9c2b7',4);
  R(c,x+cw*.52,top+22,cw*.4,13,'#e3ded4',3);R(c,x+cw*.55,top+25,cw*.2,7,on?'#bfe3cf':'#c9cfcb',2);E(c,x+cw*.85,top+28,2.5,2.5,on&&(w.reduced||Math.sin(w.time*2.4)>0)?'#6fcf8a':'#b9b3a9');
  R(c,x-14,top+30,16,6,'#e0d9ce',2);R(c,x-16,top+25,18,6,'#ffffff',1,'#d7cfc3',1);
  for(let k=0;k<2;k++){const dy=top+42+k*(h-50)/2;R(c,x+6,dy,cw-12,(h-50)/2-4,'#ebe6dd',4,'#cdc4b6',1);L(c,x+cw/2-9,dy+6,x+cw/2+9,dy+6,'#b5ab9d',2);}
  if(worn){const ty=top+h*.52;R(c,x+2,ty,cw-4,fs+6,'#f7d995',5,'#d9b56a',1);T(c,'CẦN KIỂM',x+cw/2,ty+(fs+6)/2,fit(c,'CẦN KIỂM',cw-10,fs,800),'#94643d',800);}
}
function cooler(c,x,y,s){
  E(c,x,y+2,20*s,5*s,'#8b735320');R(c,x-16*s,y-56*s,32*s,56*s,'#f3f1ec',6*s,'#c5bdb1',1.5);R(c,x-11*s,y-48*s,22*s,12*s,'#e7e2d9',3*s);
  E(c,x-5*s,y-42*s,2.6*s,3*s,'#e39a9a');E(c,x+5*s,y-42*s,2.6*s,3*s,'#8fb8d8');R(c,x-9*s,y-24*s,18*s,4*s,'#dcd5ca',2);
  R(c,x-5*s,y-63*s,10*s,8*s,'#9cc6dc',2);R(c,x-14*s,y-96*s,28*s,36*s,'#c4e3f2d8',11*s,'#9cc6dc',1.5);R(c,x-10*s,y-84*s,20*s,3*s,'#ffffff99',1);L(c,x-8*s,y-90*s,x-8*s,y-68*s,'#ffffffaa',2);
  R(c,x+18*s,y-38*s,7*s,12*s,'#fffdf7',1,'#d6cbbd',1);
}
function docTable(c,p,x,y,tw,fs,label){
  E(c,x+tw/2,y+2,tw*.62,5,'#8b735320');L(c,x+5,y-30,x+5,y,'#b58e70',4);L(c,x+tw-5,y-30,x+tw-5,y,'#b58e70',4);
  for(let k=0;k<3;k++){const ty=y-40-k*13;R(c,x+5,ty-7,tw-10,9,'#f3efe6',2,'#a9a39a',1.5);R(c,x+9,ty-11,tw-18,5,['#fffdf6','#fbe9c9','#e8f1f7'][k],1,'#d9cfbf',1);}
  L(c,x+8,y-64,x+8,y-38,'#a9a39a',1.5);L(c,x+tw-8,y-64,x+tw-8,y-38,'#a9a39a',1.5);
  R(c,x-4,y-38,tw+8,10,'#e2bb98',4,'#b99476',1.5);
  const lh=fs+6;R(c,x+2,y-28,tw-4,lh,'#fff7e9',4,'#d1b393',1);T(c,label,x+tw/2,y-28+lh/2,fit(c,label,tw-10,fs),p.dark,800);
  c.beginPath();c.arc(x+tw-10,y-80,7,0,Math.PI*2);c.strokeStyle='#a98f74';c.lineWidth=2.5;c.stroke();L(c,x+tw-5,y-75,x+tw+1,y-68,'#a98f74',3);
}
/** Wall-mounted sorter of original documents (landscape evidence). */
function trayRack(c,p,x,y,rw,rh,fs){
  const th=fs+10;R(c,x-4,y-th-4,rw+8,th,p.light,8,'#d4b8a0',1.5);T(c,'BẢN GỐC',x+rw/2,y-4-th/2,fit(c,'BẢN GỐC',rw-6,fs),p.dark,800);
  R(c,x,y,rw,rh,'#dcb396',8,'#b78b6c',2);R(c,x+5,y+5,rw-10,rh-10,'#fff3e0',5);
  const n=3,gap=(rh-10)/n;
  for(let k=0;k<n;k++){const ty=y+5+gap*(k+1)-6;
    for(let j=0;j<3;j++){c.save();c.translate(x+14+j*3,ty-4-j*3);c.rotate(-.05*j);R(c,0,-gap*.52,rw-30,gap*.52,['#fffdf6','#fbe9c9','#e8f1f7'][(j+k)%3],2,'#d9cfbf',1);c.restore();}
    R(c,x+4,ty,rw-8,7,'#d6a581',2);}
  c.beginPath();c.arc(x+rw-14,y+rh-20,7,0,Math.PI*2);c.strokeStyle='#a98f74';c.lineWidth=2.5;c.stroke();L(c,x+rw-9,y+rh-15,x+rw-4,y+rh-9,'#a98f74',3);
}
function ledgerDesk(c,p,x,y,dw,label,fs){
  const top=y-46;E(c,x+dw/2,y+3,dw*.58,6,'#8b735320');
  R(c,x,top+10,dw,y-top-10,'#d4b391',10);R(c,x-6,top,dw+12,14,'#f0d2ad',7);
  R(c,x+dw*.18,top-26,dw*.46,28,'#fff8e7',5,'#d9b596',1);L(c,x+dw*.41,top-25,x+dw*.41,top+1,'#d9b596',1.5);for(let k=0;k<3;k++){L(c,x+dw*.22,top-18+k*6,x+dw*.37,top-18+k*6,k?'#cdbcaa':p.primary,1.5);L(c,x+dw*.45,top-18+k*6,x+dw*.6,top-18+k*6,'#cdbcaa',1.5);}
  R(c,x+dw*.7,top-20,20,22,'#cfe0e6',3,'#9fb5bf',1);R(c,x+dw*.7+3,top-17,14,5,'#e8f6e9',1);for(let k=0;k<6;k++)E(c,x+dw*.7+5+(k%3)*5,top-7+Math.floor(k/3)*5,1.5,1.5,'#7f96a1');
  T(c,label,x+dw/2,top+(y-top)/2+6,fit(c,label,dw-12,fs,800),'#7c604e',800);
}
function sofa(c,p,[x0,,x1,y1],garden){
  const w=x1-x0,base=y1-4,col=p.mint,edge=mix(p.mint,'#6b5a4a',.25);
  E(c,x0+w/2,y1+2,w*.55,6,'#8b735322');L(c,x0+10,base-6,x0+10,y1,'#af8b6c',5);L(c,x1-10,base-6,x1-10,y1,'#af8b6c',5);
  R(c,x0+6,base-58,w-12,36,col,13,edge,1.5);R(c,x0,base-30,w,22,col,9,edge,1.5);R(c,x0-6,base-44,16,34,mix(col,'#6b5a4a',.08),8,edge,1.5);R(c,x1-10,base-44,16,34,mix(col,'#6b5a4a',.08),8,edge,1.5);
  R(c,x0+18,base-52,w/2-24,24,mix(col,'#ffffff',.35),9);R(c,x0+w/2+6,base-52,w/2-24,24,mix(col,'#ffffff',.35),9);heart(c,x0+w*.3,base-38,.3,p.primary);
  if(garden){bloom(c,x1-4,base-62,13,p.primary);bloom(c,x0+10,base-60,10,'#f3d590');}
}

/* ------------------------------------------------------------ Desk row */
function screen(c,p,x,base,s,on,style,mark){
  const sw=62*s,sh=42*s,top=base-15*s-sh;
  R(c,x-14*s,base-5*s,28*s,6*s,'#9aa3aa',3);R(c,x-4*s,base-17*s,8*s,14*s,'#aab3b9',2);
  R(c,x-sw/2,top,sw,sh,'#5f6b75',7*s);const ix=x-sw/2+4*s,iy=top+4*s,iw=sw-8*s,ih=sh-8*s;R(c,ix,iy,iw,ih,on?'#f6fbff':'#3f4a53',4*s);
  if(!on){L(c,ix+6,iy+ih-4,ix+iw*.45,iy+4,'#ffffff22',4);return;}
  if(style==='chat'){R(c,ix+4,iy+4,iw*.55,ih*.3,p.light,4);R(c,ix+iw*.4,iy+ih*.45,iw*.55,ih*.3,mix(p.primary,'#ffffff',.4),4);E(c,ix+8,iy+ih-5,2,2,p.primary);E(c,ix+14,iy+ih-5,2,2,p.primary);}
  else if(style==='chart'){for(let i=0;i<4;i++){const hh=ih*(.3+((i*37)%50)/100);R(c,ix+5+i*iw/4.4,iy+ih-hh-2,iw/6,hh,LOGO[i],1);}}
  else{for(let r=0;r<4;r++)L(c,ix+3,iy+4+r*ih/4.4,ix+iw-3,iy+4+r*ih/4.4,'#dbe5ec',1);for(let k=1;k<3;k++)L(c,ix+k*iw/3,iy+2,ix+k*iw/3,iy+ih-2,'#dbe5ec',1);
    R(c,ix+3,iy+3,iw-6,ih/5,style==='pay'?mix(p.primary,'#ffffff',.45):p.light,1);R(c,ix+iw*.55,iy+ih*.55,iw*.3,ih*.2,A(p.primary,.35),1);}
  if(mark)heart(c,x+sw/2-6,top+8,.22,p.primary);
}
function keyboard(c,x,y,s){R(c,x-22*s,y,44*s,7*s,'#f4f1ea',3,'#c8c0b4',1);for(let k=0;k<5;k++)L(c,x-17*s+k*8.5*s,y+2.5*s,x-13*s+k*8.5*s,y+2.5*s,'#d6cec2',1.5);R(c,x+26*s,y+1,9*s,6*s,'#eeeae2',3,'#c8c0b4',1);}
function mug(c,x,y,col){R(c,x-6,y-13,12,13,col,3,'#c9ad96',1);c.beginPath();c.arc(x+7,y-7,4,-Math.PI/2,Math.PI/2);c.strokeStyle='#c9ad96';c.lineWidth=2;c.stroke();}
/** Small desk item standing at (x, desk top y). */
function deskItem(c,p,kind,x,y,s,on){
  if(kind==='stamp'){R(c,x-10*s,y-6*s,20*s,6*s,'#e6a0a0',2);R(c,x-5*s,y-18*s,10*s,12*s,'#9b6f55',3);E(c,x,y-20*s,7*s,5*s,'#b98464');}
  else if(kind==='tray'){R(c,x-13*s,y-13*s,26*s,4*s,'#fffdf6',1,'#d9cfbf',1);R(c,x-14*s,y-10*s,28*s,10*s,'#f3efe6',2,'#a9a39a',1.5);L(c,x-5*s,y-5*s,x-1*s,y-2*s,'#6fae7c',2);L(c,x-1*s,y-2*s,x+7*s,y-8*s,'#6fae7c',2);}
  else if(kind==='folders'){['#c9b5dc','#a9d6c6','#e8cc95'].forEach((col,k)=>R(c,x-13*s+k,y-5*s-k*5*s,26*s,5*s,col,2,'#b8a89a',1));}
  else if(kind==='slips'){for(let k=0;k<3;k++){c.save();c.translate(x,y-3*s-k*3*s);c.rotate((k-1)*.08);R(c,-12*s,-3*s,24*s,6*s,'#fffdf7',1,'#d6c8b5',1);c.restore();}R(c,x-9*s,y-13*s,18*s,3*s,A(p.primary,.6),1);}
  else if(kind==='calc'){R(c,x-9*s,y-20*s,18*s,20*s,'#cfe0e6',3,'#9fb5bf',1);R(c,x-6*s,y-17*s,12*s,5*s,'#e8f6e9',1);for(let k=0;k<6;k++)E(c,x-4*s+(k%3)*4*s,y-8*s+Math.floor(k/3)*4*s,1.3*s,1.3*s,'#7f96a1');}
  else if(kind==='phone'){R(c,x-12*s,y-10*s,24*s,10*s,'#6f7f8e',4);R(c,x-14*s,y-16*s,28*s,7*s,'#5c6b78',4);E(c,x+7*s,y-5*s,2*s,2*s,on?'#7bd48f':'#c9c9c9');}
  else if(kind==='flag'){const i=Math.round(x)%4;E(c,x,y-2,7*s,2.5*s,'#b9aea2');L(c,x,y-2,x,y-34*s,'#a7998a',2);P(c,[[x,y-34*s],[x+18*s,y-28*s],[x,y-22*s]],LOGO[i]);}
  else if(kind==='lamp'){E(c,x,y-2,11*s,3*s,'#c9a585');L(c,x,y-3,x+8*s,y-26*s,'#c9a585',3);L(c,x+8*s,y-26*s,x+20*s,y-32*s,'#c9a585',3);P(c,[[x+12*s,y-36*s],[x+30*s,y-30*s],[x+24*s,y-20*s]],'#f5ddb1');}
  else if(kind==='books'){['#c98f8f','#8fb3c9','#c9b98f'].forEach((col,k)=>R(c,x-14*s+k*2,y-6*s-k*6*s,28*s,6*s,col,2,'#a88f7a',1));}
}
function deskRow(c,p,w,D,lk,portrait){
  const {x0,x1,top,bottom,n}=D,uw=(x1-x0)/n,on=!!w.c?.open,s=portrait?.9:1,care=w.career==='customer_care',hq=lk.tall;
  E(c,(x0+x1)/2,bottom+8,(x1-x0)/2+14,12,'#8b735320');
  if(w.career==='accounting'){cosyRow(c,p,w,D,portrait);return;}
  const C={white:['#f7f4ee','#cfc4b4','#ece5da','#b9b0a3'],birch:['#f1dcbf','#caa582','#e9cfae','#b8936f']}[lk.desk];
  if(care)for(let i=0;i<=n;i++){const dx=x0+i*uw;R(c,dx-6,top-58*s,12,62*s,p.mint,6,mix(p.mint,'#5d4f45',.22),1);}
  for(let i=0;i<n;i++){const ux=x0+i*uw;R(c,ux+10,top+14,uw-20,(bottom-top)*.56,C[2],6,C[1],1);L(c,ux+7,top+10,ux+7,bottom+6,C[3],5);L(c,ux+uw-7,top+10,ux+uw-7,bottom+6,C[3],5);}
  R(c,x0-6,top,x1-x0+12,15,C[0],6,C[1],1.5);R(c,x0,top+2,x1-x0,4,'#ffffff90',2);
  if(hq)for(let i=1;i<n;i++){const dx=x0+i*uw;R(c,dx-3,top-52*s,6,54*s,'#d8eef575',3,'#b8d3dc',1);}
  const kinds={corp_accounting:['stamp','tray','folders','stamp'],tax_payroll:['slips','calc','slips','calc'],group_accounting:['flag','flag','flag','flag'],customer_care:['phone','phone','phone','phone']}[w.career]||['folders','tray','folders','tray'];
  const work=workUnit(D);
  for(let i=0;i<n;i++){const ux=x0+i*uw,seat=ux+uw*.39,mx=ux+uw*.75;
    deskItem(c,p,kinds[i%kinds.length],ux+(portrait?17:21),top+2,s,on);
    keyboard(c,seat,top+2,s);
    if(hq){screen(c,p,mx-16*s,top+2,s*.72,on,'chart');screen(c,p,mx+18*s,top+2,s*.72,on,'sheet');}
    else screen(c,p,mx,top+2,s,on,lk.screen,i===work);
    if(care){const hx=x0+(i+1)*uw-12;c.beginPath();c.arc(hx,top-34*s,8*s,Math.PI,0);c.strokeStyle=p.dark;c.lineWidth=3;c.stroke();R(c,hx-10*s,top-35*s,5*s,10*s,p.primary,2);R(c,hx+5*s,top-35*s,5*s,10*s,p.primary,2);}
    if(w.career==='tax_payroll'&&i===work)mug(c,seat-30*s,top+2,p.light);}
}
function cosyRow(c,p,w,D,portrait){
  const {x0,x1,top,bottom,n}=D,uw=(x1-x0)/n,on=!!w.c?.open,s=portrait?.9:1,dEnd=x0+uw*2;
  // One warm wooden desk…
  R(c,x0+4,top+12,uw*.42,bottom-top-6,'#dcae86',6,'#b98e6a',1.5);for(let k=0;k<3;k++){const dy=top+18+k*(bottom-top-16)/3;R(c,x0+10,dy,uw*.42-12,(bottom-top-16)/3-5,'#e8c19c',4);E(c,x0+4+uw*.21,dy+8,3,3,'#b98e6a');}
  R(c,x0+uw*.46,top+12,dEnd-x0-uw*.46-6,(bottom-top)*.5,'#e8c19c',5,'#b98e6a',1);L(c,dEnd-8,top+10,dEnd-8,bottom+6,'#b98e6a',6);
  R(c,x0-6,top,dEnd-x0+8,15,'#e8bf98',6,'#b98e6a',1.5);R(c,x0,top+2,dEnd-x0-4,4,'#ffffff70',2);
  const seat=x0+uw*1.39,mx=x0+uw*1.75;
  deskItem(c,p,'lamp',x0+uw*.18,top+2,s,on);deskItem(c,p,'books',x0+uw*.55,top+2,s,on);deskItem(c,p,'calc',x0+uw*.85,top+2,s,on);
  keyboard(c,seat,top+2,s);screen(c,p,mx,top+2,s,on,'sheet',true);mug(c,dEnd-18,top+2,'#f3d6dc');
  // …and a low sideboard with ledgers, tea and a plant.
  const sx=dEnd+8,sw=x1-sx,st=top+18;
  R(c,sx,st+12,sw,bottom-st-6,'#dcae86',8,'#b98e6a',1.5);R(c,sx-4,st,sw+8,14,'#e8bf98',6,'#b98e6a',1.5);
  const doors=portrait?2:3;for(let k=0;k<doors;k++){const dx=sx+8+k*(sw-16)/doors;R(c,dx,st+20,(sw-16)/doors-6,bottom-st-26,'#e8c19c',5,'#c89f7c',1);E(c,dx+(sw-16)/doors-14,st+20+(bottom-st-26)/2,3,3,'#b98e6a');}
  let bx=sx+8;for(let i=0;i<(portrait?4:7);i++){const bh=(34+(i*7)%12)*s,bw=12*s;R(c,bx,st-bh,bw,bh,['#c98f8f','#8fb3c9','#c9b98f','#a9c7a0','#c2a8d4'][i%5],2,'#a88f7a',1);R(c,bx+2,st-bh+6,bw-4,4,'#fff5e2',1);bx+=bw+2;}
  if(!portrait){R(c,bx+14,st-26,30,26,'#fff8ef',8,'#d9c3ad',1);E(c,bx+29,st-28,8,3,'#e7d5c2');R(c,bx+48,st-12,10,12,'#fff8ef',3,'#d9c3ad',1);plantAt(c,x1-26,st+2,.5);}
  else plantAt(c,x1-20,st+2,.42);
}
/** Which desk is the player's own (the workbench). */
const workUnit=()=>1;
function chair(c,x,y,col,s=1){
  const rim=mix(col,'#4a3b30',.3);
  R(c,x-3*s,y-24*s,6*s,20*s,rim,2);R(c,x-28*s,y-30*s,11*s,8*s,rim,4);R(c,x+17*s,y-30*s,11*s,8*s,rim,4);
  R(c,x-23*s,y-58*s,46*s,36*s,col,14*s,rim,1.5);R(c,x-17*s,y-53*s,34*s,20*s,mix(col,'#ffffff',.32),10*s);L(c,x-12*s,y-27*s,x+12*s,y-27*s,mix(col,'#ffffff',.2),2);
}
/** Headsets on hired staff at the support desk (drawn over the sprite). */
function staffHeadsets(w,p){
  const c=w.ctx,out=[];
  (w.c?.ops?.staff||[]).filter(e=>e.status==='hired').forEach((e,i)=>{const pos=w.staffPosition(i,e),pt=w.project(pos.x,pos.y),n=e.avatar??(Number(String(e.id).slice(-2))||0);
    out.push([pt.y+.02,()=>{const bob=w.reduced?0:Math.sin(w.time*(pos.moving?7:1.8)+n)*(pos.moving?2:1);c.save();c.translate(pt.x,pt.y+bob);c.scale(1.08,1.08);
      c.beginPath();c.arc(0,-84,33,Math.PI*1.05,Math.PI*1.95);c.strokeStyle=p.dark;c.lineWidth=4;c.stroke();R(c,-37,-84,9,16,p.primary,4);R(c,28,-84,9,16,p.primary,4);L(c,-32,-70,-16,-63,p.dark,2);E(c,-15,-63,2.5,2.5,p.dark);c.restore();}]);});
  return out;
}

/* ------------------------------------------------------------ Sign */
function officeSign(c,p,[x,y,w,h],portrait){
  if(!portrait){signBoard(c,p,x,y,w,h);return;}
  // Phone: same board, but the subtitle wraps at a readable size.
  signBoard(c,{...p,sub:''},x,y,w,h);
  const full=String(tr(p.sub||''));if(!full)return;
  const max=w-116,cx=x+w/2+20;c.font=`700 16px ${FONT}`;
  const wrap=s=>{const lines=[];let cur='';for(const word of s.split(/\s+/)){const next=cur?cur+' '+word:word;if(cur&&c.measureText(next).width>max){lines.push(cur);cur=word;}else cur=next;}if(cur)lines.push(cur);return lines;};
  let lines=wrap(full);if(lines.length>2)lines=wrap(full.split(' · ')[0]);
  if(lines.length>2)lines=[lines[0]+'…'];
  if(lines.length===1)T(c,lines[0],cx,y+h-28,fit(c,lines[0],max,16),p.dark);
  else lines.forEach((l,i)=>T(c,l,cx,y+h-38+i*19,fit(c,l,max,16),p.dark));
}

/* ------------------------------------------------------------ Hooks */
function room(w,p){
  const c=w.ctx,portrait=port(w),g=portrait?G.port:G.land,lk=look(w),words=w.words(),fs=g.fs,items=w.c?.ops?.security?.items||[];
  shell(c,p,g,lk,portrait);
  const boss=w.career==='customer_care'?'TRƯỞNG CA':'TRƯỞNG PHÒNG';
  if(portrait){
    const [wx,wy,ww,wh]=g.win;cityWindow(c,p,wx,lk.tall?wy-6:wy,ww,lk.tall?wh+6:wh,3,lk.tall);
    bossRoom(c,p,...g.mgr,boss,17,lk,.62);
    officeDoor(c,p,w,...g.door,17,true,176,.07);
    binderShelf(c,p,...g.shelf,words.shelf,16);
    boardSlot(c,p,w,...g.wb,lk.board,16);
    clock(c,...g.clock,w.time,w.reduced);
    streetBoard(c,p,...g.board,1.25);
    camera(c,p,...g.camera,items.includes('camera'));
  }else{
    const [wx,wy,ww,wh]=g.win;cityWindow(c,p,wx,lk.tall?wy-20:wy,ww,lk.tall?wh+20:wh,2,lk.tall);
    bossRoom(c,p,...g.mgr,boss,14,lk,.5);
    officeDoor(c,p,w,...g.door,11,false,114);
    binderShelf(c,p,...g.shelf,words.shelf,13);
    boardSlot(c,p,w,...g.wb,lk.board,13);
    clock(c,...g.clock,w.time,w.reduced);
    streetBoard(c,p,...g.board);
    camera(c,p,...g.camera,items.includes('camera'));
    trayRack(c,p,...g.rack,12);
  }
  wallExtras(c,p,w,g,lk,portrait);
  officeSign(c,p,g.sign,portrait);
}
function props(w,p){
  const c=w.ctx,portrait=port(w),g=portrait?G.port:G.land,pl=w.plan(),lk=look(w),words=w.words(),fs=g.fs,tier=w.c?.ops?.property?.tier||'cozy',out=[];
  const D=g.desk,uw=(D.x1-D.x0)/D.n,chairCol=lk.chair||mix(p.primary,'#ffffff',.15);
  out.push([pl.line,()=>deskRow(c,p,w,D,lk,portrait)]);
  const seats=w.career==='accounting'?[D.x0+uw*1.39]:Array.from({length:D.n},(_,i)=>D.x0+i*uw+uw*.39);
  for(const x of seats)out.push([D.chairY,()=>chair(c,x,D.chairY,chairCol,portrait?.92:1)]);
  const [cx,cy,cw,ch]=g.cabinet;out.push([cy+ch,()=>fileCabinet(c,p,w,cx,cy,cw,ch,fs)]);
  if(g.evidence){const [ex,ey,ew]=g.evidence;out.push([ey,()=>docTable(c,p,ex,ey,ew,fs,'BẢN GỐC')]);}
  const [fx,fy,fw]=g.finance;out.push([fy,()=>ledgerDesk(c,p,fx,fy,fw,words.ledger,fs)]);
  const [ox,oy,ow]=g.copier;out.push([oy,()=>copier(c,p,w,ox,oy,ow,fs)]);
  if(g.cooler){const [qx,qy]=g.cooler;out.push([qy,()=>cooler(c,qx,qy,1)]);}
  const [px,py,ps]=g.plant;out.push([py+4,()=>plantAt(c,px,py,ps)]);
  if(tier!=='cozy')out.push([pl.bench[3],()=>sofa(c,p,pl.bench,tier==='garden')]);
  if(tier==='garden')for(const [x,y] of pl.garden)out.push([y+3,()=>plantAt(c,x,y,portrait?.7:.62)]);
  if(w.career==='customer_care')out.push(...staffHeadsets(w,p));
  return out;
}

export default {id:'office',plan:PLAN,room,props};
