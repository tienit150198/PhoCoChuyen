/** Tiệm Hoa Nắng — florist workbench. The day strip, the customer queue, the
 * order (what the customer said, what is still worth asking, the pieces of a
 * set), station tabs whose tiles carry stock badges and padlocks, live soak /
 * foam bars with a green zone, and one big "Giao". Only renders server state
 * and sends commands; the server checks every rule and keeps what the customer
 * has not said yet out of the public view.
 *
 * Next-step guide (guide.js): every order is a list of steps (ask → pick → cut →
 * strip → soak → base → card → arrange → wrap → ribbon → slot), each with the tap
 * that does it. The header hint and the one bottom button always do the next
 * one; on the first order the right flowers glow (and the button picks them). */
import {dayStrip,flash,eventCard,queue,keepBarAboveFooter,idlePanel,shopSummary,patience,openTasks} from './food_kit.js';
import {splitMai} from './tomorrow_kit.js';
import {reqList,fold} from '../ui-kit.js';
import {nextHint,stepCta,finalGo,pending,firstTime,todoAttrs,todoArrow,highlight,stepLine} from '../v4/guide.js';
import {restockFor,restockButton} from '../v4/restock.js';
import {lockChip} from './stage_fold.js';
import {reqPin,nextLine,stepper,pinTop,asmActions,finalStep} from './asm_kit.js';

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
/** 0 left of a supply (card, banner): why its buttons are off, and the restock tap next to it (fl_card / fl_banner refuse at 0). */
const outOf=(x,id,what,task,need=4)=>stock(x,id)?'':`<p class="fl-out small"><span class="bad">Hết ${x.esc(what)}: nhập thêm mới ${id==='card'?'viết':'in'} được.</span> ${restockButton(x.room,[{id,need}],{task},'small ghost')}</p>`;
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
  const attrs=(o.cmd?`data-command="${o.cmd}" data-payload="${pay(x,o.payload||{})}"`
    :o.action?`data-action="car:${o.action}"${Object.entries(o.data||{}).map(([k,v])=>` data-${k}="${x.esc(v)}"`).join('')}`:'')+(o.item?` data-fl-item="${x.esc(o.item)}"`:'');
  const cls=['tile',o.cls||'',o.selected?'is-selected':'',o.locked?'is-locked':'',o.empty?'is-empty':'',o.wanted?'wanted':''].filter(Boolean).join(' ');
  const badge=o.count!=null&&!o.locked?`<span class="count-badge${o.empty?' is-empty':''}" data-count="${x.esc(String(o.count))}">${x.esc(String(o.count))}</span>`:'';
  return `<button type="button" class="${cls}" ${attrs}${o.disabled||o.locked?' disabled':''} aria-pressed="${o.selected?'true':'false'}"${o.label?` aria-label="${x.esc(o.label)}"`:''}>${badge}<span class="tile-emoji" aria-hidden="true">${o.glyph||x.esc(o.emoji||'')}</span><b>${x.esc(o.name)}</b>${o.sub?`<small>${x.esc(o.sub)}</small>`:''}${o.flag?`<small class="fl-flag ${o.flagCls||''}">${x.esc(o.flag)}</small>`:''}</button>`;
}
const swatch=(x,o)=>`<button type="button" class="fl-swatch ${o.selected?'on is-selected':''}" data-command="${o.cmd}" data-payload="${pay(x,o.payload)}"${o.disabled?' disabled':''} aria-pressed="${o.selected?'true':'false'}"><i style="background:${x.esc(o.hex)}"></i>${x.esc(o.name)}${o.count!=null?`<span class="fl-swatch-n${o.count?'':' zero'}">${x.esc(String(o.count))}</span>`:''}</button>`;
const seg=(x,action,key,value,label,current)=>`<button type="button" class="fl-seg ${current===value?'on is-selected':''}" data-action="car:${action}" data-${key}="${x.esc(value)}" aria-pressed="${current===value}">${x.esc(label)}</button>`;
/** ui-kit reqList markup, except that a row which is not done and has a way to do it
 * (its own guide step, or `r.step`) is a button: tap it to do that step. */
const MARK={true:['ok','✓','đúng'],false:['bad','✗','sai'],null:['','○','chưa làm']};
function reqRows(x,rows,label){
  return `<ul class="req-list" aria-label="${x.esc(label)}">${rows.map(r=>{
    const [cls,mark,said]=MARK[r.ok===true?'true':r.ok===false?'false':'null'];
    const s=r.ok===true?null:(r.step||r),tap=s&&s.ok!==true?todoAttrs(s):'';
    return `<li class="req-row ${cls}${r.tone?' tone-'+x.esc(r.tone):''}${tap?' gd-todo':''}"${tap}><span class="req-mark" aria-label="${said}">${mark}</span>${r.icon?`<span class="req-icon" aria-hidden="true">${x.esc(r.icon)}</span>`:''}<span class="req-label">${x.esc(r.label)}${r.note?`<small>${x.esc(r.note)}</small>`:''}</span>${r.value?`<b class="req-value">${x.esc(r.value)}</b>`:''}${tap?todoArrow(s):''}</li>`;
  }).join('')}</ul>`;
}
/** The bench steps as the florist's own requirement rows (tappable when open). */
const checklist=(x,steps,label)=>reqRows(x,steps.filter(Boolean),label);
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
  const note=v>b?' · tiệm bù phần dư':'';
  return meter('value','',[['thin',0,p(.5)],['low',p(.5),p(.7)],['ok',p(.7),p(.85)],['full',p(.85),p(1)],['over',p(1),100]],p(v/b),`💰 ${v}/${b} xu hoa (${Math.round(v/b*100)}%)${note}`);
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

/* ---------- the brief (ticket), live ✓/✗/○; each open row does its step (K = steps by key) ---------- */
/** What the customer asked for, checked against what is on the bench (reqList rows). */
function briefRows(t,x,K={}){
  const n=t.needs,sp=spec(t),w=t.work,st=plated(t)?[]:w.stems,c=counts(st),total=st.length,any=total?true:null,f=format(x,sp.format),out=[];
  if(plated(t))return [{ok:true,icon:'🎁',label:`Đủ ${t.pieces.length} món, giao cả bộ một lượt`}];
  out.push({ok:w.base?w.base===sp.format:null,icon:f.emoji,label:f.name,short:f.name,note:w.base&&w.base!==sp.format?`đang làm ${lower(format(x,w.base).name)}`:'',step:K.base});
  // Still picking: too few is "not yet" (○), too many or finished short is wrong (✗).
  const upTo=(have,lo,hi)=>!have?null:have>hi?false:have>=lo?true:w.arranged?false:null;
  out.push({ok:upTo(total,sp.stems[0],sp.stems[1]),icon:'🌿',label:`${sp.stems[0]}–${sp.stems[1]} cành`,short:`${total}/${sp.stems[0]}–${sp.stems[1]} cành`,value:total?`${total} cành`:'',step:K.pick});
  if(sp.focal){const have=c[sp.focal.item]||0;out.push({ok:upTo(have,sp.focal.count,sp.focal.count),icon:look(x,sp.focal.item).emoji,label:`Đúng ${sp.focal.count} cành ${lower(flower(x,sp.focal.item).name)}`,short:`${have}/${sp.focal.count} ${lower(flower(x,sp.focal.item).name)}`,value:have?`${have}/${sp.focal.count}`:'',step:K.pick});}
  if(sp.palette){
    const allowed=new Set([...sp.palette,'green']);
    const off=[...new Set(st.map(s=>flower(x,s.i)).filter(fl=>fl.role!=='filler'&&!allowed.has(fl.color)).map(fl=>colour(x,fl.color).name))];
    out.push({ok:any&&!off.length,icon:'🎨',label:`Tông ${sp.palette.map(p=>colour(x,p).name).join(' – ')}`,short:`Tông ${sp.palette.map(p=>lower(colour(x,p).name)).join('–')}${off.length?` (lệch ${lower(off.join(', '))})`:''}`,note:off.length?`lệch: ${off.join(', ')}`:'',step:K.pick});
  }else out.push({ok:null,icon:'🎨',label:'Màu người nhận thích: chưa hỏi',short:'Màu: chưa hỏi',tone:'warn',step:K.palette});
  if(n.cats===true){
    const toxic=st.some(s=>flower(x,s.i).cats==='toxic'),caution=st.some(s=>flower(x,s.i).cats==='caution');
    out.push({ok:toxic?false:any,icon:'🐈',label:'Nhà có mèo: không hoa ly (độc với mèo)',short:'Có mèo: không ly',tone:'danger',note:toxic?'Trên bàn đang có hoa ly — bỏ ra!':caution?'Baby, bạch đàn: mèo gặm dễ đau bụng, nên tránh.':'',step:K.pick});
  }else if(n.cats==null)out.push({ok:null,icon:'🏠',label:'Nhà người nhận: chưa hỏi',short:'Nhà: chưa hỏi',tone:'warn',note:'Có nuôi mèo không? Hoa ly độc với mèo.',step:K.recipient});
  if(sp.card)out.push({ok:w.card?t.card_tone!=='wrong':null,icon:'💌',label:'Kèm thiệp viết tay',short:'Thiệp',note:t.card_tone==='plain'?'lời hơi chung chung':t.card_tone==='wrong'?'lời không hợp dịp':'',step:K.card});
  if(sp.banner)out.push({ok:w.banner?letters(w.banner)===letters(sp.banner):null,icon:'🎗️',label:`Băng rôn “${sp.banner}”`,short:'Băng rôn',note:w.banner&&letters(w.banner)!==letters(sp.banner)?`đang in “${w.banner}”`:'',step:K.banner});
  if(deliver(t)){
    if(n.delivery)out.push({ok:x.ui.slot?x.ui.slot===n.delivery:null,icon:'🛵',label:`Giao ${slotName(x,n.delivery)}`,short:`Giao ${slotName(x,n.delivery)}`,note:x.ui.slot&&x.ui.slot!==n.delivery?`đang chọn ${slotName(x,x.ui.slot)}`:'',step:K.slot});
    else out.push({ok:null,icon:'🛵',label:'Giao tận nơi · chưa hỏi giờ',short:'Giờ giao: chưa hỏi',tone:'warn',step:K.slotAsk||K.slot});
    if(rainy(x))out.push({ok:w.cover?true:null,icon:'🌧️',label:'Bọc nylon chống mưa',short:'Bọc nylon',step:K.cover});
  }
  return out;
}

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
  const row=w.done?{ok:true,icon:'💧',label:'Đã thay nước tủ mát hôm nay'}
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
  else if(due)btns=x.confirmCmd('💐 Cắm & giao đơn này','fl_pre',{id:b.id,do:'make'},`Cắm “${b.title}” từ hàng trong tủ? Khách trả nốt ${b.price-b.deposit} xu (${b.price} − cọc ${b.deposit}); hoa còn nụ hay sắp héo thì tiệm bớt 10 xu mỗi thứ. Tiệm dùng cành nở đẹp trước; khách đang chờ sẽ chờ thêm chút.`,'primary small',!!(b.short||[]).length||!x.room.open)
    +((b.short||[]).length?restockButton(x.room,(b.rows||[]).filter(r=>r.item&&r.have<r.need).map(r=>({id:r.item,target:r.need})),{urgent:false},'ghost small'):'');
  const say=b.status==='offer'?`<p class="fl-note">“${x.esc(b.call)}”</p>`:'';
  const tip=due?((b.short||[]).length?`<p class="small fl-warn">Thiếu: ${x.esc(b.short.join(', '))}.</p>`:''):'';
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
  return `<li class="fl-pre due">${head}<p class="small"><b>Hôm nay giao bình cho bà.</b></p>${card}<div class="fl-tpls">${menu}</div></li>`;
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
/** 🏷️ Bảng giá (chat #14 "tiệm hoa không có chỗ thay đổi giá bán"): the price list exists but no screen of the shop led
 * to it. Its flower prices are what the stems are worth against the order's budget; the customer pays the quoted price. */
const priceLink=x=>x.button('🏷️ Bảng giá','prices',{},'ghost small');
function priceNote(x){
  return `<p class="fl-price-note"><span>🏷️ Giá từng loại hoa: đổi trong Bảng giá trước khi mở ca. Giá hoa tính vào giá trị bó, khách vẫn trả đúng giá đơn đã báo.</span>${priceLink(x)}</p>`;
}
/** Between orders: what is in the cooler, oldest first, and how open it is. */
function coolerStrip(x){
  const d=data(x),cooler=d.cooler||{};
  const fl=(cc(x).flowers||[]).filter(f=>f.unlock<=lvl(x)||stock(x,f.id));
  if(!fl.length)return '';
  const old=fl.filter(f=>(cooler[f.id]?.next??9)<=0&&stock(x,f.id)).length;
  const have=fl.filter(f=>stock(x,f.id)+(cooler[f.id]?.spare||0)).length;
  return `<details class="fl-shelf fl-shelf-fold" aria-label="Tủ mát"><summary class="fl-shelf-head"><b>🧊 Trong tủ mát · ${have}/${fl.length} loại có hàng</b><small>${old?`${old} loại có cành sắp héo — dùng trước hoặc bỏ trong Kho`:''}</small></summary>
    <div class="fl-shelf-row">${fl.map(f=>{const q=stock(x,f.id)+(cooler[f.id]?.spare||0),left=q?cooler[f.id]?.next:null,st=stageLine(cooler[f.id]?.stages);
      return `<span class="fl-shelf-item${q?'':' is-empty'}${left!=null&&left<=0?' old':''}" title="${x.esc(f.name)}: ${q} ${x.esc(item(x,f.id).unit||'cành')} · ${freshLabel(left)}"><span class="count-badge${q?'':' is-empty'}" data-count="${q}">${q}</span>${glyph(x,f.id,'fl-shelf-emoji')}<small>${x.esc(f.name)}</small>${st?`<small class="fl-stage-txt">${x.esc(st)}</small>`:''}</span>`;}).join('')}</div></details>`;
}
const extras=x=>banners(x)+pinsCard(x);
/** On a job, the day (mod, served, streak) and the guest queue fold into one line; a tap opens them. */
function dayLine(x,day,t){
  const strip=dayStrip(x,day,true),q=queue(x,t);
  if(!strip&&!q)return '';
  const others=openTasks(x).filter(v=>v.id!==t.id),low=others.filter(v=>(v.patience??100)<50).length,m=day?.mod;
  const bits=[m?`${m.emoji} ${m.label}`:'',`✅ ${Number(day?.served)||0}`,others.length?`👥 ${others.length} khách chờ`:'',low?`⚠️ ${low} sốt ruột`:''].filter(Boolean).join(' · ');
  return `<details class="fl-dayfold${low?' low':''}"><summary>${x.esc(bits)}</summary>${strip}${q}</details>`;
}

/* ---------- the order ---------- */
/** Sets: one row per piece. Tap a waiting piece to switch, a finished one to take it back. */
function pieceTabs(t,x){
  const busy=started(t.work)&&!plated(t);
  return `<div class="fl-party" role="tablist" aria-label="Các món trong bộ">${t.needs.party.map((p,i)=>{
    const f=format(x,p.format),done=!!t.pieces[i],on=i===t.cur&&!done,off=on||(busy&&!on);
    return `<button type="button" role="tab" class="fl-pieceline${on?' on is-selected':''}${done?' done':''}" data-command="fl_tab" data-payload="${pay(x,{task:t.id,index:i})}" aria-selected="${on}"${off?' disabled':''}>
      <span class="fl-pieceno" aria-hidden="true">${done?'✓':i+1}</span><span class="fl-piecetext"><small>Món ${i+1} · ${done?'đã xong':on?'đang làm':busy?'chờ món đang làm xong':'chưa làm'}</small><b>${x.esc(p.label)}</b><span>${x.esc(f.emoji)} ${x.esc(f.name)} · ${p.stems[0]}–${p.stems[1]} cành</span></span></button>`;
  }).join('')}</div>`;
}
/** What the customer has told so far, and what is still worth asking. */
/** What the customer told when asked (goes inside the "Khách dặn" fold on the ticket). */
function heardList(t,x){
  const clues=Object.entries(t.needs.clues||{});
  return clues.length?`<p class="fl-brief-cap">💬 Khách kể thêm · ${clues.length}</p><ul class="fl-heard">${clues.map(([k,v])=>`<li><span aria-hidden="true">${x.esc(topic(x,k).emoji)}</span>“${x.esc(v)}”</li>`).join('')}</ul>`:'';
}
/** The questions still worth asking (stay open on the ticket). */
function consult(t,x){
  const heard='';
  const left=unasked(t);
  if(!left.length)return heard;
  const rush=t.guest?.kind==='rush',cost=rush?(cc(x).ask_cost_rush||7):(cc(x).ask_cost||5);
  return `${heard}<div class="fl-ask"><p class="fl-ask-head"><b>💬 Khách chưa nói hết</b><small>−${cost}% kiên nhẫn mỗi câu</small></p>
    <div class="fl-ask-btns">${left.map(k=>{const tp=topic(x,k);return `<button type="button" class="btn ghost fl-ask-btn" data-command="fl_ask" data-payload="${pay(x,{task:t.id,topic:k})}"><span aria-hidden="true">${x.esc(tp.emoji)}</span> ${x.esc(tp.label)}</button>`;}).join('')}</div></div>`;
}
function ticket(t,x,K={}){
  const who=x.npc(t.npc),n=t.needs,g=t.guest||{},o=occasion(x,n.occasion);
  const tags=[`<span class="tag">${x.esc(g.emoji||'🙂')} ${x.esc(g.label||'Khách')}</span>`,`<span class="tag">${x.esc(o.emoji)} ${x.esc(o.name)}</span>`];
  if(isSet(t))tags.push(`<span class="tag">🎁 Bộ ${n.party.length} món</span>`);
  if(!deliver(t))tags.push('<span class="tag">🏪 Nhận tại tiệm</span>');
  // The price is said once, here; the list below is what has to be right.
  const price=t.quoted_price!=null?`<b class="price" aria-label="Giá đơn">${x.money(t.quoted_price)}</b>`:'';
  const cap=isSet(t)&&!plated(t)?`Món ${t.cur+1}: ${spec(t).label}`:'Khách dặn';
  // The list is folded to one line with its tally: the chips on the cooler tab, the steps and the bar repeat it.
  const rows=briefRows(t,x,K);
  const nClues=Object.keys(t.needs.clues||{}).length;
  // The chips pinned over the work say the same with a live ✓; this fold keeps the full rows and what was said.
  const list=`<details class="fl-brief"><summary><b>📝 ${x.esc(cap)}</b><small>chi tiết${nClues?` · 💬 ${nClues} lời kể`:''}</small></summary>${reqRows(x,rows,cap)}${heardList(t,x)}</details>`;
  return `<article class="card ticket fl-ticket compact"><div class="fl-ticket-head">${x.portrait(who,40)}<div class="grow"><div class="row spread"><h3>${x.esc(who.display_name)}</h3>${price}</div>
    <p class="fl-tags">${tags.join(' ')}</p></div></div>
    <p class="fl-note">“${x.esc(n.note)}”</p>${consult(t,x)}${isSet(t)?pieceTabs(t,x):''}${list}${regularCard(t,x)}${patience(t.patience)}</article>`;
}

/* ---------- station panels ---------- */
/** The brief pinned over the work (asm_kit): one chip per requirement with a live ✓ / ✗, the flower
 * value against the budget, and the station tabs under it, so what the customer asked for stays in
 * sight while picking (feedback #11: the brief was folded away, "không bít làm gì đầu tiên"). */
function pin(t,x,K,tabs,next){
  const chips=briefRows(t,x,K).map(r=>({ok:r.ok,icon:r.icon,text:r.short||r.label,title:r.label+(r.note?` · ${r.note}`:'')}));
  if(!plated(t)){const v=Math.round(benchValue(t,x)/(spec(t).budget||1)*100);chips.push({ok:v>=70?true:null,icon:'💰',text:`Hoa ${v}% giá đơn`,title:'Giá trị hoa so với ngân sách (nên từ 70%)'});}
  const who=x.npc(t.npc),o=occasion(x,t.needs.occasion);
  const sub=`${x.esc(who.display_name)} · ${x.esc(o.emoji)} ${x.esc(o.name)}${isSet(t)&&!plated(t)?` · món ${t.cur+1}/${t.pieces.length}`:''}`;
  return reqPin(x,{sub,chips,tabs,key:t.id,next});
}
/** What the customer said about the flowers, for sorting the cooler (never the meaning book's taboos). */
function fitOf(t,x,f){
  const sp=spec(t);
  if(sp.focal?.item===f.id)return 2;                                   // named by the customer
  if(t.needs.cats===true&&f.cats==='toxic')return -1;                   // they said: a cat at home
  if(sp.palette&&(f.role==='filler'||[...sp.palette,'green'].includes(f.color)))return 1;  // on the palette they said
  return 0;
}
const pickCmd=(x,task,item,n=1)=>`data-command="fl_pick" data-payload="${pay(x,{task,item,n})}"`;
function coolerPanel(t,x){
  const sp=spec(t),w=t.work,d=data(x),level=lvl(x),c=counts(w.stems),max=cc(x).max_stems||30;
  const busy=w.arranged||soaking(t)||w.stems.length>=max,fixed=w.arranged||soaking(t);
  // Flowers above the shop's level collapse into one "🔒 N món mở ở cấp X–Y" chip after the grid.
  const lockedFl=(cc(x).flowers||[]).filter(f=>f.unlock>level&&sp.focal?.item!==f.id);
  // What the customer asked for first ("Khách cần"), then what fits the palette they said, then the rest.
  const list=(cc(x).flowers||[]).filter(f=>!lockedFl.includes(f)).map((f,i)=>({f,i,fit:fitOf(t,x,f)})).sort((a,b)=>b.fit-a.fit||a.i-b.i);
  const cards=list.map(({f,fit})=>{
    const info=d.cooler?.[f.id]||{},have=stock(x,f.id)+(info.spare||0),left=have?info.next:null,on=c[f.id]||0;
    const want=sp.focal?.item===f.id?Math.max(0,sp.focal.count-on):0;
    // Only for a home with cats, and in words.
    const flag=t.needs.cats!==true?'':f.cats==='toxic'?'🐈 độc với mèo':f.cats==='caution'?'🐈 mèo nên tránh':'';
    const sub=[on?`×${on} trên bàn`:'',freshLabel(left)].filter(Boolean).join(' · ');
    const main=tile(x,{item:f.id,glyph:glyph(x,f.id),name:f.name,sub,count:have,empty:!have,cmd:'fl_pick',payload:{task:t.id,item:f.id,n:1},selected:on>0,
      disabled:busy||!have,wanted:want>0,flag,flagCls:f.cats||'',cls:`fl-flower c-${f.color} ${left!=null&&left<=0?'old':''}`,
      label:`${f.name}: tủ còn ${have}, ${freshLabel(left)}${on?`, ${on} cành trên bàn`:''}. Chạm để lấy 1 cành`});
    const tag=fit===2?'<span class="asm-need">Khách cần</span>':fit===1?'<span class="asm-need soft">Đúng tông</span>':'';
    // Several stems at once: the number the customer named in one tap, then − n + once some are on the bench.
    const fill=want>1&&have>=want&&!busy?`<button type="button" class="btn small fl-fill-n" ${pickCmd(x,t.id,f.id,want)}>＋ ${want} cành</button>`:'';
    const step=on?stepper(x,{n:on,label:f.name,minus:fixed?'':`data-command="fl_remove" data-payload="${pay(x,{task:t.id,item:f.id,n:1})}"`,plus:busy||!have?'':pickCmd(x,t.id,f.id,1)}):'';
    return `<div class="fl-fcard${on?' on':''}${fit<0?' off':''}">${tag}${main}${fill}${step}</div>`;
  }).join('');
  const book=(cc(x).flowers||[]).map(f=>{const taboo=f.taboo.length>=6?'chỉ dùng cho viếng':f.taboo.map(o=>occasion(x,o).name).join(', ');
    return `<li><b>${glyph(x,f.id)} ${x.esc(f.name)}</b> — ${x.esc(f.meaning)}${f.good.length<8?`<small>Hợp: ${x.esc(f.good.map(o=>occasion(x,o).name).join(', '))}</small>`:''}${taboo?`<small class="fl-warn">Kiêng: ${x.esc(taboo)}</small>`:''}${f.cats==='toxic'?'<small class="fl-warn">Rất độc với mèo (cả phấn, lá, nước bình)</small>':f.cats==='caution'?'<small>Mèo gặm dễ đau bụng</small>':''}</li>`;}).join('');
  const old=w.stems.filter(s=>s.e-today(x)<=0).length;
  // Once stems are on the bench, the prep (cut, strip, soak) sits right under the cooler: one tab less.
  const prep=w.stems.length?`<section class="fl-prep-in"><h4 class="section-title">✂️ Sơ chế ${w.stems.length} cành${old?` <small class="fl-warn">· ${old} cành sắp héo</small>`:''}</h4>${prepPanel(t,x)}</section>`:'';
  return `<div class="fl-grid fl-cards">${cards}</div>${lockChip(lockedFl.map(f=>f.unlock),'fl-lock')}${prep}
    <details class="fl-book"><summary>📖 Sổ tay ý nghĩa hoa</summary><ul>${book}</ul></details>`;
}
function prepPanel(t,x){
  const w=t.work,f=format(x,spec(t).format),d=data(x),min=soakMin(t,x);
  const uncut=w.stems.filter(s=>!s.c).length,bare=w.stems.filter(s=>!s.s).length,locked=w.arranged||soaking(t);
  const others=(d.buckets||[]).filter(b=>b.task!==t.id);
  const full=(d.buckets||[]).length>=(cc(x).buckets||2)&&!soaking(t);
  return `<h4 class="section-title">1 · Cắt gốc dưới vòi nước</h4>
    <div class="row wrap">${x.cmd(`✂️ Cắt xéo 45° (${uncut})`,'fl_cut',{task:t.id,angle:'angled'},'',!uncut||locked)}${x.cmd('Cắt thẳng cho nhanh','fl_cut',{task:t.id,angle:'straight'},'ghost small',!uncut||locked)}</div>
    <h4 class="section-title">2 · Tuốt lá, gai phần gốc</h4>
    ${x.cmd(`🍃 Tuốt lá dưới mực nước (${bare})`,'fl_strip',{task:t.id},'',!bare||locked)}
    <h4 class="section-title">3 · Ngâm xô nước mát</h4>
    <div class="fl-pails">${soakMeter(x,w.soak,min)}${others.map(()=>`<div class="fl-other small">🪣 Xô bên cạnh đang ngâm hoa của đơn khác</div>`).join('')}</div>
    <div class="row wrap">${x.cmd('🪣 Thả vào xô','fl_soak',{task:t.id},'',!w.stems.length||!!uncut||w.arranged||soaking(t)||full)}${x.cmd('🙌 Nhấc ra','fl_lift',{task:t.id},'',!soaking(t))}</div>
    ${full?'<p class="notice small">Cả hai xô đang bận. Nhấc hoa của đơn khác ra trước.</p>':''}
    ${f.soak?'':'<p class="muted small">Cắm mút: không cần ngâm xô.</p>'}`;
}
function designPanel(t,x){
  const sp=spec(t),w=t.work,level=lvl(x),min=t.foam_min||cc(x).foam_min||10;
  const lockedFm=(cc(x).formats||[]).filter(f=>f.unlock>level&&sp.format!==f.id);
  const bases=(cc(x).formats||[]).filter(f=>!lockedFm.includes(f)).map(f=>{
    const locked=false,uses=Object.entries(f.uses||{}),short=uses.filter(([k,q])=>stock(x,k)<q);
    const main=uses[0]?stock(x,uses[0][0]):null;
    const sub=locked?`cấp ${f.unlock}`:uses.length?uses.map(([k,q])=>`${item(x,k).name} ${stock(x,k)}`).join(' · '):'dây buộc, giấy gói';
    return tile(x,{emoji:f.emoji,name:f.name,sub,count:main,empty:short.length>0,cmd:'fl_base',payload:{task:t.id,kind:f.id},selected:w.base===f.id,locked,disabled:!!w.base||short.length>0,
      label:locked?`${f.name}, mở ở cấp ${f.unlock}`:`${f.name}${short.length?', thiếu vật tư':''}`});
  }).join('');
  const foam=w.foam?`${foamMeter(x,w.foam,min)}${w.arranged?'':x.confirmCmd('👇 Ấn mút chìm cho nhanh','fl_push',{task:t.id},'Ấn mút xuống sẽ nhốt không khí, lõi mút khô. Vẫn làm?','ghost small',w.foam.pushed)}`:'';
  const verb={bouquet:'🌀 Bó xoắn ốc & buộc dây',vase:'🏺 Cắm vào bình',basket:'🧺 Cắm vào giỏ',wreath:'🕊️ Cắm kín mặt kệ'}[w.base]||'Cắm hoa';
  const foamWait=w.foam&&!w.foam.pushed&&x.now()-w.foam.start<min;
  const canArrange=w.base&&!w.arranged&&w.stems.length>=3&&!soaking(t)&&!w.stems.some(s=>!s.c)&&!foamWait;
  const arrange=`<div class="row wrap">${x.cmd(verb,'fl_arrange',{task:t.id},'',!canArrange)}${x.cmd('↩️ Tháo ra','fl_untie',{task:t.id},'ghost small',!w.arranged||!!w.paper||!!w.ribbon||!!w.banner)}</div>`;
  let step=3;
  const papers=w.base==='bouquet'?`<h4 class="section-title">${step++} · Giấy gói</h4><div class="fl-swatches">${(cc(x).papers||[]).map(p=>swatch(x,{cmd:'fl_wrap',payload:{task:t.id,paper:p.id},hex:p.hex,name:p.name,count:stock(x,p.item),selected:w.paper===p.id,disabled:!w.arranged||!!w.paper||!stock(x,p.item)})).join('')}</div>`:'';
  const ribbons=`<h4 class="section-title">${step++} · Ruy băng <span class="fl-swatch-n${stock(x,'ribbon')?'':' zero'}">${stock(x,'ribbon')}</span></h4><div class="fl-swatches">${(cc(x).ribbons||[]).map(r=>swatch(x,{cmd:'fl_ribbon',payload:{task:t.id,color:r.id},hex:r.hex,name:r.name,selected:w.ribbon===r.id,disabled:!w.arranged||!!w.ribbon||(w.base==='bouquet'&&!w.paper)||!stock(x,'ribbon')})).join('')}</div>
    ${x.cmd('✂️ Gỡ giấy & ruy băng','fl_unwrap',{task:t.id},'ghost small',!w.paper&&!w.ribbon)}`;
  const banner=w.base==='wreath'?`<h4 class="section-title">${step++} · Băng rôn chữ <span class="fl-swatch-n${stock(x,'banner')?'':' zero'}">${stock(x,'banner')}</span></h4>${w.banner?`<p class="fl-printed">🎗️ “${x.esc(w.banner)}”</p>`:''}
    <div class="fl-write"><label class="field grow">Nội dung in<input id="fl-banner-text" class="input" maxlength="60" autocomplete="off" spellcheck="false" value="${x.esc(x.ui.bannerText||'')}" placeholder="Gõ đúng từng chữ, có dấu"></label>${x.button(w.banner?'🖨️ In lại':'🖨️ In & treo','car:banner',{task:t.id},'',!stock(x,'banner'))}</div>${outOf(x,'banner','băng rôn',t.id,2)}
    ${sp.banner&&letters(w.banner||'')!==letters(sp.banner)?`<p class="fl-suggest">${x.button('📋 In đúng chữ khách dặn','car:bannertpl',{task:t.id,text:sp.banner},'ghost small',!w.arranged||!stock(x,'banner'))}</p>`:''}`:'';
  const cover=rainy(x)&&deliver(t)?`<h4 class="section-title">${step++} · Chống mưa</h4><div class="row wrap">${x.cmd(w.cover?'✓ Đã bọc nylon':'🌂 Bọc nylon chống mưa','fl_cover',{task:t.id},w.cover?'ghost small':'',!!w.cover||!w.arranged||(w.base==='bouquet'&&!w.paper))}</div>`:'';
  return `<h4 class="section-title">1 · Kiểu cắm</h4><div class="tile-grid fl-grid">${bases}</div>${lockChip(lockedFm.map(f=>f.unlock),'fl-lock')}${foam}
    <h4 class="section-title">2 · Cắm / bó</h4>${arrange}${papers}${ribbons}${banner}${cover}`;
}
function cardPanel(t,x){
  const n=t.needs,sp=spec(t),w=t.work,tone=t.card_tone;
  const toneLine=w.card?`<p class="fl-tone ${tone||''}">${{fit:'✓ Lời thiệp hợp dịp.',plain:'○ Lời hơi chung chung — thêm một câu đúng dịp sẽ ấm hơn.',wrong:'✗ Lời thiệp không hợp dịp này!'}[tone]||''}</p>`:'';
  const card=`<h4 class="section-title">Thiệp viết tay <span class="fl-swatch-n${stock(x,'card')?'':' zero'}">${stock(x,'card')}</span></h4>
    <div class="fl-write"><label class="field grow">Lời nhắn<textarea id="fl-card-text" class="input" rows="3" maxlength="160" spellcheck="false" placeholder="Viết đúng dịp: ${x.esc(lower(occasion(x,n.occasion).name))}…">${x.esc(x.ui.cardText??w.card??'')}</textarea></label>
    ${x.button(w.card?'✍️ Viết lại thiệp mới':'✍️ Viết thiệp','car:card',{task:t.id},'',!stock(x,'card'))}</div>${outOf(x,'card','thiệp',t.id,6)}${toneLine}
    ${w.card&&tone==='fit'?'':`<p class="fl-suggest"><small>Gợi ý: “${x.esc(cardLine(t))}”</small>${x.button('✨ Dùng lời này','car:cardtpl',{task:t.id,text:cardLine(t)},'ghost small',!stock(x,'card'))}</p>`}`;
  let slots='';
  if(deliver(t)){
    slots=`<h4 class="section-title">Khung giờ giao</h4>${n.delivery?'':'<p class="notice amber small">🕒 Chưa hỏi khách giờ giao.</p>'}
      <div class="fl-segs" role="group" aria-label="Khung giờ giao">${(cc(x).slots||[]).map(s=>seg(x,'slot','slot',s.id,s.name,x.ui.slot)).join('')}</div>`;
  }
  return card+slots;
}

/* ---------- next steps (guide.js): the same facts as the lists, each with the tap that does it ---------- */
function pieceReady(t){
  const sp=spec(t),w=t.work;
  if(!w.base||!w.arranged||soaking(t))return false;
  if(w.base==='bouquet'&&(!w.paper||!w.ribbon))return false;
  if(w.base==='wreath'&&!w.banner)return false;
  if(sp.card&&!w.card)return false;
  return true;
}
const BASE_PRICE={bouquet:25,vase:40,basket:45,wreath:70};
const worth=(x,id,base)=>x.room.life?.prices?.[id]??base;
const stemPrice=(x,id)=>worth(x,id,item(x,id).price||10);
const learning=x=>((x?.room?.metrics?.served)||0)<3;
const onHand=(x,id)=>stock(x,id)+(data(x).cooler?.[id]?.spare||0);
/** The bench as the server values it: the stems plus the base the brief asks for. */
const benchValue=(t,x)=>{const f=spec(t).format;return t.work.stems.reduce((v,s)=>v+stemPrice(x,s.i),0)+worth(x,f,BASE_PRICE[f]||0);};
/** One card line per occasion that reads as "fits the occasion" (one tap; writing your own still works). */
const CARD={birthday:'Chúc mừng sinh nhật! Tuổi mới thật khỏe mạnh, bình an và nhiều niềm vui nhé.',
  condolence:'Thành kính chia buồn cùng gia đình. Cầu mong người đã khuất được yên nghỉ.',
  opening:'Chúc mừng khai trương! Chúc tiệm hồng phát, đắt khách, vạn sự thành công.',
  apology:'Thành thật xin lỗi. Mong em tha thứ, thương em nhiều lắm.',
  oct20:'Chúc mừng ngày Phụ nữ Việt Nam 20/10! Cảm ơn vì tất cả yêu thương.',
  mar8:'Chúc mừng ngày 8/3! Luôn xinh đẹp và hạnh phúc nhé.',
  graduation:'Chúc mừng tốt nghiệp! Tự hào về bạn, chặng đường mới thật thành công nhé.',
  proposal:'Làm vợ anh nhé? Anh muốn mãi mãi bên nhau, trọn đời yêu em.'};
const cardLine=t=>CARD[t.needs.occasion]||CARD.birthday;
/** A control on another tab: switch there first, then glow it. */
const tabOf=k=>k==='prep'?'cooler':k;   // the prep steps sit under the cooler (three tabs, not four)
const point=(x,tab,sel,label)=>x.ui.tab===tabOf(tab)?{sel,label}:{act:'car:goto',data:{tab:tabOf(tab),sel},label};
/** A step that needs real seconds: one tap waits (live countdown in the label), then does it. */
function waitGo(t,x,cmd,at,what,done,then=''){
  const left=Math.ceil(at-x.now());
  if(left<=0)return then?seqGo([[cmd,{task:t.id}],[then,{task:t.id}]],done):{cmd,payload:{task:t.id},label:done};
  return {act:'car:wait',data:{task:t.id,cmd,then,at:at.toFixed(2)},label:`<span>⏱ ${what} · <span data-fl-count data-at="${at.toFixed(2)}">còn ${left} giây</span></span>`};
}
/** Two bench commands that always go together, as one tap (e.g. cut + strip). */
const seqGo=(list,label)=>({act:'car:seq',data:{seq:JSON.stringify(list)},label});
/** What frees the bench for a fix: out of the bucket, then paper/ribbon off, then untie. */
function unlockGo(t){
  const w=t.work,task=t.id;
  if(soaking(t))return {cmd:'fl_lift',payload:{task},label:'🙌 Nhấc hoa khỏi xô để sửa'};
  if(w.paper||w.ribbon)return {cmd:'fl_unwrap',payload:{task},confirm:'Gỡ giấy và ruy băng (bỏ vật liệu cũ) để sửa bó?',label:'✂️ Gỡ giấy & ruy băng để sửa'};
  if(w.arranged&&!w.banner)return {cmd:'fl_untie',payload:{task},label:'↩️ Tháo bó ra để sửa'};
  return {cmd:'fl_dump',payload:{task},confirm:'Bỏ toàn bộ hoa và vật liệu đang dùng, làm lại từ đầu?',label:'🗑️ Bỏ bó, làm lại'};
}
/** The first order: which stems make this brief right from what is in the cooler now ({id:count});
 * null while the brief still has unknowns (ask first). Suits the occasion, stays on the palette,
 * never a cat hazard, fills to ~85% of the budget and at least the minimum count. */
function recipe(t,x){
  const sp=spec(t),n=t.needs,occ=n.occasion,d=data(x),lv=lvl(x);
  if(!sp.palette||n.cats==null)return null;
  const pal=new Set([...sp.palette,'green']),plan={};
  const fits=f=>(f.unlock<=lv||sp.focal?.item===f.id)&&!f.taboo.includes(occ)&&!f.bad.includes(occ)&&!(n.cats&&f.cats)
    &&onHand(x,f.id)>0&&(d.cooler?.[f.id]?.next??1)>0&&(f.role==='filler'||pal.has(f.color));
  const all=(cc(x).flowers||[]).filter(fits),[lo,hi]=sp.stems;
  let stems=0,value=worth(x,sp.format,BASE_PRICE[sp.format]||0);
  const room=id=>(plan[id]||0)<onHand(x,id);
  const add=id=>{plan[id]=(plan[id]||0)+1;stems++;value+=stemPrice(x,id);};
  if(sp.focal)for(let i=0;i<sp.focal.count&&room(sp.focal.item);i++)add(sp.focal.item);
  const heads=all.filter(f=>f.role==='focal'&&f.id!==sp.focal?.item);
  const good=heads.filter(f=>f.good.includes(occ)),other=heads.filter(f=>!f.good.includes(occ)),fill=all.filter(f=>f.role!=='focal');
  const take=(group,more)=>{for(let i=0,g=0;more()&&g<60;g++){const open=group.filter(f=>room(f.id));if(!open.length)return;const f=open[i++%open.length];if(add(f.id)===false)return;}};
  for(const group of [good,other])take(group,()=>stems<hi&&value<sp.budget*.85);
  for(const group of [fill,good,other])take(group,()=>stems<lo);
  return plan;
}
/** Pick the stems: first what is wrong on the bench (one tap each), then what is missing. */
function pickStep(t,x){
  const sp=spec(t),n=t.needs,w=t.work,occ=n.occasion,c=counts(w.stems),total=w.stems.length,[lo,hi]=sp.stems;
  const label='Chọn hoa đúng phiếu',note=`${total} cành (cần ${lo}–${hi})`,locked=w.arranged||soaking(t);
  const pal=sp.palette?new Set([...sp.palette,'green']):null;
  const fix=id=>locked?unlockGo(t):{cmd:'fl_remove',payload:{task:t.id,item:id},label:`➖ Bỏ 1 cành ${x.esc(lower(flower(x,id).name))}`};
  for(const id of Object.keys(c)){
    const f=flower(x,id);
    const why=n.cats===true&&f.cats==='toxic'?`${f.name} độc với mèo`:f.taboo.includes(occ)?`${f.name} không hợp dịp ${lower(occasion(x,occ).name)}`
      :f.bad.includes(occ)?`${f.name} dễ bị hiểu sai ý`:pal&&f.role!=='filler'&&!pal.has(f.color)?`${f.name} lệch tông màu`
      :sp.focal?.item===id&&c[id]>sp.focal.count?`thừa ${lower(f.name)}, cần đúng ${sp.focal.count}`:'';
    if(why)return {ok:false,label:`Bỏ ra: ${why}`,note,go:fix(id),tab:'cooler'};
  }
  if(total>hi){const id=Object.keys(c).find(k=>k!==sp.focal?.item)||Object.keys(c)[0];return {ok:false,label:`Quá nhiều cành: tối đa ${hi}`,note,go:fix(id),tab:'cooler'};}
  const focalShort=sp.focal?sp.focal.count-(c[sp.focal.item]||0):0,thin=benchValue(t,x)<sp.budget*.7;
  if(focalShort<=0&&total>=lo&&!thin)return {ok:true,label,note,tab:'cooler'};
  const miss=focalShort>0?`thiếu ${focalShort} cành ${lower(flower(x,sp.focal.item).name)}`:total<lo?`thêm ${lo-total} cành nữa`:'bó còn thưa so với ngân sách';
  if(locked)return {ok:w.arranged?false:null,label,note:miss,go:w.arranged?unlockGo(t):null,tab:'cooler'};
  // While learning (the first orders): one tap picks exactly what the order needs, and on the very
  // first order the right flower glows too. Later orders: the button points at the cooler.
  if(learning(x)){
    const plan=recipe(t,x),left=plan&&Object.entries(plan).map(([id,q])=>[id,q-(c[id]||0)]).filter(([,q])=>q>0);
    if(left?.length){
      const s={ok:null,label,tab:'cooler',go:{act:'car:fill',data:{task:t.id,items:left.map(([id,q])=>`${id}:${q}`).join(',')},
        label:`✨ Lấy đúng hoa · ${left.map(([id,q])=>`${q}${x.esc(flower(x,id).emoji)}`).join(' ')}`}};
      if(firstTime(x))s.pulse=`.fl-flower[data-fl-item="${left[0][0]}"]`;
      return s;
    }
  }
  return {ok:null,label,note:miss,tab:'cooler',go:point(x,'cooler','.fl-grid','🧊 Chọn hoa trong tủ mát')};
}
function paperPick(t,x){
  const pal=spec(t).palette||[];
  const pref=t.needs.occasion==='condolence'?['white','kraft','black']:pal.includes('pink')?['pink','kraft','white']:['kraft','white','pink'];
  return pref.find(p=>stock(x,paper(x,p).item)>0)||null;
}
function ribbonPick(t,x){
  const ids=(cc(x).ribbons||[]).map(r=>r.id),pal=spec(t).palette||[];
  const pref=t.needs.occasion==='condolence'?['white','black']:[...pal.map(c=>c==='yellow'?'gold':c),'white','gold'];
  return pref.find(r=>ids.includes(r))||ids[0]||'white';
}
function slotStep(t,x){
  const n=t.needs,s=x.ui.slot;
  if(n.delivery)return {ok:s?s===n.delivery:null,label:`Chọn giờ giao: ${slotName(x,n.delivery)}`,note:s&&s!==n.delivery?`đang chọn ${slotName(x,s)}`:'',tab:'card',
    go:s===n.delivery?null:{act:'car:slot',data:{slot:n.delivery},label:`🕒 Giao lúc ${x.esc(slotName(x,n.delivery))}`}};
  return {ok:s?true:null,label:'Chọn khung giờ giao',tab:'card',go:s?null:point(x,'card','.fl-segs','🕒 Chọn khung giờ giao')};
}
const STEP_ICON={event:'⚡',palette:'🎨',recipient:'🏠',slotAsk:'🕒',pick:'💐',cut:'✂️',strip:'🍃',soak:'🪣',base:'🧺',card:'💌',lift:'🙌',arrange:'🌀',
  wrap:'🎁',ribbon:'🎀',banner:'🎗️',cover:'🌂',wilt:'🥀',slot:'🛵'};
/** Every step of the order, in working order; K names them for the ticket rows. */
function orderSteps(t,x){
  const K={},S=[],n=t.needs,task=t.id;
  const push=(k,s)=>{if(s){s.icon??=STEP_ICON[k];K[k]=s;S.push(s);}};
  if(data(x).day?.open_event)push('event',{ok:null,label:'Chuyện bất ngờ: chọn cách xử lý',go:{sel:'.fk-event .fk-choice:not([disabled])',label:'⚡ Chọn cách xử lý chuyện bất ngờ'}});
  for(const k of unasked(t)){const tp=topic(x,k);push(k==='slot'?'slotAsk':k,{ok:null,label:tp.label,go:{cmd:'fl_ask',payload:{task,topic:k},label:`💬 Hỏi khách: ${x.esc(lower(tp.label))}`}});}
  if(plated(t)){if(deliver(t))push('slot',slotStep(t,x));return {S,K};}
  const sp=spec(t),w=t.work,st=w.stems,total=st.length,fm=format(x,sp.format),inPail=soaking(t),locked=w.arranged||inPail;
  push('pick',pickStep(t,x));
  const uncut=st.filter(s=>!s.c).length,straight=st.filter(s=>s.c===2).length,bare=st.filter(s=>!s.s).length,dry=st.filter(s=>!s.h).length;
  push('cut',{ok:total&&!uncut?true:null,label:'Cắt xéo gốc 45°',note:straight?`${straight} gốc cắt thẳng, hút nước kém`:'',tab:'prep',
    go:!uncut||locked?null:bare?seqGo([['fl_cut',{task,angle:'angled'}],['fl_strip',{task}]],`✂️ Cắt xéo gốc & tuốt lá ${uncut} cành`)
      :{cmd:'fl_cut',payload:{task,angle:'angled'},label:`✂️ Cắt xéo 45° ${uncut} gốc`}});
  push('strip',{ok:total&&!bare?true:null,label:'Tuốt lá dưới mực nước',tab:'prep',
    go:bare&&!locked?{cmd:'fl_strip',payload:{task},label:`🍃 Tuốt lá ${bare} cành`}:null});
  if(fm.soak){
    const pails=data(x).buckets||[],full=!inPail&&pails.length>=(cc(x).buckets||2),other=pails.find(b=>b.task!==task);
    push('soak',{ok:total&&(inPail||!dry)?true:null,label:'Thả hoa vào xô nước',note:full?'cả hai xô đang bận':'',tab:'prep',
      go:!total||inPail||!dry||uncut||w.arranged?null:full?(other?{cmd:'task_select',payload:{task:other.task},label:'🪣 Sang đơn đang ngâm để nhấc hoa ra'}:null)
        :{cmd:'fl_soak',payload:{task},label:'🪣 Thả hoa vào xô nước'}});
  }
  // While the stems soak: the base and the card.
  const short=Object.entries(fm.uses||{}).filter(([k,q])=>stock(x,k)<q);
  const soakStep=K.soak;
  if(soakStep?.go?.cmd==='fl_soak'&&!w.base&&!short.length)
    soakStep.go=seqGo([['fl_soak',{task}],['fl_base',{task,kind:sp.format}]],`🪣 Ngâm hoa & chuẩn bị ${x.esc(lower(fm.name))}`);
  push('base',{ok:w.base?w.base===sp.format:null,label:`Chọn kiểu: ${fm.name}`,tab:'design',
    note:w.base&&w.base!==sp.format?`đang làm ${lower(format(x,w.base).name)}`:!w.base&&short.length?`thiếu ${short.map(([k])=>lower(item(x,k).name)).join(', ')}`:'',
    go:w.base?(w.base===sp.format?null:inPail?unlockGo(t):{cmd:'fl_dump',payload:{task},confirm:'Sai kiểu cắm: bỏ bó và làm lại từ đầu?',label:'🗑️ Bỏ bó, làm lại đúng kiểu'})
      :short.length?restockFor(x,short.map(([k])=>k),short.map(([k])=>lower(item(x,k).name)).join(', ')):{cmd:'fl_base',payload:{task,kind:sp.format},label:`${x.esc(fm.emoji)} Chuẩn bị ${x.esc(lower(fm.name))}`}});
  if(sp.card){
    const tone=t.card_tone,ok=w.card?(tone==='fit'?true:tone==='wrong'?false:null):null;
    push('card',{ok,label:'Viết thiệp đúng dịp',note:tone==='plain'?'lời hơi chung chung':tone==='wrong'?'lời không hợp dịp':'',tab:'card',
      go:ok===true?null:!stock(x,'card')?restockFor(x,'card','thiệp'):{act:'car:cardtpl',data:{task,text:cardLine(t)},label:w.card?'✍️ Viết lại thiệp bằng lời gợi ý':'✍️ Viết thiệp (lời gợi ý hợp dịp)'}});
  }
  if(fm.soak){
    const min=soakMin(t,x);
    push('lift',{ok:total&&!dry&&!inPail?true:null,label:`Ngâm đủ ${min} giây rồi nhấc ra`,tab:'prep',
      go:inPail?(w.base===sp.format&&total>=3&&!uncut
        ?waitGo(t,x,'fl_lift',w.soak+min,'Chờ đủ nước rồi nhấc ra & bó','🙌 Nhấc hoa ra & bó','fl_arrange')
        :waitGo(t,x,'fl_lift',w.soak+min,'Chờ hoa hút đủ nước rồi nhấc ra','🙌 Nhấc hoa ra (đủ nước)')):null});
  }
  const foamAt=w.foam&&!w.foam.pushed&&!w.arranged?w.foam.start+(t.foam_min||cc(x).foam_min||10):0;
  const verb={bouquet:'🌀 Bó xoắn ốc & buộc dây',vase:'🏺 Cắm vào bình',basket:'🧺 Cắm vào giỏ',wreath:'🕊️ Cắm kín mặt kệ'}[sp.format]||'Cắm hoa';
  const canArrange=w.base&&!w.arranged&&total>=3&&!inPail&&!uncut;
  push('arrange',{ok:w.arranged||null,label:{bouquet:'Bó xoắn ốc',vase:'Cắm bình',basket:'Cắm giỏ',wreath:'Cắm kệ'}[sp.format]||'Cắm hoa',tab:'design',
    go:!canArrange?null:foamAt?waitGo(t,x,'fl_arrange',foamAt,'Chờ mút tự chìm rồi cắm',verb):{cmd:'fl_arrange',payload:{task},label:verb}});
  if(fm.wrap){
    const pp=paperPick(t,x);
    push('wrap',{ok:w.paper?true:null,label:'Gói giấy',note:w.paper?paper(x,w.paper).name:'',tab:'design',
      go:!w.arranged||w.paper?null:!pp?restockFor(x,(cc(x).papers||[]).map(p=>p.item).filter(Boolean),'giấy gói')
        :!w.ribbon&&stock(x,'ribbon')?seqGo([['fl_wrap',{task,paper:pp}],['fl_ribbon',{task,color:ribbonPick(t,x)}]],`🎁 Gói ${x.esc(lower(paper(x,pp).name))} & thắt nơ`)
        :{cmd:'fl_wrap',payload:{task,paper:pp},label:`🎁 Gói ${x.esc(lower(paper(x,pp).name))}`}});
  }
  const rb=ribbonPick(t,x),canRibbon=w.arranged&&!w.ribbon&&(sp.format!=='bouquet'||w.paper);
  push('ribbon',{ok:w.ribbon?true:null,label:'Thắt ruy băng',note:w.ribbon?ribbon(x,w.ribbon).name:'',tab:'design',
    go:!canRibbon?null:stock(x,'ribbon')?{cmd:'fl_ribbon',payload:{task,color:rb},label:`🎀 Thắt ruy băng ${x.esc(lower(ribbon(x,rb).name))}`}:restockFor(x,'ribbon','ruy băng')});
  if(sp.banner){
    const right=!!w.banner&&letters(w.banner)===letters(sp.banner);
    push('banner',{ok:w.banner?right:null,label:'In băng rôn đúng chữ',note:w.banner&&!right?`đang in “${w.banner}”`:'',tab:'design',
      go:!w.arranged||right?null:stock(x,'banner')?{act:'car:bannertpl',data:{task,text:sp.banner},label:'🖨️ In băng rôn đúng chữ khách dặn'}:restockFor(x,'banner','băng rôn')});
  }
  if(rainy(x)&&deliver(t))push('cover',{ok:w.cover||null,label:'Bọc nylon chống mưa',tab:'design',
    go:!w.cover&&w.arranged&&(sp.format!=='bouquet'||w.paper)?{cmd:'fl_cover',payload:{task},label:'🌂 Bọc nylon chống mưa'}:null});
  const wilt=st.filter(s=>s.e-today(x)<=0).length;
  if(wilt)push('wilt',{ok:false,label:`${wilt} cành sắp héo`,note:'khách sẽ chê: bỏ ra, thay cành tươi',tab:'cooler'});
  if(deliver(t)&&!pendingOthers(t).length)push('slot',slotStep(t,x));
  return {S,K};
}
/** The finishing action: "piece done" inside a set, otherwise the hand-off. */
function finalFor(t,x,S){
  const n=t.needs,task=t.id;
  if(isSet(t)&&!plated(t)&&pendingOthers(t).length)
    return {label:`✅ Xong món ${t.cur+1}, đặt sang bàn chờ`,go:finalGo(S,'fl_done',{task}),ready:pieceReady(t),why:'cắm, gói xong món này'};
  const blocked=!!data(x).day?.open_event,payload={task},made=plated(t)||pieceReady(t),slot=!deliver(t)||!!x.ui.slot;
  if(deliver(t)&&x.ui.slot)payload.slot=x.ui.slot;
  const q=deliver(t)?`Giao lúc ${slotName(x,x.ui.slot||n.delivery||'')}? Người nhận sẽ xem kỹ hoa, thiệp và màu sắc.`:'Khách sẽ xem kỹ hoa, thiệp và màu sắc.';
  return {label:deliver(t)?'🛵 Giao hoa':'💐 Trao hoa cho khách',go:finalGo(S,'fl_deliver',payload,{question:q,confirm:true}),ready:made&&slot&&!blocked,
    why:blocked?'xử lý chuyện bất ngờ trước':!made?'cắm, gói xong bó hoa':'chọn khung giờ giao'};
}
/* The bench follows the guide: after a tap on the hint, the bottom button or a step row, the next
 * render shows the tab of the next step. A tap on the bench's own controls (a flower tile, a tab)
 * leaves the player where they are, so picking by hand is never pulled away mid-choice. */
let follow=true;
globalThis.document?.addEventListener('click',e=>{
  const el=e.target?.closest?.('[data-command],[data-action]');
  if(el?.closest('#sheet .career-job.fl')||el?.closest('#sheet .gd-next'))follow=!!el.closest('.gd-cta,.gd-hint,.gd-todo,.gd-alt,.gd-final');
},true);
/** {steps, K, final, pulse} for the header hint, the lists and the bottom button. */
function taskGuide(t,x){
  if(!t.known)return {steps:[{ok:null,label:'Hỏi dịp tặng & ngân sách',go:{cmd:'ask',payload:{task:t.id},label:'📝 Nghe yêu cầu'}}],K:{},pulse:'.fl-listen'};
  const {S,K}=orderSteps(t,x);
  return {steps:S,K,final:finalFor(t,x,S)};
}
/** Several commands from one tap, in order; stops at the first refusal. While they run the hint and
 * the button say "Đang làm…"; the flag drops before the last command so its own render is the real one. */
async function run(x,list){
  if(x.ui.flBusy||!list.length)return;
  x.ui.flBusy=true;
  for(let i=0;i<list.length;i++){
    if(i===list.length-1)x.ui.flBusy=false;
    if(!await x.send(list[i][0],list[i][1])){x.ui.flBusy=false;x.render();return;}
  }
}
// While a one-tap sequence is still sending, the hint and the button wait instead of offering its middle step.
const BUSY={ok:null,label:'Đang làm…',go:{act:'car:busy',label:'⏳ Đang làm…'}};
function hintFor(g,x){
  if(x.ui.flBusy)return nextHint(x,[BUSY]);
  const f=g.final&&g.final.ready!==false?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null;
  return nextHint(x,g.steps,{final:f,pulse:g.pulse||''});
}

export default {
  id:'florist',
  css:true,
  next(t,x){
    // Plain text like the old line (the host translates it before it is shown); labels hold no markup.
    try{const n=pending(taskGuide(t,x).steps);if(n)return stepLine(n);}catch{/* fall back to a fixed line */}
    return t.known?'Trao hoa cho khách!':'Hỏi dịp tặng & ngân sách';
  },
  idle(x){
    const d=data(x),open=openTasks(x);
    // Between orders the hint names the way on: the surprise, else the next waiting guest
    // (no guest waiting: the host's own button — new guest or close the day — leads).
    const steps=d.day?.open_event?[{ok:null,label:'Chuyện bất ngờ: chọn cách xử lý',go:{sel:'.fk-event .fk-choice:not([disabled])'}}]
      :open.length?[{ok:null,label:'Làm đơn tiếp theo',go:{act:'nextJob',label:'👉 Làm đơn tiếp theo'}}]:[];
    const html=idlePanel(x,d.day,'fl_event',extras(x)+careBoard(x)+coolerStrip(x)+priceNote(x)+bookFold(x),null,'fl');
    return html.replace(/^(<div[^>]*>)/,`$1${nextHint(x,steps,{cta:false})}`);
  },
  job(t,x){
    const d=data(x),day=d.day,ui=x.ui;
    const top=g=>`${hintFor(g,x)}${dayLine(x,day,t)}${flash(x,day)}${eventCard(x,day,'fl_event')}`;
    if(!t.known){
      const who=x.npc(t.npc),gs=t.guest||{};
      return `<div class="career-job fl food">${top(taskGuide(t,x))}<article class="card ticket fl-ticket"><div class="fl-ticket-head">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3>
        <p class="fl-tags"><span class="tag">${x.esc(gs.emoji||'🙂')} ${x.esc(gs.label||'Khách')}</span></p></div></div>
        <p class="fl-say">“${x.esc(t.opening)}”</p>${regularCard(t,x)}${patience(t.patience)}${x.cmd('📝 Nghe yêu cầu','ask',{task:t.id},'primary full fl-listen')}</article>${extras(x)}${careFold(x)}</div>`;
    }
    const w=t.work;
    if(ui.tabFor!==t.id){ui.tabFor=t.id;ui.cardText=null;ui.bannerText='';ui.slot=null;ui.pieceFor=t.cur;ui.flSig=null;}
    if(ui.pieceFor!==t.cur){ui.pieceFor=t.cur;ui.cardText=null;ui.bannerText='';ui.flSig=null;}
    let g=taskGuide(t,x);
    // The bench follows the work: whenever something changed on it, show the tab of the next step.
    const sig=[t.id,t.cur,w.stems.map(s=>`${s.i}${s.c}${+s.s}${+s.h}`).join(','),!!w.soak,w.base,w.arranged,w.paper,w.ribbon,w.card,w.banner,w.cover,(t.asked||[]).length].join('|');
    if(ui.flSig!==sig&&(ui.flSig==null||follow)){
      ui.flSig=sig;
      const tab=tabOf(pending(g.steps)?.tab||(ui.tab||(w.arranged?'design':'cooler')));
      if(tab!==ui.tab){ui.tab=tab;g=taskGuide(t,x);}
    }
    if(ui.tab==='prep')ui.tab='cooler';
    const S=g.steps,done=S.filter(s=>s.ok===true).length;
    const tabs=[['cooler','🧊','Chọn hoa'],['design','💐','Cắm & gói'],['card','💌',deliver(t)?'Thiệp & giao':'Thiệp']];
    const onBench=w.stems.length,tabDone=k=>{const ss=S.filter(v=>tabOf(v.tab)===k);return ss.length>0&&ss.every(v=>v.ok===true);};
    const badge=k=>k==='cooler'&&soaking(t)?'<em class="due" aria-label="đang ngâm">⏱</em>':tabDone(k)?'<em class="ok" aria-label="xong">✓</em>':k==='cooler'&&onBench?`<em aria-label="${onBench} cành">${onBench}</em>`:'';
    const tabBar=`<div class="asm-tabs" role="tablist" aria-label="Khu làm việc">${tabs.map(([k,e,l])=>`<button type="button" role="tab" class="asm-tab${ui.tab===k?' on':''}" data-action="car:tab" data-tab="${k}" aria-selected="${ui.tab===k}"><span>${e} ${l}</span>${badge(k)}</button>`).join('')}</div>`;
    const panel=plated(t)?''
      :({cooler:coolerPanel,design:designPanel,card:cardPanel}[ui.tab]?.(t,x)||'');
    const dump=x.confirmCmd('🗑️ Bỏ bó, làm lại','fl_dump',{task:t.id},'Bỏ toàn bộ hoa và vật liệu đang dùng? Giá trị ghi hao hụt.','danger small',plated(t)||(!w.stems.length&&!w.base)||soaking(t));
    const side=`<div class="fl-side"><div class="fl-look">${stage(t,x)}<div class="fl-look-txt"><p class="fl-status" aria-live="polite">${x.esc(status(t,x))}</p>${pieceChips(t)}</div></div>
      ${plated(t)?'':cardPreview(t,x)+valueMeter(t,x)}
      ${S.length?`<div class="fk-wide-only"><p class="fl-brief-cap">Các bước làm</p>${checklist(x,S,'Các bước làm')}</div>`:''}
      ${S.length?`<details class="fl-check fl-narrow-only"${ui.flCheck?' open':''}><summary data-action="car:check">📋 Các bước làm · ${done}/${S.length} xong</summary>${checklist(x,S,'Các bước làm')}</details>`:''}</div>`;
    const tools=`<p class="row wrap fl-tools">${dump} ${x.button('📦 Kho & nhập hoa','inventory',{},'ghost small')} ${priceLink(x)}</p>`;
    // One bottom button (phone and wide): it does the next step, or the hand-off once nothing is left.
    // Right above it, what is on the bench now, so the result of each tap shows next to the button.
    const n=pending(S),heads=w.stems.slice(0,14).map(s=>glyph(x,s.i)).join('')+(w.stems.length>14?`<small>+${w.stems.length-14}</small>`:'');
    const now=`<div class="fl-bar-now">${heads?`<span class="fl-bar-stems" aria-hidden="true">${heads}</span>`:''}${nextLine(x,n,g.final?.ready!==false?'Đủ rồi · trao cho khách':'')}<b class="fl-bar-n">${done}/${S.length}</b></div>`;
    const bar=`<div class="fk-bar fl-bar">${now}${ui.flBusy?stepCta(x,[BUSY],g.final):stepCta(x,S,g.final)}</div>`;
    // Shop care (water, pre-orders) waits below the order: the order on the bench comes first.
    return `<div class="career-job fl food">${top(g)}${extras(x)}${ticket(t,x,g.K)}${pin(t,x,g.K,tabBar,n||finalStep(g.final))}<div class="workbench"><section class="wb-main" role="tabpanel">${panel}${tools}</section><aside class="wb-side">${side}</aside></div>${careFold(x)}${bar}</div>`;
  },
  actions:{
    ...asmActions,
    async tab(data,el,x){x.ui.tab=data.tab;x.render();},
    async slot(data,el,x){x.ui.slot=data.slot;x.render();},
    async check(data,el,x){x.ui.flCheck=!x.ui.flCheck;},
    async busy(){/* a sequence is still running: nothing to add */},
    /** Commands that go together, one after the other; stops at the first refusal. */
    async seq(data,el,x){let list=[];try{list=JSON.parse(data.seq||'[]');}catch{/* bad markup: nothing to do */}await run(x,list);},
    /** Learning orders: one tap picks exactly the stems the order needs ("id:n,id:n"). */
    async fill(data,el,x){
      const list=[];
      // One command per flower (fl_pick n): one beat of the day for each kind, not one per stem.
      for(const part of String(data.items||'').split(',')){const [item,n]=part.split(':');const k=Math.min(10,Number(n)||0);if(k)list.push(['fl_pick',{task:data.task,item,n:k}]);}
      await run(x,list);
    },
    /** Soak / foam: wait until the server's clock says it is time, then do it (the label counts down). */
    async wait(data,el,x){
      const key=`${data.task}:${data.cmd}`;
      if(x.ui.flWait===key)return;
      x.ui.flWait=key;
      try{
        const ms=(Number(data.at)-x.now())*1000+300;
        if(ms>0){x.toast(data.cmd==='fl_lift'?`Chờ thêm ${Math.ceil(ms/1000)} giây, đủ nước là tự nhấc ra.`:`Chờ thêm ${Math.ceil(ms/1000)} giây, mút chìm là tự cắm.`);await new Promise(r=>setTimeout(r,ms));}
        const w=(x.api.state?.careers?.florist?.tasks||[]).find(v=>v.id===data.task)?.work;
        if(!w||(data.cmd==='fl_lift'&&!w.soak)||(data.cmd==='fl_arrange'&&w.arranged))return;
        if(await x.send(data.cmd,{task:data.task})&&data.then)await x.send(data.then,{task:data.task});
      }finally{x.ui.flWait=null;}
    },
    async cardtpl(data,el,x){x.ui.cardText=null;await x.send('fl_card',{task:data.task,text:data.text});},
    async bannertpl(data,el,x){x.ui.bannerText=data.text;await x.send('fl_banner',{task:data.task,text:data.text});},
    /** Hint / row on another tab: open that tab, then glow the control. */
    async goto(data,el,x){
      x.ui.tab=data.tab;x.render();
      requestAnimationFrame(()=>{const root=document.querySelector('#sheet[open]')||document;highlight([...root.querySelectorAll(data.sel)].find(e=>e.offsetParent!==null)||root.querySelector(data.sel));});
    },
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
    pinTop(root);
    // Countdown in the "wait, then lift / arrange" button and hint (the hint lives in the sheet header).
    (root.closest('dialog')||root).querySelectorAll('[data-fl-count]').forEach(el=>{
      const left=Math.max(0,Math.ceil(Number(el.dataset.at)-x.now())),text=left?`còn ${left} giây`:'xong!';
      if(el.textContent!==text)el.textContent=text;
    });
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
  // "Ngày mai" first: bookings due tomorrow, the cooler's water, flowers to use up, what is coming; the day folded.
  summary(data,x){
    const [mai,rest]=splitMai(data?.care);
    const night=rest.length?`<article class="card space-top fl-night"><h4>🌙 Qua đêm ở tiệm</h4><ul>${rest.map(l=>`<li>${x.esc(l)}</li>`).join('')}</ul></article>`:'';
    return shopSummary(data,x,{emoji:'💐',lines:mai.map(l=>x.esc(l)),extra:night});
  },
  dock:[['inventory','box','Kho','Nhập & đếm hoa'],['prices','book','Bảng giá','Giá từng loại hoa']],
};
