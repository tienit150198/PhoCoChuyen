/** Nhân viên trực tổng đài cứu hộ — a day shift at Tổng đài Cứu hộ phường Mây (server: game/careers/rescue.py).
 * The board at the start of the shift (radio each unit, mark the one out of service), the calls (the script: where,
 * what, how many, what danger, a number to call back; finding the place, calming a caller who panics, checking a
 * doubtful call), the decision (send the right teams at the right priority, or send the call where it belongs, in a
 * tone of your choosing), the safe instructions while help comes, and staying on the line; the rain-season queue
 * (several lines at once). The awkward people of the line answer through the air crew's encounter card (air_kit.js
 * oddCard); the end-of-shift log is written from what really happened.
 * The server decides everything; hints show the next step, never which way a decision should go. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,act,pane,introCard,deskCard,dayBar,askCard,bottom,kitActions,tip,clean,few} from './street_kit.js';
import {oddCard,restCard,record,ACTIONS as oddActions} from './air_kit.js';

const ODD_CFG={odd:'cu_odd',rest:'cu_rest',kinds:{charm:'Lời mời khó từ chối',harass:'Quấy rối',demand:'Yêu cầu oái oăm',corner:'Làm tắt',bargain:'Mặc cả với trung tâm'},
  rest_to:[['self','Gửi chị Thảo'],['company','Nhờ công đoàn']]};
const pay=t=>({task:t.id});
const C=(x,k)=>cc(x)[k]||{};
const PR=(x,k)=>C(x,'prio')[k]||['⚪',k,''];
const UN=(x,k)=>C(x,'units')[k]||['•',k];
const IN=(x,k)=>C(x,'instr')[k]||['•',k];
const clock=s=>`${Math.floor((s||0)/60)}:${String((s||0)%60).padStart(2,'0')}`;
/** The order turns with the task id: the right card is not always on top. */
function turn(t,rows){const k=[...t.id].reduce((n,ch)=>n+ch.charCodeAt(0),0)%Math.max(1,rows.length);return [...rows.slice(k),...rows.slice(0,k)];}

/* ------------------------------------------------------------ shared pieces */
function groundCard(x){
  const cd=data(x).odd?.conduct||{};if(!cd.ground)return '';
  return `<section class="cu-ground" role="status"><h3>⚖️ ${cd.demoted?'Bị hạ bậc, tạm đình chỉ trực hôm nay':'Tạm đình chỉ trực hôm nay'}</h3><p class="small">Mai lên phòng Điều phối trình bày. Hôm nay tan ca sớm.</p>${x.button('Tan ca','end',{},'primary')}</section>`;
}
function lineStep(x){
  const o=data(x).odd||{};
  if(o.ev)return {ok:null,label:`Trả lời: ${o.ev.title}`,go:{sel:'.air-odd',label:'💬 Trả lời'},pulse:''};
  if(o.conduct?.ground)return {ok:null,label:'Tạm đình chỉ trực: tan ca',go:{sel:'.cu-ground',label:'⚖️ Tan ca'},pulse:''};
  return null;
}
function learnNote(x){
  const l=data(x).learn;if(!l?.on)return '';
  if(clean())return `<p class="cu-learn">🎧 ${Math.min(l.n+1,l.of)}/${l.of}</p>${tip(`Chị Thảo bấm nút nghe kèm: cuộc gọi ${Math.min(l.n+1,l.of)}/${l.of}. Sai gì chị nhắc trước.`,'Học nghề','p')}`;
  return `<p class="cu-learn">🎧 Chị Thảo bấm nút nghe kèm: cuộc gọi ${Math.min(l.n+1,l.of)}/${l.of}. Sai gì chị nhắc trước.</p>`;
}
const STATE={ready:['✅','sẵn sàng'],away:['⏳','đang đi'],down:['⛔','tạm ngưng']};
function boardChips(x,pick=null,t=null){
  const rows=data(x).board||[];
  return `<div class="cu-board">${rows.map(u=>{const [e,s]=STATE[u.state]||STATE.ready;
    const inner=`<span class="cu-unit-e" aria-hidden="true">${x.esc(u.emoji)}</span><b>${x.esc(u.name)}</b><small>${e} ${s}</small>`;
    if(!pick)return `<div class="cu-unit st-${x.esc(u.state)}">${inner}</div>`;
    const on=pick.includes(u.id);
    return act(x,inner,'team',{task:t.id,unit:u.id},`cu-unit st-${u.state}${on?' on':''}`,` aria-pressed="${on}"`);}).join('')}</div>`;
}

/* ------------------------------------------------------------ the board at the start of the shift */
/** A unit in a word or two on the clean layout ("Đội chữa cháy và cứu nạn" → "Cứu hỏa"). */
const UNIT_WORD={'Đội chữa cháy và cứu nạn':'Cứu hỏa','Xe cấp cứu':'Cấp cứu','Xuồng cứu hộ':'Xuồng','Thợ cứu hộ thang máy':'Thang máy','Công an phường':'Công an'};
const unitWord=u=>clean()?(UNIT_WORD[u.name]||few(u.name,2)):u.name;
function shiftPanel(t,x){
  const units=(t.needs||{}).units||[],down=x.ui.down?.[t.id];
  const rows=units.map(u=>`<li class="${u.note?'read':''}">${u.note?`<p>${x.esc(u.note)}</p>`
    :x.cmd(`<span>${x.esc(u.emoji)} <b>${x.esc(unitWord(u))}</b></span><small>📻${clean()?'':' Gọi bộ đàm'}</small>`,'cu_radio',{task:t.id,unit:u.id},'cu-radio').replace('<button ',`<button aria-label="Gọi bộ đàm: ${x.esc(u.name)}" `)}</li>`).join('');
  const pick=[...units.map(u=>act(x,`${x.esc(u.emoji)} ${x.esc(unitWord(u))}`,'pickDown',{task:t.id,unit:u.id},`cu-down${down===u.id?' on':''}`,` aria-pressed="${down===u.id}"`)),
    act(x,'✅ Không đội nào','pickDown',{task:t.id,unit:'none'},`cu-down${down==='none'?' on':''}`,` aria-pressed="${down==='none'}"`)].join('');
  return `<section class="card cu-shift"><h4>📻 ${clean()?'Bộ đàm':'Gọi bộ đàm từng đội'}</h4><ul class="cu-notes">${rows}</ul></section>
    ${clean()?`<section class="card cu-mark">${pane(x,`down-${t.id}`,'⛔ <b>Đội tạm ngưng</b>',`<div class="cu-downs">${pick}</div>`,!units.some(u=>!u.note)||!!down)}</section>`
      :`<section class="card cu-mark"><h4>⛔ Đánh dấu đội tạm ngưng</h4><div class="cu-downs">${pick}</div></section>`}`;
}
function shiftSteps(t,x){
  const units=(t.needs||{}).units||[],next=units.find(u=>!u.note),down=x.ui.down?.[t.id];
  return [{ok:!next||null,label:'Gọi bộ đàm từng đội',note:`${units.filter(u=>u.note).length}/${units.length}`,
    go:next?{cmd:'cu_radio',payload:{task:t.id,unit:next.id},label:`📻 Gọi ${x.esc(unitWord(next).toLowerCase())}`}:null},
    {ok:down?true:null,label:'Đánh dấu đội tạm ngưng',go:{sel:'.cu-mark',label:'⛔ Đánh dấu đội tạm ngưng'},pulse:''}];
}

/* ------------------------------------------------------------ a call */
function callerCard(t,x){
  const n=t.needs||{};
  const tags=[`<span class="tag blue">☎️ Đường dây ${x.esc(n.line)}</span>`,`<span class="tag">⏱️ ${clock(t.secs)}</span>`,
    n.panicked?'<span class="tag danger">😰 Người gọi đang hoảng</span>':'',n.drop?'<span class="tag amber">📵 Máy đã cúp</span>':'',
    n.located?'<span class="tag green">📍 Đã rõ chỗ</span>':(t.asked||[]).includes('where')?'<span class="tag amber">📍 Chưa rõ chỗ</span>':''].join('');
  return `<article class="card cu-caller"><div class="row"><span class="cu-av" aria-hidden="true">${x.esc(n.emoji||'📞')}</span><div class="grow">
    <h3>${x.esc(n.label||'')}</h3><p class="cu-open">${x.esc(n.opening||'')}</p></div></div><div class="cu-tags">${tags}</div>
    ${n.addr?`<p class="cu-addr">📍 ${x.esc(n.addr)}</p>`:''}</article>`;
}
function scriptPanel(t,x){
  const n=t.needs||{},ans=n.answers||{},qs=C(x,'questions'),ids=cc(x).q_ids||[];
  const rows=ids.map(q=>{const [e,label]=qs[q]||['•',q];
    return ans[q]!=null?`<li class="seen"><small>${x.esc(e)} ${x.esc(label)}</small><p>${x.esc(ans[q])}</p></li>`
      :`<li>${x.cmd(`${x.esc(e)} ${x.esc(label)}`,'cu_ask',{task:t.id,q},'ghost cu-q')}</li>`;}).join('');
  return `<section class="card cu-script"><h4>📋 Kịch bản cuộc gọi</h4><ul class="cu-list">${rows}</ul></section>`;
}
function helpPanes(t,x){
  const n=t.needs||{},open=t.stage==='open',out=[];
  const opt=(cmd,payload,e,label)=>x.cmd(`<span class="sk-opt-label">${x.esc(e)} ${x.esc(label)}</span>`,cmd,payload,'sk-opt');
  const calm=C(x,'calm'),used=n.calmed||[];
  const calmRows=Object.entries(calm).filter(([k])=>!used.includes(k)).map(([k,[e,l]])=>opt('cu_calm',{task:t.id,how:k},e,l)).join('');
  if(calmRows)out.push(pane(x,`calm-${t.id}`,'🌬️ Trấn an người gọi…',`<div class="sk-opts">${calmRows}</div>`,!!n.panicked,'cu-calm'));
  if(open&&(t.asked||[]).includes('where')&&!n.located){
    const f=C(x,'find'),rows=Object.entries(f).filter(([k])=>!(n.found||[]).includes(k)).map(([k,[e,l]])=>opt('cu_find',{task:t.id,how:k},e,l)).join('');
    if(rows)out.push(pane(x,`find-${t.id}`,'🗺️ Tìm chỗ người gọi…',`<div class="sk-opts">${rows}</div>`,true,'cu-find'));
  }
  if(open){
    const v=C(x,'verify'),rows=Object.entries(v).filter(([k])=>!(n.checked||[]).includes(k)).map(([k,[e,l]])=>opt('cu_verify',{task:t.id,how:k},e,l)).join('');
    if(rows)out.push(pane(x,`check-${t.id}`,'🔎 Kiểm tra cuộc gọi…',`<div class="sk-opts">${rows}</div>`,!!n.drop,'cu-check'));
  }
  return out.join('');
}
function decidePanel(t,x){
  const ui=x.ui,prio=(ui.prio??={})[t.id],teams=(ui.teams??={})[t.id]||[],to=(ui.to??={})[t.id],tone=(ui.tone??={})[t.id];
  const segs=(cc(x).send_prio||[]).map(p=>{const [e,name,why]=PR(x,p);return act(x,`${e} ${x.esc(name)}<small>${x.esc(why)}</small>`,'prio',{task:t.id,p},`cu-prio p-${p}${prio===p?' on':''}`,` aria-pressed="${prio===p}"`);}).join('');
  const send=`<p class="small muted">Mức ưu tiên (Bảng ưu tiên Mây, luật của trò chơi):</p><div class="cu-prios">${segs}</div>
    <p class="small muted">Đội cần gửi:</p>${boardChips(x,teams,t)}${x.cmd('🚨 GỬI ĐỘI','cu_send',{task:t.id,prio:prio||'',teams},'primary full cu-go',!prio||!teams.length)}`;
  const rd=C(x,'redirect'),tn=C(x,'tones');
  const places=turn(t,Object.entries(rd)).map(([k,[e,l]])=>act(x,`${x.esc(e)} ${x.esc(l)}`,'to',{task:t.id,k},`cu-to${to===k?' on':''}`,` aria-pressed="${to===k}"`)).join('');
  const tones=Object.entries(tn).map(([k,[e,l]])=>act(x,`${x.esc(e)} ${x.esc(l)}`,'tone',{task:t.id,k},`cu-tone${tone===k?' on':''}`,` aria-pressed="${tone===k}"`)).join('');
  const redirect=`<p class="small muted">Không ai cần xe? Chuyển tới đâu:</p><div class="cu-tos">${places}</div><p class="small muted">Giọng nói:</p><div class="cu-tones">${tones}</div>
    ${x.cmd('↪️ CHUYỂN ĐÚNG NƠI','cu_redirect',{task:t.id,to:to||'',tone:tone||''},'full cu-go',!to||!tone)}`;
  return `<section class="card cu-decide"><h4>⚖️ Quyết</h4>${pane(x,`send-${t.id}`,'🚒 Gửi đội…',send,false,'cu-send')}${pane(x,`redir-${t.id}`,'↪️ Không điều xe, chuyển đúng nơi…',redirect,false,'cu-redir')}</section>`;
}
function afterPanel(t,x){
  const n=t.needs||{},told=t.told||[];
  const head=t.teams?.length?`<p class="tag green cu-done">${x.esc(PR(x,t.prio)[0])} Đã gửi: ${t.teams.map(u=>x.esc(UN(x,u)[1])).join(', ')}</p>`
    :`<p class="tag blue cu-done">↪️ ${x.esc((C(x,'redirect')[t.to]||['',''])[1])}</p>`;
  const cards=turn(t,n.cards||[]).map(k=>{const [e,l]=IN(x,k);
    return told.includes(k)?`<span class="tag green cu-told">✓ ${x.esc(l)}</span>`:x.cmd(`<span class="sk-opt-label">${x.esc(e)} Đọc: “${x.esc(l)}”</span>`,'cu_tell',{task:t.id,card:k},'sk-opt cu-card');}).join('');
  const instr=(n.cards||[]).length?`<section class="card cu-instr"><h4>🗣️ Hướng dẫn an toàn trong lúc chờ</h4><p class="small muted">Chọn điều người gọi nên làm. Có thẻ nghe thì hợp lý mà nguy hiểm.</p><div class="sk-opts">${cards}</div></section>`:'';
  const close=`<section class="card cu-close"><h4>☎️ Kết thúc</h4><div class="sk-opts">
    ${x.cmd('<span class="sk-opt-label">☎️ Giữ máy tới khi đội tới</span><small>nói chuyện, dặn thêm, nghe tiếng còi xe</small>','cu_close',{task:t.id,stay:true},'sk-opt')}
    ${x.cmd('<span class="sk-opt-label">📴 Kết thúc cuộc gọi</span><small>trả đường dây cho cuộc kế</small>','cu_close',{task:t.id,stay:false},'sk-opt')}</div></section>`;
  return head+instr+close;
}
function callSteps(t,x){
  const n=t.needs||{},asked=t.asked||[],qs=C(x,'questions'),rows=[];
  if(n.panicked)rows.push({ok:null,label:'Trấn an người gọi',go:{sel:'.cu-calm',label:'🌬️ Trấn an'},pulse:''});
  if(n.drop)rows.push({ok:null,label:'Gọi lại số vừa gọi',go:{cmd:'cu_verify',payload:{task:t.id,how:'recall'},label:'↩️ Gọi lại'}});
  const q=(id,label)=>rows.push({ok:asked.includes(id)||null,label,go:asked.includes(id)?null:{cmd:'cu_ask',payload:{task:t.id,q:id},label:`${x.esc((qs[id]||['•'])[0])} ${x.esc(label)}`}});
  q('where','Hỏi địa chỉ');
  if(asked.includes('where')&&!n.located&&t.stage==='open')rows.push({ok:null,label:'Tìm cho rõ chỗ',go:{sel:'.cu-find',label:'🗺️ Tìm chỗ'},pulse:''});
  q('what','Hỏi chuyện gì');
  q('who','Hỏi mấy người, ai bị thương');
  q('danger','Hỏi nguy hiểm');
  q('phone','Xin số gọi lại');
  if(t.stage==='open')rows.push({ok:null,label:'Gửi đội hoặc chuyển đúng nơi',go:{sel:'.cu-decide',label:'⚖️ Quyết'},pulse:''});
  else{
    if((n.cards||[]).length)rows.push({ok:(t.told||[]).length?true:null,label:'Đọc hướng dẫn an toàn',go:{sel:'.cu-instr',label:'🗣️ Đọc hướng dẫn'},pulse:''});
  }
  return rows;
}

/* ------------------------------------------------------------ the rain-season queue */
function queuePanel(t,x){
  const lines=(t.needs||{}).lines||[],order=cc(x).prio_order||[];
  const cards=lines.map((p,i)=>{const got=(t.colors||{})[String(i)];
    const heard=p.ask?`<p class="cu-heard">👂 ${x.esc(p.ask)}</p>`:x.cmd('👂 Nghe máy','cu_listen',{task:t.id,i},'ghost small');
    const seg=order.map(c=>{const [e,name]=PR(x,c);return x.cmd(`${e} ${x.esc(name)}`,'cu_color',{task:t.id,i,prio:c},`cu-pc p-${c}${got===c?' on':''}`);}).join('');
    return `<article class="card cu-line${got?` got p-${got}`:''}"><div class="row"><span class="cu-av" aria-hidden="true">${x.esc(p.emoji)}</span><div class="grow"><b>${x.esc(p.who)}</b><p class="small">${x.esc(p.text)}</p></div></div>
      <div class="cu-qs">${heard}</div><div class="cu-pcs" role="group" aria-label="Mức ưu tiên">${seg}</div></article>`;}).join('');
  const scale=pane(x,'prio-scale','🚦 Bảng ưu tiên Mây',`<ul class="cu-scale">${order.map(c=>{const [e,name,why]=PR(x,c);return `<li>${e} <b>${x.esc(name)}</b> · ${x.esc(why)}</li>`;}).join('')}</ul><p class="small muted">Xếp theo nguy hiểm tính mạng, không theo tiếng la. Luật của trò chơi.</p>`,false,'cu-scale-pane');
  return `${scale}<div class="cu-queue">${cards}</div>`;
}
function queueSteps(t,x){
  const lines=(t.needs||{}).lines||[];
  return lines.map((p,i)=>({ok:(t.colors||{})[String(i)]?true:null,label:`Ưu tiên: ${p.who}`,go:{sel:`.cu-line:nth-child(${i+1})`,label:`🚦 ${x.esc(p.who)}`},pulse:''}));
}

/* ------------------------------------------------------------ the end-of-shift log */
function reportCard(x){
  const td=data(x).today||{},rows=td.facts||[];
  if(!rows.length)return '';
  if(td.report)return `<p class="tag ${td.report==='ok'?'green':td.report==='miss'?'amber':'danger'} cu-report-done">📒 ${td.report==='ok'?'Đã ghi sổ nhật ký.':td.report==='miss'?'Đã ghi sổ nhật ký (còn thiếu).':'Sổ nhật ký có dòng ghi khống.'}</p>`;
  const pick=(x.ui.report??={})[td.day]||[];
  const lines=rows.map(r=>act(x,`<span>${pick.includes(r.id)?'☑️':'⬜'}</span> ${x.esc(r.text)}`,'reportPick',{id:r.id,day:td.day},`cu-logline${pick.includes(r.id)?' on':''}`,` aria-pressed="${pick.includes(r.id)}"`)).join('');
  return pane(x,`report-${td.day}`,`📒 Ghi sổ nhật ký ca trực · ${rows.length} dòng`,`<p class="small muted">Chọn những gì thật sự đã xảy ra, đủ để ca sau theo dõi.</p><div class="cu-loglines">${lines}</div>${x.cmd('📒 Ghi vào sổ nhật ký','cu_report',{lines:pick},'primary full',!pick.length)}`,true,'cu-report');
}

/* ------------------------------------------------------------ the guide */
function stepsOf(t,x){return ({shift:shiftSteps,call:callSteps,queue:queueSteps}[t.kind]||(()=>[]))(t,x);}
function finalOf(t,x,steps){
  if(t.kind==='shift'){const f=x.ui.down?.[t.id];return {label:'🗺️ KÝ NHẬN CA',go:f?finalGo(steps,'cu_sign',{task:t.id,down:f}):null,ready:!!f,why:'đánh dấu đội tạm ngưng'};}
  if(t.kind==='queue'){const n=(t.needs||{}).lines||[],all=n.length&&n.every((_,i)=>(t.colors||{})[String(i)]);return {label:'📞 NHẤC THEO THỨ TỰ',go:all?finalGo(steps,'cu_sort',pay(t)):null,ready:!!all,why:'xếp ưu tiên cho đủ các máy'};}
  if(t.kind==='call'&&t.stage==='decided')return {label:'☎️ KẾT THÚC',go:{sel:'.cu-close',label:'☎️ Kết thúc'},ready:true};
  return null;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở phòng trực',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  const o=lineStep(x);if(o)return {steps:[o],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'cu_intro',payload:{},label:'📞 Vào ca thôi!'}}],final:null};
  if(t.kind!=='shift'&&!t.known)return {steps:[{ok:null,label:t.kind==='queue'?'Nghe chị Thảo':'Nhấc máy',go:{cmd:'ask',payload:pay(t),label:t.kind==='queue'?'👂 Nghe chị Thảo':'📞 Nhấc máy'}}],final:null,pulse:'.sk-ask'};
  const steps=stepsOf(t,x);
  return {steps,final:finalOf(t,x,steps)};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});
function top(x){return `${introCard(x,'cu_intro','📞')}${deskCard(x,'cu_desk','Chuyện ở phòng trực')}${oddCard(x,ODD_CFG)}${groundCard(x)}`;}

export default {
  id:'rescue',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='shift'?'Rà bảng đội':!t.known?'Nhấc máy':'Làm tiếp';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x),head=top(x);
    if(d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk cu">${hint}${head}${bottom(x,g)}</div>`;
    let main='',side='';
    if(t.kind==='shift'){main=shiftPanel(t,x);side=stepRows(x,g.steps,'Nhận ca',{chip:true});}
    else if(!t.known)main=askCard(x,t,t.kind==='queue'?'👂 Nghe chị Thảo':'📞 Nhấc máy');
    else if(t.kind==='queue'){main=queuePanel(t,x);side=stepRows(x,g.steps,'Các đường dây',{chip:true});}
    else{
      main=`${callerCard(t,x)}${scriptPanel(t,x)}${helpPanes(t,x)}${t.stage==='open'?decidePanel(t,x):afterPanel(t,x)}`;
      side=stepRows(x,g.steps,'Kịch bản',{chip:true});
    }
    return `<div class="career-job sk cu">${hint}${head}${learnNote(x)}${dayBar(x)}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),head=top(x);
    if(d.desk?.ev||d.odd?.ev||!d.intro||x.ui.intro){
      const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở phòng trực',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}
        :d.odd?.ev?{steps:[lineStep(x)],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'cu_intro',payload:{},label:'📞 Vào ca thôi!'}}],final:null};
      return `<div class="career-job sk cu">${hintFor(g,x)}${head}${bottom(x,g)}</div>`;
    }
    const td=d.today||{};
    const tiles=[[td.calls||0,'cuộc gọi'],[td.sent||0,'lần gửi đội'],[td.checked||0,'cuộc đã kiểm tra'],[td.told||0,'hướng dẫn đã đọc']];
    return `<div class="career-job sk cu">${head}${dayBar(x)}<section class="card cu-today"><h4>📞 Ca hôm nay</h4><div class="cu-tiles">${tiles.map(([v,l])=>`<div><b>${x.esc(v)}</b><small>${x.esc(l)}</small></div>`).join('')}</div></section>
      <section class="card cu-boardcard"><h4>🗺️ Bảng đội</h4>${boardChips(x)}</section>
      ${reportCard(x)}<section class="card cu-record"><h4>📁 Hồ sơ của bạn</h4>${record(x)}${restCard(x,ODD_CFG)}</section></div>`;
  },
  tick(root){keepBarAboveFooter(root);},
  actions:{...kitActions,...oddActions,
    async pickDown(d,el,x){(x.ui.down??={})[d.task]=d.unit;x.render();},
    async prio(d,el,x){(x.ui.prio??={})[d.task]=d.p;x.render();},
    async team(d,el,x){const b=((x.ui.teams??={})[d.task]??=[]);const i=b.indexOf(d.unit);if(i>=0)b.splice(i,1);else b.push(d.unit);x.render();},
    async to(d,el,x){(x.ui.to??={})[d.task]=d.k;x.render();},
    async tone(d,el,x){(x.ui.tone??={})[d.task]=d.k;x.render();},
    async reportPick(d,el,x){const b=((x.ui.report??={})[d.day]??=[]);const i=b.indexOf(d.id);if(i>=0)b.splice(i,1);else b.push(d.id);x.render();},
  },
};
