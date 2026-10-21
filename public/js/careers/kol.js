/** 📱 Studio Hẻm Xanh: read the brand's brief, name the format, settle the brand's awkward demands, then one step of the
 * deal at a time (the opening line, the run sheet, behind the camera, the number of scenes, royalty-free music, the edit,
 * when to post, a comment, the numbers, the report) and send the report to the right contract. The server grades each
 * step (game/careers/kol.py); a wrong one stays open to fix and lowers the deal's quality and fee. */
import {data,person,askCard,introCard,deskCard,kitActions,kitInput,notesPage} from './street_kit.js';
import {current,stepsOf,stepCard,rulesList,statsCard,slipActions,stepsArt} from './slip_kit.js';
import {clean,withArt} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk slip kol">${body}</div>`;
const STATS={noun:'hợp đồng',money:'earned',moneyLabel:'cát-xê',master:[90,30],title:'Hành trình ở Studio Hẻm Xanh'};

const notebook=x=>`<details class="sl-notebook"><summary>📒 Sổ tay Studio Hẻm Xanh</summary>${rulesList(x)}</details>`;
const top=x=>`${introCard(x,'ko_intro','📱')}${deskCard(x,'ko_desk','Chuyện ở studio')}`;
const tail=x=>statsCard(x,STATS);

/** The phone screen filling up: one piece per step of the deal (solid: done, ringed: now, grey: still to do). */
const PIECE={brief:'📝',brand:'🏷️',hook:'🗣️',thu_tu:'🔢',canh:'🎥',so_canh:'🎞️',so_mon:'🛍️',nhac:'🎵',dung:'✂️',gio:'⏰',
  binh_luan:'💬',ty_le:'📊',gui_gi:'📋',hop_dong:'📨'};
/** The brief on the desk: the brand and product, and the format once it is settled (not before: that is the first step). */
function briefCard(t,x){
  const n=t.needs||{},known=t.at>0;
  return `<article class="sl-ticket">${withArt(`<small>Hợp đồng ${x.esc(n.code)} · ${x.esc(n.brand)}</small>
    <h3><span aria-hidden="true">${known?x.esc(n.emoji):'📝'}</span> ${x.esc(known?n.deal_name:n.product)}</h3>
    ${known?`<p class="small">${x.esc(n.product)} · cát-xê tối đa ${x.fmt(n.net||0)} xu, giảm theo chất lượng.</p>`:'<p class="small">Chưa chốt dạng nội dung: đọc brief rồi chốt.</p>'}`,
    stepsArt(t,{kind:'phone',icons:PIECE,head:'📱',label:'Video đang làm'}))}</article>`;
}

function slip(t,x){
  const st=current(t);
  if(!st)return `<p class="sl-finished" role="status">✓ Đã gửi báo cáo · chất lượng ${x.esc(t.quality)}% · cát-xê ${x.fmt(t.paid||0)} xu.</p>`;
  return stepCard(x,st,{at:t.at,total:stepsOf(t).length,quality:t.quality??100,cmd:'ko_step',payload:{task:t.id},key:`${t.id}-${st.id}`});
}

export default {
  id:'kol',css:true,
  next(t,x){return x.esc(!t.known?'Đọc brief của nhãn hàng':current(t)?.title||'Đã gửi báo cáo');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'ko_intro','📱'));
    if(!t.known)return wrap(top(x)+askCard(x,t,'Đọc brief của nhãn hàng')+tail(x)+notebook(x));
    return wrap(top(x)+person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+briefCard(t,x)+slip(t,x)+
      (t.lines?.length?`<p class="sl-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+notebook(x)+tail(x));
  },
  // Compact layout: the notebook folds; the full layout keeps it open.
  idle(x){return wrap(top(x)+tail(x)+(clean()?notebook(x):`<h3 class="sl-rules-h">📒 Sổ tay Studio Hẻm Xanh</h3>${rulesList(x)}`));},
  input(el,x){return kitInput(el,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'slip kol',eyebrow:'Studio Hẻm Xanh',title:'Sổ tay của studio',body:rulesList(x)}):'';},
  actions:{...kitActions,...slipActions},
  dock:[['car:notes','book','Sổ tay của studio','Ghi rõ quảng cáo, quay dọc, nhạc miễn phí bản quyền, tỉ lệ tương tác'],['car:intro','question','Giới thiệu nghề','Nói thật trước, quay đẹp sau']],
};
