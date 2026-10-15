/** 🎨 /sticker (public/sticker.html): the contest page. Who is signed in comes from GET /api/sticker/me (the game's own
 * session cookie; this page never creates a session or signs anyone in: "Vào phố đăng nhập" opens the game, and the
 * page checks again when it is shown again). The maker is ./editor.js; "Nộp bài" POSTs the image to
 * /api/sticker/submit (game/sticker_event.py checks everything again), "Tải về" saves the PNG to post in the Facebook
 * group. The CSRF token stays in memory; nothing is written to storage. */
import {createEditor,loadPicture,FONTS,SHAPES} from './editor.js';

const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const xu=n=>`${Number(n).toLocaleString('vi-VN')} xu`;
const when=t=>new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit',year:'numeric'}).format(new Date(t*1000));
const COLORS=['#ffffff','#2b1e18','#ff4d6d','#ff8c42','#ffd23f','#3bceac','#0ead69','#3a86ff','#8338ec','#ff70a6','#a0522d','#9aa5b1'];
const EMOJI='😂 🤣 😍 🥰 😎 🤩 😭 😡 🥺 😴 🤔 🙄 😱 🤯 🥳 😇 😋 🤭 👍 👏 🙏 💪 ✌️ 🫶 ❤️ 🔥 ⭐ ✨ 💯 🎉 🍜 🧋 ☕ 🍉 🌸 🌈 ☀️ 🌙 🐱 🐶 🐷 🐸 🛵 🏮 💰 🎁 💤 💢'.split(' ');
const PHRASES=['Hello!','Cảm ơn nha','Đỉnh nóc!','Hehe','Ủa alo?','Chill thôi','Ăn gì chưa?','Xin vía','Okela','Yêu cả nhà','Tới công chuyện','Hóng quá'];
const WHY={closed:'Cuộc thi đã đóng nhận bài.',full:'Bạn đã nộp đủ sticker rồi.',days:'',login:'Đăng nhập để nộp bài.'};

let me=null,ed=null,tab='move',panelFor=null,sending=false,saved=false;

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
const say=(text,tone='')=>{const m=$('#msg');m.textContent=text;m.className='msg'+(tone?' '+tone:'');};

// ---- who, rules, entries, results ----------------------------------------------------------------
async function refresh(){
  try{me=await getJSON('/api/sticker/me');}
  catch(e){$('#who').innerHTML=`<p class="bad">${esc(e.message)}</p><button type="button" class="btn ghost" data-do="retry">Thử lại</button>`;return;}
  renderRules();renderWho();renderMine();renderResults();
  const signed=Boolean(me.account);
  $('#maker').hidden=!signed;$('#send').hidden=!signed;
  if(signed&&!ed)startEditor();
  if(ed){ed.setStamp({text:'@'+me.account.username});syncSend();}
}

function renderRules(){
  const r=me.rules,end=when(r.end);
  $('#deadline').textContent=me.open?`Hạn nộp: ${end}`:`Đã đóng nhận bài lúc ${end}`;
  $('#prizes').innerHTML=`<li class="p1"><b>Top 1</b><span>${xu(r.prizes[0].coins)}</span></li><li class="p2"><b>Top ${esc(r.prizes[1].ranks)}</b><span>${xu(r.prizes[1].coins)}</span></li>`+
    `<li class="p3"><b>Top ${esc(r.prizes[2].ranks)}</b><span>${xu(r.prizes[2].coins)}</span></li><li class="pj"><b>Tham gia</b><span>${xu(r.join)}</span></li>`;
  $('#rules-list').innerHTML=[
    'Làm sticker chủ đề gì cũng được ngay trên trang này. Tên <b>@tài khoản</b> của bạn luôn có trên sticker.',
    `Bấm <b>Nộp bài</b> để gửi cho ban tổ chức (tối đa ${r.max} sticker mỗi tài khoản), rồi <b>Tải về</b> và đăng vào nhóm Facebook của phố, ghi kèm tên tài khoản và <b>${esc(r.hashtag)}</b>.`,
    `Bình chọn bằng lượt thả cảm xúc trên bài đăng trong nhóm, tính đến ${end}.`,
    `Tham gia: ${xu(r.join)} mỗi người, vào ví khi bạn quay lại phố (sticker đầu tiên được nhận, nhân vật từ ngày thứ ${r.min_days} trở lên).`,
    `Top 1: ${xu(r.prizes[0].coins)} · Top ${esc(r.prizes[1].ranks)}: ${xu(r.prizes[1].coins)} · Top ${esc(r.prizes[2].ranks)}: ${xu(r.prizes[2].coins)}. Mỗi người nhận một giải.`,
    'Top 10 sticker sẽ được đưa vào chat trong game để mọi người dùng.',
    'Sticker chép của người khác, phản cảm hay thiếu tên tài khoản sẽ bị loại.',
  ].map(x=>`<li>${x}</li>`).join('');
}

function renderWho(){
  const w=$('#who');
  if(!me.account){
    w.innerHTML=`<h2>Đăng nhập để làm sticker</h2><p>Sticker cần có tên tài khoản của bạn. Vào phố, mở <b>Cài đặt → Tài khoản</b> để đăng ký hoặc đăng nhập, rồi quay lại trang này.</p>`+
      `<div class="row"><a class="btn primary" href="/">Vào phố đăng nhập</a><button type="button" class="btn ghost" data-do="retry">Mình đăng nhập rồi</button></div>`;
    return;
  }
  const a=me.account,n=me.entries.length,r=me.rules;
  let note='';
  if(!me.open)note='<p class="warn">Cuộc thi đã đóng nhận bài. Bạn vẫn làm và tải sticker về được.</p>';
  else if(me.why==='days')note=`<p class="warn">Nhân vật cần sống ở phố từ ngày thứ ${r.min_days} mới nộp được (bạn đang ở ngày ${me.life_day}). Cứ làm sticker trước, chơi thêm chút rồi quay lại nộp nhé.</p>`;
  else if(me.why==='full')note=`<p class="good">Bạn đã nộp đủ ${r.max} sticker. Nhớ đăng lên nhóm để mọi người bình chọn!</p>`;
  const joined=me.joined?`<p class="good">🎁 Quà tham gia ${xu(me.joined.coins)}: ${me.joined.status==='revoked'?'đã bị thu hồi':me.joined.paid?'đã vào ví':'vào ví khi bạn quay lại phố'}.</p>`:'';
  w.innerHTML=`<div class="me"><span class="avatar" aria-hidden="true">🙂</span><div class="grow"><b>${esc(a.display||a.username)}</b><small>@${esc(a.username)} · ngày ${me.life_day} ở phố</small></div><span class="count" title="Đã nộp">${n}/${r.max}</span></div>${note}${joined}`;
}

const STATUS={live:['Đã nhận','good'],rejected:['Bị loại','bad']};
function renderMine(){
  const box=$('#mine');box.hidden=!me.entries.length;
  $('#mine-grid').innerHTML=me.entries.map(e=>{const [label,tone]=STATUS[e.status]||[e.status,''];
    return `<figure class="tile"><img src="${esc(e.thumb)}" alt="Sticker #${e.id}" loading="lazy" width="160" height="160"><figcaption><span class="tag ${tone}">${e.rank?`🏆 Hạng ${e.rank}`:label}</span><small>${esc(when(e.created))}</small></figcaption></figure>`;}).join('');
}
function renderResults(){
  const box=$('#results');box.hidden=!me.results.length;
  $('#results-grid').innerHTML=me.results.map(r=>`<figure class="tile win r${r.rank<=3?r.rank:'x'}"><span class="rank">#${r.rank}</span><img src="${esc(r.img)}" alt="Sticker hạng ${r.rank} của @${esc(r.username)}" loading="lazy" width="160" height="160"><figcaption><b>${esc(r.display||r.username)}</b><small>@${esc(r.username)} · ${xu(r.coins)}</small></figcaption></figure>`).join('');
}

function syncSend(){
  const sub=document.querySelector('[data-do="submit"]'),r=me.rules;
  sub.hidden=!me.open;sub.disabled=sending||!me.can;
  sub.textContent=me.why==='full'?`✅ Đã nộp ${r.max}/${r.max}`:`📮 Nộp bài (${me.entries.length}/${r.max})`;
  const share=document.querySelector('[data-do="share"]');
  share.hidden=!(navigator.canShare&&navigator.canShare({files:[new File([new Blob(['x'],{type:'image/png'})],'s.png',{type:'image/png'})]}));
  const cap=caption(),fb=r.fb;
  $('#caption').innerHTML=`<p class="small">Chú thích khi đăng nhóm:</p><div class="cap-row"><code id="cap-text">${esc(cap)}</code><button type="button" class="btn ghost sm" data-do="copy">Chép</button></div>`+
    (fb?`<a class="btn fb" href="${esc(fb)}" target="_blank" rel="noopener">Mở nhóm Facebook</a>`:'<p class="small muted">Đường dẫn nhóm Facebook sẽ có ở đây sớm.</p>');
}
const caption=()=>`Sticker của @${me?.account?.username||''} 🎨 ${me?.rules?.hashtag||''}`;

// ---- the maker panel ------------------------------------------------------------------------------
function startEditor(){
  ed=createEditor($('#cv'),{onChange:()=>{syncTools();if(ed.selected!==panelFor)renderPanel();}});
  ed.setStamp({text:'@'+me.account.username});
  document.fonts?.load('800 40px "Be Vietnam Pro"').then(()=>ed.redraw()).catch(()=>{});
  document.fonts?.load('400 40px "Be Vietnam Pro"').then(()=>ed.redraw()).catch(()=>{});
  renderPanel();syncTools();
}
function setTab(t){
  tab=t;
  for(const b of document.querySelectorAll('[data-tab]'))b.setAttribute('aria-selected',String(b.dataset.tab===t));
  if(t==='draw')ed.setTool(ed.tool==='erase'?'erase':'draw');else if(ed.tool!=='move')ed.setTool('move');
  if(t!=='move'&&ed.selected&&t!=='draw')ed.deselect();
  renderPanel();
}
function syncTools(){
  const sel=ed.selected,stamp=sel===ed.stamp,q=k=>document.querySelector(`[data-do="${k}"]`);
  q('undo').disabled=!ed.canUndo;q('redo').disabled=!ed.canRedo;
  for(const k of ['dup','front','back','del'])q(k).disabled=!sel||stamp;
  if(sel&&tab!=='move'){tab='move';for(const b of document.querySelectorAll('[data-tab]'))b.setAttribute('aria-selected',String(b.dataset.tab==='move'));}
}
const swatches=(name,cur)=>`<div class="swatches" role="group" aria-label="Màu">${COLORS.map(c=>`<button type="button" class="sw${c===cur?' on':''}" style="--c:${c}" data-${name}="${c}" aria-label="Màu ${c}" aria-pressed="${c===cur}"></button>`).join('')}<label class="sw pick" aria-label="Chọn màu khác"><input type="color" data-${name}-pick value="${esc(cur||'#ffffff')}"></label></div>`;
const range=(name,label,min,max,step,val)=>`<label class="range"><span>${label}</span><input type="range" data-range="${name}" min="${min}" max="${max}" step="${step}" value="${val}"></label>`;

function renderPanel(){
  const p=$('#panel'),sel=ed.selected;panelFor=sel;
  if(tab==='move'){
    if(!sel){p.innerHTML=`<p class="hint">Chạm một hình để chọn. Kéo để di chuyển, kéo nút <b>⤡</b> ở góc (hoặc dùng hai ngón) để phóng to và xoay.</p><button type="button" class="btn ghost sm" data-do="stamp">✏️ Chỉnh nhãn @${esc(me.account.username)}</button>`;return;}
    if(sel===ed.stamp){p.innerHTML=`<p class="hint">Nhãn tên tài khoản luôn có trên sticker. Bạn kéo nó tới chỗ hợp ý được.</p>${range('stamp','Cỡ nhãn',.8,2.2,.05,sel.s)}<div class="row"><button type="button" class="chip${sel.dark?'':' on'}" data-stamp-dark="0">Nhãn sáng</button><button type="button" class="chip${sel.dark?' on':''}" data-stamp-dark="1">Nhãn tối</button></div>`;return;}
    const common=range('s','Cỡ',.08,Math.max(4,sel.s*1.5).toFixed(2),.01,sel.s)+range('rot','Xoay',-180,180,1,Math.round(sel.rot*180/Math.PI));
    if(sel.type==='text')p.innerHTML=`<label class="field"><span>Chữ</span><textarea data-text rows="2" maxlength="80">${esc(sel.text)}</textarea></label>${fontChips(sel.font)}${swatches('color',sel.color)}<p class="small">Viền chữ</p>${swatches('outline',sel.outline)}${range('ow','Độ dày viền',0,16,1,sel.ow)}${common}`;
    else if(sel.type==='image')p.innerHTML=`<div class="row"><button type="button" class="chip${sel.mask==='none'?' on':''}" data-mask="none">⬜ Vuông</button><button type="button" class="chip${sel.mask==='round'?' on':''}" data-mask="round">▢ Bo góc</button><button type="button" class="chip${sel.mask==='circle'?' on':''}" data-mask="circle">⚪ Tròn</button><button type="button" class="chip" data-do="flip">↔️ Lật</button><button type="button" class="chip" data-do="nobg">✂️ Xóa nền</button></div>${common}`;
    else if(sel.type==='shape')p.innerHTML=`${swatches('color',sel.color)}<p class="small">Viền</p>${swatches('outline',sel.outline)}${range('ow','Độ dày viền',0,16,1,sel.ow)}${common}`;
    else p.innerHTML=common;
    return;
  }
  if(tab==='draw'){const b=ed.brush,er=ed.tool==='erase';
    p.innerHTML=`<div class="row"><button type="button" class="chip${er?'':' on'}" data-brush-mode="draw">🖌️ Bút</button><button type="button" class="chip${er?' on':''}" data-brush-mode="erase">🧽 Tẩy</button></div>${er?'':swatches('brush',b.color)}${range('brush','Cỡ nét',2,60,1,b.size)}<p class="hint">Vẽ thẳng lên khung. Bấm ↶ nếu lỡ tay.</p>`;return;}
  if(tab==='text'){p.innerHTML=`<label class="field"><span>Chữ của bạn</span><textarea id="newtext" rows="2" maxlength="80" placeholder="Gõ chữ rồi bấm Thêm"></textarea></label><button type="button" class="btn primary sm" data-do="addtext">➕ Thêm chữ</button><p class="small">Hoặc chọn nhanh:</p><div class="row">${PHRASES.map(t=>`<button type="button" class="chip" data-phrase="${esc(t)}">${esc(t)}</button>`).join('')}</div>`;return;}
  if(tab==='deco'){p.innerHTML=`<div class="emoji" role="group" aria-label="Biểu tượng">${EMOJI.map(e=>`<button type="button" data-emoji="${e}" aria-label="${e}">${e}</button>`).join('')}</div><p class="small">Hình vẽ sẵn (màu đổi được sau khi thêm):</p><div class="row">${Object.entries(SHAPES).map(([k,v])=>`<button type="button" class="chip" data-shape="${k}">${v}</button>`).join('')}</div>`;return;}
  if(tab==='photo'){p.innerHTML=`<button type="button" class="btn primary" data-do="pick">🖼️ Chọn ảnh từ máy</button><p class="hint">Ảnh được thu nhỏ ngay trên máy bạn. Sau khi thêm: kéo, phóng to để cắt khung, bấm <b>Xóa nền</b> nếu ảnh có nền trơn, hoặc cắt tròn cho dễ thương.</p>`;return;}
  if(tab==='bg'){const bg=ed.background;
    p.innerHTML=`<p class="small">Nền sticker</p><div class="row"><button type="button" class="chip${bg?'':' on'}" data-bg="">🏁 Trong suốt</button></div>${swatches('bg',bg)}<p class="small">Viền trắng quanh hình (kiểu sticker dán)</p><div class="row"><button type="button" class="chip${ed.border?' on':''}" data-border="1">Có viền</button><button type="button" class="chip${ed.border?'':' on'}" data-border="0">Không viền</button></div><button type="button" class="btn ghost sm danger" data-do="clear">🗑 Xóa hết làm lại</button>`;}
}
const fontChips=cur=>`<div class="row">${Object.entries(FONTS).map(([k,[label]])=>`<button type="button" class="chip font-${k}${k===cur?' on':''}" data-font="${k}">${label}</button>`).join('')}</div>`;

// ---- events ---------------------------------------------------------------------------------------
document.addEventListener('click',async e=>{
  const b=e.target.closest('button,[data-do]');if(!b||b.disabled)return;
  const d=b.dataset,act=d.do;
  if(act==='retry'){refresh();return;}
  if(!ed)return;
  if(d.tab){setTab(d.tab);return;}
  if(act==='undo')ed.undo();else if(act==='redo')ed.redo();else if(act==='del')ed.remove();else if(act==='dup')ed.duplicate();
  else if(act==='front')ed.order(1);else if(act==='back')ed.order(-1);
  else if(act==='stamp')ed.selectStamp();
  else if(act==='flip')ed.update({flip:!ed.selected.flip});
  else if(act==='nobg'){const share=ed.removeBackground();say(share>.02?'Đã xóa nền. Chưa ưng thì bấm ↶ nhé.':'Không thấy nền trơn quanh ảnh để xóa.',share>.02?'good':'');}
  else if(act==='pick')$('#file').click();
  else if(act==='addtext'){const t=$('#newtext').value.trim();if(!t){$('#newtext').focus();return;}ed.addText({text:t});}
  else if(act==='clear'){if(confirm('Xóa hết để làm lại từ đầu?'))ed.clear();}
  else if(act==='download')download();
  else if(act==='share')share();
  else if(act==='submit')submit();
  else if(act==='copy')copy();
  else if(d.phrase)ed.addText({text:d.phrase});
  else if(d.emoji)ed.addEmoji(d.emoji);
  else if(d.shape)ed.addShape(d.shape,COLORS[2+Math.floor(Math.random()*8)]);
  else if(d.font)ed.update({font:d.font});
  else if(d.mask)ed.update({mask:d.mask});
  else if(d.color)ed.update({color:d.color});
  else if(d.outline)ed.update({outline:d.outline,ow:ed.selected.ow||6});
  else if(d.brush)ed.setBrush({color:d.brush});
  else if(d.brushMode){ed.setTool(d.brushMode);}
  else if(d.bg!=null)ed.setBackground(d.bg);
  else if(d.border)ed.setBorder(d.border==='1');
  else if(d.stampDark)ed.update({dark:d.stampDark==='1'});
  else return;
  if(d.font||d.mask||d.color||d.outline||d.brush||d.brushMode||d.bg!=null||d.border||d.stampDark)renderPanel();
});
document.addEventListener('input',e=>{
  const t=e.target;if(!ed)return;
  if(t.dataset.range){const v=Number(t.value),k=t.dataset.range;
    if(k==='s')ed.update({s:v},'s');else if(k==='rot')ed.update({rot:v*Math.PI/180},'rot');else if(k==='ow')ed.update({ow:v},'ow');
    else if(k==='brush')ed.setBrush({size:v});else if(k==='stamp')ed.update({s:v},'stamp');return;}
  if(t.hasAttribute('data-text')){ed.update({text:t.value||' '},'text');return;}
  for(const k of ['color','outline','brush','bg'])if(t.hasAttribute(`data-${k}-pick`)){
    if(k==='brush')ed.setBrush({color:t.value});else if(k==='bg')ed.setBackground(t.value);else ed.update({[k]:t.value},k);}
});
$('#file').addEventListener('change',async e=>{
  const f=e.target.files?.[0];e.target.value='';if(!f||!ed)return;
  say('Đang mở ảnh…');
  try{ed.addPicture(await loadPicture(f));setTab('move');say('Đã thêm ảnh. Kéo, phóng to hay cắt tròn tùy bạn.','good');}
  catch(err){say(err.message||'Không mở được ảnh này.','bad');}
});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&(!me||!me.account))refresh();});
window.addEventListener('beforeunload',e=>{if(ed&&ed.canUndo&&!sending&&!saved){e.preventDefault();e.returnValue='';}});

// ---- out: download, share, submit -----------------------------------------------------------------
const fileName=()=>`sticker-${me?.account?.username||'pho'}.png`;
async function download(){
  if(ed.empty){say('Sticker đang trống. Vẽ hay thêm gì đó nhé.','bad');return;}
  const blob=await ed.png(),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=fileName();document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
  saved=true;
  say('Đã tải về. Đăng vào nhóm Facebook kèm chú thích bên dưới nhé!','good');
}
async function share(){
  if(ed.empty){say('Sticker đang trống. Vẽ hay thêm gì đó nhé.','bad');return;}
  const file=new File([await ed.png()],fileName(),{type:'image/png'});
  try{await navigator.share({files:[file],text:caption()});saved=true;}catch(e){if(e?.name!=='AbortError')say('Chưa chia sẻ được. Bấm Tải về rồi đăng tay nhé.','bad');}
}
async function copy(){
  try{await navigator.clipboard.writeText(caption());say('Đã chép chú thích.','good');}
  catch{const r=document.createRange();r.selectNodeContents($('#cap-text'));const s=getSelection();s.removeAllRanges();s.addRange(r);say('Giữ để chép chú thích nhé.');}
}
const dataURL=blob=>new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=()=>no(new Error('Không đọc được ảnh.'));r.readAsDataURL(blob);});
async function submit(){
  if(sending||!me?.can)return;
  if(ed.empty){say('Sticker đang trống. Vẽ hay thêm gì đó nhé.','bad');return;}
  const left=me.rules.max-me.entries.length;
  if(!confirm(`Nộp sticker này? Nộp rồi không sửa được (bạn còn ${left} lượt).`))return;
  sending=true;syncSend();say('Đang nộp…');
  try{
    ed.deselect();
    const out=await ed.export(me.rules.max_bytes);
    if(out.tooBig){say('Sticker nặng quá 400 KB. Bớt ảnh chụp hay thu nhỏ ảnh một chút rồi nộp lại nhé.','bad');return;}
    const res=await getJSON('/api/sticker/submit',{method:'POST',timeout:45000,headers:{'Content-Type':'application/json','X-Game-CSRF':me.csrf||''},body:JSON.stringify({image:await dataURL(out.blob)})});
    saved=true;
    say(res.joined?`Đã nộp! Quà tham gia ${xu(res.joined.coins)} vào ví khi bạn quay lại phố. Giờ tải về và đăng lên nhóm nhé!`:'Đã nộp! Giờ tải về và đăng lên nhóm Facebook nhé!','good');
    await refresh();
  }catch(e){say(e.message||'Chưa nộp được. Thử lại nhé.','bad');if(e.status===401||e.status===403)refresh();}
  finally{sending=false;if(me)syncSend();}
}

refresh();
