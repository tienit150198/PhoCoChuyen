/** Thợ dầu khí — an offshore technician on giàn Hải Âu (server: game/careers/oil.py).
 * One screen per job of the hitch: the helicopter (the soft bag on the scale, the survival gear, the HUET question),
 * the arrival (T-card, the cabin's door sign, the alarm tones), the toolbox talk (PPE, bump test, hazards), the permit
 * (permit type, the permit board, a red lock on every isolation point, bleed, prove zero, the gas reading), rounds
 * (gauges against their limits, areas to look at), the alarm (tone, route, station), storm lashing, the handover and
 * the shore day (the family's requests: ask, send what you decide, say no kindly). ✋ Dừng việc is always on screen.
 * The awkward people come through the air crew's encounter card (air_kit.js oddCard), answered in your own words.
 * Everything is decided on the server; one tap sends one command. Layout: street_kit.css + oil.css. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,tile,pane,introCard,deskCard,askCard,bottom,kitActions,act,kitInput} from './street_kit.js';
import * as air from './air_kit.js';

const BAD='⚠️ ';
const isBad=s=>typeof s==='string'&&s.startsWith(BAD);
const AIR={id:'oil',odd:'dk_odd',rest:'dk_rest',role:'KỸ THUẬT VIÊN',role_down:'TẬP SỰ'};
const ppeOf=(x,k)=>(cc(x).ppe||[]).find(p=>p.id===k)||{name:k,emoji:'🦺'};
const alarm=(x,k)=>(cc(x).alarms||[]).find(a=>a.id===k)||{name:k,tone:'',emoji:'📯'};
const hz=(x,k)=>(cc(x).hazards||{})[k]||{name:k,emoji:'⚠️'};

/* ------------------------------------------------------------ the hitch bar and the stop button */
function hitchBar(x){
  const d=data(x),h=d.hitch||{},m=d.mod||{};
  const home=h.home_in?` · về bờ sau ${h.home_in} ngày`:'';
  const sum=`<span class="sk-sky" aria-hidden="true">${x.esc(m.emoji||'🌤️')}</span><b>${x.esc(h.label||'')}</b>`;
  return `<div class="sk-day dk-hitch">${pane(x,`hitch-${x.room.day}`,sum,`<small>${x.esc(m.label||'')}: ${x.esc(m.hint||'')}${x.esc(home)}</small>${air.record(x)}`,false,'grow')}
    ${act(x,'❔','intro',{},'ghost small sk-help',' aria-label="Giới thiệu nghề"')}</div>`;
}
/** ✋ Stop-work authority: always one tap away on the rig; the reasons open under it. */
function stopBox(t,x){
  if(!['ptw','round','drill','secure','toolbox'].includes(t.kind)||t.worked||t.status==='completed')return '';
  const open=x.ui.stop===t.id,used=(t.stops||[]).length;
  const reasons=Object.entries(cc(x).stop_reasons||{}).map(([k,l])=>x.cmd(x.esc(l),'dk_stop',{task:t.id,reason:k},'small ghost dk-reason')).join('');
  return `<section class="card dk-stop"><div class="row spread"><div><b>✋ Quyền dừng việc</b><small class="muted"> · ai cũng có, không bị trách${used?` · đã dừng ${used} lần`:''}</small></div>
    ${act(x,open?'Đóng':'✋ Dừng việc','stopOpen',{task:t.id},open?'small ghost':'small danger dk-stop-go')}</div>${open?`<div class="dk-reasons">${reasons}</div>`:''}</section>`;
}
function reportBox(t,x){
  if(!t.can_report||t.nearmiss)return '';
  return `<section class="card dk-nm"><p class="small">Có chuyện suýt xảy ra ở việc này. Ghi lại để cả giàn học, người báo không bị phạt.</p>${x.cmd('📝 Báo suýt sự cố','dk_nearmiss',{task:t.id},'primary full dk-nm-go')}</section>`;
}
/** Who gave the job, in one compact line (the opening folds under it). */
function who(t,x){
  const w=x.npc(t.npc);
  return `<article class="card dk-who"><div class="row">${x.portrait(w,40)}<div class="grow"><b>${x.esc(w.display_name)}</b><small class="muted"> · ${x.esc(w.role||'')}</small>
    ${pane(x,`open-${t.id}`,`<span class="small">💬 ${x.esc(t.opening.length>70?t.opening.slice(0,68)+'…':t.opening)}</span>`,`<p class="small">${x.esc(t.opening)}</p>`,false,'dk-open')}</div></div></article>`;
}
const reading=(x,label,s)=>s?`<p class="dk-read ${isBad(s)?'bad':s.startsWith('Đã xử lý')?'fixed':'ok'}"><b>${x.esc(label)}</b> ${x.esc(isBad(s)?s.slice(BAD.length):s)}</p>`:'';

/* ------------------------------------------------------------ the helicopter out */
function heliPanel(t,x){
  const n=t.needs||{};
  if(n.cancel)return `<section class="card dk-board"><h4>🌀 Áp thấp gần bờ</h4><p>Bảng giờ bay: <b>HỦY CHUYẾN</b>. Trực thăng không bay khi có bão. Nghe thông báo rồi về nhà chờ.</p></section>`;
  const items=(cc(x).bag||[]).filter(b=>(n.bag||[]).includes(b.id)).sort((a,b)=>n.bag.indexOf(a.id)-n.bag.indexOf(b.id));
  const out=t.bag_out||[],kg=t.bag_kg||0,over=kg>n.limit;
  const bag=items.map(b=>tile(x,'dk_bag',{task:t.id,item:b.id},`<span class="tile-emoji">${x.esc(b.emoji)}</span><b>${x.esc(b.name)}</b><small>${String(b.kg).replace('.',',')} kg${out.includes(b.id)?' · để ở nhà':''}</small>`,out.includes(b.id)?'selected dk-out':'')).join('');
  const gear=(cc(x).gear||[]).map(g=>tile(x,'dk_gear',{task:t.id,item:g.id},`<span class="tile-emoji">${x.esc(g.emoji)}</span><b>${x.esc(g.name)}</b><small>${x.esc(g.note)}</small>`,(t.gear||[]).includes(g.id)?'selected':'')).join('');
  const q=t.quizq;
  const quiz=q?`<section class="card dk-quiz"><h4>🎬 Video thoát hiểm trực thăng</h4><p>${x.esc(q.text)}</p>${t.quiz?`<p class="small muted">Đã trả lời.</p>`:`<div class="sk-opts">${q.options.map(o=>x.cmd(`<span class="sk-opt-label">${x.esc(o.label)}</span>`,'dk_quiz',{task:t.id,answer:o.id},'sk-opt')).join('')}</div>`}</section>`:'';
  const delay=n.delay?`<p class="dk-read ${t.waited?'ok':'bad'}"><b>📢 Loa cảng:</b> chuyến hoãn ${n.delay} phút vì ${n.wx==='fog'?'sương mù':'gió giật'}.${t.waited?' Đã nghe, đang chờ ở phòng chờ.':''}</p>`:'';
  return `${delay}<section class="card dk-bag"><div class="row spread"><h4>🎒 Túi mềm lên trực thăng</h4><span class="tag ${over?'danger':'green'}">${String(kg).replace('.',',')}/${n.limit} kg</span></div>
    <p class="small muted">Chạm một món để để nó ở nhà. Cảng soi túi: đồ cấm bị giữ lại, quá ký phải bỏ bớt.</p><div class="tile-grid">${bag}</div></section>
    <section class="card dk-gear"><h4>🦺 Đồ cứu sinh</h4><div class="tile-grid">${gear}</div></section>${quiz}`;
}
function heliSteps(t,x){
  const n=t.needs||{};
  if(n.cancel)return {steps:[{ok:null,label:'Nghe thông báo hủy chuyến',go:{cmd:'dk_wait',payload:{task:t.id},label:'📢 Nghe thông báo'}}],final:null};
  const steps=[{ok:(t.bag_out||[]).length&&(t.bag_kg||0)<=n.limit?true:null,label:`Soạn túi: không đồ cấm, tối đa ${n.limit} kg`,go:{sel:'.dk-bag .tile-grid',label:'🎒 Xem lại túi'}}];
  for(const g of cc(x).gear||[])steps.push({ok:(t.gear||[]).includes(g.id)?true:null,label:g.name,go:{cmd:'dk_gear',payload:{task:t.id,item:g.id},label:`${x.esc(g.emoji)} ${x.esc(g.name)}`}});
  steps.push({ok:t.quiz?true:null,label:'Trả lời câu hỏi thoát hiểm',go:{sel:'.dk-quiz .sk-opts',label:'🎬 Trả lời câu hỏi'}});
  if(n.delay)steps.push({ok:t.waited?true:null,label:'Chuyến hoãn: chờ ở phòng chờ',go:{cmd:'dk_wait',payload:{task:t.id},label:'📢 Nghe thông báo, ngồi chờ'}});
  return {steps,final:{label:'🚁 LÊN TRỰC THĂNG',go:finalGo(steps,'dk_board',{task:t.id}),ready:!!t.quiz&&(!n.delay||t.waited)}};
}

/* ------------------------------------------------------------ arrival */
function inductPanel(t,x){
  const n=t.needs||{},st=cc(x).stations||{};
  const door=`<section class="card dk-door"><h4>🚪 Biển cửa phòng ${n.room}</h4><p class="dk-sign">PHÒNG ${n.room} · ĐIỂM TẬP TRUNG: <b>XUỒNG ${x.esc(n.station)}</b></p>
    <div class="row wrap">${Object.entries(st).map(([k,l])=>x.cmd(`🛶 ${x.esc(l)}`,'dk_station',{task:t.id,station:k},t.muster===k?'small primary':'small ghost')).join('')}</div></section>`;
  const poster=(cc(x).alarms||[]).map(a=>`<li><span aria-hidden="true">${x.esc(a.emoji)}</span><div><b>${x.esc(a.tone)}</b><small>${x.esc(a.name)}: ${x.esc(a.do)}</small></div></li>`).join('');
  const tones=(n.tones||[]).map(k=>{const a=alarm(x,k),done=(t.matched||{})[k];
    return `<li class="dk-tone"><p><b>🔊 ${x.esc(a.tone)}</b>${done?` → ${x.esc(alarm(x,done).name)} ✅`:''}</p>${done?'':`<div class="row wrap">${(cc(x).alarms||[]).map(b=>x.cmd(x.esc(b.name),'dk_tone',{task:t.id,tone:k,pick:b.id},'small ghost')).join('')}</div>`}</li>`;}).join('');
  const tcard=t.tcard?'<p class="dk-read ok">🪪 Thẻ đã ở cột “Trên giàn”.</p>':x.cmd('🪪 Gắn thẻ lên bảng đếm người','dk_tcard',{task:t.id},'ghost full');
  return `<section class="card dk-pob"><h4>📋 Bảng đếm người (POB)</h4>${tcard}</section>${door}
    <section class="card dk-tones"><h4>📯 Tiếng còi của giàn</h4>${pane(x,'poster','📜 Bảng tiếng còi ở chân cầu thang',`<ul class="dk-list">${poster}</ul>`,false)}<ul class="dk-list">${tones}</ul></section>`;
}
function inductSteps(t,x){
  const n=t.needs||{},m=t.matched||{};
  const steps=[{ok:t.tcard||null,label:'Gắn thẻ lên bảng đếm người',go:{cmd:'dk_tcard',payload:{task:t.id},label:'🪪 Gắn thẻ'}},
    {ok:t.muster?true:null,label:'Nhận xuồng cứu sinh của phòng mình',go:{sel:'.dk-door .row',label:'🚪 Xem biển cửa phòng'}},
    {ok:(n.tones||[]).every(k=>m[k])?true:null,label:'Nhớ ba tiếng còi',go:{sel:'.dk-tones .dk-tone .row',label:'📯 Ghép tiếng còi'}}];
  return {steps,final:{label:'🧳 CẤT TÚI, VÀO CA',go:finalGo(steps,'dk_settle',{task:t.id}),ready:!!t.muster&&(n.tones||[]).every(k=>m[k])}};
}

/* ------------------------------------------------------------ the toolbox talk */
function toolboxPanel(t,x){
  const n=t.needs||{},ppe=(cc(x).ppe||[]).map(p=>tile(x,'dk_ppe',{task:t.id,item:p.id},`<span class="tile-emoji">${x.esc(p.emoji)}</span><b>${x.esc(p.name)}</b>`,(t.ppe||[]).includes(p.id)?'selected':'')).join('');
  const mon=t.bumped==='pass'?'<p class="dk-read ok">📟 Máy đo đã thử khí mẫu: đạt.</p>':t.bumped==='fail'?`<p class="dk-read bad">📟 Kênh H₂S không phản ứng.</p>${x.cmd('🔁 Đổi máy dự phòng','dk_swap',{task:t.id},'ghost full')}`
    :x.cmd('📟 Thử khí mẫu (bump test)','dk_bump',{task:t.id},'ghost full');
  const haz=(n.hazards||[]).map(h=>{const z=hz(x,h);return tile(x,'dk_hazard',{task:t.id,hazard:h},`<span class="tile-emoji">${x.esc(z.emoji)}</span><b>${x.esc(z.name)}</b>`,(t.picked||[]).includes(h)?'selected':'');}).join('');
  return `<section class="card"><h4>🗣️ Việc hôm nay</h4><p>${x.esc(n.storm?'Chằng buộc boong trước bão: gió giật, sàn trơn, làm trên cao.':t.opening)}</p></section>
    <section class="card dk-ppe"><h4>🦺 Đồ bảo hộ của cả ca</h4><div class="tile-grid">${ppe}</div></section>
    <section class="card dk-mon"><h4>📟 Máy đo khí cá nhân</h4>${mon}</section>
    <section class="card dk-haz"><h4>⚠️ Mối nguy của việc hôm nay</h4><p class="small muted">Chọn những mối nguy có thật ở việc này để cả ca cùng nói cách phòng.</p><div class="tile-grid">${haz}</div></section>
    <section class="card">${t.remind?'<p class="dk-read ok">✋ Đã nhắc quyền dừng việc.</p>':x.cmd('✋ Nhắc cả ca quyền dừng việc','dk_remind',{task:t.id},'ghost full')}</section>`;
}
function toolboxSteps(t,x){
  const steps=[];
  const miss=(cc(x).ppe||[]).filter(p=>!(t.ppe||[]).includes(p.id));
  steps.push({ok:miss.length?null:true,label:'Đủ đồ bảo hộ',note:`${(cc(x).ppe||[]).length-miss.length}/${(cc(x).ppe||[]).length}`,go:miss[0]?{cmd:'dk_ppe',payload:{task:t.id,item:miss[0].id},label:`${x.esc(miss[0].emoji)} ${x.esc(miss[0].name)}`}:null});
  steps.push({ok:t.bumped==='pass'?true:t.bumped==='fail'?false:null,label:'Thử máy đo khí',go:t.bumped==='fail'?{cmd:'dk_swap',payload:{task:t.id},label:'🔁 Đổi máy dự phòng'}:{cmd:'dk_bump',payload:{task:t.id},label:'📟 Thử khí mẫu'}});
  steps.push({ok:(t.picked||[]).length?true:null,label:'Nói các mối nguy của việc hôm nay',go:{sel:'.dk-haz .tile-grid',label:'⚠️ Chọn mối nguy'}});
  steps.push({ok:t.remind||null,label:'Nhắc quyền dừng việc',go:{cmd:'dk_remind',payload:{task:t.id},label:'✋ Nhắc quyền dừng việc'}});
  return {steps,final:{label:'✍️ KẾT THÚC BUỔI HỌP',go:finalGo(steps,'dk_talk',{task:t.id}),ready:true}};
}

/* ------------------------------------------------------------ maintenance under a permit */
function ptwPanel(t,x){
  const j=t.job||{},p=cc(x).permits||{},read=t.read||{};
  const card=`<section class="card dk-job"><div class="row spread"><h4>📋 ${x.esc(j.tag||'')}</h4>${t.permit?`<span class="tag green">${x.esc(p[t.permit]?.emoji||'')} ${x.esc(p[t.permit]?.name||'')}</span>`:''}</div><p>${x.esc(j.work||'')}</p></section>`;
  if(!t.permit){
    const tiles=Object.entries(p).map(([k,v])=>tile(x,'dk_permit',{task:t.id,permit:k},`<span class="tile-emoji">${x.esc(v.emoji)}</span><b>${x.esc(v.name)}</b><small>${x.esc(v.note)}</small>`)).join('');
    return card+`<section class="card dk-permits"><h4>🖊️ Xin giấy phép làm việc</h4><div class="tile-grid">${tiles}</div></section>`;
  }
  const done=t.worked;
  const locks=(j.points||[]).map(pt=>{const on=(t.locks||[]).includes(pt.id);
    return `<li class="dk-point ${on?'on':''}"><span aria-hidden="true">${pt.kind==='valve'?'🛞':'🔌'}</span><div class="grow"><b>${x.esc(pt.id)}</b><small>${x.esc(pt.name)}</small></div>${done?(on?'🔒':''):x.cmd(on?'🔒 Đã khóa':'🔓 Khóa, treo thẻ','dk_iso',{task:t.id,point:pt.id},on?'small primary':'small ghost')}</li>`;}).join('');
  const rows=[];
  rows.push(`<li>${t.xref?reading(x,'📋 Bảng giấy phép:',read.xref):x.cmd('📋 Đối chiếu bảng giấy phép đang mở','dk_xref',{task:t.id},'ghost full',done)}</li>`);
  if(j.bleed)rows.push(`<li>${t.bled?`<p class="dk-read ok">💨 Đã xả: ${x.esc(j.bleed)}.</p>`:x.cmd(`💨 Xả áp · ${x.esc(j.bleed)}`,'dk_bleed',{task:t.id},'ghost full',done)}</li>`);
  if(j.prove)rows.push(`<li>${t.proven?reading(x,'0️⃣ Kiểm về không:',read.verify):x.cmd(`0️⃣ Kiểm về không · ${x.esc(j.prove)}`,'dk_verify',{task:t.id},'ghost full',done)}</li>`);
  rows.push(`<li>${t.gas?reading(x,'📟 Đo khí:',read.gas):x.cmd('📟 Đo khí tại chỗ làm','dk_gas',{task:t.id},'ghost full',done)}</li>`);
  if(j.watch){const w=(cc(x).watch||{})[j.watch]||{};rows.push(`<li>${t.watch?`<p class="dk-read ok">${x.esc(w.emoji||'')} ${x.esc(w.name||'')}: đã bố trí.</p>`:x.cmd(`${x.esc(w.emoji||'')} ${x.esc(w.name||'')}`,'dk_watch',{task:t.id},'ghost full',done)}</li>`);}
  const after=done?`<section class="card dk-after"><h4>🔧 Đã làm xong việc chính</h4>${t.restored?'<p class="dk-read ok">🔁 Đã tháo khóa, chạy thử.</p>':x.cmd('🔁 Tháo khóa, mở van theo thứ tự, chạy thử','dk_restore',{task:t.id},'ghost full')}</section>`:'';
  return card+(j.points?.length?`<section class="card dk-locks"><h4>🔒 Cô lập: mỗi điểm một ổ khóa của bạn</h4><ul class="dk-list">${locks}</ul></section>`:'')+
    `<section class="card dk-checks"><h4>🔎 Trước khi mở</h4><ul class="dk-list">${rows.join('')}</ul></section>${after}`;
}
function ptwSteps(t,x){
  const j=t.job||{},read=t.read||{};
  if(!t.permit)return {steps:[{ok:null,label:'Xin đúng loại giấy phép',go:{sel:'.dk-permits .tile-grid',label:'🖊️ Chọn giấy phép'}}],final:null};
  if(t.worked){const steps=[{ok:t.restored||null,label:'Trả thiết bị về vận hành',go:{cmd:'dk_restore',payload:{task:t.id},label:'🔁 Tháo khóa, chạy thử'}}];
    if(t.can_report&&!t.nearmiss)steps.push({ok:null,label:'Báo suýt sự cố',go:{cmd:'dk_nearmiss',payload:{task:t.id},label:'📝 Báo suýt sự cố'}});
    return {steps,final:{label:'📋 TRẢ GIẤY PHÉP',go:finalGo(steps,'dk_close',{task:t.id}),ready:true}};}
  const steps=[{ok:t.xref||null,label:'Đối chiếu bảng giấy phép',go:{cmd:'dk_xref',payload:{task:t.id},label:'📋 Đối chiếu'}}];
  for(const p of j.points||[])steps.push({ok:(t.locks||[]).includes(p.id)?true:null,label:`Khóa ${p.id}`,go:{cmd:'dk_iso',payload:{task:t.id,point:p.id},label:`🔒 Khóa ${x.esc(p.id)}`}});
  if(j.bleed)steps.push({ok:t.bled||null,label:'Xả áp',go:{cmd:'dk_bleed',payload:{task:t.id},label:'💨 Xả áp'}});
  if(j.prove)steps.push({ok:t.proven?true:null,label:'Kiểm về không',go:{cmd:'dk_verify',payload:{task:t.id},label:'0️⃣ Kiểm về không'}});
  steps.push({ok:t.gas||null,label:'Đo khí',go:{cmd:'dk_gas',payload:{task:t.id},label:'📟 Đo khí'}});
  if(j.watch)steps.push({ok:t.watch||null,label:'Bố trí người canh',go:{cmd:'dk_watch',payload:{task:t.id},label:'🧍 Bố trí người canh'}});
  if(Object.values(read).some(isBad))steps.unshift({ok:false,label:'Kết quả kiểm tra bất thường',go:{sel:'.dk-stop',label:'⚠️ Xem lại kết quả kiểm tra'}});
  if(t.can_report&&!t.nearmiss)steps.push({ok:null,label:'Báo suýt sự cố',go:{cmd:'dk_nearmiss',payload:{task:t.id},label:'📝 Báo suýt sự cố'}});
  return {steps,final:{label:'🔧 BẮT TAY VÀO VIỆC',go:finalGo(steps,'dk_work',{task:t.id}),ready:true}};
}

/* ------------------------------------------------------------ rounds */
function roundPanel(t,x){
  const reads=t.reads||{},called=t.called||[],areas=cc(x).areas||{};
  const rows=(t.gauges||[]).map(g=>{const v=reads[g.tag];
    const btns=v?`<span class="tag ${v==='ok'?'green':'amber'}">${v==='ok'?'✅ Trong giới hạn':v==='high'?'🔺 Cao':'🔻 Thấp'}</span>${v!=='ok'&&!called.includes(g.tag)?x.cmd('📻 Báo phòng điều khiển','dk_call',{task:t.id,tag:g.tag},'small primary'):called.includes(g.tag)?'<small class="muted">📻 đã báo</small>':''}`
      :['ok','high','low'].map(k=>x.cmd(k==='ok'?'✅ Trong':k==='high'?'🔺 Cao':'🔻 Thấp','dk_read',{task:t.id,tag:g.tag,verdict:k},'small ghost')).join('');
    return `<li class="dk-gauge dk-g-${x.esc(g.tag)}"><div class="grow"><b>${x.esc(g.tag)}</b> <small>${x.esc(g.name)}</small><div class="dk-dial"><span class="dk-val">${g.value} ${x.esc(g.unit)}</span><small>giới hạn ${g.lo}–${g.hi}</small></div></div><div class="row wrap dk-gbtn">${btns}</div></li>`;}).join('');
  const look=(t.needs?.areas||[]).map(a=>{const ar=areas[a]||{};const seen=(t.looked||[]).includes(a);
    return seen?`<span class="tag">${x.esc(ar.emoji||'')} ${x.esc(ar.name||a)} ✓</span>`:x.cmd(`${x.esc(ar.emoji||'')} ${x.esc(ar.name||a)}`,'dk_look',{task:t.id,area:a},'small ghost');}).join('');
  const leak=t.found&&!t.leak?`<section class="sk-event tense dk-leak"><div class="sk-ev-head"><span aria-hidden="true">🛢️</span><div><small>Phát hiện lúc đi tuần</small><h3>Có dấu hiệu rò</h3></div></div>${t.leak_seen?`<p class="dk-read bad">${x.esc(t.leak_seen)}</p>`:''}
    <div class="sk-opts">${x.cmd('<span class="sk-opt-label">📻 Báo phòng điều khiển, rào khu vực, đứng ngược gió</span>','dk_leak',{task:t.id,how:'report'},'sk-opt')}${x.cmd('<span class="sk-opt-label">🔧 Tự siết bích cho nhanh</span>','dk_leak',{task:t.id,how:'tighten'},'sk-opt')}</div></section>`:'';
  return `${leak}<section class="card dk-gauges"><h4>📈 Đồng hồ trên tuyến</h4><ul class="dk-list">${rows}</ul></section>
    <section class="card dk-areas"><h4>👂 Nghe, nhìn, ngửi từng khu</h4><div class="row wrap">${look}</div></section>`;
}
function roundSteps(t,x){
  const reads=t.reads||{},steps=[];
  const unread=(t.gauges||[]).find(g=>!reads[g.tag]);
  steps.push({ok:unread?null:true,label:'Đọc từng đồng hồ so với giới hạn',note:`${Object.keys(reads).length}/${(t.gauges||[]).length}`,go:unread?{sel:`.dk-g-${unread.tag} .dk-gbtn`,label:`📈 Đọc ${x.esc(unread.tag)}`}:null});
  const toCall=(t.gauges||[]).find(g=>reads[g.tag]&&reads[g.tag]!=='ok'&&!(t.called||[]).includes(g.tag));
  if(toCall)steps.push({ok:null,label:`Báo ${toCall.tag} cho phòng điều khiển`,go:{cmd:'dk_call',payload:{task:t.id,tag:toCall.tag},label:`📻 Báo ${x.esc(toCall.tag)}`}});
  const area=(t.needs?.areas||[]).find(a=>!(t.looked||[]).includes(a));
  steps.push({ok:area?null:true,label:'Đi hết các khu trên tuyến',go:area?{cmd:'dk_look',payload:{task:t.id,area},label:`👂 Đi ${x.esc((cc(x).areas||{})[area]?.name||area)}`}:null});
  if(t.found&&!t.leak)steps.unshift({ok:null,label:'Xử lý chỗ rò',go:{sel:'.dk-leak .sk-opts',label:'🛢️ Quyết cách xử lý'}});
  if(t.can_report&&!t.nearmiss)steps.push({ok:null,label:'Báo suýt sự cố',go:{cmd:'dk_nearmiss',payload:{task:t.id},label:'📝 Báo suýt sự cố'}});
  return {steps,final:{label:'📒 GHI SỔ TUẦN TRA',go:finalGo(steps,'dk_log',{task:t.id}),ready:!unread}};
}

/* ------------------------------------------------------------ the alarm */
function drillPanel(t,x){
  const n=t.needs||{};
  const head=`<section class="sk-event tense dk-alarm"><div class="sk-ev-head"><span aria-hidden="true">🔊</span><div><small>Gió từ hướng ${x.esc(n.wind)} · rò gần ${x.esc(n.near)}</small><h3>${x.esc(n.tone)}</h3></div></div>
    ${t.alarm?`<p class="dk-read ok">${x.esc(alarm(x,t.alarm).emoji)} ${x.esc(alarm(x,t.alarm).name)}</p>`:`<div class="sk-opts">${(cc(x).alarms||[]).map(a=>x.cmd(`<span class="sk-opt-label">Đó là: ${x.esc(a.name)}</span>`,'dk_alarm',{task:t.id,pick:a.id},'sk-opt')).join('')}</div>`}</section>`;
  const mid=t.alarm?`<section class="card dk-go"><div class="row wrap">${t.dropped?'<span class="tag green">🧰 Đã để thiết bị an toàn</span>':x.cmd('🧰 Tắt máy, để dụng cụ an toàn','dk_drop',{task:t.id},'small ghost')}
      ${!t.route&&!t.phone?x.cmd('📱 Chạy về phòng lấy điện thoại','dk_phone',{task:t.id},'small ghost'):''}</div>
    <h4 class="section-title">🧭 Đi đường nào?</h4>${t.route?`<p class="dk-read ${t.route==='up'?'ok':'bad'}">${x.esc((n.route_text||{})[t.route]||'')}</p>`:`<div class="sk-opts dk-routes">${(n.routes||[]).map(r=>x.cmd(`<span class="sk-opt-label">${x.esc((n.route_text||{})[r]||r)}</span>`,'dk_route',{task:t.id,route:r},'sk-opt')).join('')}</div>`}
    ${t.route?`<h4 class="section-title">🛶 Điểm tập trung</h4>${t.muster?`<p class="dk-read ok">🛶 ${x.esc((cc(x).stations||{})[t.muster]||'')}</p>`:`<div class="row wrap dk-stations">${Object.entries(cc(x).stations||{}).map(([k,l])=>x.cmd(`🛶 ${x.esc(l)}`,'dk_station2',{task:t.id,station:k},'small ghost')).join('')}</div><p class="small muted">Phòng của bạn đợt này: ${n.room}.</p>`}`:''}</section>`:'';
  return head+mid;
}
function drillSteps(t,x){
  const steps=[{ok:t.alarm?true:null,label:'Nhận ra tiếng còi',go:{sel:'.dk-alarm .sk-opts',label:'🔊 Đó là còi gì?'}}];
  if(t.alarm){steps.push({ok:t.dropped||null,label:'Để thiết bị đang làm ở trạng thái an toàn',go:{cmd:'dk_drop',payload:{task:t.id},label:'🧰 Để dụng cụ an toàn'}});
    steps.push({ok:t.route?true:null,label:'Chọn đường đi',go:{sel:'.dk-routes',label:'🧭 Chọn đường'}});
    if(t.route)steps.push({ok:t.muster?true:null,label:'Tới đúng xuồng của mình',go:{sel:'.dk-stations',label:'🛶 Chọn xuồng'}});}
  if(t.can_report&&!t.nearmiss&&t.muster)steps.push({ok:null,label:'Báo suýt sự cố',go:{cmd:'dk_nearmiss',payload:{task:t.id},label:'📝 Báo suýt sự cố'}});
  return {steps,final:{label:'💳 QUẸT THẺ ĐIỂM DANH',go:finalGo(steps,'dk_card',{task:t.id}),ready:!!t.muster}};
}

/* ------------------------------------------------------------ the storm, the handover */
function securePanel(t,x){
  const L=cc(x).loose||{};
  const rows=(t.needs?.items||[]).map(i=>{const it=L[i]||{},done=(t.done||{})[i];
    return `<li class="dk-loose"><span aria-hidden="true">${x.esc(it.emoji||'')}</span><div class="grow"><b>${x.esc(it.name||i)}</b>${done?`<small>✅ ${done==='lash'?'đã chằng buộc':done==='inside'?'đã cất vào trong':'đã kiểm tra'}</small>`:''}</div>
      ${done?'':`<div class="row wrap">${[['lash','🪢 Chằng'],['inside','📦 Cất vào'],['check','🔎 Kiểm']].map(([k,l])=>x.cmd(l,'dk_secure',{task:t.id,item:i,how:k},'small ghost')).join('')}</div>`}</li>`;}).join('');
  return `<section class="card dk-storm"><h4>🌀 Boong trước bão</h4><ul class="dk-list">${rows}</ul></section>
    <section class="card">${t.crane?'<p class="dk-read ok">🏗️ Cẩu đã hạ cần, khóa, tắt máy.</p>':x.cmd('🏗️ Báo cẩu trưởng dừng cẩu, hạ cần','dk_crane',{task:t.id},'ghost full')}</section>`;
}
function secureSteps(t,x){
  const left=(t.needs?.items||[]).filter(i=>!(t.done||{})[i]);
  const steps=[{ok:left.length?null:true,label:'Xử lý từng món trên boong',note:`${(t.needs?.items||[]).length-left.length}/${(t.needs?.items||[]).length}`,go:left.length?{sel:'.dk-storm .dk-list',label:'🪢 Xử lý đồ trên boong'}:null},
    {ok:t.crane||null,label:'Dừng cẩu',go:{cmd:'dk_crane',payload:{task:t.id},label:'🏗️ Dừng cẩu'}}];
  return {steps,final:{label:'📻 BÁO PHÒNG ĐIỀU KHIỂN',go:finalGo(steps,'dk_report',{task:t.id}),ready:true}};
}
function handoverPanel(t,x){
  const O=cc(x).open_items||{};
  const rows=(t.needs?.items||[]).map(i=>{const it=O[i]||{},on=(t.picked||[]).includes(i);
    return `<li>${tile(x,'dk_note',{task:t.id,item:i},`<span class="tile-emoji">${x.esc(it.emoji||'')}</span><b>${x.esc(it.text||i)}</b><small>${on?'✍️ đã ghi':'chạm để ghi'}</small>`,on?'selected dk-note':'dk-note')}</li>`;}).join('');
  return `<section class="card dk-hand"><h4>📝 Bàn giao cho người ca sau</h4><p class="small muted">Người ca sau chỉ biết những gì bạn ghi.</p><ul class="dk-list dk-notes">${rows}</ul></section>`;
}
function handoverSteps(t){
  const steps=[{ok:(t.picked||[]).length?true:null,label:'Ghi các việc còn dở',go:{sel:'.dk-notes',label:'✍️ Ghi bàn giao'}}];
  return {steps,final:{label:'🤝 BÀN GIAO, VỀ BỜ',go:finalGo(steps,'dk_handover',{task:t.id}),ready:true}};
}

/* ------------------------------------------------------------ the shore day */
const OUT={happy:'😊 Mừng',ok:'🙂 Hiểu',short:'😔 Thiếu',spoiled:'🤑 Được chiều',sulk:'😤 Hờn',lavish:'💸 Mừng to',risky:'😬 Khó đòi',scammed:'🕳️ Bị lừa',refused:'🛡️ Từ chối được',counter:'🔁 Mặc cả'};
function shorePanel(t,x){
  const n=t.needs||{},W=cc(x).shore_words||{};
  const reqs=(t.reqs||[]).map(r=>{
    const done=r.done&&r.done.out!=='counter';
    const ws=(x.ui.words??={})[r.id]||[];
    const chips=Object.entries(W).map(([k,l])=>act(x,x.esc(l),'word',{req:r.id,w:k},`small dk-word${ws.includes(k)?' on':''}`,` aria-pressed="${ws.includes(k)}"`)).join('');
    const amt=Math.max(0,Math.min(r.ask*2,Number((x.ui.amt??={})[r.id]??(r.done?.counter??Math.floor(r.ask/10)*5))||0));
    const stepper=`<div class="sk-amt-row">${act(x,'−','amtStep',{key:r.id,delta:-5,min:0,max:r.ask*2,def:amt},'ghost sk-step',' aria-label="Bớt 5 xu"')}<label class="sk-amt-in"><input type="number" inputmode="numeric" min="0" max="${r.ask*2}" value="${amt}" data-sk-amt="${x.esc(r.id)}" aria-label="Gửi bao nhiêu"><small>xu</small></label>${act(x,'+','amtStep',{key:r.id,delta:5,min:0,max:r.ask*2,def:amt},'ghost sk-step',' aria-label="Thêm 5 xu"')}</div>`;
    const body=done?`<p class="dk-read ${r.done.good===false?'bad':'ok'}">${x.esc(OUT[r.done.out]||'')} · đã gửi ${r.done.amount} xu</p>`:
      `${r.fact?`<p class="dk-read fact">🔎 ${x.esc(r.fact)}</p>`:x.cmd('🔎 Hỏi rõ','dk_ask',{task:t.id,req:r.id},'small ghost')}
       ${r.done?.out==='counter'?`<p class="dk-read bad">🔁 Đòi thêm cho đủ ${r.done.counter} xu (đã gửi ${r.done.amount}).</p>`:''}
       <div class="dk-words">${chips}</div>${stepper}
       <div class="row wrap">${act(x,'📲 Gửi số này','send',{task:t.id,req:r.id,max:r.ask*2,def:amt},'primary grow dk-send')}${act(x,'🙅 Không gửi','send',{task:t.id,req:r.id,max:r.ask*2,def:0,zero:1},'ghost')}</div>`;
    return `<li class="card dk-req dk-req-${x.esc(r.id)}"><div class="row"><span class="dk-req-emoji" aria-hidden="true">${x.esc(r.emoji)}</span><div class="grow"><b>${x.esc(r.who)}</b> <small class="muted">xin ${r.ask} xu</small><p>“${x.esc(r.line)}”</p></div></div>${body}</li>`;}).join('');
  return `<section class="card dk-allow"><div class="row spread"><h4>💵 Phụ cấp đi biển</h4><span class="tag green">${n.allowance} xu</span></div><p class="small muted">Vào quỹ khi bạn bắt đầu trả lời. Gửi bao nhiêu, nói gì là do bạn.</p>
    ${t.called?'<p class="dk-read ok">📹 Đã gọi video cả nhà.</p>':x.cmd('📹 Gọi video cả nhà','dk_love',{task:t.id},'ghost full')}</section><ul class="dk-reqs">${reqs}</ul>`;
}
function shoreSteps(t,x){
  const steps=[{ok:t.called||null,label:'Gọi video hỏi han cả nhà',go:{cmd:'dk_love',payload:{task:t.id},label:'📹 Gọi video'}}];
  for(const r of t.reqs||[]){const done=r.done&&r.done.out!=='counter';steps.push({ok:done?true:null,label:`Trả lời ${r.who}`,go:done?null:{sel:`.dk-req-${r.id} .dk-words`,label:`💬 Trả lời ${x.esc(r.who)}`}});}
  return {steps,final:{label:'🌙 XONG NGÀY TRÊN BỜ',go:finalGo(steps,'dk_done',{task:t.id}),ready:(t.reqs||[]).every(r=>r.done&&r.done.out!=='counter')}};
}

/* ------------------------------------------------------------ the shell */
const PANELS={heli:heliPanel,induct:inductPanel,toolbox:toolboxPanel,ptw:ptwPanel,round:roundPanel,drill:drillPanel,secure:securePanel,handover:handoverPanel,shore:shorePanel};
const STEPS={heli:heliSteps,induct:inductSteps,toolbox:toolboxSteps,ptw:ptwSteps,round:roundSteps,drill:drillSteps,secure:secureSteps,handover:handoverSteps,shore:shoreSteps};
const ASK={heli:'🎫 Nhận phiếu bay',induct:'🪪 Nhận phòng',toolbox:'🗣️ Mở buổi họp',ptw:'📋 Nhận phiếu việc',round:'🔎 Nhận tuyến tuần',drill:'🔊 Nghe loa',secure:'🌀 Nhận lệnh chằng buộc',handover:'📝 Mở sổ bàn giao',shore:'🏠 Về tới nhà'};
function guide(t,x){
  const d=data(x),o=d.odd||{};
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện trên giàn',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(o.ev)return {steps:[air.oddStep(x)],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'dk_intro',payload:{},label:'🛢️ Vào nghề thôi!'}}],final:null};
  if(o.conduct?.ground&&['toolbox','ptw','round','drill','secure'].includes(t.kind))return {steps:[air.oddStep(x)].filter(Boolean),final:null};
  if(!t.known)return {steps:[{ok:null,label:ASK[t.kind]||'Nhận việc',go:{cmd:'ask',payload:{task:t.id},label:ASK[t.kind]||'Nhận việc'}}],final:null,pulse:'.sk-ask'};
  return (STEPS[t.kind]||(()=>({steps:[],final:null})))(t,x);
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});
function top(x){return `${introCard(x,'dk_intro','🛢️')}${deskCard(x,'dk_desk','Chuyện trên giàn')}${air.oddCard(x,AIR)}${air.groundCard(x)}`;}
function logCard(x){
  const d=data(x),st=d.stats||{};
  const rows=(d.log||[]).slice().reverse().map(r=>`<li><span>N${r.day}</span><b class="grow">${x.esc(r.title)}</b><span aria-hidden="true">${r.ok?'✓':'•'}</span></li>`).join('');
  return `<article class="card dk-log"><h4>📘 Sổ đi biển</h4><div class="dk-stats"><div><b>${st.jobs||0}</b><small>việc</small></div><div><b>${st.stops||0}</b><small>lần dừng việc</small></div><div><b>${st.nearmiss||0}</b><small>báo suýt sự cố</small></div><div><b>${st.best_muster?st.best_muster+'′':'—'}</b><small>tập trung nhanh nhất</small></div></div>
    ${rows?`<ul class="dk-list dk-loglist">${rows}</ul>`:'<p class="small muted">Chưa có việc nào trong sổ.</p>'}</article>`;
}

export default {
  id:'oil',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed line below */}
    return t.title;
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    if(d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro||(d.odd?.conduct?.ground&&['toolbox','ptw','round','drill','secure'].includes(t.kind)))
      return `<div class="career-job sk dk">${hint}${top(x)}${bottom(x,g)}</div>`;
    const head=t.known?who(t,x):askCard(x,t,ASK[t.kind]||'Nhận việc');
    const main=t.known?(PANELS[t.kind]||(()=>''))(t,x)+reportBox(t,x)+stopBox(t,x):'';
    const side=t.known&&g.steps.length?stepRows(x,g.steps,'Các bước'):'';
    return `<div class="career-job sk dk">${hint}${top(x)}${hitchBar(x)}${head}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),o=d.odd||{};
    const steps=d.desk?.ev?[{ok:null,label:'Quyết chuyện trên giàn',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}]:air.oddStep(x)?[air.oddStep(x)]:!d.intro?[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'dk_intro',payload:{},label:'🛢️ Vào nghề thôi!'}}]:[];
    const g={steps,final:null};
    if(d.desk?.ev||o.ev||!d.intro||x.ui.intro)return `<div class="career-job sk dk">${pending(steps)?.go?hintFor(g,x):''}${top(x)}${bottom(x,g)}</div>`;
    return `<div class="career-job sk dk">${top(x)}${hitchBar(x)}<section class="card dk-crew"><h4>🧑‍🔧 Hồ sơ của bạn</h4>${air.record(x)}${air.restCard(x,AIR)}</section>${logCard(x)}</div>`;
  },
  input(el,x){return kitInput(el,x);},
  tick(root){keepBarAboveFooter(root);},
  actions:{
    ...air.ACTIONS,...kitActions,
    async stopOpen(d,el,x){x.ui.stop=x.ui.stop===d.task?null:d.task;x.render();},
    async send(d,el,x){const b=x.ui.amt??={},raw=d.zero?0:(b[d.req]===undefined||b[d.req]===''?Number(d.def):Number(b[d.req]));
      const amount=Math.max(0,Math.min(Number(d.max),Math.floor(raw)||0));
      await x.send('dk_send',{task:d.task,req:d.req,amount,words:(x.ui.words||{})[d.req]||[]});},
    async word(d,el,x){const w=(x.ui.words??={})[d.req]??=[],i=w.indexOf(d.w);if(i>=0)w.splice(i,1);else{w.push(d.w);if(w.length>2)w.shift();}x.render();},
  },
};
