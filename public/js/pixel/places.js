/** Shared outdoor scenery, private leisure rounds. Simulation coordinates stay 320x200. */
import {getCharacterStamp} from '../isometric/character-art.js';
import {createMovementController} from '../isometric-movement.js';
import {leisurePresence} from '../isometric/leisure-presence.js';
import {createLeisureActors} from '../isometric/leisure-actors.js';
import {lookOf} from '../v4/look.js';

const KINDS=['fishing','boat','pool'],DOCK={x:84,y:154},TITLES={fishing:'Bờ hồ câu cá',boat:'Bến chèo thuyền',pool:'Hồ bơi khu phố'};
const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
export function walkablePlace(kind,x,y,inWater=false){
  if(!Number.isFinite(x)||!Number.isFinite(y)||x<12||x>308||y<20||y>190)return false;
  if(inWater)return kind==='pool'?x>=64&&x<=260&&y>=58&&y<=148:x>=48&&x<=282&&y>=42&&y<=158;
  return y>=166||x>=74&&x<=94&&y>=145;
}

/** Small deterministic simulation, independent of DOM and rendering. */
export function createPixelPlay(kind,{command,now=()=>Date.now(),onChange=()=>{}}){
  if(!KINDS.includes(kind))throw new Error('Hoạt động không hợp lệ.');
  const state={kind,x:84,y:180,direction:'ne',heading:-Math.PI/4,phase:'walk',busy:false,round:null,next:0,progress:0,moving:false,action:null,message:'Đi tới đầu cầu gỗ bằng cần tròn hoặc phím mũi tên / W A S D.',stats:null};
  let alive=true,input={x:0,y:0},offset=0,retryAt=0;
  const emit=()=>{if(alive)onChange(state);};
  const animate=(kind,duration,from=[state.x,state.y],to=from)=>{state.action={kind,at:now(),duration,from:[...from],to:[...to]};};
  function setInput(x,y){if(!alive)return;const n=Math.hypot(x,y);input=Number.isFinite(n)?{x:x/Math.max(1,n),y:y/Math.max(1,n)}:{x:0,y:0};}
  async function send(action,payload,success){
    if(!alive||state.busy)return;state.busy=true;emit();
    try{const result=await command(action,payload);if(!alive)return;success(result||{});}
    catch(error){if(!alive)return;state.action=null;state.message=error?.message||'Mất kết nối. Thử lại để lưu cùng vòng chơi này.';
      retryAt=now()+1500;if(['missed','expired','bad_round'].includes(error?.data?.code)){
        if(kind!=='fishing'&&['boat','pool','return'].includes(state.phase)){
          // Keep the physical way out, without retaining expired checkpoint/finish proof.
          const entry=state.round?.entry||(kind==='boat'?[104,150]:[86,142]);state.phase='return';state.round={entry:[entry[0],entry[1]]};
          state.message=`Vòng đã kết thúc, quay về ${kind==='boat'?'bến':'thang'} để lên bờ.`;
        }else{state.phase='walk';state.round=null;}
      }}
    finally{if(alive){state.busy=false;emit();}}
  }
  function step(dt){
    if(!alive)return;
    if(state.action&&now()-state.action.at>=state.action.duration){state.action=null;emit();}
    const moving=['walk','boat','pool','return'].includes(state.phase)&&!state.busy&&!state.action;
    state.moving=Boolean(moving&&(input.x||input.y));
    if(moving&&(input.x||input.y)){
      const water=state.phase!=='walk',speed=water?(kind==='boat'?72:56):42,delta=Math.max(0,Math.min(.05,Number(dt)||0))*speed;
      const x=state.x+input.x*delta,y=state.y+input.y*delta;
      if(walkablePlace(kind,x,state.y,water))state.x=x;
      if(walkablePlace(kind,state.x,y,water))state.y=y;
      state.direction=input.y<0?(input.x<0?'nw':'ne'):(input.x<0?'sw':'se');
      state.heading=Math.atan2(input.y,input.x);
    }
    if(state.phase==='waiting'||state.phase==='bite'){
      const t=now()/1000+offset,r=state.round;
      state.progress=Math.max(0,Math.min(1,(t-r.now)/(r.bite_at-r.now+r.bite_window)));
      if(t>r.bite_at+r.bite_window){state.phase='walk';state.round=null;state.message='Cá nhả mồi rồi. Bấm thả cần để thử lại.';emit();}
      else if(t>=r.bite_at&&state.phase!=='bite'){state.phase='bite';state.message='Cá cắn câu! Bấm Giật cần hoặc phím Space ngay!';emit();}
    }
    if((state.phase==='boat'||state.phase==='pool')&&!state.busy&&!state.action&&state.round&&now()>=retryAt){
      const target=state.round.checkpoints[state.next];
      if(target&&distance(state,{x:target[0],y:target[1]})<=8){
        const index=state.next;
        void send('jr_leisure_checkpoint',{round:state.round.id,index,x:Math.round(state.x*100)/100,y:Math.round(state.y*100)/100},result=>{
          state.next=Number.isInteger(result.next)?result.next:index+1;
          state.message=state.next<state.round.checkpoints.length?`Qua mốc ${state.next}/${state.round.checkpoints.length}. Đi đến vòng đang sáng.`:'Đã quay về bến. Bấm Lưu vòng để lưu thành tích.';
        });
      }
    }
  }
  async function interact(){
    if(!alive||state.busy||state.action)return;
    if(state.phase==='walk'){
      if(distance(state,DOCK)>18){state.message='Đi đến đầu cầu gỗ đang sáng trước nhé.';emit();return;}
      const from=[state.x,state.y];if(kind==='fishing')animate('cast',700);emit();
      await send('jr_leisure_start',{kind},result=>{
        const r=result.leisure_round;if(!r?.id)throw new Error('Chưa nhận được vòng chơi. Thử lại nhé.');
        state.round=r;state.next=r.next||0;state.stats=result.leisure||state.stats;offset=r.now-now()/1000;setInput(0,0);
        if(kind==='fishing'){animate('cast',700);state.phase='waiting';state.message='Đã thả mồi. Chờ phao rung rồi bấm Giật cần trong vạch sáng.';}
        else{state.phase=kind;state.x=r.entry[0];state.y=r.entry[1];animate('board',700,from,r.entry);state.message=kind==='boat'?'Đã lên thuyền. Chèo qua từng vòng mốc rồi về bến.':'Đã xuống hồ. Bơi qua bốn mốc theo thứ tự rồi về thang.';}
      });
    }else if(state.phase==='bite'||((state.phase==='boat'||state.phase==='pool')&&state.next===state.round.checkpoints.length)){
      if(kind==='fishing'){animate('reel',750);emit();}
      await send('jr_leisure_finish',{round:state.round.id},result=>{
        state.stats=result.leisure||state.stats;state.message=result.message||'Đã lưu thành tích.';
        state.phase=kind==='fishing'?'walk':'return';if(kind==='fishing')animate('caught',1900);setInput(0,0);
      });
    }else if(state.phase==='return'){
      const entry={x:state.round.entry[0],y:state.round.entry[1]};
      if(distance(state,entry)>20){state.message='Quay về đầu cầu / thang hồ trước khi lên bờ.';emit();return;}
      const from=[state.x,state.y];state.phase='walk';state.x=84;state.y=174;animate('exit',700,from,[state.x,state.y]);state.round=null;state.message='Đã lên bờ. Có thể chơi thêm hoặc trở về khu phố.';setInput(0,0);emit();
    }
  }
  function needsFrame(){
    if(!alive)return false;if(state.action||state.phase==='waiting'||state.phase==='bite')return true;
    if(state.busy)return false;if(input.x||input.y)return true;
    const target=state.round?.checkpoints?.[state.next];return ['boat','pool'].includes(state.phase)&&!!target&&distance(state,{x:target[0],y:target[1]})<=8;
  }
  function reset(){const changed=state.moving||input.x||input.y;setInput(0,0);state.moving=false;if(changed)emit();}
  return {state,input:setInput,step,interact,needsFrame,reset,destroy(){input={x:0,y:0};state.moving=false;alive=false;}};
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
/** Cover the viewport without stretching. Coordinates stay in the private 320x200 world. */
export function placeCamera(width,height,actor={x:160,y:100}){
  width=Math.max(1,width);height=Math.max(1,height);const scale=Math.max(width/320,height/200),viewWidth=width/scale,viewHeight=height/scale;
  return {scale,width,height,viewWidth,viewHeight,x:clamp(actor.x-viewWidth/2,0,320-viewWidth),y:clamp(actor.y-viewHeight*.65,0,200-viewHeight)};
}
export function placePoint(camera,x,y){return {x:camera.x+x/camera.scale,y:camera.y+y/camera.scale};}

export function leisurePose(state,time=0,wallTime=Date.now()){
  const step=state.moving?Math.floor(time/180)%4:0;
  const action=state.action,progress=action?clamp((wallTime-action.at)/action.duration,0,1):0,ease=progress*progress*(3-2*progress);
  const travel=action&&['board','exit'].includes(action.kind),x=travel?action.from[0]+(action.to[0]-action.from[0])*ease:state.x,y=travel?action.from[1]+(action.to[1]-action.from[1])*ease-Math.sin(progress*Math.PI)*3:state.y;
  return {walkFrame:step===1?1:step===3?2:0,step,
    heading:Number.isFinite(state.heading)?state.heading:({se:Math.PI/4,sw:Math.PI*3/4,nw:-Math.PI*3/4,ne:-Math.PI/4}[state.direction]??Math.PI/4),
    water:['boat','pool','return'].includes(state.phase),bob:Math.sin(time/350)*.65,x,y,action:action?.kind||null,progress,
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

function drawBoat(ctx,boat,x,y,heading,time,moving){
  ripple(ctx,x,y+7,22,.24);if(moving)ripple(ctx,x-Math.cos(heading)*15,y-Math.sin(heading)*15,14+Math.sin(time/230)*2,.3);
  const h=46,w=h*(boat?.naturalWidth||240)/(boat?.naturalHeight||560);ctx.save();ctx.translate(x,y);ctx.rotate(heading+Math.PI/2);
  if(boat)ctx.drawImage(boat,-w/2,-h/2,w,h);
  if(moving){const sweep=Math.sin(time/180)*7;ctx.strokeStyle='#ad8252';ctx.lineWidth=1.8;ctx.lineCap='round';
    ctx.beginPath();ctx.moveTo(-7,0);ctx.lineTo(-21,-5+sweep);ctx.moveTo(7,0);ctx.lineTo(21,5-sweep);ctx.stroke();
    ripple(ctx,-21,-5+sweep,4,.7);ripple(ctx,21,5-sweep,4,.7);}
  ctx.restore();
}

function drawSwim(ctx,stamp,pose,time,moving){
  const {x,y,bob}=pose,stroke=moving?Math.sin(time/170):0;
  // Underwater legs and alternating arms give the stroke a visible rhythm.
  ctx.save();ctx.lineCap='round';ctx.lineWidth=2.3;ctx.strokeStyle='#f4cda180';ctx.beginPath();
  ctx.moveTo(x-3,y+2);ctx.quadraticCurveTo(x-5-stroke*2,y+7,x-3-stroke*3,y+12);ctx.moveTo(x+3,y+2);ctx.quadraticCurveTo(x+5+stroke*2,y+7,x+3+stroke*3,y+12);ctx.stroke();ctx.restore();
  ctx.drawImage(stamp,0,0,stamp.width,stamp.height*.72,x-11,y-22+bob,22,22);
  ctx.lineCap='round';ctx.lineWidth=2.4;ctx.strokeStyle='#f5d1ad';ctx.beginPath();ctx.moveTo(x-5,y-7);ctx.quadraticCurveTo(x-9,y-7-stroke*4,x-12,y-1-stroke*5);ctx.moveTo(x+5,y-7);ctx.quadraticCurveTo(x+9,y-7+stroke*4,x+12,y-1+stroke*5);ctx.stroke();
  ripple(ctx,x,y+2,12+Math.sin(time/220)*.8,.66);ripple(ctx,x,y+4,7,.42);
  if(moving){ripple(ctx,x-Math.cos(pose.heading)*8,y+7,17,.35);ripple(ctx,x-12,y-1-stroke*5,3,.75);ripple(ctx,x+12,y-1+stroke*5,3,.75);}
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
  const options={...appearance,direction:s.direction,step:pose.step,walkFrame:pose.walkFrame};
  const fishing=kind==='fishing'&&!s.moving,char=(fishing?art.fishingCharacter?.({...options,pose:pose.fishingPose}):null)||art.character?.(options)||getCharacterStamp(options),stamp=char.canvas||char;
  if(kind==='boat'&&(local||pose.water)){
    const moored=!pose.water||pose.action==='board',boatX=moored?104:pose.x,boatY=moored?150:pose.y+pose.bob;
    drawBoat(ctx,art.asset?.('boat'),boatX,boatY,moored?-Math.PI/2:pose.heading,time,!moored&&s.moving);
  }
  const entering=pose.action==='board'&&pose.progress<.6;
  if(pose.water&&kind==='boat'&&!entering)ctx.drawImage(stamp,0,0,stamp.width,stamp.height*.81,pose.x-10,pose.y-23+pose.bob,20,22);
  else if(pose.water&&kind==='pool'&&!entering)drawSwim(ctx,stamp,pose,time,s.moving);
  else{ctx.save();ctx.translate(pose.x,pose.y);if(pose.action==='cast')ctx.rotate(Math.sin(pose.progress*Math.PI)*-.12);if(pose.action==='reel')ctx.rotate(Math.sin(pose.progress*Math.PI)*-.18);if(pose.action==='caught'&&pose.progress<.18)ctx.rotate(Math.sin(pose.progress/.18*Math.PI)*-.18);ctx.drawImage(stamp,-12,-32,24,32);ctx.restore();}
  if(fishing)drawFishing(ctx,s,pose,time,art,char.hand);
  if(name){ctx.save();ctx.font=`6px ${font}`;ctx.textAlign='center';ctx.textBaseline='bottom';const width=Math.min(78,ctx.measureText(name).width+7);ctx.fillStyle='#fff6dce8';ctx.fillRect(pose.x-width/2,pose.y-42,width,9);ctx.fillStyle='#604b37';ctx.fillText(name,pose.x,pose.y-34,72);ctx.restore();}
}

let active=null;
/** App routing entry point; supports free play with no current career. */
export function openPixelPlace(kind,env){
  kind=({fish:'fishing',pond:'fishing',swim:'pool',boating:'boat'})[kind]||kind;
  if(!KINDS.includes(kind))return false;active?.destroy();
  const art=env.leisureArt||{},bg=scenery(kind,art),opener=document.activeElement,dialog=document.createElement('dialog');dialog.className='leisure-place pixel-place place-scene';dialog.dataset.place=kind;
  dialog.setAttribute('aria-label',TITLES[kind]);dialog.setAttribute('aria-modal','true');
  dialog.innerHTML=`<canvas width="960" height="600" tabindex="0" aria-label="${TITLES[kind]}: di chuyển rồi tương tác"></canvas><header class="place-heading"><button type="button" data-close aria-label="Trở về khu phố">←</button><h2>${TITLES[kind]}</h2></header><p class="place-help">Di chuyển: cần tròn · ↑ ↓ ← → / W A S D · Tương tác: Space</p><p data-record class="place-record"></p><p data-status class="place-status" role="status" aria-live="polite"></p><div class="place-controls"><div data-stick tabindex="0" role="group" aria-label="Kéo cần tròn để di chuyển"><span data-knob aria-hidden="true"></span></div><button type="button" data-play></button></div>`;
  document.body.append(dialog);
  const uiFont=getComputedStyle(dialog).fontFamily||'system-ui';
  const canvas=dialog.querySelector('canvas'),ctx=canvas.getContext('2d'),status=dialog.querySelector('[data-status]'),button=dialog.querySelector('[data-play]'),record=dialog.querySelector('[data-record]'),stick=dialog.querySelector('[data-stick]'),knob=dialog.querySelector('[data-knob]');
  canvas.style.imageRendering=art.pixelated===false?'auto':'pixelated';
  const listeners=[],peers=createLeisureActors(kind);let destroyed=false,focused=true,statusText='',camera=placeCamera(960,600),viewport={width:960,height:600},cameraAt=0,peerFrameAt=0,loop=null,cameraSettling=false;
  function wake(){if(!destroyed)loop?.wake();}
  const unsubscribe=leisurePresence.subscribe(kind,people=>{const changed=peers.receive(people);dialog.dataset.peers=String(people.length);if(changed)wake();});
  function listen(target,type,fn,options){target.addEventListener(type,fn,options);listeners.push(()=>target.removeEventListener(type,fn,options));}
  function sync(){
    if(destroyed||!dialog.open)return;const s=play.state;
    if(statusText!==s.message){statusText=s.message;status.textContent=s.message;}
    const labels={walk:kind==='fishing'?'Thả cần':kind==='boat'?'Lên thuyền':'Xuống hồ',waiting:'Chờ cá…',bite:'Giật cần!',boat:'Lưu vòng chèo',pool:'Lưu vòng bơi',return:'Lên bờ'};
    button.textContent=s.action?.kind==='caught'?'Bắt được cá!':s.busy?'Đang xác nhận…':labels[s.phase];button.disabled=s.busy||!!s.action||s.phase==='waiting'||(['boat','pool'].includes(s.phase)&&s.next<(s.round?.checkpoints?.length||0));
    const stats=s.stats||env.api.state?.journey?.leisure||{};
    record.textContent=`${Object.values(stats.fish||{}).reduce((n,v)=>n+(Number(v)||0),0)} cá · ${stats.boat_laps||0} vòng chèo · ${stats.swim_laps||0} vòng bơi`;
  }
  const play=createPixelPlay(kind,{command:(action,payload)=>env.api.command(action,payload,null),onChange:()=>{sync();wake();}});
  if(art.notice)play.state.message+=` ${art.notice}`;
  const control=createMovementController({onInput:(x,y)=>{play.input(x,y);if(!x&&!y){play.reset();leisurePresence.publish(play.state);}wake();},onVisual:({x,y})=>{knob.style.transform=`translate(-50%,-50%) translate(${x*30}px,${y*30}px)`;},capturePointer:id=>stick.setPointerCapture(id),releasePointer:id=>stick.releasePointerCapture(id)});
  function resize(){
    if(destroyed)return;const box=canvas.getBoundingClientRect();viewport={width:Math.max(1,box.width||window.innerWidth),height:Math.max(1,box.height||window.innerHeight)};
    const ratio=Math.min(2,Math.max(1.5,window.devicePixelRatio||1),Math.sqrt(2600000/(viewport.width*viewport.height)),4096/Math.max(viewport.width,viewport.height));
    canvas.width=Math.round(viewport.width*ratio);canvas.height=Math.round(viewport.height*ratio);
    camera=placeCamera(viewport.width,viewport.height,play.state);cameraAt=0;cameraSettling=false;wake();
  }
  function render(){
    if(destroyed||!dialog.open)return;const s=play.state,time=performance.now(),pose=leisurePose(s,time);
    leisurePresence.publish(s);
    const nextCamera=placeCamera(viewport.width,viewport.height,{x:pose.x+(kind==='fishing'&&s.phase!=='walk'?12:0),y:pose.y}),blend=cameraAt?1-Math.exp(-(time-cameraAt)/120):1;
    camera={...nextCamera,x:camera.x+(nextCamera.x-camera.x)*blend,y:camera.y+(nextCamera.y-camera.y)*blend};cameraAt=time;
    cameraSettling=Math.abs(nextCamera.x-camera.x)+Math.abs(nextCamera.y-camera.y)>.025;
    if(!cameraSettling){camera.x=nextCamera.x;camera.y=nextCamera.y;}
    const ratio=canvas.width/viewport.width,scale=camera.scale*ratio;
    ctx.setTransform(scale,0,0,scale,-camera.x*scale,-camera.y*scale);ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(bg,0,0,320,200);
    for(const [x,y] of [[146,90],[215,110],[123,138]])ripple(ctx,x,y,5+Math.sin(time/900+x)*1.5,.11);
    if(s.round?.checkpoints)s.round.checkpoints.forEach(([x,y],i)=>checkpoint(ctx,x,y,i,i===s.next,i<s.next,time,uiFont));
    const actors=peers.sample(peerFrameAt?(time-peerFrameAt)/1000:0).map(peer=>({...peer,pose:leisurePose(peer.state,time)}));peerFrameAt=time;
    actors.push({local:true,state:s,pose,look:lookOf(env.api.state),gender:env.api.state?.journey?.gender,name:''});
    actors.sort((a,b)=>a.pose.y-b.pose.y);
    for(const actor of actors)drawPlaceActor(ctx,kind,actor.state,actor.pose,time,art,{look:actor.look,gender:actor.gender,onReady:wake},{local:!!actor.local,name:actor.name,font:uiFont});
    // Screen-space hints remain readable when a portrait camera crops the route.
    ctx.setTransform(ratio,0,0,ratio,0,0);
    const target=s.round?.checkpoints?.[s.next];
    if(target){const x=(target[0]-camera.x)*camera.scale,y=(target[1]-camera.y)*camera.scale;
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
  listen(dialog,'keydown',e=>{if(e.key===' '&&!e.repeat){e.preventDefault();e.stopPropagation();void play.interact();return;}if(control.keyDown(e)){e.preventDefault();e.stopPropagation();}});
  listen(dialog,'keyup',handled(control.keyUp));listen(stick,'blur',()=>{stopMotion();wake();});
  listen(button,'click',()=>void play.interact());listen(dialog.querySelector('[data-close]'),'click',()=>dialog.close());
  listen(window,'blur',()=>{focused=false;availability();});listen(window,'focus',()=>{focused=true;availability();});listen(document,'visibilitychange',availability);
  listen(window,'resize',resize);listen(window,'orientationchange',resize);
  const api={dialog,play,destroy(){if(destroyed)return;stopMotion();loop.destroy();destroyed=true;unsubscribe();leisurePresence.clear();control.destroy();play.destroy();listeners.forEach(off=>off());dialog.remove();if(active===api)active=null;if(opener?.isConnected)opener.focus();env.renderMain?.();}};
  listen(dialog,'close',api.destroy);active=api;dialog.showModal();resize();sync();availability();canvas.focus();return api;
}
