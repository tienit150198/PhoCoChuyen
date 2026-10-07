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
console.log('old_safari_regex.mjs (check): ok');

// boot.js: the polyfills the check relies on are there, and work where the built-ins are missing.
const boot=readFileSync(new URL('../public/js/boot.js',import.meta.url),'utf8');
assert.deepEqual([...bootPolyfills(boot)].sort(),['at','findLast','findLastIndex','hasOwn','randomUUID']);
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
