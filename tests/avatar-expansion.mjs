import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {ART,defaultLook,lookOf,figureSVG,portrait,figureOf,paintAcc,SVG,cozyPortraits,accBust,accPaint} from '../public/js/v4/look.js';
import {autoFace,faceCode,parseFace,DEFAULT_FACE} from '../public/js/v4/face-code.js';
import {faceSVG} from '../public/js/v4/face.js';
import {avatarView,avatarAction} from '../public/js/v4/avatar.js';
import {paintWardrobeOverlay,characterKey} from '../public/js/isometric/character-art.js';

if(process.argv.includes('--snapshots')){
  const rows=JSON.parse(readFileSync(0,'utf8')),codes=[];
  for(const {state,look,face} of rows){
    const pair=[];
    for(const mode of [false,true]){
      cozyPortraits(mode);
      const reopened=JSON.parse(JSON.stringify(state));
      assert.deepEqual(lookOf(reopened),look);
      const code=faceCode(reopened),peer=parseFace(code);
      assert.deepEqual(peer.f,face);assert.equal(peer.acc,look.acc);assert.equal(peer.accTint,'mint');
      assert.ok(faceSVG(code).includes('<svg'));assert.ok(portrait(look,'female').includes('<svg'));
      pair.push(code);
    }
    codes.push(pair);
  }
  console.log(JSON.stringify(codes));process.exit(0);
}

const accessories=['mu_beret','mu_cao_boi','tai_nghe','vuong_mien','bang_do_tai_meo','vong_hoa','khau_trang','khan_choang'];
const base=defaultLook('female');
function recorder(){
 const calls=[],target={createLinearGradient(){return {addColorStop(){}};}};
 const ctx=new Proxy(target,{get:(object,key)=>key in object?object[key]:(...args)=>calls.push([key,...args]),set(object,key,value){calls.push(['set',key,value]);object[key]=value;return true;}});
 return {ctx,calls};
}

test('eight accessories have distinct silhouettes in classic, portrait and all four illustrated facings',()=>{
 const frontShapes=new Set(),bustShapes=new Set();
 for(const acc of accessories){
  assert.ok(ART.acc[acc],`${acc} is available to every renderer`);
  const look={...base,acc,tint:{[acc]:'mint'}},out=[];paintAcc(out,figureOf(look,'female'),SVG);
  assert.ok(out.length>0);frontShapes.add(out.join(''));
  const bust=accBust(acc,accPaint(look));assert.ok(bust);bustShapes.add(bust);
  assert.ok(figureSVG(look,'female').includes('#8fd5c0'));assert.ok(portrait(look,'female').includes('#8fd5c0'));
  const facings=[];
  for(const direction of ['se','sw','nw','ne']){
   const {ctx,calls}=recorder();paintWardrobeOverlay(ctx,{gender:'female',direction,look},{x:10,y:8,w:100,h:148});
   assert.ok(calls.some(call=>call[0]==='fill'||call[0]==='stroke'),`${acc} has a visible ${direction} silhouette`);
   assert.ok(calls.some(call=>call.includes('#8fd5c0')),`${acc} keeps its saved tint in ${direction}`);
   facings.push(characterKey({look,direction}));
  }
  assert.equal(new Set(facings).size,4);
 }
 assert.equal(frontShapes.size,8,'the new items are different shapes, not recolours');assert.equal(bustShapes.size,8);
});

test('rear face mask exposes straps instead of drawing a mask across the back of the head',()=>{
 const outputs=['se','nw'].map(direction=>{const {ctx,calls}=recorder();paintWardrobeOverlay(ctx,{direction,look:{acc:'khau_trang'}},{x:10,y:8,w:100,h:148});return calls;});
 const maskPanel=calls=>calls.some(([method,x,y])=>method==='moveTo'&&x===-23&&y===-75);
 assert.equal(maskPanel(outputs[0]),true,'front view covers the mouth');
 assert.equal(maskPanel(outputs[1]),false,'rear view draws only the ear straps');
 assert.ok(outputs[1].some(([method])=>method==='stroke'),'rear straps remain visible');
});

test('all newer wardrobe hairstyles reach the public avatar without falling back to short hair',()=>{
 const mapped={toc_song_dai:'song',toc_bob_mai:'mai',toc_duoi_cao:'duoi',toc_bui_tron:'bui_doi',toc_wolf:'dung',toc_undercut:'lech',toc_mai_bay:'bob',toc_tet:'tet'};
 for(const [hair,expected] of Object.entries(mapped)){
  const state={journey:{gender:'female'},wardrobe:{look:base},wardrobe_plus:{look:{hair:[hair,base.hair]}}};
  assert.equal(autoFace(state).hair,expected,hair);assert.equal(parseFace(faceCode(state)).f.hair,expected);
 }
});

test('server-provided preset selection is local until Save and restores from the common saved state',async()=>{
 const preset={id:'am_nhac',name:'Bạn yêu âm nhạc',face:{...DEFAULT_FACE,hair:'afro',extra:'tai_nghe'}},calls=[];
 const state={journey:{gender:'female'},wardrobe:{look:base}},api={state,content:{journey:{wardrobe:{avatar_presets:[preset]}}}},ui={};
 const env={api,ui,renderSheet(){},async cmd(action,payload){calls.push({action,payload});api.state={...api.state,avatar:{v:1,...JSON.parse(JSON.stringify(payload))}};return true;}};
 assert.ok(avatarView(env).includes('data-action="jrAvPreset"'),'the shared builder offers server presets');
 assert.equal(await avatarAction('jrAvPreset',{preset:preset.id},null,env),true);
 assert.deepEqual(ui.av.face,preset.face);assert.equal(calls.length,0);
 await avatarAction('jrAvSave',{},null,env);assert.equal(calls.length,1);assert.equal(calls[0].action,'jr_avatar');
 assert.deepEqual(api.state.avatar.face,preset.face);
 const reopened={...env,ui:{},api:{...api,state:JSON.parse(JSON.stringify(api.state))}};avatarView(reopened);
 assert.deepEqual(reopened.ui.av.face,preset.face);assert.equal(faceCode(reopened.api.state),faceCode(api.state));
});
