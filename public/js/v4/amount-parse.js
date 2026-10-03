/** What a player types in a money box → a whole number, or why not (player reports 03/10: no minus sign on a phone's
 * number pad, no "6+4", no "10 triệu"). Used by the accounting school (TT99), the accounting careers and tax_payroll.
 *
 *   minus: -500.000 · −500000 · (500.000)            (accounting brackets: one number in brackets is negative)
 *   separators: 1.000.000 · 1,000,000 · 1 000 000      (a lone . or , before 3 digits groups; otherwise it is decimal)
 *   decimals with a unit: 1,5 triệu · 1.5tr · 2,5 tỷ · 1tr5
 *   units: đ đồng vnd · k nghìn ngàn (×1.000) · tr triệu (×1.000.000) · tỷ tỉ (×1.000.000.000) · % (÷100)
 *          (and thousand / million / billion / bn for players on the English pack)
 *   arithmetic: + - × * x / : ( )
 *
 * `unit` is the unit shown beside the box (st.unit / f.unit; '' or 'đ' for đồng). A bare number keeps the box's
 * meaning: in a box in triệu, "10" is 10 and so is "10 triệu" or "10.000.000đ". Every number carries its own unit:
 * "6 + 4 triệu" is 6 + 4 triệu (= 10 in a triệu box, 4.000.006 in an đồng box). The box's own unit word ("ngày",
 * "xu", "kg"…) may follow a number too. The result must be a whole number of the box's unit; the server still checks
 * it as before. Exact arithmetic on fractions (BigInt): no floating error, and no eval/Function (CSP). */

const B=BigInt,ZERO=B(0),ONE=B(1),TEN=B(10);
const fold=s=>String(s??'').normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[đĐ]/g,'d').toLowerCase();
const MAG={k:1e3,nghin:1e3,ngan:1e3,tr:1e6,trieu:1e6,ty:1e9,ti:1e9,thousand:1e3,million:1e6,billion:1e9,bn:1e9};   // the English pack's words too
const CUR=['dong','vnd','d'];
const LIMIT=B(10)**B(15);
/** The box's unit as a number of đồng ('triệu' → 1e6). Anything else (đ, xu, ngày, kg…) counts in its own unit: 1. */
function baseOf(unit){
  const u=fold(unit).replace(/\s+(dong|d|vnd)$/,'').trim();
  return B(MAG[u]||1);
}
const gcd=(a,b)=>{a=a<ZERO?-a:a;b=b<ZERO?-b:b;while(b){[a,b]=[b,a%b];}return a;};
const q=(n,d=ONE)=>{if(d===ZERO)throw new Error('div0');if(d<ZERO){n=-n;d=-d;}const g=gcd(n,d)||ONE;return {n:n/g,d:d/g};};
const add=(a,b)=>q(a.n*b.d+b.n*a.d,a.d*b.d),sub=(a,b)=>q(a.n*b.d-b.n*a.d,a.d*b.d);
const mul=(a,b)=>q(a.n*b.n,a.d*b.d),div=(a,b)=>q(a.n*b.d,a.d*b.n);

/** "1.000.000", "1,5", "1 000,25", "1,234.5" → a fraction; null when the separators do not make sense. */
function numeral(raw){
  const seps=raw.replace(/\d/g,''),parts=raw.split(/[., ]/);
  if(!seps)return q(B(raw));
  const last=seps[seps.length-1],once=seps.indexOf(last)===seps.length-1;
  const grouped=(s,ch)=>{   // 1.234.567: a first group of 1–3 digits (no leading 0), then groups of 3
    const g=s.split(ch);
    return g[0].length>=1&&g[0].length<=3&&g[0][0]!=='0'&&g.slice(1).every(x=>x.length===3)&&g.every(x=>/^\d+$/.test(x))?q(B(g.join(''))):null;
  };
  const decimal=()=>{
    if(last===' '||!once)return null;
    const i=raw.lastIndexOf(last),head=raw.slice(0,i),tail=raw.slice(i+1),hs=head.replace(/\d/g,'');
    if(!/^\d+$/.test(tail))return null;
    const whole=!hs?q(B(head)):new Set(hs).size===1&&!hs.includes(last)?grouped(head,hs[0]):null;
    return whole&&add(whole,q(B(tail),TEN**B(tail.length)));
  };
  const mixed=new Set(seps).size>1;
  if(mixed)return decimal();
  if(!once||parts[parts.length-1].length===3){const g=grouped(raw,last);if(g)return g;}
  return decimal();
}

function tokens(src,unit){
  const s=fold(src).replace(/[   ]/g,' ').replace(/[−–‒‐]/g,'-').replace(/[×✕]/g,'*').replace(/[÷:]/g,'/').trim().replace(/=+$/,'').trim();
  const own=fold(unit).trim(),word=/^[a-z]+$/.test(own)&&!MAG[own]&&!CUR.includes(own)?own:'';
  let body=s;
  if(own&&!word&&!/^[a-z]+$/.test(own)&&own!=='%'&&body.endsWith(own))body=body.slice(0,-own.length).trim();   // "250 xu/thang"
  const base=baseOf(unit),out=[];let i=0;
  const letters=at=>/^[a-z]+/.exec(body.slice(at))?.[0]||'';
  const skip=()=>{while(body[i]===' ')i++;};
  while(i<body.length){
    const c=body[i];
    if(c===' '){i++;continue;}
    if(/\d/.test(c)){
      const m=/^\d+(?:[., ]\d+)*/.exec(body.slice(i));
      let raw=m[0];while(/[ ]\d+$/.test(raw)&&!/^\d{3}$/.test(raw.slice(raw.lastIndexOf(' ')+1)))raw=raw.slice(0,raw.lastIndexOf(' '));
      i+=raw.length;
      let v=numeral(raw);if(!v)throw new Error('number');
      const at=i;skip();
      const w=letters(i);
      if(MAG[w]){
        i+=w.length;let f=q(B(MAG[w]));
        const tail=/^\d+/.exec(body.slice(i))?.[0];   // 1tr5 = 1,5 triệu
        if(tail&&!/[., ]/.test(raw)){v=add(v,q(B(tail),TEN**B(tail.length)));i+=tail.length;}
        skip();const cw=letters(i);if(CUR.includes(cw))i+=cw.length;else if(cw===word&&word)i+=cw.length;
        v=div(mul(v,f),q(base));
      }else if(CUR.includes(w)){i+=w.length;v=div(v,q(base));}
      else if(word&&w===word)i+=w.length;
      else i=at;
      skip();
      while(body[i]==='%'){i++;if(own!=='%')v=div(v,q(B(100)));skip();}
      if(/\d/.test(body[i]||''))throw new Error('number');
      out.push({t:'n',v});continue;
    }
    if('+-*/()'.includes(c)){out.push({t:c});i++;continue;}
    if(c==='x'&&!/[a-z]/.test(body[i+1]||'')){out.push({t:'*'});i++;continue;}
    throw new Error('char');
  }
  return out;
}

/** Recursive descent: expr = term (± term)*, term = unary (×÷ unary)*, unary = -unary | primary, primary = n | ( expr ). */
function evaluate(list){
  let i=0;
  const peek=()=>list[i]?.t,need=t=>{if(peek()!==t)throw new Error('syntax');i++;};
  const primary=()=>{
    if(peek()==='n')return {v:list[i++].v,lit:true};
    if(peek()==='('){i++;const r=expr();need(')');return {v:r.v,bracketed:!!r.lit};}
    throw new Error('syntax');
  };
  const unary=depth=>{
    if(depth>40)throw new Error('syntax');
    if(peek()==='-'){i++;const u=unary(depth+1).v;return {v:q(-u.n,u.d)};}
    if(peek()==='+'){i++;return {v:unary(depth+1).v};}
    return primary();
  };
  const term=()=>{let a=unary(0);while(peek()==='*'||peek()==='/'){const op=list[i++].t,b=unary(0);a={v:op==='*'?mul(a.v,b.v):div(a.v,b.v)};}return a;};
  const expr=()=>{let a=term();while(peek()==='+'||peek()==='-'){const op=list[i++].t,b=term();a={v:op==='+'?add(a.v,b.v):sub(a.v,b.v)};}return a;};
  if(!list.length)throw new Error('syntax');
  const r=expr();
  if(i!==list.length)throw new Error('syntax');
  return r.bracketed?q(-r.v.n,r.v.d):r.v;   // (500.000) = -500.000, the way books write a negative
}

/** → {ok:true, value} with a safe integer, or {ok:false, reason: 'empty'|'syntax'|'fraction'|'big', approx?}. */
export function parseAmount(raw,unit=''){
  if(typeof raw==='number')return Number.isSafeInteger(raw)?{ok:true,value:raw}:{ok:false,reason:Number.isFinite(raw)?'fraction':'syntax'};
  const text=String(raw??'').trim();
  if(!text)return {ok:false,reason:'empty'};
  if(text.length>120)return {ok:false,reason:'syntax'};
  let v;
  try{v=evaluate(tokens(text,unit));}catch{return {ok:false,reason:'syntax'};}
  const abs=x=>x<ZERO?-x:x;
  if(abs(v.n)>LIMIT*v.d)return {ok:false,reason:'big'};
  if(v.d!==ONE)return {ok:false,reason:'fraction',approx:Number(v.n)/Number(v.d)};
  return {ok:true,value:Number(v.n)};
}
/** The whole number, or null (empty, unreadable, not whole). */
export const amountOf=(raw,unit='')=>{const r=parseAmount(raw,unit);return r.ok?r.value:null;};

/** 1234567 → "1.234.567"; 1,5 → "1,5" (Vietnamese marks, the same in every browser). */
export function formatAmount(n){
  const neg=n<0,x=Math.abs(n),whole=Math.trunc(x),frac=Math.round((x-whole)*1000);
  const g=String(whole).replace(/\B(?=(\d{3})+(?!\d))/g,'.');
  return (neg?'-':'')+g+(frac?','+String(frac).padStart(3,'0').replace(/0+$/,''):'');
}

/** The line under a box: '' when there is nothing to add, else "= 10.000.000" or why the number is not read. */
export function amountNote(raw,unit='',{plain=false}={}){
  const r=parseAmount(raw,unit),text=String(raw??'').trim(),show=n=>plain&&Number.isInteger(n)?String(n):formatAmount(n);
  if(r.ok){const typed=text.replace(/\s+/g,'');return typed===String(r.value)||typed===show(r.value)?{text:'',bad:false}:{text:`= ${show(r.value)}`,bad:false};}
  if(r.reason==='empty')return {text:'',bad:false};
  if(r.reason==='fraction')return {text:`= ${formatAmount(r.approx)} · cần số nguyên`,bad:true};
  if(r.reason==='big')return {text:'Số quá lớn',bad:true};
  return {text:'Chưa hiểu số này',bad:true};
}

const escText=s=>String(s).replace(/[&<>"']/g,c=>`&#${c.charCodeAt(0)};`);
/** Attributes of a money box: the full keyboard (−, +, letters for "triệu"), never a numbers-only pad.
 *  plain: the note writes 12400, not 12.400 (tax_payroll's pages show numbers the way players type them). */
export const amountAttrs=(unit,{plain=false}={})=>`type="text" autocomplete="off" autocapitalize="off" spellcheck="false" data-amount="${escText(unit??'')}"${plain?' data-amount-plain':''}`;
/** The note under a box, rendered with the box (a saved draft such as "6+4" shows its value at once). */
export function amountNoteHTML(raw,unit='',opts){
  const n=amountNote(raw,unit,opts);
  return `<small class="amt-note${n.bad?' bad':''}" data-amt-note>${escText(n.text)}</small>`;
}

/** Live: every box with data-amount refreshes the note in its [data-amt-box] (or its parent) as the player types. */
export function refreshAmountNote(el){
  if(!el?.dataset||el.dataset.amount===undefined)return;
  const box=el.closest?.('[data-amt-box]')||el.parentElement,note=box?.querySelector('[data-amt-note]');
  const n=amountNote(el.value,el.dataset.amount,{plain:el.dataset.amountPlain!==undefined});
  el.classList.toggle('amt-unread',n.bad);
  if(note){note.textContent=n.text;note.classList.toggle('bad',n.bad);}
}
if(typeof document!=='undefined'&&!globalThis.__amountWatch){
  globalThis.__amountWatch=true;
  document.addEventListener('input',e=>refreshAmountNote(e.target));
}
