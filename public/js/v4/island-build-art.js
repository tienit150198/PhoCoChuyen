/** 🏗️ Xây trên đảo on the old interface: the building plots of a private island and what stands on them
 * (game/island_build.py), drawn flat and warm like the rest of v4/island-walk.js (a three-quarter view from above).
 * createBuildArt(ctx, view) → {ground(built, t), standing(built, t)}: `ground` paints what lies flat (empty plots, lawns,
 * pools, piers), `standing` returns [y, draw] pairs the walk sorts with the people. `view()` gives the walk's current
 * projection {P(x, y) → [px, py], S, FLAT}. Pure painting: the list comes from public/js/island-layout.js withBuilds. */
import {PLOT_W} from '../island-layout.js';
import {HOUSES,paintHouse,houseTop} from '../house-art.js';

/** How much bigger than its plot's own scale each kind is drawn (as on the new interface: client/isometric/island-builds.ts).
 * 🏡 The house styles of public/js/house-art.js: HOUSE_GROW. */
const GROW={nha_san:1.4,biet_thu:1.3,lau_dai:1.35,cong_vien:1.25,ho_boi:1,golf:1.15,cam_trai:1.3,ben_thuyen:1};
const HOUSE_GROW=1.3;

export function createBuildArt(ctx,view){
  const darker=(hex,k)=>{const n=parseInt(String(hex).slice(1),16);const c=v=>Math.max(0,Math.min(255,Math.round(v*k)));return `rgb(${c((n>>16)&255)},${c((n>>8)&255)},${c(n&255)})`;};
  const H=PLOT_W/2;
  function rect(r,fill){const {P}=view();const [a,b]=P(r.x-r.w/2,r.y-r.h/2),[c,d]=P(r.x+r.w/2,r.y+r.h/2);ctx.fillStyle=fill;ctx.fillRect(a,b,c-a,d-b);return [a,b,c,d];}
  function emoji(e,x,y,size,alpha=1){ctx.save();ctx.globalAlpha=alpha;ctx.fillStyle='#000';ctx.font=`${Math.round(size)}px "Segoe UI Emoji","Apple Color Emoji",sans-serif`;ctx.textAlign='center';ctx.textBaseline='bottom';ctx.fillText(e,x,y);ctx.restore();}
  /** A box seen from the front: its wall from height z0 to z1 (pixels at the map's scale), its top behind it. */
  function box(x,y,hw,hd,z0,z1,wall,top){
    const {P,S,FLAT}=view(),k=S/900,[a,b]=P(x-hw,y+hd),[c]=P(x+hw,y+hd),depth=2*hd*S*FLAT*.5,y0=b-z0*k,y1=b-z1*k;
    ctx.fillStyle=top||darker(wall,1.08);ctx.fillRect(a,y1-depth,c-a,depth);
    ctx.fillStyle=wall;ctx.fillRect(a,y1,c-a,y0-y1);
    return {a,c,top:y1-depth,front:y1,base:y0,k};
  }
  function roof(bx,rh,color){const {k}=bx,o=5*k;ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(bx.a-o,bx.top+o*2);ctx.lineTo(bx.a+(bx.c-bx.a)*.2,bx.top-rh*k);ctx.lineTo(bx.a+(bx.c-bx.a)*.8,bx.top-rh*k);ctx.lineTo(bx.c+o,bx.top+o*2);ctx.closePath();ctx.fill();
    ctx.fillStyle=darker(color,.8);ctx.fillRect(bx.a-o,bx.top+o,bx.c-bx.a+o*2,4*k);}
  function windowsRow(bx,z,h,n,lit){const {k}=bx;for(let i=0;i<n;i++){ctx.fillStyle=lit?'#ffe08a':'#9fd0e4';ctx.fillRect(bx.a+(bx.c-bx.a)*(i+.25)/n,bx.base-(z+h)*k,(bx.c-bx.a)*.5/n,h*.6*k);}}
  function tree(x,y,size=1,leaf='#4f9a4a'){const {P,S}=view(),k=S/900,[a,b]=P(x,y);ctx.fillStyle='rgba(0,0,0,.14)';ctx.beginPath();ctx.ellipse(a+3*k,b+1,11*k*size,4*k*size,0,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle='#7a5432';ctx.lineWidth=4*k*size;ctx.beginPath();ctx.moveTo(a,b);ctx.lineTo(a,b-18*k*size);ctx.stroke();
    ctx.fillStyle=leaf;ctx.beginPath();ctx.arc(a,b-24*k*size,11*k*size,0,Math.PI*2);ctx.fill();ctx.fillStyle='rgba(255,255,255,.18)';ctx.beginPath();ctx.arc(a-3*k,b-28*k*size,5*k*size,0,Math.PI*2);ctx.fill();}
  function boat(x,y,size,lv,t){const {P,S}=view(),k=S/900*size,[a,b]=P(x,y);ctx.save();ctx.translate(a,b);ctx.rotate(Math.sin(t/800)*.03);
    ctx.fillStyle='rgba(255,255,255,.45)';ctx.beginPath();ctx.ellipse(0,4*k,46*k,9*k,0,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#fff';ctx.beginPath();ctx.moveTo(-40*k,-4*k);ctx.lineTo(40*k,-8*k);ctx.lineTo(30*k,8*k);ctx.lineTo(-34*k,8*k);ctx.closePath();ctx.fill();ctx.fillStyle='#24507a';ctx.fillRect(-34*k,3*k,64*k,4*k);
    if(lv===2){ctx.strokeStyle='#6b5130';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(-2,-6*k);ctx.lineTo(-2,-60*k);ctx.stroke();ctx.fillStyle='#fdfaf2';ctx.beginPath();ctx.moveTo(0,-58*k);ctx.lineTo(0,-10*k);ctx.lineTo(26*k,-12*k);ctx.fill();}
    if(lv>2){ctx.fillStyle='#eef3f7';ctx.fillRect(-20*k,-22*k,36*k,16*k);ctx.fillStyle='#3d6f96';ctx.fillRect(-16*k,-19*k,28*k,6*k);}
    ctx.restore();}

  /** 🏡 A house style (public/js/house-art.js) in this three-quarter view: x across, y squashed, z straight up. */
  function houseView(p){
    const {P,S}=view(),k=S/900;
    return {zs:k,depth:(x,y)=>y,light:(nx,ny,nz)=>Math.max(.66,Math.min(1.14,.86+.14*ny+.24*nz+.1*nx)),
      P:(x,y,z)=>{const [a,b]=P(p.x+x,p.y+y);return [a,b-z*k];},
      fill(pts,color,alpha=1){ctx.globalAlpha=alpha;ctx.fillStyle=color;ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fill();ctx.globalAlpha=1;},
      circle(x,y,r,color,alpha=1){ctx.globalAlpha=alpha;ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,Math.max(.5,r),0,Math.PI*2);ctx.fill();ctx.globalAlpha=1;},
      line(a,b,color,w){ctx.strokeStyle=color;ctx.lineWidth=w;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();}};
  }
  function groundOne(p,it){
    const r={x:p.x,y:p.y,w:PLOT_W*.92,h:PLOT_W*.92};
    if(!it){const [a,b,c,d]=rect(r,'rgba(255,255,255,.14)');ctx.setLineDash([6,5]);ctx.strokeStyle='rgba(255,255,255,.65)';ctx.lineWidth=1.5;ctx.strokeRect(a,b,c-a,d-b);ctx.setLineDash([]);
      ctx.fillStyle='#8a6038';for(const [x,y] of [[a,b],[c,b],[a,d],[c,d]])ctx.fillRect(x-1.5,y-6,3,7);
      if(p.coast)emoji('⚓',(a+c)/2,(b+d)/2+8,14,.7);return;}
    const lv=Math.max(1,Math.min(3,it.level));
    if(it.work&&it.level<1){const [a,b,c,d]=rect(r,'#c9b48a');ctx.fillStyle='#9b8a6a';for(let i=0;i<6;i++)ctx.fillRect(a+(c-a)*((i*37)%10)/10,b+(d-b)*((i*53)%10)/10,5,3);return;}
    if(HOUSES[it.kind]){const {P}=view(),[a,b]=P(p.x,p.y);ctx.save();ctx.translate(a,b);ctx.scale(HOUSE_GROW,HOUSE_GROW);ctx.translate(-a,-b);paintHouse(it.kind,lv,it.look||0,houseView(p),{only:'ground'});ctx.restore();return;}
    switch(it.kind){
      case 'nha_san':rect(r,'rgba(201,167,122,.55)');break;
      case 'biet_thu':rect(r,'#e9e2d2');break;
      case 'lau_dai':rect(r,'#b9b3a8');break;
      case 'cong_vien':{const [a,b,c,d]=rect(r,'#8fd06a');ctx.fillStyle='#e9d7a6';ctx.fillRect((a+c)/2-3,b,6,d-b);ctx.fillRect(a,(b+d)/2-2,c-a,4);
        if(lv>1){const cols=['#ff8aa0','#ffd25a','#b48de0','#fff'];for(let i=0;i<10;i++){ctx.fillStyle=cols[i%4];ctx.beginPath();ctx.arc(a+(c-a)*((i*29)%10+.5)/10,b+(d-b)*(.62+((i*17)%10)/30),2.5,0,Math.PI*2);ctx.fill();}}
        if(lv>2){ctx.fillStyle='#d8d2c8';ctx.beginPath();ctx.ellipse((a+c)/2,(b+d)/2,(c-a)*.22,(d-b)*.2,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='#6ec6e0';ctx.beginPath();ctx.ellipse((a+c)/2,(b+d)/2,(c-a)*.16,(d-b)*.14,0,0,Math.PI*2);ctx.fill();}
        break;}
      case 'ho_boi':{rect(r,'#f1ebe0');const w=lv>1?.024:.028,[a,b,c]=rect({x:p.x-(lv>1?.006:0),y:p.y,w:w*2,h:w*2*.9},'#3fb3d9');ctx.fillStyle='rgba(255,255,255,.35)';ctx.fillRect(a+3,b+3,(c-a)*.6,3);break;}
      case 'golf':{const [a,b,c,d]=rect(r,'#7ccf5a');ctx.fillStyle='#2f6d2a';ctx.beginPath();ctx.ellipse(a+(c-a)*.68,b+(d-b)*.38,4,2,0,0,Math.PI*2);ctx.fill();
        if(lv>1){ctx.fillStyle='#f0dca0';ctx.beginPath();ctx.ellipse(a+(c-a)*.28,b+(d-b)*.3,(c-a)*.16,(d-b)*.12,0,0,Math.PI*2);ctx.fill();}break;}
      case 'cam_trai':rect(r,'rgba(182,201,122,.8)');break;
      case 'ben_thuyen':{rect(r,'#d8c39a');if(it.pier){const q=it.pier.rect;rect(q,'#6e4a2e');const [a,b,c,d]=rect({...q,h:q.h*.9},'#b5844f');ctx.strokeStyle='#8b6038';ctx.lineWidth=1;
        const long=q.h>q.w;for(let i=1;i<10;i++){ctx.beginPath();if(long){const yy=b+(d-b)*i/10;ctx.moveTo(a,yy);ctx.lineTo(c,yy);}else{const xx=a+(c-a)*i/10;ctx.moveTo(xx,b);ctx.lineTo(xx,d);}ctx.stroke();}}break;}
    }
  }

  function scaffold(p,it,t){
    const top=({lau_dai:110,biet_thu:66,nha_san:50}[it.kind]||(HOUSES[it.kind]?houseTop(it.kind,Math.max(1,it.next||1))*HOUSE_GROW:36))*(it.next>1?1:.75),bx=box(p.x,p.y,H*.78,H*.78,0,top,'rgba(79,174,106,.32)','rgba(63,154,90,.2)'),{k}=bx;
    ctx.strokeStyle='#8a6038';ctx.lineWidth=2.5;for(const f of [0,.5,1]){const xx=bx.a+(bx.c-bx.a)*f;ctx.beginPath();ctx.moveTo(xx,bx.base);ctx.lineTo(xx,bx.front);ctx.stroke();ctx.beginPath();ctx.moveTo(xx,bx.front);ctx.lineTo(xx,bx.top);ctx.stroke();}
    ctx.strokeStyle='#c49a5c';ctx.lineWidth=3;for(let z=12;z<=top;z+=14){const yy=bx.base-z*k;ctx.beginPath();ctx.moveTo(bx.a-2,yy);ctx.lineTo(bx.c+2,yy);ctx.stroke();}
    if(it.kind==='lau_dai'||it.kind==='biet_thu'||(HOUSES[it.kind]?.tier||0)>=3){ctx.strokeStyle='#f2b630';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(bx.a,bx.top);ctx.lineTo(bx.a,bx.top-46*k);ctx.lineTo(bx.c+30*k,bx.top-40*k);ctx.stroke();
      const sw=Math.sin(t/700)*4;ctx.strokeStyle='#444';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(bx.c+24*k,bx.top-40*k);ctx.lineTo(bx.c+24*k,bx.top-14*k+sw);ctx.stroke();ctx.fillStyle='#8a6038';ctx.fillRect(bx.c+18*k,bx.top-14*k+sw,12*k,5*k);}
    emoji('🏗️',bx.c,bx.top-2+Math.sin(t/450)*2,18*k+8);
  }

  function standOne(p,it,t){
    const lv=Math.max(1,Math.min(3,it.level));
    if(HOUSES[it.kind]){paintHouse(it.kind,lv,it.look||0,houseView(p),{only:'parts'});return;}
    switch(it.kind){
      case 'nha_san':{const hw=lv>1?.024:.02,hd=lv>1?.02:.017,z=14;const legs=box(p.x,p.y,hw,hd,0,z,'rgba(0,0,0,0)','rgba(0,0,0,0)');
        ctx.fillStyle='#6e4a2e';for(const f of [0,1])ctx.fillRect(legs.a+(legs.c-legs.a)*f-1.5,legs.front,3,legs.base-legs.front);
        box(p.x,p.y+(lv>1?.008:0),hw+.008,hd+.012,z,z+3,'#9b6a3c','#b5844f');const bx=box(p.x,p.y,hw,hd,z+3,z+24,'#d9b77a');windowsRow(bx,z+8,12,2,false);roof(bx,16,lv>2?'#7f8f45':'#a8743a');break;}
      case 'biet_thu':{const fl=lv>1?2:1,bx=box(p.x,p.y,.028,.024,0,fl*26,'#faf7f0');for(let f=0;f<fl;f++)windowsRow(bx,f*26+8,14,3,lv>2);
        ctx.fillStyle='#3f6f96';ctx.fillRect(bx.a+(bx.c-bx.a)*.44,bx.base-18*bx.k,(bx.c-bx.a)*.12,18*bx.k);
        if(lv>2){ctx.fillStyle='#d9483b';ctx.beginPath();ctx.moveTo(bx.a+(bx.c-bx.a)*.3-14,bx.top-14*bx.k);ctx.lineTo(bx.a+(bx.c-bx.a)*.3+14,bx.top-14*bx.k);ctx.lineTo(bx.a+(bx.c-bx.a)*.3,bx.top-24*bx.k);ctx.fill();}
        else roof(bx,18,'#3d7fb0');break;}
      case 'lau_dai':{const stone='#b7b0a6';if(lv>2)box(p.x,p.y,.034,.032,0,14,darker(stone,.92));const bx=box(p.x,p.y-.004,.022,.02,0,56,stone);windowsRow(bx,10,14,2,lv>2);windowsRow(bx,36,14,2,lv>2);
        ctx.fillStyle=darker(stone,.78);for(let i=0;i<4;i++)ctx.fillRect(bx.a+(bx.c-bx.a)*i/3.4,bx.top-5*bx.k,6*bx.k,6*bx.k);
        ctx.fillStyle='#5a3a22';ctx.fillRect(bx.a+(bx.c-bx.a)*.42,bx.base-20*bx.k,(bx.c-bx.a)*.16,20*bx.k);
        const tower=(f,ht,roofC)=>{const tx=bx.a+(bx.c-bx.a)*f,r=8*bx.k;ctx.fillStyle=stone;ctx.fillRect(tx-r,bx.base-ht*bx.k,r*2,ht*bx.k);ctx.fillStyle=roofC;ctx.beginPath();ctx.moveTo(tx-r-2,bx.base-ht*bx.k);ctx.lineTo(tx+r+2,bx.base-ht*bx.k);ctx.lineTo(tx,bx.base-(ht+22)*bx.k);ctx.fill();
          if(lv>1){const fy=bx.base-(ht+22)*bx.k;ctx.strokeStyle='#555';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(tx,fy);ctx.lineTo(tx,fy-12*bx.k);ctx.stroke();ctx.fillStyle='#d9483b';ctx.beginPath();ctx.moveTo(tx,fy-12*bx.k);ctx.lineTo(tx+(10+Math.sin(t/300)*2)*bx.k,fy-9*bx.k);ctx.lineTo(tx,fy-6*bx.k);ctx.fill();}};
        tower(1.05,78,'#b5453a');if(lv>1)tower(-.05,70,'#b5453a');if(lv>2)tower(.5,92,'#3f6f96');break;}
      case 'cong_vien':{tree(p.x-.02,p.y-.02,1);if(lv>1)tree(p.x+.02,p.y-.02,.85,'#5aa94e');const {P,S}=view(),k=S/900,[a,b]=P(p.x+.016,p.y+.018);ctx.fillStyle='#8a6038';ctx.fillRect(a-10*k,b-6*k,20*k,4*k);ctx.fillRect(a-9*k,b-2*k,2*k,5*k);ctx.fillRect(a+7*k,b-2*k,2*k,5*k);
        if(lv>2){const [fx,fy]=P(p.x,p.y);ctx.fillStyle='rgba(255,255,255,.85)';ctx.beginPath();ctx.ellipse(fx,fy-10*k-Math.sin(t/350)*2,3*k,9*k,0,0,Math.PI*2);ctx.fill();}break;}
      case 'ho_boi':{const {P,S}=view(),k=S/900;if(lv>1){const [ux,uy]=P(p.x+.026,p.y-.026);ctx.strokeStyle='#888';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(ux,uy);ctx.lineTo(ux,uy-24*k);ctx.stroke();ctx.fillStyle='#ff7a59';ctx.beginPath();ctx.ellipse(ux,uy-24*k,14*k,5*k,0,0,Math.PI*2);ctx.fill();
          for(const dy of [-.016,0,.016]){const [lx,ly]=P(p.x+.026,p.y+dy);ctx.fillStyle='#fff';ctx.fillRect(lx-7*k,ly-3*k,14*k,4*k);}}
        if(lv>2){const [sx,sy]=P(p.x-.03,p.y-.03),[ex,ey]=P(p.x-.012,p.y-.006);ctx.strokeStyle='#ffc93c';ctx.lineWidth=5*k;ctx.beginPath();ctx.moveTo(sx,sy-26*k);ctx.quadraticCurveTo(sx+14*k,(sy+ey)/2,ex,ey-2);ctx.stroke();}break;}
      case 'golf':{const {P,S}=view(),k=S/900,flag=(fx,fy,c)=>{const [a,b]=P(fx,fy);ctx.strokeStyle='#f2f2f2';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(a,b);ctx.lineTo(a,b-30*k);ctx.stroke();ctx.fillStyle=c;ctx.beginPath();ctx.moveTo(a,b-30*k);ctx.lineTo(a+(14+Math.sin(t/300)*2)*k,b-26*k);ctx.lineTo(a,b-22*k);ctx.fill();};
        flag(p.x+.012,p.y-.008,'#d9483b');if(lv>1)flag(p.x-.02,p.y+.02,'#ffc93c');
        if(lv>2){const [cx,cy]=P(p.x+.022,p.y+.02);ctx.fillStyle='#fff';ctx.fillRect(cx-9*k,cy-12*k,18*k,8*k);ctx.fillStyle='#3d7fb0';ctx.fillRect(cx-9*k,cy-16*k,18*k,4*k);}break;}
      case 'cam_trai':{const {P,S}=view(),k=S/900,tent=(tx,ty,sz,c)=>{const [a,b]=P(tx,ty);const w=sz*S,ht=24*k*sz/.012;ctx.fillStyle=c;ctx.beginPath();ctx.moveTo(a-w,b);ctx.lineTo(a+w,b);ctx.lineTo(a,b-ht);ctx.fill();ctx.fillStyle='#3a2a1a';ctx.beginPath();ctx.moveTo(a-w*.3,b);ctx.lineTo(a+w*.3,b);ctx.lineTo(a,b-ht*.6);ctx.fill();};
        tent(p.x-.012,p.y-.006,.012,'#e8833a');tent(p.x+.016,p.y-.012,lv>2?.014:.01,'#4f9a6a');
        if(lv>1){const [a,b]=P(p.x+.012,p.y+.018),fl=1+Math.sin(t/120)*.2;ctx.fillStyle='#6e4a2e';ctx.fillRect(a-8*k,b-2*k,16*k,3*k);ctx.fillStyle='#ff9a3a';ctx.beginPath();ctx.moveTo(a-6*k,b-2*k);ctx.lineTo(a+6*k,b-2*k);ctx.lineTo(a,b-16*k*fl);ctx.fill();}
        if(lv>2){const [a,b]=P(p.x-.03,p.y-.03),[c,d]=P(p.x+.03,p.y-.03);for(let i=0;i<=8;i++){const f=i/8;ctx.fillStyle=['#ffe08a','#ff8aa0','#9fd0e4'][i%3];ctx.beginPath();ctx.arc(a+(c-a)*f,b-22*k+(d-b)*f+Math.sin(f*Math.PI)*8*k,2.2,0,Math.PI*2);ctx.fill();}}break;}
      case 'ben_thuyen':{const {P,S}=view(),k=S/900,[a,b]=P(p.x,p.y);ctx.strokeStyle='#6e4a2e';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(a,b);ctx.lineTo(a,b-24*k);ctx.stroke();emoji('⚓',a,b-22*k,16*k+6);
        if(it.pier){const [ex,ey]=it.pier.end,[dx,dy]=it.pier.dir;boat(ex-dx*.03+(dy?.03:0),ey-dy*.03+(dx?.03:0),lv>2?1.3:lv>1?1.05:.8,lv,t);}break;}
    }
  }

  return {
    /** Everything that lies flat, under the people: `plots` [[x, y, coast]], `built` withBuilds().built. */
    ground(plots,built){(plots||[]).forEach(([x,y,c],i)=>groundOne({x,y,coast:Boolean(c)},(built||[]).find(b=>b.plot===i)||null));},
    /** [y, draw] of what stands up, sorted with the people by the walk. */
    standing(plots,built,t){
      const out=[];
      for(const it of built||[]){
        const p=(plots||[])[it.plot];if(!p)continue;const at={x:p[0],y:p[1]};
        if(it.level>=1)out.push([at.y+H*.8,()=>{const {P}=view(),[a,b]=P(at.x,at.y),K=GROW[it.kind]||(HOUSES[it.kind]?HOUSE_GROW:1);ctx.save();ctx.translate(a,b);ctx.scale(K,K);ctx.translate(-a,-b);standOne(at,it,t);ctx.restore();}]);
        if(it.work)out.push([at.y+H*.8+.0001,()=>scaffold(at,it,t)]);
        if(it.kind==='ben_thuyen'&&it.pier&&!it.work)out.push([it.pier.end[1],()=>{}]);
      }
      return out;
    },
  };
}
