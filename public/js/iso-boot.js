/** 🏝️ Giao diện 2.5D: everything the isometric client needs, loaded only for a player who has it on (app.js UI25D).
 * The classic game never imports this module, so its first screen carries none of it (docs/PHASER_25D.md).
 *
 * Two steps, so the 2.5D first screen is not waiting on Phaser:
 * - this module's static graph (the HUD shell, the joystick, the town presence, the cozy portraits; ~20 KB gz) and its
 *   two stylesheets come with the first frame: app.js starts the import while /api/bootstrap is still on the wire;
 * - loadWorld() imports the Phaser bundle (isometric/phaser-world.js, ~360 KB gz) once the first frame is out.
 *   app.js's stand-in world takes the calls meanwhile and hands them over (adopt). */
import {bootIsometricShell,updateIsometricShell,isometricAction} from './isometric-shell.js';
import {bootIsometricMovement} from './isometric-movement.js';
import {bootIsometricTown} from './isometric-town.js';
import {bootCozyPortraits} from './isometric/portraits.js';
import {cozyPortraits} from './v4/look.js';
import {homeListFirst} from './v4/journey.js';

export {updateIsometricShell,isometricAction};

/** The HUD, the joystick, the shared town and the portraits. Once, after the app's state has loaded. */
let up=false;
export const booted=()=>up;
export function bootShell(env){
  if(up)return;up=true;
  cozyPortraits(true);   // v4/look.js: portraits drawn from now on carry the chibi marker
  homeListFirst();   // v4/journey.js: the career list, not a second (2D) town map, unless this device chose the map
  bootIsometricShell(env);bootIsometricMovement(env);bootIsometricTown(env);bootCozyPortraits();
}

/** After the first frame (app.js): the HUD if it was not in time, then the Phaser bundle into app.js's stand-in world.
 * A bundle that fails to load or start: app.js's fail (back to the classic UI). Its stylesheets come with this module
 * (app.js lazy(..., {css})). */
export function start({env,world,interact,renderMain,fail}){
  const canvas=document.getElementById('world'),stage=document.getElementById('stage')||document.body;
  const note=document.createElement('div');note.className='iso-loading';note.setAttribute('role','status');note.textContent='Đang dựng phố…';stage.append(note);
  if(!up){bootShell(env);renderMain();}
  requestAnimationFrame(()=>setTimeout(async()=>{
    try{const PhaserWorld=await loadWorld();world.adopt(new PhaserWorld(canvas,interact));renderMain();}
    catch(e){fail(e);}finally{note.remove();}
  },0));
}

/** The Phaser world class (the big bundle). */
export async function loadWorld(){
  const {PhaserWorld}=await import('./isometric/phaser-world.js');
  return PhaserWorld;
}

/** Leisure places (Câu cá, Chèo thuyền, Bơi): the pixel place and its art, on the first visit. */
export async function openLeisure(kind,env){
  const [{openPixelPlace},{loadLeisureArt}]=await Promise.all([import('./pixel/places.js'),import('./isometric/leisure-art.js')]);
  const leisureArt=await loadLeisureArt(kind);
  env.closeSheet();openPixelPlace(kind,{...env,leisureArt});
}
