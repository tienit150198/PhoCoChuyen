/** Tutorial layer: welcome card → first-run tour for brand-new players, the
 * illustrated guide, and the "something new" announcements for everyone.
 * app.js calls tutorialBoot(env) once after loading and routes the
 * `help` / `tutGuide` / `tutReplay` actions here (tutorialAction). */
import {startTour,stopTour,tourRunning} from './tour.js';
import {openGuide,closeGuide,helpButton} from './guide.js';
import {showWelcome} from './welcome.js';
import {announceBoot,quietAll} from './announce.js';
import {tourDone,savedRun,markTourDone} from './store.js';

function css(){
  if(document.querySelector('link[data-tut-css]'))return;
  const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.('/css/tutorial.css')||'/css/tutorial.css';l.dataset.tutCss='1';document.head.append(l);
}

export function tutorialBoot(env){
  try{boot(env);}catch(error){console.error('tutorial:',error);}   // never in the way of the game
}
function boot(env){
  css();
  const api=env.api,J=api.state?.journey,done=tourDone(api);
  // Brand-new story save (still in the first-day intro): welcome card, then the tour.
  if(J?.story&&!J.intro&&!done){
    quietAll(env);   // they get the tour, not the "new guide" announcement
    setTimeout(()=>showWelcome({
      onStart:()=>startTour(env),
      onExplore:()=>{markTourDone(env);env.toast('Cần giúp? Mở mục Hướng dẫn 📘','hint');},
    }),400);
  }else if(savedRun()&&!done){
    setTimeout(()=>startTour(env,{at:savedRun()}),600);   // a reload in the middle of the tour
  }
  announceBoot(env,{guide:e=>openGuide(e)});
}

export async function tutorialAction(action,data,el,env){
  switch(action){
    case'help':case'tutGuide':openGuide(env,{career:data?.career||undefined,tab:data?.tab||undefined,page:data?.page||undefined,sec:data?.sec||undefined,topic:data?.topic||undefined});return true;
    case'tutReplay':
      closeGuide();if(document.getElementById('sheet')?.open)env.closeSheet();
      if(tourRunning())stopTour('restart');
      setTimeout(()=>startTour(env),250);return true;
  }
  return false;
}

/** "?" in a work screen's header (see app.js header()). */
export const guideHelp=helpButton;

/** Cài đặt → Cách chơi. */
export const tutorialSettings=()=>`<section class="settings-block tut-settings"><h3><span aria-hidden="true">📘</span> Hướng dẫn</h3>`+
  `<div class="row wrap"><button type="button" class="btn small" data-action="tutGuide">Xem hướng dẫn</button><button type="button" class="btn small ghost" data-action="tutReplay">▶ Xem lại hướng dẫn</button></div></section>`;
