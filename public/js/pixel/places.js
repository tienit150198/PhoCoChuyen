/** Shared outdoor scenery: free rowing, private fishing/pool rounds. Public coordinates stay 320x200. */
import {getCharacterStamp} from '../isometric/character-art.js';
import {createMovementController} from '../isometric-movement.js';
import {leisurePresence} from '../isometric/leisure-presence.js';
import {createLeisureActors} from '../isometric/leisure-actors.js';
import {lookOf} from '../v4/look.js';
import {drawSwimmer,drawRowboat} from '../isometric/water-poses.js';
import {placeGeometry,placeWorldPoint,walkablePlace,moveInPlace} from './place-geometry.js';
export {walkablePlace} from './place-geometry.js';

const KINDS=['fishing','boat','pool'],TITLES={fishing:'Bờ hồ câu cá',boat:'Bến chèo thuyền',pool:'Hồ bơi khu phố'};
const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);

/** Small deterministic simulation, independent of DOM and rendering. */
export function createPixelPlay(kind,{command,now=()=>Date.now(),onChange=()=>{}}){
  if(!KINDS.includes(kind))throw new Error('Hoạt động không hợp lệ.');
  const geometry=placeGeometry(kind),dock={x:geometry.dock[0],y:geometry.dock[1]};
  const state={kind,x:geometry.start[0],y:geometry.start[1],direction:'ne',heading:-Math.PI/4,phase:'walk',busy:false,round:null,next:0,progress:0,moving:false,action:null,message:kind==='pool'?'Đi tới thang hồ bằng cần tròn hoặc phím mũi tên / W A S D.':'Đi tới đầu cầu gỗ bằng cần tròn hoặc phím mũi tên / W A S D.',stats:null};
  if(kind==='boat')state.mooring={x:geometry.entry[0],y:geometry.entry[1],heading:-Math.PI/2};
  let alive=true,input={x:0,y:0},offset=0,retryAt=0,checkpointRequest=null;
  const emit=()=>{if(alive)onChange(state);};
  const animate=(kind,duration,from=[state.x,state.y],to=from)=>{state.action={kind,at:now(),duration,from:[...from],to:[...to]};};
  function setInput(x,y){if(!alive)return;const n=Math.hypot(x,y);input=Number.isFinite(n)?{x:x/Math.max(1,n),y:y/Math.max(1,n)}:{x:0,y:0};}
  async function send(action,payload,success,checkpointRound=null){
    if(!alive||state.busy||checkpointRound&&checkpointRequest===checkpointRound)return;
    const relevant=()=>alive&&(!checkpointRound||state.phase==='pool'&&state.round===checkpointRound);
    let accepted=false;
    if(checkpointRound)checkpointRequest=checkpointRound;else{state.busy=true;emit();}
    try{const result=await command(action,payload);if(!relevant())return;accepted=true;success(result||{});}
    catch(error){if(!relevant())return;accepted=true;state.action=null;state.message=error?.message||'Mất kết nối. Thử lại để lưu cùng vòng chơi này.';
      retryAt=now()+1500;if(['missed','expired','bad_round'].includes(error?.data?.code)){
        if(kind!=='fishing'&&['boat','pool','return'].includes(state.phase)){
          // Keep the physical way out, without retaining expired checkpoint/finish proof.
          const entry=state.round?.entry||geometry.entry;state.phase='return';state.round={entry:[entry[0],entry[1]]};
          state.message=`Vòng đã kết thúc, quay về ${kind==='boat'?'bến':'thang'} để lên bờ.`;
        }else{state.phase='walk';state.round=null;}
      }}
    finally{
      if(checkpointRound){if(checkpointRequest===checkpointRound)checkpointRequest=null;if(accepted&&alive)emit();}
      else if(alive){state.busy=false;emit();}
    }
  }
  function step(dt){
    if(!alive)return;
    if(state.action&&now()-state.action.at>=state.action.duration){state.action=null;emit();}
    const moving=['walk','boat','pool','return'].includes(state.phase)&&!state.busy&&!state.action;
    state.moving=Boolean(moving&&(input.x||input.y));
    if(moving&&(input.x||input.y)){
      // Speed is measured in the same art space as the shoreline and pier.
      const water=state.phase!=='walk',speed=water?(kind==='boat'?54:56):42,delta=Math.max(0,Math.min(.05,Number(dt)||0))*speed;
      const next=moveInPlace(kind,state,input.x*delta,input.y*delta,water);state.x=next.x;state.y=next.y;
      state.direction=input.y<0?(input.x<0?'nw':'ne'):(input.x<0?'sw':'se');
      state.heading=Math.atan2(input.y,input.x);
    }
    if(state.phase==='waiting'||state.phase==='bite'){
      const t=now()/1000+offset,r=state.round;
      state.progress=Math.max(0,Math.min(1,(t-r.now)/(r.bite_at-r.now+r.bite_window)));
      if(t>r.bite_at+r.bite_window){state.phase='walk';state.round=null;state.message='Cá nhả mồi rồi. Bấm thả cần để thử lại.';emit();}
      else if(t>=r.bite_at&&state.phase!=='bite'){state.phase='bite';state.message='Cá cắn câu! Bấm Giật cần hoặc phím Space ngay!';emit();}
    }
    if(state.phase==='pool'&&!state.busy&&!state.action&&state.round&&checkpointRequest!==state.round&&now()>=retryAt){
      const target=state.round.checkpoints[state.next];
      if(target&&distance(state,{x:target[0],y:target[1]})<=8){
        const index=state.next;
        void send('jr_leisure_checkpoint',{round:state.round.id,index,x:Math.round(state.x*100)/100,y:Math.round(state.y*100)/100},result=>{
          state.next=Number.isInteger(result.next)?result.next:index+1;
          state.message=state.next<state.round.checkpoints.length?`Qua mốc ${state.next}/${state.round.checkpoints.length}. Đi đến vòng đang sáng.`:'Đã về thang hồ. Chọn Lưu vòng bơi để ghi thành tích hoặc Lên bờ.';
        },state.round);
      }
    }
  }
  async function interact(){
    if(!alive||state.busy||state.action)return;
    if(state.phase==='walk'){
      if(distance(placeWorldPoint(kind,state),placeWorldPoint(kind,dock))>18||!walkablePlace(kind,state.x,state.y)){state.message=kind==='pool'?'Đi đến thang hồ trước nhé.':'Đi đến đầu cầu gỗ trước nhé.';emit();return;}
      if(kind==='boat'){
        const from=[state.x,state.y];state.phase='boat';state.round=null;state.next=0;
        state.x=state.mooring.x;state.y=state.mooring.y;state.heading=state.mooring.heading;
        setInput(0,0);animate('board',700,from,[state.x,state.y]);
        state.message='Chèo tự do quanh hồ. Muốn lên bờ, quay lại bên phải cầu gỗ.';emit();return;
      }
      const from=[state.x,state.y];if(kind==='fishing')animate('cast',700);emit();
      await send('jr_leisure_start',{kind},result=>{
        const r=result.leisure_round;if(!r?.id)throw new Error('Chưa nhận được vòng chơi. Thử lại nhé.');
        state.round=r;state.next=r.next||0;state.stats=result.leisure||state.stats;offset=r.now-now()/1000;setInput(0,0);
        if(kind==='fishing'){animate('cast',700);state.phase='waiting';state.message='Đã thả mồi. Chờ phao rung rồi bấm Giật cần trong vạch sáng.';}
        else{state.phase=kind;state.x=r.entry[0];state.y=r.entry[1];state.heading=-Math.PI/2;animate('board',700,from,r.entry);state.message='Bơi tự do hoặc qua từng vòng mốc. Về thang rồi chọn Lên bờ.';}
      });
    }else if(state.phase==='boat'){
      await leave();
    }else if(state.phase==='bite'||(state.phase==='pool'&&state.next===state.round.checkpoints.length)){
      if(kind==='fishing'){animate('reel',750);emit();}
      await send('jr_leisure_finish',{round:state.round.id},result=>{
        state.stats=result.leisure||state.stats;state.message=result.message||'Đã lưu thành tích.';
        state.phase=kind==='fishing'?'walk':'return';if(kind==='fishing')animate('caught',1900);setInput(0,0);
      });
    }else if(state.phase==='return'){
      const landing=kind==='boat'?geometry.entry:state.round.entry,entry={x:landing[0],y:landing[1]};
      if(distance(placeWorldPoint(kind,state,true),placeWorldPoint(kind,entry,true))>18){state.message=kind==='boat'?'Chèo về chỗ thuyền đậu bên phải cầu gỗ rồi chọn Lên bờ.':'Bơi về thang ở mép dưới hồ rồi chọn Lên bờ.';emit();return;}
      if(kind==='boat')state.mooring={x:state.x,y:state.y,heading:state.heading};
      const from=[state.x,state.y];state.phase='walk';state.x=dock.x;state.y=dock.y;animate('exit',700,from,[state.x,state.y]);state.round=null;state.message='Đã lên bờ. Có thể chơi thêm hoặc trở về khu phố.';setInput(0,0);emit();
    }
  }
  async function leave(){
    if(!alive||state.busy||state.action||!['boat','pool','return'].includes(state.phase))return;
    const entry=state.round?.entry||geometry.entry;state.phase='return';state.round=kind==='boat'?null:{entry:[...entry]};state.next=0;setInput(0,0);
    await interact();
  }
  function needsFrame(){
    if(!alive)return false;if(state.action||state.phase==='waiting'||state.phase==='bite')return true;
    if(state.busy)return false;if(input.x||input.y)return true;
    const target=state.round?.checkpoints?.[state.next];return state.phase==='pool'&&checkpointRequest!==state.round&&!!target&&distance(state,{x:target[0],y:target[1]})<=8;
  }
  function reset(){const changed=state.moving||input.x||input.y;setInput(0,0);state.moving=false;if(changed)emit();}
  return {state,input:setInput,step,interact,leave,needsFrame,reset,destroy(){input={x:0,y:0};state.moving=false;alive=false;}};
}

/** One RAF owner; suspend/destroy cancel it and release every held input. */
export function createPlaceLifecycle({step,render,reset,needsFrame=()=>false},{raf=f=>requestAnimationFrame(f),caf=i=>cancelAnimationFrame(i),now=()=>performance.now()}={}){
  let id=null,last=0,enabled=false,destroyed=false,paintAt=0,dirty=false,processing=false,resetting=false;
  function schedule(){if(enabled&&!destroyed&&!processing&&id===null){last=now();id=raf(frame);}}
  function wake(){if(!enabled||destroyed||resetting)return;dirty=true;schedule();}
  function frame(t,force=false){
    id=null;if(!enabled||destroyed)return;processing=true;
    try{step(Math.min(.05,Math.max(0,(t-last)/1000)));last=t;
      if(force||dirty||needsFrame()&&t-paintAt>=32){dirty=false;render();paintAt=t;}}
    finally{processing=false;}
    if(enabled&&!destroyed&&(dirty||needsFrame()))id=raf(frame);
  }
  function suspend(){enabled=false;dirty=false;if(id!==null)caf(id);id=null;resetting=true;try{reset();}finally{resetting=false;}}
  return {wake,resume(){if(destroyed||resetting||enabled)return;enabled=true;last=now();frame(last,true);},suspend,
    destroy(){if(destroyed)return;destroyed=true;suspend();}};
}

function scenery(kind,art={}){
  const custom=art.background?.(kind,320,200);if(custom)return custom.canvas||custom;
  throw new Error('Cảnh hồ chưa sẵn sàng. Thử mở lại hoạt động nhé.');
}

const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
/** Cover the viewport without stretching; the pool has twice the usable art-space scale. */
export function placeCamera(width,height,actor={x:160,y:100},kind='boat'){
  const world=placeGeometry(kind);
  width=Math.max(1,width);height=Math.max(1,height);const scale=Math.max(width/world.width,height/world.height),viewWidth=width/scale,viewHeight=height/scale;
  return {scale,width,height,viewWidth,viewHeight,x:clamp(actor.x-viewWidth/2,0,world.width-viewWidth),y:clamp(actor.y-viewHeight*.65,0,world.height-viewHeight)};
}
export function placePoint(camera,x,y){return {x:camera.x+x/camera.scale,y:camera.y+y/camera.scale};}

export function leisurePose(state,time=0,wallTime=Date.now(),networkHeading=false){
  const step=state.moving?Math.floor(time/180)%4:0;
  const action=state.action,progress=action?clamp((wallTime-action.at)/action.duration,0,1):0,ease=progress*progress*(3-2*progress);
  const water=['boat','pool','return'].includes(state.phase),kind=state.kind||'fishing',travel=action&&['board','exit'].includes(action.kind);
  const point=placeWorldPoint(kind,state,water),from=travel?placeWorldPoint(kind,{x:action.from[0],y:action.from[1]},action.kind==='exit'):point,to=travel?placeWorldPoint(kind,{x:action.to[0],y:action.to[1]},action.kind==='board'):point;
  const x=travel?from.x+(to.x-from.x)*ease:point.x,y=travel?from.y+(to.y-from.y)*ease-Math.sin(progress*Math.PI)*3:point.y;
  let heading=Number.isFinite(state.heading)?state.heading:({se:Math.PI/4,sw:Math.PI*3/4,nw:-Math.PI*3/4,ne:-Math.PI/4}[state.direction]??Math.PI/4);
  if(networkHeading){const a=placeWorldPoint(kind,{x:0,y:0},water),b=placeWorldPoint(kind,{x:Math.cos(heading),y:Math.sin(heading)},water);heading=Math.atan2(b.y-a.y,b.x-a.x);}
  return {walkFrame:step===1?1:step===3?2:0,step,
    heading,water,bob:Math.sin(time/350)*.65,x,y,action:action?.kind||null,progress,
    fishingPose:action?.kind==='caught'&&progress<.18?'reel':action&&['cast','reel','caught'].includes(action.kind)?action.kind:'ready'};
}

function ripple(ctx,x,y,radius,alpha=.55){
  ctx.strokeStyle=`rgba(226,250,237,${alpha})`;ctx.lineWidth=.8;ctx.beginPath();ctx.ellipse(x,y,radius,radius*.28,0,0,Math.PI*2);ctx.stroke();
}

function checkpoint(ctx,x,y,index,current,done,time,font='system-ui'){
  const r=current?8.5+Math.sin(time/350)*.7:7;
  ctx.save();ctx.shadowColor=current?'#f6dc8980':'transparent';ctx.shadowBlur=current?4:0;
  ctx.fillStyle=done?'#487b5870':current?'#fff0af80':'#f7eadc35';ctx.strokeStyle=done?'#3f7754':current?'#fff1bc':'#fff6e5aa';ctx.lineWidth=current?1.8:1;
  ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.shadowBlur=0;
  ctx.fillStyle=done?'#e9f5df':'#fff8ed';ctx.font=`600 7px ${font}`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(String(index+1),x,y+.3);ctx.restore();
}

function drawFishing(ctx,state,pose,time,art,grip){
  const hand={x:pose.x+(grip?.x??6),y:pose.y+(grip?.y??-14)},target={x:pose.x+38,y:pose.y-39};let angle=-1.05,flight=1;
  if(pose.action==='cast'){const p=pose.progress;angle=p<.35?-1.05-p/.35*1.65:-2.7+(p-.35)/.65*1.65;flight=clamp((p-.35)/.65,0,1);}
  if(pose.action==='reel')angle=-1.05-Math.sin(pose.progress*Math.PI)*.75;
  if(pose.action==='caught')angle=pose.progress<.18?-1.05-Math.sin(pose.progress/.18*Math.PI)*.8:-1.4;
  if(state.phase==='bite')angle+=Math.sin(time/60)*.045;
  const tip={x:hand.x+Math.cos(angle)*29,y:hand.y+Math.sin(angle)*29};
  ctx.lineCap='round';ctx.strokeStyle='#7a5539';ctx.lineWidth=1.4;ctx.beginPath();ctx.moveTo(hand.x-2,hand.y+3);ctx.quadraticCurveTo(hand.x+Math.cos(angle)*17,hand.y+Math.sin(angle)*17-2,tip.x,tip.y);ctx.stroke();
  ctx.strokeStyle='#e4c88c';ctx.lineWidth=.55;ctx.beginPath();ctx.moveTo(hand.x+Math.cos(angle)*3,hand.y+Math.sin(angle)*3);ctx.lineTo(tip.x,tip.y);ctx.stroke();
  ctx.fillStyle='#c7a373';ctx.strokeStyle='#6b4d3c';ctx.lineWidth=.5;ctx.beginPath();ctx.ellipse(hand.x-1,hand.y+1,1.8,1.5,angle,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle='#7b5b42';ctx.beginPath();ctx.arc(hand.x-1,hand.y+1,.55,0,Math.PI*2);ctx.fill();
  const cast=pose.action==='cast',hooked=pose.action==='caught',lineOut=['waiting','bite'].includes(state.phase)||cast||pose.action==='reel'||hooked;
  if(!lineOut){ctx.strokeStyle='#fff2d6aa';ctx.lineWidth=.5;ctx.beginPath();ctx.moveTo(tip.x,tip.y);ctx.lineTo(tip.x,tip.y+4);ctx.stroke();return;}
  const bob=state.phase==='bite'?Math.sin(time/55)*1.9:pose.bob;
  let float={x:hand.x+(target.x-hand.x)*flight,y:hand.y+(target.y-hand.y)*flight-Math.sin(flight*Math.PI)*28+bob};
  if(hooked){const p=clamp((pose.progress-.16)/.48,0,1);float={x:target.x+(hand.x-target.x)*p,y:target.y+(hand.y-7-target.y)*p-Math.sin(p*Math.PI)*27};}
  const fish=art.asset?.('fish'),wiggle=Math.sin(time/95)*.2,fishHeight=14*(fish?.naturalHeight||1)/(fish?.naturalWidth||1),dx=fish?6:5,dy=fish?-fishHeight*.4:-1;
  const lineEnd=hooked&&pose.progress>=.16?{x:float.x+dx*Math.cos(wiggle)-dy*Math.sin(wiggle),y:float.y+dx*Math.sin(wiggle)+dy*Math.cos(wiggle)}:float;
  ctx.strokeStyle='#fff9e2dd';ctx.lineWidth=.55;ctx.beginPath();ctx.moveTo(tip.x,tip.y);ctx.quadraticCurveTo((tip.x+lineEnd.x)/2,(tip.y+lineEnd.y)/2+(hooked?2:8),lineEnd.x,lineEnd.y);ctx.stroke();
  if(hooked&&pose.progress>=.16){ctx.save();ctx.translate(float.x,float.y);ctx.rotate(wiggle);
    if(fish){const w=14,h=w*(fish.naturalHeight||1)/(fish.naturalWidth||1);ctx.drawImage(fish,-w/2,-h/2,w,h);}
    else{ctx.fillStyle='#e2ad6e';ctx.beginPath();ctx.ellipse(0,0,6,3.5,-.2,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.moveTo(-5,0);ctx.lineTo(-9,-4);ctx.lineTo(-9,4);ctx.closePath();ctx.fill();ctx.fillStyle='#3d4b47';ctx.beginPath();ctx.arc(3,-1,.7,0,Math.PI*2);ctx.fill();}
    ctx.restore();ctx.strokeStyle='#725842';ctx.lineWidth=.45;ctx.beginPath();ctx.arc(lineEnd.x,lineEnd.y+.7,.9,-Math.PI/2,Math.PI*.8);ctx.stroke();if(pose.progress<.25)ripple(ctx,target.x,target.y+3,5+pose.progress*35,.8);
  }else{if(flight>.8)ripple(ctx,float.x,float.y+3,5+Math.sin(time/240)*.6,.55);ctx.fillStyle='#ee9877';ctx.beginPath();ctx.ellipse(float.x,float.y,1.8,3,.1,0,Math.PI*2);ctx.fill();ctx.fillStyle='#fff8df';ctx.beginPath();ctx.ellipse(float.x,float.y-2,1.8,1.3,.1,0,Math.PI*2);ctx.fill();}
}

function drawPlaceActor(ctx,kind,s,pose,time,art,appearance,{local=false,name='',font='system-ui'}={}){
  const boarding=pose.action==='board',entering=boarding&&pose.progress<.85;
  // Water limbs are articulated separately. Walking atlas rows shift the head crop.
  const waterHead=pose.water&&(kind==='pool'||kind==='boat')&&!entering;
  const options={...appearance,direction:s.direction,step:waterHead?0:pose.step,walkFrame:waterHead?0:pose.walkFrame};
  const fishing=kind==='fishing'&&!s.moving,char=(fishing?art.fishingCharacter?.({...options,pose:pose.fishingPose}):null)||art.character?.(options)||getCharacterStamp(options),stamp=char.canvas||char;
  const entry=placeGeometry(kind).entry,mooring=placeWorldPoint(kind,s.mooring||{x:entry[0],y:entry[1]},true),mooringHeading=s.mooring?.heading??-Math.PI/2;
  if(kind==='boat'&&(local||pose.water)){
    const moored=!pose.water||entering,boatX=moored?mooring.x:pose.x,boatY=moored?mooring.y:pose.y+pose.bob;
    if(moored)drawRowboat(ctx,null,{...pose,x:boatX,y:boatY,heading:mooringHeading},time,false,appearance);
  }
  if(pose.water&&kind==='boat'&&!entering)drawRowboat(ctx,stamp,boarding?{...pose,...mooring,heading:mooringHeading}:pose,time,s.moving,appearance);
  else if(pose.water&&kind==='pool'&&!entering)drawSwimmer(ctx,stamp,pose,time,s.moving,appearance);
  else{ctx.save();ctx.translate(pose.x,pose.y);if(pose.action==='cast')ctx.rotate(Math.sin(pose.progress*Math.PI)*-.12);if(pose.action==='reel')ctx.rotate(Math.sin(pose.progress*Math.PI)*-.18);if(pose.action==='caught'&&pose.progress<.18)ctx.rotate(Math.sin(pose.progress/.18*Math.PI)*-.18);ctx.drawImage(stamp,-12,-32,24,32);ctx.restore();}
  if(fishing)drawFishing(ctx,s,pose,time,art,char.hand);
  if(name){ctx.save();ctx.font=`6px ${font}`;ctx.textAlign='center';ctx.textBaseline='bottom';const width=Math.min(78,ctx.measureText(name).width+7);ctx.fillStyle='#fff6dce8';ctx.fillRect(pose.x-width/2,pose.y-42,width,9);ctx.fillStyle='#604b37';ctx.fillText(name,pose.x,pose.y-34,72);ctx.restore();}
}

let active=null;
/** App routing entry point; supports free play with no current career. */
export function openPixelPlace(kind,env){
  kind=({fish:'fishing',pond:'fishing',swim:'pool',boating:'boat'})[kind]||kind;
  if(!KINDS.includes(kind))return false;active?.destroy();
  const art=env.leisureArt||{},bg=scenery(kind,art),world=placeGeometry(kind),opener=document.activeElement,dialog=document.createElement('dialog');dialog.className='leisure-place pixel-place place-scene';dialog.dataset.place=kind;
  dialog.setAttribute('aria-label',TITLES[kind]);dialog.setAttribute('aria-modal','true');
  dialog.innerHTML=`<canvas width="960" height="600" tabindex="0" aria-label="${TITLES[kind]}: di chuyển rồi tương tác"></canvas><header class="place-heading"><button type="button" data-close aria-label="Trở về khu phố">←</button><h2>${TITLES[kind]}</h2></header><p class="place-help">Di chuyển: cần tròn · ↑ ↓ ← → / W A S D · Tương tác: Space</p><p data-record class="place-record"></p><p data-status class="place-status" role="status" aria-live="polite"></p><div class="place-controls"><div data-stick tabindex="0" role="group" aria-label="Kéo cần tròn để di chuyển"><span data-knob aria-hidden="true"></span></div><button type="button" data-leave hidden></button><button type="button" data-play></button></div>`;
  document.body.append(dialog);
  const uiFont=getComputedStyle(dialog).fontFamily||'system-ui';
  const canvas=dialog.querySelector('canvas'),ctx=canvas.getContext('2d'),status=dialog.querySelector('[data-status]'),button=dialog.querySelector('[data-play]'),leaveButton=dialog.querySelector('[data-leave]'),record=dialog.querySelector('[data-record]'),stick=dialog.querySelector('[data-stick]'),knob=dialog.querySelector('[data-knob]');
  canvas.style.imageRendering=art.pixelated===false?'auto':'pixelated';
  const listeners=[],peers=createLeisureActors(kind);let destroyed=false,focused=true,statusText='',camera=placeCamera(960,600),viewport={width:960,height:600},cameraAt=0,peerFrameAt=0,loop=null,cameraSettling=false;
  function wake(){if(!destroyed)loop?.wake();}
  const unsubscribe=leisurePresence.subscribe(kind,people=>{const changed=peers.receive(people);dialog.dataset.peers=String(people.length);if(changed)wake();});
  function listen(target,type,fn,options){target.addEventListener(type,fn,options);listeners.push(()=>target.removeEventListener(type,fn,options));}
  function sync(){
    if(destroyed||!dialog.open)return;const s=play.state;
    if(statusText!==s.message){statusText=s.message;status.textContent=s.message;}
    const labels={walk:kind==='fishing'?'Thả cần':kind==='boat'?'Lên thuyền':'Xuống hồ',waiting:'Chờ cá…',bite:'Giật cần!',boat:'Lên bờ',pool:'Lưu vòng bơi',return:'Lên bờ'};
    const hadFocus=document.activeElement===button,hadLeaveFocus=document.activeElement===leaveButton;
    button.textContent=s.action?.kind==='caught'?'Bắt được cá!':s.busy?'Đang xác nhận…':labels[s.phase];button.disabled=s.busy||!!s.action||s.phase==='waiting'||(s.phase==='pool'&&s.next<(s.round?.checkpoints?.length||0));
    leaveButton.hidden=s.phase!=='pool';leaveButton.disabled=s.busy||!!s.action;leaveButton.textContent='Lên bờ';
    // Disabling the boarding/cast button must not send keyboard input outside the modal.
    if(hadFocus&&button.disabled||hadLeaveFocus&&(leaveButton.disabled||leaveButton.hidden))canvas.focus({preventScroll:true});
    const stats=s.stats||env.api.state?.journey?.leisure||{};
    record.hidden=kind==='boat';record.textContent=kind==='boat'?'':`${Object.values(stats.fish||{}).reduce((n,v)=>n+(Number(v)||0),0)} cá · ${stats.swim_laps||0} vòng bơi`;
  }
  const play=createPixelPlay(kind,{command:(action,payload)=>env.api.command(action,payload,null),onChange:()=>{sync();wake();}});
  if(art.notice)play.state.message+=` ${art.notice}`;
  const control=createMovementController({onInput:(x,y)=>{play.input(x,y);if(!x&&!y){play.reset();leisurePresence.publish(play.state);}wake();},onVisual:({x,y})=>{knob.style.transform=`translate(-50%,-50%) translate(${x*30}px,${y*30}px)`;},capturePointer:id=>stick.setPointerCapture(id),releasePointer:id=>stick.releasePointerCapture(id)});
  function resize(){
    if(destroyed)return;const box=canvas.getBoundingClientRect();viewport={width:Math.max(1,box.width||window.innerWidth),height:Math.max(1,box.height||window.innerHeight)};
    const ratio=Math.min(2,Math.max(1.5,window.devicePixelRatio||1),Math.sqrt(2600000/(viewport.width*viewport.height)),4096/Math.max(viewport.width,viewport.height));
    canvas.width=Math.round(viewport.width*ratio);canvas.height=Math.round(viewport.height*ratio);
    camera=placeCamera(viewport.width,viewport.height,leisurePose(play.state),kind);cameraAt=0;cameraSettling=false;wake();
  }
  function render(){
    if(destroyed||!dialog.open)return;const s=play.state,time=performance.now(),pose=leisurePose(s,time);
    leisurePresence.publish(s);
    const nextCamera=placeCamera(viewport.width,viewport.height,{x:pose.x+(kind==='fishing'&&s.phase!=='walk'?12:0),y:pose.y},kind),blend=cameraAt?1-Math.exp(-(time-cameraAt)/120):1;
    camera={...nextCamera,x:camera.x+(nextCamera.x-camera.x)*blend,y:camera.y+(nextCamera.y-camera.y)*blend};cameraAt=time;
    cameraSettling=Math.abs(nextCamera.x-camera.x)+Math.abs(nextCamera.y-camera.y)>.025;
    if(!cameraSettling){camera.x=nextCamera.x;camera.y=nextCamera.y;}
    if(kind==='boat'){
      const edge=(pose.y-camera.y)*camera.scale>viewport.height*.72?'top':'bottom';
      if(dialog.dataset.hintEdge!==edge)dialog.dataset.hintEdge=edge;
    }
    const ratio=canvas.width/viewport.width,scale=camera.scale*ratio;
    // Clear in backing-store coordinates, including any area outside the scenery.
    ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.setTransform(scale,0,0,scale,-camera.x*scale,-camera.y*scale);ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(bg,0,0,world.width,world.height);
    for(const [x,y] of [[146,90],[215,110],[123,138]]){const p=placeWorldPoint(kind,{x,y},true);ripple(ctx,p.x,p.y,5+Math.sin(time/900+x)*1.5,.11);}
    if(kind==='pool'&&s.round?.checkpoints)s.round.checkpoints.forEach(([x,y],i)=>{const p=placeWorldPoint(kind,{x,y},true);checkpoint(ctx,p.x,p.y,i,i===s.next,i<s.next,time,uiFont);});
    const actors=peers.sample(peerFrameAt?(time-peerFrameAt)/1000:0).map(peer=>({...peer,pose:leisurePose(peer.state,time,Date.now(),true)}));peerFrameAt=time;
    actors.push({local:true,state:s,pose,look:lookOf(env.api.state),gender:env.api.state?.journey?.gender,name:''});
    actors.sort((a,b)=>a.pose.y-b.pose.y);
    for(const actor of actors)drawPlaceActor(ctx,kind,actor.state,actor.pose,time,art,{look:actor.look,gender:actor.gender,onReady:wake},{local:!!actor.local,name:actor.name,font:uiFont});
    // Screen-space hints remain readable when a portrait camera crops the route.
    ctx.setTransform(ratio,0,0,ratio,0,0);
    const target=s.phase==='return'?(kind==='boat'?world.entry:s.round?.entry):kind==='pool'?s.round?.checkpoints?.[s.next]:null;
    if(target){const p=placeWorldPoint(kind,{x:target[0],y:target[1]},true),x=(p.x-camera.x)*camera.scale,y=(p.y-camera.y)*camera.scale;
      if(x<28||x>viewport.width-28||y<90||y>viewport.height-100){const ax=clamp(x,30,viewport.width-30),ay=clamp(y,100,viewport.height-130),angle=Math.atan2(y-viewport.height/2,x-viewport.width/2);ctx.save();ctx.translate(ax,ay);ctx.rotate(angle);ctx.fillStyle='#fff0b8';ctx.strokeStyle='#647b58';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(10,0);ctx.lineTo(-7,-7);ctx.lineTo(-4,0);ctx.lineTo(-7,7);ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();}}
    if(s.phase==='waiting'||s.phase==='bite'){
      const width=Math.min(250,viewport.width*.62),left=(viewport.width-width)/2,top=viewport.height*.20,wait=(s.round.bite_at-s.round.now)/(s.round.bite_at-s.round.now+s.round.bite_window);
      ctx.fillStyle='#4c665fe6';ctx.beginPath();ctx.roundRect(left,top,width,16,8);ctx.fill();ctx.fillStyle='#d7e6aa';ctx.beginPath();ctx.roundRect(left+3+wait*(width-6),top+3,(1-wait)*(width-6),10,5);ctx.fill();ctx.fillStyle='#fff4d4';ctx.beginPath();ctx.roundRect(left+3+s.progress*(width-6),top+2,3,12,1.5);ctx.fill();
    }
  }
  function stopMotion(){play.reset();control.reset();leisurePresence.publish(play.state);}
  loop=createPlaceLifecycle({step:play.step,render,reset:()=>{control.reset();play.reset();},needsFrame:()=>play.needsFrame()||peers.needsFrame()||cameraSettling});
  function availability(){if(destroyed)return;const available=dialog.open&&!document.hidden&&focused;
    if(available){control.enable(true);cameraAt=peerFrameAt=0;loop.resume();}else{stopMotion();loop.suspend();control.enable(false);}}
  const handled=fn=>e=>{if(fn(e)){e.preventDefault();e.stopPropagation();}};
  listen(stick,'pointerdown',handled(e=>control.pointerDown(e,stick.getBoundingClientRect())));listen(stick,'pointermove',handled(control.pointerMove));
  for(const type of ['pointerup','pointercancel','lostpointercapture'])listen(stick,type,handled(control.pointerUp));
  listen(dialog,'keydown',e=>{
    // Focused buttons own Space and emit their own click on keyup (including leave and close).
    if(e.key===' '&&e.target?.closest?.('button'))return;
    if(e.key===' '&&!e.repeat){e.preventDefault();e.stopPropagation();void play.interact();return;}
    if(control.keyDown(e)){e.preventDefault();e.stopPropagation();}
  });
  listen(dialog,'keyup',handled(control.keyUp));listen(stick,'blur',()=>{stopMotion();wake();});
  listen(button,'click',()=>void play.interact());listen(leaveButton,'click',()=>void play.leave());listen(dialog.querySelector('[data-close]'),'click',()=>dialog.close());
  listen(window,'blur',()=>{focused=false;availability();});listen(window,'focus',()=>{focused=true;availability();});listen(document,'visibilitychange',availability);
  listen(window,'resize',resize);listen(window,'orientationchange',resize);listen(canvas,'contextrestored',resize);
  const api={dialog,play,destroy(){if(destroyed)return;stopMotion();loop.destroy();destroyed=true;unsubscribe();leisurePresence.clear();control.destroy();play.destroy();listeners.forEach(off=>off());dialog.remove();if(active===api)active=null;if(opener?.isConnected)opener.focus();env.renderMain?.();}};
  listen(dialog,'close',api.destroy);active=api;dialog.showModal();resize();sync();availability();canvas.focus();return api;
}
