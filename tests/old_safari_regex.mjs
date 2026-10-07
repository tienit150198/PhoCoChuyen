// iOS 15 / 16.0–16.3 hotfix (07/10): the two lookbehind regexes were rewritten without lookbehind. Same output as
// before on sample and random strings; the old-Safari check catches the syntax; boot.js polyfills behave.
// Run: node tests/old_safari_regex.mjs
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {splitNotes,toastParts} from '../public/js/toast-lines.js';
import {sentences} from '../public/js/v4/i18n.js';
import {checkSource,regexProblems,bootPolyfills} from '../scripts/check_old_safari.mjs';

// The regexes as they were in rel-1.9.13 (node parses lookbehind; Safari < 16.4 does not).
const OLD_TOAST=/(?<=[.!?…)\]”"»])\s+(?=\p{Extended_Pictographic})/u;
const OLD_I18N=/(?<=[.!?…:])\s+/u;
const PICT=/\p{Extended_Pictographic}/u,LEAD=/^((?:\p{Extended_Pictographic}|\p{Emoji_Modifier}|️|‍|⃣)+)\s*/u;
function oldToastParts(message){   // toastParts of rel-1.9.13, verbatim but for the regex
  const parts=String(message??'').split(OLD_TOAST).map(s=>s.trim()).filter(Boolean);
  if(parts.length<2||!parts.slice(1).every(p=>PICT.test(p.slice(0,2))))return [];
  const rows=parts.map(p=>{const m=p.match(LEAD);return m?{icon:m[1],text:p.slice(m[0].length)}:{icon:'',text:p};});
  return rows.every(r=>r.text)?rows:[];
}

const samples=[
  '','.',' ','a',' 💵','. 💵','💵 Thu 100 xu. ✅ Giao xong.','Xong. 👍','Đã chọn 🌸 hoa hồng.','Mở hàng. ✅ Đã nhận cọc.',
  '💵 Thu 100 xu, thối 100 xu. Cuối ca túi COD sẽ thiếu đúng chừng đó. ✅ Giao thành công lúc 17:58 · phí ship +22 xu. 💛 Bé Vy quý bạn hơn (thân thiết 2/10). 🗺️ Đã thuộc hẻm quanh Chung cư Mây Xanh. Túi COD đang giữ 82 xu. 👮 Chốt kiểm tra giấy tờ xe!',
  'Khách nói “ngon quá!” 😋 Tip 5 xu.','(xong) 👌 ok','[x]\t\n 🎉 a','Hết hàng… 😢 Nhập thêm nha!','Chào! 👋🏽 Bạn mới?','Số 1. 1️⃣ Một',
  'A?  ✅ B!   ✅ C.','«Hay» 👏 tiếp','“Ừ” ⭐️ được','a.. 🎉 b','a. . 🎉 b','Lỗi: 🛑 thử lại','Chị Mận: Cẩn thận nha. Đi đường trơn.',
  'Một câu. Hai câu! Ba câu? Bốn… Năm: sáu','12 phút. 3 bước · thưởng 40 xu.','end. ','  lead. trail  ','a. b','a. 💵 b','a.\n\n💵 b',
  'Xin chào.Không cách','x: y: z','…  … 💥','.💵',') 💵','] 🧧 lì xì','» ©️ bản quyền','a! ™ b','a. 🇻🇳 cờ','a. 👨‍👩‍👧 nhà',
];
// Random strings over the characters that matter (sentence ends, quotes, spaces, emoji, letters, surrogates).
const ALPHA=['.','!','?','…',')',']','”','"','»',':',',',' ',' ',' ','\t','\n',' ','a','đ','Ư','1','💵','✅','🗺️','👍🏽','1️⃣','©','‍','️','😀','(','“','·','\u{1F1FB}'];
let seed=20261007;const rnd=n=>{seed=(seed*1103515245+12345)&0x7fffffff;return seed%n;};
for(let i=0;i<20000;i++){let s='';const len=rnd(24);for(let j=0;j<len;j++)s+=ALPHA[rnd(ALPHA.length)];samples.push(s);}

for(const s of samples){
  assert.deepEqual(splitNotes(s),s.split(OLD_TOAST),`toast split: ${JSON.stringify(s)}`);
  assert.deepEqual(toastParts(s),oldToastParts(s),`toastParts: ${JSON.stringify(s)}`);
  assert.deepEqual(sentences(s),s.split(OLD_I18N),`i18n sentences: ${JSON.stringify(s)}`);
}
console.log(`old_safari_regex.mjs: ${samples.length} strings split exactly as before`);

// The check catches what broke iOS 15, and lets the rewrites through.
assert.deepEqual(regexProblems('(?<=[.!?…:])\\s+','u'),['regex lookbehind (?<= (Safari 16.4+)']);
assert.deepEqual(regexProblems('(?<!\\w)x'),['regex lookbehind (?<! (Safari 16.4+)']);
assert.deepEqual(regexProblems('[(?<=]\\(?<=x'),[],'inside a class or escaped: not a lookbehind');
assert.deepEqual(regexProblems('(?<name>a)(?=b)(?!c)(?:d)'),[],'named groups and lookaheads are fine on Safari 15');
assert.ok(regexProblems('a','v').length&&regexProblems('a','d').length,'flags v and d');
assert.ok(regexProblems('(?i:a)').length,'modifiers');
assert.ok(regexProblems('(?<x>a)|(?<x>b)').length,'duplicate group names');
const msgs=src=>checkSource(src).map(p=>p.msg);
assert.match(msgs('const r=/(?<=a)b/u;')[0],/lookbehind/);
assert.match(msgs('const r=new RegExp(`(?<!x)${y}`,"u");')[0],/lookbehind.*RegExp/);
assert.match(msgs('class A{static{this.x=1;}}')[0],/static block/);
assert.match(msgs('const a=[1].at(-1);')[0],/\.at\(\)/);
assert.match(msgs('Object.hasOwn({}, "a");')[0],/Object\.hasOwn/);
assert.match(msgs('const c=structuredClone(x);')[0],/structuredClone/);
assert.match(msgs('[1].toSorted();')[0],/toSorted/);
assert.match(msgs('const x=1;\nusing y=z;')[0]||'',/does not parse/,'syntax newer than ES2022');
assert.deepEqual(msgs('const a=[1].at(-1);',),['.at() needs Safari 15.4+: guard it or load the page with boot.js polyfills']);
assert.deepEqual(checkSource('const a=[1].at(-1);',{polyfilled:new Set(['at'])}),[],'polyfilled by boot.js');
assert.deepEqual(msgs('const id=crypto.randomUUID?.()||1;if(typeof structuredClone==="function")structuredClone(1);try{crypto.randomUUID();}catch{}'),[],'guarded');
assert.deepEqual(msgs('class A{#x=1;static y=2;#m(){return #x in this;}}\nawait 0;\nlet z;z??=1;'),[],'ES2022 that Safari 15.0 has');
assert.deepEqual(msgs('const r=/(?<=a)b/; // old-safari-ok'),[],'explicit allow');
// 07/10 B1/B2: canvas roundRect (Safari 16) and <dialog>.showModal() (15.4) are flagged unless boot.js covers them.
assert.deepEqual(msgs('c.beginPath();c.roundRect(0,0,10,10,4);'),['.roundRect() needs Safari 16+: guard it or load the page with boot.js polyfills']);
assert.deepEqual(msgs('new Path2D().roundRect(0,0,1,1);').length,1);
assert.deepEqual(msgs('d.showModal();'),['.showModal() needs Safari 15.4+: guard it or load the page with boot.js polyfills']);
assert.deepEqual(checkSource('c.roundRect(0,0,1,1);d.showModal();',{polyfilled:new Set(['roundRect','showModal'])}),[],'covered by boot.js');
assert.deepEqual(msgs('c.roundRect?.(0,0,1,1);c.roundRect?c.roundRect(0,0,1,1):c.rect(0,0,1,1);if(typeof d.showModal==="function")d.showModal();'),[],'guarded');
assert.deepEqual(msgs('function roundRect(c){}roundRect(c);'),[],'a plain function of that name');
// Other Safari 15/16 gaps: flagged bare, fine when guarded (feature test, optional call, try).
assert.match(msgs('requestIdleCallback(f);')[0],/requestIdleCallback is missing on every Safari/);
assert.match(msgs('window.requestIdleCallback(f);')[0],/requestIdleCallback/);
assert.deepEqual(msgs('if(globalThis.requestIdleCallback)requestIdleCallback(f);(window.requestIdleCallback||setTimeout)(f);'),[]);
assert.match(msgs('const o=new OffscreenCanvas(1,1);')[0],/OffscreenCanvas needs Safari 16\.4/);
assert.deepEqual(msgs('if(typeof OffscreenCanvas==="function")new OffscreenCanvas(1,1);'),[]);
assert.match(msgs('ctx.reset();')[0],/canvas reset/);
assert.deepEqual(msgs('form.reset();edit().reset();'),[],'reset() of a form or a helper is not the canvas one');
assert.match(msgs('el.checkVisibility();')[0],/checkVisibility/);
assert.deepEqual(msgs('typeof e.checkVisibility==="function"?e.checkVisibility():0;'),[]);
assert.match(msgs('navigator.userActivation.isActive;')[0],/userActivation/);
assert.deepEqual(msgs('const o={structuredClone:1};a.structuredClone(1);class K{structuredClone(){}}'),[],'a key or a property, not the global');
console.log('old_safari_regex.mjs (check): ok');

// boot.js: the polyfills the check relies on are there, and work where the built-ins are missing.
const boot=readFileSync(new URL('../public/js/boot.js',import.meta.url),'utf8');
assert.deepEqual([...bootPolyfills(boot)].sort(),['at','findLast','findLastIndex','hasOwn','randomUUID','roundRect','showModal']);
const head=boot.slice(boot.indexOf('(()=>{')+6,boot.indexOf('const d=document'));
const ctx=vm.createContext({});
vm.runInContext(`delete Array.prototype.at;delete String.prototype.at;delete Object.getPrototypeOf(Int8Array.prototype).at;delete Object.hasOwn;
  delete Array.prototype.findLast;delete Array.prototype.findLastIndex;
  globalThis.crypto={getRandomValues:a=>{for(let i=0;i<a.length;i++)a[i]=(i*37+11)&255;return a;}};`,ctx);
vm.runInContext(head,ctx);
const r=vm.runInContext(`({
  a:[[1,2,3].at(-1),[1,2,3].at(0),[1,2,3].at(5),[1,2,3].at(-4),[1,2,3].at('1'),[].at(0),'héllo'.at(-1),new Uint8Array([7,8]).at(-1)],
  h:[Object.hasOwn({a:1},'a'),Object.hasOwn({a:1},'toString'),Object.hasOwn([5],0)],
  f:[[1,2,3,4].findLast(x=>x%2),[1,2,3,4].findLastIndex(x=>x%2),[1].findLast(x=>x>5),[1].findLastIndex(x=>x>5)],
  u:crypto.randomUUID(),
  enumerable:Object.keys(Array.prototype).length,
  nullThrows:(()=>{try{Object.hasOwn(null,'a');return false;}catch(e){return e instanceof TypeError;}})(),
})`,ctx);
assert.deepEqual(JSON.parse(JSON.stringify(r.a)),[3,1,null,null,2,null,'o',8]);
assert.deepEqual(r.a[2],undefined);
assert.deepEqual(JSON.parse(JSON.stringify(r.h)),[true,false,true]);
assert.deepEqual(JSON.parse(JSON.stringify(r.f)),[3,2,null,-1]);
assert.match(r.u,/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
assert.equal(r.enumerable,0,'never enumerable (for…in over arrays stays clean)');
assert.equal(r.nullThrows,true);
// Native built-ins are left alone.
const ctx2=vm.createContext({});const nativeAt=vm.runInContext('Array.prototype.at',ctx2);vm.runInContext(head,ctx2);
assert.equal(vm.runInContext('Array.prototype.at',ctx2),nativeAt);
console.log('old_safari_regex.mjs (boot polyfills): ok');

// boot.js roundRect: where Safari 15 has none. A path recorder stands in for the canvas; the outline it draws is
// flattened and compared, on a grid, with an independent rounded-rectangle test (radius i at the i-th corner going
// round from (x, y): (x,y), (x+w,y), (x+w,y+h), (x,y+h); corners scaled down together when they would overlap).
const ctx3=vm.createContext({});
vm.runInContext(`globalThis.CanvasRenderingContext2D=function(){};globalThis.Path2D=function(){};
  globalThis.OffscreenCanvasRenderingContext2D=function(){};OffscreenCanvasRenderingContext2D.prototype.roundRect=function native(){};`,ctx3);
vm.runInContext(head,ctx3);
const RR=vm.runInContext('CanvasRenderingContext2D.prototype.roundRect',ctx3);
assert.equal(typeof RR,'function');
assert.equal(vm.runInContext('Path2D.prototype.roundRect',ctx3),RR,'Path2D too');
assert.equal(vm.runInContext('OffscreenCanvasRenderingContext2D.prototype.roundRect.name',ctx3),'native','a native one is kept');
assert.equal(vm.runInContext('Object.keys(CanvasRenderingContext2D.prototype).length',ctx3),0,'not enumerable');
function recorder(){
  const ops=[];
  return {ops,moveTo:(x,y)=>ops.push(['M',x,y]),lineTo:(x,y)=>ops.push(['L',x,y]),closePath:()=>ops.push(['Z']),
    ellipse:(cx,cy,rx,ry,rot,a0,a1,ccw)=>{assert.ok(rx>0&&ry>0&&rot===0);ops.push(['E',cx,cy,rx,ry,a0,a1,ccw]);}};
}
/** The recorded outline as a polygon (first subpath only), and the trailing moveTo. */
function outline(ops){
  const pts=[];let i=0;
  for(;i<ops.length;i++){const o=ops[i];
    if(o[0]==='M'){if(pts.length)break;pts.push([o[1],o[2]]);}
    else if(o[0]==='L')pts.push([o[1],o[2]]);
    else if(o[0]==='E'){const [,cx,cy,rx,ry,a0,a1,ccw]=o;
      assert.ok(ccw?a0>=a1:a1>=a0,'sweeps the short way round');
      for(let k=0;k<=24;k++){const a=a0+(a1-a0)*k/24;pts.push([cx+rx*Math.cos(a),cy+ry*Math.sin(a)]);}}
    else if(o[0]==='Z'){i++;break;}
  }
  return {pts,rest:ops.slice(i)};
}
const inPoly=(pts,[px,py])=>{let w=false;for(let i=0,j=pts.length-1;i<pts.length;j=i++){const [xi,yi]=pts[i],[xj,yj]=pts[j];
  if((yi>py)!==(yj>py)&&px<(xj-xi)*(py-yi)/(yj-yi)+xi)w=!w;}return w;};
const area=pts=>pts.reduce((s,[x1,y1],i)=>{const [x2,y2]=pts[(i+1)%pts.length];return s+x1*y2-x2*y1;},0)/2;
function reference(x,y,w,h,radii){
  const list=Array.isArray(radii)?radii:[radii],n=list.length;
  let r=list.map(v=>typeof v==='object'?[v.x??0,v.y??0]:[v,v]);
  r=n===4?r:n===3?[r[0],r[1],r[2],r[1]]:n===2?[r[0],r[1],r[0],r[1]]:[r[0],r[0],r[0],r[0]];
  const W=Math.abs(w),H=Math.abs(h);
  const s=Math.min(1,W/(r[0][0]+r[1][0]),H/(r[1][1]+r[2][1]),W/(r[2][0]+r[3][0]),H/(r[0][1]+r[3][1]));
  r=r.map(([a,b])=>[a*s,b*s]);
  const corners=[[x,y],[x+w,y],[x+w,y+h],[x,y+h]];
  return ([px,py])=>{
    if(px<=Math.min(x,x+w)||px>=Math.max(x,x+w)||py<=Math.min(y,y+h)||py>=Math.max(y,y+h))return false;
    for(let i=0;i<4;i++){const [cx,cy]=corners[i],[rx,ry]=r[i];if(!(rx>0&&ry>0))continue;
      const ex=cx+(cx===Math.min(x,x+w)?rx:-rx),ey=cy+(cy===Math.min(y,y+h)?ry:-ry);   // the corner ellipse's centre
      const inCorner=(cx<ex?px<ex:px>ex)&&(cy<ey?py<ey:py>ey);
      if(inCorner&&((px-ex)/rx)**2+((py-ey)/ry)**2>1)return false;}
    return true;
  };
}
const CASES=[
  [10,10,80,40,8],[10,10,80,40,0],[10,10,80,40,[12]],[10,10,80,40,[20,4]],[10,10,80,40,[20,4,10]],[10,10,80,40,[22,22,0,0]],
  [10,10,80,40,[30,2,14,6]],[10,10,80,40,{x:30,y:12}],[10,10,80,40,[{x:30,y:6},4,{x:2,y:18},0]],[10,10,80,40,100],
  [10,10,80,40,[60,60,10,10]],[90,10,-80,40,[30,2,14,6]],[10,50,80,-40,[30,2,14,6]],[90,50,-80,-40,[30,2,14,6]],
  [5.5,7.25,33.3,61.9,[9.5,1,20,3.3]],[0,0,100,100,50],[10,10,80,40,[{x:80,y:5}]],
];
for(const [x,y,w,h,radii] of CASES){
  const rec=recorder();RR.call(rec,x,y,w,h,radii);
  const {pts,rest}=outline(rec.ops),ref=reference(x,y,w,h,radii),tag=JSON.stringify([x,y,w,h,radii]);
  assert.deepEqual(rest,[['M',Math.min(x,x+w),Math.min(y,y+h)]],`ends with a new subpath at the top left, like Chromium and WebKit: ${tag}`);
  assert.equal(Math.sign(area(pts)),Math.sign(w*h),`direction flips with each negative side: ${tag}`);
  let bad=0,tested=0;
  for(let gx=-2;gx<=102;gx+=0.37)for(let gy=-2;gy<=72;gy+=0.41){
    const ins=ref([gx,gy]);
    // skip points within half a unit of the true edge (polygon flattening, boundaries)
    const near=[[.5,0],[-.5,0],[0,.5],[0,-.5]].some(([dx,dy])=>ref([gx+dx,gy+dy])!==ins);
    if(near)continue;tested++;if(inPoly(pts,[gx,gy])!==ins)bad++;
  }
  assert.ok(tested>2000,tag);
  assert.equal(bad,0,`same shape as the reference: ${tag}`);
}
// Spec edge cases: non-finite input draws nothing; 0 or 5 radii, or a negative one, is a RangeError.
for(const args of [[NaN,0,10,10,2],[0,0,Infinity,10,2],[0,0,10,10,NaN],[0,0,10,10,[1,Infinity]],[0,0,10,10,{x:NaN,y:1}]]){
  const rec=recorder();RR.call(rec,...args);assert.deepEqual(rec.ops,[],`nothing for ${args}`);
}
for(const radii of [[],[1,2,3,4,5],-1,[1,-2],{x:1,y:-1}])assert.throws(()=>RR.call(recorder(),0,0,10,10,radii),e=>e instanceof RangeError||e?.name==='RangeError',JSON.stringify(radii));
{const rec=recorder();RR.call(rec,1,2,30,40);assert.deepEqual(rec.ops.filter(o=>o[0]==='E'),[],'no radii: square corners');}
console.log(`old_safari_regex.mjs (roundRect polyfill): ${CASES.length} shapes match`);
