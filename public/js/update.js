/** "Đã có phiên bản mới" pill: the server runs a different release than the one this page booted with.
 * Every API response carries X-Game-Version (`<release>+<build>`, server.py); api.js hands it to seen().
 * A light /api/health check also runs every 5 minutes and whenever the tab becomes visible again.
 * While the player is on the page nothing reloads by itself (they may be mid-task): the pill offers it.
 * It shows once per version; dismissing hides it until the next version. A response that says this
 * client is too old (code `client_outdated` or HTTP 426) shows it at once, even for a dismissed version.
 * Coming back to the tab (hidden → visible, or a page restored from the back/forward cache) is the one
 * moment the page reloads itself onto the new release, when idle() says nothing is being typed or sent:
 * a tab left open across a deploy otherwise keeps the old code, and on iOS such a resumed tab was seen
 * with every work card blank ("game mất chữ"). Once per version per tab (sessionStorage), so a proxy that
 * still serves the old page can never cause a reload loop.
 * While the pill is up, prewarmRelease() puts the new release's first-frame files into the HTTP cache, so the
 * reload it offers opens like a warm start.
 * Styles are inline in index.html (.update-pill), so it works whatever the stylesheets are doing. */
import {t} from './v4/i18n.js';

export const TEXT='Đã có phiên bản mới, bạn tải lại để cập nhật nha';
export const LATER='Để sau';
export const OUTDATED_CODES=new Set(['client_outdated']);
const DISMISSED='mnl.update.dismissed',AUTO='mnl.update.auto',POLL=5*60*1000;

/** -1, 0 or 1 for the release part of two `<release>+<build>` strings (null when not comparable). */
export function compareRelease(a,b){
  const parse=v=>String(v||'').split('+')[0].split('.').map(n=>/^\d+$/.test(n)?Number(n):NaN);
  const x=parse(a),y=parse(b);
  if(!x.length||!y.length||x.some(Number.isNaN)||y.some(Number.isNaN))return null;
  for(let i=0;i<Math.max(x.length,y.length);i++){const d=(x[i]||0)-(y[i]||0);if(d)return d>0?1:-1;}
  return 0;
}

/** Should the pill be offered for `seen`, given this page's own version and the last dismissed one?
 * An older release on the server (a rolling deploy still restarting its workers) is not an update. */
export function shouldOffer(own,seen,dismissed,incompatible=false){
  if(!seen||!own)return Boolean(incompatible);
  if(incompatible)return true;
  if(seen===own||seen===dismissed)return false;
  return compareRelease(seen,own)!==-1;
}

/** The URLs a page's first frame loads (its module graph and stylesheets, all ?v=<hash>), from its HTML. */
export function releaseUrls(html){
  const urls=new Set();
  for(const m of String(html).matchAll(/(?:href|src)="(\/(?:js|css)\/[\w\-/.]+\?v=[0-9a-f]{8,16})"/g))urls.add(m[1]);
  return urls;
}

/** A newer release is live and the pill offers the reload: fetch that release's page (~8 KB, no-cache) and put what
 * its first frame loads into the HTTP cache at the lowest priority (<link rel=prefetch>): its modules and stylesheets,
 * this browser's workplace (workbench, scene: mnl.warm/mnl.scene through its import map) and the first part of its
 * catalogue. Only ?v=<hash> URLs, which name exact bytes (never a mix of versions), and only the ones this page does
 * not use itself (those are cached already). Skipped on Data Saver / 2G. Returns how many it asked for. */
export async function prewarmRelease(doc=globalThis.document,storage=globalThis.localStorage){
  const c=globalThis.navigator?.connection;if(!doc||(c&&(c.saveData||/2g/.test(c.effectiveType||''))))return 0;
  const res=await fetch('/',{credentials:'same-origin',cache:'no-cache'});if(!res.ok)return 0;
  const html=await res.text(),want=releaseUrls(html);
  let map={};try{map=JSON.parse(/<script type="importmap">(.*?)<\/script>/s.exec(html)?.[1]||'{}').imports||{};}catch{/* none */}
  const get=k=>{try{return storage?.getItem(k);}catch{return null;}};
  let warm=[];try{warm=JSON.parse(get('mnl.warm')||'[]');}catch{/* none */}
  for(const path of [...(Array.isArray(warm)?warm.slice(0,6):[]),get('mnl.scene')])if(typeof path==='string'&&map[path])want.add(map[path]);
  const content=/<meta name="mnl-content" content="([^"]+)">/.exec(html)?.[1];
  if(content&&/^\/api\/content\?v=[0-9a-f]+$/.test(content))want.add(content+'&part=core');
  const own=new Set(doc.querySelector?.('script[type="importmap"]')?Object.values(JSON.parse(doc.querySelector('script[type="importmap"]').textContent||'{}').imports||{}):[]);
  const mine=doc.querySelector?.('meta[name="mnl-content"]')?.content;if(mine)own.add(mine+'&part=core');
  let n=0;
  for(const url of want){
    if(own.has(url)||n>=120)continue;
    const l=doc.createElement('link');l.rel='prefetch';l.href=url;doc.head.append(l);n++;
  }
  return n;
}

export class UpdateNotice{
  constructor(own='',{doc=globalThis.document,storage=globalThis.localStorage,session=globalThis.sessionStorage,reload=()=>globalThis.location.reload(),idle=()=>false,prewarm=null}={}){
    this.own=own;this.doc=doc;this.storage=storage;this.session=session;this.reload=reload;this.shown=null;this.el=null;this.timer=null;
    /** Called once per version while the pill is up (prewarmRelease in the page). */
    this.prewarm=prewarm;this.warmed=null;
    /** Set by the page: true when a reload loses nothing (no text being typed, no command on the wire). */
    this.idle=idle;this.returning=false;
  }
  dismissed(){try{return this.storage?.getItem(DISMISSED)||'';}catch{return '';}}
  /** A version seen on the wire (header or /api/health). The first one adopts it when the page has none. */
  seen(version,incompatible=false){
    if(!version&&!incompatible)return false;
    if(!this.own&&version&&!incompatible){this.own=version;return false;}
    if(!shouldOffer(this.own,version,this.dismissed(),incompatible))return false;
    if((this.returning||incompatible)&&this.autoReload(version||'incompatible'))return true;
    this.show(version||'incompatible');return true;
  }
  /** Reload onto the new release by itself: only when idle, and once per version in this tab. */
  autoReload(version){
    let idle=false;try{idle=Boolean(this.idle());}catch{idle=false;}
    if(!idle)return false;
    try{if(this.session?.getItem(AUTO)===version)return false;this.session?.setItem(AUTO,version);}catch{return false;}
    this.reload();return true;
  }
  show(version){
    if(this.shown===version&&this.el?.isConnected)return;
    this.shown=version;const doc=this.doc;if(!doc?.body)return;
    this.el?.remove();
    const el=this.el=doc.createElement('div');el.className='update-pill';el.setAttribute('role','status');el.dataset.version=version;
    const go=doc.createElement('button');go.type='button';go.className='update-go';go.textContent=t(TEXT);
    const x=doc.createElement('button');x.type='button';x.className='update-x';x.setAttribute('aria-label',t(LATER));x.title=t(LATER);x.textContent='✕';
    go.addEventListener('click',()=>this.reload());
    x.addEventListener('click',()=>this.dismiss());
    el.append(go,x);doc.body.append(el);
    if(this.prewarm&&this.warmed!==version&&version!=='incompatible'&&version!==this.own){this.warmed=version;Promise.resolve().then(()=>this.prewarm(version)).catch(()=>{});}
    // Popover = top layer: above an open sheet (<dialog>). Older browsers: a fixed, very high z-index.
    if(typeof el.showPopover==='function'){try{el.popover='manual';el.showPopover();return;}catch{/* fall through */}}
    el.classList.add('is-open');
  }
  dismiss(){
    try{this.storage?.setItem(DISMISSED,this.shown||'');}catch{/* storage blocked */}
    this.el?.remove();this.el=null;
  }
  /** Poll /api/health every 5 minutes (visible tab only) and when the tab comes back; a new release
   * seen on the way back reloads the page when it is idle (autoReload), otherwise shows the pill. */
  watch(check,win=globalThis){
    const doc=this.doc;if(!doc||this.timer)return;
    const run=()=>{if(doc.visibilityState!=='hidden')check().catch(()=>{});};
    const back=()=>{
      if(doc.visibilityState==='hidden')return;
      this.returning=true;let done;
      try{done=check();}catch{done=null;}
      Promise.resolve(done).catch(()=>{}).finally(()=>{this.returning=false;});
    };
    this.timer=setInterval(run,POLL);
    doc.addEventListener('visibilitychange',()=>{if(doc.visibilityState==='visible')back();});
    win?.addEventListener?.('pageshow',e=>{if(e.persisted)back();});
  }
}
