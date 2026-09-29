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

export class UpdateNotice{
  constructor(own='',{doc=globalThis.document,storage=globalThis.localStorage,session=globalThis.sessionStorage,reload=()=>globalThis.location.reload(),idle=()=>false}={}){
    this.own=own;this.doc=doc;this.storage=storage;this.session=session;this.reload=reload;this.shown=null;this.el=null;this.timer=null;
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
