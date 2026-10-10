/** A career canvas only advances while its owning dialog is visible and on top. */
export function activityVisible(element){
  if(!element?.isConnected||document.hidden||element.hidden)return false;
  const dialog=element.closest('dialog[open]');if(!dialog)return false;
  const dialogs=document.querySelectorAll('dialog[open]');
  return dialogs[dialogs.length-1]===dialog&&element.getClientRects().length>0;
}

/** Dialog open/removal does not resize a canvas. Watch that lifecycle directly. */
export function watchActivityVisibility(element,changed){
  const relevant=node=>node===element||node?.nodeType===1&&(node.matches('dialog')||node.contains(element)||node.querySelector('dialog'));
  const observer=globalThis.MutationObserver?new MutationObserver(records=>{
    if(records.some(r=>r.type==='attributes'||[...r.addedNodes,...r.removedNodes].some(relevant)))changed();
  }):null;
  observer?.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['open']});
  document.addEventListener('visibilitychange',changed);
  return ()=>{observer?.disconnect();document.removeEventListener('visibilitychange',changed);};
}
