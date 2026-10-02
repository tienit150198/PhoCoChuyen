/** 🗡️ Phóng dao at the fair (in the 🎯 phi tiêu's place, tab 'dt'): anh Sáu's turning wooden board. The player pays a
 * stake, taps to throw knives into the board level after level and, after each level cleared, chooses "Dừng" (the
 * prize) or "Chơi tiếp" (a harder level, everything riding on it); now and then the next level is 🔥 x2.
 * Every rule and result is the server's (game/fair_knife.py, fair_kn_*): a level's turning comes from the server,
 * this file draws it with the same arithmetic (angleAt), sends the throw times when the level is over, and shows what
 * the server decided (its own guess only runs the animation in the meantime).
 * fair.js owns the dialog and passes its helpers in (setup); its render() patches the page in place and calls mount()
 * after: the board lives on a canvas in a data-fh-live slot, drawn by requestAnimationFrame, so a render never
 * repaints it. The whole board is the tap target (and the “Phóng!” button / Space for keyboards). */

const KEEPER={name:'Anh Sáu phóng dao',emoji:'🧔🏽',
  idle:['Phóng dao đây bà con! Cắm đủ dao vô bia là qua màn!','Bia gỗ quay vòng vòng, canh chỗ trống mà phóng nha!','Dao chạm dao là thua hết đó, phóng cho khéo!'],
  start:['Bia quay rồi, phóng đi!','Canh chỗ trống rồi chạm một cái là dao bay!','Từ từ mà phóng, đừng ham nhanh nha!'],
  clear:['Qua màn rồi! Dừng nhận thưởng hay chơi tiếp?','Tay chắc ghê! Liều thêm màn nữa không?','Đẹp! Thưởng đang chờ nè, tính sao?'],
  x2:['Màn sau x2 nè! Qua được là thưởng tăng gấp đôi!','Ối, màn sau x2! Cơ hội hiếm à nha!'],
  lost:['Dao chạm dao rồi! Tiếc ghê, lượt sau gỡ nha.','Ui, cấn dao mất rồi! Làm lại lượt mới nha.','Suýt nữa thôi! Bia quay gắt quá.'],
  late:['Để lâu quá bia ngừng quay rồi, lượt này coi như thua nha.'],
  paid:['Biết dừng đúng lúc, khôn ghê! Thưởng đây.','Thưởng đây, đếm kỹ nha!'],
  all:['Phá đảo cả mười màn! Trời ơi, tay thần đây rồi!']};
const W=300,H=360,CX=150,CY=150,BR=80;   // the canvas (css px scaled), the board's centre and radius
const TIP=BR-12,KL=64;                   // a stuck knife's tip (radius) and length
const READY_Y=CY+BR+62;                  // the waiting knife's tip
const BOUNCE_MS=700,CLEAR_MS=650;

/* ---- the board's turning: the same arithmetic as game/fair_knife.py ---- */
function table(b){
  if(b._tab)return b._tab;
  const tab=[];let t=0,th=Number(b.th0),u=null;
  for(const [ms,w0,ramp] of b.segs){const w=w0/1000,r=Math.min(ramp,ms);if(u===null)u=w;tab.push([t,th,u,w,r]);th+=turn(u,w,r,ms);t+=ms;u=w;}
  b._tab=tab;return tab;
}
function turn(u,w,ramp,tau){
  if(ramp<=0)return w*tau;
  if(tau<=ramp)return u*tau+(w-u)*tau*tau/(2*ramp);
  return u*ramp+(w-u)*ramp/2+w*(tau-ramp);
}
/** The board's angle (degrees) t ms after the level started (angle_at). */
export function angleAt(b,t){
  const tab=table(b);let i=0;
  for(let k=tab.length-1;k>=0;k--)if(tab[k][0]<=t){i=k;break;}
  const [t0,th,u,w,r]=tab[i];return th+turn(u,w,r,t-t0);
}
const mod=x=>((x%360)+360)%360;
const dist=(a,b)=>{const x=Math.abs(a-b)%360;return x>180?360-x:x;};
/** Where a knife thrown at `tap` ms sticks (board degrees), and judge(): the knives stuck and the throw that hit one
 * (-1: none), compared unrounded like the server. */
export const lands=(b,K,tap)=>mod(K.impact-angleAt(b,tap+K.fly));
export function judge(b,K,taps){
  const stuck=[];
  for(let i=0;i<Math.min(taps.length,b.need);i++){const a=lands(b,K,taps[i]);if([...b.pre,...stuck].some(x=>dist(a,x)<K.gap))return {stuck,hit:i};stuck.push(a);}
  return {stuck,hit:-1};
}

export function setup(ctx){
  const {S,F,btn,say,xu,esc,send,render,sfx,pick,reduce,serverNow}=ctx;
  const D=S.kn={stake:5,say:'',L:null,raf:0,cv:null,busy:false,last:null,chips:[],idleT0:performance.now()};
  const K=()=>F().knife||null;
  const run=()=>K()?.run||null;
  const prize=(st,k)=>{   // the server's ladder for this stake (knife.prizes; else the same rule: tenths, +1 xu at least)
    if(k<=0)return 0;
    const kk=K(),i=kk.stakes.indexOf(st);if(kk.prizes?.[i])return kk.prizes[i][k-1];
    let p=0;for(let n=0;n<k;n++)p=Math.max(Math.floor((st*kk.ladder[n]+5)/10),p+1);return p;
  };
  const theme=()=>document.documentElement.dataset.theme==='dem';

  /** The level being thrown on this screen: from the server's run (a new level, or one resumed after a reload). */
  function level(){
    const r=run();
    if(!r||r.stage!=='play'||!r.board)return D.L&&D.L.over?D.L:null;
    if(D.L?.id!==r.id){
      const k=K(),el=Math.max(0,(r.el||0)+(serverNow()-(F().now||0)*1000));   // the level's clock, a little behind the server's
      const taps=[...(r.tp||[])],j=judge(r.board,k,taps);
      D.L={id:r.id,lv:r.lv,b:r.board,t0:performance.now()-Math.min(el,(r.el||0)+120000),taps,stuck:j.stuck,flying:[],over:null,sent:false,bounce:null,at:0};
    }
    return D.L;
  }
  const live=()=>{const r=run();return !!r&&(r.stage==='play'||r.stage==='choice');};
  const busy=()=>D.busy||!!(D.L&&D.L.over&&!D.L.done);

  /* ---- the page ---- */
  function status(r,L){
    const levels=K().levels,x2=r.x2?'<em class="fh-kn-x2">🔥 x2</em>':'';
    const keep=r.prize?`<span>Đang giữ <b>${xu(r.prize)}</b></span>`:'';
    return `<div class="fh-kn-bar" data-fh-key="kn-bar"><b>Màn ${r.lv}/${levels}</b>${x2}${keep}<span>Qua màn được <b>${xu(r.win)}</b></span></div>`;
  }
  function stakeRow(){
    const k=K(),stakes=k.stakes,wallet=F().wallet||0,dis=D.busy||live();
    if(!stakes.includes(D.stake))D.stake=stakes[1]||stakes[0];
    const why=D.stake>wallet?'Ví không đủ xu':'';
    return `<div class="fh-chips" role="group" aria-label="Tiền đặt"><span>Đặt</span>${stakes.map(v=>`<button type="button" class="fh-chip${D.stake===v?' on':''}" data-fh="knstake" data-v="${v}" aria-pressed="${D.stake===v}" data-fh-key="kns-${v}"${dis||v>wallet?' disabled':''}${v>wallet?' title="Ví không đủ xu"':''}>${v}</button>`).join('')}</div>
      <div class="fh-go"><span>Đặt <b>${xu(D.stake)}</b> · qua hết ${k.levels} màn ăn <b>${xu(prize(D.stake,k.levels))}</b></span>${btn(D.busy?'Anh Sáu đang dựng bia…':'🗡️ Vào chơi','knstart',{},'primary big',D.busy||why?' disabled data-fh-key="knstart"':' data-fh-key="knstart"')}</div>
      ${why&&!D.busy?`<p class="fh-why">${esc(why)}: chọn mức đặt nhỏ hơn nha.</p>`:''}`;
  }
  function choiceCard(r){
    const next=r.lv+1;
    if(r.late)return `<div class="fh-card fh-kn-choice" data-fh-key="kn-choice"><h3>Qua màn ${r.lv}!</h3><p>Qua ngày rồi, thưởng màn trước không chơi tiếp được nữa.</p>
      ${btn(`💰 Nhận ${xu(r.prize)}`,'knstop',{},'primary big full',D.busy?' disabled data-fh-key="knstop"':' data-fh-key="knstop"')}</div>`;
    return `<div class="fh-card fh-kn-choice${r.nx?' hot':''}" data-fh-key="kn-choice">
      <h3>${r.x2?'🔥 ':''}Qua màn ${r.lv}!</h3>
      ${r.nx?`<div class="fh-kn-hot" role="status"><b>🔥 Màn sau x2</b><small>Qua màn ${next}, phần thưởng tăng thêm được nhân đôi</small></div>`:''}
      <p>Dừng bây giờ nhận <b>${xu(r.prize)}</b>. Chơi tiếp màn ${next}: qua màn được <b>${xu(r.win)}</b>, thua mất hết.</p>
      <div class="fh-kn-pick">${btn(D.busy&&D.act==='stop'?'Đang đếm tiền…':`💰 Dừng, nhận ${xu(r.prize)}`,'knstop',{},'cream big',D.busy?' disabled data-fh-key="knstop"':' data-fh-key="knstop"')}
      ${btn(D.busy&&D.act==='next'?'Đang dựng bia…':`🗡️ Chơi tiếp màn ${next}`,'knnext',{},'primary big',D.busy||!F().open?' disabled data-fh-key="knnext"':' data-fh-key="knnext"')}</div>
      ${F().open?'':'<p class="fh-why">Hội chợ đã tàn: chỉ còn nhận thưởng thôi.</p>'}</div>`;
  }
  function resultCard(){
    const r=run();
    const x=D.last||(r?.stage==='lost'?{kind:'lost',lv:r.lv,stake:r.stake,gone:r.gone}:r?.stage==='done'?{kind:'paid',paid:r.paid,lv:r.lv,stake:r.stake}:null);   // after a reload: the server's word
    if(!x)return '';
    if(x.kind==='lost')return `<div class="fh-result bad" data-fh-key="kn-res"><b>${x.late?'Hết giờ, bia ngừng quay':`Dao chạm dao! Thua ở màn ${x.lv}`}</b><small>${x.gone?`Mất ${xu(x.gone)} thưởng và ${xu(x.stake)} tiền đặt`:`Mất ${xu(x.stake)} tiền đặt`}</small></div>`;
    if(x.kind==='paid')return `<div class="fh-result good" data-fh-key="kn-res"><b>${x.all?'🏆 Phá đảo! ':'💰 '}Nhận ${xu(x.paid)}</b><small>Qua ${x.lv} màn · ${x.paid>=x.stake?`lời ${xu(x.paid-x.stake)}`:`lỗ ${xu(x.stake-x.paid)}`}</small></div>`;
    return '';
  }
  function view(){
    const k=K(),r=run(),L=level();
    if(!D.say)D.say=pick(KEEPER.idle);
    let body;
    if(L&&(r?.stage==='play'||L.over&&!L.done)){
      const left=L.b.need-L.taps.length,ended=L.over;
      body=`${r?.stage==='play'?status(r,L):''}
        <div class="fh-go fh-kn-go">${btn(ended?'Đang tính…':'🗡️ Phóng!','knthrow',{},'primary big',ended||left<=0?' disabled data-fh-key="knthrow"':' data-fh-key="knthrow"')}</div>`;
    }else if(r?.stage==='choice')body=status(r)+choiceCard(r);
    else body=resultCard()+stakeRow();
    const ladder=k.ladder.map((m,i)=>`<li>Qua màn ${i+1}: <b>${xu(prize(r&&live()?r.stake:D.stake,i+1))}</b></li>`).join('');
    const hot=k.hot?`<p class="fh-why">🔥 Hôm nay bạn đang thắng đậm ở hội chợ nên bia quay gắt hơn.</p>`:'';
    const tally=k.n?`<p class="fh-rule">Bạn đã chơi <b>${k.n}</b> lượt, dừng nhận thưởng <b>${k.w}</b> lượt, xa nhất màn <b>${k.b}</b>${k.top?`, thưởng lớn nhất ${xu(k.top)}`:''}.</p>`:'';
    return `<section class="fh-stall fh-kn" aria-label="Phóng dao">
      ${say(KEEPER,D.say)}
      <div class="fh-kn-stage" data-fh-live data-fh-key="kn-stage"><canvas class="fh-kn-cv" tabindex="0" role="img" aria-label="Bia gỗ đang quay. Chạm vào bia để phóng dao."></canvas></div>
      ${body}${hot}
      <details class="fh-how" data-fh-key="knhow"><summary>Bậc thưởng đặt ${xu(r&&live()?r.stake:D.stake)}</summary><ol class="fh-kn-ladder">${ladder}</ol><p class="small muted">Lâu lâu có màn 🔥 x2: qua màn đó, phần thưởng tăng thêm của màn được nhân đôi.</p></details>
      <p class="fh-rule">Chạm vào bia (hoặc bấm “Phóng!”) để phóng dao từ dưới lên. Dao cắm vô gỗ là được, chạm trúng dao khác là thua cả lượt. Cắm đủ số dao là qua màn: dừng để nhận thưởng, hoặc chơi tiếp màn khó hơn, thưởng cao hơn. Mỗi màn phải xong trong ${Math.round(k.level_ms/1000)} giây.</p>
      ${tally}
    </section>`;
  }

  /* ---- drawing ---- */
  function knife(c,x,y,ang,o={}){   // tip at (x,y), the knife lying along `ang` (radians) from the tip to the handle
    c.save();c.translate(x,y);c.rotate(ang-Math.PI/2);   // local: the tip at 0,0, the handle down +y
    c.globalAlpha=o.alpha??1;
    const g=c.createLinearGradient(-7,0,7,0);g.addColorStop(0,'#9aa3ad');g.addColorStop(.45,'#f4f6f8');g.addColorStop(.55,'#d8dde3');g.addColorStop(1,'#8a939d');
    c.fillStyle=g;c.beginPath();c.moveTo(0,0);c.quadraticCurveTo(7.6,10,7.4,34);c.lineTo(-7.4,34);c.quadraticCurveTo(-7.6,10,0,0);c.fill();
    c.strokeStyle='#6d7680';c.lineWidth=.8;c.stroke();
    c.fillStyle='#c9a23a';c.fillRect(-9,33,18,5);
    c.fillStyle=o.old?'#5a3a1e':'#7a4a22';c.beginPath();c.roundRect?.(-5.5,38,11,KL-38,4);if(!c.roundRect)c.rect(-5.5,38,11,KL-38);c.fill();
    c.fillStyle='#00000033';for(let i=0;i<3;i++)c.fillRect(-5.5,44+i*7,11,2);
    c.fillStyle='#d9472b';c.beginPath();c.arc(0,KL+2,3.2,0,Math.PI*2);c.fill();   // a red tassel knot
    c.restore();
  }
  function wood(c,th,dark,flash){
    c.save();c.translate(CX,CY);c.rotate(th*Math.PI/180);
    c.fillStyle='#00000030';c.beginPath();c.arc(4,6,BR+6,0,Math.PI*2);c.fill();
    c.fillStyle='#5b3a1c';c.beginPath();c.arc(0,0,BR+6,0,Math.PI*2);c.fill();   // bark
    const g=c.createRadialGradient(-18,-22,8,0,0,BR);g.addColorStop(0,dark?'#c99a62':'#e8bf86');g.addColorStop(1,dark?'#8d6136':'#b98048');
    c.fillStyle=g;c.beginPath();c.arc(0,0,BR,0,Math.PI*2);c.fill();
    c.strokeStyle='#8a5a2655';c.lineWidth=1.4;
    for(let r=14;r<BR;r+=11){c.beginPath();c.ellipse(1.5,-1,r,r*.96,.3,0,Math.PI*2);c.stroke();}
    c.strokeStyle='#5b3a1c88';c.lineWidth=2;c.beginPath();c.moveTo(BR*.15,-BR*.2);c.lineTo(BR*.7,-BR*.55);c.stroke();   // a crack, so the turning shows
    c.fillStyle='#d9472b';c.beginPath();c.arc(0,0,15,0,Math.PI*2);c.fill();
    c.strokeStyle='#f2b53a';c.lineWidth=3;c.stroke();
    c.fillStyle='#f2b53a';c.beginPath();c.arc(0,0,4,0,Math.PI*2);c.fill();
    if(flash){c.fillStyle=`rgba(217,71,43,${flash})`;c.beginPath();c.arc(0,0,BR,0,Math.PI*2);c.fill();}
    c.restore();
  }
  function stuckKnife(c,th,a,old){const p=(a+th)*Math.PI/180;knife(c,CX+TIP*Math.cos(p),CY+TIP*Math.sin(p),p,{old});}
  function draw(now){
    const cv=D.cv;if(!cv||!cv.isConnected)return false;
    const c=cv.getContext('2d'),k=K();if(!c||!k)return false;
    const dark=theme(),L=level(),r=run();
    c.setTransform(cv._s,0,0,cv._s,0,0);c.clearRect(0,0,W,H);
    const bg=c.createRadialGradient(CX,CY,30,CX,CY,240);bg.addColorStop(0,dark?'#4a3420':'#fff1cf');bg.addColorStop(1,dark?'#20160d':'#f0cf95');
    c.fillStyle=bg;c.fillRect(0,0,W,H);
    for(let i=0;i<5;i++){const x=30+i*60;c.fillStyle=dark?'#ffb44a33':'#d9472b22';c.beginPath();c.ellipse(x,14,9,12,0,0,Math.PI*2);c.fill();}   // lantern glow along the top
    if(!L){   // no level on screen: the board idles (or rests after a run)
      const t=reduce()?0:now-D.idleT0,th=(t*.03)%360;
      wood(c,th,dark,0);
      const shown=D.rest||[];for(const a of shown)stuckKnife(c,th,a,true);
      if(!D.rest)for(const a of [30,150,270])stuckKnife(c,th,a,true);
      chips(c,now);
      return !reduce()||D.chips.length>0;
    }
    const t=now-L.t0,th=L.frozen??angleAt(L.b,t);
    let flash=0;
    if(L.over==='lost'&&L.at){const e=now-L.at;flash=Math.max(0,.35-e/1400);}
    wood(c,th,dark,flash);
    for(const a of L.b.pre)stuckKnife(c,th,a,true);
    L.taps.forEach((tap,i)=>{if(i<L.stuck.length&&t>=tap+k.fly)stuckKnife(c,th,L.stuck[i]);});
    for(const tap of L.taps){   // knives in the air
      if(t>=tap+k.fly||t<tap)continue;
      const p=(t-tap)/k.fly,y=READY_Y+(CY+BR-READY_Y)*p;knife(c,CX,y,Math.PI/2);
    }
    if(L.bounce){const e=(now-L.bounce.at)/1000;if(e<BOUNCE_MS/1000){const x=CX+L.bounce.dx*e*120,y=CY+BR+40*e+420*e*e,rot=Math.PI/2+L.bounce.dx*e*9;knife(c,x,y,rot,{alpha:1-e/(BOUNCE_MS/1000)*.5});}}
    const left=L.b.need-L.taps.length;
    if(!L.over&&left>0)knife(c,CX,READY_Y,Math.PI/2);
    for(let i=0;i<L.b.need;i++){   // the knives left, down the left side
      const y=H-16-i*15,used=i>=left;c.fillStyle=used?(dark?'#ffffff22':'#4a2a1222'):(dark?'#f6e7c8':'#4a2a12');
      c.beginPath();c.moveTo(14,y);c.lineTo(30,y-3);c.lineTo(36,y);c.lineTo(30,y+3);c.closePath();c.fill();
    }
    const rest=k.level_ms-t;   // the level's last 15 s: a ring around the board runs out
    if(!L.over&&rest<15000&&rest>0){c.strokeStyle=rest<5000?'#d9472b':'#f2b53a';c.lineWidth=4;c.beginPath();c.arc(CX,CY,BR+14,-Math.PI/2,-Math.PI/2+Math.PI*2*rest/15000);c.stroke();}
    if(!L.over&&rest<=0)timeUp();
    chips(c,now);
    return true;
  }
  function chips(c,now){
    D.chips=D.chips.filter(p=>now-p.at<CLEAR_MS);
    for(const p of D.chips){const e=(now-p.at)/1000;c.fillStyle=p.col;c.globalAlpha=1-e/(CLEAR_MS/1000);c.fillRect(p.x+p.vx*e,p.y+p.vy*e+300*e*e,p.w,p.w*.6);}
    c.globalAlpha=1;
  }
  function loop(){
    D.raf=0;
    if(S.tab!=='dt'||!S.dlg?.open||!D.cv?.isConnected)return;
    if(draw(performance.now()))D.raf=requestAnimationFrame(loop);
  }
  function start(){if(!D.raf)D.raf=requestAnimationFrame(loop);}
  function stop(){cancelAnimationFrame(D.raf);D.raf=0;}

  /** After every render: a new canvas slot gets its size, its finger and its frames. */
  function mount(){
    const cv=S.dlg?.querySelector('.fh-kn-cv');
    if(!cv)return;
    if(!cv._kn){
      cv._kn=1;D.cv=cv;
      const size=()=>{const b=cv.getBoundingClientRect(),dpr=Math.min(2,globalThis.devicePixelRatio||1),w=Math.max(1,b.width);cv.width=Math.round(w*dpr);cv.height=Math.round(w*H/W*dpr);cv._s=cv.width/W;};
      size();new ResizeObserver(()=>{size();start();}).observe(cv);
      cv.addEventListener('pointerdown',e=>{if(e.button>0)return;e.preventDefault();throwKnife();});
      cv.addEventListener('keydown',e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();throwKnife();}});
    }
    D.cv=cv;start();
  }

  /* ---- playing ---- */
  function throwKnife(){
    const L=level(),k=K(),r=run();
    if(!L||L.over||!r||r.stage!=='play'||L.id!==r.id)return;
    const t=Math.round(performance.now()-L.t0),last=L.taps[L.taps.length-1];
    if(t>k.level_ms||L.taps.length>=L.b.need)return;
    if(last!==undefined&&t-last<k.min_tap)return;   // the knife in the air sticks first
    L.taps.push(t);
    const j=judge(L.b,k,L.taps);L.stuck=j.stuck;
    sfx('throw');
    if(j.hit>=0){L.over='lost';setTimeout(()=>{L.bounce={at:performance.now(),dx:Math.random()<.5?-1:1};L.at=performance.now();sfx('clink');setTimeout(()=>sfx('lose'),120);},k.fly);finish(L);}
    else{setTimeout(()=>sfx('mark'),k.fly);if(L.stuck.length>=L.b.need){L.over='clear';finish(L);}}
    if(L.over)render();
    start();
  }
  function timeUp(){
    const L=D.L;if(!L||L.over)return;
    L.over='late';L.frozen=angleAt(L.b,performance.now()-L.t0);D.say=pick(KEEPER.late);sfx('lose');
    setTimeout(()=>{finishLate(L);},400);render();
  }
  async function finishLate(L){
    // the server marks the level lost once its time (and the network's share) is over: send what was thrown
    const r=L.taps.length?await send('fair_kn_throw',{lv:L.lv,taps:L.taps}):null;
    if(r?.fair?.run?.stage==='play'||!r)await new Promise(ok=>setTimeout(ok,4500)).then(()=>S.env.api.refresh().catch(()=>{}));
    const now=run();
    D.last={kind:'lost',late:true,lv:L.lv,stake:now?.stake||0,gone:now?.gone||0};
    L.done=true;D.L=null;D.rest=L.stuck;render();
  }
  async function finish(L){
    const k=K(),wait=new Promise(ok=>setTimeout(ok,k.fly+(L.over==='lost'?BOUNCE_MS:CLEAR_MS)));
    if(L.over==='clear')setTimeout(()=>{L.frozen=angleAt(L.b,performance.now()-L.t0);burst();sfx('cap');},k.fly+60);
    const [r]=await Promise.all([send('fair_kn_throw',{lv:L.lv,taps:L.taps}),wait]);
    const x=r?.fair;L.done=true;
    if(!x){D.L=null;render();return;}   // refused (the flash says why): the server's state shows
    if(x.lost){
      D.last={kind:'lost',late:!!x.late,lv:x.lv,stake:x.run?.stake||0,gone:x.run?.gone||0};D.say=pick(x.late?KEEPER.late:KEEPER.lost);
      D.rest=(x.stuck||[]).concat(L.b.pre);D.L=null;
    }else if(x.cleared){
      D.rest=(x.stuck||[]).concat(L.b.pre);D.L=null;
      if(x.all){D.last={kind:'paid',all:true,paid:x.paid,lv:x.lv,stake:x.run?.stake||0};D.say=pick(KEEPER.all);sfx('win');}
      else if(x.run?.nx){D.say=pick(KEEPER.x2);setTimeout(()=>sfx('open'),200);}
      else D.say=pick(KEEPER.clear);
    }else{   // the server took fewer knives than this screen thought: carry on from its count
      L.over=null;L.done=false;L.frozen=undefined;L.taps=[...(x.run?.tp||[])];L.stuck=judge(L.b,k,L.taps).stuck;L.bounce=null;
    }
    render();start();
  }
  function burst(){
    const now=performance.now(),cols=['#b98048','#e8bf86','#8a5a26','#f2b53a'];
    for(let i=0;i<22;i++){const a=Math.random()*Math.PI*2,v=60+Math.random()*120;D.chips.push({at:now,x:CX+Math.cos(a)*BR*.6,y:CY+Math.sin(a)*BR*.6,vx:Math.cos(a)*v,vy:Math.sin(a)*v-80,w:4+Math.random()*6,col:cols[i%4]});}
    start();
  }
  async function act(name,payload,kind){
    if(D.busy||S.busy)return;
    D.busy=true;D.act=kind;S.flash=null;render();
    const r=await send(name,payload);
    D.busy=false;D.act='';
    const x=r?.fair;
    if(x?.run?.stage==='play'){D.L=null;D.rest=null;D.last=null;D.say=pick(KEEPER.start);level();sfx('open');}
    else if(x?.stopped){D.last={kind:'paid',paid:x.prize,lv:x.run?.lv||0,stake:x.run?.stake||0};D.say=pick(KEEPER.paid);if(x.prize)sfx('win');}
    render();start();
  }
  function click(op,data){
    if(op==='knstake'){const v=Number(data.v);if((K()?.stakes||[]).includes(v)&&!live())D.stake=v;render();return true;}
    if(op==='knstart'){if(D.stake<=(F().wallet||0))act('fair_kn_start',{stake:D.stake},'start');return true;}
    if(op==='knnext'){act('fair_kn_next',{},'next');return true;}
    if(op==='knstop'){act('fair_kn_stop',{},'stop');return true;}
    if(op==='knthrow'){throwKnife();return true;}
    return false;
  }

  /* ---- test hooks (scripts/browser_fair_knife.py) ---- */
  globalThis.__fairKnife={state:()=>{const L=D.L;return {run:run(),level:L&&{id:L.id,lv:L.lv,taps:[...L.taps],stuck:L.stuck.length,need:L.b.need,over:L.over,t:performance.now()-L.t0},last:D.last,busy:busy()};},
    angle:t=>{const L=level();return L?angleAt(L.b,t):null;},lands:t=>{const L=level();return L?lands(L.b,K(),t):null;},
    clock:()=>{const L=level();return L?performance.now()-L.t0:null;},throw:()=>throwKnife()};

  return {view,mount,start,stop,click,live,busy};
}
