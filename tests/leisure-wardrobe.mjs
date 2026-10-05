import assert from 'node:assert/strict';
import test from 'node:test';
import {paintWardrobeOverlay} from '../public/js/isometric/character-art.js';

function recorder(){
 const calls=[];const ctx=new Proxy({createLinearGradient(...args){calls.push(['gradient',...args]);return {addColorStop(){}};}},{get(target,key){return key in target?target[key]:(...args)=>calls.push([key,...args]);},set(target,key,value){target[key]=value;return true;}});
 return {ctx,calls};
}

test('real wardrobe painter keeps skirt shape and locates a fishing hat above the pose head',()=>{
 const {ctx,calls}=recorder(),box={x:10,y:8,w:100,h:148},alignment={bodyX:60,bodyY:120,faceX:54,eyesY:65};
 assert.equal(paintWardrobeOverlay(ctx,{gender:'female',direction:'se',look:{bottom:'vay_xoe',acc:'non_la'}},box,alignment),true);
 assert.ok(calls.some(([method,x,y])=>method==='moveTo'&&x===36&&Math.abs(y-111.12)<1e-8),'saved skirt paints a flared silhouette at the torso');
 assert.ok(calls.some(([method,x,y])=>method==='moveTo'&&x===-46&&y===-103),'saved non la is painted');
 assert.ok(calls.some(([method,x,y])=>method==='translate'&&x===57&&Math.abs(y-(65+78*148/145))<1e-8),'hat follows the leaning head, independent of torso');
});

test('saved shoulder bag follows the torso and invalid geometry paints nothing',()=>{
 const {ctx,calls}=recorder();
 paintWardrobeOverlay(ctx,{direction:'se',look:{acc:'tui_cheo'}},{x:10,y:8,w:100,h:148},{bodyX:77,faceX:48,eyesY:74});
 assert.ok(calls.some(([method,x,y])=>method==='translate'&&x===80&&y===156),'bag stays with the body while fishing head leans');
 assert.ok(calls.some(([method,x,y])=>method==='moveTo'&&x===-18&&y===-50),'bag strap remains visible');
 const count=calls.length;assert.equal(paintWardrobeOverlay(ctx,{}, {x:NaN,y:0,w:100,h:148}),false);assert.equal(calls.length,count);
});
