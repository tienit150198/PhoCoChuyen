/** Pixel marks for information controls only. Scene and portrait art keep their illustrated renderer. */
import {pixelIcon} from '../pixel/icons.js';
const frames={
  chats:[[1,2,10,1],[1,3,1,6],[10,3,1,5],[2,8,7,1],[2,9,1,3],[3,9,1,2],[4,9,1,1],[12,5,2,1],[13,6,1,6],[7,11,6,1],[11,12,1,1],[12,12,1,2],[5,10,1,2]],
  overview:[[2,2,5,1],[2,2,1,5],[9,2,5,1],[13,2,1,5],[2,9,1,5],[2,13,5,1],[13,9,1,5],[9,13,5,1],[6,6,4,4],[8,5,3,2]],
  compass:[[7,0,2,4],[0,7,4,2],[7,12,2,4],[12,7,4,2],[5,5,6,1],[5,10,6,1],[5,6,1,4],[10,6,1,4],[7,7,2,2]],
};
export function uiIcon(name,size=20){
  const cells=frames[name];if(!cells)return pixelIcon(name,size);
  return `<svg class="icon pixel-ui-icon" width="${size}" height="${size}" viewBox="0 0 16 16" shape-rendering="crispEdges" aria-hidden="true">${cells.map(([x,y,w,h])=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="currentColor"/>`).join('')}</svg>`;
}
