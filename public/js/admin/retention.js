/** "Giữ chân" (GET /api/admin/stats/section?name=retention, game/admin_retention.py): where and how players
 * drop off. Numbers first, little text, phone first. Aggregates only: no names, session ids or typed text.
 * Imported on demand when the view opens (main.js). */
import {esc,icon,num,dec,pct,dm,hm,ago,bytes,tag} from './ui.js';
import {kpi,card,table} from './stats.js';

export const FUNNEL={today:'Hôm nay',yesterday:'Hôm qua',d7:'7 ngày',d30:'30 ngày'};
const SCREEN={intro:'Màn mở đầu',work:'Cảnh nơi làm',home:'Trang chủ',loading:'Đang tải',job:'Việc của khách',prepare:'Chuẩn bị ngày',summary:'Tổng kết ngày',
  chat:'Trò chuyện',town:'Khu phố',journey:'Hành trình',bank:'Ngân hàng',money:'Tiền của bạn',settings:'Cài đặt',social:'Phố',
  confirmDialog:'Hộp xác nhận',tutGuide:'Hướng dẫn',wnDialog:'Có gì mới',gfDialog:'Quà',stScene:'Cảnh truyện',lfScene:'Cảnh đời',jrScene:'Cảnh hành trình',tour:'Tour hướng dẫn',note:'Ghi chú hướng dẫn'};
const KIND={js:'Lỗi JS',promise:'Promise',asset:'Tệp',api:'API',toast:'Từ chối'};
const ms=v=>v==null?'—':v>=10000?`${dec(v/1000)} s`:`${num(v)} ms`;
const mins=v=>v==null?'—':v<1?`${num(v*60)} giây`:v<120?`${dec(v)} phút`:`${dec(v/60)} giờ`;
const seg=(key,value,options)=>`<div class="seg sm" role="radiogroup">${Object.entries(options).map(([k,l])=>`<button type="button" role="radio" aria-checked="${k===value}" class="${k===value?'on':''}" data-act="retSeg" data-key="${key}" data-value="${k}">${l}</button>`).join('')}</div>`;
function screenLabel(s){
  const [v,p]=String(s).split(' › ');const f=x=>SCREEN[x]||x;
  return esc(p?`${f(v)} › ${f(p)}`:f(v));
}
function stepLabel(t){
  if(t==='—')return '—';
  let m=/^tour:(.+)$/.exec(t);if(m)return `Tour · ${esc(m[1])}`;
  m=/^d1:s(\d+)$/.exec(t);if(m)return `Ngày đầu · ${m[1]} khách`;
  return esc(t);
}
/** Rows {label, n, pct} as compact bars; `fmt` turns a label into HTML. */
function bars(rows,fmt=esc,{tone='',empty='Chưa có số liệu.',limit=8}={}){
  if(!rows?.length)return `<p class="note">${empty}</p>`;
  const max=Math.max(1,...rows.map(r=>r.n));
  return `<ul class="hbars compact ${tone}">${rows.slice(0,limit).map(r=>`<li><span class="hl">${fmt(r.label)}</span><b class="hv">${num(r.n)} <small>${pct(r.pct)}</small></b><span class="track" aria-hidden="true"><i style="width:${Math.max(r.n?2:0,Math.round(100*r.n/max))}%"></i></span></li>`).join('')}</ul>`;
}
/** A retention cell coloured by its value (higher = stronger); '·' while that day is not over. */
function heat(v){
  if(v==null)return '<td class="na" title="Chưa đủ ngày">·</td>';
  const a=Math.min(62,Math.round(v*1.25));
  return `<td class="heat" style="background:color-mix(in srgb,var(--second) ${a}%,transparent)">${dec(v)}</td>`;
}

function kpis(d){
  const s=d.cohort_summary,f=Object.fromEntries(d.funnel.map(p=>[p.key,p])).d7,fs=d.churn.first_session;
  const served=f.steps.find(x=>x.key==='served1');
  return `<div class="kpis k4">
    ${kpi('Quay lại D1',pct(s.d1),`D3 ${pct(s.d3)} · D7 ${pct(s.d7)}`)}
    ${kpi('Phục vụ khách đầu',pct(served?.pct),`${num(f.n)} người mới 7 ngày · ${mins(served?.median_min)}`)}
    ${kpi('Rời sau lượt đầu',pct(fs.pct),`${num(fs.n)}/${num(fs.cohort)} · trung vị ${mins(fs.median_min)}`,{tone:fs.pct>50?'hot':''})}
    ${kpi('Không quay lại',num(d.churn.players),`${d.churn.window.min_days}–${d.churn.window.max_days} ngày · ${num(d.churn.with_leave)} có dấu vết`)}
  </div>`;
}
function cohortCard(d){
  const ks=[1,3,7,14,30];
  const rows=d.cohorts.map(r=>`<tr><td>${dm(r.day)}</td><td>${num(r.n)}</td>${ks.map(k=>heat(r[`d${k}`])).join('')}</tr>`);
  const s=d.cohort_summary;
  const foot=`<tr class="sum"><td>Chung</td><td></td>${ks.map(k=>`<td>${pct(s[`d${k}`])}</td>`).join('')}</tr>`;
  return card('Quay lại theo ngày bắt đầu',`<div class="scroll heat-wrap"><table class="tbl heat-tbl"><thead><tr><th>Ngày</th><th>Người</th>${ks.map(k=>`<th>D${k}</th>`).join('')}</tr></thead><tbody>${foot}${rows.join('')}</tbody></table></div>`,
    {note:'Người bắt đầu chơi trong ngày đó (có thao tác) và % có thao tác lại đúng 1, 3, 7, 14, 30 ngày sau. “·”: chưa đủ ngày.'});
}
function funnelCard(d,ui){
  const P=Object.fromEntries(d.funnel.map(p=>[p.key,p])),p=P[ui.funnel]||P.d7;
  const main=p.steps.filter(s=>s.key!=='created'),first=main.slice(0,12),rest=main.slice(12);
  const row=s=>`<li><span class="hl">${esc(s.label)}</span><b class="hv">${pct(s.pct)} <small>${num(s.n)}</small></b><span class="track" aria-hidden="true"><i style="width:${Math.max(s.n?2:0,Math.round(s.pct||0))}%"></i></span><small class="hs">${s.median_min!=null?`trung vị ${mins(s.median_min)} sau khi mở`:''}${s.est?` ${tag('ước tính','warn')}`:''}</small></li>`;
  const body=p.n?`<ul class="hbars funnel">${first.map(row).join('')}</ul>${rest.length?`<details class="more"><summary>Các mốc khác (${rest.length})</summary><ul class="hbars funnel">${rest.map(row).join('')}</ul></details>`:''}`
    :'<p class="note">Chưa có người mới được đo trong khoảng này (đo từ khi bản ghi mốc được bật).</p>';
  return card(`Phễu người mới <small>${num(p.n)} người</small>`,body,
    {extra:seg('funnel',ui.funnel,FUNNEL),note:`Người mở game ${p.start===p.end?dm(p.start):`${dm(p.start)}–${dm(p.end)}`}, % đã qua từng mốc tới giờ.${p.est?' Có mốc ước tính (gieo từ bản lưu, không có thời gian).':''}`});
}
function compareCard(d){
  const B=d.by_day,c=B.compare,lab=B.labels;
  if(!c)return '';
  const cols=[[dm(c.before.day),c.before],[c.after?(c.after.start===c.after.end?dm(c.after.start):`${dm(c.after.start)}→${dm(c.after.end)}`):'01/10→',c.after]];
  const head=`<tr><th></th>${cols.map(([l,x])=>`<th>${l}<br><small>${x?.n?`${num(x.n)} người`:'chưa có'}</small>${x?.est?`<br>${tag('ước tính','warn')}`:''}</th>`).join('')}</tr>`;
  const rows=B.keys.map(k=>`<tr><td>${esc(lab[k]||k)}</td>${cols.map(([,x])=>`<td>${x?.n?pct(x.pct[k]):'—'}</td>`).join('')}</tr>`);
  const days=B.rows.filter(r=>r.n).map(r=>`<tr><td>${dm(r.day)}${r.est?' *':''}</td><td>${num(r.n)}</td>${B.keys.map(k=>`<td>${pct(r.pct[k])}</td>`).join('')}</tr>`);
  return card('Trước và sau 0.9.16',`<div class="scroll"><table class="tbl cmp-tbl"><thead>${head}</thead><tbody>${rows.join('')}</tbody></table></div>`+
    (days.length?`<details class="more"><summary>Theo ngày bắt đầu (${days.length})</summary>${table(['Ngày','Người',...B.keys.map(k=>esc(lab[k]||k))],days,'tall')}</details>`:''),
    {note:'Người mở game trong ngày đó, % đã qua mốc tới giờ. 30/09 là trước bản khởi đầu mới (0.9.16). * có mốc ước tính.'});
}
function churnCard(d,name){
  const c=d.churn,fs=c.first_session;
  const grid=(x,n)=>`<div class="grid2">
    <div><h3 class="sub">Màn hình lúc rời</h3>${bars(x.screen,screenLabel)}</div>
    <div><h3 class="sub">Mốc cuối</h3>${bars(x.by_step,esc,{tone:'second',empty:'Chưa có người mới được đo.'})}</div>
    <div><h3 class="sub">Nơi làm</h3>${bars(x.career,v=>esc(v==='—'?'Chưa chọn':name(v)))}</div>
    <div><h3 class="sub">Ngày sống</h3>${bars(x.life,esc,{tone:'second'})}</div>
    <div><h3 class="sub">Bước hướng dẫn</h3>${bars(x.step,stepLabel)}</div>
    <div><h3 class="sub">Nút bấm cuối</h3>${bars(x.tap,v=>`<code>${esc(v)}</code>`,{tone:'second'})}</div>
  </div>`;
  const first=`<h3 class="sub">Rời ngay sau lượt chơi đầu</h3>
    <dl class="kv kv3"><div><dt>Người mới ${dm(fs.start)}–${dm(fs.end)}</dt><dd>${num(fs.cohort)}</dd></div><div><dt>Chỉ chơi 1 lượt</dt><dd>${num(fs.n)} <small>${pct(fs.pct)}</small></dd></div><div><dt>Lượt đó dài</dt><dd>${mins(fs.median_min)} <small>trung vị</small></dd></div></dl>
    ${grid(fs)}`;
  return card(`Rớt ở đâu <small>${num(c.players)} người</small>`,
    `<p class="note">Người có thao tác cuối cách đây ${c.window.min_days}–${c.window.max_days} ngày, theo lần rời trang cuối (${num(c.with_leave)} người có) và mốc cuối (${num(c.tracked)} người mới được đo).</p>`+grid(c)+
    `<details class="more"><summary>Rời ngay sau lượt đầu · ${pct(fs.pct)}</summary>${first}</details>`,{cls:'wide'});
}
function careersCard(d,name){
  const rows=d.careers.filter(c=>c.started||c.main.n||c.errors.length).map(c=>{
    const e=c.errors[0];
    return `<tr><td>${esc(name(c.id))}</td><td>${num(c.started)}</td><td>${num(c.main.n)}</td><td>${pct(c.main.d3)}</td><td>${pct(c.main.d7)}</td>
      <td class="err-cell">${e?`<code>${esc(e.action)}</code> <b>${num(e.errors)}</b> <small>${pct(e.rate)}</small>${e.err?`<small class="err-msg">${esc(e.err)}</small>`:''}`:'—'}</td></tr>`;
  });
  return card('Theo nghề',rows.length?table(['Nghề','Bắt đầu','Người mới','D3','D7','Bị từ chối nhiều nhất'],rows,'career-tbl'):'<p class="note">Chưa có số liệu.</p>',
    {note:'Bắt đầu: phục vụ khách đầu ở nghề này trong 30 ngày. Người mới: phục vụ khách đầu tiên ở đây; D3/D7 của họ. Thao tác bị từ chối nhiều nhất trong 7 ngày (số lần, tỉ lệ).'});
}
function sourcesCard(d,ui){
  const S=d.sources,rows=(S[ui.src]||[]).map(s=>`<tr><td>${esc(s.source)}</td><td>${num(s.n)} <small>${pct(s.share)}</small></td><td>${pct(s.d1)}</td><td>${pct(s.d7)}</td><td>${pct(s.served1)}</td></tr>`);
  return card(`Nguồn người mới <small>${num(S[ui.src+'_total'])}</small>`,rows.length?table(['Nguồn','Người','D1','D7','Khách đầu'],rows):'<p class="note">Chưa có người mới được ghi nguồn.</p>',
    {extra:seg('src',ui.src,{d7:'7 ngày',d30:'30 ngày'}),note:'utm_source của đường dẫn, nếu không có thì trang dẫn tới (facebook, tiktok, google, zalo…); direct: gõ thẳng hoặc không rõ.'});
}
function loadsCard(d){
  const L=d.loads,w=L.week;
  const days=L.days.filter(r=>r.n).map(r=>`<tr><td>${dm(r.day)}</td><td>${num(r.n)}</td><td>${ms(r.p50)}</td><td>${ms(r.p75)}</td><td>${ms(r.p90)}</td></tr>`);
  const WHO={new:'Người mới',ret:'Quay lại'},CACHE={cold:'Tải mới',warm:'Có sẵn',['?']:'Không rõ'},TIER={low:'RAM ≤ 2 GB',mid:'RAM 4 GB',high:'RAM ≥ 8 GB',['?']:'Không rõ'};
  const split=(rows,lab)=>rows.length?rows.map(r=>`<tr><td>${esc(lab[r.key]||r.key)}</td><td>${num(r.n)}</td><td>${ms(r.p50)}</td><td>${ms(r.p75)}</td><td>${ms(r.p90)}</td></tr>`):[];
  const head=['','Lượt','p50','p75','p90'];
  return card('Tốc độ tải',`<div class="kpis k4 inner">
      ${kpi('Khung hình đầu',ms(w.frame.p50),`p75 ${ms(w.frame.p75)} · p90 ${ms(w.frame.p90)}`)}
      ${kpi('Byte đầu (TTFB)',ms(w.ttfb.p50),`p75 ${ms(w.ttfb.p75)}`)}
      ${kpi('DOM sẵn sàng',ms(w.dcl.p50),`p75 ${ms(w.dcl.p75)}`)}
      ${kpi('Lượt đo',num(w.frame.n),'7 ngày')}
    </div>`+(days.length?`<h3 class="sub">Khung hình đầu theo ngày</h3>${table(['Ngày','Lượt','p50','p75','p90'],days)}`:'<p class="note">Chưa có lượt tải nào được đo.</p>')+
    `<details class="more"><summary>Theo mạng, người mới, bộ nhớ đệm, máy</summary><div class="grid2">
      <div><h3 class="sub">Mạng</h3>${table(head,split(L.by_net,{}))}</div><div><h3 class="sub">Người chơi</h3>${table(head,split(L.by_who,WHO))}</div>
      <div><h3 class="sub">Bộ nhớ đệm</h3>${table(head,split(L.by_cache,CACHE))}</div><div><h3 class="sub">Máy</h3>${table(head,split(L.by_tier,TIER))}</div></div></details>`,
    {note:'Từ lúc mở trang tới khung hình đầu của game, đo trên máy người chơi (7 ngày). Người mới: lượt chơi mở trong ngày.'});
}
function errorsCard(d,ui){
  const E=d.errors,rows=(E[ui.err]||[]).map(e=>`<tr><td>${tag(KIND[e.kind]||esc(e.kind),e.kind==='toast'?'info':'warn')}</td><td class="msg-cell">${esc(e.message)}</td><td>${screenLabel(e.screen)}</td><td>${num(e.n)}</td></tr>`);
  return card(`Lỗi phía người chơi <small>${num(E[ui.err+'_total'])}</small>`,rows.length?table(['Loại','Nội dung','Màn hình','Lần'],rows,'err-tbl'):'<p class="note">Chưa ghi nhận lỗi nào.</p>',
    {extra:seg('err',ui.err,{today:'Hôm nay',d7:'7 ngày'})});
}
function sizesLine(d){
  const S=d.sizes;if(!S.tables.length)return '';
  const top=S.tables.slice(0,4).map(t=>`<code>${esc(t.name)}</code> ${bytes(t.bytes)}`).join(' · ');
  return `<p class="foot">${icon('server',14)} Dung lượng log: <b>${bytes(S.total)}</b> · ${top}${S.tables.length>4?` · ${S.tables.length-4} bảng khác`:''}. Giữ chi tiết ${num(d.rules.actions_days)} ngày (thao tác, rời trang, lỗi); mốc và nguồn giữ lâu dài.</p>`;
}

/** The whole view. `ui`: {funnel, src, err} (segment choices); `name`: career id → name. */
export function retentionView(d,ui,name){
  const since=d.since?`Đo mốc từ ${hm(d.since)} (${ago(d.since)}).`:'Chưa có mốc nào được ghi.';
  return kpis(d)+cohortCard(d)+`<div class="cols"><div class="col">${funnelCard(d,ui)}${sourcesCard(d,ui)}</div><div class="col">${compareCard(d)}${careersCard(d,name)}</div></div>`+
    churnCard(d,name)+`<div class="cols"><div class="col">${loadsCard(d)}</div><div class="col">${errorsCard(d,ui)}</div></div>`+
    `<p class="foot">${since} Cập nhật ${hm(d.generated_at)}${d.cached?` (bản đệm ${num(d.age)} giây)`:''} · tính trong ${dec(d.took_ms)} ms. Không chứa tên, mã phiên hay chữ người chơi gõ.</p>`+sizesLine(d);
}
