// 🎣 The reel (public/js/v4/fish-reel.js) played by two bots against the fights of game/fishing_content.fight_of
// (tests/test_fishing_ev.py Reel feeds them on stdin: [{r, h: {secs, pull, dart, green}}, …]) and prints the share
// each bot lands per rarity: {casual: [7 rates], decent: [7 rates], fastest: the shortest landing ÷ the fight's secs}.
//   casual: never looks at the needle: holds 1–3,5 s, lets go 0,3–1,5 s, over and over;
//   decent: watches the needle (0,2 s late) and holds while it is below the green's middle;
//   lazy (2.6.5.2, a phone player who hardly looks): holds 3–7 s, lets go 2–5 s;
//   hold: never lets go (ignores the flashing red): the one way left to lose a strong fish.
import {readFileSync} from 'node:fs';
import {reelStart,reelStep,MID} from '../public/js/v4/fish-reel.js';

const cases=JSON.parse(readFileSync(0,'utf8'));
const N=Number(process.env.REEL_N)||400,DT=1/60;
function rng(seed){let a=seed>>>0;return()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};}

function play(h,bot,rnd){
  const f=reelStart(h,true,rnd),seen=[];let held=false,left=0;
  play.t=0;
  for(let i=0;i<60*120;i++){
    seen.push(f.tau);
    if(bot==='casual'||bot==='lazy'){
      if(left<=0){held=!held;left=bot==='lazy'?(held?3+rnd()*4:2+rnd()*3):(held?1+rnd()*2.5:.3+rnd()*1.2);}
      left-=DT;f.hold=held;
    }else if(bot==='hold')f.hold=true;
    else{
      const late=seen[Math.max(0,seen.length-1-12)];f.hold=late<MID;
    }
    const {end}=reelStep(f,DT,rnd);
    if(end){play.t=f.t/f.secs;return end==='ok';}
  }
  return false;
}

const out={casual:[],decent:[],lazy:[],hold:[],fastest:Infinity};
for(const bot of ['casual','decent','lazy','hold']){
  const won=Array(7).fill(0),all=Array(7).fill(0);let seed=1;
  for(const c of cases)for(let k=0;k<N;k++){all[c.r]++;if(play(c.h,bot,rng(seed++))){won[c.r]++;out.fastest=Math.min(out.fastest,play.t);}}
  out[bot]=won.map((w,r)=>all[r]?w/all[r]:null);
}
console.log(JSON.stringify(out));
