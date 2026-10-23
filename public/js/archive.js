/** "Xem cũ hơn": older rows of a history (Nhật ký, Sổ dòng tiền, Bảng tin, Sổ ví).
 * The newest rows come with the state; older ones page in, newest first, from
 * GET /api/archive, which serves the rest of the save's own rows and then the archive
 * (game/archive.py: nothing a player made is dropped). Pages stay until the save moves on. */
import {escapeHTML as esc} from './icons.js';

const pages=new Map();let revision=null;
const keyOf=(career,kind)=>`${career}|${kind}`;
const pageOf=(career,kind)=>pages.get(keyOf(career,kind))||{rows:[],before:null,done:false,loading:false};

/** Forget loaded pages once the save changed (the newest rows shown from the state moved). */
export function syncOlder(rev){if(rev!==revision){pages.clear();revision=rev;}}

/** The page of a history: {rows, before, done, loading} (the album opens its first page by itself). */
export function olderPage(career,kind){return pageOf(career,kind);}

/** Older rows loaded so far, newest first. */
export function olderRows(career,kind){return pageOf(career,kind).rows;}

/** Load the next page. `shown`: rows of this history already shown from the state (newest ones).
 * `limit`: rows a page (album photos are large: a few at a time). */
export async function loadOlder(api,career,kind,shown,limit=50){
  const k=keyOf(career,kind),page=pageOf(career,kind);if(page.done||page.loading)return page;
  page.loading=true;pages.set(k,page);
  try{
    const from=page.rows.length&&page.before!==null?`before=${page.before}`:`skip=${Number(shown)||0}`;
    const data=await api.json(`/api/archive?career=${encodeURIComponent(career)}&kind=${encodeURIComponent(kind)}&${from}&limit=${Math.max(1,Math.min(200,Number(limit)||50))}`);
    page.rows.push(...data.rows.map(r=>r.row));page.before=data.before;page.done=data.before===null;
  }finally{page.loading=false;}
  return page;
}

/** The button under a history list (nothing once everything is shown). `maybe`: older
 * rows can exist (the list from the state is longer than what is shown, or it is full). */
export function olderButton(career,kind,shown,maybe=true,limit=0){
  const page=pageOf(career,kind);
  if(!maybe&&!page.rows.length)return'';
  if(page.done)return page.rows.length?'<p class="muted small space-top older-end">Đã xem hết sổ cũ.</p>':'';
  return `<button type="button" class="btn ghost small full space-top older-btn" data-action="loadOlder" data-career="${esc(career)}" data-kind="${esc(kind)}" data-shown="${Number(shown)||0}"${limit?` data-limit="${Number(limit)}"`:''}${page.loading?' disabled':''}>Xem cũ hơn</button>`;
}
