/** Tiệm nail của chị Diệp — a little nail shop on the street (server: game/careers/nail.py).
 * The morning (lamp test, the weak bulb, the sterilizer, the stock shelf), looking at the nails, a fresh
 * file set, taking old polish off (wipe, file + soak in foil, or pry), shape and length, cuticles,
 * gel layers under the lamp (the cure times are on a lookup card on the table), art before the top,
 * the sticky layer, regular polish drying under the fan, and cash through the shared till.
 * The server decides everything; one tap sends one command. Hints say what comes next, never the answer. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {cashPanel,changeStep,changePayload,tillActions} from './till.js';
import {data,cc,lower,act,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions} from './street_kit.js';

const COL=(x,k)=>(cc(x).colours||[]).find(c=>c.id===k)||{id:k,name:k,emoji:'💅',hex:'#ccc'};
const SHAPE=(x,k)=>(cc(x).shapes||{})[k]||k;
const LEN=(x,k)=>(cc(x).lengths||{})[k]||k;
const SVC=(x,k)=>(cc(x).services||{})[k]||k;
const LAMP=(x,k)=>(cc(x).lamps||{})[k]||k;
const ORDER=['ngan','vua','dai'];
const stock=(x,k)=>Number(data(x).stock?.[k]||0);
const opened=(x,k)=>Number(data(x).open?.[k]||0);
const have=(x,k)=>opened(x,k)>0||stock(x,k)>0;
const LAYER={base:'Lớp base',color:'Lớp màu',top:'Lớp top',art:'Trang trí'};
const SECS=x=>cc(x).cure_secs||[30,60,90,120];

/** A button that cannot be used yet stays visible, disabled, with the reason under it. */
function btn(x,label,cmd,payload,cls,why){
  return `<span class="nl-b">${x.cmd(label,cmd,payload,cls,!!why)}${why?`<small class="nl-why">${x.esc(why)}</small>`:''}</span>`;
}
const pick=(x,key,val,label,cls='',why='')=>`<span class="nl-b">${act(x,label,'pick',{key,val},`small ${x.ui[key]===val?'primary':'ghost'} ${cls}`,` aria-pressed="${x.ui[key]===val}"${why?' disabled':''}`)}${why?`<small class="nl-why">${x.esc(why)}</small>`:''}</span>`;

/* ------------------------------------------------------------ the client and her nails */
function svcLine(x,n){
  return (n.svc||[]).map(s=>(s==='son_gel'||s==='son_thuong')&&n.colour?`${SVC(x,s)} ${lower(COL(x,n.colour).name)}`:SVC(x,s)).join(' · ');
}
function ticket(t,x){
  if(!t.known)return askCard(x,t,'👂 Hỏi khách muốn làm gì');
  const n=t.needs||{};
  const tags=[n.rush?'<span class="tag amber">⏰ Đang vội</span>':'',n.check?'<span class="tag">🧐 Soi từng móng</span>':''].join('');
  const body=`<p class="nl-want"><b>${x.esc(svcLine(x,n))}</b><br><small>Dáng ${x.esc(lower(SHAPE(x,n.shape)))}, móng ${x.esc(LEN(x,n.length))}</small></p>
    ${n.photo?`<p class="small nl-photo">🖼️ ${x.esc(n.photo)}</p>`:''}${n.note?`<p class="muted small">“${x.esc(n.note)}”</p>`:''}`;
  return person(x,t,body,tags?`<span class="nl-tags">${tags}</span>`:'');
}
const NAIL={ok:'Móng chắc, hồng hào, da viền lành.',broken:'Móng ngón giữa nứt ngang.',fungus:'Móng trỏ vàng đục, dày, sần, tách khỏi nền móng.',infected:'Khóe móng ngón cái sưng đỏ, có mủ.'};
const OLD={none:'Không có sơn cũ.',thuong:'Còn sơn thường cũ.',gel:'Đang có lớp gel cũ.'};
function lookCard(t,x){
  if(!t.cond)return `<section class="card nl-look"><h4>🔍 Bàn tay khách</h4><p class="small muted">Khách đặt tay lên gối kê. Nhìn kỹ trước khi làm.</p>${x.cmd('🔍 Xem móng khách','nl_inspect',{task:t.id},'primary nl-inspect')}</section>`;
  const c=t.cond,warn=c.nail==='fungus'||c.nail==='infected';
  const no=pane(x,`nl-no-${t.id}`,'<span>🙏 Không làm hôm nay</span><small>nói thật với khách</small>',
    `<div class="nl-row">${x.confirmCmd('🩺 Móng đang bệnh: khuyên đi khám','nl_decline',{task:t.id,why:'health'},'Nói với khách là hôm nay tiệm không làm bộ móng này, khuyên đi khám?','small')}
      ${x.confirmCmd('📦 Tiệm hết đồ: hẹn hôm khác','nl_decline',{task:t.id,why:'stock'},'Nói với khách là tiệm hết đồ cho bộ này, hẹn hôm khác?','small ghost')}</div>`,false,'nl-no');
  return `<section class="card nl-look ${warn?'warn':''}"><h4>🔍 Bàn tay khách</h4><ul class="nl-facts"><li>${x.esc(NAIL[c.nail]||'')}</li><li>${x.esc(OLD[c.old]||'')}</li><li>Móng thật dài ${x.esc(LEN(x,c.nat))}.</li></ul>${no}</section>`;
}

/* ------------------------------------------------------------ the lamp, the tools */
function lampBar(t,x){
  const d=data(x),l=d.lamp||{},off=d.power==='off';
  const state=!l.tested?'chưa thử':l.weak?'bóng yếu':'sáng tốt';
  const tl=d.tools||{},tools=tl.clean?'♨️ dụng cụ vừa hấp':tl.by===t?.id?'🧰 dụng cụ đang dùng cho khách này':'🧰 dụng cụ đã dùng';
  const sw=['led','uv'].map(k=>pick2(x,k,l.kind===k,off?'Cúp điện':'')).join('');
  return `<div class="nl-lamp ${off?'off':''}" role="group" aria-label="Đèn hơ gel"><span class="nl-lamp-now"><span aria-hidden="true">🪔</span><b>${x.esc(LAMP(x,l.kind))}</b><small>${off?'🔌 cúp điện':x.esc(state)}</small></span>
    ${l.kind==='pin'?'':sw}<span class="nl-tools"><small>${x.esc(tools)}</small>${x.cmd('♨️ Hấp dụng cụ','nl_sterilize',{},'small ghost')}</span></div>`;
}
function pick2(x,k,on,why){
  return `<span class="nl-b">${x.cmd(k==='led'?'Đèn LED':'Đèn UV cũ','nl_lamp',{kind:k},`small ${on?'primary':'ghost'}`,!!why||on)}</span>`;
}
function cureCard(x){
  const cu=cc(x).cure||{},rows=Object.keys(cu).map(k=>`<tr><th>${x.esc(LAMP(x,k))}</th>${['base','color','top','art'].map(l=>`<td>${cu[k][l]} giây</td>`).join('')}</tr>`).join('');
  return pane(x,'nl-card',`<span>📋 Bảng giờ hơ đèn</span><small>dán trên bàn</small>`,
    `<table class="nl-card"><thead><tr><th></th><th>Base</th><th>Màu</th><th>Top</th><th>Vẽ</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="small muted">Bóng LED yếu: gấp đôi thời gian. Thử đèn mỗi sáng bằng một giọt gel. Sơn thường không hơ đèn, hong quạt cho khô.</p>`,false,'nl-cardpane');
}

/* ------------------------------------------------------------ prep: file, old polish, shape, cuticles */
function prepPanel(t,x){
  const c=t.cond||{},rm=t.rm||{},noOld=c.old==='none'?'Không có sơn cũ':'';
  const kit=btn(x,'🪵 Bóc bộ dũa mới','nl_kit',{task:t.id},'',t.file?'Đã bóc cho khách này':!have(x,'dua')?'Hết dũa':'');
  const soak=rm.wrap!=null?`<span class="nl-soak" data-nl-soak="${Number(rm.wrap)}" data-nl-full="${Number(cc(x).soak_s||20)}">🥡 Đang ủ</span>`:'';
  const old=`<div class="nl-row">${btn(x,'🧪 Lau acetone','nl_remove',{task:t.id,how:'wipe'},'small',noOld||(rm.off||rm.wiped?'Đã sạch sơn cũ':''))}
    ${btn(x,'🪵 Dũa mặt gel','nl_remove',{task:t.id,how:'file'},'small',noOld||(rm.off?'Đã tháo xong':''))}
    ${btn(x,'🥡 Đắp bông, quấn giấy bạc','nl_remove',{task:t.id,how:'wrap'},'small',noOld||(rm.off?'Đã tháo xong':rm.wrap!=null?'Đang ủ':''))}
    ${btn(x,'✋ Gỡ giấy bạc','nl_remove',{task:t.id,how:'unwrap'},'small',rm.wrap==null?'Chưa quấn giấy bạc':'')}
    ${btn(x,'🔪 Cạy gel bằng sủi','nl_remove',{task:t.id,how:'pry'},'small ghost',c.old!=='gel'||rm.off?'Không có gel để cạy':'')}</div>${soak}`;
  const fix=btn(x,'🩹 Đắp gel gia cố móng gãy','nl_fix',{task:t.id},'small',!t.cond?'Xem móng trước':c.nail!=='broken'?'Không có móng gãy':t.fixed?'Đã sửa':'');
  const tip=btn(x,'💅 Nối móng (úp tips)','nl_tip',{task:t.id},'small',t.tip?'Đã nối':(t.coats||[]).length?'Phải nối trước khi sơn':!have(x,'tips')?'Hết tips':'');
  const now=t.tip?'dai':t.len||c.nat||'dai';
  const shapes=Object.keys(cc(x).shapes||{}).map(k=>pick(x,'shape',k,x.esc(SHAPE(x,k)))).join('');
  const lens=ORDER.map(k=>pick(x,'len',k,x.esc(LEN(x,k)),'',t.cond&&ORDER.indexOf(k)>ORDER.indexOf(now)?'Muốn dài hơn phải nối':'')).join('');
  const ready=x.ui.shape&&x.ui.len;
  const file=btn(x,'🪵 Dũa','nl_shape',{task:t.id,shape:x.ui.shape||'',length:x.ui.len||''},'primary',ready?'':'Chọn dáng và độ dài');
  const cuts=Object.entries(cc(x).cuts||{}).map(([k,v])=>x.cmd(x.esc(v),'nl_cuticle',{task:t.id,how:k},`small ${t.cut===k?'primary':'ghost'}`)).join('');
  const blood=t.bleed?`<p class="notice small nl-bad">🩸 Khóe móng rớm máu.</p><div class="nl-row">${btn(x,'🩹 Ép bông cầm máu','nl_staunch',{task:t.id},'small primary',t.staunch?'Đã cầm máu':'')}
    ${t.told==null?`${x.cmd('🙏 Nói thật với khách','nl_tell',{task:t.id,honest:true},'small')}${x.cmd('🤐 “Trầy chút xíu thôi”','nl_tell',{task:t.id,honest:false},'small ghost')}`:''}</div>`:'';
  return `<section class="card nl-prep"><h4>🪵 Chuẩn bị móng</h4><div class="nl-row">${kit}</div>
    <h4 class="section-title">Tháo sơn cũ</h4>${old}
    <h4 class="section-title">Sửa, nối móng</h4><div class="nl-row">${fix}${tip}</div>
    <h4 class="section-title">Dáng và độ dài ${t.shape?`<small>đang: ${x.esc(lower(SHAPE(x,t.shape)))}, ${x.esc(LEN(x,t.len))}</small>`:''}</h4><div class="nl-row">${shapes}</div><div class="nl-row">${lens}</div><div class="nl-row">${file}</div>
    <h4 class="section-title">Da viền móng</h4><div class="nl-row">${cuts}</div>${blood}</section>`;
}

/* ------------------------------------------------------------ polish, the lamp, art, finishing */
function coatList(t,x){
  const coats=t.coats||[];
  if(!coats.length)return '<p class="small muted">Chưa quét lớp nào.</p>';
  return `<ol class="nl-coats">${coats.map(c=>{const col=c.l==='color'?COL(x,c.k):null;
    const what=c.l==='art'?(cc(x).art||{})[c.k]||c.k:col?col.name:'';
    const st=c.p==='thuong'?'sơn thường':c.cure==null?'chưa hơ':`đã hơ ${c.cure} giây`;
    return `<li class="${c.p==='gel'&&c.cure==null?'wet':''}">${col?`<i class="nl-dot" style="background:${x.esc(col.hex)}"></i>`:'<i class="nl-dot clear"></i>'}<b>${x.esc(LAYER[c.l]||c.l)}</b>${what?`<span>${x.esc(what)}</span>`:''}<small>${c.th==='day'?'quét dày · ':''}${x.esc(st)}${c.skin?' · ⚠️ lem ra da':''}</small></li>`;}).join('')}</ol>`;
}
function polishPanel(t,x){
  const p=x.ui.p,th=x.ui.th||'mong',coats=t.coats||[],reg=cc(x).regular||[];
  const kind=`${pick(x,'p','gel','🪔 Sơn gel')}${pick(x,'p','thuong','💅 Sơn thường')}`;
  const thick=`${pick(x,'th','mong','Quét mỏng')}${pick(x,'th','day','Quét dày')}`;
  const cols=(cc(x).colours||[]).map(c=>{const item=p==='thuong'?`son_${c.id}`:`gel_${c.id}`,no=p==='thuong'&&!reg.includes(c.id);
    const out=!no&&p&&!have(x,item);
    const small=no?'không có sơn thường':out?'hết':p?(opened(x,item)?'lọ đang dùng':`${stock(x,item)} lọ`):'';
    return `<button type="button" class="tile sk-tile nl-col ${x.ui.colour===c.id?'selected':''}" data-action="car:pick" data-key="colour" data-val="${x.esc(c.id)}" aria-pressed="${x.ui.colour===c.id}"${no||out?' disabled':''}><i class="nl-swatch" style="background:${x.esc(c.hex)}"></i><b>${x.esc(c.name)}</b><small>${small}</small></button>`;}).join('');
  const pay=layer=>({task:t.id,layer,p:p||'',thick:th,...(layer==='color'?{colour:x.ui.colour||''}:{})});
  const whyP=p?'':'Chọn gel hay sơn thường';
  const layers=`<div class="nl-row">${btn(x,'🖌️ Quét lớp base','nl_coat',pay('base'),'small',whyP)}${btn(x,'🎨 Quét lớp màu','nl_coat',pay('color'),'small',whyP||(!x.ui.colour?'Chọn màu':''))}${btn(x,'💎 Quét lớp top','nl_coat',pay('top'),'small',whyP)}</div>`;
  const wetSkin=coats.some(c=>c.skin&&(c.p==='thuong'||c.cure==null));
  const pend=coats.some(c=>c.p==='gel'&&c.cure==null);
  const cure=SECS(x).map(s=>x.cmd(`${s} giây`,'nl_cure',{task:t.id,sec:s},'small',!pend)).join('');
  const hasGel=coats.some(c=>c.l==='color'&&c.p==='gel'),hasArt=coats.some(c=>c.l==='art');
  const art=Object.entries(cc(x).art||{}).map(([k,v])=>btn(x,x.esc(v),'nl_art',{task:t.id,art:k},'small ghost',hasArt?'Đã trang trí':!hasGel?'Làm trên nền gel màu':'')).join('');
  const top=[...coats].reverse().find(c=>c.l==='top'&&c.p==='gel');
  const fin=`<div class="nl-row">${btn(x,'🧴 Lau lớp dính','nl_wipe',{task:t.id},'small',t.wiped?'Đã lau':!top||top.cure==null?'Chưa có lớp top gel đã hơ':'')}
    ${btn(x,'🌬️ Hong quạt cho khô','nl_dry',{task:t.id},'small',t.dried?'Đã hong':!coats.some(c=>c.p==='thuong')?'Chưa có sơn thường':'')}
    ${btn(x,'💧 Dầu dưỡng viền móng','nl_oil',{task:t.id},'small',t.oil?'Đã thoa':'')}
    ${btn(x,'🫧 Chăm da tay','nl_care',{task:t.id},'small',t.care?'Đã chăm':'')}</div>`;
  return `<section class="card nl-polish"><h4>🎨 Sơn</h4><div class="nl-row">${kind}</div><div class="nl-row">${thick}</div>
    <div class="tile-grid nl-cols">${cols}</div>${layers}${coatList(t,x)}
    <div class="nl-row">${btn(x,'🧹 Lau chỗ sơn lem','nl_clean',{task:t.id},'small ghost',wetSkin?'':'Không có chỗ lem còn ướt')}</div>
    <h4 class="section-title">🪔 Hơ đèn</h4><div class="nl-row nl-cure">${cure}</div>${pend?'':'<small class="nl-why">Không có lớp gel nào chờ hơ</small>'}${cureCard(x)}
    <h4 class="section-title">🌸 Vẽ, đính đá</h4><div class="nl-row">${art}</div>
    <h4 class="section-title">✨ Hoàn thiện</h4>${fin}</section>`;
}

/* ------------------------------------------------------------ the morning */
function setupPanel(t,x){
  const d=data(x),l=d.lamp||{},tl=d.tools||{},sh=d.shop||{};
  const lamp=!l.tested?x.cmd('💡 Thử đèn bằng một giọt gel','nl_lamp_test',{},'primary'):l.weak&&l.kind==='led'?
    `<p class="small nl-bad">💡 Bóng LED yếu: giọt gel vẫn nhão.</p><div class="nl-row">${btn(x,'🔧 Thay bóng LED dự phòng','nl_bulb',{},'primary',stock(x,'bong_led')?'':'Hết bóng dự phòng')}${btn(x,'Dùng đèn UV cũ','nl_lamp',{kind:'uv'},'',d.power==='off'?'Cúp điện':'')}</div>`
    :`<span class="tag green">✓ ${x.esc(LAMP(x,l.kind))} sáng tốt</span>`;
  const tools=tl.clean?'<span class="tag green">✓ Dụng cụ đã hấp</span>':x.cmd('♨️ Hấp dụng cụ','nl_sterilize',{},'primary');
  const shelf=sh.stocked?'<span class="tag green">✓ Đã coi kệ hàng</span>':x.cmd('📋 Coi kệ hàng','nl_stock',{},'primary');
  return `<section class="card nl-setup"><h4>Đèn hơ gel</h4>${lamp}<h4 class="section-title">Tủ hấp dụng cụ</h4>${tools}<h4 class="section-title">Kệ hàng</h4>${shelf}
    <p class="small muted">${x.esc(t.needs?.note||'')}</p>${cureCard(x)}</section>`;
}
function setupSteps(t,x){
  const d=data(x),l=d.lamp||{},rows=[];
  rows.push({ok:l.tested?true:null,label:'Thử đèn hơ gel',go:{cmd:'nl_lamp_test',payload:{},label:'💡 Thử đèn'}});
  if(l.tested&&l.weak&&l.kind==='led')rows.push({ok:false,label:'Bóng LED yếu',go:stock(x,'bong_led')?{cmd:'nl_bulb',payload:{},label:'🔧 Thay bóng LED'}:{cmd:'nl_lamp',payload:{kind:'uv'},label:'Dùng đèn UV cũ'}});
  rows.push({ok:d.tools?.clean?true:null,label:'Hấp dụng cụ',go:{cmd:'nl_sterilize',payload:{},label:'♨️ Hấp dụng cụ'}});
  rows.push({ok:d.shop?.stocked?true:null,label:'Coi kệ hàng',go:{cmd:'nl_stock',payload:{},label:'📋 Coi kệ hàng'}});
  return rows;
}

/* ------------------------------------------------------------ the guide: what comes next, never the answer */
function serveSteps(t,x){
  const d=data(x),n=t.needs||{},c=t.cond,coats=t.coats||[],rows=[];
  if(!d.shop?.open)rows.push({ok:null,label:'Mở tiệm xong mới làm',go:null});
  rows.push({ok:c?true:null,label:'Xem móng khách',go:{cmd:'nl_inspect',payload:{task:t.id},label:'🔍 Xem móng khách'}});
  if(c&&c.old!=='none'){const rm=t.rm||{};rows.push({ok:rm.off||rm.wiped?true:null,label:'Tháo sơn cũ',note:rm.wrap!=null?'đang ủ':''});}
  rows.push({ok:t.shape?true:null,label:'Dũa dáng, độ dài'});
  rows.push({ok:t.cut?true:null,label:'Làm da viền móng'});
  if(t.bleed&&!t.staunch)rows.push({ok:false,label:'Cầm máu cho khách',go:{cmd:'nl_staunch',payload:{task:t.id},label:'🩹 Ép bông cầm máu'}});
  if(n.polish){
    rows.push({ok:coats.some(k=>k.l==='color')?true:null,label:'Sơn màu khách chọn'});
    if(coats.some(k=>k.p==='gel'&&k.cure==null))rows.push({ok:null,label:'Còn lớp gel chưa hơ đèn'});
  }
  return rows;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện ở tiệm',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'nl_intro',payload:{},label:'💅 Vào việc thôi!'}}],final:null};
  if(t.kind==='setup'){const steps=setupSteps(t,x);return {steps,final:{label:'💅 MỞ TIỆM',go:finalGo(steps,'nl_open',{task:t.id}),ready:true}};}
  if(!t.known)return {steps:[{ok:null,label:'Hỏi khách',go:{cmd:'ask',payload:{task:t.id},label:'👂 Hỏi khách muốn làm gì'}}],final:null,pulse:'.sk-ask'};
  if(t.stage==='pay'){const s=changeStep(x,t.id,t.cash),steps=s?[s]:[];return {steps,final:{label:'💵 ĐƯA TIỀN THỐI',go:finalGo(steps,'nl_pay',{task:t.id,...changePayload(x,t.id,t.cash)}),ready:true}};}
  const steps=serveSteps(t,x),worked=(t.coats||[]).length||t.shape||t.care;
  return {steps,final:{label:'💅 GIAO MÓNG',go:finalGo(steps,'nl_done',{task:t.id,confirm:true}),ready:!!worked,why:'làm móng trước đã'}};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});

/* ------------------------------------------------------------ idle: the table between clients */
function shopView(x){
  const d=data(x),cols=(cc(x).colours||[]).map(c=>`<li><i class="nl-swatch" style="background:${x.esc(c.hex)}"></i><span>${x.esc(c.name)}</span><small>${opened(x,`gel_${c.id}`)?'đang dùng · ':''}${stock(x,`gel_${c.id}`)} lọ gel</small></li>`).join('');
  return `<section class="card nl-shop"><h4>💅 Kệ gel màu</h4><ul class="nl-shelf">${cols}</ul><p class="small muted">🪵 ${stock(x,'dua')} bộ dũa · 🥡 ${stock(x,'foil')} bộ giấy bạc · 💅 ${stock(x,'tips')} bộ tips · 💡 ${stock(x,'bong_led')} bóng LED dự phòng</p>${cureCard(x)}</section>`;
}

export default {
  id:'nail',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='setup'?'Thử đèn, mở tiệm':!t.known?'Hỏi khách muốn làm gì':'Làm móng cho khách';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'nl_intro','💅')}${deskCard(x,'nl_desk','Chuyện ở tiệm')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk nl">${hint}${top}${bottom(x,g)}</div>`;
    if(x.ui.task!==t.id){x.ui.task=t.id;x.ui.shape=x.ui.len=x.ui.p=x.ui.colour=undefined;x.ui.th='mong';}
    let main='',side='';
    if(t.kind==='setup'){main=setupPanel(t,x);side=stepRows(x,g.steps,'Việc mở tiệm');}
    else if(!t.known)main='';
    else if(t.stage==='pay')main=cashPanel(x,t.id,t.cash);
    else{main=`${lookCard(t,x)}${t.cond?`${prepPanel(t,x)}${polishPanel(t,x)}`:''}`;side=stepRows(x,g.steps,'Bộ móng của khách');}
    const clock=t.needs?.rush&&t.clock!=null&&t.stage==='prep'?`<div class="nl-clock" role="timer" aria-live="off">⏱️ Đã làm <b data-nl-clock="${Number(t.clock)}">0:00</b></div>`:'';
    const head=t.kind==='setup'?dayBar(x):`${ticket(t,x)}${dayBar(x)}${t.known&&t.stage==='prep'?lampBar(t,x):''}${clock}`;
    return `<div class="career-job sk nl">${hint}${top}${head}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),top=`${introCard(x,'nl_intro','💅')}${deskCard(x,'nl_desk','Chuyện ở tiệm')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện ở tiệm',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'nl_intro',payload:{},label:'💅 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk nl">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk nl">${top}${dayBar(x)}${shopView(x)}</div>`;
  },
  tick(root,x){
    keepBarAboveFooter(root);
    const el=root.querySelector('[data-nl-clock]');
    if(el){const s=Math.max(0,Math.floor(x.now()-Number(el.dataset.nlClock))),v=`${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;if(el.textContent!==v)el.textContent=v;}
    const sk=root.querySelector('[data-nl-soak]');
    if(sk){const m=Math.floor(Math.max(0,x.now()-Number(sk.dataset.nlSoak))*10/Number(sk.dataset.nlFull||20)),v=`🥡 Đã ủ ${m} phút`;if(sk.textContent!==v)sk.textContent=v;}
  },
  actions:{...tillActions,...kitActions,
    async pick(d,el,x){x.ui[d.key]=d.val;x.render();},
  },
  dock:[['inventory','box','Kho tiệm nail','Nhập gel, sơn, dũa, giấy bạc…']],
};
