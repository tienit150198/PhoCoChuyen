/** "Tổng quan": the first screen, drawn from one GET /api/admin/stats/summary payload
 * (game/admin_stats.py). The save-derived cards (careers, play, economy, life) and the
 * "Hệ thống" view come later from GET /api/admin/stats/section and are drawn by
 * ./sections.js, loaded on demand. Aggregates only: no names, session ids or contact details. */
import {esc,icon,num,dec,pct,share,dm,stamp,last,bytes,span,hours,ago,hm,clockS,kindOf,STATUS,tag} from './ui.js';

/* ---- parts ------------------------------------------------------------------ */
export function kpi(label,value,sub,{tone='',action='',ic=''}={}){
  const inner=`<span class="kpi-label">${ic?icon(ic,14):''}${label}</span><b class="kpi-num">${value}</b>${sub?`<small class="kpi-sub">${sub}</small>`:''}`;
  return action?`<button type="button" class="kpi kpi-btn ${tone}" data-go="${action}">${inner}</button>`:`<div class="kpi ${tone}">${inner}</div>`;
}
export function kv(rows,cls=''){
  return `<dl class="kv ${cls}">${rows.filter(Boolean).map(([k,v])=>`<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>`;
}
export function card(title,body,{note='',extra='',cls=''}={}){
  return `<section class="card ${cls}"><header class="card-head"><h2>${title}</h2>${extra}</header>${body}${note?`<p class="note">${note}</p>`:''}</section>`;
}
export function table(head,rows,cls=''){
  return `<div class="scroll"><table class="tbl ${cls}"><thead><tr>${head.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}
/** "Xem thêm" under a list cut to `shown` of `total` rows (data-act="more" grows it). */
export function moreButton(key,shown,total){
  return total>shown?`<div class="more-row"><button type="button" class="btn ghost sm" data-act="more" data-key="${key}">Xem thêm (${num(total-shown)})</button></div>`:'';
}
/** Grey placeholder blocks while a part of the page is on its way. */
export const skelLines=(n=3)=>`<div class="skel-lines" aria-hidden="true">${'<i></i>'.repeat(n)}</div>`;
export function skelCard(title,{lazy='',lines=4,error='',note=''}={}){
  const body=error?`<div class="notice bad">${icon('alert',16)}<div>${esc(error)}<br><button type="button" class="btn ghost sm" data-act="retrySection" data-name="${lazy}">Thử lại</button></div></div>`:skelLines(lines)+(note?`<p class="note">${esc(note)}</p>`:'');
  return `<section class="card${error?'':' skel'}"${lazy?` data-lazy="${lazy}"`:''} aria-busy="${!error}"><header class="card-head"><h2>${title}</h2></header>${body}</section>`;
}
export function skeleton(){
  const k=`<div class="kpi skel-kpi"><span class="kpi-label">&nbsp;</span><b class="kpi-num">&nbsp;</b><small class="kpi-sub">&nbsp;</small></div>`;
  return `<div class="kpis skel" aria-hidden="true">${k.repeat(6)}</div>`+
    `<section class="card wide skel" aria-busy="true"><header class="card-head"><h2>Người chơi</h2></header><div class="skel-chart" aria-hidden="true"></div>${skelLines(2)}</section>`+
    `<section class="card wide skel" aria-busy="true"><header class="card-head"><h2>Thời gian chơi</h2></header>${skelLines(4)}</section>`+
    `<div class="cols"><div class="col">${skelCard('Nghề được chơi nhiều')}${skelCard('Kinh tế')}</div><div class="col">${skelCard('Cách chơi')}${skelCard('Góp ý')}</div></div>`;
}

/** Daily columns (HTML bars, one hover target per day). Today is drawn lighter: the day is not over. */
function columns(values,days,title,tone=''){
  const n=values.length,max=Math.max(1,...values),total=values.reduce((a,b)=>a+b,0);
  const bars=values.map((v,i)=>`<span class="bar${i===n-1?' today':''}" data-tip="${i===n-1?'Hôm nay':dm(days[i])}: ${num(v)}"><i style="height:${v?Math.max(2,Math.round(1000*v/max)/10):0}%"></i></span>`).join('');
  return `<figure class="chart ${tone}"><figcaption><b>${title}</b><span>tổng ${num(total)} · cao nhất ${num(Math.max(0,...values))} · hôm nay ${num(last(values))}</span></figcaption>
    <div class="plot"><span class="plot-max" aria-hidden="true">${num(max)}</span><div class="bars${n>40?' dense':''}" role="img" aria-label="${esc(title)}: hôm nay ${num(last(values))}, cao nhất ${num(max)}, tổng ${num(total)}">${bars}</div></div>
    <div class="xaxis" aria-hidden="true"><span>${dm(days[0])}</span><span>${n>7?dm(days[Math.floor(n/2)]):''}</span><span>hôm nay</span></div></figure>`;
}

/* ---- first-screen sections ----------------------------------------------------------- */
function playersCard(d,more){
  const p=d.players,r=p.retention;
  const since=p.tracked_since?`Số theo ngày đếm từ ${dm(p.tracked_since)}; trước đó chỉ biết lần chơi cuối của mỗi lượt.`:'Số theo ngày bắt đầu đếm từ hôm nay.';
  const daily=p.days.map((day,i)=>`<tr><td>${dm(day)}</td><td>${num(p.dau[i])}</td><td>${num(p.new_players[i])}</td><td>${num(p.new_sessions[i])}</td><td>${num(p.new_accounts[i])}</td></tr>`).reverse();
  const shown=Math.min(daily.length,more.daily);
  return card('Người chơi',
    `<div class="charts">${columns(p.dau,p.days,'Hoạt động mỗi ngày')}${columns(p.new_players,p.days,'Người mới mỗi ngày','second')}</div>
    ${kv([['Hoạt động 7 ngày',num(p.wau)],['Hoạt động 30 ngày',num(p.mau)],
      ['Giữ chân D1',`${pct(r.d1)} <small>/${num(r.d1_n)}</small>`],['Giữ chân D7',`${pct(r.d7)} <small>/${num(r.d7_n)}</small>`],
      ['Đã chơi',num(p.played)],['Lượt mở trang',num(p.total)],['Tài khoản',num(p.accounts)],['Khách đã chơi',num(p.guests)]],'kv4')}
    <details class="more"><summary>Bảng số theo ngày</summary>${table(['Ngày','Hoạt động','Mới chơi','Mở trang','Tài khoản'],daily.slice(0,shown),'tall')}${moreButton('daily',shown,daily.length)}</details>`,
    {note:`${since} Giữ chân D1/D7: người bắt đầu chơi trong ${r.window} ngày qua có quay lại đúng 1/7 ngày sau.`,cls:'wide'});
}
function feedbackCard(d){
  const f=d.feedback;
  const rows=f.kinds.map(k=>{const [,emo,label]=kindOf(k.kind);return `<tr><td><span aria-hidden="true">${emo}</span> ${esc(label)}</td><td>${num(k.new)}</td><td>${num(k.seen)}</td><td>${num(k.done)}</td></tr>`;});
  const newest=f.newest.length?`<ul class="mini-fb">${f.newest.map(it=>{const [,emo,label]=kindOf(it.kind),[st,tone]=STATUS[it.status]||STATUS.new;
    return `<li><span class="mini-top"><span><span aria-hidden="true">${emo}</span> ${esc(label)}</span>${tag(st,tone)}<small>#${num(it.id)} · ${ago(it.created_at)}</small></span><span class="mini-text">${esc(it.text)}</span></li>`;}).join('')}</ul>`:'<p class="note">Chưa có góp ý nào.</p>';
  return card('Góp ý',
    table(['Loại',...Object.values(STATUS).map(([l])=>l)],rows)+
    kv([['Đang mở',num(f.open)],['Chưa đọc',num(f.unread)],[`Mới trong ${d.range} ngày`,num(f.in_range)],['Chờ được đọc',`${hours(f.ack.median_h)} <small>TB ${hours(f.ack.avg_h)}</small>`],
      f.ack.waiting!=null&&['Còn chờ đọc',`${num(f.ack.waiting)}${f.ack.waiting?` <small>lâu nhất ${hours(f.ack.oldest_wait_h)}</small>`:''}`],
      f.ack.read_pct!=null&&['Đã đọc',`${pct(f.ack.read_pct)} <small>${num(f.ack.window_days)} ngày</small>`]],'kv4')+
    `<h3 class="sub">5 góp ý mới nhất</h3>${newest}`,
    {extra:`<button type="button" class="btn ghost sm" data-go="gop-y">${icon('inbox',15)} Mở hộp góp ý</button>`});
}
function aiCard(d){
  const a=d.ai,t=a.total;
  const rows=a.days.slice(-7).reverse().map(r=>`<tr><td>${dm(r.day)}</td><td>${num(r.calls)}</td><td>${num(r.ok)}</td><td>${num(r.failed+r.busy)}</td><td>${num(r.rejected)}</td><td>${num(r.guard)}</td></tr>`);
  return card(a.persisted?`AI <small>mọi tiến trình${a.since_day?` · từ ${dm(a.since_day)}`:''}</small>`:'AI <small>từ lúc khởi động</small>',
    (a.configured?'':`<div class="notice warn">${icon('alert',16)}<div>Máy chủ chưa cấu hình AI: nhân vật dùng lời có sẵn.</div></div>`)+
    kv([['Lượt gọi',num(t.calls)],['Thành công',`${num(t.ok)} <small>${share(t.ok,t.calls)}</small>`],['Lỗi · bận',`${num(t.failed)} · ${num(t.busy)}`],
      ['Câu AI bị lọc',num(t.rejected)],['Chặn lời lẽ xấu',num(t.guard)]],'kv3')+
    (rows.length?table(['Ngày','Gọi','Được','Lỗi','Lọc','Chặn'],rows):''),
    {note:a.persisted?`Cộng mọi tiến trình máy chủ, lưu trong cơ sở dữ liệu (ghi mỗi 30 giây; khởi động lại không mất).`:`Chỉ tiến trình này, đếm trong bộ nhớ từ ${stamp(a.since)}; khởi động lại máy chủ thì về 0.`});
}
function serverCard(d){
  const s=d.server;
  return card('Máy chủ',
    kv([['Phiên bản',`v${esc(s.version)}`],['Chạy liên tục',span(s.uptime)],['Dung lượng dữ liệu',bytes(s.db_bytes)],['Tính số liệu',`${dec(d.took_ms)} ms`]],'kv4'),
    {extra:`<button type="button" class="btn ghost sm" data-go="he-thong">${icon('server',15)} Chi tiết</button>`});
}

/* ---- live counters (GET …/section?name=live, every 15 s) ------------------------------ */
const ms=v=>v==null?'—':`${dec(v)} ms`;
/** The "Trực tiếp" band: cheap counters read on request (never the saves, never the job). */
export function liveView(L,{error='',busy=false}={}){
  if(!L){
    const k=`<div class="kpi skel-kpi"><span class="kpi-label">&nbsp;</span><b class="kpi-num">&nbsp;</b><small class="kpi-sub">&nbsp;</small></div>`;
    return `<section class="live" aria-busy="true"><header class="live-head"><h2>${icon('pulse',15)} Trực tiếp</h2><small>${error?esc(error):'Đang đọc…'}</small></header><div class="kpis k4 skel" aria-hidden="true">${k.repeat(4)}</div></section>`;
  }
  const a=L.active,n=L.new_today,c=L.commands||{};
  const cmdSub=c.n?`p50 ${ms(c.p50)} · p90 ${ms(c.p90)}`:'chưa có thao tác';
  return `<section class="live${busy?' is-busy':''}" aria-label="Số liệu trực tiếp">
    <header class="live-head"><h2><span class="dot" aria-hidden="true"></span>Trực tiếp</h2><small>cập nhật ${clockS(L.generated_at)}${error?` · <span class="warn-text">${esc(error)}</span>`:''}</small></header>
    <div class="kpis k4">
      ${kpi('Đang chơi',num(a.m5),`5 phút · 1 giờ ${num(a.h1)} · 24 giờ ${num(a.h24)}`)}
      ${kpi('Mới hôm nay',num(n.players),`${num(n.sessions)} lượt mở · ${num(n.accounts)} tài khoản`)}
      ${kpi('Thao tác / phút',dec(c.per_min),cmdSub)}
      ${kpi('Cơ sở dữ liệu',bytes(L.db_bytes),esc(L.database||L.backend||''),{action:'he-thong'})}
    </div>
    <p class="note">“Đang chơi”: lượt chơi có thao tác trong 5 phút qua. Thao tác/phút và độ trễ p50/p90 tính trên ${dec(c.minutes||0)} phút gần nhất${c.workers>1?` của ${num(c.workers)} tiến trình`:''}.</p>
  </section>`;
}
/** When the first screen is not fresh (the job's copy, a slow disk), say from when. */
export function summaryFresh(d){
  if(!d.stale&&!d.old)return '';
  const when=`Số liệu tổng quan tính lúc ${hm(d.computed_at)} (${ago(d.computed_at)})`;
  return `<div class="notice ${d.old?'warn':'info'}" role="status">${icon(d.old?'alert':'clock',16)}<div>${when}: máy chủ bận nên dùng bản tính ở chế độ nền.${d.old?' Số có thể đã cũ.':''}</div></div>`;
}
/** The save-derived cards' freshness: held for the players, or simply old. */
export function savesFresh(sv){
  const s=sv?.snapshot;if(!s||!s.computed_at)return '';
  if(s.held)return `<div class="notice info" role="status">${icon('pause',16)}<div>Số liệu bản lưu cập nhật lúc <b>${hm(s.computed_at)}</b> (đang tạm giữ để game nhanh).</div></div>`;
  if(s.old)return `<div class="notice warn" role="status">${icon('alert',16)}<div>Số liệu bản lưu cập nhật lúc <b>${hm(s.computed_at)}</b> (${ago(s.computed_at)}), đang chờ lần tính mới.</div></div>`;
  return '';
}

/** `lazy`: {careers, economy, play, life, playtime} → HTML of each card loaded on demand (the
 * real card once ./sections.js drew it, else a placeholder the page loads when it scrolls into view). */
export function overviewView(d,lazy,more,L={}){
  const p=d.players,f=d.feedback,r=p.retention,s={...d.server,db_bytes:L.data?.db_bytes??d.server.db_bytes};  // the live size is the current one
  const kpis=`<div class="kpis">
    ${kpi('Hoạt động hôm nay',num(last(p.dau)),`7 ngày ${num(p.wau)} · 30 ngày ${num(p.mau)}`)}
    ${kpi('Người mới hôm nay',num(last(p.new_players)),`${num(last(p.new_sessions))} lượt mở · ${num(last(p.new_accounts))} tài khoản`)}
    ${kpi('Giữ chân D1',pct(r.d1),`D7 ${pct(r.d7)} · trên ${num(r.d1_n)} người đủ 1 ngày`)}
    ${kpi('Người chơi',num(p.played),`${num(p.account_saves)} tài khoản · ${num(p.guests)} khách`)}
    ${kpi('Góp ý chưa đọc',num(f.unread),`${num(f.open)} đang mở ${icon('chevron',12)}`,{tone:f.unread?'hot':'',action:'gop-y'})}
    ${kpi('Máy chủ',`v${esc(s.version)}`,`chạy ${span(s.uptime)} · ${bytes(s.db_bytes)}`,{action:'he-thong'})}
  </div>`;
  return liveView(L.data,{error:L.error})+summaryFresh(d)+kpis+playersCard(d,more)+(lazy.playtime||'')+(lazy.head||'')+`<div class="cols"><div class="col">${lazy.careers}${lazy.economy}${aiCard(d)}</div><div class="col">${lazy.play}${lazy.life}${feedbackCard(d)}${serverCard({...d,server:s})}</div></div>`+
    (lazy.foot||'');
}
