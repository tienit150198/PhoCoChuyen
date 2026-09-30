/** Kết quả kinh doanh: a plain profit-and-loss read of one workplace day.
 * Markup only, no rules: every number comes from the career's own ledger
 * (c.ops.finance.ledger, written by game/operations.py record_money) and the
 * end-of-day summary (c.shift_summary, with its `operations` and `journey`
 * parts). Nothing here changes game state.
 *
 * Exports
 *  - groupOf(category, amount)      → 'revenue'|'cogs'|'opex'|'losses'|'other'|'transfers'
 *  - pnlOf(career, day)             → the day's statement (see below)
 *  - pnlSeries(career, day, n=7)    → [{day, net, revenue}] for the n days ending at `day`
 *  - pnlCard(envOrArgs)             → end-of-day "Kết quả kinh doanh" card (HTML)
 *  - orderReceipt(args)             → per-order "Bán · vốn · lời" line
 *  - bowlItems(bowl)                → restaurant bowl → {itemId: qty} for orderReceipt
 * The mapping and the wiring are described in
 * docs/superpowers/specs/2026-09-29-pnl-design.md. */
import {icon,escapeHTML as esc} from '../icons.js';

const fmt=n=>Math.round(Number(n)||0).toLocaleString('vi-VN');
const signed=n=>`${n>0?'+':n<0?'−':''}${fmt(Math.abs(n))}`;
const tone=n=>n>0?'good':n<0?'bad':'flat';

/* ------------------------------------------------------------ category map */
// Every money category written by game/*.py. A row lands in exactly one group,
// so revenue − cogs − opex − losses + other + transfers = the ledger's cash change.
// Two-sided categories pick their group by the row's sign (in = money received).
const CAT={
  // Doanh thu: money customers (or the employer) paid for the work itself.
  revenue:['revenue','Tiền bán hàng'],room:['revenue','Tiền phòng khách trả'],tip:['revenue','Tiền tip của khách'],
  commission:['revenue','Hoa hồng'],salary:['revenue','Lương'],
  // Giá vốn: the goods and ingredients that went into what was sold.
  stock:['cogs','Nhập hàng, nguyên liệu'],materials:['cogs','Vật tư, bao bì'],tour_cost:['cogs','Vé và chi phí đoàn'],
  // Chi phí vận hành: keeping the doors open.
  wage:['opex','Lương nhân viên'],staff:['opex','Thuê người thời vụ'],utility:['opex','Điện nước'],utilities:['opex','Gas, điện nước'],
  rent:['opex','Tiền mặt bằng'],insurance:['opex','Phí bảo vệ tài sản'],tax:['opex','Thuế'],repair:['opex','Sửa chữa'],
  recruitment:['opex','Tuyển người'],training:['opex','Đào tạo nhân viên'],marketing:['opex','Quảng cáo'],security:['opex','Đồ an ninh'],
  upgrade:['opex','Nâng cấp, mua sắm'],property_setup:['opex','Chuyển mặt bằng'],upkeep:['opex','Duy trì khi vắng chủ'],
  reopen_fee:['opex','Phí mở lại'],situation:['opex','Chi phí tình huống'],other_cost:['opex','Chi khác'],
  legal:['opex','Phí luật sư, tư vấn'],office:['opex','Giấy tờ, văn phòng'],
  // Thất thoát: money that left without buying anything.
  theft_loss:['losses','Bị trộm, mất tiền'],scam_loss:['losses','Bị lừa'],bad_debt:['losses','Khách quỵt'],unpaid:['losses','Khách quỵt'],
  discount:['losses','Bớt giá cho khách'],fine:['losses','Tiền phạt'],abandon_fine:['losses','Bỏ dở việc'],
  under_table:['losses','Tiền lót tay, không biên lai'],damage:['losses','Hư hỏng tài sản'],medical:['losses','Tiền thuốc'],
  // Khác: rewards, support and money that came back.
  grant:['other','Hỗ trợ khởi đầu'],recovery:['other','Lấy lại tài sản'],insurance_recovery:['other','Hỗ trợ tài sản'],
  security_reward:['other','Quỹ khu phố thưởng'],skill_reward:['other','Thưởng tay nghề'],goal_reward:['other','Thưởng mục tiêu ngày'],
  activity_reward:['other','Thưởng trò nhỏ'],festival_reward:['other','Thưởng ngày hội'],story_reward:['other','Thưởng câu chuyện'],
  situation_reward:['other','Thưởng tình huống'],promotion:['other','Được giới thiệu quán'],other_income:['other','Thu khác'],
  // Chuyển tiền của chủ: moves money between the fund and your wallet, never profit.
  owner_draw:['transfers','Rút tiền lời về ví'],owner_capital:['transfers','Góp vốn từ ví'],salary_to_wallet:['transfers','Lương chuyển về ví'],
};
const TWO_SIDED={
  refund:{in:['cogs','Nhà cung cấp hoàn tiền'],out:['losses','Hoàn tiền cho khách']},
  compensation:{in:['other','Được đền bù'],out:['losses','Đền bù cho khách']},
  gift:{in:['other','Quà nhận được'],out:['opex','Quà tặng, ủng hộ']},
  bonus:{in:['other','Tiền thưởng'],out:['opex','Thưởng nhân viên']},
  service:{in:['revenue','Tiền dịch vụ'],out:['opex','Thuê dịch vụ']},
  incident:{in:['other','Tiền từ sự việc'],out:['losses','Chi cho sự việc']},
};
export const GROUPS={revenue:'Doanh thu',cogs:'Giá vốn',opex:'Chi phí vận hành',losses:'Thất thoát',other:'Khác',transfers:'Chuyển tiền của chủ'};
const BILL_CATS=new Set(['wage','utility','rent','insurance','tax','repair']);

function classify(cat,amount){
  const two=TWO_SIDED[cat];if(two)return two[amount>=0?'in':'out'];
  return CAT[cat]||null;
}
export const groupOf=(cat,amount=0)=>(classify(cat,amount)||['other'])[0];
const labelOf=row=>(classify(row.category,row.amount)||[null,''])[1]||String(row.reason||row.category||'Khoản khác');
/** "Nhập 6 vắt Mì tươi · Nhà phân phối Hạt Nắng" → "Nhập 6 vắt Mì tươi". */
const shortReason=r=>String(r||'').split(' · ')[0].trim()||'Khoản khác';

/* ------------------------------------------------------------- statements */
const ledgerOf=career=>{const l=career?.ops?.finance?.ledger;return Array.isArray(l)?l:[];};

/** One day's statement from the ledger (cash basis). Costs are positive numbers.
 * net = revenue − cogs − opex − losses + other; cashChange = net + transfers. */
export function pnlOf(career,day){
  const rows=ledgerOf(career).filter(r=>r&&r.day===day&&Number.isFinite(r.amount));
  const sums={revenue:0,cogs:0,opex:0,losses:0,other:0,transfers:0};
  const lines={revenue:{},cogs:{},opex:{},losses:{},other:{},transfers:{}};
  const byReason={};
  let draw=0,capital=0,salary=0,tips=0,billsPaid=0;
  for(const r of rows){
    const g=groupOf(r.category,r.amount),label=labelOf(r),a=r.amount;
    sums[g]+=a;
    const key=r.category+'|'+label,ln=lines[g][key]||(lines[g][key]={category:r.category,label,amount:0,count:0});
    ln.amount+=a;ln.count++;
    if(a<0&&(g==='cogs'||g==='opex'||g==='losses')){
      const k=g+'|'+shortReason(r.reason),x=byReason[k]||(byReason[k]={reason:shortReason(r.reason),label,group:g,amount:0,count:0});
      x.amount+=-a;x.count++;
    }
    if(r.category==='owner_draw')draw+=-a;
    if(r.category==='owner_capital')capital+=a;
    if(r.category==='salary')salary+=a;
    if(r.category==='tip')tips+=a;
    if(BILL_CATS.has(r.category)&&a<0)billsPaid+=-a;
  }
  const revenue=sums.revenue,cogs=-sums.cogs,opex=-sums.opex,losses=-sums.losses,other=sums.other,transfers=sums.transfers;
  const gross=revenue-cogs,net=gross-opex-losses+other;
  const list=g=>Object.values(lines[g]).filter(x=>x.amount).sort((a,b)=>Math.abs(b.amount)-Math.abs(a.amount));
  return {day,count:rows.length,revenue,cogs,opex,losses,other,transfers,gross,net,cashChange:net+transfers,
    margin:revenue>0?Math.round((net-other)/revenue*100):null,grossMargin:revenue>0?Math.round(gross/revenue*100):null,
    lines:Object.fromEntries(Object.keys(lines).map(g=>[g,list(g)])),
    topCosts:Object.values(byReason).sort((a,b)=>b.amount-a.amount).slice(0,3),
    draw,capital,salary,tips,billsPaid,
    salaryOnly:revenue>0&&revenue===salary};
}

/** Daily net for the n days ending at `day` (days before 1 are skipped). */
export function pnlSeries(career,day,n=7){
  const out=[];
  for(let d=Math.max(1,day-n+1);d<=day;d++){const p=pnlOf(career,d);out.push({day:d,net:p.net,revenue:p.revenue,count:p.count});}
  return out;
}

/* ------------------------------------------------------------------ chart */
function miniChart(series,today){
  if(series.length<2)return '';
  const W=280,H=104,top=18,bottom=20,plot=H-top-bottom,slot=W/7,bw=Math.min(26,slot-10);
  // Positive bars grow up from zero, losses hang below; zero moves so both fit.
  const posMax=Math.max(0,...series.map(s=>s.net)),negMax=Math.max(0,...series.map(s=>-s.net));
  const scale=plot/((posMax+negMax)||1),zero=top+posMax*scale;
  const off=(7-series.length)*slot/2;
  const bars=series.map((s,i)=>{
    const x=off+i*slot+(slot-bw)/2,h=Math.max(s.net?2:0,Math.abs(s.net)*scale),y=s.net>=0?zero-h:zero,cls=`pnl-bar ${tone(s.net)}${s.day===today?' today':''}`;
    const label=s.day===today&&s.net?`<text class="pnl-val" x="${x+bw/2}" y="${s.net>=0?Math.max(11,y-5):zero-5}" text-anchor="middle">${signed(s.net)}</text>`:'';
    const tip=`Ngày ${s.day}: ${s.net>0?'lãi':s.net<0?'lỗ':'hòa'} ${fmt(Math.abs(s.net))} xu${s.revenue?` · doanh thu ${fmt(s.revenue)} xu`:''}`;
    return `<g><title>${esc(tip)}</title><rect class="pnl-hit" x="${off+i*slot}" y="0" width="${slot}" height="${H-bottom}"/>${h?`<rect class="${cls}" x="${x}" y="${y}" width="${bw}" height="${h}" rx="3"/>`:''}${label}<text class="pnl-day${s.day===today?' today':''}" x="${x+bw/2}" y="${H-5}" text-anchor="middle">${s.day===today?'Hôm nay':'N'+s.day}</text></g>`;
  }).join('');
  const total=series.reduce((a,s)=>a+s.net,0),avg=Math.round(total/series.length);
  const aria=`Lãi lỗ ròng ${series.length} ngày gần nhất: ${series.map(s=>`ngày ${s.day} ${signed(s.net)} xu`).join(', ')}.`;
  return `<section class="pnl-trend"><div class="pnl-sub"><h5>${series.length} ngày gần nhất</h5><small>Tổng <b class="${tone(total)}">${signed(total)} xu</b> · trung bình ${signed(avg)} xu/ngày</small></div>
    <svg class="pnl-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}" preserveAspectRatio="xMidYMid meet"><line class="pnl-zero" x1="0" x2="${W}" y1="${zero}" y2="${zero}"/>${bars}</svg></section>`;
}

/* ------------------------------------------------------------------- card */
const row=(sign,label,amount,note,{cls='',strong=false,show=true}={})=>show?`<tr class="${cls}${amount===0&&!strong?' zero':''}"><th scope="row"><div class="pnl-rowhead"><span class="pnl-sign" aria-hidden="true">${sign}</span><span class="pnl-lbl">${strong?`<b>${label}</b>`:label}${note?`<small>${note}</small>`:''}</span></div></th><td>${strong?`<b>${fmt(Math.abs(amount))}</b>`:fmt(Math.abs(amount))}</td></tr>`:'';

function lead(p,s){
  if(p.salaryOnly)return `Lương hôm nay ${fmt(p.salary)} xu${p.net<p.salary?`, trừ chi phí còn ${fmt(p.net)} xu`:''}.`;
  if(!p.count)return 'Hôm nay sổ chưa ghi khoản thu chi nào.';
  if(!p.revenue&&p.net<0)return `Hôm nay chưa bán được gì, đã chi ${fmt(-p.net)} xu.`;
  if(p.net>0)return `Bán được ${fmt(p.revenue)} xu, trừ tiền hàng và chi phí còn lời ${fmt(p.net)} xu.`;
  if(p.net===0)return `Bán được ${fmt(p.revenue)} xu, vừa đủ bù chi phí.`;
  const worst=p.topCosts[0];
  return `Hôm nay lỗ ${fmt(-p.net)} xu${worst?`, nặng nhất là ${esc(worst.group==='losses'?worst.label.toLowerCase():'“'+worst.reason+'”')} (${fmt(worst.amount)} xu)`:''}.`;
}

/** Normalise pnlCard's input: the app env ({api}) or plain {career, summary, journey, cid, content}. */
function argsOf(x={}){
  if(x.api){const st=x.api.state||{},cid=st.current,c=st.careers?.[cid];return {cid,career:c,summary:c?.shift_summary,journey:st.journey,content:x.api.content};}
  return {cid:x.cid,career:x.career,summary:x.summary??x.career?.shift_summary,journey:x.journey,content:x.content,day:x.day};
}

/** End-of-day card: result, statement, biggest costs, 7-day bars and what reached your wallet. */
export function pnlCard(x){
  const {cid,career,summary:s,journey:J,day:askDay,content}=argsOf(x);
  if(!career)return '';
  const day=askDay??s?.day??Math.max(1,(career.day||1)-(career.open?0:1));
  const p=pnlOf(career,day),ops=s?.operations||null,jr=s?.journey||null;
  const office=p.salaryOnly||(career.job?.required&&!p.revenue);
  const heroLabel=office?'Bạn kiếm được hôm nay':p.net>0?'Lãi ròng hôm nay':p.net<0?'Lỗ hôm nay':'Hòa vốn';
  const hero=`<div class="pnl-hero ${tone(p.net)}"><strong>${signed(p.net)}<span> xu</span></strong><span>${heroLabel}${p.margin>0&&p.net>0&&!office?` · biên lãi ${p.margin}%`:''}</span></div>`;

  // Statement: one line of plain Vietnamese under each figure.
  const revNote=office?'tiền công ty trả cho ngày làm':`tiền khách trả${p.tips?`, gồm ${fmt(p.tips)} xu tip`:''}`;
  const showGoods=!office||p.cogs!==0;
  const table=`<table class="pnl-table"><caption class="sr-only">Bảng kết quả kinh doanh ngày ${day}</caption><tbody>
    ${row('',office?'Lương':'Doanh thu',p.revenue,revNote)}
    ${row('−','Giá vốn',p.cogs,'tiền hàng, nguyên liệu nhập hôm nay',{show:showGoods})}
    ${row('=','Lãi gộp',p.gross,'',{cls:'sub '+tone(p.gross),strong:true,show:showGoods})}
    ${row('−','Chi phí vận hành',p.opex,'điện nước, lương, thuê, sửa chữa…',{show:!office||p.opex!==0})}
    ${row('−','Thất thoát',p.losses,'bị quỵt, trộm, lừa, hoàn tiền, bớt giá, phạt',{show:!office||p.losses!==0})}
    ${row(p.other<0?'−':'+','Khác',p.other,'thưởng, hỗ trợ, tiền được đền',{show:!office||p.other!==0})}
    ${row('=',office?'Còn lại':p.net<0?'Lỗ ròng':'Lãi ròng',p.net,'',{cls:'total '+tone(p.net),strong:true,show:!office||p.net!==p.revenue})}
  </tbody></table>`;
  const marginNote=office||p.margin===null||p.net>0&&p.margin>0?'':p.losses>0&&p.net+p.losses>0?`<p class="pnl-note">${icon('note',14)}<span>Không có thất thoát thì hôm nay đã lời ${fmt(p.net+p.losses)} xu.</span></p>`:'';

  // Bills: today's costs become invoices paid later; yesterday's invoices are paid today.
  const accrued=ops?(Number(ops.wages)||0)+(Number(ops.utilities)||0)+(Number(ops.rent_accrued)||0):0;
  const bills=[];
  if(accrued)bills.push(`Chi phí hôm nay sẽ thành hóa đơn trả sau: <b>${fmt(accrued)} xu</b> (${[ops.wages?`lương NV ${fmt(ops.wages)}`:'',ops.utilities?`điện nước ${fmt(ops.utilities)}`:'',ops.rent_accrued?`thuê ${fmt(ops.rent_accrued)}`:''].filter(Boolean).join(' · ')}), chưa trừ ở trên.`);
  if(p.billsPaid)bills.push(`Đã trả ${fmt(p.billsPaid)} xu hóa đơn của ngày trước, tính vào chi phí hôm nay.`);
  const usedCost=office?null:servedCost(career,day,content);
  if(usedCost&&usedCost.cost>0)bills.push(`Nguyên liệu đã dùng cho ${fmt(usedCost.orders)} đơn hôm nay: ~${fmt(usedCost.cost)} xu theo giá nhập${p.cogs?'':' (hàng nhập từ trước nên không nằm trong Giá vốn hôm nay)'}.`);
  if(s?.expired_value)bills.push(`Hàng hết hạn phải bỏ: ${fmt(s.expired_value)} xu tiền vốn (đã chi lúc nhập hàng).`);
  const billNote=bills.length?`<ul class="pnl-bills">${bills.map(b=>`<li>${b}</li>`).join('')}</ul>`:'';

  // Biggest costs by reason.
  const costTotal=p.topCosts.reduce((a,c)=>a+c.amount,0)||1,allCosts=p.cogs+p.opex+p.losses;
  const top=p.topCosts.length?`<section class="pnl-top"><div class="pnl-sub"><h5>Chi nhiều nhất hôm nay</h5><small>Giá vốn + vận hành + thất thoát: ${fmt(Math.max(allCosts,0))} xu</small></div><ol>${p.topCosts.map(c=>`<li><span class="pnl-top-text"><b>${esc(c.reason)}</b><small>${esc(GROUPS[c.group])}${c.label&&c.label!==c.reason?` · ${esc(c.label)}`:''}${c.count>1?` · ${c.count} lần`:''}</small></span><b class="pnl-amt">−${fmt(c.amount)}</b><i class="pnl-meter ${c.group}" style="--w:${Math.max(4,Math.round(c.amount/costTotal*100))}%" aria-hidden="true"></i></li>`).join('')}</ol></section>`:'';

  const trend=miniChart(pnlSeries(career,day,7),day);

  // What actually reached you: the fund is the shop's money; the wallet is yours.
  let mine='';
  const place=J?.places?.[cid];
  if(J?.story){
    const lines=[];
    if(p.draw)lines.push(['+','Rút tiền lời về ví',p.draw]);
    if(jr?.salary)lines.push(['+','Lương về ví',jr.salary]);
    if(p.capital)lines.push(['−','Góp vốn vào quỹ',-p.capital]);
    if(jr?.living)lines.push(['−','Tiền phòng và cơm nước',-jr.living]);
    if(jr?.upkeep)lines.push(['−','Duy trì nơi vắng chủ',-jr.upkeep]);
    const hist=Array.isArray(J.history)&&jr?J.history.filter(h=>h.day===jr.life_day):null;
    const change=hist&&hist.length?hist.reduce((a,h)=>a+(Number(h.amount)||0),0):lines.reduce((a,l)=>a+l[2],0);
    const kept=office?0:p.net-p.draw;
    const canDraw=!office&&place&&!place.employed&&place.withdraw_max>0&&(kept>0||J.wallet<0);
    mine=`<section class="pnl-mine"><div class="pnl-sub"><h5>${icon('coin',15)} Bạn kiếm được</h5></div>
      ${lines.length?`<ul class="pnl-mine-list">${lines.map(([sg,l,a])=>`<li><span>${l}</span><b class="${tone(a)}">${sg}${fmt(Math.abs(a))}</b></li>`).join('')}</ul>`:''}
      <div class="pnl-mine-total"><span>Ví thay đổi${jr?` Ngày ${fmt(jr.life_day)}`:''}</span><b class="${tone(change)}">${signed(change)} xu</b></div>
      ${jr?`<p class="pnl-note"><span>Ví hiện có <b>${fmt(jr.wallet)} xu</b>${jr.wallet<0?' · đang nợ, rút tiền lời để trả nhé':''}.</span></p>`:''}
      ${kept>0?`<p class="pnl-note">${icon('home',14)}<span>Còn ${fmt(kept)} xu lời hôm nay đang ở quỹ tiệm${canDraw?`, rút được tối đa ${fmt(place.withdraw_max)} xu`:''}.</span></p>`:''}
      ${canDraw?`<button type="button" class="btn ghost small" data-action="jrView" data-view="wallet">${icon('coin',14)} Mở ví để rút tiền lời</button>`:''}</section>`;
  }else if(!office&&p.net>0){
    mine=`<p class="pnl-note">${icon('home',14)}<span>Tiền lời ${fmt(p.net)} xu đã vào quỹ tiệm (quỹ hiện có ${fmt(career.money)} xu).</span></p>`;
  }

  // Full detail, grouped, for the curious.
  const detail=p.count?`<details class="pnl-detail"><summary>Sổ chi tiết ngày ${day} · ${p.count} khoản</summary>${Object.entries(p.lines).filter(([,ls])=>ls.length).map(([g,ls])=>`<h6>${esc(GROUPS[g])}</h6><ul>${ls.map(l=>`<li><span>${esc(l.label)}${l.count>1?` <small>× ${l.count}</small>`:''}</span><b class="${tone(l.amount)}">${signed(l.amount)}</b></li>`).join('')}</ul>`).join('')}${p.transfers?'<p class="pnl-note"><span>Chuyển tiền của chủ (rút, góp vốn, lương về ví) không tính vào lãi lỗ.</span></p>':''}</details>`:'';

  return `<article class="card pnl" aria-labelledby="pnl-title-${day}"><header class="pnl-head"><span class="eyebrow">${icon('clipboard',14)} KẾT QUẢ ${office?'NGÀY LÀM':'KINH DOANH'} · NGÀY ${day}</span><h4 id="pnl-title-${day}" class="sr-only">Kết quả kinh doanh ngày ${day}</h4>${hero}<p class="pnl-lead">${lead(p,s)}</p></header>
    ${table}${marginNote}${billNote}${top}${trend}${mine}${detail}</article>`;
}

/** Catalogue cost of what today's served orders used (tasks that keep `served`, e.g. restaurant bowls). */
function servedCost(career,day,content){
  if(!content?.inventory?.items)return null;
  const sold=new Set(ledgerOf(career).filter(r=>r&&r.day===day&&r.category==='revenue'&&r.ref).map(r=>r.ref));
  const tasks=(career.tasks||[]).filter(t=>t&&t.served&&sold.has(t.id));
  let cost=0,orders=0;
  for(const task of tasks){const r=orderReceipt({career,task,content});if(r&&r.estimated){cost+=r.cost;orders++;}}
  return orders?{cost,orders}:null;
}

/* ---------------------------------------------------------- order receipt */
/** Restaurant bowl → the stock it used (broth: one pot portion = 1/6 of a pack). */
export function bowlItems(bowl){
  if(!bowl||typeof bowl!=='object')return {};
  const out={},add=(k,q)=>{if(q)out[k]=(out[k]||0)+q;};
  add('noodle',Array.isArray(bowl.noodles)?bowl.noodles.length:0);
  if(bowl.container==='box')add('box',1);
  add('chili',Number(bowl.chili)||0);
  if(bowl.broth)add('pack_'+bowl.broth,1/6);
  for(const [k,q] of Object.entries(bowl.toppings||{}))add(k,Number(q)||0);
  return out;
}

/** "Bán 48 xu · vốn ~18 xu · lời ~30 xu" for one finished task.
 * args: {career, task|taskId, content?, items?, cost?}
 *  - sale: ledger rows whose ref is the task id (revenue + tip);
 *  - cost: `cost` if given; else catalogue cost of `items` ({itemId: qty}, e.g. bowlItems(bowl))
 *    from content.inventory.items[career id]; else the restaurant's served bowls. Returns null before any sale. */
export function orderReceipt({career,task,taskId,content,items,cost}={}){
  const id=taskId||task?.id;if(!career||!id)return null;
  const rows=ledgerOf(career).filter(r=>r&&r.ref===id);
  const sale=rows.filter(r=>groupOf(r.category,r.amount)==='revenue'&&r.category!=='tip').reduce((a,r)=>a+r.amount,0);
  const tip=rows.filter(r=>r.category==='tip').reduce((a,r)=>a+r.amount,0);
  const refunds=rows.filter(r=>r.amount<0).reduce((a,r)=>a-r.amount,0);
  if(!sale&&!tip)return null;
  let spent=Number.isFinite(cost)?cost:null,estimated=false;
  const cat=content?.inventory?.items?.[task?.career||career.id];
  const bowls=task?.served?.bowls||(task?.served?.bowl?[task.served.bowl]:null);
  const useItems=items||(bowls&&Array.isArray(cat)?bowls.reduce((acc,b)=>{for(const [k,q] of Object.entries(bowlItems(b)))acc[k]=(acc[k]||0)+q;return acc;},{}):null);
  if(spent===null&&useItems&&Array.isArray(cat)){
    const idx=Object.fromEntries(cat.map(i=>[i.id,i]));
    spent=Math.round(Object.entries(useItems).reduce((a,[k,q])=>a+(Number(idx[k]?.cost)||0)*q,0));estimated=true;
  }
  if(spent===null&&bowls){spent=bowls.reduce((a,b)=>a+(Number(b.cost)||0),0);}
  const profit=spent===null?null:sale+tip-refunds-spent,t=estimated?'~':'';
  const parts=[`Bán ${fmt(sale)} xu`];
  if(tip)parts.push(`tip ${fmt(tip)} xu`);
  if(refunds)parts.push(`hoàn ${fmt(refunds)} xu`);
  if(spent!==null)parts.push(`vốn ${t}${fmt(spent)} xu`,`${profit>=0?'lời':'lỗ'} ${t}${fmt(Math.abs(profit))} xu`);
  const text=parts.join(' · ');
  const html=`<p class="pnl-receipt ${profit===null?'':tone(profit)}">${icon('coin',14)}<span>${parts.map((x,i)=>i===parts.length-1&&profit!==null?`<b>${esc(x)}</b>`:esc(x)).join(' · ')}</span></p>`;
  return {sale,tip,refunds,cost:spent,profit,estimated,text,html};
}
