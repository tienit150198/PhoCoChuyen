/** 🔧 Xưởng độ xe Tư Pít-tông: hear where the customer wants to drive, inspect the vehicle, build the sheet in the goal's
 * priority order within the budget (legal parts only), settle their awkward demands, fit the parts, read the dyno chart,
 * measure noise or CO against the notebook, test-drive and stick on a true spec card. The server grades each step
 * (game/careers/tuning.py); a wrong one stays open to fix and lowers the ticket's quality, an illegal one also brings the
 * ward's warning. Other players' vehicles (🛎️ Phố dịch vụ, game/tuning_service.py) are worked in "Xe của người chơi".
 * Beside the ticket the vehicle gains its parts as they are fitted (ui-kit buildUp, kind car / bike). */
import {data,person,askCard,introCard,deskCard,kitActions,kitInput,notesPage} from './street_kit.js';
import {current,stepsOf,stepCard,rulesList,statsCard,ordersCard,inboxTick,slipActions,stepsArt} from './slip_kit.js';
import {clean,withArt,buildUp} from '../ui-kit.js';

const wrap=body=>`<div class="career-job sk slip tuning">${body}</div>`;
const ORDERS={id:'tuning',svcCmd:'dx_svc',attrs:'data-coach="tuning-orders"',title:'Xe của người chơi',emoji:'🚗',noun:'Xe',
  empty:'Chưa có xe nào. Người chơi đặt 🔧 Độ động cơ, 🛞 Độ khung gầm hoặc 🧰 Bảo dưỡng xe độ ở 🛎️ Phố dịch vụ; nhận đơn rồi làm ở đây.',
  done:'🔧 Làm xong. Bấm Giao để trả xe cho khách.'};
const STATS={noun:'xe',money:'earned',moneyLabel:'tiền công',master:[90,30],title:'Hành trình ở xưởng'};
const ASK='Nghe khách muốn độ gì';

const notebook=x=>`<details class="sl-notebook"><summary>📒 Sổ tay xưởng Tư Pít-tông</summary>${rulesList(x)}</details>`;
const top=x=>`${introCard(x,'dx_intro','🔧')}${deskCard(x,'dx_desk','Chuyện ở xưởng')}`;
const tail=x=>ordersCard(x,ORDERS)+statsCard(x,STATS)+legalLine(x);

/** One icon per step of the ticket (the slip strip under the vehicle). */
const PART={muc_tieu:'🎯',kiem:'🔎',giay:'📄',chon:'📋',tong:'🧮',luat:'⚖️',lap:'🔧',do:'📏',dyno:'📈',afr:'⛽',an_toan:'🛡️',chay_thu:'🏁',giao:'🏷️'};
/** The paint of the vehicle on the ticket (tuning_content.COLORS). */
const PAINT={'đỏ đô':'#8e1b1b','trắng ngọc':'#e9e6dc','xanh dương':'#2c5fa8','đen nhám':'#2f2f33','xám xi măng':'#8a8d90','vàng chanh':'#c9c22e'};
const mods=x=>x.cc?.mods||{};

/** Is part `m` already on the vehicle? Its own fitting / reading step is behind the open one, or the car is on the dyno. */
function fitted(t,m){
  const n=t.needs||{},steps=stepsOf(t),at=Number(t.at)||0;
  if(n.dyno)return true;
  return steps.some((st,i)=>i<at&&(st.id===`lap.${m}`||st.id===`do.${m}`));
}

/** The vehicle gaining its parts: solid once fitted, grey until then; before the sheet is settled, only the bare car. */
function vehicleArt(t,x){
  const n=t.needs||{},M=mods(x),kind=n.kind==='bike'?'bike':'car';
  const items=(n.build||[]).map(m=>({e:M[m]?.emoji||'🔧',t:M[m]?.name||m,cls:fitted(t,m)?'':'todo'}));
  const done=items.filter(i=>!i.cls).length;
  const art=buildUp({kind,items,empty:n.build?'':'chưa lên bảng độ',caption:n.build?`${kind==='bike'?'🏍️':'🚗'} ${done}/${items.length} món`:`${kind==='bike'?'🏍️':'🚗'} xe zin`,
    label:`${n.vehicle||'Xe'} đang độ`,cls:'dx-car'});
  const paint=PAINT[n.color]||'#b8322a';
  return `<div class="dx-paint" style="--dx-paint:${x.esc(paint)}">${art}${stepsArt(t,{kind:'paper',icons:PART,head:'📋',label:'Phiếu độ'})}</div>`;
}

/** The dyno sheet: power before (dashed) and after (solid) against rpm, the AFR line under it with the 13,5 limit. */
function dynoChart(dyno,x){
  if(!dyno||!dyno.rpm?.length)return '';
  const W=320,H=150,L=34,R=8,T=12,B=26,rpm=dyno.rpm,n=rpm.length;
  const top=Math.max(...dyno.after,...dyno.before),ceil=Math.ceil(top*1.1/10)*10||10;
  const X=i=>L+(n>1?i*(W-L-R)/(n-1):0),Y=v=>T+(H-T-B)*(1-v/ceil);
  const line=a=>a.map((v,i)=>`${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
  const grid=[0,.5,1].map(f=>{const v=Math.round(ceil*f);return `<line x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}" class="dx-grid"/><text x="${L-4}" y="${Y(v)+4}" text-anchor="end">${v}</text>`;}).join('');
  const ticks=rpm.map((r,i)=>i%2&&n>6?'':`<text x="${X(i)}" y="${H-8}" text-anchor="middle">${r>=1000?(r/1000).toLocaleString('vi-VN'):r}</text>`).join('');
  const changed=dyno.after.some((v,i)=>v!==dyno.before[i]);
  // The AFR strip: tenths, 11–15, the 13,5 line in red.
  const AH=58,AY=v=>8+(AH-18)*(1-(Math.max(110,Math.min(150,v))-110)/40);
  const afr=dyno.afr||[],lim=x.cc?.limits?.afr||135;
  const afrLine=afr.map((v,i)=>`${X(i).toFixed(1)},${AY(v).toFixed(1)}`).join(' ');
  const dots=afr.map((v,i)=>v>lim?`<circle cx="${X(i).toFixed(1)}" cy="${AY(v).toFixed(1)}" r="3.5" class="dx-lean"/>`:'').join('');
  const fmt=v=>`${Math.floor(v/10)},${v%10}`;
  const said=`Biểu đồ dyno: ${changed?'trước độ và sau độ, ':''}công suất theo vòng tua ${rpm[0]} đến ${rpm[n-1]} vòng/phút; AFR từ ${fmt(Math.min(...afr))} đến ${fmt(Math.max(...afr))}.`;
  const rows=rpm.map((r,i)=>`<tr><td>${r.toLocaleString('vi-VN')}</td>${changed?`<td>${dyno.before[i]}</td>`:''}<td>${dyno.after[i]}</td><td>${fmt(afr[i]??0)}</td></tr>`).join('');
  return `<figure class="card dx-dyno" aria-label="${x.esc(said)}">
    <figcaption><b>📈 Biểu đồ dyno</b><span class="dx-legend">${changed?'<i class="dx-k-before"></i> Trước độ <i class="dx-k-after"></i> Sau độ':'<i class="dx-k-after"></i> Công suất'} · ${x.esc(dyno.unit||'mã lực')}</span></figcaption>
    <svg viewBox="0 0 ${W} ${H}" role="presentation" class="dx-svg">${grid}${ticks}<text x="${W-R}" y="${H-8+12}" text-anchor="end" class="dx-axis">nghìn vòng/phút</text>
      ${changed?`<polyline points="${line(dyno.before)}" class="dx-before"/>`:''}<polyline points="${line(dyno.after)}" class="dx-after"/></svg>
    <svg viewBox="0 0 ${W} ${AH}" role="presentation" class="dx-svg dx-afr-svg"><text x="${L-4}" y="${AY(lim)+4}" text-anchor="end">13,5</text>
      <line x1="${L}" x2="${W-R}" y1="${AY(lim)}" y2="${AY(lim)}" class="dx-limit"/><polyline points="${afrLine}" class="dx-afr"/>${dots}
      <text x="${L}" y="${AH-2}" class="dx-axis">AFR ở tải lớn (vạch đỏ: giới hạn nghèo xăng)</text></svg>
    <details class="dx-table"><summary>Xem số đo từng mốc</summary><table><thead><tr><th>Vòng/phút</th>${changed?'<th>Trước</th>':''}<th>${changed?'Sau':'Công suất'}</th><th>AFR</th></tr></thead><tbody>${rows}</tbody></table></details></figure>`;
}

/** The ticket on the lift: the vehicle and its plate; the goal once named, the budget, then the build sheet. */
function ticketCard(t,x){
  const n=t.needs||{},M=mods(x),goal=n.goal_name?`${n.goal_emoji||''} ${n.goal_name}`:'';
  const build=n.build?`<p class="small dx-build">${n.build.map(m=>`<span class="dx-chip${fitted(t,m)?' on':''}">${x.esc(M[m]?.emoji||'')} ${x.esc(M[m]?.name||m)}</span>`).join('')}</p>
    <p class="small">Phụ tùng xưởng ứng ${x.fmt(n.cost||0)} xu, trừ khi giao xe.</p>`:`<p class="small">Ngân sách phụ tùng ${x.fmt(n.budget||0)} xu. ${goal?'Lên bảng độ theo thứ tự ưu tiên của mục tiêu.':'Chưa chốt mục tiêu: nghe khách nói chạy ở đâu.'}</p>`;
  return `<article class="sl-ticket">${withArt(`<small>Phiếu ${x.esc(n.tag)} · biển ${x.esc(n.plate)}</small>
    <h3><span aria-hidden="true">${n.kind==='bike'?'🏍️':'🚗'}</span> ${x.esc(n.vehicle)} màu ${x.esc(n.color)}</h3>
    ${goal?`<p class="dx-goal">${x.esc(goal)}</p>`:''}${build}`,vehicleArt(t,x))}</article>`;
}

function legalLine(x){
  const l=data(x).legal||{};
  return l.warn?`<p class="small dx-legal" role="status">⚖️ Phường đã nhắc nhở xưởng ${x.esc(l.warn)} lần (nộp ${x.fmt(l.fined||0)} xu). Lần nhắc thứ ba, đoàn kiểm tra ghé xưởng.</p>`:'';
}

function slip(t,x){
  const st=current(t);
  if(!st)return `<p class="sl-finished" role="status">✓ Đã giao xe · chất lượng ${x.esc(t.quality)}% · tiền công ${x.fmt(t.paid||0)} xu.</p>`;
  return stepCard(x,st,{at:t.at,total:stepsOf(t).length,quality:t.quality??100,cmd:'dx_step',payload:{task:t.id},key:`${t.id}-${st.id}`});
}

export default {
  id:'tuning',css:true,
  next(t,x){return x.esc(!t.known?ASK:current(t)?.title||'Đã giao xe');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'dx_intro','🔧'));
    if(!t.known)return wrap(top(x)+askCard(x,t,ASK)+tail(x)+notebook(x));
    return wrap(top(x)+person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+ticketCard(t,x)+dynoChart(t.needs?.dyno,x)+slip(t,x)+
      (t.lines?.length?`<p class="sl-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+notebook(x)+tail(x));
  },
  // Compact layout: the notebook folds; the full layout keeps it open.
  idle(x){return wrap(top(x)+tail(x)+(clean()?notebook(x):`<h3 class="sl-rules-h">📒 Sổ tay xưởng Tư Pít-tông</h3>${rulesList(x)}`));},
  input(el,x){return kitInput(el,x);},
  meters(root,x){inboxTick(root,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'slip tuning',eyebrow:'Xưởng độ xe Tư Pít-tông',title:'Sổ tay của xưởng',body:rulesList(x)}):'';},
  actions:{...kitActions,...slipActions},
  dock:[['car:notes','book','Sổ tay của xưởng','Bảng độ, luật khí thải, tiếng ồn, đèn, biển số, dyno'],['car:intro','question','Giới thiệu nghề','Nhanh mà phải dừng được']],
};
