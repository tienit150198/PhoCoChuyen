/** The parts of the operator page that need more than the first-screen summary, loaded
 * with `import()` only when one of them is shown:
 *  - the save-derived cards of "Tổng quan" (GET /api/admin/stats/section?name=saves);
 *  - "Thời gian chơi" (…?name=playtime: small day tables kept by a trigger, never the saves);
 *  - the "Hệ thống" view (…?name=system, plus the summary and the sample facts).
 * Aggregates only: no names, session ids or contact details. */
import {esc,icon,num,dec,pct,share,stamp,bytes,span,tag,hm,ago,dm} from './ui.js';
import {kpi,kv,card,table,moreButton,savesFresh} from './stats.js';

const THEME={kem:'Kem sữa',tra_xanh:'Trà xanh',bien:'Biển chiều',keo:'Kẹo ngọt',dem:'Phố đêm'};
const LANG={vi:'Tiếng Việt',en:'English'};

/** Horizontal bars: {label, n, sub?}; length relative to the largest row. */
function hbars(rows,{total=null,tone='',compact=false}={}){
  if(!rows.length)return '<p class="note">Chưa có số liệu.</p>';
  const max=Math.max(1,...rows.map(r=>r.n));
  return `<ul class="hbars ${tone}${compact?' compact':''}">${rows.map(r=>`<li><span class="hl">${r.label}</span><b class="hv">${num(r.n)}${total?` <small>${share(r.n,total)}</small>`:''}</b><span class="track" aria-hidden="true"><i style="width:${Math.max(r.n?2:0,Math.round(100*r.n/max))}%"></i></span>${r.sub?`<small class="hs">${r.sub}</small>`:''}</li>`).join('')}</ul>`;
}

function careersCard(d,name,more){
  const pl=d.play,all=pl.careers.map(c=>({label:esc(name(c.id)),n:c.players,sub:`${num(c.days)} ngày chơi · cấp TB ${dec(c.avg_level)}`}));
  const shown=Math.min(all.length,more.careers);
  return card('Nghề được chơi nhiều',hbars(all.slice(0,shown))+moreButton('careers',shown,all.length),
    {note:pl.careers_total>pl.careers.length?`Hiện ${pl.careers.length}/${pl.careers_total} nghề.`:''});
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

/** The four save-derived cards of "Tổng quan" plus the sample footnote. */
export function savesCards(d,name,more){
  return {head:savesFresh(d),careers:careersCard(d,name,more),economy:economyCard(d),play:playCard(d),life:lifeCard(d),
    foot:`<p class="foot">Số về cách chơi, kinh tế, đời sống lấy từ mẫu ${num(d.sample.size)} lượt chơi có thao tác gần nhất (tối đa ${num(d.sample.limit)}), cập nhật ${stamp(d.generated_at)}. Không chứa tên, mã phiên hay thông tin liên lạc.</p>`};
}

/* ---- Thời gian chơi (…/section?name=playtime) ------------------------------------------- */
const PERIODS={today:'Hôm nay',yesterday:'Hôm qua',d7:'7 ngày',d30:'30 ngày'};
const nf1=new Intl.NumberFormat('vi-VN',{minimumFractionDigits:1,maximumFractionDigits:1});
const m1=v=>v==null?'—':nf1.format(v);   // minutes always with one decimal: 8,0 next to 8,1
const mins=v=>v==null?'—':`${m1(v)} phút`;
const big=v=>v==null?'—':`${m1(v)}<small class="unit"> phút</small>`;
/** Exact (counted by the trigger), estimated (seeded from receipts) or not all days counted yet. */
function periodTag(p){
  const part=p.partial?(p.days>1?tag(`${p.tracked}/${p.days} ngày`,'info'):tag('chưa đủ ngày','info')):'';
  if(p.estimated.length)return tag('ước tính','warn')+(part&&p.days>1?`<br>${part}`:'');
  return part||tag('chính xác','good');
}
/** 24 columns: players active in each hour of the day (average of the last finished days). */
function hourChart(h){
  const v=h.avg,max=Math.max(1,...v),peak=v.indexOf(Math.max(...v));
  const bars=v.map((n,i)=>`<span class="bar${i===peak&&n?' peak':''}" data-tip="${i}h: ${dec(n)} người"><i style="height:${n?Math.max(2,Math.round(1000*n/max)/10):0}%"></i></span>`).join('');
  const when=h.days?`TB ${num(h.days)} ngày${h.start&&h.end&&h.start!==h.end?` ${dm(h.start)}–${dm(h.end)}`:''}`:'chưa có';
  return `<figure class="chart hours"><figcaption><b>Người chơi theo giờ</b><span>${when}${Math.max(...v)?` · đông nhất ${peak}h`:''}</span></figcaption>
    <div class="plot"><span class="plot-max" aria-hidden="true">${dec(max)}</span><div class="bars" role="img" aria-label="Người chơi theo giờ, đông nhất lúc ${peak} giờ: ${dec(v[peak])} người">${bars}</div></div>
    <div class="xaxis" aria-hidden="true"><span>0h</span><span>6h</span><span>12h</span><span>18h</span><span>23h</span></div></figure>`;
}
export function playtimeCard(d){
  const P=Object.fromEntries(d.periods.map(p=>[p.key,p])),w=P.d7,t=P.today,order=['today','yesterday','d7','d30'];
  const kpis=`<div class="kpis k4">
    ${kpi('Mỗi người/ngày',big(w.avg_min),`trung vị ${mins(w.median_min)} · 7 ngày`)}
    ${kpi('Mỗi lượt chơi',big(w.session_avg_min),`trung vị ${mins(w.session_median_min)} · ${dec(w.sessions_per_player)} lượt/người`)}
    ${kpi('Hôm nay',big(t.avg_min),`${num(t.player_days)} người · ${num(t.hours)} giờ chơi`)}
    ${kpi('Người mới',big(w.new.median_min),`ngày đầu, trung vị · ${pct(w.new.over_pct)} chơi > ${num(d.rule.new_over_min)} phút`)}
  </div>`;
  const row=(label,f,cls='')=>`<tr${cls?` class="${cls}"`:''}><td>${label}</td>${order.map(k=>`<td>${f(P[k])}</td>`).join('')}</tr>`;
  const head=`<tr><th></th>${order.map(k=>`<th>${PERIODS[k]}<br>${periodTag(P[k])}</th>`).join('')}</tr>`;
  const rows=[
    row('Người chơi<small>/ngày</small>',p=>num(p.players)),
    row('Phút/người',p=>m1(p.avg_min)),row('trung vị',p=>m1(p.median_min),'sub-row'),
    row('Phút/lượt',p=>m1(p.session_avg_min)),row('trung vị',p=>m1(p.session_median_min),'sub-row'),
    row('Lượt/người',p=>dec(p.sessions_per_player)),row('Giờ chơi',p=>num(p.hours)),
    `<tr class="grp"><td colspan="5">Người mới · ngày đầu</td></tr>`,
    row('Số người',p=>num(p.new.n)),row('Phút TB',p=>m1(p.new.avg_min)),row('trung vị',p=>m1(p.new.median_min),'sub-row'),
    row(`> ${num(d.rule.new_over_min)} phút`,p=>pct(p.new.over_pct)),
  ];
  const tbl=`<div class="scroll"><table class="tbl play-tbl"><thead>${head}</thead><tbody>${rows.join('')}</tbody></table></div>`;
  const bands=hbars(w.bands.map(b=>({label:`${esc(b.label)} phút`,n:b.n})),{total:w.player_days,compact:true});
  const est=d.estimated.length?` Ước tính (từ biên nhận${d.estimated.some(e=>e.capped)?`, thiếu phần cũ của ${num(d.estimated.reduce((a,e)=>a+e.capped,0))} lượt chơi nhiều`:''}): ${d.estimated.map(e=>dm(e.day)).join(', ')}.`:'';
  const since=d.since.day&&!d.since.estimated&&d.since.at?` Đo từ ${hm(d.since.at)}${d.since.day!==d.today?'':' hôm nay'}.`:'';
  return card('Thời gian chơi',kpis+`<div class="play-grid"><div>${tbl}</div><div class="play-side">
      <div><h3 class="sub">Phút mỗi người/ngày · 7 ngày</h3>${bands}</div>${hourChart(d.hours)}</div></div>`,
    {cls:'wide play',note:`Một lượt: các thao tác cách nhau ≤ ${num(d.rule.gap_min)} phút, cộng ${num(d.rule.tail_min)} phút sau thao tác cuối.${since}${est}`});
}

/* ---- Hệ thống ---------------------------------------------------------------------------- */
/** `top`: the summary; `sys`: the system section (table rows); `sv`: the saves section or null. */
export function systemView(top,sys,sv,api,more){
  const s={...top.server,...sys.server},tables=[...s.tables].sort((a,b)=>b.rows-a.rows||a.name.localeCompare(b.name));
  const pg=/^PostgreSQL/.test(s.database||''),dbName=esc(s.database||`SQLite ${s.sqlite}`),approx=tables.some(t=>t.approx);
  const total=tables.reduce((a,t)=>a+t.rows,0),max=Math.max(1,...tables.map(t=>t.rows)),shown=Math.min(tables.length,more.tables);
  const rows=tables.slice(0,shown).map(t=>`<tr><td><code>${esc(t.name)}</code></td><td>${t.approx?'≈ ':''}${num(t.rows)}</td><td class="share-cell"><div><span class="track" aria-hidden="true"><i style="width:${Math.max(t.rows?1:0,Math.round(100*t.rows/max))}%"></i></span><small>${share(t.rows,total)||'0%'}</small></div></td></tr>`);
  const kpis=`<div class="kpis k4">
    ${kpi('Phiên bản',`v${esc(s.version)}`,`Python ${esc(s.python)} · ${dbName}`,{ic:'sparkle'})}
    ${kpi('Chạy liên tục',span(s.uptime),`từ ${stamp(s.started)}`,{ic:'clock'})}
    ${kpi('Dung lượng dữ liệu',bytes(s.db_bytes),pg?'cơ sở dữ liệu':'cơ sở dữ liệu + WAL',{ic:'server'})}
    ${kpi('Tổng số dòng',(approx?'≈ ':'')+num(total),`${num(tables.length)} bảng`,{ic:'chart'})}
  </div>`;
  const env=card('Môi trường',kv([
    ['Phiên bản game',`v${esc(s.version)}`],['Python',esc(s.python)],['Cơ sở dữ liệu',dbName],
    ['Chế độ câu chuyện',s.story?tag('bật','good'):tag('tắt')],['AI',top.ai.configured?tag('đã cấu hình','good'):tag('chưa cấu hình','warn')],
    ['Khởi động lúc',stamp(s.started)],
  ],'kv2'));
  const sample=sv?.sample,snap=sv?.snapshot||sys.snapshot,errors={...(sys.errors||{}),...(sv?.errors||{})};
  const job=snap?(snap.held?tag(snap.reason==='busy'?'tạm giữ: máy chủ bận':'đang tạm giữ','warn'):snap.job==='running'?tag('đang chạy','good'):tag('nghỉ')):'—';
  const when=t=>t?`${hm(t)} <small>${ago(t)}</small>`:'—';
  const calc=card('Số liệu thống kê',kv([
    ['Tổng quan tính lúc',when(top.computed_at??top.generated_at)],['Thời gian tính',`${dec(top.took_ms)} ms${sv?` <small>+ mẫu ${dec(sv.took_ms)} ms</small>`:''}`],['Bộ nhớ đệm',top.stale?'bản tính nền':top.cached?`dùng bản ${dec(top.age)} giây trước`:'vừa tính mới'],
    ['Việc tính nền',job],['Bản lưu tính lúc',when(sv?.snapshot?.computed_at)],['Bảng dữ liệu tính lúc',when(sys.snapshot?.computed_at??sys.generated_at)],
    ['Mẫu lượt chơi',sample?`${num(sample.size)} <small>/ tối đa ${num(sample.limit)}</small>`:'—'],['Cách đọc mẫu',sample?(sample.engine==='sql'?(pg?'PostgreSQL jsonb':'SQLite JSON'):'Python (dự phòng)'):'—'],['Ngày (giờ VN)',esc(top.today)],
  ],'kv2')+Object.entries(errors).map(([k,e])=>`<div class="notice bad">${icon('alert',16)}<div>Lần tính “${esc(k)}” lúc ${hm(e.at)} bị lỗi: <code>${esc(e.error)}</code></div></div>`).join(''),
  {note:'Tóm tắt lưu đệm 30 giây, số trực tiếp 10 giây. Bảng dữ liệu tính nền 2 phút một lần; số liệu từ lượt chơi 30 phút một lần, trên mẫu lượt chơi gần nhất, và tạm giữ khi máy chủ bận để không làm chậm người chơi.'});
  const who=card('Phiên vận hành',kv([
    ['Đăng nhập với',`@${esc(api.account?.username||'')}`],['Tên hiển thị',esc(api.account?.display||'')],
  ],'kv2')+`<p class="note">Quyền vận hành đến từ biến môi trường <code>ADMIN_USERS</code> trên máy chủ và được kiểm tra lại ở mỗi lần gọi.</p>
    <button type="button" class="btn ghost sm" data-act="logout">${icon('exit',15)} Đăng xuất</button>`);
  return kpis+`<div class="cols"><div class="col">${card('Bảng dữ liệu',table(['Bảng','Số dòng','Tỉ lệ'],rows,'tables')+moreButton('tables',shown,tables.length),{note:approx?'Bảng lớn hiện số ước tính (≈) để không phải đếm hết.':'Số dòng đếm ở chế độ nền.'})}</div><div class="col">${env}${calc}${who}</div></div>`;
}
