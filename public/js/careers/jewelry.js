/** 💍 Tiệm vàng Ngọc Mây: the morning slip first (count the safe, check the scale, post today's board), then one customer
 * at a time: sell a piece off the case, buy old gold back, or appraise a diamond, one server-graded step at a time
 * (game/careers/jewelry.py). A wrong step stays open to fix and lowers the slip's quality. The board card shows today's
 * buy and sell prices beside yesterday's; the case is restocked in Kho. */
import {data,person,askCard,introCard,deskCard,kitActions,kitInput,notesPage} from './street_kit.js';
import {current,stepsOf,stepCard,rulesList,statsCard,inboxTick,slipActions,stepsArt} from './slip_kit.js';
import {clean,withArt} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk slip jewelry">${body}</div>`;
const STATS={noun:'lượt',money:'earned',moneyLabel:'tiền lời',master:[100,30],title:'Hành trình ở tiệm vàng'};
const ROWS=[['9999','Vàng 9999'],['18k','Vàng 18K'],['14k','Vàng 14K'],['bac','Bạc 925']];

const notebook=x=>`<details class="sl-notebook"><summary>📒 Sổ tay tiệm Ngọc Mây</summary>${rulesList(x)}</details>`;
const top=x=>`${introCard(x,'vg_intro','💍')}${deskCard(x,'vg_desk','Chuyện ở tiệm')}`;
const kho='<button type="button" class="btn ghost small" data-action="inventory">📦 Kho</button>';

/** Today's board, one row per purity, an arrow against yesterday's sell price. Shown once the morning slip posts it. */
function boardCard(x){
  const d=data(x),b=d.board,prev=d.board_prev;
  if(!b?.rows)return '';
  if(!d.opened)return `<section class="card vg-board vg-open"><h3>📈 Bảng giá hôm nay</h3><p class="small">Chưa treo bảng: làm phiếu mở két ở trên trước nhé.</p></section>`;
  const arrow=(k,v)=>{const p=prev?.rows?.[k]?.sell;if(!p||p===v)return '<i class="vg-same" aria-label="như hôm qua">=</i>';
    return p<v?`<i class="vg-up" aria-label="tăng ${x.esc(v-p)} xu">▲ ${x.esc(v-p)}</i>`:`<i class="vg-down" aria-label="giảm ${x.esc(p-v)} xu">▼ ${x.esc(p-v)}</i>`;};
  const rows=ROWS.filter(([k])=>b.rows[k]).map(([k,name])=>{const r=b.rows[k];
    return `<tr><th scope="row">${x.esc(name)}</th><td>${x.fmt(r.buy)}</td><td>${x.fmt(r.sell)}</td><td>${arrow(k,r.sell)}</td></tr>`;}).join('');
  return `<section class="card vg-board" aria-labelledby="vg-board-h"><div class="vg-board-head"><h3 id="vg-board-h">📈 Bảng giá hôm nay</h3>${kho}</div>
    <table class="vg-table"><thead><tr><th scope="col">xu / chỉ</th><th scope="col">Mua vào</th><th scope="col">Bán ra</th><th scope="col">So hôm qua</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="small">Giá giữa 9999: ${x.fmt(b.mid)} xu một chỉ. 1 chỉ = 10 phân = 3,75 g.</p></section>`;
}

const TOOL={ket:'🔐',can:'⚖️',bang:'📈',khay:'💍',khach:'💬',tien:'🧮',hd:'🧾',giao:'🎁',giay:'🪪',quet:'🔬',tra:'↩️',so:'📒',bao:'📝',mau:'🎨',soi:'🔎',cat:'💎'};
const KIND={open:['🔐','Mở két, treo bảng giá','Két và bảng giá'],ban:['💍','Bán nữ trang','Khay nữ trang'],mua:['♻️','Mua lại vàng cũ','Khay vàng cũ'],kc:['💎','Kiểm định kim cương','Khay kiểm định']};
/** The slip on the counter: what is on the tray, and the piece once it is out of the case (not before: picking it is a step). */
function slipCard(t,x){
  const n=t.needs||{},[emoji,what,label]=KIND[t.kind]||KIND.ban;
  const head=t.kind==='ban'&&n.piece_name?`${n.emoji||emoji} ${n.piece_name}`:`${emoji} ${what}`;
  const line=t.kind==='ban'?(n.piece_name?`${n.tuoi} · tiền công theo bảng của tiệm${n.stone?` · hột ${x.fmt(n.stone)} xu`:''}`:'Nghe khách tả món rồi lấy đúng món trong tủ.')
    :t.kind==='mua'?String(n.desc||''):t.kind==='kc'?`Đá rời trong túi giấy · ${n.carat_g||''} g`:'Đầu ngày: chưa đón khách khi chưa xong phiếu này.';
  return `<article class="sl-ticket${t.kind==='open'?' vg-open':''}">${withArt(`<small>${x.esc(what)}</small><h3>${x.esc(head)}</h3><p class="small">${x.esc(line)}</p>`,
    stepsArt(t,{kind:t.kind==='open'?'cash':'tray',icons:TOOL,head:emoji,label}))}</article>`;
}

function slip(t,x){
  const st=current(t);
  if(!st)return `<p class="sl-finished" role="status">✓ Xong phiếu · chất lượng ${x.esc(t.quality)}%${t.paid?` · ${x.fmt(t.paid)} xu`:''}.</p>`;
  const out=t.kind==='ban'&&t.at===0?`<div class="sl-row">${x.cmd('Hết hàng, hẹn khách','vg_out',{task:t.id},'ghost small')}${kho}</div>`:'';
  return stepCard(x,st,{at:t.at,total:stepsOf(t).length,quality:t.quality??100,cmd:'vg_step',payload:{task:t.id},key:`${t.id}-${st.id}`})+out;
}

export default {
  id:'jewelry',css:true,
  next(t,x){return x.esc(!t.known?'Nghe khách cần gì':current(t)?.title||'Xong phiếu');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'vg_intro','💍'));
    if(!t.known)return wrap(top(x)+boardCard(x)+askCard(x,t,'Nghe khách cần gì')+statsCard(x,STATS)+notebook(x));
    const who=t.kind==='open'?'':person(x,t,`<p class="small">${x.esc(t.opening)}</p>`);
    return wrap(top(x)+(t.kind==='open'?'':boardCard(x))+who+slipCard(t,x)+slip(t,x)+
      (t.lines?.length?`<p class="sl-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+notebook(x)+statsCard(x,STATS));
  },
  // Compact layout: the notebook folds; the full layout keeps it open.
  idle(x){return wrap(top(x)+boardCard(x)+statsCard(x,STATS)+(clean()?notebook(x):`<h3 class="sl-rules-h">📒 Sổ tay tiệm Ngọc Mây</h3>${rulesList(x)}`));},
  input(el,x){return kitInput(el,x);},
  meters(root,x){inboxTick(root,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'slip jewelry',eyebrow:'Tiệm vàng Ngọc Mây',title:'Sổ tay của tiệm',body:rulesList(x)}):'';},
  actions:{...kitActions,...slipActions},
  dock:[['inventory','box','Kho','Nhập nữ trang'],['car:notes','book','Sổ tay của tiệm','Chỉ, phân, tuổi vàng, bảng giá, mua lại, 4C'],['car:intro','question','Giới thiệu nghề','Cân trước mặt khách']],
};
