/** 🎨 The sticker maker of /sticker (public/sticker.html, game/sticker_event.py): one 512x512 canvas, transparent by
 * default, made of layers drawn in order: photos (resized on the device, round / rounded crop, "xóa nền" by flood fill
 * from the edges), text (font, colour, outline), emoji and simple shapes, brush and eraser strokes. Layers move with a
 * finger or the mouse, the corner handle (or two fingers) scales and turns them. Undo / redo keep 60 steps.
 * The account's @username is a layer of its own, always on top: it moves (kept inside the canvas) and grows, but can
 * not be deleted or hidden, so every exported sticker carries it (the server keeps the author too).
 * Nothing leaves the device until the page exports the image (PNG, or WebP when the PNG is over the limit). */

export const SIZE=512;
const HISTORY=60,HANDLE=30,MAX_SRC=1024;
export const FONTS={
  bvp:['Đậm','800 {s}px "Be Vietnam Pro", system-ui, sans-serif'],
  thin:['Mảnh','400 {s}px "Be Vietnam Pro", system-ui, sans-serif'],
  serif:['Có chân','700 {s}px Georgia, "Times New Roman", serif'],
  hand:['Viết tay','700 {s}px "Comic Sans MS", "Chalkboard SE", "Segoe Print", cursive'],
  mono:['Máy chữ','700 {s}px ui-monospace, "Courier New", monospace'],
};
export const SHAPES={bubble:'💬 Bong bóng',heart:'❤️ Tim',star:'⭐ Sao',burst:'💥 Nổ',circle:'⚪ Tròn'};
const font=(f,s)=>(FONTS[f]||FONTS.bvp)[1].replace('{s}',String(Math.round(s)));
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const blank=()=>{const c=document.createElement('canvas');c.width=c.height=SIZE;return c;};

/** A layer's local point (its centre at 0,0, unscaled) for a canvas point. */
function local(l,px,py){const dx=px-l.x,dy=py-l.y,c=Math.cos(-l.rot),s=Math.sin(-l.rot);return [(dx*c-dy*s)/l.s,(dx*s+dy*c)/l.s];}
function corner(l){const c=Math.cos(l.rot),s=Math.sin(l.rot),hx=l.w/2*l.s,hy=l.h/2*l.s;return [l.x+hx*c-hy*s,l.y+hx*s+hy*c];}

const measurer=document.createElement('canvas').getContext('2d');
function measureText(l){
  measurer.font=font(l.font,l.size);
  const lines=String(l.text||' ').split('\n'),lh=l.size*1.18;
  l.w=Math.max(20,...lines.map(t=>measurer.measureText(t||' ').width))+l.ow*2+8;l.h=lines.length*lh+l.ow*2+6;
}

function shapePath(ctx,kind,w,h){
  const x=-w/2,y=-h/2;ctx.beginPath();
  if(kind==='circle'){ctx.ellipse(0,0,w/2,h/2,0,0,Math.PI*2);return;}
  if(kind==='heart'){
    ctx.moveTo(0,y+h*.3);ctx.bezierCurveTo(0,y+h*.05,x,y,x,y+h*.32);ctx.bezierCurveTo(x,y+h*.6,0,y+h*.75,0,y+h);
    ctx.bezierCurveTo(0,y+h*.75,-x,y+h*.6,-x,y+h*.32);ctx.bezierCurveTo(-x,y,0,y+h*.05,0,y+h*.3);ctx.closePath();return;}
  if(kind==='star'||kind==='burst'){
    const n=kind==='star'?5:12,ro=1,ri=kind==='star'?.45:.72;
    for(let i=0;i<n*2;i++){const r=i%2?ri:ro,a=-Math.PI/2+i*Math.PI/n;ctx[i?'lineTo':'moveTo'](Math.cos(a)*r*w/2,Math.sin(a)*r*h/2);}
    ctx.closePath();return;}
  // bubble: a rounded box with a tail at the bottom left
  const bh=h*.78,r=Math.min(w,bh)*.28;
  ctx.moveTo(x+r,y);ctx.lineTo(x+w-r,y);ctx.quadraticCurveTo(x+w,y,x+w,y+r);ctx.lineTo(x+w,y+bh-r);ctx.quadraticCurveTo(x+w,y+bh,x+w-r,y+bh);
  ctx.lineTo(x+w*.42,y+bh);ctx.lineTo(x+w*.18,y+h);ctx.lineTo(x+w*.24,y+bh);ctx.lineTo(x+r,y+bh);ctx.quadraticCurveTo(x,y+bh,x,y+bh-r);
  ctx.lineTo(x,y+r);ctx.quadraticCurveTo(x,y,x+r,y);ctx.closePath();
}

function drawLayer(ctx,l){
  if(l.type==='path'){
    if(!l.pts.length)return;
    ctx.save();ctx.globalCompositeOperation=l.erase?'destination-out':'source-over';
    ctx.strokeStyle=l.color;ctx.fillStyle=l.color;ctx.lineWidth=l.size;ctx.lineCap='round';ctx.lineJoin='round';
    if(l.pts.length===1){ctx.beginPath();ctx.arc(l.pts[0][0],l.pts[0][1],l.size/2,0,Math.PI*2);ctx.fill();}
    else{ctx.beginPath();ctx.moveTo(l.pts[0][0],l.pts[0][1]);
      for(let i=1;i<l.pts.length-1;i++){const [x0,y0]=l.pts[i],[x1,y1]=l.pts[i+1];ctx.quadraticCurveTo(x0,y0,(x0+x1)/2,(y0+y1)/2);}
      const e=l.pts[l.pts.length-1];ctx.lineTo(e[0],e[1]);ctx.stroke();}
    ctx.restore();return;
  }
  ctx.save();ctx.translate(l.x,l.y);ctx.rotate(l.rot);ctx.scale(l.s,l.s);
  if(l.type==='image'){
    if(l.flip)ctx.scale(-1,1);
    if(l.mask==='circle'){ctx.beginPath();ctx.ellipse(0,0,l.w/2,l.h/2,0,0,Math.PI*2);ctx.clip();}
    else if(l.mask==='round'){const r=Math.min(l.w,l.h)*.18,x=-l.w/2,y=-l.h/2;ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+l.w,y,x+l.w,y+l.h,r);ctx.arcTo(x+l.w,y+l.h,x,y+l.h,r);ctx.arcTo(x,y+l.h,x,y,r);ctx.arcTo(x,y,x+l.w,y,r);ctx.closePath();ctx.clip();}
    ctx.drawImage(l.src,-l.w/2,-l.h/2,l.w,l.h);
  }else if(l.type==='text'){
    ctx.font=font(l.font,l.size);ctx.textAlign='center';ctx.textBaseline='middle';ctx.lineJoin='round';ctx.miterLimit=2;
    const lines=String(l.text).split('\n'),lh=l.size*1.18,top=-(lines.length-1)*lh/2;
    lines.forEach((t,i)=>{if(l.ow>0){ctx.lineWidth=l.ow*2;ctx.strokeStyle=l.outline;ctx.strokeText(t,0,top+i*lh);}ctx.fillStyle=l.color;ctx.fillText(t,0,top+i*lh);});
  }else if(l.type==='emoji'){
    ctx.font=`${l.size}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(l.ch,0,l.size*.06);
  }else if(l.type==='shape'){
    shapePath(ctx,l.kind,l.w,l.h);ctx.fillStyle=l.color;ctx.fill();
    if(l.ow>0){ctx.lineWidth=l.ow;ctx.strokeStyle=l.outline;ctx.lineJoin='round';ctx.stroke();}
  }
  ctx.restore();
}

/** The @username badge: a white pill, dark text, always legible. */
function stampMeasure(st){
  measurer.font=font('bvp',22*st.s);
  st.w=measurer.measureText(st.text).width+28*st.s;st.h=40*st.s;
  st.x=clamp(st.x,st.w/2+2,SIZE-st.w/2-2);st.y=clamp(st.y,st.h/2+2,SIZE-st.h/2-2);
}
function drawStamp(ctx,st){
  stampMeasure(st);
  const x=st.x-st.w/2,y=st.y-st.h/2,r=st.h/2;
  ctx.save();ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+st.w,y,x+st.w,y+st.h,r);ctx.arcTo(x+st.w,y+st.h,x,y+st.h,r);ctx.arcTo(x,y+st.h,x,y,r);ctx.arcTo(x,y,x+st.w,y,r);ctx.closePath();
  ctx.fillStyle=st.dark?'rgba(43,30,24,.92)':'rgba(255,255,255,.94)';ctx.fill();ctx.lineWidth=2*st.s;ctx.strokeStyle=st.dark?'rgba(255,255,255,.5)':'rgba(43,30,24,.35)';ctx.stroke();
  ctx.font=font('bvp',22*st.s);ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=st.dark?'#fff':'#2b1e18';ctx.fillText(st.text,st.x,st.y+1*st.s);
  ctx.restore();
}

/** A white (or coloured) outline around everything drawn: the art drawn shifted around a circle, filled flat. */
function outlined(art,px,color){
  const out=blank(),o=out.getContext('2d');
  for(const r of [px,px*.55])for(let i=0;i<24;i++){const a=i*Math.PI/12;o.drawImage(art,Math.cos(a)*r,Math.sin(a)*r);}
  o.globalCompositeOperation='source-in';o.fillStyle=color;o.fillRect(0,0,SIZE,SIZE);
  o.globalCompositeOperation='source-over';o.drawImage(art,0,0);
  return out;
}

/** Pixels similar to the edges' colour, reached from the edges, become transparent (a plain photo background). */
function removeBackground(src,tol=46){
  const c=document.createElement('canvas');c.width=src.width;c.height=src.height;
  const g=c.getContext('2d',{willReadFrequently:true});g.drawImage(src,0,0);
  const W=c.width,H=c.height,img=g.getImageData(0,0,W,H),d=img.data,seen=new Uint8Array(W*H),stack=[];
  const corners=[[0,0],[W-1,0],[0,H-1],[W-1,H-1]].map(([x,y])=>(y*W+x)*4);
  const ref=[0,1,2].map(k=>corners.reduce((a,i)=>a+d[i+k],0)/4),t2=tol*tol;
  const near=i=>{const dr=d[i]-ref[0],dg=d[i+1]-ref[1],db=d[i+2]-ref[2];return d[i+3]<16||dr*dr+dg*dg+db*db<=t2*3;};
  const push=p=>{if(!seen[p]&&near(p*4)){seen[p]=1;stack.push(p);}};
  for(let x=0;x<W;x++){push(x);push((H-1)*W+x);}for(let y=0;y<H;y++){push(y*W);push(y*W+W-1);}
  let n=0;
  while(stack.length){const p=stack.pop(),x=p%W;d[p*4+3]=0;n++;
    if(x>0)push(p-1);if(x<W-1)push(p+1);if(p>=W)push(p-W);if(p<W*(H-1))push(p+W);}
  g.putImageData(img,0,0);
  return {canvas:c,share:n/(W*H)};
}

export async function loadPicture(file){
  if(!file||!/^image\//.test(file.type||'image/'))throw new Error('Chọn một tấm ảnh nhé.');
  if(file.size>25*1024*1024)throw new Error('Ảnh lớn quá (tối đa 25 MB).');
  let bmp;
  try{bmp=await createImageBitmap(file,{imageOrientation:'from-image'});}
  catch{bmp=await new Promise((ok,no)=>{const u=URL.createObjectURL(file),im=new Image();im.onload=()=>{URL.revokeObjectURL(u);ok(im);};im.onerror=()=>{URL.revokeObjectURL(u);no(new Error('Không mở được ảnh này. Thử ảnh JPG hoặc PNG nhé.'));};im.src=u;});}
  const w=bmp.width||bmp.naturalWidth,h=bmp.height||bmp.naturalHeight,k=Math.min(1,MAX_SRC/Math.max(w,h));
  const c=document.createElement('canvas');c.width=Math.max(1,Math.round(w*k));c.height=Math.max(1,Math.round(h*k));
  c.getContext('2d').drawImage(bmp,0,0,c.width,c.height);bmp.close?.();
  return c;
}

export function createEditor(canvas,{onChange=()=>{}}={}){
  canvas.width=canvas.height=SIZE;
  const ctx=canvas.getContext('2d');
  let layers=[],sel=null,tool='move',brush={color:'#ff4d6d',size:14},bg=null,border=true,borderColor='#ffffff',busy=false;
  const stamp={type:'stamp',text:'@ban',x:SIZE-120,y:SIZE-34,s:1,rot:0,w:0,h:0,dark:false};
  let past=[],future=[],lastKey='',lastAt=0;
  const pointers=new Map();let drag=null,raf=0;

  const snap=()=>({layers:layers.map(l=>({...l,pts:l.pts?l.pts.slice():undefined})),stamp:{...stamp},bg,border,borderColor,sel:sel===stamp?'stamp':layers.indexOf(sel)});
  const restore=s=>{layers=s.layers;Object.assign(stamp,s.stamp);bg=s.bg;border=s.border;borderColor=s.borderColor;sel=s.sel==='stamp'?stamp:layers[s.sel]||null;};
  /** Remember the state before a change; the same `key` within a second is one step (a slider being dragged). */
  function checkpoint(key=''){
    const t=performance.now();
    if(key&&key===lastKey&&t-lastAt<1000){lastAt=t;return;}
    past.push(snap());if(past.length>HISTORY)past.shift();future=[];lastKey=key;lastAt=t;
  }
  const changed=()=>{draw();onChange(api);};

  function art(){
    const a=blank(),g=a.getContext('2d');
    for(const l of layers)drawLayer(g,l);
    return a;
  }
  function compose(target,{ui=false,quick=false}={}){
    const g=target.getContext('2d');g.clearRect(0,0,SIZE,SIZE);
    if(bg){g.fillStyle=bg;g.fillRect(0,0,SIZE,SIZE);}
    let a=art();
    if(border&&!bg&&!quick&&layers.length)a=outlined(a,9,borderColor);
    g.drawImage(a,0,0);
    drawStamp(g,stamp);
    if(ui&&sel)drawSelection(g,sel);
  }
  function drawSelection(g,l){
    g.save();
    if(l===stamp){g.setLineDash([6,5]);g.strokeStyle='#2f80ed';g.lineWidth=2;g.strokeRect(l.x-l.w/2-4,l.y-l.h/2-4,l.w+8,l.h+8);g.restore();return;}
    g.translate(l.x,l.y);g.rotate(l.rot);
    const w=l.w*l.s,h=l.h*l.s;
    g.setLineDash([8,6]);g.lineWidth=2;g.strokeStyle='rgba(255,255,255,.9)';g.strokeRect(-w/2,-h/2,w,h);g.lineDashOffset=7;g.strokeStyle='#2f80ed';g.strokeRect(-w/2,-h/2,w,h);
    g.setLineDash([]);g.beginPath();g.arc(w/2,h/2,HANDLE/2,0,Math.PI*2);g.fillStyle='#2f80ed';g.fill();g.lineWidth=3;g.strokeStyle='#fff';g.stroke();
    g.fillStyle='#fff';g.font='bold 18px system-ui,sans-serif';g.textAlign='center';g.textBaseline='middle';g.fillText('⤡',w/2,h/2+1);
    g.restore();
  }
  function draw(quick=false){compose(canvas,{ui:true,quick});}
  const schedule=()=>{if(raf)return;raf=requestAnimationFrame(()=>{raf=0;draw(Boolean(drag));});};

  // ---- pointer input -----------------------------------------------------------------------------
  const pos=e=>{const r=canvas.getBoundingClientRect();return [(e.clientX-r.left)*SIZE/r.width,(e.clientY-r.top)*SIZE/r.height];};
  const hit=(x,y)=>{
    stampMeasure(stamp);
    if(Math.abs(x-stamp.x)<=stamp.w/2+6&&Math.abs(y-stamp.y)<=stamp.h/2+6)return stamp;
    for(let i=layers.length-1;i>=0;i--){const l=layers[i];if(l.type==='path')continue;const [lx,ly]=local(l,x,y);if(Math.abs(lx)<=l.w/2+8/l.s&&Math.abs(ly)<=l.h/2+8/l.s)return l;}
    return null;
  };
  function down(e){
    if(busy)return;
    canvas.setPointerCapture?.(e.pointerId);
    const [x,y]=pos(e);pointers.set(e.pointerId,[x,y]);
    if(pointers.size===2&&sel&&sel!==stamp&&(tool==='move'||drag?.mode==='move')){
      const [a,b]=[...pointers.values()];
      if(drag?.mode==='path'){layers.pop();past.pop();}
      drag={mode:'pinch',d0:Math.hypot(b[0]-a[0],b[1]-a[1])||1,a0:Math.atan2(b[1]-a[1],b[0]-a[0]),s0:sel.s,r0:sel.rot,moved:false};return;
    }
    if(pointers.size>1)return;
    if(tool==='draw'||tool==='erase'){
      checkpoint();
      const l={type:'path',pts:[[x,y]],color:brush.color,size:tool==='erase'?brush.size*1.6:brush.size,erase:tool==='erase'};
      layers.push(l);drag={mode:'path',l};schedule();return;
    }
    if(sel&&sel!==stamp){const [cx,cy]=corner(sel);if(Math.hypot(x-cx,y-cy)<=HANDLE*.9){drag={mode:'handle',d0:Math.hypot(x-sel.x,y-sel.y)||1,a0:Math.atan2(y-sel.y,x-sel.x),s0:sel.s,r0:sel.rot,moved:false};return;}}
    const l=hit(x,y);
    if(l!==sel){sel=l;onChange(api);}
    drag=l?{mode:'move',dx:x-l.x,dy:y-l.y,moved:false}:null;
    schedule();
  }
  function move(e){
    if(!pointers.has(e.pointerId)||!drag)return;
    const [x,y]=pos(e);pointers.set(e.pointerId,[x,y]);
    if(drag.mode==='path'){const p=drag.l.pts,last=p[p.length-1];if(Math.hypot(x-last[0],y-last[1])>=1.5)p.push([x,y]);schedule();return;}
    if(!drag.moved){checkpoint();drag.moved=true;}
    if(drag.mode==='move'&&sel){
      sel.x=clamp(x-drag.dx,-SIZE*.25,SIZE*1.25);sel.y=clamp(y-drag.dy,-SIZE*.25,SIZE*1.25);
      if(sel===stamp)stampMeasure(stamp);
    }else if(drag.mode==='handle'&&sel){
      sel.s=clamp(drag.s0*Math.hypot(x-sel.x,y-sel.y)/drag.d0,.08,12);sel.rot=drag.r0+Math.atan2(y-sel.y,x-sel.x)-drag.a0;
    }else if(drag.mode==='pinch'&&sel&&pointers.size>=2){
      const [a,b]=[...pointers.values()];
      sel.s=clamp(drag.s0*Math.hypot(b[0]-a[0],b[1]-a[1])/drag.d0,.08,12);sel.rot=drag.r0+Math.atan2(b[1]-a[1],b[0]-a[0])-drag.a0;
    }
    schedule();
  }
  function up(e){
    if(!pointers.delete(e.pointerId))return;
    if(drag?.mode==='pinch'&&pointers.size===1){drag=null;return;}   // the second finger left: wait for the first
    if(pointers.size)return;
    const was=drag;drag=null;
    if(was&&(was.mode==='path'||was.moved)){if(sel&&Math.abs(sel.rot)<.06)sel.rot=0;changed();}else draw();
  }
  canvas.addEventListener('pointerdown',down);
  canvas.addEventListener('pointermove',move);
  canvas.addEventListener('pointerup',up);
  canvas.addEventListener('pointercancel',up);
  canvas.addEventListener('lostpointercapture',up);

  // ---- the API the page uses -------------------------------------------------------------------
  const center=()=>[SIZE/2+(Math.random()-.5)*40,SIZE/2+(Math.random()-.5)*40];
  function add(l){checkpoint();layers.push(l);sel=l;tool='move';changed();return l;}
  const api={
    get tool(){return tool;},
    get selected(){return sel;},
    get brush(){return brush;},
    get background(){return bg;},
    get border(){return border;},
    get canUndo(){return past.length>0;},
    get canRedo(){return future.length>0;},
    get empty(){return !layers.some(l=>l.type!=='path'||!l.erase);},
    get stamp(){return stamp;},
    setTool(t){tool=t;if(t==='draw'||t==='erase'){sel=null;}draw();onChange(api);},
    setBrush(b){Object.assign(brush,b);onChange(api);},
    setStamp({text,dark}){if(text!=null)stamp.text=text;if(dark!=null)stamp.dark=dark;stampMeasure(stamp);draw();},
    setBackground(c){checkpoint();bg=c||null;changed();},
    setBorder(on,color){checkpoint();border=Boolean(on);if(color)borderColor=color;changed();},
    addText(o){const [x,y]=center();const l={type:'text',text:o.text||'Chữ',font:o.font||'bvp',size:72,color:o.color||'#ffffff',outline:o.outline||'#2b1e18',ow:o.ow??6,x,y,s:1,rot:0,w:0,h:0};measureText(l);if(l.w>SIZE*.9)l.s=SIZE*.9/l.w;return add(l);},
    addEmoji(ch){const [x,y]=center();return add({type:'emoji',ch,size:140,x,y,s:1,rot:0,w:150,h:150});},
    addShape(kind,color){const [x,y]=center();return add({type:'shape',kind,color:color||'#ffffff',outline:'#2b1e18',ow:6,x,y,s:1,rot:0,w:kind==='bubble'?260:200,h:kind==='bubble'?190:200});},
    addPicture(src){const k=Math.min(SIZE*.86/src.width,SIZE*.86/src.height);return add({type:'image',src,w:src.width,h:src.height,x:SIZE/2,y:SIZE/2,s:k,rot:0,mask:'none',flip:false});},
    /** Change the selected layer; `key` merges a slider's steps into one undo step. */
    update(props,key='edit'){
      if(!sel)return;checkpoint(key+':'+(sel===stamp?'stamp':layers.indexOf(sel)));
      if(sel===stamp){if(props.s!=null)stamp.s=clamp(props.s,.8,2.2);if(props.dark!=null)stamp.dark=props.dark;stampMeasure(stamp);}
      else{Object.assign(sel,props);if(sel.type==='text')measureText(sel);}
      changed();
    },
    removeBackground(){
      if(sel?.type!=='image')return 0;
      busy=true;
      try{const {canvas:c,share}=removeBackground(sel.src);checkpoint();sel.src=c;changed();return share;}
      finally{busy=false;}
    },
    remove(){if(!sel||sel===stamp)return;checkpoint();layers.splice(layers.indexOf(sel),1);sel=null;changed();},
    duplicate(){if(!sel||sel===stamp)return;const c={...sel,x:sel.x+24,y:sel.y+24};add(c);},
    order(dir){
      if(!sel||sel===stamp)return;const i=layers.indexOf(sel),j=dir>0?layers.length-1:0;
      if(i===j)return;checkpoint();layers.splice(i,1);layers.splice(dir>0?layers.length:0,0,sel);changed();
    },
    deselect(){sel=null;draw();onChange(api);},
    selectStamp(){sel=stamp;tool='move';draw();onChange(api);},
    clear(){if(!layers.length&&!bg)return;checkpoint();layers=[];bg=null;sel=null;changed();},
    undo(){if(!past.length)return;future.push(snap());restore(past.pop());lastKey='';changed();},
    redo(){if(!future.length)return;past.push(snap());restore(future.pop());lastKey='';changed();},
    redraw(){if(sel?.type==='text')measureText(sel);for(const l of layers)if(l.type==='text')measureText(l);draw();},
    /** The finished sticker, without the selection box: {blob, type}. PNG first; WebP when the PNG is over `max`. */
    async export(max=Infinity){
      const out=blank();compose(out);
      const blob=(type,q)=>new Promise(ok=>out.toBlob(b=>ok(b),type,q));
      const png=await blob('image/png');
      if(png&&png.size<=max)return {blob:png,type:'image/png'};
      for(const q of [.92,.85,.75,.6]){const w=await blob('image/webp',q);if(w&&w.type==='image/webp'&&w.size<=max)return {blob:w,type:'image/webp'};if(!w||w.type!=='image/webp')break;}
      return {blob:png,type:'image/png',tooBig:true};
    },
    async png(){const out=blank();compose(out);return new Promise(ok=>out.toBlob(b=>ok(b),'image/png'));},
  };
  draw();
  return api;
}
