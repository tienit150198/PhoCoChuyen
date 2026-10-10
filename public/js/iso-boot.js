/** 🏝️ Giao diện 2.5D: loaded only when the account enables it (interface-mode.js).
 * The classic game never imports this module, so its first screen carries none of it (docs/PHASER_25D.md).
 *
 * Two steps, so the 2.5D first screen is not waiting on Phaser:
 * - this module's static graph (the HUD shell, the joystick, the town presence, the cozy portraits; ~20 KB gz) and its
 *   two stylesheets come with the first frame, after bootstrap resolves the account's preference;
 * - loadWorld() imports the Phaser bundle (isometric/phaser-world.js, ~360 KB gz) once the first frame is out.
 *   app.js's stand-in world takes the calls meanwhile and hands them over (adopt). */
import {bootIsometricShell,updateIsometricShell,isometricAction} from './isometric-shell.js';
import {bootIsometricMovement} from './isometric-movement.js';
import {bootIsometricTown} from './isometric-town.js';
import {bootCozyPortraits} from './isometric/portraits.js';
import {cozyPortraits} from './v4/look.js';
import {homeListFirst,onIsoLand} from './v4/journey.js';
import {attachGuide,landNewPlayer} from './iso-guide.js';
import {attachTreasure} from './isometric-treasure.js';

export {updateIsometricShell,isometricAction};

/** The HUD, the joystick, the shared town and the portraits. Once, after the app's state has loaded. */
let up=false;
export const booted=()=>up;
export function bootShell(env){
  if(up)return;up=true;
  cozyPortraits(true);   // v4/look.js: portraits drawn from now on carry the chibi marker
  homeListFirst();   // v4/journey.js: the career list, not a second (2D) town map, unless this device chose the map
  onIsoLand(landNewPlayer);   // a brand-new player lands on the island after the intro (iso-guide.js)
  bootIsometricShell(env);bootIsometricMovement(env);bootIsometricTown(env);bootCozyPortraits();
}

/** After the first frame (app.js): the Phaser bundle into app.js's stand-in world. A
 * bundle that fails to load is tried again (3 times, waiting longer each time), then the player gets a retry button. */
export function start({env,world,interact,renderMain}){
  const canvas=document.getElementById('world'),stage=document.getElementById('stage')||document.body;
  const note=document.createElement('div');note.className='iso-loading';note.setAttribute('role','status');note.textContent='Đang dựng phố…';stage.append(note);
  if(!up){bootShell(env);renderMain();}
  const attempt=async n=>{
    let real=null,timeout=null;
    try{
      const PhaserWorld=await loadWorld();real=new PhaserWorld(canvas,interact);
      // Construction alone does not mean the scene can paint. Keep the proxy and
      // visible loading state until boot, including a bounded wait for engine errors.
      await Promise.race([real.ready,new Promise((_,reject)=>{
        timeout=setTimeout(()=>reject(new Error('Scene initialization timed out')),20000);
      })]);
      clearTimeout(timeout);timeout=null;
      world.adopt(real);renderMain();attachGuide(real,env);attachTreasure(real,env);note.remove();
    }
    catch(e){
      if(timeout!==null)clearTimeout(timeout);
      real?.destroy();
      console.warn('2.5D:',e);
      if(n<3){setTimeout(()=>attempt(n+1),1500*2**n);return;}
      note.classList.add('is-error');note.innerHTML='Chưa tải được phố. <button type="button" class="btn primary small">Thử lại</button>';
      note.querySelector('button').addEventListener('click',()=>location.reload());
    }
  };
  requestAnimationFrame(()=>setTimeout(()=>attempt(0),0));
}

/** The Phaser world class (the big bundle). */
export async function loadWorld(){
  const {PhaserWorld}=await import('./isometric/phaser-world.js');
  return PhaserWorld;
}

/** Leisure places (Câu cá, Chèo thuyền, Bơi): the pixel place and its art, on the first visit. */
export async function openLeisure(kind,env){
  if(env.api?.state?.jail){await env.act('jail');return;}
  const [{openPixelPlace},{loadLeisureArt}]=await Promise.all([import('./pixel/places.js'),import('./isometric/leisure-art.js')]);
  const leisureArt=await loadLeisureArt(kind);
  if(env.api?.state?.jail){await env.act('jail');return;}
  env.closeSheet();openPixelPlace(kind,{...env,leisureArt});
}
