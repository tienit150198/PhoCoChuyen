/** 🐦 A small flock now and then over the town (both maps: the 2.5D island and the classic Bản đồ phố). Cheap by
 * design: nothing runs between flights (one timer, no frame loop), a flight is three tiny SVGs moved by one
 * compositor transform (Web Animations) while their wings flap in CSS, and the canvas under them is never redrawn.
 * None with reduced motion, a hidden tab, or while `on()` says the town is not what the player sees. Decoration
 * only: aria-hidden, no pointer events. */
const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
const still=()=>Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion')||document.body?.classList.contains('reduce-motion');
const BIRD='<svg viewBox="0 0 20 8" width="18" height="8" aria-hidden="true"><path d="M1 6.5Q5.5 0 10 5.6Q14.5 0 19 6.5" fill="none" stroke="#4e5a52" stroke-width="1.8" stroke-linecap="round"/></svg>';
let styled=false;
function css(){
  if(styled)return;styled=true;
  const s=document.createElement('style');s.dataset.townBirds='';
  s.textContent='.town-birds{position:absolute;left:0;top:0;z-index:0;pointer-events:none;opacity:.78;will-change:transform}'+
    '.town-birds[hidden]{display:none}.town-birds svg{position:absolute;display:block;transform-origin:50% 70%;animation:town-flap .32s ease-in-out infinite alternate}'+
    '.town-birds svg:nth-child(2){animation-delay:-.12s}.town-birds svg:nth-child(3){animation-delay:-.22s}'+
    '@keyframes town-flap{from{transform:scaleY(1)}to{transform:scaleY(.35)}}'+
    '@media (prefers-reduced-motion:reduce){.town-birds{display:none}}';
  document.head.append(s);
}
/** Birds over `host` (positioned): the first flight after a short wait, then one every 40–80 s. Returns stop(). */
export function townBirds(host,on=()=>true){
  if(!host||typeof host.animate!=='function')return ()=>{};
  css();
  const flock=document.createElement('div');flock.className='town-birds';flock.hidden=true;flock.setAttribute('aria-hidden','true');
  flock.innerHTML=BIRD+BIRD+BIRD;
  const spots=[[0,0],[16,7],[30,-3]];
  [...flock.children].forEach((b,i)=>{b.style.left=spots[i][0]+'px';b.style.top=spots[i][1]+'px';});
  host.append(flock);
  let timer=0,flying=null,stopped=false;
  const later=ms=>{clearTimeout(timer);if(!stopped)timer=setTimeout(fly,ms);};
  function fly(){
    if(stopped)return;
    if(!flock.isConnected||document.hidden||still()||!on()){later(20000);return;}
    const w=host.clientWidth,h=host.clientHeight;if(w<200||h<200){later(20000);return;}
    const ltr=Math.random()<.5,y0=h*(.12+Math.random()*.3),y1=y0+(Math.random()-.5)*h*.18,from=ltr?-60:w+20,to=ltr?w+20:-60;
    flock.hidden=false;
    try{
      flying=flock.animate([{transform:`translate3d(${from}px,${y0}px,0) scaleX(${ltr?1:-1})`},{transform:`translate3d(${to}px,${y1}px,0) scaleX(${ltr?1:-1})`}],
        {duration:Math.max(6000,w*13),easing:'linear'});
      flying.onfinish=()=>{flock.hidden=true;flying=null;later(40000+Math.random()*40000);};
    }catch{flock.hidden=true;stopped=true;}
  }
  later(6000+Math.random()*6000);
  return ()=>{stopped=true;clearTimeout(timer);flying?.cancel();flock.remove();};
}
