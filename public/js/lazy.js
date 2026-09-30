/** Feature modules that load when they are first needed, not with the page.
 *
 * The page used to import every feature up front (57 modules, ~930 KB of source before the first frame).
 * Now app.js imports only what the first screen needs; a sheet like Xếp hạng, Góp ý or Người quen loads its
 * code the first time it opens, and small always-on features (badges, notices) load in idle time after the
 * game is on screen.
 *
 *   const rank=lazy(()=>import('./v4/leaderboard.js'));
 *   rank.m        the module once it is in (else null): render with it when it is there
 *   rank.use()    rank.m, and starts the import when it is not in yet
 *   rank.get()    a promise of the module (one import, retried after a failure)
 *
 * When a module arrives, document gets a 'mnl:lazy' event; app.js re-renders on it, so a sheet that showed
 * skeleton() fills in by itself. event.detail.wanted: something on screen asked for it (use()) while it was
 * still out, so the screen is missing a piece until it re-renders. Dynamic imports go through the import map (game/webassets.py), so they hit
 * the same ?v= URLs and the long-lived cache as the static ones. */
export function lazy(load,{css=[]}={}){
  const h={m:null,p:null,wanted:false,
    get(){
      // Its stylesheets come with it (waited for, at most ~1.5 s), so the sheet never shows unstyled.
      if(!h.p)h.p=Promise.all([load(),...css.map(stylesheet)]).then(([m])=>{h.m=m;document.dispatchEvent(new CustomEvent('mnl:lazy',{detail:{wanted:h.wanted}}));return m;},e=>{h.p=null;throw e;});
      return h.p;
    },
    use(){if(!h.m){h.wanted=true;h.get().catch(e=>console.warn('lazy:',e));}return h.m;},
  };
  return h;
}

/** <link rel=stylesheet> for a versioned /css/ path, once; resolves when it is applied (or after 1.5 s). */
export function stylesheet(href){
  const url=globalThis.__mnlBoot?.asset?.(href)||href;
  let l=document.querySelector(`link[rel="stylesheet"][data-lazy-css="${href}"]`);
  if(!l){l=document.createElement('link');l.rel='stylesheet';l.href=url;l.dataset.lazyCss=href;document.head.append(l);}
  if(l.sheet)return Promise.resolve();
  return new Promise(ok=>{l.addEventListener('load',ok,{once:true});l.addEventListener('error',ok,{once:true});setTimeout(ok,1500);});
}

/** Placeholder while a sheet's code loads: three soft bars (styles inline in index.html), so a tap never
 * looks dead. */
export const skeleton=()=>`<div class="mnl-skel" role="status" aria-busy="true"><i></i><i></i><i></i></div>`;

/** fn() when the browser is idle (or after `timeout` ms at the latest). */
export function idle(fn,timeout=2500){
  const run=()=>{try{fn();}catch(e){console.warn('idle:',e);}};
  if(globalThis.requestIdleCallback)requestIdleCallback(run,{timeout});else setTimeout(run,Math.min(timeout,600));
}

/** Warm the HTTP cache with a few URLs at the lowest priority (<link rel=prefetch>): nothing is parsed or
 * run. Skipped on Data Saver / 2G. */
export function prefetch(urls){
  const c=navigator.connection;if(c&&(c.saveData||/2g/.test(c.effectiveType||'')))return;
  const asset=globalThis.__mnlBoot?.asset||(u=>u);
  for(const u of urls){
    const href=asset(u);if(document.querySelector(`link[rel="prefetch"][href="${href}"],link[rel="modulepreload"][href="${href}"]`))continue;
    const l=document.createElement('link');l.rel='prefetch';l.href=href;if(u.endsWith('.css'))l.as='style';else if(u.endsWith('.js'))l.as='script';document.head.append(l);
  }
}
