/** Gác chắn đường ngang Bến Mây — level-crossing keeper and track patrol (server: game/careers/railway.py).
 * Three kinds of job: the hand-over (test six pieces of equipment, fix and report a fault through the right channel,
 * sign), a train (the station's radio call and its read-back, the crossing to clear, the bell before the arm, the
 * people pushing at the lowered barrier and the player's own answer to each, the clear flag or stopping the train,
 * watching the whole train, the station's word before opening, the log) and the track patrol (walk each point, fix,
 * protect, report on the right form). Around them: surprises, the chuyện oái oăm (answered in your own tone and words)
 * and the keeper's record (conduct, fatigue, rest days).
 * The server decides everything; one tap sends one command. The guide only points the way: the read-back, the answer
 * to each person, the way to clear the rails and the log lines are always the player's own choice. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,lower,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,act} from './street_kit.js';
import {ACTIONS as oddActions} from './air_kit.js';

const DONE=['completed','cancelled','referred'];
const odd=x=>data(x).odd||{};
const lamp=t=>t.needs?.night;
const KIND={charm:'Lời mời khó từ chối',harass:'Quấy rối',demand:'Yêu cầu oái oăm',corner:'Làm tắt',bargain:'Mặc cả với đội'};

/* ------------------------------------------------------------ the crossing, drawn */
function crossing(t,x){
  const eta=t.eta??null,pos=t.passed?100:eta==null?0:Math.max(4,Math.min(92,100-eta*10));
  const arm=t.arm==='down'?'down':'up',bell=t.bell!=null&&!t.passed?'on':'',people=(t.left||[]).length;
  const tr=t.needs?.train||{};
  return `<div class="rw-x ${arm} ${bell}" aria-hidden="true">
    <div class="rw-track"><span class="rw-train" style="left:${pos}%">${x.esc(tr.emoji||'🚆')}</span><span class="rw-cross">✚</span></div>
    <div class="rw-road"><i class="rw-arm a"></i><i class="rw-arm b"></i><b class="rw-light l"></b><b class="rw-light r"></b>${people?`<span class="rw-ppl">${'🧍'.repeat(Math.min(3,people))}</span>`:''}</div></div>`;
}
function chips(t,x){
  const c=(on,a,b)=>`<span class="tag ${on?'amber':''}">${on?a:b}</span>`;
  const flag=t.flag==='green'?`<span class="tag green">🟩 ${lamp(t)?'Đèn trắng':'Cờ xanh'}</span>`:t.flag==='red'?'<span class="tag danger">🟥 Báo dừng</span>':'';
  return `<div class="rw-chips">${c(t.bell!=null,'🔔 Chuông đang kêu','🔕 Chuông tắt')}${c(t.arm==='down','🚧 Chắn đã hạ','🚧 Chắn đang nâng')}${flag}</div>`;
}
function eta(t){
  if(t.passed)return '<span class="rw-eta done">✅ Tàu đã qua</span>';
  if(t.standing)return '<span class="rw-eta stop">🟥 Tàu đứng chờ</span>';
  if(t.eta==null)return '';
  return `<span class="rw-eta ${t.eta<=3?'near':''}">⏱️ Tàu còn ${t.eta} phút</span>`;
}
function ticket(t,x){
  if(!t.known)return askCard(x,t,'📻 Nghe ga gọi bộ đàm');
  const tr=t.needs?.train||{};
  const tag=t.second_train?`<span class="tag blue">🚂 + ${x.esc(t.second_train)}</span>`:'';
  return person(x,t,`<p class="rw-train-line">${x.esc(tr.emoji)} ${x.esc(tr.name)} · ${x.esc(tr.cars)} toa ${eta(t)}</p>`,tag);
}

/* ------------------------------------------------------------ a train */
function radioPanel(t,x){
  const tired=odd(x).tired&&!t.awake;
  const opts=(t.needs?.readback||[]).map((o,i)=>x.cmd(`<span class="sk-opt-label">📻 “${x.esc(o)}”</span>`,'rw_readback',{task:t.id,option:i},'sk-opt rw-rb',tired)).join('');
  return `<section class="card rw-radio"><h4>📻 Nhắc lại lệnh của ga</h4><p class="small muted">Đọc lại đúng số hiệu tàu, giờ rời Bến Gỗ, giờ qua đường ngang.</p>
    ${tired?`<p class="rw-tired">😮‍💨 Mắt díp lại rồi. ${x.cmd('🚰 Rửa mặt, đi lại cho tỉnh','rw_wake',{task:t.id},'small primary')}</p>`:''}<div class="sk-opts">${opts}</div></section>`;
}
function clearList(t,x){
  if(t.left_hidden&&!(t.left||[]).length)return `<p class="small muted">Chưa nhìn hai phía đường ngang.</p>`;
  if(!(t.left||[]).length)return `<p class="small rw-ok">✅ Trên ray không còn ai, không còn gì.</p>`;
  const how=cc(x).clear||{};
  return `<ul class="rw-left">${t.left.map(p=>`<li><div class="row"><span class="rw-em" aria-hidden="true">${x.esc(p.emoji)}</span><div class="grow"><b>${x.esc(p.name)}</b>${p.line?`<small>${x.esc(p.line)}</small>`:''}${p.steps>1?`<small class="muted">${p.done}/${p.steps}</small>`:''}</div></div>
    <div class="rw-how">${Object.entries(how).map(([k,v])=>x.cmd(`${x.esc(v.emoji)} ${x.esc(v.name)}`,'rw_clear',{task:t.id,who:p.key,how:k},'small ghost')).join('')}</div></li>`).join('')}</ul>`;
}
function pusherCard(t,x){
  const p=(t.pushers||[]).find(r=>r.state==='on');if(!p)return '';
  const ans=cc(x).answers||{},who=p.npc?x.portrait(x.npc(p.npc),40):`<span class="rw-av" aria-hidden="true">${x.esc(p.emoji)}</span>`;
  const btn=(k)=>{const a=ans[k]||{name:k,emoji:''};const label=k==='explain'?`${a.emoji} Chỉ bảng giờ: tàu còn ${t.eta} phút`:`${a.emoji} ${a.name}`;
    return x.cmd(`<span class="sk-opt-label">${x.esc(label)}</span>`,'rw_answer',{task:t.id,who:p.id,answer:k},`sk-opt rw-ans ${k==='open'?'rw-open':''}`);};
  return `<section class="sk-event tense rw-push" role="group" aria-labelledby="rw-push-who"><div class="sk-ev-head">${who}<div class="grow"><small>Đòi qua chắn</small><h3 id="rw-push-who">${x.esc(p.who)}</h3></div></div>
    <p class="rw-line">${x.esc(p.line)}</p><div class="sk-opts">${['hold','explain','detour','calm','report'].map(btn).join('')}</div>
    <details class="rw-tempt"><summary>Chiều theo…</summary>${btn('open')}<p class="small muted">Chắn đã hạ thì không mở cho bất kỳ ai.</p></details></section>`;
}
function pushLog(t,x){
  const done=(t.pushers||[]).filter(p=>p.state==='done');if(!done.length)return '';
  const OUT={ok:'✅ lùi lại',sulk:'😒 càm ràm, chờ',blowup:'😤 nổi khùng',sneak:'🏃 chui chắn',opened:'⚠️ được mở chắn',waited:'⏳ đứng chờ'};
  return pane(x,`push-${t.id}`,`👥 Người chờ ở chắn · ${done.length}${t.waiting?` · còn ${t.waiting} người đang tới`:''}`,
    `<ul class="rw-plog">${done.map(p=>`<li><span aria-hidden="true">${x.esc(p.emoji)}</span> ${x.esc(p.who.split(' · ')[0])} · <small>${x.esc(OUT[p.out]||'')}</small></li>`).join('')}</ul>`,false,'rw-plog-pane');
}
function controls(t,x){
  const d=data(x),b=(label,cmd,payload={},cls='',dis=false)=>x.cmd(label,cmd,{task:t.id,...payload},cls,dis);
  const g=lamp(t)?'⚪ Giơ đèn trắng':'🟩 Giơ cờ xanh',r=lamp(t)?'🔴 Báo dừng tàu, đèn đỏ':'🟥 Báo dừng tàu, cờ đỏ';
  const rows=[];
  if(!t.scanned)rows.push(b('👀 Nhìn đường ngang','rw_scan',{},'primary'));
  if(t.bell==null&&!t.standing)rows.push(b('🔔 Bật chuông đèn','rw_warn'));
  if(t.arm==='up')rows.push(b(d.crank?'🚧 Quay tay hạ chắn':'🚧 Hạ chắn','rw_lower'));
  if(t.arm==='down'&&t.flag!=='green'&&!t.stopped)rows.push(b(g,'rw_flag',{color:'green'},'',(t.left||[]).length>0));
  if(t.late_told&&!t.held&&!t.recalled)rows.push(b('📻 Hỏi ga: tàu còn đứng ở Bến Gỗ?','rw_ask'));
  if(t.held&&t.arm==='down')rows.push(b('🚧 Nâng chắn tạm (ga đã xác nhận)','rw_raise'));
  if(t.standing)rows.push(b('📻 Báo ga: đường đã thông','rw_allclear',{},'primary',(t.left||[]).length>0||t.arm!=='down'));
  else rows.push(b('⏳ Đứng chờ tàu','rw_wait'));
  const stop=!t.stopped?x.confirmCmd(r,'rw_stop',{task:t.id},'Báo ga dừng tàu? Chỉ dùng khi đường ngang có vật cản không dẹp kịp.','danger small'):'';
  return `<div class="rw-ctl">${rows.join('')}</div>${stop?`<div class="rw-stop">${stop}</div>`:''}`;
}
function afterPanel(t,x){
  const b=(label,cmd,payload={},cls='')=>x.cmd(label,cmd,{task:t.id,...payload},cls);
  const rows=[];
  if(!t.watched)rows.push(b('👁️ Nhìn hết đoàn tàu','rw_watch',{},'primary'));
  else{
    const s=t.seen||{};
    rows.push(`<p class="rw-seen">${s.tail?'🏮 Có đèn đuôi toa cuối.':'🏮 <b>Không thấy đèn đuôi!</b>'}${s.defect?` ⚠️ ${x.esc(s.defect)}`:''}</p>`);
    if(!s.tail)rows.push((t.radioed||[]).includes('tail')?'<span class="tag green">✓ Đã báo mất đèn đuôi</span>':b('📻 Báo ga: không có đèn đuôi','rw_radio',{what:'tail'},'primary'));
    if(s.defect)rows.push((t.radioed||[]).includes('defect')?'<span class="tag green">✓ Đã báo bất thường</span>':b('📻 Báo ga: toa có bất thường','rw_radio',{what:'defect'},'primary'));
  }
  if(t.arm==='down'){
    rows.push(t.asked?'<span class="tag green">✓ Ga cho nâng chắn</span>':b(t.second==='coming'?'⏳ Chờ tàu thứ hai qua, hỏi lại ga':'📻 Hỏi ga: còn tàu nào không?','rw_ask'));
    rows.push(b('🚧 Nâng chắn, tắt chuông','rw_raise'));
  }
  return `<section class="card rw-after"><h4>🚆 Tàu đã qua</h4><div class="rw-ctl">${rows.join('')}</div></section>`;
}
function logPanel(t,x){
  const sel=x.ui.remarks?.[t.id]||[],rem=cc(x).remarks||{};
  const chips=Object.entries(rem).map(([k,v])=>act(x,x.esc(v),'remark',{task:t.id,k},`small ${sel.includes(k)?'rw-on':'ghost'}`,` aria-pressed="${sel.includes(k)}"`)).join('');
  return `<section class="card rw-log"><h4>📒 Ghi sổ nhật ký</h4><p class="small muted">Chọn đúng những gì đã xảy ra với chuyến này.</p><div class="rw-remarks">${chips}</div>
    ${x.cmd('✍️ GHI SỔ, KÝ TÊN','rw_log',{task:t.id,remarks:sel},'primary full',!sel.length)}</section>`;
}

/* ------------------------------------------------------------ the hand-over */
function shiftPanel(t,x){
  const n=t.needs||{},eq=cc(x).equip||[],forms=cc(x).forms||{};
  const board=(n.board||[]).map(b=>`<li><span aria-hidden="true">${x.esc(b.emoji)}</span><b>${x.esc(b.code)}</b><span>${x.esc(b.at)}</span><small>${x.esc(b.dir)}</small></li>`).join('');
  const tiles=eq.map(e=>{const on=(t.checked||[]).includes(e.id),bad=on&&t.found_item===e.id;
    return `<button type="button" class="tile sk-tile rw-eq ${on?(bad?'bad':'selected'):''}" data-command="rw_check" data-payload="${x.esc(JSON.stringify({task:t.id,item:e.id}))}"${on?' disabled':''}><span class="tile-emoji">${x.esc(e.emoji)}</span><b>${x.esc(e.name)}</b><small>${on?(bad?'⚠️ hỏng':'✓ ổn'):x.esc(e.test)}</small></button>`;}).join('');
  const fault=t.found?`<section class="card rw-fault"><h4>⚠️ ${x.esc(t.found_text)}</h4>
    ${t.found_fix?(t.fixed?'<span class="tag green">✓ Đã xử lý</span>':x.cmd(`🔧 ${x.esc(t.found_fix)}`,'rw_fix',{task:t.id},'')):'<p class="small muted">Không tự sửa được: báo đúng nơi để thợ tới.</p>'}
    <p class="small"><b>Báo ở đâu?</b> Chọn một hoặc nhiều.</p><div class="rw-forms">${Object.entries(forms).map(([k,f])=>x.cmd(`${x.esc(f.emoji)} ${x.esc(f.name)}<small>${x.esc(f.hint)}</small>`,'rw_form',{task:t.id,form:k},`rw-form ${(t.forms||[]).includes(k)?'rw-on':'ghost'}`)).join('')}</div></section>`:'';
  return `<section class="card rw-board"><h4>🕐 Bảng giờ tàu hôm nay</h4><ul class="rw-boardlist">${board}</ul><p class="small rw-handover">📒 ${x.esc(n.handover||'')}</p></section>
    <section class="card"><h4>🧰 Thử thiết bị <small class="muted">${(t.checked||[]).length}/${eq.length}</small></h4><div class="tile-grid rw-eqs">${tiles}</div></section>${fault}`;
}

/* ------------------------------------------------------------ the patrol */
function patrolPanel(t,x){
  const n=t.needs||{},hd=cc(x).handle||{},pf=cc(x).patrol_forms||{};
  const rows=(n.points||[]).map(p=>{const s=(t.seen||{})[p.id];
    if(!s)return `<li class="rw-pt">${x.cmd(`${x.esc(p.emoji)} <b>${x.esc(p.km)}</b> · ${x.esc(p.name)}`,'rw_walk',{task:t.id,point:p.id},'ghost rw-walk')}</li>`;
    const ok=s.find==='ok',done=(t.handled||{})[p.id],fs=(t.pforms||{})[p.id]||[];
    const hows=ok?'':Object.entries(hd).filter(([k])=>k!=='talk'||s.local).map(([k,v])=>x.cmd(`${x.esc(v.emoji)} ${x.esc(v.short||v.name)}`,'rw_handle',{task:t.id,point:p.id,how:k},`small ${done===k?'rw-on':'ghost'}`,done===k)).join('');
    const forms=ok?'':Object.entries(pf).map(([k,v])=>x.cmd(`${x.esc(v.emoji)} ${x.esc(v.short||v.name)}`,'rw_pform',{task:t.id,point:p.id,form:k},`small ${fs.includes(k)?'rw-on':'ghost'}`)).join('');
    return `<li class="rw-pt seen ${ok?'ok':''}"><div class="row"><span class="rw-em" aria-hidden="true">${x.esc(s.emoji)}</span><div class="grow"><b>${x.esc(p.km)} · ${x.esc(p.name)}</b><small>${x.esc(s.text)}</small></div></div>
      ${ok?'':`<div class="rw-how"><small class="rw-lbl">Làm gì</small>${hows}</div><div class="rw-how"><small class="rw-lbl">Báo đâu</small>${forms}</div>`}</li>`;}).join('');
  return `<section class="card rw-patrol"><h4>🔩 Tuần đường ${x.esc(n.section||'')}</h4><ul class="rw-pts">${rows}</ul></section>`;
}

/* ------------------------------------------------------------ chuyện oái oăm, the record, rest days */
function draft(x,ev){
  const key=`${ev.id}:${ev.round}`;
  if(x.ui.odd?.key!==key)x.ui.odd={key,tone:'',say:[],to:'self',n:ev.bargain?0:null};
  return x.ui.odd;
}
function oddCard(x){
  const o=odd(x),ev=o.ev;
  if(!ev){
    const last=o.last,key=last?`odd-${last.script}-${last.day}-${(o.log||[]).length}`:'';
    if(last&&last.day===x.room.day&&x.ui.seen!==key)
      return `<div class="sk-last ${last.good===true?'good':last.good===false?'bad':''}" role="status"><span aria-hidden="true">${x.esc(last.emoji)}</span><p><b>${x.esc(last.title)}</b> · ${x.esc(last.outcome)}</p>${act(x,'✕','seen',{key},'ghost small sk-x',' aria-label="Đã đọc"')}</div>`;
    return '';
  }
  const u=draft(x,ev),who=ev.npc?x.portrait(x.npc(ev.npc),40):`<span class="rw-av" aria-hidden="true">${x.esc(ev.emoji)}</span>`;
  const seg=(list,cur,a)=>list.map(i=>act(x,x.esc(i.label),a,{v:i.id},`small ${cur===i.id?'rw-on':'ghost'}`,` aria-pressed="${cur===i.id}"`)).join('');
  const words=ev.words.map(w=>act(x,x.esc(w.label),'oddSay',{v:w.id},`small ${u.say.includes(w.id)?'rw-on':'ghost'}${w.id==='yes'?' rw-give':''}`,` aria-pressed="${u.say.includes(w.id)}"`)).join('');
  const b=ev.bargain;
  const count=b?`<div class="rw-odd-row"><small>Nhận</small><div class="rw-step">${act(x,'−','oddN',{v:-1},'small ghost',' aria-label="Bớt"')}<b>${u.n}/${b.ask} ${x.esc(b.unit)}</b>${act(x,'+','oddN',{v:1},'small ghost',' aria-label="Thêm"')}<small class="muted">hợp lý ≤ ${b.limit}</small></div></div>`:'';
  const ready=u.tone&&u.say.length,payload={tone:u.tone||'soft',say:u.say,to:u.to,...(b?{n:u.n}:{})};
  const thread=ev.said.length?`<p class="small muted">Bạn (${x.esc(ev.said[ev.said.length-1].tone.toLowerCase())}): ${x.esc(ev.said[ev.said.length-1].say.join(' '))}</p>`:'';
  return `<section class="sk-event tense rw-odd" role="group" aria-labelledby="rw-odd-title"><div class="sk-ev-head">${who}<div class="grow"><small>${x.esc(KIND[ev.kind]||'')} · ${x.esc(ev.who)}</small><h3 id="rw-odd-title">${x.esc(ev.title)}</h3></div>${ev.round>1?`<span class="tag">${ev.round}/${ev.rounds}</span>`:''}</div>
    ${thread}<p class="rw-line">${x.esc(ev.line)}</p>${ev.cue?`<p class="small">${x.esc(ev.cue)}</p>`:''}
    <div class="rw-odd-row"><small>Giọng</small><div class="rw-segs">${seg(ev.tones,u.tone,'oddTone')}</div></div>
    <div class="rw-odd-row"><small>Nói</small><div class="rw-segs">${words}</div></div>${count}
    ${ev.channels.length>1?`<div class="rw-odd-row"><small>Báo</small><div class="rw-segs">${seg(ev.channels,u.to,'oddTo')}</div></div>`:''}
    ${x.cmd(ready?'💬 Nói':'Chọn giọng và ý muốn nói','rw_odd',payload,'primary full',!ready)}</section>`;
}
function record(x){
  const o=odd(x),cd=o.conduct||{},lv=cd.level||'ok',f=o.fatigue||0;
  return `<div class="rw-record"><span class="tag ${lv==='ok'?'green':'amber'}">${lv==='ok'?'✅':lv==='note'?'📝':lv==='warn'?'⚠️':'⚖️'} ${x.esc(cd.label||'Hồ sơ sạch')}</span>
    <span class="tag ${o.tired?'danger':''}">😮‍💨 Mệt ${f}/6</span></div>`;
}
function restCard(x){
  const o=odd(x);
  if(o.rest_today)return '<p class="small muted">📝 Hôm nay đã xin nghỉ rồi.</p>';
  const u=x.ui.rest||(x.ui.rest={n:1,say:[],to:'self'});
  const words=(o.rest_words||[]).map(w=>act(x,x.esc(w.label),'restSay',{v:w.id},`small ${u.say.includes(w.id)?'rw-on':'ghost'}`)).join('');
  const seg=[['self','Gửi đội trưởng'],['company','Nhờ công đoàn']].map(([id,l])=>act(x,l,'restTo',{v:id},`small ${u.to===id?'rw-on':'ghost'}`)).join('');
  const days=[1,2].map(n=>act(x,`${n} ngày`,'restN',{v:n},`small ${u.n===n?'rw-on':'ghost'}`)).join('');
  return pane(x,'rest','🛌 Xin nghỉ bù'+(o.tired?' · đang mệt':''),`<div class="rw-odd-row"><small>Xin</small><div class="rw-segs">${days}</div></div>
    <div class="rw-odd-row"><small>Vì</small><div class="rw-segs">${words}</div></div><div class="rw-odd-row"><small>Gửi</small><div class="rw-segs">${seg}</div></div>
    ${x.cmd('📝 Gửi đơn','rw_rest',{n:u.n,say:u.say,to:u.to},'primary',!u.say.length)}`,!!o.tired,'rw-rest');
}
function groundCard(x){
  const cd=odd(x).conduct||{};if(!cd.ground)return '';
  return `<section class="sk-event tense"><h3>⚖️ Tạm đình chỉ gác hôm nay</h3><p class="small">Chuyến tàu đang tới thì vẫn gác cho xong an toàn. Mai lên đội trình bày.</p></section>`;
}
function boardCard(x){
  const rows=(data(x).board||[]).map(b=>`<li class="${b.state}"><span aria-hidden="true">${x.esc(b.emoji)}</span><b>${x.esc(b.code)}</b><span>${x.esc(b.at)}</span><small>${b.state==='done'?'✓ đã qua':b.late?`chậm ${b.late}′`:x.esc(b.dir)}</small></li>`).join('');
  return rows?`<section class="card rw-board"><h4>🕐 Bảng giờ tàu</h4><ul class="rw-boardlist">${rows}</ul></section>`:'';
}

/* ------------------------------------------------------------ the guide (points; the choices stay the player's) */
function trainSteps(t,x){
  const d=data(x),rows=[],left=(t.left||[]).length,L=cc(x).lower_at||3;
  if(!d.on_duty)return [{ok:null,label:'Nhận ca, ký sổ giao ca trước',go:null}];
  if(t.eta==null)return [{ok:null,label:'Nhắc lại lệnh của ga',go:{sel:'.rw-radio .sk-opts',label:'📻 Chọn câu nhắc lại'},pulse:''}];
  if(t.standing){
    if(left)rows.push({ok:null,label:'Dẹp người, vật trên ray',go:{sel:'.rw-left',label:'👉 Dẹp khỏi ray'}});
    rows.push({ok:null,label:'Báo ga đường đã thông',go:{cmd:'rw_allclear',payload:{task:t.id},label:'📻 Báo ga đường thông'}});
    return rows;
  }
  if(!t.passed){
    const on=(t.pushers||[]).find(p=>p.state==='on');
    if(on)rows.push({ok:null,label:`${on.who.split(' · ')[0]} đòi qua: bạn trả lời sao?`,go:{sel:'.rw-push .sk-opts',label:'👉 Trả lời'},pulse:''});
    rows.push({ok:t.scanned||null,label:'Nhìn hai phía đường ngang',go:{cmd:'rw_scan',payload:{task:t.id},label:'👀 Nhìn đường ngang'}});
    if(t.scanned&&left)rows.push({ok:null,label:`Dẹp ${left} người/vật trên ray (không kịp thì báo dừng tàu)`,go:{sel:'.rw-left',label:'👉 Chọn cách dẹp'}});
    if(t.late_told&&!t.held&&!t.recalled&&t.arm==='down')rows.push({ok:null,label:'Tàu chậm: hỏi ga tàu còn đứng ở Bến Gỗ không',go:{sel:'.rw-ctl',label:'👉 Hỏi ga'}});
    if(t.held&&t.arm==='down')rows.push({ok:null,label:'Ga xác nhận tàu còn đứng: được nâng chắn tạm',go:{sel:'.rw-ctl',label:'👉 Nâng chắn tạm'}});
    rows.push({ok:t.bell!=null||null,label:'Bật chuông đèn trước khi hạ',go:{sel:'.rw-ctl',label:'👉 Chuông đèn'}});
    rows.push({ok:t.arm==='down'||null,label:`Hạ chắn khi tàu còn khoảng ${L} phút`,note:t.eta!=null?`còn ${t.eta}′`:'',go:{sel:'.rw-ctl',label:'👉 Hạ chắn'}});
    if(t.arm==='down'&&!t.stopped)rows.push({ok:t.flag==='green'||null,label:lamp(t)?'Giơ đèn trắng đón tàu':'Giơ cờ xanh đón tàu',go:{sel:'.rw-ctl',label:'👉 Đứng cờ'}});
    if(t.arm==='down')rows.push({ok:null,label:'Đứng chờ tàu qua',go:{sel:'.rw-ctl',label:'👉 Chờ tàu'}});
    return rows;
  }
  rows.push({ok:t.watched||null,label:'Nhìn hết đoàn tàu',go:{cmd:'rw_watch',payload:{task:t.id},label:'👁️ Nhìn đoàn tàu'}});
  if(t.watched&&t.seen&&(!t.seen.tail||t.seen.defect))rows.push({ok:null,label:'Thấy bất thường thì báo ga ngay',go:{sel:'.rw-after',label:'👉 Báo ga'}});
  if(t.arm==='down'){
    rows.push({ok:t.asked||null,label:'Hỏi ga còn tàu nào không',go:{sel:'.rw-after',label:'👉 Hỏi ga'}});
    rows.push({ok:null,label:'Nâng chắn, tắt chuông',go:{sel:'.rw-after',label:'👉 Nâng chắn'}});
  }else rows.push({ok:null,label:'Ghi sổ nhật ký đúng sự thật',go:{sel:'.rw-log',label:'👉 Chọn dòng ghi sổ'}});
  return rows;
}
function shiftSteps(t,x){
  const n=(cc(x).equip||[]).length,rows=[{ok:(t.checked||[]).length>=n||null,label:'Thử từng thiết bị',note:`${(t.checked||[]).length}/${n}`,go:{sel:'.rw-eqs',label:'👉 Thử thiết bị'}}];
  if(t.found){
    if(t.found_fix)rows.push({ok:t.fixed||null,label:'Tự xử lý chỗ hỏng',go:{cmd:'rw_fix',payload:{task:t.id},label:'🔧 Xử lý'}});
    rows.push({ok:(t.forms||[]).length?true:null,label:'Báo đúng nơi (nguy hiểm thì gọi ga)',go:{sel:'.rw-forms',label:'👉 Chọn nơi báo'}});
  }
  return rows;
}
function patrolSteps(t,x){
  const pts=t.needs?.points||[],walked=(t.walked||[]).length,next=pts.find(p=>!(t.walked||[]).includes(p.id));
  const rows=[{ok:walked>=pts.length||null,label:'Đi tới từng điểm',note:`${walked}/${pts.length}`,go:next?{cmd:'rw_walk',payload:{task:t.id,point:next.id},label:`🚶 Tới ${next.km}`}:null}];
  if(walked)rows.push({ok:null,label:'Chỗ nào có chuyện: xử lý, phòng vệ, ghi đúng phiếu',go:{sel:'.rw-pts',label:'👉 Xem các điểm'}});
  return rows;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở đường ngang',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(odd(x).ev)return {steps:[{ok:null,label:`Trả lời: ${odd(x).ev.title}`,go:{sel:'.rw-odd',label:'💬 Trả lời'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'rw_intro',payload:{},label:'🚦 Vào ca thôi!'}}],final:null};
  if(t.kind==='shift'){const steps=shiftSteps(t,x);return {steps,final:{label:'✍️ KÝ NHẬN CA',go:finalGo(steps,'rw_sign',{task:t.id}),ready:true}};}
  if(t.kind==='patrol'){if(!t.known)return {steps:[{ok:null,label:'Nhận sổ tuần đường',go:{cmd:'ask',payload:{task:t.id},label:'🔩 Nhận việc tuần đường'}}],final:null};
    const steps=patrolSteps(t,x);return {steps,final:{label:'📒 KÝ SỔ TUẦN ĐƯỜNG',go:finalGo(steps,'rw_patrol',{task:t.id}),ready:true}};}
  if(!t.known)return {steps:[{ok:null,label:'Nghe ga gọi bộ đàm',go:{cmd:'ask',payload:{task:t.id},label:'📻 Nghe ga gọi'}}],final:null,pulse:'.sk-ask'};
  return {steps:trainSteps(t,x),final:null};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});
const tops=x=>`${introCard(x,'rw_intro','🚦')}${deskCard(x,'rw_desk','Chuyện ở đường ngang')}${oddCard(x)}${groundCard(x)}`;

export default {
  id:'railway',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='shift'?'Nhận ca, thử thiết bị':t.kind==='patrol'?'Tuần đường':!t.known?'Nghe ga gọi':'Gác chuyến tàu';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x),top=tops(x);
    if(d.desk?.ev||odd(x).ev||!d.intro||x.ui.intro)return `<div class="career-job sk rw">${hint}${top}${bottom(x,g)}</div>`;
    let main='',side=stepRows(x,g.steps,t.kind==='train'?'Chuyến tàu':t.kind==='shift'?'Nhận ca':'Tuần đường');
    if(t.kind==='shift')main=shiftPanel(t,x);
    else if(t.kind==='patrol')main=t.known?patrolPanel(t,x):askCard(x,t,'🔩 Nhận việc tuần đường');
    else if(!t.known){main='';side='';}
    else if(t.eta==null)main=radioPanel(t,x);
    else if(t.passed&&t.arm==='up')main=logPanel(t,x);
    else if(t.passed)main=afterPanel(t,x);
    else main=`${pusherCard(t,x)}<section class="card rw-scene"><h4>🚦 Đường ngang</h4>${crossing(t,x)}${chips(t,x)}${clearList(t,x)}${controls(t,x)}</section>${pushLog(t,x)}`;
    const head=t.kind==='train'?`${ticket(t,x)}${dayBar(x)}`:dayBar(x);
    return `<div class="career-job sk rw">${hint}${top}${head}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x);
    if(d.desk?.ev||odd(x).ev||!d.intro||x.ui.intro){
      const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở đường ngang',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}
        :odd(x).ev?{steps:[{ok:null,label:`Trả lời: ${odd(x).ev.title}`,go:{sel:'.rw-odd',label:'💬 Trả lời'}}],final:null}
        :{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'rw_intro',payload:{},label:'🚦 Vào ca thôi!'}}],final:null};
      return `<div class="career-job sk rw">${hintFor(g,x)}${tops(x)}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk rw">${tops(x)}${dayBar(x)}${boardCard(x)}<section class="card"><h4>📁 Hồ sơ của bạn</h4>${record(x)}${restCard(x)}</section></div>`;
  },
  tick(root){keepBarAboveFooter(root);},
  summary(sum,x){
    if(!sum||sum.trains==null)return '';
    const lines=(Array.isArray(sum.lines)?sum.lines:[]).map(l=>`<li>${x.esc(l)}</li>`).join('');
    return `<section class="card rw-sum"><h4>🚦 Ca gác hôm nay</h4><ul class="rw-sumlist">${lines}</ul>${sum.note?`<p class="small muted">🌅 ${x.esc(sum.note)}</p>`:''}</section>`;
  },
  actions:{...kitActions,...oddActions,
    async remark(d,el,x){const m=(x.ui.remarks??={}),cur=m[d.task]||(m[d.task]=[]),i=cur.indexOf(d.k);if(i>=0)cur.splice(i,1);else cur.push(d.k);x.render();},
  },
  dock:[],
};
