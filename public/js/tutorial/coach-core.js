/** 🧭 First-day coach, the part without a page: the plan of one workplace and the step machine.
 * coach.js draws it over the real game (spotlight, bubble, chip) and feeds it what it sees; tests/coach_engine.mjs
 * drives it with fake controls. No DOM, no game rule here.
 *
 * A step (from ./coach-content.js, game/coach_content.py):
 *   {id, e: emoji, t: short words, k: [button labels], s: [css selectors], v: {t,k,s,h} a tab/fold that reveals it
 *    (h: 1 what comes first and is still being done: the coach waits out of sight while it is on screen),
 *    d: the guide line it comes from (shown under "Chi tiết"), w: where it is when it is not on screen,
 *    o: 1 optional (skipped quietly when its control is not around, unless the step before it, marked f: 1, is open
 *       again: a wrong answer the game keeps open to fix; then the walk goes back to that one), x: 1 text only (no
 *       control: "Tiếp"),
 *    at: 'job' (default: the work sheet) | 'any', kind: 'open' | 'close' | 'sum' (the shared steps below)}. */

/** Shared steps around every workplace's own: open the shift, then (after the workplace's steps) close it and read
 * the day's summary. Words are short; coach.js translates them (i18n/overrides.json). */
export const OPEN={id:'open',kind:'open',e:'☀️',t:'Bấm Mở ca để bắt đầu ngày làm.'};
export const CLOSE={id:'close',kind:'close',e:'🌙',t:'Làm thêm vài khách. Hết khách thì bấm Khép ca.'};
export const SUM={id:'sum',kind:'sum',e:'🧾',t:'Tổng kết ngày: tiền vào quỹ, sao khách chấm. Xem kỹ rồi bấm Xong.'};
/** 💰 game/pay_boost.py, optional (dropped quietly when not on screen): the 🎉 Tuần lễ tay nghề banner while the event
 * runs, and the 🧰 Bộ đồ nghề button under a finished job's pay (v4/paykit.js). */
export const PAYWEEK={id:'payweek',e:'🎉',t:'Tuần lễ tay nghề: +20% tiền công, đủ 5 việc mỗi ngày có thưởng.',s:['[data-coach="payweek"]'],o:1};
export const PAYKIT={id:'paykit',e:'🧰',t:'Tiền công từng khoản ở đây. Bộ đồ nghề giúp kiếm thêm.',s:['[data-coach="paykit-tip"]'],o:1};

/** The whole walk for one workplace: open, its own steps, close, summary. `data` = coach-content.js default export. */
export function planFor(data,cid){
  const own=data?.careers?.[cid]?.steps||[];
  return [OPEN,...own.map((s,i)=>({...s,id:s.id||'s'+i})),PAYWEEK,PAYKIT,CLOSE,SUM];
}

/** Words of a label, for matching a button: no emoji, no punctuation, lower case ("🛒 Mời đặt hàng →" → "mời đặt hàng"). */
export function norm(s){
  return String(s??'').normalize('NFC').toLowerCase()
    .replace(/[\p{Extended_Pictographic}‍️]/gu,' ').replace(/[^\p{L}\p{N}%]+/gu,' ').replace(/\s+/g,' ').trim();
}
/** How well a control's text names one of the labels: 3 the same words, 2 starts with them ("Giao món · 25 xu"),
 * 1 holds a longer label whole ("Soát hóa đơn rồi bấm CHỐT BILL" in a hint), 0 not at all. `want` = labels through norm(). */
export function labelScore(text,want){
  const x=norm(text);if(!x)return 0;
  let best=0;
  for(const w of want){
    if(!w)continue;
    if(x===w)return 3;
    if(x.startsWith(w+' '))best=Math.max(best,2);
    else if(w.length>=8&&(' '+x+' ').includes(' '+w+' '))best=Math.max(best,1);
  }
  return best;
}
export const labelHit=(text,want)=>labelScore(text,want)>0;

/** How long a tap waits for the game's answer before the step counts as done anyway (a tab, a fold: no command). */
export const SETTLE=700;
/** A step whose control is not there yet: a moment of quiet (a sheet opening, a redraw) before the "where" bubble. */
export const GRACE=1200;
/** After the player's last move (a tap the game took, "Bỏ qua"), the screen redraws: only after this long is an
 * optional step whose control is not there dropped (the ones after it then go at once), or the game's own next-step
 * mark trusted to jump ahead. */
export const OPT_WAIT=900;

/** One run of the coach at one workplace. `frame(probe)` is called a few times a second: `probe(step)` says what
 * is on screen for that step ({el} its control, {via} what reveals it, {nav} the way to the work screen, {done},
 * {hold} wait out of sight); the answer is what to draw. Taps come in through tap(), the game's answers through
 * answered(). */
export class CoachRun{
  constructor({cid,steps,at=0,now}){
    this.cid=cid;this.steps=steps;this.now=now||(()=>Date.now());
    this.i=Math.max(0,Math.min(Number(at)||0,steps.length-1));
    this.since=this.now();this.moved=this.since;this.pend=null;this.ended=false;this.shown=new Set();this.acted=false;
  }
  get step(){return this.steps[this.i]||null;}
  /** The steps that count for "2/8": every required step, and an optional one only once it was on screen (a beer
   * check that never came up is no step of this run). */
  counted(){return this.steps.filter((s,j)=>!s.o||this.shown.has(s.id)||j===this.i);}
  get total(){return this.counted().length;}
  /** Position for "2/8" (1-based). */
  get n(){const c=this.counted(),k=c.indexOf(this.step);return k<0?c.length:k+1;}
  get final(){return this.i>=this.steps.length-1;}
  /** Move to step `to` (default: the next one). `quiet`: not the player's move (an optional step that is not
   * around): the screen has not changed, the "redraw" wait is not started again. */
  next(to=this.i+1,quiet=false){
    this.pend=null;this.acted=false;
    if(!quiet)this.moved=this.now();
    if(to>=this.steps.length){this.i=this.steps.length;this.ended=true;return;}
    this.i=Math.max(this.i+1,to);this.since=this.now();
  }
  /** "Bỏ qua": this step is not for now. */
  skip(){this.next();}
  /** Back to step `j` (only ever the one just before): the game took the answer but kept that step open to fix (a wrong
   * pick lowers the quality and stays), so the walk shows it again instead of dropping the optional steps after it. */
  back(j){
    if(j==null||j<0||j>=this.i)return;
    this.i=j;this.pend=null;this.acted=false;this.since=this.moved=this.now();
  }
  /** A tap on the control of step `j` (this one, or a later one the player went ahead to). `busy()` = a command is
   * on its way. The step advances when the game answers (answered(true)), or after SETTLE when nothing was sent. */
  tap(j,{cmd=false}={}){
    if(this.ended||j==null||j<this.i)return;
    // A control that sends a command counts only once the game takes it (a confirm the player cancels, a form that
    // does not send, a mentor who stops it: no answer, the step stays).
    this.pend={to:j+1,at:this.now(),ok:false,cmd};
  }
  /** The game answered a command: ok = accepted. A refusal keeps the step (the toast says why). Any accepted command
   * after the player touched the work screen also completes a words-only step that was on screen (acted). */
  answered(ok){
    if(this.pend){if(ok)this.pend.ok=true;else this.pend=null;return;}
    if(ok&&this.step?.x&&this.shown.has(this.step.id)&&this.now()-this.since>1200)this.acted=true;
  }
  /** What to draw now. */
  frame(probe,{busy=()=>false}={}){
    for(let guard=0;guard<this.steps.length+2;guard++){
      if(this.ended)return {mode:'end'};
      const p=this.pend;
      if(p&&(p.ok||!p.cmd&&this.now()-p.at>=SETTLE&&!busy())){this.next(p.to);continue;}
      if(p&&p.cmd&&this.now()-p.at>8000)this.pend=null;   // nothing came back: forget the tap
      if(this.acted){this.next();continue;}
      const s=this.step;if(!s){this.ended=true;return {mode:'end'};}
      const look=probe(s)||{};
      if(look.done){this.next();continue;}
      const settled=this.now()-this.moved>=OPT_WAIT;
      if(look.jump!=null&&look.jump>this.i&&settled){this.next(look.jump);continue;}   // the game is already further on
      if(look.back!=null&&look.back===this.i-1&&settled){this.back(look.back);continue;}   // the last step is open again
      if(look.hold)return {mode:'hidden',step:s};
      if(look.el){this.shown.add(s.id);return {mode:look.dock?'dock-spot':'spot',el:look.el,step:s,text:look.text||''};}
      if(look.via){this.shown.add(s.id);return {mode:'via',el:look.via,step:s};}
      if(look.nav){return {mode:'nav',el:look.nav,step:s,text:look.navText||''};}
      if(look.dock){this.shown.add(s.id);return {mode:'dock',step:s};}
      if(s.x){this.shown.add(s.id);return {mode:'text',step:s};}
      const waited=this.now()-this.since;
      if(s.o&&!this.shown.has(s.id)&&settled){this.next(this.i+1,true);continue;}
      if(waited<GRACE)return {mode:'hidden',step:s};
      this.shown.add(s.id);
      return {mode:'fallback',step:s};
    }
    return {mode:'hidden'};
  }
  /** Which step (index ≥ the current one) a tapped control belongs to: `matches(step)` tests the control against a
   * step's labels/selectors. Looks a few steps ahead (the player knew the way); shared steps finish by state. */
  which(matches){
    for(let j=this.i;j<Math.min(this.steps.length,this.i+12);j++){
      const s=this.steps[j];if(!s||s.kind||s.x)continue;
      if(matches(s))return j;
    }
    return null;
  }
}
