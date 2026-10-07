/** 🪴 Bày trí phòng: the drawings (pure SVG strings, no DOM). game/deco_content.py has the rules; this file only
 * draws: a room seen from the front and a little from above (back wall with its grid of hanging spots, the floor in
 * rows from the wall to the front), the fixtures (window with day or night sky, door, kitchen counter, the attic's
 * roof, the gác lửng's ladder, the dorm's bunk) and every piece of furniture, each a small hand-made drawing.
 * Every colour is an attribute (no stylesheet needed), so the same markup becomes a photo (reno.js → canvas).
 * A piece is drawn from its footprint's front-left corner: x to the right, y up (negative). Wall pieces from the
 * top-left corner of their wall cells. Since 1.4 pieces stand anywhere (anchor(): units → pixels, a small thing on
 * the surface it stands on), each room may have a wallpaper and a floor (SKINS), the light follows the hour
 * (lightAt: the sky, a sunbeam through the window, the evening tint, lamps glowing) and the cats have their poses.
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
/** A five-pointed star of radius r around (x, y). */
const star=(x,y,r,c,sw=0)=>Pa('M'+Array.from({length:10},(_,i)=>{const a=-Math.PI/2+i*Math.PI/5,q=i%2?r*.45:r;return `${n(x+Math.cos(a)*q)} ${n(y+Math.sin(a)*q)}`;}).join('L')+'z',c,sw);

/* ---------------------------------------------------------------- the pieces
 * d(W,D): the drawing for a footprint W px wide, D px deep (wall: W × H of its cells). h: how tall it stands (thumbs).
 * g: where it glows at night [cx, cy, r]. */
export const ART={
  sofa:{h:60,d:(W)=>shadow(W,30)+legs([8,W-12],-8,8)+R(6,-58,W-12,32,P.pinkD,12)+R(10,-54,W/2-12,24,P.pink,9)+R(W/2+2,-54,W/2-12,24,P.pink,9)
    +box(2,W-4,6,16,10,P.pinkD,P.pinkL,6)+R(0,-44,16,38,P.pink,7)+R(W-16,-44,16,38,P.pink,7)+C(W/2-14,-42,7,P.butter)+L(`M${W/2-17} -44l3 3l3-3`,OL,1.1),
    back:(W)=>shadow(W,30)+legs([8,W-12],-8,8)+R(0,-58,W,50,P.pinkD,10)+R(6,-52,W-12,38,P.pink,7)
      +L(`M10 -17h${W-20}M${W/2} -49v31`,P.pinkD,1.5)+R(3,-12,W-6,6,P.pinkD,3)},
  ban_tra:{h:26,d:(W)=>shadow(W,30)+legs([8,W-12],-14,14)+box(2,W-4,12,6,10,P.woodD,P.woodL,4)+shine(10,-26,W-24,2)},
  giuong:{h:96,d:(W,D)=>shadow(W,D)+legs([4,W-8],-6,6)+R(2,-D-34,W-4,32,P.woodD,12)+R(10,-D-28,W-20,20,P.wood,8)
    +R(2,-D-4,W-4,D-6,P.white,6)+E(W*.3,-D+2,16,7,P.cream)+E(W*.66,-D+2,16,7,P.cream)
    +Pa(`M4 ${-D*0.62}q${W/2-4} -8 ${W-8} 0v${D*0.62-14}h${-(W-8)}z`,P.sky)+[0.2,0.4,0.6,0.8].map(t=>C(W*t,-D*0.36,2,P.skyL,0)).join('')
    +R(2,-14,W-4,10,P.wood,3)},
  tv:{h:66,d:(W)=>shadow(W,30)+box(4,W-8,0,16,8,P.woodD,P.woodL)+C(W/2,-9,1.6,P.cream,1)+R(W/2-3,-30,6,6,P.dark,1,1)
    +R(8,-66,W-16,38,P.dark,5)+R(12,-62,W-24,30,'#7ec8e3',3,0)+Pa(`M14 -36l10-12l8 7l9-12l${W-62} 17z`,'#a8e0f0',0)+C(W-24,-54,4,P.butter,0),
    back:(W)=>shadow(W,30)+box(4,W-8,0,16,8,P.woodD,P.woodL)+R(W/2-3,-34,6,10,P.dark,1,1)
      +R(8,-66,W-16,38,P.dark,5)+R(16,-60,W-32,25,'#575366',3)
      +Array.from({length:5},(_,i)=>L(`M${W/2-12+i*6} -55v9`,'#282634',1.5)).join('')
      +C(W-23,-37,1.5,'#282634',0)+L(`M${W-23} -35v12q0 6-8 8`,'#282634',1.4)},
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
    +L(`M3 ${H/2}q${W/2-3} 6 ${W-6} 0`,'#f2c14e',2.2)+C(W/2,H/2+3,3,P.butter,1)},
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
  ke_go_treo:{h:34,wall:1,d:(W)=>Rn(6,29,W-12,3,'#000',1,.08)+Pa('M12 28v7l7-7z',P.woodD,1.2)+Pa(`M${W-12} 28v7l-7-7z`,P.woodD,1.2)+R(2,23,W-4,6,P.wood,2,1.3)+Rn(5,24,W-10,1.6,'#fff',0,.5)+C(8,26,1,P.woodD,0)+C(W-8,26,1,P.woodD,0)},
  /* 1.4.11: nhà tắm */
  bon_tam:{h:58,d:(W,D)=>shadow(W,D)+C(18,-5,4.5,P.gold,1.2)+C(W-18,-5,4.5,P.gold,1.2)
    +Pa(`M5 -42h${W-10}q0 32-20 36h${-(W-50)}q-20-4-20-36z`,P.white)+Rn(14,-30,W-28,3,P.sky,1.5)+shine(16,-38,4,18)
    +R(1,-47,W-2,8,P.white,4)+Rn(7,-46,W-14,4,'#bfe7f7',2)
    +C(30,-50,6,'#ffffff',1)+C(41,-52,4.5,'#ffffff',1)+C(35,-57,3.5,'#ffffff',1)+C(52,-50,3,'#ffffff',1)
    +L(`M${W-16} -46v-12h-9`,P.greyD,3)+C(W-16,-58,2.4,P.grey,1)},
  buong_tam:{h:94,d:()=>shadow(40,30)+R(1,-8,38,8,P.grey,2)+Rn(4,-92,32,84,P.skyL,3,.55)+L('M4 -92v84M36 -92v84M4 -92h32',P.greyD,2.4)
    +L('M28 -88v6h-8',P.greyD,2.4)+E(19,-80,5,2,P.grey,1.1)+L('M15 -74v6M19 -72v8M23 -74v5',P.skyD,1.2,' opacity=".8"')
    +L('M10 -60l6-14',P.white,2,' opacity=".7"')+C(31,-46,2,P.greyD,1)},
  bon_rua:{h:44,d:(W)=>shadow(W,30)+box(3,W-6,0,20,8,P.wood,P.woodL,3)+L(`M${W/2} -18v16`,OL,1.2)+C(W/2-6,-11,1.6,P.cream,1)+C(W/2+6,-11,1.6,P.cream,1)
    +E(W/2,-28.5,15,3.5,P.white,1.4)+E(W/2,-28.5,10,2,'#cfe6f1',0)+L(`M${W/2+12} -30v-10h-7`,P.greyD,2.4)},
  guong_tam:{h:34,wall:1,g:(W)=>[W/2,8,40],d:(W,H)=>R(10,5,W-20,H-9,P.woodL,7)+Rn(14,9,W-28,H-17,'#dff1fb',4)+L(`M${W/2-8} 18l8-7M${W/2-2} 22l12-11`,'#fff',2)
    +[18,32,48,62].filter(x=>x<W-10).map(x=>C(x,4,2.8,P.butter,1)).join('')},
  ke_khan:{h:34,wall:1,d:(W)=>R(6,6,W-12,3.5,P.greyD,1.5,1)+R(4,4,4,8,P.grey,1.5,1)+R(W-8,4,4,8,P.grey,1.5,1)
    +R(12,8,24,22,P.pink,3)+Rn(12,22,24,3,P.pinkD)+R(42,8,24,17,P.mint,3)+Rn(42,19,24,2.5,P.mintD)},
  ke_tam:{h:36,d:()=>shadow(40,30)+R(7,-36,4,36,P.woodD,1.5,1.1)+R(29,-36,4,36,P.woodD,1.5,1.1)+R(4,-34,32,4,P.wood,2,1.2)+R(4,-20,32,4,P.wood,2,1.2)+R(4,-6,32,4,P.wood,2,1.2)
    +R(10,-30,6,10,P.pink,2,1)+R(18,-28,5,8,P.mint,2,1)+E(29,-24,4,3.5,P.butter,1)+R(10,-16,18,9,P.white,3,1)+Rn(10,-12,18,2,P.skyD,1)},
  gio_do_tam:{h:24,top:1,d:()=>E(20,-2,13,2.5,'#000',0,' opacity=".1"')+R(11,-21,6,12,P.pink,2)+R(18,-19,5,10,P.mint,2)+E(28,-12,5,4,P.sky)
    +R(7,-12,26,12,P.woodL,3)+L('M9 -8h22M9 -4h22',P.woodD,.9)+L('M14 -12v12M20 -12v12M26 -12v12',P.woodD,.7)},
  tham_tam:{h:14,rug:1,d:(W,D)=>R(4,-D+5,W-8,D-9,P.sky,8)+R(9,-D+9,W-18,D-17,P.skyL,5,1)+[W*.3,W*.5,W*.7].map(x=>Pa(`M${x} ${-D/2-3}q-2.5 3 0 5q2.5-2 0-5z`,P.skyD,0)).join('')},
  vit_cao_su:{h:24,top:1,d:()=>E(20,-2,11,2.5,'#000',0,' opacity=".1"')+Pa('M8 -8q0-9 10-9h6q8 0 9 8q-3 7-13 7q-12 0-12-6z',P.butter)+C(25,-18,6.5,P.butter)
    +Pa('M30 -18l6 1l-6 2.5z',P.peachD,1)+C(26,-20,1.3,OL,0)+blush(24,-16)+Pa('M10 -10q5-5 10 0',P.butterD,1)},
  /* hồ bơi & sân vườn */
  ghe_tam_nang:{h:46,d:(W)=>shadow(W,30)+legs([8,W-14],-10,10,P.greyD,3)+R(4,-16,W-8,6,P.white,3)+R(6,-21,W-34,6,P.sky,3)+L(`M14 -21v6M26 -21v6M38 -21v6`,P.skyD,1)
    +Pa(`M${W-32} -18l20-26q4-3 7 1l-17 25z`,P.sky)+Rn(14,-25,20,4,P.butter,2)},
  du_che:{h:100,d:()=>E(20,-3,11,3,P.greyD)+R(18.5,-84,3,82,P.greyD,1,1)+Pa('M-16 -72q36-32 72 0z',P.red)+Pa('M8 -72q12-28 24 0z',P.cream,1.2)
    +Pa('M-16 -72q4 4 8 0q4 4 8 0q4 4 8 0q4 4 8 0q4 4 8 0q4 4 8 0q4 4 8 0q4 4 8 0q4 4 8 0',P.red,1.2)+C(20,-90,2.6,P.red,1.2)},
  phao:{h:20,d:()=>E(20,-4,17,3,'#000',0,' opacity=".08"')+E(20,-9,17,8.5,P.red)+Pa('M12 -16q-8 2-8 7l8 0zM28 -2q8-2 8-7l-8 0z',P.white,1)+E(20,-10,7.5,3.4,'#7ec4e6',1.2)},
  lo_nuong:{h:58,g:()=>[20,-34,22],d:()=>shadow(40,30)+L('M10 0l6-18M30 0l-6-18M20 -18v18',P.dark,2.2)+Pa('M5 -34h30q0 17-15 17q-15 0-15-17z',P.dark)
    +R(3,-36,34,3,P.greyD,1.5,1)+R(7,-41,26,3,P.peachD,1.5,1)+[11,18,25].map(x=>C(x,-42,2.4,[P.redD,P.leafD,P.butterD][(x-11)/7],1)).join('')
    +L('M14 -48q-3-4 0-8M24 -50q-3-4 0-8',P.greyD,1.1,' opacity=".6"')+Rn(10,-27,20,2,P.red,1)},
  cay_dua:{h:92,d:()=>shadow(40,30)+Pa('M18 -18q-2-30 4-62h4q-4 32-2 62z',P.woodD,1.3)+L('M19 -30h6M20 -42h6M21 -54h6M23 -66h5',P.wood,1.4)
    +leafE(10,-80,5,15,-60,P.leaf)+leafE(36,-80,5,15,60,P.leaf)+leafE(14,-88,4.5,13,-25,P.leafL)+leafE(32,-88,4.5,13,25,P.leafL)+leafE(24,-92,4,11,0,P.leafD)
    +C(22,-77,3,P.woodD,1)+C(27,-76,3,P.woodD,1)+pot(20,26,18)},
  den_vuon:{h:76,g:()=>[20,-62,30],d:()=>E(20,-3,9,3,P.dark)+R(18,-56,4,54,P.dark,1.5,1.1)+R(12,-70,16,15,P.butter,3)+Rn(15,-67,10,9,'#fff3b0',2)
    +Pa('M10 -70l10-8l10 8z',P.dark)+C(20,-79,1.8,P.dark,0)+R(11,-56,18,3,P.dark,1.5,1)},
  /* đồ nhà kiểu Việt (after 1.4.19): phòng khách */
  sap_go:{h:30,d:(W)=>shadow(W,30)+legs([4,W/2-3,W-10],-9,9,P.woodD,6)+box(2,W-4,8,10,10,P.woodD,P.wood,3)
    +L(`M8 -8q${(W-16)/6} 6 ${(W-16)/3} 0q${(W-16)/6} 6 ${(W-16)/3} 0q${(W-16)/6} 6 ${(W-16)/3} 0`,P.woodD,1.4)
    +Rn(8,-27,W-16,9,'#ead69c',2)+L(Array.from({length:Math.floor((W-20)/8)},(_,i)=>`M${12+i*8} -26v7`).join(''),'#c8a85e',1,' opacity=".7"')
    +L(`M10 -23h${W-20}`,P.redD,1.2,' opacity=".6"')+C(12,-13,1.4,P.woodL,0)+C(W-12,-13,1.4,P.woodL,0)},
  am_chen:{h:24,top:1,d:()=>E(20,-2.5,16,3.5,P.woodD)+E(20,-3.5,13,2,P.wood,0)
    +L('M9 -11q-5-1-6-6',OL,2.6)+L('M9 -11q-5-1-6-6',P.white,1.2)+L('M21 -14q5 1 1 7',OL,1.6)+C(15,-10,7,P.white)+L('M9.5 -9q5.5 3 11 0',P.skyD,1.2)
    +E(15,-16.5,4.5,1.6,P.white,1.2)+C(15,-18.8,1.5,P.skyD,1)+R(25,-9,5,6,P.white,1.5,1.1)+R(31,-9,5,6,P.white,1.5,1.1)+Rn(25.5,-6,4,1.2,P.skyD)+Rn(31.5,-6,4,1.2,P.skyD)
    +L('M27 -12q-2-3 0-5M33 -12q-2-3 0-5',P.greyD,1,' opacity=".7"')},
  tranh_dong_ho:{h:34,wall:1,d:(W,H)=>R(3,3,W-6,H-6,P.woodD,2)+Rn(7,7,W-14,H-14,'#f6e9cc',1)+Rn(7,7,W-14,H-14,'#fff',1,.25)
    +leafE(16,21,2.6,6,-25,P.leafD)+leafE(20,19,2.4,5.5,15,P.leaf)+L('M17 25q1-4 3-8',P.leafD,1)
    +E(W/2+2,19,14,6.5,P.dark,1.2)+C(W/2+15,17,5,P.dark,1.2)+E(W/2+20,18.5,1.8,2.3,P.darkL,1)+Pa(`M${W/2+12} 13l1-4l3 3z`,P.dark,1)
    +R(W/2-8,23,3,4,P.dark,1,1)+R(W/2-3,23,3,4,P.dark,1,1)+R(W/2+5,23,3,4,P.dark,1,1)+R(W/2+10,23,3,4,P.dark,1,1)+L(`M${W/2-12} 17q-4-1-3-4`,P.dark,1.2)
    +L(`M${W/2-4} 19q2-4 5 0q-3 4-5 0M${W/2+4} 18q2-3 4 0q-2 3-4 0`,'#fff',1)+C(W/2+16,16,.8,'#fff',0)+Rn(W-15,9,5,6,P.red,1)},
  dong_ho_qua_lac:{h:68,wall:1,d:(W,H)=>Pa(`M${W/2-13} 10q0-8 13-8q13 0 13 8z`,P.woodD)+R(W/2-12,9,24,H-14,P.wood,3)+R(W/2-14,H-8,28,5,P.woodD,2,1.2)
    +C(W/2,19,8,P.cream,1.3)+[0,90,180,270].map(a=>{const r=a*Math.PI/180;return C(W/2+Math.sin(r)*6,19-Math.cos(r)*6,.8,OL,0);}).join('')+L(`M${W/2} 19v-5M${W/2} 19l3 2`,OL,1.2)
    +Rn(W/2-8,30,16,H-41,'#f6efe0',2)+L(`M${W/2} 31l3 ${H-49}`,P.gold,1.3)+C(W/2+3,H-17,3.6,P.gold,1.1)+Rn(W/2-8,30,16,H-41,'#fff',2,.25)
    +L(`M${W/2-8} 30h16`,P.woodD,1)},
  cay_kim_tien:{h:58,d:()=>{const stem=(x1,y1,s)=>{let o=L(`M20 -14Q${(20+x1)/2+s*3} ${(y1-14)/2} ${x1} ${y1}`,P.leafD,1.5);
      for(const t of [.38,.58,.78,.96]){const x=20+(x1-20)*t,y=-14+(y1+14)*t;o+=leafE(x-3.2,y,2.1,4.4,-35,P.leaf)+leafE(x+3.2,y,2.1,4.4,35,P.leafD);}return o;};
    return shadow(40,30)+stem(8,-46,-1)+stem(32,-48,1)+stem(20,-58,0)+stem(13,-36,-1)+stem(28,-34,1)+pot(20,24,16,P.white,P.grey)+Rn(10,-9,20,3,P.red,1)+C(20,-7.5,2,P.gold,1);}},
  quat_tran:{h:34,wall:1,g:(W)=>[W/2,20,26],d:(W)=>R(W/2-1.5,-10,3,18,P.greyD,1,1)+R(W/2-5,-12,10,3,P.white,1.5,1)
    +E(W/2-21,13,19,3.2,P.wood,1.3)+E(W/2+21,13,19,3.2,P.wood,1.3)+E(W/2-21,12,15,1.2,P.woodL,0)+E(W/2+21,12,15,1.2,P.woodL,0)
    +E(W/2,12,8,4.5,P.white)+Pa(`M${W/2-5} 15q5 7 10 0z`,P.cream,1.2)+L(`M${W/2+4} 16v6`,P.greyD,.8)+C(W/2+4,23,1,P.gold,.6)},
  dan_bau:{h:46,d:(W)=>shadow(W,30)+L(`M10 0l5-14M${W-10} 0l-5-14`,P.woodD,2.4)+R(6,-26,W-12,10,P.woodD,4)+Rn(9,-25,W-18,3,P.woodL,2)
    +[.3,.5,.7].map(t=>C(W*t,-20,1.3,P.gold,0)).join('')+L('M13 -26q-4-12 4-22',P.woodD,2.4)+C(18,-42,5.5,P.butterD,1.3)+Rn(16,-45,2,2,'#fff',1,.6)
    +L(`M16 -45L${W-12} -27`,P.greyD,.8)+R(W-14,-30,5,5,P.woodD,1.5,1)},
  binh_sen:{h:42,top:1,d:()=>Pa('M14 -2q-5-7 1-13q-2-3 0-5h10q2 2 0 5q6 6 1 13z',P.white)+L('M14.5 -9h11M15 -14h10',P.navy,1)+Pa('M18 -7l2-2l2 2l-2 2z',P.navy,0)
    +L('M20 -20q-1-8 1-14M17 -20q-5-6-7-8M23 -20q4-4 7-6',P.leafD,1.2)+E(11,-28,6,2.6,P.leaf,1.2)+E(30,-27,5,2.2,P.leafD,1.2)
    +Pa('M21 -34q-6-2-5-8q3 2 5 0q2 2 5 0q1 6-5 8z',P.pink,1.1)+Pa('M21 -34q-2-5 0-10q2 5 0 10z',P.pinkL,1)+E(8,-31,1.6,3,P.pinkD,1)},
  radio:{h:30,top:1,d:()=>L('M10 -20q10-9 20 0',P.greyD,2)+L('M30 -20l6-12',P.greyD,1.2)+C(36,-32,1,P.greyD,0)+R(3,-20,34,18,P.red,4)
    +C(11,-11,5.5,P.dark,1.2)+C(11,-11,2,P.darkL,0)+C(29,-11,5.5,P.dark,1.2)+C(29,-11,2,P.darkL,0)+R(16,-16,8,7,'#cfe6f1',1.5,1)+C(18.5,-12.5,1.2,P.dark,0)+C(21.5,-12.5,1.2,P.dark,0)
    +Rn(16,-7,8,2,P.cream,1)+[6,9,12].map(x=>Rn(x,-19,2,1.6,P.cream,.5)).join('')+shine(6,-18,24,1.5)},
  may_may:{h:52,d:(W)=>shadow(W,30)+L(`M8 0l4-20M${W-8} 0l-4-20M12 -4h${W-24}`,P.dark,2.6)+C(W-20,-12,6.5,'none',2)+L(`M${W-26} -12h12M${W-20} -18v12`,P.dark,1)
    +Pa(`M14 -4l10 3h20l10-3`,P.dark,1.6)+box(2,W-4,20,4,9,P.woodD,P.wood,2)
    +R(12,-44,6,14,P.dark,2)+R(12,-46,34,7,P.dark,3)+R(40,-44,7,15,P.dark,2)+L('M18 -42.5h20',P.gold,1)+L('M15 -30v3',P.greyD,1)
    +C(49,-40,4.2,P.greyD,1.2)+R(28,-51,3,5,P.redD,1,1)+Rn(19,-36,19,2,'#000',1,.15)},
  /* phòng ngủ */
  man_tuyn:{h:68,wall:1,d:(W,H)=>L(`M14 0v5M${W/2} 0v5M${W-14} 0v5`,P.greyD,1)+R(6,4,W-12,4,P.white,2,1.1)
    +Pa(`M7 7h${W-14}q4 ${H/2} 8 ${H-12}h${-W+2}q4 ${-(H/2)+12} 8 ${-(H-12)}z`,P.white,1.2,' fill-opacity=".62"')
    +L(Array.from({length:7},(_,i)=>`M${7+(W-14)*(i+1)/8} 8q${(i-3)*1.2} ${H/2} ${(i-3)*2.4} ${H-14}`).join(''),'#d9d2c8',1,' opacity=".9"')
    +L(Array.from({length:5},(_,i)=>`M8 ${16+i*10}h${W-16}`).join(''),'#e6dfd5',.8,' stroke-dasharray="1.5 3"')
    +L(`M1 ${H-5}h${W-2}`,P.pinkD,2.2)+Pa(`M10 ${H*.55}q6 3 2 8`,P.pink,1.1)+Pa(`M${W-10} ${H*.55}q-6 3-2 8`,P.pink,1.1)},
  ban_trang_diem:{h:72,d:(W)=>shadow(W,30)+R(W/2-2,-40,4,10,P.pinkD,1,1)+E(W/2,-55,14,17,P.white)+E(W/2,-55,10.5,13.5,'#dff1fb',1.1)
    +L(`M${W/2-6} -60l6-6M${W/2-3} -54l9-9`,'#fff',1.8)+[-62,-48].map(y=>C(W/2-14.5,y,1.8,P.butter,.8)+C(W/2+14.5,y,1.8,P.butter,.8)).join('')
    +legs([6,W-10],-16,16,P.pinkD)+box(2,W-4,14,10,10,P.pink,P.pinkL,3)+L(`M${W/2} -24v10`,OL,1.1)+C(W/2-8,-19,1.5,P.butter,1)+C(W/2+8,-19,1.5,P.butter,1)
    +R(8,-38,5,9,P.lilac,1.5,1)+R(8.5,-40,4,3,P.lilacD,1,1)+R(W-16,-36,6,7,P.peach,2,1)+shine(8,-33,W-20,1.5)},
  gau_bong_lon:{h:56,d:()=>shadow(40,30)+C(9,-48,5.5,P.peach)+C(31,-48,5.5,P.peach)+C(9,-48,2.5,P.pinkL,0)+C(31,-48,2.5,P.pinkL,0)
    +E(20,-18,15,14,P.peach)+E(20,-16,8,8,P.cream,1)+E(5,-22,5,9,P.peach)+E(35,-22,5,9,P.peach)+C(20,-38,12.5,P.peach)
    +E(20,-34,5.5,4,P.cream,1)+C(20,-35.5,1.6,OL,0)+eyes(15,25,-40,1.6)+blush(12,-35)+blush(28,-35)+L('M18.5 -32.5q1.5 1.5 3 0',OL,1)
    +E(11,-4,6.5,4,P.peach)+E(29,-4,6.5,4,P.peach)+C(11,-4,2.2,P.pinkL,0)+C(29,-4,2.2,P.pinkL,0)
    +Pa('M20 -27l-6-3v6zM20 -27l6-3v6z',P.red,1.1)+C(20,-27,1.6,P.redD,1)},
  den_sao:{h:26,top:1,g:()=>[20,-14,34],d:()=>R(11,-7,18,6,P.lilacD,2,1.2)+Pa('M10 -7q0-16 10-16q10 0 10 16z',P.lilac)
    +[[15,-14,2.6],[23,-17,2.2],[25,-10,1.8],[18,-9,1.5]].map(([x,y,r])=>star(x,y,r,P.butter)).join('')+star(5,-24,1.8,P.butterD)+star(35,-22,1.6,P.butterD)+C(31,-30,.9,P.butterD,0)},
  moc_ao:{h:84,d:()=>shadow(40,30)+L('M8 0l12-8l12 8',P.woodD,2.4)+R(18.5,-82,3,76,P.woodD,1.5,1.1)+L('M20 -76l-7-3M20 -76l7-3M20 -66l-6-2',P.woodD,1.6)+C(20,-83,2,P.woodD,1)
    +Pa('M13 -79l-5 4v30l5 3l5-3v-30z',P.sky,1.3)+L('M13 -77v31',P.skyD,1)+L('M27 -79q3 6 0 22q-3 6 2 10',P.pinkD,3.2)+L('M27 -79q3 6 0 22q-3 6 2 10',P.pink,1.6)
    +L('M25 -66q4 8 3 14',OL,1)+R(23,-54,11,12,P.butterD,3,1.2)+Rn(25,-50,7,2,P.butter,1)},
  /* bếp */
  am_sieu_toc:{h:30,top:1,d:()=>E(20,-2.5,11,2.5,P.dark,1.2)+R(10,-6,20,4,P.dark,1.5,1.1)+Pa('M12 -6l1-17q0-3 3-3h8q3 0 3 3l1 17z',P.mint)
    +Pa('M13 -22l-5-2l2-2l4 1z',P.mintD,1.1)+L('M27 -22q6 0 6 6q0 5-5 6',P.dark,2.6)+E(20,-26,6,1.8,P.mintD,1.1)+C(20,-28,1.4,P.dark,0)
    +Rn(15,-20,2.4,11,'#bfe7f7',1)+C(24,-8,1,'#62d26f',0)+L('M10 -30q-2-3 0-6M14 -32q-2-3 0-6',P.greyD,1,' opacity=".6"')+shine(22,-21,1.6,9)},
  lo_vi_song:{h:26,top:1,d:()=>E(20,-1.5,16,2,'#000',0,' opacity=".1"')+R(3,-24,34,22,P.white,3)+R(6,-21,21,16,P.dark,2,1.1)+Rn(8,-19,17,12,'#4a4f60',1)
    +E(16.5,-10,6,1.6,'#6a6f80',0)+Rn(9,-18,4,10,'#fff',1,.18)+Rn(29,-21,6,3.5,'#62d26f',1)+[-14,-10,-6].map(y=>C(30.5,y,1.1,P.greyD,0)+C(33.5,y,1.1,P.greyD,0)).join('')
    +L('M27 -21v16',P.grey,1)},
  chan_bat:{h:80,d:()=>shadow(40,30)+legs([6,30],-8,8,P.woodD)+R(4,-76,32,68,P.wood,3)+R(2,-79,36,5,P.woodD,2)
    +[[7,-72],[21,-72]].map(([x,y])=>R(x,y,12,28,'#f3eadc',1.5,1.1)+L(Array.from({length:5},(_,i)=>`M${x+2+i*2} ${y+1}v26`).join('')+Array.from({length:6},(_,i)=>`M${x} ${y+3+i*4.5}h12`).join(''),'#c9b494',.6)).join('')
    +E(13,-60,4.2,1.5,P.white,1)+E(13,-62,3.6,1.3,P.white,1)+E(27,-54,4,1.4,P.skyL,1)+R(24,-68,6,8,P.white,1.5,.9)
    +R(7,-40,26,7,P.woodL,2,1.1)+C(20,-36.5,1.4,P.woodD,0)+R(7,-30,12,19,P.woodL,2,1.1)+R(21,-30,12,19,P.woodL,2,1.1)+C(17,-20,1.3,P.woodD,0)+C(23,-20,1.3,P.woodD,0)},
  tu_lanh_magnet:{h:92,d:(W)=>shadow(W,30)+R(4,-92,W-8,92,P.mintL,7)+L(`M${W/2} -90v88`)+R(W/2-7,-74,3,26,P.greyD,1.5,1)+R(W/2+4,-74,3,26,P.greyD,1.5,1)
    +R(12,-62,14,16,P.grey,2,1.1)+Rn(15,-58,8,6,P.dark,1)+C(19,-50,1.2,P.skyD,0)
    +Pa(`M${W-24} -80q-3-4 0-6q2-1 3 1q1-2 3-1q3 2 0 6l-3 3z`,P.pink,1)+star(W-12,-72,3.4,P.butter)+C(W-28,-62,3,P.red,1)+leafE(W-27,-66,1.2,2,20,P.leafD)
    +R(W-26,-46,14,16,P.white,1,1)+L(`M${W-23} -41h8M${W-23} -38h6M${W-23} -35h8`,P.greyD,.9)+C(W-19,-47,1.6,P.sky,.8)
    +R(10,-84,10,7,P.butter,1.5,1)+L('M12 -81h6',P.butterD,1)+E(17,-30,4,3,P.lilac,1)+shine(8,-88,3,30)+shine(W/2+4,-88,3,12)},
  gio_trai_cay:{h:26,top:1,d:()=>E(20,-2,14,2.5,'#000',0,' opacity=".1"')+Pa('M12 -14q1-6 8-8q4 6 0 10z',P.butter,1.2)+C(13,-15,5,P.peachD)+C(26,-16,5,P.red)+leafE(27,-21,1.5,3,30,P.leafD)
    +[[19,-17],[22,-14],[18,-13],[21,-11]].map(([x,y])=>C(x,y,2.2,P.lilacD,1)).join('')+Pa('M5 -12h30l-4 11h-22z',P.woodL)
    +L('M7 -8h26M9 -4h22',P.woodD,.9)+L('M11 -12v11M16 -12v11M21 -12v11M26 -12v11M31 -12v11',P.woodD,.7)},
  /* nhà tắm, hồ bơi */
  duong_xi:{h:34,wall:1,d:(W)=>L(`M${W/2} 0L${W/2-10} 16M${W/2} 0L${W/2+10} 16M${W/2} 0v16`,P.woodD,1)+C(W/2,1,1.5,P.greyD,1)
    +leafE(W/2-12,24,3,9,25,P.leafD)+leafE(W/2+12,24,3,9,-25,P.leafD)+leafE(W/2-6,27,2.6,8,8,P.leaf)+leafE(W/2+6,27,2.6,8,-8,P.leaf)
    +Pa(`M${W/2-11} 16h22q-1 7-11 8q-10-1-11-8z`,P.woodL)+L(`M${W/2-9} 19h18`,P.woodD,.8)+leafE(W/2-8,12,2.4,6,-35,P.leafL)+leafE(W/2+8,12,2.4,6,35,P.leafL)+leafE(W/2,10,2.4,6,0,P.leaf)},
  nen_thom:{h:24,top:1,g:()=>[19,-18,22],d:()=>E(20,-1.5,14,2.2,'#000',0,' opacity=".1"')+R(10,-14,11,13,P.pinkL,3)+Rn(11,-12,9,3,P.pink,1)+R(22,-11,9,10,P.lilacL,3)+Rn(23,-9,7,2.4,P.lilac,1)
    +L('M15.5 -14v-3M26.5 -11v-3',OL,1)+Pa('M15.5 -17q-2.5-3 0-7q2.5 4 0 7z','#ffb84d',0)+Pa('M15.5 -18q-1-2 0-4q1 2 0 4z','#fff3b0',0)
    +Pa('M26.5 -14q-2-2.5 0-5.5q2 3 0 5.5z','#ffb84d',0)+leafE(7,-3,1.4,2.6,-50,P.leafD)},
  ao_choang:{h:34,wall:1,d:(W)=>C(W/2,4,2.2,P.greyD,1)+Pa(`M${W/2-11} 9q11-5 22 0l3 22h-28z`,P.skyL)+L(`M${W/2-6} 8l6 10l6-10`,OL,1.2)
    +Rn(W/2-12,20,24,3,P.skyD,1)+L(`M${W/2+3} 23l2 7M${W/2+6} 23l-1 6`,P.skyD,1.6)+R(W/2-9,24,6,5,P.sky,1.5,.9)+L(`M${W/2} 18v13`,P.skyD,.8)},
  phao_hong_hac:{h:48,d:(W)=>E(W/2,-5,W*.42,3.5,'#000',0,' opacity=".08"')+E(W/2-2,-11,27,9,P.pink)+E(W/2-6,-15,13,4.5,P.pinkL,1.1)
    +L(`M${W/2-26} -13q-6-6-2-10`,P.pinkD,2)+L(`M${W/2+18} -15q12-8 6-24q-3-7-10-4`,OL,8)+L(`M${W/2+18} -15q12-8 6-24q-3-7-10-4`,P.pink,5.4)
    +C(W/2+12,-42,5,P.pink)+Pa(`M${W/2+8} -41l-6 3l1 3l6-2z`,P.dark,1)+C(W/2+12.5,-43,1.1,OL,0)+blush(W/2+15,-39)},
  /* ban công, sân vườn */
  bonsai:{h:52,d:()=>shadow(40,30)+Pa('M19 -12q-7-8 1-16q6-6-2-13l4-2q9 8 2 16q-6 7 1 15z',P.woodD,1.2)+L('M21 -26q6-2 8-7M18 -36q-5-1-7-4',P.woodD,1.6)
    +E(11,-40,8,4.5,P.leafD)+E(29,-34,8,4.5,P.leafD)+E(20,-47,8,4.5,P.leaf)+E(9,-41.5,4,1.6,P.leafL,0)+E(27,-35.5,4,1.6,P.leafL,0)+E(18,-48.5,4,1.6,P.leafL,0)
    +E(29,-12,3,1.6,P.grey,1)+Pa('M4 -12h32l-3 10h-26z',P.navy)+Rn(4,-13,32,3,'#3a4670',1)+R(8,-3,4,3,P.navy,1,1)+R(28,-3,4,3,P.navy,1,1)},
  long_chim:{h:94,d:()=>shadow(40,30)+E(20,-3,9,3,P.woodD)+R(18.5,-62,3,60,P.woodD,1.5,1.1)+L('M20 -92v-4',P.woodD,1.4)
    +Pa('M8 -66v-12q0-14 12-14q12 0 12 14v12z',P.cream,1.3,' fill-opacity=".55"')+L('M8 -78h24',P.woodD,1)
    +E(18,-71,5.5,3.6,'#8a7a66',1.1)+Pa('M13 -70l-5 2l1-3z','#8a7a66',1)+C(23,-74,3.4,P.dark,1.1)+Pa('M22 -77l1-4l2 3z',P.dark,1)+C(24.5,-73.5,1,P.red,0)
    +E(21.5,-71,1.6,1.4,P.white,0)+Pa('M26 -74l2.5 .6l-2.5 .9z',P.greyD,0)+L('M10 -68h20',P.woodD,1.1)
    +L('M12 -66v-20M16 -66v-24M20 -66v-26M24 -66v-24M28 -66v-20',P.woodL,1.1)+R(6,-68,28,4,P.wood,2,1.2)+C(20,-93,2,P.woodD,1)},
  xe_dap:{h:56,d:(W)=>shadow(W,30)+C(16,-14,12,'none',2.2)+C(W-16,-14,12,'none',2.2)+C(16,-14,10,'none',0)
    +L(`M16 -24v20M6 -14h20M${W-16} -24v20M${W-26} -14h20`,P.greyD,.6)+C(16,-14,1.6,P.greyD,0)+C(W-16,-14,1.6,P.greyD,0)
    +L(`M16 -14L34 -14L28 -34ZM28 -34L56 -36L58 -30L${W-16} -14M34 -14L58 -30M56 -36l1 -8`,P.mintD,3)+L('M34 -14l-3 12',P.greyD,1.6)
    +E(27,-37,6,2,P.dark,1)+L('M52 -44h9',P.dark,2.4)+R(W-24,-50,15,10,P.woodL,2,1.1)+L(`M${W-22} -46h11`,P.woodD,.8)
    +C(W-20,-52,2.2,P.pink,1)+C(W-15,-53,2.2,P.butter,1)+C(W-11,-51,2,P.pink,1)},
  ban_co_tuong:{h:30,d:(W)=>shadow(W,30)+legs([8,W-12],-12,12)+box(4,W-8,10,6,14,P.woodD,P.woodL,3)+Rn(10,-28,W-20,10,'#f2dcae',1)
    +L(`M10 -26.5h${W-20}M10 -24h${W-20}M10 -20.5h${W-20}M10 -18.5h${W-20}`+Array.from({length:9},(_,i)=>`M${10+i*(W-20)/8} -27v3M${10+i*(W-20)/8} -21v3`).join(''),'#b47a45',.6)
    +[[16,-25,P.red],[30,-24,P.red],[44,-26,P.dark],[58,-19,P.dark],[24,-19,P.red],[50,-22,P.dark]].map(([x,y,c])=>E(x,y,2.6,1.6,P.cream,1)+E(x,y,1.2,.7,c,0)).join('')},
  chum_nuoc:{h:46,d:()=>shadow(40,30)+Pa('M10 -38q-7 3-7 17q0 19 17 21q17-2 17-21q0-14-7-17z','#8a5d34')+E(20,-38,10.5,3.2,'#6b4a2e')+E(20,-38,8,2,'#7fb8e0',0)
    +L('M8 -30q12 4 24 0',  '#6b4a2e',1.1)+Rn(9,-30,3,14,'#fff',2,.22)+L('M26 -40l8-8',P.woodD,2)+E(26,-41,4,1.6,P.woodD,1)},
  /* Trung thu & Tết */
  long_den_sao:{h:34,wall:1,g:(W)=>[W/2,17,28],d:(W)=>L(`M${W/2} 0v4`)+star(W/2,17,13,P.red,1.4)+star(W/2,17,7,'#ffd36b',0)+star(W/2,17,13,'none',1.4)
    +L(`M${W/2} 30v3M${W/2-2} 29l-1 4M${W/2+2} 29l1 4`,P.gold,1.1)+C(W/2,4,1.4,P.gold,1)},
  den_keo_quan:{h:38,top:1,g:()=>[20,-16,26],d:()=>E(20,-1.5,12,2.2,'#000',0,' opacity=".1"')+L('M20 -30v-5',OL,1.2)+C(20,-36,2,P.gold,1)
    +R(11,-27,18,23,'#fff3c4',2,1.2)+Rn(13,-24,14,17,'#ffe08a',2,.5)
    +Pa('M14 -9l2-5h4l2-3l2 3v5h-2v-3h-4l-1 3z',OL,0,' opacity=".55"')+C(20,-19,1.6,OL,0).replace('/>',' opacity=".55"/>')+Pa('M23 -14l3-6l2 6z',OL,0,' opacity=".45"')
    +L('M14 -27v23M26 -27v23',P.redD,1)+R(9,-30,22,4,P.red,1.5,1.1)+R(9,-5,22,4,P.red,1.5,1.1)+L('M10 -1v3M30 -1v3',P.gold,1.2)},
  cay_mai:{h:68,d:()=>shadow(40,30)+L('M20 -16q-2-14-10-24M20 -16q3-18 12-30M20 -18q-1-20 2-40M14 -34q-5-4-8-12M28 -38q4-6 4-14',P.woodD,1.6)
    +[[10,-40],[6,-47],[32,-46],[32,-53],[22,-58],[17,-51],[25,-44],[13,-30],[28,-30],[20,-38]].map(([x,y],i)=>flower(x,y,i%3?P.butter:P.butterD,1.7)).join('')
    +Rn(7,-35,4,6,P.red,1)+Rn(29,-41,4,6,P.red,1)+Rn(8,-33,2,1,P.gold)+Rn(30,-39,2,1,P.gold)+pot(20,24,16,P.redD,'#a83c2e')+C(20,-8,3,P.gold,1)},
  canh_dao:{h:72,d:()=>shadow(40,30)+L('M20 -22q-4-16-12-28M20 -22q2-22 4-46M20 -22q6-14 14-22M14 -40q-6-2-10-8M23 -52q6-4 8-10',P.woodD,1.5)
    +[[8,-50],[4,-47],[13,-42],[23,-66],[26,-58],[31,-61],[34,-44],[29,-38],[18,-56],[22,-46]].map(([x,y],i)=>flower(x,y,i%2?P.pink:P.pinkL,1.7)).join('')
    +[[11,-54],[31,-50]].map(([x,y])=>C(x,y,1.4,P.pinkD,.8)).join('')
    +Pa('M14 -22q-1 8 2 12q-4 4-2 10h12q2-6-2-10q3-4 2-12z',P.cream)+L('M14.5 -6q5.5 3 11 0M16 -14h8',P.navy,1.1)},
  cau_doi:{h:68,wall:1,d:(W,H)=>{const glyph=(x,y,s)=>L(`M${x-3} ${y}h6M${x} ${y-3}v${4+s}M${x-3} ${y+3}l${2+s} 2M${x+3} ${y+2}l-2 3`,P.gold,1.2);
    const col=x=>R(x,6,13,H-14,P.red,1.5,1.3)+Rn(x+1.5,7.5,10,H-17,'none').replace('fill="none"','fill="none" stroke="#f2c14e" stroke-width=".8"')
      +[0,1,2,3].map(i=>glyph(x+6.5,15+i*(H-26)/4,i%2)).join('')+L(`M${x+6.5} 6v-4`,OL,1);
    return col(4)+col(W-17)+Pa(`M${W/2} ${H/2-12}l12 12l-12 12l-12-12z`,P.red,1.3)+glyph(W/2,H/2-1,1)+L(`M${W/2-4} ${H/2+5}h8`,P.gold,1.2)
      +R(W/2-14,4,28,9,P.redD,1.5,1.1)+L(`M${W/2-9} 8.5h4M${W/2-2} 7v3M${W/2+4} 8.5h5`,P.gold,1.1);}},
  mam_ngu_qua:{h:34,top:1,d:()=>E(20,-1.5,8,2,P.redD,1.2)+R(18,-7,4,6,P.redD,1,1)+E(20,-8,15,3,P.red,1.3)
    +Pa('M7 -10q2-9 9-10q-2 6-2 10z',P.butter,1.1)+Pa('M33 -10q-2-9-9-10q2 6 2 10z',P.butter,1.1)+C(20,-20,8,'#b8d66b',1.3)+Rn(16,-26,3,2,'#fff',1,.4)
    +E(11,-12,4.6,3.4,P.butterD,1.1)+E(29,-12,4.6,3.4,P.leafL,1.1)+C(28,-12.5,.7,P.leafD,0)+C(30.5,-11,.7,P.leafD,0)+C(16,-11,2.2,P.peachD,1)+C(24,-11,2.2,P.peachD,1)+leafE(20,-29,1.5,3,10,P.leafD)},
  /* after 1.7.15 (góp ý #192): phòng khách */
  sofa_don:{h:52,d:()=>shadow(40,30)+legs([7,29],-7,7)+R(5,-50,30,26,P.mintD,10)+R(9,-46,22,18,P.mint,8)+box(3,34,5,14,9,P.mintD,P.mintL,6)+R(0,-38,9,32,P.mint,6)+R(31,-38,9,32,P.mint,6)+C(20,-33,5,P.butter),
    back:()=>shadow(40,30)+legs([7,29],-7,7)+R(2,-50,36,44,P.mintD,10)+R(7,-44,26,30,P.mint,7)+L('M20 -42v26',P.mintD,1.3)+R(4,-11,32,5,P.mintD,3)},
  ke_tivi:{h:24,d:(W)=>shadow(W,30)+legs([6,W-10],-4,4)+box(2,W-4,3,12,8,P.wood,P.woodL,3)+L(`M${W/3} -15v12M${W*2/3} -15v12`,OL,1.2)+C(W/3-8,-9,1.4,P.cream,1)+C(W*2/3+8,-9,1.4,P.cream,1)+R(W/3+6,-13,W/3-12,8,P.woodD,2,1),
    back:(W)=>shadow(W,30)+legs([6,W-10],-4,4)+box(2,W-4,3,12,8,P.woodD,P.woodL,3)+C(W/2,-9,3,P.dark,1)+L(`M${W/2} -9q10 8 24 6`,P.dark,1.2)},
  ghe_bap_benh:{h:56,d:()=>shadow(40,30)+L('M4 -3q16 6 32 0',P.woodD,2.6)+L('M9 -2v-18M31 -2v-18',P.woodD,2.4)+R(9,-56,22,30,P.wood,6)+L('M14 -52v22M20 -53v24M26 -52v22',P.woodD,1)
    +box(6,28,18,4,7,P.woodD,P.woodL,3)+R(3,-32,5,12,P.wood,2,1)+R(32,-32,5,12,P.wood,2,1)+E(20,-27,10,3,P.peach,1.1),
    back:()=>shadow(40,30)+L('M4 -3q16 6 32 0',P.woodD,2.6)+L('M9 -2v-18M31 -2v-18',P.woodD,2.4)+box(6,28,18,4,7,P.woodD,P.woodL,3)+R(9,-56,22,34,P.woodD,6)+L('M14 -52v26M20 -53v28M26 -52v26',P.wood,1.4)},
  piano:{h:70,d:(W)=>shadow(W,30)+legs([6,W-10],-28,28,P.dark,5)+R(4,-70,W-8,40,P.dark,4)+Rn(8,-66,W-16,16,P.darkL,2)+R(W/2-14,-62,28,8,P.cream,1,1)+L(`M${W/2-10} -59h20`,P.greyD,.8)
    +R(2,-34,W-4,8,P.dark,2)+Rn(5,-33,W-10,5,P.white,1)+Array.from({length:Math.floor((W-12)/5)},(_,i)=>Rn(7+i*5,-33,2.4,3,P.dark)).join('')+R(W/2-6,-8,12,4,P.gold,1,1)+shine(10,-68,W-20,2),
    back:(W)=>shadow(W,30)+legs([6,W-10],-6,6,P.dark,5)+R(4,-70,W-8,66,P.dark,4)+Rn(9,-64,W-18,52,P.darkL,3)+L(`M${W/3} -64v52M${W*2/3} -64v52`,P.dark,1.4)},
  binh_gom:{h:62,d:()=>shadow(40,30)+L('M20 -36q-4-12-12-20M20 -36q2-14 6-24M20 -36q8-8 14-12',P.woodD,1.4)+[[8,-56],[26,-60],[34,-48],[14,-48]].map(([x,y])=>flower(x,y,P.white,1.4)).join('')
    +Pa('M12 -36q-4 4-4 14q0 14 12 22q12-8 12-22q0-10-4-14z',P.white)+L('M10 -24q10 4 20 0M11 -14q9 4 18 0',P.navy,1.2)+Pa('M17 -20l3-3l3 3l-3 3z',P.navy,0)+E(20,-36,8,2.4,P.white,1.3)},
  tranh_son_dau:{h:68,wall:1,d:(W,H)=>R(3,3,W-6,H-8,P.gold,3)+Rn(8,8,W-16,H-18,'#f6d9a8',1)+Rn(8,8,W-16,(H-18)*.45,'#ffcf9a',1)+C(W-22,18,5,'#fff3b0',0)
    +[[10,24],[26,20],[42,26],[56,22]].filter(([x])=>x<W-18).map(([x,y],i)=>R(x,y,14,H-y-12,[P.peachD,P.butterD,P.red,P.mintD][i],1,1)+Rn(x+3,y+6,3,4,P.cream)+Rn(x+8,y+6,3,4,P.cream)+Pa(`M${x-2} ${y}l9-6l9 6z`,P.redD,1)).join('')
    +L(`M12 ${H-12}h${W-24}`,'#8a5d34',1.4)+L(`M${W/2-6} 3l6-4l6 4`,OL,1.1)},
  khung_anh_bo:{h:34,wall:1,d:(W)=>[[6,6,18,22,P.woodD,P.skyL],[28,10,16,14,P.white,P.pinkL],[48,4,22,26,P.dark,P.mintL]].filter(([x,,w])=>x+w<W).map(([x,y,w,h,f,b],i)=>R(x,y,w,h,f,2)+Rn(x+3,y+3,w-6,h-6,b,1)
    +(i===0?C(x+w/2,y+h/2,3,P.peach,1):i===1?Pa(`M${x+w/2} ${y+h-4}q-4-3-4-5q0-2 4-1q4-1 4 1q0 2-4 5z`,P.red,0):Pa(`M${x+3} ${y+h-3}l6-8l4 4l5-6v10z`,P.leaf,0))).join('')},
  den_chum:{h:34,wall:1,g:(W)=>[W/2,18,44],d:(W)=>L(`M${W/2} 0v6`)+R(W/2-14,5,28,4,P.gold,2,1.1)+L(`M${W/2-12} 9q12 14 24 0`,P.gold,1.4)
    +[-16,-8,0,8,16].map((dx,i)=>L(`M${W/2+dx} 9v${8+(i%2)*4}`,P.gold,1)+Pa(`M${W/2+dx} ${17+(i%2)*4}l-2.5 4l2.5 4l2.5-4z`,'#dff1fb',1)).join('')+C(W/2,22,4,'#fff3b0',1)},
  tham_tron:{h:20,rug:1,d:(W,D)=>E(W/2,-D/2,W/2-4,D/2-6,P.peachD,0)+E(W/2,-D/2-2,W/2-5,D/2-7,P.peach)+E(W/2,-D/2-2,W/2-14,D/2-14,P.butter,1)+E(W/2,-D/2-2,W/2-24,D/2-20,P.peach,1)+C(W/2,-D/2-2,3,P.pinkD,0)},
  tham_dai:{h:14,rug:1,d:(W,D)=>R(3,-D+5,W-6,D-8,'#b9805a',4)+R(8,-D+8,W-16,D-14,'#e8c39a',3,1)+Array.from({length:Math.floor((W-24)/12)},(_,i)=>Pa(`M${16+i*12} ${-D/2-1}l4-4l4 4l-4 4z`,'#b9805a',0)).join('')
    +L(`M3 ${-D+7}h-2M3 -6h-2M${W-3} ${-D+7}h2M${W-3} -6h2`,'#b9805a',1.2)},
  bang_neon:{h:34,wall:1,g:(W)=>[W/2,17,W*.55],d:(W)=>{const t='M12 22q-6-1-5-6q1-5 6-4M17 12v10M17 17q4-3 5 0v5M27 15v7M27 12v.5M32 11v11M37 11v11';
    return R(4,5,W-8,24,P.dark,5)+L(t,'#ff7ab8',2.4)+L(t,'#ffe3f1',.8)+Pa(`M${W-20} 14q-3-4 0-6q2-1 3 1q1-2 3-1q3 2 0 6l-3 3z`,'#6be0c8',1)+C(10,5,1.4,P.greyD,0)+C(W-10,5,1.4,P.greyD,0);}},
  ke_tron:{h:34,wall:1,d:(W)=>L(`M${W/2-14} 23a14 14 0 1 1 28 0`,P.woodD,3.2)+L(`M${W/2-14} 23a14 14 0 1 1 28 0`,P.wood,1.4)+R(W/2-16,21,32,4,P.wood,1.5,1.2)+C(W/2,7,1.4,P.greyD,0)},
  chuong_gio:{h:34,wall:1,d:(W)=>L(`M${W/2} 0v5`)+E(W/2,6,9,2.4,P.woodL,1.2)+[-6,-2,2,6].map((dx,i)=>L(`M${W/2+dx} 7v${4+i%2*3}`,OL,.7)+R(W/2+dx-1.2,11+i%2*3,2.4,10+(i%3)*3,P.mintL,1,.9)).join('')
    +L(`M${W/2} 7v18`,OL,.7)+Pa(`M${W/2-3} 25h6l-1 6h-4z`,P.pink,1)},
  may_chieu:{h:26,top:1,g:()=>[20,-30,40],d:()=>E(20,-2,11,2.5,'#000',0,' opacity=".1"')+R(10,-8,20,7,P.navy,3)+C(20,-16,10,P.navy)+C(20,-16,7,'#3a4670',1)
    +[[17,-19,2],[23,-14,1.6],[16,-12,1.3],[24,-20,1.2]].map(([x,y,r])=>star(x,y,r,P.butter)).join('')+L('M12 -24l-6-8M20 -26v-9M28 -24l6-8',P.butter,1,' opacity=".7"')},
  /* phòng ngủ */
  giuong_don:{h:84,d:(W,D)=>shadow(W,D)+R(3,-D-26,4,D+24,P.dark,1.5,1.1)+R(W-7,-D-26,4,D+24,P.dark,1.5,1.1)+L(`M5 ${-D-20}h${W-10}M5 ${-D-12}h${W-10}`,P.dark,2)
    +L(Array.from({length:5},(_,i)=>`M${14+i*(W-28)/4} ${-D-20}v8`).join(''),P.dark,1.4)+R(6,-D-4,W-12,D-6,P.white,5)+E(W*.5,-D+2,18,6,P.cream)
    +Pa(`M7 ${-D*0.6}q${W/2-7} -6 ${W-14} 0v${D*0.6-12}h${-(W-14)}z`,P.butter)+[.25,.5,.75].map(t=>C(W*t,-D*0.33,1.8,P.butterD,0)).join('')+R(3,-14,W-6,6,P.dark,2),
    back:(W,D)=>shadow(W,D)+R(6,-D-4,W-12,D-6,P.white,5)+Pa(`M7 ${-D*0.75}q${W/2-7} -6 ${W-14} 0v${D*0.75-12}h${-(W-14)}z`,P.butter)+R(3,-D-14,W-6,6,P.dark,2)
      +R(3,-40,4,38,P.dark,1.5,1.1)+R(W-7,-40,4,38,P.dark,1.5,1.1)+L(`M5 -34h${W-10}M5 -26h${W-10}`,P.dark,2)+L(Array.from({length:5},(_,i)=>`M${14+i*(W-28)/4} -34v8`).join(''),P.dark,1.4)},
  tu_ngan_keo:{h:32,d:()=>shadow(40,30)+legs([7,29],-4,4)+box(4,32,3,22,7,P.woodL,P.wood)+L('M6 -18h28M6 -11h28',P.woodD,1.2)+[-21,-14,-7].map(y=>R(17,y,6,2.4,P.woodD,1,.9)).join(''),
    back:()=>shadow(40,30)+legs([7,29],-4,4)+box(4,32,3,22,7,P.woodD,P.wood)+L('M12 -23v18M28 -23v18',P.wood,1)},
  guong_dung:{h:86,d:()=>shadow(40,30)+L('M10 0l6-10M30 0l-6-10',P.woodD,2.2)+R(9,-86,22,78,P.woodL,10)+R(12,-83,16,72,'#dff1fb',8,1.1)+L('M15 -70l8-8M15 -58l12-12',P.white,2)+C(20,-10,1.6,P.woodD,0),
    back:()=>shadow(40,30)+L('M10 0l6-10M30 0l-6-10',P.woodD,2.2)+R(9,-86,22,78,P.woodD,10)+R(12,-83,16,72,P.wood,8,1)+L('M20 -80v66',P.woodD,1)},
  den_trang:{h:30,top:1,g:()=>[20,-16,26],d:()=>E(20,-2,9,2.5,P.woodD)+R(18.5,-6,3,5,P.woodD,1,.9)+Pa('M24 -28a12 12 0 1 0 0 22a9 9 0 1 1 0-22z','#fff3b0')+C(14,-18,1.6,P.butterD,0)+C(17,-11,1,P.butterD,0)+star(30,-24,2.2,P.butter)},
  goi_tua:{h:22,top:1,d:()=>E(20,-3,13,3,'#000',0,' opacity=".1"')+Pa('M6 -20q14-4 28 0q-2 9 0 18q-14 4-28 0q2-9 0-18z',P.butter)
    +L('M10 -16q10-2 20 0M9 -10q11-2 22 0M10 -5q10-2 20 0M14 -20q-2 9 0 18M20 -21q-1 9 0 19M26 -20q2 9 0 18',P.butterD,.9)+C(6,-20,1.6,P.butterD,0)+C(34,-20,1.6,P.butterD,0)},
  rem_voan:{h:68,wall:1,d:(W,H)=>R(0,1,W,3,P.gold,1.5,1.1)+Pa(`M3 4h${W-6}q-4 ${H/2} 2 ${H-8}h${-(W-2)}q6 ${-(H/2)} 2 ${-(H-8)}z`,P.white,1.2,' fill-opacity=".7"')
    +L(`M10 6q-2 ${H/2} 0 ${H-12}M20 6q2 ${H/2} 0 ${H-10}M30 6q-2 ${H/2} 0 ${H-12}`,'#e6dfd5',1)+L(`M3 ${H*.55}q${W/2} 6 ${W-6} 0`,P.gold,1.6)},
  tho_bong:{h:34,top:1,d:()=>E(20,-8,9,7,P.white)+E(15,-30,3,9,P.white)+E(25,-30,3,9,P.white)+E(15,-30,1.4,6,P.pinkL,0)+E(25,-30,1.4,6,P.pinkL,0)+C(20,-17,7.5,P.white)
    +eyes(17,23,-18,1.2)+C(20,-15,1,P.pinkD,0)+blush(15,-14)+blush(25,-14)+C(14,-4,3,P.white)+C(26,-4,3,P.white)},
  ke_giay:{h:24,d:()=>shadow(40,30)+R(5,-24,3,24,P.woodD,1,1)+R(32,-24,3,24,P.woodD,1,1)+R(4,-24,32,4,P.wood,2,1.1)+R(4,-12,32,3,P.wood,1.5,1.1)
    +E(13,-15,6,3,P.red,1)+E(26,-15,6,3,P.sky,1)+E(14,-3,6,3,P.dark,1)+E(27,-3,6,3,P.butterD,1)},
  /* đồ chơi & đồ nhỏ */
  ngua_go:{h:46,d:()=>shadow(40,30)+L('M3 -4q17 8 34 0',P.redD,3)+L('M10 -2l3-14M30 -2l-3-14',P.woodD,2.2)+E(20,-20,11,6,P.wood)+Pa('M27 -24l5-14l7 3l-2 5l-5-1l-2 9z',P.wood)
    +L('M31 -37l-4 10',P.redD,2)+C(34,-34,1,OL,0)+L('M9 -22q-6 2-6 8',P.redD,2.4)+R(16,-28,8,4,P.red,1.5,1)},
  leu_choi:{h:76,d:(W)=>shadow(W,30)+Pa(`M6 -2L${W/2} -66L${W-6} -2z`,P.lilacL)+Pa(`M${W/2} -66L${W/2-14} -2h28z`,P.lilac,1.2)+Pa(`M${W/2} -40l-8 38h16z`,P.dark,1,' fill-opacity=".5"')
    +L(`M${W/2} -66l-4-6M${W/2} -66l4-6`,P.woodD,2)+[[16,-14],[26,-30],[W-18,-14],[W-26,-30]].map(([x,y])=>star(x,y,2.6,P.butter)).join('')+Pa(`M${W/2+2} -76h10l-3 3l3 3h-10z`,P.pink,1),
    back:(W)=>shadow(W,30)+Pa(`M6 -2L${W/2} -66L${W-6} -2z`,P.lilac)+L(`M${W/2} -66v64`,P.lilacD,1.2)+L(`M${W/2} -66l-4-6M${W/2} -66l4-6`,P.woodD,2)
      +[[20,-16],[W-20,-16],[W/2-8,-36],[W/2+8,-36]].map(([x,y])=>star(x,y,2.6,P.butter)).join('')},
  xep_hinh:{h:28,top:1,d:()=>R(6,-10,12,9,P.red,1.5,1.1)+R(19,-10,14,9,P.sky,1.5,1.1)+R(10,-19,14,9,P.butter,1.5,1.1)+R(14,-27,8,8,P.mint,1.5,1.1)
    +[[9,-10],[13,-10],[23,-10],[28,-10],[14,-19],[19,-19],[17,-27]].map(([x,y])=>Rn(x,y-2,3,2,'#fff',1,.5)).join('')},
  xe_do_choi:{h:22,top:1,d:()=>E(20,-2,13,2,'#000',0,' opacity=".1"')+Pa('M6 -6v-6q0-2 2-2h4l4-6h10l4 6h4q2 0 2 2v6z',P.red)+Rn(17,-18,4,4,'#cfe6f1',1)+Rn(23,-18,4,4,'#cfe6f1',1)
    +C(12,-5,3.4,P.dark)+C(28,-5,3.4,P.dark)+C(12,-5,1.2,P.grey,0)+C(28,-5,1.2,P.grey,0)},
  rubik:{h:22,top:1,d:()=>Pa('M10 -14l8-4l12 2l-8 4z',P.white,1.2)+Pa('M10 -14v12l12 2v-12z',P.red,1.2)+Pa('M22 -12v12l8-4v-12z',P.sky,1.2)
    +L('M14 -13.3v12M18 -12.6v12M10 -10l12 2M10 -6l12 2M24.6 -13.3v12M27.3 -14.6v12M22 -8l8-4M22 -4l8-4',OL,.7)+Rn(13,-16,4,1.5,P.butter)+Rn(19,-15.5,4,1.5,P.mint)},
  cau_tuyet:{h:32,top:1,d:()=>Pa('M9 -2l3-7h16l3 7z',P.woodD)+C(20,-18,11,'#dff1fb',1.3)+Pa('M14 -12l6-10l6 10z',P.leafD,1)+R(18.5,-12,3,3,P.woodD,1,.8)
    +[[13,-22],[25,-24],[18,-26],[27,-16],[12,-15]].map(([x,y])=>C(x,y,.9,'#fff',0)).join('')+shine(13,-25,3,6)},
  dong_ho_bao_thuc:{h:30,top:1,d:()=>L('M12 -2l3-4M28 -2l-3-4',P.dark,2)+C(13,-23,4,P.red)+C(27,-23,4,P.red)+C(20,-14,10,P.red)+C(20,-14,7.5,P.white,1.1)+L('M20 -14v-5M20 -14l3 2',OL,1.2)+C(20,-25.5,1.6,P.dark,0)},
  sach_mo:{h:24,top:1,d:()=>R(6,-8,28,7,P.sky,1.5,1.1)+Rn(8,-7,24,1.5,P.cream)+R(8,-14,24,6,P.red,1.5,1.1)+Pa('M7 -16q6-4 13 0q7-4 13 0v-1q-6-5-13-1q-7-4-13 1z',P.white,1.1)+R(28,-22,3,8,P.pink,1,.8)},
  /* bếp & ăn uống */
  bep_ga:{h:20,top:1,d:()=>R(3,-10,34,9,P.dark,2)+Rn(5,-6,6,2,P.greyD,1)+C(30,-5,1.8,P.grey,.8)+C(24,-5,1.8,P.grey,.8)+E(12,-12,7,2,P.greyD,1)+E(28,-12,7,2,P.greyD,1)
    +[8,11,14,24,27,30].map(x=>Pa(`M${x} -13q-1.5-3 0-5q1.5 2 0 5z`,'#6bb6ff',0)).join('')},
  treo_noi:{h:34,wall:1,d:(W)=>R(4,4,W-8,3,P.greyD,1.5,1)+[[14,0],[34,1],[52,2],[64,3]].filter(([x])=>x<W-6).map(([x,t])=>L(`M${x} 6v4`,P.dark,1.2)
    +[C(x,18,7,P.dark,1.3),R(x-8,12,16,12,P.red,3)+R(x-10,13,3,3,P.redD,1,1)+R(x+7,13,3,3,P.redD,1,1),L(`M${x} 10v12`,P.woodD,1.6)+E(x,24,3.6,2.6,P.greyD,1),R(x-3,10,6,14,P.woodL,1.5,1)][t]).join('')},
  thot_dao:{h:16,top:1,d:()=>E(20,-2,15,2.5,'#000',0,' opacity=".1"')+R(5,-8,30,6,P.woodL,3)+C(31,-6,1.2,P.woodD,0)+Pa('M9 -10l14-2v3l-14 1z',P.grey,1)+R(22,-12,9,3,P.dark,1,1)+C(17,-9,2,P.red,.8)+C(13,-9,1.6,P.leaf,.8)},
  may_xay:{h:34,top:1,d:()=>Pa('M12 -10l-1-20h18l-1 20z','#dff1fb',1.2)+Rn(13,-22,14,11,P.pink,1,.85)+R(10,-33,20,4,P.dark,2,1)+L('M28 -26q5 0 5 6q0 4-4 5',OL,1.6)+R(10,-10,20,9,P.white,3)+C(20,-6,1.6,P.dark,0)},
  hu_dua:{h:24,top:1,d:()=>Pa('M12 -18h16v15q0 2-2 2h-12q-2 0-2-2z','#dff1fb',1.2)+Rn(13,-14,14,12,P.butterD,1,.7)+L('M15 -12q2-3 4 0M21 -9q2-3 4 0M16 -6q2-3 4 0',P.leafD,1)+R(11,-22,18,4,P.red,2,1.1)+Rn(13,-24,14,2,P.redD,1)},
  may_ca_phe:{h:34,top:1,d:()=>R(9,-32,22,30,P.dark,3)+R(9,-6,22,4,P.greyD,1.5,1)+Rn(12,-28,16,8,P.darkL,1)+C(16,-24,1.4,'#62d26f',0)+R(17,-19,6,3,P.greyD,1,1)+R(16,-12,8,6,P.white,1.5,1)
    +L('M24 -10q3 0 3 2q0 2-3 2',OL,1)+L('M18 -14v-3M21 -14v-2',P.woodD,.8)},
  dao_bep:{h:34,d:(W)=>shadow(W,30)+box(3,W-6,0,24,9,P.white,P.woodL,3)+L(`M${W/2} -22v20`,OL,1.2)+R(8,-20,W/2-12,8,P.white,2,1)+R(W/2+4,-20,W/2-12,8,P.white,2,1)
    +R(W/4-4,-17,8,2,P.greyD,1,.8)+R(W*3/4-4,-17,8,2,P.greyD,1,.8)+R(8,-10,W-16,6,P.mintL,2,1),
    back:(W)=>shadow(W,30)+box(3,W-6,0,24,9,P.mint,P.woodL,3)+R(10,-18,W-20,12,P.mintL,2,1)+[18,W/2,W-18].map(x=>C(x,-12,2,P.mintD,.8)).join('')},
  ghe_bar:{h:52,d:()=>shadow(40,30)+L('M12 -2l4-24M28 -2l-4-24',P.dark,2.2)+L('M13 -12h14',P.dark,1.6)+R(11,-52,18,20,P.redD,6)+E(20,-28,12,4,P.red)+E(20,-29,9,2.2,P.pinkL,0),
    back:()=>shadow(40,30)+L('M12 -2l4-24M28 -2l-4-24',P.dark,2.2)+L('M13 -12h14',P.dark,1.6)+E(20,-28,12,4,P.red)+R(11,-52,18,22,P.red,6)+L('M14 -44h12M14 -38h12',P.redD,1)},
  ro_rau:{h:32,d:()=>shadow(40,30)+leafE(12,-22,3,8,-25,P.leaf)+leafE(17,-24,3,8,0,P.leafL)+Pa('M24 -30l4 10l-6 0z',P.peachD,1)+leafE(26,-31,1.5,4,10,P.leafD)+C(30,-18,4,P.red,1)+E(16,-17,6,4,P.lilacD,1)
    +Pa('M4 -16h32l-4 14q-1 2-3 2h-18q-2 0-3-2z',P.woodL)+L('M6 -11h28M8 -6h24',P.woodD,.9)+L('M12 -16v15M20 -16v16M28 -16v15',P.woodD,.7)},
  lo_nuong_banh:{h:26,top:1,d:()=>R(4,-24,32,22,P.peach,4)+R(7,-21,19,15,P.dark,2,1.1)+Rn(9,-19,15,11,'#ffb35c',1,.75)+E(16.5,-10,5,2,P.butter,0)+C(31,-18,2,P.cream,1)+C(31,-11,2,P.cream,1)+L('M7 -5h19',P.peachD,1)},
  ke_chen:{h:34,wall:1,d:(W)=>R(3,4,3,26,P.woodD,1,1)+R(W-6,4,3,26,P.woodD,1,1)+R(3,13,W-6,3,P.wood,1,1)
    +[10,22,34,46,58].filter(x=>x<W-14).map((x,i)=>E(x+4,10,5,2,i%2?P.skyL:P.white,1)+C(x+4,21,5,i%2?P.white:P.skyL,1)+C(x+4,21,2,i%2?P.skyL:P.white,.7)).join('')+R(3,26,W-6,4,P.woodD,1.5,1.2)},
  /* nhà tắm */
  ke_my_pham:{h:34,wall:1,d:(W)=>R(8,12,6,14,P.pink,2,1)+R(9,9,4,3,P.pinkD,1,.8)+R(16,16,7,10,P.mint,2,1)+R(25,10,7,16,P.lilac,3,1)+C(28.5,8,2,P.lilacD,.8)+R(4,26,W-8,4,P.white,1.5,1.2)+C(W/2,4,1.4,P.greyD,0)},
  may_say_toc:{h:26,top:1,d:()=>L('M17 -2q-4 2-8 0',P.dark,1.2)+R(14,-14,6,12,P.pink,2.4)+R(8,-24,24,11,P.pink,5)+C(28,-18.5,4,P.pinkD,1.2)+C(28,-18.5,1.6,P.dark,0)+L('M33 -21h3M33 -17h3',P.greyD,1)+R(15,-11,4,2,P.white,1,.8)},
  gio_giat:{h:40,d:()=>shadow(40,30)+Pa('M14 -38q6-4 12 0q-2 4-6 4q-4 0-6-4z',P.sky,1.1)+Pa('M22 -36q6-6 10 0q-4 3-10 0z',P.pink,1.1)+Pa('M7 -34h26l-3 33h-20z',P.woodL)
    +L('M8 -26h24M9 -17h22M9 -8h22',P.woodD,.9)+L('M13 -34v33M20 -34v34M27 -34v33',P.woodD,.7)+R(6,-36,28,4,P.wood,2,1.1)},
  coc_ban_chai:{h:32,top:1,d:()=>L('M17 -14l-3-14M23 -14l3-15',P.sky,2)+R(12,-31,4,5,P.white,1,.8)+R(24,-32,4,5,P.white,1,.8)+Pa('M12 -14h16l-2 13h-12z',P.mintL)+Rn(13,-11,14,2,P.mint)},
  cay_truc:{h:60,d:()=>shadow(40,30)+[[14,-56],[20,-48],[26,-58]].map(([x,y])=>R(x-2,y,4,-y-14,P.leaf,1.5,1.1)+L(`M${x-2} ${y+12}h4M${x-2} ${y+26}h4`,P.leafD,1)+leafE(x+5,y+4,2,5,40,P.leafL)).join('')
    +pot(20,22,16,P.white,P.grey)+Rn(10,-9,20,3,P.red,1)},
  tu_thuoc:{h:34,wall:1,d:(W)=>R(6,4,W-12,26,P.white,3)+L(`M${W/2} 4v26`,OL,1)+Rn(W/2-9,15,7,2,P.red)+Rn(W/2-6.5,12.5,2,7,P.red)+C(W/2-3,20,1.2,P.greyD,0)+C(W/2+3,20,1.2,P.greyD,0)+R(W/2+3,9,7,8,'#dff1fb',1.5,.8)},
  /* ban công, sân vườn */
  ghe_trung:{h:92,d:()=>shadow(40,30)+E(20,-3,12,3,P.dark)+L('M20 -3v-74q0-12 10-12',P.dark,2.4)+L('M30 -89v10',P.dark,1.4)+Pa('M14 -78q-14 8-12 34q2 18 18 20q16-2 18-20q2-26-12-34z',P.woodL)
    +Pa('M14 -70q-8 8-7 24q2 12 13 14q11-2 13-14q1-16-7-24z',P.wood,1.2)+E(20,-38,10,5,P.cream,1.2)+L('M8 -60q12 6 24 0M6 -46q14 6 28 0',P.woodD,.9)},
  chau_cuc:{h:44,d:()=>shadow(40,30)+leafE(12,-20,4,8,-40,P.leafD)+leafE(28,-20,4,8,40,P.leafD)+[[12,-30],[20,-36],[28,-30],[16,-24],[25,-24],[20,-29]].map(([x,y],i)=>C(x,y,4.6,i%2?'#ffb02e':'#ffd34d',1)+C(x,y,1.6,'#e08a1e',0)).join('')+pot(20,22,16)},
  bon_hoa:{h:40,d:(W)=>shadow(W,30)+Array.from({length:Math.floor((W-12)/10)},(_,i)=>{const x=11+i*10;return L(`M${x} -16v-${10+(i%3)*4}`,P.leafD,1.2)+leafE(x-3,-20,1.6,4,-30,P.leaf)+C(x,-26-(i%3)*4,3.4,[P.pink,P.red,P.lilac,P.butter][i%4],1);}).join('')
    +box(3,W-6,0,14,6,P.woodD,'#8a5d34')+L(`M5 -8h${W-10}`,P.wood,1)},
  ho_ca_koi:{h:30,d:(W)=>E(W/2,-14,W/2-2,13,P.grey)+[[8,-14],[W-8,-15],[W/2,-26],[W/2-20,-4],[W/2+18,-4],[16,-23],[W-16,-24]].map(([x,y])=>E(x,y,5,3.4,P.greyD,1)).join('')
    +E(W/2,-14,W/2-9,8.5,'#7fb8e0',1.2)+E(W/2,-15,W/2-14,5,'#a9d6f5',0)+E(W/2-8,-15,5,2,P.peachD,1)+Pa(`M${W/2-14} -15l-3-2v4z`,P.peachD,1)+E(W/2+10,-12,4.5,1.8,P.white,1)+Pa(`M${W/2+15} -12l3-2v4z`,P.white,1)
    +C(W/2+11,-12.6,.9,P.red,0)+leafE(W/2+20,-17,4,2,0,P.leaf)},
  ghe_dai:{h:44,d:(W)=>shadow(W,30)+legs([8,W-12],-14,14,P.dark,4)+R(4,-44,W-8,7,P.wood,2)+R(4,-35,W-8,7,P.wood,2)+box(2,W-4,14,4,9,P.wood,P.woodL,2)+R(4,-30,4,16,P.dark,1,1)+R(W-8,-30,4,16,P.dark,1,1),
    back:(W)=>shadow(W,30)+legs([8,W-12],-14,14,P.dark,4)+box(2,W-4,14,4,9,P.woodD,P.wood,2)+R(4,-44,W-8,7,P.woodD,2)+R(4,-35,W-8,7,P.woodD,2)+L(`M14 -44v18M${W-14} -44v18`,P.dark,2.6)},
  den_bao:{h:34,top:1,g:()=>[20,-17,24],d:()=>E(20,-2,9,2.4,P.redD,1.1)+R(12,-6,16,4,P.redD,1.5,1)+Pa('M14 -6q-4-10 0-18h12q4 8 0 18z','#fff3c4',1.2)+Pa('M20 -10q-3-4 0-8q3 4 0 8z','#ffb84d',0)
    +R(13,-26,14,3,P.redD,1.5,1)+L('M15 -26q5-8 10 0',P.dark,1.4)+L('M14 -6q-4-10 0-18M26 -6q4-10 0-18',P.redD,1.2)},
  nha_cho:{h:52,d:()=>shadow(40,30)+R(5,-34,30,32,P.woodL,2)+Pa('M2 -32L20 -52L38 -32z',P.red)+Pa('M13 -2v-16q0-7 7-7q7 0 7 7v16z',P.dark,1.2)+R(14,-46,12,5,P.white,1,1)+L('M16 -43.5h8',P.woodD,.8)+E(20,-5,6,2.5,P.butterD,1),
    back:()=>shadow(40,30)+R(5,-34,30,32,P.wood,2)+Pa('M2 -32L20 -52L38 -32z',P.redD)+L('M8 -24h24M8 -14h24',P.woodD,1)},
  binh_tuoi:{h:24,top:1,d:()=>E(20,-2,12,2.4,'#000',0,' opacity=".1"')+L('M28 -10l8-8',P.leafD,2.4)+E(37,-19,2.2,3,P.leafD,1,' transform="rotate(45 37 -19)"')+Pa('M9 -2v-14q0-4 4-4h10q4 0 4 4v14z',P.leaf)+L('M12 -20q6-8 12 0',P.leafD,2)},
  /* 🏰 villa pieces (game/estates_content.py ITEMS, 07/10): each room type's signature furniture */
  giuong_king:{h:104,d:(W,D)=>shadow(W,D)+legs([4,W-8],-6,6,P.woodD)+R(0,-D-44,W,42,P.woodD,10)+R(8,-D-38,W-16,30,'#8a5a3a',7)+L(`M${W/2} ${-D-38}v30`,P.woodD,1.4)
    +R(2,-D-4,W-4,D-6,P.white,6)+E(W*.28,-D+2,18,7,P.cream)+E(W*.72,-D+2,18,7,P.cream)
    +Pa(`M4 ${-D*0.6}q${W/2-4} -8 ${W-8} 0v${D*0.6-14}h${-(W-8)}z`,P.butter)+L(`M8 ${-D*0.42}h${W-16}`,P.gold,2)+R(2,-14,W-4,10,P.woodD,3)},
  ban_go_lim:{h:30,d:(W)=>shadow(W,30)+legs([6,W-12],-22,22,'#6b3f22',5)+box(2,W-4,20,6,10,'#6b3f22','#8a5232',3)+R(10,-26,18,2,P.cream,1,0)+R(W-30,-27,14,3,'#2f2f35',1,0)+shine(12,-35,W-30,1.6)},
  ghe_da_bo:{h:46,d:()=>shadow(40,30)+legs([8,28],-6,6,'#6b3f22')+R(3,-44,34,26,'#9a4f2e',9)+box(4,32,6,10,8,'#9a4f2e','#b8653d',5)+R(1,-30,8,24,'#b8653d',4)+R(31,-30,8,24,'#b8653d',4)
    +[10,20,30].map(x=>C(x,-38,1.2,'#6b3f22',0)).join('')},
  qua_dia_cau:{h:34,top:1,d:()=>E(20,-2,9,2.4,'#000',0,' opacity=".1"')+R(14,-6,12,4,P.woodD,1.5,1)+L('M20 -6v-4',P.woodD,2)+C(20,-20,10,P.sky)
    +Pa('M14 -24q4-4 8 0q2 4-2 6q-4 0-6-6zM22 -14q4-2 6 2q-2 3-6 1z',P.leaf,1)+L('M10 -20a10 10 0 0 0 20 0',P.gold,1.6)},
  ghe_rap_doi:{h:52,d:(W)=>shadow(W,30)+R(2,-52,W-4,34,'#8e2b3a',9)+R(6,-48,W/2-8,26,'#b13a4c',7)+R(W/2+2,-48,W/2-8,26,'#b13a4c',7)
    +box(2,W-4,4,12,8,'#8e2b3a','#b13a4c',5)+R(0,-34,8,30,'#6e1f2c',3)+R(W/2-4,-34,8,30,'#6e1f2c',3)+R(W-8,-34,8,30,'#6e1f2c',3)+C(W/2,-35,2.4,P.butter,1)},
  may_bong_ngo:{h:64,d:()=>shadow(40,30)+R(8,-22,24,22,P.redD,3)+L('M10 -14h20',P.butter,2)+R(6,-58,28,36,'#f6f0e5',3)+Rn(9,-54,22,28,'#fff7d6',2)
    +[[13,-32],[19,-35],[25,-31],[16,-40],[23,-42],[28,-37],[12,-44]].map(([x,y])=>C(x,y,2.6,P.butter,.8)).join('')+R(6,-64,28,6,P.redD,2)},
  loa_cot:{h:74,d:()=>shadow(40,30)+R(9,-74,22,74,'#2c2a33',4)+C(20,-58,6,'#4a4754',1.2)+C(20,-58,2.4,'#1b1a20',0)+C(20,-34,8,'#4a4754',1.2)+C(20,-34,3,'#1b1a20',0)+C(20,-14,3,'#4a4754',1)},
  thung_ruou:{h:44,surface:22,d:()=>shadow(40,30)+Pa('M6 -8q-4-16 0-32h28q4 16 0 32z','#9a6438')+L('M5 -14h30M5 -34h30',P.dark,2.2)+L('M12 -40q-2 16 0 32M28 -40q2 16 0 32',P.woodD,1)+C(20,-24,3,P.woodD,1)+R(17,-25,6,2,'#6b3f22',1,0)},
  ban_nem_ruou:{h:40,d:(W)=>shadow(W,30)+legs([8,W-12],-24,24,'#6b3f22',4)+box(2,W-4,22,6,10,'#6b3f22','#8a5232',3)
    +R(12,-46,5,16,'#5a1a2a',1.5,1)+C(14.5,-48,2,'#5a1a2a',1)+Pa(`M${W-26} -40h8l-1 6q-3 3-6 0z`,'#f6e9ef',1)+L(`M${W-22} -34v6M${W-25} -28h6`,OL,1.2)+Pa(`M${W-23} -38h6l-1 3h-4z`,'#a3203a',0)},
  may_chay_bo:{h:56,d:(W)=>shadow(W,30)+R(2,-12,W-4,10,'#3d3a4a',4)+Rn(6,-12,W-14,4,'#2a2833',2)+L(`M${W-10} -12l6-34`,'#8d96a0',3)+R(W-14,-54,16,10,'#5a566b',3)+Rn(W-11,-52,10,5,'#7ec8e3',1)
    +L(`M${W-14} -36h-14`,'#8d96a0',2.4)},
  gia_ta:{h:46,d:(W)=>shadow(W,30)+L(`M6 0v-40M${W-6} 0v-40M6 -40h${W-12}M6 -20h${W-12}`,'#5a566b',3)+[12,22,W-22,W-12].map(x=>R(x-3,-30,6,20,'#2f2f35',2,1)).join('')
    +L(`M8 -36h${W-16}`,'#a39a90',2.6)+R(6,-41,8,10,'#2f2f35',2,1)+R(W-14,-41,8,10,'#2f2f35',2,1)},
  tu_giay:{h:68,wall:1,d:(W,H)=>R(2,2,W-4,H-4,'#f6f0e5',4)+Rn(5,5,W-10,H-10,'#e6f3f8',2)+[0.33,0.66].map(t=>L(`M5 ${H*t}h${W-10}`,'#c9d6dc',1.4)).join('')
    +[[10,H*.33-4,P.redD],[W-22,H*.33-4,P.dark],[12,H*.66-4,P.pinkD],[W-24,H*.66-4,P.butterD],[W/2-6,H-9,P.navy]].map(([x,y,c])=>Pa(`M${x} ${y}h8l4 3v2h-12z`,c,1)).join('')},
  dao_trang_suc:{h:36,surface:22,d:(W)=>shadow(W,30)+box(2,W-4,0,20,10,'#f6f0e5','#ffffff',4)+Rn(8,-28,W-16,6,'#e6f3f8',2,.9)
    +[[12,-24,P.gold],[22,-25,P.pinkD],[32,-24,P.skyD],[W-18,-25,P.mintD]].map(([x,y,c])=>C(x,y,2.4,c,1)).join('')+L(`M6 -10h${W-12}`,P.gold,1.6)},
  xe_may_co:{h:44,d:(W)=>shadow(W,30)+C(14,-12,10,'#2f2f35')+C(14,-12,5,'#c7d3db',1)+C(W-14,-12,10,'#2f2f35')+C(W-14,-12,5,'#c7d3db',1)
    +Pa(`M14 -12l12-16h${W-48}l10 16`,'none',2.4)+Pa(`M22 -26q10-12 26-10l10 10z`,'#5a9a8a')+R(W/2-8,-36,18,5,'#6b3f22',2,1)+L(`M${W-18} -30l6-12h6`,'#8d96a0',2.2)+C(W-10,-34,3,P.butter,1)},
  bien_neon:{h:34,wall:1,g:(W)=>[W/2,17,W*.55],d:(W,H)=>R(3,4,W-6,H-8,'#2a2833',5)+L(`M10 ${H-11}l6-14l6 14M28 ${H-11}v-14l10 14v-14M46 ${H-11}h-6v-14h6M${W-22} ${H-25}v14h6`,'#ff7ab8',2.6)
    +L(`M10 ${H-11}l6-14l6 14M28 ${H-11}v-14l10 14v-14`,'#ffd1e8',1)},
  lo_suoi_ngoai:{h:40,g:()=>[20,-22,30],d:()=>shadow(40,30)+E(20,-6,16,6,'#7d7a74')+E(20,-8,13,4,'#4a4754',1)+Pa('M12 -10q-2-12 6-18q0 8 4 10q2-10 8-12q2 12-4 20z','#ffb84d',1)
    +Pa('M16 -10q0-8 4-12q2 6 4 6q2 4-2 6z','#ffe08a',0)+L('M8 -4l-2 4M32 -4l2 4',P.dark,2)},
  quay_bar_ho:{h:54,surface:26,d:(W)=>shadow(W,30)+box(2,W-4,0,24,10,'#d9a066','#ecc28f',3)+[8,18,28,38,48,58,68].filter(x=>x<W-6).map(x=>L(`M${x} -24v22`,'#b47a45',1.2)).join('')
    +Pa(`M${W-24} -46q12-12 22 0z`,P.red,1)+L(`M${W-13} -46v10`,P.dark,1.6)+Pa('M12 -40h8l-2 6h-4z','#ff9a4d',1)+L('M16 -34v4',OL,1.2)+C(15,-41,1.6,P.leaf,0)},
  kinh_thien_van:{h:58,d:()=>shadow(40,30)+L('M20 -26l-10 26M20 -26l10 26M20 -26v26',P.dark,2)+`<g transform="rotate(-32 20 -36)">`+R(4,-42,30,11,P.navy,5)+R(30,-43,6,13,'#3a4670',2,1)+R(2,-40,4,7,P.gold,1,1)+'</g>'},
};
/* ↻ Xoay hướng: the back of the pieces from 1.7.15 and before that turn too (game/deco.py FACING_ITEMS; the new
 * ones above carry their own `back`). Seen from behind: the back panel in front, what faced you hidden behind it. */
const BACKS={
  giuong:(W,D)=>shadow(W,D)+legs([4,W-8],-6,6)+R(2,-D-4,W-4,D-6,P.white,6)+Pa(`M4 ${-D*0.8}q${W/2-4} -8 ${W-8} 0v${D*0.8-14}h${-(W-8)}z`,P.sky)
    +[0.2,0.4,0.6,0.8].map(t=>C(W*t,-D*0.55,2,P.skyL,0)).join('')+R(2,-40,W-4,34,P.woodD,12)+R(10,-34,W-20,22,P.wood,8),
  ban_lam_viec:(W)=>shadow(W,30)+legs([6,W-10],-22,22)+R(6,-20,W-12,14,P.wood,2)+box(2,W-4,20,6,10,P.woodD,P.woodL,3),
  ban_hoc:(W)=>shadow(W,30)+legs([5,W-9],-22,22)+R(5,-20,W-10,14,P.woodL,2)+box(2,W-4,20,5,10,P.wood,P.butter,3),
  ban_gaming:(W)=>shadow(W,30)+L(`M8 0l6-20M${W-8} 0l-6-20`,P.dark,3)+box(2,W-4,20,6,10,P.dark,P.darkL,3)+R(W/2-20,-62,40,24,P.dark,4)
    +R(W/2-7,-52,14,9,P.darkL,2,1)+R(W/2-2,-38,4,6,P.dark,1,1)+L(`M${W/2} -32q-4 12 -14 14`,P.dark,1.2),
  ghe_hoc:()=>shadow(40,30)+L('M20 -16v-6M8 -2l12-8l12 8M20 -10v8',P.dark,2.4)+C(8,-2,2,P.dark,0)+C(32,-2,2,P.dark,0)+C(20,-1,2,P.dark,0)
    +box(7,26,20,5,6,P.mintD,P.mint,4)+R(10,-50,20,26,P.mintD,7)+L('M20 -24v-4',P.dark,2),
  ghe_gaming:()=>shadow(40,30)+L('M20 -16v-6M8 -2l12-8l12 8',P.dark,2.4)+box(6,28,20,5,6,P.dark,P.darkL,4)+R(3,-30,6,10,P.red,2,1)+R(31,-30,6,10,P.red,2,1)
    +R(9,-66,22,44,P.dark,8)+Rn(13,-60,14,6,P.red,2),
  ghe_may:()=>shadow(40,30)+legs([8,28],-10,10)+box(5,30,8,5,6,P.wood,P.woodL,4)+E(20,-30,15,17,P.wood)+Pa('M10 -30q10-12 20 0M8 -22q12-10 24 0M12 -38q8-8 16 0','none',1),
  tu_quan_ao:(W)=>shadow(W,30)+legs([6,W-10],-6,6)+R(3,-92,W-6,86,P.woodD,5)+L(`M${W/3} -88v78M${W*2/3} -88v78`,P.wood,1.2)+R(1,-96,W-2,8,P.woodD,3),
  ke_sach:(W)=>shadow(W,30)+R(4,-88,W-8,88,P.woodD,4)+Rn(8,-84,W-16,80,P.wood,2)+L(`M8 -60h${W-16}M8 -32h${W-16}`,P.woodD,1.4),
  tu_lanh:()=>shadow(40,30)+R(4,-84,32,84,P.mintD,6)+R(9,-70,22,56,P.greyD,2,1.1)+L('M11 -64h18M11 -56h18M11 -48h18M11 -40h18M11 -32h18M11 -24h18',P.dark,1)+R(14,-80,12,6,P.mint,2,1),
  tu_lanh_magnet:(W)=>shadow(W,30)+R(4,-92,W-8,92,P.mintD,7)+R(12,-76,W-24,60,P.greyD,2,1.1)
    +L(Array.from({length:7},(_,i)=>`M14 ${-70+i*8}h${W-28}`).join(''),P.dark,1)+R(W/2-8,-88,16,6,P.mint,2,1),
  may_giat:()=>shadow(40,30)+R(3,-58,34,58,P.grey,6)+C(12,-46,3,P.greyD,1)+L('M12 -43q0 10 8 14',P.dark,1.6)+R(22,-44,10,6,P.white,1.5,1)+L('M8 -20h24M8 -14h24',P.greyD,1),
  ban_trang_diem:(W)=>shadow(W,30)+legs([6,W-10],-16,16,P.pinkD)+box(2,W-4,14,10,10,P.pinkD,P.pinkL,3)+R(W/2-2,-40,4,10,P.pinkD,1,1)+E(W/2,-55,14,17,P.pinkD)+E(W/2,-55,10,13,P.pink,1),
  chan_bat:()=>shadow(40,30)+legs([6,30],-8,8,P.woodD)+R(4,-76,32,68,P.woodD,3)+R(2,-79,36,5,P.woodD,2)+L('M20 -74v64M6 -42h28',P.wood,1.2),
  quat:()=>shadow(40,30)+E(20,-2,10,3,P.white)+R(18.5,-46,3,44,P.greyD,1,1)+C(20,-50,14,P.white)+C(20,-50,11,P.grey,1)
    +L('M9 -50h22M20 -61v22M12 -58l16 16M28 -58l-16 16',P.white,1.2)+C(20,-50,4,P.sky,1.2),
};
for(const [k,b] of Object.entries(BACKS))ART[k].back=b;

/* ---------------------------------------------------------------- the room */
/** Free placement: units to a grid cell (game/deco_content.py U) and what one unit is in drawing pixels. */
export const U=20,SX=CW/U,SF=FR/U,SW=WR/U;
export function geom(room){
  const W=room.cols*CW+PX*2,WY=CEIL+TOP,FY=room.wrows?WY+room.wrows*WR+BASE:(room.out?84:60);
  return {W,H:FY+room.frows*FR+12,WY,FY};
}

/** The light of the hour (minute of the day 0..1439): the sky, the beam through the window, the room's tint, how
 * much the lamps glow. Shared by the live room and the photo. */
export function lightAt(minute){
  const m=((Math.round(Number(minute))||0)%1440+1440)%1440;
  if(m>=330&&m<600)return {phase:'morning',night:false,sky:['#ffd9b8','#fff1d6'],beam:'#fff0c2',ba:.42,skew:.55,tint:'#ffe7c4',ta:.07,lamps:0};
  if(m>=600&&m<900)return {phase:'noon',night:false,sky:['#8fd0f4','#dff1fb'],beam:'#fffbe6',ba:.34,skew:.12,tint:'',ta:0,lamps:0};
  if(m>=900&&m<1080)return {phase:'golden',night:false,sky:['#ffb27a','#ffe2b0'],beam:'#ffcf8a',ba:.46,skew:-.6,tint:'#ffb066',ta:.1,lamps:.15};
  if(m>=1080&&m<1170)return {phase:'evening',night:true,sky:['#5a4f96','#e79bb0'],beam:'',ba:0,skew:0,tint:'#5b4f9a',ta:.16,lamps:.75};
  return {phase:'night',night:true,sky:['#232b52','#4a4f86'],beam:'',ba:0,skew:0,tint:'#1d2448',ta:.26,lamps:1};
}
/** 🌌 Máy chiếu dải ngân hà (góp ý #134/#192): stars and a soft violet haze over the back wall and the ceiling,
 * faint by day, bright once the lamps glow. Drawn over the pieces, under the light of the hour; no hit area. */
export function galaxy(room,G,Lt){
  const top=4,bottom=room.wrows?G.WY+room.wrows*WR:G.FY-8,w=G.W,glow=.3+.7*(Lt?.lamps||0);
  let seed=room.cols*97+room.wrows*13+7;const rnd=()=>(seed=(seed*16807)%2147483647)/2147483647;
  const stars=Array.from({length:10+room.cols*3},()=>{const x=8+rnd()*(w-16),y=top+rnd()*(bottom-top-6),r=.8+rnd()*1.8;
    return r>2.1?star(x,y,r*1.6,'#fff3b0'):C(x,y,r*.7,'#ffffff',0);}).join('');
  return `<g class="dc-galaxy" pointer-events="none" aria-hidden="true" opacity="${glow.toFixed(2)}"><rect x="0" y="0" width="${w}" height="${bottom}" fill="#6b5bd6" opacity=".16"/>`
    +`<ellipse cx="${n(w*.55)}" cy="${n(bottom*.45)}" rx="${n(w*.42)}" ry="${n(bottom*.22)}" fill="#c9b8ff" opacity=".18" transform="rotate(-12 ${n(w*.55)} ${n(bottom*.45)})"/>${stars}</g>`;
}
/** Kept for older callers: is it dark outside right now (local clock)? */
export const night=()=>{const h=new Date().getHours();return h>=18||h<6;};

const WALLS={l0:'#eadcc3',l1:'#f9e7cf',l2:'#dfeee0',studio:'#f3e2cc',attic:'#ecd2ab',tro:'#d9eee5',loft:'#f6e3d3',bunk:'#e7dcf5',
  // 🏰 villa rooms (game/estates_content.py): each type its own colour under its theme's paper
  study:'#ead9bd',suite:'#efe4f2',cinema:'#3a2f40',cellar:'#cdb89c',gym:'#e3ecef',closet:'#f6e6ee',showroom:'#dfe3e8'};
const FLOORS={l0:'#cfc6b6',l1:'#efe6d6',l2:'#d29a63',attic:'#c99363',tro:'#eadfcf',loft:'#d7a874',bunk:'#fdf3ec',balcony:'#e2d3bf',yard:'#a8d58a',pool:'#efe2cc',
  study:'#b98a5a',suite:'#e9dccb',cinema:'#5a2f3a',cellar:'#9c8166',gym:'#3f4a52',closet:'#efe2d8',showroom:'#cfd5dc',terrace:'#d8c4a8',infinity:'#ece4d4',pavilion:'#a8d58a'};
/** 1.4.11: a bathroom (its own or the shared one) is tiled up to two thirds of the wall, and on the floor. */
const tiledRoom=room=>room.type==='bath'||room.type==='bathc';

/** Sky through a window or over a balcony, by the light of the hour. */
function sky(x,y,w,h,L,id){
  const [top,bot]=L.sky;
  let s=`<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${top}"/><stop offset="1" stop-color="${bot}"/></linearGradient></defs>`+Rn(x,y,w,h,`url(#${id})`);
  if(L.night)s+=C(x+w*.72,y+h*.3,Math.min(7,h*.18),'#fff4c4',0)+C(x+w*.72+3,y+h*.3-2,Math.min(6,h*.16),top,0)
    +[[.15,.2],[.35,.45],[.5,.15],[.85,.7],[.25,.75]].map(([a,b])=>C(x+w*a,y+h*b,1,'#fff',0)).join('');
  else{
    const sun=L.phase==='golden'?['#ff9a4d',.82,.62]:L.phase==='morning'?['#ffc46b',.2,.55]:['#ffd66b',.78,.28];
    s+=C(x+w*sun[1],y+h*sun[2],Math.min(7,h*.18),sun[0],0)+E(x+w*.32,y+h*.5,Math.min(10,w*.16),Math.min(4,h*.1),'#fff',0,' opacity=".9"')+E(x+w*.4,y+h*.45,Math.min(7,w*.12),Math.min(4,h*.1),'#fff',0,' opacity=".9"');
  }
  return s;
}

/* ---- wallpapers and floors (game/deco_content.py SKINS) */
const pat=(id,w,h,body,bg)=>`<pattern id="${id}" width="${w}" height="${h}" patternUnits="userSpaceOnUse">${bg?`<rect width="${w}" height="${h}" fill="${bg}"/>`:''}${body}</pattern>`;
const flower=(x,y,c,r=2)=>[0,72,144,216,288].map(a=>{const t=a*Math.PI/180;return C(x+Math.cos(t)*r*1.3,y+Math.sin(t)*r*1.3,r,c,0);}).join('')+C(x,y,r*.8,P.butter,0);
/** Wallpaper: [defs, fill] for the wall (0..FY). */
const WALL_SKIN={
  kem:id=>['','#fbeedb'],
  bac_ha:id=>['','#d5efe4'],
  hong_dao:id=>['','#fbdcd6'],
  soc:id=>[pat(id,28,10,Rn(0,0,10,10,'#f9cfd8')+Rn(14,0,6,10,'#cdebdc'),'#fdf3e4'),`url(#${id})`],
  cham_bi:id=>[pat(id,22,22,C(5,5,3,'#ffffff',0)+C(16,16,3,'#c9ddf2',0),'#e8f1fb'),`url(#${id})`],
  hoa_nhi:id=>[pat(id,34,30,flower(8,8,'#f9c2d1',1.7)+flower(25,22,'#bfd8f2',1.7)+C(25,7,1.1,P.leaf,0)+C(8,23,1.1,P.leaf,0),'#fff6f0'),`url(#${id})`],
  may_sao:id=>[pat(id,64,44,E(14,12,10,4,'#ffffff',0)+E(20,10,7,4,'#ffffff',0)+`<path d="M46 26l1.5 3.5l3.5 1.5l-3.5 1.5l-1.5 3.5l-1.5-3.5l-3.5-1.5l3.5-1.5z" fill="#ffe08a"/>`+C(56,8,1.4,'#ffe08a',0)+C(30,36,1.2,'#ffffff',0),'#dce6fb'),`url(#${id})`],
  gach_the:id=>[pat(id,26,14,Rn(1,1,24,5,'#f0d3bf',1)+Rn(-12,8,24,5,'#ecccb6',1)+Rn(14,8,24,5,'#f0d3bf',1),'#f8e8dc'),`url(#${id})`],
  op_go:id=>['','#f7ead6'],
  // 🏰 the villas' themes (game/estates_content.py SKINS)
  go_thong:id=>[pat(id,26,40,Rn(0,0,26,40,'#e3c79c')+Rn(25,0,1,40,'#c9a678')+C(9,14,1.2,'#c9a678',0)+C(18,30,1,'#c9a678',0),''),`url(#${id})`],
  dong_duong:id=>[pat(id,60,60,Rn(0,0,60,60,'#f4dfa2')+Rn(8,8,14,30,'#5f9a7a',1)+Rn(38,8,14,30,'#5f9a7a',1)+L('M8 14h14M8 20h14M8 26h14M8 32h14M38 14h14M38 20h14M38 26h14M38 32h14','#4a7d62',1),''),`url(#${id})`],
  kinh:id=>[pat(id,48,80,Rn(0,0,48,80,'#cfe6f2')+Rn(0,0,2,80,'#9fb8c6')+Pa('M8 70l30-50h6l-30 50z','#ffffff',0,' opacity=".45"'),''),`url(#${id})`],
  trang_bien:id=>[pat(id,40,40,Rn(0,0,40,40,'#f8fbfc')+Rn(0,30,40,10,'#bfe0ee')+L('M0 34q5-3 10 0t10 0t10 0t10 0','#7fb8e0',1.2),''),`url(#${id})`],
  nhung:id=>[pat(id,24,60,Rn(0,0,24,60,'#6e1f2c')+Rn(0,0,6,60,'#5a1824')+Rn(12,0,3,60,'#7f2836'),''),`url(#${id})`],
  da_hoc:id=>[pat(id,44,30,Rn(0,0,44,30,'#b9a385')+R(1,1,20,12,'#cdb89c',3,.8)+R(23,1,20,12,'#c4ad8f',3,.8)+R(-10,16,20,12,'#c4ad8f',3,.8)+R(12,16,20,12,'#cdb89c',3,.8)+R(34,16,20,12,'#c4ad8f',3,.8),''),`url(#${id})`],
};
export const SKIN_WALL=Object.keys(WALL_SKIN);
/** Floor: [defs, fill]. */
const FLOOR_SKIN={
  go_sang:id=>[pat(id,90,15,Rn(0,14,90,1,'#c99a62')+Rn(30,0,1,15,'#c99a62')+Rn(75,0,1,15,'#d4a970'),'#e8c597'),`url(#${id})`],
  gach_trang:id=>[pat(id,30,22,Rn(0,0,30,1,'#ddd6c8')+Rn(0,0,1,22,'#ddd6c8'),'#f6f2ea'),`url(#${id})`],
  chieu:id=>[pat(id,12,12,Rn(0,0,6,6,'#dcc07a',0,.7)+Rn(6,6,6,6,'#dcc07a',0,.7)+Rn(0,11,12,1,'#c8a85e',0,.6),'#ead69c'),`url(#${id})`],
  caro:id=>[pat(id,30,22,Rn(0,0,15,11,'#f2b8a8')+Rn(15,11,15,11,'#f2b8a8'),'#fdf3e6'),`url(#${id})`],
  tham_len:id=>[pat(id,14,12,C(4,4,1.3,'#fbe0e7',0)+C(11,9,1.3,'#e9b3c2',0),'#f6c9d4'),`url(#${id})`],
  gach_bong:id=>[pat(id,30,30,Rn(0,0,30,30,'#e7f0ec')+Pa('M15 3l5 12l-5 12l-5-12z','#7fb8a8',0)+Pa('M3 15l12-5l12 5l-12 5z','#7fb8a8',0)+C(15,15,3.5,'#f2c14e',0)+Rn(0,0,30,1,'#cfdcd6')+Rn(0,0,1,30,'#cfdcd6'),''),`url(#${id})`],
  xuong_ca:id=>[pat(id,24,24,`<path d="M0 12l12-12h6l-12 12zM12 24l12-12v6l-6 6z" fill="#c78d55"/><path d="M12 0l12 12v6l-12-12zM0 12l12 12h-6l-6-6z" fill="#b97d47"/>`,'#d79b62'),`url(#${id})`],
  ga_ke:id=>[pat(id,16,16,Rn(0,0,8,16,'#f7b9c7',0,.45)+Rn(0,0,16,8,'#f7b9c7',0,.45),'#fff6f4'),`url(#${id})`],
  ga_may:id=>[pat(id,46,30,E(12,10,9,3.5,'#ffffff',0)+E(17,8,6,3.5,'#ffffff',0)+E(34,24,8,3,'#ffffff',0),'#cfe6f7'),`url(#${id})`],
  ga_dau:id=>[pat(id,26,22,Pa('M7 7q-4 0-4 4q0 5 4 7q4-2 4-7q0-4-4-4z','#ef7f72',0)+Pa('M5 7l2-3l2 3z',P.leaf,0)+C(19,17,1.3,'#f5a9bc',0),'#fff8ef'),`url(#${id})`],
  ga_meo:id=>[pat(id,30,26,C(9,10,4.5,'#ffffff',0)+Pa('M5 8l0-5l3 3zM13 8l0-5l-3 3z','#ffffff',0)+C(7.5,10,.8,OL,0)+C(10.5,10,.8,OL,0)+C(23,21,1.3,'#f5a9bc',0),'#dccff3'),`url(#${id})`],
};
// 🏰 the villas' floors (game/estates_content.py SKINS)
Object.assign(FLOOR_SKIN,{
  da_cam_thach:id=>[pat(id,60,30,Rn(0,0,60,30,'#f3efe8')+L('M4 22q14-10 26-4t28-8','#d9d2c8',1)+Rn(0,29,60,1,'#dcd5ca')+Rn(59,0,1,30,'#dcd5ca'),''),`url(#${id})`],
  go_oc_cho:id=>[pat(id,90,15,Rn(0,0,90,15,'#6b4a2e')+Rn(0,14,90,1,'#4f3520')+Rn(40,0,1,15,'#4f3520')+L('M6 6q20-3 30 1','#7d5a3a',1),''),`url(#${id})`],
  go_tau:id=>[pat(id,60,12,Rn(0,0,60,12,'#c99a62')+Rn(0,11,60,1,'#8e6440')+C(8,6,.9,'#8e6440',0)+C(52,6,.9,'#8e6440',0),''),`url(#${id})`],
  tham_do:id=>[pat(id,20,20,Rn(0,0,20,20,'#8e2b3a')+C(10,10,1.2,'#b13a4c',0),''),`url(#${id})`],
  cao_su:id=>[pat(id,30,30,Rn(0,0,30,30,'#3f4a52')+Rn(0,0,30,1,'#2f383f')+Rn(0,0,1,30,'#2f383f')+C(15,15,1,'#55606a',0),''),`url(#${id})`],
  gach_nung:id=>[pat(id,32,16,Rn(0,0,32,16,'#b4683f')+Rn(0,15,32,1,'#8a4a2a')+Rn(16,0,1,8,'#8a4a2a')+Rn(0,8,1,8,'#8a4a2a')+Rn(0,7,32,1,'#8a4a2a'),''),`url(#${id})`],
});
export const SKIN_FLOOR=Object.keys(FLOOR_SKIN);

/** A swatch of a skin for the drawer (its own SVG). */
export function swatch(id,part,size=54){
  const fn=(part==='wall'?WALL_SKIN:FLOOR_SKIN)[id],uid=`dcSw${part[0]}${id}`;
  if(!fn){   // Như ban đầu: the room as it came
    return `<svg class="dc-swatch" viewBox="0 0 54 40" width="${size}" height="${Math.round(size*40/54)}" aria-hidden="true" focusable="false">${Rn(0,0,54,40,part==='wall'?'#f3e2cc':'#eadfcf',6)}${L('M14 26l8-8l6 6l6-10l8 12','#c9b494',2)}</svg>`;
  }
  const [defs,fill]=fn(uid);
  return `<svg class="dc-swatch" viewBox="0 0 54 40" width="${size}" height="${Math.round(size*40/54)}" aria-hidden="true" focusable="false"><defs>${defs}</defs>${Rn(0,0,54,40,fill,6)}${id==='op_go'?Rn(0,22,54,18,'#d8a874')+Rn(0,20,54,3,'#b47a45')+L('M12 24v16M26 24v16M40 24v16','#c48f5c',1.2):''}</svg>`;
}

/** The fixtures: drawn with the room, under the furniture (the counter as a floor piece of its row). */
function fixture(f,room,G,parts,Lt,uid){
  const x=PX+f.x*CW,w=f.w*CW;
  if(f.layer==='wall'){
    const y=G.WY+f.y*WR,h=f.h*WR;
    if(f.t==='window'){const id=`dcSky${uid}${f.x}`;
      return R(x+3,y+2,w-6,h-6,'#fffaf1',4,1.5)+sky(x+7,y+6,w-14,h-14,Lt,id)+L(`M${x+w/2} ${y+6}v${h-14}${f.h>1?`M${x+7} ${y+h/2}h${w-14}`:''}`,'#fffaf1',3)
        +R(x+1,y+h-6,w-2,5,'#f2e6d2',2,1.2);}
    if(f.t==='door'){const top=y+2,bot=G.FY;
      return R(x+4,top,w-8,bot-top,P.woodD,4)+Rn(x+8,top+4,w-16,bot-top-4,P.wood,2)+R(x+11,top+8,w-22,(bot-top)*.32,P.woodL,2,1)+R(x+11,top+12+(bot-top)*.36,w-22,(bot-top)*.38,P.woodL,2,1)
        +C(x+w-11,top+(bot-top)*.56,2.2,P.gold,1.1);}
    if(f.t==='splash'){const lv=parts?.kitchen?.lv||0;
      let s=Rn(x,y,w,h+BASE,lv?'#eaf4f4':'#e6dccb')+Array.from({length:f.w*4},(_,i)=>L(`M${x+i*10} ${y}v${h+BASE}`,lv?'#cfe2e2':'#d6c9b3',.8)).join('')+L(`M${x} ${y+h/2}h${w}M${x} ${y+h}h${w}`,lv?'#cfe2e2':'#d6c9b3',.8);
      if(lv>=2)s+=Pa(`M${x+w-70} ${y-6}h44l10 ${h*0.5}h-64z`,'#c9d0d6')+R(x+w-54,y-30,12,26,'#c9d0d6',2,1.2);
      if(lv===1)s+=R(x+10,y-4,60,4,P.woodD,1.5,1.1)+[16,28,40,52].map(a=>R(x+a,y-12,8,8,[P.red,P.butter,P.mint,P.sky][a/12-1|0]||P.peach,1.5,1)).join('');
      if((parts?.kitchen?.c??100)<60)s+=E(x+w-48,y+4,26,12,'#4a3f35',0,' opacity=".22"');
      return s;}
    // 🏰 the villa rooms' signature fixtures (game/estates.py): bookshelves, the cinema screen, wine racks, the gym
    // mirror, the clothes rails, the showroom's roller door
    if(f.t==='bookwall'){const cols=['#c0504d','#4f81bd','#9bbb59','#f2c14e','#8064a2','#4bacc6'];
      return R(x+1,y,w-2,h+BASE-4,'#6b3f22',2)+[0,1,2,3].map(r=>Rn(x+5,y+4+r*((h+BASE-12)/4),w-10,(h+BASE-12)/4-3,'#8a5232',1)
        +Array.from({length:Math.floor((w-12)/7)},(_,i)=>Rn(x+7+i*7,y+6+r*((h+BASE-12)/4),5,(h+BASE-12)/4-7,cols[(i+r)%6],1)).join('')).join('');}
    if(f.t==='screen')return R(x,y-2,w,h-6,'#1b1a20',3)+Rn(x+4,y+2,w-8,h-14,Lt.night?'#dfe9ff':'#cfd8e6',2)+L(`M${x+w*.2} ${y+h*.55}l${w*.18} -${h*.25}l${w*.14} ${h*.15}l${w*.22} -${h*.3}`,'#8fa6c4',2);
    if(f.t==='racks')return R(x,y,w,h+BASE-4,'#6b3f22',2)+Array.from({length:Math.floor(w/14)*3},(_,i)=>C(x+9+(i%Math.floor(w/14))*14,y+10+Math.floor(i/Math.floor(w/14))*((h+BASE-12)/3),4.2,['#5a1a2a','#2f4a2a','#7a1f2e'][i%3],1)).join('');
    if(f.t==='mirror')return R(x+2,y,w-4,h+BASE-6,'#c7d3db',3)+Rn(x+6,y+4,w-12,h+BASE-14,'#eef6fa',2)+Pa(`M${x+12} ${y+h}l${w*.3} -${h*.8}h8l-${w*.3} ${h*.8}z`,'#ffffff',0,' opacity=".6"');
    if(f.t==='rails'){const c=[P.pink,P.sky,P.mint,P.butter,P.lilac,P.peach,P.red];
      return L(`M${x+4} ${y+6}h${w-8}`,'#a39a90',2.4)+Array.from({length:Math.floor((w-10)/10)},(_,i)=>Pa(`M${x+8+i*10} ${y+8}l-4 6v${h-4}h10v${-(h-4)}l-4 -6z`,c[i%7],1)).join('');}
    if(f.t==='gate')return R(x,y,w,G.FY-y,'#b8bec6',3)+Array.from({length:Math.floor((G.FY-y)/8)},(_,i)=>L(`M${x+3} ${y+6+i*8}h${w-6}`,'#9aa3ab',1.2)).join('');
    if(f.t==='slope')return Pa(`M${x-PX} ${y-TOP-CEIL}h${w+PX+20}L${x-PX} ${y+h+10}z`,'#b98a5e')+L(`M${x-PX} ${y+h-6}L${x+w+6} ${y-TOP-CEIL}M${x-PX} ${y+h-24}L${x+w-14} ${y-TOP-CEIL}`,'#8e6440',2.4);
    if(f.t==='shelf'){const ly=y+(f.ledge||24);   // the dorm's shelf over the pillow: a plank on two brackets
      return Rn(x+6,ly+5,w-12,3,'#000',1,.08)+Pa(`M${x+12} ${ly+4}v8l8-8z`,P.woodD,1.2)+Pa(`M${x+w-12} ${ly+4}v8l-8-8z`,P.woodD,1.2)+R(x+3,ly,w-6,5,P.woodL,2,1.3)+Rn(x+6,ly+1,w-12,1.4,'#fff',0,.5);}
    if(f.t==='shower'){const v=y+h*.55;   // the shower on the bathroom wall: its pipe and head, the tap, the hose, the drain
      return Rn(x+2,y,w-4,G.FY-y,'#cfe8ec',3,.55)+L(`M${x+30} ${y+2}v10h-12`,'#9aa7b0',3)+E(x+16,y+14,8,3,'#c7d3db',1.3)
        +L(`M${x+12} ${y+20}v8M${x+16} ${y+19}v12M${x+20} ${y+20}v7`,'#7fb8e0',1.3,' opacity=".75"')
        +R(x+26,v,8,10,'#c7d3db',2,1.1)+L(`M${x+30} ${v+10}q-14 6-8 ${G.FY-v-16}`,'#9aa7b0',1.6)+E(x+w/2,G.FY+8,8,2.4,'#9aa7b0',0);}
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
  if(f.t==='toilet')return `<g transform="translate(${x} ${by})">`+E(CW/2,-4,15,3,'#000',0,' opacity=".08"')+R(9,-46,22,24,P.white,3)+R(7,-48,26,5,P.white,2.5)+C(CW/2,-38,2,P.grey,1)
    +Pa('M6 -24h28q0 14-9 19h-10q-9-5-9-19z',P.white)+E(CW/2,-24,14,3.4,P.white)+E(CW/2,-24,9,1.8,'#cfe6f1',0)+'</g>';
  if(f.t==='pool'){const y0=G.FY+f.y*FR,h=f.h*FR,id=`dcPool${uid}`,dk=Lt.night;   // the water: waves drift (CSS, not with reduced motion)
    const waves=[.28,.55,.8].map((t,i)=>{let d=`M${x+12+i*6} ${n(y0+h*t)}`;for(let a=x+12+i*6;a<x+w-24;a+=16)d+='q4 -3 8 0t8 0';return L(d,'#ffffff',1.4,` class="dc-wave w${i}" opacity=".7"`);}).join('');
    return `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${dk?'#2c5b86':'#3aa5d4'}"/><stop offset="1" stop-color="${dk?'#4a8cbc':'#93def3'}"/></linearGradient></defs>`
      +R(x-7,y0-7,w+14,h+14,'#f4ead9',10,1.5)+L(Array.from({length:f.w*2},(_,i)=>`M${x+i*20} ${y0-7}v7M${x+i*20} ${y0+h}v7`).join(''),'#e2d4bd',1)
      +Rn(x,y0,w,h,`url(#${id})`,6)+Rn(x,y0,w,7,'#000',4,.13)+(dk?E(x+w/2,y0+h*.6,w*.3,h*.3,'#bff3ff',0,' opacity=".35"'):'')
      +`<g pointer-events="none">${waves}${[[.2,.4],[.62,.25],[.8,.68]].map(([a,b],i)=>C(x+w*a,y0+h*b,1.6,'#ffffff',0).replace('/>',` class="dc-glint g${i}"/>`)).join('')}</g>`
      +L(`M${x+w-20} ${y0-12}v20M${x+w-10} ${y0-12}v20M${x+w-20} ${y0-2}h10M${x+w-20} ${y0+6}h10`,'#aab8c2',2.4);}
  if(f.t==='car')return `<g transform="translate(${x} ${by})">`+E(w/2,-4,w*.46,5,'#000',0,' opacity=".12"')   // 🏰 the showroom's classic car
    +Pa(`M6 -14q0-14 16-16l18-14h${w-80}l22 14q16 2 16 16z`,'#c0392b')+Pa(`M44 -30l12-10h${w-104}l14 10z`,'#cfe6f2',1)
    +C(28,-10,10,'#2f2f35')+C(28,-10,4.5,'#c7d3db',1)+C(w-28,-10,10,'#2f2f35')+C(w-28,-10,4.5,'#c7d3db',1)+R(w-12,-22,8,5,P.butter,1.5,1)+'</g>';
  if(f.t==='gazebo')return `<g transform="translate(${x} ${by})">`+R(4,-(f.h*FR)-60,6,f.h*FR+60,P.woodD,1.5)+R(w-10,-(f.h*FR)-60,6,f.h*FR+60,P.woodD,1.5)   // 🏰 the garden pavilion
    +Pa(`M-8 ${-(f.h*FR)-58}L${w/2} ${-(f.h*FR)-92}L${w+8} ${-(f.h*FR)-58}z`,'#b0503a')+L(`M-4 ${-(f.h*FR)-60}q${w/2+4} 10 ${w+8} 0`,'#8a3a28',2)
    +R(16,-24,w-32,8,P.woodL,3)+L(`M22 -16v14M${w-22} -16v14`,P.woodD,2.4)+'</g>';
  if(f.t==='pillow')return `<g transform="translate(${x} ${by})">`+E(CW/2,-6,17,3,'#000',0,' opacity=".08"')+R(3,-24,CW-6,18,P.white,8)+L('M8 -15q12 4 24 0',P.grey,1.2)+C(CW-10,-18,1.6,P.pinkL,0)+'</g>';
  return '';
}

/** The sunbeam through each window (day only): from the sill down the wall and over the floor. */
function beams(room,G,Lt,uid){
  if(!Lt.beam||room.out)return '';
  const out=[];
  for(const f of room.fix||[]){
    if(f.t!=='window'||f.layer!=='wall')continue;
    const x=PX+f.x*CW+6,w=f.w*CW-12,y=G.WY+(f.y+f.h)*WR-6,reach=Math.min(G.H-8,G.FY+room.frows*FR*.75),drop=reach-y,sk=Lt.skew*drop;
    const id=`dcBeam${uid}${f.x}`;
    out.push(`<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${Lt.beam}" stop-opacity="${Lt.ba}"/><stop offset="1" stop-color="${Lt.beam}" stop-opacity="0"/></linearGradient></defs>`
      +`<path d="M${x} ${y}h${w}l${sk+w*.25} ${drop}h${-w*1.5}z" fill="url(#${id})" pointer-events="none"/>`);
  }
  return out.join('');
}

/** The room's background: ceiling, wall (its skin, or paint and wallpaper as its upgrade level, the flaws of a worn
 * part), floor, fixtures, the sunbeam; outdoors the sky and the city or the garden. parts: journey.reno parts by id
 * (own home) or null. Lt: lightAt(). skin: {w, f} chosen for this room. */
export function roomBack(room,G,parts,Lt,uid='',skin={}){
  if(typeof Lt==='boolean')Lt=lightAt(Lt?1320:720);
  const out=[],wallLv=parts?.wall?.lv??null,floorLv=parts?.floor?.lv??null,sev=p=>!p?0:p.c<45?2:p.c<60?1:0;
  const wallKey=parts?`l${wallLv}`:room.type==='studio'&&room.id==='attic'?'attic':room.type==='studio'?'tro':room.type;
  const floorKey=room.out?room.type:parts?`l${floorLv}`:room.id==='attic'?'attic':room.type==='studio'?'tro':room.type;
  const ws=WALL_SKIN[skin?.w],fs=FLOOR_SKIN[skin?.f];
  if(room.out){
    out.push(sky(0,0,G.W,G.FY,Lt,`dcSkyOut${uid}`));
    if(room.type==='infinity'){   // 🏰 a villa's infinity pool: the sea to the horizon behind the edge
      out.push(Rn(0,G.FY-40,G.W,40,Lt.night?'#1f3b5c':'#4fa3c7')+L(`M0 ${G.FY-40}H${G.W}`,Lt.night?'#2c5b86':'#bfe7f5',1.6)
        +Array.from({length:Math.ceil(G.W/60)},(_,i)=>L(`M${i*60+10} ${G.FY-24}q6-3 12 0`,'#ffffff',1.2,' opacity=".6"')).join(''));
    }else if(room.type==='balcony'||room.type==='terrace'){
      const base=[[0,40],[30,56],[54,32],[84,66],[106,46],[146,74],[174,44],[210,66],[240,48],[272,78],[298,52],[330,70],[360,44]];
      const sky2=[...base,...base.map(([x,h])=>[x+390,h])].filter(([x])=>x<G.W);   // a villa's terrace is wider
      out.push(Pa(`M0 ${G.FY}`+sky2.map(([x,h])=>`V${G.FY-h}H${x+30}`).join('')+`V${G.FY}z`,Lt.night?'#3a4566':'#b9cfdd',0));
      if(Lt.night)out.push([[40,G.FY-30],[96,G.FY-50],[150,G.FY-36],[210,G.FY-44],[300,G.FY-40],[420,G.FY-52]].filter(([a])=>a<G.W).map(([a,b])=>Rn(a,b,4,4,'#ffd76a',1,.9)).join(''));
      if(room.type==='terrace')out.push(Rn(0,G.FY-30,G.W,30,'#cfe6f2',0,.45)+Rn(0,G.FY-31,G.W,3,'#9fb8c6',1)+Array.from({length:Math.ceil(G.W/80)},(_,i)=>Rn(i*80+2,G.FY-30,2,30,'#9fb8c6')).join(''));   // 🏰 glass rail
      else out.push(Rn(0,G.FY-26,G.W,4,'#7a6656',2)+Array.from({length:Math.ceil(G.W/18)},(_,i)=>Rn(i*18+6,G.FY-24,3,24,'#7a6656',1)).join(''));
    }else{
      out.push(E(G.W*.2,G.FY-30,60,34,Lt.night?'#2f5a45':'#8cc47a',0)+E(G.W*.75,G.FY-34,70,40,Lt.night?'#2a5240':'#7cb86c',0)
        +Rn(0,G.FY-22,G.W,22,Lt.night?'#2e5a40':'#6aa851')+Array.from({length:Math.ceil(G.W/22)},(_,i)=>R(i*22+4,G.FY-30,12,30,'#f3e6cf',2,1.1)).join(''));
    }
  }else{
    if(ws){const [defs,fill]=ws(`dcW${uid}`);out.push((defs?`<defs>${defs}</defs>`:'')+Rn(0,0,G.W,G.FY,fill));
      if(skin.w==='op_go'){const t=G.FY-Math.round((G.FY-G.WY)*.45);out.push(Rn(0,t,G.W,G.FY-t,'#d8a874')+Array.from({length:Math.ceil(G.W/22)},(_,i)=>L(`M${i*22+11} ${t+4}V${G.FY}`,'#c48f5c',1.2)).join('')+R(-2,t-3,G.W+4,5,P.woodD,2,1.1));}
    }else if(tiledRoom(room)){const t=Math.round(CEIL+(G.FY-CEIL)*.34),id=`dcTile${uid}`;
      out.push(Rn(0,0,G.W,G.FY,wallLv===0?'#ece4d4':'#f6f0e5')+`<defs>${pat(id,20,20,Rn(0,0,20,1,'#c3dcd9')+Rn(0,0,1,20,'#c3dcd9'),'#e3f2f0')}</defs>`
        +Rn(0,t,G.W,G.FY-t,`url(#${id})`)+R(-2,t-3,G.W+4,5,'#9fcfca',2,1));
    }else{
      out.push(Rn(0,0,G.W,G.FY,WALLS[wallKey]||WALLS.l1));
      if(wallKey==='l2'){out.push(`<defs><pattern id="dcPaper${uid}" width="22" height="22" patternUnits="userSpaceOnUse"><path d="M11 4l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="#c4d8bd"/></pattern></defs>`+Rn(0,0,G.W,G.FY,`url(#dcPaper${uid})`)+Rn(0,G.FY-24,G.W,24,'#c99a6c'));}
      if(wallKey==='attic')out.push(Array.from({length:Math.ceil(G.FY/16)},(_,i)=>L(`M0 ${i*16+8}H${G.W}`,'#d9b98c',1)).join(''));
      if(wallKey==='tro')out.push(Array.from({length:Math.ceil(G.W/30)},(_,i)=>L(`M${i*30+15} 0V${G.FY}`,'#c9e6da',6,' opacity=".6"')).join(''));
      if(wallKey==='bunk')out.push(Array.from({length:Math.ceil(G.W/24)*3},(_,i)=>C((i%Math.ceil(G.W/24))*24+12,(i/Math.ceil(G.W/24)|0)*30+30,2,'#d6c6ee',0)).join(''));
    }
    const w=parts?.wall;
    if(sev(w))out.push(Pa(`M${G.W*.06} ${G.FY*.55}q10-8 22-2l6 10q-12 10-24 2z`,'#c9b691',0,' opacity=".85"')+Pa(`M${G.W*.72} ${G.FY*.32}q12-6 20 2l-4 12q-12 2-18-6z`,'#c9b691',0,' opacity=".85"')
      +(sev(w)>1?L(`M${G.W*.2} ${CEIL+6}l8 18-6 10 10 16M${G.W*.62} ${G.FY*.6}l-6 14 8 8-4 14`,'#7c6a52',1.6,' opacity=".75"'):''));
    out.push(Rn(0,0,G.W,CEIL,'#f6efe2')+L(`M0 ${CEIL}H${G.W}`,'#e3d6c0',1.4));
    const roof=parts?.roof;
    if(sev(roof))out.push(E(G.W*.28,CEIL+4,sev(roof)>1?40:26,sev(roof)>1?10:7,'#b48d55',0,' opacity=".45"')+(sev(roof)>1?C(G.W*.3,CEIL+16,2.6,'#7fb6d9',0):''));
    if(parts?.roof?.lv===2)out.push(Rn(0,CEIL-2,G.W,3,'#ffe8a3',0,.9));
    if(room.type==='bunk'){   // the upper bunk's slats overhead, the posts, a little ladder on the right
      out.push(Rn(0,0,G.W,CEIL+8,P.woodD)+Array.from({length:Math.ceil(G.W/30)},(_,i)=>Rn(i*30+2,2,26,CEIL+2,P.wood,2)).join('')+Rn(0,CEIL+8,G.W,3,'#000',0,.08)
        +Rn(0,0,8,G.H,P.woodD)+Rn(G.W-8,0,8,G.H,P.woodD)+Rn(2,0,2,G.H,P.wood,0,.6)+Rn(G.W-6,0,2,G.H,P.wood,0,.6));
    }
    out.push(Rn(0,G.FY-6,G.W,6,room.type==='bunk'?'#e9ddd2':'#c9a27a'));
  }
  // floor
  if(fs&&!room.out||fs&&room.type==='balcony'){
    const [defs,fill]=fs(`dcF${uid}`);out.push(`<defs>${defs}</defs>`+Rn(0,G.FY,G.W,G.H-G.FY,fill));
    if(room.type==='bunk')out.push(Rn(0,G.FY,G.W,5,'#efe2d6'));
  }else if(tiledRoom(room)){const id=`dcFt${uid}`;
    out.push(`<defs>${pat(id,24,18,Rn(0,0,12,9,'#d3e8ec')+Rn(12,9,12,9,'#d3e8ec')+Rn(0,17,24,1,'#c0d9de'),'#f2f9f9')}</defs>`+Rn(0,G.FY,G.W,G.H-G.FY,`url(#${id})`));
  }else{
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
    }
  }
  const fl=parts?.floor;
  if(sev(fl)&&!room.out)out.push(L(`M${G.W*.18} ${G.FY+20}l14 6-4 10 12 8M${G.W*.74} ${G.FY+50}l10-8 12 4`,'#7c6a52',1.6,' opacity=".75"'));
  out.push(Rn(0,G.FY,G.W,10,'#000',0,.05));
  for(const f of [...room.fix,...(room.more||[])])out.push(fixture(f,room,G,parts,Lt,uid));
  out.push(beams(room,G,Lt,uid));
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
  bang_ghim:'wood',dong_ho_cuc_cu:'wood',quat:'sky',quat_mini:'pink',loa:'sky',may_choi_game:['sky','red'],hop_nhac:'pink',o_meo:'pink',ke_go_treo:'wood',
  bon_tam:'white',buong_tam:'sky',bon_rua:'wood',guong_tam:'wood',ke_khan:'pink',ke_tam:'wood',gio_do_tam:'wood',tham_tam:'sky',
  vit_cao_su:'butter',ghe_tam_nang:'sky',du_che:'red',phao:'red',lo_nuong:'dark',cay_dua:'pot',den_vuon:'dark',
  sap_go:'wood',am_chen:{skyD:'c'},tranh_dong_ho:'wood',dong_ho_qua_lac:'wood',cay_kim_tien:{white:'c',grey:'d'},quat_tran:'wood',dan_bau:'wood',
  binh_sen:{navy:'c'},radio:'red',may_may:'wood',man_tuyn:{white:'l',pinkD:'c',pink:'c'},ban_trang_diem:'pink',gau_bong_lon:'peach',den_sao:'lilac',moc_ao:'sky',
  am_sieu_toc:'mint',lo_vi_song:'white',chan_bat:'wood',tu_lanh_magnet:'mint',gio_trai_cay:'wood',duong_xi:'wood',nen_thom:['pink','lilac'],
  ao_choang:'sky',phao_hong_hac:'pink',bonsai:{navy:'c','#3a4670':'d'},long_chim:'wood',xe_dap:'mint',ban_co_tuong:'wood',
  chum_nuoc:{'#8a5d34':'c','#6b4a2e':'d'},long_den_sao:'red',den_keo_quan:'red',cay_mai:'butter',canh_dao:'pink',cau_doi:'red',mam_ngu_qua:'red',
  sofa_don:'mint',ke_tivi:'wood',ghe_bap_benh:'wood',piano:'dark',binh_gom:{navy:'c'},tranh_son_dau:{gold:'c'},khung_anh_bo:{woodD:'c',white:'l',dark:'d'},
  den_chum:{gold:'c'},tham_tron:'peach',tham_dai:{'#b9805a':'d','#e8c39a':'c'},bang_neon:{'#ff7ab8':'c'},ke_tron:'wood',chuong_gio:{mintL:'l',woodL:'c'},
  may_chieu:{navy:'c','#3a4670':'d'},giuong_don:'butter',tu_ngan_keo:'wood',guong_dung:'wood',den_trang:{'#fff3b0':'l'},goi_tua:'butter',rem_voan:'white',
  tho_bong:'white',ke_giay:'wood',ngua_go:'wood',leu_choi:'lilac',xep_hinh:['red','sky'],xe_do_choi:'red',rubik:['red','sky'],cau_tuyet:'wood',
  dong_ho_bao_thuc:'red',sach_mo:['sky','red'],bep_ga:'dark',treo_noi:'red',thot_dao:'wood',may_xay:'pink',hu_dua:'red',may_ca_phe:'dark',
  dao_bep:['mint','white'],ghe_bar:'red',ro_rau:'wood',lo_nuong_banh:'peach',ke_chen:'wood',ke_my_pham:'white',may_say_toc:'pink',gio_giat:'wood',
  coc_ban_chai:'mint',cay_truc:{white:'c',grey:'d'},tu_thuoc:'white',ghe_trung:'wood',chau_cuc:'pot',bon_hoa:'wood',ho_ca_koi:'grey',ghe_dai:'wood',
  den_bao:'red',nha_cho:'red',binh_tuoi:{leaf:'c',leafD:'d'},
  giuong_king:'butter',ban_go_lim:{'#8a5232':'c','#6b3f22':'d'},ghe_da_bo:{'#b8653d':'c','#9a4f2e':'d'},qua_dia_cau:'sky',ghe_rap_doi:{'#b13a4c':'c','#8e2b3a':'d'},
  may_bong_ngo:'red',loa_cot:{'#2c2a33':'c'},thung_ruou:{'#9a6438':'c'},ban_nem_ruou:{'#8a5232':'c','#6b3f22':'d'},may_chay_bo:{'#3d3a4a':'c'},
  gia_ta:{'#5a566b':'c'},tu_giay:{'#f6f0e5':'c'},dao_trang_suc:{'#ffffff':'l','#f6f0e5':'c'},xe_may_co:{'#5a9a8a':'c'},bien_neon:{'#ff7ab8':'c'},
  lo_suoi_ngoai:{'#7d7a74':'c'},quay_bar_ho:'wood',kinh_thien_van:'navy'};
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

/** The light of the hour over everything (a tint) and the lamps' glow (list of [cx, cy, r]). */
export function roomLight(G,Lt,glows,uid=''){
  let s='';
  if(Lt.ta&&Lt.tint)s+=`<rect width="${G.W}" height="${G.H}" fill="${Lt.tint}" opacity="${Lt.ta}" pointer-events="none"/>`;
  if(Lt.lamps>.05&&glows.length){
    s+=`<defs><radialGradient id="dcGlow${uid}"><stop offset="0" stop-color="#fff1b0" stop-opacity="${(.75*Lt.lamps).toFixed(2)}"/><stop offset=".55" stop-color="#ffe08a" stop-opacity="${(.28*Lt.lamps).toFixed(2)}"/><stop offset="1" stop-color="#ffe08a" stop-opacity="0"/></radialGradient></defs>`
      +`<g pointer-events="none">${glows.map(g=>`<circle cx="${g[0].toFixed(1)}" cy="${g[1].toFixed(1)}" r="${g[2]}" fill="url(#dcGlow${uid})"/>`).join('')}</g>`;
  }
  return s;
}

/** Where a placed piece is drawn: [x, y] of its origin. q: the piece {x, y, on…} in units; host: what it stands on
 * ({it, q} a placed piece, or {fix} a fixture), when q.on. */
export function anchor(it,q,G,host=null){
  if(q.on&&host){
    if(host.fix){const f=host.fix;
      if(f.layer==='wall')return [PX+(f.x*U+q.x)*SX,G.WY+f.y*WR+(f.ledge||0)];
      return [PX+(f.x*U+q.x)*SX,G.FY+(f.y*U+q.y+U)*SF-6-(f.top||f.surface||0)];}
    const h=host.it,hq=host.q;
    if(h.spot==='wall')return [PX+(hq.x+q.x)*SX,G.WY+hq.y*SW+(h.ledge||0)];
    return [PX+(hq.x+q.x)*SX,G.FY+(hq.y+q.y+U)*SF-6-(h.surface||0)];
  }
  if(it.spot==='wall')return [PX+q.x*SX,G.WY+q.y*SW];
  if(it.spot==='top')return [PX+q.x*SX,G.FY+(q.y+U)*SF-6];
  return [PX+q.x*SX,G.FY+(q.y+it.h*U)*SF-3];
}
/** One piece's drawing with its origin at (ax, ay) (f: mirrored; tint: its colour from the palette, if any). */
export function pieceAt(it,ax,ay,f,tint=null,face='front'){
  const a=ART[it.id];if(!a)return '';
  const W=it.w*CW,D=it.spot==='wall'?it.h*WR:it.h*FR,draw=face==='back'&&a.back?a.back:a.d,body=tinted(it.id,draw(W,D),tint);
  return `<g transform="translate(${n(ax)} ${n(ay)})">${f?`<g transform="translate(${W} 0) scale(-1 1)">${body}</g>`:body}</g>`;
}
/** A small soft shadow under a thing standing on a surface (the floor pieces draw their own). */
export const contact=(it,ax,ay)=>E(ax+it.w*CW/2,ay-1.5,it.w*CW*.3,2.6,'#000',0,' opacity=".13"');
/** A glow at night for a lamp with its origin at (ax, ay): [cx, cy, r], or null. */
export function glowAt(it,ax,ay,f){
  const a=ART[it.id];if(!a?.g)return null;
  const W=it.w*CW,D=it.spot==='wall'?it.h*WR:it.h*FR,[gx,gy,r]=a.g(W,D);
  return [ax+(f?W-gx:gx),ay+gy,r];
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

/** The cats who live in the room (drawn facing right, paws at 0,0; about 30 px long). coat: 'mochi' (cream, peach
 * patches) or 'bo' (grey tabby). pose: walk | loaf | sleep | melt. */
const COATS={mochi:{fur:'#fff6e8',patch:'#f6c79a',ear:'#f7b9c7',stripe:''},bo:{fur:'#cfc8c2',patch:'#b3aaa2',ear:'#efb0bd',stripe:'#9c938b'}};
export function catSVG(pose,coat='mochi'){
  const c=COATS[coat]||COATS.mochi,sw=1.3;
  const head=(x,y)=>Pa(`M${x-7} ${y-3}l1-8l5 4zM${x+7} ${y-3}l-1-8l-5 4z`,c.fur,sw)+Pa(`M${x-5.5} ${y-5}l.6-4l2.4 2zM${x+5.5} ${y-5}l-.6-4l-2.4 2z`,c.ear,0)
    +E(x,y,8,6.6,c.fur,sw)+(c.stripe?L(`M${x-2} ${y-6}v3M${x} ${y-6.5}v3M${x+2} ${y-6}v3`,c.stripe,1):E(x+4,y-3,3,2.4,c.patch,0));
  const awake=(x,y)=>eyes(x-3,x+3,y,1.1)+Pa(`M${x-1} ${y+2}h2l-1 1z`,P.pinkD,0)+blush(x-5,y+2.5)+blush(x+5,y+2.5);
  const asleep=(x,y)=>L(`M${x-4.5} ${y}q1.5 1.5 3 0M${x+1.5} ${y}q1.5 1.5 3 0`,OL,1)+blush(x-5,y+2.5)+blush(x+5,y+2.5);
  if(pose==='walk')return E(0,0,13,2.2,'#000',0,' opacity=".12"')
    +`<g class="dc-cat-legs a">${R(-9,-7,3.4,7,c.fur,1.5,1.1)+R(4,-7,3.4,7,c.fur,1.5,1.1)}</g><g class="dc-cat-legs b">${R(-5,-7,3.4,7,c.fur,1.5,1.1)+R(8,-7,3.4,7,c.fur,1.5,1.1)}</g>`
    +Pa('M-11 -12q-9-4-7-14',c.fur==='#fff6e8'?c.fur:c.fur,sw,' class="dc-cat-tail"')+E(0,-11,13,7,c.fur,sw)+(c.stripe?L('M-4 -17v4M0 -18v4M4 -17v4',c.stripe,1.1):E(-3,-14,5,3,c.patch,0))+head(13,-18)+awake(13,-17);
  if(pose==='sleep')return E(0,0,15,2.4,'#000',0,' opacity=".12"')+E(0,-7,14,8,c.fur,sw)+(c.stripe?L('M-6 -13v4M-2 -14v4M2 -14v4',c.stripe,1.1):E(-4,-10,6,3.4,c.patch,0))
    +Pa('M-13 -4q4 4 14 3q8-1 10-4',c.fur,sw)+head(8,-8)+asleep(8,-7)+`<text class="dc-zz" x="12" y="-20" font-size="8" font-weight="800" fill="${OL}">z</text><text class="dc-zz b" x="17" y="-26" font-size="6" font-weight="800" fill="${OL}">z</text>`;
  if(pose==='melt')return E(0,0,18,2.4,'#000',0,' opacity=".12"')+E(-2,-4,17,5,c.fur,sw)+(c.stripe?L('M-8 -8v3M-4 -9v3M0 -9v3',c.stripe,1.1):E(-6,-6,6,2.4,c.patch,0))
    +R(10,-4,8,4,c.fur,2,1.1)+Pa('M-18 -3q-6 0-6-4',c.fur,sw)+head(13,-7)+asleep(13,-6);
  // loaf: sitting tucked in, looking at you
  return E(0,0,12,2.2,'#000',0,' opacity=".12"')+Pa('M9 -3q8 0 8-6',c.fur,sw,' class="dc-cat-tail"')+R(-10,-14,20,14,c.fur,7,sw)+(c.stripe?L('M-5 -13v4M0 -14v4M5 -13v4',c.stripe,1.1):E(4,-11,5,3,c.patch,0))
    +head(0,-17)+awake(0,-16);
}

/** What stands in front of the furniture: the gác lửng's railing, the bunk's front rail (low, so pieces still show). */
export function roomFront(room,G){
  const y=G.H-4;
  if(room.type==='loft')return Rn(0,y-18,G.W,4,P.woodD,2)+Array.from({length:Math.ceil(G.W/26)+1},(_,i)=>Rn(i*26+4,y-16,4,16,P.wood,1)).join('')
    +R(-2,y-22,G.W+4,6,P.wood,3,1.2)+Rn(0,y,G.W,4,P.woodD);
  if(room.type==='bunk')return R(-2,y-14,G.W*.55,8,P.wood,4,1.2)+Rn(G.W*.55-10,y-14,8,18,P.woodD,1)+Rn(0,y-6,G.W,10,P.woodD);
  return '';
}
