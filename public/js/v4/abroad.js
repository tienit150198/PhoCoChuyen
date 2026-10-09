/** ✈️ Du học and 🌏 Làm việc ở nước ngoài (game/abroad.py → state.journey.abroad, content.journey.abroad). Loaded lazily
 * by app.js (L.abroad), opened with data-action="abroad" (data-tab study | work): the menu, the town's ✈️ door at the
 * airport, the journey list and the job card. Two tabs, one card each:
 *   study  the course running (today's lesson: a scene, one question, three answers), the degrees held, the four schools;
 *   work   the contract running (days, pay, the way home), else: pick the hired job that sends you, then a city.
 * Every rule and price is the server's; buttons send jr_abroad_* (v4Cmd asks first where money or a trip is at stake). */
import {icon,escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const act=(label,action,data={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${disabled?' disabled':''}>${label}</button>`;
const ask=(label,op,payload,question,style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="v4Cmd"${attrs({op,payload:JSON.stringify(payload),confirm:question})}${disabled?' disabled':''}>${label}</button>`;
const head=(title,sub='',eyebrow='')=>`<header class="sheet-head"><div class="grow">${eyebrow?`<span class="eyebrow">${eyebrow}</span>`:''}<h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const place=(api,cid)=>{const m=api.content.catalogue?.find(x=>x.id===cid);return m?(m.place||m.short):cid;};

export const ACTIONS=new Set(['abroad','abTab','abJob','abLesson']);

function tabs(tab){
  const row=[['study','✈️ Du học'],['work','🌏 Đi làm nước ngoài']];
  return `<nav class="pill-tabs ab-tabs" role="tablist">${row.map(([id,label])=>`<button role="tab" type="button" aria-selected="${id===tab}" class="${id===tab?'active':''}" data-action="abTab" data-tab="${id}">${label}</button>`).join('')}</nav>`;
}

/* ------------------------------------------------------------------ ✈️ Du học */
function lessonCard(env,A,K){
  const {ui}=env,st=A.study,d=K.dests.find(x=>x.id===st.p),pr=K.programs[st.p];
  const dots=`<span class="ab-dots" aria-label="Buổi ${st.n}/${st.of}">${Array.from({length:st.of},(_,i)=>`<i class="${i<st.n?'on':''}"></i>`).join('')}</span>`;
  const last=ui.abLast?`<p class="ab-last ${ui.abLast.ok?'good':''}">${esc(ui.abLast.text)}</p>`:'';
  const body=st.lesson?`<p class="ab-scene">${esc(st.lesson.scene)}</p><p class="ab-q">${esc(st.lesson.q)}</p><div class="ab-opts">${st.lesson.options.map((o,i)=>act(esc(o),'abLesson',{option:i},'ab-opt')).join('')}</div>`
    :ui.abLast?'':`<p class="ab-wait">✅ Hôm nay học rồi. Khép ca ở bất kỳ đâu để qua ngày mới, rồi học buổi ${st.n+1}.</p>`;
  return `<article class="ab-card ab-now"><p class="ab-eyebrow">${d.flag} ${esc(pr.school)} · ${esc(d.city)} ${dots}</p><h3>${esc(pr.course)}</h3>${last}${body}
    ${ask('Thôi học','jr_abroad_drop',{},'Thôi học? Trường hoàn một nửa học phí của các buổi chưa học.','ghost small')}</article>`;
}
function studyPage(env,A,K){
  const st=A.study,held=new Set(A.deg.map(x=>x.id));
  const degs=A.deg.length?`<div class="ab-degs">${A.deg.map(x=>{const d=K.dests.find(y=>y.id===x.id),pr=K.programs[x.id];return d&&pr?`<span class="ab-deg">🎓 ${d.flag} ${esc(pr.degree)} <small>${esc(K.grades[x.g]||'')}</small></span>`:'';}).join('')}</div>`:'';
  const perk=`<p class="ab-perk">🎓 Có bằng du học: lương mọi việc làm thuê <b>+${K.deg_pct[1]}%</b> (2 bằng +${K.deg_pct[2]}%, từ 3 bằng +${K.deg_pct[3]}%), lên chức cần <b>ít hơn ${K.good_cut}%</b> ngày tốt, và tính như chứng chỉ khi xét bậc 3.</p>`;
  const cards=K.dests.map(d=>{
    const pr=K.programs[d.id];if(!pr)return '';
    const btn=held.has(d.id)?'<span class="tag green">✓ Đã tốt nghiệp</span>'
      :st?(st.p===d.id?'<span class="tag">Đang học</span>':'<small class="muted">Học xong khóa đang học đã</small>')
      :ask(`Nhập học · ${fmt(pr.fee)} xu`,'jr_abroad_enrol',{program:d.id},`Nhập học ${pr.school} (${d.city})? Học phí ${fmt(pr.fee)} xu, ${pr.lessons} buổi, mỗi ngày sống học 1 buổi. Trả lời đúng hết cả ${pr.lessons} câu được học bổng ${K.scholar}% học phí.`,'primary small');
    return `<article class="ab-card"><p class="ab-eyebrow">${d.flag} ${esc(d.name)} · ${esc(d.city)}</p><h3>${esc(pr.course)}</h3><p class="small muted">${esc(pr.school)} · ${pr.lessons} buổi · ${fmt(pr.fee)} xu</p>${btn}</article>`;
  }).join('');
  const done=!st&&env.ui.abLast?`<p class="ab-last ${env.ui.abLast.ok?'good':''}">${esc(env.ui.abLast.text)}</p>`:'';   // the last lesson's line (and the degree) once the course is over
  return `${done}${st?lessonCard(env,A,K):''}${degs}${perk}<div class="ab-list">${cards}</div>`;
}

/* ------------------------------------------------------------------ 🌏 Làm việc ở nước ngoài */
function workNow(env,A,K){
  const {api}=env,w=A.work,d=K.dests.find(x=>x.id===w.to),where=place(api,w.career);
  const dots=`<span class="ab-dots">${Array.from({length:w.need},(_,i)=>`<i class="${i<w.n?'on':''}"></i>`).join('')}</span>`;
  if(w.shop){const sh=K.shop?.[w.to]||{};   // 👗 Chị Vy's partner shop (#306)
    return `<article class="ab-card ab-now"><p class="ab-eyebrow">${d.flag} ${esc(sh.name||where)} · ${esc(sh.area||d.city)} ${dots}</p><h3>Ngày ${w.n}/${w.need} · hoa hồng +${w.pct}%</h3>
    <p class="small">Khách ${esc(d.city)} nói size kiểu ${esc(d.name)}: xem 📏 ở quầy. Mỗi ngày có khách là một ngày ở ${esc(d.city)}.</p>
    ${act(`Vào tiệm ${icon('arrow',14)}`,'choose',{career:w.career},'primary')}
    ${ask('🏠 Về nước sớm','jr_abroad_home',{},'Về nước sớm? Hoa hồng những ngày đã làm vẫn là của tiệm.','ghost small')}</article>`;}
  return `<article class="ab-card ab-now"><p class="ab-eyebrow">${d.flag} Chi nhánh ${esc(d.city)} · ${esc(where)} ${dots}</p><h3>Ngày ${w.n}/${w.need} · lương +${w.pct}%</h3>
    <p class="small">Mỗi ngày làm ở ${esc(where)} là một ngày ở ${esc(d.city)}, kèm thư nhà gửi sang. Các nơi làm khác tạm nghỉ tới lúc bạn về.</p>
    <p class="small muted">Hết hợp đồng: công ty hoàn ${fmt(w.fee)} xu tiền vé, sếp ghi nhận +${K.bonus} ngày tốt để lên chức.</p>
    ${act(`Làm tiếp ở ${esc(where)} ${icon('arrow',14)}`,'choose',{career:w.career},'primary')}
    ${ask('🏠 Về nước sớm','jr_abroad_home',{},'Về nước sớm? Lương những ngày đã làm vẫn là của bạn, nhưng không được hoàn tiền vé.','ghost small')}</article>`;
}
/** 👗 Tiệm Áo Chỉ Mây's partner shops abroad (#306): not a hired job, Chị Vy sends you and pays the ticket. */
function shopPage(env,A,K,J){
  const {api}=env,S=A.shop,shops=K.shop;if(!S||!shops)return '';
  const open=Object.entries(api.state.careers||{}).find(([,c])=>c?.open);
  const rest=A.rest_until>J.life_day?`Vừa về nước, đi tiếp được từ Ngày ${A.rest_until}.`:'';
  const why=S.why||rest||(open?`Khép ca ở ${place(api,open[0])} trước đã.`:'');
  const cards=K.dests.map(d=>{const sh=shops[d.id];if(!sh)return '';
    return `<article class="ab-card"><p class="ab-eyebrow">${d.flag} ${esc(sh.name)} · ${esc(sh.area)}</p><h3>${sh.days} ngày · hoa hồng +${sh.pct}%</h3>
      <p class="small muted">${esc(sh.style)}</p>
      ${ask('Lên đường · Chị Vy bao vé','jr_abroad_work',{to:d.id,career:S.career},`Sang ${d.city} đứng tiệm ${sh.name} ${sh.days} ngày? Hoa hồng +${sh.pct}% doanh thu mỗi ngày, Chị Vy bao vé. Khách bên đó nói size kiểu ${d.name}. Trong lúc đi, các nơi làm khác tạm nghỉ.`,'primary small',!!why)}</article>`;}).join('');
  return `<h3 class="ab-sub">👗 Tiệm Áo Chỉ Mây ở nước ngoài</h3>${why?`<p class="ab-why">🔒 ${esc(why)}</p>`:''}<div class="ab-list">${cards}</div>`;
}
function workPage(env,A,K,J){
  const {api,ui}=env;
  if(A.work)return workNow(env,A,K);
  const jobs=A.jobs||[];
  const intro=`<p class="ab-perk">🌏 Công ty cử bạn sang chi nhánh nước ngoài vài ngày làm việc, <b>lương cao hơn</b>. Vé và visa trả trước, <b>hết hợp đồng được hoàn lại</b>.</p>`;
  if(!jobs.length)return intro+`<p class="ab-wait">💼 Cần đang làm thuê ở một nơi (ví dụ giao hàng, nhà thuốc, văn phòng) và đã hết thử việc thì công ty mới cử đi.</p>`+shopPage(env,A,K,J);
  const pick=jobs.find(x=>x.career===ui.abJob)||jobs.find(x=>!x.why)||jobs[0];
  const chips=jobs.length>1?`<div class="ab-jobs" role="group" aria-label="Nơi cử bạn đi">${jobs.map(x=>`<button type="button" class="ab-job${x===pick?' on':''}" data-action="abJob" data-career="${esc(x.career)}" aria-pressed="${x===pick}">${esc(place(api,x.career))}</button>`).join('')}</div>`:'';
  const open=Object.entries(api.state.careers||{}).find(([,c])=>c?.open);
  const rest=A.rest_until>J.life_day?`Vừa về nước, ở nhà ít hôm đã: đi tiếp được từ Ngày ${A.rest_until}.`:'';
  const why=pick.why||rest||(open?`Khép ca ở ${place(api,open[0])} trước rồi hẵng lên đường.`:'');
  const cards=K.dests.map(d=>{
    const w=K.work[d.id];if(!w)return '';
    const pay=Math.round(pick.pay*(100+w.pct)/100);
    return `<article class="ab-card"><p class="ab-eyebrow">${d.flag} ${esc(d.name)} · ${esc(d.city)}</p><h3>${w.days} ngày · lương +${w.pct}%</h3>
      <p class="small">≈ <b>${fmt(pay)} xu/ngày</b> <span class="muted">(ở nhà ${fmt(pick.pay)} xu)</span></p><p class="small muted">Vé & visa ${fmt(w.fee)} xu · hoàn lại khi hết hợp đồng</p>
      ${ask(`Lên đường · ${fmt(w.fee)} xu`,'jr_abroad_work',{to:d.id,career:pick.career},`Sang ${d.city} làm ${w.days} ngày cho ${place(api,pick.career)}, lương +${w.pct}%? Trả trước ${fmt(w.fee)} xu vé & visa, hết hợp đồng công ty hoàn lại. Trong lúc đi, các nơi làm khác tạm nghỉ.`,'primary small',!!why)}</article>`;
  }).join('');
  return `${intro}${chips}<p class="small">💼 Nơi cử đi: <b>${esc(place(api,pick.career))}</b> · ${esc(pick.title)}</p>${why?`<p class="ab-why">🔒 ${esc(why)}</p>`:''}<div class="ab-list">${cards}</div>${shopPage(env,A,K,J)}`;
}

export function abroadView(env){
  const {api,ui}=env,J=api.state.journey,A=J?.abroad,K=api.content.journey?.abroad;
  const title='✈️ Du học & 🌏 Đi làm nước ngoài';
  if(!J?.story||!A||!K)return head(title)+`<div class="sheet-body"><p class="muted">Du học và đi làm nước ngoài có trong hành trình.</p></div>`;
  const tab=ui.abTab==='work'?'work':'study';
  return head(title,'','SÂN BAY · TRUNG TÂM DU HỌC')+`<div class="sheet-body ab-body">${tabs(tab)}${tab==='work'?workPage(env,A,K,J):studyPage(env,A,K)}</div>`;
}

export async function abroadAction(action,data,el,env){
  if(!ACTIONS.has(action))return false;
  const {ui,cmd,openSheet,renderSheet}=env;
  if(action==='abroad'){if(data?.tab)ui.abTab=data.tab;ui.abLast=null;openSheet('abroad');return true;}
  if(action==='abTab'){ui.abTab=data.tab;ui.abLast=null;renderSheet();return true;}
  if(action==='abJob'){ui.abJob=data.career;renderSheet();return true;}
  if(action==='abLesson'){
    const r=await cmd('jr_abroad_lesson',{option:Number(data.option)},{quiet:true});
    if(r)ui.abLast={text:r.message,ok:!!r.abroad?.right||!!r.celebrate};
    renderSheet();return true;
  }
  return false;
}
