/** 🏝️ Thiết kế đảo: the decorations of the private islands (game/island_design_content.py DECOR; their cells and
 * rules: public/js/island-layout.js DECOR_META) as small 3D models, the same parts as the house styles
 * (public/js/house-art.js builder: boxes, roofs, cylinders, balls, flat shapes), so one model serves the new interface
 * (client/isometric/private-island.ts), the old one (v4/island-walk.js), the build mode (v4/island-editor.js) and the
 * cards' previews. Pure: no DOM, no canvas until a preview is asked for.
 *
 * A model is drawn around its footprint's middle in map units (x east, y south; a cell is .024 wide, a w × h thing
 * spans ±w·.012, ±h·.012 before it is turned) with heights z in pixels at the private island's scale. Turned a quarter
 * (r 1..3) by the view: turnedView(). FX tells the renderers what moves: `sway` (trees in the wind), `water` (a pool's
 * surface to shimmer: [x, y, hx, hy]), `fire` / `jet` / `glow` ([x, y, z]: flames, a fountain, a lamp at night), `bob`
 * (floats on the sea), `fall` (a waterfall's foam: [x, y, z]). */
import {modelOf,paintModelVia,isoLight,isoView,shade,HOUSES,paintHouse,previewHouse} from './house-art.js';
import {DECOR_META,turn} from './island-layout.js';

const C=.024;
const WOOD='#9b6a3c',WOOD_D='#6e4a2e',WOOD_L='#c49a5c',STONE='#cfc6b4',STONE_D='#9f9584',ROCK='#8c8a86',ROCK_D='#6d6b68';
const LEAF='#4f9a4a',LEAF_D='#3f8a3e',LEAF_L='#6fbf5a',WATER='#3fb3d9',WATER_D='#2a8fb8',WHITE='#fbf7ee',SAND='#ecd9a6';
const FLOWERS=['#ff6b8a','#ffd25a','#b48de0','#ffffff','#ff8a3d'];

function palmTree(h,x,y,s=1,lean=.006){
  const tx=x+lean*s,tz=52*s;h.part(x,y).beam([x,y,0],[x+lean*s*.5,y,tz*.55],3.6*s,'#8a6a40').beam([x+lean*s*.5,y,tz*.55],[tx,y,tz],3*s,'#9b7a4a');
  for(let i=0;i<8;i++){const a=i/8*Math.PI*2,dx=Math.cos(a)*.016*s,dy=Math.sin(a)*.016*s;
    h.flat([[tx,y,tz+2],[tx+dx,y+dy,tz-9*s],[tx+dx*.75+dy*.25,y+dy*.75-dx*.25,tz-3*s]],i%2?LEAF_D:'#4fa04a');}
  h.ball(tx-.002,y+.001,tz-3,2.4*s,'#7a5a32').ball(tx+.002,y+.002,tz-4,2.4*s,'#7a5a32');
}
function crown(h,x,y,z,r,colors){h.ball(x-.004,y+.002,z,r*.85,colors[0]).ball(x+.004,y-.003,z+r*.25,r*.9,colors[1]).ball(x,y,z+r*.7,r*.7,colors[2]);}
function bigTree(h,x,y,s,colors){h.part(x,y).post(x,y,0,26*s,4.5*s,'#7a5432').beam([x,y,18*s],[x+.008*s,y-.004*s,28*s],2.6*s,'#7a5432');
  crown(h,x,y,34*s,13*s,colors);h.ball(x+.011*s,y-.006*s,30*s,8*s,colors[1]).ball(x-.012*s,y+.004*s,29*s,8*s,colors[0]);}
function pool(h,hx,hy,o={}){
  const rim=o.rim||'#efe8da';h.ground(0,0,hx,hy,rim,1);
  h.part(0,0).prism([[-hx,-hy],[hx,-hy],[hx,hy],[-hx,hy]],0,3,rim,null);
  h.flat([[-hx+.004,-hy+.004,2.6],[hx-.004,-hy+.004,2.6],[hx-.004,hy-.004,2.6],[-hx+.004,hy-.004,2.6]],o.water||WATER);
  h.flat([[-hx+.006,-hy+.006,2.7],[hx*.4,-hy+.006,2.7],[hx*.4,-hy+.009,2.7],[-hx+.006,-hy+.009,2.7]],'#ffffff',.35);
}
function roundPool(h,r,o={}){
  const ring=h.ring(0,0,r,18),inner=h.ring(0,0,r-.004,18);
  h.part(0,0).prism(ring,0,3,o.rim||'#efe8da',o.rim||'#efe8da');h.flat(inner.map(([x,y])=>[x,y,3.2]),o.water||WATER);
}
function fencePiece(h,post,rail,o={}){
  const hx=C*.5;h.part(0,0);
  for(const x of [-hx+.002,0,hx-.002])h.post(x,0,0,o.tall||13,o.w||2,post);
  if(rail)h.beam([-hx,0,(o.tall||13)*.45],[hx,0,(o.tall||13)*.45],1.5,rail).beam([-hx,0,(o.tall||13)*.85],[hx,0,(o.tall||13)*.85],1.5,rail);
}
function tile(h,hx,hy,color,dots){h.ground(0,0,hx,hy,color,1);if(dots){h.part(0,0);for(const [x,y,c] of dots)h.flat([[x-.002,y-.002,.5],[x+.002,y-.002,.5],[x+.002,y+.002,.5],[x-.002,y+.002,.5]],c);}}

/** Each decoration's model (draw(h)) and what moves on it. */
export const DECOR_ART={
  cay_dua:{fx:{sway:1},draw(h){palmTree(h,0,0,1.15,.008);}},
  cay_co:{fx:{sway:1},draw(h){h.part(0,0).post(0,0,0,18,4,'#8a6a40');for(let i=0;i<9;i++){const a=-Math.PI*.95+i/8*Math.PI*.9,dx=Math.cos(a)*.014,dz=Math.sin(-a)*14;
    h.flat([[0,0,18],[dx-.003,.002,18+dz],[dx+.003,-.002,18+dz+3]],i%2?LEAF_D:'#58a85a');}}},
  khom_tre:{fx:{sway:1},draw(h){h.part(0,0);for(const [x,y,t] of [[-.004,.002,48],[.003,-.003,56],[.005,.004,42],[-.002,-.005,52],[0,.006,38]]){
    h.post(x,y,0,t,1.8,'#8fb84a');h.ball(x+.002,y,t,4,LEAF_L).ball(x-.002,y+.001,t-8,3.5,LEAF);}}},
  thong_bien:{fx:{sway:1},draw(h){h.part(0,0).post(0,0,0,14,3,'#6e4a2e').cone(0,0,.011,10,18,'#2f6d3a',8).cone(0,0,.009,22,16,'#357a40',8).cone(0,0,.006,34,14,'#3f8a4a',8);}},
  hoa_giay:{fx:{sway:1},draw(h){h.part(0,0).post(-.004,0,0,30,1.6,WOOD_D).post(.004,0,0,30,1.6,WOOD_D).beam([-.004,0,30],[.004,0,30],1.4,WOOD_D);
    for(let i=0;i<9;i++)h.ball(Math.cos(i*2.1)*.006,Math.sin(i*2.1)*.004,10+i*2.6,4.2,i%3?'#e8458b':'#ff7ab0');h.ball(0,0,8,5,LEAF);}},
  cay_chuoi:{fx:{sway:1},draw(h){h.part(0,0).post(0,0,0,16,4,'#9fb05a');for(let i=0;i<6;i++){const a=i/6*Math.PI*2,dx=Math.cos(a)*.012,dy=Math.sin(a)*.012;
    h.flat([[0,0,18],[dx,dy,24],[dx*1.1+dy*.3,dy*1.1-dx*.3,12]],i%2?'#5fae4a':'#7cc45a');}h.ball(.003,0,13,2.6,'#e8c84a');}},
  xuong_rong:{draw(h){h.ground(0,0,.007,.007,SAND,.8);h.part(0,0).cyl(0,0,.0035,0,30,'#4f9a5a',8).ball(0,0,30,3.6,'#5aa865')
    .cyl(.006,0,.002,12,22,'#4f9a5a',6).beam([.002,0,12],[.006,0,12],3,'#4f9a5a').cyl(-.006,0,.002,8,18,'#4f9a5a',6).beam([-.002,0,8],[-.006,0,8],3,'#4f9a5a').ball(0,0,33,1.6,'#ff6b8a');}},
  bui_hoa:{fx:{sway:1},draw(h){h.part(0,0).ball(0,0,5,7,LEAF).ball(.002,-.002,8,5,LEAF_L);for(let i=0;i<6;i++)h.ball(Math.cos(i)*.005,Math.sin(i*1.7)*.004,7+i%3*2,1.8,FLOWERS[i%5]);}},
  luong_hoa:{fx:{sway:1},draw(h){h.ground(0,0,.023,.01,'#7a5432',1);h.part(0,0).prism([[-.023,-.01],[.023,-.01],[.023,.01],[-.023,.01]],0,2,'#6e4a2e',null);
    for(let i=0;i<10;i++){const x=-.019+i*.0042,y=i%2?.004:-.004,c=['#e5484d','#ffd25a','#ff8ac0','#b48de0','#ff8a3d'][i%5];h.post(x,y,2,9,1,'#4f8a3e');h.ball(x,y,10,2.6,c);}}},
  huong_duong:{fx:{sway:1},draw(h){h.ground(0,0,.022,.008,'#6e4a2e',.8);h.part(0,0);for(let i=0;i<5;i++){const x=-.018+i*.009,t=24+(i%2)*5;
    h.post(x,0,0,t,1.6,'#5f9a3e').ball(x,.001,t,4.2,'#f5c021').ball(x,.002,t,1.8,'#7a4a1a').ball(x+.003,0,t*.5,2.2,LEAF);}}},
  cay_bang:{fx:{sway:1},draw(h){h.ground(0,0,.02,.02,'#5f9a4a',.35);bigTree(h,0,0,1.3,['#3f8a3e','#4f9a4a','#6fae58']);}},
  cay_phuong:{fx:{sway:1},draw(h){h.ground(0,0,.02,.02,'#5f9a4a',.35);bigTree(h,0,0,1.3,['#d9483b','#e8613d','#ff8a5a']);h.ball(.006,.004,44,4,'#4f9a4a');}},
  tung_canh:{draw(h){h.part(0,0).cyl(0,0,.007,0,6,'#2f6d96',10).beam([0,0,6],[-.003,0,14],2.4,'#6e4a2e').beam([-.003,0,14],[.004,-.002,20],2,'#6e4a2e')
    .ball(-.004,.001,15,4.6,'#2f6d3a').ball(.005,-.002,21,4.6,'#357a40').ball(.001,0,25,3.4,'#3f8a4a');}},
  hoa_dao:{fx:{sway:1},draw(h){h.ground(0,0,.02,.02,'#f7c6d9',.4);bigTree(h,0,0,1.2,['#f48fb1','#f7a8c4','#fbd0de']);}},
  vuon_hoa:{fx:{sway:1},draw(h){h.ground(0,0,.035,.023,'#8cc56f',1);h.part(0,0).prism([[-.035,-.023],[.035,-.023],[.035,.023],[-.035,.023]],0,2.5,'#f1ece0',null);
    h.ground(0,0,.03,.018,'#7a5432',1);for(let i=0;i<18;i++){const x=-.026+(i%6)*.0104,y=-.012+Math.floor(i/6)*.012;h.part(x,y).ball(x,y,4,3.4,LEAF).ball(x,y,7,2.4,FLOWERS[(i+Math.floor(i/6))%5]);}}},
  ho_ca:{fx:{water:[0,0,.019,.019]},draw(h){const ring=h.ring(0,0,.022,14);h.part(0,0).prism(ring,0,3,STONE_D,STONE);
    h.flat(h.ring(0,0,.018,14).map(([x,y])=>[x,y,3.2]),'#2f8f8a');for(const [x,y] of [[-.008,.004],[.006,-.006],[.002,.009]])h.flat(h.ring(x,y,.004,8).map(([a,b])=>[a,b,3.4]),'#5aa94e');
    h.ball(-.003,-.004,3.5,1.6,'#ff7a3d').ball(.007,.004,3.5,1.6,'#ffffff').ball(.008,.005,3.6,1,'#e5484d');}},
  ho_nho:{fx:{water:[0,0,.019,.019]},draw(h){pool(h,.023,.023);h.part(.02,0).post(.02,-.006,0,10,1.2,'#c0c6cc').post(.02,.006,0,10,1.2,'#c0c6cc');}},
  be_suc:{fx:{water:[0,0,.017,.017]},draw(h){roundPool(h,.022,{rim:'#d8c7a8',water:'#5fc8e0'});h.part(0,0);for(let i=0;i<7;i++)h.ball(Math.cos(i*2.4)*.01,Math.sin(i*2.4)*.01,4,1.4,'#ffffff',.8);}},
  ho_dai:{fx:{water:[0,0,.032,.019]},draw(h){pool(h,.035,.023);h.part(.034,0).post(.034,-.006,0,12,1.2,'#c0c6cc').post(.034,.006,0,12,1.2,'#c0c6cc');
    h.part(-.03,.026).box(-.03,.028,.004,.002,0,4,'#3d7fb0');}},
  ho_tron:{fx:{water:[0,0,.028,.028]},draw(h){roundPool(h,.034);h.part(.024,-.024).post(.026,-.026,0,22,1.6,'#888').cone(.026,-.026,.016,20,6,'#ff7a59',10);}},
  ho_lon:{fx:{water:[0,0,.043,.031]},draw(h){pool(h,.047,.035);h.part(-.03,.02);for(let i=0;i<3;i++)h.box(-.042+i*.004,.02,.002,.01,0,3-i*.8,'#e6dfcf');
    h.part(.015,-.008).cyl(.015,-.008,.008,0,5,SAND,10);palmTree(h,.015,-.008,.7,.004);}},
  ho_tran:{fx:{water:[0,0,.056,.03]},draw(h){h.ground(0,0,.06,.036,'#c49a5c',1);h.part(0,0).prism([[-.06,-.036],[.06,-.036],[.06,.036],[-.06,.036]],0,3,'#b5844f',null);
    h.flat([[-.056,-.03,3.1],[.056,-.03,3.1],[.056,.036,3.1],[-.056,.036,3.1]],'#2fb0d8');h.flat([[-.056,.033,3.2],[.056,.033,3.2],[.056,.036,3.2],[-.056,.036,3.2]],'#bfefff',.8);
    for(const x of [-.04,-.02])h.part(x,-.033).box(x,-.033,.006,.003,3,6,WHITE);}},
  lua_trai:{fx:{fire:[0,0,6]},draw(h){h.ground(0,0,.01,.01,'#6e5a44',.6);h.part(0,0);for(let i=0;i<7;i++)h.ball(Math.cos(i*.9)*.008,Math.sin(i*.9)*.008,1.5,2.2,ROCK);
    h.beam([-.006,-.004,1],[.006,.004,6],2.2,WOOD_D).beam([.006,-.004,1],[-.006,.004,6],2.2,WOOD_D).flat([[-.003,0,4],[.003,0,4],[0,0,16]],'#ff9a3a').flat([[-.0015,0,4],[.0015,0,4],[0,0,10]],'#ffe08a');}},
  cong_hoa:{draw(h){h.part(0,0).post(-.02,0,0,30,2.4,WHITE).post(.02,0,0,30,2.4,WHITE);for(let i=0;i<=8;i++){const t=i/8,x=-.02+t*.04,z=30+Math.sin(t*Math.PI)*8;h.ball(x,0,z,3,i%2?'#ff8ac0':'#ffffff').ball(x,.002,z-2,2.2,LEAF_L);}}},
  khu_bbq:{fx:{fire:[-.008,-.006,12]},draw(h){h.ground(0,0,.022,.022,'#b9a68a',.8);h.part(-.008,-.006).box(-.008,-.006,.007,.005,0,10,'#3a3a3a','#555').flat([[-.014,-.01,10.5],[-.002,-.01,10.5],[-.002,-.002,10.5],[-.014,-.002,10.5]],'#ff7a3d',.7);
    h.part(.008,.008).box(.008,.008,.01,.006,8,10,WOOD,WOOD_L).post(.0,.004,0,8,1.4,WOOD_D).post(.016,.012,0,8,1.4,WOOD_D).box(.008,.017,.009,.002,0,5,WOOD_D);
    h.part(0,-.02).post(-.02,-.02,0,26,1.2,'#555').post(.02,-.02,0,26,1.2,'#555');for(let i=0;i<=8;i++){const t=i/8;h.ball(-.02+t*.04,-.02,24-Math.sin(t*Math.PI)*5,1.4,['#ffe08a','#ff8aa0','#9fd0e4'][i%3]);}}},
  choi_la:{draw(h){h.ground(0,0,.022,.022,'#c9a77a',.7);h.part(0,0).box(0,0,.019,.019,0,3,WOOD,WOOD_L);for(const [x,y] of [[-.016,-.016],[.016,-.016],[.016,.016],[-.016,.016]])h.post(x,y,3,24,2,WOOD_D);
    h.roof(0,0,.017,.017,24,16,'#c99a48',{type:'pyramid',over:.008}).box(.004,.004,.008,.005,3,7,WOOD_D);}},
  cau_vom:{draw(h){const n=8;h.part(0,0);for(let i=0;i<n;i++){const y0=-.036+i*.009,y1=y0+.009,z0=Math.sin(i/n*Math.PI)*12+2,z1=Math.sin((i+1)/n*Math.PI)*12+2;
    h.face([[-.008,y0,z0],[.008,y0,z0],[.008,y1,z1],[-.008,y1,z1]],i%2?WOOD_L:'#b5844f');}
    for(const x of [-.008,.008]){for(let i=0;i<=n;i++){const y=-.036+i*.009,z=Math.sin(i/n*Math.PI)*12+2;h.post(x,y,z,z+7,1,'#c0392b');}
      for(let i=0;i<n;i++){const ya=-.036+i*.009,za=Math.sin(i/n*Math.PI)*12+9,zb=Math.sin((i+1)/n*Math.PI)*12+9;h.beam([x,ya,za],[x,ya+.009,zb],1.2,'#c0392b');}}}},
  suoi_da:{fx:{water:[0,0,.006,.034]},draw(h){h.ground(0,0,.012,.036,'#a9b89a',.8);h.ground(0,0,.006,.036,'#4fb8d8',1);h.part(0,0);
    for(let i=0;i<10;i++)h.ball((i%2?.008:-.008)+Math.sin(i)*.002,-.032+i*.007,1.8,2.4+i%3*.6,i%2?ROCK:STONE_D);}},
  san_choi:{draw(h){h.ground(0,0,.034,.034,SAND,1);h.part(-.016,-.012).box(-.022,-.016,.006,.006,0,22,'#e5484d').face([[-.016,-.022,22],[-.016,-.01,22],[.006,-.01,2],[.006,-.022,2]],'#ffd25a');
    h.part(.016,.01).post(.008,.002,0,26,1.6,'#3d7fb0').post(.024,.002,0,26,1.6,'#3d7fb0').beam([.008,.002,26],[.024,.002,26],1.8,'#3d7fb0').beam([.014,.002,26],[.014,.006,8],.8,'#555').box(.014,.006,.003,.002,7,8,'#e5484d');
    h.part(-.012,.02).box(-.012,.02,.012,.0015,4,5.5,'#4f9a4a').cyl(-.012,.02,.002,0,4,'#888');}},
  dai_phun:{fx:{jet:[0,0,26],water:[0,0,.017,.017]},draw(h){h.part(0,0).prism(h.ring(0,0,.021,14),0,5,STONE,STONE).flat(h.ring(0,0,.018,14).map(([x,y])=>[x,y,5.2]),'#6ec6e0')
    .cyl(0,0,.004,5,16,STONE_D,8).cyl(0,0,.009,16,18,STONE,10).flat(h.ring(0,0,.0075,10).map(([x,y])=>[x,y,18.2]),'#6ec6e0').ball(0,0,22,2.6,'#e8f7ff',.85);}},
  nha_kinh:{draw(h){h.ground(0,0,.034,.022,'#d9cfb8',1);h.part(0,0).box(0,0,.032,.02,0,24,'#bfe6f0',null);h.roof(0,0,.032,.02,24,12,'#d8f1f7',{type:'gable',axis:'x',over:.001,ends:'#cfeaf2'});
    for(let i=0;i<6;i++)h.ball(-.025+i*.01,.004,8,4.4,i%2?'#ff8ac0':LEAF);for(const x of [-.032,0,.032])h.post(x,.02,0,24,1.2,WHITE);}},
  nha_thuyen:{draw(h){h.ground(0,0,.034,.034,'#7fc6d8',.5);h.part(0,0);for(const [x,y] of [[-.03,-.03],[.03,-.03],[.03,.03],[-.03,.03],[0,-.03],[0,.03]])h.post(x,y,0,26,2.4,WOOD_D);
    h.roof(0,0,.032,.032,26,14,'#8a4d3a',{type:'gable',axis:'y',ends:WOOD}).prism([[-.012,-.02],[.012,-.022],[.016,0],[.012,.022],[-.012,.02]],1,6,WHITE,'#e9eef2').box(0,0,.006,.008,6,11,'#3d6f96');}},
  nha_go:{draw(h){h.ground(0,0,.034,.034,'#b9a68a',.6);h.part(0,0).box(0,-.004,.03,.026,0,4,WOOD_D,WOOD_L).box(0,-.006,.026,.022,4,30,'#a8743a','#b5844f');
    for(let z=8;z<30;z+=5)h.panel(0,-.006,.026,.022,'s',0,1,z,z+.8,'#8a5a2a').panel(0,-.006,.026,.022,'e',0,1,z,z+.8,'#8a5a2a');
    h.windows(0,-.006,.026,.022,4,26,1,2,'#ffe08a',{sides:'se',skip:true,frame:WHITE}).door(0,-.006,.026,.022,'s',.5,.22,16,'#5a3a22',4)
    .roof(0,-.006,.026,.022,30,18,'#6f8f45',{type:'gable',axis:'x',over:.006,ends:'#a8743a'}).part(.018,.024).post(.026,.026,4,22,1.6,WOOD_D).post(-.026,.026,4,22,1.6,WOOD_D);}},
  san_tennis:{draw(h){h.ground(0,0,.06,.048,'#5f9a6a',1);h.ground(0,0,.05,.036,'#3f8a6a',1);h.part(0,0);const L=(a,b,c,d)=>h.flat([[a,b,.6],[c,b,.6],[c,d,.6],[a,d,.6]],'#ffffff');
    L(-.05,-.036,.05,-.034);L(-.05,.034,.05,.036);L(-.05,-.036,-.048,.036);L(.048,-.036,.05,.036);L(-.03,-.036,-.029,.036);L(.029,-.036,.03,.036);L(-.03,-.0005,.03,.0005);
    h.part(0,0).post(0,-.04,0,10,1.6,'#555').post(0,.04,0,10,1.6,'#555').face([[0,-.04,4],[0,.04,4],[0,.04,10],[0,-.04,10]],'#f2f2f2',.55);}},
  bungalow_nuoc:{draw(h){h.part(0,0);for(const [x,y] of [[-.026,-.026],[.026,-.026],[.026,.026],[-.026,.026],[0,.03],[0,-.03]])h.post(x,y,0,12,2.2,WOOD_D);
    h.box(0,0,.032,.032,12,14,'#b5844f',WOOD_L).box(-.004,-.004,.02,.018,14,34,'#d9b77a').windows(-.004,-.004,.02,.018,14,20,1,2,'#9fd3e6',{sides:'se',skip:true})
    .door(-.004,-.004,.02,.018,'s',.5,.2,13,WOOD_D,14).roof(-.004,-.004,.02,.018,34,20,'#c99a48',{type:'hip',over:.008}).post(.028,.03,14,22,1,WOOD_D).post(-.03,.03,14,22,1,WOOD_D);}},
  thac_nuoc:{fx:{water:[0,.016,.04,.012],fall:[0,.004,4]},draw(h){h.ground(0,.012,.045,.022,'#4fb8d8',1);h.part(0,-.018).box(-.026,-.02,.02,.014,0,44,ROCK_D,ROCK).box(.026,-.02,.02,.014,0,38,ROCK_D,ROCK)
    .box(0,-.024,.01,.01,0,50,ROCK,'#9a9894');h.part(0,-.008).face([[-.008,-.012,46],[.008,-.012,46],[.008,.004,2],[-.008,.004,2]],'#cdeffa').face([[-.004,-.012,46],[.004,-.012,46],[.004,.004,2],[-.004,.004,2]],'#ffffff',.8);
    h.part(0,.02);for(let i=0;i<6;i++)h.ball(-.03+i*.012,.03,2,3.2,i%2?ROCK:'#7f9a6a');h.part(-.036,-.026).ball(-.036,-.026,46,6,LEAF).ball(.034,-.028,40,5,LEAF_L);}},
  resort:{fx:{water:[0,.026,.026,.011]},draw(h){h.ground(0,0,.072,.06,'#e9e2d2',1);h.part(0,-.03).box(0,-.03,.03,.018,0,36,WHITE).windows(0,-.03,.03,.018,0,18,2,3,'#9fd3e6',{sides:'se',skip:true})
    .door(0,-.03,.03,.018,'s',.5,.16,14,'#3f6f96').roof(0,-.03,.03,.018,36,20,'#8a4d3a',{type:'hip',over:.008,tips:6,tipColor:'#c9a227'});
    for(const sx of [-1,1]){const x=sx*.052;h.part(x,.006).box(x,.006,.016,.04,0,24,'#f4efe6').windows(x,.006,.016,.04,0,12,2,3,'#9fd3e6',{sides:sx>0?'se':'sw'}).roof(x,.006,.016,.04,24,12,'#a85a3a',{type:'hip',over:.005});}
    h.ground(0,.026,.03,.014,'#efe8da',1).ground(0,.026,.026,.011,WATER,1);palmTree(h,-.03,.05,.8,.004);palmTree(h,.03,.05,.8,-.004);}},
  den_vuon:{fx:{glow:[0,0,16]},draw(h){h.part(0,0).cyl(0,0,.003,0,2,'#3a3a3a',6).post(0,0,2,14,1.4,'#3a3a3a').ball(0,0,16,3,'#ffe7a0').ball(0,0,19,1.4,'#3a3a3a');}},
  chau_hoa:{draw(h){h.part(0,0).cyl(0,0,.005,0,6,'#c96f4a',8).ball(0,0,9,4.4,LEAF).ball(-.002,.001,11,1.8,'#ff6b8a').ball(.002,-.002,11,1.8,'#ffd25a').ball(0,.002,12,1.6,'#b48de0');}},
  o_du:{draw(h){h.ground(.002,.004,.008,.004,'#ff8a8a',.85);h.part(0,0).post(0,0,0,26,1.2,'#e9e2d2');const r=h.ring(0,0,.012,12);
    for(let i=0;i<12;i++){const a=r[i],b=r[(i+1)%12];h.flat([[0,0,30],[a[0],a[1],22],[b[0],b[1],22]],i%2?'#e5484d':'#ffffff');}}},
  ghe_go:{draw(h){h.part(0,0).box(0,0,.02,.005,6,8,WOOD,WOOD_L).box(0,-.005,.02,.0012,8,15,WOOD,WOOD_L).post(-.017,.004,0,6,1.4,WOOD_D).post(.017,.004,0,6,1.4,WOOD_D).post(-.017,-.004,0,6,1.4,WOOD_D).post(.017,-.004,0,6,1.4,WOOD_D);}},
  cot_den:{fx:{glow:[0,0,34]},draw(h){h.part(0,0).cyl(0,0,.0035,0,4,'#2f3438',8).post(0,0,4,32,1.8,'#2f3438').box(0,0,.003,.003,30,37,'#ffe7a0','#2f3438').cone(0,0,.004,37,4,'#2f3438',6);}},
  vong:{draw(h){h.part(0,0).post(-.02,0,0,20,2.4,WOOD_D).post(.02,0,0,20,2.4,WOOD_D);const pts=[];for(let i=0;i<=8;i++){const t=i/8;pts.push([-.019+t*.038,-.003,17-Math.sin(t*Math.PI)*9]);}
    for(let i=8;i>=0;i--){const t=i/8;pts.push([-.019+t*.038,.003,17-Math.sin(t*Math.PI)*9]);}h.flat(pts,'#e86a3d');h.flat(pts.slice(0,9).map(([x,y,z])=>[x,y,z+.6]),'#ffd25a',.6);}},
  ghe_dai:{draw(h){h.part(0,0).box(0,.006,.006,.012,3,5,WHITE,'#3d7fb0').face([[-.006,-.006,5],[.006,-.006,5],[.006,-.016,14],[-.006,-.016,14]],'#3d7fb0').post(-.005,.016,0,3,1.2,'#bbb').post(.005,.016,0,3,1.2,'#bbb').post(-.005,-.004,0,4,1.2,'#bbb').post(.005,-.004,0,4,1.2,'#bbb');}},
  xich_du:{draw(h){h.part(0,0).beam([-.02,-.004,0],[-.018,0,28],1.8,WOOD_D).beam([-.02,.004,0],[-.018,0,28],1.8,WOOD_D).beam([.02,-.004,0],[.018,0,28],1.8,WOOD_D).beam([.02,.004,0],[.018,0,28],1.8,WOOD_D)
    .beam([-.018,0,28],[.018,0,28],2,WOOD_D).beam([-.009,0,28],[-.009,0,9],.8,'#666').beam([.009,0,28],[.009,0,9],.8,'#666').box(0,0,.011,.004,8,9.5,WOOD,WOOD_L).box(0,-.004,.011,.001,9.5,15,WOOD,WOOD_L);}},
  bo_ban_ghe:{draw(h){h.ground(0,0,.02,.02,'#d8cfbf',.6);h.part(0,0).cyl(0,0,.0015,0,9,'#888',6).cyl(0,0,.009,9,10.5,WHITE,12);
    for(const [x,y] of [[-.014,0],[.014,0],[0,-.014],[0,.014]])h.part(x,y).box(x,y,.004,.004,5,6,WOOD,WOOD_L).post(x,y,0,5,1,WOOD_D);
    h.part(0,0).post(0,0,10,30,1,'#888');const r=h.ring(0,0,.016,10);for(let i=0;i<10;i++){const a=r[i],b=r[(i+1)%10];h.flat([[0,0,33],[a[0],a[1],26],[b[0],b[1],26]],i%2?'#2f8f8a':'#f4efe6');}}},
  kinh_thien_van:{draw(h){h.part(0,0).beam([0,0,14],[-.005,-.004,0],1.2,'#555').beam([0,0,14],[.005,-.004,0],1.2,'#555').beam([0,0,14],[0,.006,0],1.2,'#555')
    .beam([-.006,.003,13],[.008,-.005,22],3.4,'#c9a227').ball(.008,-.005,22,1.8,'#333');}},
  tuong_da:{draw(h){h.part(0,0).box(0,0,.007,.007,0,6,STONE_D,STONE).box(0,0,.004,.0035,6,24,'#8a8a82','#9a9a92').box(0,.0006,.0045,.004,24,32,'#8a8a82','#9a9a92').box(0,.002,.0045,.002,27,29,'#6d6b68');}},
  loi_soi:{draw(h){tile(h,.012,.012,'#e8e4da',[[-.005,-.004,'#c9c3b5'],[.004,.003,'#bdb7a8'],[-.002,.006,'#d6d0c2'],[.006,-.006,'#c9c3b5']]);}},
  loi_da:{draw(h){tile(h,.012,.012,'#a9a69e',[[-.005,-.005,'#c4c0b6'],[.005,-.005,'#bab6ab'],[-.005,.005,'#bab6ab'],[.005,.005,'#c4c0b6']]);}},
  loi_gach:{draw(h){tile(h,.012,.012,'#b8543a',[[-.006,-.006,'#c96a4a'],[0,-.003,'#a84a32'],[.006,.003,'#c96a4a'],[-.003,.006,'#a84a32']]);}},
  loi_go:{draw(h){h.ground(0,0,.012,.012,'#b5844f',1);h.part(0,0);for(let i=0;i<4;i++){const x=-.012+i*.006;h.flat([[x,-.012,.5],[x+.0007,-.012,.5],[x+.0007,.012,.5],[x,.012,.5]],'#8b6038');}}},
  rao_go:{draw(h){fencePiece(h,WOOD_D,WOOD);}},
  rao_tre:{draw(h){fencePiece(h,'#a8b84a','#8fa83e',{w:1.6,tall:15});}},
  rao_trang:{draw(h){fencePiece(h,WHITE,WHITE,{w:1.8});}},
  rao_cay:{fx:{sway:1},draw(h){h.part(0,0).box(0,0,.012,.006,0,12,'#3f8a3e','#4f9a4a').ball(-.005,0,12,3,LEAF_L).ball(.005,.001,12.5,3,LEAF);}},
  da_bien:{draw(h){h.part(0,0).ball(-.003,.002,3,5,ROCK).ball(.004,-.002,4,5.6,'#9a9894').ball(0,.004,2,3.4,ROCK_D);}},
  phao_boi:{fx:{bob:1},draw(h){h.part(0,0).prism(h.ring(0,0,.008,12),0,3,'#e5484d','#ffffff').flat(h.ring(0,0,.004,10).map(([x,y])=>[x,y,3.1]),WATER_D).ball(.008,0,4,1.4,'#ffffff');}},
  lau_dai_cat:{draw(h){h.ground(0,0,.011,.011,SAND,1);h.part(0,0).box(0,0,.008,.008,0,6,'#e2c98a','#ecd9a6').cyl(-.006,-.006,.0028,0,12,'#e2c98a',8).cyl(.006,-.006,.0028,0,12,'#e2c98a',8)
    .cyl(.006,.006,.0028,0,10,'#e2c98a',8).cyl(-.006,.006,.0028,0,10,'#e2c98a',8).cyl(0,0,.004,6,15,'#d9bd7a',8).post(0,0,15,22,.6,'#555').flat([[0,0,22],[.004,0,20.5],[0,0,19]],'#e5484d');}},
  da_lon:{draw(h){h.part(0,0).ball(-.008,.006,5,9,ROCK).ball(.008,.004,6,10,'#9a9894').ball(0,-.006,12,9,ROCK_D).ball(.002,.002,18,6,'#a5a39e');}},
  kayak:{fx:{bob:1},draw(h){h.part(0,0).prism([[0,-.022],[.005,-.012],[.005,.012],[0,.022],[-.005,.012],[-.005,-.012]],0,4,'#e5484d','#ff7a59').box(0,0,.003,.005,4,5,'#2f3438').beam([-.012,-.004,5],[.012,.004,6],1,'#555');}},
  cau_tau:{draw(h){h.part(0,0);for(let i=0;i<5;i++)for(const x of [-.009,.009])h.post(x,-.046+i*.023,0,6,2,WOOD_D);
    h.box(0,0,.01,.048,5,7,'#b5844f','#c49a5c');for(let i=1;i<12;i++)h.flat([[-.01,-.048+i*.008,7.1],[.01,-.048+i*.008,7.1],[.01,-.0475+i*.008,7.1],[-.01,-.0475+i*.008,7.1]],'#8b6038');
    h.post(.009,.046,7,16,1.4,WOOD_D).post(-.009,.046,7,16,1.4,WOOD_D);}},
  du_thuyen:{fx:{bob:1},draw(h){h.part(0,0).prism([[0,-.06],[.012,-.04],[.016,.02],[.012,.056],[-.012,.056],[-.016,.02],[-.012,-.04]],0,10,WHITE,'#e9eef2')
    .box(0,.016,.01,.026,10,22,'#f4f6f8','#dfe6ec').panel(0,.016,.01,.026,'e',.1,.9,13,18,'#2f4f6a').panel(0,.016,.01,.026,'w',.1,.9,13,18,'#2f4f6a').box(0,.024,.006,.012,22,30,'#f4f6f8','#cfd8e0')
    .post(0,.0,22,40,1,'#ccc').beam([-.016,-.02,8],[.016,-.02,8],1,'#24507a');}},
  bong_chuyen:{draw(h){h.ground(0,0,.048,.036,SAND,1);h.part(0,0).post(0,-.03,0,22,1.6,'#555').post(0,.03,0,22,1.6,'#555').face([[0,-.03,12],[0,.03,12],[0,.03,22],[0,-.03,22]],'#f2f2f2',.6)
    .ball(.02,.01,18,2.6,'#ffd25a').ball(.0205,.0105,18.4,1.2,'#3d7fb0');}},
};
export const DECOR_ART_IDS=Object.keys(DECOR_ART);
const cache=new Map();
/** The model of a decoration ({parts, ground, top}, cached); null: a kind this build does not know. */
export function decorModel(kind){
  const d=DECOR_ART[kind];if(!d)return null;let m=cache.get(kind);if(m)return m;
  m=modelOf(h=>d.draw(h));cache.set(kind,m);return m;
}
export const decorFx=kind=>DECOR_ART[kind]?.fx||{};
export const decorTall=kind=>decorModel(kind)?.top||20;
/** A view turned a quarter `r` times (clockwise seen from above): the model's local points, its faces' light and
 * its parts' order go through the turn, so one model stands any way round. */
export function turnedView(view,r){
  r=(r|0)&3;if(!r)return view;
  const light=view.light||isoLight;
  return {...view,P:(x,y,z)=>{const [a,b]=turn(x,y,r);return view.P(a,b,z);},depth:(x,y)=>{const [a,b]=turn(x,y,r);return view.depth(a,b);},
    light:(nx,ny,nz)=>{const [a,b]=turn(nx,ny,r);return light(a,b,nz);}};
}
/** Paint a decoration turned r through `view` (house-art.js's adapter, local points around its middle). {top}; null:
 * unknown. `only`: 'ground' | 'parts' as paintHouse(). */
export function paintDecorItem(kind,r,view,{only=''}={}){
  const m=decorModel(kind);if(!m)return null;paintModelVia(m,turnedView(view,r),only);return {top:m.top};
}
/** Draw a decoration into a <canvas> (the build mode's cards): fitted, centred on a small tile of its footprint. */
export function previewDecorItem(canvas,kind,r=0){
  const ctx=canvas?.getContext?.('2d'),m=decorModel(kind),meta=DECOR_META[kind];if(!ctx||!m||!meta)return false;
  const dpr=Math.min(2,globalThis.devicePixelRatio||1),w=canvas.clientWidth||canvas.width||72,hgt=canvas.clientHeight||canvas.height||64;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(hgt*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,hgt);
  const [fw,fh]=r&1?[meta[1],meta[0]]:[meta[0],meta[1]],hx=fw*C/2,hy=fh*C/2,wide=(hx+hy)*560,deep=(hx+hy)*280;
  const k=Math.min((w-6)/(2*wide),(hgt-8)/(2*deep+m.top)),cx=w/2,cy=hgt-4-deep*k;
  const where=meta[2],ground=where==='sea'?'#5fb6cc':where==='pier'?'#9fd3e0':'#8cc56f';
  ctx.fillStyle=ground;ctx.beginPath();[[-hx,-hy],[hx,-hy],[hx,hy],[-hx,hy]].forEach(([x,y],i)=>{const px=cx+(x-y)*560*k,py=cy+(x+y)*280*k;i?ctx.lineTo(px,py):ctx.moveTo(px,py);});ctx.closePath();ctx.fill();
  paintDecorItem(kind,r,isoView(ctx,cx,cy,k));
  return true;
}

/* ---- 🏗️ the first eight buildings (game/island_build_content.py BUILDINGS) as models, for the build mode and its
 * cards (the islands themselves draw them with their own painters: client/isometric/island-builds.ts,
 * v4/island-build-art.js). A plot is .072 wide: ±.036 around its middle. */
const LEGACY={
  nha_san(h){h.ground(0,0,.034,.034,'#c9a77a',.5);h.part(0,0);for(const [x,y] of [[-.02,-.017],[.02,-.017],[.02,.017],[-.02,.017]])h.post(x,y,0,14,2.4,WOOD_D);
    h.box(0,.004,.028,.028,14,17,WOOD,WOOD_L).box(0,0,.02,.017,17,38,'#d9b77a').windows(0,0,.02,.017,17,21,1,1,'#9fd3e6',{sides:'se'}).roof(0,0,.02,.017,38,18,'#a8743a',{type:'hip',over:.007});},
  biet_thu(h){h.ground(0,0,.034,.034,'#e9e2d2',.9);h.part(0,0).box(0,0,.028,.024,0,52,WHITE).windows(0,0,.028,.024,0,26,2,2,'#9fd3e6',{sides:'se',skip:true})
    .door(0,0,.028,.024,'s',.5,.16,18,'#3f6f96').roof(0,0,.028,.024,52,20,'#3d7fb0',{type:'hip',over:.004});},
  lau_dai(h){h.ground(0,0,.035,.035,'#b9b3a8',.9);const S='#b7b0a6';h.part(0,0).box(0,-.004,.022,.02,0,56,S).windows(0,-.004,.022,.02,0,28,2,2,'#5c5650',{sides:'se'});
    for(const [x,y,t] of [[.026,.022,78],[-.024,.024,70],[.026,-.026,88]])h.part(x,y).cyl(x,y,.009,0,t,S,10).cone(x,y,.011,t,22,'#b5453a',10);},
  cong_vien(h){h.ground(0,0,.034,.034,'#8fd06a',1);h.ground(0,0,.004,.034,'#e9d7a6',1);h.ground(0,0,.034,.004,'#e9d7a6',1);h.tree(-.02,-.02,1).tree(.02,-.02,.85,'#5aa94e');
    h.part(.016,.018).box(.016,.018,.01,.003,4,6,WOOD,WOOD_L);},
  ho_boi(h){h.ground(0,0,.034,.034,'#f1ebe0',1);h.ground(0,0,.028,.028,WATER,1);h.part(.026,-.026).post(.026,-.026,0,24,1.6,'#888').cone(.026,-.026,.014,22,6,'#ff7a59',10);},
  golf(h){h.ground(0,0,.034,.034,'#7ccf5a',1);h.ground(-.016,-.016,.012,.008,'#f0dca0',1);h.part(.012,-.008).post(.012,-.008,0,30,1.4,'#f2f2f2').flat([[.012,-.008,30],[.026,-.008,27],[.012,-.008,24]],'#d9483b');},
  cam_trai(h){h.ground(0,0,.034,.034,'#b6c97a',.7);for(const [x,y,s,c] of [[-.012,-.012,.012,'#e8833a'],[.016,-.016,.01,'#4f9a6a']])h.part(x,y).roof(x,y,s,s*.8,0,24*s/.012,c,{type:'gable',axis:'y',over:0});
    h.part(.014,.014).beam([.008,.014,1],[.02,.014,1],2,WOOD_D).flat([[.011,.014,2],[.017,.014,2],[.014,.014,14]],'#ff9a3a');},
  ben_thuyen(h){h.ground(0,0,.034,.034,'#d8c39a',.8);h.part(0,.03).box(0,.03,.008,.02,3,5,'#b5844f',WOOD_L);h.part(0,0).post(0,0,0,26,3,WOOD_D);
    h.part(.02,.03).prism([[.012,.02],[.028,.02],[.032,.03],[.028,.04],[.012,.04]],0,6,WHITE,'#e9eef2');},
};
const legacyCache=new Map();
/** A building's model for the build mode: a house style (house-art.js, in its colour) or one of the first eight. */
export function paintBuildingModel(kind,level,look,r,view){
  if(HOUSES[kind])return paintHouse(kind,level,look,turnedView(view,r));
  const d=LEGACY[kind];if(!d)return null;let m=legacyCache.get(kind);if(!m){m=modelOf(h=>d(h));legacyCache.set(kind,m);}
  paintModelVia(m,turnedView(view,r));return {top:m.top};
}
/** A building's card picture: previewHouse for a style, else its model on a tile. */
export function previewBuilding(canvas,kind,look=0){
  if(HOUSES[kind])return previewHouse(canvas,kind,1,look);
  const ctx=canvas?.getContext?.('2d'),d=LEGACY[kind];if(!ctx||!d)return false;
  const dpr=Math.min(2,globalThis.devicePixelRatio||1),w=canvas.clientWidth||canvas.width||72,hgt=canvas.clientHeight||canvas.height||64;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(hgt*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,hgt);
  const t=.036,k=Math.min((w-6)/(4*t*560),(hgt-8)/(4*t*280+90)),cx=w/2,cy=hgt-4-2*t*280*k;
  ctx.fillStyle='#8cc56f';ctx.beginPath();[[-t,-t],[t,-t],[t,t],[-t,t]].forEach(([x,y],i)=>{const px=cx+(x-y)*560*k,py=cy+(x+y)*280*k;i?ctx.lineTo(px,py):ctx.moveTo(px,py);});ctx.closePath();ctx.fill();
  paintBuildingModel(kind,1,0,0,isoView(ctx,cx,cy,k));return true;
}
export {shade};
