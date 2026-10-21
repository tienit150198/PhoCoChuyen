/** 🏁 Đường đua Bến Mây (game/racing.py; player #470 "Thêm độ xe để đua xe", owner 22/10 "độ xe này kia làm kĩ vào"):
 * tune your own motorbike or car at 🔧 Xưởng Tư Pít-tông (jr_tune_buy / jr_tune_fix, through the command queue), run
 * ⏱️ time trials, open and race ⚔️ async duels, read the week's 🏆 boards and replay a run leg by leg. Every rule, price
 * and time is the server's (POST /api/race/<op>: home, trial, challenge, accept, cancel, replay); this file shows the
 * page and sends the driver's choices. Opened with data-action="raceTrack" (🚗 Nhà xe's card, the menu).
 * Styles: /css/bank.css + /css/garage.css + /css/race.css. */
import {icon,escapeHTML as esc} from '../icons.js';
import {paint as sheetPaint} from './sheet-paint.js';

const S={dlg:null,env:null,home:null,tab:'tune',vid:'',track:'drag',fee:10,ch:null,run:null,replay:null,board:'race_drag_bike',busy:false,flash:null};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const xu=n=>`${fmt(n)} xu`;
const lc=s=>String(s||'').slice(0,1).toLowerCase()+String(s||'').slice(1);   // "Xe số Cub" → "xe số Cub" (ECU stays ECU)
const secs=ms=>`${Math.floor(ms/1000)},${String(ms%1000).padStart(3,'0')} giây`;
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const btn=(label,op,data={},cls='',why='')=>`<button type="button" class="btn ${cls}" data-rc="${op}"${attrs(data)}${S.busy||why?' disabled':''}${why?` title="${esc(why)}"`:''}>${label}</button>`;
const H=()=>S.home||{};
const R=()=>H().rules||{};
const cars=()=>H().garage?.cars||[];
const car=()=>cars().find(c=>c.id===S.vid)||cars()[0]||null;
const W=(slot,k)=>R().words?.[slot]?.[k]||k;
const TABS=[['tune','🔧 Độ xe'],['trial','⏱️ Chạy giờ'],['duel','⚔️ Tay đôi'],['board','🏆 Bảng tuần']];

let cssReady=null;
function link(href,key){
  return new Promise(done=>{
    if(document.querySelector(`link[data-${key}]`)){done();return;}
    const l=document.createElement('link');l.rel='stylesheet';l.href=globalThis.__mnlBoot?.asset?.(href)||href;l.setAttribute(`data-${key}`,'');
    l.onload=l.onerror=()=>done();document.head.append(l);setTimeout(done,1500);
  });
}
const ensureCss=()=>cssReady??=Promise.all([link('/css/bank.css','bk-css'),link('/css/garage.css','gr-css'),link('/css/race.css','rc-css')]);

function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet medium bk-sheet gr-sheet rc-sheet';d.setAttribute('aria-labelledby','rc-title');
  d.innerHTML='<div class="rc-root"></div>';
  document.body.append(d);
  d.addEventListener('click',e=>{
    if(e.target===d){d.close();return;}
    const el=e.target.closest('[data-rc]');if(!el||!d.contains(el)||el.disabled)return;
    e.preventDefault();onClick(el.dataset.rc,el.dataset);
  });
  d.addEventListener('close',()=>{S.flash=null;S.run=null;S.replay=null;});
  S.dlg=d;return d;
}
/** The choices the page starts from (the driver changes them): vừa everywhere, shifts on the line. */
const fresh=()=>({drag:{launch:'vua',shifts:['dung','dung','dung']},deo:{brakes:['vua','vua','vua','vua','vua']}});

export async function openRace(env,tab){
  S.env=env;S.ch??=fresh();
  const sheet=document.getElementById('sheet');if(sheet?.open)env.closeSheet();
  await ensureCss();
  const d=dialog();
  if(tab&&TABS.some(t=>t[0]===tab))S.tab=tab;
  if(!d.open){d.showModal();d.scrollTop=0;}
  render();await load();
}
export async function raceAction(action,data,el,env){
  if(action!=='raceTrack')return false;
  await openRace(env,data?.tab);return true;
}

async function load(){
  try{S.home=await S.env.api.post('/api/race/home',{},15000);if(!cars().some(c=>c.id===S.vid))S.vid=(cars().find(c=>c.id===H().garage?.ride)||cars()[0])?.id||'';}
  catch(e){S.flash={text:e.message||'Chưa mở được đường đua. Thử lại nhé.',kind:'bad'};}
  render();
}
/** A race op: the answer's state is adopted (the fee and the parts' wear are in the save), the page reloads. */
async function post(op,body){
  if(S.busy)return null;S.busy=true;render();
  try{const r=await S.env.api.post('/api/race/'+op,body,20000);
    if(r?.state&&typeof r.revision==='number')S.env.api.accept({state:r.state,revision:r.revision});
    S.flash=r?.message?{text:r.message,kind:'good'}:null;return r;}
  catch(e){S.flash={text:e.message||'Chưa gửi được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;if(op!=='replay')await load();else render();}
}
async function command(action,payload){
  S.busy=true;render();
  try{const r=await S.env.api.command(action,payload);S.flash={text:r?.message||'Xong.',kind:'good'};return r;}
  catch(e){S.flash=e.quiet?null:{text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};return null;}
  finally{S.busy=false;await load();}
}
const ask=(title,msg,label,money)=>S.env.confirmAction(title,msg,label,money);

async function onClick(op,data){
  const c=car();
  switch(op){
    case'close':S.dlg.close();return;
    case'garage':S.dlg.close();(await import('./garage.js')).openGarage(S.env,'mine');return;
    case'tab':S.tab=data.tab;S.flash=null;S.run=null;S.replay=null;render();S.dlg.querySelector('.rc-body')?.scrollTo?.(0,0);return;
    case'car':S.vid=data.id;S.run=null;render();return;
    case'track':S.track=data.track;S.run=null;render();return;
    case'fee':S.fee=Number(data.fee);render();return;
    case'board':S.board=data.board;render();return;
    case'pick':{const ch=S.ch[S.track];if(data.slot==='launch')ch.launch=data.v;else if(data.slot==='shift')ch.shifts[Number(data.i)]=data.v;else ch.brakes[Number(data.i)]=data.v;render();return;}
    case'buy':{if(!c)return;const m=c.mods.find(x=>x.id===data.mod),n=m?.next;if(!n)return;
      if(await ask(`Lắp ${lc(n.part)}?`,`🔧 Xưởng Tư Pít-tông lắp ${lc(m.name)} cấp ${n.stage} cho ${lc(c.name)}. Đồ đúng luật, có tem kiểm định. Lấy tiền mặt trong ví trước, thiếu thì lấy từ tài khoản.`,`Lắp · ${xu(n.price)}`,{cost:n.price,pocket:['wallet','account']}))
        await command('jr_tune_buy',{id:c.id,mod:m.id});return;}
    case'fix':{if(!c||!c.fix)return;
      if(await ask('Bảo dưỡng xe độ?',`Mọi món đã lắp trên ${lc(c.name)} mới lại như vừa ra xưởng.`,`Bảo dưỡng · ${xu(c.fix)}`,{cost:c.fix,pocket:['wallet','account']}))
        await command('jr_tune_fix',{id:c.id});return;}
    case'trial':{if(!c)return;const r=await post('trial',{track:S.track,vid:c.id,choices:S.ch[S.track]});if(r)S.run=r;render();return;}
    case'challenge':{if(!c)return;
      if(await ask('Mở lời thách đấu?',`Bạn chạy ${R().tracks?.[S.track]?.name||''} ngay bây giờ. Phí ${xu(S.fee)} được giữ lại tới khi có người đua; không ai nhận trong ${R().open_hours||24} giờ thì hoàn đủ.`,`Thách đấu · ${xu(S.fee)}`,{cost:S.fee,pocket:['wallet','account']})){
        const r=await post('challenge',{track:S.track,vid:c.id,fee:S.fee,choices:S.ch[S.track]});if(r)S.run=r;render();}return;}
    case'accept':{if(!c)return;const d=(H().others||[]).find(x=>x.id===data.id);if(!d)return;S.track=d.track;
      if(await ask('Nhận lời thách đấu?',`Bạn chạy ${R().tracks?.[d.track]?.name||''} bằng ${lc(c.name)} với cách chạy đang chọn ở trên. Phí ${xu(d.fee)}, người nhanh hơn lấy cả hũ trừ ${R().burn_pct||20}% phí sân.`,`Đua · ${xu(d.fee)}`,{cost:d.fee,pocket:['wallet','account']})){
        const r=await post('accept',{id:d.id,vid:c.id,choices:S.ch[d.track]});if(r?.duel){const rp=await post('replay',{id:d.id});if(rp)S.replay=rp;render();}}return;}
    case'cancel':await post('cancel',{id:data.id});return;
    case'replay':{const r=await post('replay',{id:data.id});if(r){S.replay=r;render();S.dlg.querySelector('.rc-replay')?.scrollIntoView?.({block:'nearest'});}return;}
    case'unreplay':S.replay=null;render();return;
  }
}

/* ---- rendering ---- */
function render(){
  if(!S.dlg)return;
  sheetPaint(S.dlg.querySelector('.rc-root'),page(),'.rc-body');
  S.dlg.setAttribute('aria-busy',String(S.busy));
}
function head(){
  return `<header class="sheet-head bk-head">${'<span class="gr-logo rc-logo" aria-hidden="true">🏁</span>'}
    <div class="grow"><span class="eyebrow">ĐƯỜNG ĐUA BẾN MÂY · TUẦN ${esc(String(H().week||'').split('-W')[1]||'')}</span><h2 id="rc-title">Độ xe &amp; đua xe</h2><p>Xe máy đua với xe máy, ô tô đua với ô tô</p></div>
    <button class="icon-btn" type="button" data-rc="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
}
const flash=()=>`<p class="bk-flash ${S.flash?.kind||''}" role="status" aria-live="polite">${S.flash?esc(S.flash.text):''}</p>`;
function page(){
  const note=(t,p)=>head()+`<div class="sheet-body bk rc-body">${flash()}<section class="bk-card bk-center"><div class="bk-big-emoji" aria-hidden="true">🏁</div><h3>${t}</h3><p>${p}</p></section></div>`;
  if(!S.home)return note('Đang mở cổng đường đua…','Chờ một chút nhé.');
  if(!H().garage?.story)return note('Đường đua chỉ có trong chế độ hành trình','Vào hành trình, sắm một chiếc xe máy hoặc ô tô rồi quay lại nhé.');
  if(!cars().length)return note('Chưa có xe để độ','Xe đạp không vào đường đua. Mua một chiếc xe máy hoặc ô tô ở 🚗 Nhà xe rồi quay lại nhé.')
    .replace('</section>',`<div class="bk-actions">${btn('🚗 Mở Nhà xe','garage',{},'primary')}</div></section>`);
  const tabs=`<div class="segmented bk-tabs rc-tabs" role="tablist" aria-label="Mục đường đua">${TABS.map(([id,l])=>`<button type="button" role="tab" aria-selected="${S.tab===id}" class="${S.tab===id?'active':''}" data-rc="tab" data-tab="${id}">${esc(l)}</button>`).join('')}</div>`;
  const off=H().off?'<p class="bk-alert warn">Đường đua tạm đóng: chưa chạy được lượt mới. Lời thách đấu đang mở vẫn hủy được.</p>':'';
  const inner=S.tab==='tune'?tuneView():S.tab==='trial'?trialView():S.tab==='duel'?duelView():boardView();
  return head()+`<div class="sheet-body bk rc-body">${flash()}${off}${tabs}${S.tab==='board'?'':carPicker()}${inner}</div>`;
}
function carPicker(){
  return `<div class="rc-cars" role="radiogroup" aria-label="Chọn xe">${cars().map(c=>`<button type="button" role="radio" aria-checked="${c.id===car()?.id}" class="rc-car${c.id===car()?.id?' on':''}" data-rc="car" data-id="${esc(c.id)}"${S.busy?' disabled':''}><span aria-hidden="true">${c.emoji}</span><b>${esc(c.name)}</b><small>Chỉ số đua ${fmt(c.perf.pi)}${c.broken?' · đang hỏng':''}</small></button>`).join('')}</div>`;
}
function stats(p){
  const row=(l,v)=>`<span><small>${l}</small><b>${v}</b></span>`;
  return `<p class="rc-stats">${row('Mã lực',fmt(p.hp))}${row('Cân nặng',`${fmt(p.kg)} kg`)}${row('Bám đường',fmt(p.grip))}${row('Phanh',fmt(p.brake))}${row('Bám đề-pa',fmt(p.launch))}${row('Độ chắc',fmt(p.firm))}</p>`;
}
const bar=w=>`<span class="rc-wear" style="--w:${Math.max(0,Math.min(100,w))}%" aria-label="Độ mới ${w}%"><i></i></span>`;

/* 🔧 The parts of the vehicle chosen: stage, wear, the next stage and its price, the full service. */
function tuneView(){
  const c=car();if(!c)return '';
  const fx=R().fx||{},hand=[c.fx?.may?`💻 Map tay +${fx.power}% mã lực · còn ${c.fx.may} lượt`:'',c.fx?.gam?`🔩 Chỉnh gầm +${fx.grip} bám · còn ${c.fx.gam} lượt`:''].filter(Boolean);
  const rows=c.mods.map(m=>`<li class="rc-mod"><div class="rc-mod-top"><span class="rc-mod-emoji" aria-hidden="true">${m.emoji}</span><div class="grow"><b>${esc(m.name)}</b><small>${m.stage?`Cấp ${m.stage}/3 · ${esc(m.part)}`:'Đồ zin'}</small></div>${m.stage?bar(m.wear):''}</div>
    ${m.next?btn(`Lắp ${lc(esc(m.next.part))} · ${xu(m.next.price)}`,'buy',{mod:m.id},'ghost small',c.broken?'Xe đang hỏng':''):'<small class="rc-max">Đã độ tới cấp cao nhất</small>'}</li>`).join('');
  return `<section class="bk-card"><h3>${c.emoji} ${esc(c.name)}</h3><p class="rc-pi">Chỉ số đua <b>${fmt(c.perf.pi)}</b></p>${stats(c.perf)}
    ${hand.length?`<p class="hs-chips">${hand.map(x=>`<span>${esc(x)}</span>`).join('')}</p>`:''}
    <ul class="rc-mods">${rows}</ul>
    ${c.fix?`<div class="bk-actions">${btn(`🧰 Bảo dưỡng đồ độ · ${xu(c.fix)}`,'fix',{},'primary',c.broken?'Xe đang hỏng':'')}</div>`:''}
    <p class="bk-hint">🔧 Xưởng Tư Pít-tông chỉ lắp đồ đúng luật. Mỗi lượt đua làm mòn đồ độ, lốp mòn nhanh nhất; đồ mòn thì yếu đi. Thợ độ xe là người chơi ở 🛎️ Phố dịch vụ còn chỉnh map tay và khung gầm cho bạn.</p></section>`;
}

/* The driver's choices for a track: drag (launch + three shifts) or đèo (a braking point at each corner). */
function choices(track){
  const ch=S.ch[track],opt=(slot,i,v,on)=>`<button type="button" class="rc-opt${on?' on':''}" role="radio" aria-checked="${on}" data-rc="pick" data-slot="${slot}" data-i="${i}" data-v="${v}"${S.busy?' disabled':''}>${esc(W(slot,v))}</button>`;
  const line=(label,slot,i,list,cur)=>`<div class="rc-line"><span>${esc(label)}</span><div class="rc-opts" role="radiogroup" aria-label="${esc(label)}">${list.map(v=>opt(slot,i,v,cur===v)).join('')}</div></div>`;
  if(track==='drag')return line('Đề-pa','launch',0,['em','vua','manh'],ch.launch)+ch.shifts.map((v,i)=>line(`Lên số ${i+2}`,'shift',i,['som','dung','tre'],v)).join('');
  return (R().corners||[]).map((k,i)=>line(k.name,'brake',i,['som','vua','muon'],ch.brakes[i])).join('');
}
function trackPick(){
  return `<div class="segmented rc-tracks" role="tablist" aria-label="Đường đua">${Object.entries(R().tracks||{}).map(([id,t])=>`<button type="button" role="tab" aria-selected="${S.track===id}" class="${S.track===id?'active':''}" data-rc="track" data-track="${id}">${t.emoji} ${esc(t.name)}</button>`).join('')}</div>`;
}
const notes=()=>`<details class="rc-notes"><summary>📒 Sổ tay đường đua</summary><ul>${(R().notes||[]).map(n=>`<li>${esc(n)}</li>`).join('')}</ul></details>`;
function legs(run,title=''){
  if(!run)return '';
  return `<div class="rc-run">${title?`<h4>${title}</h4>`:''}<ol class="rc-legs">${run.legs.map(l=>`<li class="${l.ok?'ok':'miss'}"><span>${esc(l.label)}</span><small>${esc(l.note)}</small><b>${secs(l.ms)}</b></li>`).join('')}</ol>
    <p class="rc-total">⏱️ ${secs(run.ms)}${run.luck?` <small>(mặt đường ${run.luck>0?'+':''}${String(run.luck).replace('.',',')}‰)</small>`:''}</p></div>`;
}

/* ⏱️ A time trial: the fee, today's count, the week's best, the last run leg by leg. */
function trialView(){
  const c=car();if(!c)return '';
  const fee=R().trial_fee?.[S.track]||0,today=H().today||{},left=Math.max(0,(R().trial_day||20)-(today.trials||0));
  const best=H().best?.[`race_${S.track}_${c.cls}`];
  const why=H().account===false?'Cần tài khoản':c.broken?'Xe đang hỏng':left?'':'Hết lượt hôm nay';
  return `<section class="bk-card">${trackPick()}<p class="bk-hint">${[esc(R().tracks?.[S.track]?.where||''),`phí sân ${xu(fee)} một lượt`,`hôm nay chạy được thêm ${fmt(left)} lượt`,best?`kỷ lục tuần của bạn ${secs(best.ms)} (hạng ${best.rank})`:''].filter(Boolean).join(' · ')}</p>
    ${stats(c.perf)}<div class="rc-choices">${choices(S.track)}</div>${notes()}${guestNote()}
    <div class="bk-actions">${btn(`🏁 Chạy · ${xu(fee)}`,'trial',{},'primary big',why)}</div>
    ${S.run?.run?legs(S.run.run,'Lượt vừa chạy'):''}</section>`;
}

/* 👤 A guest may tune and look, but runs and duels go on the boards by name. */
const guestNote=()=>H().account===false?'<p class="bk-alert warn">Tạo tài khoản để chạy tính giờ và đua tay đôi nhé.</p>':'';

/* ⚔️ Duels: open one (the fee escrowed), race someone's (same class, close numbers), cancel yours, the results. */
function duelView(){
  const c=car();if(!c)return '';
  const old=H().old_enough,cls=c.cls,gap=R().pi_gap||20;
  const name=t=>`${R().tracks?.[t]?.emoji||''} ${esc(R().tracks?.[t]?.name||'')}`;
  const mine=(H().open||[]).map(d=>`<li class="rc-duel"><span>${name(d.track)} · ${xu(d.fee)} · ${secs(d.a.ms)}</span>${btn('Hủy','cancel',{id:d.id},'ghost small')}</li>`).join('');
  const others=(H().others||[]).map(d=>{const fit=d.cls===cls&&c.perf.pi>=d.a.pi*(100-gap)/100&&c.perf.pi<=d.a.pi*(100+gap)/100;
    return `<li class="rc-duel"><span><b>${esc(d.a_name)}</b> · ${esc(d.a_vehicle)} · ${name(d.track)} · ${xu(d.fee)}<small>Chỉ số đua ${fmt(d.a.pi)}</small></span>${btn('Đua','accept',{id:d.id},'primary small',H().account===false?'Cần tài khoản':!old?'Tài khoản chưa đủ ngày':d.cls!==cls?'Khác hạng xe':!fit?`Chênh quá ${gap}% chỉ số đua`:c.broken?'Xe đang hỏng':'')}</li>`;}).join('');
  const recent=(H().recent||[]).map(d=>{const me=d.me==='a'?d.a:d.b,them=d.me==='a'?d.b:d.a,who=d.me==='a'?d.b_name:d.a_name;
    const res=d.status==='tie'?'🤝 Hòa':d.won?`🏆 Thắng +${xu(d.prize)}`:'😤 Thua';
    return `<li class="rc-duel"><span>${res} · ${esc(who||'')} · ${name(d.track)}<small>${secs(me?.ms||0)} – ${secs(them?.ms||0)}</small></span>${btn('Xem lại','replay',{id:d.id},'ghost small')}</li>`;}).join('');
  return `<section class="bk-card"><h3>Mở lời thách đấu</h3>${trackPick()}
    <div class="rc-fees" role="radiogroup" aria-label="Phí vào cửa">${(R().fees||[]).map(f=>`<button type="button" role="radio" aria-checked="${S.fee===f}" class="rc-opt${S.fee===f?' on':''}" data-rc="fee" data-fee="${f}">${xu(f)}</button>`).join('')}</div>
    <div class="rc-choices">${choices(S.track)}</div>${notes()}
    ${H().account===false?guestNote():old?'':`<p class="bk-alert warn">Đua tay đôi mở cho tài khoản từ ${fmt(R().account_days||3)} ngày trở lên.</p>`}
    <div class="bk-actions">${btn(`⚔️ Thách đấu · ${xu(S.fee)}`,'challenge',{},'primary',H().account===false?'Cần tài khoản':!old?'Tài khoản chưa đủ ngày':c.broken?'Xe đang hỏng':'')}</div>
    <p class="bk-hint">Hai bên cùng phí. Người nhanh hơn lấy cả hũ trừ ${fmt(R().burn_pct||20)}% phí sân; hòa thì hoàn phí. Không cược thêm. Mỗi ngày nhận tối đa ${fmt(R().duel_day||10)} lời thách đấu, cùng một người tối đa ${fmt(R().pair_day||2)} trận.</p></section>
    ${mine?`<section class="bk-card"><h3>Lời thách đấu của bạn</h3><ul class="rc-list">${mine}</ul></section>`:''}
    <section class="bk-card"><h3>Đang chờ người đua</h3>${others?`<ul class="rc-list">${others}</ul><p class="bk-hint">Nhận đua là chạy ngay với cách chạy bạn đang chọn ở trên cho đường đua đó.</p>`:'<p class="bk-hint">Chưa có lời thách đấu nào. Mở một lời đi!</p>'}</section>
    ${recent?`<section class="bk-card"><h3>Trận gần đây</h3><ul class="rc-list">${recent}</ul></section>`:''}${replayView()}`;
}
function replayView(){
  const r=S.replay;if(!r)return '';
  return `<section class="bk-card rc-replay"><h3>🎬 Xem lại · ${esc(R().tracks?.[r.track]?.name||'')}</h3>${r.runs.map(x=>legs(x.run,`${x.mine?'Bạn':'Đối thủ'} · ${esc(x.vehicle||'')}`)).join('')}
    <div class="bk-actions">${btn('Đóng','unreplay',{},'ghost small')}</div></section>`;
}

/* 🏆 The week's boards (each player's best time trial) and who holds their titles. */
function boardView(){
  const ids=Object.keys(H().boards||{}),cls=R().classes||{},tr=R().tracks||{};
  const label=id=>{const [,t,c]=id.split('_');return `${tr[t]?.emoji||''} ${tr[t]?.name||t} · ${cls[c]?.name||c}`;};
  const rows=(H().boards?.[S.board]||[]).map(r=>`<li class="rc-row${r.me?' me':''}"><span class="rc-rank">${r.rank}</span><span class="grow"><b>${esc(r.name)}</b><small>${esc(r.vehicle)}</small></span><b>${secs(r.ms)}</b></li>`).join('');
  const wk=H().weekly?.[S.board],holders=(wk?.tiers||[]).map(t=>`<p class="rc-title">${t.emoji} <b>${esc(t.name)}</b>: <span>${t.holders.length?t.holders.map(h=>esc(h.name)).join(', '):'chưa ai'}</span></p>`).join('');
  return `<section class="bk-card"><div class="rc-boards" role="tablist" aria-label="Bảng xếp hạng">${ids.map(id=>`<button type="button" role="tab" aria-selected="${S.board===id}" class="rc-opt${S.board===id?' on':''}" data-rc="board" data-board="${id}">${esc(label(id))}</button>`).join('')}</div>
    ${holders?`<div class="rc-titles">${holders}<small>Danh hiệu tuần cập nhật mỗi ngày, chốt sáng thứ Hai.</small></div>`:''}
    ${rows?`<ol class="rc-board">${rows}</ol>`:'<p class="bk-hint">Tuần này chưa ai chạy tính giờ ở đây. Ghi tên đầu tiên đi!</p>'}
    <p class="bk-hint">Mỗi người tính lượt chạy nhanh nhất trong tuần. Top 3 giữ danh hiệu tuần.</p></section>`;
}
/** Tests only (tests/race-track-ui.mjs): the page state and its markup. */
export const _view={S,page};
