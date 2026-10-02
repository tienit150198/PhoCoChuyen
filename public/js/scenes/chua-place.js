/** 🛕 Vào chùa (v4/chua-visit.js): chùa Gió Lành as a place to walk around. Three areas:
 *   san   the yard: the three-entrance gate, the bell tower, the main hall's doors, the big incense burner, the
 *         lotus pond, the wish fence, the broom rack, the old bodhi tree, a side gate to the dining hall;
 *   dien  the main hall (chánh điện): the Buddha on his lotus seat, the altar, the wooden fish (mõ), the bowl bell
 *         (chuông gia trì), the prayer mats, thầy Huệ Minh, the timetable on the wall;
 *   trai  the dining hall: the long table, bà Nhạn's stove; on rằm and mùng 1 the table is full.
 * Pure (no DOM, no server): plans in scene pixels (landscape 1200×790 / portrait 700×890, the frames of the
 * workplace scenes), a small grid path finder and the painters. Nothing moves when `reduced` is set.
 *
 * plan(area, port, day) → {floor:[x0,y0,x1,y1], blocks:[[x0,y0,x1,y1]…], spots:[{id, kind, hit:[x,y], r, stand:[x,y],
 *   icon, label, act?, to?, who?, look?}], entry:{from: [x,y]}, people:[{who, x, y, sit?}]}
 *   kind: 'act' (a chùa act of game/chua.py, `act`), 'door' (to the area `to`), 'npc' (`who`), 'look' (a line).
 * day: {lunar, feast} from the server (chua.public()); who is in the yard depends on it. */
import {R,E,L,T,P,fit} from './kit.js';
import {geo,shell,doorway,windowPane,plate,sitter,hash} from './interior.js';
import {F,RED,RED_D,GOLD,sky,hall,gate,areca,bellTower,yard,brooms} from './pagoda.js';

export const AREAS=[
  {id:'san',icon:'🌿',name:'Sân chùa'},
  {id:'dien',icon:'🪷',name:'Chánh điện'},
  {id:'trai',icon:'🍚',name:'Nhà ăn'},
];
/** The drawn part of the scene per orientation (what the stage fits). */
export const VIEW={land:[50,100,1150,760],port:[14,104,686,868]};
const PAD={x:20,y:7};       // the walker's half-size around a footprint
const CELL=12;

/* ------------------------------------------------------------ who is here today */
/** The people in each area today: thầy and bà Nhạn always; in the yard bé Na on even lunar days, chị Quyên on
 * odd ones, ông Bảy Đò on rằm and mùng 1. */
function peopleOf(area,port,day){
  const lunar=day?.lunar|0,feast=!!day?.feast,out=[];
  if(area==='san'){
    if(port){if(lunar%2===0)out.push({who:'na',x:300,y:790});else out.push({who:'quyen',x:430,y:552,sit:true});
      if(feast)out.push({who:'bay',x:470,y:700});}
    else{if(lunar%2===0)out.push({who:'na',x:480,y:670});else out.push({who:'quyen',x:700,y:518,sit:true});
      if(feast)out.push({who:'bay',x:760,y:640});}
  }
  if(area==='dien'){const g=geo(port);out.push({who:'thay',x:g.X(.14),y:g.Y(.3)});}
  if(area==='trai'){const g=geo(port);out.push({who:'nhan',x:g.X(.82),y:g.Y(.36)});}
  return out;
}
export const PEOPLE={
  thay:{icon:'🙏',name:'Thầy Huệ Minh',role:'Trụ trì chùa Gió Lành'},
  nhan:{icon:'🍲',name:'Bà Nhạn',role:'Trưởng ban trai soạn'},
  na:{icon:'🐟',name:'Bé Na',role:'Theo bà đi chùa'},
  quyen:{icon:'🍃',name:'Chị Quyên',role:'Hay ngồi ở hiên chùa'},
  bay:{icon:'🦯',name:'Ông Bảy Đò',role:'Rằm nào cũng lên chùa'},
};

/* ------------------------------------------------------------ plans */
const S=(id,kind,hit,r,stand,more={})=>({id,kind,hit,r,stand,...more});
function yardPlan(port){
  if(port)return {floor:[44,535,656,838],
    blocks:[[140,548,200,564],[305,622,395,648],[80,742,262,780],[500,560,650,575],[545,748,575,764],[400,546,460,562]],
    spots:[S('go:dien','door',[315,470],70,[315,562],{to:'dien'}),S('go:trai','door',[56,672],52,[78,690],{to:'trai'}),
      S('chuong','act',[75,400],62,[72,560],{act:'chuong'}),S('quet','act',[170,528],44,[170,592],{act:'quet'}),
      S('huong','act',[350,604],60,[350,682],{act:'huong'}),S('ngoi','act',[170,752],70,[170,722],{act:'ngoi'}),
      S('nguyen','act',[575,546],62,[575,604],{act:'nguyen'}),S('look:bode','look',[560,680],56,[510,808],{look:'bode'})],
    entry:{gate:[585,600],dien:[315,570],trai:[80,690]}};
  return {floor:[92,492,1108,725],
    blocks:[[205,505,275,522],[548,555,652,580],[215,640,445,682],[860,512,1010,528],[1020,640,1062,656],[655,510,745,526]],
    spots:[S('go:dien','door',[490,430],72,[490,506],{to:'dien'}),S('go:trai','door',[112,640],56,[122,690],{to:'trai'}),
      S('chuong','act',[138,350],70,[140,510],{act:'chuong'}),S('quet','act',[240,494],48,[240,548],{act:'quet'}),
      S('huong','act',[600,532],60,[600,606],{act:'huong'}),S('ngoi','act',[330,654],80,[330,618],{act:'ngoi'}),
      S('nguyen','act',[935,500],70,[935,556],{act:'nguyen'}),S('look:bode','look',[1040,560],60,[985,692],{look:'bode'})],
    entry:{gate:[925,620],dien:[490,516],trai:[130,690]}};
}
function hallPlan(port){
  const g=geo(port),X=g.X,Y=g.Y,H=g.H,b=(u0,v0,u1,v1)=>[X(u0),Y(v0),X(u1),Y(v1)];
  return {floor:[X(.03),Y(.1),X(.97),Y(.93)],
    blocks:[b(.36,.0,.64,.2),b(.2,.18,.27,.27),b(.73,.18,.8,.27)],
    spots:[S('go:san','door',[X(.9),g.base-70],62,[X(.9),Y(.22)],{to:'san'}),
      S('khan','act',[X(.5),Y(.52)],port?90:84,[X(.5),Y(.5)],{act:'khan'}),
      S('tung','act',[X(.235),Y(.16)],port?54:50,[X(.235),Y(.44)],{act:'tung'}),
      S('look:giatri','look',[X(.765),Y(.16)],port?54:50,[X(.765),Y(.44)],{look:'giatri'}),
      S('look:ban','look',[X(.5),g.base-40],port?70:80,[X(.5),Y(.3)],{look:'ban'}),
      S('look:thoikhoa','look',[X(.08),H(.5)],56,[X(.07),Y(.3)],{look:'thoikhoa'})],
    entry:{san:[X(.9),Y(.3)]}};
}
function diningPlan(port){
  const g=geo(port),X=g.X,Y=g.Y,H=g.H,b=(u0,v0,u1,v1)=>[X(u0),Y(v0),X(u1),Y(v1)];
  return {floor:[X(.03),Y(.1),X(.97),Y(.93)],
    blocks:[b(.27,.3,.71,.6),b(.74,.0,.94,.18)],
    spots:[S('go:san','door',[X(.1),g.base-70],62,[X(.1),Y(.22)],{to:'san'}),
      S('com','act',[X(.5),Y(.45)],port?90:100,[X(.5),Y(.72)],{act:'com'}),
      S('look:thucdon','look',[X(.32),H(.45)],56,[X(.22),Y(.7)],{look:'thucdon'})],
    entry:{san:[X(.1),Y(.3)]}};
}
const CACHE=new Map();
/** The plan of an area for this orientation and day (people included as spots and footprints). */
export function plan(area,port,day){
  const key=[area,port,day?.lunar|0,!!day?.feast].join('|');
  if(CACHE.has(key))return CACHE.get(key);
  const base=area==='dien'?hallPlan(port):area==='trai'?diningPlan(port):yardPlan(port);
  const people=peopleOf(area,port,day);
  const pl={...base,blocks:[...base.blocks],spots:[...base.spots],people};
  for(const p of people){
    pl.blocks.push(p.sit?[p.x-34,p.y-8,p.x+34,p.y+8]:[p.x-24,p.y-7,p.x+24,p.y+6]);
    const front=Math.min(pl.floor[3]-6,p.y+(port?52:44));
    pl.spots.push(S('npc:'+p.who,'npc',[p.x,p.y-(port?70:60)],port?52:46,[p.x,front],{who:p.who}));
  }
  if(CACHE.size>40)CACHE.clear();
  CACHE.set(key,pl);return pl;
}

/* ------------------------------------------------------------ walking */
export function blocked(pl,x,y){
  const f=pl.floor,e=1e-6;if(x<f[0]-e||x>f[2]+e||y<f[1]-e||y>f[3]+e)return true;
  for(const b of pl.blocks)if(x>b[0]-PAD.x&&x<b[2]+PAD.x&&y>b[1]-PAD.y&&y<b[3]+PAD.y)return true;
  return false;
}
/** Does segment AB pass through the open rectangle (x0,y0)-(x1,y1)? (the same test as boba-world.js) */
function segHitsRect(A,B,x0,y0,x1,y1){let t0=0,t1=1;const dx=B[0]-A[0],dy=B[1]-A[1];
  for(const [p,q] of [[-dx,A[0]-x0],[dx,x1-A[0]],[-dy,A[1]-y0],[dy,y1-A[1]]]){if(p===0){if(q<=0)return false;continue;}const t=q/p;if(p<0){if(t>t0)t0=t;}else if(t<t1)t1=t;if(t0>=t1)return false;}
  return t0<t1;}
/** Is the straight walk from a to b on free floor all the way? (exact: the floor is one rectangle) */
export function lineFree(pl,a,b){
  const f=pl.floor,e=1e-6,inside=p=>p[0]>=f[0]-e&&p[0]<=f[2]+e&&p[1]>=f[1]-e&&p[1]<=f[3]+e;
  if(!inside(a)||!inside(b))return false;
  for(const r of pl.blocks)if(segHitsRect(a,b,r[0]-PAD.x,r[1]-PAD.y,r[2]+PAD.x,r[3]+PAD.y))return false;
  return true;
}
function grid(pl){
  if(pl._grid)return pl._grid;
  const [x0,y0,x1,y1]=pl.floor,nx=Math.floor((x1-x0)/CELL)+1,ny=Math.floor((y1-y0)/CELL)+1,free=new Uint8Array(nx*ny);
  for(let j=0;j<ny;j++)for(let i=0;i<nx;i++)free[j*nx+i]=blocked(pl,x0+i*CELL,y0+j*CELL)?0:1;
  return (pl._grid={x0,y0,nx,ny,free,at:(i,j)=>[x0+i*CELL,y0+j*CELL]});
}
/** The nearest free floor point to p (p itself when it is free). */
export function nearestFree(pl,p){
  if(!blocked(pl,p[0],p[1]))return p;
  const G=grid(pl);let best=null,bd=Infinity;
  for(let j=0;j<G.ny;j++)for(let i=0;i<G.nx;i++)if(G.free[j*G.nx+i]){const q=G.at(i,j),d=(q[0]-p[0])**2+(q[1]-p[1])**2;if(d<bd){bd=d;best=q;}}
  return best;
}
/** A path [from, …, to] over free floor (straight when clear, else A* on the grid, string-pulled); null if none. */
export function route(pl,from,to){
  to=nearestFree(pl,to);if(!to)return null;
  if(blocked(pl,from[0],from[1]))from=nearestFree(pl,from);
  if(lineFree(pl,from,to))return [from,to];
  const G=grid(pl),cell=p=>[Math.max(0,Math.min(G.nx-1,Math.round((p[0]-G.x0)/CELL))),Math.max(0,Math.min(G.ny-1,Math.round((p[1]-G.y0)/CELL)))];
  const near=p=>{const [i,j]=cell(p);if(G.free[j*G.nx+i])return j*G.nx+i;const q=nearestFree(pl,G.at(i,j));const [a,b]=cell(q);return b*G.nx+a;};
  const s=near(from),g=near(to),N=G.nx*G.ny,dist=new Float64Array(N).fill(Infinity),prev=new Int32Array(N).fill(-1),done=new Uint8Array(N);
  const h=k=>Math.hypot(k%G.nx-g%G.nx,Math.floor(k/G.nx)-Math.floor(g/G.nx));
  const open=[s];dist[s]=0;
  while(open.length){
    let bi=0;for(let i=1;i<open.length;i++)if(dist[open[i]]+h(open[i])<dist[open[bi]]+h(open[bi]))bi=i;
    const u=open.splice(bi,1)[0];if(done[u])continue;done[u]=1;if(u===g)break;
    const ui=u%G.nx,uj=Math.floor(u/G.nx);
    for(const [di,dj] of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]]){
      const i=ui+di,j=uj+dj;if(i<0||j<0||i>=G.nx||j>=G.ny)continue;const v=j*G.nx+i;if(!G.free[v]||done[v])continue;
      if(di&&dj&&(!G.free[uj*G.nx+i]||!G.free[j*G.nx+ui]))continue;   // no corner cutting
      const d=dist[u]+(di&&dj?1.414:1);if(d<dist[v]){dist[v]=d;prev[v]=u;open.push(v);}
    }
  }
  if(dist[g]===Infinity)return null;
  const cells=[];for(let k=g;k>=0;k=prev[k]){cells.unshift(G.at(k%G.nx,Math.floor(k/G.nx)));if(k===s)break;}
  const pts=[from,...cells,to],out=[pts[0]];
  for(let i=1;i<pts.length;){let j=pts.length-1;while(j>i&&!lineFree(pl,out[out.length-1],pts[j]))j--;out.push(pts[j]);i=j+1;}
  return out;
}

/* ------------------------------------------------------------ people */
const SKIN='#efcfb0',SKIN_OLD='#e6c2a0';
/** A person standing (or sitting) at (x,y) = feet, seen from the front, s = scale. Respectful, simple. */
export function person(c,x,y,s,who,{t=0,pose=''}={}){
  c.save();c.translate(x,y);c.scale(s,s);
  const sit=pose==='sit';if(sit)c.translate(0,-18);
  E(c,0,sit?18:0,26,7,'#5a3f2c22');
  if(who==='thay'){
    // nâu robe to the ground, a saffron sash over the left shoulder, prayer beads; shaved head
    P(c,[[-24,-58],[24,-58],[30,0],[-30,0]],'#8a5a3a');P(c,[[-24,-58],[-6,-58],[22,-4],[8,0]],'#c98a3a');
    E(c,-26,-36,8,15,'#8a5a3a');E(c,26,-36,8,15,'#8a5a3a');E(c,0,-30,6,5,SKIN_OLD);
    for(let i=0;i<7;i++)E(c,-8+i*2.6,-22+Math.abs(i-3)*1.6,1.8,1.8,'#5a3a24');
    E(c,0,-80,22,23,SKIN_OLD);E(c,-22,-78,4,7,SKIN_OLD);E(c,22,-78,4,7,SKIN_OLD);
    L(c,-12,-82,-5,-81,'#6b4a36',1.6);L(c,5,-81,12,-82,'#6b4a36',1.6);L(c,-4,-70,4,-70,'#a8705a',1.4);
    L(c,-10,-92,10,-92,'#d9b08f',1);L(c,-14,-88,-8,-88,'#d9b08f',1);
  }else if(who==='na'){
    c.scale(.78,.78);R(c,-14,-26,10,26,'#5b6f8a',4);R(c,4,-26,10,26,'#5b6f8a',4);R(c,-18,-58,36,36,'#f0a6b8',12);
    E(c,0,-82,20,20,'#3b2f2a');E(c,0,-78,16,16,SKIN);R(c,-20,-96,40,14,'#3b2f2a',7);E(c,-6,-78,1.8,2.2,'#4a3a33');E(c,6,-78,1.8,2.2,'#4a3a33');E(c,-10,-72,3,1.6,'#f0a3a0aa');E(c,10,-72,3,1.6,'#f0a3a0aa');
  }else{
    // a lay Buddhist in the grey-blue áo tràng (bà Nhạn, chị Quyên) or an old man with a cane (ông Bảy)
    const bay=who==='bay',robe=bay?'#8d7258':'#7f97ad',hair=who==='nhan'?'#b9b1a8':bay?'#e8e4dc':'#3b2f2a';
    if(!sit)P(c,[[-20,-56],[20,-56],[24,0],[-24,0]],robe);else{R(c,-24,-4,48,14,robe,6);}
    R(c,-21,-60,42,sit?60:40,robe,12);E(c,-24,-36,7,13,robe);E(c,24,-36,7,13,robe);
    E(c,0,-80,19,20,hair);E(c,0,-76,16,17,bay?SKIN_OLD:SKIN);
    if(who==='nhan')E(c,0,-98,9,7,hair);else if(!bay)R(c,-17,-94,34,10,hair,5);
    E(c,-6,-77,1.8,2.2,'#4a3a33');E(c,6,-77,1.8,2.2,'#4a3a33');L(c,-3,-68,3,-68,'#a8705a',1.3);
    if(bay){L(c,28,-40,34,0,'#6b4f2a',3.5);E(c,24,-40,5,5,SKIN_OLD);}
  }
  c.restore();
}
/** The Buddha seated on a lotus, (cx, foot) = the base's bottom middle, h = height. Gold, still, eyes lowered. */
export function buddha(c,cx,foot,h){
  const G1='#d9a441',G2='#c38f33',G3='#e8bb5c',k=h/100;
  E(c,cx,foot-h*.68,h*.36,h*.36,'#f7e7b4');E(c,cx,foot-h*.68,h*.31,h*.31,'#fbf0cc');
  for(let i=-3;i<=3;i++)E(c,cx+i*h*.075,foot-h*.07,h*.07,h*.06,i%2?'#eab0a6':'#f2c4b8');
  R(c,cx-h*.3,foot-h*.13,h*.6,h*.06,G2,h*.03);
  P(c,[[cx-h*.31,foot-h*.12],[cx+h*.31,foot-h*.12],[cx+h*.22,foot-h*.3],[cx-h*.22,foot-h*.3]],G1);
  R(c,cx-h*.16,foot-h*.6,h*.32,h*.34,G1,h*.1);
  L(c,cx-h*.12,foot-h*.58,cx+h*.1,foot-h*.32,G2,2.4*k);           // the robe's fold over the shoulder
  E(c,cx,foot-h*.26,h*.11,h*.045,G3);                                 // hands resting in the lap
  E(c,cx-h*.105,foot-h*.71,h*.022,h*.07,G2);E(c,cx+h*.105,foot-h*.71,h*.022,h*.07,G2);
  E(c,cx,foot-h*.72,h*.1,h*.115,G3);
  E(c,cx,foot-h*.8,h*.1,h*.055,G2);E(c,cx,foot-h*.86,h*.045,h*.04,G2);
  L(c,cx-h*.055,foot-h*.715,cx-h*.02,foot-h*.71,'#8a6a2a',1.4*k);L(c,cx+h*.02,foot-h*.71,cx+h*.055,foot-h*.715,'#8a6a2a',1.4*k);
  L(c,cx-h*.015,foot-h*.665,cx+h*.015,foot-h*.665,'#a5793a',1.2*k);
}

/* ------------------------------------------------------------ the yard */
function smoke(c,x,y,n,{t,reduced,strong}){
  for(let i=0;i<n;i++){const ph=reduced?i*.7:t*.5+i*1.3,dx=Math.sin(ph)*6;
    c.strokeStyle=strong?'#ffffffcc':'#ffffff88';c.lineWidth=strong?3:2;c.beginPath();c.moveTo(x-6+i*6,y);
    c.bezierCurveTo(x-14+i*8+dx,y-30,x+8+i*4-dx,y-52,x-4+i*7+dx,y-(strong?100:70));c.stroke();}
}
function burner(c,cx,fy,port,o){
  const W=port?92:106,h=port?66:62,top=fy-h;E(c,cx,fy+3,W/2+8,8,'#6b584422');
  L(c,cx-W*.3,fy,cx-W*.26,top+40,'#6b4f2a',5);L(c,cx+W*.3,fy,cx+W*.26,top+40,'#6b4f2a',5);L(c,cx,fy+2,cx,top+44,'#6b4f2a',5);
  E(c,cx,top+34,W*.46,24,'#8a6a3a');E(c,cx,top+16,W*.44,9,'#6b4f2a');E(c,cx,top+15,W*.38,6,'#c9b49a');
  R(c,cx-W*.48,top+10,11,20,'#8a6a3a',4);R(c,cx+W*.48-11,top+10,11,20,'#8a6a3a',4);
  E(c,cx,top+36,W*.18,7,'#a07c46');
  for(let i=0;i<7;i++)L(c,cx-18+i*6,top+15,cx-18+i*6,top-8-(i%3)*3,'#b8432f',1.6);
  if(o.lit)for(let i=0;i<3;i++)E(c,cx-6+i*6,top-12,2,2,'#ffb35c');
  smoke(c,cx,top-10,o.lit?3:2,{t:o.t,reduced:o.reduced,strong:o.lit});
}
function pond(c,cx,cy,rx,ry,o){
  E(c,cx,cy+4,rx+8,ry+8,'#8f6746');E(c,cx,cy,rx,ry,'#6fa3a8');E(c,cx-rx*.3,cy-ry*.3,rx*.4,ry*.25,'#8fc0c2');
  for(const [dx,dy,r] of [[-.5,.1,.16],[.35,-.2,.14],[.1,.35,.13],[-.15,-.35,.11],[.62,.25,.12]])E(c,cx+dx*rx,cy+dy*ry,r*rx,r*rx*.42,'#5f8f4a');
  for(const [dx,dy] of [[-.48,-.05],[.36,-.32]]){const x=cx+dx*rx,y=cy+dy*ry;for(let i=0;i<5;i++){const a=i*Math.PI/5;E(c,x+2+Math.cos(a)*6,y-8-Math.sin(a)*4,5,8,'#f2a8b8');}E(c,x+2,y-8,3,3,'#f3d590');}
  for(let i=0;i<3;i++){const a=o.reduced?i*2.1:o.t*.4+i*2.1,x=cx+Math.cos(a)*rx*.55,y=cy+Math.sin(a)*ry*.4;E(c,x,y,7,3,'#e8693f');P(c,[[x-7,y],[x-12,y-3],[x-12,y+3]],'#e8693f');}
}
function fence(c,x0,x1,fy,o){
  for(let x=x0;x<=x1;x+=15){L(c,x,fy,x,fy-46,'#b89a5a',4);}
  L(c,x0-4,fy-36,x1+4,fy-36,'#9c7f44',4);L(c,x0-4,fy-16,x1+4,fy-16,'#9c7f44',4);
  const n=Math.floor((x1-x0)/13);
  for(let i=0;i<n;i++){const x=x0+8+i*13,sw=o.reduced?0:Math.sin(o.t*1.2+i)*1.5;if(hash(i*3.1)<.25)continue;
    R(c,x+sw,fy-32,8,16+((i*7)%3)*3,'#c8422f',2);L(c,x+4,fy-36,x+4+sw,fy-32,'#e8c26a',1);}
  if(o.mine){R(c,x1-22,fy-34,10,20,'#e04a34',2,'#ffe08a',1.5);}
}
function bodhi(c,x,fy,port){
  const s=port?.8:1;R(c,x-10*s,fy-120*s,20*s,124*s,'#7a5a3c',6);L(c,x,fy-90*s,x-30*s,fy-130*s,'#7a5a3c',8*s);L(c,x,fy-100*s,x+28*s,fy-140*s,'#7a5a3c',7*s);
  for(const [dx,dy,r,col] of [[-50,-150,46,'#5f8f4a'],[40,-160,50,'#6f9f5a'],[0,-195,52,'#5a8a46'],[-20,-130,34,'#7aa860'],[55,-120,30,'#6f9f5a']])E(c,x+dx*s,fy+dy*s,r*s,r*.82*s,col);
  for(let i=0;i<9;i++){const a=i*.7,rr=40*s;const lx=x+Math.cos(a)*rr,ly=fy-160*s+Math.sin(a)*rr*.6;P(c,[[lx,ly-5*s],[lx+4*s,ly],[lx,ly+6*s],[lx-4*s,ly]],'#8dbb6d');}
}
function bench(c,x0,x1,fy){R(c,x0,fy-20,x1-x0,9,'#b9a99a',4,'#8f8073',1.5);R(c,x0+6,fy-12,8,12,'#9c8d80',2);R(c,x1-14,fy-12,8,12,'#9c8d80',2);}
function sideGate(c,x,y0,y1,port){
  const wd=port?30:34;R(c,x-wd/2,y0-70,wd,y1-y0+70,'#f3e3c1',6,'#d6b394',2);E(c,x,y0-10,wd*.32,34,'#5a3a2a');
  R(c,x-wd/2-4,y0-78,wd+8,12,'#8a4b33',4);
}
function yardRoom(c,port,o){
  const f=port?F.port:F.land,w={c:null};
  E(c,f.x+f.w/2,f.y+f.h+12,f.w*.48,22,'#8b735322');R(c,f.x-8,f.y-6,f.w+16,f.h+14,'#b88b62',f.r+6);
  c.save();c.beginPath();c.roundRect(f.x,f.y,f.w,f.h,f.r);c.clip();
  sky(c,w,f);
  if(port){bellTower(c,40,f.base,true);hall(c,150,f.base,330,true);gate(c,500,f.base,170,true);for(const x of [490,560,640])areca(c,x,f.base,170);}
  else{bellTower(c,96,f.base,false);hall(c,230,f.base,520,false);gate(c,800,f.base,250,false);for(const x of [780,880,990,1080])areca(c,x,f.base,190);}
  yard(c,f);
  // the hall's steps, and the open middle door (where you go in)
  const [hx,hw]=port?[150,330]:[230,520];R(c,hx+hw*.3,f.base-2,hw*.4,10,'#cfa37b',3,'#b88b62',1.5);R(c,hx+hw*.34,f.base+8,hw*.32,9,'#d6ad86',3,'#b88b62',1.5);
  // the bell rings: circles spread from the bell
  const bell=port?[75,405]:[138,336];
  if(o.bell){const k=o.reduced?.5:o.bell;for(let i=0;i<3;i++){const r=20+((k*90+i*30)%90);c.strokeStyle=`rgba(255,240,200,${Math.max(0,.8-r/110)})`;c.lineWidth=3;c.beginPath();c.arc(bell[0],bell[1],r,0,Math.PI*2);c.stroke();}}
  c.restore();
}
function yardProps(c,port,o){
  const out=[];
  if(port){
    out.push([564,()=>brooms(c,140,200,564)]);
    out.push([648,()=>burner(c,350,648,true,{...o,lit:o.lit})]);
    out.push([780,()=>pond(c,171,761,95,22,o)]);
    out.push([575,()=>fence(c,505,645,575,{...o,mine:o.wish})]);
    out.push([764,()=>bodhi(c,560,764,true)]);
    out.push([562,()=>bench(c,400,460,562)]);
    out.push([700,()=>sideGate(c,44,640,700,true)]);
  }else{
    out.push([522,()=>brooms(c,205,275,522)]);
    out.push([580,()=>burner(c,600,580,false,{...o,lit:o.lit})]);
    out.push([682,()=>pond(c,330,661,115,22,o)]);
    out.push([528,()=>fence(c,865,1005,528,{...o,mine:o.wish})]);
    out.push([656,()=>bodhi(c,1041,656,false)]);
    out.push([526,()=>bench(c,655,745,526)]);
    out.push([700,()=>sideGate(c,92,620,700,false)]);
  }
  return out;
}

/* ------------------------------------------------------------ the main hall */
function mo(c,cx,fy,s,hit){
  R(c,cx-30*s,fy-14*s,60*s,14*s,'#b44a3a',5*s);E(c,cx,fy-14*s,26*s,8*s,'#c9564a');   // the red cushion
  E(c,cx,fy-30*s*(hit?.96:1),24*s,18*s,'#a5642f');E(c,cx,fy-30*s,18*s,4*s,'#5a3216');E(c,cx-8*s,fy-38*s,6*s,4*s,'#c98a4a');
  L(c,cx+30*s,fy-20*s,cx+48*s,fy-44*s,'#7a4a24',4*s);E(c,cx+48*s,fy-44*s,6*s,6*s,'#7a4a24');
}
function bowlBell(c,cx,fy,s){
  R(c,cx-30*s,fy-14*s,60*s,14*s,'#b44a3a',5*s);E(c,cx,fy-14*s,26*s,8*s,'#c9564a');
  P(c,[[cx-22*s,fy-40*s],[cx+22*s,fy-40*s],[cx+18*s,fy-16*s],[cx-18*s,fy-16*s]],'#b8873a');E(c,cx,fy-40*s,22*s,6*s,'#7a5a24');E(c,cx,fy-40*s,18*s,4*s,'#3b2a14');
}
function hallRoom(w,c,port,o){
  return shell(w,{wall:'#ecd2a6',wallLow:'#d9b585',floor:'#a8744a',floor2:'#9c6a42',tile:64,rim:'#8a5a3a',trim:'#7d2f21'},(c,g)=>{
    const X=g.X,H=g.H,k=g.k;
    // red columns and hanging banners, the timetable, the door to the yard
    for(const u of [.18,.82]){R(c,X(u)-12*k,g.f.y,24*k,g.base-g.f.y,RED,4,RED_D,2);}
    for(const u of [.29,.71]){R(c,X(u)-16*k,H(.06),32*k,H(.55)-H(.06),'#e9c46a',4,'#b8873a',1.5);R(c,X(u)-10*k,H(.1),20*k,H(.5)-H(.12),'#f4dc94',3);}
    R(c,X(.02),H(.3),X(.14)-X(.02),H(.7)-H(.3),'#5a3a2a',6,'#2f2a26',2);
    T(c,'THỜI KHÓA',X(.08),H(.36),fit(c,'THỜI KHÓA',X(.14)-X(.02)-8,port?13:11),'#f4dc94',800);
    for(let i=0;i<4;i++)L(c,X(.035),H(.44)+i*13*k,X(.125),H(.44)+i*13*k,'#e9dcc4',2);
    doorway(c,g,.9,{open:true,frame:'#c98a5a'});   // its sign is drawn over the scene (v4/chua-visit.js marks)
    // the Buddha on the back wall, his lamp light
    const foot=g.base-(port?64:58),h=(g.base-g.f.y)*(port?.74:.78);
    E(c,X(.5),foot-h*.55,h*.62,h*.5,'#fff3d222');
    buddha(c,X(.5),foot,h);
    // the prayer mats on the floor
    for(const [u,v] of [[.42,.46],[.58,.46],[.42,.6],[.58,.6]]){R(c,X(u)-48*k,g.Y(v)-14*k,96*k,30*k,'#d9b46a',6,'#b8873a',1.5);for(let i=1;i<4;i++)L(c,X(u)-48*k+i*24*k,g.Y(v)-12*k,X(u)-48*k+i*24*k,g.Y(v)+14*k,'#c99f52',1);}
  });
}
function altar(c,g,o){
  const X=g.X,Y=g.Y,k=g.k,top=Y(.02)-(g.port?54:46),x0=X(.36),x1=X(.64);
  R(c,x0,top,x1-x0,Y(.2)-top,'#8a3a26',6,'#5a2416',2);R(c,x0-8,top-8,x1-x0+16,14,'#a8432f',5,'#5a2416',1.5);
  R(c,x0+18,top+18,x1-x0-36,Y(.2)-top-30,'#7d2f21',4);
  // flowers, fruit, two covered candles, one stick of incense
  const cx=(x0+x1)/2;R(c,cx-70*k,top-34*k,16*k,26*k,'#e6e0d4',4);for(let i=0;i<3;i++)E(c,cx-62*k+(i-1)*7*k,top-40*k-i%2*5*k,6*k,7*k,'#f2a8b8');
  E(c,cx+62*k,top-14*k,22*k,7*k,'#e6e0d4');for(const [dx,col] of [[-10,'#e3b04b'],[0,'#8fbf5a'],[10,'#e8693f'],[-4,'#e3b04b']])E(c,cx+62*k+dx*k,top-22*k-(dx===-4?8*k:0),7*k,7*k,col);
  for(const dx of [-120,120]){R(c,cx+dx*k-5*k,top-30*k,10*k,26*k,'#fbf6ec',3);R(c,cx+dx*k-9*k,top-46*k,18*k,22*k,'#ffffff55',6,'#ffffff99',1);E(c,cx+dx*k,top-36*k,3*k,5*k,o.reduced?'#ffb35c':`rgba(255,179,92,${.8+.2*Math.sin(o.t*6+dx)})`);}
  R(c,cx-14*k,top-16*k,28*k,14*k,'#8a6a3a',4);L(c,cx,top-16*k,cx,top-44*k,'#b8432f',1.6);
  smoke(c,cx,top-44*k,1,{t:o.t,reduced:o.reduced,strong:false});
}
function hallProps(c,port,o){
  const g=geo(port),X=g.X,Y=g.Y,s=port?.95:1;
  return [[Y(.2),()=>altar(c,g,o)],[Y(.27),()=>mo(c,X(.235),Y(.27),s,o.mo)],[Y(.27),()=>bowlBell(c,X(.765),Y(.27),s)]];
}

/* ------------------------------------------------------------ the dining hall */
function diningRoom(w,c,port,o){
  return shell(w,{wall:'#f3e3c1',wallLow:'#e3cda4',floor:'#c9a27a',floor2:'#bf9670',tile:56,rim:'#b88b62',trim:'#a8744a'},(c,g)=>{
    const X=g.X,H=g.H,k=g.k;
    doorway(c,g,.1,{open:true,frame:'#c98a5a'});
    windowPane(c,w,X(.48)-60*k,H(.18),120*k,H(.55)-H(.18),{frame:'#e8dccb',view:(c,x,y,wd,ht)=>{for(let i=0;i<3;i++)E(c,x+wd*(.2+i*.3),y+ht*.95,wd*.18,ht*.35,'#7aa860');}});
    R(c,X(.24),H(.3),X(.4)-X(.24),H(.62)-H(.3),'#3d4a44',6,'#8f6746',3);
    T(c,o.feast?'CƠM CHAY':'BẾP CHAY',(X(.24)+X(.4))/2,H(.4),fit(c,o.feast?'CƠM CHAY':'BẾP CHAY',X(.4)-X(.24)-12,port?13:11),'#f3d98a',800);
    for(let i=0;i<3;i++)L(c,X(.26),H(.48)+i*11*k,X(.38),H(.48)+i*11*k,'#e9dcc4',2);
    plate(c,g,X(.66),H(.22),'Ăn trong chánh niệm',{bg:'#7d2f21',ink:'#f4dc94'});
  });
}
function stove(c,g,o){
  const X=g.X,Y=g.Y,k=g.k,x0=X(.74),x1=X(.94),top=Y(.0)-56*k;
  R(c,x0,top,x1-x0,Y(.18)-top,'#b85c42',6,'#7d2f21',2);R(c,x0+10,top+10,x1-x0-20,14,'#5a3a2a',4);
  const cx=(x0+x1)/2;E(c,cx,top+2,40*k,12*k,'#6b6f76');R(c,cx-40*k,top-36*k,80*k,38*k,'#7d838b',10*k);E(c,cx,top-36*k,40*k,9*k,'#9aa0a8');
  smoke(c,cx,top-40*k,2,{t:o.t,reduced:o.reduced,strong:false});
}
function table(c,g,o){
  const X=g.X,Y=g.Y,k=g.k,x0=X(.28),x1=X(.7),ty=Y(.38);
  // the people at the far bench on rằm and mùng 1
  if(o.feast)for(let i=0;i<4;i++)sitter(c,x0+(x1-x0)*(.14+i*.24),ty-6*k,g.port?.9:1,i+7,i===2?'kid':'');
  R(c,x0-10,ty-10*k,x1-x0+20,12*k,'#9c7a58',3);
  R(c,x0,ty,x1-x0,Y(.5)-ty,'#c08a5a',6,'#8f6746',2);R(c,x0,ty,x1-x0,10*k,'#d9a874',4);
  for(let i=0;i<(o.feast?6:2);i++){const x=x0+(x1-x0)*(.1+i*.16);E(c,x,ty+6*k,13*k,5*k,'#f4f1ea');E(c,x,ty+4*k,9*k,3*k,o.feast?'#e8d9a8':'#d8d2c6');}
  if(o.feast){E(c,(x0+x1)/2,ty+2*k,26*k,8*k,'#8a6a3a');E(c,(x0+x1)/2,ty-2*k,22*k,6*k,'#c9a86a');}
  R(c,x0-6,Y(.56),x1-x0+12,10*k,'#9c7a58',3);R(c,x0+8,Y(.56)+8*k,8*k,14*k,'#7a5a3c',2);R(c,x1-16,Y(.56)+8*k,8*k,14*k,'#7a5a3c',2);
}
function diningProps(c,port,o){
  const g=geo(port),Y=g.Y;
  return [[Y(.18),()=>stove(c,g,o)],[Y(.6),()=>table(c,g,o)]];
}

/* ------------------------------------------------------------ entry points */
/** Paint the area's backdrop (walls, sky, floor). w: {ctx, isPortrait(), reduced, time, c:null}. */
export function paintRoom(w,area,o){
  const c=w.ctx,port=w.isPortrait();
  if(area==='dien')hallRoom(w,c,port,o);
  else if(area==='trai')diningRoom(w,c,port,o);
  else yardRoom(c,port,o);
}
/** The area's things that stand on the floor: [[depth y, draw]] (sorted with the people by the caller). */
export function areaProps(c,area,port,o){
  return area==='dien'?hallProps(c,port,o):area==='trai'?diningProps(c,port,o):yardProps(c,port,o);
}
/** The words a "look" spot says when the player walks up to it. */
export const LOOKS={
  bode:'Cây bồ đề già, lá hình trái tim rung rinh trong gió sông.',
  giatri:'Chuông gia trì chỉ thỉnh khi tụng kinh. Muốn tụng, bạn ngồi bên mõ hoặc thưa thầy.',
  ban:'Bình sen, đĩa trái cây, hai ngọn nến có chụp kính. Trong điện chỉ thắp một nén hương.',
  thoikhoa:'Thời khóa: 4:30 công phu sáng · 11:00 cúng ngọ · 18:00 công phu chiều.',
  thucdon:'Rằm và mùng 1, chùa nấu cơm chay mời mọi người: canh nấm, đậu hũ kho, rau luộc.',
};
export {T,fit,R,E,L,P};
