/** Tutorial memory: what this player has already seen (the first-run tour,
 * the announcements). Kept in localStorage (every access in try/catch, so a
 * blocked storage never breaks the game) and mirrored in the synced settings
 * (settings.tutorialDone / settings.notesSeen) so it follows the account. */
const KEY={done:'mnl.tut.done',run:'mnl.tut.run',notes:'mnl.notes.seen'};
const get=k=>{try{return localStorage.getItem(k);}catch{return null;}};
const set=(k,v)=>{try{if(v==null)localStorage.removeItem(k);else localStorage.setItem(k,v);}catch{/* storage blocked */}};
const ids=v=>String(v||'').split(',').map(x=>x.trim()).filter(x=>/^[a-z0-9-]{1,24}$/.test(x));

/** Save a settings change quietly; an older server that does not know the key only loses the sync. */
function sync(env,patch){
  if(!env?.api?.state)return;
  const st=env.api.state;env.api.command('settings',patch,st.current||st.focus).catch(()=>{});
}

export const tourDone=api=>get(KEY.done)==='1'||api?.state?.settings?.tutorialDone===true;
export function markTourDone(env){
  set(KEY.done,'1');set(KEY.run,null);
  if(env?.api?.state?.settings?.tutorialDone!==true)sync(env,{tutorialDone:true});
}
/** The step a running tour was on (so a reload can pick it up again). */
export const savedRun=()=>get(KEY.run);
export const saveRun=id=>set(KEY.run,id||null);

/** The new-player marker (v4/onboard.js MARK): only the server sets it, so a copy left in this browser by
 * another save never spreads to the account in play. */
const MARK='onb1';
export function notesSeen(api){
  const server=ids(api?.state?.settings?.notesSeen);
  return new Set([...ids(get(KEY.notes)).filter(x=>x!==MARK||server.includes(MARK)),...server]);
}
export function markNoteSeen(env,id){
  const all=notesSeen(env?.api);if(all.has(id)&&ids(env?.api?.state?.settings?.notesSeen).includes(id))return;
  all.add(id);const list=[...all].slice(-12).join(',');
  set(KEY.notes,list);sync(env,{notesSeen:list});
}
