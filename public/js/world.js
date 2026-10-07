/** Original, dependency-free Canvas 2.5D world.
 * Isometric tile map + collision-aware pathfinding + animated vector characters.
 * All interactions also have DOM buttons; precise pointing is never required.
 */
import {t as tr} from './v4/i18n.js';
import {encodePhoto} from './v4/photo-encode.js';
const W=1200,H=790,TW=45,TH=24;
const PALETTE={mother_baby:{wall:'#f1e2c8',side:'#e4d3b5',accent:'#8da181',counter:'#a8b695',wood:'#c8aa79'},pharmacy:{wall:'#e1eddf',side:'#c8dccc',accent:'#6e9d90',counter:'#8ab3a3',wood:'#b7bc94'},accounting:{wall:'#ebe4ee',side:'#d5ccdf',accent:'#9292ac',counter:'#a4a2b7',wood:'#b8a78e'},customer_care:{wall:'#e1ebed',side:'#c9dade',accent:'#7e9faa',counter:'#9eb8bf',wood:'#b9ac94'}};
PALETTE.teacher={...PALETTE.accounting};PALETTE.tour_guide={...PALETTE.customer_care};PALETTE.milk_tea={...PALETTE.mother_baby};
const CLOTHES=['#8c9a7e','#aa8d9a','#9eacbd','#c2957e','#82a5a0','#b2a36b'];
function lerp(a,b,t){return a+(b-a)*t;}
const now=()=>globalThis.performance?.now?.()??Date.now();
/* Frame budget (ms between drawn frames). Phones got hot repainting the whole diorama 60–120 times a
 * second, also under sheets and in the background. Now: full rate (≤60 fps) only while something moves or
 * right after a touch; slow ambient life (bobbing, blinking, steam, clouds) at AMBIENT; a quieter IDLE rate
 * after LONG_IDLE ms without any activity; reduced motion or pause draw on change (plus a slow safety
 * refresh); nothing at all while the tab is hidden, the canvas is off screen or a sheet covers it. */
const FULL=1000/60,AMBIENT=100,IDLE=200,STILL=500,LONG_IDLE=20000,TOUCH=1500,SLACK=4;
function rounded(c,x,y,w,h,r=8){c.beginPath();c.roundRect(x,y,w,h,r);}
function rr(c,x,y,w,h,fill,r=8,stroke){rounded(c,x,y,w,h,r);c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=1.4;c.stroke();}}
function ell(c,x,y,rx,ry,fill){c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fillStyle=fill;c.fill();}
function poly(c,points,fill,stroke){c.beginPath();points.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.closePath();c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=1;c.stroke();}}
function line(c,x1,y1,x2,y2,color,width=1){c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.moveTo(x1,y1);c.lineTo(x2,y2);c.stroke();}
function text(c,t,x,y,size=14,fill='#525445',weight=600,align='center'){c.font=`${weight} ${size}px "Avenir Next", "Segoe UI", sans-serif`;c.textAlign=align;c.textBaseline='middle';c.fillStyle=fill;c.fillText(tr(String(t)),x,y);}
function shade(hex,factor){const n=parseInt(hex.replace('#',''),16);const r=Math.max(0,Math.min(255,((n>>16)&255)+factor)),g=Math.max(0,Math.min(255,((n>>8)&255)+factor)),b=Math.max(0,Math.min(255,(n&255)+factor));return `rgb(${r},${g},${b})`;}
export class World {
  constructor(canvas,onInteract){
    this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});this.onInteract=onInteract;
    this.career='mother_baby';this.game=null;this.state=null;this.player={x:NaN,y:NaN,path:[],goal:null,look:1};
    this.hotspots=[];this.hover=null;this.particles=[];this.speech=null;this.time=0;this.last=0;this.paused=false;this.keys=new Set();this.pending=null;this.scale=1;this.offset={x:0,y:0};this.previewCache=new Map();this.ambientPeople=[];this.actionTimer=0;
    this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(canvas);
    canvas.addEventListener('pointermove',e=>{this.poke(true);this.pointerMove(e);});canvas.addEventListener('pointerleave',()=>{this.hover=null;this.poke(true);});
    canvas.addEventListener('pointerdown',e=>{this.poke(true);canvas.focus({preventScroll:true});this.pointerDown(e);});
    canvas.addEventListener('keydown',e=>{this.poke(true);this.keydown(e);});canvas.addEventListener('keyup',e=>{this.keys.delete(e.key.toLowerCase());this.poke(true);});canvas.addEventListener('blur',()=>this.keys.clear());
    this.navDebug=/[?&]navdebug=1\b/.test(location.search);if(this.navDebug)globalThis.__navWorld=this;
    // Frame budget: see frame(). Any tap or key on the page counts as activity; closing a dialog, showing the
    // tab again or scrolling the canvas back into view wakes a stopped loop.
    this.frame=this.frame.bind(this);this.tick=()=>{this.timer=0;this.wake();};
    this.lastDraw=-1e9;this.lastTouch=-1e9;this.lastActive=now();this.dirty=true;this.onScreen=true;
    const doc=globalThis.document;
    this.listeners=[['visibilitychange',()=>this.wake(true)],['close',e=>{if(e.target?.tagName==='DIALOG')this.wake(true);},true],
      ['pointerdown',()=>this.poke(),true],['keydown',()=>this.poke(),true]];
    for(const [type,fn,capture] of this.listeners)doc?.addEventListener?.(type,fn,capture?{capture:true,passive:true}:undefined);
    if(typeof IntersectionObserver==='function'){this.visibleObserver=new IntersectionObserver(entries=>{this.onScreen=entries.at(-1).isIntersecting;this.wake(true);});this.visibleObserver.observe(canvas);}
    this.raf=requestAnimationFrame(this.frame);
  }
  destroy(){cancelAnimationFrame(this.raf);clearTimeout(this.timer);this.resizeObserver.disconnect();this.visibleObserver?.disconnect();
    for(const [type,fn,capture] of this.listeners||[])globalThis.document?.removeEventListener?.(type,fn,capture?{capture:true}:undefined);}
  /* World time: an accessor so the cached room layer (BobaWorld.backdrop) can tell whether a scene's room
   * drawing animates with time (timeRead) or is static. */
  get time(){this.timeRead=true;return this._time||0;}
  set time(v){this._time=v;}
  get navDebug(){return !!this._navDebug;}
  set navDebug(v){this._navDebug=!!v;if(this.listeners)this.wake(true);}
  get paused(){return !!this._paused;}
  set paused(v){v=!!v;if(v!==this._paused){this._paused=v;if(this.listeners)this.wake(true);}}
  /** Something changed that must be shown: draw at the next frame (the loop may be sleeping). */
  wake(dirty=false){if(dirty)this.dirty=true;if(this.timer){clearTimeout(this.timer);this.timer=0;}if(!this.raf)this.raf=requestAnimationFrame(this.frame);}
  /** Player activity: keeps the ambient rate up; `touch` (on the canvas itself) also runs full rate briefly. */
  poke(touch=false){const t=now();this.lastActive=t;if(touch){this.lastTouch=t;this.wake(true);}}
  /** A modal sheet or dialog is open over the stage (the side drawer on desktop leaves it visible). */
  covered(){const d=globalThis.document?.querySelector?.('dialog[open]');return !!d&&!d.classList?.contains('drawer');}
  /** Something moves for real right now: walking, keys, sparkles, the tap ring, a live happening, the petted cat. */
  busy(){const p=this.player,t=this._time||0;return !!(p?.path?.length||this.keys.size||this.particles.length||(this.marker&&t<this.marker.until)||(this.fx?.busy&&!this.reduced)||this.petUntil>t);}
  project(x,y,z=0){return {x:600+(x-y)*TW,y:205+(x+y)*TH-z};}
  unproject(x,y){const a=(x-600)/TW,b=(y-205)/TH;return {x:(a+b)/2,y:(b-a)/2};}
  screen(p){return {x:this.offset.x+p.x*this.scale,y:this.offset.y+p.y*this.scale};}
  resize(){const r=this.canvas.getBoundingClientRect();this.width=r.width||1200;this.height=r.height||790;
    // Small screens start at 2× (sharp) and drop to 1.5× when drawing turns out slow (watchCost).
    this.small=Math.min(this.width,this.height)<=520;this.dprCap??=2;this.costFrames=0;this.cost=null;
    this.dpr=Math.min(devicePixelRatio||1,this.small?this.dprCap:2);this.dirty=true;this.wake?.();this.canvas.width=Math.round(this.width*this.dpr);this.canvas.height=Math.round(this.height*this.dpr);this.layout();}
  layout(){const reserve=this.width>1050?215:this.width>760?145:0;const available=this.width-reserve;this.scale=Math.min(available/(this.width<760?1000:1160),this.height/(this.width<760?680:760));this.offset={x:(available-W*this.scale)/2+15,y:(this.height-H*this.scale)/2+(this.width<760?-25:8)};}
  update(state,content){
    const career=state.current||'mother_baby';
    if(career!==this.career){this.player={x:NaN,y:NaN,path:[],goal:null,look:1};this.pending=null;this.ambientPeople=[];}
    // Cached career previews show the player too: redraw them when the chosen look changes.
    const look=JSON.stringify([state.journey?.gender??null,state.wardrobe?.look??null,state.colors?.wear??null,state.wardrobe_colors?.wear??null]);if(look!==this.lookKey){this.lookKey=look;this.previewCache.clear();}
    this.career=career;this.game=content;this.state=state;this.c=state.careers[career];this.reduced=state.settings.reduceMotion;
    this.layout();this.setupObjects();this.rev=(this.rev||0)+1;this.wake(true);
  }
  setupObjects(){
    const shop=this.career==='mother_baby'||this.career==='pharmacy';
    const ph=this.career==='pharmacy';
    const c=this.c||{upgrades:[],tasks:[],event:null};
    this.obstacles=shop?[
      {x:1.2,y:.45,w:3.6,d:.95},{x:7.6,y:.5,w:2.8,d:1},
      {x:.4,y:3.4,w:1.1,d:2.1},{x:2.2,y:4.6,w:2.5,d:1.35},
      {x:7,y:5.1,w:3,d:1.15},
    ]:[{x:.5,y:3.5,w:1.1,d:2.5},{x:7.6,y:.5,w:2.8,d:1.1},{x:3.5,y:4.1,w:3.2,d:1.4},{x:7.5,y:2.8,w:2.5,d:1.3}];
    this.hotspots=[];
    const add=(id,label,x,y,z=20,range=40)=>this.hotspots.push({id,label,x,y,z,range,point:this.project(x,y,z)});
    if(shop){
      add('shelf',ph?'Kệ mã hộp':'Kệ quà nhỏ',3,1,70,75);
      add('shelf',ph?'Đọc mã · xem lô':'Kệ đồ dùng',9,1,65,65);
      add('workbench',ph?'Khay kiểm hai bước':'Bàn gói quà',3.45,5.3,48,60);
      add('counter',ph?'Bàn giao phiếu':'Quầy thu ngân',8.45,5.6,48,62);
      add('warehouse','Kho · kiểm nhận',.9,4.5,35,48);
    }else{
      add('workbench',this.career==='accounting'?'Bàn đối chiếu':'Bàn hỗ trợ',5.1,4.8,60,76);
      add('evidence',this.career==='accounting'?'Bản gốc · chứng từ':'Chứng cứ · phối hợp',8.7,3.4,54,60);
      add('warehouse','Sổ việc · đang chờ',1.1,4.8,50,48);
    }
    add('door',c.open?'Khép ca':'Bắt đầu ngày',8.4,8.7,5,40);
    add('board','Chuyện phố',5.7,.65,105,45);
    add('pet','Chơi với Mướp',2.7,7.4,14,36);
    const active=c.tasks?.filter(t=>!['completed','referred','cancelled'].includes(t.status))||[];
    const slots=shop?[[8.7,6.95],[10.15,7.2],[9.8,8.2],[7.1,7.45]]:[[7.3,6.1],[8.4,7.4],[9.6,6.6],[6.2,7.2]];
    const used=new Set();
    active.slice(0,4).forEach((t,i)=>{if(used.has(t.npc))return;used.add(t.npc);const [x,y]=slots[i];add('npc:'+t.npc,this.npcName(t.npc),x,y,35,34);});
    if(c.event&&c.event.stage!=='resolved')add('event',c.event.practice?'Diễn tập: '+c.event.title:'Có chuyện mới',4.85,7.65,38,38);
    if(c.upgrades?.includes('assistant'))add('assistant','Nhờ bạn phụ việc',6.7,2.35,38,34);
    this.navBuild();
  }
  npcName(id){return this.game?.npcs.find(n=>n.id===id)?.display_name||'Khách';}
  coords(e){const r=this.canvas.getBoundingClientRect();return {x:(e.clientX-r.left-this.offset.x)/this.scale,y:(e.clientY-r.top-this.offset.y)/this.scale};}
  hit(pos){return this.hotspots.map(h=>({h,d:Math.hypot(pos.x-h.point.x,pos.y-h.point.y)/h.range})).filter(x=>x.d<1).sort((a,b)=>a.d-b.d)[0]?.h||null;}
  pointerMove(e){this.hover=this.hit(this.coords(e));this.canvas.style.cursor=this.hover?'pointer':'default';}
  pointerDown(e){if(this.paused)return;const pos=this.coords(e);if(this.fx?.tap(pos))return;const h=this.hit(pos);if(h)this.goToHotspot(h);else{const tile=this.unproject(pos.x,pos.y);this.walkTo(tile.x,tile.y);}}
  keydown(e){if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','w','a','s','d'].includes(e.key)){e.preventDefault();this.keys.add(e.key.toLowerCase());}
    if(e.key.toLowerCase()==='e'){e.preventDefault();const h=[...this.hotspots].sort((a,b)=>this.navDist(a,this.player)-this.navDist(b,this.player))[0];if(h)this.goToHotspot(h);}}
  free(x,y){return x>=.6&&x<=10.5&&y>=.6&&y<=8.5&&!this.obstacles.some(r=>x>r.x-.15&&x<r.x+r.w+.15&&y>r.y-.15&&y<r.y+r.d+.15);}
  /* ------------------------------------------------------------ Navigation
   * Walkability is sampled on a fine grid (step NAV_STEP tiles). navFree(x,y)
   * is the continuous truth: floor bounds minus every prop footprint and every
   * standing person, already widened by the walker's own clearance. Paths are
   * A* (8-way, diagonals never squeeze between two blocked cells) and are then
   * shortened only where the straight segment passes navFree() at every few
   * pixels, so smoothing can never cut a corner through furniture. A click on a
   * blocked or outside point goes to the nearest reachable cell (or nowhere
   * when it is far from the floor). Subclasses override navFree/navBounds. */
  navBounds(){return {x0:.6,y0:.6,x1:10.5,y1:8.5};}
  navFree(x,y){return this.free(x,y);}
  navMetric(){return {kx:1,ky:1};}
  navHome(){return {x:6.1,y:6.2};}
  navSnap(){return 4;}
  navSignature(){return JSON.stringify([this.width>0,this.obstacles]);}
  navBuild(force=false){
    const sig=this.navSignature();
    if(!force&&this.nav&&this.nav.sig===sig){this.navSettle(false);return this.nav;}
    const b=this.navBounds(),step=.2,cols=Math.max(1,Math.floor((b.x1-b.x0)/step)+1),rows=Math.max(1,Math.floor((b.y1-b.y0)/step)+1);
    const walk=new Uint8Array(cols*rows),comp=new Int32Array(cols*rows).fill(-1);
    for(let j=0;j<rows;j++)for(let i=0;i<cols;i++)walk[j*cols+i]=this.navFree(b.x0+i*step,b.y0+j*step)?1:0;
    // Connected regions (4-way; diagonal moves also need both side cells).
    let label=0;const queue=new Int32Array(cols*rows);
    for(let s=0;s<walk.length;s++){if(!walk[s]||comp[s]>=0)continue;let head=0,tail=0;queue[tail++]=s;comp[s]=label;
      while(head<tail){const k=queue[head++],i=k%cols,j=(k-i)/cols,a={x:b.x0+i*step,y:b.y0+j*step};for(const [di,dj] of [[1,0],[-1,0],[0,1],[0,-1]]){const ni=i+di,nj=j+dj;if(ni<0||nj<0||ni>=cols||nj>=rows)continue;const n=nj*cols+ni;if(walk[n]&&comp[n]<0&&this.lineClear(a,{x:b.x0+ni*step,y:b.y0+nj*step})){comp[n]=label;queue[tail++]=n;}}}
      label++;}
    this.nav={...b,step,cols,rows,walk,comp,sig};
    this.navSettle(true);
    return this.nav;
  }
  navGrid(){return this.nav||this.navBuild();}
  navCell(x,y){const g=this.navGrid(),i=Math.round((x-g.x0)/g.step),j=Math.round((y-g.y0)/g.step);return i<0||j<0||i>=g.cols||j>=g.rows?-1:j*g.cols+i;}
  navPoint(k){const g=this.navGrid(),i=k%g.cols;return {x:g.x0+i*g.step,y:g.y0+(k-i)/g.cols*g.step};}
  navDist(a,b){const m=this.navMetric();return Math.hypot((a.x-b.x)*m.kx,(a.y-b.y)*m.ky);}
  /** Nearest walkable cell to (x,y), optionally inside one region and within a
   * screen-space radius. Returns a cell index or -1. */
  navNearest(x,y,region=-1,max=Infinity){const g=this.navGrid();let best=-1,bd=max;
    for(let k=0;k<g.walk.length;k++){if(!g.walk[k]||region>=0&&g.comp[k]!==region)continue;const d=this.navDist(this.navPoint(k),{x,y});if(d<bd){bd=d;best=k;}}
    return best;}
  lineClear(a,b){const n=Math.max(1,Math.ceil(this.navDist(a,b)/3));for(let i=1;i<=n;i++){const t=i/n;if(!this.navFree(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t))return false;}return true;}
  /** Keep the player out of footprints after a relayout or when a person
   * appears where they stand: step aside on foot when possible. */
  navSettle(rebuilt){const p=this.player;if(!p)return;
    if(!Number.isFinite(p.x)||!Number.isFinite(p.y)){Object.assign(p,this.navHome(),{path:[],goal:null});}
    if(this.navFree(p.x,p.y)){if(rebuilt&&p.path?.length&&p.goal)this.replan();return;}
    const k=this.navNearest(p.x,p.y);if(k<0)return;const q=this.navPoint(k);
    // A person arrived on top of us: step aside on foot. A relayout that put
    // us inside furniture: settle on the closest floor cell at once.
    if(this.navDist(q,p)<=90&&!this.navStaticBlocked(p.x,p.y)){p.path=[q];p.goal=q;}else{Object.assign(p,{x:q.x,y:q.y});p.path=[];p.goal=null;this.pending=null;}
  }
  navStaticBlocked(x,y){return !this.navFree(x,y);}
  replan(){const p=this.player,goal=p.goal,path=goal&&this.navPath(goal.x,goal.y);if(path){p.path=path;}else{p.path=[];p.goal=null;this.pending=null;}}
  /** Smoothed walk from the player to (tx,ty) as a list of points: [] when
   * already there, null when nothing reachable is near the target. With
   * strict=true only the target itself (or its own cell) is accepted. */
  navPath(tx,ty,strict=false){
    const g=this.navGrid(),p=this.player,m=this.navMetric();
    let start=this.navCell(p.x,p.y);if(start<0||!g.walk[start])start=this.navNearest(p.x,p.y);
    if(start<0)return null;
    const region=g.comp[start];let goal=-1,exact=false;
    if(this.navFree(tx,ty)){goal=this.navNearest(tx,ty,region,Math.hypot(g.step*m.kx,g.step*m.ky));exact=goal>=0;}
    if(goal<0){if(strict)return null;goal=this.navNearest(tx,ty,region,this.navSnap());}
    if(goal<0)return null;
    const cells=this.navAStar(start,goal);if(!cells)return null;
    const pts=cells.map(k=>this.navPoint(k));
    if(exact){const end={x:tx,y:ty};if(pts.length>1&&this.lineClear(pts.at(-2),end))pts[pts.length-1]=end;else if(this.lineClear(pts.at(-1),end))pts.push(end);}
    // String-pulling: from each anchor jump to the farthest point in plain
    // sight. If we start inside a person's space the first hop is the short
    // step out to the nearest free cell.
    const out=[];let anchor={x:p.x,y:p.y},i=0;
    while(i<pts.length){let j=i;while(j+1<pts.length&&this.lineClear(anchor,pts[j+1]))j++;out.push(pts[j]);anchor=pts[j];i=j+1;}
    if(out.length&&this.navDist(out[0],p)<.5)out.shift();
    return out;
  }
  navAStar(start,goal){
    const g=this.navGrid(),m=this.navMetric(),N=g.walk.length,cost=new Float64Array(N).fill(Infinity),prev=new Int32Array(N).fill(-1),closed=new Uint8Array(N);
    const sx=g.step*m.kx,sy=g.step*m.ky,diag=Math.hypot(sx,sy),gi=goal%g.cols,gj=(goal-gi)/g.cols;
    const h=k=>{const i=k%g.cols,j=(k-i)/g.cols;return Math.hypot((i-gi)*sx,(j-gj)*sy);};
    const heap=[];const push=(k,f)=>{heap.push([f,k]);let n=heap.length-1;while(n){const u=(n-1)>>1;if(heap[u][0]<=heap[n][0])break;[heap[u],heap[n]]=[heap[n],heap[u]];n=u;}};
    const pop=()=>{const top=heap[0],last=heap.pop();if(heap.length){heap[0]=last;let n=0;for(;;){const l=2*n+1,r=l+1;let s=n;if(l<heap.length&&heap[l][0]<heap[s][0])s=l;if(r<heap.length&&heap[r][0]<heap[s][0])s=r;if(s===n)break;[heap[s],heap[n]]=[heap[n],heap[s]];n=s;}}return top;};
    cost[start]=0;push(start,h(start));
    while(heap.length){const [,k]=pop();if(closed[k])continue;closed[k]=1;if(k===goal)break;const i=k%g.cols,j=(k-i)/g.cols;
      for(const [di,dj] of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[1,-1],[-1,1]]){const ni=i+di,nj=j+dj;if(ni<0||nj<0||ni>=g.cols||nj>=g.rows)continue;const n=nj*g.cols+ni;
        if(!g.walk[n]||closed[n])continue;if(di&&dj&&(!g.walk[j*g.cols+ni]||!g.walk[nj*g.cols+i]))continue;
        // Two free cells can still have a thin tip of a footprint between them.
        if(!this.lineClear(this.navPoint(k),this.navPoint(n)))continue;
        const c=cost[k]+(di&&dj?diag:di?sx:sy);if(c<cost[n]){cost[n]=c;prev[n]=k;push(n,c+h(n));}}}
    if(!closed[goal])return null;
    const cells=[];for(let k=goal;k>=0;k=prev[k])cells.unshift(k);return cells;
  }
  pathLength(path){let len=0,a=this.player;for(const b of path){len+=this.navDist(a,b);a=b;}return len;}
  walkTo(x,y,callback=null,{marker=true}={}){
    const path=this.navPath(x,y);this.wake(true);
    if(!path){this.pending=null;return false;}
    this.player.path=path;this.player.goal=path.at(-1)||{x:this.player.x,y:this.player.y};this.pending=callback;
    if(marker&&path.length){const end=path.at(-1);this.marker={x:end.x,y:end.y,until:this.time+1.1};}
    if(this.reduced||!path.length){const last=path.at(-1);if(last)Object.assign(this.player,{x:last.x,y:last.y});this.player.path=[];const fn=this.pending;this.pending=null;fn?.();}
    return true;
  }
  /** Walk to the best interaction spot of a hotspot (shortest reachable path
   * among its approach points), face it, then interact. */
  approach(h,callback){
    const spots=(h.approach&&h.approach.length?h.approach:[{x:h.x,y:h.y+.9}]);let best=null,bestLen=Infinity;
    for(const s of spots){const path=this.navPath(s.x,s.y,true);if(path){const len=this.pathLength(path);if(len<bestLen){best=s;bestLen=len;}}}
    if(!best){for(const s of spots){const path=this.navPath(s.x,s.y);if(path){const len=this.pathLength(path);if(len<bestLen){best=s;bestLen=len;}}}}
    const face=()=>{const sp=this.project(h.x,h.y),pp=this.project(this.player.x,this.player.y);if(Math.abs(sp.x-pp.x)>6)this.player.look=sp.x>=pp.x?1:-1;callback?.();};
    if(!best||!this.walkTo(best.x,best.y,face,{marker:false})){face();}
  }
  goToHotspot(h){
    if(h.id==='door'&&this.c?.open===false){this.onInteract?.(h.id);return;}
    this.ping(h.point.x,h.point.y,'#d6ad6a');
    this.approach(h,()=>this.onInteract?.(h.id));
  }
  go(id,callback){const h=this.hotspots.find(h=>h.id===id);if(!h){callback?.();return;}this.approach(h,callback);}
  /** Keyboard step in screen-space pixels with wall sliding. */
  keyMove(dx,dy,dt,speed=220){if(!dx&&!dy)return;const m=this.navMetric(),len=Math.hypot(dx,dy),p=this.player;
    const mx=dx/len*speed*dt/m.kx,my=dy/len*speed*dt/m.ky;
    const tries=[[mx,my],[mx,0],[0,my]];
    for(const [ax,ay] of tries){if(!ax&&!ay)continue;const nx=p.x+ax,ny=p.y+ay;if(this.navFree(nx,ny)){p.x=nx;p.y=ny;if(ax)p.look=ax>0?1:-1;break;}}
    p.path=[];p.goal=null;this.pending=null;}
  say(text,npc=null){const h=this.hotspots.find(h=>h.id===`npc:${npc}`)||(npc==='event'?this.hotspots.find(h=>h.id==='event'):null);const point=h?this.project(h.x,h.y,84):this.project(this.player.x,this.player.y,92);this.speech={text,point,expires:this.time+Math.min(4,1.8+String(text||'').length/30)};this.wake(true);}
  ping(x,y,color='#b99456'){this.wake(true);for(let i=0;i<8;i++)this.particles.push({x,y,vx:Math.cos(i*Math.PI/4)*24,vy:Math.sin(i*Math.PI/4)*17-13,life:1.1,max:1.1,color,size:3});}
  celebrate(){this.wake(true);const p=this.project(this.player.x,this.player.y,60);for(let i=0;i<32;i++)this.particles.push({x:p.x,y:p.y,vx:(Math.random()-.5)*140,vy:-30-Math.random()*100,life:1.7,max:1.7,color:['#d4b06f','#97aa85','#b797a9','#e6cdb2'][i%4],size:3+Math.random()*3});}
  pet(){this.say('Mrrr… chỗ này ấm quá.');const p=this.project(2.7,7.4,30);this.ping(p.x,p.y,'#c58b85');this.petUntil=this.time+4;}
  frame(at){
    this.raf=0;const dt=Math.min((at-this.last)/1000||0,.25);this.last=at;
    if(globalThis.document?.hidden||this.onScreen===false){this.dirty=true;return;}   // visibilitychange / IntersectionObserver wake us
    const covered=this.covered(),moving=this.busy(),walking=!!(this.player?.path?.length||this.keys.size);
    // Under a sheet the player keeps walking (a pending tap still arrives) but nothing is painted.
    if(!this.paused&&(!covered||walking)){this.time+=dt;this.animate(dt);}
    const t=now(),motion=this.busy(),touched=t-this.lastTouch<TOUCH;
    if(moving&&!motion)this.dirty=true;   // the last sparkle or step: show the settled frame
    if(covered){
      if(this.dirty)this.paint(t);
      // Closing a dialog wakes us; poll slowly as a fallback, and keep stepping while someone walks.
      this.next(walking&&!this.paused?0:1000);
      return;}
    const still=this.paused||this.reduced;this.longIdle=t-this.lastActive>LONG_IDLE;
    const gap=(motion&&!this.paused)||touched?FULL:still?STILL:this.longIdle?IDLE:AMBIENT;
    if(this.dirty||t-this.lastDraw>=gap-SLACK)this.paint(t);
    this.next(gap===FULL?0:Math.max(1,this.lastDraw+gap-now()-SLACK));
  }
  /** Schedule the next frame: 0 = next display frame, else a timer (no vsync wake-ups while waiting). */
  next(ms){if(this.raf)return;clearTimeout(this.timer);this.timer=0;if(ms<=0)this.raf=requestAnimationFrame(this.frame);else this.timer=setTimeout(this.tick,ms);}
  paint(t){this.dirty=false;this.lastDraw=t;const a=now();this.draw();this.watchCost(now()-a);}
  /** Phones: if drawing stays slow, render the canvas at a lower pixel ratio (never below 1.5). */
  watchCost(ms){if(!this.small||this.dprCap<=1.5)return;this.cost=this.cost==null?ms:this.cost*.9+ms*.1;
    if(++this.costFrames>30&&this.cost>12){this.dprCap=1.5;this.resize();}}
  animate(dt){
    if(this.keys.size){const k=this.keys;let dx=0,dy=0;if(k.has('w')||k.has('arrowup')){dx-=1;dy-=1;}if(k.has('s')||k.has('arrowdown')){dx+=1;dy+=1;}if(k.has('a')||k.has('arrowleft')){dx-=1;dy+=1;}if(k.has('d')||k.has('arrowright')){dx+=1;dy-=1;}
      const nx=this.player.x+dx*dt*2.2,ny=this.player.y+dy*dt*2.2;if(this.navFree(nx,ny)){this.player.x=nx;this.player.y=ny;this.player.path=[];this.player.goal=null;this.pending=null;}}
    // Constant on-screen walking speed along an already validated path.
    const target=this.player.path[0];if(target){const m=this.navMetric(),px=(target.x-this.player.x)*m.kx,py=(target.y-this.player.y)*m.ky,dist=Math.hypot(px,py),step=dt*(this.walkSpeed||3.8*m.kx);
      if(dist<=step){this.player.x=target.x;this.player.y=target.y;this.player.path.shift();if(!this.player.path.length){this.player.goal=null;const fn=this.pending;this.pending=null;fn?.();}}
      else{this.player.x+=px/dist*step/m.kx;this.player.y+=py/dist*step/m.ky;if(Math.abs(px)>1)this.player.look=px>=0?1:-1;}}
    this.particles.forEach(p=>{p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=55*dt;p.life-=dt;});this.particles=this.particles.filter(p=>p.life>0);
    if(this.speech&&this.time>this.speech.expires){this.speech=null;this.dirty=true;}
  }
  cube(x,y,w,d,h,top,front,side){const c=this.ctx,pr=(a,b,z)=>this.project(a,b,z);const a=pr(x,y,h),b=pr(x+w,y,h),e=pr(x+w,y+d,h),f=pr(x,y+d,h);poly(c,[b,e,pr(x+w,y+d,0),pr(x+w,y,0)],side||shade(top,-20),'#795f4420');poly(c,[f,e,pr(x+w,y+d,0),pr(x,y+d,0)],front||shade(top,-8),'#795f4420');poly(c,[a,b,e,f],top,'#fff5e645');}
  shadow(x,y,w=30,d=13){const p=this.project(x,y);ell(this.ctx,p.x,p.y+2,w,d,'#4e443520');}
  plant(x,y,scale=1){const c=this.ctx,p=this.project(x,y);c.save();c.translate(p.x,p.y);c.scale(scale,scale);ell(c,0,2,20,8,'#6a60431a');poly(c,[{x:-13,y:-26},{x:13,y:-26},{x:10,y:0},{x:-10,y:0}],'#c28f72');ell(c,0,-26,13,5,'#dfb495');line(c,0,-25,0,-72,'#81916b',3);for(let i=0;i<7;i++){const yy=-36-i*6;const dir=i%2?1:-1;c.save();c.translate(0,yy);c.rotate(dir*.6);ell(c,dir*9,-4,15,7,i%2?'#8ca47a':'#a8b28b');c.restore();}c.restore();}
  product(x,y,z,kind='box',color='#b7c6aa',size=1){const c=this.ctx,p=this.project(x,y,z);c.save();c.translate(p.x,p.y);c.scale(size,size);
    if(kind==='bunny'||kind==='bear'){
      const fill=kind==='bunny'?'#eee1c8':'#c3976b';ell(c,-7,-27,kind==='bunny'?4:6,kind==='bunny'?11:6,fill);ell(c,7,-27,kind==='bunny'?4:6,kind==='bunny'?11:6,fill);ell(c,0,-8,12,13,fill);ell(c,0,-20,13,12,fill);ell(c,-4,-20,1.4,1.8,'#675747');ell(c,4,-20,1.4,1.8,'#675747');ell(c,0,-15,2,1.5,'#bd907c');rr(c,-8,-6,16,5,'#90a387',2);
    }else if(kind==='bag'){rr(c,-12,-26,24,27,'#e2cdac',3);c.strokeStyle='#a28b6a';c.lineWidth=3;c.beginPath();c.arc(0,-26,7,Math.PI,0);c.stroke();ell(c,0,-12,7,6,'#aa8c6e');}
    else if(kind==='book'){rr(c,-5,-27,10,28,color,1);line(c,-2,-25,-2,-1,'#fff1d755',1);line(c,-3,-7,3,-7,'#eedfc8',1);}
    else{poly(c,[{x:-12,y:-23},{x:6,y:-27},{x:13,y:-21},{x:-5,y:-17}],shade(color,18));poly(c,[{x:-12,y:-23},{x:-5,y:-17},{x:-5,y:2},{x:-12,y:-3}],shade(color,-20));poly(c,[{x:-5,y:-17},{x:13,y:-21},{x:13,y:-2},{x:-5,y:2}],color);rr(c,-1,-14,10,8,'#f7eedb',1);}
    c.restore();}
  shelf(x,y,w=3.5,ph=false){const c=this.ctx,pal=PALETTE[this.career];this.cube(x,y,w,.8,100,'#d4b88d','#c1a071','#b7956b');
    // Open cubbies, offset in front of the face to keep shelves readable.
    for(let level=0;level<3;level++){
      const z=9+level*30;
      const a=this.project(x+.1,y+.82,z+26),b=this.project(x+w-.1,y+.82,z+26),d=this.project(x+w-.1,y+.82,z),e=this.project(x+.1,y+.82,z);
      poly(c,[a,b,d,e],pal.wall,'#a28b6650');
      for(let i=0;i<Math.floor(w*1.5);i++){
        const px=x+.38+i*.6;
        this.product(px,y+.87,z+3,ph?'box':(level===1&&i<2?['bunny','bear'][i]:level===2?'bag':'box'),['#b2c0a0','#d5a5a4','#a2bfca','#d5bb85'][i%4],.62);
      }
      const a2=this.project(x,y+.91,z),b2=this.project(x+w,y+.91,z);line(c,a2.x,a2.y,b2.x,b2.y,'#e5ca9a',5);
    }
    this.plant(x+w-.15,y+.4,.52); // plant sits visually on the upper corner below
  }
  desk(x,y,w=3,d=1.3,kind='computer'){
    const c=this.ctx,pal=PALETTE[this.career];this.shadow(x+w/2,y+d/2,65,23);
    // Individual legs keep the tables from looking like dashboard blocks.
    for(const [a,b] of [[x+.12,y+.1],[x+w-.32,y+.1],[x+.12,y+d-.22],[x+w-.32,y+d-.22]])this.cube(a,b,.18,.18,39,'#bc9f76');
    this.cube(x,y,w,d,44,'#e7cea4','#ccb087','#b89a73');
    if(kind==='wrap'){
      const p=this.project(x+w*.45,y+d*.55,46);c.save();c.translate(p.x,p.y);c.rotate(.22);rr(c,-36,-14,70,30,'#aebda1',2);rr(c,-7,-26,31,27,'#e5bc84',3);line(c,7,-26,7,2,'#a16f59',5);line(c,-7,-12,23,-12,'#a16f59',4);c.restore();
      const q=this.project(x+w*.8,y+.25,46);ell(c,q.x,q.y,8,4,'#e1b690');line(c,q.x-5,q.y-2,q.x+4,q.y-21,'#947e64',2);
    }else if(kind==='check'){
      const p=this.project(x+w*.43,y+d*.58,46);rr(c,p.x-33,p.y-13,72,26,'#eff1df',4,'#92ab95');this.product(x+w*.35,y+.6,48,'box','#abc8b3',.68);this.product(x+w*.7,y+.6,48,'box','#a7c4d1',.68);
    }else{
      const p=this.project(x+w*.5,y+d*.4,46);line(c,p.x,p.y-8,p.x,p.y-28,'#6b7669',6);ell(c,p.x,p.y-6,18,5,'#899285');
      rr(c,p.x-32,p.y-63,64,43,'#646d64',5);rr(c,p.x-28,p.y-59,56,34,'#dce6d5',3);rr(c,p.x-23,p.y-54,14,24,pal.accent,2);for(let j=0;j<4;j++)rr(c,p.x-4,p.y-52+j*6,26-(j%2)*5,2,'#b4c5ae',1);
      rr(c,p.x-20,p.y+1,46,9,'#ece7d7',3);for(let j=0;j<2;j++)for(let i=0;i<8;i++)rr(c,p.x-17+i*5,p.y+3+j*3,3,1.5,'#b5bbae',.3);
      const paper=this.project(x+.38,y+.7,48);rr(c,paper.x-8,paper.y-11,24,29,'#fbf3df',1);for(let j=0;j<4;j++)line(c,paper.x-4,paper.y-4+j*5,paper.x+11,paper.y-4+j*5,pal.accent,1.4);
      const mug=this.project(x+w-.2,y+.6,48);rr(c,mug.x-6,mug.y-13,12,14,'#bd977b',3);ell(c,mug.x,mug.y-13,6,2,'#e6cab0');
      if(this.career==='customer_care'){c.strokeStyle='#697769';c.lineWidth=4;c.beginPath();c.arc(p.x+39,p.y-12,10,Math.PI,0);c.stroke();rr(c,p.x+27,p.y-13,5,13,'#879780',2);rr(c,p.x+47,p.y-13,5,13,'#879780',2);}
    }
  }
  counter(){const c=this.ctx,pal=PALETTE[this.career];this.cube(7,5.1,3,1.15,48,'#e2cca4',pal.counter,shade(pal.counter,-12));
    const a=this.project(7.12,6.26,28),b=this.project(9.87,6.26,28);line(c,a.x,a.y,b.x,b.y,shade(pal.counter,-15),1.5);
    for(let i=0;i<3;i++){const p=this.project(7.5+i*.8,6.29,19);rr(c,p.x-8,p.y-2,16,3,'#ded5b4',2);}
    const pos=this.project(8.9,5.45,50);rr(c,pos.x-20,pos.y-5,42,12,'#798d77',3);rr(c,pos.x-12,pos.y-36,31,26,'#6d7e69',3);rr(c,pos.x-9,pos.y-33,25,19,'#c5d7b7',2);text(c,'85',pos.x+3,pos.y-23,10,'#597254',700);
    this.product(7.7,5.65,49,this.career==='pharmacy'?'box':'bag','#b3c8b0',.9);
    const flower=this.project(9.85,5.5,48);rr(c,flower.x-7,flower.y-19,14,19,'#e9dfc9',4);line(c,flower.x,flower.y-19,flower.x-3,flower.y-41,'#86986f',2);ell(c,flower.x-4,flower.y-42,8,7,'#e0b39d');ell(c,flower.x-4,flower.y-42,3,3,'#c3a062');
  }
  wallPanel(axis,start,length,z,height,fill){let ps;if(axis==='x')ps=[this.project(start,0,z),this.project(start+length,0,z),this.project(start+length,0,z+height),this.project(start,0,z+height)];else ps=[this.project(0,start,z),this.project(0,start+length,z),this.project(0,start+length,z+height),this.project(0,start,z+height)];poly(this.ctx,ps,fill,'#c7bca260');}
  windowOnWall(axis,start){const c=this.ctx;const p=axis==='x'?this.project(start,0,139):this.project(0,start,139);c.save();c.translate(p.x,p.y);c.transform(axis==='x'?1:-1,TH/TW,0,1,0,0);
    rr(c,-4,-5,116,108,'#c1aa84',2);rr(c,0,0,108,98,'#f0ead4',1);const g=c.createLinearGradient(0,0,0,100);g.addColorStop(0,'#bdd4d4');g.addColorStop(1,'#e3e5ce');rr(c,5,5,98,87,g,1);
    ell(c,73,24,13,13,'#f5e9b8');ell(c,36,82,30,22,'#a7b896');ell(c,83,85,35,20,'#b7c5a1');ell(c,9,78,22,31,'#8ca485');
    line(c,53,5,53,93,'#f5efd9',5);line(c,5,48,103,48,'#f5efd9',4);
    poly(c,[{x:1,y:0},{x:21,y:0},{x:18,y:70},{x:7,y:82},{x:1,y:83}],'#efdfbd');poly(c,[{x:85,y:0},{x:108,y:0},{x:108,y:83},{x:90,y:70}],'#f0e2c3');
    line(c,-7,-7,119,-7,'#a28b64',4);rr(c,-9,98,126,8,'#c2a67e',1);c.restore();}
  board(){const c=this.ctx;const p=this.project(5.75,.05,129);c.save();c.translate(p.x,p.y);c.transform(1,.38,0,1,0,0);rr(c,-52,-28,95,63,'#c7ac82',3);rr(c,-47,-23,85,53,'#efe3c3',2);
    const papers=[[-37,-17,'#c9d4b2'],[-3,-18,'#e4c3a7'],[-31,7,'#d5ccdb'],[1,5,'#eadfbf']];papers.forEach(([x,y,col],i)=>{rr(c,x,y,24,19,col,1);ell(c,x+12,y+2,1.7,1.7,'#a08266');line(c,x+5,y+8,x+19,y+8,'#a69d80',1);line(c,x+5,y+12,x+15,y+12,'#a69d80',1);});c.restore();}
  cat(x,y){const c=this.ctx,p=this.project(x,y);const happy=this.petUntil>this.time;const bob=this.reduced?0:Math.sin(this.time*1.5)*.8;c.save();c.translate(p.x,p.y+bob);ell(c,0,4,25,9,'#816e4820');
    c.strokeStyle='#c29766';c.lineWidth=10;c.lineCap='round';c.beginPath();c.moveTo(-13,0);c.quadraticCurveTo(-38,-3,-26,-18+(happy?Math.sin(this.time*8)*4:Math.sin(this.time*2)*2));c.stroke();
    ell(c,0,-7,20,15,'#cba570');ell(c,4,-17,17,15,'#dfba84');poly(c,[{x:-12,y:-24},{x:-12,y:-39},{x:0,y:-28}],'#dfba84');poly(c,[{x:10,y:-29},{x:23,y:-38},{x:20,y:-21}],'#dfba84');
    poly(c,[{x:-9,y:-28},{x:-10,y:-35},{x:-3,y:-29}],'#c89785');poly(c,[{x:13,y:-29},{x:21,y:-34},{x:18,y:-27}],'#c89785');
    const blink=happy||Math.sin(this.time*.75)>0.96;if(blink){line(c,-5,-18,0,-17,'#6a5944',1.8);line(c,10,-17,15,-18,'#6a5944',1.8);}else{ell(c,-2,-18,1.8,2.2,'#6a5944');ell(c,12,-18,1.8,2.2,'#6a5944');}
    ell(c,5,-12,2.4,1.6,'#a77765');line(c,4,-30,4,-26,'#b38b59',2.3);line(c,-2,-31,-2,-27,'#b38b59',2);ell(c,-8,2,8,4,'#ead1a4');ell(c,13,2,8,4,'#ead1a4');c.restore();}
  character(x,y,id,player=false,moving=false){const c=this.ctx,p=this.project(x,y);const n=Number(String(id).slice(-2))||0;const old=!player&&(n===2&&(this.career==='mother_baby'||this.career==='pharmacy'));const cap=!player&&n===5;const long=player||n%2===1&&!old;const hair=old?'#b6b4a5':player?'#665142':n%2?'#745642':'#56554b';const cloth=player?'#8a9a74':CLOTHES[n%6];const phase=this.reduced?0:this.time*(moving?10:1.8)+n;const bob=moving?Math.sin(phase)*1.2:Math.sin(phase)*.5;
    c.save();c.translate(p.x,p.y);ell(c,0,1,20,8,'#4e443526');
    // Tiny feet and restrained gait: no extreme leg rigs or changing faces.
    ell(c,-7+(moving?Math.sin(phase)*2:0),-2,7,4,'#776652');ell(c,7-(moving?Math.sin(phase)*2:0),-2,7,4,'#776652');
    c.translate(0,bob);
    if(long){rr(c,-21,-69,42,56,hair,17);ell(c,player?20:0,-48,player?8:17,player?15:22,hair);}
    rr(c,-15,-35,30,30,cloth,10);rr(c,-9,-9,7,9,'#c4b095',2);rr(c,2,-9,7,9,'#c4b095',2);
    if(player){rr(c,-10,-31,20,25,'#d9d1ad',4);line(c,-9,-36,-6,-22,'#eae1be',3);line(c,9,-36,6,-22,'#eae1be',3);rr(c,-6,-16,12,6,'#b5bb91',2);}
    else if(this.career==='pharmacy'&&n===1){rr(c,-15,-35,30,28,'#eef0df',9);line(c,0,-30,0,-8,'#b9cbbb',1.5);}
    const arm=moving?Math.sin(phase)*3:0;
    rr(c,-21,-31+arm,8,22,'#e8c2a0',4);rr(c,13,-31-arm,8,22,'#e8c2a0',4);rr(c,-21,-33+arm,8,12,cloth,4);rr(c,13,-33-arm,8,12,cloth,4);
    rr(c,-6,-43,12,13,'#e5b993',4);
    ell(c,0,-61,23,26,hair);ell(c,-21,-50,4,6,'#f0c6a2');ell(c,21,-50,4,6,'#f0c6a2');ell(c,0,-54,22,24,'#f1caa6');
    c.fillStyle=hair;c.beginPath();c.moveTo(-23,-59);c.bezierCurveTo(-26,-88,22,-92,24,-58);c.quadraticCurveTo(9,-62,4,-73);c.quadraticCurveTo(-6,-59,-23,-59);c.fill();
    const blink=!this.reduced&&Math.sin(this.time*.9+n*3)>0.992;
    if(blink){line(c,-10,-53,-5,-53,'#51493c',2);line(c,5,-53,10,-53,'#51493c',2);}else{ell(c,-8,-54,2.2,2.6,'#51493c');ell(c,8,-54,2.2,2.6,'#51493c');ell(c,-7.4,-54.8,.6,.8,'#faf1dd');ell(c,8.6,-54.8,.6,.8,'#faf1dd');}
    ell(c,-14,-47,4.4,2.8,'#ddaa92');ell(c,14,-47,4.4,2.8,'#ddaa92');c.strokeStyle='#af7d68';c.lineWidth=1.5;c.beginPath();c.arc(0,-44,4,0,Math.PI);c.stroke();
    if(old){rr(c,-17,-61,14,13,'#ffffff10',4,'#7e7967');rr(c,3,-61,14,13,'#ffffff10',4,'#7e7967');line(c,-3,-55,3,-55,'#7e7967',1.2);}
    if(cap){ell(c,1,-73,23,9,'#87a4a3');rr(c,-7,-73,38,5,'#70908e',2);rr(c,20,-37,9,17,'#647f7d',2);rr(c,21,-35,7,12,'#d0decf',1);}
    if(player){rr(c,-5,-75,11,5,'#c59c75',3);}
    c.restore();}
  decorations(){const c=this.ctx,pal=PALETTE[this.career];const spots={window:[1.5,6.4],corner:[9.9,1.8],front:[5.7,8.1],center:[5.1,3.25],wall:[.05,2.4]};
    for(const [id,item] of Object.entries(this.c?.decor||{})){const [x,y]=spots[item.spot]||spots.window;
      if(id==='plant')this.plant(x,y,1.15);
      if(id==='rug'){poly(c,[this.project(x-1.15,y-.9),this.project(x+1.15,y-.9),this.project(x+1.15,y+.9),this.project(x-1.15,y+.9)],'#b7b995','#ede1bf');poly(c,[this.project(x-.9,y-.64),this.project(x+.9,y-.64),this.project(x+.9,y+.64),this.project(x-.9,y+.64)],'#b7b995','#e7dbc1');}
      if(id==='seat'){this.cube(x-.45,y-.4,.9,.8,21,'#bdc4a3','#a8b08f','#96a282');this.cube(x-.45,y-.4,.9,.14,48,'#c7ceaf','#b7c09f');}
      if(id==='lamp'){const p=this.project(x,y);ell(c,p.x,p.y,18,6,'#ac9474');line(c,p.x,p.y,p.x,p.y-92,'#b79c74',4);poly(c,[{x:p.x-15,y:p.y-98},{x:p.x+15,y:p.y-98},{x:p.x+26,y:p.y-65},{x:p.x-26,y:p.y-65}],'#e9d6a7');const glow=c.createRadialGradient(p.x,p.y-70,1,p.x,p.y-70,75);glow.addColorStop(0,'#f7e5b232');glow.addColorStop(1,'#f7e5b200');c.fillStyle=glow;c.fillRect(p.x-80,p.y-150,160,160);}
      if(id==='poster'){this.wallPanel('y',1.05,1.4,59,72,'#b4a083');this.wallPanel('y',1.15,1.2,66,58,'#ecdfc1');const p=this.project(.02,1.75,104);ell(c,p.x,p.y,16,13,pal.accent);text(c,'✦',p.x,p.y-2,15,'#f3edd8');}
    }
    if(this.c?.upgrades?.includes('shelf'))this.shelf(6.8,1.6,2,this.career==='pharmacy');
    if(this.c?.upgrades?.includes('board')){const p=this.project(10,3.7,68);rr(c,p.x-32,p.y-43,63,65,'#bfac8a',4);rr(c,p.x-27,p.y-38,53,55,'#f7efda',2);for(let i=0;i<4;i++)line(c,p.x-20,p.y-25+i*10,p.x+20,p.y-25+i*10,'#a7b19b',2);line(c,p.x,p.y+20,p.x,p.y+63,'#ab946b',4);}
  }
  drawRoom(){const c=this.ctx,pal={...PALETTE[this.career]};if(this.c?.theme==='sage'){pal.wall='#e6ead7';pal.side='#d3dcc0';}if(this.c?.theme==='lavender'){pal.wall='#e8e0ed';pal.side='#d5cadd';}
    // The soft ground and planted edges frame the diorama without a UI-like box.
    ell(c,625,511,454,174,'#b8ae9020');
    poly(c,[this.project(-.3,-.3,-16),this.project(11.3,-.3,-16),this.project(11.3,9.3,-16),this.project(-.3,9.3,-16)],'#d7c5a5');
    const corners=[this.project(0,0),this.project(11,0),this.project(11,9),this.project(0,9)];poly(c,corners,'#e7d5b5');
    for(let x=0;x<11;x++)for(let y=0;y<9;y++)poly(c,[this.project(x,y),this.project(x+1,y),this.project(x+1,y+1),this.project(x,y+1)],((x+y)%2?'#e9d8b9':'#edddc1'),'#c8b18a32');
    poly(c,[this.project(0,9),this.project(11,9),this.project(11,9,-15),this.project(0,9,-15)],'#c4ae88');poly(c,[this.project(11,0),this.project(11,9),this.project(11,9,-15),this.project(11,0,-15)],'#b4a17f');
    this.wallPanel('x',0,11,0,169,pal.wall);this.wallPanel('y',0,9,0,169,pal.side);
    for(let i=1;i<11;i++){const p1=this.project(i,0,0),p2=this.project(i,0,169);line(c,p1.x,p1.y,p2.x,p2.y,'#b3a58715',1);}
    this.wallPanel('x',0,11,0,10,'#d4c2a0');this.wallPanel('y',0,9,0,10,'#cbb694');
    const beam=[this.project(0,9,173),this.project(0,0,173),this.project(11,0,173)];c.beginPath();beam.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.strokeStyle='#dcc9a5';c.lineWidth=8;c.lineJoin='round';c.stroke();
    this.windowOnWall('y',5.8);this.board();
    const sign=this.project(4.1,.01,148);c.save();c.translate(sign.x,sign.y);c.transform(1,.4,0,1,0,0);rr(c,-106,-20,166,36,'#fbf2dd',7,'#d1bf9b');text(c,{mother_baby:'TIỆM MÂY NHỎ',pharmacy:'QUẦY BÌNH AN',accounting:'GÓC SỔ XINH',customer_care:'TRẠM LẮNG NGHE'}[this.career],-22,-1,13,pal.accent,800);c.restore();
    // Light from the window, contained to the floor.
    poly(c,[this.project(.05,6),this.project(.05,8.2),this.project(5,7.4),this.project(5,5.2)],'#fff6cb20');
    const rug=[this.project(4.8,2.7),this.project(7.3,2.7),this.project(7.3,5.2),this.project(4.8,5.2)];poly(c,rug,this.career==='accounting'?'#c9c2d0':this.career==='customer_care'?'#b9cdd0':'#c1c7a5');
    poly(c,[this.project(5,2.9),this.project(7.1,2.9),this.project(7.1,5),this.project(5,5)],'#ffffff00','#e9e4cf70');
    const mat=this.project(8.4,8.5);c.save();c.translate(mat.x,mat.y);c.transform(1,.2,-.75,.45,0,0);rr(c,-35,-18,90,36,'#a4b394',8);text(c,this.c?.open?'XIN CHÀO':'HẸN GẶP LẠI',10,0,11,'#f3efda',700);c.restore();
    this.plant(10.65,8.1,.9);this.plant(.7,8.5,1.1);
  }
  drawFurnitureAndActors(){const shop=this.career==='mother_baby'||this.career==='pharmacy';const ph=this.career==='pharmacy';const objects=[];const add=(depth,fn)=>objects.push({depth,fn});
    if(shop){
      add(3,()=>this.shelf(1.2,.45,3.6,ph));add(9,()=>this.shelf(7.6,.5,2.8,ph));
      add(5.5,()=>{this.cube(.4,3.4,1.1,2.1,49,'#dcc6a1','#cab38c','#bba47e');this.product(.75,3.8,51,'box','#b9b29a',.9);this.product(.9,4.9,51,'box','#c6b18b',1);});
      add(7.95,()=>this.desk(2.2,4.6,2.5,1.35,ph?'check':'wrap'));
      add(14.7,()=>this.counter());
    }else{
      add(9,()=>this.shelf(7.6,.5,2.8,true));
      add(5.8,()=>{this.cube(.5,3.5,1.1,2.5,86,'#c4b392','#b5a88f','#a19885');for(let i=0;i<3;i++){const a=this.project(.6,6.01,22+i*24),b=this.project(1.55,6.01,22+i*24);line(this.ctx,a.x,a.y,b.x,b.y,'#968d7760',1.5);const p=this.project(1.05,6.01,33+i*24);rr(this.ctx,p.x-6,p.y-2,12,3,'#e8ddc3',1);}});
      add(10.5,()=>this.desk(3.5,4.1,3.2,1.4));add(12,()=>this.desk(7.5,2.8,2.5,1.3));
    }
    add(11,()=>this.decorations());
    for(const h of this.hotspots){if(h.id.startsWith('npc:'))add(h.x+h.y,()=>this.character(h.x,h.y,h.id.slice(4)));if(h.id==='event')add(h.x+h.y,()=>this.character(h.x,h.y,this.c.event.npc));if(h.id==='assistant')add(h.x+h.y,()=>this.character(h.x,h.y,`${this.career}_npc_04`));}
    add(10.1,()=>this.cat(2.7,7.4));
    add(this.player.x+this.player.y,()=>this.character(this.player.x,this.player.y,'player',true,this.player.path.length>0||this.keys.size>0));
    objects.sort((a,b)=>a.depth-b.depth).forEach(o=>o.fn());
  }
  labels(){const c=this.ctx;const active=this.c?.active_task;const activeNPC=this.c?.tasks?.find(t=>t.id===active)?.npc;
    for(const h of this.hotspots){const hover=this.hover?.id===h.id&&this.hover?.x===h.x;const npc=h.id.startsWith('npc:');const event=h.id==='event';
      if(npc||event){const p=this.project(h.x,h.y,93);const selected=npc&&h.id.slice(4)===activeNPC;const width=Math.max(48,h.label.length*7.3+24);rr(c,p.x-width/2,p.y-12,width,24,event?'#c28d68':selected?'#617b5c':'#faf5e8',10,'#ddd1b8');text(c,event?'!':h.label,p.x,p.y,11,event||selected?'#fff9e8':'#6e705c',700);if(selected){ell(c,p.x,p.y+36,3,3,'#f9efbf');}}
      if(hover){const p=this.project(h.x,h.y,h.z+35);const label=npc?'Trò chuyện với '+h.label:h.label;const width=label.length*7.2+30;rr(c,p.x-width/2,p.y-14,width,29,'#4c6149',10);text(c,label,p.x,p.y,12,'#fff8e8',650);}
      else if(!npc&&!event&&['workbench','counter','shelf','door'].includes(h.id)){
        const p=this.project(h.x,h.y,h.z+23);ell(c,p.x,p.y,10,10,'#fffbebed');text(c,h.id==='door'?this.c?.open?'↗':'▶':'+',p.x,p.y-.5,14,'#7c9272',700);
      }
    }
  }
  drawSpeech(){if(!this.speech)return;const c=this.ctx,p=this.speech.point;const words=this.speech.text.split(' ');const lines=[];let lineNow='';for(const word of words){if((lineNow+' '+word).length>33){lines.push(lineNow);lineNow=word;}else lineNow+=(lineNow?' ':'')+word;}if(lineNow)lines.push(lineNow);const shown=lines.slice(0,3),w=250,h=shown.length*20+22;rr(c,p.x-w/2,p.y-h,w,h,'#fff9ea',12,'#daccb0');poly(c,[{x:p.x-8,y:p.y},{x:p.x,y:p.y+10},{x:p.x+8,y:p.y}],'#fff9ea');shown.forEach((l,i)=>text(c,l,p.x,p.y-h+20+i*20,12,'#617056',500));}
  draw(){const c=this.ctx;if(!this.width)this.resize();c.setTransform(this.dpr,0,0,this.dpr,0,0);c.fillStyle='#f3efe3';c.fillRect(0,0,this.width,this.height);const bg=c.createRadialGradient(this.width*.5,this.height*.5,0,this.width*.5,this.height*.5,this.width*.65);bg.addColorStop(0,'#faf6ea');bg.addColorStop(1,'#eae6d9');c.fillStyle=bg;c.fillRect(0,0,this.width,this.height);
    c.translate(this.offset.x,this.offset.y);c.scale(this.scale,this.scale);this.drawRoom();this.drawFurnitureAndActors();this.labels();
    for(const p of this.particles){c.globalAlpha=Math.max(0,p.life/p.max);rr(c,p.x,p.y,p.size,p.size,p.color,1);}c.globalAlpha=1;this.drawSpeech();
    if(!this.reduced){for(let i=0;i<11;i++){const x=250+((i*119+this.time*4)%780),y=190+((i*73+Math.sin(this.time+i)*14)%430);ell(c,x,y,1.3,1.3,'#fffbed65');}}
  }
  /** The scene for the album (app.js 📸): WebP or JPEG, at most PHOTO_MAX characters (B10: Safari sent a PNG > 256 KB); null: none fits. */
  snapshot(){return encodePhoto(this.canvas,{width:1080,bg:'#efe7d5'});}
  preview(career){
    if(this.previewCache.has(career))return this.previewCache.get(career);
    const backup={ctx:this.ctx,career:this.career,c:this.c,state:this.state,game:this.game,hotspots:this.hotspots,player:this.player,obstacles:this.obstacles,hover:this.hover,nav:this.nav,people:this.people,props:this.props,pending:this.pending,marker:this.marker};
    const canvas=document.createElement('canvas');canvas.width=640;canvas.height=430;this.ctx=canvas.getContext('2d');this.ctx.fillStyle='#efe7d5';this.ctx.fillRect(0,0,640,430);this.ctx.translate(-18,6);this.ctx.scale(.55,.55);this.career=career;this.c={open:true,upgrades:['plant'],decor:{plant:{spot:'window'}},tasks:[{id:'preview',npc:career+'_npc_01',status:'new'}],active_task:'preview',event:null};this.player={x:6.1,y:6.2,path:[],look:1};this.hover=null;this.setupObjects();this.drawRoom();this.drawFurnitureAndActors();const image=canvas.toDataURL('image/webp',.85);Object.assign(this,backup);this.previewCache.set(career,image);return image;
  }
}
