/** 🛃 Hải quan giữa người chơi (game/hq_ops.py): one small modal for both sides of a warehouse inspection.
 *   openDesk(env, pid?)  an officer (Kiểm tra viên and up, the customs shift open): the shops on the street, 🔎 Kiểm tra
 *                        kho, the findings read from the shop's own books, a measure to propose (📨 nhắc nộp at once;
 *                        💰 cưỡng chế / 📦 kê biên wait for a higher post or the Cục), and the proposals waiting for me.
 *   openMine(env)        the shop owner: the inspections of my shops, what was applied, 📣 Khiếu nại within 3 days.
 * The server decides everything (the findings, the grounds, the limits); nothing here says which measure is right.
 * Names come from players: always escaped. Styles: public/css/cand.css (the same small modal as the CAND's). */
import {escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const ST={clear:'✅ Không sai phạm',found:'📋 Có phát hiện',review:'⏳ Chờ duyệt',done:'✔️ Đã thi hành',rejected:'✖️ Không duyệt',void:'↩️ Đã tự nộp',reversed:'📣 Hủy sau khiếu nại'};

let cssReady=null;
function loadCss(){
  if(cssReady)return cssReady;
  if(document.querySelector('link[data-cd-css]'))return cssReady=Promise.resolve();
  const href=globalThis.__mnlBoot?.asset?.('/css/cand.css')||'/css/cand.css';
  const l=document.createElement('link');l.rel='stylesheet';l.href=href;l.dataset.cdCss='1';
  cssReady=new Promise(done=>{l.onload=l.onerror=()=>done();setTimeout(done,4000);});
  document.head.append(l);return cssReady;
}
async function call(env,op,body={}){
  const api=env.api;
  const d=await api.json(`/api/marriage/${op}`,{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify(body)});
  if(d?.state&&typeof d.revision==='number')api.accept({state:d.state,revision:d.revision});
  return d;
}

/** The customs post shown on the page (an officer on the ladder past Tập sự), as far as the page can tell. */
export function inspector(st){
  const c=st?.careers?.customs,o=c?.promo?.org;
  return Boolean(o&&!o.susp&&o.post?.id&&o.post.id!=='hq_ts');
}

const M={dlg:null,env:null,view:'',tab:'shops',data:null,rev:null,mine:null,cur:null,flash:null,busy:false};
function dialog(){
  if(M.dlg)return M.dlg;
  const d=document.createElement('dialog');d.className='cd-dialog hq-dialog';d.setAttribute('aria-labelledby','hqTitle');
  d.addEventListener('cancel',e=>{e.preventDefault();close();});
  d.addEventListener('click',e=>{const b=e.target.closest('[data-hq]');if(b&&!b.disabled)click(b.dataset.hq,b.dataset);});
  document.body.append(d);M.dlg=d;return d;
}
function close(){M.view='';M.flash=null;M.cur=null;if(M.dlg?.open)M.dlg.close();}
async function show(){
  await loadCss();const d=dialog();d.innerHTML=html();
  if(!d.open){try{d.showModal();}catch{d.setAttribute('open','');}}
}
const head=(t,sub='')=>`<header class="cd-head"><span class="cd-badge" aria-hidden="true">🛃</span><div class="grow"><h2 id="hqTitle">${t}</h2>${sub?`<p>${sub}</p>`:''}</div><button type="button" class="icon-btn" data-hq="close" aria-label="Đóng">✕</button></header>`;
const flash=()=>M.flash?`<p class="cd-flash ${M.flash.kind}" role="status">${esc(M.flash.text)}</p>`:'';
const btn=(label,op,data={},cls='')=>`<button type="button" class="btn ${cls}" data-hq="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${M.busy?' disabled':''}>${label}</button>`;
const caseRow=(c,acts='')=>`<li class="cd-row"><div class="grow"><b data-no-translate>${esc(c.name||'')}</b> <small>${esc(ST[c.status]||c.status)}${c.measure?` · ${esc((M.data?.measures||{})[c.measure]||c.measure)}`:''}</small><small>${esc(c.text)}</small>${c.paid?`<small>Đã nộp ${fmt(c.paid)} xu${c.sold?` (bán hàng tồn ${fmt(c.sold)} xu)`:''}</small>`:''}</div><div class="cd-row-acts">${acts}</div></li>`;

function deskHTML(){
  const tabs=`<div class="cd-acts two">${btn('🏪 Cửa hàng','tab',{tab:'shops'},M.tab==='shops'?'primary small':'small')}${btn('⏳ Chờ duyệt','tab',{tab:'reviews'},M.tab==='reviews'?'primary small':'small')}</div>`;
  if(M.cur){
    const c=M.cur,ms=c.found?(c.measures||Object.keys(M.data?.measures||{})):[];
    const acts=ms.map(m=>btn(esc((M.data?.measures||{})[m]||m),'propose',{measure:m},'small')).join('');
    return head('Biên bản kiểm tra',esc(c.name||''))+`<div class="cd-body">${flash()}<p class="cd-found">${esc(c.text)}</p>
      ${c.found&&c.status==='found'?`<p class="cd-hint">Chọn biện pháp theo căn cứ trên hồ sơ. Cưỡng chế, kê biên phải qua cấp trên duyệt; đề xuất không có căn cứ bị kỷ luật.</p><div class="cd-acts">${acts}</div>`:''}
      <div class="cd-acts">${btn('← Danh sách','back',{},'ghost')}</div></div>`;
  }
  if(M.tab==='reviews'){
    const r=M.rev;
    const rows=(r?.reviews||[]).map(c=>caseRow({...c,status:'review'},`${btn('✅ Duyệt','review',{case:c.id,ok:1},'small')}${btn('✖️ Không duyệt','review',{case:c.id,ok:0},'small ghost')}`)).join('');
    return head('Hải quan · kiểm tra kho')+`<div class="cd-body">${tabs}${flash()}${r?`<ul class="cd-list">${rows||'<li class="cd-line muted">Không có đề xuất nào chờ bạn duyệt.</li>'}</ul>`:'<p class="cd-line muted">Đang tải…</p>'}
      <p class="cd-hint">Chỉ duyệt đề xuất của cấp dưới; không duyệt hồ sơ của người quen, vợ chồng. Duyệt sai cũng bị kỷ luật.</p></div>`;
  }
  const d=M.data;
  if(!d)return head('Hải quan · kiểm tra kho')+`<div class="cd-body">${tabs}${flash()||'<p class="cd-line muted">Đang tải…</p>'}</div>`;
  const shops=d.shops.map(s=>`<li class="cd-row"><div class="grow"><b data-no-translate>${esc(s.name)}</b><small>${esc((s.careers||[]).join(', ')||'Cửa hàng')}</small></div><div class="cd-row-acts">${btn('🔎 Kiểm tra','inspect',{pid:s.pid},'small')}</div></li>`).join('');
  const mine=(d.cases||[]).map(c=>caseRow(c,c.status==='found'?btn('Xử lý','open',{case:c.id},'small'):'')).join('');
  return head('Hải quan · kiểm tra kho',`Hôm nay còn ${d.left} lượt kiểm tra`)+`<div class="cd-body">${tabs}${flash()}
    ${mine?`<h4>📁 Hồ sơ của bạn (7 ngày)</h4><ul class="cd-list">${mine}</ul>`:''}
    <h4>🏪 Cửa hàng trên phố</h4><ul class="cd-list">${shops||'<li class="cd-line muted">Chưa có cửa hàng nào mở hồ sơ công khai.</li>'}</ul>
    <p class="cd-hint">Mỗi cửa hàng được kiểm tra tối đa 1 lần/24 giờ; không kiểm tra người quen, vợ chồng. Kết quả đọc từ sổ sách của chính cửa hàng.</p></div>`;
}
function mineHTML(){
  const m=M.mine;
  if(!m)return head('Hồ sơ Hải quan của tôi')+`<div class="cd-body">${flash()||'<p class="cd-line muted">Đang tải…</p>'}</div>`;
  const rows=m.cases.map(c=>caseRow(c,c.can_appeal?btn('📣 Khiếu nại','appeal',{case:c.id},'small'):c.appeal===2?'<span class="cd-tag">Đã trả lời</span>':c.appeal===3?'<span class="cd-tag">Đã hoàn trả</span>':'')).join('');
  return head('Hồ sơ Hải quan của tôi','30 ngày gần đây')+`<div class="cd-body">${flash()}<ul class="cd-list">${rows||'<li class="cd-line muted">Cửa hàng của bạn chưa bị kiểm tra lần nào.</li>'}</ul>
    <p class="cd-hint">Khiếu nại trong 3 ngày sau khi biện pháp được thi hành. Cục Hải quan xem lại ngay: không có căn cứ thì hoàn trả.</p></div>`;
}
const html=()=>M.view==='mine'?mineHTML():deskHTML();

async function load(){
  const env=M.env;
  try{if(M.view==='mine')M.mine=await call(env,'hq_mine',{});else if(M.tab==='reviews')M.rev=await call(env,'hq_reviews',{});else M.data=await call(env,'hq_shops',{});}
  catch(e){M.flash={text:e.message||'Chưa tải được.',kind:'bad'};}
  if(M.view)show();
}
export async function openDesk(env,pid=null){
  M.env=env;M.view='desk';M.tab='shops';M.cur=null;M.flash=null;M.data=null;await show();
  if(pid)return click('inspect',{pid});
  load();
}
export async function openMine(env){M.env=env;M.view='mine';M.mine=null;M.flash=null;await show();load();}

async function click(op,data={}){
  if(op==='close'){close();return;}
  if(M.busy)return;
  const env=M.env;
  const run=async fn=>{M.busy=true;M.flash=null;show();try{await fn();}catch(e){M.flash={text:e.message||'Chưa làm được. Thử lại nhé.',kind:'bad'};}finally{M.busy=false;if(M.view)show();}};
  switch(op){
    case'tab':M.tab=data.tab;M.cur=null;M.flash=null;show();return load();
    case'back':M.cur=null;M.flash=null;show();return load();
    case'open':{const c=(M.data?.cases||[]).find(r=>r.id===data.case);if(c){M.cur={...c};show();}return;}
    case'inspect':return run(async()=>{const d=await call(env,'hq_inspect',{pid:data.pid});M.cur={...d.case,measures:d.measures};if(!M.data)M.data={shops:[],cases:[],left:0,measures:{}};
      if(!M.data.measures||!Object.keys(M.data.measures).length)M.data.measures={remind:'📨 Nhắc nộp thuế',collect:'💰 Cưỡng chế trích tiền nộp thuế',seize:'📦 Kê biên hàng tồn'};});
    case'propose':return run(async()=>{const d=await call(env,'hq_propose',{case:M.cur.id,measure:data.measure});M.cur=null;M.flash={text:d.message,kind:'good'};M.data=await call(env,'hq_shops',{});});
    case'review':return run(async()=>{const d=await call(env,'hq_review',{case:data.case,ok:data.ok==='1'});M.flash={text:d.message,kind:'good'};M.rev=await call(env,'hq_reviews',{});});
    case'appeal':return run(async()=>{const d=await call(env,'hq_appeal',{case:data.case});M.flash={text:d.message,kind:'good'};M.mine=await call(env,'hq_mine',{});env.api?.refresh?.().catch(()=>{});});
  }
}
