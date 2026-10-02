/** 🎟️ Vé số cào at the fair: dì Hai's tray, the ticket and its silver layer, scratched off by hand (a finger or the
 * mouse) on a canvas. The ticket is decided and paid on the server when it is bought (game/fair_scratch.py, fair_xs);
 * this file only lets the player uncover it: the wallet shown leaves the prize out (hold) and the result line waits
 * until ~REVEAL of the silver is gone (or "Cào hết"), then the rest falls away.
 * fair.js owns the dialog and passes its helpers in (setup); its render() patches the page in place and calls mount()
 * after: the silver lives in a data-fh-live slot keyed by the ticket, so a render never repaints it; when the slot is
 * new (another ticket, back from another stall) mount() paints it and replays the strokes scratched so far. */
import {t as tr} from './i18n.js';

const SELLER={name:'Dì Hai vé số',emoji:'👩🏽',
  idle:['Vé số cào đây! Cào trúng ăn liền nè con!','Ba ô giống nhau là trúng, cào thử một tấm đi!','Vé mới về, toàn vé đẹp không à!'],
  fresh:['Cào từ từ thôi, coi kỹ từng ô nha!','Hồi hộp chưa? Dì cũng hồi hộp nè!','Cào đi con, vé này dì thấy đẹp lắm!'],
  win:['Trúng rồi! Dì nói vé đẹp mà!','Hên quá trời! Mua thêm tấm nữa hông?','Đó, ba ô y chang, dì chung liền!'],
  big:['Trời đất! Trúng lớn rồi bà con ơi!','Trúng đậm luôn! Dì bán vé bao năm mới thấy!'],
  back:['Hoàn vé rồi, coi như cào chơi khỏi tốn!','Huề vốn, cào tấm khác thử coi!'],
  lose:['Tiếc ghê, chưa trúng. Tấm sau chắc trúng!','Không sao, vui là chính nha con!','Suýt nữa rồi, chỉ thiếu một ô thôi!']};
const G=20;          // the coverage grid (G × G) that measures how much silver is gone
const REVEAL=.7;     // this much scratched: the rest falls away
const BRUSH=.085;    // the brush's radius, a share of the silver's width (at least MIN_R css px)
const MIN_R=16;

export function setup(ctx){
  const {S,F,btn,say,xu,esc,send,render,sfx,pick,reduce}=ctx;
  const D=S.xs={tier:5,t:null,done:false,cov:null,pct:0,strokes:[],say:'',buying:false,fading:false,sound:0};
  const R=()=>F().scratch||null;

  /** Prize xu already in the wallet but not yet scratched open (fair.js takes it off what it shows). */
  const hold=()=>D.t&&!D.done?D.t.prize+(D.t.bonus||0):0;   // 🔥 x3 day: the bonus waits too
  const live=()=>!!D.t&&!D.done;

  function card(){
    const t=D.t,r=R(),n=r?.cells||9;
    if(!t)return `<div class="fh-xs-card t${D.tier} blank" data-fh-key="xs-blank"><div class="fh-xs-top"><b>${esc(r?.names?.[D.tier]||'Vé số cào')}</b><span>${xu(D.tier)}</span></div>
      <div class="fh-xs-play"><div class="fh-xs-grid">${'<span class="fh-xs-cell"></span>'.repeat(n)}</div><div class="fh-xs-silver still"><span>${esc('Mua vé rồi cào nha')}</span></div></div>
      <div class="fh-xs-foot">${esc(`Cào trúng ${r?.match||3} ô giống nhau là trúng số tiền đó`)}</div></div>`;
    const cells=t.cells.map((v,i)=>`<span class="fh-xs-cell${D.done&&t.hits.includes(i)?' hit':''}${v>=t.price*10?' big':''}"><b>${v}</b><small>xu</small></span>`).join('');
    const label=D.done?`Vé đã cào: ${t.cells.map(v=>xu(v)).join(', ')}`:'Lớp bạc phủ kín vé. Kéo ngón tay hoặc chuột trên lớp bạc để cào.';
    return `<div class="fh-xs-card t${t.price}${D.done?' done':''}${D.done&&t.prize?' win':''}" data-fh-key="xs-card-${t.id}">
      <div class="fh-xs-top"><b>${esc(t.name||'Vé số cào')}</b><span>${xu(t.price)}</span></div>
      <div class="fh-xs-play"><div class="fh-xs-grid" role="img" aria-label="${esc(label)}">${cells}</div>
        ${D.done?'':`<div class="fh-xs-silver${D.fading?' gone':''}" data-fh-live data-fh-key="xs-silver-${t.id}"><canvas class="fh-xs-cv" role="img" aria-label="${esc('Lớp bạc, cào để xem')}"></canvas></div>`}</div>
      <div class="fh-xs-foot">${esc(`Cào trúng ${R()?.match||3} ô giống nhau là trúng số tiền đó`)}</div></div>`;
  }
  function result(){
    if(!D.t||!D.done)return '';
    const t=D.t;
    if(!t.prize)return `<div class="fh-result bad"><b>Chưa trúng</b><small>−${xu(t.price)}</small></div>`;
    if(t.prize===t.price)return `<div class="fh-result good"><b>Hoàn vé ${xu(t.prize)}</b><small>Ba ô đúng bằng giá vé</small></div>`;
    return `<div class="fh-result good"><b>🎉 Trúng ${xu(t.prize)}!</b><small>Lời ${xu(t.net)} · gấp ${t.mult} lần giá vé${t.bonus?` · 🔥 x3 thêm ${xu(t.bonus)}`:''}</small></div>`;
  }
  function view(){
    const f=F(),r=R(),tiers=r?.tiers||[2,5,10,20],wallet=f.wallet||0,on=live(),busy=D.buying||S.busy;
    if(!tiers.includes(D.tier))D.tier=tiers[1]||tiers[0];
    if(!D.say)D.say=pick(SELLER.idle);
    const shown=wallet-hold(),why=!on&&D.tier>shown?'Ví không đủ xu':'';
    const mults=r?.mults||[1,2,3,5,10,20,50],price=on?D.t.price:D.tier;
    const go=on?`<div class="fh-go"><span>Đã cào <b class="fh-xs-pct">${Math.round(D.pct*100)}%</b></span>${btn('🪙 Cào hết','xsall',{},'cream big',' data-fh-key="xsall"')}</div>`
      :`<div class="fh-go"><span>Vé <b>${xu(D.tier)}</b> · trúng đến <b>${xu(D.tier*mults[mults.length-1])}</b></span>${btn(busy?'Đang lấy vé…':'🎟️ Mua vé','xsbuy',{},'primary big',busy||why?' disabled data-fh-key="xsbuy"':' data-fh-key="xsbuy"')}</div>`;
    return `<section class="fh-stall fh-xs" aria-label="Vé số cào">
      ${say(SELLER,D.say)}
      ${card()}${result()}
      <div class="fh-chips" role="group" aria-label="Loại vé"><span>Vé</span>${tiers.map(v=>`<button type="button" class="fh-chip${D.tier===v?' on':''}" data-fh="xstier" data-v="${v}" aria-pressed="${D.tier===v}" data-fh-key="xst-${v}"${on||busy||v>shown?' disabled':''}${v>shown?' title="Ví không đủ xu"':''}>${v}</button>`).join('')}</div>
      ${go}
      ${why&&!busy?`<p class="fh-why">${esc(why)}: chọn vé rẻ hơn nha.</p>`:''}
      <details class="fh-how" data-fh-key="xshow"><summary>Cơ cấu giải vé ${xu(price)}</summary><ul>${mults.map(m=>`<li>3 ô <b>${xu(m*price)}</b> → trúng <b>${xu(m*price)}</b>${m===1?' (hoàn vé)':''}</li>`).join('')}</ul><p class="small muted">Mỗi vé trúng nhiều nhất một giải. Không có 3 ô giống nhau là vé không trúng.</p></details>
      <p class="fh-rule">Chọn loại vé, mua rồi cào lớp bạc bằng ngón tay (hoặc kéo chuột). Ba ô cùng một số tiền là trúng đúng số tiền đó, tiền thưởng vô ví liền.</p>
    </section>`;
  }

  /* ---- the silver: painted on a canvas, scratched with destination-out strokes ---- */
  function seeded(id){let x=(id>>>0)||1;return ()=>{x^=x<<13;x>>>=0;x^=x>>>17;x^=x<<5;x>>>=0;return x/4294967296;};}
  function paint(cv){
    const box=cv.getBoundingClientRect(),dpr=Math.min(2,globalThis.devicePixelRatio||1),w=Math.max(1,box.width),h=Math.max(1,box.height);
    cv.width=Math.round(w*dpr);cv.height=Math.round(h*dpr);
    const c=cv.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.globalCompositeOperation='source-over';
    const g=c.createLinearGradient(0,0,w,h);g.addColorStop(0,'#aeb4bd');g.addColorStop(.45,'#e6e9ed');g.addColorStop(.55,'#d5d9df');g.addColorStop(1,'#9fa6b0');
    c.fillStyle=g;c.fillRect(0,0,w,h);
    const rnd=seeded(D.t?.id||1);
    for(let i=0;i<260;i++){c.fillStyle=rnd()<.5?'#ffffff66':'#7d848f44';c.fillRect(rnd()*w,rnd()*h,1+rnd()*2,1+rnd()*2);}
    c.fillStyle='#7d848f';c.textAlign='center';c.textBaseline='middle';
    c.font=`800 ${Math.round(Math.min(w,h)*.085)}px system-ui,sans-serif`;
    c.fillText(tr('CÀO Ở ĐÂY'),w/2,h/2);
    c.font=`${Math.round(Math.min(w,h)*.07)}px system-ui,sans-serif`;
    for(let i=0;i<3;i++){c.fillText('🪙',w*(.2+.3*i),h*.22);c.fillText('🍀',w*(.2+.3*i),h*.8);}
    c.globalCompositeOperation='destination-out';c.lineCap=c.lineJoin='round';
    cv._w=w;cv._h=h;cv._r=Math.max(MIN_R,w*BRUSH);
    for(const s of D.strokes)stroke(cv,s,false);   // what was scratched before this canvas
  }
  /** One stroke [[x,y],…] in silver units (0..1): erase it, and (when new) count what it uncovers. */
  function stroke(cv,s,count=true){
    const c=cv.getContext('2d'),w=cv._w,h=cv._h,r=cv._r;
    c.lineWidth=r*2;c.beginPath();c.moveTo(s[0][0]*w,s[0][1]*h);
    if(s.length===1)c.lineTo(s[0][0]*w+.1,s[0][1]*h);
    for(let i=1;i<s.length;i++)c.lineTo(s[i][0]*w,s[i][1]*h);
    c.stroke();
    if(count)cover(s,w,h,r);
  }
  function cover(s,w,h,r){
    const cov=D.cov||(D.cov=new Uint8Array(G*G)),mark=(x,y)=>{
      const i0=Math.max(0,Math.floor((x-r)/w*G)),i1=Math.min(G-1,Math.floor((x+r)/w*G)),j0=Math.max(0,Math.floor((y-r)/h*G)),j1=Math.min(G-1,Math.floor((y+r)/h*G));
      for(let i=i0;i<=i1;i++)for(let j=j0;j<=j1;j++){const cx=(i+.5)*w/G,cy=(j+.5)*h/G;if((cx-x)**2+(cy-y)**2<=r*r)cov[j*G+i]=1;}};
    const pts=s.map(([x,y])=>[x*w,y*h]);mark(...pts[0]);
    for(let k=1;k<pts.length;k++){const [ax,ay]=pts[k-1],[bx,by]=pts[k],n=Math.ceil(Math.hypot(bx-ax,by-ay)/(r/2));for(let q=1;q<=n;q++)mark(ax+(bx-ax)*q/n,ay+(by-ay)*q/n);}
    let on=0;for(const v of cov)on+=v;D.pct=on/cov.length;
  }
  function bind(cv){
    let cur=null;
    const at=e=>{const b=cv.getBoundingClientRect();return [Math.max(0,Math.min(1,(e.clientX-b.left)/b.width)),Math.max(0,Math.min(1,(e.clientY-b.top)/b.height))];};
    const add=p=>{if(!cur||D.done||D.fading)return;const last=cur[cur.length-1];cur.push(p);stroke(cv,[last,p]);progress();
      const now=performance.now();if(now-D.sound>110){D.sound=now;sfx('scratch');}};
    cv.addEventListener('pointerdown',e=>{if(D.done||D.fading||e.button>0)return;e.preventDefault();try{cv.setPointerCapture(e.pointerId);}catch{/* fine */}
      cur=[at(e)];D.strokes.push(cur);stroke(cv,cur);progress();});
    cv.addEventListener('pointermove',e=>{if(!cur)return;e.preventDefault();const all=e.getCoalescedEvents?.();for(const ev of all?.length?all:[e])add(at(ev));});
    const end=()=>{cur=null;if(D.pct>=REVEAL)reveal();};
    cv.addEventListener('pointerup',end);cv.addEventListener('pointercancel',end);cv.addEventListener('lostpointercapture',()=>{if(cur)end();});
  }
  function progress(){
    const el=S.dlg?.querySelector('.fh-xs-pct');if(el)el.textContent=`${Math.round(D.pct*100)}%`;
    if(D.pct>=REVEAL&&!D.fading)reveal();
  }
  /** The rest of the silver falls away; then the result. */
  function reveal(){
    if(!live()||D.fading)return;
    D.fading=true;D.pct=1;
    const sv=S.dlg?.querySelector('.fh-xs-silver');if(sv)sv.classList.add('gone');
    setTimeout(()=>{
      D.fading=false;D.done=true;const t=D.t;
      D.say=pick(!t.prize?SELLER.lose:t.prize===t.price?SELLER.back:t.mult>=10?SELLER.big:SELLER.win);
      sfx(t.prize>t.price?'win':t.prize?'open':'lose');render();
      globalThis.__mnlMoneyGo?.();
    },reduce()?60:380);
  }
  /** After every render: a new silver slot gets its paint, its strokes and its finger. */
  function mount(){
    const cv=S.dlg?.querySelector('.fh-xs-cv');
    if(!cv||cv._xs)return;
    cv._xs=1;paint(cv);bind(cv);
  }
  async function buy(){
    if(D.buying||S.busy||live())return;
    const price=D.tier;if(price>(F().wallet||0))return;
    D.buying=true;S.flash=null;render();
    const r=await send('fair_xs',{price});
    D.buying=false;
    if(!r?.fair?.cells){render();return;}
    D.t={...r.fair};D.done=false;D.fading=false;D.pct=0;D.cov=null;D.strokes=[];D.say=pick(SELLER.fresh);
    sfx('open');render();
  }
  function click(op,data){
    if(op==='xstier'){const v=Number(data.v);if((R()?.tiers||[]).includes(v)&&!live())D.tier=v;render();return true;}
    if(op==='xsbuy'){buy();return true;}
    if(op==='xsall'){reveal();return true;}
    return false;
  }

  /* the "ting ting" and the read-out of the prize wait for the silver (v4/sounds.js) */
  globalThis.__mnlMoneyHold=()=>(D.buying||live())&&!!S.dlg?.open;

  /* ---- test hooks (scratch browser checks) ---- */
  globalThis.__fairScratch={state:()=>({ticket:D.t&&{...D.t},done:D.done,pct:D.pct,strokes:D.strokes.length,hold:hold()})};

  return {view,mount,click,hold,busy:()=>D.buying||D.fading,live};
}
