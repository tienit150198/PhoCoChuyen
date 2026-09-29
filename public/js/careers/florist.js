/** Tiệm Hoa Nắng — florist workbench. The day strip, the customer queue, the
 * order (what the customer said, what is still worth asking, the pieces of a
 * set), station tabs whose tiles carry stock badges and padlocks, live soak /
 * foam bars with a green zone, and one big "Giao". Only renders server state
 * and sends commands; the server checks every rule and keeps what the customer
 * has not said yet out of the public view. */
import {dayStrip,flash,eventCard,queue,actionBar,keepBarAboveFooter,idlePanel,gradeCard,patience} from './food_kit.js';
import {reqList,fold} from '../ui-kit.js';

const METER_SCALE=20;   // seconds shown on the soak / foam bars
const VALUE_SCALE=1.2;  // value bar runs to 120% of the budget

const pay=(x,o)=>x.esc(JSON.stringify(o));
const cc=x=>x.cc||{};
const data=x=>x.room.data||{};
const lower=s=>String(s||'').toLowerCase();
const find=(list,id,fallback)=>(list||[]).find(v=>v.id===id)||fallback;
const flower=(x,id)=>find(cc(x).flowers,id,{id,name:id,emoji:'🌼',color:'white',role:'focal',unlock:1,good:[],bad:[],taboo:[],meaning:''});
const format=(x,id)=>find(cc(x).formats,id,{id,name:id,emoji:'💐',uses:{},foam:false,soak:true,wrap:false,unlock:1});
const colour=(x,id)=>find(cc(x).colors,id,{id,name:id,hex:'#eeeeee'});
const paper=(x,id)=>find(cc(x).papers,id,{id,name:id,hex:'#eeeeee',item:''});
const ribbon=(x,id)=>find(cc(x).ribbons,id,{id,name:id,hex:'#eeeeee'});
const occasion=(x,id)=>find(cc(x).occasions,id,{id,name:id,emoji:'💐',celebrate:true});
const topic=(x,id)=>find(cc(x).topics,id,{id,emoji:'❓',label:id});
const slotName=(x,id)=>find(cc(x).slots,id,{name:id}).name;
const item=(x,id)=>(x.content.inventory?.items?.florist||[]).find(i=>i.id===id)||{id,name:id,unit:''};
const stock=(x,id)=>x.room.inventory?.stock?.[id]??0;
const lvl=x=>x.room.level||1;
const today=x=>x.room.day||1;
const letters=s=>String(s||'').normalize('NFC').toLocaleLowerCase('vi').replace(/[^\p{L}\p{N}\s]/gu,' ').split(/\s+/).filter(Boolean).join(' ');
const counts=stems=>stems.reduce((m,s)=>(m[s.i]=(m[s.i]||0)+1,m),{});
const soaking=t=>!!t.work.soak;
const soakMin=(t,x)=>data(x).soak_min||t.soak_min||cc(x).soak_min||8;
const rainy=x=>!!data(x).rain;
// Drawn look on the bench: one rose glyph tinted per colour reads better than
// unrelated emoji (the shared inventory keeps the distinct server emoji).
const LOOK={rose_red:['🌹',''],rose_pink:['🌹','pink'],rose_white:['🌹','white'],rose_yellow:['🌹','yellow'],lily:['🌷','white'],carnation:['🌺','pink'],orchid:['🌸','purple']};
const look=(x,id)=>{const l=LOOK[id];return l?{emoji:l[0],tint:l[1]}:{emoji:flower(x,id).emoji,tint:''};};
const glyph=(x,id,cls='')=>{const l=look(x,id);return `<span class="fl-glyph ${l.tint?'fl-tint '+l.tint:''} ${cls}" aria-hidden="true">${x.esc(l.emoji)}</span>`;};

/* ---------- order shape (mirrors the server) ---------- */
const isSet=t=>!!t.needs?.party?.length;
const spec=(t,i)=>{const n=t.needs,p=n?.party;if(!p?.length)return n;return {...n,...p[i??t.cur??0]};};
const plated=t=>isSet(t)&&!!t.pieces?.[t.cur];
const pendingOthers=t=>isSet(t)?(t.pieces||[]).map((p,i)=>p?-1:i).filter(i=>i>=0&&i!==t.cur):[];
const started=w=>!!(w&&(w.stems?.length||w.base));
const known=(t,k)=>!(t.needs?.hidden||[]).includes(k)||(t.asked||[]).includes(k);
const unasked=t=>(t.needs?.hidden||[]).filter(k=>!(t.asked||[]).includes(k));
const deliver=t=>!!(t.needs?.deliver??t.needs?.delivery);

/* ---------- building blocks ---------- */
/** A tile button: stock badge (red at 0), selected outline, padlock, dot for what the order needs. */
function tile(x,o){
  const attrs=o.cmd?`data-command="${o.cmd}" data-payload="${pay(x,o.payload||{})}"`
    :o.action?`data-action="car:${o.action}"${Object.entries(o.data||{}).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}`:'';
  const cls=['tile',o.cls||'',o.selected?'is-selected':'',o.locked?'is-locked':'',o.empty?'is-empty':'',o.wanted?'wanted':''].filter(Boolean).join(' ');
  const badge=o.count!=null&&!o.locked?`<span class="count-badge${o.empty?' is-empty':''}" data-count="${x.esc(String(o.count))}">${x.esc(String(o.count))}</span>`:'';
  return `<button type="button" class="${cls}" ${attrs}${o.disabled||o.locked?' disabled':''} aria-pressed="${o.selected?'true':'false'}"${o.label?` aria-label="${x.esc(o.label)}"`:''}>${badge}<span class="tile-emoji" aria-hidden="true">${o.glyph||x.esc(o.emoji||'')}</span><b>${x.esc(o.name)}</b>${o.sub?`<small>${x.esc(o.sub)}</small>`:''}${o.flag?`<small class="fl-flag ${o.flagCls||''}">${x.esc(o.flag)}</small>`:''}</button>`;
}
const swatch=(x,o)=>`<button type="button" class="fl-swatch ${o.selected?'on is-selected':''}" data-command="${o.cmd}" data-payload="${pay(x,o.payload)}"${o.disabled?' disabled':''} aria-pressed="${o.selected?'true':'false'}"><i style="background:${x.esc(o.hex)}"></i>${x.esc(o.name)}${o.count!=null?`<span class="fl-swatch-n${o.count?'':' zero'}">${x.esc(String(o.count))}</span>`:''}</button>`;
const seg=(x,action,key,value,label,current)=>`<button type="button" class="fl-seg ${current===value?'on is-selected':''}" data-action="car:${action}" data-${key}="${x.esc(value)}" aria-pressed="${current===value}">${x.esc(label)}</button>`;
const checklist=(x,rows,label)=>reqList(rows.map(([ok,lab,note])=>({ok,label:lab,note})),x.esc,label);
const meter=(cls,attrs,zones,fill,label)=>`<div class="fl-meter ${cls}" ${attrs}><div class="fl-track">${zones.map(([k,a,b])=>`<i class="fl-zone ${k}" style="left:${a}%;width:${Math.max(0,b-a)}%"></i>`).join('')}<b class="fl-fill" style="width:${Math.min(100,Math.max(0,fill))}%"></b></div><small class="fl-meter-label">${label}</small></div>`;
const freshLabel=left=>left==null?'hết hàng':left<=0?'⚠️ sắp héo':left===1?'còn 1 ngày':'tươi';

/* ---------- real-time bars (the server decides from its own clock) ---------- */
function soakMeter(x,start,min){
  const sec=start?Math.max(0,x.now()-start):0,p=v=>v/METER_SCALE*100;
  return meter('soak',`data-soak-start="${start||''}" data-min="${min}"`,[['thirsty',0,p(min)],['full',p(min),100]],p(sec),start?`${sec.toFixed(1)} giây · ${sec<min?'đang hút nước…':'ĐỦ NƯỚC — nhấc ra'}`:`Xô đang trống · vùng xanh từ ${min} giây`);
}
function foamMeter(x,foam,min){
  const sec=foam?Math.max(0,x.now()-foam.start):0,p=v=>v/METER_SCALE*100;
  const label=!foam?'':foam.pushed?'Mút bị ấn chìm — lõi còn khô':sec<min?`${sec.toFixed(1)} giây · mút đang tự chìm…`:'MÚT ĐÃ NGẤM ĐỀU';
  return meter('foam',`data-foam-start="${foam&&!foam.pushed?foam.start:''}" data-min="${min}"`,[['thirsty',0,p(min)],['full',p(min),100]],foam?.pushed?100:p(sec),label);
}
function valueMeter(t,x){
  const sp=spec(t),b=sp.budget||1,v=t.work.value||0,p=r=>r/VALUE_SCALE*100;
  const note=v>b?' · vượt ngân sách, tiệm chịu phần dư':'';
  return meter('value','',[['thin',0,p(.5)],['low',p(.5),p(.7)],['ok',p(.7),p(.85)],['full',p(.85),p(1)],['over',p(1),100]],p(v/b),`Hoa trên bàn đáng ~${v} xu · ${Math.round(v/b*100)}% ngân sách hoa${note}`);
}

/* ---------- preview ---------- */
function spots(n,base){
  const out=[];
  for(let i=0;i<n;i++){
    if(base==='wreath'){const a=i/n*Math.PI*2-Math.PI/2,r=i%2?30:36;out.push([50+r*Math.cos(a),44+r*Math.sin(a)*.92]);continue;}
    const r=Math.sqrt((i+.5)/Math.max(1,n))*34,a=i*2.39996;
    out.push([50+r*Math.cos(a),(base==='bouquet'?36:40)+r*Math.sin(a)*.72]);
  }
  return out;
}
function stage(t,x){
  const w=t.work,day=today(x);
  if(plated(t))return `<div class="fl-empty ok"><span aria-hidden="true">🎁</span><p class="small">Đủ ${t.pieces.length} món trên bàn chờ</p></div>`;
  if(!w.stems.length&&!w.base)return `<div class="fl-empty"><span aria-hidden="true">💐</span><p class="muted small">Chọn hoa trong tủ mát</p></div>`;
  const order={focal:0,filler:1,green:2};
  const stems=[...w.stems].sort((a,b)=>(order[flower(x,a.i).role]??0)-(order[flower(x,b.i).role]??0));
  const head=(s,style)=>{const f=flower(x,s.i),l=look(x,s.i),left=s.e-day;return `<span class="fl-head ${x.esc(f.role)} ${l.tint?'fl-tint '+l.tint:''} ${left<=0?'wilt':''} ${s.h?'':'dry'}"${style?` style="${style}"`:''} title="${x.esc(f.name)}">${x.esc(l.emoji)}</span>`;};
  if(soaking(t))return `<div class="fl-stage fl-bucket" role="img" aria-label="Hoa đang ngâm trong xô"><div class="fl-loose">${stems.map(s=>head(s)).join('')}</div><i class="fl-pail"></i></div>`;
  if(!w.arranged){
    return `<div class="fl-stage loose" role="img" aria-label="Cành hoa trên bàn">${w.base?`<p class="small muted">${x.esc(format(x,w.base).emoji)} ${x.esc(format(x,w.base).name)} đã sẵn sàng</p>`:''}<div class="fl-loose">${stems.map(s=>head(s)).join('')}</div></div>`;
  }
  const pos=spots(stems.length,w.base);
  const heads=stems.map((s,i)=>head(s,`left:${pos[i][0].toFixed(1)}%;top:${pos[i][1].toFixed(1)}%;z-index:${40-i}`)).join('');
  const wrap=w.base==='bouquet'?`<i class="fl-wrap ${w.paper?'':'bare'}" style="--paper:${x.esc(w.paper?paper(x,w.paper).hex:'#8fb07f')}"></i>`:'';
  const bow=w.ribbon?`<i class="fl-bow" style="--rib:${x.esc(ribbon(x,w.ribbon).hex)}"></i>`:'';
  const banner=w.base==='wreath'?`<div class="fl-banner"><span data-banner-live>${x.esc(w.banner||'')}</span></div>`:'';
  const cover=w.cover?'<i class="fl-cover" aria-hidden="true"></i>':'';
  return `<div class="fl-stage arranged base-${x.esc(w.base)}" role="img" aria-label="${x.esc(format(x,w.base).name)}${w.cover?', đã bọc nylon':''}">${wrap}<i class="fl-base"></i><div class="fl-heads">${heads}</div>${bow}${banner}${cover}</div>`;
}
function cardPreview(t,x){
  if(plated(t)||(!spec(t).card&&!t.work.card))return '';
  const tone=t.card_tone,cls=tone==='fit'?'good':tone==='wrong'?'bad':tone==='plain'?'warn':'';
  const card=`<div class="fl-card ${cls}"><span class="fl-card-fold" aria-hidden="true">💌</span><p data-card-live>${x.esc(t.work.card||'')}</p></div>`;
  // Phones: an empty card only takes room; it shows once something is written.
  return t.work.card||x.ui.tab==='card'?card:`<div class="fk-wide-only">${card}</div>`;
}
/** Pieces of a set: 🌸 done, 💐 on the bench, ◌ waiting. */
function pieceChips(t){
  if(!isSet(t))return '';
  return `<p class="fl-pieces" aria-label="Các món trong bộ">${t.pieces.map((p,i)=>`<span class="${p?'on':''}${i===t.cur&&!p?' cur':''}" title="Món ${i+1}">${p?'🌸':i===t.cur?'💐':'◌'}<small>${i+1}</small></span>`).join('')}</p>`;
}
/** Live one-line status of what is on the bench. */
function status(t,x){
  const w=t.work,tag=isSet(t)?`Món ${t.cur+1}: `:'';
  if(plated(t))return `Đủ ${t.pieces.length} món, chờ giao cả bộ`;
  if(!w.stems.length&&!w.base)return tag+'bàn cắm còn trống';
  const parts=[`${w.stems.length} cành`];
  if(soaking(t))parts.push('đang ngâm xô');
  else if(w.stems.length&&w.stems.every(s=>s.h))parts.push('đã hút no nước');
  if(w.base)parts.push(lower(format(x,w.base).name));
  if(w.arranged)parts.push('đã cắm xong');
  if(w.paper)parts.push('đã gói giấy');
  if(w.ribbon)parts.push('có ruy băng');
  if(w.card)parts.push('có thiệp');
  if(w.cover)parts.push('đã bọc nylon');
  return tag+parts.join(' · ');
}

/* ---------- the brief (ticket) and the bench steps (side), live ✓/✗/○ ---------- */
/** What the customer asked for, checked against what is on the bench (ui-kit reqList rows). */
function briefRows(t,x){
  const n=t.needs,sp=spec(t),w=t.work,st=plated(t)?[]:w.stems,c=counts(st),total=st.length,any=total?true:null,f=format(x,sp.format),out=[];
  if(plated(t))return [{ok:true,icon:'🎁',label:`Đủ ${t.pieces.length} món, giao cả bộ một lượt`}];
  out.push({ok:w.base?w.base===sp.format:null,icon:f.emoji,label:f.name,note:w.base&&w.base!==sp.format?`đang làm ${lower(format(x,w.base).name)}`:''});
  // Still picking: too few is "not yet" (○), too many or finished short is wrong (✗).
  const upTo=(have,lo,hi)=>!have?null:have>hi?false:have>=lo?true:w.arranged?false:null;
  out.push({ok:upTo(total,sp.stems[0],sp.stems[1]),icon:'🌿',label:`${sp.stems[0]}–${sp.stems[1]} cành`,value:total?`${total} cành`:''});
  if(sp.focal){const have=c[sp.focal.item]||0;out.push({ok:upTo(have,sp.focal.count,sp.focal.count),icon:look(x,sp.focal.item).emoji,label:`Đúng ${sp.focal.count} cành ${lower(flower(x,sp.focal.item).name)}`,value:have?`${have}/${sp.focal.count}`:''});}
  if(sp.palette){
    const allowed=new Set([...sp.palette,'green']);
    const off=[...new Set(st.map(s=>flower(x,s.i)).filter(fl=>fl.role!=='filler'&&!allowed.has(fl.color)).map(fl=>colour(x,fl.color).name))];
    out.push({ok:any&&!off.length,icon:'🎨',label:`Tông ${sp.palette.map(p=>colour(x,p).name).join(' – ')}`,note:off.length?`lệch: ${off.join(', ')}`:''});
  }else out.push({ok:null,icon:'🎨',label:'Màu người nhận thích: chưa hỏi',tone:'warn'});
  if(n.cats===true){
    const toxic=st.some(s=>flower(x,s.i).cats==='toxic'),caution=st.some(s=>flower(x,s.i).cats==='caution');
    out.push({ok:toxic?false:any,icon:'🐈',label:'Nhà có mèo: không hoa ly (độc với mèo)',tone:'danger',note:toxic?'Trên bàn đang có hoa ly — bỏ ra!':caution?'Baby, bạch đàn: mèo gặm dễ đau bụng, nên tránh.':''});
  }else if(n.cats==null)out.push({ok:null,icon:'🏠',label:'Nhà người nhận: chưa hỏi',tone:'warn',note:'Có nuôi mèo không? Hoa ly độc với mèo.'});
  if(sp.card)out.push({ok:w.card?t.card_tone!=='wrong':null,icon:'💌',label:'Kèm thiệp viết tay',note:t.card_tone==='plain'?'lời hơi chung chung':t.card_tone==='wrong'?'lời không hợp dịp':''});
  if(sp.banner)out.push({ok:w.banner?letters(w.banner)===letters(sp.banner):null,icon:'🎗️',label:`Băng rôn “${sp.banner}”`,note:w.banner&&letters(w.banner)!==letters(sp.banner)?`đang in “${w.banner}”`:''});
  if(deliver(t)){
    if(n.delivery)out.push({ok:x.ui.slot?x.ui.slot===n.delivery:null,icon:'🛵',label:`Giao ${slotName(x,n.delivery)}`,note:x.ui.slot&&x.ui.slot!==n.delivery?`đang chọn ${slotName(x,x.ui.slot)}`:''});
    else out.push({ok:null,icon:'🛵',label:'Giao tận nơi · chưa hỏi giờ',tone:'warn'});
    if(rainy(x))out.push({ok:w.cover?true:null,icon:'🌧️',label:'Bọc nylon chống mưa'});
  }
  return out;
}
/** How the piece is made: freshness, conditioning, base, wrapping. */
function stepRows(t,x){
  const sp=spec(t),w=t.work,f=format(x,sp.format),st=w.stems,day=today(x),out=[];
  if(plated(t))return [];
  const total=st.length,any=total?true:null;
  const wilt=st.filter(s=>s.e-day<=0).length;
  out.push([any&&!wilt,'Cành tươi, không héo',wilt?`${wilt} cành sắp héo`:'']);
  const uncut=st.filter(s=>!s.c).length,straight=st.filter(s=>s.c===2).length;
  out.push([total?(uncut?null:!straight):null,'Cắt xéo gốc 45°',straight?`${straight} gốc cắt thẳng`:uncut?`${uncut} cành chưa cắt`:'']);
  const bare=st.filter(s=>!s.s).length;
  out.push([total?(bare?null:true):null,'Tuốt lá dưới mực nước',bare?`${bare} cành còn lá gốc`:'']);
  if(f.soak){const dry=st.filter(s=>!s.h).length;out.push([total?(dry?null:true):null,`Ngâm nước ≥ ${soakMin(t,x)} giây`,soaking(t)?'đang ngâm…':dry?`${dry} cành chưa ngâm`:'']);}
  if(f.foam)out.push([w.foam?(w.foam.pushed?false:(w.arranged||x.now()-w.foam.start>=(t.foam_min||10))?true:null):null,'Mút tự chìm, ngấm đều',w.foam?.pushed?'đã ấn chìm':'']);
  out.push([w.arranged||null,{bouquet:'Bó xoắn ốc',vase:'Cắm bình',basket:'Cắm giỏ',wreath:'Cắm kệ'}[sp.format]||'Cắm hoa','']);
  if(f.wrap)out.push([w.paper?true:null,'Gói giấy',w.paper?paper(x,w.paper).name:'']);
  out.push([w.ribbon?true:null,'Thắt ruy băng',w.ribbon?ribbon(x,w.ribbon).name:'']);
  return out;
}
/** Both lists as [ok,…] pairs, for "is everything right?" before the hand-off. */
function rows(t,x){return [...briefRows(t,x).map(r=>[r.ok]),...stepRows(t,x)];}

/* ---------- today: rules and the wedding pins ---------- */
function banners(x){
  const d=data(x),r=d.rules||{},out=[];
  if(r.influencer==='next')out.push('📱 Đơn giao tiếp theo sẽ lên clip. Làm thật chuẩn nhé!');
  if(r.bruised)out.push('🥀 Hồng đỏ hôm nay dập mép cánh: bó nào dùng hồng đỏ sẽ bị chê.');
  if(r.warm)out.push(`🔌 Tủ mát mất điện: hoa mềm cánh, độ tươi tối đa ${5-r.warm} sao.`);
  if(d.rain)out.push('🌧️ Trời mưa: đơn giao tận nơi nhớ bọc nylon trước khi đi.');
  if(d.soak_min&&d.soak_min>(cc(x).soak_min||8))out.push(`☀️ Nắng gắt: ngâm xô ít nhất ${d.soak_min} giây.`);
  const c=d.care||{},due=(c.pre||[]).filter(b=>b.status==='booked'&&b.left<=0).map(b=>b.title);
  if(c.sub?.menu)due.push('bình hoa của bà Tám');
  if(due.length)out.push(`📅 Hôm nay phải giao: ${due.join(', ')}.`);
  return out.length?`<ul class="fl-today">${out.map(s=>`<li>${x.esc(s)}</li>`).join('')}</ul>`:'';
}
function pinsCard(x){
  const d=data(x),p=d.rules?.pins;
  if(!p||p.status!=='open')return '';
  const recipe=cc(x).pin_recipe||{rose_white:1,babys_breath:1,ribbon:1};
  const can=Object.entries(recipe).every(([k,q])=>stock(x,k)>=q);
  const left=Math.max(0,p.due-(Number(d.day?.served)||0));
  const parts=Object.entries(recipe).map(([k,q])=>{const s=stock(x,k);return `<span class="fl-need${s>=q?'':' zero'}">${x.esc(item(x,k).name)} <b>${s}</b></span>`;}).join('');
  return `<article class="card fl-pinorder"><div class="fl-pin-head"><h4>📌 Hoa cài áo cho tiệc cưới</h4><b class="fl-pin-count${p.done>=p.goal?' ok':''}">${p.done}/${p.goal}</b></div>
    <div class="fl-progress" aria-hidden="true"><i style="width:${Math.min(100,p.done/p.goal*100)}%"></i></div>
    <p class="small">Mỗi cái: 1 hồng trắng, 1 nhánh baby, 1 đoạn ruy băng · ${p.pay} xu/cái, trả khi đủ. ${left?`Tiệc chờ thêm tối đa ${left} đơn giao nữa.`:'<b>Giao thêm đơn nào nữa là tiệc hủy!</b>'}</p>
    <p class="fl-needs">${parts}</p>${x.cmd('📌 Làm 1 hoa cài áo','fl_pin',{},can?'primary small':'ghost small',!can)}</article>`;
}
/* ---------- the cooler, pre-orders, the subscription, the regulars' book ---------- */
const care=x=>data(x).care||{};
const dayWord=(left,due)=>left<=0?'hôm nay':left===1?'ngày mai':`ngày ${due} (còn ${left} ngày)`;
const stageLine=s=>s?[s.bud?`${s.bud} nụ`:'',s.bloom?`${s.bloom} nở`:'',s.wilt?`${s.wilt} sắp héo`:''].filter(Boolean).join(' · '):'';
/** The daily water change: one reqList row and its button. */
function waterRow(x){
  const w=care(x).water||{};
  const row=w.done?{ok:true,icon:'💧',label:'Đã thay nước tủ mát hôm nay',note:'Đêm nay hoa trong tủ không già thêm (mỗi lô tối đa 2 đêm).'}
    :w.last<=today(x)-2?{ok:false,icon:'🫧',label:'Nước tủ mát đã đục',note:'Tối nay mọi lô hoa sẽ già nhanh thêm 1 ngày nếu chưa thay.',tone:'danger'}
    :{ok:null,icon:'💧',label:'Thay nước & cắt lại gốc hoa trong tủ',note:'Đêm nay hoa không già thêm. Bỏ 2 ngày liền thì hoa già nhanh.',tone:'warn'};
  return reqList([row],x.esc,'Tủ mát hôm nay')+(w.done?'':`<div class="fl-care-btns">${x.cmd('💧 Thay nước tủ mát','fl_water',{},'primary small',!x.room.open)}</div>`);
}
function buyWord(x,b,r,dueToday){
  if(dueToday)return (cc(x).buds||[]).includes(r.item)?'nhập ngay thì hoa còn nụ (−1★)':'nhập ngay trong Kho';
  if(!b)return 'không kịp cho ngày đó';
  const d=today(x),w=v=>v===d?'hôm nay':v===d+1?'mai':`ngày ${v}`;
  return b[0]===b[1]?`nên nhập ${w(b[0])}`:`nên nhập ${w(b[0])}–${w(b[1])}`;
}
/** One ingredient of a made-to-order piece: stock now and stems open on the day. */
function planRow(x,r,dueToday){
  if(!r.flower)return {ok:r.have>=r.need?true:dueToday?false:null,icon:r.emoji,label:`${r.need} ${r.unit} ${lower(r.name)}`,value:`có ${r.have}`,note:r.have<r.need?`thiếu ${r.need-r.have}, nhập thêm trong Kho`:''};
  const ok=r.ready>=r.need?true:(dueToday&&r.have<r.need)?false:null;
  const odd=r.have-r.ready;   // stems that will be buds or wilting on the day
  const note=r.ready>=r.need?'':r.have>=r.need?(dueToday?`${odd} cành còn nụ hoặc sắp héo: vẫn cắm được, khách chê 1★`:`${odd} cành sẽ còn nụ hoặc sắp héo vào hôm đó · ${buyWord(x,r.buy,r,false)}`)
    :`thiếu ${r.need-r.ready} cành · ${buyWord(x,r.buy,r,dueToday)}`;
  return {ok,icon:r.emoji,label:`${r.need} ${r.unit} ${lower(r.name)}`,value:`có ${r.ready}`,note,tone:ok===false?'danger':ok===null&&dueToday?'warn':''};
}
function preCard(x,b){
  const open=b.status==='offer'||b.status==='booked',when=open?dayWord(b.left,b.due):`ngày ${b.due}`;
  const who=x.npc(b.npc),head=`<div class="fl-pre-head"><span class="fl-pre-emoji" aria-hidden="true">${x.esc(b.emoji)}</span><div class="grow"><b>${x.esc(b.title)}</b><small>${x.esc(who.display_name||'')} · ${b.status==='offer'?'hẹn':'giao'} ${x.esc(when)} · ${x.money(b.price)} (cọc ${b.deposit})</small></div></div>`;
  if(b.status==='done')return `<li class="fl-pre done">${head}<p class="small">✓ Đã giao · ${'★'.repeat(b.stars||0)}</p></li>`;
  if(b.status==='failed')return `<li class="fl-pre failed">${head}<p class="small">✗ Không kịp làm, đã hoàn cọc.</p></li>`;
  const due=b.left<=0,rows=(b.rows||[]).map(r=>planRow(x,r,due)),okN=rows.filter(r=>r.ok===true).length;
  const table=reqList(rows,x.esc,'Hàng cần cho '+b.title);
  // Due today: the list is the job. Before that it is a planning aid, folded.
  const list=due?table:fold(`📦 Hàng cần · ${okN}/${rows.length} loại đủ cho ngày đó`,table);
  let btns='';
  if(b.status==='offer')btns=`${x.confirmCmd(`✓ Nhận, lấy cọc ${b.deposit} xu`,'fl_pre',{id:b.id,do:'accept'},`Nhận “${b.title}” giao ${dayWord(b.left,b.due)}? Nhận cọc ${b.deposit} xu; không kịp làm thì hoàn cọc và khách chê.`,'primary small')}${x.cmd('Từ chối khéo','fl_pre',{id:b.id,do:'decline'},'ghost small')}`;
  else if(due)btns=x.confirmCmd('💐 Cắm & giao đơn này','fl_pre',{id:b.id,do:'make'},`Cắm “${b.title}” từ hàng trong tủ? Tiệm dùng cành nở đẹp trước; khách đang chờ sẽ chờ thêm chút.`,'primary small',!!(b.short||[]).length||!x.room.open)
    +((b.short||[]).length?x.button('📦 Mở Kho nhập hoa','inventory',{},'ghost small'):'');
  const say=b.status==='offer'?`<p class="fl-note">“${x.esc(b.call)}”</p>`:'';
  const tip=due?((b.short||[]).length?`<p class="small fl-warn">Thiếu: ${x.esc(b.short.join(', '))}.</p>`:''):'<p class="small muted">Hoa nhập đúng ngày còn nụ chặt; nhập sớm quá thì tới ngày đã sắp héo. Thay nước tủ mát giúp hoa giữ lâu hơn.</p>';
  return `<li class="fl-pre${due?' due':''}">${head}${say}${list}${tip}${btns?`<div class="fl-care-btns">${btns}</div>`:''}</li>`;
}
function subCard(x){
  const s=care(x).sub||{};
  if(!s.status||s.status==='none')return '';
  const who=x.npc(s.npc),stars=(s.stars||[]).slice(-3);
  const notes=(s.notes||[]).length?`<ul class="fl-prefs">${s.notes.map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`:'';
  const head=`<div class="fl-pre-head"><span class="fl-pre-emoji" aria-hidden="true">🏺</span><div class="grow"><b>Gói hoa định kỳ · ${x.esc(who.display_name||'Bà Tám')}</b><small>Cứ ${s.every} ngày một bình nhỏ · ${x.money(s.price)}/lần${stars.length?` · gần đây ${stars.map(v=>v+'★').join(' ')}`:''}</small></div></div>`;
  if(s.status==='offer')return `<li class="fl-pre">${head}<p class="fl-note">“Con ơi, cứ ${s.every} ngày giao bà một bình hoa nhỏ để phòng khách nha. Bà già rồi, nhìn hoa tươi là vui.”</p>
    <div class="fl-care-btns">${x.confirmCmd('✓ Nhận gói hoa','fl_sub',{do:'accept'},`Nhận giao bà Tám ${s.every} ngày một bình, ${s.price} xu/lần? Quên giao hai lần liền bà sẽ ngừng.`,'primary small')}${x.cmd('Để khi khác','fl_sub',{do:'decline'},'ghost small')}</div></li>`;
  if(s.status==='off')return '';
  const card=`<p class="fl-prefs-head">📇 Thẻ của bà${notes?'':' · chưa ghi gì'}</p>${notes}`;
  if(!s.menu)return `<li class="fl-pre">${head}<p class="small">Bình tới: <b>${x.esc(dayWord(s.left,s.next))}</b>${s.misses?' · đã quên 1 lần, quên nữa là bà ngừng':''}</p>${fold('📇 Thẻ của bà Tám',card)}
    <div class="fl-care-btns">${x.confirmCmd('Ngừng gói hoa','fl_sub',{do:'stop'},'Ngừng giao hoa định kỳ cho bà Tám?','ghost small')}</div></li>`;
  const menu=s.menu.map(m=>{const rows=m.rows.filter(r=>r.flower);
    return `<div class="fl-tpl"><p class="fl-tpl-head"><b>${x.esc(m.name)}</b><small>${rows.map(r=>`${r.need} ${lower(r.name)}`).join(' · ')}</small></p>
      ${reqList(rows.map(r=>planRow(x,r,true)),x.esc,m.name)}${x.confirmCmd('🏺 Cắm bình này',`fl_sub`,{do:'make',pick:m.id},`Cắm bình “${m.name}” giao bà Tám? Nhìn lại thẻ của bà trước nhé.`,'small',!!m.short.length||!x.room.open)}</div>`;}).join('');
  return `<li class="fl-pre due">${head}<p class="small"><b>Hôm nay giao bình cho bà.</b> Chọn một trong ba mẫu; đọc thẻ của bà trước.</p>${card}<div class="fl-tpls">${menu}</div></li>`;
}
/** Everything that carries over from day to day. */
function careBoard(x){
  // Due today and new calls first, then the vase, then later bookings, then what is finished.
  const c=care(x),rank=b=>b.status==='offer'||(b.status==='booked'&&b.left<=0)?0:b.status==='booked'?2:3;
  const list=[...(c.pre||[])].sort((a,b)=>rank(a)-rank(b)||a.due-b.due);
  const now=list.filter(b=>rank(b)===0).map(b=>preCard(x,b)).join(''),later=list.filter(b=>rank(b)>0).map(b=>preCard(x,b)).join(''),sub=subCard(x);
  return `<section class="fl-care" aria-label="Chăm tiệm"><h4 class="section-title">🧊 Tủ mát hôm nay</h4>${waterRow(x)}
    ${now||later||sub?`<h4 class="section-title">📅 Đơn đặt trước & khách định kỳ</h4><ul class="fl-pres">${now}${sub}${later}</ul>`:''}</section>`;
}
/** How many things want attention today (for the folded board on the bench). */
function careDue(x){
  const c=care(x);
  return (c.water?.done?0:1)+(c.pre||[]).filter(b=>b.status==='offer'||(b.status==='booked'&&b.left<=0)).length+(c.sub?.menu||c.sub?.status==='offer'?1:0);
}
function bookFold(x){
  const book=(care(x).book||[]).filter(r=>r.visits);
  if(!book.length)return '';
  const rows=book.map(r=>{const who=x.npc(r.npc);
    return `<li><b>${x.esc(who.display_name||'')}</b> <small>${r.visits} lần ghé</small>${r.notes.length?`<ul class="fl-prefs">${r.notes.map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`:''}${r.more?`<small class="muted">Làm thêm ${r.more} đơn để biết thêm.</small>`:''}</li>`;}).join('');
  return `<section class="fl-bookcard">${fold(`📒 Sổ khách quen · ${book.length} người`,`<ul class="fl-regs">${rows}</ul>`)}</section>`;
}
/** On the bench: the same board, folded, with a count of what wants attention today. */
function careFold(x){
  const n=careDue(x);
  return `<section class="fl-carefold${n?' due':''}">${fold(`📋 Chăm tiệm hôm nay${n?` · ${n} việc chờ`:' · xong hết'}`,careBoard(x))}</section>`;
}
/** On the ticket: what the shop already knows about this customer. */
function regularCard(t,x){
  const r=(care(x).book||[]).find(b=>b.npc===t.npc);
  if(!r||!r.notes.length)return '';
  return fold(`⭐ Khách quen · ${r.visits} lần ghé · ${r.notes.length} ghi chú`,`<ul class="fl-prefs">${r.notes.map(n=>`<li>${x.esc(n)}</li>`).join('')}</ul>`);
}
/** Between orders: what is in the cooler, oldest first, and how open it is. */
function coolerStrip(x){
  const d=data(x),cooler=d.cooler||{};
  const fl=(cc(x).flowers||[]).filter(f=>f.unlock<=lvl(x)||stock(x,f.id));
  if(!fl.length)return '';
  const old=fl.filter(f=>(cooler[f.id]?.next??9)<=0&&stock(x,f.id)).length;
  return `<section class="fl-shelf" aria-label="Tủ mát"><p class="fl-shelf-head"><b>🧊 Trong tủ mát</b><small>${old?`${old} loại có cành sắp héo — dùng trước hoặc bỏ trong Kho`:'Cành cũ nhất được lấy ra trước'}</small></p>
    <div class="fl-shelf-row">${fl.map(f=>{const q=stock(x,f.id)+(cooler[f.id]?.spare||0),left=q?cooler[f.id]?.next:null,st=stageLine(cooler[f.id]?.stages);
      return `<span class="fl-shelf-item${q?'':' is-empty'}${left!=null&&left<=0?' old':''}" title="${x.esc(f.name)}: ${q} ${x.esc(item(x,f.id).unit||'cành')} · ${freshLabel(left)}"><span class="count-badge${q?'':' is-empty'}" data-count="${q}">${q}</span>${glyph(x,f.id,'fl-shelf-emoji')}<small>${x.esc(f.name)}</small>${st?`<small class="fl-stage-txt">${x.esc(st)}</small>`:''}</span>`;}).join('')}</div></section>`;
}
const extras=x=>banners(x)+pinsCard(x);

/* ---------- the order ---------- */
/** Sets: one row per piece. Tap a waiting piece to switch, a finished one to take it back. */
function pieceTabs(t,x){
  const busy=started(t.work)&&!plated(t);
  return `<div class="fl-party" role="tablist" aria-label="Các món trong bộ">${t.needs.party.map((p,i)=>{
    const f=format(x,p.format),done=!!t.pieces[i],on=i===t.cur&&!done,off=on||(busy&&!on);
    return `<button type="button" role="tab" class="fl-pieceline${on?' on is-selected':''}${done?' done':''}" data-command="fl_tab" data-payload="${pay(x,{task:t.id,index:i})}" aria-selected="${on}"${off?' disabled':''}>
      <span class="fl-pieceno" aria-hidden="true">${done?'✓':i+1}</span><span class="fl-piecetext"><small>Món ${i+1} · ${done?'đã xong, bấm để mang lại bàn sửa':on?'đang làm':busy?'chờ món đang làm xong':'bấm để làm món này'}</small><b>${x.esc(p.label)}</b><span>${x.esc(f.emoji)} ${x.esc(f.name)} · ${p.stems[0]}–${p.stems[1]} cành</span></span></button>`;
  }).join('')}</div>`;
}
/** What the customer has told so far, and what is still worth asking. */
function consult(t,x){
  const clues=Object.entries(t.needs.clues||{});
  const heard=clues.length?`<ul class="fl-heard">${clues.map(([k,v])=>`<li><span aria-hidden="true">${x.esc(topic(x,k).emoji)}</span>“${x.esc(v)}”</li>`).join('')}</ul>`:'';
  const left=unasked(t);
  if(!left.length)return heard;
  const rush=t.guest?.kind==='rush',cost=rush?(cc(x).ask_cost_rush||7):(cc(x).ask_cost||5);
  return `${heard}<div class="fl-ask"><p class="fl-ask-head"><b>💬 Khách chưa nói hết</b><small>Mỗi câu hỏi tốn chút kiên nhẫn (−${cost}%), nhưng đoán sai thì người nhận có thể trả hoa.</small></p>
    <div class="fl-ask-btns">${left.map(k=>{const tp=topic(x,k);return `<button type="button" class="btn ghost fl-ask-btn" data-command="fl_ask" data-payload="${pay(x,{task:t.id,topic:k})}"><span aria-hidden="true">${x.esc(tp.emoji)}</span> ${x.esc(tp.label)}</button>`;}).join('')}</div></div>`;
}
function ticket(t,x){
  const who=x.npc(t.npc),n=t.needs,g=t.guest||{},o=occasion(x,n.occasion);
  const tags=[`<span class="tag">${x.esc(g.emoji||'🙂')} ${x.esc(g.label||'Khách')}</span>`,`<span class="tag">${x.esc(o.emoji)} ${x.esc(o.name)}</span>`];
  if(isSet(t))tags.push(`<span class="tag">🎁 Bộ ${n.party.length} món</span>`);
  if(!deliver(t))tags.push('<span class="tag">🏪 Nhận tại tiệm</span>');
  // The price is said once, here; the list below is what has to be right.
  const price=t.quoted_price!=null?`<b class="price" aria-label="Giá đơn">${x.money(t.quoted_price)}</b>`:'';
  const cap=isSet(t)&&!plated(t)?`Món ${t.cur+1}: ${spec(t).label}`:'Khách dặn';
  const list=`<p class="fl-brief-cap">${x.esc(cap)}</p>${reqList(briefRows(t,x),x.esc,cap)}`;
  return `<article class="card ticket fl-ticket"><div class="fl-ticket-head">${x.portrait(who,44)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3>${price}</div>
    <p class="fl-tags">${tags.join(' ')}</p></div></div>
    <p class="fl-note">“${x.esc(n.note)}”</p>${consult(t,x)}${isSet(t)?pieceTabs(t,x):''}${list}${regularCard(t,x)}${patience(t.patience)}</article>`;
}

/* ---------- station panels ---------- */
function coolerPanel(t,x){
  const sp=spec(t),w=t.work,d=data(x),level=lvl(x),c=counts(w.stems);
  const busy=w.arranged||soaking(t)||w.stems.length>=(cc(x).max_stems||30);
  const tiles=(cc(x).flowers||[]).map(f=>{
    const info=d.cooler?.[f.id]||{},have=stock(x,f.id)+(info.spare||0),wanted=sp.focal?.item===f.id;
    const locked=f.unlock>level&&!wanted,left=have?info.next:null,on=c[f.id]||0;
    // Only for a home with cats, and in words.
    const flag=t.needs.cats!==true?'':f.cats==='toxic'?'🐈 độc với mèo':f.cats==='caution'?'🐈 mèo nên tránh':'';
    const sub=locked?`cấp ${f.unlock}`:[on?`×${on} trên bàn`:'',freshLabel(left)].filter(Boolean).join(' · ');
    return tile(x,{glyph:glyph(x,f.id),name:f.name,sub,count:have,empty:!have,cmd:'fl_pick',payload:{task:t.id,item:f.id},selected:on>0,
      locked,disabled:busy||!have,wanted:wanted&&(c[f.id]||0)<sp.focal.count,flag,flagCls:f.cats||'',cls:`fl-flower c-${f.color} ${left!=null&&left<=0?'old':''}`,
      label:locked?`${f.name}, mở ở cấp ${f.unlock}`:`${f.name}: tủ còn ${have}, ${freshLabel(left)}${on?`, ${on} cành trên bàn`:''}`});
  }).join('');
  const bench=Object.entries(c).map(([id,q])=>{const f=flower(x,id),old=w.stems.filter(s=>s.i===id&&s.e-today(x)<=0).length;
    return `<li>${glyph(x,id)}<b>${x.esc(f.name)}</b> ×${q}${old?` <small class="fl-warn">${old} sắp héo</small>`:''}${x.cmd('−','fl_remove',{task:t.id,item:id},'ghost small fl-minus',w.arranged||soaking(t))}</li>`;}).join('');
  const book=(cc(x).flowers||[]).map(f=>{const taboo=f.taboo.length>=6?'chỉ dùng cho viếng':f.taboo.map(o=>occasion(x,o).name).join(', ');
    return `<li><b>${glyph(x,f.id)} ${x.esc(f.name)}</b> — ${x.esc(f.meaning)}${f.good.length<8?`<small>Hợp: ${x.esc(f.good.map(o=>occasion(x,o).name).join(', '))}</small>`:''}${taboo?`<small class="fl-warn">Kiêng: ${x.esc(taboo)}</small>`:''}${f.cats==='toxic'?'<small class="fl-warn">Rất độc với mèo (cả phấn, lá, nước bình)</small>':f.cats==='caution'?'<small>Mèo gặm dễ đau bụng</small>':''}</li>`;}).join('');
  const water=care(x).water?.done?'':`<div class="fl-water-line">${waterRow(x)}</div>`;
  return `${water}<h4 class="section-title">Tủ mát · cành cũ nhất ra trước</h4><div class="tile-grid fl-grid">${tiles}</div>
    <h4 class="section-title">Trên bàn (${w.stems.length} cành)</h4>${bench?`<ul class="fl-bench">${bench}</ul>`:'<p class="muted small">Chưa lấy cành nào. Cành chưa cắt gốc có thể cắm lại vào xô chờ.</p>'}
    <details class="fl-book"><summary>📖 Sổ tay ý nghĩa hoa</summary><ul>${book}</ul></details>`;
}
function prepPanel(t,x){
  const w=t.work,f=format(x,spec(t).format),d=data(x),min=soakMin(t,x);
  const uncut=w.stems.filter(s=>!s.c).length,bare=w.stems.filter(s=>!s.s).length,locked=w.arranged||soaking(t);
  const others=(d.buckets||[]).filter(b=>b.task!==t.id);
  const full=(d.buckets||[]).length>=(cc(x).buckets||2)&&!soaking(t);
  return `<h4 class="section-title">1 · Cắt gốc dưới vòi nước</h4>
    <div class="row wrap">${x.cmd(`✂️ Cắt xéo 45° (${uncut})`,'fl_cut',{task:t.id,angle:'angled'},uncut&&!locked?'primary':'',!uncut||locked)}${x.cmd('Cắt thẳng cho nhanh','fl_cut',{task:t.id,angle:'straight'},'ghost small',!uncut||locked)}</div>
    <p class="muted small">Gốc xéo không bị bịt đáy xô và có mặt cắt rộng hơn để hút nước.</p>
    <h4 class="section-title">2 · Tuốt lá, gai phần gốc</h4>
    ${x.cmd(`🍃 Tuốt lá dưới mực nước (${bare})`,'fl_strip',{task:t.id},'',!bare||locked)}
    <h4 class="section-title">3 · Ngâm xô nước mát</h4>
    <div class="fl-pails">${soakMeter(x,w.soak,min)}${others.map(()=>`<div class="fl-other small">🪣 Xô bên cạnh đang ngâm hoa của đơn khác</div>`).join('')}</div>
    <div class="row wrap">${x.cmd('🪣 Thả vào xô','fl_soak',{task:t.id},'',!w.stems.length||!!uncut||w.arranged||soaking(t)||full)}${x.cmd('🙌 Nhấc ra','fl_lift',{task:t.id},soaking(t)?'primary':'',!soaking(t))}</div>
    ${full?'<p class="notice small">Cả hai xô đang bận. Nhấc hoa của đơn khác ra trước.</p>':''}
    <p class="muted small">${f.soak?`Bó/bình cần ngâm ít nhất ${min} giây thật cho cành căng nước.`:'Cắm mút: mút giữ nước, ngâm xô là tùy chọn — nhưng vẫn cắt xéo và tuốt lá.'}</p>`;
}
function designPanel(t,x){
  const sp=spec(t),w=t.work,level=lvl(x),min=t.foam_min||cc(x).foam_min||10;
  const bases=(cc(x).formats||[]).map(f=>{
    const locked=f.unlock>level&&sp.format!==f.id,uses=Object.entries(f.uses||{}),short=uses.filter(([k,q])=>stock(x,k)<q);
    const main=uses[0]?stock(x,uses[0][0]):null;
    const sub=locked?`cấp ${f.unlock}`:uses.length?uses.map(([k,q])=>`${item(x,k).name} ${stock(x,k)}`).join(' · '):'dây buộc, giấy gói';
    return tile(x,{emoji:f.emoji,name:f.name,sub,count:main,empty:short.length>0,cmd:'fl_base',payload:{task:t.id,kind:f.id},selected:w.base===f.id,locked,disabled:!!w.base||short.length>0,
      label:locked?`${f.name}, mở ở cấp ${f.unlock}`:`${f.name}${short.length?', thiếu vật tư':''}`});
  }).join('');
  const foam=w.foam?`${foamMeter(x,w.foam,min)}${w.arranged?'':x.confirmCmd('👇 Ấn mút chìm cho nhanh','fl_push',{task:t.id},'Ấn mút xuống sẽ nhốt không khí, lõi mút khô. Vẫn làm?','ghost small',w.foam.pushed)}`:'';
  const verb={bouquet:'🌀 Bó xoắn ốc & buộc dây',vase:'🏺 Cắm vào bình',basket:'🧺 Cắm vào giỏ',wreath:'🕊️ Cắm kín mặt kệ'}[w.base]||'Cắm hoa';
  const foamWait=w.foam&&!w.foam.pushed&&x.now()-w.foam.start<min;
  const canArrange=w.base&&!w.arranged&&w.stems.length>=3&&!soaking(t)&&!w.stems.some(s=>!s.c)&&!foamWait;
  const arrange=`<div class="row wrap">${x.cmd(verb,'fl_arrange',{task:t.id},canArrange?'primary':'',!canArrange)}${x.cmd('↩️ Tháo ra','fl_untie',{task:t.id},'ghost small',!w.arranged||!!w.paper||!!w.ribbon||!!w.banner)}</div>`;
  let step=3;
  const papers=w.base==='bouquet'?`<h4 class="section-title">${step++} · Giấy gói</h4><div class="fl-swatches">${(cc(x).papers||[]).map(p=>swatch(x,{cmd:'fl_wrap',payload:{task:t.id,paper:p.id},hex:p.hex,name:p.name,count:stock(x,p.item),selected:w.paper===p.id,disabled:!w.arranged||!!w.paper||!stock(x,p.item)})).join('')}</div>`:'';
  const ribbons=`<h4 class="section-title">${step++} · Ruy băng <span class="fl-swatch-n${stock(x,'ribbon')?'':' zero'}">${stock(x,'ribbon')}</span></h4><div class="fl-swatches">${(cc(x).ribbons||[]).map(r=>swatch(x,{cmd:'fl_ribbon',payload:{task:t.id,color:r.id},hex:r.hex,name:r.name,selected:w.ribbon===r.id,disabled:!w.arranged||!!w.ribbon||(w.base==='bouquet'&&!w.paper)||!stock(x,'ribbon')})).join('')}</div>
    ${x.cmd('✂️ Gỡ giấy & ruy băng','fl_unwrap',{task:t.id},'ghost small',!w.paper&&!w.ribbon)}`;
  const banner=w.base==='wreath'?`<h4 class="section-title">${step++} · Băng rôn chữ <span class="fl-swatch-n${stock(x,'banner')?'':' zero'}">${stock(x,'banner')}</span></h4>${w.banner?`<p class="fl-printed">🎗️ “${x.esc(w.banner)}”</p>`:''}
    <div class="fl-write"><label class="field grow">Nội dung in<input id="fl-banner-text" class="input" maxlength="60" autocomplete="off" spellcheck="false" value="${x.esc(x.ui.bannerText||'')}" placeholder="Gõ đúng từng chữ, có dấu"></label>${x.button(w.banner?'🖨️ In lại':'🖨️ In & treo','car:banner',{task:t.id},'primary')}</div>`:'';
  const cover=rainy(x)&&deliver(t)?`<h4 class="section-title">${step++} · Chống mưa</h4><div class="row wrap">${x.cmd(w.cover?'✓ Đã bọc nylon':'🌂 Bọc nylon chống mưa','fl_cover',{task:t.id},w.cover?'ghost small':'',!!w.cover||!w.arranged||(w.base==='bouquet'&&!w.paper))}</div><p class="muted small">Trời mưa: hoa giao tận nơi không bọc sẽ ướt, giấy gói nhũn.</p>`:'';
  return `<h4 class="section-title">1 · Kiểu cắm</h4><div class="tile-grid fl-grid">${bases}</div>${foam}
    <h4 class="section-title">2 · Cắm / bó</h4>${arrange}${papers}${ribbons}${banner}${cover}`;
}
function cardPanel(t,x){
  const n=t.needs,sp=spec(t),w=t.work,tone=t.card_tone;
  const toneLine=w.card?`<p class="fl-tone ${tone||''}">${{fit:'✓ Lời thiệp hợp dịp.',plain:'○ Lời hơi chung chung — thêm một câu đúng dịp sẽ ấm hơn.',wrong:'✗ Lời thiệp không hợp dịp này!'}[tone]||''}</p>`:'';
  const card=`<h4 class="section-title">Thiệp viết tay <span class="fl-swatch-n${stock(x,'card')?'':' zero'}">${stock(x,'card')}</span></h4>${sp.card?'':'<p class="muted small">Món này khách không yêu cầu thiệp — có thể bỏ qua.</p>'}
    <div class="fl-write"><label class="field grow">Lời nhắn<textarea id="fl-card-text" class="input" rows="3" maxlength="160" spellcheck="false" placeholder="Viết đúng dịp: ${x.esc(lower(occasion(x,n.occasion).name))}…">${x.esc(x.ui.cardText??w.card??'')}</textarea></label>
    ${x.button(w.card?'✍️ Viết lại thiệp mới':'✍️ Viết thiệp','car:card',{task:t.id},'primary')}</div>${toneLine}`;
  let slots='<p class="muted small">Khách nhận hoa tại tiệm.</p>';
  if(deliver(t)){
    slots=`<h4 class="section-title">Khung giờ giao</h4>${n.delivery?'':'<p class="notice amber small">🕒 Chưa hỏi khách giờ giao. Hỏi ở phiếu đơn cho chắc, hoặc chọn theo phỏng đoán.</p>'}
      <div class="fl-segs" role="group" aria-label="Khung giờ giao">${(cc(x).slots||[]).map(s=>seg(x,'slot','slot',s.id,s.name,x.ui.slot)).join('')}</div>
      <p class="muted small">Phí giao ${cc(x).delivery_fee||15} xu đã tính vào đơn. Gọi xác nhận địa chỉ trước khi xuất phát.</p>`;
  }
  return card+slots;
}

/* ---------- next step & the one primary action ---------- */
function pieceReady(t){
  const sp=spec(t),w=t.work;
  if(!w.base||!w.arranged||soaking(t))return false;
  if(w.base==='bouquet'&&(!w.paper||!w.ribbon))return false;
  if(w.base==='wreath'&&!w.banner)return false;
  if(sp.card&&!w.card)return false;
  return true;
}
function nextStep(t,x){
  if(!t.known)return 'Hỏi dịp tặng & ngân sách';
  if(plated(t))return `Đủ ${t.pieces.length} món, giao cả bộ!`;
  const sp=spec(t),w=t.work,f=format(x,sp.format),tag=isSet(t)?`Món ${t.cur+1}: `:'';
  const ask=unasked(t);
  if(ask.length&&!w.stems.length)return 'Hỏi thêm khách: '+lower(topic(x,ask[0]).label);
  if(soaking(t))return tag+'chờ hoa hút nước rồi nhấc ra';
  if(!w.stems.length)return tag+'chọn hoa trong tủ mát';
  if(w.stems.some(s=>!s.c))return tag+'cắt xéo gốc';
  if(w.stems.some(s=>!s.s))return tag+'tuốt lá dưới mực nước';
  if(f.soak&&w.stems.some(s=>!s.h))return tag+'ngâm hoa vào xô';
  if(!w.base)return tag+'chuẩn bị '+lower(f.name);
  if(w.foam&&!w.foam.pushed&&!w.arranged&&x.now()-w.foam.start<(t.foam_min||10))return tag+'chờ mút tự chìm';
  if(!w.arranged)return tag+'cắm / bó hoa';
  if(w.base==='bouquet'&&!w.paper)return tag+'gói giấy';
  if(!w.ribbon)return tag+'thắt ruy băng';
  if(w.base==='wreath'&&!w.banner)return tag+'in băng rôn';
  if(sp.card&&!w.card)return tag+'viết thiệp';
  const next=pendingOthers(t);
  if(next.length)return `Món ${t.cur+1} xong! Đặt sang bàn chờ rồi làm món ${next[0]+1}`;
  if(deliver(t)&&rainy(x)&&!w.cover)return 'Bọc nylon chống mưa';
  if(deliver(t)&&!x.ui.slot)return 'Chọn khung giờ giao';
  return deliver(t)?'Giao hoa!':'Trao hoa cho khách!';
}
function primary(t,x,rs,big){
  const cls='primary'+(big?' big':''),n=t.needs;
  if(isSet(t)&&!plated(t)&&pendingOthers(t).length)return x.cmd(`✅ Xong món ${t.cur+1}`,'fl_done',{task:t.id},cls,!pieceReady(t));
  const blocked=!!data(x).day?.open_event;
  const payload={task:t.id,confirm:true};
  if(deliver(t)&&x.ui.slot)payload.slot=x.ui.slot;
  const can=(plated(t)||pieceReady(t))&&(!deliver(t)||!!x.ui.slot);
  const label=deliver(t)?(big?'🛵 Giao hoa':'🛵 Giao'):(big?'💐 Trao hoa cho khách':'💐 Trao');
  const allOk=rs.every(r=>r[0]===true);
  const q=deliver(t)?`Giao lúc ${slotName(x,x.ui.slot||n.delivery||'')}? Người nhận sẽ xem kỹ hoa, thiệp và màu sắc.`:'Trao hoa? Khách sẽ xem kỹ hoa, thiệp và màu sắc.';
  return allOk&&!blocked?x.cmd(label,'fl_deliver',payload,cls,!can)
    :x.confirmCmd(label,'fl_deliver',payload,blocked?'Có chuyện bất ngờ đang chờ bạn quyết. Xử lý xong rồi hãy giao nhé.':'Chưa khớp hết phiếu. Vẫn giao? '+q,cls,!can);
}

export default {
  id:'florist',
  css:true,
  next(t,x){return nextStep(t,x);},
  idle(x){
    const d=data(x);
    return idlePanel(x,d.day,'fl_event',extras(x)+careBoard(x)+coolerStrip(x)+bookFold(x),null,'fl');
  },
  job(t,x){
    const d=data(x),day=d.day;
    const head=`${dayStrip(x,day,true)}${flash(x,day)}${eventCard(x,day,'fl_event')}${queue(x,t)}`;
    if(!t.known){
      const who=x.npc(t.npc),g=t.guest||{};
      return `<div class="career-job fl food">${head}<article class="card ticket fl-ticket"><div class="fl-ticket-head">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3>
        <p class="fl-tags"><span class="tag">${x.esc(g.emoji||'🙂')} ${x.esc(g.label||'Khách')}</span></p></div></div>
        <p class="fl-say">“${x.esc(t.opening)}”</p>${regularCard(t,x)}${patience(t.patience)}${x.cmd('📝 Nghe yêu cầu','ask',{task:t.id},'primary full')}</article>${extras(x)}${careFold(x)}</div>`;
    }
    const w=t.work,ui=x.ui;
    if(ui.tabFor!==t.id){ui.tabFor=t.id;ui.tab=w.arranged?'design':'cooler';ui.cardText=null;ui.bannerText='';ui.slot=null;ui.pieceFor=t.cur;}
    if(ui.pieceFor!==t.cur){ui.pieceFor=t.cur;ui.cardText=null;ui.bannerText='';ui.tab=w.arranged?'design':'cooler';}
    const tabs=[['cooler','🧊','Tủ hoa'],['prep','✂️','Sơ chế'],['design','💐','Cắm & gói'],['card','💌',deliver(t)?'Thiệp & giao':'Thiệp']];
    const onBench=w.stems.length;
    const badge=k=>k==='prep'&&soaking(t)?'<em class="fl-badge">⏱</em>':k==='cooler'&&onBench?`<em class="fl-badge calm">${onBench}</em>`:'';
    const tabBar=`<div class="fl-tabs" role="tablist" aria-label="Khu làm việc">${tabs.map(([k,e,l])=>`<button type="button" role="tab" class="fl-tab ${ui.tab===k?'on':''}" data-action="car:tab" data-tab="${k}" aria-selected="${ui.tab===k}">${e} ${l}${badge(k)}</button>`).join('')}</div>`;
    const panel=plated(t)?`<p class="notice">🎁 Đủ ${t.pieces.length} món trên bàn chờ. Giao cả bộ, hoặc bấm một món ở phiếu đơn để mang lại bàn sửa.</p>`
      :({cooler:coolerPanel,prep:prepPanel,design:designPanel,card:cardPanel}[ui.tab]?.(t,x)||'');
    const rs=rows(t,x),steps=stepRows(t,x),ok=steps.filter(r=>r[0]===true).length;
    const dump=x.confirmCmd('🗑️ Bỏ bó, làm lại','fl_dump',{task:t.id},'Bỏ toàn bộ hoa và vật liệu đang dùng? Giá trị ghi hao hụt.','danger small',plated(t)||(!w.stems.length&&!w.base)||soaking(t));
    const side=`<div class="fl-side"><div class="fl-look">${stage(t,x)}<div class="fl-look-txt"><p class="fl-status" aria-live="polite">${x.esc(status(t,x))}</p>${pieceChips(t)}</div></div>
      ${plated(t)?'':cardPreview(t,x)+valueMeter(t,x)}
      ${steps.length?`<div class="fk-wide-only"><p class="fl-brief-cap">Các bước làm</p>${checklist(x,steps,'Các bước làm')}</div>`:''}<div class="fk-wide-only">${primary(t,x,rs,true)}${dump}</div>
      ${steps.length?`<details class="fl-check fl-narrow-only"${ui.flCheck?' open':''}><summary data-action="car:check">📋 Các bước làm · ${ok}/${steps.length} xong</summary>${checklist(x,steps,'Các bước làm')}</details>`:''}</div>`;
    const tools=`<p class="row wrap fl-tools"><span class="fl-narrow-only">${dump}</span> ${x.button('📦 Kho & nhập hoa','inventory',{},'ghost small')}</p>`;
    const barEl=actionBar(x.esc(nextStep(t,x)),primary(t,x,rs,false));
    return `<div class="career-job fl food">${head}${extras(x)}${careFold(x)}${ticket(t,x)}${tabBar}<div class="workbench"><section class="wb-main" role="tabpanel">${panel}${tools}</section><aside class="wb-side">${side}</aside></div>${barEl}</div>`;
  },
  actions:{
    async tab(data,el,x){x.ui.tab=data.tab;x.render();},
    async slot(data,el,x){x.ui.slot=data.slot;x.render();},
    async check(data,el,x){x.ui.flCheck=!x.ui.flCheck;},
    async card(data,el,x){
      const input=el?.closest('.career-job')?.querySelector('#fl-card-text');
      const text=(input?.value||'').trim();
      x.ui.cardText=text;
      if(text.length<3){x.toast('Viết vài chữ lên thiệp trước nhé.');return;}
      await x.send('fl_card',{task:data.task,text});
      x.ui.cardText=null;
    },
    async banner(data,el,x){
      const input=el?.closest('.career-job')?.querySelector('#fl-banner-text');
      const text=(input?.value||'').trim();
      x.ui.bannerText=text;
      if(text.length<2){x.toast('Gõ nội dung băng rôn trước nhé.');return;}
      await x.send('fl_banner',{task:data.task,text});
    },
  },
  tick(root,x){
    keepBarAboveFooter(root);
    const p=v=>Math.min(100,v/METER_SCALE*100);
    root.querySelectorAll('[data-soak-start]').forEach(el=>{
      const start=Number(el.dataset.soakStart);if(!start)return;
      const min=Number(el.dataset.min||8),sec=Math.max(0,x.now()-start);
      el.querySelector('.fl-fill').style.width=p(sec)+'%';
      el.querySelector('.fl-meter-label').textContent=`${sec.toFixed(1)} giây · ${sec<min?'đang hút nước…':'ĐỦ NƯỚC — nhấc ra'}`;
      el.classList.toggle('ready',sec>=min);
    });
    root.querySelectorAll('[data-foam-start]').forEach(el=>{
      const start=Number(el.dataset.foamStart);if(!start)return;
      const min=Number(el.dataset.min||10),sec=Math.max(0,x.now()-start);
      el.querySelector('.fl-fill').style.width=p(sec)+'%';
      el.querySelector('.fl-meter-label').textContent=sec<min?`${sec.toFixed(1)} giây · mút đang tự chìm…`:'MÚT ĐÃ NGẤM ĐỀU';
      el.classList.toggle('ready',sec>=min);
    });
    // Live preview of what is being typed; the draft survives re-renders.
    const card=root.querySelector('#fl-card-text'),live=root.querySelector('[data-card-live]');
    if(card){if(card.value!==(x.ui.cardText??card.defaultValue))x.ui.cardText=card.value;
      if(live&&card.value.trim()&&live.textContent!==card.value)live.textContent=card.value;}
    const banner=root.querySelector('#fl-banner-text'),blive=root.querySelector('[data-banner-live]');
    if(banner){if(banner.value!==(x.ui.bannerText||''))x.ui.bannerText=banner.value;
      if(blive&&banner.value.trim()&&blive.textContent!==banner.value)blive.textContent=banner.value;}
  },
  summary(data,x){
    const care=(data?.care||[]).map(l=>`<li>${x.esc(l)}</li>`).join('');
    return gradeCard(data,x)+(care?`<article class="card space-top fl-night"><h4>🌙 Qua đêm ở tiệm</h4><ul>${care}</ul></article>`:'');
  },
  dock:[['inventory','box','Kho','Nhập & đếm hoa']],
};
