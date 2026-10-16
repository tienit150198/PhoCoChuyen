/** 🏝️ Đảo riêng on the old interface: the island (public/js/island-layout.js) as a flat, warm 2D walk, drawn like the
 * other v4 walks (the figures are look.js paintPlayer). Same renderer contract as the new interface's Phaser scene
 * (client/isometric/private-island.ts): frame(model), toMap(clientX, clientY), toScreen(x, y, lift), personHeight,
 * resize(), destroy(). The scene controller (v4/island-scene.js) owns walking, the live room and the overlays. */
import {figureOf,paintPlayer,CANVAS} from './look.js';
import {inPoly} from '../island-layout.js';

const FLAT=.64;   // the map's y is squashed: a three-quarter view from above
const FIG_H=160,FIG_W=110;

function inset(shore,by){
  const cx=shore.reduce((s,p)=>s+p[0],0)/shore.length,cy=shore.reduce((s,p)=>s+p[1],0)/shore.length;
  return shore.map(([x,y])=>{const d=Math.hypot(x-cx,y-cy)||1,k=Math.max(0,1-by/d);return [cx+(x-cx)*k,cy+(y-cy)*k];});
}
function seeded(seed){let s=seed>>>0||1;return ()=>((s=Math.imul(s^(s>>>15),2246822507)^Math.imul(s^(s>>>13),3266489909))>>>0)/4294967296;}
function darker(hex,k){const n=parseInt(String(hex).slice(1),16);if(!Number.isFinite(n))return hex;const c=v=>Math.max(0,Math.min(255,Math.round(v*k)));return `rgb(${c((n>>16)&255)},${c((n>>8)&255)},${c(n&255)})`;}

/** The camera for a stage of w×h CSS pixels: the map's scale S (px per map unit) and its offset; a phone follows `focus`. */
export function walkCamera(w,h,focus=[.5,.5]){
  const S=Math.max(560,Math.min(1100,Math.min(w/1.02,h/(FLAT*1.04))));
  const mapW=S,mapH=S*FLAT,clamp=(v,lo,hi)=>lo>hi?(lo+hi)/2:Math.max(lo,Math.min(hi,v));
  const ox=clamp(w/2-focus[0]*S,w-mapW-S*.06,S*.06),oy=clamp(h/2-focus[1]*S*FLAT,h-mapH-S*.06,S*.06);
  return {S,ox,oy,fs:S/1400};
}

export function createWalkRenderer(canvas,L){
  const ctx=canvas.getContext('2d'),figures=new Map(),rand=seeded(L.shore.length*977+Math.round(L.villa.x*1000));
  const grass=inset(L.shore,L.sandWidth),swells=[],dots=[];
  for(let i=0;i<60;i++){const x=rand()*1.2-.1,y=rand()*1.2-.1;if(!inPoly(inset(L.shore,-.05),x,y))swells.push([x,y,8+rand()*14,rand()*6]);}
  for(let i=0;i<120;i++){const x=rand(),y=rand();if(inPoly(grass,x,y))dots.push([x,y,4+rand()*6]);}
  const palms=L.palms.map(([x,y])=>[x,y,(rand()-.5)*.5,70+rand()*24,rand()*6]);
  let w=1,h=1,dpr=1,cam=walkCamera(1,1),focus=[L.villa.x,L.villa.y+L.villa.h],destroyed=false;
  const P=(x,y)=>[cam.ox+x*cam.S,cam.oy+y*cam.S*FLAT];
  function poly(list,fill,dy=0){ctx.beginPath();list.forEach(([x,y],i)=>{const [a,b]=P(x,y);i?ctx.lineTo(a,b+dy):ctx.moveTo(a,b+dy);});ctx.closePath();ctx.fillStyle=fill;ctx.fill();}
  function rect(r,fill,dy=0){const [a,b]=P(r.x-r.w/2,r.y-r.h/2),[c,d]=P(r.x+r.w/2,r.y+r.h/2);ctx.fillStyle=fill;ctx.fillRect(a,b+dy,c-a,d-b);return [a,b,c,d];}
  function planks(r){
    rect(r,'#6e4a2e',6);const [a,b,c,d]=rect(r,'#b5844f');ctx.strokeStyle='#8b6038';ctx.lineWidth=1.2;
    const long=r.h>r.w;for(let k=1;k<12;k++){ctx.beginPath();if(long){const y=b+(d-b)*k/12;ctx.moveTo(a,y);ctx.lineTo(c,y);}else{const x=a+(c-a)*k/12;ctx.moveTo(x,b);ctx.lineTo(x,d);}ctx.stroke();}
  }
  function ground(t){
    ctx.fillStyle=L.deep;ctx.fillRect(0,0,w,h);
    poly(inset(L.shore,-.1),L.sea);
    ctx.strokeStyle='rgba(255,255,255,.4)';ctx.lineWidth=2;
    for(const [x,y,r,ph] of swells){const [a,b]=P(x,y),dx=Math.sin(t/1600+ph)*4;ctx.beginPath();ctx.arc(a+dx,b,r*cam.S/700,Math.PI*1.15,Math.PI*1.85);ctx.stroke();}
    for(const d of L.deco)if(d.t==='reef'){const [a,b]=P(d.x,d.y),r=(d.r||.05)*cam.S,cols=['#ff8a7a','#ffc56b','#b48de0','#7fd6c2'];
      for(let i=0;i<8;i++){ctx.fillStyle=cols[i%4]+'bb';ctx.beginPath();ctx.ellipse(a+Math.cos(i*2.4)*r*.6,b+Math.sin(i*2.4)*r*.3,r*.28,r*.16,0,0,Math.PI*2);ctx.fill();}}
    poly(L.shore,darker(L.sand,.72),10);poly(inset(L.shore,-.01),'rgba(255,255,255,.55)');poly(L.shore,L.sand);
    poly(grass,L.grassDark,3);poly(grass,L.grass);
    ctx.fillStyle=L.grassDark+'99';for(const [x,y,r] of dots){const [a,b]=P(x,y);ctx.beginPath();ctx.ellipse(a,b,r*cam.S/900,r*cam.S/2200,0,0,Math.PI*2);ctx.fill();}
    for(const r of [L.dock,...(L.walk||[])])planks(r);
    for(const d of L.deco){
      if(d.t==='strip'){const r={x:d.x,y:d.y,w:d.w||.5,h:d.h||.06},[a,b,c,e]=rect(r,'#5d5a5f');ctx.strokeStyle='#fff';ctx.lineWidth=3;ctx.setLineDash([14,12]);ctx.beginPath();ctx.moveTo(a+8,(b+e)/2);ctx.lineTo(c-8,(b+e)/2);ctx.stroke();ctx.setLineDash([]);}
      if(d.t==='pool'){const r={x:d.x,y:d.y,w:d.w||.14,h:d.h||.06};rect({...r,w:r.w+.015,h:r.h+.02},'#f4efe6');rect(r,'#47b7d8');rect({...r,y:r.y-r.h*.3,h:r.h*.2},'rgba(255,255,255,.35)');}
    }
    if(L.pad.kind==='heli'){const [a,b]=P(L.pad.x,L.pad.y),r=cam.S*.045;ctx.fillStyle='#6b6f74';ctx.beginPath();ctx.ellipse(a,b,r,r*FLAT,0,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle='#ffd75a';ctx.lineWidth=3;ctx.beginPath();ctx.ellipse(a,b,r*.8,r*.8*FLAT,0,0,Math.PI*2);ctx.stroke();
      ctx.fillStyle='#fff';ctx.font=`bold ${Math.round(r*.8)}px sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('H',a,b+1);}
  }
  /** Things that stand up, drawn back to front by where they touch the ground. */
  function standing(t){
    const out=[],k=cam.S/900;
    for(const [x,y,lean,ht,ph] of palms)out.push([y,()=>{const [a,b]=P(x,y),sw=Math.sin(t/1300+ph)*3,top=[a+lean*ht*k+sw,b-ht*k];
      ctx.fillStyle='rgba(0,0,0,.15)';ctx.beginPath();ctx.ellipse(a+14*k,b+2,24*k,7*k,0,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle='#8a6340';ctx.lineWidth=8*k;ctx.beginPath();ctx.moveTo(a,b);ctx.quadraticCurveTo(a+lean*ht*k*.2,b-ht*k*.6,top[0],top[1]);ctx.stroke();
      for(let i=0;i<7;i++){const an=i/7*Math.PI*2,len=36*k;ctx.fillStyle=i%2?'#3f8a3e':'#4fa04a';ctx.beginPath();ctx.moveTo(top[0],top[1]);ctx.lineTo(top[0]+Math.cos(an)*len,top[1]+Math.sin(an)*len*.55+10*k);ctx.lineTo(top[0]+Math.cos(an+.35)*len*.7,top[1]+Math.sin(an+.35)*len*.4+5*k);ctx.fill();}
      ctx.fillStyle='#7a5a32';ctx.beginPath();ctx.arc(top[0]-4*k,top[1]+5*k,4.5*k,0,Math.PI*2);ctx.arc(top[0]+5*k,top[1]+6*k,4.5*k,0,Math.PI*2);ctx.fill();}]);
    const house=(v,floors,wall,roof)=>{
      const [a,b]=P(v.x-v.w/2,v.y+v.h/2),[c]=P(v.x+v.w/2,v.y),fh=30*k,ht=fh*floors,wd=c-a,depth=v.h*cam.S*FLAT;
      ctx.fillStyle='rgba(0,0,0,.16)';ctx.fillRect(a-4,b-4,wd+12,10);
      ctx.fillStyle=darker(wall,.85);ctx.fillRect(a,b-ht-depth*.5,wd,depth*.5);
      ctx.fillStyle=wall;ctx.fillRect(a,b-ht,wd,ht);
      for(let f=0;f<floors;f++)for(let i=0;i<4;i++){if(f===0&&i===1)continue;ctx.fillStyle='#8fc6dc';ctx.fillRect(a+wd*(.1+i*.22),b-fh*(f+1)+fh*.25,wd*.12,fh*.45);}
      ctx.fillStyle='#7a4b2a';ctx.fillRect(a+wd*.33,b-fh*.75,wd*.12,fh*.75);
      const top=b-ht-depth*.5;ctx.fillStyle=roof;ctx.beginPath();ctx.moveTo(a-8*k,top+6*k);ctx.lineTo(a+wd*.2,top-22*k);ctx.lineTo(a+wd*.8,top-22*k);ctx.lineTo(a+wd+8*k,top+6*k);ctx.closePath();ctx.fill();
      ctx.fillStyle=darker(roof,.8);ctx.fillRect(a-8*k,top+2*k,wd+16*k,6*k);
    };
    const v=L.villa;out.push([v.y+v.h/2,()=>house(v,v.floors,v.wall,v.roof)]);
    for(const d of L.deco){
      if(d.t==='hut')out.push([d.y+.02,()=>house({x:d.x,y:d.y,w:.05,h:.04},1,'#c9a77a','#9b6a3c')]);
      else if(d.t==='peak')out.push([d.y+(d.r||.12)*.5,()=>{const [a,b]=P(d.x,d.y+(d.r||.12)*.5),wd=(d.r||.12)*cam.S,ht=wd*.9,rock=L.rock||'#5d5560';
        ctx.fillStyle=darker(rock,.8);ctx.beginPath();ctx.moveTo(a-wd,b);ctx.lineTo(a,b-ht);ctx.lineTo(a,b);ctx.fill();ctx.fillStyle=rock;ctx.beginPath();ctx.moveTo(a,b);ctx.lineTo(a,b-ht);ctx.lineTo(a+wd,b);ctx.fill();
        ctx.fillStyle='#f5f2ee';ctx.beginPath();ctx.moveTo(a-wd*.22,b-ht*.78);ctx.lineTo(a,b-ht);ctx.lineTo(a+wd*.22,b-ht*.78);ctx.lineTo(a,b-ht*.72);ctx.fill();}]);
      else if(d.t==='rocks')out.push([d.y,()=>{const [a,b]=P(d.x,d.y);ctx.fillStyle=L.rock||'#6f6a70';for(let i=0;i<4;i++){ctx.beginPath();ctx.ellipse(a+(i-1.5)*14*k,b-Math.abs(i-1.5)*3*k,12*k,9*k,0,0,Math.PI*2);ctx.fill();}}]);
      else if(d.t==='lighthouse')out.push([d.y,()=>{const [a,b]=P(d.x,d.y);for(let i=0;i<5;i++){ctx.fillStyle=i%2?'#d9483b':'#faf6ee';ctx.fillRect(a-12*k+i*k,b-26*k*(i+1),24*k-2*i*k,27*k);}
        ctx.fillStyle='#34383f';ctx.fillRect(a-11*k,b-150*k,22*k,9*k);ctx.fillStyle='#ffe17a';ctx.fillRect(a-8*k,b-141*k,16*k,12*k);
        const an=t/1100;ctx.fillStyle='rgba(255,243,176,.3)';ctx.beginPath();ctx.moveTo(a,b-135*k);ctx.lineTo(a+Math.cos(an)*130*k,b-135*k+Math.sin(an)*30*k-18*k);ctx.lineTo(a+Math.cos(an)*130*k,b-135*k+Math.sin(an)*30*k+18*k);ctx.fill();}]);
      else if(d.t==='steam')out.push([d.y,()=>{const [a,b]=P(d.x,d.y);for(let i=0;i<3;i++){const p=((t/2600)+i/3)%1;ctx.fillStyle=`rgba(255,255,255,${.5*(1-p)})`;ctx.beginPath();ctx.ellipse(a+(i-1)*12*k,b-10*k-p*60*k,(12+p*14)*k,(8+p*10)*k,0,0,Math.PI*2);ctx.fill();}}]);
    }
    for(const s of L.spots)out.push([s.y-.001,()=>{const [a,b]=P(s.x,s.y),bob=Math.sin(t/700+s.x*9)*4;
      ctx.fillStyle='rgba(255,255,255,.3)';ctx.strokeStyle='rgba(255,255,255,.85)';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(a,b,20*k,9*k,0,0,Math.PI*2);ctx.fill();ctx.stroke();
      ctx.fillStyle='#000';ctx.font=`${Math.round(24*k+6)}px "Segoe UI Emoji","Apple Color Emoji",sans-serif`;ctx.textAlign='center';ctx.textBaseline='bottom';ctx.fillText(s.emoji,a,b-12*k+bob);}]);
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
    const [a,b]=P(p.x,p.y),fs=cam.fs,bob=p.walking?Math.abs(Math.sin(t/110))*3:0,swim=p.pose==='swim',flip=Boolean(p.left);
    ctx.save();ctx.translate(a,b-bob);if(flip)ctx.scale(-1,1);
    if(swim){ctx.beginPath();ctx.rect(-60*fs,-160*fs,120*fs,104*fs);ctx.clip();ctx.translate(0,52*fs);}
    ctx.drawImage(figure(p),-55*fs,-150*fs,FIG_W*fs,FIG_H*fs);ctx.restore();
    if(swim){ctx.strokeStyle='rgba(255,255,255,.8)';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(a,b,30*fs,9*fs,0,0,Math.PI*2);ctx.stroke();}
  }
  function vehicle(v,t){
    const [a,b]=P(v.x,v.y),k=cam.S/900*(v.big?1.3:1)*(v.kind==='solo'?.7:1),lift=v.lift*cam.S/900;
    ctx.save();ctx.translate(a,b);if(v.dir<0)ctx.scale(-1,1);
    ctx.fillStyle='rgba(0,0,0,.16)';ctx.beginPath();ctx.ellipse(0,2,60*k,12*k,0,0,Math.PI*2);ctx.fill();
    ctx.translate(0,-lift);
    if(v.kind==='heli'){ctx.fillStyle='#2f4f7a';ctx.beginPath();ctx.ellipse(0,-30*k,34*k,18*k,0,0,Math.PI*2);ctx.fill();ctx.fillRect(-70*k,-34*k,40*k,7*k);
      ctx.fillStyle='#9fd3ea';ctx.beginPath();ctx.ellipse(16*k,-34*k,13*k,9*k,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='#3a3a3a';ctx.fillRect(-26*k,-10*k,52*k,4*k);
      const r=70*k*Math.cos(t/40);ctx.strokeStyle='rgba(30,30,30,.85)';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(-r,-52*k);ctx.lineTo(r,-52*k);ctx.stroke();}
    else if(v.kind==='plane'){ctx.fillStyle='#f3f4f6';ctx.beginPath();ctx.ellipse(0,-24*k,74*k,13*k,0,0,Math.PI*2);ctx.fill();
      ctx.fillStyle='#d9dde3';ctx.beginPath();ctx.moveTo(-20*k,-24*k);ctx.lineTo(30*k,-24*k);ctx.lineTo(-6*k,-58*k);ctx.fill();ctx.beginPath();ctx.moveTo(-20*k,-22*k);ctx.lineTo(30*k,-22*k);ctx.lineTo(-10*k,6*k);ctx.fill();
      ctx.fillStyle='#c0392b';ctx.beginPath();ctx.moveTo(-74*k,-28*k);ctx.lineTo(-56*k,-28*k);ctx.lineTo(-72*k,-58*k);ctx.fill();
      ctx.fillStyle='#4a6d8c';for(let i=0;i<6;i++){ctx.beginPath();ctx.arc(-36*k+i*14*k,-28*k,3*k,0,Math.PI*2);ctx.fill();}}
    else{ctx.rotate(Math.sin(t/700)*.025);ctx.fillStyle='#fff';ctx.beginPath();ctx.moveTo(-62*k,-6*k);ctx.lineTo(62*k,-12*k);ctx.lineTo(46*k,10*k);ctx.lineTo(-54*k,10*k);ctx.closePath();ctx.fill();
      ctx.fillStyle='#24507a';ctx.fillRect(-54*k,4*k,100*k,5*k);
      if(v.kind==='solo'){ctx.fillStyle='#d9a25a';ctx.fillRect(-30*k,-14*k,40*k,8*k);}
      else{ctx.fillStyle='#eef3f7';ctx.fillRect(-30*k,-30*k,56*k,22*k);ctx.fillStyle='#3d6f96';ctx.fillRect(-24*k,-26*k,44*k,8*k);
        if(!v.big){ctx.strokeStyle='#6b5130';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(-4*k,-30*k);ctx.lineTo(-4*k,-96*k);ctx.stroke();ctx.fillStyle='#fdfaf2';ctx.beginPath();ctx.moveTo(-2*k,-94*k);ctx.lineTo(-2*k,-34*k);ctx.lineTo(40*k,-36*k);ctx.fill();}}}
    ctx.restore();
  }
  function resize(){
    const r=canvas.getBoundingClientRect();dpr=Math.min(2,globalThis.devicePixelRatio||1);w=Math.max(1,r.width);h=Math.max(1,r.height);
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);cam=walkCamera(w,h,focus);
  }
  resize();
  const ro=typeof ResizeObserver==='function'?new ResizeObserver(()=>resize()):null;ro?.observe(canvas.parentElement||canvas);
  return {
    ready:Promise.resolve(),
    get personHeight(){return 150*cam.fs;},
    frame(model,t=performance.now()){
      if(destroyed)return;
      if(model.focus){focus=model.focus;cam=walkCamera(w,h,focus);}
      ctx.setTransform(dpr,0,0,dpr,0,0);ground(t);
      const list=standing(t);
      for(const p of model.people)list.push([p.y,()=>person(p,t)]);
      if(model.vehicle)list.push([model.vehicle.y+.001,()=>vehicle(model.vehicle,t)]);
      list.sort((a,b)=>a[0]-b[0]);for(const [,draw] of list)draw();
    },
    toMap(clientX,clientY){const r=canvas.getBoundingClientRect(),x=(clientX-r.left-cam.ox)/cam.S,y=(clientY-r.top-cam.oy)/(cam.S*FLAT);return x>=-.1&&x<=1.1&&y>=-.1&&y<=1.1?[x,y]:null;},
    toScreen(x,y,lift=0){const [a,b]=P(x,y);return [a,b-lift*cam.S/900];},
    resize,
    destroy(){destroyed=true;ro?.disconnect();figures.clear();},
  };
}
