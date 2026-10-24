/** 🐾 Thú cưng: the drawings (pure SVG strings, no DOM), in the cozy style of ./deco-art.js (warm brown outline,
 * pastel fills, blush, shiny eyes). game/pets_content.py has the breeds and their coats; each breed names a `shape`
 * (its body plan, SHAPES below) and a coat gives the colours: b base, m markings, l light parts, e eyes.
 * Poses: sit (looking at you), walk (side view, facing right, legs swing with CSS), sleep (curled up), happy.
 * Accessories (game/pets_content.py ACCS): neck, head, body are worn; bed is drawn under the pet.
 * A pet is drawn with its paws on y = 0, centred on x = 0, about 56 units tall when sitting. */

const OL='#5b4535',PINK='#f59bb0',NOSE='#4a3530',TONGUE='#f08aa0',EYE='#3b2a22';
const n=v=>Math.round(v*10)/10;
/* the outline: OL at `sw` unless the extra attributes `x` bring their own stroke / width (a duplicate attribute breaks
 * the SVG as an <img>: the walking pet on the town canvas, petURL) */
const SK=(sw,x,j='')=>sw?(x.includes(' stroke="')?'':` stroke="${OL}"`)+(x.includes(' stroke-width=')?'':` stroke-width="${sw}"`)+j:'';
const E=(cx,cy,rx,ry,f,sw=1.5,x='')=>`<ellipse cx="${n(cx)}" cy="${n(cy)}" rx="${n(rx)}" ry="${n(ry)}" fill="${f}"${SK(sw,x)}${x}/>`;
const C=(cx,cy,r,f,sw=1.5,x='')=>`<circle cx="${n(cx)}" cy="${n(cy)}" r="${n(r)}" fill="${f}"${SK(sw,x)}${x}/>`;
const R=(x,y,w,h,f,rx=3,sw=1.5,ex='')=>`<rect x="${n(x)}" y="${n(y)}" width="${n(w)}" height="${n(h)}" rx="${n(rx)}" fill="${f}"${SK(sw,ex)}${ex}/>`;
const Pa=(d,f,sw=1.5,x='')=>`<path d="${d}" fill="${f}"${SK(sw,x,' stroke-linejoin="round" stroke-linecap="round"')}${x}/>`;
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
  // 19/10: the new shop breeds, the 🧬 hybrids and the 🌟 legendaries (game/pets_content.py)
  becgie:{k:'dog',ear:'prick',tail:'plume',face:'mask',muzzle:'dog',long:1.15,body:1.05,brows:1},
  dalmatian:{k:'dog',ear:'flop',tail:'thin',muzzle:'dog',spots:1,smile:1},
  shihtzu:{k:'dog',ear:'long',tail:'plume',fluff:'ruff',muzzle:'flat',legs:.7,head:1.08,smile:1},
  beagle:{k:'dog',ear:'long',tail:'thin',face:'blaze',muzzle:'dog',brows:1},
  border:{k:'dog',ear:'flop',tail:'plume',face:'blaze',fluff:'ruff',muzzle:'dog',smile:1},
  frenchie:{k:'dog',ear:'huge',tail:'stub',muzzle:'flat',wrinkles:1,legs:.7,chubby:1},
  chowchow:{k:'dog',ear:'small',tail:'curl',fluff:'ruff',muzzle:'flat',body:1.12,chubby:1},
  akita:{k:'dog',ear:'prick',tail:'curl',face:'urajiro',muzzle:'dog',body:1.08},
  lai:{k:'dog',ear:'prick',tail:'thin',muzzle:'dog',stripes:1,brows:1},
  russian:{k:'cat',ear:'cat',tail:'long',muzzle:'cat'},
  aby:{k:'cat',ear:'bigcat',tail:'long',muzzle:'cat',face:'tabby'},
  exotic:{k:'cat',ear:'catsmall',tail:'thick',muzzle:'flatcat',chubby:1},
  mau:{k:'cat',ear:'cat',tail:'long',muzzle:'cat',spots:1},
  hmong:{k:'dog',ear:'prick',tail:'stub',fluff:'ruff',muzzle:'dog',body:1.05,brows:1},
  doodle:{k:'dog',ear:'flop',tail:'plume',fluff:'curly',muzzle:'dog',smile:1},
  pomsky:{k:'dog',ear:'prick',tail:'plume',face:'mask',fluff:'ruff',muzzle:'dog',legs:.75,head:1.06,smile:1},
  corgi_inu:{k:'dog',ear:'big',tail:'curl',face:'urajiro',legs:.55,long:1.3,muzzle:'dog',smile:1,brows:1},
  wolf:{k:'dog',ear:'prick',tail:'plume',face:'mask',fluff:'ruff',muzzle:'dog',body:1.15,long:1.1,brows:1},
  dom_xe:{k:'dog',ear:'fold',tail:'stub',muzzle:'flat',wrinkles:1,spots:1,head:1.05},
  himalaya:{k:'cat',ear:'catsmall',tail:'fluffy',fluff:'ruff',muzzle:'flatcat',face:'points',chubby:1},
  ragamuffin:{k:'cat',ear:'cat',tail:'fluffy',fluff:'ruff',muzzle:'cat',chubby:1,body:1.08},
  toyger:{k:'cat',ear:'cat',tail:'long',face:'tabby',muzzle:'cat',stripes:1,body:1.05},
  kilt:{k:'cat',ear:'fold',tail:'thick',legs:.5,muzzle:'cat',chubby:1},
  jade:{k:'cat',ear:'bigcat',tail:'long',muzzle:'cat',face:'tux2'},
  linh_khuyen:{k:'dog',ear:'prick',tail:'plume',fluff:'ruff',muzzle:'dog',ridge:1,body:1.12,brows:1,smile:1},
  than_tai:{k:'cat',ear:'cat',tail:'long',face:'calico',muzzle:'cat',chubby:1},
  // ✨ thần thú (owner 19/10 "kì lân, kì lân 1 sừng, khủng long"): horns, manes, spikes, snouts, reptile tails
  ky_lan:{k:'dog',ear:'horse',horn:'antler',mane:'flame',tail:'qilin',muzzle:'snout',scales:1,belly:1,body:1.08,brows:1,smile:1},
  unicorn:{k:'cat',ear:'horse',horn:'uni',mane:'rainbow',tail:'horse',muzzle:'snout',smile:1},
  trex:{k:'dog',ear:'none',muzzle:'snout',spikes:1,tail:'dino',belly:1,head:1.1,smile:1},
  bronto:{k:'cat',ear:'none',muzzle:'snout',tail:'dino',neck:1,belly:1,body:1.1,spots:1,smile:1},
  trice:{k:'dog',ear:'none',horn:'trice',frill:1,muzzle:'snout',tail:'dino',belly:1,body:1.05,smile:1},
  dragon:{k:'cat',ear:'fin',horn:'dragon',spikes:1,tail:'dragon',bwings:1,muzzle:'snout',belly:1,smile:1},
  // 🐱 24/10: Mai, the owner's own Scottish Fold (game/pets_content.py meo_mai): white, a lilac-grey cap over the ears
  // with a white blaze (face 'cap'), a lilac saddle, a thick ringed tail with a dark tip, sleepy amber eyes (lazy), grey
  // toe beans, a thin yellow collar with a silver ring when nothing else is worn, and her famous pose: slumped against
  // the wall like a person, belly out, legs forward (slump: maiSit)
  mai:{k:'cat',ear:'fold',tail:'ringed',face:'cap',muzzle:'cat',chubby:1,saddle:1,lazy:1,collar:'#f2c230',slump:1},
};
/* 🏅 Ranks (game/pet_tiers.py RANKS: 0 D … 6 SSS) and the coat effects of an SSS (FX) or a mutant pup. */
export const RANK=['D','C','B','A','S','SS','SSS'];
export const RANK_COLOR=['#9aa0a6','#4caf6a','#3d8bfd','#a259ff','#f2b632','#ff6a3d','#ff4fa3'];
const FXCOAT={ngan_ha:{b:'#3d2f7a',m:'#22184f',l:'#8ea2ff',e:'#ffe66b'},hong_ngoc:{b:'#c72c48',m:'#7d1426',l:'#ff9db0',e:'#ffd54a'},
  bang_tinh:{b:'#dff4ff',m:'#9fd3f2',l:'#ffffff',e:'#38c6ff'},cau_vong:{b:'url(#pt-rbs)',m:'url(#pt-rb)',l:'#fffafd',e:'#3b2a22'}};
const DEFS='<defs><linearGradient id="pt-rb" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff7a7a"/><stop offset=".2" stop-color="#ffc56b"/><stop offset=".4" stop-color="#fff07a"/><stop offset=".6" stop-color="#7de08a"/><stop offset=".8" stop-color="#6fb6ff"/><stop offset="1" stop-color="#c58cff"/></linearGradient>'
  +'<linearGradient id="pt-rbs" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffc4d2"/><stop offset=".25" stop-color="#ffe0b3"/><stop offset=".45" stop-color="#fff6b8"/><stop offset=".65" stop-color="#c8f0cd"/><stop offset=".82" stop-color="#c4e1ff"/><stop offset="1" stop-color="#dcc8ff"/></linearGradient>'
  +'<linearGradient id="pt-wing2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffb3da"/><stop offset=".3" stop-color="#d9c6ff"/><stop offset=".6" stop-color="#bfe2ff"/><stop offset="1" stop-color="#ffffff"/></linearGradient>'
  +'<linearGradient id="pt-wing" x1="1" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#fff"/><stop offset=".55" stop-color="#fff4fb"/><stop offset=".8" stop-color="#e4dcff"/><stop offset="1" stop-color="#cfe9ff"/></linearGradient>'
  +'<linearGradient id="pt-gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff3b0"/><stop offset=".5" stop-color="#ffd24a"/><stop offset="1" stop-color="#e09a1a"/></linearGradient>'
  +'<radialGradient id="pt-glow-b"><stop offset="0" stop-color="#bfe0ff" stop-opacity=".8"/><stop offset="1" stop-color="#7fb8ff" stop-opacity="0"/></radialGradient>'
  +'<radialGradient id="pt-glow-a"><stop offset="0" stop-color="#ecd9ff" stop-opacity=".9"/><stop offset=".6" stop-color="#c39bff" stop-opacity=".45"/><stop offset="1" stop-color="#a259ff" stop-opacity="0"/></radialGradient>'
  +'<radialGradient id="pt-glow-s"><stop offset="0" stop-color="#fff4c4" stop-opacity=".95"/><stop offset=".6" stop-color="#ffd76a" stop-opacity=".5"/><stop offset="1" stop-color="#ffc83a" stop-opacity="0"/></radialGradient>'
  +'<radialGradient id="pt-glow-ss"><stop offset="0" stop-color="#ffe2b8" stop-opacity=".95"/><stop offset=".55" stop-color="#ff8a4d" stop-opacity=".55"/><stop offset="1" stop-color="#ff4a2d" stop-opacity="0"/></radialGradient>'
  +'<radialGradient id="pt-glow-sss"><stop offset="0" stop-color="#fff" stop-opacity="1"/><stop offset=".4" stop-color="#ffd1f0" stop-opacity=".7"/><stop offset=".75" stop-color="#bfe6ff" stop-opacity=".35"/><stop offset="1" stop-color="#c58cff" stop-opacity="0"/></radialGradient>'
  +'<radialGradient id="pt-glow-lg"><stop offset="0" stop-color="#fffbe0" stop-opacity="1"/><stop offset=".45" stop-color="#ffe07a" stop-opacity=".8"/><stop offset=".8" stop-color="#ffb52e" stop-opacity=".35"/><stop offset="1" stop-color="#ff9f1a" stop-opacity="0"/></radialGradient>'
  +'<filter id="pt-mut"><feColorMatrix type="hueRotate" values="150"/></filter></defs>';
const RB=['#ff7a7a','#ffc56b','#fff07a','#7de08a','#6fb6ff','#c58cff'];
/** Light rays fanning out of (cx, cy): `count` wedges from r0 to r1 in `cols` (turned slowly by CSS on a dialog). */
function rays(cx,cy,r0,r1,count,cols,op){
  let d='';const w=Math.PI/count*.42;
  for(let i=0;i<count;i++){const a=i*2*Math.PI/count,p=(t,r)=>`${n(cx+Math.cos(t)*r)} ${n(cy+Math.sin(t)*r)}`;
    d+=Pa(`M${p(a-w*.35,r0)}L${p(a-w,r1)}Q${p(a,r1*1.06)} ${p(a+w,r1)}L${p(a+w*.35,r0)}z`,cols[i%cols.length],0,` opacity="${op}"`);}
  return `<g class="pet-rays" style="transform-origin:${n(cx)}px ${n(cy)}px">${d}</g>`;
}
const gem=(x,y,s,c)=>Pa(`M${n(x)} ${n(y-s)}L${n(x+s*.62)} ${n(y)}L${n(x)} ${n(y+s)}L${n(x-s*.62)} ${n(y)}z`,c,0)+Pa(`M${n(x)} ${n(y-s)}L${n(x+s*.62)} ${n(y)}L${n(x)} ${n(y)}z`,'#fff',0,' opacity=".55"');
const flame=(x,y,h,c,c2)=>Pa(`M${n(x)} ${n(y)}q${n(-h*.42)} ${n(-h*.42)} ${n(-h*.06)} ${n(-h)}q${n(h*.08)} ${n(h*.3)} ${n(h*.26)} ${n(h*.36)}q${n(h*.24)} ${n(h*.28)} ${n(-h*.2)} ${n(h*.64)}z`,c,0)+E(x,y-h*.26,h*.13,h*.2,c2,0);
/** 🪽 An angel wing (owner 19/10 "cánh cho đẹp tí nhé"): three rows of round-tipped feathers fanning out of (x, y),
 * long pastel primaries, soft secondaries, white coverts, a glow behind and a twinkle at the tip. */
function feather(len,ang,wid,fill,edge){
  const r=ang*Math.PI/180,c=Math.cos(r),s=Math.sin(r),px=-s,py=c,b0=len*.12,m=len*.58;
  const P=(t,o)=>`${n(c*t+px*o)} ${n(s*t+py*o)}`;
  const t=len-wid*.55,rr=n(wid*.62);   // a rounded tip
  return `<path d="M${P(b0,-wid*.35)}Q${P(m,-wid*1.05)} ${P(t,-wid*.62)}A${rr} ${rr} 0 0 1 ${P(t,wid*.62)}Q${P(m,wid*1.05)} ${P(b0,wid*.35)}z" fill="${fill}" stroke="${edge}" stroke-width=".7" stroke-linejoin="round"/>`
    +`<path d="M${P(b0+1,0)}Q${P(m,wid*.12)} ${P(len*.92,0)}" fill="none" stroke="${edge}" stroke-width=".45" opacity=".7"/>`;
}
const PRIM=[[168,24],[178,31],[189,37],[200,41],[211,42],[222,40],[233,35],[244,28],[254,20]];
const wing=(x,y,s,flip)=>`<g transform="translate(${n(x)} ${n(y)}) scale(${n(flip*s)} ${n(s)})">`
  +`<ellipse cx="-17" cy="-16" rx="25" ry="21" fill="url(#pt-glow-sss)" opacity=".8"/>`
  +PRIM.map(([a,l])=>feather(l,a,5.4,'url(#pt-wing2)','#9f86d6')).join('')
  +PRIM.slice(1,8).map(([a,l])=>feather(l*.64,a+5,6.2,'url(#pt-wing)','#b7a2e6')).join('')
  +[[196,13],[212,15.5],[228,15.5],[243,13],[256,10]].map(([a,l])=>feather(l,a,6.4,'#fff','#c9b8f0')).join('')
  +star(-40,-22,2.8,'#fff')+star(-30,-38,1.8,'#ffe27a')+star(-42,-4,1.5,'#ffd1f0')+'</g>';
const coin=(x,y,r)=>C(x,y,r,'url(#pt-gold)',.9,' stroke="#b47a10"')+R(x-r*.32,y-r*.32,r*.64,r*.64,'#d39a20',0,0);
const ingot=(x,y,s)=>Pa(`M${n(x-s*1.5)} ${n(y)}q${n(-s*.4)} ${n(-s*1.2)} ${n(s*.3)} ${n(-s*1.1)}q${n(s*1.2)} ${n(-s*.9)} ${n(s*2.4)} 0q${n(s*.7)} ${n(-s*.1)} ${n(s*.3)} ${n(s*1.1)}z`,'url(#pt-gold)',1,' stroke="#b47a10"')+E(x,y-s*1.05,s*.7,s*.32,'#fff3b0',0);
const cloud=(x,y,s,c,edge)=>Pa(`M${n(x-s*2)} ${n(y)}q${n(-s*.4)} ${n(-s*1.3)} ${n(s*.7)} ${n(-s*1.2)}q${n(s*.5)} ${n(-s*1.2)} ${n(s*1.6)} ${n(-s*.5)}q${n(s*1.3)} ${n(-s*.4)} ${n(s*1.6)} ${n(s*.9)}q${n(s*.6)} ${n(s*.5)} ${n(-s*.1)} ${n(s*.8)}z`,c,1,` stroke="${edge}"`)
  +L(`M${n(x-s*.6)} ${n(y-s*.5)}q${n(s*.5)} ${n(-s*.6)} ${n(s*1)} 0`,edge,.9);
/** Where the head is (a halo above it), by pose; `k` the breed's size. */
const headAt=(pose,k)=>pose==='walk'?{x:9.5*k,y:-46*k-3}:pose==='sleep'?{x:10*k,y:-27*k}:{x:0,y:-48*k-4};
/** What stands behind the pet (glow, rays, wings, its rank's ring) and what floats in front (sparkles, halo, embers,
 * coins). Owner 19/10 "bậc B, A, S, SS cũng cho đẹp đẹp, SSS thì siêu đẹp", "mèo huyền thoại cũng cho nổi hơn". */
function aura(r,x,legend,kind,pose,k=1){
  if(!r&&!legend)return ['',''];
  const col=RANK_COLOR[r]||RANK_COLOR[0],walk=pose==='walk',sleep=pose==='sleep',top=r>=6||legend,H=headAt(pose,k);
  let back='',front='',ring='';
  const cy=sleep?-12:-25;
  // the ring on the ground: one line (C), two (B…), a rainbow for SSS, gold for the legendaries
  const rc=legend?'url(#pt-gold)':top?'url(#pt-rb)':col;
  ring+=`<ellipse cx="0" cy="-.5" rx="25" ry="5.2" fill="${legend?'#ffd24a':col}" opacity="${r>=4||legend?.3:.18}"/><ellipse cx="0" cy="-.5" rx="25" ry="5.2" fill="none" stroke="${rc}" stroke-width="${r>=4||legend?2.6:1.8}"/>`;
  if(r>=2||legend)ring+=`<ellipse cx="0" cy="-.5" rx="30" ry="6.6" fill="none" stroke="${rc}" stroke-width="${top?1.6:1}" opacity="${top?.9:.6}"${top?'':' stroke-dasharray="3 3"'}/>`;
  if(r===1)front+=`<g class="pet-spark">${star(-22,-34,2,'#7ed39a')+star(22,-40,1.6,'#7ed39a')}</g>`;
  if(r===2&&!legend){
    back+=`<ellipse class="pet-glow" cx="0" cy="${cy}" rx="30" ry="27" fill="url(#pt-glow-b)"/>`;
    front+=`<g class="pet-spark">${gem(-24,-36,3.2,'#8cc4ff')+gem(23,-44,2.6,'#b5dbff')+star(26,-20,2,'#d6ecff')}</g>`
      +`<g class="pet-rise">${C(-28,-14,1.6,'#cfe6ff',.6,' stroke="#8cc4ff"')+C(28,-26,1.2,'#cfe6ff',.6,' stroke="#8cc4ff"')}</g>`;
  }
  if(r===3&&!legend){
    back+=`<ellipse class="pet-glow" cx="0" cy="${cy}" rx="34" ry="31" fill="url(#pt-glow-a)"/>`;
    ring+=[[-22,-3],[-9,-5.3],[9,-5.3],[22,-3]].map(([a,b])=>gem(a,b,2.2,'#c9a2ff')).join('');
    front+=`<g class="pet-spark">${star(-25,-40,3,'#d9b8ff')+star(24,-48,2.6,'#ffd1f0')+star(28,-20,2,'#c9a2ff')+star(-28,-18,1.8,'#ffd1f0')}</g>`
      +`<g class="pet-rise">${gem(-30,-22,3,'#b98cff')+gem(30,-32,2.4,'#e0c8ff')}</g>`;
  }
  if(r===4&&!legend){
    back+=rays(0,cy,12,38,12,['#ffd76a','#fff1b0'],.42)+`<ellipse class="pet-glow" cx="0" cy="${cy}" rx="34" ry="31" fill="url(#pt-glow-s)"/>`;
    front+=`<g class="pet-spark">${star(-25,-42,3.4,'#ffd24a')+star(23,-50,2.8,'#ffe066')+star(29,-20,2.2,'#ffd24a')+star(-29,-18,2,'#fff1b0')+star(4,-58,2.4,'#ffe066')}</g>`;
  }
  if(r===5&&!legend){
    back+=rays(0,cy,12,40,14,['#ff8a4d','#ffc06b','#ff5a3d'],.38)+`<ellipse class="pet-glow" cx="0" cy="${cy}" rx="36" ry="33" fill="url(#pt-glow-ss)"/>`;
    back+=[-24,-12,12,24].map((xx,i)=>flame(xx,-1+(i%3?0:1),9+i%2*3,'#ff7a3d','#ffd27a')).join('');
    front+=`<g class="pet-spark">${star(-26,-42,3.4,'#ffb36b')+star(24,-52,2.8,'#ffd27a')+star(30,-22,2.2,'#ff8a4d')+star(-30,-20,2,'#ffd27a')+star(4,-60,2.6,'#ffb36b')}</g>`
      +`<g class="pet-rise">${C(-20,-30,1.3,'#ffb36b',0)+C(18,-38,1.1,'#ffd27a',0)+C(26,-12,1.3,'#ff7a3d',0)+C(-27,-8,1,'#ffd27a',0)}</g>`
      +flame(-24,-1,9,'#ff9a52','#ffe6a8')+flame(24,-1,10,'#ff9a52','#ffe6a8');
  }
  if(top&&!legend){   // 🌈 SSS: angel wings, a halo, rainbow rays and a shower of stars
    back+=rays(0,cy,14,46,12,RB,.3)+`<ellipse class="pet-glow" cx="0" cy="${cy}" rx="42" ry="39" fill="url(#pt-glow-sss)"/>`;
    if(!sleep)back+=`<g class="pet-wings">${walk?wing(-6*k,-22*k,.78*k,1)+wing(-1*k,-26*k,.62*k,1):wing(-7*k,-28*k,.8*k,1)+wing(7*k,-28*k,.8*k,-1)}</g>`;
    front+=`<g class="pet-halo">${E(H.x,H.y,9.5,2.8,'none',0,' stroke="#ffe27a" stroke-width="2.4"')+E(H.x,H.y,9.5,2.8,'none',0,' stroke="#fff" stroke-width=".8" opacity=".9"')}</g>`;
    front+=`<g class="pet-spark">${[[-30,-44,3.4],[27,-54,3],[33,-24,2.4],[-33,-20,2.2],[6,-66,2.8],[-14,-60,2],[20,-8,1.8]].map(([a,b,s],i)=>star(a,b,s,RB[i%6])).join('')}</g>`
      +`<g class="pet-spark b">${[[-20,-52],[30,-40],[-36,-32],[14,-62]].map(([a,b])=>star(a,b,1.6,'#fff')).join('')}</g>`;
    if(x==='cau_vong')front+=L(`M${n(H.x-14)} ${n(H.y-3)}q14 -12 28 0`,'url(#pt-rb)',2.2,' opacity=".85"');
    if(x==='ngan_ha')front+=[[-6,-22],[4,-28],[8,-16],[-2,-12],[-34,-50],[34,-46]].map(([a,b])=>C(a,b,.9,'#fff',0)).join('');
    if(x==='hong_ngoc')back+=[-26,-14,14,26].map((xx,i)=>flame(xx,-1,8+i%2*3,'#e2384f','#ffb3c0')).join('');
    if(x==='bang_tinh')front+=`<g class="pet-rise">${[[-28,-30],[28,-38],[-18,-56]].map(([a,b])=>L(`M${a-3} ${b}h6M${a} ${b-3}v6M${a-2} ${b-2}l4 4M${a+2} ${b-2}l-4 4`,'#9fdcff',1)).join('')}</g>`;
  }
  if(legend){   // 🌟 legendaries: golden rays, a gold halo, lucky clouds; the cat's coins and gold, the dog's dragon
    back+=rays(0,cy,14,48,16,['#ffd24a','#fff1b0','#ffb52e'],.38)+`<ellipse class="pet-glow" cx="0" cy="${cy}" rx="44" ry="40" fill="url(#pt-glow-lg)"/>`;
    ring+=cloud(-27,0,4.2,'#ffe9b0','#e0a92e')+cloud(29,0,3.6,'#ffd9d0','#e05a4f');
    front+=`<g class="pet-halo">${E(H.x,H.y,10,3,'none',0,' stroke="url(#pt-gold)" stroke-width="2.8"')+E(H.x,H.y,10,3,'none',0,' stroke="#fff8d0" stroke-width=".8"')}</g>`;
    front+=`<g class="pet-spark">${[[-30,-46,3.4],[28,-56,3],[34,-24,2.4],[-34,-22,2.2],[6,-68,2.8]].map(([a,b,s])=>star(a,b,s,'#ffd24a')).join('')}${star(-12,-62,2,'#fff')+star(20,-12,1.8,'#fff')}</g>`;
    if(kind==='cat')front+=`<g class="pet-coins">${coin(-26,-34,3.4)+coin(24,-44,3)+coin(31,-16,2.6)+coin(-32,-12,2.4)}</g><g class="pet-fall">${coin(-14,-58,2.2)+coin(16,-64,2)+coin(-4,-70,1.8)}</g>`
      +ingot(-17,-1,3.2)+ingot(18,-1,3)+`<g class="pet-spark b">${C(-36,-38,1.2,'#ff6a5a',0)+C(36,-34,1.2,'#ff6a5a',0)}</g>`;
    if(kind==='dog')back+=L('M-34 -8q-12 -26 6 -42q16 -14 32 -2q12 10 4 24q-6 10 -16 6','url(#pt-gold)',3.2,' class="pet-dragon"')
      +L('M-34 -8q-12 -26 6 -42q16 -14 32 -2q12 10 4 24q-6 10 -16 6','#fff3b0',1,' class="pet-dragon"')+C(-12,-49,2.6,'url(#pt-gold)',.8,' stroke="#b47a10"')+C(-11.4,-49.6,.7,'#2fd4c0',0);
    if(kind==='dog')front+=`<g class="pet-rise">${star(-30,-30,2,'#2fd4c0')+star(30,-36,1.8,'#2fd4c0')}</g>`;
  }
  if((r>=5||legend)&&walk)front+=`<g class="pet-trail" opacity=".85">${[-36,-29,-22].map((xx,i)=>E(xx,-1.2-(i%2)*1.6,1.9,1.1,legend?'#ffd24a':r>=6?RB[i*2]:'#ff8a4d',0,` opacity="${.35+i*.2}"`)).join('')}</g>`;
  if(x==='ngan_ha'&&!top)front+=[[-6,-22],[4,-28],[8,-16],[-2,-12]].map(([a,b])=>C(a,b,.9,'#fff',0)).join('');
  return [back+ring,front];
}
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
    case'horse':return pair(.3,1.5,.1,'#f7b9c7');
    case'none':return '';
    case'fin':return front?[-1,1].map(sx=>Pa(`M${n(x+sx*r*.9)} ${n(y-r*.15)}l${n(sx*r*.55)} ${n(-r*.42)}l${n(-sx*r*.08)} ${n(r*.28)}l${n(sx*r*.3)} ${n(-r*.05)}l${n(-sx*r*.22)} ${n(r*.34)}z`,K.m,1.2)).join(''):'';
    case'puff':return front?[-1,1].map(sx=>C(x+sx*r*.98,y+r*.12,r*.42,b,1.4)+C(x+sx*r*.92,y+r*.5,r*.34,b,1.4)).join(''):'';
    case'fold':if(!front)return '';
      if(S.face==='cap')return [-1,1].map(sx=>{const X=t=>n(x+sx*r*t);
        return Pa(`M${X(.24)} ${n(y-r*.86)}Q${X(.42)} ${n(y-r*1.12)} ${X(.74)} ${n(y-r*1)}Q${X(.97)} ${n(y-r*.9)} ${X(.9)} ${n(y-r*.6)}Q${X(.6)} ${n(y-r*.8)} ${X(.24)} ${n(y-r*.86)}z`,m,1.3)
          +L(`M${X(.4)} ${n(y-r*.94)}Q${X(.66)} ${n(y-r*.97)} ${X(.86)} ${n(y-r*.76)}`,dk(m,.8),.9);}).join('');
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
    case'cap':o+=[-1,1].map(sx=>{const A=r*(S.chubby?1.2:1.1),B=r*(S.chubby?.9:.95),P=t=>{const a=t*Math.PI/180;return `${n(x+A*Math.cos(a))} ${n(y+B*Math.sin(a))}`;},X=t=>n(x+sx*r*t);
      const top=sx<0?-94:-86,side=sx<0?-174:-4,low=sx<0?-.1:.02;   // the right lobe reaches a little lower, by the eye (the photo)
      return Pa(`M${P(top)}A${n(A)} ${n(B)} 0 0 ${sx<0?0:1} ${P(side)}C${X(.98)} ${n(y+r*low)} ${X(.7)} ${n(y-r*.36)} ${X(.3)} ${n(y-r*.44)}Q${X(.14)} ${n(y-r*.6)} ${X(.08)} ${n(y-r*.89)}z`,m,0);}).join('');break;
    case'tux':if(/^#f|^#e/i.test(l)&&l!==b)o+=Pa(`M${n(x-r*.15)} ${n(y-r*.62)}q${n(r*.15)} ${n(-r*.06)} ${n(r*.3)} 0l${n(r*.2)} ${n(r*.6)}h${n(-r*.7)}z`,l,0);break;
  }
  if(S.wrinkles)o+=L(`M${n(x-r*.32)} ${n(y-r*.6)}q${n(r*.32)} ${n(-r*.14)} ${n(r*.64)} 0M${n(x-r*.22)} ${n(y-r*.44)}q${n(r*.22)} ${n(-r*.1)} ${n(r*.44)} 0`,S.k==='cat'?K.m:K.m,1.1,' opacity=".7"');
  if(S.brows&&/Đen vàng|Tam thể/.test(K.name||''))o+=E(x-r*.4,y-r*.36,r*.13,r*.09,K.m,0)+E(x+r*.4,y-r*.36,r*.13,r*.09,K.m,0);
  // Muzzle, nose, mouth.
  const my=y+r*(cat?.32:.36);
  if(S.muzzle==='snout'){o+=E(x,my+r*.04,r*.6,r*.4,l,1.1)+C(x-r*.17,my-r*.06,r*.055,NOSE,0)+C(x+r*.17,my-r*.06,r*.055,NOSE,0);}
  else if(S.muzzle==='dog'){o+=E(x,my,r*.48,r*.36,S.face==='mask'||S.face==='urajiro'||S.face==='blaze'?l:l,0)+Pa(`M${n(x-r*.2)} ${n(my-r*.2)}q${n(r*.2)} ${n(-r*.1)} ${n(r*.4)} 0q${n(-.02)} ${n(r*.2)} ${n(-r*.2)} ${n(r*.24)}q${n(-r*.2)} ${n(-r*.04)} ${n(-r*.2)} ${n(-r*.24)}z`,NOSE,0)+C(x-r*.07,my-r*.18,r*.05,'#fff',0,' opacity=".7"');}
  else if(S.muzzle==='flat'){o+=E(x,my+r*.02,r*.56,r*.4,m,0)+E(x,my-r*.14,r*.2,r*.13,NOSE,0);}
  else{const fl=S.muzzle==='flatcat';o+=E(x-r*.16,my+r*.06,r*.2,r*.15,l,0)+E(x+r*.16,my+r*.06,r*.2,r*.15,l,0)+Pa(`M${n(x-r*.1)} ${n(my-r*(fl?.14:.08))}h${n(r*.2)}l${n(-r*.1)} ${n(r*.12)}z`,'#e88a9c',0)
    +L(`M${n(x-r*.55)} ${n(my)}l${n(-r*.55)} ${n(-r*.08)}M${n(x-r*.55)} ${n(my+r*.12)}l${n(-r*.52)} ${n(r*.1)}M${n(x+r*.55)} ${n(my)}l${n(r*.55)} ${n(-r*.08)}M${n(x+r*.55)} ${n(my+r*.12)}l${n(r*.52)} ${n(r*.1)}`,OL,.7,' opacity=".55"');}
  const mouthY=my+(S.muzzle==='dog'?r*.08:S.muzzle==='snout'?r*.16:r*.14),happy=mood==='happy';
  if(happy&&(S.k==='dog'||S.muzzle==='snout'))o+=Pa(`M${n(x-r*.22)} ${n(mouthY)}q${n(r*.22)} ${n(r*.5)} ${n(r*.44)} 0z`,'#a8434f',1.1)+Pa(`M${n(x-r*.11)} ${n(mouthY+r*.14)}q${n(r*.11)} ${n(r*.36)} ${n(r*.22)} 0z`,TONGUE,0);
  else if(happy)o+=Pa(`M${n(x-r*.16)} ${n(mouthY)}q${n(r*.16)} ${n(r*.32)} ${n(r*.32)} 0z`,'#c75a6a',1);
  else if(S.lazy)o+=L(`M${n(x)} ${n(mouthY-r*.06)}v${n(r*.08)}M${n(x-r*.17)} ${n(mouthY+r*.09)}q${n(r*.17)} ${n(-r*.13)} ${n(r*.34)} 0`,OL,1.1);
  else o+=L(`M${n(x-r*.24)} ${n(mouthY)}q${n(r*.12)} ${n(r*.14)} ${n(r*.24)} 0q${n(r*.12)} ${n(r*.14)} ${n(r*.24)} 0`,OL,1.1);
  if(S.smile&&!happy)o+=Pa(`M${n(x-r*.08)} ${n(mouthY+r*.05)}q${n(r*.08)} ${n(r*.2)} ${n(r*.16)} 0z`,TONGUE,0);
  // Eyes.
  const ex=r*(S.muzzle==='flatcat'?.4:.42),ey=y-r*(S.muzzle==='flatcat'?.0:.04),er=r*(S.head>1.08?.21:.18)*(S.k==='cat'?1.08:1);
  if(blink==='sleep')o+=L(`M${n(x-ex-er)} ${n(ey)}q${n(er)} ${n(er*.9)} ${n(er*2)} 0M${n(x+ex-er)} ${n(ey)}q${n(er)} ${n(er*.9)} ${n(er*2)} 0`,OL,1.4);
  else if(S.lazy)o+=lazyEyes(K,x,ex,ey,er*1.12,happy);
  else if(happy)o+=L(`M${n(x-ex-er)} ${n(ey+er*.3)}q${n(er)} ${n(-er*1.5)} ${n(er*2)} 0M${n(x+ex-er)} ${n(ey+er*.3)}q${n(er)} ${n(-er*1.5)} ${n(er*2)} 0`,OL,1.6);
  else{const iris=K.e&&K.e!==EYE?K.e:null,dark=lum(S.face==='mask'?K.l:K.b)<.3;
    for(const sx of [-1,1]){const cx=x+sx*ex;
      o+=iris?E(cx,ey,er,er*1.1,iris,dark?0:1.1,dark?' stroke="#fff3df" stroke-width="1"':'')+E(cx,ey+er*.1,er*.4,er*.66,EYE,0):E(cx,ey,er,er*1.12,EYE,0,dark?' stroke="#fff3df" stroke-width="1.1"':'');
      o+=C(cx+er*.35,ey-er*.4,er*.36,'#fff',0)+C(cx-er*.35,ey+er*.4,er*.16,'#fff',0,' opacity=".8"');}}
  o+=blush(x-r*.68,y+r*.32,r/12)+blush(x+r*.68,y+r*.32,r/12);
  return o;
}
/** 😼 Mai's eyes: round amber irises, the upper lids half down; `awake` (happy): wide open (the photos). */
function lazyEyes(K,x,ex,ey,er,awake){
  let o='';const ry=er*1.06,iris=K.e&&K.e!==EYE?K.e:'#d9c24e';
  for(const sx of [-1,1]){const cx=x+sx*ex;
    o+=E(cx,ey,er,ry,iris,1.1)+E(cx,ey+er*.08,er*.42,er*.7,EYE,0);
    if(awake){o+=C(cx+er*.36,ey-er*.38,er*.34,'#fff',0)+C(cx-er*.34,ey+er*.4,er*.15,'#fff',0,' opacity=".8"');continue;}
    // the lid: the top of the eye cut by a chord, drooping a little to the outer corner (sleepy, unimpressed)
    const yo=ey-ry*.1,yi=ey-ry*.32,R=er+.8,RY=ry+.8,at=yy=>R*Math.sqrt(Math.max(0,1-((yy-ey)/RY)**2));
    const xo=cx+sx*at(yo),xi=cx-sx*at(yi),[x1,y1,x2,y2]=sx<0?[xo,yo,xi,yi]:[xi,yi,xo,yo];
    o+=Pa(`M${n(x1)} ${n(y1)}A${n(R)} ${n(RY)} 0 0 1 ${n(x2)} ${n(y2)}z`,K.b,0)+L(`M${n(x1)} ${n(y1)}L${n(x2)} ${n(y2)}`,OL,1.3)
      +C(cx+er*.34,ey+er*.12,er*.2,'#fff',0,' opacity=".9"');}
  return o;
}
function ruff(S,K,x,y,r){
  if(S.fluff!=='ruff')return '';
  const c=S.face==='points'||S.face==='mask'?K.l:K.b,pts=[];const N=9;
  for(let i=0;i<N;i++){const a=Math.PI*(-.08+i/(N-1)*1.16);pts.push([x+Math.cos(a)*r*1.06,y+r*.2+Math.sin(a)*r*.82]);}
  return pts.map(([a,b])=>C(a,b,r*.36,c,1.4)).join('')+pts.map(([a,b])=>C(a,b,r*.36-.75,c,0)).join('');
}
function mane(S,K,x,y,r,front){   // ✨ a rainbow (kỳ lân một sừng) or flame (kỳ lân) mane: behind the head, a forelock in front
  if(!S.mane)return '';const fl=S.mane==='flame',col=i=>fl?[K.m,'#ffb648',K.m,'#ffd36b'][i%4]:RB[i%6];
  if(front)return [[-.32,-.9,.24],[0,-1.02,.27],[.3,-.92,.22]].map(([a,b,c],i)=>C(x+a*r,y+b*r,c*r,col(i+1),1.1)).join('');
  const out=[];for(let i=0;i<7;i++){const a=Math.PI*(1.02+i*.13);out.push(C(x+Math.cos(a)*r*1.02-r*.08,y+Math.sin(a)*r*.98+r*.1,r*(fl?.34:.31),col(i),1.3));}
  for(let i=0;i<3;i++)out.push(C(x-r*(1.05+i*.12),y+r*(.25+i*.32),r*.3,col(i+3),1.3));
  return out.join('');
}
function horn(S,K,x,y,r){   // ✨ one spiral horn, a qilin's antlers, a dragon's horns, a triceratops' three
  const gold='#ffe08a',ivory='#fff4dc';
  switch(S.horn){
    case'uni':return Pa(`M${n(x-r*.16)} ${n(y-r*.78)}L${n(x)} ${n(y-r*1.78)}L${n(x+r*.16)} ${n(y-r*.78)}Z`,gold,1.3)+L(`M${n(x-r*.12)} ${n(y-r*.98)}l${n(r*.22)} ${n(-r*.08)}M${n(x-r*.09)} ${n(y-r*1.22)}l${n(r*.17)} ${n(-r*.07)}M${n(x-r*.05)} ${n(y-r*1.45)}l${n(r*.1)} ${n(-r*.05)}`,'#d9a531',1)+star(x+r*.3,y-r*1.6,r*.12,'#fff');
    case'antler':return [-1,1].map(sx=>L(`M${n(x+sx*r*.32)} ${n(y-r*.8)}q${n(sx*r*.1)} ${n(-r*.5)} ${n(sx*r*.42)} ${n(-r*.82)}M${n(x+sx*r*.42)} ${n(y-r*1.12)}l${n(sx*r*.3)} ${n(-r*.08)}M${n(x+sx*r*.5)} ${n(y-r*1.38)}l${n(-sx*r*.06)} ${n(-r*.22)}`,OL,4.2)+L(`M${n(x+sx*r*.32)} ${n(y-r*.8)}q${n(sx*r*.1)} ${n(-r*.5)} ${n(sx*r*.42)} ${n(-r*.82)}M${n(x+sx*r*.42)} ${n(y-r*1.12)}l${n(sx*r*.3)} ${n(-r*.08)}M${n(x+sx*r*.5)} ${n(y-r*1.38)}l${n(-sx*r*.06)} ${n(-r*.22)}`,gold,2.4)).join('');
    case'dragon':return [-1,1].map(sx=>Pa(`M${n(x+sx*r*.3)} ${n(y-r*.82)}q${n(sx*r*.12)} ${n(-r*.48)} ${n(sx*r*.5)} ${n(-r*.62)}q${n(-sx*r*.16)} ${n(r*.24)} ${n(-sx*r*.22)} ${n(r*.6)}z`,ivory,1.2)).join('');
    case'trice':return [-1,1].map(sx=>Pa(`M${n(x+sx*r*.42)} ${n(y-r*.62)}q${n(sx*r*.02)} ${n(-r*.42)} ${n(sx*r*.2)} ${n(-r*.72)}q${n(sx*r*.04)} ${n(r*.36)} ${n(sx*r*.06)} ${n(r*.66)}z`,ivory,1.2)).join('')
      +Pa(`M${n(x-r*.12)} ${n(y+r*.08)}q${n(r*.1)} ${n(-r*.36)} ${n(r*.12)} ${n(-r*.5)}q${n(r*.06)} ${n(r*.2)} ${n(r*.14)} ${n(r*.5)}z`,ivory,1.1);
  }
  return '';
}
function frill(S,K,x,y,r){   // the triceratops' fan behind the head
  if(!S.frill)return '';
  return E(x,y-r*.25,r*1.62,r*1.28,K.m,1.6)+[0,1,2,3,4,5,6].map(i=>{const a=Math.PI*(1.08+i*.14);return C(x+Math.cos(a)*r*1.38,y-r*.25+Math.sin(a)*r*1.06,r*.13,K.l,0);}).join('');
}
function head(S,K,x,y,r,o={}){
  const mood=o.mood||'',pos=S.chubby?1.2:S.k==='cat'?1.12:1.06,ry=S.chubby?.9:.95;
  let s=frill(S,K,x,y,r)+mane(S,K,x,y,r,false)+ruff(S,K,x,y,r)+ears(S,K,x,y,r,false);
  if(S.fluff==='curly')s+=[[-.6,-.95,.42],[0,-1.12,.5],[.6,-.95,.42]].map(([a,b,c])=>C(x+a*r,y+b*r,c*r,K.b,1.4)).join('');
  const headFill=S.face==='mask'||S.face==='blaze'&&false?K.l:(S.face==='calico'||S.face==='calico2'&&K.name==='Tam thể'?K.b:K.b);
  s+=E(x,y,r*pos,r*ry,S.face==='mask'?K.l:headFill,1.6);
  if(S.chubby)s+=E(x-r*.78,y+r*.38,r*.4,r*.28,headFill,0)+E(x+r*.78,y+r*.38,r*.4,r*.28,headFill,0);
  if(S.scales)s+=[[-.55,-.45],[.55,-.45],[-.75,0],[.75,0]].map(([a,b])=>E(x+a*r,y+b*r,r*.12,r*.08,K.m,0,' opacity=".55"')).join('');
  s+=face(S,K,x,y,r,mood,o.blink)+ears(S,K,x,y,r,true)+mane(S,K,x,y,r,true)+horn(S,K,x,y,r);
  if(o.acc?.eye&&o.blink!=='sleep')s+=eyeX(o.acc.eye,x,y,r);
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
  const it=wd(id);return it?hatX(it,x,y,r):'';
}
/** The collar: a worn neck piece, else a breed's own (Mai: a thin yellow band with a little silver ring). */
function collarOf(S,o,x,y,w){
  if(o.acc?.neck||!S.collar)return collar(o.acc?.neck,x,y,w);
  return Pa(`M${n(x-w)} ${n(y-1)}q${n(w)} ${n(3.8)} ${n(w*2)} 0v2.1q${n(-w)} ${n(3.8)} ${n(-w*2)} 0z`,S.collar,.9)
    +C(x+w*.18,y+4.3,1.55,'none',0,' stroke="#8f959e" stroke-width="1.5"')+C(x+w*.18,y+4.3,1.55,'none',0,' stroke="#e8ecf1" stroke-width=".7"');
}
function collar(id,x,y,w){
  if(!id)return '';const c={vong_chuong:'#e05a4f',vong_da:'#8a5a3a',vong_ngoc:'#f7f1ea',vong_vang:'#e7b93e'}[id];if(!c){const it=wd(id);return it?neckX(it,x,y,w):'';}
  let s=Pa(`M${n(x-w)} ${n(y-1.5)}q${n(w)} ${n(4.5)} ${n(w*2)} 0v3q${n(-w)} ${n(4.5)} ${n(-w*2)} 0z`,c,1.1);
  if(id==='vong_ngoc')s=Array.from({length:7},(_,i)=>{const t=i/6,px=x-w+t*2*w,py=y+Math.sin(t*Math.PI)*2.4;return C(px,py,1.6,'#fbf7f0',.8);}).join('');
  if(id==='vong_chuong')s+=C(x,y+4.4,2.4,'#f2c14e',1)+L(`M${n(x-1.2)} ${n(y+4.4)}h2.4`,OL,.7);
  if(id==='vong_da')s+=R(x-2,y+2.4,4,3.6,'#f2c14e',1,.9);
  if(id==='vong_vang')s+=Pa(`M${n(x)} ${n(y+2)}l2.4 2.6l-2.4 2.6l-2.4-2.6z`,'#f7d36b',1);
  return s;
}
/** Clothes over the torso. sit: (cx, top y, half width, height); walk: the body ellipse (cx, cy, rx, ry). */
function coat(id,mode,a,b,c,d){
  const col={ao_len:'#e58b7a',ao_mua:'#f6cf45',ao_vn:'#d8392f',ao_khung_long:'#79b86b',ao_dai:'#d94f6e',vay_cong_chua:'#c8a6ef'}[id];if(!col){const it=wd(id);return it?coatX(it,mode,a,b,c,d):'';}
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
    case'nha_go':return Pa(`M${n(-w*.62)} 0v-28l${n(w*.62)} -16l${n(w*.62)} 16v28z`,'#d9a066',1.5)+Pa(`M${n(-w*.7)} -27l${n(w*.7)} -19l${n(w*.7)} 19`,'none',3)
      +Pa(`M${n(-w*.34)} 0v-17q${n(w*.34)} -12 ${n(w*.68)} 0v17z`,'#7a5236',1.2)+R(-w*.08,-38,w*.16,6,'#fff6e6',1,1)+E(0,-3,w*.4,4,'#f2b8c6',1);
    case'lau_dai':return R(-w*.72,-34,w*.36,34,'#e6dcf8',0,1.5)+R(w*.36,-34,w*.36,34,'#e6dcf8',0,1.5)+R(-w*.42,-28,w*.84,28,'#cdb8f0',2,1.5)
      +Pa(`M${n(-w*.76)} -34l${n(w*.22)} -14l${n(w*.22)} 14zM${n(w*.32)} -34l${n(w*.22)} -14l${n(w*.22)} 14z`,'#ef7f8f',1.3)+Pa(`M${n(-w*.26)} 0v-15q${n(w*.26)} -10 ${n(w*.52)} 0v15z`,'#8f73c9',1.2)+star(0,-22,3,'#f2c14e')+E(0,-3,w*.36,3.6,'#f2b8c6',1);
  }
  const it=wd(id);return it?bedX(it,w):'';
}

/* ---------------------------------------------------------------- 👗 the wardrobe (game/pet_wardrobe_content.py, owner 19/10)
 * Each piece names an `art` style painted in its `color` (and `c2`); the first nineteen keep their own drawings above.
 * lookup() registers the catalogue's pieces (content.journey.pets.wardrobe.items). */
const WD=new Map();let WSRC=null;
function register(cat){const w=cat?.wardrobe?.items;if(!w||w===WSRC)return;WSRC=w;WD.clear();for(const it of w)WD.set(it.id,it);}
const wd=id=>WD.get(id)||null;
const hasWings=acc=>{const it=wd(acc?.back);return !!(it&&/^w_/.test(it.art||''));};
const dk=(h,f=.72)=>{const v=parseInt(String(h).slice(1),16);if(isNaN(v)||String(h).length!==7)return OL;const c=x=>Math.max(0,Math.min(255,Math.round(x*f))).toString(16).padStart(2,'0');return '#'+c(v>>16)+c((v>>8)&255)+c(v&255);};
function flower(x,y,s,c,c2){return [0,1,2,3,4].map(i=>{const a=i*Math.PI*2/5;return C(x+Math.cos(a)*s*.62,y+Math.sin(a)*s*.62,s*.5,c,.6);}).join('')+C(x,y,s*.38,c2||'#ffe27a',0);}
function hatX(it,x,y,r){
  const c=it.color,c2=it.c2||'#fff';
  switch(it.art){
    case'beanie':return Pa(`M${n(x-r*.98)} ${n(y-r*.42)}q${n(r*.08)} ${n(-r*.9)} ${n(r*.98)} ${n(-r*.92)}q${n(r*.9)} ${n(.02)} ${n(r*.98)} ${n(r*.92)}z`,c,1.3)
      +[-1,1].map(sx=>Pa(`M${n(x+sx*r*.95)} ${n(y-r*.55)}L${n(x+sx*r*.75)} ${n(y-r*1.55)}L${n(x+sx*r*.25)} ${n(y-r*1.1)}z`,c,1.2)+Pa(`M${n(x+sx*r*.8)} ${n(y-r*.75)}L${n(x+sx*r*.72)} ${n(y-r*1.3)}L${n(x+sx*r*.42)} ${n(y-r*1.05)}z`,c2,0)).join('')
      +L(`M${n(x-r*.95)} ${n(y-r*.5)}q${n(r*.95)} ${n(r*.2)} ${n(r*1.9)} 0`,dk(c),1.6);
    case'party':return Pa(`M${n(x-r*.42)} ${n(y-r*.82)}L${n(x+r*.12)} ${n(y-r*2)}L${n(x+r*.55)} ${n(y-r*.72)}z`,c,1.2)+L(`M${n(x-r*.2)} ${n(y-r*1.2)}l${n(r*.5)} ${n(.1)}M${n(x-.02*r)} ${n(y-r*1.55)}l${n(r*.3)} 0`,c2,1.4)+C(x+r*.12,y-r*2.05,r*.18,c2,1);
    case'sailor':return E(x,y-r*.86,r*.82,r*.26,'#fff',1.2)+Pa(`M${n(x-r*.62)} ${n(y-r*.9)}q${n(r*.62)} ${n(-r*.62)} ${n(r*1.24)} 0z`,'#fff',1.2)+L(`M${n(x-r*.66)} ${n(y-r*.92)}q${n(r*.66)} ${n(r*.12)} ${n(r*1.32)} 0`,c2,1.8)+C(x,y-r*1.15,r*.1,c2,0);
    case'flower':return flower(x+r*.55,y-r*.85,r*.32,c,c2)+flower(x+r*.05,y-r*1.02,r*.22,'#fff',c2)+flower(x+r*.95,y-r*.48,r*.2,c,c2);
    case'witch':return E(x,y-r*.82,r*1.25,r*.3,c,1.3)+Pa(`M${n(x-r*.62)} ${n(y-r*.88)}q${n(r*.2)} ${n(-r*.9)} ${n(r*.75)} ${n(-r*1.5)}q${n(r*.2)} ${n(-r*.1)} ${n(r*.18)} ${n(r*.25)}q${n(-r*.22)} ${n(r*.5)} ${n(r*.31)} ${n(r*1.25)}z`,c,1.3)+L(`M${n(x-r*.58)} ${n(y-r*1.02)}q${n(r*.6)} ${n(r*.12)} ${n(r*1.2)} 0`,c2,1.6)+star(x+r*.1,y-r*1.55,r*.16,c2);
    case'veil':return Pa(`M${n(x-r*.75)} ${n(y-r*.7)}q${n(-r*.6)} ${n(r*1.2)} ${n(-r*.5)} ${n(r*2)}h${n(r*2.5)}q${n(r*.1)} ${n(-r*.8)} ${n(-r*.5)} ${n(-r*2)}z`,c,.8,' opacity=".55"')+[-.5,0,.5].map((t,i)=>flower(x+t*r,y-r*(.92+(i===1?.1:0)),r*.2,c2,'#ffe27a')).join('');
    case'cowboy':return E(x,y-r*.82,r*1.3,r*.3,c,1.3)+Pa(`M${n(x-r*.62)} ${n(y-r*.86)}q${n(-r*.05)} ${n(-r*.8)} ${n(r*.3)} ${n(-r*.75)}q${n(r*.32)} ${n(-r*.2)} ${n(r*.64)} 0q${n(r*.35)} ${n(-r*.05)} ${n(r*.3)} ${n(r*.75)}z`,c,1.3)+L(`M${n(x-r*.6)} ${n(y-r*1)}q${n(r*.6)} ${n(r*.12)} ${n(r*1.2)} 0`,c2,1.6);
    case'turban':return Pa(`M${n(x-r*1.02)} ${n(y-r*.45)}q${n(-r*.05)} ${n(-r*.95)} ${n(r*1.02)} ${n(-r*.98)}q${n(r*1.07)} ${n(.03)} ${n(r*1.02)} ${n(r*.98)}q${n(-r*1.02)} ${n(-r*.3)} ${n(-r*2.04)} 0z`,c,1.3)+L(`M${n(x-r*.9)} ${n(y-r*.75)}q${n(r*.9)} ${n(-r*.3)} ${n(r*1.8)} 0M${n(x-r*.75)} ${n(y-r*1.05)}q${n(r*.75)} ${n(-r*.25)} ${n(r*1.5)} 0`,c2,.9,' opacity=".8"');
    case'crown':return Pa(`M${n(x-r*.7)} ${n(y-r*.82)}l${n(-r*.1)} ${n(-r*.7)}l${n(r*.35)} ${n(r*.3)}l${n(r*.45)} ${n(-r*.55)}l${n(r*.45)} ${n(r*.55)}l${n(r*.35)} ${n(-r*.3)}l${n(-r*.1)} ${n(r*.7)}z`,'#e8eef5',1.2)
      +gem(x,y-r*1.12,r*.2,c2)+gem(x-r*.45,y-r*1.02,r*.13,'#ff9db0')+gem(x+r*.45,y-r*1.02,r*.13,'#9fdcff')+star(x,y-r*1.55,r*.12,'#fff');
    case'beret':return E(x-r*.12,y-r*.88,r*.95,r*.36,c,1.3,' transform="rotate(-12 '+n(x)+' '+n(y-r*.88)+')"')+L(`M${n(x-r*.2)} ${n(y-r*1.24)}l${n(r*.04)} ${n(-r*.2)}`,dk(c),1.6);
    case'bunny':return [-1,1].map(sx=>E(x+sx*r*.42,y-r*1.55,r*.24,r*.7,c,1.3,` transform="rotate(${sx*12} ${n(x+sx*r*.42)} ${n(y-r*1.1)})"`)+E(x+sx*r*.42,y-r*1.5,r*.11,r*.5,c2,0,` transform="rotate(${sx*12} ${n(x+sx*r*.42)} ${n(y-r*1.1)})"`)).join('')
      +L(`M${n(x-r*.85)} ${n(y-r*.62)}q${n(r*.85)} ${n(-r*.55)} ${n(r*1.7)} 0`,c,1.8);
    case'helmet':return Pa(`M${n(x-r*1.04)} ${n(y-r*.2)}q${n(-r*.02)} ${n(-r*1.1)} ${n(r*1.04)} ${n(-r*1.12)}q${n(r*1.06)} ${n(.02)} ${n(r*1.04)} ${n(r*1.12)}z`,c,1.3)+Pa(`M${n(x-r*.75)} ${n(y-r*.3)}q${n(r*.75)} ${n(-r*.22)} ${n(r*1.5)} 0l${n(-r*.12)} ${n(r*.22)}q${n(-r*.63)} ${n(-r*.12)} ${n(-r*1.26)} 0z`,c2,1,' opacity=".75"')+L(`M${n(x)} ${n(y-r*1.3)}v${n(r*.4)}`,'#fff',1.4,' opacity=".7"');
    case'halo':return `<g class="pet-halo">${E(x,y-r*1.35,r*.85,r*.24,'none',0,` stroke="${c}" stroke-width="2.6"`)+E(x,y-r*1.35,r*.85,r*.24,'none',0,` stroke="${c2}" stroke-width=".9"`)}</g>`;
  }
  return '';
}
function eyeX(id,x,y,r){
  const it=wd(id);if(!it)return '';const c=it.color,c2=it.c2||'#fff',ex=r*.42,ey=y-r*.04,er=r*.27,P=[-1,1];
  const bridge=L(`M${n(x-ex+er)} ${n(ey)}q${n(ex-er)} ${n(-er*.5)} ${n((ex-er)*2)} 0`,c,1.1);
  switch(it.art){
    case'round':return P.map(sx=>C(x+sx*ex,ey,er,'#fff',0,` fill-opacity=".18" stroke="${c}" stroke-width="1.3"`)).join('')+bridge;
    case'gemglass':return P.map(sx=>C(x+sx*ex,ey,er,'#dff4ff',0,` fill-opacity=".35" stroke="#e8eef5" stroke-width="1.4"`)+gem(x+sx*(ex+er*.9),ey-er*.7,r*.1,c)).join('')+bridge;
    case'heart':return P.map(sx=>heart(x+sx*ex,ey-er*.5,er*.95,c).replace('<path ','<path opacity=".82" ')).join('')+bridge;
    case'shades':return P.map(sx=>R(x+sx*ex-er*1.1,ey-er*.7,er*2.2,er*1.5,c,er*.5,1)).join('')+L(`M${n(x-ex+er)} ${n(ey-er*.4)}h${n((ex-er)*2)}`,c,1.4)+P.map(sx=>L(`M${n(x+sx*ex-er*.6)} ${n(ey-er*.3)}l${n(er*.4)} ${n(-er*.2)}`,'#fff',.8,' opacity=".7"')).join('');
    case'star':return P.map(sx=>star(x+sx*ex,ey,er*1.25,c)).join('')+P.map(sx=>C(x+sx*ex,ey,er*.42,'#fff',0,' opacity=".5"')).join('');
    case'mask':return E(x,ey,ex+er*1.75,er*1.2,c,1)+P.map(sx=>E(x+sx*ex,ey,er*.62,er*.5,'#2b1f3a',0)).join('')+star(x,ey-er*1.05,er*.42,c2);
    case'goggles':return L(`M${n(x-r*1.02)} ${n(ey)}h${n(r*2.04)}`,dk(c),1.8)+P.map(sx=>C(x+sx*ex,ey,er*1.12,c,1.3,' fill-opacity=".45"')+C(x+sx*ex-er*.35,ey-er*.35,er*.25,'#fff',0,' opacity=".8"')).join('');
    case'monocle':return C(x+ex,ey,er*1.05,'#fff',0,` fill-opacity=".2" stroke="${c}" stroke-width="1.4"`)+L(`M${n(x+ex)} ${n(ey+er*1.05)}q${n(r*.2)} ${n(r*.5)} ${n(r*.4)} ${n(r*.9)}`,c,.8,' stroke-dasharray="1 1"');
  }
  return '';
}
function neckX(it,x,y,w){
  const c=it.color,c2=it.c2||'#fff';
  switch(it.art){
    case'scarf':return Pa(`M${n(x-w)} ${n(y-2)}q${n(w)} ${n(5.5)} ${n(w*2)} 0v4q${n(-w)} ${n(5.5)} ${n(-w*2)} 0z`,c,1.1)+Pa(`M${n(x+w*.45)} ${n(y+3)}l${n(w*.25)} 8l${n(-w*.35)} 1l${n(-w*.1)} -8z`,c,1)
      +L(`M${n(x-w*.6)} ${n(y)}v3M${n(x)} ${n(y+1)}v3.4M${n(x+w*.6)} ${n(y)}v3`,c2,1.2,' opacity=".9"');
    case'bowtie':return Pa(`M${n(x)} ${n(y+2)}l-5 -3.4v7z`,c,1)+Pa(`M${n(x)} ${n(y+2)}l5 -3.4v7z`,c,1)+C(x,y+2,1.6,c2,.8);
    case'lei':return Array.from({length:6},(_,i)=>{const t=i/5,px=x-w+t*2*w,py=y+Math.sin(t*Math.PI)*2.8;return flower(px,py,2.4,i%2?c:'#fff',c2);}).join('');
    case'beads':return Array.from({length:8},(_,i)=>{const t=i/7,px=x-w+t*2*w,py=y+Math.sin(t*Math.PI)*2.6;return C(px,py,1.6,i%2?c2:c,.7);}).join('');
    case'gems':return Array.from({length:7},(_,i)=>{const t=i/6,px=x-w+t*2*w,py=y+Math.sin(t*Math.PI)*2.4;return C(px,py,1.3,'#f4f8ff',.6);}).join('')+gem(x,y+5.4,3,c)+star(x+3.5,y+3,1.2,'#fff');
    case'pendant':return L(`M${n(x-w)} ${n(y-1)}q${n(w)} ${n(5)} ${n(w*2)} 0`,c2,1)+(it.id.includes('tim')?heart(x,y+4,2.6,c):Pa(`M${n(x+2.4)} ${n(y+2)}a3.4 3.4 0 1 0 0 6.4a2.6 2.6 0 1 1 0 -6.4z`,c,.8));
  }
  return '';
}
/** Clothes of the wardrobe, over the torso (sit: cx, top, half width, height; walk: the body ellipse). */
function coatX(it,mode,a,b,c,d){
  const col=it.color,c2=it.c2||'#fff',art=it.art;if(art==='cape')return '';
  let s='';
  if(mode==='sit'){const [x,y,w,h]=[a,b,c,d],base=(ex='')=>Pa(`M${n(x-w*.82)} ${n(y)}q${n(w*.82)} ${n(-3)} ${n(w*1.64)} 0l${n(w*.2)} ${n(h*.78)}q${n(-w*1.02)} ${n(h*.22)} ${n(-w*2.04)} 0z`,col,1.3,ex);
    switch(art){
      case'hoodie':s=base()+R(x-w*.45,y+h*.42,w*.9,h*.26,dk(col,.9),3,1)+L(`M${n(x-w*.2)} ${n(y+1)}v${n(h*.25)}M${n(x+w*.2)} ${n(y+1)}v${n(h*.25)}`,c2,1.1);break;
      case'bib':s=Pa(`M${n(x-w*.55)} ${n(y)}q${n(w*.55)} ${n(-2)} ${n(w*1.1)} 0l${n(w*.05)} ${n(h*.7)}q${n(-w*.6)} ${n(h*.25)} ${n(-w*1.2)} 0z`,col,1.2)+[[-.25,.25],[.2,.2],[0,.45],[-.2,.6],[.25,.55]].map(([p,q])=>E(x+p*w,y+q*h,1,1.3,c2,0)).join('');break;
      case'stripes':s=base()+[.22,.44,.66].map(t=>L(`M${n(x-w*(.86+t*.2))} ${n(y+h*t)}h${n(w*(1.72+t*.4))}`,c2,2.2,' opacity=".95"')).join('');break;
      case'tutu':s=base()+Array.from({length:7},(_,i)=>E(x-w*1.15+i*w*.38,y+h*.78,w*.3,h*.16,c2,1)).join('');break;
      case'space':s=base()+R(x-w*.9,y+h*.5,w*1.8,h*.1,'#9aa0a6',1,.8)+R(x+w*.15,y+h*.12,w*.42,h*.2,c2,1,.8)+C(x-w*.35,y+h*.25,1.3,'#5aa9e6',0);break;
      case'robe':s=base()+L(`M${n(x-w*.5)} ${n(y)}l${n(w*.5)} ${n(h*.4)}l${n(w*.5)} ${n(-h*.4)}`,c2,1.6)+R(x-w*.95,y+h*.5,w*1.9,h*.14,c2,1,.9);break;
      case'aodai':s=Pa(`M${n(x-w*.78)} ${n(y)}q${n(w*.78)} ${n(-3)} ${n(w*1.56)} 0l${n(w*.36)} ${n(h*1.05)}h${n(-w*.62)}l${n(-w*.24)} ${n(-h*.3)}l${n(-w*.24)} ${n(h*.3)}h${n(-w*.62)}z`,col,1.3)+flower(x+w*.3,y+h*.32,1.6,c2,'#fff')+flower(x-w*.35,y+h*.6,1.4,c2,'#fff');break;
      case'pumpkin':s=Pa(`M${n(x-w*.95)} ${n(y+h*.1)}q${n(w*.95)} ${n(-h*.3)} ${n(w*1.9)} 0q${n(w*.25)} ${n(h*.55)} 0 ${n(h*.75)}q${n(-w*.95)} ${n(h*.25)} ${n(-w*1.9)} 0q${n(-w*.25)} ${n(-h*.2)} 0 ${n(-h*.75)}z`,col,1.3)+L(`M${n(x-w*.35)} ${n(y)}q${n(-w*.15)} ${n(h*.4)} 0 ${n(h*.8)}M${n(x+w*.35)} ${n(y)}q${n(w*.15)} ${n(h*.4)} 0 ${n(h*.8)}`,dk(col),1.1)+Pa(`M${n(x-1)} ${n(y-1)}l1 -3l2 .5l-1 3z`,c2,.8);break;
      case'tux':s=base()+Pa(`M${n(x-w*.3)} ${n(y-1)}l${n(w*.3)} ${n(h*.75)}l${n(w*.3)} ${n(-h*.75)}z`,c2,.9)+Pa(`M${n(x)} ${n(y+2)}l-3 -2v4zM${n(x)} ${n(y+2)}l3 -2v4z`,'#2b2b33',.6)+C(x+w*.55,y+h*.25,1.6,'#fff',.6);break;
      case'gown':s=Pa(`M${n(x-w*.7)} ${n(y)}q${n(w*.7)} ${n(-3)} ${n(w*1.4)} 0l${n(w*.55)} ${n(h*1)}q${n(-w*1.25)} ${n(h*.25)} ${n(-w*2.5)} 0z`,col,1.3)+Array.from({length:6},(_,i)=>C(x-w*1.15+i*w*.46,y+h*.98,w*.2,c2,.8)).join('')+heart(x,y+h*.25,2,c2);break;
      case'fluffy':s=base()+Array.from({length:9},(_,i)=>C(x-w*.8+(i%3)*w*.8,y+h*(.15+Math.floor(i/3)*.27),w*.3,col,1)).join('');break;
      case'shirt':s=base()+[[-.5,.25],[.35,.2],[0,.5],[-.45,.65],[.5,.6]].map(([p,q])=>it.id==='pijama_sao'?star(x+p*w,y+q*h,1.8,c2):flower(x+p*w,y+q*h,1.6,c2,'#fff')).join('');break;
      case'puffer':s=base()+[.22,.44,.66].map(t=>L(`M${n(x-w*(.86+t*.2))} ${n(y+h*t)}h${n(w*(1.72+t*.4))}`,dk(col),1.1)).join('')+L(`M${n(x)} ${n(y)}v${n(h*.8)}`,dk(col),1);break;
      default:s=base();
    }
  }else{const [cx,cy,rx,ry]=[a,b,c,d];
    s=Pa(`M${n(cx-rx*.55)} ${n(cy-ry*.98)}q${n(rx*.55)} ${n(-ry*.3)} ${n(rx*1.1)} 0q${n(rx*.12)} ${n(ry*.95)} ${n(-rx*.02)} ${n(ry*1.55)}h${n(-rx*1.06)}q${n(-rx*.14)} ${n(-ry*.6)} ${n(-rx*.02)} ${n(-ry*1.55)}z`,art==='bib'?'none':col,art==='bib'?0:1.3);
    if(art==='stripes')s+=[-.4,0,.4].map(t=>L(`M${n(cx-rx*.5)} ${n(cy+ry*t)}h${n(rx*1.06)}`,c2,2)).join('');
    if(art==='tutu'||art==='gown')s+=Array.from({length:5},(_,i)=>C(cx-rx*.6+i*rx*.3,cy+ry*.62,ry*.36,c2,1)).join('');
    if(art==='robe'||art==='space')s+=R(cx-rx*.56,cy+ry*.1,rx*1.1,ry*.3,c2,1,.8);
    if(art==='tux')s+=Pa(`M${n(cx+rx*.3)} ${n(cy-ry*.95)}l${n(rx*.22)} ${n(ry*.9)}l${n(rx*.1)} ${n(-ry*.95)}z`,c2,.8);
    if(art==='shirt'||art==='aodai')s+=[[-.3,-.2],[.2,.3]].map(([p,q])=>it.id==='pijama_sao'?star(cx+p*rx,cy+q*ry,1.8,c2):flower(cx+p*rx,cy+q*ry,1.5,c2,'#fff')).join('');
    if(art==='fluffy')s+=Array.from({length:5},(_,i)=>C(cx-rx*.45+i*rx*.22,cy-ry*.55+(i%2)*ry*.6,ry*.38,col,.9)).join('');
    if(art==='pumpkin'||art==='puffer')s+=L(`M${n(cx-rx*.2)} ${n(cy-ry*.9)}v${n(ry*1.5)}M${n(cx+rx*.2)} ${n(cy-ry*.9)}v${n(ry*1.5)}`,dk(col),1);
    if(art==='bib')s=E(cx+rx*.62,cy+ry*.1,rx*.28,ry*.62,col,1.1)+E(cx+rx*.62,cy+ry*.1,1,1.2,c2,0);
    if(art==='hoodie')s+=R(cx-rx*.25,cy,rx*.5,ry*.5,dk(col,.9),2,.9);
  }
  return s;
}
/** 🪽 One wing (pointing left from its root at 0,0; flip -1 points right), by style. */
function wingX(it,flip,s){
  const c=it.color,c2=it.c2||'#fff',ed=dk(c,.62);let g='';
  switch(it.art){
    case'w_feather':case'w_galaxy':case'w_rainbow':{
      g+=PRIM.map(([a,l],i)=>feather(l*.62,a,4.6,it.art==='w_rainbow'?RB[i%6]:c,it.art==='w_rainbow'?dk(RB[i%6]):ed)).join('');
      g+=PRIM.slice(1,8).map(([a,l],i)=>feather(l*.42,a+5,5.2,it.art==='w_rainbow'?RB[(i+2)%6]:c2,ed)).join('');
      g+=[[196,9],[214,10.5],[232,10],[250,8]].map(([a,l])=>feather(l,a,5.4,it.art==='w_galaxy'?c:'#fff',ed)).join('');
      if(it.art==='w_galaxy')g+=[[-12,-14],[-20,-8],[-8,-22],[-24,-18],[-16,-26]].map(([x,y],i)=>i%2?C(x,y,.8,'#fff',0):star(x,y,1.5,'#fff')).join('');
      break;}
    case'w_peacock':g+=[150,165,180,195,210,225,240].map((a,i)=>feather(32+(i%2)*6,a,4.4,c,ed)).join('')+[150,165,180,195,210,225,240].map((a,i)=>{const r=a*Math.PI/180,l=30+(i%2)*6;return E(Math.cos(r)*l,Math.sin(r)*l,2.6,3.2,c2,.6)+C(Math.cos(r)*l,Math.sin(r)*l,1.3,'#2b1f5a',0)+C(Math.cos(r)*l,Math.sin(r)*l,.5,'#ffd24a',0);}).join('');break;
    case'w_butterfly':g+=Pa('M0 0C-8 -26 -34 -32 -33 -14C-32 -3 -14 -1 0 0z',c,1)+Pa('M0 0C-5 13 -23 19 -23 9C-22 2 -9 0 0 0z',c,1)+C(-22,-16,3.4,c2,0)+C(-14,-22,1.8,c2,0)+C(-15,6,2.2,c2,0)+C(-27,-10,1.6,'#fff',0,' opacity=".8"');break;
    case'w_fairy':g+=E(-15,-11,17,7,c,.8,` transform="rotate(-28 -15 -11)" fill-opacity=".62" stroke="${ed}"`)+E(-12,4,11,5,c,.8,` transform="rotate(18 -12 4)" fill-opacity=".62" stroke="${ed}"`)+L('M0 0L-26 -20M-8 -6L-18 -10M0 0L-20 9',c2,.7,' opacity=".8"')+star(-26,-20,1.6,'#fff');break;
    case'w_dragonfly':g+=E(-17,-6,19,4.2,c,.7,` transform="rotate(-16 -17 -6)" fill-opacity=".6" stroke="${c2}"`)+E(-15,5,16,3.8,c,.7,` transform="rotate(14 -15 5)" fill-opacity=".6" stroke="${c2}"`)+L('M0 0L-33 -10M0 0L-29 9',c2,.6);break;
    case'w_bat':case'w_dragon':g+=Pa('M0 0L-6 -24L-36 -22Q-33 -13 -30 -8Q-24 -12 -20 -5Q-14 -10 -9 -2Z',c,1.1,` stroke="${ed}"`)+L('M-6 -24L-30 -9M-6 -24L-20 -5M-6 -24L-9 -2',c2,.9)+(it.art==='w_dragon'?Pa('M-6 -24l-2 -4l3 1z',c2,.6)+Pa('M-36 -22l-3 -2l3 -1z',c2,.6):'');break;
    case'w_petal':g+=[200,220,240,260,180].map((a,i)=>{const r=a*Math.PI/180,l=18-(i===4?4:0);return E(Math.cos(r)*l*.62,Math.sin(r)*l*.62,l*.62,4.6,c,.9,` transform="rotate(${a} ${n(Math.cos(r)*l*.62)} ${n(Math.sin(r)*l*.62)})"`)+E(Math.cos(r)*l*.5,Math.sin(r)*l*.5,l*.36,2,c2,0,` transform="rotate(${a} ${n(Math.cos(r)*l*.5)} ${n(Math.sin(r)*l*.5)})"`);}).join('');break;
    case'w_crystal':g+=Pa('M0 0L-12 -28L-22 -20Z',c,.8,` fill-opacity=".8" stroke="${c2}"`)+Pa('M0 0L-26 -22L-33 -8Z',c,.8,` fill-opacity=".75" stroke="${c2}"`)+Pa('M0 0L-31 -3L-23 6Z',c,.8,` fill-opacity=".7" stroke="${c2}"`)+L('M-4 -6L-12 -24M-6 -4L-26 -17',c2=== '#fff'?'#fff':'#fff',.7,' opacity=".85"')+star(-20,-22,1.6,'#fff')+star(-30,-6,1.2,'#fff');break;
    case'w_flame':g+=[[-8,-4,16,-70],[-14,-2,18,-48],[-18,2,15,-25]].map(([x,y,h,a])=>`<g transform="rotate(${a} ${x} ${y})">${flame(x,y,h,c,c2)}</g>`).join('');break;
  }
  return `<g transform="scale(${n(flip*s)} ${n(s)})">${g}</g>`;
}
/** What is worn on the back, behind the body (wings, a cape, the bouquet) or in front of it (the float ring). */
function backX(acc,mode,g,inn=null){
  const it=wd(acc?.back)||inn,cape=wd(acc?.body);let behind='',front='';
  if(cape&&cape.art==='cape'){const c=cape.color,c2=cape.c2||'#fff';
    behind+=mode==='sit'?Pa(`M${n(-g.w*.7)} ${n(g.y)}q${n(-g.w*.9)} ${n(g.h*.9)} ${n(-g.w*1.15)} ${n(g.h*1.25)}h${n(g.w*3.7)}q${n(-g.w*.25)} ${n(-g.h*.35)} ${n(-g.w*1.15)} ${n(-g.h*1.25)}z`,c,1.3)
      :Pa(`M${n(g.x+g.rx*.4)} ${n(g.y-g.ry*.95)}q${n(-g.rx*.9)} ${n(-g.ry*.4)} ${n(-g.rx*1.6)} ${n(g.ry*1.1)}q${n(g.rx*.6)} ${n(g.ry*.2)} ${n(g.rx*1.3)} ${n(-g.ry*.2)}z`,c,1.3);
    front+=mode==='sit'?C(0,g.y+1,1.8,c2,.8):'';}
  if(!it)return [behind,front];
  const c=it.color,c2=it.c2||'#fff';
  if(/^w_/.test(it.art)){
    const sz=it.sz||(it.art==='w_peacock'?.66:/^w_(feather|galaxy|rainbow)$/.test(it.art)?1.12:.95),lift=/^w_(feather|galaxy|rainbow|peacock)$/.test(it.art)?-.05:.2;
    behind+=`<g class="pet-wings">`+(mode==='sit'?`<g transform="translate(${n(-g.w*.45)} ${n(g.y+g.h*lift)})">${wingX(it,1,sz)}</g><g transform="translate(${n(g.w*.45)} ${n(g.y+g.h*lift)})">${wingX(it,-1,sz)}</g>`
      :`<g transform="translate(${n(g.x-g.rx*.1)} ${n(g.y-g.ry*.75)}) rotate(14)">${wingX(it,1,sz*.8)}</g><g transform="translate(${n(g.x+g.rx*.15)} ${n(g.y-g.ry*.85)}) rotate(4)">${wingX(it,1,sz*.68)}</g>`)+'</g>';
  }else if(it.art==='pack'){
    behind+=mode==='sit'?R(g.w*.35,g.y-2,g.w*.9,g.h*.8,c,4,1.3)+E(g.w*.8,g.y+g.h*.38,g.w*.18,g.h*.12,'#fff',.8)+C(g.w*.62,g.y+g.h*.2,1.2,OL,0):'';
    if(mode!=='sit')front+=Pa(`M${n(g.x-g.rx*.4)} ${n(g.y-g.ry*1.25)}q${n(g.rx*.4)} ${n(-g.ry*.6)} ${n(g.rx*.8)} 0v${n(g.ry*.9)}h${n(-g.rx*.8)}z`,c,1.2)+Pa(`M${n(g.x+g.rx*.4)} ${n(g.y-g.ry*.8)}l4 -2v4z`,c,1);
  }else if(it.art==='ring'){
    const y=mode==='sit'?g.y+g.h*.75:g.y+g.ry*.2,rx=mode==='sit'?g.w*1.25:g.rx*1.05,ry=mode==='sit'?4.6:4;
    front+=E(0+(mode==='sit'?0:g.x),y,rx,ry,'none',0,` stroke="${c}" stroke-width="5"`)+[-.6,0,.6].map(t=>E((mode==='sit'?0:g.x)+rx*t,y+ry*.9*(1-Math.abs(t)),2.4,1.6,c2,0)).join('');
  }else if(it.art==='bouquet'){
    const x=mode==='sit'?g.w*.75:g.x-g.rx*.3,y=mode==='sit'?g.y-2:g.y-g.ry*1.3;
    behind+=L(`M${n(x)} ${n(y+8)}l-3 -8M${n(x)} ${n(y+8)}l1 -9M${n(x)} ${n(y+8)}l4 -7`,'#4f8a3c',1.4)+flower(x-3,y-1,2.6,c,'#ffe27a')+flower(x+1,y-3,2.6,'#fff',c)+flower(x+4,y,2.4,c,'#ffe27a');
  }
  return [behind,front];
}
/** ✨ Small sparkles by a piece of rank B and up (its rank's colour; SSS a rainbow pair). */
function shine(pts){
  return pts.filter(([,,r])=>r>=2).map(([x,y,r],i)=>r>=6?star(x,y,2.2,RB[i%6])+star(x+4,y-3,1.3,'#fff'):star(x,y,r>=4?2:1.5,RANK_COLOR[r])+(r>=5?star(x+3.5,y+2,1.1,'#fff'):'')).join('');
}
/** 💖 The cute aura (o 1…3: what is worn adds up) and a whole set's effect (st), around the pet. */
function wearFx(o,st){
  let back='',front='';
  if(o>=2)back+=`<ellipse class="pet-glow" cx="0" cy="-24" rx="34" ry="30" fill="#ffd1e6" opacity="${o>=3?.55:.35}"/>`;
  if(o>=1)front+=`<g class="pet-hearts">${heart(-26,-46,2.4,'#ff8fb1')+heart(27,-38,2,'#ffb3c9')}${o>=3?heart(-31,-22,1.7,'#ff6fa3')+heart(30,-58,1.8,'#ff8fb1'):''}</g>`;
  if(o>=3)front+=`<g class="pet-rise">${[[-22,-12],[24,-18],[-14,-60]].map(([x,y])=>C(x,y,2,'#fff',.6,' stroke="#ffb3d1" fill-opacity=".5"')).join('')}</g>`;
  switch(st){
    case'thuy_thu':front+=`<g class="pet-rise">${[[-28,-30,2.6],[30,-26,2],[-20,-52,1.8],[22,-56,2.4],[34,-46,1.4]].map(([x,y,r])=>C(x,y,r,'#e6f6ff',.7,' stroke="#5aa9e6" fill-opacity=".45"')).join('')}</g>`;break;
    case'oct20':front+=`<g class="pet-fall">${[[-26,-56],[18,-62],[30,-36],[-32,-30],[6,-70]].map(([x,y],i)=>E(x,y,2.2,1.3,i%2?'#ff9db0':'#ffc4d2',0,` transform="rotate(${i*40} ${x} ${y})"`)).join('')}</g>`;break;
    case'halloween':{const bat=(x,y)=>Pa(`M${x} ${y}q-3 -3 -7 -1q2 1 2 3q2 -2 5 -1zM${x} ${y}q3 -3 7 -1q-2 1 -2 3q-2 -2 -5 -1z`,'#3d2f4f',0)+C(x,y,1.2,'#3d2f4f',0);
      front+=`<g class="pet-rise">${bat(-28,-50)+bat(26,-60)+bat(32,-34)}</g>`+E(-30,-4,4.6,3.8,'#f08a3c',1)+Pa('M-31.5 -5l1 -1.4l1 1.4zM-28.5 -5l1 -1.4l1 1.4z','#3a2a1c',0)+L('M-30 -8v-2','#4f8a3c',1.2);break;}
    case'cuoi':front+=`<g class="pet-hearts">${heart(-30,-34,2.2,'#ff6f8f')+heart(28,-50,2.4,'#ff9db0')}</g>`+flower(-30,-58,2.6,'#fff','#ffe27a')+flower(32,-24,2.4,'#fff','#ff9db0');break;
    case'hoang_gia':back+=E(0,-.5,36,6,'#c0262d',0,' opacity=".85"')+E(0,-.5,36,6,'none',0,' stroke="#f2c14e" stroke-width="1.2"')+`<ellipse class="pet-glow" cx="0" cy="-26" rx="38" ry="34" fill="#ffe07a" opacity=".35"/>`;
      front+=`<g class="pet-spark">${[[-30,-44],[30,-52],[-34,-18],[34,-22]].map(([x,y])=>star(x,y,2.2,'#ffd24a')).join('')}</g>`;break;
  }
  return [back,front];
}
function bedX(it,w){
  const c=it.color,c2=it.c2||'#fff';
  switch(it.art){
    case'basket':return Pa(`M${n(-w*.62)} -9q${n(w*.62)} 8 ${n(w*1.24)} 0l-3 9h${n(-w*1.24+6)}z`,c,1.5)+L(`M${n(-w*.5)} -5h${n(w)}M${n(-w*.45)} -2h${n(w*.9)}`,dk(c),1)+E(0,-8,w*.5,3.4,c2,1)+flower(-w*.45,-10,2.6,'#ff9db0','#ffe27a')+flower(w*.45,-10,2.6,'#fff','#ff9db0');
    case'pumpkin':return Pa(`M${n(-w*.7)} 0q-4 -20 ${n(w*.7)} -24q${n(w*.7+4)} 4 ${n(w*.7)} 24z`,c,1.5)+L(`M${n(-w*.25)} -23q-4 11 0 23M${n(w*.25)} -23q4 11 0 23`,dk(c),1.1)+Pa(`M${n(-w*.32)} 0v-11q${n(w*.32)} -9 ${n(w*.64)} 0v11z`,'#3a2a1c',1)+L('M0 -24l1 -5',c2,2)+E(0,-3,w*.3,3,'#f2b8c6',1);
    case'canopy':return Pa(`M${n(-w*.7)} 0v-10h${n(w*1.4)}v10z`,c,1.5)+E(0,-10,w*.62,3.6,'#fff',1)+Pa(`M${n(-w*.72)} -10q-2 -22 ${n(w*.72)} -30q${n(w*.72+2)} 8 ${n(w*.72)} 30`,c2,1,' fill-opacity=".45"')+heart(0,-30,2.6,'#ff6f8f')+flower(-w*.4,-11,2,'#ff9db0','#fff')+flower(w*.4,-11,2,'#ff9db0','#fff');
    case'castle':return R(-w*.72,-34,w*.36,34,c,0,1.5,' fill-opacity=".85"')+R(w*.36,-34,w*.36,34,c,0,1.5,' fill-opacity=".85"')+R(-w*.42,-28,w*.84,28,c2,2,1.5,' fill-opacity=".8"')
      +Pa(`M${n(-w*.76)} -34l${n(w*.22)} -14l${n(w*.22)} 14zM${n(w*.32)} -34l${n(w*.22)} -14l${n(w*.22)} 14z`,'#b28cff',1.3)+gem(0,-20,4,'#fff')+star(-w*.54,-50,2,'#fff')+star(w*.54,-50,2,'#fff')+E(0,-3,w*.36,3.6,'#e6dcff',1);
    case'cushion':return E(0,-3.5,w*.68,6.5,c,1.5)+Array.from({length:7},(_,i)=>C(-w*.55+i*w*.18,-7+(i%2)*1.5,3,c,1)).join('')+E(0,-5,w*.42,3,c2,0,' opacity=".6"');
  }
  return '';
}

/* ---------------------------------------------------------------- tails */
/** 🐱 A thick fluffy tail along the path `d` with darker rings (dashes of the same stroke) and a dark tip (`tip`, the
 * path's end), as Mai's: lilac `c`, `k` its size. */
function ringTail(d,tip,c,k=1){
  const w=n(7.6*k),ring=dk(c,.76),dark=dk(c,.56);
  return L(d,OL,9.6*k)+L(tip,OL,9.6*k)+L(d,c,7.6*k)
    +`<path d="${d}" fill="none" stroke="${ring}" stroke-width="${w}" stroke-dasharray="${n(2.1*k)} ${n(2.5*k)}" stroke-dashoffset="${n(-1.2*k)}"/>`
    +L(tip,dark,7.6*k);
}
function tail(S,K,x,y,dir,big=1,anim=true){   // dir: 1 = the tail goes to the right/up, -1 to the left
  const c=S.face==='points'?K.m:S.tail==='pom'?K.b:K.b,cls=anim?' class="pet-tail"':'',sw=1.5,k=big;
  switch(S.tail){
    case'dino':return `<g${cls}>`+(S.spikes?[.3,.55,.78].map(t=>Pa(`M${n(x+dir*24*k*t-dir*2*k)} ${n(y-6*k-8*k*t*t)}l${n(dir*2*k)} ${n(-4.4*k)}l${n(dir*2.6*k)} ${n(3.6*k)}z`,K.m,1)).join(''):'')
      +Pa(`M${n(x)} ${n(y-6*k)}Q${n(x+dir*12*k)} ${n(y-6*k)} ${n(x+dir*24*k)} ${n(y-14*k)}Q${n(x+dir*15*k)} ${n(y+2*k)} ${n(x)} ${n(y+5*k)}Z`,c,sw)+'</g>';
    case'horse':{const cols=S.mane==='rainbow'?RB:[K.m,K.m,K.m];return `<g${cls}>`+[0,1,2,3,4].map(i=>L(`M${n(x)} ${n(y-1+i*.6)}q${n(dir*(12+i*2)*k)} ${n((-2+i)*k)} ${n(dir*(10+i*3)*k)} ${n((10-i*1.5)*k)}`,OL,4.4)).join('')
      +[0,1,2,3,4].map(i=>L(`M${n(x)} ${n(y-1+i*.6)}q${n(dir*(12+i*2)*k)} ${n((-2+i)*k)} ${n(dir*(10+i*3)*k)} ${n((10-i*1.5)*k)}`,cols[i%cols.length],2.8)).join('')+'</g>';}
    case'qilin':return `<g${cls}>`+L(`M${n(x)} ${n(y)}q${n(dir*12*k)} ${n(-2*k)} ${n(dir*13*k)} ${n(-14*k)}`,OL,4.4)+L(`M${n(x)} ${n(y)}q${n(dir*12*k)} ${n(-2*k)} ${n(dir*13*k)} ${n(-14*k)}`,c,2.8)
      +flame(x+dir*13*k,y-13*k,9*k,K.m,'#ffd36b')+'</g>';
    case'dragon':return `<g${cls}>`+L(`M${n(x)} ${n(y)}q${n(dir*14*k)} ${n(0)} ${n(dir*14*k)} ${n(-15*k)}`,OL,5)+L(`M${n(x)} ${n(y)}q${n(dir*14*k)} ${n(0)} ${n(dir*14*k)} ${n(-15*k)}`,c,3.2)
      +Pa(`M${n(x+dir*14*k)} ${n(y-13*k)}l${n(-dir*4*k)} ${n(-2*k)}l${n(dir*4*k)} ${n(-6*k)}l${n(dir*4*k)} ${n(6*k)}l${n(-dir*4*k)} ${n(2*k)}z`,K.m,1.1)+'</g>';
    case'curl':return `<g${cls}>`+Pa(`M${n(x)} ${n(y)}q${n(dir*12*k)} ${n(-2*k)} ${n(dir*10*k)} ${n(-12*k)}q${n(-dir*1*k)} ${n(-6*k)} ${n(-dir*7*k)} ${n(-3*k)}q${n(dir*4*k)} ${n(2*k)} ${n(dir*2*k)} ${n(7*k)}q${n(-dir*2*k)} ${n(5*k)} ${n(-dir*7*k)} ${n(5*k)}z`,c,sw)+'</g>';
    case'plume':return `<g${cls}>`+Pa(`M${n(x)} ${n(y)}q${n(dir*14*k)} ${n(-4*k)} ${n(dir*16*k)} ${n(-18*k)}q${n(dir*2*k)} ${n(10*k)} ${n(-dir*4*k)} ${n(16*k)}q${n(-dir*4*k)} ${n(4*k)} ${n(-dir*12*k)} ${n(4*k)}z`,c,sw)+'</g>';
    case'stub':return Pa(`M${n(x)} ${n(y)}q${n(dir*5*k)} ${n(-1*k)} ${n(dir*5*k)} ${n(-5*k)}q${n(-dir*3*k)} ${n(-1*k)} ${n(-dir*6*k)} ${n(1*k)}z`,c,sw);
    case'pom':return `<g${cls}>`+L(`M${n(x)} ${n(y)}q${n(dir*8*k)} ${n(-3*k)} ${n(dir*9*k)} ${n(-11*k)}`,OL,3.6)+L(`M${n(x)} ${n(y)}q${n(dir*8*k)} ${n(-3*k)} ${n(dir*9*k)} ${n(-11*k)}`,c,2)+C(x+dir*9*k,y-13*k,4.8*k,c,1.4)+'</g>';
    case'thin':return `<g${cls}>`+L(`M${n(x)} ${n(y)}q${n(dir*12*k)} ${n(-2*k)} ${n(dir*13*k)} ${n(-14*k)}`,OL,4)+L(`M${n(x)} ${n(y)}q${n(dir*12*k)} ${n(-2*k)} ${n(dir*13*k)} ${n(-14*k)}`,c,2.4)+'</g>';
    case'long':{const st=S.stripes?K.m:null;return `<g${cls}>`+L(`M${n(x)} ${n(y)}q${n(dir*16*k)} ${n(0)} ${n(dir*14*k)} ${n(-18*k)}`,OL,6)+L(`M${n(x)} ${n(y)}q${n(dir*16*k)} ${n(0)} ${n(dir*14*k)} ${n(-18*k)}`,S.face==='calico'?K.m:c,4)
      +(st?L(`M${n(x+dir*10*k)} ${n(y-3*k)}l${n(dir*2.5*k)} ${n(-1)}M${n(x+dir*14*k)} ${n(y-9*k)}l${n(dir*2.5*k)} 0`,st,1.6):'')+'</g>';}
    case'ringed':return `<g${cls}>`+ringTail(`M${n(x)} ${n(y)}Q${n(x+dir*16*k)} ${n(y)} ${n(x+dir*13*k)} ${n(y-14*k)}`,`M${n(x+dir*13*k)} ${n(y-14*k)}Q${n(x+dir*12.6*k)} ${n(y-16.2*k)} ${n(x+dir*11.6*k)} ${n(y-17.4*k)}`,K.m,k)+'</g>';
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
  if(S.saddle){const A=rx-.8,B=ry-.8,P=t=>{const a=t*Math.PI/180;return `${n(cx+A*Math.cos(a))} ${n(cy+B*Math.sin(a))}`;};
    s+=Pa(`M${P(-160)}A${n(A)} ${n(B)} 0 0 1 ${P(-48)}Q${n(cx+rx*.15)} ${n(cy-ry*.05)} ${n(cx-rx*.35)} ${n(cy+ry*.05)}Q${n(cx-rx*.75)} ${n(cy+ry*.05)} ${P(-160)}z`,K.m,0);}
  if(S.face==='points')s+='';
  return s;
}
function spikeRow(cx,cy,rx,ry,a0,a1,cnt,sz,col){   // ✨ dino / dragon plates along the body's edge (angles in degrees)
  let s='';for(let i=0;i<cnt;i++){const a=(a0+(a1-a0)*i/(cnt-1))*Math.PI/180,px=cx+Math.cos(a)*rx*.92,py=cy+Math.sin(a)*ry*.92,nx=Math.cos(a),ny=Math.sin(a)*rx/ry,l=Math.hypot(nx,ny),ux=nx/l,uy=ny/l;
    s+=Pa(`M${n(px-uy*sz*.7)} ${n(py+ux*sz*.7)}L${n(px+ux*sz*1.5)} ${n(py+uy*sz*1.5)}L${n(px+uy*sz*.7)} ${n(py-ux*sz*.7)}Z`,col,1.1);}
  return s;
}
const innate=(S,K)=>S.bwings?{art:'w_dragon',color:K.m,c2:K.l,sz:.72}:null;
function sitPose(S,K,o){
  const sc=S.body||1,legs=S.legs||1,lng=S.long||1,hr=12.5*(S.head||1),bw=13*sc*(S.chubby?1.12:1),bh=17*sc*(S.legs<.7?.85:1);
  const by=-bh*.62,neck=S.neck?hr*1.05:0,hy=by-bh*.55-hr*.62-neck,happy=o.mood==='happy'||o.wave;let s='';
  s+=E(0,-.5,bw*1.2+4,2.4,'#000',0,' opacity=".12"');
  const [bk,fr]=backX(o.acc,'sit',{w:bw,y:by-bh*.45,h:bh*.95},innate(S,K));s+=bk;   // 👗 wings, a cape: behind
  if(S.spikes)s+=spikeRow(0,by,bw,bh*.62,150,260,5,3.4,K.m);
  s+=tail(S,K,-bw*.7,-3,-1,1.05*sc);
  s+=E(-bw*.62,-bw*.38,bw*.5,bw*.4,K.b,1.5)+E(bw*.62,-bw*.38,bw*.5,bw*.4,K.b,1.5);   // haunches
  s+=E(0,by,bw,bh*.62,S.bald?K.b:K.b,1.6);                                         // body
  const chest=S.belly||S.face==='mask'||S.face==='urajiro'||S.face==='blaze'||S.face==='tux'&&/^#f|^#e/i.test(K.l)||S.fluff==='ruff'||S.face==='points'||S.face==='tux2'&&K.name==='Hai màu';
  if(chest)s+=E(0,by+bh*.08,bw*.55,bh*.48,K.l,0);
  if(S.belly)s+=L([-.25,.05,.35].map(t=>`M${n(-bw*.4)} ${n(by+bh*t)}q${n(bw*.4)} ${n(bh*.08)} ${n(bw*.8)} 0`).join(''),K.m,.9,' opacity=".45"');
  if(neck)s+=R(-hr*.42,hy+hr*.4,hr*.84,by-bh*.4-hy-hr*.4,K.b,hr*.4,1.5)+R(-hr*.22,hy+hr*.7,hr*.44,by-bh*.4-hy-hr*.7,K.l,hr*.22,0);
  s+=marks(S,K,0,by+2,bw,bh*.55);
  if(o.acc?.body)s+=coat(o.acc.body,'sit',0,by-bh*.45,bw,bh*.95);
  s+=fr;
  const lh=Math.max(5,11*legs),lx=bw*.38,paw=S.face==='points'?K.m:(chest?K.l:K.b),raise=happy?1:0;
  s+=R(-lx-3.4,-lh,6.8,lh+1,K.b,3,1.4)+E(-lx,-1.2,4.2,2.6,paw,1.3);
  s+=raise?`<g class="pet-wave" transform="rotate(-40 ${n(bw*.55)} ${n(by+bh*.05)})">${R(bw*.55-3.4,by+bh*.05-12,6.8,13,K.b,3.4,1.4)+E(bw*.55,by+bh*.05-12.5,4.2,3.2,paw,1.3)+E(bw*.55,by+bh*.05-13.5,1.6,1,PINK,0)}</g>`:R(lx-3.4,-lh,6.8,lh+1,K.b,3,1.4)+E(lx,-1.2,4.2,2.6,paw,1.3);
  if(raise)s+=R(lx-3.4,-lh,6.8,lh+1,K.b,3,1.4)+E(lx,-1.2,4.2,2.6,paw,1.3);
  s+=collarOf(S,o,0,hy+hr*.86,hr*.62);
  s+=head(S,K,0,hy,hr,{mood:o.mood,acc:o.acc});
  if(o.mood==='happy')s+=`<g class="pet-hearts">${heart(hr*1.25,hy-hr*.9,2.2)+heart(-hr*1.35,hy-hr*.4,1.6,'#f5a9bc')}</g>`;
  const wr=o.wr||{};s+=shine([[hr*.95,hy-hr*1.25,wr.head],[-hr*1.05,hy-hr*.05,wr.eye],[hr*.75,hy+hr*1,wr.neck],[bw*.95,by,wr.body],[-bw*1.9,by-bh*.6,wr.back],[bw*1.9,by-bh*.75,wr.back]].filter(p=>p[2]));
  return s;
}
/** 😼 Mai's pose (S.slump): slumped against a wall like a person (the photo), the round belly out, both hind legs
 * forward showing grey toe beans, one front paw on the belly and one down by her side (happy: raised, a little wave),
 * the ringed tail on the floor, the head tilted toward the wall. Same slots as sitPose: wings / cape, clothes, collar. */
function maiSit(S,K,o){
  const b=K.b,m=K.m,hr=12.5,hx=3.5,hy=-33.5,happy=o.mood==='happy',bean='#8e8992',fur='#d9d5dd';let s='';
  const tx=2,ty=-22.5,tw=12.6,th=10,bx=0,by=-12.5,bw=16,bh=12.5;    // torso (leaning right) and belly
  s+=E(0,-.5,25,2.6,'#000',0,' opacity=".12"');
  const [bk,fr]=backX(o.acc,'sit',{w:bw,y:by-bh*.95,h:bh*1.5},null);s+=bk;
  s+=ringTail(`M-9 -6Q-18 -4 -26.5 -2`,`M-26.5 -2L-28.3 -1.6`,m);                 // the tail, lying to the left
  s+=E(-9.5,-6.5,7.6,6.4,b,1.5)+E(10,-6.5,7.6,6.4,b,1.5);                                 // thighs
  const torso=`<ellipse cx="${tx}" cy="${ty}" rx="${tw}" ry="${th}" transform="rotate(10 ${tx} ${ty})"`;
  s+=`${torso} fill="${b}" stroke="${OL}" stroke-width="1.6"/>`+E(bx,by,bw,bh,b,1.6)+`${torso} fill="${b}"/>`;  // one round outline
  // the saddle: a lilac patch on her left side, along the edge of the belly and up the shoulder
  {const A=bw-.8,B=bh-.8,P=t=>{const a=t*Math.PI/180;return `${n(bx+A*Math.cos(a))} ${n(by+B*Math.sin(a))}`;};
    s+=Pa(`M${P(176)}A${n(A)} ${n(B)} 0 0 1 ${P(236)}Q-5 -22 -6 -29.5Q-11 -26.5 -11 -19Q-11.5 -13 ${P(176)}z`,m,0);}
  s+=L('M-2 -8q2.5 1.4 5 0M4 -11.5q2 1 4 0M-5 -13q1.6 .9 3.2 0',fur,.9);                // fluffy belly
  if(o.acc?.body)s+=coat(o.acc.body,'sit',tx-1,ty-6,tw*.95,th*2.1);
  s+=fr;
  // the hind feet, soles to you: grey beans
  const foot=(x,y,rot)=>`<g transform="rotate(${rot} ${x} ${y})">`+E(x,y,4.4,5.4,b,1.4)+E(x,y+1.4,2.1,1.7,bean,0)
    +[[-2.3,-1.9],[-.8,-3.3],[.9,-3.3],[2.4,-1.9]].map(([a,c])=>E(x+a,y+c,.9,1.05,bean,0)).join('')+'</g>';
  s+=foot(-9.5,-3.6,-12)+foot(10,-3.4,14);
  // front legs: her right one bent, the paw on the belly; the left one down by her side (happy: up, waving)
  const arm=d=>L(d,OL,7.6)+L(d,b,5.4);
  s+=arm('M-6.5 -26Q-10 -20 -4.5 -15.5')+E(-3.8,-15,3.6,2.8,b,1.3);
  if(!happy)s+=arm('M11.5 -25Q15 -18 14.5 -9')+E(14.6,-8.2,3.6,2.6,b,1.3);
  s+=`<g transform="rotate(4 ${hx} ${hy})">`+collarOf(S,o,hx-.6,hy+hr*.84,hr*.6)+head(S,K,hx,hy,hr,{mood:o.mood,acc:o.acc})+'</g>';
  if(happy)s+=`<g class="pet-wave" transform="rotate(-8 13 -24)">${arm('M13 -23Q20 -25 21.5 -33')+E(21.8,-35,3.8,4.4,b,1.3)
    +E(21.8,-34,1.8,1.5,bean,0)+[[-1.7,-2.7],[0,-3.5],[1.7,-2.7]].map(([a,c])=>E(21.8+a,-34+c,.8,.95,bean,0)).join('')}</g>`;
  if(happy)s+=`<g class="pet-hearts">${heart(hx+hr*1.3,hy-hr*.9,2.2)+heart(hx-hr*1.4,hy-hr*.5,1.6,'#f5a9bc')}</g>`;
  const wr=o.wr||{};s+=shine([[hx+hr*.95,hy-hr*1.25,wr.head],[hx-hr*1.05,hy-hr*.05,wr.eye],[hx+hr*.75,hy+hr*1,wr.neck],[bw*.95,by-4,wr.body],[-bw*1.9,by-bh,wr.back],[bw*1.9,by-bh*1.2,wr.back]].filter(p=>p[2]));
  return s;
}
function walkPose(S,K,o){
  const sc=S.body||1,legs=S.legs||1,lng=S.long||1,hr=11.5*(S.head||1),rx=13*sc*lng*(S.chubby?1.08:1),ry=8.2*sc,lh=Math.max(4.5,10*legs);
  const cy=-lh-ry*.6,neck=S.neck?hr*1.1:0,hx=rx*.72+neck*.35,hy=cy-ry-hr*.35-neck;let s='';
  s+=E(0,-.5,rx+5,2.3,'#000',0,' opacity=".12"');
  const [bk,fr]=backX(o.acc,'walk',{x:0,y:cy,rx,ry},innate(S,K));s+=bk;
  if(S.spikes)s+=spikeRow(0,cy,rx,ry,195,320,6,3.2,K.m);
  const leg=(x,cls)=>`<g class="pet-leg ${cls}">${R(x-2.8,cy+ry*.2,5.6,lh+ry*.4-1,K.b,2.6,1.3)+E(x,-1.1,3.6,2.1,S.face==='points'?K.m:K.l,1.1)}</g>`;
  s+=leg(-rx*.58,'b')+leg(rx*.5,'a');                                                  // far legs
  s+=tail(S,K,-rx*.9,cy-ry*.25,-1,.95*sc);
  s+=E(0,cy,rx,ry,K.b,1.6);
  if(S.face!=='calico'&&(S.face==='mask'||S.face==='urajiro'||S.face==='blaze'||S.fluff==='ruff'||S.face==='tux'&&/^#f|^#e/i.test(K.l)))s+=Pa(`M${n(-rx*.6)} ${n(cy+ry*.6)}q${n(rx*.6)} ${n(ry*.55)} ${n(rx*1.3)} ${n(-ry*.2)}q${n(-rx*.5)} ${n(ry*.05)} ${n(-rx*1.3)} ${n(ry*.2)}z`,K.l,0);
  if(S.belly)s+=Pa(`M${n(-rx*.6)} ${n(cy+ry*.6)}q${n(rx*.6)} ${n(ry*.55)} ${n(rx*1.3)} ${n(-ry*.2)}q${n(-rx*.5)} ${n(ry*.05)} ${n(-rx*1.3)} ${n(ry*.2)}z`,K.l,0);
  s+=marks(S,K,0,cy,rx,ry);
  if(neck){const d=`M${n(rx*.45)} ${n(cy-ry*.3)}Q${n(hx+hr*.05)} ${n(cy-ry*.6)} ${n(hx-hr*.05)} ${n(hy+hr*.6)}`;s+=L(d,OL,hr*.86+3)+L(d,K.b,hr*.86)+L(d,K.l,hr*.32,' opacity=".8"');}
  if(o.acc?.body)s+=coat(o.acc.body,'walk',0,cy,rx,ry);
  s+=fr;
  s+=leg(-rx*.38,'a')+leg(rx*.68,'b');                                                 // near legs
  s+=collarOf(S,o,hx,hy+hr*.84,hr*.58);
  s+=head(S,K,hx,hy,hr,{mood:o.mood,acc:o.acc});
  const wr=o.wr||{};s+=shine([[hx+hr*.9,hy-hr*1.2,wr.head],[hx+hr*1.1,hy,wr.eye],[hx-hr*.9,hy+hr*.9,wr.neck],[rx*.2,cy+ry*.2,wr.body],[-rx*1.5,cy-ry*2.6,wr.back]].filter(p=>p[2]));
  return s;
}
function sleepPose(S,K,o){
  const sc=S.body||1,lng=S.long||1,hr=11*(S.head||1),rx=16*sc*Math.min(1.25,lng),ry=8.5*sc;let s='';
  s+=E(0,-.4,rx+5,2.4,'#000',0,' opacity=".12"');
  if(S.spikes)s+=spikeRow(0,-ry,rx,ry,200,320,6,3,K.m);
  s+=E(0,-ry,rx,ry,K.b,1.6)+marks(S,K,0,-ry,rx,ry);
  if(o.acc?.body)s+=Pa(`M${n(-rx*.7)} ${n(-ry*1.75)}q${n(rx*.6)} ${n(-ry*.35)} ${n(rx*1.2)} ${n(.2)}l${n(rx*.05)} ${n(ry*1.1)}h${n(-rx*1.3)}z`,coatColor(o.acc.body),1.2);
  s+=tail(S,K,-rx*.85,-ry*.45,1,.0001,false);
  if(S.tail==='ringed')s+=ringTail(`M${n(-rx*.95)} ${n(-ry*.55)}q${n(rx*.1)} ${n(ry*.62)} ${n(rx*.95)} ${n(ry*.5)}`,`M${n(rx*0)} ${n(-ry*.05)}q${n(rx*.12)} ${n(-ry*.02)} ${n(rx*.25)} ${n(-ry*.08)}`,K.m,.7);
  else s+=Pa(`M${n(-rx*.95)} ${n(-ry*.6)}q${n(rx*.2)} ${n(ry*.75)} ${n(rx*1.25)} ${n(ry*.5)}`,'none',0)+L(`M${n(-rx*.95)} ${n(-ry*.55)}q${n(rx*.1)} ${n(ry*.62)} ${n(rx*1.2)} ${n(ry*.42)}`,OL,5.2)+L(`M${n(-rx*.95)} ${n(-ry*.55)}q${n(rx*.1)} ${n(ry*.62)} ${n(rx*1.2)} ${n(ry*.42)}`,S.face==='points'?K.m:K.b,3.4);
  s+=E(rx*.32,-2.2,5,2.6,S.face==='points'?K.m:K.l,1.2);
  s+=collarOf(S,o,rx*.58,-hr*.5,hr*.55);
  s+=head(S,K,rx*.62,-hr*.95,hr,{blink:'sleep',acc:o.acc});
  s+=`<g class="pet-zz"><text x="${n(rx*.62+hr)}" y="${n(-hr*2.1)}" font-size="8" font-weight="800" fill="${OL}">z</text><text x="${n(rx*.62+hr+6)}" y="${n(-hr*2.6)}" font-size="6" font-weight="800" fill="${OL}">z</text></g>`;
  return s;
}
const coatColor=id=>({ao_len:'#e58b7a',ao_mua:'#f6cf45',ao_vn:'#d8392f',ao_khung_long:'#79b86b',ao_dai:'#d94f6e',vay_cong_chua:'#c8a6ef'})[id]||wd(id)?.color||'#ccc';

/** The pet's markup, paws on y = 0 (no <svg> wrapper). breed: {shape, size}; coat: {b, m, l, e, name}; pose: sit | walk |
 * sleep | happy; acc: {neck, head, body, bed}. An unknown shape draws a plain dog. */
export function petInner(breed,coat,pose='sit',acc={},fx={}){
  // fx: r rank, x coat effect, lg a 🌟 legendary that kept its breed, wr {slot: piece rank}, o cute aura, st a whole set
  const x=fx?.x||'',r=Math.max(0,Math.min(6,Number(fx?.r)||0)),legend=breed?.fuse==='legend'||fx?.lg===true;
  const S=SHAPES[breed?.shape]||SHAPES.mutt,K={b:'#e2a65a',m:'#c4823a',l:'#fbe3bd',e:EYE,...(coat||{}),...(breed?.fuse==='myth'?{}:FXCOAT[x]||{})},k=SIZE[breed?.size]||1,o={acc:acc||{},mood:pose==='happy'?'happy':'',wave:breed?.id==='than_tai',wr:fx?.wr||null};
  const body=pose==='walk'?walkPose(S,K,o):pose==='sleep'?sleepPose(S,K,o):S.slump?maiSit(S,K,o):sitPose(S,K,o);
  const bed=acc?.bed?bedSVG(acc.bed,pose==='walk'?52:46):'',tall=acc?.bed==='nha_go'||acc?.bed==='lau_dai'||/^(castle|canopy)$/.test(wd(acc?.bed)?.art||'');
  const [back0,front0]=aura(r,x,legend,S.k,pose,k),[wb,wf]=wearFx(Number(fx?.o)||0,fx?.st||''),back=back0+wb,front=front0+wf,mut=x==='dot_bien'?' filter="url(#pt-mut)"':'';
  return `<g class="pet-art pet-${pose}${r?` pet-r${r}`:''}${legend?' pet-legend':''}">${back0||mut||x==='cau_vong'?DEFS:''}${back}${bed&&tall?bed:''}<g transform="scale(${k})">${bed&&!tall?`<g transform="scale(${n(1/k*100)/100})">${bed}</g>`:''}<g class="pet-bob"${mut}>${body}</g></g>${front}</g>`;
}
/** The viewBox [w, h, top] (paws on y = 0, `top` above them): the auras of S and up and the SSS / legendary wings,
 * rays and halo need room. Square boxes: the drawing's size follows from the width. */
const BIG_W=84;
function boxOf(r,legend,flat,wide=false){
  if(wide&&r<4)r=4;   // 🪽 wings, a cute aura or a set's effect need the room of an S
  if(r>=6||legend)return flat?[104,90,82]:[104,92,84];
  if(r>=4)return flat?[84,72,66]:[84,76,70];
  return flat?[72,62,58]:[68,68,64];
}
/** 🐢 Perf 19/10 (iPad "phản hồi rất lag"): an animated group inside an inline <svg> is repainted, with the whole
 * picture, on every frame (no engine composites SVG children), and an SSS pet has ~10 of them. A grid of thumbnails
 * (the pets strip, the wardrobe shelf, the 🐾 board: 25+ pets, 270+ animations) kept the main thread busy all the
 * time (a 4× slower phone: 11 fps on the board, a tap waited 76 ms on average). So only a featured picture (the pet on the stage, a podium, the photo: drawn at LIVE_MIN px or
 * more) carries `pet-live` and moves (css/pets.css); the thumbnails are the same art, still. */
const LIVE_MIN=90;
/** A whole <svg>, `size` px wide (the box is fitted to the pose; an SSS or a legendary is drawn a little larger so the
 * pet itself is not shrunk by its wider aura). */
export function petSVG(breed,coat,pose='sit',acc={},size=72,cls='pet-svg',fx={}){
  const [w,h,top]=boxOf(Number(fx?.r)||0,breed?.fuse==='legend'||fx?.lg===true,pose==='walk'||pose==='sleep',hasWings(acc)||!!fx?.o||!!fx?.st),px=Math.round(size*w/BIG_W);
  if(size>=LIVE_MIN)cls+=' pet-live';
  return `<svg class="${cls}" viewBox="${-w/2} ${-top} ${w} ${h}" width="${Math.max(size,px)}" height="${Math.max(size,px)}" aria-hidden="true" focusable="false">${petInner(breed,coat,pose,acc,fx)}</svg>`;
}
/** Look a pet up in the catalogue (content.journey.pets): {breed, coat} for a save's {b, c}. */
export function lookup(cat,b,c){register(cat);const breed=(cat?.breeds||[]).find(x=>x.id===b);return breed?{breed,coat:breed.coats[c]||breed.coats[0]}:null;}
/** An <img> source for canvases (town map, the stroll): the pet as a data URL. A picture of its own: the gradients it
 * uses (a D pet's wings, a coat) are defined inside it, not borrowed from another <svg> of the page. */
export function petURL(breed,coat,pose,acc,size=96,fx={}){return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(petFile(breed,coat,pose,acc,size,fx));}
function petFile(breed,coat,pose,acc,size,fx){
  const s=petSVG(breed,coat,pose,acc,size,'pet-svg',fx).replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" ');
  return !s.includes('<defs>')&&s.includes('url(#pt-')?s.replace(/(<svg [^>]*>)/,'$1'+DEFS):s;
}
/* 🐢 Perf 19/10: a thumbnail as one <img> instead of an inline <svg> of 300–600 shapes. Building a grid of them (the
 * 🐾 board's 40 rows, the wardrobe shelf, the pets strip) laid out every shape (875 ms of layout for the board on a
 * 4× slower phone), and a re-render after each command did it again. An <img> is parsed, sized and painted as one
 * box, and the browser keeps the decoded picture for the same URL. A blob: URL (a short attribute, not 30–60 KB of
 * data: text per pet in the markup), at most IMG_MAX kept (the oldest let go). Same art, still (thumbnails did not
 * move since LIVE_MIN either). */
const IMG=new Map(),IMG_MAX=160;
function imgURL(key,make){
  let url=IMG.get(key);
  if(url!==undefined){IMG.delete(key);IMG.set(key,url);return url;}   // most recently used last
  try{url=URL.createObjectURL(new Blob([make()],{type:'image/svg+xml'}));}
  catch{return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(make());}   // no Blob URLs here: a data: URL
  if(IMG.size>=IMG_MAX){const [old,u]=IMG.entries().next().value;IMG.delete(old);try{URL.revokeObjectURL(u);}catch{/* gone */}}
  IMG.set(key,url);return url;
}
export function petIMG(breed,coat,pose='sit',acc={},size=72,cls='pet-svg',fx={}){
  const key=JSON.stringify([breed?.id,breed?.shape,breed?.size,breed?.fuse,coat,pose,acc,size,fx]);
  const url=imgURL(key,()=>petFile(breed,coat,pose,acc,size,fx));
  const [w]=boxOf(Number(fx?.r)||0,breed?.fuse==='legend'||fx?.lg===true,pose==='walk'||pose==='sleep',hasWings(acc)||!!fx?.o||!!fx?.st),px=Math.max(size,Math.round(size*w/BIG_W));
  return `<img class="${cls} pet-img" src="${url}" width="${px}" height="${px}" alt="" aria-hidden="true" draggable="false">`;
}
/** A picture of a pet for a page: a featured one (LIVE_MIN px or more) inline and moving, a thumbnail as petIMG. */
export function petPicture(breed,coat,pose='sit',acc={},size=72,cls='pet-svg',fx={}){
  return size>=LIVE_MIN?petSVG(breed,coat,pose,acc,size,cls,fx):petIMG(breed,coat,pose,acc,size,cls,fx);
}
/** The box petSVG fits a walking pet in ({w, h} of its viewBox, `foot` the share of the height down to the paws) and
 * `k`, walkScale: what a canvas needs to draw it paws on the ground at the right size. */
export function refBox(cat,ref,pose){
  const b=(cat?.breeds||[]).find(x=>x.id===ref?.b),flat=pose==='walk'||pose==='sleep';
  const acc=accOf(cat,ref);
  const [w,h,top]=boxOf(Number(ref?.r)||0,b?.fuse==='legend'||ref?.lg===true,flat,hasWings(acc)||!!ref?.o||!!ref?.st);
  return {w,h,foot:top/h,k:walkScale(cat,ref),base:flat?72:68};
}
/** 🐶 Owner 19/10 "cún cưng to hơn tí": how much bigger a walking pet is drawn (dogs 1.3×, a high rank a little more). */
export function walkScale(cat,ref){const b=(cat?.breeds||[]).find(x=>x.id===ref?.b);if(!b)return 1;return (b.kind==='dog'?1.3:1.1)*((Number(ref?.r)||0)>=5||b.fuse==='legend'?1.08:1);}
/** The pet a save walks with ({b, c, n, a}: game/pets.py walk_ref, live `pt`) as an <img> source, or ''. */
export function refURL(cat,ref,pose='walk',size=120){
  const L=lookup(cat,ref?.b,ref?.c);if(!L)return '';
  return petURL(L.breed,L.coat,pose,accOf(cat,ref),size,fxRef(cat,ref));
}
/** {slot: piece} of a ref's `a` (wardrobe ids; an older catalogue: its accessories). */
export function accOf(cat,ref){
  register(cat);const acc={};
  for(const id of Array.isArray(ref?.a)?ref.a:[]){const a=wd(id)||(cat?.accs||[]).find(x=>x.id===id);if(a)acc[a.slot]=id;}
  return acc;
}
/** The fx of a ref (live `pt`, a board row): rank, coat effect, legendary, piece ranks by slot, cute aura, set. */
export function fxRef(cat,ref){
  register(cat);const wr={},ar=Array.isArray(ref?.ar)?ref.ar:[];
  (Array.isArray(ref?.a)?ref.a:[]).forEach((id,i)=>{const a=wd(id);if(a&&ar[i])wr[a.slot]=ar[i];});
  return {r:ref?.r,x:ref?.x,lg:ref?.lg===true,wr,o:ref?.o,st:ref?.st};
}
