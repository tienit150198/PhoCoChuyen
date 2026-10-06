// F#218 "mua 12 đồ mà vẫn chỉ hiện 4 đồ": the clothes-shop rail draws the rack the shop really has (data.grid).
import assert from 'node:assert/strict';
import boutique,{rack} from '../public/js/scenes/boutique.js';
const ctx=()=>{const calls=[];const grad={addColorStop(){}};
  return {calls,ctx:new Proxy({},{get(t,k){if(k in t)return t[k];if(k==='measureText')return s=>({width:String(s).length*6});
    if(k==='createRadialGradient'||k==='createLinearGradient')return ()=>grad;
    return (...a)=>{calls.push([k,a]);};},set(t,k,v){t[k]=v;return true;}})};};
const hangers=(grid,portrait=false)=>{const {calls,ctx:c}=ctx();
  const w={ctx:c,c:{data:{grid,look:0},open:true,ops:{security:{items:[]}}},isPortrait:()=>portrait,words:()=>({open_sign:'MỞ',closed_sign:'ĐÓNG'}),game:{catalogue:[]},time:0,reduced:true};
  for(const [,fn] of boutique.props(w,{}))fn();
  return calls.filter(([k,a])=>k==='translate'&&a[1]===-150).length;};
const twelve={tee:{M:2},shirt:{M:1},jeans:{'29':3},dress:{M:1},aodai:{M:1},pajama:{M:1},kids:{'4':1},maxi:{M:1},blazer:{M:1},polo:{L:1},skirt:{M:1},shorts:{M:1},
  hat:{F:2},socks:{F:12},bag:{F:1}};
const r=rack({c:{data:{grid:twelve}}});
assert.equal(r.hang.length,12,'12 kinds on hangers');
assert.equal(r.low.length,3,'hat, socks and bag on the shelf');
assert.equal(r.total,30);
for(const portrait of [false,true]){
  assert.equal(hangers(twelve,portrait),12,'one hanger per kind, not a fixed 8');
  assert.equal(hangers({tee:{M:2},jeans:{'29':0}},portrait),1,'sold-out kinds are not drawn');
  assert.equal(hangers({tee:{M:0}},portrait),0,'an empty rack is bare');
  assert.equal(hangers({tee:{M:4}},portrait),2,'more pieces: a fuller hanger');
}
assert.equal(rack({c:{data:{}}}),null,'no grid: the old decorative rail');
assert.equal(hangers(undefined),8);
console.log('boutique rack checks passed');
