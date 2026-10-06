/* First script of the page. server.py inlines it into index.html (allowed by a CSP hash, see
 * game/webassets.py); the raw template loads it as a file instead. With no imports it runs while the
 * module graph is still downloading, and starts everything that does not need app.js:
 * - /api/bootstrap?lite=1 (state) and /api/content?v=<hash>&part=core (the catalogue's first-frame part, cached
 *   for a year) in parallel;
 * - the stylesheets announced by <link rel=preload as=style>, applied without blocking the first paint
 *   (the splash is styled inline); api.js waits for them before the game is shown;
 * - the workbench, scene and stylesheets of the workplace this browser opened last (mnl.warm), and the
 *   English pack for English players (mnl.lang), so they no longer wait for bootstrap + app.js;
 * - on a cold start (nothing stored), the ones /api/bootstrap names in its X-Game-Warm header, and that
 *   workplace's part of the catalogue (X-Game-Place), as soon as the response headers are in (the body is still
 *   on its way), instead of an import chain after app.js.
 * api.js init() picks all of this up from globalThis.__mnlBoot; without it, it fetches on its own. */
(()=>{
  const d=document,B=globalThis.__mnlBoot={sent:Date.now()};
  let map={};
  try{map=JSON.parse(d.querySelector('script[type="importmap"]')?.textContent||'{}').imports||{};}catch{/* no import map: plain URLs */}
  const asset=B.asset=url=>map[url]||url;
  const meta=name=>d.querySelector(`meta[name="${name}"]`)?.content||'';
  B.version=meta('mnl-version');
  const store=key=>{try{return localStorage.getItem(key);}catch{return null;}};
  // ?_r= is only the cache-buster of a "Tải lại" (below): out of the address bar again, the rest of the query kept.
  const bust=u=>{const x=new URL(u,location.href);x.searchParams.set('_r',Date.now().toString(36));return x.href;};
  try{const u=new URL(location.href);if(u.searchParams.has('_r')){u.searchParams.delete('_r');history.replaceState(history.state,'',u.pathname+u.search+u.hash);}}catch{/* old browser */}
  try{const t=store('mnl.theme');if(t&&/^[a-z_]+$/.test(t))d.documentElement.dataset.theme=t;}catch{/* ignore */}
  try{
    B.response=fetch('/api/bootstrap?lite=1',{credentials:'same-origin',headers:{'X-Game-Delta':'1'}});  // its state's parts named (api.js Held)
    const content=meta('mnl-content');
    if(content){B.contentBase=content;B.contentUrl=content+'&part=core';B.content=fetch(B.contentUrl,{credentials:'same-origin'});}
  }catch{/* old browser: api.js fetches */}
  // A sheet that fails (a dropped mobile connection) is asked once more with a cache-buster before the game goes on without it.
  const sheets=[...d.querySelectorAll('link[rel="preload"][as="style"]')].map(pre=>new Promise(done=>{
    const link=d.createElement('link');link.rel='stylesheet';link.href=pre.href;let again=0;
    link.onload=()=>done();link.onerror=()=>{if(again++)return done();setTimeout(()=>{link.href=bust(pre.href);},800);};pre.after(link);
  }));
  B.css=Promise.race([Promise.all(sheets),new Promise(done=>setTimeout(done,10000))]);
  const hinted=new Set();
  const hint=(href,as)=>{if(hinted.has(href))return;hinted.add(href);const l=d.createElement('link');l.href=href;if(as==='script')l.rel='modulepreload';else{l.rel='preload';l.as=as;}d.head.append(l);};
  // Only paths of this page's own release (in its import map): never a file of another version.
  const warmUp=urls=>{for(const url of urls){
    if(typeof url!=='string'||!/^\/(js|css)\/[\w\-/]+\.(js|css)$/.test(url)||asset(url)===url)continue;
    hint(asset(url),url.endsWith('.js')?'script':'style');
  }};
  try{const warm=JSON.parse(store('mnl.warm')||'[]');warmUp([...(Array.isArray(warm)?warm.slice(0,6):[]),store('mnl.scene')]);}catch{/* no hint */}
  B.response?.then(r=>{
    B.got=Date.now();   // when its headers came in: api.js clockSample
    const place=r.headers.get('X-Game-Place')||'';
    if(B.contentBase&&/^\w+$/.test(place)){const url=`${B.contentBase}&career=${place}`;B.place={url,sent:Date.now(),response:fetch(url,{credentials:'same-origin'})};B.place.response.catch(()=>{});}
    warmUp((r.headers.get('X-Game-Warm')||'').split(',').slice(0,12));
  },()=>{});
  // Giữ chân (public/js/telemetry.js, loaded after the first frame): errors before it are kept here, and a page left
  // while still loading says so in one beacon (the session cookie, if any, tells the server whose it was).
  // s: the splash still up ('loading') or the first frame out ('start'); st: where it was thrown (raw, telemetry.js
  // shortens it). A script error with no file is code an app evaluated into the page (Zalo, Facebook): not ours.
  const T=B.tele={errs:[]},keep=x=>{if(!T.on&&T.errs.length<20){x.s=d.getElementById('loading')?.hidden?'start':'loading';T.errs.push(x);}};
  // A file of this game that fails while the splash is up (06/10: a few loads around the 1.9.2 deploy): its record
  // carries the version and the HTTP status (a HEAD past the cache; 0 = no network) in its screen, e.g.
  // 'loading:v1.9.2:404', the one field the server keeps unmasked. app.js itself (the module script: any file of its
  // graph) or a 404 (a release swapped under the page) reloads the page once, cache-busted; a second failure within
  // 2 minutes, or no network at all, shows "Tải lại" with the version and the status instead of a splash that never ends.
  const [rel,build]=String(B.version||'').split('+');   // "1.9.2+<build hash>" -> "1.9.2-c8f2e6": old or new side of a rolling deploy
  const ver=(rel.replace(/[^\w.-]/g,'').slice(0,12)+(build?`-${build.replace(/\W/g,'').slice(0,6)}`:''))||'x';
  const splash=()=>d.getElementById('loading');
  const loadingNow=()=>!T.on&&!splash()?.hidden;
  const RETRY='mnl.bootRetry';
  const retried=()=>{try{return Date.now()-Number(sessionStorage.getItem(RETRY)||0)<120000;}catch{return true;}};
  const reload=()=>{try{sessionStorage.setItem(RETRY,String(Date.now()));}catch{/* private mode: still reload */}location.replace(bust(location.href));};
  const panel=(what,h,slow)=>{
    const box=splash();if(!box){d.addEventListener('DOMContentLoaded',()=>panel(what,h,slow),{once:true});return;}
    const mine=box.querySelector('[data-boot-fail]');
    if(box.hidden||(mine?slow:box.querySelector('button')))return;   // the game is out, or app.js shows its own "Thử kết nối lại"
    mine?.remove();
    const w=d.createElement('div'),p=box.querySelector('p'),b=d.createElement('button'),s=d.createElement('small');
    if(p)p.textContent=slow?'Mạng hơi chậm, khu phố vẫn đang tải… Lâu quá thì bấm Tải lại nha.':'Tải chưa xong rồi 😢 Mạng chập chờn hoặc khu phố vừa cập nhật. Bấm Tải lại là vào được nha!';
    if(!slow)box.querySelector('.splash-bar')?.remove();
    w.dataset.bootFail='';w.style.cssText='display:flex;flex-direction:column;align-items:center';
    b.type='button';b.textContent='Tải lại';b.onclick=reload;
    b.style.cssText='margin-top:16px;padding:12px 32px;border:0;border-radius:99px;background:#c44b30;color:#fff;font:inherit;font-weight:700;font-size:1rem;cursor:pointer';
    s.style.cssText='margin-top:10px;opacity:.6;font-size:.8rem';
    s.textContent=`Phiên bản ${ver}${what?` · ${what}: ${h===0?'mất kết nối':h?`lỗi ${h}`:'chưa tải được'}`:''}`;
    w.append(b,s);box.append(w);
  };
  let probes=0;
  const failed=(t,x)=>{
    let u;try{u=new URL(x.m,location.href);}catch{return;}
    if(u.origin!==location.origin||!/^\/(js|css|i18n)\//.test(u.pathname)||!loadingNow())return;   // not one of ours, or the game is already out
    x.s+=`:v${ver}`;
    const entry=t.tagName==='SCRIPT'&&t.type==='module',name=u.pathname.split('/').pop();
    if(probes++>=3&&!entry)return;
    const status=navigator.onLine===false?Promise.resolve(0):fetch(u.href,{method:'HEAD',cache:'no-store',credentials:'same-origin'}).then(r=>r.status,()=>0);
    status.then(h=>{
      x.s+=`:${h}`;B.fail=B.fail||{name,h};
      if(!loadingNow()||!(entry||h===404))return;
      if(h&&!retried())reload();else panel(name,h);
    });
  };
  addEventListener('error',e=>{const t=e.target;
    if(t&&t!==window&&(t.src||t.href)){const x={k:'asset',m:String(t.src||t.href)};keep(x);if(x.s)failed(t,x);}
    else if(e.filename)keep({k:'js',m:String(e.message||''),st:String(e.error?.stack||`${e.filename}:${e.lineno}:${e.colno}`).slice(0,2000)});},true);
  // Nothing failed but nothing came either (a request hanging on a bad connection): offer the button after 25 s.
  setTimeout(()=>{if(loadingNow())panel(B.fail?.name,B.fail?.h,!B.fail);},25000);
  addEventListener('unhandledrejection',e=>keep({k:'promise',m:String(e.reason?.message||e.reason||''),st:String(e.reason?.stack||'').slice(0,2000)}));
  // The top 3 frames as path:line:col of this origin or ~ for another one, like telemetry.js stack().
  const short=s=>String(s||'').split('\n').map(l=>/([a-z][a-z0-9+.-]*:\/\/[^\s/]+)(\/[^\s?#)]*)[^\s)]*?:(\d+):(\d+)/i.exec(l)).filter(Boolean).slice(0,3)
    .map(f=>f[1]===location.origin?`${f[2].slice(1).slice(-80)||'-'}:${f[3]}:${f[4]}`:'~').join(' < ');
  B.stack=short;
  const gone=()=>{if(T.on||T.left)return;T.left=1;
    try{navigator.sendBeacon('/api/beacon',JSON.stringify({leave:{v:'loading',p:`v${ver}`,s:Math.round(performance.now()/1000)},errors:T.errs.splice(0,10).map(x=>{const st=short(x.st);return {k:x.k,m:x.m.split(/[?#]/)[0].slice(0,200),s:x.s,n:1,...(st?{st}:{})};})}));}catch{/* old browser */}};
  d.addEventListener('visibilitychange',()=>{if(d.visibilityState==='hidden')gone();});addEventListener('pagehide',gone);
  if(store('mnl.lang')==='en'){
    try{B.i18n=fetch(asset('/i18n/en.json'),{credentials:'same-origin'}).then(r=>r.ok?r.json():null).catch(()=>null);}catch{/* i18n.js fetches */}
  }
})();
