/* A Telex keyboard turns some code letters into accents: "A"+"R" becomes "Ả", "D"+"D" becomes "Đ", a lone "W"
 * becomes "Ư". Stripping the accented letter lost the R (players could not type a code with R, S, F, X, J or W),
 * so each mark goes back to the key that made it before the filter. */
const MARK_KEY={'́':'S','̀':'F','̉':'R','̃':'X','̣':'J','̆':'W','̛':'W'};
/** Telex text back to the keys typed, then the code alphabet (A–Z, 0–9), 4 characters at most. */
export function codeKeys(text){
  let out='';
  for(const ch of String(text||'').toUpperCase()){
    if(ch==='Đ'){out+='DD';continue;}
    if(ch==='Ư'){out+='W';continue;}   // a lone W in Telex ("UW" gives the same letter; a code rarely has U then W)
    const [base,...marks]=ch.normalize('NFD');
    out+=base;
    for(const m of marks)out+=m==='̂'?base:(MARK_KEY[m]||'');   // â ê ô: the vowel typed twice
  }
  return out.replace(/[^A-Z0-9]/g,'').slice(0,4);
}
/** A room code is ASCII, but an IME owns the field until its composition finishes. */
export function bindRoomCode(box,join){
  if(box._pbCode)return;box._pbCode=true;
  let composing=false;
  const clean=()=>{const v=codeKeys(box.value);if(v!==box.value)box.value=v;};
  box.addEventListener('compositionstart',()=>{composing=true;});
  box.addEventListener('compositionend',()=>{composing=false;clean();});
  box.addEventListener('input',e=>{if(!composing&&!e.isComposing)clean();});
  box.addEventListener('keydown',e=>{if(e.key==='Enter'&&!composing&&!e.isComposing&&e.keyCode!==229){e.preventDefault();join();}});
}
