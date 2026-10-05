/** Poses use the player's real wardrobe renderer. Only hand positions and a small body lean change. */
import {paintPlayer,SVG} from './look.js';

export const POSE_MS=3200;
export function affectionFigure(F,pose=null){
  const out=[];
  if(!pose){paintPlayer(out,F,SVG);return out.join('');}
  const {kind,role,dir,elapsed=0}=pose,receive=role==='receive';
  const arms=kind==='hug'?{l:[16,-49],r:[57,-47]}:
    kind==='kiss'?{l:[-10,-53],r:[42,-65]}:
    kind==='shy'?{l:[-17,-69],r:[17,-69]}:
    kind==='sulk'?{l:[13,-40],r:[-13,-37]}:
    receive?{l:[-12,-53],r:[14,-54]}:{l:[-6,-62],r:[9,-62]};
  paintPlayer(out,F,SVG,arms);
  const angle=kind==='hug'?10:kind==='kiss'?14:kind==='shy'?5:kind==='sulk'?-9:receive?-4:5;
  // Mirroring the canonical right-facing pose also mirrors its sleeve/hand geometry.
  return `<g class="hc-pose hc-pose-${kind}" data-role="${role}" style="--hc-lean:${angle}deg;--hc-delay:-${Math.min(POSE_MS,elapsed)}ms"><g transform="scale(${dir},1)"><g class="hc-body" transform="rotate(${angle} 0 -8)">${out.join('')}${kind==='shy'?'<ellipse cx="-20" cy="-66" rx="8" ry="5" fill="#ec8097"/><ellipse cx="20" cy="-66" rx="8" ry="5" fill="#ec8097"/>':''}${kind==='kiss'?'<path d="M27 -64q8 -5 10 0q-3 5 -10 0" fill="#c95574"/>':''}${kind==='sulk'?'<path d="M-6 -61q6 -5 12 0" fill="none" stroke="#a86e60" stroke-width="2"/>':''}</g></g></g>`;
}
