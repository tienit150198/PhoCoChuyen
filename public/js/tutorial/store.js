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
  all.add(id);const gd=guidesId(guidesFrom(all));   // the guides-seen id is never the one pushed out
  const list=[...[...all].filter(x=>!x.startsWith('gd-')).slice(gd?-11:-12),...(gd?[gd]:[])].join(',');
  set(KEY.notes,list);sync(env,{notesSeen:list});
}

/* Guides seen, per workplace: one small "Xem hướng dẫn / Bỏ qua" card the first time at a place (announce.js).
 * notesSeen holds at most 12 short ids ([a-z0-9-], ≤ 24 chars, checked by the server), too few for one id per
 * workplace, so the places are bits of ONE id, "gd-" + base 32: bit i = GUIDE_BITS[i]. Append only: a new
 * workplace goes at the end, never in between (tests/test_guide_prompt.py checks every workplace is listed). */
export const GUIDE_BITS=['mother_baby','pharmacy','accounting','customer_care','teacher','tour_guide','milk_tea','restaurant',
  'cafe_bakery','florist','grocery','repair','farm','delivery','homestay','pet_care','salon','corp_accounting','tax_payroll',
  'group_accounting','clothing','pet_shop','tra_da','fruit','garbage','drain','pilot','flight_attendant','homemaker',
  'hr_admin','secretary','it_helpdesk','ice_cream','nail','pagoda','pho','com','photobooth','giupviec','naucom','babysitter','library','oil'];
const B32='0123456789abcdefghijklmnopqrstuv',GD='gd-';
/** The workplaces whose guide card was answered, from a set of note ids (every "gd-" id counts: two devices merge). */
export function guidesFrom(seen){
  const out=new Set();
  for(const id of seen)if(id.startsWith(GD))[...id.slice(GD.length)].forEach((ch,i)=>{const v=B32.indexOf(ch);for(let k=0;k<5;k++)if(v>=0&&v>>k&1&&GUIDE_BITS[i*5+k])out.add(GUIDE_BITS[i*5+k]);});
  return out;
}
/** The one id for a set of workplaces ('' when none). */
export function guidesId(cids){
  const chars=[];GUIDE_BITS.forEach((cid,b)=>{if(cids.has(cid))chars[b/5|0]=(chars[b/5|0]||0)|1<<b%5;});
  const s=Array.from({length:chars.length},(_,i)=>B32[chars[i]||0]).join('').replace(/0+$/,'');
  return s?GD+s:'';
}
export const guideSeen=(api,cid)=>guidesFrom(notesSeen(api)).has(cid);
export function markGuideSeen(env,cid){
  const all=notesSeen(env?.api),done=guidesFrom(all);if(done.has(cid)&&ids(env?.api?.state?.settings?.notesSeen).some(x=>x.startsWith(GD)))return;
  done.add(cid);
  const list=[...[...all].filter(x=>!x.startsWith(GD)).slice(-11),guidesId(done)].join(',');
  set(KEY.notes,list);sync(env,{notesSeen:list});
}
