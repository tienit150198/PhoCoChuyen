/** Back rooms: one builder for the interiors of the storefront careers (the tea bar's kitchen, the minimart's
 * stock room, the salon's wash room…), on the kit of scenes/interior.js and the mechanism of scenes/areas.js.
 *
 * room(spec) → an area {id, name, icon, plan, room, props, looks, people}. spec:
 *   id, name, icon        the area
 *   back                  the main area's id: a door back there (go:<back>) at backU (default .06) on the wall
 *   doors                 more doors [{to, u, color}]
 *   theme                 {wall, wallLow, floor, floor2, tile, rim, trim, ink, door}
 *   sign                  the plate at the top of the wall
 *   win                   a window {u0, u1, top, bottom, view(c,x,y,wd,ht)} (time of day and weather show through)
 *   items                 the furniture, [{k, u, v, w, d, h, spot, label, fill, col, …}]: kind, centre u across, front
 *                         edge v down the floor, width w and depth d as fractions, height h in px; `spot` makes it a
 *                         hotspot ('warehouse', 'workbench', 'look:key'…) named by `label`. Items against the wall
 *                         (v ≤ .12) are painted once into the cached room; the others stand on the floor.
 *   looks                 {key: w=>line} for the look: spots
 *   clock, calendar       [u, h]: a wall clock on the workplace's time, the tear-off calendar on today's day
 *   chat                  lines a co-worker calls through the door now and then; walker: someone crosses with a box
 *   wall(c,g,w), fx(c,g,w,out)   extra painting in the room / extra props
 *   spots(g), labels      more hotspots ({key: spotAt(…)}) and their names; blocks(g) more footprints
 *   outdoor, walker:false  lamp posts outside; no co-worker crossing
 *   home                  [u, v] where the player stands (default the middle front)
 * Nothing here reads or writes anything but the career's public view. */
import {R,E,L,T,P,fit,heart,bloom,plantAt} from './kit.js';
import {geo,both,box,spotAt,shell,doorway,windowPane,weatherOf,hash,beat,bubble,passer,plate} from './interior.js';

const WOOD='#c9a27e',WOOD_D='#a57f5f',STEEL='#dfe5ea',STEEL_D='#9aa6b0',GLASS='#cfe8f2',INK='#4f4038';
const ended=t=>['completed','cancelled','referred'].includes(t.status);
/** The task in hand, or null. */
export const taskOf=w=>{const c=w.c;return c?.tasks?.find(t=>t.id===c.active_task&&!ended(t))||null;};
/** Today's sky outside the back window: the career's own weather when it has one, else a quiet day-to-day
 * variety (a rainy or misty morning now and then) that changes nothing in the work. */
export function skyWx(w){
  const own=weatherOf(w);if(own!=='clear'||w.c?.data?.weather)return own;
  const n=hash((w.c?.day||1)*7.7+String(w.career).length);return n<.16?'rain':n<.24?'fog':'clear';
}
const rot=(list,n)=>list.length?list.map((_,i)=>list[(i+n)%list.length]):list;

/* ------------------------------------------------------------ furniture */
/** Each kind draws at (x = centre, y = front edge) with width W, depth D (px) and height H (px, k applied). */
const KINDS={
  shelf(c,g,w,it,x,y,W,D,H){const col=it.col||WOOD,rows=it.rows||4,day=w.c?.day||0,fill=rot(it.fill||['📦'],day%3);
    R(c,x-W/2,y-H,W,H,col,8*g.k,'#00000022',1.5);R(c,x-W/2+6,y-H+6,W-12,H-12,it.back||'#00000014',5);
    const per=Math.max(2,Math.floor((W-16)/(32*g.k))),rh=(H-14)/rows,size=Math.min(rh*.62,24*g.k);
    for(let r=0;r<rows;r++){const by=y-H+8+rh*(r+1);R(c,x-W/2+4,by-4,W-8,6,it.board||WOOD_D,2);
      for(let j=0;j<per;j++){const f=fill[(r*per+j)%fill.length],cx=x-W/2+12+(W-24)*(j+.5)/per;
        if(f.startsWith('#')){const bw=(W-24)/per*.84,bh=rh*.66;R(c,cx-bw/2,by-4-bh,bw,bh,f,3,'#00000022',1);L(c,cx,by-4-bh,cx,by-4-bh*.6,'#ffffff66',2);}
        else T(c,f,cx,by-4-size*.55,size);}}},
  fridge(c,g,w,it,x,y,W,D,H){const fill=it.fill||['🥛','🧀','🥚'];
    R(c,x-W/2,y-H,W,H,it.col||'#eef2f5',10*g.k,STEEL_D,2);R(c,x-W/2,y-H,W,18*g.k,it.top||'#7fb7c9',8*g.k);
    const doors=W>130*g.k?2:1,dw=(W-14)/doors;
    for(let d=0;d<doors;d++){const dx=x-W/2+7+d*dw;R(c,dx,y-H+24*g.k,dw-4,H-34*g.k,GLASS,6,'#ffffffaa',1.5);
      for(let r=0;r<4;r++){const ry=y-H+24*g.k+(H-34*g.k)*(r+.6)/4;L(c,dx+4,ry+10*g.k,dx+dw-8,ry+10*g.k,'#a9c9d6',2);
        for(let j=0;j<2;j++)T(c,fill[(d*8+r*2+j)%fill.length],dx+(dw-4)*(j+.5)/2,ry,Math.min(20*g.k,dw*.3));}
      L(c,dx+dw-10,y-H*.62,dx+dw-10,y-H*.42,STEEL_D,3);}
    if(it.tag)T(c,it.tag,x,y-H+9*g.k,fit(c,it.tag,W-12,g.port?12:10),'#fff',800);},
  counter(c,g,w,it,x,y,W,D,H){const top=it.top||'#efe6da',body=it.col||WOOD,fill=it.fill||[];
    R(c,x-W/2,y-H+10,W,H-10,body,6,'#00000022',1.5);for(let i=1;i<3;i++)L(c,x-W/2+W*i/3,y-H+18,x-W/2+W*i/3,y-6,'#00000022',2);
    R(c,x-W/2-6,y-H-D*.5,W+12,D*.5+12,top,6,'#00000022',1.5);
    const sx=it.sink!=null?x-W/2+W*it.sink:null;
    if(sx!=null){E(c,sx,y-H-D*.2,W*.11,D*.16,'#b9c6cf');E(c,sx,y-H-D*.2+2,W*.09,D*.11,'#93a4b0');L(c,sx+W*.08,y-H-D*.2,sx+W*.08,y-H-D*.2-30*g.k,STEEL_D,4);L(c,sx+W*.08,y-H-D*.2-30*g.k,sx+W*.04,y-H-D*.2-30*g.k,STEEL_D,4);}
    (it.pots||[]).forEach((u,i)=>{const px=x-W/2+W*u;E(c,px,y-H-D*.16,22*g.k,7*g.k,'#3b3f45');R(c,px-20*g.k,y-H-D*.2-34*g.k,40*g.k,34*g.k,(it.potCol||['#c0c7cd','#d9a066','#c0c7cd'])[i%3],6*g.k,'#00000033',1.5);E(c,px,y-H-D*.2-34*g.k,20*g.k,5*g.k,it.brew?.[i%it.brew.length]||'#6a4a3a');});
    fill.forEach((f,i)=>{const n=fill.length,u=(i+.5)/n,fx=x-W/2+W*u;if(sx!=null&&Math.abs(fx-sx)<W*.12||(it.pots||[]).some(p=>Math.abs(x-W/2+W*p-fx)<W*.09))return;T(c,f,fx,y-H-D*.25-12*g.k,22*g.k);});},
  table(c,g,w,it,x,y,W,D,H){const fill=it.fill||[];E(c,x,y+4,W/2+8,8,'#00000020');
    R(c,x-W/2+10,y-H,10,H,WOOD_D,3);R(c,x+W/2-20,y-H,10,H,WOOD_D,3);
    R(c,x-W/2,y-H-D,W,D+10,it.col||'#e9d8c2',8,'#c4ad8e',2);if(it.cloth)R(c,x-W*.3,y-H-D+4,W*.6,D,it.cloth,5);
    fill.forEach((f,i)=>{const u=(i+.5)/fill.length;T(c,f,x-W/2+W*u,y-H-D*.5-6*g.k,24*g.k);});},
  oven(c,g,w,it,x,y,W,D,H){R(c,x-W/2,y-H,W,H,'#b8644a',14*g.k,'#8f4a36',2);for(let r=0;r<5;r++)for(let j=0;j<6;j++)if((r+j)%2)R(c,x-W/2+6+j*(W-12)/6,y-H+8+r*(H*.5)/5,(W-12)/6-3,H*.5/5-3,'#a9583f',2);
    for(let d=0;d<2;d++){const dy=y-H*.46+d*H*.22;R(c,x-W*.38,dy,W*.76,H*.16,'#2f2a28',6);R(c,x-W*.34,dy+4,W*.68,H*.16-8,'#f2a35a',4);for(let j=0;j<3;j++)T(c,it.fill?.[(j+d)%it.fill.length]||'🥖',x-W*.22+j*W*.22,dy+H*.08,16*g.k);}
    R(c,x-W/2-4,y-H-10,W+8,14,'#8f4a36',5);},
  rack(c,g,w,it,x,y,W,D,H){const cols=it.fill||['#e3a7b8','#9cc3d5','#f0cf8a','#b8d39c','#c4b2e0'];E(c,x,y+3,W/2,6,'#00000018');
    L(c,x-W/2,y,x-W/2,y-H,STEEL_D,5);L(c,x+W/2,y,x+W/2,y-H,STEEL_D,5);L(c,x-W/2,y-H+6,x+W/2,y-H+6,STEEL_D,5);
    const n=Math.max(3,Math.floor(W/(30*g.k)));for(let i=0;i<n;i++){const hx=x-W/2+W*(i+.5)/n,col=cols[i%cols.length];L(c,hx,y-H+6,hx,y-H+16,STEEL_D,2);
      P(c,[[hx-14*g.k,y-H+16],[hx+14*g.k,y-H+16],[hx+12*g.k,y-H+H*.62],[hx-12*g.k,y-H+H*.62]],col);L(c,hx-6*g.k,y-H+20,hx+6*g.k,y-H+20,'#ffffff77',2);}},
  boxes(c,g,w,it,x,y,W,D,H){const labels=it.fill||['S','M','L'],cols=['#d9b38c','#cfa57d','#e2c39d'];R(c,x-W/2,y-10,W,10,'#a5855e',2);
    const per=Math.max(2,Math.floor(W/(54*g.k))),rows=Math.max(1,Math.round(H/(46*g.k))),bw=W/per,bh=(H-10)/rows;
    for(let r=0;r<rows;r++)for(let j=0;j<per-(r%2&&per>2?1:0);j++){const bx=x-W/2+j*bw+(r%2?bw/2:0),by=y-10-(r+1)*bh;R(c,bx+2,by+2,bw-4,bh-3,cols[(r+j)%3],3,'#8f714f',1.2);L(c,bx+bw/2,by+2,bx+bw/2,by+bh*.35,'#e8d6b5',4);
      const s=labels[(r*per+j)%labels.length];T(c,s,bx+bw/2,by+bh*.62,fit(c,s,bw-10,15*g.k),INK,800);}},
  sacks(c,g,w,it,x,y,W,D,H){const labels=it.fill||['GẠO'],n=Math.max(2,Math.floor(W/(46*g.k)));
    for(let i=0;i<n;i++){const sx=x-W/2+W*(i+.5)/n,hh=H*(.8+.2*hash(i+3));E(c,sx,y-hh*.45,W/n*.48,hh*.5,'#efe3c9');E(c,sx,y-hh*.9,W/n*.3,8*g.k,'#e1d1b0');T(c,labels[i%labels.length],sx,y-hh*.45,fit(c,labels[i%labels.length],W/n*.8,13*g.k),'#8a6a4a',800);}},
  desk(c,g,w,it,x,y,W,D,H){KINDS.table(c,g,w,{...it,fill:[]},x,y,W,D,H);const ty=y-H-D*.5;
    R(c,x-W*.36,ty-12*g.k,W*.3,18*g.k,it.book||'#c4668b',3);L(c,x-W*.21,ty-12*g.k,x-W*.21,ty+6*g.k,'#ffffff88',1.5);
    L(c,x+W*.25,ty,x+W*.25,ty-40*g.k,STEEL_D,3);P(c,[[x+W*.16,ty-40*g.k],[x+W*.34,ty-40*g.k],[x+W*.3,ty-54*g.k],[x+W*.2,ty-54*g.k]],it.lamp||'#f2c14e');
    (it.fill||[]).forEach((f,i)=>T(c,f,x+W*(.02+i*.1),ty-8*g.k,18*g.k));},
  curtain(c,g,w,it,x,y,W,D,H){const col=it.col||'#c4b2e0';R(c,x-W/2-6,y-H-10,W+12,12,STEEL_D,4);
    for(let i=0;i<5;i++){const cx=x-W/2+W*(i+.5)/5;R(c,cx-W/10,y-H,W/5+1,H-16*g.k,i%2?col:shade(col),4);}
    if(it.tag)plate(c,g,x,y-H-26*g.k,it.tag,{bg:it.tagBg||'#6f4a58',size:g.port?12:10,pad:8});},
  tub(c,g,w,it,x,y,W,D,H){R(c,x-W/2,y-H,W,H,'#f4f7fa',18*g.k,STEEL_D,2);E(c,x,y-H+6,W/2-8,10*g.k,'#9fd2ee');
    T(c,it.fill?.[(w.c?.day||0)%(it.fill?.length||1)]||'🐶',x,y-H-6*g.k,30*g.k);for(let i=0;i<5;i++)E(c,x-W*.35+i*W*.17,y-H+2,10*g.k,8*g.k,'#ffffffee');
    L(c,x+W/2-14,y-H,x+W/2-14,y-H-46*g.k,STEEL_D,4);L(c,x+W/2-14,y-H-46*g.k,x+W/2-34,y-H-46*g.k,STEEL_D,4);R(c,x-W/2+8,y-8,10,10,STEEL_D,2);R(c,x+W/2-18,y-8,10,10,STEEL_D,2);},
  washchair(c,g,w,it,x,y,W,D,H){R(c,x-W/2,y-H*.45,W,H*.45,it.col||'#3e4752',10*g.k);R(c,x-W*.44,y-H*.62,W*.88,H*.2,'#56606c',10*g.k);
    E(c,x,y-H*.86,W*.34,H*.14,'#f4f7fa');E(c,x,y-H*.84,W*.26,H*.09,'#c9dbe6');L(c,x+W*.2,y-H*.94,x+W*.2,y-H*1.08,STEEL_D,3);L(c,x+W*.2,y-H*1.08,x+W*.1,y-H*1.08,STEEL_D,3);
    R(c,x-W*.32,y-H*.66,W*.64,10*g.k,'#f4ece0',4);},
  cages(c,g,w,it,x,y,W,D,H){const pets=it.fill||['🐶','🐱','🐰','🐹'],cols=Math.max(2,Math.round(W/(70*g.k))),rows=2,cw=W/cols,ch=H/rows,day=w.c?.day||0;
    for(let r=0;r<rows;r++)for(let j=0;j<cols;j++){const cx=x-W/2+j*cw,cy=y-H+r*ch,n=r*cols+j,pet=hash(n+day*3)>.25?pets[(n+day)%pets.length]:'';
      R(c,cx+3,cy+3,cw-6,ch-6,'#f6efe4',6,'#b9a48f',2);if(pet)T(c,pet,cx+cw/2,cy+ch*.58,Math.min(ch*.5,30*g.k));
      for(let b=1;b<4;b++)L(c,cx+3+(cw-6)*b/4,cy+6,cx+3+(cw-6)*b/4,cy+ch-6,'#b9a48faa',2);
      R(c,cx+cw*.3,cy+ch-14,cw*.4,8,'#e3b04b',3);}},
  cart(c,g,w,it,x,y,W,D,H){const cols=it.fill||['#ffffff','#bfe7d8','#fde4ec'];E(c,x,y+3,W/2,6,'#00000018');R(c,x-W/2,y-H,W,H-10,it.col||'#dfe5ea',6,STEEL_D,1.5);
    for(let s=0;s<3;s++)for(let j=0;j<3;j++)R(c,x-W/2+8+j*(W-16)/3,y-H+6+s*(H-22)/3,(W-16)/3-4,(H-22)/3-4,cols[(s+j)%cols.length],3,'#00000018',1);
    E(c,x-W/2+8,y-4,5,5,'#3b3f45');E(c,x+W/2-8,y-4,5,5,'#3b3f45');L(c,x+W/2,y-H+6,x+W/2+14,y-H-8,STEEL_D,3);},
  mirror(c,g,w,it,x,y,W,D,H){R(c,x-W/2,y-H,W,H,it.col||'#e6d3b3',W/2,'#c4ad8e',2);R(c,x-W/2+8,y-H+8,W-16,H-16,'#dfeef5',W/2-8);L(c,x-W*.2,y-H*.75,x+W*.05,y-H*.92,'#ffffffaa',4);L(c,x-W*.22,y-H*.6,x+W*.15,y-H*.86,'#ffffff77',3);},
  belt(c,g,w,it,x,y,W,D,H){R(c,x-W/2,y-H,W,H,'#59626c',6);R(c,x-W/2,y-H-D*.6,W,D*.6,'#3b4048',4);for(let i=0;i<10;i++)E(c,x-W/2+W*(i+.5)/10,y-H-D*.3,4,4,'#7d8790');
    L(c,x-W/2+10,y-H,x-W/2+10,y,'#3b4048',5);L(c,x+W/2-10,y-H,x+W/2-10,y,'#3b4048',5);},
  buckets(c,g,w,it,x,y,W,D,H){const fl=rot(it.fill||['🌹','🌷','🌻','💐','🌼'],(w.c?.day||0)%5),n=Math.max(2,Math.floor(W/(46*g.k)));
    for(let i=0;i<n;i++){const bx=x-W/2+W*(i+.5)/n,bw=W/n*.7;for(let j=0;j<3;j++)T(c,fl[(i+j)%fl.length],bx-bw*.25+j*bw*.25,y-H-10*g.k-(j%2)*10*g.k,20*g.k);
      P(c,[[bx-bw/2,y-H],[bx+bw/2,y-H],[bx+bw*.4,y],[bx-bw*.4,y]],'#b9c4cc');L(c,bx-bw/2,y-H+6,bx+bw/2,y-H+6,'#d9e1e6',3);}},
  basket(c,g,w,it,x,y,W,D,H){R(c,x-W/2,y-H,W,H,'#d8b48a',10*g.k,'#a57f5f',2);for(let i=1;i<4;i++)L(c,x-W/2+4,y-H+H*i/4,x+W/2-4,y-H+H*i/4,'#b8946a',2);
    (it.fill||['#ffffff','#bfe7d8']).forEach((col,i)=>E(c,x-W*.2+i*W*.25,y-H,W*.22,10*g.k,col));},
  plant(c,g,w,it,x,y,W,D,H){plantAt(c,x,y,(it.s||1)*g.k);},
  stairs(c,g,w,it,x,y,W,D,H){const n=7;for(let i=0;i<n;i++){const sx=x-W/2+W*i/n;R(c,sx,y-H*(i+1)/n,W/n+1,H*(i+1)/n,i%2?WOOD:'#d4ae88',0);}
    L(c,x-W/2,y-H*.3,x+W/2,y-H*1.2,WOOD_D,5);for(let i=0;i<n;i+=2){const sx=x-W/2+W*i/n;L(c,sx,y-H*(i+1)/n,sx,y-H*(i+1)/n-H*.3,WOOD_D,3);}},
  mailboxes(c,g,w,it,x,y,W,D,H){R(c,x-W/2,y-H,W,H,'#9aa6b0',6,'#6d7880',2);const cols=4,rows=3;
    for(let r=0;r<rows;r++)for(let j=0;j<cols;j++){const bx=x-W/2+6+j*(W-12)/cols,by=y-H+6+r*(H-12)/rows;R(c,bx,by,(W-12)/cols-4,(H-12)/rows-4,'#dfe5ea',3);
      T(c,String((r+1)*100+j+1),bx+(W-12)/cols/2-2,by+10*g.k,g.port?11:9,INK,800);if(hash(r*4+j+(w.c?.day||0))>.7)R(c,bx+4,by+(H-12)/rows-14,(W-12)/cols-12,5,'#f6efe4',1);}},
};
function shade(col){const n=parseInt(col.slice(1,7),16),f=v=>Math.max(0,Math.round(v*.86)).toString(16).padStart(2,'0');return '#'+f(n>>16&255)+f(n>>8&255)+f(n&255);}

/** Little motions over the furniture (drawn every frame, nothing when reduced motion is on). */
function itemFx(c,g,w,it,x,y,W,D,H){
  if(w.reduced)return;const t=w.time,k=g.k;
  if(it.pots)it.pots.forEach((u,i)=>{const px=x-W/2+W*u;for(let s=0;s<2;s++){const a=((t*.6+i*.37+s*.5)%1);c.globalAlpha=.45*(1-a);E(c,px+Math.sin(t*2+i+s)*6,y-H-D*.2-40*k-a*60*k,(8+a*10)*k,(6+a*8)*k,'#ffffff');}c.globalAlpha=1;});
  if(it.sink!=null){const sx=x-W/2+W*it.sink+W*.04,a=(t*1.4)%1;E(c,sx,y-H-D*.2-28*k+a*24*k,2.2,3,'#9fd2ee');}
  if(it.k==='oven'){c.globalAlpha=.18+.1*Math.sin(t*3);E(c,x,y-H*.3,W*.5,H*.3,'#ffb35a');c.globalAlpha=1;}
  if(it.k==='tub')for(let i=0;i<3;i++){const a=(t*.5+i*.33)%1;c.globalAlpha=.8*(1-a);E(c,x-W*.25+i*W*.25+Math.sin(t*2+i)*6,y-H-a*70*k,(5+a*5)*k,(5+a*5)*k,'#e8f6fd');}
  if(it.k==='tub')c.globalAlpha=1;
  if(it.k==='belt'){const step=W/4,off=(t*40)%step;for(let i=-1;i<4;i++){const bx=x-W/2+off+i*step;if(bx<x-W/2||bx>x+W/2-30*k)continue;R(c,bx,y-H-D*.3-26*k,30*k,24*k,['#d9b38c','#e2c39d','#cfa57d'][(i+9)%3],3,'#8f714f',1);L(c,bx+15*k,y-H-D*.3-26*k,bx+15*k,y-H-D*.3-14*k,'#e8d6b5',3);}}
  if(it.k==='cages'){const b=beat(w,5,it.u*10),cols=Math.max(2,Math.round(W/(70*k))),j=b.n%cols;if(b.k<.5){c.globalAlpha=1-b.k*2;heart(c,x-W/2+(j+.5)*W/cols,y-H-8*k-b.k*30*k,.35*k,'#e88aa4');c.globalAlpha=1;}}
  if(it.k==='curtain'){const b=beat(w,11,it.u*7);if(b.n%2&&b.k<.6){R(c,x-16*k,y-18*k,12*k,10*k,'#5a4438',3);R(c,x+4*k,y-18*k,12*k,10*k,'#5a4438',3);}}
}

/* ------------------------------------------------------------ the builder */
const isWall=it=>it.v<=.12&&!it.floor;
function geom(g,it){const W=it.w*g.f.w,D=(it.d??(isWall(it)?.08:.12))*(g.bot-g.base),H=(it.h??80)*g.k;return {x:g.X(it.u),y:g.Y(it.v),W,D,H};}
function draw(c,g,w,it){const {x,y,W,D,H}=geom(g,it);if(!isWall(it))E(c,x,y+3,W/2+6,7*g.k,'#00000018');KINDS[it.k]?.(c,g,w,it,x,y,W,D,H);}
/** A wall clock on the workplace's own time. */
function clock(c,g,w,u,h){const x=g.X(u),y=g.H(h),r=24*g.k,m=Number(w.c?.day_clock?.minute??540);
  E(c,x,y,r+4,r+4,'#8b7355');E(c,x,y,r,r,'#fffaf0');for(let i=0;i<12;i++){const a=i*Math.PI/6;L(c,x+Math.cos(a)*r*.8,y+Math.sin(a)*r*.8,x+Math.cos(a)*r*.9,y+Math.sin(a)*r*.9,'#8b7355',2);}
  const ha=((m/60)%12)/12*Math.PI*2-Math.PI/2,ma=(m%60)/60*Math.PI*2-Math.PI/2;L(c,x,y,x+Math.cos(ha)*r*.5,y+Math.sin(ha)*r*.5,INK,3.5);L(c,x,y,x+Math.cos(ma)*r*.75,y+Math.sin(ma)*r*.75,INK,2.2);E(c,x,y,3,3,'#c96f5a');}
/** The tear-off calendar on today's day. */
function calendar(c,g,w,u,h){const x=g.X(u),y=g.H(h),k=g.k,d=w.c?.day||1;R(c,x-26*k,y-30*k,52*k,62*k,'#fffaf0',5,'#c9b49a',1.5);R(c,x-26*k,y-30*k,52*k,16*k,'#d9534f',5);
  T(c,'NGÀY',x,y-22*k,g.port?10:9,'#fff',800);T(c,String(d),x,y+8*k,26*k,INK,800);}
/** An umbrella drying by the door on a wet day, a puddle under it. */
function umbrella(c,g,u){const x=g.X(u)+52*g.k,y=g.base+4,k=g.k;E(c,x,y+4,22*k,5*k,'#9fd2ee88');L(c,x,y,x+4*k,y-56*k,'#6b6f76',2.5);P(c,[[x+4*k,y-56*k],[x-10*k,y-14*k],[x+18*k,y-14*k]],'#e3a7b8');}

export function room(spec){
  const items=spec.items||[],th=spec.theme||{},backU=spec.backU??.06,doors=[{to:spec.back,u:backU,color:th.door},...(spec.doors||[])];
  const plan=both(g=>{
    const spots={},labels={...(spec.labels||{})},blocks=[...(spec.blocks?.(g)||[])];
    for(const it of items){const {x,y,H}=geom(g,it),d=it.d??(isWall(it)?.08:.12);
      if(!isWall(it)||it.v>.1)blocks.push(box(g,it.u-it.w/2,Math.max(0,it.v-d),it.u+it.w/2,it.v));
      if(it.spot){const go=it.go||[[it.u,Math.min(.9,it.v+(isWall(it)?.1:.13))]];spots[it.spot]=spotAt(g,[x,y-H*.55],it.range||Math.min(80,Math.max(45,it.w*g.f.w*.35)),...go);if(it.label)labels[it.spot]=it.label;}}
    for(const d of doors)spots['go:'+d.to]=spotAt(g,[g.X(d.u),g.H(.62)],50,[d.u,.2]);
    Object.assign(spots,spec.spots?.(g)||{});
    const [hu,hv]=spec.home||[.5,.78];
    return {home:[g.X(hu),g.Y(hv)],blocks,labels,spots,customers:(spec.customers||[]).map(([u,v])=>[g.X(u),g.Y(v)]),cat:spec.cat?[g.X(spec.cat[0]),g.Y(spec.cat[1])]:null};
  });
  const roomFn=(w,p)=>{shell(w,{wall:th.wall||'#f4ece0',wallLow:th.wallLow,floor:th.floor||'#d9c7ae',floor2:th.floor2,tile:th.tile||0,rim:th.rim||'#b9a48f',trim:th.trim},(c,g)=>{
    const f=g.f;R(c,f.x,f.y,f.w,g.H(.05)-f.y,'#00000010',0);
    if(spec.win){const v=spec.win,x0=g.X(v.u0),x1=g.X(v.u1),y0=g.H(v.top??.16),y1=g.H(v.bottom??.66);windowPane(c,w,x0,y0,x1-x0,y1-y0,{frame:v.frame||'#efe4d2',bars:v.bars??1,view:v.view?v.view(w):null,wx:skyWx(w)});}
    for(const d of doors)doorway(c,g,d.u,{color:d.color||th.door||'#8a6e58',glass:d.glass||null});
    if(['rain','storm'].includes(skyWx(w)))umbrella(c,g,backU);
    if(spec.calendar)calendar(c,g,w,...spec.calendar);
    spec.wall?.(c,g,w);
    for(const it of items)if(isWall(it))draw(c,g,w,it);
    if(spec.sign)plate(c,g,g.X(.5),g.H(.085),spec.sign,{bg:th.ink||'#6f4a58'});
  });};
  const propsFn=(w,p)=>{const c=w.ctx,g=geo(w.isPortrait()),out=[];
    for(const it of items){const {x,y,W,D,H}=geom(g,it);
      if(isWall(it))out.push([g.Y(.1)-1,()=>itemFx(c,g,w,it,x,y,W,D,H)]);
      else out.push([y,()=>{draw(c,g,w,it);itemFx(c,g,w,it,x,y,W,D,H);}]);}
    if(spec.clock)out.push([g.Y(.1)-2,()=>clock(c,g,w,...spec.clock)]);
    // Now and then a co-worker calls through the door, or crosses the room with a box.
    if(spec.chat?.length){const b=beat(w,13,spec.id.length);if(b.on&&b.n%3!==2&&b.k<.4){const d=doors[b.n%doors.length]||doors[0];out.push([g.bot,()=>bubble(c,g,g.X(d.u),g.H(.3),spec.chat[(b.n>>1)%spec.chat.length])]);}}
    if(spec.walker!==false){const b=beat(w,17,spec.id.length+3);if(b.on&&b.n%2===0){const dir=b.n%4?1:-1,x=dir>0?g.f.x-40+(g.f.w+80)*b.k:g.f.x+g.f.w+40-(g.f.w+80)*b.k,y=g.bot-8;
      out.push([g.bot+1,()=>{passer(c,x,y,.95*g.k,b.n,dir,w.time,{bag:false});R(c,x+dir*4*g.k-15*g.k,y-62*g.k,30*g.k,24*g.k,'#d9b38c',3,'#8f714f',1);}]);}}
    spec.fx?.(c,g,w,out);
    return out;};
  return {id:spec.id,name:spec.name,icon:spec.icon,plan,room:roomFn,props:propsFn,looks:spec.looks||{},people:!!spec.customers?.length,outdoor:!!spec.outdoor};
}

/** Where the work is for a shop: the main floor whenever a new task is taken up; otherwise wherever you are. */
export const shopFor=main=>w=>{const t=taskOf(w);return t?{key:'t:'+t.id,area:main}:{key:'idle'};};
export {KINDS};
