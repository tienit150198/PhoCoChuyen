/** 🍳 Nấu cơm tối ở nhà (game/home_cook.py, feedback #485): a small cooking game in the evening sheet.
 * Chọn món → Đi chợ (Chợ sáng Mây, or the fridge) → Sơ chế (tap to cut) → Nấu (stop the flame needle in the green
 * zone) → Nêm (pick the seasonings) → Dọn mâm. Only the last tap talks to the server (jr_cook_done {dish, heat,
 * spices}); it charges the market, scores and feeds. Every number, price and rule comes from state.needs.evening.cook.
 * Lazy: app.js loads it from the evening sheet (needs.js ndCook). */
import {escapeHTML as esc,icon} from '../icons.js';

const S={env:null,dlg:null,step:'menu',dish:null,basket:new Set(),prep:{},heat:null,pos:0,dir:1,raf:0,last:0,spices:new Set(),busy:false,result:null};
const TAPS=3;            // taps per cutting job
const SWEEP=1300;        // ms for the needle to cross the gauge once
const STEPS=[['market','Đi chợ'],['prep','Sơ chế'],['cook','Nấu'],['season','Nêm'],['plate','Dọn mâm']];
let css=null;
function styles(){return css??=new Promise(resolve=>{const el=document.createElement('link');el.rel='stylesheet';el.href=globalThis.__mnlBoot?.asset?.('/css/cook-night.css')||'/css/cook-night.css';el.onload=el.onerror=resolve;document.head.append(el);setTimeout(resolve,1500);});}
const view=()=>S.env?.api?.state?.needs?.evening?.cook||null;
const dish=()=>view()?.dishes?.find(d=>d.id===S.dish)||null;
const stars=n=>'★'.repeat(n)+'☆'.repeat(Math.max(0,3-n));
const btn=(label,op,data={},cls='',disabled=false)=>`<button type="button" class="btn ${cls}" data-ck="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(String(v))}"`).join('')}${disabled?' disabled':''}>${label}</button>`;

function stepper(){
  const at=STEPS.findIndex(s=>s[0]===S.step);
  return `<ol class="ck-steps" aria-label="Các bước nấu">${STEPS.map(([id,name],i)=>`<li class="${i<at?'done':i===at?'on':''}"${i===at?' aria-current="step"':''}><span>${i<at?'✓':i+1}</span><small>${esc(name)}</small></li>`).join('')}</ol>`;
}
function menu(V){
  const cards=V.dishes.map(d=>`<button type="button" class="ck-dish" data-ck="pick" data-id="${esc(d.id)}"${d.ok?'':' disabled'}>
    <span class="ck-dish-emoji" aria-hidden="true">${d.emoji}</span><b>${esc(d.name)}</b>
    <small>${d.ok?`${d.price} xu`:'Chưa đủ xu'} · ${d.minutes} phút</small><small class="ck-fire">🔥 ${esc(d.fire)}</small>
    ${d.best?`<small class="ck-best" aria-label="Kỷ lục ${d.best} sao">${stars(d.best)}</small>`:''}</button>`).join('');
  return `<p class="ck-lead">Tối nay nấu món gì?${V.spouse?` <span>Nấu cho ${esc(V.spouse)} cùng ăn.</span>`:''}</p><div class="ck-dishes">${cards}</div>
    <p class="ck-fine">Nấu xong là bữa tối luôn: no bụng hơn, ngon thì thêm tinh thần.${V.fridge?' Có tủ lạnh: lấy sẵn trứng, rau, bớt 1 xu.':''}</p>`;
}
function market(d){
  const all=d.items.every((_,i)=>S.basket.has(i));
  return `<p class="ck-lead">🛒 Chợ sáng Mây: lấy đủ nguyên liệu</p>
    <div class="ck-items">${d.items.map(([e,n],i)=>`<button type="button" class="ck-item${S.basket.has(i)?' on':''}" data-ck="take" data-i="${i}" aria-pressed="${S.basket.has(i)}"><span aria-hidden="true">${e}</span><small>${esc(n)}</small>${S.basket.has(i)?'<i aria-hidden="true">✓</i>':''}</button>`).join('')}</div>
    <div class="ck-card"><b>📖 ${esc(d.name)}</b><small>🔥 ${esc(d.fire)} · nêm: ${d.spices.map(k=>esc(spice(k)?.name||k)).join(', ')}</small></div>
    <div class="ck-foot">${btn('‹ Đổi món','menu',{},'ghost')}${btn(`Mua · ${d.price} xu ›`,'go',{to:'prep'},'primary',!all)}</div>`;
}
function prep(d){
  const done=d.prep.every((_,i)=>(S.prep[i]||0)>=TAPS);
  return `<p class="ck-lead">🔪 Sơ chế: chạm để làm từng việc</p>
    <div class="ck-board">${d.prep.map((name,i)=>{const n=Math.min(TAPS,S.prep[i]||0);
      return `<button type="button" class="ck-cut${n>=TAPS?' on':''}" data-ck="cut" data-i="${i}"${n>=TAPS?' disabled':''}><b>${esc(name)}</b><span class="ck-dots" aria-label="${n}/${TAPS}">${'●'.repeat(n)}${'○'.repeat(TAPS-n)}</span></button>`;}).join('')}</div>
    <div class="ck-foot"><span></span>${btn('Lên bếp ›','go',{to:'cook'},'primary',!done)}</div>`;
}
function gauge(d){
  const [lo,hi]=d.heat,near=view()?.near??10;
  return `<div class="ck-gauge" role="img" aria-label="Thanh lửa: vùng xanh từ ${lo} đến ${hi}">
    <i class="ck-near" style="left:${Math.max(0,lo-near)}%;width:${Math.min(100,hi+near)-Math.max(0,lo-near)}%"></i>
    <i class="ck-zone" style="left:${lo}%;width:${hi-lo}%"></i>
    <b class="ck-needle" style="left:${S.heat??S.pos}%"></b></div>
    <div class="ck-scale" aria-hidden="true"><span>Sống</span><span>Cháy</span></div>`;
}
function heatWord(d,h){const [lo,hi]=d.heat,near=view()?.near??10;return h>=lo&&h<=hi?['good','Vừa chuẩn!']:h>=lo-near&&h<=hi+near?['mid','Hơi lệch chút']:h<lo?['bad','Còn sống quá']:['bad','Khét mất rồi'];}
function cook(d){
  const stopped=S.heat!=null,[tone,word]=stopped?heatWord(d,S.heat):['',''];
  return `<p class="ck-lead">🔥 ${esc(d.fire)}: tắt bếp khi kim vào vùng xanh</p>
    <div class="ck-pan${stopped?'':' hot'}" aria-hidden="true"><span>🍳</span><em>${d.emoji}</em></div>${gauge(d)}
    ${stopped?`<p class="ck-say ${tone}" role="status">${esc(word)}</p>`:''}
    <div class="ck-foot"><span></span>${stopped?btn('Nêm nếm ›','go',{to:'season'},'primary'):btn('🔥 Tắt bếp!','stop',{},'primary big')}</div>`;
}
const spice=k=>view()?.spices?.find(s=>s.id===k);
function season(d){
  return `<p class="ck-lead">🧂 Nêm nếm cho vừa miệng</p>
    <div class="ck-rack">${(view()?.spices||[]).map(s=>`<button type="button" class="ck-spice${S.spices.has(s.id)?' on':''}" data-ck="spice" data-id="${esc(s.id)}" aria-pressed="${S.spices.has(s.id)}"><span aria-hidden="true">${s.emoji}</span><small>${esc(s.name)}</small></button>`).join('')}</div>
    <details class="ck-recipe"><summary>📖 Xem lại công thức</summary><p>${esc(d.name)}: ${d.spices.map(k=>esc(spice(k)?.name||k)).join(', ')}.</p></details>
    <div class="ck-foot"><span></span>${btn('Bày ra đĩa ›','go',{to:'plate'},'primary',!S.spices.size)}</div>`;
}
function plate(d){
  if(S.result){const r=S.result;
    return `<div class="ck-done"><span class="ck-tray" aria-hidden="true">${d.emoji}</span><p class="ck-stars" aria-label="${r.stars} sao">${stars(r.stars)}</p>
      <p>${esc(r.message||'')}</p></div><div class="ck-foot"><span></span>${btn('🌙 Xong, đi ngủ','close',{},'primary')}</div>`;}
  return `<p class="ck-lead">🍽️ Bày ra mâm, mời cả nhà</p><div class="ck-done"><span class="ck-tray" aria-hidden="true">${d.emoji}</span><p>${esc(d.say)}</p></div>
    <div class="ck-foot"><span></span>${btn(S.busy?'Đang dọn…':'🍽️ Dọn mâm','serve',{},'primary big',S.busy)}</div>`;
}
function render(){
  if(!S.dlg)return;
  const V=view(),d=dish(),body=S.dlg.querySelector('.ck-body');
  if(!V){body.innerHTML='<p>Chưa tới buổi tối.</p>';return;}
  if(!S.result&&!V.ok&&V.done){body.innerHTML=`<div class="ck-done"><span class="ck-tray" aria-hidden="true">${V.done.emoji}</span><p class="ck-stars">${stars(V.done.stars)}</p><p>Tối nay đã nấu ${esc(V.done.name)}.</p></div><div class="ck-foot"><span></span>${btn('Đóng','close',{},'primary')}</div>`;return;}
  if(!S.result&&!V.ok){body.innerHTML=`<p class="ck-lead">${esc(V.why||'Chưa vào bếp được.')}</p><div class="ck-foot"><span></span>${btn('Đóng','close',{},'primary')}</div>`;return;}
  if(S.step==='menu'||!d){body.innerHTML=menu(V);return;}
  body.innerHTML=stepper()+(S.step==='market'?market(d):S.step==='prep'?prep(d):S.step==='cook'?cook(d):S.step==='season'?season(d):plate(d));
}
function frame(t){
  if(S.step!=='cook'||S.heat!=null||!S.dlg?.open){S.raf=0;return;}
  const dt=S.last?Math.min(64,t-S.last):16;S.last=t;
  S.pos+=S.dir*dt*100/SWEEP;
  if(S.pos>=100){S.pos=100;S.dir=-1;}else if(S.pos<=0){S.pos=0;S.dir=1;}
  const n=S.dlg.querySelector('.ck-needle');if(n)n.style.left=S.pos+'%';
  S.raf=requestAnimationFrame(frame);
}
function startNeedle(){cancelAnimationFrame(S.raf);S.pos=0;S.dir=1;S.last=0;S.raf=requestAnimationFrame(frame);}
async function act(op,data){
  const d=dish();
  switch(op){
    case'close':S.dlg.close();return;
    case'menu':S.step='menu';S.dish=null;break;
    case'pick':S.dish=data.id;S.step='market';S.basket=new Set();S.prep={};S.heat=null;S.spices=new Set();S.result=null;break;
    case'take':{const i=Number(data.i);S.basket.has(i)?S.basket.delete(i):S.basket.add(i);break;}
    case'cut':{const i=Number(data.i);S.prep[i]=Math.min(TAPS,(S.prep[i]||0)+1);S.env.sound?.click?.();break;}
    case'go':S.step=data.to;if(S.step==='cook'){S.heat=null;render();startNeedle();return;}break;
    case'stop':S.heat=Math.round(S.pos);cancelAnimationFrame(S.raf);S.raf=0;break;
    case'spice':S.spices.has(data.id)?S.spices.delete(data.id):S.spices.add(data.id);break;
    case'serve':{
      if(S.busy||!d)return;S.busy=true;render();
      const r=await S.env.cmd('jr_cook_done',{dish:d.id,heat:S.heat??0,spices:[...S.spices]},{quiet:true});
      S.busy=false;
      if(r){S.result={stars:r.cook?.stars||1,message:r.message};S.env.renderSheet?.(false);}
      break;
    }
    default:return;
  }
  render();
}
/** Open the kitchen (env: app.js env()). */
export async function openCook(env){
  S.env=env;await styles();
  S.step='menu';S.dish=null;S.result=null;S.busy=false;S.heat=null;
  if(!S.dlg){
    const d=document.createElement('dialog');d.className='sheet v4-sheet medium ck-sheet';d.setAttribute('aria-labelledby','ck-title');
    d.innerHTML=`<header class="sheet-head"><div class="grow"><span class="eyebrow">BUỔI TỐI</span><h2 id="ck-title">🍳 Vào bếp</h2></div><button type="button" class="icon-btn" data-ck="close" aria-label="Đóng">${icon('x',21)}</button></header><div class="sheet-body ck-body"></div>`;
    document.body.append(d);S.dlg=d;
    d.addEventListener('click',e=>{if(e.target===d){d.close();return;}const el=e.target.closest('[data-ck]');if(el&&!el.disabled){e.preventDefault();act(el.dataset.ck,el.dataset);}});
    d.addEventListener('close',()=>{cancelAnimationFrame(S.raf);S.raf=0;});
  }
  if(!S.dlg.open)S.dlg.showModal();
  render();
}
