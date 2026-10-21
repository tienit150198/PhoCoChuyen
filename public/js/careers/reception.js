/** Lễ tân Khách sạn Hoa Sứ: one job slip at a time, one step at a time. The check-in plays on the hotel itself: the
 * room board (two floors of three rooms, the desk under them) takes guest cards (drag them, or tap a card then a room),
 * the hook board gives keys, the luggage cart takes each piece on a shelf. The server grades every step; a wrong one
 * stays open to fix and lowers the job's quality. The Sổ nghề page keeps the trial, the people at the desk, the
 * keepsakes and the branch. */
import {data,cc,person,askCard,introCard,deskCard,kitActions,amountBox,kitInput,notesPage,act} from './street_kit.js';
import {clean,tip,withArt} from '../ui-kit.js';
import {stepsArt} from './slip_kit.js';

const wrap=body=>`<div class="career-job sk reception">${body}</div>`;
const stepsOf=t=>t.needs?.steps||[];
const current=t=>stepsOf(t)[t.at];
const keyOf=(t,st)=>`${t.id}:${st.id}`;
const hhmm=m=>`${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;
const TAG_ICON={twin:'🛏️🛏️',double:'🛏️',quiet:'🤫',street:'🏙️',bag:'🧳',cheap:'💸',ground:'⬇️',near:'↔️'};
// The step's own confirm button: its words and its class (the coach rings these).
const SEND={'arrival.need':['Chốt yêu cầu','need'],'arrival.rooms':['Xác nhận xếp phòng','rooms'],'arrival.keys':['Giao chìa','keys'],
  'arrival.cart':['Xếp xong xe','cart'],'arrival.note':['Ghi sổ giao ca','note'],'services.plan':['Chốt lịch','plan']};
const sendBtn=(x,st,payload,disabled,fallback)=>{
  const [label,cls]=SEND[st.id]||[fallback,'step'];
  return x.cmd(label,'rc_step',payload,`primary rc-send rc-send-${cls}`,disabled);
};

function trialBanner(x,info){
  if(!info)return '';
  return `<p class="rc-trial" role="status"><span aria-hidden="true">🧪</span> <b>Ca thử việc · ${x.esc(info.title)}</b>${clean()?'':` · ${x.esc(info.note)}`}</p>`;
}

function trialCard(x){
  const v=data(x).trial_view;if(!v||v.done)return '';
  const parts=(v.parts||[]).map(p=>`<li class="${p.passed?'ok':''}"><span aria-hidden="true">${p.passed?'✅':'⬜'}</span>${x.esc(p.title)}</li>`).join('');
  const prac=(v.practise||[]).length?`<p class="rc-practise"><b>Luyện thêm:</b> ${v.practise.map(p=>x.esc(p)).join(' ')}</p>`:'';
  return `<section class="rc-trialcard" aria-label="Ca thử việc"><h4>🧪 Ca thử việc với chị Quyên</h4><ul>${parts}</ul>${prac}</section>`;
}

function progress(x){
  const d=data(x),s=d.stats||{},p=d.progress||{};
  return `<details class="rc-progress"><summary>Hành trình Hoa Sứ · ${s.good||0} việc đạt · ${s.active_days||0} ngày · ${p.kinds||0}/6 việc</summary>
    <ul>${(p.milestones||[]).map(m=>`<li><b>${m.achieved?'✓ ':''}${x.esc(m.label)}</b><span>${Math.min(s.good||0,m.jobs)}/${m.jobs} việc · ${Math.min(s.active_days||0,m.days)}/${m.days} ngày · ${Math.min(p.kinds||0,m.kinds)}/${m.kinds} loại việc</span></li>`).join('')}</ul></details>`;
}

function notebook(x){
  return `<ul class="rc-rules">${(cc(x).notebook||[]).map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`;
}

const mood=v=>v>=70?'quý bạn':v>=45?'bình thường':v>=30?'hơi giận':'giận bạn';
function castList(x){
  const cast=data(x).cast||[];if(!cast.length)return '';
  return `<ul class="rc-cast">${cast.map(p=>`<li><span class="rc-cast-name"><b>${x.esc(p.name)}</b><small>${x.esc(p.role)}</small></span>
    <span class="rc-meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Number(p.rel)||0}" aria-label="${x.esc(p.name)}: ${mood(p.rel)}"><i style="width:${Math.max(0,Math.min(100,Number(p.rel)||0))}%"></i></span>
    <em>${x.esc(mood(p.rel))}</em></li>`).join('')}</ul>`;
}

function keepsakes(x){
  const k=data(x).keepsakes||[];
  if(!k.length)return '<p class="small">Chưa có kỷ niệm nào. Xử lý khéo vài chuyện ở quầy là có.</p>';
  return `<ul class="rc-keeps">${k.map(o=>`<li><span aria-hidden="true">${x.esc(o.emoji)}</span><div><b>${x.esc(o.name)}</b><small>${x.esc(o.desc)}</small></div></li>`).join('')}</ul>`;
}

function branches(x){
  const d=data(x),bv=d.branch_view||{},rank=Number(x.room?.promo?.rank)||0,from=cc(x).branch_from||2;
  const rows=(cc(x).branches||[]).map(b=>{
    const on=bv.id===b.id,locked=rank<from||(bv.id&&bv.id!=='none'&&(x.room?.day||0)<(bv.can_change_day||0));
    return x.cmd(`<span aria-hidden="true">${x.esc(b.emoji)}</span><b>${x.esc(b.label)}</b><small>${x.esc(b.title)} · ${x.esc(b.note)}</small>`,
      'rc_branch',{branch:b.id},`rc-branch${on?' on':''}`,locked||on);
  }).join('');
  const why=rank<from?`<p class="small">Lên bậc ${from} ở 🎖️ Thăng tiến rồi mới chọn hướng đi.</p>`:bv.id&&bv.id!=='none'?`<p class="small">Đổi hướng được từ ngày ${x.esc(bv.can_change_day)}.</p>`:'';
  const self=bv.id==='self'?'<p class="small">🏡 Muốn mở homestay riêng: vào Hành trình → Nơi làm việc → Homestay.</p>':'';
  return `${why}<div class="rc-branches">${rows}</div>${self}`;
}

function bookPage(x){
  return `${trialCard(x)}<h4>👥 Người ở quầy</h4>${castList(x)}<h4>📒 Kỷ niệm</h4>${keepsakes(x)}<h4>🧭 Hướng đi</h4>${branches(x)}
    <h4>📖 Sổ quy trình Hoa Sứ</h4>${notebook(x)}`;
}

/** The job's folder filling up (owner 21/10, like the milk-tea cup): one item per step, solid once done. */
const FOLDER={need:'👂',hear:'👂',early:'⏰',rooms:'🛏️',keys:'🔑',key:'🔑',cart:'🧳',note:'📒',log:'📒',plan:'🗓️',clash:'⚠️',fee:'💰',
  bill:'🧾',hold:'💳',verify:'🪪',owner:'🪪',comp:'🎁',result:'✅',where:'📍',match:'🔍',check:'🔍',help:'🙋'};
function briefCard(t,x){
  const post=t.post||{};
  return `<article class="rc-post">${withArt(`<small>${x.esc(post.emoji||'🛎️')} ${x.esc(post.label||'Quầy')} · ${x.esc(post.work||'')}</small><h3>${x.esc(t.title)}</h3>`,
    stepsArt(t,{kind:'paper',icons:FOLDER,head:'🔑',label:'Hồ sơ khách'}))}</article>`;
}

/* ------------------------------------------------------------ picks: multi / order */
function chipsStep(t,st,x,ordered){
  const key=keyOf(t,st),seq=((x.ui.rcPick??={})[key]||[]).filter(id=>(st.options||[]).some(o=>o.id===id));
  const keys=st.id==='arrival.keys';
  const opts=(st.options||[]).map(o=>{
    const i=seq.indexOf(o.id),on=i>=0;
    const mark=on?`<i class="rc-num">${ordered?i+1:'✓'}</i>`:'';
    const hook=keys?` hook-${/móc đỏ/.test(o.label)?'red':/móc xám/.test(o.label)?'grey':/móc vàng/.test(o.label)?'gold':/nhà xe/.test(o.label)?'dark':'green'}`:'';
    const tag=TAG_ICON[o.id]?`<span class="rc-tagicon" aria-hidden="true">${TAG_ICON[o.id]}</span>`:'';
    return act(x,`${mark}${tag}<span>${x.esc(o.label)}</span>`,'rcPick',{key,id:o.id},`rc-chip${on?' on':''}${hook}`,` aria-pressed="${on}"`);
  }).join('');
  const ready=ordered?seq.length===(st.options||[]).length:seq.length>0;
  const value=ordered?seq:[...seq].sort();
  const send=sendBtn(x,st,{task:t.id,step:st.id,value},!ready,ordered?'Xác nhận thứ tự':'Xác nhận lựa chọn');
  return `${tip(ordered?'Bấm lần lượt theo thứ tự; bấm lại để bỏ.':'Bấm để chọn hoặc bỏ chọn.','','p','small')}<div class="rc-chips${keys?' rc-hooks':''}">${opts}</div>
    <div class="rc-row">${act(x,'Làm lại','rcPickClear',{key},'ghost')}${send}</div>`;
}

function choiceStep(t,st,x){
  return `<div class="rc-options">${(st.options||[]).map(o=>x.cmd(x.esc(o.label),'rc_step',{task:t.id,step:st.id,value:o.id},'rc-option')).join('')}</div>`;
}

function numberStep(t,st,x){
  return amountBox(x,`rc-${t.id}-${st.id}`,0,{min:0,max:10000,label:'Số tiền (xu)',send:'Ghi vào phiếu',cmd:'rc_step',payload:{task:t.id,step:st.id},field:'value',unit:st.unit||'xu'});
}

/* ------------------------------------------------------------ assign: guest cards → rooms, luggage → cart shelves */
const asgOf=(x,key)=>((x.ui.rcAsg??={})[key]??={});
function guestCard(t,st,x,card,key,sel,asg,placed){
  const items=(card.items||[]).length,tags=(card.tags||[]).map(g=>`<span title="${x.esc(cc(x).tags?.[g]||g)}">${TAG_ICON[g]||'•'}</span>`).join('');
  const on=sel===card.id;
  return act(x,`<b>${x.esc(card.name)}</b><small>👤×${x.esc(card.people)}${items?` · 🧳×${items}`:''}${placed?` · → ${x.esc(placed)}`:''}</small>${tags?`<span class="rc-cardtags">${tags}</span>`:''}`,
    'rcSel',{key,id:card.id},`rc-guest${on?' on':''}${placed?' placed':''}`,` aria-pressed="${on}" data-rc-drag="${x.esc(key)}" data-id="${x.esc(card.id)}"`);
}
function roomTile(x,room,status,key,asg,cards){
  const here=Object.entries(asg).filter(([,no])=>no===room.no).map(([cid])=>cards.find(c=>c.id===cid)).filter(Boolean);
  const icons=[room.quiet?'🤫':'',room.street?'🏙️':'',room.bag?'🧳':'',room.price<=35?'💸':''].filter(Boolean).join(' ');
  const st=cc(x).status?.[status]||status;
  return act(x,`<span class="rc-room-no">${x.esc(room.no)}</span><small>${x.esc(room.beds_label)} · 👤${x.esc(room.cap)}</small>
    <small class="rc-room-icons">${icons||'&nbsp;'} · ${x.esc(room.price)} xu</small><em>${x.esc(st)}</em>${here.map(c=>`<span class="rc-here">${x.esc(c.name.split(' ').slice(-2).join(' '))}</span>`).join('')}`,
    'rcPut',{key,target:room.no},`rc-room st-${x.esc(status)}${here.length?' filled':''}`,` data-rc-drop="${x.esc(key)}" data-target="${x.esc(room.no)}" aria-label="Phòng ${x.esc(room.no)}, ${x.esc(st)}"`);
}
function roomsStep(t,st,x){
  const key=keyOf(t,st),n=t.needs||{},asg=asgOf(x,key),sel=(x.ui.rcSel??={})[key];
  const rooms=n.rooms||cc(x).rooms||[],status=Object.fromEntries((n.board||[]).map(b=>[b.no,b.status]));
  const cards=n.cards||[];
  const floor=f=>`<div class="rc-floor"><span class="rc-floor-name">${f==='2'?'Tầng 2':'Tầng trệt'}</span><div class="rc-floor-rooms">${rooms.filter(r=>r.no[0]===f).map(r=>roomTile(x,r,status[r.no],key,asg,cards)).join('')}</div></div>`;
  const legend=tip('🤫 yên · 🏙️ nhìn phố · 🧳 hốc vali · 💸 rẻ · sát vách: cạnh nhau cùng tầng','Bảng phòng','p','small rc-legend');
  const desk=`<div class="rc-desk" aria-label="Quầy lễ tân"><span class="rc-desk-name">🛎️ Quầy</span><div class="rc-guests">${cards.map(c=>guestCard(t,st,x,c,key,sel,asg,asg[c.id])).join('')}</div></div>`;
  const ready=cards.every(c=>asg[c.id]);
  const value=Object.fromEntries(cards.map(c=>[c.id,asg[c.id]]).filter(([,v])=>v));
  return `<section class="rc-board" aria-label="Bảng phòng">${floor('2')}${floor('1')}${desk}</section>${legend}
    <p class="small rc-hint">${sel?'Giờ chạm vào phòng cho khách này.':'Kéo thẻ khách vào phòng, hoặc chạm thẻ rồi chạm phòng.'}</p>
    <div class="rc-row">${act(x,'Làm lại','rcClear',{key},'ghost')}${sendBtn(x,st,{task:t.id,step:st.id,value},!ready)}</div>`;
}
function cartStep(t,st,x){
  const key=keyOf(t,st),asg=asgOf(x,key),sel=(x.ui.rcSel??={})[key];
  const items=st.cards||[],shelves=cc(x).shelves||[];
  const shelf=s=>{
    const here=items.filter(i=>asg[i.id]===s.id);
    return act(x,`<span class="rc-shelf-name">${x.esc(s.label)} · ${here.length}/${x.esc(s.cap)}</span><span class="rc-shelf-items">${here.map(i=>`<span class="rc-bag">${x.esc(i.label)}</span>`).join('')||'&nbsp;'}</span>`,
      'rcPut',{key,target:s.id},`rc-shelf sh-${x.esc(s.id)}${here.length>Number(s.cap)?' over':''}`,` data-rc-drop="${x.esc(key)}" data-target="${x.esc(s.id)}"`);
  };
  const loose=items.map(i=>{
    const on=sel===i.id,placed=asg[i.id];
    return act(x,`<span>${x.esc(i.label)}</span>${placed?'<small>✓</small>':''}`,'rcSel',{key,id:i.id},`rc-item${on?' on':''}${placed?' placed':''}`,` aria-pressed="${on}" data-rc-drag="${x.esc(key)}" data-id="${x.esc(i.id)}"`);
  }).join('');
  const ready=items.every(i=>asg[i.id]);
  const value=Object.fromEntries(items.map(i=>[i.id,asg[i.id]]).filter(([,v])=>v));
  return `<div class="rc-items" aria-label="Hành lý của khách">${loose}</div><section class="rc-cart" aria-label="Xe đẩy hành lý">${shelves.map(shelf).join('')}<span class="rc-wheels" aria-hidden="true">● ●</span></section>
    <div class="rc-row">${act(x,'Làm lại','rcClear',{key},'ghost')}${sendBtn(x,st,{task:t.id,step:st.id,value},!ready)}</div>`;
}

/* ------------------------------------------------------------ times: tomorrow's timeline */
function timesStep(t,st,x){
  const key=keyOf(t,st),vals=((x.ui.rcTime??={})[key]??={});
  const slots=[];for(let m=st.low;m<=st.high;m+=st.every)slots.push(m);
  const rows=(st.fields||[]).map(f=>{
    const id=`rc-${t.id}-${f.id}`.replace(/[^\w-]/g,'-'),v=vals[f.id];
    return `<li class="rc-time"><label for="${x.esc(id)}">${x.esc(f.label)}</label><select id="${x.esc(id)}" data-car="rcTimeSel" data-key="${x.esc(key)}" data-id="${x.esc(f.id)}">
      <option value=""${v===undefined?' selected':''}>--:--</option>${slots.map(m=>`<option value="${m}"${v===m?' selected':''}>${hhmm(m)}</option>`).join('')}</select></li>`;
  }).join('');
  const ready=(st.fields||[]).every(f=>vals[f.id]!==undefined);
  const value=Object.fromEntries((st.fields||[]).map(f=>[f.id,vals[f.id]]).filter(([,v])=>v!==undefined));
  return `<ul class="rc-times">${rows}</ul><div class="rc-row">${sendBtn(x,st,{task:t.id,step:st.id,value},!ready)}</div>`;
}

/* ------------------------------------------------------------ the job */
function said(t,x){
  const cards=t.needs?.cards||[];if(!cards.length)return '';
  return `<ul class="rc-said">${cards.map(c=>`<li><b>${x.esc(c.name)}</b> <small>${x.esc(c.people)} người</small>${(c.said||[]).map(s=>`<q>${x.esc(s)}</q>`).join(' ')}</li>`).join('')}</ul>`;
}

function stepCard(t,x){
  const st=current(t),steps=stepsOf(t);
  if(!st)return `<p class="rc-finished" role="status">✓ Xong việc · chất lượng ${x.esc(t.quality)}% · thưởng ${x.fmt(t.paid||0)} xu.</p>`;
  const body=st.type==='choice'?choiceStep(t,st,x):st.type==='order'?chipsStep(t,st,x,true):st.type==='multi'?chipsStep(t,st,x,false):
    st.type==='assign'?(st.id==='arrival.rooms'?roomsStep(t,st,x):cartStep(t,st,x)):st.type==='times'?timesStep(t,st,x):numberStep(t,st,x);
  // The check-in's words stay on screen while the guest is read (the need step) and folded after (gọn: always folded).
  const words=st.id==='arrival.need'?said(t,x):'';
  const ev=st.id==='arrival.need'?'Chọn mọi yêu cầu khách vừa nói (không chọn điều khách không nói).':st.evidence;
  return `<section class="card rc-step" aria-labelledby="rc-step-title">
    <p class="rc-step-count" role="status">Bước ${t.at+1}/${steps.length} · chất lượng ${x.esc(t.quality??100)}%</p>
    <progress value="${t.at}" max="${steps.length}" aria-label="Tiến trình phiếu việc"></progress>
    <h3 id="rc-step-title">${x.esc(st.title)}</h3>${words}<p class="rc-evidence">${x.esc(ev)}</p>${body}</section>`;
}

function guestsHeard(t,x){
  // After the need step: who wants what, as small tags (the rooms step reads it).
  const cards=t.needs?.cards||[];if(!cards.length||t.at<1)return '';
  const tags=cc(x).tags||{};
  return `<details class="rc-heard"${clean()?'':' open'}><summary>Khách đã nói</summary><ul>${cards.map(c=>`<li><b>${x.esc(c.name)}</b> · ${x.esc(c.people)} người${(c.tags||[]).length?': '+c.tags.map(g=>`${TAG_ICON[g]||''} ${x.esc(tags[g]||g)}`).join(', '):''}</li>`).join('')}</ul></details>`;
}

const top=x=>`${introCard(x,'rc_intro','🔑')}${deskCard(x,'rc_desk','Chuyện ở quầy')}`;

export default {
  id:'reception',css:true,
  next(t,x){return x.esc(!t.known?'Đọc phiếu việc':current(t)?.title||'Đã xong việc');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'rc_intro','🔑'));
    if(!t.known)return wrap(top(x)+trialBanner(x,t.trial_info)+askCard(x,t,'Đọc phiếu việc')+trialCard(x)+progress(x));
    const opening=clean()?'':`<p class="small">${x.esc(t.opening)}</p>`;
    return wrap(top(x)+trialBanner(x,t.trial_info)+person(x,t,opening)+briefCard(t,x)+guestsHeard(t,x)+stepCard(t,x)+
      (t.lines?.length?`<p class="rc-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+
      `<details class="rc-notebook"><summary>Sổ quy trình Hoa Sứ</summary>${notebook(x)}</details>`+progress(x)+
      `<details class="rc-book"${x.ui.book?' open':''}><summary>Sổ nghề Hoa Sứ</summary>${bookPage(x)}</details>`);
  },
  idle(x){return wrap(top(x)+trialCard(x)+progress(x)+`<details class="rc-book"${x.ui.book||!clean()?' open':''}><summary>Sổ nghề Hoa Sứ</summary>${bookPage(x)}</details>`);},
  input(el,x){return kitInput(el,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'reception',eyebrow:'Khách sạn Hoa Sứ',title:'Sổ nghề',body:bookPage(x)}):'';},
  /** Drag a guest card onto a room / a piece of luggage onto a shelf (taps do the same: see rcSel / rcPut). */
  tick(root,x){
    for(const el of root.querySelectorAll('[data-rc-drag]')){
      if(el._rcDrag)continue;el._rcDrag=true;
      el.addEventListener('pointerdown',e=>{
        if(e.button>0)return;
        const start={x:e.clientX,y:e.clientY};let ghost=null;
        const move=ev=>{
          if(!ghost&&Math.hypot(ev.clientX-start.x,ev.clientY-start.y)<8)return;
          if(!ghost){ghost=el.cloneNode(true);ghost.classList.add('rc-ghost');ghost.removeAttribute('data-action');document.body.append(ghost);el.classList.add('dragging');}
          ghost.style.transform=`translate(${ev.clientX-30}px,${ev.clientY-20}px)`;
          // near the top or bottom edge of the sheet: scroll it, so a room off screen can still be reached
          const box=el.closest('.sheet-body')||document.scrollingElement,r=box.getBoundingClientRect?.()||{top:0,bottom:innerHeight};
          const top=Math.max(0,r.top),bottom=Math.min(innerHeight,r.bottom);
          if(ev.clientY<top+48)box.scrollBy(0,-14);else if(ev.clientY>bottom-48)box.scrollBy(0,14);
          ev.preventDefault();
        };
        const up=ev=>{
          window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',up);window.removeEventListener('pointercancel',up);
          if(!ghost)return;
          ghost.remove();el.classList.remove('dragging');
          const drop=document.elementFromPoint(ev.clientX,ev.clientY)?.closest?.('[data-rc-drop]');
          el._rcSkip=Date.now();   // the click this drag ends with is not a tap
          if(drop&&drop.dataset.rcDrop===el.dataset.rcDrag){
            const asg=asgOf(x,el.dataset.rcDrag);asg[el.dataset.id]=drop.dataset.target;(x.ui.rcSel??={})[el.dataset.rcDrag]=null;x.render();
          }
        };
        window.addEventListener('pointermove',move,{passive:false});window.addEventListener('pointerup',up);window.addEventListener('pointercancel',up);
      });
    }
  },
  actions:{...kitActions,
    // The dock's Sổ nghề from inside the work sheet: open its fold and bring it into view.
    async notes(d,el,x){x.ui.book=true;x.render();setTimeout(()=>document.querySelector('#sheet[open] .rc-book')?.scrollIntoView({block:'start'}),0);},
    async rcPick(d,el,x){const all=x.ui.rcPick??={},seq=all[d.key]||[],i=seq.indexOf(d.id);all[d.key]=i>=0?seq.filter(v=>v!==d.id):[...seq,d.id];x.render();},
    async rcPickClear(d,el,x){(x.ui.rcPick??={})[d.key]=[];x.render();},
    async rcSel(d,el,x){
      if(el?._rcSkip&&Date.now()-el._rcSkip<400)return;
      const sel=x.ui.rcSel??={};sel[d.key]=sel[d.key]===d.id?null:d.id;x.render();
    },
    async rcPut(d,el,x){
      const sel=x.ui.rcSel??={},asg=asgOf(x,d.key),id=sel[d.key];
      if(id){asg[id]=d.target;sel[d.key]=null;x.render();return;}
      // nothing in hand: tapping a filled room picks its guest back up
      const back=Object.keys(asg).find(k=>asg[k]===d.target);
      if(back){delete asg[back];sel[d.key]=back;x.render();return;}
      x.toast?.('Chạm một thẻ trước, rồi chạm chỗ đặt.');
    },
    async rcClear(d,el,x){(x.ui.rcAsg??={})[d.key]={};(x.ui.rcSel??={})[d.key]=null;x.render();},
    async rcTimeSel(d,el,x){
      const all=((x.ui.rcTime??={})[d.key]??={});
      if(d.value==='')delete all[d.id];else all[d.id]=Number(d.value);x.render();
    },
    async amtSend(d,el,x){
      // Zero is a real answer here (no compensation, a fully paid deposit).
      const raw=x.ui.amt?.[d.key],value=Number(raw===undefined||raw===''?d.def:raw);
      if(!Number.isInteger(value)||value<0||value>10000){x.toast?.('Nhập số nguyên từ 0 đến 10000.');return;}
      await x.send(d.cmd,{...JSON.parse(d.extra||'{}'),[d.field]:value});
    },
  },
  dock:[['car:notes','book','Sổ nghề','Ca thử việc, người ở quầy, kỷ niệm, hướng đi và sổ quy trình'],['car:intro','question','Giới thiệu nghề','Một ca ở quầy lễ tân Hoa Sứ']],
};
