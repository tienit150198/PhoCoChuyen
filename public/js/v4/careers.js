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
  fruit:'street_kit',garbage:'street_kit',drain:'street_kit',homemaker:'street_kit',pilot:'air_kit',flight_attendant:'air_kit'};

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
    now:()=>Date.now()/1000+(api.clockOffset||0),
    render:()=>renderSheet(),
    send:async(command,payload={})=>cmd(command,payload),
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

/** Run the current workbench's tick once, right after a render: its measured layout (e.g. the action bar
 * kept above the sheet footer) is back in the same frame instead of jumping up to 200 ms later. */
export function tickNow(env){
  const id=env?.api?.state?.current,mod=modules[id],root=document.querySelector('#sheet[open] .career-job');
  if(mod?.tick&&root){try{mod.tick(root,careerContext(env));}catch(error){console.error(error);}}
}
let timer=null;
/** Runs module.tick while the job sheet is visible (real-time bars). */
export function startTicker(getEnv){
  if(timer)return;
  timer=setInterval(()=>{
    if(document.hidden)return;   // nothing to tick in a background tab
    const env=getEnv();if(!env||!env.api.state)return;
    const id=env.api.state.current,mod=modules[id];
    const root=document.querySelector('#sheet[open] .career-job');
    if(!mod?.tick||!root)return;
    try{mod.tick(root,careerContext(env));}catch(error){console.error(error);}
  },200);
}
