import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../public/js/v4/fair-booth.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace(/export /g,'');
const noop=()=>{};
test('booth preview reuses unchanged people and invalidates pose, expression, outfit, backdrop, size and fonts',()=>{
 const oldDoc=globalThis.document;let paints=0;const fonts=new Map();
 const ctx=new Proxy({measureText:()=>({width:20}),createLinearGradient:()=>({addColorStop:noop})},{get:(o,k)=>o[k]||noop,set:()=>true});
 const canvas=()=>({_pb:1,isConnected:true,width:520,height:324,getContext:()=>ctx});const cv=canvas();
 globalThis.document={documentElement:{lang:'vi'},createElement:canvas,fonts:{addEventListener:(k,v)=>fonts.set(k,v)}};
 try{
 const deps={live:{on:noop},lookOf:s=>s.look,PROPS:[],FAIR_FRAMES:[],FRAME:{},FRAMES:[],FAIR_BACKDROPS:[{id:'kem'},{id:'day_den'}],BACKDROPS:[],STICKERS:[],FAIR_STICKERS:[],tr:s=>s,CANVAS:{E:noop},paintShot:noop,paintPeople:()=>{paints++;return [{x:100}];}};
 const S={tab:'pb',env:{api:{state:{name:'Lan',look:{},journey:{}}}},dlg:{open:true,querySelector:q=>q==='.fh-pb-cv'?cv:null}};
 const ui=new Function(...Object.keys(deps),src+';return setup;')(...Object.values(deps))({S,F:()=>({photo:{}}),reduce:()=>false});
 ui.mount();ui.mount();assert.equal(paints,1,'unchanged preview avoids rerendering complete people');
 for(const [key,value] of [['pose','vay'],['face','cuoi'],['bg','kem']]){S.pb[key]=value;ui.mount();}
 assert.equal(paints,4);
 S.env.api.state.look={shirt:'new'};ui.mount();assert.equal(paints,5);
 cv.width=600;ui.mount();assert.equal(paints,6);
 fonts.get('loadingdone')();ui.mount();assert.equal(paints,7);
 S.pb.mode='friends';S.pb.step='room';S.pb.room={bg:'kem',people:[{pid:'a',name:'Lan',lk:{},pose:'dung'},{pid:'b',name:'Minh',lk:{},pose:'dung'}]};
 ui.mount();assert.equal(paints,8);
 S.pb.room.people[1].pose='vay';ui.mount();assert.equal(paints,9,'another player changing pose invalidates the preview');
 S.pb.room.people[1].lk={shirt:'new'};ui.mount();assert.equal(paints,10,'in-place multiplayer look updates cannot leave stale pixels');
 ui.mount();assert.equal(paints,10);
 }finally{globalThis.document=oldDoc;}
});
