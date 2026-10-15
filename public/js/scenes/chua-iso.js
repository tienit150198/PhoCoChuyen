/** 🛕 Chùa Gió Lành in 2.5D (owner 15/10: "tối ưu hết chỗ chùa … đẹp hơn, theo dạng 2.5d trình bày rõ ràng và đẹp";
 * "mọi người vào 1 cái cây, rồi ghi cái ước nguyện … trong đó có rất nhiều cái cây ước nguyện").
 * One courtyard with everything in sight, drawn like the 2.5D town map: the town's own paintings (the map's pagoda, its
 * banyan and its vegetation sheet, already cached by players) on an isometric stone courtyard; the rest drawn here.
 *   back      the main hall (chánh điện), its steps facing the gate: khấn on the mat, the mõ for tụng kinh, thầy Huệ
 *             Minh; the bell pavilion, the broom rack, the timetable board, the old bodhi tree;
 *   middle    the path from the three-arch gate to the steps, the big incense burner on it, the lotus pond and bench;
 *   left      🌳 Vườn ước nguyện: one painted tree per wish tree (game/chua_wish.py TREES), each with the colours of its
 *             newest ribbons hanging from the branches and a name board;
 *   front     the dining pavilion (cơm chay on rằm and mùng 1, bà Nhạn).
 * Pure (no DOM, no server): world coordinates in tiles (0..N on both axes), projected 2:1 to scene pixels; a grid path
 * finder on free tiles; painters given the loaded images (null while loading: plain shapes instead).
 * Nothing moves when `reduced` is set. */
import {R,E,L,T,P,fit} from './kit.js';
import {person,PEOPLE,LOOKS} from './chua-place.js';

export const N=18;
export const project=(x,y)=>[(x-y)*32,(x+y)*16];
export const unproject=(sx,sy)=>[(sx/32+sy/16)/2,(sy/16-sx/32)/2];
/** The drawn part of the scene (scene pixels) that a wide stage shows whole. */
export const VIEW=[-600,-210,600,600];
export const IMAGES={hall:'/icons/careers-v1/pagoda.webp',tree:'/icons/isometric/tree.webp',veg:'/icons/cozy-v2/vegetation.webp'};
export const RIBBON={do:'#d8402f',vang:'#eab33a',hong:'#ec86a5',xanh:'#4fa463',tim:'#8d6ccc'};
/** The wish trees' places in the grove (the left half), in the order of game/chua_wish.py TREES; a little off-grid. */
export const GROVE=[[2.7,10.6],[6.3,10.4],[9.9,10.9],[2.5,13.9],[6.1,13.9],[9.7,14.3],[2.7,17.0],[6.3,17.0],[9.9,17.1]];
export {PEOPLE,LOOKS};

const S=(id,kind,at,stand,more={})=>({id,kind,at,stand,r:more.r||46,lift:more.lift??34,...more});
/** The plan of the day: {spots, blocks (world rects), people, entry}. `trees`: the wish trees (game/chua_wish.py order). */
export function plan(day,trees=[]){
  const lunar=day?.lunar|0,feast=!!day?.feast;
  const spots=[
    S('khan','act',[7.6,4.4],[8.6,4.6],{act:'khan',r:50,lift:24}),
    S('tung','act',[7.5,7.4],[8.5,7.4],{act:'tung',r:42,lift:28}),
    S('huong','act',[10.7,4.6],[11.9,5.7],{act:'huong',r:46,lift:46}),
    S('chuong','act',[13.2,1.8],[13.2,3.7],{act:'chuong',r:58,lift:100}),
    S('quet','act',[9.7,1.4],[9.8,2.8],{act:'quet',r:38,lift:34}),
    S('ngoi','act',[15.0,8.4],[11.4,10.3],{act:'ngoi',r:58,lift:14}),   // the badge on the pond, the seat on the bench
    S('com','act',[14.05,13.9],[12.55,13.9],{act:'com',r:54,lift:40}),
    S('nguyen','grove',[6.2,13.9],[12.2,12.2],{act:'nguyen',r:0,lift:0}),
    S('look:bode','look',[16.8,1.2],[16.2,3.0],{look:'bode',r:62,lift:120}),
    S('look:thoikhoa','look',[7.7,.9],[8.0,2.4],{look:'thoikhoa',r:32,lift:56}),
  ];
  const groves=Math.max(0,Math.min(GROVE.length,trees.length));
  for(let i=0;i<groves;i++){const at=GROVE[i];spots.push(S('tree:'+trees[i].id,'tree',at,[at[0]+1.3,Math.min(at[1]+.95,N-.7)],{tree:trees[i].id,r:54,lift:74}));}
  const people=[{who:'thay',x:8.4,y:6.1},{who:'nhan',x:15.6,y:12.4}];
  if(lunar%2===0)people.push({who:'na',x:12.9,y:6.9});else people.push({who:'quyen',x:12.4,y:9.25,sit:true});   // bé Na by the pond, chị Quyên on the bench
  if(feast)people.push({who:'bay',x:11.4,y:7.9});
  const front={nhan:[-.6,-.8],na:[-.8,.5],quyen:[0,1.05]};   // bà Nhạn is spoken to from the path side (her stove and the table are behind her)
  for(const q of people){const f=front[q.who]||[.85,.55];spots.push(S('npc:'+q.who,'npc',[q.x,q.y],[q.x+f[0],q.y+f[1]],{who:q.who,r:36,lift:50}));}
  const blocks=[[0,0,7.1,8.1],[12.2,.8,14.2,2.8],[9.1,1.1,10.3,1.7],[10.2,4.1,11.2,5.1],[13.6,7.0,16.4,9.8],[11.8,8.9,13.0,9.6],
    [16.0,12.2,17.6,13.6],[16.9,15.1,17.5,15.7],[13.1,12.4,14.9,15.4],[16.2,.5,17.4,1.8],[7.3,.5,8.1,1.2],[17.0,3.0,18,6.2]];
  for(let i=0;i<groves;i++){const [x,y]=GROVE[i];blocks.push([x-.6,y-.5,x+.6,y+.5]);}
  for(const q of people)if(!q.sit)blocks.push([q.x-.3,q.y-.3,q.x+.3,q.y+.3]);
  return {spots,blocks,people,entry:[16.3,4.6]};
}

/* ---------------------------------------------------------------- walking */
const PAD=.3,STEP=.5;
export function free(pl,x,y){
  if(!(x>=.5&&y>=.5&&x<=N-.5&&y<=N-.5))return false;
  for(const b of pl.blocks)if(x>b[0]-PAD&&x<b[2]+PAD&&y>b[1]-PAD&&y<b[3]+PAD)return false;
  return true;
}
/** Does segment AB pass through the open rectangle (x0,y0)-(x1,y1)? (exact, like scenes/chua-place.js) */
function hits(A,B,x0,y0,x1,y1){let t0=0,t1=1;const dx=B[0]-A[0],dy=B[1]-A[1];
  for(const [p,q] of [[-dx,A[0]-x0],[dx,x1-A[0]],[-dy,A[1]-y0],[dy,y1-A[1]]]){if(p===0){if(q<=0)return false;continue;}const t=q/p;if(p<0){if(t>t0)t0=t;}else if(t<t1)t1=t;if(t0>=t1)return false;}
  return t0<t1;}
/** Is the straight walk from a to b free all the way? (the courtyard is convex: both ends inside is enough for it) */
function clear(pl,a,b){if(!free(pl,b[0],b[1]))return false;for(const k of pl.blocks)if(hits(a,b,k[0]-PAD,k[1]-PAD,k[2]+PAD,k[3]+PAD))return false;return true;}
/** The free point nearest to p (a tap on a tree or a wall still walks somewhere sensible). */
export function nearestFree(pl,p){
  if(free(pl,p[0],p[1]))return [p[0],p[1]];
  for(let r=STEP/2;r<=7;r+=STEP/2)for(let a=0;a<16;a++){const q=[p[0]+Math.cos(a*Math.PI/8)*r,p[1]+Math.sin(a*Math.PI/8)*r];if(free(pl,q[0],q[1]))return q;}
  return null;
}
/** A walk from `from` to `to` in world tiles: [[x,y]…] (the end last), [] when already there, null when unreachable. */
export function route(pl,from,to){
  const end=nearestFree(pl,to);if(!end)return null;
  if(Math.hypot(end[0]-from[0],end[1]-from[1])<.05)return [];
  if(clear(pl,from,end))return [end];
  const cols=Math.round(N/STEP)+1,key=(i,j)=>i*cols+j;
  // the first grid point: the nearest one the player can walk straight to (a rounded one may sit past a corner)
  // the grid points next to a point that walk straight to (from) / from (to) it: a rounded one may sit past a corner
  const around=(p,ok)=>{const fi=Math.floor(p[0]/STEP),fj=Math.floor(p[1]/STEP),out=[];
    for(let di=-1;di<=2;di++)for(let dj=-1;dj<=2;dj++){const i=fi+di,j=fj+dj;if(i<0||j<0||i>=cols||j>=cols)continue;const q=[i*STEP,j*STEP];if(free(pl,q[0],q[1])&&ok(q))out.push([Math.hypot(q[0]-p[0],q[1]-p[1]),i,j]);}
    return out.sort((a,b)=>a[0]-b[0]);};
  const near=around(from,q=>clear(pl,from,q)),goals=new Set(around(end,q=>clear(pl,q,end)).map(([,i,j])=>key(i,j)));
  if(!near.length||!goals.size)return null;
  const start=[near[0][1],near[0][2]],prev=new Map([[key(...start),-1]]),queue=[start];
  let found=goals.has(key(...start))?start:null;
  for(let q=0;q<queue.length&&!found;q++){const [i,j]=queue[q];
    for(const [di,dj] of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[1,-1],[-1,1]]){const a=i+di,b=j+dj;if(a<0||b<0||a>=cols||b>=cols||prev.has(key(a,b)))continue;
      if(!free(pl,a*STEP,b*STEP)||(di&&dj&&(!free(pl,a*STEP,j*STEP)||!free(pl,i*STEP,b*STEP))))continue;
      prev.set(key(a,b),key(i,j));queue.push([a,b]);if(goals.has(key(a,b))){found=[a,b];break;}}}
  if(!found)return null;
  const cells=[];for(let k=key(...found);k!==-1;k=prev.get(k))cells.unshift([Math.floor(k/cols)*STEP,(k%cols)*STEP]);
  cells.push(end);
  const out=[];let here=from;   // keep only the corners a straight walk needs
  for(let i=0;i<cells.length;i++){const next=cells[i+1];if(!next||!clear(pl,here,next)){out.push(cells[i]);here=cells[i];}}
  return out;
}

/* ---------------------------------------------------------------- painting helpers */
const poly=(c,pts,fill,stroke,lw=1)=>{c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();if(fill){c.fillStyle=fill;c.fill();}if(stroke){c.strokeStyle=stroke;c.lineWidth=lw;c.stroke();}};
const at=(x,y,dz=0)=>{const p=project(x,y);return [p[0],p[1]-dz];};
const loaded=img=>!!(img&&img.complete&&img.naturalWidth);
/** An isometric box: footprint x0..x1 × y0..y1 standing on z, height h; the two faces we see, then the top. */
function box(c,x0,y0,x1,y1,h,top,left,right,z=0){
  const a=at(x0,y0,z),b=at(x1,y0,z),d=at(x0,y1,z),e=at(x1,y1,z),up=p=>[p[0],p[1]-h];
  poly(c,[d,e,up(e),up(d)],left);poly(c,[b,e,up(e),up(b)],right);poly(c,[up(a),up(b),up(e),up(d)],top);
}
/** A hip roof (mái đình) over x0..x1 × y0..y1 at eave height z: two faces we see, a ridge with a pearl, curled tips. */
function roof(c,x0,y0,x1,y1,z,h,o={}){
  const tile=o.tile||'#c95a3c',dark=o.dark||'#a3412b',edge=o.edge||'#f1dfc0';
  const long=x1-x0>=y1-y0,mx=(x0+x1)/2,my=(y0+y1)/2,half=Math.min(x1-x0,y1-y0)/2;
  const r0=long?at(x0+half,my,z+h):at(mx,y0+half,z+h),r1=long?at(x1-half,my,z+h):at(mx,y1-half,z+h);
  const a=at(x0,y0,z),b=at(x1,y0,z),d=at(x0,y1,z),e=at(x1,y1,z),down=p=>[p[0],p[1]+5];
  poly(c,[down(a),down(b),down(e),down(d)],'#5e2a1c');   // the eaves' underside
  if(long){poly(c,[a,b,r1,r0],dark);poly(c,[a,d,r0],tile);}else{poly(c,[a,d,r1,r0],tile);poly(c,[a,b,r0],dark);}   // the back faces
  if(long){poly(c,[d,e,r1,r0],tile);poly(c,[b,e,r1],dark);}else{poly(c,[b,e,r1,r0],dark);poly(c,[d,e,r1],tile);}
  c.strokeStyle='#7a2f1f40';c.lineWidth=1;
  const face=long?[d,e,r1,r0]:[d,e,r1,r1];for(let i=1;i<7;i++){const u=i/7,p=[face[0][0]+(face[1][0]-face[0][0])*u,face[0][1]+(face[1][1]-face[0][1])*u],q=[face[3][0]+(face[2][0]-face[3][0])*u,face[3][1]+(face[2][1]-face[3][1])*u];c.beginPath();c.moveTo(...p);c.lineTo(...q);c.stroke();}
  L(c,d[0],d[1],e[0],e[1],edge,2.5);L(c,b[0],b[1],e[0],e[1],edge,2.5);L(c,r0[0],r0[1],r1[0],r1[1],edge,3.5);
  L(c,e[0],e[1],r1[0],r1[1],edge,2.5);
  const curl=(p,dx)=>{c.strokeStyle=edge;c.lineWidth=3;c.lineCap='round';c.beginPath();c.moveTo(p[0],p[1]);c.quadraticCurveTo(p[0]+dx*.6,p[1]-2,p[0]+dx,p[1]-11);c.stroke();};
  curl(d,-9);curl(e,0);curl(b,9);curl(r0,-7);curl(r1,7);
  if(o.pearl){const m=[(r0[0]+r1[0])/2,(r0[1]+r1[1])/2];E(c,m[0],m[1]-5,5,5,'#f2c24b');}
}
function shadow(c,x,y,rx,ry,a=.18){c.save();c.globalAlpha=a;const p=project(x,y);E(c,p[0],p[1],rx,ry,'#4a3a26');c.restore();}

/* ---------------------------------------------------------------- the ground (drawn first) */
export function ground(c,o={}){
  const night=!!o.night,g=12;
  poly(c,[at(-g,-g),at(N+g,-g),at(N+g,N+g),at(-g,N+g)],night?'#5d6b4a':'#aec48b');
  c.save();c.globalAlpha=.35;for(let i=0;i<90;i++){const x=((i*37)%(N+14))-7,y=((i*53)%(N+14))-7;if(x>-.6&&x<N+.6&&y>-.6&&y<N+.6)continue;const p=project(x,y);L(c,p[0],p[1],p[0]+2,p[1]-6,'#7f9b62',2);L(c,p[0]+4,p[1],p[0]+5,p[1]-5,'#7f9b62',2);}c.restore();
  poly(c,[at(-.35,-.35),at(N+.35,-.35),at(N+.35,N+.35),at(-.35,N+.35)].map(([x,y])=>[x,y+6]),'#b8a17c');
  poly(c,[at(-.35,-.35),at(N+.35,-.35),at(N+.35,N+.35),at(-.35,N+.35)],'#cdb894');
  poly(c,[at(0,0),at(N,0),at(N,N),at(0,N)],night?'#a99a82':'#eadfc8');
  c.strokeStyle=night?'#8f826d':'#dccfb4';c.lineWidth=1;
  for(let i=1;i<N;i++){let p=at(i,0),q=at(i,N);c.beginPath();c.moveTo(...p);c.lineTo(...q);c.stroke();p=at(0,i);q=at(N,i);c.beginPath();c.moveTo(...p);c.lineTo(...q);c.stroke();}
  // the path: gate → burner → hall steps, and the open space in front of the steps
  poly(c,[at(7.1,3.6),at(N,3.6),at(N,5.6),at(7.1,5.6)],night?'#b9ab92':'#f5ecd9','#d8c7a6');
  poly(c,[at(7.1,2.6),at(9.4,2.6),at(9.4,8.0),at(7.1,8.0)],night?'#b9ab92':'#f5ecd9');
  // the grove: soil and moss on the left half, a stepping-stone path through it
  poly(c,[at(.4,8.9),at(11.6,8.9),at(11.6,N-.3),at(.4,N-.3)],night?'#6f7a52':'#bfcc94');
  c.save();c.globalAlpha=.5;for(let i=0;i<70;i++){const x=.8+((i*7.3)%10.4),y=9.2+((i*3.7)%8.4),p=project(x,y);E(c,p[0],p[1],6,2.6,'#9fb57c');}c.restore();
  for(let i=0;i<12;i++){const x=4.4+(i%2)*.4,y=9.4+i*.72,p=project(x+((i*5)%3)*.25,y);E(c,p[0],p[1],10,5,'#e2d6bd');}
  for(let i=0;i<10;i++){const x=1.2+i*1.05,y=12.2+(i%2)*.3,p=project(x,y);E(c,p[0],p[1],10,5,'#e2d6bd');}
  for(let i=0;i<10;i++){const x=1.2+i*1.05,y=15.6+(i%2)*.3,p=project(x,y);E(c,p[0],p[1],10,5,'#e2d6bd');}
  // low walls along the two back sides
  for(let x=0;x<N;x+=1)box(c,x,-.42,x+1,-.02,22,'#b4563f','#e8d6b6','#f2e4c8');
  for(let y=0;y<N;y+=1)box(c,-.42,y,-.02,y+1,22,'#a94f3a','#e2cdab','#efe0c3');
}

/* ---------------------------------------------------------------- the things (sorted with the people by depth) */
const VEG=['banyan','flamboyant','palm','banana','bamboo','flowers','shrubs','rocks'];
function veg(c,img,kind,x,y,w,flip=false){
  const p=project(x,y);if(!loaded(img)){E(c,p[0],p[1]-w*.45,w*.4,w*.34,'#7aa35e');return;}
  const i=VEG.indexOf(kind),fw=img.naturalWidth/4,fh=img.naturalHeight/2,h=w*fh/fw;
  c.save();c.translate(p[0],p[1]);if(flip)c.scale(-1,1);c.drawImage(img,i%4*fw,Math.floor(i/4)*fh,fw,fh,-w/2,-h*.93,w,h);c.restore();
}
const HALL_W=470;
function hall(c,img,o){
  const base=at(5.8,6.6);   // puts the painting's steps (mirrored: u .29, v .84) right at the mat, world (7.4, 4.4)
  if(loaded(img)){const h=HALL_W*img.naturalHeight/img.naturalWidth;
    // the map's painting, mirrored so its steps face the gate; its blank name board gets the hall's name
    c.save();c.translate(base[0],base[1]);c.scale(-1,1);c.drawImage(img,-HALL_W*.55,-h*.86,HALL_W,h);c.restore();
    // the board (game's careers-v1 sign: x .3703, y .46, width .209, angle .3375), mirrored with the painting
    c.save();c.translate(base[0]+HALL_W*(.55-.3703),base[1]+h*(.46-.86));c.rotate(-.3375);
    T(c,'ĐẠI HÙNG BẢO ĐIỆN',0,0,fit(c,'ĐẠI HÙNG BẢO ĐIỆN',HALL_W*.19,13,800),'#7a2f1f',800);c.restore();
  }else{box(c,.8,.8,6.8,7.6,96,'#c8573c','#efe0c3','#e3cfac');roof(c,.4,.4,7.2,8.0,96,70,{pearl:true});}
  // the prayer mat before the steps and the mõ on its cushion
  const m=at(7.6,4.4);P(c,[[m[0]-34,m[1]],[m[0],m[1]-16],[m[0]+34,m[1]],[m[0],m[1]+16]],'#b4483a');P(c,[[m[0]-25,m[1]],[m[0],m[1]-11],[m[0]+25,m[1]],[m[0],m[1]+11]],'#d9ad5e');
  const q=at(7.5,7.4);E(c,q[0],q[1],22,10,'#9c3a2e');E(c,q[0],q[1]-13*(o.mo?.94:1),16,12,'#a5642f');E(c,q[0],q[1]-13,12,2.8,'#5a3216');E(c,q[0]-5,q[1]-19,4,2.5,'#c98a4a');
  L(c,q[0]+18,q[1]-6,q[0]+30,q[1]-22,'#7a4a24',3);E(c,q[0]+30,q[1]-22,4,4,'#7a4a24');
}
function bellTower(c,o){
  const x0=12.4,y0=1.0,x1=14.0,y1=2.6,h=74;
  box(c,x0-.3,y0-.3,x1+.3,y1+.3,10,'#d8c6a6','#bfa983','#cdb995');
  for(const [x,y] of [[x0,y0],[x1,y0],[x0,y1]]){const p=at(x,y,10);R(c,p[0]-3.5,p[1]-h,7,h,'#9a3b28',2);}
  const m=at((x0+x1)/2,(y0+y1)/2,10),sw=o.reduced?0:Math.sin(o.t*3)*2.5*(o.bell?1:0);
  L(c,m[0],m[1]-h+6,m[0]+sw,m[1]-h+20,'#5a3b24',2);
  c.save();c.translate(m[0]+sw,m[1]-h+20);P(c,[[-15,0],[15,0],[20,34],[-20,34]],'#b4893c');E(c,0,34,20,6,'#94702e');E(c,0,2,11,4,'#d9b25a');L(c,-6,6,-9,30,'#d9b25a99',3);c.restore();
  const p=at(x1,y1,10);R(c,p[0]-3.5,p[1]-h,7,h,'#9a3b28',2);
  roof(c,x0-.7,y0-.7,x1+.7,y1+.7,10+h,40,{pearl:true});
  roof(c,x0-.2,y0-.2,x1+.2,y1+.2,10+h+30,34,{});
  if(o.bell){const k=o.reduced?.5:o.bell;for(let i=0;i<3;i++){const r=26+((k*90+i*30)%90);c.strokeStyle=`rgba(255,236,190,${Math.max(0,.85-r/120)})`;c.lineWidth=3;c.beginPath();c.ellipse(m[0],m[1]-h+40,r,r*.55,0,0,Math.PI*2);c.stroke();}}
}
function smoke(c,x,y,o,strong){
  const n=strong?4:2;
  for(let i=0;i<n;i++){const k=o.reduced?(i+.5)/n:((o.t*.35+i/n)%1),yy=y-k*70,xx=x+Math.sin(k*6+i)*7;c.globalAlpha=Math.max(0,(1-k)*(strong?.55:.32));E(c,xx,yy,5+k*9,4+k*6,'#f4efe6');}
  c.globalAlpha=1;
}
function burner(c,o){
  const p=at(10.7,4.6);shadow(c,10.7,4.6,36,15);
  box(c,10.2,4.1,11.2,5.1,14,'#d9cdb4','#bcae92','#cbbd9f');
  const q=[p[0],p[1]-14];E(c,q[0],q[1]-4,26,10,'#7a5426');R(c,q[0]-22,q[1]-38,44,34,'#a87a36',10);E(c,q[0],q[1]-38,24,9,'#c49a4a');E(c,q[0],q[1]-38,17,5.5,'#5e4020');
  R(c,q[0]-28,q[1]-32,8,12,'#8d6630',3);R(c,q[0]+20,q[1]-32,8,12,'#8d6630',3);
  for(const dx of [-5,0,5])L(c,q[0]+dx,q[1]-40,q[0]+dx*1.2,q[1]-58,'#b3462d',1.6);
  for(const dx of [-5,0,5])E(c,q[0]+dx*1.2,q[1]-59,1.8,1.8,o.lit?'#ff9a3c':'#d9653a');
  smoke(c,q[0],q[1]-62,o,o.lit);
}
function pond(c,o){
  const pts=[at(13.6,7.0),at(16.4,7.0),at(16.4,9.8),at(13.6,9.8)];
  poly(c,pts.map(([x,y])=>[x,y+4]),'#a99474');poly(c,pts,'#cbbb9a');
  poly(c,[at(13.85,7.25),at(16.15,7.25),at(16.15,9.55),at(13.85,9.55)],'#7fb3b4');
  poly(c,[at(14.1,7.5),at(15.9,7.5),at(15.9,9.3),at(14.1,9.3)],'#6aa1a6');
  for(const [x,y,r] of [[14.3,7.8,10],[15.4,7.7,9],[15.6,8.9,11],[14.5,9.0,9],[15.0,8.4,8]]){const p=project(x,y);E(c,p[0],p[1],r,r*.5,'#5d8d48');}
  for(const [x,y] of [[14.6,7.9],[15.5,8.8]]){const p=project(x,y);for(let i=0;i<5;i++){const a=i*Math.PI/5;E(c,p[0]+Math.cos(a)*5,p[1]-6-Math.sin(a)*3,4,6,'#f2a8b8');}E(c,p[0],p[1]-6,2.4,2.4,'#f3d590');}
  for(let i=0;i<3;i++){const a=o.reduced?i*2:o.t*.5+i*2.1,p=project(15+Math.cos(a)*.6,8.4+Math.sin(a)*.5);E(c,p[0],p[1],6,2.6,'#e8693f');}
}
function bench(c){box(c,11.8,8.9,13.0,9.6,12,'#c9b8a6','#9c8b7b','#ad9c8b');}
function brooms(c){
  box(c,9.1,1.1,10.3,1.7,6,'#b88b62','#9c7550','#ab8159');
  for(let i=0;i<3;i++){const p=at(9.3+i*.4,1.35,6);L(c,p[0],p[1],p[0]+4,p[1]-44,'#b88b62',3);E(c,p[0]+5,p[1]-48,6,11,'#d9b97a');}
}
function notice(c){
  const p=at(7.7,.9);R(c,p[0]-3,p[1]-46,6,46,'#6a4a2f',2);R(c,p[0]-27,p[1]-74,54,38,'#5a3a24',4,'#c9a36a',2);
  for(let i=0;i<3;i++)L(c,p[0]-18,p[1]-63+i*9,p[0]+18,p[1]-63+i*9,'#f3e3c1aa',1.5);
}
/** Bếp trai: bà Nhạn's stove with the big pot (steaming on rằm and mùng 1) and the sign; open air, so nothing at the
 * front corner hides the courtyard. */
function stove(c,o){
  box(c,16.2,12.4,17.4,13.4,22,'#b9a38a','#9c7f62','#ab8c6e');
  const p=at(16.8,12.9,22);E(c,p[0],p[1]-6,18,8,'#4f4a44');R(c,p[0]-18,p[1]-22,36,16,'#5d5850',6);E(c,p[0],p[1]-22,18,7,'#6d675e');
  if(o.feast)smoke(c,p[0],p[1]-26,o,true);
  const s=at(17.2,15.4),sub=o.feast?'🍚 Hôm nay có cơm chay':'Cơm chay rằm · mùng 1';R(c,s[0]-2.5,s[1]-46,5,46,'#6a4a2f',2);R(c,s[0]-66,s[1]-80,132,34,'#fff4dc',8,'#c9a36a',2);
  T(c,'NHÀ TRAI',s[0],s[1]-69,11,'#7a3a26',800);T(c,sub,s[0],s[1]-55,fit(c,sub,120,10,700),'#8a6a4c',700);
}
function table(c,o){
  box(c,13.3,12.9,13.6,15.0,12,'#b9a99a','#8f8073','#a39383');box(c,14.5,12.9,14.8,15.0,12,'#b9a99a','#8f8073','#a39383');
  box(c,13.75,12.6,14.35,15.3,22,'#b07444','#8a5530','#96603a');
  if(o.feast){for(let i=0;i<5;i++){const p=at(14.05,12.95+i*.55,22);E(c,p[0],p[1],7,3.4,'#f3ede1');E(c,p[0],p[1]-1,4.6,1.8,'#e0b65a');}}
}
/** An arch on the +x face of a wall at x, from y0 to y1, `h` high (dark opening). */
function arch(c,x,y0,y1,h){
  const a=at(x,y0),b=at(x,y1),m=[(a[0]+b[0])/2,(a[1]+b[1])/2];
  c.beginPath();c.moveTo(a[0],a[1]);c.lineTo(a[0],a[1]-h*.62);c.quadraticCurveTo(m[0],m[1]-h*1.05,b[0],b[1]-h*.62);c.lineTo(b[0],b[1]);c.closePath();c.fillStyle='#5a3a2a';c.fill();
}
function gate(c){
  // cổng tam quan on the courtyard's right edge: two low side arches and a tall middle one under three roofs
  const x0=17.35,x1=17.95;
  for(const [y0,y1,h,top] of [[2.9,3.9,50,0],[5.3,6.3,50,0],[3.9,5.3,70,1]]){
    box(c,x0,y0,x1,y1,h,'#e9dcc2','#e2d0b0','#f3e8d4');arch(c,x1,y0+.22,y1-.22,h*(top?.78:.7));
    roof(c,x0-.25,y0-.12,x1+.25,y1+.12,h,top?28:20,{pearl:!!top});
  }
  const p=at(x1+.25,4.6,70+14);R(c,p[0]-34,p[1]-8,68,17,'#8a2f22',4,'#e8bf62',1);T(c,'TAM QUAN',p[0],p[1]+.5,fit(c,'TAM QUAN',60,10,800),'#f6d98a',800);
}
function lantern(c,x,y){const p=at(x,y);shadow(c,x,y,10,4);R(c,p[0]-6,p[1]-30,12,30,'#cfc5b2',2);R(c,p[0]-10,p[1]-40,20,12,'#bdb3a0',3);E(c,p[0],p[1]-44,9,4,'#a9a08d');R(c,p[0]-4,p[1]-37,8,6,'#f1c36b',2);}
const TREE_W=[132,140,128,138,146,134,130,142,136];
/** One wish tree: the town's banyan painting with the newest ribbons on its branches. */
function wishTree(c,img,t,x,y,i,o){
  const p=project(x,y),w=TREE_W[i%TREE_W.length],flip=i%2===1;
  shadow(c,x,y,w*.42,w*.16,.22);
  if(loaded(img)){const h=w*img.naturalHeight/img.naturalWidth;c.save();c.translate(p[0],p[1]);if(flip)c.scale(-1,1);c.drawImage(img,-w/2,-h*.93,w,h);c.restore();}
  else{R(c,p[0]-7,p[1]-70,14,70,'#7a5638',4);E(c,p[0],p[1]-100,62,46,'#6a9d58');}
  if(o.near===t.id){c.save();c.globalAlpha=.9;c.strokeStyle='#f6d98a';c.lineWidth=3;c.beginPath();c.ellipse(p[0],p[1],w*.44,w*.17,0,0,Math.PI*2);c.stroke();c.restore();}
  // a red cord round the trunk, then the newest wishes' colours hanging from the canopy (more wishes, more ribbons)
  E(c,p[0],p[1]-w*.3,w*.1,w*.035,'#c8402f');
  const ribs=(t.ribbons||[]).slice(0,16);
  ribs.forEach((col,k)=>{const u=((k*.618+i*.13)%1),v=((k*.382+i*.29)%1),rx=p[0]+(u-.5)*w*.74,ry=p[1]-w*.92+v*w*.42+Math.abs(u-.5)*w*.2,sw=o.reduced?0:Math.sin(o.t*1.6+k+i)*1.6;
    L(c,rx,ry-7,rx+sw*.4,ry,'#f3d590',1.2);c.save();c.translate(rx+sw,ry);c.rotate(sw*.03);R(c,-3.5,0,7,15,RIBBON[col]||RIBBON.do,1.5);R(c,-3.5,11,7,4,'#00000022',1);c.restore();});
}
/** The grove's sign by the path: its board (scene px rect at label scale `ls`; the name boards keep off it). Given the
 * `view` [x0,y0,x1,y1], a board the screen's edge would cut slides along to stay whole (its post stays under it), and
 * there is none (null) while its post is out of sight. */
export function signRect(ls=1,view=null){
  const p=at(11.3,11.6),k=Math.min(1.2,ls||1),r={x:p[0]-70*k,y:p[1]-55-17*k,w:140*k,h:34*k};
  if(!view)return r;
  if(p[0]<view[0]||p[0]>view[2])return null;
  r.x=Math.max(view[0],Math.min(r.x,view[2]-r.w));return r;
}
/** The grove's sign by the path (drawn with the labels, before the tree boards), its board at `r` (signRect). */
export function groveSign(c,o,r=signRect(o.ls)){
  if(!r)return;
  const p=at(11.3,11.6),ls=Math.min(1.2,o.ls||1);R(c,p[0]-2,p[1]-38,4,38,'#6a4a2f',2);c.save();c.translate(r.x+r.w/2,r.y+r.h/2);c.scale(ls,ls);
  R(c,-70,-17,140,34,'#8a2f22',8,'#e8bf62',2);T(c,'🌳 VƯỜN ƯỚC NGUYỆN',0,0,fit(c,'🌳 VƯỜN ƯỚC NGUYỆN',126,12,800),'#f6d98a',800);c.restore();
}
/** Nhà trai's sign (scene px rect): a board keeps off it too. */
export const stoveSignRect=()=>{const s=at(17.2,15.4);return {x:s[0]-66,y:s[1]-80,w:132,h:34};};
const boardLabel=t=>`${t.emoji||''} ${t.name||''}`.trim();
/** What a tree's board counts: its wishes and its old shared lời chúc. */
const boardCount=t=>String((t.count|0)+(t.old|0));
/** A tree's name board where it sits before layout: centred just under the tree's foot (scene px rect, label scale ls). */
export function boardRect(c,t,i,ls=1){
  const [x,y]=GROVE[i],q=project(x,y);
  c.save();c.font='800 13px "Trebuchet MS", sans-serif';const tw=c.measureText(boardLabel(t)).width;c.font='800 11px "Trebuchet MS", sans-serif';const nw=Math.max(18,c.measureText(boardCount(t)).width+10);c.restore();
  const w=(tw+nw+22)*ls,h=24*ls;return {x:q[0]-w/2,y:q[1]+8,w,h};
}
/** The part of a wish tree's painting on the ground and in the air (scene px rect): is the tree in sight at all? */
export function treeRect(i){const [x,y]=GROVE[i],q=project(x,y),w=TREE_W[i%TREE_W.length];return {x:q[0]-w*.37,y:q[1]-w*.95,w:w*.74,h:w*.95};}
const cross=(a,b)=>[Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x),Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y)];
const clash=(a,b,gap)=>{const [w,h]=cross(a,b);return w>-gap&&h>-gap?Math.max(0,w+gap)*Math.max(0,h+gap):0;};
/** The name boards on a narrow screen (owner 15/10: "ở mép trái màn hình hẹp, vài nhãn tên cây bị khuất một phần"):
 * each `boards` rect (moved in place, in order) goes to the place nearest its own (just under its tree) that is wholly
 * inside `view` [x0,y0,x1,y1] (scene px, already inset) and on nothing: not on a `fixed` rect (the grove's sign, the
 * badges, the hint) nor on a board placed before it, `gap` apart. Small moves first, sideways ones cost less (a board
 * moved along stays under its tree). Pure. Returns how many boards found no clear place (they take the least crowded). */
export function layoutBoards(boards,fixed,view,gap=2){
  const [x0,y0,x1,y1]=view,placed=[];let stuck=0;
  const clamp=r=>({x:Math.max(x0,Math.min(r.x,x1-r.w)),y:Math.max(y0,Math.min(r.y,y1-r.h)),w:r.w,h:r.h});
  for(const r of boards){
    const home=clamp(r),steps=[];
    for(let j=-12;j<=12;j++)for(let i=-8;i<=8;i++)steps.push([i*r.w/8,j*r.h/2]);
    steps.sort((a,b)=>Math.hypot(a[0]*.55,a[1])-Math.hypot(b[0]*.55,b[1]));
    let best=null,least=Infinity;
    for(const [dx,dy] of steps){
      const q=clamp({x:home.x+dx,y:home.y+dy,w:r.w,h:r.h});
      let hit=0;for(const f of fixed)hit+=clash(q,f,gap);for(const o of placed)hit+=clash(q,o,gap);
      if(!hit){best=q;least=0;break;}
      if(hit<least){least=hit;best=q;}
    }
    if(least)stuck++;
    r.x=best.x;r.y=best.y;placed.push(r);
  }
  return stuck;
}
/** The name board of a wish tree at `r` (boardRect, maybe moved by layoutBoards), drawn after everything: a label is
 * never hidden by the tree in front. */
export function treeBoard(c,t,i,o,r=null){
  const ls=o.ls||1,near=o.near===t.id,label=boardLabel(t),n=boardCount(t);
  r=r||boardRect(c,t,i,ls);
  c.save();c.translate(r.x+r.w/2,r.y);c.scale(ls,ls);   // labels keep a readable size on a phone (o.ls)
  c.font='800 13px "Trebuchet MS", sans-serif';const tw=c.measureText(label).width;c.font='800 11px "Trebuchet MS", sans-serif';const nw=Math.max(18,c.measureText(n).width+10);
  const bw=tw+nw+22,b=[-bw/2,0];
  c.save();c.globalAlpha=.22;R(c,b[0]+1.5,b[1]+2.5,bw,24,'#3a2a1a',12);c.restore();
  R(c,b[0],b[1],bw,24,near?'#8a2f22':'#fff7e6',12,near?'#f1cf76':'#c9a36a',1.5);
  T(c,label,b[0]+8,b[1]+12.5,13,near?'#fff3cf':'#6b3b22',800,'left');
  R(c,b[0]+bw-nw-4,b[1]+4,nw,16,near?'#f1cf76':'#f0dfc0',8);T(c,n,b[0]+bw-4-nw/2,b[1]+12.5,11,near?'#6b2a1a':'#7a5638',800);
  c.restore();
}
/** [[depth, draw]] of everything standing; the caller adds the people, sorts, then draws the labels (treeBoard). */
export function props(c,o){
  const im=o.images||{},out=[],d=(x,y)=>project(x,y)[1];
  out.push([d(7.1,8.1)-40,()=>hall(c,im.hall,o)]);
  out.push([d(14.0,2.6),()=>bellTower(c,o)]);
  out.push([d(10.3,1.7),()=>brooms(c)]);
  out.push([d(7.7,.9),()=>notice(c)]);
  out.push([d(11.2,5.1),()=>burner(c,o)]);
  out.push([d(13.6,7.0),()=>pond(c,o)]);
  out.push([d(13.0,9.6),()=>bench(c)]);
  out.push([d(17.4,13.4),()=>stove(c,o)]);out.push([d(14.8,15.3),()=>table(c,o)]);
  out.push([d(17.6,6.0),()=>gate(c)]);
  out.push([d(16.8,1.2),()=>veg(c,im.veg,'banyan',16.8,1.2,170,true)]);
  for(const [k,x,y,w,f] of [['bamboo',.6,.6,120],['bamboo',17.5,6.9,96,1],['flowers',11.0,.6,74],['shrubs',3.6,17.6,74],['bamboo',.5,17.4,112],['flowers',17.0,17.2,84,1],['rocks',12.4,17.4,74],['flowers',12.0,10.6,58,1],['shrubs',.6,11.6,60]])
    out.push([d(x,y),()=>veg(c,im.veg,k,x,y,w,!!f)]);
  for(const [x,y] of [[9.0,3.2],[9.0,6.0],[13.0,3.3],[13.2,5.9],[11.9,8.4]])out.push([d(x,y),()=>lantern(c,x,y)]);
  (o.trees||[]).slice(0,GROVE.length).forEach((t,i)=>{const [x,y]=GROVE[i];out.push([d(x,y),()=>wishTree(c,im.tree,t,x,y,i,o)]);});
  return out;
}
/** An NPC (the frontal painter of the pagoda's people) standing at world (q.x, q.y). */
export function npc(c,q,s,t){const p=project(q.x,q.y);person(c,p[0],p[1],s,q.who,{t,pose:q.sit?'sit':''});}
export {T,R,E,L,fit};
