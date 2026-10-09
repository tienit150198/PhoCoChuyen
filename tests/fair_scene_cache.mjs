import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
const noop=()=>{};
const src=readFileSync(new URL('../public/js/scenes/fair-place.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace(/^export \{.*\};\r?\n/gm,'').replace(/export /g,'');
function fixture(){
 let text=0;const deps={R:noop,E:noop,L:noop,T:()=>text++,P:noop,fit:()=>12,sitter:noop,hash:()=>.5};
 const {props,marks,plan}=new Function(...Object.keys(deps),src+';return {props,marks,plan};')(...Object.values(deps));
 const c=new Proxy({measureText:()=>({width:50})},{get:(o,k)=>o[k]||noop,set:()=>true}),cache=new Map();
 const bitmap=(id,box,paint)=>{if(!cache.has(id)){paint(c);cache.set(id,box);}};
 return {props,marks,plan,c,cache,bitmap,text:()=>text};
}
test('static fair props and stall emoji reuse pixels while animated props retain their render callback',()=>{
 const f=fixture(),p=f.plan(true,{dt:true,loan:true,xs:true,pb:true,dg:true}),o={t:1,bitmap:f.bitmap};
 for(const [,draw] of f.props(f.c,p,o))draw();f.marks(f.c,p,o);
 const first=f.text();
 for(const [,draw] of f.props(f.c,p,{...o,t:2}))draw();f.marks(f.c,p,{...o,t:2});
 assert.equal(f.text(),first,'the repeated frame avoids all static signs and emoji text');
 
});
test('current game badges invalidate independently and near-stall marker remains hidden',()=>{
 const f=fixture(),p=f.plan(false,{dt:true,loan:true,xs:true,pb:true});
 f.marks(f.c,p,{bitmap:f.bitmap},'lt');assert.equal(f.cache.size,9);
 f.marks(f.c,p,{bitmap:f.bitmap,live:{lt:true}});assert.equal(f.cache.size,10);
 f.marks(f.c,p,{bitmap:f.bitmap,live:{lt:false}});assert.equal(f.cache.size,11,'live dot is part of the cached icon identity');
});


