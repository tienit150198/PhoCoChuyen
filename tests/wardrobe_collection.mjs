import assert from 'node:assert/strict';
import {ART,defaultLook,figureOf,figureSVG,portrait,paintPlayer,SVG} from '../public/js/v4/look.js';
import {faceCode,parseFace} from '../public/js/v4/face-code.js';
import {faceSVG} from '../public/js/v4/face.js';
const base=defaultLook('female');
const hairstyles=['toc_bui_cao','toc_bui_doi','toc_bui_thap'];
const dresses=['dam_cong_chua','dam_du_tiec','dam_yem'];
for(const [slot,ids] of [['hair',hairstyles],['top',dresses]]){
  const full=[],bust=[],chat=[];
  for(const id of ids){
    assert.ok(ART[slot][id],id);
    const look={...base,[slot]:id,uniform:false};
    full.push(figureSVG(look,'female'));bust.push(portrait(look,'female'));
    const state={journey:{gender:'female'},wardrobe:{look}};
    const code=faceCode(state);assert.equal(parseFace(code).top,look.top);
    chat.push(faceSVG(code));
    const output=[];paintPlayer(output,figureOf(look,'female'),SVG);
    assert.ok(output.length>20);
    assert.ok(!full.at(-1).includes('undefined'));
    if(slot==='top'){
      // A dress hides the stored trousers/skirt and uses its own colour for the complete silhouette.
      assert.equal(figureSVG({...look,bottom:'quan_jean'},'female'),figureSVG({...look,bottom:'vay_dai'},'female'));
      const tinted={...look,tint:{[id]:'mint'}};
      const f=figureOf(tinted,'female');
      assert.equal(f.bottom.c,f.topC);assert.equal(f.topC,'#8fd5c0');
      assert.notEqual(figureSVG(tinted,'female'),full.at(-1));
    }else assert.notEqual(parseFace(code).f.hair,'ngan');
  }
  assert.equal(new Set(full).size,ids.length);
  assert.equal(new Set(bust).size,ids.length);
  assert.equal(new Set(chat).size,ids.length);
}
console.log('Wardrobe collection: distinct full-body, portrait/chat, dress layering and tint passed');
