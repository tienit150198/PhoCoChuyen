/** 🎁 Quà mừng: a centred card that offers a one-off gift (game/journey.py GIFTS) to every save
 * that has not claimed it yet, until its deadline. The server decides: state.journey.gift is the
 * offer ({id, amount, label, until, until_text}) or null (claimed, expired, or no gift running).
 *
 * - It waits like "Có gì mới" (./whatsnew.js blocker(): loading, naming the character, a hidden
 *   tab, the tutorial) and opens only after that card is read: never two cards at once.
 * - "Nhận …" sends jr_gift_claim; the server adds the coins to the wallet and says so (toast).
 * - "Để sau" (or Esc) closes it for this visit only: it comes back on the next load until claimed.
 * app.js loads this module lazily after the first frame (giftBoot), next to whatsnew.js. */
import {blocker,pending,loadCss} from './whatsnew.js';
import {icon,escapeHTML as esc} from '../icons.js';

let E=null,timer=0,calmTicks=0,dlg=null,openedAt=0,later=false,busy=false,back=null;

/** The gift this save can claim now (server-side), or null. */
export const offer=state=>{const g=state?.journey?.gift;return g&&typeof g.id==='string'&&Number(g.amount)>0?g:null;};

/** Why the card has to wait right now ('' = it may open): the "Có gì mới" rules, then that card
 * itself (open, or still due to open by itself), then a question already on screen. */
export function waitReason(env=E,doc=document,notesPending=pending){
  const why=blocker(env,doc);if(why)return why;
  if(notesPending(env?.api?.state))return 'whatsnew';
  if(doc.getElementById('confirmDialog')?.open)return 'question';
  return '';
}

function html(g){
  const amount=Number(g.amount)||0;
  return `<header class="wn-head"><span class="wn-spark" aria-hidden="true">🎁</span><div class="grow"><h2 id="giftTitle">Quà mừng mở server</h2>`+
    `<p class="wn-meta" id="giftMeta">Nhận trước hết ngày ${esc(g.until_text||'')}</p></div>`+
    `<button type="button" class="icon-btn wn-x" data-gift="later" aria-label="Để sau">${icon('x',22)}</button></header>`+
    `<div class="gift-body"><p class="gift-text">Cảm ơn bạn đã đến Phố Có Chuyện tuần đầu! Tặng bạn ${amount} xu làm vốn. Quà có đến hết ngày ${esc(g.until_text||'')}.</p>`+
    `<p class="gift-coin"><span aria-hidden="true">🪙</span><b>+${amount} xu</b></p></div>`+
    `<footer class="wn-foot gift-foot"><button type="button" class="btn primary big full" data-gift="claim">Nhận ${amount} xu</button>`+
    `<button type="button" class="btn ghost full" data-gift="later">Để sau</button></footer>`;
}

function build(){
  if(dlg)return dlg;
  dlg=document.createElement('dialog');dlg.id='giftDialog';dlg.className='wn-dialog gift-dialog';
  dlg.setAttribute('aria-modal','true');dlg.setAttribute('aria-labelledby','giftTitle');dlg.setAttribute('aria-describedby','giftMeta');
  dlg.innerHTML='<div class="wn-card"></div>';
  document.body.append(dlg);
  dlg.addEventListener('click',onClick);
  dlg.addEventListener('cancel',e=>{e.preventDefault();if(!busy)close();});   // Esc = "Để sau"
  dlg.addEventListener('keydown',e=>{
    if(e.key!=='Tab')return;
    const f=[...dlg.querySelectorAll('button')].filter(b=>!b.disabled&&b.offsetParent!==null);if(!f.length){e.preventDefault();return;}
    const first=f[0],last=f[f.length-1],at=document.activeElement;
    if(e.shiftKey&&(at===first||at===dlg||!dlg.contains(at))){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&(at===last||!dlg.contains(at))){e.preventDefault();first.focus();}
  });
  return dlg;
}

function onClick(e){
  const b=e.target.closest('button');if(!b||!dlg.contains(b))return;
  // A tap already on its way when the card popped up must not close it unread.
  if(performance.now()-openedAt<450){e.preventDefault();return;}
  if(b.dataset.gift==='later'&&!busy)close();
  else if(b.dataset.gift==='claim')claim(b);
}

async function claim(button){
  const g=offer(E?.api?.state);if(!g||busy){close();return;}
  busy=true;button.disabled=true;const label=button.textContent;button.textContent='Đang nhận…';
  let r=null;
  try{r=await E.cmd('jr_gift_claim',{id:g.id},{career:E.api.state.current||E.api.state.focus});}
  finally{busy=false;}
  if(r){close();return;}
  // Refused (already claimed in another tab, expired) or no connection: ask the server what is left.
  try{await E.api.refresh();}catch{/* offline: the button stays for another try */}
  if(!offer(E.api.state)){close();return;}
  if(button.isConnected){button.disabled=false;button.textContent=label;}
}

export async function openGift(env=E){
  E=env||E;const g=offer(E?.api?.state);if(!g)return;
  await loadCss();
  build();back=document.activeElement;
  dlg.querySelector('.wn-card').innerHTML=html(g);
  if(!dlg.open)dlg.showModal();
  openedAt=performance.now();
  dlg.tabIndex=-1;dlg.focus({preventScroll:true});
}
function close(){
  later=true;stopWatch();
  if(!dlg?.open)return;
  dlg.close();
  if(back?.isConnected&&typeof back.focus==='function')back.focus({preventScroll:true});
  back=null;
}

function check(){
  if(later||!offer(E?.api?.state)){stopWatch();return;}
  // Two calm checks in a row (about a second): never in the gap between two cards.
  if(waitReason()){calmTicks=0;return;}
  if(++calmTicks<2)return;
  stopWatch();openGift(E);
}
function stopWatch(){clearInterval(timer);timer=0;}

/** Called once by app.js after the game is on screen. */
export function giftBoot(env){
  try{
    E=env;
    if(offer(env.api?.state)){stopWatch();calmTicks=0;timer=setInterval(check,700);}
  }catch(error){console.error('gift:',error);}   // never in the way of the game
}
