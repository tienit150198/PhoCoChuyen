/** 🎣 Cá vẽ bằng code (owner 24/10: "cá chia nhiều loại … loại càng hiếm càng to, mang được trên người"): every species of
 * game/fishing_content.py drawn from its family (a silhouette: perch, carp, cat, eel, disc, ray, shark, arowana,
 * sturgeon, armour…), its colours and a pattern clipped to the body. One list of primitives draws both an SVG (cards,
 * Sổ cá, tranh cá) and a canvas (the lake, the walk maps, the aquarium). Rarer fish glow (🟣+), shine (🟡) or burn (🔴).
 * Pure: no DOM needed for the SVG string (tests/fishing-art.mjs). The fish faces right in a 120 × 60 box. */

export const RARITY_COLORS=['#b8c0c8','#43b05c','#3d7bff','#a855f7','#ff8a1c','#ffcf26','#ff3b3b'];
const W=120,H=60,CY=30;
const F=(n)=>Math.round(n*10)/10;

/* Family shapes: xt tail base, xn snout, ht/hb half heights above/below, xm hump (0 tail … 1 snout), tail kind, fins. */
const FAM={
  perch:{xt:26,xn:108,ht:15,hb:13,xm:.55,tail:'fork',dorsal:'spiny',anal:1,pec:1},
  carp:{xt:26,xn:106,ht:16,hb:15,xm:.5,tail:'fork',dorsal:'long',anal:1,pec:1,barbel:'short'},
  cat:{xt:22,xn:108,ht:11,hb:12,xm:.78,tail:'round',dorsal:'small',anal:2,pec:1,barbel:'long',adipose:1},
  snake:{xt:20,xn:110,ht:10,hb:10,xm:.6,tail:'round',dorsal:'run',anal:3,pec:1},
  eel:{xt:8,xn:112,ht:6,hb:6,xm:.7,tail:'point',dorsal:'eel',anal:0,pec:1},
  disc:{xt:32,xn:100,ht:22,hb:21,xm:.5,tail:'fan',dorsal:'arc',anal:4,pec:1},
  angel:{xt:36,xn:98,ht:19,hb:18,xm:.55,tail:'fan',dorsal:'tall',anal:5,pec:1},
  flat:{xt:26,xn:104,ht:20,hb:20,xm:.52,tail:'fan',dorsal:'fringe',anal:0,pec:0,flat:1},
  ray:{ray:'ray'},manta:{ray:'manta'},
  shark:{xt:24,xn:112,ht:12,hb:10,xm:.6,tail:'shark',dorsal:'shark',anal:1,pec:2,gills:1},
  hammer:{xt:24,xn:106,ht:11,hb:9,xm:.6,tail:'shark',dorsal:'shark',anal:1,pec:2,gills:1,hammer:1},
  thresher:{xt:34,xn:112,ht:12,hb:10,xm:.6,tail:'thresher',dorsal:'shark',anal:1,pec:2,gills:1},
  whale:{xt:22,xn:112,ht:15,hb:12,xm:.72,tail:'shark',dorsal:'shark',anal:1,pec:2,gills:1,mouth:1},
  bill:{xt:24,xn:100,ht:13,hb:11,xm:.5,tail:'lunate',dorsal:'tall',anal:1,pec:1,bill:16},
  sail:{xt:24,xn:100,ht:11,hb:10,xm:.5,tail:'lunate',dorsal:'sail',anal:1,pec:1,bill:16},
  needle:{xt:16,xn:96,ht:5,hb:5,xm:.5,tail:'fork',dorsal:'rear',anal:2,pec:0,bill:18,beak2:1},
  flyer:{xt:26,xn:108,ht:9,hb:9,xm:.6,tail:'fork',dorsal:'small',anal:1,pec:0,wing:1},
  tuna:{xt:24,xn:110,ht:15,hb:13,xm:.42,tail:'lunate',dorsal:'tuna',anal:1,pec:1,finlets:1},
  puffer:{xt:38,xn:96,ht:20,hb:21,xm:.5,tail:'fan',dorsal:'small',anal:2,pec:1,round:1},
  box:{xt:36,xn:98,ht:16,hb:16,xm:.5,tail:'fan',dorsal:'small',anal:2,pec:1,box:1},
  arowana:{xt:22,xn:110,ht:11,hb:12,xm:.62,tail:'fan',dorsal:'rear',anal:6,pec:1,barbel:'chin',up:1},
  gar:{xt:18,xn:96,ht:8,hb:8,xm:.5,tail:'round',dorsal:'rear',anal:2,pec:1,bill:14},
  sturgeon:{xt:24,xn:106,ht:10,hb:9,xm:.55,tail:'shark',dorsal:'rear',anal:2,pec:1,snout:1,barbel:'under',scutes:1},
  mola:{xt:40,xn:100,ht:22,hb:22,xm:.5,tail:'clavus',dorsal:'mola',anal:7,pec:1},
  oar:{xt:4,xn:112,ht:6,hb:6,xm:.75,tail:'point',dorsal:'crest',anal:0,pec:0},
  fancy:{xt:42,xn:100,ht:19,hb:19,xm:.5,tail:'veil',dorsal:'arc',anal:0,pec:1,round:1},
  armor:{xt:20,xn:108,ht:15,hb:13,xm:.7,tail:'shark',dorsal:'shark',anal:1,pec:2,armor:1},
  lobe:{xt:26,xn:106,ht:15,hb:14,xm:.55,tail:'lobe',dorsal:'lobe',anal:8,pec:3},
  xipha:{xt:22,xn:110,ht:14,hb:12,xm:.62,tail:'lunate',dorsal:'small',anal:1,pec:1,jaw:1},
};
export const FAMILIES=Object.keys(FAM);

/** A small seeded random (species id → the same spots every time). */
function seeded(id){let h=2166136261;for(let i=0;i<id.length;i++){h^=id.charCodeAt(i);h=Math.imul(h,16777619);}
  return()=>{h^=h<<13;h^=h>>>17;h^=h<<5;return((h>>>0)%10000)/10000;};}

/** The lens body of a side-view fish. */
function bodyPath(f){
  const {xt,xn,ht,hb,xm}=f,x=xt+(xn-xt)*xm;
  if(f.box)return `M${xt} ${CY-ht*.55}L${xt+4} ${CY-ht}L${xn-8} ${CY-ht}Q${xn} ${CY-ht} ${xn} ${CY-4}L${xn} ${CY+4}Q${xn} ${CY+hb} ${xn-8} ${CY+hb}L${xt+4} ${CY+hb}L${xt} ${CY+hb*.55}Z`;
  if(f.round)return `M${xt} ${CY-3}C${xt+4} ${CY-ht*1.25} ${xn-6} ${CY-ht*1.3} ${xn} ${CY}C${xn-6} ${CY+hb*1.3} ${xt+4} ${CY+hb*1.25} ${xt} ${CY+3}Z`;
  const tip=f.tail==='point'?0:f.tail==='clavus'?.9:.28;
  if(f.snout)return `M${xt} ${CY-ht*tip}Q${x} ${CY-ht*1.25} ${xn-12} ${CY-ht*.5}L${xn} ${CY-3}L${xn-10} ${CY+hb*.3}Q${x} ${CY+hb*1.2} ${xt} ${CY+hb*tip}Z`;
  if(f.armor)return `M${xt} ${CY-ht*tip}Q${x-10} ${CY-ht*1.05} ${xn-26} ${CY-ht*1.05}Q${xn-4} ${CY-ht*1.05} ${xn} ${CY+2}Q${xn-6} ${CY+hb*1.1} ${xn-30} ${CY+hb}Q${x-12} ${CY+hb*1.1} ${xt} ${CY+hb*tip}Z`;
  return `M${xt} ${CY-ht*tip}Q${F(x)} ${F(CY-ht*1.32)} ${xn} ${CY+(f.up?-2:0)}Q${F(x)} ${F(CY+hb*1.32)} ${xt} ${CY+hb*tip}Z`;
}

function tailPath(f){
  const {xt}=f,a=f.ht*.3,b=f.hb*.3;
  switch(f.tail){
    case'fork':return `M${xt+2} ${CY-a}L${xt-15} ${CY-f.ht*.95}L${xt-8} ${CY}L${xt-15} ${CY+f.hb*.95}L${xt+2} ${CY+b}Z`;
    case'round':return `M${xt+2} ${CY-a}C${xt-12} ${CY-f.ht*1.1} ${xt-18} ${CY+f.hb*1.1} ${xt+2} ${CY+b}Z`;
    case'fan':return `M${xt+2} ${CY-a}L${xt-13} ${CY-f.ht*.85}Q${xt-9} ${CY} ${xt-13} ${CY+f.hb*.85}L${xt+2} ${CY+b}Z`;
    case'lunate':return `M${xt+2} ${CY-2}Q${xt-6} ${CY-f.ht*.5} ${xt-12} ${CY-f.ht*1.25}Q${xt-6} ${CY} ${xt-12} ${CY+f.hb*1.25}Q${xt-6} ${CY+f.hb*.5} ${xt+2} ${CY+2}Z`;
    case'shark':return `M${xt+3} ${CY-a}L${xt-16} ${CY-f.ht*1.35}L${xt-7} ${CY+1}L${xt-11} ${CY+f.hb*.85}L${xt+3} ${CY+b}Z`;
    case'thresher':return `M${xt+3} ${CY-a}Q${xt-14} ${CY-f.ht*1.1} ${xt-32} ${CY-f.ht*1.9}Q${xt-14} ${CY-f.ht*.3} ${xt-6} ${CY+1}L${xt-9} ${CY+f.hb*.8}L${xt+3} ${CY+b}Z`;
    case'veil':return `M${xt+3} ${CY-a}C${xt-14} ${CY-f.ht*1.5} ${xt-34} ${CY-f.ht*.9} ${xt-30} ${CY+2}C${xt-34} ${CY+f.hb*1.2} ${xt-12} ${CY+f.hb*1.6} ${xt+3} ${CY+b}Z`;
    case'lobe':return `M${xt+2} ${CY-a}L${xt-12} ${CY-f.ht*1.05}L${xt-9} ${CY-2}L${xt-17} ${CY}L${xt-9} ${CY+2}L${xt-12} ${CY+f.hb*1.05}L${xt+2} ${CY+b}Z`;
    case'clavus':return `M${xt+3} ${CY-f.ht*.9}Q${xt-7} ${CY} ${xt+3} ${CY+f.hb*.9}Z`;
    default:return '';
  }
}

function dorsalPath(f){
  const {xt,xn,ht}=f,L=xn-xt,top=CY-ht*1.12;
  switch(f.dorsal){
    case'spiny':return `M${xt+L*.32} ${top+3}L${xt+L*.38} ${top-9}L${xt+L*.45} ${top-6}L${xt+L*.5} ${top-8}L${xt+L*.56} ${top-4}L${xt+L*.66} ${top+1}Z`;
    case'long':return `M${xt+L*.3} ${top+3}Q${xt+L*.45} ${top-9} ${xt+L*.62} ${top-2}L${xt+L*.66} ${top+2}Z`;
    case'small':return `M${xt+L*.4} ${top+3}L${xt+L*.5} ${top-6}L${xt+L*.56} ${top+2}Z`;
    case'run':return `M${xt+L*.08} ${CY-ht*.55}Q${xt+L*.4} ${top-5} ${xt+L*.72} ${top+3}L${xt+L*.68} ${top+5}Z`;
    case'eel':return `M${xt} ${CY-1}Q${xt+L*.4} ${CY-ht-5} ${xt+L*.7} ${CY-ht+1}L${xt+L*.68} ${CY-ht+3}Q${xt+L*.4} ${CY-ht-1} ${xt+4} ${CY}Z`;
    case'arc':return `M${xt+L*.15} ${CY-ht*.75}Q${xt+L*.4} ${top-8} ${xt+L*.62} ${top+3}Z`;
    case'tall':return `M${xt+L*.3} ${top+3}L${xt+L*.38} ${top-18}L${xt+L*.55} ${top+2}Z`;
    case'fringe':return '';
    case'shark':return `M${xt+L*.42} ${top+3}Q${xt+L*.5} ${top-14} ${xt+L*.48} ${top-15}L${xt+L*.6} ${top+3}Z`;
    case'sail':return `M${xt+L*.25} ${top+4}Q${xt+L*.45} ${top-28} ${xt+L*.72} ${top-14}L${xt+L*.74} ${top+4}Z`;
    case'tuna':return `M${xt+L*.48} ${top+3}L${xt+L*.55} ${top-8}L${xt+L*.62} ${top+3}Z`;
    case'rear':return `M${xt+L*.08} ${CY-ht*.4}L${xt+L*.14} ${top-2}L${xt+L*.3} ${CY-ht*.85}Z`;
    case'mola':return `M${xt+L*.15} ${CY-ht*.9}L${xt+L*.12} ${top-22}L${xt+L*.32} ${CY-ht*.95}Z`;
    case'crest':return `M${xt+L*.02} ${CY-ht*.5}Q${xt+L*.5} ${CY-ht-9} ${xn-6} ${CY-ht-5}L${xn-2} ${CY-ht-24}L${xn-10} ${CY-ht-2}Q${xt+L*.5} ${CY-ht-3} ${xt+L*.04} ${CY}Z`;
    case'lobe':return `M${xt+L*.38} ${top+3}L${xt+L*.44} ${top-9}L${xt+L*.52} ${top+2}Z M${xt+L*.18} ${CY-ht*.7}Q${xt+L*.2} ${top-6} ${xt+L*.28} ${CY-ht*.8}Z`;
    default:return '';
  }
}

function analPath(f){
  const {xt,xn,hb}=f,L=xn-xt,bot=CY+hb*1.1;
  switch(f.anal){
    case 1:return `M${xt+L*.22} ${bot-3}L${xt+L*.28} ${bot+6}L${xt+L*.36} ${bot-2}Z`;
    case 2:return `M${xt+L*.15} ${bot-3}Q${xt+L*.3} ${bot+6} ${xt+L*.45} ${bot-1}Z`;
    case 3:return `M${xt+L*.08} ${CY+hb*.5}Q${xt+L*.35} ${bot+5} ${xt+L*.6} ${bot-1}Z`;
    case 4:return `M${xt+L*.15} ${CY+hb*.75}Q${xt+L*.4} ${bot+8} ${xt+L*.6} ${bot-3}Z`;
    case 5:return `M${xt+L*.3} ${bot-3}L${xt+L*.36} ${bot+16}L${xt+L*.52} ${bot-2}Z`;
    case 6:return `M${xt+L*.08} ${CY+hb*.4}L${xt+L*.14} ${bot+3}L${xt+L*.3} ${CY+hb*.85}Z`;
    case 7:return `M${xt+L*.15} ${CY+hb*.9}L${xt+L*.12} ${bot+20}L${xt+L*.32} ${CY+hb*.95}Z`;
    case 8:return `M${xt+L*.25} ${bot-3}Q${xt+L*.27} ${bot+7} ${xt+L*.34} ${bot-2}Z`;
    default:return '';
  }
}

function pecPath(f){
  const x=f.xt+(f.xn-f.xt)*.72,y=CY+f.hb*.35;
  if(f.pec===1)return `M${x} ${y}Q${x-8} ${y+4} ${x-11} ${y+9}Q${x-3} ${y+6} ${x+2} ${y+2}Z`;
  if(f.pec===2)return `M${x} ${y}Q${x-6} ${y+8} ${x-16} ${y+13}Q${x-6} ${y+6} ${x+3} ${y+1}Z`;
  if(f.pec===3)return `M${x} ${y}C${x-6} ${y+4} ${x-9} ${y+9} ${x-6} ${y+12}C${x-2} ${y+10} ${x+2} ${y+5} ${x+2} ${y+1}Z`;
  return '';
}

/** Primitives {d, fill, stroke?, sw?, clip?, op?} of a species (or a family stub). */
export function fishParts(sp){
  const fam=FAM[sp?.fam]||FAM.perch,body=sp?.body||'#8aa',belly=sp?.belly||'#dde',fin=sp?.fin||'#678',pat=sp?.pat||'none';
  const out=[];
  if(fam.ray){
    const manta=fam.ray==='manta';
    const b=manta?`M60 18Q78 8 112 30Q78 36 68 42L60 44L52 42Q42 36 8 30Q42 8 60 18Z`:`M60 8Q86 18 110 30Q86 40 60 50Q34 40 10 30Q34 18 60 8Z`;
    out.push({d:manta?'M60 42Q62 52 72 58':'M60 48Q64 56 78 59',fill:'none',stroke:fin,sw:2});
    out.push({d:b,fill:body,stroke:fin,sw:1,body:1});
    if(manta)out.push({d:'M56 18Q54 10 50 12M64 18Q66 10 70 12',fill:'none',stroke:fin,sw:2.4});
    out.push({d:b,fill:'belly',clip:1,op:.0});
    patternParts(sp,out,{xt:10,xn:110,ht:20,hb:20});
    out.push({d:'M54 22a2 2 0 1 0 0.1 0M66 22a2 2 0 1 0 0.1 0',fill:'#111'});
    return {parts:out,body:b};
  }
  const f=fam,b=bodyPath(f);
  const t=tailPath(f);if(t)out.push({d:t,fill:fin,stroke:shade(fin),sw:.8});
  const dp=dorsalPath(f);if(dp)out.push({d:dp,fill:fin,stroke:shade(fin),sw:.8});
  const ap=analPath(f);if(ap)out.push({d:ap,fill:fin,stroke:shade(fin),sw:.8});
  if(f.wing)out.push({d:`M78 ${CY+2}Q58 ${CY-24} 30 ${CY-22}Q52 ${CY-8} 74 ${CY+6}Z`,fill:fin,stroke:shade(fin),sw:.8,op:.92});
  if(f.adipose)out.push({d:`M${f.xt+10} ${CY-f.ht*.7}Q${f.xt+15} ${CY-f.ht*1.2} ${f.xt+22} ${CY-f.ht*.85}Z`,fill:fin});
  if(f.finlets)for(let i=0;i<4;i++){const x=f.xt+4+i*4;out.push({d:`M${x} ${CY-f.ht*.45}l2 -3l1 3ZM${x} ${CY+f.hb*.45}l2 3l1 -3Z`,fill:fin});}
  if(f.flat){let fr='';for(let i=0;i<14;i++){const a=Math.PI*(i/13),x=F(f.xt+6+(f.xn-f.xt-10)*i/13);fr+=`M${x} ${F(CY-f.ht*Math.sin(a)-1)}l2 -4l2 4ZM${x} ${F(CY+f.hb*Math.sin(a)+1)}l2 4l2 -4Z`;}out.push({d:fr,fill:fin});}
  if(f.bill)out.push({d:`M${f.xn-2} ${CY-2}L${f.xn+f.bill} ${CY}L${f.xn-2} ${CY+2}Z`,fill:shade(body),stroke:shade(body,.5),sw:.6});
  if(f.beak2)out.push({d:`M${f.xn-2} ${CY+1}L${f.xn+f.bill-2} ${CY+2}L${f.xn-2} ${CY+3}Z`,fill:shade(body)});
  if(f.hammer)out.push({d:`M${f.xn-6} ${CY-14}Q${f.xn+4} ${CY-14} ${f.xn+4} ${CY-10}L${f.xn+4} ${CY+8}Q${f.xn+4} ${CY+12} ${f.xn-6} ${CY+12}Q${f.xn-2} ${CY} ${f.xn-6} ${CY-14}Z`,fill:body,stroke:shade(body),sw:.8});
  out.push({d:b,fill:body,stroke:shade(body,.7),sw:1,body:1});
  out.push({d:b,fill:'belly',clip:1});
  patternParts(sp,out,f);
  const pp=pecPath(f);if(pp)out.push({d:pp,fill:fin,stroke:shade(fin),sw:.7,op:.95});
  if(f.gills)for(let i=0;i<3;i++){const x=f.xn-20-i*3;out.push({d:`M${x} ${CY-5}q-2 5 0 10`,fill:'none',stroke:shade(body,.55),sw:.8});}
  else if(!f.armor)out.push({d:`M${f.xn-15} ${CY-f.ht*.55}Q${f.xn-19} ${CY} ${f.xn-15} ${CY+f.hb*.55}`,fill:'none',stroke:shade(body,.6),sw:.9});
  if(f.armor){out.push({d:`M${f.xn-34} ${CY-f.ht*1.02}Q${f.xn-4} ${CY-f.ht} ${f.xn} ${CY+2}Q${f.xn-8} ${CY+f.hb*.6} ${f.xn-34} ${CY+f.hb*.75}Z`,fill:shade(body,.75),stroke:shade(body,.45),sw:1.2});
    out.push({d:`M${f.xn-2} ${CY+2}L${f.xn-12} ${CY+7}L${f.xn-6} ${CY+3}Z M${f.xn-1} ${CY+1}L${f.xn-10} ${CY-2}`,fill:'#f4efe2',stroke:'#3a342c',sw:.6});}
  if(f.mouth)out.push({d:`M${f.xn} ${CY+2}Q${f.xn-8} ${CY+5} ${f.xn-14} ${CY+4}`,fill:'none',stroke:shade(body,.4),sw:1.4});
  if(f.jaw)out.push({d:`M${f.xn} ${CY-3}L${f.xn-14} ${CY+4}L${f.xn+1} ${CY+3}Z M${f.xn-4} ${CY+2}l-1 3l-1 -3Z M${f.xn-8} ${CY+3}l-1 3l-1 -3Z`,fill:'#f2ead6',stroke:shade(body,.4),sw:.6});
  if(f.barbel==='short')out.push({d:`M${f.xn-2} ${CY+2}q-2 6 -6 7`,fill:'none',stroke:shade(body,.5),sw:.9});
  if(f.barbel==='long')out.push({d:`M${f.xn-1} ${CY}q4 8 -10 16M${f.xn-1} ${CY+2}q6 4 -2 10M${f.xn-2} ${CY-2}q10 -8 2 -14`,fill:'none',stroke:shade(body,.45),sw:1});
  if(f.barbel==='chin')out.push({d:`M${f.xn-2} ${CY+1}l8 4M${f.xn-2} ${CY+1}l7 6`,fill:'none',stroke:shade(body,.45),sw:1});
  if(f.barbel==='under')out.push({d:`M${f.xn-12} ${CY+3}l-1 5M${f.xn-9} ${CY+3}l0 5M${f.xn-6} ${CY+2}l1 5`,fill:'none',stroke:shade(body,.45),sw:.8});
  if(f.scutes){let sc='';for(let i=0;i<8;i++){const x=f.xt+10+i*8;sc+=`M${x} ${CY-f.ht*.65}l3 -3l3 3l-3 2Z`;}out.push({d:sc,fill:shade(belly,.85),stroke:shade(body,.5),sw:.5});}
  const ex=f.xn-(f.bill?8:f.armor?14:10),ey=CY-(f.flat?6:f.ht*.32)-(f.up?2:0);
  out.push({d:`M${ex+3.4} ${ey}a3.4 3.4 0 1 0 -6.8 0a3.4 3.4 0 1 0 6.8 0Z`,fill:'#fbfbf4',stroke:'#1a1a1a',sw:.6});
  out.push({d:`M${ex+2.4} ${ey}a1.8 1.8 0 1 0 -3.6 0a1.8 1.8 0 1 0 3.6 0Z`,fill:'#141414'});
  if(f.flat)out.push({d:`M${ex-4} ${ey+6}a2.6 2.6 0 1 0 -5.2 0a2.6 2.6 0 1 0 5.2 0Z`,fill:'#141414'});
  return {parts:out,body:b};
}

function patternParts(sp,out,f){
  const pat=sp?.pat||'none',rnd=seeded(sp?.id||'x'),c=sp?.fin||'#345',bd=sp?.body||'#888';
  const xt=f.xt||10,xn=f.xn||110,L=xn-xt,top=CY-(f.ht||15)*1.3,bot=CY+(f.hb||15)*1.3,dark=shade(bd,.6);
  let d='';
  switch(pat){
    case'bands':for(let i=1;i<5;i++){const x=xt+L*i/5.4;d+=`M${F(x)} ${top}h${F(L*.06)}V${bot}h${F(-L*.06)}Z`;}out.push({d,fill:dark,clip:1,op:.45});break;
    case'bars':for(let i=1;i<9;i++){const x=xt+L*i/9.5;d+=`M${F(x)} ${top}h2.2V${bot}h-2.2Z`;}out.push({d,fill:dark,clip:1,op:.5});break;
    case'stripe':out.push({d:`M${xt} ${CY-2}L${xn} ${CY-3}V${CY+1}L${xt} ${CY+2}Z`,fill:c,clip:1,op:.75});break;
    case'spots':case'dots':for(let i=0;i<16;i++){const x=xt+6+rnd()*(L-14),y=CY-12+rnd()*22,r=1+rnd()*1.8;d+=`M${F(x+r)} ${F(y)}a${F(r)} ${F(r)} 0 1 0 ${F(-2*r)} 0a${F(r)} ${F(r)} 0 1 0 ${F(2*r)} 0Z`;}
      out.push({d,fill:pat==='dots'?'#ffffff':dark,clip:1,op:pat==='dots'?.8:.55});break;
    case'scales':for(let y=CY-14;y<=CY+14;y+=5)for(let x=xt+6+((y/5)%2?2.5:0);x<xn-12;x+=5)d+=`M${F(x)} ${y}a2.6 2.6 0 0 1 5 0`;
      out.push({d,fill:'none',stroke:shade(bd,.7),sw:.55,clip:1,op:.7});break;
    case'marble':for(let i=0;i<7;i++){const x=xt+8+rnd()*(L-20),y=CY-10+rnd()*18,r=3+rnd()*4;d+=`M${F(x)} ${F(y)}q${F(r)} ${F(-r)} ${F(2*r)} 0t${F(-r)} ${F(r)}t${F(-r)} ${F(-r)}Z`;}
      out.push({d,fill:dark,clip:1,op:.4});break;
    case'koi':for(let i=0;i<4;i++){const x=xt+10+rnd()*(L-30),y=CY-12+rnd()*12,r=5+rnd()*5;d+=`M${F(x)} ${F(y)}q${F(r)} ${F(-r*.6)} ${F(2*r)} ${F(r*.3)}q${F(-r*.4)} ${F(r)} ${F(-2*r)} ${F(r*.4)}Z`;}
      out.push({d,fill:c,clip:1,op:.9});break;
    case'clown':for(const k of[.32,.58,.82]){const x=xt+L*k;d+=`M${F(x)} ${top}h5V${bot}h-5Z`;}
      out.push({d,fill:'#ffffff',stroke:'#1f1f1f',sw:.8,clip:1});break;
    case'plates':for(let i=1;i<6;i++){const x=xt+L*i/6;d+=`M${F(x)} ${top}Q${F(x+4)} ${CY} ${F(x)} ${bot}`;}out.push({d,fill:'none',stroke:dark,sw:1,clip:1,op:.6});break;
    case'spikes':for(let i=0;i<14;i++){const a=i/14*Math.PI*2,cx=xt+L*.5,r=18;d+=`M${F(cx+Math.cos(a)*r)} ${F(CY+Math.sin(a)*r)}l${F(Math.cos(a)*5)} ${F(Math.sin(a)*5)}`;}
      out.push({d,fill:'none',stroke:dark,sw:1.1});break;
    case'trigger':d=`M${xt+L*.35} ${CY-4}L${xt+L*.75} ${CY-8}M${xt+L*.3} ${CY+2}L${xt+L*.7} ${CY-2}M${xt+L*.3} ${CY+8}L${xt+L*.65} ${CY+5}`;out.push({d,fill:'none',stroke:c,sw:1.6,clip:1});break;
    case'tips':break;
    case'manta':for(let i=0;i<5;i++){const x=40+rnd()*40,y=26+rnd()*10;d+=`M${F(x+2)} ${F(y)}a2 2 0 1 0 -4 0a2 2 0 1 0 4 0Z`;}out.push({d,fill:'#ffffff',clip:1,op:.75});break;
    case'saw':out.push({d:`M${xn-4} ${CY+3}a6 6 0 1 0 -10 6a4 4 0 1 1 6 -4`,fill:'none',stroke:'#f2ead6',sw:1.4});break;
    default:break;
  }
}

/** A hex colour mixed toward black (k < 1) or white (k > 1). */
export function shade(hex,k=.75){
  const m=/^#?([0-9a-f]{6})$/i.exec(String(hex||''));if(!m)return hex;
  const n=parseInt(m[1],16),ch=[n>>16&255,n>>8&255,n&255].map(v=>k<1?Math.round(v*k):Math.round(v+(255-v)*(k-1)));
  return '#'+ch.map(v=>Math.max(0,Math.min(255,v)).toString(16).padStart(2,'0')).join('');
}

let uid=0;
/** The SVG markup of a fish (`silhouette`: the uncaught shadow of Sổ cá). opts: {w, h, silhouette, glow, title}. */
export function fishSvg(sp,{w=120,h=60,silhouette=false,glow=true,title=''}={}){
  const {parts,body}=fishParts(sp),id=`fa${++uid}`,r=Number(sp?.r)||0,rc=RARITY_COLORS[r]||RARITY_COLORS[0];
  const fx=!silhouette&&glow&&r>=3?` filter="url(#${id}g)"`:'';
  let defs=`<clipPath id="${id}c"><path d="${body}"/></clipPath><linearGradient id="${id}b" x1="0" y1="0" x2="0" y2="1"><stop offset=".45" stop-color="${sp?.belly||'#ddd'}" stop-opacity="0"/><stop offset="1" stop-color="${sp?.belly||'#ddd'}" stop-opacity=".95"/></linearGradient>`;
  if(fx)defs+=`<filter id="${id}g" x="-30%" y="-40%" width="160%" height="180%"><feDropShadow dx="0" dy="0" stdDeviation="${r>=5?3.2:2.2}" flood-color="${rc}" flood-opacity="${r>=6?1:.85}"/></filter>`;
  const shapes=parts.map(p=>{
    if(silhouette&&(p.clip||p.fill==='belly'))return '';
    const fill=silhouette?(p.fill==='none'?'none':'#2b3a48'):p.fill==='belly'?`url(#${id}b)`:p.fill;
    const stroke=silhouette?(p.stroke&&p.fill==='none'?'#2b3a48':'none'):p.stroke||'none';
    return `<path d="${p.d}" fill="${fill}"${stroke!=='none'?` stroke="${stroke}" stroke-width="${p.sw||1}" stroke-linecap="round"`:''}${p.op!=null&&!silhouette?` opacity="${p.op}"`:''}${p.clip&&!silhouette?` clip-path="url(#${id}c)"`:''}/>`;
  }).join('');
  const shine=!silhouette&&r>=5?`<g fill="${r>=6?'#ffd0c0':'#fff6c2'}">${[[30,8],[96,10],[70,52],[16,40]].map(([x,y],i)=>`<path d="M${x} ${y-3}l1 2.4l2.6 .6l-2.6 .6l-1 2.4l-1-2.4l-2.6-.6l2.6-.6Z"><animate attributeName="opacity" values="0;1;0" dur="${1.6+i*.4}s" repeatCount="indefinite"/></path>`).join('')}</g>`:'';
  return `<svg class="fish-art${silhouette?' fish-sil':''}" viewBox="-6 -6 ${W+12} ${H+12}" width="${w}" height="${h}" role="img"${title?` aria-label="${String(title).replace(/"/g,'')}"`:' aria-hidden="true"'}><defs>${defs}</defs><g${fx}>${shapes}</g>${shine}</svg>`;
}

const PATHS=new Map();
const path2d=d=>{let p=PATHS.get(d);if(!p){p=new Path2D(d);if(PATHS.size>4000)PATHS.clear();PATHS.set(d,p);}return p;};
const CACHE=new Map();
/** Draw a fish on a canvas: centre (x, y), `len` px long, `angle` (rad, 0 = facing right), flip to face left.
 * opts: {flip, alpha, glow, silhouette, wiggle (0..1 tail sway)}. */
export function drawFish(ctx,sp,x,y,len,{angle=0,flip=false,alpha=1,glow=true,silhouette=false,wiggle=0}={}){
  if(!ctx||!sp)return;
  let built=CACHE.get(sp.id||sp.fam);if(!built){built=fishParts(sp);CACHE.set(sp.id||sp.fam,built);}
  const k=len/W,r=Number(sp.r)||0;
  ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,y);ctx.rotate(angle);if(flip)ctx.scale(-1,1);ctx.scale(k,k);ctx.translate(-W/2,-CY);
  if(wiggle){ctx.transform(1,Math.sin(wiggle*6.283)*.05,0,1,0,0);}
  if(glow&&!silhouette&&r>=3){ctx.shadowColor=RARITY_COLORS[r];ctx.shadowBlur=(r>=5?14:9)*Math.max(.6,Math.min(2,1/k*.3));}
  const body=path2d(built.body);
  for(const p of built.parts){
    if(silhouette&&(p.clip||p.fill==='belly'))continue;
    const P=path2d(p.d);ctx.globalAlpha=alpha*(p.op!=null&&!silhouette?p.op:1);
    if(p.clip){ctx.save();ctx.clip(body);}
    if(p.fill&&p.fill!=='none'){
      if(p.fill==='belly'){const g=ctx.createLinearGradient(0,CY-15,0,CY+18);g.addColorStop(.45,hexA(sp.belly,0));g.addColorStop(1,hexA(sp.belly,.95));ctx.fillStyle=g;}
      else ctx.fillStyle=silhouette?'#2b3a48':p.fill;
      ctx.fill(P);
      if(p.body)ctx.shadowBlur=0;
    }
    if(p.stroke&&!(silhouette&&p.fill!=='none')){ctx.strokeStyle=silhouette?'#2b3a48':p.stroke;ctx.lineWidth=p.sw||1;ctx.lineCap='round';ctx.stroke(P);}
    if(p.clip)ctx.restore();
  }
  ctx.restore();
}
function hexA(hex,a){const m=/^#?([0-9a-f]{6})$/i.exec(String(hex||''));if(!m)return `rgba(220,220,220,${a})`;const n=parseInt(m[1],16);return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`;}

/** The size a carried fish shows at on the walk maps (px of a ~32 px tall character): rarer = bigger. */
export function carrySize(r,kg){return Math.round(Math.min(34,10+Number(r||0)*3+Math.log10(1+Number(kg||0))*3));}

/** "1,2 kg" / "350 g" / "2,5 tấn" (game/fishing.py fmt_kg). */
export function fmtKg(g){
  const kg=Number(g||0)/1000;
  if(kg>=1000)return `${String(+(kg/1000).toFixed(2)).replace('.',',')} tấn`;
  if(kg>=100)return `${Math.round(kg)} kg`;
  if(kg>=1)return `${String(+kg.toFixed(1)).replace('.',',')} kg`;
  return `${Math.round(Number(g||0))} g`;
}
