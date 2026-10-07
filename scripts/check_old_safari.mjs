// Old-iPhone gate: every browser file must load on Safari 15.0 (iOS 15) and Safari 16.0–16.3.
// 07/10/2026: two regex lookbehinds (Safari 16.4+) made the whole module graph fail on iOS 15 / 16.0–16.3, and
// about 90 iPhones a day could not open the game at all. One file that does not parse = no game.
//
// Checks public/**/*.js|mjs with acorn (scripts/vendor/acorn.mjs, MIT, unmodified; no npm install):
//  1. Syntax: parses at ES2022 (Safari 15.0 has class fields, private methods, `#x in o`, top-level await in
//     modules, logical assignment, numeric separators, optional chaining), then rejects what Safari 15.0 lacks:
//     class static blocks (16.4); top-level await outside a module; anything newer than ES2022 does not parse.
//  2. Regex literals and RegExp('…') strings: no lookbehind (?<= (?<! (16.4), no flag v (17) or d (kept out,
//     like the task asks), no modifiers (?i:…) (ES2025), no duplicate named groups (17).
//  3. Built-ins newer than Safari 15.0: .at() / Object.hasOwn / findLast / findLastIndex / crypto.randomUUID are
//     polyfilled by public/js/boot.js (pages with boot.js only: index.html); the checker verifies those polyfills
//     are there. Others (structuredClone, toSorted, Object.groupBy, Promise.withResolvers, Set#union, …) must be
//     guarded: an optional call `x?.()`, a `typeof`/truthiness test, a try block, or `// old-safari-ok` on the line.
// Run: node scripts/check_old_safari.mjs [files…]   (scripts/check_js.mjs runs it too)
import {readdirSync,readFileSync,statSync} from 'node:fs';
import {join,relative,sep} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {parse} from './vendor/acorn.mjs';

const ROOT=fileURLToPath(new URL('..',import.meta.url));
const BOOT=join(ROOT,'public','js','boot.js');

/** Problems in one regex: [message]. `pattern` is the regex source, `flags` its flags. */
export function regexProblems(pattern,flags=''){
  const out=[];
  if(flags.includes('v'))out.push('regex flag v (Safari 17+)');
  if(flags.includes('d'))out.push('regex flag d (match indices: keep out for old Safari)');
  const names=new Set();
  let inClass=false;
  for(let i=0;i<pattern.length;i++){
    const c=pattern[i];
    if(c==='\\'){i++;continue;}
    if(inClass){if(c===']')inClass=false;continue;}
    if(c==='['){inClass=true;continue;}
    if(c!=='('||pattern[i+1]!=='?')continue;
    const rest=pattern.slice(i+2);
    if(rest.startsWith('<=')||rest.startsWith('<!'))out.push(`regex lookbehind (?${rest.slice(0,2)} (Safari 16.4+)`);
    else if(rest[0]==='<'){const m=/^<([^>]+)>/.exec(rest);if(m){if(names.has(m[1]))out.push(`duplicate regex group name <${m[1]}> (Safari 17+)`);names.add(m[1]);}}
    else if(/^[imsx-]+[:)]/.test(rest))out.push('regex modifiers (?flags:…) (ES2025)');
  }
  return out;
}

// Built-ins Safari 15.0 lacks. poly: boot.js defines it (marker text that must be in boot.js).
const APIS=[
  {name:'.at()',min:'15.4',poly:'at',match:n=>n.type==='CallExpression'&&member(n.callee,'at')},
  {name:'Object.hasOwn',min:'15.4',poly:'hasOwn',match:n=>isPath(n,'Object','hasOwn')},
  {name:'.findLast()',min:'15.4',poly:'findLast',match:n=>n.type==='CallExpression'&&member(n.callee,'findLast')},
  {name:'.findLastIndex()',min:'15.4',poly:'findLastIndex',match:n=>n.type==='CallExpression'&&member(n.callee,'findLastIndex')},
  {name:'crypto.randomUUID',min:'15.4',poly:'randomUUID',match:n=>n.type==='MemberExpression'&&propName(n)==='randomUUID'},
  {name:'structuredClone',min:'15.4',match:n=>n.type==='Identifier'&&n.name==='structuredClone'},
  ...['toSorted','toReversed','toSpliced'].map(p=>({name:`.${p}()`,min:'16',match:n=>n.type==='CallExpression'&&member(n.callee,p)})),
  {name:'Array.fromAsync',min:'16.4',match:n=>isPath(n,'Array','fromAsync')},
  ...['isWellFormed','toWellFormed'].map(p=>({name:`.${p}()`,min:'16.4',match:n=>n.type==='CallExpression'&&member(n.callee,p)})),
  ...['union','intersection','symmetricDifference','isSubsetOf','isSupersetOf','isDisjointFrom'].map(p=>({name:`Set#${p}`,min:'17',match:n=>n.type==='CallExpression'&&member(n.callee,p)})),
  {name:'Object.groupBy',min:'17.4',match:n=>isPath(n,'Object','groupBy')},
  {name:'Map.groupBy',min:'17.4',match:n=>isPath(n,'Map','groupBy')},
  {name:'Promise.withResolvers',min:'17.4',match:n=>isPath(n,'Promise','withResolvers')},
  {name:'Promise.try',min:'18.2',match:n=>isPath(n,'Promise','try')},
  {name:'RegExp.escape',min:'18.2',match:n=>isPath(n,'RegExp','escape')},
  {name:'AbortSignal.timeout',min:'16',match:n=>isPath(n,'AbortSignal','timeout')},
  {name:'AbortSignal.any',min:'17.4',match:n=>isPath(n,'AbortSignal','any')},
  {name:'Iterator.from',min:'18.4',match:n=>isPath(n,'Iterator','from')},
];
function propName(m){return m.computed?(m.property.type==='Literal'?m.property.value:null):m.property.name;}
function member(n,name){return n?.type==='MemberExpression'&&propName(n)===name;}
function isPath(n,obj,prop){
  if(n.type!=='MemberExpression'||propName(n)!==prop)return false;
  const o=n.object;
  return (o.type==='Identifier'&&o.name===obj)||(o.type==='MemberExpression'&&propName(o)===obj&&/^(globalThis|window|self)$/.test(o.object?.name||''));
}

/** Is this API reference only tested, called optionally (`x?.()`), in a try, or under a test that names it? */
function guarded(node,parents,word,src){
  const tested=t=>t&&src.slice(t.start,t.end).includes(word);
  for(let i=0;i<parents.length;i++){
    const a=parents[i],c=parents[i+1]||node;
    if((a.type==='IfStatement'||a.type==='ConditionalExpression')&&c===a.consequent&&tested(a.test))return true;
    if(a.type==='LogicalExpression'&&a.operator==='&&'&&c===a.right&&tested(a.left))return true;
  }
  const p=parents.at(-1);
  if(!p)return false;
  if(p.type==='UnaryExpression'&&p.operator==='typeof')return true;
  if(p.type==='ChainExpression'||(p.type==='CallExpression'&&p.optional&&p.callee===node))return true;
  if(node.type==='CallExpression'&&node.optional)return true;
  if(node.type==='MemberExpression'&&p.type==='CallExpression'&&p.callee===node&&p.optional)return true;
  if((p.type==='LogicalExpression'&&p.left===node)||(p.type==='IfStatement'&&p.test===node)||(p.type==='ConditionalExpression'&&p.test===node))return true;
  if(p.type==='UnaryExpression'&&p.operator==='!')return true;
  if(p.type==='BinaryExpression'&&p.operator==='in')return true;
  // inside the block of a try (the catch is the fallback)
  return parents.some((a,i)=>a.type==='TryStatement'&&(parents[i+1]||node)===a.block);
}

function walk(node,visit,parents=[]){
  if(!node||typeof node.type!=='string')return;
  visit(node,parents);
  parents.push(node);
  for(const key of Object.keys(node)){
    if(key==='loc'||key==='start'||key==='end')continue;
    const v=node[key];
    if(Array.isArray(v)){for(const c of v)if(c&&typeof c.type==='string')walk(c,visit,parents);}
    else if(v&&typeof v.type==='string')walk(v,visit,parents);
  }
  parents.pop();
}

/** All problems of one source text: [{line, col, msg}]. `polyfilled`: APIs boot.js covers for this file. */
export function checkSource(src,{module=true,polyfilled=new Set()}={}){
  const out=[],lines=src.split('\n');
  let ast;
  try{ast=parse(src,{ecmaVersion:2022,sourceType:module?'module':'script',locations:true,allowHashBang:false});}
  catch(e){return [{line:e.loc?.line||0,col:e.loc?.column||0,msg:`does not parse as ES2022 ${module?'module':'script'}: ${e.message}`}];}
  const at=(n,msg)=>{const line=n.loc.start.line;if(!/old-safari-ok/.test(lines[line-1]||''))out.push({line,col:n.loc.start.column+1,msg});};
  walk(ast,(n,parents)=>{
    if(n.type==='StaticBlock')at(n,'class static block (Safari 16.4+)');
    if(n.type==='Literal'&&n.regex)for(const m of regexProblems(n.regex.pattern,n.regex.flags))at(n,m);
    if((n.type==='NewExpression'||n.type==='CallExpression')&&n.callee.type==='Identifier'&&n.callee.name==='RegExp'&&n.arguments.length){
      const [src,flags]=n.arguments;
      const text=src.type==='Literal'&&typeof src.value==='string'?src.value:src.type==='TemplateLiteral'?src.quasis.map(q=>q.value.cooked).join('\u0000'):'';
      const f=flags?.type==='Literal'&&typeof flags.value==='string'?flags.value:'';
      for(const m of regexProblems(text,f))at(n,`${m} in RegExp()`);
    }
    for(const api of APIS){
      if(!api.match(n))continue;
      if(api.poly&&polyfilled.has(api.poly))continue;
      if(guarded(n,parents,api.name.replace(/^.*[.#]|\(\)$/g,''),src))continue;
      at(n,`${api.name} needs Safari ${api.min}+: guard it${api.poly?' or load the page with boot.js polyfills':''}`);
    }
  });
  return out;
}

/** The polyfill markers boot.js really defines (it is inlined first into index.html). */
export function bootPolyfills(src=readFileSync(BOOT,'utf8')){
  const has=new Set();
  if(/poly\(\s*Array\.prototype\s*,\s*'at'/.test(src)&&/poly\(\s*String\.prototype\s*,\s*'at'/.test(src))has.add('at');
  if(/poly\(\s*Object\s*,\s*'hasOwn'/.test(src))has.add('hasOwn');
  if(/poly\(\s*Array\.prototype\s*,\s*'findLast'/.test(src))has.add('findLast');
  if(/poly\(\s*Array\.prototype\s*,\s*'findLastIndex'/.test(src))has.add('findLastIndex');
  if(/poly\(\s*C\s*,\s*'randomUUID'/.test(src))has.add('randomUUID');
  return has;
}

function files(dir){
  const out=[];
  for(const name of readdirSync(dir)){const p=join(dir,name);if(statSync(p).isDirectory()){if(name!=='_v')out.push(...files(p));}   // _v: hashed copies of these files (game/webassets.py)
    else if(/\.m?js$/.test(p))out.push(p);}
  return out;
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  const list=process.argv.slice(2).length?process.argv.slice(2):files(join(ROOT,'public'));
  const poly=bootPolyfills();
  let bad=0;
  for(const f of list){
    const rel=relative(ROOT,f).split(sep).join('/');
    // boot.js itself and sw.js are classic scripts; admin/ (admin.html) and sw.js have no boot.js polyfills.
    const classic=/^public\/(js\/boot\.js|sw\.js)$/.test(rel);
    const withBoot=rel.startsWith('public/js/')&&!rel.startsWith('public/js/admin/')&&!classic;
    const probs=checkSource(readFileSync(f,'utf8'),{module:!classic,polyfilled:withBoot?poly:new Set()});
    for(const p of probs)console.error(`✗ ${rel}:${p.line}:${p.col} ${p.msg}`);
    if(probs.length)bad++;
  }
  console.log(`${list.length-bad}/${list.length} JS files OK for Safari 15.0 / iOS 15 (old-Safari check)`);
  process.exit(bad?1:0);
}
