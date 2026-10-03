/** Registry of plugin career workbenches (public/js/careers/<id>.js). */
import {icon,portrait,escapeHTML as esc} from '../icons.js';
import {t as tr} from './i18n.js';
import {procedureView} from './procedure.js';
import {asset} from '../assets.js';

const modules={};
const scratch={};
// Careers whose stylesheet builds on a shared kit. The kit is its own <link> (loaded in parallel, placed
// before the career's sheet) instead of an @import inside it, which cost a second round trip.
export const CSS_KIT={cafe_bakery:'food_kit',florist:'food_kit',restaurant:'food_kit',tax_payroll:'office_kit',group_accounting:'office_kit',corp_accounting:'office_kit',
  fruit:'street_kit',garbage:'street_kit',drain:'street_kit',homemaker:'street_kit',ice_cream:'street_kit',com:'street_kit',nail:'street_kit',pagoda:'street_kit',pilot:'air_kit',flight_attendant:'air_kit',
  hr_admin:'office_kit',secretary:'office_kit',it_helpdesk:'office_kit'};

// A failed import() stays failed for the life of the page (the browser keeps it in its module map): the next try of
// a workbench that did not come (a weak network) asks for the same file under another URL (…&retry=n).
const failed={};
const retryUrl=id=>{const url=asset(`/js/careers/${id}.js`);return `${url}${url.includes('?')?'&':'?'}retry=${failed[id]}`;};
/** Import career workbenches (+ their stylesheets). `waitCss`: also wait (max 1.5 s) until the stylesheets
 * are in, so the first frame of a workbench is never unstyled (startup loads only the current career). */
export async function loadCareerModules(ids,waitCss=false){
  await Promise.all(ids.map(async id=>{
    try{
      const mod=modules[id]=(await (failed[id]?import(retryUrl(id)):import(`../careers/${id}.js`))).default;
      // Optional scoped stylesheet: public/css/careers/<id>.css (+ its kit, see CSS_KIT)
      const sheets=mod?.css?[CSS_KIT[id],id].filter(Boolean):[];
      // boot.js preloads the last opened workplace on the next visit, before bootstrap and app.js.
      try{localStorage.setItem('mnl.warm',JSON.stringify([`/js/careers/${id}.js`,...sheets.map(n=>`/css/careers/${n}.css`)]));}catch{/* storage blocked */}
      const ready=sheets.filter(n=>!document.querySelector(`link[data-career-css="${n}"]`)).map(n=>{
        const link=document.createElement('link');link.rel='stylesheet';link.href=asset(`/css/careers/${n}.css`);link.dataset.careerCss=n;
        document.head.append(link);return new Promise(done=>{link.onload=link.onerror=done;setTimeout(done,1500);});
      });
      if(waitCss)await Promise.all(ready);
    }
    catch(error){failed[id]=(failed[id]||0)+1;console.warn('Chưa có giao diện nghề',id,error);}
  }));
}
// A workbench reads its part of the catalogue (ctx.cc) deeply, so it only counts as ready once that part is in
// too (api.js careerContent, set by app.js): until then the caller shows its "still loading" fallback.
let dataIn=()=>true;
export const setCareerData=fn=>{dataIn=fn;};
export const careerUI=id=>dataIn(id)?modules[id]:undefined;
export const hasCareerUI=id=>Boolean(modules[id]);

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const attrs=obj=>Object.entries(obj).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');

/** Context passed to a career module. `env` comes from app.js. */
export function careerContext(env){
  const {api,cmd,confirmAction,toast,renderSheet}=env;
  const state=api.state,id=state.current,room=state.careers[id];
  const content=api.content,cc=content.careers?.[id]||{};
  const ui=scratch[id]??={};
  const button=(label,action,data={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}${disabled?' disabled':''}>${label}</button>`;
  const cmdBtn=(label,command,payload={},style='',disabled=false)=>`<button type="button" class="btn ${style}" data-command="${command}" data-payload="${esc(JSON.stringify(payload))}"${disabled?' disabled':''}>${label}</button>`;
  const confirmCmd=(label,command,payload={},question='',style='',disabled=false)=>`<button type="button" class="btn ${style}" data-action="v4Cmd" data-op="${command}" data-payload="${esc(JSON.stringify(payload))}" data-confirm="${esc(question)}"${disabled?' disabled':''}>${label}</button>`;
  const npc=nid=>content.npcs.find(n=>n.id===nid)||{display_name:state.name,role:'',personality:''};
  const stock=item=>room.inventory?.stock?.[item]??0;
  return {
    api,state,room,content,cc,ui,esc,icon,portrait,fmt,t:tr,npc,stock,
    pill:(label,kind='')=>`<span class="tag ${kind}">${label}</span>`,
    button,cmd:cmdBtn,confirmCmd,
    money:n=>`${fmt(n)} xu`,
    now:()=>clockOf(api),   // the server's clock; held still while a stop tap is on its way (see "live bars and stop taps")
    slide,
    render:()=>renderSheet(),
    send:async(command,payload={},options={})=>cmd(command,payload,options),   // options.quiet: the career shows its own toast
    ask:(title,text,label)=>confirmAction(title,text,label),
    toast,
    // Shared step engine UI (game/procedures.py public steps); submit + order
    // picking are handled globally, `extra` is merged into the payload.
    procedure:(steps,command,extra={})=>procedureView(steps,{command,ui:env.ui,extra}),
  };
}

/** Forms inside a career workbench go to module.submit(form, ctx) first. */
export async function careerSubmit(form,env){
  if(!form.closest('.career-job')||!env?.api?.state)return false;
  const mod=modules[env.api.state.current];if(!mod?.submit)return false;
  try{return Boolean(await mod.submit(form,careerContext(env)));}catch(error){console.error(error);return false;}
}

/** Forwards input/change events inside a career workbench to module.input
 * (el, ctx, 'input'|'change'), so modules can keep typed values in ctx.ui. */
export function careerInput(el,env,type){
  const root=el?.closest?.('.career-job');if(!root||!env?.api?.state)return false;
  const mod=modules[env.api.state.current];if(!mod)return false;
  try{
    if(mod.input&&mod.input(el,careerContext(env),type))return true;
    // <select data-car="name"> / <input data-car="name"> → actions[name](dataset, el, ctx) on change.
    const name=el.dataset?.car;
    if(type==='change'&&name&&mod.actions?.[name]){mod.actions[name]({...el.dataset,value:el.type==='checkbox'?el.checked:el.value},el,careerContext(env));return true;}
  }catch(error){console.error(error);}
  return false;
}

/* ---------------------------------------------------------------- live bars and stop taps
 * Live bars (the sealer needle, the rinse and dryer bars, a shot, the steam wand, the oven, the sewing needle, the
 * egg pan, the noodle basket, the dye timer) move on the compositor: ctx.slide() hands the bar a linear transform
 * animation (Web Animations), so it glides at the screen's own rate with no script, layout or paint per frame, and
 * a busy phone cannot make it stutter or lag behind. module.meters(root,ctx) sets the bars and their words five
 * times a second (and right after each render).
 *
 * A stop on a running meter counts where the bar stood when the finger came down, not when the command reached the
 * server (player feedback #100: "bấm dừng rồi nó vẫn cứ chạy lố"):
 * - pointerdown on a stop control (module.tapStop(op,payload) says yes, or [data-tap-stop="<op>"]) holds the
 *   workbench clock (ctx.now) at the moment of the touch (event.timeStamp: this handler may run late) and stops
 *   the bars there at once: no click, no round trip;
 * - the command it sends carries that moment as payload.tap_at (api.js tapStamp; the server's clock as the page
 *   reads it). game/careers/kit.py tap_now keeps it within a few seconds of its arrival; an older server ignores it;
 * - the clock runs again once that command settles, or when the touch ends without one (a scroll, a step the
 *   workbench turned down, a tap that was not sent). */
const tap={id:0,op:'',at:0,phase:''};   // phase: 'down' (finger on it) · 'click' · 'held' (a command on the wire first) · 'sent'
let tapTimer=0;
const liveNow=api=>Date.now()/1000+(api.clockOffset||0);
const clockOf=api=>tap.phase?tap.at:liveNow(api);
function tapEnd(id){if(id!==tap.id||!tap.phase)return;tap.phase='';clearTimeout(tapTimer);}
function tapLater(ms){const id=tap.id;clearTimeout(tapTimer);tapTimer=setTimeout(()=>{if(tap.phase!=='sent')tapEnd(id);},ms);}
/** api.command asks before sending: the moment of the stop tap behind this command, if any. */
function tapStamp(action){
  if(!tap.phase||tap.phase==='sent'||tap.op!==action)return null;
  tap.phase='sent';clearTimeout(tapTimer);
  const id=tap.id;return {at:Math.round(tap.at*1000)/1000,done:()=>tapEnd(id)};
}
/** Move a bar to `pct` (0–100 of its track) and keep it going at `perSec` % a second on the compositor.
 * `fill`: a full-width fill slid in from the left (translateX(pct-100%)); else a full-width layer whose left edge
 * is the needle (translateX(pct%)). While a stop tap holds the clock, or with no Web Animations, it stands still. */
const sliding=new Set();let drawn=0;   // bars with an animation, and the draw that last set each
function slide(el,pct,perSec,fill){
  if(!el)return;
  el._drawn=drawn;
  const at=v=>`translateX(${Math.max(0,Math.min(100,v))-(fill?100:0)}%)`;
  let a=el._slide;
  if(tap.phase||!(perSec>0)||!el.animate){
    if(a){a.cancel();el._slide=null;sliding.delete(el);}
    const v=at(pct);if(el.style.transform!==v)el.style.transform=v;
    return;
  }
  if(!a||a.playState==='idle'||a._rate!==perSec){
    a?.cancel();
    a=el._slide=el.animate([{transform:at(0)},{transform:at(100)}],{duration:100/perSec*1000,fill:'both',easing:'linear'});
    a._rate=perSec;a.currentTime=pct/perSec*1000;sliding.add(el);return;
  }
  const want=pct/perSec*1000;if(Math.abs((a.currentTime||0)-want)>40)a.currentTime=want;   // a new clock reading
}
function stopOp(el,mod){
  if(el.dataset.tapStop)return el.dataset.tapStop;
  const op=el.dataset.command||el.dataset.op;if(!op||!mod?.tapStop)return '';
  try{return mod.tapStop(op,JSON.parse(el.dataset.payload||'{}'))?op:'';}catch{return '';}
}
function tapListen(getEnv){
  document.addEventListener('pointerdown',e=>{
    if(!e.isPrimary||e.button>0)return;
    const el=e.target.closest?.('[data-tap-stop],[data-command],[data-op]');
    if(!el||el.disabled||el.classList.contains('is-pending')||!el.closest('#sheet[open]'))return;
    const env=getEnv(),api=env?.api,op=api?.state&&stopOp(el,modules[api.state.current]);if(!op)return;
    // When the finger came down: on a busy phone this handler runs late, while the bars kept gliding.
    const at=liveNow(api)-Math.min(1,Math.max(0,performance.now()-e.timeStamp)/1000);
    Object.assign(tap,{id:tap.id+1,op,at,phase:'down'});clearTimeout(tapTimer);
    const s=scope(env);if(s)draw(env,s,false);   // the bars stop on this frame
  },true);
  document.addEventListener('pointercancel',()=>{if(tap.phase==='down')tapEnd(tap.id);},true);
  document.addEventListener('pointerup',()=>{if(tap.phase==='down')tapLater(800);},true);   // no click follows: a scroll
  // The click sends it (app.js); while another command is on the wire app.js holds the tap and sends it after.
  document.addEventListener('click',()=>{if(tap.phase!=='down')return;tap.phase=document.body.classList.contains('busy')?'held':'click';tapLater(tap.phase==='held'?20000:600);},true);
  const api=getEnv()?.api;if(!api)return;
  api.tapStamp=tapStamp;
  api.addEventListener('busy',e=>{if(!e.detail&&tap.phase==='held')tapLater(600);});
}

let timer=null;
function scope(env){
  if(document.hidden||!env?.api?.state)return null;   // nothing to draw in a background tab
  const mod=modules[env.api.state.current],root=document.querySelector('#sheet[open] .career-job');
  return mod&&root?{mod,root}:null;
}
function draw(env,s,ticking){
  try{
    const ctx=careerContext(env);
    drawn++;
    if(s.mod.meters)s.mod.meters(s.root,ctx);
    // A bar its meters no longer move (the timer stopped on the server, the node left the page) stops gliding.
    for(const el of sliding)if(el._drawn!==drawn||!el.isConnected){el._slide?.cancel();el._slide=null;sliding.delete(el);}
    if(ticking&&s.mod.tick)s.mod.tick(s.root,ctx);
  }catch(error){console.error(error);}
}
/** Run the current workbench's meters and tick once, right after a render: its measured layout (e.g. the action
 * bar kept above the sheet footer) and its bars are back in the same frame instead of up to 200 ms later. */
export function tickNow(env){const s=scope(env);if(s)draw(env,s,true);}
/** Runs the workbench's meters and tick while the job sheet is visible (real-time bars). */
export function startTicker(getEnv){
  if(timer)return;
  tapListen(getEnv);
  timer=setInterval(()=>{const env=getEnv(),s=scope(env);if(s)draw(env,s,true);},200);
}
