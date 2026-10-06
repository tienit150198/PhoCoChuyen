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
  try{const t=store('mnl.theme');if(t&&/^[a-z_]+$/.test(t))d.documentElement.dataset.theme=t;}catch{/* ignore */}
  try{
    B.response=fetch('/api/bootstrap?lite=1',{credentials:'same-origin',headers:{'X-Game-Delta':'1'}});  // its state's parts named (api.js Held)
    const content=meta('mnl-content');
    if(content){B.contentBase=content;B.contentUrl=content+'&part=core';B.content=fetch(B.contentUrl,{credentials:'same-origin'});}
  }catch{/* old browser: api.js fetches */}
  const sheets=[...d.querySelectorAll('link[rel="preload"][as="style"]')].map(pre=>new Promise(done=>{
    const link=d.createElement('link');link.rel='stylesheet';link.href=pre.href;
    link.onload=link.onerror=()=>done();pre.after(link);
  }));
  B.css=Promise.race([Promise.all(sheets),new Promise(done=>setTimeout(done,10000))]);
  const hinted=new Set();
  const hint=(href,as)=>{if(hinted.has(href))return;hinted.add(href);const l=d.createElement('link');l.href=href;if(as==='script')l.rel='modulepreload';else{l.rel='preload';l.as=as;}d.head.append(l);};
  // Only paths of this page's own release (in its import map): never a file of another version.
  const warmUp=urls=>{for(const url of urls){
    if(typeof url!=='string'||!/^\/(js|css)\/[\w\-/]+\.(js|css)$/.test(url)||asset(url)===url)continue;
    hint(asset(url),url.endsWith('.js')?'script':'style');
  }};
  try{const warm=JSON.parse(store('mnl.warm')||'[]');warmUp(Array.isArray(warm)?warm.slice(0,6):[]);}catch{/* no hint */}
  // 🏝️ The island's Phaser bundle (~360 KB gz): fetched now, behind the first frame's files; run after the first frame.
  try{const u=asset('/js/isometric/phaser-world.js');if(u!=='/js/isometric/phaser-world.js'){const l=d.createElement('link');l.rel='modulepreload';l.href=u;l.fetchPriority='low';d.head.append(l);}}catch{/* no hint */}
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
  addEventListener('error',e=>{const t=e.target;
    if(t&&t!==window&&(t.src||t.href))keep({k:'asset',m:String(t.src||t.href)});
    else if(e.filename)keep({k:'js',m:String(e.message||''),st:String(e.error?.stack||`${e.filename}:${e.lineno}:${e.colno}`).slice(0,2000)});},true);
  addEventListener('unhandledrejection',e=>keep({k:'promise',m:String(e.reason?.message||e.reason||''),st:String(e.reason?.stack||'').slice(0,2000)}));
  // The top 3 frames as path:line:col of this origin or ~ for another one, like telemetry.js stack().
  const short=s=>String(s||'').split('\n').map(l=>/([a-z][a-z0-9+.-]*:\/\/[^\s/]+)(\/[^\s?#)]*)[^\s)]*?:(\d+):(\d+)/i.exec(l)).filter(Boolean).slice(0,3)
    .map(f=>f[1]===location.origin?`${f[2].slice(1).slice(-80)||'-'}:${f[3]}:${f[4]}`:'~').join(' < ');
  B.stack=short;
  const gone=()=>{if(T.on||T.left)return;T.left=1;
    try{navigator.sendBeacon('/api/beacon',JSON.stringify({leave:{v:'loading',s:Math.round(performance.now()/1000)},errors:T.errs.splice(0,10).map(x=>{const st=short(x.st);return {k:x.k,m:x.m.split(/[?#]/)[0].slice(0,200),s:x.s,n:1,...(st?{st}:{})};})}));}catch{/* old browser */}};
  d.addEventListener('visibilitychange',()=>{if(d.visibilityState==='hidden')gone();});addEventListener('pagehide',gone);
  if(store('mnl.lang')==='en'){
    try{B.i18n=fetch(asset('/i18n/en.json'),{credentials:'same-origin'}).then(r=>r.ok?r.json():null).catch(()=>null);}catch{/* i18n.js fetches */}
  }
})();
