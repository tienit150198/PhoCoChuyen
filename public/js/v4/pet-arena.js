/** 🐾 Đấu trường pet (game/pet_arena.py, pet_cup.py, pet_war.py, the engine game/pet_battle.py; owner 19/10 "thêm thi đua
 * nữa nhé, kết hợp với pet ra tranh đấu với bang nữa"). Its own dialog, opened with data-action="petArena" (data-tab:
 * fight | npc | rank | cup | war) from Tiện ích, ☰ Thêm and the pets sheet.
 * The server decides every battle (POST /api/arena/<op>, one request) and sends its whole log; this file only
 * animates it: lunges, hit flashes, damage numbers, crits, the five elements' skills, HP bars, KO, a victory pose and
 * confetti. Short (≈ 0.45 s an action, ⏩ ×2), skippable (⏭), phone first: one main button in the bottom bar.
 * ⚔️ Thách đấu bang (owner 21/10, game/bang_challenge.py): the 🛡️ tab has two sections, ⚔️ Thách đấu (any day: the bang's
 * roster and its order, challenges to answer or send, results and the town's latest matches, each a 5-duel replay) and
 * 🗓️ Bang chiến tuần (the weekly war). data-sec="tc" | "war" opens one, data-watch="<challenge id>" plays a replay.
 * 👑 Chọn đội hình (owner: "bang chủ được quyền chọn danh sách thú để xuất chiến"): Bang chủ and Phó bang open the
 * lineup editor of the weekly war (war_team: the members, each with their strongest pets; suggestion: each one's
 * strongest) and save up to 5 member + pet pairs (war_lineup); while it stands members see who chose it and cannot
 * change their own pick (war_lineup_off hands it back).
 * Styles: /css/pet-arena.css (and /css/pets.css for the pets' own motions). */
import {icon,escapeHTML as esc} from '../icons.js';
import {petSVG,petPicture,lookup,accOf,fxRef} from './pet-art.js';

// 21/10 owner: the arena is for bang members only — the town-wide weekly cup tab is gone
// 21/10 owner: "chỉ mở cho các bang hội đánh nhau thôi" — only the bang war and the practice before it
const TABS=[['war','🛡️','Bang chiến'],['npc','🎯','Luyện pet']];
const RKS=['D','C','B','A','S','SS','SSS'];
const EL={hoa:['🔥','Hỏa'],tho:['⛰️','Thổ'],thuy:['💧','Thủy'],moc:['🌿','Mộc'],kim:['🪙','Kim']};
const STEP=450;   // ms an action at ×1
const S={dlg:null,env:null,tab:'war',sub:'',busy:false,flash:null,v:null,lad:null,cup:null,war:null,friends:null,pick:[],npc:1,
  wpet:'',fight:null,fast:false,at:0,watch:0,
  // ⚔️ Thách đấu bang (game/bang_challenge.py): the 🛡️ tab's section, its view, sub-screens (find | order), the search, the pet picked
  wsec:'tc',tc:null,tcAt:0,tcsub:'',tfind:null,tq:'',tpet:'',ord:null,
  // 👑 the leaders' lineup editor (game/pet_war.py war_team / war_lineup): its view and the pairs chosen [{pid, pet}]
  wt:null,lsel:[]};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const CAT=()=>S.env?.api?.content?.journey?.pets||null;
const hm=t=>{try{return new Date(t*1000).toLocaleString('vi-VN',{weekday:'long',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Ho_Chi_Minh'});}catch{return '';}};
const clock=t=>{try{return new Date(t*1000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Ho_Chi_Minh'});}catch{return '';}};

let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/pets.css','pt-css'),link('/css/pet-arena.css','pa-css')]);

/** A fighter's picture (its look as the boards draw it). */
function pic(f,size=64,pose='sit'){
  const L=lookup(CAT(),f?.b,f?.c);if(!L)return `<span class="pa-unknown" aria-hidden="true">🐾</span>`;
  return (size>=90?petSVG:petPicture)(L.breed,L.coat,pose,accOf(CAT(),f),size,'pet-svg',fxRef(CAT(),f));
}
const elTag=e=>EL[e]?`<span class="pa-el el-${e}" title="Hệ ${EL[e][1]}">${EL[e][0]}</span>`:'';
const rk=r=>Number.isInteger(r)?`<span class="pt-rk r${r}">${RKS[r]||''}</span>`:'';

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium pa-sheet';d.setAttribute('aria-labelledby','pa-title');
  d.innerHTML='<div class="pa-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){close();return;}
    const el=e.target.closest('[data-pa]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.pa,el.dataset);
  });
  d.addEventListener('input',e=>{const t=e.target;if(t.name==='pa-tq'){S.tq=t.value;clearTimeout(S.tqT);S.tqT=setTimeout(findLoad,300);}});
  d.addEventListener('close',()=>{S.flash=null;S.sub='';S.tcsub='';S.watch++;stopFight();S.fight=null;});
  S.dlg=d;return d;
}
function close(){S.dlg?.close();}
export async function openArena(env,tab,extra={}){
  S.env=env;
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet?.();
  for(const d of document.querySelectorAll('dialog.pt-sheet[open],dialog.bg-sheet[open]'))d.close();   // from the pets or the bang sheet: one dialog at a time
  await ensureCss();
  const d=dialog();
  S.tab=TABS.some(t=>t[0]===tab)?tab:'war';S.sub='';S.tcsub='';S.flash=null;S.fight=null;
  if(extra?.sec==='tc'||extra?.sec==='war')S.wsec=extra.sec;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();
  await load();
  if(S.tab!=='fight')await loadTab();
  if(extra?.find&&S.tab==='war'&&S.wsec==='tc'&&S.tc?.mine?.officer){S.tcsub='find';S.tfind=null;render();findLoad();}   // ⚔️ Gửi thách đấu from the Bang sheet
  if(extra?.watch)await watchChallenge(String(extra.watch));
}
export async function petArenaAction(action,data,el,env){
  if(action!=='petArena')return false;
  await openArena(env,data?.tab,data||{});return true;
}

async function post(op,data={}){return S.env.api.post('/api/arena/'+op,data,20000);}
async function load(){
  try{S.v=await post('view');}catch(e){S.v=S.v||{error:e.message||'Chưa tải được.'};}
  if(S.dlg?.open)render();
}
async function loadTab(){
  try{
    if(S.tab==='rank')S.lad=await post('ladder');
    else if(S.tab==='cup')S.cup=await post('cup_board');
    else if(S.tab==='war'){const [w]=await Promise.all([post('war'),tcLoad(false)]);S.war=w;if(!S.wpet)S.wpet=S.v?.war?.pick?.id||'';}
  }catch(e){S.flash={text:e.message||'Chưa tải được.',kind:'bad'};}
  if(S.dlg?.open)render();
}
async function run(op,data,after){
  S.busy=true;render();
  try{
    const r=await post(op,data);
    if(r.match&&typeof r.match==='object'){startFight(r.match,after);}
    else if(r.message)S.flash={text:r.message,kind:'good'};
    return r;
  }catch(e){S.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;render();}
}

/* ---------------------------------------------------------------- clicks */
async function onClick(op,data){
  if(op==='close'){close();return;}
  if(op==='pets'){close();S.env.act?.('pets',{tab:'adopt'});return;}
  if(op==='bang'){close();S.env.act?.('bang',{});return;}   // ⚔️ no bang yet: v4/bang.js (find or found one)
  if(op==='isle'){close();S.env.act?.('bang',{tab:'home',isle:1});return;}   // 🏝️ the bang's island offer (v4/bang.js)
  if(op==='tab'){S.tab=data.tab;S.sub='';S.flash=null;render();loadTab();return;}
  if(op==='back'){S.sub='';S.tcsub='';render();return;}
  if(op==='wsec'){S.wsec=data.sec;S.tcsub='';S.flash=null;render();return;}
  if(op==='tpet'){S.tpet=S.tpet===data.id?'':data.id;render();return;}
  if(op==='tcunreg'){const r=await run('tc_unreg',{});if(r){S.tpet='';await tcLoad();}return;}
  if(op==='tcmode'){const r=await run('tc_set',{mode:data.mode});if(r)await tcLoad();return;}
  if(op==='tcyes'||op==='tcno'){const r=await run('tc_answer',{id:data.id,ok:op==='tcyes'});if(r){await tcLoad();if(r.match)await watchChallenge(r.match);}return;}
  if(op==='tccancel'){const r=await run('tc_cancel',{id:data.id});if(r)await tcLoad();return;}
  if(op==='tcsend'){const r=await run('tc_send',{bang:data.id,rid:rid()});if(r){S.tcsub='';await tcLoad();if(r.match)await watchChallenge(r.match);}return;}
  if(op==='tcorder'){S.tcsub='order';S.ord=(S.tc?.roster||[]).map(x=>x.pid);render();return;}
  if(op==='tcmove'){const i=Number(data.i),j=i+Number(data.d);if(S.ord&&j>=0&&j<S.ord.length)[S.ord[i],S.ord[j]]=[S.ord[j],S.ord[i]];render();return;}
  if(op==='tcwatch'){await watchChallenge(data.id);return;}
  if(op==='team'){S.sub='team';S.pick=[...(S.v?.lineup||[])];render();return;}
  if(op==='tog'){const i=S.pick.indexOf(data.id);if(i>=0)S.pick.splice(i,1);else if(S.pick.length<(S.v?.rules?.lineup||3))S.pick.push(data.id);render();return;}
  if(op==='friends'){S.sub='friends';render();try{S.friends=(await post('friends')).friends;}catch{S.friends=[];}render();return;}
  if(op==='vsfriend'){await run('friend',{pid:data.pid},'friend');return;}
  if(op==='stage'){S.npc=Number(data.stage);render();return;}
  if(op==='replay'){S.busy=true;render();try{const r=await post('replay',{id:data.id});startFight(r.match,'replay');}catch(e){S.flash={text:e.message,kind:'bad'};}finally{S.busy=false;render();}return;}
  if(op==='wpet'){S.wpet=data.id;render();return;}
  if(op==='unpick'){const r=await run('war_unpick',{});if(r){S.war=null;await loadTab();await load();}return;}
  if(op==='lineup'){await openLineup();return;}
  if(op==='lsug'){S.lsel=suggest(S.wt);render();return;}
  if(op==='lmem'){toggleMember(data.pid);render();return;}
  if(op==='lpet'){pickPet(data.pid,data.id);render();return;}
  if(op==='leadoff'){const r=await run('war_lineup_off',{});if(r){await loadTab();await load();}return;}
  if(op==='watch'){await watchWar(Number(data.rd),Number(data.slot));return;}
  if(op==='cupleave'){const r=await run('cup_leave',{});if(r)await load();return;}
  if(op==='fast'){S.fast=!S.fast;S.dlg.querySelector('[data-pa="fast"]')?.classList.toggle('on',S.fast);return;}
  if(op==='skip'){skipFight();return;}
  if(op==='done'){S.watch++;stopFight();S.fight=null;render();load();if(S.tab!=='fight')loadTab();return;}
  if(op==='again'){const kind=S.fight?.after;stopFight();S.fight=null;
    if(kind==='npc')await run('npc',{stage:S.npc},'npc');else if(kind==='rank')await run('fight',{},'rank');else render();return;}
  if(op==='go')await main();
}
async function main(){
  const [, op]=mainButton();
  if(op==='fight'){await run('fight',{},'rank');return;}
  if(op==='save'){const r=await run('lineup',{pets:S.pick});if(r){S.sub='';await load();}return;}
  if(op==='npc'){await run('npc',{stage:S.npc},'npc');return;}
  if(op==='cupjoin'){const r=await run('cup_join',{});if(r){await load();await loadTab();}return;}
  if(op==='warpick'){const r=await run('war_pick',{pet:S.wpet});if(r){await loadTab();await load();}return;}
  if(op==='lineup'){await openLineup();return;}
  if(op==='lineupsave'){const r=await run('war_lineup',{picks:S.lsel});if(r){S.sub='';S.wt=null;await loadTab();await load();}return;}
  if(op==='tofight'){S.tab='war';S.sub='';render();}
  if(op==='tcreg'){const r=await run('tc_reg',{pet:S.tpet});if(r){S.tpet='';await tcLoad();}return;}
  if(op==='tcfind'){S.tcsub='find';S.tfind=null;render();findLoad();return;}
  if(op==='tcsave'){const r=await run('tc_order',{order:S.ord||[]});if(r){S.tcsub='';await tcLoad();}}
}
const rid=()=>'tc-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,10);
async function tcLoad(draw=true){
  try{S.tc=await post('tc');S.tcAt=Date.now();}catch(e){S.tc={error:e.message||'Chưa tải được.'};}
  if(draw&&S.dlg?.open)render();
}
async function findLoad(){
  try{S.tfind=await post('tc_find',{q:S.tq.slice(0,30)});}catch(e){S.tfind={error:e.message||'Chưa tải được.'};}
  if(S.dlg?.open)render();
}

/** The bottom bar's one button: [label, op, why]. */
function mainButton(){
  const v=S.v;if(!v||v.locked||v.error)return ['','',''];
  if(S.sub==='team')return [S.pick.length?`💾 Lưu đội · ${S.pick.length} bé`:'👆 Chọn 1–3 bé','save',S.pick.length?'':' '];
  if(S.sub==='friends')return ['','',''];
  if(S.sub==='lineup'){const t=S.wt;if(!t||t.error)return ['','',''];if(!t.open)return ['🔒 Đã chốt đội hình','',' '];
    const n=S.lsel.length;return [n?`💾 Lưu đội hình · ${n}/${t.size||5} bé`:'👆 Chọn ít nhất 1 bé','lineupsave',n?'':' '];}
  const t=v.today||{};
  if(S.tab==='fight')return ['⚔️ Tìm đối thủ','fight',t.rank>=t.rank_max?'Hôm nay đã đấu đủ, mai đấu tiếp nhé':''];
  if(S.tab==='npc'){const st=(v.npc||[])[S.npc];return [st?`🎯 Thử thách ${st.name}`:'🎯 Thử thách','npc',t.npc>=t.npc_max?'Hôm nay đã thử đủ':''];}
  if(S.tab==='cup'){const c=v.cup||{};if(!c.open)return ['🏟️ Giải tuần sau mở từ thứ Hai','',' '];return c.joined?['✅ Đã đăng ký giải tuần','',' ']:['🏟️ Đăng ký giải tuần','cupjoin',''];}
  if(S.tab==='war'&&S.wsec==='tc')return tcButton(v);
  if(S.tab==='war'){const w=S.war||{};if(!w.team)return ['','',''];if(w.phase!=='pick')return ['','',''];
    if(w.lead)return w.can_lead?['👑 Đổi đội hình bang','lineup','']:[`👑 ${w.lead.role} đã chọn đội hình`,'',' '];
    const p=(v.pets||[]).find(x=>x.id===S.wpet),now=v.war?.pick?.id;
    if(p&&p.id===now)return [`✅ ${p.n} đã ra trận`,'',' '];
    return p?[`🛡️ Cho ${p.n} ra trận`,'warpick','']:['👆 Chọn 1 bé ra trận','',' '];}
  return ['🛡️ Về Bang chiến','tofight',''];
}

/** ⚔️ Thách đấu's bottom button: save the order, register the picked pet, or (an officer) find a bang to challenge. */
function tcButton(v){
  const t=S.tc,m=t?.mine;if(!m)return ['','',''];
  if(S.tcsub==='order')return ['💾 Lưu thứ tự','tcsave',''];
  if(S.tcsub==='find')return ['','',''];
  const p=(v.pets||[]).find(x=>x.id===S.tpet);
  if(p&&p.id!==m.pet)return [`🐾 Ghi danh ${p.n}`,'tcreg',''];
  if(m.officer){const r=t.rules||{},d=m.today||{};
    const why=m.ready<(r.min||3)?`Cần ${r.min||3} bé trong đội hình`:d.played>=d.play_max?'Hôm nay đã đấu đủ, mai đấu tiếp nhé':d.sent>=d.send_max?'Hôm nay đã gửi đủ':'';
    return ['⚔️ Gửi thách đấu','tcfind',why];}
  if(!m.pet)return ['👆 Chọn 1 bé để ghi danh','',' '];
  return ['','',''];
}

/* ---------------------------------------------------------------- render */
function render(){
  if(!S.dlg)return;
  const root=S.dlg.querySelector('.pa-root');
  if(S.fight){if(!root.querySelector('.pa-fight'))root.innerHTML=fightHTML();return;}
  const body=root.querySelector('.pa-body'),y=body?.scrollTop;
  const a=document.activeElement,keep=a&&S.dlg.contains(a)&&a.name==='pa-tq'?{value:a.value,pos:a.selectionStart}:null;   // typing in the search: keep it
  root.innerHTML=page();
  if(y)root.querySelector('.pa-body').scrollTop=y;
  if(keep){const b=root.querySelector('input[name="pa-tq"]');if(b){b.value=keep.value;b.focus({preventScroll:true});try{b.setSelectionRange(keep.pos,keep.pos);}catch{/* not text */}}}
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function page(){
  const t=TABS.find(x=>x[0]===S.tab)||TABS[0];
  const sub=S.sub||(S.tab==='war'&&S.wsec==='tc'?S.tcsub:'');
  const head=`<header class="sheet-head pa-head">${sub?`<button class="icon-btn" type="button" data-pa="back" aria-label="Quay lại">${icon('back',21)}</button>`:'<span class="pa-logo" aria-hidden="true">🐾</span>'}
    <div class="grow"><h2 id="pa-title">${S.sub==='lineup'?'Đội hình bang chiến':S.sub==='team'?'Xếp đội':S.sub==='friends'?'Đấu với đồng đội':sub==='find'?'Chọn bang':sub==='order'?'Xếp đội hình':'Đấu trường bang'}</h2></div>
    ${S.v?.me?`<span class="pa-score" title="Điểm xếp hạng tuần">🏆 ${fmt(S.v.me.rating)}</span>`:''}<button class="icon-btn" type="button" data-pa="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
  const tabs=sub?'':`<nav class="pa-tabs" role="tablist" aria-label="Đấu trường">${TABS.map(([id,e,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'on':''}" data-pa="tab" data-tab="${id}"><span aria-hidden="true">${e}</span><small>${esc(l)}</small></button>`).join('')}</nav>`;
  const v=S.v;
  let inner;
  if(!v)inner='<p class="pa-empty">⏳</p>';
  else if(v.error)inner=`<p class="pa-empty">${esc(v.error)}</p>`;
  else if(v.locked)inner=locked(v.locked,v.island);
  else if(S.sub==='team')inner=teamPicker(v);
  else if(S.sub==='friends')inner=friendsList();
  else if(S.sub==='lineup')inner=lineupView();
  else if(sub==='find')inner=findView();
  else if(sub==='order')inner=orderView();
  else inner=S.tab==='npc'?npcTab(v):S.tab==='rank'?rankTab():S.tab==='cup'?cupTab(v):S.tab==='war'?warTab(v):fightTab(v);
  const [label,,why]=mainButton(),w=why&&why.trim();
  const bar=label?`<footer class="pa-bar">${w?`<small class="pa-why">${esc(why)}</small>`:''}<button type="button" class="btn primary big pa-main" data-pa="go"${S.busy||w||why===' '?' disabled':''}>${esc(label)}</button></footer>`:'';
  const flash=`<p class="pa-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
  return head+tabs+`<div class="sheet-body pa-body">${flash}${inner}</div>`+bar;
}
function locked(why,isle){
  // 🏝️ 21/10: a bang plays here once it holds its island: an officer buys it, a member asks one
  if(why==='island')return `<div class="pa-locked"><span aria-hidden="true">🏝️</span><p>${isle?.officer?`Bang cần có Đảo bang mới ra trận được. Mua đảo bằng quỹ bang (${esc(fmt(isle.cost||1000000))} xu).`:'Bang cần có Đảo bang mới ra trận được. Nhờ Bang chủ hoặc Phó bang mua đảo nhé!'}</p><button type="button" class="btn primary" data-pa="isle">${isle?.officer?'🏝️ Mua Đảo bang':'⚔️ Mở Bang'}</button></div>`;
  const [e,t,a]=why==='account'?['🔐','Tạo tài khoản để vào đấu trường nhé.','']:why==='story'?['📖','Đấu trường có trong hành trình.','']:
    why==='bang'?['🏯','Đấu trường chỉ dành cho thành viên bang. Vào một bang để cùng đồng đội ra trận nhé!','<button type="button" class="btn primary" data-pa="bang">⚔️ Tìm bang</button>']:
    ['🐶','Nuôi một bé đã nhé, rồi cho bé ra đấu trường.','<button type="button" class="btn primary" data-pa="pets">🐾 Nhận nuôi</button>'];
  return `<div class="pa-locked"><span aria-hidden="true">${e}</span><p>${esc(t)}</p>${a}</div>`;
}
/** A small card of a pet in a lineup. */
function petCard(f,extra=''){
  return `<div class="pa-pet">${pic(f,56)}<b data-no-translate>${esc(f.n)}</b><small>${rk(f.r)}${elTag(f.e)} 💪${fmt(f.pw)}</small>${extra}</div>`;
}
function fightTab(v){
  const me=v.me,s=me.season,t=v.today;
  const team=(v.team||[]).map(f=>petCard(f)).join('')||'<p class="pa-muted">Chưa có bé nào trong đội.</p>';
  const recent=(v.recent||[]).slice(0,8).map(r=>`<button type="button" class="pa-row ${r.res}" data-pa="replay" data-id="${esc(r.id)}">
      <span class="pa-res" aria-hidden="true">${r.res==='win'?'🏅':r.res==='draw'?'🤝':'💤'}</span><b data-no-translate>${esc(r.vs)}</b>
      <small>${r.kind==='rank'?(r.d>0?'+':'')+r.d:KIND[r.kind]||''}</small><span class="pa-play" aria-label="Xem lại">▶</span></button>`).join('');
  return `<section class="pa-card pa-team"><div class="pa-row-head"><h3>Đội của bạn</h3><button type="button" class="pa-chip" data-pa="team">✏️ Đổi đội</button></div>
      <div class="pa-pets">${team}</div><p class="pa-muted">💪 ${fmt(v.pw)} · Tuần này ${s.w} thắng ${s.l} thua${s.d?` ${s.d} hòa`:''} · Hôm nay ${t.rank}/${t.rank_max} trận</p></section>
    <div class="pa-chips"><button type="button" class="pa-chip" data-pa="friends">🤝 Đấu với đồng đội</button><button type="button" class="pa-chip" data-pa="tab" data-tab="npc">🎯 Thử thách</button></div>
    ${recent?`<section class="pa-card"><h4>Trận gần đây</h4><div class="pa-list">${recent}</div></section>`:''}
    <details class="pa-help"><summary>Luật đấu</summary>${helpHTML(v)}</details>`;
}
const KIND={friend:'giao hữu',npc:'thử thách',spar:'đấu tập',cup:'giải tuần'};
function helpHTML(v){
  const r=v.rules||{};
  const els=(v.elements||[]).map(e=>`<li>${e.emoji} ${esc(e.name)} khắc ${EL[e.beats]?.[0]||''} ${esc(EL[e.beats]?.[1]||'')} · ${e.skill[0]} ${esc(e.skill[1])}</li>`).join('');
  return `<ul class="pa-rules"><li>Mỗi đội 1–${r.lineup||3} bé, đánh lần lượt, bé thắng giữ máu đánh tiếp.</li>
    <li>Chỉ số, hạng, huấn luyện và linh kiện của bé đều tính. Bé không bao giờ bị thương hay mất đồ.</li>
    <li>Ngũ hành:</li>${els}<li>🐶 Chó có thể trụ lại 1 máu một lần · 🐱 Mèo né giỏi hơn · 🌟 Huyền thoại, thần thú đánh mạnh hơn.</li>
    <li>Xếp hạng: ${r.rank_day} trận một ngày, cùng một người tối đa ${r.pair_day} trận, không ghép hai máy cùng mạng.</li>
    <li>Danh hiệu tuần cần ${r.min_games} trận với ${r.min_opp} người khác nhau. Không có xu, chỉ có danh hiệu.</li></ul>`;
}
function teamPicker(v){
  const max=v.rules?.lineup||3;
  const grid=(v.pets||[]).map(p=>{const i=S.pick.indexOf(p.id);return `<button type="button" class="pa-pick${i>=0?' on':''}" data-pa="tog" data-id="${esc(p.id)}" aria-pressed="${i>=0}">
      ${i>=0?`<em class="pa-num">${i+1}</em>`:''}${pic(p,64)}<b data-no-translate>${esc(p.n)}</b><small>${rk(p.r)}${elTag(p.e)} 💪${fmt(p.pw)}</small>
      <small class="pa-stat"><span>❤️${fmt(p.hp)}</span><span>⚔️${fmt(p.atk)}</span><span>🛡️${fmt(p.df)}</span></small><small class="pa-skill">${p.sk?esc(p.sk[0]+' '+p.sk[1]):''}</small></button>`;}).join('');
  return `<p class="pa-muted">Chọn tối đa ${max} bé theo thứ tự ra sân. Bé ở nhà và ở trại nuôi đều đấu được.</p><div class="pa-picks">${grid}</div>`;
}
function friendsList(){
  if(!S.friends)return '<p class="pa-empty">⏳</p>';
  if(!S.friends.length)return '<div class="pa-locked"><span aria-hidden="true">🤝</span><p>Chưa có đồng đội nào xếp đội. Rủ cả bang vào chơi nhé!</p></div>';
  return `<p class="pa-muted">Giao hữu: không tính điểm.</p><div class="pa-list">${S.friends.map(f=>`<button type="button" class="pa-row" data-pa="vsfriend" data-pid="${esc(f.pid)}"${S.busy?' disabled':''}>
    <span class="pa-res" aria-hidden="true">🤝</span><b data-no-translate>${esc(f.name)}</b><small>🏆 ${fmt(f.rating)} · 💪 ${fmt(f.pw)}</small><span class="pa-play">⚔️</span></button>`).join('')}</div>`;
}
function npcTab(v){
  const t=v.today||{};
  return `<p class="pa-muted">Đấu với Bé nhà Mây. Thắng lần đầu mỗi thử thách trong ngày: +1 ⭐. Còn ${Math.max(0,t.npc_max-t.npc)} lượt hôm nay.</p>
    <div class="pa-stages">${(v.npc||[]).map(st=>`<button type="button" class="pa-stage${S.npc===st.stage?' on':''}${st.won?' won':''}" data-pa="stage" data-stage="${st.stage}" aria-pressed="${S.npc===st.stage}">
      <b>${['🌱','🔥','💀'][st.stage]||''} ${esc(st.name)}</b><span class="pa-mini-team">${st.pets.map(f=>pic(f,40)).join('')}</span><small>💪 ${fmt(st.pw)}${st.won?' · ⭐ đã qua':''}</small></button>`).join('')}</div>
    <p class="pa-muted">Đội của bạn: 💪 ${fmt(v.pw)} · Tuần này ${v.me.season.stars} ⭐</p>`;
}
function titlesBlock(w){
  if(!w?.tiers)return '';
  return `<section class="pa-card pa-titles"><h4>Danh hiệu tuần</h4>${w.tiers.map(tr=>`<p><b>${tr.emoji} ${esc(tr.name)}</b> <small>${esc(tr.label)}</small><br>
    <span data-no-translate>${tr.holders.length?tr.holders.map(h=>esc(h.name)+(h.me?' (bạn)':'')).join(', '):'—'}</span></p>`).join('')}</section>`;
}
function rankTab(){
  const l=S.lad;if(!l)return '<p class="pa-empty">⏳</p>';
  const me=l.me;
  const mine=me?`<section class="pa-card pa-me"><b>Bạn: 🏆 ${fmt(me.rating)}</b> · ${me.w} thắng ${me.l} thua${me.rank?` · hạng ${me.rank}`:''}
    ${me.need||me.need_opp?`<p class="pa-muted">Còn ${me.need} trận, ${me.need_opp} đối thủ mới nữa để lên bảng.</p>`:''}</section>`:'';
  const rows=(l.top||[]).map(r=>`<li class="${r.me?'me':''}"><span class="pa-rank r${Math.min(r.rank,4)}">${r.rank<=3?['🥇','🥈','🥉'][r.rank-1]:r.rank}</span><b data-no-translate>${esc(r.name)}</b><small>${r.w}–${r.l}</small><em>🏆 ${fmt(r.rating)}</em></li>`).join('');
  return mine+(rows?`<ol class="pa-ladder">${rows}</ol>`:`<p class="pa-muted">Chưa ai đủ ${l.min_games} trận tuần này. Đấu ngay để lên bảng!</p>`)+titlesBlock(l.weekly);
}
function cupTab(v){
  const c=v.cup||{},b=S.cup;
  const card=`<section class="pa-card pa-cup-card"><h3>🏟️ Giải đấu pet tuần</h3><p>${c.open?`Bắt đầu <b>${esc(hm(c.at))}</b>`:'Giải tuần này đã đấu.'} · ${fmt(c.n)} người${c.joined?' · ✅ bạn đã đăng ký':''}</p>
    <p class="pa-muted">Đấu kiểu Thụy Sĩ: cùng điểm gặp nhau, không gặp lại một người. Đội đang xếp ra sân lúc giải bắt đầu.</p>
    ${c.joined&&c.open?'<button type="button" class="pa-chip" data-pa="cupleave">Rút tên</button>':''}</section>`;
  if(!b)return card+'<p class="pa-empty">⏳</p>';
  if(!b.cup)return card;
  const st=b.cup.status==='cancelled'?`<p class="pa-muted">Giải ${esc(b.cup.week)} không đủ người, hẹn tuần sau.</p>`:'';
  const top=(b.top||[]).slice(0,20).map(r=>`<li class="${r.me?'me':''}"><span class="pa-rank r${Math.min(r.rank,4)}">${r.rank<=3?['🥇','🥈','🥉'][r.rank-1]:r.rank}</span><b data-no-translate>${esc(r.name)}</b>
    <span class="pa-mini-team">${r.pets.map(f=>pic(f,28)).join('')}</span><em>${r.score} đ</em></li>`).join('');
  const mine=(b.matches||[]).map(m=>`<button type="button" class="pa-row ${m.res}" data-pa="replay" data-id="${esc(m.id)}"><span class="pa-res">V${m.rd}</span><b data-no-translate>${esc(m.vs)}</b><small>${m.res==='win'?'Thắng':m.res==='draw'?'Hòa':'Thua'}</small><span class="pa-play">▶</span></button>`).join('');
  return card+st+(top?`<section class="pa-card"><h4>Kết quả ${esc(b.cup.week)} · ${b.cup.n} người · ${b.cup.rounds} vòng</h4><ol class="pa-ladder">${top}</ol></section>`:'')+
    (mine?`<section class="pa-card"><h4>Trận của bạn</h4><div class="pa-list">${mine}</div></section>`:'')+titlesBlock(b.weekly);
}
function seg(){
  const n=S.tc?.incoming?.length||0;
  return `<div class="pa-seg" role="tablist" aria-label="Bang chiến">${[['tc','⚔️ Thách đấu'],['war','🗓️ Bang chiến tuần']].map(([k,l])=>`<button type="button" role="tab" aria-selected="${S.wsec===k}" class="${S.wsec===k?'on':''}" data-pa="wsec" data-sec="${k}">${l}${k==='tc'&&n?` <em class="pa-badge">${n}</em>`:''}</button>`).join('')}</div>`;
}
function warTab(v){
  if(S.wsec==='tc')return seg()+tcTab(v);
  return seg()+warWeek(v);
}
function warWeek(v){
  const w=S.war;if(!w)return '<p class="pa-empty">⏳</p>';
  const when=`<p>${w.phase==='pick'?`Đấu <b>${esc(hm(w.start))}</b> · chốt đội ${esc(clock(w.lock))}`:w.phase==='live'?'🔴 Đang diễn ra':w.phase==='done'?'Đã xong tuần này':w.phase==='cancelled'?'Tuần này không đủ bang':'Đang xếp cặp…'}</p>`;
  const head=`<section class="pa-card pa-war-card"><h3>🛡️ Bang chiến pet</h3>${when}<p class="pa-muted">Mỗi người chọn 1 bé, mỗi bang ${w.size} bé. Xếp cặp ngẫu nhiên ${w.size} trận 1–1, thắng nhiều hơn vào vòng trong.</p></section>`;
  let team='';
  if(!w.team)team=`<div class="pa-locked"><span aria-hidden="true">🏯</span><p>Vào một bang để cùng ra trận nhé.</p><button type="button" class="pa-chip" data-pa="bang">⚔️ Tìm bang</button></div>`;
  else{
    const slots=[];for(let i=0;i<w.size;i++){const p=w.picks[i];slots.push(p?`<div class="pa-slot${p.me?' me':''}">${pic(p.pet,44)}<small data-no-translate>${esc(p.name)}</small></div>`:`<div class="pa-slot empty"><span>?</span><small>Trống</small></div>`);}
    const mine=w.picks.find(p=>p.me);
    const lead=w.lead?`<p class="pa-lead">👑 <b>${esc(w.lead.role)} đã chọn đội hình</b>${w.can_lead?' · bạn đổi được tới lúc chốt.':' · bạn không tự đổi được.'}</p>`:'';
    const boss=w.can_lead&&w.phase==='pick'?`<div class="pa-chips"><button type="button" class="pa-chip on" data-pa="lineup">👑 ${w.lead?'Đổi':'Chọn'} đội hình bang</button>${w.lead?'<button type="button" class="pa-chip" data-pa="leadoff">↩️ Để mọi người tự chọn</button>':''}</div>`:'';
    const choose=w.lead?'':w.phase==='pick'?`<h4>${mine?'Đổi bé ra trận':'Chọn bé ra trận'}</h4><div class="pa-picks sm">${(v.pets||[]).map(p=>`<button type="button" class="pa-pick${S.wpet===p.id?' on':''}" data-pa="wpet" data-id="${esc(p.id)}" aria-pressed="${S.wpet===p.id}">${pic(p,52)}<b data-no-translate>${esc(p.n)}</b><small>${rk(p.r)}${elTag(p.e)} 💪${fmt(p.pw)}</small></button>`).join('')}</div>
      ${mine?'<button type="button" class="pa-chip" data-pa="unpick">Rút bé khỏi đội</button>':''}`:'';
    team=`<section class="pa-card"><h4 data-no-translate>${esc(w.team.name)}</h4>${lead}<div class="pa-slots">${slots.join('')}</div>${boss}${choose}</section>`;
  }
  return head+team+bracket(w)+(w.champ?`<p class="pa-champ">🏆 ${esc(w.champ)} vô địch!</p>`:'')+warLadder(w);
}
function bracket(w){
  if(!w.bracket?.length)return '';
  const by=r=>w.bracket.filter(m=>m.rd===r.rd);
  return `<section class="pa-card pa-bracket"><h4>Nhánh đấu</h4>${w.rounds.map(r=>`<div class="pa-round"><b>${esc(r.name)}</b>${by(r).map(m=>{
    const a=m.a||'?',b=m.bye?'(miễn đấu)':m.b||'?',done=m.state==='done',sc=m.bye?'✓':done?`${m.wa}–${m.wb}`:m.state==='live'?'🔴':clock(m.start);
    const can=m.state!=='wait'&&!m.bye&&m.a;
    return `<button type="button" class="pa-match${m.mine?' mine':''} ${m.state}" data-pa="watch" data-rd="${m.rd}" data-slot="${m.slot}"${can?'':' disabled'}>
      <span class="${done&&m.win===0?'won':''}" data-no-translate>${esc(a)}</span><em>${esc(sc)}</em><span class="${done&&m.win===1?'won':''}" data-no-translate>${esc(b)}</span>${can?'<i aria-hidden="true">👀</i>':''}</button>`;}).join('')}</div>`).join('')}</section>`;
}
function warLadder(w){
  if(!w.ladder?.length)return w.last?`<p class="pa-muted">Tuần trước: 🏆 ${esc(w.last.champ||'—')}</p>`:'';
  return `<section class="pa-card"><h4>Bảng xếp hạng bang</h4><ol class="pa-ladder">${w.ladder.map(r=>`<li><span class="pa-rank r${Math.min(r.rank,4)}">${r.champ?'🏆':r.rank}</span><b data-no-translate>${esc(r.name)}</b><small>${r.w}–${r.l}</small><em>${fmt(r.pts)} đ</em></li>`).join('')}</ol></section>`;
}

/* ---------------------------------------------------------------- 👑 the leaders' lineup of the weekly war */
/** Each eligible member's strongest pet, the strongest members first, up to the team's size. */
function suggest(t){return (t?.members||[]).filter(m=>m.ok&&m.best).slice(0,t.size||5).map(m=>({pid:m.pid,pet:m.best}));}
/** What the editor opens with: the leaders' lineup as it stands, else the members' own picks topped up with the suggestion. */
function prefill(t){
  const out=(t?.picks||[]).map(x=>({pid:x.pid,pet:x.pet}));if(t?.lead)return out;
  for(const m of (t?.members||[]).filter(x=>x.ok&&x.best)){if(out.length>=(t.size||5))break;if(!out.some(x=>x.pid===m.pid))out.push({pid:m.pid,pet:m.best});}
  return out;
}
async function openLineup(){
  S.sub='lineup';S.wt=null;S.lsel=[];S.flash=null;render();
  try{S.wt=await post('war_team');S.lsel=prefill(S.wt);}
  catch(e){S.wt={error:e.message||'Chưa tải được.'};}
  if(S.dlg?.open)render();
}
const lmax=()=>S.wt?.size||5;
function toggleMember(pid){
  const i=S.lsel.findIndex(x=>x.pid===pid);if(i>=0){S.lsel.splice(i,1);return;}
  const m=(S.wt?.members||[]).find(x=>x.pid===pid);if(!m?.ok)return;
  if(S.lsel.length>=lmax()){S.flash={text:`Đủ ${lmax()} bé rồi. Bỏ bớt 1 người nhé.`,kind:'bad'};return;}
  S.flash=null;S.lsel.push({pid,pet:m.best});
}
function pickPet(pid,pet){
  const x=S.lsel.find(y=>y.pid===pid);if(x){x.pet=pet;return;}
  if(S.lsel.length>=lmax()){S.flash={text:`Đủ ${lmax()} bé rồi. Bỏ bớt 1 người nhé.`,kind:'bad'};return;}
  S.flash=null;S.lsel.push({pid,pet});
}
function lineupView(){
  const t=S.wt;if(!t)return '<p class="pa-empty">⏳</p>';
  if(t.error)return `<p class="pa-empty">${esc(t.error)}</p>`;
  const size=t.size||5,by=Object.fromEntries((t.members||[]).map(m=>[m.pid,m]));
  const slots=[];
  for(let i=0;i<size;i++){const x=S.lsel[i],m=x&&by[x.pid],p=m?.pets.find(q=>q.id===x.pet);
    slots.push(p?`<button type="button" class="pa-slot on" data-pa="lmem" data-pid="${esc(m.pid)}" aria-label="Bỏ ${esc(m.name)}"><em class="pa-num">${i+1}</em>${pic(p,44)}<small data-no-translate>${esc(m.name)}</small></button>`
      :`<div class="pa-slot empty"><span>${i+1}</span><small>Trống</small></div>`);}
  const rows=(t.members||[]).map(m=>{const i=S.lsel.findIndex(x=>x.pid===m.pid),sel=i>=0?S.lsel[i]:null;
    const pets=m.ok?m.pets.map(p=>`<button type="button" class="pa-lp${sel?.pet===p.id?' on':''}" data-pa="lpet" data-pid="${esc(m.pid)}" data-id="${esc(p.id)}" aria-pressed="${sel?.pet===p.id}">${pic(p,40)}<b data-no-translate>${esc(p.n)}</b><small>${rk(p.r)}${elTag(p.e)} 💪${fmt(p.pw)}</small></button>`).join(''):'';
    return `<li class="pa-lm${sel?' on':''}${m.ok?'':' off'}"><button type="button" class="pa-lm-who" data-pa="lmem" data-pid="${esc(m.pid)}" aria-pressed="${!!sel}"${m.ok?'':' disabled'}>
      <span class="pa-lm-box" aria-hidden="true">${sel?i+1:''}</span><span class="grow"><b data-no-translate>${esc(m.name)}${m.me?' (bạn)':''}</b><small>${esc(m.role||'')}${m.ok?` · 💪 ${fmt(m.pw)}`:` · ${esc(m.why||'Chưa có bé')}`}</small></span></button>
      ${pets?`<div class="pa-lm-pets">${pets}</div>`:''}</li>`;}).join('');
  const lead=t.lead?`<p class="pa-lead">👑 <b>${esc(t.lead.role)} đã chọn đội hình</b> · lưu lại để đổi.</p>`:'';
  return `${lead}<section class="pa-card pa-lsum"><div class="pa-slots">${slots.join('')}</div>
    <p class="pa-muted">Chọn tối đa ${size} người, mỗi người 1 bé. Gợi ý sẵn bé mạnh nhất của mỗi người. Thứ tự 5 trận bốc ngẫu nhiên lúc vào trận. Chốt đội ${esc(clock(t.lock))}.</p>
    <div class="pa-chips"><button type="button" class="pa-chip" data-pa="lsug">✨ Gợi ý mạnh nhất</button></div></section>
    <ul class="pa-lms">${rows||'<li class="pa-muted">Bang chưa có ai.</li>'}</ul>`;
}

/* ---------------------------------------------------------------- ⚔️ Thách đấu bang */
const RES={win:'🏅',loss:'💤',draw:'🤝'};
const tnow=()=>(Number(S.tc?.now)||Date.now()/1000)+Math.max(0,Date.now()-S.tcAt)/1000;
function until(t){const m=Math.ceil(Math.max(0,t-tnow())/60);return m>=1?`còn ${m} phút`:'sắp hết giờ';}
function tcTab(v){
  const t=S.tc;if(!t)return '<p class="pa-empty">⏳</p>';
  if(t.error)return `<p class="pa-empty">${esc(t.error)}</p>`;
  const m=t.mine,r=t.rules||{},modes=t.modes||{};
  if(!m)return locked('bang')+townCard(t);
  const d=m.today||{},busy=S.busy?' disabled':'';
  const modeRow=m.boss?`<p class="pa-muted pa-modes-l">Khi có bang thách:</p><div class="pa-modes" aria-label="Khi có bang thách">${Object.entries(modes).map(([k,l])=>`<button type="button" class="pa-chip${m.mode===k?' on':''}" data-pa="tcmode" data-mode="${k}" aria-pressed="${m.mode===k}"${busy}>${esc(l)}</button>`).join('')}</div>`:`<p class="pa-muted">${esc(modes[m.mode]||'')}</p>`;
  const head=`<section class="pa-card pa-tc-head"><h3 data-no-translate>${esc(m.name)}</h3>
    <p class="pa-tc-rec"><b>🏆 ${fmt(m.rating)}</b><span>${m.w} thắng · ${m.l} thua${m.d?` · ${m.d} hòa`:''}</span><span>💪 ${fmt(m.power)}</span></p>
    <p class="pa-muted">Hôm nay đấu ${d.played}/${d.play_max} · gửi ${d.sent}/${d.send_max}</p>${modeRow}</section>`;
  const inc=(t.incoming||[]).map(c=>`<div class="pa-tc-row in"><span class="pa-res" aria-hidden="true">⚔️</span><span class="grow"><b data-no-translate>${esc(c.vs)}</b><small>${c.foe?`🏆 ${fmt(c.foe.rating)} · 💪 ${fmt(c.foe.power)} · `:''}⏳ ${esc(until(c.expires))}</small></span>
    ${m.officer?`<button type="button" class="btn primary" data-pa="tcyes" data-id="${esc(c.id)}"${busy}>Nhận</button><button type="button" class="btn cream" data-pa="tcno" data-id="${esc(c.id)}" aria-label="Từ chối"${busy}>✕</button>`:'<small class="pa-wait">Chờ Trưởng lão</small>'}</div>`).join('');
  const out=(t.outgoing||[]).map(c=>`<div class="pa-tc-row"><span class="pa-res" aria-hidden="true">⏳</span><span class="grow"><b data-no-translate>${esc(c.vs)}</b><small>Chờ trả lời · ${esc(until(c.expires))}</small></span>${m.officer?`<button type="button" class="btn cream" data-pa="tccancel" data-id="${esc(c.id)}"${busy}>Hủy</button>`:''}</div>`).join('');
  const box=inc||out?`<section class="pa-card pa-tc-box"><h4>📨 Lời thách đấu</h4><div class="pa-list">${inc}${out}</div></section>`:'';
  const ros=(t.roster||[]).map(x=>`<li class="${x.me?'me':''}${x.start?' start':''}${x.ok?'':' off'}"><em>${x.n}</em>${x.pet?pic(x.pet,40):'<span class="pa-unknown" aria-hidden="true">🐾</span>'}
    <span class="grow"><b data-no-translate>${esc(x.pet?.n||'—')}</b><small data-no-translate>${esc(x.name)}</small></span><small class="pa-tag">${x.ok?(x.start?'Ra sân':'Dự bị'):'Vắng'}${x.pet?`<br>💪 ${fmt(x.pet.pw)}`:''}</small></li>`).join('');
  const roster=`<section class="pa-card"><div class="pa-row-head"><h4>🐾 Đội hình · ${m.ready}/${r.size||5} ra sân</h4>${m.officer&&(t.roster||[]).length>1?'<button type="button" class="pa-chip" data-pa="tcorder">✏️ Xếp</button>':''}</div>
    ${ros?`<ol class="pa-roster">${ros}</ol>`:'<p class="pa-muted">Chưa ai ghi danh. Mỗi người ghi danh 1 bé nhé!</p>'}<p class="pa-muted">${r.size||5} bé đầu ra sân, còn lại dự bị. Cần ${r.min||3} bé để thách đấu.</p></section>`;
  const mine=(t.roster||[]).find(x=>x.me),cur=S.tpet||m.pet;
  const pick=`<details class="pa-card pa-mypet"${mine?'':' open'}><summary>${mine?`🐾 Bé của bạn: <b data-no-translate>${esc(mine.pet?.n||'—')}</b> · Đổi`:'🐾 Ghi danh 1 bé'}</summary>
    <div class="pa-picks sm">${(v.pets||[]).map(p=>`<button type="button" class="pa-pick${cur===p.id?' on':''}" data-pa="tpet" data-id="${esc(p.id)}" aria-pressed="${cur===p.id}">${pic(p,52)}<b data-no-translate>${esc(p.n)}</b><small>${rk(p.r)}${elTag(p.e)} 💪${fmt(p.pw)}</small></button>`).join('')}</div>
    ${mine?`<button type="button" class="pa-chip" data-pa="tcunreg"${busy}>Rút bé</button>`:''}</details>`;
  const rec=(t.recent||[]).map(c=>c.status==='done'?`<button type="button" class="pa-row ${c.res}" data-pa="tcwatch" data-id="${esc(c.id)}"><span class="pa-res" aria-hidden="true">${RES[c.res]||''}</span><b data-no-translate>${esc(c.vs)}</b><small>${c.mine===0?`${c.wa}–${c.wb}`:`${c.wb}–${c.wa}`}</small><span class="pa-play" aria-label="Xem lại">▶</span></button>`
    :`<div class="pa-row muted"><span class="pa-res" aria-hidden="true">${{declined:'🙅',expired:'⌛',cancelled:'↩️'}[c.status]||''}</span><b data-no-translate>${esc(c.vs)}</b><small>${{declined:'Từ chối',expired:'Hết hạn',cancelled:'Đã hủy'}[c.status]||''}</small></div>`).join('');
  const recent=rec?`<section class="pa-card"><h4>Trận của bang</h4><div class="pa-list">${rec}</div></section>`:'';
  const help=`<details class="pa-help"><summary>Luật thách đấu</summary><ul class="pa-rules"><li>Trưởng lão trở lên gửi và nhận lời, trong ${Math.round((r.window||1800)/60)} phút.</li>
    <li>${r.size||5} trận 1–1 ghép ngẫu nhiên, thắng nhiều hơn là thắng. Thiếu bé thì thua trận đó.</li>
    <li>Mỗi ngày: gửi ${r.send_day}, đấu ${r.play_day} trận, gặp cùng 1 bang ${r.pair_day} trận.</li>
    <li>Thắng: +${fmt(r.score_win)} điểm 🐾 xếp hạng bang tuần, mỗi bé ra sân +${r.pts_win} điểm cống hiến (tối đa ${r.pts_day}/ngày). Không có xu.</li>
    <li>🐾 Sân luyện pet: +1% chỉ số mỗi cấp, tối đa ${r.training}%.</li></ul></details>`;
  return head+box+roster+pick+recent+townCard(t)+help;
}
function townCard(t){
  const rows=(t.town||[]).map(c=>`<button type="button" class="pa-match done" data-pa="tcwatch" data-id="${esc(c.id)}"><span class="${c.win===0?'won':''}" data-no-translate>${esc(c.a)}</span><em>${c.wa}–${c.wb}</em><span class="${c.win===1?'won':''}" data-no-translate>${esc(c.b)}</span><i aria-hidden="true">👀</i></button>`).join('');
  return rows?`<section class="pa-card"><h4>👀 Khắp phố</h4>${rows}</section>`:'';
}
function findView(){
  const box=`<label class="pa-search"><span aria-hidden="true">🔎</span><input type="search" name="pa-tq" value="${esc(S.tq)}" placeholder="Tìm tên bang" maxlength="30" autocomplete="off" enterkeyhint="search"></label>`;
  const f=S.tfind;if(!f)return box+'<p class="pa-empty">⏳</p>';
  if(f.error)return box+`<p class="pa-empty">${esc(f.error)}</p>`;
  const rows=(f.list||[]).map(c=>`<div class="pa-tc-row${c.why?' off':''}"><span class="pa-crest" aria-hidden="true">${esc(c.emoji)}</span><span class="grow"><b data-no-translate>${esc(c.name)}</b>
    <small>🏆 ${fmt(c.rating)} · ${c.w}–${c.l} · 💪 ${fmt(c.power)}${c.auto?' · 🤖':''}</small>${c.why?`<small class="pa-why-s">${esc(c.why)}</small>`:''}</span>
    ${c.why?'':`<button type="button" class="btn primary" data-pa="tcsend" data-id="${esc(c.id)}"${S.busy?' disabled':''}>⚔️ Thách</button>`}</div>`).join('');
  return box+`<p class="pa-muted">Bang mình 💪 ${fmt(f.power)} · sức gần nhau ở trên · 🤖 tự nhận lời</p>`+(rows?`<div class="pa-list">${rows}</div>`:'<p class="pa-muted">Chưa có bang nào khác.</p>');
}
function orderView(){
  const by=Object.fromEntries((S.tc?.roster||[]).map(x=>[x.pid,x])),size=S.tc?.rules?.size||5,list=(S.ord||[]).filter(p=>by[p]);
  let n=0;
  return `<p class="pa-muted">${size} bé sẵn sàng đầu tiên ra sân, còn lại dự bị. Bấm ▲ ▼ để xếp.</p><ol class="pa-roster edit">${list.map((pid,i)=>{const x=by[pid],st=x.ok&&n++<size,at=S.ord.indexOf(pid);
    return `<li class="${st?'start':''}${x.ok?'':' off'}"><em>${i+1}</em>${x.pet?pic(x.pet,40):''}<span class="grow"><b data-no-translate>${esc(x.pet?.n||'—')}</b><small data-no-translate>${esc(x.name)} · ${x.ok?(st?'Ra sân':'Dự bị'):'Vắng'}</small></span>
      <button type="button" class="pa-mv" data-pa="tcmove" data-i="${at}" data-d="-1" aria-label="Lên"${i?'':' disabled'}>▲</button><button type="button" class="pa-mv" data-pa="tcmove" data-i="${at}" data-d="1" aria-label="Xuống"${i<list.length-1?'':' disabled'}>▼</button></li>`;}).join('')}</ol>`;
}
/** ▶ A played challenge: its five duels one after another (the same fights from the server's log), the viewer's bang on the left. */
async function watchChallenge(id){
  let mv;
  try{mv=await post('tc_match',{id});}catch(e){S.flash={text:e.message,kind:'bad'};render();return;}
  let i=0;const score=[0,0];
  const watching=++S.watch;
  const flip=mv.me===1,L=flip?mv.b:mv.a,R=flip?mv.a:mv.b;
  const next=()=>{
    if(watching!==S.watch||!S.dlg?.open||(i&&!S.fight))return;
    if(i>=mv.duels.length){
      const after=$('.pa-after');if(!after)return;
      const sc=flip?[mv.wb,mv.wa]:[mv.wa,mv.wb];
      const line=mv.win===2?'🤝 Hai bang hòa!':mv.me==null?`🏆 ${mv.win===0?mv.a:mv.b} thắng!`:mv.win===mv.me?'🎉 Bang mình thắng!':'💪 Bang mình thua, lần sau nhé!';
      after.insertAdjacentHTML('beforeend',`<p class="pa-msg">${esc(line)}</p><div class="pa-after-btns"><button type="button" class="btn primary big" data-pa="done">👌 Xong · ${sc[0]}–${sc[1]}</button></div>`);return;
    }
    const d=mv.duels[i++];
    if(d.w===0)score[0]++;else if(d.w===1)score[1]++;
    const sc=flip?[score[1],score[0]]:score;
    const m={kind:'tc',sides:d.sides,ev:d.ev,hp:d.hp,max:d.max,w:d.w,me:mv.me??null,message:`Trận ${d.i+1}/${mv.total} · ${L} ${sc[0]}–${sc[1]} ${R}`};
    startFight(m,'tc',{title:`⚔️ ${mv.a} – ${mv.b}`,sub:`Trận ${d.i+1}/${mv.total}`,next:()=>{timer=setTimeout(next,S.fast?900:1800);}});
  };
  next();
}

/* ---------------------------------------------------------------- the battle */
let timer=0,token=0;
function stopFight(){token++;clearTimeout(timer);timer=0;}
const wait=ms=>new Promise(done=>{timer=setTimeout(done,S.fast?ms/2.2:ms);});
/** Show a match (or a war match's duels): `m` {sides, ev, hp, max, w, me, kind, da, db, message}. */
function startFight(m,after,extra={}){
  stopFight();
  // the viewer's side on the left
  const flip=m.me===1;
  S.fight={m,after,flip,...extra};
  const root=S.dlg.querySelector('.pa-root');root.innerHTML=fightHTML();
  play(token);
}
function side(i){const f=S.fight;return f.flip?1-i:i;}       // a log side → the screen side (0 left)
function fightHTML(){
  const f=S.fight,m=f.m,L=m.sides[side(0)],R=m.sides[side(1)];
  const dots=(s,n)=>`<span class="pa-dots" data-dots="${s}">${Array.from({length:n},(_,i)=>`<i data-d="${i}"></i>`).join('')}</span>`;
  const title=f.title||({rank:'⚔️ Đấu xếp hạng',friend:'🤝 Giao hữu',npc:'🎯 Thử thách',spar:'🐾 Đấu tập',cup:'🏟️ Giải tuần'}[m.kind]||'⚔️ Đấu trường');
  return `<div class="pa-fight" data-kind="${esc(m.kind||'')}">
    <header class="pa-fight-head"><span class="pa-fight-title"><b>${esc(title)}</b>${f.sub?`<small>${esc(f.sub)}</small>`:''}</span>
      <button type="button" class="pa-ctl${S.fast?' on':''}" data-pa="fast" aria-label="Nhanh gấp đôi">⏩ ×2</button><button type="button" class="pa-ctl" data-pa="skip" aria-label="Bỏ qua">⏭</button></header>
    <div class="pa-plates"><div class="pa-plate l"><b data-no-translate>${esc(L.name)}</b>${dots('l',L.pets.length)}</div><div class="pa-vs">VS</div><div class="pa-plate r"><b data-no-translate>${esc(R.name)}</b>${dots('r',R.pets.length)}</div></div>
    <div class="pa-arena" aria-live="polite">
      <div class="pa-ground"></div>
      ${['l','r'].map(s=>`<div class="pa-side ${s}" data-side="${s}"><div class="pa-hud"><b class="pa-nm" data-no-translate></b><span class="pa-tags"></span><div class="pa-hp"><i></i><em></em></div><div class="pa-sh"></div></div><div class="pa-fig"></div></div>`).join('')}
      <div class="pa-fx"></div><div class="pa-banner" hidden></div><div class="pa-after" hidden></div>
    </div>
    <ol class="pa-feed" aria-label="Diễn biến"></ol>
  </div>`;
}
const $=sel=>S.dlg.querySelector(sel);
function anim(el,frames,ms,opt={}){try{return el?.animate?.(frames,{duration:S.fast?ms/2.2:ms,easing:'ease-out',...opt});}catch{return null;}}
function sound(kind){
  const s=S.env?.sound;if(!s||s.enabled===false)return;
  try{
    if(kind==='hit')s.pop?.();
    else if(kind==='crit'){s.tone?.(196,.12,.05);s.tone?.(130,.16,.04,.05,'square');}
    else if(kind==='skill')s.bell?.(880,0,.35,.02);
    else if(kind==='ko')s.tone?.(220,.3,.04,0,'triangle');
    else if(kind==='win')s.success?.();
    else if(kind==='lose')s.error?.();
  }catch{/* sound is optional */}
}
/** Put pet i of log side s on its spot. */
function enter(s,i,st){
  const sc=side(s)===0?'l':'r',f=S.fight.m.sides[s].pets[i];if(!f)return;
  const box=$(`.pa-side.${sc}`),fig=box.querySelector('.pa-fig');
  box.classList.remove('ko','win','rooted','casting');
  // 2.4.64: the fallen pet's KO tilt/fade is kept with fill:'forwards' on this same element — cancel it, or the next
  // pet walks in faded and tilted (players: "bé thứ 2 thứ 3 vào thì bị mờ")
  try{fig.getAnimations?.().forEach(a=>a.cancel());}catch{/* old browsers */}
  fig.innerHTML=pic(f,figSize());
  box.querySelector('.pa-nm').textContent=f.n;
  box.querySelector('.pa-tags').innerHTML=`${rk(f.r)}${elTag(f.e)}`;
  st.hp[s]=st.max[s][i];st.cur[s]=i;st.sh[s]=0;
  hp(s,st);shield(s,0);
  anim(box.querySelector('.pa-fig'),[{transform:`translateX(${sc==='l'?'-120':'120'}%)`,opacity:0},{transform:'translateX(0)',opacity:1}],420);
}
/** The pets' size on this stage (a phone in portrait has room for big ones, a landscape phone not). */
function figSize(){const a=$('.pa-arena'),h=a?.clientHeight||260,w=a?.clientWidth||340;return Math.round(Math.max(80,Math.min(170,h*.36,w*.34)));}
/** Where the pet of log side s stands in the stage: {x, y} its centre, {w, h} its size (px). */
function spot(s){
  const sc=side(s)===0?'l':'r',ar=$('.pa-arena')?.getBoundingClientRect(),el=$(`.pa-side.${sc} .pa-fig`),r=(el?.firstElementChild||el)?.getBoundingClientRect();
  if(!ar||!r)return {x:0,y:0,w:0,h:0};
  return {x:r.left-ar.left+r.width/2,y:r.top-ar.top+r.height*.55,w:r.width,h:r.height};
}
/** One line of the feed under the stage (newest first, four kept). */
function feed(html,cls=''){
  const ol=$('.pa-feed');if(!ol)return;
  const li=document.createElement('li');li.className=cls;li.innerHTML=html;ol.prepend(li);
  while(ol.children.length>4)ol.lastChild.remove();
}
/** A pet's name in the feed, coloured by its side of the screen (two pets of one name stay apart). */
const nameOf=(s,st)=>`<b class="pa-who ${side(s)===0?'l':'r'}" data-no-translate>${esc(S.fight.m.sides[s].pets[st.cur[s]]?.n||'')}</b>`;
function hp(s,st){
  const sc=side(s)===0?'l':'r',box=$(`.pa-side.${sc}`),m=st.max[s][st.cur[s]]||1,v=Math.max(0,st.hp[s]);
  const p=Math.round(v*100/m);
  const bar=box.querySelector('.pa-hp');bar.style.setProperty('--v',p+'%');bar.classList.toggle('low',p<30);
  box.querySelector('.pa-hp em').textContent=`${fmt(v)}/${fmt(m)}`;
}
function shield(s,n){const sc=side(s)===0?'l':'r';const el=$(`.pa-side.${sc} .pa-sh`);el.textContent=n?`🛡️ ${fmt(n)}`:'';$(`.pa-side.${sc}`).classList.toggle('shielded',n>0);}
function pop(s,text,cls=''){
  // beside the pet, toward the middle of the stage (never over the HUD); a skill's name up in the sky
  const fx=$('.pa-fx'),ar=$('.pa-arena'),W=ar?.clientWidth||340,H=ar?.clientHeight||260,p=spot(s),inward=p.x<W/2?1:-1;
  const y={skill:H*.1,heal:p.y-p.h*.3,endure:p.y-p.h*.45,charm:p.y+p.h*.05,shield:p.y+p.h*.1,ko:p.y-p.h*.2}[cls]??p.y-p.h*.15;
  const x=cls==='skill'?p.x:p.x+inward*p.w*.42;
  const el=document.createElement('span');el.className=`pa-pop ${cls}`;el.textContent=text;
  el.style.left=Math.round(Math.max(64,Math.min(W-64,x)))+'px';el.style.top=Math.round(Math.max(4,y))+'px';fx.append(el);
  setTimeout(()=>el.remove(),1200);
}
function burst(s,kind){
  // the elements' effects, drawn with CSS on the target's side (s: the target's log side)
  const fx=$('.pa-fx'),p=spot(s);
  const el=document.createElement('span');el.className=`pa-burst ${kind}`;el.style.left=Math.round(p.x)+'px';el.style.top=Math.round(p.y)+'px';
  const parts={hoa:'🔥',thuy:'💧',moc:'🍃',kim:'✨',tho:'🪨',crit:'💥',hit:'💢'}[kind]||'✨';
  const n=kind==='hit'?1:kind==='crit'?3:6;
  el.innerHTML=Array.from({length:n},(_,i)=>`<i style="--i:${i};--n:${n}">${parts}</i>`).join('');
  fx.append(el);setTimeout(()=>el.remove(),1100);
}
function projectile(from,kind){
  const fx=$('.pa-fx'),a=spot(from),b=spot(1-from),flip=b.x<a.x?' scaleX(-1)':'';
  const el=document.createElement('span');el.className=`pa-shot ${kind}`;el.style.left=Math.round(a.x)+'px';el.style.top=Math.round(a.y)+'px';
  el.textContent={hoa:'☄️',thuy:'🌊',moc:'🍃',kim:'✨',tho:'🪨'}[kind]||'✨';fx.append(el);
  anim(el,[{transform:`translate(-50%,-50%) scale(.7)${flip}`,opacity:.6},{transform:`translate(calc(-50% + ${Math.round(b.x-a.x)}px),calc(-50% + ${Math.round(b.y-a.y)}px)) scale(1.25)${flip}`,opacity:1}],440,{easing:'ease-in',fill:'forwards'});
  setTimeout(()=>el.remove(),S.fast?360:720);
}
function dot(s,i){const sc=side(s)===0?'l':'r';$(`[data-dots="${sc}"] [data-d="${i}"]`)?.classList.add('out');}
async function play(my){
  const f=S.fight,m=f.m;if(!m.ev){finish(my);return;}
  const st={hp:[0,0],max:m.max||[[],[]],cur:[0,0],sh:[0,0]};
  f.st=st;
  for(const e of m.ev){
    if(my!==token)return;
    // 2.4.64: one effect that throws (an element gone, an old browser) must not freeze the fight ("hay bị đứng")
    try{await step(e,st);}catch(err){console.warn('pet fight step',e&&e.k,err);}
    if(my!==token)return;
  }
  finish(my);
}
const SK={hoa:'☄️ Cầu lửa',tho:'🪨 Khiên đá',thuy:'🌊 Sóng nước',moc:'🍃 Dây leo',kim:'✨ Móng vàng'};
async function step(e,st){
  if(e.k==='in'){enter(e.s,e.i,st);feed(`🐾 ${nameOf(e.s,st)} ra sân`,'in');await wait(380);return;}
  if(e.k==='end')return;
  const att=e.s,tgt=1-e.s,asc=side(att)===0?'l':'r',tsc=side(tgt)===0?'l':'r';
  const aFig=$(`.pa-side.${asc} .pa-fig`),tFig=$(`.pa-side.${tsc} .pa-fig`),dir=asc==='l'?1:-1;
  if(e.k==='ko'){
    const box=$(`.pa-side.${side(e.s)===0?'l':'r'}`);box.classList.add('ko');dot(e.s,e.i);pop(e.s,'💫 Gục!','ko');sound('ko');feed(`💫 ${nameOf(e.s,st)} gục`,'ko');
    anim(box.querySelector('.pa-fig'),[{transform:'rotate(0) translateY(0)',opacity:1},{transform:`rotate(${side(e.s)===0?-80:80}deg) translateY(30%)`,opacity:.25}],520,{fill:'forwards'});
    await wait(620);return;
  }
  if(e.k==='miss'){
    anim(aFig,[{transform:'translateX(0)'},{transform:`translateX(${dir*38}%)`},{transform:'translateX(0)'}],300);
    anim(tFig,[{transform:'translateY(0)'},{transform:'translateY(-26%)'},{transform:'translateY(0)'}],320);
    pop(tgt,'Né!','miss');feed(`💨 ${nameOf(tgt,st)} né được`,'miss');await wait(STEP);return;
  }
  if(e.k==='sk'){
    $(`.pa-side.${asc}`).classList.add('casting');pop(att,SK[e.n]||'✨','skill');sound('skill');
    anim(aFig,[{transform:'scale(1)'},{transform:'scale(1.12)'},{transform:'scale(1)'}],340);
    await wait(260);
    $(`.pa-side.${asc}`).classList.remove('casting');
    if(e.n==='tho'){burst(att,'tho');}else projectile(att,e.n);
    await wait(200);
    burst(tgt,e.n);
  }else{
    anim(aFig,[{transform:'translateX(0)'},{transform:`translateX(${dir*55}%)`},{transform:'translateX(0)'}],300);
    await wait(150);
    burst(tgt,e.c?'crit':'hit');
  }
  // the blow lands
  anim(tFig,[{transform:'translateX(0)',filter:'brightness(1)'},{transform:`translateX(${dir*8}%)`,filter:'brightness(2.2)'},{transform:`translateX(${-dir*6}%)`},{transform:'translateX(0)',filter:'brightness(1)'}],260);
  if(e.c){const ar=$('.pa-arena');anim(ar,[{transform:'translate(0,0)'},{transform:'translate(4px,-3px)'},{transform:'translate(-4px,2px)'},{transform:'translate(0,0)'}],220);}
  if(e.ab){st.sh[tgt]=Math.max(0,st.sh[tgt]-e.ab);shield(tgt,st.sh[tgt]);pop(tgt,`🛡️ −${fmt(e.ab)}`,'shield');}
  st.hp[tgt]=e.h;hp(tgt,st);
  pop(tgt,`${e.c?'CHÍ MẠNG ':''}−${fmt(e.d)}`,e.c?'crit':'dmg');sound(e.c?'crit':'hit');
  if(e.x)pop(att,'💖 Mềm lòng','charm');
  if(e.e)pop(tgt,'🐶 Trụ lại!','endure');
  if(e.sh){st.sh[att]=e.sh;shield(att,e.sh);}
  if(e.he){st.hp[att]=e.hs;hp(att,st);pop(att,`+${fmt(e.he)}`,'heal');}
  feed(`${e.k==='sk'?`${SK[e.n]||'✨'}: `:e.c?'💥 ':''}${nameOf(att,st)} → ${nameOf(tgt,st)} −${fmt(e.d)}${e.he?` · +${fmt(e.he)} ❤️`:''}${e.e?' · 🐶 trụ lại':''}`,e.c?'crit':e.k);
  if(e.k==='sk'&&e.n==='moc')$(`.pa-side.${tsc}`).classList.add('rooted');
  else if(e.k==='hit'||e.k==='sk')$(`.pa-side.${asc}`).classList.remove('rooted');
  await wait(e.k==='sk'?STEP+150:STEP);
}
function skipFight(){
  const f=S.fight;if(!f)return;stopFight();
  const m=f.m,st=f.st||{hp:[0,0],max:m.max||[[],[]],cur:[0,0],sh:[0,0]};
  // the final picture: the last pet standing on each side, the dots of the fallen
  if(m.ev){
    const cur=[0,0];for(const e of m.ev)if(e.k==='in')cur[e.s]=e.i;
    for(const s of [0,1]){
      if(!m.sides[s].pets.length)continue;
      enter(s,cur[s],st);st.hp[s]=(m.hp?.[s]||[])[cur[s]]??0;hp(s,st);
      for(let i=0;i<m.sides[s].pets.length;i++)if(((m.hp?.[s]||[])[i]??1)<=0)dot(s,i);
      if(st.hp[s]<=0)$(`.pa-side.${side(s)===0?'l':'r'}`).classList.add('ko');
    }
  }
  finish(token);
}
function finish(my){
  if(my!==token)return;
  const f=S.fight,m=f.m,meSide=f.flip?1:0;
  if(!m.ev){for(const s of [0,1])if(m.sides[s].pets[0])enter(s,0,{hp:[0,0],max:[[1],[1]],cur:[0,0],sh:[0,0]});}
  const won=m.w===2?null:m.me==null?true:m.w===m.me,banner=$('.pa-banner');   // watching: the winner is cheered
  const text=m.w===2?'🤝 Hòa!':m.me==null?`🏆 ${m.sides[m.w].name} thắng!`:won?'🎉 Thắng rồi!':'💪 Thua rồi!';
  banner.hidden=false;banner.textContent=text;banner.className='pa-banner '+(m.w===2?'draw':won||m.me==null?'win':'lose');
  if(m.w!==2){
    const ws=side(m.w)===0?'l':'r',wf=m.sides[m.w].pets;
    const box=$(`.pa-side.${ws}`);const last=f.st?f.st.cur[m.w]:0;
    if(wf[last]&&!box.classList.contains('ko')){box.querySelector('.pa-fig').innerHTML=pic(wf[last],figSize(),'happy');box.classList.add('win');}
    if(won!==false)confetti();
  }
  sound(won===false?'lose':'win');
  for(const el of S.dlg.querySelectorAll('.pa-side'))el.classList.remove('rooted','casting');
  const d=m.me===0?m.da:m.me===1?m.db:0;
  const after=$('.pa-after');after.hidden=false;
  const again=f.after==='rank'?'⚔️ Đấu tiếp':f.after==='npc'?'🎯 Thử lại':'';
  const ranked=m.kind==='rank'&&m.me!=null;
  after.innerHTML=`${m.message&&!ranked?`<p class="pa-msg">${esc(m.message)}</p>`:''}${ranked?`<p class="pa-delta ${d>=0?'up':'down'}">🏆 ${d>=0?'+':''}${d} điểm</p>`:''}
    ${f.next?'':`<div class="pa-after-btns">${again?`<button type="button" class="btn primary big" data-pa="again">${again}</button>`:''}<button type="button" class="btn${again?'':' primary big'}" data-pa="done">${again?'Xong':'👌 Xong'}</button></div>`}`;
  if(f.next)f.next();
}
function confetti(){
  const fx=$('.pa-fx');const el=document.createElement('span');el.className='pa-confetti';
  const colors=['#ff6a3d','#f2b632','#4caf6a','#3d8bfd','#ff4fa3','#a259ff'];
  el.innerHTML=Array.from({length:26},(_,i)=>`<i style="--x:${(i*37)%100}%;--d:${(i%7)*0.08}s;--c:${colors[i%colors.length]};--r:${(i*53)%360}deg"></i>`).join('');
  fx.append(el);setTimeout(()=>el.remove(),2400);
}

/* ---------------------------------------------------------------- 🛡️ watching a war match: its duels one by one */
async function watchWar(rd,slot){
  let mv;
  try{mv=await post('war_match',{rd,slot,week:S.war?.week});}catch(e){S.flash={text:e.message,kind:'bad'};render();return;}
  let i=0,score=[0,0];
  const watching=++S.watch;   // a later watch (or closing the dialog) ends this one
  const next=async()=>{
    if(watching!==S.watch||!S.dlg?.open||(i&&!S.fight))return;
    if(i>=mv.duels.length){
      if(mv.over||i>=mv.total){const after=$('.pa-after');if(after)after.insertAdjacentHTML('beforeend',`<div class="pa-after-btns"><button type="button" class="btn primary big" data-pa="done">👌 Xong · ${score[0]}–${score[1]}</button></div>`);return;}
      // live: the next duel is shown when its time comes
      const at=mv.start+i*mv.duel_secs-Date.now()/1000;
      await new Promise(done=>{timer=setTimeout(done,Math.max(1500,Math.min(30000,at*1000)));});
      try{mv=await post('war_match',{rd,slot,week:S.war?.week});}catch{return;}
      next();return;
    }
    const d=mv.duels[i++];
    if(d.w===0)score[0]++;else if(d.w===1)score[1]++;
    const m={kind:'war',sides:d.sides,ev:d.ev,hp:d.hp,max:d.max,w:d.w,me:null,message:`Trận ${d.i+1}/${mv.total} · ${mv.a} ${score[0]}–${score[1]} ${mv.b}`};
    const go=()=>startFight(m,'war',{title:`🛡️ ${mv.a} – ${mv.b}`,sub:`Trận ${d.i+1}/${mv.total}`,next:()=>{timer=setTimeout(next,S.fast?900:1800);}});
    if(!d.ev){go();return;}
    go();
  };
  next();
}
