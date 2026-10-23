/** 🔍 Phóng to, thu nhỏ căn phòng (v4/reno.js): two fingers pinch, the mouse wheel zooms where it points, ＋ / － / ⤢
 * buttons; zoomed in, one finger (or the mouse) on the room pans it. One CSS transform on the room's frame (.dc-zoom):
 * the SVG keeps its own coordinates (getScreenCTM follows the transform, so taps, drags and the cells still land where
 * they point) and nothing is redrawn while zooming. A redraw writes the same transform back (style()), so it never
 * jumps. The zoom is the viewer's own: nothing is sent or saved. */
export const ZMIN=1,ZMAX=3,STEP=1.35;

export function zoomer(){
  const Z={k:1,x:0,y:0,pts:new Map(),pinch:null,pan:null,moved:false};
  const frameOf=root=>root?.querySelector?.('.dc-zoom')||null;
  /** Keep the room covering its box: no empty band at an edge. */
  function fit(f){
    const w=f?.offsetWidth||0,h=f?.offsetHeight||0;
    if(Z.k<=1.001){Z.k=1;Z.x=0;Z.y=0;return;}
    Z.x=Math.min(0,Math.max(w-w*Z.k,Z.x));Z.y=Math.min(0,Math.max(h-h*Z.k,Z.y));
  }
  const css=()=>Z.k===1?'':`translate(${Z.x.toFixed(1)}px,${Z.y.toFixed(1)}px) scale(${Z.k.toFixed(3)})`;
  /** The frame's style attribute for a redraw. */
  const style=()=>Z.k===1?'':` style="transform:${css()}"`;
  function apply(root){
    const f=frameOf(root);if(!f)return;fit(f);
    f.style.transform=css();
    const wrap=f.parentElement;wrap?.classList.toggle('zoomed',Z.k>1);
    const pct=wrap?.querySelector?.('.dc-zoom-pct');if(pct)pct.textContent=`${Math.round(Z.k*100)}%`;
    for(const b of wrap?.querySelectorAll?.('[data-dc="zoom"]')||[]){const z=b.dataset.z;b.disabled=z==='in'?Z.k>=ZMAX:Z.k<=ZMIN;}
  }
  /** Zoom to `k` keeping the point under (cx, cy) (screen pixels) where it is; no point: the middle of the room. */
  function zoomAt(root,k,cx,cy){
    const f=frameOf(root);if(!f)return;
    const r=f.parentElement.getBoundingClientRect(),px=(cx??r.left+r.width/2)-r.left,py=(cy??r.top+r.height/2)-r.top;
    k=Math.max(ZMIN,Math.min(ZMAX,k));
    const u=(px-Z.x)/Z.k,v=(py-Z.y)/Z.k;Z.k=k;Z.x=px-u*k;Z.y=py-v*k;
    apply(root);
  }
  /** ＋ / － / ⤢ */
  function button(root,z){if(z==='fit')zoomAt(root,1);else zoomAt(root,z==='in'?Z.k*STEP:Z.k/STEP);}
  /** The wheel over the room: up zooms in where the mouse is; down zooms out, and at full view the page scrolls on. */
  function wheel(root,e){
    if(e.deltaY>0&&Z.k<=ZMIN)return false;
    e.preventDefault();zoomAt(root,Z.k*Math.exp(-Math.max(-60,Math.min(60,e.deltaY))*.004),e.clientX,e.clientY);return true;
  }
  const two=()=>[...Z.pts.values()].slice(0,2);
  const mid=([a,b])=>[(a[0]+b[0])/2,(a[1]+b[1])/2],gap=([a,b])=>Math.hypot(a[0]-b[0],a[1]-b[1])||1;
  /** A finger (or the mouse) down on the room: true when it starts a pinch (the second finger). */
  function down(root,e){
    if(e.pointerType==='mouse'&&e.button>0)return false;
    if(e.isPrimary)Z.pts.clear();   // a new gesture: a finger lost by the browser is not still down
    Z.pts.set(e.pointerId,[e.clientX,e.clientY]);
    if(Z.pts.size===2){
      const p=two(),r=frameOf(root)?.parentElement?.getBoundingClientRect();if(!r)return false;
      const m=mid(p);Z.pinch={k:Z.k,d:gap(p),u:(m[0]-r.left-Z.x)/Z.k,v:(m[1]-r.top-Z.y)/Z.k};Z.pan=null;Z.moved=true;
      frameOf(root)?.classList.add('moving');return true;
    }
    return false;
  }
  /** One finger dragging the zoomed-in room. */
  function panFrom(root,cx,cy){if(Z.k<=1||Z.pinch)return false;Z.pan={cx,cy,x:Z.x,y:Z.y};Z.moved=true;frameOf(root)?.classList.add('moving');return true;}
  /** A pointer moved: true when the zoom used it (a pinch or a pan). */
  function move(root,e){
    if(!Z.pts.has(e.pointerId))return false;
    Z.pts.set(e.pointerId,[e.clientX,e.clientY]);
    if(Z.pinch&&Z.pts.size>=2){
      const p=two(),r=frameOf(root)?.parentElement?.getBoundingClientRect();if(!r)return true;
      const m=mid(p),k=Math.max(ZMIN,Math.min(ZMAX,Z.pinch.k*gap(p)/Z.pinch.d));
      Z.k=k;Z.x=m[0]-r.left-Z.pinch.u*k;Z.y=m[1]-r.top-Z.pinch.v*k;apply(root);return true;
    }
    if(Z.pan){Z.x=Z.pan.x+e.clientX-Z.pan.cx;Z.y=Z.pan.y+e.clientY-Z.pan.cy;apply(root);return true;}
    return false;
  }
  /** A pointer up or cancelled: true when it ended a pinch or a pan (not a tap). */
  function up(root,e){
    const had=Z.pts.delete(e.pointerId),was=!!(Z.pinch||Z.pan);
    if(Z.pts.size<2)Z.pinch=null;
    if(!Z.pts.size){Z.pan=null;frameOf(root)?.classList.remove('moving');}
    return had&&was;
  }
  const busy=()=>!!(Z.pinch||Z.pan);
  function reset(root){Z.k=1;Z.x=0;Z.y=0;Z.pts.clear();Z.pinch=null;Z.pan=null;if(root)apply(root);}
  /** ＋ － ⤢ over the room's corner (buttons: a screen reader and a keyboard zoom too). */
  function controls(btn){
    return `<div class="dc-zoombar" role="group" aria-label="Phóng to, thu nhỏ căn phòng">${btn('－','zoom',{z:'out'},'ghost small',` aria-label="Thu nhỏ căn phòng"${Z.k<=ZMIN?' disabled':''}`)}`
      +`<span class="dc-zoom-pct" aria-hidden="true">${Math.round(Z.k*100)}%</span>${btn('＋','zoom',{z:'in'},'ghost small',` aria-label="Phóng to căn phòng"${Z.k>=ZMAX?' disabled':''}`)}`
      +`${btn('⤢','zoom',{z:'fit'},'ghost small',' aria-label="Xem cả phòng"')}</div>`;
  }
  return {style,apply,zoomAt,button,wheel,down,move,up,panFrom,busy,reset,controls,get k(){return Z.k;},get pinching(){return !!Z.pinch;}};
}
