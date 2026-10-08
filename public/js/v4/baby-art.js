/** 👶 Bé nhà mình, drawn (game/cradle.py stages): the baby in the character's arms (paintCarried, any pen of
 * ./look.js: CANVAS on the town, fair and stroll canvases, SVG in the home room and the mirror) and the baby at home
 * (babyRoom: in a bamboo cradle when sơ sinh, crawling on a mat when biết bò, toddling when chập chững; asleep after
 * "Ru bé ngủ"). Same flat style as the character: ellipses, round rects, a few strokes. Character units: the grown-up
 * is about 150 tall, origin at the feet, up is negative. No state, no DOM: a pure painter. */
export const STAGES=['so_sinh','biet_bo','chap_chung'];
/** Outfit id (game/household.py OUTFITS) → the colour of the baby's clothes / swaddle. */
export const OUTFIT={basic:'#efc78d',yem:'#83b9db',flower:'#e5a0b1'};
const SKIN='#f4cdaa',CHEEK='#f1a7a0',HAIR='#5a3d2e',EYE='#4a3528';
const stageOf=g=>STAGES.includes(g)?g:'so_sinh';
const shade=hex=>{const n=parseInt(String(hex).slice(1),16);if(!(n>=0))return '#b58f5a';const f=v=>Math.max(0,Math.round(v*.8)).toString(16).padStart(2,'0');return `#${f(n>>16&255)}${f(n>>8&255)}${f(n&255)}`;};
const colorOf=B=>OUTFIT[B?.o]||OUTFIT.basic;

function face(c,K,x,y,r,asleep){
  K.E(c,x,y,r,r*.95,SKIN);
  K.path(c,`M${x-r*.8} ${y-r*.35}Q${x-r*.2} ${y-r*1.25} ${x+r*.75} ${y-r*.45}Q${x+r*.1} ${y-r*.75} ${x-r*.8} ${y-r*.35}Z`,HAIR);
  if(asleep){K.stroke(c,`M${x-r*.5} ${y+r*.05}q${r*.18} ${r*.18} ${r*.36} 0`,EYE,1.1);K.stroke(c,`M${x+r*.14} ${y+r*.05}q${r*.18} ${r*.18} ${r*.36} 0`,EYE,1.1);}
  else{K.E(c,x-r*.33,y+r*.05,r*.11,r*.15,EYE);K.E(c,x+r*.33,y+r*.05,r*.11,r*.15,EYE);}
  K.E(c,x-r*.55,y+r*.35,r*.2,r*.13,CHEEK);K.E(c,x+r*.55,y+r*.35,r*.2,r*.13,CHEEK);
  K.stroke(c,`M${x-r*.16} ${y+r*.45}q${r*.16} ${r*.16} ${r*.32} 0`,'#b26a5c',1);
}
function outfitMark(c,K,B,x,y,s=1){
  if(B?.o==='yem'){K.L(c,x-5*s,y-6*s,x-5*s,y+3*s,'#ffffff',1.6*s);K.L(c,x+5*s,y-6*s,x+5*s,y+3*s,'#ffffff',1.6*s);}
  else if(B?.o==='flower')K.bloom(c,x,y,3.2*s,'#fff2f6');
}

/** The baby in the arms of a character drawn with pen K (after its top, before its head). `F`: the figure (./look.js
 * figureOf: topC / classic for the sleeves, skin.hand for the hands); `B`: {g: stage, o: outfit}. */
export function paintCarried(c,B,K,F){
  const g=stageOf(B?.g),col=colorOf(B),sleeve=F?.topC||F?.classic||'#c3ab83',hand=F?.skin?.hand||'#e9b48f';
  if(g==='so_sinh'){
    K.L(c,-20,-46,-14,-32,sleeve,10);K.L(c,20,-46,16,-36,sleeve,10);
    K.E(c,4,-33,18,10,col);K.stroke(c,'M-4 -41Q2 -33 -4 -24',shade(col),2);
    face(c,K,-11,-38,8,true);
    K.E(c,-13,-30,6.5,6,hand);K.E(c,17,-35,6.5,6,hand);
    return;
  }
  if(g==='biet_bo'){
    K.L(c,-20,-46,-2,-30,sleeve,10);K.L(c,20,-46,18,-34,sleeve,10);
    K.R(c,2,-44,19,17,col,8);outfitMark(c,K,B,11.5,-36,.9);
    K.E(c,6,-26,4,3.5,SKIN);K.E(c,17,-26,4,3.5,SKIN);
    face(c,K,11.5,-52,9,false);
    K.E(c,0,-30,6.5,6,hand);K.E(c,20,-36,6.5,6,hand);
    return;
  }
  K.L(c,-20,-46,0,-28,sleeve,10);K.L(c,20,-46,21,-32,sleeve,10);
  K.R(c,3,-46,21,20,col,9);outfitMark(c,K,B,13.5,-37,1);
  K.R(c,5,-28,6,10,SKIN,3);K.R(c,15,-28,6,10,SKIN,3);K.E(c,8,-17,4,2.6,'#e98e86');K.E(c,18,-17,4,2.6,'#e98e86');
  K.L(c,22,-42,27,-48,col,5);K.E(c,27.5,-49,2.8,2.8,SKIN);   // a little wave
  face(c,K,13.5,-56,10,false);
  K.E(c,2,-28,6.5,6,hand);K.E(c,22,-31,6.5,6,hand);
}

/* ---- the room (SVG markup, character units; the room scales it like the character) ---- */
const n1=v=>Math.round(v*10)/10;
const P={
  E:(c,x,y,rx,ry,f)=>c.push(`<ellipse cx="${n1(x)}" cy="${n1(y)}" rx="${n1(rx)}" ry="${n1(ry)}" fill="${f}"/>`),
  R:(c,x,y,w,h,f,r=6)=>c.push(`<rect x="${n1(x)}" y="${n1(y)}" width="${n1(w)}" height="${n1(h)}" rx="${n1(Math.min(r,w/2,h/2))}" fill="${f}"/>`),
  L:(c,x,y,x2,y2,col,w=2)=>c.push(`<line x1="${n1(x)}" y1="${n1(y)}" x2="${n1(x2)}" y2="${n1(y2)}" stroke="${col}" stroke-width="${w}" stroke-linecap="round"/>`),
  path:(c,d,f)=>c.push(`<path d="${d}" fill="${f}"/>`),
  stroke:(c,d,col,w)=>c.push(`<path d="${d}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round"/>`),
  bloom:(c,x,y,size=12,col='#efb5ca')=>{for(let i=0;i<5;i++){const a=i*Math.PI*2/5;P.E(c,x+Math.cos(a)*size*.6,y+Math.sin(a)*size*.6,size*.5,size*.5,col);}P.E(c,x,y,size*.33,size*.33,'#f3d590');},
};
const zzz=(c,x,y)=>c.push(`<text x="${n1(x)}" y="${n1(y)}" font-size="11" font-weight="700" fill="#7d8fb3" opacity=".85">z<tspan font-size="8" dy="-6">z</tspan></text>`);
/** The baby at home as SVG markup (origin at its feet / the cradle's foot). `asleep`: after "Ru bé ngủ" today. */
export function babyRoom(B,{asleep=false}={}){
  const g=stageOf(B?.g),col=colorOf(B),c=[];
  if(g==='so_sinh'){
    P.E(c,0,1,38,6,'#00000018');
    P.stroke(c,'M-36 -3Q0 9 36 -3','#a8743f',4);
    P.L(c,-24,-12,-27,0,'#a8743f',3.5);P.L(c,24,-12,27,0,'#a8743f',3.5);
    P.R(c,-30,-30,60,20,'#d8a866',9);
    for(const x of [-18,-6,6,18])P.L(c,x,-28,x,-12,'#c08d4e',1.6);
    P.E(c,4,-31,17,6.5,col);outfitMark(c,P,B,6,-31,.8);
    face(c,P,-15,-33,8,asleep);
    P.L(c,-30,-30,30,-30,'#a8743f',4);
    P.L(c,24,-30,26,-58,'#c08d4e',2);P.L(c,26,-58,10,-58,'#c08d4e',1.6);P.L(c,12,-58,12,-50,'#c9b8a0',1);P.E(c,12,-48,3.2,3.2,'#f3d590');
    if(asleep)zzz(c,-8,-48);
  }else if(g==='biet_bo'){
    P.E(c,0,0,36,6.5,'#f1d29c');P.E(c,0,-1,30,4.5,'#f6e2b8');
    if(asleep){P.E(c,4,-8,16,7,col);outfitMark(c,P,B,6,-9,.8);face(c,P,-14,-10,8.5,true);zzz(c,-6,-26);}
    else{
      P.E(c,-9,-4,4,3.5,SKIN);P.E(c,13,-4,4.5,3.5,SKIN);P.E(c,-4,-4,3.5,3,SKIN);P.E(c,17,-5,4,3,SKIN);
      P.E(c,4,-13,15,9,col);outfitMark(c,P,B,6,-14,.8);
      face(c,P,-14,-20,9,false);
      P.E(c,22,-6,4,4,'#e98e86');P.L(c,22,-6,30,-2,'#f3d590',2);   // a rattle
    }
  }else{
    P.E(c,0,1,20,4.5,'#00000018');
    if(asleep){P.E(c,0,-1,26,5,'#f1d29c');P.E(c,3,-8,17,7.5,col);outfitMark(c,P,B,5,-9,.8);face(c,P,-15,-10,9,true);zzz(c,-6,-27);}
    else{
      P.R(c,-7,-15,6,15,SKIN,3);P.R(c,1,-15,6,15,SKIN,3);P.E(c,-4,-1,4.5,2.6,'#e98e86');P.E(c,4,-1,4.5,2.6,'#e98e86');
      P.L(c,-8,-28,-15,-38,col,5);P.L(c,8,-28,15,-38,col,5);P.E(c,-15.5,-39,3,3,SKIN);P.E(c,15.5,-39,3,3,SKIN);
      P.R(c,-10,-33,20,20,col,9);outfitMark(c,P,B,0,-24,1);
      face(c,P,0,-42,10,false);
    }
  }
  return c.join('');
}
/** A small picture of the baby (cards): the room art in its own <svg>. */
export function babyPortrait(B,{size=84,asleep=false,label=''}={}){
  return `<svg viewBox="-44 -66 88 72" width="${size}" height="${Math.round(size*72/88)}" ${label?`role="img" aria-label="${String(label).replace(/[<>&"]/g,'')}"`:'aria-hidden="true"'} focusable="false">${babyRoom(B,{asleep})}</svg>`;
}
