/** Quán phở Cây Si — bác Lâm's phở shop under the old banyan (server: game/careers/pho.py).
 * The morning pot (fire, scum, a taste and a spoon of fish sauce, yesterday's bánh phở), then each bowl by
 * hand: a bowl or a take-away box, the trụng basket dipped three or four times, the cuts laid on top (tái on
 * the side when asked), onions, a raw yolk before the broth, then the ladle: the broth rises in the bowl in
 * real time and "Dừng muôi" stops it at the customer's line (a tap-to-stop on kit.tap_now). Clear broth,
 * the fatty top or the small pot without MSG; a pot run low is topped up with bones. The hot clock, the
 * herb plate and quẩy, cash through the shared till. The server decides everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {cashPanel,changeStep,changePayload,tillActions} from './till.js';
import {data,cc,lower,tile,act,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,meter} from './street_kit.js';

const VS=(x,k)=>(cc(x).vessels||{})[k]||{name:k,emoji:'🍜',rate:12,bag:k==='hop'};
const MT=(x,k)=>(cc(x).meats||{})[k]||{name:k,emoji:'🥩'};
const SRC=(x,k)=>(cc(x).sources||{})[k]||k;
const stock=(x,k)=>Number(data(x).stock?.[k]||0);
const kindOf=v=>v==='hop'?'bag':'bowl';
const band=(x,ln)=>((cc(x).bands||{})[kindOf(ln.v)]||{})[ln.nuoc]||[70,88];
const spill=(x,v)=>Number((cc(x).spill||{})[kindOf(v)]||98);
const DIP=x=>cc(x).dip_ok||[3,4];
const sorted=a=>[...a].sort().join(',');
const HANH_N={khong:0,vua:1,nhieu:2};
const SRC_EMOJI={trong:'🥣',beo:'🫕',nho:'🍲'};
const lineText=(x,ln)=>{
  const bits=[`${VS(x,ln.v).emoji} ${VS(x,ln.v).name} ${ln.meat.map(m=>lower(MT(x,m).name)).join(' ')}`];
  if(ln.rieng)bits.push('tái để riêng');
  if(ln.nuoc!=='vua')bits.push((cc(x).nuoc||{})[ln.nuoc]||ln.nuoc);
  if(ln.src==='beo')bits.push('nước béo');else if(ln.src==='nho')bits.push('không mì chính');
  if(ln.hanh!=='vua')bits.push((cc(x).hanh||{})[ln.hanh]||ln.hanh);
  if(ln.egg)bits.push('trứng trần');
  return bits.join(' · ');
};
const cuts=b=>[...b.meat,...b.side];
const finished=b=>b.lvl>0&&(b.v!=='hop'||b.tied);

/* ------------------------------------------------------------ pairing bowls with the order (as the server does) */
function plan(t){
  const lines=t.needs?.lines||[],bowls=t.bowls||[],used=new Set(),pairs=new Map();
  lines.forEach((ln,li)=>{
    const bi=bowls.findIndex((b,i)=>!used.has(i)&&b.v===ln.v&&sorted(cuts(b))===sorted(ln.meat));
    if(bi>=0){used.add(bi);pairs.set(li,bi);}
  });
  // The bowl being made: the last one on the counter, while it still fits a line of the order.
  const last=bowls.length-1,lb=bowls[last];
  let active=-1;
  if(lb&&!finished(lb)){
    const fits=(ln,li)=>ln.v===lb.v&&cuts(lb).every(m=>ln.meat.includes(m))&&(!pairs.has(li)||pairs.get(li)===last);
    active=lines.findIndex((ln,li)=>pairs.get(li)===last&&fits(ln,li));
    if(active<0)active=lines.findIndex((ln,li)=>!pairs.has(li)&&fits(ln,li));
  }
  return {pairs,used,active,last};
}

/* ------------------------------------------------------------ the pot strip and the hot clock */
function potBar(x,setup=false){
  const d=data(x),p=d.pot||{},labels=cc(x).fire_label||{};
  const fire=Object.keys(cc(x).fire||{nho:92,vua:97,lon:100}).map(k=>x.cmd(`${k==='lon'?'🔥🔥':k==='vua'?'🔥':'🕯️'} ${x.esc((labels[k]||k).replace(/^Lửa /,''))}`,'pho_fire',{fire:k},`small ${p.fire===k?'primary':'ghost'} ph-fire-btn`)).join('');
  const hot=Number(p.heat)>=Number(cc(x).tai_cook||95);
  const low=Number(p.level)<=Number(cc(x).level_low||30),canTop=Number(p.level)<=Number(cc(x).topup_at||60)&&d.shop?.open;
  const foam=Number(p.foam)>0?x.cmd(`🥄 Hớt bọt${p.foam>1?` (${p.foam})`:''}`,'pho_skim',{},`small ${p.foam>=Number(cc(x).foam_at||2)?'warn':'ghost'}`):'';
  const top=canTop?x.cmd(`🦴 Châm nồi <small>(${stock(x,'xuong')} mẻ xương)</small>`,'pho_topup',{},`small ${low?'warn':'ghost'}`,!stock(x,'xuong')):'';
  const taste=!setup&&d.shop?.open&&!p.taste?x.cmd('👅 Nếm','pho_taste',{},'small ghost'):'';
  return `<div class="ph-pot ${hot?'hot':'cool'} ${p.cloudy?'cloudy':''}" role="group" aria-label="Nồi nước dùng">
    <span class="ph-temp"><span aria-hidden="true">🌡️</span><b>${Number(p.heat)} °C</b><small>${x.esc(p.word||'')}${p.cloudy?' · nước đục':''}</small></span>
    <span class="ph-level"><small>Nồi còn ${Number(p.level)}%</small>${meter(Number(p.level),100,low?'warn':'')}</span>
    ${p.taste?`<span class="tag ${p.salt?'amber':'green'}">👅 ${x.esc(p.taste)}</span>`:''}
    <div class="ph-fires" role="group" aria-label="Lửa bếp">${fire}</div>
    <div class="ph-pot-acts">${foam}${taste}${top}</div></div>`;
}
function hotBar(t,x){
  const h=t.hot;if(!h||h.end!=null||t.stage!=='prep')return '';
  const end=Number(h.start)+Number(h.limit),left=Math.ceil(end-x.now());
  return `<div class="ph-hot ${left<=0?'late':left<=10?'soon':''}" role="timer" aria-live="off"><span aria-hidden="true">♨️</span><span>Phở còn nóng hổi</span><b data-ph-hot="${end}">${left>0?`${left}s`:'đang nguội!'}</b></div>`;
}

/* ------------------------------------------------------------ the order and the counter */
function ticket(t,x){
  if(!t.known)return askCard(x,t,'👂 Hỏi khách gọi gì');
  const n=t.needs||{},{pairs}=plan(t);
  const chips=(n.lines||[]).map((ln,li)=>`<span class="ph-chip ${pairs.has(li)&&finished((t.bowls||[])[pairs.get(li)])?'ok':''}">${x.esc(lineText(x,ln))}</span>`).join('');
  const tags=[n.check?'<span class="tag amber">👀 Sành ăn, nếm kỹ</span>':'',n.quay?`<span class="tag">🥖 ${n.quay} quẩy</span>`:'',n.rau?'<span class="tag">🌿 Đĩa rau, giá</span>':''].join('');
  return person(x,t,`<p class="ph-chips">${chips}</p>${n.note?`<p class="muted small">“${x.esc(n.note)}”</p>`:''}`,tags?`<span class="ph-tags">${tags}</span>`:'');
}
function bowlLine(x,b){
  const d=b.dip,[lo,hi]=DIP(x),dip=`<span class="ph-bit ${d<lo?'low':d>hi?'bad':''}">🍜 ${d} lượt</span>`;
  const meat=b.meat.map(m=>`<span class="ph-bit">${x.esc(MT(x,m).emoji)} ${x.esc(MT(x,m).name)}</span>`).join('');
  const side=b.side.map(m=>`<span class="ph-bit side">${x.esc(MT(x,m).emoji)} ${x.esc(MT(x,m).name)} riêng</span>`).join('');
  const bits=[dip,meat,side,b.hanh?`<span class="ph-bit">🧅×${b.hanh}</span>`:'',b.egg?`<span class="ph-bit ${b.egg==='raw'?'bad':''}">🥚${b.egg==='raw'?' sống':''}</span>`:'',
    b.lvl?`<span class="ph-bit">${b.src.map(s=>SRC_EMOJI[s]||'').join('')} ${b.lvl}%</span>`:'',b.v==='hop'&&b.lvl?`<span class="ph-bit ${b.tied?'':'low'}">${b.tied?'🎀 đã buộc':'túi chưa buộc'}</span>`:''].join('');
  return bits;
}
function counter(t,x){
  const bowls=t.bowls||[],{used}=plan(t);
  const row=bowls.map((b,i)=>{const v=VS(x,b.v);
    return `<li class="ph-bowl ${i===bowls.length-1&&!finished(b)?'now':''} ${used.has(i)&&finished(b)?'done':''}"><span class="ph-v" aria-hidden="true">${x.esc(v.emoji)}</span><span class="ph-bowl-body"><b>${x.esc(v.name)}</b><span class="ph-bits">${bowlLine(x,b)}</span></span></li>`;}).join('');
  const drop=bowls.length&&!t.pour?x.confirmCmd('🗑️ Đổ tô đang làm','pho_drop',{task:t.id},'Đổ tô đang làm, trụng lại tô khác?','small ghost'):'';
  const sd=t.side||{},sides=sd.quay||sd.rau?`<p class="small">${sd.quay?`🥖 ${sd.quay} quẩy `:''}${sd.rau?'🌿 đĩa rau, giá':''}</p>`:'';
  return `<section class="card ph-counter"><h4>🍜 Trên quầy</h4>${row?`<ul class="ph-bowls">${row}</ul>`:'<p class="small muted">Chưa có tô nào. Lấy tô hoặc hộp mang về.</p>'}${sides}<div class="sk-go-end">${drop}</div></section>`;
}
function vesselRow(t,x){
  const want=new Set((t.needs?.lines||[]).map(l=>l.v));
  const v=k=>{const s=VS(x,k),n=k==='hop'?stock(x,'hop'):null;
    return tile(x,'pho_bowl',{task:t.id,v:k},`<span class="tile-emoji">${x.esc(s.emoji)}</span><b>${x.esc(s.name)}</b><small>${n==null?`${s.banh} nắm bánh`:`còn ${n} bộ`}</small>`,want.has(k)?'want':'',n===0||!!t.pour);};
  return `<section class="card ph-vessels"><h4>Lấy tô</h4><div class="tile-grid ph-vgrid">${['to','to_lon','hop'].map(v).join('')}</div></section>`;
}
function bowlPanel(t,x){
  const bowls=t.bowls||[],b=bowls[bowls.length-1];if(!b||finished(b))return '';
  const [lo,hi]=DIP(x),poured=b.lvl>0,busy=!!t.pour;
  const dip=tile(x,'pho_dip',{task:t.id},`<span class="tile-emoji">🧺</span><b>Nhúng rổ bánh</b><small>${b.dip?`đã ${b.dip} lượt · ${b.dip<lo?'còn cứng':b.dip<=hi?'tơi mềm':'nát rồi'}`:`${VS(x,b.v).banh} nắm · ${lo}–${hi} lượt`}</small>`,b.dip&&b.dip<lo?'want':'',poured||cuts(b).length>0||busy||(!b.dip&&stock(x,'banh')<Number(VS(x,b.v).banh||1)));
  const meats=Object.entries(cc(x).meats||{}).map(([k,m])=>tile(x,'pho_meat',{task:t.id,m:k},`<span class="tile-emoji">${x.esc(m.emoji)}</span><b>${x.esc(m.name)}</b><small>${stock(x,k)?`còn ${stock(x,k)}`:'hết'}</small>`,cuts(b).includes(k)?'selected':'',!b.dip||poured||busy||cuts(b).includes(k)||!stock(x,k))).join('');
  const sideTai=tile(x,'pho_meat',{task:t.id,m:'tai',side:true},`<span class="tile-emoji">🥩</span><b>Tái để riêng</b><small>${b.v==='hop'?'túi nhỏ':'đĩa nhỏ'}</small>`,b.side.includes('tai')?'selected':'',!b.dip||poured||busy||cuts(b).includes('tai')||!stock(x,'tai'));
  const onion=x.cmd(`🧅 Rắc hành${b.hanh?` (${b.hanh})`:''}`,'pho_onion',{task:t.id},'ph-act',!b.dip||busy||b.hanh>=3);
  const egg=x.cmd(`🥚 Đập trứng${b.egg?' ✓':''}`,'pho_egg',{task:t.id},'ph-act',!b.dip||busy||!!b.egg||!stock(x,'trung'));
  return `<section class="card ph-make"><h4>${x.esc(VS(x,b.v).emoji)} ${x.esc(VS(x,b.v).name)} đang làm</h4>
    <div class="tile-grid ph-dipgrid">${dip}</div>
    <h4 class="section-title">Xếp thịt lên mặt bánh</h4><div class="tile-grid ph-mgrid">${meats}${sideTai}</div>
    <div class="ph-acts">${onion}${egg}</div></section>`;
}

/* ------------------------------------------------------------ the ladle: a tap-to-stop */
function ladlePanel(t,x){
  const bowls=t.bowls||[],b=bowls[bowls.length-1];if(!b||finished(b)&&!t.pour)return '';
  const {active}=plan(t),ln=active>=0?t.needs.lines[active]:null,[lo,hi]=ln?band(x,ln):[0,0],sp=spill(x,b.v),pr=t.pour;
  const src=x.ui.src&&(cc(x).sources||{})[x.ui.src]?x.ui.src:'trong';
  const chips=Object.keys(cc(x).sources||{trong:1,beo:1,nho:1}).map(k=>act(x,`${SRC_EMOJI[k]||''} ${x.esc(SRC(x,k))}`,'src',{k},`small ${src===k?'primary':'ghost'} ph-src`,` aria-pressed="${src===k}"${pr?' disabled':''}`)).join('');
  const bag=b.v==='hop';
  const gauge=`<div class="ph-gauge ${bag?'bag':''}" role="img" aria-label="Mực nước trong ${bag?'túi':'tô'}">
      ${ln?`<span class="ph-band" style="bottom:${lo}%;height:${hi-lo}%"></span>`:''}<span class="ph-spill" style="bottom:${sp}%"></span>
      <span class="ph-rise"><i class="ph-fill" style="transform:translateX(${Math.min(100,b.lvl)-100}%)"></i></span>
      <span class="ph-gauge-rim" aria-hidden="true"></span></div>`;
  const read=pr?`<b class="ph-read" data-ph-pour data-start="${Number(pr.start)}" data-base="${Number(pr.base)}" data-rate="${Number(pr.rate)}" data-lo="${lo}" data-hi="${hi}" data-sp="${sp}">${Number(pr.base)}%</b>`
    :`<b class="ph-read">${b.lvl}%</b>`;
  const want=ln?`<small>${x.esc((cc(x).nuoc||{})[ln.nuoc]||'')}: ${lo}–${hi}%${ln.src!=='trong'?` · ${x.esc(SRC(x,ln.src).toLowerCase())}`:''}</small>`:'';
  const go=pr?x.cmd('✋ Dừng muôi','pho_stop',{task:t.id},'primary big ph-stop')
    :x.cmd(b.lvl?'🫗 Chan thêm':'🫗 Chan nước dùng','pho_pour',{task:t.id,src},'primary ph-pour',!b.dip||b.lvl>=sp||(bag&&b.tied));
  const tie=bag&&b.lvl&&!pr?x.cmd('🎀 Buộc túi nước','pho_tie',{task:t.id},'ph-act',b.tied):'';
  return `<section class="card ph-ladle ${pr?'pouring':''}"><h4>🫗 Muôi nước dùng</h4><div class="ph-srcs" role="group" aria-label="Múc nồi nào">${chips}</div>
    <div class="ph-ladle-row">${gauge}<div class="ph-ladle-side">${read}${want}${go}${tie}</div></div></section>`;
}
/** While the ladle is in the air: a slim copy of the bowl's level inside the sticky bottom bar, right above
 * "Dừng muôi", so the line stays in view wherever the sheet is scrolled. */
function pourMini(t,x){
  const pr=t.pour,bowls=t.bowls||[],b=bowls[bowls.length-1];if(!pr||!b)return '';
  const {active}=plan(t),ln=active>=0?t.needs.lines[active]:null,[lo,hi]=ln?band(x,ln):[0,0],sp=spill(x,b.v);
  return `<div class="ph-mini" role="img" aria-label="Mực nước trong ${b.v==='hop'?'túi':'tô'}"><span class="ph-mini-track">${ln?`<span class="ph-mini-band" style="left:${lo}%;width:${hi-lo}%"></span>`:''}<span class="ph-mini-spill" style="left:${sp}%"></span><i class="ph-fill" style="transform:translateX(${Math.min(100,b.lvl)-100}%)"></i></span>
    <b data-ph-pour data-start="${Number(pr.start)}" data-base="${Number(pr.base)}" data-rate="${Number(pr.rate)}" data-lo="${lo}" data-hi="${hi}" data-sp="${sp}">${Number(pr.base)}%</b>${ln?`<small>${lo}–${hi}%</small>`:''}</div>`;
}
function sidePanel(t,x){
  const n=t.needs||{},sd=t.side||{};
  const q=x.cmd(`🥖 Thêm quẩy${sd.quay?` (${sd.quay})`:''}`,'pho_side',{task:t.id,item:'quay'},`ph-act ${n.quay&&sd.quay<n.quay?'want':''}`,!stock(x,'quay')||sd.quay>=8);
  const r=x.cmd(`🌿 Đĩa rau, giá${sd.rau?' ✓':''}`,'pho_side',{task:t.id,item:'rau'},`ph-act ${n.rau&&!sd.rau?'want':''}`,!!sd.rau||!stock(x,'rau'));
  return `<section class="card ph-sides"><h4>Ăn kèm</h4><div class="ph-acts">${q}${r}</div></section>`;
}

/* ------------------------------------------------------------ the morning */
function setupPanel(t,x){
  const d=data(x),p=d.pot||{},old=Number(d.old_banh||0);
  const taste=p.taste?`<p class="ph-taste ${p.salt?'off':''}">👅 <b>${x.esc(p.taste)}</b></p>${p.salt?`<div class="ph-acts">${x.cmd('🫙 Nêm nước mắm','pho_season',{what:'mam'},`ph-act ${p.salt<0?'want':''}`)}${x.cmd('💧 Châm nước sôi','pho_season',{what:'nuoc'},`ph-act ${p.salt>0?'want':''}`)}</div>`:''}`
    :`<div class="ph-acts">${x.cmd('👅 Nếm nước dùng','pho_taste',{},'primary ph-act')}${x.cmd('🫙 Nêm nước mắm','pho_season',{what:'mam'},'ph-act ghost')}${x.cmd('💧 Châm nước sôi','pho_season',{what:'nuoc'},'ph-act ghost')}</div>`;
  const banh=d.sour==null?x.cmd('👃 Ngửi rổ bánh phở','pho_sniff',{},'primary ph-act')
    :d.sour&&old?`<p class="small ph-bad">🤢 ${old} nắm bánh hôm qua chua, nhớt tay.</p>${x.cmd('🗑️ Bỏ bánh chua','pho_toss',{},'primary ph-act')}`
    :`<span class="tag green">✓ ${old?`${old} nắm bánh hôm qua còn thơm`:'Bánh mới giao, trắng mềm'}</span>`;
  return `<section class="card ph-setup"><h4>🍲 Nồi nước dùng</h4>${potBar(x,true)}<h4 class="section-title">Nếm và nêm</h4>${taste}
    <h4 class="section-title">Rổ bánh phở</h4>${banh}<p class="small muted">${x.esc(t.needs?.note||'')}</p></section>`;
}
function setupSteps(t,x){
  const d=data(x),p=d.pot||{},ok=cc(x).fire_ok||'vua',old=Number(d.old_banh||0),rows=[];
  rows.push({ok:p.fire===ok?true:null,label:'Vặn lửa lăn tăn',note:p.fire!==ok?(p.fire==='lon'?'lửa lớn làm nước đục':'lửa ủ chưa đủ sôi'):'',go:{cmd:'pho_fire',payload:{fire:ok},label:'🔥 Vặn lửa lăn tăn'}});
  rows.push({ok:Number(p.foam)===0?true:null,label:'Hớt bọt trên mặt nồi',note:p.foam?`còn ${p.foam} muôi bọt`:'',go:{cmd:'pho_skim',payload:{},label:'🥄 Hớt bọt'}});
  if(!p.taste)rows.push({ok:null,label:'Nếm nước dùng',go:{cmd:'pho_taste',payload:{},label:'👅 Nếm nước dùng'}});
  else rows.push({ok:p.salt?null:true,label:p.salt?(p.salt<0?'Nêm thêm nước mắm':'Châm nước sôi cho dịu'):'Nước vừa miệng',note:p.salt?p.taste:'',
    go:p.salt?{cmd:'pho_season',payload:{what:p.salt<0?'mam':'nuoc'},label:p.salt<0?'🫙 Nêm nước mắm':'💧 Châm nước sôi'}:null});
  rows.push({ok:d.sour==null?null:d.sour&&old?false:true,label:'Ngửi bánh hôm qua',note:d.sour&&old?'bánh chua, phải bỏ':'',
    go:d.sour==null?{cmd:'pho_sniff',payload:{},label:'👃 Ngửi rổ bánh phở'}:d.sour&&old?{cmd:'pho_toss',payload:{},label:'🗑️ Bỏ bánh chua'}:null});
  return rows;
}

/* ------------------------------------------------------------ học nghề: the first customers with bác Lâm */
function learnCard(x){
  const l=data(x).learn;if(!l?.on)return '';
  return `<section class="card ph-learn" aria-label="Học nghề"><span class="eyebrow">🧑‍🍳 Học nghề với bác Lâm · khách ${Math.min(l.n+1,l.of)}/${l.of}</span><b>${x.esc(l.title||'')}</b><p class="small">${x.esc(l.text||'')}</p><p class="small muted">Bác đứng cạnh bếp: lỡ sai chỗ nào, bác nhắc trước khi bưng ra.</p></section>`;
}

/* ------------------------------------------------------------ the guide */
function lineSteps(t,x,ln,b,rows){
  const [dlo,dhi]=DIP(x),[lo,hi]=band(x,ln),d=data(x),p=d.pot||{},id=t.id;
  if(b.dip<dlo)rows.push({ok:null,label:'Nhúng rổ bánh',note:`${b.dip}/${dlo} lượt`,go:b.lvl||cuts(b).length?null:{cmd:'pho_dip',payload:{task:id},label:'🧺 Nhúng rổ bánh'}});
  else if(b.dip>dhi)rows.push({ok:false,label:'Bánh nhúng lâu quá, nát rồi',go:{cmd:'pho_drop',payload:{task:id},label:'🗑️ Đổ tô làm lại'}});
  else rows.push({ok:true,label:`Bánh tơi (${b.dip} lượt)`});
  for(const m of ln.meat){
    const side=ln.rieng&&m==='tai',has=side?b.side.includes(m):b.meat.includes(m);
    if(has)rows.push({ok:true,label:`${MT(x,m).name}${side?' để riêng':''}`});
    else if(b.lvl)rows.push({ok:false,label:`Thiếu ${lower(MT(x,m).name)}: chan rồi mới xếp`,go:{cmd:'pho_drop',payload:{task:id},label:'🗑️ Đổ tô làm lại'}});
    else rows.push({ok:null,label:`${side?'Tái để riêng':`Xếp ${lower(MT(x,m).name)}`}`,go:b.dip>=dlo&&b.dip<=dhi?{cmd:'pho_meat',payload:{task:id,m,side},label:`${x.esc(MT(x,m).emoji)} ${side?'Tái để riêng':x.esc(MT(x,m).name)}`}:null});
  }
  const want=HANH_N[ln.hanh];
  if(ln.hanh==='khong')rows.push({ok:b.hanh?false:true,label:b.hanh?'Khách dặn không hành':'Không hành',go:b.hanh?{cmd:'pho_drop',payload:{task:id},label:'🗑️ Đổ tô làm lại'}:null});
  else rows.push({ok:b.hanh>=want&&(ln.hanh==='nhieu'||b.hanh<=2)?true:null,label:ln.hanh==='nhieu'?'Nhiều hành':'Rắc hành',note:b.hanh?`${b.hanh} nhúm`:'',go:b.hanh<want&&b.dip?{cmd:'pho_onion',payload:{task:id},label:'🧅 Rắc hành'}:null});
  if(ln.egg)rows.push({ok:b.egg==='ok'?true:b.egg==='raw'?false:null,label:'Trứng trần trước khi chan',go:!b.egg&&!b.lvl&&b.dip?{cmd:'pho_egg',payload:{task:id},label:'🥚 Đập trứng'}:b.egg==='raw'?{cmd:'pho_drop',payload:{task:id},label:'🗑️ Đổ tô làm lại'}:null});
  // The pot itself: hot enough for the tái, clean of scum.
  if(!b.lvl&&ln.src!=='nho'){
    if(ln.meat.includes('tai')&&!ln.rieng&&Number(p.heat)<Number(cc(x).tai_cook||95))rows.push({ok:null,label:'Chờ nồi lăn tăn lại',note:`${p.heat} °C`,go:p.fire==='nho'?{cmd:'pho_fire',payload:{fire:'vua'},label:'🔥 Vặn lửa lăn tăn'}:null});
    if(Number(p.foam)>=Number(cc(x).foam_at||2))rows.push({ok:null,label:'Mặt nồi nổi bọt',go:{cmd:'pho_skim',payload:{},label:'🥄 Hớt bọt'}});
  }
  const srcOk=!b.src.length||(ln.src==='nho'?b.src.every(v=>v==='nho'):ln.src==='beo'?b.src.includes('beo'):true);
  const label=`Chan ${(cc(x).nuoc||{})[ln.nuoc]||''}${ln.src==='beo'?', nước béo':ln.src==='nho'?', nồi nhỏ':''}`;
  if(t.pour)rows.push({ok:null,label,note:`${lo}–${hi}%`,go:{cmd:'pho_stop',payload:{task:id},label:'✋ Dừng muôi'}});
  else if(!srcOk)rows.push({ok:false,label:ln.src==='nho'?'Khách dặn không mì chính':'Khách dặn nước béo',go:ln.src==='nho'?{cmd:'pho_drop',payload:{task:id},label:'🗑️ Đổ tô làm lại'}:{cmd:'pho_pour',payload:{task:id,src:'beo'},label:'🫕 Chan nước béo'}});
  else if(b.lvl>=spill(x,b.v))rows.push({ok:false,label:'Nước tràn rồi',go:{cmd:'pho_drop',payload:{task:id},label:'🗑️ Đổ tô làm lại'}});
  else if(b.lvl<lo)rows.push({ok:null,label,note:b.lvl?`đang ${b.lvl}% · cần ${lo}–${hi}%`:`${lo}–${hi}%`,go:b.dip?{cmd:'pho_pour',payload:{task:id,src:ln.src},label:b.lvl?'🫗 Chan thêm':'🫗 Chan nước dùng'}:null});
  else rows.push({ok:b.lvl<=hi?true:false,label:b.lvl<=hi?`Nước ${b.lvl}%`:'Nước nhiều hơn khách dặn',note:b.lvl>hi?`${b.lvl}% · cần ${lo}–${hi}%`:''});
  if(b.v==='hop'&&b.lvl&&!t.pour)rows.push({ok:b.tied?true:null,label:'Buộc túi nước',go:b.tied?null:{cmd:'pho_tie',payload:{task:id},label:'🎀 Buộc túi nước'}});
}
function orderSteps(t,x){
  const d=data(x),n=t.needs||{},lines=n.lines||[],bowls=t.bowls||[],{pairs,active,last}=plan(t),rows=[];
  if(!d.shop?.open)rows.push({ok:null,label:'Mở quán xong mới bán',go:null});
  const lb=bowls[last];
  if(lb&&!finished(lb)&&active<0)rows.push({ok:false,label:'Tô này không khớp món khách gọi',go:{cmd:'pho_drop',payload:{task:t.id},label:'🗑️ Đổ tô làm lại'}});
  lines.forEach((ln,li)=>{
    if(li===active){lineSteps(t,x,ln,lb,rows);return;}
    if(pairs.has(li)&&finished(bowls[pairs.get(li)])){rows.push({ok:true,label:lineText(x,ln)});return;}
    const out=ln.meat.find(m=>!stock(x,m))||(!stock(x,'banh')&&'banh')||(ln.v==='hop'&&!stock(x,'hop')&&'hop');
    const go=active>=0||t.pour||out?null:{cmd:'pho_bowl',payload:{task:t.id,v:ln.v},label:`${x.esc(VS(x,ln.v).emoji)} Lấy ${x.esc(lower(VS(x,ln.v).name))}`};
    rows.push({ok:null,label:lineText(x,ln),note:out?`hết ${out==='banh'?'bánh phở':out==='hop'?'hộp':lower(MT(x,out).name)}`:'',go});
  });
  const sd=t.side||{};
  if(n.quay)rows.push({ok:sd.quay>=n.quay?true:null,label:`${n.quay} cái quẩy`,note:sd.quay?`${sd.quay}/${n.quay}`:'',go:sd.quay<n.quay&&!t.pour?{cmd:'pho_side',payload:{task:t.id,item:'quay'},label:'🥖 Thêm quẩy'}:null});
  if(n.rau)rows.push({ok:sd.rau?true:null,label:'Đĩa rau, giá',go:!sd.rau&&!t.pour?{cmd:'pho_side',payload:{task:t.id,item:'rau'},label:'🌿 Đĩa rau, giá'}:null});
  return rows;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở quán',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'pho_intro',payload:{},label:'🍜 Vào việc thôi!'}}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'🍜 MỞ QUÁN',go:finalGo(steps,'pho_open',{task:t.id}),ready:true}};}
  if(!t.known)return {steps:[{ok:null,label:'Hỏi khách',go:{cmd:'ask',payload:{task:t.id},label:'👂 Hỏi khách gọi gì'}}],final:null,pulse:'.sk-ask'};
  if(t.stage==='pay'){const s=changeStep(x,t.id,t.cash),steps=s?[s]:[];return {steps,final:{label:'💵 ĐƯA TIỀN THỐI',go:finalGo(steps,'pho_pay',{task:t.id,...changePayload(x,t.id,t.cash)}),ready:true}};}
  const steps=orderSteps(t,x);
  if(t.pour)return {steps,final:{label:'🍜 BƯNG PHỞ RA',go:{cmd:'pho_serve',payload:{task:t.id}},ready:false,why:'dừng muôi trước đã'}};
  const stuck=steps.some(s=>s.ok===null&&!s.go&&/^hết /.test(s.note||''))&&!(t.bowls||[]).length;
  if(stuck)return {steps,final:{label:'🙏 Nói thật: quán hết món này',go:{cmd:'pho_decline',payload:{task:t.id}},ready:true}};
  const all=(t.bowls||[]).length&&(t.bowls||[]).every(b=>b.lvl>0);
  return {steps,final:{label:(t.bowls||[]).every(b=>b.v==='hop')?'🥡 ĐƯA KHÁCH':'🍜 BƯNG PHỞ RA',go:finalGo(steps,'pho_serve',{task:t.id}),ready:!!all,why:'chan nước cho đủ tô trước đã'}};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});

/* ------------------------------------------------------------ idle: the shop between customers */
function shopView(x){
  const meats=Object.entries(cc(x).meats||{}).map(([k,m])=>`<li><span aria-hidden="true">${x.esc(m.emoji)}</span><b>${x.esc(m.name)}</b><small>${stock(x,k)} phần</small></li>`).join('');
  return `<section class="card ph-shop"><h4>🔪 Thớt thịt</h4><ul class="ph-meats">${meats}</ul><p class="small muted">🍜 ${stock(x,'banh')} nắm bánh · 🥖 ${stock(x,'quay')} quẩy · 🌿 ${stock(x,'rau')} đĩa rau · 🥚 ${stock(x,'trung')} trứng · 🦴 ${stock(x,'xuong')} mẻ xương · 🥡 ${stock(x,'hop')} hộp</p>
    <p class="small muted">🍲 Nồi nhỏ không mì chính còn ${Number(data(x).small||0)}%</p></section>`;
}

export default {
  id:'pho',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='setup'?'Canh nồi nước, mở quán':!t.known?'Hỏi khách gọi gì':'Làm tô phở cho khách';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'pho_intro','🍜')}${deskCard(x,'pho_desk','Chuyện ở quán')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk ph">${hint}${top}${bottom(x,g)}</div>`;
    let main='',side='';
    if(t.kind==='setup'){main=setupPanel(t,x);side=stepRows(x,g.steps,'Việc mở quán');}
    else if(!t.known)main='';
    else if(t.stage==='pay')main=cashPanel(x,t.id,t.cash);
    else{
      const b=(t.bowls||[])[(t.bowls||[]).length-1],making=b&&(!finished(b)||t.pour);
      main=`${hotBar(t,x)}${ladlePanel(t,x)}${making?bowlPanel(t,x):vesselRow(t,x)}${counter(t,x)}${sidePanel(t,x)}`;
      side=stepRows(x,g.steps,'Món của khách');
    }
    const head=t.kind==='setup'?dayBar(x):`${learnCard(x)}${ticket(t,x)}${dayBar(x)}${t.known&&t.stage==='prep'?potBar(x):''}`;
    const bar=bottom(x,g),mini=t.kind!=='setup'&&t.stage==='prep'?pourMini(t,x):'';
    return `<div class="career-job sk ph">${hint}${top}${head}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${mini?bar.replace('<div class="sk-bar">',`<div class="sk-bar">${mini}`):bar}</div>`;
  },
  idle(x){
    const d=data(x),top=`${introCard(x,'pho_intro','🍜')}${deskCard(x,'pho_desk','Chuyện ở quán')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở quán',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'pho_intro',payload:{},label:'🍜 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk ph">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk ph">${top}${dayBar(x)}${potBar(x)}${shopView(x)}</div>`;
  },
  // The broth rising in the bowl moves on the compositor (x.slide); the level and its words are set five times a
  // second. "Dừng muôi" holds it where it was when the finger came down (tapStop).
  meters(root,x){
    for(const el of root.querySelectorAll('[data-ph-pour]')){
      const base=Number(el.dataset.base)||0,rate=Number(el.dataset.rate)||10,lo=Number(el.dataset.lo),hi=Number(el.dataset.hi),sp=Number(el.dataset.sp)||98;
      const lvl=Math.min(110,base+Math.max(0,x.now()-Number(el.dataset.start))*rate);
      const card=el.closest('.ph-ladle,.ph-mini');x.slide(card?.querySelector('.ph-fill'),Math.min(100,lvl),lvl>=100?0:rate,true);
      const s=`${Math.floor(lvl)}%`;if(el.textContent!==s)el.textContent=s;
      card?.classList.toggle('in-band',lvl>=lo&&lvl<=hi);card?.classList.toggle('over',lvl>hi);card?.classList.toggle('spill',lvl>=sp);
    }
  },
  tapStop:op=>op==='pho_stop',
  tick(root,x){
    keepBarAboveFooter(root);
    const el=root.querySelector('[data-ph-hot]');
    if(el){const left=Math.ceil(Number(el.dataset.phHot)-x.now()),s=left>0?`${left}s`:'đang nguội!';
      if(el.textContent!==s)el.textContent=s;const bar=el.closest('.ph-hot');bar?.classList.toggle('soon',left>0&&left<=10);bar?.classList.toggle('late',left<=0);}
  },
  actions:{...tillActions,...kitActions,
    async src(d,el,x){x.ui.src=d.k;x.render();},
  },
  dock:[['inventory','box','Kho quán phở','Nhập bánh phở, thịt bò, xương, quẩy…']],
};
