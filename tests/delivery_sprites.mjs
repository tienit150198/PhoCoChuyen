import assert from 'node:assert/strict';

const sprites=await import('../public/js/careers/delivery_sprites.js').catch(()=>({}));
for(const name of ['drawStreetPerson','drawStreetTree','drawStreetScooter'])assert.equal(typeof sprites[name],'function',`${name} exports a drawable sprite`);

// Record the real drawing calls and model Canvas state without needing a DOM.
function canvas(){
  const calls=[],stack=[],state={globalAlpha:.37,fillStyle:'original',strokeStyle:'original',lineWidth:3,lineCap:'butt',lineJoin:'miter'};
  const c=new Proxy(state,{
    get(o,key){
      if(key==='calls')return calls;
      if(key==='depth')return stack.length;
      if(key in o)return o[key];
      if(key==='save')return ()=>{stack.push({...o});calls.push(['save']);};
      if(key==='restore')return ()=>{assert.ok(stack.length,'restore has a matching save');Object.assign(o,stack.pop());calls.push(['restore']);};
      return (...args)=>{for(const a of args)if(typeof a==='number')assert.ok(Number.isFinite(a),`${key} must receive finite geometry`);if(key==='ellipse')assert.ok(args[2]>=0&&args[3]>=0);if(key==='arc')assert.ok(args[2]>=0);calls.push([key,...args,o.globalAlpha]);};
    },
    set(o,key,value){if(key==='globalAlpha')assert.ok(value>=0&&value<=.37,'sprite preserves caller fog opacity');o[key]=value;return true;}
  });
  return c;
}
const base={x:300,y:420,k:44,col:'#9a7162',helmet:'#c1bcaa',r:1.5,t:2.1};
for(const draw of Object.values(sprites))draw(canvas(),{...base,tint:color=>{assert.match(color,/^#[\da-f]{6}$/i,'renderer tint receives full hex colors');return color;}});
for(const draw of Object.values(sprites)){
  for(const k of [.2,4,22,90])for(const variant of [0,1,2,3,8]){
    const c=canvas();draw(c,{...base,k,variant,front:variant%2===0,tail:variant%2!==0,hat:variant%2===0,wave:variant%3===0});
    assert.equal(c.depth,0,'drawing balances Canvas save/restore');
    assert.equal(c.globalAlpha,.37);assert.equal(c.fillStyle,'original');assert.equal(c.strokeStyle,'original');assert.equal(c.lineWidth,3);
    assert.ok(c.calls.some(v=>v[0]==='fill'),'sprite paints visible geometry');
    assert.ok(c.calls.length<1000,'detail stays bounded at every distance');
    const repeat=canvas();draw(repeat,{...base,k,variant,front:variant%2===0,tail:variant%2!==0,hat:variant%2===0,wave:variant%3===0});
    assert.deepEqual(c.calls,repeat.calls,'the same scene does not shimmer between redraws');
  }
  for(const bad of [{k:0},{k:-1},{x:NaN},{y:Infinity},{k:NaN}]){const c=canvas();draw(c,{...base,...bad});assert.equal(c.calls.length,0,'invalid or empty projection is safely skipped');}
}
const pose=(t,calm)=>{const c=canvas();sprites.drawStreetPerson(c,{...base,t,calm,wave:true});return c.calls;};
assert.deepEqual(pose(0,true),pose(100,true),'reduced motion freezes walking and waving');
assert.notDeepEqual(pose(0,false),pose(.3,false),'normal motion articulates the person');
const view=facing=>{const c=canvas();sprites.drawStreetPerson(c,{...base,facing});return c.calls;};
assert.notDeepEqual(view(1),view(-1),'front and back person views have distinct silhouettes');
const tree=(detail,k)=>{const c=canvas();sprites.drawStreetTree(c,{...base,k,detail});return c.calls;};
assert.ok(tree(true,70).length>tree(false,70).length,'explicit low detail reduces tree work');
assert.ok(tree(true,70).length>tree(true,3).length,'distant foliage does less work');
console.log('delivery sprites: finite geometry, Canvas/fog isolation, deterministic bounded detail and reduced motion passed');
