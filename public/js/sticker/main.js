/** 🎨 /sticker (public/sticker.html): the sticker-pack contest page. Who is signed in comes from GET /api/sticker/me (the
 * game's own session cookie; this page never creates a session or signs anyone in: "Vào phố đăng nhập" opens the game,
 * and the page checks again when it is shown again). The pack is made in any app: ONE picture of the whole set (kind
 * 'sheet', the author says how many stickers it holds) or one picture per sticker (kind 'set', each fitted into the
 * 512 square on the device: ./pics.js). "Nộp" POSTs it to /api/sticker/pack (game/sticker_event.py checks everything
 * again); sending again replaces the pack. "Tải ảnh để đăng" saves the picture to post in the Facebook group (the
 * sheet with the @username badge when asked, a collage of a set). The CSRF token stays in memory; nothing is stored. */
import {SIZE,loadPicture,fitSquare,stamped,collage,encode,shrink} from './pics.js';

const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const xu=n=>`${Number(n).toLocaleString('vi-VN')} xu`;
const mb=n=>n>=1048576?`${Math.round(n/1048576)} MB`:`${Math.round(n/1024)} KB`;
const when=t=>new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit',year:'numeric'}).format(new Date(t*1000));

let me=null,kind='sheet',sheet=null,set=[],sending=false,dirty=false,busy=false,editing=false;

async function getJSON(url,opt={}){
  const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),opt.timeout||20000);
  try{
    const res=await fetch(url,{credentials:'same-origin',cache:'no-store',...opt,signal:ctl.signal});
    let data={};try{data=await res.json();}catch{data={};}
    if(!res.ok){const e=new Error(data.error||`Lỗi ${res.status}`);e.status=res.status;e.code=data.code||'';throw e;}
    return data;
  }catch(e){if(!e.status){const n=new Error(e.name==='AbortError'?'Máy chủ phản hồi lâu quá. Thử lại nhé.':'Mất kết nối. Kiểm tra mạng rồi thử lại nhé.');n.status=0;throw n;}throw e;}
  finally{clearTimeout(timer);}
}
const say=(text,tone='')=>{const m=$('#pack').hidden?$('#post-msg'):$('#msg');m.textContent=text;m.className='msg'+(tone?' '+tone:'');};  // the form folds once a pack is in
const uname=()=>'@'+(me?.account?.username||'');
const aiChoice=()=>{const r=document.querySelector('input[name="ai"]:checked');return r?r.value==='1':null;};

// ---- who, rules, my pack, results -----------------------------------------------------------------
async function refresh(){
  try{me=await getJSON('/api/sticker/me');}
  catch(e){$('#who').innerHTML=`<p class="bad">${esc(e.message)}</p><button type="button" class="btn ghost" data-do="retry">Thử lại</button>`;return;}
  renderRules();renderWho();renderMine();renderResults();
  const signed=Boolean(me.account);
  $('#pack').hidden=!signed||!me.open||(Boolean(me.pack)&&!editing);$('#post').hidden=!signed;
  for(const el of document.querySelectorAll('.uname'))el.textContent=uname();
  renderKind();renderPost();
}

function renderRules(){
  const r=me.rules,end=when(r.end);
  $('#deadline').textContent=me.open?`Hạn nộp: ${end}`:`Đã đóng nhận bài lúc ${end}`;
  $('#lead-min').textContent=r.min;
  $('#prizes').innerHTML=`<li class="p1"><b>Top 1</b><span>${xu(r.prizes[0].coins)}</span></li><li class="p2"><b>Top ${esc(r.prizes[1].ranks)}</b><span>${xu(r.prizes[1].coins)}</span></li>`+
    `<li class="p3"><b>Top ${esc(r.prizes[2].ranks)}</b><span>${xu(r.prizes[2].coins)}</span></li><li class="pj"><b>Tham gia</b><span>${xu(r.join)}</span></li>`;
  $('#rules-list').innerHTML=[
    `Làm một <b>bộ sticker</b>: một nhân vật (con vật, người, đồ vật… tùy bạn) với nhiều biểu cảm khác nhau, <b>ít nhất ${r.min} sticker</b>. Làm bằng ứng dụng nào cũng được: Canva, Picsart, CapCut, Ibis Paint, Photoshop, vẽ tay rồi chụp lại…`,
    `Nộp ở trang này: <b>một ảnh ghép cả bộ</b> (PNG/JPG, tối đa ${mb(r.sheet_bytes)}) hoặc <b>từng sticker</b> (${r.min}–${r.max_set} ảnh). Mỗi tài khoản một bộ; nộp lại trước hạn là thay bộ cũ.`,
    `Có dùng AI (ChatGPT, Gemini, Midjourney…) vẫn được thi, nhưng phải chọn <b>“Có dùng AI”</b> khi nộp và ghi rõ trong bài đăng.`,
    `Đăng bộ sticker vào nhóm Facebook của phố, ghi kèm <b>@tên tài khoản</b> và <b>${esc(r.hashtag)}</b>. Bình chọn bằng lượt thả cảm xúc trên bài đăng, tính đến ${end}.`,
    `Tham gia: ${xu(r.join)} mỗi tài khoản, vào ví khi bạn quay lại phố (nhân vật từ ngày thứ ${r.min_days} trở lên).`,
    `Top 1: ${xu(r.prizes[0].coins)} · Top ${esc(r.prizes[1].ranks)}: ${xu(r.prizes[1].coins)} · Top ${esc(r.prizes[2].ranks)}: ${xu(r.prizes[2].coins)}. Top 10 bộ được đưa vào chat trong game để mọi người dùng.`,
    'Bộ chép của người khác, phản cảm, không đủ số sticker hay không ghi tên tài khoản trong bài đăng sẽ bị loại.',
  ].map(x=>`<li>${x}</li>`).join('');
}

function renderWho(){
  const w=$('#who');
  if(!me.account){
    w.innerHTML=`<h2>Đăng nhập để nộp bộ sticker</h2><p>Bộ sticker gắn với tên tài khoản của bạn. Vào phố, mở <b>Cài đặt → Tài khoản</b> để đăng ký hoặc đăng nhập, rồi quay lại trang này.</p>`+
      `<div class="row"><a class="btn primary" href="/">Vào phố đăng nhập</a><button type="button" class="btn ghost" data-do="retry">Mình đăng nhập rồi</button></div>`;
    return;
  }
  const a=me.account,r=me.rules;
  let note='';
  if(!me.open)note='<p class="warn">Cuộc thi đã đóng nhận bài.</p>';
  else if(me.why==='days')note=`<p class="warn">Nhân vật cần sống ở phố từ ngày thứ ${r.min_days} mới nộp được (bạn đang ở ngày ${me.life_day}). Cứ làm bộ sticker trước, chơi thêm chút rồi quay lại nộp nhé.</p>`;
  if(me.legacy&&!me.pack)note+=`<p class="warn">Thể lệ đã đổi: giờ thi cả <b>bộ sticker</b> (từ ${r.min} sticker). ${me.legacy} sticker lẻ bạn gửi trước đó không được xét giải, quà tham gia vẫn giữ nguyên. Nộp một bộ ở dưới để vào vòng bình chọn nhé!</p>`;
  const joined=me.joined?`<p class="good">🎁 Quà tham gia ${xu(me.joined.coins)}: ${me.joined.status==='revoked'?'đã bị thu hồi':me.joined.paid?'đã vào ví':'vào ví khi bạn quay lại phố'}.</p>`:'';
  w.innerHTML=`<div class="me"><span class="avatar" aria-hidden="true">🙂</span><div class="grow"><b>${esc(a.display||a.username)}</b><small>@${esc(a.username)} · ngày ${me.life_day} ở phố</small></div>`+
    `<span class="count" title="Bộ đã nộp">${me.pack?'Đã nộp ✓':'Chưa nộp'}</span></div>${note}${joined}`;
}

const STATUS={live:['Đã nhận','good'],rejected:['Bị loại','bad']};
function packView(p,{small=false}={}){
  const imgs=p.kind==='sheet'
    ?`<a href="${esc(p.images[0]?.img)}" target="_blank" rel="noopener" class="sheet-view"><img src="${esc(p.images[0]?.thumb)}" alt="Ảnh cả bộ sticker" loading="lazy"></a>`
    :`<div class="set-view${small?' small':''}">${p.images.map((im,i)=>`<img src="${esc(im.thumb)}" alt="Sticker ${i+1}" width="80" height="80" loading="lazy">`).join('')}</div>`;
  return imgs;
}
function renderMine(){
  const box=$('#mine'),p=me.pack;box.hidden=!p;if(!p)return;
  const [label,tone]=STATUS[p.status]||[p.status,''];
  box.innerHTML=`<h2>Bộ sticker của bạn</h2>${packView(p)}<p class="meta"><span class="tag ${tone}">${p.rank?`🏆 Hạng ${p.rank}`:label}</span> `+
    `${p.kind==='sheet'?'Một ảnh cả bộ':'Từng sticker'} · ${p.count} sticker · ${p.ai?'🤖 Có dùng AI':'✍️ Tự làm'} · nộp lúc ${esc(when(p.updated))}</p>`+
    (p.status==='rejected'?`<p class="bad">Bộ này bị loại${p.note?`: ${esc(p.note)}`:''}. Bạn nộp bộ khác thay được nhé.</p>`:'')+
    (me.open&&!editing?'<button type="button" class="btn ghost" data-do="edit">🔁 Nộp bộ khác thay bộ này</button>':'');
}
function renderResults(){
  const box=$('#results');box.hidden=!me.results.length;
  $('#results-list').innerHTML=me.results.map(r=>`<div class="win r${r.rank<=3?r.rank:'x'}"><p class="win-head"><span class="rank">#${r.rank}</span> <b>${esc(r.display||r.username)}</b> <small>@${esc(r.username)} · ${xu(r.coins)}${r.ai?' · 🤖 có dùng AI':''}</small></p>${packView(r,{small:true})}</div>`).join('');
}

// ---- the pack being made ------------------------------------------------------------------------
function renderKind(){
  if(!me?.account)return;
  const r=me.rules;
  for(const b of document.querySelectorAll('[data-kind]'))b.setAttribute('aria-checked',String(b.dataset.kind===kind));
  $('#sheet-box').hidden=kind!=='sheet';$('#set-box').hidden=kind!=='set';$('#file').multiple=kind==='set';
  $('#kind-hint').innerHTML=kind==='sheet'
    ?`Một tấm ảnh ghép cả bộ, như ảnh mẫu 4×4 (PNG nền trong suốt hay JPG đều được). Ghi số sticker có trong ảnh: ít nhất ${r.min}.`
    :`Chọn từng ảnh sticker, ${r.min}–${r.max_set} ảnh (chọn nhiều ảnh một lúc được). Mỗi ảnh được thu vào khung vuông ${SIZE}×${SIZE} giống sticker trong chat.`;
  const cv=$('#sheet-cv');
  $('#sheet-empty').hidden=Boolean(sheet);cv.hidden=!sheet;$('#sheet-tools').hidden=!sheet;
  if(sheet){const show=$('#sheet-stamp').checked?stamped(sheet,uname()):sheet;cv.width=show.width;cv.height=show.height;cv.getContext('2d').drawImage(show,0,0);}
  $('#sheet-count').min=r.min;$('#sheet-count').max=r.max_sheet;
  $('#set-grid').innerHTML=set.map((it,i)=>`<figure class="set-item"><img src="${it.url}" alt="Sticker ${i+1}" width="96" height="96"><button type="button" class="x" data-do="drop" data-i="${i}" aria-label="Bỏ sticker ${i+1}">✕</button></figure>`).join('')||
    `<button type="button" class="drop small" data-do="pick" aria-label="Chọn ảnh sticker"><span class="drop-empty"><span class="drop-icon" aria-hidden="true">🧩</span><b>Chọn ảnh sticker</b><small>chọn nhiều ảnh một lúc, hoặc kéo thả</small></span></button>`;
  const n=set.length;
  $('#set-count').textContent=`${n}/${r.min}${n>=r.min?' ✓':''}`;$('#set-count').className='count'+(n>=r.min?' ok':'');
  $('#set-add').hidden=!n||n>=r.max_set;
  syncSubmit();
}
function syncSubmit(){
  const b=$('#submit');if(!me?.account)return;
  b.disabled=sending||busy||!me.can;
  b.textContent=sending?'Đang nộp…':me.pack?'🔁 Nộp bộ mới thay bộ cũ':'📮 Nộp bộ sticker';
}
function renderPost(){
  if(!me?.account)return;
  const r=me.rules;
  $('#cap-text').textContent=caption();
  const fb=$('#fb');fb.hidden=!r.fb;if(r.fb)fb.href=r.fb;
  $('#download').hidden=!(kind==='sheet'?sheet&&$('#sheet-stamp').checked:set.length);
  $('#download').textContent=kind==='sheet'?'⬇️ Tải ảnh có nhãn tên':'⬇️ Tải ảnh ghép cả bộ để đăng';
}
const caption=()=>{const ai=aiChoice()??me?.pack?.ai;return `Bộ sticker của ${uname()} 🎨${ai?' (có dùng AI)':''} ${me?.rules?.hashtag||''}`;};

async function addFiles(files){
  const list=[...files].filter(Boolean);if(!list.length||busy)return;
  const r=me.rules;busy=true;syncSubmit();
  try{
    if(kind==='sheet'){
      say('Đang mở ảnh…');
      const c=await loadPicture(list[0],2048);
      if(Math.min(c.width,c.height)<r.sheet_side[0]){say(`Ảnh nhỏ quá (cạnh ngắn cần từ ${r.sheet_side[0]} điểm ảnh). Chọn ảnh rõ hơn nhé.`,'bad');return;}
      sheet=c;dirty=true;say(list.length>1?'Kiểu một ảnh cả bộ chỉ lấy ảnh đầu tiên. Muốn tải từng sticker thì chọn “Từng sticker”.':'Đã chọn ảnh. Ghi số sticker trong ảnh rồi nộp nhé.','good');
    }else{
      const room=r.max_set-set.length;
      if(room<=0){say(`Tối đa ${r.max_set} sticker một bộ.`,'bad');return;}
      const take=list.slice(0,room);let bad=0,lastErr='';
      for(const [i,f] of take.entries()){
        say(`Đang xử lý ${i+1}/${take.length}…`);
        try{const sq=fitSquare(await loadPicture(f,1024)),out=await encode(sq,r.item_bytes);
          if(out.tooBig){bad++;lastErr=`“${f.name}” nặng quá sau khi thu nhỏ.`;continue;}
          set.push({canvas:sq,blob:out.blob,url:URL.createObjectURL(out.blob)});}
        catch(e){bad++;lastErr=e.message;}
      }
      dirty=true;
      const extra=list.length>take.length?` Bỏ qua ${list.length-take.length} ảnh vì tối đa ${r.max_set} sticker.`:'';
      say(bad?`${lastErr}${bad>1?` (${bad} ảnh lỗi)`:''}${extra}`:`Đã thêm ${take.length} sticker.${set.length<r.min?` Cần thêm ${r.min-set.length} nữa.`:''}${extra}`,bad?'bad':'good');
    }
  }catch(e){say(e.message||'Không mở được ảnh này.','bad');}
  finally{busy=false;renderKind();renderPost();}
}

// ---- events ---------------------------------------------------------------------------------------
document.addEventListener('click',async e=>{
  const b=e.target.closest('button,[data-do]');if(!b||b.disabled)return;
  const d=b.dataset,act=d.do;
  if(act==='retry'){refresh();return;}
  if(d.kind){kind=d.kind;say('');renderKind();renderPost();return;}
  if(act==='edit'){editing=true;refresh().then(()=>$('#pack').scrollIntoView({block:'start',behavior:'smooth'}));return;}
  if(act==='pick')$('#file').click();
  else if(act==='drop'){const it=set.splice(Number(d.i),1)[0];if(it)URL.revokeObjectURL(it.url);renderKind();renderPost();}
  else if(act==='submit')submit();
  else if(act==='download')download();
  else if(act==='copy')copy();
});
$('#file').addEventListener('change',e=>{const files=e.target.files;addFiles(files).finally(()=>{e.target.value='';});});
$('#sheet-stamp').addEventListener('change',()=>{renderKind();renderPost();});
for(const r of document.querySelectorAll('input[name="ai"]'))r.addEventListener('change',renderPost);
for(const ev of ['dragover','dragenter'])document.addEventListener(ev,e=>{const z=e.target.closest?.('.drop');if(!z||$('#pack').hidden)return;e.preventDefault();z.classList.add('over');});
document.addEventListener('dragleave',e=>e.target.closest?.('.drop')?.classList.remove('over'));
document.addEventListener('drop',e=>{const z=e.target.closest?.('.drop');if(!z||$('#pack').hidden)return;e.preventDefault();z.classList.remove('over');addFiles(e.dataTransfer?.files||[]);});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&(!me||!me.account))refresh();});
window.addEventListener('beforeunload',e=>{if(dirty&&!sending){e.preventDefault();e.returnValue='';}});

// ---- out: submit, download, caption ----------------------------------------------------------------
const dataURL=blob=>new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=()=>no(new Error('Không đọc được ảnh.'));r.readAsDataURL(blob);});
async function sheetBlob(){
  const r=me.rules,base=$('#sheet-stamp').checked?stamped(sheet,uname()):sheet;
  for(const side of [2048,1600,1280]){const out=await encode(shrink(base,side),r.sheet_bytes);if(!out.tooBig)return out.blob;}
  return null;
}
async function submit(){
  if(sending||!me?.can)return;
  const r=me.rules,ai=aiChoice();
  let body;
  if(kind==='sheet'){
    if(!sheet){say('Chọn ảnh cả bộ sticker trước nhé.','bad');return;}
    const count=Number($('#sheet-count').value);
    if(!Number.isInteger(count)||count<r.min||count>r.max_sheet){say(`Ghi số sticker có trong ảnh (từ ${r.min} trở lên).`,'bad');$('#sheet-count').focus();return;}
    body={kind,count};
  }else{
    if(set.length<r.min){say(`Bộ sticker cần ít nhất ${r.min} sticker (đang có ${set.length}).`,'bad');return;}
    body={kind};
  }
  if(ai===null){say('Chọn bộ sticker tự làm hay có dùng AI nhé.','bad');$('#ai').scrollIntoView({block:'center',behavior:'smooth'});return;}
  if(!confirm(me.pack?'Nộp bộ này thay cho bộ bạn đã nộp?':'Nộp bộ sticker này? Trước hạn bạn vẫn nộp lại để thay được.'))return;
  sending=true;syncSubmit();say('Đang chuẩn bị ảnh…');
  try{
    if(kind==='sheet'){const blob=await sheetBlob();if(!blob){say(`Ảnh nặng quá ${mb(r.sheet_bytes)} kể cả sau khi thu nhỏ. Lưu lại ảnh nhẹ hơn rồi thử lại nhé.`,'bad');return;}body.images=[await dataURL(blob)];}
    else body.images=await Promise.all(set.map(it=>dataURL(it.blob)));
    body.ai=ai;
    say('Đang nộp…');
    const res=await getJSON('/api/sticker/pack',{method:'POST',timeout:90000,headers:{'Content-Type':'application/json','X-Game-CSRF':me.csrf||''},body:JSON.stringify(body)});
    dirty=false;editing=false;
    await refresh();
    say(res.joined?`Đã nộp! Quà tham gia ${xu(res.joined.coins)} vào ví khi bạn quay lại phố. Giờ đăng bộ sticker lên nhóm Facebook nhé!`:
      res.replaced?'Đã thay bộ sticker mới. Nhớ cập nhật bài đăng trong nhóm nhé!':'Đã nộp! Giờ đăng bộ sticker lên nhóm Facebook nhé!','good');
    $('#post').scrollIntoView({block:'start',behavior:'smooth'});
  }catch(e){say(e.message||'Chưa nộp được. Thử lại nhé.','bad');if(e.status===401||e.status===403)refresh();}
  finally{sending=false;syncSubmit();}
}
async function download(){
  const name=`bo-sticker-${me?.account?.username||'pho'}`;
  let blob;
  if(kind==='sheet'&&sheet)blob=(await encode(stamped(sheet,uname()))).blob;
  else if(set.length)blob=(await encode(collage(set.map(it=>it.canvas),uname()))).blob;
  if(!blob)return;
  const url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=`${name}.png`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
  say('Đã tải ảnh về. Đăng vào nhóm Facebook kèm chú thích nhé!','good');
}
async function copy(){
  try{await navigator.clipboard.writeText(caption());say('Đã chép chú thích.','good');}
  catch{const r=document.createRange();r.selectNodeContents($('#cap-text'));const s=getSelection();s.removeAllRanges();s.addRange(r);say('Giữ để chép chú thích nhé.');}
}

refresh();
