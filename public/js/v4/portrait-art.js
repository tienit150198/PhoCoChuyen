/** portrait-art.js — 📸 the photos a player photographer makes for another player (game/photo_studio.py, owner 21/10).
 * The deliverable is the game's own render: the server keeps a small JSON (the look snapshot taken at order time, the
 * session's choices, the retouch) and every screen draws it here, with the game's own painters: the character
 * (./look.js figureOf through ./booth-poses.js paintPeople: the real hair, clothes, colours, the pose and the face),
 * the baby in the arms (./baby-art.js), the pet (./pet-art.js, the street's own picture). Nothing is uploaded, so
 * nothing a player draws ever reaches another player's screen. Canvas 2D, no network, no DOM lookups.
 *
 *   W, H                       the print in render units (4:5, a white border and a caption under the photo)
 *   BACKDROPS / LIGHTS ids     the same ids as game/photo_studio.py (tests/test_photo_studio.py checks both lists)
 *   paintPhoto(canvas, photo, {scale, cat, moment, preview}) → Promise   the whole print on the canvas (resized)
 *       photo   {pkg, snap: {me: {n, g, lk}, mate?, baby?, pet?, shop?}, set: {bd, light, frame, pose, face, prop},
 *                q: 'good'|'early'|'blink'|'late'|null, rt: {sang, am, min, vig}, by, day}
 *       cat     the pets catalogue (api.content.journey.pets) to draw a pet; without it the pet is left out
 *       moment  a session's live phase instead of q ('settle' | 'hold' | 'blink' | 'late')
 *       preview true: no paper border (the camera's screen)
 *   photoURL(photo, {width, cat}) → Promise<dataURL>    a cached JPEG of the print (album tiles, frames, profile)
 *   PRODUCT ids                what Sản phẩm draws on the pedestal
 * Everything is drawn from the data: the same photo always gives the same picture (ornaments are seeded by id). */
import {paintPeople} from './booth-poses.js';
import {refURL} from './pet-art.js';
import {t as tr} from './i18n.js';

export const W=480,H=600;
const PAD=22,FOOT=62,AX=PAD,AY=PAD,AW=W-PAD*2,AH=H-PAD-FOOT;
const TAU=Math.PI*2;
const SANS='"Trebuchet MS","Segoe UI",sans-serif',SERIF='"Noto Serif","Times New Roman",serif';

/* ---------------------------------------------------------------- seeded randomness and shapes */
function hash(s){let h=2166136261;for(const ch of String(s)){h^=ch.codePointAt(0);h=Math.imul(h,16777619);}return h>>>0;}
function rng(seed){let a=hash(seed)||1;return()=>{a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const el=(c,x,y,rx,ry,fill,rot=0)=>{c.beginPath();c.ellipse(x,y,Math.max(.1,rx),Math.max(.1,ry),rot,0,TAU);c.fillStyle=fill;c.fill();};
const rr=(c,x,y,w,h,r,fill,stroke,lw=2)=>{c.beginPath();c.roundRect(x,y,w,h,r);if(fill){c.fillStyle=fill;c.fill();}if(stroke){c.strokeStyle=stroke;c.lineWidth=lw;c.stroke();}};
const ln=(c,x,y,x2,y2,col,w=2)=>{c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.beginPath();c.moveTo(x,y);c.lineTo(x2,y2);c.stroke();};
const poly=(c,pts,fill)=>{c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fillStyle=fill;c.fill();};
const lin=(c,x0,y0,x1,y1,stops)=>{const g=c.createLinearGradient(x0,y0,x1,y1);stops.forEach(([o,col])=>g.addColorStop(o,col));return g;};
const rad=(c,x,y,r0,r1,stops)=>{const g=c.createRadialGradient(x,y,r0,x,y,r1);stops.forEach(([o,col])=>g.addColorStop(o,col));return g;};
function flower(c,x,y,s,petal,center,n=5,rot=0){for(let i=0;i<n;i++){const a=rot+i*TAU/n;el(c,x+Math.cos(a)*s*.55,y+Math.sin(a)*s*.55,s*.5,s*.34,petal,a);}el(c,x,y,s*.28,s*.28,center);}
/** Soft out-of-focus lights (a long lens: the background melts). */
function bokeh(c,w,h,rnd,cols,n,{y0=0,y1=1,r0=6,r1=22,a='55'}={}){
  for(let i=0;i<n;i++){const r=r0+rnd()*(r1-r0),x=rnd()*w,y=h*(y0+rnd()*(y1-y0)),col=cols[i%cols.length];
    c.fillStyle=rad(c,x,y,0,r,[[0,col+'cc'],[.6,col+a],[1,col+'00']]);c.beginPath();c.arc(x,y,r,0,TAU);c.fill();}
}
function lantern(c,x,y,s,body,glow=true){
  if(glow){c.fillStyle=rad(c,x,y,0,s*2.6,[[0,'#ffcf6e88'],[1,'#ffcf6e00']]);c.beginPath();c.arc(x,y,s*2.6,0,TAU);c.fill();}
  ln(c,x,y-s*1.5,x,y-s*.9,'#5a3a24',1.4);rr(c,x-s*.35,y-s*.95,s*.7,s*.16,2,'#d9a63c');el(c,x,y,s*.78,s*.8,body);
  for(const k of [.35,.7])c.strokeStyle='#00000026',c.lineWidth=1,c.beginPath(),c.ellipse(x,y,s*.78*k,s*.8,0,0,TAU),c.stroke();
  el(c,x-s*.25,y-s*.25,s*.16,s*.3,'#ffffff44',-.3);rr(c,x-s*.35,y+s*.78,s*.7,s*.16,2,'#d9a63c');ln(c,x,y+s*.95,x,y+s*1.5,'#d9a63c',2);
}
/** A sweep of seamless paper: the wall, the curve, the floor, lit from the front. */
function studio(c,w,h,[top,mid,low]){
  c.fillStyle=lin(c,0,0,0,h,[[0,top],[.62,mid],[.78,low],[1,mid]]);c.fillRect(0,0,w,h);
  c.fillStyle=rad(c,w*.5,h*.42,h*.05,h*.75,[[0,'#ffffff40'],[1,'#00000018']]);c.fillRect(0,0,w,h);
}

/* ---------------------------------------------------------------- the backdrops (game/photo_studio.py BACKDROPS) */
const BD={
  kem:(c,w,h)=>studio(c,w,h,['#f3e6d2','#f8eedf','#e8d6bd']),
  hong:(c,w,h)=>studio(c,w,h,['#f7d3dc','#fbe3e8','#eebfcb']),
  xanh:(c,w,h)=>studio(c,w,h,['#cfe6ef','#e2f1f5','#b9d8e3']),
  den:(c,w,h)=>{studio(c,w,h,['#22212a','#2d2b36','#18171d']);c.fillStyle=rad(c,w*.5,h*.38,0,h*.5,[[0,'#3a3846'],[1,'#3a384600']]);c.fillRect(0,0,w,h);},
  giay:(c,w,h)=>{studio(c,w,h,['#cfd0d3','#e2e2e4','#bdbec2']);const r=rng('giay');for(let i=0;i<260;i++){c.fillStyle=r()<.5?'#ffffff12':'#00000010';c.fillRect(r()*w,r()*h,1.5,1.5);}},
  pho_den:(c,w,h,r)=>{   // Phố đèn lồng: an old street at night, yellow walls, lanterns melting into bokeh
    c.fillStyle=lin(c,0,0,0,h,[[0,'#1d2348'],[.5,'#3b2f55'],[1,'#2a1f2c']]);c.fillRect(0,0,w,h);
    for(const [x,ww,col] of [[-.05,.38,'#caa253'],[.62,.45,'#b98f47']]){rr(c,w*x,h*.18,w*ww,h*.7,0,col);
      for(let i=0;i<3;i++)rr(c,w*(x+.06+i*.11),h*.36,w*.07,h*.16,3,'#5b3c22');rr(c,w*x,h*.16,w*ww,h*.04,0,'#7a4a2c');}
    bokeh(c,w,h,r,['#ffb84d','#ff7a59','#ffd36e','#ff9f6b'],26,{y0:.05,y1:.62,r0:10,r1:30,a:'40'});
    for(const [x,y,col] of [[.12,.12,'#e8473b'],[.3,.2,'#f2a33a'],[.5,.1,'#e8473b'],[.7,.19,'#f2c14b'],[.88,.11,'#e8473b']])lantern(c,w*x,h*y,w*.045,col);
    c.fillStyle=lin(c,0,h*.8,0,h,[[0,'#3a2a2a00'],[1,'#120d14cc']]);c.fillRect(0,h*.8,w,h*.2);
  },
  ho_sen:(c,w,h,r)=>{   // Hồ sen: a morning pond, lotus leaves and pink flowers, trees far away
    c.fillStyle=lin(c,0,0,0,h*.55,[[0,'#cfe7f2'],[1,'#f3efe0']]);c.fillRect(0,0,w,h*.55);
    for(let i=0;i<9;i++){const x=w*(i/8),rr_=w*(.09+r()*.05);el(c,x,h*.5,rr_,h*.08,i%2?'#86a983':'#9cbb8f');}
    c.fillStyle=lin(c,0,h*.5,0,h,[[0,'#a9cfc6'],[1,'#6f9f95']]);c.fillRect(0,h*.5,w,h*.5);
    for(let i=0;i<14;i++){const x=r()*w,y=h*(.55+r()*.4),s=w*(.04+r()*.05);el(c,x,y,s,s*.45,i%3?'#6e9f62':'#5f8f58');ln(c,x,y,x+s*.8,y-s*.08,'#4f7d49',1);}
    for(let i=0;i<7;i++){const x=r()*w,y=h*(.52+r()*.25),s=w*(.025+r()*.02);for(const [dx,col] of [[-.6,'#f7c6d5'],[.6,'#f7c6d5'],[-.3,'#ef9fb8'],[.3,'#ef9fb8'],[0,'#e98aa8']])el(c,x+dx*s,y-s*.4,s*.35,s*.7,col,dx);}
    c.fillStyle='#ffffff30';for(let i=0;i<6;i++)c.fillRect(r()*w,h*(.6+r()*.35),w*.12,1.5);
  },
  cho_hoa:(c,w,h,r)=>{   // Chợ hoa: stalls of flower buckets under an awning, soft bokeh
    c.fillStyle=lin(c,0,0,0,h,[[0,'#fde7d3'],[1,'#f3c9b0']]);c.fillRect(0,0,w,h);
    for(let i=0;i<6;i++){const x=i*w/6;poly(c,[[x,0],[x+w/6,0],[x+w/6,h*.1],[x,h*.13]],i%2?'#e25b5b':'#fff3e6');}
    bokeh(c,w,h,r,['#ff8fab','#ffd36e','#ffffff','#f7a1b9','#b6e3a1'],22,{y0:.15,y1:.55,r0:8,r1:24,a:'50'});
    for(let k=0;k<5;k++){const x=w*(.1+k*.2),y=h*.66;rr(c,x-w*.07,y,w*.14,h*.14,6,['#7c96b3','#b3866a','#8aa37a','#c08aa0','#9b8fc4'][k]);
      for(let i=0;i<9;i++)flower(c,x+(r()-.5)*w*.14,y-r()*h*.08,w*(.018+r()*.012),['#ff8fab','#fff3c4','#e2457a','#f6cf3c','#ffffff'][i%5],'#f6b23e',5,r()*3);}
    c.fillStyle='#7a5a4466';c.fillRect(0,h*.8,w,h*.2);
  },
  cau:(c,w,h,r)=>{   // Cầu gỗ hoàng hôn: sunset, water, a wooden bridge's rail
    c.fillStyle=lin(c,0,0,0,h*.6,[[0,'#3c4f8a'],[.45,'#e98b6b'],[1,'#ffd28a']]);c.fillRect(0,0,w,h*.6);
    c.fillStyle=rad(c,w*.66,h*.5,0,w*.18,[[0,'#fff1c7'],[.4,'#ffd28acc'],[1,'#ffd28a00']]);c.fillRect(0,0,w,h*.7);
    c.fillStyle=lin(c,0,h*.55,0,h,[[0,'#e9a37b'],[1,'#5d5a7a']]);c.fillRect(0,h*.55,w,h*.45);
    c.fillStyle='#ffe2a866';for(let i=0;i<12;i++)c.fillRect(w*.6+(r()-.5)*w*.3,h*(.58+i*.025),w*(.05+r()*.12),2);
    c.fillStyle='#2f2433';for(let i=0;i<5;i++)el(c,w*(.1+i*.08),h*.55,w*.05,h*.02,'#2f2433');
    rr(c,0,h*.7,w,h*.035,0,'#6b4a33');rr(c,0,h*.82,w,h*.04,0,'#5a3c29');for(let i=0;i<9;i++)rr(c,i*w/8-4,h*.68,8,h*.2,2,'#5a3c29');
  },
  chua:(c,w,h,r)=>{   // Chùa Gió Lành: the gate's curved roof, red columns, lanterns, incense haze
    c.fillStyle=lin(c,0,0,0,h,[[0,'#f6dfb3'],[1,'#e9c48b']]);c.fillRect(0,0,w,h);
    rr(c,w*.08,h*.3,w*.84,h*.52,0,'#c9573f');rr(c,w*.08,h*.3,w*.84,h*.04,0,'#a8402f');
    for(const x of [.16,.36,.6,.8])rr(c,w*x,h*.3,w*.05,h*.54,2,'#9c2f24');
    rr(c,w*.42,h*.4,w*.16,h*.1,3,'#3d2a1e');c.fillStyle='#f2c84b';c.font=`700 ${w*.03}px ${SERIF}`;c.textAlign='center';c.textBaseline='middle';c.fillText('GIÓ LÀNH',w*.5,h*.45);
    c.beginPath();c.moveTo(w*-.02,h*.31);c.quadraticCurveTo(w*.08,h*.26,w*.1,h*.16);c.quadraticCurveTo(w*.5,h*.22,w*.9,h*.16);c.quadraticCurveTo(w*.92,h*.26,w*1.02,h*.31);c.closePath();c.fillStyle='#3f5a4a';c.fill();
    c.beginPath();c.moveTo(w*.05,h*.2);c.quadraticCurveTo(w*.5,h*.27,w*.95,h*.2);c.lineTo(w*.95,h*.23);c.quadraticCurveTo(w*.5,h*.3,w*.05,h*.23);c.closePath();c.fillStyle='#d9a63c';c.fill();
    for(const [x,col] of [[.26,'#e8473b'],[.74,'#e8473b']])lantern(c,w*x,h*.4,w*.04,col);
    for(let i=0;i<4;i++){c.strokeStyle='#ffffff44';c.lineWidth=6;c.beginPath();const x=w*(.2+r()*.6);c.moveTo(x,h*.85);c.bezierCurveTo(x+30,h*.7,x-30,h*.6,x+10,h*.45);c.stroke();}
    c.fillStyle='#b88a5a';c.fillRect(0,h*.84,w,h*.16);for(let i=0;i<8;i++)ln(c,0,h*(.86+i*.02),w,h*(.86+i*.02),'#a37647',1);
  },
  dao:(c,w,h,r)=>{   // Đảo riêng: the sea, white sand, a palm tree
    c.fillStyle=lin(c,0,0,0,h*.55,[[0,'#7fc8f0'],[1,'#d8f1fb']]);c.fillRect(0,0,w,h*.55);
    for(const [x,y,s] of [[.2,.14,1],[.72,.1,.8]]){el(c,w*x,h*y,w*.09*s,h*.025*s,'#ffffffdd');el(c,w*(x+.05),h*(y-.012),w*.06*s,h*.022*s,'#ffffffdd');}
    c.fillStyle=lin(c,0,h*.5,0,h*.72,[[0,'#2b9bc4'],[1,'#7fd3e0']]);c.fillRect(0,h*.5,w,h*.22);
    c.fillStyle='#ffffff88';for(let i=0;i<10;i++)c.fillRect(r()*w,h*(.53+r()*.17),w*.08,1.5);
    c.fillStyle=lin(c,0,h*.7,0,h,[[0,'#f6e3b4'],[1,'#e8cc8e']]);c.fillRect(0,h*.7,w,h*.3);
    c.strokeStyle='#7a5636';c.lineWidth=w*.025;c.lineCap='round';c.beginPath();c.moveTo(w*.86,h*.86);c.quadraticCurveTo(w*.92,h*.5,w*.82,h*.2);c.stroke();
    for(let i=0;i<6;i++){const a=-Math.PI*.95+i*Math.PI/5.5;c.fillStyle=i%2?'#3f8f4f':'#4fa35d';c.beginPath();c.ellipse(w*.82+Math.cos(a)*w*.1,h*.2+Math.sin(a)*w*.05+w*.03,w*.12,w*.03,a,0,TAU);c.fill();}
  },
  cuoi:(c,w,h,r)=>{   // Cổng hoa cưới: white drapes, an arch of flowers, soft lights
    c.fillStyle=lin(c,0,0,0,h,[[0,'#fff7f2'],[1,'#f6e1dc']]);c.fillRect(0,0,w,h);
    for(let i=0;i<10;i++){c.fillStyle=i%2?'#ffffffaa':'#f8ece8aa';c.fillRect(i*w/10,0,w/10+1,h*.85);}
    bokeh(c,w,h,r,['#fff1c7','#ffe0ea','#ffffff'],18,{y0:.05,y1:.5,r0:6,r1:16,a:'60'});
    c.strokeStyle='#d8c4a8';c.lineWidth=w*.02;c.beginPath();c.arc(w*.5,h*.6,w*.42,Math.PI,0);c.stroke();
    for(let i=0;i<=22;i++){const a=Math.PI+i*Math.PI/22,x=w*.5+Math.cos(a)*w*.42,y=h*.6+Math.sin(a)*w*.42;
      el(c,x,y,w*.03,w*.018,'#8fb07e',a);flower(c,x+(r()-.5)*8,y+(r()-.5)*8,w*(.022+r()*.012),['#ffffff','#f7c6d5','#fbe3a0','#f2a5bd'][i%4],'#f6cf3c',5,r()*3);}
    c.fillStyle='#e9d6cf';c.fillRect(0,h*.85,w,h*.15);
  },
  ban_sp:(c,w,h)=>{   // Bàn chụp sản phẩm: a pastel wall, a table top, a soft shadow
    c.fillStyle=lin(c,0,0,w,h,[[0,'#e8f0ea'],[1,'#f6e9e1']]);c.fillRect(0,0,w,h*.66);
    el(c,w*.2,h*.2,w*.14,w*.14,'#ffffff55');el(c,w*.82,h*.12,w*.09,w*.09,'#ffffff44');
    c.fillStyle=lin(c,0,h*.66,0,h,[[0,'#d9b996'],[1,'#c19c78']]);c.fillRect(0,h*.66,w,h*.34);ln(c,0,h*.66,w,h*.66,'#b48d69',2);
  },
};

/* ---------------------------------------------------------------- the lights (game/photo_studio.py LIGHTS) */
// back: behind the subject (after the backdrop); front: over everything (the photo's air)
const LT={
  mem:{back:(c,w,h)=>{c.fillStyle=rad(c,w*.3,h*.25,0,w*.9,[[0,'#ffffff30'],[1,'#ffffff00']]);c.fillRect(0,0,w,h);},
       front:(c,w,h)=>{c.fillStyle=rad(c,w*.25,h*.2,0,w,[[0,'#fffaf033'],[1,'#fffaf000']]);c.fillRect(0,0,w,h);}},
  ven:{back:(c,w,h)=>{c.fillStyle=rad(c,w*.5,h*.3,0,w*.55,[[0,'#fff6dd77'],[.5,'#fff6dd22'],[1,'#fff6dd00']]);c.fillRect(0,0,w,h);},
       front:(c,w,h)=>{c.fillStyle=rad(c,w*.5,h*.45,w*.3,w*.85,[[0,'#00000000'],[1,'#00000055']]);c.fillRect(0,0,w,h);}},
  tu_nhien:{back:(c,w,h)=>{c.fillStyle=rad(c,w*.85,h*.05,0,w*.6,[[0,'#fff3c466'],[1,'#fff3c400']]);c.fillRect(0,0,w,h);},
       front:(c,w,h)=>{c.fillStyle='#eaf6ff14';c.fillRect(0,0,w,h);}},
  vang:{back:(c,w,h)=>{c.fillStyle=rad(c,w*.8,h*.15,0,w*.7,[[0,'#ffd27a88'],[1,'#ffd27a00']]);c.fillRect(0,0,w,h);},
       front:(c,w,h)=>{c.save();c.globalCompositeOperation='soft-light';c.fillStyle='#ffb04acc';c.fillRect(0,0,w,h);c.restore();
         for(const [k,r,a] of [[.15,.05,'44'],[.35,.03,'33'],[.55,.07,'22']]){const x=w*(.8-k),y=h*(.15+k*.9);c.fillStyle=rad(c,x,y,0,w*r,[[0,'#fff1c7'+a],[1,'#fff1c700']]);c.beginPath();c.arc(x,y,w*r,0,TAU);c.fill();}}},
  kich:{back:()=>{},
       front:(c,w,h)=>{c.save();c.globalCompositeOperation='multiply';c.fillStyle=lin(c,0,0,w,0,[[0,'#ffffff'],[.45,'#f2eee8'],[1,'#5e5868']]);c.fillRect(0,0,w,h);c.restore();
         c.fillStyle=lin(c,0,0,w,0,[[0,'#ffffff30'],[.4,'#ffffff00']]);c.fillRect(0,0,w,h);}},
};

/* ---------------------------------------------------------------- Sản phẩm (game/photo_studio.py PRODUCTS) */
export const PRODUCT={tra_sua:'🧋',ca_phe:'☕',banh:'🎂',banh_mi:'🥖',hoa:'💐',vay:'👗',giay:'👟',son:'💄',nhan:'💍',gau:'🧸',cay:'🪴',sach:'📚'};
function product(c,w,h,shop,ok){
  const p=PRODUCT[shop?.p]||'🎁',cx=w*.5,top=h*.6,pw=w*.27,r=rng('sp:'+(shop?.p||''));
  // a round pedestal on the table, a soft shadow, a few petals and leaves around
  el(c,cx,h*.84,pw*1.25,h*.03,'#00000026');
  c.fillStyle=lin(c,cx-pw,0,cx+pw,0,[[0,'#e9e1d6'],[.45,'#fffdf9'],[1,'#ddd2c4']]);c.fillRect(cx-pw,top,pw*2,h*.23);
  el(c,cx,top+h*.23,pw,h*.03,'#ddd2c4');el(c,cx,top,pw,h*.035,'#fffdf9');c.strokeStyle='#e0d3c2';c.lineWidth=1.5;c.beginPath();c.ellipse(cx,top,pw,h*.035,0,0,TAU);c.stroke();
  for(let i=0;i<7;i++){const x=w*(.08+r()*.84),y=h*(.86+r()*.1);if(Math.abs(x-cx)<pw*1.2)continue;
    if(i%2)el(c,x,y,w*.025,w*.011,'#8fb07e',r()*3);else flower(c,x,y,w*.016,['#f7c6d5','#fff3c4','#f2a5bd'][i%3],'#f6cf3c',5,r()*3);}
  el(c,cx,top-h*.005,pw*.7,h*.018,'#00000022');
  c.save();c.translate(cx,top-h*.125);if(!ok)c.rotate(-.08);
  c.font=`${Math.round(w*.4)}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif`;c.textAlign='center';c.textBaseline='middle';c.fillStyle='#000';c.globalAlpha=1;c.fillText(p,0,0);c.restore();   // an emoji takes the fill's alpha
  const name=String(shop?.n||'').slice(0,32);
  if(name){c.font=`700 ${Math.round(w*.04)}px ${SERIF}`;const tw=Math.min(w*.7,c.measureText(tr(name)).width+28);
    rr(c,cx-tw/2,h*.08,tw,h*.075,8,'#ffffffd9','#d9c3a8',1.5);c.fillStyle='#6b4d3a';c.textAlign='center';c.textBaseline='middle';c.fillText(tr(name),cx,h*.08+h*.0375,tw-16);}
}

/* ---------------------------------------------------------------- the people, the baby, the pet */
const PETS=new Map();
function petImage(cat,ref){
  if(!cat||!ref)return Promise.resolve(null);
  const key=JSON.stringify(ref);let p=PETS.get(key);
  if(!p){if(PETS.size>30)PETS.clear();
    p=new Promise(ok=>{const url=refURL(cat,ref,'sit',220);if(!url){ok(null);return;}const im=new Image();const t=setTimeout(()=>ok(null),2500);
      im.onload=()=>{clearTimeout(t);ok(im);};im.onerror=()=>{clearTimeout(t);ok(null);};im.src=url;});PETS.set(key,p);}
  return p;
}
const MOMENT={early:'settle',blink:'blink',late:'late',good:'hold'};
function peopleOf(snap,st,moment){
  const face=moment==='late'?'ngo_ngac':st.face,pose=moment==='late'?'dung':st.pose;
  const over=moment==='blink'?{eyes:'closed'}:moment==='late'?{lean:.2,tilt:.16}:{};
  const me={lk:snap.me?.lk,g:snap.me?.g,pose,face,prop:st.prop||'none',...over};
  if(snap.baby)me.bb={g:snap.baby.g,o:snap.baby.o};
  const out=[me];
  if(snap.mate)out.push({lk:snap.mate.lk,g:snap.mate.g,pose,face:face==='le_luoi'||face==='phong_ma'?face:face,prop:'none',...over,...(moment==='late'?{lean:-.2}:{})});
  return out;
}
/** The subject layer (people + pet) on its own canvas, `k` × the photo area, people laid out by paintPeople. */
function subject(snap,st,moment,petIm,k){
  const cv=document.createElement('canvas');cv.width=Math.round(AW*k);cv.height=Math.round(AH*k);
  const c=cv.getContext('2d');c.scale(k,k);
  const ppl=peopleOf(snap,st,moment),petW=petIm?AW*.26:0;
  const xs=paintPeople(c,ppl,AW-petW,AH,{sign:'XINH QUÁ!'});
  const s=xs[0]?.s||AH*.82/150,foot=AH*.955;
  if(petIm){const ph=Math.min(AH*.34,96*s*1.05),pw=ph*petIm.naturalWidth/Math.max(1,petIm.naturalHeight);
    const x=Math.min(AW-pw-4,(xs[xs.length-1]?.x||AW*.5)+40*s);el(c,x+pw/2,foot-2,pw*.36,ph*.05,'#0000001f');c.drawImage(petIm,x,foot-ph,pw,ph);}
  const mid=xs.length?(xs[0].x+xs[xs.length-1].x)/2:AW/2;
  return {cv,cx:petIm?(mid+(xs[xs.length-1]?.x||mid)+60*s)/2:mid,mid,top:foot-128*s,s};
}
// the characters are chibi (the head is half the body): half-body and close-up need only a gentle zoom
const ZOOM={toan:1,nua:1.3,can:1.75};
/** Where the camera looks (in the photo area's units): the window of the subject layer for this framing. */
function framing(frame,sub){
  const z=ZOOM[frame]||1;
  const cw=AW/z,ch=AH/z;
  // whole body: everyone and the pet; closer in: the people (a pet beside them may be cut, like a real lens)
  let x=(frame==='toan'?sub.cx:sub.mid)-cw/2,y=frame==='toan'?0:sub.top-ch*(frame==='can'?.1:.08);
  x=Math.max(0,Math.min(AW-cw,x));y=Math.max(0,Math.min(AH-ch,y));
  return {x,y,w:cw,h:ch,z};
}

/* ---------------------------------------------------------------- retouch (game/photo_studio.py RETOUCH) */
function retouch(c,w,h,rt,src){
  const k=v=>Number.isFinite(v)?v:0,sang=k(rt?.sang),am=k(rt?.am),min=k(rt?.min),vig=k(rt?.vig);
  if(min>0){   // smooth skin: a soft copy over itself
    const t=document.createElement('canvas');t.width=Math.max(1,Math.round(w/4));t.height=Math.max(1,Math.round(h/4));
    t.getContext('2d').drawImage(src,0,0,t.width,t.height);c.save();c.globalAlpha=.1*min;c.imageSmoothingQuality='high';c.drawImage(t,0,0,w,h);c.restore();}
  if(sang){c.save();c.globalCompositeOperation=sang>0?'screen':'multiply';c.fillStyle=sang>0?`rgba(255,250,240,${.09*sang})`:`rgba(40,30,30,${.12*-sang})`;c.fillRect(0,0,w,h);c.restore();}
  if(am){c.save();c.globalCompositeOperation='soft-light';c.fillStyle=am>0?`rgba(255,150,60,${.22*am})`:`rgba(60,130,255,${.22*-am})`;c.fillRect(0,0,w,h);c.restore();}
  if(vig){c.fillStyle=rad(c,w/2,h/2,Math.min(w,h)*.35,Math.max(w,h)*.75,[[0,'rgba(0,0,0,0)'],[1,`rgba(20,12,10,${.32*vig})`]]);c.fillRect(0,0,w,h);}
}

/* ---------------------------------------------------------------- the print */
/** The photo itself (backdrop, subject, light, the moment, retouch) into a w × h canvas context at its origin. */
async function paintArea(c,w,h,photo,{cat,moment}={}){
  const snap=photo?.snap||{},st=photo?.set||{},pkg=photo?.pkg||snap.pkg;
  const m=moment||MOMENT[photo?.q]||'hold';
  const src=c.canvas;
  c.save();c.beginPath();c.rect(0,0,w,h);c.clip();c.scale(w/AW,h/AH);
  (BD[st.bd]||BD.kem)(c,AW,AH,rng('bd:'+st.bd));
  (LT[st.light]||LT.mem).back(c,AW,AH);
  if(pkg==='san_pham')product(c,AW,AH,snap.shop,m!=='late');
  else{
    const petIm=snap.pet?await petImage(cat,snap.pet):null;
    const k=Math.min(3,(ZOOM[st.frame]||1)*1.4);
    const sub=subject(snap,st,m,petIm,k),fr=framing(st.frame,sub);
    const sx=fr.x*k,sy=fr.y*k,sw=fr.w*k,sh=fr.h*k;
    // the floor's contact shadow (whole body only)
    if(st.frame==='toan'){c.fillStyle=rad(c,AW/2,AH*.95,0,AW*.4,[[0,'#00000022'],[1,'#00000000']]);c.fillRect(0,AH*.85,AW,AH*.15);}
    if(m==='settle'){c.save();c.globalAlpha=.42;for(const d of [-7,6])c.drawImage(sub.cv,sx-d,sy,sw,sh,0,0,AW,AH);c.restore();c.globalAlpha=.5;c.drawImage(sub.cv,sx,sy,sw,sh,0,0,AW,AH);c.globalAlpha=1;}
    else c.drawImage(sub.cv,sx,sy,sw,sh,0,0,AW,AH);
  }
  (LT[st.light]||LT.mem).front(c,AW,AH);
  if(m==='late'&&pkg==='san_pham'){c.fillStyle=lin(c,0,0,AW,AH,[[.3,'#ffffff00'],[.45,'#ffffffaa'],[.6,'#ffffff00']]);c.fillRect(0,0,AW,AH);}   // a glare
  c.restore();
  if(photo?.rt)retouch(c,w,h,photo.rt,src);
}

const fitText=(c,s,max,size,weight,font)=>{c.font=`${weight} ${size}px ${font}`;const w=c.measureText(s).width;return w>max?Math.max(9,Math.floor(size*max/w)):size;};
/** The whole print on `cv` (resized to W×H × scale). preview: only the photo, no paper. */
export async function paintPhoto(cv,photo,{scale=1,cat=null,moment=null,preview=false}={}){
  const pw=preview?AW:W,ph=preview?AH:H;
  cv.width=Math.round(pw*scale);cv.height=Math.round(ph*scale);
  const c=cv.getContext('2d');c.setTransform(1,0,0,1,0,0);
  if(preview){await paintArea(c,cv.width,cv.height,photo,{cat,moment});return cv;}
  c.scale(scale,scale);
  c.fillStyle='#fffaf3';c.fillRect(0,0,W,H);
  c.fillStyle=lin(c,0,0,0,H,[[0,'#ffffff'],[1,'#f6efe4']]);c.fillRect(0,0,W,H);
  // the photo, drawn at the print's real pixels (crisp at any scale)
  const t=document.createElement('canvas');t.width=Math.round(AW*scale);t.height=Math.round(AH*scale);
  await paintArea(t.getContext('2d'),t.width,t.height,photo,{cat,moment});
  c.save();c.shadowColor='#5a40301f';c.shadowBlur=6;c.shadowOffsetY=2;c.fillStyle='#ffffff';c.fillRect(AX,AY,AW,AH);c.restore();
  c.drawImage(t,AX,AY,AW,AH);
  c.strokeStyle='#00000014';c.lineWidth=1;c.strokeRect(AX+.5,AY+.5,AW-1,AH-1);
  // the caption: the studio and the photographer, the date
  const by=String(photo?.by||'').slice(0,24),day=String(photo?.day||''),y=AY+AH+FOOT/2+2;
  // 💍 a couple's trip / ceremony photo (game/wedding_life.py) names its place and moment instead of a studio
  const head=photo?.head?tr(String(photo.head).slice(0,40)):`Tách Tách · ${by||tr('Phố Có Chuyện')}`;
  const sub=photo?.sub?tr(String(photo.sub).slice(0,60)):tr('Ảnh chụp ở Phố Có Chuyện');
  c.fillStyle='#6b4d3a';c.textBaseline='middle';c.textAlign='left';
  c.font=`italic 700 ${fitText(c,head,W*.6,19,'italic 700',SERIF)}px ${SERIF}`;c.fillText(head,AX+2,y-6);
  c.font=`600 ${fitText(c,sub,W*.62,11,600,SANS)}px ${SANS}`;c.fillStyle='#a0856f';c.fillText(sub,AX+2,y+14);
  if(day){c.textAlign='right';c.font=`700 15px "Courier New",ui-monospace,monospace`;c.fillStyle='#d0763f';c.fillText(day,AX+AW-2,y-4);}
  return cv;
}

const URLS=new Map();
/** A cached JPEG data URL of the print, `width` px wide (album tiles, frames at home, the profile card). */
export function photoURL(photo,{width=240,cat=null,preview=false}={}){
  const key=JSON.stringify([photo?.id||'',photo?.set,photo?.q,photo?.rt,photo?.head||'',width,preview,!!cat]);
  let p=URLS.get(key);
  if(!p){if(URLS.size>80)URLS.clear();
    p=(async()=>{const cv=document.createElement('canvas');await paintPhoto(cv,photo,{scale:width/(preview?AW:W),cat,preview});
      let url='';try{url=cv.toDataURL('image/jpeg',.86);}catch{url='';}return url;})().catch(e=>{console.warn('ảnh chụp:',e);URLS.delete(key);return '';});
    URLS.set(key,p);}
  return p;
}
