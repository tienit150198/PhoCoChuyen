/** Cấp hiệu, huy hiệu and the uniform of an org ladder (game/org_content.py `ins`; owner to review the art).
 * One painter for both pens of look.js (CANVAS on the scenes, SVG on the cards), so the rank card, the workplace and
 * the live street always match. Generic `ins` keys, any org may use them:
 *   base 'nco'|'officer'|'general'  board colour · v chevrons · h straight stripes · b long bars · s stars · big one big star
 *   GRADES       grade id → ins (a copy of org_content CAND_GRADES; tests/test_org_police.py compares them)
 *   boardSVG()   a shoulder board (the rank card)            badgeSVG()  the CAND badge (huy hiệu)
 *   paintRank()  boards + chest badge on a figure (pen K)    paintCap()  the peaked cap with the badge (on shift) */
export const GRADES={cand:{binh_nhi:{base:'nco',v:1},binh_nhat:{base:'nco',v:2},ha_si:{base:'nco',h:1},trung_si:{base:'nco',h:2},
  thuong_si:{base:'nco',h:3},thieu_uy:{base:'officer',b:1,s:1},trung_uy:{base:'officer',b:1,s:2},thuong_uy:{base:'officer',b:1,s:3},
  dai_uy:{base:'officer',b:1,s:4},thieu_ta:{base:'officer',b:2,s:1},trung_ta:{base:'officer',b:2,s:2},thuong_ta:{base:'officer',b:2,s:3},
  dai_ta:{base:'officer',b:2,s:4},thieu_tuong:{base:'general',big:1,s:1}}};
/* The game's own palette for Công an phường Mây (owner 07/10: "cho khác màu xíu", not the real red/yellow): deep teal
 * boards with a darker edge, silver stripes and chevrons, pale gold stars; enlisted and NCOs on a lighter teal; the
 * NPC-only general on warm bronze. [fill, edge] per base. */
const BASE={nco:['#2f7f80','#1b5254'],officer:['#1d5a5f','#0f3a3e'],general:['#b07a3c','#6c4720']};
const MARK={nco:'#dfe5ea',officer:'#c9d1d8',general:'#f4e7c2'};   // silver on teal, cream on bronze
const STAR='#f3e2a4',STAR_EDGE='#6a5a2c',UNI='#6f8455',UNI_D='#55693f',BAND='#1d5a5f',VISOR='#26221f';
export const CAP_GOLD='#e7d59a';
const starPts=(cx,cy,r)=>Array.from({length:10},(_,i)=>{const a=Math.PI/5*i-Math.PI/2,rr=i%2?r*.45:r;return [cx+rr*Math.cos(a),cy+rr*Math.sin(a)];});
/** The grade's insignia from a rank ref {o, g} (o: org id, g: grade id) or an `ins` object itself. */
export const insOf=rk=>rk?.base?rk:(GRADES[rk?.o]?.[rk?.g]||null);

/** One shoulder board, lying along x (the button at the neck end `inner`: -1 left, +1 right). */
export function board(c,K,ins,x,y,w,h,inner=-1){
  const [fill,edge]=BASE[ins.base]||BASE.officer,mark=MARK[ins.base]||MARK.officer;
  K.R(c,x,y,w,h,edge,h/2);K.R(c,x+.6,y+.6,w-1.2,h-1.2,fill,h/2);
  const bx=inner<0?x+h*.55:x+w-h*.55;K.E(c,bx,y+h/2,h*.22,h*.22,edge);   // the button
  const x0=inner<0?x+h*1.05:x+h*.35,x1=inner<0?x+w-h*.35:x+w-h*1.05,len=x1-x0,cy=y+h/2;
  if(ins.b){const gap=h/(ins.b+1);for(let i=1;i<=ins.b;i++)K.L(c,x0,y+gap*i,x1,y+gap*i,mark,Math.max(.6,h*.11));}
  if(ins.v){for(let i=0;i<ins.v;i++){const px=x0+len*(.32+i*.26),d=h*.28*-inner;K.L(c,px-d,y+h*.22,px+d*.2,cy,mark,h*.13);K.L(c,px+d*.2,cy,px-d,y+h*.78,mark,h*.13);}}
  if(ins.h){for(let i=0;i<ins.h;i++){const px=(inner<0?x1:x0)+(inner<0?-1:1)*(h*.2+i*h*.28);K.L(c,px,y+h*.18,px,y+h*.82,mark,h*.14);}}
  if(ins.big){K.P(c,starPts(x0+len*.55,cy,h*.42),STAR_EDGE);K.P(c,starPts(x0+len*.55,cy,h*.34),'#fff6d0');return;}
  if(ins.s){const r=Math.min(h*.26,len/(ins.s*2.4));for(let i=0;i<ins.s;i++){const px=x0+len*(i+.5)/ins.s;K.P(c,starPts(px,cy,r*1.25),STAR_EDGE);K.P(c,starPts(px,cy,r),STAR);}}
}
/** The ward's emblem (huy hiệu Công an phường Mây): the badge's shape in the game's palette: a pale-gold ring, a teal
 * disc, a cream star, two silver ears of rice. */
export function badge(c,K,x,y,r){
  K.E(c,x,y,r,r,'#8a7640');K.E(c,x,y,r*.86,r*.86,CAP_GOLD);K.E(c,x,y,r*.66,r*.66,BAND);
  K.P(c,starPts(x,y-r*.04,r*.48),'#f7ecc6');
  for(const s of [-1,1])for(let i=0;i<3;i++){const a=Math.PI*(.62+i*.13),px=x+s*Math.cos(a)*r*.76*-1,py=y+Math.sin(a)*r*.76;K.E(c,px,py,r*.11,r*.17,'#dfe5ea');}
}
/** Boards on both shoulders and the badge on the chest (the figure's coordinates of look.js: shoulders at y≈-52). */
export function paintRank(c,F,K,full=false){
  const ins=insOf(F.rk);if(!ins)return;
  if(full){K.R(c,-23,-52,46,36,UNI,15);K.L(c,0,-50,0,-18,UNI_D,1.2);K.R(c,-18,-40,11,8,UNI_D,2);K.R(c,7,-40,11,8,UNI_D,2);K.P(c,[[-9,-53],[0,-45],[9,-53]],'#e9ead8');K.P(c,[[-3,-49],[3,-49],[1.5,-38],[-1.5,-38]],BAND);}
  board(c,K,ins,-31,-50,18,7,1);board(c,K,ins,13,-50,18,7,-1);
  badge(c,K,-12,-36,4.2);
}
/** The peaked cap (on shift only: it sits over the hair). */
export function paintCap(c,F,K){
  K.R(c,-30,-126,60,22,UNI,11);K.R(c,-31,-108,62,8,BAND,4);K.E(c,0,-101,30,5,VISOR);badge(c,K,0,-114,6.5);
}

/* ---- SVG for the cards (the SVG pen of look.js, local copy to keep this module free of imports) ---- */
const n1=v=>Math.round(v*10)/10;
const PEN={R:(c,x,y,w,h,f,r=0)=>c.push(`<rect x="${n1(x)}" y="${n1(y)}" width="${n1(w)}" height="${n1(h)}" rx="${n1(Math.min(r,w/2,h/2))}" fill="${f}"/>`),
  E:(c,x,y,rx,ry,f)=>c.push(`<ellipse cx="${n1(x)}" cy="${n1(y)}" rx="${n1(rx)}" ry="${n1(ry)}" fill="${f}"/>`),
  L:(c,x,y,x2,y2,col,w=2)=>c.push(`<line x1="${n1(x)}" y1="${n1(y)}" x2="${n1(x2)}" y2="${n1(y2)}" stroke="${col}" stroke-width="${n1(w)}" stroke-linecap="round"/>`),
  P:(c,pts,f)=>c.push(`<polygon points="${pts.map(([x,y])=>n1(x)+','+n1(y)).join(' ')}" fill="${f}"/>`)};
export function boardSVG(ins,w=96,label=''){
  const x=insOf(ins);if(!x)return '';const out=[];board(out,PEN,x,1,1,98,34,-1);
  return `<svg class="og-board" viewBox="0 0 100 36" width="${w}" height="${Math.round(w*.36)}" ${label?`role="img" aria-label="${label}"`:'aria-hidden="true"'}>${out.join('')}</svg>`;
}
export function badgeSVG(size=28,label='Huy hiệu Công an phường Mây'){
  const out=[];badge(out,PEN,20,20,19);
  return `<svg class="og-badge" viewBox="0 0 40 40" width="${size}" height="${size}" role="img" aria-label="${label}">${out.join('')}</svg>`;
}
