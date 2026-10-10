/** Three.js is downloaded only while opening a home. A late load cannot revive a closed dialog. */
export function sceneSession(load=()=>import('./home-3d-scene.js')){
  let revision=0,scene=null,pending=null,target=null,latest=null,callbacks=null;
  function close(){revision++;pending=null;scene?.dispose();scene=null;target=null;}
  async function mount(element,data,actions={}){
    target=element;latest=data;callbacks=actions;
    if(scene){scene.attach(element);scene.update(data);return scene;}
    if(pending)return pending;
    const token=++revision;
    pending=(async()=>{
      const module=await load();if(token!==revision)return null;
      scene=module.createHomeScene(target,callbacks);scene.update(latest);return scene;
    })();
    try{return await pending;}catch(error){if(token!==revision)return null;throw error;}finally{if(token===revision)pending=null;}
  }
  return {mount,close,detach:()=>scene?.detach(),camera:action=>scene?.cameraAction(action),get current(){return scene;}};
}
