/** "Thống kê" — the operator's dashboard, a tab of the "Góp ý" sheet next to the
 * inbox. Only admin accounts see the tab; the server re-checks ADMIN_USERS on every
 * call. Data: GET /api/admin/stats?range=7|30|90 (game/admin_stats.py), cached there
 * for about a minute. Numbers only: no player names, ids or contact details. */
import {icon,escapeHTML as esc} from '../icons.js';

const RANGES=[7,30,90];
const KINDS=[['bug','🐞','Lỗi'],['idea','💡','Ý tưởng'],['praise','💖','Khen'],['hard','🤔','Khó dùng']];
const STATUS={new:['Mới','amber'],seen:['Đã xem','blue'],done:['Xong','green']};
const THEME={kem:'Kem sữa',tra_xanh:'Trà xanh',bien:'Biển chiều',keo:'Kẹo ngọt',dem:'Phố đêm'};
const LANG={vi:'Tiếng Việt',en:'English'};
const STALE_MS=60000;

const nf=new Intl.NumberFormat('vi-VN'),nf1=new Intl.NumberFormat('vi-VN',{maximumFractionDigits:1});
const num=n=>n==null?'—':nf.format(Math.round(n));
const dec=n=>n==null?'—':nf1.format(n);
const pct=n=>n==null?'—':`${nf1.format(n)}%`;
const share=(n,total)=>total?pct(Math.round(1000*n/total)/10):'';
const dm=iso=>`${iso.slice(8,10)}/${iso.slice(5,7)}`;
const clock=t=>new Date(t*1000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'});
const last=a=>a?.length?a[a.length-1]:0;
function bytes(b){if(b==null)return'—';const u=['B','KB','MB','GB'];let i=0;while(b>=1024&&i<u.length-1){b/=1024;i++;}return `${nf1.format(b)} ${u[i]}`;}
function span(s){if(s==null)return'—';const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return d?`${d} ngày ${h} giờ`:h?`${h} giờ ${m} phút`:`${m} phút`;}
function hours(h){if(h==null)return'—';return h<1?`${Math.max(1,Math.round(h*60))} phút`:h<48?`${dec(h)} giờ`:`${dec(h/24)} ngày`;}
const ago=t=>{const s=Math.max(0,Date.now()/1000-t);if(s<3600)return`${Math.max(1,Math.floor(s/60))} phút trước`;if(s<86400)return`${Math.floor(s/3600)} giờ trước`;return`${Math.floor(s/86400)} ngày trước`;};
const careerName=(api,id)=>{const c=api.content?.catalogue?.find(x=>x.id===id);return c?.short||c?.name||id;};

const statsState=ui=>ui.stats??={range:7,byRange:{},busy:false,error:null};

/* ---- data ---------------------------------------------------------------- */
function load(env,fresh=false){
  const {api,ui}=env,st=statsState(ui),range=st.range;
  if(st.busy)return;
  st.busy=true;st.error=null;
  api.json(`/api/admin/stats?range=${range}${fresh?'&fresh=1':''}`,{headers:{'X-Game-CSRF':api.csrf}},30000)
    .then(d=>{st.byRange[range]={data:d,at:Date.now()};})
    .catch(e=>{st.error={status:e.status||0,message:e.status?e.message:'Mất kết nối máy chủ. Thử lại sau nhé.'};})
    .finally(()=>{st.busy=false;if(ui.view==='gopy'&&ui.fb?.tab==='stats')env.renderSheet();});
}

/* ---- small parts ---------------------------------------------------------- */
function kpi(label,value,sub,extra=''){
  return `<div class="as-kpi"${extra}><span class="as-kpi-label">${label}</span><b class="as-kpi-num">${value}</b>${sub?`<small>${sub}</small>`:''}</div>`;
}
function kv(rows){
  return `<dl class="as-kv">${rows.filter(Boolean).map(([k,v])=>`<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>`;
}
function section(title,body,note=''){
  return `<section class="as-sec"><h3 class="as-h">${title}</h3>${body}${note?`<p class="as-note">${note}</p>`:''}</section>`;
}
/** Single-series columns over days; one hit target per day with a native tooltip. */
function columns(values,days,title,tone){
  const n=values.length,max=Math.max(1,...values),W=n*10,H=64,total=values.reduce((a,b)=>a+b,0);
  // Hit targets first (full height, hover tint behind the bar), then the bars on top.
  const hits=values.map((v,i)=>`<rect class="as-hit" x="${i*10}" y="0" width="10" height="${H}"><title>${dm(days[i])}: ${num(v)}</title></rect>`).join('');
  const bars=hits+values.map((v,i)=>{
    const h=v?Math.max(1.5,v/max*(H-2)):0,x=i*10+(n>40?1:1.6),w=n>40?8:6.8;
    return h?`<rect class="as-col" x="${x}" y="${H-h}" width="${w}" height="${h}"/>`:'';
  }).join('');
  return `<figure class="as-chart ${tone}"><figcaption><b>${title}</b><span>tổng ${num(total)} · cao nhất ${num(Math.max(0,...values))}</span></figcaption>
    <div class="as-plot"><span class="as-max" aria-hidden="true">${num(max)}</span><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(title)}: hôm nay ${num(last(values))}, cao nhất ${num(max)}"><line class="as-grid" x1="0" x2="${W}" y1="0.5" y2="0.5"/>${bars}<line class="as-base" x1="0" x2="${W}" y1="${H-.5}" y2="${H-.5}"/></svg></div>
    <div class="as-axis" aria-hidden="true"><span>${dm(days[0])}</span><span>${n>7?dm(days[Math.floor(n/2)]):''}</span><span>hôm nay</span></div></figure>`;
}
/** Horizontal bars: rows of {label, n, sub?}; the bar length is relative to the largest row. */
function hbars(rows,{total=null,tone='',compact=false}={}){
  if(!rows.length)return '<p class="as-note">Chưa có số liệu.</p>';
  const max=Math.max(1,...rows.map(r=>r.n));
  return `<ul class="as-hbars ${tone}${compact?' compact':''}">${rows.map(r=>`<li><span class="as-hl">${r.label}</span><b class="as-hv">${num(r.n)}${total?` <small>${share(r.n,total)}</small>`:''}</b><span class="as-track" aria-hidden="true"><i style="width:${Math.max(r.n?2:0,Math.round(100*r.n/max))}%"></i></span>${r.sub?`<small class="as-hs">${r.sub}</small>`:''}</li>`).join('')}</ul>`;
}
function dailyTable(p){
  const rows=p.days.map((d,i)=>`<tr><td>${dm(d)}</td><td>${num(p.dau[i])}</td><td>${num(p.new_players[i])}</td><td>${num(p.new_sessions[i])}</td><td>${num(p.new_accounts[i])}</td></tr>`).reverse().join('');
  return `<details class="as-details"><summary>Bảng số theo ngày</summary><div class="as-scroll"><table class="as-table"><thead><tr><th>Ngày</th><th>Hoạt động</th><th>Mới chơi</th><th>Mở trang</th><th>Tài khoản</th></tr></thead><tbody>${rows}</tbody></table></div></details>`;
}

/* ---- sections ------------------------------------------------------------- */
function playersSec(d){
  const p=d.players,r=p.retention;
  const since=p.tracked_since?`Số theo ngày đếm từ ${dm(p.tracked_since)}; trước đó chỉ biết lần chơi cuối của mỗi lượt.`:'Số theo ngày bắt đầu đếm từ hôm nay.';
  return section('Người chơi',
    `<div class="as-charts">${columns(p.dau,p.days,'Hoạt động mỗi ngày','')}${columns(p.new_players,p.days,'Người mới mỗi ngày','second')}</div>
    ${kv([['Hoạt động 7 ngày',num(p.wau)],['Hoạt động 30 ngày',num(p.mau)],
      ['Giữ chân D1',`${pct(r.d1)} <small>/${num(r.d1_n)}</small>`],['Giữ chân D7',`${pct(r.d7)} <small>/${num(r.d7_n)}</small>`],
      ['Đã chơi',num(p.played)],['Lượt mở trang',num(p.total)],['Tài khoản',num(p.accounts)],['Khách đã chơi',num(p.guests)]])}
    ${dailyTable(p)}`,
    `${since} Giữ chân D1/D7: người bắt đầu chơi trong ${r.window} ngày qua có quay lại đúng 1/7 ngày sau.`);
}
function careersSec(d,api){
  const pl=d.play,rows=pl.careers.map(c=>({label:esc(careerName(api,c.id)),n:c.players,sub:`${num(c.days)} ngày chơi · cấp TB ${dec(c.avg_level)}`}));
  return section('Nghề được chơi nhiều',hbars(rows),pl.careers_total>pl.careers.length?`Hiện ${pl.careers.length}/${pl.careers_total} nghề.`:'');
}
function playSec(d){
  const pl=d.play,n=pl.sample;
  const lang=pl.lang.map(x=>({label:esc(LANG[x.key]||x.key),n:x.n}));
  const theme=pl.theme.map(x=>({label:esc(THEME[x.key]||x.key),n:x.n}));
  const ch=pl.chapters.map(x=>({label:`Chương ${esc(x.key)}`,n:x.n}));
  const lv=pl.levels.map(x=>({label:`Cấp ${esc(x.key)}`,n:x.n}));
  return section('Cách chơi',
    kv([['Ngày đời trung bình',dec(pl.life_day.avg)],['Trung vị · p90',`${dec(pl.life_day.median)} · ${dec(pl.life_day.p90)}`],
      ['Chế độ câu chuyện',`${num(pl.story)} <small>${share(pl.story,n)}</small>`],['Bật nhân vật AI',`${num(pl.ai_on)} <small>${share(pl.ai_on,n)}</small>`],
      ['Bật nhạc',`${num(pl.music_on)} <small>${share(pl.music_on,n)}</small>`]])+
    `<div class="as-grid2"><div><h4 class="as-sub">Chương đang ở</h4>${hbars(ch,{total:pl.story,compact:true})}</div><div><h4 class="as-sub">Cấp nghề cao nhất</h4>${hbars(lv,{total:lv.reduce((a,b)=>a+b.n,0),compact:true})}</div>
      <div><h4 class="as-sub">Ngôn ngữ</h4>${hbars(lang,{total:n,tone:'second',compact:true})}</div><div><h4 class="as-sub">Giao diện</h4>${hbars(theme,{total:n,tone:'second',compact:true})}</div></div>`);
}
function economySec(d){
  const e=d.economy,n=e.sample;
  return section('Kinh tế',
    kv([['Ví trung vị',`${num(e.wallet.median)} xu`],['Ví p90',`${num(e.wallet.p90)} xu`],['Ví trung bình',`${dec(e.wallet.avg)} xu`],
      ['Đang nợ',`${num(e.debt)} <small>${share(e.debt,n)}</small>`],['Có đầu tư',`${num(e.investors)} <small>${share(e.investors,n)}</small>`],
      ['Mất vì lừa đảo',`${num(e.scam_lost)} xu`],['Người bị lừa',num(e.scam_victims)],['Lượt sa bẫy',num(e.scam_joined)]])+
    `<h4 class="as-sub">Số xu trong ví</h4>${hbars(e.buckets.map(b=>({label:esc(b.label),n:b.n})),{total:n,compact:true})}`);
}
function lifeSec(d){
  const L=d.life,B=d.board;
  if(!L.saves&&!B.saves)return section('Đời sống & Nhóm cư dân','<p class="as-note">Chưa lượt chơi nào có hai phần này.</p>');
  return section('Đời sống & Nhóm cư dân',
    kv([['Có “Chuyện đời”',num(L.saves)],['Tinh thần TB',dec(L.avg_spirit)],['Lần đi chơi',num(L.outings)],['Lần gặp lừa',num(L.scams)],['Tin đồn',num(L.rumours)],
      ['Có Nhóm cư dân',num(B.saves)],['Người đã đăng bài',num(B.active)],['Bài · trả lời',`${num(B.player_posts)} · ${num(B.player_replies)}`],['Lượt thả cảm xúc',num(B.reacts)]]));
}
function feedbackSec(d){
  const f=d.feedback;
  const head=`<tr><th>Loại</th>${Object.values(STATUS).map(([l])=>`<th>${l}</th>`).join('')}</tr>`;
  const rows=f.kinds.map(k=>{const [,emo,label]=KINDS.find(x=>x[0]===k.kind)||['', '', k.kind];return `<tr><td><span aria-hidden="true">${emo}</span> ${esc(label)}</td><td>${num(k.new)}</td><td>${num(k.seen)}</td><td>${num(k.done)}</td></tr>`;}).join('');
  const newest=f.newest.length?`<ul class="as-fb">${f.newest.map(it=>{const [,emo,label]=KINDS.find(x=>x[0]===it.kind)||['','',it.kind],[st,cls]=STATUS[it.status]||STATUS.new;
    return `<li><span class="as-fb-top"><span><span aria-hidden="true">${emo}</span> ${esc(label)}</span><span class="tag ${cls}">${st}</span><small>${ago(it.created_at)}</small></span><span class="as-fb-text" data-no-translate>${esc(it.text)}</span></li>`;}).join('')}</ul>`:'<p class="as-note">Chưa có góp ý nào.</p>';
  return section('Góp ý',
    `<div class="as-scroll"><table class="as-table as-fbt"><thead>${head}</thead><tbody>${rows}</tbody></table></div>`+
    kv([['Đang mở',num(f.open)],['Chưa đọc',num(f.unread)],[`Mới trong ${d.range} ngày`,num(f.in_range)],['Chờ được đọc',`${hours(f.ack.median_h)} <small>TB ${hours(f.ack.avg_h)}</small>`]])+
    `<h4 class="as-sub">5 góp ý mới nhất</h4>${newest}<button type="button" class="btn ghost small as-go" data-action="fbTab" data-tab="inbox">${icon('inbox',15)} Mở hộp góp ý</button>`);
}
function aiSec(d){
  const a=d.ai,t=a.total;
  const days=a.days.slice(-7).reverse().map(r=>`<tr><td>${dm(r.day)}</td><td>${num(r.calls)}</td><td>${num(r.ok)}</td><td>${num(r.failed+r.busy)}</td><td>${num(r.rejected)}</td><td>${num(r.guard)}</td></tr>`).join('');
  return section('AI <small>từ lúc khởi động</small>',
    (a.configured?'':`<div class="notice amber">${icon('alert',16)}<div>Máy chủ chưa cấu hình AI: nhân vật dùng lời có sẵn.</div></div>`)+
    kv([['Lượt gọi',num(t.calls)],['Thành công',`${num(t.ok)} <small>${share(t.ok,t.calls)}</small>`],['Lỗi · bận',`${num(t.failed)} · ${num(t.busy)}`],
      ['Câu AI bị lọc',num(t.rejected)],['Chặn lời lẽ xấu',num(t.guard)]])+
    (days?`<div class="as-scroll"><table class="as-table"><thead><tr><th>Ngày</th><th>Gọi</th><th>Được</th><th>Lỗi</th><th>Lọc</th><th>Chặn</th></tr></thead><tbody>${days}</tbody></table></div>`:''),
    `Đếm trong bộ nhớ từ ${clock(a.since)} ${dm(new Date(a.since*1000).toISOString().slice(0,10))}; khởi động lại máy chủ thì về 0.`);
}
function serverSec(d){
  const s=d.server;
  const tables=s.tables.map(t=>`<tr><td data-no-translate>${esc(t.name)}</td><td>${num(t.rows)}</td></tr>`).join('');
  return section('Máy chủ',
    kv([['Phiên bản',`v${esc(s.version)}`],['Chạy liên tục',span(s.uptime)],['Dung lượng dữ liệu',bytes(s.db_bytes)],['Chế độ câu chuyện',s.story?'bật':'tắt'],
      ['Python · PostgreSQL',`${esc(s.python)} · ${esc(s.database||'PostgreSQL')}`],['Tính số liệu',`${dec(d.took_ms)} ms`]])+
    `<details class="as-details"><summary>Số dòng mỗi bảng</summary><div class="as-scroll"><table class="as-table"><thead><tr><th>Bảng</th><th>Dòng</th></tr></thead><tbody>${tables}</tbody></table></div></details>`);
}

/* ---- page ------------------------------------------------------------------- */
export function statsView(env){
  const {api,ui}=env,st=statsState(ui),entry=st.byRange[st.range],d=entry?.data;
  if(!st.busy&&!st.error&&(!entry||Date.now()-entry.at>STALE_MS))load(env);
  const bar=`<div class="as-bar"><div class="segmented as-range" role="radiogroup" aria-label="Khoảng thời gian">${RANGES.map(n=>`<button type="button" role="radio" aria-checked="${st.range===n}" class="${st.range===n?'active':''}" data-action="asRange" data-range="${n}">${n} ngày</button>`).join('')}</div>
    <button type="button" class="btn ghost small as-refresh" data-action="asRefresh"${st.busy?' disabled':''}>${icon('refresh',15)}<span>${st.busy?'Đang tải…':'Làm mới'}</span></button></div>`;
  let body;
  if(st.error&&st.error.status===403)body=`<div class="notice danger">${icon('lock',17)}<div>Chỉ tài khoản vận hành xem được thống kê. Đăng nhập đúng tài khoản rồi mở lại nhé.</div></div>`;
  else if(st.error&&!d)body=`<div class="notice danger">${icon('alert',17)}<div>${esc(st.error.message)}<br><button type="button" class="btn small ghost" data-action="asRefresh">Thử lại</button></div></div>`;
  else if(!d)body=`<div class="as-loading" role="status">${icon('sparkle',24)}<p class="muted">Đang tính số liệu…</p></div>`;
  else{
    const p=d.players,f=d.feedback;
    const meta=`Cập nhật ${clock(d.generated_at)} · mẫu ${num(d.sample.size)} lượt chơi gần nhất${d.sample.size>=d.sample.limit?'':` (tối đa ${num(d.sample.limit)})`}`;
    body=(st.error?`<div class="notice amber">${icon('alert',16)}<div>${esc(st.error.message)} Đang hiện số liệu cũ.</div></div>`:'')+
      `<p class="as-meta">${meta}</p>
      <div class="as-kpis">${kpi('Hoạt động hôm nay',num(last(p.dau)),`7 ngày ${num(p.wau)} · 30 ngày ${num(p.mau)}`)}${kpi('Mới hôm nay',num(last(p.new_players)),`${num(last(p.new_sessions))} lượt mở · ${num(last(p.new_accounts))} tài khoản`)}${kpi('Người chơi',num(p.played),`${num(p.account_saves)} tài khoản · ${num(p.guests)} khách`)}
        <button type="button" class="as-kpi as-kpi-btn${f.unread?' hot':''}" data-action="fbTab" data-tab="inbox"><span class="as-kpi-label">Góp ý đang mở</span><b class="as-kpi-num">${num(f.open)}</b><small>${num(f.unread)} chưa đọc ${icon('chevron',12)}</small></button></div>`+
      playersSec(d)+careersSec(d,api)+playSec(d)+economySec(d)+lifeSec(d)+feedbackSec(d)+aiSec(d)+serverSec(d)+
      `<p class="as-meta as-foot">Số về cách chơi, kinh tế, đời sống lấy từ mẫu ${num(d.sample.size)} lượt chơi có thao tác gần nhất. Không chứa tên, mã phiên hay thông tin liên lạc.</p>`;
  }
  return `<section class="as${st.busy&&d?' is-busy':''}" aria-busy="${st.busy}">${bar}${body}</section>`;
}

export function statsAction(action,data,el,env){
  const st=statsState(env.ui);
  switch(action){
    case'asRange':{const n=Number(data.range);if(!RANGES.includes(n)||n===st.range)return true;st.range=n;st.error=null;env.renderSheet();return true;}
    case'asRefresh':st.error=null;load(env,true);env.renderSheet();return true;
  }
  return false;
}
