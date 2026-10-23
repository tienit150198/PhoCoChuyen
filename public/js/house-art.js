/** 🏡 Kiểu nhà: the house styles of the private islands (game/island_build_content.py HOUSES, owner 20/10 "đảo có thể
 * xây nhà các kiểu đẹp và nhiều hơn") and the bang hall styles (game/bang_extra_content.py HALL_STYLES), as small 3D
 * models any 2.5D view can paint. Pure: no DOM, no canvas, no Phaser.
 *
 * A model is a list of parts in local map units around the plot's middle (x east, y south; a plot is .072 wide) and
 * heights z in pixels at the private island's scale. Each part is a few primitives: boxes, roofs (hip, gable, pyramid,
 * frustum), cylinders, cones, domes, wall panels (windows, doors), posts, balls (lanterns, leaves) and flat shapes.
 * paintHouse(id, level, variant, view) draws one; `view` is the renderer's adapter:
 *   P(x, y, z) → [px, py]           the projection of a local point (the caller adds the plot's middle and its scale)
 *   fill(points, '#rrggbb', alpha)  a filled polygon of projected points
 *   circle(px, py, r, color, alpha) a disc (r in pixels)
 *   line(a, b, color, width)        a segment between projected points (width in pixels)
 *   zs                              pixels per z unit (balls and lines scale with it)
 *   depth(x, y)                     the draw order of a ground point (larger: nearer the viewer): x + y on an
 *                                   isometric view, y on the old interface's three-quarter view
 *   light?(nx, ny, nz)              optional: the brightness of a face by its outward normal (default: the sun in
 *                                   the south-east, like client/isometric/island-builds.ts prism())
 * Faces are culled by their winding on screen (only those turned to the viewer are drawn), so one model serves the
 * isometric view (new interface, the build sheet's preview, the bang island) and the old front view alike.
 * Parts are drawn back to front by their anchor's depth, then in the order written. Never rename a style id: they
 * are stored in saves (with a colour suffix: splitKind) and in island_builds / bang_facilities. */

const W=600;   // map units → pixels, for the normals only (heights are pixels)
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export function shade(hex,k){
  const n=parseInt(String(hex).slice(1),16);if(!Number.isFinite(n))return hex;
  const c=v=>clamp(Math.round(v*k),0,255).toString(16).padStart(2,'0');
  return '#'+c((n>>16)&255)+c((n>>8)&255)+c(n&255);
}
export const isoLight=(nx,ny,nz)=>clamp(.8+.2*nx+.05*ny+.3*nz,.62,1.16);

/* ---- the model builder ---------------------------------------------------------------------------------------- */
function builder(){
  const parts=[],ground={at:null,items:[]};let cur=ground,top=0;
  const up=z=>{if(z>top)top=z;};
  const face=(pts,color,alpha=1)=>{for(const p of pts)up(p[2]);cur.items.push({t:'f',pts,color,alpha});};
  const h={
    /** A new part anchored at (x, y): drawn after the parts behind it. */
    part(x,y){cur={at:[x,y],items:[]};parts.push(cur);return h;},
    /** Flat on the ground under everything (a yard, a lawn, a pool). */
    ground(x,y,hx,hy,color,alpha=1){const keep=cur;cur=ground;h.quad(x,y,hx,hy,.3,color,alpha);cur=keep;return h;},
    quad(x,y,hx,hy,z,color,alpha=1){face([[x-hx,y-hy,z],[x+hx,y-hy,z],[x+hx,y+hy,z],[x-hx,y+hy,z]],color,alpha);return h;},
    face(pts,color,alpha=1){face(pts,color,alpha);return h;},
    /** An upright prism over a convex base (points in map order NW → NE → SE → SW, clockwise from above). */
    prism(base,z0,z1,wall,topColor){
      const n=base.length;
      for(let i=0;i<n;i++){const [ax,ay]=base[i],[bx,by]=base[(i+1)%n];face([[ax,ay,z0],[bx,by,z0],[bx,by,z1],[ax,ay,z1]],wall);}
      if(topColor!==null)face(base.map(([x,y])=>[x,y,z1]),topColor||wall);
      return h;
    },
    box(x,y,hx,hy,z0,z1,wall,topColor){return h.prism([[x-hx,y-hy],[x+hx,y-hy],[x+hx,y+hy],[x-hx,y+hy]],z0,z1,wall,topColor===undefined?shade(wall,1.04):topColor);},
    /** A roof from a base ring (at z) to a top ring (each top point above its base corner; equal points merge). */
    shell(base,tops,color,cap){
      const n=base.length,same=(a,b)=>Math.abs(a[0]-b[0])<1e-9&&Math.abs(a[1]-b[1])<1e-9&&Math.abs(a[2]-b[2])<1e-9;
      for(let i=0;i<n;i++){const j=(i+1)%n,pts=[base[i],base[j],tops[j],tops[i]].filter((p,k,a)=>!same(p,a[(k+3)%4]));
        if(pts.length>=3)face(pts,color);}
      if(cap)face(tops,cap);
      return h;
    },
    /** Roofs over the rectangle (grown by `over`) at height z, `ht` high. type: hip | gable | pyramid; axis: the
     * ridge's direction ('x' east–west, 'y' north–south); ridge: how much of the length it runs (hip). `ends`: the
     * gable ends' colour. */
    roof(x,y,hx,hy,z,ht,color,o={}){
      const ov=o.over??.004,X=hx+ov,Y=hy+ov,type=o.type||'hip',axis=o.axis||(hx>=hy?'x':'y');
      const base=[[x-X,y-Y,z],[x+X,y-Y,z],[x+X,y+Y,z],[x-X,y+Y,z]];
      let r;
      if(type==='pyramid')r=Array(4).fill([x,y,z+ht]);
      else if(axis==='x'){const rx=type==='gable'?X:Math.max(0,X-Y*(o.ridge??1));r=[[x-rx,y,z+ht],[x+rx,y,z+ht],[x+rx,y,z+ht],[x-rx,y,z+ht]];}
      else{const ry=type==='gable'?Y:Math.max(0,Y-X*(o.ridge??1));r=[[x,y-ry,z+ht],[x,y-ry,z+ht],[x,y+ry,z+ht],[x,y+ry,z+ht]];}
      if(type==='gable'&&o.ends){   // the gable ends in the wall's colour, the slopes in the roof's
        const n=4;for(let i=0;i<n;i++){const j=(i+1)%n,pts=[base[i],base[j],r[j],r[i]];
          const tri=Math.abs(r[i][0]-r[j][0])<1e-9&&Math.abs(r[i][1]-r[j][1])<1e-9;face(tri?[base[i],base[j],r[i]]:pts,tri?o.ends:color);}
      }else h.shell(base,r,color);
      if(o.tips){for(const [sx,sy] of [[-1,-1],[1,-1],[1,1],[-1,1]]){const cx=x+sx*X,cy=y+sy*Y;   // the upturned corners (đầu đao)
        h.flat([[cx,cy,z],[cx+sx*.006,cy+sy*.006,z+o.tips],[cx-sx*.003,cy-sy*.001,z+2]],o.tipColor||shade(color,1.15));}}
      return h;
    },
    /** A sloped skirt: the rectangle (grown by over) at z up to an inner rectangle at z + ht, flat on top. */
    frustum(x,y,hx,hy,ihx,ihy,z,ht,color,capColor=null){
      return h.shell([[x-hx,y-hy,z],[x+hx,y-hy,z],[x+hx,y+hy,z],[x-hx,y+hy,z]],[[x-ihx,y-ihy,z+ht],[x+ihx,y-ihy,z+ht],[x+ihx,y+ihy,z+ht],[x-ihx,y+ihy,z+ht]],color,capColor);
    },
    ring(x,y,r,n=12,rot=0){const out=[];for(let i=0;i<n;i++){const a=-Math.PI*.75+rot+i/n*Math.PI*2;out.push([x+Math.cos(a)*r,y+Math.sin(a)*r]);}return out;},
    cyl(x,y,r,z0,z1,color,n=12,cap){return h.prism(h.ring(x,y,r,n),z0,z1,color,cap===undefined?shade(color,1.05):cap);},
    cone(x,y,r,z,ht,color,n=12){const b=h.ring(x,y,r,n).map(([a,c])=>[a,c,z]);return h.shell(b,b.map(()=>[x,y,z+ht]),color);},
    dome(x,y,r,z,color,n=12){
      const steps=[[1,0],[.92,.38],[.7,.72],[.38,.93]],zr=r*W*.62;
      for(let i=0;i<steps.length;i++){const [k0,z0]=steps[i],[k1,z1]=steps[i+1]||[0,1];
        const a=h.ring(x,y,r*k0,n).map(([p,q])=>[p,q,z+zr*z0]),b=k1?h.ring(x,y,r*k1,n).map(([p,q])=>[p,q,z+zr*z1]):a.map(()=>[x,y,z+zr]);
        h.shell(a,b,shade(color,1-.05*i));}
      up(z+zr);return h;
    },
    /** A panel on one wall of the box (x, y, hx, hy): side s | e | n | w, u0..u1 along it (left to right seen from
     * outside), z0..z1 up it. Slightly out of the wall so it never fights with it. */
    panel(x,y,hx,hy,side,u0,u1,z0,z1,color,alpha=1){
      const e=.0006,L=(a,b,t)=>a+(b-a)*t;let A,B;
      if(side==='s'){const yy=y+hy+e;A=[L(x-hx,x+hx,u1),yy];B=[L(x-hx,x+hx,u0),yy];}
      else if(side==='e'){const xx=x+hx+e;A=[xx,L(y+hy,y-hy,u0)];B=[xx,L(y+hy,y-hy,u1)];}
      else if(side==='n'){const yy=y-hy-e;A=[L(x+hx,x-hx,u1),yy];B=[L(x+hx,x-hx,u0),yy];}
      else{const xx=x-hx-e;A=[xx,L(y-hy,y+hy,u0)];B=[xx,L(y-hy,y+hy,u1)];}
      if(side==='e'||side==='w')[A,B]=[B,A];
      face([[A[0],A[1],z0],[B[0],B[1],z0],[B[0],B[1],z1],[A[0],A[1],z1]],color,alpha);
      return h;
    },
    /** Rows of windows on the four walls (the hidden ones are culled): `per` a side, `floors` rows of floorH. */
    windows(x,y,hx,hy,z0,floorH,floors,per,color,o={}){
      const sides=o.sides||'snew',wd=o.w??.5,lo=o.lo??.3,hi=o.hi??.75;
      for(const s of sides)for(let f=0;f<floors;f++)for(let i=0;i<per;i++){
        if(o.skip&&s==='s'&&f===0&&i===Math.floor(per/2))continue;
        const t=(i+.5)/per,w=wd/per/2;
        h.panel(x,y,hx,hy,s,t-w,t+w,z0+f*floorH+floorH*lo,z0+f*floorH+floorH*hi,color);
        if(o.frame)h.panel(x,y,hx,hy,s,t-w*.12,t+w*.12,z0+f*floorH+floorH*lo,z0+f*floorH+floorH*hi,o.frame);
      }
      return h;
    },
    door(x,y,hx,hy,side,u,wd,ht,color,z0=0){return h.panel(x,y,hx,hy,side,u-wd/2,u+wd/2,z0,z0+ht,color);},
    post(x,y,z0,z1,w,color){cur.items.push({t:'l',a:[x,y,z0],b:[x,y,z1],w,color});up(z1);return h;},
    beam(a,b,w,color){cur.items.push({t:'l',a,b,w,color});up(Math.max(a[2],b[2]));return h;},
    ball(x,y,z,r,color,alpha=1){cur.items.push({t:'b',p:[x,y,z],r,color,alpha});up(z+r);return h;},
    flat(pts,color,alpha=1){cur.items.push({t:'p',pts,color,alpha});for(const p of pts)up(p[2]);return h;},
    tree(x,y,s=1,leaf='#4f9a4a'){h.part(x,y).post(x,y,0,18*s,3.5*s,'#7a5432');
      h.ball(x-.003*s,y,20*s,9*s,shade(leaf,.82)).ball(x+.002*s,y-.002*s,24*s,10*s,leaf).ball(x,y-.001,30*s,6*s,shade(leaf,1.22));return h;},
    palm(x,y,s=1){h.part(x,y).beam([x,y,0],[x+.004*s,y,34*s],3*s,'#8a6a40');const tx=x+.004*s,tz=34*s;
      for(let i=0;i<6;i++){const a=i/6*Math.PI*2,dx=Math.cos(a)*.012*s,dy=Math.sin(a)*.012*s;h.flat([[tx,y,tz+2],[tx+dx,y+dy,tz-6*s],[tx+dx*.8+dy*.2,y+dy*.8-dx*.2,tz-2]],i%2?'#3f8a3e':'#4fa04a');}
      return h;},
    bush(x,y,r,color='#5aa94e'){h.part(x,y).ball(x,y,r*.7,r,color).ball(x+.002,y-.002,r,r*.6,shade(color,1.2));return h;},
    lantern(x,y,z,color='#e5484d',lit=true){h.post(x,y,z+5,z+8,1,'#3a2a1a');h.ball(x,y,z+2,3.2,color);if(lit)h.ball(x,y,z+2,1.6,'#ffe7a0',.9);return h;},
    get top(){return top;},
    parts,base:ground,
  };
  return h;
}

/** 🏝️ A model drawn by `draw(h)` with this builder ({parts, ground, top}): the island decorations
 * (public/js/island-decor-art.js) use the same parts as the houses. */
export function modelOf(draw){const h=builder();draw(h);return {parts:h.parts,ground:h.base,top:h.top};}
/** Paint a model of modelOf() through a view (see the top of this file). */
export function paintModelVia(m,view,only=''){paintModel(m,view,only);}

/* ---- the styles ------------------------------------------------------------------------------------------------ */
// Shared colours.
const WOOD='#9b6a3c',WOOD_D='#6e4a2e',STONE='#cfc6b4',STONE_D='#9f9584',GLASS='#9fd3e6',LIT='#ffe08a',WHITE='#fbf7ee',LEAF='#4f9a4a';
const win=lit=>lit?LIT:GLASS;

/** Each style: meta (emoji, name, tier 1–4), three palettes (variants: name + colours) and draw(h, level, pal). */
export const HOUSES={
  nha_tranh:{emoji:'🏚️',name:'Nhà tranh vách đất',tier:1,
    pals:[{name:'Rơm vàng',wall:'#d9b98a',roof:'#c99a48'},{name:'Rạ nâu',wall:'#c9a27a',roof:'#9c7444'},{name:'Cỏ tranh',wall:'#e4d2a8',roof:'#a9a27a'}],
    draw(h,lv,c){
      h.ground(0,0,.032,.03,'#d8c08e',.75);
      if(lv>1){h.part(-.03,0);for(let i=0;i<7;i++)h.post(-.03,-.026+i*.009,0,9,1.6,WOOD_D);h.beam([-.03,-.026,7],[-.03,.028,7],1.4,WOOD);
        h.part(.004,.031);for(let i=0;i<8;i++)h.post(-.028+i*.0075,.031,0,9,1.6,WOOD_D);h.beam([-.028,.031,7],[.024,.031,7],1.4,WOOD);}
      h.part(0,-.004).box(0,-.004,.022,.015,0,19,c.wall).door(0,-.004,.022,.015,'s',.5,.2,13,WOOD_D).windows(0,-.004,.022,.015,0,19,1,2,'#5a3a22',{sides:'e',w:.4})
        .panel(0,-.004,.022,.015,'s',.12,.3,7,14,'#5a3a22').panel(0,-.004,.022,.015,'s',.7,.88,7,14,'#5a3a22')
        .roof(0,-.004,.022,.015,19,24,c.roof,{over:.007,ridge:.7});
      if(lv>1)h.part(.025,.006).box(.025,.006,.008,.01,0,13,c.wall).roof(.025,.006,.008,.01,13,10,shade(c.roof,.9),{over:.004});
      if(lv>2){h.part(-.024,.022).cone(-.024,.022,.008,0,16,'#e0c070',10).ball(-.024,.022,16,2,'#c9a048');
        h.part(.02,.026).cyl(.02,.026,.005,0,6,STONE,10,'#4a7fa0').post(.016,.026,6,15,1.2,WOOD_D).post(.024,.026,6,15,1.2,WOOD_D).beam([.016,.026,15],[.024,.026,15],1.4,WOOD_D);
        h.part(-.006,.028).ball(-.008,.028,2,2.2,WHITE).ball(-.002,.03,2,2,'#e8a04a');}
    }},
  nha_tre:{emoji:'🎋',name:'Nhà tre sinh thái',tier:1,
    pals:[{name:'Lá xanh',wall:'#d8c27a',roof:'#7d9a4a'},{name:'Rơm',wall:'#e0cc8a',roof:'#c9a04f'},{name:'Lá cọ sẫm',wall:'#c8ad6a',roof:'#4f6b3a'}],
    draw(h,lv,c){
      h.ground(0,0,.032,.03,'#9fcf7a',.6);
      const z=8;
      h.part(0,0);for(const [sx,sy] of [[-1,-1],[1,-1],[1,1],[-1,1]])h.post(sx*.022,sy*.016,0,z,2.4,'#8f7238');
      h.box(0,0,.024,.018,z,z+2,'#b08a4a').box(0,-.001,.02,.015,z+2,z+22,c.wall);
      for(let i=1;i<8;i++){h.panel(0,-.001,.02,.015,'s',i/8-.012,i/8+.012,z+2,z+22,shade(c.wall,.82));if(i<6)h.panel(0,-.001,.02,.015,'e',i/6-.015,i/6+.015,z+2,z+22,shade(c.wall,.82));}
      h.door(0,-.001,.02,.015,'s',.5,.22,15,'#6e4a2a',z+2).windows(0,-.001,.02,.015,z+2,20,1,2,lv>2?LIT:'#3a2a1a',{sides:'e',w:.45});
      h.roof(0,-.001,.02,.015,z+22,16,c.roof,{type:'gable',over:.007,ends:shade(c.wall,.95)});
      if(lv>2)for(let i=0;i<3;i++)h.flat([[-.012+i*.009,.004,z+31],[-.004+i*.009,.004,z+31],[-.004+i*.009,.011,z+27],[-.012+i*.009,.011,z+27]],'#2f4f7a');   // solar panels
      if(lv>1){h.part(0,.026).box(0,.024,.024,.007,z-1,z+1,'#b08a4a');h.beam([-.024,.031,z+8],[.024,.031,z+8],1.4,'#8f7238');for(let i=0;i<5;i++)h.post(-.024+i*.012,.031,z,z+8,1.4,'#8f7238');
        h.part(-.028,.02).box(-.028,.02,.004,.008,0,4,WOOD).ball(-.028,.016,6,3.4,'#5aa94e').ball(-.028,.024,6,3,'#7cc26a');}
      if(lv>2){h.part(.028,-.014).cyl(.028,-.014,.0045,0,16,'#7a8a96',10,'#5f6e78');
        h.part(-.02,.03);for(let i=0;i<5;i++)h.ball(-.02+i*.01,.033,18+Math.sin(i)*2,1.4,['#ffe08a','#ff8aa0','#9fd0e4'][i%3]);}
    }},
  nha_cay:{emoji:'🌳',name:'Nhà trên cây',tier:1,
    pals:[{name:'Gỗ mộc',wall:'#c9965a',roof:'#8a5a32'},{name:'Xanh trời',wall:'#7fa8d0',roof:'#3f5f8a'},{name:'Đỏ gạch',wall:'#d27a5a',roof:'#7a3a2a'}],
    draw(h,lv,c){
      h.ground(0,0,.03,.028,'#7cc26a',.55);
      h.part(-.004,-.03).ball(-.016,-.022,76,15,shade(LEAF,.85)).ball(.014,-.024,72,14,shade(LEAF,.9)).ball(0,-.028,90,13,LEAF);
      h.part(0,0).cyl(0,0,.0065,0,42,'#7a5432',8);
      for(const a of [0,2.1,4.2])h.beam([0,0,4],[Math.cos(a)*.012,Math.sin(a)*.012,0],2.4,'#6a4628');
      h.box(0,0,.026,.022,42,45,WOOD);
      h.box(-.004,-.006,.016,.012,45,62,c.wall).door(-.004,-.006,.016,.012,'s',.3,.26,12,WOOD_D,45).windows(-.004,-.006,.016,.012,45,17,1,1,lv>2?LIT:'#3a2a1a',{sides:'e',w:.5})
        .panel(-.004,-.006,.016,.012,'s',.6,.85,51,57,lv>2?LIT:'#3a2a1a');
      h.roof(-.004,-.006,.016,.012,62,13,c.roof,{type:'gable',over:.005,ends:shade(c.wall,.92)});
      h.part(.016,.024);h.beam([.012,.026,0],[.012,.022,43],1.4,WOOD_D).beam([.02,.026,0],[.02,.022,43],1.4,WOOD_D);for(let i=1;i<7;i++)h.beam([.012,.026-.0006*i,i*6.2],[.02,.026-.0006*i,i*6.2],1.2,WOOD);
      if(lv>1){h.part(0,.023);h.beam([-.026,.022,52],[.026,.022,52],1.4,WOOD_D).beam([.026,.022,52],[.026,-.022,52],1.4,WOOD_D);
        for(let i=0;i<5;i++)h.post(-.026+i*.013,.022,45,52,1.2,WOOD_D);
        h.part(-.02,.03).beam([-.02,.02,44],[-.02,.03,14],.8,'#c9b48a').beam([-.012,.02,44],[-.012,.03,14],.8,'#c9b48a').box(-.016,.03,.005,.002,13,15,WOOD);}
      if(lv>2){h.part(.03,.0).beam([.026,-.01,44],[.034,.02,2],3.4,'#ffc93c');
        h.part(0,.026);for(let i=0;i<6;i++)h.ball(-.024+i*.0096,.023,54+(i%2),1.8,['#ffe08a','#ff8aa0','#9fd0e4'][i%3]);}
    }},
  cabin_go:{emoji:'🛖',name:'Cabin gỗ chữ A',tier:1,
    pals:[{name:'Gỗ sẫm',wall:'#6b4a32',roof:'#3d3f45'},{name:'Đỏ kho thóc',wall:'#a8432f',roof:'#2f3136'},{name:'Bạch dương',wall:'#d8c6a8',roof:'#5b6b4a'}],
    draw(h,lv,c){
      h.ground(0,0,.03,.028,'#a9c98a',.55);
      h.part(0,0).box(0,0,.02,.018,0,4,STONE).roof(0,0,.02,.018,4,44,c.roof,{type:'gable',axis:'y',over:.004,ends:c.wall});
      h.face([[.011,.0225,8],[-.011,.0225,8],[0,.0225,32]],lv>2?LIT:GLASS).face([[.0025,.0228,8],[-.0025,.0228,8],[-.0025,.0228,20],[.0025,.0228,20]],WOOD_D);
      h.box(.012,-.004,.0032,.0032,30,50,STONE_D);
      if(lv>1){h.part(.028,.008).box(.028,.008,.007,.016,0,4,WOOD);h.beam([.035,-.008,11],[.035,.024,11],1.4,WOOD_D);for(let i=0;i<4;i++)h.post(.035,-.008+i*.0107,4,11,1.2,WOOD_D);
        h.part(-.028,.014).box(-.028,.014,.004,.01,0,8,'#8a5a32');for(let i=0;i<3;i++)h.ball(-.024,.006+i*.008,3,2.2,'#c9965a');}
      if(lv>2){h.part(-.018,.028).cyl(-.018,.028,.0075,0,7,'#7a5432',12,'#5fb8d8');
        h.part(0,.026);for(let i=0;i<7;i++)h.ball(-.024+i*.008,.026,30+Math.sin(i/6*Math.PI)*-6,1.6,i%2?'#ffe08a':'#ffb35a');}
    }},
  bungalow:{emoji:'🏝️',name:'Bungalow mái lá',tier:2,
    pals:[{name:'Gỗ tếch',wall:'#b07a4a',roof:'#b8955a'},{name:'Vôi trắng',wall:'#f1e8d6',roof:'#a8844a'},{name:'Gỗ sẫm',wall:'#7a4f32',roof:'#8f7444'}],
    draw(h,lv,c){
      h.ground(0,0,.033,.03,'#f0dcae',.8);
      if(lv>1){h.ground(.022,.02,.009,.009,'#3fb3d9');h.ground(.022,.02,.0105,.0105,'#e8dcc4',.9);h.ground(.022,.02,.008,.008,'#3fb3d9');}
      h.part(-.004,-.006).box(-.004,-.006,.024,.019,0,5,STONE).box(-.004,-.008,.019,.014,5,22,c.wall)
        .windows(-.004,-.008,.019,.014,5,17,1,3,lv>2?LIT:'#4a3020',{w:.55,sides:'se',skip:true}).door(-.004,-.008,.019,.014,'s',.5,.2,14,WOOD_D,5);
      for(const [sx,sy] of [[-1,1],[1,1],[1,-1]])h.post(-.004+sx*.023,-.006+sy*.018,5,22,2,WOOD_D);
      h.frustum(-.004,-.007,.029,.024,.017,.013,22,10,c.roof).roof(-.004,-.007,.017,.013,32,24,shade(c.roof,1.04),{over:0,ridge:.9});
      h.ball(-.004,-.007,57,2,shade(c.roof,.7));
      if(lv>2){h.part(.028,-.004);for(const dy of [-.01,.004])h.box(.03,-.004+dy,.003,.006,0,3,WHITE);
        h.part(-.03,.024).post(-.03,.024,0,20,1.6,WOOD_D).ball(-.03,.024,21,2.6,'#ff9a3a').ball(-.03,.024,23,1.4,'#ffe08a');
        h.part(.01,.03).post(.01,.03,0,20,1.6,WOOD_D).ball(.01,.03,21,2.6,'#ff9a3a').ball(.01,.03,23,1.4,'#ffe08a');
        h.tree(-.03,-.026,.8,'#5aa94e');h.part(-.03,-.026).ball(-.028,-.026,22,1.6,'#fff4e8').ball(-.032,-.024,24,1.6,'#ffe0ec');}
    }},
  pho_hoi_an:{emoji:'🏮',name:'Nhà phố Hội An',tier:2,
    pals:[{name:'Vàng nghệ',wall:'#f2c94c',roof:'#8a4a35'},{name:'Xanh ngọc',wall:'#8fd0c0',roof:'#7a4030'},{name:'Hồng đào',wall:'#f2a7a0',roof:'#7f4636'}],
    draw(h,lv,c){
      h.ground(0,0,.032,.028,'#d9c9a8',.7);
      const hx=.024,hy=.015,z1=24,front='#7a4a2a';
      h.part(0,0).box(0,0,hx,hy,0,z1,c.wall).panel(0,0,hx,hy,'s',.12,.88,2,19,front);
      for(let i=0;i<6;i++)h.panel(0,0,hx,hy,'s',.15+i*.125,.2+i*.125,4,17,lv>2?'#c98a4a':'#5a3420');
      h.windows(0,0,hx,hy,0,z1,1,2,'#3f6f5a',{sides:'e',w:.45,lo:.35,hi:.7});
      if(lv>1){h.frustum(0,0,hx+.007,hy+.008,hx-.002,hy-.004,z1,5,c.roof,null);
        h.box(0,-.003,hx-.002,hy-.004,z1+2,z1+20,c.wall).windows(0,-.003,hx-.002,hy-.004,z1+2,18,1,3,lv>2?LIT:'#3f6f5a',{sides:'se',w:.5,frame:'#5a3420'});
        h.beam([-hx,hy+.004,z1+7],[hx,hy+.004,z1+7],1.6,'#5a3420');for(let i=0;i<7;i++)h.post(-hx+i*hx/3,hy+.004,z1+2,z1+7,1,'#5a3420');
        h.roof(0,-.003,hx-.002,hy-.004,z1+20,13,c.roof,{type:'gable',over:.006,ends:shade(c.wall,.95)});}
      else h.roof(0,0,hx,hy,z1,14,c.roof,{type:'gable',over:.007,ends:shade(c.wall,.95)});
      h.part(0,hy+.01);const zl=lv>1?z1-1:z1-3;
      for(const [i,x] of [-.016,0,.016].entries())h.lantern(x,hy+.009,zl-6,i===1?'#f2b630':'#e5484d',lv>1);
      if(lv>2){h.part(hx+.004,.004);for(let i=0;i<7;i++)h.ball(hx+.002,.012-i*.004,8+i*5,2.6,i%2?'#e85a9a':'#f27ab0');
        for(const x of [-.03,.03])h.part(x,.026).box(x,.026,.0035,.0035,0,4,'#b5653a').ball(x,.026,7,3.2,'#5aa94e');}
    }},
  nha_ruong:{emoji:'🏯',name:'Nhà rường Huế',tier:2,
    pals:[{name:'Ngói đỏ',wall:'#8a5a36',roof:'#9a4a35'},{name:'Ngói rêu',wall:'#7a5434',roof:'#6a7a4a'},{name:'Ngói vàng',wall:'#8a5a36',roof:'#d9a630'}],
    draw(h,lv,c){
      h.ground(0,0,.033,.03,'#cfd9a0',.55);
      h.part(0,-.004).box(0,-.004,.028,.019,0,4,'#b8ae9c').box(0,-.007,.023,.013,4,19,c.wall);
      for(let i=0;i<5;i++)h.panel(0,-.007,.023,.013,'s',.08+i*.19,.2+i*.19,5,17,shade(c.wall,.78));
      for(let i=0;i<5;i++)h.post(-.024+i*.012,.012,4,19,2.2,'#5a3420');
      h.roof(0,-.005,.023,.015,19,24,c.roof,{over:.009,ridge:.6,tips:6,tipColor:shade(c.roof,1.25)});
      if(lv>1){h.part(.028,-.08).box(.028,-.014,.007,.011,0,15,c.wall).panel(.028,-.014,.007,.011,'e',.2,.8,3,12,shade(c.wall,.78)).roof(.028,-.014,.007,.011,15,12,shade(c.roof,.95),{over:.004,tips:4});}
      if(lv>2){h.part(-.008,.031).box(-.008,.031,.012,.0018,0,13,'#e6dcc6').panel(-.008,.031,.012,.0018,'s',.25,.75,3,10,'#4f8a6a');
        h.ground(.016,.03,.007,.004,'#5fb0c8');h.part(.016,.03).ball(.013,.03,1,1.6,'#f4a6c0').ball(.019,.031,1,1.8,'#7cc26a');
        h.part(-.03,.022).box(-.03,.022,.003,.003,0,4,'#5a7a8a').ball(-.03,.022,7,3,'#3f7a3e');}
    }},
  hai_dang:{emoji:'🗼',name:'Nhà hải đăng',tier:2,max:1,
    pals:[{name:'Đỏ trắng',wall:WHITE,roof:'#d9483b'},{name:'Xanh trắng',wall:WHITE,roof:'#2f6fb3'},{name:'Đen trắng',wall:WHITE,roof:'#34363c'}],
    draw(h,lv,c){
      h.ground(0,0,.032,.03,'#c9c2b0',.6);
      h.part(-.03,.024).ball(-.03,.026,2,4,'#9a948a').ball(-.024,.03,1,3,'#8a847a');
      h.part(-.012,.008).box(-.012,.008,.014,.011,0,17,c.wall).door(-.012,.008,.014,.011,'s',.3,.24,11,'#4a6a8a').windows(-.012,.008,.014,.011,0,17,1,1,lv>2?LIT:GLASS,{sides:'se',w:.4})
        .roof(-.012,.008,.014,.011,17,11,c.roof,{type:'gable',over:.004,ends:c.wall});
      const tx=.012,ty=-.008,top=58+(lv>1?14:0)+(lv>2?6:0);
      h.part(tx,ty).cyl(tx,ty,.0085,0,top,c.wall,12);
      for(let z=14;z<top-6;z+=22)h.cyl(tx,ty,.0087,z,z+8,c.roof,12,null);
      h.cyl(tx,ty,.0115,top,top+3,'#3a3a40',12).cyl(tx,ty,.0065,top+3,top+13,lv>1?'#ffe9a0':'#cfe6ee',10,null).cone(tx,ty,.0085,top+13,9,c.roof,10).ball(tx,ty,top+23,1.6,'#3a3a40');
      if(lv>1)h.flat([[tx,ty,top+8],[tx+.05,ty-.012,top+16],[tx+.05,ty+.006,top+2]],'#fff3b0',.35);
      if(lv>2){h.part(tx,ty-.001).ball(tx,ty,top+8,6,'#fff3b0',.45);h.part(-.026,-.012).post(-.026,-.012,0,30,1.4,'#666').flat([[-.026,-.012,30],[-.014,-.012,27],[-.026,-.012,24]],c.roof);}
    }},
  nha_nhat:{emoji:'🎎',name:'Nhà kiểu Nhật',tier:2,
    pals:[{name:'Ngói xám',wall:'#f3ead8',roof:'#4a4f57'},{name:'Mái đồng xanh',wall:'#f3ead8',roof:'#5f8f7a'},{name:'Ngói đen',wall:'#efe4cc',roof:'#2e3036'}],
    draw(h,lv,c){
      h.ground(0,0,.033,.03,'#d8d0b8',.6);
      if(lv>2){h.ground(-.02,.024,.009,.005,'#4fa3c0');h.part(-.02,.026).ball(-.022,.024,1,1.4,'#ff8a3a').ball(-.017,.026,1,1.3,'#fff');}
      const hx=.021,hy=.015;
      h.part(0,0).box(0,0,.026,.02,0,4,'#c8a070').box(0,-.002,hx,hy,4,23,c.wall);
      for(const s of 'se')for(let i=0;i<4;i++){const t=(i+.5)/4;h.panel(0,-.002,hx,hy,s,t-.11,t+.11,6,21,'#fbf6ea');h.panel(0,-.002,hx,hy,s,t-.006,t+.006,6,21,'#7a5a3a');h.panel(0,-.002,hx,hy,s,t-.11,t+.11,13,13.8,'#7a5a3a');}
      for(const [sx,sy] of [[-1,1],[1,1],[1,-1]])h.post(sx*hx,-.002+sy*hy,4,23,2.2,'#4a3424');
      if(lv>1){h.frustum(0,-.002,hx+.009,hy+.009,hx-.006,hy-.005,23,6,c.roof,null);
        h.box(0,-.004,hx-.006,hy-.005,29,42,c.wall).windows(0,-.004,hx-.006,hy-.005,29,13,1,2,lv>2?LIT:'#fbf6ea',{sides:'se',w:.5,frame:'#7a5a3a'});
        h.roof(0,-.004,hx-.006,hy-.005,42,14,c.roof,{over:.008,ridge:.5});}
      else h.roof(0,-.002,hx,hy,23,16,c.roof,{over:.009,ridge:.5});
      if(lv>2){h.part(.028,.024).box(.028,.024,.003,.003,0,3,'#a8a8a0').box(.028,.024,.0018,.0018,3,9,'#b8b8b0').box(.028,.024,.0035,.0035,9,11,'#a0a098').roof(.028,.024,.003,.003,11,4,'#909088',{type:'pyramid',over:.001});
        h.part(-.03,-.022).post(-.03,-.022,0,14,2.4,'#6a4628').ball(-.032,-.022,16,6,'#d9483b').ball(-.027,-.024,19,5,'#e86a3a').ball(-.03,-.02,21,4,'#c8312f');}
    }},
  hanok:{emoji:'🏘️',name:'Nhà kiểu Hàn (Hanok)',tier:2,
    pals:[{name:'Ngói than',wall:'#f4efe3',roof:'#3f4650'},{name:'Ngói ngọc',wall:'#f4efe3',roof:'#5f8a7e'},{name:'Ngói nâu đất',wall:'#efe6d4',roof:'#6a4c3a'}],
    draw(h,lv,c){
      h.ground(0,0,.033,.03,'#e2d6b8',.7);
      const hx=.022,hy=.013,y=-.004;
      h.part(0,y).box(0,y,.027,.018,0,6,'#cfc6b4').box(0,y,hx,hy,6,22,c.wall);
      for(const s of 'se'){for(let i=0;i<=4;i++)h.panel(0,y,hx,hy,s,i/4-.012,i/4+.012,6,22,'#5a3a26');h.panel(0,y,hx,hy,s,0,1,19.5,22,'#5a3a26');
        for(let i=0;i<4;i++)h.panel(0,y,hx,hy,s,i/4+.06,i/4+.19,9,17,'#e9dcc0');}
      h.roof(0,y,hx,hy,22,13,c.roof,{over:.011,ridge:.85,tips:7,tipColor:shade(c.roof,1.35)});
      h.beam([-.013,y,35],[.013,y,35],2.4,shade(c.roof,.7));
      if(lv>1){h.part(-.02,.016).box(-.02,.016,.008,.011,4,18,c.wall).panel(-.02,.016,.008,.011,'s',.2,.8,8,15,'#e9dcc0').panel(-.02,.016,.008,.011,'e',.2,.8,8,15,'#e9dcc0')
        .roof(-.02,.016,.008,.011,18,11,c.roof,{over:.007,tips:5,tipColor:shade(c.roof,1.35)});}
      if(lv>2){h.part(.022,.026);for(const [dx,dy,r] of [[0,0,3],[.006,.002,2.6],[-.004,.004,2.2],[.003,-.004,2]])h.ball(.022+dx,.026+dy,r,r,'#6a3a24');
        h.tree(.03,-.02,.85,'#5a8a3e');h.part(.03,-.02).ball(.027,-.021,22,1.6,'#f2862a').ball(.032,-.019,25,1.6,'#f2862a').ball(.03,-.022,28,1.5,'#f2862a');
        h.part(-.008,.032).box(-.008,.032,.018,.0018,0,6,'#b8ae9c').box(-.008,.032,.019,.0028,6,7.5,c.roof);}
    }},
  villa_phap:{emoji:'🏛️',name:'Biệt thự Pháp',tier:3,
    pals:[{name:'Vàng kem',wall:'#f3dfb0',roof:'#b5533c'},{name:'Trắng mái xám',wall:'#f6f2ea',roof:'#5d6670'},{name:'Hồng phấn',wall:'#f2c8c0',roof:'#6e4a3a'}],
    draw(h,lv,c){
      h.ground(0,0,.034,.03,'#9fd07a',.55);
      const hx=.026,hy=.016,fl=lv>1?2:1,fh=22,zt=fl*fh,sh='#4f7a5a';
      if(lv>2){for(const [x,y,w,d] of [[-.03,.0,.0025,.026],[.0,.03,.03,.0025]])h.part(x,y).box(x,y,w,d,0,5,'#4a8a3e','#5aa94e');
        h.part(.022,.026).cyl(.022,.026,.006,0,4,'#d8d2c8',12,'#6ec6e0').post(.022,.026,4,11,1.6,'#d8d2c8').ball(.022,.026,12,2,'#fff',.9);}
      h.part(0,-.004).box(0,-.004,hx,hy,0,zt,c.wall);
      for(let f=0;f<fl;f++)for(const s of 'se'){const per=s==='s'?4:3;for(let i=0;i<per;i++){const t=(i+.5)/per,z0=f*fh+6,z1=f*fh+17;if(s==='s'&&f===0&&i===1)continue;
        h.panel(0,-.004,hx,hy,s,t-.06,t+.06,z0,z1,lv>2?LIT:GLASS).panel(0,-.004,hx,hy,s,t-.11,t-.06,z0,z1,sh).panel(0,-.004,hx,hy,s,t+.06,t+.11,z0,z1,sh);}}
      h.door(0,-.004,hx,hy,'s',.375,.1,14,'#5a3420');
      h.frustum(0,-.004,hx+.003,hy+.003,hx-.006,hy-.005,zt,12,c.roof,shade(c.roof,1.1));
      for(const x of [-.012,.012])h.box(x,hy-.004-.002,.003,.002,zt+3,zt+10,c.wall).roof(x,hy-.006,.003,.002,zt+10,4,c.roof,{type:'gable',axis:'y',over:.001,ends:c.wall});
      h.box(.016,-.012,.0025,.0025,zt+6,zt+18,'#b5653a');
      h.part(-.0055,.016).box(-.0055,.016,.008,.004,0,2,'#e8e0d0');for(const x of [-.012,.001])h.post(x,.019,2,14,2.2,WHITE);
      h.box(-.0055,.0155,.008,.0045,14,16,WHITE);
      if(lv>1){h.beam([-.0135,.02,21],[.0025,.02,21],1.4,'#2f3a2f');for(let i=0;i<5;i++)h.post(-.0135+i*.004,.02,16,21,.9,'#2f3a2f');}
    }},
  dia_trung_hai:{emoji:'🏖️',name:'Biệt thự Địa Trung Hải',tier:3,
    pals:[{name:'Mái vòm xanh',wall:WHITE,roof:'#2f6fb3'},{name:'Mái vòm ngọc',wall:WHITE,roof:'#2aa6a6'},{name:'Mái vòm đất nung',wall:'#fbf3e6',roof:'#c96a3f'}],
    draw(h,lv,c){
      h.ground(0,0,.034,.03,'#efe6d6',.85);
      if(lv>2){h.ground(.016,.025,.014,.006,'#3fb3d9');h.part(-.02,.028).cone(-.02,.028,.009,12,4,'#f2f2f2',10).post(-.02,.028,0,12,1.2,'#999');}
      h.part(-.004,-.004).box(-.004,-.004,.022,.016,0,22,c.wall).windows(-.004,-.004,.022,.016,0,22,1,2,c.roof,{sides:'se',w:.35,skip:true}).door(-.004,-.004,.022,.016,'s',.5,.14,15,c.roof);
      h.box(-.012,-.01,.012,.009,22,38,c.wall).windows(-.012,-.01,.012,.009,22,16,1,1,lv>2?LIT:c.roof,{sides:'se',w:.4});
      h.beam([-.0,.012,27],[.018,.012,27],1.2,'#d8d2c8').beam([.018,.012,27],[.018,-.02,27],1.2,'#d8d2c8');
      h.cyl(.008,-.008,.0062,22,28,c.wall,14).dome(.008,-.008,.0072,28,c.roof,14).post(.008,-.008,28+.0072*W*.62,28+.0072*W*.62+5,1,'#d8b84a');
      if(lv>1){h.part(.022,.012).box(.022,.012,.008,.008,0,15,c.wall).panel(.022,.012,.008,.008,'s',.3,.7,4,11,lv>2?LIT:c.roof).box(.022,.012,.0085,.0085,15,16.5,shade(c.wall,.95));}
      h.part(-.026,.012);for(let i=0;i<6;i++)h.ball(-.0265,.012-i*.004,6+i*3.5,2.6,i%2?'#e85a9a':'#c83a8a');
      if(lv>2){h.part(-.024,-.022).box(-.024,-.022,.004,.004,0,30,c.wall).panel(-.024,-.022,.004,.004,'s',.25,.75,21,27,'#3a3a40').cyl(-.024,-.022,.0035,30,32,c.wall,10).dome(-.024,-.022,.004,32,c.roof,10);}
    }},
  villa_kinh:{emoji:'🪟',name:'Biệt thự kính hiện đại',tier:3,
    pals:[{name:'Kính xanh',wall:WHITE,roof:'#8fcbe0'},{name:'Kính khói',wall:'#3a3d42',roof:'#6d8a96'},{name:'Gỗ ấm',wall:'#b98a5a',roof:'#a9d6e6'}],
    draw(h,lv,c){
      h.ground(0,0,.034,.03,'#d9dcd8',.8);
      if(lv>2){h.ground(.004,.026,.026,.0055,'#36b1db');h.part(.004,.031).box(.004,.031,.026,.0012,0,2,'#e8eef0');
        for(const x of [-.016,-.006])h.part(x,.02).box(x,.02,.003,.006,0,2.5,WHITE);}
      const glass=lv>2?'#ffe7a8':c.roof;
      h.part(-.004,-.004).box(-.004,-.004,.02,.015,0,19,glass,'#e8eef0');
      for(const s of 'se')for(let i=0;i<=5;i++)h.panel(-.004,-.004,.02,.015,s,i/5-.012,i/5+.012,0,19,c.wall);
      h.box(.003,-.001,.027,.019,19,22,c.wall);
      if(lv>1){h.box(.007,.0,.017,.013,22,38,glass,'#e8eef0');for(const s of 'se')for(let i=0;i<=4;i++)h.panel(.007,.0,.017,.013,s,i/4-.014,i/4+.014,22,38,c.wall);
        h.box(.007,.0,.02,.016,38,40.5,c.wall).box(.016,.006,.006,.006,40.5,41.5,'#7cc26a').ball(.014,.004,44,2.6,'#5aa94e').ball(.019,.008,43.5,2.2,'#6fbf5a');}
      h.part(.022,.014).post(.026,.016,0,19,1.6,c.wall);
      h.part(-.026,.02).tree(-.026,.02,.7,'#3f8a4e');
    }},
  dinh_thu:{emoji:'🏰',name:'Dinh thự châu Âu',tier:4,max:1,big:true,
    pals:[{name:'Đá kem mái lam',wall:'#ece4d2',roof:'#4a5a78'},{name:'Đá trắng mái đồng',wall:'#f6f2ea',roof:'#4f9a8a'},{name:'Đá hồng mái than',wall:'#e8c4b8',roof:'#3a3c44'}],
    draw(h,lv,c){
      h.ground(0,0,.035,.032,'#8fcf6a',.6);
      if(lv>2){h.part(.0,.03).box(0,.03,.03,.002,0,4,'#4a8a3e','#5aa94e');h.part(-.026,.026).cyl(-.026,.026,.005,0,4,'#d8d2c8',12,'#6ec6e0').ball(-.026,.026,9,2,'#fff',.9);}
      const hx=.024,hy=.014,zt=lv>1?40:30,lit=lv>2;
      if(lv>1)for(const x of [-.022,.022])h.part(x,-.02).cyl(x,-.02,.0075,0,zt+18,c.wall,12).windows(x,-.02,.006,.006,0,16,2,1,win(lit),{sides:'se',w:.4}).cone(x,-.02,.0095,zt+18,20,c.roof,12);
      h.part(0,-.004).box(0,-.004,hx,hy,0,zt,c.wall).windows(0,-.004,hx,hy,0,zt/2,2,4,win(lit),{sides:'se',w:.45,lo:.25,hi:.72,skip:true});
      h.roof(0,-.004,hx,hy,zt,16,c.roof,{over:.004,ridge:.7});
      for(const x of [-.012,0,.012])h.box(x,hy-.004-.001,.0025,.0018,zt+2,zt+9,c.wall).roof(x,hy-.005,.0025,.0018,zt+9,4,c.roof,{type:'pyramid',over:.001});
      for(const x of [-.028,.028])h.part(x,.04).cyl(x,.012,.0075,0,zt+12,c.wall,12).windows(x,.012,.0055,.0055,0,(zt+12)/3,3,1,win(lit),{sides:'se',w:.45}).cone(x,.012,.0095,zt+12,22,c.roof,12);
      h.part(0,.014).box(0,.014,.008,.006,0,22,shade(c.wall,.97)).door(0,.014,.008,.006,'s',.5,.4,14,'#5a3420').frustum(0,.014,.009,.007,.002,.002,22,9,c.roof);
      for(const x of [-.007,.007])h.post(x,.021,0,22,2.4,WHITE);
      h.part(0,.024).box(0,.024,.012,.004,0,2,'#d8d2c8').box(0,.0225,.01,.003,2,4,'#e2dccf');
      if(lv>1)for(const x of [-.028,.028])h.part(x,.0125).post(x,.012,zt+34,zt+44,1,'#555').flat([[x,.012,zt+44],[x+.008,.012,zt+41.5],[x,.012,zt+39]],'#d9483b');
    }},
  hoang_cung:{emoji:'👑',name:'Hoàng cung Á Đông',tier:4,max:1,big:true,
    pals:[{name:'Ngói hoàng gia',wall:'#a3242a',roof:'#e7b726'},{name:'Ngói lưu ly xanh',wall:'#a3242a',roof:'#2f7a6a'},{name:'Ngói đỏ son',wall:'#8a1f24',roof:'#c8452f'}],
    draw(h,lv,c){
      h.ground(0,0,.036,.032,'#e6dccb',.85);
      const gold='#e7b726',trim=c.roof==='#e7b726'?'#c8312f':gold;
      if(lv>1)for(const x of [-.026,.026])h.part(x,-.07).box(x,-.018,.008,.007,6,20,c.wall).roof(x,-.018,.008,.007,20,12,c.roof,{over:.005,tips:5,tipColor:trim});
      h.part(0,-.002).box(0,-.002,.031,.022,0,6,'#d8d0c0').box(0,-.005,.023,.013,6,28,c.wall);
      h.windows(0,-.005,.023,.013,6,22,1,5,'#f4c95d',{sides:'se',w:.55,lo:.15,hi:.7,skip:true}).door(0,-.005,.023,.013,'s',.5,.14,16,'#5a1215',6);
      for(let i=0;i<7;i++)h.post(-.024+i*.008,.012,6,28,2.2,gold);
      h.frustum(0,-.005,.03,.02,.018,.01,28,9,c.roof,null);
      for(const [sx,sy] of [[-1,1],[1,1],[1,-1],[-1,-1]])h.flat([[sx*.03,-.005+sy*.02,28],[sx*.036,-.005+sy*.026,37],[sx*.026,-.005+sy*.019,31]],trim);
      h.box(0,-.006,.017,.0095,37,45,c.wall).panel(0,-.006,.017,.0095,'s',.1,.9,38,44,'#f4c95d');
      h.roof(0,-.006,.017,.0095,45,lv>2?20:16,c.roof,{over:.008,ridge:.7,tips:7,tipColor:trim});
      const rz=45+(lv>2?20:16);h.beam([-.012,-.006,rz],[.012,-.006,rz],2.6,trim);
      h.flat([[-.014,-.006,rz],[-.011,-.006,rz+6],[-.008,-.006,rz]],trim).flat([[.014,-.006,rz],[.011,-.006,rz+6],[.008,-.006,rz]],trim);
      if(lv>2)h.ball(0,-.006,rz+4,2.6,gold);
      h.part(0,.026).box(0,.026,.01,.004,0,2,'#d8d0c0').box(0,.0245,.008,.003,2,4,'#e2dccf');
      if(lv>2){for(const x of [-.03,.03]){h.part(x,.028).post(x,.028,0,16,1.4,'#5a1215').lantern(x,.028,12,'#e5484d',true);}
        for(const x of [-.034,.034])h.part(x,.0).post(x,.0,0,40,1.2,'#888').flat([[x,0,40],[x,0,28],[x+.008*Math.sign(-x),0,34]],trim);}
    }},
};
export const HOUSE_IDS=Object.keys(HOUSES);
export const VARIANTS=3;

/** A stored kind (game/island_build.py): '<style>' or '<style>__<n>' (n: the colour, 1…VARIANTS−1) → [style, n]. */
export function splitKind(kind){
  const m=/^([a-z0-9_]+?)__(\d)$/.exec(String(kind||''));
  return m?[m[1],Number(m[2])]:[String(kind||''),0];
}
export const kindOf=(id,variant=0)=>variant>0?`${id}__${variant}`:id;

const cache=new Map();
/** The model of a style at a level (1…3) and colour: {parts, ground, top} (cached). Null: not a house style. */
export function houseModel(id,level=1,variant=0){
  const s=HOUSES[id];if(!s)return null;
  const lv=clamp(Math.floor(Number(level)||1),1,3),v=clamp(Math.floor(Number(variant)||0),0,s.pals.length-1),key=`${id}|${lv}|${v}`;
  let m=cache.get(key);if(m)return m;
  const h=builder();s.draw(h,lv,s.pals[v]);
  m={parts:h.parts,ground:h.base,top:h.top};cache.set(key,m);return m;
}
/** How tall a style stands at a level (pixels at the private island's scale): scaffolding, labels. */
export const houseTop=(id,level=1)=>houseModel(id,level)?.top||40;

function normal(pts){
  const [a,b,c]=pts,ux=(b[0]-a[0])*W,uy=(b[1]-a[1])*W,uz=b[2]-a[2],vx=(c[0]-a[0])*W,vy=(c[1]-a[1])*W,vz=c[2]-a[2];
  const nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx,l=Math.hypot(nx,ny,nz)||1;return [nx/l,ny/l,nz/l];
}
function drawItem(it,v,light){
  if(it.t==='f'){
    const pts=it.pts.map(p=>v.P(p[0],p[1],p[2]));let a=0;
    for(let i=0;i<pts.length;i++){const p=pts[i],q=pts[(i+1)%pts.length];a+=p[0]*q[1]-q[0]*p[1];}
    if(a<=.05)return;
    v.fill(pts,shade(it.color,light(...normal(it.pts))),it.alpha);
  }else if(it.t==='p')v.fill(it.pts.map(p=>v.P(p[0],p[1],p[2])),it.color,it.alpha);
  else if(it.t==='b'){const [x,y]=v.P(...it.p);v.circle(x,y,it.r*v.zs,it.color,it.alpha);}
  else if(it.t==='l')v.line(v.P(...it.a),v.P(...it.b),it.color,Math.max(.6,it.w*v.zs));
}
/** Paint a style at a level and colour through `view` (see the top of this file). {top} its height; null: unknown.
 * `only`: 'ground' (what lies flat: a renderer that draws people between the two) or 'parts' (what stands). */
export function paintHouse(id,level,variant,view,{only=''}={}){
  const m=houseModel(id,level,variant);if(!m)return null;
  paintModel(m,view,only);return {top:m.top};
}
function paintModel(m,view,only){
  const light=view.light||isoLight;
  if(only!=='parts')for(const it of m.ground.items)drawItem(it,view,light);
  if(only!=='ground'){
    const order=m.parts.map((p,i)=>({p,i,d:view.depth(p.at[0],p.at[1])})).sort((a,b)=>a.d-b.d||a.i-b.i);
    for(const {p} of order)for(const it of p.items)drawItem(it,view,light);
  }
}

/** A canvas 2D adapter: the isometric view (the new interface's angle) of a plot centred at (cx, cy) of `ctx`, `k`
 * pixels per map pixel. The build sheet's preview and the old interface use it. */
export function isoView(ctx,cx,cy,k=1){
  const N=560,HH=280;
  return {zs:k,depth:(x,y)=>x+y,
    P:(x,y,z)=>[cx+(x-y)*N*k,cy+((x+y)*HH-z)*k],
    fill(pts,color,alpha=1){ctx.globalAlpha=alpha;ctx.fillStyle=color;ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fill();ctx.globalAlpha=1;},
    circle(x,y,r,color,alpha=1){ctx.globalAlpha=alpha;ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,Math.max(.5,r),0,Math.PI*2);ctx.fill();ctx.globalAlpha=1;},
    line(a,b,color,w){ctx.strokeStyle=color;ctx.lineWidth=w;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();},
  };
}
/** Draw a style into a <canvas> (the build sheet's cards and preview): fitted, centred, on a soft island tile. */
export function previewHouse(canvas,id,level=1,variant=0,o={}){
  const ctx=canvas?.getContext?.('2d');if(!ctx||!HOUSES[id])return false;
  const dpr=Math.min(2,globalThis.devicePixelRatio||1),w=canvas.clientWidth||canvas.width||120,hgt=canvas.clientHeight||canvas.height||90;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(hgt*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,hgt);
  const m=houseModel(id,level,variant),tall=Math.max(50,m.top+20),k=Math.min(w/(.09*560*2),(hgt-8)/(.09*280*2+tall));
  const cx=w/2,cy=hgt-8-.045*2*280*k;
  if(o.tile!==false){ctx.fillStyle=o.ground||'#8cc56f';ctx.beginPath();const t=.042;
    [[-t,-t],[t,-t],[t,t],[-t,t]].forEach(([x,y],i)=>{const px=cx+(x-y)*560*k,py=cy+(x+y)*280*k;i?ctx.lineTo(px,py):ctx.moveTo(px,py);});ctx.closePath();ctx.fill();}
  paintHouse(id,level,variant,isoView(ctx,cx,cy,k));
  return true;
}

/* ---- ⚔️ the bang island's decorations (game/bang_extra_content.py DECOR, bought from the fund) ------------------
 * One small model each, in the same local units as the houses (drawn at its spots of public/js/bang-island-layout.js
 * DECOR_AT); `color` is the bang's colour (flags, sails). */
const RED='#d2453d',GOLD='#e7b726';
export const DECOR={
  den_long:{emoji:'🏮',draw(h){h.part(0,0).cyl(0,0,.0035,0,3,STONE_D).post(0,0,0,40,2.2,'#5a3a22').beam([-.008,.008,38],[.008,-.008,38],1.6,'#5a3a22')
    .lantern(-.007,.007,27,RED).lantern(.007,-.007,27,RED).ball(0,0,41,1.8,GOLD);}},
  hoa_dao:{emoji:'🌸',draw(h){h.ground(0,0,.012,.012,'#6e9a4a',.6);h.part(0,0).cyl(0,0,.0075,0,4,STONE).post(0,0,4,20,4,'#6e4a2e').beam([0,0,14],[.005,-.003,22],2.2,'#6e4a2e')
    .ball(-.004,.002,24,9,'#f48fb1').ball(.004,-.003,27,9,'#f7a8c4').ball(0,0,33,7,'#fbd0de').ball(.006,.003,22,5,'#f06292').ball(-.006,-.004,30,5,'#fbd0de');}},
  co_hoi:{emoji:'🎏',draw(h,c){h.part(0,0).cyl(0,0,.004,0,4,STONE_D).post(0,0,4,66,2,'#6b4a2b').ball(0,0,67,2,GOLD)
    .flat([[0,0,63],[.018,-.018,60],[.016,-.016,52],[.018,-.018,44],[0,0,47]],c).flat([[0,0,63],[.018,-.018,60],[.018,-.018,58.5],[0,0,61.5]],GOLD)
    .flat([[0,0,40],[.012,-.012,38],[.012,-.012,30],[0,0,32]],shade(c,.8));}},
  rong_da:{emoji:'🐉',draw(h){const J='#7fa38e',JD='#5d806b';h.part(0,0).box(0,0,.009,.009,0,10,STONE_D,STONE).box(0,0,.007,.007,10,13,STONE);
    const path=[[-.004,.004,18],[-.002,.0,24],[.001,-.003,28],[.004,-.002,33],[.003,.002,38],[0,.003,42]];
    path.forEach(([x,y,z],i)=>h.ball(x,y,z,5.2-i*.35,i%2?J:JD));h.ball(.002,.004,47,4.6,J).ball(.0045,.006,46,2,'#e8f3ec').ball(-.0005,.003,52,1.4,GOLD).ball(.004,.002,52,1.4,GOLD)
    .beam([.004,.006,45],[.011,.008,40],.9,GOLD).ball(-.006,.005,14,3,J);}},
  lau_chuong:{emoji:'🔔',draw(h){const q=.011;h.part(0,0).box(0,0,.014,.014,0,7,STONE_D,STONE);
    for(const [x,y] of [[-q,-q],[q,-q],[q,q],[-q,q]])h.post(x,y,7,44,2.6,'#a3242a');
    h.beam([-q,q,40],[q,q,40],2,'#7a1d1d').beam([q,-q,40],[q,q,40],2,'#7a1d1d').cone(0,0,.006,22,12,'#b88a1e').cyl(0,0,.0062,20,23,'#9a7316').post(0,0,34,44,1,'#3a2a1a')
    .roof(0,0,q,q,44,16,'#b04a35',{type:'pyramid',over:.006,tips:6,tipColor:GOLD}).ball(0,0,61,2.4,GOLD);}},
  thuyen_rong:{emoji:'🐲',draw(h,c){h.part(0,0).prism([[-.03,-.004],[.026,-.006],[.034,0],[.026,.006],[-.03,.004],[-.036,0]],0,6,RED,shade(RED,1.1)).quad(0,0,.026,.0045,6.2,GOLD,.9);
    for(let i=0;i<5;i++){const x=-.02+i*.01;h.beam([x,-.006,5],[x-.004,-.014,0],1.2,'#6e4a2e').beam([x,.006,5],[x-.004,.014,0],1.2,'#6e4a2e');}
    h.ball(.036,0,10,3.4,GOLD).ball(.039,0,15,3.8,'#3f8a5a').ball(.042,0,17,1.6,'#fff').beam([.039,0,18],[.036,0,23],1,GOLD).ball(-.038,0,10,3,'#3f8a5a').beam([-.038,0,10],[-.043,0,16],1.6,GOLD)
    .cyl(0,0,.004,6,11,'#7a1d1d').ball(0,0,12,2.6,GOLD).post(-.012,0,6,30,1.4,'#6b4a2b').flat([[-.012,0,29],[-.002,-.002,26],[-.012,0,20]],c);}},
};
export const DECOR_IDS=Object.keys(DECOR);
const decorCache=new Map();
function decorModel(id,color){
  const d=DECOR[id];if(!d)return null;const c=/^#[0-9a-f]{6}$/i.test(String(color||''))?color:'#d2453d',key=id+'|'+c;
  let m=decorCache.get(key);if(m)return m;const h=builder();d.draw(h,c);
  m={parts:h.parts,ground:h.base,top:h.top};decorCache.set(key,m);return m;
}
export const decorTop=id=>decorModel(id)?.top||30;
/** Paint one decoration through `view` (as paintHouse); `color`: the bang's. */
export function paintDecor(id,view,color,{only=''}={}){
  const m=decorModel(id,color);if(!m)return null;
  paintModel(m,view,only);return {top:m.top};
}
/** Draw a decoration into a <canvas> (the bang sheet's cards): fitted, centred on a small grass tile. */
export function previewDecor(canvas,id,color){
  const ctx=canvas?.getContext?.('2d'),m=decorModel(id,color);if(!ctx||!m)return false;
  const dpr=Math.min(2,globalThis.devicePixelRatio||1),w=canvas.clientWidth||canvas.width||96,hgt=canvas.clientHeight||canvas.height||80;
  canvas.width=Math.round(w*dpr);canvas.height=Math.round(hgt*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,hgt);
  const span=id==='thuyen_rong'?.05:.024,k=Math.min(w/(span*560*2.2),(hgt-10)/(span*280*2+m.top+8)),cx=w/2,cy=hgt-6-span*280*k;
  ctx.fillStyle=id==='thuyen_rong'?'#5fb6cc':'#8cc56f';ctx.beginPath();
  [[-span,-span],[span,-span],[span,span],[-span,span]].forEach(([x,y],i)=>{const px=cx+(x-y)*560*k,py=cy+(x+y)*280*k;i?ctx.lineTo(px,py):ctx.moveTo(px,py);});ctx.closePath();ctx.fill();
  paintDecor(id,isoView(ctx,cx,cy,k),color);
  return true;
}
