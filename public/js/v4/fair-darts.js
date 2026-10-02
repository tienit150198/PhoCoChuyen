/** 🎯 Phóng phi tiêu at the fair: the stall's page, the swinging crosshair and the throw. The result (hit or miss,
 * where the dart sticks) is the server's (game/fair_darts.py, fair_dart); this file only aims and shows it.
 * fair.js owns the dialog and passes its helpers in (setup); its render() patches the page in place, the crosshair
 * lives in a data-fh-live layer moved by requestAnimationFrame so it never re-renders the page. */

const THROWER={name:'Anh Sáu phi tiêu',emoji:'🧔🏽',
  idle:['Phi tiêu đây bà con! Cắm vô vòng màu là ăn một trả một!','Ngắm kỹ rồi phóng nha, gió hội chợ hơi lộng à!','Hồng tâm ở chính giữa đó, ai cắm trúng là có danh hiệu!'],
  hit:['Cắm ngọt luôn! Anh chung tiền nè!','Trúng vòng rồi! Tay chắc ghê!','Đẹp! Phóng thêm phát nữa không?'],
  bull:['Hồng tâm! Trời ơi, mắt thần đây rồi!','Ngay hồng tâm luôn bà con ơi!'],
  miss:['Gió thổi lệch mất rồi, phóng lại nha!','Trật ra vòng rơm rồi, tiếc ghê!','Suýt nữa thôi! Phát sau chắc trúng!']};
const RING_NAME=['hồng tâm','vòng vàng','vòng đỏ','vòng xanh','vòng rơm','ngoài bảng'];
const KEEP=6;   // darts left on the board

/** The crosshair at `t` ms: a Lissajous loop over the board (board units, centre 0,0); quicker since 03/10 (harder to aim). */
export const aimAt=(t,r=92)=>({x:r*Math.sin(t/640),y:r*Math.sin(t/430+1.1)});

export function setup(ctx){
  const {S,F,btn,say,xu,esc,send,render,sfx,pick,reduce,titles}=ctx;
  const D=S.dt={stake:5,say:'',darts:[],seq:0,last:null,raf:0,t0:0,aim:{x:0,y:0},flying:false};
  const R=()=>F().darts||null;

  function boardSvg(){
    const r=R(),rings=r?.rings||[6,20,40,60],B=r?.board||100;
    const marks=D.darts.map(d=>`<g data-fh-key="dt-${d.id}" class="fh-dt-dart${d.id===D.seq&&D.last?' new':''}${d.win?' hit':' miss'}" transform="translate(${d.x} ${d.y})"><g class="fh-dt-pin"><line x1="0" y1="0" x2="10" y2="-13"/><path d="M10 -13l6 -1 -2 5z"/><circle r="2.8"/></g></g>`).join('');
    return `<svg class="fh-dt-board" viewBox="-125 -125 250 250" role="img" aria-label="Bảng phi tiêu: vòng rơm ngoài cùng, vòng xanh, đỏ, vàng và hồng tâm ở giữa">
      <circle r="${B+16}" class="fh-dt-frame"/><circle r="${B}" class="fh-dt-straw"/><circle r="${B}" class="fh-dt-strawlines"/>
      <circle r="${rings[3]}" class="fh-dt-green"/><circle r="${rings[2]}" class="fh-dt-red"/><circle r="${rings[1]}" class="fh-dt-gold"/><circle r="${rings[0]}" class="fh-dt-bull"/>
      <circle r="${rings[3]}" class="fh-dt-edge"/>${marks}</svg>`;
  }
  function view(){
    const f=F(),r=R(),stakes=r?.stakes||[2,5,10,20,50],L0=D.last,busy=D.flying||S.busy,wallet=f.wallet||0;
    if(!D.say)D.say=pick(THROWER.idle);
    if(!stakes.includes(D.stake))D.stake=stakes[1]||stakes[0];
    const why=D.stake>wallet?'Ví không đủ xu':'';
    const res=L0&&!D.flying?`<div class="fh-result ${L0.win?'good':'bad'}"><b>${L0.win?`${L0.ring===0?'🎯 Hồng tâm! ':''}+${xu(L0.net)}`:`−${xu(-L0.net)}`}</b><small>Cắm ${RING_NAME[L0.ring]||''}</small></div>`:'';
    const tally=r&&r.n?`<p class="fh-rule">Bạn đã phóng <b>${r.n}</b> phát, trúng <b>${r.w}</b>${r.b?`, hồng tâm ${r.b}`:''}.</p>`:'';
    return `<section class="fh-stall fh-dt" aria-label="Phóng phi tiêu">
      ${say(THROWER,D.say)}
      <div class="fh-dt-stage${busy?'':' live'}">${boardSvg()}<div class="fh-dt-aimlayer" aria-hidden="true" data-fh-live><i class="fh-dt-aim"></i></div></div>${res}
      <div class="fh-chips" role="group" aria-label="Tiền đặt"><span>Đặt</span>${stakes.map(v=>`<button type="button" class="fh-chip${D.stake===v?' on':''}" data-fh="dtstake" data-v="${v}" aria-pressed="${D.stake===v}" data-fh-key="dts-${v}"${busy||v>wallet?' disabled':''}${v>wallet?' title="Ví không đủ xu"':''}>${v}</button>`).join('')}</div>
      <div class="fh-go"><span>Đặt <b>${xu(D.stake)}</b> · trúng ăn <b>${xu(D.stake)}</b></span>${btn(busy?'Phi tiêu đang bay…':'🎯 Phóng!','dtthrow',{},'primary big',busy||why?' disabled data-fh-key="dtthrow"':' data-fh-key="dtthrow"')}</div>
      ${why&&!busy?`<p class="fh-why">${esc(why)}: chọn mức đặt nhỏ hơn nha.</p>`:''}
      ${tally}
      <p class="fh-rule">Tâm ngắm chạy vòng vòng trên bảng, bấm “Phóng!” khi nó ở chỗ bạn muốn. Phi tiêu cắm trong vòng màu (xanh, đỏ, vàng, hồng tâm) là trúng: ăn một trả một. Cắm vòng rơm ngoài cùng hay rớt ra ngoài là mất tiền đặt. Gió hội chợ hay thổi lệch, nên trúng trật còn nhờ vận may.</p>
    </section>`;
  }

  /* the crosshair: moved by script, the page is not re-rendered */
  const toPct=v=>`${50+v/250*100}%`;
  function stop(){cancelAnimationFrame(D.raf);D.raf=0;}
  function start(){
    if(D.raf)return;
    if(!D.t0)D.t0=performance.now()-Math.random()*20000;
    const loop=()=>{
      if(S.tab!=='dt'||!S.dlg?.open){D.raf=0;return;}
      const el=S.dlg.querySelector('.fh-dt-aim');
      if(el&&!D.flying){const a=aimAt((performance.now()-D.t0)*(reduce()?.5:1),(R()?.board||100)*.9);D.aim=a;el.style.left=toPct(a.x);el.style.top=toPct(a.y);}
      D.raf=requestAnimationFrame(loop);
    };
    D.raf=requestAnimationFrame(loop);
  }
  async function shoot(){
    if(D.flying||S.busy)return;
    const stake=D.stake,f=F();if(stake>(f.wallet||0))return;
    const aim=[Math.round(D.aim.x),Math.round(D.aim.y)].map(v=>Math.max(-120,Math.min(120,v)));
    D.flying=true;D.last=null;S.flash=null;D.say='Vút…!';sfx('throw');render();
    const hold=Math.max(0,(S.lastRound||0)+1350-Date.now());   // the server wants rounds ≥1.2 s apart
    const [r]=await Promise.all([new Promise(ok=>setTimeout(ok,hold)).then(()=>{S.lastRound=Date.now();return send('fair_dart',{stake,aim});}),
      new Promise(ok=>setTimeout(ok,reduce()?120:450))]);
    D.flying=false;
    if(!r?.fair){D.say=pick(THROWER.idle);render();return;}
    const x=r.fair;D.seq++;
    D.darts=[...D.darts,{id:D.seq,x:x.x,y:x.y,win:x.win}].slice(-KEEP);
    D.last={...x};D.say=pick(x.win?(x.ring===0?THROWER.bull:THROWER.hit):THROWER.miss);
    sfx(x.win?'clink':'miss');if(x.win)setTimeout(()=>sfx('win'),180);
    titles(x);render();
  }
  function click(op,data){
    if(op==='dtstake'){const v=Number(data.v);if((R()?.stakes||[]).includes(v)&&!D.flying)D.stake=v;render();return true;}
    if(op==='dtthrow'){shoot();return true;}
    return false;
  }
  return {view,start,stop,click,busy:()=>D.flying};
}
