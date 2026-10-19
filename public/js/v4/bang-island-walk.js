/** ⚔️ Đảo bang on the old interface: the bang's island (public/js/bang-island-layout.js) as a flat, warm 2D walk like
 * the private islands' (v4/island-walk.js; the figures are look.js paintPlayer). The map is turned 45° the same way as
 * the new interface, so the gate and the pier face the viewer. Each facility is a front view whose size, colours and
 * roofs change with its level band (1: wood, 2: stone, 3: gold), with bamboo scaffolding while it is being built and
 * a staked plot before level 1. Same renderer contract as client/isometric/bang-island.ts: frame(model),
 * setBang(bang), toMap(clientX, clientY), toScreen(x, y, lift), anchor(id), personHeight, resize(), destroy().
 * 🏝️ The island's level (21/10) is the layout's: its zones (Võ đường, Trà đình, Bảo tháp, Hải đăng, gold lanterns) and,
 * while the next level is built, its raw sand bank with stakes, scaffolding and a crane (L.site). */
import {figureOf,paintPlayer,CANVAS} from './look.js';
import {inPoly,band as bandOf,gatePosts,screenOf} from '../bang-island-layout.js';

const FLAT=.62,R2=Math.SQRT1_2,FIG_H=160,FIG_W=110;
function inset(shore,by){
  const cx=shore.reduce((s,p)=>s+p[0],0)/shore.length,cy=shore.reduce((s,p)=>s+p[1],0)/shore.length;
  return shore.map(([x,y])=>{const d=Math.hypot(x-cx,y-cy)||1,k=Math.max(0,1-by/d);return [cx+(x-cx)*k,cy+(y-cy)*k];});
}
function seeded(seed){let s=seed>>>0||1;return ()=>((s=Math.imul(s^(s>>>15),2246822507)^Math.imul(s^(s>>>13),3266489909))>>>0)/4294967296;}
function darker(hex,k){const n=parseInt(String(hex).slice(1),16);if(!Number.isFinite(n))return hex;const c=v=>Math.max(0,Math.min(255,Math.round(v*k)));return `rgb(${c((n>>16)&255)},${c((n>>8)&255)},${c(n&255)})`;}
const safeColor=c=>/^#[0-9a-f]{6}$/i.test(String(c||''))?c:'#c2410c';

/** The camera for a stage of w×h CSS pixels: px per map unit S and the offset; a phone follows `focus`. `ext`: how far
 * the island reaches left and right on screen (a bigger island's capes, 21/10). */
export function walkCamera(w,h,focus=[.5,.5],shift=0,ext={a0:-.56,a1:.56}){
  const S=Math.max(h<450?720:900,Math.min(1450,Math.min(w/1.0,h/(FLAT*1.16))));
  const u=(focus[0]-focus[1])*R2,v=(focus[0]+focus[1])*R2,clamp=(x,lo,hi)=>lo>hi?(lo+hi)/2:Math.max(lo,Math.min(hi,x));
  const ox=clamp(w/2-u*S,w-ext.a1*S,-ext.a0*S),oy=clamp(h/2-shift-v*S*FLAT,h-1.3*S*FLAT,-.02*S*FLAT);
  return {S,ox,oy,fs:S/1800};
}
/** How tall each facility stands per band, in units of k (S/900 px): the labels sit above it. */
const TALL={dai_sanh:[16,130,170,240],kho_bang:[10,64,84,110],xuong_may:[10,60,86,130],den_vang:[10,60,104,170],tuong_bang:[8,50,84,128],san_pet:[6,20,24,44],cong_bang:[10,90,120,150]};

export function createBangWalkRenderer(canvas,L,bang){
  const ctx=canvas.getContext('2d'),figures=new Map(),rand=seeded(977);
  const grass=inset(L.shore,L.sandWidth),swells=[],dots=[];
  for(let i=0;i<70;i++){const x=rand()*1.3-.15,y=rand()*1.3-.15;if(!inPoly(inset(L.shore,-.05),x,y))swells.push([x,y,8+rand()*14,rand()*6]);}
  for(let i=0;i<160;i++){const x=rand(),y=rand();if(inPoly(grass,x,y))dots.push([x,y,4+rand()*6]);}
  const palms=L.palms.map(([x,y])=>[x,y,(rand()-.5)*.5,70+rand()*24,rand()*6]);
  const reach=[...L.shore,...(L.site?.shore||[])].map(([x,y])=>screenOf(x,y)[0]);
  const ext={a0:Math.min(-.56,Math.min(...reach)-.11),a1:Math.max(.56,Math.max(...reach)+.11)};
  let w=1,h=1,dpr=1,cam=walkCamera(1,1,undefined,0,ext),focus=L.plaza.c,destroyed=false,B=bang;
  const P=(x,y)=>[cam.ox+(x-y)*R2*cam.S,cam.oy+(x+y)*R2*cam.S*FLAT];
  const K=()=>cam.S/900;
  function poly(list,fill,dy=0){ctx.beginPath();list.forEach(([x,y],i)=>{const [a,b]=P(x,y);i?ctx.lineTo(a,b+dy):ctx.moveTo(a,b+dy);});ctx.closePath();ctx.fillStyle=fill;ctx.fill();}
  const diamond=r=>[[r.x-r.w/2,r.y-r.h/2],[r.x+r.w/2,r.y-r.h/2],[r.x+r.w/2,r.y+r.h/2],[r.x-r.w/2,r.y+r.h/2]];
  const fac=id=>B.facilities.find(f=>f.id===id)||{id,level:0,state:'done'};
  function ground(t){
    ctx.fillStyle=L.deep;ctx.fillRect(0,0,w,h);
    if(L.site){poly(inset(L.site.shore,-.09),L.sea);poly(L.site.shore,'#b89a68',8);poly(L.site.shore,'#d9c08e');}   // 🏝️ the next level's sand bank
    poly(inset(L.shore,-.09),L.sea);
    ctx.strokeStyle='rgba(255,255,255,.4)';ctx.lineWidth=2;
    for(const [x,y,r,ph] of swells){const [a,b]=P(x,y),dx=Math.sin(t/1600+ph)*4;ctx.beginPath();ctx.arc(a+dx,b,r*cam.S/800,Math.PI*1.15,Math.PI*1.85);ctx.stroke();}
    poly(L.shore,darker(L.sand,.72),10);poly(inset(L.shore,-.01),'rgba(255,255,255,.55)');poly(L.shore,L.sand);
    poly(grass,L.grassDark,3);poly(grass,L.grass);
    ctx.fillStyle=L.grassDark+'99';for(const [x,y,r] of dots){const [a,b]=P(x,y);ctx.beginPath();ctx.ellipse(a,b,r*cam.S/1000,r*cam.S/2400,0,0,Math.PI*2);ctx.fill();}
    for(const road of L.roads){poly(road,L.stoneDark,2);poly(road,L.stone);}
    const [pcx,pcy]=L.plaza.c,circle=[];for(let i=0;i<40;i++){const a=i/40*Math.PI*2;circle.push([pcx+Math.cos(a)*L.plaza.r,pcy+Math.sin(a)*L.plaza.r]);}
    poly(circle,L.stoneDark,3);poly(circle,L.stone);
    poly(L.dock,'#6e4a2e',6);poly(L.dock,'#b5844f');
    ctx.strokeStyle='#8b6038';ctx.lineWidth=1.2;const [d0,d1,d2,d3]=L.dock;
    for(let i=1;i<18;i++){const t=i/18,[a,b]=P(d0[0]+(d1[0]-d0[0])*t,d0[1]+(d1[1]-d0[1])*t),[c,e]=P(d3[0]+(d2[0]-d3[0])*t,d3[1]+(d2[1]-d3[1])*t);ctx.beginPath();ctx.moveTo(a,b);ctx.lineTo(c,e);ctx.stroke();}
    for(const p of L.plots){
      if(p.kind==='flowers'){poly(diamond(p),'#7a5a3a');const r=seeded(5);ctx.fillStyle='#fff';for(let i=0;i<22;i++){const [a,b]=P(p.x+(r()-.5)*p.w*.9,p.y+(r()-.5)*p.h*.9);ctx.fillStyle=['#ff6f91','#ffd166','#f8f4ff','#c77dff'][i%4];ctx.beginPath();ctx.arc(a,b,3*K(),0,Math.PI*2);ctx.fill();}}
      if(p.kind==='ring'){poly(diamond({...p,w:p.w*1.08,h:p.h*1.08}),'#6e4a2a',5);poly(diamond(p),'#c99a58');poly(diamond({...p,w:p.w*.7,h:p.h*.7}),'#d9ad6a');}
      if(p.kind==='teahouse'){const q={...p,w:p.w*1.5,h:p.h*1.5};poly(diamond(q),L.stoneDark,2);poly(diamond({...q,w:q.w*.94,h:q.h*.94}),'#3f9fbf');}
      if(p.kind==='pond'){poly(diamond({...p,w:p.w*1.12,h:p.h*1.12}),L.stoneDark);poly(diamond(p),'#3f9fbf');const r=seeded(9);for(let i=0;i<6;i++){const [a,b]=P(p.x+(r()-.5)*p.w*.7,p.y+(r()-.5)*p.h*.7);ctx.fillStyle='#4f9a4a';ctx.beginPath();ctx.ellipse(a,b,7*K(),3.5*K(),0,0,Math.PI*2);ctx.fill();if(i%2){ctx.fillStyle='#ff9ec0';ctx.beginPath();ctx.arc(a,b-2,2.6*K(),0,Math.PI*2);ctx.fill();}}}
    }
    // The training yard's floor (people walk on it).
    const yard=L.slots.san_pet,yf=fac('san_pet'),yb=yf.band??bandOf(yf.level);
    poly(diamond({...yard,w:yard.w*.96,h:yard.h*.96}),['#c6a06a','#c6a06a','#8fcd68','#e6cf98'][yb]);
  }
  /* A front view: a box of `wd` × `ht` standing on (a, b), walls and a roof; tiers stack up. */
  function pavilion(a,b,wd,tiers,k){
    let y=b;ctx.fillStyle='rgba(0,0,0,.16)';ctx.beginPath();ctx.ellipse(a,b,wd*.62,wd*.14,0,0,Math.PI*2);ctx.fill();
    tiers.forEach((t,i)=>{const tw=wd*(t.k||1),x=a-tw/2,hh=t.h*k;
      ctx.fillStyle=t.wall;ctx.fillRect(x,y-hh,tw,hh);ctx.fillStyle=darker(t.wall,.82);ctx.fillRect(x,y-hh,tw*.18,hh);
      if(t.win)for(let j=0;j<t.win;j++){if(i===0&&j===Math.floor(t.win/2))continue;ctx.fillStyle=t.glass||'#8fc6dc';ctx.fillRect(x+tw*(.12+j*(.76/t.win)),y-hh*.72,tw*.1,hh*.36);}
      if(i===0&&t.door){ctx.fillStyle=t.door;ctx.fillRect(a-tw*.08,y-hh*.7,tw*.16,hh*.7);}
      if(t.pillars){ctx.fillStyle=t.pillars;for(let j=0;j<=4;j++)ctx.fillRect(x+tw*j/4-2*k,y-hh,4*k,hh);}
      if(t.trim){ctx.fillStyle=t.trim;ctx.fillRect(x,y-hh,tw,4*k);}
      y-=hh;const rw=tw*(1.18),rh=(t.roofH||18)*k;
      if(t.dome){ctx.fillStyle=darker(t.roof,.8);ctx.fillRect(a-tw*.55,y-4*k,tw*1.1,6*k);ctx.fillStyle=t.roof;ctx.beginPath();ctx.arc(a,y-2*k,tw*.42,Math.PI,0);ctx.fill();
        ctx.fillStyle='rgba(255,240,168,.6)';ctx.beginPath();ctx.arc(a-tw*.14,y-tw*.2,tw*.1,0,Math.PI*2);ctx.fill();ctx.fillStyle=t.roof;ctx.beginPath();ctx.arc(a,y-tw*.42-6*k,5*k,0,Math.PI*2);ctx.fill();y-=tw*.42;return;}
      ctx.fillStyle=t.roof;ctx.beginPath();ctx.moveTo(a-rw/2-6*k,y+2*k);ctx.quadraticCurveTo(a-rw/2,y-rh*.2,a-rw*.3,y-rh);ctx.lineTo(a+rw*.3,y-rh);ctx.quadraticCurveTo(a+rw/2,y-rh*.2,a+rw/2+6*k,y+2*k);ctx.closePath();ctx.fill();
      ctx.fillStyle=darker(t.roof,.75);ctx.fillRect(a-rw/2,y-2*k,rw,4*k);
      if(t.tips){ctx.fillStyle=t.tips;for(const s of [-1,1]){ctx.beginPath();ctx.moveTo(a+s*(rw/2+6*k),y+2*k);ctx.lineTo(a+s*(rw/2+12*k),y-8*k);ctx.lineTo(a+s*(rw/2-2*k),y-2*k);ctx.fill();}}
      y-=rh*(t.overlap??.7);
    });
    return y;
  }
  function flagAt(a,b,ht,k,t,color){
    ctx.fillStyle='#6b4a2b';ctx.fillRect(a-1.5*k,b-ht,3*k,ht);const wv=Math.sin(t/300+a)*3*k;
    ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(a,b-ht);ctx.lineTo(a+26*k+wv,b-ht+5*k);ctx.lineTo(a+22*k,b-ht+10*k);ctx.lineTo(a+26*k-wv,b-ht+16*k);ctx.lineTo(a,b-ht+18*k);ctx.fill();
  }
  function bannerAt(a,top,wd,ht,color,emoji,k){
    ctx.fillStyle=color;ctx.fillRect(a-wd/2,top,wd,ht);ctx.fillStyle='#e7b726';ctx.fillRect(a-wd/2,top,wd,3*k);
    ctx.fillStyle=darker(color,.65);ctx.beginPath();ctx.moveTo(a-wd/2,top+ht);ctx.lineTo(a,top+ht+8*k);ctx.lineTo(a+wd/2,top+ht);ctx.fill();
    if(emoji){ctx.font=`${Math.round(Math.min(wd*.8,22*k))}px "Segoe UI Emoji","Apple Color Emoji",sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(emoji,a,top+ht*.5);}
  }
  function scaffold(a,b,wd,ht,k){
    ctx.strokeStyle='#c9a75c';ctx.lineWidth=3*k;const x0=a-wd*.58,x1=a+wd*.58;
    for(let i=0;i<=4;i++){const x=x0+(x1-x0)*i/4;ctx.beginPath();ctx.moveTo(x,b);ctx.lineTo(x,b-ht-10*k);ctx.stroke();}
    ctx.lineWidth=2*k;ctx.strokeStyle='#8f7238';for(let y=b-20*k;y>b-ht;y-=22*k){ctx.beginPath();ctx.moveTo(x0,y);ctx.lineTo(x1,y);ctx.stroke();}
    for(let i=0;i<4;i++){const xa=x0+(x1-x0)*i/4,xb=x0+(x1-x0)*(i+1)/4;ctx.beginPath();ctx.moveTo(xa,b);ctx.lineTo(xb,b-ht*.5);ctx.stroke();}
    ctx.fillStyle='rgba(63,155,90,.32)';ctx.fillRect(a,b-ht*.95,wd*.55,ht*.8);
    ctx.fillStyle='#b98b4e';ctx.fillRect(x0,b-ht*.5,x1-x0,4*k);
  }
  function stakes(r,k){
    poly(diamond({...r,w:r.w*.86,h:r.h*.86}),'#c6a06a');
    ctx.strokeStyle='#e8d9b0';ctx.lineWidth=1.5;const pts=diamond({...r,w:r.w*.86,h:r.h*.86}).map(([x,y])=>P(x,y));
    ctx.beginPath();pts.forEach(([a,b],i)=>i?ctx.lineTo(a,b-12*k):ctx.moveTo(a,b-12*k));ctx.closePath();ctx.stroke();
    ctx.fillStyle='#6e4a2a';for(const [a,b] of pts)ctx.fillRect(a-2*k,b-16*k,4*k,16*k);
  }
  /** One facility's front view at its slot. */
  function facility(id,t){
    const f=fac(id),band=f.band??bandOf(f.level),building=f.state==='building',r=L.slots[id],k=K(),color=safeColor(B.color);
    const [a,b]=P(r.x+r.w*.42,r.y+r.h*.42),wd=(r.w+r.h)*R2*cam.S*.82;
    if(id==='cong_bang')return gate(band,building,k,t,color);
    if(id==='san_pet')return yardFront(r,band,building,k,t,color);
    if(band===0){stakes(r,k);if(building)scaffold(a,b,wd*.8,40*k,k);return;}
    const S={
      dai_sanh:[null,[{h:52,wall:'#9a6a3c',roof:'#d6ad55',roofH:34,win:3,door:'#6e4a2a',k:.8}],
        [{h:64,wall:'#f2e4c4',roof:'#b04a35',roofH:16,win:4,door:'#a3242a',pillars:'#c8312f',tips:'#86362a',k:.86},{h:28,wall:'#f2e4c4',roof:'#b04a35',roofH:26,win:3,tips:'#86362a',k:.55}],
        [{h:80,wall:'#a3242a',roof:'#e7b726',roofH:18,win:5,door:'#5a1215',pillars:'#e7b726',trim:'#e7b726',tips:'#c8312f',glass:'#f4c95d',k:.92},{h:38,wall:'#a3242a',roof:'#e7b726',roofH:18,win:3,tips:'#c8312f',glass:'#f4c95d',trim:'#e7b726',k:.62},{h:22,wall:'#a3242a',roof:'#e7b726',roofH:34,tips:'#c8312f',k:.38}]],
      kho_bang:[null,[{h:40,wall:'#9a6a3c',roof:'#6e4a2a',roofH:20,door:'#6e4a2a',k:.6}],[{h:56,wall:'#d3cab8',roof:'#86362a',roofH:24,door:'#3d3e46',k:.75}],[{h:52,wall:'#f1e6cf',roof:'#e7b726',roofH:40,door:'#b68714',trim:'#e7b726',pillars:'#e7b726',k:.75,overlap:.9,dome:true}]],
      xuong_may:[null,[{h:38,wall:'rgba(0,0,0,0)',roof:'#d3402f',roofH:22,k:.7}],[{h:56,wall:'#f6efe0',roof:'#3f6f9e',roofH:26,win:3,door:'#6e4a2a',k:.7}],[{h:96,wall:'#f7dfe8',roof:'#7c4e9b',roofH:30,win:3,door:'#8a5a9b',tips:'#e7b726',trim:'#d9a3b8',k:.78}]],
      den_vang:[null,[{h:32,wall:'#c8312f',roof:'#b04a35',roofH:18,door:'#4a1010',tips:'#86362a',k:.45}],[{h:50,wall:'#f2c94c',roof:'#e7b726',roofH:14,door:'#a3242a',pillars:'#c8312f',tips:'#c8312f',k:.68},{h:16,wall:'#f2c94c',roof:'#e7b726',roofH:24,tips:'#c8312f',k:.45}],
        [{h:40,wall:'#f0c23a',roof:'#e7b726',roofH:14,door:'#a3242a',tips:'#c8312f',k:.68},{h:28,wall:'#f0c23a',roof:'#e7b726',roofH:12,tips:'#c8312f',k:.54},{h:22,wall:'#f0c23a',roof:'#e7b726',roofH:10,tips:'#c8312f',k:.4},{h:18,wall:'#f0c23a',roof:'#e7b726',roofH:26,tips:'#c8312f',k:.28}]],
    };
    if(id==='tuong_bang'){statue(a,b,band,k,color);if(building)scaffold(a,b,wd,TALL[id][band]*k,k);return;}
    if(id==='den_vang'&&band>=2){ctx.fillStyle=`rgba(255,227,122,${.12+.08*Math.sin(t/700)})`;ctx.beginPath();ctx.ellipse(a,b-TALL[id][band]*k*.5,wd*.9,TALL[id][band]*k*.6,0,0,Math.PI*2);ctx.fill();}
    if(id==='xuong_may'&&band===1){ctx.fillStyle='#6e4a2a';for(const s of [-1,1])ctx.fillRect(a+s*wd*.34-2*k,b-38*k,4*k,38*k);}
    const top=pavilion(a,b,wd,S[id][band],k);
    if(id==='dai_sanh'){bannerAt(a-wd*(band===3?.3:.26),b-[0,48,60,74][band]*k,14*k,[0,34,40,46][band]*k,color,B.emoji,k);flagAt(a,top+6*k,40*k,k,t,color);}
    if(id==='kho_bang'&&band===3){ctx.fillStyle='#e7b726';for(const s of [-1,1])for(let i=0;i<4;i++){ctx.beginPath();ctx.ellipse(a+s*wd*.52,b-i*3*k,9*k-i,4*k,0,0,Math.PI*2);ctx.fill();}}
    if(id==='kho_bang'&&band===1){ctx.fillStyle='#c99a58';ctx.fillRect(a+wd*.36,b-14*k,14*k,14*k);ctx.fillRect(a+wd*.42,b-26*k,12*k,12*k);}
    if(id==='xuong_may'&&band>=2){const cols=['#e5484d','#f2c14e','#4fa3d9','#8bc34a','#c77dff'];for(let i=0;i<5;i++){ctx.fillStyle=cols[i];ctx.fillRect(a+wd*.4+i*5*k,b-34*k,4*k,22*k+i%2*6*k);}}
    if(building)scaffold(a,b,wd*.86,TALL[id][band]*k*.92,k);
  }
  function statue(a,b,band,k,color){
    if(band===1){ctx.fillStyle='#9f9584';ctx.beginPath();ctx.ellipse(a,b,20*k,7*k,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='#d3cab8';ctx.fillRect(a-10*k,b-44*k,20*k,40*k);ctx.beginPath();ctx.arc(a,b-44*k,10*k,Math.PI,0);ctx.fill();
      ctx.fillStyle='#9f9584';for(let i=0;i<4;i++)ctx.fillRect(a-6*k,b-36*k+i*7*k,12*k,1.5*k);return;}
    const big=band===3,ph=(big?34:24)*k,body=big?'#e7b726':'#9aa0a6',hg=(big?84:56)*k;
    ctx.fillStyle=big?'#f4efe4':'#9f9584';ctx.fillRect(a-16*k,b-ph,32*k,ph);if(big){ctx.fillStyle='#e7b726';ctx.fillRect(a-16*k,b-ph,32*k,4*k);}
    const z=b-ph;if(big){ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(a-6*k,z-hg*.78);ctx.lineTo(a+8*k,z-hg*.78);ctx.lineTo(a+18*k,z);ctx.lineTo(a-16*k,z);ctx.fill();}
    ctx.fillStyle=body;ctx.beginPath();ctx.moveTo(a-12*k,z);ctx.lineTo(a+12*k,z);ctx.lineTo(a+7*k,z-hg*.72);ctx.lineTo(a-7*k,z-hg*.72);ctx.fill();
    ctx.beginPath();ctx.arc(a,z-hg*.84,hg*.12,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle=big?'#fff1b0':'#d7dde2';ctx.lineWidth=3*k;ctx.beginPath();ctx.moveTo(a+9*k,z-hg*.6);ctx.lineTo(a+20*k,z-hg*1.12);ctx.stroke();
  }
  function yardFront(r,band,building,k,t,color){
    const pts=diamond({...r,w:r.w*.96,h:r.h*.96}).map(([x,y])=>P(x,y));
    if(band===0){stakes(r,k);return;}
    ctx.strokeStyle=band===1?'#6e4a2a':band===2?'#f4f1ea':'#d3cab8';ctx.lineWidth=(band===3?6:3)*k;
    for(const dy of band===3?[10]:[12,6]){ctx.beginPath();pts.forEach(([a,b],i)=>i?ctx.lineTo(a,b-dy*k):ctx.moveTo(a,b-dy*k));ctx.closePath();ctx.stroke();}
    if(band===3){const [A,Bp,,D]=pts;for(let i=0;i<4;i++){const lift=(14+i*8)*k,o=i*6*k;ctx.strokeStyle=i%2?color:'#d3cab8';ctx.lineWidth=7*k;ctx.beginPath();ctx.moveTo(D[0]-o,D[1]-lift);ctx.lineTo(A[0],A[1]-lift-o*.5);ctx.lineTo(Bp[0]+o,Bp[1]-lift);ctx.stroke();}
      flagAt(A[0],A[1]-40*k,44*k,k,t,color);}
    if(band===2){const [a,b]=P(r.x,r.y);ctx.strokeStyle='#4fa3d9';ctx.lineWidth=6*k;ctx.beginPath();ctx.arc(a-20*k,b,12*k,Math.PI,0);ctx.stroke();ctx.fillStyle='#ff8a1f';ctx.beginPath();ctx.moveTo(a+20*k,b);ctx.lineTo(a+26*k,b);ctx.lineTo(a+23*k,b-10*k);ctx.fill();}
    if(band===1){const [a,b]=P(r.x-r.w*.2,r.y-r.h*.2);ctx.fillStyle='#9a6a3c';ctx.fillRect(a-2*k,b-38*k,5*k,38*k);ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(a,b-42*k,10*k,0,Math.PI*2);ctx.fill();ctx.fillStyle='#c8312f';ctx.beginPath();ctx.arc(a,b-42*k,6*k,0,Math.PI*2);ctx.fill();}
    if(building){const [a,b]=pts[2];scaffold(a,b,40*k,30*k,k);}
  }
  function gate(band,building,k,t,color){
    const posts=gatePosts(L).map(g=>P(g.x,g.y)),[[la,lb],[ra]]=posts,mid=(la+ra)/2,span=(ra-la)/2;
    if(band===0){ctx.fillStyle='#6e4a2a';for(const [a,b] of posts)ctx.fillRect(a-2*k,b-(building?40:16)*k,4*k,(building?40:16)*k);if(building){ctx.fillStyle='#c9a75c';ctx.fillRect(la,lb-36*k,ra-la,4*k);}return;}
    const ht=[0,90,110,132][band]*k,pw=[0,10,16,18][band]*k,pc=['', '#9a6a3c','#d3cab8','#a3242a'][band];
    if(band===3)for(const s of [-1,1]){const ox=mid+s*span*1.8,inner=mid+s*span;ctx.fillStyle='#a3242a';ctx.fillRect(ox-6*k,lb-86*k,12*k,86*k);ctx.fillRect(Math.min(ox,inner),lb-80*k,Math.abs(ox-inner),7*k);
      const a0=Math.min(ox,inner)-(s<0?14*k:0),a1=Math.max(ox,inner)+(s>0?14*k:0);ctx.fillStyle='#e7b726';ctx.beginPath();ctx.moveTo(a0,lb-84*k);ctx.lineTo(a1,lb-84*k);ctx.lineTo(a1-s*0-(s>0?10*k:-4*k),lb-100*k);ctx.lineTo(a0+(s<0?10*k:-4*k),lb-100*k);ctx.fill();
      ctx.fillStyle='#c8312f';ctx.beginPath();const tip=s<0?a0:a1;ctx.moveTo(tip,lb-84*k);ctx.lineTo(tip+s*8*k,lb-94*k);ctx.lineTo(tip-s*4*k,lb-88*k);ctx.fill();}
    ctx.fillStyle=pc;for(const [a,b] of posts)ctx.fillRect(a-pw/2,b-ht,pw,ht);
    ctx.fillStyle=band===1?'#6e4a2a':band===2?'#9f9584':'#a3242a';ctx.fillRect(la-14*k,lb-ht+ (band===1?6:16)*k,ra-la+28*k,12*k);
    if(band>=2){const rw=span*2+(band===3?70:56)*k,top=lb-ht;ctx.fillStyle=band===3?'#e7b726':'#b04a35';ctx.beginPath();ctx.moveTo(mid-rw/2,top+6*k);ctx.lineTo(mid-rw*.36,top-24*k);ctx.lineTo(mid+rw*.36,top-24*k);ctx.lineTo(mid+rw/2,top+6*k);ctx.fill();
      if(band===3){ctx.beginPath();ctx.moveTo(mid-rw*.36,top-20*k);ctx.lineTo(mid-rw*.24,top-46*k);ctx.lineTo(mid+rw*.24,top-46*k);ctx.lineTo(mid+rw*.36,top-20*k);ctx.fill();}
      ctx.fillStyle='#7a1d1d';ctx.fillRect(mid-44*k,lb-ht+18*k,88*k,22*k);ctx.fillStyle='#ffe9a8';ctx.font=`bold ${Math.round(12*k)}px "Be Vietnam Pro","Segoe UI",sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
      const name=String(B.name||'');let size=12*k;ctx.font=`bold ${Math.round(size)}px "Be Vietnam Pro","Segoe UI",sans-serif`;while(size>6&&ctx.measureText(name).width>84*k){size-=1;ctx.font=`bold ${Math.round(size)}px "Be Vietnam Pro","Segoe UI",sans-serif`;}
      ctx.fillText(name,mid,lb-ht+29*k);
      for(const s of [-1,1])flagAt(mid+s*span*(band===3?1.8:1),lb-ht-(band===3?0:6)*k,44*k,k,t,color);}
    bannerAt(mid,lb-ht+(band===1?20:42)*k,32*k,(band===1?40:44)*k,color,B.emoji,k);
    if(building)scaffold(mid,lb,span*2,ht,k);
  }
  function standing(t){
    const out=[],k=K();
    for(const [x,y,lean,ht,ph] of palms)out.push([x+y,()=>{const [a,b]=P(x,y),sw=Math.sin(t/1300+ph)*3,top=[a+lean*ht*k+sw,b-ht*k];
      ctx.fillStyle='rgba(0,0,0,.15)';ctx.beginPath();ctx.ellipse(a+14*k,b+2,24*k,7*k,0,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle='#8a6340';ctx.lineWidth=8*k;ctx.beginPath();ctx.moveTo(a,b);ctx.quadraticCurveTo(a+lean*ht*k*.2,b-ht*k*.6,top[0],top[1]);ctx.stroke();
      for(let i=0;i<7;i++){const an=i/7*Math.PI*2,len=36*k;ctx.fillStyle=i%2?'#3f8a3e':'#4fa04a';ctx.beginPath();ctx.moveTo(top[0],top[1]);ctx.lineTo(top[0]+Math.cos(an)*len,top[1]+Math.sin(an)*len*.55+10*k);ctx.lineTo(top[0]+Math.cos(an+.35)*len*.7,top[1]+Math.sin(an+.35)*len*.4+5*k);ctx.fill();}}]);
    for(const [x,y] of L.trees)out.push([x+y,()=>{const [a,b]=P(x,y);ctx.fillStyle='#76532f';ctx.fillRect(a-3*k,b-40*k,6*k,40*k);ctx.fillStyle='#4c9a4a';for(const [ox,oy,r] of [[-11,-44,16],[11,-46,15],[0,-58,18]]){ctx.beginPath();ctx.arc(a+ox*k,b+oy*k,r*k,0,Math.PI*2);ctx.fill();}}]);
    for(const p of L.plots){
      if(p.kind==='bamboo')out.push([p.x+p.y+p.w,()=>{const r=seeded(3);for(let i=0;i<8;i++){const [a,b]=P(p.x+(r()-.5)*p.w,p.y+(r()-.5)*p.h),hh=(60+r()*40)*k;ctx.fillStyle='#7fae4a';ctx.fillRect(a-2*k,b-hh,4*k,hh);ctx.fillStyle='#4f9a3a';ctx.beginPath();ctx.ellipse(a+6*k,b-hh,10*k,4*k,0,0,Math.PI*2);ctx.fill();}}]);
      if(p.kind==='lanterns')out.push([p.x+p.y,()=>{for(let i=-1;i<=1;i++){const [a,b]=P(p.x+i*.03,p.y-i*.03);ctx.fillStyle='#6e4a2a';ctx.fillRect(a-1.5*k,b-46*k,3*k,46*k);ctx.fillStyle='#c8312f';ctx.beginPath();ctx.ellipse(a+10*k,b-36*k,6*k,8*k,0,0,Math.PI*2);ctx.fill();}}]);
      if(p.kind==='pines')out.push([p.x+p.y+p.w,()=>{const [a,b]=P(p.x,p.y);ctx.fillStyle='#5c9a4a';ctx.beginPath();ctx.ellipse(a,b,40*k,16*k,0,0,Math.PI*2);ctx.fill();
        for(const [ox,hh] of [[-22,50],[0,64],[22,48]]){ctx.fillStyle='#2f6b3a';ctx.beginPath();ctx.moveTo(a+ox*k-14*k,b-6*k);ctx.lineTo(a+ox*k+14*k,b-6*k);ctx.lineTo(a+ox*k,b-hh*k);ctx.fill();}}]);
      if(p.kind==='ring')out.push([p.x+p.y+p.w,()=>{const pts=diamond(p).map(([x,y])=>P(x,y));ctx.fillStyle='#6e4a2a';for(const [a,b] of pts)ctx.fillRect(a-2.5*k,b-30*k,5*k,30*k);
        ctx.strokeStyle='#c8312f';ctx.lineWidth=2.5*k;for(const lift of [14,24]){ctx.beginPath();pts.forEach(([a,b],i)=>i?ctx.lineTo(a,b-lift*k):ctx.moveTo(a,b-lift*k));ctx.closePath();ctx.stroke();}}]);
      if(p.kind==='teahouse')out.push([p.x+p.y+p.w*.6,()=>{const [a,b]=P(p.x+p.w*.3,p.y+p.h*.3),wd=(p.w+p.h)*R2*cam.S*.8;
        pavilion(a,b,wd,[{h:34,wall:'rgba(0,0,0,0)',roof:'#2f6d55',roofH:20,pillars:'#a3242a',tips:'#e7b726',k:.8}],k);
        for(let i=0;i<3;i++){const [fa,fb]=P(p.x-p.w*(.55-i*.2),p.y+p.h*(.6-i*.15));ctx.fillStyle=i%2?'#ffffff':'#ff7a2f';ctx.beginPath();ctx.ellipse(fa,fb,6*k,3*k,0,0,Math.PI*2);ctx.fill();}}]);
      if(p.kind==='pagoda')out.push([p.x+p.y+p.w,()=>{const [a,b]=P(p.x+p.w*.4,p.y+p.h*.4),wd=(p.w+p.h)*R2*cam.S*.9;
        pavilion(a,b,wd,[{h:26,wall:'#f2e4c4',roof:'#b04a35',roofH:12,door:'#a3242a',tips:'#e7b726',k:.8},{h:20,wall:'#f2e4c4',roof:'#b04a35',roofH:11,tips:'#e7b726',k:.66},
          {h:18,wall:'#f2e4c4',roof:'#b04a35',roofH:10,tips:'#e7b726',k:.54},{h:16,wall:'#f2e4c4',roof:'#b04a35',roofH:10,tips:'#e7b726',k:.44},{h:14,wall:'#f2e4c4',roof:'#e7b726',roofH:22,tips:'#c8312f',k:.34}],k);}]);
      if(p.kind==='lighthouse')out.push([p.x+p.y+p.w,()=>{const [a,b]=P(p.x+p.w*.3,p.y+p.h*.3),ht=150*k;
        ctx.fillStyle='#6b6b6b';ctx.beginPath();ctx.ellipse(a,b,22*k,8*k,0,0,Math.PI*2);ctx.fill();
        for(let i=0;i<6;i++){const y0=b-ht*i/6,y1=b-ht*(i+1)/6,w0=16*k-i*1.4*k,w1=16*k-(i+1)*1.4*k;ctx.fillStyle=i%2?'#c8312f':'#fbf7ee';ctx.beginPath();ctx.moveTo(a-w0,y0);ctx.lineTo(a+w0,y0);ctx.lineTo(a+w1,y1);ctx.lineTo(a-w1,y1);ctx.fill();}
        ctx.fillStyle='#3d3e46';ctx.fillRect(a-10*k,b-ht-16*k,20*k,16*k);ctx.fillStyle=`rgba(255,227,122,${.75+.25*Math.sin(t/400)})`;ctx.fillRect(a-7*k,b-ht-14*k,14*k,11*k);
        ctx.fillStyle='#c8312f';ctx.beginPath();ctx.moveTo(a-12*k,b-ht-16*k);ctx.lineTo(a+12*k,b-ht-16*k);ctx.lineTo(a,b-ht-30*k);ctx.fill();
        ctx.fillStyle=`rgba(255,240,170,${.16+.1*Math.sin(t/400)})`;ctx.beginPath();ctx.moveTo(a,b-ht-9*k);ctx.lineTo(a+150*k,b-ht-40*k);ctx.lineTo(a+150*k,b-ht+20*k);ctx.fill();}]);
      if(p.kind==='dummies')out.push([p.x+p.y,()=>{const [a,b]=P(p.x,p.y);for(const ox of [-10,12]){ctx.fillStyle='#9a6a3c';ctx.fillRect(a+ox*k-2*k,b-40*k,5*k,40*k);ctx.fillRect(a+ox*k-12*k,b-32*k,24*k,4*k);ctx.fillStyle='#d6ad55';ctx.beginPath();ctx.ellipse(a+ox*k,b-22*k,7*k,10*k,0,0,Math.PI*2);ctx.fill();}}]);
    }
    for(const [x,y] of L.lamps||[])out.push([x+y,()=>{const [a,b]=P(x,y);ctx.fillStyle='#3d3e46';ctx.fillRect(a-1.5*k,b-40*k,3*k,40*k);
      ctx.fillStyle='#e7b726';ctx.beginPath();ctx.ellipse(a,b-44*k,6*k,8*k,0,0,Math.PI*2);ctx.fill();ctx.fillStyle=`rgba(255,227,122,${.35+.15*Math.sin(t/600+x*9)})`;ctx.beginPath();ctx.arc(a,b-44*k,12*k,0,Math.PI*2);ctx.fill();}]);
    if(L.site){const r=L.site;out.push([r.x+r.y+r.w,()=>{const [a,b]=P(r.x+r.w*.42,r.y+r.h*.42),wd=(r.w+r.h)*R2*cam.S*.82;stakes(r,k);scaffold(a,b,wd,60*k,k);
      ctx.strokeStyle='#e7b726';ctx.lineWidth=4*k;ctx.beginPath();ctx.moveTo(a+wd*.7,b);ctx.lineTo(a+wd*.7,b-120*k);ctx.lineTo(a-wd*.5,b-112*k);ctx.stroke();
      ctx.strokeStyle='#3d3e46';ctx.lineWidth=1.5*k;ctx.beginPath();ctx.moveTo(a-wd*.3,b-113*k);ctx.lineTo(a-wd*.3,b-70*k);ctx.stroke();ctx.fillStyle='#c99a58';ctx.fillRect(a-wd*.3-7*k,b-70*k,14*k,10*k);}]);}
    for(const id of Object.keys(L.slots)){const r=L.slots[id];const d=id==='cong_bang'?r.x+r.y:r.x+r.y+(r.w+r.h)/2*.84;out.push([d,()=>facility(id,t)]);}
    // The bang's boat beside the pier, its sail in the bang's colour.
    const [bx,by]=[.5+(.075+.5)*R2,.5+(.5-.075)*R2];out.push([bx+by,()=>{const [a,b]=P(bx,by),bob=Math.sin(t/800)*2;
      ctx.fillStyle='#8a5a32';ctx.beginPath();ctx.moveTo(a-48*k,b-4*k+bob);ctx.lineTo(a+50*k,b-8*k+bob);ctx.lineTo(a+38*k,b+8*k+bob);ctx.lineTo(a-40*k,b+8*k+bob);ctx.fill();
      ctx.fillStyle='#5a3a20';ctx.fillRect(a-1.5*k,b-90*k+bob,3*k,84*k);ctx.fillStyle=safeColor(B.color);ctx.beginPath();ctx.moveTo(a+2*k,b-86*k+bob);ctx.lineTo(a+2*k,b-18*k+bob);ctx.lineTo(a+40*k,b-24*k+bob);ctx.fill();}]);
    for(const s of L.spots)out.push([s.x+s.y-.001,()=>{const [a,b]=P(s.x,s.y),bob=Math.sin(t/700+s.x*9)*4;
      ctx.fillStyle='rgba(255,255,255,.3)';ctx.strokeStyle='rgba(255,255,255,.85)';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(a,b,18*k,8*k,0,0,Math.PI*2);ctx.fill();ctx.stroke();
      ctx.fillStyle='#000';ctx.font=`${Math.round(20*k+6)}px "Segoe UI Emoji","Apple Color Emoji",sans-serif`;ctx.textAlign='center';ctx.textBaseline='bottom';ctx.fillText(s.emoji,a,b-10*k+bob);}]);
    return out;
  }
  function figure(p){
    const key=JSON.stringify([p.look,p.gender]),px=Math.max(.1,cam.fs*dpr),size=Math.round(px*100);let hit=figures.get(key);
    if(!hit||hit.size!==size){
      const cv=document.createElement('canvas');cv.width=Math.ceil(FIG_W*px);cv.height=Math.ceil(FIG_H*px);
      const q=cv.getContext('2d');q.setTransform(px,0,0,px,55*px,150*px);
      try{paintPlayer(q,figureOf(p.look||{},p.gender==='male'||p.gender==='female'?p.gender:'none'),CANVAS);}catch{/* an unknown look draws nothing */}
      hit={cv,size};figures.set(key,hit);if(figures.size>60)figures.delete(figures.keys().next().value);
    }
    return hit.cv;
  }
  function person(p,t){
    if(p.hidden)return;
    const [a,b]=P(p.x,p.y),fs=cam.fs,bob=p.walking?Math.abs(Math.sin(t/110))*3:0,flip=Boolean(p.left),sit=p.pose==='sit';
    ctx.save();ctx.translate(a,b-bob);if(flip)ctx.scale(-1,1);if(p.pose==='bow')ctx.rotate(.14);
    if(sit){ctx.beginPath();ctx.rect(-60*fs,-160*fs,120*fs,130*fs);ctx.clip();ctx.translate(0,14*fs);}
    ctx.drawImage(figure(p),-55*fs,-150*fs,FIG_W*fs,FIG_H*fs);ctx.restore();
  }
  function resize(){
    const r=canvas.getBoundingClientRect();dpr=Math.min(2,globalThis.devicePixelRatio||1);w=Math.max(1,r.width);h=Math.max(1,r.height);
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);cam=walkCamera(w,h,focus,0,ext);
  }
  resize();
  const ro=typeof ResizeObserver==='function'?new ResizeObserver(()=>resize()):null;ro?.observe(canvas.parentElement||canvas);
  return {
    ready:Promise.resolve(),
    get personHeight(){return 125*cam.fs;},
    setBang(next){B=next;},
    frame(model,t=performance.now()){
      if(destroyed)return;
      if(model.focus){focus=model.focus;cam=walkCamera(w,h,focus,model.shift||0,ext);}
      ctx.setTransform(dpr,0,0,dpr,0,0);ground(t);
      const list=standing(t);
      for(const p of model.people)list.push([p.x+p.y,()=>person(p,t)]);
      list.sort((a,b)=>a[0]-b[0]);for(const [,draw] of list)draw();
    },
    toMap(clientX,clientY){const r=canvas.getBoundingClientRect(),u=(clientX-r.left-cam.ox)/cam.S,v=(clientY-r.top-cam.oy)/(cam.S*FLAT),x=(u+v)*R2,y=(v-u)*R2;return x>=-.1&&x<=1.1&&y>=-.1&&y<=1.1?[x,y]:null;},
    toScreen(x,y,lift=0){const [a,b]=P(x,y);return [a,b-lift*cam.S/900];},
    anchor(id){const s=L.slots[id];if(!s)return null;const f=fac(id),tall=(TALL[id]||[10,60,90,120])[f.band??bandOf(f.level)];
      if(id==='cong_bang'){const g=gatePosts(L);return {x:(g[0].x+g[1].x)/2,y:(g[0].y+g[1].y)/2,lift:tall+12};}
      return {x:s.x+s.w*.42,y:s.y+s.h*.42,lift:tall+(id==='dai_sanh'?40:24)};},
    resize,
    destroy(){destroyed=true;ro?.disconnect();figures.clear();},
  };
}
