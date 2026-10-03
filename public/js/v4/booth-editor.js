/** booth-editor.js — the sticker editor on a finished photo strip of the fair's photobooth (./fair-booth.js; owner
 * 03/10 22:00: "cho trang trí kéo thả không giới hạn nhé, mặc định rồi nhưng cho kéo thả icon sau chụp xong nữa").
 * The strip as printed (its frame, colours, words and the default stickers) is the base; on top of it the player puts
 * as many stickers (./booth-stickers.js) as they like: tap one in the tray to add it, drag it anywhere, resize and turn
 * it with the corner handle or two fingers (or the mouse wheel), tap to pick one, ✕ to take it off, bring it to the
 * front, undo, clear all. Only on this player's own copy: nothing goes to the server or to the friends in the room.
 *
 *   createEditor({onPick, onChange, t, max, seen}) → editor   seen() → [top, bottom] of the page the player sees
 *     (viewport px, without a tray over it); a new sticker lands in the middle of the strip's part in there
 *     editor.items            [{id, x, y, s, r}]  x, y the centre and s the box side, in strip widths; r radians
 *     editor.sel              the picked item's index (-1: none)
 *     editor.attach(canvas)   the on-screen canvas (its CSS width sets the size); listeners once per canvas
 *     editor.setBase(cv)      the strip as printed (any resolution; its shape is the strip's)
 *     editor.add(id, y?)      a sticker near y (strip widths; default: the middle of what is on screen); false at max
 *     editor.remove(), front(), undo(), clear(), reset()
 *     editor.draw()           the frame on screen (the selection box only on screen)
 *     editor.compose(c, w, h) the stickers over a w × h strip drawn in c (the saved picture, full resolution)
 *     editor.canUndo()
 * Light on cheap phones: each sticker is a cached sprite on screen (decoSprite), one redraw per animation frame while a
 * finger moves; the full-resolution vector drawing (drawDeco) only when the picture is saved. A touch on empty paper
 * scrolls the page as usual; a touch on a sticker (or two fingers on the picked one) moves it instead. */
import {drawDeco,decoSprite,knownDeco,DECO_FILL} from './booth-stickers.js';

const MIN_S=.06,MAX_S=1.1,UNDO=60;
const HANDLE=13;   // CSS px: the corner handles' radius (a finger's worth with the slack below)

export function createEditor({onPick=()=>{},onChange=()=>{},t=s=>s,max=200,seen=()=>null}={}){
  const ed={items:[],sel:-1,cv:null,base:null,aspect:3};
  const hist=[];let raf=0,gest=null;const ptrs=new Map();

  const snap=()=>{hist.push(JSON.stringify(ed.items));if(hist.length>UNDO)hist.shift();};
  const changed=()=>{draw();onChange(ed);};
  const pick=i=>{if(ed.sel!==i){ed.sel=i;onPick(ed);}draw();};
  const css=()=>{const b=ed.cv?.getBoundingClientRect();return b&&b.width?{w:b.width,h:b.height,b}:null;};
  const clampItem=it=>{it.s=Math.min(MAX_S,Math.max(MIN_S,it.s));it.x=Math.min(1,Math.max(0,it.x));it.y=Math.min(ed.aspect,Math.max(0,it.y));
    it.r=((it.r+Math.PI)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)-Math.PI;return it;};

  /* ---- geometry: a point on screen (CSS px of the canvas) in the item's own frame ---- */
  function local(it,px,py,W){const dx=px-it.x*W,dy=py-it.y*W,c=Math.cos(-it.r),s=Math.sin(-it.r);return [dx*c-dy*s,dx*s+dy*c];}
  /** A corner handle of the picked one (sx, sy ±1), kept inside the canvas so a finger can always reach it. */
  function corner(it,W,sx,sy){const h=it.s*W*DECO_FILL/2+4,c=Math.cos(it.r),s=Math.sin(it.r),H=W*ed.aspect,m=HANDLE+1;
    return [Math.min(W-m,Math.max(m,it.x*W+(sx*h)*c-(sy*h)*s)),Math.min(H-m,Math.max(m,it.y*W+(sx*h)*s+(sy*h)*c))];}
  function hit(px,py){
    const g=css();if(!g)return null;const W=g.w,slack=matchMedia?.('(pointer: coarse)').matches?8:3;
    if(ed.sel>=0){const it=ed.items[ed.sel];
      const [hx,hy]=corner(it,W,1,1),[dx,dy]=corner(it,W,-1,-1);
      if(Math.hypot(px-hx,py-hy)<=HANDLE+slack)return {i:ed.sel,part:'turn'};
      if(Math.hypot(px-dx,py-dy)<=HANDLE+slack)return {i:ed.sel,part:'del'};}
    for(let i=ed.items.length-1;i>=0;i--){const it=ed.items[i],[lx,ly]=local(it,px,py,W),h=it.s*W*DECO_FILL/2+slack;
      if(Math.abs(lx)<=h&&Math.abs(ly)<=h)return {i,part:'body'};}
    return null;
  }

  /* ---- drawing ---- */
  function paint(c,W,{sprites,box}){
    for(let i=0;i<ed.items.length;i++){const it=ed.items[i],side=it.s*W;
      c.save();c.translate(it.x*W,it.y*W);c.rotate(it.r);
      try{
        if(sprites){const sp=decoSprite(it.id,Math.max(32,Math.round(side*(sprites||1))),{t});if(sp)c.drawImage(sp,-side/2,-side/2,side,side);}
        else drawDeco(c,it.id,side*DECO_FILL,{t});
      }catch(e){console.warn('chụp ảnh: sticker',e);}
      c.restore();}
    if(box&&ed.sel>=0&&ed.items[ed.sel]){const it=ed.items[ed.sel],h=it.s*W*DECO_FILL/2+4;
      c.save();c.translate(it.x*W,it.y*W);c.rotate(it.r);
      c.lineWidth=1.6;c.setLineDash([5,4]);c.strokeStyle='#ffffff';c.strokeRect(-h,-h,2*h,2*h);c.lineDashOffset=4.5;c.strokeStyle='#7a3fb0';c.strokeRect(-h,-h,2*h,2*h);c.setLineDash([]);
      c.restore();
      const knob=(x,y,fill,glyph)=>{c.beginPath();c.arc(x,y,HANDLE,0,Math.PI*2);c.fillStyle='#ffffff';c.fill();c.beginPath();c.arc(x,y,HANDLE-2.2,0,Math.PI*2);c.fillStyle=fill;c.fill();
        c.fillStyle='#fff';c.font='900 13px "Trebuchet MS",sans-serif';c.textAlign='center';c.textBaseline='middle';c.fillText(glyph,x,y+.5);};
      knob(...corner(it,W,-1,-1),'#e2574c','✕');knob(...corner(it,W,1,1),'#7a3fb0','↻');}
  }
  function draw(){
    cancelAnimationFrame(raf);raf=0;
    const cv=ed.cv;if(!cv?.isConnected)return;
    const g=css();if(!g)return;
    const dpr=Math.min(2,globalThis.devicePixelRatio||1),pw=Math.round(g.w*dpr),ph=Math.round(g.w*ed.aspect*dpr);
    if(cv.width!==pw||cv.height!==ph){cv.width=pw;cv.height=ph;}
    const c=cv.getContext('2d');c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,pw,ph);
    if(ed.base)c.drawImage(ed.base,0,0,pw,ph);
    c.setTransform(dpr,0,0,dpr,0,0);
    paint(c,g.w,{sprites:dpr,box:true});
  }
  const soon=()=>{if(!raf)raf=requestAnimationFrame(draw);};

  /* ---- fingers and the mouse ---- */
  const at=e=>{const g=css();return g?[e.clientX-g.b.left,e.clientY-g.b.top]:[0,0];};
  function down(e){
    if(e.button>0)return;
    const p=at(e);ptrs.set(e.pointerId,p);
    if(ptrs.size===2&&ed.sel>=0&&gest){   // a second finger: pinch and turn the picked one
      const [a,b]=[...ptrs.values()],it=ed.items[ed.sel];
      gest={kind:'pinch',d0:Math.hypot(b[0]-a[0],b[1]-a[1])||1,a0:Math.atan2(b[1]-a[1],b[0]-a[0]),m0:[(a[0]+b[0])/2,(a[1]+b[1])/2],o:{...it},saved:gest.saved};
      e.preventDefault();return;
    }
    if(ptrs.size>1)return;
    const h=hit(...p);
    if(!h){gest=null;if(ed.sel>=0)pick(-1);return;}
    e.preventDefault();try{ed.cv.setPointerCapture(e.pointerId);ed.cv.focus({preventScroll:true});}catch{/* an old browser */}
    if(h.part==='del'){ed.sel=h.i;remove();gest=null;return;}
    if(h.i!==ed.sel)pick(h.i);
    const it=ed.items[h.i],g=css();
    gest=h.part==='turn'?{kind:'turn',o:{...it},c:[it.x*g.w,it.y*g.w],d0:Math.hypot(p[0]-it.x*g.w,p[1]-it.y*g.w)||1,a0:Math.atan2(p[1]-it.y*g.w,p[0]-it.x*g.w),saved:false}
      :{kind:'drag',o:{...it},p0:p,saved:false};
  }
  function move(e){
    if(!ptrs.has(e.pointerId))return;
    const p=at(e);ptrs.set(e.pointerId,p);
    if(!gest||ed.sel<0)return;
    e.preventDefault();
    const it=ed.items[ed.sel],g=css();if(!it||!g)return;const W=g.w;
    if(!gest.saved){hist.push(JSON.stringify(ed.items.map((x,i)=>i===ed.sel?gest.o:x)));if(hist.length>UNDO)hist.shift();gest.saved=true;}
    if(gest.kind==='drag'){it.x=gest.o.x+(p[0]-gest.p0[0])/W;it.y=gest.o.y+(p[1]-gest.p0[1])/W;}
    else if(gest.kind==='turn'){const d=Math.hypot(p[0]-gest.c[0],p[1]-gest.c[1]),a=Math.atan2(p[1]-gest.c[1],p[0]-gest.c[0]);it.s=gest.o.s*d/gest.d0;it.r=gest.o.r+a-gest.a0;}
    else if(gest.kind==='pinch'&&ptrs.size>=2){const [a,b]=[...ptrs.values()],d=Math.hypot(b[0]-a[0],b[1]-a[1])||1,ang=Math.atan2(b[1]-a[1],b[0]-a[0]),m=[(a[0]+b[0])/2,(a[1]+b[1])/2];
      it.s=gest.o.s*d/gest.d0;it.r=gest.o.r+ang-gest.a0;it.x=gest.o.x+(m[0]-gest.m0[0])/W;it.y=gest.o.y+(m[1]-gest.m0[1])/W;}
    clampItem(it);soon();
  }
  function up(e){
    if(!ptrs.delete(e.pointerId))return;
    if(gest?.kind==='pinch'&&ptrs.size===1&&ed.sel>=0){const [p]=[...ptrs.values()];gest={kind:'drag',o:{...ed.items[ed.sel]},p0:p,saved:true};return;}
    if(ptrs.size)return;
    const did=gest?.saved;gest=null;
    if(did)changed();else draw();
  }
  function wheel(e){
    if(ed.sel<0)return;const p=at(e),h=hit(...p);if(!h||h.i!==ed.sel)return;
    e.preventDefault();const it=ed.items[ed.sel];if(!wheel.t)snap();
    if(e.shiftKey)it.r+=e.deltaY>0?.12:-.12;else it.s*=e.deltaY>0?.92:1.08;
    clampItem(it);clearTimeout(wheel.t);wheel.t=setTimeout(()=>{wheel.t=0;onChange(ed);},250);soon();
  }
  function key(e){
    if(ed.sel<0)return;
    if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault();remove();return;}
    const step={ArrowLeft:[-.01,0],ArrowRight:[.01,0],ArrowUp:[0,-.01],ArrowDown:[0,.01]}[e.key];
    if(step){e.preventDefault();snap();const it=ed.items[ed.sel];it.x+=step[0];it.y+=step[1];clampItem(it);changed();}
  }
  // a touch on a sticker moves it (no page scroll); elsewhere the page scrolls as usual
  function touch(e){
    const g=css();if(!g)return;
    const tt=[...e.touches].map(x=>[x.clientX-g.b.left,x.clientY-g.b.top]);
    if((tt.length>=2&&ed.sel>=0&&gest)||(tt.length===1&&hit(...tt[0])))e.preventDefault();
  }

  ed.attach=cv=>{
    ed.cv=cv;
    if(cv&&!cv._ed){cv._ed=1;
      cv.addEventListener('pointerdown',down);cv.addEventListener('pointermove',move);
      cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);cv.addEventListener('lostpointercapture',up);
      cv.addEventListener('wheel',wheel,{passive:false});cv.addEventListener('keydown',key);
      cv.addEventListener('touchstart',touch,{passive:false});cv.addEventListener('touchmove',e=>{if(gest)e.preventDefault();},{passive:false});
      try{new ResizeObserver(()=>draw()).observe(cv);}catch{/* drawn on the next change */}}
    draw();
  };
  ed.setBase=cv=>{ed.base=cv||null;if(cv?.width)ed.aspect=cv.height/cv.width;draw();};
  /** The middle of the strip as it is on screen now (strip widths), so a new sticker lands where the player looks. */
  function middle(){
    const g=css();if(!g)return ed.aspect/2;
    let v=null;try{v=seen();}catch{/* the window then */}
    const [vt,vb]=Array.isArray(v)?v:[0,globalThis.innerHeight||g.h];
    const top=Math.max(0,vt-g.b.top),bot=Math.min(g.h,vb-g.b.top);
    return bot>top?((top+bot)/2)/g.w:ed.aspect/2;
  }
  ed.add=(id,y)=>{
    if(!knownDeco(id))return false;
    if(ed.items.length>=max)return false;
    snap();
    const n=ed.items.length,yy=Number.isFinite(y)?y:middle();
    ed.items.push(clampItem({id,x:.5+((n*37)%9-4)*.045,y:yy+((n*53)%7-3)*.04,s:.26,r:((n*29)%11-5)*.04}));
    ed.sel=ed.items.length-1;onPick(ed);changed();return true;
  };
  function remove(){if(ed.sel<0||!ed.items[ed.sel])return;snap();ed.items.splice(ed.sel,1);ed.sel=-1;onPick(ed);changed();}
  ed.remove=remove;
  ed.front=()=>{if(ed.sel<0||ed.sel===ed.items.length-1)return;snap();const [it]=ed.items.splice(ed.sel,1);ed.items.push(it);ed.sel=ed.items.length-1;onPick(ed);changed();};
  ed.undo=()=>{if(!hist.length)return;ed.items=JSON.parse(hist.pop());ed.sel=-1;onPick(ed);changed();};
  ed.clear=()=>{if(!ed.items.length)return;snap();ed.items=[];ed.sel=-1;onPick(ed);changed();};
  ed.reset=()=>{ed.items=[];ed.sel=-1;hist.length=0;gest=null;ptrs.clear();};
  ed.canUndo=()=>hist.length>0;
  ed.draw=draw;
  // w is in the canvas's own pixels: whatever transform the strip's painter left behind (drawPrint keeps its ×scale) is dropped
  ed.compose=(c,w)=>{if(!ed.items.length)return;c.save();c.setTransform(1,0,0,1,0,0);paint(c,w,{sprites:0,box:false});c.restore();};
  return ed;
}
