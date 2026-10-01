/** The first minutes of a brand-new player: the small facts the onboarding keys on (no markup here).
 * Everything is read from the save, so a player past the first life day (day 2+) sees the game exactly as
 * before, and a sandbox save (no story) never matches. */

/** The recommended first workplace ("Trà sữa · hợp người mới"). */
export const FIRST_JOB='milk_tea';
/** Marker the server adds to settings.notesSeen when a brand-new save is named (game/journey.py ONBOARD_MARK):
 * the contextual hints are for these saves only. */
export const MARK='onb1';

/** Story mode, still in the first life day (the intro, the first workplace, the first shift). */
export const firstDay=s=>!!(s?.journey?.story&&(Number(s.journey.life_day)||1)<=1);
/** Customers served so far (every workplace whose metrics are in the view: the current one always is). */
export const servedAll=s=>Object.values(s?.careers||{}).reduce((n,c)=>n+(Number(c?.metrics?.served)||0),0);
/** The first 3 customers: nothing modal pops up over the game. */
export const quiet=s=>firstDay(s)&&servedAll(s)<3;
/** Named with this onboarding (see MARK). */
export const markedNew=s=>String(s?.settings?.notesSeen||'').split(',').includes(MARK);
/** The first workplace on the first day: its shop opens straight into the first customer (no "Chuẩn bị" sheet). */
export function quickOpen(s,cid){
  const c=s?.careers?.[cid];
  if(!firstDay(s)||!c||c.open||Number(c.day)!==1||c.shift_summary)return false;
  return Object.entries(s.careers).every(([id,x])=>id===cid||!x?.started);
}
