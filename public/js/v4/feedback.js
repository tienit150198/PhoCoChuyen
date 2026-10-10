/** "Góp ý" — players send a short note (bug, idea, praise, hard to use) to the
 * people who make the game, and see the owner's reply. Admin accounts (the
 * bootstrap `admin` flag, re-checked by the server on every call) also get the
 * "📥 Hộp góp ý" inbox. See docs/superpowers/specs/2026-09-29-player-feedback-design.md. */
import {icon,escapeHTML as esc} from '../icons.js';
import {statsView,statsAction} from './admin-stats.js';

const TEXT_MAX=10000,REPLY_MAX=10000;   // owner 06/10: 10,000 characters, 10/10 the reply too (game/player_feedback.py)
const IMAGE_MAX=3,IMAGE_BYTES=2*1024*1024;
const IMAGE_TYPES=new Set(['image/png','image/jpeg','image/webp']);
export const KINDS=[['bug','🐞','Lỗi'],['idea','💡','Ý tưởng'],['praise','💖','Khen'],['hard','🤔','Khó dùng']];
const HINTS={bug:'Bạn đang làm gì thì gặp lỗi? Lỗi trông ra sao?',idea:'Bạn muốn game có thêm điều gì?',praise:'Điều gì làm bạn thấy vui?',hard:'Chỗ nào làm bạn lúng túng hoặc phải đoán?'};
const STATUS={new:['Đã gửi',''],seen:['Đã xem','blue'],done:['Đã xử lý','green']};
const ADMIN_STATUS=[['new','Mới'],['seen','Đã xem'],['done','Xong']];
const LAYOUT_NAME={phone:'điện thoại',tablet:'máy tính bảng',desktop:'máy tính'};

const attrs=obj=>Object.entries(obj).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const button=(label,action,data={},style='',extra='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${extra}>${label}</button>`;
const pill=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
const head=(title,sub)=>`<header class="sheet-head"><div class="grow"><span class="eyebrow">GÓP Ý</span><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const ago=t=>{const s=Math.max(0,Date.now()/1000-t);if(s<60)return'vừa xong';if(s<3600)return`${Math.floor(s/60)} phút trước`;if(s<86400)return`${Math.floor(s/3600)} giờ trước`;return`${Math.floor(s/86400)} ngày trước`;};
const kindOf=id=>KINDS.find(k=>k[0]===id)||KINDS[0];
const loading=`<div class="empty">${icon('sparkle',26)}<p class="muted">Đang tải…</p></div>`;
const failed=d=>`<div class="notice danger">${icon('alert',17)}<div>${esc(d.error)}</div></div>`;

const fbState=ui=>ui.fb??={kind:'bug',draft:'',images:[],tab:'write',filter:{status:'new',kind:''},sent:null,mine:null,inbox:null};
const layout=()=>document.documentElement.dataset.layout||'desktop';
function careerName(api,id){const c=api.content?.catalogue?.find(x=>x.id===id);return c?.short||c?.name||id;}

/** What the server will attach (it derives career/day itself; the client only adds view, layout, screen). */
function clientContext(ui){return {view:ui.fb?.from||'stage',layout:layout(),screen:`${Math.round(innerWidth)}x${Math.round(innerHeight)}`};}
function contextLine(env){
  const {api}=env,cur=api.state?.current,c=cur?api.state.careers?.[cur]:null,parts=[];
  if(cur)parts.push(esc(careerName(api,cur)));
  if(c?.day)parts.push(`ngày ${c.day}`);
  else if(api.state?.journey?.life_day)parts.push(`ngày ${api.state.journey.life_day}`);
  parts.push(LAYOUT_NAME[layout()]||layout());
  return parts.join(' · ');
}

/* ---- data ---------------------------------------------------------------- */
function loadMine(env){
  const {api,ui}=env,fb=fbState(ui);
  if(fb.mine||fb.mineBusy)return;
  fb.mineBusy=true;
  api.json('/api/feedback/mine').then(d=>{fb.mine=d;if(typeof d.admin==='boolean')api.admin=d.admin;})
    .catch(e=>{fb.mine={error:e.message};}).finally(()=>{fb.mineBusy=false;if(ui.view==='gopy')env.renderSheet();});
}
function inboxQuery(fb,before){
  const q=new URLSearchParams();if(fb.filter.status)q.set('status',fb.filter.status);if(fb.filter.kind)q.set('kind',fb.filter.kind);if(before)q.set('before',before);
  return q.toString();
}
function loadInbox(env,more=false){
  const {api,ui}=env,fb=fbState(ui);
  if(fb.inboxBusy||(!more&&fb.inbox))return;
  fb.inboxBusy=true;
  const before=more?fb.inbox?.next:null;
  api.json('/api/admin/feedback?'+inboxQuery(fb,before),{headers:{'X-Game-CSRF':api.csrf}})
    .then(d=>{fb.inbox=more&&fb.inbox?{...d,items:[...fb.inbox.items,...d.items]}:d;})
    .catch(e=>{fb.inbox={error:e.message,items:[]};if(e.status===403)api.admin=false;})
    .finally(()=>{fb.inboxBusy=false;if(ui.view==='gopy')env.renderSheet();});
}

/* ---- player page ----------------------------------------------------------- */
function imagePicker(fb){
  const images=fb.images||[],busy=fb.sending||fb.imagesBusy;
  return `<div class="fb-attachments"><span class="field">Ảnh đính kèm (tùy chọn)</span>
    <label class="btn ghost small fb-image-choose${busy||images.length>=IMAGE_MAX?' disabled':''}" for="fb-images">Chọn ảnh
    <input id="fb-images" class="fb-image-input" type="file" accept="image/png,image/jpeg,image/webp" multiple aria-describedby="fb-images-help"${busy||images.length>=IMAGE_MAX?' disabled':''}></label>
    <p id="fb-images-help" class="small muted">Chọn tối đa 3 ảnh PNG, JPG hoặc WebP, mỗi ảnh tối đa 2 MB. ${fb.imagesBusy?'Đang đọc ảnh…':`${images.length}/3 ảnh đã chọn.`}</p>
    ${images.length?`<div class="fb-image-grid">${images.map((image,index)=>`<figure class="fb-image-draft"><img src="${esc(image.data)}" alt="Ảnh đính kèm ${index+1}" width="120" height="90"><figcaption>${esc(image.name)}</figcaption>${button('Bỏ ảnh','fbRemoveImage',{index},'ghost small',busy?' disabled':'')}</figure>`).join('')}</div>`:''}
  </div>`;
}
function imageGallery(images){
  // Use only protected same-origin image paths returned by the feedback API.
  const safe=(images||[]).filter(image=>/^\/api\/feedback\/images\/[a-f0-9]{32}$/.test(image.url));
  if(!safe.length)return '';
  return `<div class="fb-image-grid" aria-label="Ảnh đính kèm">${safe.map((image,index)=>`<a class="fb-image-link" href="${esc(image.url)}" target="_blank" rel="noopener" aria-label="Mở ảnh đính kèm ${index+1}"><img src="${esc(image.url)}" alt="Ảnh đính kèm ${index+1}" loading="lazy" width="120" height="90"><span class="small">Xem ảnh ${index+1}</span></a>`).join('')}</div>`;
}
function readFile(file){
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve({name:file.name,data:reader.result});
    reader.onerror=reader.onabort=()=>reject(new Error('Không đọc được ảnh. Chọn lại ảnh rồi thử nhé.'));
    reader.readAsDataURL(file);
  });
}
async function addImages(el,env){
  const fb=fbState(env.ui),files=Array.from(el.files||[]);el.value='';
  if(!files.length||fb.sending||fb.imagesBusy)return;
  fb.images??=[];
  if(fb.images.length+files.length>IMAGE_MAX){env.toast('Mỗi góp ý được gửi tối đa 3 ảnh.',true);return;}
  if(files.some(file=>!IMAGE_TYPES.has(file.type))){env.toast('Chọn ảnh PNG, JPG hoặc WebP tĩnh.',true);return;}
  if(files.some(file=>!file.size||file.size>IMAGE_BYTES)){env.toast('Mỗi ảnh tối đa 2 MB. Hãy chọn ảnh nhỏ hơn.',true);return;}
  fb.imagesBusy=true;env.renderSheet();
  try{const images=await Promise.all(files.map(readFile));fb.images.push(...images);}
  catch(error){env.toast(error.message,true);}
  finally{fb.imagesBusy=false;if(env.ui.view==='gopy')env.renderSheet();}
}
function writeForm(env){
  const fb=fbState(env.ui),len=[...fb.draft].length;
  if(fb.sent)return `<section class="card fb-done" role="status"><span class="fb-done-mark" aria-hidden="true">${icon('check',30)}</span><h3>${esc(fb.sent.message||'Đã ghi nhận, cảm ơn bạn!')}</h3><p class="muted small">Nhà làm game sẽ đọc từng góp ý. Khi có lời đáp, bạn xem ở mục “Góp ý của bạn” ngay bên dưới.</p>${button(icon('plus',15)+' Viết thêm góp ý','fbAgain',{},'primary')}</section>`;
  return `<form id="fbForm" class="card fb-form" novalidate>
    <div class="fb-kinds" role="radiogroup" aria-label="Loại góp ý">${KINDS.map(([id,emo,label])=>`<button type="button" role="radio" class="chip fb-kind${fb.kind===id?' selected':''}" aria-checked="${fb.kind===id}" data-action="fbKind" data-kind="${id}"><span aria-hidden="true">${emo}</span> ${label}</button>`).join('')}</div>
    <label class="field fb-field" for="fb-text">Bạn muốn nói gì?<textarea id="fb-text" name="text" rows="5" maxlength="${TEXT_MAX}" placeholder="${esc(HINTS[fb.kind])}" data-no-translate>${esc(fb.draft)}</textarea></label>
    <div class="fb-meta"><span class="fb-context">${icon('clipboard',14)}<span>Gửi kèm: <b>${contextLine(env)}</b></span></span><output id="fb-count" class="fb-count${len>TEXT_MAX-50?' near':''}" for="fb-text">${len}/${TEXT_MAX}</output></div>
    ${imagePicker(fb)}
    <p class="small muted fb-privacy">Máy chủ tự ẩn số điện thoại, email và đường link trong lời viết. Hãy che thông tin riêng tư trên ảnh trước khi gửi. Chỉ bạn và nhà làm game xem được góp ý cùng ảnh đính kèm. <a href="/privacy" target="_blank" rel="noopener">Quyền riêng tư</a></p>
    <button class="btn primary full" type="submit"${fb.sending||fb.imagesBusy?' disabled':''}>${icon('send',16)} ${fb.sending?'Đang gửi…':'Gửi góp ý'}</button>
  </form>`;
}
/** ✏️ F#295 "nên có nút sửa lại góp ý": a note with no reply yet can be edited in place (game/player_feedback.py edit
 * re-checks owner and "no reply" in one UPDATE). fb.edit = {id, draft, sending} while the form is open. */
function editForm(fb,it){
  const e=fb.edit,len=[...e.draft].length;
  return `<form class="fb-edit-form" data-fb-edit="${it.id}" novalidate><label class="field fb-field" for="fb-edit-${it.id}">Sửa góp ý<textarea id="fb-edit-${it.id}" name="text" rows="4" maxlength="${TEXT_MAX}" data-preserve data-no-translate>${esc(e.draft)}</textarea></label>
    <div class="fb-meta"><span class="small muted">Lưu xong, góp ý được đọc lại từ đầu.</span><output id="fb-edit-count" class="fb-count${len>TEXT_MAX-50?' near':''}" for="fb-edit-${it.id}">${len}/${TEXT_MAX}</output></div>
    <div class="row wrap"><button class="btn primary small" type="submit"${e.sending?' disabled':''}>${icon('check',14)} ${e.sending?'Đang lưu…':'Lưu góp ý'}</button>${button('Hủy','fbEditCancel',{},'ghost small')}</div></form>`;
}
function mineItem(it,fb={}){
  const [emo,label]=kindOf(it.kind).slice(1),[st,cls]=STATUS[it.status]||STATUS.new,editing=!it.reply&&fb.edit?.id===it.id;
  return `<article class="fb-item"><div class="fb-item-top"><span class="fb-item-kind"><span aria-hidden="true">${emo}</span> ${label}</span>${pill(st,cls)}<small class="muted">${ago(it.created_at)}</small></div>
    ${editing?editForm(fb,it):`<p class="fb-text" data-no-translate>${esc(it.text)}</p>`}
    ${imageGallery(it.images)}
    ${it.reply?`<div class="fb-reply"><b>${icon('chat',14)} Nhà làm game trả lời</b><p data-no-translate>${esc(it.reply)}</p>${it.replied_at?`<small class="muted">${ago(it.replied_at)}</small>`:''}</div>`:editing?'':`<div class="row fb-edit-row">${button('✏️ Sửa','fbEdit',{id:it.id},'ghost small')}</div>`}</article>`;
}
function mineList(env){
  const fb=fbState(env.ui);loadMine(env);
  const d=fb.mine;
  const body=!d?loading:d.error?failed(d):d.items.length?`<div class="fb-list">${d.items.map(it=>mineItem(it,fb)).join('')}</div>`:`<p class="muted small fb-empty">Bạn chưa gửi góp ý nào. Góp ý đầu tiên luôn được đọc kỹ nhất!</p>`;
  return `<section class="fb-mine"><h3 class="section-title">Góp ý của bạn</h3>${body}</section>`;
}

/* ---- admin inbox ------------------------------------------------------------ */
const CTX_LABEL={career:'Nghề',day:'Ngày trong nghề',life_day:'Ngày đời',view:'Màn hình',layout:'Bố cục',screen:'Kích thước',lang:'Ngôn ngữ',version:'Phiên bản',ua:'Trình duyệt'};
function contextKV(env,ctx){
  const rows=Object.entries(ctx||{}).map(([k,v])=>{
    const val=k==='career'?`${esc(careerName(env.api,v))} <small class="muted">(${esc(v)})</small>`:k==='layout'?esc(LAYOUT_NAME[v]||v):esc(v);
    return `<div class="kv-row"><span>${esc(CTX_LABEL[k]||k)}</span><span data-no-translate>${val}</span></div>`;
  });
  return rows.length?`<div class="kv fb-ctx">${rows.join('')}</div>`:'<p class="muted small">Không có ngữ cảnh.</p>';
}
function adminItem(env,it){
  const [emo,label]=kindOf(it.kind).slice(1),[st,cls]=STATUS[it.status]||STATUS.new;
  const who=it.account?`@${esc(it.account)}`:`khách #${esc(it.player)}`;
  const firstLine=esc((it.text||'').split('\n')[0].slice(0,90));
  return `<details class="fb-admin-item ${it.status}" data-id="${it.id}"><summary><span class="fb-item-kind"><span aria-hidden="true">${emo}</span> ${label}</span>${pill(it.status==='new'?'Mới':st,it.status==='new'?'amber':cls)}<span class="fb-sum-text" data-no-translate>${firstLine}</span><small class="muted fb-sum-who" data-no-translate>${who} · ${ago(it.created_at)} · #${it.id}</small></summary>
    <div class="fb-admin-body"><p class="fb-text" data-no-translate>${esc(it.text)}</p>
      ${imageGallery(it.images)}
      <h4 class="fb-sub">Ngữ cảnh</h4>${contextKV(env,it.context)}
      <div class="fb-status-row" role="group" aria-label="Đổi trạng thái">${ADMIN_STATUS.map(([s,l])=>`<button type="button" class="chip${it.status===s?' selected':''}" aria-pressed="${it.status===s}" data-action="fbSetStatus" data-id="${it.id}" data-status="${s}">${l}</button>`).join('')}</div>
      <form class="fb-reply-form" data-fb-reply="${it.id}"><label class="field" for="fb-reply-${it.id}">Lời đáp cho người chơi<textarea id="fb-reply-${it.id}" name="reply" rows="3" maxlength="${REPLY_MAX}" data-preserve data-no-translate placeholder="Cảm ơn bạn, mình đã sửa trong bản tới…">${esc(it.reply||'')}</textarea></label>
        <div class="row wrap"><button class="btn primary small" type="submit">${icon('send',14)} ${it.reply?'Cập nhật lời đáp':'Gửi lời đáp'}</button>${it.reply?button('Xóa lời đáp','fbClearReply',{id:it.id},'ghost small'):''}</div></form>
    </div></details>`;
}
function inboxView(env){
  const fb=fbState(env.ui);loadInbox(env);
  const d=fb.inbox,counts=d?.counts||{};
  const total=Object.values(counts).reduce((a,b)=>a+b,0);
  const statusChips=[['','Tất cả',total],...ADMIN_STATUS.map(([s,l])=>[s,l,counts[s]||0])].map(([s,l,n])=>`<button type="button" class="chip${(fb.filter.status||'')===s?' selected':''}" aria-pressed="${(fb.filter.status||'')===s}" data-action="fbFilter" data-field="status" data-value="${s}">${l} <em>${d?n:'·'}</em></button>`).join('');
  const kindChips=[['','Mọi loại',''],...KINDS.map(([k,e,l])=>[k,l,e])].map(([k,l,e])=>`<button type="button" class="chip${(fb.filter.kind||'')===k?' selected':''}" aria-pressed="${(fb.filter.kind||'')===k}" data-action="fbFilter" data-field="kind" data-value="${k}">${e?`<span aria-hidden="true">${e}</span> `:''}${l}</button>`).join('');
  let list;
  if(!d)list=loading;
  else if(d.error)list=failed(d);
  else if(!d.items.length)list=`<div class="empty">${icon('inbox',28)}<p class="muted">Không có góp ý nào ở mục này.</p></div>`;
  else list=`<div class="fb-admin-list">${d.items.map(it=>adminItem(env,it)).join('')}</div>${d.next?`<div class="row fb-more">${button(fb.inboxBusy?'Đang tải…':'Xem thêm','fbMore',{},'ghost small')}</div>`:''}`;
  const summary=d&&!d.error?`<b>${total}</b> góp ý · <b>${counts.new||0}</b> chưa đọc`:'&nbsp;';
  return `<section class="fb-inbox"><div class="row spread fb-inbox-head"><p class="small muted">${summary}</p>${button(icon('refresh',14)+' Tải lại','fbReload',{},'ghost small')}</div>
    <div class="chip-row fb-filters" aria-label="Lọc theo trạng thái">${statusChips}</div><div class="chip-row fb-filters" aria-label="Lọc theo loại">${kindChips}</div>${list}</section>`;
}

export function feedbackPageView(env){
  const {api,ui}=env,fb=fbState(ui),admin=!!api.admin;
  if(!admin&&(fb.tab==='inbox'||fb.tab==='stats'))fb.tab='write';
  if(fb.tab==='stats')return head('Thống kê','Chỉ tài khoản vận hành thấy mục này.').replace('>GÓP Ý<','>VẬN HÀNH<')+`<div class="sheet-body fb-sheet">${adminTabs(fb)}${statsView(env)}</div>`;
  const tabs=admin?adminTabs(fb):'';
  const body=fb.tab==='inbox'?inboxView(env):writeForm(env)+mineList(env);
  return head(fb.tab==='inbox'?'Hộp góp ý':'Góp ý cho nhà làm game',fb.tab==='inbox'?'Chỉ tài khoản vận hành thấy mục này.':'Lỗi, ý tưởng, lời khen hay chỗ khó dùng: viết vài dòng là đủ.')+`<div class="sheet-body fb-sheet">${tabs}${body}</div>`;
}
function adminTabs(fb){
  return `<nav class="pill-tabs" role="tablist">${[['write','💬 Góp ý'],['inbox','📥 Hộp góp ý'],['stats','📊 Thống kê']].map(([id,l])=>`<button type="button" role="tab" aria-selected="${fb.tab===id}" class="${fb.tab===id?'active':''}" data-action="fbTab" data-tab="${id}">${l}</button>`).join('')}</nav>`;
}

/* ---- actions ---------------------------------------------------------------- */
function patchItem(fb,item){
  if(!fb.inbox?.items)return;
  const i=fb.inbox.items.findIndex(x=>x.id===item.id);if(i<0)return;
  const old=fb.inbox.items[i].status;
  if(old!==item.status&&fb.inbox.counts){fb.inbox.counts[old]=Math.max(0,(fb.inbox.counts[old]||0)-1);fb.inbox.counts[item.status]=(fb.inbox.counts[item.status]||0)+1;}
  fb.inbox.items[i]=item;
}
async function adminUpdate(env,body){
  const {api,ui,toast}=env,fb=fbState(ui);
  try{const d=await api.post('/api/admin/feedback',body);patchItem(fb,d.item);fb.mine=null;return d.item;}
  catch(e){toast(e.message,true);if(e.status===403){api.admin=false;fb.tab='write';}return null;}
  finally{env.renderSheet();}
}

export async function feedbackAction(action,data,el,env){
  const {ui}=env;
  switch(action){
    case'gopy':{const fb=fbState(ui);fb.from=ui.view&&ui.view!=='gopy'?ui.view:'stage';fb.sent=null;fb.mine=null;fb.inbox=null;fb.edit=null;env.openSheet('gopy');return true;}
    case'fbKind':fbState(ui).kind=data.kind;env.renderSheet();return true;
    case'fbRemoveImage':{const fb=fbState(ui),index=Number(data.index);if(!fb.sending&&!fb.imagesBusy&&Number.isInteger(index)&&index>=0)fb.images?.splice(index,1);env.renderSheet();return true;}
    case'fbAgain':fbState(ui).sent=null;env.renderSheet(false);setTimeout(()=>document.getElementById('fb-text')?.focus(),0);return true;
    case'fbTab':fbState(ui).tab=data.tab;env.renderSheet(false);return true;
    case'fbFilter':{const fb=fbState(ui);fb.filter[data.field]=data.value;fb.inbox=null;env.renderSheet(false);return true;}
    case'fbReload':{const fb=fbState(ui);fb.inbox=null;env.renderSheet();return true;}
    case'fbMore':loadInbox(env,true);env.renderSheet();return true;
    case'fbSetStatus':{const it=await adminUpdate(env,{id:Number(data.id),status:data.status});if(it)env.toast('Đã đổi trạng thái.');return true;}
    case'fbEdit':{const fb=fbState(ui),it=fb.mine?.items?.find(x=>x.id===Number(data.id));if(!it||it.reply)return true;
      fb.edit={id:it.id,draft:it.text,sending:false};env.renderSheet(false);setTimeout(()=>{const t=document.getElementById(`fb-edit-${it.id}`);if(t){t.focus();t.setSelectionRange?.(t.value.length,t.value.length);}},0);return true;}
    case'fbEditCancel':fbState(ui).edit=null;env.renderSheet(false);return true;
    case'fbClearReply':{const it=await adminUpdate(env,{id:Number(data.id),reply:''});if(it)env.toast('Đã xóa lời đáp.');return true;}
  }
  return statsAction(action,data,el,env);
}

export async function feedbackSubmit(f,env){
  const {api,ui,toast}=env;
  if(f.dataset.fbReply){
    const reply=f.querySelector('textarea')?.value.trim()||'';
    if(!reply){toast('Viết lời đáp trước đã nhé.',true);return true;}
    // Replying also marks the note as seen (unless it is already done).
    const cur=fbState(ui).inbox?.items?.find(x=>x.id===Number(f.dataset.fbReply));
    const it=await adminUpdate(env,{id:Number(f.dataset.fbReply),reply,...(cur?.status==='new'?{status:'seen'}:{})});
    if(it)toast('Đã gửi lời đáp.','good');
    return true;
  }
  if(f.dataset.fbEdit){
    const fb=fbState(ui),e=fb.edit,id=Number(f.dataset.fbEdit),text=(f.querySelector('textarea')?.value||'').trim();
    if(!e||e.id!==id||e.sending)return true;
    e.draft=f.querySelector('textarea')?.value||'';
    if([...text].length<3){toast('Viết thêm vài chữ nữa nhé.',true);return true;}
    e.sending=true;env.renderSheet(false);
    try{
      const d=await api.post('/api/feedback/edit',{id,text});
      const i=fb.mine?.items?.findIndex(x=>x.id===id)??-1;if(i>=0&&d.item)fb.mine.items[i]=d.item;
      fb.edit=null;toast(d.message||'Đã lưu góp ý.','good');
    }catch(err){
      e.sending=false;
      if(err.status===409){fb.edit=null;fb.mine=null;}   // a reply came meanwhile: show it
      toast(err.status?err.message:'Mất kết nối. Chữ vẫn còn trong ô, thử lại sau nhé.',true);
    }
    finally{env.renderSheet(false);}
    return true;
  }
  if(f.id!=='fbForm')return false;
  const fb=fbState(ui),text=(f.querySelector('#fb-text')?.value||'').trim();
  fb.draft=f.querySelector('#fb-text')?.value||'';
  if([...text].length<3){toast('Viết thêm vài chữ nữa nhé.',true);f.querySelector('#fb-text')?.focus();return true;}
  if(fb.sending||fb.imagesBusy)return true;
  fb.sending=true;env.renderSheet();
  try{
    const d=await api.post('/api/feedback',{kind:fb.kind,text,context:clientContext(ui),images:(fb.images||[]).map(image=>image.data)});
    fb.sent={id:d.id,message:d.message};fb.draft='';fb.images=[];fb.mine=null;
  }catch(e){toast(e.status?e.message:'Mất kết nối. Góp ý vẫn còn trong ô, thử lại sau nhé.',true);}
  finally{fb.sending=false;env.renderSheet();}
  return true;
}

/** Live counter; the draft survives closing the sheet. */
export function feedbackInput(el,env){
  if(el.id==='fb-images'){void addImages(el,env);return true;}
  if(el.id?.startsWith('fb-edit-')){
    const e=fbState(env.ui).edit;if(!e||el.id!==`fb-edit-${e.id}`)return true;e.draft=el.value;
    const out=document.getElementById('fb-edit-count'),n=[...el.value].length;
    if(out){out.textContent=`${n}/${TEXT_MAX}`;out.classList.toggle('near',n>TEXT_MAX-50);}
    return true;
  }
  if(el.id!=='fb-text')return false;
  const fb=fbState(env.ui);fb.draft=el.value;
  const out=document.getElementById('fb-count'),n=[...el.value].length;
  if(out){out.textContent=`${n}/${TEXT_MAX}`;out.classList.toggle('near',n>TEXT_MAX-50);}
  return true;
}
