/** 🐾 Thú cưng: the drawings (pure SVG strings, no DOM), in the cozy style of ./deco-art.js (warm brown outline,
 * pastel fills, blush, shiny eyes). game/pets_content.py has the breeds and their coats; each breed names a `shape`
 * (its body plan, SHAPES below) and a coat gives the colours: b base, m markings, l light parts, e eyes.
 * Poses: sit (looking at you), walk (side view, facing right, legs swing with CSS), sleep (curled up), happy.
 * Accessories (game/pets_content.py ACCS): neck, head, body are worn; bed is drawn under the pet.
 * A pet is drawn with its paws on y = 0, centred on x = 0, about 56 units tall when sitting. */

const OL='#5b4535',PINK='#f59bb0',NOSE='#4a3530',TONGUE='#f08aa0',EYE='#3b2a22';
const n=v=>Math.round(v*10)/10;
const E=(cx,cy,rx,ry,f,sw=1.5,x='')=>`<ellipse cx="${n(cx)}" cy="${n(cy)}" rx="${n(rx)}" ry="${n(ry)}" fill="${f}"${sw?` stroke="${OL}" stroke-width="${sw}"`:''}${x}/>`;
const C=(cx,cy,r,f,sw=1.5,x='')=>`<circle cx="${n(cx)}" cy="${n(cy)}" r="${n(r)}" fill="${f}"${sw?` stroke="${OL}" stroke-width="${sw}"`:''}${x}/>`;
const R=(x,y,w,h,f,rx=3,sw=1.5,ex='')=>`<rect x="${n(x)}" y="${n(y)}" width="${n(w)}" height="${n(h)}" rx="${n(rx)}" fill="${f}"${sw?` stroke="${OL}" stroke-width="${sw}"`:''}${ex}/>`;
const Pa=(d,f,sw=1.5,x='')=>`<path d="${d}" fill="${f}"${sw?` stroke="${OL}" stroke-width="${sw}" stroke-linejoin="round" stroke-linecap="round"`:''}${x}/>`;
const L=(d,c=OL,w=1.4,x='')=>`<path d="${d}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"${x}/>`;
const heart=(x,y,s,c='#ef7f8f')=>Pa(`M${n(x)} ${n(y+s*.9)}q${n(-s*1.3)} ${n(-s*.8)} ${n(-s*1.1)} ${n(-s*1.6)}q${n(s*.2)} ${n(-s*.8)} ${n(s*1.1)} ${n(-s*.3)}q${n(s*.9)} ${n(-s*.5)} ${n(s*1.1)} ${n(s*.3)}q${n(s*.2)} ${n(s*.8)} ${n(-s*1.1)} ${n(s*1.6)}z`,c,0);
const lum=h=>{const v=parseInt(String(h).slice(1),16);return isNaN(v)?1:((v>>16)*.299+((v>>8)&255)*.587+(v&255)*.114)/255;};
const blush=(x,y,s=1)=>E(x,y,2.6*s,1.6*s,PINK,0,' opacity=".75"');

/* The body plans. k: dog | cat. ear: prick, big, huge, small, flop, long, puff, fold (dog: folded over / cat: Scottish),
 * cat, catsmall, bigcat, tuft. tail: curl, plume, stub, thin, pom, long, thick, fluffy. face: '', blaze, urajiro, mask,
 * points, tabby, calico, spots, tux. fluff: '', ruff, curly. legs (×), long (body length ×), head (×), muzzle: dog,
 * flat (pug: dark short), cat, flatcat (Persian). Extras: ridge, wrinkles, smile, chubby, bald, brows. */
export const SHAPES={
  mutt:{k:'dog',ear:'prick',tail:'curl',face:'tux',head:1,muzzle:'dog'},
  poodle:{k:'dog',ear:'puff',tail:'pom',fluff:'curly',muzzle:'dog'},
  corgi:{k:'dog',ear:'big',tail:'stub',face:'blaze',legs:.55,long:1.3,muzzle:'dog',smile:1,brows:1},
  shiba:{k:'dog',ear:'prick',tail:'curl',face:'urajiro',muzzle:'dog',brows:1},
  pom:{k:'dog',ear:'small',tail:'plume',fluff:'ruff',muzzle:'dog',legs:.7,head:1.05,smile:1},
  chihuahua:{k:'dog',ear:'huge',tail:'thin',muzzle:'dog',head:1.12,body:.85,brows:1},
  husky:{k:'dog',ear:'prick',tail:'plume',face:'mask',muzzle:'dog'},
  golden:{k:'dog',ear:'flop',tail:'plume',muzzle:'dog',smile:1},
  alaska:{k:'dog',ear:'small',tail:'curl',face:'mask',fluff:'ruff',muzzle:'dog',body:1.1},
  ridgeback:{k:'dog',ear:'prick',tail:'thin',muzzle:'dog',ridge:1},
  bacha:{k:'dog',ear:'prick',tail:'curl',fluff:'ruff',muzzle:'dog',face:'tux'},
  pug:{k:'dog',ear:'fold',tail:'curl',muzzle:'flat',wrinkles:1,head:1.05},
  samoyed:{k:'dog',ear:'prick',tail:'curl',fluff:'ruff',muzzle:'dog',smile:1},
  dachshund:{k:'dog',ear:'long',tail:'thin',legs:.5,long:1.45,muzzle:'dog',brows:1},
  tabby:{k:'cat',ear:'cat',tail:'long',face:'tabby',muzzle:'cat',stripes:1},
  calico:{k:'cat',ear:'cat',tail:'long',face:'calico',muzzle:'cat'},
  cat:{k:'cat',ear:'cat',tail:'long',face:'tux',muzzle:'cat'},
  british:{k:'cat',ear:'catsmall',tail:'thick',muzzle:'cat',chubby:1,face:'tux2'},
  british_long:{k:'cat',ear:'catsmall',tail:'fluffy',fluff:'ruff',muzzle:'cat',chubby:1},
  persian:{k:'cat',ear:'catsmall',tail:'fluffy',fluff:'ruff',muzzle:'flatcat',chubby:1},
  fold:{k:'cat',ear:'fold',tail:'thick',muzzle:'cat',chubby:1,face:'tux2'},
  munchkin:{k:'cat',ear:'cat',tail:'long',legs:.5,muzzle:'cat',face:'calico2'},
  ragdoll:{k:'cat',ear:'cat',tail:'fluffy',fluff:'ruff',face:'points',muzzle:'cat'},
  bengal:{k:'cat',ear:'cat',tail:'long',face:'spots',muzzle:'cat',spots:1},
  sphynx:{k:'cat',ear:'bigcat',tail:'thin',muzzle:'cat',wrinkles:1,bald:1},
  maine:{k:'cat',ear:'tuft',tail:'fluffy',fluff:'ruff',face:'tabby',muzzle:'cat',stripes:1},
  siamese:{k:'cat',ear:'bigcat',tail:'thin',face:'points',muzzle:'cat'},
};
const SIZE={s:.9,m:1,l:1.1};

/* ---------------------------------------------------------------- the head (looking at you), centre (x, y), radius r */
function ears(S,K,x,y,r,front){
  const b=K.b,m=K.m,inner=S.k==='cat'?'#f7b9c7':K.l,pts=S.face==='points',ec=pts?m:b,dark=S.face==='calico'?[K.m,K.l]:[ec,ec];
  const tri=(sx,w,h,out,c,ic)=>{const bx=x+sx*r*.55,by=y-r*.5,tx=bx+sx*r*out,ty=y-r*h;
    return Pa(`M${n(bx-sx*w*r)} ${n(by+r*.12)}L${n(tx)} ${n(ty)}L${n(bx+sx*w*r*.9)} ${n(by-r*.18)}Z`,c)+Pa(`M${n(bx-sx*w*r*.45)} ${n(by)}L${n(tx-sx*r*.06)} ${n(ty+r*.32)}L${n(bx+sx*w*r*.5)} ${n(by-r*.14)}Z`,ic,0);};
  const pair=(w,h,out,ic=inner)=>front?'':tri(-1,w,h,out,dark[0],ic)+tri(1,w,h,out,dark[1],ic);
  switch(S.ear){
    case'prick':return pair(.42,1.42,.22);
    case'small':return pair(.32,1.22,.15);
    case'big':return pair(.5,1.68,.42);
    case'huge':return pair(.58,1.75,.62);
    case'cat':return pair(.42,1.4,.2);
    case'catsmall':return pair(.34,1.18,.18);
    case'bigcat':return pair(.55,1.6,.38);
    case'tuft':return front?L(`M${n(x-r*.82)} ${n(y-r*1.42)}l${n(-r*.08)} ${n(-r*.3)}M${n(x+r*.82)} ${n(y-r*1.42)}l${n(r*.08)} ${n(-r*.3)}`,m,1.3):pair(.44,1.45,.25);
    case'flop':case'long':{const h=S.ear==='long'?1.2:.95;if(!front)return '';
      return [-1,1].map(sx=>Pa(`M${n(x+sx*r*.62)} ${n(y-r*.62)}q${n(sx*r*.62)} ${n(r*.02)} ${n(sx*r*.5)} ${n(r*h)}q${n(-sx*r*.08)} ${n(r*.3)} ${n(-sx*r*.34)} ${n(r*.14)}q${n(-sx*r*.22)} ${n(-r*.42)} ${n(-sx*r*.3)} ${n(-r*.95)}z`,S.face==='blaze'?b:(K.m))).join('');}
    case'puff':return front?[-1,1].map(sx=>C(x+sx*r*.98,y+r*.12,r*.42,b,1.4)+C(x+sx*r*.92,y+r*.5,r*.34,b,1.4)).join(''):'';
    case'fold':if(!front)return '';
      if(S.k==='cat')return [-1,1].map(sx=>Pa(`M${n(x+sx*r*.25)} ${n(y-r*.82)}q${n(sx*r*.38)} ${n(-r*.18)} ${n(sx*r*.62)} ${n(r*.12)}q${n(-sx*r*.22)} ${n(r*.05)} ${n(-sx*r*.58)} ${n(-r*.02)}z`,ec,1.3)).join('');
      return [-1,1].map(sx=>Pa(`M${n(x+sx*r*.4)} ${n(y-r*.8)}q${n(sx*r*.5)} ${n(-r*.08)} ${n(sx*r*.62)} ${n(r*.35)}q${n(-sx*r*.3)} ${n(-r*.05)} ${n(-sx*r*.5)} ${n(-r*.12)}z`,K.m,1.3)).join('');
  }
  return '';
}
function face(S,K,x,y,r,mood,blink){
  const cat=S.k==='cat',m=K.m,l=K.l,b=K.b;let o='';
  // Markings on the head shape (clipped by being drawn inside the head's outline, small enough not to spill).
  switch(S.face){
    case'mask':o+=Pa(`M${n(x-r*1.02)} ${n(y)}q${n(-r*.05)} ${n(-r*.95)} ${n(r*1.02)} ${n(-r*.96)}q${n(r*1.07)} ${n(.01)} ${n(r*1.02)} ${n(r*.96)}q${n(-r*.45)} ${n(-r*.2)} ${n(-r*.62)} ${n(-r*.08)}l${n(-r*.4)} ${n(r*.32)}l${n(-r*.4)} ${n(-r*.32)}q${n(-r*.17)} ${n(-r*.12)} ${n(-r*.62)} ${n(r*.08)}z`,b,0);break;
    case'urajiro':o+=E(x-r*.5,y+r*.3,r*.42,r*.32,l,0)+E(x+r*.5,y+r*.3,r*.42,r*.32,l,0)+E(x-r*.38,y-r*.35,r*.12,r*.08,l,0)+E(x+r*.38,y-r*.35,r*.12,r*.08,l,0);break;
    case'blaze':o+=Pa(`M${n(x-r*.12)} ${n(y-r*.95)}q${n(r*.12)} ${n(-r*.03)} ${n(r*.24)} 0l${n(r*.12)} ${n(r*.9)}h${n(-r*.48)}z`,l,0)+E(x,y+r*.42,r*.62,r*.42,l,0);break;
    case'points':o+=E(x,y+r*.34,r*.52,r*.46,m,0,' opacity=".7"')+E(x,y+r*.4,r*.34,r*.28,m,0,' opacity=".6"');break;
    case'tabby':o+=L(`M${n(x-r*.32)} ${n(y-r*.85)}l${n(r*.12)} ${n(r*.38)}l${n(r*.2)} ${n(-r*.32)}l${n(r*.2)} ${n(r*.32)}l${n(r*.12)} ${n(-r*.38)}M${n(x)} ${n(y-r*.92)}v${n(r*.3)}`,m,1.5)
      +L(`M${n(x-r*1.02)} ${n(y+r*.05)}h${n(r*.3)}M${n(x-r*1)} ${n(y+r*.28)}h${n(r*.26)}M${n(x+r*1.02)} ${n(y+r*.05)}h${n(-r*.3)}M${n(x+r*1)} ${n(y+r*.28)}h${n(-r*.26)}`,m,1.3);break;
    case'calico':o+=Pa(`M${n(x-r*1.05)} ${n(y-r*.1)}q${n(r*.05)} ${n(-r*.8)} ${n(r*.75)} ${n(-r*.82)}q${n(-r*.05)} ${n(r*.45)} ${n(-r*.2)} ${n(r*.7)}q${n(-r*.3)} ${n(r*.25)} ${n(-r*.55)} ${n(r*.12)}z`,m,0)
      +Pa(`M${n(x+r*1.05)} ${n(y-r*.1)}q${n(-r*.05)} ${n(-r*.8)} ${n(-r*.72)} ${n(-r*.82)}q${n(.02)} ${n(r*.4)} ${n(r*.22)} ${n(r*.62)}q${n(r*.3)} ${n(r*.28)} ${n(r*.5)} ${n(r*.2)}z`,l,0);break;
    case'calico2':if(K.name==='Tam thể')o+=Pa(`M${n(x-r*1.05)} ${n(y-r*.1)}q${n(r*.05)} ${n(-r*.8)} ${n(r*.75)} ${n(-r*.82)}q${n(-r*.05)} ${n(r*.45)} ${n(-r*.2)} ${n(r*.7)}q${n(-r*.3)} ${n(r*.25)} ${n(-r*.55)} ${n(r*.12)}z`,m,0)+E(x+r*.6,y-r*.5,r*.32,r*.24,l,0);break;
    case'spots':o+=[[-.5,-.55],[.45,-.6],[0,-.75],[-.8,.05],[.82,.08]].map(([a,c])=>E(x+a*r,y+c*r,r*.11,r*.08,m,0)).join('');break;
    case'tux':if(/^#f|^#e/i.test(l)&&l!==b)o+=Pa(`M${n(x-r*.15)} ${n(y-r*.62)}q${n(r*.15)} ${n(-r*.06)} ${n(r*.3)} 0l${n(r*.2)} ${n(r*.6)}h${n(-r*.7)}z`,l,0);break;
  }
  if(S.wrinkles)o+=L(`M${n(x-r*.32)} ${n(y-r*.6)}q${n(r*.32)} ${n(-r*.14)} ${n(r*.64)} 0M${n(x-r*.22)} ${n(y-r*.44)}q${n(r*.22)} ${n(-r*.1)} ${n(r*.44)} 0`,S.k==='cat'?K.m:K.m,1.1,' opacity=".7"');
  if(S.brows&&/Đen vàng|Tam thể/.test(K.name||''))o+=E(x-r*.4,y-r*.36,r*.13,r*.09,K.m,0)+E(x+r*.4,y-r*.36,r*.13,r*.09,K.m,0);
  // Muzzle, nose, mouth.
  const my=y+r*(cat?.32:.36);
  if(S.muzzle==='dog'){o+=E(x,my,r*.48,r*.36,S.face==='mask'||S.face==='urajiro'||S.face==='blaze'?l:l,0)+Pa(`M${n(x-r*.2)} ${n(my-r*.2)}q${n(r*.2)} ${n(-r*.1)} ${n(r*.4)} 0q${n(-.02)} ${n(r*.2)} ${n(-r*.2)} ${n(r*.24)}q${n(-r*.2)} ${n(-r*.04)} ${n(-r*.2)} ${n(-r*.24)}z`,NOSE,0)+C(x-r*.07,my-r*.18,r*.05,'#fff',0,' opacity=".7"');}
  else if(S.muzzle==='flat'){o+=E(x,my+r*.02,r*.56,r*.4,m,0)+E(x,my-r*.14,r*.2,r*.13,NOSE,0);}
  else{const fl=S.muzzle==='flatcat';o+=E(x-r*.16,my+r*.06,r*.2,r*.15,l,0)+E(x+r*.16,my+r*.06,r*.2,r*.15,l,0)+Pa(`M${n(x-r*.1)} ${n(my-r*(fl?.14:.08))}h${n(r*.2)}l${n(-r*.1)} ${n(r*.12)}z`,'#e88a9c',0)
    +L(`M${n(x-r*.55)} ${n(my)}l${n(-r*.55)} ${n(-r*.08)}M${n(x-r*.55)} ${n(my+r*.12)}l${n(-r*.52)} ${n(r*.1)}M${n(x+r*.55)} ${n(my)}l${n(r*.55)} ${n(-r*.08)}M${n(x+r*.55)} ${n(my+r*.12)}l${n(r*.52)} ${n(r*.1)}`,OL,.7,' opacity=".55"');}
  const mouthY=my+(S.muzzle==='dog'?r*.08:r*.14),happy=mood==='happy';
  if(happy&&S.k==='dog')o+=Pa(`M${n(x-r*.22)} ${n(mouthY)}q${n(r*.22)} ${n(r*.5)} ${n(r*.44)} 0z`,'#a8434f',1.1)+Pa(`M${n(x-r*.11)} ${n(mouthY+r*.14)}q${n(r*.11)} ${n(r*.36)} ${n(r*.22)} 0z`,TONGUE,0);
  else if(happy)o+=Pa(`M${n(x-r*.16)} ${n(mouthY)}q${n(r*.16)} ${n(r*.32)} ${n(r*.32)} 0z`,'#c75a6a',1);
  else o+=L(`M${n(x-r*.24)} ${n(mouthY)}q${n(r*.12)} ${n(r*.14)} ${n(r*.24)} 0q${n(r*.12)} ${n(r*.14)} ${n(r*.24)} 0`,OL,1.1);
  if(S.smile&&!happy)o+=Pa(`M${n(x-r*.08)} ${n(mouthY+r*.05)}q${n(r*.08)} ${n(r*.2)} ${n(r*.16)} 0z`,TONGUE,0);
  // Eyes.
  const ex=r*(S.muzzle==='flatcat'?.4:.42),ey=y-r*(S.muzzle==='flatcat'?.0:.04),er=r*(S.head>1.08?.21:.18)*(S.k==='cat'?1.08:1);
  if(blink==='sleep')o+=L(`M${n(x-ex-er)} ${n(ey)}q${n(er)} ${n(er*.9)} ${n(er*2)} 0M${n(x+ex-er)} ${n(ey)}q${n(er)} ${n(er*.9)} ${n(er*2)} 0`,OL,1.4);
  else if(happy)o+=L(`M${n(x-ex-er)} ${n(ey+er*.3)}q${n(er)} ${n(-er*1.5)} ${n(er*2)} 0M${n(x+ex-er)} ${n(ey+er*.3)}q${n(er)} ${n(-er*1.5)} ${n(er*2)} 0`,OL,1.6);
  else{const iris=K.e&&K.e!==EYE?K.e:null,dark=lum(S.face==='mask'?K.l:K.b)<.3;
    for(const sx of [-1,1]){const cx=x+sx*ex;
      o+=iris?E(cx,ey,er,er*1.1,iris,dark?0:1.1,dark?' stroke="#fff3df" stroke-width="1"':'')+E(cx,ey+er*.1,er*.4,er*.66,EYE,0):E(cx,ey,er,er*1.12,EYE,0,dark?' stroke="#fff3df" stroke-width="1.1"':'');
      o+=C(cx+er*.35,ey-er*.4,er*.36,'#fff',0)+C(cx-er*.35,ey+er*.4,er*.16,'#fff',0,' opacity=".8"');}}
  o+=blush(x-r*.68,y+r*.32,r/12)+blush(x+r*.68,y+r*.32,r/12);
  return o;
}
function ruff(S,K,x,y,r){
  if(S.fluff!=='ruff')return '';
  const c=S.face==='points'||S.face==='mask'?K.l:K.b,pts=[];const N=9;
  for(let i=0;i<N;i++){const a=Math.PI*(-.08+i/(N-1)*1.16);pts.push([x+Math.cos(a)*r*1.06,y+r*.2+Math.sin(a)*r*.82]);}
  return pts.map(([a,b])=>C(a,b,r*.36,c,1.4)).join('')+pts.map(([a,b])=>C(a,b,r*.36-.75,c,0)).join('');
}
function head(S,K,x,y,r,o={}){
  const mood=o.mood||'',pos=S.chubby?1.2:S.k==='cat'?1.12:1.06,ry=S.chubby?.9:.95;
  let s=ruff(S,K,x,y,r)+ears(S,K,x,y,r,false);
  if(S.fluff==='curly')s+=[[-.6,-.95,.42],[0,-1.12,.5],[.6,-.95,.42]].map(([a,b,c])=>C(x+a*r,y+b*r,c*r,K.b,1.4)).join('');
  const headFill=S.face==='mask'||S.face==='blaze'&&false?K.l:(S.face==='calico'||S.face==='calico2'&&K.name==='Tam thể'?K.b:K.b);
  s+=E(x,y,r*pos,r*ry,S.face==='mask'?K.l:headFill,1.6);
  if(S.chubby)s+=E(x-r*.78,y+r*.38,r*.4,r*.28,headFill,0)+E(x+r*.78,y+r*.38,r*.4,r*.28,headFill,0);
  s+=face(S,K,x,y,r,mood,o.blink)+ears(S,K,x,y,r,true);
  if(S.fluff==='curly')s+=[[-.38,-.92,.3],[.38,-.92,.3],[0,-1.02,.32]].map(([a,b,c])=>C(x+a*r,y+b*r,c*r,K.b,1.2)).join('');
  if(o.acc?.head)s+=hat(o.acc.head,x,y,r);
  return s;
}

/* ---------------------------------------------------------------- accessories */
function hat(id,x,y,r){
  switch(id){
    case'no_hong':case'no_cham':{const c=id==='no_hong'?'#f28fb0':'#5b8fd9',bx=x+r*.55,by=y-r*.88;
      return Pa(`M${n(bx)} ${n(by)}l${n(-r*.48)} ${n(-r*.3)}v${n(r*.6)}z`,c,1.2)+Pa(`M${n(bx)} ${n(by)}l${n(r*.48)} ${n(-r*.3)}v${n(r*.6)}z`,c,1.2)+C(bx,by,r*.13,c,1.2)
        +(id==='no_cham'?C(bx-r*.28,by-r*.05,r*.05,'#fff',0)+C(bx+r*.3,by+r*.06,r*.05,'#fff',0):'');}
    case'non_la':return Pa(`M${n(x-r*1.05)} ${n(y-r*.7)}L${n(x)} ${n(y-r*1.75)}L${n(x+r*1.05)} ${n(y-r*.7)}q${n(-r*1.05)} ${n(r*.22)} ${n(-r*2.1)} 0z`,'#ecd28f',1.3)
      +L(`M${n(x-r*.55)} ${n(y-r*1.18)}q${n(r*.55)} ${n(r*.1)} ${n(r*1.1)} 0M${n(x-r*.8)} ${n(y-r*.92)}q${n(r*.8)} ${n(r*.14)} ${n(r*1.6)} 0`,'#c9a35b',.9);
    case'mu_ech':return Pa(`M${n(x-r*.95)} ${n(y-r*.55)}q${n(r*.1)} ${n(-r*.9)} ${n(r*.95)} ${n(-r*.92)}q${n(r*.85)} ${n(.02)} ${n(r*.95)} ${n(r*.92)}q${n(-r*.95)} ${n(-r*.2)} ${n(-r*1.9)} 0z`,'#7cc47f',1.3)
      +C(x-r*.42,y-r*1.38,r*.26,'#7cc47f',1.2)+C(x+r*.42,y-r*1.38,r*.26,'#7cc47f',1.2)+C(x-r*.42,y-r*1.4,r*.12,'#fff',0)+C(x+r*.42,y-r*1.4,r*.12,'#fff',0)+C(x-r*.4,y-r*1.4,r*.06,EYE,0)+C(x+r*.44,y-r*1.4,r*.06,EYE,0);
    case'vuong_mien':return Pa(`M${n(x-r*.5)} ${n(y-r*.86)}l${n(-r*.06)} ${n(-r*.5)}l${n(r*.26)} ${n(r*.22)}l${n(r*.3)} ${n(-r*.38)}l${n(r*.3)} ${n(r*.38)}l${n(r*.26)} ${n(-r*.22)}l${n(-r*.06)} ${n(r*.5)}z`,'#f2c14e',1.2)
      +C(x,y-r*1.06,r*.08,'#ef7f72',0)+C(x-r*.3,y-r*1,r*.06,'#7fb8e0',0)+C(x+r*.3,y-r*1,r*.06,'#7cc47f',0);
  }
  return '';
}
function collar(id,x,y,w){
  if(!id)return '';const c={vong_chuong:'#e05a4f',vong_da:'#8a5a3a',vong_ngoc:'#f7f1ea',vong_vang:'#e7b93e'}[id];if(!c)return '';
  let s=Pa(`M${n(x-w)} ${n(y-1.5)}q${n(w)} ${n(4.5)} ${n(w*2)} 0v3q${n(-w)} ${n(4.5)} ${n(-w*2)} 0z`,c,1.1);
  if(id==='vong_ngoc')s=Array.from({length:7},(_,i)=>{const t=i/6,px=x-w+t*2*w,py=y+Math.sin(t*Math.PI)*2.4;return C(px,py,1.6,'#fbf7f0',.8);}).join('');
  if(id==='vong_chuong')s+=C(x,y+4.4,2.4,'#f2c14e',1)+L(`M${n(x-1.2)} ${n(y+4.4)}h2.4`,OL,.7);
  if(id==='vong_da')s+=R(x-2,y+2.4,4,3.6,'#f2c14e',1,.9);
  if(id==='vong_vang')s+=Pa(`M${n(x)} ${n(y+2)}l2.4 2.6l-2.4 2.6l-2.4-2.6z`,'#f7d36b',1);
  return s;
}
/** Clothes over the torso. sit: (cx, top y, half width, height); walk: the body ellipse (cx, cy, rx, ry). */
function coat(id,mode,a,b,c,d){
  const col={ao_len:'#e58b7a',ao_mua:'#f6cf45',ao_vn:'#d8392f',ao_khung_long:'#79b86b',ao_dai:'#d94f6e',vay_cong_chua:'#c8a6ef'}[id];if(!col)return '';
  let s='';
  if(mode==='sit'){const [x,y,w,h]=[a,b,c,d];
    s=Pa(`M${n(x-w*.82)} ${n(y)}q${n(w*.82)} ${n(-3)} ${n(w*1.64)} 0l${n(w*.2)} ${n(h*.78)}q${n(-w*1.02)} ${n(h*.22)} ${n(-w*2.04)} 0z`,col,1.3);
    if(id==='ao_len')s+=L(`M${n(x-w*.86)} ${n(y+h*.35)}h${n(w*1.72)}M${n(x-w*.9)} ${n(y+h*.55)}h${n(w*1.8)}`,'#fff',1.4,' opacity=".75"');
    if(id==='ao_mua')s+=C(x,y+h*.25,1.1,'#fff',.7)+C(x,y+h*.5,1.1,'#fff',.7)+Pa(`M${n(x-w*.8)} ${n(y-1)}q${n(w*.8)} ${n(5)} ${n(w*1.6)} 0`,'#f6cf45',1.2);
    if(id==='ao_vn')s+=star(x,y+h*.38,h*.18,'#f6d23e');
    if(id==='ao_khung_long')s+=[0,1,2].map(i=>Pa(`M${n(x-w*.5+i*w*.5-2)} ${n(y+1)}l2 -4l2 4z`,'#f2d36b',.9)).join('')+Pa(`M${n(x-w*.82)} ${n(y)}q${n(w*.82)} ${n(-3)} ${n(w*1.64)} 0v-3q${n(-w*.82)} ${n(-4)} ${n(-w*1.64)} 0z`,col,1.1);
    if(id==='ao_dai')s=Pa(`M${n(x-w*.78)} ${n(y)}q${n(w*.78)} ${n(-3)} ${n(w*1.56)} 0l${n(w*.36)} ${n(h*1.05)}h${n(-w*.62)}l${n(-w*.24)} ${n(-h*.3)}l${n(-w*.24)} ${n(h*.3)}h${n(-w*.62)}z`,col,1.3)+L(`M${n(x)} ${n(y)}v${n(h*.75)}`,'#f2c14e',1)+C(x+w*.3,y+h*.3,1.3,'#f2c14e',0)+C(x-w*.35,y+h*.55,1.2,'#fbe08a',0);
    if(id==='vay_cong_chua')s+=Array.from({length:6},(_,i)=>C(x-w*1.05+i*w*.42,y+h*.82,w*.26,'#e3d4fa',1)).join('')+heart(x,y+h*.28,2.2,'#fff');
  }else{const [cx,cy,rx,ry]=[a,b,c,d];
    s=Pa(`M${n(cx-rx*.55)} ${n(cy-ry*.98)}q${n(rx*.55)} ${n(-ry*.3)} ${n(rx*1.1)} 0q${n(rx*.12)} ${n(ry*.95)} ${n(-rx*.02)} ${n(ry*1.55)}h${n(-rx*1.06)}q${n(-rx*.14)} ${n(-ry*.6)} ${n(-rx*.02)} ${n(-ry*1.55)}z`,col,1.3);
    if(id==='ao_vn')s+=star(cx,cy+ry*.1,ry*.42,'#f6d23e');
    if(id==='ao_len')s+=L(`M${n(cx-rx*.56)} ${n(cy)}h${n(rx*1.12)}`,'#fff',1.4,' opacity=".75"');
    if(id==='ao_khung_long')s+=[0,1,2,3].map(i=>Pa(`M${n(cx-rx*.5+i*rx*.33-2)} ${n(cy-ry*1.02)}l2 -4l2 4z`,'#f2d36b',.9)).join('');
    if(id==='ao_mua')s+=C(cx,cy-ry*.3,1.1,'#fff',.7)+C(cx,cy+ry*.3,1.1,'#fff',.7);
    if(id==='ao_dai')s+=Pa(`M${n(cx-rx*.5)} ${n(cy+ry*.5)}l${n(-rx*.25)} ${n(ry*.9)}h${n(rx*.35)}zM${n(cx+rx*.5)} ${n(cy+ry*.5)}l${n(rx*.25)} ${n(ry*.9)}h${n(-rx*.35)}z`,col,1.1);
    if(id==='vay_cong_chua')s+=Array.from({length:5},(_,i)=>C(cx-rx*.6+i*rx*.3,cy+ry*.62,ry*.36,'#e3d4fa',1)).join('');
  }
  return s;
}
const star=(x,y,r,c)=>Pa('M'+Array.from({length:10},(_,i)=>{const a=-Math.PI/2+i*Math.PI/5,q=i%2?r*.45:r;return `${n(x+Math.cos(a)*q)} ${n(y+Math.sin(a)*q)}`;}).join('L')+'z',c,0);
/** The bed under the pet (home, dialog card). */
export function bedSVG(id,w=44){
  switch(id){
    case'o_bong':return E(0,-3,w*.62,7.5,'#f2b8c6',1.5)+E(0,-5,w*.48,4.5,'#fbe0e7',0);
    case'nem_may':return Pa(`M${n(-w*.62)} 0q-4-7 3-10q2-6 9-4q4-5 10-2q5-4 10 0q7-2 8 5q6 2 3 11z`,'#e4f1fb',1.5)+E(0,-4,w*.4,3.5,'#fff',0,' opacity=".8"');
    case'nha_go':return Pa(`M${n(-w*.62)} 0v-28l${n(w*.62)} -16l${n(w*.62)} 16v28z`,'#d9a066',1.5)+Pa(`M${n(-w*.7)} -27l${n(w*.7)} -19l${n(w*.7)} 19`,'none',3,' stroke-linecap="round"')
      +Pa(`M${n(-w*.34)} 0v-17q${n(w*.34)} -12 ${n(w*.68)} 0v17z`,'#7a5236',1.2)+R(-w*.08,-38,w*.16,6,'#fff6e6',1,1)+E(0,-3,w*.4,4,'#f2b8c6',1);
    case'lau_dai':return R(-w*.72,-34,w*.36,34,'#e6dcf8',0,1.5)+R(w*.36,-34,w*.36,34,'#e6dcf8',0,1.5)+R(-w*.42,-28,w*.84,28,'#cdb8f0',2,1.5)
      +Pa(`M${n(-w*.76)} -34l${n(w*.22)} -14l${n(w*.22)} 14zM${n(w*.32)} -34l${n(w*.22)} -14l${n(w*.22)} 14z`,'#ef7f8f',1.3)+Pa(`M${n(-w*.26)} 0v-15q${n(w*.26)} -10 ${n(w*.52)} 0v15z`,'#8f73c9',1.2)+star(0,-22,3,'#f2c14e')+E(0,-3,w*.36,3.6,'#f2b8c6',1);
  }
  return '';
}

/* ---------------------------------------------------------------- tails */
function tail(S,K,x,y,dir,big=1,anim=true){   // dir: 1 = the tail goes to the right/up, -1 to the left
  const c=S.face==='points'?K.m:S.tail==='pom'?K.b:K.b,cls=anim?' class="pet-tail"':'',sw=1.5,k=big;
  switch(S.tail){
    case'curl':return `<g${cls}>`+Pa(`M${n(x)} ${n(y)}q${n(dir*12*k)} ${n(-2*k)} ${n(dir*10*k)} ${n(-12*k)}q${n(-dir*1*k)} ${n(-6*k)} ${n(-dir*7*k)} ${n(-3*k)}q${n(dir*4*k)} ${n(2*k)} ${n(dir*2*k)} ${n(7*k)}q${n(-dir*2*k)} ${n(5*k)} ${n(-dir*7*k)} ${n(5*k)}z`,c,sw)+'</g>';
    case'plume':return `<g${cls}>`+Pa(`M${n(x)} ${n(y)}q${n(dir*14*k)} ${n(-4*k)} ${n(dir*16*k)} ${n(-18*k)}q${n(dir*2*k)} ${n(10*k)} ${n(-dir*4*k)} ${n(16*k)}q${n(-dir*4*k)} ${n(4*k)} ${n(-dir*12*k)} ${n(4*k)}z`,c,sw)+'</g>';
    case'stub':return Pa(`M${n(x)} ${n(y)}q${n(dir*5*k)} ${n(-1*k)} ${n(dir*5*k)} ${n(-5*k)}q${n(-dir*3*k)} ${n(-1*k)} ${n(-dir*6*k)} ${n(1*k)}z`,c,sw);
    case'pom':return `<g${cls}>`+L(`M${n(x)} ${n(y)}q${n(dir*8*k)} ${n(-3*k)} ${n(dir*9*k)} ${n(-11*k)}`,OL,3.6)+L(`M${n(x)} ${n(y)}q${n(dir*8*k)} ${n(-3*k)} ${n(dir*9*k)} ${n(-11*k)}`,c,2)+C(x+dir*9*k,y-13*k,4.8*k,c,1.4)+'</g>';
    case'thin':return `<g${cls}>`+L(`M${n(x)} ${n(y)}q${n(dir*12*k)} ${n(-2*k)} ${n(dir*13*k)} ${n(-14*k)}`,OL,4)+L(`M${n(x)} ${n(y)}q${n(dir*12*k)} ${n(-2*k)} ${n(dir*13*k)} ${n(-14*k)}`,c,2.4)+'</g>';
    case'long':{const st=S.stripes?K.m:null;return `<g${cls}>`+L(`M${n(x)} ${n(y)}q${n(dir*16*k)} ${n(0)} ${n(dir*14*k)} ${n(-18*k)}`,OL,6)+L(`M${n(x)} ${n(y)}q${n(dir*16*k)} ${n(0)} ${n(dir*14*k)} ${n(-18*k)}`,S.face==='calico'?K.m:c,4)
      +(st?L(`M${n(x+dir*10*k)} ${n(y-3*k)}l${n(dir*2.5*k)} ${n(-1)}M${n(x+dir*14*k)} ${n(y-9*k)}l${n(dir*2.5*k)} 0`,st,1.6):'')+'</g>';}
    case'thick':return `<g${cls}>`+L(`M${n(x)} ${n(y)}q${n(dir*15*k)} ${n(0)} ${n(dir*13*k)} ${n(-16*k)}`,OL,8)+L(`M${n(x)} ${n(y)}q${n(dir*15*k)} ${n(0)} ${n(dir*13*k)} ${n(-16*k)}`,c,6)+'</g>';
    case'fluffy':{const st=S.stripes?K.m:null;return `<g${cls}>`+Pa(`M${n(x)} ${n(y+2*k)}q${n(dir*18*k)} ${n(2*k)} ${n(dir*16*k)} ${n(-20*k)}q${n(dir*4*k)} ${n(-4*k)} ${n(dir*1*k)} ${n(-6*k)}q${n(-dir*6*k)} ${n(2*k)} ${n(-dir*8*k)} ${n(10*k)}q${n(-dir*2*k)} ${n(6*k)} ${n(-dir*9*k)} ${n(6*k)}z`,c,sw)
      +(st?L(`M${n(x+dir*12*k)} ${n(y-4*k)}l${n(dir*4*k)} ${n(-2*k)}M${n(x+dir*14*k)} ${n(y-11*k)}l${n(dir*4*k)} 0`,st,1.6):'')+'</g>';}
  }
  return '';
}

/* ---------------------------------------------------------------- the poses */
function marks(S,K,cx,cy,rx,ry){   // body markings: tabby stripes, Bengal spots, the ridge, a calico patch
  let s='';
  if(S.stripes||/Vện/.test(K.name||''))s+=L([-.45,-.15,.15,.45].map(t=>`M${n(cx+t*rx)} ${n(cy-ry*.95)}q${n(rx*.06)} ${n(ry*.4)} 0 ${n(ry*.75)}`).join(''),K.m,1.6,' opacity=".85"');
  if(S.spots)s+=[[-.5,-.4],[-.1,-.6],[.3,-.3],[-.3,.1],[.15,.15],[.55,-.05]].map(([a,b])=>E(cx+a*rx,cy+b*ry,rx*.09+1,ry*.12+.6,K.m,0,' opacity=".9"')).join('');
  if(S.ridge)s+=Pa(`M${n(cx-rx*.55)} ${n(cy-ry*.9)}q${n(rx*.55)} ${n(-ry*.42)} ${n(rx*1.1)} 0q${n(-rx*.55)} ${n(-ry*.12)} ${n(-rx*1.1)} 0z`,K.m,0,' opacity=".9"');
  if(S.face==='calico'||S.face==='calico2'&&K.name==='Tam thể')s+=E(cx-rx*.35,cy-ry*.4,rx*.32,ry*.36,K.m,0)+E(cx+rx*.32,cy-ry*.1,rx*.24,ry*.3,K.l,0);
  if(S.face==='points')s+='';
  return s;
}
function sitPose(S,K,o){
  const sc=S.body||1,legs=S.legs||1,lng=S.long||1,hr=12.5*(S.head||1),bw=13*sc*(S.chubby?1.12:1),bh=17*sc*(S.legs<.7?.85:1);
  const by=-bh*.62,hy=by-bh*.55-hr*.62,happy=o.mood==='happy';let s='';
  s+=E(0,-.5,bw*1.2+4,2.4,'#000',0,' opacity=".12"');
  s+=tail(S,K,-bw*.7,-3,-1,1.05*sc);
  s+=E(-bw*.62,-bw*.38,bw*.5,bw*.4,K.b,1.5)+E(bw*.62,-bw*.38,bw*.5,bw*.4,K.b,1.5);   // haunches
  s+=E(0,by,bw,bh*.62,S.bald?K.b:K.b,1.6);                                         // body
  const chest=S.face==='mask'||S.face==='urajiro'||S.face==='blaze'||S.face==='tux'&&/^#f|^#e/i.test(K.l)||S.fluff==='ruff'||S.face==='points'||S.face==='tux2'&&K.name==='Hai màu';
  if(chest)s+=E(0,by+bh*.08,bw*.55,bh*.48,K.l,0);
  s+=marks(S,K,0,by+2,bw,bh*.55);
  if(o.acc?.body)s+=coat(o.acc.body,'sit',0,by-bh*.45,bw,bh*.95);
  const lh=Math.max(5,11*legs),lx=bw*.38,paw=S.face==='points'?K.m:(chest?K.l:K.b),raise=happy?1:0;
  s+=R(-lx-3.4,-lh,6.8,lh+1,K.b,3,1.4)+E(-lx,-1.2,4.2,2.6,paw,1.3);
  s+=raise?`<g class="pet-wave" transform="rotate(-40 ${n(bw*.55)} ${n(by+bh*.05)})">${R(bw*.55-3.4,by+bh*.05-12,6.8,13,K.b,3.4,1.4)+E(bw*.55,by+bh*.05-12.5,4.2,3.2,paw,1.3)+E(bw*.55,by+bh*.05-13.5,1.6,1,PINK,0)}</g>`:R(lx-3.4,-lh,6.8,lh+1,K.b,3,1.4)+E(lx,-1.2,4.2,2.6,paw,1.3);
  if(raise)s+=R(lx-3.4,-lh,6.8,lh+1,K.b,3,1.4)+E(lx,-1.2,4.2,2.6,paw,1.3);
  s+=collar(o.acc?.neck,0,hy+hr*.86,hr*.62);
  s+=head(S,K,0,hy,hr,{mood:o.mood,acc:o.acc});
  if(happy)s+=`<g class="pet-hearts">${heart(hr*1.25,hy-hr*.9,2.2)+heart(-hr*1.35,hy-hr*.4,1.6,'#f5a9bc')}</g>`;
  return s;
}
function walkPose(S,K,o){
  const sc=S.body||1,legs=S.legs||1,lng=S.long||1,hr=11.5*(S.head||1),rx=13*sc*lng*(S.chubby?1.08:1),ry=8.2*sc,lh=Math.max(4.5,10*legs);
  const cy=-lh-ry*.6,hx=rx*.72,hy=cy-ry-hr*.35;let s='';
  s+=E(0,-.5,rx+5,2.3,'#000',0,' opacity=".12"');
  const leg=(x,cls)=>`<g class="pet-leg ${cls}">${R(x-2.8,cy+ry*.2,5.6,lh+ry*.4-1,K.b,2.6,1.3)+E(x,-1.1,3.6,2.1,S.face==='points'?K.m:K.l,1.1)}</g>`;
  s+=leg(-rx*.58,'b')+leg(rx*.5,'a');                                                  // far legs
  s+=tail(S,K,-rx*.9,cy-ry*.25,-1,.95*sc);
  s+=E(0,cy,rx,ry,K.b,1.6);
  if(S.face!=='calico'&&(S.face==='mask'||S.face==='urajiro'||S.face==='blaze'||S.fluff==='ruff'||S.face==='tux'&&/^#f|^#e/i.test(K.l)))s+=Pa(`M${n(-rx*.6)} ${n(cy+ry*.6)}q${n(rx*.6)} ${n(ry*.55)} ${n(rx*1.3)} ${n(-ry*.2)}q${n(-rx*.5)} ${n(ry*.05)} ${n(-rx*1.3)} ${n(ry*.2)}z`,K.l,0);
  s+=marks(S,K,0,cy,rx,ry);
  if(o.acc?.body)s+=coat(o.acc.body,'walk',0,cy,rx,ry);
  s+=leg(-rx*.38,'a')+leg(rx*.68,'b');                                                 // near legs
  s+=collar(o.acc?.neck,hx,hy+hr*.84,hr*.58);
  s+=head(S,K,hx,hy,hr,{mood:o.mood,acc:o.acc});
  return s;
}
function sleepPose(S,K,o){
  const sc=S.body||1,lng=S.long||1,hr=11*(S.head||1),rx=16*sc*Math.min(1.25,lng),ry=8.5*sc;let s='';
  s+=E(0,-.4,rx+5,2.4,'#000',0,' opacity=".12"');
  s+=E(0,-ry,rx,ry,K.b,1.6)+marks(S,K,0,-ry,rx,ry);
  if(o.acc?.body)s+=Pa(`M${n(-rx*.7)} ${n(-ry*1.75)}q${n(rx*.6)} ${n(-ry*.35)} ${n(rx*1.2)} ${n(.2)}l${n(rx*.05)} ${n(ry*1.1)}h${n(-rx*1.3)}z`,coatColor(o.acc.body),1.2);
  s+=tail(S,K,-rx*.85,-ry*.45,1,.0001,false);
  s+=Pa(`M${n(-rx*.95)} ${n(-ry*.6)}q${n(rx*.2)} ${n(ry*.75)} ${n(rx*1.25)} ${n(ry*.5)}`,'none',0)+L(`M${n(-rx*.95)} ${n(-ry*.55)}q${n(rx*.1)} ${n(ry*.62)} ${n(rx*1.2)} ${n(ry*.42)}`,OL,5.2)+L(`M${n(-rx*.95)} ${n(-ry*.55)}q${n(rx*.1)} ${n(ry*.62)} ${n(rx*1.2)} ${n(ry*.42)}`,S.face==='points'?K.m:K.b,3.4);
  s+=E(rx*.32,-2.2,5,2.6,S.face==='points'?K.m:K.l,1.2);
  s+=collar(o.acc?.neck,rx*.58,-hr*.5,hr*.55);
  s+=head(S,K,rx*.62,-hr*.95,hr,{blink:'sleep',acc:o.acc});
  s+=`<g class="pet-zz"><text x="${n(rx*.62+hr)}" y="${n(-hr*2.1)}" font-size="8" font-weight="800" fill="${OL}">z</text><text x="${n(rx*.62+hr+6)}" y="${n(-hr*2.6)}" font-size="6" font-weight="800" fill="${OL}">z</text></g>`;
  return s;
}
const coatColor=id=>({ao_len:'#e58b7a',ao_mua:'#f6cf45',ao_vn:'#d8392f',ao_khung_long:'#79b86b',ao_dai:'#d94f6e',vay_cong_chua:'#c8a6ef'})[id]||'#ccc';

/** The pet's markup, paws on y = 0 (no <svg> wrapper). breed: {shape, size}; coat: {b, m, l, e, name}; pose: sit | walk |
 * sleep | happy; acc: {neck, head, body, bed}. An unknown shape draws a plain dog. */
export function petInner(breed,coat,pose='sit',acc={}){
  const S=SHAPES[breed?.shape]||SHAPES.mutt,K={b:'#e2a65a',m:'#c4823a',l:'#fbe3bd',e:EYE,...(coat||{})},k=SIZE[breed?.size]||1,o={acc:acc||{},mood:pose==='happy'?'happy':''};
  const body=pose==='walk'?walkPose(S,K,o):pose==='sleep'?sleepPose(S,K,o):sitPose(S,K,o);
  const bed=acc?.bed?bedSVG(acc.bed,pose==='walk'?52:46):'';
  return `<g class="pet-art pet-${pose}">${bed&&(acc.bed==='nha_go'||acc.bed==='lau_dai')?bed:''}<g transform="scale(${k})">${bed&&!(acc.bed==='nha_go'||acc.bed==='lau_dai')?`<g transform="scale(${n(1/k*100)/100})">${bed}</g>`:''}<g class="pet-bob">${body}</g></g></g>`;
}
/** A whole <svg>, `size` px wide (the box is fitted to the pose). */
export function petSVG(breed,coat,pose='sit',acc={},size=72,cls='pet-svg'){
  const vb=pose==='walk'||pose==='sleep'?'-36 -58 72 62':'-34 -64 68 68';
  return `<svg class="${cls}" viewBox="${vb}" width="${size}" height="${size}" aria-hidden="true" focusable="false">${petInner(breed,coat,pose,acc)}</svg>`;
}
/** Look a pet up in the catalogue (content.journey.pets): {breed, coat} for a save's {b, c}. */
export function lookup(cat,b,c){const breed=(cat?.breeds||[]).find(x=>x.id===b);return breed?{breed,coat:breed.coats[c]||breed.coats[0]}:null;}
/** An <img> source for canvases (town map, the stroll): the pet as a data URL. */
export function petURL(breed,coat,pose,acc,size=96){return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(petSVG(breed,coat,pose,acc,size).replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" '));}
/** The pet a save walks with ({b, c, n, a}: game/pets.py walk_ref, live `pt`) as an <img> source, or ''. */
export function refURL(cat,ref,pose='walk',size=120){
  const L=lookup(cat,ref?.b,ref?.c);if(!L)return '';
  const acc={};for(const id of Array.isArray(ref.a)?ref.a:[]){const a=(cat.accs||[]).find(x=>x.id===id);if(a)acc[a.slot]=id;}
  return petURL(L.breed,L.coat,pose,acc,size);
}
