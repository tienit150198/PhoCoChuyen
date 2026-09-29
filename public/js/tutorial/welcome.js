/** Welcome card for a brand-new player: one friendly picture, three short
 * lines, "start the 1-minute tour" or "explore on my own". */
import {streetArt} from './art.js';

export function showWelcome({onStart,onExplore}){
  let d=document.getElementById('tutWelcome');
  if(!d){
    d=document.createElement('dialog');d.id='tutWelcome';d.className='tut-welcome';d.setAttribute('aria-labelledby','tutWelcomeTitle');
    document.body.append(d);
  }
  d.innerHTML=`<div class="tut-wel">${streetArt()}<span class="eyebrow">Phố Có Chuyện</span><h2 id="tutWelcomeTitle">Chào bạn mới! 👋</h2>`+
    `<ul class="tut-wel-list"><li><span aria-hidden="true">🏘️</span>Một khu phố nhỏ</li><li><span aria-hidden="true">🧋</span>Thử nhiều nghề</li><li><span aria-hidden="true">👛</span>Kiếm xu, lên cấp</li></ul>`+
    `<button type="button" class="btn primary big full" data-tut-w="start">▶ Bắt đầu hướng dẫn (1 phút)</button>`+
    `<button type="button" class="btn ghost full" data-tut-w="explore">Tự khám phá</button></div>`;
  let done=false;
  const finish=fn=>{if(done)return;done=true;if(d.open)d.close();fn?.();};
  d.onclick=e=>{const b=e.target.closest('[data-tut-w]');if(!b)return;finish(b.dataset.tutW==='start'?onStart:onExplore);};
  d.oncancel=e=>{e.preventDefault();finish(onExplore);};
  if(!d.open)d.showModal();
  d.tabIndex=-1;d.focus({preventScroll:true});   // no focus ring on the first paint (like the sheets)
}
