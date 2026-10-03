/** Toast text → tidy lines. A command result often chains several notes into one string
 * ("💵 Thu 100 xu… ✅ Giao thành công… 💛 Bé Vy quý bạn hơn…"); read as one paragraph it is a wall
 * of text. Each note that starts with an emoji right after a sentence end becomes its own row:
 * the emoji in a fixed left column, the first row as the headline, the rest a size smaller. */
const PICT=/\p{Extended_Pictographic}/u;
// A sentence end (. ! ? … or a closing bracket/quote after one), spaces, then an emoji (with its modifiers).
const SPLIT=/(?<=[.!?…)\]”"»])\s+(?=\p{Extended_Pictographic})/u;
const LEAD=/^((?:\p{Extended_Pictographic}|\p{Emoji_Modifier}|️|‍|⃣)+)\s*/u;

/** [{icon, text}] — a single part (or none with an emoji) means: keep the plain toast. */
export function toastParts(message){
  const parts=String(message??'').split(SPLIT).map(s=>s.trim()).filter(Boolean);
  if(parts.length<2||!parts.slice(1).every(p=>PICT.test(p.slice(0,2))))return [];
  const rows=parts.map(p=>{const m=p.match(LEAD);return m?{icon:m[1],text:p.slice(m[0].length)}:{icon:'',text:p};});
  return rows.every(r=>r.text)?rows:[];   // "Xong. 👍": a trailing emoji alone is not a note
}

/** Fill a .toast element: rows when the text chains several notes, plain text otherwise. */
export function fillToast(el,message){
  const parts=toastParts(message);
  if(!parts.length){el.textContent=message;return false;}
  el.classList.add('multi');el.textContent='';
  const list=document.createElement('ul');list.className='toast-lines';
  for(const p of parts){
    const li=document.createElement('li');
    const ic=document.createElement('span');ic.className='tl-ic';ic.setAttribute('aria-hidden','true');ic.textContent=p.icon||'•';
    const tx=document.createElement('span');tx.className='tl-tx';tx.textContent=p.text;
    li.append(ic,tx);list.append(li);
  }
  el.append(list);
  return true;
}

/** Words that count toward a toast's length: an emoji, "·" or "→" alone is not a word. */
const count=s=>s.split(' ').filter(w=>/[\p{L}\d]/u.test(w)).length;
const QUOTE=/[“"«][^”"»]*(?:[”"»]|$)/u;
/** The few words a toast shows (owner 03/10: "chữ ít thôi"): the whole note when it is short; else its first
 * note, a customer's quoted words dropped when there is a note around them (only the words when there is
 * not), asides in brackets dropped, the first sentence, then at most `max` words: cut at a " · ", " — ",
 * ": ", ", " break when one leaves a full phrase, else with "…". An error keeps its whole first sentence:
 * it says what to fix. {head, more}: more = the full text says more (a tap on the toast shows it). */
export function toastHead(message,{max=8,error=false}={}){
  const full=String(message??'').replace(/\s+/g,' ').trim();
  const bare=t=>t.replace(/^[•\s]+/u,'').replace(/[\s.!?…:·,—–-]+$/u,'');
  if(count(full)<=max)return {head:full,more:false};
  const rows=toastParts(full);
  let s=(rows.length?`${rows[0].icon?rows[0].icon+' ':''}${rows[0].text}`:full).replace(/^[•\s]+/u,'');
  // "Chị Hạnh: “…”": the speaker alone says nothing, so the words stay; "Linh để lại 5 xu tip: “…”": the note stays.
  const said=s.match(new RegExp(`^([^“"«]{1,60}?): *(${QUOTE.source})$`,'u'));
  if(said&&count(said[1])<=7&&!/\d/.test(said[1]))s=said[2].replace(/^[“"«]|[”"»]$/gu,'');
  else s=s.replace(new RegExp(`: *${QUOTE.source}`,'gu'),'').replace(new RegExp(`([.!?…]) +${QUOTE.source}`,'gu'),'$1').trim()||s;
  if(!error)s=s.replace(/\s*\((?:[^()]|\([^()]*\))*\)/gu,'');
  const sentence=s.match(/^(.+?[.!?…])(?=\s|$)/u);
  // A one-word first sentence ("Bíp!") is not a note: keep the next one with it.
  if(sentence&&count(sentence[1])>=3)s=sentence[1];
  else if(sentence){const two=s.match(/^(.+?[.!?…]\s+.+?[.!?…])(?=\s|$)/u);if(two)s=two[1];}
  s=s.replace(/[\s.:·,—–-]+$/u,'').trim();
  if(!error&&count(s)>max){
    let cut='';
    for(const br of [' · ',' — ',' – ',' → ',': ',', ']){
      for(let i=s.indexOf(br);i>0;i=s.indexOf(br,i+1)){
        const head=s.slice(0,i).trim(),n=count(head);
        if(n>=3&&n<=max&&n>count(cut))cut=head;
      }
      if(cut)break;
    }
    if(!cut){const w=s.split(' ');let n=0,k=0;while(k<w.length&&(n+=/[\p{L}\d]/u.test(w[k])?1:0)<=max)k++;cut=w.slice(0,k).join(' ').replace(/[\s.:·,—–-]+$/u,'')+'…';}
    s=cut;
  }
  return {head:s||full,more:bare(s)!==bare(full)};
}
