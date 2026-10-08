// 🎙️ Voice and music, before (1.9.19) and after (08/10): a listener's page in simulated time, 1 s sync ticks.
// Imported by tests/karaoke_sync.mjs (which asserts on it); `node tests/karaoke_sim.mjs` prints the table.
//
// The world: the server clock is exact; the song started at 0. The singer's video runs `drift` s off the shared
// clock; they hear it `ol` s late (output latency: Bluetooth earphones ~0.18 s) and sing to what they hear; their
// voice reaches the listener `L` s later (capture, network, the jitter buffer). So the voice heard at T matches the
// music position V(T) = S(T − L) − ol. The listener's page knows L only as getStats says (`lagErr` off), reads its
// YouTube time with ±20 ms of noise, and a seek re-buffers 0.2–0.9 s (aimed ahead by the last one's time, like the
// page). The ear hears E(T) = P(T) − V(T − hold): positive = the voice late against the music.
//
// "before": 1.9.19's sync(): the video aimed at vt − lag, nudged by a rate only from YouTube's list (which has
// nothing between 0.75 and 1.25, measured 08/10: so no nudge), a seek past 0.6 s (2 a song, 10 s apart), and no
// singer latency. "after": mixNow/voiceMove with the real karaoke-mic.js functions (followTarget, voiceLag with the
// singer's `ol`, mixPlan, musicMove) and the voice's hold (holder(): glide 3 %/s, a jump past 0.25 s).
import {followTarget,voiceLag,mixPlan,musicMove,MIX} from '../public/js/v4/karaoke-mic.js';

const YT_RATES=[0.25,0.5,0.75,1,1.25,1.5,1.75,2];
function rng(seed){let s=seed>>>0;return ()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296;};}

/** One run: returns the mean and the 95th percentile of |E| (seconds) from `from` s to the end. */
export function run({algo,L=.35,ol=0,drift=0,lagErr=.02,olSeen=true,rates='youtube',secs=90,from=20,seed=7}){
  const rnd=rng(seed),dt=.02;
  const Lf=typeof L==='function'?L:()=>L;              // the voice's delay (it may change: the jitter buffer grows)
  const S=T=>T+drift;                                   // the singer's video
  const V=T=>S(T-Lf(T))-ol;                             // the music position the voice heard at T matches
  let P=0,rate=1,buf=0,bufTo=0,lastSeekT=.6,seekAt=-1e9,seeks=0,far=0,hold=0,holdTo=0,rateOk=null,rateAt=0,est=Lf(0)+lagErr;
  const errs=[],stEst=()=>({jb:est-.04-.06,rtt:.06});   // voiceLag(stEst(), .06) = est: getStats, smoothed every 2 s
  const honour=r=>rates==='any'?r:(YT_RATES.includes(r)?r:1);
  for(let i=0,next=1;i*dt<secs;i++){
    const T=i*dt;
    if(T>=from&&buf<=0)errs.push(Math.abs(P-V(T-(algo==='before'?0:hold))));
    if(T>=next){
      next+=1;
      if(next%2===0)est+=(Lf(T)+lagErr-est)*.3;
      if(buf<=0){
        const cur=P+(rnd()-.5)*.04,st=T-.4,vt=S(st);   // the singer's last kara_vt, 0.4 s old
        const v={vt,at:st,r:1,got:0};
        if(algo==='before'){
          const lag=voiceLag(stEst(),.06);
          const t=followTarget({clock:T,vt:v,now:T,age:.4,lag,voice:true}).t,off=cur-t;
          if(Math.abs(off)>(seeks<2?.6:2)&&T*1000-seekAt>=10000){seekAt=T*1000;seeks++;const b=.2+rnd()*.7;buf=b;bufTo=t+lastSeekT;lastSeekT=Math.min(1.5,b);rate=1;}
          else{far=Math.abs(off)>.12?far+1:0;const want=far>=2?(off<0?YT_RATES.filter(x=>x>1&&x<=1.05)[0]:YT_RATES.filter(x=>x<1&&x>=.95)[0])||1:1;rate=want;}
        }else{
          if(rate!==1&&rateAt&&T-rateAt>=1.5&&rateOk===null){rateOk=honour(rate)===rate;if(!rateOk)rate=1;}
          const lag=voiceLag(stEst(),.06,olSeen?ol:0);
          const t=followTarget({clock:T,vt:v,now:T,age:.4,lag,voice:true}).t;
          const plan=mixPlan({cur,voices:[{id:'',t}],lead:['']});
          const d=plan.d[''];if(Math.abs(d-holdTo)>=MIX.dead){if(Math.abs(d-hold)>MIX.jump)hold=d;holdTo=d;}
          const off=cur-plan.aim,mv=musicMove(off),gap=T*1000-seekAt;
          if(mv==='seek'&&((seeks<3&&gap>=6000)||(Math.abs(off)>2&&gap>=10000))){seekAt=T*1000;seeks++;const b=.2+rnd()*.7;buf=b;bufTo=plan.aim+lastSeekT;lastSeekT=Math.min(1.5,b);rate=1;}
          else{far=mv!=='ok'?far+1:0;const want=(far>=2||(rate!==1&&Math.abs(off)>.05))&&off&&rateOk!==false?(off<0?1.05:.95):1;if(want!==rate){rate=want;rateAt=T;}}
        }
      }
    }
    if(buf>0){buf-=dt;if(buf<=0)P=bufTo;}else P+=dt*honour(rate);   // the player, to T + dt
    if(hold!==holdTo){const step=MIX.glide*dt;hold=Math.abs(holdTo-hold)<=step?holdTo:hold+Math.sign(holdTo-hold)*step;}   // the hold glides (holder)
  }
  errs.sort((a,b)=>a-b);
  return {mean:errs.reduce((a,b)=>a+b,0)/errs.length,p95:errs[Math.floor(errs.length*.95)]};
}

export const SCENARIOS=[
  ['TCP voice 0.35 s, wired', {L:.35}],
  ['TCP voice 0.35 s, singer on Bluetooth (0.18 s)', {L:.35,ol:.18}],
  ['voice 0.5 s, singer video +0.3 s off the clock', {L:.5,drift:.3}],
  ['voice 0.25 s, singer video −0.4 s, lag misread +60 ms', {L:.25,drift:-.4,lagErr:.06}],
  ['voice 0.3 s, growing to 0.6 s at 40 s (TCP congestion)', {L:T=>T<40?.3:.6}],
];

if(process.argv[1]?.endsWith('karaoke_sim.mjs')){   // run by itself: the table
  const ms=x=>`${Math.round(x*1000)} ms`;
  for(const [name,o] of SCENARIOS){
    const b=run({algo:'before',...o}),a=run({algo:'after',...o}),r=run({algo:'after',rates:'any',...o});
    console.log(`${name}\n  before: mean ${ms(b.mean)}, p95 ${ms(b.p95)}   after: mean ${ms(a.mean)}, p95 ${ms(a.p95)}   after (player takes 1.05): mean ${ms(r.mean)}, p95 ${ms(r.p95)}`);
  }
}
