/** booth-stickers.js — the decoration stickers of the fair photobooth (owner 03/10 22:00: "thêm nhiều icon biểu cảm,
 * động tác,... cho xinh nhé, trang trí nữa, cho trang trí kéo thả không giới hạn nhé"). The editor drags them onto the
 * finished print; this module only draws them. Canvas 2D only: no images, no fonts to fetch, no DOM at import.
 *
 *   DECO_CATS              [{id, emoji, name}]          the picker's tabs, in order
 *   DECO                   [{id, cat, name, emoji}]     every sticker (a text sticker's name is its word)
 *   DECO_BY / knownDeco(id)
 *   DECO_FILL              decoSprite(id, px) is a px × px canvas with drawDeco(c, id, px * DECO_FILL) at its centre
 *   drawDeco(c, id, size, {t})   the sticker centred on (0, 0), all of it (white die-cut edge and its shadow too)
 *                          inside ±size/2; t translates the words of the text stickers; an unknown id draws nothing
 *   decoSprite(id, px, {t})      cached canvas (px rounded to a multiple of 16, 32…512); null without a document
 *   decoThumb(id, px=96, {t})    its dataURL (cached), '' without a document
 *
 * Every sticker is drawn in a 100 × 100 box (−50…50): its silhouette in white with a soft shadow (the die-cut edge),
 * then the art with a brown line. */

const TAU=Math.PI*2;
const FONT='"Trebuchet MS", "Segoe UI", "Arial Rounded MT Bold", sans-serif';
const INK='#705140',EYE='#4a3328',WHITE='#ffffff';
const CUT=14;          // die-cut line width (7 units outside the silhouette)
const G=0.91;          // the art's 100-box shrinks by this so the edge and shadow stay inside ±50
export const DECO_FILL=0.98;

/* ---------------------------------------------------------------- paths (100-unit space) */
const P=()=>new Path2D();
function pc(p,x,y,r){p.moveTo(x+r,y);p.arc(x,y,r,0,TAU);return p;}
function pe(p,x,y,rx,ry,rot=0){p.moveTo(x+rx*Math.cos(rot),y+rx*Math.sin(rot));p.ellipse(x,y,rx,ry,rot,0,TAU);return p;}
function pr(p,x,y,w,h,r){r=Math.max(0,Math.min(r,w/2,h/2));p.moveTo(x+r,y);p.arcTo(x+w,y,x+w,y+h,r);p.arcTo(x+w,y+h,x,y+h,r);p.arcTo(x,y+h,x,y,r);p.arcTo(x,y,x+w,y,r);p.closePath();return p;}
function pp(p,pts){p.moveTo(pts[0][0],pts[0][1]);for(let i=1;i<pts.length;i++)p.lineTo(pts[i][0],pts[i][1]);p.closePath();return p;}
/** heart centred on (x, y), about 2s wide and 1.7s tall, turned by rot */
function ph(p,x,y,s,rot=0){
  const cs=Math.cos(rot),sn=Math.sin(rot),T=(u,v)=>[x+(u*cs-v*sn)*s,y+(u*sn+v*cs)*s-0];
  const k=[[0,.84],[-.2,.64],[-1,.29],[-1,-.31],[-1,-.86],[-.3,-1.06],[0,-.56]];
  const m=([u,v])=>T(u,v),mm=([u,v])=>T(-u,v);
  p.moveTo(...m(k[0]));p.bezierCurveTo(...m(k[1]),...m(k[2]),...m(k[3]));p.bezierCurveTo(...m(k[4]),...m(k[5]),...m(k[6]));
  p.bezierCurveTo(...mm(k[5]),...mm(k[4]),...mm(k[3]));p.bezierCurveTo(...mm(k[2]),...mm(k[1]),...mm(k[0]));p.closePath();return p;
}
function pstar(p,x,y,R,r,n=5,a0=-Math.PI/2){for(let i=0;i<n*2;i++){const a=a0+i*Math.PI/n,q=i%2?r:R,X=x+Math.cos(a)*q,Y=y+Math.sin(a)*q;i?p.lineTo(X,Y):p.moveTo(X,Y);}p.closePath();return p;}
function pspark(p,x,y,R,k=.2){const q=R*k;p.moveTo(x,y-R);p.quadraticCurveTo(x+q,y-q,x+R,y);p.quadraticCurveTo(x+q,y+q,x,y+R);p.quadraticCurveTo(x-q,y+q,x-R,y);p.quadraticCurveTo(x-q,y-q,x,y-R);p.closePath();return p;}
function pdrop(p,x,y,r){p.moveTo(x,y-r*1.9);p.bezierCurveTo(x+r*.25,y-r*1.2,x+r,y-r*.55,x+r,y);p.arc(x,y,r,0,Math.PI);p.bezierCurveTo(x-r,y-r*.55,x-r*.25,y-r*1.2,x,y-r*1.9);p.closePath();return p;}
function pscallop(p,x,y,r,n,b){for(let i=0;i<n;i++){const a=i*TAU/n;pc(p,x+Math.cos(a)*r,y+Math.sin(a)*r,b);}return pc(p,x,y,r);}
function pcloud(p,x,y,s){pc(p,x-s*.55,y+s*.05,s*.42);pc(p,x,y-s*.18,s*.56);pc(p,x+s*.55,y+s*.05,s*.42);return pr(p,x-s*.95,y,s*1.9,s*.48,s*.24);}
/** a thick segment as a closed shape */
function pseg(p,x1,y1,x2,y2,w){const a=Math.atan2(y2-y1,x2-x1),dx=Math.sin(a)*w/2,dy=-Math.cos(a)*w/2;
  p.moveTo(x1+dx,y1+dy);p.lineTo(x2+dx,y2+dy);p.arc(x2,y2,w/2,a-Math.PI/2,a+Math.PI/2);p.lineTo(x1-dx,y1-dy);p.arc(x1,y1,w/2,a+Math.PI/2,a+Math.PI*1.5);p.closePath();return p;}

/* ---------------------------------------------------------------- paint */
/** fill a (many-part) shape with a brown line `lw` outside it (inner joins hidden) */
function blob(c,p,fill,ink=INK,lw=2.6){c.lineJoin='round';if(ink&&lw){c.strokeStyle=ink;c.lineWidth=lw*2;c.stroke(p);}if(fill){c.fillStyle=fill;c.fill(p);}}
function fill(c,p,f){c.fillStyle=f;c.fill(p);}
function line(c,pts,col,w){c.beginPath();c.moveTo(pts[0][0],pts[0][1]);for(let i=1;i<pts.length;i++)c.lineTo(pts[i][0],pts[i][1]);c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.lineJoin='round';c.stroke();}
function arcl(c,x,y,r,a0,a1,col,w){c.beginPath();c.arc(x,y,r,a0,a1);c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.stroke();}
function curve(c,x0,y0,cx,cy,x1,y1,col,w){c.beginPath();c.moveTo(x0,y0);c.quadraticCurveTo(cx,cy,x1,y1);c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.stroke();}
function stops(g,cols){cols.forEach((s,i)=>g.addColorStop(i/(cols.length-1),s));return g;}
const lg=(c,x0,y0,x1,y1,cols)=>stops(c.createLinearGradient(x0,y0,x1,y1),cols);
const rg=(c,x0,y0,r0,x1,y1,r1,cols)=>stops(c.createRadialGradient(x0,y0,r0,x1,y1,r1),cols);
const shine=(c,x,y,rx,ry,rot=0,a=.6)=>fill(c,pe(P(),x,y,rx,ry,rot),`rgba(255,255,255,${a})`);
const blush=(c,x,y,rx=7,ry=4.2,a=.5)=>fill(c,pe(P(),x,y,rx,ry),`rgba(255,110,135,${a})`);
function clipTo(c,p,fn){c.save();c.clip(p);fn();c.restore();}
function sparkle(c,x,y,R,col='#ffcf3d',lw=1.6){blob(c,pspark(P(),x,y,R),col,INK,lw);}

/** the die-cut: the silhouette fat in white, one soft shadow */
function cut(c,k,p,w=CUT){
  c.save();c.shadowColor='rgba(0,0,0,.18)';c.shadowOffsetX=0;c.shadowOffsetY=1.6*k;c.shadowBlur=1.6*k;
  c.lineJoin='round';c.lineCap='round';c.strokeStyle=WHITE;c.lineWidth=w;c.stroke(p);
  c.shadowColor='transparent';c.fillStyle=WHITE;c.fill(p);c.restore();
}

/* ---------------------------------------------------------------- faces */
const SUN=['#fff2ae','#ffd64f','#f3b233'];
function face(c,x=0,y=0,r=38,cols=SUN){blob(c,pc(P(),x,y,r),rg(c,x-r*.3,y-r*.42,r*.08,x,y,r*1.02,cols));shine(c,x-r*.4,y-r*.56,r*.22,r*.11,-.55,.6);}
function smileD(c,x,y,w,h){const m=P();m.moveTo(x-w,y);m.lineTo(x+w,y);m.bezierCurveTo(x+w,y+h*1.3,x-w,y+h*1.3,x-w,y);m.closePath();
  blob(c,m,'#8a3b33',EYE,1.4);clipTo(c,m,()=>fill(c,pe(P(),x,y+h*.95,w*.55,h*.42),'#ff8a9a'));}
const cheeks=(c,y=9,x=24,a=.5)=>{blush(c,-x,y,7,4.2,a);blush(c,x,y,7,4.2,a);};

/* ---------------------------------------------------------------- the stickers */
// sil(p): the silhouette (cached); art(c, o): the colours. A sticker with draw(c, k, o) does both itself (words).
const ART={
  /* --- mat: faces */
  cuoi_hip:{sil:p=>pc(p,0,0,38),art(c){face(c);
    arcl(c,-13,-3,7,Math.PI*1.1,Math.PI*1.9,EYE,4.2);arcl(c,13,-3,7,Math.PI*1.1,Math.PI*1.9,EYE,4.2);
    smileD(c,0,7,15,13);cheeks(c,7,25,.55);}},
  mat_tim:{sil:p=>{pc(p,0,2,37);ph(p,29,-29,10,.3);},art(c){face(c,0,2,37);
    for(const x of[-13,13]){blob(c,ph(P(),x,-3,10.5),lg(c,0,-14,0,8,['#ff8a80','#e2574c']),EYE,1.4);shine(c,x-4,-6,2.6,1.6,-.6,.8);}
    smileD(c,0,11,11,9);cheeks(c,11,25,.45);
    blob(c,ph(P(),29,-29,10,.3),lg(c,20,-38,36,-20,['#ffb3cf','#ff6f9f']),INK,2);shine(c,25,-32,2.6,1.6,-.4,.8);}},
  long_lanh:{sil:p=>{pc(p,0,3,36);pspark(p,-29,-28,12);pspark(p,31,-27,8.5);},art(c){face(c,0,3,36);
    for(const x of[-13,13]){fill(c,pe(P(),x,0,8.6,10.6),lg(c,0,-10,0,11,['#3e2a2a','#6b4a7a']));
      fill(c,pc(P(),x+3,-4,3.8),WHITE);fill(c,pc(P(),x-3.2,4.5,1.9),WHITE);fill(c,pspark(P(),x+3.4,4.6,2.6),'#ffe680');}
    arcl(c,-3.6,15,3.6,.1,Math.PI-.1,EYE,2.8);arcl(c,3.6,15,3.6,.1,Math.PI-.1,EYE,2.8);cheeks(c,13,25,.5);
    sparkle(c,-29,-28,12);sparkle(c,31,-27,8.5,'#ffb3cf');}},
  le_luoi:{sil:p=>pc(p,0,0,38),art(c){face(c);
    line(c,[[-20,-10],[-10,-5],[-20,0]],EYE,4.2);fill(c,pe(P(),13,-5,4.6,6.6),EYE);fill(c,pc(P(),14.8,-7.6,1.8),WHITE);
    const t=P();t.moveTo(2,13);t.lineTo(17,13);t.lineTo(17,22);t.arc(9.5,22,7.5,0,Math.PI);t.closePath();
    blob(c,t,'#ff8a9a',EYE,1.4);line(c,[[9.5,16],[9.5,23]],'#e0607a',2);
    arcl(c,0,0,15,.2*Math.PI,.8*Math.PI,EYE,3.8);cheeks(c,8,25,.5);}},
  khoc_nhe:{sil:p=>{pc(p,0,0,37);pdrop(p,-36,-10,5.5);pdrop(p,37,-6,4.5);},art(c){face(c,0,0,37);
    line(c,[[-21,-14],[-8,-19]],EYE,3.4);line(c,[[21,-14],[8,-19]],EYE,3.4);
    for(const x of[-14,14]){clipTo(c,pc(P(),0,0,37),()=>fill(c,pr(P(),x-4,-3,8,44,4),'rgba(120,205,235,.85)'));line(c,[[x-7,-5],[x+7,-5]],EYE,4.2);}
    const m=P();m.moveTo(-10,22);m.quadraticCurveTo(0,4,10,22);m.quadraticCurveTo(0,26,-10,22);m.closePath();blob(c,m,'#8a3b33',EYE,1.4);
    blob(c,pdrop(P(),-36,-10,5.5),'#8fd3ee',INK,1.6);blob(c,pdrop(P(),37,-6,4.5),'#8fd3ee',INK,1.6);shine(c,-37.5,-10,1.6,2.4,0,.9);}},
  ngai:{sil:p=>{pc(p,0,2,37);pdrop(p,30,-31,6);},art(c){face(c,0,2,37,['#ffeeb0','#ffcf5a','#f2a73a']);
    arcl(c,-13,-4,6.2,.15*Math.PI,.85*Math.PI,EYE,3.8);arcl(c,13,-4,6.2,.15*Math.PI,.85*Math.PI,EYE,3.8);
    for(const x of[-22,22]){fill(c,pe(P(),x,10,10,6.2),'rgba(255,100,130,.62)');for(const d of[-5,0,5])line(c,[[x+d-1.8,13],[x+d+1.8,7]],'rgba(214,60,95,.8)',1.6);}
    const m=P();m.moveTo(-7,17);m.quadraticCurveTo(-3.5,13.5,0,17);m.quadraticCurveTo(3.5,20.5,7,17);c.strokeStyle=EYE;c.lineWidth=3;c.lineCap='round';c.stroke(m);
    blob(c,pdrop(P(),30,-31,6),'#8fd3ee',INK,1.6);shine(c,28.5,-31,1.6,2.6,0,.9);}},
  gian_doi:{sil:p=>{pc(p,-1,3,37);pc(p,28,-28,12);},art(c){face(c,-1,3,37,['#ffd0a6','#ff9a6a','#e8604c']);
    fill(c,pe(P(),-22,13,9,7),'rgba(255,90,90,.45)');fill(c,pe(P(),20,13,9,7),'rgba(255,90,90,.45)');
    line(c,[[-23,-11],[-8,-5]],EYE,4.6);line(c,[[21,-11],[6,-5]],EYE,4.6);
    fill(c,pe(P(),-14,2,3.6,4.6),EYE);fill(c,pe(P(),12,2,3.6,4.6),EYE);
    arcl(c,-1,24,6.5,1.15*Math.PI,1.85*Math.PI,EYE,3.6);
    blob(c,pc(P(),28,-28,10.5),'#fff3f0',INK,1.8);
    for(const[sx,sy]of[[1,1],[1,-1],[-1,1],[-1,-1]]){const a=Math.atan2(-sy,-sx);arcl(c,28+sx*5.6,-28+sy*5.6,4.4,a-1.1,a+1.1,'#e2574c',2.8);}}},
  ngu_zzz:{sil:p=>{pc(p,-5,6,35);pc(p,22,-25,10.5);pc(p,34,-36,7);},art(c){face(c,-5,6,35);
    arcl(c,-17,1,6,.15*Math.PI,.85*Math.PI,EYE,3.6);arcl(c,7,1,6,.15*Math.PI,.85*Math.PI,EYE,3.6);
    fill(c,pe(P(),-5,21,3.6,4.2),'#8a3b33');cheeks(c,12,-5+24,.45);
    fill(c,pc(P(),9,15,6),'rgba(160,220,245,.7)');arcl(c,9,15,6,0,TAU,'rgba(91,182,217,.9)',1.2);shine(c,7,13,1.8,1.2,-.5,.9);
    c.textAlign='center';c.textBaseline='middle';c.lineJoin='round';
    for(const[x,y,s]of[[22,-25,15],[34,-36,10]]){c.font=`900 ${s}px ${FONT}`;c.strokeStyle='#2f7fa3';c.lineWidth=s*.22;c.strokeText('Z',x,y+1);c.fillStyle='#5bb6d9';c.fillText('Z',x,y+1);}}},
  kinh_ram:{sil:p=>{pc(p,0,2,37);pspark(p,30,-28,9);},art(c){face(c,0,2,37);
    for(const x of[-17,17]){const g=pr(P(),x-13,-12,26,17,7);blob(c,g,lg(c,0,-12,0,6,['#5a4870','#2a2233']),EYE,1.6);
      clipTo(c,g,()=>{line(c,[[x-9,7],[x+3,-14]],'rgba(255,255,255,.35)',4);line(c,[[x-1,7],[x+7,-6]],'rgba(255,255,255,.22)',2);});}
    line(c,[[-4,-7],[4,-7]],EYE,3);line(c,[[-30,-8],[-36,-11]],EYE,3);line(c,[[30,-8],[36,-11]],EYE,3);
    const m=P();m.moveTo(-9,18);m.quadraticCurveTo(5,25,14,13);c.strokeStyle=EYE;c.lineWidth=3.8;c.lineCap='round';c.stroke(m);
    cheeks(c,13,26,.4);sparkle(c,30,-28,9);}},
  like:{sil:p=>{pr(p,-26,-4,14,38,4);pr(p,-14,-6,26,42,10);for(let i=0;i<4;i++)pr(p,0,-6+i*10.5,28,10.5,5.2);pr(p,-12,-39,15,40,7.5);pspark(p,27,-27,10);},
    art(c){const sk=lg(c,0,-40,0,36,['#ffe68a','#ffd14d','#f3b233']);
      blob(c,pr(P(),-27,-5,15,40,4),lg(c,0,-5,0,35,['#7fcbe6','#5bb6d9']),INK,2.4);
      const h=P();pr(h,-14,-6,26,42,10);for(let i=0;i<4;i++)pr(h,0,-6+i*10.5,28,10.5,5.2);pr(h,-12,-39,15,40,7.5);blob(c,h,sk,INK,2.6);
      for(let i=1;i<4;i++)line(c,[[11,-6+i*10.5],[24,-6+i*10.5]],INK,2);
      line(c,[[-12,-4],[3,-4]],INK,2);curve(c,3,-4,7,9,4,30,INK,2);
      shine(c,-7,-30,2.6,6,0,.55);fill(c,pr(P(),-25,2,4,26,2),'rgba(255,255,255,.4)');
      sparkle(c,27,-27,10);}},

  /* --- tim: hearts and sparkles */
  tim_do:{sil:p=>ph(p,0,1,38),art(c){blob(c,ph(P(),0,1,38),rg(c,-14,-14,4,0,0,44,['#ff9a8f','#e8564b','#c0392b']),INK,2.8);
    shine(c,-18,-11,9,5,-.75,.7);fill(c,pc(P(),-25,2,2.6),'rgba(255,255,255,.65)');shine(c,15,-16,4,2.2,.6,.35);}},
  tim_hong:{rot:-8,sil:p=>{ph(p,-2,3,35);pspark(p,30,-27,9);},art(c){blob(c,ph(P(),-2,3,35),rg(c,-14,-12,3,-2,3,40,['#ffe0ec','#ffb3cf','#ff6f9f']),INK,2.8);
    fill(c,ph(P(),-2,0,24),'rgba(255,255,255,.22)');arcl(c,-17,-8,13,1.08*Math.PI,1.5*Math.PI,'rgba(255,255,255,.9)',4.2);
    fill(c,pc(P(),-27,4,2.4),'rgba(255,255,255,.85)');for(const[x,y]of[[8,14],[16,0],[-6,22]])fill(c,pc(P(),x,y,2),'rgba(255,255,255,.55)');
    sparkle(c,30,-27,9,'#fff3b0');}},
  tim_doi:{sil:p=>{ph(p,-12,-8,24,-.3);ph(p,12,9,25,.25);},art(c){
    blob(c,ph(P(),-12,-8,24,-.3),rg(c,-20,-16,2,-12,-8,30,['#ffd6e5','#ff8fb8']),INK,2.6);shine(c,-20,-16,5,3,-1,.75);
    blob(c,ph(P(),12,9,25,.25),rg(c,5,1,2,12,9,30,['#ff9a8f','#e2574c','#c0392b']),INK,2.6);shine(c,5,0,5.5,3.2,-.5,.75);
    fill(c,pc(P(),26,10,1.8),'rgba(255,255,255,.6)');}},
  ban_tim:{sil:p=>{pr(p,-22,2,38,34,13);pseg(p,-12,10,0,-20,11);pseg(p,10,8,-4,-16,12);ph(p,20,-27,12,.25);},art(c){const sk=lg(c,0,-24,0,36,['#ffe68a','#ffd14d','#f3b233']);
    blob(c,pseg(P(),-12,10,0,-20,11),sk,INK,2.4);
    blob(c,pr(P(),-22,2,38,34,13),sk,INK,2.6);for(const y of[13,21,29])line(c,[[-17,y],[-6,y]],INK,1.8);
    blob(c,pseg(P(),10,8,-4,-16,12),sk,INK,2.4);fill(c,pe(P(),-3,-14,3,2.4,.5),'rgba(255,255,255,.55)');
    shine(c,-15,8,2,5,0,.4);
    blob(c,ph(P(),20,-27,12,.25),lg(c,10,-38,30,-16,['#ff8a80','#e2574c']),INK,2.2);shine(c,16,-31,3,1.8,-.4,.8);
    line(c,[[31,-12],[36,-9]],'#ff6f9f',2.4);line(c,[[28,-6],[32,-1]],'#ff6f9f',2.4);}},
  lap_lanh:{sil:p=>{pspark(p,-6,5,36,.22);pspark(p,26,-26,13);pc(p,28,26,5);},art(c){
    blob(c,pspark(P(),-6,5,36,.22),rg(c,-6,5,2,-6,5,36,['#fffbe0','#ffe27a','#ffcf3d','#f2a93b']),INK,2.4);
    shine(c,-9,-6,2.2,8,0,.65);
    sparkle(c,26,-26,13,'#ffb3cf',2.2);blob(c,pc(P(),28,26,5),'#9cd8c0',INK,2);}},
  ngoi_sao:{sil:p=>pstar(p,0,3,38,19),art(c){const s=pstar(P(),0,3,38,19);c.lineJoin='round';
    c.strokeStyle=INK;c.lineWidth=11;c.stroke(s);const g=rg(c,-6,-6,2,0,3,40,['#fff3b0','#ffd84a','#f2b23a']);c.strokeStyle=g;c.lineWidth=5.6;c.stroke(s);fill(c,s,g);
    shine(c,-3,-20,2.4,6,.1,.65);
    fill(c,pe(P(),-7.5,4,3,4),EYE);fill(c,pe(P(),7.5,4,3,4),EYE);fill(c,pc(P(),-6.6,2.4,1.1),WHITE);fill(c,pc(P(),8.4,2.4,1.1),WHITE);
    arcl(c,0,9,4,.15*Math.PI,.85*Math.PI,EYE,2.6);blush(c,-14,11,4.4,2.8,.55);blush(c,14,11,4.4,2.8,.55);}},
  cau_vong:{sil:p=>{p.moveTo(-40,20);p.arc(0,20,40,Math.PI,TAU);p.lineTo(13,20);p.arc(0,20,13,0,Math.PI,true);p.closePath();pcloud(p,-26,22,15);pcloud(p,26,22,15);},art(c){
    const a=P();a.moveTo(-40,20);a.arc(0,20,40,Math.PI,TAU);a.lineTo(13,20);a.arc(0,20,13,0,Math.PI,true);a.closePath();blob(c,a,'#fff',INK,2.6);
    const cols=['#ff8a80','#ffb35c','#ffd95a','#9cd8c0','#5bb6d9'];c.lineCap='butt';
    cols.forEach((col,i)=>{c.beginPath();c.arc(0,20,40-2.7-i*5.4,Math.PI,TAU);c.strokeStyle=col;c.lineWidth=5.6;c.stroke();});
    arcl(c,0,20,36,1.15*Math.PI,1.35*Math.PI,'rgba(255,255,255,.55)',2.4);
    for(const x of[-26,26]){blob(c,pcloud(P(),x,22,15),lg(c,0,10,0,30,['#ffffff','#e6f2fa']),INK,2.4);}}},
  no_hong:{sil:p=>bowLoops(p),art(c){
    const tails=P();pp(tails,[[-4,4],[-20,34],[-12,30],[-7,38],[4,6]]);pp(tails,[[4,4],[20,34],[12,30],[7,38],[-4,6]]);
    blob(c,tails,lg(c,0,4,0,38,['#ff8fb8','#e8689a']),INK,2.4);
    const loops=P();loopPath(loops,1);loopPath(loops,-1);blob(c,loops,rg(c,0,-4,2,0,-4,40,['#ffd1e3','#ff9ec4','#ff6f9f']),INK,2.6);
    for(const s of[1,-1]){curve(c,s*10,-4,s*22,-14,s*30,-8,'rgba(200,60,110,.55)',2.2);shine(c,s*24,-14,4.5,2.2,s*-.3,.6);}
    blob(c,pr(P(),-7,-10,14,16,5.5),lg(c,0,-10,0,6,['#ffb3cf','#ff6f9f']),INK,2.4);shine(c,-2,-6,2.6,1.4,0,.7);}},

  /* --- an: fair food */
  keo_bong:{sil:p=>{cottonPath(p);pr(p,-3.5,6,7,32,3.5);},art(c){
    blob(c,pr(P(),-3.5,6,7,32,3.5),lg(c,-3,0,3,0,['#fff6e6','#ead2ad']),INK,2.2);
    const q=P();cottonPath(q);blob(c,q,rg(c,-8,-20,3,0,-10,38,['#ffe3ee','#ffb3cf','#f78db9']),INK,2.6);
    clipTo(c,q,()=>{fill(c,pc(P(),18,0,13),'rgba(205,175,240,.65)');fill(c,pc(P(),-20,-6,8),'rgba(205,175,240,.45)');});
    for(const[x,y,r,a0,a1]of[[-6,-20,8,3.6,5.4],[10,-12,7,3.4,5.2],[-14,-4,6,3.5,5.3]])arcl(c,x,y,r,a0,a1,'rgba(255,255,255,.85)',2.4);
    sparkle(c,24,-28,6.5,'#fff3b0',1.4);}},
  que_kem:{rot:-12,sil:p=>{pr(p,-17,-38,34,56,17);pr(p,-5,12,10,26,5);},art(c){
    blob(c,pr(P(),-5,12,10,26,5),lg(c,-5,0,5,0,['#f3dcb6','#dcb987']),INK,2.2);
    const b=pr(P(),-17,-38,34,56,17);blob(c,b,lg(c,0,-38,0,18,['#fff7e6','#ffe8c2']),INK,2.6);
    clipTo(c,b,()=>{const d=P();d.moveTo(-20,-40);d.lineTo(20,-40);d.lineTo(20,-6);d.quadraticCurveTo(15,-8,12,-4);d.arc(8.5,-4,3.5,0,Math.PI);d.quadraticCurveTo(3,-10,-2,-6);
      d.arc(-6,-4,4,0,Math.PI);d.quadraticCurveTo(-12,-10,-20,-6);d.closePath();
      fill(c,d,lg(c,0,-38,0,0,['#ffb3cf','#ff6f9f']));c.strokeStyle='rgba(180,50,100,.35)';c.lineWidth=1.4;c.stroke(d);
      const cols=['#5bb6d9','#ffcf3d','#9cd8c0','#fff'];[[-8,-28,.6],[4,-30,-.5],[-2,-20,1.2],[9,-18,.2],[-11,-14,-.8],[1,-12,.9]].forEach(([x,y,a],i)=>{c.save();c.translate(x,y);c.rotate(a);fill(c,pr(P(),-2.6,-1,5.2,2,1),cols[i%4]);c.restore();});
      fill(c,pr(P(),-13,-33,5,22,2.5),'rgba(255,255,255,.45)');});}},
  tra_sua:{sil:p=>{pp(p,[[-21,-9],[21,-9],[16,38],[-16,38]]);lidPath(p);pseg(p,3,-14,16,-40,7);},art(c){
    c.save();line(c,[[3,-14],[16,-40]],INK,9.6);line(c,[[3,-14],[16,-40]],'#ff6f9f',5);
    c.setLineDash([2.6,3.4]);line(c,[[3,-14],[16,-40]],'#ffd1e3',5);c.restore();
    const cup=pp(P(),[[-21,-9],[21,-9],[16,38],[-16,38]]);blob(c,cup,lg(c,0,-9,0,38,['#f6e0c2','#e6b98a','#d39d6a']),INK,2.6);
    clipTo(c,cup,()=>{for(const[x,y]of[[-11,33],[-3,34],[5,33],[12,34],[-7,27],[2,27],[9,28],[-13,25]]){fill(c,pc(P(),x,y,3.5),'#4a3328');fill(c,pc(P(),x-1.1,y-1.2,1),'rgba(255,255,255,.6)');}
      fill(c,pr(P(),-15,-5,5,26,2.5),'rgba(255,255,255,.35)');});
    blob(c,ph(P(),1,9,7.5),'#ff8fb8',INK,1.6);
    const lid=P();lidPath(lid);blob(c,lid,'rgba(255,251,245,1)',INK,2.4);
    c.save();line(c,[[3,-14],[9,-26]],INK,9.6);line(c,[[3,-14],[9,-26]],'#ff6f9f',5);c.setLineDash([2.6,3.4]);line(c,[[3,-14],[9,-26]],'#ffd1e3',5);c.restore();
    shine(c,-11,-17,6,2.4,-.4,.9);}},
  xien_que:{rot:-35,sil:p=>{pr(p,-2.6,-42,5.2,82,2.6);pc(p,0,-25,12.5);pc(p,0,-1,12.5);pc(p,0,23,12.5);},art(c){
    blob(c,pr(P(),-2.6,-42,5.2,82,2.6),lg(c,-3,0,3,0,['#f6e4c4','#d9b88a']),INK,2);
    [['#ffd88a','#e9a24a','#c77a32'],['#e7b98a','#b9784a','#8a5232'],['#ffd88a','#e9a24a','#c77a32']].forEach((cols,i)=>{const y=-25+i*24;
      blob(c,pc(P(),0,y,12.5),rg(c,-4,y-5,1,0,y,13,cols),INK,2.4);
      c.save();c.beginPath();c.moveTo(-9,y-3);for(let j=0;j<5;j++)c.lineTo(-7+j*4,y+(j%2?-6:2));c.strokeStyle='#e2574c';c.lineWidth=2.6;c.lineCap='round';c.lineJoin='round';c.stroke();c.restore();
      shine(c,-5,y-6,3.2,1.8,-.6,.6);});}},
  bap_rang:{sil:p=>{pp(p,[[-23,-6],[23,-6],[17,36],[-17,36]]);popPath(p);},art(c){
    const q=P();popPath(q);blob(c,q,rg(c,-4,-28,2,0,-20,30,['#fffdf2','#fff1c8','#ffe39a']),INK,2.4);
    for(const[x,y]of[[-12,-20],[6,-26],[14,-12],[-3,-10],[-18,-8]])fill(c,pe(P(),x,y,3,2.2,.5),'rgba(255,200,60,.65)');
    const b=pp(P(),[[-23,-6],[23,-6],[17,36],[-17,36]]);blob(c,b,'#fff6ea',INK,2.6);
    clipTo(c,b,()=>{for(let i=-3;i<=3;i+=2){const s=pp(P(),[[i*7.6-3.8,-8],[i*7.6+3.8,-8],[i*5.6+2.8,38],[i*5.6-2.8,38]]);fill(c,s,'#e2574c');}
      fill(c,pr(P(),-25,-7,50,6,0),'#c0392b');});
    blob(c,pc(P(),0,17,7.5),'#fff6ea',INK,1.8);blob(c,pstar(P(),0,17.6,5,2.3),'#ffcf3d',null,0);}},
  ho_lo:{rot:14,sil:p=>{pr(p,-2.6,-42,5.2,82,2.6);for(const y of[-27,-6,15])pc(p,0,y,12);},art(c){
    blob(c,pr(P(),-2.6,-42,5.2,82,2.6),lg(c,-3,0,3,0,['#f6e4c4','#d9b88a']),INK,2);
    for(const y of[15,-6,-27]){blob(c,pc(P(),0,y,12),rg(c,-4,y-5,1,0,y,13,['#ff9a8f','#e2574c','#a8302b']),INK,2.4);
      shine(c,-5,y-5,4,2.2,-.6,.85);fill(c,pc(P(),5,y+5,1.6),'rgba(255,255,255,.6)');arcl(c,0,y,8.5,.2,1.1,'rgba(255,255,255,.35)',1.6);}}},
  dua_hau:{rot:-10,sil:p=>{p.moveTo(40,-16);p.arc(0,-16,40,0,Math.PI);p.closePath();},art(c){
    const w=P();w.moveTo(40,-16);w.arc(0,-16,40,0,Math.PI);w.closePath();blob(c,w,lg(c,0,-16,0,24,['#7fcf7a','#4f9e55']),INK,2.6);
    const r=P();r.moveTo(35,-16);r.arc(0,-16,35,0,Math.PI);r.closePath();fill(c,r,'#e9f7d6');
    const f=P();f.moveTo(31,-16);f.arc(0,-16,31,0,Math.PI);f.closePath();fill(c,f,rg(c,0,-16,4,0,-16,32,['#ff9a8f','#ff6b6b','#e8564b']));
    for(const[x,y,a]of[[-18,-8,-.5],[-6,0,-.15],[8,-1,.2],[19,-9,.5],[0,-10,0],[-11,-4,-.3],[12,-10,.35]]){c.save();c.translate(x,y);c.rotate(a);fill(c,pe(P(),0,0,1.8,3,0),'#4a3328');c.restore();}
    line(c,[[-34,-16],[34,-16]],'rgba(255,255,255,.35)',1.6);}},
  banh_bao:{sil:p=>baoPath(p),art(c){const b=P();baoPath(b);blob(c,b,rg(c,-8,-14,3,0,0,42,['#ffffff','#fff8ec','#efdcc2']),INK,2.6);
    for(const a of[-.9,-.45,0,.45,.9]){curve(c,0,-27,Math.sin(a)*8,-22,Math.sin(a)*16,-15+Math.abs(a)*4,'rgba(170,130,100,.6)',1.8);}
    fill(c,pc(P(),0,-27,3.2),'#e2574c');
    fill(c,pe(P(),-11,4,2.8,3.6),EYE);fill(c,pe(P(),11,4,2.8,3.6),EYE);fill(c,pc(P(),-10.2,2.6,1),WHITE);fill(c,pc(P(),11.8,2.6,1),WHITE);
    arcl(c,0,7,4.2,.15*Math.PI,.85*Math.PI,EYE,2.6);blush(c,-19,11,5,3,.5);blush(c,19,11,5,3,.5);shine(c,-16,-10,5,2.4,-.6,.8);}},

  /* --- trung_thu: the mid-autumn festival */
  ong_sao:{sil:p=>{pstar(p,0,8,31,15);pseg(p,-30,-34,30,-40,5);pseg(p,0,-24,0,-36,3);pseg(p,0,24,0,38,3);pc(p,0,39,3.6);},art(c){
    line(c,[[0,-24],[0,-37]],INK,2);line(c,[[0,24],[0,36]],'#e2574c',2.4);blob(c,pc(P(),0,39,3.4),'#ffcf3d',INK,1.4);
    blob(c,pseg(P(),-30,-34,30,-40,5),lg(c,0,-40,0,-34,['#d6eaa0','#a8c86a']),INK,1.8);
    const s=pstar(P(),0,8,31,15);c.lineJoin='round';c.strokeStyle=INK;c.lineWidth=8.6;c.stroke(s);
    const g=rg(c,0,6,2,0,8,32,['#fff1a8','#ffb35c','#e2574c','#c0392b']);c.strokeStyle=g;c.lineWidth=3.4;c.stroke(s);fill(c,s,g);
    clipTo(c,s,()=>{for(let i=0;i<5;i++){const a=-Math.PI/2+i*TAU/5;line(c,[[0,8],[Math.cos(a)*34,8+Math.sin(a)*34]],'rgba(150,40,30,.35)',1.4);}});
    fill(c,pstar(P(),0,9,12,6),'rgba(255,240,170,.75)');shine(c,-9,-2,2.4,5,.6,.5);}},
  ca_chep:{sil:p=>{carpPath(p);pc(p,-36,-20,3.4);pc(p,-31,-29,2.6);pseg(p,-2,-17,-2,-34,3);},art(c){
    line(c,[[-2,-17],[-2,-33]],INK,2);blob(c,pc(P(),-2,-34,2.6),'#ffcf3d',INK,1.4);
    const f=P();carpPath(f);blob(c,f,lg(c,0,-20,0,22,['#ffc06a','#f27c45','#e2574c']),INK,2.6);
    clipTo(c,f,()=>{for(let r=0;r<2;r++)for(let i=0;i<4;i++)arcl(c,-6+i*8+r*4,-6+r*9,5,.2*Math.PI,.8*Math.PI,'rgba(255,214,90,.9)',1.8);
      fill(c,pp(P(),[[18,0],[42,-20],[42,20]]),'rgba(255,230,120,.35)');for(const y of[-10,0,10])line(c,[[22,y*.3],[40,y*1.4]],'rgba(255,240,170,.8)',1.4);
      fill(c,pe(P(),-4,15,14,4,0),'rgba(255,240,200,.35)');});
    fill(c,pc(P(),-22,-4,6),WHITE);arcl(c,-22,-4,6,0,TAU,INK,1.6);fill(c,pc(P(),-21,-4,3.4),EYE);fill(c,pc(P(),-20,-5.4,1.1),WHITE);
    arcl(c,-31,6,3,-.4,1.4,INK,1.8);blush(c,-17,6,3.5,2.2,.6);
    for(const[x,y,r]of[[-36,-20,3.4],[-31,-29,2.6]]){blob(c,pc(P(),x,y,r),'rgba(200,236,248,1)',INK,1.2);}}},
  banh_tt:{sil:p=>pscallop(p,0,0,33,12,7.6),art(c){const m=pscallop(P(),0,0,33,12,7.6);blob(c,m,rg(c,-8,-10,3,0,0,42,['#f9cf86','#e7a456','#c9813c']),INK,2.6);
    blob(c,pc(P(),0,0,24),rg(c,-6,-8,2,0,0,26,['#f6c579','#e19a4c']),'#a86a35',1.4);
    for(let i=0;i<12;i++){const a=i*TAU/12+TAU/24;fill(c,pc(P(),Math.cos(a)*29,Math.sin(a)*29,1.6),'rgba(140,80,40,.5)');}
    for(let i=0;i<4;i++){const a=i*Math.PI/2;fill(c,pe(P(),Math.cos(a)*10,Math.sin(a)*10,8.4,4.6,a),'rgba(150,85,40,.42)');}
    fill(c,pc(P(),0,0,4),'rgba(150,85,40,.5)');arcl(c,0,0,18,0,TAU,'rgba(150,85,40,.4)',1.4);
    shine(c,-14,-17,6,2.6,-.7,.55);}},
  trang_ram:{sil:p=>{pc(p,2,-4,34);pcloud(p,-20,25,17);pstar(p,-30,-28,7,3.2);},art(c){
    blob(c,pc(P(),2,-4,34),rg(c,-8,-14,3,2,-4,36,['#fffbe0','#ffe27a','#f6bf3e']),INK,2.6);
    for(const[x,y,r]of[[-12,-16,5],[-2,8,3.6],[-18,2,3]])fill(c,pc(P(),x,y,r),'rgba(230,160,40,.35)');
    const tr='rgba(196,128,40,.62)';fill(c,pr(P(),13,0,3.4,16,1.5),tr);for(const[x,y,r]of[[8,-4,7.5],[19,-6,8],[14,-13,7.5],[23,1,5.5],[6,3,5]])fill(c,pc(P(),x,y,r),tr);
    fill(c,pc(P(),6,12,2.4),tr);fill(c,pr(P(),4.6,13,3,5,1.2),tr);
    blob(c,pcloud(P(),-20,25,17),lg(c,0,14,0,34,['#ffffff','#eee6fb']),INK,2.4);
    blob(c,pstar(P(),-30,-28,7,3.2),'#fff3b0',INK,1.4);}},
  tho_ngoc:{sil:p=>rabbitPath(p),art(c){const fur=lg(c,0,-38,0,38,['#ffffff','#fbf6f4','#ece2ea']);
    for(const[x,r]of[[-9,-.22],[10,.26]]){blob(c,pe(P(),x,-23,7,13.5,r),fur,INK,2.4);fill(c,pe(P(),x,-21.5,3.2,9,r),'#ffb3cf');}
    blob(c,pe(P(),0,22,21,15.5),fur,INK,2.6);blob(c,pc(P(),0,-1,20),fur,INK,2.6);
    blob(c,pscallop(P(),0,23,8,10,2.2),rg(c,-2,20,1,0,23,11,['#f6c579','#d98f45']),INK,1.6);
    blob(c,pe(P(),-9,21,5,4.4),fur,INK,1.6);blob(c,pe(P(),9,21,5,4.4),fur,INK,1.6);
    fill(c,pe(P(),-7.5,-2,2.8,3.6),EYE);fill(c,pe(P(),7.5,-2,2.8,3.6),EYE);fill(c,pc(P(),-6.6,-3.4,1),WHITE);fill(c,pc(P(),8.4,-3.4,1),WHITE);
    fill(c,pe(P(),0,3.6,2.2,1.6),'#ff8fb8');arcl(c,-2,5.4,2,.1,Math.PI-.1,EYE,1.6);arcl(c,2,5.4,2,.1,Math.PI-.1,EYE,1.6);
    blush(c,-12,5,3.6,2.4,.55);blush(c,12,5,3.6,2.4,.55);}},
  keo_quan:{sil:p=>{pr(p,-32,-31,64,62,5);pc(p,0,-35,4.6);for(const x of[-16,0,16])pseg(p,x,30,x,x?37:40,4);},art(c){
    for(const x of[-16,0,16]){line(c,[[x,30],[x,x?36:39]],'#e2574c',2.6);blob(c,pc(P(),x,x?37:40,2.6),'#ffcf3d',INK,1.2);}
    arcl(c,0,-35,3.6,0,TAU,INK,2);
    const body=pr(P(),-29,-21,58,42,2);blob(c,body,lg(c,-29,0,29,0,['#f6a03a','#ffe08a','#fff1b0','#ffe08a','#f6a03a']),INK,2.4);
    clipTo(c,body,()=>{const sh='rgba(120,60,30,.72)';
      fill(c,pe(P(),-3,3,10,5),sh);fill(c,pe(P(),9,-4,5,3.2,-.6),sh);line(c,[[5,0],[8,-5]],sh,4);
      for(const[x0,x1]of[[-10,-14],[-6,-4],[0,3],[3,8]])line(c,[[x0,6],[x1,14]],sh,2.4);curve(c,-12,0,-18,-2,-19,6,sh,2.4);
      fill(c,pc(P(),-3,-8,3.2),sh);line(c,[[-3,-5],[-2,1]],sh,3.4);line(c,[[-2,-3],[5,-6]],sh,1.8);
      fill(c,pc(P(),-22,-9,2),sh);fill(c,pc(P(),20,9,1.6),sh);});
    for(const x of[-10,10])line(c,[[x,-21],[x,21]],'#c0392b',2.6);
    blob(c,pp(P(),[[-22,-31],[22,-31],[32,-20],[-32,-20]]),lg(c,0,-31,0,-20,['#e8564b','#c0392b']),INK,2.4);
    blob(c,pp(P(),[[-32,20],[32,20],[22,31],[-22,31]]),lg(c,0,20,0,31,['#e8564b','#c0392b']),INK,2.4);
    line(c,[[-26,-23],[26,-23]],'#ffcf3d',2);line(c,[[-26,23],[26,23]],'#ffcf3d',2);}},
  dau_lan:{sil:p=>{pscallop(p,0,3,30,14,8.5);pp(p,[[-6,-30],[0,-41],[6,-30]]);},art(c){
    blob(c,pp(P(),[[-6,-28],[0,-40],[6,-28]]),lg(c,0,-40,0,-28,['#fff3b0','#ffcf3d']),INK,2);
    const m=pscallop(P(),0,3,30,14,8.5);blob(c,m,rg(c,0,0,10,0,3,40,['#fff6d6','#ffe08a','#f2c84b']),INK,2.6);
    for(let i=0;i<14;i++){const a=i*TAU/14;fill(c,pc(P(),Math.cos(a)*31,3+Math.sin(a)*31,3.2),'rgba(255,255,255,.55)');}
    blob(c,pc(P(),0,3,25),rg(c,-6,-6,3,0,3,27,['#ff8f80','#e2574c','#b83a30']),INK,2);
    fill(c,pc(P(),0,-15,3.8),'#e8eef5');arcl(c,0,-15,3.8,0,TAU,INK,1.4);shine(c,-1,-16,1.2,.8,0,.9);
    for(const x of[-10,10]){fill(c,pc(P(),x,-4,7.4),WHITE);arcl(c,x,-4,7.4,0,TAU,INK,1.6);fill(c,pc(P(),x+(x<0?1:-1),-3,3.8),EYE);fill(c,pc(P(),x+(x<0?2:0),-4.6,1.3),WHITE);
      arcl(c,x,-4,8.6,1.08*Math.PI,1.92*Math.PI,'#ffcf3d',3.4);}
    blob(c,pc(P(),0,6,5.5),rg(c,-1.5,4.5,.5,0,6,6,['#fff3b0','#f2b23a']),INK,1.4);
    const mo=P();mo.moveTo(-15,12);mo.quadraticCurveTo(0,30,15,12);mo.quadraticCurveTo(0,17,-15,12);mo.closePath();blob(c,mo,'#8a2b25',INK,1.4);
    clipTo(c,mo,()=>{fill(c,pr(P(),-15,10,30,5.6,0),WHITE);fill(c,pe(P(),0,22,6,3.4),'#ff8a9a');});
    blush(c,-17,10,4,2.6,.6);blush(c,17,10,4,2.6,.6);}},

  /* --- chu: words */
  xinh:{word:'Xinh',draw:(c,k,o)=>letters(c,k,o.t('Xinh'),{top:'#ffc6dc',bot:'#ff6f9f',ink:'#c2416f',shade:'#a83a66',heart:'#ffcf3d'})},
  iu:{word:'iu',draw:(c,k,o)=>letters(c,k,o.t('iu'),{top:'#ff9a8f',bot:'#e2574c',ink:'#a8302b',shade:'#8f2a26',heart:'#ff6f9f'})},
  ban_than:{word:'Bạn thân',draw:(c,k,o)=>pill(c,k,o.t('Bạn thân'),{top:'#8fd0ea',bot:'#5bb6d9',ink:'#2f7fa3',deco:'hearts'})},
  hoi_cho:{word:'Hội chợ',draw:(c,k,o)=>pill(c,k,o.t('Hội chợ'),{top:'#ff8a80',bot:'#e2574c',ink:'#a8302b',deco:'star',rim:'#ffcf3d'})},
  vui_ghe:{word:'Vui ghê',draw:(c,k,o)=>pill(c,k,o.t('Vui ghê'),{top:'#bfe8d6',bot:'#86cdb0',ink:'#3f8f72',deco:'spark',tail:1})},
  cute:{word:'Cute',draw:(c,k,o)=>letters(c,k,o.t('Cute'),{top:'#e2d0fa',bot:'#b48be8',ink:'#7a52b3',shade:'#6a4799',spark:'#ffb3cf'})},
  dinh:{word:'Đỉnh!',draw:(c,k,o)=>letters(c,k,o.t('Đỉnh!'),{top:'#fff1a0',bot:'#ffbf2e',ink:'#c97a1f',shade:'#a8621a',spark:'#ff6f9f'})},
  yeu_lam:{word:'Yêu lắm',draw:(c,k,o)=>pill(c,k,o.t('Yêu lắm'),{top:'#ffb3cf',bot:'#ff6f9f',ink:'#c2416f',deco:'heart'})},
  o_la_la:{word:'Ố là la',draw:(c,k,o)=>pill(c,k,o.t('Ố là la'),{top:'#ffd2a8',bot:'#f7a35c',ink:'#b96a25',deco:'spark',tail:-1})},

  /* --- nhan: labels and frames */
  washi_hong:{rot:-16,sil:p=>tapePath(p),art(c){const t=P();tapePath(t);blob(c,t,'#ffb8d2','#e88aae',1.2);
    clipTo(c,t,()=>{for(let x=-40;x<=40;x+=8)for(let r=0;r<3;r++)fill(c,pc(P(),x+(r%2)*4,-7+r*7,1.7),'rgba(255,255,255,.85)');
      fill(c,pr(P(),-44,-11,88,4,0),'rgba(255,255,255,.3)');});}},
  washi_mint:{rot:14,sil:p=>tapePath(p),art(c){const t=P();tapePath(t);blob(c,t,'#a6dcc6','#6fb89a',1.2);
    clipTo(c,t,()=>{for(let x=-56;x<=50;x+=9)fill(c,pp(P(),[[x,12],[x+4,12],[x+16,-12],[x+12,-12]]),'rgba(255,255,255,.6)');
      for(const x of[-24,0,24])fill(c,ph(P(),x+4,0,3.2),'#ff8fb8');fill(c,pr(P(),-44,-11,88,4,0),'rgba(255,255,255,.3)');});}},
  goc_no:{sil:p=>cornerPath(p),art(c){const t=P();cornerPath(t);blob(c,t,lg(c,-38,-38,0,0,['#ffe3ee','#ffc6dc']),INK,2.4);
    clipTo(c,t,()=>{for(let i=0;i<6;i++)for(let j=0;i+j<6;j++)fill(c,pc(P(),-32+i*12,-32+j*12,1.5),'rgba(255,255,255,.9)');
      line(c,[[-44,6],[6,-44]],INK,10.6);line(c,[[-44,6],[6,-44]],'#ff6f9f',7);line(c,[[-44,6],[6,-44]],'rgba(255,255,255,.35)',1.4);});
    c.save();c.translate(-19,-19);c.rotate(-Math.PI/4);
    const tl=P();pp(tl,[[-2,2],[-9,17],[-4,15],[-1,19],[2,3]]);pp(tl,[[2,2],[9,17],[4,15],[1,19],[-2,3]]);blob(c,tl,'#ff6f9f',INK,1.8);
    const l=P();pe(l,-10,-1,11,6.5,-.3);pe(l,10,-1,11,6.5,.3);blob(c,l,lg(c,0,-8,0,6,['#ffc6dc','#ff8fb8']),INK,2);
    shine(c,-12,-4,3.4,1.6,-.3,.7);shine(c,12,-4,3.4,1.6,.3,.7);
    blob(c,pc(P(),0,-1,4.6),'#ff6f9f',INK,1.6);c.restore();}},
  ky_niem:{sil:p=>bannerPath(p),draw(c,k,o){const b=P();bannerPath(b);cut(c,k,b);
    for(const s of[1,-1]){blob(c,pp(P(),[[s*42,-3],[s*28,-3],[s*28,19],[s*42,19],[s*36,8]]),'#d9507f',INK,2.2);
      fill(c,pp(P(),[[s*32,12],[s*28,12],[s*28,19]]),'#a83a66');}
    const m=P();m.moveTo(-32,-13);m.quadraticCurveTo(0,-21,32,-13);m.lineTo(32,13);m.quadraticCurveTo(0,5,-32,13);m.closePath();
    blob(c,m,lg(c,0,-19,0,13,['#ffa3c4','#ff6f9f']),INK,2.4);
    c.save();c.setLineDash([2.4,2.4]);const d=P();d.moveTo(-29,-9);d.quadraticCurveTo(0,-17,29,-9);d.moveTo(-29,9);d.quadraticCurveTo(0,1,29,9);c.strokeStyle='rgba(255,255,255,.7)';c.lineWidth=1.2;c.stroke(d);c.restore();
    words(c,o.t('Kỷ niệm'),0,-3,52,16,'#fffaf2','#a83a66');
    blob(c,ph(P(),0,-26,6),'#ffcf3d',INK,1.6);}},
  ve_hoi_cho:{rot:-8,sil:p=>ticketPath(p),draw(c,k,o){const t=P();ticketPath(t);cut(c,k,t);blob(c,t,lg(c,0,-22,0,22,['#ffe9a3','#ffcf3d','#f2b23a']),INK,2.4);
    c.save();c.setLineDash([3,2.4]);c.strokeStyle='#e2574c';c.lineWidth=1.5;c.beginPath();c.roundRect?c.roundRect(-35,-16,70,32,3):c.rect(-35,-16,70,32);c.stroke();
    c.beginPath();c.moveTo(-19,-16);c.lineTo(-19,16);c.strokeStyle='rgba(112,81,64,.7)';c.stroke();c.restore();
    blob(c,pstar(P(),-27,0,7.6,3.4),'#e2574c',null,0);
    words(c,o.t('VÉ HỘI CHỢ'),9,-3,48,14,'#c0392b',null);
    for(const x of[-1,9,19])fill(c,ph(P(),x,9,2.6),'#ff6f9f');
    fill(c,pr(P(),-38,-19,76,4,2),'rgba(255,255,255,.35)');}},
  bong_thoai:{sil:p=>{pr(p,-40,-34,80,52,24);pp(p,[[-24,12],[-8,16],[-30,36]]);},art(c){
    const b=P();pr(b,-40,-34,80,52,24);pp(b,[[-24,12],[-8,16],[-30,36]]);blob(c,b,lg(c,0,-34,0,30,['#ffffff','#fff6f0']),INK,2.8);
    arcl(c,-14,-8,20,1.1*Math.PI,1.45*Math.PI,'rgba(255,182,207,.7)',3);fill(c,pc(P(),-33,-11,1.8),'rgba(255,182,207,.7)');}},
  polaroid:{rot:7,sil:p=>{pr(p,-30,-34,60,70,3);},art(c){
    blob(c,pr(P(),-30,-34,60,70,3),'#fffdf7',INK,2.2);
    const ph2=pr(P(),-24,-28,48,44,1.6);fill(c,ph2,lg(c,0,-28,0,16,['#a9dcef','#d7eef7','#ffe3ee']));
    clipTo(c,ph2,()=>{blob(c,pc(P(),12,-16,6.5),'#ffd95a',null,0);fill(c,pc(P(),12,-16,9.5),'rgba(255,217,90,.3)');
      fill(c,pe(P(),-14,22,26,16),'#9cd8c0');fill(c,pe(P(),16,24,22,13),'#7fc4a8');fill(c,pcloud(P(),-10,-14,9),'rgba(255,255,255,.95)');
      fill(c,ph(P(),2,2,5.4),'#ff6f9f');});
    c.strokeStyle='rgba(112,81,64,.35)';c.lineWidth=1;c.strokeRect(-24,-28,48,44);
    const w=P();w.moveTo(-18,26);w.quadraticCurveTo(-12,22,-6,26);w.quadraticCurveTo(0,30,6,26);w.quadraticCurveTo(12,22,18,26);c.strokeStyle='#ff8fb8';c.lineWidth=2;c.lineCap='round';c.stroke(w);
    c.save();c.translate(0,-35);c.rotate(-.08);fill(c,pp(P(),[[-13,-5],[13,-5],[12,-2.5],[13,0],[12,2.5],[13,5],[-13,5],[-12,2.5],[-13,0],[-12,-2.5]]),'rgba(255,207,61,.82)');c.restore();}},
  huy_hieu:{sil:p=>{pscallop(p,0,-8,27,16,5.6);ribbonTails(p);},draw(c,k,o){const s=P();pscallop(s,0,-8,27,16,5.6);ribbonTails(s);cut(c,k,s);
    const r1=P(),r2=P();pp(r1,[[-14,8],[-2,12],[-9,38],[-15,32],[-23,36]]);pp(r2,[[14,8],[2,12],[9,38],[15,32],[23,36]]);
    blob(c,r1,lg(c,0,8,0,38,['#ff8fb8','#ff6f9f']),INK,2.2);blob(c,r2,lg(c,0,8,0,38,['#8fd0ea','#5bb6d9']),INK,2.2);
    blob(c,pscallop(P(),0,-8,27,16,5.6),rg(c,-6,-16,2,0,-8,34,['#fff3b0','#ffcf3d','#f2a93b']),INK,2.4);
    blob(c,pc(P(),0,-8,21),'#fff8e6',INK,1.6);arcl(c,0,-8,17.5,0,TAU,'#e2574c',1.6);
    words(c,'2026',0,-7,26,12,'#c0392b',null);
    for(const x of[-7,0,7])blob(c,pstar(P(),x,-18.5,2.8,1.2),'#ffcf3d',null,0);
    for(const x of[-7,0,7])blob(c,pstar(P(),x,3.5,2.8,1.2),'#ffcf3d',null,0);}},
};

/* ---------------------------------------------------------------- shapes shared by sil and art */
function loopPath(p,s){p.moveTo(s*3,-3);p.bezierCurveTo(s*14,-30,s*40,-26,s*38,-4);p.bezierCurveTo(s*36,14,s*14,10,s*3,3);p.closePath();if(s<0){/* same winding for the union */}return p;}
function bowLoops(p){loopPath(p,1);loopPath(p,-1);pp(p,[[-4,4],[-20,34],[-12,30],[-7,38],[4,6]]);pp(p,[[4,4],[20,34],[12,30],[7,38],[-4,6]]);pr(p,-7,-10,14,16,5.5);return p;}
function cottonPath(p){for(const[x,y,r]of[[0,-24,15],[-17,-13,13.5],[17,-13,13.5],[-9,0,12],[9,0,12],[0,-10,15],[-24,-2,8],[24,-2,8]])pc(p,x,y,r);return p;}
function lidPath(p){p.moveTo(-23,-9);p.bezierCurveTo(-23,-30,23,-30,23,-9);p.closePath();pr(p,-24,-12,48,6,3);return p;}
function popPath(p){for(const[x,y,r]of[[-17,-10,9],[-6,-15,10],[7,-13,10],[17,-9,8.5],[-11,-24,8.5],[2,-28,9],[13,-22,8],[-1,-6,8],[-21,-2,6],[21,-2,6]])pc(p,x,y,r);return p;}
function baoPath(p){p.moveTo(-38,20);p.bezierCurveTo(-40,-8,-18,-30,0,-30);p.bezierCurveTo(18,-30,40,-8,38,20);p.quadraticCurveTo(0,31,-38,20);p.closePath();return p;}
function carpPath(p){p.moveTo(-36,2);p.bezierCurveTo(-34,-16,-12,-24,6,-18);p.lineTo(10,-26);p.lineTo(16,-13);p.bezierCurveTo(19,-9,20,-4,20,0);
  p.lineTo(40,-19);p.quadraticCurveTo(33,0,40,21);p.lineTo(20,4);p.bezierCurveTo(16,16,-2,22,-14,20);p.lineTo(-12,28);p.lineTo(-22,18);p.bezierCurveTo(-30,16,-36,10,-36,2);p.closePath();return p;}
function rabbitPath(p){pe(p,-9,-23,7,13.5,-.22);pe(p,10,-23,7,13.5,.26);pe(p,0,22,21,15.5);pc(p,0,-1,20);return p;}
function tapePath(p){const pts=[];for(let i=0;i<=8;i++)pts.push([40+(i%2?-3:0),-11+i*22/8]);for(let i=0;i<=8;i++)pts.push([-40+(i%2?3:0),11-i*22/8]);return pp(p,pts);}
function cornerPath(p){pp(p,[[-38,-38],[30,-38],[-38,30]]);for(let i=1;i<8;i++){const u=i/8;pc(p,30-68*u,-38+68*u,4.6);}return p;}
function bannerPath(p){p.moveTo(-32,-13);p.quadraticCurveTo(0,-21,32,-13);p.lineTo(32,13);p.quadraticCurveTo(0,5,-32,13);p.closePath();
  for(const s of[1,-1])pp(p,[[s*42,-3],[s*28,-3],[s*28,19],[s*42,19],[s*36,8]]);ph(p,0,-26,6);return p;}
function ticketPath(p){const W=40,H=21,n=6,r=3;p.moveTo(-W+r,-H);p.lineTo(W-r,-H);p.arcTo(W,-H,W,-H+r,r);p.lineTo(W,-n);p.arc(W,0,n,-Math.PI/2,Math.PI/2,true);
  p.lineTo(W,H-r);p.arcTo(W,H,W-r,H,r);p.lineTo(-W+r,H);p.arcTo(-W,H,-W,H-r,r);p.lineTo(-W,n);p.arc(-W,0,n,Math.PI/2,-Math.PI/2,true);p.lineTo(-W,-H+r);p.arcTo(-W,-H,-W+r,-H,r);p.closePath();return p;}
function ribbonTails(p){pp(p,[[-14,8],[-2,12],[-9,38],[-15,32],[-23,36]]);pp(p,[[14,8],[2,12],[9,38],[15,32],[23,36]]);return p;}

/* ---------------------------------------------------------------- words */
/** set the biggest font (weight 900) that keeps `s` inside maxW × maxH; returns its metrics */
function fitWord(c,s,maxW,maxH,pad=0){
  c.font=`900 100px ${FONT}`;const m=c.measureText(s),w=Math.max(1,m.width);
  const asc=m.actualBoundingBoxAscent||72,desc=m.actualBoundingBoxDescent||18,h=Math.max(1,asc+desc);
  const sz=Math.max(4,Math.min(100*maxW/(w+pad*100),100*maxH/(h+pad*100)));c.font=`900 ${sz}px ${FONT}`;
  const q=sz/100;return {sz,w:w*q,asc:asc*q,desc:desc*q};
}
/** a word centred on (x, y) in the current box: optional coloured outline */
function words(c,s,x,y,maxW,maxH,col,ink){const f=fitWord(c,s,maxW,maxH,ink?.14:0);c.textAlign='center';c.textBaseline='alphabetic';c.lineJoin='round';
  const by=y+(f.asc-f.desc)/2;if(ink){c.strokeStyle=ink;c.lineWidth=f.sz*.14;c.strokeText(s,x,by);}c.fillStyle=col;c.fillText(s,x,by);return f;}
/** a short word as fat die-cut letters (a little heart, a sparkle or a burst beside it) */
function letters(c,k,s,o){
  const side=o.heart||o.spark?12:0,f=fitWord(c,s,86-side*1.2,60,.4);
  const by=(f.asc-f.desc)/2+2,x=-side*.5,lw=f.sz*.4;
  c.textAlign='center';c.textBaseline='alphabetic';c.lineJoin='round';
  const hx=Math.min(40-9,x+f.w/2+6),hy=by-f.asc-1;
  c.save();c.shadowColor='rgba(0,0,0,.18)';c.shadowOffsetY=1.6*k;c.shadowBlur=1.6*k;c.strokeStyle=WHITE;c.lineWidth=lw;c.strokeText(s,x,by);c.fillStyle=WHITE;c.fillText(s,x,by);c.restore();
  const deco=o.heart?ph(P(),hx,Math.max(-38,hy+4),9,.3):o.spark?pspark(P(),hx,Math.max(-38,hy+4),10):null;
  if(deco)cut(c,0,deco,12);
  c.lineWidth=f.sz*.16;c.strokeStyle=o.shade;c.fillStyle=o.shade;c.strokeText(s,x,by+f.sz*.07);c.fillText(s,x,by+f.sz*.07);
  c.lineWidth=f.sz*.13;c.strokeStyle=o.ink;c.strokeText(s,x,by);c.fillStyle=lg(c,0,by-f.asc,0,by+f.desc,[o.top,o.bot]);c.fillText(s,x,by);
  c.save();c.globalAlpha=.55;c.fillStyle=WHITE;c.beginPath();c.rect(x-f.w/2-4,by-f.asc-4,f.w+8,f.asc*.32+4);c.clip();c.fillStyle='rgba(255,255,255,.5)';c.fillText(s,x,by);c.restore();
  if(o.heart)blob(c,deco,o.heart,INK,1.8);else if(o.spark)blob(c,deco,o.spark,INK,1.8);
}
/** a longer word on a pill (or a speech bubble: tail ±1 = its side) */
function pill(c,k,s,o){
  c.font=`900 100px ${FONT}`;const w100=Math.max(1,c.measureText(s).width);
  const H=40,tw=Math.min(68,w100*.29),W=Math.min(86,Math.max(48,tw+20)),x0=-W/2,y0=-H/2-2;
  const p=pr(P(),x0,y0,W,H,H/2);
  if(o.tail){const s1=o.tail,tp=[[s1*-W*.26,y0+H-8],[s1*-W*.02,y0+H-8],[s1*-W*.34,y0+H+11]];pp(p,s1>0?tp:tp.reverse());}
  const dx=W/2-4,dy=y0+2,dec=o.deco==='heart'?ph(P(),dx,dy,8.5,.3):o.deco==='star'?pstar(P(),dx,dy,9,4.2):o.deco==='spark'?pspark(P(),dx,dy,9.5):null;
  cut(c,k,p);
  const hearts=o.deco==='hearts'?[ph(P(),x0+3,y0+2,6.5,-.35),ph(P(),x0+12,y0-4,4.5,.2)]:[];
  for(const h of hearts)cut(c,0,h,10);if(dec)cut(c,0,dec,11);
  blob(c,p,lg(c,0,y0,0,y0+H,[o.top,o.bot]),INK,2.4);
  if(o.rim){c.save();c.setLineDash([2.6,2.6]);c.strokeStyle=o.rim;c.lineWidth=1.6;c.stroke(pr(P(),x0+3.5,y0+3.5,W-7,H-7,(H-7)/2));c.restore();}
  fill(c,pr(P(),x0+8,y0+3.4,W-16,5.4,2.7),'rgba(255,255,255,.45)');
  words(c,s,0,y0+H/2+.5,W-14,H-15,'#fffaf2',o.ink);
  for(const h of hearts)blob(c,h,'#ff8fb8',INK,1.6);
  if(dec)blob(c,dec,o.deco==='heart'?'#e2574c':o.deco==='star'?'#ffcf3d':'#fff3b0',INK,1.8);
}

/* ---------------------------------------------------------------- the catalogue */
export const DECO_CATS=[
  {id:'mat',emoji:'😊',name:'Biểu cảm'},{id:'tim',emoji:'💖',name:'Tim & lấp lánh'},{id:'an',emoji:'🍡',name:'Đồ ăn hội chợ'},
  {id:'trung_thu',emoji:'🏮',name:'Trung thu'},{id:'chu',emoji:'💬',name:'Chữ xinh'},{id:'nhan',emoji:'🎀',name:'Nhãn dán'},
];
const ROWS=[
  ['mat','cuoi_hip','Cười híp','😆'],['mat','mat_tim','Mắt tim','😍'],['mat','long_lanh','Mắt lấp lánh','🤩'],['mat','le_luoi','Lè lưỡi','😜'],
  ['mat','khoc_nhe','Khóc nhè','😭'],['mat','ngai','Ngại đỏ mặt','☺️'],['mat','gian_doi','Giận dỗi','😤'],['mat','ngu_zzz','Ngủ khò khò','😴'],
  ['mat','kinh_ram','Kính râm ngầu','😎'],['mat','like','Tuyệt vời','👍'],
  ['tim','tim_do','Tim đỏ','❤️'],['tim','tim_hong','Tim hồng','💗'],['tim','tim_doi','Tim đôi','💕'],['tim','ban_tim','Bắn tim','🫰'],
  ['tim','lap_lanh','Lấp lánh','✨'],['tim','ngoi_sao','Ngôi sao','⭐'],['tim','cau_vong','Cầu vồng','🌈'],['tim','no_hong','Nơ hồng','🎀'],
  ['an','keo_bong','Kẹo bông','🍭'],['an','que_kem','Que kem','🍦'],['an','tra_sua','Trà sữa','🧋'],['an','xien_que','Cá viên chiên','🍢'],
  ['an','bap_rang','Bắp rang bơ','🍿'],['an','ho_lo','Kẹo hồ lô','🍡'],['an','dua_hau','Dưa hấu','🍉'],['an','banh_bao','Bánh bao','🥟'],
  ['trung_thu','ong_sao','Đèn ông sao','🌟'],['trung_thu','ca_chep','Đèn cá chép','🐟'],['trung_thu','banh_tt','Bánh trung thu','🥮'],
  ['trung_thu','trang_ram','Trăng rằm','🌕'],['trung_thu','tho_ngoc','Thỏ ngọc','🐰'],['trung_thu','keo_quan','Đèn kéo quân','🏮'],['trung_thu','dau_lan','Đầu lân','🦁'],
  ['chu','xinh','Xinh','💖'],['chu','iu','iu','💕'],['chu','ban_than','Bạn thân','👭'],['chu','hoi_cho','Hội chợ','🎡'],['chu','vui_ghe','Vui ghê','😄'],
  ['chu','cute','Cute','🌸'],['chu','dinh','Đỉnh!','🔥'],['chu','yeu_lam','Yêu lắm','💘'],['chu','o_la_la','Ố là la','🎶'],
  ['nhan','washi_hong','Băng keo hồng','🩷'],['nhan','washi_mint','Băng keo xanh','🩵'],['nhan','goc_no','Góc ảnh nơ','📐'],['nhan','ky_niem','Kỷ niệm','🎗️'],
  ['nhan','ve_hoi_cho','Vé hội chợ','🎟️'],['nhan','bong_thoai','Khung thoại','💬'],['nhan','polaroid','Khung ảnh','📷'],['nhan','huy_hieu','Huy hiệu 2026','🏅'],
];
export const DECO=ROWS.map(([cat,id,name,emoji])=>({id,cat,name,emoji}));
export const DECO_BY=Object.fromEntries(DECO.map(d=>[d.id,d]));
export const knownDeco=id=>typeof id==='string'&&Object.hasOwn(DECO_BY,id);

/* ---------------------------------------------------------------- draw */
const SIL=new Map();
function silOf(id,d){let p=SIL.get(id);if(!p){p=new Path2D();d.sil(p);SIL.set(id,p);}return p;}
const tr=t=>s=>{if(typeof t!=='function')return s;try{const v=t(s);return v==null||v===''?s:String(v);}catch{return s;}};

/** Draw sticker `id` centred on (0, 0), fitting size × size (die-cut edge and shadow included). Never throws. */
export function drawDeco(c,id,size,opts){
  const d=knownDeco(id)?ART[id]:null;if(!d||!c||!(size>0)||typeof c.save!=='function')return;
  const u=size/100*G;let k=u;
  c.save();
  try{
    try{const m=c.getTransform();k=u*(Math.hypot(m.a,m.b)||1);}catch{}
    c.scale(u,u);if(d.rot)c.rotate(d.rot*Math.PI/180);
    c.lineJoin='round';c.lineCap='round';
    const o={k,t:tr(opts&&opts.t)};
    if(d.draw)d.draw(c,k,o);else{cut(c,k,silOf(id,d));d.art(c,o);}
  }catch{}finally{c.restore();}
}

const SPR=new Map(),THUMB=new Map(),CAP=300;
const bucket=px=>Math.max(32,Math.min(512,Math.round((Number(px)||0)/16)*16));
function keyOf(id,b,opts){const d=ART[id];return id+'|'+b+(d&&d.word?'|'+tr(opts&&opts.t)(d.word):'');}
/** A px × px canvas (px rounded to a multiple of 16, 32…512) with the sticker drawn at px·DECO_FILL; cached. */
export function decoSprite(id,px,opts){
  if(!knownDeco(id)||typeof document==='undefined')return null;
  const b=bucket(px),key=keyOf(id,b,opts);let cv=SPR.get(key);if(cv)return cv;
  try{cv=document.createElement('canvas');cv.width=cv.height=b;const c=cv.getContext('2d');if(!c)return null;
    c.translate(b/2,b/2);drawDeco(c,id,b*DECO_FILL,opts);}catch{return null;}
  if(SPR.size>=CAP)SPR.clear();SPR.set(key,cv);return cv;
}
/** The picker tile: a dataURL of decoSprite (cached). */
export function decoThumb(id,px=96,opts){
  if(!knownDeco(id)||typeof document==='undefined')return '';
  const key=keyOf(id,bucket(px),opts);let u=THUMB.get(key);if(u)return u;
  try{const cv=decoSprite(id,px,opts);u=cv?cv.toDataURL('image/png'):'';}catch{u='';}
  if(u){if(THUMB.size>=CAP)THUMB.clear();THUMB.set(key,u);}return u;
}
