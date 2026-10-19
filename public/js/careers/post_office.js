/** Cánh Thư: read the evidence, record each parcel, then file its handover proof. */
import {data,cc,person,askCard,introCard,kitActions,amountBox,kitInput,notesPage} from './street_kit.js';
import {clean,tip} from '../ui-kit.js';

const current=t=>t.needs?.steps?.[t.at];
const modeName={send:'Gửi đi',collection:'Nhận tại quầy',return:'Hàng hoàn'};
const wrap=body=>`<div class="career-job sk post-office">${body}</div>`;

function tariffBoard(x){
  const c=cc(x);
  return `<section class="post-rates" aria-label="Bảng cước trong game"><h4>Bảng cước · chỉ dùng trong game</h4>
    <p>Giá vùng + 3 xu × số khối 500 g làm tròn lên + dịch vụ + 5 xu nếu cạnh dài trên 60 cm.</p>
    <dl>${(c.zones||[]).map(z=>`<div><dt>${x.esc(z.label)} · tuyến ${x.esc(z.route)}</dt><dd>${x.fmt(z.base)} xu</dd></div>`).join('')}</dl>
    <ul>${(c.services||[]).map(s=>`<li>${x.esc(s.label)} · ${s.id==='stored'||s.id==='return'?'không thu thêm':`+${x.fmt(s.extra)} xu`}</li>`).join('')}</ul>
    ${tip('Cước thuộc bưu điện. Lương theo hợp đồng; thưởng chất lượng 4–9 xu/phiếu.','','p','small')}</section>`;
}

function progress(x){
  const d=data(x),s=d.stats||{};
  return `<details class="post-progress"><summary>Hành trình Cánh Thư · ${s.qualified||0} phiếu đạt chuẩn · ${s.active_days||0} ngày</summary>
    <p class="small">Ngày khép ca có phiếu không sai sót mới được ghi nhận.</p>
    <ul>${(d.progress?.milestones||[]).map(m=>`<li><b>${m.achieved?'✓ ':''}${x.esc(m.label)}</b><span>${Math.min(s.qualified||0,m.jobs)}/${m.jobs} phiếu · ${Math.min(s.active_days||0,m.days)}/${m.days} ngày${m.advanced?` · ${Math.min(s.advanced||0,m.advanced)}/${m.advanced} túi thư cuối tuyến`:''}</span></li>`).join('')}</ul>
    <p class="small">Mốc 4: thư bảo đảm · 10: dễ vỡ và khổ dài · 20: nhận và hoàn · 40: túi nhiều kiện.</p></details>`;
}

function notebook(x){
  return tariffBoard(x)+`<ul class="post-rules">${(cc(x).notebook||[]).map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`;
}

function parcelCard(t,x,st){
  const ps=t.needs.parcels||[],p=ps.find(p=>p.id===st.parcel);
  if(!p)return '';
  const index=ps.indexOf(p);
  return `<article class="post-parcel"><div class="post-stamp" aria-hidden="true">✉</div>
    <small>KIỆN ${index+1}/${ps.length} · ${x.esc(modeName[p.mode]||'Bưu gửi')}</small><h3>${x.esc(p.code)}</h3>
    <p>${x.esc(p.item)}</p><dl><div><dt>Người gửi</dt><dd>${x.esc(p.sender)}</dd></div><div><dt>Người nhận</dt><dd>${x.esc(p.recipient)}</dd></div>
    <div><dt>Vùng</dt><dd>${x.esc(p.zone_label)}</dd></div><div><dt>Kích thước</dt><dd>Cạnh dài ${p.length_cm} cm</dd></div></dl>
    ${ps.length>1?`<ol class="post-batch" aria-label="Túi bưu gửi">${ps.map((a,i)=>`<li class="${i===index?'current':i<index?'done':''}">${i<index?'✓ ':''}${x.esc(a.code)}</li>`).join('')}</ol>`:''}</article>`;
}

function stepCard(t,x){
  const st=current(t);if(!st)return '<p class="post-finished" role="status">✓ Đã lưu đủ chứng từ bưu gửi.</p>';
  const payload={task:t.id,step:st.id};
  const buttons=st.options?`<div class="post-options">${st.options.map(o=>x.cmd(x.esc(o.label),'post_step',{...payload,value:o.id},'post-option')).join('')}</div>`:
    amountBox(x,`post-${t.id}-${st.id}`,0,{min:0,max:10000,label:st.kind==='weight'?'Ghi khối lượng cân thực tế (g)':'Ghi cước đã tính (xu)',
      send:st.kind==='weight'?'Ghi số cân':'Ghi cước vào phiếu',cmd:'post_step',payload,field:'value',unit:st.kind==='weight'?'g':'xu'});
  const isFee=st.kind==='tariff'||st.kind==='service';
  const chosen=st.kind==='tariff'?(cc(x).services||[]).find(s=>s.id===t.work?.[`${st.parcel}.service`]):null;
  return `${parcelCard(t,x,st)}<section class="card post-step" aria-labelledby="post-step-title">
    <p class="post-step-count" role="status">Bước ${t.at+1}/${t.needs.steps.length}</p><progress value="${t.at}" max="${t.needs.steps.length}" aria-label="Tiến trình phiếu"></progress>
    <h3 id="post-step-title">${x.esc(st.title)}</h3><p class="post-evidence">${x.esc(st.evidence)}</p>
    ${chosen?`<p class="small">Dịch vụ đã ghi: <b>${x.esc(chosen.label)}</b></p>`:''}${isFee?tariffBoard(x):''}${buttons}</section>`;
}

export default {
  id:'post_office',css:true,
  next(t,x){return x.esc(!t.known?'Đọc phiếu bưu gửi':current(t)?.title||'Đã lưu chứng từ');},
  job(t,x){
    if(!data(x).intro||x.ui.intro)return wrap(introCard(x,'post_intro','✉️'));
    if(!t.known)return wrap(askCard(x,t,'Đọc phiếu bưu gửi')+progress(x));
    return wrap(person(x,t,`<p class="small">${x.esc(t.opening)}</p>`)+stepCard(t,x)+
      (t.lines?.length?`<p class="post-last" role="status">${x.esc(t.lines.at(-1))}</p>`:'')+
      `<details class="post-notebook"><summary>Bảng quy tắc bưu điện</summary>${notebook(x)}</details>`+progress(x));
  },
  // Compact layout: the tariff and the rules fold like on the work screen (the full layout keeps them open).
  idle(x){return wrap(introCard(x,'post_intro','✉️')+progress(x)+(clean()?`<details class="post-notebook"><summary>Bảng quy tắc bưu điện</summary>${notebook(x)}</details>`:notebook(x)));},
  input(el,x){return kitInput(el,x);},
  page(view,x){return view==='car:notes'?notesPage(x,{cls:'post-office',eyebrow:'Bưu điện Cánh Thư',title:'Bảng cước & bàn giao',body:notebook(x)}):'';},
  actions:{...kitActions,
    async amtSend(d,el,x){
      // Collection and returns have prepaid postage: zero is a meaningful entry.
      const raw=x.ui.amt?.[d.key],value=Number(raw===undefined||raw===''?d.def:raw);
      if(!Number.isInteger(value)||value<0||value>10000){x.toast?.('Nhập số nguyên từ 0 đến 10000.');return;}
      await x.send(d.cmd,{...JSON.parse(d.extra||'{}'),[d.field]:value});
    },
  },
  dock:[['car:notes','book','Bảng cước','Quy tắc và biểu cước trong game'],['car:intro','question','Giới thiệu nghề','Quầy nhận và chia tuyến']],
};
