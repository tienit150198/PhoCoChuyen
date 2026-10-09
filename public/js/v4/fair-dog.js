/** 🐕 Đua chó at the Chợ đen (owner 09/10: "trò đua chó"; the player only watches and cheers): anh Tư's track, six
 * dogs of the pet system's breeds (./pet-art.js), each with its payout on the board. The player picks a dog and a
 * stake; the server draws the whole race at once (game/fair_dog.py, fair_dg: the finishing order, a photo finish or
 * not, a seed for the show) and pays it before the dogs even start. This file only plays the race out so that it ends
 * with that order (lead changes on the way, the crowd, the 📣 cổ vũ button, which sends nothing and changes nothing),
 * then shows the receipt. No chance or rate is known here: only the payouts (prices) the server sends.
 * fair.js owns the dialog and passes its helpers in (setup); its render() patches the page in place: the track lives
 * in a data-fh-live slot keyed by the run, so a render never touches the running dogs. */
import {petSVG} from './pet-art.js';
import {t as tr} from './i18n.js';

const HOST={name:'Anh Tư đua chó',emoji:'🧢',
  idle:['Đua chó đây bà con ơi! Chọn một em, đặt bao nhiêu tùy!','Em nào cũng khỏe re, chọn đi rồi hò hét cho vui!','Đàn này mới tắm xong, chạy nhanh như gió nè!'],
  go:['Vô vạch! Ba, hai, một… chạy!','Chạy rồi bà con ơi! Hò to lên!'],
  cheer:['Hò to lên nữa!','Nghe tiếng cổ vũ là chạy hăng liền!','Bà con la muốn bể chợ luôn!'],
  win:['Trúng rồi! Em này đúng là chiến binh!','Về nhất! Anh chung tiền liền nè!'],
  lose:['Tiếc ghê, chỉ thua chút xíu thôi!','Không sao, lượt sau chọn em khác thử coi!','Đua chó là vậy, hên xui mà!']};
const BIBS=['#e2462d','#2f7fd1','#f0b44a','#5aa06a','#8a4bb8','#e86aa0'];
const CHIPS=[10,100,1000,10000,100000];
const RACE_MS=15500;       // the winner's finish (the others come in after it)
const CROWD='🧑🏻👩🏽👴🏻👧🏻🧔🏽👵🏻🧑🏽👦🏻';
const CHEERS=['Cố lên!','Chạy lẹ!','Tới luôn!','Hú hú!','Nhanh lên!'];

/** A small seeded random (the show only). */
export function seeded(seed){let x=(seed>>>0)||1;return ()=>{x^=x<<13;x>>>=0;x^=x>>>17;x^=x<<5;x>>>=0;return x/4294967296;};}
/** The race's script: for each lane its finish time (ms) and checkpoints [time ms, share of the track], ending at 1
 * exactly in the server's order (`order`: lanes, the winner first). A photo finish puts the second one 60 ms behind.
 * Pure (the node tests check the order). */
export function script(order,seed,photo,lanes=order.length,total=RACE_MS){
  const rnd=seeded(seed),fin=new Array(lanes).fill(total);
  let t=total;
  order.forEach((lane,rank)=>{if(rank===1)t+=photo?60:180+rnd()*420;else if(rank>1)t+=220+rnd()*520;fin[lane]=Math.round(t);});
  const K=7;
  return fin.map((T,lane)=>{
    const w=[];for(let k=0;k<K;k++)w.push(.55+rnd()*.9);
    if(lane===order[0]&&rnd()<.6){w[0]*=.6;w[1]*=.7;w[K-1]*=1.5;}   // the winner often comes from behind
    const sum=w.reduce((a,b)=>a+b,0);let acc=0;
    const pts=[[0,0]];for(let k=0;k<K;k++){acc+=w[k];pts.push([Math.round(T*(k+1)/K),k===K-1?1:acc/sum]);}
    return {fin:T,pts};
  });
}
/** Where a lane is at time ms (0..1), eased between its checkpoints. */
export function at(path,ms){
  const p=path.pts;if(ms<=0)return 0;if(ms>=path.fin)return 1;
  for(let i=1;i<p.length;i++)if(ms<=p[i][0]){const [t0,a]=p[i-1],[t1,b]=p[i],u=(ms-t0)/Math.max(1,t1-t0),e=u*u*(3-2*u);return a+(b-a)*(.35*u+.65*e);}
  return 1;
}

export function setup(ctx){
  const {S,F,btn,say,xu,esc,send,render,sfx,pick,reduce,serverNow,amtBox,amtClear,payX}=ctx;
  const D=S.dg={lane:null,stake:100,race:null,lanes:null,phase:'idle',res:null,say:'',run:0,raf:0,t0:0,paths:null,cheers:0,shown:0};
  const R=()=>F().dog||null;
  const nowRace=()=>{const r=R();return r?Math.floor(serverNow()/1000/(r.slot||120)):0;};
  /** The lineup shown: kept while a dog is picked (the server takes this race and the one after), else the current. */
  function sync(){
    const r=R();if(!r||D.phase!=='idle')return;
    const n=nowRace(),keep=D.race!=null&&D.lane!=null&&n-D.race<=1&&D.lanes;
    if(keep||D.race===n&&D.lanes)return;
    const row=(r.races||[]).find(x=>x[0]===n)||(r.races||[])[0];if(!row)return;
    if(D.race!=null&&D.race!==row[0]){D.lane=null;D.res=null;D.paths=null;}   // a new lineup: the last receipt goes with the old one
    D.race=row[0];D.lanes=row[1];
  }
  const dogOf=i=>(R()?.dogs||[])[i]||{name:'?',shape:'mutt'};
  const pet=(d,size=46)=>petSVG({shape:d.shape,size:d.size},{b:d.b,m:d.m,l:d.l,e:d.e},'walk',{},size,'fh-dg-pet');
  const mult=m=>'×'+payX(m/10);
  const busy=()=>D.phase!=='idle';
  const live=()=>D.phase==='run';
  function why(){
    const r=R(),w=F().wallet||0;if(!r)return '';
    if(D.stake<(r.min||10))return `Đặt ít nhất ${xu(r.min||10)}`;
    if(D.stake>w)return 'Ví không đủ xu';
    if(D.stake>(r.max||D.stake))return 'Ván lớn cỡ này nhà cái không nhận đâu';
    return '';
  }

  function track(){
    const lanes=D.lanes||[],res=D.res,pos=i=>D.paths?at(D.paths[i],D.shown):res?1:0;
    const rows=lanes.map(([di],i)=>{const d=dogOf(di),me=D.lane===i;
      return `<div class="fh-dg-lane${me?' me':''}" style="--bib:${BIBS[i%BIBS.length]}"><span class="fh-dg-bib" aria-hidden="true">${i+1}</span>
        <span class="fh-dg-run" data-dg-lane="${i}" style="transform:translateX(${(pos(i)*100).toFixed(2)}%)"><span class="fh-dg-dog">${pet(d,40)}</span></span></div>`;}).join('');
    return `<div class="fh-dg-track${live()?' go':''}" data-fh-live data-fh-key="dg-track-${D.race}-${D.run}" role="img" aria-label="${esc(tr('Đường đua chó'))}">
      <div class="fh-dg-crowd" aria-hidden="true">${[...CROWD].filter(c=>c.trim()).map((c,i)=>`<i style="--i:${i}">${c}</i>`).join('')}</div>
      <div class="fh-dg-lanes">${rows}<span class="fh-dg-finish" aria-hidden="true"></span></div><div class="fh-dg-pop" aria-hidden="true"></div></div>`;
  }
  function board(){
    const lanes=D.lanes||[],dis=busy();
    return `<div class="fh-dg-board" role="radiogroup" aria-label="${esc(tr('Chọn chó'))}">${lanes.map(([di,m],i)=>{const d=dogOf(di),on=D.lane===i;
      return `<button type="button" class="fh-dg-pick${on?' on':''}" data-fh="dgpick" data-v="${i}" data-fh-key="dgp-${i}" role="radio" aria-checked="${on}" style="--bib:${BIBS[i%BIBS.length]}"${dis?' disabled':''}>
        <span class="fh-dg-bib" aria-hidden="true">${i+1}</span><span class="fh-dg-face" aria-hidden="true">${pet(d,34)}</span>
        <span class="grow"><b>${esc(d.name)}</b><small>${esc(d.breed||'')}</small></span><em class="fh-dg-mult">${mult(m)}</em></button>`;}).join('')}</div>`;
  }
  function result(){
    const x=D.res;if(!x||live())return '';
    const lanes=D.lanes||[],name=i=>esc(dogOf((lanes[i]||[])[0]).name),podium=x.order.slice(0,3).map((l,k)=>`<li><span aria-hidden="true">${['🥇','🥈','🥉'][k]}</span> <b>${name(l)}</b> <small>số ${l+1}</small></li>`).join('');
    const mine=name(x.lane),first=name(x.order[0]),gain=xu(x.net),lost=xu(x.stake),pays=mult(x.mult);
    const head=x.won?`🎉 ${mine} về nhất! +${gain}`:`${first} về nhất · −${lost}`;
    const sub=x.photo?`Bạn cược ${mine} · ${pays} · 📸 về đích sát nút`:`Bạn cược ${mine} · ${pays}`;
    return `<div class="fh-result ${x.won?'good':'bad'}" data-fh-key="dg-res"><b>${head}</b><small>${sub}</small></div><ol class="fh-dg-podium">${podium}</ol>`;
  }
  function view(){
    sync();
    const r=R();if(!r)return '';
    if(!D.say)D.say=pick(HOST.idle);
    const w=why(),dis=busy(),picked=D.lane!=null,who=picked?esc(dogOf(D.lanes[D.lane][0]).name):'',amt=xu(D.stake);
    const line=picked?`Cược <b>${who}</b> · <b>${amt}</b>`:esc(tr('Chọn một chú chó'));
    const go=live()?`<div class="fh-go"><span>${esc(tr('Hò lên cho chú chó của bạn!'))}</span>${btn('📣 Cổ vũ','dgcheer',{},'cream big',' data-fh-key="dgcheer"')}</div>`
      :`<div class="fh-go"><span>${line}</span>${btn(D.phase==='send'?'Đang vô vạch…':'🏁 Xuất phát!','dggo',{},'primary big',!picked||w||dis?' disabled data-fh-key="dggo"':' data-fh-key="dggo"')}</div>`;
    return `<section class="fh-stall fh-dg" aria-label="Đua chó">
      ${say(HOST,D.say)}
      ${track()}${result()}
      ${board()}
      <div class="fh-chips" role="group" aria-label="Tiền cược"><span>Cược</span>${CHIPS.map(v=>`<button type="button" class="fh-chip${D.stake===v?' on':''}" data-fh="dgstake" data-v="${v}" aria-pressed="${D.stake===v}" data-fh-key="dgs-${v}"${dis?' disabled':''}>${v>=1000?`${v/1000}k`:v}</button>`).join('')}${amtBox('dg',CHIPS.includes(D.stake)?0:D.stake,dis)}</div>
      ${go}
      ${w&&picked&&!dis?`<p class="fh-why">${esc(w)}: chọn mức cược khác nha.</p>`:''}
      <p class="fh-rule">Chọn một chú chó và tiền cược. Chó của bạn về nhất thì ăn đúng số lần ghi bên cạnh (tính cả tiền vốn). Cổ vũ cho vui thôi, không đổi được kết quả đâu nha.</p>
      <p class="fh-rule">🚨 Đây vẫn là chợ đen: công an có thể ập vào bất cứ lúc nào.</p>
    </section>`;
  }

  /* ---- the race ---- */
  function frame(){
    D.raf=0;if(!live())return;
    const el=S.dlg?.querySelector(`[data-fh-key="dg-track-${D.race}-${D.run}"]`);
    D.shown=performance.now()-D.t0;
    if(el){for(const n of el.querySelectorAll('[data-dg-lane]')){const i=Number(n.dataset.dgLane);n.style.transform=`translateX(${(at(D.paths[i],D.shown)*100).toFixed(2)}%)`;}}
    const end=Math.max(...D.paths.map(p=>p.fin))+400;
    if(D.shown>=end||!S.dlg?.open||document.hidden){finish();return;}
    D.raf=requestAnimationFrame(frame);
  }
  function finish(){
    cancelAnimationFrame(D.raf);D.raf=0;
    if(!D.res)return;
    D.phase='idle';D.shown=1e9;
    D.say=pick(D.res.won?HOST.win:HOST.lose);
    sfx(D.res.won?'win':'lose');
    render();
  }
  async function go(){
    sync();
    if(busy()||D.lane==null||why())return;
    D.phase='send';D.res=null;D.paths=null;D.shown=0;D.cheers=0;S.flash=null;render();
    const r=await send('fair_dg',{race:D.race,lane:D.lane,stake:D.stake});
    if(!r?.fair||r.fair.game!=='dg'||!Array.isArray(r.fair.order)){
      D.phase='idle';
      if(S.err==='fair_dg_race'){D.race=null;D.lanes=null;D.lane=null;S.env?.api?.refresh?.().catch(()=>{/* the next state */});}
      render();return;
    }
    D.res={...r.fair};D.run++;D.paths=script(r.fair.order,r.fair.seed,!!r.fair.photo,(D.lanes||[]).length||6,reduce()?600:RACE_MS);
    D.phase='run';D.say=pick(HOST.go);D.t0=performance.now();sfx('whistle');render();
    D.raf=requestAnimationFrame(frame);
  }
  function cheer(){
    if(!live())return;
    D.cheers++;sfx('cheer');
    if(D.cheers%4===1){D.say=pick(HOST.cheer);const p=S.dlg?.querySelector('.fh-dg .fh-npcline .fh-bubble p');if(p)p.textContent=D.say;}
    const pop=S.dlg?.querySelector(`[data-fh-key="dg-track-${D.race}-${D.run}"] .fh-dg-pop`);
    if(pop&&!reduce()){const s=document.createElement('span');s.textContent='📣 '+pick(CHEERS);s.style.left=`${10+Math.random()*70}%`;pop.append(s);setTimeout(()=>s.remove(),1300);}
  }
  function click(op,data){
    switch(op){
      case'dgpick':if(busy())return;D.lane=Math.max(0,Math.min(5,Number(data.v)||0));if(D.res){D.res=null;D.paths=null;}sfx('mark');render();return;
      case'dgstake':if(busy())return;D.stake=Number(data.v)||100;amtClear('dg');render();return;
      case'dggo':go();return;
      case'dgcheer':cheer();return;
    }
  }
  function typed(v){const r=R();if(!r||busy())return;D.stake=Math.max(r.min||10,Math.min(v,r.max||v));render();}
  /** Every second while the stall is open: a new lineup when the race moved on and no dog is picked. */
  function tick(){if(D.phase!=='idle')return;const was=D.race;sync();if(D.race!==was)render();}
  function stop(){if(live()){D.shown=1e9;finish();}}
  /** Xu already paid for a race still running (fair.js leaves it out of what it shows until the finish): 'day' the
   * stall's own row (today_xu), else with a 🍀 Lộc's own row too. */
  const hold=k=>live()&&D.res?(D.res.back||0)+(k==='day'?0:D.res.loc?.bonus||0):0;
  return {view,click,typed,tick,stop,busy,live,hold};
}
