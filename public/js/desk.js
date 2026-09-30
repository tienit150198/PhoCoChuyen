/* Paperwork desks: pharmacy counter, bookkeeping desk, support station.
   Render-only: every fact and grade comes from the server (game/desk.py).
   Phone first: one quote, the papers, a short rulebook, and one row of stamps. */
import {icon,portrait,escapeHTML as esc} from './icons.js';
import {asset} from './assets.js';
import {nextHint} from './v4/guide.js';

if(typeof document!=='undefined'&&!document.querySelector('link[data-desk-css]')){
  const link=document.createElement('link');link.rel='stylesheet';link.href=asset('/css/desk.css');link.dataset.deskCss='';document.head.append(link);
}

const local={sel:null,task:null,tally:{}};
const DONE=['completed','referred','cancelled'];
const COLOR={do:'#d9463b',xanh:'#2f7fd1',tim:'#8a4fd0'};
const CLINIC={hp:'PK Hạnh Phúc',ak:'PK An Khang',mh:'PK Mây Hồng'};
const MOOD={new:'Khách mới',angry:'Đang bực',polite:'Lịch sự',suspect:'Cần xác minh',public:'Công khai',threat:'Căng thẳng'};
const GRADE={perfect:['Chuẩn','good'],good:['Đạt','warn'],wrong:['Chưa đúng','bad']};
const attrs=o=>Object.entries(o).map(([k,v])=>` data-${k}="${esc(String(v))}"`).join('');
const act=(label,action,data={},cls='')=>`<button type="button" class="btn ${cls}" data-action="${action}"${attrs(data)}>${label}</button>`;
const cmdBtn=(label,command,payload={},cls='',disabled=false)=>`<button type="button" class="btn ${cls}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${label}</button>`;
const person=(api,id)=>api.content.npcs.find(n=>n.id===id)||{display_name:'Khách',role:''};
const room=api=>api.state.careers[api.state.current];

/** Visual clinic stamp: shape-colour-petals, e.g. 'tron-do-5'. */
export function stampArt(mark,size=34){
  if(!mark)return'';const [shape,color,petals]=mark.split('-');
  return `<span class="dk-stamp-art ${esc(shape)}" style="--stamp:${COLOR[color]||'#777'};--size:${size}px" aria-hidden="true"><b>${'✿'.repeat(Math.min(6,Number(petals)||0))}</b></span>`;
}

export function deskNext(t,api){
  if(t.career==='customer_care'&&t.reply==null){const left=t.due_turn==null?null:t.due_turn-room(api).turn;return left==null?'Trả lời khách trước':left>=0?`Trả lời khách · còn ${left} nhịp`:'Trả lời khách · đã trễ hạn';}
  if(!t.known)return'Nhận giấy tờ của khách';
  if(Object.keys(t.pending||{}).length)return'Chờ kết quả kiểm tra';
  return'Soát từng dòng rồi đóng dấu';
}

function patience(t,api){const v=room(api).life.mode==='calm'?100:(t.patience??100);return `<div class="dk-patience ${v<50?'low':''}" title="Kiên nhẫn"><i style="width:${v}%"></i><small>${v}%</small></div>`;}

function header(t,api){
  const n=person(api,t.npc),line=t.known?t.request:t.opening;
  const mood=t.career==='customer_care'?`<span class="dk-mood ${esc(t.mood)}">${MOOD[t.mood]||''}</span>`:'';
  return `<header class="dk-head">${portrait(n,44)}<div class="dk-who"><strong>${esc(n.display_name)}</strong> ${mood}<small>${esc(n.role||'')}</small></div>${patience(t,api)}${act(icon('chat',16),'chat',{npc:t.npc,task:t.id},'ghost icon-only dk-chat')}</header><p class="dk-quote">${line.includes('“')?esc(line):`“${esc(line)}”`}</p>`;
}

function queueStrip(t,api){
  const c=room(api),open=c.tasks.filter(x=>!DONE.includes(x.status)&&x.desk&&x.career==='customer_care');
  if(open.length<2)return'';
  return `<nav class="dk-queue" aria-label="Hàng đợi tin nhắn">${open.map(x=>{const left=x.due_turn==null?null:x.due_turn-c.turn,late=x.reply==null&&left!=null&&left<0,urgent=x.reply==null&&left!=null&&left>=0&&left<=3;
    const tag=x.reply!=null?'✓ đã trả lời':left==null?'chưa trả lời':late?'trễ hạn':`${left} nhịp`;
    return `<button type="button" class="dk-ticket ${x.id===t.id?'on':''} ${late?'late':urgent?'urgent':''}" data-command="task_select" data-payload="${esc(JSON.stringify({task:x.id}))}"><b>${esc(person(api,x.npc).display_name)}</b><span>${esc(x.title)}</span><small>${tag}</small></button>`;}).join('')}</nav>`;
}

function replies(t,api){
  if(t.career!=='customer_care')return'';
  if(t.reply!=null)return `<div class="dk-thread">${(t.thread||[]).map(m=>`<p class="dk-bubble ${m.who}">${esc(m.text)}</p>`).join('')}</div>`;
  const left=t.due_turn==null?null:t.due_turn-room(api).turn;
  const timer=left==null?'<span class="dk-sla calm">Hôm nay chưa tính giờ</span>':left>=0?`<span class="dk-sla ${left<=3?'urgent':''}">⏰ còn ${left} nhịp để trả lời</span>`:'<span class="dk-sla late">⏰ đã trễ hạn phản hồi</span>';
  return `<section class="dk-replies"><div class="dk-row-head"><h4>Trả lời đầu tiên</h4>${timer}</div>${t.replies.map(r=>cmdBtn(esc(r.text),'desk_reply',{task:t.id,reply:r.id},'dk-reply',!room(api).open)).join('')}</section>`;
}

function rulebook(t){
  const fresh=t.rules.filter(r=>r.new).length;
  const stamps=t.stamps?`<div class="dk-registry">${Object.entries(t.stamps).map(([k,m])=>`<span>${stampArt(m,26)}<small>${esc(CLINIC[k]||k)}</small></span>`).join('')}</div>`:'';
  return `<details class="dk-book"${fresh?' data-fresh':''}><summary>${icon('book',16)} Sổ quy định hôm nay <span class="dk-count">${t.rules.length}</span>${fresh?`<span class="dk-new">${fresh} MỚI</span>`:''}</summary>${t.bulletin?.length?`<ul class="dk-notices">${t.bulletin.map(n=>`<li>📰 ${esc(n)}</li>`).join('')}</ul>`:''}${stamps}<ol class="dk-rules">${t.rules.map(r=>`<li class="${r.new?'new':''}"><b>${esc(r.short)}</b>${r.new?' <span class="dk-new">MỚI</span>':''}<span>${esc(r.text)}</span></li>`).join('')}</ol></details>`;
}

function markOf(t,ref){const ms=(t.marks||[]).filter(m=>m.field===ref);return ms.find(m=>m.result==='found')||ms.find(m=>m.result==='partial')||ms[ms.length-1];}

function docCard(t,d,api){
  const rows=d.fields.map(f=>{const ref=d.id+'.'+f.id,m=markOf(t,ref),sel=local.task===t.id&&local.sel===ref;
    if(f.locked)return `<div class="dk-field locked"><span>${esc(f.label)}</span><em>🔒 cần kiểm</em></div>`;
    const stamp=m?`<span class="dk-mark ${m.result}">${m.result==='found'?'✔':m.result==='partial'?'?':'×'}</span>`:'';
    const art=f.mark?stampArt(f.mark,30):'';
    const chips=sel?`<div class="dk-chips" role="group" aria-label="Chọn quy định bị trái">${t.rules.map(r=>act(esc(r.short),'desk:flag',{task:t.id,field:ref,rule:r.id},'dk-chip'+(r.new?' fresh':''))).join('')}${act('Bỏ chọn','desk:unsel',{},'dk-chip ghost')}</div>`:'';
    return `<button type="button" class="dk-field ${sel?'sel':''} ${m?m.result:''}" data-action="desk:sel" data-field="${esc(ref)}" data-task="${esc(t.id)}" aria-pressed="${sel}"><span>${esc(f.label)}</span><strong>${art}${esc(f.value)}</strong>${stamp}</button>${chips}`;}).join('');
  return `<article class="dk-doc ${esc(d.kind)}"><h4>${d.icon} ${esc(d.title)}</h4>${rows}</article>`;
}

function checks(t,api){
  if(!t.checks.length)return'';const c=room(api);
  return `<section class="dk-checks"><h4>Kiểm tra thêm</h4><div class="dk-check-row">${t.checks.filter(k=>k.id!=='count').map(k=>{const done=t.verified.includes(k.id),wait=t.pending?.[k.id];
    if(done)return `<span class="dk-check done">${k.icon} ${esc(k.label)} ✓</span>`;
    if(wait!=null)return `<span class="dk-check wait">${k.icon} ${esc(k.label)} · ⏳ ${Math.max(0,wait-c.turn)} nhịp</span>${cmdBtn('Chờ một nhịp','advance',{},'ghost small')}`;
    return cmdBtn(`${k.icon} ${esc(k.label)}`,'desk_check',{task:t.id,check:k.id},'dk-check',!c.open);}).join('')}</div></section>`;
}

function drawer(t,api){
  if(!t.drawer)return'';
  const counted=t.verified.includes('count');
  const tally=local.tally[t.id]??={in:[],out:[]};
  const sum=t.drawer.filter(n=>tally.in.includes(n.id)).reduce((s,n)=>s+n.v,0);
  const notes=t.drawer.map(n=>{const state=tally.in.includes(n.id)?'in':tally.out.includes(n.id)?'out':'';
    return `<button type="button" class="dk-note v${n.v} ${state}" data-action="desk:note" data-task="${esc(t.id)}" data-note="${esc(n.id)}" aria-label="Tờ ${n.v} xu${n.thread?'':' không có sợi bạc'}"${counted?' disabled':''}><b>${n.v}</b>${n.thread?'<i>🧵</i>':'<i class="nothread">?</i>'}</button>`;}).join('');
  return `<section class="dk-drawer"><div class="dk-row-head"><h4>🧮 Đếm két</h4>${counted?'<span class="dk-sla calm">Đã đếm khớp ✓</span>':`<span class="dk-sum">Đang đếm: <b>${sum}</b> xu</span>`}</div>
    ${counted?'':'<p class="dk-hint">Chạm một lần: đếm vào. Chạm lần nữa: để riêng. Chạm lần ba: bỏ ra.</p>'}<div class="dk-notes">${notes}</div>
    ${counted?'':(t.miscounts||0)>=6?'<p class="small muted">Đếm lệch nhiều lần rồi. Bạn vẫn có thể đóng dấu theo những gì đã thấy.</p>':`<div class="dk-count-row">${cmdBtn(`Chốt số đếm: ${sum} xu`,'desk_count',{task:t.id,total:sum},'primary',!room(api).open)}${act('Đếm lại','desk:reset',{task:t.id},'ghost')}</div>`}</section>`;
}

function stamps(t,api){
  const open=room(api).open;
  return `<section class="dk-stamps"><h4>Đóng dấu quyết định</h4><div class="dk-stamp-grid">${t.verdicts.map(v=>act(`<span class="dk-stamp-ico">${v.icon}</span><span>${esc(v.label)}</span>`,'desk:decide',{task:t.id,verdict:v.id,label:v.label},'dk-stamp'+(open?'':' disabled'))).join('')}</div><p class="dk-hint">Đánh dấu nhầm làm khách sốt ruột.</p></section>`;
}

function progress(t){
  const marks=t.marks||[],found=marks.filter(m=>m.result==='found').length,wrong=marks.filter(m=>m.result==='wrong').length;
  if(!marks.length)return'';
  return `<p class="dk-progress">✔ ${found} chỗ sai đã chỉ ra${wrong?` · × ${wrong} lần đánh dấu nhầm`:''}</p>`;
}

/** Next steps at a desk (guide.js): answer, take the papers, run the extra checks, count the
 * till, read every line, stamp. Which line is wrong stays the player's call. */
function deskSteps(t,api){
  const c=room(api),rows=[];
  if(t.career==='customer_care'&&t.reply==null)rows.push({ok:null,label:'Chọn câu trả lời đầu tiên cho khách',go:{sel:'.dk-replies .dk-reply'}});
  if(!t.known){rows.push({ok:null,label:t.career==='customer_care'?'Mở hồ sơ đơn':'Nhận giấy tờ của khách',go:{cmd:'ask',payload:{task:t.id}},pulse:'.dk-start .dk-cta'});return rows;}
  for(const k of (t.checks||[]).filter(k=>k.id!=='count')){
    const done=t.verified.includes(k.id),wait=t.pending?.[k.id];
    rows.push({ok:done||null,label:`${k.icon} ${k.label}`,note:wait!=null?`⏳ ${Math.max(0,wait-c.turn)} nhịp`:'',
      go:done?null:wait!=null?{cmd:'advance',label:'⏳ Chờ kết quả một nhịp'}:{cmd:'desk_check',payload:{task:t.id,check:k.id},label:`${esc(k.icon)} ${esc(k.label)}`}});
  }
  if(t.drawer&&!t.verified.includes('count')&&(t.miscounts||0)<6)rows.push({ok:null,label:'Đếm két: chạm từng tờ rồi chốt số',go:{sel:'.dk-drawer .dk-note'}});
  const marks=t.marks||[];
  if(!marks.length)rows.push({ok:null,label:'Soát từng dòng: chạm dòng sai, chọn quy định nó trái',go:{sel:'.dk-docs .dk-field:not(.locked)'}});
  rows.push({ok:null,label:'Đóng dấu quyết định',go:{sel:'.dk-stamps .dk-stamp'}});
  return rows;
}

export function deskJob(t,ctx){
  const {api}=ctx;
  let body=nextHint({room:room(api)},deskSteps(t,api),{cta:false});
  if(t.career==='customer_care')body+=queueStrip(t,api)+replies(t,api);
  if(!t.known){
    body+=`<div class="dk-start">${cmdBtn('📥 '+(t.career==='customer_care'?'Mở hồ sơ đơn':'Nhận giấy tờ'),'ask',{task:t.id},'primary full dk-cta',!room(api).open)}</div>`;
  }else{
    body+=rulebook(t)+`<p class="dk-hint">Chạm vào dòng có vấn đề, rồi chọn quy định mà nó trái.</p><div class="dk-docs">${(t.docs||[]).map(d=>docCard(t,d,api)).join('')}</div>`+progress(t)+drawer(t,api)+checks(t,api)+stamps(t,api);
  }
  return `<div class="dk" data-career="${esc(t.career)}">${header(t,api)}${body}</div>`;
}

export function deskDone(t,ctx){
  if(!t.result)return '<div class="dk dk-done"><p class="dk-says">Hồ sơ này đã khép từ trước.</p></div>';
  const r=t.result,[label,kind]=GRADE[r.grade]||['Đã xong',''];
  const verdict=(t.verdicts||[]).find(v=>v.id===r.verdict);
  const money=[r.pay?`+${r.pay} xu thù lao`:'Không có thù lao',r.tip?`+${r.tip} xu khách gửi`:'',r.fine?`−${r.fine} xu phạt`:''].filter(Boolean).join(' · ');
  return `<div class="dk dk-done"><div class="dk-result ${kind}"><span class="dk-big-stamp">${esc(label)}</span><p class="dk-verdict">${verdict?verdict.icon+' '+esc(verdict.label):''}</p></div>
    <p class="dk-says">${esc(r.says||'')}</p>
    ${r.found?.length?`<div class="dk-list good"><h4>Bạn đã chỉ ra</h4><ul>${r.found.map(x=>`<li>✔ ${esc(x)}</li>`).join('')}</ul></div>`:''}
    ${r.missed?.length?`<div class="dk-list bad"><h4>Còn sót</h4><ul>${r.missed.map(x=>`<li>• ${esc(x)}</li>`).join('')}</ul></div>`:''}
    ${r.false_flags?`<p class="dk-hint">Đánh dấu nhầm ${r.false_flags} lần.</p>`:''}${r.breached?'<p class="dk-hint">Trả lời trễ hạn phản hồi.</p>':''}
    ${(r.lines||[]).map(l=>`<p class="dk-citation">${esc(l)}</p>`).join('')}
    <p class="dk-money">${esc(money)}</p></div>`;
}

/** 'desk:*' actions (client-only selection, till tally, stamp confirmation). */
export async function deskAction(action,data,el,ctx){
  if(!action.startsWith('desk:'))return false;
  const name=action.slice(5),{api,cmd,confirmAction,renderSheet,toast}=ctx;
  if(name==='sel'){local.task=data.task;local.sel=local.sel===data.field?null:data.field;renderSheet();return true;}
  if(name==='unsel'){local.sel=null;renderSheet();return true;}
  if(name==='flag'){const r=await cmd('desk_flag',{task:data.task,field:data.field,rule:data.rule},{quiet:true});
    if(r){toast(r.message,r.mark==='found'?'good':r.mark==='wrong'?'error':false);if(r.mark==='found')local.sel=null;renderSheet();}
    return true;}
  if(name==='note'){const tally=local.tally[data.task]??={in:[],out:[]},id=data.note;
    if(tally.in.includes(id)){tally.in=tally.in.filter(x=>x!==id);tally.out.push(id);}
    else if(tally.out.includes(id))tally.out=tally.out.filter(x=>x!==id);
    else tally.in.push(id);
    renderSheet();return true;}
  if(name==='reset'){local.tally[data.task]={in:[],out:[]};renderSheet();return true;}
  if(name==='decide'){
    const t=room(api).tasks.find(x=>x.id===data.task);if(!t)return true;
    if(!room(api).open){toast('Mở ca trước khi đóng dấu nhé.',true);return true;}
    const found=(t.marks||[]).filter(m=>m.result==='found').length;
    const waiting=Object.keys(t.pending||{}).length?' Vẫn còn một bước kiểm đang chờ kết quả.':'';
    const ok=await confirmAction('Đóng dấu: '+data.label+'?',`Bạn đã chỉ ra ${found} chỗ sai.${waiting} Đóng dấu rồi thì hồ sơ khép lại, không sửa được nữa.`,'Đóng dấu');
    if(ok){const r=await cmd('desk_decide',{task:t.id,verdict:data.verdict,confirm:true},{quiet:true});if(r){local.sel=null;renderSheet();}}
    return true;}
  return false;
}
