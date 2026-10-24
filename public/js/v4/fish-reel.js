/** 🎣 The reel's physics (v4/fishing.js plays it, tests/fishing-reel.mjs measures it with bots against
 * game/fishing_content.fight_of). Owner 24/10 "khó ở chỗ giật màu xanh ấy, màu xanh rất khó để canh được khoảng đó lúc
 * kéo lên": a wide green zone, a slow and smooth needle that drifts back toward the green by itself (ASSIST) when it
 * leaves it, progress in the yellow band too (slower), and the red only snaps the line after RED_MAX seconds in it
 * (the bar flashes all along). Holding reels in and lifts the needle; letting go eases it down. A casual player who
 * just holds and lets go when the bar flashes red lands nearly every common fish and most 🔴 Cổ đại ones.
 * 2.6.5.2 (owner 25/10 "thanh kéo cá fix xong chưa"; a phone player holding 3–7 s, letting go 2–5 s without looking
 * landed 13 % of 🔴 Cổ đại before, 75 % now): a wider green (GREEN_ADD, GREEN_FLOOR), a slower, smoother needle, softer
 * and rarer darts, longer in the red (RED_MAX) or slack (SLACK_MAX) before the fish is lost, little lost while letting
 * go. Only never letting go (ignoring the flashing red) still loses a strong fish (tests/fishing-reel.mjs `hold`).
 *
 * Pure: no DOM, no clock. `rnd` is Math.random (or a seeded one in the test). The fated snap of a fish too heavy for
 * the line is the server's (`snap_at`, seconds into the fight). */
export const MID=.55,RED=.9,SLACK=.1,RED_MAX=3.2,SLACK_MAX=4.5,ASSIST=.75;
/** 2.6.5.2 (owner 25/10 "thanh kéo cá fix xong chưa"): the green the player sees and plays is wider than the server's
 * (GREEN_ADD more, never under GREEN_FLOOR: about 3/5 of the bar for a common fish, over 2/5 for a 🔴 Cổ đại one). */
export const GREEN_ADD=.08,GREEN_FLOOR=.42,GREEN_MAX=.66;
const clamp=(v,a,b)=>v<a?a:v>b?b:v;

/** A fight from what jr_fish_hook answered: {secs, pull, dart, green, heavy, snap_at}. */
export function reelStart(h,hold=false,rnd=Math.random){
  return {secs:Math.max(1.5,Number(h.secs)||3),pull:clamp(Number(h.pull)||.2,0,1),dart:clamp(Number(h.dart)||.1,0,1),
    green:clamp(Math.max(GREEN_FLOOR,(Number(h.green)||.45)+GREEN_ADD),GREEN_FLOOR,GREEN_MAX),heavy:!!h.heavy,snapAt:h.snap_at!=null?Number(h.snap_at):0,
    t:0,tau:.45,prog:0,red:0,slack:0,hold:!!hold,dl:0,dv:0,seed:rnd()*6,sway:0};
}

/** The green zone [from, to] of a fight. */
export const greenOf=f=>[MID-f.green/2,MID+f.green/2];

/** One step of `dt` seconds: {end: 'ok' | 'snap' | 'slack' | '', dart: the fish just darted}. */
export function reelStep(f,dt,rnd=Math.random){
  const [g0,g1]=greenOf(f);let dart=false;
  f.t+=dt;
  if(f.dl>0){f.dl-=dt;f.tau+=f.dv*dt;}
  else if(rnd()<dt*(.08+f.dart*.35)){   // a dart: a short, soft tug (mostly up, now and then a slack)
    f.dl=.2+rnd()*.15;f.dv=(.18+f.pull*.3)*(rnd()<.75?1:-.6);f.sway=rnd()<.5?-1:1;dart=true;
  }
  f.tau+=(f.hold?(.2+.1*f.pull):-(.27-.05*f.pull))*dt+f.pull*.04*Math.sin(f.t*1.3+f.seed)*dt;   // slow and smooth
  if(f.tau<g0||f.tau>g1)f.tau+=(MID-f.tau)*ASSIST*dt;   // the assist: out of the green, the needle drifts back
  f.tau=clamp(f.tau,0,1);
  if(f.hold){
    const k=f.tau>=g0&&f.tau<=g1?.85:f.tau>RED?2.5:f.tau<SLACK?3:1.5;   // green fastest, yellow slower, red / slack slowest
    f.prog+=dt/(f.secs*k);
  }else f.prog-=dt*(.005+.01*f.pull);   // letting go loses little
  f.prog=clamp(f.prog,0,1);
  f.red=f.tau>RED?f.red+dt:Math.max(0,f.red-dt*.8);
  f.slack=f.tau<SLACK&&!f.hold?f.slack+dt:Math.max(0,f.slack-dt*1.5);
  const end=f.snapAt&&f.t>=f.snapAt?'snap':f.red>RED_MAX?'snap':f.slack>SLACK_MAX?'slack':f.prog>=1?'ok':'';
  return {end,dart};
}
