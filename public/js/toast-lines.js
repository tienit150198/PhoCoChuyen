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
