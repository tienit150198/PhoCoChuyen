/** 🪴 Bày trí phòng: the drawings (pure SVG strings, no DOM). game/deco_content.py has the rules; this file only
 * draws: a room seen from the front and a little from above (back wall with its grid of hanging spots, the floor in
 * rows from the wall to the front), the fixtures (window with day or night sky, door, kitchen counter, the attic's
 * roof, the gác lửng's ladder, the dorm's bunk) and 65 pieces of furniture, each a small hand-made drawing.
 * Every colour is an attribute (no stylesheet needed), so the same markup becomes a photo (reno.js → canvas).
 * A piece is drawn from its footprint's front-left corner: x to the right, y up (negative). Wall pieces from the
 * top-left corner of their wall cells.
 * Bảng màu: a piece may wear a colour of the player's palette (state.colors.deco[uid], game/wardrobe.py): TINT says which
 * of its own colours take the chosen one (its main part: the sofa's fabric, a pot, a frame…), see `tinted`. */
import {PALETTE} from './look.js';

export const CW=40,FR=30,WR=34,PX=14,CEIL=10,TOP=12,BASE=28;
const OL='#5b4535';
const P={wood:'#d9a066',woodD:'#b47a45',woodL:'#ecc28f',cream:'#fff6e6',white:'#fffdf8',pink:'#f5a9bc',pinkL:'#fcd3dd',pinkD:'#e0839b',
  mint:'#a8e0c8',mintD:'#7cc4a8',mintL:'#d3f1e4',sky:'#a9d6f5',skyD:'#7fb8e0',skyL:'#d6ecfb',butter:'#ffe08a',butterD:'#f2c45a',
  lilac:'#cdb8f0',lilacD:'#a993d8',lilacL:'#e6dcf8',peach:'#ffc9a3',peachD:'#f4a77a',red:'#ef7f72',redD:'#d45f55',grey:'#d9d2c8',greyD:'#a39a90',
  dark:'#3d3a4a',darkL:'#5a566b',leaf:'#7cc47f',leafD:'#4f9a5a',leafL:'#a8dc9a',pot:'#e08e64',potD:'#c26f4a',gold:'#f2c14e',navy:'#4b5a8a'};
const n=v=>Math.round(v*10)/10;
const R=(x,y,w,h,fill,rx=3,sw=1.5)=>`<rect x="${n(x)}" y="${n(y)}" width="${n(w)}" height="${n(h)}" rx="${rx}" fill="${fill}"${sw?` stroke="${OL}" stroke-width="${sw}"`:''}/>`;
const Rn=(x,y,w,h,fill,rx=0,op=1)=>`<rect x="${n(x)}" y="${n(y)}" width="${n(w)}" height="${n(h)}" rx="${rx}" fill="${fill}"${op<1?` opacity="${op}"`:''}/>`;
const C=(cx,cy,r,fill,sw=1.5)=>`<circle cx="${n(cx)}" cy="${n(cy)}" r="${n(r)}" fill="${fill}"${sw?` stroke="${OL}" stroke-width="${sw}"`:''}/>`;
const E=(cx,cy,rx,ry,fill,sw=1.5,extra='')=>`<ellipse cx="${n(cx)}" cy="${n(cy)}" rx="${n(rx)}" ry="${n(ry)}" fill="${fill}"${sw?` stroke="${OL}" stroke-width="${sw}"`:''}${extra}/>`;
const Pa=(d,fill,sw=1.5,extra='')=>`<path d="${d}" fill="${fill}"${sw?` stroke="${OL}" stroke-width="${sw}" stroke-linejoin="round"`:''}${extra}/>`;
const L=(d,color=OL,w=1.5,extra='')=>`<path d="${d}" fill="none" stroke="${color}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"${extra}/>`;
const shine=(x,y,w,h)=>Rn(x,y,w,h,'#fff',2,.45);
const blush=(x,y)=>E(x,y,2.4,1.5,'#f59bb0',0,' opacity=".8"');
const eyes=(x1,x2,y,r=1.4)=>C(x1,y,r,OL,0)+C(x2,y,r,OL,0);
/** A 3/4 box: the top face (depth td) over the front face (height fh), lifted `lift` above the floor. */
const box=(x,w,lift,fh,td,front,top,rx=3)=>R(x,-lift-fh-td,w,td+3,top,rx)+R(x,-lift-fh,w,fh,front,rx);
const legs=(xs,y0,h,c=P.woodD,w=4)=>xs.map(x=>R(x,y0,w,h,c,1.5,1.2)).join('');
const shadow=(W,D)=>E(W/2,-D*.32,W*.46,Math.min(9,D*.3),'#000',0,' opacity=".1"');
const pot=(cx,w=22,h=16,c=P.pot,cd=P.potD)=>Pa(`M${cx-w/2} ${-h}h${w}l-3 ${h-2}q0 2-2 2h${-w+10}q-2 0-2-2z`,c)+Rn(cx-w/2+1,-h,w-2,3,cd,1);
const leafE=(cx,cy,rx,ry,rot,c=P.leaf)=>`<ellipse cx="${n(cx)}" cy="${n(cy)}" rx="${rx}" ry="${ry}" fill="${c}" stroke="${OL}" stroke-width="1.3" transform="rotate(${rot} ${n(cx)} ${n(cy)})"/>`;
const note=(x,y,c=P.lilacD)=>Pa(`M${x} ${y}v-9l6-2v9`,'none',1.4)+C(x-1.5,y,2,c,1)+C(x+4.5,y-2,2,c,1);

/* ---------------------------------------------------------------- the pieces
 * d(W,D): the drawing for a footprint W px wide, D px deep (wall: W × H of its cells). h: how tall it stands (thumbs).
 * g: where it glows at night [cx, cy, r]. */
export const ART={
  sofa:{h:60,d:(W)=>shadow(W,30)+legs([8,W-12],-8,8)+R(6,-58,W-12,32,P.pinkD,12)+R(10,-54,W/2-12,24,P.pink,9)+R(W/2+2,-54,W/2-12,24,P.pink,9)
    +box(2,W-4,6,16,10,P.pinkD,P.pinkL,6)+R(0,-44,16,38,P.pink,7)+R(W-16,-44,16,38,P.pink,7)+C(W/2-14,-42,7,P.butter)+L(`M${W/2-17} -44l3 3l3-3`,OL,1.1)},
  ban_tra:{h:26,d:(W)=>shadow(W,30)+legs([8,W-12],-14,14)+box(2,W-4,12,6,10,P.woodD,P.woodL,4)+shine(10,-26,W-24,2)},
  giuong:{h:96,d:(W,D)=>shadow(W,D)+legs([4,W-8],-6,6)+R(2,-D-34,W-4,32,P.woodD,12)+R(10,-D-28,W-20,20,P.wood,8)
    +R(2,-D-4,W-4,D-6,P.white,6)+E(W*.3,-D+2,16,7,P.cream)+E(W*.66,-D+2,16,7,P.cream)
    +Pa(`M4 ${-D*0.62}q${W/2-4} -8 ${W-8} 0v${D*0.62-14}h${-(W-8)}z`,P.sky)+[0.2,0.4,0.6,0.8].map(t=>C(W*t,-D*0.36,2,P.skyL,0)).join('')
    +R(2,-14,W-4,10,P.wood,3)},
  tv:{h:66,d:(W)=>shadow(W,30)+box(4,W-8,0,16,8,P.woodD,P.woodL)+C(W/2,-9,1.6,P.cream,1)+R(W/2-3,-30,6,6,P.dark,1,1)
    +R(8,-66,W-16,38,P.dark,5)+R(12,-62,W-24,30,'#7ec8e3',3,0)+Pa(`M14 -36l10-12l8 7l9-12l${W-62} 17z`,'#a8e0f0',0)+C(W-24,-54,4,P.butter,0)},
  be_ca:{h:64,d:(W)=>shadow(W,30)+box(4,W-8,0,16,8,P.woodD,P.woodL)+R(6,-64,W-12,40,'#bfe7f7',5)+Rn(8,-56,W-16,30,'#8fd2ef',3,.75)
    +Pa('M18 -26q-4-12 2-18q2 10 2 18','#7cc47f',1)+Pa(`M${W-20} -26q-5-10 0-16q4 8 3 16`,P.leafD,1)
    +E(30,-44,7,4,P.peachD,1.2)+Pa('M23 -44l-6-4v8z',P.peachD,1.2)+C(32,-45,.9,OL,0)+E(W-30,-36,6,3.5,P.butterD,1.2)+Pa(`M${W-24} -36l5-3v6z`,P.butterD,1.2)
    +C(40,-56,2,'#fff',.8)+C(44,-50,1.4,'#fff',.8)+shine(10,-62,4,22)},
  ke_sach:{h:88,d:(W)=>shadow(W,30)+R(4,-88,W-8,88,P.woodD,4)+Rn(8,-84,W-16,80,P.wood,2)+R(6,-60,W-12,4,P.woodD,1,1)+R(6,-32,W-12,4,P.woodD,1,1)
    +[[10,-82,7,22,P.red],[18,-80,6,20,P.sky],[25,-84,8,24,P.butter],[34,-78,6,18,P.mint],[50,-82,12,6,P.lilac],[50,-76,12,6,P.pink],
      [10,-54,6,22,P.lilac],[17,-52,7,20,P.peach],[25,-55,6,23,P.mintD],[44,-50,16,18,P.skyD],[12,-26,22,6,P.red],[12,-20,22,6,P.butterD],[44,-28,7,24,P.pink],[52,-26,7,22,P.sky]]
      .filter(b=>b[0]+b[2]<W-6).map(b=>R(b[0],b[1],b[2],b[3],b[4],1.5,1.1)).join('')},
  ban_lam_viec:{h:34,d:(W)=>shadow(W,30)+legs([6,W-10],-22,22)+box(2,W-4,20,6,10,P.woodD,P.woodL,3)+R(W-30,-20,24,10,P.wood,2)+C(W-18,-15,1.6,P.cream,1)},
  dan:{h:76,d:()=>L('M10 0l10-14l10 14',P.woodD,2)+R(18,-74,4,40,P.woodD,1.5)+R(16,-78,8,8,P.dark,2)+C(20,-24,10,P.peachD)+C(20,-38,7.5,P.peachD)
    +Rn(14,-38,12,16,P.peachD)+C(20,-30,3.5,P.dark,1)+L('M19 -70v52M21 -70v52',P.cream,.6)+R(15,-18,10,3,P.woodD,1,1)},
  gau_bong:{h:28,top:1,d:()=>E(20,-8,10,8,P.peach)+C(12,-4,3.5,P.peach)+C(28,-4,3.5,P.peach)+C(13,-22,4,P.peach)+C(27,-22,4,P.peach)+C(20,-17,8.5,P.peach)
    +E(20,-14,4,3,P.cream,1)+eyes(16.5,23.5,-18)+C(20,-15,1.2,OL,0)+blush(14,-14)+blush(26,-14)+E(20,-7,4,3.5,P.cream,0)},
  cay_canh:{h:58,d:()=>shadow(40,30)+leafE(13,-38,6,13,-30)+leafE(27,-40,6,13,30)+leafE(20,-48,6,14,0,P.leafL)+leafE(10,-26,5,10,-60,P.leafD)+leafE(30,-26,5,10,60,P.leafD)+pot(20)},
  ghe_may:{h:48,d:()=>shadow(40,30)+legs([8,28],-10,10)+E(20,-32,15,16,P.woodL)+Pa('M10 -32q10-12 20 0M8 -24q12-10 24 0M12 -40q8-8 16 0','none',1)
    +box(5,30,8,5,6,P.wood,P.woodL,4)},
  tu_lanh:{h:84,d:()=>shadow(40,30)+R(4,-84,32,84,P.mintL,6)+L('M4 -54h32')+R(29,-78,3,14,P.greyD,1.5,1)+R(29,-48,3,18,P.greyD,1.5,1)
    +Pa('M14 -70q-3-4 0-6q2-1 3 1q1-2 3-1q3 2 0 6l-3 3z',P.pink,1)+R(10,-40,8,6,P.butter,1,1)+shine(7,-80,3,22)},
  ban_an:{h:34,d:(W)=>shadow(W,30)+legs([6,W-10],-22,22)+box(2,W-4,20,6,10,P.woodD,P.woodL,3)+Pa(`M10 -36h${W-20}l-3 10h${-(W-26)}z`,P.pinkL,1.1)
    +[16,28,40,52].filter(x=>x<W-14).map(x=>C(x,-30,1.3,P.pink,0)).join('')},
  noi_com:{h:26,top:1,d:()=>E(20,-3,13,3,'#000',0,' opacity=".1"')+R(8,-18,24,18,P.white,7)+Pa('M7 -18q13-10 26 0z',P.pink)+C(20,-24,2.5,P.pinkD,1.2)
    +R(15,-10,10,4,P.pinkL,2,1)+L('M14 -30q-3-4 0-8M22 -32q-3-4 0-8',P.greyD,1.1,' opacity=".7"')},
  may_giat:{h:58,d:()=>shadow(40,30)+R(3,-58,34,58,P.white,6)+R(3,-58,34,12,P.grey,6)+C(11,-52,2,P.mint,1)+C(18,-52,2,P.pink,1)+R(24,-54,10,4,P.dark,1.5,1)
    +C(20,-24,12,P.greyD)+C(20,-24,9,'#bfe7f7',1.2)+Pa('M13 -22q7-6 14 0q-7 7-14 0z','#8fd2ef',0)+shine(14,-30,4,3)},
  hoa_giay:{h:52,d:()=>shadow(40,30)+leafE(12,-30,6,10,-35,P.leafD)+leafE(28,-30,6,10,35,P.leafD)
    +[[12,-40],[22,-46],[30,-38],[18,-34],[26,-28],[8,-30],[32,-26]].map(([x,y])=>C(x,y,5.5,'#e85fa8',1.1)+C(x,y,1.6,P.butter,0)).join('')+pot(20,22,16)},
  ban_ngoai:{h:96,d:(W)=>shadow(W,30)+R(W/2-2,-86,4,70,P.greyD,1,1)+legs([10,W-14],-14,14,P.greyD)+box(4,W-8,12,5,9,P.greyD,P.white,4)
    +Pa(`M${W/2-40} -74q40-30 80 0z`,P.red)+Pa(`M${W/2-14} -74q14-28 28 0z`,P.cream,1.2)+C(W/2,-92,2.5,P.red,1.2)},
  tranh:{h:34,wall:1,d:(W,H)=>R(4,3,W-8,H-8,P.woodD,3)+Rn(8,7,W-16,H-16,'#cfe9f7',1)+Pa(`M8 ${H-9}q${W*.2} -14 ${W*.38} -6q${W*.15} -12 ${W*.4} 1v5h${-(W-16)}z`,P.leaf,0)
    +Pa(`M8 ${H-9}q${W*.3} -8 ${W*.6} -2q${W*.1} -3 ${W*.26} 0v2h${-(W-16)}z`,P.leafD,0)+C(W-20,13,4,P.butter,0)+L(`M${W/2-6} 3l6-4l6 4`,OL,1.1)},
  den_long:{h:34,wall:1,g:(W,H)=>[W/2,H/2+2,30],d:(W)=>L(`M${W/2} 0v6`)+R(W/2-5,5,10,3,P.gold,1,1)+E(W/2,17,11,10,P.redD)+L(`M${W/2-5} 8q-3 9 0 18M${W/2+5} 8q3 9 0 18`,'#b8473f',1.1)
    +R(W/2-5,26,10,3,P.gold,1,1)+L(`M${W/2-2} 29v4M${W/2} 29v5M${W/2+2} 29v4`,P.gold,1.2)+shine(W/2-7,12,2,7)},
  den_nhay:{h:34,wall:1,g:(W,H)=>[W/2,14,W*.6],d:(W)=>{const pts=[],c=[P.butter,P.pink,P.mint,P.sky,P.lilac,P.peach];
    for(let i=0;i<=7;i++){const t=i/7,x=4+t*(W-8),y=5+Math.sin(t*Math.PI)*14;pts.push([x,y]);}
    return L(`M4 5q${W/2-4} 32 ${W-8} 0`,'#7a6a58',1.2)+pts.slice(1,-1).map(([x,y],i)=>R(x-1.5,y-1,3,3,'#7a6a58',.5,0)+E(x,y+5,3,4.2,c[i%c.length],1.1)).join('')+C(4,5,1.8,OL,0)+C(W-4,5,1.8,OL,0);}},
  dong_ho:{h:34,wall:1,d:(W)=>C(W/2,17,13,P.cream,2)+C(W/2,17,10.5,P.white,1)+[0,90,180,270].map(a=>{const r=a*Math.PI/180;return C(W/2+Math.sin(r)*8,17-Math.cos(r)*8,1,OL,0);}).join('')
    +L(`M${W/2} 17v-7M${W/2} 17l5 3`,OL,1.6)+C(W/2,17,1.4,P.red,0)},
  guong:{h:34,wall:1,d:(W)=>C(W/2,17,14,P.woodL,2)+C(W/2,17,10.5,'#dff1fb',1.2)+L(`M${W/2-5} 13l5-5M${W/2-4} 19l8-8`,'#fff',2)+C(W/2,3,1.6,P.gold,1)},
  ke_cay:{h:34,wall:1,d:(W)=>R(3,22,W-6,4,P.woodD,1.5,1.2)+L(`M8 26v6M${W-8} 26v6`,P.woodD,1.5)+`<g transform="translate(0 22)">${pot(W/2,14,10)}</g>`+leafE(W/2-6,8,4,8,-30)+leafE(W/2+6,8,4,8,30)+leafE(W/2,5,4,8,0,P.leafL)
    +L(`M${W/2-7} 22q-5 6-2 11M${W/2+7} 22q6 5 2 10`,P.leafD,1.5)+leafE(W/2-9,31,2.5,4,20,P.leafD)+leafE(W/2+9,31,2.5,4,-20,P.leafD)},
  anh:{h:34,wall:1,d:(W)=>R(W/2-12,4,24,26,P.white,3)+Rn(W/2-9,7,18,15,P.skyL,1)+C(W/2-4,13,3,P.peach,1)+C(W/2+4,13,3,P.peach,1)+Rn(W/2-7,16,6,6,P.pink,2)+Rn(W/2+1,16,6,6,P.sky,2)
    +Pa(`M${W/2} 27q-3-2-3-4q0-2 3-1q3-1 3 1q0 2-3 4z`,P.red,0)+L(`M${W/2-6} 4l6-4l6 4`,OL,1.1)},
  lich:{h:34,wall:1,d:(W)=>R(W/2-12,4,24,28,P.white,2)+Rn(W/2-12,4,24,8,P.red,2)+R(W/2-12,4,24,28,'none',2)+C(W/2-6,4,1.8,P.greyD,1)+C(W/2+6,4,1.8,P.greyD,1)
    +[0,1,2].map(r=>[0,1,2,3].map(c=>Rn(W/2-9+c*5,15+r*5,3,3,c===2&&r===1?P.red:P.greyD,1)).join('')).join('')},
  may_lanh:{h:34,wall:1,d:(W)=>R(4,5,W-8,20,P.white,8)+L(`M10 20h${W-20}M10 23h${W-20}`,P.greyD,1)+C(W-14,11,1.6,'#62d26f',0)+L(`M16 30q3 3 0 6M${W/2} 30q3 3 0 6M${W-16} 30q3 3 0 6`,P.skyD,1.2,' opacity=".8"')},
  ke_bep:{h:34,wall:1,d:(W)=>R(3,24,W-6,4,P.woodD,1.5,1.2)+[[8,P.red],[20,P.butterD],[32,P.leafD],[44,P.peachD],[56,P.lilacD]].filter(([x])=>x<W-14)
    .map(([x,c])=>R(x,12,10,12,'#f4f1ea',2,1.1)+R(x-.5,9,11,4,c,1.5,1.1)).join('')},
  tu_quan_ao:{h:94,d:(W)=>shadow(W,30)+legs([6,W-10],-6,6)+R(3,-92,W-6,86,P.woodL,5)+L(`M${W/2} -88v78`)+R(W/2-7,-56,3,12,P.woodD,1.5,1)+R(W/2+4,-56,3,12,P.woodD,1.5,1)
    +R(1,-96,W-2,8,P.woodD,3)+Pa(`M${W/2-8} -88q8 -8 16 0`,'none',1.2)+R(10,-30,W/2-16,12,P.wood,3,1)+R(W/2+6,-30,W/2-16,12,P.wood,3,1)},
  nem:{h:30,d:(W,D)=>shadow(W,D)+R(2,-D,W-4,D-2,P.cream,8)+R(2,-12,W-4,10,P.grey,5)+Pa(`M4 ${-D*0.55}q${W/2} -8 ${W-8} 0v${D*0.55-12}h${-(W-8)}z`,P.lilac)
    +[.25,.5,.75].map(t=>C(W*t,-D*0.3,1.8,P.lilacL,0)).join('')+E(W*.3,-D+4,13,5,P.white)},
  tu_dau_giuong:{h:30,d:()=>shadow(40,30)+box(5,30,0,20,8,P.wood,P.woodL)+L('M7 -10h26')+C(20,-15,1.6,P.cream,1)+C(20,-5,1.6,P.cream,1)},
  ke_go:{h:30,d:()=>shadow(40,30)+box(4,32,0,22,7,P.woodD,P.woodL)+Rn(8,-19,24,16,'#8a5d34',2)+R(11,-18,4,15,P.red,1,1)+R(15,-16,4,13,P.sky,1,1)+R(19,-17,4,14,P.butter,1,1)},
  goi_om:{h:22,top:1,d:()=>E(20,-3,13,3,'#000',0,' opacity=".1"')+Pa('M9 -16l2-6l4 3M31 -16l-2-6l-4 3',P.greyD,1.3)+R(7,-18,26,17,P.grey,8)
    +eyes(15.5,24.5,-11,1.3)+L('M18.5 -8q1.5 1.5 3 0',OL,1)+blush(13,-8)+blush(27,-8)+L('M8 -9h-3M8 -7l-3 1M32 -9h3M32 -7l3 1',OL,.8)},
  rem_giuong:{h:68,wall:1,d:(W,H)=>R(0,1,W,3,P.woodD,1.5,1.1)+Pa(`M3 4h${W-6}v${H-12}q${-(W-6)/2} 8 ${-(W-6)} 0z`,P.pink)+L(`M12 6v${H-14}M20 6v${H-12}M28 6v${H-14}`,P.pinkD,1)
    +Pa(`M3 ${H/2}q${W/2-3} 6 ${W-6} 0`,'none',2.2,' stroke="#f2c14e"')+C(W/2,H/2+3,3,P.butter,1)},
  tham:{h:20,rug:1,d:(W,D)=>E(W/2,-D/2,W/2-4,D/2-4,P.lilacD,0)+E(W/2,-D/2-2,W/2-5,D/2-5,P.lilac)+E(W/2,-D/2-2,W/2-18,D/2-12,P.lilacL,1,' stroke-dasharray="3 3"')
    +Array.from({length:12},(_,i)=>{const a=i/12*Math.PI*2;return C(W/2+Math.cos(a)*(W/2-4),-D/2-2+Math.sin(a)*(D/2-4),1.3,P.lilacL,0);}).join('')},
  tham_hoa:{h:14,rug:1,d:(W,D)=>R(4,-D+6,W-8,D-10,P.peach,8)+R(9,-D+10,W-18,D-18,P.cream,5,1)+[W*.32,W*.5,W*.68].map(x=>C(x,-D/2,3,P.pink,1)+C(x,-D/2,1.2,P.butter,0)).join('')},
  ban_hoc:{h:34,d:(W)=>shadow(W,30)+legs([5],-22,22)+R(W-26,-22,22,22,P.woodL,2)+L(`M${W-26} -11h22`)+C(W-15,-16,1.4,P.woodD,0)+C(W-15,-5,1.4,P.woodD,0)
    +box(2,W-4,20,5,10,P.wood,P.butter,3)+shine(10,-34,W-30,2)},
  ghe_hoc:{h:50,d:()=>shadow(40,30)+L('M20 -16v-6M8 -2l12-8l12 8M20 -10v8',P.dark,2.4)+C(8,-2,2,P.dark,0)+C(32,-2,2,P.dark,0)+C(20,-1,2,P.dark,0)
    +R(10,-50,20,24,P.mintD,7)+box(7,26,20,5,6,P.mintD,P.mint,4)},
  ghe_luoi:{h:34,d:()=>shadow(40,30)+Pa('M4 -4q-4-26 16-30q20 4 16 30q-16 6-32 0z',P.butter)+E(14,-24,5,3,'#fff',0,' opacity=".45"')+eyes(15,25,-14,1.5)+L('M18 -10q2 2 4 0',OL,1.2)+blush(11,-10)+blush(29,-10)},
  ban_xep:{h:20,d:()=>shadow(40,30)+L('M10 -2l6-10M30 -2l-6-10',P.woodD,2.2)+box(4,32,10,4,7,P.woodD,P.woodL,3)},
  ghe_dau:{h:22,d:()=>shadow(40,30)+Pa('M10 0l3-16h14l3 16h-4l-2-8h-8l-2 8z',P.red)+E(20,-17,11,4,P.red)+E(20,-17,5,1.6,P.redD,0)},
  ban_gaming:{h:62,d:(W)=>shadow(W,30)+L(`M8 0l6-20M${W-8} 0l-6-20`,P.dark,3)+box(2,W-4,20,6,10,P.dark,P.darkL,3)+Rn(4,-22,W-8,2,'#ff6bd6')+Rn(4,-22,(W-8)/2,2,'#6bd6ff')
    +R(W/2-20,-62,40,24,P.dark,4)+Rn(W/2-17,-59,34,18,'#6b5bd6',2)+Pa(`M${W/2-14} -44l8-9l6 5l8-8l6 12z`,'#9d8ff0',0)+R(W/2-2,-38,4,6,P.dark,1,1)},
  ghe_gaming:{h:66,d:()=>shadow(40,30)+L('M20 -16v-6M8 -2l12-8l12 8',P.dark,2.4)+R(9,-66,22,42,P.dark,8)+Rn(17,-64,6,38,P.red,2)+R(12,-62,16,8,P.red,4,1)
    +box(6,28,20,5,6,P.dark,P.darkL,4)+R(3,-30,6,10,P.red,2,1)+R(31,-30,6,10,P.red,2,1)},
  xich_du:{h:96,d:(W)=>shadow(W,30)+L(`M4 0l12-94M${W-4} 0l-12-94`,P.woodD,4)+R(10,-98,W-20,7,P.wood,3)+L(`M22 -91v62M${W-22} -91v62`,P.greyD,1.5)
    +box(14,W-28,24,4,7,P.woodD,P.woodL,3)+C(W/2,-34,3,P.pink,1)+leafE(W/2-6,-36,2,3.5,-40,P.leaf)+leafE(W/2+6,-36,2,3.5,40,P.leaf)},
  vong:{h:56,d:(W)=>shadow(W,30)+R(2,-56,6,56,P.woodD,2)+R(W-8,-56,6,56,P.woodD,2)+Pa(`M8 -48q${W/2-8} 44 ${W-16} 0q${-(W/2-8)} 30 ${-(W-16)} 0z`,P.sky)
    +L(`M8 -48q${W/2-8} 36 ${W-16} 0`,P.red,1.6)+L(`M8 -48q${W/2-8} 28 ${W-16} 0`,P.butter,1.6)},
  den_ban:{h:34,top:1,g:()=>[24,-22,26],d:()=>E(20,-2,9,2.5,P.greyD)+L('M18 -3l-4-16l12-10',P.greyD,2.4)+C(14,-19,2,P.grey,1)+Pa('M22 -34l12 6l-4 8l-14-6z',P.butter)+C(30,-23,2.5,'#fff3b0',0)},
  den_cay:{h:86,g:()=>[20,-70,34],d:()=>shadow(40,30)+L('M10 0l10-18l10 18M20 -18v-50',P.woodD,2.2)+Pa('M8 -66l4-20h16l4 20z',P.cream)+L('M10 -72h20',P.peachD,1.2)},
  den_ngu:{h:28,top:1,g:()=>[20,-16,24],d:()=>E(20,-2,9,2.5,'#000',0,' opacity=".1"')+R(16,-12,8,12,P.cream,3)+Pa('M6 -12q0-16 14-16q14 0 14 16z',P.red)+C(14,-20,2.2,P.white,0)+C(23,-23,2,P.white,0)+C(27,-16,1.6,P.white,0)+eyes(18,22,-6,1)},
  den_tha:{h:34,wall:1,g:(W)=>[W/2,24,30],d:(W)=>L(`M${W/2} 0v12`)+Pa(`M${W/2-12} 26q0-14 12-14q12 0 12 14z`,P.woodL)+L(`M${W/2-8} 18h16M${W/2-11} 22h22M${W/2-4} 13v12M${W/2+4} 13v12`,P.woodD,1)+E(W/2,27,5,2,'#fff3b0',0)},
  den_led:{h:34,wall:1,g:(W)=>[W/2,10,W*.5],d:(W)=>`<defs><linearGradient id="dcLed" x1="0" x2="1"><stop offset="0" stop-color="#ff7ab8"/><stop offset=".33" stop-color="#ffd36b"/><stop offset=".66" stop-color="#6be0c8"/><stop offset="1" stop-color="#8a8cff"/></linearGradient></defs>`
    +R(2,7,W-4,6,'url(#dcLed)',3,1.2)+[.15,.35,.55,.75,.92].map(t=>C(2+(W-4)*t,10,1.2,'#fff',0)).join('')},
  cay_monstera:{h:66,d:()=>shadow(40,30)+L('M20 -16q-6-20-12-30M20 -16q4-26 8-38M20 -16q8-14 14-20',P.leafD,1.6)
    +Pa('M2 -44q2-14 14-6q-4 4-2 8q-8-2-12-2z',P.leaf,1.3)+Pa('M18 -58q10-12 18 0q-6 0-6 4q-4-4-12-4z',P.leafL,1.3)+Pa('M26 -38q12-6 14 6q-6-2-8 2q-2-6-6-8z',P.leaf,1.3)
    +L('M8 -44l4 3M26 -58v4M32 -34l-2 3',P.leafD,1)+pot(20,24,18,P.white,P.grey)},
  cay_luoi_ho:{h:60,d:()=>shadow(40,30)+[[14,-56,-8],[20,-60,0],[26,-54,8],[10,-44,-16],[30,-44,16]].map(([x,y,r])=>`<path d="M${x-3} -16q3 ${y+16} 3 ${y+16}q0 0 3 ${-(y+16)}z" fill="${P.leafD}" stroke="${OL}" stroke-width="1.2" transform="rotate(${r} ${x} -16)"/>`).join('')
    +L('M14 -36h1M20 -40h1M26 -34h1',P.butter,1.4)+pot(20,24,18,P.lilac,P.lilacD)},
  xuong_rong:{h:26,top:1,d:()=>R(13,-24,14,18,P.leaf,7)+R(6,-18,7,9,P.leaf,3.5)+R(27,-20,7,9,P.leaf,3.5)+L('M17 -18v2M22 -14v2M19 -10v2',P.leafD,1.2)+C(20,-25,2.6,P.pink,1)+pot(20,16,9)},
  binh_hoa:{h:34,top:1,d:()=>L('M14 -14l-4-14M20 -14v-18M26 -14l4-12',P.leafD,1.3)+[[10,-28],[20,-32],[30,-26]].map(([x,y])=>[0,72,144,216,288].map(a=>{const r=a*Math.PI/180;return C(x+Math.cos(r)*3,y+Math.sin(r)*3,2.4,P.white,.9);}).join('')+C(x,y,1.8,P.butterD,0)).join('')
    +Pa('M13 -14h14l-2 14h-10z','#cdeef7')+shine(15,-12,2,8)},
  gian_rau:{h:40,d:(W)=>shadow(W,30)+[10,20,30,42,52,62].filter(x=>x<W-8).map((x,i)=>leafE(x,-26-(i%2)*4,4,8,(i%2?14:-14),i%3?P.leaf:P.leafL)).join('')
    +box(3,W-6,0,16,7,P.woodD,P.woodL)+R(W/2-10,-12,20,8,P.cream,2,1)+L(`M${W/2-6} -8h12`,P.leafD,1.2)},
  rem:{h:68,wall:1,d:(W,H)=>R(0,1,W,3,P.woodD,1.5,1.1)+C(2,2.5,2.5,P.gold,1)+Pa(`M3 4h${W-8}q-6 ${H/2} 4 ${H-8}h${-(W-4)}z`,P.mintL)
    +[[10,14],[22,22],[12,36],[24,46],[14,56]].filter(([,y])=>y<H-6).map(([x,y])=>C(x,y,2.2,P.pink,0)+C(x,y,.8,P.butter,0)).join('')+L(`M${W/2+2} 6q-2 ${H/2} 2 ${H-10}`,P.mintD,1)},
  poster:{h:68,wall:1,d:(W,H)=>R(4,4,W-8,H-10,P.lilacL,2)+C(W/2,H/2-4,9,P.butter)+Pa(`M${W/2-8} ${H/2-10}l2-7l4 4M${W/2+8} ${H/2-10}l-2-7l-4 4`,P.butter,1.2)
    +eyes(W/2-3.5,W/2+3.5,H/2-5,1.2)+blush(W/2-6,H/2-2)+blush(W/2+6,H/2-2)+L(`M${W/2-2} ${H/2-1}q2 2 4 0`,OL,1)+R(8,H-20,W-16,6,P.pink,2,1)+C(W/2,5,1.8,P.red,1)},
  ke_treo:{h:34,wall:1,d:(W)=>R(3,24,W-6,4,P.wood,1.5,1.2)+R(8,8,6,16,P.sky,1,1)+R(14,10,6,14,P.butter,1,1)+R(20,7,7,17,P.pink,1,1)+R(28,14,12,5,P.mint,1,1)+R(28,19,12,5,P.lilac,1,1)
    +`<g transform="translate(0 24)">${pot(W-16,12,9)}</g>`+leafE(W-19,12,3,6,-20)+leafE(W-13,12,3,6,20,P.leafL)},
  bang_ghim:{h:34,wall:1,d:(W,H)=>R(3,3,W-6,H-6,P.woodD,3)+Rn(6,6,W-12,H-12,'#e5c08f',2)+R(10,9,14,11,P.white,1,1)+Rn(12,11,10,6,P.skyL,1)+R(28,8,12,10,P.butter,1,1)+L('M30 12h8M30 15h6',P.greyD,1)
    +R(W-26,12,13,13,P.pinkL,1,1)+Pa(`M${W-19.5} 21q-3-2-3-4q0-2 3-1q3-1 3 1q0 2-3 4z`,P.red,0)+C(17,9,1.6,P.red,.8)+C(34,8,1.6,P.sky,.8)+C(W-19,12,1.6,P.leaf,.8)},
  dong_ho_cuc_cu:{h:44,wall:1,d:(W)=>Pa(`M${W/2-14} 12l14-11l14 11z`,P.woodD)+R(W/2-12,11,24,20,P.wood,2)+C(W/2,22,6,P.cream,1.2)+L(`M${W/2} 22v-4M${W/2} 22l3 1`,OL,1.2)
    +R(W/2-3,13,6,4,'#6b4a2e',1,0)+C(W/2,14,1.6,P.butter,.8)+L(`M${W/2-4} 31v8M${W/2+4} 31v6`,P.gold,1.2)+C(W/2-4,40,2,P.gold,1)+C(W/2+4,38,2,P.gold,1)},
  quat:{h:66,d:()=>shadow(40,30)+E(20,-2,10,3,P.white)+R(18.5,-46,3,44,P.greyD,1,1)+C(20,-50,14,P.white)+C(20,-50,11,P.skyL,1)
    +[0,120,240].map(a=>leafE(20+Math.cos(a*Math.PI/180)*6,-50+Math.sin(a*Math.PI/180)*6,3.5,6,a+90,P.sky)).join('')+C(20,-50,2.5,P.white,1.2)},
  quat_mini:{h:26,top:1,d:()=>E(20,-2,7,2,P.pinkD)+R(19,-12,2.5,10,P.pinkD,1,1)+C(20,-17,9,P.white)+[0,120,240].map(a=>leafE(20+Math.cos(a*Math.PI/180)*4,-17+Math.sin(a*Math.PI/180)*4,2.4,4,a+90,P.pink)).join('')+C(20,-17,1.6,P.white,1)},
  loa:{h:26,top:1,d:()=>R(10,-24,20,24,P.sky,5)+C(20,-16,4.5,P.skyD,1.2)+C(20,-16,1.6,P.dark,0)+C(20,-6,2.5,P.skyD,1)+note(31,-20,P.pinkD)},
  may_choi_game:{h:22,top:1,d:()=>E(20,-2,14,2.5,'#000',0,' opacity=".1"')+R(2,-17,10,15,P.sky,5)+R(28,-17,10,15,P.red,5)+R(10,-18,20,16,P.dark,2)+Rn(12,-16,16,12,'#8fd0f5',1)+Pa('M15 -7l4-5l3 3l3-4l3 6z','#c8ecff',0)+C(7,-12,1.8,P.dark,0)+C(33,-8,1.6,P.white,0)+C(34,-12,1.6,P.white,0)},
  hop_nhac:{h:28,top:1,d:()=>box(9,22,0,10,5,P.pinkD,P.pinkL,2)+Pa('M9 -15l-2-11h22l2 11z',P.pink)+R(18,-22,4,8,P.butter,1,1)+C(20,-24,2.5,P.butter,1)+note(32,-14,P.lilacD)},
  o_meo:{h:30,d:()=>shadow(40,30)+E(20,-8,18,8,P.pinkD)+E(20,-10,14,5,P.pinkL,1)+E(22,-15,11,7,P.grey)+Pa('M13 -18l-1-8l6 4z',P.grey,1.2)+Pa('M22 -20l3-7l3 6z',P.grey,1.2)
    +L('M14 -16q1.5 1.5 3 0M20 -16q1.5 1.5 3 0',OL,1.1)+C(18.5,-13,1,P.pinkD,0)+blush(13,-12)+blush(25,-12)+Pa('M32 -12q6 0 4-6',P.grey,1.3)+L('M30 -18l3-2M31 -15h4',P.greyD,1)},
};

/* ---------------------------------------------------------------- the room */
export function geom(room){
  const W=room.cols*CW+PX*2,WY=CEIL+TOP,FY=room.wrows?WY+room.wrows*WR+BASE:(room.out?84:60);
  return {W,H:FY+room.frows*FR+12,WY,FY};
}
export const night=()=>{const h=new Date().getHours();return document.documentElement.dataset.theme==='dem'||h>=18||h<6;};

const WALLS={l0:'#eadcc3',l1:'#f9e7cf',l2:'#dfeee0',studio:'#f3e2cc',attic:'#ecd2ab',tro:'#d9eee5',loft:'#f6e3d3',bunk:'#e7dcf5'};
const FLOORS={l0:'#cfc6b6',l1:'#efe6d6',l2:'#d29a63',attic:'#c99363',tro:'#eadfcf',loft:'#d7a874',bunk:'#fdf3ec',balcony:'#e2d3bf',yard:'#a8d58a'};

/** Sky through a window or over a balcony: day (sun, cloud) or night (moon, stars). */
function sky(x,y,w,h,isNight,id){
  const top=isNight?'#232b52':'#9fd4f2',bot=isNight?'#4a4f86':'#dff1fb';
  let s=`<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${top}"/><stop offset="1" stop-color="${bot}"/></linearGradient></defs>`+Rn(x,y,w,h,`url(#${id})`);
  if(isNight)s+=C(x+w*.72,y+h*.3,Math.min(7,h*.18),'#fff4c4',0)+C(x+w*.72+3,y+h*.3-2,Math.min(6,h*.16),top,0)
    +[[.15,.2],[.35,.45],[.5,.15],[.85,.7],[.25,.75]].map(([a,b])=>C(x+w*a,y+h*b,1,'#fff',0)).join('');
  else s+=C(x+w*.78,y+h*.28,Math.min(7,h*.18),'#ffd66b',0)+E(x+w*.32,y+h*.5,Math.min(10,w*.16),Math.min(4,h*.1),'#fff',0)+E(x+w*.4,y+h*.45,Math.min(7,w*.12),Math.min(4,h*.1),'#fff',0);
  return s;
}

/** The fixtures: drawn with the room, under the furniture (the counter as a floor piece of its row). */
function fixture(f,room,G,parts,isNight,uid){
  const x=PX+f.x*CW,w=f.w*CW;
  if(f.layer==='wall'){
    const y=G.WY+f.y*WR,h=f.h*WR;
    if(f.t==='window'){const id=`dcSky${uid}${f.x}`;
      return R(x+3,y+2,w-6,h-6,'#fffaf1',4,1.5)+sky(x+7,y+6,w-14,h-14,isNight,id)+L(`M${x+w/2} ${y+6}v${h-14}${f.h>1?`M${x+7} ${y+h/2}h${w-14}`:''}`,'#fffaf1',3)
        +R(x+1,y+h-6,w-2,5,'#f2e6d2',2,1.2)+(isNight?'':Pa(`M${x+8} ${y+h-6}l${w*0.5} ${G.FY-(y+h)+FR*1.4}h${w*0.9}l${-w*0.25} ${-(G.FY-(y+h)+FR*1.4)}z`,'#fff6c8',0,' opacity=".28"'));}
    if(f.t==='door'){const top=y+2,bot=G.FY;
      return R(x+4,top,w-8,bot-top,P.woodD,4)+Rn(x+8,top+4,w-16,bot-top-4,P.wood,2)+R(x+11,top+8,w-22,(bot-top)*.32,P.woodL,2,1)+R(x+11,top+12+(bot-top)*.36,w-22,(bot-top)*.38,P.woodL,2,1)
        +C(x+w-11,top+(bot-top)*.56,2.2,P.gold,1.1);}
    if(f.t==='splash'){const lv=parts?.kitchen?.lv||0;
      let s=Rn(x,y,w,h+BASE,lv?'#eaf4f4':'#e6dccb')+Array.from({length:f.w*4},(_,i)=>L(`M${x+i*10} ${y}v${h+BASE}`,lv?'#cfe2e2':'#d6c9b3',.8)).join('')+L(`M${x} ${y+h/2}h${w}M${x} ${y+h}h${w}`,lv?'#cfe2e2':'#d6c9b3',.8);
      if(lv>=2)s+=Pa(`M${x+w-70} ${y-6}h44l10 ${h*0.5}h-64z`,'#c9d0d6')+R(x+w-54,y-30,12,26,'#c9d0d6',2,1.2);
      if(lv===1)s+=R(x+10,y-4,60,4,P.woodD,1.5,1.1)+[16,28,40,52].map(a=>R(x+a,y-12,8,8,[P.red,P.butter,P.mint,P.sky][a/12-1|0]||P.peach,1.5,1)).join('');
      if((parts?.kitchen?.c??100)<60)s+=E(x+w-48,y+4,26,12,'#4a3f35',0,' opacity=".22"');
      return s;}
    if(f.t==='slope')return Pa(`M${x-PX} ${y-TOP-CEIL}h${w+PX+20}L${x-PX} ${y+h+10}z`,'#b98a5e')+L(`M${x-PX} ${y+h-6}L${x+w+6} ${y-TOP-CEIL}M${x-PX} ${y+h-24}L${x+w-14} ${y-TOP-CEIL}`,'#8e6440',2.4);
    return '';
  }
  // floor fixtures: drawn standing on their row
  const by=G.FY+(f.y+f.h)*FR;
  if(f.t==='counter'){const lv=parts?.kitchen?.lv||0,top=f.surface;
    let s=`<g transform="translate(${x} ${by})">`+R(0,-top,w,top,lv>=2?'#f2ebe0':lv?'#e9dcc4':'#d6c6aa',3)+R(-2,-top-9,w+4,10,lv>=2?'#9aa3ab':'#9e8a6c',2)
      +Array.from({length:f.w},(_,i)=>R(i*CW+4,-top+5,CW-8,top-9,lv>=2?'#fffdf8':'#e8dcc6',2,1.1)+C(i*CW+CW/2,-top+10,1.4,OL,0)).join('')
      +R(10,-top-8,30,5,'#c7d3db',2,1)+L(`M24 ${-top-8}v-10h8`,'#8d9aa3',2.4)
      +(lv?R(w-56,-top-8,40,4,'#2f2f35',1.5,1)+E(w-46,-top-9,6,1.6,'#4a4a52',0)+E(w-26,-top-9,6,1.6,'#4a4a52',0):R(w-50,-top-12,28,8,'#7d7a74',2,1.2)+C(w-36,-top-13,4,'#4a4a52',1));
    return s+'</g>';}
  if(f.t==='ladder')return `<g transform="translate(${x} ${by})">`+Rn(4,-FR+4,CW-8,FR-6,'#6e4a2c',3)+L(`M10 4v${-FR-14}M30 4v${-FR-14}M10 -4h20M10 -14h20M10 -24h20`,P.woodD,2.6)+'</g>';
  if(f.t==='pillow')return `<g transform="translate(${x} ${by})">`+R(3,-24,CW-6,18,P.white,8)+L('M8 -15q12 4 24 0',P.grey,1.2)+'</g>';
  return '';
}

/** The room's background: ceiling, wall (paint or wallpaper as its upgrade level, the flaws of a worn part), floor,
 * fixtures; outdoors the sky and the city or the garden. parts: journey.reno parts by id (own home) or null. */
export function roomBack(room,G,parts,isNight,uid=''){
  const out=[],wallLv=parts?.wall?.lv??null,floorLv=parts?.floor?.lv??null,sev=p=>!p?0:p.c<45?2:p.c<60?1:0;
  const wallKey=parts?`l${wallLv}`:room.type==='studio'&&room.id==='attic'?'attic':room.type==='studio'?'tro':room.type;
  const floorKey=room.out?room.type:parts?`l${floorLv}`:room.id==='attic'?'attic':room.type==='studio'?'tro':room.type;
  if(room.out){
    out.push(sky(0,0,G.W,G.FY,isNight,`dcSkyOut${uid}`));
    if(room.type==='balcony'){
      const sky2=[[0,40],[30,56],[54,32],[84,66],[106,46],[146,74],[174,44],[210,66],[240,48],[272,78],[298,52],[330,70],[360,44]].filter(([x])=>x<G.W);
      out.push(Pa(`M0 ${G.FY}`+sky2.map(([x,h])=>`V${G.FY-h}H${x+30}`).join('')+`V${G.FY}z`,isNight?'#3a4566':'#b9cfdd',0));
      if(isNight)out.push([[40,G.FY-30],[96,G.FY-50],[150,G.FY-36],[210,G.FY-44]].map(([a,b])=>Rn(a,b,4,4,'#ffd76a',1,.9)).join(''));
      out.push(Rn(0,G.FY-26,G.W,4,'#7a6656',2)+Array.from({length:Math.ceil(G.W/18)},(_,i)=>Rn(i*18+6,G.FY-24,3,24,'#7a6656',1)).join(''));
    }else{
      out.push(E(G.W*.2,G.FY-30,60,34,isNight?'#2f5a45':'#8cc47a',0)+E(G.W*.75,G.FY-34,70,40,isNight?'#2a5240':'#7cb86c',0)
        +Rn(0,G.FY-22,G.W,22,isNight?'#2e5a40':'#6aa851')+Array.from({length:Math.ceil(G.W/22)},(_,i)=>R(i*22+4,G.FY-30,12,30,'#f3e6cf',2,1.1)).join(''));
    }
  }else{
    out.push(Rn(0,0,G.W,G.FY,WALLS[wallKey]||WALLS.l1));
    if(wallKey==='l2'){out.push(`<defs><pattern id="dcPaper${uid}" width="22" height="22" patternUnits="userSpaceOnUse"><path d="M11 4l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="#c4d8bd"/></pattern></defs>`+Rn(0,0,G.W,G.FY,`url(#dcPaper${uid})`)+Rn(0,G.FY-24,G.W,24,'#c99a6c'));}
    if(wallKey==='attic')out.push(Array.from({length:Math.ceil(G.FY/16)},(_,i)=>L(`M0 ${i*16+8}H${G.W}`,'#d9b98c',1)).join(''));
    if(wallKey==='tro')out.push(Array.from({length:Math.ceil(G.W/30)},(_,i)=>L(`M${i*30+15} 0V${G.FY}`,'#c9e6da',6,' opacity=".6"')).join(''));
    if(wallKey==='bunk')out.push(Array.from({length:Math.ceil(G.W/24)*3},(_,i)=>C((i%Math.ceil(G.W/24))*24+12,(i/Math.ceil(G.W/24)|0)*30+30,2,'#d6c6ee',0)).join(''));
    const w=parts?.wall;
    if(sev(w))out.push(Pa(`M${G.W*.06} ${G.FY*.55}q10-8 22-2l6 10q-12 10-24 2z`,'#c9b691',0,' opacity=".85"')+Pa(`M${G.W*.72} ${G.FY*.32}q12-6 20 2l-4 12q-12 2-18-6z`,'#c9b691',0,' opacity=".85"')
      +(sev(w)>1?L(`M${G.W*.2} ${CEIL+6}l8 18-6 10 10 16M${G.W*.62} ${G.FY*.6}l-6 14 8 8-4 14`,'#7c6a52',1.6,' opacity=".75"'):''));
    out.push(Rn(0,0,G.W,CEIL,'#f6efe2')+L(`M0 ${CEIL}H${G.W}`,'#e3d6c0',1.4));
    const roof=parts?.roof;
    if(sev(roof))out.push(E(G.W*.28,CEIL+4,sev(roof)>1?40:26,sev(roof)>1?10:7,'#b48d55',0,' opacity=".45"')+(sev(roof)>1?C(G.W*.3,CEIL+16,2.6,'#7fb6d9',0):''));
    if(parts?.roof?.lv===2)out.push(Rn(0,CEIL-2,G.W,3,'#ffe8a3',0,.9));
    if(room.type==='bunk')out.push(Rn(0,0,G.W,CEIL+8,P.woodD)+Array.from({length:Math.ceil(G.W/30)},(_,i)=>Rn(i*30+2,2,26,CEIL+2,P.wood,2)).join('')+Rn(0,0,8,G.H,P.woodD)+Rn(G.W-8,0,8,G.H,P.woodD));
    out.push(Rn(0,G.FY-6,G.W,6,'#c9a27a'));
  }
  // floor
  const fc=FLOORS[floorKey]||FLOORS.l1;
  out.push(Rn(0,G.FY,G.W,G.H-G.FY,fc));
  if(floorKey==='yard')out.push([[30,G.FY+30],[110,G.FY+60],[200,G.FY+24],[290,G.FY+70],[60,G.FY+90]].filter(([a,b])=>a<G.W&&b<G.H).map(([a,b])=>L(`M${a} ${b}l4-8 4 8`,'#6aa851',2)).join(''));
  else if(floorKey==='bunk')out.push(Array.from({length:Math.ceil(G.W/26)},(_,i)=>Rn(i*26+10,G.FY,8,G.H-G.FY,'#f6d6df',0,.7)).join('')+Rn(0,G.FY,G.W,5,'#efe2d6'));
  else{
    const wood=floorKey==='l2'||floorKey==='attic'||floorKey==='loft',line=wood?'#a46f3d':floorKey==='l0'?'#b5ab99':'#d8ccb8',lines=[];
    for(let r=1;r<=room.frows;r++)lines.push(`M0 ${G.FY+r*FR}H${G.W}`);
    if(wood)for(let r=0;r<room.frows;r++)for(let c=0;c<4;c++)lines.push(`M${(c*97+r*53)%G.W+10} ${G.FY+r*FR}v${FR}`);
    else for(let c=0;c<=room.cols;c++)lines.push(`M${PX+c*CW} ${G.FY}V${G.H}`);
    out.push(L(lines.join(''),line,1,' opacity=".7"'));
    const fl=parts?.floor;
    if(sev(fl))out.push(L(`M${G.W*.18} ${G.FY+20}l14 6-4 10 12 8M${G.W*.74} ${G.FY+50}l10-8 12 4`,'#7c6a52',1.6,' opacity=".75"'));
  }
  out.push(Rn(0,G.FY,G.W,10,'#000',0,.05));
  for(const f of room.fix)out.push(fixture(f,room,G,parts,isNight,uid));
  return out.join('');
}

/* ---------------------------------------------------------------- colours (bảng màu)
 * TINT[id]: a palette family of the piece ('pink': pink→c, pinkD→d, pinkL→l of the chosen colour), several families,
 * or {P key or #hex: 'c'|'d'|'l'}. Every piece has an entry (tests/test_deco.py checks it). */
const FAM={wood:{wood:'c',woodD:'d',woodL:'l'},pink:{pink:'c',pinkD:'d',pinkL:'l'},mint:{mint:'c',mintD:'d',mintL:'l'},
  sky:{sky:'c',skyD:'d',skyL:'l'},butter:{butter:'c',butterD:'d'},lilac:{lilac:'c',lilacD:'d',lilacL:'l'},peach:{peach:'c',peachD:'d'},
  red:{red:'c',redD:'d'},grey:{grey:'c',greyD:'d'},dark:{dark:'c',darkL:'l'},pot:{pot:'c',potD:'d'},cream:{cream:'c'},white:{white:'c'}};
export const TINT={sofa:'pink',ban_tra:'wood',giuong:'sky',tv:'wood',be_ca:'wood',ke_sach:'wood',ban_lam_viec:'wood',dan:'peach',
  gau_bong:'peach',cay_canh:'pot',ghe_may:'wood',tu_lanh:'mint',ban_an:'pink',noi_com:'pink',may_giat:'grey',hoa_giay:'pot',
  ban_ngoai:'red',tranh:'wood',den_long:{redD:'c','#b8473f':'d'},den_nhay:['butter','pink','mint','sky','lilac','peach'],dong_ho:'cream',
  guong:'wood',ke_cay:'pot',anh:'white',lich:'red',may_lanh:'white',ke_bep:'wood',tu_quan_ao:'wood',nem:'lilac',tu_dau_giuong:'wood',
  ke_go:'wood',goi_om:'grey',rem_giuong:'pink',tham:'lilac',tham_hoa:'peach',ban_hoc:'wood',ghe_hoc:'mint',ghe_luoi:'butter',
  ban_xep:'wood',ghe_dau:'red',ban_gaming:'dark',ghe_gaming:'red',xich_du:'wood',vong:'sky',den_ban:'butter',den_cay:'cream',
  den_ngu:'red',den_tha:'wood',den_led:{'#ff7ab8':'c','#ffd36b':'l','#6be0c8':'c','#8a8cff':'d'},cay_monstera:{white:'c',grey:'d'},
  cay_luoi_ho:'lilac',xuong_rong:'pot',binh_hoa:{'#cdeef7':'c'},gian_rau:'wood',rem:'mint',poster:'lilac',ke_treo:'wood',
  bang_ghim:'wood',dong_ho_cuc_cu:'wood',quat:'sky',quat_mini:'pink',loa:'sky',may_choi_game:['sky','red'],hop_nhac:'pink',o_meo:'pink'};
const MAPS=new Map();
function tintMap(id){
  if(MAPS.has(id))return MAPS.get(id);
  const spec=TINT[id];let m=null;
  if(spec){
    m=Object.create(null);
    const add=(k,role)=>{m[String(P[k]||k).toLowerCase()]=role;};
    if(typeof spec==='string'||Array.isArray(spec))for(const f of [].concat(spec))for(const [k,r] of Object.entries(FAM[f]||{}))add(k,r);
    else for(const [k,r] of Object.entries(spec))add(k,r);
  }
  MAPS.set(id,m);return m;
}
/** A piece's markup in colour `col` (a palette id; anything else, e.g. 'goc' or null: its own colours). */
export function tinted(id,svg,col){
  const t=col?PALETTE[col]:null,m=t&&tintMap(id);
  if(!m)return svg;
  return svg.replace(/#[0-9a-fA-F]{6}(?![0-9a-fA-F])/g,h=>{const r=m[h.toLowerCase()];return r?t[r]:h;});
}

/** Where a placed piece is drawn: [translate x, translate y] of its origin. surf: the height it stands on. */
export function spotXY(it,x,y,G,surf=0){
  if(it.spot==='wall')return [PX+x*CW,G.WY+y*WR];
  if(it.spot==='top')return [PX+x*CW,G.FY+(y+1)*FR-6-surf];
  return [PX+x*CW,G.FY+(y+it.h)*FR-3];
}
/** One piece's drawing at its spot (flip: mirrored; tint: its colour from the palette, if any). */
export function pieceSVG(it,x,y,f,G,surf=0,tint=null){
  const a=ART[it.id];if(!a)return '';
  const [tx,ty]=spotXY(it,x,y,G,surf),W=it.w*CW,D=it.spot==='wall'?it.h*WR:it.h*FR;
  const body=tinted(it.id,a.d(W,D),tint);
  return `<g transform="translate(${tx} ${ty})">${f?`<g transform="translate(${W} 0) scale(-1 1)">${body}</g>`:body}</g>`;
}
/** A glow at night for a lamp at its spot: [cx, cy, r] in room units, or null. */
export function glowAt(it,x,y,f,G,surf=0){
  const a=ART[it.id];if(!a?.g)return null;
  const [tx,ty]=spotXY(it,x,y,G,surf),W=it.w*CW,D=it.spot==='wall'?it.h*WR:it.h*FR,[gx,gy,r]=a.g(W,D);
  return [tx+(f?W-gx:gx),ty+gy,r];
}
/** A small picture of a piece for the drawer (its own viewBox), in colour `tint` when given. */
export function thumb(it,size=56,tint=null){
  const a=ART[it.id];if(!a)return '';
  const W=it.w*CW,D=it.spot==='wall'?it.h*WR:it.h*FR;
  const vb=it.spot==='wall'?`-4 -4 ${W+8} ${D+8}`:it.spot==='rug'?`-4 ${-D-6} ${W+8} ${D+10}`:`-6 ${-(a.h||40)-8} ${W+12} ${(a.h||40)+12}`;
  return `<svg class="dc-thumb" viewBox="${vb}" width="${size}" height="${size}" aria-hidden="true" focusable="false">${tinted(it.id,a.d(W,D),tint)}</svg>`;
}

/** Mochi the cat, who lives on the Ấm cúng card: 0 sleepy … 4 hearts in her eyes. */
export function mascot(level,size=64){
  const face=[
    L('M24 30q3 2 6 0M34 30q3 2 6 0',OL,1.6)+L('M30 37q2 1 4 0',OL,1.2),
    eyes(27,37,30,1.8)+L('M30 36q2 2 4 0',OL,1.3),
    L('M24 31q3-4 6 0M34 31q3-4 6 0',OL,1.8)+Pa('M29 35q3 4 6 0z',P.pinkD,1)+blush(23,35)+blush(41,35),
    `<path d="M27 26l1 3l3 1l-3 1l-1 3l-1-3l-3-1l3-1z" fill="${P.gold}"/><path d="M37 26l1 3l3 1l-3 1l-1 3l-1-3l-3-1l3-1z" fill="${P.gold}"/>`+Pa('M29 36q3 4 6 0z',P.pinkD,1)+blush(22,35)+blush(42,35),
    Pa('M27 33q-4-3-4-5q0-3 4-1q4-2 4 1q0 2-4 5z',P.red,0)+Pa('M37 33q-4-3-4-5q0-3 4-1q4-2 4 1q0 2-4 5z',P.red,0)+Pa('M29 37q3 4 6 0z',P.pinkD,1)+blush(21,36)+blush(43,36)][Math.max(0,Math.min(4,level))];
  const extra=level>=4?Pa('M50 10q-3-2-3-4q0-2 3-1q3-1 3 1q0 2-3 4z',P.red,0)+Pa('M10 16q-2-1.5-2-3q0-1.5 2-.8q2-.7 2 .8q0 1.5-2 3z',P.pink,0):level===0?`<text x="44" y="16" font-size="9" font-weight="700" fill="${OL}">z</text><text x="50" y="9" font-size="7" font-weight="700" fill="${OL}">z</text>`:'';
  return `<svg class="dc-mochi" viewBox="0 0 64 64" width="${size}" height="${size}" aria-hidden="true" focusable="false">`
    +E(32,58,18,4,'#000',0,' opacity=".1"')+Pa('M14 22l2-14l12 8M50 22l-2-14l-12 8',P.cream)+Pa('M17 18l1-6l6 4M47 18l-1-6l-6 4',P.pinkL,0)
    +E(32,46,20,13,P.cream)+E(32,31,19,15,P.cream)+Pa('M50 50q12-2 8-14',P.cream,1.5)+L('M24 22l-2-3M32 20v-3M40 22l2-3',P.peachD,1.4)
    +face+L('M14 33h-6M14 36l-6 2M50 33h6M50 36l6 2',OL,.9)+extra+'</svg>';
}

/** What stands in front of the furniture: the gác lửng's railing, the bunk's front rail (low, so pieces still show). */
export function roomFront(room,G){
  const y=G.H-4;
  if(room.type==='loft')return Rn(0,y-18,G.W,4,P.woodD,2)+Array.from({length:Math.ceil(G.W/26)+1},(_,i)=>Rn(i*26+4,y-16,4,16,P.wood,1)).join('')
    +R(-2,y-22,G.W+4,6,P.wood,3,1.2)+Rn(0,y,G.W,4,P.woodD);
  if(room.type==='bunk')return R(-2,y-14,G.W*.55,8,P.wood,4,1.2)+Rn(G.W*.55-10,y-14,8,18,P.woodD,1)+Rn(0,y-6,G.W,10,P.woodD);
  return '';
}
