/** Khách sạn Sông Mây: one post of the shift per job (desk, rooms, laundry, breakfast, repairs, decor), one step at a
 * time. The server grades each step; a wrong one stays open to fix and lowers the job's quality. */
import {data,cc,person,askCard,introCard,deskCard,kitActions,amountBox,kitInput,notesPage,act} from './street_kit.js';
import {clean,tip} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk hotel">${body}</div>`;
const stepsOf=t=>t.needs?.steps||[];
const current=t=>stepsOf(t)[t.at];
const keyOf=(t,st)=>`${t.id}:${st.id}`;

function seasonBanner(x,s){
  if(!s)return '';
  return `<p class="ht-season" role="status"><span aria-hidden="true">${x.esc(s.emoji)}</span> <b>${x.esc(s.label)}</b> · ${x.esc(s.note)} Thưởng ×${x.esc(s.bonus)}.</p>`;
}

function progress(x){
  const d=data(x),s=d.stats||{},p=d.progress||{};
  return `<details class="ht-progress"><summary>Hành trình Sông Mây · ${s.good||0} việc đạt · ${s.active_days||0} ngày · ${p.posts||0}/6 vị trí</summary>
    <p class="small">Việc đạt từ 90% chất lượng mới được ghi; ngày có việc đạt mới tính ngày.</p>
    <ul>${(p.milestones||[]).map(m=>`<li><b>${m.achieved?'✓ ':''}${x.esc(m.label)}</b><span>${Math.min(s.good||0,m.jobs)}/${m.jobs} việc · ${Math.min(s.active_days||0,m.days)}/${m.days} ngày · ${Math.min(p.posts||0,m.posts)}/${m.posts} vị trí</span></li>`).join('')}</ul></details>`;
}

function notebook(x){
  return `<ul class="ht-rules">${(cc(x).notebook||[]).map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`;
}

/** The shift's briefing from the duty manager (a big hotel's numbers). */
const briefLine=x=>data(x).briefing?`<p class="ht-brief" role="note">${x.esc(data(x).briefing)}</p>`:'';

/* Generator 2 (#466): the housekeeping supervisor's board, floor 4 at the top like the one behind the desk. */
const SHORT_BED={double:'Đôi',twin:'2 đơn',family:'Gia đình'},SHORT_VIEW={river:'Sông',street:'Phố',garden:'Vườn'},SHORT_SPOT={lift:'Gần thang',quiet:'Yên tĩnh'};
function statusBoard(t,x,title){
  const c=cc(x),n=t.needs||{},w=t.work||{};
  // The supervisor's own decisions show on the board as soon as they are made: a locked room, a signed-off room.
  const now={};
  if(n.fault&&w['housekeeping.ooo']==='ooo')now[n.fault.room]='ooo';
  if(n.check&&w['housekeeping.inspect']==='pass')now[n.check.room]='vci';
  const board=(n.board||[]).map(r=>now[r.no]?{...r,status:now[r.no]}:r);
  const floors=[...new Set(board.map(r=>r.floor))].sort((a,b)=>b-a);
  const legend=Object.entries(c.status2||{}).map(([k,v])=>`<span class="ht-key st-${x.esc(k)}">${x.esc(v)}</span>`).join('');
  return `<section class="ht-board ht-board2" aria-label="${x.esc(title)}"><h4>${x.esc(title)}</h4>${floors.map(f=>`<div class="ht-floor"><small>Tầng ${f}</small><ul>${board.filter(r=>r.floor===f).map(r=>`<li class="ht-room st-${x.esc(r.status)}">
    <b>${x.esc(r.no)}</b><span>${x.esc(SHORT_BED[r.bed]||r.bed)} · ${x.esc(SHORT_VIEW[r.view]||r.view)}${r.spot?` · ${x.esc(SHORT_SPOT[r.spot]||r.spot)}`:''}${r.access?' · ♿':''}</span>
    <em>${x.esc(c.status2?.[r.status]||r.status)}</em></li>`).join('')}</ul></div>`).join('')}<p class="ht-legend">${legend}</p></section>`;
}

/** Rush hour at the desk: everyone waiting at once, what they need and by when, and who is on the team today. */
function queueCard(t,x){
  const q=t.needs?.queue||[];
  if(!q.length)return '';
  return `<section class="ht-queue" aria-label="Hàng chờ ở quầy"><h4>🕒 ${x.esc(t.needs.now)} · ${q.length} khách đang chờ ở quầy</h4><ul>${q.map(g=>`<li class="ht-guest k-${x.esc(g.kind)}">
    <span class="ht-guest-ico" aria-hidden="true">${x.esc(g.emoji)}</span><span class="grow"><b>${x.esc(g.who)}</b><small>${x.esc(g.need)}</small></span><em>xong trước ${x.esc(g.by)}</em></li>`).join('')}</ul>
    <p class="ht-team">👥 Ca này: Chị Hằng trưởng ca · Anh Khôi quản lý trực · Tú quầy đoàn</p></section>`;
}

/** The room post as supervisor: today's arrivals (rooms already assigned) and the housekeeping team by floor. */
function arrivalsCard(t,x){
  const n=t.needs||{},a=n.arrivals||[];
  if(!a.length)return '';
  return `<section class="ht-list ht-arrivals" aria-label="Khách đến hôm nay"><h4>🧳 Khách đến hôm nay</h4><ul>${a.map(g=>`<li><b>${x.esc(g.eta)} · ${x.esc(g.name)}${g.vip?' ⭐ VIP':''}</b><span>Phòng đã gán: ${x.esc(g.room)}</span></li>`).join('')}</ul>
    <p class="ht-team">🧺 Tổ buồng: ${(n.team||[]).map(m=>`${x.esc(m.who)} (${x.esc(m.floors)})`).join(' · ')}</p></section>`;
}

/** The room board of a check-in: every room's bed, view, spot, access and status (the room step reads it). */
function roomBoard(t,x){
  const c=cc(x),board=t.needs?.board||[];
  if(!board.length)return '';
  if(t.gen>=2)return statusBoard(t,x,'Bảng phòng');
  return `<section class="ht-board" aria-label="Bảng phòng"><h4>Bảng phòng</h4><ul>${board.map(r=>`<li class="ht-room st-${x.esc(r.status)}">
    <b>${x.esc(r.no)}</b><span>${x.esc(c.beds?.[r.bed]||r.bed)}</span><span>${x.esc(c.views?.[r.view]||r.view)}${r.spot?` · ${x.esc(c.spots?.[r.spot]||r.spot)}`:''}${r.access?' · ♿ Tiếp cận':''}</span>
    <em>${x.esc(c.status?.[r.status]||r.status)}</em></li>`).join('')}</ul></section>`;
}

/** Tomorrow's breakfast list: each room's notes and each guest's pre-order. */
function breakfastList(t,x){
  const rooms=t.needs?.rooms||[];
  if(!rooms.length||t.kind!=='breakfast')return '';
  return `<section class="ht-list" aria-label="Danh sách bữa sáng"><h4>Danh sách bữa sáng</h4><ul>${rooms.map(r=>`<li><b>Phòng ${x.esc(r.no)}</b>
    ${r.notes?.length?`<span class="ht-notes">${r.notes.map(n=>x.esc(n)).join(' · ')}</span>`:''}
    <span>${(r.guests||[]).map(g=>`${x.esc(g.who)}: ${x.esc(g.label)}`).join('; ')}</span></li>`).join('')}</ul></section>`;
}

function briefCard(t,x){
  const post=t.post||{};
  const n=t.needs||{};
  const decor=t.kind==='decor'&&n.title?`<p class="ht-ask"><span aria-hidden="true">${x.esc(n.emoji)}</span> ${x.esc(n.ask)}</p>`:'';
  return `<article class="ht-post"><small>${x.esc(post.emoji||'🛎️')} ${x.esc(post.label||'Ca trực')} · ${x.esc(post.work||'')}</small><h3>${x.esc(t.title)}</h3>${decor}</article>`;
}

function choiceStep(t,st,x){
  return `<div class="ht-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),'ht_step',{task:t.id,step:st.id,value:o.id},'ht-option')).join('')}</div>`;
}

function pickStep(t,st,x,ordered){
  const key=keyOf(t,st),seq=((x.ui.htPick??={})[key]||[]).filter(id=>(st.options||[]).some(o=>o.id===id));
  const opts=(st.options||[]).map(o=>{
    const i=seq.indexOf(o.id),on=i>=0;
    const mark=on?(ordered?`<i class="ht-num">${i+1}</i>`:'<i class="ht-num">✓</i>'):'';
    return act(x,`${mark}<span>${x.esc(o.label)}</span>`,'htPick',{key,id:o.id,ordered:ordered?1:0},`ht-pick${on?' on':''}`,` aria-pressed="${on}"`);
  }).join('');
  const ready=ordered?seq.length===(st.options||[]).length:true;
  const value=ordered?seq:[...seq].sort();
  const send=x.cmd(ordered?'Xác nhận thứ tự':'Xác nhận lựa chọn','ht_step',{task:t.id,step:st.id,value},'primary ht-send',!ready);
  return `${tip(ordered?'Bấm lần lượt theo thứ tự; bấm lại để bỏ.':'Bấm để chọn hoặc bỏ chọn từng món.','','p','small')}<div class="ht-picks">${opts}</div>
    <div class="ht-row">${act(x,'Làm lại','htClear',{key},'ghost')}${send}</div>`;
}

function countsStep(t,st,x){
  const key=keyOf(t,st),vals=(x.ui.htCnt??={})[key]||{};
  const rows=(st.fields||[]).map(f=>{
    const id=`ht-${t.id}-${st.id}-${f.id}`.replace(/[^\w-]/g,'-');
    return `<label class="ht-count" for="${x.esc(id)}"><span>${x.esc(f.label)}</span><input id="${x.esc(id)}" type="number" inputmode="numeric" min="0" max="200" step="1"
      value="${x.esc(vals[f.id]??'')}" data-ht-cnt="${x.esc(key)}" data-field="${x.esc(f.id)}" aria-label="${x.esc(f.label)}"></label>`;
  }).join('');
  return `<div class="ht-counts">${rows}</div>${act(x,'Ghi số vào phiếu','htCounts',{key,task:t.id,step:st.id,fields:(st.fields||[]).map(f=>f.id).join(',')},'primary ht-send')}`;
}

function numberStep(t,st,x){
  return amountBox(x,`ht-${t.id}-${st.id}`,0,{min:0,max:10000,label:st.unit==='hộp'?'Số hộp mang đi':st.unit==='phòng'?'Số phòng':'Số tiền (xu)',send:'Ghi vào phiếu',
    cmd:'ht_step',payload:{task:t.id,step:st.id},field:'value',unit:st.unit||'xu'});
}

function stepCard(t,x){
  const st=current(t),steps=stepsOf(t);
  if(!st)return `<p class="ht-finished" role="status">✓ Xong việc · chất lượng ${x.esc(t.quality)}% · thưởng ${x.fmt(t.paid||0)} xu.${t.fast===true?' ⏱️ Nhanh, đúng quy trình.':''}</p>`;
  const body=st.type==='choice'?choiceStep(t,st,x):st.type==='order'?pickStep(t,st,x,true):st.type==='multi'?pickStep(t,st,x,false):
    st.type==='counts'?countsStep(t,st,x):numberStep(t,st,x);
  return `<section class="card ht-step" aria-labelledby="ht-step-title">
    <p class="ht-step-count" role="status">Bước ${t.at+1}/${steps.length} · chất lượng ${x.esc(t.quality??100)}%${t.target?` · ⏱️ chuẩn ${x.esc(t.target)} giây`:''}</p>
    <progress value="${t.at}" max="${steps.length}" aria-label="Tiến trình phiếu việc"></progress>
    <h3 id="ht-step-title">${x.esc(st.title)}</h3><p class="ht-evidence">${x.esc(st.evidence)}</p>
    ${st.id==='decor.items'&&t.needs?.rule?`<p class="ht-rule" role="note"><span aria-hidden="true">📌</span> ${x.esc(t.needs.rule)}</p>`:''}
    ${st.id==='checkin.room'||st.id==='rush.room'?roomBoard(t,x):''}${body}</section>`;
}

const top=x=>`${introCard(x,'ht_intro','🛎️')}${deskCard(x,'ht_desk','Chuyện ở quầy')}`;

export default {
  id:'hotel',css:true,
  next(t,x){return x.esc(!t.known?'Đọc phiếu việc':current(t)?.title||'Đã xong việc');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'ht_intro','🛎️'));
    if(!t.known)return wrap(top(x)+seasonBanner(x,data(x).season)+briefLine(x)+askCard(x,t,'Đọc phiếu việc')+progress(x));
    const roomsPost=t.kind==='housekeeping'&&t.gen>=2;
    return wrap(top(x)+seasonBanner(x,t.season_info)+person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+briefCard(t,x)+
      breakfastList(t,x)+queueCard(t,x)+(roomsPost?arrivalsCard(t,x):'')+stepCard(t,x)+(roomsPost?statusBoard(t,x,'Bảng tình trạng phòng'):'')+
      (t.lines?.length?`<p class="ht-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+
      `<details class="ht-notebook"><summary>Sổ quy trình Sông Mây</summary>${notebook(x)}</details>`+progress(x));
  },
  // Compact layout: the notebook folds like on the work screen (the full layout keeps it open, as before).
  idle(x){return wrap(top(x)+seasonBanner(x,data(x).season)+briefLine(x)+progress(x)+(clean()?`<details class="ht-notebook"><summary>Sổ quy trình Sông Mây</summary>${notebook(x)}</details>`:notebook(x)));},
  input(el,x){
    const key=el.dataset?.htCnt;
    if(key){((x.ui.htCnt??={})[key]??={})[el.dataset.field]=el.value===''?'':Math.floor(Number(el.value)||0);return true;}
    return kitInput(el,x);
  },
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'hotel',eyebrow:'Khách sạn Sông Mây',title:'Sổ quy trình',body:notebook(x)}):'';},
  actions:{...kitActions,
    async htPick(d,el,x){
      const all=x.ui.htPick??={},seq=all[d.key]||[],i=seq.indexOf(d.id);
      all[d.key]=i>=0?seq.filter(id=>id!==d.id):[...seq,d.id];x.render();
    },
    async htClear(d,el,x){(x.ui.htPick??={})[d.key]=[];x.render();},
    async htCounts(d,el,x){
      const vals=(x.ui.htCnt??={})[d.key]||{},value={};
      for(const f of String(d.fields||'').split(',').filter(Boolean)){
        const v=Number(vals[f]===undefined||vals[f]===''?NaN:vals[f]);
        if(!Number.isInteger(v)||v<0||v>200){x.toast?.('Ghi đủ số (0–200) cho từng loại nhé.');return;}
        value[f]=v;
      }
      await x.send('ht_step',{task:d.task,step:d.step,value});
    },
    async amtSend(d,el,x){
      // Zero is a real answer here (an untouched minibar, no box to pack).
      const raw=x.ui.amt?.[d.key],value=Number(raw===undefined||raw===''?d.def:raw);
      if(!Number.isInteger(value)||value<0||value>10000){x.toast?.('Nhập số nguyên từ 0 đến 10000.');return;}
      await x.send(d.cmd,{...JSON.parse(d.extra||'{}'),[d.field]:value});
    },
  },
  dock:[['car:notes','book','Sổ quy trình','Nội quy, giá và mùa lễ của Sông Mây'],['car:intro','question','Giới thiệu nghề','Một ca làm thuê theo quy trình']],
};
