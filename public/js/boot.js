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
    B.response=fetch('/api/bootstrap?lite=1',{credentials:'same-origin'});
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
  try{const warm=JSON.parse(store('mnl.warm')||'[]');warmUp([...(Array.isArray(warm)?warm.slice(0,6):[]),store('mnl.scene')]);}catch{/* no hint */}
  B.response?.then(r=>{
    const place=r.headers.get('X-Game-Place')||'';
    if(B.contentBase&&/^\w+$/.test(place)){const url=`${B.contentBase}&career=${place}`;B.place={url,sent:Date.now(),response:fetch(url,{credentials:'same-origin'})};B.place.response.catch(()=>{});}
    warmUp((r.headers.get('X-Game-Warm')||'').split(',').slice(0,12));
  },()=>{});
  if(store('mnl.lang')==='en'){
    try{B.i18n=fetch(asset('/i18n/en.json'),{credentials:'same-origin'}).then(r=>r.ok?r.json():null).catch(()=>null);}catch{/* i18n.js fetches */}
  }
})();
