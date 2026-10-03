/** Rice-stall scene (kind `comtam`): dì Bảy's cơm tấm cart at the mouth of the market. The market
 * gate and its tin roofs behind, a tube house with a striped awning and the stall's sign, the glass
 * case cart with its trays and two rice cookers, the charcoal grill with sườn and a curl of smoke,
 * red plastic tables and stools on the old tiles, sacks of broken rice, the cash tin on a stool and
 * the chalk price board. Moods (rain, market day, full moon) come from the career's public data.
 * Footprints follow the sidewalk plan (see shop.js for the PLAN schema). */
import {R,E,L,T,P,fit,streetBoard} from './kit.js';
import {PLAN} from './sidewalk.js';

const WOOD_D='#8f6746',RED='#d9483b',RED_D='#a8352b',BLUE='#3f7fbf';
const F={land:{x:66,y:116,w:1068,h:622,r:32,base:462,curb:668,road:680,sign:[350,58,500,104]},
         port:{x:24,y:118,w:652,h:736,r:28,base:505,curb:800,road:812,sign:[135,30,430,104]}};
const D=w=>w.c?.data||{};
const mod=w=>D(w).mod?.id||'normal';

/* ------------------------------------------------------------ backdrop */
function sky(c,w,f){const m=mod(w),rain=m==='rain',g=c.createLinearGradient(0,f.y,0,f.base);
  g.addColorStop(0,rain?'#b6c1c8':m==='ram'?'#e9d9c4':'#f5d7a8');g.addColorStop(1,rain?'#dde0d8':'#fcefd6');c.fillStyle=g;c.fillRect(f.x,f.y,f.w,f.base-f.y);
  const port=f===F.port,sx=port?606:1046,sy=port?176:170;
  if(m==='ram'){E(c,sx,sy,30,30,'#fff6dc');E(c,sx-6,sy-4,26,26,'#fff9e8');}
  else if(!rain){E(c,sx,sy,34,34,'#ffe3a6');E(c,sx,sy,22,22,'#ffd27a');}
}
function rainLines(c,w,f){if(mod(w)!=='rain')return;const t=w.reduced?0:(w.time*220)%40;c.strokeStyle='#8fa6b855';c.lineWidth=1.5;
  for(let x=f.x+10;x<f.x+f.w;x+=26)for(let y=f.y+((x/26|0)%3)*14-40+t;y<f.curb;y+=40){c.beginPath();c.moveTo(x,y);c.lineTo(x-6,y+16);c.stroke();}}
/** The market behind: a row of tin roofs and the arched gate with its name. */
function market(c,w,x,base,wd,port){const top=base-(port?120:132);
  for(let i=0;i<5;i++){const rx=x+i*wd/5;P(c,[[rx-6,top+40],[rx+wd/10,top+12],[rx+wd/5+6,top+40]],i%2?'#9fb2b8':'#b5c3c4');R(c,rx,top+40,wd/5-4,base-top-40,i%2?'#e8dcc6':'#efe4cf',2);
    for(let k=0;k<3;k++)R(c,rx+8+k*(wd/5-20)/3,top+56,(wd/5-28)/3,base-top-60,['#e7b65a','#9fc27f','#e58a6a'][(i+k)%3]+'aa',3);}
  const gx=x+wd/2,gw=port?150:190;L(c,gx-gw/2,base,gx-gw/2,top-6,'#8f6746',10);L(c,gx+gw/2,base,gx+gw/2,top-6,'#8f6746',10);
  R(c,gx-gw/2-14,top-34,gw+28,34,'#c9483b',10,'#8f2f27',2);T(c,'CHỢ ĐẦU HẺM',gx,top-17,fit(c,'CHỢ ĐẦU HẺM',gw,port?14:16,800),'#fff3d6',800);
  if(mod(w)==='market')for(let i=0;i<9;i++){const fx=gx-gw/2+i*gw/8;L(c,fx,top-34,fx+gw/16,top-26,'#8f6746',1);P(c,[[fx,top],[fx+8,top+14],[fx+16,top]],['#e94f4f','#f3c34a','#4f9ad9'][i%3]);}}
/** A tube house with shutters and a tiled edge. */
function tube(c,x,top,wd,base,col,shut='#8fbfa6'){R(c,x,top,wd,base-top+2,col,6,'#d6b394',2);R(c,x-6,top-12,wd+12,16,'#d98f73',7,'#b8765d',1.5);
  for(let i=0;i<Math.max(1,Math.floor(wd/90));i++){const cx=x+wd*(i+.5)/Math.max(1,Math.floor(wd/90));R(c,cx-20,top+26,40,48,'#cfe7ea',4,'#d6b394',1.5);R(c,cx-37,top+24,14,52,shut,3);R(c,cx+23,top+24,14,52,shut,3);}}
/** The stall's own house front: an open shutter, the striped awning and the painted name. */
function stallFront(c,x,base,wd,port){const top=base-(port?176:196);R(c,x,top,wd,base-top,'#f6e6c8',4,'#d6b394',2);
  R(c,x+14,top+64,wd-28,base-top-64,'#5b4636',3);for(let y=top+70;y<top+86;y+=5)L(c,x+16,y,x+wd-16,y,'#8a7462',1.2);
  R(c,x+24,top+96,wd-48,base-top-100,'#7a5f49',3);for(let i=0;i<4;i++)R(c,x+40+i*(wd-80)/4,top+110,(wd-80)/4-14,18,'#e9dcc5',3);
  R(c,x+wd/2-(port?92:110),top+10,port?184:220,32,'#fff4dc',8,'#c9483b',2);const s='CƠM TẤM DÌ BẢY';T(c,s,x+wd/2,top+27,fit(c,s,port?170:204,port?16:19,800),'#a8352b',800);
  const aw=top+48;for(let i=0;i<10;i++){const a=x-12+i*(wd+24)/10,b=a+(wd+24)/10;P(c,[[a,aw],[b,aw],[b+4,aw+30],[a+4,aw+30]],i%2?RED:'#fff3e2');}
  for(let i=0;i<11;i++)E(c,x-10+i*(wd+28)/10,aw+30,(wd+28)/20,5,i%2?RED:'#fff3e2');}
function pavement(c,f){const {base,curb,road}=f,bottom=f.y+f.h;R(c,f.x,base,f.w,curb-base,'#ead9bf',0);
  c.save();c.beginPath();c.rect(f.x,base,f.w,curb-base);c.clip();const tw=f===F.port?46:52,th=f===F.port?46:40;
  for(let y=base,row=0;y<curb;y+=th,row++)for(let x=f.x;x<f.x+f.w;x+=tw){c.fillStyle=((x/tw|0)+row)%2?'#e0caa8':'#ecdcc2';c.fillRect(x+1.5,y+1.5,tw-3,th-3);}
  c.restore();R(c,f.x,curb,f.w,road-curb,'#c9c3b8',0);L(c,f.x,curb,f.x+f.w,curb,'#a79f93',2);R(c,f.x,road,f.w,bottom-road,'#9fa7aa',0);
  for(let x=f.x+30;x<f.x+f.w;x+=120)R(c,x,road+(bottom-road)/2-2,56,4,'#f1e7c8',2);}

/* ------------------------------------------------------------ the stall */
function stool(c,x,y,col,s=1){P(c,[[x-15*s,y],[x-11*s,y-26*s],[x+11*s,y-26*s],[x+15*s,y]],col);R(c,x-16*s,y-32*s,32*s,8*s,col,3);E(c,x,y-28*s,12*s,3*s,'#ffffff33');}
function plate(c,x,y,s,full){E(c,x,y,16*s,6*s,'#fbf7ef');if(full){E(c,x-3*s,y-3*s,9*s,4*s,'#fffaf0');R(c,x+2*s,y-6*s,11*s,5*s,'#a8552b',2);E(c,x-8*s,y-2*s,3*s,2*s,'#7fb06b');}}
/** Red plastic tables with stools and a plate or two. */
function tables(c,w,x0,x1,fy,port){const n=port?2:3,step=(x1-x0)/n,s=port?1.05:1,busy=D(w).today?.plates||0;
  for(let i=0;i<n;i++){const cx=x0+step*(i+.5),top=fy-40*s;stool(c,cx-34*s,fy+4,BLUE,s*.85);stool(c,cx+34*s,fy+4,BLUE,s*.85);
    L(c,cx-22*s,top+8,cx-24*s,fy,RED_D,4);L(c,cx+22*s,top+8,cx+24*s,fy,RED_D,4);R(c,cx-30*s,top,60*s,10*s,RED,4,RED_D,1.5);
    if(w.c?.open&&(busy>i||i===0))plate(c,cx,top-2,s*.9,busy>i);
    R(c,cx+16*s,top-14*s,6*s,14*s,'#f3e9d2',2);R(c,cx+24*s,top-12*s,6*s,12*s,'#c97b3b',2);}}
/** Sacks of broken rice and a crate of eggs (the stock room). */
function sacks(c,p,x0,x1,fy,port){const W=x1-x0;E(c,(x0+x1)/2,fy+3,W/2+8,7,'#6b584420');
  for(let i=0;i<2;i++){const sx=x0+6+i*(W/2-4),sw=W/2-10;P(c,[[sx,fy],[sx+4,fy-46],[sx+sw-4,fy-46],[sx+sw,fy]],'#efe6d2');R(c,sx+4,fy-52,sw-8,10,'#e2d4b8',5);
    T(c,'GẠO',sx+sw/2,fy-26,port?10:9,'#8a5d4a',800);}
  R(c,x0+W/2-18,fy-70,36,18,'#d9b98a',3,'#a8835a',1.5);for(let i=0;i<4;i++)E(c,x0+W/2-12+i*8,fy-72,4,5,'#fbeede');}
/** The glass case cart with its trays and the two rice cookers on top. */
function cart(c,p,w,x0,x1,fy,port){const W=x1-x0,h=port?92:86,top=fy-h,d=D(w),trays=d.trays||{};E(c,(x0+x1)/2,fy+4,W/2+12,8,'#6b584422');
  for(const wx of [x0+16,x1-16]){E(c,wx,fy-6,9,9,'#4a4a4a');E(c,wx,fy-6,4,4,'#9a9a9a');}
  R(c,x0,top+36,W,h-46,'#d8dfe0',6,'#9aa6a8',2);
  R(c,x0+4,top-4,W-8,42,'#e8f4f6cc',4,'#a6b8bc',2);L(c,x0+W/2,top-4,x0+W/2,top+38,'#a6b8bc',1.5);
  const keys=['bi','cha','thit_kho','ca_kho','rau','dau_hu'],cols={bi:'#efe0b8',cha:'#f2c45c',thit_kho:'#9a5a33',ca_kho:'#7a4a2b',rau:'#5f9a4f',dau_hu:'#d9583f'};
  keys.forEach((k,i)=>{const tx=x0+10+i*(W-20)/6,tw=(W-20)/6-4,n=Number(trays[k]?.n||0);R(c,tx,top+22,tw,12,'#f5f5f2',2,'#c9cfd0',1);
    if(n)for(let j=0;j<Math.min(4,Math.ceil(n/4));j++)E(c,tx+tw*(j+.5)/4,top+24,tw/9,4,cols[k]);});
  const label=w.words().counter;R(c,x0+12,top+48,W-24,port?24:20,'#fff7e6',4,'#c9a06a',1);T(c,label,(x0+x1)/2,top+48+(port?12:10),fit(c,label,W-36,port?14:12),'#5a3f2c',800);
  for(const [cx,r] of [[x0+W*.22,'tam'],[x0+W*.78,'trang']]){const pot=d.pots?.[r]||{},full=pot.va>0;
    R(c,cx-20,top-34,40,30,'#f4f1ea',10,'#b9b3a6',1.5);R(c,cx-22,top-40,44,10,'#e7e1d4',6,'#b9b3a6',1.2);E(c,cx,top-42,6,3,'#8f8a80');R(c,cx-4,top-20,8,5,full?'#e9573f':'#9ba3a5',2);
    if(full&&!w.reduced){const t=(w.time*40)%30;c.strokeStyle='#ffffff99';c.lineWidth=2;c.beginPath();c.moveTo(cx,top-46);c.quadraticCurveTo(cx+6,top-56-t/3,cx-2,top-66-t/2);c.stroke();}}
}
/** The charcoal grill: a clay brazier, a wire rack with sườn, and smoke. */
function grill(c,w,x0,x1,fy,port){const cx=(x0+x1)/2,s=port?1.15:1,top=fy-46*s,g=D(w).grill||{},lit=!!g.lit,b=g.b,rack=(D(w).rack||[]).length;
  E(c,cx,fy+3,40*s,7*s,'#6b584422');P(c,[[cx-34*s,top],[cx+34*s,top],[cx+24*s,fy],[cx-24*s,fy]],'#b8643e');R(c,cx-38*s,top-6*s,76*s,10*s,'#9a4f30',4);
  R(c,cx-10*s,fy-20*s,20*s,12*s,lit?'#ff9a3c':'#5a463a',3);if(lit)for(let i=0;i<5;i++)E(c,cx-26*s+i*13*s,top-6*s,6*s,4*s,['#ff7a2c','#ffb14a','#e8572a'][i%3]);
  for(let i=0;i<7;i++)L(c,cx-34*s+i*11*s,top-10*s,cx-34*s+i*11*s,top-8*s,'#444',1);L(c,cx-36*s,top-10*s,cx+36*s,top-10*s,'#555',2);
  const n=b?.n||0;for(let i=0;i<n;i++)R(c,cx-30*s+i*15*s,top-18*s,13*s,8*s,b.flip!=null?'#9a4f22':'#d98b6b',3);
  if(lit&&!w.reduced){const t=w.time;c.strokeStyle='#d9d4cc88';c.lineWidth=5*s;for(let k=0;k<2;k++){const ox=cx+(k?10:-12)*s,o=((t*18+k*20)%60)*s;c.beginPath();c.moveTo(ox,top-20*s);
    c.bezierCurveTo(ox+14*s,top-40*s-o/2,ox-14*s,top-60*s-o/2,ox+8*s,top-84*s-o);c.stroke();}}
  if(rack){R(c,x1-4,top+4,30*s,8*s,'#cfcac2',2);for(let i=0;i<Math.min(rack,4);i++)R(c,x1-2+i*7*s,top-2,6*s,6*s,'#9a4f22',2);}}
function cashTin(c,p,w,x0,x1,fy,port){const cx=(x0+x1)/2;stool(c,cx,fy,BLUE,port?1.2:1.05);const top=fy-(port?38:34);
  R(c,cx-20,top-16,40,16,'#e1c25a',3,'#a8862e',1.5);R(c,cx-14,top-20,28,6,'#c9a43e',2);
  const label=w.words().ledger;R(c,cx-34,fy+2,68,port?20:18,'#fffaf0',8,'#c7ad90',1);T(c,label,cx,fy+(port?12:11),fit(c,label,60,port?11:10),'#6b5040',800);}
function priceBoard(c,p,w,cx,fy,port){const open=w.c?.open,bw=port?126:112,bh=port?64:56,top=fy-bh-22;
  E(c,cx,fy+2,bw/2,6,'#6b584420');L(c,cx-bw/2+12,top+bh,cx-bw/2+4,fy,WOOD_D,4);L(c,cx+bw/2-12,top+bh,cx+bw/2-4,fy,WOOD_D,4);
  R(c,cx-bw/2,top,bw,bh,'#3d4a44',8,WOOD_D,3);
  if(open){T(c,'Sườn · bì · chả',cx,top+16,fit(c,'Sườn · bì · chả',bw-14,port?13:12),'#fdf7e8',700);T(c,'Cơm phần',cx,top+34,port?13:12,'#f3d98a',700);
    T(c,mod(w)==='ram'?'Có cơm chay':'Có hộp mang về',cx,top+bh-11,fit(c,'Có hộp mang về',bw-14,port?11:10),'#cfe8c4',700);}
  else T(c,w.words().closed_sign,cx,top+bh/2,fit(c,w.words().closed_sign,bw-14,port?15:13,800),'#fdf7e8',800);}

/* ------------------------------------------------------------ rooms */
function room(w,p,port){const c=w.ctx,f=port?F.port:F.land;
  if(port){E(c,350,862,320,22,'#cba88d22');R(c,f.x-7,f.y-5,f.w+14,f.h+12,'#c9a27e',33);}
  else{E(c,600,742,520,22,'#cba88d22');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#c9a27e',38);}
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  if(port){market(c,w,30,f.base-150,640,true);tube(c,24,262,150,f.base,'#f3dfb0');stallFront(c,190,f.base,280,true);tube(c,486,250,200,f.base,'#f2d2c4','#e8a9a0');}
  else{market(c,w,90,f.base-160,1020,false);tube(c,78,236,230,f.base,'#f3dfb0');stallFront(c,330,f.base,320,false);tube(c,668,226,230,f.base,'#f2d2c4','#e8a9a0');tube(c,912,246,220,f.base,'#d6e8d8');}
  pavement(c,f);
  streetBoard(c,p,port?30:1013,port?282:322,port?1.6:1);
  rainLines(c,w,f);
  c.restore();
  const [sx,sy,sw,sh]=f.sign,title=p.title||'Cơm tấm Dì Bảy';R(c,sx-5,sy+7,sw+10,sh,'#8f6746',26);R(c,sx,sy,sw,sh,'#fff4dc',24,'#c9a06a',3);
  T(c,title,sx+sw/2,sy+40,fit(c,title,sw-60,30,800),'#5a3f2c',800);T(c,p.sub||'',sx+sw/2,sy+sh-26,fit(c,p.sub||'',sw-60,13),'#7b5b44');
  E(c,sx+36,sy+sh/2,14,14,RED);E(c,sx+sw-36,sy+sh/2,14,14,'#f2c45c');
}

/* ------------------------------------------------------------ props */
function props(w,p){const c=w.ctx,port=w.isPortrait(),b=w.plan().blocks,out=[];
  const [wh,wb,co,ev,fi,dr]=b;
  out.push([wh[3],()=>sacks(c,p,wh[0],wh[2],wh[3],port)]);
  out.push([wb[3],()=>tables(c,w,wb[0],wb[2],wb[3],port)]);
  out.push([co[3],()=>cart(c,p,w,co[0],co[2],co[3],port)]);
  out.push([ev[3],()=>grill(c,w,ev[0],ev[2],ev[3],port)]);
  out.push([fi[3],()=>cashTin(c,p,w,fi[0],fi[2],fi[3],port)]);
  out.push([dr[3],()=>priceBoard(c,p,w,(dr[0]+dr[2])/2,dr[3],port)]);
  return out;
}

export default {
  id:'comtam',
  plan:PLAN,
  room(w,p){room(w,p,w.isPortrait());},
  props(w,p){return props(w,p);},
};
