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
 * another save never spreads to the account in play (nor does the coach's "cn1": it counts once the server has it). */
const MARK='onb1';
export function notesSeen(api){
  const server=ids(api?.state?.settings?.notesSeen);
  return new Set([...ids(get(KEY.notes)).filter(x=>x!==MARK&&x!==COACH_NEW||server.includes(x)),...server]);
}
export function markNoteSeen(env,id){
  const all=notesSeen(env?.api);if(all.has(id)&&ids(env?.api?.state?.settings?.notesSeen).includes(id))return;
  all.add(id);save(env,all);
}
/** The list written back: at most 12 ids; the packed per-workplace ids ("gd-", and the coach's "co-"/"cd-") and the
 * coach's "cn1" are never the ones pushed out (each packed kind merges into ONE id: two devices add up). */
function save(env,all){
  const keep=[...PACKED.map(p=>bitsId(bitsFrom(all,p),p)).filter(Boolean),...STICKY.filter(x=>all.has(x))];
  const rest=[...all].filter(x=>!PACKED.some(p=>x.startsWith(p))&&!STICKY.includes(x)).slice(-(12-keep.length));
  const list=[...rest,...keep].join(',');
  set(KEY.notes,list);sync(env,{notesSeen:list});
}

/* Guides seen, per workplace: one small "Xem hướng dẫn / Bỏ qua" card the first time at a place (announce.js).
 * notesSeen holds at most 12 short ids ([a-z0-9-], ≤ 24 chars, checked by the server), too few for one id per
 * workplace, so the places are bits of ONE id, "gd-" + base 32: bit i = GUIDE_BITS[i]. Append only: a new
 * workplace goes at the end, never in between (tests/test_guide_prompt.py checks every workplace is listed). */
export const GUIDE_BITS=['mother_baby','pharmacy','accounting','customer_care','teacher','tour_guide','milk_tea','restaurant',
  'cafe_bakery','florist','grocery','repair','farm','delivery','homestay','pet_care','salon','corp_accounting','tax_payroll',
  'group_accounting','clothing','pet_shop','tra_da','fruit','garbage','drain','pilot','flight_attendant','homemaker',
  'hr_admin','secretary','it_helpdesk','ice_cream','nail','pagoda','pho','com','photobooth','giupviec','naucom','babysitter','library','oil','railway','nurse','lighthouse','rescue','lifeguard','police','zpop',
  'art_studio','lawyer','laundry','post_office','customs','hotel','banquet','reception','teller','restore','research','radio','moto','vet','kol','singer','actor','tuning','jewelry','car_dealer'];
const B32='0123456789abcdefghijklmnopqrstuv',GD='gd-';
/** 🧭 The first-day coach (coach.js), per workplace with the same bits: "co-" offered and answered (it ran, was turned
 * off, or its "Có hướng dẫn mới" chip was closed), "cd-" finished to the end. "cn1": a save that started with the coach
 * (every workplace's first day starts it by itself; older saves get the chip instead). All three ride in notesSeen,
 * which every release since 0.x accepts: nothing new in the save, a rollback only forgets nothing. */
const CO='co-',CD='cd-';export const COACH_NEW='cn1';
/** First-use hints of the town's player services (tips.js FEATS: 🛎️ Phố dịch vụ, 🏥 phòng sinh, 📸 tiệm ảnh, 💒 dịch vụ
 * cưới, 🎪 Hội chợ việc làm), packed the same way in ONE "fh-" id. Append only, like GUIDE_BITS. */
export const FEATURE_BITS=['svc','svc-mine','birth','birth-room','photo','studio','wed','wed-work','fair','booth'];
const FH='fh-';
const PACKED=[GD,CO,CD,FH],STICKY=[COACH_NEW];
const BITS={[GD]:GUIDE_BITS,[CO]:GUIDE_BITS,[CD]:GUIDE_BITS,[FH]:FEATURE_BITS};
/** The workplaces (or hints, for "fh-") packed in every `prefix` id of a set of note ids. */
function bitsFrom(seen,prefix){
  const out=new Set(),list=BITS[prefix];
  for(const id of seen)if(id.startsWith(prefix))[...id.slice(prefix.length)].forEach((ch,i)=>{const v=B32.indexOf(ch);for(let k=0;k<5;k++)if(v>=0&&v>>k&1&&list[i*5+k])out.add(list[i*5+k]);});
  return out;
}
/** The one `prefix` id for a set of workplaces (or hints) ('' when none). */
function bitsId(cids,prefix){
  const chars=[];BITS[prefix].forEach((cid,b)=>{if(cids.has(cid))chars[b/5|0]=(chars[b/5|0]||0)|1<<b%5;});
  const s=Array.from({length:chars.length},(_,i)=>B32[chars[i]||0]).join('').replace(/0+$/,'');
  return s?prefix+s:'';
}
/** The workplaces whose guide card was answered, from a set of note ids (every "gd-" id counts: two devices merge). */
export const guidesFrom=seen=>bitsFrom(seen,GD);
/** The one id for a set of workplaces ('' when none). */
export const guidesId=cids=>bitsId(cids,GD);
export const guideSeen=(api,cid)=>guidesFrom(notesSeen(api)).has(cid);
export function markGuideSeen(env,cid){
  const all=notesSeen(env?.api),done=guidesFrom(all);if(done.has(cid)&&ids(env?.api?.state?.settings?.notesSeen).some(x=>x.startsWith(GD)))return;
  all.add(guidesId(new Set([cid])));save(env,all);
}
/** Coach: {offered, done} sets of workplaces, and whether this save began with the coach. */
export function coachSeen(api){const all=notesSeen(api);return {offered:bitsFrom(all,CO),done:bitsFrom(all,CD),native:all.has(COACH_NEW)};}
/** Remember the coach at a workplace: `done` = finished to the end (also counts as offered). */
export function markCoach(env,cid,{done=false}={}){
  const all=notesSeen(env?.api),server=ids(env?.api?.state?.settings?.notesSeen);
  const has=(p,set)=>set.has(cid)&&server.some(x=>x.startsWith(p));
  if(has(CO,bitsFrom(all,CO))&&(!done||has(CD,bitsFrom(all,CD))))return;
  all.add(bitsId(new Set([cid]),CO));if(done)all.add(bitsId(new Set([cid]),CD));
  save(env,all);
}
export const coachIds={bitsFrom,bitsId,CO,CD};
/** First-use hints of the player services already shown (tips.js FEATS). */
export const featuresSeen=api=>bitsFrom(notesSeen(api),FH);
export function markFeature(env,id){
  const all=notesSeen(env?.api);if(bitsFrom(all,FH).has(id)&&ids(env?.api?.state?.settings?.notesSeen).some(x=>x.startsWith(FH)))return;
  all.add(bitsId(new Set([id]),FH));save(env,all);
}
