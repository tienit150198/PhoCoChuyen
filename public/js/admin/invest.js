/** "📊 Tổng quan đầu tư" (GET /api/admin/stats/section?name=invest, game/admin_kpi.py): the numbers a buyer or a
 * franchisee asks for, by tab, with a period selector (7 / 30 / 90 days / all; complete Vietnam days only, today
 * shown apart), an ⓘ on every number (definition and formula, from the payload's `defs`) and the date each
 * counter started. Also the printable report (#bao-cao: one page per part, cells under 5 players hidden).
 * Aggregates only: no names, session ids or typed text. Imported on demand (main.js). */
import {esc,icon,num,dec,pct,dm,hm,stamp,bytes,span,tag,utcText} from './ui.js';
import {card,table,kv} from './stats.js';

export const TABS=[['tong','Tổng quan'],['tang-truong','Tăng trưởng'],['hoat-dong','Hoạt động'],['giu-chan','Giữ chân'],['gan-bo','Gắn bó'],
  ['kinh-te','Kinh tế'],['chat-luong','Chất lượng'],['nguon','Nguồn'],['ha-tang','Hạ tầng']];
export const PART={tong:'all','tang-truong':'growth','hoat-dong':'activity','giu-chan':'retention','gan-bo':'engagement','kinh-te':'economy',
  'chat-luong':'quality',nguon:'acquisition','ha-tang':'infra'};
export const PERIODS={7:'7 ngày',30:'30 ngày',90:'90 ngày',0:'Tất cả'};
const WD=['T2','T3','T4','T5','T6','T7','CN'];
const FEAT_ICON={work:'🧋',bank:'🏦',learn:'🎓',home:'🏠',wardrobe:'👗',needs:'🍜',board:'📋',life:'🌿',close:'🤝',story:'📖',fair:'🎪',jobs:'💼'};
const OS={android:'Android',ios:'iOS',windows:'Windows',mac:'macOS',linux:'Linux',chromeos:'ChromeOS',other:'Khác'};
const FORM={mobile:'Điện thoại',tablet:'Máy tính bảng',desktop:'Máy tính',other:'Khác'};
const LANG={vi:'Tiếng Việt',en:'English',other:'Khác'};

/* ---- numbers ------------------------------------------------------------------------------------ */
export function fmt(kind,v){
  if(v==null||Number.isNaN(v))return '—';
  switch(kind){
    case 'pct':return v>0&&v<0.1?`${v.toLocaleString('vi-VN',{maximumFractionDigits:3})}%`:pct(v);
    case 'xu':return `${num(v)} xu`;
    case 'ms':return `${num(v)} ms`;
    case 'min':return `${dec(v)} phút`;
    case 'num':return dec(v);
    default:return num(v);
  }
}
/** Every daily series of the payload by key (one axis: d.days). */
function seriesMap(d){
  return {...(d.growth?.series||{}),...(d.activity?.series||{}),...(d.economy?.series||{}),...(d.quality?.series||{}),...(d.engagement?.chat||{})};
}
/** A series summed up over the last `n` complete days (0: all) by its rule (DEFS agg), like admin_kpi._period. */
export function period(d,key,n,S=seriesMap(d)){
  const vals=S[key];if(!vals)return null;
  const rule=d.defs?.[key]?.agg||'last';
  let idx=d.days.map((x,i)=>x<d.today?i:-1).filter(i=>i>=0);
  if(n)idx=idx.slice(-n);
  const v=idx.map(i=>vals[i]).filter(x=>x!=null);
  if(!v.length)return null;
  if(rule==='sum')return v.reduce((a,b)=>a+b,0);
  if(rule==='max')return Math.max(...v);
  if(rule==='last')return v[v.length-1];
  const [kind,spec]=rule.split(':');
  if(kind==='wavg'){const w=S[spec]||[];let s=0,t=0;for(const i of idx)if(vals[i]!=null&&w[i]){s+=vals[i]*w[i];t+=w[i];}return t?Math.round(100*s/t)/100:null;}
  if(kind.startsWith('ratio')){
    const [a,b]=spec.split('/'),A=S[a]||[],B=S[b]||[],scale=kind==='ratio1'?1:kind==='ratio1000'?1000:100;let x=0,y=0;
    for(const i of idx)if(A[i]!=null&&B[i]){x+=A[i];y+=B[i];}
    return y?Math.round(100*scale*x/y)/100:null;
  }
  return Math.round(100*v.reduce((a,b)=>a+b,0)/v.length)/100;
}
/** The visible window of the axis: the last `n` days (today included), or all. */
const windowIdx=(d,n)=>{const all=d.days.map((_,i)=>i);return n?all.slice(-n-1):all;};
const def=(d,key)=>d.defs?.[key]||{label:key,d:'',f:'',kind:'n'};

/* ---- parts ---------------------------------------------------------------------------------------- */
export function infoBtn(d,key){
  const x=def(d,key);
  const text=`${x.label}\n${x.d}${x.f?`\nCách tính: ${x.f}`:''}`;
  return `<button type="button" class="info" data-act="info" data-tip="${esc(text)}" aria-label="${esc('Giải thích: '+x.label)}">${icon('info',14)}</button>`;
}
/** "từ dd/mm" for a number whose collection started later than the game. */
function sinceTag(d,key){
  const s=def(d,key).since;if(!s)return '';
  const at=d.meta?.since?.[s];
  if(at&&d.meta?.tracked_since&&at<=d.meta.tracked_since)return '';  // as old as the day log itself: nothing to flag
  return at?`<span class="since" title="Đang thu thập từ ${dm(at)}">từ ${dm(at)}</span>`:`<span class="since warn">chưa có số liệu</span>`;
}
/** A small line chart of a series (gaps where null). */
export function spark(values,{w=120,h=28}={}){
  const pts=values.map((v,i)=>[i,v]).filter(p=>p[1]!=null);
  if(pts.length<2)return '';
  const max=Math.max(...pts.map(p=>p[1])),min=Math.min(0,...pts.map(p=>p[1])),n=Math.max(1,values.length-1),r=max-min||1;
  let path='',prev=-2;
  for(const [i,v] of pts){const x=(i/n*w).toFixed(1),y=(h-2-(v-min)/r*(h-4)).toFixed(1);path+=`${i===prev+1?'L':'M'}${x} ${y}`;prev=i;}
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><path d="${path}"/></svg>`;
}
function smallN(d,n){
  if(n==null)return '';
  if(n<d.small)return ` ${tag(`n=${num(n)} · quá ít`,'warn')}`;
  if(n<d.few)return ` ${tag(`ít dữ liệu · n=${num(n)}`,'info')}`;
  return '';
}
/** One number card: label + ⓘ, value, a sub line, the series' sparkline over the window, small-n flag. */
export function metric(d,key,value,{sub='',series=null,n=null,ci=null,win=null,text=null}={}){
  const x=def(d,key);
  const sp=series?spark((win||series.map((_,i)=>i)).filter(i=>d.days[i]<d.today).map(i=>series[i])):'';  // finished days only
  const civ=ci?`<small class="ci">khoảng tin cậy 95%: <span class="nw">${dec(ci[0])}–${dec(ci[1])}%</span></small>`:'';
  return `<div class="kpi m"><span class="kpi-label">${esc(x.label)}${infoBtn(d,key)}</span><b class="kpi-num">${text??fmt(x.kind,value)}</b>${sub?`<small class="kpi-sub">${sub}</small>`:''}${civ}<span class="m-foot">${sp}${sinceTag(d,key)}${smallN(d,n)}</span></div>`;
}
/** Daily columns over the window; today lighter (not over); a null day is empty with "chưa có" in its tip. */
export function columns(d,key,win,{tone=''}={}){
  const x=def(d,key),S=seriesMap(d),vals=S[key]||[],v=win.map(i=>vals[i]);
  const nums=v.filter(a=>a!=null),max=Math.max(1,...nums.map(Math.abs));
  const bars=win.map((i,j)=>{const a=v[j],today=d.days[i]===d.today;
    return `<span class="bar${today?' today':''}${a!=null&&a<0?' neg':''}" data-tip="${today?'Hôm nay (chưa hết ngày)':dm(d.days[i])}: ${a==null?'chưa có':esc(fmt(x.kind,a))}"><i style="height:${a?Math.max(2,Math.round(1000*Math.abs(a)/max)/10):0}%"></i></span>`;}).join('');
  const last=win.length?vals[win[win.length-1]]:null;
  return `<figure class="chart ${tone}"><figcaption><b>${esc(x.label)} ${infoBtn(d,key)}</b><span>cao nhất ${fmt(x.kind,nums.length?Math.max(...nums):null)} · hôm nay ${fmt(x.kind,last)}</span></figcaption>
    <div class="plot"><span class="plot-max" aria-hidden="true">${fmt(x.kind,max)}</span><div class="bars${win.length>40?' dense':''}" role="img" aria-label="${esc(x.label)}">${bars}</div></div>
    <div class="xaxis" aria-hidden="true"><span>${win.length?dm(d.days[win[0]]):''}</span><span>${win.length>7?dm(d.days[win[Math.floor(win.length/2)]]):''}</span><span>hôm nay</span></div></figure>`;
}
function notices(d){
  const out=[];
  const errs=Object.keys(d.errors||{});
  if(errs.length)out.push(`<div class="notice warn">${icon('alert',16)}<div>Chưa tính được: ${errs.map(e=>`<code>${esc(e)}</code>`).join(', ')} (hết thời gian cho phép hoặc lỗi). Phần đó để trống, không đoán số; lần tính sau (mỗi 10 phút) sẽ thử lại.</div></div>`);
  return out.join('');
}
function heat(v,max,tone='second'){
  if(v==null)return '<td class="na">·</td>';
  const a=max?Math.min(70,Math.round(70*v/max)):0;
  return `<td class="heat" style="background:color-mix(in srgb,var(--${tone}) ${a}%,transparent)">${v>=10?num(v):dec(v)}</td>`;
}

/* ---- tabs ---------------------------------------------------------------------------------------------- */
function overview(d,ui){
  const S=seriesMap(d),n=Number(ui.period),win=windowIdx(d,n),P=k=>period(d,k,n,S),pl=PERIODS[ui.period];
  const g=d.growth||{},r=d.retention||{},tot=g.totals||{},m=d.meta||{};
  const curve=k=>(r.curve||[]).find(c=>c.k===k)||{};
  const c1=curve(1),c7=curve(7),c30=curve(30),conv=r.conversion||{};
  const daysOfData=m.tracked_since?Math.round((Date.parse(d.today)-Date.parse(m.tracked_since))/86400000):0;
  const cards=[
    metric(d,'players_total',tot.players_total,{sub:`${num(tot.accounts_total)} tài khoản · ${num(tot.guests_played)} khách`,series:S.cum_players,win}),
    metric(d,'new_players',P('new_players'),{sub:`${pl} đã qua`,series:S.new_players,win}),
    metric(d,'dau',P('dau'),{sub:`trung bình ${pl}`,series:S.dau,win}),
    metric(d,'mau',P('mau'),{sub:'hết hôm qua',series:S.mau,win}),
    metric(d,'stickiness',P('stickiness'),{sub:`trung bình ${pl}`,series:S.stickiness,win}),
    metric(d,'avg_min',P('avg_min'),{sub:`trung bình ${pl}`,series:S.avg_min,win}),
    metric(d,'d1',c1.pct,{sub:`${num(c1.n)} người · ${num(c1.cohorts)} ngày bắt đầu`,n:c1.n,ci:c1.ci}),
    metric(d,'d7',c7.pct,{sub:`${num(c7.n)} người`,n:c7.n,ci:c7.ci}),
    metric(d,'d30',c30.pct,{sub:c30.n?`${num(c30.n)} người`:'chưa đủ 30 ngày',n:c30.n,ci:c30.ci}),
    metric(d,'conversion',conv.pct,{sub:`${num(conv.n)} người mới 30 ngày`,n:conv.n,ci:conv.ci}),
    metric(d,'xu_net',P('xu_net'),{sub:`${pl} đã qua`,series:S.xu_net,win}),
    metric(d,'lat_p95',P('lat_p95'),{sub:`trung bình ${pl}`,series:S.lat_p95,win}),
    metric(d,'uptime',P('uptime'),{sub:`${pl} đã qua`,series:S.uptime,win}),
    `<div class="kpi m rev"><span class="kpi-label">${esc(def(d,'revenue').label)}${infoBtn(d,'revenue')}</span><b class="kpi-num">Chưa bật</b><small class="kpi-sub">${esc(d.economy?.revenue?.note||'')}</small></div>`,
  ];
  const facts=kv([
    ['Ra mắt (bản đầu)',m.launch?dm(m.launch)+'/'+m.launch.slice(0,4):'—'],['Nhật ký ngày từ',m.tracked_since?dm(m.tracked_since):'—'],
    ['Số ngày có số liệu',num(daysOfData+1)],['Phiên bản',`v${esc(m.version||'')}`],['Bộ đếm mới từ',m.counters_since?dm(m.counters_since):'hôm nay'],
    ['Số liệu lúc',hm(d.generated_at)]],'kv3');
  const warn=daysOfData<30?`<div class="notice info">${icon('clock',16)}<div>Game mới có <b>${num(daysOfData+1)} ngày</b> số liệu theo ngày. Giữ chân D7/D30 và xu hướng tháng cần thêm thời gian; các ô có ${tag('ít dữ liệu','info')} nên đọc như tín hiệu sớm, chưa phải con số ổn định.</div></div>`:'';
  return notices(d)+warn+`<div class="kpis inv">${cards.join('')}</div>`+
    `<div class="charts two">${columns(d,'dau',win)}${columns(d,'new_players',win,{tone:'second'})}</div>`+
    card('Về số liệu này',facts+`<p class="note">Mọi ngày là ngày giờ Việt Nam (00:00–24:00, UTC+7). Khoảng "${pl}" chỉ tính các ngày đã kết thúc; hôm nay hiện riêng trên biểu đồ. Bấm ${icon('info',12)} để xem định nghĩa và cách tính. Không có tên, mã phiên hay chữ người chơi gõ.</p>`);
}
function growthTab(d,ui){
  const g=d.growth;if(!g)return notices(d);
  const S=seriesMap(d),n=Number(ui.period),win=windowIdx(d,n),P=k=>period(d,k,n,S),t=g.totals,pl=PERIODS[ui.period];
  const cmp=(k)=>['7','30'].map(w=>{const c=g.compare?.[w]?.[k]||{};return `<td>${num(c.now)}</td><td>${c.growth==null?'—':`${c.growth>0?'+':''}${dec(c.growth)}%`}</td>`;}).join('');
  return notices(d)+`<div class="kpis inv">
      ${metric(d,'saves_total',t.saves_total,{sub:`${num(t.unplayed_migrated)} chưa từng thao tác (đã loại khỏi “đã chơi”)`})}
      ${metric(d,'players_total',t.players_total,{series:S.cum_players,win})}
      ${metric(d,'accounts_total',t.accounts_total,{sub:`${pct(t.account_rate)} người đã chơi`})}
      ${metric(d,'guests_played',t.guests_played)}
      ${metric(d,'new_sessions',P('new_sessions'),{sub:`${pl} đã qua`,series:S.new_sessions,win})}
      ${metric(d,'new_players',P('new_players'),{sub:`${pl} đã qua`,series:S.new_players,win})}
      ${metric(d,'activation',P('activation'),{sub:'người chơi mới ÷ lượt mở mới',series:S.activation,win})}
      ${metric(d,'new_accounts',P('new_accounts'),{sub:`${pl} đã qua`,series:S.new_accounts,win})}
    </div>`+
    `<div class="charts two">${columns(d,'new_players',win)}${columns(d,'cum_players',win,{tone:'second'})}${columns(d,'new_sessions',win)}${columns(d,'new_accounts',win,{tone:'second'})}</div>`+
    card('So với kỳ trước',`<div class="scroll"><table class="tbl"><thead><tr><th></th><th>7 ngày</th><th>so với 7 ngày trước</th><th>30 ngày</th><th>so với 30 ngày trước</th></tr></thead><tbody>
      ${['new_sessions','new_players','new_accounts'].map(k=>`<tr><td>${esc(def(d,k).label)}</td>${cmp(k)}</tr>`).join('')}</tbody></table></div>`,
      {note:'Chỉ ngày đã kết thúc. "—": kỳ trước chưa nằm trọn trong lịch sử số liệu.'});
}
function activityTab(d,ui){
  const a=d.activity;if(!a)return notices(d);
  const S=seriesMap(d),n=Number(ui.period),win=windowIdx(d,n),P=k=>period(d,k,n,S),pl=PERIODS[ui.period];
  const hm_=a.heatmap,max=Math.max(0,...hm_.grid.flat().filter(v=>v!=null));
  const grid=`<div class="scroll"><table class="tbl heatmap"><thead><tr><th></th>${Array.from({length:24},(_,h)=>`<th>${h}</th>`).join('')}</tr></thead><tbody>
    ${hm_.grid.map((row,w)=>`<tr><td>${WD[w]}</td>${row.map(v=>heat(v,max)).join('')}</tr>`).join('')}</tbody></table></div>`;
  return notices(d)+`<div class="kpis inv">
      ${metric(d,'dau',P('dau'),{sub:`trung bình ${pl}`,series:S.dau,win})}
      ${metric(d,'wau',P('wau'),{sub:'hết hôm qua',series:S.wau,win})}
      ${metric(d,'mau',P('mau'),{sub:'hết hôm qua',series:S.mau,win})}
      ${metric(d,'stickiness',P('stickiness'),{sub:`trung bình ${pl}`,series:S.stickiness,win})}
      ${metric(d,'returning',P('returning'),{sub:`trung bình ${pl}`,series:S.returning,win})}
      ${metric(d,'resurrected',P('resurrected'),{sub:`${pl} đã qua`,series:S.resurrected,win})}
      ${metric(d,'peak_online',P('peak_online'),{sub:`cao nhất ${pl}`,series:S.peak_online,win})}
      ${metric(d,'peak_cmd_min',P('peak_cmd_min'),{sub:`cao nhất ${pl}`,series:S.peak_cmd_min,win})}
      ${metric(d,'avg_min',P('avg_min'),{sub:`trung bình ${pl}`,series:S.avg_min,win})}
      ${metric(d,'median_min',P('median_min'),{sub:`trung bình ${pl}`,series:S.median_min,win})}
      ${metric(d,'sessions_pp',P('sessions_pp'),{sub:`trung bình ${pl}`,series:S.sessions_pp,win})}
      ${metric(d,'hours_total',P('hours_total'),{sub:`${pl} đã qua`,series:S.hours_total,win})}
    </div>`+
    `<div class="charts two">${columns(d,'dau',win)}${columns(d,'stickiness',win,{tone:'second'})}${columns(d,'avg_min',win)}${columns(d,'peak_online',win,{tone:'second'})}</div>`+
    card(`Giờ chơi trong tuần <small>${hm_.days?`TB ${num(hm_.days)} ngày ${hm_.start?dm(hm_.start):''}–${hm_.end?dm(hm_.end):''}`:'chưa có'}</small>`,grid,
      {note:`Số người có thao tác trong từng giờ (giờ Việt Nam), trung bình theo thứ trong tuần, các ngày đã qua gần nhất (tối đa 28).${hm_.peak_hour!=null?` Đông nhất lúc ${hm_.peak_hour}h.`:''}${a.estimated?.length?` Ngày ước tính: ${a.estimated.map(dm).join(', ')}.`:''}`});
}
function retentionTab(d,ui){
  const r=d.retention;if(!r)return notices(d);
  const row=c=>`<tr><td>D${c.k}</td><td>${c.n?pct(c.pct):'—'}${smallN(d,c.n)}</td><td>${c.ci?`${dec(c.ci[0])}–${dec(c.ci[1])}%`:'—'}</td><td>${num(c.n)}</td><td>${num(c.cohorts)}</td></tr>`;
  const curve=table(['Ngày','Quay lại','Tin cậy 95%','Người','Ngày bắt đầu'],r.curve.map(row));
  const all=table(['Ngày','Quay lại','Tin cậy 95%','Người','Ngày bắt đầu'],r.curve_all.map(row));
  const roll=table(['Ngày','Còn quay lại (k trở đi)','Tin cậy 95%','Người'],r.rolling.map(c=>`<tr><td>D${c.k}+</td><td>${c.n?pct(c.pct):'—'}${smallN(d,c.n)}</td><td>${c.ci?`${dec(c.ci[0])}–${dec(c.ci[1])}%`:'—'}</td><td>${num(c.n)}</td></tr>`));
  const W=r.weekly,first=W.rows.findIndex(x=>x.n>0),rows=first<0?[]:W.rows.slice(first),cols=rows.length;  // weeks before the first new player left out
  const tri=`<div class="scroll heat-wrap"><table class="tbl heat-tbl"><thead><tr><th>Tuần bắt đầu</th><th>Người</th>${Array.from({length:cols},(_,k)=>`<th>T${k}</th>`).join('')}</tr></thead><tbody>
    ${rows.map(x=>`<tr><td>${dm(x.week)}</td><td>${num(x.n)}</td>${Array.from({length:cols},(_,k)=>{const c=x.cells[k];if(!c)return '<td></td>';if(!x.n)return '<td class="na">·</td>';
      return `<td class="heat${c.partial?' part':''}" style="background:color-mix(in srgb,var(--second) ${Math.min(62,Math.round((c.pct||0)*.62))}%,transparent)" title="${c.partial?'tuần chưa hết':''}">${dec(c.pct)}</td>`;}).join('')}</tr>`).join('')}</tbody></table></div>`;
  const weeks=r.weeks.slice(-12).reverse().map(w=>`<tr><td>${dm(w.week)}${w.partial?' *':''}</td><td>${num(w.active)}</td><td>${num(w.new)}</td><td>${num(w.retained)}</td><td>${num(w.back)}</td><td>${num(w.churned)}</td><td>${pct(w.churn_pct)}</td></tr>`);
  const L=r.lifetime,conv=r.conversion;
  return notices(d)+`<div class="kpis inv">
      ${['d1','d3','d7','d14','d30'].map(k=>{const c=r.curve.find(x=>`d${x.k}`===k)||{};return metric(d,k,c.pct,{sub:c.n?`${num(c.n)} người`:'chưa đủ ngày',n:c.n,ci:c.ci});}).join('')}
      ${metric(d,'conversion',conv.pct,{sub:`${num(conv.accounts)}/${num(conv.n)} người mới 30 ngày`,n:conv.n,ci:conv.ci})}
      ${metric(d,'lifetime_days',L.avg_days,{sub:`trung bình · ${num(L.players)} người`})}
      ${metric(d,'wk_churn',r.weeks.length?r.weeks[r.weeks.length-1].churn_pct:null,{sub:r.weeks.length?`tuần ${dm(r.weeks[r.weeks.length-1].week)}`:'chưa đủ một tuần',n:r.weeks.length?r.weeks[r.weeks.length-1].prev:null})}
    </div>`+
    `<div class="cols"><div class="col">${card(`Đường giữ chân <small>60 ngày bắt đầu gần nhất</small>`,curve,{extra:infoBtn(d,'d1'),note:'Mỗi người chơi mới được tính một lần, ở ngày bắt đầu; chỉ các ngày bắt đầu đã đủ k ngày. Khoảng tin cậy Wilson 95%: càng ít người càng rộng.'})}
      ${card('Từ đầu (số đông cứng)',all,{note:'Cùng cách tính trên mọi ngày bắt đầu từ khi có nhật ký, đọc từ số đã đông cứng mỗi ngày (không đổi khi bản lưu bị xoá).'})}</div>
      <div class="col">${card('Giữ chân cuốn',roll,{extra:infoBtn(d,'rolling')})}
      ${card('Số ngày hoạt động mỗi người',table(['Số ngày','Người','%'],L.bands.map(b=>`<tr><td>${esc(b.label)}</td><td>${num(b.n)}</td><td>${pct(b.pct)}</td></tr>`)),{extra:infoBtn(d,'lifetime_days')})}</div></div>`+
    card('Nhóm theo tuần bắt đầu',tri,{cls:'wide',note:'% người chơi mới của tuần (thứ Hai–Chủ nhật) còn hoạt động ở tuần thứ k sau đó. T0 = tuần bắt đầu. Ô nhạt: tuần chưa hết.'})+
    card('Tăng trưởng theo tuần',weeks.length?table(['Tuần','Hoạt động','Mới','Ở lại','Trở lại','Rời đi','Tỉ lệ rời'],weeks):'<p class="note">Chưa hết tuần đầu tiên có số liệu.</p>',
      {cls:'wide',extra:infoBtn(d,'wk_churn'),note:'Hoạt động = mới + ở lại (cũng chơi tuần trước) + trở lại (nghỉ ≥ 1 tuần). Rời đi: chơi tuần trước, tuần này không. * tuần đầu: chưa có tuần trước để so.'});
}
function engagementTab(d,ui,name){
  const e=d.engagement;if(!e)return notices(d);
  const S=seriesMap(d),n=Number(ui.period),win=windowIdx(d,n),P=k=>period(d,k,n,S),pl=PERIODS[ui.period];
  const max=Math.max(1,...e.features.adoption.map(f=>f.pct||0));
  const feats=`<ul class="hbars">${e.features.adoption.map(f=>`<li><span class="hl">${FEAT_ICON[f.key]||'•'} ${esc(f.label)}</span><b class="hv">${pct(f.pct)}</b><span class="track" aria-hidden="true"><i style="width:${Math.round(100*(f.pct||0)/max)}%"></i></span></li>`).join('')}</ul>`;
  const careers=e.careers.slice(0,15).map(c=>`<tr><td>${esc(c.name||name(c.id))}</td><td>${num(c.players)}</td><td>${pct(c.mastered_pct)}</td><td>${dec(c.avg_days)}</td></tr>`);
  const ms=e.milestones.steps.map(s=>`<li><span class="hl">${esc(s.label)}</span><b class="hv">${pct(s.pct)} <small>${num(s.n)}</small></b><span class="track" aria-hidden="true"><i style="width:${Math.round(s.pct||0)}%"></i></span></li>`).join('');
  const so=e.social;
  return notices(d)+`<div class="kpis inv">
      ${metric(d,'board_players',e.board.players)}
      ${metric(d,'mastered_pct',e.board.mastered_pct,{sub:`${num(e.board.mastered)} người`,n:e.board.players})}
      ${metric(d,'work_days_median',e.board.work_days_median,{sub:`p90 ${dec(e.board.work_days_p90)} ngày`})}
      ${metric(d,'chat_share',P('chat_share'),{sub:`${pl} đã qua`,series:S.chat_share,win})}
      ${metric(d,'chat_msgs',P('chat_msgs'),{sub:`${pl} đã qua`,series:S.chat_msgs,win})}
      ${metric(d,'friend_pairs',so.friend_pairs,{sub:`${num(so.with_friend)} người có bạn`})}
      ${metric(d,'couples',so.couples,{sub:`${num(so.married)} đã cưới · ${num(so.weddings_done)} đám cưới`})}
      ${metric(d,'dates_30d',so.dates_30d)}
    </div>`+
    `<div class="cols"><div class="col">${card(`Dùng tính năng <small>${num(e.features.days)} ngày đã qua</small>`,feats,{extra:infoBtn(d,'feature'),note:'Trung bình mỗi ngày: người dùng nhóm thao tác ÷ người hoạt động. Thao tác xã hội (bạn bè, chat, hẹn hò) ở mục bên cạnh.'})}
      ${card('Nghề',careers.length?table(['Nghề','Người','Thành thạo','Ngày TB'],careers):'<p class="note">Chưa có.</p>',{note:'Người có tên trên bảng xếp hạng của nghề; thành thạo = lên cấp 3 ở nghề đó.'})}</div>
      <div class="col">${card(`Cột mốc <small>${num(e.milestones.created)} người mở game</small>`,`<ul class="hbars">${ms}</ul>`,{extra:infoBtn(d,'milestone')})}
      ${columns(d,'chat_senders',win,{tone:'second'})}</div></div>`;
}
function economyTab(d,ui){
  const e=d.economy;if(!e)return notices(d);
  const S=seriesMap(d),n=Number(ui.period),win=windowIdx(d,n),P=k=>period(d,k,n,S),pl=PERIODS[ui.period];
  const g=e.groups.map(x=>`<tr><td>${FEAT_ICON[x.key]||'•'} ${esc(x.label)}</td><td>${num(x.xu_in)}</td><td>${num(x.xu_out)}</td><td class="${x.net<0?'neg':''}">${x.net>0?'+':''}${num(x.net)}</td></tr>`);
  const top=(rows)=>rows.length?table(['Thao tác','Xu'],rows.map(t=>`<tr><td><code>${esc(t.action)}</code></td><td>${num(t.xu)}</td></tr>`)):'<p class="note">Chưa có.</p>';
  const s=e.sample,w=s?.wallet||{};
  const sample=s?kv([['Ví trung vị',`${num(w.median)} xu`],['Ví p90',`${num(w.p90)} xu`],['Ví trung bình',`${num(w.avg)} xu`],
      ['Đang nợ',`${pct(s.debt_pct)} <small>±${dec(s.debt_moe)}</small>`],['Có đầu tư',`${pct(s.investors_pct)} <small>±${dec(s.investors_moe)}</small>`],['Cỡ mẫu',num(s.n)]],'kv3')+
      `<p class="note">${num(s.n)} lượt chơi thay đổi gần nhất${s.covers_since?` (mọi người chơi có thao tác từ ${stamp(utcText(s.covers_since))})`:''}: không phải mẫu ngẫu nhiên của mọi người chơi. ± là sai số 95% nếu coi đây là mẫu.</p>`:'<p class="note">Mẫu bản lưu chưa được tính (mở “Hệ thống” hoặc chờ lần tính nền).</p>';
  return notices(d)+`<div class="kpis inv">
      ${metric(d,'xu_in',P('xu_in'),{sub:`${pl} đã qua`,series:S.xu_in,win})}
      ${metric(d,'xu_out',P('xu_out'),{sub:`${pl} đã qua`,series:S.xu_out,win})}
      ${metric(d,'xu_net',P('xu_net'),{sub:`${pl} đã qua`,series:S.xu_net,win})}
      ${metric(d,'xu_in_pp',P('xu_in_pp'),{sub:'mỗi người mỗi ngày',series:S.xu_in_pp,win})}
      ${metric(d,'wallet_median',w.median,{sub:s?`mẫu ${num(s.n)}`:'',series:S.wallet_median,win})}
      <div class="kpi m rev"><span class="kpi-label">${esc(def(d,'revenue').label)}${infoBtn(d,'revenue')}</span><b class="kpi-num">Chưa bật</b><small class="kpi-sub">${esc(e.revenue.note)}</small></div>
    </div>`+
    `<div class="charts two">${columns(d,'xu_net',win)}${columns(d,'xu_in',win,{tone:'second'})}</div>`+
    `<div class="cols"><div class="col">${card(`Xu theo nhóm thao tác <small>${num(e.window_days)} ngày</small>`,g.length?table(['Nhóm','Tạo ra','Tiêu đi','Ròng'],g):'<p class="note">Đang thu thập (bắt đầu từ bản này).</p>',
        {note:'Thay đổi số xu (ví + quỹ nơi làm + ngân hàng) sau mỗi thao tác. Tiền chuyển giữa ví, quỹ và ngân hàng không tính; vay được tính là xu vào, trả nợ là xu ra. Quà và quỹ chung giữa hai người chơi chưa được tính.'})}
      ${card('Ví người chơi (mẫu)',sample,{extra:infoBtn(d,'wallet_median')})}</div>
      <div class="col">${card('Nguồn xu lớn nhất',top(e.top_in))}${card('Chỗ tiêu xu lớn nhất',top(e.top_out))}</div></div>`;
}
function qualityTab(d,ui){
  const q=d.quality;if(!q)return notices(d);
  const S=seriesMap(d),n=Number(ui.period),win=windowIdx(d,n),P=k=>period(d,k,n,S),pl=PERIODS[ui.period];
  const fb=q.feedback,ack=fb.ack||{},L=q.loads||{},ai=q.ai||{},t=ai.total||{};
  const ms=v=>v==null?'—':`${num(v)} ms`;
  return notices(d)+`<div class="kpis inv">
      ${metric(d,'lat_p50',P('lat_p50'),{sub:`trung bình ${pl}`,series:S.lat_p50,win})}
      ${metric(d,'lat_p95',P('lat_p95'),{sub:`trung bình ${pl}`,series:S.lat_p95,win})}
      ${metric(d,'lat_p99',P('lat_p99'),{sub:`trung bình ${pl}`,series:S.lat_p99,win})}
      ${metric(d,'uptime',P('uptime'),{sub:`${pl} đã qua`,series:S.uptime,win})}
      ${metric(d,'http_5xx_pct',P('http_5xx_pct'),{sub:`${pl} đã qua`,series:S.http_5xx_pct,win})}
      ${metric(d,'err_per_1k',P('err_per_1k'),{sub:`${pl} đã qua`,series:S.err_per_1k,win})}
      ${metric(d,'feedback_per_100',P('feedback_per_100'),{sub:`${num(P('feedback'))} góp ý ${pl}`,series:S.feedback_per_100,win})}
      ${metric(d,'load_p50',L.frame?.p50,{sub:`p90 ${ms(L.frame?.p90)} · ${num(L.frame?.n)} lượt 7 ngày`})}
    </div>`+
    `<div class="charts two">${columns(d,'lat_p95',win)}${columns(d,'feedback',win,{tone:'second'})}</div>`+
    `<div class="cols"><div class="col">${card('Phản hồi góp ý',kv([['Đọc sau (trung vị)',ack.median_h==null?'—':`${dec(ack.median_h)} giờ`],['Trung bình',ack.avg_h==null?'—':`${dec(ack.avg_h)} giờ`],
        ['Đã đọc',`${pct(ack.read_pct)} <small>${num(ack.window_days)} ngày</small>`],['Còn chờ',`${num(ack.waiting)}${ack.waiting?` <small>lâu nhất ${dec(ack.oldest_wait_h)} giờ</small>`:''}`],
        ['Đang mở',num(fb.open)],['Tổng góp ý',num(fb.total)]],'kv3')+
        `<p class="note">Loại 30 ngày: ${Object.entries(fb.kinds||{}).map(([k,v])=>`${esc(k)} ${num(v)}`).join(' · ')||'chưa có'}.</p>`)}</div>
      <div class="col">${card(`AI <small>${ai.persisted?'mọi tiến trình':'tiến trình này'}</small>`,kv([['Lượt gọi',num(t.calls)],['Thành công',num(t.ok)],['Lỗi · bận',`${num(t.failed)} · ${num(t.busy)}`],['Bị lọc',num(t.rejected)]],'kv2'),{extra:infoBtn(d,'ai_calls')})}</div></div>`;
}
function acquisitionTab(d,ui){
  const a=d.acquisition;if(!a)return notices(d);
  const key=Number(ui.period)===7?'d7':'d30',src=a.sources[key]||[];
  const bars=(rows,lab)=>{if(!rows.length)return '<p class="note">Đang thu thập (bắt đầu từ bản này).</p>';const max=Math.max(1,...rows.map(r=>r.n));
    return `<ul class="hbars compact">${rows.map(r=>`<li><span class="hl">${esc(lab[r.key]||r.key)}</span><b class="hv">${num(r.n)} <small>${pct(r.pct)}</small></b><span class="track" aria-hidden="true"><i style="width:${Math.round(100*r.n/max)}%"></i></span></li>`).join('')}</ul>`;};
  return notices(d)+card(`Nguồn người mới <small>${key==='d7'?'7':'30'} ngày · ${num(a.sources[key+'_total'])} người</small>`,
      src.length?table(['Nguồn','Người','Tỉ lệ','D1','D7'],src.map(s=>`<tr><td>${esc(s.source)}</td><td>${num(s.n)}</td><td>${pct(s.share)}</td><td>${pct(s.d1)}${smallN(d,s.d1_n)}</td><td>${pct(s.d7)}${smallN(d,s.d7_n)}</td></tr>`)):'<p class="note">Chưa có người mới được ghi nguồn.</p>',
      {cls:'wide',extra:infoBtn(d,'source')})+
    `<div class="cols"><div class="col">${card('Hệ điều hành <small>30 ngày</small>',bars(a.os,OS),{extra:infoBtn(d,'device')})}${card('Loại máy',bars(a.form,FORM))}</div>
      <div class="col">${card('Trình duyệt / ứng dụng',bars(a.browser,{}))}${card('Ngôn ngữ trình duyệt',bars(a.lang,LANG))}
      ${card('Bot',kv([['Lượt mở của bot',num(a.bots.n)],['Tỉ lệ',pct(a.bots.pct)]],'kv2'),{note:'Bot (máy tìm kiếm, xem trước liên kết) cũng tạo bản lưu; chúng không bao giờ thành "người chơi mới" vì không thao tác.'})}</div></div>`;
}
function infraTab(d){
  const x=d.infra;if(!x)return notices(d);
  const ss=x.save_sizes,c=x.command||{};
  const hist=ss?.hist?.length?(()=>{const labels=['< 10 KB','10–25 KB','25–50 KB','50–100 KB','100–200 KB','200–400 KB','≥ 400 KB'],max=Math.max(1,...ss.hist);
    return `<ul class="hbars compact">${ss.hist.map((v,i)=>`<li><span class="hl">${labels[i]}</span><b class="hv">${num(v)}</b><span class="track" aria-hidden="true"><i style="width:${Math.round(100*v/max)}%"></i></span></li>`).join('')}</ul>`;})():'<p class="note">Chưa đo (mẫu bản lưu chưa tính).</p>';
  const tables=(x.tables||[]).slice(0,15).map(t=>`<tr><td><code>${esc(t.name)}</code></td><td>${t.approx?'≈ ':''}${num(t.rows)}</td></tr>`);
  return notices(d)+`<div class="kpis inv">
      ${metric(d,'db_bytes',null,{text:bytes(x.db_bytes)})}
      <div class="kpi m"><span class="kpi-label">Phiên bản</span><b class="kpi-num">v${esc(x.version)}</b><small class="kpi-sub">${esc(x.database||'')} · Python ${esc(x.python||'')}</small></div>
      <div class="kpi m"><span class="kpi-label">Tiến trình · CPU</span><b class="kpi-num">${num(x.workers)} · ${num(x.cpus)}</b><small class="kpi-sub">tiến trình này chạy ${span(x.uptime)}</small></div>
      <div class="kpi m"><span class="kpi-label">Thao tác / phút (lúc này)</span><b class="kpi-num">${dec(c.per_min)}</b><small class="kpi-sub">p50 ${num(c.p50)} ms · p90 ${num(c.p90)} ms</small></div>
      ${metric(d,'save_size',null,{sub:ss?`trung vị · p90 ${bytes(ss.p90)} · lớn nhất ${bytes(ss.max)} · ${ss.stored==='compressed'?'sau nén':'chưa nén'}`:'',text:bytes(ss?.median)})}
    </div>`+
    `<div class="cols"><div class="col">${card(`Kích thước bản lưu <small>mẫu ${num(ss?.n)}</small>`,hist)}</div><div class="col">${card('Bảng lớn nhất',table(['Bảng','Số dòng'],tables),{note:'Số dòng đếm nền mỗi 2 phút; bảng lớn là số ước tính (≈).'})}</div></div>`+
    `<p class="foot">Máy chủ đọc/ghi bản lưu khi người chơi thao tác; số liệu vận hành tính nền theo mẫu, có giới hạn thời gian và tạm dừng khi máy bận, để không làm chậm người chơi.</p>`;
}

/** The view: tabs + the selected tab. `ui`: {tab, period}; `name`: career id → name. */
export function investView(d,ui,name){
  const tab=TABS.some(([k])=>k===ui.tab)?ui.tab:'tong';
  const tabs=`<nav class="tabs" aria-label="Phần của tổng quan đầu tư">${TABS.map(([k,l])=>`<button type="button" class="${k===tab?'on':''}" data-act="invTab" data-value="${k}"${k===tab?' aria-current="page"':''}>${esc(l)}</button>`).join('')}</nav>`;
  const body={tong:overview,'tang-truong':growthTab,'hoat-dong':activityTab,'giu-chan':retentionTab,'gan-bo':engagementTab,'kinh-te':economyTab,
    'chat-luong':qualityTab,nguon:acquisitionTab,'ha-tang':infraTab}[tab](d,ui,name);
  return tabs+body+`<p class="foot">Số liệu lúc ${stamp(d.generated_at)} (giờ Việt Nam) · tính nền trong ${dec(d.took_ms)} ms, mỗi 10 phút khi có người xem trang này · ${d.cached&&d.age!=null?`bản ${num(d.age)} giây trước`:''}</p>`;
}

/* ---- the printable report (#bao-cao) ------------------------------------------------------------------------ */
/** Export rule: a count of players under `small` shows "<5"; a percentage over fewer is hidden. */
function sup(d,kind,v,n){
  if(v==null)return '—';
  if(kind==='n'&&v>0&&v<d.small)return `&lt;${d.small}`;
  if(kind==='pct'&&n!=null&&n<d.small)return '—';
  return fmt(kind,v);
}
function repRows(d,rows){
  return `<table class="rep-tbl"><thead><tr><th>Chỉ số</th><th class="v">Giá trị</th><th>Định nghĩa · cách tính</th></tr></thead><tbody>${rows.map(([key,v,n,note])=>{const x=def(d,key);
    return `<tr><td><b>${esc(x.label)}</b>${note?`<br><small>${esc(note)}</small>`:''}</td><td class="v">${key==='revenue'?'Chưa bật (0)':sup(d,x.kind,v,n)}</td><td><small>${esc(x.d)}<br><i>${esc(x.f)}</i></small></td></tr>`;}).join('')}</tbody></table>`;
}
const periodText=ui=>Number(ui.period)?`${PERIODS[ui.period]} đã kết thúc (đến hết hôm qua)`:'từ đầu nhật ký đến hết hôm qua';
function page(d,title,body,ui){
  return `<section class="rep-page"><header class="rep-head"><h2>${esc(title)}</h2><small>Phố Có Chuyện · số liệu lúc ${stamp(d.generated_at)} (giờ VN) · kỳ: ${periodText(ui)}</small></header>${body}</section>`;
}
export function reportView(d,ui,name){
  const S=seriesMap(d),n=Number(ui.period),P=k=>period(d,k,n,S),pl=PERIODS[ui.period],m=d.meta||{};
  const g=d.growth||{},t=g.totals||{},r=d.retention||{},e=d.engagement||{},ec=d.economy||{},q=d.quality||{},a=d.acquisition||{},x=d.infra||{};
  const pages=[];
  pages.push(`<section class="rep-page rep-cover"><h1>Phố Có Chuyện</h1><p class="rep-sub">Báo cáo số liệu vận hành</p>
    ${kv([['Số liệu lúc',stamp(d.generated_at)+' (giờ Việt Nam, UTC+7)'],['Kỳ',periodText(ui)],['Phiên bản',`v${esc(m.version||'')}`],['Ra mắt',m.launch||'—'],
      ['Nhật ký theo ngày từ',m.tracked_since||'—'],['Bộ đếm mới từ',m.counters_since||'—']],'kv2')}
    <p class="note">Mọi số là tổng hợp, không chứa tên, mã phiên, email, IP hay chữ người chơi gõ. Ô dưới ${d.small} người ghi “&lt;${d.small}”; tỉ lệ trên dưới ${d.small} người để trống. “—”: chưa có số liệu. Mỗi chỉ số có định nghĩa và cách tính ngay bên cạnh.</p>
    ${Object.keys(d.errors||{}).length?`<p class="note">Phần chưa tính được lúc xuất: ${Object.keys(d.errors).join(', ')}.</p>`:''}</section>`);
  pages.push(page(d,'1. Tổng quan',repRows(d,(d.headline||[]).map(c=>[c.key,c.key==='revenue'?null:c.value,c.n,c.key==='revenue'?'chưa bật — 0':c.sub])),ui));
  pages.push(page(d,'2. Tăng trưởng',repRows(d,[['saves_total',t.saves_total],['players_total',t.players_total],['accounts_total',t.accounts_total],['guests_played',t.guests_played],
    ['account_rate',t.account_rate,t.players_total],['new_sessions',P('new_sessions')],['new_players',P('new_players')],['activation',P('activation'),P('new_sessions')],['new_accounts',P('new_accounts')]]),ui));
  pages.push(page(d,'3. Hoạt động',repRows(d,['dau','wau','mau','stickiness','returning','resurrected','peak_online','peak_cmd_min','avg_min','median_min','sessions_pp','hours_total'].map(k=>[k,P(k)])),ui));
  const rc=(r.curve||[]).map(c=>`<tr><td>D${c.k}</td><td class="v">${sup(d,'pct',c.pct,c.n)}</td><td class="v">${c.ci&&c.n>=d.small?`${dec(c.ci[0])}–${dec(c.ci[1])}%`:'—'}</td><td class="v">${sup(d,'n',c.n)}</td></tr>`).join('');
  const wk=(r.weeks||[]).slice(-8).map(w=>`<tr><td>${dm(w.week)}</td><td class="v">${sup(d,'n',w.active)}</td><td class="v">${sup(d,'n',w.new)}</td><td class="v">${sup(d,'n',w.retained)}</td><td class="v">${sup(d,'n',w.back)}</td><td class="v">${sup(d,'n',w.churned)}</td><td class="v">${sup(d,'pct',w.churn_pct,w.prev)}</td></tr>`).join('');
  pages.push(page(d,'4. Giữ chân',`<table class="rep-tbl"><thead><tr><th>Ngày</th><th class="v">Quay lại</th><th class="v">Tin cậy 95%</th><th class="v">Người</th></tr></thead><tbody>${rc}</tbody></table>
    ${repRows(d,[['conversion',r.conversion?.pct,r.conversion?.n],['lifetime_days',r.lifetime?.avg_days]])}
    ${wk?`<h3>Theo tuần</h3><table class="rep-tbl"><thead><tr><th>Tuần</th><th class="v">Hoạt động</th><th class="v">Mới</th><th class="v">Ở lại</th><th class="v">Trở lại</th><th class="v">Rời đi</th><th class="v">Tỉ lệ rời</th></tr></thead><tbody>${wk}</tbody></table>`:''}
    <p class="note">${esc(def(d,'d1').d)} Khoảng tin cậy Wilson 95%.</p>`,ui));
  const feats=(e.features?.adoption||[]).map(f=>`<tr><td>${esc(f.label)}</td><td class="v">${sup(d,'pct',f.pct,f.dau_days)}</td></tr>`).join('');
  const so=e.social||{};
  pages.push(page(d,'5. Gắn bó',repRows(d,[['board_players',e.board?.players],['mastered_pct',e.board?.mastered_pct,e.board?.players],['work_days_median',e.board?.work_days_median],
    ['chat_share',P('chat_share')],['chat_msgs',P('chat_msgs')],['friend_pairs',so.friend_pairs],['with_friend',so.with_friend],['couples',so.couples],['married',so.married],['weddings_done',so.weddings_done],['dates_30d',so.dates_30d]])+
    (feats?`<h3>Dùng tính năng (7 ngày, % người hoạt động mỗi ngày)</h3><table class="rep-tbl"><tbody>${feats}</tbody></table>`:''),ui));
  const grp=(ec.groups||[]).map(x=>`<tr><td>${esc(x.label)}</td><td class="v">${num(x.xu_in)}</td><td class="v">${num(x.xu_out)}</td><td class="v">${num(x.net)}</td></tr>`).join('');
  pages.push(page(d,'6. Kinh tế',repRows(d,[['xu_in',P('xu_in')],['xu_out',P('xu_out')],['xu_net',P('xu_net')],['xu_in_pp',P('xu_in_pp')],['wallet_median',ec.sample?.wallet?.median,null,ec.sample?`mẫu ${ec.sample.n} lượt chơi gần nhất`:''],['revenue',null,null,'chưa bật — 0']])+
    (grp?`<h3>Theo nhóm thao tác (${num(ec.window_days)} ngày)</h3><table class="rep-tbl"><thead><tr><th>Nhóm</th><th class="v">Tạo ra</th><th class="v">Tiêu đi</th><th class="v">Ròng</th></tr></thead><tbody>${grp}</tbody></table>`:''),ui));
  pages.push(page(d,'7. Chất lượng & ổn định',repRows(d,[['lat_p50',P('lat_p50')],['lat_p95',P('lat_p95')],['lat_p99',P('lat_p99')],['uptime',P('uptime')],['http_5xx_pct',P('http_5xx_pct')],
    ['err_per_1k',P('err_per_1k')],['feedback',P('feedback')],['feedback_per_100',P('feedback_per_100')],['load_p50',q.loads?.frame?.p50],['ai_calls',q.ai?.total?.calls]]),ui));
  const srcs=(a.sources?.d30||[]).map(s=>`<tr><td>${esc(s.source)}</td><td class="v">${sup(d,'n',s.n)}</td><td class="v">${pct(s.share)}</td><td class="v">${sup(d,'pct',s.d1,s.d1_n)}</td><td class="v">${sup(d,'pct',s.d7,s.d7_n)}</td></tr>`).join('');
  const dev=(rows,lab)=>(rows||[]).map(r=>`${esc(lab[r.key]||r.key)} ${pct(r.pct)}`).join(' · ')||'—';
  pages.push(page(d,'8. Nguồn người chơi',`<table class="rep-tbl"><thead><tr><th>Nguồn (30 ngày)</th><th class="v">Người</th><th class="v">Tỉ lệ</th><th class="v">D1</th><th class="v">D7</th></tr></thead><tbody>${srcs||'<tr><td colspan="5">Chưa có.</td></tr>'}</tbody></table>
    ${kv([['Hệ điều hành',dev(a.os,OS)],['Loại máy',dev(a.form,FORM)],['Trình duyệt',dev(a.browser,{})],['Ngôn ngữ',dev(a.lang,LANG)],['Bot',`${num(a.bots?.n)} lượt mở (${pct(a.bots?.pct)})`]],'kv1')}`,ui));
  const ss=x.save_sizes||{};
  pages.push(page(d,'9. Hạ tầng',kv([['Cơ sở dữ liệu',esc(x.database||'')],['Dung lượng',bytes(x.db_bytes)],['Phiên bản',`v${esc(x.version||'')}`],['Tiến trình · CPU',`${num(x.workers)} · ${num(x.cpus)}`],
    ['Bản lưu (trung vị · p90)',`${bytes(ss.median)} · ${bytes(ss.p90)}`],['Thao tác/phút lúc xuất',dec(x.command?.per_min)]],'kv2'),ui));
  pages.push(page(d,'Phụ lục: định nghĩa',`<table class="rep-tbl"><thead><tr><th>Chỉ số</th><th>Định nghĩa</th><th>Cách tính</th></tr></thead><tbody>${Object.entries(d.defs||{}).map(([k,v])=>`<tr><td><b>${esc(v.label)}</b></td><td><small>${esc(v.d)}</small></td><td><small>${esc(v.f)}</small></td></tr>`).join('')}</tbody></table>`,ui));
  return `<div class="report">${pages.join('')}</div>`;
}
