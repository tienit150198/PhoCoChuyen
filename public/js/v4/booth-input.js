/** A room code is ASCII, but an IME owns the field until its composition finishes. */
export function bindRoomCode(box,join){
  if(box._pbCode)return;box._pbCode=true;
  let composing=false;
  const clean=()=>{const v=box.value.toUpperCase().replace(/[^A-Z0-9]/g,'').slice(0,4);if(v!==box.value)box.value=v;};
  box.addEventListener('compositionstart',()=>{composing=true;});
  box.addEventListener('compositionend',()=>{composing=false;clean();});
  box.addEventListener('input',e=>{if(!composing&&!e.isComposing)clean();});
  box.addEventListener('keydown',e=>{if(e.key==='Enter'&&!composing&&!e.isComposing&&e.keyCode!==229){e.preventDefault();join();}});
}
