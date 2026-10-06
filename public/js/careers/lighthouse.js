/** Người gác hải đăng — keeper of đèn biển Hòn Gió (server: game/careers/lighthouse.py).
 * Six kinds of job: the morning round (put the light out on time, test six pieces of equipment, clean the lens with the
 * rotation locked off, the fuel log, report a fault through the right channel, sign), the weather report (read four
 * instruments, report four values, warn the boats when it blows), the evening light (light up on time, time the flashes
 * against the list of lights, the fog horn, a truthful log), the sea (look, call, throw a buoy, relay at the right
 * priority and bearing, keep the target in sight; never go out alone), visitors (papers, the island's rules, shelter
 * for anyone in danger) and the supply boat (dip the tank, check the goods, sign the litres measured, haggle the
 * captain's basket). Around them: surprises, the chuyện oái oăm, the keeper's record and life on the rock (Mun the cat,
 * the vegetable boxes, the calls home). The server decides everything; the guide only points the way: every answer,
 * reading, priority and log line stays the player's own choice. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,lower,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,kitInput,amountBox,act,meter} from './street_kit.js';
import {ACTIONS as oddActions} from './air_kit.js';

const odd=x=>data(x).odd||{};
const KIND={charm:'Lời mời khó từ chối',harass:'Quấy rối',demand:'Yêu cầu oái oăm',corner:'Làm tắt',bargain:'Mặc cả với xí nghiệp'};
const ui=(x,t)=>((x.ui.job??={})[t.id]??={});

/* ------------------------------------------------------------ small pieces */
function choiceRow(x,list,cur,action,tid,key){
  return `<div class="hd-segs">${list.map(([id,label])=>act(x,x.esc(label),action,{task:tid,key,v:id},`small ${String(cur)===String(id)?'hd-on':'ghost'}`,` aria-pressed="${String(cur)===String(id)}"`)).join('')}</div>`;
}
function timeCard(x,t,title,when,cmd,chosen){
  const n=t.needs||{};
  const opts=(n.times||[]).map((at,i)=>x.cmd(`🕰️ ${x.esc(at)}`,cmd,{task:t.id,option:i},`hd-time ${chosen===i?'hd-on':'ghost'}`,chosen!=null)).join('');
  return `<section class="card hd-times"><h4>${title}</h4><p class="small">${x.esc(when)} · <span class="muted">${x.esc(n.rule||'')}</span></p><div class="hd-row3">${opts}</div></section>`;
}

/* ------------------------------------------------------------ dawn: the morning round */
function dawnPanel(t,x){
  const n=t.needs||{},eq=cc(x).equip||[],forms=cc(x).forms||{};
  const tiles=eq.map(e=>{const on=(t.checked||[]).includes(e.id),bad=on&&t.found_item===e.id;
    return `<button type="button" class="tile sk-tile hd-eq ${on?(bad?'bad':'selected'):''}" data-command="hd_check" data-payload="${x.esc(JSON.stringify({task:t.id,item:e.id}))}"${on?' disabled':''}><span class="tile-emoji">${x.esc(e.emoji)}</span><b>${x.esc(e.name)}</b><small>${on?(bad?'⚠️ hỏng':'✓ ổn'):x.esc(e.test)}</small></button>`;}).join('');
  const lens=(t.checked||[]).includes('lens');
  const clean=!lens?'':t.cleaned?`<p class="small hd-ok">✓ Đã lau kính${t.cleaned==='quick'?' (lúc đèn còn quay)':''}</p>`
    :`<div class="hd-row2">${x.cmd('🔒 Tắt mô-tơ, treo biển rồi lau','hd_clean',{task:t.id,how:'lock'},'')}${x.cmd('🧽 Lau luôn khi đèn còn quay','hd_clean',{task:t.id,how:'quick'},'ghost')}</div>`;
  const fuel=t.fuel_seen==null?'<p class="small muted">Đo bồn dầu ở máy phát trước đã.</p>'
    :`<p class="small">📏 Thước đo bồn: <b>${x.fmt(t.fuel_seen)} lít</b>${t.fuel_log!=null?` · sổ đang ghi ${x.fmt(t.fuel_log)} lít`:''}</p>${amountBox(x,`fuel-${t.id}`,300,{min:0,max:5000,step:5,label:'Ghi sổ dầu',send:'⛽ Ghi sổ dầu',cmd:'hd_fuel',payload:{task:t.id},field:'litres',unit:'lít'})}`;
  const fault=t.found?`<section class="card hd-fault"><h4>⚠️ ${x.esc(t.found_text)}</h4>
    ${t.found_fix?(t.fixed?'<span class="tag green">✓ Đã xử lý</span>':x.cmd(`🔧 ${x.esc(t.found_fix)}`,'hd_fix',{task:t.id},'')):'<p class="small muted">Không tự sửa được: báo đúng nơi để thợ ra đảo.</p>'}
    <p class="small"><b>Báo ở đâu?</b> Chọn một hoặc nhiều.</p><div class="hd-forms">${Object.entries(forms).map(([k,f])=>x.cmd(`${x.esc(f.emoji)} ${x.esc(f.name)}<small>${x.esc(f.hint)}</small>`,'hd_form',{task:t.id,form:k},`hd-form ${(t.forms||[]).includes(k)?'hd-on':'ghost'}`)).join('')}</div></section>`:'';
  return `${timeCard(x,t,'💡 Tắt đèn',`Mặt trời mọc ${n.rise||''}`,'hd_off',t.off)}<p class="small hd-handover">📒 ${x.esc(n.handover||'')}</p>
    <section class="card"><h4>🧰 Thử thiết bị <small class="muted">${(t.checked||[]).length}/${eq.length}</small></h4><div class="tile-grid hd-eqs">${tiles}</div>${clean}</section>
    ${fault}<section class="card hd-fuel"><h4>⛽ Sổ dầu</h4>${fuel}</section>`;
}

/* ------------------------------------------------------------ the weather watch */
function weatherPanel(t,x){
  const c=cc(x),seen=t.seen||{},u=ui(x,t),ins=c.instruments||{};
  const reads=Object.entries(ins).map(([k,v])=>seen[k]?`<li><span aria-hidden="true">${x.esc(v.emoji)}</span><div><b>${x.esc(v.short)}</b><small>${x.esc(seen[k])}</small></div></li>`
    :`<li>${x.cmd(`${x.esc(v.emoji)} ${x.esc(v.name)}`,'hd_read',{task:t.id,what:k},'ghost hd-read')}</li>`).join('');
  const beau=(c.beaufort||[]).map(([n,lo,hi])=>`<span><b>${n}</b> ${lo}–${hi}</span>`).join('');
  if(t.report){
    const r=t.report;
    return `<section class="card hd-wx"><h4>🌬️ Quan trắc ${x.esc(t.needs?.hour||'')}</h4><ul class="hd-reads">${reads}</ul></section>
      <section class="card hd-sent"><h4>📻 Đã báo đài</h4><p class="small">Gió cấp ${r.wind} · ${x.esc((c.sea_states||{})[r.sea]||'')} · tầm nhìn ${x.esc(lower((c.vis||{})[r.vis]||''))} · áp ${x.esc(lower((c.baro||{})[r.baro]||''))}</p>
      ${t.warned?'<span class="tag amber">📢 Đã phát cảnh báo</span>':x.cmd('📢 Phát cảnh báo trên kênh 16','hd_warn',{task:t.id},'ghost hd-warn')}</section>`;
  }
  const wind=choiceRow(x,Array.from({length:10},(_,i)=>[i,String(i)]),u.wind,'pick',t.id,'wind');
  const row=(k,label,map)=>`<div class="hd-field"><small>${label}</small>${choiceRow(x,Object.entries(map||{}),u[k],'pick',t.id,k)}</div>`;
  const ready=u.wind!=null&&u.sea&&u.vis&&u.baro;
  const payload={task:t.id,wind:Number(u.wind),sea:u.sea,vis:u.vis,baro:u.baro};
  return `<section class="card hd-wx"><h4>🌬️ Quan trắc ${x.esc(t.needs?.hour||'')}</h4><ul class="hd-reads">${reads}</ul>
      ${pane(x,'beaufort','📏 Bảng cấp gió (m/s)',`<div class="hd-beau">${beau}</div>`,false,'hd-beau-pane')}</section>
    <section class="card hd-report"><h4>📻 Báo đài</h4><div class="hd-field"><small>Cấp gió</small>${wind}</div>
      ${row('sea','Mặt biển',c.sea_states)}${row('vis','Tầm nhìn',c.vis)}${row('baro','Áp suất',c.baro)}
      ${x.cmd(ready?'📻 Báo đài số liệu':'Chọn đủ bốn số liệu','hd_report',payload,'primary full',!ready)}</section>`;
}

/* ------------------------------------------------------------ the evening light */
function duskPanel(t,x){
  const n=t.needs||{},c=cc(x),tired=odd(x).tired&&!t.awake&&t.lit==null;
  const wake=tired?`<p class="hd-tired">😮‍💨 Mắt díp lại rồi. ${x.cmd('🚰 Rửa mặt, pha trà cho tỉnh','hd_wake',{task:t.id},'small primary')}</p>`:'';
  let rest='';
  if(t.lit!=null){
    const count=t.counted?`<p class="hd-count">⏱️ Đếm được: <b>${x.esc(t.count_text)}</b><br><small class="muted">Danh mục đèn: ${x.esc(n.chart||'')} · ${x.esc(n.code||'')}</small></p>`
      :x.cmd('⏱️ Bấm giờ đếm chớp','hd_count',{task:t.id},'primary');
    const radio=t.counted?((t.radioed||[]).includes('char')?'<span class="tag green">✓ Đã báo đài đèn sai đặc tính</span>':x.cmd('📻 Báo đài: đèn sai đặc tính','hd_radio',{task:t.id,what:'char'},'ghost')):'';
    const horn=t.horn?(t.horn_dead?((t.radioed||[]).includes('horn')?'<span class="tag green">✓ Đã báo đài còi hỏng</span>':x.cmd('📻 Báo đài: còi sương mù hỏng','hd_radio',{task:t.id,what:'horn'},'primary')):'<span class="tag blue">📯 Còi đang chạy</span>')
      :x.cmd('📯 Chạy còi sương mù','hd_horn',{task:t.id},n.fog?'':'ghost');
    const sel=x.ui.remarks?.[t.id]||[],rem=c.remarks||{};
    const chips=Object.entries(rem).map(([k,v])=>act(x,x.esc(v),'remark',{task:t.id,k},`small ${sel.includes(k)?'hd-on':'ghost'}`,` aria-pressed="${sel.includes(k)}"`)).join('');
    rest=`<section class="card hd-signal"><h4>🔆 Đặc tính đèn${n.fog?' · 🌫️ sương mù':''}</h4>${count}<div class="hd-row2">${radio}${horn}</div></section>
      <section class="card hd-log"><h4>📒 Sổ trực buổi tối</h4><p class="small muted">Chọn đúng những gì đã xảy ra tối nay.</p><div class="hd-remarks">${chips}</div>
      ${x.cmd('✍️ GHI SỔ TRỰC TỐI','hd_log',{task:t.id,remarks:sel},'primary full',!sel.length)}</section>`;
  }
  return `${wake}${timeCard(x,t,'💡 Thắp đèn',`Mặt trời lặn ${n.set||''}`,'hd_light',t.lit)}${rest}`;
}

/* ------------------------------------------------------------ the sea */
function seaPanel(t,x){
  const n=t.needs||{},c=cc(x),u=ui(x,t);
  if(!t.looked)return `<section class="card hd-sea"><p>${x.esc(t.opening)}</p>${x.cmd('🔭 Nhìn kỹ qua ống nhòm','hd_look',{task:t.id},'primary full hd-look')}</section>`;
  const did=t.did||[];
  let call='';
  if(n.talk==='reef')call=t.talk_out?`<p class="hd-said">${x.esc(t.talk_line||'')}</p>`:x.cmd('📻 Gọi tàu trên kênh 16','hd_vhf',{task:t.id},'primary');
  else if(n.talk){
    const words=c.words||{},say=u.say||[];
    const chips=Object.entries(words).map(([k,w])=>act(x,`${x.esc(w.emoji)} ${x.esc(w.name)}`,'say',{task:t.id,k},`small ${say.includes(k)?'hd-on':'ghost'}`,` aria-pressed="${say.includes(k)}"`)).join('');
    const open=t.talk_out==null||t.talk_out==='again';
    call=`${t.talk_line?`<p class="hd-said">${x.esc(t.talk_line)}</p>`:''}${open?`<div class="hd-field"><small>Nói gì (1–2 ý)</small><div class="hd-segs">${chips}</div></div>${x.cmd(say.length?'📻 Gọi tàu trên kênh 16':'Chọn điều muốn nói','hd_vhf',{task:t.id,say},'primary',!say.length)}`:''}`;
  }
  const acts=['horn','lamp','buoy','track'].map(k=>{const a=(c.sea_acts||{})[k];
    return did.includes(k)?`<span class="tag green">✓ ${x.esc(a.name)}</span>`:x.cmd(`${x.esc(a.emoji)} ${x.esc(a.name)}`,'hd_act',{task:t.id,what:k},'ghost hd-act');}).join('');
  const tempt=['boat','swim'].map(k=>{const a=(c.sea_acts||{})[k];return did.includes(k)?`<span class="tag danger">${x.esc(a.name)}</span>`:x.cmd(`${x.esc(a.emoji)} ${x.esc(a.name)}`,'hd_act',{task:t.id,what:k},'ghost hd-risk');}).join('');
  let relay;
  if(t.relay){const r=t.relay,k=(c.relay||{})[r.kind]||{};relay=`<p class="small">${x.esc(k.emoji||'')} Đã báo: ${x.esc(k.name||'')} · phương vị ${x.esc(r.bearing)}${r.persons!=null?` · ${r.persons} người`:''}</p>`;}
  else{
    const kinds=Object.entries(c.relay||{}).map(([k,v])=>act(x,`${x.esc(v.emoji)} ${x.esc(v.name)}<small>${x.esc(v.hint)}</small>`,'pick',{task:t.id,key:'kind',v:k},`hd-kind ${u.kind===k?'hd-on':'ghost'}`,` aria-pressed="${u.kind===k}"`)).join('');
    const bear=choiceRow(x,(n.bearings||[]).map(b=>[b,`${b}°`]),u.bearing,'pick',t.id,'bearing');
    const per=n.persons&&u.kind!=='border'?`<div class="hd-field"><small>Số người</small>${choiceRow(x,n.persons.map(p=>[p,`${p} người`]),u.persons,'pick',t.id,'persons')}</div>`:'';
    const ready=u.kind&&u.bearing&&(!n.persons||u.kind==='border'||u.persons!=null);
    relay=`<div class="hd-kinds">${kinds}</div><div class="hd-field"><small>Phương vị</small>${bear}</div>${per}
      ${x.cmd(ready?'📻 Báo đài':'Chọn mức báo, phương vị'+(n.persons?', số người':''),'hd_relay',{task:t.id,kind:u.kind,bearing:u.bearing,...(u.persons!=null?{persons:Number(u.persons)}:{})},'primary full',!ready)}`;
  }
  return `<section class="card hd-sea"><p class="hd-seen">🔭 ${x.esc(t.seen||'')}</p>${call}<div class="hd-acts">${acts}</div>
      <details class="hd-tempt"><summary>Liều mạng…</summary><div class="hd-row2">${tempt}</div><p class="small muted">Một mình ra khơi, nhảy xuống bơi là thành người thứ hai cần cứu.</p></details></section>
    <section class="card hd-relay"><h4>📻 Báo đài duyên hải</h4>${relay}</section>`;
}

/* ------------------------------------------------------------ visitors */
function visitorPanel(t,x){
  const n=t.needs||{},c=cc(x),ans=c.answers||{};
  const papers=t.papers?`<p class="hd-papers">🪪 ${x.esc(t.papers_text||'')}</p>`:x.cmd('🪪 Xem giấy tờ','hd_papers',{task:t.id},'primary');
  const open=t.out==null||t.out==='again';
  const btn=k=>{const a=ans[k]||{emoji:'',name:k};return x.cmd(`<span class="sk-opt-label">${x.esc(a.emoji)} ${x.esc(a.name)}</span>`,'hd_answer',{task:t.id,answer:k},`sk-opt hd-ans ${k==='give'?'hd-give':''}`);};
  const answers=open?`<div class="sk-opts">${['escort','yard','refuse','shelter','report'].map(btn).join('')}</div>
    <details class="hd-tempt"><summary>Chiều theo…${t.offer?` (họ dúi ${t.offer} xu)`:''}</summary>${btn('give')}<p class="small muted">Không ai vào phòng đèn, không ai ở lại trái nội quy.</p></details>`:'';
  const stop=t.sneak&&!t.stopped?`<section class="sk-event tense"><h3>🏃 Có người đang leo cầu thang tháp!</h3>${x.cmd('🧗 Chạy lên chặn, mời xuống, khóa cửa tháp','hd_stop',{task:t.id},'primary full')}</section>`:'';
  const who=x.npc(t.npc);
  return `${stop}<section class="sk-event ${n.night?'tense':''} hd-visit"><div class="sk-ev-head">${x.portrait(who,40)}<div class="grow"><small>${x.esc(n.wants||'')}${n.night?' · 🌙 ban đêm':''}</small><h3>${x.esc(n.emoji||'')} ${x.esc(n.who||'')}</h3></div>${t.round?'<span class="tag">2/2</span>':''}</div>
    <p class="hd-line">${x.esc(t.line||'')}</p>${papers}${answers}</section>`;
}

/* ------------------------------------------------------------ the supply boat */
function supplyPanel(t,x){
  const n=t.needs||{},c=cc(x),dips=t.dips||{},st=t.states||{};
  const dip=w=>dips[w]!=null?`<span class="tag blue">📏 ${w==='before'?'Trước':'Sau'}: ${x.fmt(dips[w])} lít</span>`:x.cmd(`📏 Đo bồn ${w==='before'?'trước khi bơm':'sau khi bơm'}`,'hd_dip',{task:t.id,when:w},'ghost',w==='after'&&dips.before==null);
  const goods=(n.goods||[]).map(g=>{const s=st[g.id],noted=(t.noted||[]).includes(g.id);
    return `<li class="${s&&s!=='ok'?'bad':''}"><div class="row"><span class="hd-em" aria-hidden="true">${x.esc(g.emoji)}</span><div class="grow"><b>${x.esc(g.name)}</b>${s?`<small>${x.esc((c.goods_state||{})[s]||'')}</small>`:''}</div>
      ${s?x.cmd(noted?'✍️ Đã ghi thiếu/hỏng':'✍️ Ghi thiếu/hỏng','hd_note',{task:t.id,item:g.id},`small ${noted?'hd-on':'ghost'}`):x.cmd('🔍 Kiểm','hd_goods',{task:t.id,item:g.id},'small')}</div></li>`;}).join('');
  const b=n.basket||{};
  const basket=t.buy?`<p class="small">${t.buy==='bought'?`🧺 Đã mua giỏ: ${x.fmt(t.offers[t.offers.length-1])} xu.`:t.buy==='walked'?'🧺 Chú Tư Lực mang giỏ về.':'🧺 Không mua giỏ.'}</p>`
    :`<p class="small">${x.esc(b.items||'')} · chú hét <b>${x.fmt(b.ask)} xu</b>${t.counter?` · trả lại: <b>${x.fmt(t.counter)} xu</b>`:''}</p>
      ${amountBox(x,`basket-${t.id}`,t.counter||Math.round((b.ask||40)*.6),{min:1,max:b.ask||100,label:'Bạn trả',send:'🧺 Trả giá',cmd:'hd_offer',payload:{task:t.id},field:'price'})}
      ${x.cmd('Thôi, không mua','hd_skipbuy',{task:t.id},'ghost small')}`;
  return `<section class="card hd-dip"><h4>⛽ Dầu: phiếu ghi ${x.fmt(n.claim)} lít</h4><div class="hd-row2">${dip('before')}${dip('after')}</div>
      ${amountBox(x,`litres-${t.id}`,n.claim||200,{min:0,max:1000,step:5,label:'Ký nhận số lít',send:'✍️ KÝ PHIẾU GIAO HÀNG',cmd:'hd_ssign',payload:{task:t.id},field:'litres',unit:'lít'})}</section>
    <section class="card hd-goods"><h4>📦 Hàng theo phiếu</h4><ul class="hd-list">${goods}</ul></section>
    ${pane(x,`basket-${t.id}`,`🧺 ${x.esc(b.name||'Giỏ hàng riêng')}`,basket,!t.buy,'hd-basket')}`;
}

/* ------------------------------------------------------------ chuyện oái oăm, the record, rest days, life on the rock */
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
  const u=draft(x,ev),who=ev.npc?x.portrait(x.npc(ev.npc),40):`<span class="hd-av" aria-hidden="true">${x.esc(ev.emoji)}</span>`;
  const seg=(list,cur,a)=>list.map(i=>act(x,x.esc(i.label),a,{v:i.id},`small ${cur===i.id?'hd-on':'ghost'}`,` aria-pressed="${cur===i.id}"`)).join('');
  const words=ev.words.map(w=>act(x,x.esc(w.label),'oddSay',{v:w.id},`small ${u.say.includes(w.id)?'hd-on':'ghost'}${w.id==='yes'?' hd-give':''}`,` aria-pressed="${u.say.includes(w.id)}"`)).join('');
  const b=ev.bargain;
  const count=b?`<div class="hd-odd-row"><small>Nhận</small><div class="hd-step">${act(x,'−','oddN',{v:-1},'small ghost',' aria-label="Bớt"')}<b>${u.n}/${b.ask} ${x.esc(b.unit)}</b>${act(x,'+','oddN',{v:1},'small ghost',' aria-label="Thêm"')}<small class="muted">hợp lý ≤ ${b.limit}</small></div></div>`:'';
  const ready=u.tone&&u.say.length,payload={tone:u.tone||'soft',say:u.say,to:u.to,...(b?{n:u.n}:{})};
  const thread=ev.said.length?`<p class="small muted">Bạn (${x.esc(ev.said[ev.said.length-1].tone.toLowerCase())}): ${x.esc(ev.said[ev.said.length-1].say.join(' '))}</p>`:'';
  return `<section class="sk-event tense hd-odd" role="group" aria-labelledby="hd-odd-title"><div class="sk-ev-head">${who}<div class="grow"><small>${x.esc(KIND[ev.kind]||'')} · ${x.esc(ev.who)}</small><h3 id="hd-odd-title">${x.esc(ev.title)}</h3></div>${ev.round>1?`<span class="tag">${ev.round}/${ev.rounds}</span>`:''}</div>
    ${thread}<p class="hd-line">${x.esc(ev.line)}</p>${ev.cue?`<p class="small">${x.esc(ev.cue)}</p>`:''}
    <div class="hd-odd-row"><small>Giọng</small><div class="hd-segs">${seg(ev.tones,u.tone,'oddTone')}</div></div>
    <div class="hd-odd-row"><small>Nói</small><div class="hd-segs">${words}</div></div>${count}
    ${ev.channels.length>1?`<div class="hd-odd-row"><small>Báo</small><div class="hd-segs">${seg(ev.channels,u.to,'oddTo')}</div></div>`:''}
    ${x.cmd(ready?'💬 Nói':'Chọn giọng và ý muốn nói','hd_odd',payload,'primary full',!ready)}</section>`;
}
function record(x){
  const o=odd(x),cd=o.conduct||{},lv=cd.level||'ok',f=o.fatigue||0;
  return `<div class="hd-record"><span class="tag ${lv==='ok'?'green':'amber'}">${lv==='ok'?'✅':lv==='note'?'📝':lv==='warn'?'⚠️':'⚖️'} ${x.esc(cd.label||'Hồ sơ sạch')}</span>
    <span class="tag ${o.tired?'danger':''}">😮‍💨 Mệt ${f}/6</span></div>`;
}
function restCard(x){
  const o=odd(x);
  if(o.rest_today)return '<p class="small muted">📝 Hôm nay đã xin nghỉ rồi.</p>';
  const u=x.ui.rest||(x.ui.rest={n:1,say:[],to:'self'});
  const words=(o.rest_words||[]).map(w=>act(x,x.esc(w.label),'restSay',{v:w.id},`small ${u.say.includes(w.id)?'hd-on':'ghost'}`)).join('');
  const seg=[['self','Gửi xí nghiệp'],['company','Nhờ công đoàn']].map(([id,l])=>act(x,l,'restTo',{v:id},`small ${u.to===id?'hd-on':'ghost'}`)).join('');
  const days=[1,2].map(n=>act(x,`${n} ngày`,'restN',{v:n},`small ${u.n===n?'hd-on':'ghost'}`)).join('');
  return pane(x,'rest','🛌 Xin nghỉ bù'+(o.tired?' · đang mệt':''),`<div class="hd-odd-row"><small>Xin</small><div class="hd-segs">${days}</div></div>
    <div class="hd-odd-row"><small>Vì</small><div class="hd-segs">${words}</div></div><div class="hd-odd-row"><small>Gửi</small><div class="hd-segs">${seg}</div></div>
    ${x.cmd('📝 Gửi đơn','hd_rest',{n:u.n,say:u.say,to:u.to},'primary',!u.say.length)}`,!!o.tired,'hd-rest');
}
function lifeCard(x){
  const d=data(x),l=d.life||{},max=l.max||10;
  const sup=d.supply_in===0?'⛴️ Hôm nay có tàu tiếp tế':`⛴️ Còn ${d.supply_in} ngày tới tàu tiếp tế`;
  return `<section class="card hd-life"><h4>🏝️ Đời sống trên đảo</h4>
    <div class="hd-meter"><small>Nhớ nhà</small>${meter(l.lonely||0,max,(l.lonely||0)>=(l.tired||7)?'bad':'')}<b>${l.lonely||0}/${max}</b></div>
    <p class="small">🥬 Đồ tươi còn ${l.fresh||0} ngày · 🪴 Vườn rau ${l.garden||0}/${l.ripe||5} · ${sup}</p>
    <div class="hd-row3">${x.cmd(l.pet?'🐈‍⬛ Mun đang ngủ':'🐈‍⬛ Chơi với Mun','hd_pet',{},'ghost',!!l.pet)}${x.cmd(l.watered?'🪴 Đã tưới':'🪴 Tưới vườn rau','hd_garden',{},'ghost',!!l.watered)}${x.cmd(l.called?'📞 Đã gọi':'📞 Gọi về nhà','hd_call',{},'ghost',!!l.called)}</div></section>`;
}
function groundCard(x){
  const cd=odd(x).conduct||{};if(!cd.ground)return '';
  return `<section class="sk-event tense"><h3>⚖️ Tạm đình chỉ trực hôm nay</h3><p class="small">Đèn vẫn phải sáng: chú Bảy trực thay. Mai lên trình bày qua bộ đàm.</p></section>`;
}

/* ------------------------------------------------------------ the guide (points; the choices stay the player's) */
const need=(x)=>!data(x).on_duty?[{ok:null,label:'Làm ca sáng, ký sổ trực trước',go:null}]:null;
function dawnSteps(t,x){
  const n=(cc(x).equip||[]).length,rows=[{ok:t.off!=null||null,label:'Tắt đèn đúng giờ',go:{sel:'.hd-times',label:'👉 Chọn giờ tắt đèn'}},
    {ok:(t.checked||[]).length>=n||null,label:'Thử từng thiết bị',note:`${(t.checked||[]).length}/${n}`,go:{sel:'.hd-eqs',label:'👉 Thử thiết bị'}}];
  if((t.checked||[]).includes('lens'))rows.push({ok:t.cleaned?true:null,label:'Lau kính đèn (an toàn)',go:{sel:'.hd-row2',label:'👉 Lau kính'}});
  rows.push({ok:t.fuel_log!=null||null,label:'Ghi sổ dầu đúng số đo',go:{sel:'.hd-fuel',label:'👉 Sổ dầu'}});
  if(t.found){
    if(t.found_fix)rows.push({ok:t.fixed||null,label:'Tự xử lý chỗ hỏng',go:{cmd:'hd_fix',payload:{task:t.id},label:'🔧 Xử lý'}});
    rows.push({ok:(t.forms||[]).length?true:null,label:'Báo đúng nơi (ảnh hưởng đèn, còi thì báo đài)',go:{sel:'.hd-forms',label:'👉 Chọn nơi báo'}});
  }
  return rows;
}
function weatherSteps(t,x){
  const ins=Object.keys(cc(x).instruments||{}),read=Object.keys(t.seen||{}).length;
  const rows=[{ok:read>=ins.length||null,label:'Đọc đủ bốn thứ',note:`${read}/${ins.length}`,go:{sel:'.hd-reads',label:'👉 Quan trắc'}},
    {ok:t.report?true:null,label:'Báo đài bốn số liệu',go:{sel:'.hd-report',label:'👉 Báo đài'}}];
  if(t.report)rows.push({ok:t.warned||null,label:`Gió từ cấp ${cc(x).warn_wind||6} hoặc áp giảm nhanh thì cảnh báo tàu thuyền`,go:{sel:'.hd-sent',label:'👉 Xem có cần cảnh báo'}});
  return rows;
}
function duskSteps(t,x){
  const rows=[{ok:t.lit!=null||null,label:'Thắp đèn trước giờ lặn 15 phút',go:{sel:'.hd-times',label:'👉 Chọn giờ thắp đèn'}}];
  if(t.lit!=null){
    rows.push({ok:t.counted||null,label:'Đếm chớp so với danh mục đèn',go:{cmd:'hd_count',payload:{task:t.id},label:'⏱️ Đếm chớp'}});
    if(t.needs?.fog)rows.push({ok:t.horn||null,label:'Sương mù: chạy còi',go:{cmd:'hd_horn',payload:{task:t.id},label:'📯 Chạy còi'}});
    rows.push({ok:null,label:'Ghi sổ trực đúng sự thật',go:{sel:'.hd-log',label:'👉 Chọn dòng ghi sổ'}});
  }
  return rows;
}
function seaSteps(t,x){
  if(!t.looked)return [{ok:null,label:'Nhìn kỹ qua ống nhòm',go:{cmd:'hd_look',payload:{task:t.id},label:'🔭 Nhìn kỹ'}}];
  const rows=[];
  if(t.needs?.talk&&(t.talk_out==null||t.talk_out==='again'))rows.push({ok:null,label:'Gọi tàu trên kênh 16',go:{sel:'.hd-sea',label:'👉 Gọi tàu'}});
  rows.push({ok:t.relay?true:null,label:'Báo đài đúng mức, đúng phương vị (nếu cần)',go:{sel:'.hd-relay',label:'👉 Báo đài'}});
  rows.push({ok:null,label:'Ném phao, kéo còi, canh giữ mục tiêu: tùy chuyện',go:{sel:'.hd-acts',label:'👉 Việc ngoài bến'}});
  return rows;
}
function visitorSteps(t,x){
  const rows=[{ok:t.papers||null,label:'Xem giấy tờ',go:{cmd:'hd_papers',payload:{task:t.id},label:'🪪 Xem giấy tờ'}}];
  if(t.out==null||t.out==='again')rows.push({ok:null,label:'Trả lời theo nội quy trạm',go:{sel:'.hd-visit .sk-opts',label:'👉 Trả lời'},pulse:''});
  if(t.sneak&&!t.stopped)rows.push({ok:null,label:'Có người leo lên tháp: đưa xuống',go:{cmd:'hd_stop',payload:{task:t.id},label:'🧗 Chặn lại'}});
  return rows;
}
function supplySteps(t,x){
  const dips=Object.keys(t.dips||{}).length,seen=Object.keys(t.states||{}).length,n=(t.needs?.goods||[]).length;
  return [{ok:dips>=2||null,label:'Đo bồn trước và sau khi bơm',note:`${dips}/2`,go:{sel:'.hd-dip',label:'👉 Đo bồn'}},
    {ok:seen>=n||null,label:'Kiểm từng món, ghi món thiếu, hỏng',note:`${seen}/${n}`,go:{sel:'.hd-goods',label:'👉 Kiểm hàng'}},
    {ok:null,label:'Ký đúng số lít đo được',go:{sel:'.hd-dip .sk-amt',label:'👉 Ký phiếu'}}];
}
const FINAL={dawn:['✍️ KÝ SỔ TRỰC','hd_sign'],weather:['📒 GHI SỔ QUAN TRẮC','hd_wdone'],sea:['📒 GHI SỔ TRỰC','hd_sdone'],visitor:['📒 GHI SỔ KHÁCH','hd_vdone']};
const STEPS={dawn:dawnSteps,weather:weatherSteps,dusk:duskSteps,sea:seaSteps,visitor:visitorSteps,supply:supplySteps};
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện trên đảo',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(odd(x).ev)return {steps:[{ok:null,label:`Trả lời: ${odd(x).ev.title}`,go:{sel:'.hd-odd',label:'💬 Trả lời'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'hd_intro',payload:{},label:'🗼 Vào ca thôi!'}}],final:null};
  if(!t.known){const lab=t.kind==='sea'?'🔭 Nhìn ra biển':t.kind==='supply'?'⛴️ Ra bến đón tàu':'🚤 Ra bến đón khách';
    return {steps:[{ok:null,label:lab.replace(/^[^\p{L}]+/u,''),go:{cmd:'ask',payload:{task:t.id},label:lab}}],final:null,pulse:'.sk-ask'};}
  if(t.kind!=='dawn'){const n=need(x);if(n)return {steps:n,final:null};}
  const steps=STEPS[t.kind](t,x),f=FINAL[t.kind];
  if(t.kind==='weather'&&!t.report)return {steps,final:null};
  if(t.kind==='visitor'&&(t.out==null||t.out==='again'))return {steps,final:null};
  return {steps,final:f?{label:f[0],go:finalGo(steps,f[1],{task:t.id}),ready:true}:null};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});
const tops=x=>`${introCard(x,'hd_intro','🗼')}${deskCard(x,'hd_desk','Chuyện trên đảo')}${oddCard(x)}${groundCard(x)}`;
const TITLE={dawn:'Ca sáng',weather:'Quan trắc',dusk:'Thắp đèn',sea:'Canh biển',visitor:'Khách ra đảo',supply:'Tàu tiếp tế'};

export default {
  id:'lighthouse',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return TITLE[t.kind]||'Việc trên đảo';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x),top=tops(x);
    if(d.desk?.ev||odd(x).ev||!d.intro||x.ui.intro)return `<div class="career-job sk hd">${hint}${top}${bottom(x,g)}</div>`;
    let main='',side=stepRows(x,g.steps,TITLE[t.kind]||'Việc cần làm');
    const lab=t.kind==='sea'?'🔭 Nhìn ra biển':t.kind==='supply'?'⛴️ Ra bến đón tàu':'🚤 Ra bến đón khách';
    if(!t.known){main=askCard(x,t,lab);side='';}
    else if(t.kind==='dawn')main=dawnPanel(t,x);
    else if(t.kind==='weather')main=weatherPanel(t,x);
    else if(t.kind==='dusk')main=duskPanel(t,x);
    else if(t.kind==='sea')main=seaPanel(t,x);
    else if(t.kind==='visitor')main=visitorPanel(t,x);
    else main=supplyPanel(t,x);
    return `<div class="career-job sk hd">${hint}${top}${dayBar(x,` · 🌅 ${x.esc(d.rise||'')} · 🌇 ${x.esc(d.set||'')}`)}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x);
    if(d.desk?.ev||odd(x).ev||!d.intro||x.ui.intro){
      const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện trên đảo',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}
        :odd(x).ev?{steps:[{ok:null,label:`Trả lời: ${odd(x).ev.title}`,go:{sel:'.hd-odd',label:'💬 Trả lời'}}],final:null}
        :{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'hd_intro',payload:{},label:'🗼 Vào ca thôi!'}}],final:null};
      return `<div class="career-job sk hd">${hintFor(g,x)}${tops(x)}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk hd">${tops(x)}${dayBar(x)}${lifeCard(x)}<section class="card"><h4>📁 Hồ sơ của bạn</h4>${record(x)}${restCard(x)}</section></div>`;
  },
  tick(root){keepBarAboveFooter(root);},
  input(el,x){return kitInput(el,x);},
  summary(sum,x){
    if(!sum||sum.lit==null)return '';
    const lines=(Array.isArray(sum.lines)?sum.lines:[]).map(l=>`<li>${x.esc(l)}</li>`).join('');
    return `<section class="card hd-sum"><h4>🗼 Ca trực hôm nay</h4><ul class="hd-sumlist">${lines}</ul>${sum.note?`<p class="small muted">🌅 ${x.esc(sum.note)}</p>`:''}</section>`;
  },
  actions:{...kitActions,...oddActions,
    async remark(d,el,x){const m=(x.ui.remarks??={}),cur=m[d.task]||(m[d.task]=[]),i=cur.indexOf(d.k);if(i>=0)cur.splice(i,1);else cur.push(d.k);x.render();},
    async pick(d,el,x){const u=((x.ui.job??={})[d.task]??={});u[d.key]=d.v;x.render();},
    async say(d,el,x){const u=((x.ui.job??={})[d.task]??={}),s=u.say||(u.say=[]),i=s.indexOf(d.k);if(i>=0)s.splice(i,1);else if(s.length<2)s.push(d.k);x.render();},
  },
  dock:[],
};
