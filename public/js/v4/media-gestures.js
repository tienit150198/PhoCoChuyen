/** Keep browser image menus and dragging from interrupting the game canvas.
 * This does not affect normal clicks, editable text or deliberate copy buttons. */
export function suppressMediaGesture(event){
 if(!['contextmenu','dragstart','dblclick'].includes(event.type))return;
 const target=event.target;
 if(!target?.closest?.('canvas,img'))return;
 if(target.closest('input,textarea,[contenteditable="true"],[contenteditable=""]'))return;
 if(event.type==='dragstart'&&target.closest('[data-drag-card]'))return;
 event.preventDefault();
}
