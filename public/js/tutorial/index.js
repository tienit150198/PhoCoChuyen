/** Tutorial layer: in-context tips for brand-new players (tips.js, while they play), the
 * coach-mark tour on request (Cài đặt → Hướng dẫn), the illustrated guide, and the
 * "something new" announcements for everyone.
 * app.js calls tutorialBoot(env) once after loading and routes the
 * `help` / `tutGuide` / `tutReplay` actions here (tutorialAction). */
import {startTour,stopTour,tourRunning} from './tour.js';
import {openGuide,closeGuide,helpButton} from './guide.js';
import {startTips,stopTips,tipsSaved,hintsBoot} from './tips.js';
import {announceBoot,quietAll} from './announce.js';
import {tourDone,savedRun,notesSeen,markNoteSeen} from './store.js';
import {markedNew,quiet} from '../v4/onboard.js';

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
  // Brand-new story save (still in the first-day intro): no welcome card and no pages before playing;
  // short tips show up on the controls while they play (tips.js), and pick up again after a reload.
  if(J?.story&&!J.intro&&!done||tipsSaved()&&!done&&(J?.life_day|0)<=2){
    quietAll(env);   // they get the tips, not the "new guide" announcement
    startTips(env);
  }else if(savedRun()&&!done){
    setTimeout(()=>startTour(env,{at:savedRun()}),600);   // a reload in the middle of the tour
  }
  announceBoot(env,{guide:e=>openGuide(e)});
  hintsBoot(env,{markedNew,quiet,notesSeen,markSeen:markNoteSeen});   // first-time hints (new saves only)
}

export async function tutorialAction(action,data,el,env){
  switch(action){
    case'help':case'tutGuide':openGuide(env,{career:data?.career||undefined,tab:data?.tab||undefined,page:data?.page||undefined,sec:data?.sec||undefined,topic:data?.topic||undefined});return true;
    case'tutReplay':
      closeGuide();if(document.getElementById('sheet')?.open)env.closeSheet();
      stopTips('replay');if(tourRunning())stopTour('restart');
      setTimeout(()=>startTour(env),250);return true;
  }
  return false;
}

/** "?" in a work screen's header (see app.js header()). */
export const guideHelp=helpButton;

/** Cài đặt → Cách chơi. */
export const tutorialSettings=()=>`<section class="settings-block tut-settings"><h3><span aria-hidden="true">📘</span> Hướng dẫn</h3>`+
  `<div class="row wrap"><button type="button" class="btn small" data-action="tutGuide">Xem hướng dẫn</button><button type="button" class="btn small ghost" data-action="tutReplay">▶ Xem lại hướng dẫn</button></div></section>`;
