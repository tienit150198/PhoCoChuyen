/** Continuous rider controls. Positive drive is forward, negative is reverse. */
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
const towardZero=(v,amount)=>Math.abs(v)<=amount?0:Math.sign(v)*(Math.abs(v)-amount);
export function joystickAxes(x,y){
  const length=Math.max(1,Math.hypot(x,y));
  const axis=v=>Math.abs(v)<=.14?0:Math.sign(v)*(Math.abs(v)-.14)/.86;
  return {steer:axis(x/length),drive:axis(-y/length)};
}
/** Exponential response gives the same steering feel at 30, 60 and 120 fps. */
export const nextSteer=(value,target,dt)=>target+(value-target)*Math.exp(-12*Math.max(0,dt));

/** One finger owns a control until release. The touch origin avoids a jump on contact.
 * reset is also used by blur, hidden pages, overlays and full-screen transitions. */
export function holdPointer(element,{enabled=()=>true,start=()=>{},move=()=>{},end=()=>{}}){
  let pointer=null,origin=null;
  const reset=()=>{
    if(pointer===null)return;
    const id=pointer;pointer=null;origin=null;end();
    try{if(element.hasPointerCapture(id))element.releasePointerCapture(id);}catch{/* already cancelled */}
  };
  element.addEventListener('pointerdown',e=>{
    if(pointer!==null||e.button!==0||!enabled())return;
    e.preventDefault();pointer=e.pointerId;origin={x:e.clientX,y:e.clientY};
    try{element.setPointerCapture(pointer);}catch{/* still handle release and blur */}
    start(e);
  });
  element.addEventListener('pointermove',e=>{
    if(e.pointerId!==pointer)return;
    if(!enabled()){reset();return;}
    e.preventDefault();move(e,origin);
  });
  for(const name of ['pointerup','pointercancel','lostpointercapture'])
    element.addEventListener(name,e=>{if(e.pointerId===pointer)reset();});
  element.addEventListener('contextmenu',e=>e.preventDefault());
  return reset;
}
export function nextSpeed(v,{drive=0,brake=false},dt,vmax=15){
  drive=clamp(drive,-1,1);
  if(brake||v*drive<0)return towardZero(v,16*dt);
  if(!drive)return towardZero(v,4.5*dt);
  const limit=(drive<0?4:vmax)*Math.abs(drive),acc=drive<0?3.2:7;
  const speed=Math.abs(v);
  if(speed>limit)return Math.sign(v)*Math.max(limit,speed-7*dt);
  return Math.sign(drive)*Math.min(limit,speed+acc*Math.abs(drive)*dt*(1-speed/(limit*1.08)));
}
export const motionSign=(speed,drive)=>Math.sign(speed)||Math.sign(drive)||1;
