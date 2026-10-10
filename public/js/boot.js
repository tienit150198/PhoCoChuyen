/* First script of the page. server.py inlines it into index.html (allowed by a CSP hash, see
 * game/webassets.py); the raw template loads it as a file instead. With no imports it runs while the
 * module graph is still downloading, and starts everything that does not need app.js:
 * - /api/bootstrap?lite=1 (state) and /api/content?v=<hash>&part=core (the catalogue's first-frame part, cached
 *   for a year) in parallel;
 * - the stylesheets announced by <link rel=preload as=style>, applied without blocking the first paint
 *   (the splash is styled inline); api.js waits for them before the game is shown;
 * - the workbench and stylesheets of the workplace this browser opened last (mnl.warm), and the
 *   English pack for English players (mnl.lang), so they no longer wait for bootstrap + app.js;
 * - on a cold start (nothing stored), the ones /api/bootstrap names in its X-Game-Warm header, and that
 *   workplace's part of the catalogue (X-Game-Place), as soon as the response headers are in (the body is still
 *   on its way), instead of an import chain after app.js.
 * api.js init() picks all of this up from globalThis.__mnlBoot; without it, it fetches on its own. */
(()=>{
  // Old iPhones (07/10, iOS 15 / 16.0–16.3 could not open the game). Before the polyfills below: is this browser
  // older than the game targets (no regex lookbehind = Safari < 16.4, no Object.hasOwn = Safari < 15.4 / Chrome < 93)?
  // Only used to word the failure panel; scripts/check_old_safari.mjs keeps the game's files parseable there.
  let oldBrowser=typeof Object.hasOwn!=='function';
  try{new RegExp('(?<=a)b');}catch{oldBrowser=true;}   // old-safari-ok: a probe, in try
  // Built-ins Safari 15.0–15.3 lacks (iOS 15 phones not updated past 15.3). Only when missing, never enumerable.
  // scripts/check_old_safari.mjs lets the game call these only because they are defined here (keep the poly(…) form).
  const poly=(o,name,fn)=>{if(o&&typeof o[name]!=='function'){try{Object.defineProperty(o,name,{value:fn,writable:true,configurable:true});}catch{/* frozen */}}};
  const at=function(i){const n=this.length>>>0;i=Math.trunc(Number(i))||0;if(i<0)i+=n;return i<0||i>=n?undefined:this[i];};
  poly(Array.prototype,'at',at);poly(String.prototype,'at',at);
  try{poly(Object.getPrototypeOf(Int8Array.prototype),'at',at);}catch{/* no typed arrays */}
  poly(Object,'hasOwn',(o,k)=>{if(o==null)throw new TypeError('Cannot convert undefined or null to object');return Object.prototype.hasOwnProperty.call(Object(o),k);});
  poly(Array.prototype,'findLast',function(f,t){for(let i=(this.length>>>0)-1;i>=0;i--)if(f.call(t,this[i],i,this))return this[i];return undefined;});
  poly(Array.prototype,'findLastIndex',function(f,t){for(let i=(this.length>>>0)-1;i>=0;i--)if(f.call(t,this[i],i,this))return i;return -1;});
  const C=globalThis.crypto;
  if(C&&typeof C.getRandomValues==='function')poly(C,'randomUUID',()=>{const b=C.getRandomValues(new Uint8Array(16));b[6]=b[6]&15|64;b[8]=b[8]&63|128;
    const h=Array.from(b,x=>(x+256).toString(16).slice(1)).join('');return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;});
  // Canvas roundRect (Safari 16.0). 07/10: about 3,700 "roundRect is not a function" from iOS 15.4–15.8 once 1.9.14
  // let them in, and no scene drew (scenes/kit.js R(), world.js, boba-world.js and ~45 other files call it).
  // The HTML spec's steps: radii a number, a DOMPointInit {x,y} or a list of 1–4 of them (RangeError otherwise or when
  // negative), non-finite input draws nothing, overlapping corners scaled down, a negative w/h flips the rectangle
  // (and the direction), then a new subpath at its top left. Corners are quarter ellipses (x and y radii may differ).
  // Pixel for pixel the native one of Chromium and WebKit (fill, stroke, Path2D; dashes start where Chromium's do).
  const roundRect=function(x,y,w,h,radii=0){
    x=+x;y=+y;w=+w;h=+h;
    const list=radii!==null&&typeof radii==='object'&&typeof radii[Symbol.iterator]==='function'?[...radii]:[radii];
    if(![x,y,w,h].every(Number.isFinite))return;
    if(list.length<1||list.length>4)throw new RangeError(`roundRect: ${list.length} radii, expected 1 to 4`);
    const r=[];
    for(const v of list){
      const p=v!==null&&typeof v==='object'?[+(v.x??0),+(v.y??0)]:[+v,+v];
      if(!Number.isFinite(p[0])||!Number.isFinite(p[1]))return;
      if(p[0]<0||p[1]<0)throw new RangeError(`roundRect: radius ${p[0]<0?p[0]:p[1]} is negative`);
      r.push(p);
    }
    const n=r.length;   // upper-left, upper-right, lower-right, lower-left
    let [ul,ur,lr,ll]=n===4?r:n===3?[r[0],r[1],r[2],r[1]]:n===2?[r[0],r[1],r[0],r[1]]:[r[0],r[0],r[0],r[0]];
    let cw=true;
    if(w<0){x+=w;w=-w;cw=!cw;[ul,ur,lr,ll]=[ur,ul,ll,lr];}
    if(h<0){y+=h;h=-h;cw=!cw;[ul,ur,lr,ll]=[ll,lr,ur,ul];}
    const s=Math.min(w/(ul[0]+ur[0]),h/(ur[1]+lr[1]),w/(lr[0]+ll[0]),h/(ul[1]+ll[1]));
    if(s<1)[ul,ur,lr,ll]=[ul,ur,lr,ll].map(([a,b])=>[a*s,b*s]);
    const H=Math.PI/2;
    // [centre x, centre y, rx, ry, start angle, end angle] of each corner, clockwise from the top right.
    const C={ur:[x+w-ur[0],y+ur[1],ur[0],ur[1],-H,0],lr:[x+w-lr[0],y+h-lr[1],lr[0],lr[1],0,H],
      ll:[x+ll[0],y+h-ll[1],ll[0],ll[1],H,2*H],ul:[x+ul[0],y+ul[1],ul[0],ul[1],2*H,3*H]};
    this.moveTo(x+ul[0],y);
    for(const k of cw?['ur','lr','ll','ul']:['ul','ll','lr','ur']){
      const [cx,cy,rx,ry,a0,a1]=C[k],[from,to]=cw?[a0,a1]:[a1,a0];
      if(rx>0&&ry>0)this.ellipse(cx,cy,rx,ry,0,from,to,!cw);
      else{this.lineTo(cx+rx*Math.cos(from),cy+ry*Math.sin(from));this.lineTo(cx+rx*Math.cos(to),cy+ry*Math.sin(to));}
    }
    this.closePath();this.moveTo(x,y);
  };
  poly(globalThis.CanvasRenderingContext2D?.prototype,'roundRect',roundRect);
  poly(globalThis.Path2D?.prototype,'roundRect',roundRect);
  poly(globalThis.OffscreenCanvasRenderingContext2D?.prototype,'roundRect',roundRect);
  // <dialog> (Safari 15.4, Firefox 98): iOS 15.0–15.3 could open no sheet (~39 showModal() calls). Only where the
  // browser has no HTMLDialogElement at all: open/show/showModal/close/returnValue, a 'close' event, Escape fires a
  // cancelable 'cancel', a .mnl-backdrop element under the dialog (a tap on it is a tap on the dialog, like ::backdrop).
  if(typeof HTMLDialogElement!=='function'&&typeof HTMLElement==='function'&&typeof document==='object'){try{
    const P=HTMLElement.prototype,open=[],dd=document;let z=2147480000;
    const css=dd.createElement('style');
    css.textContent='dialog:not([open]){display:none!important}dialog[open]{display:block}'
      +'dialog{position:absolute;left:0;right:0;margin:auto;width:-webkit-fit-content;width:fit-content;height:-webkit-fit-content;height:fit-content;border:solid;padding:1em;background:#fff;color:#000}'
      +'dialog.mnl-modal{position:fixed;top:0;bottom:0;max-width:calc(100% - 6px - 2em);max-height:calc(100% - 6px - 2em);overflow:auto}'
      +'.mnl-backdrop{position:fixed;top:0;right:0;bottom:0;left:0;background:rgba(0,0,0,.4)}';
    (dd.head||dd.documentElement).append(css);
    if(!('open' in P))Object.defineProperty(P,'open',{configurable:true,get(){return this.hasAttribute('open');},set(v){this.toggleAttribute('open',Boolean(v));}});
    if(!('returnValue' in P))Object.defineProperty(P,'returnValue',{configurable:true,writable:true,value:''});
    poly(P,'show',function(){this.setAttribute('open','');});
    poly(P,'showModal',function(){
      if(this.hasAttribute('open'))return;
      const b=dd.createElement('div');b.className='mnl-backdrop';b.style.zIndex=String(z++);this.style.zIndex=String(z++);
      // A dialog removed or un-opened without close() leaves no backdrop over the game: the next tap clears it.
      b.addEventListener('click',()=>{if(this.isConnected&&this.hasAttribute('open'))this.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));
        else{b.remove();const i=open.indexOf(this);if(i>=0)open.splice(i,1);}});
      this.before(b);this._mnlBack=b;this.classList.add('mnl-modal');this.setAttribute('open','');open.push(this);
      this.querySelector('[autofocus]')?.focus?.();
    });
    poly(P,'close',function(v){
      if(!this.hasAttribute('open'))return;
      if(v!==undefined)this.returnValue=String(v);
      this.removeAttribute('open');this.classList.remove('mnl-modal');this._mnlBack?.remove();this._mnlBack=null;
      const i=open.indexOf(this);if(i>=0)open.splice(i,1);
      this.dispatchEvent(new Event('close'));
    });
    dd.addEventListener('keydown',e=>{const top=open[open.length-1];
      if(e.key==='Escape'&&top&&top.dispatchEvent(new Event('cancel',{cancelable:true})))top.close();},true);
  }catch{/* keep going without */}}
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
    if(typeof url!=='string'||!/^\/(js|css)\/[\w\-/]+\.(js|css)$/.test(url)||url.startsWith('/js/scenes/')||asset(url)===url)continue;
    hint(asset(url),url.endsWith('.js')?'script':'style');
  }};
  try{const warm=JSON.parse(store('mnl.warm')||'[]');warmUp(Array.isArray(warm)?warm.slice(0,6):[]);}catch{/* no hint */}
  // Renderer assets wait for the authenticated save's interface preference (interface-mode.js).
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
  // Failed loads of this tab within 2 minutes ({n, at}): the first reloads by itself, the second shows a panel.
  // No session storage (private mode): never reload by itself, it could not count and would loop.
  const RETRY='mnl.bootRetry';
  const fails=()=>{try{const r=JSON.parse(sessionStorage.getItem(RETRY)||'null');return r&&Date.now()-Number(r.at||0)<120000?Number(r.n)||1:0;}catch{return 1;}};
  const reload=()=>{location.replace(bust(location.href));};
  const panel=(what,h,slow,old)=>{
    const box=splash();if(!box){d.addEventListener('DOMContentLoaded',()=>panel(what,h,slow,old),{once:true});return;}
    const mine=box.querySelector('[data-boot-fail]');
    if(box.hidden||(mine?slow:box.querySelector('button')))return;   // the game is out, or app.js shows its own "Thử kết nối lại"
    mine?.remove();
    const w=d.createElement('div'),p=box.querySelector('p'),b=d.createElement('button'),s=d.createElement('small');
    if(p)p.textContent=old?'Trình duyệt này quá cũ nên khu phố chưa mở được 😢 Bạn cập nhật iOS (Cài đặt → Cài đặt chung → Cập nhật phần mềm) hoặc mở game bằng Chrome nha!'
      :slow?'Mạng hơi chậm, khu phố vẫn đang tải… Lâu quá thì bấm Tải lại nha.':'Tải chưa xong rồi 😢 Mạng chập chờn hoặc khu phố vừa cập nhật. Bấm Tải lại là vào được nha!';
    if(!slow)box.querySelector('.splash-bar')?.remove();
    w.dataset.bootFail=old?'old':'';w.style.cssText='display:flex;flex-direction:column;align-items:center';
    b.type='button';b.textContent=old?'Thử lại':'Tải lại';b.onclick=reload;
    b.style.cssText='margin-top:16px;padding:12px 32px;border:0;border-radius:99px;background:#c44b30;color:#fff;font:inherit;font-weight:700;font-size:1rem;cursor:pointer';
    s.style.cssText='margin-top:10px;opacity:.6;font-size:.8rem';
    s.textContent=`Phiên bản ${ver}${what?` · ${what}: ${h==='parse'?'lỗi cú pháp':h===0?'mất kết nối':h?`lỗi ${h}`:'chưa tải được'}`:''}`;
    w.append(b,s);box.append(w);
  };
  // "iPhone OS 15_8" -> ios15.8, "Chrome/90" -> chrome90: where a parse error came from (the beacon's screen field,
  // the one field the server keeps unmasked).
  const uaTag=()=>{const u=navigator.userAgent||'';let m;
    if((m=/(?:iPhone|iPad|iPod).*? OS (\d+)_(\d+)/.exec(u)))return `ios${m[1]}.${m[2]}`;
    if((m=/(?:Chrome|CriOS)\/(\d+)/.exec(u)))return `chrome${m[1]}`;
    if((m=/Version\/(\d+)\.(\d+).*Safari/.exec(u)))return `safari${m[1]}.${m[2]}`;
    if((m=/Firefox\/(\d+)/.exec(u)))return `firefox${m[1]}`;
    return 'other';};
  // A file of ours that does not parse here (07/10: regex lookbehind on Safari < 16.4) breaks the whole module
  // graph. Kept across the one reload, so the second failure knows why.
  const PARSE='mnl.bootParse';
  let parseErr=null;try{if(fails())parseErr=JSON.parse(sessionStorage.getItem(PARSE)||'null');}catch{/* none */}
  let broken=false,told=false;
  // The game's files did not load (h: HEAD status of the file, 'parse' for a syntax error). Once per page: the
  // first failure in 2 minutes reloads, cache-busted; the second shows a panel and never reloads by itself. With a
  // syntax error on an old browser the panel says to update iOS or use Chrome, and one beacon reports it with the UA.
  const broke=(name,h)=>{
    if(broken||!loadingNow())return;
    broken=true;
    let n=fails()+1;
    try{sessionStorage.setItem(RETRY,JSON.stringify({n,at:Date.now()}));}catch{n=2;/* private mode: cannot count */}
    if(h&&n<2){reload();return;}
    if(parseErr&&!told){told=true;
      try{navigator.sendBeacon('/api/beacon',JSON.stringify({errors:[{k:'js',n:1,s:`${oldBrowser?'old':'parse'}:v${ver}:${uaTag()}`.slice(0,40),
        m:`${oldBrowser?'Trình duyệt cũ':'Lỗi cú pháp'}: ${parseErr.m} | ${navigator.userAgent||''}`.slice(0,200),...(parseErr.st?{st:parseErr.st}:{})}]}));}catch{/* old browser */}}
    panel(name,h,false,Boolean(parseErr)&&oldBrowser);
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
      broke(name,h);
    });
  };
  addEventListener('error',e=>{const t=e.target;
    if(t&&t!==window&&(t.src||t.href)){const x={k:'asset',m:String(t.src||t.href)};keep(x);if(x.s)failed(t,x);}
    else if(e.filename){const m=String(e.message||''),st=String(e.error?.stack||`${e.filename}:${e.lineno}:${e.colno}`).slice(0,2000);keep({k:'js',m,st});
      // A file of ours that does not parse while the splash is up (not JSON.parse at run time): the game cannot start.
      let u;try{u=new URL(e.filename,location.href);}catch{/* not a URL */}
      if(u?.origin===location.origin&&/^\/js\//.test(u.pathname)&&loadingNow()&&!/JSON/i.test(m)
        &&(e.error?.name==='SyntaxError'||/SyntaxError|Invalid regular expression|Unexpected (reserved word|token|identifier|keyword)/i.test(m))){
        parseErr={m:m.slice(0,120),st:B.stack(`${e.filename}:${e.lineno}:${e.colno}`)};
        try{sessionStorage.setItem(PARSE,JSON.stringify(parseErr));}catch{/* private mode */}
        // Safari also fails the module <script> (handled above, after a HEAD); Chrome reports the parse error only.
        setTimeout(()=>broke(u.pathname.split('/').pop(),'parse'),3000);
      }}},true);
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
