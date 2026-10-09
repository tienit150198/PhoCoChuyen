/** Khách đưa thiếu tiền (server side: game/short_pay.py through game/careers/till.py).
 * Drawn inside the till's cash card (till.js cashPanel): a quiet "count again" button on every cash
 * payment, and once a gap is noticed, the story line and the choices. Nothing here decides anything:
 * each button is the career's `<prefix>short` command and the server tells what happened. */
import {stylesheet} from '../lazy.js';

stylesheet('/css/shortpay.css');

/** The command of each till career (its SPEC prefix + 'short'). */
export const SHORT_ACT={clothing:'ao_short',pet_shop:'ps_short',tra_da:'td_short',fruit:'tc_short',drain:'cg_short',ice_cream:'kem_short',com:'com_short',nail:'nl_short',pho:'pho_short',photobooth:'pb_short',zpop:'zp_short'};
const actOf=id=>SHORT_ACT[String(id||'').split('-')[0]]||'';

const OPEN=['open','kid','cheat'];
const LABEL={
  ask:['🙏 Nhắc khách đưa thêm','Hỏi nhẹ nhàng, khách tự đếm lại'],
  police:['🚓 Báo công an','Phải chờ công an tới, khách phía sau sốt ruột'],
  let:['🤐 Bỏ qua, coi như bớt giá','Mất khoản thiếu, khách vui vẻ ra về'],
  owe:['📒 Cho nợ, mai trả','Hẹn bé mai mang ra trả'],
  less:['🧺 Bớt món cho vừa tiền','Bé để lại bớt một món'],
  give:['🎁 Thôi, cho con luôn','Mất khoản thiếu, bé vui'],
};
const CHEAT_LET=['🚶 Để khách đi','Mất khoản thiếu'];
const TITLE={open:'Khách đưa thiếu tiền',kid:'Bé không đủ tiền',cheat:'Khách chối, không chịu đưa thêm'};

/** A gap is noticed and waits for a decision (the hand-over waits too). */
export const gapOpen=cash=>Boolean(cash?.gap&&OPEN.includes(cash.gap.stage));

/** The block inside the cash card: the count button, or the gap's story and choices. */
export function gapBlock(x,id,cash){
  const act=actOf(id);
  if(!cash||!act||cash.outcome!=null)return '';
  const g=cash.gap;
  if(!g){
    return `<div class="sp-count">${x.cmd(cash.counted?'✓ Đã đếm lại: đủ tiền':'🔍 Đếm lại tiền khách đưa',act,{task:id,choice:'count'},'small ghost',cash.counted)}</div>`;
  }
  const line=g.line?`<p class="sp-line">${x.esc(g.line)}</p>`:'';
  if(g.stage==='done')return `<div class="sp-card done" data-gap="${x.esc(id)}">${line}</div>`;
  const btn=c=>{
    const [label,hint]=c==='let'&&g.stage==='cheat'?CHEAT_LET:LABEL[c];
    const inner=`${label}<small>${hint}</small>`;
    return c==='police'
      ?x.confirmCmd(inner,act,{task:id,choice:c},'Gọi công an khu vực tới quầy? Phải chờ một lúc, khách phía sau sẽ sốt ruột.','sp-opt')
      :x.cmd(inner,act,{task:id,choice:c},'sp-opt');
  };
  return `<div class="sp-card" data-gap="${x.esc(id)}" role="group" aria-label="${x.esc(TITLE[g.stage]||TITLE.open)}">
    <h5>⚠️ ${x.esc(TITLE[g.stage]||TITLE.open)} · thiếu ${x.money(g.short)}</h5>${line}
    <div class="sp-opts">${(g.choices||[]).map(btn).join('')}</div></div>`;
}

/** One guide row while a gap waits for a decision (null otherwise: an unnoticed gap is never hinted). */
export function gapStep(x,id,cash){
  if(!gapOpen(cash))return null;
  return {ok:null,label:`Khách đưa thiếu ${cash.gap.short} xu: chọn cách xử lý`,go:{sel:`[data-gap="${id}"]`},pulse:''};
}
