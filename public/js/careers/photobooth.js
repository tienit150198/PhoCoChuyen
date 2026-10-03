/** Tiệm ảnh Tách Tách — chị Lam's photobooth by the night market (server: game/careers/photobooth.py).
 * The morning (wipe the lens, a test shot, the ink roll in the printer), then each group: the order at the
 * counter, the booth set up (package, frame, backdrop, props, light), the countdown and the shutter at the
 * moment everyone holds the pose with their eyes open (a stop tap: tapStop + kit.tap_now), the shots on the
 * screen and the customers' choice, stickers / date / colour, printing, trimming, handing over, the till.
 * Frames, people and the printed strip are drawn by ../v4/photo-frames.js (shared with the fair's booth).
 * The server decides everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine,firstTime} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {cashPanel,changeStep,changePayload,tillActions} from './till.js';
import {data,cc,lower,tile,act,introCard,deskCard,dayBar,person,askCard,bottom,kitActions} from './street_kit.js';
import * as PF from '../v4/photo-frames.js';

const PK=(x,k)=>(cc(x).pkgs||{})[k]||{name:k,emoji:'🎞️',shots:4,paper:'giay_dai',sleeves:1};
const NAME=(x,table,k)=>(cc(x)[table]||{})[k]||k;
const PF_ITEM=(list,k)=>list.find(v=>v.id===k)||{id:k,name:k,emoji:'✨'};
const stockOf=(x,k)=>Number(data(x).stock?.[k]??x.room.inventory?.stock?.[k]??0);
const LIGHT={diu:'soft',sang:'bright',am:'warm'};
const LIGHT_EMOJI={diu:'🕯️',sang:'💡',am:'🌅'};
const Q_TAG={good:['ok','✓ đẹp'],early:['bad','nhòe'],blink:['bad','nhắm mắt'],late:['bad','hết dáng']};
const TABS=[['set','① Bố trí'],['shoot','② Chụp'],['pick','③ Chọn ảnh'],['print','④ In & giao']];
const BRAND='Tách Tách · Phố Có Chuyện';
const sameSet=(a,b)=>[...(a||[])].sort().join(',')===[...(b||[])].sort().join(',');
const need=t=>t.needs||{};
const kOf=(x,t)=>PK(x,need(t).pkg).shots;
function dateStr(){const d=new Date(),p=n=>String(n).padStart(2,'0');return `${p(d.getDate())}.${p(d.getMonth()+1)}.${String(d.getFullYear()).slice(2)}`;}
const fltText=(x,f)=>f==='none'?'giữ màu gốc':`màu ${lower(NAME(x,'filters',f))}`;

/* ------------------------------------------------------------ pictures (drawn after each render, see meters) */
const PAINT=new Map();
let LIVE=null;
/** A canvas drawn once per `key` (the key changes when the picture would). */
function canvas(key,paint,cls='',label=''){const k=String(key).replace(/["'<>&]/g,'');PAINT.set(k,paint);return `<canvas class="pb-cv ${cls}" data-pb-k="${k}"${label?` role="img" aria-label="${label}"`:''}></canvas>`;}
function fit(cv,w,h){const r=Math.min(2,Math.max(1,globalThis.devicePixelRatio||1));cv.width=Math.round(w*r);cv.height=Math.round(h*r);const c=cv.getContext('2d');c.setTransform(r,0,0,r,0,0);return c;}
function fog(c,w,h){c.save();const g=c.createRadialGradient(w/2,h/2,h*.1,w/2,h/2,w*.7);g.addColorStop(0,'rgba(255,255,255,.28)');g.addColorStop(1,'rgba(240,244,248,.62)');c.fillStyle=g;c.fillRect(0,0,w,h);c.restore();}
/** The people of this group as photo-frames.js draws them. */
function crowd(x,t){return ((cc(x).looks||{})[need(t).look]||[{age:'adult',style:'short',top:'#d0567f'}]).map(p=>({eyes:'open',mouth:'smile',...p}));}
/** A shot the server keeps ({q, bd, light, props, haze, who}) as a picture. */
function picOf(x,t,s,i=0){
  const people=crowd(x,t);let blur=0,pose=i%4;
  if(s.q==='early')blur=.8;
  if(s.q==='blink'&&people[s.who])people[s.who]={...people[s.who],eyes:'closed'};
  if(s.q==='late'){people.forEach((p,j)=>{p.eyes=j===s.who?'closed':'half';p.mouth='o';});blur=.2;pose=3;}
  return {backdrop:s.bd,light:LIGHT[s.light]||'soft',blur,pose,sign:need(t).sign||'',people,props:s.props||[],haze:!!s.haze};
}
function paintCell(c,shot,w,h){PF.paintShot(c,shot,w,h);if(shot?.haze)fog(c,w,h);}
function shotCanvas(x,t,i,cls=''){
  const s=t.shots[i];const key=`shot-${t.id}-${i}-${s.q}-${s.bd}-${s.light}-${(s.props||[]).join('.')}-${s.haze?1:0}`;
  return canvas(key,cv=>{const c=fit(cv,156,97);paintCell(c,picOf(x,t,s,i),156,97);},cls,`Tấm ${i+1}`);
}
/** The print as it would come out now (`printed` = what did come out). */
function stripOf(x,t,src){
  const pk=src.pkg||need(t).pkg||'strip',cells=pk==='big'?1:4;
  const shots=Array.from({length:cells},(_,j)=>{const i=src.pick?.[j];return i!=null&&t.shots[i]?picOf(x,t,t.shots[i],i):null;});
  return {strip:{layout:pk,shots},frame:src.frame||'kawaii',deco:{stickers:src.st||[],date:src.date?dateStr():'',filter:src.flt||'none',cut:pk==='double'}};
}
function printCanvas(x,t,src,cls,scale){
  const p=stripOf(x,t,src);
  const key=`print-${t.id}-${PF.sig(p.strip,p.frame,p.deco)}-${(src.pick||[]).map(i=>t.shots[i]?.q).join('')}-${scale}`;
  const dpr=Math.min(2,Math.max(1,globalThis.devicePixelRatio||1));
  return canvas(key,cv=>{PF.draw(cv,p.strip,p.frame,p.deco,{scale:scale*dpr,brand:BRAND,t:x.t,paintShot:(c,s,w,h)=>paintCell(c,s,w,h)});},`pb-print ${cls} lay-${p.strip.layout}`,'Ảnh in');
}

/* ------------------------------------------------------------ the order */
/** `tab`: past the set-up the card shrinks to a name and the words that matter on that tab, so the work stays in view. */
function ticket(t,x,tab='set'){
  if(!t.known)return askCard(x,t,'👂 Hỏi khách muốn chụp gì');
  const n=need(t),st=t.set||{},de=t.deco||{};
  const chip=(ok,s)=>`<span class="pb-chip ${ok?'ok':''}">${s}</span>`;
  const props=n.props?.length?n.props.map(k=>x.esc(lower(NAME(x,'props',k)))).join(', '):'không đạo cụ';
  const sts=n.st?.length?`dán ${n.st.map(k=>x.esc(lower(NAME(x,'stickers',k)))).join(', ')}${n.free?' (+ tùy ý)':''}`:n.free?'sticker tùy ý':'không sticker';
  const list=[chip(st.pkg===n.pkg,`${x.esc(PK(x,n.pkg).emoji)} ${x.esc(PK(x,n.pkg).name)}`),
    chip((n.frames||[]).includes(st.frame),`🖼️ ${(n.frames||[]).map(k=>x.esc(NAME(x,'frames',k))).join(' / ')}`),
    chip((n.bd||[]).includes(st.bd),`🎨 ${(n.bd||[]).map(k=>x.esc(lower(NAME(x,'backdrops',k)))).join(' / ')}`),
    chip(sameSet(st.props,n.props),`🎩 ${props}`),
    chip(st.light===n.light,`${LIGHT_EMOJI[n.light]||'💡'} ${x.esc(lower(NAME(x,'lights',n.light)))}`),
    chip((n.st||[]).every(k=>(de.st||[]).includes(k))&&(n.free||sameSet(de.st,n.st)),`✨ ${sts}`),
    chip(de.date===n.date,n.date?'📅 có ngày tháng':'📅 không ghi ngày'),
    chip(de.flt===n.flt,`🎞️ ${x.esc(fltText(x,n.flt))}`)],chips=list.join('');
  if(tab!=='set'){
    const pick={shoot:[0,2,3,4],pick:[5,6,7],print:[0,1],pay:[]}[tab]||[];
    return `<article class="card pb-slim"><p><b>${x.esc(x.npc(t.npc).display_name)}</b> <span class="muted small">· ${x.esc(t.title)}</span></p>${pick.length?`<p class="pb-chips">${pick.map(i=>list[i]).join('')}</p>`:''}</article>`;
  }
  const tags=[n.check?'<span class="tag amber">👀 Soi ảnh kỹ</span>':'',n.kid?'<span class="tag">🧒 Bé khó ngồi yên</span>':'',n.old?'<span class="tag">👴 Cười chậm</span>':''].join('');
  return person(x,t,`<p class="pb-chips">${chips}</p>${n.note?`<p class="muted small">${x.esc(n.note)}</p>`:''}`,tags?`<span class="pb-tags">${tags}</span>`:'');
}

/* ------------------------------------------------------------ ① the booth */
function setPanel(t,x){
  const st=t.set||{},n=need(t),locked=!!t.trim;
  const pkgs=Object.entries(cc(x).pkgs||{}).map(([k,v])=>{const left=stockOf(x,v.paper);
    return tile(x,'pb_pkg',{task:t.id,pkg:k},`<span class="tile-emoji">${x.esc(v.emoji)}</span><b>${x.esc(v.name)}</b><small>${Number(cc(x).prices?.[k]||0)} xu · giấy còn ${left}</small>`,st.pkg===k?'selected':'',locked)
      .replace('<button ',`<button aria-label="${x.esc(v.name)} · ${Number(cc(x).prices?.[k]||0)} xu" `);}).join('');
  const frames=PF.FRAMES.filter(f=>(cc(x).frames||{})[f.id]).map(f=>tile(x,'pb_frame',{task:t.id,frame:f.id},
    `${canvas(`thumb-${f.id}`,cv=>PF.thumb(cv,f.id,{layout:'big',scale:.11,t:x.t}),'pb-thumb')}<b>${x.esc(NAME(x,'frames',f.id))}</b>`,`pb-frame ${st.frame===f.id?'selected':''}`,locked)).join('');
  const bds=Object.entries(cc(x).backdrops||{}).map(([k,v])=>tile(x,'pb_bd',{task:t.id,bd:k},`<span class="pb-swatch bd-${x.esc(k)}" aria-hidden="true"></span><b>${x.esc(v)}</b>`,`pb-bd ${st.bd===k?'selected':''}`)).join('');
  const props=Object.entries(cc(x).props||{}).map(([k,v])=>{const on=(st.props||[]).includes(k),p=PF_ITEM(PF.PROPS,k);
    return x.cmd(`<span aria-hidden="true">${x.esc(p.emoji)}</span> ${x.esc(v)}`,'pb_prop',{task:t.id,prop:k},`small pb-prop ${on?'primary':'ghost'}`).replace('<button ',`<button aria-pressed="${on}" `);}).join('');
  const lights=Object.entries(cc(x).lights||{}).map(([k,v])=>tile(x,'pb_light',{task:t.id,light:k},`<span class="tile-emoji">${LIGHT_EMOJI[k]||'💡'}</span><b>${x.esc(v)}</b>`,`pb-light ${st.light===k?'selected':''}`)).join('');
  return `<section class="card pb-set"><h4>🎞️ Gói ảnh</h4><div class="tile-grid pb-pkgs">${pkgs}</div>
    <h4 class="section-title">🖼️ Khung ảnh</h4><div class="tile-grid pb-frames">${frames}</div>
    <h4 class="section-title">🎨 Phông nền</h4><div class="tile-grid pb-bds">${bds}</div>
    <h4 class="section-title">🎩 Rổ đạo cụ <small class="muted">chạm để đưa / cất</small></h4><div class="pb-props">${props}</div>
    <h4 class="section-title">💡 Đèn</h4><div class="tile-grid pb-lights">${lights}</div>
    ${n.kid||n.old?`<p class="small muted">${n.kid?'Bé nhỏ giữ dáng rất ngắn: canh thật nhanh tay.':'Ông bà cười chậm: đợi thêm nửa nhịp rồi hẵng bấm.'}</p>`:''}</section>`;
}

/* ------------------------------------------------------------ ② the camera */
function camPanel(t,x){
  const b=t.beat||{count:3,lead:.4,hold:1.3,blink:1.2,recharge:1},st=t.set||{},shots=t.shots||[],max=Number(cc(x).max_shots||8),d=data(x);
  const span=b.count+b.lead+b.hold+b.blink+1.2,pc=v=>(v/span*100).toFixed(2);
  const zones=`<i class="z z-count" style="left:0;width:${pc(b.count)}%"></i><i class="z z-lead" style="left:${pc(b.count)}%;width:${pc(b.lead)}%"></i><i class="z z-hold" style="left:${pc(b.count+b.lead)}%;width:${pc(b.hold)}%"></i><i class="z z-blink" style="left:${pc(b.count+b.lead+b.hold)}%;width:${pc(b.blink)}%"></i>`;
  const ready=st.bd&&st.light,cam=t.cam;
  LIVE={t,x,b};
  const view=`<div class="pb-view ${cam?'live':''}"${cam?` data-pb-cam="${Number(cam.start)}" data-beat="${[b.count,b.lead,b.hold,b.blink].join(',')}"`:''}>
    <canvas class="pb-cv pb-live" data-pb-live="1" role="img" aria-label="Màn hình máy ảnh"></canvas><b class="pb-count" aria-live="off">${cam?'':ready?'Sẵn sàng':'Chưa bố trí'}</b>
    ${d.booth?.fog||d.booth&&!d.booth.lens?'<span class="pb-fog-tag">💧 kính mờ</span>':''}</div>`;
  const meter=cam?`<div class="pb-meter" aria-hidden="true">${zones}<span class="pb-needle"><i></i></span></div><p class="pb-say small" data-pb-say>…</p>`:'';
  const go=cam?`<div class="pb-shutter">${x.cmd('📸 BẤM MÁY','pb_snap',{task:t.id},'primary big pb-snap').replace('<button ','<button data-fd-wait=".pb-view.ready" ')}${x.cmd('⏸️','pb_stop',{task:t.id},'ghost pb-stop').replace('<button ','<button aria-label="Tạm dừng máy" ')}</div>`
    :`<div class="pb-shutter">${x.cmd(shots.length?'⏱️ Đếm tiếp':'⏱️ Bắt đầu đếm 3-2-1','pb_shoot',{task:t.id},'primary big pb-shoot',!ready||shots.length>=max||!!t.printed)}</div>`;
  const roll=shots.length?`<ol class="pb-roll">${shots.map((s,i)=>`<li class="q-${x.esc(s.q)}">${shotCanvas(x,t,i)}<small><b>${i+1}</b> <span class="tag ${Q_TAG[s.q]?.[0]==='ok'?'green':'red'}">${Q_TAG[s.q]?.[1]||''}</span></small></li>`).join('')}</ol>`:'';
  const after=`<div class="sk-row pb-after">${x.cmd('🖥️ Cho khách xem ảnh','pb_show',{task:t.id},'pb-show',!shots.length)}${shots.length&&!t.printed?x.confirmCmd('🔄 Xóa, chụp lượt mới','pb_redo',{task:t.id},'Xóa hết ảnh lượt này rồi chụp lại từ đầu?','ghost small pb-redo'):''}</div>`;
  const lens=d.booth?.fog||d.booth&&!d.booth.lens?`<p class="notice small">💧 Ống kính mờ hơi nước. ${x.cmd('🧽 Lau ống kính','pb_lens',{},'small pb-lens')}</p>`:'';
  return `<section class="card pb-cam"><h4>📸 Buồng chụp <small class="muted">${shots.length}/${max} kiểu</small></h4>${lens}${view}${meter}${go}${roll}${after}</section>`;
}
/** The words under the bar and the picture on the camera's screen, by where the countdown is. */
function camPhase(el,b){
  if(el<0)return ['flash','⚡ Đèn flash đang sạc…'];
  if(el<b.count)return [`count${Math.floor(el)}`,`${3-Math.floor(el)}…`];
  if(el<b.count+b.lead)return ['settle','Cả nhóm vào dáng…'];
  if(el<=b.count+b.lead+b.hold)return ['hold','📸 Đứng yên, mở mắt: BẤM!'];
  if(el<=b.count+b.lead+b.hold+b.blink)return ['blink','Ơ, có người chớp mắt…'];
  return ['late','Hết dáng rồi, đợi lượt sau'];
}
function paintLive(cv,phase){
  if(!LIVE||cv._phase===phase)return;cv._phase=phase;
  const {t,x}=LIVE,st=t.set||{},people=crowd(x,t),d=data(x);
  let blur=0,pose=(t.shots||[]).length%4;
  if(phase.startsWith('count'))blur=.55,pose=Number(phase.slice(5))%4;
  else if(phase==='settle'||phase==='flash')blur=.25;
  else if(phase==='blink')people.forEach((p,i)=>{if(i===0)p.eyes='closed';});
  else if(phase==='late')people.forEach(p=>{p.eyes='half';p.mouth='o';}),pose=3;
  const shot={backdrop:st.bd||'kem',light:LIGHT[st.light]||'dim',blur,pose,sign:need(t).sign||'',people:st.bd?people:[],props:st.props||[]};
  const w=Math.max(200,cv.clientWidth||260),h=Math.round(w*162/260),c=fit(cv,w,h);
  PF.paintShot(c,shot,w,h);if(d.booth?.fog||d.booth&&!d.booth.lens)fog(c,w,h);
  if(phase==='flash'){c.fillStyle='rgba(255,255,255,.35)';c.fillRect(0,0,w,h);}
}

/* ------------------------------------------------------------ ③ choosing and decorating */
function pickPanel(t,x){
  const shots=t.shots||[],k=kOf(x,t),pick=t.pick||[],de=t.deco||{},locked=!!t.trim;
  if(!shots.length)return `<section class="card pb-pick"><p class="small muted">Chưa chụp tấm nào. Sang ② Chụp trước nhé.</p></section>`;
  const said=t.want?`<p class="pb-said">💬 Khách chọn: <b>tấm ${t.want.map(i=>i+1).join(', ')}</b></p>`:`<p class="small muted">Mời khách xem màn hình (② Chụp → “Cho khách xem ảnh”) để khách chọn.</p>`;
  const grid=`<ol class="pb-grid">${shots.map((s,i)=>{const at=pick.indexOf(i);
    return `<li><button type="button" class="pb-pickbtn ${at>=0?'on':''}" data-command="pb_pick" data-payload="${x.esc(JSON.stringify({task:t.id,i}))}" aria-pressed="${at>=0}"${locked?' disabled':''}>${shotCanvas(x,t,i)}<span class="pb-num">${i+1}</span>${at>=0?`<span class="pb-order">${at+1}</span>`:''}<small class="tag ${Q_TAG[s.q]?.[0]==='ok'?'green':'red'}">${Q_TAG[s.q]?.[1]||''}</small></button></li>`;}).join('')}</ol>`;
  const stickers=Object.entries(cc(x).stickers||{}).map(([k,v])=>{const on=(de.st||[]).includes(k),p=PF_ITEM(PF.STICKERS,k);
    return x.cmd(`<span aria-hidden="true">${x.esc(p.emoji)}</span> ${x.esc(v)}`,'pb_sticker',{task:t.id,st:k},`small pb-st ${on?'primary':'ghost'}`,locked).replace('<button ',`<button aria-pressed="${on}" `);}).join('');
  const date=`<div class="segmented pb-date" role="group" aria-label="Ngày tháng">${x.cmd('📅 Có ngày','pb_date',{task:t.id,on:true},`small ${de.date?'primary':'ghost'}`,locked)}${x.cmd('Không ghi ngày','pb_date',{task:t.id,on:false},`small ${de.date?'ghost':'primary'}`,locked)}</div>`;
  const flts=Object.entries(cc(x).filters||{}).map(([k,v])=>x.cmd(x.esc(v),'pb_filter',{task:t.id,flt:k},`small pb-flt ${de.flt===k?'primary':'ghost'}`,locked)).join('');
  const st=t.set||{};
  const prev=st.frame&&st.pkg?`<figure class="pb-preview">${printCanvas(x,t,{pkg:st.pkg,frame:st.frame,pick,st:de.st,date:de.date,flt:de.flt},'small',.42)}<figcaption class="small muted">Bản xem trước</figcaption></figure>`:'';
  return `<section class="card pb-pick"><h4>🖥️ Chọn ảnh <small class="muted">${pick.length}/${k} tấm</small></h4>${said}${grid}
    <div class="pb-deco"><div class="pb-deco-ctl"><h4 class="section-title">✨ Sticker</h4><div class="pb-sts">${stickers}</div>
    <h4 class="section-title">📅 Ngày tháng</h4>${date}<h4 class="section-title">🎞️ Màu ảnh</h4><div class="pb-flts">${flts}</div></div>${prev}</div></section>`;
}

/* ------------------------------------------------------------ ④ printing, trimming, handing over */
function printPanel(t,x){
  const st=t.set||{},de=t.deco||{},pr=t.printed,pk=PK(x,st.pkg||need(t).pkg),d=data(x);
  const cur={pkg:st.pkg,frame:st.frame,pick:t.pick||[],st:de.st,date:de.date,flt:de.flt};
  const big=pr?`<figure class="pb-out">${printCanvas(x,t,pr,'big',pr.pkg==='double'?.62:pr.pkg==='big'?.5:.72)}<figcaption class="small">${t.trim?'✂️ Đã cắt, sẵn sàng giao':'🖨️ Vừa in xong'}</figcaption></figure>`
    :st.frame&&st.pkg?`<figure class="pb-out ghost">${printCanvas(x,t,cur,'big',st.pkg==='double'?.5:st.pkg==='big'?.42:.6)}<figcaption class="small muted">Bản xem trước · chưa in</figcaption></figure>`:'';
  const changed=pr&&(pr.pkg!==cur.pkg||pr.frame!==cur.frame||!sameSet(pr.pick,cur.pick)||!sameSet(pr.st,cur.st)||pr.date!==cur.date||pr.flt!==cur.flt);
  const k=pk.shots,ready=st.pkg&&st.frame&&(t.pick||[]).length===k;
  const ink=`<p class="small muted">🖨️ Cuộn mực còn <b>${Number(d.ribbon??0)}</b> tấm · ${x.esc(lower(PK(x,st.pkg||'strip').name))}: giấy còn ${stockOf(x,pk.paper)}</p>`;
  const print=t.trim?'':pr?(changed?x.confirmCmd('🖨️ In lại theo chỉnh mới','pb_print',{task:t.id},'In lại? Tờ ảnh vừa in bỏ đi, tiệm chịu tiền giấy.','pb-print-go',!ready):'')
    :x.cmd('🖨️ In ảnh','pb_print',{task:t.id},'primary pb-print-go',!ready||!d.ribbon);
  const trim=pr&&!t.trim?x.cmd(pr.pkg==='big'?'🪵 Lồng vào khung gỗ':pr.pkg==='double'?'✂️ Cắt đôi, bỏ 2 bao kiếng':'✂️ Cắt rìa, bỏ bao kiếng','pb_trim',{task:t.id},'primary pb-trim'):'';
  const ribbon=!d.ribbon?`<p class="notice small">Máy in hết mực. ${x.cmd('🖨️ Thay cuộn mực','pb_ribbon',{},'small',!stockOf(x,'muc'))}</p>`:'';
  return `<section class="card pb-printer"><h4>🖨️ Máy in & bàn cắt</h4>${ribbon}${big}${ink}<div class="sk-row pb-print-row">${print}${trim}</div>
    ${!ready&&!pr?`<p class="small muted">Chọn đủ ${k} tấm ở ③ trước khi in.</p>`:''}</section>`;
}

/* ------------------------------------------------------------ the morning */
function setupPanel(t,x){
  const d=data(x),b=d.booth||{},muc=stockOf(x,'muc');
  const test=b.tested?canvas(`test-${b.lens?1:0}${b.fog?1:0}`,cv=>{const c=fit(cv,156,97);PF.paintShot(c,{backdrop:'kem',light:'soft',people:[],props:[]},156,97);if(!b.lens||b.fog)fog(c,156,97);},'pb-test','Ảnh chụp thử'):'';
  return `<section class="card pb-setup"><h4>📷 Máy ảnh</h4>
    <div class="sk-row">${b.lens?'<span class="tag green">✓ Ống kính sạch</span>':x.cmd('🧽 Lau ống kính','pb_lens',{},'primary pb-lens')}${x.cmd('📸 Chụp thử phông trống','pb_test',{},`${b.tested?'ghost small':'primary'} pb-test-go`)}</div>${test}
    <h4 class="section-title">🖨️ Máy in</h4><p class="small">${b.tested?`Máy in báo cuộn mực còn <b>${Number(d.ribbon??0)}</b>/${Number(cc(x).ribbon||24)} tấm.`:'Chụp thử một tấm để máy in báo mực còn bao nhiêu.'}</p>
    <div class="sk-row">${x.cmd(`🖨️ Thay cuộn mực mới <small>(kho còn ${muc})</small>`,'pb_ribbon',{},'pb-ribbon',!muc)}</div>
    <p class="small muted">${x.esc(t.needs?.note||'')}</p></section>`;
}
function setupSteps(t,x){
  const d=data(x),b=d.booth||{},low=Number(cc(x).ribbon_low||4)+4,rows=[];
  rows.push({ok:b.lens?true:null,label:'Lau ống kính',go:{cmd:'pb_lens',payload:{},label:'🧽 Lau ống kính'}});
  rows.push({ok:b.tested?true:null,label:'Chụp thử một tấm',go:{cmd:'pb_test',payload:{},label:'📸 Chụp thử phông trống'}});
  if(b.tested&&Number(d.ribbon)<low)rows.push({ok:null,label:'Cuộn mực sắp hết: thay cuộn mới',note:`còn ${d.ribbon} tấm`,go:stockOf(x,'muc')?{cmd:'pb_ribbon',payload:{},label:'🖨️ Thay cuộn mực mới'}:null});
  return rows;
}

/* ------------------------------------------------------------ học nghề: the first customers with chị Lam */
function learnCard(x,full=true){
  const l=data(x).learn;if(!l?.on)return '';
  if(!full)return `<p class="pb-learn slim" aria-label="Học nghề">📷 Học nghề · khách ${Math.min(l.n+1,l.of)}/${l.of} · <b>${x.esc(l.title||'')}</b></p>`;
  return `<section class="card pb-learn" aria-label="Học nghề"><span class="eyebrow">📷 Học nghề với chị Lam · khách ${Math.min(l.n+1,l.of)}/${l.of}</span><b>${x.esc(l.title||'')}</b><p class="small">${x.esc(l.text||'')}</p><p class="small muted">Chị đứng cạnh máy in: lỡ sai chỗ nào, chị nhắc trước khi in.</p></section>`;
}

/* ------------------------------------------------------------ the guide */
/** The first customer ever: the morning set-up counts as served, so firstTime() alone would end the walk-through early. */
const isFirst=x=>firstTime(x)||!(Number(data(x).stats?.customers)>0);
/** The one button that sends this command with this payload (what a pointer arrow lands on). */
const ctl=(cmd,payload)=>`[data-command="${cmd}"][data-payload='${JSON.stringify(payload)}']`;
function orderSteps(t,x){
  const d=data(x),n=need(t),st=t.set||{},de=t.deco||{},shots=t.shots||[],k=kOf(x,t),rows=[];
  // first customer (the morning set-up is not one): the button does the step; later ones: it only points at the very control.
  const first=isFirst(x);
  const go=(cmd,payload,label,sel)=>first?{cmd,payload,label}:{sel:sel==null?ctl(cmd,payload):sel,label};
  if(!d.booth?.open)rows.push({ok:null,tab:'set',label:'Mở tiệm xong mới chụp',go:null});
  // ① the booth
  rows.push({ok:st.pkg===n.pkg?true:st.pkg?false:null,tab:'set',label:`Gói ${lower(PK(x,n.pkg).name)}`,go:go('pb_pkg',{task:t.id,pkg:n.pkg},`${PK(x,n.pkg).emoji} Gói ${x.esc(lower(PK(x,n.pkg).name))}`)});
  rows.push({ok:(n.frames||[]).includes(st.frame)?true:st.frame?false:null,tab:'set',label:`Khung ${(n.frames||[]).map(f=>NAME(x,'frames',f)).join(' / ')}`,
    go:go('pb_frame',{task:t.id,frame:n.frames[0]},`🖼️ Khung ${x.esc(NAME(x,'frames',n.frames[0]))}`)});
  rows.push({ok:(n.bd||[]).includes(st.bd)?true:st.bd?false:null,tab:'set',label:(n.bd||[]).map(b=>NAME(x,'backdrops',b)).join(' / '),
    go:go('pb_bd',{task:t.id,bd:n.bd[0]},`🎨 ${x.esc(NAME(x,'backdrops',n.bd[0]))}`)});
  for(const p of n.props||[])if(!(st.props||[]).includes(p))rows.push({ok:null,tab:'set',label:`Đưa khách ${lower(NAME(x,'props',p))}`,go:go('pb_prop',{task:t.id,prop:p},`🎩 ${x.esc(NAME(x,'props',p))}`)});
  for(const p of st.props||[])if(!(n.props||[]).includes(p))rows.push({ok:false,tab:'set',label:`Khách không dặn ${lower(NAME(x,'props',p))}`,go:go('pb_prop',{task:t.id,prop:p},`↩️ Cất ${x.esc(lower(NAME(x,'props',p)))}`)});
  if(sameSet(st.props,n.props))rows.push({ok:true,tab:'set',label:n.props?.length?`Đạo cụ: ${n.props.map(p=>lower(NAME(x,'props',p))).join(', ')}`:'Không đạo cụ'});
  rows.push({ok:st.light===n.light?true:st.light?false:null,tab:'set',label:NAME(x,'lights',n.light),go:go('pb_light',{task:t.id,light:n.light},`${LIGHT_EMOJI[n.light]||'💡'} ${x.esc(NAME(x,'lights',n.light))}`)});
  // ② the camera: good shots taken with the booth as asked
  const right=s=>(n.bd||[]).includes(s.bd)&&s.light===n.light&&sameSet(s.props,n.props)&&!s.haze;
  const good=shots.filter(s=>s.q==='good'&&right(s)).length,max=Number(cc(x).max_shots||8),setOk=st.bd&&(n.bd||[]).includes(st.bd)&&st.light===n.light&&sameSet(st.props,n.props);
  if(d.booth?.fog)rows.push({ok:false,tab:'shoot',label:'Ống kính mờ hơi nước',go:{cmd:'pb_lens',payload:{},label:'🧽 Lau ống kính'}});
  if(t.want==null){
    let g=null;
    // The first customer: the big bottom button is the shutter too (a stop tap like the one on the camera).
    if(t.cam)g=first?{cmd:'pb_snap',payload:{task:t.id},label:'📸 BẤM MÁY'}:{sel:'.pb-snap',label:'📸 Bấm máy lúc cả nhóm đứng yên, mở mắt'};
    else if(shots.length>=max||(shots.length&&!setOk&&shots.some(s=>!right(s))&&good<k&&shots.length+k-good>max))g={cmd:'pb_redo',payload:{task:t.id},confirm:'Xóa hết ảnh lượt này rồi chụp lại từ đầu?',label:'🔄 Xóa, chụp lượt mới'};
    else if(setOk||!first)g=go('pb_shoot',{task:t.id},'⏱️ Bắt đầu đếm 3-2-1','.pb-shoot');
    rows.push({ok:good>=k?true:null,tab:'shoot',label:`Chụp ${k} tấm đẹp`,note:`${good}/${k}`,go:good>=k?null:g});
    rows.push({ok:null,tab:'shoot',label:'Cho khách xem, chọn ảnh',go:shots.length?go('pb_show',{task:t.id},'🖥️ Cho khách xem ảnh','.pb-show'):null});
  }else rows.push({ok:true,tab:'shoot',label:`Khách chọn tấm ${t.want.map(i=>i+1).join(', ')}`});
  // ③ the customers' choice and the decoration
  if(t.want!=null){
    const pick=t.pick||[],okPick=sameSet(pick,t.want);
    const extra=pick.find(i=>!t.want.includes(i)),miss=t.want.find(i=>!pick.includes(i));
    rows.push({ok:okPick?true:extra!=null?false:null,tab:'pick',label:`Chọn đúng tấm ${t.want.map(i=>i+1).join(', ')}`,note:`${pick.length}/${k}`,
      go:okPick?null:extra!=null?go('pb_pick',{task:t.id,i:extra},`↩️ Bỏ tấm ${extra+1}`):go('pb_pick',{task:t.id,i:miss},`☑️ Chọn tấm ${miss+1}`)});
  }
  for(const s of n.st||[])if(!(de.st||[]).includes(s))rows.push({ok:null,tab:'pick',label:`Dán ${lower(NAME(x,'stickers',s))}`,go:go('pb_sticker',{task:t.id,st:s},`✨ ${x.esc(NAME(x,'stickers',s))}`)});
  if(!n.free)for(const s of de.st||[])if(!(n.st||[]).includes(s))rows.push({ok:false,tab:'pick',label:`Khách không dặn ${lower(NAME(x,'stickers',s))}`,go:go('pb_sticker',{task:t.id,st:s},`↩️ Gỡ ${x.esc(lower(NAME(x,'stickers',s)))}`)});
  rows.push({ok:de.date===n.date?true:null,tab:'pick',label:n.date?'Đóng ngày tháng':'Không ghi ngày',go:go('pb_date',{task:t.id,on:!!n.date},n.date?'📅 Có ngày':'Không ghi ngày')});
  rows.push({ok:de.flt===n.flt?true:null,tab:'pick',label:fltText(x,n.flt).replace(/^./,c=>c.toUpperCase()),go:go('pb_filter',{task:t.id,flt:n.flt},`🎞️ ${x.esc(NAME(x,'filters',n.flt))}`)});
  // ④ the printer and the trimming table
  const pr=t.printed,cur=pr&&pr.pkg===st.pkg&&pr.frame===st.frame&&sameSet(pr.pick,t.pick)&&sameSet(pr.st,de.st)&&pr.date===de.date&&pr.flt===de.flt;
  if(!t.trim)rows.push({ok:cur?true:pr?false:null,tab:'print',label:pr&&!cur?'In lại theo chỉnh mới':'In ảnh',
    go:(t.pick||[]).length===k&&st.frame&&st.pkg?(pr?{cmd:'pb_print',payload:{task:t.id},confirm:'In lại? Tờ ảnh vừa in bỏ đi, tiệm chịu tiền giấy.',label:'🖨️ In lại'}:go('pb_print',{task:t.id},'🖨️ In ảnh','.pb-print-go')):null});
  rows.push({ok:t.trim?true:null,tab:'print',label:PK(x,st.pkg||n.pkg).frame?'Lồng khung':'Cắt, bỏ bao kiếng',go:pr?go('pb_trim',{task:t.id},PK(x,pr.pkg).frame?'🪵 Lồng vào khung gỗ':'✂️ Cắt, bỏ bao kiếng','.pb-trim'):null});
  return rows;
}
/** Which tab the work is on: the player's own pick for this customer, else the first with something left. */
function tabOf(t,x,steps){
  const own=x.ui.tab;if(own?.id===t.id&&TABS.some(([k])=>k===own.tab))return own.tab;
  const n=pending(steps);return n?.tab||'print';
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở tiệm',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'pb_intro',payload:{},label:'📸 Vào việc thôi!'}}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'📸 MỞ TIỆM',go:finalGo(steps,'pb_open',{task:t.id}),ready:true}};}
  if(!t.known)return {steps:[{ok:null,label:'Hỏi khách',go:{cmd:'ask',payload:{task:t.id},label:'👂 Hỏi khách muốn chụp gì'}}],final:null,pulse:'.sk-ask'};
  if(t.stage==='pay'){const s=changeStep(x,t.id,t.cash),steps=s?[s]:[];return {steps,final:{label:'💵 ĐƯA TIỀN THỐI',go:finalGo(steps,'pb_pay',{task:t.id,...changePayload(x,t.id,t.cash)}),ready:true}};}
  const steps=orderSteps(t,x),tab=tabOf(t,x,steps),first=isFirst(x);
  // A pointer at a control on another tab first opens that tab (it never does the step).
  for(const s of steps)if(s.go?.sel&&s.tab&&s.tab!==tab)s.go={act:'car:tab',data:{tab:s.tab,task:t.id},label:`👉 Sang mục ${TABS.find(([k])=>k===s.tab)[1]}`};
  const pk=PK(x,need(t).pkg),out=!t.printed&&(!stockOf(x,pk.paper)||(pk.frame&&!stockOf(x,pk.frame)));
  if(out)return {steps,tab,final:{label:'🙏 Nói thật: tiệm hết giấy, khung',go:{cmd:'pb_decline',payload:{task:t.id}},ready:true},first};
  return {steps,tab,first,final:{label:'🖼️ ĐƯA ẢNH',go:finalGo(steps,'pb_serve',{task:t.id}),ready:!!t.trim,why:'in và cắt ảnh trước đã'}};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse,glow:!!g.first});
function tabsRow(t,x,tab,steps){
  return `<div class="pb-tabs" role="tablist">${TABS.map(([k,l])=>{const left=steps.filter(s=>s.tab===k&&s.ok!==true).length;
    return act(x,`${x.esc(l)}${left?`<small>${left}</small>`:'<small>✓</small>'}`,'tab',{tab:k,task:t.id},`pb-tab ${k===tab?'on':''}`,` role="tab" aria-selected="${k===tab}"`);}).join('')}</div>`;
}

/* ------------------------------------------------------------ idle: the shop between customers */
function shopView(x){
  const d=data(x),b=d.booth||{};
  const wall=PF.FRAMES.slice(0,14).map(f=>`<li>${canvas(`wall-${f.id}`,cv=>PF.thumb(cv,f.id,{layout:'strip',scale:.12,t:x.t}),'pb-wallcv',x.esc(NAME(x,'frames',f.id)))}</li>`).join('');
  const items=['giay_dai','giay_doi','giay_lon','khung','bao','muc'].map(k=>`${k==='muc'?'🖨️':k==='khung'?'🪵':k==='bao'?'🛍️':'📄'} ${stockOf(x,k)}`).join(' · ');
  return `<section class="card pb-shop"><h4>🎞️ Tường khung mẫu</h4><ul class="pb-wall">${wall}</ul>
    <p class="small muted">${b.open?(b.lens&&!b.fog?'📷 Ống kính sạch':'💧 Ống kính cần lau'):'Tiệm chưa mở'} · 🖨️ mực còn ${Number(d.ribbon??0)} tấm</p><p class="small muted">Kho: ${items}</p></section>`;
}

export default {
  id:'photobooth',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='setup'?'Lau ống kính, mở tiệm':!t.known?'Hỏi khách muốn chụp gì':'Chụp ảnh cho khách';
  },
  job(t,x){
    PAINT.clear();LIVE=null;
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'pb_intro','📸')}${deskCard(x,'pb_desk','Chuyện ở tiệm')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk pb">${hint}${top}${bottom(x,g)}</div>`;
    let main='',side='',tabs='';
    if(t.kind==='setup'){main=setupPanel(t,x);side=stepRows(x,g.steps,'Việc mở tiệm');}
    else if(!t.known)main='';
    else if(t.stage==='pay')main=`${cashPanel(x,t.id,t.cash)}${t.printed?`<figure class="pb-out">${printCanvas(x,t,t.printed,'big',t.printed.pkg==='double'?.62:t.printed.pkg==='big'?.5:.72)}</figure>`:''}`;
    else{
      const tab=g.tab||'set';tabs=tabsRow(t,x,tab,g.steps);
      main=tab==='set'?setPanel(t,x):tab==='shoot'?camPanel(t,x):tab==='pick'?pickPanel(t,x):printPanel(t,x);
      side=stepRows(x,g.steps.filter(s=>s.tab===tab),'Việc của bước này');
    }
    const at=!t.known?'set':t.stage==='pay'?'pay':g.tab||'set';
    const head=t.kind==='setup'?dayBar(x):`${learnCard(x,at==='set')}${ticket(t,x,at)}${dayBar(x)}`;
    const bench=`${tabs}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>`;
    // Reading the order comes first; past it the hands-on part leads (the camera must be in view while counting down).
    const body=t.kind==='setup'||at==='set'?`${head}${bench}`:`${bench}${head}`;
    return `<div class="career-job sk pb">${hint}${top}${body}${bottom(x,g)}</div>`;
  },
  idle(x){
    PAINT.clear();LIVE=null;
    const d=data(x),top=`${introCard(x,'pb_intro','📸')}${deskCard(x,'pb_desk','Chuyện ở tiệm')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở tiệm',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'pb_intro',payload:{},label:'📸 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk pb">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk pb">${top}${dayBar(x)}${shopView(x)}</div>`;
  },
  // Pictures are drawn here, right after a render (and the camera five times a second): the bar glides on the
  // compositor (ctx.slide), the words and the camera's screen change with the countdown.
  meters(root,x){
    for(const cv of root.querySelectorAll('canvas[data-pb-k]')){const k=cv.dataset.pbK;if(cv._k===k)continue;const f=PAINT.get(k);if(!f)continue;try{f(cv);cv._k=k;}catch(error){console.error(error);}}
    const live=root.querySelector('canvas[data-pb-live]'),box=root.querySelector('[data-pb-cam]');
    if(!box){if(live)paintLive(live,'idle');return;}
    const b=LIVE?.b||{count:3,lead:.4,hold:1.3,blink:1.2},[count,lead,hold,blink]=box.dataset.beat.split(',').map(Number),beat={count,lead,hold,blink};
    const span=count+lead+hold+blink+1.2,el=x.now()-Number(box.dataset.pbCam);
    x.slide(root.querySelector('.pb-needle'),el/span*100,100/span);
    const [phase,say]=camPhase(el,beat||b);
    const cnt=box.querySelector('.pb-count'),words=phase.startsWith('count')?String(3-Math.floor(el)):phase==='hold'?'📸':'';
    if(cnt&&cnt.textContent!==words)cnt.textContent=words;
    const line=root.querySelector('[data-pb-say]');if(line&&line.textContent!==say)line.textContent=say;
    box.classList.toggle('ready',phase==='hold');box.classList.toggle('over',phase==='blink'||phase==='late');
    if(live)paintLive(live,phase);
  },
  tapStop:op=>op==='pb_snap',
  tick(root){keepBarAboveFooter(root);},
  summary(sum,x){
    if(!sum||sum.shots==null)return '';
    const row=(l,v)=>`<div class="kv-row"><span>${l}</span><b>${v}</b></div>`,tm=sum.tomorrow,names={giay_dai:'giấy dải',giay_doi:'giấy tờ đôi',giay_lon:'giấy ảnh lớn',khung:'khung gỗ',bao:'bao kiếng',muc:'cuộn mực'};
    const lines=[Number(sum.ribbon)<8?`🖨️ Cuộn mực còn <b>${Number(sum.ribbon)}</b> tấm: sáng mai thay cuộn mới`:'',
      sum.low?.length?`📦 Sắp hết: ${sum.low.map(k=>x.esc(names[k]||k)).join(' · ')}`:''].filter(Boolean);
    const plan=`<section class="pb-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>${tm?`<p class="pb-tomorrow"><span aria-hidden="true">${x.esc(tm.emoji)}</span> <b>Mai: ${x.esc(tm.label)}</b><small>${x.esc(tm.hint)}</small></p>`:''}${lines.length?`<ul class="pb-plan-list">${lines.map(l=>`<li>${l}</li>`).join('')}</ul>`:''}${x.button('🧺 Mở Kho','warehouse',{},'primary small pb-plan-go')}</section>`;
    const rate=sum.shots?Math.round(sum.good*100/sum.shots):0;
    const kv=`<div class="kv">${row('Lượt khách',sum.customers)}${row('Kiểu đã chụp',sum.shots)}${row('Bấm đúng lúc',`${sum.good} (${rate}%)`)}${row('Tấm đã in',sum.prints)}</div>${(sum.lines||[]).length?`<ul class="small">${sum.lines.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul>`:''}${sum.note?`<p class="small muted">${x.esc(sum.note)}</p>`:''}`;
    return `<article class="card space-top pb-sum">${plan}<details class="pb-sum-more"><summary>📸 Tiệm ảnh hôm nay · ${sum.customers} lượt khách · ${sum.prints} tấm in</summary>${kv}</details></article>`;
  },
  actions:{...tillActions,...kitActions,
    async tab(d,el,x){x.ui.tab={id:d.task,tab:d.tab};x.render();},
  },
  dock:[['inventory','box','Kho tiệm ảnh','Giấy in, khung gỗ, bao kiếng, cuộn mực…']],
};
