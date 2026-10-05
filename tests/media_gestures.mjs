import assert from 'node:assert/strict';
import {suppressMediaGesture} from '../public/js/v4/media-gestures.js';
function event(type,{media=true,editable=false,card=false}={}){
 return {type,cancelled:false,preventDefault(){this.cancelled=true;},target:{closest(q){
   if(q==='canvas,img')return media?{}:null;
   if(q==='[data-drag-card]')return card?{}:null;
   return editable?{}:null;
 }}};
}
for(const type of ['contextmenu','dragstart','dblclick']){const e=event(type);suppressMediaGesture(e);assert(e.cancelled,type);}
for(const opts of [{media:false},{editable:true}]){const e=event('contextmenu',opts);suppressMediaGesture(e);assert(!e.cancelled);}
const card=event('dragstart',{card:true});suppressMediaGesture(card);assert(!card.cancelled,'game card dragging remains available');
const click=event('click');suppressMediaGesture(click);assert(!click.cancelled,'normal gameplay clicks remain available');
console.log('media gestures: accidental media menus/drags suppressed; gameplay and editing preserved');
