/** Client-side language layer. Vietnamese is the source language everywhere
 * (server messages, content, UI). English is applied on display: exact strings
 * from /i18n/en.json, then regex patterns for strings with numbers or names.
 * Payload identifiers are never translated, so game rules stay identical.
 * The pack is built by scripts/i18n_extract.py. */
let lang='vi',dict=null,patterns=[],outputs=new Set(),observer=null,loading=null;
const VI=/[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
const ATTRS=['aria-label','placeholder','title','alt','data-tip'];
const EDGE=/^([\p{Extended_Pictographic}\p{S}\p{P}\d\s‍️]*?)([\p{L}][\s\S]*?)([\s\p{Extended_Pictographic}‍️]*)$/u;
const SEP=/(\s+[·•|–—→+]\s+|\s*\/\s+)/u;
// Vietnamese without diacritics: "30 xu", " xu", "Anh Phong", "Em Na".
const XU=/(?:^\s*|\d\s?)xu\b/i,TITLE=/^\s*(?:Anh|Em) \p{Lu}/u;
const isVi=s=>VI.test(s)||XU.test(s)||TITLE.test(s);
const memo=new Map();
/** Vietnamese strings seen in English mode without a translation (for QA). */
export const misses=new Set();
globalThis.__i18nMisses=misses;

export const language=()=>lang;

async function load(){
  if(dict)return;
  const url=globalThis.__mnlBoot?.asset?.('/i18n/en.json')||'/i18n/en.json',early=globalThis.__mnlBoot?.i18n||Promise.resolve(null);
  loading??=early.then(pack=>pack||fetch(url,{credentials:'same-origin'}).then(r=>r.ok?r.json():{strings:{},patterns:[]})).catch(()=>({strings:{},patterns:[]}));
  const data=await loading;
  dict=data.strings||{};
  outputs=new Set(Object.values(dict));
  patterns=(data.patterns||[]).filter(p=>Array.isArray(p)&&typeof p[0]==='string'&&typeof p[1]==='string').map(([src,out],i)=>({i,src,out,lit:literals(src),re:undefined}));
  byFirst=new Map();anyFirst=patterns.filter(p=>!p.lit?.[0]);
}

/* Pattern index. The pack has ~6,700 patterns; trying every one as a regex on each untranslated string cost
 * ~5 ms per string on a laptop (20+ ms on a phone), plus compiling all of them on the first English screen.
 * A pack pattern is literal text around (.+?) holes, so a string can only match when it starts with the
 * first piece, ends with the last and holds the others in order: that check (plain string search) picks the
 * few candidates, in pack order, and only those run as regexes (compiled on first use). Same results. */
let byFirst=new Map(),anyFirst=[];
/** Literal pieces around the (.+?) holes, or null when the source uses other regex syntax (always tried). */
function literals(src){
  const segs=[''];
  for(let i=0;i<src.length;i++){
    const ch=src[i];
    if(ch==='('&&src.startsWith('(.+?)',i)){segs.push('');i+=4;continue;}
    if(ch==='\\'){const n=src[i+1];if(n===undefined||/[\w]/.test(n))return null;segs[segs.length-1]+=n;i++;continue;}
    if('^$.|?*+()[]{}'.includes(ch))return null;
    segs[segs.length-1]+=ch;
  }
  return segs;
}
/** Could `key` match this pattern? (necessary condition: the regex decides) */
function fits(lit,key){
  if(!lit)return true;
  const last=lit.length-1;
  if(!last)return key===lit[0];
  if(!key.startsWith(lit[0])||!key.endsWith(lit[last])||key.length<lit.reduce((n,s)=>n+s.length,last))return false;
  let pos=lit[0].length;
  for(let j=1;j<last;j++){const at=key.indexOf(lit[j],pos+1);if(at<0)return false;pos=at+lit[j].length;}
  return key.length-lit[last].length>pos;
}
/** Patterns worth trying for `key`, in pack order (first match wins, as before). */
function candidates(key){
  const first=key[0];
  let list=byFirst.get(first);
  if(!list){
    const own=patterns.filter(p=>p.lit?.[0]?.[0]===first);
    list=own.length?[...own,...anyFirst].sort((a,b)=>a.i-b.i):anyFirst;
    byFirst.set(first,list);
  }
  return list;
}
function regex(p){if(p.re===undefined){try{p.re=new RegExp('^'+p.src+'$','u');}catch{p.re=null;}}return p.re;}

/** A pattern capture that stays Vietnamese means the pattern matched too
 * broadly ("Đã $1" swallowing a whole sentence): try the next one instead.
 * Capitalised names ("Hạnh", "Mầm Nắng") are fine to keep. */
function viWords(text){
  const words=text.match(/\p{L}+/gu)||[];
  return words.some(w=>VI.test(w)&&(w===w.toLowerCase()||w.length>1&&w===w.toUpperCase()));
}
function tooBroad(src,tr){
  if(/\s[·•|]\s/u.test(src))return true;
  return tr===null?viWords(src):tr!==src&&viWords(tr);
}

function lookup(key,depth,variants=true){
  const hit=dict[key];
  if(hit!==undefined)return hit;
  // Already English ("Mầm Nắng Class"); "30 xu" is still Vietnamese even if some output reads so.
  if(VI.test(key)&&outputs.has(key))return key;
  // A sentence shown without its final period ("Cân đúng lạng").
  if(!/[.!?…:]$/u.test(key)){const d=dict[key+'.'];if(typeof d==='string'&&d.endsWith('.'))return d.slice(0,-1);}
  const v=variants?caseVariant(key):null;
  if(v)for(const k of v.keys)if(dict[k]!==undefined)return v.back(dict[k]);
  for(const p of candidates(key)){
    if(!fits(p.lit,key))continue;
    const re=regex(p),m=re&&key.match(re);
    if(!m)continue;
    const out=p.out;
    let ok=true;
    const res=out.replace(/\$(\d)/g,(_,i)=>{
      const src=m[Number(i)]??'',tr=resolve(src,depth+1);
      if(tooBroad(src,tr))ok=false;
      return tr??src;
    });
    if(ok)return res;
  }
  if(v)for(const k of v.keys){const r=lookup(k,depth,false);if(r!==null)return v.back(r);}
  return null;
}

/** "TIẾT HỌC" → "Tiết học" → "LESSON"; "toán vui" → "Toán vui" → "fun math". */
function caseVariant(key){
  const upper=key.toLocaleUpperCase('vi'),lower=key.toLocaleLowerCase('vi');
  const cap=s=>s.charAt(0).toLocaleUpperCase('vi')+s.slice(1);
  if(key===upper&&key!==lower&&cap(lower)!==key)return {keys:[cap(lower),lower],back:r=>r.toUpperCase()};
  if(key.charAt(0)===lower.charAt(0)&&key.charAt(0)!==upper.charAt(0))return {keys:[cap(key)],back:r=>r.charAt(0).toLowerCase()+r.slice(1)};
  return null;
}

/** QA only: English text that merely carries Vietnamese names ("Mầm Nắng
 * Class", "Ms. Hạ") is not a miss; lowercase Vietnamese words are. */
function looksVietnamese(key){
  const words=key.match(/\p{L}+/gu)||[],vi=words.filter(w=>VI.test(w));
  if(vi.some(w=>w===w.toLowerCase()))return true;
  const title=w=>w.length>1&&w[0]===w[0].toUpperCase()&&w.slice(1)===w.slice(1).toLowerCase();
  return vi.length===words.length&&!(words.length<=3&&words.every(title));
}

function miss(key,depth){if(depth===0&&misses.size<2000&&looksVietnamese(key))misses.add(key);}

/** Split into pieces, translate each; null unless at least one piece changed. */
function pieces(parts,depth,glue){
  let changed=false;
  const done=parts.map(p=>{
    if(!isVi(p))return p;
    const r=resolve(p,depth+1);
    if(r===null){miss(p,depth);return p;}
    if(r!==p)changed=true;
    return r;
  });
  return changed?done.join(glue):null;
}

/** "bear · Kho 6 · Đang giữ 0": the longest run of segments with a
 * translation wins ("Kho $1 · Đang giữ $2"), the rest go one by one. */
function segments(key,depth){
  const parts=key.split(SEP),segs=parts.filter((_,i)=>i%2===0),seps=parts.filter((_,i)=>i%2);
  if(segs.length>10)return null;
  const out=[];let i=0,changed=false;
  while(i<segs.length){
    let done=null,j=segs.length-1;
    for(;j>i;j--){
      if(i===0&&j===segs.length-1)continue;
      let run=segs[i];for(let k=i;k<j;k++)run+=seps[k]+segs[k+1];
      if(isVi(run)){done=lookup(run,depth+1);if(done!==null)break;}
    }
    if(done!==null)changed=true;
    else{
      j=i;const seg=segs[i];done=seg;
      if(isVi(seg)){const r=resolve(seg,depth+1);if(r===null)miss(seg,depth);else{done=r;changed=changed||r!==seg;}}
    }
    out.push(done);
    if(j<segs.length-1)out.push(seps[j]);
    i=j+1;
  }
  return changed?out.join(''):null;
}

/** Translation of one normalised string, or null when there is none. */
function resolve(key,depth){
  if(!key||!isVi(key))return key;
  if(depth>4)return null;
  // A miss found deep in a nested lookup may only be the depth limit talking: it is reused at the same depth
  // or deeper, never for a shallower lookup of the same text (a sale message lost its "…đã về tài khoản" line).
  const seen=memo.get(key);if(seen&&(seen.out!==null||seen.depth<=depth))return seen.out;
  let out=lookup(key,depth);
  if(out===null){
    // "🍜 Bún bò ·" → translate the core, keep emoji/punctuation around it.
    const m=key.match(EDGE);
    if(m&&(m[1]||m[3])){const core=lookup(m[2],depth);if(core!==null)out=m[1]+core+m[3];}
  }
  if(out===null){
    // “Quoted line” → translate inside the quotes.
    const q=key.match(/^([“"‘(])([\s\S]+)([”"’)][.!?…]*)$/u);
    if(q){const core=resolve(q[2],depth+1);if(core!==null)out=q[1]+core+q[3];}
  }
  if(out===null){
    // "Chị Mận:" / "Cẩn thận 72" / "12 phút": translate the words, keep the rest.
    const p=key.match(/^([\s\S]*?\p{L}[\s\S]*?)([:;,.!?…]+)$/u)||key.match(/^([\s\S]*?\p{L}[\s\S]*?)(\s+[-+]?\d[\d.,:%/]*)$/u);
    if(p){const core=lookup(p[1],depth);if(core!==null)out=core+p[2];}
    const n=out===null&&key.match(/^([-+]?\d[\d.,:%/]*\s+)(\p{L}[\s\S]*)$/u);
    if(n){const core=lookup(n[2],depth);if(core!==null)out=n[1]+core;}
  }
  // "3 bước · thưởng 40 xu" → segments; then sentence by sentence.
  if(out===null&&SEP.test(key))out=segments(key,depth);
  if(out===null){const parts=sentences(key);if(parts.length>1)out=pieces(parts,depth,' ');}
  if(memo.size>20000)memo.clear();
  memo.set(key,{out,depth});
  return out;
}

// Sentence by sentence: cut after . ! ? … : and the spaces that follow. The end mark is matched and kept (no
// lookbehind: Safari parses `(?<=…)` only from 16.4, and one such regex stopped the game loading on iOS 15 /
// 16.0–16.3). Same pieces as `key.split(/(?<=[.!?…:])\s+/u)` (tests/old_safari_regex.mjs).
const SENTENCE_END=/([.!?…:])\s+/gu;
export function sentences(key){
  const out=[];let from=0;
  for(const m of key.matchAll(SENTENCE_END)){out.push(key.slice(from,m.index+1));from=m.index+m[0].length;}
  out.push(key.slice(from));
  return out;
}

function translate(key){
  const out=resolve(key,0);
  if(out===null){miss(key,0);return key;}
  return out;
}

export function t(text){
  if(lang!=='en'||!dict||typeof text!=='string')return text;
  if(!isVi(text)){
    // Canvas labels in capitals without diacritics ("KHO").
    const k=text.trim(),d=dict[k];
    return k.length>2&&k===k.toUpperCase()&&typeof d==='string'?text.replace(k,d):text;
  }
  const key=text.replace(/\s+/g,' ').trim();if(!key)return text;
  const out=translate(key);
  if(out===key)return text;
  // Keep the surrounding whitespace of the original text node.
  const lead=text.match(/^\s*/)[0],tail=text.match(/\s*$/)[0];
  return lead+out+tail;
}

function translateAttrs(el){
  for(const name of ATTRS){
    const v=el.getAttribute?.(name);
    if(v&&isVi(v)){const out=t(v);if(out!==v)el.setAttribute(name,out);}
  }
}

function translateNode(node){
  if(node.nodeType===Node.TEXT_NODE){
    const value=node.nodeValue;
    if(!value||!isVi(value))return;
    const parent=node.parentElement;
    if(!parent||parent.closest('[data-no-translate],script,style,textarea,input'))return;
    const out=t(value);
    if(out!==value)node.nodeValue=out;
    return;
  }
  if(node.nodeType!==Node.ELEMENT_NODE||node.closest?.('[data-no-translate]'))return;
  translateAttrs(node);
  const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT|NodeFilter.SHOW_ELEMENT,{
    acceptNode:n=>n.nodeType===Node.ELEMENT_NODE&&n.hasAttribute('data-no-translate')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT
  });
  let n=walker.nextNode();
  while(n){
    if(n.nodeType===Node.TEXT_NODE)translateNode(n);
    else translateAttrs(n);
    n=walker.nextNode();
  }
}

export async function setLanguage(next){
  lang=next==='en'?'en':'vi';
  document.documentElement.lang=lang;
  if(lang==='en'){
    await load();
    translateNode(document.body);
    document.title=t(document.title);
    if(!observer){
      observer=new MutationObserver(records=>{
        if(lang!=='en')return;
        for(const r of records){
          if(r.type==='childList')r.addedNodes.forEach(translateNode);
          else translateNode(r.target);
        }
      });
      observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:ATTRS});
    }
  }else if(observer){
    observer.disconnect();observer=null;
  }
}
