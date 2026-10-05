/** Native fullscreen with an in-page fallback for embedded/mobile browsers. */
export function stageFullscreen(stage,button,{doc=document,reset,resize,text}){
 let active=false,native=false,host=null;
 function update(on){
   active=on;reset();
   stage.classList.toggle('dd-expanded',on);
   if(on)host=stage.closest('dialog');
   host?.classList.toggle('dd-expanded-host',on);
   button.textContent=on?'↙ '+text('Thu nhỏ'):'⛶ '+text('Toàn màn hình');
   button.setAttribute('aria-pressed',String(on));resize();
 }
 async function exit(){
   update(false);native=false;
   if(doc.fullscreenElement===stage){try{await doc.exitFullscreen();}catch{/* layout already restored */}}
 }
 async function toggle(){
   if(active)return exit();
   update(true);
   if(!stage.requestFullscreen)return;
   try{
     await stage.requestFullscreen();
     if(!active||!stage.isConnected){await exit();return;}
     native=doc.fullscreenElement===stage;resize();
   }catch{/* Expanded in-page layout remains available when fullscreen is denied. */}
 }
 doc.addEventListener('fullscreenchange',()=>{
   if(doc.fullscreenElement===stage){native=true;resize();}
   else if(native){native=false;update(false);if(stage.isConnected)button.focus({preventScroll:true});}
 });
 return {get active(){return active;},toggle,exit};
}
