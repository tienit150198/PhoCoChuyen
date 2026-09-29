/** "Tổng quan" and "Hệ thống": pure renderers over one GET /api/admin/stats payload
 * (game/admin_stats.py). Ported from public/js/v4/admin-stats.js for the standalone
 * operator site. Aggregates only: no names, session ids or contact details. */
import {esc,icon,num,dec,pct,share,dm,stamp,last,bytes,span,hours,ago,kindOf,STATUS,tag} from './ui.js';

const THEME={kem:'Kem sữa',tra_xanh:'Trà xanh',bien:'Biển chiều',keo:'Kẹo ngọt',dem:'Phố đêm'};
const LANG={vi:'Tiếng Việt',en:'English'};

/* ---- parts ------------------------------------------------------------------ */
function kpi(label,value,sub,{tone='',action='',ic=''}={}){
  const inner=`<span class="kpi-label">${ic?icon(ic,14):''}${label}</span><b class="kpi-num">${value}</b>${sub?`<small class="kpi-sub">${sub}</small>`:''}`;
  return action?`<button type="button" class="kpi kpi-btn ${tone}" data-go="${action}">${inner}</button>`:`<div class="kpi ${tone}">${inner}</div>`;
}
export function kv(rows,cls=''){
  return `<dl class="kv ${cls}">${rows.filter(Boolean).map(([k,v])=>`<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>`;
}
export function card(title,body,{note='',extra='',cls=''}={}){
  return `<section class="card ${cls}"><header class="card-head"><h2>${title}</h2>${extra}</header>${body}${note?`<p class="note">${note}</p>`:''}</section>`;
}
/** Daily columns (HTML bars, one hover target per day). Today is drawn lighter: the day is not over. */
function columns(values,days,title,tone=''){
  const n=values.length,max=Math.max(1,...values),total=values.reduce((a,b)=>a+b,0);
  const bars=values.map((v,i)=>`<span class="bar${i===n-1?' today':''}" data-tip="${i===n-1?'Hôm nay':dm(days[i])}: ${num(v)}"><i style="height:${v?Math.max(2,Math.round(1000*v/max)/10):0}%"></i></span>`).join('');
  return `<figure class="chart ${tone}"><figcaption><b>${title}</b><span>tổng ${num(total)} · cao nhất ${num(Math.max(0,...values))} · hôm nay ${num(last(values))}</span></figcaption>
    <div class="plot"><span class="plot-max" aria-hidden="true">${num(max)}</span><div class="bars${n>40?' dense':''}" role="img" aria-label="${esc(title)}: hôm nay ${num(last(values))}, cao nhất ${num(max)}, tổng ${num(total)}">${bars}</div></div>
    <div class="xaxis" aria-hidden="true"><span>${dm(days[0])}</span><span>${n>7?dm(days[Math.floor(n/2)]):''}</span><span>hôm nay</span></div></figure>`;
}
/** Horizontal bars: {label, n, sub?}; length relative to the largest row. */
function hbars(rows,{total=null,tone='',compact=false}={}){
  if(!rows.length)return '<p class="note">Chưa có số liệu.</p>';
  const max=Math.max(1,...rows.map(r=>r.n));
  return `<ul class="hbars ${tone}${compact?' compact':''}">${rows.map(r=>`<li><span class="hl">${r.label}</span><b class="hv">${num(r.n)}${total?` <small>${share(r.n,total)}</small>`:''}</b><span class="track" aria-hidden="true"><i style="width:${Math.max(r.n?2:0,Math.round(100*r.n/max))}%"></i></span>${r.sub?`<small class="hs">${r.sub}</small>`:''}</li>`).join('')}</ul>`;
}
function table(head,rows,cls=''){
  return `<div class="scroll"><table class="tbl ${cls}"><thead><tr>${head.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}

/* ---- overview sections -------------------------------------------------------------- */
function playersCard(d){
  const p=d.players,r=p.retention;
  const since=p.tracked_since?`Số theo ngày đếm từ ${dm(p.tracked_since)}; trước đó chỉ biết lần chơi cuối của mỗi lượt.`:'Số theo ngày bắt đầu đếm từ hôm nay.';
  const daily=p.days.map((day,i)=>`<tr><td>${dm(day)}</td><td>${num(p.dau[i])}</td><td>${num(p.new_players[i])}</td><td>${num(p.new_sessions[i])}</td><td>${num(p.new_accounts[i])}</td></tr>`).reverse();
  return card('Người chơi',
    `<div class="charts">${columns(p.dau,p.days,'Hoạt động mỗi ngày')}${columns(p.new_players,p.days,'Người mới mỗi ngày','second')}</div>
    ${kv([['Hoạt động 7 ngày',num(p.wau)],['Hoạt động 30 ngày',num(p.mau)],
      ['Giữ chân D1',`${pct(r.d1)} <small>/${num(r.d1_n)}</small>`],['Giữ chân D7',`${pct(r.d7)} <small>/${num(r.d7_n)}</small>`],
      ['Đã chơi',num(p.played)],['Lượt mở trang',num(p.total)],['Tài khoản',num(p.accounts)],['Khách đã chơi',num(p.guests)]],'kv4')}
    <details class="more"><summary>Bảng số theo ngày</summary>${table(['Ngày','Hoạt động','Mới chơi','Mở trang','Tài khoản'],daily,'tall')}</details>`,
    {note:`${since} Giữ chân D1/D7: người bắt đầu chơi trong ${r.window} ngày qua có quay lại đúng 1/7 ngày sau.`,cls:'wide'});
}
function careersCard(d,api){
  const pl=d.play,rows=pl.careers.map(c=>({label:esc(api.career(c.id)),n:c.players,sub:`${num(c.days)} ngày chơi · cấp TB ${dec(c.avg_level)}`}));
  return card('Nghề được chơi nhiều',hbars(rows),{note:pl.careers_total>pl.careers.length?`Hiện ${pl.careers.length}/${pl.careers_total} nghề.`:''});
}
function playCard(d){
  const pl=d.play,n=pl.sample;
  const lang=pl.lang.map(x=>({label:esc(LANG[x.key]||x.key),n:x.n}));
  const theme=pl.theme.map(x=>({label:esc(THEME[x.key]||x.key),n:x.n}));
  const ch=pl.chapters.map(x=>({label:`Chương ${esc(x.key)}`,n:x.n}));
  const lv=pl.levels.map(x=>({label:`Cấp ${esc(x.key)}`,n:x.n}));
  return card('Cách chơi',
    kv([['Ngày đời TB',dec(pl.life_day.avg)],['Trung vị · p90',`${dec(pl.life_day.median)} · ${dec(pl.life_day.p90)}`],
      ['Chế độ câu chuyện',`${num(pl.story)} <small>${share(pl.story,n)}</small>`],['Bật nhân vật AI',`${num(pl.ai_on)} <small>${share(pl.ai_on,n)}</small>`],
      ['Bật nhạc',`${num(pl.music_on)} <small>${share(pl.music_on,n)}</small>`]],'kv3')+
    `<div class="grid2"><div><h3 class="sub">Chương đang ở</h3>${hbars(ch,{total:pl.story,compact:true})}</div><div><h3 class="sub">Cấp nghề cao nhất</h3>${hbars(lv,{total:lv.reduce((a,b)=>a+b.n,0),compact:true})}</div>
      <div><h3 class="sub">Ngôn ngữ</h3>${hbars(lang,{total:n,tone:'second',compact:true})}</div><div><h3 class="sub">Giao diện</h3>${hbars(theme,{total:n,tone:'second',compact:true})}</div></div>`);
}
function economyCard(d){
  const e=d.economy,n=e.sample;
  return card('Kinh tế',
    kv([['Ví trung vị',`${num(e.wallet.median)} xu`],['Ví p90',`${num(e.wallet.p90)} xu`],['Ví trung bình',`${dec(e.wallet.avg)} xu`],
      ['Đang nợ',`${num(e.debt)} <small>${share(e.debt,n)}</small>`],['Có đầu tư',`${num(e.investors)} <small>${share(e.investors,n)}</small>`],
      ['Mất vì lừa đảo',`${num(e.scam_lost)} xu`],['Người bị lừa',num(e.scam_victims)],['Lượt sa bẫy',num(e.scam_joined)]],'kv3')+
    `<h3 class="sub">Số xu trong ví</h3>${hbars(e.buckets.map(b=>({label:esc(b.label),n:b.n})),{total:n,compact:true})}`);
}
function lifeCard(d){
  const L=d.life,B=d.board;
  if(!L.saves&&!B.saves)return card('Đời sống & Nhóm cư dân','<p class="note">Chưa lượt chơi nào có hai phần này.</p>');
  return card('Đời sống & Nhóm cư dân',
    `<h3 class="sub">Chuyện đời</h3>`+kv([['Có “Chuyện đời”',num(L.saves)],['Tinh thần TB',dec(L.avg_spirit)],['Lần đi chơi',num(L.outings)],['Lần gặp lừa',num(L.scams)],['Tin đồn',num(L.rumours)],['Chuyện ấm · khó',`${num(L.warm)} · ${num(L.hard)}`]],'kv3')+
    `<h3 class="sub">Nhóm cư dân</h3>`+kv([['Có Nhóm cư dân',num(B.saves)],['Người đã đăng bài',num(B.active)],['Bài · trả lời',`${num(B.player_posts)} · ${num(B.player_replies)}`],['Lượt thả cảm xúc',num(B.reacts)]],'kv3'));
}
function feedbackCard(d){
  const f=d.feedback;
  const rows=f.kinds.map(k=>{const [,emo,label]=kindOf(k.kind);return `<tr><td><span aria-hidden="true">${emo}</span> ${esc(label)}</td><td>${num(k.new)}</td><td>${num(k.seen)}</td><td>${num(k.done)}</td></tr>`;});
  const newest=f.newest.length?`<ul class="mini-fb">${f.newest.map(it=>{const [,emo,label]=kindOf(it.kind),[st,tone]=STATUS[it.status]||STATUS.new;
    return `<li><span class="mini-top"><span><span aria-hidden="true">${emo}</span> ${esc(label)}</span>${tag(st,tone)}<small>#${num(it.id)} · ${ago(it.created_at)}</small></span><span class="mini-text">${esc(it.text)}</span></li>`;}).join('')}</ul>`:'<p class="note">Chưa có góp ý nào.</p>';
  return card('Góp ý',
    table(['Loại',...Object.values(STATUS).map(([l])=>l)],rows)+
    kv([['Đang mở',num(f.open)],['Chưa đọc',num(f.unread)],[`Mới trong ${d.range} ngày`,num(f.in_range)],['Chờ được đọc',`${hours(f.ack.median_h)} <small>TB ${hours(f.ack.avg_h)}</small>`]],'kv4')+
    `<h3 class="sub">5 góp ý mới nhất</h3>${newest}`,
    {extra:`<button type="button" class="btn ghost sm" data-go="gop-y">${icon('inbox',15)} Mở hộp góp ý</button>`});
}
function aiCard(d){
  const a=d.ai,t=a.total;
  const rows=a.days.slice(-7).reverse().map(r=>`<tr><td>${dm(r.day)}</td><td>${num(r.calls)}</td><td>${num(r.ok)}</td><td>${num(r.failed+r.busy)}</td><td>${num(r.rejected)}</td><td>${num(r.guard)}</td></tr>`);
  return card('AI <small>từ lúc khởi động</small>',
    (a.configured?'':`<div class="notice warn">${icon('alert',16)}<div>Máy chủ chưa cấu hình AI: nhân vật dùng lời có sẵn.</div></div>`)+
    kv([['Lượt gọi',num(t.calls)],['Thành công',`${num(t.ok)} <small>${share(t.ok,t.calls)}</small>`],['Lỗi · bận',`${num(t.failed)} · ${num(t.busy)}`],
      ['Câu AI bị lọc',num(t.rejected)],['Chặn lời lẽ xấu',num(t.guard)]],'kv3')+
    (rows.length?table(['Ngày','Gọi','Được','Lỗi','Lọc','Chặn'],rows):''),
    {note:`Đếm trong bộ nhớ từ ${stamp(a.since)}; khởi động lại máy chủ thì về 0.`});
}
function serverCard(d){
  const s=d.server;
  return card('Máy chủ',
    kv([['Phiên bản',`v${esc(s.version)}`],['Chạy liên tục',span(s.uptime)],['Dung lượng dữ liệu',bytes(s.db_bytes)],['Tính số liệu',`${dec(d.took_ms)} ms`]],'kv4'),
    {extra:`<button type="button" class="btn ghost sm" data-go="he-thong">${icon('server',15)} Chi tiết</button>`});
}

export function overviewView(d,api){
  const p=d.players,f=d.feedback,r=p.retention,s=d.server;
  const kpis=`<div class="kpis">
    ${kpi('Hoạt động hôm nay',num(last(p.dau)),`7 ngày ${num(p.wau)} · 30 ngày ${num(p.mau)}`)}
    ${kpi('Người mới hôm nay',num(last(p.new_players)),`${num(last(p.new_sessions))} lượt mở · ${num(last(p.new_accounts))} tài khoản`)}
    ${kpi('Giữ chân D1',pct(r.d1),`D7 ${pct(r.d7)} · nhóm ${num(r.cohort)} người`)}
    ${kpi('Người chơi',num(p.played),`${num(p.account_saves)} tài khoản · ${num(p.guests)} khách`)}
    ${kpi('Góp ý chưa đọc',num(f.unread),`${num(f.open)} đang mở ${icon('chevron',12)}`,{tone:f.unread?'hot':'',action:'gop-y'})}
    ${kpi('Máy chủ',`v${esc(s.version)}`,`chạy ${span(s.uptime)} · ${bytes(s.db_bytes)}`,{action:'he-thong'})}
  </div>`;
  return kpis+playersCard(d)+`<div class="cols"><div class="col">${careersCard(d,api)}${economyCard(d)}${aiCard(d)}</div><div class="col">${playCard(d)}${lifeCard(d)}${feedbackCard(d)}${serverCard(d)}</div></div>`+
    `<p class="foot">Số về cách chơi, kinh tế, đời sống lấy từ mẫu ${num(d.sample.size)} lượt chơi có thao tác gần nhất (tối đa ${num(d.sample.limit)}). Không chứa tên, mã phiên hay thông tin liên lạc.</p>`;
}

/* ---- Hệ thống ---------------------------------------------------------------------------- */
export function systemView(d,api){
  const s=d.server,tables=[...s.tables].sort((a,b)=>b.rows-a.rows||a.name.localeCompare(b.name));
  const total=tables.reduce((a,t)=>a+t.rows,0),max=Math.max(1,...tables.map(t=>t.rows));
  const rows=tables.map(t=>`<tr><td><code>${esc(t.name)}</code></td><td>${num(t.rows)}</td><td class="share-cell"><div><span class="track" aria-hidden="true"><i style="width:${Math.max(t.rows?1:0,Math.round(100*t.rows/max))}%"></i></span><small>${share(t.rows,total)||'0%'}</small></div></td></tr>`);
  const kpis=`<div class="kpis k4">
    ${kpi('Phiên bản',`v${esc(s.version)}`,`Python ${esc(s.python)} · SQLite ${esc(s.sqlite)}`,{ic:'sparkle'})}
    ${kpi('Chạy liên tục',span(s.uptime),`từ ${stamp(s.started)}`,{ic:'clock'})}
    ${kpi('Dung lượng dữ liệu',bytes(s.db_bytes),'cơ sở dữ liệu + WAL',{ic:'server'})}
    ${kpi('Tổng số dòng',num(total),`${num(tables.length)} bảng`,{ic:'chart'})}
  </div>`;
  const env=card('Môi trường',kv([
    ['Phiên bản game',`v${esc(s.version)}`],['Python',esc(s.python)],['SQLite',esc(s.sqlite)],
    ['Chế độ câu chuyện',s.story?tag('bật','good'):tag('tắt')],['AI',d.ai.configured?tag('đã cấu hình','good'):tag('chưa cấu hình','warn')],
    ['Khởi động lúc',stamp(s.started)],
  ],'kv2'));
  const calc=card('Số liệu thống kê',kv([
    ['Tạo lúc',stamp(d.generated_at)],['Thời gian tính',`${dec(d.took_ms)} ms`],['Bộ nhớ đệm',d.cached?`dùng bản ${dec(d.age)} giây trước`:'vừa tính mới'],
    ['Mẫu lượt chơi',`${num(d.sample.size)} <small>/ tối đa ${num(d.sample.limit)}</small>`],['Cách đọc mẫu',d.sample.engine==='sql'?'SQLite JSON':'Python (dự phòng)'],['Ngày (giờ VN)',esc(d.today)],
  ],'kv2'),{note:'Số liệu được lưu đệm khoảng 60 giây trên máy chủ; nút “Làm mới” yêu cầu tính lại.'});
  const who=card('Phiên vận hành',kv([
    ['Đăng nhập với',`@${esc(api.account?.username||'')}`],['Tên hiển thị',esc(api.account?.display||'')],
  ],'kv2')+`<p class="note">Quyền vận hành đến từ biến môi trường <code>ADMIN_USERS</code> trên máy chủ và được kiểm tra lại ở mỗi lần gọi.</p>
    <button type="button" class="btn ghost sm" data-act="logout">${icon('exit',15)} Đăng xuất</button>`);
  return kpis+`<div class="cols"><div class="col">${card('Bảng dữ liệu',table(['Bảng','Số dòng','Tỉ lệ'],rows,'tables'),{note:'Số dòng đếm trực tiếp khi tính thống kê.'})}</div><div class="col">${env}${calc}${who}</div></div>`;
}

