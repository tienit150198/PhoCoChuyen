/** 🪑 Dùng đồ thật (góp ý #372): the character sits on a chair or the sofa, lies down on the bed, reads at the bookshelf,
 * watches TV with the remote, exercises on the gym things, cooks at the stove, soaks in the tub, plays a game or an
 * instrument. Drawn with the player's own wardrobe painter (look.js paintPlayer: the same clothes, hair and colours),
 * only the hands, a prop and the body's place change. Pure SVG strings; nothing is sent or saved here (v4/home-walk.js
 * places the figure; v4/home-crowd.js draws the others' poses from live home_mv `a`). */
import {paintPlayer,SVG} from './look.js';

/** The poses a resident may show (live/home.py POSES keeps the same list). */
export const POSES=['sit','lie','read','watch','gym','cook','bath','play'];
const ARMS={sit:{l:[-14,-25],r:[14,-25]},watch:{l:[-14,-25],r:[18,-40]},read:{l:[-13,-50],r:[13,-50]},gym:{l:[-31,-99],r:[31,-99]},
  cook:{l:[-9,-43],r:[25,-52]},bath:{l:[-27,-42],r:[27,-42]},play:{l:[-10,-41],r:[10,-41]}};
const OL='#5b4535';
let CLIP=0;
const r1=v=>Math.round(v*10)/10;
/** What a piece is for, from its catalogue entry (id, tags, category): one of POSES, or '' (just a line). */
export function actFor(it){
  if(!it)return '';
  const id=it.id,tags=it.tags||[];
  if(['may_chay_bo','gia_ta','xe_dap','xe_dap_tap','ta_tay','bao_cat','ghe_tap_ta','tham_yoga','xa_don'].includes(id))return 'gym';
  if(tags.includes('bed'))return 'lie';
  if(tags.includes('soak'))return 'bath';
  if(id==='may_choi_game'||tags.includes('music')&&it.spot!=='wall'||tags.includes('toy')&&it.spot!=='wall')return 'play';
  if(tags.includes('screen')||id==='may_chieu')return 'watch';
  if(tags.includes('seat'))return 'sit';
  if(tags.includes('books')||tags.includes('reading')||tags.includes('desk'))return 'read';
  if(tags.includes('kitchen')||tags.includes('grill'))return 'cook';
  return '';
}
/** The figure in pose `act` (origin at the feet, like paintPlayer). F: look.js figureOf(...). opts.asleep: eyes shut, Zz. */
export function poseFigure(F,act,{asleep=false}={}){
  const out=[],hand=F?.skin?.hand||'#f3c9a8',face=F?.skin?.face||'#f6d2b8';
  paintPlayer(out,F,SVG,ARMS[act]||null);
  let body=out.join(''),over='';
  const hands=(...ps)=>ps.map(([x,y])=>`<ellipse cx="${x}" cy="${y}" rx="7" ry="7.5" fill="${hand}"/>`).join('');
  const shut=`<ellipse cx="-11" cy="-78" rx="6.5" ry="8" fill="${face}"/><ellipse cx="11" cy="-78" rx="6.5" ry="8" fill="${face}"/><path d="M-16 -77q5 4 10 0M6 -77q5 4 10 0" fill="none" stroke="#705140" stroke-width="2.2" stroke-linecap="round"/>`;
  switch(act){
    case'read':over=`<path d="M-24 -66l22 4v24l-22-4z" fill="#fffdf3" stroke="${OL}" stroke-width="1.6"/><path d="M24 -66l-22 4v24l22-4z" fill="#fff6e6" stroke="${OL}" stroke-width="1.6"/>`
      +`<path d="M-19 -58l13 2M-19 -52l13 2M19 -58l-13 2M19 -52l-13 2" stroke="#c9b8a4" stroke-width="1.4"/><path d="M-25 -40l23 4l23-4" fill="none" stroke="#b5523b" stroke-width="3"/>`+hands([-13,-50],[13,-50]);break;
    case'watch':over=`<rect x="13" y="-48" width="9" height="15" rx="3" fill="#3d3a4a"/><circle cx="17.5" cy="-44" r="1.6" fill="#ef7f72"/>`+hands([18,-40]);break;
    case'gym':over=`<g class="hp-bar"><rect x="-44" y="-104" width="88" height="5" rx="2.5" fill="#6b6f80"/><rect x="-50" y="-112" width="9" height="21" rx="3" fill="#3d3a4a"/><rect x="41" y="-112" width="9" height="21" rx="3" fill="#3d3a4a"/></g>`
      +hands([-31,-99],[31,-99])+`<path d="M36 -78q4 6 0 9" fill="none" stroke="#7fc8f0" stroke-width="2.4" stroke-linecap="round"/>`;break;
    case'cook':over=`<ellipse cx="38" cy="-50" rx="15" ry="5" fill="#3d3a4a"/><rect x="17" y="-53" width="12" height="4" rx="2" fill="#8a6a4a"/>`
      +hands([25,-52])+`<path class="hp-steam" d="M32 -62q-4 -6 0 -12q4 -6 0 -12M42 -60q-4 -6 0 -12" fill="none" stroke="#fff" stroke-opacity=".85" stroke-width="2.6" stroke-linecap="round"/>`;break;
    case'play':over=`<rect x="-17" y="-48" width="34" height="13" rx="6" fill="#4b5a8a" stroke="${OL}" stroke-width="1.4"/><circle cx="-9" cy="-41.5" r="2.2" fill="#ffe08a"/><circle cx="9" cy="-41.5" r="2.2" fill="#ef7f72"/>`
      +hands([-10,-41],[10,-41])+`<path class="hp-note" d="M30 -96v-12l8-2v12" fill="none" stroke="${OL}" stroke-width="1.6"/><circle cx="28" cy="-96" r="3" fill="#a993d8"/><circle cx="36" cy="-98" r="3" fill="#a993d8"/>`;break;
    case'bath':{const id=`hpc${++CLIP}`;
      body=`<clipPath id="${id}"><rect x="-70" y="-190" width="140" height="152"/></clipPath><g clip-path="url(#${id})">${body}</g>`;
      over=[-30,-16,0,16,30].map((x,i)=>`<circle cx="${x}" cy="${-38+(i%2)*3}" r="${7+(i%3)}" fill="#fff" stroke="#bfe7f7" stroke-width="1.5"/>`).join('')
        +`<circle class="hp-bubble" cx="22" cy="-70" r="4" fill="#fff" fill-opacity=".8" stroke="#bfe7f7"/>`;break;}
    case'lie':
      body+=`<path d="M-31 -54h62v52q0 6-6 6h-50q-6 0-6-6z" fill="#a9d6f5" stroke="${OL}" stroke-width="1.6"/><path d="M-31 -46h62" stroke="#d6ecfb" stroke-width="4"/>`;
      if(asleep)body+=shut;
      break;
  }
  return body+over;
}
/** The pose drawn in the room: `fig` (poseFigure markup) at (dx, dy) from where the character stands, at scale k; a lying
 * figure turned with its head toward the pillow (`flip`: the pillow on the right). */
export function posed(fig,act,{dx=0,dy=0,k=.42,flip=false,asleep=false}={}){
  const turn=act==='lie'?` rotate(${flip?90:-90})`:flip?' scale(-1 1)':'';
  const zz=act==='lie'&&asleep?`<g class="hp-zz" aria-hidden="true"><text x="${flip?26:-26}" y="-30" font-size="11" font-weight="700" fill="#7b8fc7">z</text><text x="${flip?33:-33}" y="-40" font-size="14" font-weight="700" fill="#7b8fc7">Z</text></g>`:'';
  return `<g class="hp-pose hp-${act}" transform="translate(${r1(dx)} ${r1(dy)})"><g class="hp-body" transform="scale(${k})${turn}">${fig}</g>${zz}</g>`;
}
/** Where a pose sits on its piece, from the piece's drawing origin `a` ([x, y], deco-art anchor) and the character's
 * standing spot `s`: the offset {dx, dy} and the side (a bed's pillow). W: the piece's width in pixels, D: its depth. */
export function seatOf(act,it,a,s,{W,D,h=40,f=0}={}){
  const cx=a[0]+W/2;
  if(act==='sit'){const seat=Math.max(10,Math.min(24,h*.36));return {dx:cx-s[0],dy:a[1]-seat+8-s[1]};}
  if(act==='lie'){const flip=!!f,head=a[0]+W*(flip?.72:.28);return {dx:head+(flip?-35:35)-s[0],dy:a[1]-D*.5-s[1],flip};}
  if(act==='bath')return {dx:cx-s[0],dy:a[1]-8-s[1]};
  return {dx:0,dy:0};
}
/** The same pose for a resident seen from another screen (no piece known there): a small fixed lift. */
export const remoteSeat={sit:{dy:-12},lie:{dy:-16},bath:{dy:-8}};
