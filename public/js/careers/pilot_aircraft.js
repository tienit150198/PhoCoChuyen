/** Exterior flight presentation. Geometry is drawn in CSS pixels; flight rules stay in pilot_fly. */
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
let painted=null,loading=false,tree=null,treeLoading=false;
export const airportTreeArt=()=>tree;
/** One small transparent sprite, fetched only when the player enters a flight. */
export function loadAircraftArt(){
  if(!tree&&!treeLoading&&typeof Image!=='undefined'){
    treeLoading=true;const foliage=new Image();foliage.decoding='async';foliage.onload=()=>{tree=foliage;treeLoading=false;};foliage.onerror=()=>{treeLoading=false;};
    const src='/icons/isometric/tree.webp';foliage.src=globalThis.__mnlBoot?.asset?.(src)||src;
  }
  if(painted||loading||typeof Image==='undefined')return;
  loading=true;const img=new Image();img.decoding='async';
  img.onload=()=>{painted=img;loading=false;};img.onerror=()=>{loading=false;};
  const src='/icons/cozy-v3/aircraft-chase.webp';img.src=globalThis.__mnlBoot?.asset?.(src)||src;
}
export function chaseCamera(state,view={w:640,h:400},focal=view.w*1.1){
  const back=320,up=160;
  return {x:state.x-Math.sin(state.psi)*back,z:state.z-Math.cos(state.psi)*back,y:state.h+up+3.2,pitch:-Math.atan2(up+3.2,back)+Math.atan(view.h*.24/focal)};
}
export function drawAircraft(c,view,state,time=0){
  const k=clamp(view.w/620,.52,1.35),x=view.w*.5,y=view.h*.66;
  const airborne=!state.ground,alt=Math.max(0,state.h||0),bank=clamp(state.ph||0,-.8,.8);
  c.save();c.translate(x,y);c.scale(k,k);
  if(alt<100){
    c.save();c.translate(12+alt*.16,18+alt*.25);c.scale(1,clamp(1-alt/180,.4,1));c.globalAlpha=.18*(1-alt/120);c.fillStyle='#263e3c';
    c.beginPath();c.ellipse(0,0,88,18,0,0,Math.PI*2);c.fill();c.restore();
  }
  c.rotate(-bank*.75);c.translate(0,airborne?Math.sin(time*1.8)*.7:0);
  const shape=(points,fill,line='#536e76')=>{c.beginPath();points.forEach(([px,py],i)=>i?c.lineTo(px,py):c.moveTo(px,py));c.closePath();c.fillStyle=fill;c.fill();c.strokeStyle=line;c.lineWidth=1.2;c.stroke();};
  const oval=(px,py,rx,ry,fill)=>{c.beginPath();c.ellipse(px,py,rx,ry,0,0,Math.PI*2);c.fillStyle=fill;c.fill();c.strokeStyle='#536e76';c.lineWidth=1;c.stroke();};
  if(state.gear){for(const side of [-1,1]){shape([[side*17,8],[side*20,8],[side*20,20],[side*17,20]],'#69767a');oval(side*19,20,3.5,5,'#445456');}}
  if(painted){c.drawImage(painted,-106,-72,212,141.333);c.restore();return;}
  // Broad swept wings, shadowed lower edge and warm enamel on the upper surface.
  shape([[-7,-18],[-90,20],[-91,28],[-11,14],[11,14],[91,28],[90,20],[7,-18]],'#94adb0');
  shape([[-7,-21],[-88,15],[-89,23],[-11,8],[11,8],[89,23],[88,15],[7,-21]],'#e8ece1');
  for(const side of [-1,1]){
    shape([[side*33,-1],[side*44,3],[side*44,24],[side*35,22]],'#769d9e');
    oval(side*39,20,6,8,'#527e83');oval(side*39,23,4,3,'#334d54');
    c.strokeStyle='#b9c7bd';c.lineWidth=1;c.beginPath();c.moveTo(side*17,6);c.lineTo(side*77,19);c.stroke();
    oval(side*87,17,2.5,1.6,side<0?'#d46e59':'#82b883');
  }
  // Rounded fuselage and glazed cockpit, seen from behind and above.
  const enamel=c.createLinearGradient(-13,0,13,0);enamel.addColorStop(0,'#bdceca');enamel.addColorStop(.35,'#fff9e8');enamel.addColorStop(1,'#d7e3dc');
  c.beginPath();c.moveTo(0,-58);c.bezierCurveTo(12,-57,13,-24,12,8);c.bezierCurveTo(10,29,5,44,0,47);c.bezierCurveTo(-5,44,-10,29,-12,8);c.bezierCurveTo(-13,-24,-12,-57,0,-58);c.closePath();c.fillStyle=enamel;c.fill();c.strokeStyle='#5c767a';c.lineWidth=1.3;c.stroke();
  shape([[-7,-41],[-5,-46],[5,-46],[7,-41],[6,-36],[-6,-36]],'#78a5af');
  c.strokeStyle='#fff9e8';c.lineWidth=.8;c.beginPath();c.moveTo(0,-45);c.lineTo(0,-37);c.stroke();
  for(const side of [-1,1])for(let n=0;n<6;n++)oval(side*9,-29+n*5.5,1.2,1.7,'#628c97');
  shape([[-3,22],[-35,38],[-35,43],[-2,36],[2,36],[35,43],[35,38],[3,22]],'#c2d6d0');
  shape([[-2,32],[-3,5],[1,-3],[6,30],[1,43]],'#468a86');
  shape([[0,12],[2,12],[4,29],[1,36]],'#e8c981');
  c.restore();
}
