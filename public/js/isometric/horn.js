/** 📯 Bấm còi (owner 17/10 "cảm giác lái"): the ride's horn in the island town. A recorded CC0 car horn
 * (public/audio/sfx/horn.mp3, licence in CREDITS.md there) for a motor, the recorded bell (ting.mp3) for a bicycle.
 * Played from the button's own tap (audio needs a gesture), fetched once, silent with the game's sound off. */
import {Sound,loadSample} from '../audio.js';

const HORN='/audio/sfx/horn.mp3',BELL='/audio/sfx/ting.mp3';
let snd=null;
/** Play the horn (`bell`: a bicycle's bell). Resolves true when it played. Never throws. */
export async function honk(settings,bell=false){
  try{
    snd??=new Sound();snd.configure(settings||{});if(!snd.enabled)return false;snd.unlock();
    const buf=await loadSample(globalThis.__mnlBoot?.asset?.(bell?BELL:HORN)||(bell?BELL:HORN));
    return Boolean(buf&&snd.sample(buf,0,bell?.35:.6));
  }catch{return false;}
}
