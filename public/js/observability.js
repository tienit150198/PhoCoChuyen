/** Optional Google collection, loaded by telemetry only after the first game frame.
 * No player identifiers, free text, saves, URLs with queries, or detailed errors are sent.
 * A failed/blocked SDK never blocks the game. Existing /api/beacon remains the detailed error source. */
const SDK='https://www.gstatic.com/firebasejs/12.19.0/';
const CONSENT_KEY='mnl.analytics';
const ID=/^[a-z][a-z0-9_]{0,39}$/;
const ERROR_KINDS=new Set(['js','promise','asset','api','toast']);
let active=null;

export function createObservability(ctx){
  let transport=null,pending=null,generation=0,lastScreen='',count=0;
  const listeners=[];
  const allowed=()=>ctx.config?.firebase&&ctx.origin===ctx.config.origin&&ctx.consent==='yes'
    &&ctx.navigator?.doNotTrack!=='1'&&ctx.navigator?.doNotTrack!=='yes'&&!ctx.navigator?.globalPrivacyControl;
  const career=()=>ID.test(ctx.api?.state?.current||'')?ctx.api.state.current:undefined;
  function emit(name,extra={}){
    if(!transport||!allowed()||count>=200)return;
    count++;
    try{transport.event(name,{game_version:String(ctx.version||'').slice(0,48),...(career()?{career:career()}:{}),...extra});}catch{/* Google is optional */}
  }
  function screen(name){
    if(!ID.test(name||'')||name===lastScreen||!transport)return;
    lastScreen=name;emit('screen_view',{screen_name:name});
  }
  function error(kind){if(ERROR_KINDS.has(kind))emit('client_error',{error_kind:kind});}
  const listen=(target,name,fn)=>{target?.addEventListener?.(name,fn);listeners.push([target,name,fn]);};
  function stop(){
    generation++;pending=null;
    for(const [target,name,fn] of listeners.splice(0))target?.removeEventListener?.(name,fn);
    try{transport?.stop();}catch{/* blocked SDK */}
    transport=null;lastScreen='';
  }
  async function start(){
    if(!allowed()||transport)return;
    if(pending)return pending;
    const epoch=generation;
    pending=(async()=>{
      try{
        const loaded=await ctx.load();
        if(epoch!==generation||!allowed()){loaded?.stop();return;}
        transport=loaded;
        if(!transport)return;
        emit('game_ready');
        listen(ctx.api,'result',ev=>{
          const d=ev.detail||{};
          if(d.action==='start_day')emit('career_start');
          if(d.action==='end_day')emit('shift_complete');
        });
        listen(ctx.api,'state',()=>screen(ctx.ui?.view||'home'));
      }catch{/* offline, unsupported browser, extension or strict browser policy */}
      finally{if(epoch===generation)pending=null;}
    })();
    return pending;
  }
  return {start,stop,screen,error,setConsent(value){ctx.consent=value;if(value==='yes')return start();stop();}};
}

async function loadFirebase(config,permitted=()=>true){
  const [{initializeApp,getApps},{isSupported,initializeAnalytics,logEvent,setAnalyticsCollectionEnabled,setConsent}]=await Promise.all([
    import(SDK+'firebase-app.js'),import(SDK+'firebase-analytics.js')
  ]);
  if(!permitted()||!await isSupported()||!permitted())return null;
  // No advertising consent or personalization; override default full location/referrer before initialization.
  setConsent({analytics_storage:'granted',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});
  const page_location=config.origin+'/',page_referrer=(()=>{try{return document.referrer?new URL(document.referrer).origin+'/':'';}catch{return '';}})();
  // Performance supports the default app only. Never attach to a different project's existing default app.
  const existing=getApps().find(a=>a.name==='[DEFAULT]');
  if(existing&&existing.options.appId!==config.firebase.appId)return null;
  const app=existing||initializeApp(config.firebase);
  const analytics=initializeAnalytics(app,{config:{send_page_view:false,page_location,page_referrer,
    allow_google_signals:false,allow_ad_personalization_signals:false}});
  setAnalyticsCollectionEnabled(analytics,true);
  logEvent(analytics,'page_view',{page_location,page_referrer,page_title:'Phố Có Chuyện'});
  let perf=null,stopped=false;
  if(config.performance)import(SDK+'firebase-performance.js').then(m=>{
    if(stopped||!permitted())return;perf=m.getPerformance(app);perf.dataCollectionEnabled=true;perf.instrumentationEnabled=true;
  }).catch(()=>{});
  return {
    event(name,params){if(!stopped)logEvent(analytics,name,{page_location,page_referrer,...params});},
    stop(){stopped=true;setAnalyticsCollectionEnabled(analytics,false);setConsent({analytics_storage:'denied'});
      if(perf){perf.dataCollectionEnabled=false;perf.instrumentationEnabled=false;}}
  };
}

function choice(){try{return localStorage.getItem(CONSENT_KEY);}catch{return 'no';}}
function remember(value){try{localStorage.setItem(CONSENT_KEY,value);}catch{/* unavailable: use this page only */}}
function blocked(){return navigator.doNotTrack==='1'||navigator.doNotTrack==='yes'||navigator.globalPrivacyControl;}
function notice(tracker){
  if(choice()!==null||blocked()||document.getElementById('analytics-choice'))return;
  const en=document.documentElement.lang==='en',box=document.createElement('aside');
  box.id='analytics-choice';box.setAttribute('aria-label',en?'Usage statistics':'Thống kê sử dụng');
  box.style.cssText='position:fixed;bottom:calc(env(safe-area-inset-bottom,0px) + 12px);left:12px;right:12px;margin:auto;max-width:460px;z-index:45;padding:12px;border-radius:12px;background:#fff7ec;color:#3b2a22;box-shadow:0 3px 18px #0003;font:14px/1.4 system-ui';
  const text=document.createElement('p');text.style.margin='0 0 8px';
  text.textContent=en?'Allow Google statistics on visits, game steps and speed to help improve the game?':'Cho phép Google thống kê lượt ghé, các bước chơi và tốc độ để cải thiện game?';
  const more=document.createElement('a');more.href='/privacy';more.textContent=en?'Privacy':'Quyền riêng tư';more.style.marginRight='12px';
  box.append(text,more);
  for(const [value,label] of [['yes',en?'Allow':'Cho phép'],['no',en?'Decline':'Từ chối']]){
    const button=document.createElement('button');button.type='button';button.textContent=label;
    button.style.cssText='margin:2px 6px;padding:6px 10px;border:1px solid #9a7454;border-radius:8px;color:inherit;background:transparent;cursor:pointer';
    button.addEventListener('click',()=>{remember(value);box.remove();tracker.setConsent(value);});box.append(button);
  }
  document.body.append(box);
}

export function observabilityBoot(env){
  if(active)return;
  let config;try{config=JSON.parse(document.querySelector('meta[name="mnl-observability"]')?.content||'null');}catch{return;}
  if(!config||location.origin!==config.origin)return;
  active=createObservability({config,origin:location.origin,consent:choice(),navigator,api:env.api,ui:env.ui,
    version:globalThis.__mnlBoot?.version,load:()=>loadFirebase(config,()=>choice()==='yes'&&!blocked())});
  active.start();
  // A small non-modal choice after the game opens; no SDK download before a choice.
  setTimeout(()=>notice(active),1800);
  addEventListener('storage',e=>{if(e.key===CONSENT_KEY)active.setConsent(choice());});
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')active.setConsent(choice());});
  document.addEventListener('click',()=>{setTimeout(()=>active.screen(env.ui?.view||'home'),0);});
}
export function analyticsError(kind){active?.error(kind);}
